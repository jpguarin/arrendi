"""The lease's inventory: a second file of the lease, with the same flow as the signed lease.

The checks on the file itself (type, size, real content) are shared with the signed lease
and covered in test_documents.py; here, what is the inventory's own.
"""

from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

from app.dependencies import get_storage
from app.main import app
from app.storage import StorageError
from tests.conftest import FakeStorage, MakeToken, Tree, bearer

PDF = b"%PDF-1.7\n" + b"x" * 100
PNG = b"\x89PNG\r\n\x1a\n" + b"x" * 100


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
    filename: str = "inventario.pdf",
    content_type: str = "application/pdf",
    size: int = len(PDF),
    file: str = "inventory",
):
    return api.post(
        f"/api/leases/{lease_id}/{file}/upload-url",
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
    return api.post(f"/api/leases/{lease_id}/inventory", json={"path": path}, headers=headers)


def stored_path(admin_engine: Engine, lease_id: UUID, column: str = "inventory_path") -> str | None:
    with admin_engine.connect() as connection:
        return connection.execute(
            text(f"select {column} from leases where id = :id"), {"id": lease_id}
        ).scalar_one()


# Upload link


def test_upload_link_points_inside_the_owners_inventory_folder(
    api: TestClient,
    storage: FakeStorage,
    ana: dict[str, str],
    two_owners: tuple[UUID, UUID],
    trees: tuple[Tree, Tree],
) -> None:
    anas, _ = trees

    response = request_upload(api, ana, anas.lease_id, filename="Inventario Apto 2.PDF")

    assert response.status_code == 200, response.text
    folder, upload_id, name = response.json()["path"].rsplit("/", 2)
    assert folder == f"{two_owners[0]}/inventories/{anas.lease_id}"
    assert UUID(upload_id)
    assert name == "Inventario-Apto-2.pdf"


def test_a_name_with_nothing_usable_becomes_inventario(
    api: TestClient, storage: FakeStorage, ana: dict[str, str], trees: tuple[Tree, Tree]
) -> None:
    anas, _ = trees

    response = request_upload(api, ana, anas.lease_id, filename="???")

    assert response.json()["path"].rsplit("/", 1)[-1] == "inventario.pdf"


def test_the_inventory_has_the_same_limits_as_the_signed_lease(
    api: TestClient, storage: FakeStorage, ana: dict[str, str], trees: tuple[Tree, Tree]
) -> None:
    anas, _ = trees

    wrong_type = request_upload(api, ana, anas.lease_id, content_type="image/gif")
    too_large = request_upload(api, ana, anas.lease_id, size=10 * 1024 * 1024 + 1)
    fake = upload(api, storage, ana, anas.lease_id, b"MZ\x90\x00 this is a program")

    assert wrong_type.json()["code"] == "unsupported_file_type"
    assert too_large.json()["code"] == "file_too_large"
    assert fake.status_code == 422
    assert storage.objects == {}


# Confirmation


def test_confirming_attaches_the_inventory_and_leaves_the_signed_lease_alone(
    api: TestClient,
    storage: FakeStorage,
    ana: dict[str, str],
    trees: tuple[Tree, Tree],
    admin_engine: Engine,
) -> None:
    anas, _ = trees

    response = upload(
        api, storage, ana, anas.lease_id, PNG, filename="foto.png", content_type="image/png"
    )

    assert response.status_code == 200, response.text
    lease = response.json()
    assert lease["inventory_name"] == "foto.png"
    assert lease["inventory_uploaded_at"] is not None
    assert lease["document_name"] is None
    assert lease["document_uploaded_at"] is None
    assert stored_path(admin_engine, anas.lease_id, "document_path") is None
    assert api.get(f"/api/leases/{anas.lease_id}", headers=ana).json() == lease


def test_confirming_before_uploading_is_an_error(
    api: TestClient, storage: FakeStorage, ana: dict[str, str], trees: tuple[Tree, Tree]
) -> None:
    anas, _ = trees
    path = request_upload(api, ana, anas.lease_id).json()["path"]

    response = api.post(f"/api/leases/{anas.lease_id}/inventory", json={"path": path}, headers=ana)

    assert response.status_code == 400
    assert response.json()["code"] == "document_not_uploaded"


def test_replacing_removes_the_previous_inventory(
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

    assert response.json()["inventory_name"] == "nuevo.pdf"
    new_path = stored_path(admin_engine, anas.lease_id)
    assert new_path != old_path
    assert list(storage.objects) == [new_path]


def test_a_failed_replacement_keeps_the_previous_inventory(
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


def test_confirming_the_same_inventory_twice_changes_nothing(
    api: TestClient,
    storage: FakeStorage,
    ana: dict[str, str],
    trees: tuple[Tree, Tree],
    admin_engine: Engine,
) -> None:
    anas, _ = trees
    first = upload(api, storage, ana, anas.lease_id)
    path = stored_path(admin_engine, anas.lease_id)

    again = api.post(f"/api/leases/{anas.lease_id}/inventory", json={"path": path}, headers=ana)

    assert again.status_code == 200
    assert again.json() == first.json()
    assert list(storage.objects) == [path]


def test_the_signed_lease_and_the_inventory_live_side_by_side(
    api: TestClient,
    storage: FakeStorage,
    ana: dict[str, str],
    trees: tuple[Tree, Tree],
    admin_engine: Engine,
) -> None:
    """Replacing one never removes the other."""
    anas, _ = trees
    document = request_upload(api, ana, anas.lease_id, filename="contrato.pdf", file="document")
    storage.upload(document.json()["path"], PDF)
    api.post(
        f"/api/leases/{anas.lease_id}/document",
        json={"path": document.json()["path"]},
        headers=ana,
    )
    upload(api, storage, ana, anas.lease_id, filename="uno.pdf")

    response = upload(api, storage, ana, anas.lease_id, filename="dos.pdf")

    assert (response.json()["document_name"], response.json()["inventory_name"]) == (
        "contrato.pdf",
        "dos.pdf",
    )
    assert sorted(storage.objects) == sorted(
        [
            stored_path(admin_engine, anas.lease_id, "document_path"),
            stored_path(admin_engine, anas.lease_id),
        ]
    )


def test_a_signed_lease_upload_cannot_be_confirmed_as_the_inventory(
    api: TestClient,
    storage: FakeStorage,
    ana: dict[str, str],
    trees: tuple[Tree, Tree],
    admin_engine: Engine,
) -> None:
    anas, _ = trees
    document_path = request_upload(api, ana, anas.lease_id, file="document").json()["path"]
    inventory_path = request_upload(api, ana, anas.lease_id).json()["path"]
    storage.upload(document_path, PDF)
    storage.upload(inventory_path, PDF)

    as_inventory = api.post(
        f"/api/leases/{anas.lease_id}/inventory", json={"path": document_path}, headers=ana
    )
    as_document = api.post(
        f"/api/leases/{anas.lease_id}/document", json={"path": inventory_path}, headers=ana
    )

    assert (as_inventory.status_code, as_document.status_code) == (404, 404)
    assert stored_path(admin_engine, anas.lease_id) is None
    assert stored_path(admin_engine, anas.lease_id, "document_path") is None


@pytest.mark.parametrize(
    "path",
    [
        "{owner}/inventories/{lease}/../../../otro/archivo.pdf",
        "{owner}/inventories/{lease}/archivo.pdf",
        "{owner}/inventories/{lease}/{upload}/sub/archivo.pdf",
        "{owner}/leases/{lease}/{upload}/archivo.pdf",
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

    response = api.post(f"/api/leases/{anas.lease_id}/inventory", json={"path": path}, headers=ana)

    assert response.status_code in (404, 422)
    assert stored_path(admin_engine, anas.lease_id) is None


# Reading


def test_the_owner_gets_a_temporary_link_to_the_inventory(
    api: TestClient,
    storage: FakeStorage,
    ana: dict[str, str],
    trees: tuple[Tree, Tree],
    admin_engine: Engine,
) -> None:
    anas, _ = trees
    upload(api, storage, ana, anas.lease_id)
    path = stored_path(admin_engine, anas.lease_id)

    response = api.get(f"/api/leases/{anas.lease_id}/inventory", headers=ana)

    assert response.status_code == 200
    assert response.json() == {
        "url": f"https://storage.test/download/{path}?token=signed&expires_in=300",
        "name": "inventario.pdf",
        "expires_in": 300,
    }


def test_a_lease_without_an_inventory_has_no_link(
    api: TestClient, storage: FakeStorage, ana: dict[str, str], trees: tuple[Tree, Tree]
) -> None:
    anas, _ = trees

    response = api.get(f"/api/leases/{anas.lease_id}/inventory", headers=ana)

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Este contrato no tiene inventario.",
        "code": "inventory_not_found",
    }


# Isolation: another owner's lease is a 404 on the three routes


def test_owner_cannot_get_an_upload_link_for_another_owners_lease(
    api: TestClient, storage: FakeStorage, beto: dict[str, str], trees: tuple[Tree, Tree]
) -> None:
    anas, _ = trees

    response = request_upload(api, beto, anas.lease_id)

    assert response.status_code == 404
    assert response.json()["code"] == "not_found"


def test_owner_cannot_open_another_owners_inventory(
    api: TestClient,
    storage: FakeStorage,
    ana: dict[str, str],
    beto: dict[str, str],
    trees: tuple[Tree, Tree],
) -> None:
    anas, _ = trees
    upload(api, storage, ana, anas.lease_id)

    response = api.get(f"/api/leases/{anas.lease_id}/inventory", headers=beto)

    assert response.status_code == 404
    assert response.json()["code"] == "not_found"
    assert "url" not in response.json()


def test_owner_cannot_attach_an_inventory_to_another_owners_lease(
    api: TestClient,
    storage: FakeStorage,
    beto: dict[str, str],
    trees: tuple[Tree, Tree],
    admin_engine: Engine,
) -> None:
    anas, betos = trees
    path = request_upload(api, beto, betos.lease_id).json()["path"]
    storage.upload(path, PDF)

    response = api.post(f"/api/leases/{anas.lease_id}/inventory", json={"path": path}, headers=beto)

    assert response.status_code == 404
    assert stored_path(admin_engine, anas.lease_id) is None


def test_owner_cannot_take_another_owners_inventory(
    api: TestClient,
    storage: FakeStorage,
    ana: dict[str, str],
    beto: dict[str, str],
    trees: tuple[Tree, Tree],
    admin_engine: Engine,
) -> None:
    anas, betos = trees
    upload(api, storage, ana, anas.lease_id)
    anas_path = stored_path(admin_engine, anas.lease_id)

    response = api.post(
        f"/api/leases/{betos.lease_id}/inventory", json={"path": anas_path}, headers=beto
    )

    assert response.status_code == 404
    assert stored_path(admin_engine, betos.lease_id) is None
    assert list(storage.objects) == [anas_path]


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("post", f"/api/leases/{uuid4()}/inventory/upload-url"),
        ("post", f"/api/leases/{uuid4()}/inventory"),
        ("get", f"/api/leases/{uuid4()}/inventory"),
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
    new_path = f"{two_owners[0]}/inventories/{anas.lease_id}/{uuid4()}/otro.pdf"

    responses = [
        request_upload(api, ana, anas.lease_id),
        api.post(f"/api/leases/{anas.lease_id}/inventory", json={"path": new_path}, headers=ana),
        api.get(f"/api/leases/{anas.lease_id}/inventory", headers=ana),
    ]

    assert [response.status_code for response in responses] == [503, 503, 503]
    assert {response.json()["code"] for response in responses} == {"storage_unavailable"}
    assert stored_path(admin_engine, anas.lease_id) == good_path
