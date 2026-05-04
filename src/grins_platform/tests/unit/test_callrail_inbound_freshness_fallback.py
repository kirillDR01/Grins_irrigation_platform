"""Bug #3 — CallRail inbound freshness-window fallback chain.

CallRail's verified inbound text-message webhook does not include
``created_at`` or ``sent_at`` at the top level (see
``services/sms/callrail_provider.py:258-286``). Without a fallback,
every real inbound webhook 400s with ``replay_or_stale_timestamp`` and
the appointment-confirmation handler never runs.

These tests pin the fallback chain:
1. ``payload.created_at`` → use as-is
2. ``payload.sent_at`` → use as-is (defensive future-proofing)
3. neither → fall back to receipt time

Replay protection is preserved by ``resource_id`` dedup against Redis
primary + ``webhook_processed_logs`` table.

Validates: ``.agents/plans/master-plan-run-findings-bug-resolution-2026-05-04.md``
Phase 2 / Task 2.3.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from grins_platform.api.v1.callrail_webhooks import _extract_created_at

pytestmark = pytest.mark.unit


_FIXTURE_PATH = (
    Path(__file__).parent / "fixtures" / "callrail_real_inbound.json"
)


def _is_iso_within_clock_skew(value: str, *, max_skew_seconds: int = 30) -> bool:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    delta = abs(datetime.now(timezone.utc) - parsed)
    return delta < timedelta(seconds=max_skew_seconds)


class TestExtractCreatedAt:
    def test_payload_with_created_at_uses_it(self) -> None:
        ts = "2026-05-04T15:30:00+00:00"
        value, source = _extract_created_at({"created_at": ts})
        assert value == ts
        assert source == "payload_created_at"

    def test_payload_with_only_sent_at_falls_back_to_sent_at(self) -> None:
        ts = "2026-05-04T15:31:00+00:00"
        value, source = _extract_created_at({"sent_at": ts})
        assert value == ts
        assert source == "payload_sent_at"

    def test_payload_with_both_prefers_created_at(self) -> None:
        value, source = _extract_created_at(
            {
                "created_at": "2026-05-04T15:30:00+00:00",
                "sent_at": "2026-05-04T15:31:00+00:00",
            },
        )
        assert value == "2026-05-04T15:30:00+00:00"
        assert source == "payload_created_at"

    def test_payload_with_neither_falls_back_to_receipt_time(self) -> None:
        value, source = _extract_created_at({})
        assert source == "receipt_time"
        assert _is_iso_within_clock_skew(value)

    def test_real_callrail_payload_falls_back_to_receipt_time(self) -> None:
        """The verified-real CallRail payload has no timestamp fields."""
        payload = json.loads(_FIXTURE_PATH.read_text())
        assert "created_at" not in payload
        assert "sent_at" not in payload
        value, source = _extract_created_at(payload)
        assert source == "receipt_time"
        assert _is_iso_within_clock_skew(value)

    def test_empty_string_created_at_falls_through(self) -> None:
        """Empty string is not a valid timestamp — fall through."""
        value, source = _extract_created_at({"created_at": ""})
        assert source == "receipt_time"
        assert _is_iso_within_clock_skew(value)
