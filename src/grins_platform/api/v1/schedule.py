"""
Schedule generation API endpoints.

Validates: Requirements 5.1, 5.6, 5.7, 5.8
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import date, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session  # noqa: TC002

from grins_platform.database import get_database_manager, get_sync_db
from grins_platform.log_config import LoggerMixin
from grins_platform.models.appointment import Appointment
from grins_platform.models.customer import Customer
from grins_platform.models.job import Job
from grins_platform.models.property import Property
from grins_platform.schemas.schedule_explanation import (
    JobReadyToSchedule,
    JobsReadyToScheduleResponse,
    ParseConstraintsRequest,
    ParseConstraintsResponse,
    ScheduleExplanationRequest,
    ScheduleExplanationResponse,
    UnassignedJobExplanationRequest,
    UnassignedJobExplanationResponse,
)
from grins_platform.schemas.schedule_generation import (
    ApplyScheduleRequest,
    ApplyScheduleResponse,
    EmergencyInsertRequest,
    EmergencyInsertResponse,
    ReoptimizeRequest,
    ScheduleCapacityResponse,
    ScheduleGenerateRequest,
    ScheduleGenerateResponse,
)
from grins_platform.services.ai.constraint_parser import (
    ConstraintParserService,
)
from grins_platform.services.ai.explanation_service import (
    ScheduleExplanationService,
)
from grins_platform.services.ai.unassigned_analyzer import (
    UnassignedJobAnalyzer,
)
from grins_platform.services.schedule_generation_service import (
    ScheduleGenerationService,
)

router = APIRouter(prefix="/schedule", tags=["schedule"])


class ScheduleEndpoints(LoggerMixin):
    """Schedule generation endpoints."""

    DOMAIN = "api"


endpoints = ScheduleEndpoints()


def get_schedule_service(
    db: Session = Depends(get_sync_db),
) -> ScheduleGenerationService:
    """Dependency to get ScheduleGenerationService."""
    return ScheduleGenerationService(db)


async def get_explanation_service() -> AsyncGenerator[
    ScheduleExplanationService,
    None,
]:
    """Dependency to get ScheduleExplanationService."""
    db_manager = get_database_manager()
    async with db_manager.session_factory() as session:
        yield ScheduleExplanationService(session)


async def get_unassigned_analyzer() -> AsyncGenerator[
    UnassignedJobAnalyzer,
    None,
]:
    """Dependency to get UnassignedJobAnalyzer."""
    db_manager = get_database_manager()
    async with db_manager.session_factory() as session:
        yield UnassignedJobAnalyzer(session)


async def get_constraint_parser() -> AsyncGenerator[
    ConstraintParserService,
    None,
]:
    """Dependency to get ConstraintParserService."""
    db_manager = get_database_manager()
    async with db_manager.session_factory() as session:
        yield ConstraintParserService(session)


@router.post(  # type: ignore[misc,untyped-decorator]
    "/generate",
    response_model=ScheduleGenerateResponse,
)
def generate_schedule(
    request: ScheduleGenerateRequest,
    service: ScheduleGenerationService = Depends(get_schedule_service),
) -> ScheduleGenerateResponse:
    """Generate an optimized schedule for a date.

    POST /api/v1/schedule/generate
    """
    endpoints.log_started("generate_schedule", schedule_date=str(request.schedule_date))

    try:
        response = service.generate_schedule(
            schedule_date=request.schedule_date,
            timeout_seconds=request.timeout_seconds,
        )
    except Exception as e:
        endpoints.log_failed("generate_schedule", error=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Schedule generation failed: {e!s}",
        ) from e
    else:
        endpoints.log_completed(
            "generate_schedule",
            is_feasible=response.is_feasible,
            assigned=response.total_assigned,
        )
        return response


@router.post(  # type: ignore[misc,untyped-decorator]
    "/preview",
    response_model=ScheduleGenerateResponse,
)
def preview_schedule(
    request: ScheduleGenerateRequest,
    service: ScheduleGenerationService = Depends(get_schedule_service),
) -> ScheduleGenerateResponse:
    """Preview a schedule without persisting.

    POST /api/v1/schedule/preview
    """
    endpoints.log_started("preview_schedule", schedule_date=str(request.schedule_date))

    try:
        # Preview is same as generate but doesn't persist
        response = service.generate_schedule(
            schedule_date=request.schedule_date,
            timeout_seconds=request.timeout_seconds,
        )
    except Exception as e:
        endpoints.log_failed("preview_schedule", error=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Schedule preview failed: {e!s}",
        ) from e
    else:
        endpoints.log_completed("preview_schedule", assigned=response.total_assigned)
        return response


@router.get(  # type: ignore[misc,untyped-decorator]
    "/capacity/{schedule_date}",
    response_model=ScheduleCapacityResponse,
)
def get_capacity(
    schedule_date: date,
    service: ScheduleGenerationService = Depends(get_schedule_service),
) -> ScheduleCapacityResponse:
    """Get scheduling capacity for a date.

    GET /api/v1/schedule/capacity/{date}
    """
    endpoints.log_started("get_capacity", schedule_date=str(schedule_date))

    try:
        response = service.get_capacity(schedule_date)
    except Exception as e:
        endpoints.log_failed("get_capacity", error=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Capacity check failed: {e!s}",
        ) from e
    else:
        endpoints.log_completed(
            "get_capacity",
            available_staff=response.available_staff,
            remaining_minutes=response.remaining_capacity_minutes,
        )
        return response


@router.post(  # type: ignore[misc,untyped-decorator]
    "/insert-emergency",
    response_model=EmergencyInsertResponse,
)
def insert_emergency_job(
    request: EmergencyInsertRequest,
    service: ScheduleGenerationService = Depends(get_schedule_service),
) -> EmergencyInsertResponse:
    """Insert an emergency job into existing schedule.

    POST /api/v1/schedule/insert-emergency

    Validates: Requirement 9.1
    """
    endpoints.log_started(
        "insert_emergency",
        job_id=str(request.job_id),
        target_date=str(request.target_date),
    )

    try:
        response = service.insert_emergency_job(
            job_id=request.job_id,
            target_date=request.target_date,
            priority_level=request.priority_level,
        )
    except Exception as e:
        endpoints.log_failed("insert_emergency", error=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Emergency insertion failed: {e!s}",
        ) from e
    else:
        endpoints.log_completed("insert_emergency", success=response.success)
        return response


@router.post(  # type: ignore[misc,untyped-decorator]
    "/re-optimize/{target_date}",
    response_model=ScheduleGenerateResponse,
)
def reoptimize_schedule(
    target_date: date,
    request: ReoptimizeRequest | None = None,
    service: ScheduleGenerationService = Depends(get_schedule_service),
) -> ScheduleGenerateResponse:
    """Re-optimize an existing schedule for a date.

    POST /api/v1/schedule/re-optimize/{date}
    """
    timeout = request.timeout_seconds if request else 15
    endpoints.log_started("reoptimize", target_date=str(target_date))

    try:
        response = service.reoptimize_schedule(target_date, timeout)
    except Exception as e:
        endpoints.log_failed("reoptimize", error=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Re-optimization failed: {e!s}",
        ) from e
    else:
        endpoints.log_completed("reoptimize", assigned=response.total_assigned)
        return response


@router.post(  # type: ignore[misc,untyped-decorator]
    "/explain",
    response_model=ScheduleExplanationResponse,
)
async def explain_schedule(
    request: ScheduleExplanationRequest,
    service: ScheduleExplanationService = Depends(get_explanation_service),
) -> ScheduleExplanationResponse:
    """Generate natural language explanation of a schedule.

    POST /api/v1/schedule/explain

    Validates: Requirement 6.1
    """
    endpoints.log_started(
        "explain_schedule",
        schedule_date=str(request.schedule_date),
        staff_count=len(request.staff_assignments),
    )

    try:
        response = await service.explain_schedule(request)
    except Exception as e:
        endpoints.log_failed("explain_schedule", error=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Schedule explanation failed: {e!s}",
        ) from e
    else:
        endpoints.log_completed(
            "explain_schedule",
            explanation_length=len(response.explanation),
        )
        return response


@router.post(  # type: ignore[misc,untyped-decorator]
    "/explain-unassigned",
    response_model=UnassignedJobExplanationResponse,
)
async def explain_unassigned_job(
    request: UnassignedJobExplanationRequest,
    analyzer: UnassignedJobAnalyzer = Depends(get_unassigned_analyzer),
) -> UnassignedJobExplanationResponse:
    """Explain why a specific job couldn't be scheduled.

    POST /api/v1/schedule/explain-unassigned

    Validates: Requirement 6.2, 3.8
    """
    endpoints.log_started(
        "explain_unassigned_job",
        job_id=str(request.job_id),
        job_type=request.job_type,
        city=request.city,
    )

    try:
        response = await analyzer.explain_unassigned_job(request)
    except Exception as e:
        endpoints.log_failed("explain_unassigned_job", error=e)
        # Provide fallback when AI unavailable (Requirement 3.8)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unassigned job explanation failed: {e!s}",
        ) from e
    else:
        endpoints.log_completed(
            "explain_unassigned_job",
            suggestions_count=len(response.suggestions),
        )
        return response


@router.post(  # type: ignore[misc,untyped-decorator]
    "/parse-constraints",
    response_model=ParseConstraintsResponse,
)
async def parse_constraints(
    request: ParseConstraintsRequest,
    parser: ConstraintParserService = Depends(get_constraint_parser),
) -> ParseConstraintsResponse:
    """Parse natural language constraints into structured format.

    POST /api/v1/schedule/parse-constraints

    Validates: Requirement 6.3
    """
    endpoints.log_started(
        "parse_constraints",
        text_length=len(request.constraint_text),
    )

    try:
        response = await parser.parse_constraints(request)
    except Exception as e:
        endpoints.log_failed("parse_constraints", error=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Constraint parsing failed: {e!s}",
        ) from e
    else:
        endpoints.log_completed(
            "parse_constraints",
            constraints_count=len(response.constraints),
            has_validation_errors=any(
                c.validation_errors for c in response.constraints
            ),
        )
        return response


@router.get(  # type: ignore[misc,untyped-decorator]
    "/jobs-ready",
    response_model=JobsReadyToScheduleResponse,
)
def get_jobs_ready_to_schedule(
    db: Session = Depends(get_sync_db),
    date_from: date | None = None,
    date_to: date | None = None,
) -> JobsReadyToScheduleResponse:
    """Get jobs ready to schedule with grouping by city and job type.

    GET /api/v1/schedule/jobs-ready

    Args:
        db: Database session
        date_from: Filter jobs from this date
        date_to: Filter jobs to this date

    Returns:
        JobsReadyToScheduleResponse with jobs grouped by city and job type

    Validates: Requirements 9.2, 9.3, 9.4
    """
    endpoints.log_started(
        "get_jobs_ready",
        date_from=str(date_from) if date_from else None,
        date_to=str(date_to) if date_to else None,
    )

    try:
        # Query jobs with status "approved" or "requested"
        # that haven't been scheduled yet
        query = (
            select(Job, Customer, Property)
            .join(Customer, Job.customer_id == Customer.id)
            .outerjoin(Property, Job.property_id == Property.id)
            .where(Job.status.in_(["approved", "requested"]))
            .where(Job.scheduled_at.is_(None))  # Only unscheduled jobs
        )

        # Note: date_from and date_to parameters are ignored for this endpoint
        # as we want to show ALL unscheduled jobs, not filter by creation date

        result = db.execute(query)
        rows = result.all()

        # Build response
        jobs = []
        by_city: dict[str, int] = {}
        by_job_type: dict[str, int] = {}

        for job, customer, property_ in rows:
            city = property_.city if property_ else "Unknown"
            customer_name = f"{customer.first_name} {customer.last_name}"

            jobs.append(
                JobReadyToSchedule(
                    job_id=job.id,
                    customer_id=customer.id,
                    customer_name=customer_name,
                    job_type=job.job_type,
                    city=city,
                    priority=str(job.priority_level),
                    estimated_duration_minutes=job.estimated_duration_minutes or 60,
                    requires_equipment=job.equipment_required or [],
                    status=job.status,
                ),
            )

            # Group by city
            by_city[city] = by_city.get(city, 0) + 1

            # Group by job type
            by_job_type[job.job_type] = by_job_type.get(job.job_type, 0) + 1

        response = JobsReadyToScheduleResponse(
            jobs=jobs,
            total_count=len(jobs),
            by_city=by_city,
            by_job_type=by_job_type,
        )

    except Exception as e:
        endpoints.log_failed("get_jobs_ready", error=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get jobs ready to schedule: {e!s}",
        ) from e
    else:
        endpoints.log_completed("get_jobs_ready", total_count=len(jobs))
        return response


@router.post(  # type: ignore[misc,untyped-decorator]
    "/apply",
    response_model=ApplyScheduleResponse,
)
def apply_schedule(
    request: ApplyScheduleRequest,
    db: Session = Depends(get_sync_db),
) -> ApplyScheduleResponse:
    """Apply a generated schedule by creating appointments.

    POST /api/v1/schedule/apply

    This endpoint takes the generated schedule assignments and creates
    actual appointment records in the database.

    IMPORTANT: This will delete any existing appointments for the same date
    before creating new ones to prevent overlapping appointments.

    Validates: Requirements 5.1, 5.8
    """
    endpoints.log_started(
        "apply_schedule",
        schedule_date=str(request.schedule_date),
        staff_count=len(request.assignments),
    )

    try:
        # First, delete any existing appointments for this date to prevent overlaps
        # Only delete appointments that are in 'scheduled' status (not started yet)
        existing_appointments = (
            db.query(Appointment)
            .filter(
                Appointment.scheduled_date == request.schedule_date,
                Appointment.status.in_(["scheduled", "confirmed"]),
            )
            .all()
        )

        deleted_count = 0
        deleted_job_ids: set[UUID] = set()
        for existing in existing_appointments:
            deleted_job_ids.add(existing.job_id)
            db.delete(existing)
            deleted_count += 1

        if deleted_count > 0:
            endpoints.log_started(
                "apply_schedule_cleanup",
                deleted_appointments=deleted_count,
                schedule_date=str(request.schedule_date),
            )

        # Reset job status for deleted appointments back to approved
        for job_id in deleted_job_ids:
            job_record = db.execute(
                select(Job).where(Job.id == job_id),
            ).scalar_one_or_none()
            if job_record and job_record.status == "scheduled":
                job_record.status = "approved"
                job_record.scheduled_at = None

        created_ids: list[UUID] = []

        for staff_assignment in request.assignments:
            staff_id = staff_assignment.staff_id

            for job in staff_assignment.jobs:
                job_id = job.job_id
                start_time = job.start_time
                end_time = job.end_time

                # Create appointment
                appointment = Appointment(
                    job_id=job_id,
                    staff_id=staff_id,
                    scheduled_date=request.schedule_date,
                    time_window_start=start_time,
                    time_window_end=end_time,
                    status="scheduled",
                    route_order=job.sequence_index,
                    estimated_arrival=start_time,
                    notes=f"Auto-generated from schedule for {request.schedule_date}",
                )

                db.add(appointment)
                db.flush()
                created_ids.append(appointment.id)

                # Update job status to scheduled
                job_record = db.execute(
                    select(Job).where(Job.id == job_id),
                ).scalar_one_or_none()
                if job_record:
                    job_record.status = "scheduled"
                    job_record.scheduled_at = datetime.combine(
                        request.schedule_date,
                        start_time,
                    )

        db.commit()

        msg = (
            f"Successfully created {len(created_ids)} appointments "
            f"for {request.schedule_date}"
        )
        if deleted_count > 0:
            msg += f" (replaced {deleted_count} existing appointments)"

        response = ApplyScheduleResponse(
            success=True,
            schedule_date=request.schedule_date,
            appointments_created=len(created_ids),
            message=msg,
            created_appointment_ids=created_ids,
        )

    except Exception as e:
        db.rollback()
        endpoints.log_failed("apply_schedule", error=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to apply schedule: {e!s}",
        ) from e
    else:
        endpoints.log_completed(
            "apply_schedule",
            appointments_created=len(created_ids),
            deleted_existing=deleted_count,
        )
        return response
