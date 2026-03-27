"""Property test: Failed Payment Escalation Timeline.

Property 23: For any agreement PAST_DUE ≥ 7 days → transitions to PAUSED;
PAUSED ≥ 14 days → transitions to CANCELLED.

Validates: Requirements 15.2, 15.3
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from hypothesis import (
    given,
    settings,
    strategies as st,
)

from grins_platform.models.enums import AgreementStatus, JobStatus
from grins_platform.services.background_jobs import FailedPaymentEscalator


def _make_agreement(
    status: str,
    days_since_update: int,
    jobs: list[MagicMock] | None = None,
) -> MagicMock:
    agr = MagicMock()
    agr.id = uuid4()
    agr.status = status
    agr.updated_at = datetime.now(timezone.utc) - timedelta(days=days_since_update)
    agr.stripe_subscription_id = None  # Skip Stripe calls
    agr.jobs = jobs or []
    agr.cancelled_at = None
    agr.pause_reason = None
    return agr


class TestFailedPaymentEscalationTimeline:
    """Property 23: Failed Payment Escalation Timeline."""

    @given(days=st.integers(min_value=7, max_value=365))
    @settings(max_examples=20)
    @pytest.mark.asyncio
    async def test_past_due_ge_7_days_becomes_paused(self, days):
        """PAST_DUE ≥ 7 days → PAUSED."""
        escalator = FailedPaymentEscalator()
        agreement = _make_agreement(AgreementStatus.PAST_DUE.value, days)

        mock_session = AsyncMock()
        paused_result = MagicMock()
        paused_result.scalars.return_value.all.return_value = []
        past_due_result = MagicMock()
        past_due_result.scalars.return_value.all.return_value = [agreement]
        mock_session.execute = AsyncMock(side_effect=[paused_result, past_due_result])

        mock_db = MagicMock()

        async def mock_get_session():
            yield mock_session

        mock_db.get_session = mock_get_session

        with (
            patch(
                "grins_platform.services.background_jobs.get_database_manager",
                return_value=mock_db,
            ),
            patch(
                "grins_platform.services.background_jobs.StripeSettings",
            ) as mock_ss,
        ):
            mock_ss.return_value.is_configured = False
            await escalator.run()

        assert agreement.status == AgreementStatus.PAUSED.value

    @given(days=st.integers(min_value=14, max_value=365))
    @settings(max_examples=20)
    @pytest.mark.asyncio
    async def test_paused_ge_14_days_becomes_cancelled(self, days):
        """PAUSED ≥ 14 days → CANCELLED."""
        escalator = FailedPaymentEscalator()
        approved_job = MagicMock()
        approved_job.status = JobStatus.TO_BE_SCHEDULED.value
        completed_job = MagicMock()
        completed_job.status = JobStatus.COMPLETED.value

        agreement = _make_agreement(
            AgreementStatus.PAUSED.value,
            days,
            jobs=[approved_job, completed_job],
        )

        mock_session = AsyncMock()
        paused_result = MagicMock()
        paused_result.scalars.return_value.all.return_value = [agreement]
        past_due_result = MagicMock()
        past_due_result.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(side_effect=[paused_result, past_due_result])

        mock_db = MagicMock()

        async def mock_get_session():
            yield mock_session

        mock_db.get_session = mock_get_session

        with (
            patch(
                "grins_platform.services.background_jobs.get_database_manager",
                return_value=mock_db,
            ),
            patch(
                "grins_platform.services.background_jobs.StripeSettings",
            ) as mock_ss,
        ):
            mock_ss.return_value.is_configured = False
            await escalator.run()

        assert agreement.status == AgreementStatus.CANCELLED.value
        assert agreement.cancelled_at is not None
        # TO_BE_SCHEDULED jobs cancelled, COMPLETED preserved
        assert approved_job.status == JobStatus.CANCELLED.value
        assert completed_job.status == JobStatus.COMPLETED.value
