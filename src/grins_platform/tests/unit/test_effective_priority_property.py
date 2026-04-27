"""Property-based tests for the picker's ``effective_priority_level``.

The picker derives a display priority by combining three signals:
``Job.priority_level`` (0-2), the ``priority`` ``CustomerTag``, and the
existence of an active ``ServiceAgreement``. The derivation must be
*monotone* in each input — a customer can only see priority climb (or
stay equal) as additional signals appear, never drop. These tests pin
that invariant against arbitrary signal combinations.
"""

from __future__ import annotations

import pytest
from hypothesis import (
    given,
    strategies as st,
)

from grins_platform.api.v1.schedule import _compute_effective_priority


@pytest.mark.unit
@given(
    base=st.integers(min_value=0, max_value=2),
    has_priority_tag=st.booleans(),
    has_active_agreement=st.booleans(),
)
def test_effective_is_at_least_base(
    base: int,
    has_priority_tag: bool,
    has_active_agreement: bool,
) -> None:
    """Effective priority never drops below the underlying job priority."""
    result = _compute_effective_priority(
        base,
        has_priority_tag=has_priority_tag,
        has_active_agreement=has_active_agreement,
    )
    assert result >= base


@pytest.mark.unit
@given(
    base=st.integers(min_value=0, max_value=2),
    has_priority_tag=st.booleans(),
    has_active_agreement=st.booleans(),
)
def test_effective_is_at_least_one_when_any_signal_present(
    base: int,
    has_priority_tag: bool,
    has_active_agreement: bool,
) -> None:
    """Tag or agreement alone escalates priority to at least 1."""
    result = _compute_effective_priority(
        base,
        has_priority_tag=has_priority_tag,
        has_active_agreement=has_active_agreement,
    )
    if has_priority_tag or has_active_agreement:
        assert result >= 1


@pytest.mark.unit
@given(base=st.integers(min_value=0, max_value=2))
def test_effective_equals_base_when_no_signals(base: int) -> None:
    """No tag and no agreement → effective tracks base exactly."""
    result = _compute_effective_priority(
        base,
        has_priority_tag=False,
        has_active_agreement=False,
    )
    assert result == base


@pytest.mark.unit
@given(
    base=st.integers(min_value=0, max_value=2),
    has_priority_tag=st.booleans(),
    has_active_agreement=st.booleans(),
)
def test_effective_is_monotone_in_priority_tag(
    base: int,
    has_priority_tag: bool,
    has_active_agreement: bool,
) -> None:
    """Adding the priority tag can only raise (never lower) the result."""
    without = _compute_effective_priority(
        base,
        has_priority_tag=False,
        has_active_agreement=has_active_agreement,
    )
    with_tag = _compute_effective_priority(
        base,
        has_priority_tag=True,
        has_active_agreement=has_active_agreement,
    )
    _ = has_priority_tag  # parameter unused but kept for symmetry
    assert with_tag >= without


@pytest.mark.unit
@given(
    base=st.integers(min_value=0, max_value=2),
    has_priority_tag=st.booleans(),
    has_active_agreement=st.booleans(),
)
def test_effective_is_monotone_in_active_agreement(
    base: int,
    has_priority_tag: bool,
    has_active_agreement: bool,
) -> None:
    """Adding an active agreement can only raise (never lower) the result."""
    without = _compute_effective_priority(
        base,
        has_priority_tag=has_priority_tag,
        has_active_agreement=False,
    )
    with_agreement = _compute_effective_priority(
        base,
        has_priority_tag=has_priority_tag,
        has_active_agreement=True,
    )
    _ = has_active_agreement
    assert with_agreement >= without


@pytest.mark.unit
def test_effective_caps_at_base_when_base_is_urgent() -> None:
    """Job already at level 2 stays at 2 even with all signals present."""
    assert (
        _compute_effective_priority(
            2,
            has_priority_tag=True,
            has_active_agreement=True,
        )
        == 2
    )
