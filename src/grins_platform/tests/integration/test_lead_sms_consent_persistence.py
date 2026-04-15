"""Regression tests for BUG-001: lead form silent rollback when sms_consent=true.

Bug context: on 2026-04-14 every POST /api/v1/leads with sms_consent=true
returned HTTP 201 + lead_id, but the row was rolled back before commit
because inline SMS confirmation raised a SQLAlchemy error that corrupted
the request-scoped session. These tests guard the fix: SMS + email
confirmations are scheduled as FastAPI BackgroundTasks (run post-commit
in a fresh session), so a failure in the notification path cannot poison
the lead-intake transaction.

Validates: BUG-001 fix (bughunt/2026-04-14-lead-form-sms-consent-rollback.md);
Requirements 1.10, 46.7, 55.1-55.3.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from grins_platform.models.enums import LeadSituation
from grins_platform.schemas.lead import LeadSubmission
from grins_platform.services.lead_service import (
    LeadService,
    send_lead_confirmations_post_commit,
)


def _build_lead_mock(
    *,
    sms_consent: bool,
    phone: str = "9527373312",
    email: str | None = "lead-sms@grinstest.example",
) -> MagicMock:
    lead = MagicMock()
    lead.id = uuid.uuid4()
    lead.phone = phone
    lead.email = email
    lead.sms_consent = sms_consent
    return lead


def _build_service(
    *,
    created_lead: MagicMock,
    sms_raises: bool = False,
) -> tuple[LeadService, AsyncMock, AsyncMock, AsyncMock]:
    lead_repo = AsyncMock()
    lead_repo.get_recent_by_phone_or_email = AsyncMock(return_value=None)
    lead_repo.get_by_phone_and_active_status = AsyncMock(return_value=None)
    lead_repo.create = AsyncMock(return_value=created_lead)

    sms_svc = AsyncMock()
    if sms_raises:
        sms_svc.send_automated_message = AsyncMock(
            side_effect=RuntimeError(
                "simulated SMS/session failure — if this propagates, "
                "the lead would be silently rolled back (BUG-001)",
            ),
        )
    else:
        sms_svc.send_automated_message = AsyncMock(return_value={"success": True})

    compliance_svc = AsyncMock()
    compliance_svc.create_sms_consent = AsyncMock()

    service = LeadService(
        lead_repository=lead_repo,
        customer_service=AsyncMock(),
        job_service=AsyncMock(),
        staff_repository=AsyncMock(),
        sms_service=sms_svc,
        email_service=MagicMock(),
        compliance_service=compliance_svc,
    )
    return service, lead_repo, sms_svc, compliance_svc


@pytest.mark.integration
class TestLeadSmsConsentPersistence:
    """Guard BUG-001: lead must persist regardless of sms_consent value."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("sms_consent", [True, False])
    async def test_lead_persists_for_both_sms_consent_values(
        self,
        sms_consent: bool,
    ) -> None:
        """POST path must persist the lead for both sms_consent values.

        Prior to the fix, sms_consent=True silently rolled back the lead.
        """
        created_lead = _build_lead_mock(sms_consent=sms_consent)
        service, lead_repo, sms_svc, compliance_svc = _build_service(
            created_lead=created_lead,
        )
        background_tasks = MagicMock()

        data = LeadSubmission(
            name="BUG-001 Regression",
            phone="9527373312",
            email="lead-sms@grinstest.example",
            address="123 Regression Rd, Plymouth, MN 55441",
            zip_code="55441",
            situation=LeadSituation.NEW_SYSTEM,
            sms_consent=sms_consent,
            terms_accepted=True,
            source_site="website",
        )

        result = await service.submit_lead(
            data,
            background_tasks=background_tasks,
        )

        assert result.success is True
        assert result.lead_id == created_lead.id
        lead_repo.create.assert_awaited_once()
        compliance_svc.create_sms_consent.assert_awaited_once()
        # SMS must never be called synchronously inside the request
        # transaction — that was the bug path.
        sms_svc.send_automated_message.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_sms_consent_true_schedules_post_commit_task(self) -> None:
        """With sms_consent=True, a post-commit background task is scheduled."""
        created_lead = _build_lead_mock(sms_consent=True)
        service, _, _, _ = _build_service(created_lead=created_lead)
        background_tasks = MagicMock()

        data = LeadSubmission(
            name="SMS Scheduler Test",
            phone="9527373312",
            email="sched@grinstest.example",
            address="123 Scheduler St, Plymouth, MN 55441",
            zip_code="55441",
            situation=LeadSituation.NEW_SYSTEM,
            sms_consent=True,
            terms_accepted=True,
            source_site="website",
        )

        await service.submit_lead(data, background_tasks=background_tasks)

        background_tasks.add_task.assert_called_once()
        scheduled_fn, *scheduled_args = background_tasks.add_task.call_args.args
        assert scheduled_fn is send_lead_confirmations_post_commit
        assert scheduled_args[0] == created_lead.id

    @pytest.mark.asyncio
    async def test_submit_lead_survives_sms_failure(self) -> None:
        """Even when SMS path would raise, submit_lead still returns success.

        This proves the structural fix: the SMS send is deferred to a
        post-commit task run in a fresh session, so it cannot affect the
        lead transaction. The raising AsyncMock here would have poisoned
        the request session under the old inline-call code path.
        """
        created_lead = _build_lead_mock(sms_consent=True)
        service, lead_repo, sms_svc, _ = _build_service(
            created_lead=created_lead,
            sms_raises=True,
        )
        background_tasks = MagicMock()

        data = LeadSubmission(
            name="SMS Failure Survivor",
            phone="9527373312",
            email="survivor@grinstest.example",
            address="123 Survivor Way, Plymouth, MN 55441",
            zip_code="55441",
            situation=LeadSituation.NEW_SYSTEM,
            sms_consent=True,
            terms_accepted=True,
            source_site="website",
        )

        result = await service.submit_lead(
            data,
            background_tasks=background_tasks,
        )

        assert result.success is True
        assert result.lead_id == created_lead.id
        lead_repo.create.assert_awaited_once()
        sms_svc.send_automated_message.assert_not_awaited()
        background_tasks.add_task.assert_called_once()
