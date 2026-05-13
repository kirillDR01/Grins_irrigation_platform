"""PhotoService S3 error mapping tests (Cluster A).

Verifies that boto3 exception classes raised by ``put_object`` are wrapped
into ``S3UploadError`` with the correct ``retryable`` flag:

- ClientError / EndpointConnectionError / BotoCoreError → retryable=True
- NoCredentialsError → retryable=False
- happy path → returns UploadResult with the bucket/key passed through
"""

from __future__ import annotations

from io import BytesIO
from unittest.mock import MagicMock

import pytest
from botocore.exceptions import (
    BotoCoreError,
    ClientError,
    EndpointConnectionError,
    NoCredentialsError,
)
from PIL import Image

from grins_platform.exceptions.upload import S3UploadError
from grins_platform.services.photo_service import PhotoService, UploadContext


def _tiny_jpeg() -> bytes:
    """Build a real 1×1 RGB JPEG in memory — passes MIME sniff for
    CUSTOMER_PHOTO. Avoids hand-encoded hex that's brittle to wrap/format."""
    buf = BytesIO()
    Image.new("RGB", (1, 1), color=(0, 0, 0)).save(buf, format="JPEG")
    return buf.getvalue()


_TINY_JPEG = _tiny_jpeg()


def _make_client(error: Exception | None = None) -> MagicMock:
    client = MagicMock()
    if error is None:
        client.put_object = MagicMock(return_value={"ETag": '"abc"'})
    else:
        client.put_object = MagicMock(side_effect=error)
    return client


def _service(client: MagicMock) -> PhotoService:
    return PhotoService(s3_client=client, bucket="test-bucket")


@pytest.mark.unit
def test_upload_file_raises_s3_error_on_client_error() -> None:
    err = ClientError(
        {"Error": {"Code": "AccessDenied", "Message": "x"}},
        "PutObject",
    )
    svc = _service(_make_client(error=err))
    with pytest.raises(S3UploadError) as excinfo:
        svc.upload_file(
            _TINY_JPEG,
            "test.jpg",
            UploadContext.CUSTOMER_PHOTO,
            strip_metadata=False,
        )
    assert excinfo.value.retryable is True


@pytest.mark.unit
def test_upload_file_raises_s3_error_on_endpoint_connection_error() -> None:
    err = EndpointConnectionError(endpoint_url="https://example.invalid")
    svc = _service(_make_client(error=err))
    with pytest.raises(S3UploadError) as excinfo:
        svc.upload_file(
            _TINY_JPEG,
            "test.jpg",
            UploadContext.CUSTOMER_PHOTO,
            strip_metadata=False,
        )
    assert excinfo.value.retryable is True


@pytest.mark.unit
def test_upload_file_raises_s3_error_on_botocore_error() -> None:
    # BotoCoreError is abstract; instantiate via subclass-style direct call.
    class _Boom(BotoCoreError):
        fmt = "boom"

    svc = _service(_make_client(error=_Boom()))
    with pytest.raises(S3UploadError) as excinfo:
        svc.upload_file(
            _TINY_JPEG,
            "test.jpg",
            UploadContext.CUSTOMER_PHOTO,
            strip_metadata=False,
        )
    assert excinfo.value.retryable is True


@pytest.mark.unit
def test_upload_file_raises_s3_error_on_no_credentials() -> None:
    svc = _service(_make_client(error=NoCredentialsError()))
    with pytest.raises(S3UploadError) as excinfo:
        svc.upload_file(
            _TINY_JPEG,
            "test.jpg",
            UploadContext.CUSTOMER_PHOTO,
            strip_metadata=False,
        )
    assert excinfo.value.retryable is False


@pytest.mark.unit
def test_upload_file_passes_through_on_success() -> None:
    client = _make_client()
    svc = _service(client)
    result = svc.upload_file(
        _TINY_JPEG,
        "test.jpg",
        UploadContext.CUSTOMER_PHOTO,
        strip_metadata=False,
    )
    assert result.file_key.endswith(".jpg")
    assert result.content_type == "image/jpeg"
    client.put_object.assert_called_once()
