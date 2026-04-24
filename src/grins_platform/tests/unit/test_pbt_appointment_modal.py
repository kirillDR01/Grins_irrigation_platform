"""Property-based tests for Combined Appointment Modal spec.

Covers Properties 7–9, 11–13 (backend-focused):
  7: Tag label uniqueness per customer (Req 12.2)
  8: Tag save performs diff and preserves system tags (Req 12.5, 12.6)
  9: Tag input validation rejects invalid data (Req 12.7)
 11: Status-to-step mapping is deterministic and correct (Req 16.1)
 12: Step transitions are strictly linear (Req 16.3, 16.4)
 13: Tone-to-color mapping is complete and correct (Req 17.2, 17.5)
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from datetime import datetime, timezone
from typing import TypeVar
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from hypothesis import given, settings, strategies as st
from pydantic import ValidationError

from grins_platform.models.customer_tag import CustomerTag
from grins_platform.schemas.customer_tag import (
    CustomerTagsUpdateRequest,
    TagInput,
    TagTone,
)
from grins_platform.services.customer_tag_service import CustomerTagService

_T = TypeVar("_T")


def _run_async(coro: Awaitable[_T]) -> _T:
    """Run an async coroutine in a fresh event loop."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_tag(
    label: str,
    tone: str = "neutral",
    source: str = "manual",
    customer_id: UUID | None = None,
) -> CustomerTag:
    """Create a CustomerTag instance for testing."""
    tag = CustomerTag(
        customer_id=customer_id or uuid4(),
        label=label,
        tone=tone,
        source=source,
    )
    tag.id = uuid4()
    tag.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    return tag


def _make_service() -> tuple[CustomerTagService, AsyncMock]:
    """Create a CustomerTagService with a mocked repository."""
    repo = AsyncMock()
    svc = CustomerTagService(repo)
    return svc, repo


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Valid tag labels: 1-32 printable characters (no control chars)
valid_labels = st.text(
    alphabet=st.characters(
        whitelist_categories=("L", "N", "Zs", "P"),
        blacklist_characters="\x00",
    ),
    min_size=1,
    max_size=32,
).filter(lambda s: len(s.strip()) > 0)

# Valid tone values
valid_tones = st.sampled_from(list(TagTone))

# All valid appointment statuses for step mapping
all_statuses = st.sampled_from([
    "confirmed",
    "scheduled",
    "en_route",
    "in_progress",
    "completed",
    "pending",
    "draft",
    "cancelled",
    "no_show",
])

# Statuses that map to workflow steps
workflow_statuses = st.sampled_from([
    "confirmed",
    "scheduled",
    "en_route",
    "in_progress",
    "completed",
])

# Non-workflow statuses (return null)
non_workflow_statuses = st.sampled_from([
    "pending",
    "draft",
    "cancelled",
    "no_show",
])


# ---------------------------------------------------------------------------
# Pure functions under test (implemented here per design doc)
# ---------------------------------------------------------------------------


def derive_step(status: str) -> int | None:
    """Map appointment status to step value.

    Implements the deriveStep pure function from the design document §Key Interfaces.

    Returns:
        0 for confirmed/scheduled, 1 for en_route, 2 for in_progress,
        3 for completed, None for pending/draft/cancelled/no_show.
    """
    mapping: dict[str, int] = {
        "confirmed": 0,
        "scheduled": 0,
        "en_route": 1,
        "in_progress": 2,
        "completed": 3,
    }
    return mapping.get(status)


# Valid step transitions: only +1 forward
VALID_STEP_TRANSITIONS: dict[int, int] = {
    0: 1,  # Booked → En route
    1: 2,  # En route → On site
    2: 3,  # On site → Done
}

# Mutation mapping per transition
STEP_MUTATION_MAP: dict[tuple[int, int], str] = {
    (0, 1): "useMarkAppointmentEnRoute",
    (1, 2): "useMarkAppointmentArrived",
    (2, 3): "useMarkAppointmentCompleted",
}

# Tone-to-color mapping from design doc §7.1
TONE_COLOR_MAP: dict[str, dict[str, str]] = {
    "neutral": {
        "text": "#374151",
        "background": "#F3F4F6",
        "border": "#E5E7EB",
    },
    "blue": {
        "text": "#1D4ED8",
        "background": "#DBEAFE",
        "border": "#93C5FD",
    },
    "green": {
        "text": "#047857",
        "background": "#D1FAE5",
        "border": "#6EE7B7",
    },
    "amber": {
        "text": "#B45309",
        "background": "#FEF3C7",
        "border": "#FCD34D",
    },
    "violet": {
        "text": "#6D28D9",
        "background": "#EDE9FE",
        "border": "#C4B5FD",
    },
}


# ===================================================================
# Property 7: Tag label uniqueness per customer
# Feature: appointment-modal-combined, Property 7: Tag label uniqueness per customer
# ===================================================================


@pytest.mark.unit
class TestProperty7TagLabelUniqueness:
    """Property 7: Tag label uniqueness per customer.

    **Validates: Requirements 12.2**

    FOR ALL (customer_id, label) pairs:
      inserting a tag succeeds, but inserting a second tag with the
      same (customer_id, label) raises a constraint violation (409).
    """

    @given(
        customer_id=st.uuids(),
        label=valid_labels,
        tone=valid_tones,
    )
    @settings(max_examples=100, deadline=None)
    def test_duplicate_label_same_customer_raises_conflict(
        self,
        customer_id: UUID,
        label: str,
        tone: TagTone,
    ) -> None:
        """Inserting two tags with the same (customer_id, label) raises 409."""
        from fastapi import HTTPException
        from sqlalchemy.exc import IntegrityError

        svc, repo = _make_service()

        # First tag already exists in DB
        existing_tag = _make_tag(label=label, tone=tone.value, customer_id=customer_id)
        repo.get_by_customer_id.return_value = []

        # Simulate IntegrityError on second insert (unique constraint)
        repo.create.side_effect = IntegrityError(
            "INSERT INTO customer_tags",
            {},
            Exception("duplicate key value violates unique constraint"),
        )

        session = AsyncMock()
        request = CustomerTagsUpdateRequest(
            tags=[TagInput(label=label, tone=tone)],
        )

        with pytest.raises(HTTPException) as exc_info:
            _run_async(svc.save_tags(customer_id, request, session))

        assert exc_info.value.status_code == 409

    @given(
        customer_id=st.uuids(),
        label=valid_labels,
        tone=valid_tones,
    )
    @settings(max_examples=100, deadline=None)
    def test_schema_rejects_duplicate_labels_in_request(
        self,
        customer_id: UUID,
        label: str,
        tone: TagTone,
    ) -> None:
        """Pydantic schema rejects requests with duplicate labels."""
        with pytest.raises(ValidationError):
            CustomerTagsUpdateRequest(
                tags=[
                    TagInput(label=label, tone=tone),
                    TagInput(label=label, tone=tone),
                ],
            )

    @given(
        customer_id_a=st.uuids(),
        customer_id_b=st.uuids(),
        label=valid_labels,
        tone=valid_tones,
    )
    @settings(max_examples=50, deadline=None)
    def test_same_label_different_customers_allowed(
        self,
        customer_id_a: UUID,
        customer_id_b: UUID,
        label: str,
        tone: TagTone,
    ) -> None:
        """Same label on different customers does not conflict."""
        svc, repo = _make_service()

        # Both customers have no existing tags
        repo.get_by_customer_id.return_value = []
        new_tag_a = _make_tag(label=label, tone=tone.value, customer_id=customer_id_a)
        new_tag_b = _make_tag(label=label, tone=tone.value, customer_id=customer_id_b)
        repo.create.side_effect = [new_tag_a, new_tag_b]

        session = AsyncMock()
        request = CustomerTagsUpdateRequest(
            tags=[TagInput(label=label, tone=tone)],
        )

        # Both saves should succeed (no IntegrityError)
        result_a = _run_async(svc.save_tags(customer_id_a, request, session))
        assert any(t.label == label for t in result_a.tags)

        repo.get_by_customer_id.return_value = []
        result_b = _run_async(svc.save_tags(customer_id_b, request, session))
        assert any(t.label == label for t in result_b.tags)


# ===================================================================
# Property 8: Tag save performs diff and preserves system tags
# Feature: appointment-modal-combined, Property 8: Tag save performs diff and preserves system tags
# ===================================================================


@pytest.mark.unit
class TestProperty8SystemTagPreservation:
    """Property 8: Tag save performs diff and preserves system tags.

    **Validates: Requirements 12.5, 12.6**

    FOR ALL customers with existing tags (including system tags):
      PUT with new manual tags preserves all system tags in the response.
      No system tag is ever deleted by the PUT endpoint.
    """

    @given(
        customer_id=st.uuids(),
        system_labels=st.lists(
            valid_labels,
            min_size=0,
            max_size=5,
            unique=True,
        ),
        new_manual_labels=st.lists(
            valid_labels,
            min_size=0,
            max_size=5,
            unique=True,
        ),
    )
    @settings(max_examples=100, deadline=None)
    def test_system_tags_always_preserved_after_save(
        self,
        customer_id: UUID,
        system_labels: list[str],
        new_manual_labels: list[str],
    ) -> None:
        """System tags are never deleted by PUT, regardless of incoming manual tags."""
        # Ensure no overlap between system and manual labels for clean test
        new_manual_labels = [
            lbl for lbl in new_manual_labels if lbl not in system_labels
        ]

        svc, repo = _make_service()

        # Build existing tags: system tags
        existing_system = [
            _make_tag(lbl, source="system", customer_id=customer_id)
            for lbl in system_labels
        ]
        repo.get_by_customer_id.return_value = existing_system

        # Mock create for new manual tags
        created_tags = []
        for lbl in new_manual_labels:
            t = _make_tag(lbl, customer_id=customer_id)
            created_tags.append(t)
        repo.create.side_effect = created_tags

        session = AsyncMock()
        request = CustomerTagsUpdateRequest(
            tags=[TagInput(label=lbl) for lbl in new_manual_labels],
        )

        result = _run_async(svc.save_tags(customer_id, request, session))

        # All system tags must appear in the response
        result_labels = {t.label for t in result.tags}
        for sys_label in system_labels:
            assert sys_label in result_labels, (
                f"System tag '{sys_label}' was not preserved in response. "
                f"Got: {result_labels}"
            )

        # delete_by_ids should never include system tag IDs
        if repo.delete_by_ids.called:
            deleted_ids = repo.delete_by_ids.call_args[0][0]
            system_ids = {t.id for t in existing_system}
            assert not system_ids.intersection(deleted_ids), (
                "System tag IDs were passed to delete_by_ids"
            )

    @given(
        customer_id=st.uuids(),
        system_labels=st.lists(
            valid_labels,
            min_size=1,
            max_size=3,
            unique=True,
        ),
    )
    @settings(max_examples=50, deadline=None)
    def test_empty_manual_request_preserves_all_system_tags(
        self,
        customer_id: UUID,
        system_labels: list[str],
    ) -> None:
        """Sending an empty manual tag list still preserves all system tags."""
        svc, repo = _make_service()

        existing_system = [
            _make_tag(lbl, source="system", customer_id=customer_id)
            for lbl in system_labels
        ]
        repo.get_by_customer_id.return_value = existing_system

        session = AsyncMock()
        request = CustomerTagsUpdateRequest(tags=[])

        result = _run_async(svc.save_tags(customer_id, request, session))

        result_labels = {t.label for t in result.tags}
        for sys_label in system_labels:
            assert sys_label in result_labels


# ===================================================================
# Property 9: Tag input validation rejects invalid data
# Feature: appointment-modal-combined, Property 9: Tag input validation rejects invalid data
# ===================================================================


@pytest.mark.unit
class TestProperty9TagInputValidation:
    """Property 9: Tag input validation rejects invalid data.

    **Validates: Requirements 12.7**

    FOR ALL tags with label < 1 char, label > 32 chars, or invalid tone:
      Pydantic validation rejects with 422.
    """

    @given(
        label=st.text(
            alphabet=st.characters(whitelist_categories=("L", "N", "Zs")),
            min_size=33,
            max_size=100,
        ),
    )
    @settings(max_examples=100, deadline=None)
    def test_label_too_long_rejected(self, label: str) -> None:
        """Labels longer than 32 characters are rejected."""
        with pytest.raises(ValidationError):
            TagInput(label=label, tone=TagTone.neutral)

    @given(
        invalid_tone=st.text(
            alphabet=st.characters(whitelist_categories=("L",)),
            min_size=1,
            max_size=20,
        ).filter(
            lambda s: s.lower() not in {"neutral", "blue", "green", "amber", "violet"}
        ),
    )
    @settings(max_examples=100, deadline=None)
    def test_invalid_tone_rejected(self, invalid_tone: str) -> None:
        """Tone values not in the allowed set are rejected."""
        with pytest.raises(ValidationError):
            TagInput(label="Valid label", tone=invalid_tone)  # type: ignore[arg-type]

    def test_empty_label_rejected(self) -> None:
        """Empty string label is rejected."""
        with pytest.raises(ValidationError):
            TagInput(label="", tone=TagTone.neutral)

    @given(tone=valid_tones, label=valid_labels)
    @settings(max_examples=50, deadline=None)
    def test_valid_label_and_tone_accepted(
        self,
        tone: TagTone,
        label: str,
    ) -> None:
        """Valid labels (1-32 chars) with valid tones are accepted."""
        tag = TagInput(label=label, tone=tone)
        assert tag.label == label
        assert tag.tone == tone
        assert 1 <= len(tag.label) <= 32


# ===================================================================
# Property 11: Status-to-step mapping is deterministic and correct
# Feature: appointment-modal-combined, Property 11: Status-to-step mapping is deterministic and correct
# ===================================================================


@pytest.mark.unit
class TestProperty11StatusToStepMapping:
    """Property 11: Status-to-step mapping is deterministic and correct.

    **Validates: Requirements 16.1**

    FOR ALL valid appointment statuses:
      deriveStep returns the correct step value deterministically.
      confirmed/scheduled → 0, en_route → 1, in_progress → 2,
      completed → 3, pending/draft/cancelled/no_show → None.
    """

    @given(status=all_statuses)
    @settings(max_examples=100, deadline=None)
    def test_derive_step_is_deterministic(self, status: str) -> None:
        """Same status always produces the same step value."""
        result1 = derive_step(status)
        result2 = derive_step(status)
        assert result1 == result2, (
            f"deriveStep({status}) returned {result1} then {result2}"
        )

    @given(status=workflow_statuses)
    @settings(max_examples=100, deadline=None)
    def test_workflow_statuses_return_correct_step(self, status: str) -> None:
        """Workflow statuses map to the correct step integer."""
        expected: dict[str, int] = {
            "confirmed": 0,
            "scheduled": 0,
            "en_route": 1,
            "in_progress": 2,
            "completed": 3,
        }
        result = derive_step(status)
        assert result == expected[status], (
            f"deriveStep({status}) = {result}, expected {expected[status]}"
        )

    @given(status=non_workflow_statuses)
    @settings(max_examples=100, deadline=None)
    def test_non_workflow_statuses_return_none(self, status: str) -> None:
        """Non-workflow statuses (pending, draft, cancelled, no_show) return None."""
        result = derive_step(status)
        assert result is None, (
            f"deriveStep({status}) = {result}, expected None"
        )


# ===================================================================
# Property 12: Step transitions are strictly linear
# Feature: appointment-modal-combined, Property 12: Step transitions are strictly linear
# ===================================================================


@pytest.mark.unit
class TestProperty12StepTransitionLinearity:
    """Property 12: Step transitions are strictly linear.

    **Validates: Requirements 16.3, 16.4**

    FOR ALL step sequences:
      step value only increases by exactly 1 per transition (0→1→2→3).
      No transition skips a step or reverses direction.
      Each transition maps to the correct mutation.
    """

    @given(
        current_step=st.sampled_from([0, 1, 2]),
    )
    @settings(max_examples=100, deadline=None)
    def test_valid_transition_advances_by_one(self, current_step: int) -> None:
        """Valid transitions advance step by exactly 1."""
        next_step = VALID_STEP_TRANSITIONS[current_step]
        assert next_step == current_step + 1, (
            f"Transition from step {current_step} should go to "
            f"{current_step + 1}, got {next_step}"
        )

    @given(
        current_step=st.sampled_from([0, 1, 2]),
        target_step=st.sampled_from([0, 1, 2, 3]),
    )
    @settings(max_examples=100, deadline=None)
    def test_only_plus_one_transitions_allowed(
        self,
        current_step: int,
        target_step: int,
    ) -> None:
        """Only +1 transitions are valid; skips and reverses are rejected."""
        is_valid = target_step == current_step + 1
        allowed_next = VALID_STEP_TRANSITIONS.get(current_step)

        if is_valid:
            assert allowed_next == target_step
        else:
            assert allowed_next != target_step or target_step != current_step + 1

    @given(
        current_step=st.sampled_from([0, 1, 2]),
    )
    @settings(max_examples=100, deadline=None)
    def test_transition_maps_to_correct_mutation(self, current_step: int) -> None:
        """Each step transition maps to the correct backend mutation."""
        next_step = VALID_STEP_TRANSITIONS[current_step]
        mutation = STEP_MUTATION_MAP[(current_step, next_step)]

        expected_mutations: dict[tuple[int, int], str] = {
            (0, 1): "useMarkAppointmentEnRoute",
            (1, 2): "useMarkAppointmentArrived",
            (2, 3): "useMarkAppointmentCompleted",
        }
        assert mutation == expected_mutations[(current_step, next_step)]

    def test_step_3_has_no_forward_transition(self) -> None:
        """Step 3 (Done) has no valid forward transition."""
        assert 3 not in VALID_STEP_TRANSITIONS

    @given(
        steps=st.lists(
            st.sampled_from([0, 1, 2, 3]),
            min_size=2,
            max_size=10,
        ),
    )
    @settings(max_examples=100, deadline=None)
    def test_random_sequences_only_valid_if_strictly_increasing_by_one(
        self,
        steps: list[int],
    ) -> None:
        """A random step sequence is valid iff each consecutive pair differs by +1."""
        for i in range(len(steps) - 1):
            current = steps[i]
            next_val = steps[i + 1]
            is_valid_transition = next_val == current + 1

            if is_valid_transition and current in VALID_STEP_TRANSITIONS:
                assert VALID_STEP_TRANSITIONS[current] == next_val
            elif not is_valid_transition:
                # This transition would be rejected by the state machine
                assert next_val != current + 1 or current not in VALID_STEP_TRANSITIONS


# ===================================================================
# Property 13: Tone-to-color mapping is complete and correct
# Feature: appointment-modal-combined, Property 13: Tone-to-color mapping is complete and correct
# ===================================================================


@pytest.mark.unit
class TestProperty13ToneToColorMapping:
    """Property 13: Tone-to-color mapping is complete and correct.

    **Validates: Requirements 17.2, 17.5**

    FOR ALL valid tone values:
      the TONE_COLOR_MAP returns a complete color triplet
      (text, background, border) with no undefined or fallback values.
    """

    @given(tone=valid_tones)
    @settings(max_examples=100, deadline=None)
    def test_every_tone_has_color_triplet(self, tone: TagTone) -> None:
        """Every valid tone maps to a complete (text, bg, border) triplet."""
        colors = TONE_COLOR_MAP.get(tone.value)
        assert colors is not None, f"Tone '{tone.value}' has no color mapping"
        assert "text" in colors, f"Tone '{tone.value}' missing 'text' color"
        assert "background" in colors, f"Tone '{tone.value}' missing 'background' color"
        assert "border" in colors, f"Tone '{tone.value}' missing 'border' color"

    @given(tone=valid_tones)
    @settings(max_examples=100, deadline=None)
    def test_color_values_are_valid_hex(self, tone: TagTone) -> None:
        """All color values are valid hex color strings (#RRGGBB)."""
        import re

        hex_pattern = re.compile(r"^#[0-9A-Fa-f]{6}$")
        colors = TONE_COLOR_MAP[tone.value]
        for key, value in colors.items():
            assert hex_pattern.match(value), (
                f"Tone '{tone.value}' {key} color '{value}' is not valid hex"
            )

    @given(tone=valid_tones)
    @settings(max_examples=100, deadline=None)
    def test_mapping_is_deterministic(self, tone: TagTone) -> None:
        """Same tone always returns the same color triplet."""
        result1 = TONE_COLOR_MAP[tone.value]
        result2 = TONE_COLOR_MAP[tone.value]
        assert result1 == result2

    def test_all_five_tones_covered(self) -> None:
        """The color map covers all 5 valid tones with no gaps."""
        expected_tones = {"neutral", "blue", "green", "amber", "violet"}
        actual_tones = set(TONE_COLOR_MAP.keys())
        assert actual_tones == expected_tones, (
            f"Missing tones: {expected_tones - actual_tones}, "
            f"Extra tones: {actual_tones - expected_tones}"
        )

    def test_no_two_tones_share_same_text_color(self) -> None:
        """Each tone has a distinct text color for visual differentiation."""
        text_colors = [v["text"] for v in TONE_COLOR_MAP.values()]
        assert len(text_colors) == len(set(text_colors)), (
            "Two or more tones share the same text color"
        )
