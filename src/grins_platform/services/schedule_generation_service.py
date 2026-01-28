"""
Schedule generation service for route optimization.

Validates: Requirements 5.1-5.8
"""

from __future__ import annotations

import time as time_module
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from grins_platform.log_config import LoggerMixin
from grins_platform.models.appointment import Appointment
from grins_platform.models.enums import JobStatus
from grins_platform.models.job import Job
from grins_platform.models.staff import Staff
from grins_platform.models.staff_availability import StaffAvailability
from grins_platform.schemas.schedule_generation import (
    EmergencyInsertResponse,
    ScheduleCapacityResponse,
    ScheduleGenerateResponse,
    ScheduleJobAssignment,
    ScheduleStaffAssignment,
    UnassignedJob,
)
from grins_platform.services.schedule_domain import (
    JobTimeSlot,
    ScheduleJob,
    ScheduleLocation,
    ScheduleStaff,
)
from grins_platform.services.schedule_solver_service import ScheduleSolverService

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from grins_platform.services.schedule_domain import ScheduleSolution


class ScheduleGenerationService(LoggerMixin):
    """Service for generating optimized schedules.

    Validates: Requirements 5.1-5.8
    """

    DOMAIN = "business"

    def __init__(self, db: Session) -> None:
        """Initialize the service."""
        super().__init__()
        self.db = db

    def generate_schedule(
        self,
        schedule_date: date,
        timeout_seconds: int = 30,
    ) -> ScheduleGenerateResponse:
        """Generate an optimized schedule for a date.

        Args:
            schedule_date: Date to generate schedule for
            timeout_seconds: Maximum optimization time

        Returns:
            Generated schedule response
        """
        self.log_started("generate_schedule", schedule_date=str(schedule_date))
        start_time = time_module.time()

        # Load jobs and staff from database
        jobs = self._load_jobs_for_date(schedule_date)
        staff_with_availability = self._load_available_staff(schedule_date)

        if not jobs:
            self.log_completed("generate_schedule", result="no_jobs")
            return ScheduleGenerateResponse(
                schedule_date=schedule_date,
                is_feasible=True,
                hard_score=0,
                soft_score=0,
                total_jobs=0,
                total_assigned=0,
            )

        if not staff_with_availability:
            self.log_completed("generate_schedule", result="no_staff")
            return ScheduleGenerateResponse(
                schedule_date=schedule_date,
                is_feasible=False,
                hard_score=-len(jobs),
                soft_score=0,
                total_jobs=len(jobs),
                total_assigned=0,
                unassigned_jobs=[
                    UnassignedJob(
                        job_id=j.id,
                        customer_name=self._get_job_customer_name(j),
                        service_type=self._get_job_service_type(j),
                        reason="No staff available",
                    )
                    for j in jobs
                ],
            )

        # Convert to schedule domain objects
        schedule_jobs = [self._job_to_schedule_job(j) for j in jobs]
        schedule_staff = [
            self._staff_to_schedule_staff(s, a) for s, a in staff_with_availability
        ]

        # Run solver
        solver = ScheduleSolverService(timeout_seconds=timeout_seconds)
        solution = solver.solve(schedule_date, schedule_jobs, schedule_staff)

        # Calculate time slots
        time_slots = solver.calculate_time_slots(solution)

        # Build response
        response = self._build_response(
            schedule_date,
            solution,
            time_slots,
            jobs,
            start_time,
        )

        self.log_completed(
            "generate_schedule",
            is_feasible=response.is_feasible,
            assigned=response.total_assigned,
            unassigned=len(response.unassigned_jobs),
        )

        return response

    def get_capacity(self, schedule_date: date) -> ScheduleCapacityResponse:
        """Get scheduling capacity for a date.

        Args:
            schedule_date: Date to check capacity for

        Returns:
            Capacity information
        """
        staff_with_availability = self._load_available_staff(schedule_date)

        total_capacity = 0
        for _staff, availability in staff_with_availability:
            if availability:
                start_mins = (
                    availability.start_time.hour * 60 + availability.start_time.minute
                )
                end_mins = (
                    availability.end_time.hour * 60 + availability.end_time.minute
                )
                capacity = end_mins - start_mins
                if availability.lunch_duration_minutes:
                    capacity -= availability.lunch_duration_minutes
                total_capacity += capacity

        # Get scheduled minutes (from existing appointments)
        scheduled_minutes = self._get_scheduled_minutes(schedule_date)

        return ScheduleCapacityResponse(
            schedule_date=schedule_date,
            total_staff=len(staff_with_availability),
            available_staff=len(staff_with_availability),
            total_capacity_minutes=total_capacity,
            scheduled_minutes=scheduled_minutes,
            remaining_capacity_minutes=total_capacity - scheduled_minutes,
            can_accept_more=total_capacity > scheduled_minutes,
        )

    def _load_jobs_for_date(self, schedule_date: date) -> list[Job]:  # noqa: ARG002
        """Load jobs that need scheduling for a date."""
        jobs: list[Job] = (
            self.db.query(Job)
            .filter(
                Job.status.in_([JobStatus.APPROVED.value, JobStatus.REQUESTED.value]),
                Job.is_deleted == False,  # noqa: E712
            )
            .all()
        )
        return jobs

    def _load_available_staff(
        self,
        schedule_date: date,
    ) -> list[tuple[Staff, StaffAvailability | None]]:
        """Load staff with their availability for a date."""
        staff_list = (
            self.db.query(Staff)
            .filter(Staff.is_active == True, Staff.is_available == True)  # noqa: E712
            .all()
        )

        result = []
        for staff in staff_list:
            availability = (
                self.db.query(StaffAvailability)
                .filter(
                    StaffAvailability.staff_id == staff.id,
                    StaffAvailability.date == schedule_date,
                    StaffAvailability.is_available == True,  # noqa: E712
                )
                .first()
            )
            if availability:
                result.append((staff, availability))

        return result

    def _get_scheduled_minutes(self, schedule_date: date) -> int:
        """Get total scheduled minutes for a date."""
        appointments = (
            self.db.query(Appointment)
            .filter(Appointment.scheduled_date == schedule_date)
            .all()
        )

        total = 0
        for apt in appointments:
            if apt.time_window_start and apt.time_window_end:
                start = apt.time_window_start
                end = apt.time_window_end
                start_mins = start.hour * 60 + start.minute
                end_mins = end.hour * 60 + end.minute
                total += end_mins - start_mins

        return total

    def _job_to_schedule_job(self, job: Job) -> ScheduleJob:
        """Convert Job model to ScheduleJob."""
        lat = Decimal("44.8547")
        lng = Decimal("-93.4708")
        city = None
        address = None

        if job.job_property:
            lat = job.job_property.latitude or lat
            lng = job.job_property.longitude or lng
            city = job.job_property.city
            address = job.job_property.address

        buffer_minutes = 10
        if job.service_offering and job.service_offering.buffer_minutes:
            buffer_minutes = job.service_offering.buffer_minutes

        return ScheduleJob(
            id=job.id,
            customer_name=self._get_job_customer_name(job),
            location=ScheduleLocation(lat, lng, address=address, city=city),
            service_type=self._get_job_service_type(job),
            duration_minutes=job.estimated_duration_minutes or 60,
            equipment_required=job.equipment_required or [],
            priority=job.priority_level or 0,
            preferred_time_start=None,
            preferred_time_end=None,
            buffer_minutes=buffer_minutes,
        )

    def _staff_to_schedule_staff(
        self,
        staff: Staff,
        availability: StaffAvailability | None,
    ) -> ScheduleStaff:
        """Convert Staff model to ScheduleStaff."""
        start_location = ScheduleLocation(
            latitude=staff.default_start_lat or Decimal("44.8547"),
            longitude=staff.default_start_lng or Decimal("-93.4708"),
            address=staff.default_start_address,
            city=staff.default_start_city,
        )

        if availability:
            return ScheduleStaff(
                id=staff.id,
                name=staff.name,
                start_location=start_location,
                assigned_equipment=staff.assigned_equipment or [],
                availability_start=availability.start_time,
                availability_end=availability.end_time,
                lunch_start=availability.lunch_start,
                lunch_duration_minutes=availability.lunch_duration_minutes or 30,
            )

        return ScheduleStaff(
            id=staff.id,
            name=staff.name,
            start_location=start_location,
            assigned_equipment=staff.assigned_equipment or [],
        )

    def _get_job_customer_name(self, job: Job) -> str:
        """Get customer name for a job."""
        if job.customer:
            return f"{job.customer.first_name} {job.customer.last_name}"
        return "Unknown"

    def _get_job_service_type(self, job: Job) -> str:
        """Get service type for a job."""
        if job.service_offering:
            return str(job.service_offering.name)
        return "Unknown"

    def _build_response(
        self,
        schedule_date: date,
        solution: ScheduleSolution,
        time_slots: dict[UUID, list[JobTimeSlot]],
        original_jobs: list[Job],
        start_time: float,
    ) -> ScheduleGenerateResponse:
        """Build response from solution."""
        assignments = []
        total_travel = 0

        for assignment in solution.assignments:
            if not assignment.jobs:
                continue

            slots = time_slots.get(assignment.staff.id, [])
            job_assignments = []
            staff_travel = 0

            for slot in slots:
                loc = slot.job.location
                job_assignments.append(
                    ScheduleJobAssignment(
                        job_id=slot.job.id,
                        customer_name=slot.job.customer_name,
                        address=loc.address,
                        city=loc.city,
                        latitude=float(loc.latitude) if loc.latitude else None,
                        longitude=float(loc.longitude) if loc.longitude else None,
                        service_type=slot.job.service_type,
                        start_time=slot.start_time,
                        end_time=slot.end_time,
                        duration_minutes=slot.job.duration_minutes,
                        travel_time_minutes=slot.travel_time_from_previous,
                        sequence_index=slot.sequence_index,
                    ),
                )
                staff_travel += slot.travel_time_from_previous

            if job_assignments:
                start_loc = assignment.staff.start_location
                start_lat = float(start_loc.latitude) if start_loc.latitude else None
                start_lng = float(start_loc.longitude) if start_loc.longitude else None
                assignments.append(
                    ScheduleStaffAssignment(
                        staff_id=assignment.staff.id,
                        staff_name=assignment.staff.name,
                        start_lat=start_lat,
                        start_lng=start_lng,
                        jobs=job_assignments,
                        total_jobs=len(job_assignments),
                        total_travel_minutes=staff_travel,
                        first_job_start=job_assignments[0].start_time,
                        last_job_end=job_assignments[-1].end_time,
                    ),
                )
                total_travel += staff_travel

        # Build unassigned jobs list
        unassigned: list[UnassignedJob] = []
        assigned_ids = {slot.job.id for slots in time_slots.values() for slot in slots}

        unassigned.extend(
            UnassignedJob(
                job_id=job.id,
                customer_name=self._get_job_customer_name(job),
                service_type=self._get_job_service_type(job),
                reason="Could not fit in schedule",
            )
            for job in original_jobs
            if job.id not in assigned_ids
        )

        elapsed = time_module.time() - start_time

        return ScheduleGenerateResponse(
            schedule_date=schedule_date,
            is_feasible=solution.is_feasible(),
            hard_score=solution.hard_score,
            soft_score=solution.soft_score,
            assignments=assignments,
            unassigned_jobs=unassigned,
            total_jobs=len(original_jobs),
            total_assigned=len(original_jobs) - len(unassigned),
            total_travel_minutes=total_travel,
            optimization_time_seconds=round(elapsed, 2),
        )

    def insert_emergency_job(
        self,
        job_id: UUID,
        target_date: date,
        priority_level: int = 2,
        timeout_seconds: int = 15,
    ) -> EmergencyInsertResponse:
        """Insert an emergency job into an existing schedule.

        Args:
            job_id: ID of the job to insert
            target_date: Date to insert the job
            priority_level: Priority (2=urgent, 3=emergency)
            timeout_seconds: Max time for re-optimization

        Returns:
            EmergencyInsertResponse with result

        Validates: Requirements 9.1, 9.2, 9.3, 9.5
        """
        self.log_started(
            "insert_emergency_job",
            job_id=str(job_id),
            target_date=str(target_date),
        )

        # Load the job
        job = self.db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return EmergencyInsertResponse(
                success=False,
                job_id=job_id,
                target_date=target_date,
                message="Job not found",
            )

        # Update job priority
        job.priority_level = priority_level

        # Load available staff for the date
        staff_with_availability = self._load_available_staff(target_date)
        if not staff_with_availability:
            return EmergencyInsertResponse(
                success=False,
                job_id=job_id,
                target_date=target_date,
                constraint_violations=["No staff available on this date"],
                message="No staff available",
            )

        # Load existing scheduled jobs for the date
        existing_jobs = self._load_jobs_for_date(target_date)

        # Add emergency job if not already in list
        if job not in existing_jobs:
            existing_jobs.append(job)

        # Convert to schedule domain objects
        schedule_jobs = [self._job_to_schedule_job(j) for j in existing_jobs]
        schedule_staff = [
            self._staff_to_schedule_staff(s, a) for s, a in staff_with_availability
        ]

        # Re-optimize with emergency job having high priority
        solver = ScheduleSolverService(timeout_seconds=timeout_seconds)
        solution = solver.solve(target_date, schedule_jobs, schedule_staff)

        # Find where the emergency job was assigned
        assigned_staff = None
        scheduled_time = None
        for assignment in solution.assignments:
            for sched_job in assignment.jobs:
                if sched_job.id == job_id:
                    assigned_staff = assignment.staff
                    # Calculate time slot
                    time_slots = solver.calculate_time_slots(solution)
                    slots = time_slots.get(assignment.staff.id, [])
                    for slot in slots:
                        if slot.job.id == job_id:
                            scheduled_time = slot.start_time
                            break
                    break

        if assigned_staff and scheduled_time:
            self.log_completed(
                "insert_emergency_job",
                success=True,
                staff_id=str(assigned_staff.id),
            )
            return EmergencyInsertResponse(
                success=True,
                job_id=job_id,
                target_date=target_date,
                assigned_staff_id=assigned_staff.id,
                assigned_staff_name=assigned_staff.name,
                scheduled_time=scheduled_time,
                message="Emergency job successfully inserted",
            )

        self.log_completed("insert_emergency_job", success=False)
        return EmergencyInsertResponse(
            success=False,
            job_id=job_id,
            target_date=target_date,
            constraint_violations=["Could not fit job in schedule"],
            message="Unable to schedule emergency job",
        )

    def reoptimize_schedule(
        self,
        target_date: date,
        timeout_seconds: int = 15,
    ) -> ScheduleGenerateResponse:
        """Re-optimize an existing schedule.

        Args:
            target_date: Date to re-optimize
            timeout_seconds: Max optimization time

        Returns:
            Updated schedule response
        """
        self.log_started("reoptimize_schedule", target_date=str(target_date))
        return self.generate_schedule(target_date, timeout_seconds)
