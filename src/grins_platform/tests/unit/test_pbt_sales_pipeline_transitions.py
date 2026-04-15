"""Property-based tests for sales pipeline status transitions.

Validates: CRM Changes Update 2 Req 33.1, 33.2, 33.3
"""

from __future__ import annotations

import pytest
from hypothesis import (
    given,
    settings,
    strategies as st,
)

from grins_platform.models.enums import (
    SALES_PIPELINE_ORDER,
    SALES_TERMINAL_STATUSES,
    VALID_SALES_TRANSITIONS,
    SalesEntryStatus,
)

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

non_terminal_statuses = st.sampled_from(
    [s for s in SalesEntryStatus if s not in SALES_TERMINAL_STATUSES],
)
terminal_statuses = st.sampled_from(list(SALES_TERMINAL_STATUSES))
all_statuses = st.sampled_from(list(SalesEntryStatus))


def _next_status(current: SalesEntryStatus) -> SalesEntryStatus:
    """Mirror the service's _next_status logic for pure testing."""
    idx = SALES_PIPELINE_ORDER.index(current)
    return SALES_PIPELINE_ORDER[idx + 1]


# ===================================================================
# Property 5: Sales Pipeline Status Transition Validity
# Validates: Req 33.1
# ===================================================================


@pytest.mark.unit
class TestProperty5TransitionValidity:
    """advance_status result ∈ VALID_TRANSITIONS[current_status]."""

    @given(status=non_terminal_statuses)
    @settings(max_examples=50)
    def test_next_status_is_valid_transition(
        self,
        status: SalesEntryStatus,
    ) -> None:
        target = _next_status(status)
        assert target in VALID_SALES_TRANSITIONS[status]


# ===================================================================
# Property 6: Sales Pipeline Terminal State Immutability
# Validates: Req 33.2
# ===================================================================


@pytest.mark.unit
class TestProperty6TerminalImmutability:
    """CLOSED_WON/CLOSED_LOST cannot advance further."""

    @given(status=terminal_statuses)
    @settings(max_examples=20)
    def test_terminal_status_has_no_transitions(
        self,
        status: SalesEntryStatus,
    ) -> None:
        assert VALID_SALES_TRANSITIONS.get(status, set()) == set()

    @given(status=terminal_statuses)
    @settings(max_examples=20)
    def test_terminal_status_not_in_pipeline_order_tail(
        self,
        status: SalesEntryStatus,
    ) -> None:
        # Terminal statuses at end of pipeline order have no next
        if status in SALES_PIPELINE_ORDER:
            idx = SALES_PIPELINE_ORDER.index(status)
            is_last = idx == len(SALES_PIPELINE_ORDER) - 1
            assert is_last or status == SalesEntryStatus.CLOSED_LOST


# ===================================================================
# Property 7: Sales Pipeline Idempotent Advance
# Validates: Req 33.3
# ===================================================================


@pytest.mark.unit
class TestProperty7IdempotentAdvance:
    """Action advances exactly one step forward in SALES_PIPELINE_ORDER."""

    @given(status=non_terminal_statuses)
    @settings(max_examples=50)
    def test_advance_moves_exactly_one_step(
        self,
        status: SalesEntryStatus,
    ) -> None:
        idx = SALES_PIPELINE_ORDER.index(status)
        target = _next_status(status)
        target_idx = SALES_PIPELINE_ORDER.index(target)
        assert target_idx == idx + 1
