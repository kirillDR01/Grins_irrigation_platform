"""Unit tests for preferred_schedule in CompleteOnboardingRequest.

Validates: preferred_schedule field validation, defaults, and enum enforcement.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from grins_platform.api.v1.onboarding import CompleteOnboardingRequest

_DETAILS_REQUIRED = "preferred_schedule_details is required"


@pytest.mark.unit
class TestCompleteOnboardingRequestPreferredSchedule:
    """Tests for preferred_schedule validation."""

    def test_defaults_to_asap(self) -> None:
        """preferred_schedule defaults to ASAP when not provided."""
        req = CompleteOnboardingRequest(session_id="cs_test_123")
        assert req.preferred_schedule == "ASAP"
        assert req.preferred_schedule_details is None

    def test_validates_other_requires_details(self) -> None:
        """OTHER without details raises ValidationError."""
        with pytest.raises(
            ValidationError,
            match=_DETAILS_REQUIRED,
        ):
            CompleteOnboardingRequest(
                session_id="cs_test_123",
                preferred_schedule="OTHER",
            )

    def test_validates_other_rejects_blank_details(self) -> None:
        """OTHER with whitespace-only details raises ValidationError."""
        with pytest.raises(
            ValidationError,
            match=_DETAILS_REQUIRED,
        ):
            CompleteOnboardingRequest(
                session_id="cs_test_123",
                preferred_schedule="OTHER",
                preferred_schedule_details="   ",
            )

    @pytest.mark.parametrize(
        "value",
        ["ASAP", "ONE_TWO_WEEKS", "THREE_FOUR_WEEKS"],
    )
    def test_accepts_all_non_other_enum_values(
        self,
        value: str,
    ) -> None:
        """All non-OTHER enum values are accepted without details."""
        req = CompleteOnboardingRequest(
            session_id="cs_test_123",
            preferred_schedule=value,
        )
        assert req.preferred_schedule == value

    def test_accepts_other_with_details(self) -> None:
        """OTHER with valid details is accepted."""
        req = CompleteOnboardingRequest(
            session_id="cs_test_123",
            preferred_schedule="OTHER",
            preferred_schedule_details="Week of April 14th",
        )
        assert req.preferred_schedule == "OTHER"
        assert req.preferred_schedule_details == "Week of April 14th"

    def test_rejects_invalid_schedule(self) -> None:
        """Invalid preferred_schedule value raises ValidationError."""
        with pytest.raises(
            ValidationError,
            match="preferred_schedule must be one of",
        ):
            CompleteOnboardingRequest(
                session_id="cs_test_123",
                preferred_schedule="NEXT_MONTH",
            )
