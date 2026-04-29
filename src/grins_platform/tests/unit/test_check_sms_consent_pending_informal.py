"""Unit tests for `check_sms_consent(require_no_pending_informal=True)`.

Validates Gap 06 — pending INFORMAL_OPT_OUT alert suppresses marketing +
non-urgent transactional sends, but urgent transactional still goes through.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from grins_platform.services.sms.consent import check_sms_consent


def _fake_session(*, has_hard_stop: bool, has_pending_alert: bool, customer_id=None):
    """Build an AsyncMock whose `.execute()` routes based on FROM-clause text.

    str(stmt) of a SQLAlchemy Select emits e.g. ``SELECT ... FROM alerts``
    even when bound params are elided; the table name reliably differentiates
    the consent module's internal queries:

    - ``FROM sms_consent_records``: either _has_hard_stop (first) or
      _has_marketing_opt_in (last). Call ordering disambiguates.
    - ``FROM customers``: _resolve_customer_id_by_phone OR marketing
      opt-in fallback (Customer.sms_opt_in check).
    - ``FROM alerts``: _has_open_informal_opt_out_alert.
    - ``FROM leads``: marketing opt-in fallback.
    """
    session = AsyncMock()

    state = {"sms_consent_calls": 0, "customer_calls": 0}

    async def _execute(stmt):
        text = str(stmt).lower()
        if "from alerts" in text:
            return SimpleNamespace(
                scalar_one_or_none=lambda: uuid4() if has_pending_alert else None,
            )
        if "from sms_consent_records" in text:
            state["sms_consent_calls"] += 1
            # First sms_consent_records call is always _has_hard_stop.
            if state["sms_consent_calls"] == 1:
                return SimpleNamespace(
                    scalar_one_or_none=(lambda: uuid4() if has_hard_stop else None),
                )
            # Subsequent calls are marketing opt-in look-ups → default no.
            return SimpleNamespace(scalar_one_or_none=lambda: None)
        if "from customers" in text:
            state["customer_calls"] += 1
            # First customers call is _resolve_customer_id_by_phone.
            if state["customer_calls"] == 1:
                return SimpleNamespace(scalar_one_or_none=lambda: customer_id)
            return SimpleNamespace(scalar_one_or_none=lambda: None)
        return SimpleNamespace(scalar_one_or_none=lambda: None)

    session.execute.side_effect = _execute
    return session


@pytest.mark.unit
class TestPendingInformalGating:
    """check_sms_consent must honor pending INFORMAL_OPT_OUT alerts."""

    @pytest.mark.asyncio
    async def test_pending_alert_blocks_marketing(self) -> None:
        session = _fake_session(
            has_hard_stop=False,
            has_pending_alert=True,
            customer_id=uuid4(),
        )
        allowed = await check_sms_consent(
            session,
            "+16125551234",
            "marketing",
            require_no_pending_informal=True,
        )
        assert allowed is False

    @pytest.mark.asyncio
    async def test_pending_alert_blocks_reminder_transactional(self) -> None:
        """Non-urgent transactional (caller passes require_no_pending_informal=True)."""
        session = _fake_session(
            has_hard_stop=False,
            has_pending_alert=True,
            customer_id=uuid4(),
        )
        allowed = await check_sms_consent(
            session,
            "+16125551234",
            "transactional",
            require_no_pending_informal=True,
        )
        assert allowed is False

    @pytest.mark.asyncio
    async def test_pending_alert_does_not_block_urgent_transactional(self) -> None:
        """Urgent callers pass require_no_pending_informal=False — allowed."""
        session = _fake_session(
            has_hard_stop=False,
            has_pending_alert=True,
            customer_id=uuid4(),
        )
        allowed = await check_sms_consent(
            session,
            "+16125551234",
            "transactional",
            require_no_pending_informal=False,
        )
        assert allowed is True

    @pytest.mark.asyncio
    async def test_no_pending_alert_returns_base_consent_transactional(self) -> None:
        """With no alert, transactional always passes (EBR)."""
        session = _fake_session(
            has_hard_stop=False,
            has_pending_alert=False,
            customer_id=uuid4(),
        )
        allowed = await check_sms_consent(
            session,
            "+16125551234",
            "transactional",
            require_no_pending_informal=True,
        )
        assert allowed is True

    @pytest.mark.asyncio
    async def test_hard_stop_still_wins(self) -> None:
        """Hard-STOP blocks even when no pending alert and urgent."""
        session = _fake_session(
            has_hard_stop=True,
            has_pending_alert=False,
            customer_id=uuid4(),
        )
        allowed = await check_sms_consent(
            session,
            "+16125551234",
            "transactional",
            require_no_pending_informal=False,
        )
        assert allowed is False

    @pytest.mark.asyncio
    async def test_phone_only_lead_pending_alert_allows(self) -> None:
        """No customer resolution → no pending-alert block."""
        session = _fake_session(
            has_hard_stop=False,
            has_pending_alert=True,  # will never be queried because customer=None
            customer_id=None,
        )
        allowed = await check_sms_consent(
            session,
            "+16125551234",
            "transactional",
            require_no_pending_informal=True,
        )
        assert allowed is True
