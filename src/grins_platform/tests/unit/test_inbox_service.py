"""Unit tests for :class:`InboxService` (gap-16 v0).

Covers the pure helpers (cursor codec, triage classifier, filter matcher,
counts builder) that don't require a live SQLAlchemy session. Full
integration of the SQL fan-out is exercised in functional tests.

Validates: scheduling-gaps gap-16.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from grins_platform.schemas.inbox import InboxItem
from grins_platform.services.inbox_service import (
    InboxService,
    _classify_triage,
    _Cursor,
    _matches_filter,
    _sort_key,
)


def _make_item(
    *,
    source_table: str = "communications",
    triage_status: str = "pending",
    received_at: datetime | None = None,
    customer_id: bool | None = None,
    status: str | None = None,
) -> InboxItem:
    return InboxItem(
        id=uuid4(),
        source_table=source_table,  # type: ignore[arg-type]
        triage_status=triage_status,  # type: ignore[arg-type]
        received_at=received_at or datetime.now(tz=timezone.utc),
        body="example body",
        from_phone=None,
        customer_id=uuid4() if customer_id else None,
        customer_name=None,
        appointment_id=None,
        parsed_keyword=None,
        status=status,
    )


@pytest.mark.unit
class TestCursorCodec:
    """Cursor round-trip is required for stable pagination."""

    def test_encode_decode_round_trip(self) -> None:
        original = _Cursor(
            timestamp=datetime(2026, 4, 26, 12, 30, tzinfo=timezone.utc),
            source_table="communications",
            source_id="11111111-1111-1111-1111-111111111111",
        )

        decoded = _Cursor.decode(original.encode())

        assert decoded is not None
        assert decoded.timestamp == original.timestamp
        assert decoded.source_table == original.source_table
        assert decoded.source_id == original.source_id

    def test_decode_garbage_returns_none(self) -> None:
        assert _Cursor.decode("not-a-valid-cursor") is None
        assert _Cursor.decode("") is None


@pytest.mark.unit
class TestClassifyTriage:
    """The dispatch table must keep handled rows out of the pending bucket."""

    @pytest.mark.parametrize(
        ("source_table", "status", "customer_id", "expected"),
        [
            # job_confirmation_responses
            ("job_confirmation_responses", "needs_review", None, "pending"),
            ("job_confirmation_responses", "parsed", None, "handled"),
            ("job_confirmation_responses", "confirmed", None, "handled"),
            # reschedule_requests
            ("reschedule_requests", "open", None, "pending"),
            ("reschedule_requests", "resolved", None, "handled"),
            ("reschedule_requests", "rejected", None, "handled"),
            # campaign_responses
            ("campaign_responses", "orphan", None, "pending"),
            ("campaign_responses", "opted_out", None, "pending"),
            ("campaign_responses", "parsed", None, "handled"),
            # communications — orphan (no customer_id) always pending
            ("communications", "addressed", None, "pending"),
            # communications — addressed when linked
            ("communications", "addressed", uuid4(), "handled"),
            # communications — unaddressed when linked
            ("communications", "unaddressed", uuid4(), "pending"),
        ],
    )
    def test_classify_dispatch(
        self,
        source_table: str,
        status: str,
        customer_id: object,
        expected: str,
    ) -> None:
        result = _classify_triage(
            source_table=source_table,  # type: ignore[arg-type]
            status=status,
            customer_id=customer_id,  # type: ignore[arg-type]
        )
        assert result == expected


@pytest.mark.unit
class TestMatchesFilter:
    """The filter token semantics drive the queue-pill counts and rows."""

    def test_all_returns_everything(self) -> None:
        assert _matches_filter(triage="all", item=_make_item()) is True

    def test_needs_triage_only_pending(self) -> None:
        assert (
            _matches_filter(
                triage="needs_triage",
                item=_make_item(triage_status="pending"),
            )
            is True
        )
        assert (
            _matches_filter(
                triage="needs_triage",
                item=_make_item(triage_status="handled"),
            )
            is False
        )

    def test_orphans_match_null_customer_or_orphan_status(self) -> None:
        # Null customer_id qualifies regardless of status.
        assert (
            _matches_filter(
                triage="orphans",
                item=_make_item(customer_id=False, status="parsed"),
            )
            is True
        )
        # Linked customer with explicit "orphan" status still qualifies.
        assert (
            _matches_filter(
                triage="orphans",
                item=_make_item(customer_id=True, status="orphan"),
            )
            is True
        )
        # Linked customer with normal status does not.
        assert (
            _matches_filter(
                triage="orphans",
                item=_make_item(customer_id=True, status="parsed"),
            )
            is False
        )

    def test_unrecognized_filters_to_needs_review(self) -> None:
        assert (
            _matches_filter(
                triage="unrecognized",
                item=_make_item(status="needs_review"),
            )
            is True
        )
        assert (
            _matches_filter(
                triage="unrecognized",
                item=_make_item(status="parsed"),
            )
            is False
        )

    def test_opt_outs_filter(self) -> None:
        assert (
            _matches_filter(
                triage="opt_outs",
                item=_make_item(status="opted_out"),
            )
            is True
        )
        assert (
            _matches_filter(
                triage="opt_outs",
                item=_make_item(status="parsed"),
            )
            is False
        )

    # F8: standalone STOP/START rows arrive on source_table=consent.
    def test_consent_stop_appears_in_opt_outs_filter(self) -> None:
        assert (
            _matches_filter(
                triage="opt_outs",
                item=_make_item(source_table="consent", status="opt_out"),
            )
            is True
        )

    def test_consent_start_appears_in_opt_ins_filter(self) -> None:
        assert (
            _matches_filter(
                triage="opt_ins",
                item=_make_item(source_table="consent", status="opt_in"),
            )
            is True
        )
        # Other sources never match opt_ins.
        assert (
            _matches_filter(
                triage="opt_ins",
                item=_make_item(source_table="campaign_responses", status="opt_in"),
            )
            is False
        )

    def test_consent_pending_classification_for_stop(self) -> None:
        result = _classify_triage(
            source_table="consent",
            status="opt_out",
            customer_id=uuid4(),
        )
        assert result == "pending"

    def test_consent_handled_classification_for_start(self) -> None:
        result = _classify_triage(
            source_table="consent",
            status="opt_in",
            customer_id=uuid4(),
        )
        assert result == "handled"


@pytest.mark.unit
class TestComputeCounts:
    """Counts must be agnostic to the active filter."""

    def test_counts_aggregate_per_pill(self) -> None:
        now = datetime.now(tz=timezone.utc)
        items = [
            _make_item(
                source_table="job_confirmation_responses",
                triage_status="pending",
                customer_id=True,
                status="needs_review",
                received_at=now,
            ),
            _make_item(
                source_table="campaign_responses",
                triage_status="pending",
                customer_id=False,
                status="orphan",
                received_at=now - timedelta(minutes=1),
            ),
            _make_item(
                source_table="job_confirmation_responses",
                triage_status="handled",
                customer_id=True,
                status="parsed",
                received_at=now - timedelta(minutes=2),
            ),
            _make_item(
                source_table="campaign_responses",
                triage_status="pending",
                customer_id=True,
                status="opted_out",
                received_at=now - timedelta(minutes=3),
            ),
        ]

        counts = InboxService._compute_counts(items)

        assert counts.all == 4
        assert counts.needs_triage == 3
        assert counts.archived == 0
        # orphan customer_id is None OR explicit "orphan" status
        assert counts.orphans == 1
        assert counts.unrecognized == 1
        assert counts.opt_outs == 1


@pytest.mark.unit
class TestSortKey:
    """Sort key must yield strict descending timestamp order."""

    def test_descending_timestamp(self) -> None:
        now = datetime.now(tz=timezone.utc)
        older = _make_item(received_at=now - timedelta(hours=1))
        newer = _make_item(received_at=now)
        ordered = sorted([older, newer], key=_sort_key)
        # Newer comes first because we negate the epoch.
        assert ordered[0] is newer
        assert ordered[1] is older
