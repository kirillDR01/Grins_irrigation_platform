"""Sent Message model for tracking SMS communications.

Supports delivery status tracking and Twilio integration.

Validates: AI Assistant Requirements 7.8, 12.4
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import (
    TIMESTAMP,
    UUID as PGUUID,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from grins_platform.database import Base


class SentMessage(Base):
    """Model for tracking SMS communications sent to customers."""

    __tablename__ = "sent_messages"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default="gen_random_uuid()",
    )
    customer_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("customers.id", name="fk_sent_messages_customer_id"),
        nullable=False,
    )
    job_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("jobs.id", name="fk_sent_messages_job_id"),
        nullable=True,
    )
    appointment_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("appointments.id", name="fk_sent_messages_appointment_id"),
        nullable=True,
    )
    message_type: Mapped[str] = mapped_column(String(50), nullable=False)
    message_content: Mapped[str] = mapped_column(Text(), nullable=False)
    recipient_phone: Mapped[str] = mapped_column(String(20), nullable=False)
    delivery_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="pending",
    )
    twilio_sid: Mapped[str | None] = mapped_column(String(50), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text(), nullable=True)
    scheduled_for: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
    )
    sent_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
    )
    created_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default="NOW()",
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default="NOW()",
    )

    # Relationships
    customer: Mapped["Customer"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Customer",
        back_populates="sent_messages",
        lazy="selectin",
    )
    job: Mapped["Job | None"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Job",
        back_populates="sent_messages",
        lazy="selectin",
    )
    appointment: Mapped["Appointment | None"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Appointment",
        back_populates="sent_messages",
        lazy="selectin",
    )

    __table_args__ = (
        CheckConstraint(
            "message_type IN ('appointment_confirmation', 'appointment_reminder', "
            "'on_the_way', 'arrival', 'completion', 'invoice', 'payment_reminder', "
            "'custom')",
            name="ck_sent_messages_message_type",
        ),
        CheckConstraint(
            "delivery_status IN ('pending', 'scheduled', 'sent', 'delivered', "
            "'failed', 'cancelled')",
            name="ck_sent_messages_delivery_status",
        ),
        Index("idx_sent_messages_customer_id", "customer_id"),
        Index("idx_sent_messages_job_id", "job_id"),
        Index("idx_sent_messages_message_type", "message_type"),
        Index("idx_sent_messages_delivery_status", "delivery_status"),
        Index("idx_sent_messages_scheduled_for", "scheduled_for"),
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"<SentMessage(id={self.id}, customer_id={self.customer_id}, "
            f"message_type={self.message_type}, status={self.delivery_status})>"
        )
