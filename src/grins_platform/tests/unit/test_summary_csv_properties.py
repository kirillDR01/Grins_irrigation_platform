"""Property-based tests for summary bucket counts and CSV export.

Property 9: Summary bucket counts match latest-wins data.
Property 10: CSV export content and filtering.
Property 11: Lead name split for CSV.

Validates: Requirements 9.2, 9.3, 11.2, 11.3, 11.4, 11.7, 14.5
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from hypothesis import (
    given,
    settings,
    strategies as st,
)

from grins_platform.services.campaign_response_service import (
    CampaignResponseService,
    _split_name,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_BASE_TIME = datetime(2026, 4, 1, tzinfo=timezone.utc)
_OPTION_KEYS = ["1", "2", "3"]
_STATUSES = ["parsed", "needs_review", "opted_out"]


def _make_row(
    *,
    phone: str,
    option_key: str | None,
    option_label: str | None,
    status: str,
    received_at: datetime,
    recipient_name: str | None = None,
    raw_reply_body: str = "1",
) -> MagicMock:
    row = MagicMock()
    row.id = uuid4()
    row.campaign_id = uuid4()
    row.phone = phone
    row.selected_option_key = option_key
    row.selected_option_label = option_label
    row.status = status
    row.received_at = received_at
    row.recipient_name = recipient_name
    row.raw_reply_body = raw_reply_body
    row.recipient_address = None
    return row


def _latest_wins(rows: list[MagicMock]) -> list[MagicMock]:
    """Compute latest-wins: one row per phone, most recent."""
    by_phone: dict[str, MagicMock] = {}
    for r in rows:
        cur = by_phone.get(r.phone)
        if cur is None or r.received_at > cur.received_at:
            by_phone[r.phone] = r
    return list(by_phone.values())


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

_phones = st.sampled_from(
    ["+16125551111", "+16125552222", "+16125553333", "+16125554444"],
)


@st.composite
def _response_set(draw: st.DrawFn) -> list[MagicMock]:
    """Generate 1-15 response rows from 1-4 phones."""
    count = draw(st.integers(min_value=1, max_value=15))
    rows: list[MagicMock] = []
    for i in range(count):
        phone = draw(_phones)
        status = draw(st.sampled_from(_STATUSES))
        key = draw(st.sampled_from(_OPTION_KEYS)) if status == "parsed" else None
        label = f"Week {key}" if key else None
        rows.append(
            _make_row(
                phone=phone,
                option_key=key,
                option_label=label,
                status=status,
                received_at=_BASE_TIME + timedelta(hours=i),
            ),
        )
    return rows


# ---------------------------------------------------------------------------
# Property 9: Summary bucket counts match latest-wins data
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSummaryBucketCountsProperty9:
    """Property 9 — bucket counts sum to total_replied and match
    latest-wins rows grouped by (status, option_key)."""

    @given(rows=_response_set())
    @settings(max_examples=50)
    @pytest.mark.asyncio
    async def test_bucket_counts_sum_to_total_replied(
        self,
        rows: list[MagicMock],
    ) -> None:
        """Req 9.2: Bucket counts sum to total_replied."""
        latest = _latest_wins(rows)

        grouped: dict[tuple[str, str | None], int] = {}
        for r in latest:
            key = (r.status, r.selected_option_key)
            grouped[key] = grouped.get(key, 0) + 1

        count_rows = [
            {"status": s, "option_key": ok, "count": c}
            for (s, ok), c in grouped.items()
        ]

        session = AsyncMock()
        repo_mock = AsyncMock()
        repo_mock.count_by_status_and_option.return_value = count_rows

        sent_result = MagicMock()
        sent_result.scalar.return_value = 10
        session.execute.return_value = sent_result

        svc = CampaignResponseService(session)
        svc.repo = repo_mock

        summary = await svc.get_response_summary(uuid4())

        assert summary.total_replied == sum(
            b.count for b in summary.buckets if b.status in ("parsed", "needs_review")
        )
        assert summary.total_replied == len(
            [r for r in latest if r.status in ("parsed", "needs_review")],
        )

    @given(rows=_response_set())
    @settings(max_examples=50)
    @pytest.mark.asyncio
    async def test_each_bucket_matches_grouped_count(
        self,
        rows: list[MagicMock],
    ) -> None:
        """Req 9.3: Each bucket matches latest-wins group count."""
        latest = _latest_wins(rows)

        grouped: dict[tuple[str, str | None], int] = {}
        for r in latest:
            key = (r.status, r.selected_option_key)
            grouped[key] = grouped.get(key, 0) + 1

        count_rows = [
            {"status": s, "option_key": ok, "count": c}
            for (s, ok), c in grouped.items()
        ]

        session = AsyncMock()
        repo_mock = AsyncMock()
        repo_mock.count_by_status_and_option.return_value = count_rows

        sent_result = MagicMock()
        sent_result.scalar.return_value = 5
        session.execute.return_value = sent_result

        svc = CampaignResponseService(session)
        svc.repo = repo_mock

        summary = await svc.get_response_summary(uuid4())

        for bucket in summary.buckets:
            expected = grouped.get(
                (bucket.status, bucket.option_key),
                0,
            )
            assert bucket.count == expected


# ---------------------------------------------------------------------------
# Property 10: CSV export content and filtering
# ---------------------------------------------------------------------------


def _make_iter_export(
    latest: list[MagicMock],
):  # type: ignore[no-untyped-def]
    """Build an async generator matching iter_for_export signature."""

    async def _iter(
        _campaign_id: object,
        option_key: str | None = None,
    ):  # type: ignore[no-untyped-def]
        filtered = (
            latest
            if option_key is None
            else [r for r in latest if r.selected_option_key == option_key]
        )
        for r in filtered:
            yield r

    return _iter


@pytest.mark.unit
class TestCsvExportProperty10:
    """Property 10 — one row per latest-wins response, correct columns,
    option_key filter works."""

    @given(rows=_response_set())
    @settings(max_examples=50)
    @pytest.mark.asyncio
    async def test_csv_row_count_matches_latest_wins(
        self,
        rows: list[MagicMock],
    ) -> None:
        """Req 11.2: One CSV row per latest-wins response."""
        latest = _latest_wins(rows)

        session = AsyncMock()
        repo_mock = AsyncMock()
        repo_mock.iter_for_export = _make_iter_export(latest)

        svc = CampaignResponseService(session)
        svc.repo = repo_mock

        csv_rows = [r async for r in svc.iter_csv_rows(uuid4())]
        assert len(csv_rows) == len(latest)

    @given(rows=_response_set())
    @settings(max_examples=30)
    @pytest.mark.asyncio
    async def test_csv_option_key_filter(
        self,
        rows: list[MagicMock],
    ) -> None:
        """Req 11.4: option_key filter returns only matching rows."""
        latest = _latest_wins(rows)
        filter_key = "1"
        expected = [r for r in latest if r.selected_option_key == filter_key]

        session = AsyncMock()
        repo_mock = AsyncMock()
        repo_mock.iter_for_export = _make_iter_export(latest)

        svc = CampaignResponseService(session)
        svc.repo = repo_mock

        csv_rows = [
            r
            async for r in svc.iter_csv_rows(
                uuid4(),
                option_key=filter_key,
            )
        ]
        assert len(csv_rows) == len(expected)

    @given(rows=_response_set())
    @settings(max_examples=30)
    @pytest.mark.asyncio
    async def test_csv_rows_have_correct_fields(
        self,
        rows: list[MagicMock],
    ) -> None:
        """Req 11.3: CSV rows have correct columns."""
        latest = _latest_wins(rows)

        session = AsyncMock()
        repo_mock = AsyncMock()
        repo_mock.iter_for_export = _make_iter_export(latest)

        svc = CampaignResponseService(session)
        svc.repo = repo_mock

        async for csv_row in svc.iter_csv_rows(uuid4()):
            assert hasattr(csv_row, "first_name")
            assert hasattr(csv_row, "last_name")
            assert hasattr(csv_row, "phone")
            assert hasattr(csv_row, "selected_option_label")
            assert hasattr(csv_row, "raw_reply")
            assert hasattr(csv_row, "received_at")


# ---------------------------------------------------------------------------
# Property 11: Lead name split for CSV
# ---------------------------------------------------------------------------

_SINGLE_TOKEN = st.from_regex(r"[A-Z][a-z]+", fullmatch=True)


@pytest.mark.unit
class TestNameSplitProperty11:
    """Property 11 — first whitespace split produces correct
    first/last; single-token → empty last; null → both empty."""

    @given(first=_SINGLE_TOKEN, last=_SINGLE_TOKEN)
    @settings(max_examples=50)
    def test_two_part_name_splits_correctly(
        self,
        first: str,
        last: str,
    ) -> None:
        """Req 11.7: Two-part name splits on first whitespace."""
        first_out, last_out = _split_name(f"{first} {last}")
        assert first_out == first
        assert last_out == last

    @given(name=_SINGLE_TOKEN)
    @settings(max_examples=30)
    def test_single_token_gives_empty_last(
        self,
        name: str,
    ) -> None:
        """Single-token name → (token, "")."""
        first_out, last_out = _split_name(name)
        assert first_out == name
        assert last_out == ""

    def test_none_gives_both_empty(self) -> None:
        """None → ("", "")."""
        assert _split_name(None) == ("", "")

    def test_empty_string_gives_both_empty(self) -> None:
        """Empty string → ("", "")."""
        assert _split_name("") == ("", "")

    @given(
        first=_SINGLE_TOKEN,
        middle=_SINGLE_TOKEN,
        last=_SINGLE_TOKEN,
    )
    @settings(max_examples=30)
    def test_three_part_name_splits_on_first_space(
        self,
        first: str,
        middle: str,
        last: str,
    ) -> None:
        """Three-part name: first token → first_name, rest → last."""
        full = f"{first} {middle} {last}"
        first_out, last_out = _split_name(full)
        assert first_out == first
        assert last_out == f"{middle} {last}"
