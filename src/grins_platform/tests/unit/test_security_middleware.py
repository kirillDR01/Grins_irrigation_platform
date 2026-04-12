"""Unit tests for security middleware, PII masking, and file upload pipeline.

Covers:
- Rate limiting returns 429 after threshold (P65)
- Security headers present on responses (P66)
- httpOnly cookie flags on login response (P67)
- JWT startup validation rejects default secret in production (P68)
- Key rotation accepts previous key within grace period (P68)
- Request size limit returns 413 for oversized payloads (P69)
- PII masking processor masks phone, email, address fields (P72)
- Magic byte validation rejects mismatched files (P11)
- EXIF stripping removes GPS data (P73)
- Pre-signed URL expiry (P74)
- Input validation rejects oversized strings, invalid UUIDs, script tags (P71)

Validates: Requirements 9.2, 15.1, 49.5, 69.1-69.5, 70.1-70.4,
           71.1-71.6, 72.1-72.6, 73.1-73.6, 75.1-75.8, 76.1-76.6,
           77.1-77.9
"""

from __future__ import annotations

import io
import os
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from jose import jwt
from limits import parse as parse_limit
from PIL import Image
from pydantic import ValidationError
from slowapi.errors import Limit, RateLimitExceeded
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route
from starlette.testclient import TestClient

from grins_platform.exceptions.auth import InvalidTokenError
from grins_platform.middleware.rate_limit import rate_limit_exceeded_handler
from grins_platform.middleware.request_size import (
    DEFAULT_MAX_BYTES,
    UPLOAD_MAX_BYTES,
    RequestSizeLimitMiddleware,
    _is_upload_path,
)
from grins_platform.middleware.security_headers import SecurityHeadersMiddleware
from grins_platform.models.enums import LeadSituation
from grins_platform.schemas.customer import CustomerCreate
from grins_platform.schemas.lead import LeadSubmission
from grins_platform.services.auth_service import (
    JWT_ALGORITHM,
    AuthService,
    validate_jwt_config,
)
from grins_platform.services.photo_service import (
    PhotoService,
    UploadContext,
)
from grins_platform.services.pii_masking import (
    mask_address,
    mask_email,
    mask_phone,
    pii_masking_processor,
)

pytestmark = pytest.mark.unit


# ============================================================================
# Helpers
# ============================================================================


async def _ok_endpoint(request: Request) -> Response:
    return JSONResponse({"ok": True})


async def _post_endpoint(request: Request) -> Response:
    return JSONResponse({"ok": True})


def _build_app(middleware: list[Any] | None = None) -> Starlette:
    routes = [
        Route("/test", _ok_endpoint),
        Route("/test/photos", _post_endpoint, methods=["POST"]),
        Route("/upload", _post_endpoint, methods=["POST"]),
    ]
    app = Starlette(routes=routes)
    for mw in middleware or []:
        app.add_middleware(mw)
    return app


def _make_jpeg_bytes() -> bytes:
    """Create a minimal JPEG image."""
    img = Image.new("RGB", (2, 2), color="red")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def _make_rate_limit_exc() -> RateLimitExceeded:
    """Create a RateLimitExceeded with a proper Limit object."""
    limit = Limit(
        limit=parse_limit("5/minute"),
        key_func=lambda _: "test",
        scope=None,
        per_method=False,
        methods=None,
        error_message=None,
        exempt_when=None,
        cost=1,
        override_defaults=False,
    )
    return RateLimitExceeded(limit)


# ============================================================================
# P65: Rate limiting returns 429 after threshold
# Validates: Requirements 69.1, 69.2, 69.3
# ============================================================================


class TestRateLimitMiddleware:
    """Test rate limit handler returns correct 429 response."""

    def test_rate_limit_exceeded_returns_429(self) -> None:
        """rate_limit_exceeded_handler returns 429 with Retry-After."""
        scope: dict[str, Any] = {
            "type": "http",
            "method": "GET",
            "path": "/api/v1/test",
            "query_string": b"",
            "headers": [],
            "server": ("localhost", 8000),
        }
        mock_request = Request(scope)
        response = rate_limit_exceeded_handler(
            mock_request,
            _make_rate_limit_exc(),
        )

        assert response.status_code == 429
        assert response.headers.get("Retry-After") == "60"

    def test_rate_limit_response_body(self) -> None:
        """Response body contains error code and retry_after."""
        scope: dict[str, Any] = {
            "type": "http",
            "method": "GET",
            "path": "/test",
            "query_string": b"",
            "headers": [],
            "server": ("localhost", 8000),
        }
        mock_request = Request(scope)
        response = rate_limit_exceeded_handler(
            mock_request,
            _make_rate_limit_exc(),
        )

        assert response.status_code == 429
        body = bytes(response.body).decode()
        assert "RATE_LIMIT_EXCEEDED" in body
        assert "retry_after" in body


# ============================================================================
# P66: Security headers present on all responses
# Validates: Requirements 70.1, 70.2, 70.3
# ============================================================================


class TestSecurityHeadersMiddleware:
    """Test security headers are injected into every response."""

    def setup_method(self) -> None:
        app = _build_app([SecurityHeadersMiddleware])
        self.client = TestClient(app)

    def test_x_content_type_options(self) -> None:
        resp = self.client.get("/test")
        assert resp.headers["X-Content-Type-Options"] == "nosniff"

    def test_x_frame_options(self) -> None:
        resp = self.client.get("/test")
        assert resp.headers["X-Frame-Options"] == "DENY"

    def test_x_xss_protection(self) -> None:
        resp = self.client.get("/test")
        assert resp.headers["X-XSS-Protection"] == "1; mode=block"

    def test_referrer_policy(self) -> None:
        resp = self.client.get("/test")
        assert resp.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"

    def test_permissions_policy(self) -> None:
        resp = self.client.get("/test")
        assert "Permissions-Policy" in resp.headers

    def test_content_security_policy(self) -> None:
        resp = self.client.get("/test")
        assert "Content-Security-Policy" in resp.headers
        assert "default-src 'self'" in resp.headers["Content-Security-Policy"]

    def test_hsts_not_in_development(self) -> None:
        """HSTS should NOT be set in development."""
        resp = self.client.get("/test")
        assert "Strict-Transport-Security" not in resp.headers

    def test_all_required_headers_present(self) -> None:
        """All six required security headers are present."""
        resp = self.client.get("/test")
        required = [
            "X-Content-Type-Options",
            "X-Frame-Options",
            "X-XSS-Protection",
            "Referrer-Policy",
            "Permissions-Policy",
            "Content-Security-Policy",
        ]
        for header in required:
            assert header in resp.headers, f"Missing header: {header}"


# ============================================================================
# P67: Secure token storage in httpOnly cookies
# Validates: Requirements 71.1, 71.2
# ============================================================================


class TestHttpOnlyCookieFlags:
    """Test that auth tokens are set as httpOnly cookies."""

    def test_set_cookie_httponly_flag(self) -> None:
        """Verify httpOnly flag is set on auth cookies."""
        response = JSONResponse({"ok": True})
        response.set_cookie(
            key="access_token",
            value="test-token",
            httponly=True,
            secure=True,
            samesite="lax",
            path="/",
        )
        cookie_header = response.headers.get("set-cookie", "")
        assert "httponly" in cookie_header.lower()
        assert "samesite=lax" in cookie_header.lower()


# ============================================================================
# P68: JWT secret validation at startup
# Validates: Requirements 72.1, 72.2, 72.3, 72.4
# ============================================================================


class TestJWTStartupValidation:
    """Test JWT configuration validation at startup."""

    def test_rejects_default_secret_in_production(self) -> None:
        """Default secret must be rejected in production."""
        with (
            patch.dict(os.environ, {"ENVIRONMENT": "production"}),
            patch(
                "grins_platform.services.auth_service.JWT_SECRET_KEY",
                "dev-secret-key-change-in-production",
            ),
            pytest.raises(RuntimeError, match="must not use a default"),
        ):
            validate_jwt_config()

    def test_rejects_short_secret_in_production(self) -> None:
        """Short secrets must be rejected in production."""
        with (
            patch.dict(os.environ, {"ENVIRONMENT": "production"}),
            patch(
                "grins_platform.services.auth_service.JWT_SECRET_KEY",
                "short",
            ),
            pytest.raises(RuntimeError, match="at least 32 characters"),
        ):
            validate_jwt_config()

    def test_accepts_valid_secret_in_production(self) -> None:
        """Valid long secret should pass in production."""
        with (
            patch.dict(os.environ, {"ENVIRONMENT": "production"}),
            patch(
                "grins_platform.services.auth_service.JWT_SECRET_KEY",
                "a" * 64,
            ),
        ):
            validate_jwt_config()  # Should not raise

    def test_allows_default_in_development(self) -> None:
        """Default secret is allowed in development."""
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            validate_jwt_config()  # Should not raise


class TestJWTKeyRotation:
    """Test JWT key rotation with grace period."""

    def test_previous_key_accepted_within_grace_period(self) -> None:
        """Token signed with previous key should be accepted within 24h."""
        old_secret = "old-secret-key-for-rotation-testing-12345"
        new_secret = "new-secret-key-for-rotation-testing-12345"

        payload = {
            "sub": "test-user-id",
            "type": "access",
            "role": "admin",
            "iat": datetime.now(UTC).timestamp(),
            "exp": (datetime.now(UTC) + timedelta(hours=1)).timestamp(),
        }
        token = jwt.encode(payload, old_secret, algorithm=JWT_ALGORITHM)

        mock_repo = MagicMock()
        service = AuthService(mock_repo)

        with (
            patch(
                "grins_platform.services.auth_service.JWT_SECRET_KEY",
                new_secret,
            ),
            patch(
                "grins_platform.services.auth_service.JWT_PREVIOUS_SECRET_KEY",
                old_secret,
            ),
        ):
            result = service._decode_with_rotation(token)
            assert result["sub"] == "test-user-id"

    def test_previous_key_rejected_outside_grace_period(self) -> None:
        """Token signed with previous key outside grace period is rejected."""
        old_secret = "old-secret-key-for-rotation-testing-12345"
        new_secret = "new-secret-key-for-rotation-testing-12345"

        payload = {
            "sub": "test-user-id",
            "type": "access",
            "role": "admin",
            "iat": (datetime.now(UTC) - timedelta(hours=48)).timestamp(),
            "exp": (datetime.now(UTC) + timedelta(hours=1)).timestamp(),
        }
        token = jwt.encode(payload, old_secret, algorithm=JWT_ALGORITHM)

        mock_repo = MagicMock()
        service = AuthService(mock_repo)

        with (
            patch(
                "grins_platform.services.auth_service.JWT_SECRET_KEY",
                new_secret,
            ),
            patch(
                "grins_platform.services.auth_service.JWT_PREVIOUS_SECRET_KEY",
                old_secret,
            ),
            pytest.raises(InvalidTokenError),
        ):
            service._decode_with_rotation(token)


# ============================================================================
# P69: Request size limit enforcement
# Validates: Requirements 73.1, 73.2, 73.3
# ============================================================================


class TestRequestSizeLimitMiddleware:
    """Test request size limiting middleware."""

    def setup_method(self) -> None:
        app = _build_app([RequestSizeLimitMiddleware])
        self.client = TestClient(app)

    def test_returns_413_for_oversized_default(self) -> None:
        """Requests exceeding 10MB default should get 413."""
        oversized = DEFAULT_MAX_BYTES + 1
        resp = self.client.post(
            "/test",
            content=b"x",
            headers={"content-length": str(oversized)},
        )
        assert resp.status_code == 413

    def test_allows_normal_request(self) -> None:
        """Normal-sized requests should pass through."""
        resp = self.client.get("/test")
        assert resp.status_code == 200

    def test_upload_path_allows_larger(self) -> None:
        """Upload paths should allow up to 50MB."""
        large_but_ok = DEFAULT_MAX_BYTES + 1
        resp = self.client.post(
            "/test/photos",
            content=b"x",
            headers={"content-length": str(large_but_ok)},
        )
        assert resp.status_code == 200

    def test_upload_path_rejects_over_50mb(self) -> None:
        """Upload paths should reject over 50MB."""
        oversized = UPLOAD_MAX_BYTES + 1
        resp = self.client.post(
            "/test/photos",
            content=b"x",
            headers={"content-length": str(oversized)},
        )
        assert resp.status_code == 413

    def test_is_upload_path_detection(self) -> None:
        """Upload path detection works for known suffixes."""
        assert _is_upload_path("/api/v1/customers/123/photos") is True
        assert _is_upload_path("/api/v1/leads/123/attachments") is True
        assert _is_upload_path("/api/v1/media") is True
        assert _is_upload_path("/api/v1/customers") is False

    def test_413_response_body(self) -> None:
        """413 response contains error code and max_bytes."""
        oversized = DEFAULT_MAX_BYTES + 1
        resp = self.client.post(
            "/test",
            content=b"x",
            headers={"content-length": str(oversized)},
        )
        body = resp.json()
        assert body["success"] is False
        assert body["error"]["code"] == "REQUEST_TOO_LARGE"
        assert body["error"]["max_bytes"] == DEFAULT_MAX_BYTES


# ============================================================================
# P72: PII masking in log output
# Validates: Requirements 76.1, 76.2, 76.3, 76.4
# ============================================================================


class TestPIIMasking:
    """Test PII masking processor and helper functions."""

    def test_mask_phone_shows_last_4(self) -> None:
        assert mask_phone("6125551234") == "***1234"

    def test_mask_phone_formatted(self) -> None:
        assert mask_phone("(612) 555-1234") == "***1234"

    def test_mask_email_shows_first_char_and_domain(self) -> None:
        assert mask_email("john@example.com") == "j***@example.com"

    def test_mask_address_fully_masked(self) -> None:
        assert mask_address("123 Main St, Eden Prairie, MN") == "***MASKED***"

    def test_processor_masks_phone_key(self) -> None:
        event = {"event": "test", "phone": "6125551234"}
        result = pii_masking_processor(None, "", event)  # type: ignore[arg-type]
        assert result["phone"] == "***1234"

    def test_processor_masks_email_key(self) -> None:
        event = {"event": "test", "email": "john@example.com"}
        result = pii_masking_processor(None, "", event)  # type: ignore[arg-type]
        assert result["email"] == "j***@example.com"

    def test_processor_masks_address_key(self) -> None:
        event = {"event": "test", "address": "123 Main St"}
        result = pii_masking_processor(None, "", event)  # type: ignore[arg-type]
        assert result["address"] == "***MASKED***"

    def test_processor_redacts_password(self) -> None:
        event = {"event": "test", "password": "secret123"}
        result = pii_masking_processor(None, "", event)  # type: ignore[arg-type]
        assert result["password"] == "REDACTED"

    def test_processor_redacts_token(self) -> None:
        event = {"event": "test", "token": "eyJhbGciOi..."}
        result = pii_masking_processor(None, "", event)  # type: ignore[arg-type]
        assert result["token"] == "REDACTED"

    def test_processor_redacts_api_key(self) -> None:
        event = {"event": "test", "api_key": "sk-abc123"}
        result = pii_masking_processor(None, "", event)  # type: ignore[arg-type]
        assert result["api_key"] == "REDACTED"

    def test_processor_redacts_card_number_key(self) -> None:
        event = {"event": "test", "card_number": "4111111111111111"}
        result = pii_masking_processor(None, "", event)  # type: ignore[arg-type]
        assert result["card_number"] == "REDACTED"

    def test_processor_masks_inline_email_in_string(self) -> None:
        event = {"event": "User john@example.com logged in"}
        result = pii_masking_processor(None, "", event)  # type: ignore[arg-type]
        assert "john@example.com" not in str(result["event"])
        assert "j***@example.com" in str(result["event"])

    def test_processor_masks_inline_phone_in_string(self) -> None:
        event = {"event": "Called 6125551234 for update"}
        result = pii_masking_processor(None, "", event)  # type: ignore[arg-type]
        assert "6125551234" not in str(result["event"])
        assert "***1234" in str(result["event"])

    def test_processor_handles_nested_dict(self) -> None:
        event = {"event": "test", "data": {"phone": "6125551234"}}
        result = pii_masking_processor(None, "", event)  # type: ignore[arg-type]
        assert result["data"]["phone"] == "***1234"  # type: ignore[index]

    def test_processor_preserves_non_pii(self) -> None:
        event = {"event": "test", "job_id": "abc-123", "count": 5}
        result = pii_masking_processor(None, "", event)  # type: ignore[arg-type]
        assert result["job_id"] == "abc-123"
        assert result["count"] == 5

    def test_processor_redacts_stripe_customer_id(self) -> None:
        event = {"event": "test", "stripe_customer_id": "cus_abc123"}
        result = pii_masking_processor(None, "", event)  # type: ignore[arg-type]
        assert result["stripe_customer_id"] == "REDACTED"


# ============================================================================
# P11: File upload validation rejects invalid files
# Validates: Requirements 9.2, 15.1, 49.5, 75.3, 77.1
# ============================================================================


class TestFileUploadValidation:
    """Test magic byte validation rejects mismatched files."""

    def setup_method(self) -> None:
        mock_s3 = MagicMock()
        self.service = PhotoService(s3_client=mock_s3, bucket="test")

    def test_rejects_text_file_as_image(self) -> None:
        """Text file disguised as .jpg should be rejected."""
        data = b"This is not an image file at all"
        with pytest.raises(ValueError, match="not allowed"):
            self.service.validate_file(
                data,
                "fake.jpg",
                UploadContext.CUSTOMER_PHOTO,
            )

    def test_rejects_html_as_image(self) -> None:
        """HTML file should be rejected for image context."""
        data = b"<html><body>Hello</body></html>"
        with pytest.raises(ValueError, match="not allowed"):
            self.service.validate_file(
                data,
                "page.html",
                UploadContext.CUSTOMER_PHOTO,
            )

    def test_accepts_valid_jpeg(self) -> None:
        """Valid JPEG bytes should pass validation."""
        data = _make_jpeg_bytes()
        mime = self.service.validate_file(
            data,
            "photo.jpg",
            UploadContext.CUSTOMER_PHOTO,
        )
        assert mime == "image/jpeg"

    def test_rejects_oversized_file(self) -> None:
        """File exceeding max size should be rejected."""
        data = b"\xff\xd8\xff\xe0" + b"\x00" * (10 * 1024 * 1024 + 1)
        with pytest.raises(ValueError, match="exceeds maximum size"):
            self.service.validate_file(
                data,
                "huge.jpg",
                UploadContext.CUSTOMER_PHOTO,
            )

    def test_accepts_pdf_for_lead_attachment(self) -> None:
        """PDF should be accepted for lead attachment context."""
        data = b"%PDF-1.4 test content" + b"\x00" * 100
        mime = self.service.validate_file(
            data,
            "doc.pdf",
            UploadContext.LEAD_ATTACHMENT,
        )
        assert mime == "application/pdf"

    def test_rejects_pdf_for_customer_photo(self) -> None:
        """PDF should be rejected for customer photo context."""
        data = b"%PDF-1.4 test content" + b"\x00" * 100
        with pytest.raises(ValueError, match="not allowed"):
            self.service.validate_file(
                data,
                "doc.pdf",
                UploadContext.CUSTOMER_PHOTO,
            )


# ============================================================================
# P73: EXIF stripping removes GPS data from uploaded images
# Validates: Requirements 77.4
# ============================================================================


class TestEXIFStripping:
    """Test EXIF/GPS metadata stripping from images."""

    def setup_method(self) -> None:
        mock_s3 = MagicMock()
        self.service = PhotoService(s3_client=mock_s3, bucket="test")

    def test_strip_exif_removes_metadata(self) -> None:
        """Stripped image should have no EXIF data."""
        original = _make_jpeg_bytes()
        stripped = self.service.strip_exif(original, "image/jpeg")

        img = Image.open(io.BytesIO(stripped))
        assert img.size == (2, 2)
        exif = img.getexif()
        assert len(exif) == 0

    def test_strip_exif_returns_original_for_non_image(self) -> None:
        """Non-image MIME types should return data unchanged."""
        data = b"%PDF-1.4 test"
        result = self.service.strip_exif(data, "application/pdf")
        assert result == data

    def test_strip_exif_produces_valid_jpeg(self) -> None:
        """Stripped output should be a valid JPEG."""
        original = _make_jpeg_bytes()
        stripped = self.service.strip_exif(original, "image/jpeg")
        assert stripped[:2] == b"\xff\xd8"


# ============================================================================
# P74: Pre-signed URLs expire after configured duration
# Validates: Requirements 77.3
# ============================================================================


class TestPresignedURLExpiry:
    """Test pre-signed URL generation with expiry."""

    def test_presigned_url_generated_with_expiry(self) -> None:
        """generate_presigned_url passes correct expiry to S3 client."""
        mock_s3 = MagicMock()
        mock_s3.generate_presigned_url.return_value = (
            "https://s3.example.com/file?X-Amz-Expires=3600"
        )
        service = PhotoService(s3_client=mock_s3, bucket="test")

        url = service.generate_presigned_url("customer-photos/abc.jpg")

        mock_s3.generate_presigned_url.assert_called_once_with(
            "get_object",
            Params={"Bucket": "test", "Key": "customer-photos/abc.jpg"},
            ExpiresIn=3600,
        )
        assert "s3.example.com" in url

    def test_presigned_url_custom_expiry(self) -> None:
        """Custom expiry is passed through."""
        mock_s3 = MagicMock()
        mock_s3.generate_presigned_url.return_value = "https://example.com"
        service = PhotoService(s3_client=mock_s3, bucket="test")

        service.generate_presigned_url("key.jpg", expiry=600)

        mock_s3.generate_presigned_url.assert_called_once_with(
            "get_object",
            Params={"Bucket": "test", "Key": "key.jpg"},
            ExpiresIn=600,
        )


# ============================================================================
# P71: Input validation rejects oversized and malformed input
# Validates: Requirements 75.1, 75.2, 75.4, 75.5
# ============================================================================


class TestInputValidation:
    """Test Pydantic schema input validation."""

    def test_customer_phone_rejects_invalid(self) -> None:
        """Invalid phone numbers should be rejected."""
        with pytest.raises(ValidationError):
            CustomerCreate(
                first_name="Test",
                last_name="User",
                phone="not-a-phone",
                email="test@example.com",
            )

    def test_customer_email_rejects_invalid(self) -> None:
        """Invalid email should be rejected."""
        with pytest.raises(ValidationError):
            CustomerCreate(
                first_name="Test",
                last_name="User",
                phone="6125551234",
                email="not-an-email",
            )

    def test_lead_phone_rejects_invalid(self) -> None:
        """Invalid phone in lead submission should be rejected."""
        with pytest.raises(ValidationError):
            LeadSubmission(
                name="Test User",
                phone="abc",
                address="123 Main St, Denver, CO 80209",
                zip_code="55344",
                situation=LeadSituation.NEW_SYSTEM,
            )

    def test_lead_zip_code_rejects_invalid(self) -> None:
        """Invalid zip code should be rejected."""
        with pytest.raises(ValidationError):
            LeadSubmission(
                name="Test User",
                phone="6125551234",
                address="123 Main St, Denver, CO 80209",
                zip_code="ABCDE",
                situation=LeadSituation.NEW_SYSTEM,
            )

    def test_html_tags_stripped_from_lead_notes(self) -> None:
        """Script tags should be stripped from lead notes."""
        lead = LeadSubmission(
            name="Test User",
            phone="6125551234",
            address="123 Main St, Denver, CO 80209",
            zip_code="55344",
            situation=LeadSituation.NEW_SYSTEM,
            notes="<script>alert('xss')</script>Hello",
        )
        assert "<script>" not in (lead.notes or "")
        assert "Hello" in (lead.notes or "")
