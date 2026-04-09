"""Campaign poll-response API endpoints.

Provides summary, list, and CSV export for poll campaign responses.

Validates: Scheduling Poll Req 9, 10, 11
"""

from __future__ import annotations

import csv
import io
import re
from datetime import date
from collections.abc import AsyncGenerator
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: TC002

from grins_platform.api.v1.auth_dependencies import (
    ManagerOrAdminUser,  # noqa: TC001 - Required at runtime for FastAPI DI
)
from grins_platform.api.v1.dependencies import get_db_session
from grins_platform.log_config import LoggerMixin
from grins_platform.models.campaign import (
    Campaign,  # noqa: TC001 - Used at runtime for attribute access
)
from grins_platform.repositories.campaign_repository import CampaignRepository
from grins_platform.repositories.campaign_response_repository import (
    CampaignResponseRepository,
)
from grins_platform.schemas.campaign_response import (
    CampaignResponseSummary,
    PaginatedCampaignResponseOut,
)
from grins_platform.services.campaign_response_service import CampaignResponseService

router = APIRouter()


class _Endpoints(LoggerMixin):
    DOMAIN = "api"


_ep = _Endpoints()


def _slugify(name: str) -> str:
    """Convert campaign name to a filename-safe slug."""
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return slug or "campaign"


async def _get_campaign_or_404(
    campaign_id: UUID,
    session: AsyncSession,
) -> Campaign:
    """Raise 404 if campaign does not exist, otherwise return it."""
    repo = CampaignRepository(session)
    campaign = await repo.get_by_id(campaign_id)
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campaign not found: {campaign_id}",
        )
    return campaign


@router.get(
    "/{campaign_id}/responses/summary",
    response_model=CampaignResponseSummary,
    summary="Get poll response summary",
    description="Returns per-option bucket counts for a poll campaign.",
)
async def get_response_summary(
    campaign_id: UUID,
    _current_user: ManagerOrAdminUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CampaignResponseSummary:
    """Validates: Scheduling Poll Req 9.1-9.5."""
    _ep.log_started("get_response_summary", campaign_id=str(campaign_id))
    _ = await _get_campaign_or_404(campaign_id, session)
    svc = CampaignResponseService(session)
    result = await svc.get_response_summary(campaign_id)
    _ep.log_completed("get_response_summary", campaign_id=str(campaign_id))
    return result


@router.get(
    "/{campaign_id}/responses",
    response_model=PaginatedCampaignResponseOut,
    summary="List poll responses",
    description="Paginated list of poll responses with optional filters.",
)
async def list_responses(
    campaign_id: UUID,
    _current_user: ManagerOrAdminUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    option_key: str | None = None,
    response_status: str | None = None,
    page: int = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PaginatedCampaignResponseOut:
    """Validates: Scheduling Poll Req 10.1-10.4."""
    _ep.log_started("list_responses", campaign_id=str(campaign_id))
    _ = await _get_campaign_or_404(campaign_id, session)
    repo = CampaignResponseRepository(session)
    rows, total = await repo.list_for_campaign(
        campaign_id,
        option_key=option_key,
        status=response_status,
        page=page,
        page_size=page_size,
    )
    _ep.log_completed("list_responses", campaign_id=str(campaign_id), count=len(rows))
    return PaginatedCampaignResponseOut(
        items=rows,  # type: ignore[arg-type]
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{campaign_id}/responses/export.csv",
    summary="Export poll responses as CSV",
    description="Stream CSV of poll responses with latest-wins deduplication.",
)
async def export_responses_csv(
    campaign_id: UUID,
    current_user: ManagerOrAdminUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    option_key: str | None = None,
) -> StreamingResponse:
    """Validates: Scheduling Poll Req 11.1-11.9, 16.5."""
    _ep.log_started("export_responses_csv", campaign_id=str(campaign_id))
    campaign = await _get_campaign_or_404(campaign_id, session)
    svc = CampaignResponseService(session)

    slug = _slugify(campaign.name)
    today = date.today().isoformat()
    filename = f"campaign_{slug}_{today}_responses.csv"

    async def _csv_stream() -> AsyncGenerator[str, None]:
        buf = io.StringIO()
        writer = csv.writer(buf, quoting=csv.QUOTE_ALL)
        writer.writerow([
            "first_name", "last_name", "phone",
            "selected_option_label", "raw_reply", "status", "address", "received_at",
        ])
        yield buf.getvalue()
        buf.seek(0)
        buf.truncate(0)

        async for csv_row in svc.iter_csv_rows(campaign_id, option_key):
            writer.writerow([
                csv_row.first_name, csv_row.last_name, csv_row.phone,
                csv_row.selected_option_label, csv_row.raw_reply,
                csv_row.status, csv_row.address, csv_row.received_at,
            ])
            yield buf.getvalue()
            buf.seek(0)
            buf.truncate(0)

    _ep.logger.info(
        "campaign.response.csv_exported",
        campaign_id=str(campaign_id),
        actor_id=str(current_user.id),
    )
    _ep.log_completed("export_responses_csv", campaign_id=str(campaign_id))

    return StreamingResponse(
        _csv_stream(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
