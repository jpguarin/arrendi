"""How many emails an owner can ask for in a day. The daily task is not held back."""

from concurrent.futures import ThreadPoolExecutor
from datetime import date
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

from app.dates import today_in_bogota
from app.main import app
from app.services.notifications import MAX_EMAILS_PER_BILL, MAX_EMAILS_PER_OWNER
from app.tasks.daily import run_daily
from tests.conftest import FakeEmailSender, FakeStorage, MakeToken, Tree, bearer

TODAY = date(2026, 10, 3)


@pytest.fixture
def ana(two_owners: tuple[UUID, UUID], make_token: MakeToken) -> dict[str, str]:
    return bearer(make_token(two_owners[0]))


@pytest.fixture
def beto(two_owners: tuple[UUID, UUID], make_token: MakeToken) -> dict[str, str]:
    return bearer(make_token(two_owners[1]))


@pytest.fixture(autouse=True)
def today(storage: FakeStorage, mailer: FakeEmailSender) -> None:
    app.dependency_overrides[today_in_bogota] = lambda: TODAY


def manual_bill(api: TestClient, headers: dict[str, str], tree: Tree) -> dict:
    response = api.post(
        "/api/bills",
        headers=headers,
        json={
            "lease_id": str(tree.lease_id),
            "items": [{"description": "Reparación", "amount": 100_000}],
            "due_date": "2026-10-20",
        },
    )
    assert response.status_code == 201
    return response.json()


def send(api: TestClient, headers: dict[str, str], bill: dict, action: str = "send"):
    return api.post(f"/api/bills/{bill['id']}/{action}", headers=headers)


def pay(api: TestClient, headers: dict[str, str], bill: dict, send_receipt: bool):
    return api.post(
        f"/api/bills/{bill['id']}/payments",
        headers=headers,
        json={
            "amount": 1_000,
            "payment_date": TODAY.isoformat(),
            "method": "cash",
            "send_receipt": send_receipt,
        },
    )


def use_up_the_owner(api: TestClient, headers: dict[str, str], tree: Tree) -> None:
    sent = 0
    while sent < MAX_EMAILS_PER_OWNER:
        bill = manual_bill(api, headers, tree)
        for _ in range(min(MAX_EMAILS_PER_BILL, MAX_EMAILS_PER_OWNER - sent)):
            assert send(api, headers, bill).status_code == 200
            sent += 1


def test_a_bill_takes_a_few_emails_a_day_of_any_kind(
    api: TestClient,
    ana: dict[str, str],
    trees: tuple[Tree, Tree],
    mailer: FakeEmailSender,
) -> None:
    bill = manual_bill(api, ana, trees[0])
    assert send(api, ana, bill).status_code == 200
    assert send(api, ana, bill, "remind").status_code == 200
    assert pay(api, ana, bill, send_receipt=True).status_code == 201

    for action in ("send", "remind"):
        response = send(api, ana, bill, action)
        assert response.status_code == 429
        assert response.json()["code"] == "email_limit_reached"

    assert len(mailer.sent) == MAX_EMAILS_PER_BILL
    found = api.get(f"/api/bills/{bill['id']}", headers=ana).json()
    assert len(found["notifications"]) == MAX_EMAILS_PER_BILL


def test_a_payment_over_the_limit_is_not_recorded_until_it_asks_for_no_receipt(
    api: TestClient, ana: dict[str, str], trees: tuple[Tree, Tree], mailer: FakeEmailSender
) -> None:
    bill = manual_bill(api, ana, trees[0])
    for _ in range(MAX_EMAILS_PER_BILL):
        assert send(api, ana, bill).status_code == 200

    refused = pay(api, ana, bill, send_receipt=True)
    assert refused.status_code == 429
    assert refused.json()["code"] == "email_limit_reached"
    # The owner is told what to do now, not to come back tomorrow.
    assert "sin recibo" in refused.json()["detail"]
    assert api.get(f"/api/bills/{bill['id']}", headers=ana).json()["payments"] == []

    assert pay(api, ana, bill, send_receipt=False).status_code == 201
    assert len(mailer.sent) == MAX_EMAILS_PER_BILL


def test_an_owner_takes_a_limited_number_of_emails_a_day(
    api: TestClient, ana: dict[str, str], trees: tuple[Tree, Tree], mailer: FakeEmailSender
) -> None:
    use_up_the_owner(api, ana, trees[0])

    # A new bill does not get around it: its first send counts too.
    response = send(api, ana, manual_bill(api, ana, trees[0]))

    assert response.status_code == 429
    assert response.json()["code"] == "email_limit_reached"
    assert len(mailer.sent) == MAX_EMAILS_PER_OWNER


def move_notifications_to(admin_engine: Engine, offset: str) -> None:
    """Moves every notification to this far from the moment today began in Colombia."""
    with admin_engine.begin() as connection:
        connection.execute(
            text(
                """
                update notifications set created_at =
                  date_trunc('day', now() at time zone 'America/Bogota')
                  at time zone 'America/Bogota' + cast(:offset as interval)
                """
            ),
            {"offset": offset},
        )


def test_the_limit_starts_over_at_midnight_in_colombia(
    api: TestClient, ana: dict[str, str], trees: tuple[Tree, Tree], admin_engine: Engine
) -> None:
    bill = manual_bill(api, ana, trees[0])
    for _ in range(MAX_EMAILS_PER_BILL):
        assert send(api, ana, bill).status_code == 200

    # Both sides of midnight, so a count by the day in UTC fails at any hour it runs: for
    # part of the day it would take the first as today, and for the rest the second as not.
    move_notifications_to(admin_engine, "1 second")
    assert send(api, ana, bill).status_code == 429

    move_notifications_to(admin_engine, "-1 minute")
    assert send(api, ana, bill).status_code == 200


def test_one_owners_emails_do_not_count_against_another(
    api: TestClient,
    ana: dict[str, str],
    beto: dict[str, str],
    trees: tuple[Tree, Tree],
) -> None:
    use_up_the_owner(api, ana, trees[0])
    assert send(api, ana, manual_bill(api, ana, trees[0])).status_code == 429

    assert send(api, beto, manual_bill(api, beto, trees[1])).status_code == 200


def test_a_limit_never_reveals_another_owners_bill(
    api: TestClient, ana: dict[str, str], beto: dict[str, str], trees: tuple[Tree, Tree]
) -> None:
    bill = manual_bill(api, ana, trees[0])
    for _ in range(MAX_EMAILS_PER_BILL):
        assert send(api, ana, bill).status_code == 200

    assert send(api, beto, bill).status_code == 404
    assert pay(api, beto, bill, send_receipt=True).status_code == 404


def test_requests_at_once_cannot_get_past_the_limit(
    api: TestClient, ana: dict[str, str], trees: tuple[Tree, Tree], mailer: FakeEmailSender
) -> None:
    bill = manual_bill(api, ana, trees[0])

    with ThreadPoolExecutor(max_workers=8) as pool:
        codes = list(pool.map(lambda _: send(api, ana, bill, "remind").status_code, range(8)))

    assert sorted(codes) == [200] * MAX_EMAILS_PER_BILL + [429] * (8 - MAX_EMAILS_PER_BILL)
    assert len(mailer.sent) == MAX_EMAILS_PER_BILL


def test_the_daily_task_still_sends_for_an_owner_at_the_limit(
    api: TestClient,
    ana: dict[str, str],
    trees: tuple[Tree, Tree],
    tasks_engine: Engine,
    mailer: FakeEmailSender,
    storage: FakeStorage,
) -> None:
    use_up_the_owner(api, ana, trees[0])
    before = len(mailer.sent)

    result = run_daily(tasks_engine, mailer, storage, TODAY)

    assert result.errors == 0
    assert len(mailer.sent) > before
