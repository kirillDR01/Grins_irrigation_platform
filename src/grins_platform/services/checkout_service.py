"""Checkout service for creating Stripe Checkout Sessions.

Validates consent tokens, tier availability, and creates Stripe Checkout
Sessions with subscription mode, tax configuration, and metadata.

Validates: Requirements 31.1, 31.2, 31.3, 31.4, 31.5, 31.6, 31.7, 31.8, 39A.4
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, Any

import stripe
from sqlalchemy import select

from grins_platform.log_config import LoggerMixin
from grins_platform.models.sms_consent_record import SmsConsentRecord
from grins_platform.services.stripe_config import StripeSettings
from grins_platform.services.surcharge_calculator import SurchargeCalculator

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from grins_platform.models.service_agreement_tier import ServiceAgreementTier
    from grins_platform.repositories.agreement_tier_repository import (
        AgreementTierRepository,
    )

# Maximum age for consent tokens (2 hours)
CONSENT_TOKEN_MAX_AGE = timedelta(hours=2)


class SubscriptionNotFoundError(Exception):
    """Raised when no Stripe customer is found for the given email."""

    def __init__(self, email: str) -> None:
        self.email = email
        super().__init__(f"No subscription found for email: {email}")


class CheckoutError(Exception):
    """Base error for checkout operations."""


class ConsentTokenExpiredError(CheckoutError):
    """Raised when consent token is older than 2 hours."""

    def __init__(self, token: UUID) -> None:
        """Initialize with expired token."""
        super().__init__(f"Consent token expired: {token}")
        self.token = token


class ConsentTokenNotFoundError(CheckoutError):
    """Raised when consent token has no matching records."""

    def __init__(self, token: UUID) -> None:
        """Initialize with missing token."""
        super().__init__(f"Consent token not found: {token}")
        self.token = token


class TierNotFoundError(CheckoutError):
    """Raised when tier does not exist."""

    def __init__(self, slug: str) -> None:
        """Initialize with missing tier slug."""
        super().__init__(f"Tier not found: {slug}")
        self.slug = slug


class TierInactiveError(CheckoutError):
    """Raised when tier is inactive."""

    def __init__(self, slug: str) -> None:
        """Initialize with inactive tier slug."""
        super().__init__(f"Tier is inactive: {slug}")
        self.slug = slug


class TierNotConfiguredError(CheckoutError):
    """Raised when tier has no stripe_price_id (HTTP 503)."""

    def __init__(self, slug: str) -> None:
        """Initialize with unconfigured tier slug."""
        super().__init__(f"Tier not configured for Stripe: {slug}")
        self.slug = slug


class StripeUnavailableError(CheckoutError):
    """Raised when Stripe SDK calls fail (auth, network, API errors).

    Should map to HTTP 503 Service Unavailable.
    """

    def __init__(self, message: str) -> None:
        """Initialize with underlying Stripe error message."""
        super().__init__(f"Stripe is unavailable: {message}")
        self.message = message


class CheckoutService(LoggerMixin):
    """Service for creating Stripe Checkout Sessions.

    Validates: Requirements 31.1, 31.2, 31.3, 31.4, 31.5, 31.6, 31.7, 31.8, 39A.4
    """

    DOMAIN = "checkout"

    def __init__(
        self,
        session: AsyncSession,
        tier_repo: AgreementTierRepository,
        stripe_settings: StripeSettings | None = None,
    ) -> None:
        """Initialize with database session, tier repository, and Stripe settings."""
        super().__init__()
        self.session = session
        self.tier_repo = tier_repo
        self.stripe_settings = stripe_settings or StripeSettings()

    async def _validate_consent_token(self, consent_token: UUID) -> None:
        """Validate consent token exists and is less than 2 hours old.

        Validates: Requirement 31.2
        """
        stmt = (
            select(SmsConsentRecord.consent_timestamp)
            .where(SmsConsentRecord.consent_token == consent_token)
            .order_by(SmsConsentRecord.consent_timestamp.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        row = result.scalar_one_or_none()

        if row is None:
            self.log_rejected(
                "validate_consent_token",
                reason="not_found",
                consent_token=str(consent_token),
            )
            raise ConsentTokenNotFoundError(consent_token)

        age = datetime.now(timezone.utc) - row
        if age > CONSENT_TOKEN_MAX_AGE:
            self.log_rejected(
                "validate_consent_token",
                reason="expired",
                consent_token=str(consent_token),
                age_seconds=age.total_seconds(),
            )
            raise ConsentTokenExpiredError(consent_token)

    async def _validate_tier(
        self,
        slug: str,
        package_type: str,
    ) -> ServiceAgreementTier:
        """Validate tier exists, is active, and has stripe_price_id.

        Validates: Requirements 31.3, 31.4
        """
        tier = await self.tier_repo.get_by_slug_and_type(slug, package_type)
        if not tier:
            self.log_rejected(
                "validate_tier",
                reason="not_found",
                slug=slug,
                package_type=package_type,
            )
            raise TierNotFoundError(slug)

        if not tier.is_active:
            self.log_rejected(
                "validate_tier",
                reason="inactive",
                slug=slug,
            )
            raise TierInactiveError(slug)

        if not tier.stripe_price_id:
            self.log_rejected(
                "validate_tier",
                reason="no_stripe_price_id",
                slug=slug,
            )
            raise TierNotConfiguredError(slug)

        return tier

    async def create_checkout_session(
        self,
        package_tier: str,
        package_type: str,
        consent_token: UUID,
        *,
        zone_count: int = 1,
        has_lake_pump: bool = False,
        has_rpz_backflow: bool = False,
        email_marketing_consent: bool = False,
        utm_params: dict[str, str] | None = None,
        success_url: str = "",
        cancel_url: str = "",
    ) -> str:
        """Create a Stripe Checkout Session for subscription purchase.

        Validates consent_token (< 2 hours), tier (exists, active, has
        stripe_price_id), computes surcharges, then creates a Stripe
        Checkout Session with subscription mode.

        Returns the Stripe Checkout URL.

        Validates: Requirements 3.1, 3.11, 3.12, 4.4, 31.1-31.8, 39A.4
        """
        self.log_started(
            "create_checkout_session",
            package_tier=package_tier,
            package_type=package_type,
            consent_token=str(consent_token),
            zone_count=zone_count,
            has_lake_pump=has_lake_pump,
            has_rpz_backflow=has_rpz_backflow,
        )

        await self._validate_consent_token(consent_token)
        tier = await self._validate_tier(package_tier, package_type)

        # Compute surcharges
        breakdown = SurchargeCalculator.calculate(
            tier_slug=tier.slug,
            package_type=package_type,
            zone_count=zone_count,
            has_lake_pump=has_lake_pump,
            base_price=Decimal(str(tier.annual_price)),
            has_rpz_backflow=has_rpz_backflow,
        )

        # Build metadata
        metadata: dict[str, str] = {
            "consent_token": str(consent_token),
            "package_tier": tier.slug,
            "package_type": package_type,
            "zone_count": str(zone_count),
            "has_lake_pump": str(has_lake_pump).lower(),
            "has_rpz_backflow": str(has_rpz_backflow).lower(),
            "email_marketing_consent": str(email_marketing_consent).lower(),
        }
        if utm_params:
            for key, value in utm_params.items():
                metadata[f"utm_{key}"] = value

        # Build Stripe line items: base price + optional surcharges
        line_items: list[dict[str, Any]] = [
            {"price": tier.stripe_price_id, "quantity": 1},
        ]

        if breakdown.zone_surcharge > 0:
            line_items.append(
                {
                    "price_data": {
                        "currency": "usd",
                        "product_data": {
                            "name": f"Zone surcharge ({zone_count - 9} extra zones)",
                        },
                        "unit_amount": int(breakdown.zone_surcharge * 100),
                        "recurring": {"interval": "year"},
                    },
                    "quantity": 1,
                },
            )

        if breakdown.lake_pump_surcharge > 0:
            line_items.append(
                {
                    "price_data": {
                        "currency": "usd",
                        "product_data": {"name": "Lake pump surcharge"},
                        "unit_amount": int(breakdown.lake_pump_surcharge * 100),
                        "recurring": {"interval": "year"},
                    },
                    "quantity": 1,
                },
            )

        if breakdown.rpz_backflow_surcharge > 0:
            is_winterization = tier.slug.startswith("winterization-only-")
            rpz_name = (
                "RPZ/backflow removal"
                if is_winterization
                else "RPZ/backflow connection & removal"
            )
            line_items.append(
                {
                    "price_data": {
                        "currency": "usd",
                        "product_data": {"name": rpz_name},
                        "unit_amount": int(breakdown.rpz_backflow_surcharge * 100),
                        "recurring": {"interval": "year"},
                    },
                    "quantity": 1,
                },
            )

        # Build Stripe Checkout Session params
        stripe.api_key = self.stripe_settings.stripe_secret_key
        stripe.api_version = self.stripe_settings.stripe_api_version

        session_params: dict[str, Any] = {
            "mode": "subscription",
            "payment_method_types": ["card"],
            "line_items": line_items,
            "phone_number_collection": {"enabled": True},
            "billing_address_collection": "required",
            "consent_collection": {
                "terms_of_service": "required",
            },
            "metadata": metadata,
            "subscription_data": {"metadata": metadata},
        }

        if success_url:
            session_params["success_url"] = success_url
        if cancel_url:
            session_params["cancel_url"] = cancel_url

        # Configure automatic tax if enabled
        if self.stripe_settings.stripe_tax_enabled:
            session_params["automatic_tax"] = {"enabled": True}

        checkout_session = stripe.checkout.Session.create(**session_params)
        checkout_url: str = checkout_session.url or ""

        self.log_completed(
            "create_checkout_session",
            session_id=checkout_session.id,
            tier_slug=tier.slug,
            total=str(breakdown.total),
        )
        return checkout_url

    async def create_portal_session(self, email: str) -> str:
        """Look up Stripe customer by email and create a billing portal session URL.

        Returns the portal session URL.
        Raises SubscriptionNotFoundError if no customer is found.
        Raises StripeUnavailableError if Stripe SDK calls fail (auth, network, etc.).

        Validates: Requirements 2.1, 2.2
        """
        self.log_started("create_portal_session", email=email[:3] + "***")

        stripe.api_key = self.stripe_settings.stripe_secret_key
        stripe.api_version = self.stripe_settings.stripe_api_version

        try:
            customers = stripe.Customer.list(email=email, limit=1)
        except stripe.error.StripeError as exc:
            self.log_failed("create_portal_session", error=exc)
            raise StripeUnavailableError(str(exc)) from exc

        if not customers.data:
            self.log_rejected(
                "create_portal_session",
                reason="customer_not_found",
            )
            raise SubscriptionNotFoundError(email)

        customer = customers.data[0]

        try:
            portal_session = stripe.billing_portal.Session.create(
                customer=customer.id,
                return_url=self.stripe_settings.stripe_customer_portal_url or None,
            )
        except stripe.error.StripeError as exc:
            self.log_failed("create_portal_session", error=exc)
            raise StripeUnavailableError(str(exc)) from exc

        portal_url: str = portal_session.url

        self.log_completed(
            "create_portal_session",
            customer_id=customer.id,
        )
        return portal_url
