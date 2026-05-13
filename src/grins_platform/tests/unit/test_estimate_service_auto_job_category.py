"""Unit tests for the auto-job-on-approval JobCategory override in
``EstimateService._maybe_auto_create_job``.

The standalone branch now passes ``category_override=JobCategory.READY_TO_SCHEDULE``
to ``JobService.create_job`` so the resulting Job lands ready-to-schedule
instead of inheriting the (stale) "Needs Estimate" badge.

The attached branch does NOT call ``create_job`` at all — it copies the
estimate scope into the parent job's existing scope_items.

Validates: cluster-c-job-creation-and-signwell-removal Task 3.
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from grins_platform.models.enums import JobCategory
from grins_platform.services.estimate_service import EstimateService


def _make_service(
    *,
    job_service: AsyncMock | None = None,
    business_setting_service: AsyncMock | None = None,
    audit_service: AsyncMock | None = None,
) -> EstimateService:
    repo = AsyncMock()
    repo.session = AsyncMock()
    return EstimateService(
        estimate_repository=repo,
        portal_base_url="http://localhost:5173",
        email_service=None,
        job_service=job_service,
        business_setting_service=business_setting_service,
        audit_service=audit_service,
    )


def _make_estimate(
    *,
    customer_id: object | None = None,
    job_id: object | None = None,
) -> MagicMock:
    est = MagicMock()
    est.id = uuid4()
    est.customer_id = customer_id
    est.job_id = job_id
    est.total = Decimal("499.00")
    est.notes = None
    est.line_items = [
        {"description": "Spring start-up", "unit_price": 250, "quantity": 2},
    ]
    return est


@pytest.mark.unit
class TestMaybeAutoCreateJobCategory:
    """Verify the AJ-7 standalone branch sets the category override and the
    attached branch never reaches ``create_job``."""

    @pytest.mark.asyncio
    async def test_standalone_passes_category_override_ready_to_schedule(
        self,
    ) -> None:
        bss = AsyncMock()
        bss.get_bool = AsyncMock(return_value=True)

        new_job = MagicMock()
        new_job.id = uuid4()

        job_service = AsyncMock()
        job_service.create_job = AsyncMock(return_value=new_job)

        audit_service = AsyncMock()
        audit_service.log_action = AsyncMock()

        svc = _make_service(
            job_service=job_service,
            business_setting_service=bss,
            audit_service=audit_service,
        )
        svc.repo.update = AsyncMock()

        est = _make_estimate(customer_id=uuid4(), job_id=None)
        await svc._maybe_auto_create_job(est, "1.2.3.4", "ua")

        job_service.create_job.assert_awaited_once()
        kwargs = job_service.create_job.await_args.kwargs
        assert kwargs.get("category_override") == JobCategory.READY_TO_SCHEDULE

    @pytest.mark.asyncio
    async def test_attached_branch_does_not_call_create_job(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Estimates already attached to a job copy scope into the parent
        job and MUST NOT spawn a fresh Job."""
        bss = AsyncMock()
        bss.get_bool = AsyncMock(return_value=True)

        job_service = AsyncMock()
        job_service.create_job = AsyncMock()

        audit_service = AsyncMock()
        svc = _make_service(
            job_service=job_service,
            business_setting_service=bss,
            audit_service=audit_service,
        )

        est = _make_estimate(customer_id=uuid4(), job_id=uuid4())

        # The attached path delegates to _copy_scope_into_parent_job; stub
        # it so the unit test focuses on the branching, not the SQL.
        copy_mock = AsyncMock()
        monkeypatch.setattr(svc, "_copy_scope_into_parent_job", copy_mock)

        await svc._maybe_auto_create_job(est, "1.2.3.4", "ua")

        copy_mock.assert_awaited_once()
        job_service.create_job.assert_not_called()
