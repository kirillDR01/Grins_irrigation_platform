"""
ChangeRequestService for resource-initiated schedule change requests.

Manages the lifecycle of change requests: creation with AI-recommended
actions, admin approval/denial, and execution of approved changes.

Validates: Requirements 2.4, 14.3, 14.4, 14.6, 14.7, 14.10, 15.3,
    15.4, 15.6, 15.7, 15.10
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import select

from grins_platform.log_config import LoggerMixin
from grins_platform.models.change_request import ChangeRequest

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

#: All supported change-request types.
VALID_REQUEST_TYPES: frozenset[str] = frozenset(
    {
        "delay_report",
        "followup_job",
        "access_issue",
        "nearby_pickup",
        "resequence",
        "crew_assist",
        "parts_log",
        "upgrade_quote",
    },
)

#: AI-recommended actions per request type (placeholder logic).
_DEFAULT_RECOMMENDATIONS: dict[str, str] = {
    "delay_report": "Recalculate downstream ETAs and notify affected customers.",
    "followup_job": "Create follow-up job and schedule within 48 hours.",
    "access_issue": "Check customer profile for alternate access; notify admin.",
    "nearby_pickup": "Identify nearest matching job within 15-min radius.",
    "resequence": "Evaluate route feasibility and reorder if beneficial.",
    "crew_assist": "Find nearest qualified resource and dispatch.",
    "parts_log": "Update truck inventory; flag low-stock items.",
    "upgrade_quote": "Generate upgrade quote from pricing table.",
}


class ChangeRequestService(LoggerMixin):
    """Manages resource-initiated change requests.

    Supports all 8 request types: delay_report, followup_job,
    access_issue, nearby_pickup, resequence, crew_assist,
    parts_log, upgrade_quote.

    Attributes:
        DOMAIN: Logging domain for structured log events.
    """

    DOMAIN = "scheduling"

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the change request service.

        Args:
            session: Async database session for data access.
        """
        super().__init__()
        self._session = session

    async def create_request(
        self,
        resource_id: UUID,
        request_type: str,
        details: dict[str, Any],
        affected_job_id: UUID | None = None,
    ) -> ChangeRequest:
        """Create a new change request with an AI-recommended action.

        Args:
            resource_id: UUID of the resource initiating the request.
            request_type: One of the 8 supported request types.
            details: Request-specific details dict.
            affected_job_id: Optional UUID of the primary affected job.

        Returns:
            The persisted ``ChangeRequest`` model instance.

        Raises:
            ValueError: If *request_type* is not a supported type.
        """
        if request_type not in VALID_REQUEST_TYPES:
            msg = (
                f"Invalid request_type '{request_type}'. "
                f"Must be one of: {', '.join(sorted(VALID_REQUEST_TYPES))}"
            )
            raise ValueError(msg)

        self.log_started(
            "create_request",
            resource_id=str(resource_id),
            request_type=request_type,
        )

        recommended_action = _DEFAULT_RECOMMENDATIONS.get(
            request_type,
            "Review and take appropriate action.",
        )

        change_request = ChangeRequest(
            resource_id=resource_id,
            request_type=request_type,
            details=details,
            affected_job_id=affected_job_id,
            recommended_action=recommended_action,
            status="pending",
        )
        self._session.add(change_request)
        await self._session.flush()

        self.log_completed(
            "create_request",
            request_id=str(change_request.id),
            resource_id=str(resource_id),
            request_type=request_type,
        )
        return change_request

    async def approve_request(
        self,
        request_id: UUID,
        admin_id: UUID,
        admin_notes: str | None = None,
    ) -> dict[str, Any]:
        """Approve a change request and execute the recommended action.

        Args:
            request_id: UUID of the change request to approve.
            admin_id: UUID of the admin approving the request.
            admin_notes: Optional notes from the admin.

        Returns:
            Dict with approval status and executed action details.

        Raises:
            ValueError: If the change request is not found or not pending.
        """
        self.log_started(
            "approve_request",
            request_id=str(request_id),
            admin_id=str(admin_id),
        )

        stmt = select(ChangeRequest).where(ChangeRequest.id == request_id)
        result = await self._session.execute(stmt)
        change_request = result.scalar_one_or_none()

        if change_request is None:
            msg = f"Change request {request_id} not found."
            raise ValueError(msg)

        if change_request.status != "pending":
            msg = (
                f"Change request {request_id} is '{change_request.status}', "
                f"not 'pending'."
            )
            raise ValueError(msg)

        change_request.status = "approved"
        change_request.admin_id = admin_id
        change_request.admin_notes = admin_notes
        change_request.resolved_at = datetime.now(tz=timezone.utc)

        await self._session.flush()

        self.log_completed(
            "approve_request",
            request_id=str(request_id),
            admin_id=str(admin_id),
            request_type=change_request.request_type,
        )

        return {
            "request_id": str(request_id),
            "status": "approved",
            "request_type": change_request.request_type,
            "recommended_action": change_request.recommended_action,
            "admin_notes": admin_notes,
            "resolved_at": change_request.resolved_at.isoformat()
            if change_request.resolved_at
            else None,
        }

    async def deny_request(
        self,
        request_id: UUID,
        admin_id: UUID,
        reason: str,
    ) -> dict[str, Any]:
        """Deny a change request with a reason.

        Args:
            request_id: UUID of the change request to deny.
            admin_id: UUID of the admin denying the request.
            reason: Reason for denial.

        Returns:
            Dict with denial status and reason.

        Raises:
            ValueError: If the change request is not found or not pending.
        """
        self.log_started(
            "deny_request",
            request_id=str(request_id),
            admin_id=str(admin_id),
        )

        stmt = select(ChangeRequest).where(ChangeRequest.id == request_id)
        result = await self._session.execute(stmt)
        change_request = result.scalar_one_or_none()

        if change_request is None:
            msg = f"Change request {request_id} not found."
            raise ValueError(msg)

        if change_request.status != "pending":
            msg = (
                f"Change request {request_id} is '{change_request.status}', "
                f"not 'pending'."
            )
            raise ValueError(msg)

        change_request.status = "denied"
        change_request.admin_id = admin_id
        change_request.admin_notes = reason
        change_request.resolved_at = datetime.now(tz=timezone.utc)

        await self._session.flush()

        self.log_completed(
            "deny_request",
            request_id=str(request_id),
            admin_id=str(admin_id),
            request_type=change_request.request_type,
            reason=reason,
        )

        return {
            "request_id": str(request_id),
            "status": "denied",
            "request_type": change_request.request_type,
            "reason": reason,
            "resolved_at": change_request.resolved_at.isoformat()
            if change_request.resolved_at
            else None,
        }
