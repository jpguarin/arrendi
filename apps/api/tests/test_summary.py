"""The home screen's figures, and how each unit is doing."""

from datetime import date
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

from app.dates import today_in_bogota
from app.main import app
from tests.conftest import FakeEmailSender, FakeStorage, MakeToken, bearer, create_tree


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
    set_today(date(2026, 10, 3))


def monthly(api: TestClient, headers: dict[str, str], lease_id: UUID) -> dict:
    return api.post(f"/api/leases/{lease_id}/bills", headers=headers).json()


def pay(api: TestClient, headers: dict[str, str], bill: dict, amount: int, day: str) -> None:
    response = api.post(
        f"/api/bills/{bill['id']}/payments",
        headers=headers,
        json={"amount": amount, "payment_date": day, "method": "transfer"},
    )
    assert response.status_code == 201, response.text


@pytest.fixture
def house(
    api: TestClient, ana: dict[str, str], two_owners: tuple[UUID, UUID], admin_engine: Engine
) -> dict[str, dict]:
    """Ana's three units on 11 October, each $950.000 a month and due on the 5th.

    - uno: September unpaid (overdue), October unpaid (overdue).
    - dos: October with a payment of $400.000 made before the due date... and now overdue.
    - tres: October paid in full.
    And a fourth unit with no lease.
    """
    with admin_engine.begin() as connection:
        one = create_tree(connection, two_owners[0], "uno")
        two = create_tree(connection, two_owners[0], "dos")
        three = create_tree(connection, two_owners[0], "tres")
        connection.execute(
            text(
                "insert into units (owner_id, property_id, name, use) "
                "values (:owner, :property, 'Local vacío', 'commercial')"
            ),
            {"owner": two_owners[0], "property": one.property_id},
        )
    set_today(date(2026, 9, 1))
    september = monthly(api, ana, one.lease_id)
    set_today(date(2026, 10, 3))
    bills = {
        "september": september,
        "one": monthly(api, ana, one.lease_id),
        "two": monthly(api, ana, two.lease_id),
        "three": monthly(api, ana, three.lease_id),
    }
    pay(api, ana, bills["two"], 400_000, "2026-10-02")
    pay(api, ana, bills["three"], 950_000, "2026-10-03")
    # The daily task marks what is past its due date.
    with admin_engine.begin() as connection:
        connection.execute(
            text(
                "update bills set status = 'overdue' where owner_id = :owner "
                "and status in ('pending', 'partial') and due_date < '2026-10-11'"
            ),
            {"owner": two_owners[0]},
        )
    set_today(date(2026, 10, 11))
    return bills


def test_figures_are_of_the_month_and_older_debt_is_counted_apart(
    api: TestClient, ana: dict[str, str], house: dict[str, dict]
) -> None:
    response = api.get("/api/summary", headers=ana)

    assert response.status_code == 200
    summary = response.json()
    assert summary["month"] == "2026-10-01"
    # October: three bills of $950.000; $400.000 + $950.000 paid.
    assert (summary["expected"], summary["collected"], summary["pending"]) == (
        2_850_000,
        1_350_000,
        1_500_000,
    )
    # September's bill is owed in full, but it is not part of October's figures.
    assert summary["previous_pending"] == 950_000
    assert (summary["units_total"], summary["units_overdue"]) == (4, 2)


def test_receivable_lists_everything_owed_and_paid_only_the_month(
    api: TestClient, ana: dict[str, str], house: dict[str, dict]
) -> None:
    summary = api.get("/api/summary", headers=ana).json()

    # Oldest due date first: September's, then October's.
    assert [(b["number"], b["status"], b["balance"]) for b in summary["receivable"]] == [
        (1, "overdue", 950_000),
        (2, "overdue", 950_000),
        (3, "overdue", 550_000),
    ]
    (paid,) = summary["paid"]
    assert (paid["number"], paid["unit_name"], paid["last_payment_date"]) == (
        4,
        "Apto tres",
        "2026-10-03",
    )


def test_figures_match_the_list_of_bills_of_the_same_month(
    api: TestClient, ana: dict[str, str], house: dict[str, dict]
) -> None:
    summary = api.get("/api/summary", headers=ana).json()
    listed = api.get(
        "/api/bills", headers=ana, params={"from": "2026-10-01", "to": "2026-10-31"}
    ).json()

    assert summary["expected"] == sum(bill["total"] for bill in listed)
    assert summary["collected"] == sum(bill["total"] - bill["balance"] for bill in listed)


def test_payment_counts_in_the_month_of_its_bill(
    api: TestClient, ana: dict[str, str], house: dict[str, dict]
) -> None:
    # In October, a payment on September's bill.
    pay(api, ana, house["september"], 300_000, "2026-10-10")

    october = api.get("/api/summary", headers=ana).json()
    september = api.get("/api/summary", headers=ana, params={"month": "2026-09"}).json()

    assert october["collected"] == 1_350_000
    assert october["previous_pending"] == 650_000
    assert (september["expected"], september["collected"], september["pending"]) == (
        950_000,
        300_000,
        650_000,
    )
    assert september["previous_pending"] == 0


def test_voided_bills_are_left_out(
    api: TestClient, ana: dict[str, str], house: dict[str, dict]
) -> None:
    api.post(f"/api/bills/{house['one']['id']}/void", headers=ana)

    summary = api.get("/api/summary", headers=ana).json()

    assert summary["expected"] == 1_900_000
    assert [b["number"] for b in summary["receivable"]] == [1, 3]


def test_bounced_emails_of_bills_still_owed_are_listed(
    api: TestClient, ana: dict[str, str], house: dict[str, dict], admin_engine: Engine
) -> None:
    with admin_engine.begin() as connection:
        for bill in ("one", "three"):
            connection.execute(
                text(
                    "insert into notifications (owner_id, bill_id, type, recipient, "
                    "delivery_status) select owner_id, id, 'bill', 'mal@example.com', 'bounced' "
                    "from bills where id = :id"
                ),
                {"id": house[bill]["id"]},
            )

    bounced = api.get("/api/summary", headers=ana).json()["bounced"]

    # The paid bill's bounce no longer matters.
    assert bounced == [
        {
            "bill_id": house["one"]["id"],
            "number": 2,
            "unit_name": "Apto uno",
            "tenant_name": "Arrendatario uno",
            "recipient": "mal@example.com",
        }
    ]


def test_empty_summary_and_month_format(api: TestClient, ana: dict[str, str]) -> None:
    summary = api.get("/api/summary", headers=ana).json()

    assert summary == {
        "month": "2026-10-01",
        "expected": 0,
        "collected": 0,
        "pending": 0,
        "previous_pending": 0,
        "units_total": 0,
        "units_overdue": 0,
        "receivable": [],
        "paid": [],
        "bounced": [],
    }
    for month in ("2026-13", "octubre", "2026-1", "2026-10-01"):
        assert api.get("/api/summary", headers=ana, params={"month": month}).status_code == 422


def test_each_unit_says_how_it_is_doing(
    api: TestClient, ana: dict[str, str], house: dict[str, dict]
) -> None:
    properties = api.get("/api/properties", headers=ana).json()
    statuses = {unit["name"]: unit["status"] for p in properties for unit in p["units"]}

    assert statuses == {
        "Apto uno": "overdue",
        "Apto dos": "overdue",
        "Apto tres": "up_to_date",
        "Local vacío": "vacant",
    }


def test_unit_with_a_partial_bill_not_yet_due_is_partial(
    api: TestClient, ana: dict[str, str], trees
) -> None:
    bill = monthly(api, ana, trees[0].lease_id)
    pay(api, ana, bill, 100_000, "2026-10-03")

    (property_,) = api.get("/api/properties", headers=ana).json()

    assert property_["units"][0]["status"] == "partial"


def test_summary_is_per_owner(
    api: TestClient, ana: dict[str, str], beto: dict[str, str], house: dict[str, dict]
) -> None:
    summary = api.get("/api/summary", headers=beto).json()

    assert (summary["expected"], summary["units_total"], summary["receivable"]) == (0, 0, [])
    assert api.get("/api/summary").status_code == 401
