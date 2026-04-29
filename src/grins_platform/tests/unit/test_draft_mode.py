"""Comprehensive unit tests for Schedule Draft Mode (Req 8).

This file consolidates all draft mode test scenarios. Most scenarios are
already covered in dedicated test files created during tasks 11.3–11.6:

- test_send_confirmation.py (task 11.3): Req 8.4, 8.12
  • send-confirmation sends SMS and transitions DRAFT → SCHEDULED
  • send-confirmation on non-DRAFT appointment returns 422

- test_bulk_send_confirmations.py (task 11.4): Req 8.6, 8.13
  • bulk send sends SMS for all DRAFT appointments in range

- test_reschedule_detection.py (task 11.5): Req 8.8, 8.9
  • moving a DRAFT appointment does not send SMS
  • moving a SCHEDULED appointment sends reschedule notification

- test_cancellation_sms.py (task 11.6): Req 8.10, 8.11
  • deleting a DRAFT appointment does not send SMS
  • deleting a SCHEDULED appointment sends cancellation SMS

This file adds the one scenario NOT covered elsewhere:
- Creating an appointment sets status to DRAFT and does NOT send SMS (Req 8.2)

It also re-imports/references the existing tests for completeness.

Validates: Requirements 8.2, 8.4, 8.6, 8.8, 8.9, 8.10, 8.11, 8.12
"""

from __future__ import annotations

from datetime import date, time
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from grins_platform.models.enums import AppointmentStatus, JobStatus

# =============================================================================
# Helpers
# =============================================================================


def _build_service() -> tuple:
    """Build an AppointmentService with mocked repositories."""
    from grins_platform.services.appointment_service import AppointmentService

    mock_appt_repo = AsyncMock()
    mock_appt_repo.session = AsyncMock()

    mock_job_repo = AsyncMock()
    mock_staff_repo = AsyncMock()

    service = AppointmentService(
        appointment_repository=mock_appt_repo,
        job_repository=mock_job_repo,
        staff_repository=mock_staff_repo,
    )
    return service, mock_appt_repo, mock_job_repo, mock_staff_repo


# =============================================================================
# NEW: Appointment creation sets DRAFT and does NOT send SMS (Req 8.2)
# =============================================================================


class TestAppointmentCreationDraftMode:
    """Tests that appointment creation sets DRAFT status and sends no SMS.

    Validates: Requirement 8.2
    """

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_appointment_sets_draft_status(self) -> None:
        """Creating an appointment sets initial status to DRAFT, not SCHEDULED.

        Validates: Requirement 8.2
        """
        service, mock_appt_repo, mock_job_repo, mock_staff_repo = _build_service()

        job_id = uuid4()
        staff_id = uuid4()

        mock_job = MagicMock()
        mock_job.id = job_id
        mock_job.status = JobStatus.TO_BE_SCHEDULED.value

        mock_staff = MagicMock()
        mock_staff.id = staff_id

        mock_appointment = MagicMock()
        mock_appointment.id = uuid4()
        mock_appointment.job_id = job_id
        mock_appointment.status = AppointmentStatus.DRAFT.value

        mock_job_repo.get_by_id.return_value = mock_job
        mock_staff_repo.get_by_id.return_value = mock_staff
        mock_appt_repo.create.return_value = mock_appointment

        data = MagicMock()
        data.job_id = job_id
        data.staff_id = staff_id
        data.scheduled_date = date(2025, 6, 2)
        data.time_window_start = time(9, 0)
        data.time_window_end = time(11, 0)
        data.notes = None

        result = await service.create_appointment(data)

        # Verify the repository was called with DRAFT status
        mock_appt_repo.create.assert_called_once()
        call_kwargs = mock_appt_repo.create.call_args
        assert call_kwargs.kwargs["status"] == AppointmentStatus.DRAFT.value

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_appointment_does_not_send_sms(self) -> None:
        """Creating an appointment does NOT trigger any SMS send.

        Validates: Requirement 8.2
        """
        service, mock_appt_repo, mock_job_repo, mock_staff_repo = _build_service()

        job_id = uuid4()
        staff_id = uuid4()

        mock_job = MagicMock()
        mock_job.id = job_id
        mock_job.status = JobStatus.TO_BE_SCHEDULED.value

        mock_staff = MagicMock()
        mock_staff.id = staff_id

        mock_appointment = MagicMock()
        mock_appointment.id = uuid4()
        mock_appointment.job_id = job_id
        mock_appointment.status = AppointmentStatus.DRAFT.value

        mock_job_repo.get_by_id.return_value = mock_job
        mock_staff_repo.get_by_id.return_value = mock_staff
        mock_appt_repo.create.return_value = mock_appointment

        data = MagicMock()
        data.job_id = job_id
        data.staff_id = staff_id
        data.scheduled_date = date(2025, 6, 2)
        data.time_window_start = time(9, 0)
        data.time_window_end = time(11, 0)
        data.notes = None

        # Patch any SMS-related methods to ensure they are NOT called
        with (
            patch.object(
                service, "_send_confirmation_sms", new_callable=AsyncMock
            ) as mock_confirm_sms,
            patch.object(
                service, "_send_reschedule_sms", new_callable=AsyncMock
            ) as mock_reschedule_sms,
            patch.object(
                service, "_send_cancellation_sms", new_callable=AsyncMock
            ) as mock_cancel_sms,
        ):
            await service.create_appointment(data)

            mock_confirm_sms.assert_not_called()
            mock_reschedule_sms.assert_not_called()
            mock_cancel_sms.assert_not_called()


# =============================================================================
# CR-1: apply_schedule creates DRAFT appointments, not SCHEDULED
# =============================================================================


def _build_apply_schedule_request(
    *,
    job_id: uuid4 | None = None,
    staff_id: uuid4 | None = None,
    schedule_date: date | None = None,
) -> ApplyScheduleRequest:
    from grins_platform.schemas.schedule_generation import (
        ApplyScheduleRequest,
        ScheduleJobAssignment,
        ScheduleStaffAssignment,
    )

    return ApplyScheduleRequest(
        schedule_date=schedule_date or date(2025, 6, 2),
        assignments=[
            ScheduleStaffAssignment(
                staff_id=staff_id or uuid4(),
                staff_name="Test Tech",
                jobs=[
                    ScheduleJobAssignment(
                        job_id=job_id or uuid4(),
                        customer_name="Alice",
                        service_type="spring_startup",
                        start_time=time(9, 0),
                        end_time=time(11, 0),
                        duration_minutes=120,
                        travel_time_minutes=0,
                        sequence_index=0,
                    ),
                ],
            ),
        ],
    )


def _build_mock_sync_db() -> MagicMock:
    """Mock sync Session that tracks db.add() calls and returns no existing appts."""
    db = MagicMock()
    # .query(Appointment).filter(...).all() returns [] (no overlap cleanup needed)
    query_mock = MagicMock()
    query_mock.filter.return_value.all.return_value = []
    db.query.return_value = query_mock
    db.added_objects: list = []

    def _add(obj: object) -> None:
        # Assign an id so apply_schedule's created_ids.append(appointment.id) works.
        if getattr(obj, "id", None) is None:
            obj.id = uuid4()
        db.added_objects.append(obj)

    db.add.side_effect = _add
    db.flush = MagicMock()
    db.commit = MagicMock()
    db.rollback = MagicMock()
    db.delete = MagicMock()
    # .execute(select(Job)...).scalar_one_or_none() — only hit from the cleanup path
    # when deleted_job_ids is populated, which is empty in our test.
    execute_result = MagicMock()
    execute_result.scalar_one_or_none.return_value = None
    db.execute.return_value = execute_result
    return db


class TestApplyScheduleDraftMode:
    """apply_schedule bulk-creates appointments in DRAFT, not SCHEDULED.

    **Validates: CR-1 (bughunt 2026-04-16).** Before CR-1, the endpoint
    wrote ``status="scheduled"`` and set ``job.status="scheduled"`` /
    ``job.scheduled_at=...``, bypassing Draft Mode and the "no SMS until
    Send Confirmation" contract. Job stays in ``to_be_scheduled`` now.
    """

    @pytest.mark.unit
    def test_apply_schedule_creates_draft_appointments_not_scheduled(self) -> None:
        from grins_platform.api.v1.schedule import apply_schedule
        from grins_platform.models.appointment import Appointment

        db = _build_mock_sync_db()
        request = _build_apply_schedule_request()

        response = apply_schedule(request=request, db=db)

        created_appts = [o for o in db.added_objects if isinstance(o, Appointment)]
        assert len(created_appts) == 1
        assert created_appts[0].status == AppointmentStatus.DRAFT.value
        assert response.success is True
        assert response.appointments_created == 1

    @pytest.mark.unit
    def test_apply_schedule_does_not_promote_job_status(self) -> None:
        from grins_platform.api.v1.schedule import apply_schedule

        db = _build_mock_sync_db()
        # db.execute(...).scalar_one_or_none() MUST NOT be called with a Job
        # lookup in the create loop (the cleanup loop is bypassed because
        # no existing appointments were returned). Stub returns a job anyway
        # to catch regressions: if the old code path ran, the job's status
        # would be mutated.
        tracker_job = MagicMock()
        tracker_job.status = JobStatus.TO_BE_SCHEDULED.value
        tracker_job.scheduled_at = None
        db.execute.return_value.scalar_one_or_none.return_value = tracker_job

        request = _build_apply_schedule_request()

        apply_schedule(request=request, db=db)

        # Job status must remain TO_BE_SCHEDULED — Job.scheduled_at must stay None.
        assert tracker_job.status == JobStatus.TO_BE_SCHEDULED.value
        assert tracker_job.scheduled_at is None

    @pytest.mark.unit
    def test_apply_schedule_does_not_set_job_scheduled_at(self) -> None:
        """Separately asserts the Job.scheduled_at invariant.

        If someone re-introduces the job promotion but only updates
        ``status`` (not ``scheduled_at``), the previous test still fires;
        this second assertion nails the ``scheduled_at`` invariant.
        """
        from grins_platform.api.v1.schedule import apply_schedule

        db = _build_mock_sync_db()
        tracker_job = MagicMock()
        tracker_job.status = JobStatus.TO_BE_SCHEDULED.value
        tracker_job.scheduled_at = None
        db.execute.return_value.scalar_one_or_none.return_value = tracker_job

        request = _build_apply_schedule_request()
        apply_schedule(request=request, db=db)

        assert tracker_job.scheduled_at is None


# =============================================================================
# Cross-references to existing test files for completeness
# =============================================================================

# The following imports verify that the existing test modules are importable
# and serve as documentation of the full draft mode test coverage.

from grins_platform.tests.unit.test_bulk_send_confirmations import (  # noqa: F401
    TestBulkSendConfirmationsService,
)
from grins_platform.tests.unit.test_cancellation_sms import (  # noqa: F401
    TestCancellationSmsLogic,
)
from grins_platform.tests.unit.test_reschedule_detection import (  # noqa: F401
    TestRescheduleDetection,
)
from grins_platform.tests.unit.test_send_confirmation import (  # noqa: F401
    TestSendConfirmationService,
)
