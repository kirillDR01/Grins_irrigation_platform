"""
ServiceOffering model for the service catalog.

This module defines the ServiceOffering SQLAlchemy model representing
service offerings in the Grin's Irrigation Platform service catalog.

Validates: Requirements 1.1, 1.4-1.13
"""

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import JSON, Boolean, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from grins_platform.database import Base
from grins_platform.models.enums import PricingModel, ServiceCategory


class ServiceOffering(Base):
    """Service offering model representing a service in the catalog.

    Attributes:
        id: Unique identifier for the service offering
        name: Name of the service (e.g., "Spring Startup")
        category: Service category (seasonal, repair, installation, etc.)
        description: Detailed description of the service
        base_price: Base price for the service
        price_per_zone: Additional price per zone (for zone_based pricing)
        pricing_model: How the service is priced (flat, zone_based, hourly, custom)
        estimated_duration_minutes: Base estimated duration in minutes
        duration_per_zone_minutes: Additional minutes per zone
        staffing_required: Number of staff members required
        equipment_required: List of equipment needed
        lien_eligible: Whether service qualifies for mechanic's lien
        requires_prepay: Whether payment is required before work
        is_active: Whether the service is currently offered
        created_at: Timestamp when the record was created
        updated_at: Timestamp when the record was last updated

    Validates: Requirements 1.1, 1.4-1.13
    """

    __tablename__ = "service_offerings"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        primary_key=True, server_default=func.gen_random_uuid(),
    )

    # Service Identity
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Pricing (Requirements 1.8)
    base_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    price_per_zone: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True,
    )
    pricing_model: Mapped[str] = mapped_column(String(50), nullable=False)

    # Duration Estimates (Requirement 1.9)
    estimated_duration_minutes: Mapped[int | None] = mapped_column(
        Integer, nullable=True,
    )
    duration_per_zone_minutes: Mapped[int | None] = mapped_column(
        Integer, nullable=True,
    )

    # Requirements (Requirement 1.10)
    staffing_required: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="1",
    )
    equipment_required: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)

    # Buffer Time (Requirement 8.1 - Route Optimization)
    buffer_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="10",
    )

    # Business Rules (Requirements 1.12, 1.13)
    lien_eligible: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false",
    )
    requires_prepay: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false",
    )

    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true",
    )

    # Timestamps (Requirement 1.7)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(),
    )

    def __repr__(self) -> str:
        """Return string representation of the service offering."""
        return (
            f"<ServiceOffering(id={self.id}, name='{self.name}', "
            f"category='{self.category}')>"
        )

    @property
    def category_enum(self) -> ServiceCategory:
        """Get the category as an enum value."""
        return ServiceCategory(self.category)

    @property
    def pricing_model_enum(self) -> PricingModel:
        """Get the pricing model as an enum value."""
        return PricingModel(self.pricing_model)

    def to_dict(self) -> dict[str, Any]:
        """Convert the service offering to a dictionary.

        Returns:
            Dictionary representation of the service offering.
        """
        return {
            "id": str(self.id),
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "base_price": float(self.base_price) if self.base_price else None,
            "price_per_zone": float(self.price_per_zone)
            if self.price_per_zone
            else None,
            "pricing_model": self.pricing_model,
            "estimated_duration_minutes": self.estimated_duration_minutes,
            "duration_per_zone_minutes": self.duration_per_zone_minutes,
            "staffing_required": self.staffing_required,
            "equipment_required": self.equipment_required,
            "lien_eligible": self.lien_eligible,
            "requires_prepay": self.requires_prepay,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
