from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints


class UploadUrlRequest(BaseModel):
    filename: Annotated[str, StringConstraints(max_length=500)]
    content_type: Annotated[str, StringConstraints(max_length=100)]
    size: Annotated[int, Field(strict=True, gt=0)]


class UploadUrlResponse(BaseModel):
    # The browser sends the file here with a PUT, straight to storage.
    upload_url: str
    # Sent back to confirm the upload.
    path: str


class DocumentConfirm(BaseModel):
    path: Annotated[str, StringConstraints(max_length=500)]


class DocumentUrlResponse(BaseModel):
    url: str
    name: str
    expires_in: int
