"""Sending a bill and reminding of it by hand."""

from datetime import date
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

from app.dates import today_in_bogota
from app.main import app
from tests.conftest import FakeEmailSender, FakeStorage, MakeToken, Tree, bearer


@pytest.fixture
def ana(two_owners: tuple[UUID, UUID], make_token: MakeToken) -> dict[str, str]:
    return bearer(make_token(two_owners[0]))


@pytest.fixture
def beto(two_owners: tuple[UUID, UUID], make_token: MakeToken) -> dict[str, str]:
    return bearer(make_token(two_owners[1]))


@pytest.fixture(autouse=True)
def today(storage: FakeStorage, mailer: FakeEmailSender) -> None:
    app.dependency_overrides[today_in_bogota] = lambda: date(2026, 10, 3)


@pytest.fixture
def bill(api: TestClient, ana: dict[str, str], trees: tuple[Tree, Tree]) -> dict:
    return api.post(f"/api/leases/{trees[0].lease_id}/bills", headers=ana).json()


def kinds(body: dict) -> list[tuple[str, str]]:
    return [(n["type"], n["delivery_status"]) for n in body["notifications"]]


def detail(api: TestClient, headers: dict[str, str], bill: dict) -> dict:
    return api.get(f"/api/bills/{bill['id']}", headers=headers).json()


def test_issuing_by_hand_sends_nothing(bill: dict, mailer: FakeEmailSender) -> None:
    # The lease has automatic sending on; only the daily task sends on its own.
    assert bill["notifications"] == []
    assert mailer.sent == []


def test_send_emails_the_bill_with_its_stored_pdf(
    api: TestClient, ana: dict[str, str], bill: dict, mailer: FakeEmailSender, storage: FakeStorage
) -> None:
    response = api.post(f"/api/bills/{bill['id']}/send", headers=ana)

    assert response.status_code == 200
    # The answer comes before the email: the notification is only set aside.
    assert kinds(response.json()) == [("bill", "pending")]
    (message,) = mailer.sent
    assert message.to == "ana@example.com"
    assert message.sender_name == "Ana"
    assert message.reply_to == "ana@example.com"
    assert message.subject == "Cuenta de cobro N.º 0001"
    assert "Canon de arrendamiento · Octubre 2026 · Apto ana" in message.text
    assert "$950.000" in message.text and "Vence el 5 de octubre de 2026" in message.text
    assert message.bcc is None
    (attachment,) = message.attachments
    assert attachment.filename == "cuenta-de-cobro-0001.pdf"
    assert attachment.content == next(iter(storage.objects.values()))
    # Afterwards the notification says it went out.
    (sent,) = detail(api, ana, bill)["notifications"]
    assert (sent["type"], sent["delivery_status"], sent["recipient"]) == (
        "bill",
        "sent",
        "ana@example.com",
    )
    assert sent["sent_at"] is not None


def test_sending_again_is_a_resend(
    api: TestClient, ana: dict[str, str], bill: dict, mailer: FakeEmailSender
) -> None:
    api.post(f"/api/bills/{bill['id']}/send", headers=ana)
    api.post(f"/api/bills/{bill['id']}/send", headers=ana)
    api.post(f"/api/bills/{bill['id']}/send", headers=ana)

    assert sorted(kinds(detail(api, ana, bill))) == [
        ("bill", "sent"),
        ("resend", "sent"),
        ("resend", "sent"),
    ]
    assert [message.subject for message in mailer.sent] == ["Cuenta de cobro N.º 0001"] * 3
    # Each email has its own key, so the provider does not take them for the same one.
    assert len({message.idempotency_key for message in mailer.sent}) == 3


def test_owner_gets_a_copy_when_they_ask_for_it(
    api: TestClient,
    ana: dict[str, str],
    two_owners: tuple[UUID, UUID],
    bill: dict,
    mailer: FakeEmailSender,
    admin_engine: Engine,
) -> None:
    with admin_engine.begin() as connection:
        connection.execute(
            text("update owners set email_copy = true where id = :id"), {"id": two_owners[0]}
        )

    api.post(f"/api/bills/{bill['id']}/send", headers=ana)

    assert mailer.sent[0].bcc == "ana@example.com"


def test_manual_reminder_says_the_balance(
    api: TestClient, ana: dict[str, str], bill: dict, mailer: FakeEmailSender
) -> None:
    response = api.post(f"/api/bills/{bill['id']}/remind", headers=ana)

    assert response.status_code == 200
    (message,) = mailer.sent
    assert message.subject == "Recordatorio de pago: cuenta de cobro N.º 0001"
    assert "Saldo pendiente: $950.000" in message.text
    assert len(message.attachments) == 1
    assert kinds(detail(api, ana, bill)) == [("manual_reminder", "sent")]


def test_provider_failure_leaves_the_notification_failed(
    api: TestClient, ana: dict[str, str], bill: dict, mailer: FakeEmailSender
) -> None:
    mailer.failing = True

    response = api.post(f"/api/bills/{bill['id']}/send", headers=ana)

    assert response.status_code == 200
    assert kinds(detail(api, ana, bill)) == [("bill", "failed")]
    # Trying again by hand works once the provider is back.
    mailer.failing = False
    api.post(f"/api/bills/{bill['id']}/send", headers=ana)
    assert sorted(kinds(detail(api, ana, bill))) == [("bill", "failed"), ("resend", "sent")]


def test_missing_pdf_leaves_the_notification_failed(
    api: TestClient, ana: dict[str, str], bill: dict, mailer: FakeEmailSender, storage: FakeStorage
) -> None:
    storage.objects.clear()

    api.post(f"/api/bills/{bill['id']}/send", headers=ana)

    assert mailer.sent == []
    assert kinds(detail(api, ana, bill)) == [("bill", "failed")]


def test_voided_bill_is_not_sent_or_reminded(
    api: TestClient, ana: dict[str, str], bill: dict, mailer: FakeEmailSender
) -> None:
    api.post(f"/api/bills/{bill['id']}/void", headers=ana)

    for action in ("send", "remind"):
        response = api.post(f"/api/bills/{bill['id']}/{action}", headers=ana)
        assert response.status_code == 400
        assert response.json()["code"] == "bill_voided"
    assert mailer.sent == []
    assert detail(api, ana, bill)["notifications"] == []


def test_paid_bill_has_nothing_to_remind(
    api: TestClient, ana: dict[str, str], bill: dict, mailer: FakeEmailSender, admin_engine: Engine
) -> None:
    with admin_engine.begin() as connection:
        connection.execute(
            text("update bills set status = 'paid' where id = :id"), {"id": bill["id"]}
        )

    response = api.post(f"/api/bills/{bill['id']}/remind", headers=ana)

    assert response.status_code == 400
    assert response.json()["code"] == "bill_has_no_balance"
    assert mailer.sent == []


def test_owner_cannot_email_another_owners_bill(
    api: TestClient, ana: dict[str, str], beto: dict[str, str], bill: dict, mailer: FakeEmailSender
) -> None:
    for action in ("send", "remind"):
        assert api.post(f"/api/bills/{bill['id']}/{action}", headers=beto).status_code == 404
        assert api.post(f"/api/bills/{bill['id']}/{action}").status_code == 401

    assert mailer.sent == []
    assert detail(api, ana, bill)["notifications"] == []
