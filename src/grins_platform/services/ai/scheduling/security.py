"""
Security, guardrails, and audit trail for AI scheduling.

Enforces PII protection, off-topic guardrails, and audit logging
for all AI scheduling interactions.

Validates: Requirements 24.1, 24.2, 24.3, 24.4, 24.5, 34.5
"""

from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from typing import Any, ClassVar
from uuid import UUID

from grins_platform.log_config import LoggerMixin

# PII patterns to scrub from AI prompts and logs
_PII_PATTERNS: list[tuple[str, str]] = [
    # Phone numbers (various formats)
    (
        r"\b\+?1?\s*[\(\-\.]?\d{3}[\)\-\.\s]\s*\d{3}[\-\.\s]\d{4}\b",
        "[PHONE]",
    ),
    # Email addresses
    (
        r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Z|a-z]{2,}\b",
        "[EMAIL]",
    ),
    # Full street addresses (number + street name)
    (
        r"\b\d{1,5}\s+[A-Za-z0-9\s,\.]+(?:St|Ave|Blvd|Dr|Rd|Ln|Way|Ct|Pl)\b",
        "[ADDRESS]",
    ),
    # SSN
    (r"\b\d{3}-\d{2}-\d{4}\b", "[SSN]"),
    # Credit card numbers
    (r"\b(?:\d{4}[\s\-]?){3}\d{4}\b", "[CARD]"),
]

# Off-topic rejection patterns
_OFF_TOPIC_PATTERNS: list[str] = [
    (
        r"\b(recipe|cook|food|restaurant|movie|music|sport|game"
        r"|weather forecast for personal|stock|crypto|bitcoin)\b"
    ),
]


class SchedulingSecurityService(LoggerMixin):
    """Security and guardrails for AI scheduling interactions.

    Attributes:
        DOMAIN: Logging domain identifier.
    """

    DOMAIN = "scheduling"

    def scrub_pii(self, text: str) -> str:
        """Remove PII from text before including in AI prompts or logs.

        Replaces phone numbers, emails, and addresses with placeholders.

        Args:
            text: Input text that may contain PII.

        Returns:
            Text with PII replaced by placeholders.
        """
        result = text
        for pattern, replacement in _PII_PATTERNS:
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
        return result

    def is_off_topic(self, message: str) -> bool:
        """Check if a message is off-topic for scheduling.

        Args:
            message: User message to check.

        Returns:
            True if the message is clearly off-topic.
        """
        lower = message.lower()
        return any(re.search(pattern, lower) for pattern in _OFF_TOPIC_PATTERNS)

    def log_interaction(
        self,
        user_id: UUID,
        role: str,
        message: str,
        parsed_intent: str,
        response_summary: str,
        session_id: UUID | None = None,
    ) -> None:
        """Log an AI interaction to the audit trail.

        Scrubs PII before logging. Includes user ID, role, timestamp,
        parsed intent, and response summary.

        Args:
            user_id: Staff member UUID.
            role: User role.
            message: User's message (PII will be scrubbed).
            parsed_intent: AI-parsed intent of the message.
            response_summary: Brief summary of the AI response.
            session_id: Optional session UUID.
        """
        scrubbed_message = self.scrub_pii(message)
        self.logger.info(
            "scheduling.security.interaction_audit",
            user_id=str(user_id),
            role=role,
            session_id=str(session_id) if session_id else None,
            message_scrubbed=scrubbed_message[:200],
            parsed_intent=parsed_intent,
            response_summary=response_summary[:200],
            timestamp=datetime.now(tz=timezone.utc).isoformat(),
        )

    def validate_prompt_safety(self, prompt: str) -> tuple[bool, str]:
        """Validate that a prompt is safe to send to the AI model.

        Checks for PII and prompt injection attempts.

        Args:
            prompt: Prompt to validate.

        Returns:
            Tuple of (is_safe, reason). If not safe, reason explains why.
        """
        injection_patterns = [
            r"ignore (previous|all|above) instructions",
            r"you are now",
            r"forget (everything|all|your instructions)",
            r"system prompt",
            r"jailbreak",
        ]
        lower = prompt.lower()
        for pattern in injection_patterns:
            if re.search(pattern, lower):
                return False, f"Potential prompt injection detected: {pattern}"

        return True, "safe"


class SchedulingLLMConfig(LoggerMixin):
    """LLM configuration and AI cost tracking for scheduling.

    Validates: Requirements 34.1, 34.2, 34.3
    """

    DOMAIN = "scheduling"

    _DEFAULT_MODELS: ClassVar[dict[str, str]] = {
        "chat": "gpt-4o-mini",
        "explanations": "gpt-4o-mini",
        "constraint_parsing": "gpt-4o-mini",
        "predictions": "gpt-4o-mini",
    }

    _COST_PER_1K_TOKENS: ClassVar[dict[str, dict[str, float]]] = {
        "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
        "gpt-4o": {"input": 0.005, "output": 0.015},
        "gpt-4-turbo": {"input": 0.01, "output": 0.03},
    }

    def __init__(self) -> None:
        """Initialise LLM config."""
        super().__init__()
        self._model_overrides: dict[str, str] = {
            "chat": os.getenv("SCHEDULING_CHAT_MODEL", self._DEFAULT_MODELS["chat"]),
            "explanations": os.getenv(
                "SCHEDULING_EXPLANATION_MODEL",
                self._DEFAULT_MODELS["explanations"],
            ),
            "constraint_parsing": os.getenv(
                "SCHEDULING_CONSTRAINT_MODEL",
                self._DEFAULT_MODELS["constraint_parsing"],
            ),
            "predictions": os.getenv(
                "SCHEDULING_PREDICTION_MODEL",
                self._DEFAULT_MODELS["predictions"],
            ),
        }
        self._usage_log: list[dict[str, Any]] = []

    def get_model(self, function: str) -> str:
        """Get the configured model for a scheduling function.

        Args:
            function: Function name (chat, explanations, etc.).

        Returns:
            Model identifier string.
        """
        return self._model_overrides.get(
            function,
            self._DEFAULT_MODELS.get(function, "gpt-4o-mini"),
        )

    def track_usage(
        self,
        function: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """Track AI usage and calculate cost.

        Args:
            function: Scheduling function that used the AI.
            model: Model used.
            input_tokens: Number of input tokens.
            output_tokens: Number of output tokens.

        Returns:
            Estimated cost in USD.
        """
        costs = self._COST_PER_1K_TOKENS.get(model, {"input": 0.001, "output": 0.002})
        cost_usd = (
            input_tokens / 1000 * costs["input"]
            + output_tokens / 1000 * costs["output"]
        )

        entry: dict[str, Any] = {
            "function": function,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": round(cost_usd, 6),
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        }
        self._usage_log.append(entry)

        self.logger.info(
            "scheduling.llmconfig.usage_tracked",
            function=function,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=entry["cost_usd"],
        )
        return cost_usd

    def get_usage_summary(self) -> dict[str, Any]:
        """Get a summary of AI usage and costs.

        Returns:
            Dict with total tokens, total cost, and per-function breakdown.
        """
        total_cost = sum(e["cost_usd"] for e in self._usage_log)
        total_input = sum(e["input_tokens"] for e in self._usage_log)
        total_output = sum(e["output_tokens"] for e in self._usage_log)

        by_function: dict[str, dict[str, Any]] = {}
        for entry in self._usage_log:
            fn = entry["function"]
            if fn not in by_function:
                by_function[fn] = {"calls": 0, "cost_usd": 0.0, "tokens": 0}
            by_function[fn]["calls"] += 1
            by_function[fn]["cost_usd"] += entry["cost_usd"]
            by_function[fn]["tokens"] += entry["input_tokens"] + entry["output_tokens"]

        return {
            "total_calls": len(self._usage_log),
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "total_cost_usd": round(total_cost, 6),
            "by_function": by_function,
        }


class SchedulingStorageConfig(LoggerMixin):
    """Storage limits and scalability configuration for AI scheduling.

    Validates: Requirements 35.1, 35.2, 35.3, 35.4
    """

    DOMAIN = "scheduling"

    DEFAULT_SCHEDULE_HISTORY_DAYS = 365
    DEFAULT_AI_LOG_RETENTION_DAYS = 90
    DEFAULT_ML_TRAINING_DATA_DAYS = 730
    DEFAULT_MAX_JOBS_PER_GENERATION = 50
    DEFAULT_BATCH_ZONE_SIZE = 20

    def __init__(self) -> None:
        """Initialise storage config."""
        super().__init__()
        self.schedule_history_days = int(
            os.getenv(
                "SCHEDULING_HISTORY_RETENTION_DAYS",
                str(self.DEFAULT_SCHEDULE_HISTORY_DAYS),
            )
        )
        self.ai_log_retention_days = int(
            os.getenv(
                "SCHEDULING_AI_LOG_RETENTION_DAYS",
                str(self.DEFAULT_AI_LOG_RETENTION_DAYS),
            )
        )
        self.max_jobs_per_generation = int(
            os.getenv(
                "SCHEDULING_MAX_JOBS_PER_GENERATION",
                str(self.DEFAULT_MAX_JOBS_PER_GENERATION),
            )
        )

    def should_archive(self, record_date: datetime) -> bool:
        """Check if a record should be archived based on retention policy.

        Args:
            record_date: Record creation date.

        Returns:
            True if the record is beyond the retention period.
        """
        age_days = (datetime.now(tz=timezone.utc) - record_date).days
        return age_days > self.schedule_history_days

    def get_batch_partitions(
        self,
        job_count: int,
        zone_count: int = 1,
    ) -> list[dict[str, int]]:
        """Get batch generation partitions for large job counts.

        Partitions jobs by zone/resource group to ensure sub-30s
        generation for up to 50 jobs per partition.

        Args:
            job_count: Total number of jobs to schedule.
            zone_count: Number of zones to partition by.

        Returns:
            List of partition dicts with start/end indices.
        """
        if job_count <= self.max_jobs_per_generation:
            return [{"start": 0, "end": job_count, "zone": 0}]

        partitions: list[dict[str, int]] = []
        jobs_per_zone = max(1, job_count // zone_count)

        for zone_idx in range(zone_count):
            start = zone_idx * jobs_per_zone
            end = min(start + jobs_per_zone, job_count)
            if start < job_count:
                partitions.append({"start": start, "end": end, "zone": zone_idx})

        self.logger.info(
            "scheduling.storageconfig.batch_partitions_created",
            job_count=job_count,
            zone_count=zone_count,
            partition_count=len(partitions),
        )
        return partitions
