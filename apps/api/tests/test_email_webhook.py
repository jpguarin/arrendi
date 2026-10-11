"""Bounce notices from the email provider."""

import base64
import hashlib
import hmac
import json
import time
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

from app.config import get_settings
from app.dependencies import get_tasks_db_engine
from app.main import app
from tests.conftest import Tree
from tests.test_bill_tables import insert_bill

KEY = b"a-signing-key-for-the-tests"
SECRET = "whsec_" + base64.b64encode(KEY).decode()
BOUNCE = {"type": "email.bounced", "data": {"email_id": "email-abc"}}


def signed(payload: object, key: bytes = KEY, at: float | None = None) -> tuple[bytes, dict]:
    body = json.dumps(payload).encode()
    timestamp = str(int(at if at is not None else time.time()))
    content = b"msg_1." + timestamp.encode() + b"." + body
    signature = base64.b64encode(hmac.new(key, content, hashlib.sha256).digest()).decode()
    return body, {
        "svix-id": "msg_1",
        "svix-timestamp": timestamp,
        # The header may carry signatures of other versions or older secrets.
        "svix-signature": f"v1,bm90LXRoaXMtb25l v1,{signature}",
        "content-type": "application/json",
    }


@pytest.fixture
def webhook(api: TestClient, tasks_engine: Engine, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(get_settings(), "email_webhook_secret", SECRET)
    app.dependency_overrides[get_tasks_db_engine] = lambda: tasks_engine
    return api


@pytest.fixture
def sent(admin_engine: Engine, two_owners: tuple[UUID, UUID], trees: tuple[Tree, Tree]) -> None:
    """Ana's bill was emailed, and the provider knows that email as `email-abc`."""
    with admin_engine.begin() as connection:
        bill_id = insert_bill(connection, two_owners[0], trees[0].lease_id)
        connection.execute(
            text(
                "insert into notifications (owner_id, bill_id, type, recipient, "
                "delivery_status, provider_id, sent_at) values (:owner, :bill, 'bill', "
                "'carlos@example.com', 'sent', 'email-abc', now())"
            ),
            {"owner": two_owners[0], "bill": bill_id},
        )


def status(admin_engine: Engine) -> str:
    with admin_engine.connect() as connection:
        return connection.execute(
            text("select delivery_status from notifications where provider_id = 'email-abc'")
        ).scalar_one()


def test_bounce_marks_the_notification(webhook: TestClient, sent, admin_engine: Engine) -> None:
    body, headers = signed(BOUNCE)

    response = webhook.post("/api/webhooks/email", content=body, headers=headers)

    assert response.status_code == 200
    assert status(admin_engine) == "bounced"
    # The provider may deliver the same notice twice.
    assert webhook.post("/api/webhooks/email", content=body, headers=headers).status_code == 200
    assert status(admin_engine) == "bounced"


def test_other_events_and_unknown_emails_change_nothing(
    webhook: TestClient, sent, admin_engine: Engine
) -> None:
    for payload in (
        {"type": "email.delivered", "data": {"email_id": "email-abc"}},
        {"type": "email.bounced", "data": {"email_id": "someone-elses"}},
        {"type": "email.bounced"},
        ["not", "an", "event"],
    ):
        body, headers = signed(payload)
        assert webhook.post("/api/webhooks/email", content=body, headers=headers).status_code == 200

    assert status(admin_engine) == "sent"


def test_notice_must_be_signed_with_our_secret(
    webhook: TestClient, sent, admin_engine: Engine
) -> None:
    body, headers = signed(BOUNCE)
    _, forged = signed(BOUNCE, key=b"someone-elses-key")
    _, old = signed(BOUNCE, at=time.time() - 3600)
    tampered = body.replace(b"email-abc", b"email-xyz")

    attempts = [
        (body, {"content-type": "application/json"}),
        (body, forged),
        (body, old),
        (tampered, headers),
        (body, headers | {"svix-timestamp": "not-a-number"}),
        (body, headers | {"svix-signature": "v1"}),
    ]
    for content, attempt_headers in attempts:
        response = webhook.post("/api/webhooks/email", content=content, headers=attempt_headers)
        assert response.status_code == 401

    assert status(admin_engine) == "sent"


def test_without_a_secret_configured_every_notice_is_refused(
    webhook: TestClient, sent, admin_engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(get_settings(), "email_webhook_secret", "")
    body, headers = signed(BOUNCE, key=b"")

    assert webhook.post("/api/webhooks/email", content=body, headers=headers).status_code == 401
    assert status(admin_engine) == "sent"
