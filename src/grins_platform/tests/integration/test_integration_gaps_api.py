"""Integration tests for backend-frontend integration gaps.

End-to-end API flows covering:
- Pre-checkout consent TCPA fix (20.1)
- Checkout session with surcharges (20.2)
- Lead creation with new fields and duplicate detection (20.3)
- Inbound SMS opt-out processing (20.4)
- Webhook handler with new fields (20.5)

Validates: Requirements 1.1-1.4, 2.2-2.5, 3.1-3.14, 5.2, 6.1-6.4,
7.1-7.5, 8.1-8.5
"""

from __future__ import annotations

import json
import uuid
from collections.abc import AsyncGenerator
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from grins_platform.api.v1.dependencies import get_db_session
from grins_platform.api.v1.leads import _get_lead_service
from grins_platform.api.v1.webhooks import StripeWebhookHandler
from grins_platform.exceptions import ConsentValidationError, DuplicateLeadError
from grins_platform.main import app
from grins_platform.schemas.lead import LeadSubmissionResponse
from grins_platform.services.surcharge_calculator import SurchargeBreakdown

# Patch targets
_COMPLIANCE_SVC = "grins_platform.api.v1.onboarding.ComplianceService"
_CHECKOUT_SVC_CLASS = "grins_platform.api.v1.checkout.CheckoutService"
_TWILIO_VALIDATE = "grins_platform.api.v1.webhooks.validate_twilio_signature"
_SMS_SERVICE = "grins_platform.api.v1.webhooks.SMSService"
_STRIPE_CONSTRUCT = "stripe.Webhook.construct_event"
_STRIPE_SETTINGS = "grins_platform.api.v1.webhooks.StripeSettings"
_WEBHOOK_HANDLER = "grins_platform.api.v1.webhooks.StripeWebhookHandler"


def _mock_db() -> AsyncMock:
    session = AsyncMock()
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    return session


@pytest_asyncio.fixture
async def public_client() -> AsyncGenerator[AsyncClient, None]:
    """Client without auth for public endpoints."""
    db = _mock_db()
    app.dependency_overrides[get_db_session] = lambda: db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def raw_client() -> AsyncGenerator[AsyncClient, None]:
    """Client without any dependency overrides (for webhook tests)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# =========================================================================
# 20.1 — Pre-checkout consent TCPA fix
# =========================================================================


@pytest.mark.integration
class TestPreCheckoutConsentTCPAFix:
    """Integration tests for pre-checkout consent TCPA fix.

    Validates: Requirements 1.1, 1.2, 1.3, 1.4, 2.4
    """

    @pytest.mark.asyncio
    async def test_sms_false_terms_true_returns_201(
        self,
        public_client: AsyncClient,
    ) -> None:
        """sms_consent=false, terms_accepted=true → 201."""
        consent_token = uuid.uuid4()
        mock_compliance = AsyncMock()
        mock_compliance.process_pre_checkout_consent = AsyncMock(
            return_value=(consent_token, MagicMock(), MagicMock()),
        )

        with patch(_COMPLIANCE_SVC, return_value=mock_compliance):
            response = await public_client.post(
                "/api/v1/onboarding/pre-checkout-consent",
                json={
                    "sms_consent": False,
                    "terms_accepted": True,
                    "phone": "6125551234",
                },
            )

        assert response.status_code == 201
        body = response.json()
        assert body["consent_token"] == str(consent_token)

        kw = mock_compliance.process_pre_checkout_consent.call_args.kwargs
        assert kw["sms_consent"] is False
        assert kw["terms_accepted"] is True

    @pytest.mark.asyncio
    async def test_terms_false_returns_422(
        self,
        public_client: AsyncClient,
    ) -> None:
        """terms_accepted=false → 422."""
        mock_compliance = AsyncMock()
        mock_compliance.process_pre_checkout_consent = AsyncMock(
            side_effect=ConsentValidationError(["terms_accepted"]),
        )

        with patch(_COMPLIANCE_SVC, return_value=mock_compliance):
            response = await public_client.post(
                "/api/v1/onboarding/pre-checkout-consent",
                json={
                    "sms_consent": False,
                    "terms_accepted": False,
                    "phone": "6125551234",
                },
            )

        assert response.status_code == 422
        body = response.json()
        assert "terms_accepted" in str(body)

    @pytest.mark.asyncio
    async def test_email_marketing_consent_passed(
        self,
        public_client: AsyncClient,
    ) -> None:
        """email_marketing_consent forwarded to ComplianceService."""
        consent_token = uuid.uuid4()
        mock_compliance = AsyncMock()
        mock_compliance.process_pre_checkout_consent = AsyncMock(
            return_value=(consent_token, MagicMock(), MagicMock()),
        )

        with patch(_COMPLIANCE_SVC, return_value=mock_compliance):
            response = await public_client.post(
                "/api/v1/onboarding/pre-checkout-consent",
                json={
                    "sms_consent": True,
                    "terms_accepted": True,
                    "phone": "6125551234",
                    "email_marketing_consent": True,
                },
            )

        assert response.status_code == 201
        kw = mock_compliance.process_pre_checkout_consent.call_args.kwargs
        assert kw["email_marketing_consent"] is True


# =========================================================================
# 20.2 — Checkout session with surcharges
# =========================================================================


@pytest.mark.integration
class TestCheckoutSessionWithSurcharges:
    """Integration tests for checkout session with surcharges.

    Validates: Requirements 3.1, 3.2, 3.11, 3.12, 4.4
    """

    @pytest.mark.asyncio
    async def test_surcharges_pass_zone_and_lake(
        self,
        public_client: AsyncClient,
    ) -> None:
        """zone_count=12, has_lake_pump=true → passed to service."""
        mock_svc = AsyncMock()
        mock_svc.create_checkout_session = AsyncMock(
            return_value="https://checkout.stripe.com/test",
        )

        with patch(_CHECKOUT_SVC_CLASS, return_value=mock_svc):
            response = await public_client.post(
                "/api/v1/checkout/create-session",
                json={
                    "package_tier": "essential-residential",
                    "package_type": "residential",
                    "consent_token": str(uuid.uuid4()),
                    "zone_count": 12,
                    "has_lake_pump": True,
                    "email_marketing_consent": True,
                },
            )

        assert response.status_code == 200
        body = response.json()
        assert body["checkout_url"] == "https://checkout.stripe.com/test"

        kw = mock_svc.create_checkout_session.call_args.kwargs
        assert kw["zone_count"] == 12
        assert kw["has_lake_pump"] is True
        assert kw["email_marketing_consent"] is True

    @pytest.mark.asyncio
    async def test_no_surcharges_base_only(
        self,
        public_client: AsyncClient,
    ) -> None:
        """zone_count=5, has_lake_pump=false → base only."""
        mock_svc = AsyncMock()
        mock_svc.create_checkout_session = AsyncMock(
            return_value="https://checkout.stripe.com/base",
        )

        with patch(_CHECKOUT_SVC_CLASS, return_value=mock_svc):
            response = await public_client.post(
                "/api/v1/checkout/create-session",
                json={
                    "package_tier": "essential-residential",
                    "package_type": "residential",
                    "consent_token": str(uuid.uuid4()),
                    "zone_count": 5,
                    "has_lake_pump": False,
                },
            )

        assert response.status_code == 200
        kw = mock_svc.create_checkout_session.call_args.kwargs
        assert kw["zone_count"] == 5
        assert kw["has_lake_pump"] is False

    @pytest.mark.asyncio
    async def test_winterization_only_tier(
        self,
        public_client: AsyncClient,
    ) -> None:
        """Winterization-only tier passes through."""
        mock_svc = AsyncMock()
        mock_svc.create_checkout_session = AsyncMock(
            return_value="https://checkout.stripe.com/winter",
        )

        with patch(_CHECKOUT_SVC_CLASS, return_value=mock_svc):
            response = await public_client.post(
                "/api/v1/checkout/create-session",
                json={
                    "package_tier": "essential-residential",
                    "package_type": "residential",
                    "consent_token": str(uuid.uuid4()),
                    "zone_count": 15,
                    "has_lake_pump": True,
                },
            )

        assert response.status_code == 200


# =========================================================================
# 20.3 — Lead creation with new fields and duplicate detection
# =========================================================================


@pytest.mark.integration
class TestLeadNewFieldsAndDuplicateDetection:
    """Integration tests for lead creation with new fields.

    Validates: Requirements 2.2, 5.2, 6.1-6.4, 7.1, 7.3, 7.4
    """

    @pytest.mark.asyncio
    async def test_lead_with_new_fields(self) -> None:
        """POST /leads with new consent fields → 201."""
        lead_id = uuid.uuid4()
        mock_service = AsyncMock()
        mock_service.submit_lead = AsyncMock(
            return_value=LeadSubmissionResponse(
                success=True,
                message="Thank you!",
                lead_id=lead_id,
            ),
        )

        app.dependency_overrides[_get_lead_service] = lambda: mock_service
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport,
                base_url="http://test",
            ) as ac:
                response = await ac.post(
                    "/api/v1/leads",
                    json={
                        "name": "Test User",
                        "phone": "6125559876",
                        "zip_code": "55424",
                        "situation": "new_system",
                        "email": "test@example.com",
                        "sms_consent": True,
                        "email_marketing_consent": True,
                        "page_url": "https://grins.com/residential",
                        "consent_ip": "192.168.1.1",
                        "consent_user_agent": "Mozilla/5.0",
                        "consent_language_version": "v1.0",
                    },
                )
        finally:
            app.dependency_overrides.pop(_get_lead_service, None)

        assert response.status_code == 201
        body = response.json()
        assert body["success"] is True
        assert body["lead_id"] == str(lead_id)

        data = mock_service.submit_lead.call_args[0][0]
        assert data.email_marketing_consent is True
        assert data.page_url == "https://grins.com/residential"
        assert data.consent_ip == "192.168.1.1"
        assert data.consent_user_agent == "Mozilla/5.0"
        assert data.consent_language_version == "v1.0"

    @pytest.mark.asyncio
    async def test_duplicate_phone_returns_409(self) -> None:
        """Same phone within 24h → 409."""
        mock_service = AsyncMock()
        mock_service.submit_lead = AsyncMock(
            side_effect=DuplicateLeadError(),
        )

        app.dependency_overrides[_get_lead_service] = lambda: mock_service
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport,
                base_url="http://test",
            ) as ac:
                response = await ac.post(
                    "/api/v1/leads",
                    json={
                        "name": "Dup User",
                        "phone": "6125551111",
                        "zip_code": "55424",
                        "situation": "repair",
                    },
                )
        finally:
            app.dependency_overrides.pop(_get_lead_service, None)

        assert response.status_code == 409
        assert response.json()["detail"] == "duplicate_lead"

    @pytest.mark.asyncio
    async def test_duplicate_email_returns_409(self) -> None:
        """Same email within 24h → 409."""
        mock_service = AsyncMock()
        mock_service.submit_lead = AsyncMock(
            side_effect=DuplicateLeadError(),
        )

        app.dependency_overrides[_get_lead_service] = lambda: mock_service
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport,
                base_url="http://test",
            ) as ac:
                response = await ac.post(
                    "/api/v1/leads",
                    json={
                        "name": "Email Dup",
                        "phone": "6125552222",
                        "zip_code": "55424",
                        "situation": "new_system",
                        "email": "dup@example.com",
                    },
                )
        finally:
            app.dependency_overrides.pop(_get_lead_service, None)

        assert response.status_code == 409
        assert response.json()["detail"] == "duplicate_lead"


# =========================================================================
# 20.4 — Inbound SMS opt-out processing
# =========================================================================


@pytest.mark.integration
class TestInboundSMSOptOutProcessing:
    """Integration tests for inbound SMS opt-out processing.

    Validates: Requirements 8.1-8.5
    """

    @pytest.mark.asyncio
    async def test_stop_keyword_triggers_opt_out(
        self,
        raw_client: AsyncClient,
    ) -> None:
        """Body='STOP' → opt-out processed."""
        mock_sms = AsyncMock()
        mock_sms.handle_inbound = AsyncMock(
            return_value={"action": "opt_out_processed", "keyword": "stop"},
        )

        with (
            patch(_TWILIO_VALIDATE, return_value=True),
            patch(_SMS_SERVICE, return_value=mock_sms),
        ):
            response = await raw_client.post(
                "/api/v1/webhooks/twilio-inbound",
                data={
                    "From": "+16125551234",
                    "Body": "STOP",
                    "MessageSid": "SM_test_123",
                },
            )

        assert response.status_code == 200
        assert "Response" in response.text
        mock_sms.handle_inbound.assert_called_once_with(
            "+16125551234",
            "STOP",
            "SM_test_123",
        )

    @pytest.mark.asyncio
    async def test_informal_opt_out_flags_for_admin(
        self,
        raw_client: AsyncClient,
    ) -> None:
        """Body='stop texting me' → flagged for admin review."""
        mock_sms = AsyncMock()
        mock_sms.handle_inbound = AsyncMock(
            return_value={"action": "flagged_for_review"},
        )

        with (
            patch(_TWILIO_VALIDATE, return_value=True),
            patch(_SMS_SERVICE, return_value=mock_sms),
        ):
            response = await raw_client.post(
                "/api/v1/webhooks/twilio-inbound",
                data={
                    "From": "+16125559999",
                    "Body": "stop texting me",
                    "MessageSid": "SM_test_456",
                },
            )

        assert response.status_code == 200
        mock_sms.handle_inbound.assert_called_once()

    @pytest.mark.asyncio
    async def test_invalid_twilio_signature_returns_403(
        self,
        raw_client: AsyncClient,
    ) -> None:
        """Invalid Twilio signature → 403."""
        with patch(_TWILIO_VALIDATE, return_value=False):
            response = await raw_client.post(
                "/api/v1/webhooks/twilio-inbound",
                data={
                    "From": "+16125551234",
                    "Body": "STOP",
                    "MessageSid": "SM_test_789",
                },
            )

        assert response.status_code == 403


# =========================================================================
# 20.5 — Webhook handler with new fields
# =========================================================================


@pytest.mark.integration
class TestWebhookHandlerNewFields:
    """Integration tests for webhook handler with new fields.

    Validates: Requirements 3.14, 2.5
    """

    @pytest.mark.asyncio
    async def test_checkout_completed_surcharge_metadata(
        self,
        raw_client: AsyncClient,
    ) -> None:
        """Webhook routes event with surcharge metadata."""
        mock_event: dict[str, Any] = {
            "id": f"evt_{uuid.uuid4().hex[:24]}",
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_test_surcharge",
                    "metadata": {
                        "zone_count": "15",
                        "has_lake_pump": "true",
                        "email_marketing_consent": "true",
                    },
                },
            },
        }

        mock_settings = MagicMock()
        mock_settings.stripe_webhook_secret = "whsec_test"
        mock_handler = AsyncMock()
        mock_handler.handle_event = AsyncMock(
            return_value={"status": "processed"},
        )

        with (
            patch(_STRIPE_SETTINGS, return_value=mock_settings),
            patch(_STRIPE_CONSTRUCT, return_value=mock_event),
            patch(_WEBHOOK_HANDLER, return_value=mock_handler),
        ):
            response = await raw_client.post(
                "/api/v1/webhooks/stripe",
                content=json.dumps(mock_event),
                headers={
                    "stripe-signature": "t=123,v1=abc",
                    "content-type": "application/json",
                },
            )

        assert response.status_code == 200
        mock_handler.handle_event.assert_called_once()

    @pytest.mark.asyncio
    async def test_checkout_completed_extracts_metadata(
        self,
    ) -> None:
        """Handler extracts zone_count, has_lake_pump, email_marketing_consent."""
        mock_session = AsyncMock()
        mock_session.flush = AsyncMock()
        mock_session.refresh = AsyncMock()

        handler = StripeWebhookHandler(mock_session)

        mock_customer = MagicMock()
        mock_customer.id = uuid.uuid4()
        mock_customer.stripe_customer_id = None
        mock_customer.email_opt_in_at = None
        mock_customer.email_opt_in = False

        mock_tier = MagicMock()
        mock_tier.id = uuid.uuid4()
        mock_tier.name = "Standard Residential"
        mock_tier.slug = "standard-residential"
        mock_tier.annual_price = Decimal("499.00")
        mock_tier.stripe_price_id = "price_123"

        mock_agreement = MagicMock()
        mock_agreement.id = uuid.uuid4()
        mock_agreement.agreement_number = "AGR-2026-001"
        mock_agreement.property_id = None
        mock_agreement.jobs = []

        event_data: dict[str, Any] = {
            "id": "evt_test",
            "data": {
                "object": {
                    "customer_details": {
                        "email": "test@example.com",
                        "name": "Test User",
                        "phone": "+16125551234",
                    },
                    "customer_email": "test@example.com",
                    "customer": "cus_test",
                    "subscription": "sub_test",
                    "metadata": {
                        "consent_token": str(uuid.uuid4()),
                        "package_tier": "standard-residential",
                        "package_type": "residential",
                        "zone_count": "15",
                        "has_lake_pump": "true",
                        "email_marketing_consent": "true",
                    },
                },
            },
        }
        mock_event = MagicMock()
        mock_event.__getitem__ = lambda _s, key: event_data[key]

        mock_agr_repo = AsyncMock()
        mock_agr_repo.update = AsyncMock(return_value=mock_agreement)

        mock_cust_repo = AsyncMock()
        mock_cust_repo.find_by_email = AsyncMock(
            return_value=[mock_customer],
        )

        mock_tier_repo = AsyncMock()
        mock_tier_repo.get_by_slug_and_type = AsyncMock(
            return_value=mock_tier,
        )

        mock_agr_svc = AsyncMock()
        mock_agr_svc.create_agreement = AsyncMock(
            return_value=mock_agreement,
        )

        mock_compliance = AsyncMock()
        mock_compliance.link_orphaned_records = AsyncMock()
        mock_compliance.create_disclosure = AsyncMock()

        mock_email = MagicMock()
        mock_email.send_confirmation_email = MagicMock(
            return_value={
                "content": "test",
                "sent_via": "email",
                "sent": True,
            },
        )
        mock_email.send_welcome_email = MagicMock(return_value={})

        mock_job_gen = AsyncMock()
        mock_job_gen.generate_jobs = AsyncMock(return_value=[])

        _wh = "grins_platform.api.v1.webhooks"
        with (
            patch(f"{_wh}.CustomerRepository", return_value=mock_cust_repo),
            patch(f"{_wh}.AgreementRepository", return_value=mock_agr_repo),
            patch(
                f"{_wh}.AgreementTierRepository",
                return_value=mock_tier_repo,
            ),
            patch(f"{_wh}.AgreementService", return_value=mock_agr_svc),
            patch(f"{_wh}.ComplianceService", return_value=mock_compliance),
            patch(f"{_wh}.EmailService", return_value=mock_email),
            patch(f"{_wh}.JobGenerator", return_value=mock_job_gen),
            patch(f"{_wh}.SurchargeCalculator") as mock_sc,
        ):
            mock_sc.calculate = MagicMock(
                return_value=SurchargeBreakdown(
                    base_price=Decimal("499.00"),
                    zone_surcharge=Decimal("90.00"),
                    lake_pump_surcharge=Decimal("50.00"),
                ),
            )

            handler.repo = AsyncMock()
            await handler._handle_checkout_completed(mock_event)

        # Verify agreement updated with surcharge fields
        mock_agr_repo.update.assert_called_once()
        update_data = mock_agr_repo.update.call_args[0][1]
        assert update_data["zone_count"] == 15
        assert update_data["has_lake_pump"] is True
        assert update_data["base_price"] == Decimal("499.00")

        # Verify email_marketing_consent carried to customer
        assert mock_customer.email_opt_in is True
