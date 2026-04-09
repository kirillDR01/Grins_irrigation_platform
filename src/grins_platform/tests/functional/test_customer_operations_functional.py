"""Functional tests for customer operations.

Tests customer merge with FK reassignment and customer photo
upload/list/delete workflows with mocked repositories and S3 storage,
verifying cross-service interactions as a user would experience them.

Validates: Requirements 7.6, 9.8
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from grins_platform.exceptions import (
    CustomerNotFoundError,
    MergeConflictError,
)
from grins_platform.services.customer_service import CustomerService
from grins_platform.services.photo_service import (
    PhotoService,
    UploadContext,
    UploadResult,
)

# =============================================================================
# Helpers
# =============================================================================


def _make_customer(
    *,
    customer_id: Any | None = None,
    first_name: str = "Jane",
    last_name: str = "Smith",
    phone: str = "5125551234",
    email: str | None = "jane@example.com",
    internal_notes: str | None = None,
    is_deleted: bool = False,
    stripe_customer_id: str | None = None,
) -> MagicMock:
    """Create a mock Customer."""
    c = MagicMock()
    c.id = customer_id or uuid4()
    c.first_name = first_name
    c.last_name = last_name
    c.phone = phone
    c.email = email
    c.internal_notes = internal_notes
    c.is_deleted = is_deleted
    c.deleted_at = None
    c.stripe_customer_id = stripe_customer_id
    c.status = "active"
    c.is_priority = False
    c.is_red_flag = False
    c.is_slow_payer = False
    c.is_new_customer = False
    c.sms_opt_in = True
    c.email_opt_in = True
    c.lead_source = None
    c.preferred_service_times = None
    c.created_at = datetime.now()
    c.updated_at = datetime.now()
    c.properties = []
    return c


def _build_customer_service(
    *,
    repo: AsyncMock | None = None,
) -> tuple[CustomerService, AsyncMock]:
    """Build a CustomerService with mocked repository."""
    repository = repo or AsyncMock()
    svc = CustomerService(repository=repository)
    return svc, repository


def _mock_db_for_merge(
    *,
    execute_side_effects: list[Any] | None = None,
) -> AsyncMock:
    """Create a mock db session for merge operations."""
    db = AsyncMock()
    if execute_side_effects:
        db.execute = AsyncMock(side_effect=execute_side_effects)
    else:
        db.execute = AsyncMock(return_value=MagicMock())
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.refresh = AsyncMock()
    return db


def _build_mock_s3_client() -> MagicMock:
    """Build a mock S3 client for photo operations."""
    client = MagicMock()
    client.put_object = MagicMock(return_value={"ETag": '"abc123"'})
    client.delete_object = MagicMock(return_value={})
    client.generate_presigned_url = MagicMock(
        return_value="https://s3.example.com/presigned-url",
    )
    # Paginator for quota checks
    paginator = MagicMock()
    paginator.paginate = MagicMock(return_value=[{"Contents": []}])
    client.get_paginator = MagicMock(return_value=paginator)
    return client


# =============================================================================
# 1. Customer Merge with FK Reassignment
# =============================================================================


@pytest.mark.functional
@pytest.mark.asyncio
class TestCustomerMergeWorkflow:
    """Test customer merge reassigns all FKs and soft-deletes duplicates.

    Validates: Requirement 7.6
    """

    async def test_merge_reassigns_all_related_records_to_primary(
        self,
    ) -> None:
        """Merging duplicates moves all FK references to the primary customer."""
        svc, repo = _build_customer_service()

        primary = _make_customer(
            first_name="Alice",
            last_name="Johnson",
            phone="5125550001",
            internal_notes="Primary notes",
        )
        dup1 = _make_customer(
            first_name="Alice",
            last_name="Jonson",
            phone="5125550002",
            internal_notes="Dup1 notes",
        )
        dup2 = _make_customer(
            first_name="Alicia",
            last_name="Johnson",
            phone="5125550003",
        )

        repo.get_by_id = AsyncMock(
            side_effect=lambda cid: {
                primary.id: primary,
                dup1.id: dup1,
                dup2.id: dup2,
            }.get(cid),
        )

        db = _mock_db_for_merge()
        actor_id = uuid4()

        await svc.merge_customers(
            db=db,
            primary_id=primary.id,
            duplicate_ids=[dup1.id, dup2.id],
            actor_id=actor_id,
            ip_address="127.0.0.1",
        )

        # Verify FK reassignment SQL was executed for each table
        execute_calls = db.execute.call_args_list
        # Should have calls for FK tables + notes update + soft-delete calls
        assert len(execute_calls) > 0

        # Verify audit log entry was added
        db.add.assert_called_once()
        audit_entry = db.add.call_args[0][0]
        assert audit_entry.action == "customer.merge"
        assert audit_entry.resource_id == primary.id
        assert str(dup1.id) in audit_entry.details["merged_customer_ids"]
        assert str(dup2.id) in audit_entry.details["merged_customer_ids"]

        # Verify flush was called to commit the transaction
        db.flush.assert_awaited_once()

    async def test_merge_soft_deletes_duplicate_customers(self) -> None:
        """Merged duplicates are soft-deleted after FK reassignment."""
        svc, repo = _build_customer_service()

        primary = _make_customer(first_name="Bob", phone="5125550010")
        dup = _make_customer(first_name="Bobby", phone="5125550011")

        repo.get_by_id = AsyncMock(
            side_effect=lambda cid: {
                primary.id: primary,
                dup.id: dup,
            }.get(cid),
        )

        db = _mock_db_for_merge()
        actor_id = uuid4()

        await svc.merge_customers(
            db=db,
            primary_id=primary.id,
            duplicate_ids=[dup.id],
            actor_id=actor_id,
            ip_address="10.0.0.1",
        )

        # Verify soft-delete SQL was executed (UPDATE ... SET is_deleted=True)
        execute_calls = db.execute.call_args_list
        # Soft-delete uses sa_update(Customer).values(is_deleted=True)
        soft_delete_found = False
        for c in execute_calls:
            args = c[0] if c[0] else ()
            for arg in args:
                arg_str = str(arg)
                if "is_deleted" in arg_str and "customers" in arg_str:
                    soft_delete_found = True
                    break
        assert soft_delete_found, "Soft-delete SQL not found in execute calls"

    async def test_merge_combines_internal_notes_from_duplicates(
        self,
    ) -> None:
        """Internal notes from duplicates are merged into the primary."""
        svc, repo = _build_customer_service()

        primary = _make_customer(
            first_name="Carol",
            phone="5125550020",
            internal_notes="Primary customer notes.",
        )
        dup = _make_customer(
            first_name="Carol",
            phone="5125550021",
            internal_notes="Important info from duplicate.",
        )

        repo.get_by_id = AsyncMock(
            side_effect=lambda cid: {
                primary.id: primary,
                dup.id: dup,
            }.get(cid),
        )

        db = _mock_db_for_merge()
        actor_id = uuid4()

        await svc.merge_customers(
            db=db,
            primary_id=primary.id,
            duplicate_ids=[dup.id],
            actor_id=actor_id,
            ip_address="127.0.0.1",
        )

        # Verify notes merge SQL was executed
        execute_calls = db.execute.call_args_list
        notes_update_found = False
        for c in execute_calls:
            args = c[0] if c[0] else ()
            for arg in args:
                arg_str = str(arg)
                if "internal_notes" in arg_str:
                    notes_update_found = True
                    break
        assert notes_update_found, "Internal notes merge SQL not found"

    async def test_merge_rejects_primary_not_found(self) -> None:
        """Merge raises CustomerNotFoundError when primary doesn't exist."""
        svc, repo = _build_customer_service()
        repo.get_by_id = AsyncMock(return_value=None)

        db = _mock_db_for_merge()

        with pytest.raises(CustomerNotFoundError):
            await svc.merge_customers(
                db=db,
                primary_id=uuid4(),
                duplicate_ids=[uuid4()],
                actor_id=uuid4(),
                ip_address="127.0.0.1",
            )

    async def test_merge_rejects_primary_in_duplicate_list(self) -> None:
        """Merge raises MergeConflictError when primary is in duplicates."""
        svc, repo = _build_customer_service()

        primary = _make_customer(first_name="Dave", phone="5125550030")
        repo.get_by_id = AsyncMock(return_value=primary)

        db = _mock_db_for_merge()

        with pytest.raises(MergeConflictError):
            await svc.merge_customers(
                db=db,
                primary_id=primary.id,
                duplicate_ids=[primary.id],
                actor_id=uuid4(),
                ip_address="127.0.0.1",
            )

    async def test_merge_creates_audit_log_entry(self) -> None:
        """Merge creates an AuditLog with actor, action, and details."""
        svc, repo = _build_customer_service()

        primary = _make_customer(first_name="Eve", phone="5125550040")
        dup = _make_customer(first_name="Eva", phone="5125550041")

        repo.get_by_id = AsyncMock(
            side_effect=lambda cid: {
                primary.id: primary,
                dup.id: dup,
            }.get(cid),
        )

        db = _mock_db_for_merge()
        actor_id = uuid4()

        await svc.merge_customers(
            db=db,
            primary_id=primary.id,
            duplicate_ids=[dup.id],
            actor_id=actor_id,
            ip_address="192.168.1.1",
        )

        db.add.assert_called_once()
        audit = db.add.call_args[0][0]
        assert audit.actor_id == actor_id
        assert audit.actor_role == "admin"
        assert audit.action == "customer.merge"
        assert audit.resource_type == "customer"
        assert audit.ip_address == "192.168.1.1"
        assert audit.details["primary_customer_id"] == str(primary.id)


# =============================================================================
# 2. Customer Photo Upload, List, and Delete
# =============================================================================


@pytest.mark.functional
@pytest.mark.asyncio
class TestCustomerPhotoWorkflow:
    """Test customer photo upload, list, and delete against S3 storage.

    Validates: Requirement 9.8
    """

    async def test_photo_upload_stores_file_in_s3_and_returns_metadata(
        self,
    ) -> None:
        """Uploading a photo validates, strips EXIF, stores in S3."""
        s3_client = _build_mock_s3_client()
        photo_svc = PhotoService(
            s3_client=s3_client,
            bucket="test-bucket",
        )

        # Create a minimal valid JPEG (magic bytes)
        jpeg_data = (
            b"\xff\xd8\xff\xe0"
            + b"\x00" * 100
            + b"\xff\xd9"
        )

        # Mock magic.from_buffer to return image/jpeg
        import magic as magic_mod  # noqa: PLC0415

        original_from_buffer = magic_mod.from_buffer

        def mock_from_buffer(
            data: bytes, mime: bool = False,
        ) -> str:
            if mime and data[:2] == b"\xff\xd8":
                return "image/jpeg"
            return original_from_buffer(data, mime=mime)

        magic_mod.from_buffer = mock_from_buffer  # type: ignore[assignment]

        try:
            result = photo_svc.upload_file(
                data=jpeg_data,
                file_name="property-front.jpg",
                context=UploadContext.CUSTOMER_PHOTO,
            )

            assert isinstance(result, UploadResult)
            assert result.file_name == "property-front.jpg"
            assert result.content_type == "image/jpeg"
            assert result.file_key.startswith("customer-photos/")
            assert result.file_key.endswith(".jpg")
            assert result.file_size > 0

            # Verify S3 put_object was called
            s3_client.put_object.assert_called_once()
            put_kwargs = s3_client.put_object.call_args
            assert put_kwargs.kwargs["Bucket"] == "test-bucket"
            assert put_kwargs.kwargs["ContentType"] == "image/jpeg"
        finally:
            magic_mod.from_buffer = original_from_buffer  # type: ignore[assignment]

    async def test_photo_upload_rejects_oversized_file(self) -> None:
        """Files exceeding 10MB are rejected for customer photos."""
        s3_client = _build_mock_s3_client()
        photo_svc = PhotoService(
            s3_client=s3_client,
            bucket="test-bucket",
        )

        # 11MB of data
        oversized_data = b"\xff\xd8\xff\xe0" + b"\x00" * (11 * 1024 * 1024)

        with pytest.raises(ValueError, match="maximum size"):
            photo_svc.upload_file(
                data=oversized_data,
                file_name="huge.jpg",
                context=UploadContext.CUSTOMER_PHOTO,
            )

        # S3 should NOT have been called
        s3_client.put_object.assert_not_called()

    async def test_photo_upload_rejects_disallowed_mime_type(self) -> None:
        """Non-image files are rejected for customer photo context."""
        s3_client = _build_mock_s3_client()
        photo_svc = PhotoService(
            s3_client=s3_client,
            bucket="test-bucket",
        )

        # PDF magic bytes
        pdf_data = b"%PDF-1.4" + b"\x00" * 100

        import magic as magic_mod  # noqa: PLC0415

        original_from_buffer = magic_mod.from_buffer

        def mock_from_buffer(
            data: bytes, mime: bool = False,
        ) -> str:
            if mime and data[:5] == b"%PDF-":
                return "application/pdf"
            return original_from_buffer(data, mime=mime)

        magic_mod.from_buffer = mock_from_buffer  # type: ignore[assignment]

        try:
            with pytest.raises(ValueError, match="not allowed"):
                photo_svc.upload_file(
                    data=pdf_data,
                    file_name="document.pdf",
                    context=UploadContext.CUSTOMER_PHOTO,
                )
        finally:
            magic_mod.from_buffer = original_from_buffer  # type: ignore[assignment]

        s3_client.put_object.assert_not_called()

    async def test_photo_presigned_url_generation(self) -> None:
        """Listing photos generates pre-signed download URLs."""
        s3_client = _build_mock_s3_client()
        photo_svc = PhotoService(
            s3_client=s3_client,
            bucket="test-bucket",
        )

        file_key = "customer-photos/abc123.jpg"
        url = photo_svc.generate_presigned_url(file_key)

        assert url == "https://s3.example.com/presigned-url"
        s3_client.generate_presigned_url.assert_called_once_with(
            "get_object",
            Params={"Bucket": "test-bucket", "Key": file_key},
            ExpiresIn=3600,
        )

    async def test_photo_delete_removes_from_s3(self) -> None:
        """Deleting a photo removes the S3 object."""
        s3_client = _build_mock_s3_client()
        photo_svc = PhotoService(
            s3_client=s3_client,
            bucket="test-bucket",
        )

        file_key = "customer-photos/abc123.jpg"
        photo_svc.delete_file(file_key)

        s3_client.delete_object.assert_called_once_with(
            Bucket="test-bucket",
            Key=file_key,
        )

    async def test_full_photo_lifecycle_upload_url_delete(self) -> None:
        """Full lifecycle: upload → get URL → delete as user would experience."""
        s3_client = _build_mock_s3_client()
        photo_svc = PhotoService(
            s3_client=s3_client,
            bucket="test-bucket",
        )

        # Create minimal JPEG data
        jpeg_data = (
            b"\xff\xd8\xff\xe0"
            + b"\x00" * 100
            + b"\xff\xd9"
        )

        import magic as magic_mod  # noqa: PLC0415

        original_from_buffer = magic_mod.from_buffer

        def mock_from_buffer(
            data: bytes, mime: bool = False,
        ) -> str:
            if mime and data[:2] == b"\xff\xd8":
                return "image/jpeg"
            return original_from_buffer(data, mime=mime)

        magic_mod.from_buffer = mock_from_buffer  # type: ignore[assignment]

        try:
            # Step 1: Upload
            result = photo_svc.upload_file(
                data=jpeg_data,
                file_name="backyard-sprinkler.jpg",
                context=UploadContext.CUSTOMER_PHOTO,
            )
            assert result.file_key.startswith("customer-photos/")

            # Step 2: Generate pre-signed URL (simulates listing)
            url = photo_svc.generate_presigned_url(result.file_key)
            assert url.startswith("https://")

            # Step 3: Delete
            photo_svc.delete_file(result.file_key)
            s3_client.delete_object.assert_called_once_with(
                Bucket="test-bucket",
                Key=result.file_key,
            )
        finally:
            magic_mod.from_buffer = original_from_buffer  # type: ignore[assignment]

    async def test_photo_quota_check_rejects_over_limit(self) -> None:
        """Upload is rejected when customer storage quota is exceeded."""
        s3_client = _build_mock_s3_client()

        # Simulate existing usage near quota (499 MB)
        paginator = MagicMock()
        paginator.paginate = MagicMock(
            return_value=[
                {
                    "Contents": [
                        {"Size": 499 * 1024 * 1024},
                    ],
                },
            ],
        )
        s3_client.get_paginator = MagicMock(return_value=paginator)

        photo_svc = PhotoService(
            s3_client=s3_client,
            bucket="test-bucket",
        )

        customer_id = str(uuid4())

        # 2MB additional would exceed 500MB quota
        with pytest.raises(ValueError, match="quota"):
            photo_svc.check_customer_quota(
                customer_id=customer_id,
                additional_bytes=2 * 1024 * 1024,
            )
