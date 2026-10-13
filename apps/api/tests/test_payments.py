"""Payments: every status transition, the limits, the proof, the receipt and isolation."""

from concurrent.futures import ThreadPoolExecutor
from datetime import date
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

from app.dates import today_in_bogota
from app.main import app
from tests.conftest import FakeEmailSender, FakeStorage, MakeToken, Tree, bearer

# The trees' leases charge $950.000 and are due on the 5th.
BEFORE_DUE = date(2026, 10, 3)
AFTER_DUE = date(2026, 10, 11)
PDF = b"%PDF-1.4 proof of payment"


@pytest.fixture
def ana(two_owners: tuple[UUID, UUID], make_token: MakeToken) -> dict[str, str]:
    return bearer(make_token(two_owners[0]))


@pytest.fixture
def beto(two_owners: tuple[UUID, UUID], make_token: MakeToken) -> dict[str, str]:
    return bearer(make_token(two_owners[1]))


def set_today(day: date) -> None:
    app.dependency_overrides[today_in_bogota] = lambda: day


@pytest.fixture(autouse=True)
def today(storage: FakeStorage, mailer: FakeEmailSender) -> None:
    set_today(BEFORE_DUE)


@pytest.fixture
def bill(api: TestClient, ana: dict[str, str], trees: tuple[Tree, Tree]) -> dict:
    """Ana's bill of October: $950.000, due on the 5th, pending."""
    return api.post(f"/api/leases/{trees[0].lease_id}/bills", headers=ana).json()


def pay(api: TestClient, headers: dict[str, str], bill: dict, amount: int, **overrides: object):
    payload = {"amount": amount, "payment_date": "2026-10-03", "method": "transfer"} | overrides
    return api.post(f"/api/bills/{bill['id']}/payments", headers=headers, json=payload)


def detail(api: TestClient, headers: dict[str, str], bill: dict) -> dict:
    return api.get(f"/api/bills/{bill['id']}", headers=headers).json()


def state(body: dict) -> tuple[str, int]:
    return body["status"], body["balance"]


# Transitions (docs/reglas-de-negocio.md), one by one


def test_pending_to_partial_with_a_payment_below_the_balance(
    api: TestClient, ana: dict[str, str], bill: dict
) -> None:
    response = pay(api, ana, bill, 400_000)

    assert response.status_code == 201
    assert state(response.json()) == ("partial", 550_000)
    (payment,) = response.json()["payments"]
    assert payment | {"id": None, "created_at": None} == {
        "id": None,
        "payment_date": "2026-10-03",
        "amount": 400_000,
        "method": "transfer",
        "has_proof": False,
        "created_at": None,
    }


def test_pending_to_paid_with_a_payment_equal_to_the_total(
    api: TestClient, ana: dict[str, str], bill: dict
) -> None:
    assert state(pay(api, ana, bill, 950_000).json()) == ("paid", 0)


def test_partial_to_paid_with_a_payment_that_completes_the_balance(
    api: TestClient, ana: dict[str, str], bill: dict
) -> None:
    pay(api, ana, bill, 400_000)

    assert state(pay(api, ana, bill, 550_000, method="nequi").json()) == ("paid", 0)
    assert [p["amount"] for p in detail(api, ana, bill)["payments"]] == [550_000, 400_000]


def test_partial_payment_on_an_overdue_bill_leaves_it_overdue(
    api: TestClient, ana: dict[str, str], trees: tuple[Tree, Tree]
) -> None:
    set_today(AFTER_DUE)
    overdue = api.post(f"/api/leases/{trees[0].lease_id}/bills", headers=ana).json()
    assert overdue["status"] == "overdue"

    assert state(pay(api, ana, overdue, 400_000).json()) == ("overdue", 550_000)


def test_overdue_to_paid_with_a_payment_that_completes_the_balance(
    api: TestClient, ana: dict[str, str], trees: tuple[Tree, Tree]
) -> None:
    set_today(AFTER_DUE)
    overdue = api.post(f"/api/leases/{trees[0].lease_id}/bills", headers=ana).json()
    pay(api, ana, overdue, 400_000)

    assert state(pay(api, ana, overdue, 550_000).json()) == ("paid", 0)


def test_partial_bill_past_its_due_date_is_overdue_on_the_next_payment(
    api: TestClient, ana: dict[str, str], bill: dict
) -> None:
    pay(api, ana, bill, 100_000)
    set_today(AFTER_DUE)

    assert state(pay(api, ana, bill, 100_000).json()) == ("overdue", 750_000)


def test_overdue_bill_with_a_payment_cannot_be_voided(
    api: TestClient, ana: dict[str, str], trees: tuple[Tree, Tree]
) -> None:
    set_today(AFTER_DUE)
    overdue = api.post(f"/api/leases/{trees[0].lease_id}/bills", headers=ana).json()
    pay(api, ana, overdue, 100_000)

    response = api.post(f"/api/bills/{overdue['id']}/void", headers=ana)

    # Its status is still "overdue"; what stops it is the payment itself.
    assert response.status_code == 400
    assert response.json()["code"] == "bill_has_payments"


# Limits


def test_payment_above_the_balance_is_refused(
    api: TestClient, ana: dict[str, str], bill: dict
) -> None:
    pay(api, ana, bill, 400_000)

    response = pay(api, ana, bill, 550_001)

    assert response.status_code == 400
    assert response.json()["code"] == "payment_exceeds_balance"
    assert "$550.000" in response.json()["detail"]
    assert state(detail(api, ana, bill)) == ("partial", 550_000)


def test_paid_and_voided_bills_take_no_payments(
    api: TestClient, ana: dict[str, str], bill: dict, trees: tuple[Tree, Tree]
) -> None:
    pay(api, ana, bill, 950_000)
    paid = pay(api, ana, bill, 1)
    assert (paid.status_code, paid.json()["code"]) == (400, "bill_already_paid")

    manual = api.post(
        "/api/bills",
        headers=ana,
        json={
            "lease_id": str(trees[0].lease_id),
            "items": [{"description": "Arreglo", "amount": 80_000}],
            "due_date": "2026-10-20",
        },
    ).json()
    api.post(f"/api/bills/{manual['id']}/void", headers=ana)
    voided = pay(api, ana, manual, 80_000)
    assert (voided.status_code, voided.json()["code"]) == (400, "bill_voided")


def test_payment_date_cannot_be_in_the_future(
    api: TestClient, ana: dict[str, str], bill: dict
) -> None:
    tomorrow = pay(api, ana, bill, 100_000, payment_date="2026-10-04")
    today = pay(api, ana, bill, 100_000, payment_date="2026-10-03")
    earlier = pay(api, ana, bill, 100_000, payment_date="2026-09-28")

    assert (tomorrow.status_code, tomorrow.json()["code"]) == (400, "payment_date_in_future")
    assert (today.status_code, earlier.status_code) == (201, 201)


@pytest.mark.parametrize(
    "overrides",
    [
        {"amount": 0},
        {"amount": -100},
        {"amount": 100.5},
        {"amount": "100"},
        {"method": "card"},
        {"payment_date": "ayer"},
    ],
)
def test_payment_is_validated(
    api: TestClient, ana: dict[str, str], bill: dict, overrides: dict
) -> None:
    response = pay(api, ana, bill, **({"amount": 100_000} | overrides))

    assert response.status_code == 422
    assert detail(api, ana, bill)["payments"] == []


def test_payments_at_once_never_exceed_the_balance(
    api: TestClient, ana: dict[str, str], bill: dict
) -> None:
    # Eight payments of $200.000 on a bill of $950.000: only four fit.
    with ThreadPoolExecutor(max_workers=8) as pool:
        responses = list(pool.map(lambda _: pay(api, ana, bill, 200_000), range(8)))

    assert sorted(response.status_code for response in responses) == [201] * 4 + [400] * 4
    after = detail(api, ana, bill)
    assert state(after) == ("partial", 150_000)
    assert len(after["payments"]) == 4


# Deleting


def test_deleting_a_payment_recalculates_the_status(
    api: TestClient, ana: dict[str, str], bill: dict
) -> None:
    first = pay(api, ana, bill, 400_000).json()["payments"][0]
    paid = pay(api, ana, bill, 550_000).json()
    assert paid["status"] == "paid"

    # A paid bill goes back to partial, and then to pending.
    partial = api.delete(f"/api/payments/{paid['payments'][0]['id']}", headers=ana)
    assert partial.status_code == 200
    assert state(partial.json()) == ("partial", 550_000)

    pending = api.delete(f"/api/payments/{first['id']}", headers=ana)
    assert state(pending.json()) == ("pending", 950_000)
    assert pending.json()["payments"] == []
    # With no payments left it can be voided again.
    assert api.post(f"/api/bills/{bill['id']}/void", headers=ana).status_code == 200


def test_deleting_the_payment_of_a_bill_past_its_due_date_leaves_it_overdue(
    api: TestClient, ana: dict[str, str], bill: dict
) -> None:
    payment = pay(api, ana, bill, 950_000).json()["payments"][0]
    set_today(AFTER_DUE)

    response = api.delete(f"/api/payments/{payment['id']}", headers=ana)

    assert state(response.json()) == ("overdue", 950_000)


# Balance everywhere


def test_lists_show_the_balance_and_the_latest_payment(
    api: TestClient, ana: dict[str, str], bill: dict, trees: tuple[Tree, Tree]
) -> None:
    pay(api, ana, bill, 100_000, payment_date="2026-10-01", method="cash")
    pay(api, ana, bill, 300_000, payment_date="2026-10-02", method="nequi")

    (row,) = api.get("/api/bills", headers=ana).json()
    (recent,) = api.get(f"/api/leases/{trees[0].lease_id}", headers=ana).json()["recent_bills"]

    for summary in (row, recent):
        assert (summary["total"], summary["balance"], summary["status"]) == (
            950_000,
            550_000,
            "partial",
        )
        assert (summary["last_payment_date"], summary["last_payment_method"]) == (
            "2026-10-02",
            "nequi",
        )


def test_reminder_says_what_is_left_to_pay(
    api: TestClient, ana: dict[str, str], bill: dict, mailer: FakeEmailSender
) -> None:
    pay(api, ana, bill, 400_000)

    api.post(f"/api/bills/{bill['id']}/remind", headers=ana)

    assert "Saldo pendiente: $550.000" in mailer.sent[0].text


# The receipt


def test_receipt_goes_out_when_asked_for(
    api: TestClient, ana: dict[str, str], bill: dict, mailer: FakeEmailSender
) -> None:
    response = pay(api, ana, bill, 400_000, method="nequi", send_receipt=True)

    assert response.status_code == 201
    (message,) = mailer.sent
    assert message.subject == "Recibo de pago: cuenta de cobro N.º 0001"
    assert message.to == "ana@example.com"
    assert "Valor recibido: $400.000" in message.text
    assert "3 de octubre de 2026 · Nequi" in message.text
    assert "Saldo restante: $550.000" in message.text
    assert message.attachments == []
    (notification,) = detail(api, ana, bill)["notifications"]
    assert (notification["type"], notification["delivery_status"]) == ("receipt", "sent")


def test_receipt_of_the_last_payment_says_the_bill_is_paid(
    api: TestClient, ana: dict[str, str], bill: dict, mailer: FakeEmailSender
) -> None:
    pay(api, ana, bill, 950_000, send_receipt=True)

    assert "La cuenta queda pagada." in mailer.sent[0].text


def test_no_receipt_unless_asked_for_or_when_the_payment_is_refused(
    api: TestClient, ana: dict[str, str], bill: dict, mailer: FakeEmailSender
) -> None:
    pay(api, ana, bill, 400_000)
    pay(api, ana, bill, 900_000, send_receipt=True)

    assert mailer.sent == []
    assert detail(api, ana, bill)["notifications"] == []


def test_receipt_that_fails_does_not_undo_the_payment(
    api: TestClient, ana: dict[str, str], bill: dict, mailer: FakeEmailSender
) -> None:
    mailer.failing = True

    response = pay(api, ana, bill, 400_000, send_receipt=True)

    assert response.status_code == 201
    after = detail(api, ana, bill)
    assert state(after) == ("partial", 550_000)
    assert [(n["type"], n["delivery_status"]) for n in after["notifications"]] == [
        ("receipt", "failed")
    ]


# The proof of payment


@pytest.fixture
def payment(api: TestClient, ana: dict[str, str], bill: dict) -> dict:
    return pay(api, ana, bill, 400_000).json()["payments"][0]


def upload_url(api: TestClient, headers: dict[str, str], payment: dict, **overrides: object):
    payload = {
        "filename": "Comprobante Nequi.pdf",
        "content_type": "application/pdf",
        "size": len(PDF),
    } | overrides
    return api.post(
        f"/api/payments/{payment['id']}/proof/upload-url", headers=headers, json=payload
    )


def test_proof_is_uploaded_confirmed_and_opened(
    api: TestClient,
    ana: dict[str, str],
    two_owners: tuple[UUID, UUID],
    bill: dict,
    payment: dict,
    storage: FakeStorage,
) -> None:
    link = upload_url(api, ana, payment)
    assert link.status_code == 200
    path = link.json()["path"]
    assert path.startswith(f"{two_owners[0]}/proofs/{payment['id']}/")
    assert path.endswith("/Comprobante-Nequi.pdf")
    storage.upload(path, PDF)

    confirmed = api.post(f"/api/payments/{payment['id']}/proof", headers=ana, json={"path": path})

    assert confirmed.status_code == 200
    assert confirmed.json()["payments"][0]["has_proof"] is True
    opened = api.get(f"/api/payments/{payment['id']}/proof", headers=ana)
    assert opened.status_code == 200
    assert opened.json()["name"] == "Comprobante-Nequi.pdf"
    assert opened.json()["expires_in"] == 300


def test_payment_without_a_proof_has_nothing_to_open(
    api: TestClient, ana: dict[str, str], payment: dict
) -> None:
    response = api.get(f"/api/payments/{payment['id']}/proof", headers=ana)

    assert (response.status_code, response.json()["code"]) == (404, "document_not_found")


def test_proof_is_checked_by_its_content_and_size(
    api: TestClient, ana: dict[str, str], payment: dict, storage: FakeStorage
) -> None:
    too_large = upload_url(api, ana, payment, size=10 * 1024 * 1024 + 1)
    wrong_type = upload_url(api, ana, payment, content_type="application/zip")
    assert (too_large.json()["code"], wrong_type.json()["code"]) == (
        "file_too_large",
        "unsupported_file_type",
    )

    # A file that says it is a PDF and is not.
    path = upload_url(api, ana, payment).json()["path"]
    storage.upload(path, b"MZ this is a program")
    fake = api.post(f"/api/payments/{payment['id']}/proof", headers=ana, json={"path": path})
    assert (fake.status_code, fake.json()["code"]) == (422, "unsupported_file_type")
    assert path not in storage.objects

    never_uploaded = upload_url(api, ana, payment).json()["path"]
    missing = api.post(
        f"/api/payments/{payment['id']}/proof", headers=ana, json={"path": never_uploaded}
    )
    assert (missing.status_code, missing.json()["code"]) == (400, "document_not_uploaded")


def test_proof_must_be_a_path_the_api_handed_out_for_that_payment(
    api: TestClient, ana: dict[str, str], bill: dict, payment: dict, storage: FakeStorage
) -> None:
    other = pay(api, ana, bill, 100_000).json()["payments"][0]
    others_path = upload_url(api, ana, other).json()["path"]
    storage.upload(others_path, PDF)

    for path in (others_path, "somewhere/else.pdf", f"x/proofs/{payment['id']}/../a.pdf"):
        response = api.post(
            f"/api/payments/{payment['id']}/proof", headers=ana, json={"path": path}
        )
        assert response.status_code == 404
    assert others_path in storage.objects


def test_deleting_a_payment_deletes_its_proof(
    api: TestClient, ana: dict[str, str], payment: dict, storage: FakeStorage
) -> None:
    path = upload_url(api, ana, payment).json()["path"]
    storage.upload(path, PDF)
    api.post(f"/api/payments/{payment['id']}/proof", headers=ana, json={"path": path})

    api.delete(f"/api/payments/{payment['id']}", headers=ana)

    assert path not in storage.objects


# Isolation


def test_payments_need_a_session(api: TestClient, bill: dict, payment: dict) -> None:
    for response in (
        api.post(f"/api/bills/{bill['id']}/payments", json={}),
        api.delete(f"/api/payments/{payment['id']}"),
        api.post(f"/api/payments/{payment['id']}/proof/upload-url", json={}),
        api.post(f"/api/payments/{payment['id']}/proof", json={}),
        api.get(f"/api/payments/{payment['id']}/proof"),
    ):
        assert response.status_code == 401


def test_owner_cannot_touch_another_owners_payments(
    api: TestClient,
    ana: dict[str, str],
    beto: dict[str, str],
    bill: dict,
    payment: dict,
    storage: FakeStorage,
    admin_engine: Engine,
) -> None:
    path = upload_url(api, ana, payment).json()["path"]
    storage.upload(path, PDF)
    api.post(f"/api/payments/{payment['id']}/proof", headers=ana, json={"path": path})

    for response in (
        pay(api, beto, bill, 100_000),
        api.delete(f"/api/payments/{payment['id']}", headers=beto),
        upload_url(api, beto, payment),
        api.post(f"/api/payments/{payment['id']}/proof", headers=beto, json={"path": path}),
        api.get(f"/api/payments/{payment['id']}/proof", headers=beto),
        api.delete(f"/api/payments/{uuid4()}", headers=ana),
    ):
        assert response.status_code == 404
        assert response.json()["code"] == "not_found"

    # Nothing of Ana's changed.
    with admin_engine.connect() as connection:
        amounts = connection.execute(text("select amount from payments")).scalars().all()
    assert amounts == [400_000]
    assert path in storage.objects
    assert state(detail(api, ana, bill)) == ("partial", 550_000)
