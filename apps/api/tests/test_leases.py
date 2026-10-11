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
            "tenant": LUISA | {"document_number": " 52.123.456 ", "phone": ""},
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
            "document_number": "52.123.456",
            "phone": None,
        },
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
