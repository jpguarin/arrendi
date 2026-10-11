"""SupabaseStorage speaks Supabase's Storage REST API. Checked against a stand-in server."""

import json

import httpx2
import pytest

from app.storage import StorageError, SupabaseStorage

BASE = "https://project.supabase.co/storage/v1"
PATH = "owner-1/leases/lease-1/upload-1/contrato.pdf"


def make_storage(handler) -> tuple[SupabaseStorage, list[httpx2.Request]]:
    requests: list[httpx2.Request] = []

    def record(request: httpx2.Request) -> httpx2.Response:
        requests.append(request)
        return handler(request)

    storage = SupabaseStorage(
        "https://project.supabase.co/",
        "sb_secret_test",
        "arrendi",
        transport=httpx2.MockTransport(record),
    )
    return storage, requests


def test_every_request_carries_the_secret_key() -> None:
    storage, requests = make_storage(lambda request: httpx2.Response(200, json={"size": 1}))

    storage.size(PATH)

    assert requests[0].headers["apikey"] == "sb_secret_test"
    assert requests[0].headers["authorization"] == "Bearer sb_secret_test"


def test_upload_url_is_signed_for_the_path() -> None:
    signed = f"/object/upload/sign/arrendi/{PATH}?token=abc"
    storage, requests = make_storage(lambda request: httpx2.Response(200, json={"url": signed}))

    url = storage.create_upload_url(PATH)

    assert url == BASE + signed
    assert requests[0].method == "POST"
    assert str(requests[0].url) == f"{BASE}/object/upload/sign/arrendi/{PATH}"


def test_download_url_asks_for_the_expiry() -> None:
    signed = f"/object/sign/arrendi/{PATH}?token=abc"
    storage, requests = make_storage(
        lambda request: httpx2.Response(200, json={"signedURL": signed})
    )

    url = storage.create_download_url(PATH, 300)

    assert url == BASE + signed
    assert requests[0].method == "POST"
    assert str(requests[0].url) == f"{BASE}/object/sign/arrendi/{PATH}"
    assert json.loads(requests[0].content) == {"expiresIn": 300}


@pytest.mark.parametrize("info", [{"size": 1234}, {"metadata": {"size": 1234}}, {"size": "1234"}])
def test_size_reads_what_storage_reports(info: dict[str, object]) -> None:
    storage, requests = make_storage(lambda request: httpx2.Response(200, json=info))

    assert storage.size(PATH) == 1234
    assert str(requests[0].url) == f"{BASE}/object/info/arrendi/{PATH}"


@pytest.mark.parametrize("status", [400, 404])
def test_size_of_a_missing_file_is_none(status: int) -> None:
    storage, _ = make_storage(lambda request: httpx2.Response(status, json={"error": "not_found"}))

    assert storage.size(PATH) is None


def test_read_start_asks_only_for_the_first_bytes() -> None:
    storage, requests = make_storage(lambda request: httpx2.Response(206, content=b"%PDF-1.7"))

    assert storage.read_start(PATH, 8) == b"%PDF-1.7"
    assert requests[0].headers["range"] == "bytes=0-7"
    assert str(requests[0].url) == f"{BASE}/object/arrendi/{PATH}"


def test_read_start_cuts_the_answer_if_storage_ignores_the_range() -> None:
    storage, _ = make_storage(lambda request: httpx2.Response(200, content=b"%PDF-1.7" + b"x" * 99))

    assert storage.read_start(PATH, 8) == b"%PDF-1.7"


def test_delete_names_the_file() -> None:
    storage, requests = make_storage(lambda request: httpx2.Response(200, json=[]))

    storage.delete(PATH)

    assert requests[0].method == "DELETE"
    assert str(requests[0].url) == f"{BASE}/object/arrendi"
    assert json.loads(requests[0].content) == {"prefixes": [PATH]}


def test_paths_are_escaped() -> None:
    storage, requests = make_storage(lambda request: httpx2.Response(200, json={"size": 1}))

    storage.size("owner/leases/lease/upload/a b#c.pdf")

    assert requests[0].url.raw_path.endswith(b"/a%20b%23c.pdf")


@pytest.mark.parametrize(
    "call",
    [
        lambda storage: storage.create_upload_url(PATH),
        lambda storage: storage.create_download_url(PATH, 300),
        lambda storage: storage.size(PATH),
        lambda storage: storage.read_start(PATH, 8),
        lambda storage: storage.delete(PATH),
    ],
)
def test_an_error_from_storage_is_a_storage_error(call) -> None:
    storage, _ = make_storage(lambda request: httpx2.Response(500, json={"error": "boom"}))

    with pytest.raises(StorageError):
        call(storage)


def test_no_answer_from_storage_is_a_storage_error() -> None:
    def no_network(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ConnectError("no network")

    storage, _ = make_storage(no_network)

    with pytest.raises(StorageError):
        storage.size(PATH)


def test_upload_sends_the_file_and_replaces_the_one_there() -> None:
    storage, requests = make_storage(lambda request: httpx2.Response(200, json={"Key": PATH}))

    storage.upload(PATH, b"%PDF-1.4 file", "application/pdf")

    assert requests[0].method == "POST"
    assert str(requests[0].url) == f"{BASE}/object/arrendi/{PATH}"
    assert requests[0].headers["content-type"] == "application/pdf"
    assert requests[0].headers["x-upsert"] == "true"
    assert requests[0].content == b"%PDF-1.4 file"


def test_upload_that_storage_refuses_is_an_error() -> None:
    storage, _ = make_storage(lambda request: httpx2.Response(413, json={"error": "too large"}))

    with pytest.raises(StorageError):
        storage.upload(PATH, b"x", "application/pdf")


def test_download_returns_the_whole_file() -> None:
    storage, requests = make_storage(lambda request: httpx2.Response(200, content=b"%PDF-1.4"))

    assert storage.download(PATH) == b"%PDF-1.4"
    assert requests[0].method == "GET"
    assert str(requests[0].url) == f"{BASE}/object/arrendi/{PATH}"
