"""Sales pipeline service for estimate-to-job workflow.

Validates: CRM Changes Update 2 Req 14.3, 14.4, 14.5, 14.7, 14.8, 14.9,
           16.1, 16.2, 16.3, 16.4
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Literal

from sqlalchemy import select

from grins_platform.exceptions import (
    InvalidSalesTransitionError,
    SalesEntryNotFoundError,
    SignatureRequiredError,
)
from grins_platform.log_config import LoggerMixin
from grins_platform.models.enums import (
    SALES_PIPELINE_ORDER,
    SALES_TERMINAL_STATUSES,
    VALID_SALES_TRANSITIONS,
    SalesEntryStatus,
)
from grins_platform.models.sales import SalesEntry
from grins_platform.schemas.job import JobCreate

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from grins_platform.models.estimate import Estimate
    from grins_platform.models.job import Job
    from grins_platform.services.audit_service import AuditService
    from grins_platform.services.job_service import JobService


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

        Validates: Req 14.3, 14.4, 14.5, 33.1, 33.3
        """
        self.log_started("advance_status", entry_id=str(entry_id))

        entry = await self._get_entry(db, entry_id)
        current = SalesEntryStatus(entry.status)

        if current in SALES_TERMINAL_STATUSES:
            raise InvalidSalesTransitionError(current.value, current.value)

        target = self._next_status(current)

        if target not in VALID_SALES_TRANSITIONS.get(current, set()):
            raise InvalidSalesTransitionError(current.value, target.value)

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
        force: bool = False,
        actor_id: UUID | None = None,
    ) -> Job:
        """Convert a sales entry to a Job record.

        Gated on customer signature unless force=True.

        Validates: Req 16.1, 16.2, 16.3, 16.4
        """
        self.log_started(
            "convert_to_job",
            entry_id=str(entry_id),
            force=force,
        )

        entry = await self._get_entry(db, entry_id)
        current = SalesEntryStatus(entry.status)

        if current in SALES_TERMINAL_STATUSES:
            raise InvalidSalesTransitionError(
                current.value,
                SalesEntryStatus.CLOSED_WON.value,
            )

        # Signature gating: require signwell_document_id unless force
        has_signature = bool(entry.signwell_document_id)
        if not has_signature and not force:
            raise SignatureRequiredError(entry_id)

        # Create job from sales entry data
        job_data = JobCreate(
            customer_id=entry.customer_id,
            property_id=entry.property_id,
            job_type=entry.job_type or "estimate",
            description=entry.notes,
        )
        job = await self.job_service.create_job(job_data)

        # Update sales entry
        entry.status = SalesEntryStatus.CLOSED_WON.value
        entry.updated_at = datetime.now(tz=timezone.utc)
        if force and not has_signature:
            entry.override_flag = True

        # Audit log for force override
        if force and not has_signature:
            _ = await self.audit_service.log_action(
                db,
                actor_id=actor_id,
                action="sales_entry.force_convert",
                resource_type="sales_entry",
                resource_id=entry_id,
                details={
                    "job_id": str(job.id),
                    "override_reason": "No signature on file",
                },
            )

        await db.flush()
        await db.refresh(entry)

        self.log_completed(
            "convert_to_job",
            entry_id=str(entry_id),
            job_id=str(job.id),
            forced=force and not has_signature,
        )
        return job
