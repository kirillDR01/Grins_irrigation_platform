"""Sheet submissions API endpoints.

Admin-only endpoints for viewing Google Sheet submissions,
triggering sync, and manually creating leads.

Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8, 11.4, 16.3
"""

from __future__ import annotations

from typing import Annotated, cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import (
    AsyncSession,  # noqa: TC002 - Required at runtime for FastAPI DI
)

from grins_platform.api.v1.auth_dependencies import (
    AdminUser,  # noqa: TC001 - Required at runtime for FastAPI DI
)
from grins_platform.api.v1.dependencies import get_db_session, get_sheets_service
from grins_platform.repositories.google_sheet_submission_repository import (
    GoogleSheetSubmissionRepository,
)
from grins_platform.log_config import DomainLogger, get_logger
from grins_platform.schemas.google_sheet_submission import (
    GoogleSheetSubmissionResponse,
    PaginatedSubmissionResponse,
    SubmissionListParams,
    SyncStatusResponse,
    TriggerSyncResponse,
)
from grins_platform.services.google_sheets_service import (
    GoogleSheetsService,  # noqa: TC001 - Required at runtime for FastAPI DI
)

router = APIRouter()
logger = get_logger(__name__)


# =============================================================================
# GET /sync-status — registered BEFORE /{id} to avoid path conflict
# =============================================================================


@router.get(  # type: ignore[untyped-decorator]
    "/sync-status",
    response_model=SyncStatusResponse,
    summary="Get poller sync status",
)
async def get_sync_status(
    _current_user: AdminUser,
    request: Request,
) -> SyncStatusResponse:
    """Return current poller sync status.

    Validates: Requirements 5.3
    """
    DomainLogger.api_event(logger, "get_sync_status", "started")
    poller = getattr(request.app.state, "sheets_poller", None)
    if poller is None:
        DomainLogger.api_event(logger, "get_sync_status", "completed", poller="none")
        return SyncStatusResponse(last_sync=None, is_running=False, last_error=None)
    result = cast("SyncStatusResponse", poller.sync_status)
    DomainLogger.api_event(
        logger,
        "get_sync_status",
        "completed",
        is_running=result.is_running,
    )
    return result


# =============================================================================
# POST /trigger-sync — registered BEFORE /{id} to avoid path conflict
# =============================================================================


@router.post(  # type: ignore[untyped-decorator]
    "/trigger-sync",
    response_model=TriggerSyncResponse,
    summary="Trigger immediate sync",
)
async def trigger_sync(
    _current_user: AdminUser,
    request: Request,
) -> TriggerSyncResponse:
    """Trigger an immediate poll cycle.

    Validates: Requirements 5.8
    """
    DomainLogger.api_event(logger, "trigger_sync", "started")
    poller = getattr(request.app.state, "sheets_poller", None)
    if poller is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Sheets poller is not running",
        )
    new_rows = await poller.trigger_sync()
    DomainLogger.api_event(
        logger,
        "trigger_sync",
        "completed",
        new_rows_imported=new_rows,
    )
    return TriggerSyncResponse(new_rows_imported=new_rows)


# =============================================================================
# POST /reset-sync — clear all submissions and reimport from scratch
# =============================================================================


@router.post(  # type: ignore[untyped-decorator]
    "/reset-sync",
    response_model=TriggerSyncResponse,
    summary="Reset and resync all submissions",
)
async def reset_sync(
    _current_user: AdminUser,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> TriggerSyncResponse:
    """Delete all existing submissions and reimport from Google Sheets.

    Useful when the sheet structure changes or stale data blocks new imports.
    """
    DomainLogger.api_event(logger, "reset_sync", "started")

    # Delete all existing submissions
    sub_repo = GoogleSheetSubmissionRepository(session)
    deleted = await sub_repo.delete_all()
    await session.commit()
    DomainLogger.api_event(logger, "reset_sync", "deleted_old", count=deleted)

    # Trigger a fresh sync
    poller = getattr(request.app.state, "sheets_poller", None)
    if poller is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Sheets poller is not running",
        )
    new_rows = await poller.trigger_sync()
    DomainLogger.api_event(
        logger,
        "reset_sync",
        "completed",
        deleted=deleted,
        new_rows_imported=new_rows,
    )
    return TriggerSyncResponse(new_rows_imported=new_rows)


# =============================================================================
# GET / — paginated list with filters
# =============================================================================


@router.get(  # type: ignore[untyped-decorator]
    "",
    response_model=PaginatedSubmissionResponse,
    summary="List sheet submissions",
)
async def list_submissions(
    _current_user: AdminUser,
    service: Annotated[GoogleSheetsService, Depends(get_sheets_service)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    processing_status: str | None = Query(default=None),
    client_type: str | None = Query(default=None),
    search: str | None = Query(default=None),
    sort_by: str = Query(default="imported_at"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
) -> PaginatedSubmissionResponse:
    """List submissions with filtering and pagination.

    Validates: Requirements 5.1
    """
    DomainLogger.api_event(logger, "list_submissions", "started", page=page)
    params = SubmissionListParams(
        page=page,
        page_size=page_size,
        processing_status=processing_status,
        client_type=client_type,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    result = await service.list_submissions(params, session)
    DomainLogger.api_event(
        logger,
        "list_submissions",
        "completed",
        total=result.total,
    )
    return result


# =============================================================================
# GET /{submission_id} — single submission detail
# =============================================================================


@router.get(  # type: ignore[untyped-decorator]
    "/{submission_id}",
    response_model=GoogleSheetSubmissionResponse,
    summary="Get submission by ID",
)
async def get_submission(
    submission_id: UUID,
    _current_user: AdminUser,
    service: Annotated[GoogleSheetsService, Depends(get_sheets_service)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> GoogleSheetSubmissionResponse:
    """Get a single submission by ID.

    Validates: Requirements 5.2
    """
    DomainLogger.api_event(
        logger,
        "get_submission",
        "started",
        submission_id=str(submission_id),
    )
    submission = await service.get_submission(submission_id, session)
    if submission is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submission not found",
        )
    DomainLogger.api_event(
        logger,
        "get_submission",
        "completed",
        submission_id=str(submission_id),
    )
    return cast(
        "GoogleSheetSubmissionResponse",
        GoogleSheetSubmissionResponse.model_validate(submission),
    )


# =============================================================================
# POST /{submission_id}/create-lead — manual lead creation
# =============================================================================


@router.post(  # type: ignore[untyped-decorator]
    "/{submission_id}/create-lead",
    response_model=GoogleSheetSubmissionResponse,
    summary="Create lead from submission",
)
async def create_lead_from_submission(
    submission_id: UUID,
    _current_user: AdminUser,
    service: Annotated[GoogleSheetsService, Depends(get_sheets_service)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> GoogleSheetSubmissionResponse:
    """Manually create a lead from a submission. Returns 409 if already linked.

    Validates: Requirements 5.4, 5.5
    """
    DomainLogger.api_event(
        logger,
        "create_lead",
        "started",
        submission_id=str(submission_id),
    )
    try:
        updated = await service.create_lead_from_submission(submission_id, session)
        await session.commit()
    except ValueError as e:
        error_msg = str(e)
        if "not found" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_msg,
            ) from e
        # "already has a linked lead" → 409
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=error_msg,
        ) from e
    DomainLogger.api_event(
        logger,
        "create_lead",
        "completed",
        submission_id=str(submission_id),
        lead_id=str(updated.lead_id) if updated.lead_id else None,
    )
    return cast(
        "GoogleSheetSubmissionResponse",
        GoogleSheetSubmissionResponse.model_validate(updated),
    )
