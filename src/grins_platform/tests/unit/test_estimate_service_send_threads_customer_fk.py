"""Bug #1 — estimate-service SMS sites must thread customer/lead FKs.

The four ``send_automated_message`` call sites in ``estimate_service.py``
(customer branch, lead branch, internal-staff branch, follow-up
reminder branch) must pass the right FK keyword so the
``SentMessage`` audit row satisfies ``ck_sent_messages_recipient``
without poisoning the transaction.

These tests pin the kwargs each branch threads — regression guards for
Bug #1 (master-plan-run-findings 2026-05-04).

Validates: ``.agents/plans/master-plan-run-findings-bug-resolution-2026-05-04.md``
Phase 3 / Task 3.8.
"""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from grins_platform.services.estimate_service import EstimateService

pytestmark = pytest.mark.unit


def _make_service(sms_service: AsyncMock) -> EstimateService:
    repo = AsyncMock()
    repo.session = AsyncMock()
    return EstimateService(
        estimate_repository=repo,
        portal_base_url="http://localhost:5173",
        email_service=None,
        sms_service=sms_service,
    )


class TestEstimateServiceSendThreadsFK:
    """``send_estimate`` and follow-up sites must thread the right FK."""

    @pytest.mark.asyncio
    async def test_customer_branch_threads_customer_id(self) -> None:
        sms = AsyncMock()
        sms.send_automated_message = AsyncMock(
            return_value={"success": True, "message_id": "m1"},
        )
        svc = _make_service(sms_service=sms)

        customer_id = uuid4()
        estimate_id = uuid4()
        customer = SimpleNamespace(
            id=customer_id,
            phone="+19527373312",
            email="kirillrakitinsecond@gmail.com",
        )
        estimate = SimpleNamespace(
            id=estimate_id,
            status="draft",
            customer=customer,
            customer_id=customer_id,
            lead=None,
            lead_id=None,
            customer_token=uuid4(),
        )
        svc.repo.get_by_id = AsyncMock(return_value=estimate)
        svc.repo.update = AsyncMock(return_value=estimate)

        await svc.send_estimate(estimate_id)

        sms.send_automated_message.assert_awaited()
        kwargs = sms.send_automated_message.await_args.kwargs
        assert kwargs["customer_id"] == customer_id
        assert "lead_id" not in kwargs or kwargs.get("lead_id") is None

    @pytest.mark.asyncio
    async def test_lead_branch_threads_lead_id(self) -> None:
        sms = AsyncMock()
        sms.send_automated_message = AsyncMock(
            return_value={"success": True, "message_id": "m1"},
        )
        svc = _make_service(sms_service=sms)

        lead_id = uuid4()
        estimate_id = uuid4()
        lead = SimpleNamespace(
            id=lead_id,
            phone="+19527373312",
            email=None,
            name="Jane Doe",
        )
        estimate = SimpleNamespace(
            id=estimate_id,
            status="draft",
            customer=None,
            customer_id=None,
            lead=lead,
            lead_id=lead_id,
            customer_token=uuid4(),
        )
        svc.repo.get_by_id = AsyncMock(return_value=estimate)
        svc.repo.update = AsyncMock(return_value=estimate)

        await svc.send_estimate(estimate_id)

        sms.send_automated_message.assert_awaited()
        kwargs = sms.send_automated_message.await_args.kwargs
        assert kwargs["lead_id"] == lead_id
        assert "customer_id" not in kwargs or kwargs.get("customer_id") is None

    @pytest.mark.asyncio
    async def test_internal_decision_branch_threads_is_internal(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("INTERNAL_NOTIFICATION_PHONE", "+19527373312")
        sms = AsyncMock()
        sms.send_automated_message = AsyncMock(
            return_value={"success": True, "internal": True},
        )
        svc = _make_service(sms_service=sms)

        estimate = MagicMock()
        estimate.id = uuid4()
        estimate.total = Decimal("499.00")
        estimate.rejected_reason = None
        estimate.customer = MagicMock()
        estimate.customer.full_name = "Jane Doe"
        estimate.lead = None

        await svc._notify_internal_decision(estimate, "approved")

        sms.send_automated_message.assert_awaited_once()
        kwargs = sms.send_automated_message.await_args.kwargs
        assert kwargs["is_internal"] is True


class TestGetContactPhoneWithKeys:
    """The new helper for the follow-up branch returns FK alongside phone."""

    def test_customer_takes_precedence_over_lead(self) -> None:
        cid = uuid4()
        lid = uuid4()
        estimate = SimpleNamespace(
            customer=SimpleNamespace(id=cid, phone="+19527373312"),
            lead=SimpleNamespace(id=lid, phone="+19528888888"),
        )
        phone, customer_id, lead_id = (
            EstimateService._get_contact_phone_with_keys(estimate)
        )
        assert phone == "+19527373312"
        assert customer_id == cid
        assert lead_id is None

    def test_lead_used_when_no_customer_phone(self) -> None:
        lid = uuid4()
        estimate = SimpleNamespace(
            customer=None,
            lead=SimpleNamespace(id=lid, phone="+19528888888"),
        )
        phone, customer_id, lead_id = (
            EstimateService._get_contact_phone_with_keys(estimate)
        )
        assert phone == "+19528888888"
        assert customer_id is None
        assert lead_id == lid

    def test_returns_all_none_when_no_phone(self) -> None:
        estimate = SimpleNamespace(customer=None, lead=None)
        result = EstimateService._get_contact_phone_with_keys(estimate)
        assert result == (None, None, None)
