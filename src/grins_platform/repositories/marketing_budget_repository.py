"""Marketing budget repository for database operations.

CRUD + budget vs actual calculation.

Validates: CRM Gap Closure Req 64.2
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import func, select

from grins_platform.log_config import LoggerMixin
from grins_platform.models.marketing_budget import MarketingBudget

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession


class MarketingBudgetRepository(LoggerMixin):
    """Repository for marketing budget database operations.

    Validates: CRM Gap Closure Req 64.2
    """

    DOMAIN = "database"

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session."""
        super().__init__()
        self.session = session

    async def create(self, **kwargs: Any) -> MarketingBudget:
        """Create a new marketing budget record.

        Args:
            **kwargs: Budget field values

        Returns:
            Created MarketingBudget instance
        """
        self.log_started("create")

        budget = MarketingBudget(**kwargs)
        self.session.add(budget)
        await self.session.flush()
        await self.session.refresh(budget)

        self.log_completed("create", budget_id=str(budget.id))
        return budget

    async def get_by_id(self, budget_id: UUID) -> MarketingBudget | None:
        """Get a marketing budget by ID.

        Args:
            budget_id: Budget UUID

        Returns:
            MarketingBudget or None if not found
        """
        self.log_started("get_by_id", budget_id=str(budget_id))

        stmt = select(MarketingBudget).where(MarketingBudget.id == budget_id)
        result = await self.session.execute(stmt)
        budget: MarketingBudget | None = result.scalar_one_or_none()

        self.log_completed("get_by_id", found=budget is not None)
        return budget

    async def update(
        self,
        budget_id: UUID,
        **kwargs: Any,
    ) -> MarketingBudget | None:
        """Update a marketing budget record.

        Args:
            budget_id: Budget UUID
            **kwargs: Fields to update

        Returns:
            Updated MarketingBudget or None if not found
        """
        self.log_started("update", budget_id=str(budget_id))

        budget = await self.get_by_id(budget_id)
        if not budget:
            self.log_completed("update", found=False)
            return None

        for key, value in kwargs.items():
            if hasattr(budget, key):
                setattr(budget, key, value)

        await self.session.flush()
        await self.session.refresh(budget)

        self.log_completed("update", budget_id=str(budget.id))
        return budget

    async def delete(self, budget_id: UUID) -> bool:
        """Delete a marketing budget record.

        Args:
            budget_id: Budget UUID

        Returns:
            True if deleted, False if not found
        """
        self.log_started("delete", budget_id=str(budget_id))

        budget = await self.get_by_id(budget_id)
        if not budget:
            self.log_completed("delete", found=False)
            return False

        await self.session.delete(budget)
        await self.session.flush()

        self.log_completed("delete", budget_id=str(budget_id))
        return True

    async def list_with_filters(
        self,
        page: int = 1,
        page_size: int = 20,
        channel: str | None = None,
        period_start: date | None = None,
        period_end: date | None = None,
    ) -> tuple[list[MarketingBudget], int]:
        """List marketing budgets with filtering and pagination.

        Args:
            page: Page number (1-based)
            page_size: Items per page
            channel: Filter by marketing channel
            period_start: Filter budgets overlapping from this date
            period_end: Filter budgets overlapping to this date

        Returns:
            Tuple of (list of budgets, total count)
        """
        self.log_started("list_with_filters", page=page, page_size=page_size)

        base_query = select(MarketingBudget)
        count_query = select(func.count(MarketingBudget.id))

        if channel is not None:
            base_query = base_query.where(MarketingBudget.channel == channel)
            count_query = count_query.where(MarketingBudget.channel == channel)

        if period_start is not None:
            base_query = base_query.where(
                MarketingBudget.period_end >= period_start,
            )
            count_query = count_query.where(
                MarketingBudget.period_end >= period_start,
            )

        if period_end is not None:
            base_query = base_query.where(
                MarketingBudget.period_start <= period_end,
            )
            count_query = count_query.where(
                MarketingBudget.period_start <= period_end,
            )

        count_result = await self.session.execute(count_query)
        total = count_result.scalar() or 0

        offset = (page - 1) * page_size
        stmt = (
            base_query.order_by(MarketingBudget.period_start.desc())
            .offset(offset)
            .limit(page_size)
        )

        result = await self.session.execute(stmt)
        budgets = list(result.scalars().all())

        self.log_completed("list_with_filters", count=len(budgets), total=total)
        return budgets, total

    async def get_budget_vs_actual(
        self,
        period_start: date | None = None,
        period_end: date | None = None,
    ) -> list[dict[str, Any]]:
        """Get budget vs actual spend comparison by channel.

        Args:
            period_start: Filter from date
            period_end: Filter to date

        Returns:
            List of dicts with channel, budget_amount, actual_spend, variance

        Validates: CRM Gap Closure Req 64.2
        """
        self.log_started("get_budget_vs_actual")

        stmt = select(
            MarketingBudget.channel,
            func.sum(MarketingBudget.budget_amount).label("total_budget"),
            func.sum(MarketingBudget.actual_spend).label("total_actual"),
        ).group_by(MarketingBudget.channel)

        if period_start is not None:
            stmt = stmt.where(MarketingBudget.period_end >= period_start)

        if period_end is not None:
            stmt = stmt.where(MarketingBudget.period_start <= period_end)

        stmt = stmt.order_by(MarketingBudget.channel.asc())

        result = await self.session.execute(stmt)
        rows: list[dict[str, Any]] = []
        for row in result.all():
            budget_amount = Decimal(str(row[1]))
            actual_spend = Decimal(str(row[2]))
            rows.append(
                {
                    "channel": str(row[0]),
                    "budget_amount": budget_amount,
                    "actual_spend": actual_spend,
                    "variance": budget_amount - actual_spend,
                },
            )

        self.log_completed("get_budget_vs_actual", channels=len(rows))
        return rows

    async def get_total_budget(
        self,
        period_start: date | None = None,
        period_end: date | None = None,
    ) -> Decimal:
        """Get total budget amount for a period.

        Args:
            period_start: Filter from date
            period_end: Filter to date

        Returns:
            Total budget amount
        """
        self.log_started("get_total_budget")

        stmt = select(func.coalesce(func.sum(MarketingBudget.budget_amount), 0))

        if period_start is not None:
            stmt = stmt.where(MarketingBudget.period_end >= period_start)

        if period_end is not None:
            stmt = stmt.where(MarketingBudget.period_start <= period_end)

        result = await self.session.execute(stmt)
        total = Decimal(str(result.scalar() or 0))

        self.log_completed("get_total_budget", total=str(total))
        return total
