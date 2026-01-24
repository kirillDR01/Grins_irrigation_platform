"""
Staff Availability model for route optimization.

This module defines the StaffAvailability SQLAlchemy model representing
staff availability calendar entries in the Grin's Irrigation Platform.

Validates: Requirements 1.1, 1.6, 1.7 (Route Optimization)
"""

from datetime import (
    date as date_type,
    datetime,
    time,
)
from typing import TYPE_CHECKING, Any, Optional
from uuid import UUID

from sqlalchemy import Boolean, Date, ForeignKey, Integer, Text, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates
from sqlalchemy.sql import func

from grins_platform.database import Base

if TYPE_CHECKING:
    from grins_platform.models.staff import Staff


class StaffAvailability(Base):
    """Staff availability model representing a calendar entry.

    Attributes:
        id: Unique identifier for the availability entry
        staff_id: Foreign key to the staff member
        date: Date of availability
        start_time: Start time of availability window
        end_time: End time of availability window
        is_available: Whether the staff member is available
        lunch_start: Start time of lunch break (optional)
        lunch_duration_minutes: Duration of lunch break in minutes
        notes: Additional notes about availability
        created_at: Record creation timestamp
        updated_at: Record update timestamp

    Validates: Requirements 1.1, 1.6, 1.7 (Route Optimization)
    """

    __tablename__ = "staff_availability"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        primary_key=True, server_default=func.gen_random_uuid(),
    )

    # Foreign key to staff
    staff_id: Mapped[UUID] = mapped_column(
        ForeignKey("staff.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Date for availability
    date: Mapped[date_type] = mapped_column(Date, nullable=False)

    # Time window
    start_time: Mapped[time] = mapped_column(
        Time, nullable=False, server_default="07:00:00",
    )
    end_time: Mapped[time] = mapped_column(
        Time, nullable=False, server_default="17:00:00",
    )

    # Availability flag
    is_available: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true",
    )

    # Lunch break configuration
    lunch_start: Mapped[Optional[time]] = mapped_column(
        Time, nullable=True, server_default="12:00:00",
    )
    lunch_duration_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="30",
    )

    # Notes
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(),
    )

    # Relationships
    staff: Mapped["Staff"] = relationship(
        "Staff", back_populates="availability_entries",
    )

    def __repr__(self) -> str:
        """Return string representation of the availability entry."""
        return (
            f"<StaffAvailability(id={self.id}, staff_id={self.staff_id}, "
            f"date={self.date}, available={self.is_available})>"
        )

    @validates("start_time", "end_time")  # type: ignore[misc,untyped-decorator]
    def validate_time_range(self, key: str, value: time) -> time:
        """Validate that start_time is before end_time.

        Requirement 1.6: Start time must be before end time.
        """
        if key == "end_time" and self.start_time is not None:
            if value <= self.start_time:
                msg = "end_time must be after start_time"
                raise ValueError(msg)
        elif (
            key == "start_time"
            and self.end_time is not None
            and value >= self.end_time
        ):
            msg = "start_time must be before end_time"
            raise ValueError(msg)
        return value

    @validates("lunch_start")  # type: ignore[misc,untyped-decorator]
    def validate_lunch_within_window(
        self, key: str, value: Optional[time],  # noqa: ARG002
    ) -> Optional[time]:
        """Validate that lunch_start is within the availability window.

        Requirement 1.7: Lunch time must be within availability window.
        """
        if (
            value is not None
            and self.start_time is not None
            and self.end_time is not None
            and (value < self.start_time or value >= self.end_time)
        ):
            msg = "lunch_start must be within availability window"
            raise ValueError(msg)
        return value

    @validates("lunch_duration_minutes")  # type: ignore[misc,untyped-decorator]
    def validate_lunch_duration(self, key: str, value: int) -> int:  # noqa: ARG002
        """Validate lunch duration is within acceptable range."""
        if value < 0 or value > 120:
            msg = "lunch_duration_minutes must be between 0 and 120"
            raise ValueError(msg)
        return value

    @property
    def available_minutes(self) -> int:
        """Calculate total available minutes excluding lunch.

        Returns:
            Total available minutes for the day.
        """
        if not self.is_available:
            return 0

        start_minutes = self.start_time.hour * 60 + self.start_time.minute
        end_minutes = self.end_time.hour * 60 + self.end_time.minute
        total_minutes = end_minutes - start_minutes

        # Subtract lunch if configured
        if self.lunch_start is not None and self.lunch_duration_minutes > 0:
            total_minutes -= self.lunch_duration_minutes

        return int(max(0, total_minutes))

    @property
    def lunch_end(self) -> Optional[time]:
        """Calculate the end time of lunch break.

        Returns:
            End time of lunch break, or None if no lunch configured.
        """
        if self.lunch_start is None or self.lunch_duration_minutes == 0:
            return None

        lunch_start_minutes = self.lunch_start.hour * 60 + self.lunch_start.minute
        lunch_end_minutes = lunch_start_minutes + self.lunch_duration_minutes

        return time(lunch_end_minutes // 60, lunch_end_minutes % 60)

    def is_time_available(self, check_time: time) -> bool:
        """Check if a specific time is available (not during lunch).

        Args:
            check_time: Time to check availability for.

        Returns:
            True if the time is available, False otherwise.
        """
        if not self.is_available:
            return False

        # Check if within availability window
        if check_time < self.start_time or check_time >= self.end_time:
            return False

        # Check if during lunch
        if self.lunch_start is not None and self.lunch_duration_minutes > 0:
            lunch_end = self.lunch_end
            if lunch_end is not None and self.lunch_start <= check_time < lunch_end:
                return False

        return True

    def to_dict(self) -> dict[str, Any]:
        """Convert the availability entry to a dictionary.

        Returns:
            Dictionary representation of the availability entry.
        """
        return {
            "id": str(self.id),
            "staff_id": str(self.staff_id),
            "date": self.date.isoformat() if self.date else None,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "is_available": self.is_available,
            "lunch_start": self.lunch_start.isoformat() if self.lunch_start else None,
            "lunch_duration_minutes": self.lunch_duration_minutes,
            "notes": self.notes,
            "available_minutes": self.available_minutes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
