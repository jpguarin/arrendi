"""The late fee: a bill's own terms, and the item a later bill charges it with."""

from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text
from sqlalchemy.exc import IntegrityError

from app.dates import today_in_bogota
from app.db import set_owner_id
from app.main import app
from app.services.bills import late_fee_amount
from app.tasks.daily import run_daily
from tests.conftest import FakeEmailSender, FakeStorage, MakeToken, Tree, bearer

# The trees' leases charge $950.000 and are due on the 5th. With 5 % and three days of
# grace, paying after the 8th costs $47.500.
RENT_ITEM = {"description": "Canon de arrendamiento", "amount": 950000}
OCTOBER_FEE = {"description": "Recargo por mora de octubre 2026", "amount": 47500}
ISSUED = date(2026, 10, 1)
DEADLINE = date(2026, 10, 8)
NOVEMBER = date(2026, 11, 1)


@pytest.fixture
def ana(two_owners: tuple[UUID, UUID], make_token: MakeToken) -> dict[str, str]:
    return bearer(make_token(two_owners[0]))


@pytest.fixture
def beto(two_owners: tuple[UUID, UUID], make_token: MakeToken) -> dict[str, str]:
    return bearer(make_token(two_owners[1]))


def set_today(day: date) -> None:
    app.dependency_overrides[today_in_bogota] = lambda: day


@pytest.fixture(autouse=True)
def today(storage: FakeStorage) -> None:
    set_today(ISSUED)


def late_fee_on(api: TestClient, headers: dict[str, str], lease_id: UUID, **changes) -> None:
    body = {"late_fee_enabled": True, "late_fee_percent": "5", "late_fee_grace_days": 3}
    response = api.patch(f"/api/leases/{lease_id}", headers=headers, json=body | changes)
    assert response.status_code == 200, response.text


@pytest.fixture
def lease(api: TestClient, ana: dict[str, str], trees: tuple[Tree, Tree]) -> UUID:
    """Ana's lease, with the late fee on."""
    late_fee_on(api, ana, trees[0].lease_id)
    return trees[0].lease_id


def monthly(api: TestClient, headers: dict[str, str], lease_id: UUID, day: date | None = None):
    if day:
        set_today(day)
    return api.post(f"/api/leases/{lease_id}/bills", headers=headers)


def pay(api: TestClient, headers: dict[str, str], bill: dict, amount: int, on: date) -> None:
    body = {"amount": amount, "payment_date": on.isoformat(), "method": "transfer"}
    response = api.post(f"/api/bills/{bill['id']}/payments", headers=headers, json=body)
    assert response.status_code == 201, response.text


def late_fee(api: TestClient, headers: dict[str, str], bill: dict) -> dict | None:
    return api.get(f"/api/bills/{bill['id']}", headers=headers).json()["late_fee"]


def status(api: TestClient, headers: dict[str, str], bill: dict) -> str:
    return late_fee(api, headers, bill)["status"]


# The amount


@pytest.mark.parametrize(
    ("rent", "percent", "expected"),
    [
        (950000, "5", 47500),
        (1000000, "2.5", 25000),
        # Half a peso goes up, and it is decimal arithmetic all the way.
        (1000020, "2.5", 25001),
        (1234567, "2.5", 30864),
        (333333, "0.01", 33),
        (100, "0.01", None),
    ],
)
def test_fee_is_a_percentage_of_the_rent_in_whole_pesos(
    rent: int, percent: str, expected: int | None
) -> None:
    assert late_fee_amount(rent, Decimal(percent)) == expected


# The terms of a bill


def test_monthly_bill_keeps_what_paying_late_costs_and_until_when(
    api: TestClient, ana: dict[str, str], lease: UUID
) -> None:
    bill = monthly(api, ana, lease).json()

    assert bill["items"] == [RENT_ITEM]
    assert bill["total"] == 950000
    assert bill["late_fee"] == {
        "amount": 47500,
        "deadline": "2026-10-08",
        "status": "on_time",
        "charged_on": None,
    }


def test_bill_and_its_email_say_what_paying_late_costs(
    api: TestClient,
    ana: dict[str, str],
    lease: UUID,
    storage: FakeStorage,
    mailer: FakeEmailSender,
) -> None:
    bill = monthly(api, ana, lease).json()

    api.post(f"/api/bills/{bill['id']}/send", headers=ana)

    (pdf,) = storage.objects.values()
    assert b"s del 8 de octubre de 2026, la siguiente cuenta" in pdf
    assert b"un recargo por" in pdf and b"mora de $47.500." in pdf
    (message,) = mailer.sent
    assert (
        "Si se paga después del 8 de octubre de 2026, la siguiente cuenta incluirá un "
        "recargo por mora de $47.500." in message.text
    )


def test_bill_of_a_lease_without_a_late_fee_never_owes_one(
    api: TestClient, ana: dict[str, str], trees: tuple[Tree, Tree]
) -> None:
    lease_id = trees[0].lease_id
    october = monthly(api, ana, lease_id).json()
    assert october["late_fee"] is None

    # Turning it on later does not reach the bill already issued.
    late_fee_on(api, ana, lease_id)
    november = monthly(api, ana, lease_id, NOVEMBER).json()

    assert late_fee(api, ana, october) is None
    assert november["items"] == [RENT_ITEM]
    assert november["late_fee"]["deadline"] == "2026-11-08"


def test_changing_the_lease_later_does_not_touch_the_terms_of_the_bill(
    api: TestClient, ana: dict[str, str], lease: UUID
) -> None:
    october = monthly(api, ana, lease).json()

    late_fee_on(api, ana, lease, late_fee_percent="10", late_fee_grace_days=0)
    api.patch(f"/api/leases/{lease}", headers=ana, json={"late_fee_enabled": False})

    assert late_fee(api, ana, october)["amount"] == 47500
    # The next bill charges October's fee as October's bill said, and has none of its own.
    november = monthly(api, ana, lease, NOVEMBER).json()
    assert november["items"] == [RENT_ITEM, OCTOBER_FEE]
    assert november["late_fee"] is None


def test_manual_bill_has_no_late_fee_and_charges_none(
    api: TestClient, ana: dict[str, str], lease: UUID
) -> None:
    monthly(api, ana, lease)
    set_today(NOVEMBER)

    manual = api.post(
        "/api/bills",
        headers=ana,
        json={
            "lease_id": str(lease),
            "items": [{"description": "Arreglo", "amount": 80000}],
            "due_date": "2026-11-20",
        },
    ).json()

    assert manual["late_fee"] is None
    assert manual["items"] == [{"description": "Arreglo", "amount": 80000}]


# Late or in time


def test_unpaid_bill_is_in_time_until_its_deadline_and_late_the_day_after(
    api: TestClient, ana: dict[str, str], lease: UUID
) -> None:
    bill = monthly(api, ana, lease).json()

    set_today(DEADLINE)
    assert status(api, ana, bill) == "on_time"
    set_today(date(2026, 10, 9))
    assert status(api, ana, bill) == "pending"


def test_bill_paid_on_the_deadline_owes_no_fee(
    api: TestClient, ana: dict[str, str], lease: UUID
) -> None:
    bill = monthly(api, ana, lease).json()
    set_today(date(2026, 10, 20))
    # Registered late, but the payment came in on the last day.
    pay(api, ana, bill, 950000, DEADLINE)

    assert status(api, ana, bill) == "on_time"
    assert monthly(api, ana, lease, NOVEMBER).json()["items"] == [RENT_ITEM]


def test_bill_paid_in_full_after_the_deadline_owes_the_fee(
    api: TestClient, ana: dict[str, str], lease: UUID
) -> None:
    bill = monthly(api, ana, lease).json()
    set_today(date(2026, 10, 20))
    pay(api, ana, bill, 950000, date(2026, 10, 9))

    assert status(api, ana, bill) == "pending"
    assert monthly(api, ana, lease, NOVEMBER).json()["items"] == [RENT_ITEM, OCTOBER_FEE]


def test_part_paid_in_time_and_the_rest_late_owes_the_whole_fee(
    api: TestClient, ana: dict[str, str], lease: UUID
) -> None:
    bill = monthly(api, ana, lease).json()
    set_today(date(2026, 10, 20))
    pay(api, ana, bill, 900000, date(2026, 10, 4))
    pay(api, ana, bill, 50000, date(2026, 10, 15))

    # On the rent, not on what was left to pay.
    assert monthly(api, ana, lease, NOVEMBER).json()["items"] == [RENT_ITEM, OCTOBER_FEE]


def test_voided_bill_owes_no_fee(api: TestClient, ana: dict[str, str], lease: UUID) -> None:
    bill = monthly(api, ana, lease).json()
    set_today(date(2026, 10, 20))
    api.post(f"/api/bills/{bill['id']}/void", headers=ana)

    assert late_fee(api, ana, bill) is None
    assert monthly(api, ana, lease, NOVEMBER).json()["items"] == [RENT_ITEM]


# The next bill charges it


def test_next_monthly_bill_charges_the_fee_as_its_own_item(
    api: TestClient, ana: dict[str, str], lease: UUID, storage: FakeStorage
) -> None:
    october = monthly(api, ana, lease).json()

    november = monthly(api, ana, lease, NOVEMBER).json()

    assert november["items"] == [RENT_ITEM, OCTOBER_FEE]
    assert (november["total"], november["balance"]) == (997500, 997500)
    assert late_fee(api, ana, october) == {
        "amount": 47500,
        "deadline": "2026-10-08",
        "status": "charged",
        "charged_on": {"id": november["id"], "number": 2},
    }
    # The late bill itself is as it was issued.
    after = api.get(f"/api/bills/{october['id']}", headers=ana).json()
    assert (after["items"], after["total"]) == ([RENT_ITEM], 950000)
    pdf = storage.objects[next(path for path in storage.objects if november["id"] in path)]
    assert b"Recargo por mora de octubre 2026" in pdf and b"$47.500" in pdf


def test_fee_goes_after_the_items_of_the_lease(
    api: TestClient, ana: dict[str, str], lease: UUID
) -> None:
    fee_item = {"description": "Administración", "amount": 200000}
    api.patch(f"/api/leases/{lease}", headers=ana, json={"items": [fee_item]})
    monthly(api, ana, lease)

    november = monthly(api, ana, lease, NOVEMBER).json()

    # On the rent alone: 5 % of $950.000, not of the $1.150.000 the bill added up to.
    assert november["items"] == [RENT_ITEM, fee_item, OCTOBER_FEE]


def test_fee_is_charged_only_once(api: TestClient, ana: dict[str, str], lease: UUID) -> None:
    monthly(api, ana, lease)
    november = monthly(api, ana, lease, NOVEMBER).json()
    pay(api, ana, november, 997500, NOVEMBER)

    december = monthly(api, ana, lease, date(2026, 12, 1)).json()

    assert december["items"] == [RENT_ITEM]


def test_every_late_bill_gets_its_own_fee(
    api: TestClient, ana: dict[str, str], lease: UUID
) -> None:
    monthly(api, ana, lease)
    monthly(api, ana, lease, NOVEMBER)

    december = monthly(api, ana, lease, date(2026, 12, 1)).json()

    # November's was not paid either; October's is already on November's bill.
    assert december["items"] == [
        RENT_ITEM,
        {"description": "Recargo por mora de noviembre 2026", "amount": 47500},
    ]


def test_deadline_after_the_next_bill_is_issued_waits_for_the_one_after(
    api: TestClient, ana: dict[str, str], trees: tuple[Tree, Tree]
) -> None:
    lease_id = trees[0].lease_id
    api.patch(f"/api/leases/{lease_id}", headers=ana, json={"due_day": 28})
    late_fee_on(api, ana, lease_id, late_fee_grace_days=5)
    october = monthly(api, ana, lease_id).json()
    assert october["late_fee"]["deadline"] == "2026-11-02"

    november = monthly(api, ana, lease_id, NOVEMBER).json()
    pay(api, ana, november, 950000, NOVEMBER)
    december = monthly(api, ana, lease_id, date(2026, 12, 1)).json()

    assert november["items"] == [RENT_ITEM]
    assert december["items"] == [RENT_ITEM, OCTOBER_FEE]


def test_voiding_the_bill_that_charged_the_fee_leaves_it_to_the_one_that_replaces_it(
    api: TestClient, ana: dict[str, str], lease: UUID
) -> None:
    october = monthly(api, ana, lease).json()
    november = monthly(api, ana, lease, NOVEMBER).json()

    api.post(f"/api/bills/{november['id']}/void", headers=ana)
    assert status(api, ana, october) == "pending"
    again = monthly(api, ana, lease).json()

    assert again["items"] == [RENT_ITEM, OCTOBER_FEE]
    assert late_fee(api, ana, october)["charged_on"] == {"id": again["id"], "number": 3}


def test_two_requests_at_once_charge_the_fee_once(
    api: TestClient, ana: dict[str, str], lease: UUID, admin_engine: Engine
) -> None:
    monthly(api, ana, lease)
    set_today(NOVEMBER)

    with ThreadPoolExecutor(max_workers=4) as pool:
        codes = list(pool.map(lambda _: monthly(api, ana, lease).status_code, range(4)))

    assert sorted(codes) == [201, 409, 409, 409]
    with admin_engine.connect() as connection:
        fees = connection.execute(
            text("select count(*) from bill_items where late_fee_of_bill_id is not null")
        ).scalar_one()
    assert fees == 1


def test_daily_task_charges_the_fee_once_however_often_it_runs(
    api: TestClient,
    ana: dict[str, str],
    lease: UUID,
    two_owners: tuple[UUID, UUID],
    tasks_engine: Engine,
    admin_engine: Engine,
    storage: FakeStorage,
) -> None:
    mailer = FakeEmailSender()
    for day in (ISSUED, ISSUED, NOVEMBER, NOVEMBER, date(2026, 11, 2)):
        run_daily(tasks_engine, mailer, storage, day)

    with admin_engine.connect() as connection:
        bills = connection.execute(
            text(
                "select number, total, late_fee_amount, late_fee_deadline from bills "
                "where owner_id = :id order by number"
            ),
            {"id": two_owners[0]},
        ).all()
        fees = connection.execute(
            text(
                "select i.description, i.amount, b.number from bill_items i "
                "join bills b on b.id = i.bill_id where i.late_fee_of_bill_id is not null"
            )
        ).all()
    assert [tuple(row) for row in bills] == [
        (1, 950000, 47500, DEADLINE),
        (2, 997500, 47500, date(2026, 11, 8)),
    ]
    assert [tuple(row) for row in fees] == [("Recargo por mora de octubre 2026", 47500, 2)]


# Waiving


def test_waived_fee_is_not_charged_and_can_be_brought_back(
    api: TestClient, ana: dict[str, str], lease: UUID
) -> None:
    october = monthly(api, ana, lease).json()
    set_today(date(2026, 10, 9))

    waived = api.post(f"/api/bills/{october['id']}/late-fee/waive", headers=ana)

    assert waived.status_code == 200
    assert waived.json()["late_fee"]["status"] == "waived"
    november = monthly(api, ana, lease, NOVEMBER).json()
    assert november["items"] == [RENT_ITEM]

    # Changed their mind: the fee is owed again, and the bill after that one charges it.
    restored = api.post(f"/api/bills/{october['id']}/late-fee/restore", headers=ana)
    assert restored.json()["late_fee"]["status"] == "pending"
    pay(api, ana, november, 950000, NOVEMBER)
    december = monthly(api, ana, lease, date(2026, 12, 1)).json()
    assert december["items"] == [RENT_ITEM, OCTOBER_FEE]


def test_fee_can_be_waived_before_the_bill_is_late(
    api: TestClient, ana: dict[str, str], lease: UUID
) -> None:
    october = monthly(api, ana, lease).json()

    response = api.post(f"/api/bills/{october['id']}/late-fee/waive", headers=ana)

    assert response.json()["late_fee"]["status"] == "waived"
    assert monthly(api, ana, lease, NOVEMBER).json()["items"] == [RENT_ITEM]


def test_fee_already_charged_cannot_be_waived(
    api: TestClient, ana: dict[str, str], lease: UUID
) -> None:
    october = monthly(api, ana, lease).json()
    monthly(api, ana, lease, NOVEMBER)

    for action in ("waive", "restore"):
        response = api.post(f"/api/bills/{october['id']}/late-fee/{action}", headers=ana)
        assert (response.status_code, response.json()["code"]) == (
            400,
            "late_fee_already_charged",
        )


def test_bill_without_a_late_fee_has_nothing_to_waive(
    api: TestClient, ana: dict[str, str], trees: tuple[Tree, Tree]
) -> None:
    bill = monthly(api, ana, trees[0].lease_id).json()

    for action in ("waive", "restore"):
        response = api.post(f"/api/bills/{bill['id']}/late-fee/{action}", headers=ana)
        assert (response.status_code, response.json()["code"]) == (400, "bill_has_no_late_fee")


# The lease


def test_lease_says_its_late_fee(api: TestClient, ana: dict[str, str], lease: UUID) -> None:
    body = api.get(f"/api/leases/{lease}", headers=ana).json()

    assert (
        body["late_fee_enabled"],
        Decimal(body["late_fee_percent"]),
        body["late_fee_grace_days"],
    ) == (True, Decimal("5"), 3)


@pytest.mark.parametrize(
    "changes",
    [
        {"late_fee_enabled": True},
        {"late_fee_enabled": True, "late_fee_percent": None},
        {"late_fee_enabled": True, "late_fee_percent": "0"},
        {"late_fee_enabled": True, "late_fee_percent": "100.01"},
        {"late_fee_enabled": True, "late_fee_percent": "2.555"},
        {"late_fee_enabled": True, "late_fee_percent": "5", "late_fee_grace_days": 31},
        {"late_fee_enabled": True, "late_fee_percent": "5", "late_fee_grace_days": -1},
        {"late_fee_enabled": None},
        {"late_fee_grace_days": None},
    ],
)
def test_late_fee_of_a_lease_is_validated(
    api: TestClient, ana: dict[str, str], trees: tuple[Tree, Tree], changes: dict
) -> None:
    response = api.patch(f"/api/leases/{trees[0].lease_id}", headers=ana, json=changes)

    assert response.status_code == 422, response.text


def test_late_fee_can_be_turned_off_and_keeps_its_percentage(
    api: TestClient, ana: dict[str, str], lease: UUID
) -> None:
    body = api.patch(f"/api/leases/{lease}", headers=ana, json={"late_fee_enabled": False}).json()

    assert body["late_fee_enabled"] is False
    assert Decimal(body["late_fee_percent"]) == Decimal("5")


# Isolation


def test_owner_cannot_see_or_waive_another_owners_late_fee(
    api: TestClient, ana: dict[str, str], beto: dict[str, str], lease: UUID
) -> None:
    october = monthly(api, ana, lease).json()

    assert api.get(f"/api/bills/{october['id']}", headers=beto).status_code == 404
    for action in ("waive", "restore"):
        response = api.post(f"/api/bills/{october['id']}/late-fee/{action}", headers=beto)
        assert response.status_code == 404
    assert status(api, ana, october) == "on_time"


def test_another_owners_late_bill_does_not_reach_this_owners_bills(
    api: TestClient,
    ana: dict[str, str],
    beto: dict[str, str],
    lease: UUID,
    trees: tuple[Tree, Tree],
) -> None:
    monthly(api, ana, lease)
    late_fee_on(api, beto, trees[1].lease_id)

    betos = monthly(api, beto, trees[1].lease_id, NOVEMBER).json()

    assert betos["items"] == [RENT_ITEM]


def test_fee_item_cannot_point_at_another_owners_bill(
    api: TestClient,
    ana: dict[str, str],
    beto: dict[str, str],
    lease: UUID,
    two_owners: tuple[UUID, UUID],
    trees: tuple[Tree, Tree],
    api_engine: Engine,
) -> None:
    anas = monthly(api, ana, lease).json()
    betos = monthly(api, beto, trees[1].lease_id).json()

    with (
        pytest.raises(IntegrityError, match="bill_items_late_fee_fk"),
        api_engine.begin() as connection,
    ):
        set_owner_id(connection, two_owners[0])
        connection.execute(
            text(
                "insert into bill_items (owner_id, bill_id, description, amount, "
                "late_fee_of_bill_id) values (:owner, :bill, 'Recargo', 1, :other)"
            ),
            {"owner": two_owners[0], "bill": anas["id"], "other": betos["id"]},
        )


@pytest.mark.parametrize("action", ["waive", "restore"])
def test_waiving_needs_a_session(api: TestClient, action: str) -> None:
    bill_id = "00000000-0000-0000-0000-000000000000"

    assert api.post(f"/api/bills/{bill_id}/late-fee/{action}").status_code == 401
