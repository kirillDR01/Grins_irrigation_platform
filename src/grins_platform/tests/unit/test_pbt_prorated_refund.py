"""Property test for prorated refund calculation.

Property 12: Prorated Refund Calculation
For any cancelled agreement, cancellation_refund_amount =
annual_price * (remaining_visits / total_visits).

Validates: Requirements 14.4
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

prices = st.decimals(min_value=Decimal("1.00"), max_value=Decimal("9999.99"), places=2)
job_counts = st.integers(min_value=0, max_value=20)

# Statuses that count as "remaining" in the refund calculation
REMAINING_STATUSES = [
    JobStatus.TO_BE_SCHEDULED.value,
    JobStatus.IN_PROGRESS.value,
]
# Statuses that do NOT count as remaining
DONE_STATUSES = [
    JobStatus.COMPLETED.value,
    JobStatus.CANCELLED.value,
]

all_job_statuses = st.sampled_from(
    REMAINING_STATUSES + DONE_STATUSES,
)


def _make_job(status: str) -> MagicMock:
    job = MagicMock()
    job.id = uuid4()
    job.status = status
    return job


def _make_agreement(
    annual_price: Decimal,
    jobs: list[MagicMock],
) -> MagicMock:
    agr = MagicMock()
    agr.id = uuid4()
    agr.agreement_number = "AGR-2026-001"
    agr.status = AgreementStatus.ACTIVE.value
    agr.annual_price = annual_price
    agr.jobs = jobs
    return agr


def _make_service(agr: MagicMock) -> tuple[AgreementService, AsyncMock]:
    repo = AsyncMock()
    repo.get_by_id = AsyncMock(return_value=agr)
    repo.update = AsyncMock(return_value=agr)
    svc = AgreementService(
        agreement_repo=repo,
        tier_repo=AsyncMock(),
        stripe_settings=MagicMock(is_configured=False),
    )
    return svc, repo


@pytest.mark.unit
@pytest.mark.asyncio
class TestProratedRefundProperty:
    """Property-based tests for prorated refund calculation."""

    @given(
        annual_price=prices,
        job_statuses=st.lists(all_job_statuses, min_size=1, max_size=15),
    )
    @settings(max_examples=50)
    async def test_refund_equals_price_times_remaining_over_total(
        self,
        annual_price: Decimal,
        job_statuses: list[str],
    ) -> None:
        """refund = annual_price * remaining_visits / total_visits."""
        jobs = [_make_job(s) for s in job_statuses]
        agr = _make_agreement(annual_price, jobs)
        svc, repo = _make_service(agr)

        await svc.cancel_agreement(agr.id, "test")

        total = len(job_statuses)
        remaining = sum(1 for s in job_statuses if s in REMAINING_STATUSES)
        expected = (
            annual_price * Decimal(str(remaining)) / Decimal(str(total))
        ).quantize(Decimal("0.01"))

        last_update = repo.update.call_args_list[-1]
        actual = last_update.args[1]["cancellation_refund_amount"]
        assert actual == expected

    @given(annual_price=prices)
    @settings(max_examples=20)
    async def test_zero_jobs_zero_refund(self, annual_price: Decimal) -> None:
        """No jobs → refund is zero regardless of price."""
        agr = _make_agreement(annual_price, [])
        svc, repo = _make_service(agr)

        await svc.cancel_agreement(agr.id, "test")

        last_update = repo.update.call_args_list[-1]
        assert last_update.args[1]["cancellation_refund_amount"] == Decimal("0.00")

    @given(annual_price=prices, count=st.integers(min_value=1, max_value=10))
    @settings(max_examples=20)
    async def test_all_completed_zero_refund(
        self,
        annual_price: Decimal,
        count: int,
    ) -> None:
        """All COMPLETED/CANCELLED → refund is zero."""
        jobs = [_make_job(JobStatus.COMPLETED.value) for _ in range(count)]
        agr = _make_agreement(annual_price, jobs)
        svc, repo = _make_service(agr)

        await svc.cancel_agreement(agr.id, "test")

        last_update = repo.update.call_args_list[-1]
        assert last_update.args[1]["cancellation_refund_amount"] == Decimal("0.00")

    @given(annual_price=prices, count=st.integers(min_value=1, max_value=10))
    @settings(max_examples=20)
    async def test_all_to_be_scheduled_full_refund(
        self,
        annual_price: Decimal,
        count: int,
    ) -> None:
        """All TO_BE_SCHEDULED → refund equals full annual_price."""
        jobs = [_make_job(JobStatus.TO_BE_SCHEDULED.value) for _ in range(count)]
        agr = _make_agreement(annual_price, jobs)
        svc, repo = _make_service(agr)

        await svc.cancel_agreement(agr.id, "test")

        last_update = repo.update.call_args_list[-1]
        expected_refund = annual_price.quantize(Decimal("0.01"))
        assert last_update.args[1]["cancellation_refund_amount"] == expected_refund
