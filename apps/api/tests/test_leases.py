from concurrent.futures import ThreadPoolExecutor
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

from tests.conftest import MakeToken, Tree, bearer

LUISA = {"name": "Luisa Gómez", "email": "luisa.gomez@example.com"}
TERMS = {"rent": 950000, "due_day": 5, "start_date": "2026-01-01"}


@pytest.fixture
def ana(two_owners: tuple[UUID, UUID], make_token: MakeToken) -> dict[str, str]:
    return bearer(make_token(two_owners[0]))


@pytest.fixture
def beto(two_owners: tuple[UUID, UUID], make_token: MakeToken) -> dict[str, str]:
    return bearer(make_token(two_owners[1]))


@pytest.fixture
def vacant_unit(api: TestClient, ana: dict[str, str]) -> dict:
    """A unit of Ana's with no lease, in its own property."""
    casa = api.post("/api/properties", json={"name": "Casa", "type": "house"}, headers=ana).json()
    return api.post(
        f"/api/properties/{casa['id']}/units",
        json={"name": "Apto 1", "use": "residential"},
        headers=ana,
    ).json() | {"property_name": "Casa"}


def lease_count(admin_engine: Engine, unit_id: object) -> int:
    with admin_engine.connect() as connection:
        return connection.execute(
            text("select count(*) from leases where unit_id = :id"), {"id": unit_id}
        ).scalar_one()


def tenant_count(admin_engine: Engine, owner_id: UUID) -> int:
    with admin_engine.connect() as connection:
        return connection.execute(
            text("select count(*) from tenants where owner_id = :id"), {"id": owner_id}
        ).scalar_one()


# Create


def test_create_a_lease_with_a_new_tenant(
    api: TestClient, ana: dict[str, str], vacant_unit: dict
) -> None:
    response = api.post(
        "/api/leases",
        json=TERMS
        | {
            "unit_id": vacant_unit["id"],
            "tenant": LUISA
            | {"document_type": "nit", "document_number": " 900.123.456-7 ", "phone": ""},
            "end_date": "2026-12-31",
            "deposit": 950000,
        },
        headers=ana,
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body == {
        "id": body["id"],
        "status": "active",
        "rent": 950000,
        "due_day": 5,
        "start_date": "2026-01-01",
        "end_date": "2026-12-31",
        "deposit": 950000,
        "auto_send": True,
        "charge_deposit": True,
        "items": [],
        "late_fee_enabled": False,
        "late_fee_percent": None,
        "late_fee_grace_days": 0,
        "payment_details": None,
        "document_name": None,
        "document_uploaded_at": None,
        "unit": {
            "id": vacant_unit["id"],
            "name": "Apto 1",
            "use": "residential",
            "property_id": vacant_unit["property_id"],
            "property_name": "Casa",
        },
        "tenant": {
            "id": body["tenant"]["id"],
            "name": "Luisa Gómez",
            "email": "luisa.gomez@example.com",
            "document_type": "nit",
            "document_number": "900.123.456-7",
            "phone": None,
        },
        "recent_bills": [],
    }


def test_the_new_lease_can_be_read_and_shows_on_the_unit(
    api: TestClient, ana: dict[str, str], vacant_unit: dict
) -> None:
    created = api.post(
        "/api/leases", json=TERMS | {"unit_id": vacant_unit["id"], "tenant": LUISA}, headers=ana
    ).json()

    response = api.get(f"/api/leases/{created['id']}", headers=ana)
    [unit] = api.get("/api/properties", headers=ana).json()[0]["units"]

    assert response.status_code == 200
    assert response.json() == created
    assert unit["status"] == "up_to_date"
    assert unit["active_lease"] == {
        "id": created["id"],
        "tenant_name": "Luisa Gómez",
        "rent": 950000,
    }


def test_create_a_lease_with_an_existing_tenant(
    api: TestClient,
    ana: dict[str, str],
    vacant_unit: dict,
    trees: tuple[Tree, Tree],
    two_owners: tuple[UUID, UUID],
    admin_engine: Engine,
) -> None:
    anas, _ = trees

    response = api.post(
        "/api/leases",
        json=TERMS | {"unit_id": vacant_unit["id"], "tenant_id": str(anas.tenant_id)},
        headers=ana,
    )

    assert response.status_code == 201, response.text
    assert response.json()["tenant"]["id"] == str(anas.tenant_id)
    assert tenant_count(admin_engine, two_owners[0]) == 1


@pytest.mark.parametrize(
    "changes",
    [
        {"rent": 0},
        {"rent": -1},
        {"rent": 950000.5},
        {"rent": "950000"},
        {"due_day": 0},
        {"due_day": 29},
        {"start_date": "01/01/2026"},
        {"deposit": -1},
        {"tenant": {"name": "Luisa", "email": "no-es-un-correo"}},
        {"tenant": {"name": " ", "email": "luisa@example.com"}},
        {"tenant": {"name": "Luisa"}},
        {"tenant": None},
        {"tenant_id": str(uuid4())},  # both a new tenant and an existing one
    ],
)
def test_create_rejects_invalid_data(
    api: TestClient,
    ana: dict[str, str],
    vacant_unit: dict,
    admin_engine: Engine,
    changes: dict[str, object],
) -> None:
    payload = TERMS | {"unit_id": vacant_unit["id"], "tenant": LUISA} | changes

    response = api.post("/api/leases", json=payload, headers=ana)

    assert response.status_code == 422, response.text
    assert lease_count(admin_engine, vacant_unit["id"]) == 0


@pytest.mark.parametrize("end_date", ["2026-01-01", "2025-12-31"])
def test_end_date_must_be_after_the_start(
    api: TestClient,
    ana: dict[str, str],
    vacant_unit: dict,
    two_owners: tuple[UUID, UUID],
    admin_engine: Engine,
    end_date: str,
) -> None:
    response = api.post(
        "/api/leases",
        json=TERMS | {"unit_id": vacant_unit["id"], "tenant": LUISA, "end_date": end_date},
        headers=ana,
    )

    assert response.status_code == 422
    assert response.json() == {
        "detail": "La fecha de fin debe ser posterior a la de inicio.",
        "code": "invalid_lease_dates",
    }
    # Nothing is left behind, not even the tenant.
    assert tenant_count(admin_engine, two_owners[0]) == 0


def test_lease_for_a_unit_that_does_not_exist_is_404(
    api: TestClient, ana: dict[str, str], two_owners: tuple[UUID, UUID], admin_engine: Engine
) -> None:
    response = api.post(
        "/api/leases", json=TERMS | {"unit_id": str(uuid4()), "tenant": LUISA}, headers=ana
    )

    assert response.status_code == 404
    assert tenant_count(admin_engine, two_owners[0]) == 0


# One active lease per unit


def test_a_unit_with_an_active_lease_does_not_take_another(
    api: TestClient,
    ana: dict[str, str],
    trees: tuple[Tree, Tree],
    two_owners: tuple[UUID, UUID],
    admin_engine: Engine,
) -> None:
    anas, _ = trees

    response = api.post(
        "/api/leases", json=TERMS | {"unit_id": str(anas.unit_id), "tenant": LUISA}, headers=ana
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": "Esta unidad ya tiene un contrato activo. Termínalo antes de crear otro.",
        "code": "unit_has_active_lease",
    }
    assert lease_count(admin_engine, anas.unit_id) == 1
    assert tenant_count(admin_engine, two_owners[0]) == 1


def test_simultaneous_requests_create_only_one_lease(
    api: TestClient,
    ana: dict[str, str],
    vacant_unit: dict,
    two_owners: tuple[UUID, UUID],
    admin_engine: Engine,
) -> None:
    payload = TERMS | {"unit_id": vacant_unit["id"], "tenant": LUISA}

    with ThreadPoolExecutor(max_workers=8) as pool:
        responses = list(
            pool.map(lambda _: api.post("/api/leases", json=payload, headers=ana), range(8))
        )

    assert sorted(response.status_code for response in responses) == [201] + [409] * 7
    assert lease_count(admin_engine, vacant_unit["id"]) == 1
    # The losers' tenants are rolled back with their leases.
    assert tenant_count(admin_engine, two_owners[0]) == 1


def test_after_ending_a_lease_the_unit_takes_a_new_one(
    api: TestClient, ana: dict[str, str], trees: tuple[Tree, Tree], admin_engine: Engine
) -> None:
    anas, _ = trees
    payload = TERMS | {"unit_id": str(anas.unit_id), "tenant": LUISA}

    ended = api.post(f"/api/leases/{anas.lease_id}/end", headers=ana)
    created = api.post("/api/leases", json=payload, headers=ana)

    assert ended.status_code == 200
    assert ended.json()["status"] == "ended"
    assert created.status_code == 201
    assert lease_count(admin_engine, anas.unit_id) == 2


def test_ending_a_lease_twice_is_an_error(
    api: TestClient, ana: dict[str, str], trees: tuple[Tree, Tree]
) -> None:
    anas, _ = trees
    api.post(f"/api/leases/{anas.lease_id}/end", headers=ana)

    response = api.post(f"/api/leases/{anas.lease_id}/end", headers=ana)

    assert response.status_code == 400
    assert response.json() == {
        "detail": "Este contrato ya está terminado.",
        "code": "lease_already_ended",
    }


# Update


def test_update_changes_the_terms_and_the_tenant(
    api: TestClient, ana: dict[str, str], trees: tuple[Tree, Tree]
) -> None:
    anas, _ = trees
    before = api.get(f"/api/leases/{anas.lease_id}", headers=ana).json()

    response = api.patch(
        f"/api/leases/{anas.lease_id}",
        json={
            "rent": 1000000,
            "auto_send": False,
            "end_date": "2026-12-31",
            "tenant": {"email": "nuevo@example.com", "phone": "300 123 4567"},
        },
        headers=ana,
    )

    assert response.status_code == 200, response.text
    assert response.json() == before | {
        "rent": 1000000,
        "auto_send": False,
        "end_date": "2026-12-31",
        "tenant": before["tenant"] | {"email": "nuevo@example.com", "phone": "300 123 4567"},
    }
    assert api.get(f"/api/leases/{anas.lease_id}", headers=ana).json() == response.json()


def test_update_can_clear_the_optional_fields(
    api: TestClient, ana: dict[str, str], trees: tuple[Tree, Tree]
) -> None:
    anas, _ = trees
    api.patch(
        f"/api/leases/{anas.lease_id}",
        json={"end_date": "2026-12-31", "deposit": 500000},
        headers=ana,
    )

    response = api.patch(
        f"/api/leases/{anas.lease_id}", json={"end_date": None, "deposit": None}, headers=ana
    )

    assert response.status_code == 200
    assert (response.json()["end_date"], response.json()["deposit"]) == (None, None)


@pytest.mark.parametrize(
    "payload",
    [
        {"rent": 0},
        {"rent": None},
        {"due_day": 29},
        {"start_date": None},
        {"auto_send": None},
        {"charge_deposit": None},
        {"items": None},
        {"items": [{"description": "Administración", "amount": 0}]},
        {"items": [{"description": " ", "amount": 200000}]},
        {"items": [{"description": "Administración"}]},
        {"items": [{"description": "Administración", "amount": 1}] * 11},
        {"charge_deposit": "sí"},
        {"tenant": {"email": "mal"}},
        {"tenant": {"name": None}},
        {"tenant": {"email": None}},
    ],
)
def test_update_rejects_invalid_data(
    api: TestClient, ana: dict[str, str], trees: tuple[Tree, Tree], payload: dict[str, object]
) -> None:
    anas, _ = trees

    response = api.patch(f"/api/leases/{anas.lease_id}", json=payload, headers=ana)

    assert response.status_code == 422


@pytest.mark.parametrize("payload", [{"end_date": "2025-06-01"}, {"start_date": "2027-01-01"}])
def test_update_checks_the_dates_against_the_stored_ones(
    api: TestClient, ana: dict[str, str], trees: tuple[Tree, Tree], payload: dict[str, str]
) -> None:
    anas, _ = trees
    api.patch(f"/api/leases/{anas.lease_id}", json={"end_date": "2026-12-31"}, headers=ana)

    response = api.patch(f"/api/leases/{anas.lease_id}", json=payload, headers=ana)

    assert response.status_code == 422
    assert response.json()["code"] == "invalid_lease_dates"


# Isolation: another owner's resource is a 404, and nothing changes


def test_owner_cannot_read_another_owners_lease(
    api: TestClient, beto: dict[str, str], trees: tuple[Tree, Tree]
) -> None:
    anas, _ = trees

    response = api.get(f"/api/leases/{anas.lease_id}", headers=beto)

    assert response.status_code == 404
    assert response.json()["code"] == "not_found"


def test_owner_cannot_update_another_owners_lease(
    api: TestClient, beto: dict[str, str], trees: tuple[Tree, Tree], admin_engine: Engine
) -> None:
    anas, _ = trees

    response = api.patch(
        f"/api/leases/{anas.lease_id}",
        json={"rent": 1, "tenant": {"email": "ladron@example.com"}},
        headers=beto,
    )

    assert response.status_code == 404
    with admin_engine.connect() as connection:
        row = connection.execute(
            text(
                "select l.rent, t.email from leases l join tenants t on t.id = l.tenant_id "
                "where l.id = :id"
            ),
            {"id": anas.lease_id},
        ).one()
    assert tuple(row) == (950000, "ana@example.com")


def test_owner_cannot_end_another_owners_lease(
    api: TestClient, beto: dict[str, str], trees: tuple[Tree, Tree], admin_engine: Engine
) -> None:
    anas, _ = trees

    response = api.post(f"/api/leases/{anas.lease_id}/end", headers=beto)

    assert response.status_code == 404
    with admin_engine.connect() as connection:
        status = connection.execute(
            text("select status from leases where id = :id"), {"id": anas.lease_id}
        ).scalar_one()
    assert status == "active"


def test_owner_cannot_create_a_lease_on_another_owners_unit(
    api: TestClient,
    beto: dict[str, str],
    trees: tuple[Tree, Tree],
    two_owners: tuple[UUID, UUID],
    admin_engine: Engine,
) -> None:
    anas, _ = trees
    # Ana's unit is free, so only the ownership check can stop Beto.
    with admin_engine.begin() as connection:
        connection.execute(
            text("update leases set status = 'ended' where id = :id"), {"id": anas.lease_id}
        )

    response = api.post(
        "/api/leases", json=TERMS | {"unit_id": str(anas.unit_id), "tenant": LUISA}, headers=beto
    )

    assert response.status_code == 404
    assert lease_count(admin_engine, anas.unit_id) == 1
    assert tenant_count(admin_engine, two_owners[1]) == 1


def test_a_taken_unit_of_another_owner_is_also_a_404(
    api: TestClient, beto: dict[str, str], trees: tuple[Tree, Tree]
) -> None:
    """Not a 409, which would reveal that the unit exists and is rented."""
    anas, _ = trees

    response = api.post(
        "/api/leases", json=TERMS | {"unit_id": str(anas.unit_id), "tenant": LUISA}, headers=beto
    )

    assert response.status_code == 404


def test_owner_cannot_use_another_owners_tenant(
    api: TestClient,
    beto: dict[str, str],
    trees: tuple[Tree, Tree],
    admin_engine: Engine,
) -> None:
    anas, betos = trees
    with admin_engine.begin() as connection:
        connection.execute(
            text("update leases set status = 'ended' where id = :id"), {"id": betos.lease_id}
        )

    response = api.post(
        "/api/leases",
        json=TERMS | {"unit_id": str(betos.unit_id), "tenant_id": str(anas.tenant_id)},
        headers=beto,
    )

    assert response.status_code == 404
    assert lease_count(admin_engine, betos.unit_id) == 1


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("post", "/api/leases"),
        ("get", f"/api/leases/{uuid4()}"),
        ("patch", f"/api/leases/{uuid4()}"),
        ("post", f"/api/leases/{uuid4()}/end"),
    ],
)
def test_every_route_requires_a_token(api: TestClient, method: str, path: str) -> None:
    response = api.request(method, path, json={})

    assert response.status_code == 401
    assert response.json()["code"] == "unauthorized"


def test_tenant_document_and_its_type_are_edited_with_the_lease(
    api: TestClient, ana: dict[str, str], trees: tuple[Tree, Tree]
) -> None:
    anas, _ = trees
    url = f"/api/leases/{anas.lease_id}"
    assert api.get(url, headers=ana).json()["tenant"]["document_type"] == "cc"

    changed = api.patch(
        url,
        headers=ana,
        json={"tenant": {"document_type": "nit", "document_number": "901.555.111-2"}},
    )

    assert changed.status_code == 200
    tenant = changed.json()["tenant"]
    assert (tenant["document_type"], tenant["document_number"]) == ("nit", "901.555.111-2")
    for bad in ({"document_type": None}, {"document_type": "passport"}):
        assert api.patch(url, headers=ana, json={"tenant": bad}).status_code == 422


# Payment details of the lease: they replace the owner's on its bills.


def test_lease_can_have_its_own_payment_details(
    api: TestClient, ana: dict[str, str], vacant_unit: dict
) -> None:
    created = api.post(
        "/api/leases",
        json=TERMS
        | {"unit_id": vacant_unit["id"], "tenant": LUISA, "payment_details": "  Daviplata 300  "},
        headers=ana,
    )

    assert created.status_code == 201, created.text
    lease = created.json()
    assert lease["payment_details"] == "Daviplata 300"

    changed = api.patch(
        f"/api/leases/{lease['id']}", json={"payment_details": "Nequi\n310"}, headers=ana
    )
    assert changed.json()["payment_details"] == "Nequi\n310"
    # Leaving it out keeps it; sending it blank clears it.
    kept = api.patch(f"/api/leases/{lease['id']}", json={"rent": 1000000}, headers=ana)
    assert kept.json()["payment_details"] == "Nequi\n310"
    cleared = api.patch(f"/api/leases/{lease['id']}", json={"payment_details": ""}, headers=ana)
    assert cleared.json()["payment_details"] is None


def test_lease_payment_details_are_validated(
    api: TestClient, ana: dict[str, str], trees: tuple[Tree, Tree]
) -> None:
    anas, _ = trees

    response = api.patch(
        f"/api/leases/{anas.lease_id}", json={"payment_details": "x" * 501}, headers=ana
    )

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"


def test_owner_cannot_read_or_change_another_owners_payment_details(
    api: TestClient,
    ana: dict[str, str],
    beto: dict[str, str],
    trees: tuple[Tree, Tree],
    admin_engine: Engine,
) -> None:
    anas, _ = trees
    api.patch(f"/api/leases/{anas.lease_id}", json={"payment_details": "de Ana"}, headers=ana)

    assert api.get(f"/api/leases/{anas.lease_id}", headers=beto).status_code == 404
    response = api.patch(
        f"/api/leases/{anas.lease_id}", json={"payment_details": "de Beto"}, headers=beto
    )

    assert response.status_code == 404
    with admin_engine.connect() as connection:
        stored = connection.execute(
            text("select payment_details from leases where id = :id"), {"id": anas.lease_id}
        ).scalar_one()
    assert stored == "de Ana"


# Whether the deposit gets charged on the first monthly bill.


def test_new_lease_charges_its_deposit_unless_told_not_to(
    api: TestClient, ana: dict[str, str], vacant_unit: dict
) -> None:
    created = api.post(
        "/api/leases",
        json=TERMS
        | {
            "unit_id": vacant_unit["id"],
            "tenant": LUISA,
            "deposit": 950000,
            "charge_deposit": False,
        },
        headers=ana,
    ).json()
    assert created["charge_deposit"] is False

    changed = api.patch(f"/api/leases/{created['id']}", json={"charge_deposit": True}, headers=ana)
    assert changed.json()["charge_deposit"] is True
    # Leaving it out keeps it.
    kept = api.patch(f"/api/leases/{created['id']}", json={"rent": 1000000}, headers=ana)
    assert kept.json()["charge_deposit"] is True


def test_owner_cannot_make_another_owners_lease_charge_its_deposit(
    api: TestClient, beto: dict[str, str], trees: tuple[Tree, Tree], admin_engine: Engine
) -> None:
    anas, _ = trees

    response = api.patch(
        f"/api/leases/{anas.lease_id}", json={"deposit": 1, "charge_deposit": True}, headers=beto
    )

    assert response.status_code == 404
    with admin_engine.connect() as connection:
        row = connection.execute(
            text("select deposit, charge_deposit from leases where id = :id"),
            {"id": anas.lease_id},
        ).one()
    assert tuple(row) == (None, False)


# The items of the lease: what it charges every month besides the rent.

FEE = {"description": "Administración", "amount": 200000}
PARKING = {"description": "Parqueadero", "amount": 80000}


def test_lease_is_created_with_its_items_in_order(
    api: TestClient, ana: dict[str, str], vacant_unit: dict
) -> None:
    created = api.post(
        "/api/leases",
        json=TERMS
        | {
            "unit_id": vacant_unit["id"],
            "tenant": LUISA,
            "items": [{"description": "  Administración ", "amount": 200000}, PARKING],
        },
        headers=ana,
    )

    assert created.status_code == 201, created.text
    assert created.json()["items"] == [FEE, PARKING]
    read = api.get(f"/api/leases/{created.json()['id']}", headers=ana).json()
    assert read["items"] == [FEE, PARKING]


def test_update_replaces_the_items_only_when_they_are_sent(
    api: TestClient, ana: dict[str, str], trees: tuple[Tree, Tree]
) -> None:
    path = f"/api/leases/{trees[0].lease_id}"
    assert api.patch(path, json={"items": [FEE, PARKING]}, headers=ana).json()["items"] == [
        FEE,
        PARKING,
    ]

    # Leaving them out keeps them.
    assert api.patch(path, json={"rent": 1000000}, headers=ana).json()["items"] == [FEE, PARKING]
    # Sending them replaces the whole list, in the order sent.
    swapped = api.patch(path, json={"items": [PARKING, FEE | {"amount": 250000}]}, headers=ana)
    assert swapped.json()["items"] == [PARKING, FEE | {"amount": 250000}]
    # An empty list removes them.
    assert api.patch(path, json={"items": []}, headers=ana).json()["items"] == []
    assert api.get(path, headers=ana).json()["items"] == []


def test_create_rejects_invalid_items(
    api: TestClient, ana: dict[str, str], vacant_unit: dict
) -> None:
    response = api.post(
        "/api/leases",
        json=TERMS
        | {"unit_id": vacant_unit["id"], "tenant": LUISA, "items": [FEE | {"amount": 0.5}]},
        headers=ana,
    )

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"


def test_owner_cannot_read_or_replace_another_owners_items(
    api: TestClient,
    ana: dict[str, str],
    beto: dict[str, str],
    trees: tuple[Tree, Tree],
    admin_engine: Engine,
) -> None:
    anas, betos = trees
    api.patch(f"/api/leases/{anas.lease_id}", json={"items": [FEE]}, headers=ana)

    assert api.get(f"/api/leases/{anas.lease_id}", headers=beto).status_code == 404
    response = api.patch(f"/api/leases/{anas.lease_id}", json={"items": []}, headers=beto)

    assert response.status_code == 404
    # Beto's own lease shows nothing of Ana's, and replacing his list leaves hers alone.
    assert api.get(f"/api/leases/{betos.lease_id}", headers=beto).json()["items"] == []
    api.patch(f"/api/leases/{betos.lease_id}", json={"items": [PARKING]}, headers=beto)
    with admin_engine.connect() as connection:
        stored = connection.execute(
            text("select lease_id, description from lease_items order by description")
        ).all()
    assert [tuple(row) for row in stored] == [
        (anas.lease_id, "Administración"),
        (betos.lease_id, "Parqueadero"),
    ]


def test_replacing_the_items_at_once_leaves_one_whole_list(
    api: TestClient, ana: dict[str, str], trees: tuple[Tree, Tree]
) -> None:
    path = f"/api/leases/{trees[0].lease_id}"
    api.patch(path, json={"items": [FEE, PARKING]}, headers=ana)
    lists = [[{"description": f"Lista {n}", "amount": 1000 * n}] * 3 for n in range(1, 7)]

    with ThreadPoolExecutor(max_workers=6) as pool:
        codes = list(
            pool.map(
                lambda items: api.patch(path, json={"items": items}, headers=ana).status_code,
                lists,
            )
        )

    # Each one waits for the one before it; none trips over another's rows.
    assert codes == [200] * 6
    assert api.get(path, headers=ana).json()["items"] in lists
