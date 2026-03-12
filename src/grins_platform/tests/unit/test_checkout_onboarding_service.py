"""Unit tests for CheckoutService and OnboardingService.

Tests session creation, consent token validation, tier validation,
session verification, property creation, and agreement/job linking.

Validates: Requirements 30.1-30.5, 31.1-31.8, 32.1-32.7, 40.1
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
import stripe

from grins_platform.services.checkout_service import (
    CheckoutService,
    ConsentTokenExpiredError,
    ConsentTokenNotFoundError,
    TierInactiveError,
    TierNotConfiguredError,
    TierNotFoundError,
)
from grins_platform.services.onboarding_service import (
    AgreementNotFoundForSessionError,
    OnboardingService,
    SessionNotFoundError,
)

# =============================================================================
# Helpers
# =============================================================================


def _make_tier(
    *,
    tier_id: UUID | None = None,
    slug: str = "essential-residential",
    is_active: bool = True,
    stripe_price_id: str | None = "price_test_123",
    annual_price: str = "299.00",
) -> MagicMock:
    tier = MagicMock()
    tier.id = tier_id or uuid4()
    tier.slug = slug
    tier.is_active = is_active
    tier.stripe_price_id = stripe_price_id
    tier.annual_price = annual_price
    return tier


def _make_stripe_settings(*, tax_enabled: bool = True) -> MagicMock:
    s = MagicMock()
    s.stripe_secret_key = "sk_test_fake"
    s.stripe_tax_enabled = tax_enabled
    return s


def _mock_session_with_consent(timestamp: datetime | None) -> AsyncMock:
    """Return an AsyncSession mock whose execute returns the given timestamp."""
    session = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = timestamp
    session.execute = AsyncMock(return_value=result)
    return session


def _make_checkout_service(
    session: AsyncMock | None = None,
    tier_repo: AsyncMock | None = None,
    stripe_settings: MagicMock | None = None,
) -> CheckoutService:
    return CheckoutService(
        session=session or AsyncMock(),
        tier_repo=tier_repo or AsyncMock(),
        stripe_settings=stripe_settings or _make_stripe_settings(),
    )


def _make_agreement_mock(
    *,
    subscription_id: str = "sub_123",
    customer_id: UUID | None = None,
    jobs: list[Any] | None = None,
) -> MagicMock:
    agr = MagicMock()
    agr.id = uuid4()
    agr.customer_id = customer_id or uuid4()
    agr.stripe_subscription_id = subscription_id
    agr.jobs = jobs or []
    agr.customer = MagicMock()
    agr.customer.preferred_service_times = None
    agr.property = None
    return agr


def _make_onboarding_service(
    session: AsyncMock | None = None,
    agreement_repo: AsyncMock | None = None,
    property_repo: AsyncMock | None = None,
    stripe_settings: MagicMock | None = None,
) -> OnboardingService:
    return OnboardingService(
        session=session or AsyncMock(),
        agreement_repo=agreement_repo or AsyncMock(),
        property_repo=property_repo or AsyncMock(),
        stripe_settings=stripe_settings or _make_stripe_settings(),
    )


# =============================================================================
# CheckoutService — Consent Token Validation
# =============================================================================


@pytest.mark.unit
class TestConsentTokenValidation:
    """Tests for consent_token validation (valid, expired, missing)."""

    @pytest.mark.asyncio
    async def test_valid_consent_token_passes(self) -> None:
        ts = datetime.now(timezone.utc) - timedelta(minutes=30)
        session = _mock_session_with_consent(ts)
        svc = _make_checkout_service(session=session)

        # Should not raise
        await svc._validate_consent_token(uuid4())

    @pytest.mark.asyncio
    async def test_expired_consent_token_raises(self) -> None:
        ts = datetime.now(timezone.utc) - timedelta(hours=3)
        session = _mock_session_with_consent(ts)
        svc = _make_checkout_service(session=session)

        with pytest.raises(ConsentTokenExpiredError):
            await svc._validate_consent_token(uuid4())

    @pytest.mark.asyncio
    async def test_missing_consent_token_raises(self) -> None:
        session = _mock_session_with_consent(None)
        svc = _make_checkout_service(session=session)

        with pytest.raises(ConsentTokenNotFoundError):
            await svc._validate_consent_token(uuid4())


# =============================================================================
# CheckoutService — Tier Validation
# =============================================================================


@pytest.mark.unit
class TestTierValidation:
    """Tests for tier lookup (active, inactive, missing, null stripe_price_id)."""

    @pytest.mark.asyncio
    async def test_active_tier_with_price_passes(self) -> None:
        tier = _make_tier()
        tier_repo = AsyncMock()
        tier_repo.get_by_slug_and_type = AsyncMock(return_value=tier)
        svc = _make_checkout_service(tier_repo=tier_repo)

        result = await svc._validate_tier(tier.slug, "residential")
        assert result is tier

    @pytest.mark.asyncio
    async def test_missing_tier_raises(self) -> None:
        tier_repo = AsyncMock()
        tier_repo.get_by_slug_and_type = AsyncMock(return_value=None)
        svc = _make_checkout_service(tier_repo=tier_repo)

        with pytest.raises(TierNotFoundError):
            await svc._validate_tier("nonexistent", "residential")

    @pytest.mark.asyncio
    async def test_inactive_tier_raises(self) -> None:
        tier = _make_tier(is_active=False)
        tier_repo = AsyncMock()
        tier_repo.get_by_slug_and_type = AsyncMock(return_value=tier)
        svc = _make_checkout_service(tier_repo=tier_repo)

        with pytest.raises(TierInactiveError):
            await svc._validate_tier(tier.slug, "residential")

    @pytest.mark.asyncio
    async def test_tier_without_stripe_price_id_raises(self) -> None:
        tier = _make_tier(stripe_price_id=None)
        tier_repo = AsyncMock()
        tier_repo.get_by_slug_and_type = AsyncMock(return_value=tier)
        svc = _make_checkout_service(tier_repo=tier_repo)

        with pytest.raises(TierNotConfiguredError):
            await svc._validate_tier(tier.slug, "residential")


# =============================================================================
# CheckoutService — Session Creation
# =============================================================================


@pytest.mark.unit
class TestCreateCheckoutSession:
    """Tests for Stripe Checkout Session creation."""

    @pytest.mark.asyncio
    @patch("grins_platform.services.checkout_service.stripe.checkout.Session.create")
    async def test_creates_session_with_valid_inputs(self, mock_create) -> None:
        tier = _make_tier()
        tier_repo = AsyncMock()
        tier_repo.get_by_slug_and_type = AsyncMock(return_value=tier)

        ts = datetime.now(timezone.utc) - timedelta(minutes=10)
        session = _mock_session_with_consent(ts)

        mock_create.return_value = MagicMock(
            id="cs_test_123",
            url="https://checkout.stripe.com/test",
        )

        svc = _make_checkout_service(
            session=session,
            tier_repo=tier_repo,
        )
        url = await svc.create_checkout_session(
            package_tier=tier.slug,
            package_type="residential",
            consent_token=uuid4(),
            success_url="https://example.com/success",
            cancel_url="https://example.com/cancel",
        )

        assert url == "https://checkout.stripe.com/test"
        mock_create.assert_called_once()
        call_kwargs = mock_create.call_args[1]
        assert call_kwargs["mode"] == "subscription"
        assert call_kwargs["success_url"] == "https://example.com/success"
        assert call_kwargs["cancel_url"] == "https://example.com/cancel"

    @pytest.mark.asyncio
    @patch("grins_platform.services.checkout_service.stripe.checkout.Session.create")
    async def test_automatic_tax_enabled(self, mock_create) -> None:
        tier = _make_tier()
        tier_repo = AsyncMock()
        tier_repo.get_by_slug_and_type = AsyncMock(return_value=tier)
        ts = datetime.now(timezone.utc) - timedelta(minutes=5)
        session = _mock_session_with_consent(ts)

        mock_create.return_value = MagicMock(id="cs_1", url="https://x.com")

        svc = _make_checkout_service(
            session=session,
            tier_repo=tier_repo,
            stripe_settings=_make_stripe_settings(tax_enabled=True),
        )
        await svc.create_checkout_session(
            package_tier=tier.slug,
            package_type="residential",
            consent_token=uuid4(),
        )

        call_kwargs = mock_create.call_args[1]
        assert call_kwargs["automatic_tax"] == {"enabled": True}

    @pytest.mark.asyncio
    @patch("grins_platform.services.checkout_service.stripe.checkout.Session.create")
    async def test_automatic_tax_disabled(self, mock_create) -> None:
        tier = _make_tier()
        tier_repo = AsyncMock()
        tier_repo.get_by_slug_and_type = AsyncMock(return_value=tier)
        ts = datetime.now(timezone.utc) - timedelta(minutes=5)
        session = _mock_session_with_consent(ts)

        mock_create.return_value = MagicMock(id="cs_1", url="https://x.com")

        svc = _make_checkout_service(
            session=session,
            tier_repo=tier_repo,
            stripe_settings=_make_stripe_settings(tax_enabled=False),
        )
        await svc.create_checkout_session(
            package_tier=tier.slug,
            package_type="residential",
            consent_token=uuid4(),
        )

        call_kwargs = mock_create.call_args[1]
        assert "automatic_tax" not in call_kwargs

    @pytest.mark.asyncio
    @patch("grins_platform.services.checkout_service.stripe.checkout.Session.create")
    async def test_utm_params_included_in_metadata(self, mock_create) -> None:
        tier = _make_tier()
        tier_repo = AsyncMock()
        tier_repo.get_by_slug_and_type = AsyncMock(return_value=tier)
        ts = datetime.now(timezone.utc) - timedelta(minutes=5)
        session = _mock_session_with_consent(ts)

        mock_create.return_value = MagicMock(id="cs_1", url="https://x.com")

        svc = _make_checkout_service(session=session, tier_repo=tier_repo)
        await svc.create_checkout_session(
            package_tier=tier.slug,
            package_type="residential",
            consent_token=uuid4(),
            utm_params={"source": "google", "medium": "cpc"},
        )

        call_kwargs = mock_create.call_args[1]
        meta = call_kwargs["metadata"]
        assert meta["utm_source"] == "google"
        assert meta["utm_medium"] == "cpc"


# =============================================================================
# OnboardingService — Session Verification
# =============================================================================


@pytest.mark.unit
class TestVerifySession:
    """Tests for Stripe session verification."""

    @pytest.mark.asyncio
    @patch(
        "grins_platform.services.onboarding_service.stripe.checkout.Session.retrieve",
    )
    async def test_valid_session_returns_info(self, mock_retrieve) -> None:
        customer_details = SimpleNamespace(
            name="John Doe",
            email="john@example.com",
            phone="+16125551234",
            address=SimpleNamespace(
                line1="123 Main St",
                line2="",
                city="Minneapolis",
                state="MN",
                postal_code="55401",
                country="US",
            ),
        )
        mock_retrieve.return_value = SimpleNamespace(
            customer_details=customer_details,
            metadata={
                "package_tier": "essential-residential",
                "package_type": "residential",
            },
            payment_status="paid",
            subscription="sub_test_123",
        )

        # Mock session.execute for _find_agreement_by_subscription
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)

        svc = _make_onboarding_service(session=mock_session)
        info = await svc.verify_session("cs_test_123")

        assert info.customer_name == "John Doe"
        assert info.email == "john@example.com"
        assert info.package_tier == "essential-residential"
        assert info.payment_status == "paid"
        assert info.billing_address["city"] == "Minneapolis"
        assert info.already_completed is False

    @pytest.mark.asyncio
    @patch(
        "grins_platform.services.onboarding_service.stripe.checkout.Session.retrieve",
    )
    async def test_not_found_session_raises(self, mock_retrieve) -> None:
        mock_retrieve.side_effect = stripe.InvalidRequestError(  # type: ignore[no-untyped-call]
            "No such session",
            param="id",
        )

        svc = _make_onboarding_service()
        with pytest.raises(SessionNotFoundError):
            await svc.verify_session("cs_invalid")


# =============================================================================
# OnboardingService — Complete Onboarding
# =============================================================================


@pytest.mark.unit
class TestCompleteOnboarding:
    """Tests for property creation and agreement/job linking."""

    @pytest.mark.asyncio
    @patch(
        "grins_platform.services.onboarding_service.stripe.checkout.Session.retrieve",
    )
    async def test_creates_property_same_as_billing(self, mock_retrieve) -> None:
        mock_retrieve.return_value = SimpleNamespace(
            subscription="sub_123",
            customer_details=SimpleNamespace(
                address=SimpleNamespace(
                    line1="456 Oak Ave",
                    city="St Paul",
                    state="MN",
                    postal_code="55102",
                ),
            ),
        )

        prop_mock = MagicMock()
        prop_mock.id = uuid4()

        property_repo = AsyncMock()
        property_repo.create = AsyncMock(return_value=prop_mock)

        job1 = MagicMock()
        job1.property_id = None
        agreement = _make_agreement_mock(jobs=[job1])

        agreement_repo = AsyncMock()
        agreement_repo.update = AsyncMock(return_value=agreement)

        db_session = AsyncMock()
        # Mock the execute for _find_agreement_by_subscription
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = agreement
        db_session.execute = AsyncMock(return_value=result_mock)

        svc = _make_onboarding_service(
            session=db_session,
            agreement_repo=agreement_repo,
            property_repo=property_repo,
        )
        await svc.complete_onboarding("cs_test_123")

        property_repo.create.assert_called_once()
        call_kwargs = property_repo.create.call_args[1]
        assert call_kwargs["address"] == "456 Oak Ave"
        assert call_kwargs["city"] == "St Paul"
        assert call_kwargs["is_primary"] is True
        assert job1.property_id == prop_mock.id

    @pytest.mark.asyncio
    @patch(
        "grins_platform.services.onboarding_service.stripe.checkout.Session.retrieve",
    )
    async def test_creates_property_with_custom_address(self, mock_retrieve) -> None:
        mock_retrieve.return_value = SimpleNamespace(
            subscription="sub_123",
            customer_details=None,
        )

        prop_mock = MagicMock()
        prop_mock.id = uuid4()

        property_repo = AsyncMock()
        property_repo.create = AsyncMock(return_value=prop_mock)

        agreement = _make_agreement_mock(jobs=[])
        agreement_repo = AsyncMock()
        agreement_repo.update = AsyncMock(return_value=agreement)

        db_session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = agreement
        db_session.execute = AsyncMock(return_value=result_mock)

        svc = _make_onboarding_service(
            session=db_session,
            agreement_repo=agreement_repo,
            property_repo=property_repo,
        )
        await svc.complete_onboarding(
            "cs_test_123",
            service_address_same_as_billing=False,
            service_address={
                "street": "789 Elm St",
                "city": "Eagan",
                "state": "MN",
                "zip": "55122",
            },
        )

        call_kwargs = property_repo.create.call_args[1]
        assert call_kwargs["address"] == "789 Elm St"
        assert call_kwargs["city"] == "Eagan"

    @pytest.mark.asyncio
    @patch(
        "grins_platform.services.onboarding_service.stripe.checkout.Session.retrieve",
    )
    async def test_updates_customer_preferred_times(self, mock_retrieve) -> None:
        mock_retrieve.return_value = SimpleNamespace(
            subscription="sub_123",
            customer_details=SimpleNamespace(
                address=SimpleNamespace(
                    line1="1 St",
                    city="Mpls",
                    state="MN",
                    postal_code="55401",
                ),
            ),
        )

        prop_mock = MagicMock()
        prop_mock.id = uuid4()

        property_repo = AsyncMock()
        property_repo.create = AsyncMock(return_value=prop_mock)

        customer_mock = MagicMock()
        customer_mock.preferred_service_times = None
        agreement = _make_agreement_mock(jobs=[])
        agreement.customer = customer_mock

        agreement_repo = AsyncMock()
        agreement_repo.update = AsyncMock(return_value=agreement)

        db_session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = agreement
        db_session.execute = AsyncMock(return_value=result_mock)

        svc = _make_onboarding_service(
            session=db_session,
            agreement_repo=agreement_repo,
            property_repo=property_repo,
        )
        await svc.complete_onboarding("cs_test_123", preferred_times="MORNING")

        assert customer_mock.preferred_service_times == {"preference": "MORNING"}

    @pytest.mark.asyncio
    @patch(
        "grins_platform.services.onboarding_service.stripe.checkout.Session.retrieve",
    )
    async def test_session_not_found_raises(self, mock_retrieve) -> None:
        mock_retrieve.side_effect = stripe.InvalidRequestError(  # type: ignore[no-untyped-call]
            "No such session",
            param="id",
        )

        svc = _make_onboarding_service()
        with pytest.raises(SessionNotFoundError):
            await svc.complete_onboarding("cs_invalid")

    @pytest.mark.asyncio
    @patch(
        "grins_platform.services.onboarding_service.stripe.checkout.Session.retrieve",
    )
    async def test_no_subscription_raises(self, mock_retrieve) -> None:
        mock_retrieve.return_value = SimpleNamespace(
            subscription=None,
            customer_details=None,
        )

        svc = _make_onboarding_service()
        with pytest.raises(AgreementNotFoundForSessionError):
            await svc.complete_onboarding("cs_no_sub")

    @pytest.mark.asyncio
    @patch(
        "grins_platform.services.onboarding_service.stripe.checkout.Session.retrieve",
    )
    async def test_agreement_not_found_raises(self, mock_retrieve) -> None:
        mock_retrieve.return_value = SimpleNamespace(
            subscription="sub_orphan",
            customer_details=None,
        )

        db_session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        db_session.execute = AsyncMock(return_value=result_mock)

        svc = _make_onboarding_service(session=db_session)
        with pytest.raises(AgreementNotFoundForSessionError):
            await svc.complete_onboarding("cs_no_agreement")

    @pytest.mark.asyncio
    @patch(
        "grins_platform.services.onboarding_service.stripe.checkout.Session.retrieve",
    )
    async def test_links_all_jobs_to_property(self, mock_retrieve) -> None:
        mock_retrieve.return_value = SimpleNamespace(
            subscription="sub_123",
            customer_details=SimpleNamespace(
                address=SimpleNamespace(
                    line1="1 St",
                    city="Mpls",
                    state="MN",
                    postal_code="55401",
                ),
            ),
        )

        prop_mock = MagicMock()
        prop_mock.id = uuid4()

        property_repo = AsyncMock()
        property_repo.create = AsyncMock(return_value=prop_mock)

        job1 = MagicMock()
        job1.property_id = None
        job2 = MagicMock()
        job2.property_id = None
        job3 = MagicMock()
        job3.property_id = None

        agreement = _make_agreement_mock(jobs=[job1, job2, job3])
        agreement_repo = AsyncMock()
        agreement_repo.update = AsyncMock(return_value=agreement)

        db_session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = agreement
        db_session.execute = AsyncMock(return_value=result_mock)

        svc = _make_onboarding_service(
            session=db_session,
            agreement_repo=agreement_repo,
            property_repo=property_repo,
        )
        await svc.complete_onboarding("cs_test_123")

        assert job1.property_id == prop_mock.id
        assert job2.property_id == prop_mock.id
        assert job3.property_id == prop_mock.id


# =============================================================================
# CheckoutService — Surcharge Integration (Task 12)
# =============================================================================


@pytest.mark.unit
class TestCheckoutSessionSurcharges:
    """Tests for surcharge line items in Stripe Checkout Session.

    Validates: Requirements 3.1, 3.11, 3.12, 4.4
    """

    @pytest.mark.asyncio
    @patch("grins_platform.services.checkout_service.stripe.checkout.Session.create")
    async def test_surcharges_create_extra_line_items(
        self,
        mock_create: MagicMock,
    ) -> None:
        """zone_count=12, has_lake_pump=true -> 3 Stripe line items."""
        tier = _make_tier(slug="essential-residential", annual_price="299.00")
        tier_repo = AsyncMock()
        tier_repo.get_by_slug_and_type = AsyncMock(return_value=tier)
        ts = datetime.now(timezone.utc) - timedelta(minutes=5)
        session = _mock_session_with_consent(ts)

        mock_create.return_value = MagicMock(id="cs_1", url="https://x.com")

        svc = _make_checkout_service(session=session, tier_repo=tier_repo)
        await svc.create_checkout_session(
            package_tier=tier.slug,
            package_type="residential",
            consent_token=uuid4(),
            zone_count=12,
            has_lake_pump=True,
        )

        call_kwargs = mock_create.call_args[1]
        items = call_kwargs["line_items"]
        assert len(items) == 3
        # Base price
        assert items[0]["price"] == "price_test_123"
        # Zone surcharge: 3 extra zones x $7.50 = $22.50 = 2250 cents
        assert items[1]["price_data"]["unit_amount"] == 2250
        # Lake pump surcharge: $175.00 = 17500 cents
        assert items[2]["price_data"]["unit_amount"] == 17500

    @pytest.mark.asyncio
    @patch("grins_platform.services.checkout_service.stripe.checkout.Session.create")
    async def test_no_surcharges_single_line_item(self, mock_create: MagicMock) -> None:
        """zone_count=5, has_lake_pump=false → 1 Stripe line item (base only)."""
        tier = _make_tier(slug="essential-residential", annual_price="299.00")
        tier_repo = AsyncMock()
        tier_repo.get_by_slug_and_type = AsyncMock(return_value=tier)
        ts = datetime.now(timezone.utc) - timedelta(minutes=5)
        session = _mock_session_with_consent(ts)

        mock_create.return_value = MagicMock(id="cs_1", url="https://x.com")

        svc = _make_checkout_service(session=session, tier_repo=tier_repo)
        await svc.create_checkout_session(
            package_tier=tier.slug,
            package_type="residential",
            consent_token=uuid4(),
            zone_count=5,
            has_lake_pump=False,
        )

        call_kwargs = mock_create.call_args[1]
        items = call_kwargs["line_items"]
        assert len(items) == 1
        assert items[0]["price"] == "price_test_123"

    @pytest.mark.asyncio
    @patch("grins_platform.services.checkout_service.stripe.checkout.Session.create")
    async def test_winterization_only_tier_uses_correct_rates(
        self,
        mock_create: MagicMock,
    ) -> None:
        """Winterization-only tier uses winterization surcharge rates."""
        tier = _make_tier(
            slug="winterization-only-residential",
            annual_price="80.00",
        )
        tier_repo = AsyncMock()
        tier_repo.get_by_slug_and_type = AsyncMock(return_value=tier)
        ts = datetime.now(timezone.utc) - timedelta(minutes=5)
        session = _mock_session_with_consent(ts)

        mock_create.return_value = MagicMock(id="cs_1", url="https://x.com")

        svc = _make_checkout_service(session=session, tier_repo=tier_repo)
        await svc.create_checkout_session(
            package_tier=tier.slug,
            package_type="residential",
            consent_token=uuid4(),
            zone_count=11,
            has_lake_pump=True,
        )

        call_kwargs = mock_create.call_args[1]
        items = call_kwargs["line_items"]
        assert len(items) == 3
        # Zone surcharge: 2 extra zones x $5.00 = $10.00 = 1000 cents
        assert items[1]["price_data"]["unit_amount"] == 1000
        # Lake pump surcharge: $75.00 = 7500 cents
        assert items[2]["price_data"]["unit_amount"] == 7500

    @pytest.mark.asyncio
    @patch("grins_platform.services.checkout_service.stripe.checkout.Session.create")
    async def test_metadata_includes_new_fields(self, mock_create: MagicMock) -> None:
        """Metadata includes zone_count, has_lake_pump, email_marketing_consent."""
        tier = _make_tier()
        tier_repo = AsyncMock()
        tier_repo.get_by_slug_and_type = AsyncMock(return_value=tier)
        ts = datetime.now(timezone.utc) - timedelta(minutes=5)
        session = _mock_session_with_consent(ts)

        mock_create.return_value = MagicMock(id="cs_1", url="https://x.com")

        svc = _make_checkout_service(session=session, tier_repo=tier_repo)
        await svc.create_checkout_session(
            package_tier=tier.slug,
            package_type="residential",
            consent_token=uuid4(),
            zone_count=15,
            has_lake_pump=True,
            email_marketing_consent=True,
        )

        call_kwargs = mock_create.call_args[1]
        meta = call_kwargs["metadata"]
        assert meta["zone_count"] == "15"
        assert meta["has_lake_pump"] == "true"
        assert meta["email_marketing_consent"] == "true"
        # Also in subscription_data metadata
        sub_meta = call_kwargs["subscription_data"]["metadata"]
        assert sub_meta["zone_count"] == "15"
        assert sub_meta["has_lake_pump"] == "true"
        assert sub_meta["email_marketing_consent"] == "true"
