"""Unit tests for EstimateService._correlate_to_sales_entry (Q-A wiring).

Validates: Feature — estimate approval email portal Q-A.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from grins_platform.services.estimate_service import EstimateService


def _make_service(
    *,
    sales_pipeline_service: AsyncMock | None = None,
) -> EstimateService:
    repo = AsyncMock()
    repo.session = AsyncMock()
    return EstimateService(
        estimate_repository=repo,
        portal_base_url="http://localhost:5173",
        sales_pipeline_service=sales_pipeline_service,
    )


def _make_estimate() -> MagicMock:
    est = MagicMock()
    est.id = uuid4()
    return est


@pytest.mark.unit
class TestEstimateCorrelation:
    @pytest.mark.asyncio
    async def test_calls_breadcrumb_on_approved(self) -> None:
        sps = AsyncMock()
        sps.record_estimate_decision_breadcrumb = AsyncMock(return_value=None)
        svc = _make_service(sales_pipeline_service=sps)
        est = _make_estimate()
        await svc._correlate_to_sales_entry(est, "approved")
        sps.record_estimate_decision_breadcrumb.assert_awaited_once()
        args, kwargs = sps.record_estimate_decision_breadcrumb.await_args
        # Either positional or kw — accept both. Decision must be "approved".
        decision = args[2] if len(args) >= 3 else kwargs.get("decision")
        assert decision == "approved"

    @pytest.mark.asyncio
    async def test_forwards_rejection_reason(self) -> None:
        sps = AsyncMock()
        sps.record_estimate_decision_breadcrumb = AsyncMock(return_value=None)
        svc = _make_service(sales_pipeline_service=sps)
        est = _make_estimate()
        await svc._correlate_to_sales_entry(est, "rejected", reason="too high")
        kwargs = sps.record_estimate_decision_breadcrumb.await_args.kwargs
        assert kwargs.get("reason") == "too high"

    @pytest.mark.asyncio
    async def test_swallows_breadcrumb_failure(self) -> None:
        sps = AsyncMock()
        sps.record_estimate_decision_breadcrumb = AsyncMock(
            side_effect=RuntimeError("DB hiccup"),
        )
        svc = _make_service(sales_pipeline_service=sps)
        # Must not raise
        await svc._correlate_to_sales_entry(_make_estimate(), "approved")

    @pytest.mark.asyncio
    async def test_no_op_when_service_not_injected(self) -> None:
        svc = _make_service(sales_pipeline_service=None)
        # Must not raise even with no dep
        await svc._correlate_to_sales_entry(_make_estimate(), "approved")
