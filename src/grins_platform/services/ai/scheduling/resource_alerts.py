"""
ResourceAlertService for resource-facing mobile alerts and suggestions.

Generates alerts (schedule changes, equipment, access) and suggestions
(pre-job prep, upsell, departure, parts, pending approval) for the
resource mobile view.

Validates: Requirements 16.1-16.5, 17.1-17.5
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any
from uuid import UUID

from grins_platform.log_config import LoggerMixin

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class ResourceAlertService(LoggerMixin):
    """Resource-facing alert and suggestion generator.

    Produces structured dicts consumed by the resource mobile view
    for schedule-change alerts, equipment/access alerts, and
    optimisation suggestions.

    Attributes:
        DOMAIN: Logging domain for structured log events.
    """

    DOMAIN = "scheduling"

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the resource alert service.

        Args:
            session: Async database session for data access.
        """
        super().__init__()
        self._session = session

    # ------------------------------------------------------------------
    # Resource-facing alerts (5 types)
    # ------------------------------------------------------------------

    async def generate_job_added_alert(
        self,
        resource_id: UUID,
        job: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate an alert when a job is added to the resource's schedule.

        Args:
            resource_id: UUID of the affected resource.
            job: Dict with job details (job_id, customer_name, address,
                scheduled_time, job_type).

        Returns:
            Alert dict for the resource mobile view.
        """
        self.log_started(
            "generate_job_added_alert",
            resource_id=str(resource_id),
            job_id=str(job.get("job_id", "")),
        )

        alert = {
            "alert_type": "job_added",
            "resource_id": str(resource_id),
            "title": "New Job Added",
            "message": (
                f"A new {job.get('job_type', 'job')} has been added "
                f"to your schedule for {job.get('customer_name', 'a customer')} "
                f"at {job.get('address', 'TBD')}."
            ),
            "job": job,
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "requires_action": False,
        }

        self.log_completed(
            "generate_job_added_alert",
            resource_id=str(resource_id),
            job_id=str(job.get("job_id", "")),
        )
        return alert

    async def generate_job_removed_alert(
        self,
        resource_id: UUID,
        job: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate an alert when a job is removed with gap-fill suggestions.

        Args:
            resource_id: UUID of the affected resource.
            job: Dict with removed job details.

        Returns:
            Alert dict with gap-fill suggestions.
        """
        self.log_started(
            "generate_job_removed_alert",
            resource_id=str(resource_id),
            job_id=str(job.get("job_id", "")),
        )

        alert = {
            "alert_type": "job_removed",
            "resource_id": str(resource_id),
            "title": "Job Removed",
            "message": (
                f"The {job.get('job_type', 'job')} for "
                f"{job.get('customer_name', 'a customer')} has been "
                f"removed from your schedule."
            ),
            "job": job,
            "gap_fill_suggestions": [
                "Check nearby backlog jobs",
                "Use time for vehicle maintenance",
            ],
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "requires_action": False,
        }

        self.log_completed(
            "generate_job_removed_alert",
            resource_id=str(resource_id),
            job_id=str(job.get("job_id", "")),
        )
        return alert

    async def generate_route_resequenced_alert(
        self,
        resource_id: UUID,
        reason: str,
    ) -> dict[str, Any]:
        """Generate an alert when the route is resequenced.

        Args:
            resource_id: UUID of the affected resource.
            reason: Human-readable reason for the resequence.

        Returns:
            Alert dict with reason and updated navigation prompt.
        """
        self.log_started(
            "generate_route_resequenced_alert",
            resource_id=str(resource_id),
        )

        alert = {
            "alert_type": "route_resequenced",
            "resource_id": str(resource_id),
            "title": "Route Resequenced",
            "message": f"Your route has been resequenced: {reason}",
            "reason": reason,
            "action_prompt": "Tap to view updated navigation.",
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "requires_action": True,
        }

        self.log_completed(
            "generate_route_resequenced_alert",
            resource_id=str(resource_id),
        )
        return alert

    async def generate_equipment_alert(
        self,
        resource_id: UUID,
        job: dict[str, Any],
        equipment: list[str],
    ) -> dict[str, Any]:
        """Generate an alert for special equipment requirements.

        Args:
            resource_id: UUID of the affected resource.
            job: Dict with job details.
            equipment: List of required equipment items.

        Returns:
            Alert dict with equipment list and confirmation prompt.
        """
        self.log_started(
            "generate_equipment_alert",
            resource_id=str(resource_id),
            job_id=str(job.get("job_id", "")),
        )

        alert = {
            "alert_type": "equipment_required",
            "resource_id": str(resource_id),
            "title": "Special Equipment Required",
            "message": (
                f"Job at {job.get('address', 'TBD')} requires: "
                f"{', '.join(equipment)}."
            ),
            "job": job,
            "required_equipment": equipment,
            "action_prompt": "Confirm you have all equipment loaded.",
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "requires_action": True,
        }

        self.log_completed(
            "generate_equipment_alert",
            resource_id=str(resource_id),
            job_id=str(job.get("job_id", "")),
        )
        return alert

    async def generate_access_alert(
        self,
        resource_id: UUID,
        job: dict[str, Any],
        access_info: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate an alert for customer access requirements.

        Args:
            resource_id: UUID of the affected resource.
            job: Dict with job details.
            access_info: Dict with gate_code, instructions, pet_warnings.

        Returns:
            Alert dict with access details.
        """
        self.log_started(
            "generate_access_alert",
            resource_id=str(resource_id),
            job_id=str(job.get("job_id", "")),
        )

        alert = {
            "alert_type": "access_info",
            "resource_id": str(resource_id),
            "title": "Customer Access Information",
            "message": (
                f"Access details for {job.get('customer_name', 'customer')} "
                f"at {job.get('address', 'TBD')}."
            ),
            "job": job,
            "gate_code": access_info.get("gate_code"),
            "instructions": access_info.get("instructions"),
            "pet_warnings": access_info.get("pet_warnings"),
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "requires_action": False,
        }

        self.log_completed(
            "generate_access_alert",
            resource_id=str(resource_id),
            job_id=str(job.get("job_id", "")),
        )
        return alert

    # ------------------------------------------------------------------
    # Resource-facing suggestions (5 types)
    # ------------------------------------------------------------------

    async def generate_prejob_prep_suggestion(
        self,
        resource_id: UUID,
        job: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate a pre-job prep suggestion with customer history.

        Args:
            resource_id: UUID of the resource.
            job: Dict with job details and customer history.

        Returns:
            Suggestion dict with prep recommendations.
        """
        self.log_started(
            "generate_prejob_prep_suggestion",
            resource_id=str(resource_id),
            job_id=str(job.get("job_id", "")),
        )

        suggestion = {
            "suggestion_type": "prejob_prep",
            "resource_id": str(resource_id),
            "title": "Pre-Job Preparation",
            "message": (
                f"Review customer history for "
                f"{job.get('customer_name', 'customer')} before arrival."
            ),
            "job": job,
            "customer_history": job.get("customer_history", []),
            "spare_parts_recommendation": job.get(
                "spare_parts_recommendation",
                [],
            ),
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        }

        self.log_completed(
            "generate_prejob_prep_suggestion",
            resource_id=str(resource_id),
            job_id=str(job.get("job_id", "")),
        )
        return suggestion

    async def generate_upsell_suggestion(
        self,
        resource_id: UUID,
        job: dict[str, Any],
        equipment_info: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate an upsell suggestion based on equipment age.

        Args:
            resource_id: UUID of the resource.
            job: Dict with job details.
            equipment_info: Dict with equipment_name, age_years,
                recommended_upgrade.

        Returns:
            Suggestion dict with upsell opportunity details.
        """
        self.log_started(
            "generate_upsell_suggestion",
            resource_id=str(resource_id),
            job_id=str(job.get("job_id", "")),
        )

        suggestion = {
            "suggestion_type": "upsell_opportunity",
            "resource_id": str(resource_id),
            "title": "Upsell Opportunity",
            "message": (
                f"{equipment_info.get('equipment_name', 'Equipment')} is "
                f"{equipment_info.get('age_years', 'N/A')} years old. "
                f"Consider recommending "
                f"{equipment_info.get('recommended_upgrade', 'an upgrade')}."
            ),
            "job": job,
            "equipment_info": equipment_info,
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        }

        self.log_completed(
            "generate_upsell_suggestion",
            resource_id=str(resource_id),
            job_id=str(job.get("job_id", "")),
        )
        return suggestion

    async def generate_departure_suggestion(
        self,
        resource_id: UUID,
        traffic_info: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate an optimised departure time suggestion.

        Args:
            resource_id: UUID of the resource.
            traffic_info: Dict with recommended_departure, traffic_level,
                estimated_travel_minutes.

        Returns:
            Suggestion dict with departure timing.
        """
        self.log_started(
            "generate_departure_suggestion",
            resource_id=str(resource_id),
        )

        suggestion = {
            "suggestion_type": "departure_time",
            "resource_id": str(resource_id),
            "title": "Optimized Departure Time",
            "message": (
                f"Leave at {traffic_info.get('recommended_departure', 'now')} "
                f"to avoid {traffic_info.get('traffic_level', 'traffic')}. "
                f"Estimated travel: "
                f"{traffic_info.get('estimated_travel_minutes', 'N/A')} min."
            ),
            "traffic_info": traffic_info,
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        }

        self.log_completed(
            "generate_departure_suggestion",
            resource_id=str(resource_id),
        )
        return suggestion

    async def generate_parts_low_suggestion(
        self,
        resource_id: UUID,
        parts_info: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate a low-stock parts suggestion.

        Args:
            resource_id: UUID of the resource.
            parts_info: Dict with part_name, current_quantity,
                reorder_threshold, nearest_supply_house.

        Returns:
            Suggestion dict with restock recommendation.
        """
        self.log_started(
            "generate_parts_low_suggestion",
            resource_id=str(resource_id),
        )

        suggestion = {
            "suggestion_type": "parts_low",
            "resource_id": str(resource_id),
            "title": "Parts Running Low",
            "message": (
                f"{parts_info.get('part_name', 'A part')} is low "
                f"({parts_info.get('current_quantity', 0)} remaining). "
                f"Nearest supply: "
                f"{parts_info.get('nearest_supply_house', 'N/A')}."
            ),
            "parts_info": parts_info,
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        }

        self.log_completed(
            "generate_parts_low_suggestion",
            resource_id=str(resource_id),
        )
        return suggestion

    async def generate_pending_approval_suggestion(
        self,
        resource_id: UUID,
        request_id: UUID,
    ) -> dict[str, Any]:
        """Generate a pending approval status suggestion.

        Args:
            resource_id: UUID of the resource.
            request_id: UUID of the submitted change request.

        Returns:
            Suggestion dict with approval status.
        """
        self.log_started(
            "generate_pending_approval_suggestion",
            resource_id=str(resource_id),
            request_id=str(request_id),
        )

        suggestion = {
            "suggestion_type": "pending_approval",
            "resource_id": str(resource_id),
            "title": "Pending Approval",
            "message": (
                f"Your change request ({request_id}) is pending "
                f"admin approval."
            ),
            "request_id": str(request_id),
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        }

        self.log_completed(
            "generate_pending_approval_suggestion",
            resource_id=str(resource_id),
            request_id=str(request_id),
        )
        return suggestion
