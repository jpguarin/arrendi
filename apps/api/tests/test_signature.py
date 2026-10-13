"""The owner's signature: uploading it, seeing it, replacing it and taking it away."""

from datetime import date
from io import BytesIO
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw
from sqlalchemy import Engine, text

from app.dates import today_in_bogota
from app.main import app
from tests.conftest import FakeStorage, MakeToken, Tree, bearer

MB = 1024 * 1024


def drawing(
    size: tuple[int, int] = (900, 500), kind: str = "PNG", background: object = (0, 0, 0, 0)
) -> bytes:
    """An image with a few dark strokes in the middle, like a signature."""
    image = Image.new("RGBA", size, background)
    pen = ImageDraw.Draw(image)
    width, height = size
    pen.line(
        [(width * 0.3, height * 0.6), (width * 0.5, height * 0.4), (width * 0.7, height * 0.6)],
        fill=(20, 38, 76, 255),
        width=6,
    )
    out = BytesIO()
    (image.convert("RGB") if kind == "JPEG" else image).save(out, kind)
    return out.getvalue()


PNG = drawing()
JPG = drawing(kind="JPEG", background=(255, 255, 255, 255))


@pytest.fixture
def ana(two_owners: tuple[UUID, UUID], make_token: MakeToken) -> dict[str, str]:
    return bearer(make_token(two_owners[0]))


@pytest.fixture
def beto(two_owners: tuple[UUID, UUID], make_token: MakeToken) -> dict[str, str]:
    return bearer(make_token(two_owners[1]))


@pytest.fixture(autouse=True)
def today(storage: FakeStorage) -> None:
    app.dependency_overrides[today_in_bogota] = lambda: date(2026, 10, 3)


def request_upload(
    api: TestClient,
    headers: dict[str, str],
    filename: str = "firma.png",
    content_type: str = "image/png",
    size: int = len(PNG),
):
    return api.post(
        "/api/settings/signature/upload-url",
        json={"filename": filename, "content_type": content_type, "size": size},
        headers=headers,
    )


def upload(
    api: TestClient,
    storage: FakeStorage,
    headers: dict[str, str],
    content: bytes = PNG,
    **request: object,
):
    """The whole flow: ask for the link, send the file to storage, confirm."""
    path = request_upload(api, headers, **request).json()["path"]
    storage.upload(path, content)
    return api.post("/api/settings/signature", json={"path": path}, headers=headers)


def stored_path(admin_engine: Engine, owner_id: UUID) -> str | None:
    with admin_engine.connect() as connection:
        return connection.execute(
            text("select signature_path from owners where id = :id"), {"id": owner_id}
        ).scalar_one()


def has_signature(api: TestClient, headers: dict[str, str]) -> bool:
    return api.get("/api/settings", headers=headers).json()["has_signature"]


# Upload link


def test_upload_link_points_inside_the_owners_signature_folder(
    api: TestClient, ana: dict[str, str], two_owners: tuple[UUID, UUID]
) -> None:
    response = request_upload(api, ana, filename="Mi firma (final).PNG")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["path"].startswith(f"{two_owners[0]}/signature/")
    assert body["path"].endswith("/Mi-firma-final.png")
    assert body["upload_url"].endswith(f"{body['path']}?token=signed")


@pytest.mark.parametrize(
    ("request_fields", "code"),
    [
        ({"content_type": "application/pdf", "filename": "firma.pdf"}, "unsupported_file_type"),
        ({"content_type": "image/gif", "filename": "firma.gif"}, "unsupported_file_type"),
        ({"size": 2 * MB + 1}, "file_too_large"),
    ],
)
def test_upload_link_is_refused_for_what_is_not_a_small_png_or_jpg(
    api: TestClient, ana: dict[str, str], request_fields: dict, code: str
) -> None:
    response = request_upload(api, ana, **request_fields)

    assert response.status_code == 422
    assert response.json()["code"] == code


# Confirming


@pytest.mark.parametrize(
    ("content", "request_fields"),
    [(PNG, {}), (JPG, {"filename": "firma.jpg", "content_type": "image/jpeg", "size": len(JPG)})],
    ids=["png", "jpg"],
)
def test_signature_is_stored_as_a_small_png_cut_to_its_strokes(
    api: TestClient,
    ana: dict[str, str],
    two_owners: tuple[UUID, UUID],
    storage: FakeStorage,
    admin_engine: Engine,
    content: bytes,
    request_fields: dict,
) -> None:
    response = upload(api, storage, ana, content, **request_fields)

    assert response.status_code == 200, response.text
    assert response.json()["has_signature"] is True
    path = stored_path(admin_engine, two_owners[0])
    assert path.startswith(f"{two_owners[0]}/signature/") and path.endswith("/firma.png")
    # Only the signature is left: what the browser sent is gone.
    assert list(storage.objects) == [path]
    with Image.open(BytesIO(storage.objects[path])) as stored:
        assert stored.format == "PNG"
        assert stored.width <= 600 and stored.height <= 200
        # The empty margin around the strokes went away: they reach the edges.
        assert stored.width > stored.height * 1.2


def test_small_signature_is_not_blown_up(
    api: TestClient, ana: dict[str, str], storage: FakeStorage
) -> None:
    upload(api, storage, ana, drawing(size=(120, 60)))

    (stored,) = storage.objects.values()
    with Image.open(BytesIO(stored)) as image:
        assert image.width <= 120 and image.height <= 60


AS_JPG = {"filename": "firma.jpg", "content_type": "image/jpeg"}


@pytest.mark.parametrize(
    ("content", "request_fields"),
    [
        (b"\x89PNG\r\n\x1a\n" + b"x" * 200, {}),
        (b"\xff\xd8\xff\xe0" + b"x" * 200, AS_JPG),
        (drawing(background=(255, 255, 255, 255))[:300], {}),
    ],
    ids=["not a png", "not a jpg", "cut short"],
)
def test_file_that_is_not_really_an_image_is_refused_and_removed(
    api: TestClient,
    ana: dict[str, str],
    storage: FakeStorage,
    content: bytes,
    request_fields: dict,
) -> None:
    response = upload(api, storage, ana, content, **request_fields)

    assert response.status_code == 422
    assert response.json()["code"] == "invalid_image"
    assert storage.objects == {}
    assert has_signature(api, ana) is False


def test_blank_image_is_refused(api: TestClient, ana: dict[str, str], storage: FakeStorage) -> None:
    blank = BytesIO()
    Image.new("RGBA", (400, 200), (255, 255, 255, 255)).save(blank, "PNG")

    response = upload(api, storage, ana, blank.getvalue())

    assert response.status_code == 422
    assert response.json()["code"] == "invalid_image"
    assert storage.objects == {}


def test_file_that_lies_about_its_type_is_refused(
    api: TestClient, ana: dict[str, str], storage: FakeStorage
) -> None:
    response = upload(api, storage, ana, b"%PDF-1.7\n" + b"x" * 100)

    assert response.status_code == 422
    assert response.json()["code"] == "unsupported_file_type"
    assert storage.objects == {}


def test_file_larger_than_it_said_is_refused(
    api: TestClient, ana: dict[str, str], storage: FakeStorage
) -> None:
    response = upload(api, storage, ana, PNG + b"\x00" * (2 * MB))

    assert response.status_code == 422
    assert response.json()["code"] == "file_too_large"
    assert storage.objects == {}


def test_confirming_what_never_arrived_is_an_error(api: TestClient, ana: dict[str, str]) -> None:
    path = request_upload(api, ana).json()["path"]

    response = api.post("/api/settings/signature", json={"path": path}, headers=ana)

    assert (response.status_code, response.json()["code"]) == (400, "document_not_uploaded")


# Seeing it, replacing it, removing it


def test_signature_has_a_temporary_link(
    api: TestClient, ana: dict[str, str], two_owners: tuple[UUID, UUID], storage: FakeStorage
) -> None:
    assert api.get("/api/settings/signature", headers=ana).status_code == 404
    upload(api, storage, ana)

    response = api.get("/api/settings/signature", headers=ana)

    assert response.status_code == 200
    body = response.json()
    assert f"/download/{two_owners[0]}/signature/" in body["url"]
    assert (body["name"], body["expires_in"]) == ("firma.png", 300)


def test_new_signature_replaces_the_one_before_and_its_file(
    api: TestClient,
    ana: dict[str, str],
    two_owners: tuple[UUID, UUID],
    storage: FakeStorage,
    admin_engine: Engine,
) -> None:
    upload(api, storage, ana)
    first = stored_path(admin_engine, two_owners[0])

    upload(api, storage, ana, JPG, filename="otra.jpg", content_type="image/jpeg", size=len(JPG))

    second = stored_path(admin_engine, two_owners[0])
    assert second != first
    assert list(storage.objects) == [second]


def test_removing_the_signature_removes_its_file(
    api: TestClient, ana: dict[str, str], storage: FakeStorage
) -> None:
    upload(api, storage, ana)

    response = api.delete("/api/settings/signature", headers=ana)

    assert response.status_code == 200
    assert response.json()["has_signature"] is False
    assert storage.objects == {}
    # Nothing left to remove; it is not an error.
    assert api.delete("/api/settings/signature", headers=ana).status_code == 200


def test_signature_a_bill_was_issued_with_stays_in_storage(
    api: TestClient,
    ana: dict[str, str],
    two_owners: tuple[UUID, UUID],
    trees: tuple[Tree, Tree],
    storage: FakeStorage,
    admin_engine: Engine,
) -> None:
    upload(api, storage, ana)
    signed_with = stored_path(admin_engine, two_owners[0])
    api.post(f"/api/leases/{trees[0].lease_id}/bills", headers=ana)

    api.delete("/api/settings/signature", headers=ana)

    # The owner has none now, but the bill still needs its own to be drawn again.
    assert has_signature(api, ana) is False
    assert signed_with in storage.objects


# Isolation


def test_owner_cannot_confirm_a_file_in_another_owners_folder(
    api: TestClient,
    ana: dict[str, str],
    beto: dict[str, str],
    two_owners: tuple[UUID, UUID],
    storage: FakeStorage,
    admin_engine: Engine,
) -> None:
    anas_path = request_upload(api, ana).json()["path"]
    storage.upload(anas_path, PNG)

    response = api.post("/api/settings/signature", json={"path": anas_path}, headers=beto)

    assert response.status_code == 404
    # Ana's file was not read, moved or deleted, and Beto has no signature.
    assert storage.objects == {anas_path: PNG}
    assert stored_path(admin_engine, two_owners[1]) is None


def test_each_owner_sees_and_removes_only_their_own_signature(
    api: TestClient,
    ana: dict[str, str],
    beto: dict[str, str],
    two_owners: tuple[UUID, UUID],
    storage: FakeStorage,
    admin_engine: Engine,
) -> None:
    upload(api, storage, ana)

    assert has_signature(api, beto) is False
    assert api.get("/api/settings/signature", headers=beto).status_code == 404
    api.delete("/api/settings/signature", headers=beto)

    assert has_signature(api, ana) is True
    assert stored_path(admin_engine, two_owners[0]) in storage.objects


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("post", "/api/settings/signature/upload-url"),
        ("post", "/api/settings/signature"),
        ("get", "/api/settings/signature"),
        ("delete", "/api/settings/signature"),
    ],
)
def test_every_route_requires_a_token(api: TestClient, method: str, path: str) -> None:
    response = getattr(api, method)(path)

    assert response.status_code == 401
