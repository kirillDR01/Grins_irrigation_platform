"""Sales pipeline service for estimate-to-job workflow.

Validates: CRM Changes Update 2 Req 14.3, 14.4, 14.5, 14.7, 14.8, 14.9,
           16.1, 16.2, 16.3, 16.4
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any, Literal

from sqlalchemy import select

from grins_platform.exceptions import (
    CustomerHasNoPhoneError,
    CustomerNotFoundError,
    EstimateNotConfirmedError,
    InvalidSalesTransitionError,
    SalesCalendarEventNotFoundError,
    SalesEntryNotFoundError,
)
from grins_platform.log_config import LoggerMixin
from grins_platform.models.customer import Customer
from grins_platform.models.enums import (
    SALES_PIPELINE_ORDER,
    SALES_TERMINAL_STATUSES,
    VALID_SALES_TRANSITIONS,
    JobCategory,
    SalesEntryStatus,
)
from grins_platform.models.sales import SalesCalendarEvent, SalesEntry
from grins_platform.schemas.ai import MessageType
from grins_platform.schemas.job import JobCreate
from grins_platform.services.sms.recipient import Recipient

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from grins_platform.models.estimate import Estimate
    from grins_platform.models.job import Job
    from grins_platform.services.audit_service import AuditService
    from grins_platform.services.job_service import JobService
    from grins_platform.services.sms_service import SMSService


class SalesPipelineService(LoggerMixin):
    """Orchestrates the sales pipeline estimate-to-job workflow.

    Validates: CRM Changes Update 2 Req 14.3-14.9, 16.1-16.4
    """

    DOMAIN = "sales"

    def __init__(
        self,
        job_service: JobService,
        audit_service: AuditService,
    ) -> None:
        super().__init__()
        self.job_service = job_service
        self.audit_service = audit_service

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _get_entry(self, db: AsyncSession, entry_id: UUID) -> SalesEntry:
        result = await db.execute(
            select(SalesEntry).where(SalesEntry.id == entry_id),
        )
        entry: SalesEntry | None = result.scalar_one_or_none()
        if not entry:
            raise SalesEntryNotFoundError(entry_id)
        return entry

    def _next_status(self, current: SalesEntryStatus) -> SalesEntryStatus:
        """Return the next status in the pipeline order."""
        try:
            idx = SALES_PIPELINE_ORDER.index(current)
        except ValueError as exc:
            raise InvalidSalesTransitionError(
                current.value,
                current.value,
            ) from exc
        if idx + 1 >= len(SALES_PIPELINE_ORDER):
            raise InvalidSalesTransitionError(current.value, current.value)
        return SALES_PIPELINE_ORDER[idx + 1]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def record_estimate_decision_breadcrumb(
        self,
        db: AsyncSession,
        estimate: Estimate,
        decision: Literal["approved", "rejected"],
        *,
        reason: str | None = None,
        actor_id: UUID | None = None,
    ) -> SalesEntry | None:
        """Append a note + audit row to the active SalesEntry for ``estimate``.

        Best-effort. Never raises — internal notification and the
        customer-side decision are higher priority than the breadcrumb.

        Match strategy:
          1. By ``estimate.customer_id`` → active SalesEntry
             (status NOT IN closed_won, closed_lost), most recently
             updated.
          2. Else by ``estimate.lead_id`` → same.
          3. If neither: log and return ``None``.

        Where the customer has TWO active SalesEntries (e.g., a
        winterization deal and a separate spring-startup deal both in
        ``send_estimate``) the most recently updated entry wins. The
        other is untouched.

        Validates: Feature — estimate approval email portal Q-A.
        """
        self.log_started(
            "record_estimate_decision_breadcrumb",
            estimate_id=str(estimate.id),
            decision=decision,
        )
        try:
            customer_id = getattr(estimate, "customer_id", None)
            lead_id = getattr(estimate, "lead_id", None)

            conditions = [
                SalesEntry.status.notin_(
                    [
                        SalesEntryStatus.CLOSED_WON.value,
                        SalesEntryStatus.CLOSED_LOST.value,
                    ]
                ),
            ]
            if customer_id is not None:
                conditions.append(SalesEntry.customer_id == customer_id)
            elif lead_id is not None:
                conditions.append(SalesEntry.lead_id == lead_id)
            else:
                self.log_rejected(
                    "record_estimate_decision_breadcrumb",
                    reason="estimate_has_no_customer_or_lead",
                    estimate_id=str(estimate.id),
                )
                return None

            stmt = (
                select(SalesEntry)
                .where(*conditions)
                .order_by(SalesEntry.updated_at.desc())
                .limit(1)
            )
            result = await db.execute(stmt)
            entry: SalesEntry | None = result.scalar_one_or_none()
            if not entry:
                self.logger.info(
                    "sales.estimate_correlation.no_active_entry",
                    estimate_id=str(estimate.id),
                    decision=decision,
                )
                return None

            now = datetime.now(tz=timezone.utc)
            ts = now.strftime("%Y-%m-%d %H:%M UTC")
            short_id = str(estimate.id)[:8]
            if decision == "approved":
                note_line = (
                    f"\n[{ts}] Customer APPROVED estimate {short_id} via portal. "
                    "Ready to send contract for signature."
                )
            else:
                reason_part = f' Reason: "{reason}".' if reason else ""
                note_line = (
                    f"\n[{ts}] Customer REJECTED estimate {short_id} via portal."
                    f"{reason_part}"
                )
            entry.notes = (entry.notes or "") + note_line
            entry.last_contact_date = now
            entry.updated_at = now

            _ = await self.audit_service.log_action(
                db,
                actor_id=actor_id,
                action="sales_entry.estimate_decision_received",
                resource_type="sales_entry",
                resource_id=entry.id,
                details={
                    "estimate_id": str(estimate.id),
                    "decision": decision,
                    "reason": reason,
                    "current_status": entry.status,
                },
            )
            await db.flush()
            self.log_completed(
                "record_estimate_decision_breadcrumb",
                entry_id=str(entry.id),
                decision=decision,
            )
        except Exception as e:
            self.log_failed(
                "record_estimate_decision_breadcrumb",
                error=e,
                estimate_id=str(estimate.id),
            )
            return None
        return entry

    async def create_from_lead(
        self,
        db: AsyncSession,
        lead_id: UUID,
        customer_id: UUID,
        job_type: str | None = None,
        notes: str | None = None,
    ) -> SalesEntry:
        """Create a pipeline entry from a lead move-out.

        Validates: Req 14.1
        """
        self.log_started("create_from_lead", lead_id=str(lead_id))

        entry = SalesEntry(
            customer_id=customer_id,
            lead_id=lead_id,
            job_type=job_type,
            status=SalesEntryStatus.SCHEDULE_ESTIMATE.value,
            notes=notes,
        )
        db.add(entry)
        await db.flush()
        await db.refresh(entry)

        self.log_completed("create_from_lead", entry_id=str(entry.id))
        return entry

    async def advance_status(
        self,
        db: AsyncSession,
        entry_id: UUID,
    ) -> SalesEntry:
        """Advance a sales entry one step forward in the pipeline.

        Programmatic advance to ``SEND_ESTIMATE`` is gated on the
        customer having confirmed the latest estimate visit (Y reply →
        ``SalesCalendarEvent.confirmation_status='confirmed'``). The
        manual-override path bypasses this guard.

        Validates: Req 14.3, 14.4, 14.5, 33.1, 33.3;
        sales-pipeline-estimate-visit-confirmation-lifecycle (OQ-6).
        """
        self.log_started("advance_status", entry_id=str(entry_id))

        entry = await self._get_entry(db, entry_id)
        current = SalesEntryStatus(entry.status)

        if current in SALES_TERMINAL_STATUSES:
            raise InvalidSalesTransitionError(current.value, current.value)

        target = self._next_status(current)

        if target not in VALID_SALES_TRANSITIONS.get(current, set()):
            raise InvalidSalesTransitionError(current.value, target.value)

        if target == SalesEntryStatus.SEND_ESTIMATE:
            latest_event = await self._get_latest_calendar_event(db, entry_id)
            event_status = (
                latest_event.confirmation_status
                if latest_event is not None
                else None
            )
            if event_status != "confirmed":
                self.log_rejected(
                    "advance_status",
                    reason="estimate_not_confirmed",
                    entry_id=str(entry_id),
                    confirmation_status=event_status,
                )
                raise EstimateNotConfirmedError(
                    entry_id,
                    current_status=event_status,
                )

        entry.status = target.value
        entry.updated_at = datetime.now(tz=timezone.utc)
        await db.flush()
        await db.refresh(entry)

        self.log_completed(
            "advance_status",
            entry_id=str(entry_id),
            from_status=current.value,
            to_status=target.value,
        )
        return entry

    async def _get_latest_calendar_event(
        self,
        db: AsyncSession,
        entry_id: UUID,
    ) -> SalesCalendarEvent | None:
        """Return the most recently created calendar event for ``entry_id``."""
        result = await db.execute(
            select(SalesCalendarEvent)
            .where(SalesCalendarEvent.sales_entry_id == entry_id)
            .order_by(SalesCalendarEvent.created_at.desc())
            .limit(1),
        )
        event: SalesCalendarEvent | None = result.scalar_one_or_none()
        return event

    async def manual_override_status(
        self,
        db: AsyncSession,
        entry_id: UUID,
        new_status: SalesEntryStatus,
        *,
        closed_reason: str | None = None,
        actor_id: UUID | None = None,
    ) -> SalesEntry:
        """Admin escape-hatch: set status to any value with audit log.

        Validates: Req 14.8
        """
        self.log_started(
            "manual_override_status",
            entry_id=str(entry_id),
            new_status=new_status.value,
        )

        entry = await self._get_entry(db, entry_id)
        old_status = entry.status

        entry.status = new_status.value
        entry.updated_at = datetime.now(tz=timezone.utc)
        if closed_reason is not None:
            entry.closed_reason = closed_reason

        _ = await self.audit_service.log_action(
            db,
            actor_id=actor_id,
            action="sales_entry.status_override",
            resource_type="sales_entry",
            resource_id=entry_id,
            details={
                "old_status": old_status,
                "new_status": new_status.value,
                "closed_reason": closed_reason,
            },
        )

        await db.flush()
        await db.refresh(entry)

        self.log_completed(
            "manual_override_status",
            entry_id=str(entry_id),
            old_status=old_status,
            new_status=new_status.value,
        )
        return entry

    async def mark_lost(
        self,
        db: AsyncSession,
        entry_id: UUID,
        *,
        closed_reason: str | None = None,
        actor_id: UUID | None = None,
    ) -> SalesEntry:
        """Mark a sales entry as Closed-Lost.

        Validates: Req 14.7, 14.9
        """
        self.log_started("mark_lost", entry_id=str(entry_id))

        entry = await self._get_entry(db, entry_id)
        current = SalesEntryStatus(entry.status)

        if current in SALES_TERMINAL_STATUSES:
            raise InvalidSalesTransitionError(
                current.value,
                SalesEntryStatus.CLOSED_LOST.value,
            )

        entry.status = SalesEntryStatus.CLOSED_LOST.value
        entry.closed_reason = closed_reason
        entry.updated_at = datetime.now(tz=timezone.utc)

        _ = await self.audit_service.log_action(
            db,
            actor_id=actor_id,
            action="sales_entry.mark_lost",
            resource_type="sales_entry",
            resource_id=entry_id,
            details={"closed_reason": closed_reason},
        )

        await db.flush()
        await db.refresh(entry)

        self.log_completed("mark_lost", entry_id=str(entry_id))
        return entry

    async def convert_to_job(
        self,
        db: AsyncSession,
        entry_id: UUID,
        *,
        actor_id: UUID | None = None,
    ) -> Job:
        """Convert a sales entry to a Job record.

        Admin-discretion: no programmatic signature gate. Per Cluster C,
        the SignWell signature requirement was removed — admins control
        whether to advance an entry via the Create-Job modal.

        Job.category is forced to READY_TO_SCHEDULE because by the time
        a sales entry reaches this method it has already been approved.

        Validates: Req 16.1, 16.2, 16.3, 16.4
        """
        self.log_started(
            "convert_to_job",
            entry_id=str(entry_id),
        )

        entry = await self._get_entry(db, entry_id)
        current = SalesEntryStatus(entry.status)

        if current in SALES_TERMINAL_STATUSES:
            raise InvalidSalesTransitionError(
                current.value,
                SalesEntryStatus.CLOSED_WON.value,
            )

        # Create job from sales entry data
        job_data = JobCreate(
            customer_id=entry.customer_id,
            property_id=entry.property_id,
            job_type=entry.job_type or "estimate",
            description=entry.notes,
        )
        job = await self.job_service.create_job(
            job_data,
            category_override=JobCategory.READY_TO_SCHEDULE,
        )

        # Update sales entry
        entry.status = SalesEntryStatus.CLOSED_WON.value
        entry.updated_at = datetime.now(tz=timezone.utc)

        if actor_id is not None:
            _ = await self.audit_service.log_action(
                db,
                actor_id=actor_id,
                action="sales_entry.convert_to_job",
                resource_type="sales_entry",
                resource_id=entry_id,
                details={"job_id": str(job.id)},
            )

        await db.flush()
        await db.refresh(entry)

        self.log_completed(
            "convert_to_job",
            entry_id=str(entry_id),
            job_id=str(job.id),
        )
        return job

    # ------------------------------------------------------------------
    # NEW-D: pause/unpause nudges, send text confirmation, dismiss
    # ------------------------------------------------------------------

    async def pause_nudges(
        self,
        db: AsyncSession,
        entry_id: UUID,
        *,
        paused_until: datetime | None = None,
        actor_id: UUID | None = None,
    ) -> SalesEntry:
        """Pause auto-nudge cadence for ``entry_id`` until ``paused_until``.

        Defaults to ``now + 7 days`` when ``paused_until`` is None.
        Last call wins — re-pausing an already-paused entry refreshes
        the window.

        Validates: NEW-D pause/unpause nudges.
        """
        self.log_started("pause_nudges", entry_id=str(entry_id))

        entry = await self._get_entry(db, entry_id)
        target = paused_until or (datetime.now(tz=timezone.utc) + timedelta(days=7))
        entry.nudges_paused_until = target
        entry.updated_at = datetime.now(tz=timezone.utc)
        await db.flush()
        await db.refresh(entry)

        self.log_completed(
            "pause_nudges",
            entry_id=str(entry_id),
            paused_until=target.isoformat(),
        )
        _ = actor_id  # reserved for future audit hook
        return entry

    async def unpause_nudges(
        self,
        db: AsyncSession,
        entry_id: UUID,
        *,
        actor_id: UUID | None = None,
    ) -> SalesEntry:
        """Clear ``nudges_paused_until`` so the entry resumes nudges.

        Validates: NEW-D pause/unpause nudges.
        """
        self.log_started("unpause_nudges", entry_id=str(entry_id))

        entry = await self._get_entry(db, entry_id)
        entry.nudges_paused_until = None
        entry.updated_at = datetime.now(tz=timezone.utc)
        await db.flush()
        await db.refresh(entry)

        self.log_completed("unpause_nudges", entry_id=str(entry_id))
        _ = actor_id
        return entry

    async def send_text_confirmation(
        self,
        db: AsyncSession,
        entry_id: UUID,
        *,
        sms_service: SMSService,
        actor_id: UUID | None = None,
    ) -> dict[str, Any]:
        """Compat shim — resend the latest estimate-visit confirmation.

        Looks up the most recent ``SalesCalendarEvent`` for ``entry_id``
        and delegates to :meth:`send_estimate_visit_confirmation` so the
        outbound SMS asks for Y/R/C and is correlated to the visit
        (which the prior implementation did not — replies fell through).
        Keeps the legacy ``POST .../send-text-confirmation`` endpoint
        working without changing its contract.

        Validates: sales-pipeline-estimate-visit-confirmation-lifecycle
        (OQ-4).
        """
        self.log_started("send_text_confirmation", entry_id=str(entry_id))

        latest_event = await self._get_latest_calendar_event(db, entry_id)
        if latest_event is None:
            self.log_rejected(
                "send_text_confirmation",
                reason="no_calendar_event",
                entry_id=str(entry_id),
            )
            raise SalesCalendarEventNotFoundError(entry_id)

        result = await self.send_estimate_visit_confirmation(
            db,
            event_id=latest_event.id,
            sms_service=sms_service,
            resend=True,
            actor_id=actor_id,
        )
        self.log_completed(
            "send_text_confirmation",
            entry_id=str(entry_id),
            message_id=str(result.get("message_id")),
        )
        return result

    async def send_estimate_visit_confirmation(
        self,
        db: AsyncSession,
        event_id: UUID,
        *,
        sms_service: SMSService,
        resend: bool = False,
        actor_id: UUID | None = None,
    ) -> dict[str, Any]:
        """Send the Y/R/C SMS for an estimate visit and prime the lifecycle.

        Composes an estimate-tailored confirmation body, dispatches via
        :meth:`SMSService.send_message` with
        ``message_type=ESTIMATE_VISIT_CONFIRMATION`` and
        ``sales_calendar_event_id=event.id`` so inbound replies correlate
        back. On first send the entry advances ``schedule_estimate`` →
        ``estimate_scheduled``.

        Validates: sales-pipeline-estimate-visit-confirmation-lifecycle.
        """
        self.log_started(
            "send_estimate_visit_confirmation",
            event_id=str(event_id),
            resend=resend,
        )

        event_result = await db.execute(
            select(SalesCalendarEvent).where(SalesCalendarEvent.id == event_id),
        )
        event: SalesCalendarEvent | None = event_result.scalar_one_or_none()
        if event is None:
            self.log_rejected(
                "send_estimate_visit_confirmation",
                reason="event_not_found",
                event_id=str(event_id),
            )
            raise SalesCalendarEventNotFoundError(event_id)

        customer_result = await db.execute(
            select(Customer).where(Customer.id == event.customer_id),
        )
        customer = customer_result.scalar_one_or_none()
        if customer is None:
            self.log_rejected(
                "send_estimate_visit_confirmation",
                reason="customer_not_found",
                event_id=str(event_id),
            )
            raise CustomerNotFoundError(event.customer_id)
        if not customer.phone:
            self.log_rejected(
                "send_estimate_visit_confirmation",
                reason="no_phone",
                event_id=str(event_id),
            )
            raise CustomerHasNoPhoneError(customer.id)

        body = self._build_estimate_visit_confirmation_body(
            customer=customer,
            event=event,
        )
        recipient = Recipient.from_customer(customer)
        result = await sms_service.send_message(
            recipient,
            body,
            MessageType.ESTIMATE_VISIT_CONFIRMATION,
            consent_type="transactional",
            sales_calendar_event_id=event.id,
        )

        if event.confirmation_status != "pending" or resend:
            event.confirmation_status = "pending"
            event.confirmation_status_at = datetime.now(tz=timezone.utc)

        # Per OQ-6: auto-advance to ESTIMATE_SCHEDULED only on first
        # successful SMS dispatch. The auto-advance previously fired on
        # bare event creation (api/v1/sales_pipeline.py:726-742) is gone —
        # an event without a confirmation SMS no longer claims the
        # customer has been told.
        entry = await self._get_entry(db, event.sales_entry_id)
        if entry.status == SalesEntryStatus.SCHEDULE_ESTIMATE.value:
            entry.status = SalesEntryStatus.ESTIMATE_SCHEDULED.value
            entry.updated_at = datetime.now(tz=timezone.utc)
            self.logger.info(
                "sales.calendar_event.confirmation_sent.advance",
                sales_entry_id=str(entry.id),
                from_status=SalesEntryStatus.SCHEDULE_ESTIMATE.value,
                to_status=SalesEntryStatus.ESTIMATE_SCHEDULED.value,
            )

        await db.flush()

        self.log_completed(
            "send_estimate_visit_confirmation",
            event_id=str(event_id),
            message_id=str(result.get("message_id")),
        )
        _ = actor_id
        return result

    @staticmethod
    def _build_estimate_visit_confirmation_body(
        *,
        customer: Customer,
        event: SalesCalendarEvent,
    ) -> str:
        """Compose the estimate-tailored Y/R/C SMS body."""
        from grins_platform.services.sms.formatters import (  # noqa: PLC0415
            format_sms_time_12h,
        )

        first_name = customer.first_name or "there"
        date_str = event.scheduled_date.strftime("%B %d, %Y")
        time_str = format_sms_time_12h(event.start_time) if event.start_time else None
        when = f"{date_str} at {time_str}" if time_str else date_str
        return (
            f"Hi {first_name}, your estimate visit with Grin's Irrigation "
            f"is scheduled for {when}. Reply Y to confirm, R to "
            "reschedule, or C to cancel."
        )

    async def dismiss_entry(
        self,
        db: AsyncSession,
        entry_id: UUID,
        *,
        actor_id: UUID | None = None,
    ) -> SalesEntry:
        """Mark a pipeline row as dismissed (idempotent).

        Sets ``dismissed_at = now()``. A second call leaves the existing
        timestamp untouched — repeat dismisses are a no-op.

        Validates: NEW-D pipeline-list dismiss.
        """
        self.log_started("dismiss_entry", entry_id=str(entry_id))

        entry = await self._get_entry(db, entry_id)
        if entry.dismissed_at is None:
            now = datetime.now(tz=timezone.utc)
            entry.dismissed_at = now
            entry.updated_at = now
            await db.flush()
            await db.refresh(entry)
            self.log_completed(
                "dismiss_entry",
                entry_id=str(entry_id),
                already_dismissed=False,
            )
        else:
            self.log_completed(
                "dismiss_entry",
                entry_id=str(entry_id),
                already_dismissed=True,
            )
        _ = actor_id
        return entry
