"""Integration tests for agreement flow preservation.

Regression test suite verifying the complete service agreement flow is
preserved and unmodified by any CRM gap closure changes. Tests the full
pipeline: tier retrieval → checkout session creation → webhook processing →
agreement record creation → job generation → job-customer linkage.

**Property 64: Agreement flow preservation invariant**

Validates: Requirements 68.1, 68.2, 68.3, 68.4, 68.5, 68.6, 68.7, 68.8, 68.10
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import stripe

from grins_platform.api.v1.webhooks import StripeWebhookHandler
from grins_platform.models.enums import (
    VALID_AGREEMENT_STATUS_TRANSITIONS,
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
    """Build a mock agreement tier."""
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
    """Build a mock service agreement."""
    agr = MagicMock()
    agr.id = overrides.get("id", uuid4())
    agr.customer_id = overrides.get("customer_id", uuid4())
    agr.tier_id = overrides.get("tier_id", uuid4())
    agr.property_id = overrides.get("property_id", uuid4())
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
    agr.jobs = overrides.get("jobs", [])
    agr.customer = overrides.get(
        "customer",
        MagicMock(email="test@example.com"),
    )
    agr.tier = overrides.get("tier", _make_tier())
    agr.status_logs = overrides.get("status_logs", [])
    return agr


def _make_job(
    *,
    customer_id: Any = None,
    property_id: Any = None,
    service_agreement_id: Any = None,
    status: str = JobStatus.TO_BE_SCHEDULED.value,
    category: str = JobCategory.READY_TO_SCHEDULE.value,
) -> MagicMock:
    """Build a mock job with agreement-expected fields."""
    job = MagicMock()
    job.id = uuid4()
    job.customer_id = customer_id or uuid4()
    job.property_id = property_id or uuid4()
    job.service_agreement_id = service_agreement_id or uuid4()
    job.status = status
    job.category = category
    job.target_start_date = date(2026, 4, 1)
    job.target_end_date = date(2026, 4, 30)
    job.requested_at = datetime.now(timezone.utc)
    job.description = "Spring system activation and inspection"
    job.job_type = "spring_startup"
    return job


def _make_service() -> tuple[AgreementService, AsyncMock, AsyncMock]:
    """Build AgreementService with mocked repositories."""
    a_repo = AsyncMock(spec=AgreementRepository)
    t_repo = AsyncMock(spec=AgreementTierRepository)
    svc = AgreementService(
        a_repo,
        t_repo,
        stripe_settings=MagicMock(is_configured=False),
    )
    return svc, a_repo, t_repo


def _make_handler() -> tuple[StripeWebhookHandler, AsyncMock]:
    """Build StripeWebhookHandler with mocked session."""
    session = AsyncMock()
    handler = StripeWebhookHandler(session)
    handler.repo = AsyncMock()
    handler.repo.get_by_stripe_event_id.return_value = None
    handler.repo.create_event_record.return_value = MagicMock()
    return handler, session


def _make_event(
    event_type: str,
    data_object: dict[str, Any] | None = None,
) -> stripe.Event:
    """Build a mock Stripe event."""
    raw: dict[str, Any] = {
        "id": f"evt_{uuid4().hex[:24]}",
        "type": event_type,
        "object": "event",
        "data": {"object": data_object or {}},
    }
    return stripe.Event.construct_from(raw, key="sk_test")  # type: ignore[no-untyped-call]


# =============================================================================
# 1. TestAgreementFlowPreservation — End-to-end flow
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
class TestAgreementFlowPreservation:
    """End-to-end agreement flow: create → PENDING → ACTIVE → jobs generated.

    Validates: Requirements 68.1, 68.2, 68.3, 68.6
    """

    async def test_agreement_creation_works_with_existing_service(
        self,
    ) -> None:
        """Create agreement → verify PENDING status and correct fields."""
        svc, a_repo, t_repo = _make_service()
        tier = _make_tier()
        t_repo.get_by_id.return_value = tier

        customer_id = uuid4()
        agr = _make_agreement(customer_id=customer_id, tier_id=tier.id)
        a_repo.get_next_agreement_number_seq.return_value = 1
        a_repo.create.return_value = agr
        a_repo.add_status_log.return_value = None

        result = await svc.create_agreement(customer_id, tier.id)

        assert result.status == AgreementStatus.PENDING.value
        a_repo.create.assert_called_once()
        a_repo.add_status_log.assert_called_once()

    async def test_agreement_activation_works_with_existing_transition(
        self,
    ) -> None:
        """PENDING → ACTIVE transition preserves agreement flow."""
        svc, a_repo, _t_repo = _make_service()
        agr_id = uuid4()

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
        a_repo.add_status_log.return_value = None

        result = await svc.transition_status(
            agr_id,
            AgreementStatus.ACTIVE,
            reason="First invoice paid",
        )

        assert result.status == AgreementStatus.ACTIVE.value

    async def test_full_flow_create_activate_generate_jobs_works_with_existing_pipeline(
        self,
    ) -> None:
        """Full pipeline: create agreement → activate → generate jobs."""
        svc, a_repo, t_repo = _make_service()
        tier = _make_tier(name="Professional")
        t_repo.get_by_id.return_value = tier

        customer_id = uuid4()
        property_id = uuid4()
        agr_id = uuid4()

        # Step 1: Create agreement
        pending_agr = _make_agreement(
            id=agr_id,
            customer_id=customer_id,
            property_id=property_id,
            tier_id=tier.id,
            tier=tier,
        )
        a_repo.get_next_agreement_number_seq.return_value = 1
        a_repo.create.return_value = pending_agr
        a_repo.add_status_log.return_value = None

        created = await svc.create_agreement(customer_id, tier.id)
        assert created.status == AgreementStatus.PENDING.value

        # Step 2: Activate
        active_agr = _make_agreement(
            id=agr_id,
            customer_id=customer_id,
            property_id=property_id,
            status=AgreementStatus.ACTIVE.value,
            tier=tier,
        )
        a_repo.get_by_id.return_value = pending_agr
        a_repo.update.return_value = active_agr

        activated = await svc.transition_status(
            agr_id,
            AgreementStatus.ACTIVE,
            reason="Payment confirmed",
        )
        assert activated.status == AgreementStatus.ACTIVE.value

        # Step 3: Generate jobs
        session = AsyncMock()
        gen = JobGenerator(session)
        jobs = await gen.generate_jobs(active_agr)

        assert len(jobs) == 3  # Professional = 3 jobs
        for job in jobs:
            assert job.customer_id == customer_id
            assert job.service_agreement_id == agr_id
            assert job.property_id == property_id
            assert job.status == JobStatus.TO_BE_SCHEDULED.value
            assert job.category == JobCategory.READY_TO_SCHEDULE.value


# =============================================================================
# 2. TestCheckoutWebhookPreservation — Webhook pipeline
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
class TestCheckoutWebhookPreservation:
    """Checkout webhook creates customer + agreement + jobs pipeline.

    Validates: Requirements 68.1, 68.4, 68.6
    """

    @patch("grins_platform.api.v1.webhooks.EmailService")
    @patch("grins_platform.api.v1.webhooks.JobGenerator")
    @patch("grins_platform.api.v1.webhooks.ComplianceService")
    @patch("grins_platform.api.v1.webhooks.AgreementService")
    @patch("grins_platform.api.v1.webhooks.AgreementTierRepository")
    @patch("grins_platform.api.v1.webhooks.AgreementRepository")
    @patch("grins_platform.api.v1.webhooks.CustomerService")
    @patch("grins_platform.api.v1.webhooks.CustomerRepository")
    async def test_checkout_completed_works_with_existing_webhook_handler(
        self,
        mock_cust_repo_cls: MagicMock,
        mock_cust_svc_cls: MagicMock,
        mock_agr_repo_cls: MagicMock,
        mock_tier_repo_cls: MagicMock,
        mock_agr_svc_cls: MagicMock,
        mock_compliance_cls: MagicMock,
        mock_job_gen_cls: MagicMock,
        mock_email_cls: MagicMock,
    ) -> None:
        """checkout.session.completed creates full pipeline unchanged."""
        handler, _session = _make_handler()

        # Customer repo — no existing customer by email or phone
        cust_repo = AsyncMock()
        cust_repo.find_by_email.return_value = []
        cust_repo.find_by_phone.return_value = None
        customer = MagicMock()
        customer.id = uuid4()
        customer.stripe_customer_id = None
        customer.email_opt_in_at = None
        customer.email_opt_in = False
        customer.email = None
        cust_repo.get_by_id.return_value = customer
        mock_cust_repo_cls.return_value = cust_repo

        # Customer service
        cust_svc = AsyncMock()
        cust_resp = MagicMock()
        cust_resp.id = customer.id
        cust_svc.create_customer.return_value = cust_resp
        mock_cust_svc_cls.return_value = cust_svc

        # Agreement repo
        agr_repo = AsyncMock()
        mock_agr_repo_cls.return_value = agr_repo

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
        job_gen.generate_jobs.return_value = [
            _make_job(
                customer_id=customer.id,
                service_agreement_id=agreement.id,
            ),
            _make_job(
                customer_id=customer.id,
                service_agreement_id=agreement.id,
            ),
        ]
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

        # Verify full pipeline executed
        cust_svc.create_customer.assert_called_once()
        agr_svc.create_agreement.assert_called_once()
        job_gen.generate_jobs.assert_called_once()
        assert compliance.create_disclosure.call_count >= 2
        email_svc.send_welcome_email.assert_called_once()
        email_svc.send_confirmation_email.assert_called_once()

    @patch("grins_platform.api.v1.webhooks.EmailService")
    @patch("grins_platform.api.v1.webhooks.ComplianceService")
    @patch("grins_platform.api.v1.webhooks.AgreementService")
    @patch("grins_platform.api.v1.webhooks.AgreementTierRepository")
    @patch("grins_platform.api.v1.webhooks.AgreementRepository")
    async def test_invoice_upcoming_works_with_existing_webhook_handler(
        self,
        mock_agr_repo_cls: MagicMock,
        _mock_tier_repo_cls: MagicMock,
        mock_agr_svc_cls: MagicMock,
        mock_compliance_cls: MagicMock,
        mock_email_cls: MagicMock,
    ) -> None:
        """invoice.upcoming webhook still triggers renewal notice."""
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
    async def test_subscription_deleted_works_with_existing_webhook_handler(
        self,
        mock_agr_repo_cls: MagicMock,
        _mock_tier_repo_cls: MagicMock,
        mock_agr_svc_cls: MagicMock,
        mock_compliance_cls: MagicMock,
        mock_email_cls: MagicMock,
    ) -> None:
        """subscription.deleted webhook still cancels agreement."""
        handler, _session = _make_handler()

        agr = _make_agreement(status=AgreementStatus.ACTIVE.value)
        agr_repo = AsyncMock()
        agr_repo.get_by_stripe_subscription_id.return_value = agr
        mock_agr_repo_cls.return_value = agr_repo

        agr_svc = AsyncMock()
        cancelled = _make_agreement(
            id=agr.id,
            status=AgreementStatus.CANCELLED.value,
        )
        agr_svc.cancel_agreement.return_value = cancelled
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
                "cancellation_details": {"reason": "Customer requested"},
            },
        )
        await handler._handle_subscription_deleted(event)

        email_svc.send_cancellation_confirmation.assert_called_once()
        compliance.create_disclosure.assert_called_once()
        call_kwargs = compliance.create_disclosure.call_args[1]
        assert call_kwargs["disclosure_type"] == DisclosureType.CANCELLATION_CONF


# =============================================================================
# 3. TestJobGenerationPreservation — Tier-based job counts
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
class TestJobGenerationPreservation:
    """Job generation per tier: Essential=2, Professional=3, Premium=7.

    Validates: Requirements 68.3, 68.6, 68.10
    """

    async def test_essential_tier_works_with_existing_job_generator(
        self,
    ) -> None:
        """Essential tier generates exactly 2 jobs with correct linkage."""
        session = AsyncMock()
        gen = JobGenerator(session)

        customer_id = uuid4()
        property_id = uuid4()
        agr_id = uuid4()
        agr = _make_agreement(
            id=agr_id,
            customer_id=customer_id,
            property_id=property_id,
        )
        agr.tier.name = "Essential"
        agr.tier.slug = "essential"

        jobs = await gen.generate_jobs(agr)

        assert len(jobs) == 2
        for job in jobs:
            assert job.customer_id == customer_id
            assert job.service_agreement_id == agr_id
            assert job.property_id == property_id
            assert job.status == JobStatus.TO_BE_SCHEDULED.value
            assert job.category == JobCategory.READY_TO_SCHEDULE.value

        # Verify job types
        job_types = [j.job_type for j in jobs]
        assert "spring_startup" in job_types
        assert "fall_winterization" in job_types

    async def test_professional_tier_works_with_existing_job_generator(
        self,
    ) -> None:
        """Professional tier generates exactly 3 jobs."""
        session = AsyncMock()
        gen = JobGenerator(session)

        customer_id = uuid4()
        property_id = uuid4()
        agr_id = uuid4()
        agr = _make_agreement(
            id=agr_id,
            customer_id=customer_id,
            property_id=property_id,
        )
        agr.tier.name = "Professional"
        agr.tier.slug = "professional"

        jobs = await gen.generate_jobs(agr)

        assert len(jobs) == 3
        job_types = [j.job_type for j in jobs]
        assert "spring_startup" in job_types
        assert "mid_season_inspection" in job_types
        assert "fall_winterization" in job_types

        for job in jobs:
            assert job.customer_id == customer_id
            assert job.service_agreement_id == agr_id
            assert job.status == JobStatus.TO_BE_SCHEDULED.value
            assert job.category == JobCategory.READY_TO_SCHEDULE.value

    async def test_premium_tier_works_with_existing_job_generator(
        self,
    ) -> None:
        """Premium tier generates exactly 7 jobs."""
        session = AsyncMock()
        gen = JobGenerator(session)

        customer_id = uuid4()
        property_id = uuid4()
        agr_id = uuid4()
        agr = _make_agreement(
            id=agr_id,
            customer_id=customer_id,
            property_id=property_id,
        )
        agr.tier.name = "Premium"
        agr.tier.slug = "premium"

        jobs = await gen.generate_jobs(agr)

        assert len(jobs) == 7
        job_types = [j.job_type for j in jobs]
        assert job_types.count("monthly_visit") == 5
        assert "spring_startup" in job_types
        assert "fall_winterization" in job_types

        for job in jobs:
            assert job.customer_id == customer_id
            assert job.service_agreement_id == agr_id
            assert job.property_id == property_id
            assert job.status == JobStatus.TO_BE_SCHEDULED.value
            assert job.category == JobCategory.READY_TO_SCHEDULE.value

    async def test_job_target_dates_works_with_existing_job_generator(
        self,
    ) -> None:
        """Generated jobs have correct target date ranges per season."""
        session = AsyncMock()
        gen = JobGenerator(session)

        agr = _make_agreement()
        agr.tier.name = "Essential"
        agr.tier.slug = "essential"

        jobs = await gen.generate_jobs(agr)

        spring = next(j for j in jobs if j.job_type == "spring_startup")
        assert spring.target_start_date.month == 4
        assert spring.target_end_date.month == 4

        fall = next(j for j in jobs if j.job_type == "fall_winterization")
        assert fall.target_start_date.month == 10
        assert fall.target_end_date.month == 10


# =============================================================================
# 4. TestAgreementStatusTransitionsPreservation — All valid transitions
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
class TestAgreementStatusTransitionsPreservation:
    """All valid agreement status transitions still work.

    Validates: Requirements 68.1, 68.2, 68.5
    """

    async def test_pending_to_active_works_with_existing_transitions(
        self,
    ) -> None:
        """PENDING → ACTIVE transition preserved."""
        svc, a_repo, _ = _make_service()
        agr_id = uuid4()
        a_repo.get_by_id.return_value = _make_agreement(
            id=agr_id,
            status=AgreementStatus.PENDING.value,
        )
        a_repo.update.return_value = _make_agreement(
            id=agr_id,
            status=AgreementStatus.ACTIVE.value,
        )
        a_repo.add_status_log.return_value = None

        result = await svc.transition_status(
            agr_id,
            AgreementStatus.ACTIVE,
            reason="Payment confirmed",
        )
        assert result.status == AgreementStatus.ACTIVE.value

    async def test_active_to_past_due_works_with_existing_transitions(
        self,
    ) -> None:
        """ACTIVE → PAST_DUE transition preserved."""
        svc, a_repo, _ = _make_service()
        agr_id = uuid4()
        a_repo.get_by_id.return_value = _make_agreement(
            id=agr_id,
            status=AgreementStatus.ACTIVE.value,
        )
        a_repo.update.return_value = _make_agreement(
            id=agr_id,
            status=AgreementStatus.PAST_DUE.value,
        )
        a_repo.add_status_log.return_value = None

        result = await svc.transition_status(
            agr_id,
            AgreementStatus.PAST_DUE,
            reason="Payment failed",
        )
        assert result.status == AgreementStatus.PAST_DUE.value

    async def test_past_due_to_paused_works_with_existing_transitions(
        self,
    ) -> None:
        """PAST_DUE → PAUSED transition preserved."""
        svc, a_repo, _ = _make_service()
        agr_id = uuid4()
        a_repo.get_by_id.return_value = _make_agreement(
            id=agr_id,
            status=AgreementStatus.PAST_DUE.value,
        )
        a_repo.update.return_value = _make_agreement(
            id=agr_id,
            status=AgreementStatus.PAUSED.value,
        )
        a_repo.add_status_log.return_value = None

        result = await svc.transition_status(
            agr_id,
            AgreementStatus.PAUSED,
            reason="Retries exhausted",
        )
        assert result.status == AgreementStatus.PAUSED.value

    async def test_paused_to_cancelled_works_with_existing_transitions(
        self,
    ) -> None:
        """PAUSED → CANCELLED via cancel_agreement preserved."""
        svc, a_repo, _ = _make_service()
        agr_id = uuid4()
        paused = _make_agreement(
            id=agr_id,
            status=AgreementStatus.PAUSED.value,
            jobs=[
                _make_job(status=JobStatus.TO_BE_SCHEDULED.value),
                _make_job(status=JobStatus.COMPLETED.value),
            ],
        )
        cancelled = _make_agreement(
            id=agr_id,
            status=AgreementStatus.CANCELLED.value,
        )
        a_repo.get_by_id.return_value = paused
        a_repo.update.return_value = cancelled
        a_repo.add_status_log.return_value = None

        result = await svc.cancel_agreement(agr_id, reason="No recovery")
        assert result.status == AgreementStatus.CANCELLED.value

    async def test_active_to_pending_renewal_works_with_existing_transitions(
        self,
    ) -> None:
        """ACTIVE → PENDING_RENEWAL transition preserved."""
        svc, a_repo, _ = _make_service()
        agr_id = uuid4()
        a_repo.get_by_id.return_value = _make_agreement(
            id=agr_id,
            status=AgreementStatus.ACTIVE.value,
        )
        a_repo.update.return_value = _make_agreement(
            id=agr_id,
            status=AgreementStatus.PENDING_RENEWAL.value,
        )
        a_repo.add_status_log.return_value = None

        result = await svc.transition_status(
            agr_id,
            AgreementStatus.PENDING_RENEWAL,
            reason="Upcoming invoice",
        )
        assert result.status == AgreementStatus.PENDING_RENEWAL.value

    async def test_pending_renewal_to_active_works_with_existing_transitions(
        self,
    ) -> None:
        """PENDING_RENEWAL → ACTIVE transition preserved."""
        svc, a_repo, _ = _make_service()
        agr_id = uuid4()
        a_repo.get_by_id.return_value = _make_agreement(
            id=agr_id,
            status=AgreementStatus.PENDING_RENEWAL.value,
        )
        a_repo.update.return_value = _make_agreement(
            id=agr_id,
            status=AgreementStatus.ACTIVE.value,
        )
        a_repo.add_status_log.return_value = None

        result = await svc.transition_status(
            agr_id,
            AgreementStatus.ACTIVE,
            reason="Renewal paid",
        )
        assert result.status == AgreementStatus.ACTIVE.value

    async def test_valid_transitions_map_works_with_existing_enums(
        self,
    ) -> None:
        """VALID_AGREEMENT_STATUS_TRANSITIONS map is unchanged."""
        # Verify the transition map contains all expected entries
        assert AgreementStatus.PENDING in VALID_AGREEMENT_STATUS_TRANSITIONS
        assert AgreementStatus.ACTIVE in VALID_AGREEMENT_STATUS_TRANSITIONS
        assert AgreementStatus.PAST_DUE in VALID_AGREEMENT_STATUS_TRANSITIONS
        assert AgreementStatus.PAUSED in VALID_AGREEMENT_STATUS_TRANSITIONS
        assert AgreementStatus.PENDING_RENEWAL in VALID_AGREEMENT_STATUS_TRANSITIONS
        assert AgreementStatus.CANCELLED in VALID_AGREEMENT_STATUS_TRANSITIONS
        assert AgreementStatus.EXPIRED in VALID_AGREEMENT_STATUS_TRANSITIONS

        # Verify key transitions exist
        pending_targets = VALID_AGREEMENT_STATUS_TRANSITIONS[AgreementStatus.PENDING]
        assert AgreementStatus.ACTIVE in pending_targets
        assert AgreementStatus.CANCELLED in pending_targets

        active_targets = VALID_AGREEMENT_STATUS_TRANSITIONS[AgreementStatus.ACTIVE]
        assert AgreementStatus.PAST_DUE in active_targets
        assert AgreementStatus.PENDING_RENEWAL in active_targets
        assert AgreementStatus.CANCELLED in active_targets

        # CANCELLED is terminal
        assert (
            len(
                VALID_AGREEMENT_STATUS_TRANSITIONS[AgreementStatus.CANCELLED],
            )
            == 0
        )

    async def test_subscription_updated_recovery_works_with_existing_handler(
        self,
    ) -> None:
        """PAUSED → ACTIVE via subscription.updated webhook preserved."""
        handler, _session = _make_handler()

        with (
            patch(
                "grins_platform.api.v1.webhooks.AgreementRepository",
            ) as mock_agr_repo_cls,
            patch(
                "grins_platform.api.v1.webhooks.AgreementTierRepository",
            ),
            patch(
                "grins_platform.api.v1.webhooks.AgreementService",
            ) as mock_agr_svc_cls,
        ):
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
            assert (
                update_data.get("payment_status")
                == AgreementPaymentStatus.CURRENT.value
            )


# =============================================================================
# 5. TestAgreementJobListViewPreservation — Job fields for display
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
class TestAgreementJobListViewPreservation:
    """Agreement-generated jobs have all expected fields for Job_List_View.

    Validates: Requirements 68.3, 68.10
    """

    async def test_essential_jobs_have_all_expected_fields_for_existing_list_view(
        self,
    ) -> None:
        """Essential tier jobs have correct status, category, and linkage."""
        session = AsyncMock()
        gen = JobGenerator(session)

        customer_id = uuid4()
        property_id = uuid4()
        agr_id = uuid4()
        agr = _make_agreement(
            id=agr_id,
            customer_id=customer_id,
            property_id=property_id,
        )
        agr.tier.name = "Essential"
        agr.tier.slug = "essential"

        jobs = await gen.generate_jobs(agr)

        for job in jobs:
            # Status and category for Job_List_View
            assert job.status == JobStatus.TO_BE_SCHEDULED.value
            assert job.category == JobCategory.READY_TO_SCHEDULE.value

            # Customer and agreement linkage
            assert job.customer_id == customer_id
            assert job.service_agreement_id == agr_id
            assert job.property_id == property_id

            # Target dates present
            assert isinstance(job.target_start_date, date)
            assert isinstance(job.target_end_date, date)

            # Request timestamp
            assert job.requested_at is not None

            # Description present
            assert job.description is not None
            assert len(job.description) > 0

    async def test_premium_jobs_have_correct_monthly_schedule_for_existing_list_view(
        self,
    ) -> None:
        """Premium tier monthly visits span May through September."""
        session = AsyncMock()
        gen = JobGenerator(session)

        agr = _make_agreement()
        agr.tier.name = "Premium"
        agr.tier.slug = "premium"

        jobs = await gen.generate_jobs(agr)

        monthly_jobs = [j for j in jobs if j.job_type == "monthly_visit"]
        assert len(monthly_jobs) == 5

        monthly_months = sorted(
            [j.target_start_date.month for j in monthly_jobs],
        )
        assert monthly_months == [5, 6, 7, 8, 9]

    async def test_all_tiers_produce_approved_ready_to_schedule_for_existing_list_view(
        self,
    ) -> None:
        """Every tier produces jobs with APPROVED status and READY_TO_SCHEDULE."""
        session = AsyncMock()
        gen = JobGenerator(session)

        for tier_name, expected_count in [
            ("Essential", 2),
            ("Professional", 3),
            ("Premium", 7),
        ]:
            agr = _make_agreement()
            agr.tier.name = tier_name
            agr.tier.slug = tier_name.lower()

            jobs = await gen.generate_jobs(agr)
            assert len(jobs) == expected_count, (
                f"{tier_name} should produce {expected_count} jobs"
            )

            for job in jobs:
                assert job.status == JobStatus.TO_BE_SCHEDULED.value, (
                    f"{tier_name} job should be APPROVED"
                )
                assert job.category == JobCategory.READY_TO_SCHEDULE.value, (
                    f"{tier_name} job should be READY_TO_SCHEDULE"
                )
