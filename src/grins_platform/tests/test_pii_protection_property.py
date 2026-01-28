"""Property-based tests for PII protection in AI prompts.

Validates: Schedule AI Updates Requirement 2.7
Property 1: PII Protection - AI prompts never contain full addresses,
phone numbers, or emails.
"""

import re
from datetime import date
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from hypothesis import (
    given,
    strategies as st,
)

from grins_platform.schemas.schedule_explanation import (
    ScheduleExplanationRequest,
    StaffAssignmentSummary,
)
from grins_platform.services.ai.explanation_service import (
    ScheduleExplanationService,
)


# Strategies for generating test data
@st.composite
def staff_assignment_strategy(draw: st.DrawFn) -> StaffAssignmentSummary:
    """Generate random staff assignment with potential PII."""
    return StaffAssignmentSummary(
        staff_id=uuid4(),
        staff_name=draw(st.text(min_size=1, max_size=50)),
        job_count=draw(st.integers(min_value=1, max_value=20)),
        total_minutes=draw(st.integers(min_value=30, max_value=480)),
        cities=draw(
            st.lists(st.text(min_size=1, max_size=30), min_size=1, max_size=5),
        ),
        job_types=draw(
            st.lists(st.text(min_size=1, max_size=30), min_size=1, max_size=3),
        ),
    )


@st.composite
def schedule_request_strategy(draw: st.DrawFn) -> ScheduleExplanationRequest:
    """Generate random schedule explanation request."""
    return ScheduleExplanationRequest(
        schedule_date=date(2025, 1, 27),
        staff_assignments=draw(
            st.lists(staff_assignment_strategy(), min_size=1, max_size=5),
        ),
        unassigned_job_count=draw(st.integers(min_value=0, max_value=10)),
    )


# PII detection patterns
PHONE_PATTERN = re.compile(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b")
EMAIL_PATTERN = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
)
# Full address pattern (street number + street name)
ADDRESS_PATTERN = re.compile(
    r"\b\d+\s+[A-Za-z]+\s+(Street|St|Avenue|Ave|Road|Rd|Drive|Dr|"
    r"Lane|Ln|Boulevard|Blvd)\b",
    re.IGNORECASE,
)


def contains_pii(text: str) -> tuple[bool, str]:
    """Check if text contains PII.

    Args:
        text: Text to check

    Returns:
        Tuple of (has_pii, pii_type)
    """
    if PHONE_PATTERN.search(text):
        return True, "phone number"
    if EMAIL_PATTERN.search(text):
        return True, "email"
    if ADDRESS_PATTERN.search(text):
        return True, "full address"
    return False, ""


@pytest.mark.unit
class TestPIIProtectionProperty:
    """Property-based tests for PII protection.

    Validates: Requirement 2.7
    """

    @given(request=schedule_request_strategy())
    def test_schedule_context_never_contains_pii(
        self,
        request: ScheduleExplanationRequest,
    ) -> None:
        """Property: Schedule context never contains PII.

        Validates: Requirement 2.7

        Args:
            request: Random schedule explanation request
        """
        mock_session = AsyncMock()
        service = ScheduleExplanationService(mock_session)

        # Build context
        context = service._build_schedule_context(request)

        # Convert context to string for PII detection
        context_str = str(context)

        # Check for PII
        has_pii, pii_type = contains_pii(context_str)

        assert not has_pii, f"Context contains {pii_type}: {context_str}"

    @given(request=schedule_request_strategy())
    def test_explanation_prompt_never_contains_pii(
        self,
        request: ScheduleExplanationRequest,
    ) -> None:
        """Property: Explanation prompt never contains PII.

        Validates: Requirement 2.7

        Args:
            request: Random schedule explanation request
        """
        mock_session = AsyncMock()
        service = ScheduleExplanationService(mock_session)

        # Build context and create prompt
        context = service._build_schedule_context(request)
        prompt = service._create_explanation_prompt(context)

        # Check for PII in prompt
        has_pii, pii_type = contains_pii(prompt)

        assert not has_pii, f"Prompt contains {pii_type}: {prompt}"

    @given(request=schedule_request_strategy())
    @patch("grins_platform.services.ai.explanation_service.AIAgentService")
    @pytest.mark.asyncio
    async def test_ai_service_never_receives_pii(
        self,
        mock_ai_service_class: AsyncMock,
        request: ScheduleExplanationRequest,
    ) -> None:
        """Property: AI service never receives PII in prompts.

        Validates: Requirement 2.7

        Args:
            mock_ai_service_class: Mock AI service class
            request: Random schedule explanation request
        """
        # Setup mock
        mock_ai_instance = AsyncMock()
        mock_ai_instance.chat = AsyncMock(
            return_value="Test explanation",
        )
        mock_ai_service_class.return_value = mock_ai_instance

        mock_session = AsyncMock()
        service = ScheduleExplanationService(mock_session)

        # Call explain_schedule
        await service.explain_schedule(request)

        # Verify AI service was called
        assert mock_ai_instance.chat.called

        # Get the prompt that was sent to AI
        call_args = mock_ai_instance.chat.call_args
        prompt = call_args.kwargs.get("message", "")
        context = call_args.kwargs.get("context", {})

        # Check prompt for PII
        has_pii_prompt, pii_type_prompt = contains_pii(prompt)
        assert not has_pii_prompt, (
            f"AI received prompt with {pii_type_prompt}: {prompt}"
        )

        # Check context for PII
        context_str = str(context)
        has_pii_context, pii_type_context = contains_pii(context_str)
        assert not has_pii_context, (
            f"AI received context with {pii_type_context}: {context_str}"
        )
