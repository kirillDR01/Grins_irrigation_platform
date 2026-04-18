"""Appointment attachment model for file uploads on appointments.

Supports the Calendar Enrichment feature where staff can attach files
(photos, PDFs, documents) to both job and estimate appointments. Files
are stored in S3 with metadata tracked in this table.

Validates: april-16th-fixes-enhancements Requirement 6
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from grins_platform.database import Base


class AppointmentAttachment(Base):
    """File attachment linked to a job or estimate appointment.

    Validates: april-16th-fixes-enhancements Requirement 6
    """

    __tablename__ = "appointment_attachments"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    appointment_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=False,
    )
    appointment_type: Mapped[str] = mapped_column(String(20), nullable=False)
    file_key: Mapped[str] = mapped_column(String(500), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    uploaded_by: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("staff.id"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    uploader: Mapped["Staff"] = relationship("Staff", lazy="selectin")  # type: ignore[name-defined]  # noqa: F821

    __table_args__ = (
        Index(
            "idx_appointment_attachments_appointment",
            "appointment_type",
            "appointment_id",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<AppointmentAttachment(id={self.id}, "
            f"appointment_id={self.appointment_id}, "
            f"file_name='{self.file_name}')>"
        )
