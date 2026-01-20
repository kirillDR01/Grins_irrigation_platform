"""
Service offering repository for database operations.

This module provides the ServiceOfferingRepository class for all
service offering-related database operations using SQLAlchemy 2.0 async patterns.

Validates: Requirement 1.1, 1.4-1.6, 1.11
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import func, select, update

from grins_platform.log_config import LoggerMixin
from grins_platform.models.enums import ServiceCategory  # noqa: TC001
from grins_platform.models.service_offering import ServiceOffering

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession


class ServiceOfferingRepository(LoggerMixin):
    """Repository for service offering database operations.

    This class handles all database operations for service offerings including
    CRUD operations and queries.

    Attributes:
        session: AsyncSession for database operations

    Validates: Requirement 1.1, 1.4-1.6, 1.11
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
        name: str,
        category: ServiceCategory,
        pricing_model: str,
        description: str | None = None,
        base_price: float | None = None,
        price_per_zone: float | None = None,
        estimated_duration_minutes: int | None = None,
        duration_per_zone_minutes: int | None = None,
        staffing_required: int = 1,
        equipment_required: list[str] | None = None,
        lien_eligible: bool = False,
        requires_prepay: bool = False,
    ) -> ServiceOffering:
        """Create a new service offering record.

        Args:
            name: Service name
            category: Service category
            pricing_model: Pricing model type
            description: Service description
            base_price: Base price for the service
            price_per_zone: Price per zone (for zone-based pricing)
            estimated_duration_minutes: Estimated duration
            duration_per_zone_minutes: Duration per zone
            staffing_required: Number of staff required
            equipment_required: List of required equipment
            lien_eligible: Whether service is lien eligible
            requires_prepay: Whether prepayment is required

        Returns:
            Created ServiceOffering instance

        Validates: Requirement 1.1
        """
        self.log_started("create", name=name, category=category.value)

        service = ServiceOffering(
            name=name,
            category=category,
            pricing_model=pricing_model,
            description=description,
            base_price=base_price,
            price_per_zone=price_per_zone,
            estimated_duration_minutes=estimated_duration_minutes,
            duration_per_zone_minutes=duration_per_zone_minutes,
            staffing_required=staffing_required,
            equipment_required=equipment_required,
            lien_eligible=lien_eligible,
            requires_prepay=requires_prepay,
        )

        self.session.add(service)
        await self.session.flush()
        await self.session.refresh(service)

        self.log_completed("create", service_id=str(service.id))
        return service

    async def get_by_id(
        self,
        service_id: UUID,
        include_inactive: bool = False,
    ) -> ServiceOffering | None:
        """Get a service offering by ID.

        Args:
            service_id: UUID of the service offering
            include_inactive: Whether to include inactive services

        Returns:
            ServiceOffering instance or None if not found

        Validates: Requirement 1.4
        """
        self.log_started("get_by_id", service_id=str(service_id))

        stmt = select(ServiceOffering).where(ServiceOffering.id == service_id)

        if not include_inactive:
            stmt = stmt.where(ServiceOffering.is_active == True)  # noqa: E712

        result = await self.session.execute(stmt)
        service: ServiceOffering | None = result.scalar_one_or_none()

        if service:
            self.log_completed("get_by_id", service_id=str(service_id))
        else:
            self.log_completed("get_by_id", service_id=str(service_id), found=False)

        return service

    async def update(
        self,
        service_id: UUID,
        data: dict[str, Any],
    ) -> ServiceOffering | None:
        """Update a service offering record.

        Args:
            service_id: UUID of the service to update
            data: Dictionary of fields to update

        Returns:
            Updated ServiceOffering instance or None if not found

        Validates: Requirement 1.5
        """
        self.log_started("update", service_id=str(service_id))

        # Remove None values
        update_data = {k: v for k, v in data.items() if v is not None}

        if not update_data:
            return await self.get_by_id(service_id, include_inactive=True)

        update_data["updated_at"] = datetime.now()

        stmt = (
            update(ServiceOffering)
            .where(ServiceOffering.id == service_id)
            .values(**update_data)
            .returning(ServiceOffering)
        )

        result = await self.session.execute(stmt)
        await self.session.flush()

        service: ServiceOffering | None = result.scalar_one_or_none()

        if service:
            self.log_completed("update", service_id=str(service_id))
        else:
            self.log_completed("update", service_id=str(service_id), found=False)

        return service

    async def deactivate(self, service_id: UUID) -> bool:
        """Deactivate a service offering (soft delete).

        Args:
            service_id: UUID of the service to deactivate

        Returns:
            True if service was deactivated, False if not found

        Validates: Requirement 1.6
        """
        self.log_started("deactivate", service_id=str(service_id))

        stmt = (
            update(ServiceOffering)
            .where(ServiceOffering.id == service_id)
            .where(ServiceOffering.is_active == True)  # noqa: E712
            .values(is_active=False, updated_at=datetime.now())
        )

        result = await self.session.execute(stmt)
        await self.session.flush()

        rowcount: int = getattr(result, "rowcount", 0) or 0
        deactivated: bool = rowcount > 0

        if deactivated:
            self.log_completed("deactivate", service_id=str(service_id))
        else:
            self.log_completed("deactivate", service_id=str(service_id), found=False)

        return deactivated

    async def find_by_category(
        self,
        category: ServiceCategory,
        active_only: bool = True,
    ) -> list[ServiceOffering]:
        """Find services by category.

        Args:
            category: Service category to filter by
            active_only: Whether to return only active services

        Returns:
            List of matching ServiceOffering instances

        Validates: Requirement 1.11
        """
        self.log_started("find_by_category", category=category.value)

        stmt = select(ServiceOffering).where(ServiceOffering.category == category)

        if active_only:
            stmt = stmt.where(ServiceOffering.is_active == True)  # noqa: E712

        stmt = stmt.order_by(ServiceOffering.name)

        result = await self.session.execute(stmt)
        services = list(result.scalars().all())

        self.log_completed("find_by_category", count=len(services))
        return services

    async def list_with_filters(
        self,
        page: int = 1,
        page_size: int = 20,
        category: ServiceCategory | None = None,
        is_active: bool | None = None,
        sort_by: str = "name",
        sort_order: str = "asc",
    ) -> tuple[list[ServiceOffering], int]:
        """List service offerings with filtering and pagination.

        Args:
            page: Page number (1-indexed)
            page_size: Number of items per page
            category: Filter by category
            is_active: Filter by active status
            sort_by: Field to sort by
            sort_order: Sort order (asc/desc)

        Returns:
            Tuple of (list of services, total count)
        """
        self.log_started("list_with_filters", page=page, page_size=page_size)

        # Base query
        base_query = select(ServiceOffering)

        # Apply filters
        if category is not None:
            base_query = base_query.where(ServiceOffering.category == category)

        if is_active is not None:
            base_query = base_query.where(ServiceOffering.is_active == is_active)

        # Get total count
        count_query = select(func.count()).select_from(base_query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        # Apply sorting
        sort_column = getattr(ServiceOffering, sort_by, ServiceOffering.name)
        sort_column = sort_column.desc() if sort_order == "desc" else sort_column.asc()

        # Apply pagination
        offset = (page - 1) * page_size
        paginated_query = (
            base_query.order_by(sort_column).offset(offset).limit(page_size)
        )

        result = await self.session.execute(paginated_query)
        services = list(result.scalars().all())

        self.log_completed("list_with_filters", count=len(services), total=total)
        return services, total
