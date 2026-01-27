"""Property tests for categorization.

Property 9: Confidence Threshold Routing

Validates: Requirements 5.5, 5.6
"""

from unittest.mock import AsyncMock

import pytest
from hypothesis import (
    given,
    settings,
    strategies as st,
)

from grins_platform.services.ai.tools.categorization import (
    CONFIDENCE_THRESHOLD,
    CategorizationTools,
)


@pytest.mark.asyncio
class TestCategorizationProperty:
    """Property-based tests for categorization."""

    @given(confidence=st.integers(min_value=CONFIDENCE_THRESHOLD, max_value=100))
    @settings(max_examples=20)
    def test_high_confidence_auto_categorizes(self, confidence: int) -> None:
        """Property: Confidence >= threshold routes to auto-categorize."""
        mock_session = AsyncMock()
        tools = CategorizationTools(mock_session)

        result = tools.route_by_confidence(confidence)

        assert result == "auto_categorize"

    @given(confidence=st.integers(min_value=0, max_value=CONFIDENCE_THRESHOLD - 1))
    @settings(max_examples=20)
    def test_low_confidence_needs_review(self, confidence: int) -> None:
        """Property: Confidence < threshold routes to human review."""
        mock_session = AsyncMock()
        tools = CategorizationTools(mock_session)

        result = tools.route_by_confidence(confidence)

        assert result == "human_review"

    async def test_urgent_keywords_high_confidence(self) -> None:
        """Test that urgent keywords result in high confidence."""
        mock_session = AsyncMock()
        tools = CategorizationTools(mock_session)

        result = await tools.categorize_job("Emergency! Water flooding everywhere!")

        assert result["category"] == "urgent"
        assert result["confidence"] >= CONFIDENCE_THRESHOLD
        assert result["needs_review"] is False

    async def test_standard_service_high_confidence(self) -> None:
        """Test that standard services result in high confidence."""
        mock_session = AsyncMock()
        tools = CategorizationTools(mock_session)

        result = await tools.categorize_job(
            "Need spring startup for my irrigation system",
        )

        assert result["category"] == "ready_to_schedule"
        assert result["confidence"] >= CONFIDENCE_THRESHOLD
        assert result["needs_review"] is False

    async def test_vague_description_low_confidence(self) -> None:
        """Test that vague descriptions result in low confidence."""
        mock_session = AsyncMock()
        tools = CategorizationTools(mock_session)

        result = await tools.categorize_job("Something is wrong with my yard")

        assert result["confidence"] < CONFIDENCE_THRESHOLD
        assert result["needs_review"] is True

    async def test_suggests_appropriate_services(self) -> None:
        """Test that appropriate services are suggested."""
        mock_session = AsyncMock()
        tools = CategorizationTools(mock_session)

        result = await tools.categorize_job("Broken sprinkler head in front yard")

        assert "head_replacement" in result["suggested_services"]
