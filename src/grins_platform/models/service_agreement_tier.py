"""
ServiceAgreementTier model for service package definitions.

Defines template records for service packages (Essential/Professional/Premium
x Residential/Commercial) with pricing, included services, and Stripe IDs.

Validates: Requirements 1.1, 1.2, 1.3, 1.4
"""

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import Boolean, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import (
    JSON,
    UUID as PGUUID,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from grins_platform.database import Base


class ServiceAgreementTier(Base):
    """Template record defining a service package tier.

    Attributes:
        id: Unique identifier (UUID)
        name: Tier display name (e.g., "Essential")
        slug: URL-friendly unique identifier (e.g., "essential-residential")
        description: Tier description text
        package_type: RESIDENTIAL or COMMERCIAL
        annual_price: Annual subscription price
        billing_frequency: Billing cycle (currently only "annual")
        included_services: JSONB array of {service_type, frequency, description}
        perks: JSONB array of perk strings
        stripe_product_id: Stripe product ID (nullable, env-specific)
        stripe_price_id: Stripe price ID (nullable, env-specific)
        is_active: Whether tier is available for new agreements
        display_order: Sort order for UI display
        created_at: Record creation timestamp
        updated_at: Record last update timestamp

    Validates: Requirements 1.1, 1.2, 1.3, 1.4
    """

    __tablename__ = "service_agreement_tiers"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    package_type: Mapped[str] = mapped_column(String(20), nullable=False)
    annual_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    billing_frequency: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="annual",
    )
    included_services: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON,
        nullable=False,
    )
    perks: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    stripe_product_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    stripe_price_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="true",
    )
    display_order: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now(),
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"<ServiceAgreementTier(id={self.id}, name='{self.name}', "
            f"slug='{self.slug}', package_type='{self.package_type}')>"
        )
