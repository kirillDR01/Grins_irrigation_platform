"""Job confirmation response and reschedule request models.

Validates: CRM Changes Update 2 Req 24.6, 25.1
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import (
    JSON,
    UUID as PGUUID,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from grins_platform.database import Base

if TYPE_CHECKING:
    from grins_platform.models.appointment import Appointment
    from grins_platform.models.customer import Customer
    from grins_platform.models.job import Job
    from grins_platform.models.sent_message import SentMessage


class JobConfirmationResponse(Base):
    """Customer reply to an appointment confirmation SMS.

    Validates: CRM Changes Update 2 Req 24.6
    """

    __tablename__ = "job_confirmation_responses"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    job_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("jobs.id"),
        nullable=False,
    )
    appointment_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("appointments.id"),
        nullable=False,
    )
    sent_message_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("sent_messages.id"),
        nullable=True,
    )
    customer_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("customers.id"),
        nullable=False,
    )
    from_phone: Mapped[str] = mapped_column(String(20), nullable=False)
    reply_keyword: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    raw_reply_body: Mapped[str] = mapped_column(Text, nullable=False)
    provider_sid: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        server_default="pending",
    )
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    processed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    job: Mapped["Job"] = relationship("Job", lazy="selectin")
    appointment: Mapped["Appointment"] = relationship("Appointment", lazy="selectin")
    sent_message: Mapped[Optional["SentMessage"]] = relationship(
        "SentMessage",
        lazy="selectin",
    )
    customer: Mapped["Customer"] = relationship("Customer", lazy="selectin")

    __table_args__ = (
        Index("idx_confirmation_responses_appointment", "appointment_id"),
        Index("idx_confirmation_responses_status", "status"),
    )

    def __repr__(self) -> str:
        return (
            f"<JobConfirmationResponse(id={self.id}, "
            f"keyword='{self.reply_keyword}', status='{self.status}')>"
        )


class RescheduleRequest(Base):
    """Customer reschedule request from Y/R/C flow.

    Validates: CRM Changes Update 2 Req 25.1
    """

    __tablename__ = "reschedule_requests"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    job_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("jobs.id"),
        nullable=False,
    )
    appointment_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("appointments.id"),
        nullable=False,
    )
    customer_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("customers.id"),
        nullable=False,
    )
    original_reply_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("job_confirmation_responses.id"),
        nullable=True,
    )
    requested_alternatives: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
    )
    raw_alternatives_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        server_default="open",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    job: Mapped["Job"] = relationship("Job", lazy="selectin")
    appointment: Mapped["Appointment"] = relationship("Appointment", lazy="selectin")
    customer: Mapped["Customer"] = relationship("Customer", lazy="selectin")
    original_reply: Mapped[Optional["JobConfirmationResponse"]] = relationship(
        "JobConfirmationResponse",
        lazy="selectin",
    )

    __table_args__ = (
        Index("idx_reschedule_requests_appointment", "appointment_id"),
        Index("idx_reschedule_requests_status", "status"),
    )

    def __repr__(self) -> str:
        return f"<RescheduleRequest(id={self.id}, status='{self.status}')>"
