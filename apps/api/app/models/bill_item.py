from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    SmallInteger,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class BillItem(Base):
    __tablename__ = "bill_items"
    __table_args__ = (
        ForeignKeyConstraint(
            ["owner_id", "bill_id"], ["bills.owner_id", "bills.id"], name="bill_items_bill_fk"
        ),
        ForeignKeyConstraint(
            ["owner_id", "late_fee_of_bill_id"],
            ["bills.owner_id", "bills.id"],
            name="bill_items_late_fee_fk",
        ),
        CheckConstraint("amount > 0", name="bill_items_amount_check"),
        Index("bill_items_bill_id_idx", "bill_id"),
        Index(
            "bill_items_late_fee_of_bill_id_idx",
            "late_fee_of_bill_id",
            postgresql_where=text("late_fee_of_bill_id is not null"),
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=func.gen_random_uuid())
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("owners.id", name="bill_items_owner_fk"))
    bill_id: Mapped[UUID]
    description: Mapped[str] = mapped_column(Text)
    # Money is whole pesos.
    amount: Mapped[int] = mapped_column(BigInteger)
    # The late bill this item is the late fee of; null in every other item.
    late_fee_of_bill_id: Mapped[UUID | None]
    # Its place in the bill, from 0: the items of a bill are created in the same instant.
    position: Mapped[int] = mapped_column(SmallInteger, server_default=text("0"))
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
    # Kept up to date by the `set_updated_at` trigger.
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
