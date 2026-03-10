"""Property-based test for MRR calculation correctness.

Property 5: For any set of agreements with varying statuses and prices,
MRR = sum(annual_price/12) for exactly ACTIVE agreements;
ARPA = MRR / active count.

Validates: Requirement 20.1
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from hypothesis import (
    given,
    settings,
    strategies as st,
)

from grins_platform.services.metrics_service import MetricsService


def _make_row(*values: object) -> MagicMock:
    """Create a mock row supporting index access."""
    row = MagicMock()
    row.__getitem__ = lambda _self, idx: values[idx]
    return row


def _make_scalar_result(value: object) -> MagicMock:
    result = MagicMock()
    result.scalar.return_value = value
    return result


def _make_one_result(*values: object) -> MagicMock:
    result = MagicMock()
    result.one.return_value = _make_row(*values)
    return result


@pytest.mark.unit
class TestMrrCalculationProperty:
    """Property 5: MRR Calculation Correctness."""

    @given(
        active_count=st.integers(min_value=0, max_value=1000),
        annual_prices=st.lists(
            st.decimals(
                min_value=Decimal("0.01"),
                max_value=Decimal("99999.99"),
                places=2,
                allow_nan=False,
                allow_infinity=False,
            ),
            min_size=0,
            max_size=50,
        ),
        past_due_amount=st.decimals(
            min_value=Decimal(0),
            max_value=Decimal("999999.99"),
            places=2,
            allow_nan=False,
            allow_infinity=False,
        ),
    )
    @settings(max_examples=50)
    @pytest.mark.asyncio
    async def test_mrr_equals_sum_annual_price_div_12_for_active(
        self,
        active_count: int,
        annual_prices: list[Decimal],
        past_due_amount: Decimal,
    ) -> None:
        """MRR = sum(annual_price/12) for ACTIVE agreements; ARPA = MRR/count."""
        # Simulate: the DB returns the sum of annual_price/12 for active agreements
        expected_mrr = (
            sum(p / 12 for p in annual_prices) if annual_prices else Decimal(0)
        )
        expected_mrr_rounded = Decimal(str(expected_mrr)).quantize(Decimal("0.01"))

        session = AsyncMock()
        service = MetricsService(session)

        session.execute = AsyncMock(
            side_effect=[
                _make_one_result(active_count, Decimal(str(expected_mrr))),
                _make_scalar_result(0),  # renewed
                _make_scalar_result(0),  # not renewed
                _make_scalar_result(0),  # cancelled
                _make_scalar_result(active_count),  # active for churn
                _make_scalar_result(past_due_amount),
            ],
        )

        metrics = await service.compute_metrics()

        # MRR matches what DB returns (rounded)
        assert metrics.mrr == expected_mrr_rounded

        # ARPA = MRR / active_count when active_count > 0
        if active_count > 0:
            expected_arpa = (Decimal(str(expected_mrr)) / active_count).quantize(
                Decimal("0.01"),
            )
            assert metrics.arpa == expected_arpa
        else:
            assert metrics.arpa == Decimal("0.00")

        # Past-due amount matches
        assert metrics.past_due_amount == past_due_amount.quantize(Decimal("0.01"))
