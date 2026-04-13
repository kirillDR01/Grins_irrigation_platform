"""Property-based tests for invoice filter composition.

Validates: Requirements 37.1, 37.2, 37.3

Property 14: Invoice Filter Composition — combining filters A and B produces
    a superset of filter clauses vs either alone (AND composition).
Property 15: Invoice Filter URL Round-Trip — deserialize(serialize(state)) == state.
Property 16: Invoice Filter Clear-All Identity — default params produce zero filters.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from hypothesis import (
    given,
    settings,
    strategies as st,
)

from grins_platform.models.enums import InvoiceStatus
from grins_platform.repositories.invoice_repository import InvoiceRepository
from grins_platform.schemas.invoice import InvoiceListParams

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

_statuses = st.sampled_from(list(InvoiceStatus))
_uuids = st.builds(uuid4)
_dates = st.dates(min_value=date(2020, 1, 1), max_value=date(2030, 12, 31))
_amounts = st.decimals(min_value=Decimal(0), max_value=Decimal("99999.99"), places=2)
_date_types = st.sampled_from(["created", "due", "paid"])
_payment_types = st.sampled_from(["cash", "check", "venmo", "zelle", "stripe"])
_days = st.integers(min_value=0, max_value=365)
_invoice_numbers = st.from_regex(r"INV-[0-9]{4,8}", fullmatch=True)
_sort_orders = st.sampled_from(["asc", "desc"])


def _params_strategy() -> st.SearchStrategy[InvoiceListParams]:
    """Strategy that generates random InvoiceListParams with optional filters."""
    return st.builds(
        InvoiceListParams,
        page=st.just(1),
        page_size=st.just(20),
        status=st.one_of(st.none(), _statuses),
        customer_id=st.one_of(st.none(), _uuids),
        job_id=st.one_of(st.none(), _uuids),
        date_from=st.one_of(st.none(), _dates),
        date_to=st.one_of(st.none(), _dates),
        date_type=_date_types,
        amount_min=st.one_of(st.none(), _amounts),
        amount_max=st.one_of(st.none(), _amounts),
        payment_types=st.one_of(st.none(), _payment_types),
        days_until_due_min=st.one_of(st.none(), _days),
        days_until_due_max=st.one_of(st.none(), _days),
        days_past_due_min=st.one_of(st.none(), _days),
        days_past_due_max=st.one_of(st.none(), _days),
        invoice_number=st.one_of(st.none(), _invoice_numbers),
        lien_eligible=st.one_of(st.none(), st.booleans()),
        sort_by=st.just("created_at"),
        sort_order=_sort_orders,
    )


def _count_active_filters(params: InvoiceListParams) -> int:
    """Count how many filter axes are active (non-None/non-default)."""
    count = 0
    if params.status is not None:
        count += 1
    if params.customer_id is not None:
        count += 1
    if params.job_id is not None:
        count += 1
    if params.date_from is not None:
        count += 1
    if params.date_to is not None:
        count += 1
    if params.amount_min is not None:
        count += 1
    if params.amount_max is not None:
        count += 1
    if params.payment_types is not None:
        count += 1
    if params.days_until_due_min is not None:
        count += 1
    if params.days_until_due_max is not None:
        count += 1
    if params.days_past_due_min is not None:
        count += 1
    if params.days_past_due_max is not None:
        count += 1
    if params.invoice_number is not None:
        count += 1
    if params.lien_eligible is not None:
        count += 1
    return count


def _merge_params(
    a: InvoiceListParams,
    b: InvoiceListParams,
) -> InvoiceListParams:
    """Merge two filter sets: B's non-None values override A's."""
    data = a.model_dump()
    for key, val in b.model_dump().items():
        skip = ("page", "page_size", "sort_by", "sort_order", "date_type")
        if val is not None and key not in skip:
            data[key] = val
    return InvoiceListParams(**data)


# We need a repo instance just for _build_filters (no DB needed).
_repo = InvoiceRepository.__new__(InvoiceRepository)


# ===================================================================
# Property 14: Invoice Filter Composition
# Combining filters A and B produces at least as many SQL clauses as
# either A or B alone (AND composition — more filters = more clauses).
# Validates: Req 37.1
# ===================================================================
@pytest.mark.unit
@given(a=_params_strategy(), b=_params_strategy())
@settings(max_examples=200, deadline=None)
def test_invoice_filter_composition(
    a: InvoiceListParams,
    b: InvoiceListParams,
) -> None:
    clauses_a = _repo._build_filters(a)
    clauses_b = _repo._build_filters(b)
    merged = _merge_params(a, b)
    clauses_merged = _repo._build_filters(merged)

    # AND composition: merged filters >= max(individual filters)
    assert len(clauses_merged) >= max(len(clauses_a), len(clauses_b))


# ===================================================================
# Property 15: Invoice Filter URL Round-Trip
# deserialize(serialize(filter_state)) == filter_state
# Validates: Req 37.2
# ===================================================================
@pytest.mark.unit
@given(params=_params_strategy())
@settings(max_examples=200, deadline=None)
def test_invoice_filter_url_round_trip(params: InvoiceListParams) -> None:
    # Serialize to dict (simulates URL query params)
    serialized = params.model_dump(mode="json")
    # Deserialize back
    restored = InvoiceListParams(**serialized)

    # All filter fields must survive the round-trip
    assert restored.status == params.status
    assert restored.customer_id == params.customer_id
    assert restored.job_id == params.job_id
    assert restored.date_from == params.date_from
    assert restored.date_to == params.date_to
    assert restored.date_type == params.date_type
    assert restored.amount_min == params.amount_min
    assert restored.amount_max == params.amount_max
    assert restored.payment_types == params.payment_types
    assert restored.days_until_due_min == params.days_until_due_min
    assert restored.days_until_due_max == params.days_until_due_max
    assert restored.days_past_due_min == params.days_past_due_min
    assert restored.days_past_due_max == params.days_past_due_max
    assert restored.invoice_number == params.invoice_number
    assert restored.lien_eligible == params.lien_eligible
    assert restored.sort_by == params.sort_by
    assert restored.sort_order == params.sort_order


# ===================================================================
# Property 16: Invoice Filter Clear-All Identity
# Default InvoiceListParams produces zero filter clauses.
# Validates: Req 37.3
# ===================================================================
@pytest.mark.unit
def test_invoice_filter_clear_all_identity() -> None:
    default_params = InvoiceListParams()
    clauses = _repo._build_filters(default_params)
    assert len(clauses) == 0, (
        f"Default params should produce zero filters, got {len(clauses)}"
    )
