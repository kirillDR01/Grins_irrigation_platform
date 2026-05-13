"""Functional tests for sales pipeline flow.

Tests the full sales pipeline lifecycle: create from lead, advance
through all statuses, and convert to job (post-Cluster-C: no SignWell
signature gate, no force override) — using mocked DB sessions following
the project's functional test pattern.

Validates: Requirements 14.3, 14.4, 14.5, 14.6, 16.2;
cluster-c-job-creation-and-signwell-removal.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from grins_platform.exceptions import (
    InvalidSalesTransitionError,
)
from grins_platform.models.enums import SalesEntryStatus
from grins_platform.models.sales import SalesEntry
from grins_platform.services.sales_pipeline_service import SalesPipelineService

# =============================================================================
# Helpers
# =============================================================================


def _make_sales_entry(**overrides: Any) -> MagicMock:
    """Create a mock SalesEntry with all fields."""
    entry = MagicMock(spec=SalesEntry)
    entry.id = overrides.get("id", uuid4())
    entry.customer_id = overrides.get("customer_id", uuid4())
    entry.property_id = overrides.get("property_id")
    entry.lead_id = overrides.get("lead_id")
    entry.job_type = overrides.get("job_type", "estimate")
    entry.status = overrides.get(
        "status",
        SalesEntryStatus.SCHEDULE_ESTIMATE.value,
    )
    entry.last_contact_date = overrides.get("last_contact_date")
    entry.notes = overrides.get("notes")
    entry.override_flag = overrides.get("override_flag", False)
    entry.closed_reason = overrides.get("closed_reason")
    # Legacy column kept on the model; new flows no longer populate it.
    entry.signwell_document_id = overrides.get("signwell_document_id")
    entry.created_at = overrides.get(
        "created_at",
        datetime.now(tz=timezone.utc),
    )
    entry.updated_at = overrides.get(
        "updated_at",
        datetime.now(tz=timezone.utc),
    )
    return entry


def _make_job(**overrides: Any) -> MagicMock:
    """Create a mock Job returned by JobService.create_job."""
    job = MagicMock()
    job.id = overrides.get("id", uuid4())
    job.customer_id = overrides.get("customer_id", uuid4())
    job.property_id = overrides.get("property_id")
    job.job_type = overrides.get("job_type", "estimate")
    job.status = overrides.get("status", "to_be_scheduled")
    return job


def _build_service(
    *,
    job_service: AsyncMock | None = None,
    audit_service: AsyncMock | None = None,
) -> tuple[SalesPipelineService, AsyncMock, AsyncMock]:
    """Build a SalesPipelineService with mocked dependencies.

    Returns:
        Tuple of (service, job_service_mock, audit_service_mock).
    """
    js = job_service or AsyncMock()
    aus = audit_service or AsyncMock()
    svc = SalesPipelineService(job_service=js, audit_service=aus)
    return svc, js, aus


def _mock_db_returning(entry: MagicMock) -> AsyncMock:
    """Create a mock AsyncSession that returns the given entry on execute."""
    db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = entry
    db.execute.return_value = result
    db.flush = AsyncMock()
    db.refresh = AsyncMock()
    return db


# =============================================================================
# 1. Full Pipeline: Create → Advance Through All Statuses → Convert to Job
# =============================================================================


@pytest.mark.functional
@pytest.mark.asyncio
class TestFullSalesPipelineFlow:
    """Test the complete sales pipeline from lead to job conversion.

    Validates: Requirements 14.3, 14.4, 14.5, 14.6, 16.2
    """

    async def test_create_from_lead_initialises_at_schedule_estimate(
        self,
    ) -> None:
        """Creating a sales entry from a lead starts at schedule_estimate.

        Validates: Requirement 14.3
        """
        svc, _, _ = _build_service()
        db = AsyncMock()
        db.flush = AsyncMock()
        db.refresh = AsyncMock()

        lead_id = uuid4()
        customer_id = uuid4()

        entry = await svc.create_from_lead(
            db,
            lead_id=lead_id,
            customer_id=customer_id,
            job_type="repair",
        )

        assert entry.status == SalesEntryStatus.SCHEDULE_ESTIMATE.value
        assert entry.customer_id == customer_id
        assert entry.lead_id == lead_id
        db.add.assert_called_once()

    async def test_advance_through_all_statuses_one_step_at_a_time(
        self,
    ) -> None:
        """Advancing moves exactly one step forward each time.

        The estimate-scheduled → send_estimate transition (migration
        20260509_120000) requires the latest ``SalesCalendarEvent`` to
        be ``confirmation_status='confirmed'`` — this test feeds a
        confirmed event to the gate so the legacy progression still
        completes end-to-end.

        Validates: Requirements 14.3, 14.4, 14.5;
        sales-pipeline-estimate-visit-confirmation-lifecycle (OQ-6).
        """
        svc, _, _ = _build_service()

        expected_progression = [
            SalesEntryStatus.SCHEDULE_ESTIMATE,
            SalesEntryStatus.ESTIMATE_SCHEDULED,
            SalesEntryStatus.SEND_ESTIMATE,
            SalesEntryStatus.PENDING_APPROVAL,
            SalesEntryStatus.SEND_CONTRACT,
            SalesEntryStatus.CLOSED_WON,
        ]

        entry_id = uuid4()
        entry = _make_sales_entry(
            id=entry_id,
            status=SalesEntryStatus.SCHEDULE_ESTIMATE.value,
        )

        confirmed_event = MagicMock()
        confirmed_event.confirmation_status = "confirmed"

        for i in range(len(expected_progression) - 1):
            current = expected_progression[i]
            expected_next = expected_progression[i + 1]

            entry.status = current.value
            db = AsyncMock()
            entry_result = MagicMock()
            entry_result.scalar_one_or_none.return_value = entry
            event_result = MagicMock()
            event_result.scalar_one_or_none.return_value = confirmed_event
            # Each advance executes once for the entry; when the gate
            # fires (target=SEND_ESTIMATE) it executes again to fetch
            # the latest calendar event. side_effect supplies both.
            db.execute = AsyncMock(side_effect=[entry_result, event_result])
            db.flush = AsyncMock()
            db.refresh = AsyncMock()

            result = await svc.advance_status(db, entry_id)

            assert result.status == expected_next.value, (
                f"Expected {current.value} → {expected_next.value}, got {result.status}"
            )

    async def test_advance_from_terminal_closed_won_raises(self) -> None:
        """Advancing from Closed-Won raises InvalidSalesTransitionError.

        Validates: Requirement 14.3
        """
        svc, _, _ = _build_service()
        entry = _make_sales_entry(
            status=SalesEntryStatus.CLOSED_WON.value,
        )
        db = _mock_db_returning(entry)

        with pytest.raises(InvalidSalesTransitionError):
            await svc.advance_status(db, entry.id)

    async def test_advance_from_terminal_closed_lost_raises(self) -> None:
        """Advancing from Closed-Lost raises InvalidSalesTransitionError.

        Validates: Requirement 14.3
        """
        svc, _, _ = _build_service()
        entry = _make_sales_entry(
            status=SalesEntryStatus.CLOSED_LOST.value,
        )
        db = _mock_db_returning(entry)

        with pytest.raises(InvalidSalesTransitionError):
            await svc.advance_status(db, entry.id)


# =============================================================================
# 2. Convert to Job — Signature Gating and Force Override
# =============================================================================


@pytest.mark.functional
@pytest.mark.asyncio
class TestConvertToJobFlow:
    """Test convert-to-job with signature gating and force override.

    Validates: Requirements 14.6, 16.2
    """

    async def test_convert_creates_job_and_closes_won(
        self,
    ) -> None:
        """Convert to job succeeds and transitions entry to CLOSED_WON.

        Post-Cluster-C: no SignWell signature gate. An entry can be
        converted regardless of whether ``signwell_document_id`` is set.

        Validates: Requirement 16.2;
        cluster-c-job-creation-and-signwell-removal.
        """
        mock_job = _make_job()
        js = AsyncMock()
        js.create_job = AsyncMock(return_value=mock_job)
        svc, _, _ = _build_service(job_service=js)

        entry = _make_sales_entry(
            status=SalesEntryStatus.SEND_CONTRACT.value,
        )
        db = _mock_db_returning(entry)

        job = await svc.convert_to_job(db, entry.id)

        assert job.id == mock_job.id
        assert entry.status == SalesEntryStatus.CLOSED_WON.value
        js.create_job.assert_awaited_once()

    async def test_convert_to_job_no_signature_required(
        self,
    ) -> None:
        """convert_to_job no longer raises when the entry has no SignWell doc.

        Validates: cluster-c-job-creation-and-signwell-removal.
        """
        mock_job = _make_job()
        js = AsyncMock()
        js.create_job = AsyncMock(return_value=mock_job)
        svc, _, _ = _build_service(job_service=js)

        entry = _make_sales_entry(
            status=SalesEntryStatus.SEND_CONTRACT.value,
        )
        db = _mock_db_returning(entry)

        # Must not raise — signature gate removed.
        job = await svc.convert_to_job(db, entry.id)
        assert job.id == mock_job.id
        assert entry.status == SalesEntryStatus.CLOSED_WON.value

    async def test_convert_from_terminal_status_raises(self) -> None:
        """Cannot convert an already-closed entry.

        Validates: Requirement 16.2
        """
        svc, _, _ = _build_service()
        entry = _make_sales_entry(
            status=SalesEntryStatus.CLOSED_WON.value,
        )
        db = _mock_db_returning(entry)

        with pytest.raises(InvalidSalesTransitionError):
            await svc.convert_to_job(db, entry.id)


# =============================================================================
# 3. Mark Lost and Manual Override
# =============================================================================


@pytest.mark.functional
@pytest.mark.asyncio
class TestMarkLostAndManualOverride:
    """Test mark-lost and manual status override flows.

    Validates: Requirements 14.4, 14.5
    """

    async def test_mark_lost_from_active_status_transitions_to_closed_lost(
        self,
    ) -> None:
        """Mark lost from any active status sets Closed-Lost.

        Validates: Requirement 14.4
        """
        svc, _, aus = _build_service()
        aus.log_action = AsyncMock(return_value=MagicMock())

        entry = _make_sales_entry(
            status=SalesEntryStatus.PENDING_APPROVAL.value,
        )
        db = _mock_db_returning(entry)

        result = await svc.mark_lost(
            db,
            entry.id,
            closed_reason="Customer declined",
        )

        assert result.status == SalesEntryStatus.CLOSED_LOST.value
        assert result.closed_reason == "Customer declined"

    async def test_mark_lost_from_terminal_raises(self) -> None:
        """Cannot mark lost on an already-terminal entry.

        Validates: Requirement 14.4
        """
        svc, _, _ = _build_service()
        entry = _make_sales_entry(
            status=SalesEntryStatus.CLOSED_WON.value,
        )
        db = _mock_db_returning(entry)

        with pytest.raises(InvalidSalesTransitionError):
            await svc.mark_lost(db, entry.id)

    async def test_manual_override_sets_any_status_with_audit(self) -> None:
        """Manual override jumps to any status and writes audit log.

        Validates: Requirement 14.5
        """
        aus = AsyncMock()
        aus.log_action = AsyncMock(return_value=MagicMock())
        svc, _, _ = _build_service(audit_service=aus)

        entry = _make_sales_entry(
            status=SalesEntryStatus.SCHEDULE_ESTIMATE.value,
        )
        db = _mock_db_returning(entry)

        result = await svc.manual_override_status(
            db,
            entry.id,
            SalesEntryStatus.SEND_CONTRACT,
        )

        assert result.status == SalesEntryStatus.SEND_CONTRACT.value
        aus.log_action.assert_awaited_once()
        audit_call = aus.log_action.call_args
        assert audit_call.kwargs["action"] == "sales_entry.status_override"
