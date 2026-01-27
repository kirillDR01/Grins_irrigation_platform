"""
Appointment model for scheduling management.

This module defines the Appointment SQLAlchemy model representing scheduled
appointments in the Grin's Irrigation Platform.

Validates: Admin Dashboard Requirements 1.1-1.5
"""

from datetime import date, datetime, time
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import Date, ForeignKey, Integer, String, Text, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from grins_platform.database import Base
from grins_platform.models.enums import AppointmentStatus

if TYPE_CHECKING:
    from grins_platform.models.job import Job
    from grins_platform.models.sent_message import SentMessage
    from grins_platform.models.staff import Staff


# Valid status transitions for appointments
VALID_APPOINTMENT_TRANSITIONS: dict[str, list[str]] = {
    AppointmentStatus.SCHEDULED.value: [
        AppointmentStatus.CONFIRMED.value,
        AppointmentStatus.CANCELLED.value,
    ],
    AppointmentStatus.CONFIRMED.value: [
        AppointmentStatus.IN_PROGRESS.value,
        AppointmentStatus.CANCELLED.value,
    ],
    AppointmentStatus.IN_PROGRESS.value: [
        AppointmentStatus.COMPLETED.value,
        AppointmentStatus.CANCELLED.value,
    ],
    AppointmentStatus.COMPLETED.value: [],  # Terminal state
    AppointmentStatus.CANCELLED.value: [
        AppointmentStatus.SCHEDULED.value,  # Can be rescheduled
    ],
}


class Appointment(Base):
    """Appointment model representing a scheduled job.

    Attributes:
        id: Unique identifier for the appointment
        job_id: Reference to the job being scheduled
        staff_id: Reference to the assigned staff member
        scheduled_date: Date of the appointment
        time_window_start: Start of the time window
        time_window_end: End of the time window
        status: Current status (scheduled, confirmed, in_progress, completed, cancelled)
        arrived_at: When the staff arrived
        completed_at: When the appointment was completed
        notes: Additional notes
        route_order: Order in the daily route
        estimated_arrival: Estimated arrival time
        created_at: Record creation timestamp
        updated_at: Record update timestamp

    Validates: Admin Dashboard Requirements 1.1-1.5
    """

    __tablename__ = "appointments"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )

    # Foreign keys
    job_id: Mapped[UUID] = mapped_column(
        ForeignKey("jobs.id"),
        nullable=False,
    )
    staff_id: Mapped[UUID] = mapped_column(
        ForeignKey("staff.id"),
        nullable=False,
    )

    # Scheduling
    scheduled_date: Mapped[date] = mapped_column(Date, nullable=False)
    time_window_start: Mapped[time] = mapped_column(Time, nullable=False)
    time_window_end: Mapped[time] = mapped_column(Time, nullable=False)

    # Status
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        server_default="scheduled",
    )

    # Execution Tracking
    arrived_at: Mapped[datetime | None] = mapped_column(nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Notes
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Route Information
    route_order: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated_arrival: Mapped[time | None] = mapped_column(Time, nullable=True)

    # Record Timestamps
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Cancellation/Reschedule fields (Requirement 10.2, 10.3)
    cancellation_reason: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(nullable=True)
    rescheduled_from_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("appointments.id"),
        nullable=True,
    )

    # Relationships
    job: Mapped["Job"] = relationship("Job", back_populates="appointments")
    staff: Mapped["Staff"] = relationship("Staff", back_populates="appointments")
    rescheduled_from: Mapped["Appointment | None"] = relationship(
        "Appointment",
        remote_side="Appointment.id",
        foreign_keys=[rescheduled_from_id],
    )
    sent_messages: Mapped[list["SentMessage"]] = relationship(
        "SentMessage",
        back_populates="appointment",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        """Return string representation of the appointment."""
        return (
            f"<Appointment(id={self.id}, job_id={self.job_id}, "
            f"scheduled_date={self.scheduled_date}, status='{self.status}')>"
        )

    @property
    def status_enum(self) -> AppointmentStatus:
        """Get the status as an enum value."""
        return AppointmentStatus(self.status)

    def can_transition_to(self, new_status: str) -> bool:
        """Check if the appointment can transition to the given status.

        Args:
            new_status: The target status to transition to.

        Returns:
            True if the transition is valid, False otherwise.
        """
        valid_transitions = VALID_APPOINTMENT_TRANSITIONS.get(self.status, [])
        return new_status in valid_transitions

    def get_valid_transitions(self) -> list[str]:
        """Get the list of valid status transitions from current status.

        Returns:
            List of valid target statuses.
        """
        return VALID_APPOINTMENT_TRANSITIONS.get(self.status, [])

    def is_terminal_status(self) -> bool:
        """Check if the appointment is in a terminal status.

        Returns:
            True if the appointment is completed or cancelled.
        """
        return self.status in [
            AppointmentStatus.COMPLETED.value,
            AppointmentStatus.CANCELLED.value,
        ]

    def get_duration_minutes(self) -> int:
        """Calculate the duration of the appointment in minutes.

        Returns:
            Duration in minutes.
        """
        start_minutes: int = (
            self.time_window_start.hour * 60 + self.time_window_start.minute
        )
        end_minutes: int = (
            self.time_window_end.hour * 60 + self.time_window_end.minute
        )
        return end_minutes - start_minutes

    def to_dict(self) -> dict[str, Any]:
        """Convert the appointment to a dictionary.

        Returns:
            Dictionary representation of the appointment.
        """
        return {
            "id": str(self.id),
            "job_id": str(self.job_id),
            "staff_id": str(self.staff_id),
            "scheduled_date": self.scheduled_date.isoformat(),
            "time_window_start": self.time_window_start.isoformat(),
            "time_window_end": self.time_window_end.isoformat(),
            "status": self.status,
            "arrived_at": self.arrived_at.isoformat() if self.arrived_at else None,
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
            "notes": self.notes,
            "route_order": self.route_order,
            "estimated_arrival": self.estimated_arrival.isoformat()
            if self.estimated_arrival
            else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
