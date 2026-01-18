"""
Property repository for database operations.

This module provides the PropertyRepository class for all property-related
database operations using SQLAlchemy 2.0 async patterns.

Validates: Requirement 2.1, 2.5, 2.6, 2.7
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import select, update

from grins_platform.log_config import LoggerMixin
from grins_platform.models.property import Property

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession


class PropertyRepository(LoggerMixin):
    """Repository for property database operations.

    This class handles all database operations for properties including
    CRUD operations and primary flag management.

    Attributes:
        session: AsyncSession for database operations

    Validates: Requirement 2.1, 2.5, 2.6, 2.7
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
        address: str,
        city: str,
        state: str = "MN",
        zip_code: str | None = None,
        zone_count: int | None = None,
        system_type: str = "standard",
        property_type: str = "residential",
        is_primary: bool = False,
        access_instructions: str | None = None,
        gate_code: str | None = None,
        has_dogs: bool = False,
        special_notes: str | None = None,
        latitude: float | Decimal | None = None,
        longitude: float | Decimal | None = None,
    ) -> Property:
        """Create a new property record.

        Args:
            customer_id: UUID of the owning customer
            address: Street address
            city: City name
            state: State abbreviation (default: MN)
            zip_code: ZIP code (optional)
            zone_count: Number of irrigation zones (1-50)
            system_type: Type of irrigation system
            property_type: Type of property
            is_primary: Whether this is the primary property
            access_instructions: Special entry instructions
            gate_code: Gate access code
            has_dogs: Safety flag for field technicians
            special_notes: Additional notes
            latitude: GPS latitude
            longitude: GPS longitude

        Returns:
            Created Property instance

        Validates: Requirement 2.1
        """
        self.log_started("create", customer_id=str(customer_id), city=city)

        # Convert float to Decimal for database storage
        lat_decimal = Decimal(str(latitude)) if latitude is not None else None
        lon_decimal = Decimal(str(longitude)) if longitude is not None else None

        property_obj = Property(
            customer_id=customer_id,
            address=address,
            city=city,
            state=state,
            zip_code=zip_code,
            zone_count=zone_count,
            system_type=system_type,
            property_type=property_type,
            is_primary=is_primary,
            access_instructions=access_instructions,
            gate_code=gate_code,
            has_dogs=has_dogs,
            special_notes=special_notes,
            latitude=lat_decimal,
            longitude=lon_decimal,
        )

        self.session.add(property_obj)
        await self.session.flush()
        await self.session.refresh(property_obj)

        self.log_completed("create", property_id=str(property_obj.id))
        return property_obj

    async def get_by_id(self, property_id: UUID) -> Property | None:
        """Get a property by ID.

        Args:
            property_id: UUID of the property

        Returns:
            Property instance or None if not found

        Validates: Requirement 2.5
        """
        self.log_started("get_by_id", property_id=str(property_id))

        stmt = select(Property).where(Property.id == property_id)

        result = await self.session.execute(stmt)
        property_obj: Property | None = result.scalar_one_or_none()

        if property_obj:
            self.log_completed("get_by_id", property_id=str(property_id))
        else:
            self.log_completed("get_by_id", property_id=str(property_id), found=False)

        return property_obj

    async def update(
        self,
        property_id: UUID,
        data: dict[str, Any],
    ) -> Property | None:
        """Update a property record.

        Args:
            property_id: UUID of the property to update
            data: Dictionary of fields to update

        Returns:
            Updated Property instance or None if not found

        Validates: Requirement 2.5
        """
        self.log_started("update", property_id=str(property_id))

        # Remove None values
        update_data = {k: v for k, v in data.items() if v is not None}

        if not update_data:
            return await self.get_by_id(property_id)

        # Convert float coordinates to Decimal
        if "latitude" in update_data and update_data["latitude"] is not None:
            update_data["latitude"] = Decimal(str(update_data["latitude"]))
        if "longitude" in update_data and update_data["longitude"] is not None:
            update_data["longitude"] = Decimal(str(update_data["longitude"]))

        # Handle enum values - convert to string if needed
        if "system_type" in update_data:
            val = update_data["system_type"]
            update_data["system_type"] = val.value if hasattr(val, "value") else val
        if "property_type" in update_data:
            val = update_data["property_type"]
            update_data["property_type"] = val.value if hasattr(val, "value") else val

        # Update timestamp
        update_data["updated_at"] = datetime.now()

        stmt = (
            update(Property)
            .where(Property.id == property_id)
            .values(**update_data)
            .returning(Property)
        )

        result = await self.session.execute(stmt)
        await self.session.flush()

        property_obj: Property | None = result.scalar_one_or_none()

        if property_obj:
            self.log_completed("update", property_id=str(property_id))
        else:
            self.log_completed("update", property_id=str(property_id), found=False)

        return property_obj

    async def delete(self, property_id: UUID) -> bool:
        """Delete a property.

        Args:
            property_id: UUID of the property to delete

        Returns:
            True if property was deleted, False if not found

        Validates: Requirement 2.6
        """
        self.log_started("delete", property_id=str(property_id))

        property_obj = await self.get_by_id(property_id)

        if not property_obj:
            self.log_completed("delete", property_id=str(property_id), found=False)
            return False

        await self.session.delete(property_obj)
        await self.session.flush()

        self.log_completed("delete", property_id=str(property_id))
        return True

    async def get_by_customer_id(self, customer_id: UUID) -> list[Property]:
        """Get all properties for a customer.

        Args:
            customer_id: UUID of the customer

        Returns:
            List of Property instances

        Validates: Requirement 2.5
        """
        self.log_started("get_by_customer_id", customer_id=str(customer_id))

        stmt = (
            select(Property)
            .where(Property.customer_id == customer_id)
            .order_by(Property.is_primary.desc(), Property.created_at)
        )

        result = await self.session.execute(stmt)
        properties = list(result.scalars().all())

        self.log_completed("get_by_customer_id", count=len(properties))
        return properties

    async def clear_primary_flag(self, customer_id: UUID) -> int:
        """Clear the primary flag for all properties of a customer.

        Args:
            customer_id: UUID of the customer

        Returns:
            Number of properties updated

        Validates: Requirement 2.7
        """
        self.log_started("clear_primary_flag", customer_id=str(customer_id))

        stmt = (
            update(Property)
            .where(Property.customer_id == customer_id)
            .where(Property.is_primary == True)  # noqa: E712
            .values(is_primary=False, updated_at=datetime.now())
        )

        result = await self.session.execute(stmt)
        await self.session.flush()

        # rowcount is available on CursorResult but pyright doesn't recognize it
        updated_count: int = getattr(result, "rowcount", 0) or 0

        self.log_completed("clear_primary_flag", updated_count=updated_count)
        return updated_count

    async def set_primary(self, property_id: UUID) -> Property | None:
        """Set a property as the primary property.

        This method first clears the primary flag from all other properties
        of the same customer, then sets the specified property as primary.

        Args:
            property_id: UUID of the property to set as primary

        Returns:
            Updated Property instance or None if not found

        Validates: Requirement 2.7
        """
        self.log_started("set_primary", property_id=str(property_id))

        # Get the property to find the customer_id
        property_obj = await self.get_by_id(property_id)

        if not property_obj:
            self.log_completed("set_primary", property_id=str(property_id), found=False)
            return None

        # Clear primary flag from all other properties of this customer
        _ = await self.clear_primary_flag(property_obj.customer_id)

        # Set this property as primary
        updated = await self.update(property_id, {"is_primary": True})

        self.log_completed("set_primary", property_id=str(property_id))
        return updated

    async def count_by_customer_id(self, customer_id: UUID) -> int:
        """Count properties for a customer.

        Args:
            customer_id: UUID of the customer

        Returns:
            Number of properties

        Validates: Requirement 2.6
        """
        self.log_started("count_by_customer_id", customer_id=str(customer_id))

        from sqlalchemy import func as sqla_func  # noqa: PLC0415

        stmt = (
            select(sqla_func.count())
            .select_from(Property)
            .where(Property.customer_id == customer_id)
        )

        result = await self.session.execute(stmt)
        count = result.scalar() or 0

        self.log_completed("count_by_customer_id", count=count)
        return count
