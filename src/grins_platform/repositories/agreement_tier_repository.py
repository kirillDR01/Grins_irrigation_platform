"""Repository for ServiceAgreementTier database operations.

Validates: Requirements 1.4, 19.6, 19.7
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select

from grins_platform.log_config import LoggerMixin
from grins_platform.models.service_agreement_tier import ServiceAgreementTier

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession


class AgreementTierRepository(LoggerMixin):
    """Repository for ServiceAgreementTier database operations.

    Validates: Requirements 1.4, 19.6, 19.7
    """

    DOMAIN = "database"

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session."""
        super().__init__()
        self.session = session

    async def list_active(self) -> list[ServiceAgreementTier]:
        """List all active tiers ordered by display_order.

        Validates: Requirement 1.4, 19.6
        """
        self.log_started("list_active")
        stmt = (
            select(ServiceAgreementTier)
            .where(ServiceAgreementTier.is_active.is_(True))
            .order_by(ServiceAgreementTier.display_order.asc())
        )
        result = await self.session.execute(stmt)
        tiers = list(result.scalars().all())
        self.log_completed("list_active", count=len(tiers))
        return tiers

    async def get_by_id(self, tier_id: UUID) -> ServiceAgreementTier | None:
        """Get a tier by ID.

        Validates: Requirement 19.7
        """
        self.log_started("get_by_id", tier_id=str(tier_id))
        stmt = select(ServiceAgreementTier).where(
            ServiceAgreementTier.id == tier_id,
        )
        result = await self.session.execute(stmt)
        tier: ServiceAgreementTier | None = result.scalar_one_or_none()
        self.log_completed("get_by_id", found=tier is not None)
        return tier

    async def get_by_slug_and_type(
        self,
        slug: str,
        package_type: str,
    ) -> ServiceAgreementTier | None:
        """Get a tier by slug and package_type combination.

        Validates: Requirement 1.4
        """
        self.log_started("get_by_slug_and_type", slug=slug, package_type=package_type)
        stmt = select(ServiceAgreementTier).where(
            ServiceAgreementTier.slug == slug,
            ServiceAgreementTier.package_type == package_type,
        )
        result = await self.session.execute(stmt)
        tier: ServiceAgreementTier | None = result.scalar_one_or_none()
        self.log_completed("get_by_slug_and_type", found=tier is not None)
        return tier
