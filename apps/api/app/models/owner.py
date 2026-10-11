from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, SmallInteger, Text, func, text
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Owner(Base):
    __tablename__ = "owners"
    __table_args__ = (
        CheckConstraint("send_day between 1 and 28", name="owners_send_day_check"),
        CheckConstraint("document_type in ('cc', 'nit')", name="owners_document_type_check"),
    )

    # Same id as the user in Supabase Auth.
    id: Mapped[UUID] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(Text)
    # What `document_number` is: a cédula or a NIT.
    document_type: Mapped[str] = mapped_column(Text, server_default=text("'cc'"))
    document_number: Mapped[str | None] = mapped_column(Text)
    email: Mapped[str] = mapped_column(Text)
    payment_details: Mapped[str | None] = mapped_column(Text)
    send_day: Mapped[int] = mapped_column(SmallInteger, server_default=text("1"))
    reminder_1: Mapped[bool] = mapped_column(server_default=text("true"))
    reminder_2: Mapped[bool] = mapped_column(server_default=text("true"))
    email_copy: Mapped[bool] = mapped_column(server_default=text("false"))
    next_number: Mapped[int] = mapped_column(server_default=text("1"))
    data_consent_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
    # Kept up to date by the `set_updated_at` trigger.
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
