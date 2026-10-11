"""The signed lease: upload link, confirmation and temporary link to read it."""

from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

from app.dependencies import get_storage
from app.main import app
from app.storage import StorageError
from tests.conftest import FakeStorage, MakeToken, Tree, bearer

PDF = b"%PDF-1.7\n" + b"x" * 100
JPG = b"\xff\xd8\xff\xe0" + b"x" * 100
PNG = b"\x89PNG\r\n\x1a\n" + b"x" * 100
MB = 1024 * 1024


@pytest.fixture
def ana(two_owners: tuple[UUID, UUID], make_token: MakeToken) -> dict[str, str]:
    return bearer(make_token(two_owners[0]))


@pytest.fixture
def beto(two_owners: tuple[UUID, UUID], make_token: MakeToken) -> dict[str, str]:
    return bearer(make_token(two_owners[1]))


def request_upload(
    api: TestClient,
    headers: dict[str, str],
    lease_id: UUID,
    filename: str = "contrato.pdf",
    content_type: str = "application/pdf",
    size: int = len(PDF),
):
    return api.post(
        f"/api/leases/{lease_id}/document/upload-url",
        json={"filename": filename, "content_type": content_type, "size": size},
        headers=headers,
    )


def upload(
    api: TestClient,
    storage: FakeStorage,
    headers: dict[str, str],
    lease_id: UUID,
    content: bytes = PDF,
    **request: object,
):
    """The whole flow: ask for the link, send the file to storage, confirm."""
    path = request_upload(api, headers, lease_id, **request).json()["path"]
    storage.upload(path, content)
    return api.post(f"/api/leases/{lease_id}/document", json={"path": path}, headers=headers)


def stored_path(admin_engine: Engine, lease_id: UUID) -> str | None:
    with admin_engine.connect() as connection:
        return connection.execute(
            text("select document_path from leases where id = :id"), {"id": lease_id}
        ).scalar_one()


# Upload link


def test_upload_link_points_inside_the_owners_folder(
    api: TestClient,
    storage: FakeStorage,
    ana: dict[str, str],
    two_owners: tuple[UUID, UUID],
    trees: tuple[Tree, Tree],
) -> None:
    anas, _ = trees

    response = request_upload(api, ana, anas.lease_id, filename="Contrato Apto 2 señor Pérez.PDF")

    assert response.status_code == 200, response.text
    body = response.json()
    folder, upload_id, name = body["path"].rsplit("/", 2)
    assert folder == f"{two_owners[0]}/leases/{anas.lease_id}"
    assert UUID(upload_id)
    assert name == "Contrato-Apto-2-senor-Perez.pdf"
    assert body["upload_url"] == f"https://storage.test/upload/{body['path']}?token=signed"


@pytest.mark.parametrize(
    ("filename", "content_type", "expected"),
    [
        ("foto.jpeg", "image/jpeg", "foto.jpg"),
        ("escaneo", "image/png", "escaneo.png"),
        ("../../etc/passwd", "application/pdf", "passwd.pdf"),
        ("???", "application/pdf", "contrato.pdf"),
        ("a" * 300 + ".pdf", "application/pdf", "a" * 80 + ".pdf"),
    ],
)
def test_the_file_name_is_made_safe(
    api: TestClient,
    storage: FakeStorage,
    ana: dict[str, str],
    trees: tuple[Tree, Tree],
    filename: str,
    content_type: str,
    expected: str,
) -> None:
    anas, _ = trees

    response = request_upload(api, ana, anas.lease_id, filename=filename, content_type=content_type)

    assert response.status_code == 200, response.text
    assert response.json()["path"].rsplit("/", 1)[-1] == expected


@pytest.mark.parametrize("content_type", ["application/zip", "image/gif", "text/html", ""])
def test_only_pdf_jpg_and_png_get_a_link(
    api: TestClient,
    storage: FakeStorage,
    ana: dict[str, str],
    trees: tuple[Tree, Tree],
    content_type: str,
) -> None:
    anas, _ = trees

    response = request_upload(api, ana, anas.lease_id, content_type=content_type)

    assert response.status_code == 422
    assert response.json() == {
        "detail": "Solo se aceptan archivos PDF, JPG o PNG.",
        "code": "unsupported_file_type",
    }


def test_a_file_over_10_mb_gets_no_link(
    api: TestClient, storage: FakeStorage, ana: dict[str, str], trees: tuple[Tree, Tree]
) -> None:
    anas, _ = trees

    at_the_limit = request_upload(api, ana, anas.lease_id, size=10 * MB)
    over = request_upload(api, ana, anas.lease_id, size=10 * MB + 1)

    assert at_the_limit.status_code == 200
    assert over.status_code == 422
    assert over.json() == {"detail": "El archivo supera los 10 MB.", "code": "file_too_large"}


@pytest.mark.parametrize("size", [0, -1, 1.5, "100"])
def test_upload_link_rejects_an_invalid_size(
    api: TestClient,
    storage: FakeStorage,
    ana: dict[str, str],
    trees: tuple[Tree, Tree],
    size: object,
) -> None:
    anas, _ = trees

    response = request_upload(api, ana, anas.lease_id, size=size)

    assert response.status_code == 422


# Confirmation


@pytest.mark.parametrize(
    ("content", "filename", "content_type", "name"),
    [
        (PDF, "contrato.pdf", "application/pdf", "contrato.pdf"),
        (JPG, "foto.jpg", "image/jpeg", "foto.jpg"),
        (PNG, "foto.png", "image/png", "foto.png"),
    ],
)
def test_confirming_attaches_the_document_to_the_lease(
    api: TestClient,
    storage: FakeStorage,
    ana: dict[str, str],
    trees: tuple[Tree, Tree],
    content: bytes,
    filename: str,
    content_type: str,
    name: str,
) -> None:
    anas, _ = trees

    response = upload(
        api,
        storage,
        ana,
        anas.lease_id,
        content,
        filename=filename,
        content_type=content_type,
        size=len(content),
    )

    assert response.status_code == 200, response.text
    lease = response.json()
    assert lease["document_name"] == name
    assert lease["document_uploaded_at"] is not None
    assert api.get(f"/api/leases/{anas.lease_id}", headers=ana).json() == lease


def test_a_file_that_only_looks_like_a_pdf_is_rejected_and_removed(
    api: TestClient,
    storage: FakeStorage,
    ana: dict[str, str],
    trees: tuple[Tree, Tree],
    admin_engine: Engine,
) -> None:
    anas, _ = trees

    response = upload(api, storage, ana, anas.lease_id, b"MZ\x90\x00 this is a program")

    assert response.status_code == 422
    assert response.json()["code"] == "unsupported_file_type"
    assert storage.objects == {}
    assert stored_path(admin_engine, anas.lease_id) is None


def test_the_content_must_match_the_declared_type(
    api: TestClient, storage: FakeStorage, ana: dict[str, str], trees: tuple[Tree, Tree]
) -> None:
    anas, _ = trees

    # A real PNG, sent as if it were a PDF.
    response = upload(api, storage, ana, anas.lease_id, PNG)

    assert response.status_code == 422
    assert response.json()["code"] == "unsupported_file_type"
    assert storage.objects == {}


def test_the_real_size_is_checked_not_the_declared_one(
    api: TestClient,
    storage: FakeStorage,
    ana: dict[str, str],
    trees: tuple[Tree, Tree],
    admin_engine: Engine,
) -> None:
    anas, _ = trees

    # Declared as tiny, but 10 MB and one byte arrive.
    response = upload(api, storage, ana, anas.lease_id, PDF + b"x" * (10 * MB), size=100)

    assert response.status_code == 422
    assert response.json()["code"] == "file_too_large"
    assert storage.objects == {}
    assert stored_path(admin_engine, anas.lease_id) is None


def test_confirming_before_uploading_is_an_error(
    api: TestClient, storage: FakeStorage, ana: dict[str, str], trees: tuple[Tree, Tree]
) -> None:
    anas, _ = trees
    path = request_upload(api, ana, anas.lease_id).json()["path"]

    response = api.post(f"/api/leases/{anas.lease_id}/document", json={"path": path}, headers=ana)

    assert response.status_code == 400
    assert response.json() == {
        "detail": "No recibimos el archivo. Súbelo de nuevo.",
        "code": "document_not_uploaded",
    }


def test_replacing_removes_the_previous_file(
    api: TestClient,
    storage: FakeStorage,
    ana: dict[str, str],
    trees: tuple[Tree, Tree],
    admin_engine: Engine,
) -> None:
    anas, _ = trees
    upload(api, storage, ana, anas.lease_id, filename="viejo.pdf")
    old_path = stored_path(admin_engine, anas.lease_id)

    response = upload(api, storage, ana, anas.lease_id, filename="nuevo.pdf")

    assert response.status_code == 200
    assert response.json()["document_name"] == "nuevo.pdf"
    new_path = stored_path(admin_engine, anas.lease_id)
    assert new_path != old_path
    assert list(storage.objects) == [new_path]


def test_a_failed_replacement_keeps_the_previous_file(
    api: TestClient,
    storage: FakeStorage,
    ana: dict[str, str],
    trees: tuple[Tree, Tree],
    admin_engine: Engine,
) -> None:
    anas, _ = trees
    upload(api, storage, ana, anas.lease_id, filename="bueno.pdf")
    good_path = stored_path(admin_engine, anas.lease_id)

    response = upload(api, storage, ana, anas.lease_id, b"not a pdf", filename="malo.pdf")

    assert response.status_code == 422
    assert stored_path(admin_engine, anas.lease_id) == good_path
    assert list(storage.objects) == [good_path]


def test_confirming_the_same_file_twice_changes_nothing(
    api: TestClient,
    storage: FakeStorage,
    ana: dict[str, str],
    trees: tuple[Tree, Tree],
    admin_engine: Engine,
) -> None:
    anas, _ = trees
    first = upload(api, storage, ana, anas.lease_id)
    path = stored_path(admin_engine, anas.lease_id)

    again = api.post(f"/api/leases/{anas.lease_id}/document", json={"path": path}, headers=ana)

    assert again.status_code == 200
    assert again.json() == first.json()
    assert list(storage.objects) == [path]


# Reading


def test_the_owner_gets_a_temporary_link_to_the_document(
    api: TestClient,
    storage: FakeStorage,
    ana: dict[str, str],
    trees: tuple[Tree, Tree],
    admin_engine: Engine,
) -> None:
    anas, _ = trees
    upload(api, storage, ana, anas.lease_id)
    path = stored_path(admin_engine, anas.lease_id)

    response = api.get(f"/api/leases/{anas.lease_id}/document", headers=ana)

    assert response.status_code == 200
    assert response.json() == {
        "url": f"https://storage.test/download/{path}?token=signed&expires_in=300",
        "name": "contrato.pdf",
        "expires_in": 300,
    }


def test_a_lease_without_a_document_has_no_link(
    api: TestClient, storage: FakeStorage, ana: dict[str, str], trees: tuple[Tree, Tree]
) -> None:
    anas, _ = trees

    response = api.get(f"/api/leases/{anas.lease_id}/document", headers=ana)

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Este contrato no tiene documento.",
        "code": "document_not_found",
    }


# Isolation: another owner's lease is a 404 on the three routes


def test_owner_cannot_get_an_upload_link_for_another_owners_lease(
    api: TestClient, storage: FakeStorage, beto: dict[str, str], trees: tuple[Tree, Tree]
) -> None:
    anas, _ = trees

    response = request_upload(api, beto, anas.lease_id)

    assert response.status_code == 404
    assert response.json()["code"] == "not_found"


def test_owner_cannot_open_another_owners_document(
    api: TestClient,
    storage: FakeStorage,
    ana: dict[str, str],
    beto: dict[str, str],
    trees: tuple[Tree, Tree],
) -> None:
    anas, _ = trees
    upload(api, storage, ana, anas.lease_id)

    response = api.get(f"/api/leases/{anas.lease_id}/document", headers=beto)

    assert response.status_code == 404
    assert response.json()["code"] == "not_found"
    assert "url" not in response.json()


def test_owner_cannot_attach_a_document_to_another_owners_lease(
    api: TestClient,
    storage: FakeStorage,
    beto: dict[str, str],
    trees: tuple[Tree, Tree],
    admin_engine: Engine,
) -> None:
    anas, betos = trees
    # Beto uploads a real file to his own folder...
    path = request_upload(api, beto, betos.lease_id).json()["path"]
    storage.upload(path, PDF)

    # ...and tries to hang it on Ana's lease.
    response = api.post(f"/api/leases/{anas.lease_id}/document", json={"path": path}, headers=beto)

    assert response.status_code == 404
    assert stored_path(admin_engine, anas.lease_id) is None


def test_owner_cannot_take_another_owners_file(
    api: TestClient,
    storage: FakeStorage,
    ana: dict[str, str],
    beto: dict[str, str],
    trees: tuple[Tree, Tree],
    admin_engine: Engine,
) -> None:
    """Confirming a path outside the lease's own folder would hand over someone's file."""
    anas, betos = trees
    upload(api, storage, ana, anas.lease_id)
    anas_path = stored_path(admin_engine, anas.lease_id)

    response = api.post(
        f"/api/leases/{betos.lease_id}/document", json={"path": anas_path}, headers=beto
    )

    assert response.status_code == 404
    assert stored_path(admin_engine, betos.lease_id) is None
    # And Ana's file is still there: a rejected confirmation must not delete it.
    assert list(storage.objects) == [anas_path]


@pytest.mark.parametrize(
    "path",
    [
        "{owner}/leases/{lease}/../../../otro/archivo.pdf",
        "{owner}/leases/{lease}/archivo.pdf",
        "{owner}/leases/{lease}/{upload}/sub/archivo.pdf",
        "/{owner}/leases/{lease}/{upload}/archivo.pdf",
        "",
    ],
)
def test_confirmation_only_takes_paths_the_api_handed_out(
    api: TestClient,
    storage: FakeStorage,
    ana: dict[str, str],
    two_owners: tuple[UUID, UUID],
    trees: tuple[Tree, Tree],
    admin_engine: Engine,
    path: str,
) -> None:
    anas, _ = trees
    path = path.format(owner=two_owners[0], lease=anas.lease_id, upload=uuid4())
    storage.upload(path, PDF)

    response = api.post(f"/api/leases/{anas.lease_id}/document", json={"path": path}, headers=ana)

    assert response.status_code in (404, 422)
    assert stored_path(admin_engine, anas.lease_id) is None


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("post", f"/api/leases/{uuid4()}/document/upload-url"),
        ("post", f"/api/leases/{uuid4()}/document"),
        ("get", f"/api/leases/{uuid4()}/document"),
    ],
)
def test_every_route_requires_a_token(api: TestClient, method: str, path: str) -> None:
    response = api.request(method, path, json={})

    assert response.status_code == 401
    assert response.json()["code"] == "unauthorized"


# Storage is down


class BrokenStorage(FakeStorage):
    def create_upload_url(self, path: str) -> str:
        raise StorageError("down")

    def size(self, path: str) -> int | None:
        raise StorageError("down")

    def create_download_url(self, path: str, expires_in: int) -> str:
        raise StorageError("down")


def test_when_storage_is_down_the_owner_gets_a_clear_error(
    api: TestClient,
    storage: FakeStorage,
    ana: dict[str, str],
    two_owners: tuple[UUID, UUID],
    trees: tuple[Tree, Tree],
    admin_engine: Engine,
) -> None:
    anas, _ = trees
    upload(api, storage, ana, anas.lease_id)
    good_path = stored_path(admin_engine, anas.lease_id)
    app.dependency_overrides[get_storage] = lambda: BrokenStorage()
    new_path = f"{two_owners[0]}/leases/{anas.lease_id}/{uuid4()}/otro.pdf"

    responses = [
        request_upload(api, ana, anas.lease_id),
        api.post(f"/api/leases/{anas.lease_id}/document", json={"path": new_path}, headers=ana),
        api.get(f"/api/leases/{anas.lease_id}/document", headers=ana),
    ]

    assert [response.status_code for response in responses] == [503, 503, 503]
    assert {response.json()["code"] for response in responses} == {"storage_unavailable"}
    assert stored_path(admin_engine, anas.lease_id) == good_path
