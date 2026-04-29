"""
Resource alert generation for mobile view.

Generates resource-facing alerts (schedule changes, pre-job requirements)
and suggestions (pre-job prep, upsell, departure timing, parts, approvals).

Validates: Requirements 16.1-16.5, 17.1-17.5
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from grins_platform.log_config import LoggerMixin
from grins_platform.schemas.ai_scheduling import AlertCandidate, ResolutionOption


class ResourceAlertGenerator(LoggerMixin):
    """Generates resource-facing alerts and suggestions for mobile view.

    Attributes:
        DOMAIN: Logging domain identifier.
    """

    DOMAIN = "scheduling"

    # ------------------------------------------------------------------
    # Alert types (schedule changes, pre-job requirements)
    # ------------------------------------------------------------------

    def schedule_change_job_added(
        self,
        job_id: UUID,
        staff_id: UUID,
        job_details: dict[str, Any],
    ) -> AlertCandidate:
        """Generate a 'Job Added' schedule change alert.

        Validates: Requirement 16.1
        """
        return AlertCandidate(
            alert_type="schedule_change_job_added",
            severity="critical",
            title="Schedule Change — Job Added",
            description=(
                f"A new job has been added to your schedule: "
                f"{job_details.get('job_type', 'Service')} at "
                f"{job_details.get('address', 'address on file')}."
            ),
            affected_job_ids=[job_id],
            affected_staff_ids=[staff_id],
            criteria_triggered=[13],
            resolution_options=[
                ResolutionOption(
                    action="view_job_details",
                    label="View job details",
                    description="See full job information and customer notes",
                ),
                ResolutionOption(
                    action="launch_navigation",
                    label="Navigate to job",
                    description="Open navigation to job site",
                ),
            ],
        )

    def schedule_change_job_removed(
        self,
        job_id: UUID,
        staff_id: UUID,
        gap_fill_suggestions: list[dict[str, Any]] | None = None,  # noqa: ARG002
    ) -> AlertCandidate:
        """Generate a 'Job Removed' schedule change alert with gap-fill suggestions.

        Validates: Requirement 16.2
        """
        return AlertCandidate(
            alert_type="schedule_change_job_removed",
            severity="critical",
            title="Schedule Change — Job Removed",
            description=(
                "A job has been removed from your schedule. "
                "You may have a gap — backlog jobs are available to fill it."
            ),
            affected_job_ids=[job_id],
            affected_staff_ids=[staff_id],
            criteria_triggered=[16, 20],
            resolution_options=[
                ResolutionOption(
                    action="request_backlog_fill",
                    label="Request backlog job",
                    description="Ask admin to assign a nearby backlog job",
                ),
            ],
        )

    def route_resequenced(
        self,
        staff_id: UUID,
        reason: str,
        new_sequence: list[dict[str, Any]] | None = None,  # noqa: ARG002
    ) -> AlertCandidate:
        """Generate a 'Route Resequenced' alert with updated navigation.

        Validates: Requirement 16.3
        """
        return AlertCandidate(
            alert_type="route_resequenced",
            severity="critical",
            title="Route Resequenced",
            description=(
                f"Your route has been resequenced: {reason}. "
                "Updated navigation is available."
            ),
            affected_staff_ids=[staff_id],
            criteria_triggered=[1, 2],
            resolution_options=[
                ResolutionOption(
                    action="view_updated_route",
                    label="View updated route",
                    description="See the new job sequence with ETAs",
                ),
                ResolutionOption(
                    action="launch_navigation",
                    label="Start navigation",
                    description="Open navigation for first job in new sequence",
                ),
            ],
        )

    def prejob_special_equipment(
        self,
        job_id: UUID,
        staff_id: UUID,
        equipment_list: list[str],
    ) -> AlertCandidate:
        """Generate a 'Special Equipment Required' pre-job alert.

        Validates: Requirement 16.4
        """
        return AlertCandidate(
            alert_type="prejob_special_equipment",
            severity="critical",
            title="Pre-Job Requirement — Special Equipment",
            description=(
                f"This job requires special equipment: "
                f"{', '.join(equipment_list)}. "
                "Please confirm you have these items on your truck."
            ),
            affected_job_ids=[job_id],
            affected_staff_ids=[staff_id],
            criteria_triggered=[7],
            resolution_options=[
                ResolutionOption(
                    action="confirm_equipment",
                    label="Confirm equipment on truck",
                    description="Mark equipment as confirmed",
                ),
                ResolutionOption(
                    action="report_missing_equipment",
                    label="Report missing equipment",
                    description="Alert admin that equipment is not available",
                ),
            ],
        )

    def prejob_customer_access(
        self,
        job_id: UUID,
        staff_id: UUID,
        gate_code: str | None,
        instructions: str | None,
        has_pet_warning: bool = False,
    ) -> AlertCandidate:
        """Generate a 'Customer Access' pre-job alert.

        Validates: Requirement 16.5
        """
        desc_parts = ["Customer access information for this job:"]
        if gate_code:
            desc_parts.append(f"Gate code: {gate_code}")
        if instructions:
            desc_parts.append(f"Instructions: {instructions}")
        if has_pet_warning:
            desc_parts.append("⚠️ Pet warning: secure pets before entering.")

        return AlertCandidate(
            alert_type="prejob_customer_access",
            severity="critical",
            title="Pre-Job Requirement — Customer Access",
            description=" ".join(desc_parts),
            affected_job_ids=[job_id],
            affected_staff_ids=[staff_id],
            criteria_triggered=[5],
            resolution_options=[
                ResolutionOption(
                    action="acknowledge_access",
                    label="Acknowledge access info",
                    description="Confirm you have reviewed access requirements",
                ),
            ],
        )

    # ------------------------------------------------------------------
    # Suggestion types
    # ------------------------------------------------------------------

    def prejob_prep_suggestion(
        self,
        job_id: UUID,
        staff_id: UUID,
        customer_history_notes: str | None = None,
        spare_parts_recommendation: list[str] | None = None,
    ) -> AlertCandidate:
        """Generate a 'Pre-Job Prep' suggestion.

        Validates: Requirement 17.1
        """
        desc = "Pre-job preparation suggestion based on customer history."
        if customer_history_notes:
            desc += f" Notes: {customer_history_notes}"
        if spare_parts_recommendation:
            desc += (
                f" Recommended spare parts: {', '.join(spare_parts_recommendation)}."
            )

        return AlertCandidate(
            alert_type="prejob_prep",
            severity="suggestion",
            title="Pre-Job Prep",
            description=desc,
            affected_job_ids=[job_id],
            affected_staff_ids=[staff_id],
            criteria_triggered=[15, 27],
            resolution_options=[
                ResolutionOption(
                    action="view_customer_history",
                    label="View customer history",
                    description="See full service history for this customer",
                ),
            ],
        )

    def upsell_opportunity(
        self,
        job_id: UUID,
        staff_id: UUID,
        equipment_name: str,
        age_years: float,
        recommended_upgrade: str,
    ) -> AlertCandidate:
        """Generate an 'Upsell Opportunity' suggestion.

        Validates: Requirement 17.2
        """
        return AlertCandidate(
            alert_type="upsell_opportunity",
            severity="suggestion",
            title="Upsell Opportunity",
            description=(
                f"Customer's {equipment_name} is {age_years:.1f} years old. "
                f"Consider recommending: {recommended_upgrade}."
            ),
            affected_job_ids=[job_id],
            affected_staff_ids=[staff_id],
            criteria_triggered=[22, 14],
            resolution_options=[
                ResolutionOption(
                    action="initiate_quote",
                    label="Initiate upgrade quote",
                    description="Start an upgrade quote for the customer",
                ),
            ],
        )

    def optimized_departure_time(
        self,
        staff_id: UUID,
        recommended_departure: str,
        traffic_reason: str,
    ) -> AlertCandidate:
        """Generate an 'Optimized Departure Time' suggestion.

        Validates: Requirement 17.3
        """
        return AlertCandidate(
            alert_type="optimized_departure",
            severity="suggestion",
            title="Optimized Departure Time",
            description=(
                f"Recommended departure: {recommended_departure}. "
                f"Reason: {traffic_reason}"
            ),
            affected_staff_ids=[staff_id],
            criteria_triggered=[4, 1],
            resolution_options=[
                ResolutionOption(
                    action="update_departure",
                    label="Update departure time",
                    description="Set your planned departure to the recommended time",
                ),
            ],
        )

    def parts_running_low(
        self,
        staff_id: UUID,
        part_name: str,
        current_quantity: int,
        nearest_supply_house: str | None = None,
    ) -> AlertCandidate:
        """Generate a 'Parts Running Low' suggestion.

        Validates: Requirement 17.4
        """
        desc = (
            f"Your truck is running low on {part_name} "
            f"(current: {current_quantity} units)."
        )
        if nearest_supply_house:
            desc += f" Nearest supply house: {nearest_supply_house}."

        return AlertCandidate(
            alert_type="parts_low",
            severity="suggestion",
            title="Parts Running Low",
            description=desc,
            affected_staff_ids=[staff_id],
            criteria_triggered=[7],
            resolution_options=[
                ResolutionOption(
                    action="navigate_supply_house",
                    label="Navigate to supply house",
                    description="Get directions to nearest supply house",
                ),
            ],
        )

    def pending_approval(
        self,
        staff_id: UUID,
        change_request_id: UUID,  # noqa: ARG002
        request_type: str,
    ) -> AlertCandidate:
        """Generate a 'Pending Approval' suggestion for submitted ChangeRequests.

        Validates: Requirement 17.5
        """
        return AlertCandidate(
            alert_type="pending_approval",
            severity="suggestion",
            title="Pending Approval",
            description=(
                f"Your {request_type.replace('_', ' ')} request is pending"
                " admin approval. "
                "You'll be notified when a decision is made."
            ),
            affected_staff_ids=[staff_id],
            criteria_triggered=[],
            resolution_options=[
                ResolutionOption(
                    action="view_request_status",
                    label="View request status",
                    description="See the current status of your change request",
                ),
            ],
        )
