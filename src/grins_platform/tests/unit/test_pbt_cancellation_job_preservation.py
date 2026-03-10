"""Property test for cancellation job preservation.

Property 13: Cancellation Preserves Non-APPROVED Jobs
For any cancelled agreement, APPROVED jobs cancelled;
SCHEDULED/IN_PROGRESS/COMPLETED jobs unchanged.

Validates: Requirements 14.2, 14.3
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from hypothesis import (
    given,
    settings,
    strategies as st,
)

from grins_platform.models.enums import AgreementStatus, JobStatus
from grins_platform.services.agreement_service import AgreementService

# Statuses that should be CANCELLED by cancel_agreement
CANCELLABLE = [JobStatus.APPROVED.value]

# Statuses that must be PRESERVED (not modified) by cancel_agreement
PRESERVED = [
    JobStatus.SCHEDULED.value,
    JobStatus.IN_PROGRESS.value,
    JobStatus.COMPLETED.value,
    JobStatus.CLOSED.value,
    JobStatus.CANCELLED.value,
]

all_statuses = st.sampled_from(CANCELLABLE + PRESERVED)
prices = st.decimals(min_value=Decimal("1.00"), max_value=Decimal("9999.99"), places=2)


def _make_job(status: str) -> MagicMock:
    job = MagicMock()
    job.id = uuid4()
    job.status = status
    job.closed_at = None
    return job


def _make_agreement(jobs: list[MagicMock]) -> MagicMock:
    agr = MagicMock()
    agr.id = uuid4()
    agr.agreement_number = "AGR-2026-001"
    agr.status = AgreementStatus.ACTIVE.value
    agr.annual_price = Decimal("500.00")
    agr.jobs = jobs
    return agr


def _make_service(agr: MagicMock) -> AgreementService:
    repo = AsyncMock()
    repo.get_by_id = AsyncMock(return_value=agr)
    repo.update = AsyncMock(return_value=agr)
    return AgreementService(
        agreement_repo=repo,
        tier_repo=AsyncMock(),
        stripe_settings=MagicMock(is_configured=False),
    )


@pytest.mark.unit
@pytest.mark.asyncio
class TestCancellationJobPreservationProperty:
    """Property 13: Cancellation preserves non-APPROVED jobs."""

    @given(job_statuses=st.lists(all_statuses, min_size=1, max_size=15))
    @settings(max_examples=50)
    async def test_approved_jobs_cancelled(
        self,
        job_statuses: list[str],
    ) -> None:
        """All APPROVED jobs transition to CANCELLED after cancellation."""
        jobs = [_make_job(s) for s in job_statuses]
        agr = _make_agreement(jobs)
        svc = _make_service(agr)

        await svc.cancel_agreement(agr.id, "test")

        for job, original in zip(jobs, job_statuses):
            if original == JobStatus.APPROVED.value:
                assert job.status == JobStatus.CANCELLED.value

    @given(job_statuses=st.lists(all_statuses, min_size=1, max_size=15))
    @settings(max_examples=50)
    async def test_non_approved_jobs_unchanged(
        self,
        job_statuses: list[str],
    ) -> None:
        """SCHEDULED/IN_PROGRESS/COMPLETED/CLOSED/CANCELLED jobs are untouched."""
        jobs = [_make_job(s) for s in job_statuses]
        agr = _make_agreement(jobs)
        svc = _make_service(agr)

        await svc.cancel_agreement(agr.id, "test")

        for job, original in zip(jobs, job_statuses):
            if original != JobStatus.APPROVED.value:
                assert job.status == original

    @given(count=st.integers(min_value=1, max_value=10))
    @settings(max_examples=20)
    async def test_all_approved_all_cancelled(self, count: int) -> None:
        """When every job is APPROVED, every job becomes CANCELLED."""
        jobs = [_make_job(JobStatus.APPROVED.value) for _ in range(count)]
        agr = _make_agreement(jobs)
        svc = _make_service(agr)

        await svc.cancel_agreement(agr.id, "test")

        assert all(j.status == JobStatus.CANCELLED.value for j in jobs)

    @given(count=st.integers(min_value=1, max_value=10))
    @settings(max_examples=20)
    async def test_all_completed_none_changed(self, count: int) -> None:
        """When every job is COMPLETED, none are modified."""
        jobs = [_make_job(JobStatus.COMPLETED.value) for _ in range(count)]
        agr = _make_agreement(jobs)
        svc = _make_service(agr)

        await svc.cancel_agreement(agr.id, "test")

        assert all(j.status == JobStatus.COMPLETED.value for j in jobs)

    @given(
        approved=st.integers(min_value=1, max_value=5),
        scheduled=st.integers(min_value=1, max_value=5),
    )
    @settings(max_examples=30)
    async def test_mixed_only_approved_cancelled(
        self,
        approved: int,
        scheduled: int,
    ) -> None:
        """In a mix of APPROVED + SCHEDULED, only APPROVED become CANCELLED."""
        jobs_approved = [_make_job(JobStatus.APPROVED.value) for _ in range(approved)]
        jobs_scheduled = [
            _make_job(JobStatus.SCHEDULED.value) for _ in range(scheduled)
        ]
        agr = _make_agreement(jobs_approved + jobs_scheduled)
        svc = _make_service(agr)

        await svc.cancel_agreement(agr.id, "test")

        assert all(j.status == JobStatus.CANCELLED.value for j in jobs_approved)
        assert all(j.status == JobStatus.SCHEDULED.value for j in jobs_scheduled)
