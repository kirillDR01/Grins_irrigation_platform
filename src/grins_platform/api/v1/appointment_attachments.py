"""
Appointment attachments API endpoints.

This module provides REST API endpoints for managing file attachments
on appointments (job or estimate), including listing, uploading, and
deleting attachments.

Validates: april-16th-fixes-enhancements Requirement 10.5, 10.7
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy.ext.asyncio import (
    AsyncSession,  # noqa: TC002 - Required at runtime for FastAPI DI
)

from grins_platform.api.v1.auth_dependencies import (
    CurrentActiveUser,  # noqa: TC001 - Required at runtime for FastAPI DI
)
from grins_platform.api.v1.dependencies import get_db_session
from grins_platform.log_config import LoggerMixin
from grins_platform.schemas.appointment_attachment import (
    AttachmentListResponse,
    AttachmentUploadResponse,
)
from grins_platform.services.appointment_attachment_service import (
    AppointmentAttachmentService,
    AttachmentNotFoundError,
    AttachmentTooLargeError,
)

router = APIRouter()


class AttachmentEndpoints(LoggerMixin):
    """Appointment attachment API endpoint handlers with logging."""

    DOMAIN = "api"


_endpoints = AttachmentEndpoints()


async def _get_attachment_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AppointmentAttachmentService:
    """Build AppointmentAttachmentService dependency.

    Args:
        session: Database session from dependency injection.

    Returns:
        AppointmentAttachmentService instance.
    """
    return AppointmentAttachmentService(session=session)


# =============================================================================
# GET /api/v1/appointments/{appointment_id}/attachments
# =============================================================================


@router.get(
    "/appointments/{appointment_id}/attachments",
    response_model=AttachmentListResponse,
    summary="List appointment attachments",
    description=(
        "List all file attachments for an appointment with presigned download URLs."
    ),
)
async def list_attachments(
    appointment_id: UUID,
    _current_user: CurrentActiveUser,
    service: Annotated[AppointmentAttachmentService, Depends(_get_attachment_service)],
    appointment_type: str = Query(
        default="job",
        description="Appointment type: 'job' or 'estimate'",
    ),
) -> AttachmentListResponse:
    """List attachments for an appointment.

    Validates: Requirement 10.5
    """
    _endpoints.log_started(
        "list_attachments",
        appointment_id=str(appointment_id),
        appointment_type=appointment_type,
    )
    result = await service.list_attachments(
        appointment_id=appointment_id,
        appointment_type=appointment_type,
    )
    _endpoints.log_completed(
        "list_attachments",
        appointment_id=str(appointment_id),
        count=result.total,
    )
    return result


# =============================================================================
# POST /api/v1/appointments/{appointment_id}/attachments
# =============================================================================


@router.post(
    "/appointments/{appointment_id}/attachments",
    response_model=AttachmentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload appointment attachment",
    description="Upload a file attachment to an appointment. Max 25 MB, any MIME type.",
)
async def upload_attachment(
    appointment_id: UUID,
    current_user: CurrentActiveUser,
    service: Annotated[AppointmentAttachmentService, Depends(_get_attachment_service)],
    file: Annotated[UploadFile, File(description="File to upload")],
    appointment_type: str = Query(
        default="job",
        description="Appointment type: 'job' or 'estimate'",
    ),
) -> AttachmentUploadResponse:
    """Upload a file attachment to an appointment.

    Validates: Requirement 10.5, 10.7
    """
    _endpoints.log_started(
        "upload_attachment",
        appointment_id=str(appointment_id),
        appointment_type=appointment_type,
        filename=file.filename,
    )
    try:
        result = await service.upload_attachment(
            appointment_id=appointment_id,
            appointment_type=appointment_type,
            file=file,
            uploaded_by=current_user.id,
        )
    except AttachmentTooLargeError as e:
        _endpoints.log_rejected(
            "upload_attachment",
            reason="file_too_large",
            file_size=e.file_size,
        )
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File size exceeds 25 MB limit",
        ) from e

    _endpoints.log_completed(
        "upload_attachment",
        attachment_id=str(result.id),
        appointment_id=str(appointment_id),
    )
    return result


# =============================================================================
# DELETE /api/v1/appointments/{appointment_id}/attachments/{attachment_id}
# =============================================================================


@router.delete(
    "/appointments/{appointment_id}/attachments/{attachment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete appointment attachment",
    description="Delete a file attachment from an appointment.",
)
async def delete_attachment(
    appointment_id: UUID,
    attachment_id: UUID,
    current_user: CurrentActiveUser,
    service: Annotated[AppointmentAttachmentService, Depends(_get_attachment_service)],
) -> None:
    """Delete an appointment attachment.

    Validates: Requirement 10.5
    """
    _endpoints.log_started(
        "delete_attachment",
        appointment_id=str(appointment_id),
        attachment_id=str(attachment_id),
    )
    try:
        await service.delete_attachment(
            attachment_id=attachment_id,
            actor_id=current_user.id,
        )
    except AttachmentNotFoundError as e:
        _endpoints.log_rejected("delete_attachment", reason="not_found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Attachment {attachment_id} not found",
        ) from e

    _endpoints.log_completed(
        "delete_attachment",
        attachment_id=str(attachment_id),
    )
