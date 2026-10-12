from datetime import date, datetime
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (
        ForeignKeyConstraint(
            ["owner_id", "bill_id"], ["bills.owner_id", "bills.id"], name="payments_bill_fk"
        ),
        CheckConstraint("amount > 0", name="payments_amount_check"),
        CheckConstraint(
            "method in ('transfer', 'nequi', 'cash', 'other')", name="payments_method_check"
        ),
        Index("payments_bill_id_idx", "bill_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=func.gen_random_uuid())
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("owners.id", name="payments_owner_fk"))
    bill_id: Mapped[UUID]
    payment_date: Mapped[date]
    # Money is whole pesos.
    amount: Mapped[int] = mapped_column(BigInteger)
    method: Mapped[str] = mapped_column(Text)
    # Path of the proof of payment in the private storage bucket.
    proof_path: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
    # Kept up to date by the `set_updated_at` trigger.
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
