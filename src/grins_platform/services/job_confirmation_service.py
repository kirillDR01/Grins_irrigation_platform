"""Job confirmation service — Y/R/C reply handling.

Parses inbound SMS replies to appointment confirmation messages,
transitions appointment status, and creates reschedule requests.

Validates: CRM Changes Update 2 Req 24.1-24.8, 25.1
"""

from __future__ import annotations

import os
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
#
# bughunt M-3: Spec §9 lists "Y (or yes, confirm, ok, okay)" and §15 leaves
# room for common synonyms and number replies. ``stop`` is intentionally
# excluded — it is a reserved compliance keyword handled by the SMS opt-out
# pipeline, mapping it to CANCEL would silently swallow opt-outs.
_KEYWORD_MAP: dict[str, ConfirmationKeyword] = {
    # CONFIRM
    "y": ConfirmationKeyword.CONFIRM,
    "yes": ConfirmationKeyword.CONFIRM,
    "confirm": ConfirmationKeyword.CONFIRM,
    "confirmed": ConfirmationKeyword.CONFIRM,
    "ok": ConfirmationKeyword.CONFIRM,
    "okay": ConfirmationKeyword.CONFIRM,
    "yup": ConfirmationKeyword.CONFIRM,
    "yeah": ConfirmationKeyword.CONFIRM,
    "1": ConfirmationKeyword.CONFIRM,
    # RESCHEDULE
    "r": ConfirmationKeyword.RESCHEDULE,
    "reschedule": ConfirmationKeyword.RESCHEDULE,
    "different time": ConfirmationKeyword.RESCHEDULE,
    "change time": ConfirmationKeyword.RESCHEDULE,
    "2": ConfirmationKeyword.RESCHEDULE,
    # CANCEL — note: ``stop`` is NOT included; it's a compliance opt-out keyword.
    "c": ConfirmationKeyword.CANCEL,
    "cancel": ConfirmationKeyword.CANCEL,
}

# Auto-reply templates. CONFIRM is built dynamically per appointment
# (bughunt M-4) — see :func:`_build_confirm_message`.
_AUTO_REPLIES: dict[ConfirmationKeyword, str] = {
    ConfirmationKeyword.RESCHEDULE: (
        "We've received your reschedule request. We'll be in touch with a new time."
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
        original = await self.find_confirmation_message(thread_id)
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

        # Expose the real E.164 phone we sent the original confirmation to.
        # The inbound webhook's ``from_phone`` is provider-masked on CallRail
        # (e.g. ``***3312``); routing a Y/R/C auto-reply through it produces a
        # malformed number. Callers use this field to target the real phone.
        result["recipient_phone"] = original.recipient_phone

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
            "auto_reply": self._build_confirm_message(appt),
        }

    @staticmethod
    def _build_confirm_message(appt: Any | None) -> str:  # noqa: ANN401
        """Build the CONFIRM auto-reply with the appointment date and time.

        Spec §4 (lines 219-222): ``"Your appointment has been confirmed.
        See you on [date] at [time]!"``. Mirrors the formatting helpers used
        by :meth:`_build_cancellation_message` so the wording is consistent
        across CONFIRM and CANCEL flows (bughunt M-4).
        """
        from grins_platform.services.sms.formatters import (  # noqa: PLC0415
            format_sms_time_12h,
        )

        appt_date = getattr(appt, "scheduled_date", None) if appt else None
        appt_time = getattr(appt, "time_window_start", None) if appt else None

        date_str = appt_date.strftime("%B %d, %Y") if appt_date else None
        time_str = format_sms_time_12h(appt_time) if appt_time else None

        if date_str and time_str:
            return (
                f"Your appointment has been confirmed. "
                f"See you on {date_str} at {time_str}!"
            )
        return "Your appointment has been confirmed. See you then!"

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

        # Follow-up SMS asking for alternative times (Req 14.1, 14.2)
        follow_up_text = (
            "We'd be happy to reschedule. Please reply with 2-3 dates "
            "and times that work for you and we'll get you set up."
        )

        return {
            "action": "reschedule_requested",
            "appointment_id": str(appointment_id),
            "reschedule_request_id": str(reschedule.id),
            "auto_reply": _AUTO_REPLIES[ConfirmationKeyword.RESCHEDULE],
            "follow_up_sms": follow_up_text,
        }

    async def _handle_cancel(
        self,
        response: JobConfirmationResponse,
        appointment_id: UUID,
    ) -> dict[str, Any]:
        """CANCEL: SCHEDULED → CANCELLED + detailed auto-reply + admin notification."""
        from grins_platform.models.appointment import Appointment  # noqa: PLC0415
        from grins_platform.models.job import Job  # noqa: PLC0415
        from grins_platform.services.appointment_service import (  # noqa: PLC0415
            clear_on_site_data,
        )

        appt = await self.db.get(Appointment, appointment_id)

        # CR-3 / H-2 / 2026-04-14 E2E-3 — "repeat C is a no-op" (spec line 1070).
        # Short-circuit before we build + send another cancellation SMS.
        if appt and appt.status == AppointmentStatus.CANCELLED.value:
            response.status = "cancelled"
            response.processed_at = datetime.now(tz=timezone.utc)
            await self.db.flush()
            self.log_rejected(
                "handle_cancel",
                reason="already_cancelled",
                appointment_id=str(appointment_id),
            )
            return {
                "action": "cancelled",
                "appointment_id": str(appointment_id),
                "auto_reply": "",  # falsy → sms_service._try_confirmation_reply skips send
            }

        if appt and appt.status in (
            AppointmentStatus.SCHEDULED.value,
            AppointmentStatus.CONFIRMED.value,
        ):
            appt.status = AppointmentStatus.CANCELLED.value
            await self.db.flush()

            # Clear on-site data after cancellation (Req 2.1, 2.2, 2.3)
            job = await self.db.get(Job, appt.job_id)
            await clear_on_site_data(self.db, appt, job=job)
        else:
            job = await self.db.get(Job, response.job_id) if response.job_id else None

        # Build detailed cancellation SMS (Req 15.1, 15.2, 15.3)
        auto_reply = self._build_cancellation_message(appt, job)

        response.status = "cancelled"
        response.processed_at = datetime.now(tz=timezone.utc)
        await self.db.flush()

        return {
            "action": "cancelled",
            "appointment_id": str(appointment_id),
            "auto_reply": auto_reply,
        }

    @staticmethod
    def _build_cancellation_message(
        appt: Any | None,
        job: Any | None,
    ) -> str:
        """Build detailed cancellation SMS with service type, date/time, and phone.

        Uses the canonical :func:`job_type_display` map (bughunt L-1) and the
        portable :func:`format_sms_time_12h` formatter (bughunt M-11) so the
        template renders identically on Linux, macOS, and Windows dev
        environments.

        Validates: Req 15.1, 15.2, 15.3; bughunt L-1, M-11.
        """
        from grins_platform.models.enums import (  # noqa: PLC0415
            job_type_display,
        )
        from grins_platform.services.sms.formatters import (  # noqa: PLC0415
            format_sms_time_12h,
        )

        service_type = getattr(job, "job_type", None) if job else None
        business_phone = os.environ.get("BUSINESS_PHONE_NUMBER", "")

        if appt and service_type:
            service_display = job_type_display(service_type)
            appt_date = getattr(appt, "scheduled_date", None)
            appt_time = getattr(appt, "time_window_start", None)

            date_str = (
                appt_date.strftime("%B %d, %Y") if appt_date else "your scheduled date"
            )
            time_str = format_sms_time_12h(appt_time) or "your scheduled time"

            msg = (
                f"Your {service_display} appointment on {date_str} at {time_str} "
                f"has been cancelled."
            )
            if business_phone:
                msg += (
                    f" If you'd like to reschedule, please call us at {business_phone}."
                )
            else:
                msg += " Please contact us if you'd like to reschedule."
            return msg

        # Fallback to generic message
        return _AUTO_REPLIES[ConfirmationKeyword.CANCEL]

    async def _handle_needs_review(
        self,
        response: JobConfirmationResponse,
    ) -> dict[str, Any]:
        """Unknown keyword: check for open reschedule request, else log with status needs_review.

        If an open reschedule request exists for this appointment, capture the
        reply as requested_alternatives (Req 14.3, 14.4).
        """
        # Check for open reschedule request to capture alternative times
        stmt = (
            select(RescheduleRequest)
            .where(
                RescheduleRequest.appointment_id == response.appointment_id,
                RescheduleRequest.status == "open",
            )
            .order_by(RescheduleRequest.created_at.desc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        reschedule_req: RescheduleRequest | None = result.scalar_one_or_none()

        if reschedule_req is not None:
            # Capture customer's alternative times (Req 14.3). bughunt M-3:
            # customers often split the list across multiple texts
            # ("Tue 2pm", then "or Wed morning"). Append each reply as its
            # own entry instead of overwriting the previous one so admins
            # see the full history.
            now_iso = datetime.now(tz=timezone.utc).isoformat()
            new_entry = {"text": response.raw_reply_body, "at": now_iso}
            existing = reschedule_req.requested_alternatives
            entries: list[dict[str, Any]]
            if isinstance(existing, dict) and isinstance(existing.get("entries"), list):
                # Already appended-to list — keep growing it.
                entries = list(existing["entries"])
            elif isinstance(existing, dict) and existing:
                # Legacy single-reply shape ({"raw_text": ..., "received_at": ...})
                # — preserve it as the first entry, then append the new one.
                legacy_text = existing.get("raw_text") or existing.get("text") or ""
                legacy_at = existing.get("received_at") or existing.get("at") or ""
                entries = []
                if legacy_text:
                    entries.append({"text": legacy_text, "at": legacy_at})
            else:
                entries = []
            entries.append(new_entry)
            reschedule_req.requested_alternatives = {"entries": entries}
            response.status = "reschedule_alternatives_received"
            response.processed_at = datetime.now(tz=timezone.utc)
            await self.db.flush()

            return {
                "action": "reschedule_alternatives_received",
                "appointment_id": str(response.appointment_id),
                "reschedule_request_id": str(reschedule_req.id),
                "alternatives_text": response.raw_reply_body,
                "alternatives_count": len(entries),
            }

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

    async def find_confirmation_message(
        self,
        thread_id: str,
    ) -> SentMessage | None:
        """Find the original APPOINTMENT_CONFIRMATION SMS by thread_id.

        Public entry point used by :class:`SMSService` to correlate an
        inbound reply back to the outbound confirmation message (bughunt
        L-14: the SMS router previously reached into ``_find_confirmation_message``
        — an encapsulation leak flagged by lint).

        Validates: CRM Changes Update 2 Req 24.7; bughunt L-14.
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

    # Deprecated private alias — retained until all in-tree callers migrate
    # to :meth:`find_confirmation_message`. Remove in a follow-up once unit
    # tests targeting the private name are updated.
    _find_confirmation_message = find_confirmation_message
