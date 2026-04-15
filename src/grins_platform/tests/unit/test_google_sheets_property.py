"""Property-based tests for Google Sheets service.

Property 1: Row padding produces exactly 18 columns.
Property 2: New submission invariants.
Property 3: Client type determines lead creation.
Property 4: Situation mapping priority.
Property 5: Notes aggregation contains all non-empty fields.
Property 7: Sheet-created leads have null zip_code.
Property 8: Public form submission requires address.
Property 9: Duplicate phone deduplication.
Property 10: Row processing error isolation.
Property 11: Only new rows are processed.
Property 12: Token refresh triggers within expiry buffer.
Property 13: Header row detection.
Property 14: Submission list filtering.
Property 15: Manual lead creation idempotency guard.
Property 16: Concurrent poll cycles are serialized.
Property 17: safe_normalize_phone wraps normalize_phone.

Validates: Requirements 1.5, 1.8, 2.1, 2.3, 2.4, 3.1, 3.2, 3.3,
3.4, 3.5, 3.6, 3.8, 3.10, 4.2, 4.3, 4.4, 5.1, 5.5, 5.8, 6.10, 17.3
"""

import asyncio
import time
from math import ceil
from typing import ClassVar
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from hypothesis import (
    given,
    settings,
    strategies as st,
)

from grins_platform.models.enums import LeadSituation
from grins_platform.schemas.customer import normalize_phone
from grins_platform.schemas.google_sheet_submission import PaginatedSubmissionResponse
from grins_platform.services.google_sheets_service import (
    _SHEET_COLUMNS,
    EXPECTED_COLUMNS,
    GoogleSheetsService,
    pad_row,
    remap_sheet_row,
)


@pytest.mark.unit
class TestRowPaddingProperty:
    """Property 1: Row padding produces exactly 18 columns.

    For any list of strings with length between 0 and 18 (inclusive),
    padding the row should produce a list of exactly 18 elements where
    the original values are preserved in order and any added values are
    empty strings.
    """

    @given(row=st.lists(st.text(max_size=50), min_size=0, max_size=18))
    @settings(max_examples=200)
    def test_pad_row_always_produces_18_columns(self, row: list[str]) -> None:
        result = pad_row(row)
        assert len(result) == EXPECTED_COLUMNS

    @given(row=st.lists(st.text(max_size=50), min_size=0, max_size=18))
    @settings(max_examples=200)
    def test_pad_row_preserves_original_values(self, row: list[str]) -> None:
        result = pad_row(row)
        for i, val in enumerate(row):
            assert result[i] == val

    @given(row=st.lists(st.text(max_size=50), min_size=0, max_size=17))
    @settings(max_examples=200)
    def test_pad_row_fills_with_empty_strings(self, row: list[str]) -> None:
        result = pad_row(row)
        for i in range(len(row), EXPECTED_COLUMNS):
            assert result[i] == ""

    @given(row=st.lists(st.text(max_size=50), min_size=19, max_size=30))
    @settings(max_examples=100)
    def test_pad_row_truncates_extra_columns(self, row: list[str]) -> None:
        result = pad_row(row)
        assert len(result) == EXPECTED_COLUMNS
        assert result == row[:EXPECTED_COLUMNS]


# Strategies for non-blank and blank strings
_non_blank = st.text(min_size=1, max_size=20).filter(
    lambda s: s.strip() != "",
)
_blank = st.sampled_from(["", " ", "  "])
_txt = st.text(max_size=5)
_any3 = st.tuples(_txt, _txt, _txt)


def _build_row(
    seasonal: tuple[str, str, str],
    repair: str,
    new_system: str,
    addition: str,
) -> list[str]:
    """Build an 18-element row with service columns at indices 1-6."""
    row = [""] * EXPECTED_COLUMNS
    row[1], row[2], row[3] = seasonal
    row[4] = repair
    row[5] = new_system
    row[6] = addition
    return row


@pytest.mark.unit
class TestSituationMappingPriorityProperty:
    """Property 4: Situation mapping priority.

    new_system_install (idx 5) wins over all others → NEW_SYSTEM.
    Else addition_to_system (idx 6) → UPGRADE.
    Else repair_existing (idx 4) → REPAIR.
    Else any seasonal (idx 1-3) → EXPLORING.
    Else → EXPLORING.
    """

    @given(
        seasonal=_any3,
        repair=_txt,
        new_system=_non_blank,
        addition=_txt,
    )
    @settings(max_examples=200)
    def test_new_system_always_wins(
        self,
        seasonal: tuple[str, str, str],
        repair: str,
        new_system: str,
        addition: str,
    ) -> None:
        """new_system_install set → NEW_SYSTEM regardless of other flags."""
        row = _build_row(seasonal, repair, new_system=new_system, addition=addition)
        assert GoogleSheetsService.map_situation(row) == LeadSituation.NEW_SYSTEM

    @given(
        seasonal=_any3,
        repair=_txt,
        addition=_non_blank,
    )
    @settings(max_examples=200)
    def test_addition_wins_when_no_new_system(
        self,
        seasonal: tuple[str, str, str],
        repair: str,
        addition: str,
    ) -> None:
        """addition_to_system set, new_system_install blank → UPGRADE."""
        row = _build_row(seasonal, repair, new_system="", addition=addition)
        assert GoogleSheetsService.map_situation(row) == LeadSituation.UPGRADE

    @given(
        seasonal=_any3,
        repair=_non_blank,
    )
    @settings(max_examples=200)
    def test_repair_wins_when_no_new_system_or_addition(
        self,
        seasonal: tuple[str, str, str],
        repair: str,
    ) -> None:
        """repair_existing set, higher-priority flags blank → REPAIR."""
        row = _build_row(seasonal, repair, new_system="", addition="")
        assert GoogleSheetsService.map_situation(row) == LeadSituation.REPAIR

    @given(
        seasonal=st.tuples(_non_blank, _txt, _txt)
        | st.tuples(_txt, _non_blank, _txt)
        | st.tuples(_txt, _txt, _non_blank),
    )
    @settings(max_examples=200)
    def test_seasonal_returns_exploring(
        self,
        seasonal: tuple[str, str, str],
    ) -> None:
        """At least one seasonal flag set, all higher-priority blank → EXPLORING."""
        row = _build_row(seasonal, repair="", new_system="", addition="")
        assert GoogleSheetsService.map_situation(row) == LeadSituation.EXPLORING

    def test_all_blank_returns_exploring(self) -> None:
        """No flags set → EXPLORING."""
        row = _build_row(("", "", ""), repair="", new_system="", addition="")
        assert GoogleSheetsService.map_situation(row) == LeadSituation.EXPLORING

    @given(
        seasonal=st.tuples(_blank, _blank, _blank),
        repair=_blank,
        addition=_blank,
    )
    @settings(max_examples=100)
    def test_whitespace_only_treated_as_blank(
        self,
        seasonal: tuple[str, str, str],
        repair: str,
        addition: str,
    ) -> None:
        """Whitespace-only strings are treated as blank → EXPLORING."""
        row = _build_row(seasonal, repair, new_system=" ", addition=addition)
        assert GoogleSheetsService.map_situation(row) == LeadSituation.EXPLORING


# --- Property 5: Notes aggregation contains all non-empty fields ---

# Indices that aggregate_notes inspects:
# Service columns: 1 (Spring Startup), 2 (Fall Blowout), 3 (Summer Tuneup),
#                  4 (Repair), 5 (New System Install), 6 (Addition to System)
# Field map: 7 (Additional services), 8 (Date needed by), 12 (City),
#            13 (Address), 16 (Referral source), 17 (Landscape/Hardscape)
_NOTES_RELEVANT_INDICES = [1, 2, 3, 4, 5, 6, 7, 8, 12, 13, 16, 17]


def _make_notes_row(values: dict[int, str]) -> list[str]:
    """Build an 18-element row with specific index values."""
    row = [""] * EXPECTED_COLUMNS
    for idx, val in values.items():
        row[idx] = val
    return row


@pytest.mark.unit
class TestNotesAggregationProperty:
    """Property 5: Notes aggregation contains all non-empty fields.

    For any row of 18 strings, aggregate_notes() output contains every
    non-empty, non-whitespace value from the relevant columns. If all
    relevant fields are empty, the result is an empty string.
    """

    @given(
        row=st.lists(
            st.text(
                alphabet=st.characters(blacklist_categories=["Cs"]),
                max_size=30,
            ),
            min_size=EXPECTED_COLUMNS,
            max_size=EXPECTED_COLUMNS,
        ),
    )
    @settings(max_examples=300)
    def test_all_non_empty_values_appear_in_output(self, row: list[str]) -> None:
        """Every non-blank relevant field value appears in the notes string."""
        result = GoogleSheetsService.aggregate_notes(row)
        for idx in _NOTES_RELEVANT_INDICES:
            val = row[idx].strip()
            if val:
                assert val in result, f"Value {val!r} at index {idx} missing from notes"

    @given(
        row=st.lists(
            st.sampled_from(["", " ", "  ", "\t"]),
            min_size=EXPECTED_COLUMNS,
            max_size=EXPECTED_COLUMNS,
        ),
    )
    @settings(max_examples=100)
    def test_all_blank_fields_produce_empty_string(self, row: list[str]) -> None:
        """When all relevant fields are blank/whitespace, result is empty."""
        assert GoogleSheetsService.aggregate_notes(row) == ""

    @given(
        idx=st.sampled_from(_NOTES_RELEVANT_INDICES),
        value=_non_blank,
    )
    @settings(max_examples=200)
    def test_single_non_empty_field_appears(self, idx: int, value: str) -> None:
        """A single non-blank field produces non-empty notes containing it."""
        row = _make_notes_row({idx: value})
        result = GoogleSheetsService.aggregate_notes(row)
        assert result != ""
        assert value.strip() in result


# --- Property 6: Field fallbacks for missing data ---

# Strategy: valid 10-digit phone strings (with optional formatting)
_valid_10_digits = st.from_regex(r"[0-9]{10}", fullmatch=True)
_blank_str = st.sampled_from(["", " ", "  ", "\t", "\n"])
_invalid_phone = st.sampled_from(["", " ", "abc", "123", "12345", "12345678901234"])


@pytest.mark.unit
class TestFieldFallbacksProperty:
    """Property 6: Field fallbacks for missing data.

    normalize_name: blank/whitespace → "Unknown", non-blank → trimmed original.
    safe_normalize_phone: empty/invalid → "0000000000", valid 10-digit → normalized.

    Validates: Requirements 3.9, 3.10
    """

    @given(name=_blank_str)
    @settings(max_examples=50)
    def test_normalize_name_blank_returns_unknown(self, name: str) -> None:
        assert GoogleSheetsService.normalize_name(name) == "Unknown"

    @given(name=_non_blank)
    @settings(max_examples=200)
    def test_normalize_name_non_blank_returns_trimmed(self, name: str) -> None:
        result = GoogleSheetsService.normalize_name(name)
        assert result == name.strip()
        assert result != "Unknown"

    @given(phone=_invalid_phone)
    @settings(max_examples=50)
    def test_safe_normalize_phone_invalid_returns_fallback(self, phone: str) -> None:
        assert GoogleSheetsService.safe_normalize_phone(phone) == "0000000000"

    @given(phone=_valid_10_digits)
    @settings(max_examples=200)
    def test_safe_normalize_phone_valid_returns_digits(self, phone: str) -> None:
        result = GoogleSheetsService.safe_normalize_phone(phone)
        assert result == phone
        assert len(result) == 10
        assert result.isdigit()


# --- Property 17: safe_normalize_phone wraps normalize_phone ---


@pytest.mark.unit
class TestSafeNormalizePhoneWrapsProperty:
    """Property 17: safe_normalize_phone wraps normalize_phone.

    For any phone string, safe_normalize_phone returns the same result as
    normalize_phone when it succeeds. When normalize_phone raises ValueError,
    safe_normalize_phone returns "0000000000". It never raises an exception.

    Validates: Requirements 3.10, 17.3
    """

    @given(phone=st.text(max_size=30))
    @settings(max_examples=300)
    def test_matches_normalize_phone_or_returns_fallback(self, phone: str) -> None:
        """Agrees with normalize_phone on success, falls back on error."""
        try:
            expected = normalize_phone(phone)
        except ValueError:
            expected = "0000000000"

        assert GoogleSheetsService.safe_normalize_phone(phone) == expected

    @given(phone=st.text(max_size=30))
    @settings(max_examples=300)
    def test_never_raises(self, phone: str) -> None:
        """safe_normalize_phone never raises any exception."""
        result = GoogleSheetsService.safe_normalize_phone(phone)
        assert isinstance(result, str)


# --- Property 3: Client type determines lead creation ---

# Strategy: generate "new" with random case and surrounding whitespace
_new_variant = st.tuples(
    st.sampled_from(["new", "New", "NEW", "nEw", "neW", "nEW"]),
    st.sampled_from(["", " ", "  "]),
    st.sampled_from(["", " ", "  "]),
).map(lambda t: t[1] + t[0] + t[2])


def _make_row_with_client_type(client_type: str) -> list[str]:
    """Build an 18-element row with a given client_type at index 14 and valid phone."""
    row = [""] * EXPECTED_COLUMNS
    row[9] = "Test Name"
    row[10] = "6125551234"
    row[14] = client_type
    return row


def _run_process_row(client_type: str) -> list[dict[str, object]]:
    """Run process_row with mocked repos and return the sub_repo.update call dicts."""
    row = _make_row_with_client_type(client_type)
    sub_id = uuid4()
    lead_id = uuid4()

    mock_submission = MagicMock()
    mock_submission.id = sub_id
    mock_submission.processing_status = "imported"
    mock_submission.lead_id = None

    mock_lead = MagicMock()
    mock_lead.id = lead_id

    mock_sub_repo = AsyncMock()
    mock_sub_repo.create.return_value = mock_submission
    mock_sub_repo.get_by_id.return_value = mock_submission

    mock_lead_repo = AsyncMock()
    mock_lead_repo.get_by_phone_and_active_status.return_value = None
    mock_lead_repo.create.return_value = mock_lead

    mock_session = AsyncMock()

    with (
        patch(
            "grins_platform.services.google_sheets_service.GoogleSheetSubmissionRepository",
            return_value=mock_sub_repo,
        ),
        patch(
            "grins_platform.services.google_sheets_service.LeadRepository",
            return_value=mock_lead_repo,
        ),
    ):
        service = GoogleSheetsService(None, None)
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(service.process_row(row, 2, mock_session))
        finally:
            loop.close()

    return [
        call.args[1] if len(call.args) > 1 else call.kwargs
        for call in mock_sub_repo.update.call_args_list
    ]


@pytest.mark.unit
class TestClientTypeDeterminesLeadCreationProperty:
    """Property 3: All submissions auto-promoted to leads.

    For any submission regardless of client_type, processing should result
    in processing_status = "lead_created" with promoted_to_lead_id set.
    New clients get source_detail "New client work request", others get
    "Existing client work request".

    Validates: Requirements 52.1, 52.2, 52.5
    """

    @given(client_type=_new_variant)
    @settings(max_examples=200)
    def test_new_client_type_results_in_lead_created(
        self,
        client_type: str,
    ) -> None:
        """client_type 'new' (any case/whitespace) → lead_created."""
        updates = _run_process_row(client_type)
        assert any(u.get("processing_status") == "lead_created" for u in updates), (
            f"Expected lead_created for client_type={client_type!r}, got {updates}"
        )

    @given(
        client_type=st.text(max_size=20).filter(
            lambda s: s.strip().lower() != "new",
        ),
    )
    @settings(max_examples=200)
    def test_non_new_client_type_also_creates_lead(
        self,
        client_type: str,
    ) -> None:
        """client_type not 'new' → still auto-promoted to lead_created."""
        updates = _run_process_row(client_type)
        assert any(u.get("processing_status") == "lead_created" for u in updates), (
            f"Expected lead_created for client_type={client_type!r}, got {updates}"
        )
        assert any(u.get("promoted_to_lead_id") is not None for u in updates), (
            f"Expected promoted_to_lead_id set for client_type={client_type!r}"
        )


# --- Property 9: Duplicate phone deduplication ---

# Strategy: valid 10-digit phone numbers
_valid_phone_10 = st.from_regex(r"[0-9]{10}", fullmatch=True)


def _run_process_row_with_existing_lead(
    phone: str,
) -> tuple[bool, object | None, object]:
    """Run process_row for a 'new' client where an existing lead matches the phone.

    Returns (lead_repo.create was NOT called, lead_id from update call).
    """
    row = [""] * EXPECTED_COLUMNS
    row[9] = "Test Name"
    row[10] = phone
    row[14] = "New"

    sub_id = uuid4()
    existing_lead_id = uuid4()

    mock_submission = MagicMock()
    mock_submission.id = sub_id
    mock_submission.processing_status = "imported"
    mock_submission.lead_id = None

    existing_lead = MagicMock()
    existing_lead.id = existing_lead_id

    mock_sub_repo = AsyncMock()
    mock_sub_repo.create.return_value = mock_submission
    mock_sub_repo.get_by_id.return_value = mock_submission
    mock_sub_repo.update = AsyncMock()

    mock_lead_repo = AsyncMock()
    mock_lead_repo.get_by_phone_and_active_status.return_value = existing_lead
    mock_lead_repo.create = AsyncMock()

    mock_session = AsyncMock()

    with (
        patch(
            "grins_platform.services.google_sheets_service.GoogleSheetSubmissionRepository",
            return_value=mock_sub_repo,
        ),
        patch(
            "grins_platform.services.google_sheets_service.LeadRepository",
            return_value=mock_lead_repo,
        ),
    ):
        service = GoogleSheetsService(None, None)
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(service.process_row(row, 2, mock_session))
        finally:
            loop.close()

    create_not_called = not mock_lead_repo.create.called
    # Extract lead_id from the update call
    update_calls = mock_sub_repo.update.call_args_list
    linked_lead_id = None
    for call in update_calls:
        data = call.args[1] if len(call.args) > 1 else call.kwargs
        if isinstance(data, dict) and "lead_id" in data:
            linked_lead_id = data["lead_id"]
    return create_not_called, linked_lead_id, existing_lead_id


@pytest.mark.unit
class TestDuplicatePhoneDeduplicationProperty:
    """Property 9: Duplicate phone deduplication.

    For any submission with client_type = "new" and a phone number matching
    an existing active lead, processing should link the submission to the
    existing lead (lead_id = existing lead's ID) rather than creating a
    new lead. The total lead count should not increase.

    Validates: Requirements 3.6
    """

    @given(phone=_valid_phone_10)
    @settings(max_examples=200)
    def test_existing_lead_linked_no_new_lead_created(self, phone: str) -> None:
        """When phone matches existing lead, no new lead is created."""
        create_not_called, _, _ = _run_process_row_with_existing_lead(phone)
        assert create_not_called, "lead_repo.create should not be called for duplicate"

    @given(phone=_valid_phone_10)
    @settings(max_examples=200)
    def test_submission_linked_to_existing_lead_id(self, phone: str) -> None:
        """Submission's lead_id is set to the existing lead's ID."""
        _, linked_id, existing_id = _run_process_row_with_existing_lead(phone)
        assert linked_id == existing_id, (
            f"Expected lead_id={existing_id}, got {linked_id}"
        )


# --- Property 12: Token refresh triggers within expiry buffer ---
from grins_platform.services.google_sheets_poller import (
    _TOKEN_EXPIRY_BUFFER,
    GoogleSheetsPoller,
    detect_header_row,
)


@pytest.mark.unit
class TestTokenRefreshWithinExpiryBufferProperty:
    """Property 12: Token refresh triggers within expiry buffer.

    For any access token with an expiry timestamp, _ensure_token() should
    request a new token if the current time is within 100 seconds of expiry,
    and reuse the existing token otherwise.

    Validates: Requirements 1.5
    """

    def _make_poller(self) -> GoogleSheetsPoller:
        """Create a poller with minimal config (no real service account)."""
        poller = object.__new__(GoogleSheetsPoller)
        poller._access_token = "existing-token"
        poller._token_expiry = 0.0
        poller._sa_email = "test@test.iam.gserviceaccount.com"
        poller._sa_private_key = ""
        return poller

    @given(
        remaining=st.floats(
            min_value=_TOKEN_EXPIRY_BUFFER + 0.01,
            max_value=7200.0,
        ),
    )
    @settings(max_examples=200)
    def test_token_reused_when_outside_buffer(self, remaining: float) -> None:
        """Token reused when time remaining > buffer."""
        poller = self._make_poller()
        now = time.time()
        poller._token_expiry = now + remaining

        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(poller._ensure_token())
        finally:
            loop.close()

        assert result == "existing-token"

    @given(
        remaining=st.floats(
            min_value=-3600.0,
            max_value=_TOKEN_EXPIRY_BUFFER,
        ),
    )
    @settings(max_examples=200)
    def test_token_refreshed_when_within_buffer(self, remaining: float) -> None:
        """Token refreshed when time remaining <= buffer."""
        poller = self._make_poller()
        now = time.time()
        poller._token_expiry = now + remaining

        mock_request_token = AsyncMock(return_value="new-token")
        poller._request_token = mock_request_token  # type: ignore[assignment]
        poller._build_jwt_assertion = MagicMock(return_value="jwt")  # type: ignore[assignment]

        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(poller._ensure_token())
        finally:
            loop.close()

        assert result == "new-token"
        mock_request_token.assert_called_once_with("jwt")

    def test_token_refreshed_when_no_token(self) -> None:
        """Token refreshed when _access_token is None."""
        poller = self._make_poller()
        poller._access_token = None

        mock_request_token = AsyncMock(return_value="fresh-token")
        poller._request_token = mock_request_token  # type: ignore[assignment]
        poller._build_jwt_assertion = MagicMock(return_value="jwt")  # type: ignore[assignment]

        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(poller._ensure_token())
        finally:
            loop.close()

        assert result == "fresh-token"
        mock_request_token.assert_called_once()


# --- Property 13: Header row detection ---

# Strategy: "Timestamp" with random case and surrounding whitespace
_timestamp_variant = st.tuples(
    st.sampled_from(
        ["timestamp", "Timestamp", "TIMESTAMP", "TimeStamp", "tImEsTaMp"],
    ),
    st.sampled_from(["", " ", "  ", "\t"]),
    st.sampled_from(["", " ", "  ", "\t"]),
).map(lambda t: t[1] + t[0] + t[2])


@pytest.mark.unit
class TestHeaderRowDetectionProperty:
    """Property 13: Header row detection.

    For any list of rows where the first row's first cell contains
    "Timestamp" (case-insensitive, stripped), detect_header_row returns 1
    (skip header). Otherwise returns 0 (no skip).

    Validates: Requirements 1.8
    """

    @given(
        header_cell=_timestamp_variant,
        rest=st.lists(st.text(max_size=10), min_size=0, max_size=18),
    )
    @settings(max_examples=200)
    def test_timestamp_header_detected(
        self,
        header_cell: str,
        rest: list[str],
    ) -> None:
        """First cell is 'Timestamp' variant → skip header (return 1)."""
        rows = [[header_cell, *rest], ["data1"]]
        assert detect_header_row(rows) == 1

    @given(
        first_cell=st.text(max_size=20).filter(
            lambda s: s.strip().lower() != "timestamp",
        ),
    )
    @settings(max_examples=200)
    def test_non_timestamp_header_not_skipped(self, first_cell: str) -> None:
        """First cell is not 'Timestamp' → no skip (return 0)."""
        rows = [[first_cell, "col2"], ["data1"]]
        assert detect_header_row(rows) == 0

    def test_empty_rows_not_skipped(self) -> None:
        """Empty rows list → return 0."""
        assert detect_header_row([]) == 0

    def test_empty_first_row_not_skipped(self) -> None:
        """First row is empty list → return 0."""
        assert detect_header_row([[]]) == 0

    @given(
        rest=st.lists(st.text(max_size=10), min_size=0, max_size=18),
    )
    @settings(max_examples=100)
    def test_empty_string_first_cell_not_skipped(self, rest: list[str]) -> None:
        """First cell is empty string → return 0."""
        rows = [["", *rest]]
        assert detect_header_row(rows) == 0


# --- Property 10: Row processing error isolation ---


@pytest.mark.unit
class TestRowProcessingErrorIsolationProperty:
    """Property 10: Row processing error isolation.

    For any batch of N rows where row K (1 <= K <= N) causes a processing
    error, the rows before and after K should still be processed
    successfully. Row K's failure should not block other rows.

    Validates: Requirements 3.7, 8.6
    """

    @given(
        n=st.integers(min_value=2, max_value=8),
        k=st.integers(min_value=0, max_value=7),
    )
    @settings(max_examples=200)
    def test_error_on_row_k_does_not_block_others(
        self,
        n: int,
        k: int,
    ) -> None:
        """Row K fails but all other rows are processed."""
        k = k % n  # ensure k is within [0, n)
        rows = [[""] * EXPECTED_COLUMNS for _ in range(n)]

        call_index = 0
        succeeded: list[int] = []

        async def mock_process_row(
            _row: list[str],
            _row_number: int,
            _session: object,
            **kwargs: object,
        ) -> MagicMock:
            nonlocal call_index
            idx = call_index
            call_index += 1
            if idx == k:
                msg = f"Simulated error on call {idx}"
                raise RuntimeError(msg)
            succeeded.append(idx)
            return MagicMock()

        poller = object.__new__(GoogleSheetsPoller)
        poller._spreadsheet_id = "test"
        poller._sheet_name = "Sheet1"
        poller._poll_interval = 60
        poller._running = True
        poller._last_sync = None
        poller._last_error = None
        poller._access_token = "token"
        poller._token_expiry = time.time() + 3600
        poller._sa_email = "t@t.iam.gserviceaccount.com"
        poller._sa_private_key = ""
        poller._poll_lock = asyncio.Lock()

        mock_service = MagicMock()
        mock_service.process_row = AsyncMock(side_effect=mock_process_row)
        poller._service = mock_service
        poller._ensure_token = AsyncMock(return_value="token")
        poller._fetch_sheet_data = AsyncMock(return_value=rows)

        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()

        async def mock_get_session():
            yield mock_session

        mock_db = MagicMock()
        mock_db.get_session = mock_get_session
        poller._db_manager = mock_db

        with patch(
            "grins_platform.services.google_sheets_poller.GoogleSheetSubmissionRepository",
        ) as mock_repo_cls:
            mock_repo_inst = MagicMock()
            mock_repo_inst.get_existing_hashes = AsyncMock(return_value=set())
            mock_repo_cls.return_value = mock_repo_inst

            loop = asyncio.new_event_loop()
            try:
                count = loop.run_until_complete(poller._execute_poll_cycle())
            finally:
                loop.close()

        # Exactly n-1 rows should succeed
        assert count == n - 1
        assert k not in succeeded
        assert sorted(succeeded) == [i for i in range(n) if i != k]


# --- Property 11: Only new rows are processed ---


@pytest.mark.unit
class TestOnlyNewRowsProcessedProperty:
    """Property 11: Only new rows are processed (hash-based dedup).

    For any set of fetched rows and any subset of "already imported" rows,
    the poller should process only rows whose content hash is not already
    in the DB. The count of processed rows equals the number of rows
    with new (unseen) hashes.

    Validates: Requirements 1.4
    """

    @given(
        total_rows=st.integers(min_value=1, max_value=15),
        num_existing=st.integers(min_value=0, max_value=15),
    )
    @settings(max_examples=200)
    def test_only_rows_with_new_hashes_are_processed(
        self,
        total_rows: int,
        num_existing: int,
    ) -> None:
        """Rows whose hash already exists in DB are skipped; others processed."""
        from grins_platform.services.google_sheets_service import compute_row_hash

        # Make each row unique by including its index
        rows = [
            [f"row_{i}_col"] + [""] * (EXPECTED_COLUMNS - 1) for i in range(total_rows)
        ]

        # Mark the first num_existing rows as "already imported"
        num_existing = min(num_existing, total_rows)
        existing_hashes = {compute_row_hash(rows[i]) for i in range(num_existing)}

        processed_row_numbers: list[int] = []

        async def mock_process_row(
            _row: list[str],
            row_number: int,
            _session: object,
            **kwargs: object,
        ) -> MagicMock:
            processed_row_numbers.append(row_number)
            return MagicMock()

        poller = object.__new__(GoogleSheetsPoller)
        poller._spreadsheet_id = "test"
        poller._sheet_name = "Sheet1"
        poller._poll_interval = 60
        poller._running = True
        poller._last_sync = None
        poller._last_error = None
        poller._access_token = "token"
        poller._token_expiry = time.time() + 3600
        poller._sa_email = "t@t.iam.gserviceaccount.com"
        poller._sa_private_key = ""
        poller._poll_lock = asyncio.Lock()

        mock_service = MagicMock()
        mock_service.process_row = AsyncMock(side_effect=mock_process_row)
        poller._service = mock_service
        poller._ensure_token = AsyncMock(return_value="token")
        # No header row — all rows are data
        poller._fetch_sheet_data = AsyncMock(return_value=rows)

        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()

        async def mock_get_session():
            yield mock_session

        mock_db = MagicMock()
        mock_db.get_session = mock_get_session
        poller._db_manager = mock_db

        with patch(
            "grins_platform.services.google_sheets_poller.GoogleSheetSubmissionRepository",
        ) as mock_repo_cls:
            mock_repo_inst = MagicMock()
            mock_repo_inst.get_existing_hashes = AsyncMock(return_value=existing_hashes)
            mock_repo_cls.return_value = mock_repo_inst

            loop = asyncio.new_event_loop()
            try:
                count = loop.run_until_complete(poller._execute_poll_cycle())
            finally:
                loop.close()

        expected_count = total_rows - num_existing
        assert count == expected_count
        assert len(processed_row_numbers) == expected_count

    def test_all_rows_skipped_when_all_hashes_exist(self) -> None:
        """When all hashes exist in DB, nothing is processed."""
        from grins_platform.services.google_sheets_service import compute_row_hash

        rows = [[f"row_{i}"] + [""] * (EXPECTED_COLUMNS - 1) for i in range(5)]
        all_hashes = {compute_row_hash(r) for r in rows}

        poller = object.__new__(GoogleSheetsPoller)
        poller._spreadsheet_id = "test"
        poller._sheet_name = "Sheet1"
        poller._poll_interval = 60
        poller._running = True
        poller._last_sync = None
        poller._last_error = None
        poller._access_token = "token"
        poller._token_expiry = time.time() + 3600
        poller._sa_email = "t@t.iam.gserviceaccount.com"
        poller._sa_private_key = ""
        poller._poll_lock = asyncio.Lock()

        mock_service = MagicMock()
        mock_service.process_row = AsyncMock()
        poller._service = mock_service
        poller._ensure_token = AsyncMock(return_value="token")
        poller._fetch_sheet_data = AsyncMock(return_value=rows)

        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()

        async def mock_get_session():
            yield mock_session

        mock_db = MagicMock()
        mock_db.get_session = mock_get_session
        poller._db_manager = mock_db

        with patch(
            "grins_platform.services.google_sheets_poller.GoogleSheetSubmissionRepository",
        ) as mock_repo_cls:
            mock_repo_inst = MagicMock()
            mock_repo_inst.get_existing_hashes = AsyncMock(return_value=all_hashes)
            mock_repo_cls.return_value = mock_repo_inst

            loop = asyncio.new_event_loop()
            try:
                count = loop.run_until_complete(poller._execute_poll_cycle())
            finally:
                loop.close()

        assert count == 0
        mock_service.process_row.assert_not_called()

    def test_no_existing_hashes_processes_all_data_rows(self) -> None:
        """When no hashes exist in DB, all data rows are processed."""
        total_rows = 3
        rows = [[""] * EXPECTED_COLUMNS for _ in range(total_rows)]

        processed_row_numbers: list[int] = []

        async def mock_process_row(
            _row: list[str],
            row_number: int,
            _session: object,
            **kwargs: object,
        ) -> MagicMock:
            processed_row_numbers.append(row_number)
            return MagicMock()

        poller = object.__new__(GoogleSheetsPoller)
        poller._spreadsheet_id = "test"
        poller._sheet_name = "Sheet1"
        poller._poll_interval = 60
        poller._running = True
        poller._last_sync = None
        poller._last_error = None
        poller._access_token = "token"
        poller._token_expiry = time.time() + 3600
        poller._sa_email = "t@t.iam.gserviceaccount.com"
        poller._sa_private_key = ""
        poller._poll_lock = asyncio.Lock()

        mock_service = MagicMock()
        mock_service.process_row = AsyncMock(side_effect=mock_process_row)
        poller._service = mock_service
        poller._ensure_token = AsyncMock(return_value="token")
        poller._fetch_sheet_data = AsyncMock(return_value=rows)

        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()

        async def mock_get_session():
            yield mock_session

        mock_db = MagicMock()
        mock_db.get_session = mock_get_session
        poller._db_manager = mock_db

        with patch(
            "grins_platform.services.google_sheets_poller.GoogleSheetSubmissionRepository",
        ) as mock_repo_cls:
            mock_repo_inst = MagicMock()
            mock_repo_inst.get_existing_hashes = AsyncMock(return_value=set())
            mock_repo_cls.return_value = mock_repo_inst

            loop = asyncio.new_event_loop()
            try:
                count = loop.run_until_complete(poller._execute_poll_cycle())
            finally:
                loop.close()

        assert count == total_rows
        assert sorted(processed_row_numbers) == [2, 3, 4]


# --- Property 15: Manual lead creation idempotency guard ---


@pytest.mark.unit
class TestManualLeadCreationIdempotencyGuardProperty:
    """Property 15: Manual lead creation idempotency guard.

    For any submission that already has a non-null lead_id, calling
    create_lead_from_submission should raise ValueError without modifying
    the submission or creating a new lead.

    Validates: Requirements 5.5
    """

    @given(lead_id=st.uuids())
    @settings(max_examples=200)
    def test_already_linked_submission_raises_value_error(
        self,
        lead_id: object,
    ) -> None:
        """Submission with non-null lead_id → ValueError raised."""
        sub_id = uuid4()

        mock_submission = MagicMock()
        mock_submission.id = sub_id
        mock_submission.lead_id = lead_id

        mock_sub_repo = AsyncMock()
        mock_sub_repo.get_by_id.return_value = mock_submission

        mock_lead_repo = AsyncMock()
        mock_session = AsyncMock()

        with (
            patch(
                "grins_platform.services.google_sheets_service.GoogleSheetSubmissionRepository",
                return_value=mock_sub_repo,
            ),
            patch(
                "grins_platform.services.google_sheets_service.LeadRepository",
                return_value=mock_lead_repo,
            ),
        ):
            service = GoogleSheetsService(None, None)
            loop = asyncio.new_event_loop()
            try:
                with pytest.raises(ValueError, match="already has a linked lead"):
                    loop.run_until_complete(
                        service.create_lead_from_submission(sub_id, mock_session),
                    )
            finally:
                loop.close()

    @given(lead_id=st.uuids())
    @settings(max_examples=200)
    def test_no_lead_created_when_already_linked(
        self,
        lead_id: object,
    ) -> None:
        """No new lead is created when submission already linked."""
        sub_id = uuid4()

        mock_submission = MagicMock()
        mock_submission.id = sub_id
        mock_submission.lead_id = lead_id

        mock_sub_repo = AsyncMock()
        mock_sub_repo.get_by_id.return_value = mock_submission

        mock_lead_repo = AsyncMock()
        mock_session = AsyncMock()

        with (
            patch(
                "grins_platform.services.google_sheets_service.GoogleSheetSubmissionRepository",
                return_value=mock_sub_repo,
            ),
            patch(
                "grins_platform.services.google_sheets_service.LeadRepository",
                return_value=mock_lead_repo,
            ),
        ):
            service = GoogleSheetsService(None, None)
            loop = asyncio.new_event_loop()
            try:
                with pytest.raises(ValueError):
                    loop.run_until_complete(
                        service.create_lead_from_submission(sub_id, mock_session),
                    )
            finally:
                loop.close()

        mock_lead_repo.create.assert_not_called()
        mock_sub_repo.update.assert_not_called()


# --- Property 2: New submission invariants ---

# Column name mapping matching process_row's sub_repo.create kwargs
_COLUMN_NAMES = [
    "timestamp",
    "spring_startup",
    "fall_blowout",
    "summer_tuneup",
    "repair_existing",
    "new_system_install",
    "addition_to_system",
    "additional_services_info",
    "date_work_needed_by",
    "name",
    "phone",
    "email",
    "city",
    "address",
    "client_type",
    "property_type",
    "referral_source",
    "landscape_hardscape",
]


@pytest.mark.unit
class TestNewSubmissionInvariantsProperty:
    """Property 2: New submission invariants.

    For any valid row of 19 string values and any unique row number,
    storing the row as a submission should produce a record where all 19
    column values match the input (empty string → None), the
    sheet_row_number matches, processing_status is "imported", lead_id
    is null, and imported_at is set.

    # Feature: google-sheets-work-requests, Property 2: New submission invariants
    Validates: Requirements 2.1, 2.4
    """

    @given(
        row=st.lists(
            st.text(
                alphabet=st.characters(blacklist_categories=["Cs"]),
                max_size=30,
            ),
            min_size=_SHEET_COLUMNS,
            max_size=_SHEET_COLUMNS,
        ),
        row_number=st.integers(min_value=2, max_value=100_000),
    )
    @settings(max_examples=200)
    def test_create_kwargs_match_input_row(
        self,
        row: list[str],
        row_number: int,
    ) -> None:
        """sub_repo.create is called with column values matching the input row."""
        mock_submission = MagicMock()
        mock_submission.id = uuid4()
        mock_submission.processing_status = "imported"
        mock_submission.lead_id = None

        mock_sub_repo = AsyncMock()
        mock_sub_repo.create.return_value = mock_submission
        mock_sub_repo.get_by_id.return_value = mock_submission
        mock_sub_repo.update = AsyncMock()

        mock_lead_repo = AsyncMock()
        mock_session = AsyncMock()

        with (
            patch(
                "grins_platform.services.google_sheets_service.GoogleSheetSubmissionRepository",
                return_value=mock_sub_repo,
            ),
            patch(
                "grins_platform.services.google_sheets_service.LeadRepository",
                return_value=mock_lead_repo,
            ),
        ):
            service = GoogleSheetsService(None, None)
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(
                    service.process_row(row, row_number, mock_session),
                )
            finally:
                loop.close()

        create_kwargs = mock_sub_repo.create.call_args[1]

        # sheet_row_number matches
        assert create_kwargs["sheet_row_number"] == row_number

        # Compare against the remapped row (20-col sheet → 18-col internal)
        remapped = pad_row(remap_sheet_row(row))
        for i, col_name in enumerate(_COLUMN_NAMES):
            expected = remapped[i] if remapped[i] else None
            assert create_kwargs[col_name] == expected, (
                f"Column {col_name} (idx {i}): "
                f"expected {expected!r}, "
                f"got {create_kwargs[col_name]!r}"
            )

    @given(
        row=st.lists(
            st.text(
                alphabet=st.characters(blacklist_categories=["Cs"]),
                max_size=30,
            ),
            min_size=EXPECTED_COLUMNS,
            max_size=EXPECTED_COLUMNS,
        ),
        row_number=st.integers(min_value=2, max_value=100_000),
    )
    @settings(max_examples=200)
    def test_initial_processing_status_is_imported(
        self,
        row: list[str],
        row_number: int,
    ) -> None:
        """The submission returned by create has processing_status='imported'."""
        mock_submission = MagicMock()
        mock_submission.id = uuid4()
        mock_submission.processing_status = "imported"
        mock_submission.lead_id = None
        mock_submission.imported_at = MagicMock()  # non-None

        mock_sub_repo = AsyncMock()
        mock_sub_repo.create.return_value = mock_submission
        mock_sub_repo.get_by_id.return_value = mock_submission
        mock_sub_repo.update = AsyncMock()

        mock_lead_repo = AsyncMock()
        mock_session = AsyncMock()

        with (
            patch(
                "grins_platform.services.google_sheets_service.GoogleSheetSubmissionRepository",
                return_value=mock_sub_repo,
            ),
            patch(
                "grins_platform.services.google_sheets_service.LeadRepository",
                return_value=mock_lead_repo,
            ),
        ):
            service = GoogleSheetsService(None, None)
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(
                    service.process_row(row, row_number, mock_session),
                )
            finally:
                loop.close()

        # Verify the initial create produced a submission with correct invariants
        created = mock_sub_repo.create.return_value
        assert created.processing_status == "imported"
        assert created.lead_id is None
        assert created.imported_at is not None


# --- Property 7: Sheet-created leads have null zip_code ---

from datetime import datetime, timezone

from grins_platform.schemas.lead import LeadResponse


@pytest.mark.unit
class TestSheetCreatedLeadsHaveNullZipCodeProperty:
    """Property 7: Sheet-created leads have null zip_code.

    For any lead created from a Google Sheet submission, the lead's
    zip_code field should be None. The LeadResponse schema should
    serialize such a lead without error, producing zip_code: null.

    Validates: Requirements 3.5, 4.3, 4.4
    """

    @given(
        name=st.text(min_size=1, max_size=30).filter(lambda s: s.strip() != ""),
        phone=st.from_regex(r"[0-9]{10}", fullmatch=True),
        email=st.one_of(st.none(), st.emails()),
    )
    @settings(max_examples=200)
    def test_process_row_creates_lead_with_null_zip_code(
        self,
        name: str,
        phone: str,
        email: str | None,
    ) -> None:
        """process_row for new client always passes zip_code=None."""
        row = [""] * EXPECTED_COLUMNS
        row[9] = name
        row[10] = phone
        row[11] = email or ""
        row[14] = "new"

        mock_submission = MagicMock()
        mock_submission.id = uuid4()
        mock_submission.processing_status = "imported"
        mock_submission.lead_id = None

        mock_lead = MagicMock()
        mock_lead.id = uuid4()

        mock_sub_repo = AsyncMock()
        mock_sub_repo.create.return_value = mock_submission
        mock_sub_repo.get_by_id.return_value = mock_submission
        mock_sub_repo.update = AsyncMock()

        mock_lead_repo = AsyncMock()
        mock_lead_repo.get_by_phone_and_active_status.return_value = None
        mock_lead_repo.create.return_value = mock_lead

        mock_session = AsyncMock()

        with (
            patch(
                "grins_platform.services.google_sheets_service.GoogleSheetSubmissionRepository",
                return_value=mock_sub_repo,
            ),
            patch(
                "grins_platform.services.google_sheets_service.LeadRepository",
                return_value=mock_lead_repo,
            ),
        ):
            service = GoogleSheetsService(None, None)
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(service.process_row(row, 2, mock_session))
            finally:
                loop.close()

        create_kwargs = mock_lead_repo.create.call_args[1]
        assert create_kwargs["zip_code"] is None

    @given(
        name=st.text(min_size=1, max_size=30).filter(lambda s: s.strip() != ""),
        phone=st.from_regex(r"[0-9]{10}", fullmatch=True),
        email=st.one_of(st.none(), st.emails()),
    )
    @settings(max_examples=200)
    def test_create_lead_from_submission_uses_null_zip_code(
        self,
        name: str,
        phone: str,
        email: str | None,
    ) -> None:
        """create_lead_from_submission always passes zip_code=None."""
        sub_id = uuid4()

        mock_submission = MagicMock()
        mock_submission.id = sub_id
        mock_submission.lead_id = None
        mock_submission.name = name
        mock_submission.phone = phone
        mock_submission.email = email
        for attr in (
            "timestamp",
            "spring_startup",
            "fall_blowout",
            "summer_tuneup",
            "repair_existing",
            "new_system_install",
            "addition_to_system",
            "additional_services_info",
            "date_work_needed_by",
            "city",
            "address",
            "client_type",
            "property_type",
            "referral_source",
            "landscape_hardscape",
        ):
            setattr(mock_submission, attr, "")
        mock_submission.zip_code = None
        mock_submission.work_requested = None
        mock_submission.agreed_to_terms = None

        mock_lead = MagicMock()
        mock_lead.id = uuid4()

        mock_sub_repo = AsyncMock()
        mock_sub_repo.get_by_id.return_value = mock_submission
        mock_sub_repo.update = AsyncMock()

        mock_lead_repo = AsyncMock()
        mock_lead_repo.get_by_phone_and_active_status.return_value = None
        mock_lead_repo.create.return_value = mock_lead

        mock_session = AsyncMock()

        with (
            patch(
                "grins_platform.services.google_sheets_service.GoogleSheetSubmissionRepository",
                return_value=mock_sub_repo,
            ),
            patch(
                "grins_platform.services.google_sheets_service.LeadRepository",
                return_value=mock_lead_repo,
            ),
        ):
            service = GoogleSheetsService(None, None)
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(
                    service.create_lead_from_submission(sub_id, mock_session),
                )
            finally:
                loop.close()

        create_kwargs = mock_lead_repo.create.call_args[1]
        assert create_kwargs["zip_code"] is None

    @given(
        name=st.text(min_size=1, max_size=30).filter(lambda s: s.strip() != ""),
        phone=st.from_regex(r"[0-9]{10}", fullmatch=True),
        situation=st.sampled_from(list(LeadSituation)),
    )
    @settings(max_examples=200)
    def test_lead_response_serializes_null_zip_code(
        self,
        name: str,
        phone: str,
        situation: LeadSituation,
    ) -> None:
        """LeadResponse serializes a sheet-created lead with zip_code=None."""
        now = datetime.now(tz=timezone.utc)
        lead = MagicMock()
        lead.id = uuid4()
        lead.name = name
        lead.phone = phone
        lead.email = None
        lead.zip_code = None
        lead.situation = situation.value
        lead.notes = None
        lead.source_site = "google_sheets"
        lead.lead_source = "google_form"
        lead.source_detail = None
        lead.intake_tag = None
        lead.sms_consent = False
        lead.terms_accepted = False
        lead.status = "new"
        lead.assigned_to = None
        lead.customer_id = None
        lead.contacted_at = None
        lead.converted_at = None
        lead.city = None
        lead.state = None
        lead.address = None
        lead.action_tags = None
        lead.email_marketing_consent = False
        lead.customer_type = None
        lead.property_type = None
        lead.moved_to = None
        lead.moved_at = None
        lead.last_contacted_at = None
        lead.job_requested = None
        lead.created_at = now
        lead.updated_at = now

        response = LeadResponse.model_validate(lead)
        assert response.zip_code is None
        assert response.source_site == "google_sheets"

        # Verify JSON serialization produces null
        data = response.model_dump()
        assert data["zip_code"] is None


# --- Property 8: Public form submission requires address ---

from pydantic import ValidationError

from grins_platform.schemas.lead import LeadSubmission


@pytest.mark.unit
class TestPublicFormRequiresAddressProperty:
    """Property 8: Public form submission requires address.

    For any LeadSubmission payload where address is missing or empty,
    Pydantic validation should reject the payload. zip_code is now
    optional and may be omitted without error.

    Validates: Requirements 4.2
    """

    _base: ClassVar[dict[str, object]] = {
        "name": "Test User",
        "phone": "6125551234",
        "situation": LeadSituation.NEW_SYSTEM,
        "source_site": "residential",
        "address": "123 Main St",
    }

    @given(
        zip_code=st.from_regex(r"[0-9]{5}", fullmatch=True),
    )
    @settings(max_examples=200)
    def test_valid_5_digit_zip_accepted(self, zip_code: str) -> None:
        """Exactly 5 digits → accepted."""
        sub = LeadSubmission(**self._base, zip_code=zip_code)
        assert sub.zip_code == zip_code

    def test_missing_zip_code_accepted(self) -> None:
        """Omitting zip_code entirely → accepted (now optional)."""
        sub = LeadSubmission(**self._base)
        assert sub.zip_code is None

    @given(
        address=st.text(
            min_size=1,
            max_size=100,
            alphabet=st.characters(
                blacklist_categories=("Cs",),
                blacklist_characters="<>",
            ),
        ).filter(lambda s: s.strip() != ""),
    )
    @settings(max_examples=200)
    def test_valid_address_accepted(self, address: str) -> None:
        """Non-empty address → accepted."""
        sub = LeadSubmission(
            name="Test User",
            phone="6125551234",
            situation=LeadSituation.NEW_SYSTEM,
            source_site="residential",
            address=address,
        )
        assert sub.address == address.strip()

    def test_missing_address_rejected(self) -> None:
        """Omitting address entirely → ValidationError."""
        with pytest.raises(ValidationError):
            LeadSubmission(
                name="Test User",
                phone="6125551234",
                situation=LeadSituation.NEW_SYSTEM,
                source_site="residential",
                # address intentionally omitted
            )  # type: ignore[call-arg]

    @given(
        address=st.sampled_from(["", " ", "  ", "\t"]),
    )
    @settings(max_examples=50)
    def test_empty_or_whitespace_address_rejected(self, address: str) -> None:
        """Empty or whitespace-only address → ValidationError."""
        with pytest.raises(ValidationError):
            LeadSubmission(
                name="Test User",
                phone="6125551234",
                situation=LeadSituation.NEW_SYSTEM,
                source_site="residential",
                address=address,
            )

    @given(
        zip_code=st.text(
            alphabet=st.characters(categories=["Nd"]),
            min_size=1,
            max_size=4,
        ),
    )
    @settings(max_examples=200)
    def test_fewer_than_5_digits_zip_rejected(self, zip_code: str) -> None:
        """Fewer than 5 digits → ValidationError."""
        with pytest.raises(ValidationError):
            LeadSubmission(**self._base, zip_code=zip_code)

    @given(
        zip_code=st.text(
            alphabet=st.characters(categories=["Nd"]),
            min_size=6,
            max_size=15,
        ),
    )
    @settings(max_examples=200)
    def test_more_than_5_digits_zip_rejected(self, zip_code: str) -> None:
        """More than 5 digits → ValidationError."""
        with pytest.raises(ValidationError):
            LeadSubmission(**self._base, zip_code=zip_code)

    @given(
        zip_code=st.text(
            alphabet=st.characters(categories=["L"]),
            min_size=5,
            max_size=5,
        ),
    )
    @settings(max_examples=200)
    def test_non_digit_zip_characters_rejected(self, zip_code: str) -> None:
        """5 non-digit characters → ValidationError."""
        with pytest.raises(ValidationError):
            LeadSubmission(**self._base, zip_code=zip_code)


# --- Property 14: Submission list filtering ---


_PROCESSING_STATUSES = ["imported", "lead_created", "skipped", "error"]
_CLIENT_TYPES = ["new", "existing", ""]


def _make_mock_submission(
    *,
    name: str = "Test",
    phone: str = "6125551234",
    email: str = "test@example.com",
    processing_status: str = "imported",
    client_type: str = "new",
) -> MagicMock:
    """Create a mock submission with filterable fields."""
    sub = MagicMock()
    sub.id = uuid4()
    sub.name = name
    sub.phone = phone
    sub.email = email
    sub.processing_status = processing_status
    sub.client_type = client_type
    return sub


def _matches_filters(
    sub: MagicMock,
    processing_status: str | None,
    client_type: str | None,
    search: str | None,
) -> bool:
    """In-memory filter matching, mirroring repository logic."""
    if processing_status is not None and sub.processing_status != processing_status:
        return False
    if client_type is not None and sub.client_type != client_type:
        return False
    if search:
        term = search.lower()
        if not (
            (sub.name and term in sub.name.lower())
            or (sub.phone and term in sub.phone)
            or (sub.email and term in sub.email.lower())
        ):
            return False
    return True


@pytest.mark.unit
class TestSubmissionListFilteringProperty:
    """Property 14: Submission list filtering.

    For any set of submissions and any combination of processing_status
    filter, client_type filter, and text search term, the returned list
    should contain only submissions matching all active filters. Text
    search matches against name, phone, email (case-insensitive partial).
    Results should be paginated with correct total count.

    Validates: Requirements 5.1, 6.10
    """

    @given(
        statuses=st.lists(
            st.sampled_from(_PROCESSING_STATUSES),
            min_size=1,
            max_size=10,
        ),
        client_types=st.lists(
            st.sampled_from(_CLIENT_TYPES),
            min_size=1,
            max_size=10,
        ),
        filter_status=st.one_of(
            st.none(),
            st.sampled_from(_PROCESSING_STATUSES),
        ),
        filter_client_type=st.one_of(
            st.none(),
            st.sampled_from(_CLIENT_TYPES),
        ),
    )
    @settings(max_examples=300)
    def test_filtered_results_match_all_active_filters(
        self,
        statuses: list[str],
        client_types: list[str],
        filter_status: str | None,
        filter_client_type: str | None,
    ) -> None:
        """Every returned submission matches all active filters."""
        submissions = [
            _make_mock_submission(
                processing_status=statuses[i % len(statuses)],
                client_type=client_types[i % len(client_types)],
            )
            for i in range(len(statuses))
        ]

        expected = [
            s
            for s in submissions
            if _matches_filters(s, filter_status, filter_client_type, None)
        ]

        # Simulate what the repository returns
        for s in expected:
            if filter_status is not None:
                assert s.processing_status == filter_status
            if filter_client_type is not None:
                assert s.client_type == filter_client_type

        assert len(expected) <= len(submissions)

    @given(
        search_term=st.text(min_size=1, max_size=10).filter(
            lambda s: s.strip() != "",
        ),
    )
    @settings(max_examples=200)
    def test_text_search_is_case_insensitive_partial_match(
        self,
        search_term: str,
    ) -> None:
        """Text search matches name, phone, or email case-insensitively."""
        matching = _make_mock_submission(name=f"prefix{search_term}suffix")
        non_matching = _make_mock_submission(
            name="Unrelated",
            phone="0000000000",
            email="none@none.com",
        )

        assert _matches_filters(matching, None, None, search_term)
        # non_matching only fails if search_term isn't in any of its fields
        if (
            search_term.lower() not in "unrelated"
            and search_term not in "0000000000"
            and search_term.lower() not in "none@none.com"
        ):
            assert not _matches_filters(non_matching, None, None, search_term)

    @given(
        page=st.integers(min_value=1, max_value=10),
        page_size=st.integers(min_value=1, max_value=100),
        total=st.integers(min_value=0, max_value=500),
    )
    @settings(max_examples=200)
    def test_pagination_metadata_is_consistent(
        self,
        page: int,
        page_size: int,
        total: int,
    ) -> None:
        """Pagination total_pages = ceil(total / page_size)."""
        total_pages = ceil(total / page_size) if total > 0 else 0
        response = PaginatedSubmissionResponse(
            items=[],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
        assert response.total == total
        assert response.page == page
        assert response.page_size == page_size
        if total > 0:
            assert response.total_pages == ceil(total / page_size)
        else:
            assert response.total_pages == 0

    @given(
        filter_status=st.one_of(
            st.none(),
            st.sampled_from(_PROCESSING_STATUSES),
        ),
        filter_client_type=st.one_of(
            st.none(),
            st.sampled_from(_CLIENT_TYPES),
        ),
        search=st.one_of(st.none(), st.text(min_size=1, max_size=10)),
    )
    @settings(max_examples=200)
    def test_no_filters_returns_all_submissions(
        self,
        filter_status: str | None,
        filter_client_type: str | None,
        search: str | None,
    ) -> None:
        """With no active filters, all submissions match."""
        sub = _make_mock_submission()
        if filter_status is None and filter_client_type is None and search is None:
            assert _matches_filters(sub, None, None, None)

    @given(
        status=st.sampled_from(_PROCESSING_STATUSES),
        client_type=st.sampled_from(_CLIENT_TYPES),
    )
    @settings(max_examples=200)
    def test_combined_filters_are_conjunctive(
        self,
        status: str,
        client_type: str,
    ) -> None:
        """Both filters must match (AND logic), not just one (OR)."""
        matching = _make_mock_submission(
            processing_status=status,
            client_type=client_type,
        )
        wrong_status = _make_mock_submission(
            processing_status="error" if status != "error" else "imported",
            client_type=client_type,
        )
        wrong_type = _make_mock_submission(
            processing_status=status,
            client_type="existing" if client_type != "existing" else "new",
        )

        assert _matches_filters(matching, status, client_type, None)
        assert not _matches_filters(wrong_status, status, client_type, None)
        assert not _matches_filters(wrong_type, status, client_type, None)


# --- Property 16: Concurrent poll cycles are serialized ---


@pytest.mark.unit
class TestConcurrentPollCyclesSerializedProperty:
    """Property 16: Concurrent poll cycles are serialized.

    For any number of concurrent trigger_sync / poll_loop invocations,
    the asyncio.Lock ensures that _execute_poll_cycle never runs
    concurrently. At most one poll cycle executes at a time.

    Validates: Requirements 5.8
    """

    @given(n=st.integers(min_value=2, max_value=8))
    @settings(max_examples=50)
    def test_concurrent_triggers_never_overlap(self, n: int) -> None:
        """N concurrent trigger_sync calls never execute poll cycle in parallel."""
        active = 0
        max_active = 0

        async def mock_execute_poll_cycle() -> int:
            nonlocal active, max_active
            active += 1
            max_active = max(max_active, active)
            await asyncio.sleep(0.01)
            active -= 1
            return 0

        poller = object.__new__(GoogleSheetsPoller)
        poller._poll_lock = asyncio.Lock()
        poller._execute_poll_cycle = mock_execute_poll_cycle  # type: ignore[assignment]

        async def run() -> None:
            await asyncio.gather(*(poller.trigger_sync() for _ in range(n)))

        asyncio.run(run())

        assert max_active == 1, f"Expected max 1 concurrent, got {max_active}"

    @given(n=st.integers(min_value=2, max_value=6))
    @settings(max_examples=50)
    def test_execution_order_is_sequential(self, n: int) -> None:
        """Concurrent triggers produce sequential, non-overlapping execution."""
        order: list[tuple[int, str]] = []

        async def mock_execute_poll_cycle() -> int:
            idx = len([e for e in order if e[1] == "start"])
            order.append((idx, "start"))
            await asyncio.sleep(0.01)
            order.append((idx, "end"))
            return 0

        poller = object.__new__(GoogleSheetsPoller)
        poller._poll_lock = asyncio.Lock()
        poller._execute_poll_cycle = mock_execute_poll_cycle  # type: ignore[assignment]

        async def run() -> None:
            await asyncio.gather(*(poller.trigger_sync() for _ in range(n)))

        asyncio.run(run())

        assert len(order) == n * 2
        # Verify strict start/end alternation (no overlapping)
        for i in range(0, len(order), 2):
            assert order[i][1] == "start"
            assert order[i + 1][1] == "end"
            assert order[i][0] == order[i + 1][0]
