"""Expense repository for database operations.

CRUD + by-category aggregation + by-job filtering.

Validates: CRM Gap Closure Req 53.2, 53.3
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import func, select

from grins_platform.log_config import LoggerMixin
from grins_platform.models.expense import Expense

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession


class ExpenseRepository(LoggerMixin):
    """Repository for expense database operations.

    Validates: CRM Gap Closure Req 53.2, 53.3
    """

    DOMAIN = "database"

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session."""
        super().__init__()
        self.session = session

    async def create(self, **kwargs: Any) -> Expense:
        """Create a new expense record.

        Args:
            **kwargs: Expense field values

        Returns:
            Created Expense instance
        """
        self.log_started("create")

        expense = Expense(**kwargs)
        self.session.add(expense)
        await self.session.flush()
        await self.session.refresh(expense)

        self.log_completed("create", expense_id=str(expense.id))
        return expense

    async def get_by_id(self, expense_id: UUID) -> Expense | None:
        """Get an expense by ID.

        Args:
            expense_id: Expense UUID

        Returns:
            Expense instance or None if not found
        """
        self.log_started("get_by_id", expense_id=str(expense_id))

        stmt = select(Expense).where(Expense.id == expense_id)
        result = await self.session.execute(stmt)
        expense: Expense | None = result.scalar_one_or_none()

        self.log_completed("get_by_id", found=expense is not None)
        return expense

    async def update(
        self,
        expense_id: UUID,
        **kwargs: Any,
    ) -> Expense | None:
        """Update an expense record.

        Args:
            expense_id: Expense UUID
            **kwargs: Fields to update

        Returns:
            Updated Expense or None if not found
        """
        self.log_started("update", expense_id=str(expense_id))

        expense = await self.get_by_id(expense_id)
        if not expense:
            self.log_completed("update", found=False)
            return None

        for key, value in kwargs.items():
            if hasattr(expense, key):
                setattr(expense, key, value)

        await self.session.flush()
        await self.session.refresh(expense)

        self.log_completed("update", expense_id=str(expense.id))
        return expense

    async def delete(self, expense_id: UUID) -> bool:
        """Delete an expense record.

        Args:
            expense_id: Expense UUID

        Returns:
            True if deleted, False if not found
        """
        self.log_started("delete", expense_id=str(expense_id))

        expense = await self.get_by_id(expense_id)
        if not expense:
            self.log_completed("delete", found=False)
            return False

        await self.session.delete(expense)
        await self.session.flush()

        self.log_completed("delete", expense_id=str(expense_id))
        return True

    async def list_with_filters(
        self,
        page: int = 1,
        page_size: int = 20,
        category: str | None = None,
        job_id: UUID | None = None,
        staff_id: UUID | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> tuple[list[Expense], int]:
        """List expenses with filtering and pagination.

        Args:
            page: Page number (1-based)
            page_size: Items per page
            category: Filter by expense category
            job_id: Filter by job
            staff_id: Filter by staff member
            date_from: Filter from date (inclusive)
            date_to: Filter to date (inclusive)

        Returns:
            Tuple of (list of expenses, total count)
        """
        self.log_started("list_with_filters", page=page, page_size=page_size)

        base_query = select(Expense)
        count_query = select(func.count(Expense.id))

        if category is not None:
            base_query = base_query.where(Expense.category == category)
            count_query = count_query.where(Expense.category == category)

        if job_id is not None:
            base_query = base_query.where(Expense.job_id == job_id)
            count_query = count_query.where(Expense.job_id == job_id)

        if staff_id is not None:
            base_query = base_query.where(Expense.staff_id == staff_id)
            count_query = count_query.where(Expense.staff_id == staff_id)

        if date_from is not None:
            base_query = base_query.where(Expense.expense_date >= date_from)
            count_query = count_query.where(Expense.expense_date >= date_from)

        if date_to is not None:
            base_query = base_query.where(Expense.expense_date <= date_to)
            count_query = count_query.where(Expense.expense_date <= date_to)

        count_result = await self.session.execute(count_query)
        total = count_result.scalar() or 0

        offset = (page - 1) * page_size
        stmt = (
            base_query.order_by(Expense.expense_date.desc())
            .offset(offset)
            .limit(page_size)
        )

        result = await self.session.execute(stmt)
        expenses = list(result.scalars().all())

        self.log_completed("list_with_filters", count=len(expenses), total=total)
        return expenses, total

    async def get_by_job(self, job_id: UUID) -> list[Expense]:
        """Get all expenses for a specific job.

        Args:
            job_id: Job UUID

        Returns:
            List of expenses for the job

        Validates: CRM Gap Closure Req 53.2
        """
        self.log_started("get_by_job", job_id=str(job_id))

        stmt = (
            select(Expense)
            .where(Expense.job_id == job_id)
            .order_by(Expense.expense_date.desc())
        )

        result = await self.session.execute(stmt)
        expenses = list(result.scalars().all())

        self.log_completed("get_by_job", count=len(expenses))
        return expenses

    async def aggregate_by_category(
        self,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[tuple[str, Decimal, int]]:
        """Aggregate expenses by category.

        Args:
            date_from: Filter from date (inclusive)
            date_to: Filter to date (inclusive)

        Returns:
            List of (category, total_amount, count) tuples

        Validates: CRM Gap Closure Req 53.3
        """
        self.log_started("aggregate_by_category")

        stmt = select(
            Expense.category,
            func.sum(Expense.amount).label("total"),
            func.count(Expense.id).label("count"),
        ).group_by(Expense.category)

        if date_from is not None:
            stmt = stmt.where(Expense.expense_date >= date_from)

        if date_to is not None:
            stmt = stmt.where(Expense.expense_date <= date_to)

        stmt = stmt.order_by(func.sum(Expense.amount).desc())

        result = await self.session.execute(stmt)
        rows = [
            (str(row[0]), Decimal(str(row[1])), int(row[2])) for row in result.all()
        ]

        self.log_completed("aggregate_by_category", categories=len(rows))
        return rows

    async def get_total_spend(
        self,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> Decimal:
        """Get total expense spend for a period.

        Args:
            date_from: Filter from date (inclusive)
            date_to: Filter to date (inclusive)

        Returns:
            Total spend amount
        """
        self.log_started("get_total_spend")

        stmt = select(func.coalesce(func.sum(Expense.amount), 0))

        if date_from is not None:
            stmt = stmt.where(Expense.expense_date >= date_from)

        if date_to is not None:
            stmt = stmt.where(Expense.expense_date <= date_to)

        result = await self.session.execute(stmt)
        total = Decimal(str(result.scalar() or 0))

        self.log_completed("get_total_spend", total=str(total))
        return total
