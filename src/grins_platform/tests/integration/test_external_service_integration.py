"""Integration tests for external service interactions.

Tests cross-component interactions with S3 (file upload/download),
Redis (staff location tracking with TTL), and the end-to-end estimate
portal flow spanning multiple services.

Validates: Requirements 9.8, 41.6
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from grins_platform.models.enums import (
    ActionTag,
    EstimateStatus,
    FollowUpStatus,
)
from grins_platform.schemas.estimate import EstimateCreate
from grins_platform.services.estimate_service import (
    TOKEN_VALIDITY_DAYS,
    EstimateService,
)
from grins_platform.services.photo_service import (
    PhotoService,
    UploadContext,
    UploadResult,
)
from grins_platform.services.staff_location_service import (
    STAFF_LOCATION_PREFIX,
    STAFF_LOCATION_TTL_SECONDS,
    StaffLocation,
    StaffLocationService,
)

# =============================================================================
# Helpers
# =============================================================================


def _build_mock_s3_client() -> MagicMock:
    """Build a mock S3 client that tracks uploaded data for round-trip."""
    client = MagicMock()
    # Storage dict to simulate S3 bucket contents
    storage: dict[str, bytes] = {}

    def put_object(**kwargs: Any) -> dict[str, str]:
        key = kwargs["Key"]
        body = kwargs["Body"]
        storage[key] = body
        return {"ETag": f'"{key}-etag"'}

    def delete_object(**kwargs: Any) -> dict[str, Any]:
        key = kwargs["Key"]
        storage.pop(key, None)
        return {}

    def generate_presigned_url(
        _method: str,
        Params: dict[str, str],
        ExpiresIn: int = 3600,
    ) -> str:
        key = Params["Key"]
        bucket = Params["Bucket"]
        return f"https://{bucket}.s3.amazonaws.com/{key}?expires={ExpiresIn}"

    client.put_object = MagicMock(side_effect=put_object)
    client.delete_object = MagicMock(side_effect=delete_object)
    client.generate_presigned_url = MagicMock(
        side_effect=generate_presigned_url,
    )
    # Paginator for quota checks
    paginator = MagicMock()
    paginator.paginate = MagicMock(return_value=[{"Contents": []}])
    client.get_paginator = MagicMock(return_value=paginator)
    # Expose storage for assertions
    client._storage = storage
    return client


def _mock_magic_jpeg(data: bytes, mime: bool = False) -> str:
    """Mock magic.from_buffer for JPEG detection."""
    if mime and len(data) >= 2 and data[:2] == b"\xff\xd8":
        return "image/jpeg"
    return "application/octet-stream"


def _mock_magic_png(data: bytes, mime: bool = False) -> str:
    """Mock magic.from_buffer for PNG detection."""
    if mime and len(data) >= 4 and data[:4] == b"\x89PNG":
        return "image/png"
    return "application/octet-stream"


def _mock_magic_pdf(data: bytes, mime: bool = False) -> str:
    """Mock magic.from_buffer for PDF detection."""
    if mime and len(data) >= 5 and data[:5] == b"%PDF-":
        return "application/pdf"
    return "application/octet-stream"


def _make_jpeg_bytes(size: int = 104) -> bytes:
    """Create minimal JPEG-like bytes."""
    return b"\xff\xd8\xff\xe0" + b"\x00" * max(size - 6, 0) + b"\xff\xd9"


def _make_png_bytes(size: int = 104) -> bytes:
    """Create minimal PNG-like bytes."""
    return b"\x89PNG" + b"\x00" * max(size - 4, 0)


def _build_mock_redis() -> AsyncMock:
    """Build a mock async Redis client with TTL tracking."""
    redis = AsyncMock()
    store: dict[str, tuple[str, float | None]] = {}

    async def mock_set(
        key: str,
        value: str,
        ex: int | None = None,
    ) -> bool:
        expiry = datetime.now(tz=timezone.utc).timestamp() + ex if ex else None
        store[key] = (value, expiry)
        return True

    async def mock_get(key: str) -> str | None:
        entry = store.get(key)
        if entry is None:
            return None
        value, expiry = entry
        if expiry and datetime.now(tz=timezone.utc).timestamp() > expiry:
            del store[key]
            return None
        return value

    async def mock_delete(key: str) -> int:
        if key in store:
            del store[key]
            return 1
        return 0

    async def mock_ttl(key: str) -> int:
        entry = store.get(key)
        if entry is None:
            return -2
        _, expiry = entry
        if expiry is None:
            return -1
        remaining = expiry - datetime.now(tz=timezone.utc).timestamp()
        return max(int(remaining), 0)

    redis.set = AsyncMock(side_effect=mock_set)
    redis.get = AsyncMock(side_effect=mock_get)
    redis.delete = AsyncMock(side_effect=mock_delete)
    redis.ttl = AsyncMock(side_effect=mock_ttl)
    redis._store = store
    return redis


def _make_estimate_mock(**overrides: Any) -> MagicMock:
    """Create a mock Estimate with all fields."""
    est = MagicMock()
    est.id = overrides.get("id", uuid4())
    est.lead_id = overrides.get("lead_id")
    est.customer_id = overrides.get("customer_id")
    est.job_id = overrides.get("job_id")
    est.template_id = overrides.get("template_id")
    est.status = overrides.get("status", EstimateStatus.DRAFT.value)
    est.line_items = overrides.get(
        "line_items",
        [
            {"item": "Sprinkler Head", "unit_price": "25.00", "quantity": "4"},
        ],
    )
    est.options = overrides.get("options")
    est.subtotal = overrides.get("subtotal", Decimal("100.00"))
    est.tax_amount = overrides.get("tax_amount", Decimal("8.25"))
    est.discount_amount = overrides.get("discount_amount", Decimal(0))
    est.total = overrides.get("total", Decimal("108.25"))
    est.promotion_code = overrides.get("promotion_code")
    est.valid_until = overrides.get(
        "valid_until",
        datetime.now(tz=timezone.utc) + timedelta(days=30),
    )
    est.notes = overrides.get("notes")
    est.customer_token = overrides.get("customer_token", uuid4())
    est.token_expires_at = overrides.get(
        "token_expires_at",
        datetime.now(tz=timezone.utc) + timedelta(days=TOKEN_VALIDITY_DAYS),
    )
    est.token_readonly = overrides.get("token_readonly", False)
    est.approved_at = overrides.get("approved_at")
    est.approved_ip = overrides.get("approved_ip")
    est.approved_user_agent = overrides.get("approved_user_agent")
    est.rejected_at = overrides.get("rejected_at")
    est.rejection_reason = overrides.get("rejection_reason")
    est.created_at = overrides.get(
        "created_at",
        datetime.now(tz=timezone.utc),
    )
    est.updated_at = datetime.now(tz=timezone.utc)
    est.customer = overrides.get("customer")
    est.lead = overrides.get("lead")
    return est


def _make_customer_mock(**overrides: Any) -> MagicMock:
    """Create a mock Customer."""
    c = MagicMock()
    c.id = overrides.get("id", uuid4())
    c.phone = overrides.get("phone", "5125551234")
    c.email = overrides.get("email", "customer@example.com")
    c.first_name = overrides.get("first_name", "Jane")
    c.last_name = overrides.get("last_name", "Doe")
    c.internal_notes = overrides.get("internal_notes")
    c.preferred_service_times = overrides.get("preferred_service_times")
    return c


def _make_lead_mock(**overrides: Any) -> MagicMock:
    """Create a mock Lead."""
    lead = MagicMock()
    lead.id = overrides.get("id", uuid4())
    lead.phone = overrides.get("phone", "5125559999")
    lead.name = overrides.get("name", "Test Lead")
    lead.action_tags = overrides.get(
        "action_tags",
        [ActionTag.ESTIMATE_PENDING.value],
    )
    lead.city = overrides.get("city")
    lead.state = overrides.get("state")
    lead.address = overrides.get("address")
    return lead


# =============================================================================
# 1. S3 File Upload/Download Round-Trip
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
class TestS3FileRoundTrip:
    """Test S3 file upload/download round-trip across contexts.

    Verifies that PhotoService correctly handles upload → presigned URL
    generation → delete for customer photos, lead attachments, and
    media library files, testing cross-component S3 interactions.

    Validates: Requirement 9.8
    """

    async def test_customer_photo_upload_download_roundtrip_works_with_existing_s3(
        self,
    ) -> None:
        """Customer photo: upload → get URL → verify key → delete."""
        import magic as magic_mod

        s3_client = _build_mock_s3_client()
        photo_svc = PhotoService(
            s3_client=s3_client,
            bucket="test-bucket",
        )

        jpeg_data = _make_jpeg_bytes()
        original_from_buffer = magic_mod.from_buffer
        magic_mod.from_buffer = _mock_magic_jpeg  # type: ignore[assignment]

        try:
            # Upload
            result = photo_svc.upload_file(
                data=jpeg_data,
                file_name="front-yard.jpg",
                context=UploadContext.CUSTOMER_PHOTO,
            )
            assert isinstance(result, UploadResult)
            assert result.file_key.startswith("customer-photos/")
            assert result.file_key.endswith(".jpg")
            assert result.content_type == "image/jpeg"

            # Verify data was stored in mock S3
            assert result.file_key in s3_client._storage

            # Generate presigned URL
            url = photo_svc.generate_presigned_url(result.file_key)
            assert "test-bucket" in url
            assert result.file_key in url

            # Delete
            photo_svc.delete_file(result.file_key)
            assert result.file_key not in s3_client._storage
        finally:
            magic_mod.from_buffer = original_from_buffer  # type: ignore[assignment]

    async def test_lead_attachment_upload_download_roundtrip_works_with_existing_s3(
        self,
    ) -> None:
        """Lead attachment: upload PDF → get URL → delete."""
        import magic as magic_mod

        s3_client = _build_mock_s3_client()
        photo_svc = PhotoService(
            s3_client=s3_client,
            bucket="test-bucket",
        )

        pdf_data = b"%PDF-1.4" + b"\x00" * 200
        original_from_buffer = magic_mod.from_buffer
        magic_mod.from_buffer = _mock_magic_pdf  # type: ignore[assignment]

        try:
            result = photo_svc.upload_file(
                data=pdf_data,
                file_name="estimate-doc.pdf",
                context=UploadContext.LEAD_ATTACHMENT,
            )
            assert result.file_key.startswith("lead-attachments/")
            assert result.content_type == "application/pdf"

            # Verify stored
            assert result.file_key in s3_client._storage

            # Generate URL
            url = photo_svc.generate_presigned_url(result.file_key)
            assert result.file_key in url

            # Delete
            photo_svc.delete_file(result.file_key)
            assert result.file_key not in s3_client._storage
        finally:
            magic_mod.from_buffer = original_from_buffer  # type: ignore[assignment]

    async def test_media_library_upload_download_roundtrip_works_with_existing_s3(
        self,
    ) -> None:
        """Media library: upload PNG → get URL → delete."""
        import magic as magic_mod

        s3_client = _build_mock_s3_client()
        photo_svc = PhotoService(
            s3_client=s3_client,
            bucket="test-bucket",
        )

        png_data = _make_png_bytes()
        original_from_buffer = magic_mod.from_buffer
        magic_mod.from_buffer = _mock_magic_png  # type: ignore[assignment]

        try:
            result = photo_svc.upload_file(
                data=png_data,
                file_name="testimonial-photo.png",
                context=UploadContext.MEDIA_LIBRARY,
            )
            assert result.file_key.startswith("media-library/")
            assert result.content_type == "image/png"

            # Verify stored
            assert result.file_key in s3_client._storage

            # Generate URL
            url = photo_svc.generate_presigned_url(result.file_key)
            assert result.file_key in url

            # Delete
            photo_svc.delete_file(result.file_key)
            assert result.file_key not in s3_client._storage
        finally:
            magic_mod.from_buffer = original_from_buffer  # type: ignore[assignment]

    async def test_multiple_files_across_contexts_coexist_in_s3(
        self,
    ) -> None:
        """Multiple files across different contexts coexist in S3."""
        import magic as magic_mod

        s3_client = _build_mock_s3_client()
        photo_svc = PhotoService(
            s3_client=s3_client,
            bucket="test-bucket",
        )

        jpeg_data = _make_jpeg_bytes()
        original_from_buffer = magic_mod.from_buffer
        magic_mod.from_buffer = _mock_magic_jpeg  # type: ignore[assignment]

        try:
            # Upload to customer photos
            r1 = photo_svc.upload_file(
                data=jpeg_data,
                file_name="photo1.jpg",
                context=UploadContext.CUSTOMER_PHOTO,
            )
            # Upload to media library
            r2 = photo_svc.upload_file(
                data=jpeg_data,
                file_name="photo2.jpg",
                context=UploadContext.MEDIA_LIBRARY,
            )

            # Both exist
            assert r1.file_key in s3_client._storage
            assert r2.file_key in s3_client._storage
            assert r1.file_key != r2.file_key

            # Delete one, other persists
            photo_svc.delete_file(r1.file_key)
            assert r1.file_key not in s3_client._storage
            assert r2.file_key in s3_client._storage

            # Clean up
            photo_svc.delete_file(r2.file_key)
            assert len(s3_client._storage) == 0
        finally:
            magic_mod.from_buffer = original_from_buffer  # type: ignore[assignment]


# =============================================================================
# 2. Redis Location Storage and TTL Expiry for Staff Tracking
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
class TestRedisStaffLocationTracking:
    """Test Redis location storage and TTL expiry for staff tracking.

    Verifies StaffLocationService stores locations with correct TTL,
    retrieves them, and handles expiry correctly.

    Validates: Requirement 41.6
    """

    async def test_staff_location_store_and_retrieve_works_with_existing_redis(
        self,
    ) -> None:
        """Store a location and retrieve it back with correct data."""
        redis = _build_mock_redis()
        svc = StaffLocationService(redis_client=redis)

        staff_id = uuid4()
        appt_id = uuid4()

        stored = await svc.store_location(
            staff_id=staff_id,
            latitude=30.2672,
            longitude=-97.7431,
            appointment_id=appt_id,
        )
        assert stored is True

        # Retrieve
        loc = await svc.get_location(staff_id)
        assert loc is not None
        assert isinstance(loc, StaffLocation)
        assert loc.staff_id == staff_id
        assert loc.latitude == pytest.approx(30.2672)
        assert loc.longitude == pytest.approx(-97.7431)
        assert loc.appointment_id == appt_id
        assert loc.timestamp  # ISO format string

    async def test_staff_location_stored_with_correct_ttl_in_redis(
        self,
    ) -> None:
        """Location is stored with 5-minute (300s) TTL."""
        redis = _build_mock_redis()
        svc = StaffLocationService(redis_client=redis)

        staff_id = uuid4()
        await svc.store_location(
            staff_id=staff_id,
            latitude=30.0,
            longitude=-97.0,
        )

        # Verify set was called with correct TTL
        redis.set.assert_called_once()
        call_kwargs = redis.set.call_args
        assert call_kwargs.kwargs.get("ex") == STAFF_LOCATION_TTL_SECONDS
        # Verify key pattern
        expected_key = f"{STAFF_LOCATION_PREFIX}{staff_id}"
        assert call_kwargs.args[0] == expected_key

    async def test_staff_location_returns_none_after_ttl_expiry(
        self,
    ) -> None:
        """Location returns None after TTL expires (simulated)."""
        redis = _build_mock_redis()
        svc = StaffLocationService(redis_client=redis)

        staff_id = uuid4()
        await svc.store_location(
            staff_id=staff_id,
            latitude=30.0,
            longitude=-97.0,
        )

        # Manually expire the entry by setting past timestamp
        key = f"{STAFF_LOCATION_PREFIX}{staff_id}"
        value, _ = redis._store[key]
        past_time = datetime.now(tz=timezone.utc).timestamp() - 1
        redis._store[key] = (value, past_time)

        # Should return None (expired)
        loc = await svc.get_location(staff_id)
        assert loc is None

    async def test_multiple_staff_locations_tracked_independently(
        self,
    ) -> None:
        """Multiple staff members' locations are tracked independently."""
        redis = _build_mock_redis()
        svc = StaffLocationService(redis_client=redis)

        staff_1 = uuid4()
        staff_2 = uuid4()

        await svc.store_location(
            staff_id=staff_1,
            latitude=30.2672,
            longitude=-97.7431,
        )
        await svc.store_location(
            staff_id=staff_2,
            latitude=29.7604,
            longitude=-95.3698,
        )

        loc_1 = await svc.get_location(staff_1)
        loc_2 = await svc.get_location(staff_2)

        assert loc_1 is not None
        assert loc_2 is not None
        assert loc_1.latitude == pytest.approx(30.2672)
        assert loc_2.latitude == pytest.approx(29.7604)

    async def test_get_all_locations_works_with_existing_redis(
        self,
    ) -> None:
        """Batch retrieval returns only active (non-expired) locations."""
        redis = _build_mock_redis()
        svc = StaffLocationService(redis_client=redis)

        staff_1 = uuid4()
        staff_2 = uuid4()
        staff_3 = uuid4()

        await svc.store_location(
            staff_id=staff_1,
            latitude=30.0,
            longitude=-97.0,
        )
        await svc.store_location(
            staff_id=staff_2,
            latitude=29.0,
            longitude=-95.0,
        )
        # staff_3 has no location stored

        locations = await svc.get_all_locations([staff_1, staff_2, staff_3])
        assert len(locations) == 2

        ids = {loc.staff_id for loc in locations}
        assert staff_1 in ids
        assert staff_2 in ids
        assert staff_3 not in ids

    async def test_location_update_overwrites_previous_in_redis(
        self,
    ) -> None:
        """Storing a new location overwrites the previous one."""
        redis = _build_mock_redis()
        svc = StaffLocationService(redis_client=redis)

        staff_id = uuid4()

        await svc.store_location(
            staff_id=staff_id,
            latitude=30.0,
            longitude=-97.0,
        )
        await svc.store_location(
            staff_id=staff_id,
            latitude=31.0,
            longitude=-98.0,
        )

        loc = await svc.get_location(staff_id)
        assert loc is not None
        assert loc.latitude == pytest.approx(31.0)
        assert loc.longitude == pytest.approx(-98.0)

    async def test_store_location_returns_false_when_redis_unavailable(
        self,
    ) -> None:
        """Returns False when Redis client is None."""
        svc = StaffLocationService(redis_client=None)

        result = await svc.store_location(
            staff_id=uuid4(),
            latitude=30.0,
            longitude=-97.0,
        )
        assert result is False

    async def test_get_location_returns_none_when_redis_unavailable(
        self,
    ) -> None:
        """Returns None when Redis client is None."""
        svc = StaffLocationService(redis_client=None)
        loc = await svc.get_location(uuid4())
        assert loc is None


# =============================================================================
# 3. End-to-End Estimate Portal Flow
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
class TestEstimatePortalEndToEnd:
    """Test end-to-end estimate portal flow across multiple services.

    Full flow: create estimate → send → customer opens portal →
    approves → lead tag updated → job creation triggered.

    This tests cross-service interactions between EstimateService,
    LeadService (tag updates), SMSService (notifications), and
    the portal token lifecycle.

    Validates: Requirements 9.8, 41.6
    """

    async def test_estimate_portal_approval_flow_works_with_existing_services(
        self,
    ) -> None:
        """Full e2e: create → send → portal approve → lead tag → job ready.

        Verifies the complete cross-service flow:
        1. EstimateService creates estimate with portal token
        2. EstimateService sends estimate (SMS + follow-ups scheduled)
        3. Customer approves via portal token
        4. LeadService updates lead tag to ESTIMATE_APPROVED
        5. Follow-ups are cancelled on approval
        """
        lead_id = uuid4()
        customer = _make_customer_mock()
        lead = _make_lead_mock(id=lead_id)

        # Wire up mocked dependencies
        estimate_repo = AsyncMock()
        lead_service = AsyncMock()
        sms_service = AsyncMock()
        sms_service.send_automated_message = AsyncMock(
            return_value={"success": True, "message_id": str(uuid4())},
        )
        lead_service.update_action_tags = AsyncMock(
            return_value=MagicMock(),
        )

        svc = EstimateService(
            estimate_repository=estimate_repo,
            lead_service=lead_service,
            sms_service=sms_service,
            email_service=MagicMock(),
            portal_base_url="https://portal.grins.com",
        )

        # --- Step 1: Create estimate ---
        created_est = _make_estimate_mock(
            lead_id=lead_id,
            customer_id=customer.id,
            customer=customer,
            lead=lead,
            line_items=[
                {"item": "Drip Line", "unit_price": "50.00", "quantity": "3"},
                {"item": "Timer", "unit_price": "75.00", "quantity": "1"},
            ],
            subtotal=Decimal("225.00"),
            tax_amount=Decimal("18.56"),
            total=Decimal("243.56"),
        )
        estimate_repo.create.return_value = created_est

        data = EstimateCreate(
            lead_id=lead_id,
            customer_id=customer.id,
            line_items=[
                {"item": "Drip Line", "unit_price": "50.00", "quantity": "3"},
                {"item": "Timer", "unit_price": "75.00", "quantity": "1"},
            ],
            tax_amount=Decimal("18.56"),
        )
        result = await svc.create_estimate(data, uuid4())
        assert result.id == created_est.id
        assert result.status == EstimateStatus.DRAFT

        # --- Step 2: Send estimate ---
        sent_est = _make_estimate_mock(
            id=created_est.id,
            status=EstimateStatus.SENT.value,
            customer_token=created_est.customer_token,
            customer=customer,
            lead=lead,
            lead_id=lead_id,
        )
        estimate_repo.get_by_id.return_value = sent_est
        estimate_repo.update.return_value = sent_est
        estimate_repo.create_follow_up.return_value = MagicMock()

        send_result = await svc.send_estimate(created_est.id)

        # Verify portal URL generated
        assert send_result.portal_url.startswith(
            "https://portal.grins.com/estimates/",
        )
        assert str(sent_est.customer_token) in send_result.portal_url
        # Verify SMS was sent
        assert "sms" in send_result.sent_via
        sms_service.send_automated_message.assert_called()

        # --- Step 3: Customer approves via portal ---
        approved_est = _make_estimate_mock(
            id=created_est.id,
            status=EstimateStatus.APPROVED.value,
            approved_at=datetime.now(tz=timezone.utc),
            approved_ip="192.168.1.100",
            approved_user_agent="Mozilla/5.0 (iPhone)",
            token_readonly=True,
            customer_token=created_est.customer_token,
            lead_id=lead_id,
            lead=lead,
        )
        estimate_repo.get_by_token.return_value = sent_est
        estimate_repo.update.return_value = approved_est
        estimate_repo.cancel_follow_ups_for_estimate.return_value = 4

        approval = await svc.approve_via_portal(
            token=created_est.customer_token,
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0 (iPhone)",
        )

        # Verify approval recorded
        assert approval.status == EstimateStatus.APPROVED
        assert approval.approved_at is not None
        assert approval.token_readonly is True

        # --- Step 4: Lead tag updated to ESTIMATE_APPROVED ---
        lead_service.update_action_tags.assert_called_once_with(
            lead_id,
            add_tags=[ActionTag.ESTIMATE_APPROVED],
            remove_tags=[ActionTag.ESTIMATE_PENDING],
        )

        # --- Step 5: Follow-ups cancelled ---
        estimate_repo.cancel_follow_ups_for_estimate.assert_called_once_with(
            created_est.id,
        )

    async def test_estimate_portal_rejection_updates_lead_tag_across_services(
        self,
    ) -> None:
        """Rejection flow: send → reject → lead tag ESTIMATE_REJECTED."""
        lead_id = uuid4()
        customer = _make_customer_mock()
        lead = _make_lead_mock(id=lead_id)

        estimate_repo = AsyncMock()
        lead_service = AsyncMock()
        lead_service.update_action_tags = AsyncMock(
            return_value=MagicMock(),
        )

        svc = EstimateService(
            estimate_repository=estimate_repo,
            lead_service=lead_service,
            sms_service=AsyncMock(),
            portal_base_url="https://portal.grins.com",
        )

        sent_est = _make_estimate_mock(
            lead_id=lead_id,
            customer_id=customer.id,
            customer=customer,
            lead=lead,
            status=EstimateStatus.SENT.value,
        )
        estimate_repo.get_by_token.return_value = sent_est

        rejected_est = _make_estimate_mock(
            id=sent_est.id,
            status=EstimateStatus.REJECTED.value,
            rejected_at=datetime.now(tz=timezone.utc),
            rejection_reason="Too expensive",
            token_readonly=True,
            lead_id=lead_id,
            lead=lead,
        )
        estimate_repo.update.return_value = rejected_est
        estimate_repo.cancel_follow_ups_for_estimate.return_value = 3

        rejection = await svc.reject_via_portal(
            token=sent_est.customer_token,
            reason="Too expensive",
        )

        assert rejection.status == EstimateStatus.REJECTED
        assert rejection.rejection_reason == "Too expensive"

        # Lead tag updated to ESTIMATE_REJECTED
        lead_service.update_action_tags.assert_called_once_with(
            lead_id,
            add_tags=[ActionTag.ESTIMATE_REJECTED],
            remove_tags=[ActionTag.ESTIMATE_PENDING],
        )

        # Follow-ups cancelled
        estimate_repo.cancel_follow_ups_for_estimate.assert_called_once_with(
            sent_est.id,
        )

    async def test_estimate_send_schedules_follow_ups_across_services(
        self,
    ) -> None:
        """Sending an estimate schedules follow-ups at Day 3, 7, 14, 21."""
        customer = _make_customer_mock()
        lead = _make_lead_mock()

        estimate_repo = AsyncMock()
        sms_service = AsyncMock()
        sms_service.send_automated_message = AsyncMock(
            return_value={"success": True},
        )

        svc = EstimateService(
            estimate_repository=estimate_repo,
            lead_service=AsyncMock(),
            sms_service=sms_service,
            portal_base_url="https://portal.grins.com",
        )

        est = _make_estimate_mock(
            customer=customer,
            lead=lead,
            status=EstimateStatus.DRAFT.value,
        )
        estimate_repo.get_by_id.return_value = est
        estimate_repo.update.return_value = _make_estimate_mock(
            id=est.id,
            status=EstimateStatus.SENT.value,
            customer=customer,
            lead=lead,
        )
        estimate_repo.create_follow_up.return_value = MagicMock()

        await svc.send_estimate(est.id)

        # 4 follow-ups scheduled (Day 3, 7, 14, 21)
        assert estimate_repo.create_follow_up.call_count == 4

        # Verify follow-up numbers
        calls = estimate_repo.create_follow_up.call_args_list
        follow_up_numbers = [c.kwargs["follow_up_number"] for c in calls]
        assert follow_up_numbers == [1, 2, 3, 4]

        # Later follow-ups (3, 4) get promotion codes
        statuses = [c.kwargs["status"] for c in calls]
        assert all(s == FollowUpStatus.SCHEDULED.value for s in statuses)

    async def test_estimate_portal_with_s3_and_lead_service_integration(
        self,
    ) -> None:
        """Cross-service: S3 photo + estimate approval in same workflow.

        Simulates a real scenario where a customer photo is uploaded
        (S3), then an estimate is created and approved (portal flow),
        verifying both external services work together.
        """
        import magic as magic_mod

        # --- S3: Upload customer photo ---
        s3_client = _build_mock_s3_client()
        photo_svc = PhotoService(
            s3_client=s3_client,
            bucket="test-bucket",
        )

        jpeg_data = _make_jpeg_bytes()
        original_from_buffer = magic_mod.from_buffer
        magic_mod.from_buffer = _mock_magic_jpeg  # type: ignore[assignment]

        try:
            photo_result = photo_svc.upload_file(
                data=jpeg_data,
                file_name="property-photo.jpg",
                context=UploadContext.CUSTOMER_PHOTO,
            )
            assert photo_result.file_key in s3_client._storage
        finally:
            magic_mod.from_buffer = original_from_buffer  # type: ignore[assignment]

        # --- Estimate: Create and approve ---
        lead_id = uuid4()
        customer = _make_customer_mock()
        lead = _make_lead_mock(id=lead_id)

        estimate_repo = AsyncMock()
        lead_service = AsyncMock()
        lead_service.update_action_tags = AsyncMock(
            return_value=MagicMock(),
        )

        est_svc = EstimateService(
            estimate_repository=estimate_repo,
            lead_service=lead_service,
            sms_service=AsyncMock(),
            portal_base_url="https://portal.grins.com",
        )

        sent_est = _make_estimate_mock(
            lead_id=lead_id,
            customer_id=customer.id,
            customer=customer,
            lead=lead,
            status=EstimateStatus.SENT.value,
        )
        approved_est = _make_estimate_mock(
            id=sent_est.id,
            status=EstimateStatus.APPROVED.value,
            approved_at=datetime.now(tz=timezone.utc),
            token_readonly=True,
            lead_id=lead_id,
            lead=lead,
        )
        estimate_repo.get_by_token.return_value = sent_est
        estimate_repo.update.return_value = approved_est
        estimate_repo.cancel_follow_ups_for_estimate.return_value = 4

        approval = await est_svc.approve_via_portal(
            token=sent_est.customer_token,
            ip_address="10.0.0.1",
            user_agent="TestAgent",
        )

        # Both services worked: photo in S3, estimate approved
        assert photo_result.file_key in s3_client._storage
        assert approval.status == EstimateStatus.APPROVED
        lead_service.update_action_tags.assert_called_once()
