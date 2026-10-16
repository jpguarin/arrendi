from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

from tests.conftest import MakeToken, Tree, bearer

CASA = {"name": "Casa Calle 45", "address": "Calle 45 # 10-20", "city": "Bogotá", "type": "house"}


@pytest.fixture
def ana(two_owners: tuple[UUID, UUID], make_token: MakeToken) -> dict[str, str]:
    return bearer(make_token(two_owners[0]))


@pytest.fixture
def beto(two_owners: tuple[UUID, UUID], make_token: MakeToken) -> dict[str, str]:
    return bearer(make_token(two_owners[1]))


def create_property(api: TestClient, headers: dict[str, str], **overrides: object) -> dict:
    response = api.post("/api/properties", json=CASA | overrides, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


# Properties


def test_create_a_property(api: TestClient, ana: dict[str, str]) -> None:
    response = api.post("/api/properties", json=CASA, headers=ana)

    assert response.status_code == 201
    body = response.json()
    assert UUID(body["id"])
    # Without a country, Colombia.
    assert body == CASA | {"id": body["id"], "country": "CO", "units": []}


def test_a_property_can_be_in_another_country(api: TestClient, ana: dict[str, str]) -> None:
    body = create_property(api, ana, city="Ciudad de Panamá", country="PA")

    assert body["country"] == "PA"
    assert api.get("/api/properties", headers=ana).json()[0]["country"] == "PA"


def test_list_returns_properties_with_their_units_in_creation_order(
    api: TestClient, ana: dict[str, str]
) -> None:
    casa = create_property(api, ana)
    edificio = create_property(api, ana, name="Edificio Norte", type="building")
    for name in ("Apto 1", "Apto 2"):
        api.post(
            f"/api/properties/{casa['id']}/units",
            json={"name": name, "use": "residential"},
            headers=ana,
        )

    response = api.get("/api/properties", headers=ana)

    assert response.status_code == 200
    properties = response.json()
    assert [p["name"] for p in properties] == ["Casa Calle 45", "Edificio Norte"]
    assert [u["name"] for u in properties[0]["units"]] == ["Apto 1", "Apto 2"]
    assert properties[1]["id"] == edificio["id"]
    assert properties[1]["units"] == []


def test_a_new_owner_can_create_a_property_before_calling_me(
    api: TestClient, make_token: MakeToken, new_user_ids: tuple[UUID, UUID]
) -> None:
    headers = bearer(make_token(new_user_ids[0]))

    response = api.post("/api/properties", json=CASA, headers=headers)

    assert response.status_code == 201


def test_optional_fields_can_be_left_out_and_blank_becomes_null(
    api: TestClient, ana: dict[str, str]
) -> None:
    response = api.post(
        "/api/properties",
        json={"name": "  Local Centro  ", "type": "shop", "city": "   "},
        headers=ana,
    )

    assert response.status_code == 201
    body = response.json()
    assert (body["name"], body["address"], body["city"]) == ("Local Centro", None, None)


@pytest.mark.parametrize(
    "payload",
    [
        {"type": "house"},
        {"name": "", "type": "house"},
        {"name": "   ", "type": "house"},
        {"name": "Casa", "type": "castle"},
        {"name": "Casa"},
        {"name": "x" * 121, "type": "house"},
        # The country is a code of ISO 3166-1, in capitals, that exists.
        {"name": "Casa", "type": "house", "country": "XX"},
        {"name": "Casa", "type": "house", "country": "co"},
        {"name": "Casa", "type": "house", "country": "Colombia"},
        {"name": "Casa", "type": "house", "country": ""},
        {"name": "Casa", "type": "house", "country": None},
    ],
)
def test_create_rejects_invalid_data(
    api: TestClient, ana: dict[str, str], payload: dict[str, str]
) -> None:
    response = api.post("/api/properties", json=payload, headers=ana)

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"


def test_update_changes_only_the_fields_sent(api: TestClient, ana: dict[str, str]) -> None:
    casa = create_property(api, ana)

    response = api.patch(
        f"/api/properties/{casa['id']}", json={"name": "Casa Grande", "address": None}, headers=ana
    )

    assert response.status_code == 200
    assert response.json() == casa | {"name": "Casa Grande", "address": None}
    assert api.get("/api/properties", headers=ana).json()[0]["name"] == "Casa Grande"


def test_update_changes_the_country(api: TestClient, ana: dict[str, str]) -> None:
    casa = create_property(api, ana)

    response = api.patch(f"/api/properties/{casa['id']}", json={"country": "MX"}, headers=ana)

    assert response.status_code == 200
    assert response.json() == casa | {"country": "MX"}


@pytest.mark.parametrize(
    "payload",
    [
        {"name": None},
        {"name": " "},
        {"type": None},
        {"type": "x"},
        # A property always has a country: it changes, it is not taken away.
        {"country": None},
        {"country": "ZZ"},
    ],
)
def test_update_rejects_invalid_data(
    api: TestClient, ana: dict[str, str], payload: dict[str, object]
) -> None:
    casa = create_property(api, ana)

    response = api.patch(f"/api/properties/{casa['id']}", json=payload, headers=ana)

    assert response.status_code == 422


def test_update_of_a_property_that_does_not_exist_is_404(
    api: TestClient, ana: dict[str, str]
) -> None:
    response = api.patch(f"/api/properties/{uuid4()}", json={"name": "X"}, headers=ana)

    assert response.status_code == 404
    assert response.json()["code"] == "not_found"


# Units


def test_add_a_unit(api: TestClient, ana: dict[str, str]) -> None:
    casa = create_property(api, ana)

    response = api.post(
        f"/api/properties/{casa['id']}/units",
        json={"name": " Apto 1 ", "use": "residential"},
        headers=ana,
    )

    assert response.status_code == 201
    body = response.json()
    assert body == {
        "id": body["id"],
        "property_id": casa["id"],
        "name": "Apto 1",
        "use": "residential",
        "status": "vacant",
        "active_lease": None,
    }


@pytest.mark.parametrize(
    "payload", [{"use": "residential"}, {"name": " ", "use": "residential"}, {"name": "A"}]
)
def test_add_unit_rejects_invalid_data(
    api: TestClient, ana: dict[str, str], payload: dict[str, str]
) -> None:
    casa = create_property(api, ana)

    response = api.post(f"/api/properties/{casa['id']}/units", json=payload, headers=ana)

    assert response.status_code == 422


def test_update_a_unit(api: TestClient, ana: dict[str, str]) -> None:
    casa = create_property(api, ana)
    unit = api.post(
        f"/api/properties/{casa['id']}/units",
        json={"name": "Apto 1", "use": "residential"},
        headers=ana,
    ).json()

    response = api.patch(f"/api/units/{unit['id']}", json={"use": "commercial"}, headers=ana)

    assert response.status_code == 200
    assert response.json() == unit | {"use": "commercial"}


def test_a_unit_with_an_active_lease_is_up_to_date(
    api: TestClient, ana: dict[str, str], trees: tuple[Tree, Tree]
) -> None:
    anas, _ = trees

    [unit] = api.get("/api/properties", headers=ana).json()[0]["units"]

    assert unit["status"] == "up_to_date"
    assert unit["active_lease"] == {
        "id": str(anas.lease_id),
        "tenant_name": "Arrendatario ana",
        "rent": 950000,
    }


def test_a_unit_whose_lease_ended_is_vacant(
    api: TestClient, ana: dict[str, str], trees: tuple[Tree, Tree], admin_engine: Engine
) -> None:
    anas, _ = trees
    with admin_engine.begin() as connection:
        connection.execute(
            text("update leases set status = 'ended' where id = :id"), {"id": anas.lease_id}
        )

    [unit] = api.get("/api/properties", headers=ana).json()[0]["units"]

    assert (unit["status"], unit["active_lease"]) == ("vacant", None)


# Onboarding flag


def test_onboarding_is_complete_once_the_owner_has_a_property(
    api: TestClient, ana: dict[str, str], beto: dict[str, str]
) -> None:
    assert api.get("/api/me", headers=ana).json()["onboarding_complete"] is False

    create_property(api, ana)

    assert api.get("/api/me", headers=ana).json()["onboarding_complete"] is True
    assert api.get("/api/me", headers=beto).json()["onboarding_complete"] is False


# Isolation: another owner's resource is a 404, and nothing changes


def test_list_shows_only_the_owners_properties(
    api: TestClient, ana: dict[str, str], beto: dict[str, str], trees: tuple[Tree, Tree]
) -> None:
    anas, betos = trees

    as_ana = api.get("/api/properties", headers=ana).json()
    as_beto = api.get("/api/properties", headers=beto).json()

    assert [p["id"] for p in as_ana] == [str(anas.property_id)]
    assert [p["id"] for p in as_beto] == [str(betos.property_id)]
    assert [u["id"] for u in as_beto[0]["units"]] == [str(betos.unit_id)]


def test_owner_cannot_update_another_owners_property(
    api: TestClient, beto: dict[str, str], trees: tuple[Tree, Tree], admin_engine: Engine
) -> None:
    anas, _ = trees

    response = api.patch(
        f"/api/properties/{anas.property_id}", json={"name": "Hackeada"}, headers=beto
    )

    assert response.status_code == 404
    assert response.json()["code"] == "not_found"
    with admin_engine.connect() as connection:
        name = connection.execute(
            text("select name from properties where id = :id"), {"id": anas.property_id}
        ).scalar_one()
    assert name == "Casa ana"


def test_owner_cannot_change_the_country_of_another_owners_property(
    api: TestClient, beto: dict[str, str], trees: tuple[Tree, Tree], admin_engine: Engine
) -> None:
    anas, _ = trees

    response = api.patch(
        f"/api/properties/{anas.property_id}", json={"country": "PA"}, headers=beto
    )

    assert response.status_code == 404
    with admin_engine.connect() as connection:
        country = connection.execute(
            text("select country from properties where id = :id"), {"id": anas.property_id}
        ).scalar_one()
    assert country == "CO"


def test_owner_cannot_add_a_unit_to_another_owners_property(
    api: TestClient, beto: dict[str, str], trees: tuple[Tree, Tree], admin_engine: Engine
) -> None:
    anas, _ = trees

    response = api.post(
        f"/api/properties/{anas.property_id}/units",
        json={"name": "Colada", "use": "residential"},
        headers=beto,
    )

    assert response.status_code == 404
    with admin_engine.connect() as connection:
        units = connection.execute(
            text("select count(*) from units where property_id = :id"), {"id": anas.property_id}
        ).scalar_one()
    assert units == 1


def test_owner_cannot_update_another_owners_unit(
    api: TestClient, beto: dict[str, str], trees: tuple[Tree, Tree], admin_engine: Engine
) -> None:
    anas, _ = trees

    response = api.patch(f"/api/units/{anas.unit_id}", json={"name": "Hackeada"}, headers=beto)

    assert response.status_code == 404
    with admin_engine.connect() as connection:
        name = connection.execute(
            text("select name from units where id = :id"), {"id": anas.unit_id}
        ).scalar_one()
    assert name == "Apto ana"


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/api/properties"),
        ("post", "/api/properties"),
        ("patch", f"/api/properties/{uuid4()}"),
        ("post", f"/api/properties/{uuid4()}/units"),
        ("patch", f"/api/units/{uuid4()}"),
    ],
)
def test_every_route_requires_a_token(api: TestClient, method: str, path: str) -> None:
    response = api.request(method, path, json={})

    assert response.status_code == 401
    assert response.json()["code"] == "unauthorized"
