"""Unit tests for the tightened ``_parse_address`` city guard.

The Pick-Jobs page City facet rail surfaced raw street addresses from
``properties.city`` because lead intake was permissive about what it
accepted as a city. ``_parse_address`` now rejects digit-prefixed tokens
and tokens that end in a recognised street suffix, falling back to the
``_UNKNOWN_CITY`` sentinel so dirty rows are visible (and recoverable)
without polluting the facet rail.
"""

from __future__ import annotations

import pytest

from grins_platform.services.property_service import _UNKNOWN_CITY, _parse_address


@pytest.mark.unit
def test_parse_address_with_well_formed_input_returns_real_city() -> None:
    _street, city, _state, _zip = _parse_address(
        "1234 Main St, Eden Prairie, MN 55344",
    )
    assert city == "Eden Prairie"


@pytest.mark.unit
def test_parse_address_with_st_paul_preserves_proper_noun() -> None:
    """``St. Paul`` ends in a period — the trailing-suffix regex anchors
    on end-of-string with optional whitespace, so the period prevents a
    false match."""
    _street, city, _state, _zip = _parse_address(
        "1234 Main St, St. Paul, MN 55101",
    )
    assert city == "St. Paul"


@pytest.mark.unit
def test_parse_address_with_no_commas_falls_back_to_unknown() -> None:
    """Single-segment street-shaped input has no comma-delimited city
    slot and is quarantined to the sentinel."""
    _street, city, _state, _zip = _parse_address("5808 View Ln Edina 55436")
    assert city == _UNKNOWN_CITY


@pytest.mark.unit
def test_parse_address_with_state_zip_in_city_slot_falls_back() -> None:
    """``Andover, MN 55304`` has only two comma segments; the second is
    state+ZIP, not a city, and the existing rule converts it to Unknown."""
    _street, city, _state, _zip = _parse_address("Andover, MN 55304")
    assert city == _UNKNOWN_CITY


@pytest.mark.unit
def test_parse_address_with_digit_prefixed_city_falls_back() -> None:
    """Address-shaped string masquerading as a city is quarantined."""
    _street, city, _state, _zip = _parse_address("123 Plymouth Way")
    assert city == _UNKNOWN_CITY


@pytest.mark.unit
def test_parse_address_with_street_suffix_in_city_falls_back() -> None:
    """Two-segment input where the second segment is itself a street name
    (e.g. ``Plymouth Way``) is rejected as an address-shaped token."""
    _street, city, _state, _zip = _parse_address("99 Foo, Plymouth Way")
    assert city == _UNKNOWN_CITY


@pytest.mark.unit
def test_parse_address_with_empty_input_returns_unknown_city() -> None:
    _street, city, _state, _zip = _parse_address("")
    assert city == _UNKNOWN_CITY
