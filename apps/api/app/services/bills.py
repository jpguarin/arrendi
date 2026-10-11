import logging
from datetime import date
from uuid import UUID, uuid4

from fastapi import BackgroundTasks
from sqlalchemy import Select, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.errors import AppError, conflict, not_found, storage_unavailable
from app.models import Bill, BillItem, Lease, Notification, Owner, Property, Tenant, Unit
from app.pdf.bill import BillDocument, BillLine, render_bill
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
from app.storage import Storage, StorageError

logger = logging.getLogger(__name__)

# Every query here runs inside the owner's transaction: row security already limits it to
# their rows, so another owner's id simply finds nothing.

ONE_MONTHLY_PER_PERIOD = "bills_one_monthly_per_period"
RENT = "Canon de arrendamiento"
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


def _pdf_path(bill: Bill) -> str:
    return f"{bill.owner_id}/bills/{bill.id}.pdf"


def _document(session: Session, bill: Bill, voided: bool = False) -> BillDocument:
    """What the PDF shows, as it is right now. Called when issuing and when voiding."""
    owner = session.get_one(Owner, bill.owner_id)
    lease = session.get_one(Lease, bill.lease_id)
    tenant = session.get_one(Tenant, lease.tenant_id)
    unit = session.get_one(Unit, lease.unit_id)
    detail = f"{format_month(bill.period)} · {unit.name}" if bill.period else unit.name
    items = session.scalars(
        select(BillItem).where(BillItem.bill_id == bill.id).order_by(BillItem.created_at)
    )
    return BillDocument(
        number=bill.number,
        issue_date=bill.issue_date,
        due_date=bill.due_date,
        owner_name=owner.name,
        owner_document_type=owner.document_type,
        owner_document=owner.document_number,
        tenant_name=tenant.name,
        tenant_document=tenant.document_number,
        lines=[BillLine(item.description, detail, item.amount) for item in items],
        total=bill.total,
        payment_details=owner.payment_details,
        voided=voided,
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
    description: str,
    amount: int,
) -> Bill:
    """Creates a bill with the owner's next number and its PDF, all or nothing."""
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
        total=amount,
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
    session.add(
        BillItem(owner_id=bill.owner_id, bill_id=bill.id, description=description, amount=amount)
    )
    session.flush()

    try:
        storage.upload(bill.pdf_path, render_bill(_document(session, bill)), "application/pdf")
    except StorageError as error:
        raise storage_unavailable() from error
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
        description=RENT,
        # The rent as it is now; changing it later does not touch this bill.
        amount=lease.rent,
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
        description=data.description,
        amount=data.amount,
    )


# Reads

# The month a bill belongs to: its period, or the month it is due when it is manual.
_MONTH = func.coalesce(Bill.period, func.date_trunc("month", Bill.due_date))


def _summaries(session: Session, query: Select) -> list[BillSummary]:
    rows = session.execute(
        query.add_columns(Unit.id, Unit.name, Tenant.name)
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
            # Payments arrive in stage 5; until then nothing has been paid.
            balance=bill.total,
            status=bill.status,
            lease_id=bill.lease_id,
            unit_id=unit_id,
            unit_name=unit_name,
            tenant_name=tenant_name,
        )
        for bill, unit_id, unit_name, tenant_name in rows
    ]


def list_bills(
    session: Session,
    unit_id: UUID | None = None,
    status: BillStatusFilter | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
) -> list[BillSummary]:
    query = select(Bill).order_by(_MONTH.desc(), Bill.number.desc())
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
    return _summaries(session, query)


def recent_bills(session: Session, lease_id: UUID) -> list[BillSummary]:
    """The latest bills of a lease, voided ones too: the lease screen shows its history."""
    query = (
        select(Bill)
        .where(Bill.lease_id == lease_id)
        .order_by(Bill.number.desc())
        .limit(RECENT_BILLS)
    )
    return _summaries(session, query)


def get_bill(session: Session, bill_id: UUID) -> Bill:
    bill = session.get(Bill, bill_id)
    if bill is None:
        raise not_found()
    return bill


def bill_response(session: Session, bill: Bill) -> BillResponse:
    summary = _summaries(session, select(Bill).where(Bill.id == bill.id))[0]
    owner = session.get_one(Owner, bill.owner_id)
    lease = session.get_one(Lease, bill.lease_id)
    tenant = session.get_one(Tenant, lease.tenant_id)
    unit = session.get_one(Unit, lease.unit_id)
    items = session.scalars(
        select(BillItem).where(BillItem.bill_id == bill.id).order_by(BillItem.created_at)
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
        tenant_document_number=tenant.document_number,
        issuer=BillIssuer(
            name=owner.name,
            document_type=owner.document_type,
            document_number=owner.document_number,
            payment_details=owner.payment_details,
        ),
        created_at=bill.created_at,
        voided_at=bill.voided_at,
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
    # Until payments have their own table (stage 5), these two statuses are what says
    # that a bill has them.
    if bill.status in ("partial", "paid"):
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
    pdf = render_bill(_document(session, bill, voided=True))
    background.add_task(_replace_pdf, storage, bill.pdf_path, pdf)
    return bill_response(session, bill)
