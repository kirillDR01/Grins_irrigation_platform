"""
Schedule solver service for route optimization.

This module provides a constraint-based scheduler using a greedy
algorithm with local search optimization.

Validates: Requirements 5.1, 5.2
"""

from __future__ import annotations

import random
import time as time_module
from datetime import date, time
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from grins_platform.log_config import LoggerMixin
from grins_platform.services.schedule_constraints import (
    ConstraintChecker,
    haversine_travel_minutes,
)
from grins_platform.services.schedule_domain import (
    JobTimeSlot,
    ScheduleAssignment,
    ScheduleJob,
    ScheduleLocation,
    ScheduleSolution,
    ScheduleStaff,
)

if TYPE_CHECKING:
    from grins_platform.models.job import Job
    from grins_platform.models.staff import Staff
    from grins_platform.models.staff_availability import StaffAvailability


class ScheduleSolverService(LoggerMixin):
    """Service for solving schedule optimization problems.

    Uses a greedy algorithm with local search to optimize schedules.

    Validates: Requirements 5.1, 5.2
    """

    DOMAIN = "business"

    def __init__(self, timeout_seconds: int = 30) -> None:
        """Initialize the solver service.

        Args:
            timeout_seconds: Maximum time for optimization (default 30s)
        """
        super().__init__()
        self.timeout_seconds = timeout_seconds
        self.constraint_checker = ConstraintChecker()

    def solve(
        self,
        schedule_date: date,
        jobs: list[ScheduleJob],
        staff: list[ScheduleStaff],
    ) -> ScheduleSolution:
        """Solve the scheduling problem.

        Args:
            schedule_date: Date to generate schedule for
            jobs: List of jobs to schedule
            staff: List of available staff

        Returns:
            Optimized schedule solution

        Validates: Requirements 5.1, 5.2
        """
        self.log_started(
            "solve",
            schedule_date=str(schedule_date),
            job_count=len(jobs),
            staff_count=len(staff),
        )

        # Create initial solution using greedy assignment
        solution = self._create_greedy_solution(schedule_date, jobs, staff)

        # Calculate initial score
        score = self.constraint_checker.calculate_score(solution)
        solution.hard_score = score.hard_score
        solution.soft_score = score.soft_score

        # Try to improve with local search
        solution = self._local_search(solution)

        self.log_completed(
            "solve",
            score=solution.score_str(),
            assigned_jobs=sum(len(a.jobs) for a in solution.assignments),
            unassigned_jobs=len(solution.get_unassigned_jobs()),
        )

        return solution

    def _create_greedy_solution(
        self,
        schedule_date: date,
        jobs: list[ScheduleJob],
        staff: list[ScheduleStaff],
    ) -> ScheduleSolution:
        """Create initial solution using greedy assignment.

        Assigns jobs to staff based on:
        1. Equipment compatibility
        2. Geographic proximity (city batching)
        3. Priority (high priority first)
        """
        # Sort jobs by priority (descending) then by city
        sorted_jobs = sorted(
            jobs,
            key=lambda j: (-j.priority, j.location.city or ""),
        )

        # Create empty assignments for each staff
        assignments = [
            ScheduleAssignment(id=uuid4(), staff=s, jobs=[])
            for s in staff
        ]

        # Track remaining capacity per staff
        staff_remaining: dict[UUID, int] = {
            s.id: s.get_available_minutes() for s in staff
        }

        # Assign jobs greedily
        for job in sorted_jobs:
            best_assignment = None
            best_score = float("-inf")

            for assignment in assignments:
                # Check equipment compatibility
                if not assignment.staff.has_equipment(job.equipment_required):
                    continue

                # Check capacity
                job_time = job.duration_minutes + job.buffer_minutes
                if staff_remaining[assignment.staff.id] < job_time:
                    continue

                # Calculate score for this assignment
                score = self._calculate_assignment_score(assignment, job)

                if score > best_score:
                    best_score = score
                    best_assignment = assignment

            # Assign to best staff if found
            if best_assignment is not None:
                best_assignment.jobs.append(job)
                job_time = job.duration_minutes + job.buffer_minutes
                staff_remaining[best_assignment.staff.id] -= job_time

        # Optimize job order within each assignment
        for assignment in assignments:
            assignment.jobs = self._optimize_job_order(assignment)

        return ScheduleSolution(
            schedule_date=schedule_date,
            jobs=jobs,
            staff=staff,
            assignments=assignments,
        )

    def _calculate_assignment_score(
        self,
        assignment: ScheduleAssignment,
        job: ScheduleJob,
    ) -> float:
        """Calculate score for assigning a job to a staff member."""
        score = 0.0

        # Prefer same city (city batching)
        if assignment.jobs:
            last_job = assignment.jobs[-1]
            if last_job.location.city == job.location.city:
                score += 100

            # Penalize travel distance
            travel = haversine_travel_minutes(
                float(last_job.location.latitude),
                float(last_job.location.longitude),
                float(job.location.latitude),
                float(job.location.longitude),
            )
            score -= travel * 2
        else:
            # First job - prefer close to start location
            travel = haversine_travel_minutes(
                float(assignment.staff.start_location.latitude),
                float(assignment.staff.start_location.longitude),
                float(job.location.latitude),
                float(job.location.longitude),
            )
            score -= travel * 2

        return score

    def _optimize_job_order(
        self,
        assignment: ScheduleAssignment,
    ) -> list[ScheduleJob]:
        """Optimize job order using nearest neighbor heuristic."""
        if len(assignment.jobs) <= 1:
            return assignment.jobs

        jobs = list(assignment.jobs)
        optimized: list[ScheduleJob] = []

        # Start from staff's start location
        current_lat = float(assignment.staff.start_location.latitude)
        current_lng = float(assignment.staff.start_location.longitude)

        while jobs:
            # Find nearest job
            best_job = None
            best_distance = float("inf")

            for job in jobs:
                distance = haversine_travel_minutes(
                    current_lat, current_lng,
                    float(job.location.latitude),
                    float(job.location.longitude),
                )
                if distance < best_distance:
                    best_distance = distance
                    best_job = job

            if best_job:
                optimized.append(best_job)
                jobs.remove(best_job)
                current_lat = float(best_job.location.latitude)
                current_lng = float(best_job.location.longitude)

        return optimized

    def _local_search(
        self,
        solution: ScheduleSolution,
        max_iterations: int = 100,
    ) -> ScheduleSolution:
        """Improve solution using local search."""
        start_time = time_module.time()
        best_solution = solution
        best_score = (solution.hard_score, solution.soft_score)

        for _ in range(max_iterations):
            # Check timeout
            if time_module.time() - start_time > self.timeout_seconds:
                break

            # Try a random move
            new_solution = self._try_random_move(best_solution)
            score = self.constraint_checker.calculate_score(new_solution)
            new_solution.hard_score = score.hard_score
            new_solution.soft_score = score.soft_score

            new_score = (new_solution.hard_score, new_solution.soft_score)

            # Accept if better
            if new_score > best_score:
                best_solution = new_solution
                best_score = new_score

        return best_solution

    def _try_random_move(self, solution: ScheduleSolution) -> ScheduleSolution:
        """Try a random move to improve the solution."""
        # Deep copy assignments
        new_assignments = [
            ScheduleAssignment(id=a.id, staff=a.staff, jobs=list(a.jobs))
            for a in solution.assignments
        ]

        # Choose random move type
        move_type = random.choice(["swap_within", "swap_between", "move"])  # noqa: S311

        if move_type == "swap_within":
            # Swap two jobs within same assignment
            for assignment in new_assignments:
                if len(assignment.jobs) >= 2:
                    i, j = random.sample(range(len(assignment.jobs)), 2)
                    assignment.jobs[i], assignment.jobs[j] = (
                        assignment.jobs[j], assignment.jobs[i],
                    )
                    break

        elif move_type == "swap_between":
            # Swap jobs between two assignments
            valid_pairs = [
                (a1, a2)
                for a1 in new_assignments
                for a2 in new_assignments
                if a1 != a2 and a1.jobs and a2.jobs
            ]
            if valid_pairs:
                a1, a2 = random.choice(valid_pairs)  # noqa: S311
                i = random.randrange(len(a1.jobs))  # noqa: S311
                j = random.randrange(len(a2.jobs))  # noqa: S311
                # Check equipment compatibility
                if (a1.staff.has_equipment(a2.jobs[j].equipment_required) and
                    a2.staff.has_equipment(a1.jobs[i].equipment_required)):
                    a1.jobs[i], a2.jobs[j] = a2.jobs[j], a1.jobs[i]

        else:  # move
            # Move a job from one assignment to another
            source_assignments = [a for a in new_assignments if a.jobs]
            if source_assignments:
                source = random.choice(source_assignments)  # noqa: S311
                job_idx = random.randrange(len(source.jobs))  # noqa: S311
                job = source.jobs[job_idx]

                # Find valid target
                valid_targets = [
                    a for a in new_assignments
                    if a != source and a.staff.has_equipment(job.equipment_required)
                ]
                if valid_targets:
                    target = random.choice(valid_targets)  # noqa: S311
                    source.jobs.pop(job_idx)
                    target.jobs.append(job)

        return ScheduleSolution(
            schedule_date=solution.schedule_date,
            jobs=solution.jobs,
            staff=solution.staff,
            assignments=new_assignments,
        )

    def calculate_time_slots(
        self,
        solution: ScheduleSolution,
    ) -> dict[UUID, list[JobTimeSlot]]:
        """Calculate actual time slots for jobs in the solution."""
        result: dict[UUID, list[JobTimeSlot]] = {}

        for assignment in solution.assignments:
            if not assignment.jobs:
                continue

            slots: list[JobTimeSlot] = []
            current_time_minutes = self._time_to_minutes(
                assignment.staff.availability_start,
            )

            # Add travel from start location to first job
            if assignment.jobs:
                first_job = assignment.jobs[0]
                travel_time = haversine_travel_minutes(
                    float(assignment.staff.start_location.latitude),
                    float(assignment.staff.start_location.longitude),
                    float(first_job.location.latitude),
                    float(first_job.location.longitude),
                )
                current_time_minutes += travel_time

            for i, job in enumerate(assignment.jobs):
                if i == 0:
                    travel_from_prev = haversine_travel_minutes(
                        float(assignment.staff.start_location.latitude),
                        float(assignment.staff.start_location.longitude),
                        float(job.location.latitude),
                        float(job.location.longitude),
                    )
                else:
                    prev_job = assignment.jobs[i - 1]
                    travel_from_prev = haversine_travel_minutes(
                        float(prev_job.location.latitude),
                        float(prev_job.location.longitude),
                        float(job.location.latitude),
                        float(job.location.longitude),
                    )

                start_time = self._minutes_to_time(current_time_minutes)
                end_minutes = current_time_minutes + job.duration_minutes
                end_time = self._minutes_to_time(end_minutes)

                slot = JobTimeSlot(
                    job=job,
                    staff=assignment.staff,
                    start_time=start_time,
                    end_time=end_time,
                    travel_time_from_previous=travel_from_prev,
                    sequence_index=i,
                )
                slots.append(slot)

                current_time_minutes = end_minutes + job.buffer_minutes
                if i < len(assignment.jobs) - 1:
                    next_job = assignment.jobs[i + 1]
                    current_time_minutes += haversine_travel_minutes(
                        float(job.location.latitude),
                        float(job.location.longitude),
                        float(next_job.location.latitude),
                        float(next_job.location.longitude),
                    )

            result[assignment.staff.id] = slots

        return result

    def _time_to_minutes(self, t: time) -> int:
        """Convert time to minutes since midnight."""
        return t.hour * 60 + t.minute

    def _minutes_to_time(self, minutes: int) -> time:
        """Convert minutes since midnight to time."""
        return time(hour=minutes // 60, minute=minutes % 60)


# =============================================================================
# Conversion helpers
# =============================================================================


def job_to_schedule_job(
    job: Job,
    buffer_minutes: int = 10,
) -> ScheduleJob:
    """Convert a Job model to a ScheduleJob for scheduling."""
    prop = job.job_property
    location = ScheduleLocation(
        latitude=prop.latitude if prop else Decimal("44.8547"),
        longitude=prop.longitude if prop else Decimal("-93.4708"),
        address=prop.address if prop else None,
        city=prop.city if prop else None,
    )

    return ScheduleJob(
        id=job.id,
        customer_name=f"{job.customer.first_name} {job.customer.last_name}",
        location=location,
        service_type=job.service_offering.name if job.service_offering else "Unknown",
        duration_minutes=job.estimated_duration_minutes or 60,
        equipment_required=job.equipment_required or [],
        priority=job.priority_level or 0,
        preferred_time_start=None,
        preferred_time_end=None,
        requires_multi_staff=job.requires_multi_staff or False,
        staff_count_required=job.staff_count_required or 1,
        buffer_minutes=buffer_minutes,
    )


def staff_to_schedule_staff(
    staff: Staff,
    availability: StaffAvailability | None = None,
) -> ScheduleStaff:
    """Convert a Staff model to a ScheduleStaff for scheduling."""
    start_location = ScheduleLocation(
        latitude=staff.default_start_lat or Decimal("44.8547"),
        longitude=staff.default_start_lng or Decimal("-93.4708"),
        address=staff.default_start_address,
        city=staff.default_start_city,
    )

    if availability:
        avail_start = availability.start_time
        avail_end = availability.end_time
        lunch_start = availability.lunch_start
        lunch_duration = availability.lunch_duration_minutes or 30
    else:
        avail_start = time(8, 0)
        avail_end = time(17, 0)
        lunch_start = time(12, 0)
        lunch_duration = 30

    return ScheduleStaff(
        id=staff.id,
        name=staff.name,
        start_location=start_location,
        assigned_equipment=staff.assigned_equipment or [],
        availability_start=avail_start,
        availability_end=avail_end,
        lunch_start=lunch_start,
        lunch_duration_minutes=lunch_duration,
    )
