"""Functional tests for marketing and remaining operations.

Tests lead source aggregation, chat context with service info,
voice webhook processing, Stripe PaymentIntent creation,
and cookie-based authentication.

Validates: Requirements 63.8, 43.7, 44.8, 56.8, 71.7
"""

from __future__ import annotations

import json
from datetime import date
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from grins_platform.api.v1.auth import (
    ACCESS_TOKEN_COOKIE,
    REFRESH_TOKEN_COOKIE,
    login,
    refresh,
)
from grins_platform.api.v1.auth_dependencies import get_current_user
from grins_platform.api.v1.voice import voice_webhook
from grins_platform.exceptions import MergeConflictError
from grins_platform.models.enums import UserRole
from grins_platform.schemas.auth import LoginRequest
from grins_platform.schemas.marketing import (
    FunnelStage,
    LeadAnalyticsResponse,
    LeadSourceAnalytics,
)
from grins_platform.services.chat_service import (
    GRINS_SYSTEM_CONTEXT,
    ChatResponse,
    ChatService,
)
from grins_platform.services.customer_service import CustomerService
from grins_platform.services.marketing_service import MarketingService

# =============================================================================
# Helpers
# =============================================================================


def _mock_customer(**overrides: Any) -> MagicMock:
    """Create a mock Customer."""
    c = MagicMock()
    c.id = overrides.get("id", uuid4())
    c.first_name = overrides.get("first_name", "John")
    c.last_name = overrides.get("last_name", "Doe")
    c.email = overrides.get("email", "john@example.com")
    c.phone = overrides.get("phone", "6125551234")
    c.stripe_customer_id = overrides.get(
        "stripe_customer_id",
        "cus_test123",
    )
    return c


def _build_source_analytics(
    sources: list[tuple[str, int, int]],
) -> list[LeadSourceAnalytics]:
    """Build LeadSourceAnalytics from (source, count, converted)."""
    return [
        LeadSourceAnalytics(
            source=src,
            count=cnt,
            converted=conv,
            conversion_rate=(round((conv / cnt) * 100, 2) if cnt > 0 else 0.0),
        )
        for src, cnt, conv in sources
    ]


# =============================================================================
# 1. Lead Source Aggregation — Validates: Requirement 63.8
# =============================================================================


@pytest.mark.functional
@pytest.mark.asyncio
class TestLeadSourceAggregationWorkflow:
    """Test lead source analytics aggregation from real lead data.

    Validates: Requirement 63.8
    """

    async def test_lead_source_aggregation_as_user_would_experience(
        self,
    ) -> None:
        """Lead analytics aggregates sources, funnel, and metrics."""
        service = MarketingService()

        sources = _build_source_analytics(
            [
                ("website", 20, 5),
                ("google_ad", 15, 3),
                ("referral", 10, 4),
                ("phone_call", 5, 2),
            ],
        )
        funnel = [
            FunnelStage(stage="Total Leads", count=50),
            FunnelStage(stage="Contacted", count=35),
            FunnelStage(stage="Qualified", count=20),
            FunnelStage(stage="Converted", count=14),
        ]

        with (
            patch.object(
                service,
                "_get_source_analytics",
                return_value=sources,
            ),
            patch.object(
                service,
                "_get_avg_conversion_time",
                return_value=72.5,
            ),
            patch.object(
                service,
                "_get_funnel",
                return_value=funnel,
            ),
        ):
            result = await service.get_lead_analytics(
                db=AsyncMock(),
                date_from=date(2025, 1, 1),
                date_to=date(2025, 6, 30),
            )

        assert isinstance(result, LeadAnalyticsResponse)
        assert result.total_leads == 50
        assert result.conversion_rate == 28.0
        assert result.avg_time_to_conversion_hours == 72.5
        assert result.top_source == "website"
        assert len(result.sources) == 4
        assert result.sources[0].source == "website"
        assert result.sources[0].count == 20
        assert result.sources[0].converted == 5

        # Verify funnel stages
        assert len(result.funnel) == 4
        assert result.funnel[0].stage == "Total Leads"
        assert result.funnel[0].count == 50
        assert result.funnel[3].stage == "Converted"
        assert result.funnel[3].count == 14

    async def test_lead_source_aggregation_empty_data(
        self,
    ) -> None:
        """Lead analytics handles zero leads without errors."""
        service = MarketingService()

        with (
            patch.object(
                service,
                "_get_source_analytics",
                return_value=[],
            ),
            patch.object(
                service,
                "_get_avg_conversion_time",
                return_value=None,
            ),
            patch.object(
                service,
                "_get_funnel",
                return_value=[
                    FunnelStage(stage="Total Leads", count=0),
                    FunnelStage(stage="Contacted", count=0),
                    FunnelStage(stage="Qualified", count=0),
                    FunnelStage(stage="Converted", count=0),
                ],
            ),
        ):
            result = await service.get_lead_analytics(
                db=AsyncMock(),
                date_from=date(2025, 1, 1),
                date_to=date(2025, 3, 31),
            )

        assert result.total_leads == 0
        assert result.conversion_rate == 0.0
        assert result.top_source is None
        assert result.avg_time_to_conversion_hours is None


# =============================================================================
# 2. Chat Context with Service Info — Validates: Requirement 43.7
# =============================================================================


@pytest.mark.functional
@pytest.mark.asyncio
class TestChatContextWorkflow:
    """Test chat context includes service information and pricing.

    Validates: Requirement 43.7
    """

    async def test_chat_context_includes_service_info(
        self,
    ) -> None:
        """Chat system context contains irrigation service info."""
        context_lower = GRINS_SYSTEM_CONTEXT.lower()
        assert "irrigation" in context_lower
        assert "pricing" in context_lower
        assert "service" in context_lower
        assert "schedule" in context_lower

    async def test_chat_sends_context_to_openai(
        self,
    ) -> None:
        """Chat service sends system context to OpenAI."""
        redis = AsyncMock()
        redis.get.return_value = None

        service = ChatService(
            redis_client=redis,
            openai_api_key="test-key",
        )

        captured_messages: list[dict[str, str]] = []

        async def _mock_call_openai(
            messages: list[dict[str, str]],
        ) -> str:
            captured_messages.extend(messages)
            return "We offer sprinkler installation."

        with patch.object(
            service,
            "_call_openai",
            side_effect=_mock_call_openai,
        ):
            result = await service.handle_public_message(
                db=AsyncMock(),
                session_id="test-session-123",
                message="What services do you offer?",
            )

        assert isinstance(result, ChatResponse)
        assert result.session_id == "test-session-123"
        assert result.escalated is False

        # Verify system context was sent as first message
        assert len(captured_messages) >= 2
        system_msg = captured_messages[0]
        assert system_msg["role"] == "system"
        assert "irrigation" in system_msg["content"].lower()
        assert "pricing" in system_msg["content"].lower()

        # Verify user message was included
        user_msg = captured_messages[1]
        assert user_msg["role"] == "user"
        assert "What services" in user_msg["content"]

    async def test_chat_escalation_creates_lead(
        self,
    ) -> None:
        """Escalation request creates a lead with info."""
        redis = AsyncMock()
        history = [
            {"role": "user", "content": "My name is Sarah Johnson"},
            {"role": "assistant", "content": "Hi Sarah!"},
            {"role": "user", "content": "My phone is 6125559876"},
            {"role": "assistant", "content": "Got it!"},
        ]
        redis.get.return_value = json.dumps(history)

        service = ChatService(
            redis_client=redis,
            openai_api_key="test-key",
        )

        db = AsyncMock()
        db.add = MagicMock()
        db.flush = AsyncMock()

        result = await service.handle_public_message(
            db=db,
            session_id="escalation-session",
            message="I want to speak to a real person",
        )

        assert result.escalated is True
        msg_lower = result.message.lower()
        assert "follow up" in msg_lower or "representative" in msg_lower

        # Verify Lead was created via db.add
        assert db.add.call_count >= 1


# =============================================================================
# 3. Voice Webhook Processing — Validates: Requirement 44.8
# =============================================================================


@pytest.mark.functional
@pytest.mark.asyncio
class TestVoiceWebhookWorkflow:
    """Test voice webhook processes call data and creates leads.

    Validates: Requirement 44.8
    """

    async def test_voice_webhook_processes_call_data(
        self,
    ) -> None:
        """Voice webhook processes Vapi call event and returns ok."""
        mock_request = AsyncMock()
        mock_request.json.return_value = {
            "type": "call.ended",
            "call": {
                "id": "call_abc123",
                "customer": {"number": "+16125551234"},
                "transcript": "Customer wants sprinkler repair",
            },
            "assistant": {
                "collected_data": {
                    "name": "Mike Wilson",
                    "phone": "6125551234",
                    "service_needed": "sprinkler repair",
                    "preferred_callback": "morning",
                },
            },
        }

        response = await voice_webhook(request=mock_request)

        assert response.status == "ok"
        assert "call.ended" in (response.message or "")

    async def test_voice_webhook_handles_unknown_event(
        self,
    ) -> None:
        """Voice webhook handles unknown event types gracefully."""
        mock_request = AsyncMock()
        mock_request.json.return_value = {
            "type": "call.started",
            "call": {"id": "call_xyz789"},
        }

        response = await voice_webhook(request=mock_request)

        assert response.status == "ok"
        assert "call.started" in (response.message or "")

    async def test_voice_webhook_handles_malformed_data(
        self,
    ) -> None:
        """Voice webhook returns error for malformed JSON."""
        mock_request = AsyncMock()
        mock_request.json.side_effect = ValueError("Invalid JSON")

        response = await voice_webhook(request=mock_request)

        assert response.status == "error"
        assert response.message is not None


# =============================================================================
# 4. Stripe PaymentIntent Creation — Validates: Requirement 56.8
# =============================================================================


@pytest.mark.functional
@pytest.mark.asyncio
class TestStripePaymentIntentWorkflow:
    """Test Stripe PaymentIntent creation with test mode.

    Validates: Requirement 56.8
    """

    async def test_stripe_payment_intent_creation(
        self,
    ) -> None:
        """Charging a customer creates a Stripe PaymentIntent."""
        customer_id = uuid4()
        mock_customer = _mock_customer(
            id=customer_id,
            stripe_customer_id="cus_test_abc123",
        )

        repo = AsyncMock()
        repo.get_by_id.return_value = mock_customer

        service = CustomerService(repository=repo)

        mock_stripe_customer = {
            "id": "cus_test_abc123",
            "invoice_settings": {
                "default_payment_method": "pm_test_card_visa",
            },
        }

        mock_intent = {
            "id": "pi_test_intent_123",
            "status": "succeeded",
            "amount": 15000,
            "currency": "usd",
        }

        mock_settings = MagicMock()
        mock_settings.is_configured = True
        mock_settings.stripe_secret_key = "sk_test_fake_key"

        stripe_mod = "grins_platform.services.customer_service"

        with (
            patch(
                f"{stripe_mod}.StripeSettings",
                return_value=mock_settings,
            ),
            patch(
                f"{stripe_mod}.stripe.Customer.retrieve",
                return_value=mock_stripe_customer,
            ),
            patch(
                f"{stripe_mod}.stripe.PaymentIntent.create",
                return_value=mock_intent,
            ) as mock_create,
        ):
            result = await service.charge_customer(
                db=AsyncMock(),
                customer_id=customer_id,
                amount=15000,
                description="Invoice INV-2025-042 payment",
            )

        assert result.payment_intent_id == "pi_test_intent_123"
        assert result.status == "succeeded"
        assert result.amount == 15000
        assert result.currency == "usd"

        # Verify PaymentIntent.create was called correctly
        mock_create.assert_called_once()
        call_kwargs = mock_create.call_args[1]
        assert call_kwargs["amount"] == 15000
        assert call_kwargs["currency"] == "usd"
        assert call_kwargs["customer"] == "cus_test_abc123"
        assert call_kwargs["payment_method"] == "pm_test_card_visa"
        assert call_kwargs["off_session"] is True
        assert call_kwargs["confirm"] is True
        desc = "Invoice INV-2025-042 payment"
        assert call_kwargs["description"] == desc

    async def test_stripe_payment_no_stripe_customer_raises_error(
        self,
    ) -> None:
        """Charging without Stripe ID raises MergeConflictError."""
        customer_id = uuid4()
        mock_customer = _mock_customer(
            id=customer_id,
            stripe_customer_id=None,
        )

        repo = AsyncMock()
        repo.get_by_id.return_value = mock_customer

        service = CustomerService(repository=repo)

        with pytest.raises(
            MergeConflictError,
            match="no Stripe account",
        ):
            await service.charge_customer(
                db=AsyncMock(),
                customer_id=customer_id,
                amount=5000,
                description="Test charge",
            )


# =============================================================================
# 5. Cookie-Based Auth — Validates: Requirement 71.7
# =============================================================================


@pytest.mark.functional
@pytest.mark.asyncio
class TestCookieBasedAuthWorkflow:
    """Test cookie-based authentication for frontend API calls.

    Validates: Requirement 71.7
    """

    async def test_login_sets_httponly_cookies(
        self,
    ) -> None:
        """Login sets access_token and refresh_token as httpOnly."""
        mock_staff = MagicMock()
        mock_staff.id = uuid4()
        mock_staff.username = "admin"
        mock_staff.name = "Viktor"
        mock_staff.email = "admin@grins.com"
        mock_staff.is_active = True
        mock_staff.role = "admin"

        mock_auth_service = AsyncMock()
        mock_auth_service.authenticate.return_value = (
            mock_staff,
            "access_token_value",
            "refresh_token_value",
            "csrf_token_value",
        )
        mock_auth_service.get_user_role = MagicMock(
            return_value=UserRole.ADMIN,
        )

        request = LoginRequest(
            username="admin",
            password="testpass123",
        )
        response = MagicMock()
        response.set_cookie = MagicMock()

        result = await login(
            request=request,
            response=response,
            auth_service=mock_auth_service,
        )

        # Verify login returns tokens
        assert result.access_token == "access_token_value"
        assert result.token_type == "bearer"
        assert result.csrf_token == "csrf_token_value"

        # Verify httpOnly cookies were set
        calls = response.set_cookie.call_args_list
        assert len(calls) == 3  # access, refresh, csrf

        cookie_keys = [c.kwargs["key"] for c in calls]
        assert ACCESS_TOKEN_COOKIE in cookie_keys
        assert REFRESH_TOKEN_COOKIE in cookie_keys

        # Verify httpOnly flags on auth cookies
        for call in calls:
            key = call.kwargs["key"]
            if key in (ACCESS_TOKEN_COOKIE, REFRESH_TOKEN_COOKIE):
                assert call.kwargs["httponly"] is True
                assert call.kwargs["path"] == "/"

    async def test_auth_dependency_reads_cookie(
        self,
    ) -> None:
        """Auth dependency extracts token from httpOnly cookie."""
        mock_staff = MagicMock()
        mock_staff.id = uuid4()
        mock_staff.is_active = True

        mock_auth_service = AsyncMock()
        mock_auth_service.get_current_user.return_value = mock_staff

        # Simulate request with cookie but no Authorization header
        mock_request = MagicMock()
        mock_request.cookies = {
            ACCESS_TOKEN_COOKIE: "cookie_access_token",
        }

        user = await get_current_user(
            request=mock_request,
            credentials=None,
            auth_service=mock_auth_service,
        )

        assert user.id == mock_staff.id
        mock_auth_service.get_current_user.assert_called_once_with(
            "cookie_access_token",
        )

    async def test_refresh_sets_new_access_cookie(
        self,
    ) -> None:
        """Token refresh sets updated access_token cookie."""
        mock_auth_service = AsyncMock()
        mock_auth_service.refresh_access_token.return_value = (
            "new_access_token",
            900,
        )

        response = MagicMock()
        response.set_cookie = MagicMock()

        result = await refresh(
            response=response,
            auth_service=mock_auth_service,
            refresh_token="valid_refresh_token",
        )

        assert result.access_token == "new_access_token"
        assert result.expires_in == 900

        # Verify new access token cookie was set
        response.set_cookie.assert_called_once()
        call_kwargs = response.set_cookie.call_args.kwargs
        assert call_kwargs["key"] == ACCESS_TOKEN_COOKIE
        assert call_kwargs["value"] == "new_access_token"
        assert call_kwargs["httponly"] is True
