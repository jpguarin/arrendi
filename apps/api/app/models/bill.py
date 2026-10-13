from datetime import date, datetime
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Bill(Base):
    __tablename__ = "bills"
    __table_args__ = (
        UniqueConstraint("owner_id", "id", name="bills_owner_id_id_key"),
        # The number: one sequence per owner.
        UniqueConstraint("owner_id", "number", name="bills_owner_id_number_key"),
        ForeignKeyConstraint(
            ["owner_id", "lease_id"], ["leases.owner_id", "leases.id"], name="bills_lease_fk"
        ),
        CheckConstraint("number > 0", name="bills_number_check"),
        CheckConstraint("origin in ('monthly', 'manual')", name="bills_origin_check"),
        CheckConstraint(
            "(origin = 'monthly') = (period is not null) "
            "and (period is null or extract(day from period) = 1)",
            name="bills_period_check",
        ),
        CheckConstraint("total > 0", name="bills_total_check"),
        CheckConstraint(
            "status in ('pending', 'partial', 'paid', 'overdue', 'voided')",
            name="bills_status_check",
        ),
        CheckConstraint(
            "(status = 'voided') = (voided_at is not null)", name="bills_voided_at_check"
        ),
        # One monthly bill per lease and period, unless it was voided.
        Index(
            "bills_one_monthly_per_period",
            "lease_id",
            "period",
            unique=True,
            postgresql_where=text("origin = 'monthly' and status <> 'voided'"),
        ),
        CheckConstraint(
            "(late_fee_amount is null) = (late_fee_deadline is null) "
            "and (late_fee_amount is null or late_fee_amount > 0) "
            "and (late_fee_waived_at is null or late_fee_amount is not null)",
            name="bills_late_fee_check",
        ),
        Index("bills_status_due_date_idx", "status", "due_date"),
        Index("bills_lease_id_idx", "lease_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=func.gen_random_uuid())
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("owners.id", name="bills_owner_fk"))
    lease_id: Mapped[UUID]
    number: Mapped[int]
    origin: Mapped[str] = mapped_column(Text)
    # First day of the month being billed; null in manual bills.
    period: Mapped[date | None]
    issue_date: Mapped[date]
    due_date: Mapped[date]
    # Money is whole pesos.
    total: Mapped[int] = mapped_column(BigInteger)
    status: Mapped[str] = mapped_column(Text, server_default=text("'pending'"))
    # How to pay, as it was when the bill was issued: its own, the lease's or the owner's.
    payment_details: Mapped[str | None] = mapped_column(Text)
    # What paying this bill late costs, and the last day to pay it in time, as they were
    # when it was issued. Null if the lease had no late fee then: it never owes one. The
    # fee is not added here: a later bill charges it as an item.
    late_fee_amount: Mapped[int | None] = mapped_column(BigInteger)
    late_fee_deadline: Mapped[date | None]
    # When the owner decided not to charge it.
    late_fee_waived_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    # The owner's signature as it was when the bill was issued; null if they had none.
    signature_path: Mapped[str | None] = mapped_column(Text)
    # Path in the private storage bucket.
    pdf_path: Mapped[str] = mapped_column(Text)
    voided_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
    # Kept up to date by the `set_updated_at` trigger.
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
