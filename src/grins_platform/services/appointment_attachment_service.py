"""AppointmentAttachmentService for file uploads on appointments.

Reuses the existing S3 presign pipeline from PhotoService (lead attachments)
to handle file uploads, listing, and deletion for appointment attachments.

Validates: april-16th-fixes-enhancements Requirement 10.5, 10.7
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import select

from grins_platform.log_config import LoggerMixin
from grins_platform.models.appointment_attachment import AppointmentAttachment
from grins_platform.schemas.appointment_attachment import (
    AttachmentListResponse,
    AttachmentUploadResponse,
)
from grins_platform.services.photo_service import PhotoService, UploadContext

if TYPE_CHECKING:
    from fastapi import UploadFile
    from sqlalchemy.ext.asyncio import AsyncSession

# Maximum file size: 25 MB
MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024


class AttachmentTooLargeError(Exception):
    """Raised when an uploaded file exceeds the 25 MB limit."""

    def __init__(self, file_size: int) -> None:
        self.file_size = file_size
        max_mb = MAX_FILE_SIZE_BYTES / (1024 * 1024)
        super().__init__(f"File size exceeds {max_mb:.0f} MB limit")


class AttachmentNotFoundError(Exception):
    """Raised when an attachment record is not found."""

    def __init__(self, attachment_id: UUID) -> None:
        self.attachment_id = attachment_id
        super().__init__(f"Attachment {attachment_id} not found")


class AppointmentAttachmentService(LoggerMixin):
    """Service for appointment file attachment operations.

    Reuses the existing S3 presign pipeline from PhotoService for
    upload, presigned URL generation, and deletion. Stores metadata
    in the appointment_attachments table.

    Attributes:
        session: SQLAlchemy async session for database operations.
        photo_service: PhotoService instance for S3 operations.

    Validates: april-16th-fixes-enhancements Requirement 10.5, 10.7
    """

    DOMAIN = "appointment_attachments"

    def __init__(
        self,
        session: AsyncSession,
        photo_service: PhotoService | None = None,
    ) -> None:
        """Initialize AppointmentAttachmentService.

        Args:
            session: SQLAlchemy AsyncSession for database operations.
            photo_service: Optional PhotoService instance. If not provided,
                a default instance is created.
        """
        super().__init__()
        self.session = session
        self.photo_service = photo_service or PhotoService()

    async def list_attachments(
        self,
        appointment_id: UUID,
        appointment_type: str,
    ) -> AttachmentListResponse:
        """List all attachments for an appointment with presigned URLs.

        Args:
            appointment_id: UUID of the appointment.
            appointment_type: Type of appointment ('job' or 'estimate').

        Returns:
            AttachmentListResponse with items and total count.

        Validates: Requirement 10.5
        """
        self.log_started(
            "list_attachments",
            appointment_id=str(appointment_id),
            appointment_type=appointment_type,
        )

        stmt = (
            select(AppointmentAttachment)
            .where(
                AppointmentAttachment.appointment_id == appointment_id,
                AppointmentAttachment.appointment_type == appointment_type,
            )
            .order_by(AppointmentAttachment.created_at.desc())
        )

        result = await self.session.execute(stmt)
        attachments = list(result.scalars().all())

        items: list[AttachmentUploadResponse] = []
        for att in attachments:
            # Images render inline (thumbnails); other types force download.
            disposition_name = (
                None
                if att.content_type.startswith("image/")
                else att.file_name
            )
            presigned_url = self.photo_service.generate_presigned_url(
                att.file_key,
                download_filename=disposition_name,
            )
            items.append(
                AttachmentUploadResponse(
                    id=att.id,
                    appointment_id=att.appointment_id,
                    appointment_type=att.appointment_type,
                    file_key=att.file_key,
                    file_name=att.file_name,
                    file_size=att.file_size,
                    content_type=att.content_type,
                    uploaded_by=att.uploaded_by,
                    created_at=att.created_at,
                    presigned_url=presigned_url,
                ),
            )

        self.log_completed(
            "list_attachments",
            appointment_id=str(appointment_id),
            count=len(items),
        )

        return AttachmentListResponse(items=items, total=len(items))

    async def upload_attachment(
        self,
        appointment_id: UUID,
        appointment_type: str,
        file: UploadFile,
        uploaded_by: UUID,
    ) -> AttachmentUploadResponse:
        """Upload a file attachment to an appointment.

        Reads the file, validates size (25 MB max), uploads to S3 via
        PhotoService, and creates a database record.

        Args:
            appointment_id: UUID of the appointment.
            appointment_type: Type of appointment ('job' or 'estimate').
            file: FastAPI UploadFile instance.
            uploaded_by: UUID of the staff member uploading.

        Returns:
            AttachmentUploadResponse with the created attachment data.

        Raises:
            AttachmentTooLargeError: If file exceeds 25 MB.

        Validates: Requirement 10.5, 10.7
        """
        self.log_started(
            "upload_attachment",
            appointment_id=str(appointment_id),
            appointment_type=appointment_type,
            uploaded_by=str(uploaded_by),
        )

        # Read file data
        file_data = await file.read()

        # Size check: 25 MB limit
        if len(file_data) > MAX_FILE_SIZE_BYTES:
            self.log_rejected(
                "upload_attachment",
                reason="file_too_large",
                file_size=len(file_data),
                max_size=MAX_FILE_SIZE_BYTES,
            )
            raise AttachmentTooLargeError(len(file_data))

        # Upload to S3 via PhotoService using LEAD_ATTACHMENT context
        # (same pipeline, 25 MB limit, supports common document types)
        upload_result = self.photo_service.upload_file(
            data=file_data,
            file_name=file.filename or "attachment",
            context=UploadContext.LEAD_ATTACHMENT,
        )

        # Create database record
        attachment = AppointmentAttachment(
            appointment_id=appointment_id,
            appointment_type=appointment_type,
            file_key=upload_result.file_key,
            file_name=upload_result.file_name,
            file_size=upload_result.file_size,
            content_type=upload_result.content_type,
            uploaded_by=uploaded_by,
        )
        self.session.add(attachment)
        await self.session.flush()
        await self.session.refresh(attachment)

        # Generate presigned URL for immediate use. Images stay inline so
        # AppointmentAttachments can render thumbnails; other types force
        # the browser to save-as-file instead of opening in a new tab.
        disposition_name = (
            None
            if attachment.content_type.startswith("image/")
            else attachment.file_name
        )
        presigned_url = self.photo_service.generate_presigned_url(
            attachment.file_key,
            download_filename=disposition_name,
        )

        self.log_completed(
            "upload_attachment",
            attachment_id=str(attachment.id),
            file_key=upload_result.file_key,
            file_size=upload_result.file_size,
        )

        return AttachmentUploadResponse(
            id=attachment.id,
            appointment_id=attachment.appointment_id,
            appointment_type=attachment.appointment_type,
            file_key=attachment.file_key,
            file_name=attachment.file_name,
            file_size=attachment.file_size,
            content_type=attachment.content_type,
            uploaded_by=attachment.uploaded_by,
            created_at=attachment.created_at,
            presigned_url=presigned_url,
        )

    async def delete_attachment(
        self,
        attachment_id: UUID,
        actor_id: UUID,
    ) -> None:
        """Delete an attachment record and its S3 object.

        Args:
            attachment_id: UUID of the attachment to delete.
            actor_id: UUID of the staff member performing the deletion.

        Raises:
            AttachmentNotFoundError: If the attachment does not exist.

        Validates: Requirement 10.5
        """
        self.log_started(
            "delete_attachment",
            attachment_id=str(attachment_id),
            actor_id=str(actor_id),
        )

        stmt = select(AppointmentAttachment).where(
            AppointmentAttachment.id == attachment_id,
        )
        result = await self.session.execute(stmt)
        attachment = result.scalar_one_or_none()

        if attachment is None:
            self.log_rejected(
                "delete_attachment",
                reason="not_found",
                attachment_id=str(attachment_id),
            )
            raise AttachmentNotFoundError(attachment_id)

        # Delete from S3
        self.photo_service.delete_file(attachment.file_key)

        # Delete database record
        await self.session.delete(attachment)
        await self.session.flush()

        self.log_completed(
            "delete_attachment",
            attachment_id=str(attachment_id),
            file_key=attachment.file_key,
        )
