"""Unit tests for signing document wiring in the sales pipeline.

Tests that the email and embedded signing endpoints use real uploaded
documents (via S3 presigned URLs) instead of placeholder URLs, return
422 when no document exists, and select the most recent document by default.

Validates: Requirements 9.1, 9.2, 9.3
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import uuid4

import pytest

from grins_platform.models.customer_document import CustomerDocument

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_customer(
    *,
    customer_id: object | None = None,
    email: str = "customer@example.com",
) -> Mock:
    c = Mock()
    c.id = customer_id or uuid4()
    c.first_name = "John"
    c.last_name = "Doe"
    c.email = email
    c.phone = "+15551234567"
    return c


def _make_entry(
    *,
    customer_id: object | None = None,
    signwell_document_id: str | None = None,
) -> Mock:
    cust = _make_customer(customer_id=customer_id)
    entry = Mock()
    entry.id = uuid4()
    entry.customer_id = cust.id
    entry.customer = cust
    entry.property = None
    entry.signwell_document_id = signwell_document_id
    entry.status = "send_estimate"
    return entry


def _make_document(
    *,
    customer_id: object | None = None,
    document_type: str = "estimate",
    file_key: str = "docs/estimate-abc123.pdf",
    uploaded_at: datetime | None = None,
) -> Mock:
    doc = Mock(spec=CustomerDocument)
    doc.id = uuid4()
    doc.customer_id = customer_id or uuid4()
    doc.file_key = file_key
    doc.file_name = "estimate.pdf"
    doc.document_type = document_type
    doc.mime_type = "application/pdf"
    doc.size_bytes = 102400
    doc.uploaded_at = uploaded_at or datetime.now(tz=timezone.utc)
    return doc


def _mock_user() -> Mock:
    user = Mock()
    user.id = uuid4()
    user.is_active = True
    user.role = "admin"
    user.email = "admin@example.com"
    return user


# ---------------------------------------------------------------------------
# _get_signing_document helper tests
# ---------------------------------------------------------------------------


@pytest.mark.unit()
class TestGetSigningDocument:
    """Test the _get_signing_document helper selects the correct document.

    Validates: Requirements 9.1, 9.2, 9.3
    """

    @pytest.mark.asyncio()
    async def test_returns_most_recent_document(self) -> None:
        """Most recent estimate/contract document is returned.

        Validates: Requirement 9.3
        """
        from grins_platform.api.v1.sales_pipeline import _get_signing_document

        customer_id = uuid4()
        recent_doc = _make_document(
            customer_id=customer_id,
            file_key="docs/latest-estimate.pdf",
        )

        mock_session = AsyncMock()
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = recent_doc
        mock_session.execute.return_value = mock_result

        result = await _get_signing_document(mock_session, customer_id)

        assert result is recent_doc
        assert result.file_key == "docs/latest-estimate.pdf"

    @pytest.mark.asyncio()
    async def test_returns_none_when_no_document(self) -> None:
        """Returns None when no estimate/contract document exists.

        Validates: Requirement 9.2
        """
        from grins_platform.api.v1.sales_pipeline import _get_signing_document

        mock_session = AsyncMock()
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await _get_signing_document(mock_session, uuid4())

        assert result is None

    @pytest.mark.asyncio()
    async def test_strict_scope_excludes_legacy_unscoped_rows(self) -> None:
        """bughunt M-11: with sales_entry_id provided and the default
        ``include_legacy=False``, the WHERE clause must demand
        ``CustomerDocument.sales_entry_id == sales_entry_id`` so a
        legacy ``sales_entry_id IS NULL`` row never leaks across to a
        different entry's signing flow.
        """
        from grins_platform.api.v1.sales_pipeline import _get_signing_document

        mock_session = AsyncMock()
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        sales_entry_id = uuid4()
        await _get_signing_document(
            mock_session,
            uuid4(),
            sales_entry_id=sales_entry_id,
        )

        # Inspect the compiled SQL — the strict WHERE must reference
        # an equality check on sales_entry_id, never the IS NULL branch.
        stmt = mock_session.execute.await_args.args[0]
        sql = str(stmt.compile(compile_kwargs={"literal_binds": True}))
        assert "sales_entry_id =" in sql
        # Strict-scope path must not include the legacy-fallback OR clause.
        assert "sales_entry_id IS NULL" not in sql

    @pytest.mark.asyncio()
    async def test_include_legacy_restores_unscoped_fallback(self) -> None:
        """bughunt M-11: opting back into the legacy fallback (for
        reporting reads) re-enables the ``sales_entry_id IS NULL``
        branch in the WHERE clause."""
        from grins_platform.api.v1.sales_pipeline import _get_signing_document

        mock_session = AsyncMock()
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        await _get_signing_document(
            mock_session,
            uuid4(),
            sales_entry_id=uuid4(),
            include_legacy=True,
        )

        stmt = mock_session.execute.await_args.args[0]
        sql = str(stmt.compile(compile_kwargs={"literal_binds": True}))
        assert "IS NULL" in sql


# ---------------------------------------------------------------------------
# Email signing endpoint tests
# ---------------------------------------------------------------------------


@pytest.mark.unit()
class TestEmailSigningWithDocument:
    """Test trigger_email_signing uses real uploaded document.

    Validates: Requirements 9.1, 9.2, 9.4
    """

    @pytest.mark.asyncio()
    async def test_email_signing_passes_presigned_url_to_signwell(self) -> None:
        """Signing with uploaded document passes presigned URL, not placeholder.

        Validates: Requirement 9.1
        """
        entry = _make_entry()
        signing_doc = _make_document(
            customer_id=entry.customer_id,
            file_key="docs/real-estimate.pdf",
        )
        presigned_url = (
            "https://s3.amazonaws.com/bucket/docs/real-estimate.pdf?signed=abc"
        )

        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()

        # First execute: fetch SalesEntry
        entry_result = Mock()
        entry_result.scalar_one_or_none.return_value = entry
        # Second execute: _get_signing_document query
        doc_result = Mock()
        doc_result.scalar_one_or_none.return_value = signing_doc

        mock_session.execute = AsyncMock(side_effect=[entry_result, doc_result])

        mock_signwell = AsyncMock()
        mock_signwell.create_document_for_email.return_value = {
            "id": "sw-doc-123",
            "status": "sent",
        }

        mock_photo_service = MagicMock()
        mock_photo_service.generate_presigned_url.return_value = presigned_url

        with (
            patch(
                "grins_platform.services.signwell.client.SignWellClient",
                return_value=mock_signwell,
            ),
            patch(
                "grins_platform.api.v1.sales_pipeline.PhotoService",
                return_value=mock_photo_service,
            ),
        ):
            from grins_platform.api.v1.sales_pipeline import trigger_email_signing

            result = await trigger_email_signing(
                entry_id=entry.id,
                _user=_mock_user(),
                session=mock_session,
            )

        # Verify presigned URL was generated from the real document
        mock_photo_service.generate_presigned_url.assert_called_once_with(
            signing_doc.file_key,
        )
        # Verify SignWell received the real presigned URL
        mock_signwell.create_document_for_email.assert_called_once_with(
            pdf_url=presigned_url,
            email=entry.customer.email,
            name=f"{entry.customer.first_name} {entry.customer.last_name}",
        )
        assert result["document_id"] == "sw-doc-123"
        assert result["status"] == "sent"

    @pytest.mark.asyncio()
    async def test_email_signing_without_document_returns_422(self) -> None:
        """Signing without uploaded document returns 422 error.

        Validates: Requirement 9.2
        """
        entry = _make_entry()

        mock_session = AsyncMock()
        # First execute: fetch SalesEntry
        entry_result = Mock()
        entry_result.scalar_one_or_none.return_value = entry
        # Second execute: no document found
        doc_result = Mock()
        doc_result.scalar_one_or_none.return_value = None

        mock_session.execute = AsyncMock(side_effect=[entry_result, doc_result])

        from fastapi import HTTPException

        from grins_platform.api.v1.sales_pipeline import trigger_email_signing

        with pytest.raises(HTTPException) as exc_info:
            await trigger_email_signing(
                entry_id=entry.id,
                _user=_mock_user(),
                session=mock_session,
            )

        assert exc_info.value.status_code == 422
        assert "Upload an estimate document first" in str(exc_info.value.detail)


# ---------------------------------------------------------------------------
# Embedded signing endpoint tests
# ---------------------------------------------------------------------------


@pytest.mark.unit()
class TestEmbeddedSigningWithDocument:
    """Test get_embedded_signing uses real uploaded document.

    Validates: Requirements 9.1, 9.2, 9.4
    """

    @pytest.mark.asyncio()
    async def test_embedded_signing_passes_presigned_url_to_signwell(self) -> None:
        """Embedded signing with uploaded document passes presigned URL.

        Validates: Requirement 9.1
        """
        entry = _make_entry(signwell_document_id=None)
        signing_doc = _make_document(
            customer_id=entry.customer_id,
            file_key="docs/contract-v2.pdf",
        )
        presigned_url = (
            "https://s3.amazonaws.com/bucket/docs/contract-v2.pdf?signed=xyz"
        )

        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.flush = AsyncMock()

        # First execute: fetch SalesEntry
        entry_result = Mock()
        entry_result.scalar_one_or_none.return_value = entry
        # Second execute: _get_signing_document query
        doc_result = Mock()
        doc_result.scalar_one_or_none.return_value = signing_doc

        mock_session.execute = AsyncMock(side_effect=[entry_result, doc_result])

        mock_signwell = AsyncMock()
        mock_signwell.create_document_for_embedded.return_value = {
            "id": "sw-embedded-456",
        }
        mock_signwell.get_embedded_url.return_value = (
            "https://app.signwell.com/embed/sw-embedded-456"
        )

        mock_photo_service = MagicMock()
        mock_photo_service.generate_presigned_url.return_value = presigned_url

        with (
            patch(
                "grins_platform.services.signwell.client.SignWellClient",
                return_value=mock_signwell,
            ),
            patch(
                "grins_platform.api.v1.sales_pipeline.PhotoService",
                return_value=mock_photo_service,
            ),
        ):
            from grins_platform.api.v1.sales_pipeline import get_embedded_signing

            result = await get_embedded_signing(
                entry_id=entry.id,
                _user=_mock_user(),
                session=mock_session,
            )

        # Verify presigned URL was generated from the real document
        mock_photo_service.generate_presigned_url.assert_called_once_with(
            signing_doc.file_key,
        )
        # Verify SignWell received the real presigned URL for embedded doc creation
        mock_signwell.create_document_for_embedded.assert_called_once_with(
            pdf_url=presigned_url,
            signer_name=f"{entry.customer.first_name} {entry.customer.last_name}",
        )
        assert result["signing_url"] == "https://app.signwell.com/embed/sw-embedded-456"

    @pytest.mark.asyncio()
    async def test_embedded_signing_without_document_returns_422(self) -> None:
        """Embedded signing without uploaded document returns 422 error.

        Validates: Requirement 9.2
        """
        entry = _make_entry()

        mock_session = AsyncMock()
        # First execute: fetch SalesEntry
        entry_result = Mock()
        entry_result.scalar_one_or_none.return_value = entry
        # Second execute: no document found
        doc_result = Mock()
        doc_result.scalar_one_or_none.return_value = None

        mock_session.execute = AsyncMock(side_effect=[entry_result, doc_result])

        from fastapi import HTTPException

        from grins_platform.api.v1.sales_pipeline import get_embedded_signing

        with pytest.raises(HTTPException) as exc_info:
            await get_embedded_signing(
                entry_id=entry.id,
                _user=_mock_user(),
                session=mock_session,
            )

        assert exc_info.value.status_code == 422
        assert "Upload an estimate document first" in str(exc_info.value.detail)

    @pytest.mark.asyncio()
    async def test_embedded_signing_reuses_existing_signwell_doc(self) -> None:
        """When entry already has signwell_document_id, reuse it.

        Validates: Requirement 9.1
        """
        entry = _make_entry(signwell_document_id="sw-existing-789")
        signing_doc = _make_document(
            customer_id=entry.customer_id,
            file_key="docs/estimate-existing.pdf",
        )
        presigned_url = (
            "https://s3.amazonaws.com/bucket/docs/estimate-existing.pdf?signed=reuse"
        )

        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()

        # First execute: fetch SalesEntry
        entry_result = Mock()
        entry_result.scalar_one_or_none.return_value = entry
        # Second execute: _get_signing_document query
        doc_result = Mock()
        doc_result.scalar_one_or_none.return_value = signing_doc

        mock_session.execute = AsyncMock(side_effect=[entry_result, doc_result])

        mock_signwell = AsyncMock()
        mock_signwell.get_embedded_url.return_value = (
            "https://app.signwell.com/embed/sw-existing-789"
        )

        mock_photo_service = MagicMock()
        mock_photo_service.generate_presigned_url.return_value = presigned_url

        with (
            patch(
                "grins_platform.services.signwell.client.SignWellClient",
                return_value=mock_signwell,
            ),
            patch(
                "grins_platform.api.v1.sales_pipeline.PhotoService",
                return_value=mock_photo_service,
            ),
        ):
            from grins_platform.api.v1.sales_pipeline import get_embedded_signing

            result = await get_embedded_signing(
                entry_id=entry.id,
                _user=_mock_user(),
                session=mock_session,
            )

        # Should NOT create a new document — reuse existing
        mock_signwell.create_document_for_embedded.assert_not_called()
        # Should get embedded URL for the existing document
        mock_signwell.get_embedded_url.assert_called_once_with("sw-existing-789")
        assert result["signing_url"] == "https://app.signwell.com/embed/sw-existing-789"
