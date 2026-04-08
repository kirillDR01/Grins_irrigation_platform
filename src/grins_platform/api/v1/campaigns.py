"""Campaign API endpoints.

Provides CRUD for marketing campaigns, sending, and stats.

Validates: CRM Gap Closure Req 45.3, 45.4, 45.5
"""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: TC002

from grins_platform.api.v1.auth_dependencies import (
    AdminUser,
    CurrentActiveUser,
    ManagerOrAdminUser,
    require_campaign_send_authority,
)
from grins_platform.api.v1.dependencies import get_campaign_service, get_db_session
from grins_platform.log_config import LoggerMixin
from grins_platform.models.enums import (
    CampaignStatus,  # noqa: TC001 - Required at runtime for FastAPI query params
)
from grins_platform.models.staff import (
    Staff,  # noqa: TC001 - Required at runtime for FastAPI DI
)
from grins_platform.repositories.campaign_repository import CampaignRepository
from grins_platform.schemas.campaign import (
    AudiencePreviewResponse,
    CampaignCancelResult,
    CampaignCreate,
    CampaignResponse,
    CampaignSendAcceptedResponse,
    CampaignStats,
    CsvRejectedRow,
    CsvUploadResult,
    TargetAudience,
    WorkerHealthResponse,
)
from grins_platform.services.campaign_service import (
    CampaignAlreadySentError,
    CampaignNotFoundError,
    CampaignService,
    NoRecipientsError,
)
from grins_platform.services.sms.audit import (
    log_campaign_cancelled,
    log_campaign_created,
    log_campaign_sent_initiated,
)

router = APIRouter()


class _CampaignEndpoints(LoggerMixin):
    """Campaign API endpoint handlers with logging."""

    DOMAIN = "api"


_endpoints = _CampaignEndpoints()


# =============================================================================
# CRUD endpoints
# =============================================================================


@router.post(
    "",
    response_model=CampaignResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create campaign",
    description="Create a new marketing campaign.",
)
async def create_campaign(
    data: CampaignCreate,
    current_user: ManagerOrAdminUser,
    service: Annotated[CampaignService, Depends(get_campaign_service)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CampaignResponse:
    """Create a new campaign.

    Validates: CRM Gap Closure Req 45.3, Requirement 41
    """
    _endpoints.log_started("create_campaign", name=data.name)
    result = await service.create_campaign(data, created_by=current_user.id)
    await log_campaign_created(
        session,
        campaign_id=result.id,
        actor_id=current_user.id,
        actor_role=current_user.role,
        details={"name": data.name, "type": data.campaign_type.value},
    )
    _endpoints.log_completed("create_campaign", campaign_id=str(result.id))
    return result


@router.get(
    "",
    response_model=dict[str, Any],
    summary="List campaigns",
    description="List campaigns with pagination and optional status filter.",
)
async def list_campaigns(
    _current_user: CurrentActiveUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    status_filter: CampaignStatus | None = Query(
        default=None,
        alias="status",
        description="Filter by status",
    ),
) -> dict[str, Any]:
    """List campaigns with pagination.

    Validates: CRM Gap Closure Req 45.3
    """
    _endpoints.log_started("list_campaigns", page=page)
    repo = CampaignRepository(session)
    campaigns, total = await repo.list_with_filters(
        page=page,
        page_size=page_size,
        status=status_filter.value if status_filter else None,
    )
    items = [CampaignResponse.model_validate(c) for c in campaigns]
    _endpoints.log_completed("list_campaigns", count=len(items), total=total)
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get(
    "/worker-health",
    response_model=WorkerHealthResponse,
    summary="Get campaign worker health",
    description=(
        "Returns background worker health status including "
        "last tick, pending counts, and rate limits."
    ),
)
async def get_worker_health(
    _current_user: ManagerOrAdminUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> WorkerHealthResponse:
    """Get campaign background worker health status.

    Validates: Requirement 32, 31
    """
    import json  # noqa: PLC0415
    import os  # noqa: PLC0415
    from datetime import datetime, timedelta, timezone  # noqa: PLC0415

    from sqlalchemy import func  # noqa: PLC0415

    from grins_platform.models.campaign import CampaignRecipient  # noqa: PLC0415
    from grins_platform.schemas.campaign import RateLimitInfo  # noqa: PLC0415
    from grins_platform.services.sms.rate_limit_tracker import (  # noqa: PLC0415
        SMSRateLimitTracker,
    )

    _endpoints.log_started("get_worker_health")

    # 1. Read last tick data from Redis
    last_tick_at: str | None = None
    last_tick_duration_ms: int | None = None
    last_tick_recipients_processed: int | None = None
    orphans_recovered = 0
    worker_status = "unknown"

    redis_url = os.environ.get("REDIS_URL")
    redis_client = None
    if redis_url:
        try:
            from redis.asyncio import Redis  # noqa: PLC0415

            redis_client = Redis.from_url(redis_url, decode_responses=True)
            raw = await redis_client.get("sms:worker:last_tick")
            if raw:
                tick_data = json.loads(raw)
                last_tick_at = tick_data.get("last_tick_at")
                last_tick_duration_ms = tick_data.get("last_tick_duration_ms")
                last_tick_recipients_processed = tick_data.get(
                    "last_tick_recipients_processed",
                )
                orphans_recovered = tick_data.get("orphans_recovered", 0)

                # Determine health: stale if last tick > 2 min ago
                if last_tick_at:
                    tick_time = datetime.fromisoformat(last_tick_at)
                    if datetime.now(timezone.utc) - tick_time < timedelta(minutes=2):
                        worker_status = "healthy"
                    else:
                        worker_status = "stale"
        except Exception:
            _endpoints.log_failed(
                "get_worker_health",
                reason="redis_read_failed",
            )
        finally:
            if redis_client:
                await redis_client.aclose()

    # 2. Count pending and sending recipients from DB
    pending_result = await session.execute(
        select(func.count()).where(CampaignRecipient.delivery_status == "pending"),
    )
    pending_count = pending_result.scalar() or 0

    sending_result = await session.execute(
        select(func.count()).where(CampaignRecipient.delivery_status == "sending"),
    )
    sending_count = sending_result.scalar() or 0

    # 3. Get rate limit state from tracker
    rate_limit_info = RateLimitInfo()
    provider_name = os.environ.get("SMS_PROVIDER", "callrail")
    account_id = os.environ.get("CALLRAIL_ACCOUNT_ID", "")

    rl_redis = None
    if redis_url:
        try:
            from redis.asyncio import Redis  # noqa: PLC0415

            rl_redis = Redis.from_url(redis_url, decode_responses=True)
            tracker = SMSRateLimitTracker(
                provider=provider_name,
                account_id=account_id,
                redis_client=rl_redis,
            )
            rl_result = await tracker.check()
            state = rl_result.state
            rate_limit_info = RateLimitInfo(
                hourly_allowed=state.hourly_allowed,
                hourly_used=state.hourly_used,
                hourly_remaining=state.hourly_remaining,
                daily_allowed=state.daily_allowed,
                daily_used=state.daily_used,
                daily_remaining=state.daily_remaining,
            )
        except Exception:
            _endpoints.log_failed(
                "get_worker_health",
                reason="rate_limit_read_failed",
            )
        finally:
            if rl_redis:
                await rl_redis.aclose()

    _endpoints.log_completed("get_worker_health", status=worker_status)
    return WorkerHealthResponse(
        last_tick_at=last_tick_at,
        last_tick_duration_ms=last_tick_duration_ms,
        last_tick_recipients_processed=last_tick_recipients_processed,
        pending_count=pending_count,
        sending_count=sending_count,
        orphans_recovered_last_hour=orphans_recovered,
        rate_limit=rate_limit_info,
        status=worker_status,
    )


@router.post(
    "/audience/preview",
    response_model=AudiencePreviewResponse,
    summary="Preview audience",
    description=(
        "Preview matched recipients for a target audience without creating a campaign."
    ),
)
async def preview_audience(
    target_audience: TargetAudience,
    _current_user: ManagerOrAdminUser,
    service: Annotated[CampaignService, Depends(get_campaign_service)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AudiencePreviewResponse:
    """Preview audience: total count, per-source breakdown, first 20 matches.

    Validates: Requirement 13.8
    """
    _endpoints.log_started("preview_audience")
    result = await service.preview_audience(
        session,
        target_audience.model_dump(exclude_none=True),
    )
    _endpoints.log_completed("preview_audience", total=result["total"])
    return AudiencePreviewResponse(**result)


@router.post(
    "/audience/csv",
    response_model=CsvUploadResult,
    status_code=status.HTTP_200_OK,
    summary="Upload CSV audience file",
    description=(
        "Upload a CSV file with phone, first_name, last_name columns. "
        "Returns upload_id and recipient breakdown. Ghost leads are NOT "
        "created until final campaign send."
    ),
)
async def upload_csv_audience(
    current_user: AdminUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    file: Annotated[UploadFile, File(description="CSV file with phone column")],
    staff_attestation_confirmed: Annotated[
        bool,
        Form(description="Staff confirmed consent attestation"),
    ] = False,
    attestation_text_shown: Annotated[
        str,
        Form(description="Verbatim attestation text displayed"),
    ] = "",
    attestation_version: Annotated[
        str,
        Form(description="Attestation form version"),
    ] = "CSV_ATTESTATION_V1",
) -> CsvUploadResult:
    """Upload and stage a CSV audience file.

    Validates: Requirements 13.9, 23.5, 25, 30, 31, 35, 41
    """
    import json as _json  # noqa: PLC0415
    import os  # noqa: PLC0415

    from grins_platform.services.sms.audit import (  # noqa: PLC0415
        log_csv_attestation_submitted,
    )
    from grins_platform.services.sms.csv_upload import (  # noqa: PLC0415
        match_recipients,
        parse_csv,
    )

    _endpoints.log_started("upload_csv_audience")

    if not staff_attestation_confirmed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Staff attestation must be confirmed before upload",
        )

    raw_bytes = await file.read()

    try:
        parse_result = parse_csv(raw_bytes)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    matched_customers, matched_leads, will_ghost = await match_recipients(
        session,
        parse_result.recipients,
    )

    # Stage parsed data + attestation in Redis (1h TTL) for send time
    redis_url = os.environ.get("REDIS_URL")
    if redis_url:
        try:
            from redis.asyncio import Redis  # noqa: PLC0415

            redis_client = Redis.from_url(redis_url, decode_responses=True)
            try:
                staged = {
                    "recipients": [
                        {
                            "phone": r.phone_e164,
                            "first_name": r.first_name,
                            "last_name": r.last_name,
                        }
                        for r in parse_result.recipients
                    ],
                    "attestation_text_shown": attestation_text_shown,
                    "attestation_version": attestation_version,
                }
                await redis_client.setex(
                    f"sms:csv_upload:{parse_result.upload_id}",
                    3600,
                    _json.dumps(staged),
                )
            finally:
                await redis_client.aclose()
        except Exception:
            _endpoints.log_failed(
                "upload_csv_audience",
                reason="redis_stage_failed",
            )

    # Emit audit event
    await log_csv_attestation_submitted(
        session,
        upload_id=parse_result.upload_id,
        actor_id=current_user.id,
        actor_role=current_user.role,
        phone_count=len(parse_result.recipients),
        attestation_version=attestation_version,
    )

    _endpoints.log_completed(
        "upload_csv_audience",
        upload_id=parse_result.upload_id,
        total_rows=parse_result.total_rows,
        recipients=len(parse_result.recipients),
        rejected=len(parse_result.rejected),
    )

    return CsvUploadResult(
        upload_id=parse_result.upload_id,
        total_rows=parse_result.total_rows,
        matched_customers=matched_customers,
        matched_leads=matched_leads,
        will_become_ghost_leads=will_ghost,
        rejected=len(parse_result.rejected),
        duplicates_collapsed=parse_result.duplicates_collapsed,
        rejected_rows=[
            CsvRejectedRow(
                row_number=r.row_number,
                phone_raw=r.phone_raw,
                reason=r.reason,
            )
            for r in parse_result.rejected
        ],
    )


@router.get(
    "/{campaign_id}",
    response_model=CampaignResponse,
    summary="Get campaign by ID",
)
async def get_campaign(
    campaign_id: UUID,
    _current_user: CurrentActiveUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CampaignResponse:
    """Get a single campaign by ID."""
    _endpoints.log_started("get_campaign", campaign_id=str(campaign_id))
    repo = CampaignRepository(session)
    campaign = await repo.get_by_id(campaign_id)
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campaign not found: {campaign_id}",
        )
    _endpoints.log_completed("get_campaign", campaign_id=str(campaign_id))
    return CampaignResponse.model_validate(campaign)


@router.delete(
    "/{campaign_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete campaign",
)
async def delete_campaign(
    campaign_id: UUID,
    _current_user: AdminUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> None:
    """Delete a campaign by ID."""
    _endpoints.log_started("delete_campaign", campaign_id=str(campaign_id))
    repo = CampaignRepository(session)
    deleted = await repo.delete(campaign_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campaign not found: {campaign_id}",
        )
    _endpoints.log_completed("delete_campaign", campaign_id=str(campaign_id))


# =============================================================================
# Campaign actions
# =============================================================================


@router.post(
    "/{campaign_id}/send",
    response_model=CampaignSendAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Enqueue campaign for sending",
    description=(
        "Enqueue campaign recipients for background delivery. "
        "Returns 202 immediately; background worker drains the queue."
    ),
)
async def send_campaign(
    campaign_id: UUID,
    _current_user: Annotated[Staff, Depends(require_campaign_send_authority)],
    service: Annotated[CampaignService, Depends(get_campaign_service)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CampaignSendAcceptedResponse:
    """Enqueue a campaign for background delivery.

    Validates: Requirements 8.4, 31, 41
    """
    _endpoints.log_started("send_campaign", campaign_id=str(campaign_id))
    try:
        cid, total = await service.enqueue_campaign_send(session, campaign_id)
    except CampaignNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except CampaignAlreadySentError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except NoRecipientsError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    else:
        await log_campaign_sent_initiated(
            session,
            campaign_id=campaign_id,
            actor_id=_current_user.id,
            actor_role=_current_user.role,
            recipient_count=total,
        )
        _endpoints.log_completed(
            "send_campaign",
            campaign_id=str(campaign_id),
            total_recipients=total,
        )
        return CampaignSendAcceptedResponse(
            campaign_id=cid,
            total_recipients=total,
        )


@router.post(
    "/{campaign_id}/cancel",
    response_model=CampaignCancelResult,
    summary="Cancel campaign",
    description=(
        "Cancel a campaign. Transitions all pending recipients to cancelled. "
        "Recipients already in sending state are allowed to finish naturally."
    ),
)
async def cancel_campaign_endpoint(
    campaign_id: UUID,
    current_user: ManagerOrAdminUser,
    service: Annotated[CampaignService, Depends(get_campaign_service)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CampaignCancelResult:
    """Cancel a campaign.

    Validates: Requirements 28, 31, 37, 41
    """
    _endpoints.log_started("cancel_campaign", campaign_id=str(campaign_id))
    try:
        cancelled = await service.cancel_campaign(campaign_id)
    except CampaignNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    else:
        await log_campaign_cancelled(
            session,
            campaign_id=campaign_id,
            actor_id=current_user.id,
            actor_role=current_user.role,
        )
        _endpoints.log_completed(
            "cancel_campaign",
            campaign_id=str(campaign_id),
            cancelled=cancelled,
        )
        return CampaignCancelResult(
            campaign_id=campaign_id,
            cancelled_recipients=cancelled,
        )


@router.get(
    "/{campaign_id}/stats",
    response_model=CampaignStats,
    summary="Get campaign stats",
    description="Get delivery statistics for a campaign.",
)
async def get_campaign_stats(
    campaign_id: UUID,
    _current_user: CurrentActiveUser,
    service: Annotated[CampaignService, Depends(get_campaign_service)],
) -> CampaignStats:
    """Get campaign delivery statistics.

    Validates: CRM Gap Closure Req 45.5
    """
    _endpoints.log_started("get_campaign_stats", campaign_id=str(campaign_id))
    try:
        result = await service.get_campaign_stats(campaign_id)
    except CampaignNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    else:
        _endpoints.log_completed(
            "get_campaign_stats",
            campaign_id=str(campaign_id),
        )
        return result
