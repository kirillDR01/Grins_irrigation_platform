"""
Lead repository for database operations.

This module provides the LeadRepository class for all lead-related
database operations using SQLAlchemy 2.0 async patterns.

Validates: Requirement 4, 5, 8
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    delete as sa_delete,
    func,
    or_,
    select,
    update,
)

from grins_platform.log_config import LoggerMixin
from grins_platform.models.enums import LeadStatus
from grins_platform.models.lead import Lead

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from grins_platform.schemas.lead import LeadListParams


class LeadRepository(LoggerMixin):
    """Repository for lead database operations.

    This class handles all database operations for leads including
    CRUD operations, queries, filtering, and dashboard metric counts.

    Attributes:
        session: AsyncSession for database operations

    Validates: Requirement 4, 5, 8
    """

    DOMAIN = "database"

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session.

        Args:
            session: AsyncSession for database operations
        """
        super().__init__()
        self.session = session

    async def create(self, **kwargs: Any) -> Lead:
        """Create a new lead record.

        Args:
            **kwargs: Lead field values (name, phone, zip_code, situation,
                      email, notes, source_site, status, etc.)

        Returns:
            Created Lead instance

        Validates: Requirement 4.1
        """
        self.log_started("create")

        lead = Lead(**kwargs)

        self.session.add(lead)
        await self.session.flush()
        await self.session.refresh(lead)

        self.log_completed("create", lead_id=str(lead.id))
        return lead

    async def get_by_id(self, lead_id: UUID) -> Lead | None:
        """Get a lead by UUID.

        Args:
            lead_id: UUID of the lead

        Returns:
            Lead instance or None if not found

        Validates: Requirement 5.8
        """
        self.log_started("get_by_id", lead_id=str(lead_id))

        stmt = select(Lead).where(Lead.id == lead_id)

        result = await self.session.execute(stmt)
        lead: Lead | None = result.scalar_one_or_none()

        if lead:
            self.log_completed("get_by_id", lead_id=str(lead_id))
        else:
            self.log_completed("get_by_id", lead_id=str(lead_id), found=False)

        return lead

    async def get_by_phone_and_active_status(self, phone: str) -> Lead | None:
        """Find existing lead by phone with active status.

        Searches for a lead matching the given phone number with status
        in (new, contacted, qualified). Used for duplicate detection.

        Args:
            phone: Normalized phone number (10 digits)

        Returns:
            Lead instance or None if not found

        Validates: Requirement 3.1-3.3
        """
        self.log_started("get_by_phone_and_active_status")

        active_statuses = [
            LeadStatus.NEW.value,
            LeadStatus.CONTACTED.value,
            LeadStatus.QUALIFIED.value,
        ]

        stmt = (
            select(Lead)
            .where(Lead.phone == phone)
            .where(Lead.status.in_(active_statuses))
            .order_by(Lead.created_at.desc())
            .limit(1)
        )

        result = await self.session.execute(stmt)
        lead: Lead | None = result.scalar_one_or_none()

        self.log_completed(
            "get_by_phone_and_active_status",
            found=lead is not None,
        )
        return lead

    async def list_with_filters(
        self,
        params: LeadListParams,
    ) -> tuple[list[Lead], int]:
        """List leads with filtering, search, and pagination.

        Args:
            params: Query parameters for filtering and pagination

        Returns:
            Tuple of (list of leads, total count)

        Validates: Requirement 5.1-5.5
        """
        self.log_started(
            "list_with_filters",
            page=params.page,
            page_size=params.page_size,
        )

        # Base query
        base_query = select(Lead)

        # Apply filters
        if params.status is not None:
            base_query = base_query.where(Lead.status == params.status.value)

        if params.situation is not None:
            base_query = base_query.where(Lead.situation == params.situation.value)

        if params.date_from is not None:
            base_query = base_query.where(Lead.created_at >= params.date_from)

        if params.date_to is not None:
            base_query = base_query.where(Lead.created_at <= params.date_to)

        # Search on name or phone (case-insensitive)
        if params.search:
            search_term = f"%{params.search}%"
            base_query = base_query.where(
                or_(
                    func.lower(Lead.name).like(func.lower(search_term)),
                    Lead.phone.like(search_term),
                ),
            )

        # Get total count
        count_query = select(func.count()).select_from(base_query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        # Apply sorting
        sort_column = getattr(Lead, params.sort_by, Lead.created_at)
        if params.sort_order == "desc":
            sort_column = sort_column.desc()
        else:
            sort_column = sort_column.asc()

        # Apply pagination
        offset = (params.page - 1) * params.page_size
        paginated_query = (
            base_query.order_by(sort_column)
            .offset(offset)
            .limit(params.page_size)
        )

        result = await self.session.execute(paginated_query)
        leads = list(result.scalars().all())

        self.log_completed(
            "list_with_filters",
            count=len(leads),
            total=total,
        )
        return leads, total

    async def update(self, lead_id: UUID, update_data: dict[str, Any]) -> Lead | None:
        """Update lead fields and return updated lead.

        Args:
            lead_id: UUID of the lead to update
            update_data: Dictionary of fields to update

        Returns:
            Updated Lead instance

        Validates: Requirement 5.6-5.7
        """
        self.log_started("update", lead_id=str(lead_id))

        # Set updated_at timestamp
        update_data["updated_at"] = datetime.now(tz=timezone.utc)

        stmt = (
            update(Lead)
            .where(Lead.id == lead_id)
            .values(**update_data)
            .returning(Lead)
        )

        result = await self.session.execute(stmt)
        await self.session.flush()

        lead: Lead | None = result.scalar_one_or_none()

        if lead:
            await self.session.refresh(lead)
            self.log_completed("update", lead_id=str(lead_id))
        else:
            self.log_completed("update", lead_id=str(lead_id), found=False)

        # The caller (service layer) should handle the not-found case
        # by checking before calling update. We return the lead as-is.
        return lead

    async def delete(self, lead_id: UUID) -> None:
        """Hard delete a lead record.

        Args:
            lead_id: UUID of the lead to delete

        Validates: Requirement 5.9
        """
        self.log_started("delete", lead_id=str(lead_id))

        stmt = sa_delete(Lead).where(Lead.id == lead_id)
        await self.session.execute(stmt)
        await self.session.flush()

        self.log_completed("delete", lead_id=str(lead_id))

    async def count_new_today(self) -> int:
        """Count leads created today with status 'new'.

        Used for dashboard metrics (new_leads_today).

        Returns:
            Count of leads submitted today with status 'new'

        Validates: Requirement 8.1
        """
        self.log_started("count_new_today")

        today_start = datetime.combine(
            date.today(),
            datetime.min.time(),
            tzinfo=timezone.utc,
        )

        stmt = (
            select(func.count())
            .select_from(Lead)
            .where(Lead.status == LeadStatus.NEW.value)
            .where(Lead.created_at >= today_start)
        )

        result = await self.session.execute(stmt)
        count = result.scalar() or 0

        self.log_completed("count_new_today", count=count)
        return count

    async def count_uncontacted(self) -> int:
        """Count all leads with status 'new' (all time).

        Used for dashboard metrics (uncontacted_leads).

        Returns:
            Count of all leads with status 'new'

        Validates: Requirement 8.2
        """
        self.log_started("count_uncontacted")

        stmt = (
            select(func.count())
            .select_from(Lead)
            .where(Lead.status == LeadStatus.NEW.value)
        )

        result = await self.session.execute(stmt)
        count = result.scalar() or 0

        self.log_completed("count_uncontacted", count=count)
        return count
