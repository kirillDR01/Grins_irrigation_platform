"""Property tests for rate limit enforcement.

Property 3: Rate Limit Enforcement
- Requests >= 100 are rejected
- Requests < 100 are allowed

Validates: Requirements 2.1, 2.2
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from hypothesis import (
    given,
    settings,
    strategies as st,
)

from grins_platform.services.ai.rate_limiter import (
    DAILY_REQUEST_LIMIT,
    RateLimitError,
    RateLimitService,
)


@pytest.mark.asyncio
class TestRateLimitProperty:
    """Property-based tests for rate limiting."""

    @given(request_count=st.integers(min_value=0, max_value=99))
    @settings(max_examples=20)
    async def test_requests_under_limit_allowed(self, request_count: int) -> None:
        """Property: Requests under limit are always allowed."""
        mock_session = AsyncMock()
        service = RateLimitService(mock_session)

        mock_usage = MagicMock()
        mock_usage.request_count = request_count
        service.usage_repo.get_daily_usage = AsyncMock(return_value=mock_usage)

        result = await service.check_limit(uuid4())
        assert result is True

    @given(request_count=st.integers(min_value=100, max_value=1000))
    @settings(max_examples=20)
    async def test_requests_at_or_over_limit_rejected(
        self, request_count: int,
    ) -> None:
        """Property: Requests at or over limit are always rejected."""
        mock_session = AsyncMock()
        service = RateLimitService(mock_session)

        mock_usage = MagicMock()
        mock_usage.request_count = request_count
        service.usage_repo.get_daily_usage = AsyncMock(return_value=mock_usage)

        with pytest.raises(RateLimitError):
            await service.check_limit(uuid4())

    async def test_no_usage_record_allowed(self) -> None:
        """Test that users with no usage record are allowed."""
        mock_session = AsyncMock()
        service = RateLimitService(mock_session)
        service.usage_repo.get_daily_usage = AsyncMock(return_value=None)

        result = await service.check_limit(uuid4())
        assert result is True

    async def test_exactly_at_limit_rejected(self) -> None:
        """Test that exactly 100 requests is rejected."""
        mock_session = AsyncMock()
        service = RateLimitService(mock_session)

        mock_usage = MagicMock()
        mock_usage.request_count = DAILY_REQUEST_LIMIT
        service.usage_repo.get_daily_usage = AsyncMock(return_value=mock_usage)

        with pytest.raises(RateLimitError):
            await service.check_limit(uuid4())

    async def test_one_under_limit_allowed(self) -> None:
        """Test that 99 requests is allowed."""
        mock_session = AsyncMock()
        service = RateLimitService(mock_session)

        mock_usage = MagicMock()
        mock_usage.request_count = DAILY_REQUEST_LIMIT - 1
        service.usage_repo.get_daily_usage = AsyncMock(return_value=mock_usage)

        result = await service.check_limit(uuid4())
        assert result is True
