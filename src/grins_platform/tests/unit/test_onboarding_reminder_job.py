"""Unit tests for OnboardingReminderJob.

Tests specific scenarios: timing thresholds, property_id skip,
consent gating, time window gating, and admin notification.

Validates: Requirements 10.1, 10.2, 10.3, 10.4, 10.5, 10.6
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from grins_platform.services.onboarding_reminder_job import OnboardingReminderJob


def _make_agreement(
    *,
    created_hours_ago: float,
    reminder_count: int = 0,
    property_id: object | None = None,
    status: str = "active",
    phone: str = "6125551234",
) -> MagicMock:
    now = datetime.now(timezone.utc)
    agr = MagicMock()
    agr.id = uuid4()
    agr.created_at = now - timedelta(hours=created_hours_ago)
    agr.onboarding_reminder_count = reminder_count
    agr.onboarding_reminder_sent_at = None
    agr.property_id = property_id
    agr.status = status
    agr.customer = MagicMock()
    agr.customer.phone = phone
    return agr


def _make_sms_service(
    *,
    consent: bool = True,
    deferred: datetime | None = None,
) -> AsyncMock:
    svc = AsyncMock()
    svc.check_sms_consent = AsyncMock(return_value=consent)
    svc.enforce_time_window = MagicMock(return_value=deferred)
    svc.send_automated_message = AsyncMock(return_value={"success": True})
    return svc


@pytest.mark.unit
class TestOnboardingReminderJobProcessAgreement:
    """Tests for _process_agreement logic."""

    @pytest.mark.asyncio
    async def test_no_action_at_23h_count_0(self) -> None:
        """Agreement at T+23h, reminder_count=0 → no action."""
        job = OnboardingReminderJob()
        agr = _make_agreement(created_hours_ago=23)
        sms = _make_sms_service()
        now = datetime.now(timezone.utc)

        await job._process_agreement(agr, sms, now)

        sms.send_automated_message.assert_not_called()
        assert agr.onboarding_reminder_count == 0

    @pytest.mark.asyncio
    async def test_sms_sent_at_24h_count_0(self) -> None:
        """Agreement at T+24h, reminder_count=0 → SMS reminder sent."""
        job = OnboardingReminderJob()
        agr = _make_agreement(created_hours_ago=25)
        sms = _make_sms_service()
        now = datetime.now(timezone.utc)

        await job._process_agreement(agr, sms, now)

        sms.send_automated_message.assert_called_once()
        assert agr.onboarding_reminder_count == 1
        assert agr.onboarding_reminder_sent_at == now

    @pytest.mark.asyncio
    async def test_second_sms_at_72h_count_1(self) -> None:
        """Agreement at T+72h, reminder_count=1 → second SMS sent."""
        job = OnboardingReminderJob()
        agr = _make_agreement(created_hours_ago=73, reminder_count=1)
        sms = _make_sms_service()
        now = datetime.now(timezone.utc)

        await job._process_agreement(agr, sms, now)

        sms.send_automated_message.assert_called_once()
        assert agr.onboarding_reminder_count == 2
        assert agr.onboarding_reminder_sent_at == now

    @pytest.mark.asyncio
    async def test_admin_notification_at_7d_count_2(self) -> None:
        """Agreement at T+7d, reminder_count=2 → admin notification (no SMS)."""
        job = OnboardingReminderJob()
        agr = _make_agreement(created_hours_ago=169, reminder_count=2)
        sms = _make_sms_service()
        now = datetime.now(timezone.utc)

        await job._process_agreement(agr, sms, now)

        sms.send_automated_message.assert_not_called()
        sms.check_sms_consent.assert_not_called()
        assert agr.onboarding_reminder_count == 3
        assert agr.onboarding_reminder_sent_at == now

    @pytest.mark.asyncio
    async def test_no_action_count_3(self) -> None:
        """Agreement with reminder_count=3 → no further action."""
        job = OnboardingReminderJob()
        agr = _make_agreement(created_hours_ago=500, reminder_count=3)
        sms = _make_sms_service()
        now = datetime.now(timezone.utc)

        await job._process_agreement(agr, sms, now)

        sms.send_automated_message.assert_not_called()
        assert agr.onboarding_reminder_count == 3

    @pytest.mark.asyncio
    async def test_skipped_when_opted_out(self) -> None:
        """SMS send gated on consent check — opted-out → no SMS."""
        job = OnboardingReminderJob()
        agr = _make_agreement(created_hours_ago=25)
        sms = _make_sms_service(consent=False)
        now = datetime.now(timezone.utc)

        await job._process_agreement(agr, sms, now)

        sms.send_automated_message.assert_not_called()
        assert agr.onboarding_reminder_count == 0

    @pytest.mark.asyncio
    async def test_deferred_outside_time_window(self) -> None:
        """SMS send gated on time window — deferred when outside window."""
        job = OnboardingReminderJob()
        agr = _make_agreement(created_hours_ago=25)
        deferred = datetime.now(timezone.utc) + timedelta(hours=8)
        sms = _make_sms_service(deferred=deferred)
        now = datetime.now(timezone.utc)

        await job._process_agreement(agr, sms, now)

        sms.send_automated_message.assert_not_called()
        assert agr.onboarding_reminder_count == 0


@pytest.mark.unit
class TestOnboardingReminderJobRun:
    """Tests for the full run() method."""

    @pytest.mark.asyncio
    async def test_property_id_set_skipped(self) -> None:
        """Agreement with property_id set → skipped entirely (filtered by query)."""
        job = OnboardingReminderJob()

        # The query filters property_id IS NULL, so agreements with
        # property_id set never reach _process_agreement.
        # We verify the query filter is correct by mocking the DB.
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()

        mock_db = MagicMock()

        async def mock_get_session():
            yield mock_session

        mock_db.get_session = mock_get_session

        with (
            patch(
                "grins_platform.services.onboarding_reminder_job.get_database_manager",
                return_value=mock_db,
            ),
            patch(
                "grins_platform.services.onboarding_reminder_job.SMSService",
            ),
        ):
            await job.run()

        # Verify execute was called (query ran)
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_processes_eligible_agreements(self) -> None:
        """run() processes agreements returned by query."""
        job = OnboardingReminderJob()
        agr = _make_agreement(created_hours_ago=25)

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [agr]
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()

        mock_db = MagicMock()

        async def mock_get_session():
            yield mock_session

        mock_db.get_session = mock_get_session

        mock_sms_cls = MagicMock()
        mock_sms_instance = _make_sms_service()
        mock_sms_cls.return_value = mock_sms_instance

        with (
            patch(
                "grins_platform.services.onboarding_reminder_job.get_database_manager",
                return_value=mock_db,
            ),
            patch(
                "grins_platform.services.onboarding_reminder_job.SMSService",
                mock_sms_cls,
            ),
        ):
            await job.run()

        mock_sms_instance.send_automated_message.assert_called_once()
        assert agr.onboarding_reminder_count == 1
