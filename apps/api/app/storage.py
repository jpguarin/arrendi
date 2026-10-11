"""Private file storage. The only module that uses Supabase's secret key.

Nothing here knows about owners: callers check that the path belongs to the owner of the
request before they ask for a link.
"""

from typing import Protocol
from urllib.parse import quote

import httpx2

TIMEOUT_SECONDS = 10


class StorageError(Exception):
    """Storage did not answer, or answered with an error."""


class Storage(Protocol):
    def create_upload_url(self, path: str) -> str:
        """A link the browser can send one file to, for that path only."""

    def upload(self, path: str, content: bytes, content_type: str) -> None:
        """Stores a file the API itself made, replacing the one at that path if any."""

    def download(self, path: str) -> bytes:
        """The whole stored file. Only for files the API made, which are small."""

    def size(self, path: str) -> int | None:
        """Size in bytes of the stored file, or None if there is none."""

    def read_start(self, path: str, length: int) -> bytes:
        """The first bytes of the stored file."""

    def delete(self, path: str) -> None: ...

    def create_download_url(self, path: str, expires_in: int) -> str:
        """A link to read the file that stops working after `expires_in` seconds."""


class SupabaseStorage:
    def __init__(
        self,
        supabase_url: str,
        secret_key: str,
        bucket: str,
        transport: httpx2.BaseTransport | None = None,
    ) -> None:
        self.base_url = f"{supabase_url.rstrip('/')}/storage/v1"
        self.bucket = bucket
        self.client = httpx2.Client(
            headers={"apikey": secret_key, "Authorization": f"Bearer {secret_key}"},
            timeout=TIMEOUT_SECONDS,
            transport=transport,
        )

    def _url(self, prefix: str, path: str = "") -> str:
        return f"{self.base_url}/{prefix}/{self.bucket}" + (f"/{quote(path)}" if path else "")

    def _request(self, method: str, url: str, **kwargs: object) -> httpx2.Response:
        try:
            return self.client.request(method, url, **kwargs)
        except httpx2.HTTPError as error:
            raise StorageError(str(error)) from error

    @staticmethod
    def _check(response: httpx2.Response) -> httpx2.Response:
        if response.is_error:
            raise StorageError(f"storage answered {response.status_code}")
        return response

    def create_upload_url(self, path: str) -> str:
        response = self._check(self._request("POST", self._url("object/upload/sign", path)))
        return self.base_url + response.json()["url"]

    def upload(self, path: str, content: bytes, content_type: str) -> None:
        # Without `x-upsert`, storage refuses a path that already has a file.
        headers = {"Content-Type": content_type, "x-upsert": "true"}
        self._check(
            self._request("POST", self._url("object", path), content=content, headers=headers)
        )

    def download(self, path: str) -> bytes:
        return self._check(self._request("GET", self._url("object", path))).content

    def size(self, path: str) -> int | None:
        response = self._request("GET", self._url("object/info", path))
        # Storage answers 400 or 404 for a file that is not there, depending on the version.
        if response.status_code in (400, 404):
            return None
        info = self._check(response).json()
        size = info.get("size", (info.get("metadata") or {}).get("size"))
        if size is None:
            raise StorageError("storage did not report the size")
        return int(size)

    def read_start(self, path: str, length: int) -> bytes:
        headers = {"Range": f"bytes=0-{length - 1}"}
        try:
            # Streamed, so a storage that ignores the range does not send us the whole file.
            with self.client.stream("GET", self._url("object", path), headers=headers) as response:
                self._check(response)
                start = b""
                for chunk in response.iter_bytes():
                    start += chunk
                    if len(start) >= length:
                        break
                return start[:length]
        except httpx2.HTTPError as error:
            raise StorageError(str(error)) from error

    def delete(self, path: str) -> None:
        self._check(self._request("DELETE", self._url("object"), json={"prefixes": [path]}))

    def create_download_url(self, path: str, expires_in: int) -> str:
        response = self._check(
            self._request("POST", self._url("object/sign", path), json={"expiresIn": expires_in})
        )
        return self.base_url + response.json()["signedURL"]
