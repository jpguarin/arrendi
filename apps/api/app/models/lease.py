from datetime import date, datetime
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    SmallInteger,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Lease(Base):
    __tablename__ = "leases"
    __table_args__ = (
        UniqueConstraint("owner_id", "id", name="leases_owner_id_id_key"),
        ForeignKeyConstraint(
            ["owner_id", "unit_id"], ["units.owner_id", "units.id"], name="leases_unit_fk"
        ),
        ForeignKeyConstraint(
            ["owner_id", "tenant_id"], ["tenants.owner_id", "tenants.id"], name="leases_tenant_fk"
        ),
        CheckConstraint("rent > 0", name="leases_rent_check"),
        CheckConstraint("due_day between 1 and 28", name="leases_due_day_check"),
        CheckConstraint("end_date is null or end_date > start_date", name="leases_dates_check"),
        CheckConstraint("deposit is null or deposit >= 0", name="leases_deposit_check"),
        CheckConstraint("status in ('active', 'ended')", name="leases_status_check"),
        # A unit has at most one active lease.
        Index(
            "leases_one_active_per_unit",
            "unit_id",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
        Index("leases_tenant_id_idx", "tenant_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=func.gen_random_uuid())
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("owners.id", name="leases_owner_fk"))
    unit_id: Mapped[UUID]
    tenant_id: Mapped[UUID]
    # Money is whole pesos.
    rent: Mapped[int] = mapped_column(BigInteger)
    due_day: Mapped[int] = mapped_column(SmallInteger)
    start_date: Mapped[date]
    end_date: Mapped[date | None]
    deposit: Mapped[int | None] = mapped_column(BigInteger)
    status: Mapped[str] = mapped_column(Text, server_default=text("'active'"))
    auto_send: Mapped[bool] = mapped_column(server_default=text("true"))
    # How to pay the bills of this lease; null means the owner's.
    payment_details: Mapped[str | None] = mapped_column(Text)
    # Path in the private storage bucket.
    document_path: Mapped[str | None] = mapped_column(Text)
    document_uploaded_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
    # Kept up to date by the `set_updated_at` trigger.
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
