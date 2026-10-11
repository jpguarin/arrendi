from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

# The emails that go out on their own, once per bill.
AUTOMATIC_TYPES = ("bill", "reminder_1", "reminder_2")


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        ForeignKeyConstraint(
            ["owner_id", "bill_id"], ["bills.owner_id", "bills.id"], name="notifications_bill_fk"
        ),
        CheckConstraint(
            "type in ('bill', 'reminder_1', 'reminder_2', 'receipt', 'manual_reminder', 'resend')",
            name="notifications_type_check",
        ),
        CheckConstraint("channel in ('email')", name="notifications_channel_check"),
        CheckConstraint(
            "delivery_status in ('pending', 'sent', 'bounced', 'failed')",
            name="notifications_delivery_status_check",
        ),
        Index(
            "notifications_one_automatic_per_bill",
            "bill_id",
            "type",
            unique=True,
            postgresql_where=text("type in ('bill', 'reminder_1', 'reminder_2')"),
        ),
        Index("notifications_provider_id_idx", "provider_id"),
        Index("notifications_bill_id_idx", "bill_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=func.gen_random_uuid())
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("owners.id", name="notifications_owner_fk"))
    bill_id: Mapped[UUID]
    type: Mapped[str] = mapped_column(Text)
    channel: Mapped[str] = mapped_column(Text, server_default=text("'email'"))
    # The tenant's address, even when the email was diverted to the test inbox.
    recipient: Mapped[str] = mapped_column(Text)
    # `pending` while the row is set aside and the email has not gone out yet.
    delivery_status: Mapped[str] = mapped_column(Text, server_default=text("'pending'"))
    # The provider's id of the email, to match its bounce notices.
    provider_id: Mapped[str | None] = mapped_column(Text)
    sent_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
    # Kept up to date by the `set_updated_at` trigger.
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
