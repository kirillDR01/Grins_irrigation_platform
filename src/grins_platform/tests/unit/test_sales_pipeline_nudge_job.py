"""Unit tests for SalesPipelineNudgeJob (F6).

Validates: F6 sign-off (run-20260504-185844-full).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from grins_platform.models.enums import SalesEntryStatus
from grins_platform.services.sales_pipeline_nudge_job import (
    STALE_DAYS,
    SalesPipelineNudgeJob,
)


def _make_entry(
    *,
    status: str = SalesEntryStatus.SEND_ESTIMATE.value,
    last_contact_age_days: float = STALE_DAYS + 1,
    nudges_paused_until: datetime | None = None,
    dismissed_at: datetime | None = None,
    customer_email: str | None = "kirillrakitinsecond@gmail.com",
    customer_first_name: str | None = "Test",
):
    """Build a minimal SalesEntry-like SimpleNamespace for the job."""
    now = datetime.now(timezone.utc)
    customer = SimpleNamespace(
        email=customer_email,
        first_name=customer_first_name,
    )
    return SimpleNamespace(
        id=uuid4(),
        status=status,
        last_contact_date=now - timedelta(days=last_contact_age_days),
        nudges_paused_until=nudges_paused_until,
        dismissed_at=dismissed_at,
        updated_at=now - timedelta(days=last_contact_age_days),
        customer=customer,
    )


def _make_session(entries: list) -> AsyncMock:
    """Build a mock session whose execute() returns the given entries."""
    session = AsyncMock()
    list_result = MagicMock()
    list_result.scalars.return_value.all.return_value = entries
    session.execute = AsyncMock(return_value=list_result)
    session.commit = AsyncMock()
    return session


def _make_db_manager(session):
    db = MagicMock()

    async def _get_session():
        yield session

    db.get_session = _get_session
    return db


@pytest.mark.asyncio
async def test_nudge_sends_for_stale_send_estimate():
    """Stale SEND_ESTIMATE → email sent, last_contact_date bumped, audit row."""
    entry = _make_entry()
    session = _make_session([entry])
    job = SalesPipelineNudgeJob()

    mock_email = MagicMock()
    mock_email.send_sales_pipeline_nudge = MagicMock(
        return_value={"sent": True, "sent_via": "resend", "content": "..."},
    )
    mock_audit = AsyncMock()
    mock_audit.log_action = AsyncMock(return_value=MagicMock(id=uuid4()))

    with (
        patch(
            "grins_platform.services.sales_pipeline_nudge_job.get_database_manager",
            return_value=_make_db_manager(session),
        ),
        patch(
            "grins_platform.services.sales_pipeline_nudge_job.EmailService",
            return_value=mock_email,
        ),
        patch(
            "grins_platform.services.sales_pipeline_nudge_job.AuditService",
            return_value=mock_audit,
        ),
    ):
        await job.run()

    mock_email.send_sales_pipeline_nudge.assert_called_once()
    mock_audit.log_action.assert_called_once()
    audit_kwargs = mock_audit.log_action.call_args.kwargs
    assert audit_kwargs["action"] == "sales_pipeline.nudge.sent"
    assert audit_kwargs["resource_type"] == "sales_pipeline_entry"
    assert audit_kwargs["details"]["actor_type"] == "system"
    assert audit_kwargs["details"]["source"] == "nightly_job"
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_nudge_skips_paused():
    """nudges_paused_until in the future → no email, but per repo this is
    enforced at query level. The mock returns an empty list when paused."""
    session = _make_session([])  # query filters out the paused row
    job = SalesPipelineNudgeJob()

    mock_email = MagicMock()
    mock_email.send_sales_pipeline_nudge = MagicMock()
    mock_audit = AsyncMock()

    with (
        patch(
            "grins_platform.services.sales_pipeline_nudge_job.get_database_manager",
            return_value=_make_db_manager(session),
        ),
        patch(
            "grins_platform.services.sales_pipeline_nudge_job.EmailService",
            return_value=mock_email,
        ),
        patch(
            "grins_platform.services.sales_pipeline_nudge_job.AuditService",
            return_value=mock_audit,
        ),
    ):
        await job.run()

    mock_email.send_sales_pipeline_nudge.assert_not_called()
    mock_audit.log_action.assert_not_called()


@pytest.mark.asyncio
async def test_nudge_skips_no_email():
    """Entry whose customer has no email → no send, no audit, no exception."""
    entry = _make_entry(customer_email=None)
    session = _make_session([entry])
    job = SalesPipelineNudgeJob()

    mock_email = MagicMock()
    mock_email.send_sales_pipeline_nudge = MagicMock()
    mock_audit = AsyncMock()

    with (
        patch(
            "grins_platform.services.sales_pipeline_nudge_job.get_database_manager",
            return_value=_make_db_manager(session),
        ),
        patch(
            "grins_platform.services.sales_pipeline_nudge_job.EmailService",
            return_value=mock_email,
        ),
        patch(
            "grins_platform.services.sales_pipeline_nudge_job.AuditService",
            return_value=mock_audit,
        ),
    ):
        await job.run()

    mock_email.send_sales_pipeline_nudge.assert_not_called()
    mock_audit.log_action.assert_not_called()
    # Job still commits (to release the snapshot, even if zero changes).
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_nudge_send_failed_does_not_audit_or_bump():
    """If the email returns sent=False, no audit row and no last_contact_date bump."""
    entry = _make_entry()
    original_lcd = entry.last_contact_date
    session = _make_session([entry])
    job = SalesPipelineNudgeJob()

    mock_email = MagicMock()
    mock_email.send_sales_pipeline_nudge = MagicMock(
        return_value={"sent": False, "sent_via": "pending"},
    )
    mock_audit = AsyncMock()

    with (
        patch(
            "grins_platform.services.sales_pipeline_nudge_job.get_database_manager",
            return_value=_make_db_manager(session),
        ),
        patch(
            "grins_platform.services.sales_pipeline_nudge_job.EmailService",
            return_value=mock_email,
        ),
        patch(
            "grins_platform.services.sales_pipeline_nudge_job.AuditService",
            return_value=mock_audit,
        ),
    ):
        await job.run()

    mock_email.send_sales_pipeline_nudge.assert_called_once()
    mock_audit.log_action.assert_not_called()
    assert entry.last_contact_date == original_lcd


@pytest.mark.asyncio
async def test_nudge_processes_multiple_entries():
    """Multiple stale entries → multiple sends + audits in one run."""
    entries = [_make_entry(), _make_entry(), _make_entry()]
    session = _make_session(entries)
    job = SalesPipelineNudgeJob()

    mock_email = MagicMock()
    mock_email.send_sales_pipeline_nudge = MagicMock(
        return_value={"sent": True, "sent_via": "resend"},
    )
    mock_audit = AsyncMock()
    mock_audit.log_action = AsyncMock(return_value=MagicMock(id=uuid4()))

    with (
        patch(
            "grins_platform.services.sales_pipeline_nudge_job.get_database_manager",
            return_value=_make_db_manager(session),
        ),
        patch(
            "grins_platform.services.sales_pipeline_nudge_job.EmailService",
            return_value=mock_email,
        ),
        patch(
            "grins_platform.services.sales_pipeline_nudge_job.AuditService",
            return_value=mock_audit,
        ),
    ):
        await job.run()

    assert mock_email.send_sales_pipeline_nudge.call_count == 3
    assert mock_audit.log_action.call_count == 3
    session.commit.assert_awaited_once()


def test_register_scheduled_jobs_includes_nudge():
    """register_scheduled_jobs must register the nudge_stale_sales_entries job."""
    from apscheduler.schedulers.background import BackgroundScheduler

    from grins_platform.services.background_jobs import register_scheduled_jobs

    scheduler = BackgroundScheduler()
    register_scheduled_jobs(scheduler)
    job_ids = {j.id for j in scheduler.get_jobs()}
    assert "nudge_stale_sales_entries" in job_ids
