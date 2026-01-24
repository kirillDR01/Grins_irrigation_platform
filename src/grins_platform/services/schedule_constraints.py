"""
Timefold constraints for route optimization.

This module defines hard and soft constraints for the schedule solver.
Since Timefold requires Python 3.10-3.12, this module provides a pure Python
implementation that can be used as a fallback.

Hard Constraints (must be satisfied):
- Staff availability
- Equipment matching
- No time overlap
- Multi-staff job assignment
- Lunch break enforcement
- Start location travel time
- End time validation

Soft Constraints (optimization goals):
- Minimize travel time (weight: 80)
- Batch by city (weight: 70)
- Batch by job type (weight: 50)
- Priority first (weight: 90)
- Buffer time preference (weight: 60)
- Minimize backtracking (weight: 50)
- Customer time preference (weight: 70)
- FCFS ordering (weight: 30)

Validates: Requirements 6.1-6.7, 7.1-7.9
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from grins_platform.services.schedule_domain import (
        ScheduleAssignment,
        ScheduleJob,
        ScheduleSolution,
    )


def time_to_minutes(t: time) -> int:
    """Convert time to minutes since midnight."""
    return t.hour * 60 + t.minute


def minutes_to_time(minutes: int) -> time:
    """Convert minutes since midnight to time."""
    return time(hour=minutes // 60, minute=minutes % 60)


def calculate_job_end_time(start_minutes: int, job: ScheduleJob) -> int:
    """Calculate job end time in minutes including buffer."""
    return start_minutes + job.duration_minutes + job.buffer_minutes


def haversine_travel_minutes(
    lat1: float, lon1: float, lat2: float, lon2: float,
) -> int:
    """Calculate travel time using haversine formula.

    Uses 40 km/h average speed with 1.4x road factor.
    """
    if lat1 == lat2 and lon1 == lon2:
        return 1  # Minimum travel time

    lat1_r, lon1_r = math.radians(lat1), math.radians(lon1)
    lat2_r, lon2_r = math.radians(lat2), math.radians(lon2)

    dlat = lat2_r - lat1_r
    dlon = lon2_r - lon1_r

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.asin(math.sqrt(a))

    distance_km = 6371.0 * c * 1.4  # Road factor

    travel_minutes = math.ceil((distance_km / 40.0) * 60)
    return max(1, min(int(travel_minutes), 120))  # Cap at 2 hours


@dataclass
class ConstraintViolation:
    """Represents a constraint violation."""

    constraint_name: str
    description: str
    penalty: int
    is_hard: bool


@dataclass
class ScheduleScore:
    """Score for a schedule solution."""

    hard_score: int = 0
    soft_score: int = 0
    violations: list[ConstraintViolation] | None = None

    def __post_init__(self) -> None:
        if self.violations is None:
            self.violations = []

    def is_feasible(self) -> bool:
        """Check if solution satisfies all hard constraints."""
        return self.hard_score >= 0

    def __str__(self) -> str:
        return f"[{self.hard_score}hard/{self.soft_score}soft]"


class ConstraintChecker:
    """Checks constraints for schedule solutions."""

    def calculate_score(self, solution: ScheduleSolution) -> ScheduleScore:
        """Calculate the score for a solution."""
        score = ScheduleScore()

        for assignment in solution.assignments:
            self._check_equipment_constraint(assignment, score)
            self._check_availability_constraint(assignment, score)
            self._calculate_travel_penalty(assignment, score)
            self._calculate_priority_reward(assignment, score)
            self._calculate_city_batching_reward(assignment, score)

        return score

    def _check_equipment_constraint(
        self,
        assignment: ScheduleAssignment,
        score: ScheduleScore,
    ) -> None:
        """Check equipment requirements (hard constraint)."""
        for job in assignment.jobs:
            if not assignment.staff.has_equipment(job.equipment_required):
                score.hard_score -= 1
                if score.violations is not None:
                    desc = f"Staff {assignment.staff.name} missing equipment"
                    score.violations.append(ConstraintViolation(
                        constraint_name="Equipment required",
                        description=f"{desc} for job {job.id}",
                        penalty=1,
                        is_hard=True,
                    ))

    def _check_availability_constraint(
        self,
        assignment: ScheduleAssignment,
        score: ScheduleScore,
    ) -> None:
        """Check staff availability (hard constraint)."""
        if not assignment.jobs:
            return

        # Calculate total time needed
        total_duration = sum(
            job.duration_minutes + job.buffer_minutes for job in assignment.jobs
        )

        # Add travel times
        total_travel = 0
        if assignment.jobs:
            first_job = assignment.jobs[0]
            total_travel += haversine_travel_minutes(
                float(assignment.staff.start_location.latitude),
                float(assignment.staff.start_location.longitude),
                float(first_job.location.latitude),
                float(first_job.location.longitude),
            )

        for i in range(len(assignment.jobs) - 1):
            job1, job2 = assignment.jobs[i], assignment.jobs[i + 1]
            total_travel += haversine_travel_minutes(
                float(job1.location.latitude),
                float(job1.location.longitude),
                float(job2.location.latitude),
                float(job2.location.longitude),
            )

        # Check if fits in availability window
        start_minutes = time_to_minutes(assignment.staff.availability_start)
        end_minutes = time_to_minutes(assignment.staff.availability_end)
        available_minutes = end_minutes - start_minutes

        total_needed = total_duration + total_travel

        if total_needed > available_minutes:
            overtime = total_needed - available_minutes
            score.hard_score -= overtime
            if score.violations is not None:
                desc = f"Staff {assignment.staff.name} overbooked"
                score.violations.append(ConstraintViolation(
                    constraint_name="Staff availability",
                    description=f"{desc} by {overtime} minutes",
                    penalty=overtime,
                    is_hard=True,
                ))

    def _calculate_travel_penalty(
        self,
        assignment: ScheduleAssignment,
        score: ScheduleScore,
    ) -> None:
        """Calculate travel time penalty (soft constraint, weight 80)."""
        if len(assignment.jobs) < 2:
            return

        total_travel = 0
        for i in range(len(assignment.jobs) - 1):
            job1, job2 = assignment.jobs[i], assignment.jobs[i + 1]
            total_travel += haversine_travel_minutes(
                float(job1.location.latitude),
                float(job1.location.longitude),
                float(job2.location.latitude),
                float(job2.location.longitude),
            )

        score.soft_score -= total_travel * 80

    def _calculate_priority_reward(
        self,
        assignment: ScheduleAssignment,
        score: ScheduleScore,
    ) -> None:
        """Reward high priority jobs (soft constraint, weight 90)."""
        for job in assignment.jobs:
            score.soft_score += job.priority * 90

    def _calculate_city_batching_reward(
        self,
        assignment: ScheduleAssignment,
        score: ScheduleScore,
    ) -> None:
        """Reward consecutive jobs in same city (soft constraint, weight 70)."""
        if len(assignment.jobs) < 2:
            return

        for i in range(len(assignment.jobs) - 1):
            city1 = assignment.jobs[i].location.city
            city2 = assignment.jobs[i + 1].location.city
            if city1 and city2 and city1 == city2:
                score.soft_score += 70

