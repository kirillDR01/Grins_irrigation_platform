"""Unit tests for the auto-job-on-approval branch in EstimateService.

Validates: appointment-modal umbrella plan Phase 0 (AJ-1, AJ-3, AJ-4,
AJ-7, N5).
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from grins_platform.services.estimate_service import EstimateService


def _make_service(
    *,
    job_service: AsyncMock | None = None,
    business_setting_service: AsyncMock | None = None,
    audit_service: AsyncMock | None = None,
    estimate_pdf_service: AsyncMock | None = None,
    email_service: MagicMock | None = None,
) -> EstimateService:
    repo = AsyncMock()
    repo.session = AsyncMock()
    return EstimateService(
        estimate_repository=repo,
        portal_base_url="http://localhost:5173",
        email_service=email_service,
        job_service=job_service,
        business_setting_service=business_setting_service,
        audit_service=audit_service,
        estimate_pdf_service=estimate_pdf_service,
    )


def _make_estimate(
    *,
    customer_id: object | None = None,
    job_id: object | None = None,
    line_items: list[dict[str, object]] | None = None,
) -> MagicMock:
    est = MagicMock()
    est.id = uuid4()
    est.customer_id = customer_id
    est.job_id = job_id
    est.total = Decimal("499.00")
    est.notes = None
    est.line_items = line_items or [
        {"description": "Spring start-up", "unit_price": 250, "quantity": 2}
    ]
    return est


@pytest.mark.unit
class TestMaybeAutoCreateJob:
    @pytest.mark.asyncio
    async def test_standalone_creates_job_when_setting_on(self) -> None:
        bss = AsyncMock()
        bss.get_bool = AsyncMock(return_value=True)

        new_job = MagicMock()
        new_job.id = uuid4()

        job_service = AsyncMock()
        job_service.create_job = AsyncMock(return_value=new_job)

        audit_service = AsyncMock()
        audit_service.log_action = AsyncMock()

        svc = _make_service(
            job_service=job_service,
            business_setting_service=bss,
            audit_service=audit_service,
        )
        # repo.update returns the updated estimate (not used here)
        svc.repo.update = AsyncMock()

        est = _make_estimate(customer_id=uuid4(), job_id=None)
        await svc._maybe_auto_create_job(est, "1.2.3.4", "ua")

        job_service.create_job.assert_awaited_once()
        # estimate.job_id back-fill
        svc.repo.update.assert_awaited_once()
        # scope_items copied to job
        assert new_job.scope_items == est.line_items
        # audit row written
        audit_service.log_action.assert_awaited()
        action = audit_service.log_action.await_args.kwargs["action"]
        assert action == "estimate.auto_job_created"

    @pytest.mark.asyncio
    async def test_standalone_skips_when_setting_off(self) -> None:
        bss = AsyncMock()
        bss.get_bool = AsyncMock(return_value=False)

        job_service = AsyncMock()
        audit_service = AsyncMock()

        svc = _make_service(
            job_service=job_service,
            business_setting_service=bss,
            audit_service=audit_service,
        )

        est = _make_estimate(customer_id=uuid4(), job_id=None)
        await svc._maybe_auto_create_job(est, "1.2.3.4", "ua")

        job_service.create_job.assert_not_called()
        audit_service.log_action.assert_awaited()
        kwargs = audit_service.log_action.await_args.kwargs
        assert kwargs["action"] == "estimate.auto_job_skipped"
        assert kwargs["details"]["skip_reason"] == "setting_off"

    @pytest.mark.asyncio
    async def test_attached_branch_copies_into_parent_job(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        bss = AsyncMock()
        bss.get_bool = AsyncMock(return_value=True)

        job_service = AsyncMock()
        # Standalone path's create_job MUST NOT be called for attached.
        job_service.create_job = AsyncMock()

        audit_service = AsyncMock()
        svc = _make_service(
            job_service=job_service,
            business_setting_service=bss,
            audit_service=audit_service,
        )

        est = _make_estimate(customer_id=uuid4(), job_id=uuid4())

        # Stub the helper that touches the DB session — the unit test
        # focuses on the branching, not the SQL plumbing.
        copy_mock = AsyncMock()
        monkeypatch.setattr(svc, "_copy_scope_into_parent_job", copy_mock)

        await svc._maybe_auto_create_job(est, "1.2.3.4", "ua")

        copy_mock.assert_awaited_once()
        job_service.create_job.assert_not_called()
        action = audit_service.log_action.await_args.kwargs["action"]
        assert action == "estimate.auto_job_created"
        assert (
            audit_service.log_action.await_args.kwargs["details"]["branch"]
            == "attached"
        )

    @pytest.mark.asyncio
    async def test_lead_only_estimate_skips_with_no_customer_reason(self) -> None:
        bss = AsyncMock()
        bss.get_bool = AsyncMock(return_value=True)

        job_service = AsyncMock()
        audit_service = AsyncMock()

        svc = _make_service(
            job_service=job_service,
            business_setting_service=bss,
            audit_service=audit_service,
        )

        est = _make_estimate(customer_id=None, job_id=None)
        await svc._maybe_auto_create_job(est, "1.2.3.4", "ua")

        job_service.create_job.assert_not_called()
        audit_service.log_action.assert_awaited()
        kwargs = audit_service.log_action.await_args.kwargs
        assert kwargs["action"] == "estimate.auto_job_skipped"
        assert kwargs["details"]["skip_reason"] == "no_customer"

    @pytest.mark.asyncio
    async def test_no_job_service_di_skips_silently(self) -> None:
        bss = AsyncMock()
        bss.get_bool = AsyncMock(return_value=True)
        svc = _make_service(business_setting_service=bss)
        est = _make_estimate(customer_id=uuid4(), job_id=None)
        # Must not raise.
        await svc._maybe_auto_create_job(est, "1.2.3.4", "ua")

    @pytest.mark.asyncio
    async def test_create_job_failure_is_swallowed_and_audited(self) -> None:
        bss = AsyncMock()
        bss.get_bool = AsyncMock(return_value=True)

        job_service = AsyncMock()
        job_service.create_job = AsyncMock(
            side_effect=RuntimeError("downstream failure")
        )

        audit_service = AsyncMock()

        svc = _make_service(
            job_service=job_service,
            business_setting_service=bss,
            audit_service=audit_service,
        )

        est = _make_estimate(customer_id=uuid4(), job_id=None)
        # Must NOT raise — approval has been recorded already.
        await svc._maybe_auto_create_job(est, "1.2.3.4", "ua")
        kwargs = audit_service.log_action.await_args.kwargs
        assert kwargs["action"] == "estimate.auto_job_skipped"
        assert kwargs["details"]["skip_reason"] == "job_create_failed"


@pytest.mark.unit
class TestSendSignedPdfEmail:
    @pytest.mark.asyncio
    async def test_skips_when_recipient_has_no_email(self) -> None:
        pdf = AsyncMock()
        email = MagicMock()
        svc = _make_service(estimate_pdf_service=pdf, email_service=email)
        est = MagicMock()
        est.id = uuid4()
        est.customer = None
        est.lead = MagicMock()
        est.lead.email = None
        await svc._send_signed_pdf_email(est)
        pdf.generate_pdf_bytes.assert_not_called()
        email.send_estimate_approved_email.assert_not_called()

    @pytest.mark.asyncio
    async def test_sends_attachment_when_recipient_has_email(self) -> None:
        pdf = AsyncMock()
        pdf.generate_pdf_bytes = AsyncMock(return_value=b"%PDF-1.4 fake")
        email = MagicMock()
        email.send_estimate_approved_email = MagicMock(
            return_value={"sent": True, "sent_via": "email"}
        )
        svc = _make_service(estimate_pdf_service=pdf, email_service=email)

        est = MagicMock()
        est.id = uuid4()
        est.customer_token = uuid4()
        est.customer = MagicMock()
        est.customer.email = "kirillrakitinsecond@gmail.com"
        est.lead = None

        await svc._send_signed_pdf_email(est)
        pdf.generate_pdf_bytes.assert_awaited_once()
        email.send_estimate_approved_email.assert_called_once()
        kwargs = email.send_estimate_approved_email.call_args.kwargs
        assert kwargs["pdf_bytes"] == b"%PDF-1.4 fake"
