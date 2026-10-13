from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    ForeignKey,
    ForeignKeyConstraint,
    SmallInteger,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class LeaseItem(Base):
    """Something the lease charges every month besides the rent, like the building fee."""

    __tablename__ = "lease_items"
    __table_args__ = (
        ForeignKeyConstraint(
            ["owner_id", "lease_id"], ["leases.owner_id", "leases.id"], name="lease_items_lease_fk"
        ),
        CheckConstraint("amount > 0", name="lease_items_amount_check"),
        CheckConstraint("position >= 0", name="lease_items_position_check"),
        UniqueConstraint("lease_id", "position", name="lease_items_lease_id_position_key"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=func.gen_random_uuid())
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("owners.id", name="lease_items_owner_fk"))
    lease_id: Mapped[UUID]
    description: Mapped[str] = mapped_column(Text)
    # Money is whole pesos.
    amount: Mapped[int] = mapped_column(BigInteger)
    # Its place in the bill, from 0, after the rent.
    position: Mapped[int] = mapped_column(SmallInteger)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
    # Kept up to date by the `set_updated_at` trigger.
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
