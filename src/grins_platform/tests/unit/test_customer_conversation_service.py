"""Unit tests for :class:`CustomerConversationService` (gap-13).

Covers cursor encode/decode round-trips, channel classification, and
the merge-sort invariant. Full SQL fan-out is exercised in functional
tests against a real DB.

Validates: scheduling-gaps gap-13.
"""

from __future__ import annotations

import heapq
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from grins_platform.schemas.customer_conversation import ConversationItem
from grins_platform.services.customer_conversation_service import (
    CustomerConversationService,
    _Cursor,
    _sort_key,
)


def _make_item(
    *,
    source_table: str = "sent_messages",
    direction: str = "outbound",
    timestamp: datetime | None = None,
) -> ConversationItem:
    return ConversationItem(
        id=uuid4(),
        source_table=source_table,  # type: ignore[arg-type]
        direction=direction,  # type: ignore[arg-type]
        channel="sms",
        timestamp=timestamp or datetime.now(tz=timezone.utc),
        body="hello",
        status=None,
        parsed_keyword=None,
        appointment_id=None,
        from_phone=None,
        to_phone=None,
        message_type=None,
    )


@pytest.mark.unit
class TestCursorCodec:
    def test_round_trip(self) -> None:
        original = _Cursor(
            timestamp=datetime(2026, 4, 26, 10, 0, tzinfo=timezone.utc),
            source_table="sent_messages",
            source_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        )
        decoded = _Cursor.decode(original.encode())

        assert decoded is not None
        assert decoded.timestamp == original.timestamp
        assert decoded.source_table == original.source_table
        assert decoded.source_id == original.source_id

    def test_decode_garbage_returns_none(self) -> None:
        assert _Cursor.decode("not-base64") is None
        assert _Cursor.decode("") is None


@pytest.mark.unit
class TestChannelClassification:
    def test_email_message_type_maps_to_email(self) -> None:
        assert (
            CustomerConversationService._classify_outbound_channel("email_estimate")
            == "email"
        )

    def test_voice_phone_call_maps_to_phone(self) -> None:
        assert (
            CustomerConversationService._classify_outbound_channel("voice_call")
            == "phone"
        )

    def test_sms_default(self) -> None:
        assert (
            CustomerConversationService._classify_outbound_channel(
                "appointment_confirmation"
            )
            == "sms"
        )

    def test_communications_channel_known_values(self) -> None:
        assert (
            CustomerConversationService._classify_communication_channel("sms") == "sms"
        )
        assert (
            CustomerConversationService._classify_communication_channel("email")
            == "email"
        )
        assert (
            CustomerConversationService._classify_communication_channel("phone")
            == "phone"
        )

    def test_communications_channel_unknown_falls_back_to_other(self) -> None:
        assert (
            CustomerConversationService._classify_communication_channel("fax")
            == "other"
        )


@pytest.mark.unit
class TestMergeOrdering:
    """The merge invariant: the merged stream is monotonically descending.

    Mirrors the property-based test described in the gap-13 plan; here
    expressed deterministically over hand-crafted inputs.
    """

    def test_heapq_merge_yields_descending_timestamps(self) -> None:
        now = datetime.now(tz=timezone.utc)
        sent = sorted(
            [
                _make_item(timestamp=now),
                _make_item(timestamp=now - timedelta(hours=2)),
            ],
            key=_sort_key,
        )
        confirmations = sorted(
            [
                _make_item(
                    source_table="job_confirmation_responses",
                    direction="inbound",
                    timestamp=now - timedelta(hours=1),
                ),
                _make_item(
                    source_table="job_confirmation_responses",
                    direction="inbound",
                    timestamp=now - timedelta(hours=3),
                ),
            ],
            key=_sort_key,
        )

        merged = list(heapq.merge(sent, confirmations, key=_sort_key))

        timestamps = [item.timestamp for item in merged]
        assert timestamps == sorted(timestamps, reverse=True)
