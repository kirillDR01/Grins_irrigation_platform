"""Unit tests for POST /api/v1/appointments/{id}/send-confirmation endpoint.

Tests the send_confirmation service method and endpoint behavior:
- Sends Y/R/C confirmation SMS via SMSService
- Transitions appointment from DRAFT to SCHEDULED
- Rejects with 422 if appointment is not in DRAFT status

Validates: Requirements 8.4, 8.12
"""

from __future__ import annotations

from datetime import date, time
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from grins_platform.exceptions import (
    AppointmentNotFoundError,
    InvalidStatusTransitionError,
)
from grins_platform.models.enums import AppointmentStatus


class TestSendConfirmationService:
    """Tests for AppointmentService.send_confirmation().

    Validates: Req 8.4, 8.12
    """

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_send_confirmation_transitions_draft_to_scheduled(self) -> None:
        """send_confirmation on a DRAFT appointment transitions to SCHEDULED."""
        from grins_platform.services.appointment_service import AppointmentService

        appt_id = uuid4()

        mock_appointment = MagicMock()
        mock_appointment.id = appt_id
        mock_appointment.status = AppointmentStatus.DRAFT.value
        mock_appointment.job_id = uuid4()
        mock_appointment.scheduled_date = date(2025, 5, 1)
        mock_appointment.time_window_start = time(9, 0)
        mock_appointment.time_window_end = time(11, 0)

        updated_appointment = MagicMock()
        updated_appointment.id = appt_id
        updated_appointment.status = AppointmentStatus.SCHEDULED.value

        mock_appt_repo = AsyncMock()
        mock_appt_repo.get_by_id.return_value = mock_appointment
        mock_appt_repo.update.return_value = updated_appointment
        mock_appt_repo.session = AsyncMock()

        service = AppointmentService(
            appointment_repository=mock_appt_repo,
            job_repository=AsyncMock(),
            staff_repository=AsyncMock(),
        )

        with patch.object(service, "_send_confirmation_sms", new_callable=AsyncMock):
            result = await service.send_confirmation(appt_id)

        assert result.status == AppointmentStatus.SCHEDULED.value
        mock_appt_repo.update.assert_called_once_with(
            appt_id,
            {"status": AppointmentStatus.SCHEDULED.value},
        )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_send_confirmation_sends_sms(self) -> None:
        """send_confirmation calls _send_confirmation_sms."""
        from grins_platform.services.appointment_service import AppointmentService

        appt_id = uuid4()

        mock_appointment = MagicMock()
        mock_appointment.id = appt_id
        mock_appointment.status = AppointmentStatus.DRAFT.value
        mock_appointment.job_id = uuid4()

        mock_appt_repo = AsyncMock()
        mock_appt_repo.get_by_id.return_value = mock_appointment
        mock_appt_repo.update.return_value = mock_appointment
        mock_appt_repo.session = AsyncMock()

        service = AppointmentService(
            appointment_repository=mock_appt_repo,
            job_repository=AsyncMock(),
            staff_repository=AsyncMock(),
        )

        mock_send_sms = AsyncMock()
        with patch.object(service, "_send_confirmation_sms", mock_send_sms):
            await service.send_confirmation(appt_id)

        mock_send_sms.assert_called_once_with(
            mock_appt_repo.session,
            mock_appointment,
        )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_send_confirmation_rejects_non_draft(self) -> None:
        """send_confirmation raises InvalidStatusTransitionError for non-DRAFT."""
        from grins_platform.services.appointment_service import AppointmentService

        appt_id = uuid4()

        mock_appointment = MagicMock()
        mock_appointment.id = appt_id
        mock_appointment.status = AppointmentStatus.SCHEDULED.value

        mock_appt_repo = AsyncMock()
        mock_appt_repo.get_by_id.return_value = mock_appointment

        service = AppointmentService(
            appointment_repository=mock_appt_repo,
            job_repository=AsyncMock(),
            staff_repository=AsyncMock(),
        )

        with pytest.raises(InvalidStatusTransitionError):
            await service.send_confirmation(appt_id)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_send_confirmation_rejects_confirmed(self) -> None:
        """send_confirmation raises InvalidStatusTransitionError for CONFIRMED."""
        from grins_platform.services.appointment_service import AppointmentService

        appt_id = uuid4()

        mock_appointment = MagicMock()
        mock_appointment.id = appt_id
        mock_appointment.status = AppointmentStatus.CONFIRMED.value

        mock_appt_repo = AsyncMock()
        mock_appt_repo.get_by_id.return_value = mock_appointment

        service = AppointmentService(
            appointment_repository=mock_appt_repo,
            job_repository=AsyncMock(),
            staff_repository=AsyncMock(),
        )

        with pytest.raises(InvalidStatusTransitionError):
            await service.send_confirmation(appt_id)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_send_confirmation_not_found(self) -> None:
        """send_confirmation raises AppointmentNotFoundError for missing ID."""
        from grins_platform.services.appointment_service import AppointmentService

        appt_id = uuid4()

        mock_appt_repo = AsyncMock()
        mock_appt_repo.get_by_id.return_value = None

        service = AppointmentService(
            appointment_repository=mock_appt_repo,
            job_repository=AsyncMock(),
            staff_repository=AsyncMock(),
        )

        with pytest.raises(AppointmentNotFoundError):
            await service.send_confirmation(appt_id)
