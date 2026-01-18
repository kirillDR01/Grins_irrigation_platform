"""
Property service for business logic operations.

This module provides the PropertyService class for all property-related
business operations including CRUD and primary flag management.

Validates: Requirement 2.1, 2.5-2.11
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from grins_platform.log_config import LoggerMixin
from grins_platform.schemas.property import (
    PropertyCreate,
    PropertyResponse,
    PropertyUpdate,
    is_in_service_area,
)

if TYPE_CHECKING:
    from uuid import UUID

    from grins_platform.repositories.property_repository import PropertyRepository


class PropertyNotFoundError(Exception):
    """Raised when a property is not found.

    Validates: Requirement 6.1-6.5, 10.2-10.4
    """

    def __init__(self, property_id: UUID) -> None:
        """Initialize with property ID.

        Args:
            property_id: UUID of the property that was not found
        """
        self.property_id = property_id
        super().__init__(f"Property not found: {property_id}")


class PropertyService(LoggerMixin):
    """Service for property management operations.

    This class handles all business logic for property operations including
    CRUD operations and primary flag management. It uses the PropertyRepository
    for database operations and includes comprehensive logging.

    Attributes:
        repository: PropertyRepository for database operations

    Validates: Requirement 2.1, 2.5-2.11
    """

    DOMAIN = "business"

    def __init__(self, repository: PropertyRepository) -> None:
        """Initialize service with repository.

        Args:
            repository: PropertyRepository for database operations
        """
        super().__init__()
        self.repository = repository

    async def add_property(
        self,
        customer_id: UUID,
        data: PropertyCreate,
    ) -> PropertyResponse:
        """Add a property to a customer.

        If the property is marked as primary, this method will first clear
        the primary flag from all other properties of the same customer.

        If this is the first property for the customer, it will automatically
        be set as primary.

        Args:
            customer_id: UUID of the customer to add property to
            data: PropertyCreate schema with property data

        Returns:
            PropertyResponse with the created property data

        Validates: Requirement 2.1, 2.7, 2.8-2.11
        """
        self.log_started(
            "add_property",
            customer_id=str(customer_id),
            city=data.city,
            is_primary=data.is_primary,
        )

        # Check if city is in service area and log warning if not
        if not is_in_service_area(data.city):
            self.logger.warning(
                "business.propertyservice.add_property_warning",
                customer_id=str(customer_id),
                city=data.city,
                reason="city_outside_service_area",
            )

        # Check if this is the first property for the customer
        existing_count = await self.repository.count_by_customer_id(customer_id)
        is_first_property = existing_count == 0

        # If this is the first property, make it primary automatically
        should_be_primary = data.is_primary or is_first_property

        # If this property should be primary, clear other primary flags first
        if should_be_primary and not is_first_property:
            _ = await self.repository.clear_primary_flag(customer_id)

        # Create the property
        property_obj = await self.repository.create(
            customer_id=customer_id,
            address=data.address,
            city=data.city,
            state=data.state,
            zip_code=data.zip_code,
            zone_count=data.zone_count,
            system_type=data.system_type.value,
            property_type=data.property_type.value,
            is_primary=should_be_primary,
            access_instructions=data.access_instructions,
            gate_code=data.gate_code,
            has_dogs=data.has_dogs,
            special_notes=data.special_notes,
            latitude=data.latitude,
            longitude=data.longitude,
        )

        self.log_completed(
            "add_property",
            property_id=str(property_obj.id),
            customer_id=str(customer_id),
            is_primary=should_be_primary,
        )

        response: PropertyResponse = PropertyResponse.model_validate(property_obj)
        return response

    async def get_property(self, property_id: UUID) -> PropertyResponse:
        """Get a property by ID.

        Args:
            property_id: UUID of the property to retrieve

        Returns:
            PropertyResponse with the property data

        Raises:
            PropertyNotFoundError: If property is not found

        Validates: Requirement 2.5
        """
        self.log_started("get_property", property_id=str(property_id))

        property_obj = await self.repository.get_by_id(property_id)

        if not property_obj:
            self.log_rejected(
                "get_property",
                reason="not_found",
                property_id=str(property_id),
            )
            raise PropertyNotFoundError(property_id)

        self.log_completed("get_property", property_id=str(property_id))
        response: PropertyResponse = PropertyResponse.model_validate(property_obj)
        return response

    async def get_customer_properties(
        self,
        customer_id: UUID,
    ) -> list[PropertyResponse]:
        """Get all properties for a customer.

        Args:
            customer_id: UUID of the customer

        Returns:
            List of PropertyResponse objects

        Validates: Requirement 2.5
        """
        self.log_started("get_customer_properties", customer_id=str(customer_id))

        properties = await self.repository.get_by_customer_id(customer_id)

        self.log_completed(
            "get_customer_properties",
            customer_id=str(customer_id),
            count=len(properties),
        )

        return [PropertyResponse.model_validate(p) for p in properties]

    async def update_property(
        self,
        property_id: UUID,
        data: PropertyUpdate,
    ) -> PropertyResponse:
        """Update a property.

        Args:
            property_id: UUID of the property to update
            data: PropertyUpdate schema with fields to update

        Returns:
            PropertyResponse with the updated property data

        Raises:
            PropertyNotFoundError: If property is not found

        Validates: Requirement 2.2-2.4, 2.8-2.11
        """
        self.log_started("update_property", property_id=str(property_id))

        # Check if property exists
        existing = await self.repository.get_by_id(property_id)
        if not existing:
            self.log_rejected(
                "update_property",
                reason="not_found",
                property_id=str(property_id),
            )
            raise PropertyNotFoundError(property_id)

        # Check if city is being updated and warn if outside service area
        if data.city and not is_in_service_area(data.city):
            self.logger.warning(
                "business.propertyservice.update_property_warning",
                property_id=str(property_id),
                city=data.city,
                reason="city_outside_service_area",
            )

        # Get update data, excluding unset fields
        update_data = data.model_dump(exclude_unset=True)

        if not update_data:
            # No fields to update, return existing property
            self.log_completed(
                "update_property",
                property_id=str(property_id),
                fields_updated=0,
            )
            response: PropertyResponse = PropertyResponse.model_validate(existing)
            return response

        # Update the property
        updated = await self.repository.update(property_id, update_data)

        if not updated:
            # This shouldn't happen since we checked existence above
            self.log_failed(
                "update_property",
                error=Exception("Update returned None unexpectedly"),
                property_id=str(property_id),
            )
            raise PropertyNotFoundError(property_id)

        self.log_completed(
            "update_property",
            property_id=str(property_id),
            fields_updated=len(update_data),
        )

        updated_response: PropertyResponse = PropertyResponse.model_validate(updated)
        return updated_response

    async def delete_property(self, property_id: UUID) -> bool:
        """Delete a property.

        Args:
            property_id: UUID of the property to delete

        Returns:
            True if property was deleted

        Raises:
            PropertyNotFoundError: If property is not found

        Validates: Requirement 2.6
        """
        self.log_started("delete_property", property_id=str(property_id))

        # Check if property exists first
        existing = await self.repository.get_by_id(property_id)
        if not existing:
            self.log_rejected(
                "delete_property",
                reason="not_found",
                property_id=str(property_id),
            )
            raise PropertyNotFoundError(property_id)

        customer_id = existing.customer_id
        was_primary = existing.is_primary

        # Delete the property
        deleted = await self.repository.delete(property_id)

        if not deleted:
            self.log_failed(
                "delete_property",
                error=Exception("Delete returned False unexpectedly"),
                property_id=str(property_id),
            )
            raise PropertyNotFoundError(property_id)

        # If the deleted property was primary, set another property as primary
        if was_primary:
            remaining = await self.repository.get_by_customer_id(customer_id)
            if remaining:
                # Set the first remaining property as primary
                _ = await self.repository.set_primary(remaining[0].id)
                self.logger.info(
                    "business.propertyservice.delete_property_primary_reassigned",
                    property_id=str(property_id),
                    new_primary_id=str(remaining[0].id),
                )

        self.log_completed(
            "delete_property",
            property_id=str(property_id),
            was_primary=was_primary,
        )

        return True

    async def set_primary(self, property_id: UUID) -> PropertyResponse:
        """Set a property as the primary property for its customer.

        This method clears the primary flag from all other properties
        of the same customer and sets the specified property as primary.

        Args:
            property_id: UUID of the property to set as primary

        Returns:
            PropertyResponse with the updated property data

        Raises:
            PropertyNotFoundError: If property is not found

        Validates: Requirement 2.7
        """
        self.log_started("set_primary", property_id=str(property_id))

        # Check if property exists
        existing = await self.repository.get_by_id(property_id)
        if not existing:
            self.log_rejected(
                "set_primary",
                reason="not_found",
                property_id=str(property_id),
            )
            raise PropertyNotFoundError(property_id)

        # If already primary, just return it
        if existing.is_primary:
            self.log_completed(
                "set_primary",
                property_id=str(property_id),
                already_primary=True,
            )
            response: PropertyResponse = PropertyResponse.model_validate(existing)
            return response

        # Use repository method to set primary (handles clearing other flags)
        updated = await self.repository.set_primary(property_id)

        if not updated:
            self.log_failed(
                "set_primary",
                error=Exception("set_primary returned None unexpectedly"),
                property_id=str(property_id),
            )
            raise PropertyNotFoundError(property_id)

        self.log_completed(
            "set_primary",
            property_id=str(property_id),
            customer_id=str(updated.customer_id),
        )

        result: PropertyResponse = PropertyResponse.model_validate(updated)
        return result
