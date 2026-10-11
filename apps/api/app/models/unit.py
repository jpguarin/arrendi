from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Unit(Base):
    __tablename__ = "units"
    __table_args__ = (
        UniqueConstraint("owner_id", "id", name="units_owner_id_id_key"),
        ForeignKeyConstraint(
            ["owner_id", "property_id"],
            ["properties.owner_id", "properties.id"],
            name="units_property_fk",
        ),
        CheckConstraint("use in ('residential', 'commercial')", name="units_use_check"),
        Index("units_property_id_idx", "property_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=func.gen_random_uuid())
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("owners.id", name="units_owner_fk"))
    property_id: Mapped[UUID]
    name: Mapped[str] = mapped_column(Text)
    use: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
    # Kept up to date by the `set_updated_at` trigger.
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
