from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Text, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Tenant(Base):
    __tablename__ = "tenants"
    __table_args__ = (
        UniqueConstraint("owner_id", "id", name="tenants_owner_id_id_key"),
        CheckConstraint("document_type in ('cc', 'nit')", name="tenants_document_type_check"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=func.gen_random_uuid())
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("owners.id", name="tenants_owner_fk"))
    name: Mapped[str] = mapped_column(Text)
    # What `document_number` is: a cédula or a NIT.
    document_type: Mapped[str] = mapped_column(Text, server_default=text("'cc'"))
    document_number: Mapped[str | None] = mapped_column(Text)
    # Required: it is the channel the bills are sent through.
    email: Mapped[str] = mapped_column(Text)
    phone: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
    # Kept up to date by the `set_updated_at` trigger.
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
