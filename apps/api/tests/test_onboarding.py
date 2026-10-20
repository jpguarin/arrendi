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


def complete_profile(
    api: TestClient, admin_engine: Engine, headers: dict[str, str], owner_id: UUID
) -> None:
    """What the owner fills in before the first property: Ajustes' data and a signature."""
    response = api.patch(
        "/api/settings",
        json={"document_number": "52.814.337", "payment_details": "Bancolombia · Ahorros 123"},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    # The signature has its own upload, tested in test_signature.py: here, only its path.
    with admin_engine.begin() as connection:
        connection.execute(
            text("update owners set signature_path = :path where id = :id"),
            {"path": f"{owner_id}/signature/stored/firma.png", "id": owner_id},
        )


@pytest.fixture
def new_ana(new_user_ids: tuple[UUID, UUID], make_token: MakeToken) -> dict[str, str]:
    """A user who has just signed up: the API has never seen her."""
    return bearer(make_token(new_user_ids[0]))


@pytest.fixture
def new_beto(new_user_ids: tuple[UUID, UUID], make_token: MakeToken) -> dict[str, str]:
    return bearer(make_token(new_user_ids[1], email="beto@example.com"))


@pytest.fixture
def ana(
    api: TestClient, admin_engine: Engine, new_ana: dict[str, str], new_user_ids: tuple[UUID, UUID]
) -> dict[str, str]:
    """Ana, with her data already filled in: ready for her first property."""
    complete_profile(api, admin_engine, new_ana, new_user_ids[0])
    return new_ana


@pytest.fixture
def beto(
    api: TestClient, admin_engine: Engine, new_beto: dict[str, str], new_user_ids: tuple[UUID, UUID]
) -> dict[str, str]:
    complete_profile(api, admin_engine, new_beto, new_user_ids[1])
    return new_beto


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


def test_onboarding_lease_takes_its_copies(api: TestClient, ana: dict[str, str]) -> None:
    lease = LEASE | {"cc_emails": ["pedro@example.com"]}

    response = api.post(
        "/api/onboarding", json={"property": PROPERTY, "units": UNITS, "lease": lease}, headers=ana
    )

    assert response.status_code == 201, response.text
    assert response.json()["lease"]["cc_emails"] == ["pedro@example.com"]


def test_onboarding_takes_the_country_of_the_property(api: TestClient, ana: dict[str, str]) -> None:
    response = api.post(
        "/api/onboarding",
        json={"property": PROPERTY | {"country": "EC"}, "units": UNITS},
        headers=ana,
    )

    assert response.status_code == 201, response.text
    assert response.json()["property"]["country"] == "EC"


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


# The owner's data comes first: it goes on every bill.


def test_a_new_owner_cannot_create_the_first_property_without_their_data(
    api: TestClient, new_ana: dict[str, str], new_user_ids: tuple[UUID, UUID], admin_engine: Engine
) -> None:
    response = api.post(
        "/api/onboarding",
        json={"property": PROPERTY, "units": UNITS, "lease": LEASE},
        headers=new_ana,
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": "Antes de crear tu primer inmueble, completa tus datos: número de documento, "
        "datos de pago y firma.",
        "code": "profile_incomplete",
    }
    assert row_counts(admin_engine, new_user_ids[0]) == NOTHING


@pytest.mark.parametrize(
    ("column", "missing"),
    [
        ("document_number", "número de documento"),
        ("payment_details", "datos de pago"),
        ("signature_path", "firma"),
    ],
)
def test_each_piece_of_the_owners_data_is_required(
    api: TestClient,
    ana: dict[str, str],
    new_user_ids: tuple[UUID, UUID],
    admin_engine: Engine,
    column: str,
    missing: str,
) -> None:
    with admin_engine.begin() as connection:
        connection.execute(
            text(f"update owners set {column} = null where id = :id"), {"id": new_user_ids[0]}
        )

    response = api.post("/api/onboarding", json={"property": PROPERTY, "units": UNITS}, headers=ana)

    assert response.status_code == 409
    assert response.json() == {
        "detail": f"Antes de crear tu primer inmueble, completa tus datos: {missing}.",
        "code": "profile_incomplete",
    }
    assert row_counts(admin_engine, new_user_ids[0]) == NOTHING


def test_me_says_whether_the_owners_data_is_complete(
    api: TestClient, new_ana: dict[str, str], new_user_ids: tuple[UUID, UUID], admin_engine: Engine
) -> None:
    before = api.get("/api/me", headers=new_ana).json()
    complete_profile(api, admin_engine, new_ana, new_user_ids[0])
    after = api.get("/api/me", headers=new_ana).json()

    assert (before["profile_complete"], after["profile_complete"]) == (False, True)


def test_one_owners_data_does_not_open_the_onboarding_of_another(
    api: TestClient,
    ana: dict[str, str],
    new_beto: dict[str, str],
    new_user_ids: tuple[UUID, UUID],
    admin_engine: Engine,
) -> None:
    beto_response = api.post(
        "/api/onboarding", json={"property": PROPERTY, "units": UNITS}, headers=new_beto
    )
    ana_response = api.post(
        "/api/onboarding", json={"property": PROPERTY, "units": UNITS}, headers=ana
    )

    assert beto_response.status_code == 409
    assert beto_response.json()["code"] == "profile_incomplete"
    assert api.get("/api/me", headers=new_beto).json()["profile_complete"] is False
    assert ana_response.status_code == 201
    assert row_counts(admin_engine, new_user_ids[1]) == NOTHING


def test_onboarding_requires_a_token(api: TestClient) -> None:
    response = api.post("/api/onboarding", json={"property": PROPERTY, "units": UNITS})

    assert response.status_code == 401
    assert response.json()["code"] == "unauthorized"
