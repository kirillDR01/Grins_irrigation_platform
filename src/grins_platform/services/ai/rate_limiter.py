"""Rate Limit Service for AI requests.

Enforces 100 requests/day limit per user and tracks token/cost usage.

Validates: AI Assistant Requirements 2.1-2.10
"""

from datetime import date
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from grins_platform.log_config import LoggerMixin
from grins_platform.repositories.ai_usage_repository import AIUsageRepository

DAILY_REQUEST_LIMIT = 100


class RateLimitError(Exception):
    """Raised when rate limit is exceeded."""



class RateLimitService(LoggerMixin):
    """Service for rate limiting AI requests."""

    DOMAIN = "business"

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with database session."""
        super().__init__()
        self.usage_repo = AIUsageRepository(session)

    async def check_limit(self, user_id: UUID) -> bool:
        """Check if user is within rate limit.

        Args:
            user_id: The user ID

        Returns:
            True if within limit, False if exceeded

        Raises:
            RateLimitError: If rate limit exceeded
        """
        self.log_started("check_limit", user_id=str(user_id))

        usage = await self.usage_repo.get_daily_usage(user_id, date.today())

        if usage and usage.request_count >= DAILY_REQUEST_LIMIT:
            self.log_rejected(
                "check_limit",
                reason="rate_limit_exceeded",
                current=usage.request_count,
                limit=DAILY_REQUEST_LIMIT,
            )
            msg = f"Daily limit of {DAILY_REQUEST_LIMIT} requests exceeded"
            raise RateLimitError(msg)

        self.log_completed(
            "check_limit",
            current=usage.request_count if usage else 0,
            limit=DAILY_REQUEST_LIMIT,
        )
        return True

    async def record_usage(
        self,
        user_id: UUID,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cost_usd: float = 0.0,
    ) -> int:
        """Record AI usage for a user.

        Args:
            user_id: The user ID
            input_tokens: Number of input tokens used
            output_tokens: Number of output tokens used
            cost_usd: Estimated cost in USD

        Returns:
            Updated request count for today
        """
        self.log_started(
            "record_usage",
            user_id=str(user_id),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

        usage = await self.usage_repo.increment(
            user_id,
            date.today(),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd,
        )

        self.log_completed("record_usage", request_count=usage.request_count)
        return int(usage.request_count)

    async def get_usage(self, user_id: UUID) -> dict[str, int | float]:
        """Get usage statistics for a user.

        Args:
            user_id: The user ID

        Returns:
            Dictionary with usage statistics
        """
        self.log_started("get_usage", user_id=str(user_id))

        usage = await self.usage_repo.get_daily_usage(user_id, date.today())

        if not usage:
            return {
                "request_count": 0,
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "estimated_cost_usd": 0.0,
                "daily_limit": DAILY_REQUEST_LIMIT,
                "remaining_requests": DAILY_REQUEST_LIMIT,
            }

        remaining = max(0, DAILY_REQUEST_LIMIT - usage.request_count)

        self.log_completed("get_usage", request_count=usage.request_count)
        return {
            "request_count": usage.request_count,
            "total_input_tokens": usage.total_input_tokens,
            "total_output_tokens": usage.total_output_tokens,
            "estimated_cost_usd": usage.estimated_cost_usd,
            "daily_limit": DAILY_REQUEST_LIMIT,
            "remaining_requests": remaining,
        }
