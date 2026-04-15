"""Functional tests for preferred_schedule onboarding persistence.

Tests OnboardingService to verify preferred_schedule
and preferred_schedule_details are passed through correctly.

Validates: preferred_schedule column persistence in service_agreements table.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from grins_platform.services.onboarding_service import OnboardingService


def _mock_stripe_session(subscription_id: str) -> MagicMock:
    """Build a mock Stripe Checkout Session."""
    session = MagicMock()
    session.subscription = subscription_id
    session.metadata = {
        "package_tier": "essential-residential",
        "package_type": "residential",
    }
    session.customer_details = MagicMock()
    session.customer_details.name = "Test User"
    session.customer_details.email = "test@example.com"
    session.customer_details.phone = "6125551234"
    session.customer_details.address = MagicMock()
    session.customer_details.address.line1 = "123 Main St"
    session.customer_details.address.line2 = ""
    session.customer_details.address.city = "Minneapolis"
    session.customer_details.address.state = "MN"
    session.customer_details.address.postal_code = "55401"
    session.customer_details.address.country = "US"
    session.payment_status = "paid"
    return session


def _make_agreement(sub_id: str) -> MagicMock:
    """Build a mock ServiceAgreement."""
    agr = MagicMock()
    agr.id = uuid4()
    agr.customer_id = uuid4()
    agr.stripe_subscription_id = sub_id
    agr.preferred_schedule = None
    agr.preferred_schedule_details = None
    agr.jobs = []
    return agr


@pytest.mark.functional
class TestOnboardingPreferredSchedulePersistence:
    """Functional tests verifying preferred_schedule persistence."""

    @pytest.mark.asyncio
    async def test_saves_one_two_weeks(self) -> None:
        """complete_onboarding persists ONE_TWO_WEEKS to agreement."""
        mock_session = AsyncMock()
        # Mock session.execute for customer reload
        mock_session.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)),
        )
        agreement = _make_agreement("sub_test_123")
        updated_agreement = _make_agreement("sub_test_123")
        updated_agreement.preferred_schedule = "ONE_TWO_WEEKS"

        mock_agreement_repo = AsyncMock()
        mock_agreement_repo.update = AsyncMock(return_value=updated_agreement)
        mock_property_repo = AsyncMock()
        mock_prop = MagicMock()
        mock_prop.id = uuid4()
        mock_property_repo.create = AsyncMock(return_value=mock_prop)
        mock_tier_repo = AsyncMock()

        service = OnboardingService(
            session=mock_session,
            agreement_repo=mock_agreement_repo,
            property_repo=mock_property_repo,
            tier_repo=mock_tier_repo,
        )

        stripe_session = _mock_stripe_session("sub_test_123")
        with (
            patch(
                "grins_platform.services.onboarding_service.stripe",
            ) as mock_stripe,
            patch.object(
                service,
                "_find_agreement_by_subscription",
                new_callable=AsyncMock,
                return_value=agreement,
            ),
        ):
            mock_stripe.checkout.Session.retrieve.return_value = stripe_session

            result = await service.complete_onboarding(
                session_id="cs_test_123",
                preferred_schedule="ONE_TWO_WEEKS",
            )

        # Verify update was called with correct preferred_schedule
        update_call = mock_agreement_repo.update.call_args
        assert update_call[0][1]["preferred_schedule"] == "ONE_TWO_WEEKS"
        assert result.preferred_schedule == "ONE_TWO_WEEKS"

    @pytest.mark.asyncio
    async def test_saves_other_with_details(self) -> None:
        """complete_onboarding persists OTHER + details to agreement."""
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)),
        )
        agreement = _make_agreement("sub_test_456")
        updated_agreement = _make_agreement("sub_test_456")
        updated_agreement.preferred_schedule = "OTHER"
        updated_agreement.preferred_schedule_details = "Week of April 14th"

        mock_agreement_repo = AsyncMock()
        mock_agreement_repo.update = AsyncMock(return_value=updated_agreement)
        mock_property_repo = AsyncMock()
        mock_prop = MagicMock()
        mock_prop.id = uuid4()
        mock_property_repo.create = AsyncMock(return_value=mock_prop)
        mock_tier_repo = AsyncMock()

        service = OnboardingService(
            session=mock_session,
            agreement_repo=mock_agreement_repo,
            property_repo=mock_property_repo,
            tier_repo=mock_tier_repo,
        )

        stripe_session = _mock_stripe_session("sub_test_456")
        with (
            patch(
                "grins_platform.services.onboarding_service.stripe",
            ) as mock_stripe,
            patch.object(
                service,
                "_find_agreement_by_subscription",
                new_callable=AsyncMock,
                return_value=agreement,
            ),
        ):
            mock_stripe.checkout.Session.retrieve.return_value = stripe_session

            result = await service.complete_onboarding(
                session_id="cs_test_456",
                preferred_schedule="OTHER",
                preferred_schedule_details="Week of April 14th",
            )

        update_call = mock_agreement_repo.update.call_args
        assert update_call[0][1]["preferred_schedule"] == "OTHER"
        assert update_call[0][1]["preferred_schedule_details"] == "Week of April 14th"
        assert result.preferred_schedule == "OTHER"
        assert result.preferred_schedule_details == "Week of April 14th"

    @pytest.mark.asyncio
    async def test_asap_has_no_details(self) -> None:
        """complete_onboarding with ASAP leaves details as None."""
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)),
        )
        agreement = _make_agreement("sub_test_789")
        updated_agreement = _make_agreement("sub_test_789")
        updated_agreement.preferred_schedule = "ASAP"

        mock_agreement_repo = AsyncMock()
        mock_agreement_repo.update = AsyncMock(return_value=updated_agreement)
        mock_property_repo = AsyncMock()
        mock_prop = MagicMock()
        mock_prop.id = uuid4()
        mock_property_repo.create = AsyncMock(return_value=mock_prop)
        mock_tier_repo = AsyncMock()

        service = OnboardingService(
            session=mock_session,
            agreement_repo=mock_agreement_repo,
            property_repo=mock_property_repo,
            tier_repo=mock_tier_repo,
        )

        stripe_session = _mock_stripe_session("sub_test_789")
        with (
            patch(
                "grins_platform.services.onboarding_service.stripe",
            ) as mock_stripe,
            patch.object(
                service,
                "_find_agreement_by_subscription",
                new_callable=AsyncMock,
                return_value=agreement,
            ),
        ):
            mock_stripe.checkout.Session.retrieve.return_value = stripe_session

            result = await service.complete_onboarding(
                session_id="cs_test_789",
                preferred_schedule="ASAP",
            )

        update_call = mock_agreement_repo.update.call_args
        assert update_call[0][1]["preferred_schedule"] == "ASAP"
        assert update_call[0][1]["preferred_schedule_details"] is None
        assert result.preferred_schedule == "ASAP"
        assert result.preferred_schedule_details is None
