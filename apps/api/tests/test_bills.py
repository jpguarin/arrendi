"""Issuing bills: the number, one per month, the PDF, and who can see what."""

from concurrent.futures import ThreadPoolExecutor
from datetime import date
from io import BytesIO
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw
from sqlalchemy import Engine, text

from app.dates import today_in_bogota
from app.dependencies import get_storage
from app.main import app
from app.storage import StorageError
from tests.conftest import FakeStorage, MakeToken, Tree, bearer, create_tree

# The trees' leases charge $950.000 and are due on the 5th.
BEFORE_DUE = date(2026, 10, 3)
AFTER_DUE = date(2026, 10, 11)


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
    """Every test here runs on 3 October 2026, with storage standing by."""
    set_today(BEFORE_DUE)


def monthly(api: TestClient, headers: dict[str, str], lease_id: UUID):
    return api.post(f"/api/leases/{lease_id}/bills", headers=headers)


LOCK_ITEM = {"description": "Arreglo de la chapa", "amount": 80000}


def manual_payload(lease_id: UUID, **overrides: object) -> dict:
    return {
        "lease_id": str(lease_id),
        "items": [LOCK_ITEM],
        "due_date": "2026-10-20",
    } | overrides


def numbers(admin_engine: Engine, owner_id: UUID) -> list[int]:
    with admin_engine.connect() as connection:
        return list(
            connection.execute(
                text("select number from bills where owner_id = :id order by number"),
                {"id": owner_id},
            ).scalars()
        )


def next_number(admin_engine: Engine, owner_id: UUID) -> int:
    with admin_engine.connect() as connection:
        return connection.execute(
            text("select next_number from owners where id = :id"), {"id": owner_id}
        ).scalar_one()


def more_leases(admin_engine: Engine, owner_id: UUID, count: int) -> list[UUID]:
    with admin_engine.begin() as connection:
        return [create_tree(connection, owner_id, f"extra{i}").lease_id for i in range(count)]


# The monthly bill


def test_monthly_bill_takes_its_terms_from_the_lease(
    api: TestClient,
    ana: dict[str, str],
    two_owners: tuple[UUID, UUID],
    trees: tuple[Tree, Tree],
    storage: FakeStorage,
) -> None:
    anas, _ = trees

    response = monthly(api, ana, anas.lease_id)

    assert response.status_code == 201
    bill = response.json()
    assert bill | {"id": None, "created_at": None} == {
        "id": None,
        "number": 1,
        "origin": "monthly",
        "period": "2026-10-01",
        "issue_date": "2026-10-03",
        "due_date": "2026-10-05",
        "total": 950000,
        "balance": 950000,
        "status": "pending",
        "last_payment_date": None,
        "last_payment_method": None,
        "lease_id": str(anas.lease_id),
        "unit_id": str(anas.unit_id),
        "unit_name": "Apto ana",
        "tenant_name": "Arrendatario ana",
        "items": [{"description": "Canon de arrendamiento", "amount": 950000}],
        "property_name": "Casa ana",
        "tenant_document_type": "cc",
        "tenant_document_number": None,
        "issuer": {
            "name": "Ana",
            "document_type": "cc",
            "document_number": None,
            "payment_details": None,
        },
        "signed": False,
        "created_at": None,
        "voided_at": None,
        "payments": [],
        "notifications": [],
    }
    # The PDF is stored when the bill is issued, under the owner's folder.
    pdf = storage.objects[f"{two_owners[0]}/bills/{bill['id']}.pdf"]
    assert pdf.startswith(b"%PDF-")
    assert b"0001" in pdf and b"$950.000" in pdf and b"Vence el 5 de octubre de 2026" in pdf
    # The monthly bill says its month and its unit under the rent, and nowhere else.
    assert b"Octubre 2026 \\267 Apto ana" in pdf
    assert pdf.count(b"Apto ana") == 1


def test_pdf_carries_the_owners_details(
    api: TestClient, ana: dict[str, str], trees: tuple[Tree, Tree], storage: FakeStorage
) -> None:
    anas, _ = trees
    api.patch(
        "/api/settings",
        headers=ana,
        json={
            "document_type": "nit",
            "document_number": "900.123.456-7",
            "payment_details": "Nequi 300 123 4567",
        },
    )

    bill = monthly(api, ana, anas.lease_id).json()

    assert bill["issuer"] == {
        "name": "Ana",
        "document_type": "nit",
        "document_number": "900.123.456-7",
        "payment_details": "Nequi 300 123 4567",
    }
    (pdf,) = storage.objects.values()
    assert b"NIT 900.123.456-7" in pdf and b"Pagar a: Nequi 300 123 4567" in pdf


def test_bill_past_its_due_date_is_born_overdue(
    api: TestClient, ana: dict[str, str], trees: tuple[Tree, Tree]
) -> None:
    anas, _ = trees
    set_today(AFTER_DUE)

    bill = monthly(api, ana, anas.lease_id).json()

    assert (bill["issue_date"], bill["due_date"], bill["status"]) == (
        "2026-10-11",
        "2026-10-05",
        "overdue",
    )


def test_bill_due_today_is_still_pending(
    api: TestClient, ana: dict[str, str], trees: tuple[Tree, Tree]
) -> None:
    anas, _ = trees
    set_today(date(2026, 10, 5))

    assert monthly(api, ana, anas.lease_id).json()["status"] == "pending"


def test_one_monthly_bill_per_lease_and_period(
    api: TestClient,
    ana: dict[str, str],
    two_owners: tuple[UUID, UUID],
    trees: tuple[Tree, Tree],
    admin_engine: Engine,
    storage: FakeStorage,
) -> None:
    anas, _ = trees
    monthly(api, ana, anas.lease_id)

    again = monthly(api, ana, anas.lease_id)

    assert again.status_code == 409
    assert again.json()["code"] == "bill_already_exists"
    assert numbers(admin_engine, two_owners[0]) == [1]
    # The refused one did not use up a number or leave a file.
    assert next_number(admin_engine, two_owners[0]) == 2
    assert len(storage.objects) == 1


def test_next_month_gets_its_own_bill(
    api: TestClient, ana: dict[str, str], trees: tuple[Tree, Tree]
) -> None:
    anas, _ = trees
    monthly(api, ana, anas.lease_id)
    set_today(date(2026, 11, 1))

    november = monthly(api, ana, anas.lease_id)

    assert november.status_code == 201
    assert (november.json()["number"], november.json()["period"]) == (2, "2026-11-01")


def test_same_month_at_once_issues_only_one(
    api: TestClient,
    ana: dict[str, str],
    two_owners: tuple[UUID, UUID],
    trees: tuple[Tree, Tree],
    admin_engine: Engine,
) -> None:
    anas, _ = trees

    with ThreadPoolExecutor(max_workers=8) as pool:
        responses = list(pool.map(lambda _: monthly(api, ana, anas.lease_id), range(8)))

    assert sorted(response.status_code for response in responses) == [201] + [409] * 7
    assert numbers(admin_engine, two_owners[0]) == [1]
    assert next_number(admin_engine, two_owners[0]) == 2


def test_changing_the_rent_later_does_not_touch_the_bill(
    api: TestClient, ana: dict[str, str], trees: tuple[Tree, Tree]
) -> None:
    anas, _ = trees
    bill = monthly(api, ana, anas.lease_id).json()

    api.patch(f"/api/leases/{anas.lease_id}", headers=ana, json={"rent": 1_200_000})

    assert api.get(f"/api/bills/{bill['id']}", headers=ana).json()["total"] == 950000


def test_ended_lease_gets_no_bills(
    api: TestClient, ana: dict[str, str], trees: tuple[Tree, Tree]
) -> None:
    anas, _ = trees
    api.post(f"/api/leases/{anas.lease_id}/end", headers=ana)

    for response in (
        monthly(api, ana, anas.lease_id),
        api.post("/api/bills", headers=ana, json=manual_payload(anas.lease_id)),
    ):
        assert response.status_code == 400
        assert response.json()["code"] == "lease_not_active"


# The number


def test_numbers_have_no_gaps_when_issued_at_once(
    api: TestClient,
    ana: dict[str, str],
    beto: dict[str, str],
    two_owners: tuple[UUID, UUID],
    trees: tuple[Tree, Tree],
    admin_engine: Engine,
) -> None:
    anas, betos = trees
    leases = [anas.lease_id, *more_leases(admin_engine, two_owners[0], 11)]

    with ThreadPoolExecutor(max_workers=12) as pool:
        responses = list(pool.map(lambda lease_id: monthly(api, ana, lease_id), leases))

    assert [response.status_code for response in responses] == [201] * 12
    assert sorted(response.json()["number"] for response in responses) == list(range(1, 13))
    assert numbers(admin_engine, two_owners[0]) == list(range(1, 13))
    assert next_number(admin_engine, two_owners[0]) == 13
    # Each owner has their own sequence.
    assert monthly(api, beto, betos.lease_id).json()["number"] == 1


def test_manual_and_monthly_bills_share_the_sequence_at_once(
    api: TestClient,
    ana: dict[str, str],
    two_owners: tuple[UUID, UUID],
    trees: tuple[Tree, Tree],
    admin_engine: Engine,
) -> None:
    anas, _ = trees
    payload = manual_payload(anas.lease_id)

    def issue(index: int):
        if index == 0:
            return monthly(api, ana, anas.lease_id)
        return api.post("/api/bills", headers=ana, json=payload)

    with ThreadPoolExecutor(max_workers=10) as pool:
        responses = list(pool.map(issue, range(10)))

    assert [response.status_code for response in responses] == [201] * 10
    assert numbers(admin_engine, two_owners[0]) == list(range(1, 11))


class FailingStorage(FakeStorage):
    def upload(self, path: str, content: bytes, content_type: str = "") -> None:
        raise StorageError("storage is down")


def test_failed_issue_leaves_no_gap(
    api: TestClient,
    ana: dict[str, str],
    two_owners: tuple[UUID, UUID],
    trees: tuple[Tree, Tree],
    admin_engine: Engine,
    storage: FakeStorage,
) -> None:
    anas, _ = trees
    app.dependency_overrides[get_storage] = lambda: FailingStorage()

    failed = monthly(api, ana, anas.lease_id)

    assert failed.status_code == 503
    assert failed.json()["code"] == "storage_unavailable"
    # Nothing was created and the number is still free.
    assert numbers(admin_engine, two_owners[0]) == []
    assert next_number(admin_engine, two_owners[0]) == 1

    app.dependency_overrides[get_storage] = lambda: storage
    assert monthly(api, ana, anas.lease_id).json()["number"] == 1


# The manual bill


def test_manual_bill_has_its_own_description_amount_and_due_date(
    api: TestClient, ana: dict[str, str], trees: tuple[Tree, Tree], storage: FakeStorage
) -> None:
    anas, _ = trees

    response = api.post("/api/bills", headers=ana, json=manual_payload(anas.lease_id))

    assert response.status_code == 201
    bill = response.json()
    assert (bill["origin"], bill["period"], bill["total"], bill["due_date"], bill["status"]) == (
        "manual",
        None,
        80000,
        "2026-10-20",
        "pending",
    )
    assert bill["items"] == [LOCK_ITEM]
    (pdf,) = storage.objects.values()
    assert b"Arreglo de la chapa" in pdf and b"$80.000" in pdf
    # The unit goes in the heading, after the number and the date; no line repeats it.
    assert b"3 de octubre de 2026 \\267 Apto ana" in pdf
    assert pdf.count(b"Apto ana") == 1


def test_manual_bill_adds_up_its_items_in_the_order_given(
    api: TestClient, ana: dict[str, str], trees: tuple[Tree, Tree], storage: FakeStorage
) -> None:
    anas, _ = trees
    items = [
        LOCK_ITEM,
        {"description": "  Destape de la tubería  ", "amount": 120000},
        {"description": "Pintura", "amount": 45000},
    ]

    response = api.post("/api/bills", headers=ana, json=manual_payload(anas.lease_id, items=items))

    assert response.status_code == 201, response.text
    bill = response.json()
    expected = [
        LOCK_ITEM,
        {"description": "Destape de la tubería", "amount": 120000},
        {"description": "Pintura", "amount": 45000},
    ]
    assert bill["items"] == expected
    assert (bill["total"], bill["balance"], bill["due_date"]) == (245000, 245000, "2026-10-20")
    assert api.get(f"/api/bills/{bill['id']}", headers=ana).json()["items"] == expected
    (pdf,) = storage.objects.values()
    for text_in_pdf in (b"Arreglo de la chapa", b"Pintura", b"$80.000", b"$120.000", b"$45.000"):
        assert text_in_pdf in pdf
    assert b"$245.000" in pdf
    # One due date for the whole bill.
    assert pdf.count(b"Vence el") == 1


def test_manual_bill_takes_up_to_ten_items(
    api: TestClient, ana: dict[str, str], trees: tuple[Tree, Tree], storage: FakeStorage
) -> None:
    anas, _ = trees
    items = [{"description": f"Concepto {n}", "amount": 1000 * n} for n in range(1, 11)]

    bill = api.post(
        "/api/bills", headers=ana, json=manual_payload(anas.lease_id, items=items)
    ).json()

    assert bill["items"] == items
    assert bill["total"] == 55000


def test_several_manual_bills_fit_in_the_same_month(
    api: TestClient, ana: dict[str, str], trees: tuple[Tree, Tree]
) -> None:
    anas, _ = trees
    monthly(api, ana, anas.lease_id)

    first = api.post("/api/bills", headers=ana, json=manual_payload(anas.lease_id))
    second = api.post("/api/bills", headers=ana, json=manual_payload(anas.lease_id))

    assert (first.json()["number"], second.json()["number"]) == (2, 3)


@pytest.mark.parametrize(
    "overrides",
    [
        {"items": [LOCK_ITEM | {"amount": 0}]},
        {"items": [LOCK_ITEM | {"amount": -1}]},
        {"items": [LOCK_ITEM | {"amount": 80000.5}]},
        {"items": [LOCK_ITEM | {"amount": "80000"}]},
        {"items": [LOCK_ITEM | {"description": "   "}]},
        {"items": [LOCK_ITEM | {"description": "x" * 201}]},
        # One bad item among good ones is enough.
        {"items": [LOCK_ITEM, LOCK_ITEM | {"amount": 0}]},
        {"items": []},
        {"items": [LOCK_ITEM] * 11},
        {"items": None},
        # The old shape, with one description and one amount, is no longer a bill.
        {"items": None, "description": "Arreglo de la chapa", "amount": 80000},
        {"due_date": "20 de octubre"},
    ],
)
def test_manual_bill_is_validated(
    api: TestClient, ana: dict[str, str], trees: tuple[Tree, Tree], overrides: dict
) -> None:
    anas, _ = trees

    response = api.post("/api/bills", headers=ana, json=manual_payload(anas.lease_id, **overrides))

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"


# The deposit: charged once, next to the rent, on the first monthly bill of the lease.

RENT_ITEM = {"description": "Canon de arrendamiento", "amount": 950000}
DEPOSIT_ITEM = {"description": "Depósito", "amount": 500000}


def with_deposit(api: TestClient, headers: dict[str, str], lease_id: UUID, **changes) -> None:
    """Gives the lease a deposit of $500.000 to charge, unless `changes` say otherwise."""
    body = {"deposit": 500000, "charge_deposit": True} | changes
    assert api.patch(f"/api/leases/{lease_id}", headers=headers, json=body).status_code == 200


def test_first_monthly_bill_charges_the_deposit_as_its_own_item(
    api: TestClient, ana: dict[str, str], trees: tuple[Tree, Tree], storage: FakeStorage
) -> None:
    anas, _ = trees
    with_deposit(api, ana, anas.lease_id)

    bill = monthly(api, ana, anas.lease_id).json()

    assert bill["items"] == [RENT_ITEM, DEPOSIT_ITEM]
    assert (bill["total"], bill["balance"]) == (1450000, 1450000)
    # The detail and the list say the same as the answer to issuing.
    assert api.get(f"/api/bills/{bill['id']}", headers=ana).json()["items"] == bill["items"]
    assert api.get("/api/bills", headers=ana).json()[0]["total"] == 1450000
    (pdf,) = storage.objects.values()
    for text_in_pdf in (b"Canon de arrendamiento", b"$950.000", b"$500.000", b"$1.450.000"):
        assert text_in_pdf in pdf
    # "Depósito" has an accent, which the PDF encodes; its plain half is enough.
    assert b"sito" in pdf


def test_later_monthly_bills_do_not_charge_the_deposit_again(
    api: TestClient, ana: dict[str, str], trees: tuple[Tree, Tree]
) -> None:
    anas, _ = trees
    with_deposit(api, ana, anas.lease_id)
    monthly(api, ana, anas.lease_id)
    set_today(date(2026, 11, 1))

    november = monthly(api, ana, anas.lease_id).json()

    assert november["items"] == [RENT_ITEM]
    assert november["total"] == 950000


def test_bill_that_replaces_a_voided_first_one_charges_the_deposit_again(
    api: TestClient, ana: dict[str, str], trees: tuple[Tree, Tree]
) -> None:
    anas, _ = trees
    with_deposit(api, ana, anas.lease_id)
    first = monthly(api, ana, anas.lease_id).json()
    api.post(f"/api/bills/{first['id']}/void", headers=ana)

    second = monthly(api, ana, anas.lease_id).json()

    assert second["items"] == [RENT_ITEM, DEPOSIT_ITEM]
    assert second["total"] == 1450000


@pytest.mark.parametrize(
    "changes",
    [{"charge_deposit": False}, {"deposit": 0}, {"deposit": None}],
    ids=["switched off", "zero", "none"],
)
def test_deposit_is_not_charged_when_there_is_nothing_to_charge(
    api: TestClient, ana: dict[str, str], trees: tuple[Tree, Tree], changes: dict
) -> None:
    anas, _ = trees
    with_deposit(api, ana, anas.lease_id, **changes)

    bill = monthly(api, ana, anas.lease_id).json()

    assert bill["items"] == [RENT_ITEM]
    assert bill["total"] == 950000


def test_lease_that_was_never_asked_to_does_not_charge_its_deposit(
    api: TestClient, ana: dict[str, str], trees: tuple[Tree, Tree], admin_engine: Engine
) -> None:
    # A lease from before the switch existed: it has a deposit, and the database default.
    anas, _ = trees
    with admin_engine.begin() as connection:
        connection.execute(
            text("update leases set deposit = 500000 where id = :id"), {"id": anas.lease_id}
        )

    assert monthly(api, ana, anas.lease_id).json()["items"] == [RENT_ITEM]


def test_manual_bills_neither_charge_the_deposit_nor_count_as_the_first(
    api: TestClient, ana: dict[str, str], trees: tuple[Tree, Tree]
) -> None:
    anas, _ = trees
    with_deposit(api, ana, anas.lease_id)

    manual = api.post("/api/bills", headers=ana, json=manual_payload(anas.lease_id)).json()
    month = monthly(api, ana, anas.lease_id).json()

    assert manual["items"] == [LOCK_ITEM]
    assert month["items"] == [RENT_ITEM, DEPOSIT_ITEM]


def test_changing_the_deposit_later_does_not_touch_the_bill(
    api: TestClient, ana: dict[str, str], trees: tuple[Tree, Tree]
) -> None:
    anas, _ = trees
    with_deposit(api, ana, anas.lease_id)
    bill = monthly(api, ana, anas.lease_id).json()

    with_deposit(api, ana, anas.lease_id, deposit=900000)

    after = api.get(f"/api/bills/{bill['id']}", headers=ana).json()
    assert (after["items"], after["total"]) == ([RENT_ITEM, DEPOSIT_ITEM], 1450000)


def test_first_bill_at_once_charges_the_deposit_only_once(
    api: TestClient, ana: dict[str, str], trees: tuple[Tree, Tree], admin_engine: Engine
) -> None:
    anas, _ = trees
    with_deposit(api, ana, anas.lease_id)

    with ThreadPoolExecutor(max_workers=4) as pool:
        codes = list(pool.map(lambda _: monthly(api, ana, anas.lease_id).status_code, range(4)))

    assert sorted(codes) == [201, 409, 409, 409]
    with admin_engine.connect() as connection:
        items = connection.execute(
            text("select description from bill_items order by position")
        ).scalars()
        assert list(items) == ["Canon de arrendamiento", "Depósito"]


# The items of the lease: charged every month, after the rent and before the deposit.

FEE_ITEM = {"description": "Administración", "amount": 200000}
PARKING_ITEM = {"description": "Parqueadero", "amount": 80000}


def set_items(api: TestClient, headers: dict[str, str], lease_id: UUID, items: list) -> None:
    response = api.patch(f"/api/leases/{lease_id}", headers=headers, json={"items": items})
    assert response.status_code == 200, response.text


def test_monthly_bill_charges_the_rent_and_the_items_of_the_lease(
    api: TestClient, ana: dict[str, str], trees: tuple[Tree, Tree], storage: FakeStorage
) -> None:
    anas, _ = trees
    set_items(api, ana, anas.lease_id, [FEE_ITEM, PARKING_ITEM])

    bill = monthly(api, ana, anas.lease_id).json()

    assert bill["items"] == [RENT_ITEM, FEE_ITEM, PARKING_ITEM]
    assert (bill["total"], bill["balance"]) == (1230000, 1230000)
    assert api.get("/api/bills", headers=ana).json()[0]["total"] == 1230000
    (pdf,) = storage.objects.values()
    for text_in_pdf in (b"Parqueadero", b"$950.000", b"$200.000", b"$80.000", b"$1.230.000"):
        assert text_in_pdf in pdf


def test_every_monthly_bill_charges_the_items_and_only_the_first_the_deposit(
    api: TestClient, ana: dict[str, str], trees: tuple[Tree, Tree]
) -> None:
    anas, _ = trees
    set_items(api, ana, anas.lease_id, [FEE_ITEM])
    with_deposit(api, ana, anas.lease_id)

    october = monthly(api, ana, anas.lease_id).json()
    set_today(date(2026, 11, 1))
    november = monthly(api, ana, anas.lease_id).json()

    assert october["items"] == [RENT_ITEM, FEE_ITEM, DEPOSIT_ITEM]
    assert october["total"] == 1650000
    assert november["items"] == [RENT_ITEM, FEE_ITEM]
    assert november["total"] == 1150000


def test_changing_the_items_of_the_lease_does_not_touch_issued_bills(
    api: TestClient, ana: dict[str, str], trees: tuple[Tree, Tree]
) -> None:
    anas, _ = trees
    set_items(api, ana, anas.lease_id, [FEE_ITEM])
    october = monthly(api, ana, anas.lease_id).json()

    set_items(api, ana, anas.lease_id, [PARKING_ITEM])

    after = api.get(f"/api/bills/{october['id']}", headers=ana).json()
    assert (after["items"], after["total"]) == ([RENT_ITEM, FEE_ITEM], 1150000)
    # The next one takes the lease as it is then.
    set_today(date(2026, 11, 1))
    assert monthly(api, ana, anas.lease_id).json()["items"] == [RENT_ITEM, PARKING_ITEM]


def test_manual_bills_do_not_charge_the_items_of_the_lease(
    api: TestClient, ana: dict[str, str], trees: tuple[Tree, Tree]
) -> None:
    anas, _ = trees
    set_items(api, ana, anas.lease_id, [FEE_ITEM])

    manual = api.post("/api/bills", headers=ana, json=manual_payload(anas.lease_id)).json()

    assert (manual["items"], manual["total"]) == ([LOCK_ITEM], 80000)


# The signature: the owner's when the bill is issued, kept on the bill.

IMAGE = b"/Subtype /Image"


def sign(api: TestClient, storage: FakeStorage, headers: dict[str, str]) -> str:
    """Uploads a signature for the owner and returns the path it ends up stored at."""
    picture = Image.new("RGBA", (300, 100), (0, 0, 0, 0))
    strokes = [(10, 80), (150, 20), (290, 80)]
    ImageDraw.Draw(picture).line(strokes, fill=(20, 38, 76, 255), width=5)
    content = BytesIO()
    picture.save(content, "PNG")
    before = set(storage.objects)
    path = api.post(
        "/api/settings/signature/upload-url",
        headers=headers,
        json={"filename": "firma.png", "content_type": "image/png", "size": content.tell()},
    ).json()["path"]
    storage.upload(path, content.getvalue())
    confirmed = api.post("/api/settings/signature", headers=headers, json={"path": path})
    assert confirmed.status_code == 200, confirmed.text
    (stored,) = set(storage.objects) - before
    return stored


def pdf_of(storage: FakeStorage, bill: dict) -> bytes:
    (path,) = [path for path in storage.objects if path.endswith(f"/bills/{bill['id']}.pdf")]
    return storage.objects[path]


def test_bill_is_issued_with_the_owners_signature(
    api: TestClient, ana: dict[str, str], trees: tuple[Tree, Tree], storage: FakeStorage
) -> None:
    anas, _ = trees
    unsigned = api.post("/api/bills", headers=ana, json=manual_payload(anas.lease_id)).json()
    sign(api, storage, ana)

    month = monthly(api, ana, anas.lease_id).json()
    manual = api.post("/api/bills", headers=ana, json=manual_payload(anas.lease_id)).json()

    assert (unsigned["signed"], month["signed"], manual["signed"]) == (False, True, True)
    assert IMAGE not in pdf_of(storage, unsigned)
    assert IMAGE in pdf_of(storage, month) and IMAGE in pdf_of(storage, manual)
    # Signing later does not reach the bill issued before.
    assert api.get(f"/api/bills/{unsigned['id']}", headers=ana).json()["signed"] is False


def test_changing_or_removing_the_signature_later_does_not_touch_the_bill(
    api: TestClient, ana: dict[str, str], trees: tuple[Tree, Tree], storage: FakeStorage
) -> None:
    anas, _ = trees
    signed_with = sign(api, storage, ana)
    bill = monthly(api, ana, anas.lease_id).json()
    issued = pdf_of(storage, bill)

    replaced_by = sign(api, storage, ana)
    api.delete("/api/settings/signature", headers=ana)

    assert api.get(f"/api/bills/{bill['id']}", headers=ana).json()["signed"] is True
    assert pdf_of(storage, bill) == issued
    # Its signature is still there, and the one no bill used is gone.
    assert signed_with in storage.objects and replaced_by not in storage.objects
    # Voiding draws the PDF again, with the signature the bill was issued with.
    api.post(f"/api/bills/{bill['id']}/void", headers=ana)
    voided = pdf_of(storage, bill)
    assert b"ANULADA" in voided and IMAGE in voided


def test_voiding_survives_a_signature_that_cannot_be_fetched(
    api: TestClient, ana: dict[str, str], trees: tuple[Tree, Tree], storage: FakeStorage
) -> None:
    anas, _ = trees
    signed_with = sign(api, storage, ana)
    bill = monthly(api, ana, anas.lease_id).json()
    del storage.objects[signed_with]

    response = api.post(f"/api/bills/{bill['id']}/void", headers=ana)

    assert response.status_code == 200
    assert response.json()["status"] == "voided"
    assert b"ANULADA" in pdf_of(storage, bill)


def test_bill_is_not_issued_without_the_signature_it_should_carry(
    api: TestClient,
    ana: dict[str, str],
    two_owners: tuple[UUID, UUID],
    trees: tuple[Tree, Tree],
    storage: FakeStorage,
    admin_engine: Engine,
) -> None:
    anas, _ = trees
    signed_with = sign(api, storage, ana)
    del storage.objects[signed_with]

    response = monthly(api, ana, anas.lease_id)

    # Storage lost the file: better no bill than one that went out unsigned by accident.
    assert response.status_code == 503
    assert numbers(admin_engine, two_owners[0]) == []
    assert next_number(admin_engine, two_owners[0]) == 1


# Payment details: the bill's own, else the lease's, else the owner's. Kept on the bill.


def set_details(api: TestClient, headers: dict[str, str], lease_id: UUID | None, details) -> None:
    """Sets the owner's payment details, or the lease's when one is given."""
    path = f"/api/leases/{lease_id}" if lease_id else "/api/settings"
    assert api.patch(path, headers=headers, json={"payment_details": details}).status_code == 200


def test_bill_without_its_own_details_takes_the_leases(
    api: TestClient, ana: dict[str, str], trees: tuple[Tree, Tree], storage: FakeStorage
) -> None:
    anas, _ = trees
    set_details(api, ana, None, "Nequi de Ajustes")
    set_details(api, ana, anas.lease_id, "Daviplata del contrato")

    month = monthly(api, ana, anas.lease_id).json()
    manual = api.post("/api/bills", headers=ana, json=manual_payload(anas.lease_id)).json()

    for bill in (month, manual):
        assert bill["issuer"]["payment_details"] == "Daviplata del contrato"
    for pdf in storage.objects.values():
        assert b"Pagar a: Daviplata del contrato" in pdf and b"Nequi de Ajustes" not in pdf


def test_manual_bill_can_carry_its_own_details(
    api: TestClient, ana: dict[str, str], trees: tuple[Tree, Tree], storage: FakeStorage
) -> None:
    anas, _ = trees
    set_details(api, ana, None, "Nequi de Ajustes")
    set_details(api, ana, anas.lease_id, "Daviplata del contrato")

    response = api.post(
        "/api/bills",
        headers=ana,
        json=manual_payload(anas.lease_id, payment_details="  En efectivo al plomero  "),
    )

    assert response.status_code == 201
    assert response.json()["issuer"]["payment_details"] == "En efectivo al plomero"
    (pdf,) = storage.objects.values()
    assert b"Pagar a: En efectivo al plomero" in pdf and b"Daviplata" not in pdf


@pytest.mark.parametrize("blank", [None, "", "   "])
def test_blank_details_on_a_manual_bill_fall_back(
    api: TestClient, ana: dict[str, str], trees: tuple[Tree, Tree], blank: str | None
) -> None:
    anas, _ = trees
    set_details(api, ana, None, "Nequi de Ajustes")

    bill = api.post(
        "/api/bills", headers=ana, json=manual_payload(anas.lease_id, payment_details=blank)
    ).json()

    assert bill["issuer"]["payment_details"] == "Nequi de Ajustes"


def test_clearing_the_leases_details_goes_back_to_the_owners(
    api: TestClient, ana: dict[str, str], trees: tuple[Tree, Tree]
) -> None:
    anas, _ = trees
    set_details(api, ana, None, "Nequi de Ajustes")
    set_details(api, ana, anas.lease_id, "Daviplata del contrato")
    set_details(api, ana, anas.lease_id, " ")

    bill = monthly(api, ana, anas.lease_id).json()

    assert bill["issuer"]["payment_details"] == "Nequi de Ajustes"


def test_changing_the_details_later_does_not_touch_the_bill(
    api: TestClient, ana: dict[str, str], trees: tuple[Tree, Tree], storage: FakeStorage
) -> None:
    anas, _ = trees
    set_details(api, ana, None, "Nequi de Ajustes")
    bill = monthly(api, ana, anas.lease_id).json()

    set_details(api, ana, None, "Otro banco")
    set_details(api, ana, anas.lease_id, "Daviplata del contrato")

    after = api.get(f"/api/bills/{bill['id']}", headers=ana).json()
    assert after["issuer"]["payment_details"] == "Nequi de Ajustes"
    # Voiding draws the PDF again, with what the bill was issued with.
    api.post(f"/api/bills/{bill['id']}/void", headers=ana)
    (pdf,) = storage.objects.values()
    assert b"ANULADA" in pdf and b"Pagar a: Nequi de Ajustes" in pdf


def test_manual_bill_details_are_validated(
    api: TestClient, ana: dict[str, str], trees: tuple[Tree, Tree]
) -> None:
    anas, _ = trees

    response = api.post(
        "/api/bills", headers=ana, json=manual_payload(anas.lease_id, payment_details="x" * 501)
    )

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"


# Reading


@pytest.fixture
def history(
    api: TestClient, ana: dict[str, str], two_owners: tuple[UUID, UUID], admin_engine: Engine
) -> dict[str, dict]:
    """Ana's bills: September and October for one unit, October and a repair for another."""
    with admin_engine.begin() as connection:
        one = create_tree(connection, two_owners[0], "uno")
        two = create_tree(connection, two_owners[0], "dos")
    set_today(date(2026, 9, 1))
    september = monthly(api, ana, one.lease_id).json()
    set_today(BEFORE_DUE)
    october_one = monthly(api, ana, one.lease_id).json()
    october_two = monthly(api, ana, two.lease_id).json()
    repair = api.post(
        "/api/bills", headers=ana, json=manual_payload(two.lease_id, due_date="2026-11-10")
    ).json()
    with admin_engine.begin() as connection:
        connection.execute(
            text("update bills set status = 'paid' where id = :id"), {"id": september["id"]}
        )
        connection.execute(
            text("update bills set status = 'voided', voided_at = now() where id = :id"),
            {"id": october_two["id"]},
        )
    return {
        "september": september,
        "october_one": october_one,
        "october_two": october_two,
        "repair": repair,
    }


def listed(api: TestClient, headers: dict[str, str], **params: object) -> list[int]:
    response = api.get("/api/bills", headers=headers, params=params)
    assert response.status_code == 200
    return [bill["number"] for bill in response.json()]


def test_list_goes_from_newest_month_and_hides_voided_bills(
    api: TestClient, ana: dict[str, str], history: dict[str, dict]
) -> None:
    # The repair is due in November; October's second bill is voided.
    assert listed(api, ana) == [4, 2, 1]


def test_list_filters_by_status(
    api: TestClient, ana: dict[str, str], history: dict[str, dict]
) -> None:
    assert listed(api, ana, status="receivable") == [4, 2]
    assert listed(api, ana, status="paid") == [1]
    assert listed(api, ana, status="voided") == [3]
    assert api.get("/api/bills", headers=ana, params={"status": "pending"}).status_code == 422


def test_list_filters_by_unit_and_dates(
    api: TestClient, ana: dict[str, str], history: dict[str, dict]
) -> None:
    unit_one = history["october_one"]["unit_id"]

    assert listed(api, ana, unit_id=unit_one) == [2, 1]
    assert listed(api, ana, unit_id=str(uuid4())) == []
    assert listed(api, ana, **{"from": "2026-10-01", "to": "2026-10-31"}) == [2]
    assert listed(api, ana, **{"from": "2026-10-02"}) == [4]
    assert listed(api, ana, to="2026-09-30") == [1]


def test_list_rows_say_who_owes(
    api: TestClient, ana: dict[str, str], history: dict[str, dict]
) -> None:
    row = api.get("/api/bills", headers=ana, params={"status": "paid"}).json()[0]

    assert (row["unit_name"], row["tenant_name"], row["status"], row["balance"]) == (
        "Apto uno",
        "Arrendatario uno",
        "paid",
        950000,
    )
    assert "items" not in row


def test_lease_shows_its_latest_bills(
    api: TestClient, ana: dict[str, str], history: dict[str, dict]
) -> None:
    one = api.get(f"/api/leases/{history['october_one']['lease_id']}", headers=ana).json()
    two = api.get(f"/api/leases/{history['repair']['lease_id']}", headers=ana).json()

    assert [bill["number"] for bill in one["recent_bills"]] == [2, 1]
    # Voided ones too: it is the history of the lease.
    assert [(bill["number"], bill["status"]) for bill in two["recent_bills"]] == [
        (4, "pending"),
        (3, "voided"),
    ]


def test_pdf_link_is_temporary(
    api: TestClient, ana: dict[str, str], two_owners: tuple[UUID, UUID], trees: tuple[Tree, Tree]
) -> None:
    anas, _ = trees
    bill = monthly(api, ana, anas.lease_id).json()

    response = api.get(f"/api/bills/{bill['id']}/pdf", headers=ana)

    assert response.status_code == 200
    assert response.json() == {
        "url": f"https://storage.test/download/{two_owners[0]}/bills/{bill['id']}.pdf"
        "?token=signed&expires_in=300",
        "name": "cuenta-de-cobro-0001.pdf",
        "expires_in": 300,
    }


# Voiding


def set_status(admin_engine: Engine, bill_id: str, status: str) -> None:
    with admin_engine.begin() as connection:
        connection.execute(
            text("update bills set status = :status where id = :id"),
            {"status": status, "id": bill_id},
        )


def test_voided_bill_keeps_its_number_and_its_pdf_gets_marked(
    api: TestClient, ana: dict[str, str], trees: tuple[Tree, Tree], storage: FakeStorage
) -> None:
    anas, _ = trees
    bill = monthly(api, ana, anas.lease_id).json()
    assert b"ANULADA" not in next(iter(storage.objects.values()))

    response = api.post(f"/api/bills/{bill['id']}/void", headers=ana)

    assert response.status_code == 200
    voided = response.json()
    assert (voided["status"], voided["number"]) == ("voided", 1)
    assert voided["voided_at"] is not None
    # Same file, replaced.
    (pdf,) = storage.objects.values()
    assert b"ANULADA" in pdf and b"0001" in pdf


def test_after_voiding_the_same_month_gets_a_new_number(
    api: TestClient,
    ana: dict[str, str],
    two_owners: tuple[UUID, UUID],
    trees: tuple[Tree, Tree],
    admin_engine: Engine,
) -> None:
    anas, _ = trees
    first = monthly(api, ana, anas.lease_id).json()
    api.post(f"/api/bills/{first['id']}/void", headers=ana)

    second = monthly(api, ana, anas.lease_id)

    assert second.status_code == 201
    assert (second.json()["number"], second.json()["period"]) == (2, "2026-10-01")
    assert numbers(admin_engine, two_owners[0]) == [1, 2]


def test_overdue_bill_can_be_voided(
    api: TestClient, ana: dict[str, str], trees: tuple[Tree, Tree]
) -> None:
    anas, _ = trees
    set_today(AFTER_DUE)
    bill = monthly(api, ana, anas.lease_id).json()

    assert api.post(f"/api/bills/{bill['id']}/void", headers=ana).json()["status"] == "voided"


@pytest.mark.parametrize("status", ["partial", "paid"])
def test_bill_with_payments_cannot_be_voided(
    api: TestClient,
    ana: dict[str, str],
    trees: tuple[Tree, Tree],
    admin_engine: Engine,
    storage: FakeStorage,
    status: str,
) -> None:
    anas, _ = trees
    bill = monthly(api, ana, anas.lease_id).json()
    # There is no payments table until stage 5: the status is what says it has payments.
    set_status(admin_engine, bill["id"], status)

    response = api.post(f"/api/bills/{bill['id']}/void", headers=ana)

    assert response.status_code == 400
    assert response.json()["code"] == "bill_has_payments"
    assert api.get(f"/api/bills/{bill['id']}", headers=ana).json()["status"] == status
    assert b"ANULADA" not in next(iter(storage.objects.values()))


def test_bill_cannot_be_voided_twice(
    api: TestClient, ana: dict[str, str], trees: tuple[Tree, Tree]
) -> None:
    anas, _ = trees
    bill = monthly(api, ana, anas.lease_id).json()
    api.post(f"/api/bills/{bill['id']}/void", headers=ana)

    again = api.post(f"/api/bills/{bill['id']}/void", headers=ana)

    assert again.status_code == 400
    assert again.json()["code"] == "bill_already_voided"


def test_voiding_survives_a_storage_failure(
    api: TestClient, ana: dict[str, str], trees: tuple[Tree, Tree], storage: FakeStorage
) -> None:
    anas, _ = trees
    bill = monthly(api, ana, anas.lease_id).json()
    app.dependency_overrides[get_storage] = lambda: FailingStorage()

    response = api.post(f"/api/bills/{bill['id']}/void", headers=ana)

    assert response.status_code == 200
    assert api.get(f"/api/bills/{bill['id']}", headers=ana).json()["status"] == "voided"


def test_owner_cannot_void_another_owners_bill(
    api: TestClient,
    ana: dict[str, str],
    beto: dict[str, str],
    trees: tuple[Tree, Tree],
    storage: FakeStorage,
) -> None:
    _, betos = trees
    bill = monthly(api, beto, betos.lease_id).json()

    response = api.post(f"/api/bills/{bill['id']}/void", headers=ana)

    assert response.status_code == 404
    assert api.get(f"/api/bills/{bill['id']}", headers=beto).json()["status"] == "pending"
    assert b"ANULADA" not in next(iter(storage.objects.values()))
    assert api.post(f"/api/bills/{bill['id']}/void").status_code == 401


# Isolation


def test_bills_need_a_session(api: TestClient, trees: tuple[Tree, Tree]) -> None:
    anas, _ = trees
    bill_id = uuid4()

    for response in (
        api.get("/api/bills"),
        api.post("/api/bills", json=manual_payload(anas.lease_id)),
        api.post(f"/api/leases/{anas.lease_id}/bills"),
        api.get(f"/api/bills/{bill_id}"),
        api.get(f"/api/bills/{bill_id}/pdf"),
    ):
        assert response.status_code == 401


def test_owner_cannot_bill_another_owners_lease(
    api: TestClient,
    ana: dict[str, str],
    two_owners: tuple[UUID, UUID],
    trees: tuple[Tree, Tree],
    admin_engine: Engine,
    storage: FakeStorage,
) -> None:
    _, betos = trees

    for response in (
        monthly(api, ana, betos.lease_id),
        api.post("/api/bills", headers=ana, json=manual_payload(betos.lease_id)),
    ):
        assert response.status_code == 404
        assert response.json()["code"] == "not_found"

    assert numbers(admin_engine, two_owners[1]) == []
    assert next_number(admin_engine, two_owners[0]) == 1
    assert storage.objects == {}


def test_owner_cannot_read_another_owners_bills(
    api: TestClient, ana: dict[str, str], beto: dict[str, str], trees: tuple[Tree, Tree]
) -> None:
    anas, betos = trees
    betos_bill = monthly(api, beto, betos.lease_id).json()
    monthly(api, ana, anas.lease_id)

    assert api.get(f"/api/bills/{betos_bill['id']}", headers=ana).status_code == 404
    assert api.get(f"/api/bills/{betos_bill['id']}/pdf", headers=ana).status_code == 404
    # Ana's list has only her own bill, also when she asks for Beto's unit.
    assert [bill["unit_name"] for bill in api.get("/api/bills", headers=ana).json()] == ["Apto ana"]
    assert listed(api, ana, unit_id=str(betos.unit_id)) == []
