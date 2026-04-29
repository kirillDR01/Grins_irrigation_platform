"""Unit tests for required service_week_preferences in onboarding.

Covers three layers:

1. ``CompleteOnboardingRequest`` Pydantic validation — field is required,
   allows ``None`` values as "No preference", rejects malformed ISO dates.

2. ``expected_job_types_for_tier`` helper — derives the expected set of
   job_types from a tier's ``included_services``, expanding
   ``monthly_visit`` (frequency ``5x``) into ``monthly_visit_5..9``.

3. ``OnboardingService.complete_onboarding`` — raises
   ``IncompleteServiceWeekPreferencesError`` when the submitted keys
   don't cover every expected job_type, and persists the full agreement
   snapshot (tier name/slug, preferred service time, access
   instructions, gate code, dogs flag, no_preference_flags) on success.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from pydantic import ValidationError

from grins_platform.api.v1.onboarding import CompleteOnboardingRequest
from grins_platform.services.onboarding_service import (
    IncompleteServiceWeekPreferencesError,
    OnboardingService,
    expected_job_types_for_tier,
)

# ---------------------------------------------------------------------------
# 1. Pydantic schema: field required + value validation
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCompleteOnboardingRequestValidation:
    """Schema-level validation for service_week_preferences."""

    def test_field_is_required(self) -> None:
        """Omitting service_week_preferences raises ValidationError."""
        with pytest.raises(ValidationError, match="service_week_preferences"):
            CompleteOnboardingRequest(session_id="cs_test_123")  # type: ignore[call-arg]

    def test_accepts_empty_dict(self) -> None:
        """Empty dict is allowed at the schema layer.

        The tier-completeness check runs later in the service layer, not
        here — the schema just cares about shape.
        """
        req = CompleteOnboardingRequest(
            session_id="cs_test_123",
            service_week_preferences={},
        )
        assert req.service_week_preferences == {}

    def test_accepts_null_values_as_no_preference(self) -> None:
        """A null value means "explicit No preference"."""
        req = CompleteOnboardingRequest(
            session_id="cs_test_123",
            service_week_preferences={
                "spring_startup": None,
                "fall_winterization": "2026-04-06",
            },
        )
        assert req.service_week_preferences["spring_startup"] is None
        assert req.service_week_preferences["fall_winterization"] == "2026-04-06"

    def test_rejects_malformed_iso_date(self) -> None:
        """Non-null value must be a YYYY-MM-DD string."""
        with pytest.raises(ValidationError, match="not a valid ISO date"):
            CompleteOnboardingRequest(
                session_id="cs_test_123",
                service_week_preferences={"spring_startup": "not-a-date"},
            )


# ---------------------------------------------------------------------------
# 2. expected_job_types_for_tier — derives required keys per tier
# ---------------------------------------------------------------------------


def _tier(included: list[dict[str, Any]]) -> SimpleNamespace:
    return SimpleNamespace(included_services=included)


@pytest.mark.unit
class TestExpectedJobTypesForTier:
    """Helper for deriving expected service_week_preferences keys."""

    def test_essential_tier(self) -> None:
        tier = _tier(
            [
                {"service_type": "spring_startup", "frequency": "1x"},
                {"service_type": "fall_winterization", "frequency": "1x"},
            ]
        )
        assert expected_job_types_for_tier(tier) == {
            "spring_startup",
            "fall_winterization",
        }

    def test_professional_tier(self) -> None:
        tier = _tier(
            [
                {"service_type": "spring_startup", "frequency": "1x"},
                {"service_type": "mid_season_inspection", "frequency": "1x"},
                {"service_type": "fall_winterization", "frequency": "1x"},
            ]
        )
        assert expected_job_types_for_tier(tier) == {
            "spring_startup",
            "mid_season_inspection",
            "fall_winterization",
        }

    def test_premium_tier_expands_monthly_visit_into_five(self) -> None:
        tier = _tier(
            [
                {"service_type": "spring_startup", "frequency": "1x"},
                {"service_type": "monthly_visit", "frequency": "5x"},
                {"service_type": "fall_winterization", "frequency": "1x"},
            ]
        )
        assert expected_job_types_for_tier(tier) == {
            "spring_startup",
            "monthly_visit_5",
            "monthly_visit_6",
            "monthly_visit_7",
            "monthly_visit_8",
            "monthly_visit_9",
            "fall_winterization",
        }

    def test_winterization_only_tier(self) -> None:
        tier = _tier(
            [
                {"service_type": "fall_winterization", "frequency": "1x"},
            ]
        )
        assert expected_job_types_for_tier(tier) == {"fall_winterization"}

    def test_empty_included_services(self) -> None:
        tier = _tier([])
        assert expected_job_types_for_tier(tier) == set()

    def test_tolerates_malformed_service_entries(self) -> None:
        """Entries missing service_type are ignored (forward-compat)."""
        tier = _tier(
            [
                {"service_type": "spring_startup"},
                {"frequency": "1x"},  # no service_type
                {},
            ]
        )
        assert expected_job_types_for_tier(tier) == {"spring_startup"}


# ---------------------------------------------------------------------------
# 3. OnboardingService.complete_onboarding — tier-completeness + snapshot
# ---------------------------------------------------------------------------


def _premium_tier_included() -> list[dict[str, Any]]:
    return [
        {"service_type": "spring_startup", "frequency": "1x"},
        {"service_type": "monthly_visit", "frequency": "5x"},
        {"service_type": "fall_winterization", "frequency": "1x"},
    ]


def _essential_tier_included() -> list[dict[str, Any]]:
    return [
        {"service_type": "spring_startup", "frequency": "1x"},
        {"service_type": "fall_winterization", "frequency": "1x"},
    ]


def _make_agreement(
    *,
    tier_included: list[dict[str, Any]],
    tier_slug: str = "essential-residential",
    tier_name: str = "Essential",
) -> MagicMock:
    agr = MagicMock()
    agr.id = uuid4()
    agr.customer_id = uuid4()
    agr.stripe_subscription_id = "sub_123"
    agr.jobs = []
    agr.customer = MagicMock()
    agr.customer.preferred_service_times = None
    agr.property = None
    agr.tier = MagicMock()
    agr.tier.slug = tier_slug
    agr.tier.name = tier_name
    agr.tier.included_services = tier_included
    return agr


def _make_service(
    agreement: MagicMock,
    *,
    property_repo: AsyncMock | None = None,
    agreement_repo: AsyncMock | None = None,
    db_session: AsyncMock | None = None,
) -> OnboardingService:
    prop_mock = MagicMock()
    prop_mock.id = uuid4()
    property_repo = property_repo or AsyncMock(create=AsyncMock(return_value=prop_mock))
    agreement_repo = agreement_repo or AsyncMock(
        update=AsyncMock(return_value=agreement),
    )
    db_session = db_session or AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = agreement
    db_session.execute = AsyncMock(return_value=result_mock)

    from grins_platform.services.stripe_config import StripeSettings

    stripe_settings = StripeSettings(
        stripe_secret_key="sk_test_xxx",
        stripe_webhook_secret="whsec_xxx",
        stripe_customer_portal_url="https://billing.stripe.com/portal",
    )
    return OnboardingService(
        session=db_session,
        agreement_repo=agreement_repo,
        property_repo=property_repo,
        tier_repo=None,
        stripe_settings=stripe_settings,
    )


@pytest.mark.unit
class TestCompleteOnboardingTierCompleteness:
    """complete_onboarding enforces tier coverage and persists snapshot."""

    @pytest.mark.asyncio
    @patch(
        "grins_platform.services.onboarding_service.stripe.checkout.Session.retrieve",
    )
    async def test_raises_when_premium_prefs_missing_monthly_keys(
        self,
        mock_retrieve: MagicMock,
    ) -> None:
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
        agreement = _make_agreement(
            tier_included=_premium_tier_included(),
            tier_slug="premium-residential",
            tier_name="Premium",
        )
        svc = _make_service(agreement)
        partial_prefs = {
            "spring_startup": None,
            "fall_winterization": None,
            # monthly_visit_5..9 all missing
        }
        with pytest.raises(IncompleteServiceWeekPreferencesError) as exc_info:
            await svc.complete_onboarding(
                "cs_test_123",
                service_week_preferences=partial_prefs,
            )
        err = exc_info.value
        assert err.missing_job_types == {
            "monthly_visit_5",
            "monthly_visit_6",
            "monthly_visit_7",
            "monthly_visit_8",
            "monthly_visit_9",
        }

    @pytest.mark.asyncio
    @patch(
        "grins_platform.services.onboarding_service.stripe.checkout.Session.retrieve",
    )
    async def test_raises_when_essential_prefs_empty(
        self,
        mock_retrieve: MagicMock,
    ) -> None:
        mock_retrieve.return_value = SimpleNamespace(
            subscription="sub_123",
            customer_details=None,
        )
        agreement = _make_agreement(tier_included=_essential_tier_included())
        svc = _make_service(agreement)
        with pytest.raises(IncompleteServiceWeekPreferencesError) as exc_info:
            await svc.complete_onboarding(
                "cs_test_123",
                service_week_preferences={},
            )
        assert exc_info.value.missing_job_types == {
            "spring_startup",
            "fall_winterization",
        }

    @pytest.mark.asyncio
    @patch(
        "grins_platform.services.onboarding_service.stripe.checkout.Session.retrieve",
    )
    async def test_accepts_complete_prefs_with_mix_of_dates_and_nulls(
        self,
        mock_retrieve: MagicMock,
    ) -> None:
        mock_retrieve.return_value = SimpleNamespace(
            subscription="sub_123",
            customer_details=None,
        )
        agreement = _make_agreement(tier_included=_essential_tier_included())
        svc = _make_service(agreement)
        await svc.complete_onboarding(
            "cs_test_123",
            service_week_preferences={
                "spring_startup": "2026-04-06",
                "fall_winterization": None,
            },
        )
        # Should have reached agreement_repo.update without raising.
        # The chosen Monday for spring_startup also propagates to the
        # agreement's stored service_week_preferences (verified in the
        # job-date propagation test below); access_instructions /
        # gate_code / has_dogs / preferred_times go to property and
        # customer rows, not the agreement.

    @pytest.mark.asyncio
    @patch(
        "grins_platform.services.onboarding_service.stripe.checkout.Session.retrieve",
    )
    async def test_applies_chosen_week_to_existing_jobs(
        self,
        mock_retrieve: MagicMock,
    ) -> None:
        """Chosen Monday rewrites job target_start_date/target_end_date.

        Jobs are created at Stripe-webhook time with a full-month
        default. When the customer submits an explicit preferred week at
        onboarding completion, that job's target range must shrink to
        the Mon-Sun of the chosen week in-place.
        """
        import datetime as _dt

        mock_retrieve.return_value = SimpleNamespace(
            subscription="sub_123",
            customer_details=None,
        )
        spring_job = MagicMock()
        spring_job.job_type = "spring_startup"
        spring_job.target_start_date = _dt.date(2026, 4, 1)
        spring_job.target_end_date = _dt.date(2026, 4, 30)
        spring_job.property_id = None
        fall_job = MagicMock()
        fall_job.job_type = "fall_winterization"
        fall_job.target_start_date = _dt.date(2026, 10, 1)
        fall_job.target_end_date = _dt.date(2026, 10, 31)
        fall_job.property_id = None

        agreement = _make_agreement(tier_included=_essential_tier_included())
        agreement.jobs = [spring_job, fall_job]
        svc = _make_service(agreement)

        await svc.complete_onboarding(
            "cs_test_123",
            service_week_preferences={
                "spring_startup": "2026-04-20",  # Monday of week
                "fall_winterization": None,  # No preference
            },
        )
        # Spring job now spans Mon Apr 20 - Sun Apr 26
        assert spring_job.target_start_date == _dt.date(2026, 4, 20)
        assert spring_job.target_end_date == _dt.date(2026, 4, 26)
        # Fall job kept its default full-month range (null = no preference)
        assert fall_job.target_start_date == _dt.date(2026, 10, 1)
        assert fall_job.target_end_date == _dt.date(2026, 10, 31)

    @pytest.mark.asyncio
    @patch(
        "grins_platform.services.onboarding_service.stripe.checkout.Session.retrieve",
    )
    async def test_persists_only_week_prefs_on_agreement(
        self,
        mock_retrieve: MagicMock,
    ) -> None:
        """Agreement update carries service_week_preferences only.

        Live values for gate_code, has_dogs, access_instructions, and
        preferred_service_time live on properties / customers and are
        not duplicated on the agreement. The snapshot columns added in
        20260414_100200 were dropped in 20260414_100400 to keep the
        schema clean.
        """
        mock_retrieve.return_value = SimpleNamespace(
            subscription="sub_123",
            customer_details=None,
        )
        agreement = _make_agreement(
            tier_included=_essential_tier_included(),
            tier_slug="essential-commercial",
            tier_name="Essential",
        )
        agreement_repo = AsyncMock(update=AsyncMock(return_value=agreement))
        svc = _make_service(agreement, agreement_repo=agreement_repo)
        await svc.complete_onboarding(
            "cs_test_123",
            gate_code="1234",
            has_dogs=True,
            access_instructions="Side gate",
            preferred_times="MORNING",
            service_week_preferences={
                "spring_startup": "2026-04-06",
                "fall_winterization": None,
            },
        )

        update_payload = agreement_repo.update.call_args[0][1]
        # Customer's raw week selections are stored on the agreement
        assert update_payload["service_week_preferences"] == {
            "spring_startup": "2026-04-06",
            "fall_winterization": None,
        }
        # property_id + scheduling preference round out the agreement update
        assert "property_id" in update_payload
        assert update_payload["preferred_schedule"] == "ASAP"
        # Snapshot fields removed in migration 20260414_100400 must not be
        # present in the agreement update payload anymore
        for dropped in (
            "tier_slug_snapshot",
            "tier_name_snapshot",
            "preferred_service_time",
            "access_instructions",
            "gate_code",
            "dogs_on_property",
            "no_preference_flags",
        ):
            assert dropped not in update_payload, (
                f"Agreement update should not write {dropped!r} — "
                "it duplicates data on properties/customers/tier."
            )
