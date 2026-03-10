"""Unit tests for all Stripe webhook event handlers.

Tests checkout.session.completed, invoice.paid, invoice.payment_failed,
invoice.upcoming, customer.subscription.updated, customer.subscription.deleted.

Validates: Requirements 8.1-8.7, 10.1-10.3, 11.1-11.2, 12.1-12.5,
13.1-13.3, 14.1-14.4, 40.1
"""

from __future__ import annotations

from datetime import datetime, timezone
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
)

# =============================================================================
# Helpers
# =============================================================================


def _make_event(
    event_type: str,
    data_object: dict[str, Any] | None = None,
    event_id: str | None = None,
) -> stripe.Event:
    """Build a Stripe Event with custom data.object."""
    eid = event_id or f"evt_{uuid4().hex[:24]}"
    raw: dict[str, Any] = {
        "id": eid,
        "type": event_type,
        "object": "event",
        "data": {"object": data_object or {}},
    }
    return stripe.Event.construct_from(raw, key="sk_test")  # type: ignore[no-untyped-call]


def _make_agreement(**overrides: Any) -> MagicMock:
    """Build a mock ServiceAgreement."""
    agr = MagicMock()
    agr.id = overrides.get("id", uuid4())
    agr.customer_id = overrides.get("customer_id", uuid4())
    agr.tier_id = overrides.get("tier_id", uuid4())
    agr.agreement_number = overrides.get("agreement_number", "AGR-2026-001")
    agr.status = overrides.get("status", AgreementStatus.ACTIVE.value)
    agr.annual_price = overrides.get("annual_price", Decimal("599.00"))
    agr.auto_renew = overrides.get("auto_renew", True)
    agr.stripe_subscription_id = overrides.get("stripe_subscription_id", "sub_123")
    agr.payment_status = overrides.get("payment_status", "current")
    agr.pause_reason = overrides.get("pause_reason")
    agr.jobs = overrides.get("jobs", [])
    agr.customer = overrides.get("customer", MagicMock())
    return agr


def _make_handler() -> tuple[StripeWebhookHandler, AsyncMock]:
    """Create handler with mocked session and repo (event already new)."""
    session = AsyncMock()
    handler = StripeWebhookHandler(session)
    handler.repo = AsyncMock()
    handler.repo.get_by_stripe_event_id.return_value = None
    handler.repo.create_event_record.return_value = MagicMock()
    return handler, session


# =============================================================================
# checkout.session.completed
# =============================================================================


class TestCheckoutSessionCompleted:
    """Tests for _handle_checkout_completed."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("grins_platform.api.v1.webhooks.EmailService")
    @patch("grins_platform.api.v1.webhooks.JobGenerator")
    @patch("grins_platform.api.v1.webhooks.ComplianceService")
    @patch("grins_platform.api.v1.webhooks.AgreementService")
    @patch("grins_platform.api.v1.webhooks.AgreementTierRepository")
    @patch("grins_platform.api.v1.webhooks.AgreementRepository")
    @patch("grins_platform.api.v1.webhooks.CustomerService")
    @patch("grins_platform.api.v1.webhooks.CustomerRepository")
    async def test_new_customer_created_when_no_match(
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
        """New customer is created when email doesn't match existing."""
        handler, _session = _make_handler()

        # Customer repo: no existing customer
        cust_repo = AsyncMock()
        cust_repo.find_by_email.return_value = []
        new_customer = MagicMock()
        new_customer.id = uuid4()
        new_customer.stripe_customer_id = None
        new_customer.email_opt_in_at = None
        new_customer.email_opt_in = False
        cust_repo.get_by_id.return_value = new_customer
        mock_cust_repo_cls.return_value = cust_repo

        # Customer service
        cust_svc = AsyncMock()
        cust_resp = MagicMock()
        cust_resp.id = new_customer.id
        cust_svc.create_customer.return_value = cust_resp
        mock_cust_svc_cls.return_value = cust_svc

        # Tier repo
        tier = MagicMock()
        tier.id = uuid4()
        tier.name = "Essential"
        tier.annual_price = Decimal("299.00")
        tier.is_active = True
        tier_repo = AsyncMock()
        tier_repo.get_by_slug_and_type.return_value = tier
        mock_tier_repo_cls.return_value = tier_repo

        # Agreement service
        agreement = _make_agreement(status=AgreementStatus.PENDING.value)
        agr_svc = AsyncMock()
        agr_svc.create_agreement.return_value = agreement
        mock_agr_svc_cls.return_value = agr_svc

        mock_agr_repo_cls.return_value = AsyncMock()

        # Compliance
        compliance = AsyncMock()
        mock_compliance_cls.return_value = compliance

        # Job generator
        job_gen = AsyncMock()
        job_gen.generate_jobs.return_value = []
        mock_job_gen_cls.return_value = job_gen

        # Email service
        email_svc = MagicMock()
        email_svc.send_confirmation_email.return_value = {
            "content": "conf",
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
                    "phone": "5551234567",
                },
                "customer": "cus_stripe123",
                "subscription": "sub_abc",
                "metadata": {
                    "consent_token": str(uuid4()),
                    "package_tier": "essential",
                    "package_type": "residential",
                },
            },
        )

        result = await handler.handle_event(event)

        assert result["status"] == "processed"
        cust_svc.create_customer.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("grins_platform.api.v1.webhooks.EmailService")
    @patch("grins_platform.api.v1.webhooks.JobGenerator")
    @patch("grins_platform.api.v1.webhooks.ComplianceService")
    @patch("grins_platform.api.v1.webhooks.AgreementService")
    @patch("grins_platform.api.v1.webhooks.AgreementTierRepository")
    @patch("grins_platform.api.v1.webhooks.AgreementRepository")
    @patch("grins_platform.api.v1.webhooks.CustomerRepository")
    async def test_existing_customer_matched_by_email(
        self,
        mock_cust_repo_cls: MagicMock,
        mock_agr_repo_cls: MagicMock,
        mock_tier_repo_cls: MagicMock,
        mock_agr_svc_cls: MagicMock,
        mock_compliance_cls: MagicMock,
        mock_job_gen_cls: MagicMock,
        mock_email_cls: MagicMock,
    ) -> None:
        """Existing customer is matched by email, not duplicated."""
        handler, _session = _make_handler()

        existing_customer = MagicMock()
        existing_customer.id = uuid4()
        existing_customer.stripe_customer_id = None
        existing_customer.email_opt_in_at = None
        existing_customer.email_opt_in = False

        cust_repo = AsyncMock()
        cust_repo.find_by_email.return_value = [existing_customer]
        mock_cust_repo_cls.return_value = cust_repo

        tier = MagicMock()
        tier.id = uuid4()
        tier.name = "Professional"
        tier.annual_price = Decimal("499.00")
        tier.is_active = True
        tier_repo = AsyncMock()
        tier_repo.get_by_slug_and_type.return_value = tier
        mock_tier_repo_cls.return_value = tier_repo

        agreement = _make_agreement(status=AgreementStatus.PENDING.value)
        agr_svc = AsyncMock()
        agr_svc.create_agreement.return_value = agreement
        mock_agr_svc_cls.return_value = agr_svc
        mock_agr_repo_cls.return_value = AsyncMock()

        mock_compliance_cls.return_value = AsyncMock()

        job_gen = AsyncMock()
        job_gen.generate_jobs.return_value = []
        mock_job_gen_cls.return_value = job_gen

        email_svc = MagicMock()
        email_svc.send_confirmation_email.return_value = {
            "content": "c",
            "sent_via": "email",
            "sent": True,
        }
        email_svc.send_welcome_email.return_value = {"sent": True}
        mock_email_cls.return_value = email_svc

        event = _make_event(
            "checkout.session.completed",
            {
                "customer_details": {"email": "existing@example.com", "name": "John"},
                "customer": "cus_456",
                "subscription": "sub_789",
                "metadata": {
                    "package_tier": "professional",
                    "package_type": "residential",
                },
            },
        )

        result = await handler.handle_event(event)

        assert result["status"] == "processed"
        # stripe_customer_id should be updated
        assert existing_customer.stripe_customer_id == "cus_456"

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("grins_platform.api.v1.webhooks.EmailService")
    @patch("grins_platform.api.v1.webhooks.JobGenerator")
    @patch("grins_platform.api.v1.webhooks.ComplianceService")
    @patch("grins_platform.api.v1.webhooks.AgreementService")
    @patch("grins_platform.api.v1.webhooks.AgreementTierRepository")
    @patch("grins_platform.api.v1.webhooks.AgreementRepository")
    @patch("grins_platform.api.v1.webhooks.CustomerRepository")
    async def test_agreement_created_and_jobs_generated(
        self,
        mock_cust_repo_cls: MagicMock,
        mock_agr_repo_cls: MagicMock,
        mock_tier_repo_cls: MagicMock,
        mock_agr_svc_cls: MagicMock,
        mock_compliance_cls: MagicMock,
        mock_job_gen_cls: MagicMock,
        mock_email_cls: MagicMock,
    ) -> None:
        """Agreement is created and job generator is called."""
        handler, _session = _make_handler()

        customer = MagicMock()
        customer.id = uuid4()
        customer.stripe_customer_id = "cus_existing"
        customer.email_opt_in_at = datetime.now(timezone.utc)
        customer.email_opt_in = True

        cust_repo = AsyncMock()
        cust_repo.find_by_email.return_value = [customer]
        mock_cust_repo_cls.return_value = cust_repo

        tier = MagicMock()
        tier.id = uuid4()
        tier.name = "Premium"
        tier.annual_price = Decimal("899.00")
        tier.is_active = True
        tier_repo = AsyncMock()
        tier_repo.get_by_slug_and_type.return_value = tier
        mock_tier_repo_cls.return_value = tier_repo

        agreement = _make_agreement(status=AgreementStatus.PENDING.value)
        agr_svc = AsyncMock()
        agr_svc.create_agreement.return_value = agreement
        mock_agr_svc_cls.return_value = agr_svc
        mock_agr_repo_cls.return_value = AsyncMock()

        mock_compliance_cls.return_value = AsyncMock()

        job_gen = AsyncMock()
        job_gen.generate_jobs.return_value = [MagicMock(), MagicMock()]
        mock_job_gen_cls.return_value = job_gen

        email_svc = MagicMock()
        email_svc.send_confirmation_email.return_value = {
            "content": "c",
            "sent_via": "email",
            "sent": True,
        }
        email_svc.send_welcome_email.return_value = {"sent": True}
        mock_email_cls.return_value = email_svc

        event = _make_event(
            "checkout.session.completed",
            {
                "customer_details": {"email": "test@example.com"},
                "customer": "cus_existing",
                "subscription": "sub_new",
                "metadata": {"package_tier": "premium", "package_type": "residential"},
            },
        )

        result = await handler.handle_event(event)

        assert result["status"] == "processed"
        agr_svc.create_agreement.assert_called_once()
        job_gen.generate_jobs.assert_called_once_with(agreement)

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("grins_platform.api.v1.webhooks.EmailService")
    @patch("grins_platform.api.v1.webhooks.JobGenerator")
    @patch("grins_platform.api.v1.webhooks.ComplianceService")
    @patch("grins_platform.api.v1.webhooks.AgreementService")
    @patch("grins_platform.api.v1.webhooks.AgreementTierRepository")
    @patch("grins_platform.api.v1.webhooks.AgreementRepository")
    @patch("grins_platform.api.v1.webhooks.CustomerRepository")
    async def test_consent_token_linkage(
        self,
        mock_cust_repo_cls: MagicMock,
        mock_agr_repo_cls: MagicMock,
        mock_tier_repo_cls: MagicMock,
        mock_agr_svc_cls: MagicMock,
        mock_compliance_cls: MagicMock,
        mock_job_gen_cls: MagicMock,
        mock_email_cls: MagicMock,
    ) -> None:
        """Consent token triggers orphaned record linkage."""
        handler, _session = _make_handler()

        customer = MagicMock()
        customer.id = uuid4()
        customer.stripe_customer_id = "cus_x"
        customer.email_opt_in_at = datetime.now(timezone.utc)
        customer.email_opt_in = True

        cust_repo = AsyncMock()
        cust_repo.find_by_email.return_value = [customer]
        mock_cust_repo_cls.return_value = cust_repo

        tier = MagicMock()
        tier.id = uuid4()
        tier.name = "Essential"
        tier.annual_price = Decimal("299.00")
        tier.is_active = True
        tier_repo = AsyncMock()
        tier_repo.get_by_slug_and_type.return_value = tier
        mock_tier_repo_cls.return_value = tier_repo

        agreement = _make_agreement(status=AgreementStatus.PENDING.value)
        agr_svc = AsyncMock()
        agr_svc.create_agreement.return_value = agreement
        mock_agr_svc_cls.return_value = agr_svc
        mock_agr_repo_cls.return_value = AsyncMock()

        compliance = AsyncMock()
        mock_compliance_cls.return_value = compliance

        job_gen = AsyncMock()
        job_gen.generate_jobs.return_value = []
        mock_job_gen_cls.return_value = job_gen

        email_svc = MagicMock()
        email_svc.send_confirmation_email.return_value = {
            "content": "c",
            "sent_via": "email",
            "sent": True,
        }
        email_svc.send_welcome_email.return_value = {"sent": True}
        mock_email_cls.return_value = email_svc

        consent_token = uuid4()
        event = _make_event(
            "checkout.session.completed",
            {
                "customer_details": {"email": "test@example.com"},
                "customer": "cus_x",
                "subscription": "sub_y",
                "metadata": {
                    "consent_token": str(consent_token),
                    "package_tier": "essential",
                    "package_type": "residential",
                },
            },
        )

        result = await handler.handle_event(event)

        assert result["status"] == "processed"
        compliance.link_orphaned_records.assert_called_once_with(
            consent_token=consent_token,
            customer_id=customer.id,
            agreement_id=agreement.id,
        )

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("grins_platform.api.v1.webhooks.EmailService")
    @patch("grins_platform.api.v1.webhooks.JobGenerator")
    @patch("grins_platform.api.v1.webhooks.ComplianceService")
    @patch("grins_platform.api.v1.webhooks.AgreementService")
    @patch("grins_platform.api.v1.webhooks.AgreementTierRepository")
    @patch("grins_platform.api.v1.webhooks.AgreementRepository")
    @patch("grins_platform.api.v1.webhooks.CustomerRepository")
    async def test_emails_sent(
        self,
        mock_cust_repo_cls: MagicMock,
        mock_agr_repo_cls: MagicMock,
        mock_tier_repo_cls: MagicMock,
        mock_agr_svc_cls: MagicMock,
        mock_compliance_cls: MagicMock,
        mock_job_gen_cls: MagicMock,
        mock_email_cls: MagicMock,
    ) -> None:
        """Welcome and confirmation emails are sent."""
        handler, _session = _make_handler()

        customer = MagicMock()
        customer.id = uuid4()
        customer.stripe_customer_id = "cus_e"
        customer.email_opt_in_at = datetime.now(timezone.utc)
        customer.email_opt_in = True

        cust_repo = AsyncMock()
        cust_repo.find_by_email.return_value = [customer]
        mock_cust_repo_cls.return_value = cust_repo

        tier = MagicMock()
        tier.id = uuid4()
        tier.name = "Essential"
        tier.annual_price = Decimal("299.00")
        tier.is_active = True
        tier_repo = AsyncMock()
        tier_repo.get_by_slug_and_type.return_value = tier
        mock_tier_repo_cls.return_value = tier_repo

        agreement = _make_agreement(status=AgreementStatus.PENDING.value)
        agr_svc = AsyncMock()
        agr_svc.create_agreement.return_value = agreement
        mock_agr_svc_cls.return_value = agr_svc
        mock_agr_repo_cls.return_value = AsyncMock()

        mock_compliance_cls.return_value = AsyncMock()

        job_gen = AsyncMock()
        job_gen.generate_jobs.return_value = []
        mock_job_gen_cls.return_value = job_gen

        email_svc = MagicMock()
        email_svc.send_confirmation_email.return_value = {
            "content": "c",
            "sent_via": "email",
            "sent": True,
        }
        email_svc.send_welcome_email.return_value = {"sent": True}
        mock_email_cls.return_value = email_svc

        event = _make_event(
            "checkout.session.completed",
            {
                "customer_details": {"email": "test@example.com"},
                "customer": "cus_e",
                "subscription": "sub_e",
                "metadata": {
                    "package_tier": "essential",
                    "package_type": "residential",
                },
            },
        )

        result = await handler.handle_event(event)

        assert result["status"] == "processed"
        email_svc.send_welcome_email.assert_called_once()
        email_svc.send_confirmation_email.assert_called_once()


# =============================================================================
# invoice.paid
# =============================================================================


class TestInvoicePaid:
    """Tests for _handle_invoice_paid."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("grins_platform.api.v1.webhooks.JobGenerator")
    @patch("grins_platform.api.v1.webhooks.AgreementService")
    @patch("grins_platform.api.v1.webhooks.AgreementTierRepository")
    @patch("grins_platform.api.v1.webhooks.AgreementRepository")
    async def test_first_invoice_activates_agreement(
        self,
        mock_agr_repo_cls: MagicMock,
        mock_tier_repo_cls: MagicMock,
        mock_agr_svc_cls: MagicMock,
        mock_job_gen_cls: MagicMock,
    ) -> None:
        """First invoice transitions PENDING → ACTIVE."""
        handler, _session = _make_handler()

        agreement = _make_agreement(status=AgreementStatus.PENDING.value)
        agr_repo = AsyncMock()
        agr_repo.get_by_stripe_subscription_id.return_value = agreement
        mock_agr_repo_cls.return_value = agr_repo
        mock_tier_repo_cls.return_value = AsyncMock()

        agr_svc = AsyncMock()
        mock_agr_svc_cls.return_value = agr_svc

        mock_job_gen_cls.return_value = AsyncMock()

        event = _make_event(
            "invoice.paid",
            {"subscription": "sub_123", "amount_paid": 29900},
        )

        result = await handler.handle_event(event)

        assert result["status"] == "processed"
        agr_svc.transition_status.assert_called_once_with(
            agreement.id,
            AgreementStatus.ACTIVE,
            reason="First invoice paid",
        )

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("grins_platform.api.v1.webhooks.JobGenerator")
    @patch("grins_platform.api.v1.webhooks.AgreementService")
    @patch("grins_platform.api.v1.webhooks.AgreementTierRepository")
    @patch("grins_platform.api.v1.webhooks.AgreementRepository")
    async def test_renewal_invoice_generates_new_jobs(
        self,
        mock_agr_repo_cls: MagicMock,
        mock_tier_repo_cls: MagicMock,
        mock_agr_svc_cls: MagicMock,
        mock_job_gen_cls: MagicMock,
    ) -> None:
        """Renewal invoice updates dates and generates new season jobs."""
        handler, _session = _make_handler()

        agreement = _make_agreement(status=AgreementStatus.ACTIVE.value)
        agr_repo = AsyncMock()
        agr_repo.get_by_stripe_subscription_id.return_value = agreement
        mock_agr_repo_cls.return_value = agr_repo
        mock_tier_repo_cls.return_value = AsyncMock()

        agr_svc = AsyncMock()
        mock_agr_svc_cls.return_value = agr_svc

        job_gen = AsyncMock()
        job_gen.generate_jobs.return_value = []
        mock_job_gen_cls.return_value = job_gen

        event = _make_event(
            "invoice.paid",
            {"subscription": "sub_123", "amount_paid": 59900},
        )

        result = await handler.handle_event(event)

        assert result["status"] == "processed"
        # Already ACTIVE, no transition needed
        agr_svc.transition_status.assert_not_called()
        # But dates updated and jobs generated
        agr_repo.update.assert_called()
        job_gen.generate_jobs.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("grins_platform.api.v1.webhooks.JobGenerator")
    @patch("grins_platform.api.v1.webhooks.AgreementService")
    @patch("grins_platform.api.v1.webhooks.AgreementTierRepository")
    @patch("grins_platform.api.v1.webhooks.AgreementRepository")
    async def test_invoice_paid_updates_payment_fields(
        self,
        mock_agr_repo_cls: MagicMock,
        mock_tier_repo_cls: MagicMock,
        mock_agr_svc_cls: MagicMock,
        mock_job_gen_cls: MagicMock,
    ) -> None:
        """Payment fields are updated on invoice.paid."""
        handler, _session = _make_handler()

        agreement = _make_agreement(status=AgreementStatus.PENDING.value)
        agr_repo = AsyncMock()
        agr_repo.get_by_stripe_subscription_id.return_value = agreement
        mock_agr_repo_cls.return_value = agr_repo
        mock_tier_repo_cls.return_value = AsyncMock()
        mock_agr_svc_cls.return_value = AsyncMock()
        mock_job_gen_cls.return_value = AsyncMock()

        event = _make_event(
            "invoice.paid",
            {"subscription": "sub_123", "amount_paid": 29900},
        )

        result = await handler.handle_event(event)

        assert result["status"] == "processed"
        # Check payment fields update call
        update_calls = agr_repo.update.call_args_list
        payment_update = update_calls[-1]
        update_dict = payment_update[0][1]
        assert update_dict["payment_status"] == AgreementPaymentStatus.CURRENT.value
        assert update_dict["last_payment_amount"] == Decimal("299.00")

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("grins_platform.api.v1.webhooks.AgreementRepository")
    async def test_invoice_paid_no_subscription_skips(
        self,
        mock_agr_repo_cls: MagicMock,
    ) -> None:
        """invoice.paid with no subscription_id is skipped."""
        handler, _session = _make_handler()
        mock_agr_repo_cls.return_value = AsyncMock()

        event = _make_event("invoice.paid", {"subscription": ""})

        result = await handler.handle_event(event)

        assert result["status"] == "processed"


# =============================================================================
# invoice.payment_failed
# =============================================================================


class TestInvoicePaymentFailed:
    """Tests for _handle_invoice_payment_failed."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("grins_platform.api.v1.webhooks.AgreementService")
    @patch("grins_platform.api.v1.webhooks.AgreementTierRepository")
    @patch("grins_platform.api.v1.webhooks.AgreementRepository")
    async def test_first_failure_transitions_to_past_due(
        self,
        mock_agr_repo_cls: MagicMock,
        mock_tier_repo_cls: MagicMock,
        mock_agr_svc_cls: MagicMock,
    ) -> None:
        """First payment failure transitions ACTIVE → PAST_DUE."""
        handler, _session = _make_handler()

        agreement = _make_agreement(status=AgreementStatus.ACTIVE.value)
        agr_repo = AsyncMock()
        agr_repo.get_by_stripe_subscription_id.return_value = agreement
        mock_agr_repo_cls.return_value = agr_repo
        mock_tier_repo_cls.return_value = AsyncMock()

        agr_svc = AsyncMock()
        mock_agr_svc_cls.return_value = agr_svc

        event = _make_event(
            "invoice.payment_failed",
            {"subscription": "sub_123", "attempt_count": 1},
        )

        result = await handler.handle_event(event)

        assert result["status"] == "processed"
        agr_svc.transition_status.assert_called_once_with(
            agreement.id,
            AgreementStatus.PAST_DUE,
            reason="Invoice payment failed",
        )

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("grins_platform.api.v1.webhooks.AgreementService")
    @patch("grins_platform.api.v1.webhooks.AgreementTierRepository")
    @patch("grins_platform.api.v1.webhooks.AgreementRepository")
    async def test_retries_exhausted_escalates_to_paused(
        self,
        mock_agr_repo_cls: MagicMock,
        mock_tier_repo_cls: MagicMock,
        mock_agr_svc_cls: MagicMock,
    ) -> None:
        """Already PAST_DUE with retries exhausted → PAUSED."""
        handler, _session = _make_handler()

        agreement = _make_agreement(status=AgreementStatus.PAST_DUE.value)
        agr_repo = AsyncMock()
        agr_repo.get_by_stripe_subscription_id.return_value = agreement
        mock_agr_repo_cls.return_value = agr_repo
        mock_tier_repo_cls.return_value = AsyncMock()

        agr_svc = AsyncMock()
        mock_agr_svc_cls.return_value = agr_svc

        event = _make_event(
            "invoice.payment_failed",
            {"subscription": "sub_123", "attempt_count": 3},
        )

        result = await handler.handle_event(event)

        assert result["status"] == "processed"
        agr_svc.transition_status.assert_called_once_with(
            agreement.id,
            AgreementStatus.PAUSED,
            reason="Payment failed after 3 attempts",
        )
        # Check payment_status set to FAILED
        update_call = agr_repo.update.call_args
        assert (
            update_call[0][1]["payment_status"] == AgreementPaymentStatus.FAILED.value
        )

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("grins_platform.api.v1.webhooks.AgreementRepository")
    async def test_payment_failed_no_subscription_skips(
        self,
        mock_agr_repo_cls: MagicMock,
    ) -> None:
        """invoice.payment_failed with no subscription_id is skipped."""
        handler, _session = _make_handler()
        mock_agr_repo_cls.return_value = AsyncMock()

        event = _make_event("invoice.payment_failed", {"subscription": ""})

        result = await handler.handle_event(event)

        assert result["status"] == "processed"


# =============================================================================
# invoice.upcoming
# =============================================================================


class TestInvoiceUpcoming:
    """Tests for _handle_invoice_upcoming."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("grins_platform.api.v1.webhooks.EmailService")
    @patch("grins_platform.api.v1.webhooks.ComplianceService")
    @patch("grins_platform.api.v1.webhooks.AgreementService")
    @patch("grins_platform.api.v1.webhooks.AgreementTierRepository")
    @patch("grins_platform.api.v1.webhooks.AgreementRepository")
    async def test_transitions_to_pending_renewal(
        self,
        mock_agr_repo_cls: MagicMock,
        mock_tier_repo_cls: MagicMock,
        mock_agr_svc_cls: MagicMock,
        mock_compliance_cls: MagicMock,
        mock_email_cls: MagicMock,
    ) -> None:
        """invoice.upcoming transitions ACTIVE → PENDING_RENEWAL."""
        handler, _session = _make_handler()

        agreement = _make_agreement(status=AgreementStatus.ACTIVE.value)
        agreement.customer = MagicMock()
        agr_repo = AsyncMock()
        agr_repo.get_by_stripe_subscription_id.return_value = agreement
        mock_agr_repo_cls.return_value = agr_repo
        mock_tier_repo_cls.return_value = AsyncMock()

        agr_svc = AsyncMock()
        mock_agr_svc_cls.return_value = agr_svc

        compliance = AsyncMock()
        mock_compliance_cls.return_value = compliance

        email_svc = MagicMock()
        email_svc.send_renewal_notice.return_value = {
            "content": "renewal",
            "sent_via": "email",
            "sent": True,
        }
        mock_email_cls.return_value = email_svc

        event = _make_event(
            "invoice.upcoming",
            {"subscription": "sub_123"},
        )

        result = await handler.handle_event(event)

        assert result["status"] == "processed"
        agr_svc.transition_status.assert_called_once_with(
            agreement.id,
            AgreementStatus.PENDING_RENEWAL,
            reason="Upcoming invoice received from Stripe",
        )

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("grins_platform.api.v1.webhooks.EmailService")
    @patch("grins_platform.api.v1.webhooks.ComplianceService")
    @patch("grins_platform.api.v1.webhooks.AgreementService")
    @patch("grins_platform.api.v1.webhooks.AgreementTierRepository")
    @patch("grins_platform.api.v1.webhooks.AgreementRepository")
    async def test_creates_renewal_notice_disclosure(
        self,
        mock_agr_repo_cls: MagicMock,
        mock_tier_repo_cls: MagicMock,
        mock_agr_svc_cls: MagicMock,
        mock_compliance_cls: MagicMock,
        mock_email_cls: MagicMock,
    ) -> None:
        """RENEWAL_NOTICE disclosure record is created."""
        handler, _session = _make_handler()

        agreement = _make_agreement(status=AgreementStatus.ACTIVE.value)
        agreement.customer = MagicMock()
        agr_repo = AsyncMock()
        agr_repo.get_by_stripe_subscription_id.return_value = agreement
        mock_agr_repo_cls.return_value = agr_repo
        mock_tier_repo_cls.return_value = AsyncMock()
        mock_agr_svc_cls.return_value = AsyncMock()

        compliance = AsyncMock()
        mock_compliance_cls.return_value = compliance

        email_svc = MagicMock()
        email_svc.send_renewal_notice.return_value = {
            "content": "renewal",
            "sent_via": "email",
            "sent": True,
        }
        mock_email_cls.return_value = email_svc

        event = _make_event("invoice.upcoming", {"subscription": "sub_123"})

        await handler.handle_event(event)

        compliance.create_disclosure.assert_called_once()
        call_kwargs = compliance.create_disclosure.call_args[1]
        assert call_kwargs["disclosure_type"] == DisclosureType.RENEWAL_NOTICE
        assert call_kwargs["agreement_id"] == agreement.id


# =============================================================================
# customer.subscription.updated
# =============================================================================


class TestSubscriptionUpdated:
    """Tests for _handle_subscription_updated."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("grins_platform.api.v1.webhooks.AgreementService")
    @patch("grins_platform.api.v1.webhooks.AgreementTierRepository")
    @patch("grins_platform.api.v1.webhooks.AgreementRepository")
    async def test_status_sync_from_stripe(
        self,
        mock_agr_repo_cls: MagicMock,
        mock_tier_repo_cls: MagicMock,
        mock_agr_svc_cls: MagicMock,
    ) -> None:
        """Stripe status change triggers local status transition."""
        handler, _session = _make_handler()

        agreement = _make_agreement(status=AgreementStatus.ACTIVE.value)
        agr_repo = AsyncMock()
        agr_repo.get_by_stripe_subscription_id.return_value = agreement
        mock_agr_repo_cls.return_value = agr_repo
        mock_tier_repo_cls.return_value = AsyncMock()

        agr_svc = AsyncMock()
        mock_agr_svc_cls.return_value = agr_svc

        event = _make_event(
            "customer.subscription.updated",
            {"id": "sub_123", "status": "past_due", "cancel_at_period_end": False},
        )

        result = await handler.handle_event(event)

        assert result["status"] == "processed"
        agr_svc.transition_status.assert_called_once_with(
            agreement.id,
            AgreementStatus.PAST_DUE,
            reason="Stripe subscription status changed to past_due",
        )

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("grins_platform.api.v1.webhooks.AgreementService")
    @patch("grins_platform.api.v1.webhooks.AgreementTierRepository")
    @patch("grins_platform.api.v1.webhooks.AgreementRepository")
    async def test_payment_recovery_paused_to_active(
        self,
        mock_agr_repo_cls: MagicMock,
        mock_tier_repo_cls: MagicMock,
        mock_agr_svc_cls: MagicMock,
    ) -> None:
        """PAUSED → ACTIVE recovery clears pause_reason and sets CURRENT."""
        handler, _session = _make_handler()

        agreement = _make_agreement(
            status=AgreementStatus.PAUSED.value,
            pause_reason="Payment failed",
        )
        agr_repo = AsyncMock()
        agr_repo.get_by_stripe_subscription_id.return_value = agreement
        mock_agr_repo_cls.return_value = agr_repo
        mock_tier_repo_cls.return_value = AsyncMock()

        agr_svc = AsyncMock()
        mock_agr_svc_cls.return_value = agr_svc

        event = _make_event(
            "customer.subscription.updated",
            {"id": "sub_123", "status": "active", "cancel_at_period_end": False},
        )

        result = await handler.handle_event(event)

        assert result["status"] == "processed"
        agr_svc.transition_status.assert_called_once()
        # Check recovery fields
        update_call = agr_repo.update.call_args
        update_dict = update_call[0][1]
        assert update_dict["pause_reason"] is None
        assert update_dict["payment_status"] == AgreementPaymentStatus.CURRENT.value

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("grins_platform.api.v1.webhooks.AgreementService")
    @patch("grins_platform.api.v1.webhooks.AgreementTierRepository")
    @patch("grins_platform.api.v1.webhooks.AgreementRepository")
    async def test_cancel_at_period_end_syncs_auto_renew(
        self,
        mock_agr_repo_cls: MagicMock,
        mock_tier_repo_cls: MagicMock,
        mock_agr_svc_cls: MagicMock,
    ) -> None:
        """cancel_at_period_end=True sets auto_renew=False."""
        handler, _session = _make_handler()

        agreement = _make_agreement(
            status=AgreementStatus.ACTIVE.value,
            auto_renew=True,
        )
        agr_repo = AsyncMock()
        agr_repo.get_by_stripe_subscription_id.return_value = agreement
        mock_agr_repo_cls.return_value = agr_repo
        mock_tier_repo_cls.return_value = AsyncMock()
        mock_agr_svc_cls.return_value = AsyncMock()

        event = _make_event(
            "customer.subscription.updated",
            {"id": "sub_123", "status": "active", "cancel_at_period_end": True},
        )

        result = await handler.handle_event(event)

        assert result["status"] == "processed"
        update_call = agr_repo.update.call_args
        update_dict = update_call[0][1]
        assert update_dict["auto_renew"] is False

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("grins_platform.api.v1.webhooks.AgreementService")
    @patch("grins_platform.api.v1.webhooks.AgreementTierRepository")
    @patch("grins_platform.api.v1.webhooks.AgreementRepository")
    async def test_idempotent_skip_when_state_matches(
        self,
        mock_agr_repo_cls: MagicMock,
        mock_tier_repo_cls: MagicMock,
        mock_agr_svc_cls: MagicMock,
    ) -> None:
        """No transition when local status already matches Stripe status."""
        handler, _session = _make_handler()

        agreement = _make_agreement(
            status=AgreementStatus.ACTIVE.value,
            auto_renew=True,
        )
        agr_repo = AsyncMock()
        agr_repo.get_by_stripe_subscription_id.return_value = agreement
        mock_agr_repo_cls.return_value = agr_repo
        mock_tier_repo_cls.return_value = AsyncMock()

        agr_svc = AsyncMock()
        mock_agr_svc_cls.return_value = agr_svc

        event = _make_event(
            "customer.subscription.updated",
            {"id": "sub_123", "status": "active", "cancel_at_period_end": False},
        )

        result = await handler.handle_event(event)

        assert result["status"] == "processed"
        agr_svc.transition_status.assert_not_called()
        agr_repo.update.assert_not_called()


# =============================================================================
# customer.subscription.deleted
# =============================================================================


class TestSubscriptionDeleted:
    """Tests for _handle_subscription_deleted."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("grins_platform.api.v1.webhooks.EmailService")
    @patch("grins_platform.api.v1.webhooks.ComplianceService")
    @patch("grins_platform.api.v1.webhooks.AgreementService")
    @patch("grins_platform.api.v1.webhooks.AgreementTierRepository")
    @patch("grins_platform.api.v1.webhooks.AgreementRepository")
    async def test_cancellation_flow(
        self,
        mock_agr_repo_cls: MagicMock,
        mock_tier_repo_cls: MagicMock,
        mock_agr_svc_cls: MagicMock,
        mock_compliance_cls: MagicMock,
        mock_email_cls: MagicMock,
    ) -> None:
        """Subscription deletion triggers full cancellation flow."""
        handler, _session = _make_handler()

        agreement = _make_agreement(status=AgreementStatus.ACTIVE.value)
        agreement.customer = MagicMock()
        agr_repo = AsyncMock()
        agr_repo.get_by_stripe_subscription_id.return_value = agreement
        mock_agr_repo_cls.return_value = agr_repo
        mock_tier_repo_cls.return_value = AsyncMock()

        cancelled_agreement = _make_agreement(status=AgreementStatus.CANCELLED.value)
        cancelled_agreement.customer = agreement.customer
        agr_svc = AsyncMock()
        agr_svc.cancel_agreement.return_value = cancelled_agreement
        mock_agr_svc_cls.return_value = agr_svc

        compliance = AsyncMock()
        mock_compliance_cls.return_value = compliance

        email_svc = MagicMock()
        email_svc.send_cancellation_confirmation.return_value = {
            "content": "cancelled",
            "sent_via": "email",
            "sent": True,
        }
        mock_email_cls.return_value = email_svc

        event = _make_event(
            "customer.subscription.deleted",
            {
                "id": "sub_123",
                "cancellation_details": {"reason": "customer_request"},
            },
        )

        result = await handler.handle_event(event)

        assert result["status"] == "processed"
        agr_svc.cancel_agreement.assert_called_once_with(
            agreement.id,
            reason="customer_request",
        )

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("grins_platform.api.v1.webhooks.EmailService")
    @patch("grins_platform.api.v1.webhooks.ComplianceService")
    @patch("grins_platform.api.v1.webhooks.AgreementService")
    @patch("grins_platform.api.v1.webhooks.AgreementTierRepository")
    @patch("grins_platform.api.v1.webhooks.AgreementRepository")
    async def test_cancellation_disclosure_created(
        self,
        mock_agr_repo_cls: MagicMock,
        mock_tier_repo_cls: MagicMock,
        mock_agr_svc_cls: MagicMock,
        mock_compliance_cls: MagicMock,
        mock_email_cls: MagicMock,
    ) -> None:
        """CANCELLATION_CONF disclosure record is created."""
        handler, _session = _make_handler()

        agreement = _make_agreement(status=AgreementStatus.ACTIVE.value)
        agreement.customer = MagicMock()
        agr_repo = AsyncMock()
        agr_repo.get_by_stripe_subscription_id.return_value = agreement
        mock_agr_repo_cls.return_value = agr_repo
        mock_tier_repo_cls.return_value = AsyncMock()

        cancelled = _make_agreement(status=AgreementStatus.CANCELLED.value)
        cancelled.customer = agreement.customer
        agr_svc = AsyncMock()
        agr_svc.cancel_agreement.return_value = cancelled
        mock_agr_svc_cls.return_value = agr_svc

        compliance = AsyncMock()
        mock_compliance_cls.return_value = compliance

        email_svc = MagicMock()
        email_svc.send_cancellation_confirmation.return_value = {
            "content": "cancel_conf",
            "sent_via": "email",
            "sent": True,
        }
        mock_email_cls.return_value = email_svc

        event = _make_event(
            "customer.subscription.deleted",
            {"id": "sub_123", "cancellation_details": {"reason": "test"}},
        )

        await handler.handle_event(event)

        compliance.create_disclosure.assert_called_once()
        call_kwargs = compliance.create_disclosure.call_args[1]
        assert call_kwargs["disclosure_type"] == DisclosureType.CANCELLATION_CONF

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("grins_platform.api.v1.webhooks.EmailService")
    @patch("grins_platform.api.v1.webhooks.ComplianceService")
    @patch("grins_platform.api.v1.webhooks.AgreementService")
    @patch("grins_platform.api.v1.webhooks.AgreementTierRepository")
    @patch("grins_platform.api.v1.webhooks.AgreementRepository")
    async def test_cancellation_email_sent(
        self,
        mock_agr_repo_cls: MagicMock,
        mock_tier_repo_cls: MagicMock,
        mock_agr_svc_cls: MagicMock,
        mock_compliance_cls: MagicMock,
        mock_email_cls: MagicMock,
    ) -> None:
        """Cancellation confirmation email is sent."""
        handler, _session = _make_handler()

        agreement = _make_agreement(status=AgreementStatus.ACTIVE.value)
        agreement.customer = MagicMock()
        agr_repo = AsyncMock()
        agr_repo.get_by_stripe_subscription_id.return_value = agreement
        mock_agr_repo_cls.return_value = agr_repo
        mock_tier_repo_cls.return_value = AsyncMock()

        cancelled = _make_agreement(status=AgreementStatus.CANCELLED.value)
        cancelled.customer = agreement.customer
        agr_svc = AsyncMock()
        agr_svc.cancel_agreement.return_value = cancelled
        mock_agr_svc_cls.return_value = agr_svc

        mock_compliance_cls.return_value = AsyncMock()

        email_svc = MagicMock()
        email_svc.send_cancellation_confirmation.return_value = {
            "content": "c",
            "sent_via": "email",
            "sent": True,
        }
        mock_email_cls.return_value = email_svc

        event = _make_event(
            "customer.subscription.deleted",
            {"id": "sub_123", "cancellation_details": {"reason": "test"}},
        )

        await handler.handle_event(event)

        email_svc.send_cancellation_confirmation.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("grins_platform.api.v1.webhooks.AgreementRepository")
    async def test_subscription_deleted_no_id_skips(
        self,
        mock_agr_repo_cls: MagicMock,
    ) -> None:
        """subscription.deleted with no subscription id is skipped."""
        handler, _session = _make_handler()
        mock_agr_repo_cls.return_value = AsyncMock()

        event = _make_event("customer.subscription.deleted", {"id": ""})

        result = await handler.handle_event(event)

        assert result["status"] == "processed"
