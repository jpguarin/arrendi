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


def test_the_copies_of_the_lease_get_every_email_of_the_tenant(
    api: TestClient,
    ana: dict[str, str],
    trees: tuple[Tree, Tree],
    bill: dict,
    mailer: FakeEmailSender,
) -> None:
    copies = ["pedro@example.com", "pagos@empresa.example.com"]
    api.patch(f"/api/leases/{trees[0].lease_id}", json={"cc_emails": copies}, headers=ana)

    api.post(f"/api/bills/{bill['id']}/send", headers=ana)
    api.post(f"/api/bills/{bill['id']}/send", headers=ana)
    api.post(f"/api/bills/{bill['id']}/remind", headers=ana)
    api.post(
        f"/api/bills/{bill['id']}/payments",
        json={
            "amount": 400_000,
            "payment_date": "2026-10-03",
            "method": "transfer",
            "send_receipt": True,
        },
        headers=ana,
    )

    assert [message.subject.split(":")[0] for message in mailer.sent] == [
        "Cuenta de cobro N.º 0001",
        "Cuenta de cobro N.º 0001",
        "Recordatorio de pago",
        "Recibo de pago",
    ]
    assert all(message.to == "ana@example.com" for message in mailer.sent)
    assert all(message.cc == copies for message in mailer.sent)
    # The notification is still the tenant's.
    assert {n["recipient"] for n in detail(api, ana, bill)["notifications"]} == {"ana@example.com"}


def test_without_copies_the_email_goes_to_the_tenant_alone(
    api: TestClient, ana: dict[str, str], bill: dict, mailer: FakeEmailSender
) -> None:
    api.post(f"/api/bills/{bill['id']}/send", headers=ana)

    assert mailer.sent[0].cc == []


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


def test_emails_carry_the_payment_details_the_bill_was_issued_with(
    api: TestClient, ana: dict[str, str], trees: tuple[Tree, Tree], mailer: FakeEmailSender
) -> None:
    lease = f"/api/leases/{trees[0].lease_id}"
    api.patch("/api/settings", headers=ana, json={"payment_details": "Nequi de Ajustes"})
    api.patch(lease, headers=ana, json={"payment_details": "Daviplata del contrato"})
    bill = api.post(f"{lease}/bills", headers=ana).json()
    api.patch("/api/settings", headers=ana, json={"payment_details": "Otro banco"})
    api.patch(lease, headers=ana, json={"payment_details": None})

    api.post(f"/api/bills/{bill['id']}/send", headers=ana)
    api.post(f"/api/bills/{bill['id']}/remind", headers=ana)

    assert len(mailer.sent) == 2
    for message in mailer.sent:
        assert "Daviplata del contrato" in message.text
        assert "Otro banco" not in message.text and "Nequi de Ajustes" not in message.text


def test_email_names_the_first_item_as_typed_and_counts_the_rest(
    api: TestClient, ana: dict[str, str], trees: tuple[Tree, Tree], mailer: FakeEmailSender
) -> None:
    manual = api.post(
        "/api/bills",
        headers=ana,
        json={
            "lease_id": str(trees[0].lease_id),
            "items": [
                {"description": "IVA del canon", "amount": 190000},
                {"description": "EPM servicios", "amount": 80000},
                {"description": "Parqueadero Juan", "amount": 50000},
            ],
            "due_date": "2026-10-20",
        },
    ).json()

    api.post(f"/api/bills/{manual['id']}/send", headers=ana)

    (message,) = mailer.sent
    # Not a letter of what the owner typed changes, at the start of a line or mid-sentence.
    assert "IVA del canon y 2 conceptos más · Apto ana" in message.text
    assert "la cuenta de cobro de IVA del canon y 2 conceptos más" in message.text
    for mangled in ("iVA", "ePM", "EPM", "Parqueadero Juan"):
        assert mangled not in message.text
    assert "$320.000" in message.text


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
