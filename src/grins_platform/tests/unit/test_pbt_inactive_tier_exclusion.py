"""Property test for inactive tier exclusion.

Property 22: Inactive Tier Exclusion
For any tier with is_active=false, checkout session creation and agreement
creation reject with appropriate error.

Validates: Requirements 1.4
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from hypothesis import (
    given,
    settings,
    strategies as st,
)

from grins_platform.exceptions import InactiveTierError
from grins_platform.services.agreement_service import AgreementService
from grins_platform.services.checkout_service import (
    CheckoutService,
    TierInactiveError,
)

slugs = st.sampled_from(
    [
        "essential-residential",
        "essential-commercial",
        "professional-residential",
        "professional-commercial",
        "premium-residential",
        "premium-commercial",
    ],
)
prices = st.decimals(min_value=Decimal("1.00"), max_value=Decimal("9999.99"), places=2)


def _make_inactive_tier(slug: str, price: Decimal) -> MagicMock:
    tier = MagicMock()
    tier.id = uuid4()
    tier.slug = slug
    tier.is_active = False
    tier.annual_price = price
    tier.stripe_price_id = "price_test"
    return tier


def _make_active_tier(slug: str, price: Decimal) -> MagicMock:
    tier = MagicMock()
    tier.id = uuid4()
    tier.slug = slug
    tier.is_active = True
    tier.annual_price = price
    tier.stripe_price_id = "price_test"
    return tier


def _mock_session_with_consent() -> AsyncMock:
    """Return AsyncSession mock with valid consent token."""
    session = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = datetime.now(timezone.utc) - timedelta(
        minutes=5,
    )
    session.execute = AsyncMock(return_value=result)
    return session


@pytest.mark.unit
@pytest.mark.asyncio
class TestInactiveTierExclusionProperty:
    """Property-based tests for inactive tier exclusion."""

    @given(slug=slugs, price=prices)
    @settings(max_examples=30)
    async def test_checkout_rejects_inactive_tier(
        self,
        slug: str,
        price: Decimal,
    ) -> None:
        """Checkout session creation rejects any inactive tier."""
        tier = _make_inactive_tier(slug, price)
        tier_repo = AsyncMock()
        tier_repo.get_by_id = AsyncMock(return_value=tier)

        svc = CheckoutService(
            session=_mock_session_with_consent(),
            tier_repo=tier_repo,
            stripe_settings=MagicMock(
                stripe_secret_key="sk_test",
                stripe_tax_enabled=False,
            ),
        )

        with pytest.raises(TierInactiveError):
            await svc.create_checkout_session(
                tier_id=tier.id,
                package_type="residential",
                consent_token=uuid4(),
            )

    @given(slug=slugs, price=prices)
    @settings(max_examples=30)
    async def test_agreement_creation_rejects_inactive_tier(
        self,
        slug: str,
        price: Decimal,
    ) -> None:
        """Agreement creation rejects any inactive tier."""
        tier = _make_inactive_tier(slug, price)
        tier_repo = AsyncMock()
        tier_repo.get_by_id = AsyncMock(return_value=tier)
        agreement_repo = AsyncMock()

        svc = AgreementService(
            agreement_repo=agreement_repo,
            tier_repo=tier_repo,
            stripe_settings=MagicMock(is_configured=False),
        )

        with pytest.raises(InactiveTierError):
            await svc.create_agreement(uuid4(), tier.id)

        agreement_repo.create.assert_not_called()

    @given(slug=slugs, price=prices)
    @settings(max_examples=30)
    async def test_active_tier_accepted_for_agreement(
        self,
        slug: str,
        price: Decimal,
    ) -> None:
        """Active tiers are accepted for agreement creation (contrast test)."""
        tier = _make_active_tier(slug, price)
        tier_repo = AsyncMock()
        tier_repo.get_by_id = AsyncMock(return_value=tier)

        agreement_repo = AsyncMock()
        agreement_repo.get_next_agreement_number_seq = AsyncMock(return_value=1)
        created = MagicMock()
        created.id = uuid4()

        def capture_create(**kwargs: object) -> MagicMock:
            for k, v in kwargs.items():
                setattr(created, k, v)
            return created

        agreement_repo.create = AsyncMock(side_effect=capture_create)

        svc = AgreementService(
            agreement_repo=agreement_repo,
            tier_repo=tier_repo,
            stripe_settings=MagicMock(is_configured=False),
        )

        result = await svc.create_agreement(uuid4(), tier.id)
        agreement_repo.create.assert_called_once()
        assert result is created
