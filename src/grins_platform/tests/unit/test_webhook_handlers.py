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
    agr.last_payment_date = overrides.get("last_payment_date")
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

        # Customer repo: no existing customer by email or phone
        cust_repo = AsyncMock()
        cust_repo.find_by_email.return_value = []
        cust_repo.find_by_phone.return_value = None
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
    @patch("grins_platform.api.v1.webhooks.CustomerService")
    @patch("grins_platform.api.v1.webhooks.CustomerRepository")
    async def test_existing_customer_matched_by_phone_when_email_differs(
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
        """Existing customer is matched by phone when email differs (BUG #18)."""
        handler, _session = _make_handler()

        # Customer repo: no email match, but phone match
        existing_customer = MagicMock()
        existing_customer.id = uuid4()
        existing_customer.stripe_customer_id = "cus_old"
        existing_customer.email = "old@example.com"
        existing_customer.email_opt_in_at = None
        existing_customer.email_opt_in = False

        cust_repo = AsyncMock()
        cust_repo.find_by_email.return_value = []
        cust_repo.find_by_phone.return_value = existing_customer
        mock_cust_repo_cls.return_value = cust_repo

        # Customer service should NOT be called (no create needed)
        cust_svc = AsyncMock()
        mock_cust_svc_cls.return_value = cust_svc

        # Tier repo
        tier = MagicMock()
        tier.id = uuid4()
        tier.name = "Essential"
        tier.annual_price = Decimal("170.00")
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
                "customer_details": {
                    "email": "different@example.com",
                    "name": "Jane Doe",
                    "phone": "+16125551234",
                },
                "customer": "cus_new_stripe",
                "subscription": "sub_new",
                "metadata": {
                    "consent_token": str(uuid4()),
                    "package_tier": "essential",
                    "package_type": "residential",
                },
            },
        )

        result = await handler.handle_event(event)

        assert result["status"] == "processed"
        # Customer should be reused, NOT created
        cust_svc.create_customer.assert_not_called()
        # Phone lookup should have been called with normalized phone
        cust_repo.find_by_phone.assert_called_once_with("6125551234")
        # stripe_customer_id should be updated to the new one
        assert existing_customer.stripe_customer_id == "cus_new_stripe"

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
# checkout.session.completed — surcharge & metadata field population
# Validates: Requirements 3.14, 2.5
# =============================================================================


class TestCheckoutCompletedNewFields:
    """Tests for new field population in _handle_checkout_completed."""

    @staticmethod
    def _setup_checkout_mocks(
        mock_cust_repo_cls: MagicMock,
        mock_agr_repo_cls: MagicMock,
        mock_tier_repo_cls: MagicMock,
        mock_agr_svc_cls: MagicMock,
        mock_compliance_cls: MagicMock,
        mock_job_gen_cls: MagicMock,
        mock_email_cls: MagicMock,
        *,
        tier_annual_price: Decimal = Decimal("599.00"),
        customer_email_opt_in: bool = False,
    ) -> tuple[MagicMock, MagicMock, AsyncMock, MagicMock]:
        """Set up common mocks for checkout tests.

        Returns (customer, tier, agr_repo, agreement).
        """
        customer = MagicMock()
        customer.id = uuid4()
        customer.stripe_customer_id = "cus_existing"
        customer.email_opt_in_at = (
            datetime.now(timezone.utc) if customer_email_opt_in else None
        )
        customer.email_opt_in = customer_email_opt_in
        customer.email_opt_in_source = (
            "stripe_checkout" if customer_email_opt_in else None
        )

        cust_repo = AsyncMock()
        cust_repo.find_by_email.return_value = [customer]
        mock_cust_repo_cls.return_value = cust_repo

        tier = MagicMock()
        tier.id = uuid4()
        tier.name = "Essential"
        tier.annual_price = tier_annual_price
        tier.is_active = True
        tier_repo = AsyncMock()
        tier_repo.get_by_slug_and_type.return_value = tier
        mock_tier_repo_cls.return_value = tier_repo

        agreement = _make_agreement(status=AgreementStatus.PENDING.value)
        agr_svc = AsyncMock()
        agr_svc.create_agreement.return_value = agreement
        mock_agr_svc_cls.return_value = agr_svc

        agr_repo = AsyncMock()
        agr_repo.update.return_value = agreement
        mock_agr_repo_cls.return_value = agr_repo

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

        return customer, tier, agr_repo, agreement

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("grins_platform.api.v1.webhooks.SurchargeCalculator")
    @patch("grins_platform.api.v1.webhooks.EmailService")
    @patch("grins_platform.api.v1.webhooks.JobGenerator")
    @patch("grins_platform.api.v1.webhooks.ComplianceService")
    @patch("grins_platform.api.v1.webhooks.AgreementService")
    @patch("grins_platform.api.v1.webhooks.AgreementTierRepository")
    @patch("grins_platform.api.v1.webhooks.AgreementRepository")
    @patch("grins_platform.api.v1.webhooks.CustomerRepository")
    async def test_surcharge_fields_populated_with_zone_and_lake_pump(
        self,
        mock_cust_repo_cls: MagicMock,
        mock_agr_repo_cls: MagicMock,
        mock_tier_repo_cls: MagicMock,
        mock_agr_svc_cls: MagicMock,
        mock_compliance_cls: MagicMock,
        mock_job_gen_cls: MagicMock,
        mock_email_cls: MagicMock,
        mock_surcharge_cls: MagicMock,
    ) -> None:
        """zone_count=15, has_lake_pump=true populates agreement fields correctly."""
        handler, _session = _make_handler()

        _customer, _tier, agr_repo, _agreement = self._setup_checkout_mocks(
            mock_cust_repo_cls,
            mock_agr_repo_cls,
            mock_tier_repo_cls,
            mock_agr_svc_cls,
            mock_compliance_cls,
            mock_job_gen_cls,
            mock_email_cls,
            tier_annual_price=Decimal("599.00"),
        )

        # Mock SurchargeCalculator
        mock_breakdown = MagicMock()
        mock_breakdown.total = Decimal("749.00")
        mock_surcharge_cls.calculate.return_value = mock_breakdown

        event = _make_event(
            "checkout.session.completed",
            {
                "customer_details": {"email": "test@example.com"},
                "customer": "cus_existing",
                "subscription": "sub_1",
                "metadata": {
                    "package_tier": "essential",
                    "package_type": "residential",
                    "zone_count": "15",
                    "has_lake_pump": "true",
                    "email_marketing_consent": "false",
                },
            },
        )

        result = await handler.handle_event(event)

        assert result["status"] == "processed"
        mock_surcharge_cls.calculate.assert_called_once_with(
            tier_slug="essential",
            package_type="residential",
            zone_count=15,
            has_lake_pump=True,
            base_price=Decimal("599.00"),
            has_rpz_backflow=False,
        )
        # Verify agreement_repo.update called with surcharge fields
        agr_repo.update.assert_called_once()
        update_args = agr_repo.update.call_args
        update_dict = update_args[0][1]
        assert update_dict["zone_count"] == 15
        assert update_dict["has_lake_pump"] is True
        assert update_dict["has_rpz_backflow"] is False
        assert update_dict["base_price"] == Decimal("599.00")
        assert update_dict["annual_price"] == Decimal("749.00")

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("grins_platform.api.v1.webhooks.SurchargeCalculator")
    @patch("grins_platform.api.v1.webhooks.EmailService")
    @patch("grins_platform.api.v1.webhooks.JobGenerator")
    @patch("grins_platform.api.v1.webhooks.ComplianceService")
    @patch("grins_platform.api.v1.webhooks.AgreementService")
    @patch("grins_platform.api.v1.webhooks.AgreementTierRepository")
    @patch("grins_platform.api.v1.webhooks.AgreementRepository")
    @patch("grins_platform.api.v1.webhooks.CustomerRepository")
    async def test_no_surcharges_when_low_zone_count(
        self,
        mock_cust_repo_cls: MagicMock,
        mock_agr_repo_cls: MagicMock,
        mock_tier_repo_cls: MagicMock,
        mock_agr_svc_cls: MagicMock,
        mock_compliance_cls: MagicMock,
        mock_job_gen_cls: MagicMock,
        mock_email_cls: MagicMock,
        mock_surcharge_cls: MagicMock,
    ) -> None:
        """zone_count=5, has_lake_pump=false → base_price equals annual_price."""
        handler, _session = _make_handler()

        _customer, _tier, agr_repo, _agreement = self._setup_checkout_mocks(
            mock_cust_repo_cls,
            mock_agr_repo_cls,
            mock_tier_repo_cls,
            mock_agr_svc_cls,
            mock_compliance_cls,
            mock_job_gen_cls,
            mock_email_cls,
            tier_annual_price=Decimal("599.00"),
        )

        mock_breakdown = MagicMock()
        mock_breakdown.total = Decimal("599.00")
        mock_surcharge_cls.calculate.return_value = mock_breakdown

        event = _make_event(
            "checkout.session.completed",
            {
                "customer_details": {"email": "test@example.com"},
                "customer": "cus_existing",
                "subscription": "sub_2",
                "metadata": {
                    "package_tier": "essential",
                    "package_type": "residential",
                    "zone_count": "5",
                    "has_lake_pump": "false",
                },
            },
        )

        result = await handler.handle_event(event)

        assert result["status"] == "processed"
        update_dict = agr_repo.update.call_args[0][1]
        assert update_dict["zone_count"] == 5
        assert update_dict["has_lake_pump"] is False
        assert update_dict["base_price"] == Decimal("599.00")
        assert update_dict["annual_price"] == Decimal("599.00")

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("grins_platform.api.v1.webhooks.SurchargeCalculator")
    @patch("grins_platform.api.v1.webhooks.EmailService")
    @patch("grins_platform.api.v1.webhooks.JobGenerator")
    @patch("grins_platform.api.v1.webhooks.ComplianceService")
    @patch("grins_platform.api.v1.webhooks.AgreementService")
    @patch("grins_platform.api.v1.webhooks.AgreementTierRepository")
    @patch("grins_platform.api.v1.webhooks.AgreementRepository")
    @patch("grins_platform.api.v1.webhooks.CustomerRepository")
    async def test_base_price_vs_annual_price_distinction(
        self,
        mock_cust_repo_cls: MagicMock,
        mock_agr_repo_cls: MagicMock,
        mock_tier_repo_cls: MagicMock,
        mock_agr_svc_cls: MagicMock,
        mock_compliance_cls: MagicMock,
        mock_job_gen_cls: MagicMock,
        mock_email_cls: MagicMock,
        mock_surcharge_cls: MagicMock,
    ) -> None:
        """base_price is tier price, annual_price includes surcharges."""
        handler, _session = _make_handler()

        _customer, _tier, agr_repo, _agreement = self._setup_checkout_mocks(
            mock_cust_repo_cls,
            mock_agr_repo_cls,
            mock_tier_repo_cls,
            mock_agr_svc_cls,
            mock_compliance_cls,
            mock_job_gen_cls,
            mock_email_cls,
            tier_annual_price=Decimal("299.00"),
        )

        mock_breakdown = MagicMock()
        mock_breakdown.total = Decimal("449.00")  # 299 + surcharges
        mock_surcharge_cls.calculate.return_value = mock_breakdown

        event = _make_event(
            "checkout.session.completed",
            {
                "customer_details": {"email": "test@example.com"},
                "customer": "cus_existing",
                "subscription": "sub_3",
                "metadata": {
                    "package_tier": "essential",
                    "package_type": "residential",
                    "zone_count": "12",
                    "has_lake_pump": "true",
                },
            },
        )

        result = await handler.handle_event(event)

        assert result["status"] == "processed"
        update_dict = agr_repo.update.call_args[0][1]
        assert update_dict["base_price"] == Decimal("299.00")
        assert update_dict["annual_price"] == Decimal("449.00")
        assert update_dict["base_price"] != update_dict["annual_price"]

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("grins_platform.api.v1.webhooks.SurchargeCalculator")
    @patch("grins_platform.api.v1.webhooks.EmailService")
    @patch("grins_platform.api.v1.webhooks.JobGenerator")
    @patch("grins_platform.api.v1.webhooks.ComplianceService")
    @patch("grins_platform.api.v1.webhooks.AgreementService")
    @patch("grins_platform.api.v1.webhooks.AgreementTierRepository")
    @patch("grins_platform.api.v1.webhooks.AgreementRepository")
    @patch("grins_platform.api.v1.webhooks.CustomerRepository")
    async def test_email_marketing_consent_true_sets_customer_opt_in(
        self,
        mock_cust_repo_cls: MagicMock,
        mock_agr_repo_cls: MagicMock,
        mock_tier_repo_cls: MagicMock,
        mock_agr_svc_cls: MagicMock,
        mock_compliance_cls: MagicMock,
        mock_job_gen_cls: MagicMock,
        mock_email_cls: MagicMock,
        mock_surcharge_cls: MagicMock,
    ) -> None:
        """email_marketing_consent=true sets opt_in for
        existing customer who opted out.
        """
        handler, _session = _make_handler()

        # Existing customer who previously had email_opt_in_at set but opted out
        customer, _tier, _agr_repo, _agreement = self._setup_checkout_mocks(
            mock_cust_repo_cls,
            mock_agr_repo_cls,
            mock_tier_repo_cls,
            mock_agr_svc_cls,
            mock_compliance_cls,
            mock_job_gen_cls,
            mock_email_cls,
            customer_email_opt_in=False,
        )
        # Customer has email_opt_in_at set (existing) but email_opt_in=False (opted out)
        customer.email_opt_in = False
        customer.email_opt_in_at = datetime.now(timezone.utc)
        customer.email_opt_in_source = "previous"

        mock_breakdown = MagicMock()
        mock_breakdown.total = Decimal("599.00")
        mock_surcharge_cls.calculate.return_value = mock_breakdown

        event = _make_event(
            "checkout.session.completed",
            {
                "customer_details": {"email": "test@example.com"},
                "customer": "cus_existing",
                "subscription": "sub_4",
                "metadata": {
                    "package_tier": "essential",
                    "package_type": "residential",
                    "email_marketing_consent": "true",
                },
            },
        )

        result = await handler.handle_event(event)

        assert result["status"] == "processed"
        assert customer.email_opt_in is True
        assert customer.email_opt_in_source == "checkout_marketing_consent"

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("grins_platform.api.v1.webhooks.SurchargeCalculator")
    @patch("grins_platform.api.v1.webhooks.EmailService")
    @patch("grins_platform.api.v1.webhooks.JobGenerator")
    @patch("grins_platform.api.v1.webhooks.ComplianceService")
    @patch("grins_platform.api.v1.webhooks.AgreementService")
    @patch("grins_platform.api.v1.webhooks.AgreementTierRepository")
    @patch("grins_platform.api.v1.webhooks.AgreementRepository")
    @patch("grins_platform.api.v1.webhooks.CustomerRepository")
    async def test_email_marketing_consent_false_does_not_change_opt_in(
        self,
        mock_cust_repo_cls: MagicMock,
        mock_agr_repo_cls: MagicMock,
        mock_tier_repo_cls: MagicMock,
        mock_agr_svc_cls: MagicMock,
        mock_compliance_cls: MagicMock,
        mock_job_gen_cls: MagicMock,
        mock_email_cls: MagicMock,
        mock_surcharge_cls: MagicMock,
    ) -> None:
        """email_marketing_consent=false does not override existing opt-out."""
        handler, _session = _make_handler()

        # Existing customer who opted out — email_opt_in_at set, email_opt_in=False
        customer, _tier, _agr_repo, _agreement = self._setup_checkout_mocks(
            mock_cust_repo_cls,
            mock_agr_repo_cls,
            mock_tier_repo_cls,
            mock_agr_svc_cls,
            mock_compliance_cls,
            mock_job_gen_cls,
            mock_email_cls,
            customer_email_opt_in=False,
        )
        customer.email_opt_in = False
        customer.email_opt_in_at = datetime.now(timezone.utc)
        customer.email_opt_in_source = "previous"

        mock_breakdown = MagicMock()
        mock_breakdown.total = Decimal("599.00")
        mock_surcharge_cls.calculate.return_value = mock_breakdown

        event = _make_event(
            "checkout.session.completed",
            {
                "customer_details": {"email": "test@example.com"},
                "customer": "cus_existing",
                "subscription": "sub_5",
                "metadata": {
                    "package_tier": "essential",
                    "package_type": "residential",
                    "email_marketing_consent": "false",
                },
            },
        )

        result = await handler.handle_event(event)

        assert result["status"] == "processed"
        # email_opt_in should remain False since marketing consent is false
        assert customer.email_opt_in is False
        assert customer.email_opt_in_source == "previous"

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("grins_platform.api.v1.webhooks.SurchargeCalculator")
    @patch("grins_platform.api.v1.webhooks.EmailService")
    @patch("grins_platform.api.v1.webhooks.JobGenerator")
    @patch("grins_platform.api.v1.webhooks.ComplianceService")
    @patch("grins_platform.api.v1.webhooks.AgreementService")
    @patch("grins_platform.api.v1.webhooks.AgreementTierRepository")
    @patch("grins_platform.api.v1.webhooks.AgreementRepository")
    @patch("grins_platform.api.v1.webhooks.CustomerRepository")
    async def test_winterization_only_tier_uses_correct_slug(
        self,
        mock_cust_repo_cls: MagicMock,
        mock_agr_repo_cls: MagicMock,
        mock_tier_repo_cls: MagicMock,
        mock_agr_svc_cls: MagicMock,
        mock_compliance_cls: MagicMock,
        mock_job_gen_cls: MagicMock,
        mock_email_cls: MagicMock,
        mock_surcharge_cls: MagicMock,
    ) -> None:
        """Winterization-only tier slug is passed to SurchargeCalculator."""
        handler, _session = _make_handler()

        _customer, _tier, _agr_repo, _agreement = self._setup_checkout_mocks(
            mock_cust_repo_cls,
            mock_agr_repo_cls,
            mock_tier_repo_cls,
            mock_agr_svc_cls,
            mock_compliance_cls,
            mock_job_gen_cls,
            mock_email_cls,
            tier_annual_price=Decimal("80.00"),
        )

        mock_breakdown = MagicMock()
        mock_breakdown.total = Decimal("80.00")
        mock_surcharge_cls.calculate.return_value = mock_breakdown

        event = _make_event(
            "checkout.session.completed",
            {
                "customer_details": {"email": "test@example.com"},
                "customer": "cus_existing",
                "subscription": "sub_6",
                "metadata": {
                    "package_tier": "winterization-only-residential",
                    "package_type": "residential",
                    "zone_count": "5",
                    "has_lake_pump": "false",
                },
            },
        )

        result = await handler.handle_event(event)

        assert result["status"] == "processed"
        mock_surcharge_cls.calculate.assert_called_once_with(
            tier_slug="winterization-only-residential",
            package_type="residential",
            zone_count=5,
            has_lake_pump=False,
            base_price=Decimal("80.00"),
            has_rpz_backflow=False,
        )

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("grins_platform.api.v1.webhooks.SurchargeCalculator")
    @patch("grins_platform.api.v1.webhooks.EmailService")
    @patch("grins_platform.api.v1.webhooks.JobGenerator")
    @patch("grins_platform.api.v1.webhooks.ComplianceService")
    @patch("grins_platform.api.v1.webhooks.AgreementService")
    @patch("grins_platform.api.v1.webhooks.AgreementTierRepository")
    @patch("grins_platform.api.v1.webhooks.AgreementRepository")
    @patch("grins_platform.api.v1.webhooks.CustomerRepository")
    async def test_missing_metadata_defaults(
        self,
        mock_cust_repo_cls: MagicMock,
        mock_agr_repo_cls: MagicMock,
        mock_tier_repo_cls: MagicMock,
        mock_agr_svc_cls: MagicMock,
        mock_compliance_cls: MagicMock,
        mock_job_gen_cls: MagicMock,
        mock_email_cls: MagicMock,
        mock_surcharge_cls: MagicMock,
    ) -> None:
        """Missing metadata defaults to zone_count=1,
        has_lake_pump=false, email_marketing_consent=false.
        """
        handler, _session = _make_handler()

        _customer, _tier, agr_repo, _agreement = self._setup_checkout_mocks(
            mock_cust_repo_cls,
            mock_agr_repo_cls,
            mock_tier_repo_cls,
            mock_agr_svc_cls,
            mock_compliance_cls,
            mock_job_gen_cls,
            mock_email_cls,
        )

        mock_breakdown = MagicMock()
        mock_breakdown.total = Decimal("599.00")
        mock_surcharge_cls.calculate.return_value = mock_breakdown

        event = _make_event(
            "checkout.session.completed",
            {
                "customer_details": {"email": "test@example.com"},
                "customer": "cus_existing",
                "subscription": "sub_7",
                "metadata": {
                    "package_tier": "essential",
                    "package_type": "residential",
                    # No zone_count, has_lake_pump, or email_marketing_consent
                },
            },
        )

        result = await handler.handle_event(event)

        assert result["status"] == "processed"
        mock_surcharge_cls.calculate.assert_called_once_with(
            tier_slug="essential",
            package_type="residential",
            zone_count=1,
            has_lake_pump=False,
            base_price=Decimal("599.00"),
            has_rpz_backflow=False,
        )
        update_dict = agr_repo.update.call_args[0][1]
        assert update_dict["zone_count"] == 1
        assert update_dict["has_lake_pump"] is False
        assert update_dict["has_rpz_backflow"] is False


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
    async def test_first_invoice_skips_transition_for_active_agreement(
        self,
        mock_agr_repo_cls: MagicMock,
        mock_tier_repo_cls: MagicMock,
        mock_agr_svc_cls: MagicMock,
        mock_job_gen_cls: MagicMock,
    ) -> None:
        """First invoice for already-ACTIVE agreement skips transition."""
        handler, _session = _make_handler()

        # Already ACTIVE (activated by checkout webhook), no payment yet
        agreement = _make_agreement(
            status=AgreementStatus.ACTIVE.value,
            last_payment_date=None,
        )
        agr_repo = AsyncMock()
        agr_repo.get_by_stripe_subscription_id.return_value = agreement
        mock_agr_repo_cls.return_value = agr_repo
        mock_tier_repo_cls.return_value = AsyncMock()

        agr_svc = AsyncMock()
        mock_agr_svc_cls.return_value = agr_svc

        job_gen = AsyncMock()
        mock_job_gen_cls.return_value = job_gen

        event = _make_event(
            "invoice.paid",
            {"subscription": "sub_123", "amount_paid": 17000},
        )

        result = await handler.handle_event(event)

        assert result["status"] == "processed"
        # Already ACTIVE — no transition needed
        agr_svc.transition_status.assert_not_called()
        # First invoice — no job generation (checkout already did that)
        job_gen.generate_jobs.assert_not_called()
        # Payment fields should still be updated
        agr_repo.update.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("grins_platform.api.v1.webhooks.ContractRenewalReviewService")
    @patch("grins_platform.api.v1.webhooks.JobGenerator")
    @patch("grins_platform.api.v1.webhooks.AgreementService")
    @patch("grins_platform.api.v1.webhooks.AgreementTierRepository")
    @patch("grins_platform.api.v1.webhooks.AgreementRepository")
    async def test_invoice_paid_subscription_cycle_without_auto_renew_generates_jobs(
        self,
        mock_agr_repo_cls: MagicMock,
        mock_tier_repo_cls: MagicMock,
        mock_agr_svc_cls: MagicMock,
        mock_job_gen_cls: MagicMock,
        mock_renewal_svc_cls: MagicMock,
    ) -> None:
        """CR-4: ``subscription_cycle`` + auto_renew=False → generate_jobs, no proposal."""
        handler, _session = _make_handler()

        agreement = _make_agreement(
            status=AgreementStatus.ACTIVE.value,
            last_payment_date=datetime(2025, 3, 1, tzinfo=timezone.utc),
            auto_renew=False,
        )
        agr_repo = AsyncMock()
        agr_repo.get_by_stripe_subscription_id.return_value = agreement
        mock_agr_repo_cls.return_value = agr_repo
        mock_tier_repo_cls.return_value = AsyncMock()

        agr_svc = AsyncMock()
        mock_agr_svc_cls.return_value = agr_svc

        job_gen = AsyncMock()
        job_gen.generate_jobs.return_value = []
        mock_job_gen_cls.return_value = job_gen

        mock_renewal_svc_cls.return_value = AsyncMock()

        event = _make_event(
            "invoice.paid",
            {
                "subscription": "sub_123",
                "amount_paid": 59900,
                "billing_reason": "subscription_cycle",
            },
        )

        result = await handler.handle_event(event)

        assert result["status"] == "processed"
        # Already ACTIVE, no transition needed
        agr_svc.transition_status.assert_not_called()
        # But dates updated and jobs generated (auto_renew=False)
        agr_repo.update.assert_called()
        job_gen.generate_jobs.assert_called_once()
        mock_renewal_svc_cls.return_value.generate_proposal.assert_not_called()

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("grins_platform.api.v1.webhooks.ContractRenewalReviewService")
    @patch("grins_platform.api.v1.webhooks.JobGenerator")
    @patch("grins_platform.api.v1.webhooks.AgreementService")
    @patch("grins_platform.api.v1.webhooks.AgreementTierRepository")
    @patch("grins_platform.api.v1.webhooks.AgreementRepository")
    async def test_invoice_paid_subscription_cycle_triggers_renewal_proposal(
        self,
        mock_agr_repo_cls: MagicMock,
        mock_tier_repo_cls: MagicMock,
        mock_agr_svc_cls: MagicMock,
        mock_job_gen_cls: MagicMock,
        mock_renewal_svc_cls: MagicMock,
    ) -> None:
        """CR-4: ``subscription_cycle`` + auto_renew=True → proposal (Req 31.1)."""
        handler, _session = _make_handler()

        agreement = _make_agreement(
            status=AgreementStatus.ACTIVE.value,
            last_payment_date=datetime(2025, 3, 1, tzinfo=timezone.utc),
            auto_renew=True,
        )
        agr_repo = AsyncMock()
        agr_repo.get_by_stripe_subscription_id.return_value = agreement
        mock_agr_repo_cls.return_value = agr_repo
        mock_tier_repo_cls.return_value = AsyncMock()

        agr_svc = AsyncMock()
        mock_agr_svc_cls.return_value = agr_svc

        job_gen = AsyncMock()
        mock_job_gen_cls.return_value = job_gen

        renewal_svc = AsyncMock()
        mock_renewal_svc_cls.return_value = renewal_svc

        event = _make_event(
            "invoice.paid",
            {
                "subscription": "sub_123",
                "amount_paid": 59900,
                "billing_reason": "subscription_cycle",
            },
        )

        result = await handler.handle_event(event)

        assert result["status"] == "processed"
        # auto_renew=True → proposal, not direct jobs
        renewal_svc.generate_proposal.assert_called_once_with(agreement.id)
        job_gen.generate_jobs.assert_not_called()

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("grins_platform.api.v1.webhooks.ContractRenewalReviewService")
    @patch("grins_platform.api.v1.webhooks.JobGenerator")
    @patch("grins_platform.api.v1.webhooks.AgreementService")
    @patch("grins_platform.api.v1.webhooks.AgreementTierRepository")
    @patch("grins_platform.api.v1.webhooks.AgreementRepository")
    async def test_invoice_paid_subscription_create_transitions_to_active_no_renewal(
        self,
        mock_agr_repo_cls: MagicMock,
        mock_tier_repo_cls: MagicMock,
        mock_agr_svc_cls: MagicMock,
        mock_job_gen_cls: MagicMock,
        mock_renewal_svc_cls: MagicMock,
    ) -> None:
        """CR-4: ``subscription_create`` + first payment activates PENDING; no renewal."""
        handler, _session = _make_handler()

        agreement = _make_agreement(
            status=AgreementStatus.PENDING.value,
            last_payment_date=None,
        )
        agr_repo = AsyncMock()
        agr_repo.get_by_stripe_subscription_id.return_value = agreement
        mock_agr_repo_cls.return_value = agr_repo
        mock_tier_repo_cls.return_value = AsyncMock()

        agr_svc = AsyncMock()
        mock_agr_svc_cls.return_value = agr_svc

        job_gen = AsyncMock()
        mock_job_gen_cls.return_value = job_gen

        renewal_svc = AsyncMock()
        mock_renewal_svc_cls.return_value = renewal_svc

        event = _make_event(
            "invoice.paid",
            {
                "subscription": "sub_123",
                "amount_paid": 29900,
                "billing_reason": "subscription_create",
            },
        )

        result = await handler.handle_event(event)

        assert result["status"] == "processed"
        agr_svc.transition_status.assert_called_once_with(
            agreement.id,
            AgreementStatus.ACTIVE,
            reason="First invoice paid",
        )
        renewal_svc.generate_proposal.assert_not_called()
        job_gen.generate_jobs.assert_not_called()

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("grins_platform.api.v1.webhooks.ContractRenewalReviewService")
    @patch("grins_platform.api.v1.webhooks.JobGenerator")
    @patch("grins_platform.api.v1.webhooks.AgreementService")
    @patch("grins_platform.api.v1.webhooks.AgreementTierRepository")
    @patch("grins_platform.api.v1.webhooks.AgreementRepository")
    async def test_invoice_paid_subscription_update_skips_renewal_logic(
        self,
        mock_agr_repo_cls: MagicMock,
        mock_tier_repo_cls: MagicMock,
        mock_agr_svc_cls: MagicMock,
        mock_job_gen_cls: MagicMock,
        mock_renewal_svc_cls: MagicMock,
    ) -> None:
        """CR-4: ``subscription_update`` (mid-cycle add-on) must NOT fire renewal."""
        handler, _session = _make_handler()

        agreement = _make_agreement(
            status=AgreementStatus.ACTIVE.value,
            last_payment_date=datetime(2025, 3, 1, tzinfo=timezone.utc),
            auto_renew=True,
        )
        agr_repo = AsyncMock()
        agr_repo.get_by_stripe_subscription_id.return_value = agreement
        mock_agr_repo_cls.return_value = agr_repo
        mock_tier_repo_cls.return_value = AsyncMock()

        agr_svc = AsyncMock()
        mock_agr_svc_cls.return_value = agr_svc

        job_gen = AsyncMock()
        mock_job_gen_cls.return_value = job_gen

        renewal_svc = AsyncMock()
        mock_renewal_svc_cls.return_value = renewal_svc

        event = _make_event(
            "invoice.paid",
            {
                "subscription": "sub_123",
                "amount_paid": 5000,
                "billing_reason": "subscription_update",
            },
        )

        result = await handler.handle_event(event)

        assert result["status"] == "processed"
        # No renewal proposal, no jobs, no transition
        renewal_svc.generate_proposal.assert_not_called()
        job_gen.generate_jobs.assert_not_called()
        agr_svc.transition_status.assert_not_called()
        # Payment fields still update
        agr_repo.update.assert_called()

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("grins_platform.api.v1.webhooks.ContractRenewalReviewService")
    @patch("grins_platform.api.v1.webhooks.JobGenerator")
    @patch("grins_platform.api.v1.webhooks.AgreementService")
    @patch("grins_platform.api.v1.webhooks.AgreementTierRepository")
    @patch("grins_platform.api.v1.webhooks.AgreementRepository")
    async def test_invoice_paid_manual_skips_renewal_logic(
        self,
        mock_agr_repo_cls: MagicMock,
        mock_tier_repo_cls: MagicMock,
        mock_agr_svc_cls: MagicMock,
        mock_job_gen_cls: MagicMock,
        mock_renewal_svc_cls: MagicMock,
    ) -> None:
        """CR-4: manual Stripe-dashboard invoice on existing agreement is not a renewal."""
        handler, _session = _make_handler()

        agreement = _make_agreement(
            status=AgreementStatus.ACTIVE.value,
            last_payment_date=datetime(2025, 3, 1, tzinfo=timezone.utc),
            auto_renew=True,
        )
        agr_repo = AsyncMock()
        agr_repo.get_by_stripe_subscription_id.return_value = agreement
        mock_agr_repo_cls.return_value = agr_repo
        mock_tier_repo_cls.return_value = AsyncMock()

        agr_svc = AsyncMock()
        mock_agr_svc_cls.return_value = agr_svc

        job_gen = AsyncMock()
        mock_job_gen_cls.return_value = job_gen

        renewal_svc = AsyncMock()
        mock_renewal_svc_cls.return_value = renewal_svc

        event = _make_event(
            "invoice.paid",
            {
                "subscription": "sub_123",
                "amount_paid": 10000,
                "billing_reason": "manual",
            },
        )

        result = await handler.handle_event(event)

        assert result["status"] == "processed"
        renewal_svc.generate_proposal.assert_not_called()
        job_gen.generate_jobs.assert_not_called()
        agr_svc.transition_status.assert_not_called()
        agr_repo.update.assert_called()

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("grins_platform.api.v1.webhooks.JobGenerator")
    @patch("grins_platform.api.v1.webhooks.AgreementService")
    @patch("grins_platform.api.v1.webhooks.AgreementTierRepository")
    @patch("grins_platform.api.v1.webhooks.AgreementRepository")
    async def test_invoice_paid_missing_billing_reason_first_payment_activates_agreement(
        self,
        mock_agr_repo_cls: MagicMock,
        mock_tier_repo_cls: MagicMock,
        mock_agr_svc_cls: MagicMock,
        mock_job_gen_cls: MagicMock,
    ) -> None:
        """CR-4: missing ``billing_reason`` on the FIRST payment still activates PENDING.

        Backward-compat — legacy test fixtures and old Stripe events may not
        include ``billing_reason``. When combined with
        ``last_payment_date is None``, this is treated as the first invoice.
        """
        handler, _session = _make_handler()

        agreement = _make_agreement(
            status=AgreementStatus.PENDING.value,
            last_payment_date=None,
        )
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
    @pytest.mark.parametrize(
        "billing_reason",
        ["subscription_create", "subscription_cycle", "subscription_update", "manual"],
    )
    @patch("grins_platform.api.v1.webhooks.ContractRenewalReviewService")
    @patch("grins_platform.api.v1.webhooks.JobGenerator")
    @patch("grins_platform.api.v1.webhooks.AgreementService")
    @patch("grins_platform.api.v1.webhooks.AgreementTierRepository")
    @patch("grins_platform.api.v1.webhooks.AgreementRepository")
    async def test_invoice_paid_always_updates_payment_fields(
        self,
        mock_agr_repo_cls: MagicMock,
        mock_tier_repo_cls: MagicMock,
        mock_agr_svc_cls: MagicMock,
        mock_job_gen_cls: MagicMock,
        mock_renewal_svc_cls: MagicMock,
        billing_reason: str,
    ) -> None:
        """CR-4: payment fields are ALWAYS refreshed regardless of billing_reason."""
        handler, _session = _make_handler()

        agreement = _make_agreement(
            status=AgreementStatus.ACTIVE.value,
            last_payment_date=datetime(2025, 3, 1, tzinfo=timezone.utc),
            auto_renew=False,
        )
        agr_repo = AsyncMock()
        agr_repo.get_by_stripe_subscription_id.return_value = agreement
        mock_agr_repo_cls.return_value = agr_repo
        mock_tier_repo_cls.return_value = AsyncMock()
        mock_agr_svc_cls.return_value = AsyncMock()
        job_gen = AsyncMock()
        job_gen.generate_jobs.return_value = []
        mock_job_gen_cls.return_value = job_gen
        mock_renewal_svc_cls.return_value = AsyncMock()

        event = _make_event(
            "invoice.paid",
            {
                "subscription": "sub_123",
                "amount_paid": 12345,
                "billing_reason": billing_reason,
            },
        )

        result = await handler.handle_event(event)

        assert result["status"] == "processed"
        update_calls = agr_repo.update.call_args_list
        payment_update_dict = update_calls[-1][0][1]
        assert payment_update_dict["payment_status"] == AgreementPaymentStatus.CURRENT.value
        assert payment_update_dict["last_payment_amount"] == Decimal("123.45")
        assert payment_update_dict["last_payment_date"] is not None

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


# =============================================================================
# checkout.session.completed — SMS & email consent transfer
# Validates: Bugs #18, #19
# =============================================================================


class TestCheckoutConsentTransfer:
    """Tests for SMS and email consent transfer in _handle_checkout_completed."""

    @staticmethod
    def _setup_mocks(
        mock_cust_repo_cls: MagicMock,
        mock_agr_repo_cls: MagicMock,
        mock_tier_repo_cls: MagicMock,
        mock_agr_svc_cls: MagicMock,
        mock_compliance_cls: MagicMock,
        mock_job_gen_cls: MagicMock,
        mock_email_cls: MagicMock,
        *,
        customer_email_opt_in: bool = False,
    ) -> tuple[MagicMock, AsyncMock]:
        """Set up common mocks. Returns (customer, compliance)."""
        customer = MagicMock()
        customer.id = uuid4()
        customer.stripe_customer_id = "cus_consent"
        customer.email_opt_in_at = None
        customer.email_opt_in = customer_email_opt_in
        customer.email_opt_in_source = None
        customer.sms_opt_in = False
        customer.sms_opt_in_at = None
        customer.sms_opt_in_source = None

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

        return customer, compliance

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("grins_platform.api.v1.webhooks.SurchargeCalculator")
    @patch("grins_platform.api.v1.webhooks.EmailService")
    @patch("grins_platform.api.v1.webhooks.JobGenerator")
    @patch("grins_platform.api.v1.webhooks.ComplianceService")
    @patch("grins_platform.api.v1.webhooks.AgreementService")
    @patch("grins_platform.api.v1.webhooks.AgreementTierRepository")
    @patch("grins_platform.api.v1.webhooks.AgreementRepository")
    @patch("grins_platform.api.v1.webhooks.CustomerRepository")
    async def test_sms_consent_true_sets_customer_sms_opt_in(
        self,
        mock_cust_repo_cls: MagicMock,
        mock_agr_repo_cls: MagicMock,
        mock_tier_repo_cls: MagicMock,
        mock_agr_svc_cls: MagicMock,
        mock_compliance_cls: MagicMock,
        mock_job_gen_cls: MagicMock,
        mock_email_cls: MagicMock,
        mock_surcharge_cls: MagicMock,
    ) -> None:
        """SMS consent record with consent_given=True sets customer.sms_opt_in."""
        handler, _session = _make_handler()

        customer, _compliance = self._setup_mocks(
            mock_cust_repo_cls,
            mock_agr_repo_cls,
            mock_tier_repo_cls,
            mock_agr_svc_cls,
            mock_compliance_cls,
            mock_job_gen_cls,
            mock_email_cls,
        )

        mock_breakdown = MagicMock()
        mock_breakdown.total = Decimal("299.00")
        mock_surcharge_cls.calculate.return_value = mock_breakdown

        # Mock SMS consent query: return a record with consent_given=True
        sms_record = MagicMock()
        sms_record.consent_given = True
        mock_sms_result = MagicMock()
        mock_sms_result.scalar_one_or_none.return_value = sms_record
        _session.execute.return_value = mock_sms_result

        consent_token = uuid4()
        event = _make_event(
            "checkout.session.completed",
            {
                "customer_details": {"email": "sms@example.com"},
                "customer": "cus_consent",
                "subscription": "sub_sms1",
                "metadata": {
                    "consent_token": str(consent_token),
                    "package_tier": "essential",
                    "package_type": "residential",
                },
            },
        )

        result = await handler.handle_event(event)

        assert result["status"] == "processed"
        assert customer.sms_opt_in is True
        assert customer.sms_opt_in_source == "stripe_checkout"

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("grins_platform.api.v1.webhooks.SurchargeCalculator")
    @patch("grins_platform.api.v1.webhooks.EmailService")
    @patch("grins_platform.api.v1.webhooks.JobGenerator")
    @patch("grins_platform.api.v1.webhooks.ComplianceService")
    @patch("grins_platform.api.v1.webhooks.AgreementService")
    @patch("grins_platform.api.v1.webhooks.AgreementTierRepository")
    @patch("grins_platform.api.v1.webhooks.AgreementRepository")
    @patch("grins_platform.api.v1.webhooks.CustomerRepository")
    async def test_sms_consent_false_does_not_set_customer_sms_opt_in(
        self,
        mock_cust_repo_cls: MagicMock,
        mock_agr_repo_cls: MagicMock,
        mock_tier_repo_cls: MagicMock,
        mock_agr_svc_cls: MagicMock,
        mock_compliance_cls: MagicMock,
        mock_job_gen_cls: MagicMock,
        mock_email_cls: MagicMock,
        mock_surcharge_cls: MagicMock,
    ) -> None:
        """SMS consent record with consent_given=False keeps sms_opt_in=False."""
        handler, _session = _make_handler()

        customer, _compliance = self._setup_mocks(
            mock_cust_repo_cls,
            mock_agr_repo_cls,
            mock_tier_repo_cls,
            mock_agr_svc_cls,
            mock_compliance_cls,
            mock_job_gen_cls,
            mock_email_cls,
        )

        mock_breakdown = MagicMock()
        mock_breakdown.total = Decimal("299.00")
        mock_surcharge_cls.calculate.return_value = mock_breakdown

        # Mock SMS consent query: no matching record (consent_given=False filtered out)
        mock_sms_result = MagicMock()
        mock_sms_result.scalar_one_or_none.return_value = None
        _session.execute.return_value = mock_sms_result

        consent_token = uuid4()
        event = _make_event(
            "checkout.session.completed",
            {
                "customer_details": {"email": "sms@example.com"},
                "customer": "cus_consent",
                "subscription": "sub_sms2",
                "metadata": {
                    "consent_token": str(consent_token),
                    "package_tier": "essential",
                    "package_type": "residential",
                },
            },
        )

        result = await handler.handle_event(event)

        assert result["status"] == "processed"
        assert customer.sms_opt_in is False

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("grins_platform.api.v1.webhooks.SurchargeCalculator")
    @patch("grins_platform.api.v1.webhooks.EmailService")
    @patch("grins_platform.api.v1.webhooks.JobGenerator")
    @patch("grins_platform.api.v1.webhooks.ComplianceService")
    @patch("grins_platform.api.v1.webhooks.AgreementService")
    @patch("grins_platform.api.v1.webhooks.AgreementTierRepository")
    @patch("grins_platform.api.v1.webhooks.AgreementRepository")
    @patch("grins_platform.api.v1.webhooks.CustomerRepository")
    async def test_no_consent_token_does_not_set_sms(
        self,
        mock_cust_repo_cls: MagicMock,
        mock_agr_repo_cls: MagicMock,
        mock_tier_repo_cls: MagicMock,
        mock_agr_svc_cls: MagicMock,
        mock_compliance_cls: MagicMock,
        mock_job_gen_cls: MagicMock,
        mock_email_cls: MagicMock,
        mock_surcharge_cls: MagicMock,
    ) -> None:
        """No consent_token in metadata — SMS opt-in stays False, no crash."""
        handler, _session = _make_handler()

        customer, _compliance = self._setup_mocks(
            mock_cust_repo_cls,
            mock_agr_repo_cls,
            mock_tier_repo_cls,
            mock_agr_svc_cls,
            mock_compliance_cls,
            mock_job_gen_cls,
            mock_email_cls,
        )

        mock_breakdown = MagicMock()
        mock_breakdown.total = Decimal("299.00")
        mock_surcharge_cls.calculate.return_value = mock_breakdown

        event = _make_event(
            "checkout.session.completed",
            {
                "customer_details": {"email": "sms@example.com"},
                "customer": "cus_consent",
                "subscription": "sub_sms3",
                "metadata": {
                    "package_tier": "essential",
                    "package_type": "residential",
                    # No consent_token
                },
            },
        )

        result = await handler.handle_event(event)

        assert result["status"] == "processed"
        assert customer.sms_opt_in is False

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("grins_platform.api.v1.webhooks.SurchargeCalculator")
    @patch("grins_platform.api.v1.webhooks.EmailService")
    @patch("grins_platform.api.v1.webhooks.JobGenerator")
    @patch("grins_platform.api.v1.webhooks.ComplianceService")
    @patch("grins_platform.api.v1.webhooks.AgreementService")
    @patch("grins_platform.api.v1.webhooks.AgreementTierRepository")
    @patch("grins_platform.api.v1.webhooks.AgreementRepository")
    @patch("grins_platform.api.v1.webhooks.CustomerRepository")
    async def test_email_consent_true_sets_email_opt_in(
        self,
        mock_cust_repo_cls: MagicMock,
        mock_agr_repo_cls: MagicMock,
        mock_tier_repo_cls: MagicMock,
        mock_agr_svc_cls: MagicMock,
        mock_compliance_cls: MagicMock,
        mock_job_gen_cls: MagicMock,
        mock_email_cls: MagicMock,
        mock_surcharge_cls: MagicMock,
    ) -> None:
        """email_marketing_consent=true in metadata sets email_opt_in=True."""
        handler, _session = _make_handler()

        customer, _compliance = self._setup_mocks(
            mock_cust_repo_cls,
            mock_agr_repo_cls,
            mock_tier_repo_cls,
            mock_agr_svc_cls,
            mock_compliance_cls,
            mock_job_gen_cls,
            mock_email_cls,
        )

        mock_breakdown = MagicMock()
        mock_breakdown.total = Decimal("299.00")
        mock_surcharge_cls.calculate.return_value = mock_breakdown

        event = _make_event(
            "checkout.session.completed",
            {
                "customer_details": {"email": "email@example.com"},
                "customer": "cus_consent",
                "subscription": "sub_email1",
                "metadata": {
                    "package_tier": "essential",
                    "package_type": "residential",
                    "email_marketing_consent": "true",
                },
            },
        )

        result = await handler.handle_event(event)

        assert result["status"] == "processed"
        assert customer.email_opt_in is True
        assert customer.email_opt_in_source == "checkout_marketing_consent"

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("grins_platform.api.v1.webhooks.SurchargeCalculator")
    @patch("grins_platform.api.v1.webhooks.EmailService")
    @patch("grins_platform.api.v1.webhooks.JobGenerator")
    @patch("grins_platform.api.v1.webhooks.ComplianceService")
    @patch("grins_platform.api.v1.webhooks.AgreementService")
    @patch("grins_platform.api.v1.webhooks.AgreementTierRepository")
    @patch("grins_platform.api.v1.webhooks.AgreementRepository")
    @patch("grins_platform.api.v1.webhooks.CustomerRepository")
    async def test_email_consent_false_keeps_email_opt_in_false(
        self,
        mock_cust_repo_cls: MagicMock,
        mock_agr_repo_cls: MagicMock,
        mock_tier_repo_cls: MagicMock,
        mock_agr_svc_cls: MagicMock,
        mock_compliance_cls: MagicMock,
        mock_job_gen_cls: MagicMock,
        mock_email_cls: MagicMock,
        mock_surcharge_cls: MagicMock,
    ) -> None:
        """email_marketing_consent=false keeps email_opt_in=False."""
        handler, _session = _make_handler()

        customer, _compliance = self._setup_mocks(
            mock_cust_repo_cls,
            mock_agr_repo_cls,
            mock_tier_repo_cls,
            mock_agr_svc_cls,
            mock_compliance_cls,
            mock_job_gen_cls,
            mock_email_cls,
        )

        mock_breakdown = MagicMock()
        mock_breakdown.total = Decimal("299.00")
        mock_surcharge_cls.calculate.return_value = mock_breakdown

        event = _make_event(
            "checkout.session.completed",
            {
                "customer_details": {"email": "email@example.com"},
                "customer": "cus_consent",
                "subscription": "sub_email2",
                "metadata": {
                    "package_tier": "essential",
                    "package_type": "residential",
                    "email_marketing_consent": "false",
                },
            },
        )

        result = await handler.handle_event(event)

        assert result["status"] == "processed"
        assert customer.email_opt_in is False
