from datetime import datetime
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


class BillItem(Base):
    __tablename__ = "bill_items"
    __table_args__ = (
        ForeignKeyConstraint(
            ["owner_id", "bill_id"], ["bills.owner_id", "bills.id"], name="bill_items_bill_fk"
        ),
        CheckConstraint("amount > 0", name="bill_items_amount_check"),
        Index("bill_items_bill_id_idx", "bill_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=func.gen_random_uuid())
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("owners.id", name="bill_items_owner_fk"))
    bill_id: Mapped[UUID]
    description: Mapped[str] = mapped_column(Text)
    # Money is whole pesos.
    amount: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
    # Kept up to date by the `set_updated_at` trigger.
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
