"""
Property SQLAlchemy model.

This module defines the Property model with all fields, relationships,
and behaviors as specified in the design document.

Validates: Requirement 2.1, 2.6
"""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from grins_platform.database import Base
from grins_platform.models.enums import PropertyType, SystemType

if TYPE_CHECKING:
    from grins_platform.models.customer import Customer
    from grins_platform.models.job import Job


class Property(Base):
    """Property model representing a physical location for irrigation services.

    This model stores property location, irrigation system details,
    and access information for field technicians.

    Attributes:
        id: Unique identifier (UUID)
        customer_id: Foreign key to the owning customer
        address: Street address
        city: City name
        state: State abbreviation (default: MN)
        zip_code: ZIP code (optional)
        latitude: GPS latitude for route optimization
        longitude: GPS longitude for route optimization
        zone_count: Number of irrigation zones (1-50)
        system_type: Type of irrigation system (standard/lake_pump)
        property_type: Type of property (residential/commercial)
        is_primary: Whether this is the customer's primary property
        access_instructions: Special entry instructions
        gate_code: Gate access code
        has_dogs: Safety flag for field technicians
        special_notes: Additional notes about the property
        created_at: Record creation timestamp
        updated_at: Record last update timestamp
        customer: Related customer object

    Validates: Requirement 2.1, 2.6
    """

    __tablename__ = "properties"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )

    # Foreign key to customers (Requirement 2.1)
    customer_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Location fields (Requirement 2.8)
    address: Mapped[str] = mapped_column(String(255), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    state: Mapped[str] = mapped_column(String(50), nullable=False, default="MN")
    zip_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    latitude: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 8),
        nullable=True,
    )
    longitude: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(11, 8),
        nullable=True,
    )

    # System Details (Requirement 2.2, 2.3, 2.4)
    zone_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    system_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=SystemType.STANDARD.value,
    )
    property_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=PropertyType.RESIDENTIAL.value,
    )

    # Access Information (Requirement 2.7, 2.9, 2.10)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    access_instructions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    gate_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    has_dogs: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    special_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    customer: Mapped["Customer"] = relationship(
        "Customer",
        back_populates="properties",
    )
    jobs: Mapped[list["Job"]] = relationship(
        "Job",
        back_populates="job_property",
        lazy="selectin",
    )

    @property
    def system_type_enum(self) -> SystemType:
        """Get the system type as an enum value."""
        return SystemType(self.system_type)

    @property
    def property_type_enum(self) -> PropertyType:
        """Get the property type as an enum value."""
        return PropertyType(self.property_type)

    @property
    def full_address(self) -> str:
        """Get the full formatted address."""
        parts = [self.address, self.city, self.state]
        if self.zip_code:
            parts.append(self.zip_code)
        return ", ".join(parts)

    @property
    def has_coordinates(self) -> bool:
        """Check if GPS coordinates are available."""
        return self.latitude is not None and self.longitude is not None

    def __repr__(self) -> str:
        """Return string representation of property."""
        return (
            f"<Property(id={self.id}, address='{self.address}', "
            f"city='{self.city}', zones={self.zone_count})>"
        )
