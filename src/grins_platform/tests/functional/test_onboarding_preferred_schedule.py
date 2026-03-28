"""Functional tests for preferred_schedule onboarding persistence.

Tests real DB writes via OnboardingService to verify preferred_schedule
and preferred_schedule_details are saved to the customer record.

Validates: preferred_schedule column persistence in customers table.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import select

from grins_platform.models.customer import Customer
from grins_platform.models.service_agreement import ServiceAgreement
from grins_platform.repositories.agreement_repository import (
    AgreementRepository,
)
from grins_platform.repositories.agreement_tier_repository import (
    AgreementTierRepository,
)
from grins_platform.repositories.property_repository import (
    PropertyRepository,
)
from grins_platform.services.onboarding_service import OnboardingService

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


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


@pytest.mark.functional
class TestOnboardingPreferredSchedulePersistence:
    """Functional tests verifying preferred_schedule DB persistence."""

    @pytest.mark.asyncio
    async def test_saves_one_two_weeks(
        self,
        db_session: AsyncSession,
    ) -> None:
        """complete_onboarding persists ONE_TWO_WEEKS to customer."""
        customer = Customer(
            first_name="Test",
            last_name="User",
            phone="6125551234",
            email="test@example.com",
        )
        db_session.add(customer)
        await db_session.flush()

        agreement = ServiceAgreement(
            customer_id=customer.id,
            stripe_subscription_id="sub_test_123",
            status="active",
            tier_slug="essential-residential",
            package_type="residential",
        )
        db_session.add(agreement)
        await db_session.flush()

        service = OnboardingService(
            session=db_session,
            agreement_repo=AgreementRepository(session=db_session),
            property_repo=PropertyRepository(session=db_session),
            tier_repo=AgreementTierRepository(session=db_session),
        )

        stripe_session = _mock_stripe_session("sub_test_123")
        patch_target = "grins_platform.services.onboarding_service.stripe"
        with patch(patch_target) as mock_stripe:
            mock_stripe.checkout.Session.retrieve.return_value = stripe_session

            await service.complete_onboarding(
                session_id="cs_test_123",
                preferred_schedule="ONE_TWO_WEEKS",
            )
            await db_session.flush()

        stmt = select(Customer).where(
            Customer.id == customer.id,
        )
        result = await db_session.execute(stmt)
        updated = result.scalar_one()
        assert updated.preferred_schedule == "ONE_TWO_WEEKS"
        assert updated.preferred_schedule_details is None

    @pytest.mark.asyncio
    async def test_saves_other_with_details(
        self,
        db_session: AsyncSession,
    ) -> None:
        """complete_onboarding persists OTHER + details to customer."""
        customer = Customer(
            first_name="Other",
            last_name="User",
            phone="6125559876",
            email="other@example.com",
        )
        db_session.add(customer)
        await db_session.flush()

        agreement = ServiceAgreement(
            customer_id=customer.id,
            stripe_subscription_id="sub_test_456",
            status="active",
            tier_slug="essential-residential",
            package_type="residential",
        )
        db_session.add(agreement)
        await db_session.flush()

        service = OnboardingService(
            session=db_session,
            agreement_repo=AgreementRepository(session=db_session),
            property_repo=PropertyRepository(session=db_session),
            tier_repo=AgreementTierRepository(session=db_session),
        )

        stripe_session = _mock_stripe_session("sub_test_456")
        patch_target = "grins_platform.services.onboarding_service.stripe"
        with patch(patch_target) as mock_stripe:
            mock_stripe.checkout.Session.retrieve.return_value = stripe_session

            await service.complete_onboarding(
                session_id="cs_test_456",
                preferred_schedule="OTHER",
                preferred_schedule_details="Week of April 14th",
            )
            await db_session.flush()

        stmt = select(Customer).where(
            Customer.id == customer.id,
        )
        result = await db_session.execute(stmt)
        updated = result.scalar_one()
        assert updated.preferred_schedule == "OTHER"
        assert updated.preferred_schedule_details == ("Week of April 14th")

    @pytest.mark.asyncio
    async def test_asap_has_no_details(
        self,
        db_session: AsyncSession,
    ) -> None:
        """complete_onboarding with ASAP leaves details as None."""
        customer = Customer(
            first_name="Asap",
            last_name="User",
            phone="6125554321",
            email="asap@example.com",
        )
        db_session.add(customer)
        await db_session.flush()

        agreement = ServiceAgreement(
            customer_id=customer.id,
            stripe_subscription_id="sub_test_789",
            status="active",
            tier_slug="essential-residential",
            package_type="residential",
        )
        db_session.add(agreement)
        await db_session.flush()

        service = OnboardingService(
            session=db_session,
            agreement_repo=AgreementRepository(session=db_session),
            property_repo=PropertyRepository(session=db_session),
            tier_repo=AgreementTierRepository(session=db_session),
        )

        stripe_session = _mock_stripe_session("sub_test_789")
        patch_target = "grins_platform.services.onboarding_service.stripe"
        with patch(patch_target) as mock_stripe:
            mock_stripe.checkout.Session.retrieve.return_value = stripe_session

            await service.complete_onboarding(
                session_id="cs_test_789",
                preferred_schedule="ASAP",
            )
            await db_session.flush()

        stmt = select(Customer).where(
            Customer.id == customer.id,
        )
        result = await db_session.execute(stmt)
        updated = result.scalar_one()
        assert updated.preferred_schedule == "ASAP"
        assert updated.preferred_schedule_details is None
