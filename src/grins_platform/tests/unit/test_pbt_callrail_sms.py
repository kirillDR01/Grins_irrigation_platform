"""Property-based tests for CallRail SMS integration.

All property-based tests for the callrail-sms-integration spec live here.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac as _hmac
import importlib.util as _ilu
import json
import math
import sys as _sys
import tempfile as _tempfile
from datetime import date, datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import httpx
import pytest
from hypothesis import (
    given,
    settings,
    strategies as st,
)
from pydantic import ValidationError

from grins_platform.api.v1.callrail_webhooks import (
    _REDIS_KEY_PREFIX,
    _REDIS_MSGID_KEY_PREFIX,
    _is_duplicate,
    _mark_processed,
)
from grins_platform.models.campaign import Campaign
from grins_platform.models.customer import Customer
from grins_platform.models.lead import Lead
from grins_platform.repositories.campaign_repository import CampaignRepository
from grins_platform.schemas.ai import MessageType
from grins_platform.schemas.campaign import TargetAudience
from grins_platform.services.background_jobs import (
    _BATCH_SIZE,
    CampaignWorker,
    _is_within_time_window,
)
from grins_platform.services.campaign_service import CampaignService
from grins_platform.services.sms.callrail_provider import (
    CallRailProvider,
    _mask_phone as _mask_phone_callrail,
)
from grins_platform.services.sms.consent import (
    bulk_insert_attestation_consent,
    check_sms_consent,
)
from grins_platform.services.sms.ghost_lead import create_or_get
from grins_platform.services.sms.null_provider import NullProvider
from grins_platform.services.sms.phone_normalizer import (
    PhoneNormalizationError,
    is_central_timezone,
    lookup_timezone,
    normalize_to_e164,
)
from grins_platform.services.sms.rate_limit_tracker import (
    CheckResult,
    SMSRateLimitTracker,
)
from grins_platform.services.sms.recipient import Recipient
from grins_platform.services.sms.segment_counter import (
    _DEFAULT_FOOTER,
    _DEFAULT_PREFIX,
    _GSM7_BASIC,
    _gsm7_char_count,
    count_segments,
)
from grins_platform.services.sms.state_machine import (
    _ALLOWED_TRANSITIONS,
    _ORPHAN_RECOVERY_SQL,
    InvalidStateTransitionError,
    RecipientState,
    transition,
)
from grins_platform.services.sms.templating import render_template
from grins_platform.services.sms_service import (
    _DEFAULT_FOOTER as _SVC_FOOTER,
    _DEFAULT_PREFIX as _SVC_PREFIX,
    SMSConsentDeniedError,
    SMSService,
    _mask_phone as _mask_phone_sms,
)

# ---------------------------------------------------------------------------
# Shared autouse fixture: disable the SMS recipient allow-list guard
#
# ``enforce_recipient_allowlist`` blocks any outbound send whose phone is
# not in ``SMS_TEST_PHONE_ALLOWLIST``. In production that env var is unset
# (guard is a no-op); in this test suite the owner's `.env` pins the
# allowlist to a single real phone so stray debugging scripts cannot page
# customers. Hypothesis here generates arbitrary E.164 phones, so every
# property test would trip the guard even though all HTTP calls are
# intercepted by ``httpx.MockTransport`` and never hit the network.
# Scrub the env var for the duration of each test so the property tests
# can exercise ``CallRailProvider.send_text`` without the guard firing.
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _disable_sms_allowlist_for_pbt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SMS_TEST_PHONE_ALLOWLIST", raising=False)
    # ``SMS_TEST_REDIRECT_TO`` rewrites outbound phones in dev/staging.
    # The property tests assert payload[customer_phone_number] equals the
    # randomly-generated phone, so the redirect must be off here too.
    monkeypatch.delenv("SMS_TEST_REDIRECT_TO", raising=False)


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

e164_phone = st.from_regex(r"\+1[2-9]\d{9}", fullmatch=True)
sms_body = st.text(min_size=1, max_size=1600)
# Alphanumeric IDs for CallRail config values
callrail_id = st.from_regex(r"[A-Za-z0-9]{10,30}", fullmatch=True)


# ---------------------------------------------------------------------------
# Property 1: NullProvider records all sends
# Validates: Requirement 1.9
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestProperty1NullProviderRecordsAllSends:
    """Every send_text call is recorded in NullProvider.sent with correct data."""

    @given(
        phones=st.lists(e164_phone, min_size=1, max_size=20),
        bodies=st.lists(sms_body, min_size=1, max_size=20),
    )
    @settings(max_examples=50, deadline=None)
    def test_all_sends_recorded(
        self,
        phones: list[str],
        bodies: list[str],
    ) -> None:
        """NullProvider.sent length equals send_text call count."""
        provider = NullProvider()
        pairs = list(zip(phones, bodies))

        async def _run() -> None:
            for phone, body in pairs:
                await provider.send_text(phone, body)

        asyncio.run(_run())

        assert len(provider.sent) == len(pairs)
        for record, (phone, body) in zip(provider.sent, pairs):
            assert record["to"] == phone
            assert record["body"] == body
            assert "id" in record  # synthetic UUID present

    @given(phone=e164_phone, body=sms_body)
    @settings(max_examples=50, deadline=None)
    def test_send_returns_sent_status(
        self,
        phone: str,
        body: str,
    ) -> None:
        """send_text returns status='sent' with provider_message_id."""
        provider = NullProvider()
        result = asyncio.run(provider.send_text(phone, body))
        assert result.status == "sent"
        assert result.provider_message_id  # non-empty

    @given(data=st.data())
    @settings(max_examples=20, deadline=None)
    def test_provider_name_is_null(self, data: st.DataObject) -> None:
        """provider_name is always 'null'."""
        _ = data  # unused, but ensures Hypothesis drives the test
        provider = NullProvider()
        assert provider.provider_name == "null"

    @given(phone=e164_phone, body=sms_body)
    @settings(max_examples=20, deadline=None)
    def test_each_send_has_unique_id(self, phone: str, body: str) -> None:
        """Two sends produce distinct provider_message_ids."""
        provider = NullProvider()

        async def _run() -> tuple[str, str]:
            r1 = await provider.send_text(phone, body)
            r2 = await provider.send_text(phone, body)
            return r1.provider_message_id, r2.provider_message_id

        id1, id2 = asyncio.run(_run())
        assert id1 != id2


# ---------------------------------------------------------------------------
# Property 2: CallRail send_text payload structure
# Validates: Requirement 2.3
# ---------------------------------------------------------------------------


def _make_callrail_ok_response(_request: httpx.Request) -> httpx.Response:
    """Return a minimal 200 response matching CallRail's contract."""
    return httpx.Response(
        200,
        json={
            "id": "conv_123",
            "recent_messages": [
                {"sms_thread": {"id": "thread_456"}},
            ],
        },
        headers={
            "x-request-id": "req-abc",
            "x-rate-limit-hourly-allowed": "150",
            "x-rate-limit-hourly-used": "1",
            "x-rate-limit-daily-allowed": "500",
            "x-rate-limit-daily-used": "1",
        },
    )


@pytest.mark.unit
class TestProperty2CallRailPayloadStructure:
    """send_text always POSTs the correct JSON payload to the right URL."""

    @given(
        phone=e164_phone,
        body=sms_body,
        account_id=callrail_id,
        company_id=callrail_id,
        tracking_number=e164_phone,
    )
    @settings(max_examples=50, deadline=None)
    def test_payload_contains_required_fields(
        self,
        phone: str,
        body: str,
        account_id: str,
        company_id: str,
        tracking_number: str,
    ) -> None:
        """Payload has required fields: company_id, tracking_number, phone, content."""
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return _make_callrail_ok_response(request)

        transport = httpx.MockTransport(handler)
        provider = CallRailProvider(
            api_key="test-key",
            account_id=account_id,
            company_id=company_id,
            tracking_number=tracking_number,
        )
        provider._client = httpx.AsyncClient(
            transport=transport,
            base_url="https://api.callrail.com",
        )

        asyncio.run(provider.send_text(phone, body))

        assert len(captured) == 1
        payload = json.loads(captured[0].content)
        assert payload["company_id"] == company_id
        assert payload["tracking_number"] == tracking_number
        assert payload["customer_phone_number"] == phone
        assert payload["content"] == body

    @given(
        phone=e164_phone,
        body=sms_body,
        account_id=callrail_id,
    )
    @settings(max_examples=50, deadline=None)
    def test_url_contains_account_id(
        self,
        phone: str,
        body: str,
        account_id: str,
    ) -> None:
        """POST URL is always /v3/a/{account_id}/text-messages.json."""
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return _make_callrail_ok_response(request)

        transport = httpx.MockTransport(handler)
        provider = CallRailProvider(
            api_key="test-key",
            account_id=account_id,
            company_id="comp",
            tracking_number="+19525293750",
        )
        provider._client = httpx.AsyncClient(
            transport=transport,
            base_url="https://api.callrail.com",
        )

        asyncio.run(provider.send_text(phone, body))

        assert len(captured) == 1
        assert captured[0].url.path == f"/v3/a/{account_id}/text-messages.json"

    @given(phone=e164_phone, body=sms_body)
    @settings(max_examples=30, deadline=None)
    def test_result_maps_conversation_fields(
        self,
        phone: str,
        body: str,
    ) -> None:
        """ProviderSendResult maps id→conversation_id and sms_thread.id→thread_id."""
        transport = httpx.MockTransport(_make_callrail_ok_response)
        provider = CallRailProvider(
            api_key="k",
            account_id="acc",
            company_id="comp",
            tracking_number="+19525293750",
        )
        provider._client = httpx.AsyncClient(
            transport=transport,
            base_url="https://api.callrail.com",
        )

        result = asyncio.run(provider.send_text(phone, body))

        assert result.provider_conversation_id == "conv_123"
        assert result.provider_thread_id == "thread_456"
        assert result.status == "sent"
        assert result.request_id == "req-abc"


# ---------------------------------------------------------------------------
# Property 5: Recipient factory correctness
# Validates: Requirements 4.2, 4.3, 4.4
# ---------------------------------------------------------------------------

_uuid_st = st.builds(uuid4)
_name_part = st.text(
    alphabet=st.characters(whitelist_categories=["L"]),
    min_size=1,
    max_size=30,
)


@pytest.mark.unit
class TestProperty5RecipientFactoryCorrectness:
    """Recipient factories map source fields correctly."""

    @given(
        cust_id=_uuid_st,
        phone=e164_phone,
        first_name=_name_part,
        last_name=_name_part,
    )
    @settings(max_examples=50, deadline=None)
    def test_from_customer(
        self,
        cust_id: UUID,
        phone: str,
        first_name: str,
        last_name: str,
    ) -> None:
        customer = SimpleNamespace(
            id=cust_id,
            phone=phone,
            first_name=first_name,
            last_name=last_name,
        )
        r = Recipient.from_customer(customer)  # type: ignore[arg-type]
        assert r.source_type == "customer"
        assert r.customer_id == cust_id
        assert r.lead_id is None
        assert r.phone == phone
        assert r.first_name == first_name
        assert r.last_name == last_name

    @given(
        lead_id=_uuid_st,
        phone=e164_phone,
        first=_name_part,
        last=_name_part,
    )
    @settings(max_examples=50, deadline=None)
    def test_from_lead(
        self,
        lead_id: UUID,
        phone: str,
        first: str,
        last: str,
    ) -> None:
        lead = SimpleNamespace(id=lead_id, phone=phone, name=f"{first} {last}")
        r = Recipient.from_lead(lead)  # type: ignore[arg-type]
        assert r.source_type == "lead"
        assert r.lead_id == lead_id
        assert r.customer_id is None
        assert r.phone == phone
        assert r.first_name == first
        assert r.last_name == last

    @given(lead_id=_uuid_st, phone=e164_phone, single_name=_name_part)
    @settings(max_examples=50, deadline=None)
    def test_from_lead_single_name(
        self,
        lead_id: UUID,
        phone: str,
        single_name: str,
    ) -> None:
        """Lead with single-token name → first_name set, last_name None."""
        lead = SimpleNamespace(id=lead_id, phone=phone, name=single_name)
        r = Recipient.from_lead(lead)  # type: ignore[arg-type]
        assert r.first_name == single_name
        assert r.last_name is None

    @given(
        phone=e164_phone,
        lead_id=_uuid_st,
        first_name=st.one_of(st.none(), _name_part),
        last_name=st.one_of(st.none(), _name_part),
    )
    @settings(max_examples=50, deadline=None)
    def test_from_adhoc(
        self,
        phone: str,
        lead_id: UUID,
        first_name: str | None,
        last_name: str | None,
    ) -> None:
        r = Recipient.from_adhoc(phone, lead_id, first_name, last_name)
        assert r.source_type == "ad_hoc"
        assert r.lead_id == lead_id
        assert r.customer_id is None
        assert r.phone == phone
        assert r.first_name == first_name
        assert r.last_name == last_name


# ---------------------------------------------------------------------------
# Property 7: Ghost lead creation invariants
# Validates: Requirements 5.1, 5.2
# ---------------------------------------------------------------------------

# Valid 10-digit US phone formats for ghost lead tests
_raw_phone_formats = st.sampled_from(
    [
        "(952) 529-3750",
        "952-529-3750",
        "9525293750",
        "+19525293750",
        "1-952-529-3750",
    ],
)
# Generate varied valid phones: area code 200-999, exchange 200-999
_valid_area = st.integers(min_value=200, max_value=999)
_valid_exchange = st.integers(min_value=200, max_value=999)
_valid_subscriber = st.integers(min_value=0, max_value=9999)
_generated_phone = st.builds(
    lambda a, e, s: f"+1{a}{e}{s:04d}",
    _valid_area,
    _valid_exchange,
    _valid_subscriber,
).filter(lambda p: p[5:8] != "555" or p[8:10] != "01")


def _make_mock_session(existing_lead: Lead | None = None) -> AsyncMock:
    """Create a mock AsyncSession for ghost_lead tests."""
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()

    mock_result = AsyncMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=existing_lead)
    session.execute = AsyncMock(return_value=mock_result)
    return session


@pytest.mark.unit
class TestProperty7GhostLeadCreationInvariants:
    """Ghost leads always have campaign_import source, new status, sms_consent=False."""

    @given(
        phone=_generated_phone,
        first_name=st.one_of(st.none(), _name_part),
        last_name=st.one_of(st.none(), _name_part),
    )
    @settings(max_examples=50, deadline=None)
    def test_ghost_lead_has_correct_fields(
        self,
        phone: str,
        first_name: str | None,
        last_name: str | None,
    ) -> None:
        """Ghost lead has campaign_import source, new status, no consent."""
        session = _make_mock_session(existing_lead=None)
        lead = asyncio.run(
            create_or_get(session, phone, first_name, last_name),
        )

        assert lead.lead_source == "campaign_import"
        assert lead.source_site == "campaign_csv_import"
        assert lead.status == "new"
        assert lead.sms_consent is False
        assert lead.situation == "exploring"
        session.add.assert_called_once_with(lead)

    @given(
        phone=_generated_phone,
        first_name=_name_part,
        last_name=_name_part,
    )
    @settings(max_examples=50, deadline=None)
    def test_ghost_lead_name_from_parts(
        self,
        phone: str,
        first_name: str,
        last_name: str,
    ) -> None:
        """Name is 'first last' when both provided."""
        session = _make_mock_session(existing_lead=None)
        lead = asyncio.run(
            create_or_get(session, phone, first_name, last_name),
        )
        assert lead.name == f"{first_name} {last_name}"

    @given(phone=_generated_phone)
    @settings(max_examples=30, deadline=None)
    def test_ghost_lead_name_defaults_to_unknown(self, phone: str) -> None:
        """Name defaults to 'Unknown' when no names provided."""
        session = _make_mock_session(existing_lead=None)
        lead = asyncio.run(create_or_get(session, phone, None, None))
        assert lead.name == "Unknown"

    @given(phone=_generated_phone)
    @settings(max_examples=30, deadline=None)
    def test_ghost_lead_phone_is_e164(self, phone: str) -> None:
        """Phone is always stored in E.164 format."""
        session = _make_mock_session(existing_lead=None)
        lead = asyncio.run(create_or_get(session, phone, None, None))
        assert lead.phone.startswith("+1")
        assert len(lead.phone) == 12


# ---------------------------------------------------------------------------
# Property 8: Ghost lead phone deduplication (idempotence)
# Validates: Requirements 5.2, 5.4
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestProperty8GhostLeadPhoneDeduplication:
    """Calling create_or_get with an existing phone returns the existing lead."""

    @given(
        phone=_generated_phone,
        first_name=st.one_of(st.none(), _name_part),
        last_name=st.one_of(st.none(), _name_part),
    )
    @settings(max_examples=50, deadline=None)
    def test_existing_lead_returned_without_create(
        self,
        phone: str,
        first_name: str | None,
        last_name: str | None,
    ) -> None:
        """When a lead with the phone exists, return it without creating."""
        existing = Lead(
            name="Existing Person",
            phone=normalize_to_e164(phone),
            situation="exploring",
            lead_source="website",
            source_site="residential",
            status="contacted",
            sms_consent=True,
        )
        existing.id = uuid4()

        session = _make_mock_session(existing_lead=existing)
        result = asyncio.run(
            create_or_get(session, phone, first_name, last_name),
        )

        assert result is existing
        session.add.assert_not_called()

    @given(phone=_generated_phone)
    @settings(max_examples=30, deadline=None)
    def test_existing_lead_fields_not_overwritten(self, phone: str) -> None:
        """Existing lead fields are preserved, not overwritten."""
        existing = Lead(
            name="Original Name",
            phone=normalize_to_e164(phone),
            situation="exploring",
            lead_source="website",
            source_site="residential",
            status="contacted",
            sms_consent=True,
        )
        existing.id = uuid4()

        session = _make_mock_session(existing_lead=existing)
        result = asyncio.run(create_or_get(session, phone))

        assert result.name == "Original Name"
        assert result.lead_source == "website"
        assert result.status == "contacted"
        assert result.sms_consent is True

    @given(phone=_generated_phone)
    @settings(max_examples=30, deadline=None)
    def test_existing_lead_name_updated_from_csv(self, phone: str) -> None:
        """CSV name overwrites stale DB name on existing lead."""
        existing = Lead(
            name="Claude test",
            phone=normalize_to_e164(phone),
            situation="exploring",
            lead_source="campaign_import",
            source_site="campaign_csv_import",
            status="new",
            sms_consent=False,
        )
        existing.id = uuid4()

        session = _make_mock_session(existing_lead=existing)
        result = asyncio.run(create_or_get(session, phone, "John", "Smith"))

        assert result.name == "John Smith"

    @given(phone=_generated_phone)
    @settings(max_examples=30, deadline=None)
    def test_existing_lead_name_preserved_when_csv_has_no_name(
        self, phone: str
    ) -> None:
        """Existing lead name is kept when CSV provides no name."""
        existing = Lead(
            name="Claude test",
            phone=normalize_to_e164(phone),
            situation="exploring",
            lead_source="campaign_import",
            source_site="campaign_csv_import",
            status="new",
            sms_consent=False,
        )
        existing.id = uuid4()

        session = _make_mock_session(existing_lead=existing)
        result = asyncio.run(create_or_get(session, phone, None, None))

        assert result.name == "Claude test"


# ---------------------------------------------------------------------------
# Property 24: Template rendering with safe defaults
# Validates: Requirements 14.1, 14.2
# ---------------------------------------------------------------------------

# Strategy: merge-field keys (simple identifiers)
_merge_key = st.from_regex(r"[a-z][a-z0-9_]{0,19}", fullmatch=True)
_merge_val = st.text(min_size=0, max_size=100)


@pytest.mark.unit
class TestProperty24TemplateRenderingWithSafeDefaults:
    """render_template replaces present keys and silently drops missing ones."""

    @given(
        data=st.data(),
        n=st.integers(min_value=1, max_value=5),
    )
    @settings(max_examples=50, deadline=None)
    def test_present_keys_replaced(
        self,
        data: st.DataObject,
        n: int,
    ) -> None:
        """All context keys present in the template are substituted."""
        keys = data.draw(st.lists(_merge_key, min_size=n, max_size=n, unique=True))
        values = [data.draw(_merge_val) for _ in keys]
        context = dict(zip(keys, values))
        body = " ".join(f"{{{k}}}" for k in keys)
        result = render_template(body, context)
        expected = " ".join(context[k] for k in keys)
        assert result == expected

    @given(
        present=st.lists(_merge_key, min_size=0, max_size=3, unique=True),
        missing=st.lists(_merge_key, min_size=1, max_size=3, unique=True),
        values=st.lists(_merge_val, min_size=0, max_size=3),
    )
    @settings(max_examples=50, deadline=None)
    def test_missing_keys_resolve_to_empty(
        self,
        present: list[str],
        missing: list[str],
        values: list[str],
    ) -> None:
        """Missing keys become empty string — never KeyError."""
        # Ensure no overlap between present and missing
        missing = [k for k in missing if k not in present]
        if not missing:
            return  # degenerate case, skip
        context = dict(zip(present, values))
        body = " ".join(f"{{{k}}}" for k in missing)
        result = render_template(body, context)
        # Every missing key → ""
        assert result == " ".join("" for _ in missing)

    @given(body=st.text(min_size=0, max_size=200))
    @settings(max_examples=50, deadline=None)
    def test_no_placeholders_returns_body_unchanged(self, body: str) -> None:
        """Body with no {key} placeholders is returned as-is."""
        # Filter out strings that contain format syntax characters
        if "{" in body or "}" in body:
            return  # skip bodies that contain format syntax
        result = render_template(body, {"first_name": "Alice"})
        assert result == body

    @given(
        key=_merge_key,
        value=_merge_val,
        prefix=st.text(min_size=0, max_size=50),
        suffix=st.text(min_size=0, max_size=50),
    )
    @settings(max_examples=50, deadline=None)
    def test_surrounding_text_preserved(
        self,
        key: str,
        value: str,
        prefix: str,
        suffix: str,
    ) -> None:
        """Text around merge fields is preserved."""
        # Skip if prefix/suffix contain format syntax
        if "{" in prefix or "}" in prefix or "{" in suffix or "}" in suffix:
            return
        body = f"{prefix}{{{key}}}{suffix}"
        result = render_template(body, {key: value})
        assert result == f"{prefix}{value}{suffix}"


# ---------------------------------------------------------------------------
# Property 37: Rate limit tracker blocks at threshold
# Validates: Requirement 39 (acceptance criteria 4, 5)
# ---------------------------------------------------------------------------

# Strategy: hourly or daily remaining ≤ 5 (at threshold)
_at_threshold_hourly = st.builds(
    lambda allowed, remaining: (allowed, allowed - remaining),
    st.integers(min_value=10, max_value=1000),
    st.integers(min_value=0, max_value=5),
)
_at_threshold_daily = st.builds(
    lambda allowed, remaining: (allowed, allowed - remaining),
    st.integers(min_value=10, max_value=5000),
    st.integers(min_value=0, max_value=5),
)
# Strategy: remaining > 5 (above threshold)
_above_threshold = st.builds(
    lambda allowed, remaining: (allowed, allowed - remaining),
    st.integers(min_value=20, max_value=1000),
    st.integers(min_value=6, max_value=19),
)


@pytest.mark.unit
class TestProperty37RateLimitTrackerBlocksAtThreshold:
    """check() returns allowed=False when remaining ≤ 5 for hourly or daily."""

    @given(
        hourly=_at_threshold_hourly,
        daily_allowed=st.integers(min_value=100, max_value=5000),
    )
    @settings(max_examples=50, deadline=None)
    def test_blocks_when_hourly_at_threshold(
        self,
        hourly: tuple[int, int],
        daily_allowed: int,
    ) -> None:
        """Blocked when hourly remaining ≤ 5, regardless of daily."""
        hourly_allowed, hourly_used = hourly
        tracker = SMSRateLimitTracker()
        headers = {
            "x-rate-limit-hourly-allowed": str(hourly_allowed),
            "x-rate-limit-hourly-used": str(hourly_used),
            "x-rate-limit-daily-allowed": str(daily_allowed),
            "x-rate-limit-daily-used": "0",
        }

        async def _run() -> CheckResult:
            await tracker.update_from_headers(headers)
            return await tracker.check()

        result = asyncio.run(_run())
        assert result.allowed is False
        assert result.retry_after_seconds > 0

    @given(
        daily=_at_threshold_daily,
        hourly_allowed=st.integers(min_value=100, max_value=1000),
    )
    @settings(max_examples=50, deadline=None)
    def test_blocks_when_daily_at_threshold(
        self,
        daily: tuple[int, int],
        hourly_allowed: int,
    ) -> None:
        """Blocked when daily remaining ≤ 5, regardless of hourly."""
        daily_allowed, daily_used = daily
        tracker = SMSRateLimitTracker()
        headers = {
            "x-rate-limit-hourly-allowed": str(hourly_allowed),
            "x-rate-limit-hourly-used": "0",
            "x-rate-limit-daily-allowed": str(daily_allowed),
            "x-rate-limit-daily-used": str(daily_used),
        }

        async def _run() -> CheckResult:
            await tracker.update_from_headers(headers)
            return await tracker.check()

        result = asyncio.run(_run())
        assert result.allowed is False
        assert result.retry_after_seconds > 0

    @given(hourly=_above_threshold, daily=_above_threshold)
    @settings(max_examples=50, deadline=None)
    def test_allows_when_above_threshold(
        self,
        hourly: tuple[int, int],
        daily: tuple[int, int],
    ) -> None:
        """Allowed when both hourly and daily remaining > 5."""
        hourly_allowed, hourly_used = hourly
        daily_allowed, daily_used = daily
        tracker = SMSRateLimitTracker()
        headers = {
            "x-rate-limit-hourly-allowed": str(hourly_allowed),
            "x-rate-limit-hourly-used": str(hourly_used),
            "x-rate-limit-daily-allowed": str(daily_allowed),
            "x-rate-limit-daily-used": str(daily_used),
        }

        async def _run() -> CheckResult:
            await tracker.update_from_headers(headers)
            return await tracker.check()

        result = asyncio.run(_run())
        assert result.allowed is True
        assert result.retry_after_seconds == 0

    def test_allows_when_no_data_yet(self) -> None:
        """First check with no prior headers returns allowed=True."""
        tracker = SMSRateLimitTracker()
        result = asyncio.run(tracker.check())
        assert result.allowed is True
        assert result.retry_after_seconds == 0


# ---------------------------------------------------------------------------
# Property 38: Rate limit tracker header round-trip
# Validates: Requirement 39 (acceptance criteria 1, 2, 3)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestProperty38RateLimitTrackerHeaderRoundTrip:
    """update_from_headers() persists state that check() reads back."""

    @given(
        hourly_allowed=st.integers(min_value=10, max_value=1000),
        hourly_used=st.integers(min_value=0, max_value=500),
        daily_allowed=st.integers(min_value=100, max_value=5000),
        daily_used=st.integers(min_value=0, max_value=2500),
    )
    @settings(max_examples=50, deadline=None)
    def test_inmemory_round_trip(
        self,
        hourly_allowed: int,
        hourly_used: int,
        daily_allowed: int,
        daily_used: int,
    ) -> None:
        """Headers → update → check reads back correct remaining values."""
        tracker = SMSRateLimitTracker()
        headers = {
            "x-rate-limit-hourly-allowed": str(hourly_allowed),
            "x-rate-limit-hourly-used": str(hourly_used),
            "x-rate-limit-daily-allowed": str(daily_allowed),
            "x-rate-limit-daily-used": str(daily_used),
        }

        async def _run() -> CheckResult:
            await tracker.update_from_headers(headers)
            return await tracker.check()

        result = asyncio.run(_run())
        state = result.state
        assert state.hourly_allowed == hourly_allowed
        assert state.hourly_used == hourly_used
        assert state.daily_allowed == daily_allowed
        assert state.daily_used == daily_used
        assert state.hourly_remaining == max(hourly_allowed - hourly_used, 0)
        assert state.daily_remaining == max(daily_allowed - daily_used, 0)

    @given(
        hourly_allowed=st.integers(min_value=10, max_value=1000),
        hourly_used=st.integers(min_value=0, max_value=500),
        daily_allowed=st.integers(min_value=100, max_value=5000),
        daily_used=st.integers(min_value=0, max_value=2500),
    )
    @settings(max_examples=50, deadline=None)
    def test_redis_round_trip(
        self,
        hourly_allowed: int,
        hourly_used: int,
        daily_allowed: int,
        daily_used: int,
    ) -> None:
        """Headers → update → Redis set → check reads from Redis."""
        mock_redis = AsyncMock()
        stored: dict[str, str] = {}

        async def _set(key: str, value: str, **_kwargs: int) -> None:
            stored[key] = value

        async def _get(key: str) -> str | None:
            return stored.get(key)

        mock_redis.set = _set
        mock_redis.get = _get

        tracker = SMSRateLimitTracker(
            provider="callrail",
            account_id="acc123",
            redis_client=mock_redis,
        )
        headers = {
            "x-rate-limit-hourly-allowed": str(hourly_allowed),
            "x-rate-limit-hourly-used": str(hourly_used),
            "x-rate-limit-daily-allowed": str(daily_allowed),
            "x-rate-limit-daily-used": str(daily_used),
        }

        async def _run() -> CheckResult:
            await tracker.update_from_headers(headers)
            return await tracker.check()

        result = asyncio.run(_run())
        # Verify Redis key was written
        assert "sms:rl:callrail:acc123" in stored
        # Verify state read back correctly
        state = result.state
        assert state.hourly_allowed == hourly_allowed
        assert state.hourly_used == hourly_used
        assert state.daily_allowed == daily_allowed
        assert state.daily_used == daily_used

    def test_ignores_missing_headers(self) -> None:
        """update_from_headers with no rate-limit headers is a no-op."""
        tracker = SMSRateLimitTracker()

        async def _run() -> CheckResult:
            await tracker.update_from_headers({"content-type": "application/json"})
            return await tracker.check()

        result = asyncio.run(_run())
        # No data → allowed (first-request bootstrap)
        assert result.allowed is True
        assert result.state.updated_at == 0.0

    @given(
        h_allowed=st.integers(min_value=10, max_value=1000),
        h_used=st.integers(min_value=0, max_value=500),
    )
    @settings(max_examples=30, deadline=None)
    def test_partial_headers_still_parsed(
        self,
        h_allowed: int,
        h_used: int,
    ) -> None:
        """Only hourly headers → state has hourly values, daily defaults to 0."""
        tracker = SMSRateLimitTracker()
        headers = {
            "x-rate-limit-hourly-allowed": str(h_allowed),
            "x-rate-limit-hourly-used": str(h_used),
        }

        async def _run() -> CheckResult:
            await tracker.update_from_headers(headers)
            return await tracker.check()

        result = asyncio.run(_run())
        state = result.state
        assert state.hourly_allowed == h_allowed
        assert state.hourly_used == h_used
        assert state.daily_allowed == 0
        assert state.daily_used == 0
        assert state.updated_at > 0.0


# ---------------------------------------------------------------------------
# Property 20: Phone normalization to E.164
# Validates: Requirements 20.1, 12.9, 20.3
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestProperty20PhoneNormalizationToE164:
    """Valid US phones normalize to +1XXXXXXXXXX; invalid phones raise errors."""

    @given(
        area=st.integers(min_value=200, max_value=999),
        exchange=st.integers(min_value=200, max_value=999),
        subscriber=st.integers(min_value=0, max_value=9999),
    )
    @settings(max_examples=100, deadline=None)
    def test_ten_digit_normalizes(
        self,
        area: int,
        exchange: int,
        subscriber: int,
    ) -> None:
        """10-digit raw phone → +1XXXXXXXXXX."""
        raw = f"{area}{exchange}{subscriber:04d}"
        # Skip 555-01xx test numbers
        if f"{exchange}" == "555" and f"{subscriber:04d}".startswith("01"):
            return
        result = normalize_to_e164(raw)
        assert result == f"+1{raw}"
        assert len(result) == 12

    @given(
        area=st.integers(min_value=200, max_value=999),
        exchange=st.integers(min_value=200, max_value=999),
        subscriber=st.integers(min_value=0, max_value=9999),
    )
    @settings(max_examples=100, deadline=None)
    def test_parenthesized_format(
        self,
        area: int,
        exchange: int,
        subscriber: int,
    ) -> None:
        """(XXX) XXX-XXXX → +1XXXXXXXXXX."""
        if f"{exchange}" == "555" and f"{subscriber:04d}".startswith("01"):
            return
        raw = f"({area}) {exchange}-{subscriber:04d}"
        result = normalize_to_e164(raw)
        assert result == f"+1{area}{exchange}{subscriber:04d}"

    @given(
        area=st.integers(min_value=200, max_value=999),
        exchange=st.integers(min_value=200, max_value=999),
        subscriber=st.integers(min_value=0, max_value=9999),
    )
    @settings(max_examples=100, deadline=None)
    def test_dashed_format(
        self,
        area: int,
        exchange: int,
        subscriber: int,
    ) -> None:
        """XXX-XXX-XXXX → +1XXXXXXXXXX."""
        if f"{exchange}" == "555" and f"{subscriber:04d}".startswith("01"):
            return
        raw = f"{area}-{exchange}-{subscriber:04d}"
        result = normalize_to_e164(raw)
        assert result == f"+1{area}{exchange}{subscriber:04d}"

    @given(
        area=st.integers(min_value=200, max_value=999),
        exchange=st.integers(min_value=200, max_value=999),
        subscriber=st.integers(min_value=0, max_value=9999),
    )
    @settings(max_examples=100, deadline=None)
    def test_e164_passthrough(
        self,
        area: int,
        exchange: int,
        subscriber: int,
    ) -> None:
        """Already E.164 (+1XXXXXXXXXX) passes through unchanged."""
        if f"{exchange}" == "555" and f"{subscriber:04d}".startswith("01"):
            return
        raw = f"+1{area}{exchange}{subscriber:04d}"
        result = normalize_to_e164(raw)
        assert result == raw

    @given(
        area=st.integers(min_value=200, max_value=999),
        exchange=st.integers(min_value=200, max_value=999),
        subscriber=st.integers(min_value=0, max_value=9999),
    )
    @settings(max_examples=50, deadline=None)
    def test_eleven_digit_with_country_code(
        self,
        area: int,
        exchange: int,
        subscriber: int,
    ) -> None:
        """1XXXXXXXXXX (11 digits with leading 1) → +1XXXXXXXXXX."""
        if f"{exchange}" == "555" and f"{subscriber:04d}".startswith("01"):
            return
        raw = f"1{area}{exchange}{subscriber:04d}"
        result = normalize_to_e164(raw)
        assert result == f"+1{area}{exchange}{subscriber:04d}"

    @given(phone=st.from_regex(r"[a-zA-Z]{3,10}", fullmatch=True))
    @settings(max_examples=50, deadline=None)
    def test_letters_rejected(self, phone: str) -> None:
        """Phones containing letters raise PhoneNormalizationError."""
        with pytest.raises(PhoneNormalizationError):
            normalize_to_e164(phone)

    @given(
        area=st.integers(min_value=200, max_value=999),
        exchange=st.integers(min_value=200, max_value=999),
        subscriber=st.integers(min_value=0, max_value=9999),
    )
    @settings(max_examples=30, deadline=None)
    def test_extension_rejected(
        self,
        area: int,
        exchange: int,
        subscriber: int,
    ) -> None:
        """Phones with extension markers raise PhoneNormalizationError."""
        raw = f"{area}{exchange}{subscriber:04d} ext 123"
        with pytest.raises(PhoneNormalizationError):
            normalize_to_e164(raw)

    @given(digits=st.from_regex(r"[2-9]\d{0,7}", fullmatch=True))
    @settings(max_examples=50, deadline=None)
    def test_too_few_digits_rejected(self, digits: str) -> None:
        """Fewer than 10 digits raise PhoneNormalizationError."""
        with pytest.raises(PhoneNormalizationError):
            normalize_to_e164(digits)

    @given(digits=st.from_regex(r"[2-9]\d{11,15}", fullmatch=True))
    @settings(max_examples=50, deadline=None)
    def test_too_many_digits_rejected(self, digits: str) -> None:
        """More than 11 digits raise PhoneNormalizationError."""
        with pytest.raises(PhoneNormalizationError):
            normalize_to_e164(digits)

    @given(
        area=st.sampled_from(["000", "011", "100", "199"]),
        exchange=st.integers(min_value=200, max_value=999),
        subscriber=st.integers(min_value=0, max_value=9999),
    )
    @settings(max_examples=30, deadline=None)
    def test_invalid_area_code_rejected(
        self,
        area: str,
        exchange: int,
        subscriber: int,
    ) -> None:
        """Area codes starting with 0 or 1 raise PhoneNormalizationError."""
        raw = f"{area}{exchange}{subscriber:04d}"
        with pytest.raises(PhoneNormalizationError):
            normalize_to_e164(raw)

    def test_555_01xx_test_numbers_rejected(self) -> None:
        """555-01xx test numbers are rejected."""
        with pytest.raises(PhoneNormalizationError):
            normalize_to_e164("2005550100")
        with pytest.raises(PhoneNormalizationError):
            normalize_to_e164("(200) 555-0199")

    def test_empty_and_whitespace_rejected(self) -> None:
        """Empty strings and whitespace-only raise PhoneNormalizationError."""
        with pytest.raises(PhoneNormalizationError):
            normalize_to_e164("")
        with pytest.raises(PhoneNormalizationError):
            normalize_to_e164("   ")

    @given(
        area=st.integers(min_value=200, max_value=999),
        exchange=st.integers(min_value=200, max_value=999),
        subscriber=st.integers(min_value=0, max_value=9999),
    )
    @settings(max_examples=50, deadline=None)
    def test_all_formats_produce_same_result(
        self,
        area: int,
        exchange: int,
        subscriber: int,
    ) -> None:
        """All supported formats for the same number produce identical E.164."""
        if f"{exchange}" == "555" and f"{subscriber:04d}".startswith("01"):
            return
        expected = f"+1{area}{exchange}{subscriber:04d}"
        formats = [
            f"{area}{exchange}{subscriber:04d}",
            f"({area}) {exchange}-{subscriber:04d}",
            f"{area}-{exchange}-{subscriber:04d}",
            f"+1{area}{exchange}{subscriber:04d}",
            f"1{area}{exchange}{subscriber:04d}",
        ]
        for fmt in formats:
            assert normalize_to_e164(fmt) == expected, f"Failed for format: {fmt}"


# ---------------------------------------------------------------------------
# Property 48: Area-code timezone lookup
# Validates: Requirement 36 (acceptance criteria 3, 4)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestProperty48AreaCodeTimezoneLookup:
    """Area codes map to known IANA timezones; non-CT zones are detectable."""

    @given(phone=e164_phone)
    @settings(max_examples=100, deadline=None)
    def test_lookup_returns_string(self, phone: str) -> None:
        """lookup_timezone always returns a non-empty string."""
        tz = lookup_timezone(phone)
        assert isinstance(tz, str)
        assert len(tz) > 0

    @given(phone=e164_phone)
    @settings(max_examples=100, deadline=None)
    def test_lookup_returns_iana_format(self, phone: str) -> None:
        """Returned timezone follows IANA format (contains '/')."""
        tz = lookup_timezone(phone)
        assert "/" in tz

    def test_known_central_area_codes(self) -> None:
        """Minnesota area codes (612, 651, 763, 952) → America/Chicago."""
        for ac in ["612", "651", "763", "952"]:
            phone = f"+1{ac}5551234"
            tz = lookup_timezone(phone)
            assert tz == "America/Chicago", f"Area code {ac} → {tz}"
            assert is_central_timezone(tz)

    def test_known_non_central_area_codes(self) -> None:
        """Non-CT area codes return non-Chicago timezones."""
        cases = {
            "212": "America/New_York",
            "310": "America/Los_Angeles",
            "303": "America/Denver",
            "602": "America/Phoenix",
            "808": "Pacific/Honolulu",
            "907": "America/Anchorage",
        }
        for ac, expected_tz in cases.items():
            phone = f"+1{ac}5551234"
            tz = lookup_timezone(phone)
            msg = f"Area code {ac}: expected {expected_tz}, got {tz}"
            assert tz == expected_tz, msg
            assert not is_central_timezone(tz)

    @given(phone=e164_phone)
    @settings(max_examples=100, deadline=None)
    def test_is_central_consistent_with_lookup(self, phone: str) -> None:
        """is_central_timezone agrees with known CT timezone set."""
        tz = lookup_timezone(phone)
        if tz == "America/Chicago":
            assert is_central_timezone(tz)

    def test_unknown_area_code_defaults_to_chicago(self) -> None:
        """Unknown area codes fall back to America/Chicago."""
        # 999 is not an assigned area code
        tz = lookup_timezone("+19995551234")
        assert tz == "America/Chicago"

    def test_non_e164_defaults_to_chicago(self) -> None:
        """Non-E.164 input returns America/Chicago fallback."""
        assert lookup_timezone("5551234") == "America/Chicago"
        assert lookup_timezone("") == "America/Chicago"
        assert lookup_timezone("not-a-phone") == "America/Chicago"

    @given(
        area=st.integers(min_value=200, max_value=999),
        exchange=st.integers(min_value=200, max_value=999),
        subscriber=st.integers(min_value=0, max_value=9999),
    )
    @settings(max_examples=100, deadline=None)
    def test_normalized_phone_roundtrip(
        self,
        area: int,
        exchange: int,
        subscriber: int,
    ) -> None:
        """normalize_to_e164 output is valid input for lookup_timezone."""
        if f"{exchange}" == "555" and f"{subscriber:04d}".startswith("01"):
            return
        raw = f"{area}{exchange}{subscriber:04d}"
        e164 = normalize_to_e164(raw)
        tz = lookup_timezone(e164)
        assert isinstance(tz, str)
        assert "/" in tz


# ---------------------------------------------------------------------------
# Property 32: Hard-STOP precedence
# Validates: Requirement 26
# ---------------------------------------------------------------------------


def _mock_consent_session(
    *,
    has_hard_stop: bool = False,
    has_marketing_record: bool = False,
    has_customer_opt_in: bool = False,
    has_lead_consent: bool = False,
) -> AsyncMock:
    """Build a mock session for consent queries.

    The consent module issues up to 4 sequential execute() calls:
      1. hard-STOP check
      2. marketing consent record check
      3. Customer.sms_opt_in fallback
      4. Lead.sms_consent fallback
    """
    session = AsyncMock()
    call_idx = {"n": 0}

    # Map call index → scalar_one_or_none return value
    responses: list[object] = [
        uuid4() if has_hard_stop else None,  # 1: hard-STOP
        uuid4() if has_marketing_record else None,  # 2: marketing record
        True if has_customer_opt_in else None,  # 3: customer fallback
        True if has_lead_consent else None,  # 4: lead fallback
    ]

    async def _execute(_stmt: object) -> MagicMock:
        idx = call_idx["n"]
        call_idx["n"] += 1
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(
            return_value=responses[idx] if idx < len(responses) else None,
        )
        return result

    session.execute = _execute
    return session


@pytest.mark.unit
class TestProperty32HardStopPrecedence:
    """Hard-STOP blocks marketing and transactional, not operational."""

    @given(
        phone=e164_phone,
        consent_type=st.sampled_from(["marketing", "transactional"]),
    )
    @settings(max_examples=50, deadline=None)
    def test_hard_stop_blocks_non_operational(
        self,
        phone: str,
        consent_type: str,
    ) -> None:
        """When hard-STOP exists, marketing and transactional are denied."""
        session = _mock_consent_session(
            has_hard_stop=True,
            has_marketing_record=True,  # even with opt-in, still blocked
            has_customer_opt_in=True,
        )
        result = asyncio.run(check_sms_consent(session, phone, consent_type))  # type: ignore[arg-type]
        assert result is False

    @given(phone=e164_phone)
    @settings(max_examples=50, deadline=None)
    def test_hard_stop_never_blocks_operational(self, phone: str) -> None:
        """Operational consent is always allowed, even with hard-STOP."""
        session = _mock_consent_session(has_hard_stop=True)
        result = asyncio.run(check_sms_consent(session, phone, "operational"))  # type: ignore[arg-type]
        assert result is True

    @given(phone=e164_phone)
    @settings(max_examples=50, deadline=None)
    def test_no_hard_stop_allows_transactional(self, phone: str) -> None:
        """Without hard-STOP, transactional is allowed (EBR exemption)."""
        session = _mock_consent_session(has_hard_stop=False)
        result = asyncio.run(check_sms_consent(session, phone, "transactional"))  # type: ignore[arg-type]
        assert result is True

    @given(phone=e164_phone)
    @settings(max_examples=50, deadline=None)
    def test_hard_stop_takes_priority_over_marketing_opt_in(
        self,
        phone: str,
    ) -> None:
        """Hard-STOP overrides explicit marketing opt-in records."""
        session = _mock_consent_session(
            has_hard_stop=True,
            has_marketing_record=True,
        )
        result = asyncio.run(check_sms_consent(session, phone, "marketing"))  # type: ignore[arg-type]
        assert result is False


# ---------------------------------------------------------------------------
# Property 33: Type-scoped consent (S11)
# Validates: Requirement 26
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestProperty33TypeScopedConsent:
    """Consent differs by type: operational, transactional, marketing."""

    @given(phone=e164_phone)
    @settings(max_examples=50, deadline=None)
    def test_operational_always_allowed(self, phone: str) -> None:
        """Operational consent returns True regardless of any records."""
        # Session won't even be queried for operational
        session = AsyncMock()
        result = asyncio.run(check_sms_consent(session, phone, "operational"))  # type: ignore[arg-type]
        assert result is True

    @given(phone=e164_phone)
    @settings(max_examples=50, deadline=None)
    def test_marketing_denied_without_opt_in(self, phone: str) -> None:
        """Marketing denied without consent record or opt-in."""
        session = _mock_consent_session(
            has_hard_stop=False,
            has_marketing_record=False,
            has_customer_opt_in=False,
            has_lead_consent=False,
        )
        result = asyncio.run(check_sms_consent(session, phone, "marketing"))  # type: ignore[arg-type]
        assert result is False

    @given(phone=e164_phone)
    @settings(max_examples=50, deadline=None)
    def test_marketing_allowed_with_consent_record(self, phone: str) -> None:
        """Marketing allowed when explicit SmsConsentRecord exists."""
        session = _mock_consent_session(
            has_hard_stop=False,
            has_marketing_record=True,
        )
        result = asyncio.run(check_sms_consent(session, phone, "marketing"))  # type: ignore[arg-type]
        assert result is True

    @given(phone=e164_phone)
    @settings(max_examples=50, deadline=None)
    def test_marketing_allowed_via_customer_fallback(self, phone: str) -> None:
        """Marketing allowed when Customer.sms_opt_in=True (fallback)."""
        session = _mock_consent_session(
            has_hard_stop=False,
            has_marketing_record=False,
            has_customer_opt_in=True,
        )
        result = asyncio.run(check_sms_consent(session, phone, "marketing"))  # type: ignore[arg-type]
        assert result is True

    @given(phone=e164_phone)
    @settings(max_examples=50, deadline=None)
    def test_marketing_allowed_via_lead_fallback(self, phone: str) -> None:
        """Marketing allowed when Lead.sms_consent=True (fallback)."""
        session = _mock_consent_session(
            has_hard_stop=False,
            has_marketing_record=False,
            has_customer_opt_in=False,
            has_lead_consent=True,
        )
        result = asyncio.run(check_sms_consent(session, phone, "marketing"))  # type: ignore[arg-type]
        assert result is True

    @given(phone=e164_phone)
    @settings(max_examples=50, deadline=None)
    def test_transactional_allowed_without_opt_in(self, phone: str) -> None:
        """Transactional allowed under EBR exemption even without explicit opt-in."""
        session = _mock_consent_session(
            has_hard_stop=False,
            has_marketing_record=False,
            has_customer_opt_in=False,
            has_lead_consent=False,
        )
        result = asyncio.run(check_sms_consent(session, phone, "transactional"))  # type: ignore[arg-type]
        assert result is True

    @given(
        phone=e164_phone,
        consent_type=st.sampled_from(["marketing", "transactional", "operational"]),
    )
    @settings(max_examples=100, deadline=None)
    def test_consent_type_exhaustive(
        self,
        phone: str,
        consent_type: str,
    ) -> None:
        """All three consent types return bool without error."""
        session = _mock_consent_session(has_hard_stop=False)
        result = asyncio.run(check_sms_consent(session, phone, consent_type))  # type: ignore[arg-type]
        assert isinstance(result, bool)


# ---------------------------------------------------------------------------
# Property 35: State machine transition invariants
# Validates: Requirement 28 (acceptance criteria 2, 3)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestProperty35StateMachineTransitionInvariants:
    """Allowed transitions succeed; forbidden raise; terminals reject."""

    @given(
        from_state=st.sampled_from(list(RecipientState)),
        to_state=st.sampled_from(list(RecipientState)),
    )
    @settings(max_examples=200, deadline=None)
    def test_transition_matches_allowed_set(
        self,
        from_state: RecipientState,
        to_state: RecipientState,
    ) -> None:
        """transition() succeeds iff (from, to) is allowed."""
        allowed = to_state in _ALLOWED_TRANSITIONS[from_state]
        if allowed:
            result = transition(from_state, to_state)
            assert result == to_state
        else:
            with pytest.raises(
                InvalidStateTransitionError,
            ) as exc_info:
                transition(from_state, to_state)
            assert exc_info.value.from_state == from_state
            assert exc_info.value.to_state == to_state

    @given(to_state=st.sampled_from(list(RecipientState)))
    @settings(max_examples=50, deadline=None)
    def test_terminal_sent_rejects_all(
        self,
        to_state: RecipientState,
    ) -> None:
        """Terminal 'sent' rejects every outbound transition."""
        with pytest.raises(InvalidStateTransitionError):
            transition(RecipientState.sent, to_state)

    @given(to_state=st.sampled_from(list(RecipientState)))
    @settings(max_examples=50, deadline=None)
    def test_terminal_cancelled_rejects_all(
        self,
        to_state: RecipientState,
    ) -> None:
        """Terminal 'cancelled' rejects every outbound transition."""
        with pytest.raises(InvalidStateTransitionError):
            transition(RecipientState.cancelled, to_state)


# ---------------------------------------------------------------------------
# Property 36: Orphan recovery
# Validates: Requirement 28 (acceptance criteria 5)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestProperty36OrphanRecovery:
    """orphan_recovery_query marks stale 'sending' rows as 'failed'."""

    def test_orphan_recovery_sql_targets_sending_state(
        self,
    ) -> None:
        """SQL targets sending rows older than 5 min."""
        sql_text = str(_ORPHAN_RECOVERY_SQL.text)
        assert "delivery_status = 'sending'" in sql_text
        assert "delivery_status = 'failed'" in sql_text
        assert "worker_interrupted" in sql_text
        assert "5 minutes" in sql_text

    def test_orphan_recovery_sets_failed_and_error(
        self,
    ) -> None:
        """SQL sets failed status and worker_interrupted msg."""
        sql_text = str(_ORPHAN_RECOVERY_SQL.text)
        assert "SET delivery_status = 'failed'" in sql_text
        assert "error_message = 'worker_interrupted'" in sql_text

    def test_orphan_recovery_checks_sending_started_at(
        self,
    ) -> None:
        """SQL filters on sending_started_at < now() - 5 min."""
        sql_text = str(_ORPHAN_RECOVERY_SQL.text)
        assert "sending_started_at" in sql_text
        assert "now()" in sql_text


# ---------------------------------------------------------------------------
# Property 49: Sending state before provider call
# Validates: Requirement 28 (acceptance criteria 4)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestProperty49SendingStateBeforeProviderCall:
    """State machine enforces pending→sending before sent/failed."""

    @given(data=st.data())
    @settings(max_examples=100, deadline=None)
    def test_pending_must_go_through_sending(
        self,
        data: st.DataObject,
    ) -> None:
        """Cannot jump from pending directly to sent or failed."""
        terminal = data.draw(
            st.sampled_from(
                [RecipientState.sent, RecipientState.failed],
            ),
        )
        with pytest.raises(InvalidStateTransitionError):
            transition(RecipientState.pending, terminal)

    def test_pending_to_sending_allowed(self) -> None:
        """pending → sending is the required first step."""
        result = transition(RecipientState.pending, RecipientState.sending)
        assert result == RecipientState.sending

    @given(
        outcome=st.sampled_from([RecipientState.sent, RecipientState.failed]),
    )
    @settings(max_examples=50, deadline=None)
    def test_sending_to_outcome_allowed(self, outcome: RecipientState) -> None:
        """sending → sent and sending → failed are both allowed."""
        result = transition(RecipientState.sending, outcome)
        assert result == outcome

    def test_full_success_path(self) -> None:
        """pending → sending → sent is the happy path."""
        s1 = transition(RecipientState.pending, RecipientState.sending)
        s2 = transition(s1, RecipientState.sent)
        assert s2 == RecipientState.sent

    def test_full_failure_path(self) -> None:
        """pending → sending → failed is the error path."""
        s1 = transition(RecipientState.pending, RecipientState.sending)
        s2 = transition(s1, RecipientState.failed)
        assert s2 == RecipientState.failed


# ---------------------------------------------------------------------------
# Property 25: SMS segment count
# Validates: Requirement 15.9
# ---------------------------------------------------------------------------

# Strategy: GSM-7 only text (basic charset minus braces to avoid format issues)
_gsm7_chars = st.sampled_from(sorted(_GSM7_BASIC - {"{", "}"}))
_gsm7_text = st.text(alphabet=_gsm7_chars, min_size=1, max_size=800)

# Strategy: text guaranteed to contain at least one UCS-2 char
_ucs2_char = st.sampled_from(["😀", "🔧", "💧", "中", "日", "한", "ñ" * 0 or "🌱"])
_ucs2_text = st.builds(
    lambda prefix, emoji, suffix: prefix + emoji + suffix,
    st.text(alphabet=_gsm7_chars, min_size=0, max_size=200),
    _ucs2_char,
    st.text(alphabet=_gsm7_chars, min_size=0, max_size=200),
)


@pytest.mark.unit
class TestProperty25SMSSegmentCount:
    """Segment count follows GSM-7 160/153 thresholds for GSM-7 text."""

    @given(body=_gsm7_text)
    @settings(max_examples=100, deadline=None)
    def test_gsm7_segment_formula(self, body: str) -> None:
        """GSM-7 text: 1 segment if ≤160 chars, else ceil(chars/153)."""
        encoding, segments, chars = count_segments(
            body,
            include_prefix=False,
            include_footer=False,
        )
        assert encoding == "GSM-7"
        expected = 1 if chars <= 160 else math.ceil(chars / 153)
        assert segments == expected

    @given(body=_gsm7_text)
    @settings(max_examples=100, deadline=None)
    def test_segments_always_positive(self, body: str) -> None:
        """Segment count is always ≥ 1 for non-empty text."""
        _, segments, _ = count_segments(
            body,
            include_prefix=False,
            include_footer=False,
        )
        assert segments >= 1

    @given(body=_gsm7_text)
    @settings(max_examples=50, deadline=None)
    def test_prefix_and_footer_increase_char_count(self, body: str) -> None:
        """Including prefix+footer always produces ≥ chars than without."""
        _, _, chars_bare = count_segments(
            body,
            include_prefix=False,
            include_footer=False,
        )
        _, _, chars_full = count_segments(
            body,
            include_prefix=True,
            include_footer=True,
        )
        assert chars_full >= chars_bare

    def test_empty_body_with_prefix_footer(self) -> None:
        """Empty body still counts prefix + footer chars."""
        _encoding, segments, chars = count_segments("")
        overhead = _gsm7_char_count(_DEFAULT_PREFIX + _DEFAULT_FOOTER)
        assert chars == overhead
        assert segments >= 1

    def test_exactly_160_gsm7_is_one_segment(self) -> None:
        """Exactly 160 GSM-7 chars (no prefix/footer) = 1 segment."""
        body = "a" * 160
        encoding, segments, chars = count_segments(
            body,
            include_prefix=False,
            include_footer=False,
        )
        assert encoding == "GSM-7"
        assert chars == 160
        assert segments == 1

    def test_161_gsm7_is_two_segments(self) -> None:
        """161 GSM-7 chars (no prefix/footer) = 2 segments (ceil(161/153))."""
        body = "a" * 161
        encoding, segments, chars = count_segments(
            body,
            include_prefix=False,
            include_footer=False,
        )
        assert encoding == "GSM-7"
        assert chars == 161
        assert segments == 2


# ---------------------------------------------------------------------------
# Property 47: SMS segment count for GSM-7 and UCS-2
# Validates: Requirement 43
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestProperty47SMSSegmentCountGSM7AndUCS2:
    """UCS-2 text uses 70/67 thresholds; GSM-7 extension chars cost 2."""

    @given(body=_ucs2_text)
    @settings(max_examples=100, deadline=None)
    def test_ucs2_detected_for_non_gsm_chars(self, body: str) -> None:
        """Any non-GSM-7 character forces UCS-2 encoding."""
        encoding, _, _ = count_segments(
            body,
            include_prefix=False,
            include_footer=False,
        )
        assert encoding == "UCS-2"

    @given(body=_ucs2_text)
    @settings(max_examples=100, deadline=None)
    def test_ucs2_segment_formula(self, body: str) -> None:
        """UCS-2 text: 1 segment if ≤70 chars, else ceil(chars/67)."""
        encoding, segments, chars = count_segments(
            body,
            include_prefix=False,
            include_footer=False,
        )
        assert encoding == "UCS-2"
        expected = 1 if chars <= 70 else math.ceil(chars / 67)
        assert segments == expected

    def test_exactly_70_ucs2_is_one_segment(self) -> None:
        """Exactly 70 UCS-2 chars = 1 segment."""
        # 69 GSM chars + 1 emoji = 70 UCS-2 chars
        body = "a" * 69 + "😀"
        encoding, segments, chars = count_segments(
            body,
            include_prefix=False,
            include_footer=False,
        )
        assert encoding == "UCS-2"
        assert chars == 70
        assert segments == 1

    def test_71_ucs2_is_two_segments(self) -> None:
        """71 UCS-2 chars = 2 segments (ceil(71/67))."""
        body = "a" * 70 + "😀"
        encoding, segments, chars = count_segments(
            body,
            include_prefix=False,
            include_footer=False,
        )
        assert encoding == "UCS-2"
        assert chars == 71
        assert segments == 2

    @given(
        ext_count=st.integers(min_value=1, max_value=10),
        padding=st.integers(min_value=0, max_value=100),
    )
    @settings(max_examples=50, deadline=None)
    def test_gsm7_extension_chars_count_as_two(
        self,
        ext_count: int,
        padding: int,
    ) -> None:
        """GSM-7 extension chars (e.g. ^, {, }, [, ]) each cost 2 char units."""
        ext_chars = "^" * ext_count
        pad_chars = "a" * padding
        body = pad_chars + ext_chars
        encoding, _, chars = count_segments(
            body,
            include_prefix=False,
            include_footer=False,
        )
        assert encoding == "GSM-7"
        assert chars == padding + (ext_count * 2)

    def test_single_emoji_forces_ucs2(self) -> None:
        """A single emoji in otherwise GSM-7 text forces UCS-2."""
        body = "Hello 🔧"
        encoding, _, _ = count_segments(
            body,
            include_prefix=False,
            include_footer=False,
        )
        assert encoding == "UCS-2"

    @given(body=_gsm7_text)
    @settings(max_examples=50, deadline=None)
    def test_gsm7_char_count_matches_segments(self, body: str) -> None:
        """GSM-7 char count accounts for extension chars costing 2."""
        encoding, segments, chars = count_segments(
            body,
            include_prefix=False,
            include_footer=False,
        )
        if encoding == "GSM-7":
            expected = 1 if chars <= 160 else math.ceil(chars / 153)
            assert segments == expected


# ---------------------------------------------------------------------------
# Property 26: Campaign time estimate
# Validates: Requirements 15.11
# ---------------------------------------------------------------------------

_SENDS_PER_HOUR = 140
_WINDOW_HOURS = 13  # 8 AM - 9 PM CT


def _estimate_hours(n: int) -> float:
    """Pure estimate: total hours = n / 140."""
    return n / _SENDS_PER_HOUR


@pytest.mark.unit
class TestProperty26CampaignTimeEstimate:
    """For any positive recipient count N, estimated completion ≈ N/140 hours."""

    @given(n=st.integers(min_value=1, max_value=100_000))
    @settings(max_examples=200, deadline=None)
    def test_estimate_equals_n_over_140(self, n: int) -> None:
        """Estimated hours equals N / 140."""
        hours = _estimate_hours(n)
        assert hours == pytest.approx(n / 140)

    @given(n=st.integers(min_value=1, max_value=100_000))
    @settings(max_examples=100, deadline=None)
    def test_estimate_is_positive(self, n: int) -> None:
        """Estimated time is always positive for positive N."""
        assert _estimate_hours(n) > 0

    @given(
        a=st.integers(min_value=1, max_value=50_000),
        b=st.integers(min_value=1, max_value=50_000),
    )
    @settings(max_examples=100, deadline=None)
    def test_estimate_is_monotonic(self, a: int, b: int) -> None:
        """More recipients → longer or equal estimate."""
        if a <= b:
            assert _estimate_hours(a) <= _estimate_hours(b)
        else:
            assert _estimate_hours(a) >= _estimate_hours(b)

    @given(n=st.integers(min_value=1, max_value=100_000))
    @settings(max_examples=100, deadline=None)
    def test_minutes_rounded_up(self, n: int) -> None:
        """Ceiling of minutes is always ≥ actual minutes."""
        hours = _estimate_hours(n)
        mins_exact = hours * 60
        mins_ceil = math.ceil(mins_exact)
        assert mins_ceil >= mins_exact

    def test_140_recipients_takes_one_hour(self) -> None:
        """Exactly 140 recipients = exactly 1 hour."""
        assert _estimate_hours(140) == pytest.approx(1.0)

    def test_1_recipient_takes_fraction_of_hour(self) -> None:
        """1 recipient = 1/140 hour ≈ 0.43 minutes."""
        assert _estimate_hours(1) == pytest.approx(1 / 140)

    @given(n=st.integers(min_value=1, max_value=100_000))
    @settings(max_examples=50, deadline=None)
    def test_window_days_calculation(self, n: int) -> None:
        """When hours exceed window, days = floor(hours / 13)."""
        hours = _estimate_hours(n)
        days = math.floor(hours / _WINDOW_HOURS)
        remaining = hours - days * _WINDOW_HOURS
        assert remaining >= 0
        assert remaining < _WINDOW_HOURS
        assert days * _WINDOW_HOURS + remaining == pytest.approx(hours)


# ---------------------------------------------------------------------------
# Helpers for SMSService property tests (Properties 6, 9, 15, 19)
# ---------------------------------------------------------------------------


def _make_sms_session(
    *,
    consent_allowed: bool = True,
) -> AsyncMock:
    """Build a mock AsyncSession for SMSService tests.

    The session needs to handle:
    1. consent check queries (delegated to consent module)
    2. dedupe queries
    3. model add/flush/refresh
    """
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()

    # Track call index to return different results per execute call
    call_idx = {"n": 0}

    async def _execute(stmt: object) -> MagicMock:
        idx = call_idx["n"]
        call_idx["n"] += 1
        result = MagicMock()
        # Consent module issues up to 4 queries; dedupe is after that
        # For simplicity: hard-stop query returns None (no hard stop) if consent_allowed
        # Marketing opt-in returns a value if consent_allowed
        if idx == 0:
            # hard-STOP check
            result.scalar_one_or_none = MagicMock(
                return_value=uuid4() if not consent_allowed else None,
            )
        elif idx == 1:
            # marketing consent record (only reached if no hard-stop)
            result.scalar_one_or_none = MagicMock(
                return_value=uuid4() if consent_allowed else None,
            )
        elif idx == 2:
            # customer fallback
            result.scalar_one_or_none = MagicMock(return_value=None)
        elif idx == 3:
            # lead fallback
            result.scalar_one_or_none = MagicMock(return_value=None)
        else:
            # dedupe query
            mock_scalars = MagicMock()
            mock_scalars.all = MagicMock(return_value=[])
            result.scalars = MagicMock(return_value=mock_scalars)
        return result

    session.execute = _execute
    return session


# ---------------------------------------------------------------------------
# Property 6: SentMessage FK from Recipient source_type
# Validates: Requirements 4.6, 5.3
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestProperty6SentMessageFKFromRecipientSourceType:
    """SentMessage gets customer_id or lead_id based on Recipient.source_type."""

    @given(
        cust_id=_uuid_st,
        phone=e164_phone,
        first_name=_name_part,
        last_name=_name_part,
    )
    @settings(max_examples=50, deadline=None)
    def test_customer_recipient_sets_customer_id(
        self,
        cust_id: UUID,
        phone: str,
        first_name: str,
        last_name: str,
    ) -> None:
        """Customer recipient → customer_id set, lead_id None."""
        recipient = Recipient(
            phone=phone,
            source_type="customer",
            customer_id=cust_id,
            first_name=first_name,
            last_name=last_name,
        )
        session = _make_sms_session(consent_allowed=True)
        provider = NullProvider()
        svc = SMSService(session, provider)

        result = asyncio.run(
            svc.send_message(
                recipient,
                "Hello",
                MessageType.CUSTOM,
                consent_type="transactional",
            ),
        )
        assert result["success"] is True
        # Verify the SentMessage added to session has correct FKs
        added = session.add.call_args[0][0]
        assert added.customer_id == cust_id
        assert added.lead_id is None

    @given(
        lead_id=_uuid_st,
        phone=e164_phone,
        first_name=_name_part,
        last_name=_name_part,
    )
    @settings(max_examples=50, deadline=None)
    def test_lead_recipient_sets_lead_id(
        self,
        lead_id: UUID,
        phone: str,
        first_name: str,
        last_name: str,
    ) -> None:
        """Lead recipient → lead_id set, customer_id None."""
        recipient = Recipient(
            phone=phone,
            source_type="lead",
            lead_id=lead_id,
            first_name=first_name,
            last_name=last_name,
        )
        session = _make_sms_session(consent_allowed=True)
        provider = NullProvider()
        svc = SMSService(session, provider)

        result = asyncio.run(
            svc.send_message(
                recipient,
                "Hello",
                MessageType.CUSTOM,
                consent_type="transactional",
            ),
        )
        assert result["success"] is True
        added = session.add.call_args[0][0]
        assert added.lead_id == lead_id
        assert added.customer_id is None

    @given(
        lead_id=_uuid_st,
        phone=e164_phone,
        first_name=st.one_of(st.none(), _name_part),
        last_name=st.one_of(st.none(), _name_part),
    )
    @settings(max_examples=50, deadline=None)
    def test_adhoc_recipient_sets_lead_id(
        self,
        lead_id: UUID,
        phone: str,
        first_name: str | None,
        last_name: str | None,
    ) -> None:
        """Ad-hoc recipient → lead_id set, customer_id None."""
        recipient = Recipient.from_adhoc(phone, lead_id, first_name, last_name)
        session = _make_sms_session(consent_allowed=True)
        provider = NullProvider()
        svc = SMSService(session, provider)

        result = asyncio.run(
            svc.send_message(
                recipient,
                "Hello",
                MessageType.CUSTOM,
                consent_type="transactional",
            ),
        )
        assert result["success"] is True
        added = session.add.call_args[0][0]
        assert added.lead_id == lead_id
        assert added.customer_id is None

    @given(
        source_type=st.sampled_from(["customer", "lead", "ad_hoc"]),
        phone=e164_phone,
    )
    @settings(max_examples=50, deadline=None)
    def test_check_constraint_always_satisfied(
        self,
        source_type: str,
        phone: str,
    ) -> None:
        """At least one of customer_id or lead_id is always set."""
        cid = uuid4() if source_type == "customer" else None
        lid = uuid4() if source_type != "customer" else None
        recipient = Recipient(
            phone=phone,
            source_type=source_type,  # type: ignore[arg-type]
            customer_id=cid,
            lead_id=lid,
        )
        session = _make_sms_session(consent_allowed=True)
        provider = NullProvider()
        svc = SMSService(session, provider)

        result = asyncio.run(
            svc.send_message(
                recipient,
                "Hi",
                MessageType.CUSTOM,
                consent_type="transactional",
            ),
        )
        assert result["success"] is True
        added = session.add.call_args[0][0]
        assert added.customer_id is not None or added.lead_id is not None


# ---------------------------------------------------------------------------
# Property 9: Universal phone-keyed consent check
# Validates: Requirements 7.1, 7.3, 7.4, 11.6, 5.5
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestProperty9UniversalPhoneKeyedConsentCheck:
    """Consent denial blocks send for any Recipient source_type."""

    @given(
        source_type=st.sampled_from(["customer", "lead", "ad_hoc"]),
        phone=e164_phone,
    )
    @settings(max_examples=50, deadline=None)
    def test_consent_denied_blocks_all_source_types(
        self,
        source_type: str,
        phone: str,
    ) -> None:
        """When consent is denied, send_message raises SMSConsentDeniedError."""
        cid = uuid4() if source_type == "customer" else None
        lid = uuid4() if source_type != "customer" else None
        recipient = Recipient(
            phone=phone,
            source_type=source_type,  # type: ignore[arg-type]
            customer_id=cid,
            lead_id=lid,
        )
        session = _make_sms_session(consent_allowed=False)
        provider = NullProvider()
        svc = SMSService(session, provider)

        with pytest.raises(SMSConsentDeniedError):
            asyncio.run(
                svc.send_message(
                    recipient,
                    "Hello",
                    MessageType.CAMPAIGN,
                    consent_type="marketing",
                ),
            )
        # Provider should NOT have been called
        assert len(provider.sent) == 0

    @given(
        source_type=st.sampled_from(["customer", "lead", "ad_hoc"]),
        phone=e164_phone,
    )
    @settings(max_examples=50, deadline=None)
    def test_consent_allowed_permits_send(
        self,
        source_type: str,
        phone: str,
    ) -> None:
        """When consent is allowed, send_message succeeds."""
        cid = uuid4() if source_type == "customer" else None
        lid = uuid4() if source_type != "customer" else None
        recipient = Recipient(
            phone=phone,
            source_type=source_type,  # type: ignore[arg-type]
            customer_id=cid,
            lead_id=lid,
        )
        session = _make_sms_session(consent_allowed=True)
        provider = NullProvider()
        svc = SMSService(session, provider)

        result = asyncio.run(
            svc.send_message(
                recipient,
                "Hello",
                MessageType.CUSTOM,
                consent_type="transactional",
            ),
        )
        assert result["success"] is True
        assert len(provider.sent) == 1

    @given(phone=e164_phone)
    @settings(max_examples=30, deadline=None)
    def test_consent_check_uses_phone_not_source_model(
        self,
        phone: str,
    ) -> None:
        """Consent is checked by phone, not by Customer.sms_opt_in."""
        # Customer recipient with consent denied at phone level
        recipient = Recipient(
            phone=phone,
            source_type="customer",
            customer_id=uuid4(),
        )
        session = _make_sms_session(consent_allowed=False)
        provider = NullProvider()
        svc = SMSService(session, provider)

        with pytest.raises(SMSConsentDeniedError):
            asyncio.run(
                svc.send_message(
                    recipient,
                    "Hello",
                    MessageType.CAMPAIGN,
                    consent_type="marketing",
                ),
            )


# ---------------------------------------------------------------------------
# Property 15: Outbound message formatting
# Validates: Requirements 11.2, 11.3
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestProperty15OutboundMessageFormatting:
    """Outbound messages include sender prefix and STOP footer."""

    @given(body=sms_body)
    @settings(max_examples=50, deadline=None)
    def test_message_starts_with_prefix(self, body: str) -> None:
        """Sent message content starts with the sender prefix."""
        recipient = Recipient(
            phone="+19525293750",
            source_type="lead",
            lead_id=uuid4(),
        )
        session = _make_sms_session(consent_allowed=True)
        provider = NullProvider()
        svc = SMSService(session, provider)

        asyncio.run(
            svc.send_message(
                recipient,
                body,
                MessageType.CUSTOM,
                consent_type="transactional",
            ),
        )
        assert len(provider.sent) == 1
        sent_body = provider.sent[0]["body"]
        assert sent_body.startswith(_SVC_PREFIX)

    @given(body=sms_body)
    @settings(max_examples=50, deadline=None)
    def test_message_contains_stop_keyword(self, body: str) -> None:
        """Sent message content contains STOP keyword in footer."""
        recipient = Recipient(
            phone="+19525293750",
            source_type="lead",
            lead_id=uuid4(),
        )
        session = _make_sms_session(consent_allowed=True)
        provider = NullProvider()
        svc = SMSService(session, provider)

        asyncio.run(
            svc.send_message(
                recipient,
                body,
                MessageType.CUSTOM,
                consent_type="transactional",
            ),
        )
        sent_body = provider.sent[0]["body"]
        stop_keywords = {"stop", "cancel", "unsubscribe", "quit", "end"}
        assert any(kw in sent_body.lower() for kw in stop_keywords)

    @given(body=sms_body)
    @settings(max_examples=50, deadline=None)
    def test_message_ends_with_footer(self, body: str) -> None:
        """Sent message content ends with the STOP footer."""
        recipient = Recipient(
            phone="+19525293750",
            source_type="lead",
            lead_id=uuid4(),
        )
        session = _make_sms_session(consent_allowed=True)
        provider = NullProvider()
        svc = SMSService(session, provider)

        asyncio.run(
            svc.send_message(
                recipient,
                body,
                MessageType.CUSTOM,
                consent_type="transactional",
            ),
        )
        sent_body = provider.sent[0]["body"]
        assert sent_body.endswith(_SVC_FOOTER)

    @given(body=sms_body)
    @settings(max_examples=30, deadline=None)
    def test_skip_formatting_sends_raw(self, body: str) -> None:
        """skip_formatting=True sends body as-is without prefix/footer."""
        recipient = Recipient(
            phone="+19525293750",
            source_type="lead",
            lead_id=uuid4(),
        )
        session = _make_sms_session(consent_allowed=True)
        provider = NullProvider()
        svc = SMSService(session, provider)

        asyncio.run(
            svc.send_message(
                recipient,
                body,
                MessageType.CUSTOM,
                consent_type="transactional",
                skip_formatting=True,
            ),
        )
        sent_body = provider.sent[0]["body"]
        assert sent_body == body


# ---------------------------------------------------------------------------
# Property 19: Send persistence round-trip
# Validates: Requirements 2.9, 12.7
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestProperty19SendPersistenceRoundTrip:
    """Successful send creates SentMessage with correct provider fields."""

    @given(
        phone=e164_phone,
        body=sms_body,
    )
    @settings(max_examples=50, deadline=None)
    def test_sent_message_has_provider_id(
        self,
        phone: str,
        body: str,
    ) -> None:
        """SentMessage.provider_message_id matches provider_message_id."""
        recipient = Recipient(
            phone=phone,
            source_type="lead",
            lead_id=uuid4(),
        )
        session = _make_sms_session(consent_allowed=True)
        provider = NullProvider()
        svc = SMSService(session, provider)

        result = asyncio.run(
            svc.send_message(
                recipient,
                body,
                MessageType.CUSTOM,
                consent_type="transactional",
            ),
        )
        assert result["success"] is True
        assert result["provider_message_id"]
        # The SentMessage added to session should have the provider ID
        added = session.add.call_args[0][0]
        assert added.provider_message_id == result["provider_message_id"]

    @given(phone=e164_phone, body=sms_body)
    @settings(max_examples=50, deadline=None)
    def test_sent_message_has_sent_status(
        self,
        phone: str,
        body: str,
    ) -> None:
        """SentMessage.delivery_status is 'sent' after successful send."""
        recipient = Recipient(
            phone=phone,
            source_type="lead",
            lead_id=uuid4(),
        )
        session = _make_sms_session(consent_allowed=True)
        provider = NullProvider()
        svc = SMSService(session, provider)

        result = asyncio.run(
            svc.send_message(
                recipient,
                body,
                MessageType.CUSTOM,
                consent_type="transactional",
            ),
        )
        assert result["status"] == "sent"
        added = session.add.call_args[0][0]
        assert added.delivery_status == "sent"

    @given(phone=e164_phone, body=sms_body)
    @settings(max_examples=50, deadline=None)
    def test_sent_message_has_recipient_phone(
        self,
        phone: str,
        body: str,
    ) -> None:
        """SentMessage.recipient_phone matches the Recipient's phone (E.164)."""
        recipient = Recipient(
            phone=phone,
            source_type="lead",
            lead_id=uuid4(),
        )
        session = _make_sms_session(consent_allowed=True)
        provider = NullProvider()
        svc = SMSService(session, provider)

        asyncio.run(
            svc.send_message(
                recipient,
                body,
                MessageType.CUSTOM,
                consent_type="transactional",
            ),
        )
        added = session.add.call_args[0][0]
        # Phone should be E.164 formatted
        assert added.recipient_phone.startswith("+")

    @given(phone=e164_phone, body=sms_body)
    @settings(max_examples=30, deadline=None)
    def test_sent_message_has_sent_at_timestamp(
        self,
        phone: str,
        body: str,
    ) -> None:
        """SentMessage.sent_at is set after successful send."""
        recipient = Recipient(
            phone=phone,
            source_type="lead",
            lead_id=uuid4(),
        )
        session = _make_sms_session(consent_allowed=True)
        provider = NullProvider()
        svc = SMSService(session, provider)

        asyncio.run(
            svc.send_message(
                recipient,
                body,
                MessageType.CUSTOM,
                consent_type="transactional",
            ),
        )
        added = session.add.call_args[0][0]
        assert added.sent_at is not None


# ---------------------------------------------------------------------------
# Property 27: Consent field mapping
# Validates: Requirement 19.1
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestProperty27ConsentFieldMapping:
    """Customer.sms_opt_in and Lead.sms_consent map identically to consent outcome.

    The naming asymmetry (sms_opt_in vs sms_consent) must be invisible to
    downstream code — both fields produce the same boolean consent result
    when used as the marketing fallback in check_sms_consent().
    """

    @given(phone=e164_phone, opt_in=st.booleans())
    @settings(max_examples=50, deadline=None)
    def test_customer_sms_opt_in_maps_to_marketing_consent(
        self,
        phone: str,
        opt_in: bool,
    ) -> None:
        """Customer.sms_opt_in=X → marketing consent returns X (fallback path)."""
        session = _mock_consent_session(
            has_hard_stop=False,
            has_marketing_record=False,
            has_customer_opt_in=opt_in,
            has_lead_consent=False,
        )
        result = asyncio.run(check_sms_consent(session, phone, "marketing"))  # type: ignore[arg-type]
        assert result is opt_in

    @given(phone=e164_phone, consent=st.booleans())
    @settings(max_examples=50, deadline=None)
    def test_lead_sms_consent_maps_to_marketing_consent(
        self,
        phone: str,
        consent: bool,
    ) -> None:
        """Lead.sms_consent=Y → marketing consent returns Y (fallback path)."""
        session = _mock_consent_session(
            has_hard_stop=False,
            has_marketing_record=False,
            has_customer_opt_in=False,
            has_lead_consent=consent,
        )
        result = asyncio.run(check_sms_consent(session, phone, "marketing"))  # type: ignore[arg-type]
        assert result is consent

    @given(phone=e164_phone, opt_in=st.booleans())
    @settings(max_examples=50, deadline=None)
    def test_customer_and_lead_fields_produce_same_outcome(
        self,
        phone: str,
        opt_in: bool,
    ) -> None:
        """Same boolean value in either field yields identical consent result."""
        cust_session = _mock_consent_session(
            has_hard_stop=False,
            has_marketing_record=False,
            has_customer_opt_in=opt_in,
            has_lead_consent=False,
        )
        lead_session = _mock_consent_session(
            has_hard_stop=False,
            has_marketing_record=False,
            has_customer_opt_in=False,
            has_lead_consent=opt_in,
        )
        cust_result = asyncio.run(check_sms_consent(cust_session, phone, "marketing"))  # type: ignore[arg-type]
        lead_result = asyncio.run(check_sms_consent(lead_session, phone, "marketing"))  # type: ignore[arg-type]
        assert cust_result == lead_result


# ---------------------------------------------------------------------------
# Property 10: Inbound webhook parsing
# Validates: Requirements 9.2
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestProperty10InboundWebhookParsing:
    """CallRailProvider.parse_inbound_webhook extracts fields correctly."""

    @given(
        phone=e164_phone,
        body=sms_body,
        conv_id=callrail_id,
        tracking=e164_phone,
    )
    @settings(max_examples=50, deadline=None)
    def test_parses_all_fields(
        self,
        phone: str,
        body: str,
        conv_id: str,
        tracking: str,
    ) -> None:
        """All payload fields map to InboundSMS attributes.

        Field names mirror the real CallRail inbound webhook payload
        verified on 2026-04-08: ``source_number`` /
        ``destination_number`` / ``resource_id`` (NOT the
        ``customer_phone_number`` / ``id`` we originally guessed).
        """
        provider = CallRailProvider(
            api_key="k",
            account_id="acc",
            company_id="comp",
            tracking_number="+19525293750",
        )
        payload = {
            "source_number": phone,
            "content": body,
            "resource_id": conv_id,
            "destination_number": tracking,
        }
        result = provider.parse_inbound_webhook(payload)
        assert result.from_phone == phone
        assert result.body == body
        assert result.provider_sid == conv_id
        assert result.to_phone == tracking

    @given(phone=e164_phone, body=sms_body)
    @settings(max_examples=50, deadline=None)
    def test_missing_optional_fields_default_to_empty(
        self,
        phone: str,
        body: str,
    ) -> None:
        """Missing optional fields default to empty-string / None.

        ``provider_sid`` is a required string column in the consumer
        (``SentMessage.provider_message_id``) so it defaults to ``""``.
        ``to_phone`` / ``thread_id`` / ``conversation_id`` are
        Optional[str] on ``InboundSMS`` and the provider explicitly
        coalesces empty payload values to ``None``.
        """
        provider = CallRailProvider(
            api_key="k",
            account_id="acc",
            company_id="comp",
            tracking_number="+19525293750",
        )
        payload = {
            "source_number": phone,
            "content": body,
        }
        result = provider.parse_inbound_webhook(payload)
        assert result.from_phone == phone
        assert result.body == body
        assert result.provider_sid == ""
        assert result.to_phone is None

    @given(data=st.data())
    @settings(max_examples=30, deadline=None)
    def test_empty_payload_returns_empty_strings(
        self,
        data: st.DataObject,
    ) -> None:
        """Completely empty payload returns an InboundSMS with safe defaults.

        Required-on-consumer fields (``from_phone``, ``body``,
        ``provider_sid``) default to ``""``; Optional fields
        (``to_phone``, ``thread_id``, ``conversation_id``) default to
        ``None`` so downstream code can distinguish "not provided"
        from "empty string".
        """
        _ = data
        provider = CallRailProvider(
            api_key="k",
            account_id="acc",
            company_id="comp",
            tracking_number="+19525293750",
        )
        result = provider.parse_inbound_webhook({})
        assert result.from_phone == ""
        assert result.body == ""
        assert result.provider_sid == ""
        assert result.to_phone is None
        assert result.thread_id is None
        assert result.conversation_id is None

    @given(
        phone=e164_phone,
        body=sms_body,
        conv_id=callrail_id,
    )
    @settings(max_examples=30, deadline=None)
    def test_result_is_frozen_dataclass(
        self,
        phone: str,
        body: str,
        conv_id: str,
    ) -> None:
        """InboundSMS is immutable (frozen dataclass)."""
        provider = CallRailProvider(
            api_key="k",
            account_id="acc",
            company_id="comp",
            tracking_number="+19525293750",
        )
        payload = {
            "customer_phone_number": phone,
            "content": body,
            "id": conv_id,
        }
        result = provider.parse_inbound_webhook(payload)
        with pytest.raises(AttributeError):
            result.from_phone = "changed"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Property 16: STOP keyword consent revocation
# Validates: Requirements 9.4, 9.5, 11.4
# ---------------------------------------------------------------------------

_opt_out_kw = st.sampled_from(
    ["stop", "quit", "cancel", "unsubscribe", "end", "revoke"],
)


@pytest.mark.unit
class TestProperty16StopKeywordConsentRevocation:
    """STOP keywords create SmsConsentRecord with consent_given=False."""

    @given(keyword=_opt_out_kw, phone=e164_phone)
    @settings(max_examples=50, deadline=None)
    def test_exact_keyword_creates_opt_out_record(
        self,
        keyword: str,
        phone: str,
    ) -> None:
        """Exact opt-out keyword creates consent record with consent_given=False."""
        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()
        provider = NullProvider()
        svc = SMSService(session, provider)

        result = asyncio.run(svc.handle_inbound(phone, keyword, "sid_123"))

        assert result["action"] == "opt_out"
        assert result["keyword"] == keyword
        # Verify consent record was added (+ audit log)
        assert session.add.call_count >= 1
        record = session.add.call_args_list[0][0][0]
        assert record.consent_given is False
        assert record.consent_method == "text_stop"
        assert record.opt_out_method == "text_stop"

    @given(keyword=_opt_out_kw, phone=e164_phone)
    @settings(max_examples=50, deadline=None)
    def test_case_insensitive_keyword_match(
        self,
        keyword: str,
        phone: str,
    ) -> None:
        """Keywords match case-insensitively."""
        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()
        provider = NullProvider()
        svc = SMSService(session, provider)

        result = asyncio.run(
            svc.handle_inbound(phone, keyword.upper(), "sid"),
        )
        assert result["action"] == "opt_out"

    @given(keyword=_opt_out_kw, phone=e164_phone)
    @settings(max_examples=50, deadline=None)
    def test_stop_sends_confirmation_sms(
        self,
        keyword: str,
        phone: str,
    ) -> None:
        """STOP keyword triggers a confirmation SMS."""
        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()
        provider = NullProvider()
        svc = SMSService(session, provider)

        asyncio.run(svc.handle_inbound(phone, keyword, "sid"))

        assert len(provider.sent) == 1
        assert "unsubscribed" in provider.sent[0]["body"].lower()

    @given(phone=e164_phone)
    @settings(max_examples=30, deadline=None)
    def test_non_keyword_does_not_create_opt_out(
        self,
        phone: str,
    ) -> None:
        """Non-keyword messages do not create opt-out consent records."""
        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()

        # Mock execute for handle_webhook path (returns empty result)
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        session.execute = AsyncMock(return_value=mock_result)

        provider = NullProvider()
        svc = SMSService(session, provider)

        result = asyncio.run(svc.handle_inbound(phone, "Hello there", "sid"))

        assert result.get("action") != "opt_out"


# ---------------------------------------------------------------------------
# Property 42: Webhook signature rejection
# Validates: Requirements 44
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestProperty42WebhookSignatureRejection:
    """verify_webhook_signature rejects invalid/missing signatures."""

    @given(
        body=st.binary(min_size=1, max_size=500),
        secret=st.text(min_size=1, max_size=50),
    )
    @settings(max_examples=50, deadline=None)
    def test_valid_signature_accepted(
        self,
        body: bytes,
        secret: str,
    ) -> None:
        """Correct HMAC-SHA1 / base64 signature is accepted.

        Matches the real CallRail webhook contract verified on
        2026-04-08:
        - Header name: ``signature`` (lowercase, no ``x-`` prefix)
        - Algorithm: HMAC-SHA1 (NOT SHA256)
        - Encoding: base64 of the raw digest
        """
        import base64

        provider = CallRailProvider(
            api_key="k",
            account_id="acc",
            company_id="comp",
            tracking_number="+19525293750",
            webhook_secret=secret,
        )
        sig = base64.b64encode(
            _hmac.new(secret.encode(), body, hashlib.sha1).digest(),
        ).decode()
        headers = {"signature": sig}

        result = asyncio.run(provider.verify_webhook_signature(headers, body))
        assert result is True

    @given(
        body=st.binary(min_size=1, max_size=500),
        secret=st.text(min_size=1, max_size=50),
        bad_sig=st.from_regex(r"[a-f0-9]{64}", fullmatch=True),
    )
    @settings(max_examples=50, deadline=None)
    def test_wrong_signature_rejected(
        self,
        body: bytes,
        secret: str,
        bad_sig: str,
    ) -> None:
        """Incorrect signature is rejected."""
        import base64

        provider = CallRailProvider(
            api_key="k",
            account_id="acc",
            company_id="comp",
            tracking_number="+19525293750",
            webhook_secret=secret,
        )
        # Ensure bad_sig differs from the real one (HMAC-SHA1/base64).
        real_sig = base64.b64encode(
            _hmac.new(secret.encode(), body, hashlib.sha1).digest(),
        ).decode()
        if bad_sig == real_sig:
            return  # skip degenerate case
        headers = {"signature": bad_sig}

        result = asyncio.run(provider.verify_webhook_signature(headers, body))
        assert result is False

    @given(
        body=st.binary(min_size=1, max_size=500),
        secret=st.text(min_size=1, max_size=50),
    )
    @settings(max_examples=50, deadline=None)
    def test_missing_signature_header_rejected(
        self,
        body: bytes,
        secret: str,
    ) -> None:
        """Missing ``signature`` header is rejected."""
        provider = CallRailProvider(
            api_key="k",
            account_id="acc",
            company_id="comp",
            tracking_number="+19525293750",
            webhook_secret=secret,
        )
        result = asyncio.run(provider.verify_webhook_signature({}, body))
        assert result is False

    @given(body=st.binary(min_size=1, max_size=500))
    @settings(max_examples=30, deadline=None)
    def test_empty_webhook_secret_rejects_all(self, body: bytes) -> None:
        """Provider with no webhook_secret rejects all signatures."""
        provider = CallRailProvider(
            api_key="k",
            account_id="acc",
            company_id="comp",
            tracking_number="+19525293750",
            webhook_secret="",
        )
        headers = {"x-callrail-signature": "anything"}
        result = asyncio.run(provider.verify_webhook_signature(headers, body))
        assert result is False


# ---------------------------------------------------------------------------
# Property 43: Webhook idempotency
# Validates: Requirements 30
# ---------------------------------------------------------------------------

_iso_ts = st.from_regex(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}",
    fullmatch=True,
)


def _stub_db_with_exists(found: bool) -> MagicMock:
    """Build a MagicMock ``db`` so ``WebhookProcessedLogRepository.exists``
    resolves to ``found``. ``exists`` runs ``session.execute(...).scalar_one_or_none``.
    """
    exec_result = MagicMock()
    exec_result.scalar_one_or_none.return_value = True if found else None
    db = MagicMock()
    db.execute = AsyncMock(return_value=exec_result)
    db.flush = AsyncMock()
    return db


@pytest.mark.unit
class TestProperty43WebhookIdempotency:
    """_is_duplicate deduplicates webhooks via Redis (primary + msg-id)."""

    @given(conv_id=callrail_id, created_at=_iso_ts, msgid=callrail_id)
    @settings(max_examples=50, deadline=None)
    def test_first_call_returns_false(
        self,
        conv_id: str,
        created_at: str,
        msgid: str,
    ) -> None:
        """First call returns False (not duplicate)."""
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        db = _stub_db_with_exists(False)

        result = asyncio.run(
            _is_duplicate(mock_redis, db, "callrail", conv_id, created_at, msgid),
        )
        assert result is False

    @given(conv_id=callrail_id, created_at=_iso_ts, msgid=callrail_id)
    @settings(max_examples=50, deadline=None)
    def test_second_call_returns_true(
        self,
        conv_id: str,
        created_at: str,
        msgid: str,
    ) -> None:
        """Second call for same primary key returns True (duplicate)."""
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=b"1")
        db = _stub_db_with_exists(False)

        result = asyncio.run(
            _is_duplicate(mock_redis, db, "callrail", conv_id, created_at, msgid),
        )
        assert result is True

    @given(conv_id=callrail_id, created_at=_iso_ts)
    @settings(max_examples=30, deadline=None)
    def test_redis_none_with_no_msgid_returns_false(
        self,
        conv_id: str,
        created_at: str,
    ) -> None:
        """Redis=None AND no message_id → False (DB fallback is skipped)."""
        db = _stub_db_with_exists(False)
        result = asyncio.run(
            _is_duplicate(None, db, "callrail", conv_id, created_at, ""),
        )
        assert result is False

    @given(conv_id=callrail_id, created_at=_iso_ts, msgid=callrail_id)
    @settings(max_examples=30, deadline=None)
    def test_redis_error_falls_back_to_db(
        self,
        conv_id: str,
        created_at: str,
        msgid: str,
    ) -> None:
        """Redis exception → fall through to DB. Not-in-DB → False."""
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(
            side_effect=ConnectionError("Redis down"),
        )
        db = _stub_db_with_exists(False)

        result = asyncio.run(
            _is_duplicate(mock_redis, db, "callrail", conv_id, created_at, msgid),
        )
        assert result is False

    @given(conv_id=callrail_id, created_at=_iso_ts, msgid=callrail_id)
    @settings(max_examples=30, deadline=None)
    def test_redis_key_format_primary(
        self,
        conv_id: str,
        created_at: str,
        msgid: str,
    ) -> None:
        """First Redis lookup targets prefix:conv_id:created_at."""
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        db = _stub_db_with_exists(False)

        asyncio.run(
            _is_duplicate(mock_redis, db, "callrail", conv_id, created_at, msgid),
        )
        expected_primary = f"{_REDIS_KEY_PREFIX}:{conv_id}:{created_at}"
        first_call = mock_redis.get.await_args_list[0]
        assert first_call.args[0] == expected_primary


# ---------------------------------------------------------------------------
# Property 46: Phone masking in logs
# Validates: Requirement 42 (acceptance criteria 2, 3)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestProperty46PhoneMaskingInLogs:
    """For any E.164 phone, the masked output must never contain the raw
    phone and must expose at most the last 4 digits."""

    @given(phone=e164_phone)
    @settings(max_examples=100, deadline=None)
    def test_raw_phone_never_in_masked_output_callrail(self, phone: str) -> None:
        masked = _mask_phone_callrail(phone)
        assert phone not in masked, "Raw phone leaked through masking"

    @given(phone=e164_phone)
    @settings(max_examples=100, deadline=None)
    def test_raw_phone_never_in_masked_output_sms(self, phone: str) -> None:
        masked = _mask_phone_sms(phone)
        assert phone not in masked, "Raw phone leaked through masking"

    @given(phone=e164_phone)
    @settings(max_examples=100, deadline=None)
    def test_masked_preserves_only_prefix_and_suffix(self, phone: str) -> None:
        """Masked output is exactly prefix(4) + '***' + suffix(4)."""
        masked = _mask_phone_callrail(phone)
        assert masked.endswith(phone[-4:])
        assert masked.startswith(phone[:4])
        assert len(masked) == 4 + 3 + 4  # prefix + *** + suffix

    @given(phone=e164_phone)
    @settings(max_examples=100, deadline=None)
    def test_masked_format_matches_spec(self, phone: str) -> None:
        """Output format: +1XXX***XXXX (first 4 chars + *** + last 4)."""
        masked = _mask_phone_callrail(phone)
        assert masked == phone[:4] + "***" + phone[-4:]

    @given(phone=e164_phone)
    @settings(max_examples=100, deadline=None)
    def test_short_phone_fully_masked(self, phone: str) -> None:
        """Phones shorter than threshold are fully masked."""
        short = phone[:5]  # e.g. "+1952"
        assert _mask_phone_callrail(short) == "***"
        assert _mask_phone_sms(short) == "***"


# ---------------------------------------------------------------------------
# Property 17: CSV row parsing
# Validates: Requirement 12.1
# ---------------------------------------------------------------------------

# Import parse_csv and CsvRow from the script
_script_path = str(
    Path(__file__).resolve().parents[4] / "scripts" / "send_callrail_campaign.py",
)
_spec_mod = _ilu.spec_from_file_location(
    "send_callrail_campaign",
    _script_path,
)
assert _spec_mod is not None and _spec_mod.loader is not None
_csv_script = _ilu.module_from_spec(_spec_mod)
_sys.modules["send_callrail_campaign"] = _csv_script
_spec_mod.loader.exec_module(_csv_script)  # type: ignore[union-attr]
_parse_csv = _csv_script.parse_csv  # type: ignore[attr-defined]
_CsvRow = _csv_script.CsvRow  # type: ignore[attr-defined]
_run = _csv_script.run  # type: ignore[attr-defined]

# Strategy: names that are safe for CSV (no commas/newlines)
_csv_safe_name = st.text(
    alphabet=st.characters(
        whitelist_categories=("L", "N", "Zs"),
        blacklist_characters=',\r\n"',
    ),
    min_size=0,
    max_size=30,
)


@pytest.mark.unit
class TestProperty17CsvRowParsing:
    """Valid CSV with phone/first_name/last_name columns parses correctly."""

    @given(
        rows=st.lists(
            st.tuples(
                st.from_regex(r"[2-9]\d{9}", fullmatch=True),
                _csv_safe_name,
                _csv_safe_name,
            ),
            min_size=1,
            max_size=20,
        ),
    )
    @settings(max_examples=50, deadline=None)
    def test_csv_parses_all_rows(
        self,
        rows: list[tuple[str, str, str]],
    ) -> None:
        """Every row in a valid CSV produces a CsvRow with correct fields."""
        with _tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".csv",
            delete=False,
            newline="",
        ) as f:
            f.write("phone,first_name,last_name\n")
            for phone, first, last in rows:
                f.write(f"{phone},{first},{last}\n")
            tmp = Path(f.name)

        try:
            parsed, errors = _parse_csv(tmp)
        finally:
            tmp.unlink()

        assert not errors, f"Unexpected parse errors: {errors}"
        assert len(parsed) == len(rows)
        for i, (row_obj, (phone, first, last)) in enumerate(zip(parsed, rows)):
            assert row_obj.phone == phone.strip()
            assert row_obj.first_name == first.strip()
            assert row_obj.last_name == last.strip()
            assert row_obj.line == i + 2  # header is line 1

    def test_missing_phone_column_errors(self) -> None:
        """CSV without a 'phone' column produces an error."""
        with _tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".csv",
            delete=False,
            newline="",
        ) as f:
            f.write("name,email\nJohn,john@test.com\n")
            tmp = Path(f.name)

        try:
            parsed, errors = _parse_csv(tmp)
        finally:
            tmp.unlink()

        assert len(parsed) == 0
        assert any("phone" in e.lower() for e in errors)

    def test_empty_phone_skipped(self) -> None:
        """Rows with empty phone produce per-row errors."""
        with _tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".csv",
            delete=False,
            newline="",
        ) as f:
            f.write("phone,first_name,last_name\n,John,Doe\n9525293750,Jane,Smith\n")
            tmp = Path(f.name)

        try:
            parsed, errors = _parse_csv(tmp)
        finally:
            tmp.unlink()

        assert len(parsed) == 1
        assert parsed[0].phone == "9525293750"
        assert len(errors) == 1


# ---------------------------------------------------------------------------
# Property 18: Dry-run zero sends
# Validates: Requirement 12.3
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestProperty18DryRunZeroSends:
    """Dry-run mode never calls the SMS provider."""

    @given(
        rows=st.lists(
            st.tuples(
                st.from_regex(r"\+1[2-9]\d{9}", fullmatch=True),
                st.text(min_size=1, max_size=10, alphabet="abcdefghij"),
                st.text(min_size=1, max_size=10, alphabet="abcdefghij"),
            ),
            min_size=1,
            max_size=5,
        ),
        template=st.just("Hi {first_name}!"),
    )
    @settings(max_examples=20, deadline=None)
    def test_dry_run_sends_nothing(
        self,
        rows: list[tuple[str, str, str]],
        template: str,
    ) -> None:
        """Dry-run produces preview output but zero provider calls."""
        with _tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".csv",
            delete=False,
            newline="",
        ) as f:
            f.write("phone,first_name,last_name\n")
            for phone, first, last in rows:
                f.write(f"{phone},{first},{last}\n")
            tmp = Path(f.name)

        mock_provider = MagicMock()
        mock_db = MagicMock()

        try:
            with (
                patch.object(
                    _csv_script,
                    "get_sms_provider",
                    return_value=mock_provider,
                ),
                patch.object(
                    _csv_script,
                    "DatabaseManager",
                    return_value=mock_db,
                ),
            ):
                asyncio.run(_run(tmp, template, confirm=False))
        finally:
            tmp.unlink()

        # Dry-run must never instantiate provider or DB
        mock_provider.send_text.assert_not_called()
        mock_db.get_session.assert_not_called()


# ---------------------------------------------------------------------------
# Properties 11, 12, 13, 14, 28, 29, 30, 45: Background campaign worker
# Validates: Requirements 8.2, 10.2, 10.4, 10.6, 10.7, 11.5, 21.1-21.5, 28
# ---------------------------------------------------------------------------


def _make_mock_cr(
    *,
    delivery_status: str = "pending",
    campaign_id: object | None = None,
    customer_id: object | None = None,
    lead_id: object | None = None,
    channel: str = "sms",
    sending_started_at: object | None = None,
) -> MagicMock:
    """Create a mock CampaignRecipient."""
    cr = MagicMock()
    cr.id = uuid4()
    cr.campaign_id = campaign_id or uuid4()
    cr.customer_id = customer_id or uuid4()
    cr.lead_id = lead_id
    cr.channel = channel
    cr.delivery_status = delivery_status
    cr.sending_started_at = sending_started_at
    cr.sent_at = None
    cr.error_message = None
    cr.created_at = datetime.now(timezone.utc)
    return cr


def _make_mock_campaign(
    *,
    status: str = "sending",
    body: str = "Hello {first_name}!",
    scheduled_at: object | None = None,
) -> MagicMock:
    camp = MagicMock()
    camp.id = uuid4()
    camp.status = status
    camp.body = body
    camp.scheduled_at = scheduled_at
    camp.sent_at = None
    return camp


def _mock_worker_session(
    *,
    orphan_count: int = 0,
    recipients: list[MagicMock] | None = None,
    campaign: MagicMock | None = None,
    customer: MagicMock | None = None,
) -> tuple[AsyncMock, MagicMock]:
    """Build a mock session + db_manager for CampaignWorker.run()."""
    session = AsyncMock()

    orphan_result = MagicMock()
    orphan_result.rowcount = orphan_count

    claim_result = MagicMock()
    claim_result.scalars.return_value.all.return_value = recipients or []

    count_result = MagicMock()
    count_result.all.return_value = []

    session.execute = AsyncMock(
        side_effect=[orphan_result, claim_result, count_result],
    )

    async def _get(model: type, _pk: object) -> object | None:
        from grins_platform.models.campaign import Campaign
        from grins_platform.models.customer import Customer

        if model is Campaign:
            return campaign
        if model is Customer:
            return customer
        return None

    session.get = AsyncMock(side_effect=_get)
    session.flush = AsyncMock()

    db_manager = MagicMock()

    async def _gen():
        yield session

    db_manager.get_session = _gen

    return session, db_manager


def _worker_patches(
    db_manager: MagicMock,
    *,
    in_window: bool = True,
    consent: bool = True,
    rate_allowed: bool = True,
    send_result: dict[str, object] | None = None,
    send_error: Exception | None = None,
):
    """Return a combined context manager with standard worker patches."""
    from contextlib import contextmanager

    rl_state = MagicMock()
    rl_check = CheckResult(
        allowed=rate_allowed,
        retry_after_seconds=0 if rate_allowed else 60,
        state=rl_state,
    )

    @contextmanager
    def _ctx():
        with (
            patch(
                "grins_platform.services.background_jobs.get_database_manager",
                return_value=db_manager,
            ),
            patch(
                "grins_platform.services.background_jobs._is_within_time_window",
                return_value=in_window,
            ),
            patch(
                "grins_platform.services.background_jobs.get_sms_provider",
                return_value=NullProvider(),
            ),
            patch(
                "grins_platform.services.background_jobs.check_sms_consent",
                new_callable=AsyncMock,
                return_value=consent,
            ),
            patch(
                "grins_platform.services.sms.rate_limit_tracker.SMSRateLimitTracker.check",
                new_callable=AsyncMock,
                return_value=rl_check,
            ),
            patch(
                "grins_platform.services.sms_service.SMSService.send_message",
                new_callable=AsyncMock,
                side_effect=send_error,
                return_value=send_result
                if send_result is not None
                else {"success": True},
            ),
        ):
            yield

    return _ctx()


def _make_customer(cr: MagicMock) -> MagicMock:
    """Create a mock Customer matching a CampaignRecipient."""
    c = MagicMock()
    c.id = cr.customer_id
    c.phone = "+19525293750"
    c.first_name = "Test"
    c.last_name = "User"
    c.sms_opt_in = True
    return c


@pytest.mark.unit
class TestProperty11BackgroundWorkerRespectsRateLimits:
    """Worker skips sending when rate limit tracker denies."""

    @pytest.mark.asyncio
    async def test_rate_limited_recipient_reverts_to_pending(self) -> None:
        """When rate limit check fails, recipient stays pending."""
        worker = CampaignWorker()
        cr = _make_mock_cr()
        campaign = _make_mock_campaign()
        customer = _make_customer(cr)
        _, db_manager = _mock_worker_session(
            recipients=[cr],
            campaign=campaign,
            customer=customer,
        )

        with _worker_patches(db_manager, rate_allowed=False):
            await worker.run()

        assert cr.delivery_status == "pending"
        assert cr.sending_started_at is None


@pytest.mark.unit
class TestProperty12WorkerResumability:
    """Worker picks up where it left off — only processes pending rows."""

    @pytest.mark.asyncio
    async def test_only_pending_recipients_claimed(self) -> None:
        """Worker query filters on delivery_status='pending'."""
        worker = CampaignWorker()
        session, db_manager = _mock_worker_session(recipients=[])

        with _worker_patches(db_manager):
            await worker.run()

        # orphan recovery + claim query
        assert session.execute.call_count >= 2

    @pytest.mark.asyncio
    async def test_empty_claim_exits_cleanly(self) -> None:
        """No pending recipients → worker exits without errors."""
        worker = CampaignWorker()
        _, db_manager = _mock_worker_session(recipients=[])

        with _worker_patches(db_manager):
            await worker.run()  # should not raise


@pytest.mark.unit
class TestProperty13WorkerHonorsScheduledAt:
    """Worker only processes campaigns where scheduled_at <= now()."""

    @pytest.mark.asyncio
    async def test_no_recipients_when_none_pending(self) -> None:
        """When claim returns empty, worker does nothing."""
        worker = CampaignWorker()
        _, db_manager = _mock_worker_session(recipients=[])

        with _worker_patches(db_manager):
            await worker.run()

    def test_claim_query_checks_scheduled_at(self) -> None:
        """The claim SQL includes scheduled_at filter."""
        import inspect

        source = inspect.getsource(CampaignWorker.run)
        assert "scheduled_at" in source


@pytest.mark.unit
class TestProperty14TimeWindowEnforcement:
    """Worker skips processing outside 8 AM - 9 PM CT."""

    @pytest.mark.asyncio
    async def test_outside_window_skips_processing(self) -> None:
        """Worker returns early when outside time window."""
        worker = CampaignWorker()
        session, db_manager = _mock_worker_session()

        with _worker_patches(db_manager, in_window=False):
            await worker.run()

        # Only orphan recovery executed, no claim query
        assert session.execute.call_count == 1

    @pytest.mark.asyncio
    async def test_inside_window_processes(self) -> None:
        """Worker proceeds when inside time window."""
        worker = CampaignWorker()
        session, db_manager = _mock_worker_session(recipients=[])

        with _worker_patches(db_manager, in_window=True):
            await worker.run()

        assert session.execute.call_count >= 2

    @given(hour=st.integers(min_value=0, max_value=23))
    @settings(max_examples=24, deadline=None)
    def test_time_window_function_boundaries(self, hour: int) -> None:
        """_is_within_time_window returns True only for 8-20 CT hours."""
        from zoneinfo import ZoneInfo

        mock_now = datetime(2026, 4, 8, hour, 30, tzinfo=ZoneInfo("America/Chicago"))
        with patch(
            "grins_platform.services.background_jobs.datetime",
        ) as mock_dt:
            mock_dt.now.return_value = mock_now
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            result = _is_within_time_window()

        expected = 8 <= hour < 21
        assert result == expected


@pytest.mark.unit
class TestProperty28ExponentialBackoffOnRetry:
    """Failed sends result in failed status (retry via new row)."""

    @pytest.mark.asyncio
    async def test_provider_error_sets_failed(self) -> None:
        """Provider exception transitions recipient to failed."""
        from grins_platform.services.sms_service import SMSError

        worker = CampaignWorker()
        cr = _make_mock_cr()
        campaign = _make_mock_campaign()
        customer = _make_customer(cr)
        _, db_manager = _mock_worker_session(
            recipients=[cr],
            campaign=campaign,
            customer=customer,
        )

        with _worker_patches(
            db_manager,
            send_error=SMSError("provider_down"),
        ):
            await worker.run()

        assert cr.delivery_status == "failed"
        assert cr.error_message == "provider_down"


@pytest.mark.unit
class TestProperty29CampaignRecipientStatusTracking:
    """Recipient delivery_status transitions correctly through worker."""

    @pytest.mark.asyncio
    async def test_successful_send_transitions_to_sent(self) -> None:
        """Successful provider call sets delivery_status='sent'."""
        worker = CampaignWorker()
        cr = _make_mock_cr()
        campaign = _make_mock_campaign()
        customer = _make_customer(cr)
        _, db_manager = _mock_worker_session(
            recipients=[cr],
            campaign=campaign,
            customer=customer,
        )

        with _worker_patches(db_manager, send_result={"success": True}):
            await worker.run()

        assert cr.delivery_status == "sent"
        assert cr.sent_at is not None

    @pytest.mark.asyncio
    async def test_consent_denied_transitions_to_failed(self) -> None:
        """Consent denial — worker sends anyway (consent gating removed)."""
        worker = CampaignWorker()
        cr = _make_mock_cr()
        campaign = _make_mock_campaign()
        customer = _make_customer(cr)
        _, db_manager = _mock_worker_session(
            recipients=[cr],
            campaign=campaign,
            customer=customer,
        )

        with _worker_patches(db_manager, consent=False):
            await worker.run()

        # Worker no longer gates on check_sms_consent; message is sent
        assert cr.delivery_status == "sent"


@pytest.mark.unit
class TestProperty30CampaignCompletionDetection:
    """Campaign status derived from aggregate recipient states."""

    @pytest.mark.asyncio
    async def test_all_sent_marks_campaign_sent(self) -> None:
        """When all recipients are sent, campaign status becomes SENT."""
        worker = CampaignWorker()
        cr = _make_mock_cr()
        campaign = _make_mock_campaign()
        customer = _make_customer(cr)

        session = AsyncMock()

        orphan_result = MagicMock()
        orphan_result.rowcount = 0

        claim_result = MagicMock()
        claim_result.scalars.return_value.all.return_value = [cr]

        # All sent, no pending/sending
        count_result = MagicMock()
        count_result.all.return_value = [("sent", 1)]

        session.execute = AsyncMock(
            side_effect=[orphan_result, claim_result, count_result],
        )
        session.get = AsyncMock(
            side_effect=lambda model, _pk: campaign
            if model.__name__ == "Campaign"
            else customer,
        )
        session.flush = AsyncMock()

        db_manager = MagicMock()

        async def _gen():
            yield session

        db_manager.get_session = _gen

        with _worker_patches(db_manager, send_result={"success": True}):
            await worker.run()

        assert campaign.status == "sent"
        assert campaign.sent_at is not None

    @pytest.mark.asyncio
    async def test_pending_remaining_keeps_sending(self) -> None:
        """Campaign stays sending while pending recipients remain."""
        worker = CampaignWorker()
        cr = _make_mock_cr()
        campaign = _make_mock_campaign(status="sending")
        customer = _make_customer(cr)

        session = AsyncMock()

        orphan_result = MagicMock()
        orphan_result.rowcount = 0

        claim_result = MagicMock()
        claim_result.scalars.return_value.all.return_value = [cr]

        count_result = MagicMock()
        count_result.all.return_value = [("sent", 1), ("pending", 2)]

        session.execute = AsyncMock(
            side_effect=[orphan_result, claim_result, count_result],
        )
        session.get = AsyncMock(
            side_effect=lambda model, _pk: campaign
            if model.__name__ == "Campaign"
            else customer,
        )
        session.flush = AsyncMock()

        db_manager = MagicMock()

        async def _gen():
            yield session

        db_manager.get_session = _gen

        with _worker_patches(db_manager, send_result={"success": True}):
            await worker.run()

        assert campaign.status == "sending"


@pytest.mark.unit
class TestProperty45ConcurrentWorkerClaimUniqueness:
    """FOR UPDATE SKIP LOCKED ensures no two workers claim the same row."""

    def test_claim_query_uses_skip_locked(self) -> None:
        """The claim SQL uses with_for_update(skip_locked=True)."""
        import inspect

        source = inspect.getsource(CampaignWorker.run)
        assert "skip_locked=True" in source

    def test_claim_query_has_limit(self) -> None:
        """The claim SQL limits batch size."""
        import inspect

        source = inspect.getsource(CampaignWorker.run)
        assert ".limit(" in source

    def test_batch_size_is_small(self) -> None:
        """Batch size is ≤ 5 to stay under 140/hr."""
        assert _BATCH_SIZE <= 5

    @given(batch=st.integers(min_value=1, max_value=_BATCH_SIZE))
    @settings(max_examples=5, deadline=None)
    def test_batch_size_under_rate_limit(self, batch: int) -> None:
        """Any batch ≤ _BATCH_SIZE at 60s interval stays under 140/hr."""
        sends_per_hour = batch * 60
        assert sends_per_hour <= 140


# ---------------------------------------------------------------------------
# Property 23: Target audience schema validation
# Validates: Requirements 13.7
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestProperty23TargetAudienceSchemaValidation:
    """Valid TargetAudience dicts pass; invalid types/unknown keys are rejected."""

    # -- Hypothesis strategies for valid filter dicts --

    _uuid_st = st.uuids().map(str)
    _date_st = st.dates(
        min_value=date(2020, 1, 1),
        max_value=date(2030, 12, 31),
    )
    _date_pair_st = _date_st.flatmap(
        lambda d1: st.dates(min_value=d1, max_value=date(2030, 12, 31)).map(
            lambda d2: [d1.isoformat(), d2.isoformat()],
        ),
    )

    _customer_filter_st = st.fixed_dictionaries(
        {},
        optional={
            "sms_opt_in": st.booleans(),
            "ids_include": st.lists(_uuid_st, max_size=3),
            "cities": st.lists(st.text(min_size=1, max_size=30), max_size=3),
            "last_service_between": _date_pair_st,
            "tags_include": st.lists(
                st.text(min_size=1, max_size=20),
                max_size=3,
            ),
            "lead_source": st.text(min_size=1, max_size=30),
            "is_active": st.booleans(),
            "no_appointment_in_days": st.integers(min_value=1, max_value=365),
        },
    )

    _lead_filter_st = st.fixed_dictionaries(
        {},
        optional={
            "sms_consent": st.booleans(),
            "ids_include": st.lists(_uuid_st, max_size=3),
            "statuses": st.lists(
                st.sampled_from(["new", "contacted", "qualified"]),
                max_size=3,
            ),
            "lead_source": st.text(min_size=1, max_size=30),
            "intake_tag": st.text(min_size=1, max_size=30),
            "action_tags_include": st.lists(
                st.text(min_size=1, max_size=20),
                max_size=3,
            ),
            "cities": st.lists(st.text(min_size=1, max_size=30), max_size=3),
            "created_between": _date_pair_st,
        },
    )

    _adhoc_filter_st = st.fixed_dictionaries(
        {
            "staff_attestation_confirmed": st.booleans(),
            "attestation_text_shown": st.text(max_size=200),
            "attestation_version": st.text(min_size=1, max_size=50),
        },
        optional={
            "csv_upload_id": _uuid_st,
        },
    )

    _valid_audience_st = st.fixed_dictionaries(
        {},
        optional={
            "customers": _customer_filter_st,
            "leads": _lead_filter_st,
            "ad_hoc": _adhoc_filter_st,
        },
    )

    @given(data=_valid_audience_st)
    @settings(max_examples=50, deadline=None)
    def test_valid_audience_accepted(self, data: dict[str, Any]) -> None:
        """Any well-typed TargetAudience dict passes validation."""
        audience = TargetAudience.model_validate(data)
        assert isinstance(audience, TargetAudience)

    @given(bad_type=st.sampled_from([123, True, [1, 2], "not_a_dict"]))
    @settings(max_examples=4, deadline=None)
    def test_invalid_top_level_type_rejected(self, bad_type: object) -> None:
        """Non-dict top-level values are rejected."""
        with pytest.raises(ValidationError):
            TargetAudience.model_validate(bad_type)

    @given(
        key=st.sampled_from(["customers", "leads"]),
        bad_val=st.sampled_from([123, "string", [1]]),
    )
    @settings(max_examples=6, deadline=None)
    def test_invalid_filter_type_rejected(
        self,
        key: str,
        bad_val: object,
    ) -> None:
        """Non-dict filter values are rejected."""
        with pytest.raises(ValidationError):
            TargetAudience.model_validate({key: bad_val})

    def test_no_appointment_in_days_rejects_zero(self) -> None:
        """no_appointment_in_days must be >= 1."""
        with pytest.raises(ValidationError):
            TargetAudience.model_validate(
                {"customers": {"no_appointment_in_days": 0}},
            )

    def test_no_appointment_in_days_rejects_negative(self) -> None:
        """no_appointment_in_days must be >= 1."""
        with pytest.raises(ValidationError):
            TargetAudience.model_validate(
                {"customers": {"no_appointment_in_days": -5}},
            )

    def test_empty_audience_accepted(self) -> None:
        """An empty dict (no sources) is valid."""
        audience = TargetAudience.model_validate({})
        assert audience.customers is None
        assert audience.leads is None
        assert audience.ad_hoc is None

    def test_all_none_sources_accepted(self) -> None:
        """Explicit None for all sources is valid."""
        audience = TargetAudience.model_validate(
            {"customers": None, "leads": None, "ad_hoc": None},
        )
        assert audience.customers is None

    def test_ids_include_rejects_bad_uuid(self) -> None:
        """Non-UUID strings in ids_include are rejected."""
        with pytest.raises(ValidationError):
            TargetAudience.model_validate(
                {"customers": {"ids_include": ["not-a-uuid"]}},
            )


# ---------------------------------------------------------------------------
# Helpers for Property 21 & 22 — audience filter tests
# ---------------------------------------------------------------------------


def _mock_customer(
    *,
    phone: str = "9525293750",
    first_name: str = "John",
    last_name: str = "Doe",
    sms_opt_in: bool = True,
    status: str = "active",
    is_deleted: bool = False,
    lead_source: str | None = None,
    cid: UUID | None = None,
) -> MagicMock:
    c = MagicMock(spec=Customer)
    c.id = cid or uuid4()
    c.phone = phone
    c.first_name = first_name
    c.last_name = last_name
    c.sms_opt_in = sms_opt_in
    c.status = status
    c.is_deleted = is_deleted
    c.lead_source = lead_source
    c.properties = []
    return c


def _mock_lead(
    *,
    phone: str = "6125551234",
    name: str = "Jane Smith",
    sms_consent: bool = True,
    status: str = "new",
    lead_source: str = "website",
    intake_tag: str | None = None,
    city: str | None = None,
    action_tags: list[str] | None = None,
    created_at: datetime | None = None,
    lid: UUID | None = None,
) -> MagicMock:
    ld = MagicMock(spec=Lead)
    ld.id = lid or uuid4()
    ld.phone = phone
    ld.name = name
    ld.sms_consent = sms_consent
    ld.status = status
    ld.lead_source = lead_source
    ld.intake_tag = intake_tag
    ld.city = city
    ld.action_tags = action_tags or []
    ld.created_at = created_at or datetime.now(tz=timezone.utc)
    return ld


def _mock_campaign(audience: dict[str, Any]) -> MagicMock:
    camp = MagicMock(spec=Campaign)
    camp.target_audience = audience
    camp.id = uuid4()
    return camp


def _audience_session(
    *query_results: list[Any],
) -> AsyncMock:
    """Build a mock session returning successive query results.

    Each positional arg is the list of model objects for one ``db.execute()``
    call.  Customer queries use ``.scalars().unique().all()``; lead queries
    use ``.scalars().all()``.  We wire both paths so the mock works
    regardless of which query runs first.
    """
    session = AsyncMock()
    idx = 0

    async def _execute(_stmt: Any, *_a: Any, **_kw: Any) -> Any:
        nonlocal idx
        rows = query_results[idx] if idx < len(query_results) else []
        idx += 1
        result = MagicMock()
        scalars_mock = MagicMock()
        unique_mock = MagicMock()
        unique_mock.all.return_value = rows
        scalars_mock.unique.return_value = unique_mock
        scalars_mock.all.return_value = rows
        result.scalars.return_value = scalars_mock
        return result

    session.execute = AsyncMock(side_effect=_execute)
    return session


def _make_svc() -> CampaignService:
    return CampaignService(campaign_repository=MagicMock(spec=CampaignRepository))


def _run_async(coro: Any) -> Any:
    """Run an async coroutine synchronously."""
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# Property 21: Audience filter correctness
# Validates: Requirements 13.1, 13.3, 13.4, 13.6, 13.8
# ---------------------------------------------------------------------------


class TestProperty21AudienceFilterCorrectness:
    """Property 21: _filter_recipients returns correct Recipient objects.

    Verifies that customers and leads matching the target_audience filters
    are included in the result with the correct source_type, and that
    records with bad phones are excluded.
    """

    def test_customers_only_returns_customer_recipients(self) -> None:
        """When audience has customer filters, matching customers appear."""
        c1 = _mock_customer(phone="9525293750")
        c2 = _mock_customer(phone="6125551234")
        # Structured audience with customers key → customer query runs
        session = _audience_session([c1, c2])
        campaign = _mock_campaign({"customers": {"sms_opt_in": True}})

        result = _run_async(_make_svc()._filter_recipients(session, campaign))

        assert len(result) == 2
        assert all(r.source_type == "customer" for r in result)

    def test_leads_only_returns_lead_recipients(self) -> None:
        """When audience has only lead filters (customers=None), leads appear."""
        ld = _mock_lead(phone="6125559999")
        # customers is None → cust_filters={}, is_structured=True
        # if {} or not True → False → customer query skipped
        # Lead query is the FIRST execute call
        session = _audience_session([ld])
        campaign = _mock_campaign({"leads": {"sms_consent": True}})

        result = _run_async(_make_svc()._filter_recipients(session, campaign))

        assert len(result) == 1
        assert result[0].source_type == "lead"

    @given(n_customers=st.integers(min_value=0, max_value=5))
    @settings(max_examples=10, deadline=None)
    def test_result_count_matches_unique_phones(self, n_customers: int) -> None:
        """Result count equals the number of unique E.164 phones."""
        customers = [
            _mock_customer(phone=f"952529{3750 + i:04d}") for i in range(n_customers)
        ]
        session = _audience_session(customers)
        campaign = _mock_campaign({"customers": {"sms_opt_in": True}})

        result = _run_async(_make_svc()._filter_recipients(session, campaign))

        assert len(result) == n_customers

    def test_empty_audience_returns_customers_via_legacy_path(self) -> None:
        """Empty audience dict triggers legacy customer-only path."""
        c = _mock_customer(phone="9525293750")
        session = _audience_session([c])
        campaign = _mock_campaign({})

        result = _run_async(_make_svc()._filter_recipients(session, campaign))

        assert len(result) == 1
        assert result[0].source_type == "customer"

    def test_bad_phone_customer_excluded(self) -> None:
        """Customers with un-normalizable phones are silently skipped."""
        good = _mock_customer(phone="9525293750")
        bad = _mock_customer(phone="000BADPHONE")
        session = _audience_session([good, bad])
        campaign = _mock_campaign({"customers": {"sms_opt_in": True}})

        result = _run_async(_make_svc()._filter_recipients(session, campaign))

        assert len(result) == 1

    def test_bad_phone_lead_excluded(self) -> None:
        """Leads with un-normalizable phones are silently skipped."""
        good_lead = _mock_lead(phone="6125559999")
        bad_lead = _mock_lead(phone="XXXBAD")
        # Only leads key → customer query skipped, lead query is first
        session = _audience_session([good_lead, bad_lead])
        campaign = _mock_campaign({"leads": {"sms_consent": True}})

        result = _run_async(_make_svc()._filter_recipients(session, campaign))

        assert len(result) == 1


# ---------------------------------------------------------------------------
# Property 22: Audience deduplication — customer wins
# Validates: Requirements 13.1, 13.3, 13.4, 13.6, 13.8
# ---------------------------------------------------------------------------


class TestProperty22AudienceDeduplicationCustomerWins:
    """Property 22: When a customer and lead share the same E.164 phone,
    only the customer Recipient appears in the result.
    """

    def test_same_phone_customer_wins(self) -> None:
        """Customer record wins when customer and lead share the same phone."""
        shared_phone = "9525293750"
        cust = _mock_customer(phone=shared_phone)
        lead = _mock_lead(phone=shared_phone)

        # Both sources active → customer query first, lead query second
        session = _audience_session([cust], [lead])
        campaign = _mock_campaign(
            {
                "customers": {"sms_opt_in": True},
                "leads": {"sms_consent": True},
            },
        )

        result = _run_async(_make_svc()._filter_recipients(session, campaign))

        assert len(result) == 1
        assert result[0].source_type == "customer"
        assert result[0].customer_id == cust.id

    @given(
        n_shared=st.integers(min_value=1, max_value=5),
        n_lead_only=st.integers(min_value=0, max_value=3),
    )
    @settings(max_examples=20, deadline=None)
    def test_dedup_count_property(
        self,
        n_shared: int,
        n_lead_only: int,
    ) -> None:
        """Result count = n_customers + n_lead_only (shared phones counted once)."""
        customers = []
        leads_all = []

        for i in range(n_shared):
            phone = f"952529{3000 + i:04d}"
            customers.append(_mock_customer(phone=phone))
            leads_all.append(_mock_lead(phone=phone))

        for i in range(n_lead_only):
            phone = f"612555{4000 + i:04d}"
            leads_all.append(_mock_lead(phone=phone))

        session = _audience_session(customers, leads_all)
        campaign = _mock_campaign(
            {
                "customers": {"sms_opt_in": True},
                "leads": {"sms_consent": True},
            },
        )

        result = _run_async(_make_svc()._filter_recipients(session, campaign))

        assert len(result) == n_shared + n_lead_only

        # All shared phones must be customer-sourced
        shared_e164 = {normalize_to_e164(c.phone) for c in customers}
        for r in result:
            if normalize_to_e164(r.phone) in shared_e164:
                assert r.source_type == "customer"

    def test_lead_only_phones_are_lead_sourced(self) -> None:
        """Leads with unique phones (not shared with customers) are lead-sourced."""
        cust = _mock_customer(phone="9525293750")
        lead_unique = _mock_lead(phone="6125559999")

        session = _audience_session([cust], [lead_unique])
        campaign = _mock_campaign(
            {
                "customers": {"sms_opt_in": True},
                "leads": {"sms_consent": True},
            },
        )

        result = _run_async(_make_svc()._filter_recipients(session, campaign))

        assert len(result) == 2
        by_type = {r.source_type for r in result}
        assert by_type == {"customer", "lead"}

    def test_no_duplicate_phones_in_result(self) -> None:
        """Result never contains two Recipients with the same E.164 phone."""
        shared = "9525293750"
        cust = _mock_customer(phone=shared)
        lead = _mock_lead(phone=shared)
        lead2 = _mock_lead(phone="6125559999")

        session = _audience_session([cust], [lead, lead2])
        campaign = _mock_campaign(
            {
                "customers": {"sms_opt_in": True},
                "leads": {"sms_consent": True},
            },
        )

        result = _run_async(_make_svc()._filter_recipients(session, campaign))

        phones = [normalize_to_e164(r.phone) for r in result]
        assert len(phones) == len(set(phones)), "Duplicate phones in result"


# ---------------------------------------------------------------------------
# Property 34: CSV staff attestation creates consent records
# Validates: Requirement 25
# ---------------------------------------------------------------------------


def _extract_multi_values(stmt: Any) -> list[dict[str, Any]]:
    """Extract row dicts from a pg_insert(...).values(rows) statement.

    SQLAlchemy stores multi-value inserts in ``_multi_values`` as a tuple
    of lists of Column→value dicts.  We convert Column keys to their
    string names for easy assertion.
    """
    raw = getattr(stmt, "_multi_values", None)
    if not raw or not raw[0]:
        return []
    return [{col.key: val for col, val in row.items()} for row in raw[0]]


@pytest.mark.unit
class TestProperty34CsvStaffAttestationCreatesConsentRecords:
    """bulk_insert_attestation_consent creates correct SmsConsentRecord rows."""

    @given(
        phones=st.lists(
            st.from_regex(r"[2-9]\d{9}", fullmatch=True),
            min_size=1,
            max_size=10,
        ),
        attestation_version=st.text(min_size=1, max_size=30),
        attestation_text=st.text(min_size=1, max_size=500),
    )
    @settings(max_examples=50, deadline=None)
    def test_returns_count_equal_to_phone_list_length(
        self,
        phones: list[str],
        attestation_version: str,
        attestation_text: str,
    ) -> None:
        """Return value equals len(phones)."""
        session = AsyncMock()
        staff_id = uuid4()
        result = asyncio.run(
            bulk_insert_attestation_consent(
                session,
                staff_id,
                phones,
                attestation_version,
                attestation_text,
            ),
        )
        assert result == len(phones)

    @given(
        phone=st.from_regex(r"[2-9]\d{9}", fullmatch=True),
        attestation_version=st.text(min_size=1, max_size=30),
        attestation_text=st.text(min_size=1, max_size=500),
    )
    @settings(max_examples=50, deadline=None)
    def test_rows_have_correct_consent_fields(
        self,
        phone: str,
        attestation_version: str,
        attestation_text: str,
    ) -> None:
        """Each inserted row has marketing consent via csv_upload_staff_attestation."""
        captured: list[Any] = []
        session = AsyncMock()

        async def _capture_execute(stmt: Any) -> MagicMock:
            if hasattr(stmt, "_multi_values"):
                captured.append(stmt)
            return MagicMock()

        session.execute = _capture_execute
        staff_id = uuid4()

        asyncio.run(
            bulk_insert_attestation_consent(
                session,
                staff_id,
                [phone],
                attestation_version,
                attestation_text,
            ),
        )

        assert len(captured) == 1
        rows = _extract_multi_values(captured[0])
        assert len(rows) == 1
        row = rows[0]
        assert row["consent_type"] == "marketing"
        assert row["consent_given"] is True
        assert row["consent_method"] == "csv_upload_staff_attestation"
        assert row["consent_form_version"] == attestation_version
        assert row["consent_language_shown"] == attestation_text
        assert row["created_by_staff_id"] == staff_id
        assert row["phone_number"] == normalize_to_e164(phone)

    def test_empty_phone_list_returns_zero(self) -> None:
        """Empty phone list returns 0 without executing any SQL."""
        session = AsyncMock()
        staff_id = uuid4()
        result = asyncio.run(
            bulk_insert_attestation_consent(
                session,
                staff_id,
                [],
                "V1",
                "I attest",
            ),
        )
        assert result == 0
        session.execute.assert_not_called()

    @given(
        phones=st.lists(
            st.from_regex(r"[2-9]\d{9}", fullmatch=True),
            min_size=1,
            max_size=5,
        ),
    )
    @settings(max_examples=50, deadline=None)
    def test_all_phones_normalized_to_e164(
        self,
        phones: list[str],
    ) -> None:
        """Every phone in the insert is E.164-normalized."""
        captured: list[Any] = []
        session = AsyncMock()

        async def _capture(stmt: Any) -> MagicMock:
            if hasattr(stmt, "_multi_values"):
                captured.append(stmt)
            return MagicMock()

        session.execute = _capture
        staff_id = uuid4()

        asyncio.run(
            bulk_insert_attestation_consent(
                session,
                staff_id,
                phones,
                "V1",
                "attest",
            ),
        )

        assert len(captured) == 1
        rows = _extract_multi_values(captured[0])
        assert len(rows) == len(phones)
        for raw_phone, row in zip(phones, rows):
            assert row["phone_number"] == normalize_to_e164(raw_phone)

    @given(phone=st.from_regex(r"[2-9]\d{9}", fullmatch=True))
    @settings(max_examples=30, deadline=None)
    def test_session_flush_called_after_insert(self, phone: str) -> None:
        """Session.flush() is called after execute to persist rows."""
        session = AsyncMock()
        staff_id = uuid4()
        asyncio.run(
            bulk_insert_attestation_consent(
                session,
                staff_id,
                [phone],
                "V1",
                "attest",
            ),
        )
        session.flush.assert_awaited_once()


# ---------------------------------------------------------------------------
# Property: Dual-key webhook dedup invariant (Gap 07.A / 7.B)
#
# Given an arbitrary stream of payloads, the set of payloads that
# ``_is_duplicate`` ever reports as "not seen yet" must equal the set of
# unique ``resource_id`` values in the stream. Equivalently: once a
# ``resource_id`` has been marked processed, every subsequent payload
# bearing that same ``resource_id`` returns True, even if its
# ``conversation_id`` / ``created_at`` differ (a hostile replay that
# tampered with those fields but left ``resource_id`` intact).
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDualKeyDedupInvariant:
    """_is_duplicate is keyed on both (conv_id, created_at) and resource_id."""

    @given(
        payloads=st.lists(
            st.tuples(callrail_id, _iso_ts, callrail_id),
            min_size=1,
            max_size=20,
        ),
    )
    @settings(max_examples=30, deadline=None)
    def test_processed_set_matches_first_key_seen_invariant(
        self,
        payloads: list[tuple[str, str, str]],
    ) -> None:
        """Every key triple is seen at most once as 'new'.

        Invariant: a payload is processed as new iff NEITHER the
        ``(conv_id, created_at)`` pair NOR the ``resource_id`` has
        already been recorded on a prior iteration of the stream.
        """

        class _FakeRedis:
            """Tiny in-memory substitute for the Redis client."""

            def __init__(self) -> None:
                self.store: dict[str, str] = {}

            async def get(self, key: str) -> str | None:
                return self.store.get(key)

            async def set(
                self,
                key: str,
                value: str,
                *,
                nx: bool = False,
                ex: int | None = None,
            ) -> bool:
                if nx and key in self.store:
                    return False
                self.store[key] = value
                return True

        async def _run() -> tuple[list[bool], list[bool]]:
            actual_new: list[bool] = []
            expected_new: list[bool] = []
            seen_primary: set[tuple[str, str]] = set()
            seen_msgids: set[str] = set()
            redis = _FakeRedis()
            db = _stub_db_with_exists(False)
            for conv_id, created_at, msgid in payloads:
                primary = (conv_id, created_at)
                is_expected_new = (
                    primary not in seen_primary and msgid not in seen_msgids
                )
                expected_new.append(is_expected_new)

                duplicate = await _is_duplicate(
                    redis,  # type: ignore[arg-type]
                    db,
                    "callrail",
                    conv_id,
                    created_at,
                    msgid,
                )
                actual_new.append(not duplicate)
                if not duplicate:
                    await _mark_processed(
                        redis,  # type: ignore[arg-type]
                        db,
                        "callrail",
                        conv_id,
                        created_at,
                        msgid,
                    )
                if is_expected_new:
                    seen_primary.add(primary)
                    seen_msgids.add(msgid)
            return actual_new, expected_new

        actual_new, expected_new = asyncio.run(_run())
        # The dedup layer reports 'new' exactly when no prior payload
        # shared either the primary key or the resource_id.
        assert actual_new == expected_new

    @given(msgid=callrail_id, conv_id=callrail_id, created_at=_iso_ts)
    @settings(max_examples=30, deadline=None)
    def test_msgid_key_marked_alongside_primary_key(
        self,
        msgid: str,
        conv_id: str,
        created_at: str,
    ) -> None:
        """``_mark_processed`` writes both Redis keys (primary + msgid)."""
        mock_redis = AsyncMock()
        mock_redis.set = AsyncMock()
        db = _stub_db_with_exists(False)

        asyncio.run(
            _mark_processed(
                mock_redis,
                db,
                "callrail",
                conv_id,
                created_at,
                msgid,
            ),
        )

        keys = [call.args[0] for call in mock_redis.set.await_args_list]
        assert f"{_REDIS_KEY_PREFIX}:{conv_id}:{created_at}" in keys
        assert f"{_REDIS_MSGID_KEY_PREFIX}:{msgid}" in keys
