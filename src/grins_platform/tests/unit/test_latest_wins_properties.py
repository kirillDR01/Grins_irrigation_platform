"""Property-based tests for latest-wins deduplication.

Property 8: Latest-wins deduplication — ``DISTINCT ON`` query returns
exactly one row per phone with the most recent ``received_at``.

Validates: Requirements 8.2, 8.3, 10.3, 11.6
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

from grins_platform.repositories.campaign_response_repository import (
    CampaignResponseRepository,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_BASE_TIME = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _make_response(
    *,
    phone: str,
    received_at: datetime,
) -> MagicMock:
    """Build a mock CampaignResponse row."""
    row = MagicMock()
    row.id = uuid4()
    row.phone = phone
    row.received_at = received_at
    row.status = "parsed"
    return row


def _expected_latest(rows: list[MagicMock]) -> dict[str, MagicMock]:
    """Compute expected latest-wins: one row per phone, most recent."""
    by_phone: dict[str, MagicMock] = {}
    for r in rows:
        if r.phone not in by_phone or r.received_at > by_phone[r.phone].received_at:
            by_phone[r.phone] = r
    return by_phone


def _build_repo_with_results(
    latest_rows: list[MagicMock],
) -> CampaignResponseRepository:
    """Return a repo whose session.execute returns *latest_rows*."""
    session = AsyncMock()
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = latest_rows
    result_mock = MagicMock()
    result_mock.scalars.return_value = scalars_mock
    session.execute.return_value = result_mock
    return CampaignResponseRepository(session)


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

_phones = st.sampled_from(
    ["+16125551111", "+16125552222", "+16125553333", "+16125554444"],
)
_offsets = st.integers(min_value=0, max_value=100)


@st.composite
def _response_sets(draw: st.DrawFn) -> tuple[list[MagicMock], list[MagicMock]]:
    """Generate 1-20 responses from 1-4 phones; return (all_rows, expected)."""
    count = draw(st.integers(min_value=1, max_value=20))
    rows: list[MagicMock] = []
    for i in range(count):
        phone = draw(_phones)
        offset = draw(_offsets)
        rows.append(
            _make_response(
                phone=phone,
                received_at=_BASE_TIME + timedelta(hours=offset, minutes=i),
            ),
        )
    expected = _expected_latest(rows)
    return rows, list(expected.values())


# ---------------------------------------------------------------------------
# Property 8: Latest-wins deduplication
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestLatestWinsProperty8:
    """Property 8 — DISTINCT ON returns exactly one row per phone
    with the most recent received_at."""

    @given(data=_response_sets())
    @settings(max_examples=50)
    @pytest.mark.asyncio
    async def test_one_row_per_phone(
        self,
        data: tuple[list[MagicMock], list[MagicMock]],
    ) -> None:
        """Req 8.2: Result contains at most one row per phone."""
        _all_rows, expected = data
        repo = _build_repo_with_results(expected)
        result = await repo.get_latest_for_campaign(uuid4())

        phones = [r.phone for r in result]
        assert len(phones) == len(set(phones)), "Duplicate phones in result"

    @given(data=_response_sets())
    @settings(max_examples=50)
    @pytest.mark.asyncio
    async def test_most_recent_per_phone(
        self,
        data: tuple[list[MagicMock], list[MagicMock]],
    ) -> None:
        """Req 8.3: Each returned row is the most recent for its phone."""
        all_rows, expected = data
        latest_map = _expected_latest(all_rows)

        repo = _build_repo_with_results(expected)
        result = await repo.get_latest_for_campaign(uuid4())

        for row in result:
            assert row.received_at == latest_map[row.phone].received_at

    @given(data=_response_sets())
    @settings(max_examples=50)
    @pytest.mark.asyncio
    async def test_count_equals_distinct_phones(
        self,
        data: tuple[list[MagicMock], list[MagicMock]],
    ) -> None:
        """Req 10.3, 11.6: Row count equals number of distinct phones."""
        all_rows, expected = data
        distinct_phones = {r.phone for r in all_rows}

        repo = _build_repo_with_results(expected)
        result = await repo.get_latest_for_campaign(uuid4())

        assert len(result) == len(distinct_phones)

    @pytest.mark.asyncio
    async def test_empty_campaign_returns_empty(self) -> None:
        """No responses → empty list."""
        repo = _build_repo_with_results([])
        result = await repo.get_latest_for_campaign(uuid4())
        assert result == []

    @pytest.mark.asyncio
    async def test_single_phone_multiple_replies(self) -> None:
        """Req 8.2: Multiple replies from one phone → exactly one row."""
        phone = "+16125551111"
        rows = [
            _make_response(
                phone=phone,
                received_at=_BASE_TIME + timedelta(hours=i),
            )
            for i in range(3)
        ]
        latest = max(rows, key=lambda r: r.received_at)

        repo = _build_repo_with_results([latest])
        result = await repo.get_latest_for_campaign(uuid4())

        assert len(result) == 1
        assert result[0].phone == phone
        assert result[0].received_at == latest.received_at
