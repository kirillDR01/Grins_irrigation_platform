"""Unassigned job analyzer service using AI.

This service explains why specific jobs couldn't be scheduled and provides
actionable suggestions for resolving scheduling conflicts.

Validates: Schedule AI Updates Requirements 3.2-3.7
"""

from datetime import date, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from grins_platform.log_config import LoggerMixin
from grins_platform.schemas.schedule_explanation import (
    UnassignedJobExplanationRequest,
    UnassignedJobExplanationResponse,
)
from grins_platform.services.ai.agent import AIAgentService


class UnassignedJobAnalyzer(LoggerMixin):
    """Service for analyzing unassigned jobs using AI.

    Validates: Requirements 3.2-3.7
    """

    DOMAIN = "business"

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the analyzer.

        Args:
            session: Async database session
        """
        super().__init__()
        self.session = session
        self.ai_service = AIAgentService(session)

    async def explain_unassigned_job(
        self,
        request: UnassignedJobExplanationRequest,
    ) -> UnassignedJobExplanationResponse:
        """Explain why a job couldn't be scheduled with actionable suggestions.

        Args:
            request: Unassigned job explanation request

        Returns:
            Explanation with suggestions and alternative dates

        Validates: Requirements 3.2-3.7
        """
        self.log_started(
            "explain_unassigned_job",
            job_id=str(request.job_id),
            job_type=request.job_type,
            city=request.city,
        )

        # Build context for AI (Requirement 3.2)
        context = self._build_job_context(request)

        # Create prompt for AI
        prompt = self._create_explanation_prompt(context)

        try:
            # Use existing AI service
            explanation_text = await self.ai_service.chat(
                user_id=UUID("00000000-0000-0000-0000-000000000000"),  # System user
                message=prompt,
                context=context,
            )

            # Parse response into structured format
            reason = self._extract_reason(explanation_text, request)
            suggestions = self._extract_suggestions(explanation_text)
            alternative_dates = self._suggest_alternative_dates()

            self.log_completed(
                "explain_unassigned_job",
                suggestions_count=len(suggestions),
                alternatives_count=len(alternative_dates),
            )

            return UnassignedJobExplanationResponse(
                reason=reason,
                suggestions=suggestions,
                alternative_dates=alternative_dates,
            )

        except Exception as e:
            self.log_failed("explain_unassigned_job", error=e)
            # Fallback to basic constraint violation (Requirement 3.8)
            return self._create_fallback_response(request)

    def _build_job_context(
        self,
        request: UnassignedJobExplanationRequest,
    ) -> dict[str, Any]:
        """Build context for AI without PII.

        Args:
            request: Unassigned job explanation request

        Returns:
            Context dictionary without PII
        """
        return {
            "job_type": request.job_type,
            "city": request.city,
            "estimated_duration_minutes": request.estimated_duration_minutes,
            "priority": request.priority,
            "requires_equipment": request.requires_equipment,
            "constraint_violations": request.constraint_violations,
        }

    def _create_explanation_prompt(
        self,
        context: dict[str, Any],
    ) -> str:
        """Create prompt for unassigned job explanation.

        Validates: Requirements 3.3-3.5

        Args:
            context: Job context without PII

        Returns:
            Prompt for AI
        """
        job_type = context["job_type"]
        city = context["city"]
        duration = context["estimated_duration_minutes"]
        priority = context["priority"]
        equipment = context["requires_equipment"]
        violations = context["constraint_violations"]

        violations_text = (
            chr(10).join(f"- {v}" for v in violations)
            if violations
            else "- No specific violations recorded"
        )

        return f"""Explain why this irrigation job couldn't be scheduled:

Job Details:
- Type: {job_type}
- City: {city}
- Duration: {duration} minutes
- Priority: {priority}
- Required Equipment: {", ".join(equipment) if equipment else "None"}

Constraint Violations:
{violations_text}

Provide:
1. Clear reason why the job couldn't be scheduled (Requirement 3.3)
2. Specific actionable suggestions to resolve (Requirement 3.4)
3. Alternative approaches (e.g., move jobs, different day) (Requirement 3.5)

Keep the explanation concise and actionable.
"""

    def _extract_reason(
        self,
        explanation: str,
        request: UnassignedJobExplanationRequest,
    ) -> str:
        """Extract the main reason from explanation text.

        Args:
            explanation: Full explanation text
            request: Original request for fallback

        Returns:
            Main reason why job couldn't be scheduled
        """
        # Take first paragraph as the reason
        paragraphs = [p.strip() for p in explanation.split("\n\n") if p.strip()]
        if paragraphs:
            return paragraphs[0]

        # Fallback to constraint violations
        if request.constraint_violations:
            return request.constraint_violations[0]

        return "Unable to schedule due to capacity or constraint conflicts."

    def _extract_suggestions(self, explanation: str) -> list[str]:
        """Extract actionable suggestions from explanation text.

        Args:
            explanation: Full explanation text

        Returns:
            List of actionable suggestions
        """
        suggestions = []

        # Look for numbered lists or bullet points
        lines = explanation.split("\n")
        for original_line in lines:
            line = original_line.strip()
            # Match numbered items (1., 2., etc.) or bullet points (-, *, •)
            if line and (line[0].isdigit() or line.startswith(("-", "*", "•"))):
                # Remove numbering/bullets
                cleaned = line.lstrip("0123456789.-*• ").strip()
                if len(cleaned) > 10:  # Substantial suggestion
                    suggestions.append(cleaned)

        # If no structured suggestions found, take sentences with action words
        if not suggestions:
            action_words = ["move", "schedule", "assign", "try", "consider"]
            sentences = [s.strip() for s in explanation.split(".") if s.strip()]
            suggestions.extend(
                sentence + "."
                for sentence in sentences
                if any(word in sentence.lower() for word in action_words)
            )

        return suggestions[:5]  # Limit to 5 suggestions

    def _suggest_alternative_dates(self) -> list[date]:
        """Suggest alternative dates for scheduling.

        Validates: Requirement 3.5

        Returns:
            List of suggested alternative dates (next 3 business days)
        """
        today = date.today()
        alternatives: list[date] = []

        # Suggest next 3 business days
        current = today + timedelta(days=1)
        while len(alternatives) < 3:
            # Skip weekends (5=Saturday, 6=Sunday)
            if current.weekday() < 5:
                alternatives.append(current)
            current += timedelta(days=1)

        return alternatives

    def _create_fallback_response(
        self,
        request: UnassignedJobExplanationRequest,
    ) -> UnassignedJobExplanationResponse:
        """Create fallback response when AI is unavailable.

        Validates: Requirement 3.8

        Args:
            request: Original request

        Returns:
            Basic explanation from constraint violations
        """
        # Use constraint violations as reason
        if request.constraint_violations:
            reason = request.constraint_violations[0]
            suggestions = [f"Review {v}" for v in request.constraint_violations[1:3]]
        else:
            reason = "Unable to schedule due to capacity or constraint conflicts."
            suggestions = [
                "Try scheduling on a different day",
                "Check staff availability and capacity",
            ]

        return UnassignedJobExplanationResponse(
            reason=reason,
            suggestions=suggestions,
            alternative_dates=self._suggest_alternative_dates(),
        )
