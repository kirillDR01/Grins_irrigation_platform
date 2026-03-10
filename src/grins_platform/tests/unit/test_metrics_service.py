"""Unit tests for MetricsService.

Tests MRR calculation, ARPA, renewal rate, churn rate,
and past-due amount computation.

Validates: Requirements 20.1, 40.1
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from grins_platform.services.metrics_service import AgreementMetrics, MetricsService


def _make_row(*values: Any) -> MagicMock:
    """Create a mock row that supports index access."""
    row = MagicMock()
    row.__getitem__ = lambda _self, idx: values[idx]
    return row


def _make_scalar_result(value: Any) -> MagicMock:
    """Create a mock result with scalar() returning value."""
    result = MagicMock()
    result.scalar.return_value = value
    return result


def _make_one_result(*values: Any) -> MagicMock:
    """Create a mock result with one() returning a row."""
    result = MagicMock()
    result.one.return_value = _make_row(*values)
    return result


@pytest.mark.unit
class TestMetricsService:
    """Tests for MetricsService.compute_metrics."""

    @pytest.fixture
    def session(self) -> AsyncMock:
        return AsyncMock()

    @pytest.fixture
    def service(self, session: AsyncMock) -> MetricsService:
        return MetricsService(session)

    @pytest.mark.asyncio
    async def test_compute_metrics_with_active_agreements(
        self,
        service: MetricsService,
        session: AsyncMock,
    ) -> None:
        """MRR = sum(annual_price/12) for ACTIVE agreements."""
        # 3 active agreements: $1200, $2400, $3600 annual
        # MRR = (1200+2400+3600)/12 = 600
        # ARPA = 600/3 = 200
        session.execute = AsyncMock(
            side_effect=[
                _make_one_result(3, Decimal("600.00")),  # active count, mrr
                _make_scalar_result(0),  # renewed count
                _make_scalar_result(0),  # not renewed count
                _make_scalar_result(0),  # cancelled count
                _make_scalar_result(3),  # active count for churn
                _make_scalar_result(Decimal(0)),  # past due amount
            ],
        )

        metrics = await service.compute_metrics()

        assert metrics.active_count == 3
        assert metrics.mrr == Decimal("600.00")
        assert metrics.arpa == Decimal("200.00")

    @pytest.mark.asyncio
    async def test_compute_metrics_no_agreements(
        self,
        service: MetricsService,
        session: AsyncMock,
    ) -> None:
        """Zero agreements yields zero for all metrics."""
        session.execute = AsyncMock(
            side_effect=[
                _make_one_result(0, Decimal(0)),  # active count, mrr
                _make_scalar_result(0),  # renewed
                _make_scalar_result(0),  # not renewed
                _make_scalar_result(0),  # cancelled
                _make_scalar_result(0),  # active for churn
                _make_scalar_result(Decimal(0)),  # past due
            ],
        )

        metrics = await service.compute_metrics()

        assert metrics.active_count == 0
        assert metrics.mrr == Decimal("0.00")
        assert metrics.arpa == Decimal("0.00")
        assert metrics.renewal_rate == Decimal("0.00")
        assert metrics.churn_rate == Decimal("0.00")
        assert metrics.past_due_amount == Decimal("0.00")

    @pytest.mark.asyncio
    async def test_mrr_calculation_various_prices(
        self,
        service: MetricsService,
        session: AsyncMock,
    ) -> None:
        """MRR correctly sums annual_price/12 for active agreements."""
        # 2 agreements: $1200 + $600 = $1800 annual, MRR = $150
        session.execute = AsyncMock(
            side_effect=[
                _make_one_result(2, Decimal("150.00")),
                _make_scalar_result(0),
                _make_scalar_result(0),
                _make_scalar_result(0),
                _make_scalar_result(2),
                _make_scalar_result(Decimal(0)),
            ],
        )

        metrics = await service.compute_metrics()

        assert metrics.mrr == Decimal("150.00")
        assert metrics.arpa == Decimal("75.00")

    @pytest.mark.asyncio
    async def test_renewal_rate_calculation(
        self,
        service: MetricsService,
        session: AsyncMock,
    ) -> None:
        """Renewal rate = renewed / (renewed + not_renewed) * 100."""
        # 8 renewed, 2 not renewed = 80%
        session.execute = AsyncMock(
            side_effect=[
                _make_one_result(10, Decimal("1000.00")),
                _make_scalar_result(8),  # renewed
                _make_scalar_result(2),  # not renewed
                _make_scalar_result(0),  # cancelled
                _make_scalar_result(10),  # active
                _make_scalar_result(Decimal(0)),
            ],
        )

        metrics = await service.compute_metrics()

        assert metrics.renewal_rate == Decimal("80.00")

    @pytest.mark.asyncio
    async def test_churn_rate_calculation(
        self,
        service: MetricsService,
        session: AsyncMock,
    ) -> None:
        """Churn rate = cancelled / (active + cancelled) * 100."""
        # 2 cancelled, 8 active = 20%
        session.execute = AsyncMock(
            side_effect=[
                _make_one_result(8, Decimal("800.00")),
                _make_scalar_result(0),
                _make_scalar_result(0),
                _make_scalar_result(2),  # cancelled
                _make_scalar_result(8),  # active
                _make_scalar_result(Decimal(0)),
            ],
        )

        metrics = await service.compute_metrics()

        assert metrics.churn_rate == Decimal("20.00")

    @pytest.mark.asyncio
    async def test_past_due_amount(
        self,
        service: MetricsService,
        session: AsyncMock,
    ) -> None:
        """Past-due amount sums annual_price for PAST_DUE/FAILED agreements."""
        session.execute = AsyncMock(
            side_effect=[
                _make_one_result(5, Decimal("500.00")),
                _make_scalar_result(0),
                _make_scalar_result(0),
                _make_scalar_result(0),
                _make_scalar_result(5),
                _make_scalar_result(Decimal("3600.00")),  # past due amount
            ],
        )

        metrics = await service.compute_metrics()

        assert metrics.past_due_amount == Decimal("3600.00")

    @pytest.mark.asyncio
    async def test_arpa_zero_when_no_active(
        self,
        service: MetricsService,
        session: AsyncMock,
    ) -> None:
        """ARPA is 0 when no active agreements (avoid division by zero)."""
        session.execute = AsyncMock(
            side_effect=[
                _make_one_result(0, Decimal(0)),
                _make_scalar_result(0),
                _make_scalar_result(0),
                _make_scalar_result(0),
                _make_scalar_result(0),
                _make_scalar_result(Decimal(0)),
            ],
        )

        metrics = await service.compute_metrics()

        assert metrics.arpa == Decimal("0.00")

    @pytest.mark.asyncio
    async def test_metrics_returns_dataclass(
        self,
        service: MetricsService,
        session: AsyncMock,
    ) -> None:
        """compute_metrics returns an AgreementMetrics dataclass."""
        session.execute = AsyncMock(
            side_effect=[
                _make_one_result(1, Decimal("100.00")),
                _make_scalar_result(0),
                _make_scalar_result(0),
                _make_scalar_result(0),
                _make_scalar_result(1),
                _make_scalar_result(Decimal(0)),
            ],
        )

        metrics = await service.compute_metrics()

        assert isinstance(metrics, AgreementMetrics)
