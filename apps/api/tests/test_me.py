from concurrent.futures import ThreadPoolExecutor
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

from tests.conftest import MakeToken, bearer


def owner_rows(admin_engine: Engine, owner_id: UUID) -> list[tuple[str, str]]:
    with admin_engine.connect() as connection:
        rows = connection.execute(
            text("select name, email from owners where id = :id"), {"id": owner_id}
        )
        return [tuple(row) for row in rows]


def test_first_call_creates_the_owner_from_the_token(
    api: TestClient, make_token: MakeToken, admin_engine: Engine, new_user_ids: tuple[UUID, UUID]
) -> None:
    ana, _ = new_user_ids

    response = api.get("/api/me", headers=bearer(make_token(ana)))

    assert response.status_code == 200
    assert response.json() == {
        "id": str(ana),
        "name": "Ana Gómez",
        "email": "ana@example.com",
        "onboarding_complete": False,
    }
    assert owner_rows(admin_engine, ana) == [("Ana Gómez", "ana@example.com")]


def test_later_calls_keep_the_stored_owner(
    api: TestClient, make_token: MakeToken, admin_engine: Engine, new_user_ids: tuple[UUID, UUID]
) -> None:
    ana, _ = new_user_ids
    api.get("/api/me", headers=bearer(make_token(ana)))
    with admin_engine.begin() as connection:
        connection.execute(text("update owners set name = 'Ana María' where id = :id"), {"id": ana})

    # The token still says "Ana Gómez": the name the owner saved wins.
    response = api.get("/api/me", headers=bearer(make_token(ana)))

    assert response.json()["name"] == "Ana María"
    assert owner_rows(admin_engine, ana) == [("Ana María", "ana@example.com")]


def test_each_owner_gets_only_their_own_data(
    api: TestClient, make_token: MakeToken, new_user_ids: tuple[UUID, UUID]
) -> None:
    ana, beto = new_user_ids
    beto_token = make_token(beto, email="beto@example.com", user_metadata={"full_name": "Beto"})
    api.get("/api/me", headers=bearer(beto_token))

    as_ana = api.get("/api/me", headers=bearer(make_token(ana))).json()
    as_beto = api.get("/api/me", headers=bearer(beto_token)).json()

    assert (as_ana["id"], as_ana["name"], as_ana["email"]) == (
        str(ana),
        "Ana Gómez",
        "ana@example.com",
    )
    assert (as_beto["id"], as_beto["name"], as_beto["email"]) == (
        str(beto),
        "Beto",
        "beto@example.com",
    )


def test_name_falls_back_to_the_email(
    api: TestClient, make_token: MakeToken, new_user_ids: tuple[UUID, UUID]
) -> None:
    ana, _ = new_user_ids

    response = api.get("/api/me", headers=bearer(make_token(ana, user_metadata={})))

    assert response.json()["name"] == "ana@example.com"


def test_user_without_email_cannot_become_an_owner(
    api: TestClient, make_token: MakeToken, admin_engine: Engine, new_user_ids: tuple[UUID, UUID]
) -> None:
    ana, _ = new_user_ids

    response = api.get("/api/me", headers=bearer(make_token(ana, email="")))

    assert response.status_code == 400
    assert response.json()["code"] == "email_required"
    assert owner_rows(admin_engine, ana) == []


def test_me_requires_a_token(api: TestClient) -> None:
    response = api.get("/api/me")

    assert response.status_code == 401
    assert response.json()["code"] == "unauthorized"


def test_me_is_described_in_openapi(api: TestClient) -> None:
    schema = api.get("/openapi.json").json()

    me = schema["paths"]["/api/me"]["get"]
    assert me["responses"]["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/MeResponse"
    }
    assert set(schema["components"]["schemas"]["MeResponse"]["required"]) == {
        "id",
        "name",
        "email",
        "onboarding_complete",
    }


def test_simultaneous_first_calls_create_one_owner(
    api: TestClient, make_token: MakeToken, admin_engine: Engine, new_user_ids: tuple[UUID, UUID]
) -> None:
    ana, _ = new_user_ids
    headers = bearer(make_token(ana))

    with ThreadPoolExecutor(max_workers=8) as pool:
        responses = list(pool.map(lambda _: api.get("/api/me", headers=headers), range(8)))

    assert [response.status_code for response in responses] == [200] * 8
    assert owner_rows(admin_engine, ana) == [("Ana Gómez", "ana@example.com")]
