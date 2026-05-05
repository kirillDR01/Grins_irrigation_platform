"""Functional tests for the F7 estimate-follow-up cron.

Wires the cron through ``EstimateFollowUpJob.run`` with mocked DB
manager + repository + SMS provider, asserting that:

- a Day-3 follow-up whose ``scheduled_at`` is in the past flips to
  ``SENT`` after one cron pass,
- the other 3 (Day 7 / 14 / 21) future rows remain ``SCHEDULED`` because
  ``EstimateRepository.get_pending_follow_ups`` only returns due rows,
- the cron commits the session,
- the SMS provider receives a single send call.

Mirrors ``test_background_jobs_functional.py``'s shape: mocked repo +
real ``EstimateService`` so the integration between the cron wrapper
and ``process_follow_ups`` is exercised end-to-end (only the DB and the
SMS network call are stubbed).

Validates: F7 sign-off (run-20260504-184355-portal-cron).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from grins_platform.models.enums import EstimateStatus, FollowUpStatus


def _make_customer(
    *,
    phone: str = "9527373312",
    email: str = "kirillrakitinsecond@gmail.com",
    first_name: str = "Test",
) -> MagicMock:
    c = MagicMock()
    c.id = uuid4()
    c.phone = phone
    c.email = email
    c.first_name = first_name
    return c


def _make_estimate(*, customer: MagicMock | None = None) -> MagicMock:
    customer = customer or _make_customer()
    e = MagicMock()
    e.id = uuid4()
    e.customer_id = customer.id
    e.lead_id = None
    e.status = EstimateStatus.SENT.value
    e.approved_at = None
    e.rejected_at = None
    e.customer_token = uuid4()
    e.customer = customer
    return e


def _make_follow_up(
    *,
    estimate_id: Any,
    follow_up_number: int,
    scheduled_at: datetime,
    status: str = FollowUpStatus.SCHEDULED.value,
) -> MagicMock:
    fu = MagicMock()
    fu.id = uuid4()
    fu.estimate_id = estimate_id
    fu.follow_up_number = follow_up_number
    fu.scheduled_at = scheduled_at
    fu.status = status
    fu.message = None
    fu.promotion_code = None
    fu.sent_at = None
    return fu


def _make_db_manager(session: MagicMock) -> MagicMock:
    db = MagicMock()

    async def _get_session():
        yield session

    db.get_session = _get_session
    return db


@pytest.mark.functional
@pytest.mark.asyncio
async def test_due_day3_follow_up_flips_to_sent() -> None:
    """A Day-3 row whose scheduled_at is in the past flips to SENT after one run.

    Day 7/14/21 rows aren't in the repo's pending-list (the real repo
    filters by ``scheduled_at <= now``), so they remain SCHEDULED.
    """
    from grins_platform.services.estimate_follow_up_job import EstimateFollowUpJob

    customer = _make_customer()
    estimate = _make_estimate(customer=customer)

    now = datetime.now(tz=timezone.utc)
    fu_day3 = _make_follow_up(
        estimate_id=estimate.id,
        follow_up_number=1,
        scheduled_at=now - timedelta(days=3, minutes=1),
    )
    fu_day7 = _make_follow_up(
        estimate_id=estimate.id,
        follow_up_number=2,
        scheduled_at=now + timedelta(days=4),
    )
    fu_day14 = _make_follow_up(
        estimate_id=estimate.id,
        follow_up_number=3,
        scheduled_at=now + timedelta(days=11),
    )
    fu_day21 = _make_follow_up(
        estimate_id=estimate.id,
        follow_up_number=4,
        scheduled_at=now + timedelta(days=18),
    )

    session = AsyncMock()
    session.commit = AsyncMock()
    session.flush = AsyncMock()

    repo = AsyncMock()
    repo.session = session
    # Real repo would filter scheduled_at <= now; mirror that here.
    repo.get_pending_follow_ups = AsyncMock(return_value=[fu_day3])
    repo.get_by_id = AsyncMock(return_value=estimate)

    sms_service = AsyncMock()
    sms_service.send_automated_message = AsyncMock(
        return_value={"success": True, "message_id": str(uuid4())},
    )

    with (
        patch(
            "grins_platform.services.estimate_follow_up_job.get_database_manager",
            return_value=_make_db_manager(session),
        ),
        patch(
            "grins_platform.services.estimate_follow_up_job.EstimateRepository",
            return_value=repo,
        ),
        patch(
            "grins_platform.services.estimate_follow_up_job.SMSService",
            return_value=sms_service,
        ),
        patch(
            "grins_platform.services.estimate_follow_up_job.get_sms_provider",
            return_value=MagicMock(),
        ),
        patch(
            "grins_platform.services.estimate_follow_up_job.EmailSettings",
            return_value=MagicMock(
                portal_base_url=(
                    "https://grins-irrigation-platform-git-dev-"
                    "kirilldr01s-projects.vercel.app"
                ),
            ),
        ),
    ):
        await EstimateFollowUpJob().run()

    assert fu_day3.status == FollowUpStatus.SENT.value
    assert fu_day3.sent_at is not None
    assert fu_day7.status == FollowUpStatus.SCHEDULED.value
    assert fu_day14.status == FollowUpStatus.SCHEDULED.value
    assert fu_day21.status == FollowUpStatus.SCHEDULED.value

    sms_service.send_automated_message.assert_awaited_once()
    sent_kwargs = sms_service.send_automated_message.call_args.kwargs
    assert sent_kwargs["phone"] == customer.phone
    assert sent_kwargs["message_type"] == "estimate_sent"

    session.commit.assert_awaited_once()


@pytest.mark.functional
@pytest.mark.asyncio
async def test_already_approved_estimate_cancels_remaining_follow_ups() -> None:
    """If estimate is already approved between scheduling and running,
    process_follow_ups cancels remaining rows and does not SMS."""
    from grins_platform.services.estimate_follow_up_job import EstimateFollowUpJob

    customer = _make_customer()
    estimate = _make_estimate(customer=customer)
    estimate.approved_at = datetime.now(tz=timezone.utc)

    fu = _make_follow_up(
        estimate_id=estimate.id,
        follow_up_number=1,
        scheduled_at=datetime.now(tz=timezone.utc) - timedelta(hours=1),
    )

    session = AsyncMock()
    session.commit = AsyncMock()
    session.flush = AsyncMock()

    repo = AsyncMock()
    repo.session = session
    repo.get_pending_follow_ups = AsyncMock(return_value=[fu])
    repo.get_by_id = AsyncMock(return_value=estimate)
    repo.cancel_follow_ups_for_estimate = AsyncMock(return_value=1)

    sms_service = AsyncMock()
    sms_service.send_automated_message = AsyncMock()

    with (
        patch(
            "grins_platform.services.estimate_follow_up_job.get_database_manager",
            return_value=_make_db_manager(session),
        ),
        patch(
            "grins_platform.services.estimate_follow_up_job.EstimateRepository",
            return_value=repo,
        ),
        patch(
            "grins_platform.services.estimate_follow_up_job.SMSService",
            return_value=sms_service,
        ),
        patch(
            "grins_platform.services.estimate_follow_up_job.get_sms_provider",
            return_value=MagicMock(),
        ),
        patch(
            "grins_platform.services.estimate_follow_up_job.EmailSettings",
            return_value=MagicMock(portal_base_url="https://example.test"),
        ),
    ):
        await EstimateFollowUpJob().run()

    sms_service.send_automated_message.assert_not_awaited()
    repo.cancel_follow_ups_for_estimate.assert_awaited_once_with(estimate.id)
    session.commit.assert_awaited_once()
