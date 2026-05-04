"""AuditService for tracking administrative actions.

Provides log_action() to create audit log entries and get_audit_log()
for paginated, filterable retrieval. Also provides TCPA audit logging
for consent field toggles on leads and customers.

`details` JSONB discriminator (gap-05, 2026-04-26)
--------------------------------------------------

Audit rows whose action originates from a customer SMS, an admin UI
click, or a nightly job carry a stable shape inside ``details`` so the
admin history view can answer "who did this and why?" without joining
across actor / phone / handler tables:

- ``actor_type``: ``"customer"`` | ``"staff"`` | ``"system"``
- ``source``:     ``"customer_sms"`` | ``"admin_ui"`` | ``"nightly_job"``

Canonical action strings (do NOT invent new ones — extend this list
when adding a new flow):

- ``appointment.confirm``                        — first Y, SCHEDULED→CONFIRMED
- ``appointment.confirm_repeat``                 — Y on already-CONFIRMED
- ``appointment.reschedule_requested``           — customer R creates RescheduleRequest
- ``appointment.reschedule_rejected``            — late R blocked by state guard
- ``appointment.cancel``                         — admin cancel OR customer C
- ``appointment.update``                         — admin edit / drag-drop reschedule
- ``appointment.reactivate``                     — admin reschedules a CANCELLED appt
- ``appointment.reschedule.reconfirmation_sent`` — admin resolved a customer R
- ``appointment.reminder_sent``                  — manual reminder via admin UI
- ``appointment.mark_contacted``                 — admin clears needs_review_reason
- ``consent.opt_out_sms``                        — STOP keyword opt-out
- ``consent.opt_out_informal_flag``              — informal STOP phrase flagged
- ``consent.opt_out_admin_confirmed``            — admin confirms informal opt-out
- ``consent.opt_in_sms``                         — START keyword opt-in (F3)
- ``estimate.auto_job_created``                  — portal-approval auto-created a job
- ``estimate.auto_job_skipped``                  — auto-job branch skipped
- ``sales_pipeline.nudge.sent``                  — nightly job nudged a stale entry (F6)

Validates: CRM Gap Closure Req 74.1, 74.2, 74.3;
           april-16th-fixes-enhancements Req 2.7, 5.5, 5.9;
           scheduling gaps gap-05 (audit asymmetry)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any
from uuid import UUID

from grins_platform.log_config import LoggerMixin
from grins_platform.repositories.audit_log_repository import AuditLogRepository
from grins_platform.schemas.audit import AuditLogFilters, AuditLogResponse

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from grins_platform.models.audit_log import AuditLog

# Consent fields that require TCPA audit logging
LEAD_CONSENT_FIELDS = frozenset(
    {"sms_consent", "email_marketing_consent", "terms_accepted"},
)
CUSTOMER_CONSENT_FIELDS = frozenset({"sms_opt_in", "email_opt_in"})


class AuditService(LoggerMixin):
    """Service for audit log management.

    Called by other services at the point of auditable actions.
    A FastAPI dependency extracts ip_address and user_agent from
    the request and passes them through.

    Validates: CRM Gap Closure Req 74.1, 74.2, 74.3;
               april-16th-fixes-enhancements Req 2.7, 5.5, 5.9
    """

    DOMAIN = "audit"

    async def log_action(
        self,
        db: AsyncSession,
        *,
        actor_id: UUID | None = None,
        actor_role: str | None = None,
        action: str,
        resource_type: str,
        resource_id: UUID | str | None = None,
        details: dict[str, Any] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AuditLog:
        """Create an audit log entry for an administrative action.

        Args:
            db: Database session.
            actor_id: Staff UUID who performed the action.
            actor_role: Role of the actor (e.g. "admin", "staff").
            action: Action performed (e.g. "customer.merge").
            resource_type: Resource type affected (e.g. "customer").
            resource_id: Resource UUID.
            details: Additional event details (JSONB).
            ip_address: Client IP address.
            user_agent: Client user agent string.

        Returns:
            Created AuditLog instance.

        Validates: Req 74.1, 74.2
        """
        self.log_started(
            "log_action",
            audit_action=action,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id else None,
        )

        repo = AuditLogRepository(db)
        entry = await repo.create(
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            actor_id=actor_id,
            actor_role=actor_role,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        self.log_completed(
            "log_action",
            audit_log_id=str(entry.id),
            audit_action=action,
        )
        return entry

    async def get_audit_log(
        self,
        db: AsyncSession,
        filters: AuditLogFilters,
    ) -> dict[str, Any]:
        """Retrieve paginated, filterable audit log entries.

        Args:
            db: Database session.
            filters: AuditLogFilters with page, page_size, and optional filters.

        Returns:
            Dict with items (list of AuditLogResponse), total, page, page_size.

        Validates: Req 74.3
        """
        self.log_started(
            "get_audit_log",
            page=filters.page,
            page_size=filters.page_size,
        )

        repo = AuditLogRepository(db)
        entries, total = await repo.list_with_filters(filters)

        items = [AuditLogResponse.model_validate(e) for e in entries]

        self.log_completed(
            "get_audit_log",
            count=len(items),
            total=total,
        )
        return {
            "items": items,
            "total": total,
            "page": filters.page,
            "page_size": filters.page_size,
        }

    async def log_tcpa_consent_change(
        self,
        db: AsyncSession,
        *,
        actor_id: UUID,
        subject_type: str,
        subject_id: UUID,
        field: str,
        old_value: bool | None,
        new_value: bool | None,
    ) -> AuditLog:
        """Log a TCPA-relevant consent field change.

        Called when a consent field (sms_consent, email_marketing_consent,
        terms_accepted on leads; sms_opt_in, email_opt_in on customers)
        is toggled. Creates an audit log entry with the actor, subject,
        field name, old value, new value, and timestamp.

        Args:
            db: Database session.
            actor_id: Staff UUID who performed the change.
            subject_type: Entity type ('lead' or 'customer').
            subject_id: UUID of the entity being modified.
            field: Name of the consent field being changed.
            old_value: Previous value of the field.
            new_value: New value of the field.

        Returns:
            Created AuditLog instance.

        Validates: april-16th-fixes-enhancements Req 2.7, 5.5, 5.9
        """
        self.log_started(
            "log_tcpa_consent_change",
            subject_type=subject_type,
            subject_id=str(subject_id),
            field=field,
        )

        details = {
            "field": field,
            "old_value": old_value,
            "new_value": new_value,
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "tcpa_relevant": True,
        }

        entry = await self.log_action(
            db,
            actor_id=actor_id,
            action=f"{subject_type}.consent_change",
            resource_type=subject_type,
            resource_id=subject_id,
            details=details,
        )

        self.log_completed(
            "log_tcpa_consent_change",
            audit_log_id=str(entry.id),
            field=field,
        )
        return entry

    async def log_status_change(
        self,
        db: AsyncSession,
        *,
        actor_id: UUID,
        subject_type: str,
        subject_id: UUID,
        old_status: str | None,
        new_status: str,
    ) -> AuditLog:
        """Log a status change on a lead or customer.

        Args:
            db: Database session.
            actor_id: Staff UUID who performed the change.
            subject_type: Entity type ('lead' or 'customer').
            subject_id: UUID of the entity being modified.
            old_status: Previous status value.
            new_status: New status value.

        Returns:
            Created AuditLog instance.

        Validates: april-16th-fixes-enhancements Req 5.9
        """
        self.log_started(
            "log_status_change",
            subject_type=subject_type,
            subject_id=str(subject_id),
            old_status=old_status,
            new_status=new_status,
        )

        details = {
            "old_status": old_status,
            "new_status": new_status,
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        }

        entry = await self.log_action(
            db,
            actor_id=actor_id,
            action=f"{subject_type}.status_change",
            resource_type=subject_type,
            resource_id=subject_id,
            details=details,
        )

        self.log_completed(
            "log_status_change",
            audit_log_id=str(entry.id),
        )
        return entry

    async def log_last_contacted_edit(
        self,
        db: AsyncSession,
        *,
        actor_id: UUID,
        lead_id: UUID,
        old_value: datetime | None,
        new_value: datetime | None,
    ) -> AuditLog:
        """Log a manual edit of last_contacted_at on a lead.

        Args:
            db: Database session.
            actor_id: Staff UUID who performed the edit.
            lead_id: UUID of the lead being modified.
            old_value: Previous last_contacted_at value.
            new_value: New last_contacted_at value.

        Returns:
            Created AuditLog instance.

        Validates: april-16th-fixes-enhancements Req 13.5
        """
        self.log_started(
            "log_last_contacted_edit",
            lead_id=str(lead_id),
        )

        details = {
            "field": "last_contacted_at",
            "old_value": old_value.isoformat() if old_value else None,
            "new_value": new_value.isoformat() if new_value else None,
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "manual_edit": True,
        }

        entry = await self.log_action(
            db,
            actor_id=actor_id,
            action="lead.last_contacted_edit",
            resource_type="lead",
            resource_id=lead_id,
            details=details,
        )

        self.log_completed(
            "log_last_contacted_edit",
            audit_log_id=str(entry.id),
        )
        return entry
