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
# Cross-references to existing test files for completeness
# =============================================================================

# The following imports verify that the existing test modules are importable
# and serve as documentation of the full draft mode test coverage.

from grins_platform.tests.unit.test_send_confirmation import (  # noqa: E402, F401
    TestSendConfirmationService,
)
from grins_platform.tests.unit.test_bulk_send_confirmations import (  # noqa: E402, F401
    TestBulkSendConfirmationsService,
)
from grins_platform.tests.unit.test_reschedule_detection import (  # noqa: E402, F401
    TestRescheduleDetection,
)
from grins_platform.tests.unit.test_cancellation_sms import (  # noqa: E402, F401
    TestCancellationSmsLogic,
)
