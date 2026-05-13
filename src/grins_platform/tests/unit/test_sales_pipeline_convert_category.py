"""Unit tests for ``SalesPipelineService.convert_to_job`` category override
and the removal of the SignWell signature gate.

Validates: cluster-c-job-creation-and-signwell-removal Tasks 1 and 2.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from grins_platform.models.enums import (
    JobCategory,
    SalesEntryStatus,
)
from grins_platform.services.sales_pipeline_service import SalesPipelineService

# =============================================================================
# Fixtures (mirrored from test_sales_pipeline_and_signwell.py:248-327)
# =============================================================================


@pytest.fixture()
def mock_job_service() -> AsyncMock:
    return AsyncMock()


@pytest.fixture()
def mock_audit_service() -> AsyncMock:
    svc = AsyncMock()
    svc.log_action = AsyncMock(return_value=Mock(id=uuid4()))
    return svc


@pytest.fixture()
def pipeline_service(
    mock_job_service: AsyncMock,
    mock_audit_service: AsyncMock,
) -> SalesPipelineService:
    return SalesPipelineService(
        job_service=mock_job_service,
        audit_service=mock_audit_service,
    )


@pytest.fixture()
def mock_db() -> AsyncMock:
    db = AsyncMock()
    db.flush = AsyncMock()
    db.refresh = AsyncMock()
    return db


def _make_entry(
    status: str = SalesEntryStatus.SEND_CONTRACT.value,
    *,
    signwell_document_id: str | None = None,
) -> Mock:
    entry = Mock()
    entry.id = uuid4()
    entry.customer_id = uuid4()
    entry.property_id = uuid4()
    entry.lead_id = uuid4()
    entry.job_type = "estimate"
    entry.status = status
    entry.notes = "test notes"
    entry.signwell_document_id = signwell_document_id
    entry.override_flag = False
    entry.closed_reason = None
    entry.nudges_paused_until = None
    entry.dismissed_at = None
    entry.updated_at = datetime.now(tz=timezone.utc)
    entry.customer_tags = None
    return entry


# =============================================================================
# Tests
# =============================================================================


@pytest.mark.unit()
class TestConvertToJobCategoryOverride:
    """convert_to_job forces JobCategory.READY_TO_SCHEDULE via category_override."""

    @pytest.mark.asyncio()
    async def test_convert_to_job_sets_category_to_ready_to_schedule(
        self,
        pipeline_service: SalesPipelineService,
        mock_db: AsyncMock,
        mock_job_service: AsyncMock,
    ) -> None:
        """convert_to_job must call JobService.create_job with
        ``category_override=JobCategory.READY_TO_SCHEDULE``."""
        entry = _make_entry()
        mock_db.execute = AsyncMock(
            return_value=Mock(scalar_one_or_none=Mock(return_value=entry)),
        )
        mock_job = Mock(id=uuid4(), category=JobCategory.READY_TO_SCHEDULE.value)
        mock_job_service.create_job = AsyncMock(return_value=mock_job)

        result = await pipeline_service.convert_to_job(mock_db, entry.id)

        job = result[0] if isinstance(result, tuple) else result
        assert job.id == mock_job.id

        # Verify create_job was called once with the category_override kwarg.
        mock_job_service.create_job.assert_awaited_once()
        kwargs = mock_job_service.create_job.await_args.kwargs
        assert kwargs.get("category_override") == JobCategory.READY_TO_SCHEDULE

    @pytest.mark.asyncio()
    async def test_convert_to_job_no_signature_required_anymore(
        self,
        pipeline_service: SalesPipelineService,
        mock_db: AsyncMock,
        mock_job_service: AsyncMock,
    ) -> None:
        """Per Cluster C, ``convert_to_job`` no longer raises
        ``SignatureRequiredError`` when ``signwell_document_id`` is None.
        It simply succeeds and returns the created job."""
        entry = _make_entry(signwell_document_id=None)
        mock_db.execute = AsyncMock(
            return_value=Mock(scalar_one_or_none=Mock(return_value=entry)),
        )
        mock_job = Mock(id=uuid4())
        mock_job_service.create_job = AsyncMock(return_value=mock_job)

        # Must NOT raise.
        result = await pipeline_service.convert_to_job(mock_db, entry.id)

        job = result[0] if isinstance(result, tuple) else result
        assert job.id == mock_job.id
        assert entry.status == SalesEntryStatus.CLOSED_WON.value
