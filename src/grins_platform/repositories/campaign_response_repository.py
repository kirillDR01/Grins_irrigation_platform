"""Campaign response repository for poll reply data access.

Validates: Scheduling Poll Req 14.1, 14.2, 14.3, 14.4, 14.5
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import TYPE_CHECKING

from sqlalchemy import func, literal_column, select

from grins_platform.log_config import LoggerMixin
from grins_platform.models.campaign_response import CampaignResponse

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.sql.selectable import Subquery


class CampaignResponseRepository(LoggerMixin):
    """Repository for campaign_responses table operations.

    All read queries that return "current" responses apply the latest-wins
    deduplication: ``DISTINCT ON (campaign_id, phone) ORDER BY received_at DESC``.

    Validates: Scheduling Poll Req 14.1-14.5
    """

    DOMAIN = "database"

    def __init__(self, session: AsyncSession) -> None:
        super().__init__()
        self.session = session

    async def add(self, row: CampaignResponse) -> CampaignResponse:
        """Insert a new campaign_responses row.

        Validates: Req 14.1
        """
        self.log_started("add", campaign_id=str(row.campaign_id))
        self.session.add(row)
        await self.session.flush()
        await self.session.refresh(row)
        self.log_completed("add", response_id=str(row.id))
        return row

    def _latest_wins_subquery(self, campaign_id: UUID) -> Subquery:
        """Build a subquery returning only the most recent row per phone.

        Uses ``DISTINCT ON (campaign_id, phone) ORDER BY received_at DESC``.

        Validates: Req 14.2
        """
        return (
            select(CampaignResponse.id)
            .where(CampaignResponse.campaign_id == campaign_id)
            .distinct(CampaignResponse.campaign_id, CampaignResponse.phone)
            .order_by(
                CampaignResponse.campaign_id,
                CampaignResponse.phone,
                CampaignResponse.received_at.desc(),
            )
            .subquery()
        )

    async def get_latest_for_campaign(
        self,
        campaign_id: UUID,
    ) -> list[CampaignResponse]:
        """Return the most recent response per phone for a campaign.

        Validates: Req 14.2
        """
        self.log_started("get_latest_for_campaign", campaign_id=str(campaign_id))
        sub = self._latest_wins_subquery(campaign_id)
        stmt = (
            select(CampaignResponse)
            .where(CampaignResponse.id.in_(select(sub.c.id)))
            .order_by(CampaignResponse.received_at.desc())
        )
        result = await self.session.execute(stmt)
        rows = list(result.scalars().all())
        self.log_completed("get_latest_for_campaign", count=len(rows))
        return rows

    async def list_for_campaign(
        self,
        campaign_id: UUID,
        option_key: str | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[CampaignResponse], int]:
        """Paginated list with latest-wins applied before pagination.

        Validates: Req 14.3
        """
        self.log_started("list_for_campaign", campaign_id=str(campaign_id))
        sub = self._latest_wins_subquery(campaign_id)

        base = select(CampaignResponse).where(
            CampaignResponse.id.in_(select(sub.c.id)),
        )

        # Build count subquery incrementally so that BOTH filters are
        # applied when both are provided. The previous implementation
        # rebuilt count_q from scratch inside each ``if`` block, which
        # meant that when both option_key AND status were supplied the
        # count only reflected the status filter (the last one applied).
        count_sub = (
            select(literal_column("1"))
            .where(CampaignResponse.id.in_(select(sub.c.id)))
            .select_from(CampaignResponse)
        )

        if option_key is not None:
            base = base.where(CampaignResponse.selected_option_key == option_key)
            count_sub = count_sub.where(
                CampaignResponse.selected_option_key == option_key,
            )
        if status is not None:
            base = base.where(CampaignResponse.status == status)
            count_sub = count_sub.where(CampaignResponse.status == status)

        count_q = select(func.count()).select_from(count_sub.subquery())

        total_result = await self.session.execute(count_q)
        total = total_result.scalar() or 0

        offset = (page - 1) * page_size
        stmt = (
            base.order_by(CampaignResponse.received_at.desc())
            .offset(offset)
            .limit(
                page_size,
            )
        )
        result = await self.session.execute(stmt)
        rows = list(result.scalars().all())

        self.log_completed("list_for_campaign", count=len(rows), total=total)
        return rows, total

    async def iter_for_export(
        self,
        campaign_id: UUID,
        option_key: str | None = None,
    ) -> AsyncIterator[CampaignResponse]:
        """Stream latest-wins rows in batches of 100 for CSV export.

        Validates: Req 14.4
        """
        self.log_started("iter_for_export", campaign_id=str(campaign_id))
        sub = self._latest_wins_subquery(campaign_id)
        base = select(CampaignResponse).where(
            CampaignResponse.id.in_(select(sub.c.id)),
        )
        if option_key is not None:
            base = base.where(CampaignResponse.selected_option_key == option_key)
        base = base.order_by(CampaignResponse.received_at.desc())

        result = await self.session.stream(base)
        count = 0
        async for partition in result.partitions(100):
            for row in partition:
                count += 1
                yield row[0]  # type: ignore[misc]
        self.log_completed("iter_for_export", count=count)

    async def count_by_status_and_option(
        self,
        campaign_id: UUID,
    ) -> list[dict[str, object]]:
        """Grouped counts for the summary endpoint.

        Returns a list of dicts with keys: status, option_key, count.

        Validates: Req 14.5
        """
        self.log_started(
            "count_by_status_and_option",
            campaign_id=str(campaign_id),
        )
        sub = self._latest_wins_subquery(campaign_id)

        stmt = (
            select(
                CampaignResponse.status,
                CampaignResponse.selected_option_key,
                func.count().label("cnt"),
            )
            .where(CampaignResponse.id.in_(select(sub.c.id)))
            .group_by(CampaignResponse.status, CampaignResponse.selected_option_key)
        )
        result = await self.session.execute(stmt)
        rows: list[dict[str, object]] = [
            {"status": r[0], "option_key": r[1], "count": r[2]} for r in result.all()
        ]
        self.log_completed("count_by_status_and_option", buckets=len(rows))
        return rows
