"""Unit tests for cancellation SMS logic based on appointment state (task 11.6).

When a DRAFT appointment is deleted → no SMS (customer was never notified).
When a SCHEDULED or CONFIRMED appointment is deleted → send cancellation SMS.

Validates: Requirements 8.10, 8.11
"""

from __future__ import annotations

from datetime import date, time
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from grins_platform.models.enums import AppointmentStatus


def _make_mock_appointment(
    *,
    status: str = AppointmentStatus.DRAFT.value,
    scheduled_date: date | None = None,
    time_window_start: time | None = None,
    time_window_end: time | None = None,
) -> MagicMock:
    """Create a mock appointment with sensible defaults."""
    appt = MagicMock()
    appt.id = uuid4()
    appt.job_id = uuid4()
    appt.staff_id = uuid4()
    appt.status = status
    appt.scheduled_date = scheduled_date or date(2025, 7, 14)
    appt.time_window_start = time_window_start or time(9, 0)
    appt.time_window_end = time_window_end or time(11, 0)
    appt.can_transition_to = MagicMock(return_value=True)
    return appt


def _build_service() -> tuple:
    """Build an AppointmentService with mocked repositories."""
    from grins_platform.services.appointment_service import AppointmentService

    mock_appt_repo = AsyncMock()
    mock_appt_repo.session = AsyncMock()

    mock_job_repo = AsyncMock()
    mock_job_repo.get_by_id.return_value = MagicMock()

    service = AppointmentService(
        appointment_repository=mock_appt_repo,
        job_repository=mock_job_repo,
        staff_repository=AsyncMock(),
    )
    return service, mock_appt_repo


class TestCancellationSmsLogic:
    """Tests for cancellation SMS based on appointment state.

    Validates: Req 8.10, 8.11
    """

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_deleting_draft_appointment_does_not_send_sms(self) -> None:
        """Deleting a DRAFT appointment does NOT send cancellation SMS.

        Validates: Requirement 8.10
        """
        service, mock_appt_repo = _build_service()

        appt = _make_mock_appointment(status=AppointmentStatus.DRAFT.value)
        mock_appt_repo.get_by_id.return_value = appt
        mock_appt_repo.update_status.return_value = appt

        with (
            patch.object(
                service, "_send_cancellation_sms", new_callable=AsyncMock
            ) as mock_sms,
            patch(
                "grins_platform.services.appointment_service.clear_on_site_data",
                new_callable=AsyncMock,
            ),
        ):
            await service.cancel_appointment(appt.id)
            mock_sms.assert_not_called()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_deleting_scheduled_appointment_sends_cancellation_sms(
        self,
    ) -> None:
        """Deleting a SCHEDULED appointment sends cancellation SMS.

        Validates: Requirement 8.11
        """
        service, mock_appt_repo = _build_service()

        appt = _make_mock_appointment(status=AppointmentStatus.SCHEDULED.value)
        mock_appt_repo.get_by_id.return_value = appt
        mock_appt_repo.update_status.return_value = appt

        with (
            patch.object(
                service, "_send_cancellation_sms", new_callable=AsyncMock
            ) as mock_sms,
            patch(
                "grins_platform.services.appointment_service.clear_on_site_data",
                new_callable=AsyncMock,
            ),
        ):
            await service.cancel_appointment(appt.id)
            mock_sms.assert_called_once_with(mock_appt_repo.session, appt)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_deleting_confirmed_appointment_sends_cancellation_sms(
        self,
    ) -> None:
        """Deleting a CONFIRMED appointment sends cancellation SMS.

        Validates: Requirement 8.11
        """
        service, mock_appt_repo = _build_service()

        appt = _make_mock_appointment(status=AppointmentStatus.CONFIRMED.value)
        mock_appt_repo.get_by_id.return_value = appt
        mock_appt_repo.update_status.return_value = appt

        with (
            patch.object(
                service, "_send_cancellation_sms", new_callable=AsyncMock
            ) as mock_sms,
            patch(
                "grins_platform.services.appointment_service.clear_on_site_data",
                new_callable=AsyncMock,
            ),
        ):
            await service.cancel_appointment(appt.id)
            mock_sms.assert_called_once_with(mock_appt_repo.session, appt)
