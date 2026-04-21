"""Unit test verifying provider_thread_id storage on outbound sends.

Validates: Requirements 19.1, 19.2, 19.3
- 19.1: CallRailProvider.send_text() extracts thread_resource_id from response
- 19.2: SMSService.send_message() stores provider_thread_id on SentMessage
- 19.3: Correlator matches against sent_messages.provider_thread_id
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from grins_platform.schemas.ai import MessageType
from grins_platform.services.sms.base import ProviderSendResult
from grins_platform.services.sms.recipient import Recipient
from grins_platform.services.sms_service import SMSService

if TYPE_CHECKING:
    from grins_platform.models.sent_message import SentMessage


def _make_service(
    *,
    provider_thread_id: str | None = "SMTabc123",
) -> tuple[SMSService, AsyncMock]:
    """Build an SMSService with a mock provider returning the given thread_id."""
    session = AsyncMock()
    added: list[SentMessage] = []
    session.add = MagicMock(side_effect=lambda obj: added.append(obj))
    session.flush = AsyncMock()
    session.refresh = AsyncMock()

    provider = AsyncMock()
    provider.provider_name = "callrail"
    provider.send_text = AsyncMock(
        return_value=ProviderSendResult(
            provider_message_id="conv_999",
            provider_conversation_id="conv_999",
            provider_thread_id=provider_thread_id,
            status="sent",
            raw_response={"id": "conv_999"},
        ),
    )

    svc = SMSService(session, provider=provider)
    svc._added = added  # type: ignore[attr-defined]
    return svc, session


@pytest.mark.unit
class TestThreadIdStorageOnSend:
    """Req 19.2: provider_thread_id is stored on SentMessage after send."""

    @pytest.mark.asyncio
    @patch("grins_platform.services.sms_service.check_sms_consent", return_value=True)
    async def test_thread_id_stored_on_sent_message(self, _consent: MagicMock) -> None:
        """After successful send, SentMessage.provider_thread_id == provider result."""
        svc, _session = _make_service(provider_thread_id="SMTthread789")
        recipient = Recipient.from_adhoc("+16125551234")

        result = await svc.send_message(
            recipient=recipient,
            message="Test",
            message_type=MessageType.CAMPAIGN,
            consent_type="marketing",
            skip_formatting=True,
        )

        assert result["success"] is True
        added = svc._added  # type: ignore[attr-defined]
        assert len(added) == 1
        sent_msg: SentMessage = added[0]
        assert sent_msg.provider_thread_id == "SMTthread789"
        assert sent_msg.provider_conversation_id == "conv_999"

    @pytest.mark.asyncio
    @patch("grins_platform.services.sms_service.check_sms_consent", return_value=True)
    async def test_null_thread_id_stored_when_absent(
        self,
        _consent: MagicMock,
    ) -> None:
        """When provider returns no thread_id, SentMessage stores None."""
        svc, _session = _make_service(provider_thread_id=None)
        recipient = Recipient.from_adhoc("+16125551234")

        result = await svc.send_message(
            recipient=recipient,
            message="Test",
            message_type=MessageType.CAMPAIGN,
            consent_type="marketing",
            skip_formatting=True,
        )

        assert result["success"] is True
        added = svc._added  # type: ignore[attr-defined]
        assert len(added) == 1
        assert added[0].provider_thread_id is None


# ---------------------------------------------------------------------------
# Gap 03.B — supersession marker on confirmation-like outbound
# ---------------------------------------------------------------------------


def _was_supersession_update(call: Any) -> bool:
    """Inspect a ``session.execute`` call and detect whether it was the
    supersession UPDATE (vs. any other statement).

    The marker compiles to ``UPDATE sent_messages SET superseded_at = ...``
    so a stringified view of the bound statement is enough to classify.
    """
    if not call.args:
        return False
    stmt = call.args[0]
    try:
        compiled = str(stmt.compile(compile_kwargs={"literal_binds": True}))
    except Exception:
        compiled = str(stmt)
    lowered = compiled.lower()
    return "update" in lowered and "superseded_at" in lowered


@pytest.mark.unit
class TestSupersessionOnSend:
    """Gap 03.B: confirmation-like outbounds tombstone their predecessors."""

    @pytest.mark.asyncio
    @patch("grins_platform.services.sms_service.check_sms_consent", return_value=True)
    async def test_confirmation_like_send_runs_supersession_update(
        self,
        _consent: MagicMock,
    ) -> None:
        """Sending an APPOINTMENT_RESCHEDULE with appointment_id triggers the UPDATE."""
        from uuid import uuid4

        svc, session = _make_service()
        appt_id = uuid4()
        recipient = Recipient.from_adhoc("+16125551234")

        await svc.send_message(
            recipient=recipient,
            message="Moved to Wed.",
            message_type=MessageType.APPOINTMENT_RESCHEDULE,
            consent_type="transactional",
            appointment_id=appt_id,
            skip_formatting=True,
        )

        supersede_calls = [
            c for c in session.execute.call_args_list if _was_supersession_update(c)
        ]
        assert len(supersede_calls) == 1

    @pytest.mark.asyncio
    @patch("grins_platform.services.sms_service.check_sms_consent", return_value=True)
    async def test_non_confirmation_like_send_skips_supersession(
        self,
        _consent: MagicMock,
    ) -> None:
        """ON_THE_WAY is not confirmation-like → no supersession UPDATE."""
        from uuid import uuid4

        svc, session = _make_service()
        appt_id = uuid4()
        recipient = Recipient.from_adhoc("+16125551234")

        await svc.send_message(
            recipient=recipient,
            message="Crew en route.",
            message_type=MessageType.ON_THE_WAY,
            consent_type="transactional",
            appointment_id=appt_id,
            skip_formatting=True,
        )

        supersede_calls = [
            c for c in session.execute.call_args_list if _was_supersession_update(c)
        ]
        assert len(supersede_calls) == 0

    @pytest.mark.asyncio
    @patch("grins_platform.services.sms_service.check_sms_consent", return_value=True)
    async def test_send_without_appointment_id_skips_supersession(
        self,
        _consent: MagicMock,
    ) -> None:
        """Lead-confirmation sends (no appointment) must not fire supersession."""
        svc, session = _make_service()
        recipient = Recipient.from_adhoc("+16125551234")

        await svc.send_message(
            recipient=recipient,
            message="Thanks for your inquiry!",
            message_type=MessageType.LEAD_CONFIRMATION,
            consent_type="transactional",
            skip_formatting=True,
        )

        supersede_calls = [
            c for c in session.execute.call_args_list if _was_supersession_update(c)
        ]
        assert len(supersede_calls) == 0

    @pytest.mark.asyncio
    @patch("grins_platform.services.sms_service.check_sms_consent", return_value=True)
    async def test_supersession_update_failure_does_not_fail_send(
        self,
        _consent: MagicMock,
    ) -> None:
        """A failing supersession UPDATE still returns the send as successful."""
        from uuid import uuid4

        svc, session = _make_service()
        appt_id = uuid4()
        recipient = Recipient.from_adhoc("+16125551234")

        # Wrap session.execute so supersession UPDATEs raise, but inserts
        # continue to no-op (AsyncMock default).
        original_execute = session.execute

        async def _failing_execute(stmt: Any, *args: Any, **kwargs: Any) -> Any:
            try:
                compiled = str(
                    stmt.compile(compile_kwargs={"literal_binds": True}),
                ).lower()
            except Exception:
                compiled = str(stmt).lower()
            if "update" in compiled and "superseded_at" in compiled:
                msg = "supersession down"
                raise RuntimeError(msg)
            return await original_execute(stmt, *args, **kwargs)

        session.execute = AsyncMock(side_effect=_failing_execute)

        result = await svc.send_message(
            recipient=recipient,
            message="Moved to Wed.",
            message_type=MessageType.APPOINTMENT_RESCHEDULE,
            consent_type="transactional",
            appointment_id=appt_id,
            skip_formatting=True,
        )

        assert result["success"] is True
