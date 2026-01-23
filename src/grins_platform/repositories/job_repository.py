"""
Job repository for database operations.

This module provides the JobRepository class for all job-related
database operations using SQLAlchemy 2.0 async patterns.

Validates: Requirement 2.1-2.12, 6.1-6.9, 7.1-7.4
"""

from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import func, select, update
from sqlalchemy.orm import selectinload

from grins_platform.log_config import LoggerMixin
from grins_platform.models.enums import JobCategory, JobStatus  # noqa: TC001
from grins_platform.models.job import Job
from grins_platform.models.job_status_history import JobStatusHistory

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession


class JobRepository(LoggerMixin):
    """Repository for job database operations.

    This class handles all database operations for jobs including
    CRUD operations, queries, and status history management.

    Attributes:
        session: AsyncSession for database operations

    Validates: Requirement 2.1-2.12, 6.1-6.9, 7.1-7.4
    """

    DOMAIN = "database"

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session.

        Args:
            session: AsyncSession for database operations
        """
        super().__init__()
        self.session = session

    async def create(
        self,
        customer_id: UUID,
        job_type: str,
        category: str,
        status: str = "requested",
        property_id: UUID | None = None,
        service_offering_id: UUID | None = None,
        description: str | None = None,
        estimated_duration_minutes: int | None = None,
        priority_level: int = 0,
        weather_sensitive: bool = False,
        staffing_required: int = 1,
        equipment_required: list[str] | None = None,
        materials_required: list[str] | None = None,
        quoted_amount: float | None = None,
        source: str | None = None,
        source_details: dict[str, Any] | None = None,
    ) -> Job:
        """Create a new job record.

        Args:
            customer_id: Customer UUID
            job_type: Type of job
            category: Job category (ready_to_schedule/requires_estimate)
            status: Initial job status
            property_id: Property UUID (optional)
            service_offering_id: Service offering UUID (optional)
            description: Job description
            estimated_duration_minutes: Estimated duration
            priority_level: Priority (0=normal, 1=high, 2=urgent)
            weather_sensitive: Whether job is weather sensitive
            staffing_required: Number of staff required
            equipment_required: List of required equipment
            materials_required: List of required materials
            quoted_amount: Quoted price
            source: Lead source
            source_details: Additional source details

        Returns:
            Created Job instance

        Validates: Requirement 2.1
        """
        self.log_started("create", customer_id=str(customer_id), job_type=job_type)

        job = Job(
            customer_id=customer_id,
            property_id=property_id,
            service_offering_id=service_offering_id,
            job_type=job_type,
            category=category,
            status=status,
            description=description,
            estimated_duration_minutes=estimated_duration_minutes,
            priority_level=priority_level,
            weather_sensitive=weather_sensitive,
            staffing_required=staffing_required,
            equipment_required=equipment_required,
            materials_required=materials_required,
            quoted_amount=quoted_amount,
            source=source,
            source_details=source_details,
            requested_at=datetime.now(),
        )

        self.session.add(job)
        await self.session.flush()
        await self.session.refresh(job)

        self.log_completed("create", job_id=str(job.id))
        return job

    async def get_by_id(
        self,
        job_id: UUID,
        include_deleted: bool = False,
        include_relationships: bool = False,
    ) -> Job | None:
        """Get a job by ID.

        Args:
            job_id: UUID of the job
            include_deleted: Whether to include soft-deleted jobs
            include_relationships: Whether to load related entities

        Returns:
            Job instance or None if not found

        Validates: Requirement 6.1
        """
        self.log_started("get_by_id", job_id=str(job_id))

        stmt = select(Job).where(Job.id == job_id)

        if include_relationships:
            stmt = stmt.options(
                selectinload(Job.customer),
                selectinload(Job.job_property),
                selectinload(Job.service_offering),
                selectinload(Job.status_history),
            )

        if not include_deleted:
            stmt = stmt.where(Job.is_deleted == False)  # noqa: E712

        result = await self.session.execute(stmt)
        job: Job | None = result.scalar_one_or_none()

        if job:
            self.log_completed("get_by_id", job_id=str(job_id))
        else:
            self.log_completed("get_by_id", job_id=str(job_id), found=False)

        return job

    async def update(
        self,
        job_id: UUID,
        data: dict[str, Any],
    ) -> Job | None:
        """Update a job record.

        Args:
            job_id: UUID of the job to update
            data: Dictionary of fields to update

        Returns:
            Updated Job instance or None if not found
        """
        self.log_started("update", job_id=str(job_id))

        # Remove None values
        update_data = {k: v for k, v in data.items() if v is not None}

        if not update_data:
            return await self.get_by_id(job_id)

        update_data["updated_at"] = datetime.now()

        stmt = (
            update(Job)
            .where(Job.id == job_id)
            .where(Job.is_deleted == False)  # noqa: E712
            .values(**update_data)
            .returning(Job)
        )

        result = await self.session.execute(stmt)
        await self.session.flush()

        job: Job | None = result.scalar_one_or_none()

        if job:
            self.log_completed("update", job_id=str(job_id))
        else:
            self.log_completed("update", job_id=str(job_id), found=False)

        return job

    async def soft_delete(self, job_id: UUID) -> bool:
        """Soft delete a job.

        Args:
            job_id: UUID of the job to delete

        Returns:
            True if job was deleted, False if not found

        Validates: Requirement 10.11
        """
        self.log_started("soft_delete", job_id=str(job_id))

        stmt = (
            update(Job)
            .where(Job.id == job_id)
            .where(Job.is_deleted == False)  # noqa: E712
            .values(
                is_deleted=True,
                deleted_at=datetime.now(),
                updated_at=datetime.now(),
            )
        )

        result = await self.session.execute(stmt)
        await self.session.flush()

        rowcount: int = getattr(result, "rowcount", 0) or 0
        deleted: bool = rowcount > 0

        if deleted:
            self.log_completed("soft_delete", job_id=str(job_id))
        else:
            self.log_completed("soft_delete", job_id=str(job_id), found=False)

        return deleted

    async def find_by_status(
        self,
        status: JobStatus,
        include_deleted: bool = False,
    ) -> list[Job]:
        """Find jobs by status.

        Args:
            status: Job status to filter by
            include_deleted: Whether to include soft-deleted jobs

        Returns:
            List of matching Job instances

        Validates: Requirement 6.2
        """
        self.log_started("find_by_status", status=status.value)

        stmt = select(Job).where(Job.status == status.value)

        if not include_deleted:
            stmt = stmt.where(Job.is_deleted == False)  # noqa: E712

        stmt = stmt.order_by(Job.created_at.desc())

        result = await self.session.execute(stmt)
        jobs = list(result.scalars().all())

        self.log_completed("find_by_status", count=len(jobs))
        return jobs

    async def find_by_category(
        self,
        category: JobCategory,
        include_deleted: bool = False,
    ) -> list[Job]:
        """Find jobs by category.

        Args:
            category: Job category to filter by
            include_deleted: Whether to include soft-deleted jobs

        Returns:
            List of matching Job instances

        Validates: Requirement 6.7, 6.8
        """
        self.log_started("find_by_category", category=category.value)

        stmt = select(Job).where(Job.category == category.value)

        if not include_deleted:
            stmt = stmt.where(Job.is_deleted == False)  # noqa: E712

        stmt = stmt.order_by(Job.created_at.desc())

        result = await self.session.execute(stmt)
        jobs = list(result.scalars().all())

        self.log_completed("find_by_category", count=len(jobs))
        return jobs

    async def find_by_customer(
        self,
        customer_id: UUID,
        include_deleted: bool = False,
    ) -> list[Job]:
        """Find jobs by customer.

        Args:
            customer_id: Customer UUID to filter by
            include_deleted: Whether to include soft-deleted jobs

        Returns:
            List of matching Job instances

        Validates: Requirement 6.4
        """
        self.log_started("find_by_customer", customer_id=str(customer_id))

        stmt = select(Job).where(Job.customer_id == customer_id)

        if not include_deleted:
            stmt = stmt.where(Job.is_deleted == False)  # noqa: E712

        stmt = stmt.order_by(Job.created_at.desc())

        result = await self.session.execute(stmt)
        jobs = list(result.scalars().all())

        self.log_completed("find_by_customer", count=len(jobs))
        return jobs

    async def list_with_filters(
        self,
        page: int = 1,
        page_size: int = 20,
        status: JobStatus | None = None,
        category: JobCategory | None = None,
        customer_id: UUID | None = None,
        property_id: UUID | None = None,
        service_offering_id: UUID | None = None,
        priority_level: int | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        include_deleted: bool = False,
    ) -> tuple[list[Job], int]:
        """List jobs with filtering and pagination.

        Args:
            page: Page number (1-indexed)
            page_size: Number of items per page
            status: Filter by status
            category: Filter by category
            customer_id: Filter by customer
            property_id: Filter by property
            service_offering_id: Filter by service offering
            priority_level: Filter by priority
            date_from: Filter by created_at >= date_from
            date_to: Filter by created_at <= date_to
            sort_by: Field to sort by
            sort_order: Sort order (asc/desc)
            include_deleted: Whether to include soft-deleted jobs

        Returns:
            Tuple of (list of jobs, total count)

        Validates: Requirement 6.1-6.9
        """
        self.log_started("list_with_filters", page=page, page_size=page_size)

        # Base query
        base_query = select(Job)

        if not include_deleted:
            base_query = base_query.where(Job.is_deleted == False)  # noqa: E712

        # Apply filters
        if status is not None:
            base_query = base_query.where(Job.status == status.value)

        if category is not None:
            base_query = base_query.where(Job.category == category.value)

        if customer_id is not None:
            base_query = base_query.where(Job.customer_id == customer_id)

        if property_id is not None:
            base_query = base_query.where(Job.property_id == property_id)

        if service_offering_id is not None:
            base_query = base_query.where(
                Job.service_offering_id == service_offering_id,
            )

        if priority_level is not None:
            base_query = base_query.where(Job.priority_level == priority_level)

        if date_from is not None:
            base_query = base_query.where(Job.created_at >= date_from)

        if date_to is not None:
            base_query = base_query.where(Job.created_at <= date_to)

        # Get total count
        count_query = select(func.count()).select_from(base_query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        # Apply sorting
        sort_column = getattr(Job, sort_by, Job.created_at)
        sort_column = sort_column.desc() if sort_order == "desc" else sort_column.asc()

        # Apply pagination
        offset = (page - 1) * page_size
        paginated_query = (
            base_query.order_by(sort_column).offset(offset).limit(page_size)
        )

        result = await self.session.execute(paginated_query)
        jobs = list(result.scalars().all())

        self.log_completed("list_with_filters", count=len(jobs), total=total)
        return jobs, total

    async def add_status_history(
        self,
        job_id: UUID,
        new_status: JobStatus,
        previous_status: JobStatus | None = None,
        changed_by: str | None = None,
        notes: str | None = None,
    ) -> JobStatusHistory:
        """Add a status history entry for a job.

        Args:
            job_id: UUID of the job
            new_status: New status
            previous_status: Previous status (optional)
            changed_by: User who made the change
            notes: Notes about the change

        Returns:
            Created JobStatusHistory instance

        Validates: Requirement 7.1
        """
        self.log_started(
            "add_status_history",
            job_id=str(job_id),
            new_status=new_status.value,
        )

        history = JobStatusHistory(
            job_id=job_id,
            previous_status=previous_status.value if previous_status else None,
            new_status=new_status.value,
            changed_by=changed_by,
            notes=notes,
        )

        self.session.add(history)
        await self.session.flush()
        await self.session.refresh(history)

        self.log_completed("add_status_history", history_id=str(history.id))
        return history

    async def get_status_history(self, job_id: UUID) -> list[JobStatusHistory]:
        """Get status history for a job.

        Args:
            job_id: UUID of the job

        Returns:
            List of JobStatusHistory instances in chronological order

        Validates: Requirement 7.2
        """
        self.log_started("get_status_history", job_id=str(job_id))

        stmt = (
            select(JobStatusHistory)
            .where(JobStatusHistory.job_id == job_id)
            .order_by(JobStatusHistory.changed_at.asc())
        )

        result = await self.session.execute(stmt)
        history = list(result.scalars().all())

        self.log_completed("get_status_history", count=len(history))
        return history

    async def count_by_status(self) -> dict[str, int]:
        """Count jobs grouped by status.

        Returns:
            Dictionary mapping status string to count

        Validates: Admin Dashboard Requirement 1.6
        """
        self.log_started("count_by_status")

        stmt = (
            select(Job.status, func.count())
            .where(Job.is_deleted == False)  # noqa: E712
            .group_by(Job.status)
        )

        result = await self.session.execute(stmt)
        rows = result.all()

        # Convert to dict with proper types
        counts: dict[str, int] = {}
        for row in rows:
            status_val: str = str(row[0]) if row[0] else ""
            count_val: int = int(row[1]) if row[1] else 0
            if status_val:
                counts[status_val] = count_val

        self.log_completed("count_by_status", statuses=len(counts))
        return counts

    async def count_by_day(
        self,
        start_date: date,
        end_date: date,
    ) -> dict[date, int]:
        """Count jobs created per day within a date range.

        Args:
            start_date: Start of the date range
            end_date: End of the date range

        Returns:
            Dictionary mapping date to count of jobs created

        Validates: Admin Dashboard Requirement 1.6
        """
        self.log_started(
            "count_by_day",
            start_date=str(start_date),
            end_date=str(end_date),
        )

        # Cast created_at to date for grouping
        stmt = (
            select(
                func.date(Job.created_at).label("job_date"),
                func.count().label("count"),
            )
            .where(Job.is_deleted == False)  # noqa: E712
            .where(func.date(Job.created_at) >= start_date)
            .where(func.date(Job.created_at) <= end_date)
            .group_by(func.date(Job.created_at))
            .order_by(func.date(Job.created_at))
        )

        result = await self.session.execute(stmt)
        rows = result.all()

        counts: dict[date, int] = {
            job_date: count
            for job_date, count in rows
            if isinstance(job_date, date)
        }

        self.log_completed("count_by_day", days=len(counts))
        return counts

    async def count_by_category(
        self,
        start_date: date,
        end_date: date,
    ) -> dict[str, int]:
        """Count jobs by category within a date range.

        Args:
            start_date: Start of the date range
            end_date: End of the date range

        Returns:
            Dictionary mapping category string to count

        Validates: Admin Dashboard Requirement 1.6
        """
        self.log_started(
            "count_by_category",
            start_date=str(start_date),
            end_date=str(end_date),
        )

        stmt = (
            select(Job.category, func.count())
            .where(Job.is_deleted == False)  # noqa: E712
            .where(func.date(Job.created_at) >= start_date)
            .where(func.date(Job.created_at) <= end_date)
            .group_by(Job.category)
        )

        result = await self.session.execute(stmt)
        rows = result.all()

        counts: dict[str, int] = {
            category: count for category, count in rows if category
        }

        self.log_completed("count_by_category", categories=len(counts))
        return counts

    async def count_by_source(
        self,
        start_date: date,
        end_date: date,
    ) -> dict[str, int]:
        """Count jobs by source within a date range.

        Args:
            start_date: Start of the date range
            end_date: End of the date range

        Returns:
            Dictionary mapping source string to count

        Validates: Admin Dashboard Requirement 1.6
        """
        self.log_started(
            "count_by_source",
            start_date=str(start_date),
            end_date=str(end_date),
        )

        stmt = (
            select(Job.source, func.count())
            .where(Job.is_deleted == False)  # noqa: E712
            .where(func.date(Job.created_at) >= start_date)
            .where(func.date(Job.created_at) <= end_date)
            .group_by(Job.source)
        )

        result = await self.session.execute(stmt)
        rows = result.all()

        counts: dict[str, int] = {}
        for source, count in rows:
            source_key = source if source else "unknown"
            counts[source_key] = count

        self.log_completed("count_by_source", sources=len(counts))
        return counts
