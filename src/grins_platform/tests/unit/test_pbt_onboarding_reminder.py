"""Property tests for OnboardingReminderJob.

Property 17: Onboarding reminder scheduling — verify correct action based on
elapsed time and reminder_count.

Validates: Requirements 10.2, 10.3, 10.4
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from hypothesis import (
    given,
    settings,
    strategies as st,
)

from grins_platform.services.onboarding_reminder_job import (
    _7D,
    _24H,
    _72H,
    OnboardingReminderJob,
)


def _make_agreement(
    *,
    created_hours_ago: float,
    reminder_count: int,
    has_property: bool = False,
) -> MagicMock:
    now = datetime.now(timezone.utc)
    agr = MagicMock()
    agr.id = MagicMock()
    agr.created_at = now - timedelta(hours=created_hours_ago)
    agr.onboarding_reminder_count = reminder_count
    agr.onboarding_reminder_sent_at = None
    agr.property_id = MagicMock() if has_property else None
    agr.status = "active"
    agr.customer = MagicMock()
    agr.customer.phone = "6125551234"
    return agr


@pytest.mark.unit
class TestProperty17OnboardingReminderScheduling:
    """Property 17: Onboarding reminder scheduling.

    Validates: Requirements 10.2, 10.3, 10.4
    """

    @given(
        hours_ago=st.floats(min_value=0, max_value=500, allow_nan=False),
        reminder_count=st.sampled_from([0, 1, 2, 3]),
    )
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_correct_action_for_elapsed_time_and_count(
        self,
        hours_ago: float,
        reminder_count: int,
    ) -> None:
        """Verify correct action based on hours elapsed and reminder_count."""
        job = OnboardingReminderJob()
        agreement = _make_agreement(
            created_hours_ago=hours_ago,
            reminder_count=reminder_count,
        )

        sms_service = AsyncMock()
        sms_service.check_sms_consent = AsyncMock(return_value=True)
        sms_service.enforce_time_window = MagicMock(return_value=None)
        sms_service.send_automated_message = AsyncMock(
            return_value={"success": True},
        )

        now = datetime.now(timezone.utc)
        await job._process_agreement(agreement, sms_service, now)

        # Determine expected action
        should_send_sms = (reminder_count == 0 and hours_ago >= _24H) or (
            reminder_count == 1 and hours_ago >= _72H
        )
        should_admin_alert = reminder_count == 2 and hours_ago >= _7D
        should_do_nothing = not should_send_sms and not should_admin_alert

        if should_send_sms:
            sms_service.send_automated_message.assert_called_once()
            assert agreement.onboarding_reminder_count == reminder_count + 1
        elif should_admin_alert:
            sms_service.send_automated_message.assert_not_called()
            assert agreement.onboarding_reminder_count == reminder_count + 1
        elif should_do_nothing:
            sms_service.send_automated_message.assert_not_called()
            assert agreement.onboarding_reminder_count == reminder_count

    @given(hours_ago=st.floats(min_value=24, max_value=500, allow_nan=False))
    @settings(max_examples=30)
    @pytest.mark.asyncio
    async def test_no_sms_when_opted_out(self, hours_ago: float) -> None:
        """SMS gated on consent — opted-out customer gets no SMS."""
        job = OnboardingReminderJob()
        agreement = _make_agreement(created_hours_ago=hours_ago, reminder_count=0)

        sms_service = AsyncMock()
        sms_service.check_sms_consent = AsyncMock(return_value=False)
        sms_service.enforce_time_window = MagicMock(return_value=None)
        sms_service.send_automated_message = AsyncMock()

        now = datetime.now(timezone.utc)
        await job._process_agreement(agreement, sms_service, now)

        sms_service.send_automated_message.assert_not_called()
        # Count should NOT increment when consent denied
        assert agreement.onboarding_reminder_count == 0

    @given(hours_ago=st.floats(min_value=24, max_value=500, allow_nan=False))
    @settings(max_examples=30)
    @pytest.mark.asyncio
    async def test_deferred_when_outside_time_window(
        self,
        hours_ago: float,
    ) -> None:
        """SMS deferred when outside time window."""
        job = OnboardingReminderJob()
        agreement = _make_agreement(created_hours_ago=hours_ago, reminder_count=0)

        deferred_time = datetime.now(timezone.utc) + timedelta(hours=8)
        sms_service = AsyncMock()
        sms_service.check_sms_consent = AsyncMock(return_value=True)
        sms_service.enforce_time_window = MagicMock(return_value=deferred_time)
        sms_service.send_automated_message = AsyncMock()

        now = datetime.now(timezone.utc)
        await job._process_agreement(agreement, sms_service, now)

        sms_service.send_automated_message.assert_not_called()
        # Count should NOT increment when deferred
        assert agreement.onboarding_reminder_count == 0
