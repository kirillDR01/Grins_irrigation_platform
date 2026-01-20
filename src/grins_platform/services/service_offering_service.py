"""
Service offering service for business logic operations.

This module provides the ServiceOfferingService class for all service
offering-related business operations.

Validates: Requirement 1.1-1.13, 11.1, 11.4-11.9
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from grins_platform.exceptions import ServiceOfferingNotFoundError
from grins_platform.log_config import LoggerMixin
from grins_platform.models.enums import ServiceCategory  # noqa: TC001

if TYPE_CHECKING:
    from uuid import UUID

    from grins_platform.models.service_offering import ServiceOffering
    from grins_platform.repositories.service_offering_repository import (
        ServiceOfferingRepository,
    )
    from grins_platform.schemas.service_offering import (
        ServiceOfferingCreate,
        ServiceOfferingUpdate,
    )


class ServiceOfferingService(LoggerMixin):
    """Service for service offering management operations.

    This class handles all business logic for service offerings including
    CRUD operations and category filtering.

    Attributes:
        repository: ServiceOfferingRepository for database operations

    Validates: Requirement 1.1-1.13, 11.1, 11.4-11.9
    """

    DOMAIN = "service"

    def __init__(self, repository: ServiceOfferingRepository) -> None:
        """Initialize service with repository.

        Args:
            repository: ServiceOfferingRepository for database operations
        """
        super().__init__()
        self.repository = repository

    async def create_service(
        self,
        data: ServiceOfferingCreate,
    ) -> ServiceOffering:
        """Create a new service offering.

        Args:
            data: Service offering creation data

        Returns:
            Created ServiceOffering instance

        Validates: Requirement 1.1
        """
        self.log_started("create_service", name=data.name, category=data.category.value)

        service = await self.repository.create(
            name=data.name,
            category=data.category,
            pricing_model=data.pricing_model.value,
            description=data.description,
            base_price=float(data.base_price) if data.base_price else None,
            price_per_zone=float(data.price_per_zone) if data.price_per_zone else None,
            estimated_duration_minutes=data.estimated_duration_minutes,
            duration_per_zone_minutes=data.duration_per_zone_minutes,
            staffing_required=data.staffing_required,
            equipment_required=data.equipment_required,
            lien_eligible=data.lien_eligible,
            requires_prepay=data.requires_prepay,
        )

        self.log_completed("create_service", service_id=str(service.id))
        return service

    async def get_service(self, service_id: UUID) -> ServiceOffering:
        """Get service offering by ID.

        Args:
            service_id: UUID of the service offering

        Returns:
            ServiceOffering instance

        Raises:
            ServiceOfferingNotFoundError: If service not found

        Validates: Requirement 1.4
        """
        self.log_started("get_service", service_id=str(service_id))

        service = await self.repository.get_by_id(service_id, include_inactive=True)
        if not service:
            self.log_rejected("get_service", reason="not_found")
            raise ServiceOfferingNotFoundError(service_id)

        self.log_completed("get_service", service_id=str(service_id))
        return service

    async def update_service(
        self,
        service_id: UUID,
        data: ServiceOfferingUpdate,
    ) -> ServiceOffering:
        """Update service offering.

        Args:
            service_id: UUID of the service to update
            data: Update data

        Returns:
            Updated ServiceOffering instance

        Raises:
            ServiceOfferingNotFoundError: If service not found

        Validates: Requirement 1.5
        """
        self.log_started("update_service", service_id=str(service_id))

        # Check if service exists
        service = await self.repository.get_by_id(service_id, include_inactive=True)
        if not service:
            self.log_rejected("update_service", reason="not_found")
            raise ServiceOfferingNotFoundError(service_id)

        # Build update dict, converting enums and decimals
        update_data = data.model_dump(exclude_unset=True)
        if update_data.get("category"):
            update_data["category"] = update_data["category"].value
        if update_data.get("pricing_model"):
            update_data["pricing_model"] = update_data["pricing_model"].value
        if "base_price" in update_data and update_data["base_price"] is not None:
            update_data["base_price"] = float(update_data["base_price"])
        if (
            "price_per_zone" in update_data
            and update_data["price_per_zone"] is not None
        ):
            update_data["price_per_zone"] = float(update_data["price_per_zone"])

        updated = await self.repository.update(service_id, update_data)

        self.log_completed("update_service", service_id=str(service_id))
        return updated  # type: ignore[return-value]

    async def deactivate_service(self, service_id: UUID) -> None:
        """Deactivate a service offering (soft delete).

        Args:
            service_id: UUID of the service to deactivate

        Raises:
            ServiceOfferingNotFoundError: If service not found

        Validates: Requirement 1.6
        """
        self.log_started("deactivate_service", service_id=str(service_id))

        # Check if service exists
        service = await self.repository.get_by_id(service_id, include_inactive=True)
        if not service:
            self.log_rejected("deactivate_service", reason="not_found")
            raise ServiceOfferingNotFoundError(service_id)

        await self.repository.deactivate(service_id)

        self.log_completed("deactivate_service", service_id=str(service_id))

    async def list_services(
        self,
        page: int = 1,
        page_size: int = 20,
        category: ServiceCategory | None = None,
        is_active: bool | None = None,
        sort_by: str = "name",
        sort_order: str = "asc",
    ) -> tuple[list[ServiceOffering], int]:
        """List service offerings with filtering.

        Args:
            page: Page number (1-indexed)
            page_size: Number of items per page
            category: Filter by category
            is_active: Filter by active status
            sort_by: Field to sort by
            sort_order: Sort order (asc/desc)

        Returns:
            Tuple of (list of services, total count)

        Validates: Requirement 1.11
        """
        self.log_started("list_services", page=page, page_size=page_size)

        services, total = await self.repository.list_with_filters(
            page=page,
            page_size=page_size,
            category=category,
            is_active=is_active,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        self.log_completed("list_services", count=len(services), total=total)
        return services, total

    async def get_by_category(
        self,
        category: ServiceCategory,
    ) -> list[ServiceOffering]:
        """Get all active services in a category.

        Args:
            category: Service category to filter by

        Returns:
            List of active ServiceOffering instances

        Validates: Requirement 1.11
        """
        self.log_started("get_by_category", category=category.value)

        services = await self.repository.find_by_category(category, active_only=True)

        self.log_completed("get_by_category", count=len(services))
        return services
