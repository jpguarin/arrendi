import logging
from dataclasses import replace
from datetime import date
from uuid import UUID, uuid4

from fastapi import BackgroundTasks
from sqlalchemy import Select, exists, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.errors import AppError, conflict, not_found, storage_unavailable
from app.models import (
    Bill,
    BillItem,
    Lease,
    LeaseItem,
    Notification,
    Owner,
    Payment,
    Property,
    Tenant,
    Unit,
)
from app.pdf.bill import BillDocument, BillLine, SignatureError, render_bill
from app.pdf.format import format_month
from app.schemas.bill import (
    BillCreate,
    BillIssuer,
    BillItemResponse,
    BillResponse,
    BillStatusFilter,
    BillSummary,
    NotificationResponse,
)
from app.schemas.document import DocumentUrlResponse
from app.schemas.payment import PaymentResponse
from app.storage import Storage, StorageError

logger = logging.getLogger(__name__)

# Every query here runs inside the owner's transaction: row security already limits it to
# their rows, so another owner's id simply finds nothing.

ONE_MONTHLY_PER_PERIOD = "bills_one_monthly_per_period"
RENT = "Canon de arrendamiento"
DEPOSIT = "Depósito"
DOWNLOAD_LINK_SECONDS = 300
RECENT_BILLS = 6
STATUS_FILTERS: dict[BillStatusFilter, tuple[str, ...]] = {
    "receivable": ("pending", "partial", "overdue"),
    "paid": ("paid",),
    "voided": ("voided",),
}


def _active_lease(session: Session, lease_id: UUID) -> Lease:
    lease = session.get(Lease, lease_id)
    if lease is None:
        raise not_found()
    if lease.status != "active":
        raise AppError(
            400,
            "Este contrato está terminado. No se le pueden generar cuentas.",
            "lease_not_active",
        )
    return lease


def _items(session: Session, bill_id: UUID) -> list[BillItem]:
    return list(
        session.scalars(
            select(BillItem)
            .where(BillItem.bill_id == bill_id)
            .order_by(BillItem.position, BillItem.created_at)
        )
    )


def lease_items(session: Session, lease_id: UUID) -> list[LeaseItem]:
    """What the lease charges every month besides the rent, in the order the bill shows it."""
    return list(
        session.scalars(
            select(LeaseItem).where(LeaseItem.lease_id == lease_id).order_by(LeaseItem.position)
        )
    )


def _pdf_path(bill: Bill) -> str:
    return f"{bill.owner_id}/bills/{bill.id}.pdf"


def _document(session: Session, storage: Storage, bill: Bill, voided: bool = False) -> BillDocument:
    """What the PDF shows, as it is right now. Called when issuing and when voiding."""
    signature = None
    if bill.signature_path:
        try:
            signature = storage.download(bill.signature_path)
        except StorageError:
            # A bill is not issued without the signature it should carry. A voided one is
            # no longer owed: its PDF only has to say so.
            if not voided:
                raise
            logger.exception("could not fetch the signature of a voided bill: %s", bill.id)
    owner = session.get_one(Owner, bill.owner_id)
    lease = session.get_one(Lease, bill.lease_id)
    tenant = session.get_one(Tenant, lease.tenant_id)
    unit = session.get_one(Unit, lease.unit_id)
    # A monthly bill says its month and its unit under the rent, its first line. A manual
    # one has no line to say it under, so the unit goes in the heading.
    of_the_rent = f"{format_month(bill.period)} · {unit.name}" if bill.period else None
    return BillDocument(
        number=bill.number,
        issue_date=bill.issue_date,
        due_date=bill.due_date,
        owner_name=owner.name,
        owner_document_type=owner.document_type,
        owner_document=owner.document_number,
        tenant_name=tenant.name,
        tenant_document_type=tenant.document_type,
        tenant_document=tenant.document_number,
        lines=[
            BillLine(item.description, item.amount, None if index else of_the_rent)
            for index, item in enumerate(_items(session, bill.id))
        ],
        total=bill.total,
        payment_details=bill.payment_details,
        voided=voided,
        unit_name=None if bill.period else unit.name,
        signature=signature,
    )


def _owes_deposit(session: Session, lease: Lease) -> bool:
    """Whether the monthly bill about to be issued is the one that charges the deposit.

    It is the first one of the lease. A voided one does not count, so the bill that
    replaces it charges the deposit again.
    """
    if not (lease.charge_deposit and lease.deposit):
        return False
    return not session.scalar(
        select(
            exists().where(
                Bill.lease_id == lease.id, Bill.origin == "monthly", Bill.status != "voided"
            )
        )
    )


def _issue(
    session: Session,
    storage: Storage,
    today: date,
    lease: Lease,
    *,
    origin: str,
    period: date | None,
    due_date: date,
    charges: list[tuple[str, int]],
    payment_details: str | None = None,
) -> Bill:
    """Creates a bill with the owner's next number and its PDF, all or nothing.

    `charges` are its items, description and amount, in the order the bill shows them.
    The total is their sum.
    """
    # The lock on the owner's row makes issuing one at a time per owner: whoever comes
    # next waits here and reads the number this transaction leaves. If anything below
    # fails, the whole transaction rolls back and the number is not used up.
    owner = session.execute(
        select(Owner)
        .where(Owner.id == lease.owner_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).scalar_one()
    number = owner.next_number
    owner.next_number = number + 1

    # Decided here, under the lock, so two requests at once cannot both be the first bill.
    if origin == "monthly" and _owes_deposit(session, lease):
        charges = [*charges, (DEPOSIT, lease.deposit)]

    bill = Bill(
        # Made here, not by the database, because the path of the PDF carries it.
        id=uuid4(),
        owner_id=lease.owner_id,
        lease_id=lease.id,
        number=number,
        origin=origin,
        period=period,
        issue_date=today,
        due_date=due_date,
        total=sum(charged for _, charged in charges),
        # The bill's own, else the lease's, else the owner's. Kept here, so changing any
        # of them later does not touch this bill.
        payment_details=payment_details or lease.payment_details or owner.payment_details,
        # The owner's signature as it is now, kept for the same reason.
        signature_path=owner.signature_path,
        # Already past its due date: the same thing the daily task would do tomorrow.
        status="overdue" if due_date < today else "pending",
    )
    bill.pdf_path = _pdf_path(bill)
    session.add(bill)
    try:
        session.flush()
    except IntegrityError as error:
        # The unique index decides, so two requests at once cannot both win.
        if getattr(error.orig.diag, "constraint_name", None) == ONE_MONTHLY_PER_PERIOD:
            raise conflict(
                "Este contrato ya tiene la cuenta de este mes. Anúlala antes de generar otra.",
                "bill_already_exists",
            ) from error
        raise
    session.add_all(
        BillItem(
            owner_id=bill.owner_id,
            bill_id=bill.id,
            description=charge,
            amount=charged,
            position=position,
        )
        for position, (charge, charged) in enumerate(charges)
    )
    session.flush()

    try:
        storage.upload(
            bill.pdf_path, render_bill(_document(session, storage, bill)), "application/pdf"
        )
    except StorageError as error:
        raise storage_unavailable() from error
    except SignatureError as error:
        # Better no bill than one kept as signed that is not. Everything above rolls back.
        raise conflict(
            "No pudimos poner tu firma en la cuenta. Súbela de nuevo en Ajustes.",
            "signature_unreadable",
        ) from error
    return bill


def issue_monthly_bill(session: Session, storage: Storage, today: date, lease_id: UUID) -> Bill:
    """The bill of the current month for a lease. The daily task issues the same one."""
    lease = _active_lease(session, lease_id)
    period = today.replace(day=1)
    return _issue(
        session,
        storage,
        today,
        lease,
        origin="monthly",
        period=period,
        # The due day goes from 1 to 28, so it exists in every month.
        due_date=period.replace(day=lease.due_day),
        # The rent and the items of the lease as they are now; changing them later does
        # not touch this bill. The first bill of the lease may also charge its deposit.
        charges=[
            (RENT, lease.rent),
            *((item.description, item.amount) for item in lease_items(session, lease.id)),
        ],
    )


def issue_manual_bill(session: Session, storage: Storage, today: date, data: BillCreate) -> Bill:
    lease = _active_lease(session, data.lease_id)
    return _issue(
        session,
        storage,
        today,
        lease,
        origin="manual",
        period=None,
        due_date=data.due_date,
        charges=[(item.description, item.amount) for item in data.items],
        payment_details=data.payment_details,
    )


# Reads

# The month a bill belongs to: its period, or the month it is due when it is manual.
BILL_MONTH = func.coalesce(Bill.period, func.date_trunc("month", Bill.due_date))


# What has been paid on each bill. The balance is never stored: it is the total minus this.
PAID = (
    select(func.coalesce(func.sum(Payment.amount), 0))
    .where(Payment.bill_id == Bill.id)
    .correlate(Bill)
    .scalar_subquery()
)


def _last_payment(column: object) -> object:
    return (
        select(column)
        .where(Payment.bill_id == Bill.id)
        .order_by(Payment.payment_date.desc(), Payment.created_at.desc())
        .limit(1)
        .correlate(Bill)
        .scalar_subquery()
    )


def paid_amount(session: Session, bill_id: UUID) -> int:
    return session.scalar(
        select(func.coalesce(func.sum(Payment.amount), 0)).where(Payment.bill_id == bill_id)
    )


def bill_summaries(session: Session, query: Select) -> list[BillSummary]:
    """The bills a `select(Bill)` finds, each with who owes it and what is left to pay."""
    rows = session.execute(
        query.add_columns(
            Unit.id,
            Unit.name,
            Tenant.name,
            PAID,
            _last_payment(Payment.payment_date),
            _last_payment(Payment.method),
        )
        .join(Lease, Lease.id == Bill.lease_id)
        .join(Unit, Unit.id == Lease.unit_id)
        .join(Tenant, Tenant.id == Lease.tenant_id)
    )
    return [
        BillSummary(
            id=bill.id,
            number=bill.number,
            origin=bill.origin,
            period=bill.period,
            issue_date=bill.issue_date,
            due_date=bill.due_date,
            total=bill.total,
            balance=bill.total - paid,
            status=bill.status,
            last_payment_date=last_date,
            last_payment_method=last_method,
            lease_id=bill.lease_id,
            unit_id=unit_id,
            unit_name=unit_name,
            tenant_name=tenant_name,
        )
        for bill, unit_id, unit_name, tenant_name, paid, last_date, last_method in rows
    ]


def list_bills(
    session: Session,
    unit_id: UUID | None = None,
    status: BillStatusFilter | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
) -> list[BillSummary]:
    query = select(Bill).order_by(BILL_MONTH.desc(), Bill.number.desc())
    if unit_id is not None:
        query = query.where(Lease.unit_id == unit_id)
    if status is not None:
        query = query.where(Bill.status.in_(STATUS_FILTERS[status]))
    else:
        # Provisional: voided bills stay out of the way unless asked for.
        query = query.where(Bill.status != "voided")
    belongs_to = func.coalesce(Bill.period, Bill.due_date)
    if from_date is not None:
        query = query.where(belongs_to >= from_date)
    if to_date is not None:
        query = query.where(belongs_to <= to_date)
    return bill_summaries(session, query)


def recent_bills(session: Session, lease_id: UUID) -> list[BillSummary]:
    """The latest bills of a lease, voided ones too: the lease screen shows its history."""
    query = (
        select(Bill)
        .where(Bill.lease_id == lease_id)
        .order_by(Bill.number.desc())
        .limit(RECENT_BILLS)
    )
    return bill_summaries(session, query)


def get_bill(session: Session, bill_id: UUID) -> Bill:
    bill = session.get(Bill, bill_id)
    if bill is None:
        raise not_found()
    return bill


def bill_response(session: Session, bill: Bill) -> BillResponse:
    summary = bill_summaries(session, select(Bill).where(Bill.id == bill.id))[0]
    owner = session.get_one(Owner, bill.owner_id)
    lease = session.get_one(Lease, bill.lease_id)
    tenant = session.get_one(Tenant, lease.tenant_id)
    unit = session.get_one(Unit, lease.unit_id)
    items = _items(session, bill.id)
    payments = session.scalars(
        select(Payment)
        .where(Payment.bill_id == bill.id)
        .order_by(Payment.payment_date.desc(), Payment.created_at.desc())
    )
    notifications = session.scalars(
        select(Notification)
        .where(Notification.bill_id == bill.id)
        .order_by(Notification.created_at.desc(), Notification.id)
    )
    return BillResponse(
        **summary.model_dump(),
        items=[BillItemResponse(description=i.description, amount=i.amount) for i in items],
        property_name=session.get_one(Property, unit.property_id).name,
        tenant_document_type=tenant.document_type,
        tenant_document_number=tenant.document_number,
        issuer=BillIssuer(
            name=owner.name,
            document_type=owner.document_type,
            document_number=owner.document_number,
            payment_details=bill.payment_details,
        ),
        signed=bill.signature_path is not None,
        created_at=bill.created_at,
        voided_at=bill.voided_at,
        payments=[
            PaymentResponse(
                id=p.id,
                payment_date=p.payment_date,
                amount=p.amount,
                method=p.method,
                has_proof=p.proof_path is not None,
                created_at=p.created_at,
            )
            for p in payments
        ],
        notifications=[
            NotificationResponse(
                id=n.id,
                type=n.type,
                recipient=n.recipient,
                delivery_status=n.delivery_status,
                created_at=n.created_at,
                sent_at=n.sent_at,
            )
            for n in notifications
        ],
    )


def get_pdf_url(session: Session, storage: Storage, bill_id: UUID) -> DocumentUrlResponse:
    bill = get_bill(session, bill_id)
    try:
        url = storage.create_download_url(bill.pdf_path, DOWNLOAD_LINK_SECONDS)
    except StorageError as error:
        raise storage_unavailable() from error
    return DocumentUrlResponse(
        url=url,
        name=f"cuenta-de-cobro-{bill.number:04d}.pdf",
        expires_in=DOWNLOAD_LINK_SECONDS,
    )


# Voiding


def _replace_pdf(storage: Storage, path: str, pdf: bytes) -> None:
    try:
        storage.upload(path, pdf, "application/pdf")
    except StorageError:
        # The bill is voided all the same; its PDF just lacks the mark.
        logger.exception("could not mark the PDF of a voided bill: %s", path)


def void_bill(
    session: Session, storage: Storage, background: BackgroundTasks, bill_id: UUID
) -> BillResponse:
    """Voids a bill nobody has paid. It keeps its number, and its PDF gets marked."""
    bill = get_bill(session, bill_id)
    if bill.status == "voided":
        raise AppError(400, "Esta cuenta ya está anulada.", "bill_already_voided")
    # An overdue bill may have payments too, so the status alone does not say.
    has_payments = session.scalar(select(exists().where(Payment.bill_id == bill.id)))
    if has_payments or bill.status in ("partial", "paid"):
        raise AppError(
            400,
            "Esta cuenta tiene pagos y no se puede anular.",
            "bill_has_payments",
        )
    bill.status = "voided"
    bill.voided_at = func.now()
    session.flush()
    session.refresh(bill)

    # After the response, which is after the commit: if saving fails, the bill is still
    # owed and its PDF must not say otherwise.
    document = _document(session, storage, bill, voided=True)
    try:
        pdf = render_bill(document)
    except SignatureError:
        # A voided bill is no longer owed: its PDF only has to say so.
        logger.exception("could not draw the signature of a voided bill: %s", bill.id)
        pdf = render_bill(replace(document, signature=None))
    background.add_task(_replace_pdf, storage, bill.pdf_path, pdf)
    return bill_response(session, bill)
