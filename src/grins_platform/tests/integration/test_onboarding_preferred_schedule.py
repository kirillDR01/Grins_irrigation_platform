"""Integration tests for preferred_schedule via the onboarding API.

Tests the POST /api/v1/onboarding/complete endpoint end-to-end,
verifying the response and database state.

Validates: preferred_schedule round-trip through API -> service -> DB.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import select

from grins_platform.models.customer import Customer
from grins_platform.models.service_agreement import ServiceAgreement

if TYPE_CHECKING:
    from httpx import AsyncClient
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
    session.customer_details.name = "Integration Test"
    session.customer_details.email = "integration@example.com"
    session.customer_details.phone = "6125550000"
    session.customer_details.address = MagicMock()
    session.customer_details.address.line1 = "456 Oak Ave"
    session.customer_details.address.line2 = ""
    session.customer_details.address.city = "St Paul"
    session.customer_details.address.state = "MN"
    session.customer_details.address.postal_code = "55101"
    session.customer_details.address.country = "US"
    session.payment_status = "paid"
    return session


@pytest.mark.integration
class TestOnboardingPreferredScheduleAPI:
    """Integration tests for preferred_schedule through the API."""

    @pytest.mark.asyncio
    async def test_complete_onboarding_with_schedule(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """POST /complete with ONE_TWO_WEEKS saves to DB."""
        customer = Customer(
            first_name="Integration",
            last_name="Test",
            phone="6125550000",
            email="integration@example.com",
        )
        db_session.add(customer)
        await db_session.flush()

        agreement = ServiceAgreement(
            customer_id=customer.id,
            stripe_subscription_id="sub_int_123",
            status="active",
            tier_slug="essential-residential",
            package_type="residential",
        )
        db_session.add(agreement)
        await db_session.commit()

        stripe_session = _mock_stripe_session("sub_int_123")
        patch_target = "grins_platform.services.onboarding_service.stripe"
        with patch(patch_target) as mock_stripe:
            mock_stripe.checkout.Session.retrieve.return_value = stripe_session
            mock_stripe.InvalidRequestError = Exception

            response = await async_client.post(
                "/api/v1/onboarding/complete",
                json={
                    "session_id": "cs_int_123",
                    "preferred_schedule": "ONE_TWO_WEEKS",
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert "agreement_id" in data

        stmt = select(Customer).where(
            Customer.id == customer.id,
        )
        result = await db_session.execute(stmt)
        updated = result.scalar_one()
        assert updated.preferred_schedule == "ONE_TWO_WEEKS"
        assert updated.preferred_schedule_details is None

    @pytest.mark.asyncio
    async def test_complete_onboarding_rejects_other_without_details(
        self,
        async_client: AsyncClient,
    ) -> None:
        """POST /complete with OTHER but no details returns 422."""
        response = await async_client.post(
            "/api/v1/onboarding/complete",
            json={
                "session_id": "cs_int_456",
                "preferred_schedule": "OTHER",
            },
        )
        assert response.status_code == 422
