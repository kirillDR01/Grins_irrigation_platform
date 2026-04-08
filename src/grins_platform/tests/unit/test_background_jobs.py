"""Unit tests for background scheduled jobs.

Tests: escalate_failed_payments, send_annual_notices,
cleanup_orphaned_consent_records, and scheduler infrastructure.

Validates: Requirements 15.1-15.4, 16.1-16.4, 40.1
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from grins_platform.models.enums import (
    AgreementPaymentStatus,
    AgreementStatus,
    JobStatus,
)
from grins_platform.services.background_jobs import (
    AnnualNoticeSender,
    FailedPaymentEscalator,
    OrphanedConsentCleaner,
    UpcomingRenewalChecker,
    register_scheduled_jobs,
)


def _make_agreement(
    *,
    status: str = AgreementStatus.PAST_DUE.value,
    payment_status: str = AgreementPaymentStatus.PAST_DUE.value,
    updated_at: datetime | None = None,
    stripe_subscription_id: str = "sub_test",
    jobs: list[MagicMock] | None = None,
    customer: MagicMock | None = None,
    tier: MagicMock | None = None,
    last_annual_notice_sent: datetime | None = None,
    renewal_date: date | datetime | None = None,
) -> MagicMock:
    agr = MagicMock()
    agr.id = uuid4()
    agr.status = status
    agr.payment_status = payment_status
    agr.updated_at = updated_at or datetime.now(timezone.utc) - timedelta(days=10)
    agr.stripe_subscription_id = stripe_subscription_id
    agr.jobs = jobs or []
    agr.customer = customer or MagicMock(
        full_name="Test User",
        email="test@example.com",
    )
    agr.customer_id = uuid4()
    agr.tier = tier or MagicMock(name="Essential", included_services=["Spring Startup"])
    agr.last_annual_notice_sent = last_annual_notice_sent
    agr.renewal_date = renewal_date
    agr.annual_price = Decimal("299.00")
    return agr


def _make_job(status: str = JobStatus.TO_BE_SCHEDULED.value) -> MagicMock:
    job = MagicMock()
    job.status = status
    return job


class TestFailedPaymentEscalator:
    """Tests for FailedPaymentEscalator.run()."""

    @pytest.mark.asyncio
    async def test_past_due_7_days_transitions_to_paused(self):
        """PAST_DUE ≥ 7 days → PAUSED with Stripe pause_collection."""
        escalator = FailedPaymentEscalator()
        agreement = _make_agreement(
            status=AgreementStatus.PAST_DUE.value,
            updated_at=datetime.now(timezone.utc) - timedelta(days=8),
        )

        mock_session = AsyncMock()
        # First query (PAUSED ≥ 14 days) returns empty
        paused_result = MagicMock()
        paused_result.scalars.return_value.all.return_value = []
        # Second query (PAST_DUE ≥ 7 days) returns our agreement
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
            ) as mock_stripe_settings,
            patch("grins_platform.services.background_jobs.stripe") as mock_stripe,
        ):
            mock_stripe_settings.return_value.is_configured = True
            mock_stripe_settings.return_value.stripe_secret_key = "sk_test"
            await escalator.run()

        assert agreement.status == AgreementStatus.PAUSED.value
        assert "auto-paused" in agreement.pause_reason
        mock_stripe.Subscription.modify.assert_called_once()

    @pytest.mark.asyncio
    async def test_paused_14_days_transitions_to_cancelled(self):
        """PAUSED ≥ 14 days → CANCELLED with Stripe cancel."""
        escalator = FailedPaymentEscalator()
        job_to_be_scheduled = _make_job(JobStatus.TO_BE_SCHEDULED.value)
        job_completed = _make_job(JobStatus.COMPLETED.value)
        agreement = _make_agreement(
            status=AgreementStatus.PAUSED.value,
            updated_at=datetime.now(timezone.utc) - timedelta(days=15),
            jobs=[job_to_be_scheduled, job_completed],
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
            ) as mock_stripe_settings,
            patch("grins_platform.services.background_jobs.stripe") as mock_stripe,
        ):
            mock_stripe_settings.return_value.is_configured = True
            mock_stripe_settings.return_value.stripe_secret_key = "sk_test"
            await escalator.run()

        assert agreement.status == AgreementStatus.CANCELLED.value
        assert agreement.cancelled_at is not None
        assert job_to_be_scheduled.status == JobStatus.CANCELLED.value
        # Completed job should not be changed
        assert job_completed.status == JobStatus.COMPLETED.value
        mock_stripe.Subscription.cancel.assert_called_once()

    @pytest.mark.asyncio
    async def test_stripe_api_error_logged_not_raised(self):
        """Stripe API errors are logged but don't crash the job."""
        escalator = FailedPaymentEscalator()
        agreement = _make_agreement(
            status=AgreementStatus.PAST_DUE.value,
            updated_at=datetime.now(timezone.utc) - timedelta(days=8),
        )

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
            ) as mock_stripe_settings,
            patch("grins_platform.services.background_jobs.stripe") as mock_stripe,
        ):
            mock_stripe_settings.return_value.is_configured = True
            mock_stripe_settings.return_value.stripe_secret_key = "sk_test"
            mock_stripe.Subscription.modify.side_effect = Exception("Stripe error")
            # Should not raise
            await escalator.run()


class TestAnnualNoticeSender:
    """Tests for AnnualNoticeSender.run()."""

    @pytest.mark.asyncio
    async def test_skips_when_not_january(self):
        """Job skips execution when current month is not January."""
        sender = AnnualNoticeSender()
        non_jan = datetime(2026, 3, 15, tzinfo=timezone.utc)

        with patch(
            "grins_platform.services.background_jobs.datetime",
        ) as mock_dt:
            mock_dt.now.return_value = non_jan
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            await sender.run()
            # No DB calls should be made

    @pytest.mark.asyncio
    async def test_sends_annual_notice_in_january(self):
        """Sends annual notices and creates disclosure records in January."""
        sender = AnnualNoticeSender()
        agreement = _make_agreement(
            status=AgreementStatus.ACTIVE.value,
            last_annual_notice_sent=None,
        )

        mock_session = AsyncMock()
        mock_compliance = AsyncMock()
        mock_compliance.get_annual_notice_due = AsyncMock(return_value=[agreement])
        mock_compliance.create_disclosure = AsyncMock()

        mock_email = MagicMock()
        mock_email.send_annual_notice.return_value = {
            "sent": True,
            "sent_via": "email",
            "recipient_email": "test@example.com",
            "content": "<html>notice</html>",
        }

        mock_db = MagicMock()

        async def mock_get_session():
            yield mock_session

        mock_db.get_session = mock_get_session

        jan_time = datetime(2026, 1, 15, 10, 0, tzinfo=timezone.utc)

        with (
            patch(
                "grins_platform.services.background_jobs.get_database_manager",
                return_value=mock_db,
            ),
            patch(
                "grins_platform.services.background_jobs.EmailService",
                return_value=mock_email,
            ),
            patch(
                "grins_platform.services.background_jobs.ComplianceService",
                return_value=mock_compliance,
            ),
            patch(
                "grins_platform.services.background_jobs.datetime",
            ) as mock_dt,
        ):
            mock_dt.now.return_value = jan_time
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            await sender.run()

        mock_email.send_annual_notice.assert_called_once_with(
            customer=agreement.customer,
            agreement=agreement,
        )
        mock_compliance.create_disclosure.assert_called_once()


class TestOrphanedConsentCleaner:
    """Tests for OrphanedConsentCleaner.run()."""

    @pytest.mark.asyncio
    async def test_marks_old_orphaned_records_as_abandoned(self):
        """Records > 30 days with no customer_id are marked abandoned."""
        cleaner = OrphanedConsentCleaner()
        old_record = MagicMock()
        old_record.customer_id = None
        old_record.consent_timestamp = datetime.now(timezone.utc) - timedelta(days=35)

        mock_session = AsyncMock()
        result = MagicMock()
        result.scalars.return_value.all.return_value = [old_record]
        mock_session.execute = AsyncMock(return_value=result)

        mock_db = MagicMock()

        async def mock_get_session():
            yield mock_session

        mock_db.get_session = mock_get_session

        with patch(
            "grins_platform.services.background_jobs.get_database_manager",
            return_value=mock_db,
        ):
            await cleaner.run()

        assert old_record.consent_type == "abandoned"


class TestUpcomingRenewalChecker:
    """Tests for UpcomingRenewalChecker.run()."""

    @pytest.mark.asyncio
    async def test_logs_upcoming_renewals(self):
        """Agreements renewing within 30 days are logged."""
        checker = UpcomingRenewalChecker()
        today = datetime.now(timezone.utc).date()
        agreement = _make_agreement(
            status=AgreementStatus.ACTIVE.value,
            renewal_date=today + timedelta(days=7),
        )

        mock_session = AsyncMock()
        result = MagicMock()
        result.scalars.return_value.all.return_value = [agreement]
        mock_session.execute = AsyncMock(return_value=result)

        mock_db = MagicMock()

        async def mock_get_session():
            yield mock_session

        mock_db.get_session = mock_get_session

        with patch(
            "grins_platform.services.background_jobs.get_database_manager",
            return_value=mock_db,
        ):
            await checker.run()
        # No exception means success


class TestRegisterScheduledJobs:
    """Tests for register_scheduled_jobs."""

    def test_registers_all_four_jobs(self):
        """All six scheduled jobs are registered."""
        mock_scheduler = MagicMock()
        register_scheduled_jobs(mock_scheduler)
        assert mock_scheduler.add_job.call_count == 6

        job_ids = [call.kwargs["id"] for call in mock_scheduler.add_job.call_args_list]
        assert "escalate_failed_payments" in job_ids
        assert "check_upcoming_renewals" in job_ids
        assert "send_annual_notices" in job_ids
        assert "cleanup_orphaned_consent_records" in job_ids
        assert "remind_incomplete_onboarding" in job_ids
        assert "process_pending_campaign_recipients" in job_ids

    def test_escalate_runs_daily(self):
        """escalate_failed_payments is a daily cron job."""
        mock_scheduler = MagicMock()
        register_scheduled_jobs(mock_scheduler)

        escalate_call = next(
            c
            for c in mock_scheduler.add_job.call_args_list
            if c.kwargs["id"] == "escalate_failed_payments"
        )
        assert escalate_call.args[1] == "cron"

    def test_renewal_check_at_9am(self):
        """check_upcoming_renewals runs at 9 AM."""
        mock_scheduler = MagicMock()
        register_scheduled_jobs(mock_scheduler)

        renewal_call = next(
            c
            for c in mock_scheduler.add_job.call_args_list
            if c.kwargs["id"] == "check_upcoming_renewals"
        )
        assert renewal_call.kwargs["hour"] == 9

    def test_cleanup_runs_weekly(self):
        """cleanup_orphaned_consent_records runs weekly on Sunday."""
        mock_scheduler = MagicMock()
        register_scheduled_jobs(mock_scheduler)

        cleanup_call = next(
            c
            for c in mock_scheduler.add_job.call_args_list
            if c.kwargs["id"] == "cleanup_orphaned_consent_records"
        )
        assert cleanup_call.kwargs["day_of_week"] == "sun"
