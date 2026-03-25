"""Estimate repository for database operations.

CRUD + get_by_token + find unapproved older than N hours + template CRUD.

Validates: CRM Gap Closure Req 17.3, 17.4, 48.2
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

from sqlalchemy import func, select, update

from grins_platform.log_config import LoggerMixin
from grins_platform.models.contract_template import ContractTemplate
from grins_platform.models.estimate import Estimate
from grins_platform.models.estimate_follow_up import EstimateFollowUp
from grins_platform.models.estimate_template import EstimateTemplate

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession


class EstimateRepository(LoggerMixin):
    """Repository for estimate database operations.

    Validates: CRM Gap Closure Req 17.3, 17.4, 48.2
    """

    DOMAIN = "database"

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session."""
        super().__init__()
        self.session = session

    # =========================================================================
    # Estimate CRUD
    # =========================================================================

    async def create(self, **kwargs: Any) -> Estimate:
        """Create a new estimate record.

        Args:
            **kwargs: Estimate field values

        Returns:
            Created Estimate instance
        """
        self.log_started("create")

        estimate = Estimate(**kwargs)
        self.session.add(estimate)
        await self.session.flush()
        await self.session.refresh(estimate)

        self.log_completed("create", estimate_id=str(estimate.id))
        return estimate

    async def get_by_id(self, estimate_id: UUID) -> Estimate | None:
        """Get an estimate by ID.

        Args:
            estimate_id: Estimate UUID

        Returns:
            Estimate instance or None if not found
        """
        self.log_started("get_by_id", estimate_id=str(estimate_id))

        stmt = select(Estimate).where(Estimate.id == estimate_id)
        result = await self.session.execute(stmt)
        estimate: Estimate | None = result.scalar_one_or_none()

        self.log_completed("get_by_id", found=estimate is not None)
        return estimate

    async def get_by_token(self, token: UUID) -> Estimate | None:
        """Get an estimate by customer portal token.

        Args:
            token: Customer portal token UUID

        Returns:
            Estimate instance or None if not found

        Validates: CRM Gap Closure Req 48.2, 78.1
        """
        self.log_started("get_by_token")

        stmt = select(Estimate).where(Estimate.customer_token == token)
        result = await self.session.execute(stmt)
        estimate: Estimate | None = result.scalar_one_or_none()

        self.log_completed("get_by_token", found=estimate is not None)
        return estimate

    async def update(
        self,
        estimate_id: UUID,
        **kwargs: Any,
    ) -> Estimate | None:
        """Update an estimate record.

        Args:
            estimate_id: Estimate UUID
            **kwargs: Fields to update

        Returns:
            Updated Estimate or None if not found
        """
        self.log_started("update", estimate_id=str(estimate_id))

        estimate = await self.get_by_id(estimate_id)
        if not estimate:
            self.log_completed("update", found=False)
            return None

        for key, value in kwargs.items():
            if hasattr(estimate, key):
                setattr(estimate, key, value)

        await self.session.flush()
        await self.session.refresh(estimate)

        self.log_completed("update", estimate_id=str(estimate.id))
        return estimate

    async def delete(self, estimate_id: UUID) -> bool:
        """Delete an estimate record.

        Args:
            estimate_id: Estimate UUID

        Returns:
            True if deleted, False if not found
        """
        self.log_started("delete", estimate_id=str(estimate_id))

        estimate = await self.get_by_id(estimate_id)
        if not estimate:
            self.log_completed("delete", found=False)
            return False

        await self.session.delete(estimate)
        await self.session.flush()

        self.log_completed("delete", estimate_id=str(estimate_id))
        return True

    async def list_with_filters(
        self,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        lead_id: UUID | None = None,
        customer_id: UUID | None = None,
    ) -> tuple[list[Estimate], int]:
        """List estimates with filtering and pagination.

        Args:
            page: Page number (1-based)
            page_size: Items per page
            status: Filter by status
            lead_id: Filter by lead
            customer_id: Filter by customer

        Returns:
            Tuple of (list of estimates, total count)
        """
        self.log_started("list_with_filters", page=page, page_size=page_size)

        base_query = select(Estimate)
        count_query = select(func.count(Estimate.id))

        if status is not None:
            base_query = base_query.where(Estimate.status == status)
            count_query = count_query.where(Estimate.status == status)

        if lead_id is not None:
            base_query = base_query.where(Estimate.lead_id == lead_id)
            count_query = count_query.where(Estimate.lead_id == lead_id)

        if customer_id is not None:
            base_query = base_query.where(Estimate.customer_id == customer_id)
            count_query = count_query.where(Estimate.customer_id == customer_id)

        count_result = await self.session.execute(count_query)
        total = count_result.scalar() or 0

        offset = (page - 1) * page_size
        stmt = (
            base_query.order_by(Estimate.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )

        result = await self.session.execute(stmt)
        estimates = list(result.scalars().all())

        self.log_completed("list_with_filters", count=len(estimates), total=total)
        return estimates, total

    async def find_unapproved_older_than(self, hours: int) -> list[Estimate]:
        """Find estimates sent but not approved after N hours.

        Used by background job to auto-route unapproved estimates to leads.

        Args:
            hours: Number of hours since estimate was sent

        Returns:
            List of unapproved estimates older than threshold

        Validates: CRM Gap Closure Req 32.4, 32.7
        """
        self.log_started("find_unapproved_older_than", hours=hours)

        cutoff = datetime.now(tz=timezone.utc) - timedelta(hours=hours)

        stmt = (
            select(Estimate)
            .where(Estimate.status == "sent")
            .where(Estimate.created_at <= cutoff)
            .where(Estimate.approved_at.is_(None))
            .where(Estimate.rejected_at.is_(None))
            .order_by(Estimate.created_at.asc())
        )

        result = await self.session.execute(stmt)
        estimates = list(result.scalars().all())

        self.log_completed("find_unapproved_older_than", count=len(estimates))
        return estimates

    # =========================================================================
    # Follow-Up Operations
    # =========================================================================

    async def create_follow_up(self, **kwargs: Any) -> EstimateFollowUp:
        """Create an estimate follow-up record.

        Args:
            **kwargs: Follow-up field values

        Returns:
            Created EstimateFollowUp instance
        """
        self.log_started("create_follow_up")

        follow_up = EstimateFollowUp(**kwargs)
        self.session.add(follow_up)
        await self.session.flush()
        await self.session.refresh(follow_up)

        self.log_completed("create_follow_up", follow_up_id=str(follow_up.id))
        return follow_up

    async def get_pending_follow_ups(self) -> list[EstimateFollowUp]:
        """Get follow-ups that are due to be sent.

        Returns:
            List of pending follow-ups with scheduled_at in the past
        """
        self.log_started("get_pending_follow_ups")

        now = datetime.now(tz=timezone.utc)
        stmt = (
            select(EstimateFollowUp)
            .where(EstimateFollowUp.status == "scheduled")
            .where(EstimateFollowUp.scheduled_at <= now)
            .order_by(EstimateFollowUp.scheduled_at.asc())
        )

        result = await self.session.execute(stmt)
        follow_ups = list(result.scalars().all())

        self.log_completed("get_pending_follow_ups", count=len(follow_ups))
        return follow_ups

    async def cancel_follow_ups_for_estimate(
        self,
        estimate_id: UUID,
    ) -> int:
        """Cancel all pending follow-ups for an estimate.

        Args:
            estimate_id: Estimate UUID

        Returns:
            Number of follow-ups cancelled
        """
        self.log_started(
            "cancel_follow_ups_for_estimate",
            estimate_id=str(estimate_id),
        )

        stmt = (
            update(EstimateFollowUp)
            .where(EstimateFollowUp.estimate_id == estimate_id)
            .where(EstimateFollowUp.status == "scheduled")
            .values(status="cancelled")
        )

        result = await self.session.execute(stmt)
        await self.session.flush()

        cancelled: int = getattr(result, "rowcount", 0) or 0

        self.log_completed(
            "cancel_follow_ups_for_estimate",
            cancelled=cancelled,
        )
        return cancelled

    # =========================================================================
    # Estimate Template CRUD
    # =========================================================================

    async def create_template(self, **kwargs: Any) -> EstimateTemplate:
        """Create an estimate template.

        Args:
            **kwargs: Template field values

        Returns:
            Created EstimateTemplate instance

        Validates: CRM Gap Closure Req 17.3
        """
        self.log_started("create_template")

        template = EstimateTemplate(**kwargs)
        self.session.add(template)
        await self.session.flush()
        await self.session.refresh(template)

        self.log_completed("create_template", template_id=str(template.id))
        return template

    async def get_template_by_id(
        self,
        template_id: UUID,
    ) -> EstimateTemplate | None:
        """Get an estimate template by ID.

        Args:
            template_id: Template UUID

        Returns:
            EstimateTemplate or None if not found
        """
        self.log_started("get_template_by_id", template_id=str(template_id))

        stmt = select(EstimateTemplate).where(EstimateTemplate.id == template_id)
        result = await self.session.execute(stmt)
        template: EstimateTemplate | None = result.scalar_one_or_none()

        self.log_completed("get_template_by_id", found=template is not None)
        return template

    async def list_templates(
        self,
        active_only: bool = True,
    ) -> list[EstimateTemplate]:
        """List estimate templates.

        Args:
            active_only: Whether to return only active templates

        Returns:
            List of EstimateTemplate instances

        Validates: CRM Gap Closure Req 17.3
        """
        self.log_started("list_templates", active_only=active_only)

        stmt = select(EstimateTemplate)
        if active_only:
            stmt = stmt.where(EstimateTemplate.is_active == True)  # noqa: E712

        stmt = stmt.order_by(EstimateTemplate.name.asc())

        result = await self.session.execute(stmt)
        templates = list(result.scalars().all())

        self.log_completed("list_templates", count=len(templates))
        return templates

    async def update_template(
        self,
        template_id: UUID,
        **kwargs: Any,
    ) -> EstimateTemplate | None:
        """Update an estimate template.

        Args:
            template_id: Template UUID
            **kwargs: Fields to update

        Returns:
            Updated EstimateTemplate or None if not found
        """
        self.log_started("update_template", template_id=str(template_id))

        template = await self.get_template_by_id(template_id)
        if not template:
            self.log_completed("update_template", found=False)
            return None

        for key, value in kwargs.items():
            if hasattr(template, key):
                setattr(template, key, value)

        await self.session.flush()
        await self.session.refresh(template)

        self.log_completed("update_template", template_id=str(template.id))
        return template

    async def delete_template(self, template_id: UUID) -> bool:
        """Delete an estimate template (soft-delete via is_active=False).

        Args:
            template_id: Template UUID

        Returns:
            True if deactivated, False if not found
        """
        self.log_started("delete_template", template_id=str(template_id))

        template = await self.get_template_by_id(template_id)
        if not template:
            self.log_completed("delete_template", found=False)
            return False

        template.is_active = False
        await self.session.flush()

        self.log_completed("delete_template", template_id=str(template_id))
        return True

    # =========================================================================
    # Contract Template CRUD
    # =========================================================================

    async def create_contract_template(self, **kwargs: Any) -> ContractTemplate:
        """Create a contract template.

        Args:
            **kwargs: Template field values

        Returns:
            Created ContractTemplate instance

        Validates: CRM Gap Closure Req 17.4
        """
        self.log_started("create_contract_template")

        template = ContractTemplate(**kwargs)
        self.session.add(template)
        await self.session.flush()
        await self.session.refresh(template)

        self.log_completed(
            "create_contract_template",
            template_id=str(template.id),
        )
        return template

    async def get_contract_template_by_id(
        self,
        template_id: UUID,
    ) -> ContractTemplate | None:
        """Get a contract template by ID.

        Args:
            template_id: Template UUID

        Returns:
            ContractTemplate or None if not found
        """
        self.log_started(
            "get_contract_template_by_id",
            template_id=str(template_id),
        )

        stmt = select(ContractTemplate).where(ContractTemplate.id == template_id)
        result = await self.session.execute(stmt)
        template: ContractTemplate | None = result.scalar_one_or_none()

        self.log_completed(
            "get_contract_template_by_id",
            found=template is not None,
        )
        return template

    async def list_contract_templates(
        self,
        active_only: bool = True,
    ) -> list[ContractTemplate]:
        """List contract templates.

        Args:
            active_only: Whether to return only active templates

        Returns:
            List of ContractTemplate instances

        Validates: CRM Gap Closure Req 17.4
        """
        self.log_started("list_contract_templates", active_only=active_only)

        stmt = select(ContractTemplate)
        if active_only:
            stmt = stmt.where(ContractTemplate.is_active == True)  # noqa: E712

        stmt = stmt.order_by(ContractTemplate.name.asc())

        result = await self.session.execute(stmt)
        templates = list(result.scalars().all())

        self.log_completed("list_contract_templates", count=len(templates))
        return templates

    async def update_contract_template(
        self,
        template_id: UUID,
        **kwargs: Any,
    ) -> ContractTemplate | None:
        """Update a contract template.

        Args:
            template_id: Template UUID
            **kwargs: Fields to update

        Returns:
            Updated ContractTemplate or None if not found
        """
        self.log_started(
            "update_contract_template",
            template_id=str(template_id),
        )

        template = await self.get_contract_template_by_id(template_id)
        if not template:
            self.log_completed("update_contract_template", found=False)
            return None

        for key, value in kwargs.items():
            if hasattr(template, key):
                setattr(template, key, value)

        await self.session.flush()
        await self.session.refresh(template)

        self.log_completed(
            "update_contract_template",
            template_id=str(template.id),
        )
        return template

    async def delete_contract_template(self, template_id: UUID) -> bool:
        """Delete a contract template (soft-delete via is_active=False).

        Args:
            template_id: Template UUID

        Returns:
            True if deactivated, False if not found
        """
        self.log_started(
            "delete_contract_template",
            template_id=str(template_id),
        )

        template = await self.get_contract_template_by_id(template_id)
        if not template:
            self.log_completed("delete_contract_template", found=False)
            return False

        template.is_active = False
        await self.session.flush()

        self.log_completed(
            "delete_contract_template",
            template_id=str(template_id),
        )
        return True
