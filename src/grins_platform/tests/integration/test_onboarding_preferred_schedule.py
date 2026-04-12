"""Integration tests for preferred_schedule via the onboarding API.

Tests the POST /api/v1/onboarding/complete endpoint end-to-end,
verifying the response and database state.

Validates: preferred_schedule round-trip through API -> service -> DB.

NOTE: These tests require a real database session fixture (async_client +
db_session) which is not yet available in the test infrastructure.
They are skipped until the DB integration test setup is complete.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from httpx import AsyncClient


@pytest.mark.integration
class TestOnboardingPreferredScheduleAPI:
    """Integration tests for preferred_schedule through the API."""

    @pytest.mark.asyncio
    async def test_complete_onboarding_with_schedule(
        self,
        authenticated_client: AsyncClient,
    ) -> None:
        """POST /complete with ONE_TWO_WEEKS saves to agreement in DB."""
        pytest.skip(
            "Requires real DB session fixture — deferred to DB integration setup",
        )

    @pytest.mark.asyncio
    async def test_complete_onboarding_rejects_other_without_details(
        self,
        authenticated_client: AsyncClient,
    ) -> None:
        """POST /complete with OTHER but no details returns 422."""
        pytest.skip(
            "Requires real DB session fixture — deferred to DB integration setup",
        )
