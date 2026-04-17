"""
Lead API endpoints.

This module provides REST API endpoints for lead management including
public form submission (no auth), admin CRUD, status workflow,
conversion to customer, bulk outreach, and attachment management.

Validates: Requirement 1.10, 5.10, 7.9, 12.2, 12.3, 13.1, 14.1, 15.2, 15.3, 15.4
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,  # noqa: TC002 - Required at runtime for FastAPI DI
)

from grins_platform.api.v1.auth_dependencies import (
    CurrentActiveUser,  # noqa: TC001 - Required at runtime for FastAPI DI
)
from grins_platform.api.v1.dependencies import get_db_session
from grins_platform.log_config import LoggerMixin
from grins_platform.models.enums import LeadSituation, LeadStatus
from grins_platform.models.lead import Lead
from grins_platform.models.lead_attachment import LeadAttachment
from grins_platform.repositories.customer_repository import CustomerRepository
from grins_platform.repositories.job_repository import JobRepository
from grins_platform.repositories.lead_repository import LeadRepository
from grins_platform.repositories.property_repository import PropertyRepository
from grins_platform.repositories.service_offering_repository import (
    ServiceOfferingRepository,
)
from grins_platform.repositories.staff_repository import StaffRepository
from grins_platform.schemas.lead import (
    BulkOutreachRequest,
    BulkOutreachSummary,
    FromCallSubmission,
    LeadConversionRequest,
    LeadConversionResponse,
    LeadListParams,
    LeadMetricsBySourceResponse,
    LeadMoveResponse,
    LeadResponse,
    LeadSubmission,
    LeadSubmissionResponse,
    LeadUpdate,
    ManualLeadCreate,
    PaginatedFollowUpQueueResponse,
    PaginatedLeadResponse,
)
from grins_platform.schemas.lead_attachment import (
    LeadAttachmentListResponse,
    LeadAttachmentResponse,
)
from grins_platform.services.compliance_service import ComplianceService
from grins_platform.services.customer_service import CustomerService
from grins_platform.services.email_service import EmailService
from grins_platform.services.job_service import JobService
from grins_platform.services.lead_service import (
    LeadDuplicateFoundError,
    LeadService,
)
from grins_platform.services.photo_service import PhotoService, UploadContext
from grins_platform.services.sms_service import SMSService

router = APIRouter()


class LeadEndpoints(LoggerMixin):
    """Lead API endpoint handlers with logging."""

    DOMAIN = "api"


_endpoints = LeadEndpoints()


async def _get_lead_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> LeadService:
    """Build LeadService with all dependencies.

    Args:
        session: Database session from dependency injection

    Returns:
        LeadService instance
    """
    lead_repository = LeadRepository(session=session)
    customer_repository = CustomerRepository(session=session)
    property_repository = PropertyRepository(session=session)
    service_repository = ServiceOfferingRepository(session=session)
    job_repository = JobRepository(session=session)
    staff_repository = StaffRepository(session=session)

    customer_service = CustomerService(repository=customer_repository)
    job_service = JobService(
        job_repository=job_repository,
        customer_repository=customer_repository,
        property_repository=property_repository,
        service_repository=service_repository,
    )

    return LeadService(
        lead_repository=lead_repository,
        customer_service=customer_service,
        job_service=job_service,
        staff_repository=staff_repository,
        sms_service=SMSService(session=session),
        email_service=EmailService(),
        compliance_service=ComplianceService(session=session),
    )


# =============================================================================
# POST /api/v1/leads — Public (no auth)
# =============================================================================


@router.post(  # type: ignore[untyped-decorator]
    "",
    response_model=LeadSubmissionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a lead from public form",
    description=(
        "Public endpoint for website form submissions. No authentication required."
    ),
)
async def submit_lead(
    data: LeadSubmission,
    background_tasks: BackgroundTasks,
    service: Annotated[LeadService, Depends(_get_lead_service)],
) -> LeadSubmissionResponse:
    """Submit a lead from the public website form.

    Validates: Requirement 1, 2, 3
    """
    _endpoints.log_started(
        "submit_lead",
        source_site=data.source_site,
        honeypot_present=bool(getattr(data, "hp_field", None)),
    )

    # Per E-BUG-B — add structured logging around the handler so the
    # marketing-site dev can correlate silent failures from the browser.
    # ``X-Request-ID`` (set by the FastAPI middleware) shows up on every
    # emitted line via log_config's context binding.
    try:
        result = await service.submit_lead(data, background_tasks=background_tasks)
    except Exception as exc:  # noqa: BLE001 — re-raised below, purely for observability
        _endpoints.log_failed(
            "submit_lead",
            error=exc,
            source_site=data.source_site,
            exception_type=type(exc).__name__,
        )
        raise

    _endpoints.log_completed(
        "submit_lead",
        source_site=data.source_site,
        lead_id=str(result.lead_id) if result.lead_id else "honeypot",
        honeypot_triggered=result.lead_id is None,
    )
    return result


# =============================================================================
# POST /api/v1/leads/from-call — Admin auth required
# =============================================================================


@router.post(  # type: ignore[untyped-decorator]
    "/from-call",
    response_model=LeadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create lead from phone call",
    description="Admin-only endpoint for creating leads from inbound calls.",
)
async def create_from_call(
    data: FromCallSubmission,
    _current_user: CurrentActiveUser,
    service: Annotated[LeadService, Depends(_get_lead_service)],
) -> LeadResponse:
    """Create a lead from an inbound phone call.

    Validates: Requirement 45.4, 45.5
    """
    _endpoints.log_started("create_from_call")

    result = await service.create_from_call(data)

    _endpoints.log_completed("create_from_call", lead_id=str(result.id))
    return result


# =============================================================================
# POST /api/v1/leads/manual — Admin auth required
# =============================================================================


@router.post(  # type: ignore[untyped-decorator]
    "/manual",
    response_model=LeadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create lead manually",
    description="Admin-only endpoint for creating leads manually via CRM interface.",
)
async def create_manual_lead(
    data: ManualLeadCreate,
    _current_user: CurrentActiveUser,
    service: Annotated[LeadService, Depends(_get_lead_service)],
) -> LeadResponse:
    """Create a lead manually from the CRM interface.

    Validates: Requirement 7.1-7.5
    """
    _endpoints.log_started("create_manual_lead")

    result = await service.create_manual_lead(data)

    _endpoints.log_completed("create_manual_lead", lead_id=str(result.id))
    return result


# =============================================================================
# GET /api/v1/leads — Admin auth required
# =============================================================================


@router.get(  # type: ignore[untyped-decorator]
    "",
    response_model=PaginatedLeadResponse,
    summary="List leads",
    description=(
        "List leads with filtering, sorting, and pagination. Admin auth required."
    ),
)
async def list_leads(
    _current_user: CurrentActiveUser,
    service: Annotated[LeadService, Depends(_get_lead_service)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status_filter: str | None = Query(default=None, alias="status"),
    situation: str | None = Query(default=None),
    search: str | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    lead_source: str | None = Query(
        default=None,
        description="Comma-separated lead sources",
    ),
    intake_tag: str | None = Query(
        default=None,
        description="Intake tag filter",
    ),
    sort_by: str = Query(default="created_at"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
) -> PaginatedLeadResponse:
    """List leads with filtering and pagination.

    Validates: Requirement 5.1-5.5, 45.3, 48.4
    """
    _endpoints.log_started("list_leads", page=page, page_size=page_size)

    # Parse comma-separated lead_source into list
    lead_source_list: list[str] | None = None
    if lead_source:
        lead_source_list = [s.strip() for s in lead_source.split(",") if s.strip()]

    params = LeadListParams(
        page=page,
        page_size=page_size,
        status=LeadStatus(status_filter) if status_filter else None,
        situation=LeadSituation(situation) if situation else None,
        search=search,
        date_from=datetime.fromisoformat(date_from) if date_from else None,
        date_to=datetime.fromisoformat(date_to) if date_to else None,
        lead_source=lead_source_list,
        intake_tag=intake_tag,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    result = await service.list_leads(params)

    _endpoints.log_completed("list_leads", total=result.total)
    return result


# =============================================================================
# GET /api/v1/leads/follow-up-queue — Admin auth required
# =============================================================================


@router.get(  # type: ignore[untyped-decorator]
    "/follow-up-queue",
    response_model=PaginatedFollowUpQueueResponse,
    summary="Get follow-up queue",
    description=(
        "Paginated queue of leads tagged for follow-up with active status. "
        "Admin auth required."
    ),
)
async def get_follow_up_queue(
    _current_user: CurrentActiveUser,
    service: Annotated[LeadService, Depends(_get_lead_service)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaginatedFollowUpQueueResponse:
    """Get follow-up queue.

    Validates: Requirement 50.1, 50.2, 50.3, 50.4
    """
    _endpoints.log_started("get_follow_up_queue", page=page, page_size=page_size)

    result = await service.get_follow_up_queue(page=page, page_size=page_size)

    _endpoints.log_completed("get_follow_up_queue", total=result.total)
    return result


# =============================================================================
# GET /api/v1/leads/metrics/by-source — Admin auth required
# =============================================================================


@router.get(  # type: ignore[untyped-decorator]
    "/metrics/by-source",
    response_model=LeadMetricsBySourceResponse,
    summary="Get lead metrics by source",
    description=(
        "Returns lead counts grouped by lead_source for a configurable date range. "
        "Defaults to trailing 30 days. Admin auth required."
    ),
)
async def get_lead_metrics_by_source(
    _current_user: CurrentActiveUser,
    service: Annotated[LeadService, Depends(_get_lead_service)],
    date_from: datetime | None = Query(
        default=None,
        description="Start date (ISO 8601)",
    ),
    date_to: datetime | None = Query(
        default=None,
        description="End date (ISO 8601)",
    ),
) -> LeadMetricsBySourceResponse:
    """Get lead metrics grouped by source.

    Validates: Requirement 61.3
    """
    _endpoints.log_started("get_lead_metrics_by_source")

    result = await service.get_metrics_by_source(
        date_from=date_from,
        date_to=date_to,
    )

    _endpoints.log_completed("get_lead_metrics_by_source", total=result.total)
    return result


# =============================================================================
# POST /api/v1/leads/bulk-outreach — Admin auth required
# =============================================================================


@router.post(  # type: ignore[untyped-decorator]
    "/bulk-outreach",
    response_model=BulkOutreachSummary,
    summary="Bulk SMS/email outreach to leads",
    description=(
        "Send bulk outreach messages to multiple leads. "
        "Respects SMS consent and contact preferences. Admin auth required."
    ),
)
async def bulk_outreach(
    data: BulkOutreachRequest,
    _current_user: CurrentActiveUser,
    service: Annotated[LeadService, Depends(_get_lead_service)],
) -> BulkOutreachSummary:
    """Send bulk outreach to multiple leads.

    Validates: Requirement 14.1
    """
    _endpoints.log_started(
        "bulk_outreach",
        lead_count=len(data.lead_ids),
        channel=data.channel,
    )

    result = await service.bulk_outreach(
        lead_ids=data.lead_ids,
        template=data.template,
        channel=data.channel,
    )

    _endpoints.log_completed(
        "bulk_outreach",
        sent=result.sent_count,
        skipped=result.skipped_count,
        failed=result.failed_count,
    )
    return result


# =============================================================================
# GET /api/v1/leads/{lead_id} — Admin auth required
# =============================================================================


@router.get(  # type: ignore[untyped-decorator]
    "/{lead_id}",
    response_model=LeadResponse,
    summary="Get lead by ID",
    description="Retrieve a lead by its unique identifier. Admin auth required.",
)
async def get_lead(
    lead_id: UUID,
    _current_user: CurrentActiveUser,
    service: Annotated[LeadService, Depends(_get_lead_service)],
) -> LeadResponse:
    """Get lead by ID.

    Validates: Requirement 5.8
    """
    _endpoints.log_started("get_lead", lead_id=str(lead_id))

    result = await service.get_lead(lead_id)

    _endpoints.log_completed("get_lead", lead_id=str(lead_id))
    return result


# =============================================================================
# PATCH /api/v1/leads/{lead_id} — Admin auth required
# =============================================================================


@router.patch(  # type: ignore[untyped-decorator]
    "/{lead_id}",
    response_model=LeadResponse,
    summary="Update lead",
    description="Update lead status, assignment, or notes. Admin auth required.",
)
async def update_lead(
    lead_id: UUID,
    data: LeadUpdate,
    _current_user: CurrentActiveUser,
    service: Annotated[LeadService, Depends(_get_lead_service)],
) -> LeadResponse:
    """Update a lead.

    Validates: Requirement 5.6-5.7, 6
    """
    _endpoints.log_started("update_lead", lead_id=str(lead_id))

    result = await service.update_lead(lead_id, data)

    _endpoints.log_completed("update_lead", lead_id=str(lead_id))
    return result


# =============================================================================
# POST /api/v1/leads/{lead_id}/convert — Admin auth required
# =============================================================================


@router.post(  # type: ignore[untyped-decorator]
    "/{lead_id}/convert",
    response_model=LeadConversionResponse,
    summary="Convert lead to customer",
    description=(
        "Convert a lead to a customer and optionally create a job. Admin auth required."
    ),
    responses={
        409: {
            "description": (
                "Duplicate customer found (Tier-1 phone/email match). "
                "Retry with ``force=true`` to override."
            ),
        },
    },
)
async def convert_lead(
    lead_id: UUID,
    data: LeadConversionRequest,
    _current_user: CurrentActiveUser,
    service: Annotated[LeadService, Depends(_get_lead_service)],
) -> LeadConversionResponse:
    """Convert a lead to a customer.

    Validates: Requirement 7, CR-6 (bughunt 2026-04-16)
    """
    _endpoints.log_started("convert_lead", lead_id=str(lead_id))

    try:
        result = await service.convert_lead(lead_id, data)
    except LeadDuplicateFoundError as exc:
        _endpoints.log_rejected(
            "convert_lead",
            reason="duplicate_found",
            lead_id=str(lead_id),
            duplicate_count=len(exc.duplicates),
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "duplicate_found",
                "lead_id": str(exc.lead_id),
                "phone": exc.phone,
                "email": exc.email,
                "duplicates": [d.model_dump(mode="json") for d in exc.duplicates],
            },
        ) from exc

    _endpoints.log_completed(
        "convert_lead",
        lead_id=str(lead_id),
        customer_id=str(result.customer_id),
    )
    return result


# =============================================================================
# DELETE /api/v1/leads/{lead_id} — Admin auth required
# =============================================================================


@router.delete(  # type: ignore[untyped-decorator]
    "/{lead_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete lead",
    description="Delete a lead record. Admin auth required.",
)
async def delete_lead(
    lead_id: UUID,
    _current_user: CurrentActiveUser,
    service: Annotated[LeadService, Depends(_get_lead_service)],
) -> None:
    """Delete a lead.

    Validates: Requirement 5.9
    """
    _endpoints.log_started("delete_lead", lead_id=str(lead_id))

    await service.delete_lead(lead_id)

    _endpoints.log_completed("delete_lead", lead_id=str(lead_id))


# =============================================================================
# POST /api/v1/leads/{lead_id}/move-to-jobs — Admin auth required
# =============================================================================


@router.post(  # type: ignore[untyped-decorator]
    "/{lead_id}/move-to-jobs",
    response_model=LeadMoveResponse,
    summary="Move lead to Jobs",
    description=(
        "Auto-generate customer if needed, create a Job with TO_BE_SCHEDULED, "
        "and remove the lead from the Leads list. Admin auth required. "
        "If the lead's situation maps to requires_estimate and force=false, "
        "returns requires_estimate_warning=true instead of creating the job."
    ),
)
async def move_lead_to_jobs(
    lead_id: UUID,
    _current_user: CurrentActiveUser,
    service: Annotated[LeadService, Depends(_get_lead_service)],
    force: bool = False,
) -> LeadMoveResponse:
    """Move a lead to the Jobs tab.

    Validates: CRM2 Req 9.2, 12.1, Smoothing Req 6.1, 6.2
    """
    _endpoints.log_started("move_lead_to_jobs", lead_id=str(lead_id), force=force)
    result = await service.move_to_jobs(lead_id, force=force)
    _endpoints.log_completed("move_lead_to_jobs", lead_id=str(lead_id))
    return result


# =============================================================================
# POST /api/v1/leads/{lead_id}/move-to-sales — Admin auth required
# =============================================================================


@router.post(  # type: ignore[untyped-decorator]
    "/{lead_id}/move-to-sales",
    response_model=LeadMoveResponse,
    summary="Move lead to Sales",
    description=(
        "Auto-generate customer if needed, create a SalesEntry with "
        "schedule_estimate status, and remove the lead from the Leads list. "
        "Admin auth required."
    ),
)
async def move_lead_to_sales(
    lead_id: UUID,
    _current_user: CurrentActiveUser,
    service: Annotated[LeadService, Depends(_get_lead_service)],
) -> LeadMoveResponse:
    """Move a lead to the Sales tab.

    Validates: CRM2 Req 9.2, 12.2
    """
    _endpoints.log_started("move_lead_to_sales", lead_id=str(lead_id))
    result = await service.move_to_sales(lead_id)
    _endpoints.log_completed("move_lead_to_sales", lead_id=str(lead_id))
    return result


# =============================================================================
# PUT /api/v1/leads/{lead_id}/contacted — Admin auth required
# =============================================================================


@router.put(  # type: ignore[untyped-decorator]
    "/{lead_id}/contacted",
    response_model=LeadResponse,
    summary="Mark lead as contacted",
    description=(
        "Set lead status to Contacted (Awaiting Response) and update "
        "last_contacted_at timestamp. Admin auth required."
    ),
)
async def mark_lead_contacted(
    lead_id: UUID,
    _current_user: CurrentActiveUser,
    service: Annotated[LeadService, Depends(_get_lead_service)],
) -> LeadResponse:
    """Mark a lead as contacted.

    Validates: CRM2 Req 11.1, 11.2
    """
    _endpoints.log_started("mark_lead_contacted", lead_id=str(lead_id))
    result = await service.mark_contacted(lead_id)
    _endpoints.log_completed("mark_lead_contacted", lead_id=str(lead_id))
    return result


# =============================================================================
# POST /api/v1/leads/{lead_id}/attachments — Admin auth required
# =============================================================================


@router.post(  # type: ignore[untyped-decorator]
    "/{lead_id}/attachments",
    response_model=LeadAttachmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload lead attachment",
    description=(
        "Upload a file attachment to a lead. "
        "Supports PDF, DOCX, JPEG, PNG (max 25MB). Admin auth required."
    ),
)
async def upload_lead_attachment(
    lead_id: UUID,
    _current_user: CurrentActiveUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    file: Annotated[UploadFile, File(description="File to upload")],
    attachment_type: Annotated[
        str,
        Form(description="Attachment type: ESTIMATE, CONTRACT, or OTHER"),
    ] = "OTHER",
) -> LeadAttachmentResponse:
    """Upload an attachment to a lead.

    Validates: Requirement 15.2
    """
    _endpoints.log_started(
        "upload_lead_attachment",
        lead_id=str(lead_id),
        attachment_type=attachment_type,
    )

    # Validate attachment_type
    valid_types = {"ESTIMATE", "CONTRACT", "OTHER"}
    if attachment_type.upper() not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"attachment_type must be one of: {', '.join(sorted(valid_types))}",
        )

    # Verify lead exists
    result = await session.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lead {lead_id} not found",
        )

    # Read file data
    file_data = await file.read()
    if not file_data:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Empty file",
        )

    # Upload via PhotoService
    photo_service = PhotoService()
    try:
        upload_result = photo_service.upload_file(
            data=file_data,
            file_name=file.filename or "attachment",
            context=UploadContext.LEAD_ATTACHMENT,
        )
    except ValueError as e:
        # bughunt M-16: size cap exceeded → 413 Payload Too Large.
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=str(e),
        ) from e
    except TypeError as e:
        # bughunt M-16: MIME not in allow-list → 415 Unsupported Media Type.
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=str(e),
        ) from e

    # Create DB record
    attachment = LeadAttachment(
        lead_id=lead_id,
        file_key=upload_result.file_key,
        file_name=upload_result.file_name,
        file_size=upload_result.file_size,
        content_type=upload_result.content_type,
        attachment_type=attachment_type.upper(),
    )
    session.add(attachment)
    await session.commit()
    await session.refresh(attachment)

    # Generate pre-signed URL
    download_url = photo_service.generate_presigned_url(attachment.file_key)

    _endpoints.log_completed(
        "upload_lead_attachment",
        lead_id=str(lead_id),
        attachment_id=str(attachment.id),
        file_key=upload_result.file_key,
    )

    return LeadAttachmentResponse(
        id=attachment.id,
        lead_id=attachment.lead_id,
        file_key=attachment.file_key,
        file_name=attachment.file_name,
        file_size=attachment.file_size,
        content_type=attachment.content_type,
        attachment_type=attachment.attachment_type,
        download_url=download_url,
        created_at=attachment.created_at,
    )


# =============================================================================
# GET /api/v1/leads/{lead_id}/attachments — Admin auth required
# =============================================================================


@router.get(  # type: ignore[untyped-decorator]
    "/{lead_id}/attachments",
    response_model=LeadAttachmentListResponse,
    summary="List lead attachments",
    description=(
        "List all attachments for a lead with pre-signed download URLs. "
        "Admin auth required."
    ),
)
async def list_lead_attachments(
    lead_id: UUID,
    _current_user: CurrentActiveUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> LeadAttachmentListResponse:
    """List attachments for a lead.

    Validates: Requirement 15.3
    """
    _endpoints.log_started("list_lead_attachments", lead_id=str(lead_id))

    # Verify lead exists
    lead_result = await session.execute(select(Lead).where(Lead.id == lead_id))
    lead = lead_result.scalar_one_or_none()
    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lead {lead_id} not found",
        )

    # Query attachments
    stmt = (
        select(LeadAttachment)
        .where(LeadAttachment.lead_id == lead_id)
        .order_by(LeadAttachment.created_at.desc())
    )
    result = await session.execute(stmt)
    attachments = list(result.scalars().all())

    # Generate pre-signed URLs
    photo_service = PhotoService()
    items: list[LeadAttachmentResponse] = []
    for att in attachments:
        download_url = photo_service.generate_presigned_url(att.file_key)
        items.append(
            LeadAttachmentResponse(
                id=att.id,
                lead_id=att.lead_id,
                file_key=att.file_key,
                file_name=att.file_name,
                file_size=att.file_size,
                content_type=att.content_type,
                attachment_type=att.attachment_type,
                download_url=download_url,
                created_at=att.created_at,
            ),
        )

    _endpoints.log_completed(
        "list_lead_attachments",
        lead_id=str(lead_id),
        count=len(items),
    )

    return LeadAttachmentListResponse(items=items, total=len(items))


# =============================================================================
# DELETE /api/v1/leads/{lead_id}/attachments/{attachment_id} — Admin auth
# =============================================================================


@router.delete(  # type: ignore[untyped-decorator]
    "/{lead_id}/attachments/{attachment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete lead attachment",
    description="Delete a lead attachment and its S3 object. Admin auth required.",
)
async def delete_lead_attachment(
    lead_id: UUID,
    attachment_id: UUID,
    _current_user: CurrentActiveUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> None:
    """Delete a lead attachment.

    Validates: Requirement 15.4
    """
    _endpoints.log_started(
        "delete_lead_attachment",
        lead_id=str(lead_id),
        attachment_id=str(attachment_id),
    )

    # Find attachment
    stmt = select(LeadAttachment).where(
        LeadAttachment.id == attachment_id,
        LeadAttachment.lead_id == lead_id,
    )
    result = await session.execute(stmt)
    attachment = result.scalar_one_or_none()
    if not attachment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Attachment {attachment_id} not found for lead {lead_id}",
        )

    # Delete from S3
    photo_service = PhotoService()
    try:
        photo_service.delete_file(attachment.file_key)
    except Exception:
        _endpoints.log_failed(
            "delete_lead_attachment",
            lead_id=str(lead_id),
            attachment_id=str(attachment_id),
            error="S3 delete failed, proceeding with DB cleanup",
        )

    # Delete DB record
    await session.delete(attachment)
    await session.commit()

    _endpoints.log_completed(
        "delete_lead_attachment",
        lead_id=str(lead_id),
        attachment_id=str(attachment_id),
    )
