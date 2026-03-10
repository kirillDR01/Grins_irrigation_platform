"""Functional tests for agreement lifecycle.

Tests full agreement lifecycle workflows with mocked repositories,
verifying cross-service interactions as a user would experience them.

Validates: Requirements 40.2
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import stripe

from grins_platform.api.v1.webhooks import StripeWebhookHandler
from grins_platform.models.enums import (
    AgreementPaymentStatus,
    AgreementStatus,
    DisclosureType,
    JobCategory,
    JobStatus,
)
from grins_platform.repositories.agreement_repository import AgreementRepository
from grins_platform.repositories.agreement_tier_repository import (
    AgreementTierRepository,
)
from grins_platform.services.agreement_service import AgreementService
from grins_platform.services.job_generator import JobGenerator

# =============================================================================
# Helpers
# =============================================================================


def _make_tier(**overrides: Any) -> MagicMock:
    tier = MagicMock()
    tier.id = overrides.get("id", uuid4())
    tier.name = overrides.get("name", "Essential")
    tier.slug = overrides.get("slug", "essential")
    tier.package_type = overrides.get("package_type", "residential")
    tier.annual_price = overrides.get("annual_price", Decimal("399.00"))
    tier.is_active = overrides.get("is_active", True)
    tier.stripe_price_id = overrides.get("stripe_price_id", "price_123")
    tier.included_services = overrides.get("included_services", [])
    return tier


def _make_agreement(**overrides: Any) -> MagicMock:
    agr = MagicMock()
    agr.id = overrides.get("id", uuid4())
    agr.customer_id = overrides.get("customer_id", uuid4())
    agr.tier_id = overrides.get("tier_id", uuid4())
    agr.agreement_number = overrides.get("agreement_number", "AGR-2026-001")
    agr.status = overrides.get("status", AgreementStatus.PENDING.value)
    agr.annual_price = overrides.get("annual_price", Decimal("399.00"))
    agr.auto_renew = overrides.get("auto_renew", True)
    agr.stripe_subscription_id = overrides.get(
        "stripe_subscription_id",
        "sub_123",
    )
    agr.stripe_customer_id = overrides.get("stripe_customer_id", "cus_123")
    agr.payment_status = overrides.get("payment_status", "current")
    agr.pause_reason = overrides.get("pause_reason")
    agr.property_id = overrides.get("property_id")
    agr.jobs = overrides.get("jobs", [])
    agr.customer = overrides.get(
        "customer",
        MagicMock(email="test@example.com"),
    )
    agr.tier = overrides.get("tier", _make_tier())
    agr.status_logs = overrides.get("status_logs", [])
    return agr


def _make_job(*, status: str = JobStatus.APPROVED.value) -> MagicMock:
    job = MagicMock()
    job.id = uuid4()
    job.status = status
    job.closed_at = None
    return job


def _make_event(
    event_type: str,
    data_object: dict[str, Any] | None = None,
) -> stripe.Event:
    raw: dict[str, Any] = {
        "id": f"evt_{uuid4().hex[:24]}",
        "type": event_type,
        "object": "event",
        "data": {"object": data_object or {}},
    }
    return stripe.Event.construct_from(raw, key="sk_test")  # type: ignore[no-untyped-call]


def _make_service() -> tuple[AgreementService, AsyncMock, AsyncMock]:
    a_repo = AsyncMock(spec=AgreementRepository)
    t_repo = AsyncMock(spec=AgreementTierRepository)
    svc = AgreementService(
        a_repo,
        t_repo,
        stripe_settings=MagicMock(is_configured=False),
    )
    return svc, a_repo, t_repo


def _make_handler() -> tuple[StripeWebhookHandler, AsyncMock]:
    session = AsyncMock()
    handler = StripeWebhookHandler(session)
    handler.repo = AsyncMock()
    handler.repo.get_by_stripe_event_id.return_value = None
    handler.repo.create_event_record.return_value = MagicMock()
    return handler, session


# =============================================================================
# Full Lifecycle: PENDING → ACTIVE → PENDING_RENEWAL → ACTIVE
# =============================================================================


@pytest.mark.functional
@pytest.mark.asyncio
class TestAgreementFullLifecycle:
    """Test full agreement lifecycle as user would experience.

    Validates: Requirement 40.2
    """

    async def test_pending_to_active_to_renewal_to_active(
        self,
    ) -> None:
        """Full lifecycle through all major states."""
        svc, a_repo, t_repo = _make_service()
        tier = _make_tier()
        t_repo.get_by_id.return_value = tier

        agr_id = uuid4()
        customer_id = uuid4()

        # Create agreement (PENDING)
        agr = _make_agreement(id=agr_id, customer_id=customer_id)
        a_repo.get_next_agreement_number_seq.return_value = 1
        a_repo.create.return_value = agr
        a_repo.add_status_log.return_value = None
        result = await svc.create_agreement(customer_id, tier.id)
        assert result.status == AgreementStatus.PENDING.value

        # PENDING → ACTIVE
        pending = _make_agreement(
            id=agr_id,
            status=AgreementStatus.PENDING.value,
        )
        active = _make_agreement(
            id=agr_id,
            status=AgreementStatus.ACTIVE.value,
        )
        a_repo.get_by_id.return_value = pending
        a_repo.update.return_value = active
        result = await svc.transition_status(
            agr_id,
            AgreementStatus.ACTIVE,
            reason="First invoice paid",
        )
        assert result.status == AgreementStatus.ACTIVE.value

        # ACTIVE → PENDING_RENEWAL
        active2 = _make_agreement(
            id=agr_id,
            status=AgreementStatus.ACTIVE.value,
        )
        pr = _make_agreement(
            id=agr_id,
            status=AgreementStatus.PENDING_RENEWAL.value,
        )
        a_repo.get_by_id.return_value = active2
        a_repo.update.return_value = pr
        result = await svc.transition_status(
            agr_id,
            AgreementStatus.PENDING_RENEWAL,
            reason="Upcoming invoice",
        )
        assert result.status == AgreementStatus.PENDING_RENEWAL.value

        # PENDING_RENEWAL → ACTIVE
        pr2 = _make_agreement(
            id=agr_id,
            status=AgreementStatus.PENDING_RENEWAL.value,
        )
        active3 = _make_agreement(
            id=agr_id,
            status=AgreementStatus.ACTIVE.value,
        )
        a_repo.get_by_id.return_value = pr2
        a_repo.update.return_value = active3
        result = await svc.transition_status(
            agr_id,
            AgreementStatus.ACTIVE,
            reason="Renewal paid",
        )
        assert result.status == AgreementStatus.ACTIVE.value

        # Status logs: create + 3 transitions = 4
        assert a_repo.add_status_log.call_count >= 4


# =============================================================================
# Checkout Webhook → Customer + Agreement + Jobs Pipeline
# =============================================================================


@pytest.mark.functional
@pytest.mark.asyncio
class TestCheckoutWebhookPipeline:
    """Test checkout webhook creates customer, agreement, and jobs.

    Validates: Requirement 40.2
    """

    @patch("grins_platform.api.v1.webhooks.EmailService")
    @patch("grins_platform.api.v1.webhooks.JobGenerator")
    @patch("grins_platform.api.v1.webhooks.ComplianceService")
    @patch("grins_platform.api.v1.webhooks.AgreementService")
    @patch("grins_platform.api.v1.webhooks.AgreementTierRepository")
    @patch("grins_platform.api.v1.webhooks.AgreementRepository")
    @patch("grins_platform.api.v1.webhooks.CustomerService")
    @patch("grins_platform.api.v1.webhooks.CustomerRepository")
    async def test_checkout_creates_customer_agreement_jobs(
        self,
        mock_cust_repo_cls: MagicMock,
        mock_cust_svc_cls: MagicMock,
        _mock_agr_repo_cls: MagicMock,
        mock_tier_repo_cls: MagicMock,
        mock_agr_svc_cls: MagicMock,
        mock_compliance_cls: MagicMock,
        mock_job_gen_cls: MagicMock,
        mock_email_cls: MagicMock,
    ) -> None:
        """Checkout webhook creates full pipeline."""
        handler, _session = _make_handler()

        # Customer repo — no existing customer
        cust_repo = AsyncMock()
        cust_repo.find_by_email.return_value = []
        customer = MagicMock()
        customer.id = uuid4()
        customer.stripe_customer_id = None
        customer.email_opt_in_at = None
        customer.email_opt_in = False
        cust_repo.get_by_id.return_value = customer
        mock_cust_repo_cls.return_value = cust_repo

        # Customer service
        cust_svc = AsyncMock()
        cust_resp = MagicMock()
        cust_resp.id = customer.id
        cust_svc.create_customer.return_value = cust_resp
        mock_cust_svc_cls.return_value = cust_svc

        # Tier repo
        tier_repo = AsyncMock()
        tier = _make_tier()
        tier_repo.get_by_slug_and_type.return_value = tier
        mock_tier_repo_cls.return_value = tier_repo

        # Agreement service
        agr_svc = AsyncMock()
        agreement = _make_agreement(
            customer_id=customer.id,
            tier_id=tier.id,
        )
        agr_svc.create_agreement.return_value = agreement
        mock_agr_svc_cls.return_value = agr_svc

        # Job generator
        job_gen = AsyncMock()
        job_gen.generate_jobs.return_value = [_make_job(), _make_job()]
        mock_job_gen_cls.return_value = job_gen

        # Compliance
        compliance = AsyncMock()
        mock_compliance_cls.return_value = compliance

        # Email
        email_svc = MagicMock()
        email_svc.send_confirmation_email.return_value = {
            "content": "Confirmation",
            "sent_via": "email",
            "sent": True,
        }
        email_svc.send_welcome_email.return_value = {"sent": True}
        mock_email_cls.return_value = email_svc

        event = _make_event(
            "checkout.session.completed",
            {
                "customer_details": {
                    "email": "new@example.com",
                    "name": "Jane Doe",
                    "phone": "6125551234",
                },
                "customer": "cus_new",
                "subscription": "sub_new",
                "metadata": {
                    "consent_token": str(uuid4()),
                    "package_tier": "essential",
                    "package_type": "residential",
                },
            },
        )

        await handler._handle_checkout_completed(event)

        cust_svc.create_customer.assert_called_once()
        agr_svc.create_agreement.assert_called_once()
        job_gen.generate_jobs.assert_called_once()
        assert compliance.create_disclosure.call_count >= 2
        email_svc.send_welcome_email.assert_called_once()
        email_svc.send_confirmation_email.assert_called_once()


# =============================================================================
# Failed Payment Escalation
# =============================================================================


@pytest.mark.functional
@pytest.mark.asyncio
class TestFailedPaymentEscalation:
    """Test ACTIVE → PAST_DUE → PAUSED → CANCELLED escalation.

    Validates: Requirement 40.2
    """

    async def test_escalation_through_all_failure_states(self) -> None:
        """Full escalation path through payment failure states."""
        svc, a_repo, _ = _make_service()
        agr_id = uuid4()
        a_repo.add_status_log.return_value = None

        # ACTIVE → PAST_DUE
        active = _make_agreement(
            id=agr_id,
            status=AgreementStatus.ACTIVE.value,
        )
        past_due = _make_agreement(
            id=agr_id,
            status=AgreementStatus.PAST_DUE.value,
        )
        a_repo.get_by_id.return_value = active
        a_repo.update.return_value = past_due
        result = await svc.transition_status(
            agr_id,
            AgreementStatus.PAST_DUE,
            reason="Payment failed",
        )
        assert result.status == AgreementStatus.PAST_DUE.value

        # PAST_DUE → PAUSED
        pd2 = _make_agreement(
            id=agr_id,
            status=AgreementStatus.PAST_DUE.value,
        )
        paused = _make_agreement(
            id=agr_id,
            status=AgreementStatus.PAUSED.value,
        )
        a_repo.get_by_id.return_value = pd2
        a_repo.update.return_value = paused
        result = await svc.transition_status(
            agr_id,
            AgreementStatus.PAUSED,
            reason="Retries exhausted",
        )
        assert result.status == AgreementStatus.PAUSED.value

        # PAUSED → CANCELLED via cancel_agreement
        paused2 = _make_agreement(
            id=agr_id,
            status=AgreementStatus.PAUSED.value,
            jobs=[
                _make_job(status=JobStatus.APPROVED.value),
                _make_job(status=JobStatus.COMPLETED.value),
            ],
        )
        cancelled = _make_agreement(
            id=agr_id,
            status=AgreementStatus.CANCELLED.value,
        )
        a_repo.get_by_id.return_value = paused2
        a_repo.update.return_value = cancelled
        result = await svc.cancel_agreement(agr_id, reason="No recovery")
        assert result.status == AgreementStatus.CANCELLED.value


# =============================================================================
# Renewal Approval and Rejection
# =============================================================================


@pytest.mark.functional
@pytest.mark.asyncio
class TestRenewalWorkflows:
    """Test renewal approval and rejection workflows.

    Validates: Requirement 40.2
    """

    async def test_renewal_approval_records_fields(self) -> None:
        """Approve renewal records staff and timestamp."""
        svc, a_repo, _ = _make_service()
        staff_id = uuid4()
        agr = _make_agreement(
            status=AgreementStatus.PENDING_RENEWAL.value,
        )
        a_repo.get_by_id.return_value = agr
        a_repo.update.return_value = agr
        a_repo.add_status_log.return_value = None

        await svc.approve_renewal(agr.id, staff_id)

        update_data = a_repo.update.call_args[0][1]
        assert update_data["renewal_approved_by"] == staff_id
        assert "renewal_approved_at" in update_data

    async def test_renewal_rejection_transitions_to_expired(self) -> None:
        """Reject renewal transitions to EXPIRED."""
        svc, a_repo, _ = _make_service()
        staff_id = uuid4()
        agr_id = uuid4()

        # reject_renewal calls get_by_id twice:
        # once in reject_renewal, once in transition_status
        pr_agr = _make_agreement(
            id=agr_id,
            status=AgreementStatus.PENDING_RENEWAL.value,
        )
        expired_agr = _make_agreement(
            id=agr_id,
            status=AgreementStatus.EXPIRED.value,
        )
        a_repo.get_by_id.return_value = pr_agr
        a_repo.update.return_value = expired_agr
        a_repo.add_status_log.return_value = None

        result = await svc.reject_renewal(agr_id, staff_id)
        assert result.status == AgreementStatus.EXPIRED.value


# =============================================================================
# Seasonal Job Generation with Correct Linking
# =============================================================================


@pytest.mark.functional
@pytest.mark.asyncio
class TestSeasonalJobGeneration:
    """Test seasonal job generation links correctly.

    Validates: Requirement 40.2
    """

    async def test_jobs_linked_to_agreement_and_customer(self) -> None:
        """Generated jobs are linked to agreement and customer."""
        session = AsyncMock()
        gen = JobGenerator(session)

        agr = _make_agreement()
        agr.tier.name = "Essential"
        agr.property_id = uuid4()

        jobs = await gen.generate_jobs(agr)

        assert len(jobs) == 2
        for job in jobs:
            assert job.customer_id == agr.customer_id
            assert job.service_agreement_id == agr.id
            assert job.property_id == agr.property_id
            assert job.status == JobStatus.APPROVED.value
            assert job.category == JobCategory.READY_TO_SCHEDULE.value

    async def test_professional_tier_generates_three_jobs(self) -> None:
        """Professional tier generates 3 jobs."""
        session = AsyncMock()
        gen = JobGenerator(session)
        agr = _make_agreement()
        agr.tier.name = "Professional"

        jobs = await gen.generate_jobs(agr)
        assert len(jobs) == 3

    async def test_premium_tier_generates_seven_jobs(self) -> None:
        """Premium tier generates 7 jobs."""
        session = AsyncMock()
        gen = JobGenerator(session)
        agr = _make_agreement()
        agr.tier.name = "Premium"

        jobs = await gen.generate_jobs(agr)
        assert len(jobs) == 7


# =============================================================================
# Portal Payment Recovery: PAUSED → ACTIVE
# =============================================================================


@pytest.mark.functional
@pytest.mark.asyncio
class TestPaymentRecovery:
    """Test payment recovery via subscription.updated webhook.

    Validates: Requirement 40.2
    """

    @patch("grins_platform.api.v1.webhooks.AgreementTierRepository")
    @patch("grins_platform.api.v1.webhooks.AgreementRepository")
    @patch("grins_platform.api.v1.webhooks.AgreementService")
    async def test_paused_to_active_via_subscription_updated(
        self,
        mock_agr_svc_cls: MagicMock,
        mock_agr_repo_cls: MagicMock,
        _mock_tier_repo_cls: MagicMock,
    ) -> None:
        """PAUSED → ACTIVE when Stripe subscription active."""
        handler, _session = _make_handler()

        agr = _make_agreement(
            status=AgreementStatus.PAUSED.value,
            pause_reason="Payment failed",
            payment_status=AgreementPaymentStatus.FAILED.value,
        )
        agr_repo = AsyncMock()
        agr_repo.get_by_stripe_subscription_id.return_value = agr
        agr_repo.update.return_value = agr
        mock_agr_repo_cls.return_value = agr_repo

        agr_svc = AsyncMock()
        mock_agr_svc_cls.return_value = agr_svc

        event = _make_event(
            "customer.subscription.updated",
            {
                "id": "sub_123",
                "status": "active",
                "cancel_at_period_end": False,
            },
        )

        await handler._handle_subscription_updated(event)

        agr_svc.transition_status.assert_called_once()
        assert agr_svc.transition_status.call_args[0][1] == AgreementStatus.ACTIVE

        agr_repo.update.assert_called()
        update_data = agr_repo.update.call_args[0][1]
        assert update_data.get("pause_reason") is None
        assert update_data.get("payment_status") == AgreementPaymentStatus.CURRENT.value


# =============================================================================
# Compliance Email Dispatch Pipeline
# =============================================================================


@pytest.mark.functional
@pytest.mark.asyncio
class TestComplianceEmailPipeline:
    """Test compliance email dispatch through webhook handlers.

    Validates: Requirement 40.2
    """

    @patch("grins_platform.api.v1.webhooks.EmailService")
    @patch("grins_platform.api.v1.webhooks.ComplianceService")
    @patch("grins_platform.api.v1.webhooks.AgreementService")
    @patch("grins_platform.api.v1.webhooks.AgreementTierRepository")
    @patch("grins_platform.api.v1.webhooks.AgreementRepository")
    async def test_upcoming_sends_renewal_notice(
        self,
        mock_agr_repo_cls: MagicMock,
        _mock_tier_repo_cls: MagicMock,
        mock_agr_svc_cls: MagicMock,
        mock_compliance_cls: MagicMock,
        mock_email_cls: MagicMock,
    ) -> None:
        """invoice.upcoming creates disclosure and sends email."""
        handler, _session = _make_handler()

        agr = _make_agreement(status=AgreementStatus.ACTIVE.value)
        agr_repo = AsyncMock()
        agr_repo.get_by_stripe_subscription_id.return_value = agr
        agr_repo.update.return_value = agr
        mock_agr_repo_cls.return_value = agr_repo

        agr_svc = AsyncMock()
        mock_agr_svc_cls.return_value = agr_svc

        compliance = AsyncMock()
        mock_compliance_cls.return_value = compliance

        email_svc = MagicMock()
        email_svc.send_renewal_notice.return_value = {
            "content": "Renewal notice",
            "sent_via": "email",
            "sent": True,
        }
        mock_email_cls.return_value = email_svc

        event = _make_event(
            "invoice.upcoming",
            {"subscription": "sub_123"},
        )
        await handler._handle_invoice_upcoming(event)

        email_svc.send_renewal_notice.assert_called_once()
        compliance.create_disclosure.assert_called_once()
        call_kwargs = compliance.create_disclosure.call_args[1]
        assert call_kwargs["disclosure_type"] == DisclosureType.RENEWAL_NOTICE

    @patch("grins_platform.api.v1.webhooks.EmailService")
    @patch("grins_platform.api.v1.webhooks.ComplianceService")
    @patch("grins_platform.api.v1.webhooks.AgreementService")
    @patch("grins_platform.api.v1.webhooks.AgreementTierRepository")
    @patch("grins_platform.api.v1.webhooks.AgreementRepository")
    async def test_deleted_sends_cancellation_email(
        self,
        mock_agr_repo_cls: MagicMock,
        _mock_tier_repo_cls: MagicMock,
        mock_agr_svc_cls: MagicMock,
        mock_compliance_cls: MagicMock,
        mock_email_cls: MagicMock,
    ) -> None:
        """subscription.deleted sends cancellation email."""
        handler, _session = _make_handler()

        agr = _make_agreement(status=AgreementStatus.ACTIVE.value)
        agr_repo = AsyncMock()
        agr_repo.get_by_stripe_subscription_id.return_value = agr
        mock_agr_repo_cls.return_value = agr_repo

        agr_svc = AsyncMock()
        cancelled_agr = _make_agreement(
            id=agr.id,
            status=AgreementStatus.CANCELLED.value,
        )
        agr_svc.cancel_agreement.return_value = cancelled_agr
        mock_agr_svc_cls.return_value = agr_svc

        compliance = AsyncMock()
        mock_compliance_cls.return_value = compliance

        email_svc = MagicMock()
        email_svc.send_cancellation_confirmation.return_value = {
            "content": "Cancellation",
            "sent_via": "email",
            "sent": True,
        }
        mock_email_cls.return_value = email_svc

        event = _make_event(
            "customer.subscription.deleted",
            {
                "id": "sub_123",
                "cancellation_details": {
                    "reason": "Customer requested",
                },
            },
        )
        await handler._handle_subscription_deleted(event)

        email_svc.send_cancellation_confirmation.assert_called_once()
        compliance.create_disclosure.assert_called_once()
        call_kwargs = compliance.create_disclosure.call_args[1]
        assert call_kwargs["disclosure_type"] == DisclosureType.CANCELLATION_CONF
