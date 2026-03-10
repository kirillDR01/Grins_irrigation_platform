"""Property test for annual price lock at purchase.

Property 11: Annual Price Lock at Purchase
For any ServiceAgreement, annual_price at creation remains unchanged
regardless of tier price modifications.

Validates: Requirements 2.4
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from hypothesis import (
    given,
    settings,
    strategies as st,
)

from grins_platform.models.enums import AgreementStatus
from grins_platform.services.agreement_service import AgreementService

prices = st.decimals(min_value=Decimal("1.00"), max_value=Decimal("9999.99"), places=2)


def _make_tier(annual_price: Decimal) -> MagicMock:
    tier = MagicMock()
    tier.id = uuid4()
    tier.annual_price = annual_price
    tier.name = "Test"
    tier.slug = "test"
    tier.is_active = True
    tier.stripe_price_id = "price_test"
    return tier


def _make_service(tier: MagicMock) -> tuple[AgreementService, AsyncMock]:
    tier_repo = AsyncMock()
    tier_repo.get_by_id = AsyncMock(return_value=tier)

    agreement_repo = AsyncMock()
    agreement_repo.get_next_agreement_number_seq = AsyncMock(return_value=1)
    # create returns a mock with the kwargs passed to it
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
    return svc, agreement_repo


@pytest.mark.unit
@pytest.mark.asyncio
class TestAnnualPriceLockProperty:
    """Property-based tests for annual price lock at purchase."""

    @given(tier_price=prices)
    @settings(max_examples=50)
    async def test_agreement_locks_tier_price_at_creation(
        self,
        tier_price: Decimal,
    ) -> None:
        """Agreement annual_price equals tier price at creation time."""
        tier = _make_tier(tier_price)
        svc, repo = _make_service(tier)

        await svc.create_agreement(uuid4(), tier.id)

        repo.create.assert_called_once()
        call_kwargs = repo.create.call_args.kwargs
        assert call_kwargs["annual_price"] == tier_price

    @given(tier_price=prices, new_tier_price=prices)
    @settings(max_examples=50)
    async def test_tier_price_change_does_not_affect_agreement(
        self,
        tier_price: Decimal,
        new_tier_price: Decimal,
    ) -> None:
        """Changing tier price after creation doesn't alter agreement price."""
        tier = _make_tier(tier_price)
        svc, _repo = _make_service(tier)

        agreement = await svc.create_agreement(uuid4(), tier.id)

        # Mutate tier price after agreement creation
        tier.annual_price = new_tier_price

        # Agreement's locked price is unchanged
        assert agreement.annual_price == tier_price
        assert agreement.status == AgreementStatus.PENDING.value
