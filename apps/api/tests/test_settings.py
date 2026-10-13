from uuid import UUID

from fastapi.testclient import TestClient

from tests.conftest import MakeToken, bearer


def test_settings_start_with_what_the_token_says(
    api: TestClient, make_token: MakeToken, new_user_ids: tuple[UUID, UUID]
) -> None:
    ana, _ = new_user_ids

    response = api.get("/api/settings", headers=bearer(make_token(ana)))

    assert response.status_code == 200
    assert response.json() == {
        "name": "Ana Gómez",
        "email": "ana@example.com",
        "document_type": "cc",
        "document_number": None,
        "payment_details": None,
        "has_signature": False,
        "send_day": 1,
        "reminder_1": True,
        "reminder_2": True,
        "email_copy": False,
    }


def test_update_changes_only_the_fields_sent(
    api: TestClient, make_token: MakeToken, two_owners: tuple[UUID, UUID]
) -> None:
    ana, _ = two_owners
    headers = bearer(make_token(ana))
    details = "Bancolombia, ahorros 123-456789-00\nNequi 300 123 4567"

    first = api.patch(
        "/api/settings",
        headers=headers,
        json={
            "document_type": "nit",
            "document_number": " 900.123.456-7 ",
            "payment_details": details,
        },
    )
    second = api.patch("/api/settings", headers=headers, json={"name": "Ana María Gómez"})

    assert first.status_code == 200
    assert second.json() == {
        "name": "Ana María Gómez",
        "email": "ana@example.com",
        "document_type": "nit",
        "document_number": "900.123.456-7",
        "payment_details": details,
        "has_signature": False,
        "send_day": 1,
        "reminder_1": True,
        "reminder_2": True,
        "email_copy": False,
    }
    assert api.get("/api/settings", headers=headers).json() == second.json()
    assert api.get("/api/me", headers=headers).json()["name"] == "Ana María Gómez"


def test_optional_fields_are_cleared_with_null_or_blank(
    api: TestClient, make_token: MakeToken, two_owners: tuple[UUID, UUID]
) -> None:
    ana, _ = two_owners
    headers = bearer(make_token(ana))
    api.patch(
        "/api/settings", headers=headers, json={"document_number": "1", "payment_details": "x"}
    )

    response = api.patch(
        "/api/settings", headers=headers, json={"document_number": None, "payment_details": "  "}
    )

    assert response.json()["document_number"] is None
    assert response.json()["payment_details"] is None


def test_name_and_document_type_cannot_be_cleared(
    api: TestClient, make_token: MakeToken, two_owners: tuple[UUID, UUID]
) -> None:
    ana, _ = two_owners
    headers = bearer(make_token(ana))

    for body in (
        {"name": None},
        {"name": "  "},
        {"payment_details": "x" * 501},
        {"document_type": None},
        {"document_type": "passport"},
    ):
        response = api.patch("/api/settings", headers=headers, json=body)
        assert response.status_code == 422
        assert response.json()["code"] == "validation_error"


def test_sending_settings_are_saved(
    api: TestClient, make_token: MakeToken, two_owners: tuple[UUID, UUID]
) -> None:
    ana, _ = two_owners
    headers = bearer(make_token(ana))

    response = api.patch(
        "/api/settings",
        headers=headers,
        json={"send_day": 28, "reminder_1": False, "email_copy": True},
    )

    assert response.status_code == 200
    saved = api.get("/api/settings", headers=headers).json()
    assert (saved["send_day"], saved["reminder_1"], saved["reminder_2"], saved["email_copy"]) == (
        28,
        False,
        True,
        True,
    )


def test_sending_settings_are_validated(
    api: TestClient, make_token: MakeToken, two_owners: tuple[UUID, UUID]
) -> None:
    ana, _ = two_owners
    headers = bearer(make_token(ana))

    for body in (
        {"send_day": 0},
        {"send_day": 29},
        {"send_day": "5"},
        {"send_day": None},
        {"reminder_1": None},
        {"email_copy": None},
    ):
        response = api.patch("/api/settings", headers=headers, json=body)
        assert response.status_code == 422, body


def test_settings_need_a_session(api: TestClient) -> None:
    assert api.get("/api/settings").status_code == 401
    assert api.patch("/api/settings", json={"name": "X"}).status_code == 401


def test_an_owner_changes_only_their_own_settings(
    api: TestClient, make_token: MakeToken, two_owners: tuple[UUID, UUID]
) -> None:
    ana, beto = two_owners

    api.patch("/api/settings", headers=bearer(make_token(ana)), json={"payment_details": "de Ana"})

    as_beto = api.get("/api/settings", headers=bearer(make_token(beto))).json()
    assert (as_beto["name"], as_beto["payment_details"]) == ("Beto", None)
