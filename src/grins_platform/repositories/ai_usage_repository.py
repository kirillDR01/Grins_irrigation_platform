"""AI Usage Repository for tracking daily AI usage per user.

Validates: AI Assistant Requirements 2.1, 2.7, 2.8
"""

from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from grins_platform.log_config import LoggerMixin
from grins_platform.models.ai_usage import AIUsage


class AIUsageRepository(LoggerMixin):
    """Repository for AI usage tracking operations."""

    DOMAIN = "database"

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session."""
        self.session = session

    async def get_or_create(
        self,
        user_id: UUID,
        usage_date: date,
    ) -> AIUsage:
        """Get or create a usage record for a user and date.

        Args:
            user_id: The user ID
            usage_date: The date for the usage record

        Returns:
            The usage record (existing or newly created)
        """
        self.log_started(
            "get_or_create_usage",
            user_id=str(user_id),
            usage_date=str(usage_date),
        )

        # Try to get existing record
        result = await self.session.execute(
            select(AIUsage).where(
                AIUsage.user_id == user_id,
                AIUsage.usage_date == usage_date,
            ),
        )
        existing_usage: AIUsage | None = result.scalar_one_or_none()

        if existing_usage:
            self.log_completed("get_or_create_usage", created=False)
            return existing_usage

        # Create new record
        new_usage = AIUsage(
            user_id=user_id,
            usage_date=usage_date,
            request_count=0,
            total_input_tokens=0,
            total_output_tokens=0,
            estimated_cost_usd=0.0,
        )

        self.session.add(new_usage)
        await self.session.flush()
        await self.session.refresh(new_usage)

        self.log_completed("get_or_create_usage", created=True)
        return new_usage

    async def increment(
        self,
        user_id: UUID,
        usage_date: date,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cost_usd: float = 0.0,
    ) -> AIUsage:
        """Increment usage counters for a user and date.

        Args:
            user_id: The user ID
            usage_date: The date for the usage record
            input_tokens: Number of input tokens to add
            output_tokens: Number of output tokens to add
            cost_usd: Cost in USD to add

        Returns:
            The updated usage record
        """
        self.log_started(
            "increment_usage",
            user_id=str(user_id),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

        usage = await self.get_or_create(user_id, usage_date)

        usage.request_count += 1
        usage.total_input_tokens += input_tokens
        usage.total_output_tokens += output_tokens
        usage.estimated_cost_usd += cost_usd

        await self.session.flush()
        await self.session.refresh(usage)

        self.log_completed(
            "increment_usage",
            request_count=usage.request_count,
            total_tokens=usage.total_input_tokens + usage.total_output_tokens,
        )
        return usage

    async def get_monthly_cost(
        self,
        user_id: UUID,
        year: int,
        month: int,
    ) -> Decimal:
        """Get total cost for a user in a specific month.

        Args:
            user_id: The user ID
            year: The year
            month: The month (1-12)

        Returns:
            Total cost in USD for the month
        """
        self.log_started(
            "get_monthly_cost",
            user_id=str(user_id),
            year=year,
            month=month,
        )

        # Calculate date range for the month
        start_date = date(year, month, 1)
        end_date = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)

        result = await self.session.execute(
            select(func.sum(AIUsage.estimated_cost_usd)).where(
                AIUsage.user_id == user_id,
                AIUsage.usage_date >= start_date,
                AIUsage.usage_date < end_date,
            ),
        )
        total = result.scalar_one_or_none()

        cost = Decimal(str(total)) if total else Decimal("0.00")
        self.log_completed("get_monthly_cost", cost=float(cost))
        return cost

    async def get_daily_usage(
        self,
        user_id: UUID,
        usage_date: date,
    ) -> AIUsage | None:
        """Get usage record for a specific user and date.

        Args:
            user_id: The user ID
            usage_date: The date

        Returns:
            The usage record or None if not found
        """
        self.log_started(
            "get_daily_usage",
            user_id=str(user_id),
            usage_date=str(usage_date),
        )

        result = await self.session.execute(
            select(AIUsage).where(
                AIUsage.user_id == user_id,
                AIUsage.usage_date == usage_date,
            ),
        )
        usage: AIUsage | None = result.scalar_one_or_none()

        self.log_completed("get_daily_usage", found=usage is not None)
        return usage
