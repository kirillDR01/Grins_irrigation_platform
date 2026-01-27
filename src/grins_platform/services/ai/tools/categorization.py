"""Categorization tools for AI assistant.

Validates: AI Assistant Requirements 5.1-5.14
"""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from grins_platform.log_config import LoggerMixin

# Confidence threshold for auto-categorization
CONFIDENCE_THRESHOLD = 85


class CategorizationTools(LoggerMixin):
    """Tools for job categorization."""

    DOMAIN = "business"

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with database session."""
        super().__init__()
        self.session = session

    async def categorize_job(
        self,
        description: str,
        customer_history: list[dict[str, Any]] | None = None,  # noqa: ARG002
    ) -> dict[str, Any]:
        """Categorize a job request.

        Args:
            description: Job description
            customer_history: Optional customer service history

        Returns:
            Categorization result with confidence score
        """
        self.log_started("categorize_job", description_length=len(description))

        # Analyze description for keywords
        category, confidence, reasoning = self._analyze_description(description)

        # Determine if auto-categorize or needs review
        needs_review = confidence < CONFIDENCE_THRESHOLD

        result = {
            "category": category,
            "confidence": confidence,
            "reasoning": reasoning,
            "needs_review": needs_review,
            "suggested_services": self._suggest_services(description),
        }

        self.log_completed(
            "categorize_job",
            category=category,
            confidence=confidence,
            needs_review=needs_review,
        )
        return result

    def _analyze_description(
        self,
        description: str,
    ) -> tuple[str, int, str]:
        """Analyze job description to determine category.

        Args:
            description: Job description

        Returns:
            Tuple of (category, confidence, reasoning)
        """
        desc_lower = description.lower()

        # Check for urgent keywords
        urgent_keywords = ["emergency", "flooding", "leak", "urgent", "asap"]
        if any(kw in desc_lower for kw in urgent_keywords):
            return (
                "urgent",
                95,
                "Contains urgent/emergency keywords",
            )

        # Check for ready-to-schedule keywords
        ready_keywords = [
            "startup",
            "turn on",
            "winterize",
            "winterization",
            "tune-up",
            "tune up",
            "broken head",
            "sprinkler head",
        ]
        if any(kw in desc_lower for kw in ready_keywords):
            return (
                "ready_to_schedule",
                90,
                "Standard service with known pricing",
            )

        # Check for estimate-required keywords
        estimate_keywords = [
            "install",
            "new system",
            "redesign",
            "major repair",
            "pipe",
            "valve",
            "quote",
            "estimate",
        ]
        if any(kw in desc_lower for kw in estimate_keywords):
            return (
                "requires_estimate",
                88,
                "Complex work requiring site assessment",
            )

        # Default to requires_estimate with lower confidence
        return (
            "requires_estimate",
            60,
            "Unable to determine scope from description",
        )

    def _suggest_services(self, description: str) -> list[str]:
        """Suggest services based on description.

        Args:
            description: Job description

        Returns:
            List of suggested service types
        """
        desc_lower = description.lower()
        services = []

        if "startup" in desc_lower or "turn on" in desc_lower:
            services.append("spring_startup")
        if "winterize" in desc_lower:
            services.append("winterization")
        if "tune" in desc_lower:
            services.append("tune_up")
        if "head" in desc_lower or "sprinkler" in desc_lower:
            services.append("head_replacement")
        if "leak" in desc_lower:
            services.append("leak_repair")
        if "install" in desc_lower:
            services.append("installation")

        return services if services else ["diagnostic"]

    def route_by_confidence(
        self,
        confidence: int,
    ) -> str:
        """Route job based on confidence score.

        Args:
            confidence: Confidence score (0-100)

        Returns:
            Routing decision
        """
        if confidence >= CONFIDENCE_THRESHOLD:
            return "auto_categorize"
        return "human_review"
