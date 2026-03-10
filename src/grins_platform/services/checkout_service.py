"""Checkout service for creating Stripe Checkout Sessions.

Validates consent tokens, tier availability, and creates Stripe Checkout
Sessions with subscription mode, tax configuration, and metadata.

Validates: Requirements 31.1, 31.2, 31.3, 31.4, 31.5, 31.6, 31.7, 31.8, 39A.4
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

import stripe
from sqlalchemy import select

from grins_platform.log_config import LoggerMixin
from grins_platform.models.sms_consent_record import SmsConsentRecord
from grins_platform.services.stripe_config import StripeSettings

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from grins_platform.models.service_agreement_tier import ServiceAgreementTier
    from grins_platform.repositories.agreement_tier_repository import (
        AgreementTierRepository,
    )

# Maximum age for consent tokens (2 hours)
CONSENT_TOKEN_MAX_AGE = timedelta(hours=2)


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

    def __init__(self, tier_id: UUID) -> None:
        """Initialize with missing tier ID."""
        super().__init__(f"Tier not found: {tier_id}")
        self.tier_id = tier_id


class TierInactiveError(CheckoutError):
    """Raised when tier is inactive."""

    def __init__(self, tier_id: UUID) -> None:
        """Initialize with inactive tier ID."""
        super().__init__(f"Tier is inactive: {tier_id}")
        self.tier_id = tier_id


class TierNotConfiguredError(CheckoutError):
    """Raised when tier has no stripe_price_id (HTTP 503)."""

    def __init__(self, tier_id: UUID) -> None:
        """Initialize with unconfigured tier ID."""
        super().__init__(f"Tier not configured for Stripe: {tier_id}")
        self.tier_id = tier_id


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

    async def _validate_tier(self, tier_id: UUID) -> ServiceAgreementTier:
        """Validate tier exists, is active, and has stripe_price_id.

        Validates: Requirements 31.3, 31.4
        """
        tier = await self.tier_repo.get_by_id(tier_id)
        if not tier:
            self.log_rejected(
                "validate_tier",
                reason="not_found",
                tier_id=str(tier_id),
            )
            raise TierNotFoundError(tier_id)

        if not tier.is_active:
            self.log_rejected(
                "validate_tier",
                reason="inactive",
                tier_id=str(tier_id),
            )
            raise TierInactiveError(tier_id)

        if not tier.stripe_price_id:
            self.log_rejected(
                "validate_tier",
                reason="no_stripe_price_id",
                tier_id=str(tier_id),
            )
            raise TierNotConfiguredError(tier_id)

        return tier

    async def create_checkout_session(
        self,
        tier_id: UUID,
        package_type: str,
        consent_token: UUID,
        *,
        utm_params: dict[str, str] | None = None,
        success_url: str = "",
        cancel_url: str = "",
    ) -> str:
        """Create a Stripe Checkout Session for subscription purchase.

        Validates consent_token (< 2 hours), tier (exists, active, has
        stripe_price_id), then creates a Stripe Checkout Session with
        subscription mode.

        Returns the Stripe Checkout URL.

        Validates: Requirements 31.1, 31.2, 31.3, 31.4, 31.5, 31.6, 31.7, 31.8, 39A.4
        """
        self.log_started(
            "create_checkout_session",
            tier_id=str(tier_id),
            package_type=package_type,
            consent_token=str(consent_token),
        )

        await self._validate_consent_token(consent_token)
        tier = await self._validate_tier(tier_id)

        # Build metadata
        metadata: dict[str, str] = {
            "consent_token": str(consent_token),
            "package_tier": tier.slug,
            "package_type": package_type,
        }
        if utm_params:
            for key, value in utm_params.items():
                metadata[f"utm_{key}"] = value

        # Build Stripe Checkout Session params
        stripe.api_key = self.stripe_settings.stripe_secret_key

        session_params: dict[str, Any] = {
            "mode": "subscription",
            "line_items": [{"price": tier.stripe_price_id, "quantity": 1}],
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
        )
        return checkout_url
