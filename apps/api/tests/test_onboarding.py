from concurrent.futures import ThreadPoolExecutor
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

from tests.conftest import MakeToken, bearer

PROPERTY = {
    "name": "Casa Calle 45",
    "address": "Calle 45 # 10-20",
    "city": "Bogotá",
    "type": "house",
}
UNITS = [
    {"name": "Apto 1", "use": "residential"},
    {"name": "Apto 2", "use": "residential"},
    {"name": "Local", "use": "commercial"},
]
LEASE = {
    "unit_index": 1,
    "tenant": {"name": "Luisa Gómez", "email": "luisa.gomez@example.com"},
    "rent": 950000,
    "due_day": 5,
    "start_date": "2026-01-01",
    "end_date": "2026-12-31",
}


@pytest.fixture
def ana(new_user_ids: tuple[UUID, UUID], make_token: MakeToken) -> dict[str, str]:
    """A user who has just signed up: the API has never seen her."""
    return bearer(make_token(new_user_ids[0]))


@pytest.fixture
def beto(new_user_ids: tuple[UUID, UUID], make_token: MakeToken) -> dict[str, str]:
    return bearer(make_token(new_user_ids[1], email="beto@example.com"))


def row_counts(admin_engine: Engine, owner_id: UUID) -> dict[str, int]:
    with admin_engine.connect() as connection:
        return {
            table: connection.execute(
                text(f"select count(*) from {table} where owner_id = :id"), {"id": owner_id}
            ).scalar_one()
            for table in ("properties", "units", "tenants", "leases")
        }


NOTHING = {"properties": 0, "units": 0, "tenants": 0, "leases": 0}


def test_onboarding_with_a_lease_creates_everything(
    api: TestClient, ana: dict[str, str], new_user_ids: tuple[UUID, UUID], admin_engine: Engine
) -> None:
    response = api.post(
        "/api/onboarding", json={"property": PROPERTY, "units": UNITS, "lease": LEASE}, headers=ana
    )

    assert response.status_code == 201, response.text
    body = response.json()
    units = body["property"]["units"]
    assert body["property"]["name"] == "Casa Calle 45"
    assert [unit["name"] for unit in units] == ["Apto 1", "Apto 2", "Local"]
    assert [unit["status"] for unit in units] == ["vacant", "up_to_date", "vacant"]
    assert units[1]["active_lease"] == {
        "id": body["lease"]["id"],
        "tenant_name": "Luisa Gómez",
        "rent": 950000,
    }
    assert body["lease"]["unit"]["id"] == units[1]["id"]
    assert body["lease"]["end_date"] == "2026-12-31"
    assert row_counts(admin_engine, new_user_ids[0]) == {
        "properties": 1,
        "units": 3,
        "tenants": 1,
        "leases": 1,
    }


def test_onboarding_without_a_lease(
    api: TestClient, ana: dict[str, str], new_user_ids: tuple[UUID, UUID], admin_engine: Engine
) -> None:
    response = api.post("/api/onboarding", json={"property": PROPERTY, "units": UNITS}, headers=ana)

    assert response.status_code == 201, response.text
    assert response.json()["lease"] is None
    assert row_counts(admin_engine, new_user_ids[0]) == NOTHING | {"properties": 1, "units": 3}


def test_onboarding_completes_the_owner(api: TestClient, ana: dict[str, str]) -> None:
    api.post("/api/onboarding", json={"property": PROPERTY, "units": UNITS}, headers=ana)

    me = api.get("/api/me", headers=ana).json()

    assert me["onboarding_complete"] is True


@pytest.mark.parametrize(
    "lease_changes",
    [
        {"end_date": "2025-12-31"},  # a business rule, checked after the property is built
        {"rent": 0},
        {"unit_index": 3},
        {"unit_index": -1},
        {"tenant": {"name": "Luisa", "email": "mal"}},
    ],
)
def test_if_the_lease_is_invalid_nothing_is_created(
    api: TestClient,
    ana: dict[str, str],
    new_user_ids: tuple[UUID, UUID],
    admin_engine: Engine,
    lease_changes: dict[str, object],
) -> None:
    response = api.post(
        "/api/onboarding",
        json={"property": PROPERTY, "units": UNITS, "lease": LEASE | lease_changes},
        headers=ana,
    )

    assert response.status_code == 422, response.text
    assert row_counts(admin_engine, new_user_ids[0]) == NOTHING
    assert api.get("/api/me", headers=ana).json()["onboarding_complete"] is False


@pytest.mark.parametrize(
    "payload",
    [
        {"property": PROPERTY, "units": []},
        {"property": PROPERTY},
        {"units": UNITS},
        {"property": PROPERTY | {"type": "castle"}, "units": UNITS},
        {"property": PROPERTY, "units": [{"name": " ", "use": "residential"}]},
        {"property": PROPERTY, "units": [UNITS[0]] * 51},
    ],
)
def test_onboarding_rejects_invalid_data(
    api: TestClient,
    ana: dict[str, str],
    new_user_ids: tuple[UUID, UUID],
    admin_engine: Engine,
    payload: dict[str, object],
) -> None:
    response = api.post("/api/onboarding", json=payload, headers=ana)

    assert response.status_code == 422
    assert row_counts(admin_engine, new_user_ids[0]) == NOTHING


def test_onboarding_happens_only_once(
    api: TestClient, ana: dict[str, str], new_user_ids: tuple[UUID, UUID], admin_engine: Engine
) -> None:
    payload = {"property": PROPERTY, "units": UNITS}
    api.post("/api/onboarding", json=payload, headers=ana)

    response = api.post("/api/onboarding", json=payload, headers=ana)

    assert response.status_code == 409
    assert response.json() == {
        "detail": "Ya creaste tu primer inmueble. Agrega los demás desde Inmuebles.",
        "code": "onboarding_already_complete",
    }
    assert row_counts(admin_engine, new_user_ids[0])["properties"] == 1


def test_a_double_tap_creates_only_one_property(
    api: TestClient, ana: dict[str, str], new_user_ids: tuple[UUID, UUID], admin_engine: Engine
) -> None:
    payload = {"property": PROPERTY, "units": UNITS, "lease": LEASE}

    with ThreadPoolExecutor(max_workers=6) as pool:
        responses = list(
            pool.map(lambda _: api.post("/api/onboarding", json=payload, headers=ana), range(6))
        )

    assert sorted(response.status_code for response in responses) == [201] + [409] * 5
    assert row_counts(admin_engine, new_user_ids[0]) == {
        "properties": 1,
        "units": 3,
        "tenants": 1,
        "leases": 1,
    }


def test_each_owner_onboards_on_their_own(
    api: TestClient,
    ana: dict[str, str],
    beto: dict[str, str],
    new_user_ids: tuple[UUID, UUID],
    admin_engine: Engine,
) -> None:
    api.post("/api/onboarding", json={"property": PROPERTY, "units": UNITS}, headers=ana)

    # Ana's property does not count as Beto's onboarding, and he does not see it.
    assert api.get("/api/me", headers=beto).json()["onboarding_complete"] is False
    assert api.get("/api/properties", headers=beto).json() == []

    response = api.post(
        "/api/onboarding",
        json={"property": PROPERTY | {"name": "Casa de Beto"}, "units": UNITS[:1]},
        headers=beto,
    )

    assert response.status_code == 201
    assert [p["name"] for p in api.get("/api/properties", headers=beto).json()] == ["Casa de Beto"]
    assert [p["name"] for p in api.get("/api/properties", headers=ana).json()] == ["Casa Calle 45"]
    assert row_counts(admin_engine, new_user_ids[1]) == NOTHING | {"properties": 1, "units": 1}


def test_onboarding_requires_a_token(api: TestClient) -> None:
    response = api.post("/api/onboarding", json={"property": PROPERTY, "units": UNITS})

    assert response.status_code == 401
    assert response.json()["code"] == "unauthorized"
