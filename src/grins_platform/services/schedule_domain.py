"""
Schedule domain models for route optimization.

This module defines the domain models for the schedule solver.
Uses pure Python dataclasses for compatibility with Python 3.10+.

Validates: Requirement 5.1 (Route Optimization)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from decimal import Decimal  # noqa: TC003
from uuid import UUID  # noqa: TC003


@dataclass
class ScheduleLocation:
    """Represents a geographic location for travel calculations."""

    latitude: Decimal
    longitude: Decimal
    address: str | None = None
    city: str | None = None

    def to_tuple(self) -> tuple[float, float]:
        """Convert to tuple for travel time calculations."""
        return (float(self.latitude), float(self.longitude))


@dataclass
class ScheduleJob:
    """A job to be scheduled."""

    id: UUID
    customer_name: str
    location: ScheduleLocation
    service_type: str
    duration_minutes: int
    equipment_required: list[str] = field(default_factory=list)
    priority: int = 0  # Higher = more important
    preferred_time_start: time | None = None
    preferred_time_end: time | None = None
    requires_multi_staff: bool = False
    staff_count_required: int = 1
    buffer_minutes: int = 10

    @property
    def total_time_minutes(self) -> int:
        """Total time including buffer."""
        return self.duration_minutes + self.buffer_minutes

    def __hash__(self) -> int:
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ScheduleJob):
            return False
        return self.id == other.id


@dataclass
class ScheduleStaff:
    """A staff member available for scheduling."""

    id: UUID
    name: str
    start_location: ScheduleLocation
    assigned_equipment: list[str] = field(default_factory=list)
    availability_start: time = field(default_factory=lambda: time(8, 0))
    availability_end: time = field(default_factory=lambda: time(17, 0))
    lunch_start: time | None = None
    lunch_duration_minutes: int = 30

    def __hash__(self) -> int:
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ScheduleStaff):
            return False
        return self.id == other.id

    def has_equipment(self, required: list[str]) -> bool:
        """Check if staff has all required equipment."""
        if not required:
            return True
        return all(eq in self.assigned_equipment for eq in required)

    def get_lunch_end(self) -> time | None:
        """Calculate lunch end time."""
        if self.lunch_start is None:
            return None
        lunch_start_dt = datetime.combine(date.today(), self.lunch_start)
        lunch_end_dt = lunch_start_dt + timedelta(minutes=self.lunch_duration_minutes)
        return lunch_end_dt.time()

    def get_available_minutes(self) -> int:
        """Get total available minutes excluding lunch."""
        start_mins = self.availability_start.hour * 60 + self.availability_start.minute
        end_mins = self.availability_end.hour * 60 + self.availability_end.minute
        total = end_mins - start_mins
        if self.lunch_start:
            total -= self.lunch_duration_minutes
        return total


@dataclass
class ScheduleAssignment:
    """Assignment of jobs to a staff member."""

    id: UUID
    staff: ScheduleStaff
    jobs: list[ScheduleJob] = field(default_factory=list)

    def __hash__(self) -> int:
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ScheduleAssignment):
            return False
        return self.id == other.id


@dataclass
class ScheduleSolution:
    """The complete schedule solution."""

    schedule_date: date
    jobs: list[ScheduleJob] = field(default_factory=list)
    staff: list[ScheduleStaff] = field(default_factory=list)
    assignments: list[ScheduleAssignment] = field(default_factory=list)
    hard_score: int = 0
    soft_score: int = 0

    def get_unassigned_jobs(self) -> list[ScheduleJob]:
        """Get jobs not assigned to any staff."""
        assigned_job_ids = set()
        for assignment in self.assignments:
            for job in assignment.jobs:
                assigned_job_ids.add(job.id)
        return [job for job in self.jobs if job.id not in assigned_job_ids]

    def get_assignment_for_staff(self, staff_id: UUID) -> ScheduleAssignment | None:
        """Get assignment for a specific staff member."""
        for assignment in self.assignments:
            if assignment.staff.id == staff_id:
                return assignment
        return None

    def is_feasible(self) -> bool:
        """Check if solution satisfies all hard constraints."""
        return self.hard_score >= 0

    def score_str(self) -> str:
        """Get score as string."""
        return f"[{self.hard_score}hard/{self.soft_score}soft]"


@dataclass
class JobTimeSlot:
    """Calculated time slot for a job in the schedule."""

    job: ScheduleJob
    staff: ScheduleStaff
    start_time: time
    end_time: time
    travel_time_from_previous: int  # minutes
    sequence_index: int

    @property
    def duration_with_buffer(self) -> int:
        """Total duration including buffer time."""
        return self.job.duration_minutes + self.job.buffer_minutes
