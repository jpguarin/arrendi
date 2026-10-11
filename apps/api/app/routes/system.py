import base64
import hashlib
import hmac
import json
import time
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request
from pydantic import BaseModel
from sqlalchemy import Engine, update
from sqlalchemy.orm import Session

from app.config import get_settings
from app.dependencies import FileStorage, Mailer, Today, get_tasks_db_engine
from app.errors import ErrorResponse, unauthorized
from app.models import Notification
from app.tasks.daily import run_daily

router = APIRouter()

# These routes are not called by an owner: they have no token and no owner's transaction.

# Under the shortest limit a Vercel function can have (60 s), to answer before it is cut
# off. What does not fit is left for the next run.
DAILY_SECONDS = 50


class DailyResponse(BaseModel):
    bills_generated: int
    bills_marked_overdue: int
    emails_sent: int
    errors: int
    finished: bool


def check_cron_secret(authorization: Annotated[str | None, Header()] = None) -> None:
    """Vercel calls its Cron Jobs with `Authorization: Bearer <CRON_SECRET>`."""
    secret = get_settings().cron_secret
    # Without a secret configured nobody gets in, rather than everybody.
    if not secret or not hmac.compare_digest(
        (authorization or "").encode(), f"Bearer {secret}".encode()
    ):
        raise unauthorized()


@router.get(
    "/cron/daily",
    dependencies=[Depends(check_cron_secret)],
    responses={401: {"model": ErrorResponse}},
)
def daily(
    engine: Annotated[Engine, Depends(get_tasks_db_engine)],
    mailer: Mailer,
    storage: FileStorage,
    today: Today,
) -> DailyResponse:
    """The daily task. Safe to call more than once a day."""
    result = run_daily(engine, mailer, storage, today, time.monotonic() + DAILY_SECONDS)
    return DailyResponse(
        bills_generated=result.bills_generated,
        bills_marked_overdue=result.bills_marked_overdue,
        emails_sent=result.emails_sent,
        errors=result.errors,
        finished=result.finished,
    )


# Notices from the email provider. Resend signs them the way Svix does: an HMAC-SHA256 of
# "id.timestamp.body" with the secret, in a header that may carry several signatures.

WEBHOOK_TOLERANCE_SECONDS = 300
SECRET_PREFIX = "whsec_"


class WebhookResponse(BaseModel):
    ok: bool


def is_signed_by_provider(
    secret: str, message_id: str, timestamp: str, signatures: str, body: bytes, now: float
) -> bool:
    try:
        key = base64.b64decode(secret.removeprefix(SECRET_PREFIX))
        sent_at = int(timestamp)
    except ValueError:
        return False
    # An old notice replayed later is not accepted.
    if abs(now - sent_at) > WEBHOOK_TOLERANCE_SECONDS:
        return False
    signed = message_id.encode() + b"." + timestamp.encode() + b"." + body
    expected = base64.b64encode(hmac.new(key, signed, hashlib.sha256).digest()).decode()
    return any(
        version == "v1" and hmac.compare_digest(signature, expected)
        for version, _, signature in (item.partition(",") for item in signatures.split())
    )


async def signed_body(
    request: Request,
    svix_id: Annotated[str | None, Header()] = None,
    svix_timestamp: Annotated[str | None, Header()] = None,
    svix_signature: Annotated[str | None, Header()] = None,
) -> bytes:
    """The body exactly as it arrived, once its signature checks out."""
    secret = get_settings().email_webhook_secret
    body = await request.body()
    if not (
        secret
        and svix_id
        and svix_timestamp
        and svix_signature
        and is_signed_by_provider(
            secret, svix_id, svix_timestamp, svix_signature, body, time.time()
        )
    ):
        raise unauthorized()
    return body


@router.post("/webhooks/email", responses={401: {"model": ErrorResponse}})
def email_webhook(
    body: Annotated[bytes, Depends(signed_body)],
    engine: Annotated[Engine, Depends(get_tasks_db_engine)],
) -> WebhookResponse:
    """A bounce leaves its notification as `bounced`. Everything else is ignored."""
    try:
        event = json.loads(body)
        kind, email_id = event["type"], event["data"]["email_id"]
    except (ValueError, KeyError, TypeError):
        # Signed but not something we understand: nothing to do, and no reason to retry.
        return WebhookResponse(ok=True)
    if kind == "email.bounced" and isinstance(email_id, str):
        with Session(engine) as session, session.begin():
            session.execute(
                update(Notification)
                .where(
                    Notification.provider_id == email_id,
                    Notification.delivery_status == "sent",
                )
                .values(delivery_status="bounced")
            )
    return WebhookResponse(ok=True)
