"""PhotoService Content-Disposition override tests.

Covers the ``download_filename`` parameter added to
``generate_presigned_url`` and the ``format_attachment_disposition``
helper that builds the RFC 6266 / RFC 5987 header value.

Guards the invariant that PDFs/docs force a browser download while
image-gallery endpoints (no filename passed) keep inline rendering.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from grins_platform.services.photo_service import (
    PhotoService,
    format_attachment_disposition,
)


@pytest.fixture
def s3_client() -> MagicMock:
    """A boto3-shaped mock returning a deterministic presigned URL."""
    client = MagicMock()
    client.generate_presigned_url = MagicMock(
        return_value="https://example.r2.cloudflarestorage.com/signed",
    )
    return client


@pytest.fixture
def photo_svc(s3_client: MagicMock) -> PhotoService:
    return PhotoService(s3_client=s3_client, bucket="bkt")


# --- PhotoService.generate_presigned_url wiring ---------------------------


class TestPresignDownloadFilename:
    def test_no_filename_keeps_inline_behavior(
        self,
        photo_svc: PhotoService,
        s3_client: MagicMock,
    ) -> None:
        """Calling without ``download_filename`` must not add
        ``ResponseContentDisposition`` — the gallery contract."""
        photo_svc.generate_presigned_url("customer-photos/abc.jpg")
        _, kwargs = s3_client.generate_presigned_url.call_args
        assert "ResponseContentDisposition" not in kwargs["Params"]

    def test_filename_sets_attachment_disposition(
        self,
        photo_svc: PhotoService,
        s3_client: MagicMock,
    ) -> None:
        """Passing a filename must add ``attachment; filename=…`` to
        the presigned URL params so the browser saves-as-file."""
        photo_svc.generate_presigned_url(
            "customer-documents/abc.pdf",
            download_filename="estimate.pdf",
        )
        _, kwargs = s3_client.generate_presigned_url.call_args
        disp = kwargs["Params"]["ResponseContentDisposition"]
        assert disp.startswith("attachment;")
        assert 'filename="estimate.pdf"' in disp
        assert "filename*=UTF-8''estimate.pdf" in disp

    def test_expiry_is_passed_through(
        self,
        photo_svc: PhotoService,
        s3_client: MagicMock,
    ) -> None:
        photo_svc.generate_presigned_url(
            "key",
            expiry=120,
            download_filename="x.pdf",
        )
        _, kwargs = s3_client.generate_presigned_url.call_args
        assert kwargs["ExpiresIn"] == 120


# --- format_attachment_disposition hardening ------------------------------


class TestFormatAttachmentDisposition:
    def test_ascii_name_round_trips(self) -> None:
        out = format_attachment_disposition("spring_startup.pdf")
        assert 'filename="spring_startup.pdf"' in out
        assert "filename*=UTF-8''spring_startup.pdf" in out

    def test_unicode_name_encodes_utf8_variant(self) -> None:
        out = format_attachment_disposition("résumé.pdf")
        # ASCII fallback replaces non-ASCII with underscore
        assert 'filename="r_sum_.pdf"' in out
        # UTF-8 variant percent-encodes the original
        assert "filename*=UTF-8''r%C3%A9sum%C3%A9.pdf" in out

    def test_crlf_injection_is_stripped(self) -> None:
        """Header injection via CR/LF in a user-supplied filename must
        be neutralized — a malicious upload can't inject a new header."""
        out = format_attachment_disposition(
            "a\r\nX-Injected: yes\r\n.pdf",
        )
        assert "\r" not in out
        assert "\n" not in out
        assert "X-Injected" in out  # content preserved, but inert

    def test_quotes_are_escaped_in_fallback(self) -> None:
        """Embedded double-quote would close the ASCII ``filename="..."``
        token and allow syntax corruption. Must be replaced."""
        out = format_attachment_disposition('bad"name.pdf')
        # ASCII fallback replaces " with '
        assert 'filename="bad\'name.pdf"' in out

    def test_only_control_chars_falls_back_to_literal_download(self) -> None:
        """An entirely non-printable name must not produce an empty
        ``filename=""`` (which some browsers reject)."""
        out = format_attachment_disposition("\x00\x01\x02")
        assert 'filename="download"' in out
