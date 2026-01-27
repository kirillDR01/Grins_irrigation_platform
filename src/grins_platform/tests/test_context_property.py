"""Property tests for context building.

Property 5: Context Completeness
- All required fields are present
- Data is properly formatted

Validates: Requirements 3.1-3.7, 4.1-4.5, 5.1-5.5
"""

from datetime import date, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from hypothesis import (
    given,
    settings,
    strategies as st,
)

from grins_platform.services.ai.context.builder import ContextBuilder


@pytest.mark.asyncio
class TestContextBuilderProperty:
    """Property-based tests for context building."""

    @given(
        days_offset=st.integers(min_value=-365, max_value=365),
    )
    @settings(max_examples=20)
    async def test_scheduling_context_has_required_fields(
        self, days_offset: int,
    ) -> None:
        """Property: Scheduling context always has required fields."""
        mock_session = AsyncMock()
        builder = ContextBuilder(mock_session)

        target_date = date.today() + timedelta(days=days_offset)
        context = await builder.build_scheduling_context(target_date)

        assert "target_date" in context
        assert "day_of_week" in context
        assert "jobs" in context
        assert "staff" in context
        assert "constraints" in context
        assert context["target_date"] == target_date.isoformat()

    @given(
        description=st.text(min_size=1, max_size=500),
    )
    @settings(max_examples=20)
    async def test_categorization_context_has_required_fields(
        self, description: str,
    ) -> None:
        """Property: Categorization context always has required fields."""
        mock_session = AsyncMock()
        builder = ContextBuilder(mock_session)

        context = await builder.build_categorization_context(description)

        assert "job_description" in context
        assert "categories" in context
        assert context["job_description"] == description
        assert "ready_to_schedule" in context["categories"]
        assert "requires_estimate" in context["categories"]

    @given(
        message_type=st.sampled_from(
            ["confirmation", "reminder", "on_the_way", "completion"],
        ),
    )
    @settings(max_examples=10)
    async def test_communication_context_has_required_fields(
        self, message_type: str,
    ) -> None:
        """Property: Communication context always has required fields."""
        mock_session = AsyncMock()
        builder = ContextBuilder(mock_session)

        context = await builder.build_communication_context(
            uuid4(), message_type,
        )

        assert "customer_id" in context
        assert "message_type" in context
        assert "business_info" in context
        assert "templates" in context
        assert context["message_type"] == message_type

    async def test_estimate_context_has_pricing(self) -> None:
        """Test that estimate context includes pricing information."""
        mock_session = AsyncMock()
        builder = ContextBuilder(mock_session)

        context = await builder.build_estimate_context(uuid4())

        assert "pricing" in context
        assert "labor_estimates" in context
        assert "startup_per_zone" in context["pricing"]
        assert "winterization_per_zone" in context["pricing"]

    @given(
        query=st.text(min_size=1, max_size=200),
    )
    @settings(max_examples=20)
    async def test_query_context_has_required_fields(self, query: str) -> None:
        """Property: Query context always has required fields."""
        mock_session = AsyncMock()
        builder = ContextBuilder(mock_session)

        context = await builder.build_query_context(query)

        assert "query" in context
        assert "date_range" in context
        assert "available_data" in context
        assert context["query"] == query
