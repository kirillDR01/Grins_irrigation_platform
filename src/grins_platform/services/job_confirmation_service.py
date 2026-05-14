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
from sqlalchemy.exc import IntegrityError

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
from grins_platform.services.confirmation_target import ConfirmationTarget

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from grins_platform.models.appointment import Appointment
    from grins_platform.services.email_service import EmailService

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
    # User directive 2026-05-05: replace the receipt-only wording with the
    # actionable "please reply with 2-3 dates" prompt so the customer
    # knows what to do next. Combined with the follow-up suppression
    # below, this collapses two redundant SMS into one clear ask.
    ConfirmationKeyword.RESCHEDULE: (
        "We'd be happy to reschedule. Please reply with 2-3 dates "
        "and times that work for you and we'll get you booked."
    ),
    ConfirmationKeyword.CANCEL: (
        "Your appointment has been cancelled. "
        "Please contact us if you'd like to reschedule."
    ),
}

# Gap 03.A — message types that should resolve to the primary confirmation
# handler. Cancellation notifications are intentionally excluded: a Y/R reply
# to a cancellation SMS routes through ``handle_post_cancellation_reply``.
_CONFIRMATION_LIKE_TYPES: frozenset[str] = frozenset(
    {
        MessageType.APPOINTMENT_CONFIRMATION.value,
        MessageType.APPOINTMENT_RESCHEDULE.value,
        MessageType.APPOINTMENT_REMINDER.value,
        # Sales-pipeline lifecycle (migration 20260509_120000): a Y/R/C
        # reply on an estimate-visit thread routes through the same
        # correlator. Dispatcher branches on ConfirmationTarget.kind.
        MessageType.ESTIMATE_VISIT_CONFIRMATION.value,
    }
)


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
            # Gap 1.C — fall through to the reschedule-followup thread so
            # free-text alternatives land on the open RescheduleRequest.
            # Keyword replies stay locked to the confirmation thread to
            # avoid a numeric body on a follow-up thread (e.g. "2pm")
            # being parsed as RESCHEDULE.
            if keyword is not None:
                # Gap 03.B — a Y/R/C on a thread whose only
                # confirmation-like row is superseded is a stale-thread
                # reply: write an audit row + return a courteous
                # auto-reply instead of a silent no_match.
                stale_result = await self._handle_stale_thread_reply(
                    thread_id=thread_id,
                    keyword=keyword,
                    raw_body=raw_body,
                    from_phone=from_phone,
                    provider_sid=provider_sid,
                )
                if stale_result is not None:
                    self.log_completed(
                        "handle_confirmation",
                        result_action=stale_result.get("action"),
                        thread_id=thread_id,
                    )
                    return stale_result
                self.log_rejected(
                    "handle_confirmation",
                    reason="no_matching_confirmation",
                    thread_id=thread_id,
                )
                return {"action": "no_match", "thread_id": thread_id}
            original = await self.find_reschedule_thread(thread_id)
            if original is None:
                self.log_rejected(
                    "handle_confirmation",
                    reason="no_matching_thread",
                    thread_id=thread_id,
                )
                return {"action": "no_match", "thread_id": thread_id}

        # 1.5. Build a polymorphic dispatch target from the correlated
        # SentMessage. PR A only wires the appointment branch; PR B will
        # add an estimate-visit branch that routes to dedicated handlers
        # for SalesCalendarEvent. An orphaned SentMessage (neither FK
        # set, e.g. a stray campaign row that somehow matched the
        # thread) cannot anchor a Y/R/C lifecycle — return no_match.
        try:
            target = ConfirmationTarget.from_sent_message(original)
        except ValueError:
            self.log_rejected(
                "handle_confirmation",
                reason="orphan_sent_message",
                thread_id=thread_id,
            )
            return {"action": "no_match", "thread_id": thread_id}

        if target.kind == "estimate_visit":
            estimate_result = await self._handle_estimate_visit_reply(
                target=target,
                original=original,
                keyword=keyword,
                raw_body=raw_body,
                from_phone=from_phone,
                provider_sid=provider_sid,
            )
            estimate_result["recipient_phone"] = original.recipient_phone
            self.log_completed(
                "handle_confirmation",
                result_action=estimate_result.get("action"),
                sales_calendar_event_id=str(target.sales_calendar_event_id),
            )
            return estimate_result

        appointment_id: UUID = target.appointment_id  # type: ignore[assignment]
        job_id: UUID = target.job_id  # type: ignore[assignment]
        customer_id: UUID = target.customer_id

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
        """CONFIRM: SCHEDULED → CONFIRMED + auto-reply.

        Gap 02: a repeat ``Y`` on an already-CONFIRMED appointment
        short-circuits to a reassurance reply (mirror of
        :meth:`_handle_cancel`'s already-cancelled branch with a non-empty
        reassurance ``auto_reply`` instead of silence, because confirmation
        is about trust).

        The appointment fetch uses ``SELECT ... FOR UPDATE`` so two
        concurrent Y webhooks serialize through the status check: only one
        can observe ``SCHEDULED`` and transition; the loser sees
        ``CONFIRMED`` and takes the repeat branch.
        """
        from grins_platform.models.appointment import Appointment  # noqa: PLC0415

        # Row-level lock so concurrent Y webhooks serialize through the
        # status check. Without this, two webhooks can both observe
        # ``SCHEDULED`` and both try to transition, producing two response
        # rows with ``status='confirmed'`` instead of one ``'confirmed'``
        # and one ``'confirmed_repeat'``.
        stmt = (
            select(Appointment)
            .where(Appointment.id == appointment_id)
            .with_for_update()
        )
        appt = (await self.db.execute(stmt)).scalar_one_or_none()

        # Gap 02 — repeat Y on an already-confirmed appointment. Mirror of
        # the ``_handle_cancel`` already-cancelled short-circuit with two
        # deliberate deltas:
        #   1. ``auto_reply`` is NON-empty — a short reassurance
        #      (confirmation is about trust; silence after a repeat Y
        #      reinforces the doubt that prompted it).
        #   2. ``response.status`` is ``'confirmed_repeat'`` (not plain
        #      ``'confirmed'``) so analytics and support can tell first-Y
        #      apart from repeat-Y rows.
        if appt and appt.status == AppointmentStatus.CONFIRMED.value:
            pre_status_repeat = appt.status
            response.status = "confirmed_repeat"
            response.processed_at = datetime.now(tz=timezone.utc)
            await self.db.flush()
            await self._record_customer_sms_confirm_audit(
                appointment_id=appointment_id,
                action="appointment.confirm_repeat",
                pre_status=pre_status_repeat,
                post_status=AppointmentStatus.CONFIRMED.value,
                response_id=response.id,
                from_phone=response.from_phone,
                raw_body=response.raw_reply_body,
            )
            self.log_rejected(
                "handle_confirm",
                reason="already_confirmed",
                appointment_id=str(appointment_id),
            )
            return {
                "action": "confirmed",
                "appointment_id": str(appointment_id),
                "auto_reply": self._build_confirm_reassurance_message(appt),
                "dedup": True,
            }

        pre_status = appt.status if appt else None
        transitioned = False
        if appt and appt.status == AppointmentStatus.SCHEDULED.value:
            appt.status = AppointmentStatus.CONFIRMED.value
            transitioned = True
            await self.db.flush()

        response.status = "confirmed"
        response.processed_at = datetime.now(tz=timezone.utc)
        await self.db.flush()

        if transitioned:
            await self._record_customer_sms_confirm_audit(
                appointment_id=appointment_id,
                action="appointment.confirm",
                pre_status=pre_status or "",
                post_status=AppointmentStatus.CONFIRMED.value,
                response_id=response.id,
                from_phone=response.from_phone,
                raw_body=response.raw_reply_body,
            )

        return {
            "action": "confirmed",
            "appointment_id": str(appointment_id),
            "auto_reply": self._build_confirm_message(appt),
        }

    async def _record_customer_sms_confirm_audit(
        self,
        *,
        appointment_id: UUID,
        action: str,
        pre_status: str,
        post_status: str,
        response_id: Any,  # noqa: ANN401 — JobConfirmationResponse.id is UUID at runtime
        from_phone: str | None,
        raw_body: str | None,
    ) -> None:
        """Audit a customer Y reply (gap-05, mirrors cancel-audit).

        ``action`` is ``appointment.confirm`` for the first-Y SCHEDULED→
        CONFIRMED transition, or ``appointment.confirm_repeat`` for a
        repeat Y on an already-CONFIRMED appointment. Failures are
        logged and swallowed so the customer reply path never fails on
        an audit-write hiccup.
        """
        from grins_platform.repositories.audit_log_repository import (  # noqa: PLC0415
            AuditLogRepository,
        )

        try:
            repo = AuditLogRepository(self.db)
            _ = await repo.create(
                action=action,
                resource_type="appointment",
                resource_id=appointment_id,
                actor_id=None,
                details={
                    "actor_type": "customer",
                    "source": "customer_sms",
                    "pre_status": pre_status,
                    "post_status": post_status,
                    "response_id": str(response_id),
                    "from_phone": from_phone,
                    "raw_body": raw_body,
                },
            )
        except Exception:
            self.log_failed(
                "customer_sms_confirm_audit",
                appointment_id=str(appointment_id),
            )

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

    @staticmethod
    def _build_confirm_reassurance_message(appt: Any | None) -> str:  # noqa: ANN401
        """Build the reassurance SMS for a repeat ``Y`` on an already-confirmed appt.

        Shorter than :meth:`_build_confirm_message` — the customer already
        received the full confirmation on their first Y. This reply exists
        only to reassure them the second Y landed, without re-implying a
        state change.

        Validates: gap-02.
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
                f"You're already confirmed for {date_str} at {time_str}. See you then!"
            )
        return "You're already confirmed. See you then!"

    async def _handle_reschedule(
        self,
        response: JobConfirmationResponse,
        appointment_id: UUID,
        job_id: UUID,
        customer_id: UUID,
        raw_body: str,
    ) -> dict[str, Any]:
        """RESCHEDULE: create reschedule_request + follow-up SMS.

        Gap 1.B — state guard: refuse "R" replies when the appointment is
        already in a field-work or terminal state and fire a
        ``late_reschedule_attempt`` admin alert so the admin still sees
        the customer's intent.

        Gap 1.A — idempotency: a second identical "R" does not create a
        second open ``RescheduleRequest``. The partial unique index
        ``uq_reschedule_requests_open_per_appointment`` is a DB safety
        net behind the application-level dedup; a concurrent-webhook
        race is caught via a SAVEPOINT around the insert.
        """
        from grins_platform.models.appointment import Appointment  # noqa: PLC0415

        # Gap 1.B — state guard. If the appointment is in a field-work or
        # terminal state, do NOT create a RescheduleRequest (the admin
        # resolve path rejects these source statuses anyway). Fire an
        # admin alert and send a tailored auto-reply instead.
        appt = await self.db.get(Appointment, appointment_id)
        blocked_statuses = {
            AppointmentStatus.EN_ROUTE.value,
            AppointmentStatus.IN_PROGRESS.value,
            AppointmentStatus.COMPLETED.value,
            AppointmentStatus.CANCELLED.value,
            AppointmentStatus.NO_SHOW.value,
        }
        if appt is not None and appt.status in blocked_statuses:
            response.status = "reschedule_rejected"
            response.processed_at = datetime.now(tz=timezone.utc)
            await self.db.flush()
            await self._dispatch_late_reschedule_alert(
                appointment_id=appointment_id,
                customer_id=customer_id,
                appt=appt,
            )
            await self._record_customer_sms_reschedule_audit(
                appointment_id=appointment_id,
                action="appointment.reschedule_rejected",
                pre_status=appt.status,
                response_id=response.id,
                from_phone=response.from_phone,
                raw_body=raw_body,
                reschedule_request_id=None,
            )
            self.log_rejected(
                "handle_reschedule",
                reason="invalid_state",
                appointment_id=str(appointment_id),
                current_status=appt.status,
            )
            return {
                "action": "reschedule_rejected",
                "appointment_id": str(appointment_id),
                "current_status": appt.status,
                "auto_reply": self._build_late_reschedule_reply(appt),
            }

        # Gap 1.A — application-level dedup. Oldest open request wins so
        # any admin resolve path touches the original row.
        open_stmt = (
            select(RescheduleRequest)
            .where(
                RescheduleRequest.appointment_id == appointment_id,
                RescheduleRequest.status == "open",
            )
            .order_by(RescheduleRequest.created_at.asc())
            .limit(1)
        )
        existing = (await self.db.execute(open_stmt)).scalar_one_or_none()
        if existing is not None:
            return await self._append_duplicate_open_request(
                response=response,
                existing=existing,
                raw_body=raw_body,
                appointment_id=appointment_id,
                reason="duplicate_open_request",
            )

        reschedule = RescheduleRequest(
            job_id=job_id,
            appointment_id=appointment_id,
            customer_id=customer_id,
            original_reply_id=response.id,
            raw_alternatives_text=raw_body,
            status="open",
        )
        try:
            # SAVEPOINT — preserves the JobConfirmationResponse row added
            # by handle_confirmation() even when the partial unique index
            # rejects our insert because a concurrent webhook won the race.
            async with self.db.begin_nested():
                self.db.add(reschedule)
                await self.db.flush()
        except IntegrityError:
            # Race: the concurrent webhook inserted the open row first.
            existing = (await self.db.execute(open_stmt)).scalar_one_or_none()
            if existing is None:
                raise
            return await self._append_duplicate_open_request(
                response=response,
                existing=existing,
                raw_body=raw_body,
                appointment_id=appointment_id,
                reason="duplicate_open_request_race",
            )

        response.status = "reschedule_requested"
        response.processed_at = datetime.now(tz=timezone.utc)
        await self.db.flush()

        await self._record_customer_sms_reschedule_audit(
            appointment_id=appointment_id,
            action="appointment.reschedule_requested",
            pre_status=appt.status if appt is not None else "",
            response_id=response.id,
            from_phone=response.from_phone,
            raw_body=raw_body,
            reschedule_request_id=reschedule.id,
        )
        await self._dispatch_pending_reschedule_alert(
            appointment_id=appointment_id,
            customer_id=customer_id,
            reschedule_request_id=reschedule.id,
        )

        # User directive 2026-05-05: the follow-up SMS asking for 2-3
        # dates is now the auto_reply itself (above) so the customer
        # gets ONE message instead of receipt + nudge. The legacy
        # ``follow_up_sms`` slot is intentionally omitted — keep the
        # field absent rather than empty so the dispatch site at
        # ``sms_service.py:1230`` short-circuits cleanly.
        return {
            "action": "reschedule_requested",
            "appointment_id": str(appointment_id),
            "reschedule_request_id": str(reschedule.id),
            "auto_reply": _AUTO_REPLIES[ConfirmationKeyword.RESCHEDULE],
        }

    async def _record_customer_sms_reschedule_audit(
        self,
        *,
        appointment_id: UUID,
        action: str,
        pre_status: str,
        response_id: Any,  # noqa: ANN401 — UUID at runtime
        from_phone: str | None,
        raw_body: str | None,
        reschedule_request_id: UUID | None,
    ) -> None:
        """Audit a customer R reply (gap-05).

        ``action`` is ``appointment.reschedule_requested`` on the
        new-request path, or ``appointment.reschedule_rejected`` when
        the late-reschedule guard refuses the request.
        """
        from grins_platform.repositories.audit_log_repository import (  # noqa: PLC0415
            AuditLogRepository,
        )

        try:
            repo = AuditLogRepository(self.db)
            _ = await repo.create(
                action=action,
                resource_type="appointment",
                resource_id=appointment_id,
                actor_id=None,
                details={
                    "actor_type": "customer",
                    "source": "customer_sms",
                    "pre_status": pre_status,
                    "response_id": str(response_id),
                    "from_phone": from_phone,
                    "raw_body": raw_body,
                    "reschedule_request_id": (
                        str(reschedule_request_id)
                        if reschedule_request_id is not None
                        else None
                    ),
                },
            )
        except Exception:
            self.log_failed(
                "customer_sms_reschedule_audit",
                appointment_id=str(appointment_id),
            )

    async def _dispatch_pending_reschedule_alert(
        self,
        *,
        appointment_id: UUID,
        customer_id: UUID,
        reschedule_request_id: UUID,
    ) -> None:
        """Raise a PENDING_RESCHEDULE_REQUEST admin alert (gap-14).

        Fired only on the new-RescheduleRequest insert path, never on
        the duplicate-fold branches (those route through
        ``_append_duplicate_open_request`` which leaves the existing
        open alert untouched). Failures are swallowed so the
        customer-facing reply still succeeds when alert creation
        hiccups.
        """
        from grins_platform.models.alert import Alert  # noqa: PLC0415
        from grins_platform.models.customer import Customer  # noqa: PLC0415
        from grins_platform.models.enums import (  # noqa: PLC0415
            AlertSeverity,
            AlertType,
        )
        from grins_platform.repositories.alert_repository import (  # noqa: PLC0415
            AlertRepository,
        )

        try:
            customer = await self.db.get(Customer, customer_id)
            customer_name = customer.full_name if customer is not None else "customer"
            alert = Alert(
                type=AlertType.PENDING_RESCHEDULE_REQUEST.value,
                severity=AlertSeverity.WARNING.value,
                entity_type="appointment",
                entity_id=appointment_id,
                message=(
                    f"Reschedule requested by {customer_name} "
                    f"(request {reschedule_request_id})"
                ),
            )
            await AlertRepository(self.db).create(alert)
        except Exception:
            self.log_failed(
                "pending_reschedule_alert",
                appointment_id=str(appointment_id),
            )

    async def _append_duplicate_open_request(
        self,
        *,
        response: JobConfirmationResponse,
        existing: RescheduleRequest,
        raw_body: str,
        appointment_id: UUID,
        reason: str,
    ) -> dict[str, Any]:
        """Fold a duplicate "R" reply into the existing open request.

        Appends the new reply body onto ``raw_alternatives_text`` so the
        admin sees both messages, marks the response as
        ``reschedule_requested``, and returns a result dict that
        deliberately omits ``follow_up_sms`` — the follow-up was already
        sent on the first "R", re-sending would be spammy.
        """
        existing.raw_alternatives_text = (
            f"{existing.raw_alternatives_text or ''}\n---\n{raw_body}".strip()
        )
        response.status = "reschedule_requested"
        response.processed_at = datetime.now(tz=timezone.utc)
        await self.db.flush()
        self.log_rejected(
            "handle_reschedule",
            reason=reason,
            appointment_id=str(appointment_id),
            existing_request_id=str(existing.id),
        )
        return {
            "action": "reschedule_requested",
            "appointment_id": str(appointment_id),
            "reschedule_request_id": str(existing.id),
            "auto_reply": _AUTO_REPLIES[ConfirmationKeyword.RESCHEDULE],
            "duplicate": True,
        }

    @staticmethod
    def _build_late_reschedule_reply(appt: Appointment) -> str:
        """Build a state-specific SMS for customers who text "R" too late.

        Selects wording by appointment status so the message is honest
        about *why* the reschedule can't run through the automated flow
        and directs the customer to the business line.
        """
        from grins_platform.services.sms.formatters import (  # noqa: PLC0415
            format_sms_time_12h,
        )

        business_phone = os.environ.get("BUSINESS_PHONE_NUMBER", "")
        call_clause = f" at {business_phone}" if business_phone else ""
        status = getattr(appt, "status", None)

        if status == AppointmentStatus.EN_ROUTE.value:
            return (
                "Your technician is already on the way. "
                f"Please call us{call_clause} if you need to make a change."
            )
        if status == AppointmentStatus.IN_PROGRESS.value:
            return (
                "Your technician is already on site. "
                f"Please call us{call_clause} if you need to make a change."
            )
        if status == AppointmentStatus.COMPLETED.value:
            appt_date = getattr(appt, "scheduled_date", None)
            appt_time = getattr(appt, "time_window_start", None)
            date_str = appt_date.strftime("%B %d, %Y") if appt_date else None
            time_str = format_sms_time_12h(appt_time) if appt_time else None
            when = None
            if date_str and time_str:
                when = f" on {date_str} at {time_str}"
            elif date_str:
                when = f" on {date_str}"
            when = when or ""
            tail = (
                f"To book a new service, call{call_clause}"
                if business_phone
                else "To book a new service, please contact us"
            )
            return f"Your appointment was completed{when}. {tail}."

        # CANCELLED / NO_SHOW (and any other blocked state).
        tail = (
            f"Please call us{call_clause}." if business_phone else "Please contact us."
        )
        return f"This appointment is no longer active. {tail}"

    async def _dispatch_late_reschedule_alert(
        self,
        *,
        appointment_id: UUID,
        customer_id: UUID,
        appt: Appointment | None,
    ) -> None:
        """Notify admin of a late reschedule attempt.

        Mirrors :meth:`_dispatch_admin_cancellation_alert` — resolves the
        customer name and scheduled-at, then delegates to
        :meth:`NotificationService.send_admin_late_reschedule_alert`.
        Exceptions are logged and swallowed so admin notification never
        blocks the customer-facing reply.

        Validates: gap-01 (1.B).
        """
        from grins_platform.models.customer import Customer  # noqa: PLC0415
        from grins_platform.services.notification_service import (  # noqa: PLC0415
            NotificationService,
        )

        try:
            customer = await self.db.get(Customer, customer_id)
            if customer is None:
                self.log_rejected(
                    "handle_reschedule.late_alert",
                    reason="customer_not_found",
                    customer_id=str(customer_id),
                )
                return

            notification_svc = NotificationService(
                email_service=self._build_email_service(),
            )
            await notification_svc.send_admin_late_reschedule_alert(
                self.db,
                appointment_id=appointment_id,
                customer_id=customer_id,
                customer_name=customer.full_name,
                scheduled_at=self._resolve_scheduled_at(appt),
                current_status=getattr(appt, "status", "") or "",
            )
        except Exception as exc:
            self.log_failed(
                "handle_reschedule.late_alert_failed",
                error=exc,
                appointment_id=str(appointment_id),
            )

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
        # Idempotency guarantee for H-5: the admin alert is dispatched after
        # this short-circuit, so a repeat C reply does NOT re-alert the admin.
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

        pre_cancel_status = appt.status if appt else None
        transitioned = False
        if appt and appt.status in (
            AppointmentStatus.SCHEDULED.value,
            AppointmentStatus.CONFIRMED.value,
        ):
            appt.status = AppointmentStatus.CANCELLED.value
            transitioned = True
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

        # bughunt H-5 (2026-04-16): notify admin + raise dashboard alert row.
        # Runs AFTER the CR-3 short-circuit above so repeat C replies remain
        # no-ops. Failures are swallowed inside the notification service so
        # admin-side errors never block the customer reply.
        await self._dispatch_admin_cancellation_alert(
            appointment_id=appointment_id,
            customer_id=response.customer_id,
            appt=appt,
        )

        # bughunt M-8 (2026-04-16): audit the customer-initiated cancel so
        # the admin history view shows *why* an appointment was cancelled
        # (the admin-side path already audits via
        # AppointmentService._record_cancellation_audit). Gated on
        # ``transitioned`` so we don't write an audit row when the cancel
        # was a no-op (already CANCELLED in some other state path).
        if transitioned:
            await self._record_customer_sms_cancel_audit(
                appointment_id=appointment_id,
                pre_cancel_status=pre_cancel_status or "",
                response_id=response.id,
                from_phone=response.from_phone,
            )

        return {
            "action": "cancelled",
            "appointment_id": str(appointment_id),
            "auto_reply": auto_reply,
        }

    async def _record_customer_sms_cancel_audit(
        self,
        *,
        appointment_id: UUID,
        pre_cancel_status: str,
        response_id: Any,  # noqa: ANN401 — JobConfirmationResponse.id is UUID at runtime
        from_phone: str | None,
    ) -> None:
        """Audit a ``C`` SMS cancel with ``source="customer_sms"`` (bughunt M-8).

        Mirrors :meth:`AppointmentService._record_cancellation_audit` but
        records the customer's phone in place of an admin actor so the
        history view can tell admin- and customer-initiated cancels apart.
        """
        from grins_platform.repositories.audit_log_repository import (  # noqa: PLC0415
            AuditLogRepository,
        )

        try:
            repo = AuditLogRepository(self.db)
            _ = await repo.create(
                action="appointment.cancel",
                resource_type="appointment",
                resource_id=appointment_id,
                actor_id=None,
                details={
                    "actor_type": "customer",
                    "source": "customer_sms",
                    "pre_cancel_status": pre_cancel_status,
                    "response_id": str(response_id),
                    "from_phone": from_phone,
                },
            )
        except Exception:
            self.log_failed(
                "customer_sms_cancel_audit",
                appointment_id=str(appointment_id),
            )

    async def _dispatch_admin_cancellation_alert(
        self,
        *,
        appointment_id: UUID,
        customer_id: UUID,
        appt: Appointment | None,
    ) -> None:
        """Notify admin of a customer SMS cancellation.

        Resolves the customer name and scheduled-at from the supplied
        appointment object (fetching the :class:`Customer` if needed) and
        delegates to
        :meth:`NotificationService.send_admin_cancellation_alert`.

        Any exception is logged and swallowed — admin notification must
        never block the customer-facing response (H-5 acceptance criteria).

        Validates: bughunt 2026-04-16 finding H-5
        """
        from grins_platform.models.customer import Customer  # noqa: PLC0415
        from grins_platform.services.notification_service import (  # noqa: PLC0415
            NotificationService,
        )

        try:
            customer = await self.db.get(Customer, customer_id)
            if customer is None:
                self.log_rejected(
                    "handle_cancel.admin_notification",
                    reason="customer_not_found",
                    customer_id=str(customer_id),
                )
                return

            customer_name = customer.full_name

            scheduled_at = self._resolve_scheduled_at(appt)

            notification_svc = NotificationService(
                email_service=self._build_email_service(),
            )
            await notification_svc.send_admin_cancellation_alert(
                self.db,
                appointment_id=appointment_id,
                customer_id=customer_id,
                customer_name=customer_name,
                scheduled_at=scheduled_at,
                source="customer_sms",
            )
        except Exception as exc:
            self.log_failed(
                "handle_cancel.admin_notification_failed",
                error=exc,
                appointment_id=str(appointment_id),
            )

    @staticmethod
    def _resolve_scheduled_at(appt: Appointment | None) -> datetime:
        """Return the appointment start as a tz-aware UTC datetime.

        Falls back to ``datetime.now(tz=UTC)`` when the appointment is
        missing either ``scheduled_date`` or ``time_window_start`` (edge
        case observed with legacy rows).
        """
        if appt is None:
            return datetime.now(tz=timezone.utc)

        scheduled_date = getattr(appt, "scheduled_date", None)
        time_window_start = getattr(appt, "time_window_start", None)

        if scheduled_date is None or time_window_start is None:
            return datetime.now(tz=timezone.utc)

        return datetime.combine(
            scheduled_date,
            time_window_start,
            tzinfo=timezone.utc,
        )

    @staticmethod
    def _build_email_service() -> EmailService:
        """Construct the production :class:`EmailService`.

        Separated into a helper so tests can monkeypatch a stub sender in
        place of the real email dispatch path.
        """
        from grins_platform.services.email_service import (  # noqa: PLC0415
            EmailService,
        )

        return EmailService()

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

        await self._dispatch_unrecognized_reply_alert(
            appointment_id=response.appointment_id,
            response_id=response.id,
            raw_body=response.raw_reply_body,
        )

        logger.warning(
            "confirmation.needs_review",
            response_id=str(response.id),
            raw_body=response.raw_reply_body,
        )
        return {"action": "needs_review", "response_id": str(response.id)}

    async def _dispatch_unrecognized_reply_alert(
        self,
        *,
        appointment_id: UUID,
        response_id: UUID,
        raw_body: str | None,
    ) -> None:
        """Raise an UNRECOGNIZED_CONFIRMATION_REPLY admin alert (gap-14).

        Severity escalates from INFO to WARNING when a second
        unrecognized reply lands for the same appointment within 24h
        — that signals confused customer or template churn that the
        admin should triage rather than ignore.
        """
        from datetime import timedelta  # noqa: PLC0415

        from sqlalchemy import and_, func  # noqa: PLC0415

        from grins_platform.models.alert import Alert  # noqa: PLC0415
        from grins_platform.models.enums import (  # noqa: PLC0415
            AlertSeverity,
            AlertType,
        )
        from grins_platform.repositories.alert_repository import (  # noqa: PLC0415
            AlertRepository,
        )

        try:
            cutoff = datetime.now(tz=timezone.utc) - timedelta(hours=24)
            count_stmt = select(func.count(Alert.id)).where(
                and_(
                    Alert.type == AlertType.UNRECOGNIZED_CONFIRMATION_REPLY.value,
                    Alert.entity_type == "appointment",
                    Alert.entity_id == appointment_id,
                    Alert.created_at >= cutoff,
                ),
            )
            recent_count = (await self.db.execute(count_stmt)).scalar_one_or_none() or 0
            severity = (
                AlertSeverity.WARNING.value
                if recent_count >= 1
                else AlertSeverity.INFO.value
            )
            snippet = (raw_body or "")[:120]
            alert = Alert(
                type=AlertType.UNRECOGNIZED_CONFIRMATION_REPLY.value,
                severity=severity,
                entity_type="appointment",
                entity_id=appointment_id,
                message=(
                    f"Unrecognized reply on confirmation: '{snippet}' "
                    f"(response {response_id})"
                ),
            )
            await AlertRepository(self.db).create(alert)
        except Exception:
            self.log_failed(
                "unrecognized_reply_alert",
                appointment_id=str(appointment_id),
            )

    # ------------------------------------------------------------------
    # Post-cancellation reply handling (gap-03 3.A)
    # ------------------------------------------------------------------

    async def handle_post_cancellation_reply(
        self,
        thread_id: str,
        keyword: ConfirmationKeyword | None,
        raw_body: str,
        from_phone: str,
        provider_sid: str | None = None,
    ) -> dict[str, Any]:
        """Route an inbound reply to a cancellation-notification SMS.

        Fired from :meth:`SMSService._try_confirmation_reply` when the
        primary confirmation-like lookup AND the reschedule-followup
        lookup both miss and :meth:`find_cancellation_thread` matches.

        - R → create a new :class:`RescheduleRequest` in ``open`` state
          so the admin resolve path can bring the appointment back.
        - Y → raise a ``CUSTOMER_RECONSIDER_CANCELLATION`` admin alert
          (no auto-transition; admin must manually reactivate).
        - Any other keyword / free text → log as ``needs_review``.

        Validates: gap-03 (3.A post-cancellation reply).
        """
        self.log_started(
            "handle_post_cancellation_reply",
            thread_id=thread_id,
            keyword=keyword.value if keyword else None,
        )

        original = await self.find_cancellation_thread(thread_id)
        if original is None:
            self.log_rejected(
                "handle_post_cancellation_reply",
                reason="no_matching_thread",
                thread_id=thread_id,
            )
            return {"action": "no_match", "thread_id": thread_id}

        appointment_id: UUID = original.appointment_id  # type: ignore[assignment]
        job_id: UUID = original.job_id  # type: ignore[assignment]
        customer_id: UUID = original.customer_id  # type: ignore[assignment]

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

        if keyword == ConfirmationKeyword.RESCHEDULE:
            result = await self._handle_post_cancel_reschedule(
                response=response,
                appointment_id=appointment_id,
                job_id=job_id,
                customer_id=customer_id,
                raw_body=raw_body,
            )
        elif keyword == ConfirmationKeyword.CONFIRM:
            result = await self._handle_post_cancel_reconsider(
                response=response,
                appointment_id=appointment_id,
                customer_id=customer_id,
            )
        else:
            # CANCEL reply on a cancellation thread is redundant; free
            # text is ambiguous — both route to needs_review so an admin
            # can triage the intent manually.
            response.status = "needs_review"
            response.processed_at = datetime.now(tz=timezone.utc)
            await self.db.flush()
            logger.warning(
                "post_cancellation.needs_review",
                response_id=str(response.id),
                raw_body=response.raw_reply_body,
            )
            result = {
                "action": "needs_review",
                "response_id": str(response.id),
            }

        result["recipient_phone"] = original.recipient_phone

        self.log_completed(
            "handle_post_cancellation_reply",
            result_action=result.get("action"),
            appointment_id=str(appointment_id),
        )
        return result

    async def _handle_post_cancel_reschedule(
        self,
        *,
        response: JobConfirmationResponse,
        appointment_id: UUID,
        job_id: UUID,
        customer_id: UUID,
        raw_body: str,
    ) -> dict[str, Any]:
        """Create a new open reschedule request for a CANCELLED appointment.

        Mirrors :meth:`_handle_reschedule`'s SAVEPOINT + dedup pattern
        but skips the blocked-state guard — the appointment is (by
        construction) CANCELLED here, which the guard would otherwise
        reject. Admin must reactivate the appointment before resolving
        the queued request (tracked as a follow-up gap).
        """
        # Application-level dedup against the partial unique index
        # ``uq_reschedule_requests_open_per_appointment``. A prior open
        # request for this appointment folds the new reply into the
        # existing row so the admin sees the full history.
        open_stmt = (
            select(RescheduleRequest)
            .where(
                RescheduleRequest.appointment_id == appointment_id,
                RescheduleRequest.status == "open",
            )
            .order_by(RescheduleRequest.created_at.asc())
            .limit(1)
        )
        existing = (await self.db.execute(open_stmt)).scalar_one_or_none()
        if existing is not None:
            return await self._append_duplicate_open_request(
                response=response,
                existing=existing,
                raw_body=raw_body,
                appointment_id=appointment_id,
                reason="post_cancel_duplicate_open_request",
            )

        reschedule = RescheduleRequest(
            job_id=job_id,
            appointment_id=appointment_id,
            customer_id=customer_id,
            original_reply_id=response.id,
            raw_alternatives_text=raw_body,
            status="open",
        )
        try:
            async with self.db.begin_nested():
                self.db.add(reschedule)
                await self.db.flush()
        except IntegrityError:
            existing = (await self.db.execute(open_stmt)).scalar_one_or_none()
            if existing is None:
                raise
            return await self._append_duplicate_open_request(
                response=response,
                existing=existing,
                raw_body=raw_body,
                appointment_id=appointment_id,
                reason="post_cancel_duplicate_open_request_race",
            )

        response.status = "reschedule_requested"
        response.processed_at = datetime.now(tz=timezone.utc)
        await self.db.flush()

        # User directive 2026-05-05: collapse receipt + nudge into one
        # actionable ask so the customer knows exactly what to send next.
        return {
            "action": "post_cancel_reschedule_requested",
            "appointment_id": str(appointment_id),
            "reschedule_request_id": str(reschedule.id),
            "auto_reply": (
                "We'd be happy to reschedule. Please reply with 2-3 dates "
                "and times that work for you and we'll get you set up."
            ),
        }

    async def _handle_post_cancel_reconsider(
        self,
        *,
        response: JobConfirmationResponse,
        appointment_id: UUID,
        customer_id: UUID,
    ) -> dict[str, Any]:
        """Record a Y reply on a cancellation thread + raise admin alert.

        Intentionally does NOT transition the appointment back to
        ``SCHEDULED`` — reactivation is a manual admin step so a stray
        Y can't silently undo a cancellation. The alert surfaces the
        customer's intent to the admin dashboard.
        """
        from grins_platform.models.appointment import Appointment  # noqa: PLC0415

        appt = await self.db.get(Appointment, appointment_id)

        response.status = "cancel_reconsider_pending"
        response.processed_at = datetime.now(tz=timezone.utc)
        await self.db.flush()

        await self._dispatch_reconsider_cancellation_alert(
            appointment_id=appointment_id,
            customer_id=customer_id,
            appt=appt,
        )

        business_phone = os.environ.get("BUSINESS_PHONE_NUMBER", "")
        call_clause = (
            f" Please call us at {business_phone} to confirm a new time."
            if business_phone
            else " Please contact us to confirm a new time."
        )
        auto_reply = f"Got it — we've flagged this for a callback.{call_clause}"

        return {
            "action": "post_cancel_reconsider_pending",
            "appointment_id": str(appointment_id),
            "auto_reply": auto_reply,
        }

    async def _dispatch_reconsider_cancellation_alert(
        self,
        *,
        appointment_id: UUID,
        customer_id: UUID,
        appt: Appointment | None,
    ) -> None:
        """Notify admin that a customer texted "Y" to a cancellation SMS.

        Mirrors :meth:`_dispatch_late_reschedule_alert`. Per-spec
        contract: exceptions are logged and swallowed so admin
        notification never blocks the customer-facing reply.

        Validates: gap-03 (3.A cancel-reconsider alert).
        """
        from grins_platform.models.customer import Customer  # noqa: PLC0415
        from grins_platform.services.notification_service import (  # noqa: PLC0415
            NotificationService,
        )

        try:
            customer = await self.db.get(Customer, customer_id)
            if customer is None:
                self.log_rejected(
                    "handle_post_cancellation_reply.reconsider_alert",
                    reason="customer_not_found",
                    customer_id=str(customer_id),
                )
                return

            notification_svc = NotificationService(
                email_service=self._build_email_service(),
            )
            await notification_svc.send_admin_reconsider_cancellation_alert(
                self.db,
                appointment_id=appointment_id,
                customer_id=customer_id,
                customer_name=customer.full_name,
                scheduled_at=self._resolve_scheduled_at(appt),
            )
        except Exception as exc:
            self.log_failed(
                "handle_post_cancellation_reply.reconsider_alert_failed",
                error=exc,
                appointment_id=str(appointment_id),
            )

    async def _handle_stale_thread_reply(
        self,
        *,
        thread_id: str,
        keyword: ConfirmationKeyword | None,
        raw_body: str,
        from_phone: str,
        provider_sid: str | None,
    ) -> dict[str, Any] | None:
        """Audit a keyword reply on a superseded confirmation thread.

        Gap 03.B: once a newer confirmation-like SMS is sent for the
        same appointment, the prior row is stamped with ``superseded_at``.
        A customer replying ``Y`` to that stale thread must NOT
        silently confirm the new date they never saw — route to an
        audit row + courteous auto-reply instead.

        Returns ``None`` when no superseded row matches (caller falls
        through to the ``no_match`` path).

        Validates: gap-03 (3.B telemetry).
        """
        superseded = await self._find_superseded_confirmation_for_thread(
            thread_id,
        )
        if superseded is None:
            return None

        response = JobConfirmationResponse(
            job_id=superseded.job_id,
            appointment_id=superseded.appointment_id,
            sent_message_id=superseded.id,
            customer_id=superseded.customer_id,
            from_phone=from_phone,
            reply_keyword=keyword.value if keyword else None,
            raw_reply_body=raw_body,
            provider_sid=provider_sid,
            status="stale_thread_reply",
            processed_at=datetime.now(tz=timezone.utc),
        )
        self.db.add(response)
        await self.db.flush()

        logger.info(
            "handle_confirmation.stale_thread",
            thread_id=thread_id,
            appointment_id=str(superseded.appointment_id),
            response_id=str(response.id),
        )

        business_phone = os.environ.get("BUSINESS_PHONE_NUMBER", "")
        call_clause = (
            f", or call us at {business_phone} for help"
            if business_phone
            else ", or call us for help"
        )
        auto_reply = (
            "Your appointment was updated — please reply to the most "
            f"recent message from us{call_clause}."
        )

        return {
            "action": "stale_thread_reply",
            "thread_id": thread_id,
            "appointment_id": str(superseded.appointment_id),
            "auto_reply": auto_reply,
            "recipient_phone": superseded.recipient_phone,
        }

    # ------------------------------------------------------------------
    # Correlation helper
    # ------------------------------------------------------------------

    async def find_confirmation_message(
        self,
        thread_id: str,
    ) -> SentMessage | None:
        """Find the authoritative confirmation-like SMS for a thread_id.

        Gap 03:
        - Widened from ``APPOINTMENT_CONFIRMATION`` only to the
          confirmation-like set (confirmation / reschedule notification /
          reminder). A reply to any of these solicits Y/R/C and should
          route through the same handler tree.
        - Filters rows with a non-null ``superseded_at`` so a stale-thread
          reply does not accidentally route to an appointment whose state
          has moved on.

        Cancellation notifications are intentionally NOT included here —
        :meth:`find_cancellation_thread` handles that separately through
        ``handle_post_cancellation_reply``.

        Validates: CRM Changes Update 2 Req 24.7; bughunt L-14; gap-03
        (3.A, 3.B).
        """
        stmt = (
            select(SentMessage)
            .where(
                SentMessage.provider_thread_id == thread_id,
                SentMessage.message_type.in_(_CONFIRMATION_LIKE_TYPES),
                SentMessage.superseded_at.is_(None),
            )
            .order_by(SentMessage.created_at.desc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        row: SentMessage | None = result.scalar_one_or_none()
        return row

    async def find_reschedule_thread(
        self,
        thread_id: str,
    ) -> SentMessage | None:
        """Find the most recent confirmation or reschedule-followup SMS.

        Used to attribute free-text follow-up replies (the 2-3 alternative
        dates the customer sends after texting "R") back to the right
        :class:`RescheduleRequest`. Gap 1.C: the follow-up SMS is stored
        as ``MessageType.RESCHEDULE_FOLLOWUP`` on the same thread, and
        :meth:`find_confirmation_message` filters that type out — so a
        customer's reply on the follow-up thread falls through to the
        orphan path. This sibling accepts both message types.

        Kept separate from :meth:`find_confirmation_message` so Y/R/C
        keyword gating stays locked to the confirmation thread; if
        widened, a stray "2" inside a free-text date could be misparsed
        as RESCHEDULE.

        Validates: gap-01 (1.C).
        """
        stmt = (
            select(SentMessage)
            .where(
                SentMessage.provider_thread_id == thread_id,
                SentMessage.message_type.in_(
                    [
                        MessageType.APPOINTMENT_CONFIRMATION.value,
                        MessageType.RESCHEDULE_FOLLOWUP.value,
                    ],
                ),
            )
            .order_by(SentMessage.created_at.desc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        row: SentMessage | None = result.scalar_one_or_none()
        return row

    async def find_cancellation_thread(
        self,
        thread_id: str,
    ) -> SentMessage | None:
        """Find the most recent cancellation SMS for a thread_id.

        Used to attribute inbound replies to a cancellation notification
        (Y = reconsideration, R = new reschedule request, free text =
        needs_review). Separate from :meth:`find_confirmation_message` so
        confirmation-like Y/R/C routing never accidentally transitions a
        CANCELLED appointment.

        Filters rows whose ``superseded_at`` is non-null — a cancellation
        that was itself superseded (e.g. admin reactivated the appointment
        and a new reschedule SMS went out) no longer owns the thread.

        Validates: gap-03 (3.A post-cancellation reply).
        """
        stmt = (
            select(SentMessage)
            .where(
                SentMessage.provider_thread_id == thread_id,
                SentMessage.message_type == MessageType.APPOINTMENT_CANCELLATION.value,
                SentMessage.superseded_at.is_(None),
            )
            .order_by(SentMessage.created_at.desc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        row: SentMessage | None = result.scalar_one_or_none()
        return row

    async def _find_superseded_confirmation_for_thread(
        self,
        thread_id: str,
    ) -> SentMessage | None:
        """Find the most recent confirmation-like row for the thread_id,
        ignoring the ``superseded_at`` filter.

        Used only by the stale-thread-reply telemetry branch in
        :meth:`handle_confirmation` — callers must NOT use the returned
        row to drive a status transition. The row is a tombstone that
        tells us *which* appointment this thread used to authoritatively
        reference so we can write a stale-reply audit and return a
        courteous auto-reply.

        Validates: gap-03 (3.B telemetry).
        """
        stmt = (
            select(SentMessage)
            .where(
                SentMessage.provider_thread_id == thread_id,
                SentMessage.message_type.in_(_CONFIRMATION_LIKE_TYPES),
                SentMessage.superseded_at.is_not(None),
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

    # ------------------------------------------------------------------
    # Gap 11 — appointment-scoped listings for the timeline aggregator
    # ------------------------------------------------------------------

    async def list_responses_by_appointment(
        self,
        appointment_id: UUID,
    ) -> list[JobConfirmationResponse]:
        """List all inbound Y/R/C replies for an appointment, newest first.

        Validates: Gap 11.
        """
        self.log_started(
            "list_responses_by_appointment",
            appointment_id=str(appointment_id),
        )
        result = await self.db.execute(
            select(JobConfirmationResponse)
            .where(JobConfirmationResponse.appointment_id == appointment_id)
            .order_by(JobConfirmationResponse.received_at.desc()),
        )
        rows = list(result.scalars().all())
        self.log_completed("list_responses_by_appointment", count=len(rows))
        return rows

    async def list_reschedule_requests_by_appointment(
        self,
        appointment_id: UUID,
    ) -> list[RescheduleRequest]:
        """List all reschedule requests for an appointment, newest first.

        Validates: Gap 11.
        """
        self.log_started(
            "list_reschedule_requests_by_appointment",
            appointment_id=str(appointment_id),
        )
        result = await self.db.execute(
            select(RescheduleRequest)
            .where(RescheduleRequest.appointment_id == appointment_id)
            .order_by(RescheduleRequest.created_at.desc()),
        )
        rows = list(result.scalars().all())
        self.log_completed(
            "list_reschedule_requests_by_appointment",
            count=len(rows),
        )
        return rows

    async def list_responses_by_sales_event(
        self,
        sales_calendar_event_id: UUID,
    ) -> list[JobConfirmationResponse]:
        """List inbound Y/R/C replies for an estimate visit, newest first."""
        self.log_started(
            "list_responses_by_sales_event",
            sales_calendar_event_id=str(sales_calendar_event_id),
        )
        result = await self.db.execute(
            select(JobConfirmationResponse)
            .where(
                JobConfirmationResponse.sales_calendar_event_id
                == sales_calendar_event_id,
            )
            .order_by(JobConfirmationResponse.received_at.desc()),
        )
        rows = list(result.scalars().all())
        self.log_completed("list_responses_by_sales_event", count=len(rows))
        return rows

    async def list_reschedule_requests_by_sales_event(
        self,
        sales_calendar_event_id: UUID,
    ) -> list[RescheduleRequest]:
        """List reschedule requests for an estimate visit, newest first."""
        self.log_started(
            "list_reschedule_requests_by_sales_event",
            sales_calendar_event_id=str(sales_calendar_event_id),
        )
        result = await self.db.execute(
            select(RescheduleRequest)
            .where(
                RescheduleRequest.sales_calendar_event_id == sales_calendar_event_id,
            )
            .order_by(RescheduleRequest.created_at.desc()),
        )
        rows = list(result.scalars().all())
        self.log_completed(
            "list_reschedule_requests_by_sales_event",
            count=len(rows),
        )
        return rows

    # ------------------------------------------------------------------
    # Estimate-visit (sales-pipeline) Y/R/C handlers
    # ------------------------------------------------------------------

    async def _handle_estimate_visit_reply(
        self,
        *,
        target: ConfirmationTarget,
        original: SentMessage,
        keyword: ConfirmationKeyword | None,
        raw_body: str,
        from_phone: str,
        provider_sid: str | None,
    ) -> dict[str, Any]:
        """Dispatch a Y/R/C reply on an estimate-visit confirmation thread.

        Mirror of the appointment-side ``handle_confirmation`` body —
        records the inbound reply on ``JobConfirmationResponse`` keyed by
        ``sales_calendar_event_id`` (XOR with ``appointment_id`` per
        migration ``20260509_120000``), then branches on keyword.
        """
        sales_calendar_event_id: UUID = target.sales_calendar_event_id  # type: ignore[assignment]
        customer_id: UUID = target.customer_id

        response = JobConfirmationResponse(
            job_id=None,
            appointment_id=None,
            sales_calendar_event_id=sales_calendar_event_id,
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

        if keyword == ConfirmationKeyword.CONFIRM:
            return await self._handle_estimate_visit_confirm(
                response=response,
                sales_calendar_event_id=sales_calendar_event_id,
            )
        if keyword == ConfirmationKeyword.RESCHEDULE:
            return await self._handle_estimate_visit_reschedule(
                response=response,
                sales_calendar_event_id=sales_calendar_event_id,
                customer_id=customer_id,
                raw_body=raw_body,
            )
        if keyword == ConfirmationKeyword.CANCEL:
            return await self._handle_estimate_visit_cancel(
                response=response,
                sales_calendar_event_id=sales_calendar_event_id,
                customer_id=customer_id,
            )
        return await self._handle_estimate_visit_needs_review(response)

    async def _handle_estimate_visit_confirm(
        self,
        *,
        response: JobConfirmationResponse,
        sales_calendar_event_id: UUID,
    ) -> dict[str, Any]:
        """CONFIRM: pending → confirmed on ``SalesCalendarEvent``."""
        from grins_platform.models.sales import SalesCalendarEvent  # noqa: PLC0415

        stmt = (
            select(SalesCalendarEvent)
            .where(SalesCalendarEvent.id == sales_calendar_event_id)
            .with_for_update()
        )
        event = (await self.db.execute(stmt)).scalar_one_or_none()

        if event is not None and event.confirmation_status == "confirmed":
            response.status = "confirmed_repeat"
            response.processed_at = datetime.now(tz=timezone.utc)
            await self.db.flush()
            self.log_rejected(
                "handle_estimate_visit_confirm",
                reason="already_confirmed",
                sales_calendar_event_id=str(sales_calendar_event_id),
            )
            return {
                "action": "confirmed",
                "sales_calendar_event_id": str(sales_calendar_event_id),
                "auto_reply": self._build_estimate_confirm_reassurance(event),
                "dedup": True,
            }

        transitioned = False
        if event is not None and event.confirmation_status in (
            "pending",
            "reschedule_requested",
        ):
            event.confirmation_status = "confirmed"
            event.confirmation_status_at = datetime.now(tz=timezone.utc)
            transitioned = True
            await self.db.flush()

        response.status = "confirmed"
        response.processed_at = datetime.now(tz=timezone.utc)
        await self.db.flush()

        logger.info(
            "sales.calendar_event.confirmed",
            sales_calendar_event_id=str(sales_calendar_event_id),
            transitioned=transitioned,
        )

        return {
            "action": "confirmed",
            "sales_calendar_event_id": str(sales_calendar_event_id),
            "auto_reply": self._build_estimate_confirm_message(event),
        }

    async def _handle_estimate_visit_reschedule(
        self,
        *,
        response: JobConfirmationResponse,
        sales_calendar_event_id: UUID,
        customer_id: UUID,
        raw_body: str,
    ) -> dict[str, Any]:
        """RESCHEDULE: open RescheduleRequest + ack with 2-3 dates prompt."""
        from grins_platform.models.sales import SalesCalendarEvent  # noqa: PLC0415

        open_stmt = (
            select(RescheduleRequest)
            .where(
                RescheduleRequest.sales_calendar_event_id == sales_calendar_event_id,
                RescheduleRequest.status == "open",
            )
            .order_by(RescheduleRequest.created_at.asc())
            .limit(1)
        )
        existing = (await self.db.execute(open_stmt)).scalar_one_or_none()
        if existing is not None:
            existing.raw_alternatives_text = (
                f"{existing.raw_alternatives_text or ''}\n---\n{raw_body}".strip()
            )
            response.status = "reschedule_requested"
            response.processed_at = datetime.now(tz=timezone.utc)
            await self.db.flush()
            self.log_rejected(
                "handle_estimate_visit_reschedule",
                reason="duplicate_open_request",
                sales_calendar_event_id=str(sales_calendar_event_id),
                existing_request_id=str(existing.id),
            )
            return {
                "action": "reschedule_requested",
                "sales_calendar_event_id": str(sales_calendar_event_id),
                "reschedule_request_id": str(existing.id),
                "auto_reply": _AUTO_REPLIES[ConfirmationKeyword.RESCHEDULE],
                "duplicate": True,
            }

        reschedule = RescheduleRequest(
            job_id=None,
            appointment_id=None,
            sales_calendar_event_id=sales_calendar_event_id,
            customer_id=customer_id,
            original_reply_id=response.id,
            raw_alternatives_text=raw_body,
            status="open",
        )
        try:
            async with self.db.begin_nested():
                self.db.add(reschedule)
                await self.db.flush()
        except IntegrityError:
            existing = (await self.db.execute(open_stmt)).scalar_one_or_none()
            if existing is None:
                raise
            existing.raw_alternatives_text = (
                f"{existing.raw_alternatives_text or ''}\n---\n{raw_body}".strip()
            )
            response.status = "reschedule_requested"
            response.processed_at = datetime.now(tz=timezone.utc)
            await self.db.flush()
            return {
                "action": "reschedule_requested",
                "sales_calendar_event_id": str(sales_calendar_event_id),
                "reschedule_request_id": str(existing.id),
                "auto_reply": _AUTO_REPLIES[ConfirmationKeyword.RESCHEDULE],
                "duplicate": True,
            }

        event = await self.db.get(SalesCalendarEvent, sales_calendar_event_id)
        if event is not None and event.confirmation_status != "cancelled":
            event.confirmation_status = "reschedule_requested"
            event.confirmation_status_at = datetime.now(tz=timezone.utc)

        response.status = "reschedule_requested"
        response.processed_at = datetime.now(tz=timezone.utc)
        await self.db.flush()

        logger.info(
            "sales.calendar_event.reschedule_requested",
            sales_calendar_event_id=str(sales_calendar_event_id),
            reschedule_request_id=str(reschedule.id),
        )

        return {
            "action": "reschedule_requested",
            "sales_calendar_event_id": str(sales_calendar_event_id),
            "reschedule_request_id": str(reschedule.id),
            "auto_reply": _AUTO_REPLIES[ConfirmationKeyword.RESCHEDULE],
        }

    async def _handle_estimate_visit_cancel(
        self,
        *,
        response: JobConfirmationResponse,
        sales_calendar_event_id: UUID,
        customer_id: UUID,
    ) -> dict[str, Any]:
        """CANCEL: flip event to ``cancelled`` + raise admin alert."""
        from grins_platform.models.sales import SalesCalendarEvent  # noqa: PLC0415

        event = await self.db.get(SalesCalendarEvent, sales_calendar_event_id)

        if event is not None and event.confirmation_status == "cancelled":
            response.status = "cancelled"
            response.processed_at = datetime.now(tz=timezone.utc)
            await self.db.flush()
            self.log_rejected(
                "handle_estimate_visit_cancel",
                reason="already_cancelled",
                sales_calendar_event_id=str(sales_calendar_event_id),
            )
            return {
                "action": "cancelled",
                "sales_calendar_event_id": str(sales_calendar_event_id),
                "auto_reply": "",
            }

        transitioned = False
        if event is not None:
            event.confirmation_status = "cancelled"
            event.confirmation_status_at = datetime.now(tz=timezone.utc)
            transitioned = True

        response.status = "cancelled"
        response.processed_at = datetime.now(tz=timezone.utc)
        await self.db.flush()

        if transitioned:
            await self._dispatch_estimate_visit_cancellation_alert(
                sales_calendar_event_id=sales_calendar_event_id,
                customer_id=customer_id,
                event=event,
            )

        logger.info(
            "sales.calendar_event.cancelled",
            sales_calendar_event_id=str(sales_calendar_event_id),
            transitioned=transitioned,
        )

        business_phone = os.environ.get("BUSINESS_PHONE_NUMBER", "")
        contact_clause = (
            f" Please call us at {business_phone} if you'd like to reschedule."
            if business_phone
            else " Please contact us if you'd like to reschedule."
        )
        auto_reply = "Your estimate visit has been cancelled." + contact_clause
        return {
            "action": "cancelled",
            "sales_calendar_event_id": str(sales_calendar_event_id),
            "auto_reply": auto_reply,
        }

    async def _handle_estimate_visit_needs_review(
        self,
        response: JobConfirmationResponse,
    ) -> dict[str, Any]:
        """Free-text or unknown reply on an estimate-visit thread."""
        sales_calendar_event_id = response.sales_calendar_event_id
        if sales_calendar_event_id is None:
            response.status = "needs_review"
            response.processed_at = datetime.now(tz=timezone.utc)
            await self.db.flush()
            return {"action": "needs_review", "response_id": str(response.id)}

        stmt = (
            select(RescheduleRequest)
            .where(
                RescheduleRequest.sales_calendar_event_id == sales_calendar_event_id,
                RescheduleRequest.status == "open",
            )
            .order_by(RescheduleRequest.created_at.desc())
            .limit(1)
        )
        reschedule_req = (await self.db.execute(stmt)).scalar_one_or_none()

        if reschedule_req is not None:
            now_iso = datetime.now(tz=timezone.utc).isoformat()
            new_entry = {"text": response.raw_reply_body, "at": now_iso}
            existing_alts = reschedule_req.requested_alternatives
            entries: list[dict[str, Any]]
            if isinstance(existing_alts, dict) and isinstance(
                existing_alts.get("entries"),
                list,
            ):
                entries = list(existing_alts["entries"])
            else:
                entries = []
            entries.append(new_entry)
            reschedule_req.requested_alternatives = {"entries": entries}
            reschedule_req.raw_alternatives_text = (
                f"{reschedule_req.raw_alternatives_text or ''}"
                f"\n---\n{response.raw_reply_body}"
            ).strip()
            response.status = "reschedule_alternatives_received"
            response.processed_at = datetime.now(tz=timezone.utc)
            await self.db.flush()
            return {
                "action": "reschedule_alternatives_received",
                "sales_calendar_event_id": str(sales_calendar_event_id),
                "reschedule_request_id": str(reschedule_req.id),
                "alternatives_text": response.raw_reply_body,
                "alternatives_count": len(entries),
            }

        response.status = "needs_review"
        response.processed_at = datetime.now(tz=timezone.utc)
        await self.db.flush()
        logger.warning(
            "estimate_visit.needs_review",
            response_id=str(response.id),
            raw_body=response.raw_reply_body,
        )
        return {"action": "needs_review", "response_id": str(response.id)}

    @staticmethod
    def _format_estimate_visit_window(event: Any | None) -> str:  # noqa: ANN401
        """Format an estimate visit's date + time window for SMS copy."""
        from grins_platform.services.sms.formatters import (  # noqa: PLC0415
            format_sms_time_12h,
        )

        if event is None:
            return ""
        scheduled_date = getattr(event, "scheduled_date", None)
        start_time = getattr(event, "start_time", None)
        if scheduled_date is None:
            return ""
        date_str: str = scheduled_date.strftime("%B %d, %Y")
        time_str = format_sms_time_12h(start_time) if start_time else None
        if time_str:
            return f"{date_str} at {time_str}"
        return date_str

    @classmethod
    def _build_estimate_confirm_message(cls, event: Any | None) -> str:  # noqa: ANN401
        """CONFIRM ack copy for the estimate-visit lifecycle."""
        when = cls._format_estimate_visit_window(event)
        if when:
            return f"Your estimate visit is confirmed. See you on {when}!"
        return "Your estimate visit is confirmed. See you then!"

    @classmethod
    def _build_estimate_confirm_reassurance(
        cls,
        event: Any | None,  # noqa: ANN401
    ) -> str:
        """Reassurance copy for a repeat ``Y`` on an already-confirmed visit."""
        when = cls._format_estimate_visit_window(event)
        if when:
            return f"You're already confirmed for {when}. See you then!"
        return "You're already confirmed. See you then!"

    async def _dispatch_estimate_visit_cancellation_alert(
        self,
        *,
        sales_calendar_event_id: UUID,
        customer_id: UUID,
        event: Any | None,  # noqa: ANN401
    ) -> None:
        """Raise an admin alert that the customer cancelled an estimate visit."""
        from grins_platform.models.alert import Alert  # noqa: PLC0415
        from grins_platform.models.customer import Customer  # noqa: PLC0415
        from grins_platform.models.enums import (  # noqa: PLC0415
            AlertSeverity,
            AlertType,
        )
        from grins_platform.repositories.alert_repository import (  # noqa: PLC0415
            AlertRepository,
        )

        try:
            customer = await self.db.get(Customer, customer_id)
            customer_name = customer.full_name if customer is not None else "customer"
            when = self._format_estimate_visit_window(event)
            tail = f" scheduled for {when}" if when else ""
            alert = Alert(
                type=AlertType.CUSTOMER_CANCELLED_APPOINTMENT.value,
                severity=AlertSeverity.WARNING.value,
                entity_type="sales_calendar_event",
                entity_id=sales_calendar_event_id,
                message=f"Estimate visit cancelled by {customer_name}{tail}.",
            )
            await AlertRepository(self.db).create(alert)
        except Exception:
            self.log_failed(
                "estimate_visit.admin_cancellation_alert",
                sales_calendar_event_id=str(sales_calendar_event_id),
            )
