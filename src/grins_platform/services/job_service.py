"""
Job service for business logic operations.

This module provides the JobService class for all job-related
business operations including auto-categorization, status transitions,
and price calculation.

Validates: Requirement 2.1-2.12, 3.1-3.7, 4.1-4.10, 5.1-5.7, 6.1-6.9, 7.1-7.4
"""

from __future__ import annotations

from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import TYPE_CHECKING, ClassVar

from grins_platform.exceptions import (
    CustomerNotFoundError,
    InvalidStatusTransitionError,
    JobNotFoundError,
    PropertyCustomerMismatchError,
    PropertyNotFoundError,
    ServiceOfferingInactiveError,
    ServiceOfferingNotFoundError,
)
from grins_platform.log_config import LoggerMixin
from grins_platform.models.enums import (
    JobCategory,
    JobSource,
    JobStatus,
    PricingModel,
)

if TYPE_CHECKING:
    from uuid import UUID

    from grins_platform.models.job import Job
    from grins_platform.models.job_status_history import JobStatusHistory
    from grins_platform.repositories.customer_repository import CustomerRepository
    from grins_platform.repositories.job_repository import JobRepository
    from grins_platform.repositories.property_repository import PropertyRepository
    from grins_platform.repositories.service_offering_repository import (
        ServiceOfferingRepository,
    )
    from grins_platform.schemas.job import JobCreate, JobStatusUpdate, JobUpdate


class JobService(LoggerMixin):
    """Service for job management operations.

    This class handles all business logic for jobs including
    auto-categorization, status transitions, and price calculation.

    Attributes:
        job_repository: JobRepository for job database operations
        customer_repository: CustomerRepository for customer validation
        property_repository: PropertyRepository for property validation
        service_repository: ServiceOfferingRepository for service validation

    Validates: Requirement 2.1-2.12, 3.1-3.7, 4.1-4.10, 5.1-5.7
    """

    DOMAIN = "job"

    # Valid status transitions
    VALID_TRANSITIONS: ClassVar[dict[JobStatus, set[JobStatus]]] = {
        JobStatus.REQUESTED: {JobStatus.APPROVED, JobStatus.CANCELLED},
        JobStatus.APPROVED: {JobStatus.SCHEDULED, JobStatus.CANCELLED},
        JobStatus.SCHEDULED: {JobStatus.IN_PROGRESS, JobStatus.CANCELLED},
        JobStatus.IN_PROGRESS: {JobStatus.COMPLETED, JobStatus.CANCELLED},
        JobStatus.COMPLETED: {JobStatus.CLOSED},
        JobStatus.CLOSED: set(),  # Terminal state
        JobStatus.CANCELLED: set(),  # Terminal state
    }

    # Job types that are ready to schedule
    READY_TO_SCHEDULE_TYPES: ClassVar[set[str]] = {
        "spring_startup",
        "summer_tuneup",
        "winterization",
        "small_repair",
        "head_replacement",
    }

    def __init__(
        self,
        job_repository: JobRepository,
        customer_repository: CustomerRepository,
        property_repository: PropertyRepository,
        service_repository: ServiceOfferingRepository,
    ) -> None:
        """Initialize service with repositories.

        Args:
            job_repository: JobRepository for job database operations
            customer_repository: CustomerRepository for customer validation
            property_repository: PropertyRepository for property validation
            service_repository: ServiceOfferingRepository for service validation
        """
        super().__init__()
        self.job_repository = job_repository
        self.customer_repository = customer_repository
        self.property_repository = property_repository
        self.service_repository = service_repository

    def _determine_category(self, data: JobCreate) -> JobCategory:
        """Determine job category based on auto-categorization rules.

        Args:
            data: Job creation data

        Returns:
            JobCategory (ready_to_schedule or requires_estimate)

        Validates: Requirement 3.1-3.5
        """
        # Rule 1-2: Seasonal work and small repairs are ready to schedule
        if data.job_type.lower() in self.READY_TO_SCHEDULE_TYPES:
            return JobCategory.READY_TO_SCHEDULE

        # Rule 3: Jobs with approved estimates are ready to schedule
        if data.quoted_amount is not None:
            return JobCategory.READY_TO_SCHEDULE

        # Rule 4: Partner jobs are ready to schedule
        if data.source == JobSource.PARTNER:
            return JobCategory.READY_TO_SCHEDULE

        # Rule 5: Everything else requires estimate
        return JobCategory.REQUIRES_ESTIMATE

    def _get_timestamp_field(self, status: JobStatus) -> str | None:
        """Get the timestamp field name for a status.

        Args:
            status: Job status

        Returns:
            Field name or None if no timestamp field
        """
        timestamp_map = {
            JobStatus.REQUESTED: "requested_at",
            JobStatus.APPROVED: "approved_at",
            JobStatus.SCHEDULED: "scheduled_at",
            JobStatus.IN_PROGRESS: "started_at",
            JobStatus.COMPLETED: "completed_at",
            JobStatus.CLOSED: "closed_at",
        }
        return timestamp_map.get(status)

    async def create_job(self, data: JobCreate) -> Job:
        """Create a new job request with auto-categorization.

        Args:
            data: Job creation data

        Returns:
            Created Job instance

        Raises:
            CustomerNotFoundError: If customer not found
            PropertyNotFoundError: If property not found
            PropertyCustomerMismatchError: If property doesn't belong to customer
            ServiceOfferingNotFoundError: If service not found
            ServiceOfferingInactiveError: If service is inactive

        Validates: Requirement 2.1-2.12, 3.1-3.5
        """
        self.log_started(
            "create_job",
            customer_id=str(data.customer_id),
            job_type=data.job_type,
        )

        # Validate customer exists
        customer = await self.customer_repository.get_by_id(data.customer_id)
        if not customer:
            self.log_rejected("create_job", reason="customer_not_found")
            raise CustomerNotFoundError(data.customer_id)

        # Validate property belongs to customer if provided
        if data.property_id:
            prop = await self.property_repository.get_by_id(data.property_id)
            if not prop:
                self.log_rejected("create_job", reason="property_not_found")
                raise PropertyNotFoundError(data.property_id)
            if prop.customer_id != data.customer_id:
                self.log_rejected("create_job", reason="property_customer_mismatch")
                raise PropertyCustomerMismatchError(data.property_id, data.customer_id)

        # Validate service offering if provided
        if data.service_offering_id:
            service = await self.service_repository.get_by_id(
                data.service_offering_id,
                include_inactive=True,
            )
            if not service:
                self.log_rejected("create_job", reason="service_not_found")
                raise ServiceOfferingNotFoundError(data.service_offering_id)
            if not service.is_active:
                self.log_rejected("create_job", reason="service_inactive")
                raise ServiceOfferingInactiveError(data.service_offering_id)

        # Auto-categorize the job
        category = self._determine_category(data)

        # Create the job
        job = await self.job_repository.create(
            customer_id=data.customer_id,
            property_id=data.property_id,
            service_offering_id=data.service_offering_id,
            job_type=data.job_type,
            category=category.value,
            status=JobStatus.REQUESTED.value,
            description=data.description,
            estimated_duration_minutes=data.estimated_duration_minutes,
            priority_level=data.priority_level,
            weather_sensitive=data.weather_sensitive,
            staffing_required=data.staffing_required,
            equipment_required=data.equipment_required,
            materials_required=data.materials_required,
            quoted_amount=float(data.quoted_amount) if data.quoted_amount else None,
            source=data.source.value if data.source else None,
            source_details=data.source_details,
        )

        # Record initial status in history
        await self.job_repository.add_status_history(
            job_id=job.id,
            new_status=JobStatus.REQUESTED,
            previous_status=None,
        )

        self.log_completed(
            "create_job",
            job_id=str(job.id),
            category=category.value,
        )
        return job

    async def get_job(
        self,
        job_id: UUID,
        include_relationships: bool = False,
    ) -> Job:
        """Get job by ID.

        Args:
            job_id: UUID of the job
            include_relationships: Whether to load related entities

        Returns:
            Job instance

        Raises:
            JobNotFoundError: If job not found

        Validates: Requirement 6.1
        """
        self.log_started("get_job", job_id=str(job_id))

        job = await self.job_repository.get_by_id(
            job_id,
            include_relationships=include_relationships,
        )
        if not job:
            self.log_rejected("get_job", reason="not_found")
            raise JobNotFoundError(job_id)

        self.log_completed("get_job", job_id=str(job_id))
        return job

    async def update_job(self, job_id: UUID, data: JobUpdate) -> Job:
        """Update job details.

        Args:
            job_id: UUID of the job to update
            data: Update data

        Returns:
            Updated Job instance

        Raises:
            JobNotFoundError: If job not found

        Validates: Requirement 3.6, 3.7
        """
        self.log_started("update_job", job_id=str(job_id))

        # Check if job exists
        job = await self.job_repository.get_by_id(job_id)
        if not job:
            self.log_rejected("update_job", reason="not_found")
            raise JobNotFoundError(job_id)

        # Build update dict
        update_data = data.model_dump(exclude_unset=True)

        # Convert enums and decimals
        if update_data.get("category"):
            update_data["category"] = update_data["category"].value
        if update_data.get("source"):
            update_data["source"] = update_data["source"].value
        if "quoted_amount" in update_data and update_data["quoted_amount"] is not None:
            update_data["quoted_amount"] = float(update_data["quoted_amount"])
            # Re-evaluate category if quoted_amount is set (Requirement 3.7)
            if job.category == JobCategory.REQUIRES_ESTIMATE.value:
                update_data["category"] = JobCategory.READY_TO_SCHEDULE.value
        if "final_amount" in update_data and update_data["final_amount"] is not None:
            update_data["final_amount"] = float(update_data["final_amount"])

        updated = await self.job_repository.update(job_id, update_data)

        self.log_completed("update_job", job_id=str(job_id))
        return updated  # type: ignore[return-value]

    async def delete_job(self, job_id: UUID) -> None:
        """Soft delete a job.

        Args:
            job_id: UUID of the job to delete

        Raises:
            JobNotFoundError: If job not found

        Validates: Requirement 10.11
        """
        self.log_started("delete_job", job_id=str(job_id))

        # Check if job exists
        job = await self.job_repository.get_by_id(job_id)
        if not job:
            self.log_rejected("delete_job", reason="not_found")
            raise JobNotFoundError(job_id)

        await self.job_repository.soft_delete(job_id)

        self.log_completed("delete_job", job_id=str(job_id))

    async def update_status(self, job_id: UUID, data: JobStatusUpdate) -> Job:
        """Update job status with validation.

        Args:
            job_id: UUID of the job
            data: Status update data

        Returns:
            Updated Job instance

        Raises:
            JobNotFoundError: If job not found
            InvalidStatusTransitionError: If transition is invalid

        Validates: Requirement 4.1-4.10, 7.1
        """
        self.log_started(
            "update_status",
            job_id=str(job_id),
            new_status=data.status.value,
        )

        # Get current job
        job = await self.job_repository.get_by_id(job_id)
        if not job:
            self.log_rejected("update_status", reason="not_found")
            raise JobNotFoundError(job_id)

        current_status = JobStatus(job.status)

        # Validate transition
        valid_transitions = self.VALID_TRANSITIONS.get(current_status, set())
        if data.status not in valid_transitions:
            self.log_rejected(
                "update_status",
                reason="invalid_transition",
                current=current_status.value,
                requested=data.status.value,
            )
            raise InvalidStatusTransitionError(current_status, data.status)

        # Build update data
        update_data: dict[str, str | datetime] = {"status": data.status.value}

        # Update corresponding timestamp
        timestamp_field = self._get_timestamp_field(data.status)
        if timestamp_field:
            update_data[timestamp_field] = datetime.now()

        # Update the job
        updated = await self.job_repository.update(job_id, update_data)

        # Record status history
        await self.job_repository.add_status_history(
            job_id=job_id,
            new_status=data.status,
            previous_status=current_status,
            notes=data.notes,
        )

        self.log_completed(
            "update_status",
            job_id=str(job_id),
            new_status=data.status.value,
        )
        return updated  # type: ignore[return-value]

    async def get_status_history(self, job_id: UUID) -> list[JobStatusHistory]:
        """Get status history for a job.

        Args:
            job_id: UUID of the job

        Returns:
            List of JobStatusHistory instances

        Raises:
            JobNotFoundError: If job not found

        Validates: Requirement 7.2
        """
        self.log_started("get_status_history", job_id=str(job_id))

        # Check if job exists
        job = await self.job_repository.get_by_id(job_id)
        if not job:
            self.log_rejected("get_status_history", reason="not_found")
            raise JobNotFoundError(job_id)

        history = await self.job_repository.get_status_history(job_id)

        self.log_completed("get_status_history", count=len(history))
        return history

    async def list_jobs(
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
        search: str | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[Job], int]:
        """List jobs with filtering.

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
            search: Search by job type or description
            sort_by: Field to sort by
            sort_order: Sort order (asc/desc)

        Returns:
            Tuple of (list of jobs, total count)

        Validates: Requirement 6.1-6.9
        """
        self.log_started("list_jobs", page=page, page_size=page_size, search=search)

        jobs, total = await self.job_repository.list_with_filters(
            page=page,
            page_size=page_size,
            status=status,
            category=category,
            customer_id=customer_id,
            property_id=property_id,
            service_offering_id=service_offering_id,
            priority_level=priority_level,
            date_from=date_from,
            date_to=date_to,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        self.log_completed("list_jobs", count=len(jobs), total=total)
        return jobs, total

    async def get_ready_to_schedule(
        self,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Job], int]:
        """Get jobs ready to schedule.

        Args:
            page: Page number (1-indexed)
            page_size: Number of items per page

        Returns:
            Tuple of (list of jobs, total count)

        Validates: Requirement 6.7
        """
        return await self.list_jobs(
            page=page,
            page_size=page_size,
            category=JobCategory.READY_TO_SCHEDULE,
        )

    async def get_needs_estimate(
        self,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Job], int]:
        """Get jobs needing estimates.

        Args:
            page: Page number (1-indexed)
            page_size: Number of items per page

        Returns:
            Tuple of (list of jobs, total count)

        Validates: Requirement 6.8
        """
        return await self.list_jobs(
            page=page,
            page_size=page_size,
            category=JobCategory.REQUIRES_ESTIMATE,
        )

    async def get_by_status(
        self,
        status: JobStatus,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Job], int]:
        """Get jobs by status.

        Args:
            status: Job status to filter by
            page: Page number (1-indexed)
            page_size: Number of items per page

        Returns:
            Tuple of (list of jobs, total count)

        Validates: Requirement 6.2
        """
        return await self.list_jobs(
            page=page,
            page_size=page_size,
            status=status,
        )

    async def get_customer_jobs(
        self,
        customer_id: UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Job], int]:
        """Get all jobs for a customer.

        Args:
            customer_id: Customer UUID
            page: Page number (1-indexed)
            page_size: Number of items per page

        Returns:
            Tuple of (list of jobs, total count)

        Validates: Requirement 6.4
        """
        return await self.list_jobs(
            page=page,
            page_size=page_size,
            customer_id=customer_id,
        )

    async def calculate_price(
        self,
        job_id: UUID,
    ) -> dict[str, Decimal | int | str | bool | None]:
        """Calculate price for a job based on service and property.

        Args:
            job_id: UUID of the job

        Returns:
            Price calculation result dict

        Raises:
            JobNotFoundError: If job not found

        Validates: Requirement 5.1-5.7
        """
        self.log_started("calculate_price", job_id=str(job_id))

        # Get job with relationships
        job = await self.job_repository.get_by_id(
            job_id,
            include_relationships=True,
        )
        if not job:
            self.log_rejected("calculate_price", reason="not_found")
            raise JobNotFoundError(job_id)

        result: dict[str, Decimal | int | str | bool | None] = {
            "job_id": str(job_id),
            "service_offering_id": str(job.service_offering_id)
            if job.service_offering_id
            else None,
            "pricing_model": None,
            "base_price": None,
            "zone_count": None,
            "calculated_price": None,
            "requires_manual_quote": True,
        }

        # If no service offering, requires manual quote
        if not job.service_offering_id:
            self.log_completed("calculate_price", requires_manual_quote=True)
            return result

        # Get service offering
        service = await self.service_repository.get_by_id(
            job.service_offering_id,
            include_inactive=True,
        )
        if not service:
            self.log_completed("calculate_price", requires_manual_quote=True)
            return result

        result["pricing_model"] = service.pricing_model
        result["base_price"] = (
            Decimal(str(service.base_price)) if service.base_price else None
        )

        # Get zone count from property if available
        zone_count = None
        if job.property_id:
            prop = await self.property_repository.get_by_id(job.property_id)
            if prop and prop.zone_count:
                zone_count = prop.zone_count
                result["zone_count"] = zone_count

        # Calculate based on pricing model
        pricing_model = PricingModel(service.pricing_model)

        if pricing_model == PricingModel.FLAT:
            # Flat pricing: just base price
            if service.base_price:
                calculated = Decimal(str(service.base_price))
                result["calculated_price"] = calculated.quantize(
                    Decimal("0.01"),
                    rounding=ROUND_HALF_UP,
                )
                result["requires_manual_quote"] = False

        elif pricing_model == PricingModel.ZONE_BASED:
            # Zone-based: base_price + (price_per_zone * zone_count)
            if service.base_price is not None and zone_count:
                base = Decimal(str(service.base_price))
                per_zone = (
                    Decimal(str(service.price_per_zone))
                    if service.price_per_zone
                    else Decimal(0)
                )
                calculated = base + (per_zone * zone_count)
                result["calculated_price"] = calculated.quantize(
                    Decimal("0.01"),
                    rounding=ROUND_HALF_UP,
                )
                result["requires_manual_quote"] = False

        elif pricing_model == PricingModel.HOURLY and service.base_price:
            # Hourly: base_price * estimated_hours
            # For now, just return base price as hourly rate
            result["calculated_price"] = Decimal(str(service.base_price)).quantize(
                Decimal("0.01"),
                rounding=ROUND_HALF_UP,
            )
            result["requires_manual_quote"] = True  # Still needs hours estimate

        # Custom pricing always requires manual quote
        # (pricing_model == PricingModel.CUSTOM is handled by default)

        self.log_completed(
            "calculate_price",
            calculated_price=str(result.get("calculated_price")),
            requires_manual_quote=result["requires_manual_quote"],
        )
        return result
