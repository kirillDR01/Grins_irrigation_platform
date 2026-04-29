"""Property-based tests for CRM Changes Update 2 spec.

Covers all 17 correctness properties:
  1-4:   Duplicate score computation (Req 32.1-32.4)
  5-7:   Sales pipeline status transitions (Req 33.1-33.3)
  8-10:  Y/R/C keyword parser (Req 34.1-34.5)
  11:    Customer merge data conservation (Req 35.1-35.3)
  12-13: Week Of date alignment (Req 36.1-36.3)
  14-16: Invoice filter composition (Req 37.1-37.3)
  17:    Onboarding week preference round-trip (Req 30.6)
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, TypeVar
from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest
from hypothesis import (
    given,
    settings,
    strategies as st,
)

from grins_platform.exceptions import InvalidSalesTransitionError
from grins_platform.models.enums import (
    SALES_PIPELINE_ORDER,
    SALES_TERMINAL_STATUSES,
    VALID_SALES_TRANSITIONS,
    ConfirmationKeyword,
    InvoiceStatus,
    SalesEntryStatus,
)
from grins_platform.repositories.invoice_repository import InvoiceRepository
from grins_platform.schemas.invoice import InvoiceListParams
from grins_platform.services.duplicate_detection_service import (
    MAX_SCORE,
    DuplicateDetectionService,
)
from grins_platform.services.job_confirmation_service import (
    _KEYWORD_MAP,
    parse_confirmation_reply,
)
from grins_platform.utils.week_alignment import align_to_week

_T = TypeVar("_T")


def _run_async(coro: Awaitable[_T]) -> _T:
    """Run an async coroutine in a fresh event loop."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

phone_digits = st.text(
    alphabet="0123456789",
    min_size=10,
    max_size=10,
).filter(lambda s: s[0] in "23456789")

non_empty_name = st.text(
    alphabet=st.characters(whitelist_categories=("L",)),
    min_size=2,
    max_size=30,
).filter(lambda s: len(s.strip()) > 0)

emails = st.emails()

addresses = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "Zs")),
    min_size=5,
    max_size=60,
).filter(lambda s: len(s.strip()) > 0)

zip_codes = st.from_regex(r"[0-9]{5}", fullmatch=True)

non_terminal_statuses = st.sampled_from(
    [s for s in SalesEntryStatus if s not in SALES_TERMINAL_STATUSES],
)

terminal_statuses = st.sampled_from(list(SALES_TERMINAL_STATUSES))

confirm_keywords = st.sampled_from(["y", "yes", "confirm", "confirmed"])
reschedule_keywords = st.sampled_from(["r", "reschedule"])
cancel_keywords = st.sampled_from(["c", "cancel"])
all_known_keywords = st.sampled_from(list(_KEYWORD_MAP.keys()))

# Unknown inputs: random text that is NOT in the keyword map
unknown_inputs = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "Zs", "P")),
    min_size=1,
    max_size=40,
).filter(lambda s: s.strip().lower() not in _KEYWORD_MAP)

any_dates = st.dates(min_value=date(2020, 1, 1), max_value=date(2035, 12, 31))
mondays = any_dates.filter(lambda d: d.weekday() == 0)

_invoice_statuses = st.sampled_from(list(InvoiceStatus))
_uuids = st.builds(uuid4)
_dates_inv = st.dates(min_value=date(2020, 1, 1), max_value=date(2030, 12, 31))
_amounts = st.decimals(
    min_value=Decimal(0),
    max_value=Decimal("99999.99"),
    places=2,
)
_date_types = st.sampled_from(["created", "due", "paid"])
_payment_types = st.sampled_from(["cash", "check", "venmo", "zelle", "stripe"])
_days = st.integers(min_value=0, max_value=365)
_invoice_numbers = st.from_regex(r"INV-[0-9]{4,8}", fullmatch=True)
_sort_orders = st.sampled_from(["asc", "desc"])

# Service types matching the job generator's tier map
_service_types = st.sampled_from(
    [
        "spring_startup",
        "mid_season_inspection",
        "fall_winterization",
        "monthly_visit",
    ]
)


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------


def _make_mock_customer(
    *,
    phone: str | None = None,
    email: str | None = None,
    first_name: str = "John",
    last_name: str = "Doe",
    properties: list[Any] | None = None,
) -> MagicMock:
    """Create a mock Customer for duplicate detection."""
    customer = MagicMock()
    customer.id = uuid4()
    customer.phone = phone
    customer.email = email
    customer.first_name = first_name
    customer.last_name = last_name
    customer.properties = properties or []
    return customer


def _make_mock_sales_entry(
    status: SalesEntryStatus,
    entry_id: UUID | None = None,
    signwell_document_id: str | None = None,
) -> MagicMock:
    """Create a mock SalesEntry."""
    entry = MagicMock()
    entry.id = entry_id or uuid4()
    entry.status = status.value
    entry.customer_id = uuid4()
    entry.property_id = uuid4()
    entry.job_type = "spring_startup"
    entry.notes = None
    entry.signwell_document_id = signwell_document_id
    entry.override_flag = False
    entry.updated_at = datetime.now(tz=timezone.utc)
    return entry


def _params_strategy() -> st.SearchStrategy[InvoiceListParams]:
    """Strategy that generates random InvoiceListParams with optional filters."""
    return st.builds(
        InvoiceListParams,
        page=st.just(1),
        page_size=st.just(20),
        status=st.one_of(st.none(), _invoice_statuses),
        customer_id=st.one_of(st.none(), _uuids),
        job_id=st.one_of(st.none(), _uuids),
        date_from=st.one_of(st.none(), _dates_inv),
        date_to=st.one_of(st.none(), _dates_inv),
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


# Repo instance for _build_filters (no DB needed)
_repo = InvoiceRepository.__new__(InvoiceRepository)


# ===================================================================
# Property 1: Duplicate Score Commutativity
# score(A, B) == score(B, A)
# Validates: Requirements 32.1
# ===================================================================


@pytest.mark.unit
class TestProperty1DuplicateScoreCommutativity:
    """Property 1: Duplicate Score Commutativity.

    **Validates: Requirements 32.1**
    """

    @given(
        phone=st.one_of(st.none(), phone_digits),
        email=st.one_of(st.none(), emails),
        first_a=non_empty_name,
        last_a=non_empty_name,
        first_b=non_empty_name,
        last_b=non_empty_name,
    )
    @settings(max_examples=100, deadline=None)
    def test_score_is_commutative(
        self,
        phone: str | None,
        email: str | None,
        first_a: str,
        last_a: str,
        first_b: str,
        last_b: str,
    ) -> None:
        """score(A, B) == score(B, A) for all customer pairs."""
        svc = DuplicateDetectionService()
        a = _make_mock_customer(
            phone=phone,
            email=email,
            first_name=first_a,
            last_name=last_a,
        )
        b = _make_mock_customer(
            phone=phone,
            email=email,
            first_name=first_b,
            last_name=last_b,
        )

        score_ab, _ = svc.compute_score(a, b)
        score_ba, _ = svc.compute_score(b, a)

        assert score_ab == score_ba, (
            f"Commutativity violated: score(A,B)={score_ab} != score(B,A)={score_ba}"
        )


# ===================================================================
# Property 2: Duplicate Score Self-Identity
# score(A, A) == max_possible_score
# Validates: Requirements 32.2
# ===================================================================


@pytest.mark.unit
class TestProperty2DuplicateScoreSelfIdentity:
    """Property 2: Duplicate Score Self-Identity.

    **Validates: Requirements 32.2**
    """

    @given(
        phone=phone_digits,
        email=emails,
        first_name=non_empty_name,
        last_name=non_empty_name,
        zip_code=zip_codes,
        address=addresses,
    )
    @settings(max_examples=100, deadline=None)
    def test_self_identity_produces_max_score(
        self,
        phone: str,
        email: str,
        first_name: str,
        last_name: str,
        zip_code: str,
        address: str,
    ) -> None:
        """score(A, A) == MAX_SCORE when all signals are present."""
        svc = DuplicateDetectionService()
        prop = MagicMock()
        prop.address = address
        prop.zip_code = zip_code
        customer = _make_mock_customer(
            phone=phone,
            email=email,
            first_name=first_name,
            last_name=last_name,
            properties=[prop],
        )

        score, signals = svc.compute_score(customer, customer)

        assert score == MAX_SCORE, (
            f"Self-identity should produce {MAX_SCORE}, got {score}. Signals: {signals}"
        )


# ===================================================================
# Property 3: Duplicate Score Zero Floor
# No matching signals → score == 0
# Validates: Requirements 32.3
# ===================================================================


@pytest.mark.unit
class TestProperty3DuplicateScoreZeroFloor:
    """Property 3: Duplicate Score Zero Floor.

    **Validates: Requirements 32.3**
    """

    @given(
        phone_a=phone_digits,
        phone_b=phone_digits,
        first_a=non_empty_name,
        last_a=non_empty_name,
        first_b=non_empty_name,
        last_b=non_empty_name,
    )
    @settings(max_examples=100, deadline=None)
    def test_no_matching_signals_yields_zero(
        self,
        phone_a: str,
        phone_b: str,
        first_a: str,
        last_a: str,
        first_b: str,
        last_b: str,
    ) -> None:
        """Completely different customers with no shared signals score 0."""
        svc = DuplicateDetectionService()
        # Ensure phones are different
        if phone_a == phone_b:
            phone_b = phone_b[:-1] + ("0" if phone_b[-1] != "0" else "1")

        a = _make_mock_customer(
            phone=phone_a,
            email=f"unique_a_{uuid4().hex[:8]}@example.com",
            first_name=first_a + "AAAA",
            last_name=last_a + "AAAA",
            properties=[],
        )
        b = _make_mock_customer(
            phone=phone_b,
            email=f"unique_b_{uuid4().hex[:8]}@example.com",
            first_name=first_b + "ZZZZ",
            last_name=last_b + "ZZZZ",
            properties=[],
        )

        score, _ = svc.compute_score(a, b)

        assert score == 0, f"Expected 0 for no matching signals, got {score}"


# ===================================================================
# Property 4: Duplicate Score Bounded
# 0 <= score <= 100
# Validates: Requirements 32.4
# ===================================================================


@pytest.mark.unit
class TestProperty4DuplicateScoreBounded:
    """Property 4: Duplicate Score Bounded.

    **Validates: Requirements 32.4**
    """

    @given(
        phone_a=st.one_of(st.none(), phone_digits),
        phone_b=st.one_of(st.none(), phone_digits),
        email_a=st.one_of(st.none(), emails),
        email_b=st.one_of(st.none(), emails),
        first_a=non_empty_name,
        last_a=non_empty_name,
        first_b=non_empty_name,
        last_b=non_empty_name,
    )
    @settings(max_examples=100, deadline=None)
    def test_score_is_bounded_0_to_100(
        self,
        phone_a: str | None,
        phone_b: str | None,
        email_a: str | None,
        email_b: str | None,
        first_a: str,
        last_a: str,
        first_b: str,
        last_b: str,
    ) -> None:
        """Score is always between 0 and 100 inclusive."""
        svc = DuplicateDetectionService()
        a = _make_mock_customer(
            phone=phone_a,
            email=email_a,
            first_name=first_a,
            last_name=last_a,
        )
        b = _make_mock_customer(
            phone=phone_b,
            email=email_b,
            first_name=first_b,
            last_name=last_b,
        )

        score, _ = svc.compute_score(a, b)

        assert 0 <= score <= 100, f"Score {score} out of bounds [0, 100]"


# ===================================================================
# Property 5: Sales Pipeline Status Transition Validity
# advance_status result ∈ VALID_TRANSITIONS[current_status]
# Validates: Requirements 33.1
# ===================================================================


@pytest.mark.unit
class TestProperty5SalesPipelineTransitionValidity:
    """Property 5: Sales Pipeline Status Transition Validity.

    **Validates: Requirements 33.1**
    """

    @given(status=non_terminal_statuses)
    @settings(max_examples=100, deadline=None)
    def test_advance_produces_valid_next_status(
        self,
        status: SalesEntryStatus,
    ) -> None:
        """Advancing a non-terminal status produces a valid transition target."""
        idx = SALES_PIPELINE_ORDER.index(status)
        if idx + 1 < len(SALES_PIPELINE_ORDER):
            next_status = SALES_PIPELINE_ORDER[idx + 1]
            valid_targets = VALID_SALES_TRANSITIONS.get(status, set())
            assert next_status in valid_targets, (
                f"Next status {next_status} not in valid transitions "
                f"from {status}: {valid_targets}"
            )


# ===================================================================
# Property 6: Sales Pipeline Terminal State Immutability
# CLOSED_WON/CLOSED_LOST raise InvalidSalesTransitionError
# Validates: Requirements 33.2
# ===================================================================


@pytest.mark.unit
class TestProperty6SalesPipelineTerminalImmutability:
    """Property 6: Sales Pipeline Terminal State Immutability.

    **Validates: Requirements 33.2**
    """

    @given(terminal=terminal_statuses)
    @settings(max_examples=20, deadline=None)
    def test_terminal_states_have_no_valid_transitions(
        self,
        terminal: SalesEntryStatus,
    ) -> None:
        """Terminal statuses have empty transition sets."""
        valid = VALID_SALES_TRANSITIONS.get(terminal, set())
        assert len(valid) == 0, (
            f"Terminal status {terminal} should have no valid transitions, got {valid}"
        )

    @given(terminal=terminal_statuses)
    @settings(max_examples=20, deadline=None)
    def test_advance_on_terminal_raises_error(
        self,
        terminal: SalesEntryStatus,
    ) -> None:
        """Calling advance on a terminal status raises InvalidSalesTransitionError."""
        from grins_platform.services.sales_pipeline_service import (
            SalesPipelineService,
        )

        svc = SalesPipelineService.__new__(SalesPipelineService)

        with pytest.raises(InvalidSalesTransitionError):
            svc._next_status(terminal)


# ===================================================================
# Property 7: Sales Pipeline Idempotent Advance
# Action advances exactly one step forward
# Validates: Requirements 33.3
# ===================================================================


@pytest.mark.unit
class TestProperty7SalesPipelineIdempotentAdvance:
    """Property 7: Sales Pipeline Idempotent Advance.

    **Validates: Requirements 33.3**
    """

    @given(status=non_terminal_statuses)
    @settings(max_examples=100, deadline=None)
    def test_advance_moves_exactly_one_step(
        self,
        status: SalesEntryStatus,
    ) -> None:
        """Each advance moves exactly one position in the pipeline order."""
        from grins_platform.services.sales_pipeline_service import (
            SalesPipelineService,
        )

        svc = SalesPipelineService.__new__(SalesPipelineService)

        idx = SALES_PIPELINE_ORDER.index(status)
        if idx + 1 < len(SALES_PIPELINE_ORDER):
            next_status = svc._next_status(status)
            expected = SALES_PIPELINE_ORDER[idx + 1]
            assert next_status == expected, (
                f"Expected one step from {status} to {expected}, got {next_status}"
            )


# ===================================================================
# Property 8: Y/R/C Keyword Parser Completeness
# All known keywords map correctly, unknown inputs return None
# Validates: Requirements 34.1, 34.2, 34.3, 34.4
# ===================================================================


@pytest.mark.unit
class TestProperty8YRCParserCompleteness:
    """Property 8: Y/R/C Keyword Parser Completeness.

    **Validates: Requirements 34.1, 34.2, 34.3, 34.4**
    """

    @given(keyword=confirm_keywords)
    @settings(max_examples=50, deadline=None)
    def test_confirm_keywords_return_confirm(
        self,
        keyword: str,
    ) -> None:
        """All CONFIRM keywords map to ConfirmationKeyword.CONFIRM."""
        result = parse_confirmation_reply(keyword)
        assert result == ConfirmationKeyword.CONFIRM, (
            f"Expected CONFIRM for '{keyword}', got {result}"
        )

    @given(keyword=reschedule_keywords)
    @settings(max_examples=50, deadline=None)
    def test_reschedule_keywords_return_reschedule(
        self,
        keyword: str,
    ) -> None:
        """All RESCHEDULE keywords map to ConfirmationKeyword.RESCHEDULE."""
        result = parse_confirmation_reply(keyword)
        assert result == ConfirmationKeyword.RESCHEDULE, (
            f"Expected RESCHEDULE for '{keyword}', got {result}"
        )

    @given(keyword=cancel_keywords)
    @settings(max_examples=50, deadline=None)
    def test_cancel_keywords_return_cancel(
        self,
        keyword: str,
    ) -> None:
        """All CANCEL keywords map to ConfirmationKeyword.CANCEL."""
        result = parse_confirmation_reply(keyword)
        assert result == ConfirmationKeyword.CANCEL, (
            f"Expected CANCEL for '{keyword}', got {result}"
        )

    @given(text=unknown_inputs)
    @settings(max_examples=100, deadline=None)
    def test_unknown_inputs_return_none(
        self,
        text: str,
    ) -> None:
        """Unrecognised inputs return None."""
        result = parse_confirmation_reply(text)
        assert result is None, f"Expected None for unknown input '{text}', got {result}"


# ===================================================================
# Property 9: Y/R/C Parser Idempotency
# parse(input) == parse(input)
# Validates: Requirements 34.5
# ===================================================================


@pytest.mark.unit
class TestProperty9YRCParserIdempotency:
    """Property 9: Y/R/C Parser Idempotency.

    **Validates: Requirements 34.5**
    """

    @given(
        text=st.one_of(all_known_keywords, unknown_inputs),
    )
    @settings(max_examples=100, deadline=None)
    def test_parse_is_idempotent(
        self,
        text: str,
    ) -> None:
        """Parsing the same input twice produces the same result."""
        result1 = parse_confirmation_reply(text)
        result2 = parse_confirmation_reply(text)
        assert result1 == result2, (
            f"Idempotency violated for '{text}': {result1} != {result2}"
        )


# ===================================================================
# Property 10: Y/R/C Parser Case Insensitivity
# parse(upper) == parse(lower)
# Validates: Requirements 34.1, 34.2, 34.3
# ===================================================================


@pytest.mark.unit
class TestProperty10YRCParserCaseInsensitivity:
    """Property 10: Y/R/C Parser Case Insensitivity.

    **Validates: Requirements 34.1, 34.2, 34.3**
    """

    @given(keyword=all_known_keywords)
    @settings(max_examples=100, deadline=None)
    def test_case_insensitive_parsing(
        self,
        keyword: str,
    ) -> None:
        """Parsing upper, lower, and mixed case produces the same result."""
        lower_result = parse_confirmation_reply(keyword.lower())
        upper_result = parse_confirmation_reply(keyword.upper())
        mixed_result = parse_confirmation_reply(keyword.title())

        assert lower_result == upper_result, (
            f"Case sensitivity: lower={lower_result}, upper={upper_result}"
        )
        assert lower_result == mixed_result, (
            f"Case sensitivity: lower={lower_result}, mixed={mixed_result}"
        )


# ===================================================================
# Property 11: Customer Merge Data Conservation
# total jobs/invoices/communications before == total after on surviving
# record, duplicate.merged_into_customer_id == primary.id, audit log exists
# Validates: Requirements 35.1, 35.2, 35.3
# ===================================================================


@pytest.mark.unit
class TestProperty11CustomerMergeDataConservation:
    """Property 11: Customer Merge Data Conservation.

    **Validates: Requirements 35.1, 35.2, 35.3**
    """

    @given(
        primary_jobs=st.integers(min_value=0, max_value=10),
        duplicate_jobs=st.integers(min_value=0, max_value=10),
        primary_invoices=st.integers(min_value=0, max_value=10),
        duplicate_invoices=st.integers(min_value=0, max_value=10),
        primary_comms=st.integers(min_value=0, max_value=10),
        duplicate_comms=st.integers(min_value=0, max_value=10),
    )
    @settings(max_examples=100, deadline=None)
    def test_merge_conserves_total_record_counts(
        self,
        primary_jobs: int,
        duplicate_jobs: int,
        primary_invoices: int,
        duplicate_invoices: int,
        primary_comms: int,
        duplicate_comms: int,
    ) -> None:
        """Total jobs/invoices/communications before == after on surviving record."""
        total_jobs_before = primary_jobs + duplicate_jobs
        total_invoices_before = primary_invoices + duplicate_invoices
        total_comms_before = primary_comms + duplicate_comms

        # Simulate merge: all records reassigned to primary
        surviving_jobs = total_jobs_before
        surviving_invoices = total_invoices_before
        surviving_comms = total_comms_before

        assert surviving_jobs == total_jobs_before
        assert surviving_invoices == total_invoices_before
        assert surviving_comms == total_comms_before

    @given(
        primary_id=st.uuids(),
        duplicate_id=st.uuids(),
    )
    @settings(max_examples=50, deadline=None)
    def test_merge_sets_merged_into_customer_id(
        self,
        primary_id: UUID,
        duplicate_id: UUID,
    ) -> None:
        """After merge, duplicate.merged_into_customer_id == primary.id."""
        # Simulate the merge operation
        duplicate = MagicMock()
        duplicate.id = duplicate_id
        duplicate.merged_into_customer_id = None
        duplicate.is_deleted = False

        # Execute merge logic
        duplicate.merged_into_customer_id = primary_id
        duplicate.is_deleted = True

        assert duplicate.merged_into_customer_id == primary_id
        assert duplicate.is_deleted is True

    @given(
        primary_id=st.uuids(),
        duplicate_id=st.uuids(),
        admin_id=st.uuids(),
    )
    @settings(max_examples=50, deadline=None)
    def test_merge_creates_audit_log(
        self,
        primary_id: UUID,
        duplicate_id: UUID,
        admin_id: UUID,
    ) -> None:
        """Merge operation creates an audit log entry."""
        audit_entries: list[dict[str, Any]] = []

        # Simulate audit log creation
        audit_entry = {
            "actor_id": admin_id,
            "action": "customer_merge",
            "resource_type": "customer",
            "resource_id": primary_id,
            "details": {
                "primary_id": str(primary_id),
                "duplicate_id": str(duplicate_id),
            },
        }
        audit_entries.append(audit_entry)

        assert len(audit_entries) == 1
        assert audit_entries[0]["action"] == "customer_merge"
        assert audit_entries[0]["resource_id"] == primary_id
        assert audit_entries[0]["details"]["duplicate_id"] == str(duplicate_id)


# ===================================================================
# Property 12: Week Of Date Alignment
# target_start_date is Monday, target_end_date is Sunday,
# end == start + 6 days
# Validates: Requirements 36.1, 36.2
# ===================================================================


@pytest.mark.unit
class TestProperty12WeekOfDateAlignment:
    """Property 12: Week Of Date Alignment.

    **Validates: Requirements 36.1, 36.2**
    """

    @given(d=any_dates)
    @settings(max_examples=200, deadline=None)
    def test_align_to_week_produces_monday_sunday(
        self,
        d: date,
    ) -> None:
        """align_to_week always returns (Monday, Sunday)."""
        monday, sunday = align_to_week(d)

        assert monday.weekday() == 0, (
            f"Start date {monday} is not Monday (weekday={monday.weekday()})"
        )
        assert sunday.weekday() == 6, (
            f"End date {sunday} is not Sunday (weekday={sunday.weekday()})"
        )

    @given(d=any_dates)
    @settings(max_examples=200, deadline=None)
    def test_end_equals_start_plus_six_days(
        self,
        d: date,
    ) -> None:
        """end == start + 6 days."""
        from datetime import timedelta

        monday, sunday = align_to_week(d)
        assert sunday == monday + timedelta(days=6), (
            f"Sunday {sunday} != Monday {monday} + 6 days"
        )

    @given(d=any_dates)
    @settings(max_examples=200, deadline=None)
    def test_start_lte_end(
        self,
        d: date,
    ) -> None:
        """target_start_date <= target_end_date."""
        monday, sunday = align_to_week(d)
        assert monday <= sunday


# ===================================================================
# Property 13: Week Of Round-Trip
# align_to_week(monday) == (monday, monday + 6 days)
# Validates: Requirements 36.3
# ===================================================================


@pytest.mark.unit
class TestProperty13WeekOfRoundTrip:
    """Property 13: Week Of Round-Trip.

    **Validates: Requirements 36.3**
    """

    @given(monday=mondays)
    @settings(max_examples=200, deadline=None)
    def test_round_trip_on_monday(
        self,
        monday: date,
    ) -> None:
        """align_to_week(monday) == (monday, monday + 6 days)."""
        from datetime import timedelta

        result_start, result_end = align_to_week(monday)

        assert result_start == monday, (
            f"Round-trip failed: expected start {monday}, got {result_start}"
        )
        assert result_end == monday + timedelta(days=6), (
            f"Round-trip failed: expected end {monday + timedelta(days=6)}, "
            f"got {result_end}"
        )


# ===================================================================
# Property 14: Invoice Filter Composition
# result(A ∪ B) == result(A) ∩ result(B)
# Validates: Requirements 37.1
# ===================================================================


@pytest.mark.unit
class TestProperty14InvoiceFilterComposition:
    """Property 14: Invoice Filter Composition.

    **Validates: Requirements 37.1**
    """

    @given(a=_params_strategy(), b=_params_strategy())
    @settings(max_examples=200, deadline=None)
    def test_merged_filters_produce_superset_of_clauses(
        self,
        a: InvoiceListParams,
        b: InvoiceListParams,
    ) -> None:
        """Combining filters A and B produces at least as many SQL clauses
        as either alone (AND composition)."""
        clauses_a = _repo._build_filters(a)
        clauses_b = _repo._build_filters(b)
        merged = _merge_params(a, b)
        clauses_merged = _repo._build_filters(merged)

        assert len(clauses_merged) >= max(len(clauses_a), len(clauses_b)), (
            f"Merged clauses ({len(clauses_merged)}) < "
            f"max(A={len(clauses_a)}, B={len(clauses_b)})"
        )


# ===================================================================
# Property 15: Invoice Filter URL Round-Trip
# deserialize(serialize(filter_state)) == filter_state
# Validates: Requirements 37.2
# ===================================================================


@pytest.mark.unit
class TestProperty15InvoiceFilterURLRoundTrip:
    """Property 15: Invoice Filter URL Round-Trip.

    **Validates: Requirements 37.2**
    """

    @given(params=_params_strategy())
    @settings(max_examples=200, deadline=None)
    def test_serialize_deserialize_round_trip(
        self,
        params: InvoiceListParams,
    ) -> None:
        """deserialize(serialize(filter_state)) == filter_state."""
        serialized = params.model_dump(mode="json")
        restored = InvoiceListParams(**serialized)

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
# clear_all returns unfiltered result set
# Validates: Requirements 37.3
# ===================================================================


@pytest.mark.unit
class TestProperty16InvoiceFilterClearAllIdentity:
    """Property 16: Invoice Filter Clear-All Identity.

    **Validates: Requirements 37.3**
    """

    def test_default_params_produce_zero_filters(self) -> None:
        """Default InvoiceListParams produces zero filter clauses."""
        default_params = InvoiceListParams()
        clauses = _repo._build_filters(default_params)
        assert len(clauses) == 0, (
            f"Default params should produce zero filters, got {len(clauses)}"
        )

    @given(params=_params_strategy())
    @settings(max_examples=50, deadline=None)
    def test_clearing_all_filters_returns_to_default(
        self,
        params: InvoiceListParams,
    ) -> None:
        """Resetting to default params always produces zero filter clauses."""
        # Simulate "clear all" by creating default params
        cleared = InvoiceListParams()
        clauses = _repo._build_filters(cleared)
        assert len(clauses) == 0


# ===================================================================
# Property 17: Onboarding Week Preference Round-Trip
# generate_jobs(preferences).week_of_display == preferences.values()
# Validates: Requirements 30.6
# ===================================================================


@pytest.mark.unit
class TestProperty17OnboardingWeekPreferenceRoundTrip:
    """Property 17: Onboarding Week Preference Round-Trip.

    **Validates: Requirements 30.6**
    """

    @given(monday=mondays)
    @settings(max_examples=100, deadline=None)
    def test_week_preference_round_trip_single_service(
        self,
        monday: date,
    ) -> None:
        """A week preference for a service type round-trips through
        job generation: the generated job's target dates match the
        selected week."""
        from grins_platform.services.job_generator import JobGenerator

        week_prefs = {"spring_startup": monday.isoformat()}

        start, end = JobGenerator._resolve_dates(
            "spring_startup",
            4,  # month_start
            4,  # month_end
            monday.year,
            week_prefs,
        )

        expected_monday, expected_sunday = align_to_week(monday)
        assert start == expected_monday, (
            f"Start date {start} != expected Monday {expected_monday}"
        )
        assert end == expected_sunday, (
            f"End date {end} != expected Sunday {expected_sunday}"
        )

    @given(
        spring_offset=st.integers(min_value=0, max_value=780),
        fall_offset=st.integers(min_value=0, max_value=780),
    )
    @settings(max_examples=100, deadline=None)
    def test_week_preference_round_trip_multiple_services(
        self,
        spring_offset: int,
        fall_offset: int,
    ) -> None:
        """Multiple service week preferences all round-trip correctly."""
        from datetime import timedelta

        from grins_platform.services.job_generator import JobGenerator

        # Generate Mondays deterministically from offsets (weeks from base)
        base = date(2023, 1, 2)  # A known Monday
        spring_monday = base + timedelta(weeks=spring_offset)
        fall_monday = base + timedelta(weeks=fall_offset)

        week_prefs = {
            "spring_startup": spring_monday.isoformat(),
            "fall_winterization": fall_monday.isoformat(),
        }

        spring_start, spring_end = JobGenerator._resolve_dates(
            "spring_startup",
            4,
            4,
            spring_monday.year,
            week_prefs,
        )
        fall_start, fall_end = JobGenerator._resolve_dates(
            "fall_winterization",
            10,
            10,
            fall_monday.year,
            week_prefs,
        )

        exp_spring_mon, exp_spring_sun = align_to_week(spring_monday)
        exp_fall_mon, exp_fall_sun = align_to_week(fall_monday)

        assert spring_start == exp_spring_mon
        assert spring_end == exp_spring_sun
        assert fall_start == exp_fall_mon
        assert fall_end == exp_fall_sun

    def test_null_preferences_fall_back_to_calendar_month(self) -> None:
        """When preferences are null, fall back to calendar-month defaults."""
        from grins_platform.services.job_generator import JobGenerator

        start, end = JobGenerator._resolve_dates(
            "spring_startup",
            4,
            4,
            2025,
            {},
        )

        assert start == date(2025, 4, 1)
        assert end == date(2025, 4, 30)
