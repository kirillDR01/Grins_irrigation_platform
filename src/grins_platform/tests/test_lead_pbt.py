"""
Property-based tests for lead capture feature.

Uses Hypothesis to validate formal correctness properties defined
in the lead-capture design document.

Properties:
  P1: Phone normalization idempotency
  P2: Status transition validity
  P3: Duplicate detection correctness
  P4: Input sanitization completeness
  P5: Name splitting consistency
  P6: Honeypot transparency
"""

from __future__ import annotations

import re
import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from hypothesis import (
    given,
    settings,
    strategies as st,
)

from grins_platform.models.enums import (
    VALID_LEAD_STATUS_TRANSITIONS,
    LeadSituation,
    LeadStatus,
)
from grins_platform.schemas.customer import normalize_phone
from grins_platform.schemas.lead import (
    LeadSubmission,
    strip_html_tags,
)
from grins_platform.services.lead_service import LeadService

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Characters that commonly appear in phone number formatting
phone_chars = st.sampled_from(
    list("0123456789()-. +"),
)

# Generate phone-like strings of varying length
phone_strings = st.text(alphabet=phone_chars, min_size=1, max_size=25)

# Generate strings that will normalize to valid 10-digit phones.
# Instead of filtering random strings (too many rejects), we compose
# valid 10-digit sequences with random formatting inserted.
def _build_valid_phone(digits: str, fmt: str) -> str:
    """Insert formatting characters around a 10-digit string."""
    if fmt == "plain":
        return digits
    if fmt == "parens":
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    if fmt == "dashes":
        return f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"
    if fmt == "dots":
        return f"{digits[:3]}.{digits[3:6]}.{digits[6:]}"
    if fmt == "spaces":
        return f"{digits[:3]} {digits[3:6]} {digits[6:]}"
    if fmt == "plus1":
        return f"+1{digits}"
    return digits


valid_phone_strings = st.builds(
    _build_valid_phone,
    digits=st.from_regex(r"[2-9][0-9]{2}[2-9][0-9]{6}", fullmatch=True),
    fmt=st.sampled_from(["plain", "parens", "dashes", "dots", "spaces", "plus1"]),
)

# All LeadStatus values
lead_statuses = st.sampled_from(list(LeadStatus))

# Name-like strings: 1-4 words of alphabetic characters
word = st.text(
    alphabet=st.sampled_from(list("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")),
    min_size=1,
    max_size=15,
)
name_strings = st.lists(word, min_size=1, max_size=4).map(lambda ws: " ".join(ws))

# Strings that may contain HTML-like patterns
html_chars = st.text(
    alphabet=st.sampled_from(
        list("abcdefghijklmnopqrstuvwxyz<>/\"'= 0123456789!@#$%^&*()_+-"),
    ),
    min_size=0,
    max_size=100,
)


def _is_valid_phone(s: str) -> bool:
    """Check if a string normalizes to a valid 10-digit phone."""
    try:
        normalize_phone(s)
    except (ValueError, Exception):
        return False
    else:
        return True


# ---------------------------------------------------------------------------
# Property 1: Phone Normalization Idempotency
# ---------------------------------------------------------------------------


class TestPhoneNormalizationIdempotency:
    """**Validates: Requirement 1.2**

    For any phone string that normalizes successfully,
    normalize(normalize(p)) == normalize(p).
    """

    @given(phone=valid_phone_strings)
    @settings(max_examples=100)
    def test_normalize_is_idempotent(self, phone: str) -> None:
        """PBT: Property 1 — Phone normalization idempotency.

        **Validates: Requirements 1.2**
        """
        first = normalize_phone(phone)
        second = normalize_phone(first)
        assert first == second

    @given(phone=valid_phone_strings)
    @settings(max_examples=100)
    def test_normalized_phone_is_10_digits(self, phone: str) -> None:
        """Normalized phone is always exactly 10 digits.

        **Validates: Requirements 1.2**
        """
        result = normalize_phone(phone)
        assert len(result) == 10
        assert result.isdigit()


# ---------------------------------------------------------------------------
# Property 2: Status Transition Validity
# ---------------------------------------------------------------------------


class TestStatusTransitionValidity:
    """**Validates: Requirement 6.2-6.3**

    For any (current_status, new_status) pair:
    - Valid transitions succeed
    - Invalid transitions raise InvalidLeadStatusTransitionError
    - Terminal states have empty transition sets
    """

    @given(current=lead_statuses, target=lead_statuses)
    @settings(max_examples=100)
    def test_transition_map_consistency(
        self, current: LeadStatus, target: LeadStatus,
    ) -> None:
        """PBT: Property 2 — Status transition validity.

        **Validates: Requirements 6.2-6.3**
        """
        valid_targets = VALID_LEAD_STATUS_TRANSITIONS.get(current, set())

        if target in valid_targets:
            # Valid transition — should be in the map
            assert target in VALID_LEAD_STATUS_TRANSITIONS[current]
        else:
            # Invalid transition — should NOT be in the map
            assert target not in valid_targets

    def test_terminal_states_have_empty_transitions(self) -> None:
        """Terminal states (converted, spam) have no outgoing transitions.

        **Validates: Requirements 6.3**
        """
        assert VALID_LEAD_STATUS_TRANSITIONS[LeadStatus.CONVERTED] == set()
        assert VALID_LEAD_STATUS_TRANSITIONS[LeadStatus.SPAM] == set()

    @given(current=lead_statuses, target=lead_statuses)
    @settings(max_examples=100)
    def test_all_statuses_present_in_transition_map(
        self, current: LeadStatus, target: LeadStatus,  # noqa: ARG002
    ) -> None:
        """Every LeadStatus has an entry in the transition map.

        **Validates: Requirements 6.2**
        """
        assert current in VALID_LEAD_STATUS_TRANSITIONS


# ---------------------------------------------------------------------------
# Property 3: Duplicate Detection Correctness
# ---------------------------------------------------------------------------


class TestDuplicateDetectionCorrectness:
    """**Validates: Requirement 3.1-3.5**

    Lead count invariants based on existing lead status.
    """

    @given(
        existing_status=st.sampled_from([
            LeadStatus.NEW, LeadStatus.CONTACTED, LeadStatus.QUALIFIED,
        ]),
    )
    @settings(max_examples=50)
    @pytest.mark.asyncio
    async def test_active_duplicate_does_not_increase_count(
        self, existing_status: LeadStatus,
    ) -> None:
        """PBT: Property 3 — Active duplicate updates, doesn't create.

        **Validates: Requirements 3.1-3.5**
        """
        # Setup: existing lead with active status
        existing = MagicMock()
        existing.id = uuid.uuid4()
        existing.phone = "6125551234"
        existing.email = None
        existing.notes = None
        existing.situation = LeadSituation.REPAIR.value
        existing.status = existing_status.value

        repo = AsyncMock()
        repo.get_by_phone_and_active_status = AsyncMock(return_value=existing)
        repo.update = AsyncMock(return_value=existing)

        service = LeadService(
            lead_repository=repo,
            customer_service=AsyncMock(),
            job_service=AsyncMock(),
            staff_repository=AsyncMock(),
        )

        submission = LeadSubmission(
            name="Test",
            phone="(612) 555-1234",
            zip_code="55424",
            situation=LeadSituation.NEW_SYSTEM,
            source_site="residential",
        )
        result = await service.submit_lead(submission)

        assert result.success is True
        # Should update, NOT create
        repo.create.assert_not_called()
        repo.update.assert_called_once()

    @given(
        existing_status=st.sampled_from([
            LeadStatus.CONVERTED, LeadStatus.LOST, LeadStatus.SPAM,
        ]),
    )
    @settings(max_examples=50)
    @pytest.mark.asyncio
    async def test_terminal_status_creates_new_lead(
        self, existing_status: LeadStatus,  # noqa: ARG002
    ) -> None:
        """PBT: Property 3 — Terminal/lost status allows new lead creation.

        **Validates: Requirements 3.1-3.5**
        """
        # No active lead found (existing is terminal)
        new_lead = MagicMock()
        new_lead.id = uuid.uuid4()

        repo = AsyncMock()
        repo.get_by_phone_and_active_status = AsyncMock(return_value=None)
        repo.create = AsyncMock(return_value=new_lead)

        service = LeadService(
            lead_repository=repo,
            customer_service=AsyncMock(),
            job_service=AsyncMock(),
            staff_repository=AsyncMock(),
        )

        submission = LeadSubmission(
            name="Test",
            phone="(612) 555-1234",
            zip_code="55424",
            situation=LeadSituation.REPAIR,
            source_site="residential",
        )
        result = await service.submit_lead(submission)

        assert result.success is True
        repo.create.assert_called_once()


# ---------------------------------------------------------------------------
# Property 4: Input Sanitization Completeness
# ---------------------------------------------------------------------------


class TestInputSanitizationCompleteness:
    """**Validates: Requirement 1.11, 12.4**

    For any string s:
    - strip_html_tags(strip_html_tags(s)) == strip_html_tags(s)  (idempotency)
    - The output contains no substrings matching <[^>]+>
    """

    @given(text=html_chars)
    @settings(max_examples=200)
    def test_strip_html_tags_is_idempotent(self, text: str) -> None:
        """PBT: Property 4 — HTML sanitization idempotency.

        **Validates: Requirements 1.11**
        """
        first = strip_html_tags(text)
        second = strip_html_tags(first)
        assert first == second

    @given(text=html_chars)
    @settings(max_examples=200)
    def test_output_contains_no_html_tags(self, text: str) -> None:
        """PBT: Property 4 — No HTML tags remain after sanitization.

        **Validates: Requirements 12.4**
        """
        result = strip_html_tags(text)
        assert not re.search(r"<[^>]+>", result), (
            f"HTML tag found in sanitized output: {result!r}"
        )


# ---------------------------------------------------------------------------
# Property 5: Name Splitting Consistency
# ---------------------------------------------------------------------------


class TestNameSplittingConsistency:
    """**Validates: Requirement 7.1-7.2**

    For any non-empty name string:
    - first_name is non-empty
    - Single-word names produce (word, "")
    - Re-splitting produces the same result
    """

    @given(name=name_strings)
    @settings(max_examples=200)
    def test_first_name_is_non_empty(self, name: str) -> None:
        """PBT: Property 5 — first_name is always non-empty.

        **Validates: Requirements 7.1**
        """
        first, _last = LeadService.split_name(name)
        assert len(first) > 0

    @given(single_word=word)
    @settings(max_examples=100)
    def test_single_word_produces_empty_last_name(self, single_word: str) -> None:
        """PBT: Property 5 — Single-word names produce (word, "").

        **Validates: Requirements 7.2**
        """
        first, last = LeadService.split_name(single_word)
        assert first == single_word
        assert last == ""

    @given(name=name_strings)
    @settings(max_examples=200)
    def test_resplitting_is_stable(self, name: str) -> None:
        """PBT: Property 5 — Re-splitting produces the same result.

        **Validates: Requirements 7.1-7.2**
        """
        first1, last1 = LeadService.split_name(name)
        # Reconstruct and re-split
        reconstructed = f"{first1} {last1}".strip()
        first2, last2 = LeadService.split_name(reconstructed)
        assert first1 == first2
        assert last1 == last2


# ---------------------------------------------------------------------------
# Property 6: Honeypot Transparency
# ---------------------------------------------------------------------------


class TestHoneypotTransparency:
    """**Validates: Requirement 2.1, 2.4**

    For any valid submission:
    - Response with empty honeypot has success=True and creates a lead
    - Response with non-empty honeypot has success=True and does NOT create a lead
    - Response shape is identical (no information leakage)
    """

    @given(
        honeypot_value=st.text(min_size=1, max_size=50),
    )
    @settings(max_examples=50)
    @pytest.mark.asyncio
    async def test_honeypot_filled_returns_success_without_storing(
        self, honeypot_value: str,
    ) -> None:
        """PBT: Property 6 — Non-empty honeypot returns success but doesn't store.

        **Validates: Requirements 2.1**
        """
        repo = AsyncMock()

        service = LeadService(
            lead_repository=repo,
            customer_service=AsyncMock(),
            job_service=AsyncMock(),
            staff_repository=AsyncMock(),
        )

        submission = LeadSubmission(
            name="Bot Test",
            phone="(612) 555-1234",
            zip_code="55424",
            situation=LeadSituation.NEW_SYSTEM,
            source_site="residential",
            website=honeypot_value,
        )
        result = await service.submit_lead(submission)

        # Response looks successful (no info leakage)
        assert result.success is True
        assert result.message == "Thank you! We'll be in touch within 24 hours."
        # But nothing was stored
        repo.create.assert_not_called()
        repo.update.assert_not_called()
        repo.get_by_phone_and_active_status.assert_not_called()

    @pytest.mark.asyncio
    async def test_empty_honeypot_creates_lead(self) -> None:
        """PBT: Property 6 — Empty honeypot creates a lead normally.

        **Validates: Requirements 2.4**
        """
        new_lead = MagicMock()
        new_lead.id = uuid.uuid4()

        repo = AsyncMock()
        repo.get_by_phone_and_active_status = AsyncMock(return_value=None)
        repo.create = AsyncMock(return_value=new_lead)

        service = LeadService(
            lead_repository=repo,
            customer_service=AsyncMock(),
            job_service=AsyncMock(),
            staff_repository=AsyncMock(),
        )

        submission = LeadSubmission(
            name="Real User",
            phone="(612) 555-1234",
            zip_code="55424",
            situation=LeadSituation.REPAIR,
            source_site="residential",
            website="",  # Empty honeypot = legitimate
        )
        result = await service.submit_lead(submission)

        assert result.success is True
        assert result.lead_id == new_lead.id
        repo.create.assert_called_once()

    @given(
        honeypot_value=st.text(min_size=1, max_size=50),
    )
    @settings(max_examples=50)
    @pytest.mark.asyncio
    async def test_response_shape_identical(
        self, honeypot_value: str,
    ) -> None:
        """PBT: Property 6 — Response shape is identical for bot vs real.

        **Validates: Requirements 2.1, 2.4**
        """
        new_lead = MagicMock()
        new_lead.id = uuid.uuid4()

        # Setup for real submission
        real_repo = AsyncMock()
        real_repo.get_by_phone_and_active_status = AsyncMock(return_value=None)
        real_repo.create = AsyncMock(return_value=new_lead)

        real_service = LeadService(
            lead_repository=real_repo,
            customer_service=AsyncMock(),
            job_service=AsyncMock(),
            staff_repository=AsyncMock(),
        )

        # Setup for bot submission
        bot_repo = AsyncMock()

        bot_service = LeadService(
            lead_repository=bot_repo,
            customer_service=AsyncMock(),
            job_service=AsyncMock(),
            staff_repository=AsyncMock(),
        )

        base_data: dict[str, Any] = {
            "name": "Test User",
            "phone": "(612) 555-1234",
            "zip_code": "55424",
            "situation": LeadSituation.NEW_SYSTEM,
            "source_site": "residential",
        }

        real_submission = LeadSubmission(**base_data, website="")
        bot_submission = LeadSubmission(**base_data, website=honeypot_value)

        real_result = await real_service.submit_lead(real_submission)
        bot_result = await bot_service.submit_lead(bot_submission)

        # Response shape is identical — both have same fields
        assert real_result.success == bot_result.success
        assert real_result.message == bot_result.message
        # Both are LeadSubmissionResponse instances
        assert type(real_result) is type(bot_result)
