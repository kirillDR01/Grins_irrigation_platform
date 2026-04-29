"""
ChangeRequestService — manages resource-initiated schedule change requests.

Validates: Requirements 2.4, 14.3, 14.4, 14.6, 14.7, 14.10,
           15.3, 15.4, 15.6, 15.7, 15.10
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import select

from grins_platform.log_config import LoggerMixin
from grins_platform.models.change_request import ChangeRequest
from grins_platform.schemas.ai_scheduling import ChangeRequestResponse

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class ChangeRequestResult:
    """Result of approving or denying a change request."""

    __slots__ = ("change_request", "message", "success")

    def __init__(
        self,
        success: bool,
        message: str,
        change_request: ChangeRequest | None = None,
    ) -> None:
        self.success = success
        self.message = message
        self.change_request = change_request


# Valid request types
_VALID_REQUEST_TYPES = frozenset(
    {
        "delay_report",
        "followup_job",
        "access_issue",
        "nearby_pickup",
        "resequence",
        "crew_assist",
        "parts_log",
        "upgrade_quote",
    }
)


class ChangeRequestService(LoggerMixin):
    """Manages resource-initiated schedule change requests.

    Handles creation, approval, and denial of change requests from
    field resources. Approved requests trigger the corresponding
    schedule action.

    Attributes:
        DOMAIN: Logging domain identifier.
    """

    DOMAIN = "scheduling"

    def __init__(self, session: AsyncSession) -> None:
        """Initialise the change request service.

        Args:
            session: Async SQLAlchemy session.
        """
        super().__init__()
        self._session = session

    async def create_request(
        self,
        resource_id: UUID,
        request_type: str,
        details: dict[str, Any] | None = None,
        affected_job_id: UUID | None = None,
    ) -> ChangeRequest:
        """Create a new change request from a resource.

        Args:
            resource_id: Staff UUID of the requesting resource.
            request_type: Type of request (must be in _VALID_REQUEST_TYPES).
            details: Request-specific details.
            affected_job_id: Primary job affected by the request.

        Returns:
            Newly created ``ChangeRequest`` record.

        Raises:
            ValueError: If request_type is not valid.
        """
        self.log_started(
            "create_request",
            resource_id=str(resource_id),
            request_type=request_type,
        )

        if request_type not in _VALID_REQUEST_TYPES:
            msg = (
                f"Invalid request_type '{request_type}'. "
                f"Must be one of: {sorted(_VALID_REQUEST_TYPES)}"
            )
            raise ValueError(msg)

        try:
            recommended_action = self._recommend_action(request_type, details or {})

            cr = ChangeRequest(
                resource_id=resource_id,
                request_type=request_type,
                details=details,
                affected_job_id=affected_job_id,
                recommended_action=recommended_action,
                status="pending",
            )
            self._session.add(cr)
            await self._session.flush()

        except Exception as exc:
            self.log_failed(
                "create_request",
                error=exc,
                resource_id=str(resource_id),
                request_type=request_type,
            )
            raise
        else:
            self.log_completed(
                "create_request",
                resource_id=str(resource_id),
                request_type=request_type,
                change_request_id=str(cr.id),
            )
            return cr

    async def approve_request(
        self,
        request_id: UUID,
        admin_id: UUID,
        admin_notes: str | None = None,
    ) -> ChangeRequestResult:
        """Approve a change request and execute the action.

        Args:
            request_id: Change request UUID.
            admin_id: Admin staff UUID.
            admin_notes: Optional admin notes.

        Returns:
            ``ChangeRequestResult`` with success flag and message.
        """
        self.log_started(
            "approve_request",
            request_id=str(request_id),
            admin_id=str(admin_id),
        )

        try:
            stmt = select(ChangeRequest).where(ChangeRequest.id == request_id)
            result = await self._session.execute(stmt)
            cr = result.scalar_one_or_none()

            if cr is None:
                return ChangeRequestResult(
                    success=False,
                    message=f"Change request {request_id} not found.",
                )

            if cr.status != "pending":
                return ChangeRequestResult(
                    success=False,
                    message=(
                        f"Change request {request_id} is already {cr.status}. "
                        "Only pending requests can be approved."
                    ),
                    change_request=cr,
                )

            cr.status = "approved"
            cr.admin_id = admin_id
            cr.admin_notes = admin_notes
            cr.resolved_at = datetime.now(tz=timezone.utc)
            await self._session.flush()

            # Execute the approved action
            await self._execute_action(cr)

        except Exception as exc:
            self.log_failed(
                "approve_request",
                error=exc,
                request_id=str(request_id),
            )
            raise
        else:
            self.log_completed(
                "approve_request",
                request_id=str(request_id),
                admin_id=str(admin_id),
            )
            return ChangeRequestResult(
                success=True,
                message=f"Change request {request_id} approved and executed.",
                change_request=cr,
            )

    async def deny_request(
        self,
        request_id: UUID,
        admin_id: UUID,
        reason: str,
    ) -> ChangeRequestResult:
        """Deny a change request with a reason.

        Args:
            request_id: Change request UUID.
            admin_id: Admin staff UUID.
            reason: Reason for denial.

        Returns:
            ``ChangeRequestResult`` with success flag and message.
        """
        self.log_started(
            "deny_request",
            request_id=str(request_id),
            admin_id=str(admin_id),
        )

        try:
            stmt = select(ChangeRequest).where(ChangeRequest.id == request_id)
            result = await self._session.execute(stmt)
            cr = result.scalar_one_or_none()

            if cr is None:
                return ChangeRequestResult(
                    success=False,
                    message=f"Change request {request_id} not found.",
                )

            if cr.status != "pending":
                return ChangeRequestResult(
                    success=False,
                    message=(
                        f"Change request {request_id} is already {cr.status}. "
                        "Only pending requests can be denied."
                    ),
                    change_request=cr,
                )

            cr.status = "denied"
            cr.admin_id = admin_id
            cr.admin_notes = reason
            cr.resolved_at = datetime.now(tz=timezone.utc)
            await self._session.flush()

        except Exception as exc:
            self.log_failed(
                "deny_request",
                error=exc,
                request_id=str(request_id),
            )
            raise
        else:
            self.log_completed(
                "deny_request",
                request_id=str(request_id),
                admin_id=str(admin_id),
            )
            return ChangeRequestResult(
                success=True,
                message=f"Change request {request_id} denied: {reason}",
                change_request=cr,
            )

    def to_response(self, cr: ChangeRequest) -> ChangeRequestResponse:
        """Convert a ChangeRequest model to response schema.

        Args:
            cr: ChangeRequest model instance.

        Returns:
            ``ChangeRequestResponse`` schema.
        """
        return ChangeRequestResponse(
            id=cr.id,  # type: ignore[arg-type]
            resource_id=cr.resource_id,
            request_type=cr.request_type,
            details=cr.details,
            affected_job_id=cr.affected_job_id,
            recommended_action=cr.recommended_action,
            status=cr.status,
            created_at=cr.created_at,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _recommend_action(
        request_type: str,
        _details: dict[str, Any],
    ) -> str:
        """Generate an AI-recommended action for a request type."""
        recommendations: dict[str, str] = {
            "delay_report": (
                "Recalculate ETAs for remaining jobs and notify affected customers."
            ),
            "followup_job": (
                "Review field notes and schedule follow-up job at earliest"
                " availability."
            ),
            "access_issue": ("Contact customer to resolve access issue or reschedule."),
            "nearby_pickup": (
                "Review nearby jobs and assign if skills and equipment match."
            ),
            "resequence": (
                "Evaluate route efficiency and approve resequencing if beneficial."
            ),
            "crew_assist": (
                "Find nearest qualified resource and dispatch for assistance."
            ),
            "parts_log": ("Update job record and check truck inventory levels."),
            "upgrade_quote": (
                "Review equipment age and generate upgrade quote for customer."
            ),
        }
        return recommendations.get(
            request_type,
            f"Review {request_type} request and take appropriate action.",
        )

    async def _execute_action(self, cr: ChangeRequest) -> None:
        """Execute the action for an approved change request.

        Args:
            cr: Approved ChangeRequest record.
        """
        self.logger.info(
            "scheduling.changerequestsvc.action_executed",
            request_type=cr.request_type,
            change_request_id=str(cr.id),
            resource_id=str(cr.resource_id),
        )
        # Specific execution logic per request type would be implemented here.
        # For now, log the execution — downstream services handle the actual changes.
