"""Unit tests for POST /api/v1/appointments/send-confirmations bulk endpoint.

Tests the bulk_send_confirmations service method:
- Bulk send with list of IDs sends SMS for all DRAFT appointments
- Bulk send with date range sends SMS for all DRAFT appointments in range
- Non-DRAFT appointments in the list are skipped
- Empty list returns 0 sent
- Per-appointment result rows distinguish sent / deferred / skipped /
  failed (bughunt M-8, M-9)
- No-phone customer raises CustomerHasNoPhoneError and the bulk call
  reports skipped, without transitioning the appointment (bughunt M-9)

Validates: Requirements 8.6, 8.13; bughunt M-8, M-9
"""

from __future__ import annotations

from datetime import date, time
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from grins_platform.exceptions import CustomerHasNoPhoneError
from grins_platform.models.enums import AppointmentStatus


_SENT = {"success": True, "deferred": False}
_DEFERRED = {"success": True, "deferred": True}
_DEDUPED = {
    "success": False,
    "deferred": False,
    "reason": "Duplicate message prevented",
}


def _make_mock_appointment(
    *,
    status: str = AppointmentStatus.DRAFT.value,
    scheduled_date: date = date(2025, 5, 5),
) -> MagicMock:
    """Create a mock appointment with sensible defaults."""
    appt = MagicMock()
    appt.id = uuid4()
    appt.status = status
    appt.job_id = uuid4()
    appt.scheduled_date = scheduled_date
    appt.time_window_start = time(9, 0)
    appt.time_window_end = time(11, 0)
    return appt


class TestBulkSendConfirmationsService:
    """Tests for AppointmentService.bulk_send_confirmations().

    Validates: Req 8.6, 8.13
    """

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_bulk_send_with_ids_sends_sms_for_all_draft(self) -> None:
        """Bulk send with a list of IDs sends SMS for all DRAFT appointments."""
        from grins_platform.services.appointment_service import AppointmentService

        draft1 = _make_mock_appointment()
        draft2 = _make_mock_appointment()
        draft3 = _make_mock_appointment()
        drafts = [draft1, draft2, draft3]

        # Mock the session and query result
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = drafts

        mock_session = AsyncMock()
        mock_session.execute.return_value = mock_result
        mock_session.flush = AsyncMock()

        mock_appt_repo = AsyncMock()
        mock_appt_repo.session = mock_session

        service = AppointmentService(
            appointment_repository=mock_appt_repo,
            job_repository=AsyncMock(),
            staff_repository=AsyncMock(),
        )

        with patch.object(
            service,
            "_send_confirmation_sms",
            new_callable=AsyncMock,
            return_value=_SENT,
        ):
            result = await service.bulk_send_confirmations(
                appointment_ids=[d.id for d in drafts],
            )

        assert result["sent_count"] == 3
        assert result["failed_count"] == 0
        assert result["total_draft"] == 3
        assert result["deferred_count"] == 0
        assert result["skipped_count"] == 0
        assert len(result["results"]) == 3
        assert all(row["status"] == "sent" for row in result["results"])
        # All appointments should be transitioned to SCHEDULED
        for appt in drafts:
            assert appt.status == AppointmentStatus.SCHEDULED.value

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_bulk_send_with_date_range_sends_sms(self) -> None:
        """Bulk send with date range sends SMS for all DRAFT appointments in range."""
        from grins_platform.services.appointment_service import AppointmentService

        draft1 = _make_mock_appointment(scheduled_date=date(2025, 5, 5))
        draft2 = _make_mock_appointment(scheduled_date=date(2025, 5, 7))
        drafts = [draft1, draft2]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = drafts

        mock_session = AsyncMock()
        mock_session.execute.return_value = mock_result
        mock_session.flush = AsyncMock()

        mock_appt_repo = AsyncMock()
        mock_appt_repo.session = mock_session

        service = AppointmentService(
            appointment_repository=mock_appt_repo,
            job_repository=AsyncMock(),
            staff_repository=AsyncMock(),
        )

        with patch.object(
            service,
            "_send_confirmation_sms",
            new_callable=AsyncMock,
            return_value=_SENT,
        ):
            result = await service.bulk_send_confirmations(
                date_from=date(2025, 5, 1),
                date_to=date(2025, 5, 10),
            )

        assert result["sent_count"] == 2
        assert result["failed_count"] == 0
        assert result["total_draft"] == 2
        for appt in drafts:
            assert appt.status == AppointmentStatus.SCHEDULED.value

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_bulk_send_skips_non_draft_appointments(self) -> None:
        """Non-DRAFT appointments are not returned by the query (filtered at DB level)."""
        from grins_platform.services.appointment_service import AppointmentService

        # The query filters for DRAFT status, so only DRAFT appointments are returned.
        # If we pass IDs that include non-DRAFT appointments, the DB query
        # only returns the DRAFT ones. Simulate this by returning only the draft.
        draft = _make_mock_appointment(status=AppointmentStatus.DRAFT.value)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [draft]

        mock_session = AsyncMock()
        mock_session.execute.return_value = mock_result
        mock_session.flush = AsyncMock()

        mock_appt_repo = AsyncMock()
        mock_appt_repo.session = mock_session

        service = AppointmentService(
            appointment_repository=mock_appt_repo,
            job_repository=AsyncMock(),
            staff_repository=AsyncMock(),
        )

        non_draft_id = uuid4()  # SCHEDULED appointment ID — won't be in results

        with patch.object(
            service,
            "_send_confirmation_sms",
            new_callable=AsyncMock,
            return_value=_SENT,
        ):
            result = await service.bulk_send_confirmations(
                appointment_ids=[draft.id, non_draft_id],
            )

        # Only the DRAFT appointment was found and sent
        assert result["sent_count"] == 1
        assert result["total_draft"] == 1
        assert draft.status == AppointmentStatus.SCHEDULED.value

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_bulk_send_empty_list_returns_zero(self) -> None:
        """Empty appointment list returns 0 sent."""
        from grins_platform.services.appointment_service import AppointmentService

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []

        mock_session = AsyncMock()
        mock_session.execute.return_value = mock_result
        mock_session.flush = AsyncMock()

        mock_appt_repo = AsyncMock()
        mock_appt_repo.session = mock_session

        service = AppointmentService(
            appointment_repository=mock_appt_repo,
            job_repository=AsyncMock(),
            staff_repository=AsyncMock(),
        )

        result = await service.bulk_send_confirmations(appointment_ids=[])

        assert result["sent_count"] == 0
        assert result["failed_count"] == 0
        assert result["total_draft"] == 0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_bulk_send_handles_sms_failure_gracefully(self) -> None:
        """When SMS fails for one appointment, it increments failed_count and continues."""
        from grins_platform.services.appointment_service import AppointmentService

        draft_ok = _make_mock_appointment()
        draft_fail = _make_mock_appointment()

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [draft_ok, draft_fail]

        mock_session = AsyncMock()
        mock_session.execute.return_value = mock_result
        mock_session.flush = AsyncMock()

        mock_appt_repo = AsyncMock()
        mock_appt_repo.session = mock_session

        service = AppointmentService(
            appointment_repository=mock_appt_repo,
            job_repository=AsyncMock(),
            staff_repository=AsyncMock(),
        )

        call_count = 0

        async def _sms_side_effect(
            _session: object, _appt: object
        ) -> dict[str, object]:
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise RuntimeError("SMS provider error")
            return _SENT

        with patch.object(
            service, "_send_confirmation_sms", side_effect=_sms_side_effect
        ):
            result = await service.bulk_send_confirmations(
                appointment_ids=[draft_ok.id, draft_fail.id],
            )

        assert result["sent_count"] == 1
        assert result["failed_count"] == 1
        assert result["total_draft"] == 2
        # First appointment transitioned, second did not
        assert draft_ok.status == AppointmentStatus.SCHEDULED.value
        assert draft_fail.status == AppointmentStatus.DRAFT.value
        # Per-row payload distinguishes the two outcomes
        row_statuses = {
            row["appointment_id"]: row["status"] for row in result["results"]
        }
        assert row_statuses[str(draft_ok.id)] == "sent"
        assert row_statuses[str(draft_fail.id)] == "failed"


class TestBulkSendConfirmationsPerRowOutcomes:
    """Per-appointment result shape for the bulk endpoint.

    Validates: bughunt M-8, M-9
    """

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_deferred_send_does_not_transition(self) -> None:
        """Rate-limited sends must stay DRAFT and be reported as deferred."""
        from grins_platform.services.appointment_service import AppointmentService

        draft = _make_mock_appointment()

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [draft]

        mock_session = AsyncMock()
        mock_session.execute.return_value = mock_result
        mock_session.flush = AsyncMock()

        mock_appt_repo = AsyncMock()
        mock_appt_repo.session = mock_session

        service = AppointmentService(
            appointment_repository=mock_appt_repo,
            job_repository=AsyncMock(),
            staff_repository=AsyncMock(),
        )

        with patch.object(
            service,
            "_send_confirmation_sms",
            new_callable=AsyncMock,
            return_value=_DEFERRED,
        ):
            result = await service.bulk_send_confirmations(
                appointment_ids=[draft.id],
            )

        assert result["sent_count"] == 0
        assert result["deferred_count"] == 1
        assert draft.status == AppointmentStatus.DRAFT.value
        assert result["results"][0]["status"] == "deferred"
        assert result["results"][0]["reason"] == "rate_limited"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_no_phone_customer_is_skipped(self) -> None:
        """CustomerHasNoPhoneError → skipped row, no transition (M-9)."""
        from grins_platform.services.appointment_service import AppointmentService

        draft = _make_mock_appointment()

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [draft]

        mock_session = AsyncMock()
        mock_session.execute.return_value = mock_result
        mock_session.flush = AsyncMock()

        mock_appt_repo = AsyncMock()
        mock_appt_repo.session = mock_session

        service = AppointmentService(
            appointment_repository=mock_appt_repo,
            job_repository=AsyncMock(),
            staff_repository=AsyncMock(),
        )

        customer_id = uuid4()

        with patch.object(
            service,
            "_send_confirmation_sms",
            new_callable=AsyncMock,
            side_effect=CustomerHasNoPhoneError(customer_id),
        ):
            result = await service.bulk_send_confirmations(
                appointment_ids=[draft.id],
            )

        assert result["sent_count"] == 0
        assert result["skipped_count"] == 1
        assert draft.status == AppointmentStatus.DRAFT.value
        row = result["results"][0]
        assert row["status"] == "skipped"
        assert row["reason"] == "no_phone"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_dedup_block_counts_as_failed(self) -> None:
        """send_message → {success: False, reason: 'Duplicate...'} is a failure row."""
        from grins_platform.services.appointment_service import AppointmentService

        draft = _make_mock_appointment()

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [draft]

        mock_session = AsyncMock()
        mock_session.execute.return_value = mock_result
        mock_session.flush = AsyncMock()

        mock_appt_repo = AsyncMock()
        mock_appt_repo.session = mock_session

        service = AppointmentService(
            appointment_repository=mock_appt_repo,
            job_repository=AsyncMock(),
            staff_repository=AsyncMock(),
        )

        with patch.object(
            service,
            "_send_confirmation_sms",
            new_callable=AsyncMock,
            return_value=_DEDUPED,
        ):
            result = await service.bulk_send_confirmations(
                appointment_ids=[draft.id],
            )

        assert result["sent_count"] == 0
        assert result["failed_count"] == 1
        assert draft.status == AppointmentStatus.DRAFT.value
        row = result["results"][0]
        assert row["status"] == "failed"
        assert row["reason"] == "Duplicate message prevented"
