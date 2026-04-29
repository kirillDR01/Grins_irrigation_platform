"""Secure file upload pipeline for photos, attachments, media, and receipts.

Handles magic-byte validation, EXIF stripping, UUID-based S3 keys,
pre-signed URL generation, and per-customer quota tracking.

Validates: Requirements 9.2, 9.6, 15.2, 49.5, 75.3, 77.1-77.6
"""

from __future__ import annotations

import io
import os
import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum
from typing import Any, Protocol
from urllib.parse import quote

import boto3
import magic
from botocore.config import Config as BotoConfig
from PIL import Image

from grins_platform.log_config import LoggerMixin

# ---------------------------------------------------------------------------
# S3 client protocol (avoids Any in public signatures)
# ---------------------------------------------------------------------------


class _S3Paginator(Protocol):
    """Minimal paginator interface."""

    def paginate(
        self,
        **kwargs: str,
    ) -> Iterable[dict[str, object]]: ...


class S3ClientProtocol(Protocol):
    """Minimal S3 client interface used by PhotoService."""

    def put_object(self, **kwargs: Any) -> dict[str, Any]: ...

    def delete_object(
        self,
        **kwargs: Any,
    ) -> dict[str, Any]: ...

    def generate_presigned_url(
        self,
        client_method: str,
        Params: dict[str, Any] | None = ...,  # noqa: N803
        ExpiresIn: int = ...,  # noqa: N803
    ) -> str: ...

    def get_paginator(
        self,
        operation: str,
    ) -> _S3Paginator: ...


# ---------------------------------------------------------------------------
# Upload context definitions
# ---------------------------------------------------------------------------


class UploadContext(str, Enum):
    """Supported upload contexts with distinct validation rules."""

    CUSTOMER_PHOTO = "customer_photo"
    CUSTOMER_DOCUMENT = "customer_document"
    LEAD_ATTACHMENT = "lead_attachment"
    MEDIA_LIBRARY = "media_library"
    RECEIPT = "receipt"


@dataclass(frozen=True)
class _ContextRules:
    """Validation rules for a specific upload context."""

    allowed_mimes: frozenset[str]
    max_bytes: int
    s3_prefix: str


_IMAGE_MIMES = frozenset(
    {
        "image/jpeg",
        "image/png",
        "image/heic",
        "image/heif",
    },
)

_RULES: dict[UploadContext, _ContextRules] = {
    UploadContext.CUSTOMER_PHOTO: _ContextRules(
        allowed_mimes=_IMAGE_MIMES,
        max_bytes=10 * 1024 * 1024,
        s3_prefix="customer-photos",
    ),
    UploadContext.CUSTOMER_DOCUMENT: _ContextRules(
        allowed_mimes=frozenset(
            {
                "image/jpeg",
                "image/png",
                "application/pdf",
                "application/vnd.openxmlformats-officedocument"
                ".wordprocessingml.document",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "application/msword",
                "application/vnd.ms-excel",
            },
        ),
        max_bytes=25 * 1024 * 1024,
        s3_prefix="customer-documents",
    ),
    UploadContext.LEAD_ATTACHMENT: _ContextRules(
        allowed_mimes=frozenset(
            {
                "image/jpeg",
                "image/png",
                "application/pdf",
                "application/vnd.openxmlformats-officedocument"
                ".wordprocessingml.document",
            },
        ),
        max_bytes=25 * 1024 * 1024,
        s3_prefix="lead-attachments",
    ),
    UploadContext.MEDIA_LIBRARY: _ContextRules(
        allowed_mimes=frozenset(
            {
                "image/jpeg",
                "image/png",
                "image/heic",
                "image/heif",
                "video/mp4",
                "video/quicktime",
            },
        ),
        max_bytes=50 * 1024 * 1024,
        s3_prefix="media-library",
    ),
    UploadContext.RECEIPT: _ContextRules(
        allowed_mimes=frozenset(
            {
                "image/jpeg",
                "image/png",
                "application/pdf",
            },
        ),
        max_bytes=10 * 1024 * 1024,
        s3_prefix="receipts",
    ),
}

# EXIF-strippable MIME types
_EXIF_STRIPPABLE = frozenset(
    {
        "image/jpeg",
        "image/png",
        "image/heic",
        "image/heif",
    },
)

# Pre-signed URL expiry in seconds (1 hour)
_PRESIGNED_EXPIRY = 3600

# Per-customer storage quota in bytes (500 MB)
CUSTOMER_QUOTA_BYTES = 500 * 1024 * 1024


@dataclass(frozen=True)
class UploadResult:
    """Result of a successful file upload."""

    file_key: str
    file_name: str
    file_size: int
    content_type: str


class PhotoService(LoggerMixin):
    """Secure file upload pipeline backed by S3-compatible storage."""

    DOMAIN = "files"

    def __init__(
        self,
        s3_client: S3ClientProtocol | None = None,
        bucket: str | None = None,
    ) -> None:
        super().__init__()
        self._bucket: str = (
            bucket
            or os.getenv(
                "S3_BUCKET_NAME",
                "grins-platform-files",
            )
            or "grins-platform-files"
        )
        self._client: S3ClientProtocol = s3_client or _build_default_client()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def validate_file(
        self,
        data: bytes,
        file_name: str,
        context: UploadContext,
    ) -> str:
        """Validate file via magic bytes and size.

        Returns detected MIME type.

        bughunt M-16: distinct exception types for the two rejection
        reasons so the API layer can translate to the right status:
        size → 413 Payload Too Large, MIME → 415 Unsupported Media Type.
        """
        rules = _RULES[context]

        # Size check — server-enforced even when the frontend gates the
        # input, since a direct API/curl call bypasses any browser cap.
        if len(data) > rules.max_bytes:
            max_mb = rules.max_bytes / (1024 * 1024)
            self.log_rejected(
                "validate_file",
                reason="file_too_large",
                file_name=file_name,
                size=len(data),
                max_bytes=rules.max_bytes,
            )
            msg = f"File exceeds maximum size of {max_mb:.0f} MB"
            raise ValueError(msg)

        # Magic-byte detection — never trust the multipart Content-Type;
        # check the actual bytes against the allow-list for this context.
        detected_mime = magic.from_buffer(data[:2048], mime=True)

        if detected_mime not in rules.allowed_mimes:
            self.log_rejected(
                "validate_file",
                reason="disallowed_mime",
                file_name=file_name,
                detected_mime=detected_mime,
                context=context.value,
            )
            msg = f"File type '{detected_mime}' is not allowed for {context.value}"
            raise TypeError(msg)

        return detected_mime

    def strip_exif(self, data: bytes, mime: str) -> bytes:
        """Strip EXIF/GPS metadata from image bytes.

        Returns cleaned bytes.
        """
        if mime not in _EXIF_STRIPPABLE:
            return data

        try:
            img = Image.open(io.BytesIO(data))
            # Re-save without EXIF by copying pixel data (avoids deprecated getdata())
            clean = Image.frombytes(img.mode, img.size, img.tobytes())

            buf = io.BytesIO()
            fmt = "JPEG" if mime == "image/jpeg" else "PNG"
            clean.save(buf, format=fmt)
            return buf.getvalue()
        except Exception:
            # If stripping fails, return original rather than block
            self.log_failed(
                "strip_exif",
                error=None,
                mime=mime,
            )
            return data

    def upload_file(
        self,
        data: bytes,
        file_name: str,
        context: UploadContext,
        *,
        strip_metadata: bool = True,
    ) -> UploadResult:
        """Validate, process, and upload a file to S3.

        Args:
            data: Raw file bytes.
            file_name: Original file name.
            context: Upload context determining rules.
            strip_metadata: Strip EXIF from images.

        Returns:
            UploadResult with S3 key and metadata.

        Raises:
            ValueError: On validation failure.
        """
        self.log_started(
            "upload_file",
            file_name=file_name,
            context=context.value,
            size=len(data),
        )

        # 1. Validate
        detected_mime = self.validate_file(
            data,
            file_name,
            context,
        )

        # 2. Strip EXIF if applicable
        processed = data
        if strip_metadata and detected_mime in _EXIF_STRIPPABLE:
            processed = self.strip_exif(data, detected_mime)

        # 3. Generate UUID-based key
        rules = _RULES[context]
        ext = _extension_for_mime(detected_mime)
        file_key = f"{rules.s3_prefix}/{uuid.uuid4()}{ext}"

        # 4. Upload to S3
        _ = self._client.put_object(
            Bucket=self._bucket,
            Key=file_key,
            Body=processed,
            ContentType=detected_mime,
        )

        result = UploadResult(
            file_key=file_key,
            file_name=file_name,
            file_size=len(processed),
            content_type=detected_mime,
        )

        self.log_completed(
            "upload_file",
            file_key=file_key,
            size=len(processed),
            context=context.value,
        )
        return result

    def generate_presigned_url(
        self,
        file_key: str,
        expiry: int = _PRESIGNED_EXPIRY,
        *,
        download_filename: str | None = None,
    ) -> str:
        """Generate a pre-signed download URL.

        When ``download_filename`` is provided, the URL carries a
        ``response-content-disposition=attachment; filename=…`` override
        so the browser saves the file to disk instead of rendering it
        inline. Leave it ``None`` for image-gallery contexts where an
        ``<img src>`` tag should render the object directly.
        """
        params: dict[str, Any] = {"Bucket": self._bucket, "Key": file_key}
        if download_filename:
            params["ResponseContentDisposition"] = format_attachment_disposition(
                download_filename
            )
        url: str = self._client.generate_presigned_url(
            "get_object",
            Params=params,
            ExpiresIn=expiry,
        )
        return url

    def delete_file(self, file_key: str) -> None:
        """Delete a file from S3."""
        _ = self._client.delete_object(
            Bucket=self._bucket,
            Key=file_key,
        )
        self.log_completed("delete_file", file_key=file_key)

    def get_customer_usage_bytes(
        self,
        customer_id: str,
    ) -> int:
        """Return total bytes stored under a customer prefix.

        Uses S3 list to sum object sizes.
        """
        prefix = f"customer-photos/{customer_id}/"
        total = 0
        paginator = self._client.get_paginator(
            "list_objects_v2",
        )
        pages: Iterable[dict[str, object]] = paginator.paginate(
            Bucket=self._bucket,
            Prefix=prefix,
        )
        for page in pages:
            contents = page.get("Contents", [])
            if not isinstance(contents, list):
                continue
            for obj in contents:
                if isinstance(obj, dict):
                    size = obj.get("Size", 0)
                    if isinstance(size, int):
                        total += size
        return total

    def check_customer_quota(
        self,
        customer_id: str,
        additional_bytes: int,
    ) -> None:
        """Raise ``ValueError`` if upload would exceed quota."""
        current = self.get_customer_usage_bytes(customer_id)
        if current + additional_bytes > CUSTOMER_QUOTA_BYTES:
            self.log_rejected(
                "check_customer_quota",
                reason="quota_exceeded",
                customer_id=customer_id,
                current=current,
                additional=additional_bytes,
                quota=CUSTOMER_QUOTA_BYTES,
            )
            usage_mb = current / (1024 * 1024)
            msg = (
                "Upload would exceed the 500 MB storage"
                f" quota (current: {usage_mb:.1f} MB)"
            )
            raise ValueError(msg)


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def format_attachment_disposition(file_name: str) -> str:
    """Build an RFC 6266 ``Content-Disposition: attachment`` header value.

    Emits both an ASCII ``filename="..."`` fallback and a UTF-8
    ``filename*=UTF-8''...`` variant per RFC 5987 so unicode names
    survive on any browser. Control characters and quote/backslash
    characters are stripped from the fallback to prevent header
    injection via user-supplied upload names.
    """
    cleaned = file_name.replace("\r", "").replace("\n", "").replace("\\", "_")
    cleaned = "".join(c for c in cleaned if c.isprintable())
    ascii_fallback = (
        cleaned.encode("ascii", "replace")
        .decode("ascii")
        .replace("?", "_")
        .replace('"', "'")
    )
    if not ascii_fallback.strip():
        ascii_fallback = "download"
    encoded_utf8 = quote(cleaned, safe="")
    return f"attachment; filename=\"{ascii_fallback}\"; filename*=UTF-8''{encoded_utf8}"


def _build_default_client() -> S3ClientProtocol:
    """Build a boto3 S3 client from env vars."""
    kwargs: dict[str, Any] = {
        "region_name": os.getenv("S3_REGION", "us-east-1"),
        "config": BotoConfig(signature_version="s3v4"),
    }
    endpoint = os.getenv("S3_ENDPOINT_URL")
    if endpoint:
        kwargs["endpoint_url"] = endpoint
    return boto3.client("s3", **kwargs)  # type: ignore[no-any-return,return-value]


_MIME_TO_EXT: dict[str, str] = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/heic": ".heic",
    "image/heif": ".heif",
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "video/mp4": ".mp4",
    "video/quicktime": ".mov",
}


def _extension_for_mime(mime: str) -> str:
    return _MIME_TO_EXT.get(mime, "")
