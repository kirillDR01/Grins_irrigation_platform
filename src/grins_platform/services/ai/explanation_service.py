"""Schedule explanation service using AI.

This service generates natural language explanations for scheduling decisions,
helping users understand why jobs were assigned the way they were.

Validates: Schedule AI Updates Requirements 2.2-2.8
"""

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from grins_platform.log_config import LoggerMixin
from grins_platform.schemas.schedule_explanation import (
    ScheduleExplanationRequest,
    ScheduleExplanationResponse,
)
from grins_platform.services.ai.agent import AIAgentService


class ScheduleExplanationService(LoggerMixin):
    """Service for generating schedule explanations using AI.

    Validates: Requirements 2.2-2.8
    """

    DOMAIN = "business"

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the service.

        Args:
            session: Async database session
        """
        super().__init__()
        self.session = session
        self.ai_service = AIAgentService(session)

    async def explain_schedule(
        self,
        request: ScheduleExplanationRequest,
    ) -> ScheduleExplanationResponse:
        """Generate natural language explanation of a schedule.

        Args:
            request: Schedule explanation request with staff assignments

        Returns:
            Natural language explanation with highlights

        Validates: Requirements 2.2-2.8
        """
        self.log_started(
            "explain_schedule",
            schedule_date=str(request.schedule_date),
            staff_count=len(request.staff_assignments),
            unassigned_count=request.unassigned_job_count,
        )

        # Build context without PII (Requirement 2.7)
        context = self._build_schedule_context(request)

        # Create prompt for AI
        prompt = self._create_explanation_prompt(context)

        try:
            # Use existing AI service (Requirement 2.2)
            explanation_text = await self.ai_service.chat(
                user_id=UUID("00000000-0000-0000-0000-000000000000"),  # System user
                message=prompt,
                context=context,
            )

            # Parse response into structured format
            highlights = self._extract_highlights(explanation_text)

            self.log_completed(
                "explain_schedule",
                explanation_length=len(explanation_text),
                highlights_count=len(highlights),
            )

            return ScheduleExplanationResponse(
                explanation=explanation_text,
                highlights=highlights,
            )

        except Exception as e:
            # Graceful degradation: provide fallback explanation (Requirement 2.9)
            self.log_rejected(
                "explain_schedule",
                reason="ai_unavailable",
                error=str(e),
            )
            return self._generate_fallback_explanation(request)

    def _build_schedule_context(
        self,
        request: ScheduleExplanationRequest,
    ) -> dict[str, Any]:
        """Build context for AI without PII.

        Validates: Requirement 2.7 (no full addresses, phone numbers)

        Args:
            request: Schedule explanation request

        Returns:
            Context dictionary without PII
        """
        staff_summaries = [
            {
                "staff_name": assignment.staff_name,
                "job_count": assignment.job_count,
                "total_minutes": assignment.total_minutes,
                "cities": assignment.cities,
                "job_types": assignment.job_types,
            }
            for assignment in request.staff_assignments
        ]

        return {
            "schedule_date": str(request.schedule_date),
            "staff_assignments": staff_summaries,
            "unassigned_job_count": request.unassigned_job_count,
        }

    def _create_explanation_prompt(
        self,
        context: dict[str, Any],
    ) -> str:
        """Create prompt for schedule explanation.

        Validates: Requirements 2.3-2.6

        Args:
            context: Schedule context without PII

        Returns:
            Prompt for AI
        """
        staff_assignments: list[dict[str, Any]] = context["staff_assignments"]

        schedule_date = context["schedule_date"]
        prompt = f"""Explain this irrigation service schedule for \
{schedule_date}.

Staff Assignments:
"""
        for assignment in staff_assignments:
            cities_str = ", ".join(assignment["cities"])
            job_types_str = ", ".join(assignment["job_types"])
            staff_name = assignment["staff_name"]
            job_count = assignment["job_count"]
            total_minutes = assignment["total_minutes"]
            prompt += f"""
- {staff_name}: {job_count} jobs, {total_minutes} minutes
  Cities: {cities_str}
  Job types: {job_types_str}
"""

        unassigned_count: int = context["unassigned_job_count"]
        if unassigned_count > 0:
            prompt += f"\nUnassigned jobs: {unassigned_count}\n"

        prompt += """
Provide a clear explanation covering:
1. Staff assignments and geographic grouping rationale (Requirement 2.3)
2. Time slot decisions and priority job handling (Requirement 2.4)
3. Equipment-based assignment decisions if relevant (Requirement 2.5)
4. Route optimization choices (e.g., city grouping) (Requirement 2.6)

Keep the explanation concise (2-3 paragraphs) and actionable.
"""
        return prompt

    def _extract_highlights(self, explanation: str) -> list[str]:
        """Extract key highlights from explanation text.

        Args:
            explanation: Full explanation text

        Returns:
            List of key highlights (3-5 bullet points)
        """
        # Split by periods and take first 3-5 substantial sentences
        sentences = [s.strip() for s in explanation.split(".") if len(s.strip()) > 20]

        # Take up to 5 highlights, filter out meta-text
        return [
            sentence + "."
            for sentence in sentences[:5]
            if sentence and not sentence.startswith("Explain")
        ]

    def _generate_fallback_explanation(
        self,
        request: ScheduleExplanationRequest,
    ) -> ScheduleExplanationResponse:
        """Generate basic fallback explanation when AI unavailable.

        Validates: Requirement 2.9 (graceful degradation)

        Args:
            request: Schedule explanation request

        Returns:
            Basic explanation without AI
        """
        staff_count = len(request.staff_assignments)
        unassigned = request.unassigned_job_count

        # Build basic explanation from data
        explanation_parts = [
            f"Schedule generated for {request.schedule_date}.",
            f"Assigned {staff_count} staff member(s) to jobs.",
        ]

        if unassigned > 0:
            explanation_parts.append(
                f"{unassigned} job(s) could not be assigned due to constraints.",
            )

        # Add staff summaries
        for assignment in request.staff_assignments:
            cities = ", ".join(assignment.cities)
            explanation_parts.append(
                f"{assignment.staff_name}: {assignment.job_count} jobs "
                f"in {cities} ({assignment.total_minutes} minutes).",
            )

        explanation = " ".join(explanation_parts)

        # Basic highlights
        highlights = [
            f"{staff_count} staff assigned",
            f"{unassigned} jobs unassigned" if unassigned > 0 else "All jobs assigned",
        ]

        return ScheduleExplanationResponse(
            explanation=explanation + " (AI explanation unavailable)",
            highlights=highlights,
        )
