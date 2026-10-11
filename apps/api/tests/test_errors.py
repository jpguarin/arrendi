import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.errors import AppError, register_error_handlers


def test_unknown_route_uses_error_format(client: TestClient) -> None:
    response = client.get("/api/does-not-exist")

    assert response.status_code == 404
    assert response.json() == {"detail": "No encontramos lo que buscas.", "code": "not_found"}


def test_wrong_method_uses_error_format(client: TestClient) -> None:
    response = client.post("/api/health")

    assert response.status_code == 405
    assert response.json()["code"] == "method_not_allowed"


@pytest.fixture
def sample_client() -> TestClient:
    sample = FastAPI()
    register_error_handlers(sample)

    @sample.get("/app-error")
    def raise_app_error() -> None:
        raise AppError(400, "El valor supera el saldo.", "payment_exceeds_balance")

    @sample.get("/crash")
    def crash() -> None:
        raise RuntimeError("secret internal detail")

    @sample.get("/validated")
    def validated(amount: int) -> int:
        return amount

    return TestClient(sample, raise_server_exceptions=False)


def test_app_error_keeps_its_detail_and_code(sample_client: TestClient) -> None:
    response = sample_client.get("/app-error")

    assert response.status_code == 400
    assert response.json() == {
        "detail": "El valor supera el saldo.",
        "code": "payment_exceeds_balance",
    }


def test_validation_error_uses_error_format(sample_client: TestClient) -> None:
    response = sample_client.get("/validated", params={"amount": "abc"})

    assert response.status_code == 422
    assert response.json() == {
        "detail": "Revisa los datos e inténtalo de nuevo.",
        "code": "validation_error",
    }


def test_unexpected_error_uses_error_format_and_hides_the_cause(sample_client: TestClient) -> None:
    response = sample_client.get("/crash")

    assert response.status_code == 500
    assert response.json() == {
        "detail": "Algo salió mal. Inténtalo de nuevo.",
        "code": "internal_error",
    }
