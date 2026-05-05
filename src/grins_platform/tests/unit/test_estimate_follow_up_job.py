"""Unit tests for EstimateFollowUpJob (F7).

Mirrors ``test_sales_pipeline_nudge_job.py``: the cron wraps an
``EstimateService.process_follow_ups()`` call wired with the SMS service
the production cron must construct itself. The unit tests here patch
collaborators at the cron-module boundary (``EstimateService``,
``EstimateRepository``, ``SMSService``, ``get_database_manager``,
``EmailSettings``) and assert the job:

- constructs an ``EstimateService`` with a non-None ``sms_service`` (so
  rows don't silently flip to ``SKIPPED``),
- calls ``process_follow_ups`` exactly once,
- commits the session.

Validates: F7 sign-off (run-20260504-184355-portal-cron).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _make_db_manager(session) -> MagicMock:
    db = MagicMock()

    async def _get_session():
        yield session

    db.get_session = _get_session
    return db


@pytest.mark.asyncio
async def test_run_constructs_service_with_sms_and_calls_process_follow_ups():
    """run() must wire SMS into EstimateService and call process_follow_ups."""
    from grins_platform.services.estimate_follow_up_job import EstimateFollowUpJob

    session = AsyncMock()
    session.commit = AsyncMock()

    mock_estimate_service = MagicMock()
    mock_estimate_service.process_follow_ups = AsyncMock(return_value=2)
    mock_sms_service = MagicMock()
    mock_repo = MagicMock()
    mock_email_settings = MagicMock(portal_base_url="https://example.test")

    with (
        patch(
            "grins_platform.services.estimate_follow_up_job.get_database_manager",
            return_value=_make_db_manager(session),
        ),
        patch(
            "grins_platform.services.estimate_follow_up_job.EstimateRepository",
            return_value=mock_repo,
        ),
        patch(
            "grins_platform.services.estimate_follow_up_job.SMSService",
            return_value=mock_sms_service,
        ),
        patch(
            "grins_platform.services.estimate_follow_up_job.get_sms_provider",
            return_value=MagicMock(),
        ),
        patch(
            "grins_platform.services.estimate_follow_up_job.EmailSettings",
            return_value=mock_email_settings,
        ),
        patch(
            "grins_platform.services.estimate_follow_up_job.EstimateService",
            return_value=mock_estimate_service,
        ) as mock_es_ctor,
    ):
        await EstimateFollowUpJob().run()

    # EstimateService must be constructed with a non-None sms_service —
    # without it process_follow_ups silently SKIPS every row.
    ctor_kwargs = mock_es_ctor.call_args.kwargs
    assert ctor_kwargs["sms_service"] is mock_sms_service
    assert ctor_kwargs["portal_base_url"] == "https://example.test"
    assert ctor_kwargs["estimate_repository"] is mock_repo

    mock_estimate_service.process_follow_ups.assert_awaited_once_with()
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_run_zero_pending_still_commits():
    """No due rows → process_follow_ups returns 0; cron still commits."""
    from grins_platform.services.estimate_follow_up_job import EstimateFollowUpJob

    session = AsyncMock()
    session.commit = AsyncMock()
    mock_estimate_service = MagicMock()
    mock_estimate_service.process_follow_ups = AsyncMock(return_value=0)

    with (
        patch(
            "grins_platform.services.estimate_follow_up_job.get_database_manager",
            return_value=_make_db_manager(session),
        ),
        patch(
            "grins_platform.services.estimate_follow_up_job.EstimateRepository",
            return_value=MagicMock(),
        ),
        patch(
            "grins_platform.services.estimate_follow_up_job.SMSService",
            return_value=MagicMock(),
        ),
        patch(
            "grins_platform.services.estimate_follow_up_job.get_sms_provider",
            return_value=MagicMock(),
        ),
        patch(
            "grins_platform.services.estimate_follow_up_job.EmailSettings",
            return_value=MagicMock(portal_base_url="https://example.test"),
        ),
        patch(
            "grins_platform.services.estimate_follow_up_job.EstimateService",
            return_value=mock_estimate_service,
        ),
    ):
        await EstimateFollowUpJob().run()

    mock_estimate_service.process_follow_ups.assert_awaited_once_with()
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_async_wrapper_invokes_singleton_run():
    """process_estimate_follow_ups_job calls the module-level singleton."""
    from grins_platform.services import estimate_follow_up_job as module

    with patch.object(module._estimate_follow_up_job, "run", AsyncMock()) as mock_run:
        await module.process_estimate_follow_ups_job()
    mock_run.assert_awaited_once_with()


def test_register_scheduled_jobs_includes_estimate_follow_ups():
    """register_scheduled_jobs must register process_estimate_follow_ups."""
    from apscheduler.schedulers.background import BackgroundScheduler

    from grins_platform.services.background_jobs import register_scheduled_jobs

    scheduler = BackgroundScheduler()
    register_scheduled_jobs(scheduler)
    job_ids = {j.id for j in scheduler.get_jobs()}
    assert "process_estimate_follow_ups" in job_ids
