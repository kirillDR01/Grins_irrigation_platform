"""Unit tests for post-send reschedule detection (task 11.5).

When a SCHEDULED or CONFIRMED appointment's date/time is changed via the
update endpoint, the system should automatically send a reschedule
notification SMS and reset the appointment status to SCHEDULED.

When a DRAFT appointment is moved, nothing happens (silent).

Validates: Requirements 8.8, 8.9
"""

from __future__ import annotations

from datetime import date, time
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from grins_platform.models.enums import AppointmentStatus
from grins_platform.schemas.appointment import AppointmentUpdate


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
    appt.scheduled_date = scheduled_date or date(2025, 6, 10)
    appt.time_window_start = time_window_start or time(9, 0)
    appt.time_window_end = time_window_end or time(11, 0)
    appt.can_transition_to = MagicMock(return_value=True)
    return appt


def _build_service() -> tuple:
    """Build an AppointmentService with mocked repositories."""
    from grins_platform.services.appointment_service import AppointmentService

    mock_appt_repo = AsyncMock()
    mock_appt_repo.session = AsyncMock()

    service = AppointmentService(
        appointment_repository=mock_appt_repo,
        job_repository=AsyncMock(),
        staff_repository=AsyncMock(),
    )
    return service, mock_appt_repo


class TestRescheduleDetection:
    """Tests for post-send reschedule detection in update_appointment.

    Validates: Req 8.8, 8.9
    """

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_moving_draft_appointment_does_not_send_sms(self) -> None:
        """Moving a DRAFT appointment does NOT send reschedule SMS.

        Validates: Requirement 8.8
        """
        service, mock_appt_repo = _build_service()

        original = _make_mock_appointment(status=AppointmentStatus.DRAFT.value)
        updated = _make_mock_appointment(
            status=AppointmentStatus.DRAFT.value,
            scheduled_date=date(2025, 6, 12),
        )

        mock_appt_repo.get_by_id.return_value = original
        mock_appt_repo.update.return_value = updated

        update_data = AppointmentUpdate(scheduled_date=date(2025, 6, 12))

        with patch.object(
            service, "_send_reschedule_sms", new_callable=AsyncMock
        ) as mock_sms:
            await service.update_appointment(original.id, update_data)
            mock_sms.assert_not_called()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_moving_scheduled_appointment_sends_reschedule_sms(self) -> None:
        """Moving a SCHEDULED appointment sends reschedule SMS and resets to SCHEDULED.

        Validates: Requirement 8.9
        """
        service, mock_appt_repo = _build_service()

        original = _make_mock_appointment(status=AppointmentStatus.SCHEDULED.value)
        updated = _make_mock_appointment(
            status=AppointmentStatus.SCHEDULED.value,
            scheduled_date=date(2025, 6, 15),
        )

        mock_appt_repo.get_by_id.return_value = original
        mock_appt_repo.update.return_value = updated

        update_data = AppointmentUpdate(scheduled_date=date(2025, 6, 15))

        with patch.object(
            service, "_send_reschedule_sms", new_callable=AsyncMock
        ) as mock_sms:
            await service.update_appointment(original.id, update_data)
            mock_sms.assert_called_once_with(mock_appt_repo.session, updated)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_moving_confirmed_appointment_sends_reschedule_sms_and_resets(
        self,
    ) -> None:
        """Moving a CONFIRMED appointment sends reschedule SMS and resets to SCHEDULED.

        Validates: Requirement 8.9
        """
        service, mock_appt_repo = _build_service()

        original = _make_mock_appointment(status=AppointmentStatus.CONFIRMED.value)
        # After the update, the status is still CONFIRMED until the reset
        updated = _make_mock_appointment(
            status=AppointmentStatus.CONFIRMED.value,
            scheduled_date=date(2025, 6, 18),
        )

        mock_appt_repo.get_by_id.return_value = original
        mock_appt_repo.update.return_value = updated

        update_data = AppointmentUpdate(scheduled_date=date(2025, 6, 18))

        with patch.object(
            service, "_send_reschedule_sms", new_callable=AsyncMock
        ) as mock_sms:
            await service.update_appointment(original.id, update_data)

            # SMS was sent
            mock_sms.assert_called_once_with(mock_appt_repo.session, updated)

        # Status was reset to SCHEDULED (second update call)
        calls = mock_appt_repo.update.call_args_list
        assert len(calls) == 2
        reset_call = calls[1]
        assert reset_call.args[1] == {"status": AppointmentStatus.SCHEDULED.value}

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_updating_scheduled_without_date_change_does_not_send_sms(
        self,
    ) -> None:
        """Updating a SCHEDULED appointment without changing date/time does NOT send SMS.

        Validates: Requirement 8.8
        """
        service, mock_appt_repo = _build_service()

        original = _make_mock_appointment(status=AppointmentStatus.SCHEDULED.value)
        updated = _make_mock_appointment(status=AppointmentStatus.SCHEDULED.value)

        mock_appt_repo.get_by_id.return_value = original
        mock_appt_repo.update.return_value = updated

        # Only updating notes — no date/time change
        update_data = AppointmentUpdate(notes="Updated notes only")

        with patch.object(
            service, "_send_reschedule_sms", new_callable=AsyncMock
        ) as mock_sms:
            await service.update_appointment(original.id, update_data)
            mock_sms.assert_not_called()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_suppress_notifications_skips_sms_but_still_demotes(
        self,
    ) -> None:
        """Drag-drop path: suppress_notifications=True → no SMS, status still demotes.

        Cluster D Item 1: dragging a CONFIRMED appointment to a new slot
        must revert to SCHEDULED without spamming the customer.
        """
        service, mock_appt_repo = _build_service()

        original = _make_mock_appointment(status=AppointmentStatus.CONFIRMED.value)
        updated = _make_mock_appointment(
            status=AppointmentStatus.CONFIRMED.value,
            scheduled_date=date(2025, 6, 20),
        )

        mock_appt_repo.get_by_id.return_value = original
        mock_appt_repo.update.return_value = updated

        update_data = AppointmentUpdate(
            scheduled_date=date(2025, 6, 20),
            suppress_notifications=True,
        )

        with patch.object(
            service, "_send_reschedule_sms", new_callable=AsyncMock
        ) as mock_sms:
            await service.update_appointment(
                original.id,
                update_data,
                notify_customer=False,
            )
            mock_sms.assert_not_called()

        # Status was still reset to SCHEDULED (demote happens regardless of SMS gating)
        calls = mock_appt_repo.update.call_args_list
        assert len(calls) == 2
        reset_call = calls[1]
        assert reset_call.args[1] == {"status": AppointmentStatus.SCHEDULED.value}

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_default_suppress_notifications_still_sends_sms(self) -> None:
        """Default suppress_notifications=False still fires the reschedule SMS.

        Regression guard: the new flag is additive and must not change the
        default behavior for callers that omit it.
        """
        service, mock_appt_repo = _build_service()

        original = _make_mock_appointment(status=AppointmentStatus.CONFIRMED.value)
        updated = _make_mock_appointment(
            status=AppointmentStatus.CONFIRMED.value,
            scheduled_date=date(2025, 6, 22),
        )

        mock_appt_repo.get_by_id.return_value = original
        mock_appt_repo.update.return_value = updated

        update_data = AppointmentUpdate(scheduled_date=date(2025, 6, 22))
        assert update_data.suppress_notifications is False

        with patch.object(
            service, "_send_reschedule_sms", new_callable=AsyncMock
        ) as mock_sms:
            await service.update_appointment(original.id, update_data)
            mock_sms.assert_called_once_with(mock_appt_repo.session, updated)
