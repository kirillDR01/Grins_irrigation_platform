"""Job confirmation service — Y/R/C reply handling.

Parses inbound SMS replies to appointment confirmation messages,
transitions appointment status, and creates reschedule requests.

Validates: CRM Changes Update 2 Req 24.1-24.8, 25.1
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from sqlalchemy import select

from grins_platform.log_config import LoggerMixin, get_logger
from grins_platform.models.enums import (
    AppointmentStatus,
    ConfirmationKeyword,
    MessageType,
)
from grins_platform.models.job_confirmation import (
    JobConfirmationResponse,
    RescheduleRequest,
)
from grins_platform.models.sent_message import SentMessage

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)

# Keyword mapping: normalised text → ConfirmationKeyword
_KEYWORD_MAP: dict[str, ConfirmationKeyword] = {
    "y": ConfirmationKeyword.CONFIRM,
    "yes": ConfirmationKeyword.CONFIRM,
    "confirm": ConfirmationKeyword.CONFIRM,
    "confirmed": ConfirmationKeyword.CONFIRM,
    "r": ConfirmationKeyword.RESCHEDULE,
    "reschedule": ConfirmationKeyword.RESCHEDULE,
    "c": ConfirmationKeyword.CANCEL,
    "cancel": ConfirmationKeyword.CANCEL,
}

# Auto-reply templates
_AUTO_REPLIES: dict[ConfirmationKeyword, str] = {
    ConfirmationKeyword.CONFIRM: ("Your appointment has been confirmed. See you then!"),
    ConfirmationKeyword.RESCHEDULE: (
        "We received your reschedule request. "
        "Our team will reach out with alternative times shortly."
    ),
    ConfirmationKeyword.CANCEL: (
        "Your appointment has been cancelled. "
        "Please contact us if you'd like to reschedule."
    ),
}


def parse_confirmation_reply(body: str) -> ConfirmationKeyword | None:
    """Parse a Y/R/C keyword from an SMS body.

    Case-insensitive, whitespace-trimmed. Returns None for unrecognised input.

    Validates: CRM Changes Update 2 Req 24.1
    """
    return _KEYWORD_MAP.get(body.strip().lower())


class JobConfirmationService(LoggerMixin):
    """Orchestrates appointment confirmation via SMS replies.

    Validates: CRM Changes Update 2 Req 24.1-24.8, 25.1
    """

    DOMAIN = "confirmation"

    def __init__(self, db: AsyncSession) -> None:
        super().__init__()
        self.db = db

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def handle_confirmation(
        self,
        thread_id: str,
        keyword: ConfirmationKeyword | None,
        raw_body: str,
        from_phone: str,
        provider_sid: str | None = None,
    ) -> dict[str, Any]:
        """Process an inbound confirmation reply.

        Correlates via provider_thread_id on sent_messages, then dispatches
        to the appropriate handler based on keyword.

        Validates: CRM Changes Update 2 Req 24.2-24.8
        """
        self.log_started(
            "handle_confirmation",
            thread_id=thread_id,
            keyword=keyword.value if keyword else None,
        )

        # 1. Correlate thread_id → original confirmation SMS
        original = await self._find_confirmation_message(thread_id)
        if original is None:
            self.log_rejected(
                "handle_confirmation",
                reason="no_matching_confirmation",
                thread_id=thread_id,
            )
            return {"action": "no_match", "thread_id": thread_id}

        appointment_id: UUID = original.appointment_id  # type: ignore[assignment]
        job_id: UUID = original.job_id  # type: ignore[assignment]
        customer_id: UUID = original.customer_id  # type: ignore[assignment]

        # 2. Record the confirmation response
        response = JobConfirmationResponse(
            job_id=job_id,
            appointment_id=appointment_id,
            sent_message_id=original.id,
            customer_id=customer_id,
            from_phone=from_phone,
            reply_keyword=keyword.value if keyword else None,
            raw_reply_body=raw_body,
            provider_sid=provider_sid,
            status="pending",
        )
        self.db.add(response)
        await self.db.flush()

        # 3. Dispatch by keyword
        if keyword == ConfirmationKeyword.CONFIRM:
            result = await self._handle_confirm(response, appointment_id)
        elif keyword == ConfirmationKeyword.RESCHEDULE:
            result = await self._handle_reschedule(
                response,
                appointment_id,
                job_id,
                customer_id,
                raw_body,
            )
        elif keyword == ConfirmationKeyword.CANCEL:
            result = await self._handle_cancel(response, appointment_id)
        else:
            result = await self._handle_needs_review(response)

        self.log_completed(
            "handle_confirmation",
            result_action=result.get("action"),
            appointment_id=str(appointment_id),
        )
        return result

    # ------------------------------------------------------------------
    # Internal handlers
    # ------------------------------------------------------------------

    async def _handle_confirm(
        self,
        response: JobConfirmationResponse,
        appointment_id: UUID,
    ) -> dict[str, Any]:
        """CONFIRM: SCHEDULED → CONFIRMED + auto-reply."""
        from grins_platform.models.appointment import Appointment  # noqa: PLC0415

        appt = await self.db.get(Appointment, appointment_id)
        if appt and appt.status == AppointmentStatus.SCHEDULED.value:
            appt.status = AppointmentStatus.CONFIRMED.value
            await self.db.flush()

        response.status = "confirmed"
        response.processed_at = datetime.now(tz=timezone.utc)
        await self.db.flush()

        return {
            "action": "confirmed",
            "appointment_id": str(appointment_id),
            "auto_reply": _AUTO_REPLIES[ConfirmationKeyword.CONFIRM],
        }

    async def _handle_reschedule(
        self,
        response: JobConfirmationResponse,
        appointment_id: UUID,
        job_id: UUID,
        customer_id: UUID,
        raw_body: str,
    ) -> dict[str, Any]:
        """RESCHEDULE: create reschedule_request + follow-up SMS."""
        reschedule = RescheduleRequest(
            job_id=job_id,
            appointment_id=appointment_id,
            customer_id=customer_id,
            original_reply_id=response.id,
            raw_alternatives_text=raw_body,
            status="open",
        )
        self.db.add(reschedule)

        response.status = "reschedule_requested"
        response.processed_at = datetime.now(tz=timezone.utc)
        await self.db.flush()

        return {
            "action": "reschedule_requested",
            "appointment_id": str(appointment_id),
            "reschedule_request_id": str(reschedule.id),
            "auto_reply": _AUTO_REPLIES[ConfirmationKeyword.RESCHEDULE],
        }

    async def _handle_cancel(
        self,
        response: JobConfirmationResponse,
        appointment_id: UUID,
    ) -> dict[str, Any]:
        """CANCEL: SCHEDULED → CANCELLED + auto-reply + admin notification."""
        from grins_platform.models.appointment import Appointment  # noqa: PLC0415
        from grins_platform.models.job import Job  # noqa: PLC0415
        from grins_platform.services.appointment_service import (  # noqa: PLC0415
            clear_on_site_data,
        )

        appt = await self.db.get(Appointment, appointment_id)
        if appt and appt.status in (
            AppointmentStatus.SCHEDULED.value,
            AppointmentStatus.CONFIRMED.value,
        ):
            appt.status = AppointmentStatus.CANCELLED.value
            await self.db.flush()

            # Clear on-site data after cancellation (Req 2.1, 2.2, 2.3)
            job = await self.db.get(Job, appt.job_id)
            await clear_on_site_data(self.db, appt, job=job)

        response.status = "cancelled"
        response.processed_at = datetime.now(tz=timezone.utc)
        await self.db.flush()

        return {
            "action": "cancelled",
            "appointment_id": str(appointment_id),
            "auto_reply": _AUTO_REPLIES[ConfirmationKeyword.CANCEL],
        }

    async def _handle_needs_review(
        self,
        response: JobConfirmationResponse,
    ) -> dict[str, Any]:
        """Unknown keyword: log with status needs_review."""
        response.status = "needs_review"
        response.processed_at = datetime.now(tz=timezone.utc)
        await self.db.flush()

        logger.warning(
            "confirmation.needs_review",
            response_id=str(response.id),
            raw_body=response.raw_reply_body,
        )
        return {"action": "needs_review", "response_id": str(response.id)}

    # ------------------------------------------------------------------
    # Correlation helper
    # ------------------------------------------------------------------

    async def _find_confirmation_message(
        self,
        thread_id: str,
    ) -> SentMessage | None:
        """Find the original APPOINTMENT_CONFIRMATION SMS by thread_id.

        Validates: CRM Changes Update 2 Req 24.7
        """
        stmt = (
            select(SentMessage)
            .where(
                SentMessage.provider_thread_id == thread_id,
                SentMessage.message_type == MessageType.APPOINTMENT_CONFIRMATION.value,
            )
            .order_by(SentMessage.created_at.desc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        row: SentMessage | None = result.scalar_one_or_none()
        return row
