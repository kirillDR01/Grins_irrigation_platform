"""Property test: Lead Metrics by Source Accuracy.

Property 21: For any set of leads in a date range, sum of all group counts
= total leads in range.

Validates: Requirements 61.3
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from hypothesis import (
    given,
    settings,
    strategies as st,
)

from grins_platform.models.enums import LeadSourceExtended
from grins_platform.services.lead_service import LeadService

ALL_SOURCES = [s.value for s in LeadSourceExtended]


@pytest.mark.unit
class TestLeadMetricsBySourceAccuracyProperty:
    """Property 21: Lead Metrics by Source Accuracy."""

    @given(
        source_counts=st.lists(
            st.tuples(
                st.sampled_from(ALL_SOURCES),
                st.integers(min_value=0, max_value=500),
            ),
            min_size=0,
            max_size=len(ALL_SOURCES),
            unique_by=lambda x: x[0],
        ),
    )
    @settings(max_examples=50)
    @pytest.mark.asyncio
    async def test_sum_of_group_counts_equals_total(
        self,
        source_counts: list[tuple[str, int]],
    ) -> None:
        """Sum of all group counts must equal total leads in range."""
        # Filter out zero-count sources (repo wouldn't return them)
        nonzero = [(src, cnt) for src, cnt in source_counts if cnt > 0]

        mock_repo = AsyncMock()
        mock_repo.count_by_source = AsyncMock(return_value=nonzero)

        service = LeadService(
            lead_repository=mock_repo,
            customer_service=MagicMock(),
            job_service=MagicMock(),
            staff_repository=MagicMock(),
        )

        result = await service.get_metrics_by_source()

        expected_total = sum(cnt for _, cnt in nonzero)
        assert result.total == expected_total
        assert sum(item.count for item in result.items) == result.total
        assert len(result.items) == len(nonzero)

    @given(
        n_sources=st.integers(min_value=1, max_value=len(ALL_SOURCES)),
    )
    @settings(max_examples=30)
    @pytest.mark.asyncio
    async def test_each_source_appears_once(
        self,
        n_sources: int,
    ) -> None:
        """Each source appears at most once in the response."""
        sources = ALL_SOURCES[:n_sources]
        rows = [(src, 5) for src in sources]

        mock_repo = AsyncMock()
        mock_repo.count_by_source = AsyncMock(return_value=rows)

        service = LeadService(
            lead_repository=mock_repo,
            customer_service=MagicMock(),
            job_service=MagicMock(),
            staff_repository=MagicMock(),
        )

        result = await service.get_metrics_by_source()

        returned_sources = [item.lead_source for item in result.items]
        assert len(returned_sources) == len(set(returned_sources))

    @given(
        days_back=st.integers(min_value=1, max_value=365),
    )
    @settings(max_examples=20)
    @pytest.mark.asyncio
    async def test_date_range_defaults_and_passthrough(
        self,
        days_back: int,
    ) -> None:
        """Custom date range is passed to repository correctly."""
        mock_repo = AsyncMock()
        mock_repo.count_by_source = AsyncMock(return_value=[])

        service = LeadService(
            lead_repository=mock_repo,
            customer_service=MagicMock(),
            job_service=MagicMock(),
            staff_repository=MagicMock(),
        )

        now = datetime.now(tz=timezone.utc)
        date_from = now - timedelta(days=days_back)

        result = await service.get_metrics_by_source(
            date_from=date_from,
            date_to=now,
        )

        # Verify the repo was called with the provided dates
        mock_repo.count_by_source.assert_awaited_once_with(date_from, now)
        assert result.date_from == date_from
        assert result.date_to == now
        assert result.total == 0
        assert result.items == []

    @pytest.mark.asyncio
    async def test_default_date_range_is_trailing_30_days(self) -> None:
        """When no dates provided, defaults to trailing 30 days."""
        mock_repo = AsyncMock()
        mock_repo.count_by_source = AsyncMock(return_value=[])

        service = LeadService(
            lead_repository=mock_repo,
            customer_service=MagicMock(),
            job_service=MagicMock(),
            staff_repository=MagicMock(),
        )

        before = datetime.now(tz=timezone.utc)
        result = await service.get_metrics_by_source()
        after = datetime.now(tz=timezone.utc)

        # date_to should be ~now
        assert before <= result.date_to <= after
        # date_from should be ~30 days before date_to
        delta = result.date_to - result.date_from
        assert 29 <= delta.days <= 31
