"""Unit tests for SalesPipelineService.record_estimate_decision_breadcrumb (Q-A).

Validates: Feature — estimate approval email portal Q-A.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from grins_platform.models.enums import SalesEntryStatus
from grins_platform.services.sales_pipeline_service import SalesPipelineService


@pytest.fixture
def audit_service() -> AsyncMock:
    svc = AsyncMock()
    svc.log_action = AsyncMock(return_value=MagicMock())
    return svc


@pytest.fixture
def pipeline(audit_service: AsyncMock) -> SalesPipelineService:
    return SalesPipelineService(
        job_service=AsyncMock(),
        audit_service=audit_service,
    )


def _make_db(entry: MagicMock | None) -> AsyncMock:
    db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none = MagicMock(return_value=entry)
    db.execute = AsyncMock(return_value=result)
    db.flush = AsyncMock()
    return db


def _make_entry(
    *,
    notes: str | None = None,
    status: str = SalesEntryStatus.SEND_ESTIMATE.value,
) -> MagicMock:
    entry = MagicMock()
    entry.id = uuid4()
    entry.status = status
    entry.notes = notes
    entry.last_contact_date = None
    entry.updated_at = None
    return entry


def _make_estimate(
    *,
    customer_id: object = None,
    lead_id: object = None,
) -> MagicMock:
    est = MagicMock()
    est.id = uuid4()
    est.customer_id = customer_id
    est.lead_id = lead_id
    return est


@pytest.mark.unit
class TestRecordEstimateDecisionBreadcrumb:
    @pytest.mark.asyncio
    async def test_with_active_entry_appends_note_and_audit(
        self,
        pipeline: SalesPipelineService,
        audit_service: AsyncMock,
    ) -> None:
        entry = _make_entry()
        db = _make_db(entry)
        est = _make_estimate(customer_id=uuid4())
        result = await pipeline.record_estimate_decision_breadcrumb(
            db, est, "approved",
        )
        assert result is entry
        assert "APPROVED" in (entry.notes or "")
        audit_service.log_action.assert_awaited_once()
        kwargs = audit_service.log_action.await_args.kwargs
        assert kwargs["action"] == "sales_entry.estimate_decision_received"
        assert kwargs["details"]["decision"] == "approved"

    @pytest.mark.asyncio
    async def test_no_matching_entry_returns_none(
        self,
        pipeline: SalesPipelineService,
        audit_service: AsyncMock,
    ) -> None:
        db = _make_db(None)
        est = _make_estimate(customer_id=uuid4())
        result = await pipeline.record_estimate_decision_breadcrumb(
            db, est, "approved",
        )
        assert result is None
        audit_service.log_action.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_falls_back_to_lead_id(
        self,
        pipeline: SalesPipelineService,
    ) -> None:
        entry = _make_entry()
        db = _make_db(entry)
        est = _make_estimate(customer_id=None, lead_id=uuid4())
        result = await pipeline.record_estimate_decision_breadcrumb(
            db, est, "rejected",
        )
        assert result is entry

    @pytest.mark.asyncio
    async def test_no_customer_no_lead_returns_none(
        self,
        pipeline: SalesPipelineService,
    ) -> None:
        db = _make_db(None)
        est = _make_estimate(customer_id=None, lead_id=None)
        result = await pipeline.record_estimate_decision_breadcrumb(
            db, est, "approved",
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_swallows_db_error(
        self,
        pipeline: SalesPipelineService,
    ) -> None:
        db = AsyncMock()
        db.execute = AsyncMock(side_effect=RuntimeError("connection lost"))
        est = _make_estimate(customer_id=uuid4())
        # Must not raise
        result = await pipeline.record_estimate_decision_breadcrumb(
            db, est, "approved",
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_appends_rejection_reason(
        self,
        pipeline: SalesPipelineService,
    ) -> None:
        entry = _make_entry()
        db = _make_db(entry)
        est = _make_estimate(customer_id=uuid4())
        await pipeline.record_estimate_decision_breadcrumb(
            db, est, "rejected", reason="Too expensive",
        )
        assert "Too expensive" in (entry.notes or "")

    @pytest.mark.asyncio
    async def test_does_not_overwrite_existing_notes(
        self,
        pipeline: SalesPipelineService,
    ) -> None:
        entry = _make_entry(notes="prior content")
        db = _make_db(entry)
        est = _make_estimate(customer_id=uuid4())
        await pipeline.record_estimate_decision_breadcrumb(
            db, est, "approved",
        )
        assert entry.notes is not None
        assert entry.notes.startswith("prior content")
        assert "APPROVED" in entry.notes

    @pytest.mark.asyncio
    async def test_handles_none_initial_notes(
        self,
        pipeline: SalesPipelineService,
    ) -> None:
        entry = _make_entry(notes=None)
        db = _make_db(entry)
        est = _make_estimate(customer_id=uuid4())
        await pipeline.record_estimate_decision_breadcrumb(
            db, est, "approved",
        )
        assert entry.notes is not None
        assert "APPROVED" in entry.notes
