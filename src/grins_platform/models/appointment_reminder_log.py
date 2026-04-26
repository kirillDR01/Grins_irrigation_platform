"""Append-only log of automated appointment-reminder sends.

A row is written by :class:`Day2ReminderJob` (and future
``day_before`` / ``morning_of`` jobs) every time the system actually
fires a reminder SMS for an appointment. The presence of a row for
``(appointment_id, stage)`` is the dedup key — the eligibility query
joins against this table so an hourly tick can re-evaluate the same
48-52 h sliding window without sending duplicate SMS.

Validates: scheduling gaps gap-10 Phase 1 (Day-2 No-Reply Reminder)
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import (
    UUID as PGUUID,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from grins_platform.database import Base


class AppointmentReminderLog(Base):
    """One row per reminder SMS actually sent for an appointment.

    Attributes:
        id: Primary key (UUID).
        appointment_id: FK to ``appointments.id`` the reminder targets.
        stage: Reminder cadence. ``day_2`` is the only stage shipped in
            gap-10 Phase 1; ``day_before`` and ``morning_of`` are
            reserved for Phase 2.
        sent_at: Tz-aware UTC timestamp of the actual SMS send.
        sent_message_id: FK to the corresponding ``sent_messages.id``
            row (nullable so the log row survives if the SentMessage is
            ever pruned).
        cancelled_at: Reserved for the future scheduled-send pattern
            (gap-10 Phase 2). Always ``None`` in Phase 1 because
            reminders fire synchronously inside the eligibility scan.
        created_at: Insertion timestamp (server default).

    Validates: scheduling gaps gap-10 Phase 1
    """

    __tablename__ = "appointment_reminder_log"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )

    appointment_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey(
            "appointments.id",
            name="fk_appointment_reminder_log_appointment_id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    stage: Mapped[str] = mapped_column(String(32), nullable=False)

    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    sent_message_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey(
            "sent_messages.id",
            name="fk_appointment_reminder_log_sent_message_id",
            ondelete="SET NULL",
        ),
        nullable=True,
    )

    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        Index(
            "ix_appointment_reminder_log_appointment_id",
            "appointment_id",
        ),
        Index(
            "idx_appointment_reminder_log_stage_appointment_id",
            "stage",
            "appointment_id",
        ),
    )

    def to_dict(self) -> dict[str, Any]:
        """Return a plain-dict representation."""
        return {
            "id": str(self.id),
            "appointment_id": str(self.appointment_id),
            "stage": self.stage,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "sent_message_id": (
                str(self.sent_message_id) if self.sent_message_id else None
            ),
            "cancelled_at": (
                self.cancelled_at.isoformat() if self.cancelled_at else None
            ),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"<AppointmentReminderLog(id={self.id}, "
            f"appointment_id={self.appointment_id}, stage='{self.stage}')>"
        )
