"""Campaign repository for database operations.

CRUD + recipient management + stats aggregation.

Validates: CRM Gap Closure Req 45.3, 45.5
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import func, select, update

from grins_platform.log_config import LoggerMixin
from grins_platform.models.campaign import Campaign, CampaignRecipient

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession


class CampaignRepository(LoggerMixin):
    """Repository for campaign database operations.

    Validates: CRM Gap Closure Req 45.3, 45.5
    """

    DOMAIN = "database"

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session."""
        super().__init__()
        self.session = session

    # =========================================================================
    # Campaign CRUD
    # =========================================================================

    async def create(self, **kwargs: Any) -> Campaign:
        """Create a new campaign record.

        Args:
            **kwargs: Campaign field values

        Returns:
            Created Campaign instance
        """
        self.log_started("create")

        campaign = Campaign(**kwargs)
        self.session.add(campaign)
        await self.session.flush()
        await self.session.refresh(campaign)

        self.log_completed("create", campaign_id=str(campaign.id))
        return campaign

    async def get_by_id(self, campaign_id: UUID) -> Campaign | None:
        """Get a campaign by ID.

        Args:
            campaign_id: Campaign UUID

        Returns:
            Campaign instance or None if not found
        """
        self.log_started("get_by_id", campaign_id=str(campaign_id))

        stmt = select(Campaign).where(Campaign.id == campaign_id)
        result = await self.session.execute(stmt)
        campaign: Campaign | None = result.scalar_one_or_none()

        self.log_completed("get_by_id", found=campaign is not None)
        return campaign

    async def update(
        self,
        campaign_id: UUID,
        **kwargs: Any,
    ) -> Campaign | None:
        """Update a campaign record.

        Args:
            campaign_id: Campaign UUID
            **kwargs: Fields to update

        Returns:
            Updated Campaign or None if not found
        """
        self.log_started("update", campaign_id=str(campaign_id))

        campaign = await self.get_by_id(campaign_id)
        if not campaign:
            self.log_completed("update", found=False)
            return None

        for key, value in kwargs.items():
            if hasattr(campaign, key):
                setattr(campaign, key, value)

        await self.session.flush()
        await self.session.refresh(campaign)

        self.log_completed("update", campaign_id=str(campaign.id))
        return campaign

    async def delete(self, campaign_id: UUID) -> bool:
        """Delete a campaign and its recipients (cascade).

        Args:
            campaign_id: Campaign UUID

        Returns:
            True if deleted, False if not found
        """
        self.log_started("delete", campaign_id=str(campaign_id))

        campaign = await self.get_by_id(campaign_id)
        if not campaign:
            self.log_completed("delete", found=False)
            return False

        await self.session.delete(campaign)
        await self.session.flush()

        self.log_completed("delete", campaign_id=str(campaign_id))
        return True

    async def list_with_filters(
        self,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        campaign_type: str | None = None,
    ) -> tuple[list[Campaign], int]:
        """List campaigns with filtering and pagination.

        Args:
            page: Page number (1-based)
            page_size: Items per page
            status: Filter by campaign status
            campaign_type: Filter by campaign type

        Returns:
            Tuple of (list of campaigns, total count)

        Validates: CRM Gap Closure Req 45.3
        """
        self.log_started("list_with_filters", page=page, page_size=page_size)

        base_query = select(Campaign)
        count_query = select(func.count(Campaign.id))

        if status is not None:
            base_query = base_query.where(Campaign.status == status)
            count_query = count_query.where(Campaign.status == status)

        if campaign_type is not None:
            base_query = base_query.where(Campaign.campaign_type == campaign_type)
            count_query = count_query.where(Campaign.campaign_type == campaign_type)

        count_result = await self.session.execute(count_query)
        total = count_result.scalar() or 0

        offset = (page - 1) * page_size
        stmt = (
            base_query.order_by(Campaign.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )

        result = await self.session.execute(stmt)
        campaigns = list(result.scalars().all())

        self.log_completed("list_with_filters", count=len(campaigns), total=total)
        return campaigns, total

    async def find_scheduled_ready(self) -> list[Campaign]:
        """Find campaigns scheduled to be sent now.

        Returns:
            List of campaigns with status=scheduled and scheduled_at in the past
        """
        self.log_started("find_scheduled_ready")

        stmt = (
            select(Campaign)
            .where(Campaign.status == "scheduled")
            .where(Campaign.scheduled_at.isnot(None))
            .where(Campaign.scheduled_at <= func.now())
            .order_by(Campaign.scheduled_at.asc())
        )

        result = await self.session.execute(stmt)
        campaigns = list(result.scalars().all())

        self.log_completed("find_scheduled_ready", count=len(campaigns))
        return campaigns

    # =========================================================================
    # Recipient Management
    # =========================================================================

    async def add_recipient(self, **kwargs: Any) -> CampaignRecipient:
        """Add a recipient to a campaign.

        Args:
            **kwargs: Recipient field values

        Returns:
            Created CampaignRecipient instance

        Validates: CRM Gap Closure Req 45.5
        """
        self.log_started("add_recipient")

        recipient = CampaignRecipient(**kwargs)
        self.session.add(recipient)
        await self.session.flush()
        await self.session.refresh(recipient)

        self.log_completed("add_recipient", recipient_id=str(recipient.id))
        return recipient

    async def add_recipients_bulk(
        self,
        recipients: list[dict[str, Any]],
    ) -> list[CampaignRecipient]:
        """Add multiple recipients to a campaign.

        Args:
            recipients: List of recipient field value dicts

        Returns:
            List of created CampaignRecipient instances
        """
        self.log_started("add_recipients_bulk", count=len(recipients))

        created: list[CampaignRecipient] = []
        for recipient_data in recipients:
            recipient = CampaignRecipient(**recipient_data)
            self.session.add(recipient)
            created.append(recipient)

        await self.session.flush()
        for r in created:
            await self.session.refresh(r)

        self.log_completed("add_recipients_bulk", count=len(created))
        return created

    async def get_recipients(
        self,
        campaign_id: UUID,
        page: int = 1,
        page_size: int = 50,
        delivery_status: str | None = None,
    ) -> tuple[list[CampaignRecipient], int]:
        """Get recipients for a campaign with pagination.

        Args:
            campaign_id: Campaign UUID
            page: Page number (1-based)
            page_size: Items per page
            delivery_status: Filter by delivery status

        Returns:
            Tuple of (list of recipients, total count)
        """
        self.log_started("get_recipients", campaign_id=str(campaign_id))

        base_query = select(CampaignRecipient).where(
            CampaignRecipient.campaign_id == campaign_id,
        )
        count_query = select(func.count(CampaignRecipient.id)).where(
            CampaignRecipient.campaign_id == campaign_id,
        )

        if delivery_status is not None:
            base_query = base_query.where(
                CampaignRecipient.delivery_status == delivery_status,
            )
            count_query = count_query.where(
                CampaignRecipient.delivery_status == delivery_status,
            )

        count_result = await self.session.execute(count_query)
        total = count_result.scalar() or 0

        offset = (page - 1) * page_size
        stmt = (
            base_query.order_by(CampaignRecipient.created_at.asc())
            .offset(offset)
            .limit(page_size)
        )

        result = await self.session.execute(stmt)
        recipients = list(result.scalars().all())

        self.log_completed("get_recipients", count=len(recipients), total=total)
        return recipients, total

    async def update_recipient_status(
        self,
        recipient_id: UUID,
        delivery_status: str,
        error_message: str | None = None,
    ) -> CampaignRecipient | None:
        """Update a recipient's delivery status.

        Args:
            recipient_id: Recipient UUID
            delivery_status: New delivery status
            error_message: Error message if failed

        Returns:
            Updated CampaignRecipient or None if not found
        """
        self.log_started(
            "update_recipient_status",
            recipient_id=str(recipient_id),
            delivery_status=delivery_status,
        )

        stmt = select(CampaignRecipient).where(
            CampaignRecipient.id == recipient_id,
        )
        result = await self.session.execute(stmt)
        recipient: CampaignRecipient | None = result.scalar_one_or_none()

        if not recipient:
            self.log_completed("update_recipient_status", found=False)
            return None

        recipient.delivery_status = delivery_status
        if error_message is not None:
            recipient.error_message = error_message

        await self.session.flush()
        await self.session.refresh(recipient)

        self.log_completed(
            "update_recipient_status",
            recipient_id=str(recipient_id),
        )
        return recipient

    # =========================================================================
    # Stats Aggregation
    # =========================================================================

    async def get_campaign_stats(
        self,
        campaign_id: UUID,
    ) -> dict[str, int]:
        """Get delivery statistics for a campaign.

        Args:
            campaign_id: Campaign UUID

        Returns:
            Dict with status counts: total, sent, delivered, failed, bounced, opted_out

        Validates: CRM Gap Closure Req 45.5
        """
        self.log_started("get_campaign_stats", campaign_id=str(campaign_id))

        stmt = (
            select(
                CampaignRecipient.delivery_status,
                func.count(CampaignRecipient.id),
            )
            .where(CampaignRecipient.campaign_id == campaign_id)
            .group_by(CampaignRecipient.delivery_status)
        )

        result = await self.session.execute(stmt)
        status_counts = {str(row[0]): int(row[1]) for row in result.all()}

        total = sum(status_counts.values())
        stats: dict[str, int] = {
            "total": total,
            "sent": status_counts.get("sent", 0),
            "delivered": status_counts.get("delivered", 0),
            "failed": status_counts.get("failed", 0),
            "bounced": status_counts.get("bounced", 0),
            "opted_out": status_counts.get("opted_out", 0),
            "pending": status_counts.get("pending", 0),
            "sending": status_counts.get("sending", 0),
        }

        self.log_completed("get_campaign_stats", total=total)
        return stats

    async def get_failed_recipients(
        self,
        campaign_id: UUID,
    ) -> list[CampaignRecipient]:
        """Get all failed recipients for a campaign.

        Args:
            campaign_id: Campaign UUID

        Returns:
            List of failed CampaignRecipient rows.
        """
        self.log_started("get_failed_recipients", campaign_id=str(campaign_id))
        stmt = (
            select(CampaignRecipient)
            .where(CampaignRecipient.campaign_id == campaign_id)
            .where(CampaignRecipient.delivery_status == "failed")
            .order_by(CampaignRecipient.created_at.asc())
        )
        result = await self.session.execute(stmt)
        rows = list(result.scalars().all())
        self.log_completed("get_failed_recipients", count=len(rows))
        return rows

    async def clone_recipients_as_pending(
        self,
        campaign_id: UUID,
        source_recipient_ids: list[UUID],
    ) -> int:
        """Create new pending CampaignRecipient rows cloned from failed ones.

        Original failed rows are kept for audit. New rows get fresh ``pending``
        status.

        Args:
            campaign_id: Campaign UUID
            source_recipient_ids: IDs of failed recipients to retry.

        Returns:
            Number of new rows created.
        """
        self.log_started(
            "clone_recipients_as_pending",
            campaign_id=str(campaign_id),
            count=len(source_recipient_ids),
        )
        if not source_recipient_ids:
            return 0

        stmt = select(CampaignRecipient).where(
            CampaignRecipient.id.in_(source_recipient_ids),
            CampaignRecipient.campaign_id == campaign_id,
            CampaignRecipient.delivery_status == "failed",
        )
        result = await self.session.execute(stmt)
        sources = list(result.scalars().all())

        created = 0
        for src in sources:
            new_row = CampaignRecipient(
                campaign_id=campaign_id,
                customer_id=src.customer_id,
                lead_id=src.lead_id,
                channel=src.channel,
                delivery_status="pending",
            )
            self.session.add(new_row)
            created += 1

        if created:
            await self.session.flush()

        self.log_completed("clone_recipients_as_pending", created=created)
        return created

    async def cancel_pending_recipients(self, campaign_id: UUID) -> int:
        """Transition all ``pending`` recipients to ``cancelled``.

        ``sending`` rows are left untouched so they finish naturally.

        Args:
            campaign_id: Campaign UUID

        Returns:
            Number of rows transitioned to cancelled.
        """
        self.log_started("cancel_pending_recipients", campaign_id=str(campaign_id))

        stmt = (
            update(CampaignRecipient)
            .where(CampaignRecipient.campaign_id == campaign_id)
            .where(CampaignRecipient.delivery_status == "pending")
            .values(delivery_status="cancelled")
        )
        result = await self.session.execute(stmt)
        cancelled: int = result.rowcount  # type: ignore[assignment]
        await self.session.flush()

        self.log_completed(
            "cancel_pending_recipients",
            campaign_id=str(campaign_id),
            cancelled=cancelled,
        )
        return cancelled
