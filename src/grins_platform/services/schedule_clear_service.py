"""Schedule Clear Service for clearing schedules and resetting jobs.

This service handles the business logic for clearing schedules,
creating audit logs, resetting job statuses, and restoring cleared schedules.

Requirements: 3.1-3.7, 5.1-5.6, 6.1-6.5
"""

from __future__ import annotations

from datetime import date, datetime, time
from typing import TYPE_CHECKING, Any
from uuid import UUID

from grins_platform.exceptions import ScheduleClearAuditNotFoundError
from grins_platform.log_config import LoggerMixin
from grins_platform.models.enums import JobStatus
from grins_platform.schemas.schedule_clear import (
    ScheduleClearAuditDetailResponse,
    ScheduleClearAuditResponse,
    ScheduleClearResponse,
    ScheduleRestoreResponse,
)

if TYPE_CHECKING:
    from grins_platform.repositories.appointment_repository import (
        AppointmentRepository,
    )
    from grins_platform.repositories.job_repository import JobRepository
    from grins_platform.repositories.schedule_clear_audit_repository import (
        ScheduleClearAuditRepository,
    )


class ScheduleClearService(LoggerMixin):
    """Service for schedule clear operations.

    This class handles all business logic for clearing schedules,
    including audit logging and job status resets.

    Attributes:
        appointment_repository: Repository for appointment operations
        job_repository: Repository for job operations
        audit_repository: Repository for audit log operations

    Validates: Requirements 3.1-3.7, 5.1-5.6, 6.1-6.5
    """

    DOMAIN = "schedule"

    def __init__(
        self,
        appointment_repository: AppointmentRepository,
        job_repository: JobRepository,
        audit_repository: ScheduleClearAuditRepository,
    ) -> None:
        """Initialize service with repositories.

        Args:
            appointment_repository: Repository for appointment operations
            job_repository: Repository for job operations
            audit_repository: Repository for audit log operations
        """
        super().__init__()
        self.appointment_repository = appointment_repository
        self.job_repository = job_repository
        self.audit_repository = audit_repository

    async def clear_schedule(
        self,
        schedule_date: date,
        cleared_by: UUID | None = None,
        notes: str | None = None,
    ) -> ScheduleClearResponse:
        """Clear all appointments for a specific date.

        This method:
        1. Gets all appointments for the date
        2. Serializes appointment data for audit
        3. Finds jobs with status 'scheduled' to reset
        4. Creates audit log before deletion
        5. Deletes appointments
        6. Resets job statuses to 'approved'
        7. Returns response with counts

        Args:
            schedule_date: Date to clear appointments for
            cleared_by: Staff ID who performed the clear
            notes: Optional notes about the clear operation

        Returns:
            ScheduleClearResponse with audit ID and counts

        Validates: Requirements 3.1-3.7
        """
        self.log_started(
            "clear_schedule",
            schedule_date=str(schedule_date),
            cleared_by=str(cleared_by) if cleared_by else None,
        )

        # Get all appointments for the date
        appointments = await self.appointment_repository.get_daily_schedule(
            schedule_date=schedule_date,
            include_relationships=True,
        )

        # Serialize appointment data for audit
        appointments_data = self._serialize_appointments(appointments)

        # Find jobs with status 'scheduled' to reset
        jobs_to_reset: list[UUID] = []
        for appointment in appointments:
            job = await self.job_repository.get_by_id(appointment.job_id)
            if job and job.status == JobStatus.SCHEDULED.value:
                jobs_to_reset.append(job.id)

        # Create audit log before deletion
        audit = await self.audit_repository.create(
            schedule_date=schedule_date,
            appointments_data=appointments_data,
            jobs_reset=jobs_to_reset,
            appointment_count=len(appointments),
            cleared_by=cleared_by,
            notes=notes,
        )

        # Delete appointments
        for appointment in appointments:
            _ = await self.appointment_repository.delete(appointment.id)

        # Reset job statuses to 'approved'
        for job_id in jobs_to_reset:
            _ = await self.job_repository.update(
                job_id=job_id,
                data={"status": JobStatus.APPROVED.value},
            )

        self.log_completed(
            "clear_schedule",
            audit_id=str(audit.id),
            appointments_deleted=len(appointments),
            jobs_reset=len(jobs_to_reset),
        )

        return ScheduleClearResponse(
            audit_id=audit.id,
            schedule_date=schedule_date,
            appointments_deleted=len(appointments),
            jobs_reset=len(jobs_to_reset),
            cleared_at=audit.cleared_at,
        )

    async def get_recent_clears(
        self,
        hours: int = 24,
    ) -> list[ScheduleClearAuditResponse]:
        """Get recently cleared schedules.

        Args:
            hours: Number of hours to look back (default 24)

        Returns:
            List of audit records within the time window

        Validates: Requirements 6.1-6.5
        """
        self.log_started("get_recent_clears", hours=hours)

        audits = await self.audit_repository.find_since(hours=hours)

        responses = [
            ScheduleClearAuditResponse.model_validate(audit) for audit in audits
        ]

        self.log_completed("get_recent_clears", count=len(responses))
        return responses

    async def get_clear_details(
        self,
        audit_id: UUID,
    ) -> ScheduleClearAuditDetailResponse:
        """Get detailed audit record by ID.

        Args:
            audit_id: UUID of the audit record

        Returns:
            Detailed audit record with appointments_data and jobs_reset

        Raises:
            ScheduleClearAuditNotFoundError: If audit record not found

        Validates: Requirement 6.3
        """
        self.log_started("get_clear_details", audit_id=str(audit_id))

        audit = await self.audit_repository.get_by_id(audit_id)

        if not audit:
            self.log_rejected(
                "get_clear_details",
                reason="audit_not_found",
                audit_id=str(audit_id),
            )
            raise ScheduleClearAuditNotFoundError(audit_id)

        self.log_completed("get_clear_details", audit_id=str(audit_id))
        response: ScheduleClearAuditDetailResponse = (
            ScheduleClearAuditDetailResponse.model_validate(audit)
        )
        return response

    def _serialize_appointments(
        self,
        appointments: list[Any],
    ) -> list[dict[str, Any]]:
        """Serialize appointments for audit storage.

        Args:
            appointments: List of appointment objects

        Returns:
            List of serialized appointment dictionaries
        """
        serialized: list[dict[str, Any]] = []

        for appointment in appointments:
            data: dict[str, Any] = {
                "id": str(appointment.id),
                "job_id": str(appointment.job_id),
                "staff_id": str(appointment.staff_id),
                "scheduled_date": str(appointment.scheduled_date),
                "time_window_start": str(appointment.time_window_start),
                "time_window_end": str(appointment.time_window_end),
                "status": appointment.status,
                "notes": appointment.notes,
                "route_order": appointment.route_order,
                "estimated_arrival": (
                    str(appointment.estimated_arrival)
                    if appointment.estimated_arrival
                    else None
                ),
            }
            serialized.append(data)

        return serialized

    async def restore_schedule(
        self,
        audit_id: UUID,
        restored_by: UUID | None = None,
    ) -> ScheduleRestoreResponse:
        """Restore a previously cleared schedule from audit data.

        This method:
        1. Gets the audit record with appointment data
        2. Recreates appointments from the stored data
        3. Updates job statuses back to 'scheduled'
        4. Deletes the audit record after successful restore

        Args:
            audit_id: UUID of the audit record to restore from
            restored_by: Staff ID who performed the restore

        Returns:
            ScheduleRestoreResponse with counts of restored items

        Raises:
            ScheduleClearAuditNotFoundError: If audit record not found
        """
        self.log_started(
            "restore_schedule",
            audit_id=str(audit_id),
            restored_by=str(restored_by) if restored_by else None,
        )

        # Get the audit record
        audit = await self.audit_repository.get_by_id(audit_id)
        if not audit:
            self.log_rejected(
                "restore_schedule",
                reason="audit_not_found",
                audit_id=str(audit_id),
            )
            raise ScheduleClearAuditNotFoundError(audit_id)

        appointments_restored = 0
        jobs_updated = 0

        # Recreate appointments from stored data
        for apt_data in audit.appointments_data:
            try:
                # Parse time strings back to time objects
                time_start = self._parse_time(apt_data.get("time_window_start", ""))
                time_end = self._parse_time(apt_data.get("time_window_end", ""))
                estimated_arrival = None
                if apt_data.get("estimated_arrival"):
                    estimated_arrival = self._parse_time(apt_data["estimated_arrival"])

                # Parse date string back to date object
                scheduled_date = datetime.strptime(
                    apt_data.get("scheduled_date", ""),
                    "%Y-%m-%d",
                ).date()

                # Create the appointment
                _ = await self.appointment_repository.create(
                    job_id=UUID(apt_data["job_id"]),
                    staff_id=UUID(apt_data["staff_id"]),
                    scheduled_date=scheduled_date,
                    time_window_start=time_start,
                    time_window_end=time_end,
                    status=apt_data.get("status", "scheduled"),
                    notes=apt_data.get("notes"),
                    route_order=apt_data.get("route_order"),
                    estimated_arrival=estimated_arrival,
                )
                appointments_restored += 1
            except (ValueError, KeyError) as e:  # noqa: PERF203
                self.log_failed(
                    "restore_schedule",
                    error=e,
                    appointment_data=apt_data,
                )
                # Continue with other appointments even if one fails
                continue

        # Update job statuses back to 'scheduled'
        for job_id_str in audit.jobs_reset:
            try:
                job_id = UUID(job_id_str) if isinstance(job_id_str, str) else job_id_str
                _ = await self.job_repository.update(
                    job_id=job_id,
                    data={"status": JobStatus.SCHEDULED.value},
                )
                jobs_updated += 1
            except (ValueError, KeyError) as e:  # noqa: PERF203
                self.log_failed(
                    "restore_schedule",
                    error=e,
                    job_id=str(job_id_str),
                )
                continue

        # Delete the audit record after successful restore
        _ = await self.audit_repository.delete(audit_id)

        self.log_completed(
            "restore_schedule",
            audit_id=str(audit_id),
            appointments_restored=appointments_restored,
            jobs_updated=jobs_updated,
        )

        return ScheduleRestoreResponse(
            audit_id=audit_id,
            schedule_date=audit.schedule_date,
            appointments_restored=appointments_restored,
            jobs_updated=jobs_updated,
            restored_at=datetime.now(),
        )

    def _parse_time(self, time_str: str) -> time:
        """Parse a time string into a time object.

        Args:
            time_str: Time string in HH:MM:SS or HH:MM format

        Returns:
            time object
        """
        if not time_str:
            return time(0, 0, 0)

        # Handle different time formats
        time_str = time_str.strip()
        if len(time_str) == 5:  # HH:MM format
            return datetime.strptime(time_str, "%H:%M").time()
        if len(time_str) == 8:  # HH:MM:SS format
            return datetime.strptime(time_str, "%H:%M:%S").time()
        # Try to parse as full datetime and extract time
        try:
            return datetime.fromisoformat(time_str).time()
        except ValueError:
            return time(0, 0, 0)
