"""
LLM configuration and AI cost tracking for the scheduling engine.

Provides per-function model selection, usage tracking, cost
summaries, and response caching for repeated AI queries.

Validates: Requirements 34.1, 34.2, 34.3
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import TYPE_CHECKING, Any

from grins_platform.log_config import LoggerMixin

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


# ---------------------------------------------------------------------------
# Default model mapping per scheduling function
# ---------------------------------------------------------------------------

_DEFAULT_MODEL_MAP: dict[str, str] = {
    "chat": "gpt-4o-mini",
    "explanations": "gpt-4o-mini",
    "constraint_parsing": "gpt-4o",
    "predictions": "gpt-4o-mini",
}

# Approximate cost per 1K tokens (USD) — updated as pricing changes
_MODEL_COSTS: dict[str, dict[str, float]] = {
    "gpt-4o": {"input": 0.0025, "output": 0.01},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
}


class LLMConfigService(LoggerMixin):
    """LLM configuration and AI cost tracking.

    Manages per-function model selection, tracks token usage and
    costs, provides usage summaries, and caches repeated AI queries.

    Attributes:
        DOMAIN: Logging domain for structured log events.
    """

    DOMAIN = "scheduling"

    def __init__(self, session: AsyncSession) -> None:
        """Initialise the LLM config service.

        Args:
            session: Async database session for persistence.
        """
        super().__init__()
        self._session = session
        self._usage_log: list[dict[str, Any]] = []
        self._response_cache: dict[str, tuple[str, datetime]] = {}

    # ------------------------------------------------------------------
    # Model selection
    # ------------------------------------------------------------------

    async def get_model_for_function(self, function_name: str) -> str:
        """Return the configured LLM model for a scheduling function.

        Args:
            function_name: One of ``chat``, ``explanations``,
                ``constraint_parsing``, ``predictions``.

        Returns:
            Model identifier string (e.g. ``"gpt-4o-mini"``).
        """
        self.log_started("get_model_for_function", function_name=function_name)

        model = _DEFAULT_MODEL_MAP.get(function_name, "gpt-4o-mini")

        self.log_completed(
            "get_model_for_function",
            function_name=function_name,
            model=model,
        )
        return model

    # ------------------------------------------------------------------
    # Usage tracking
    # ------------------------------------------------------------------

    async def track_usage(
        self,
        function_name: str,
        model: str,
        tokens_in: int,
        tokens_out: int,
        cost: float | None = None,
    ) -> None:
        """Track AI usage cost per function.

        Args:
            function_name: Scheduling function that made the call.
            model: Model used (e.g. ``"gpt-4o"``).
            tokens_in: Input token count.
            tokens_out: Output token count.
            cost: Pre-calculated cost in USD. If ``None``, cost is
                estimated from the model's per-token rates.
        """
        self.log_started(
            "track_usage",
            function_name=function_name,
            model=model,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
        )

        if cost is None:
            rates = _MODEL_COSTS.get(model, {"input": 0.0, "output": 0.0})
            cost = (
                (tokens_in / 1000.0) * rates["input"]
                + (tokens_out / 1000.0) * rates["output"]
            )

        entry: dict[str, Any] = {
            "function_name": function_name,
            "model": model,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "cost_usd": round(cost, 6),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._usage_log.append(entry)

        # Stub: persist to DB in production
        self.log_completed(
            "track_usage",
            function_name=function_name,
            cost_usd=entry["cost_usd"],
        )

    # ------------------------------------------------------------------
    # Usage summary
    # ------------------------------------------------------------------

    async def get_usage_summary(
        self,
        start_date: date,
        end_date: date,
    ) -> dict[str, Any]:
        """Get AI usage summary for a date range.

        Args:
            start_date: Start of the reporting period.
            end_date: End of the reporting period.

        Returns:
            Dict with ``total_cost``, ``total_tokens``,
            ``by_function`` breakdown, and ``by_model`` breakdown.
        """
        self.log_started(
            "get_usage_summary",
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
        )

        # Filter in-memory log by date range
        start_iso = start_date.isoformat()
        end_iso = end_date.isoformat()

        filtered = [
            e
            for e in self._usage_log
            if start_iso <= e["timestamp"][:10] <= end_iso
        ]

        total_cost = sum(e["cost_usd"] for e in filtered)
        total_tokens_in = sum(e["tokens_in"] for e in filtered)
        total_tokens_out = sum(e["tokens_out"] for e in filtered)

        by_function: dict[str, dict[str, Any]] = {}
        by_model: dict[str, dict[str, Any]] = {}

        for entry in filtered:
            fn = entry["function_name"]
            if fn not in by_function:
                by_function[fn] = {
                    "calls": 0,
                    "tokens_in": 0,
                    "tokens_out": 0,
                    "cost_usd": 0.0,
                }
            by_function[fn]["calls"] += 1
            by_function[fn]["tokens_in"] += entry["tokens_in"]
            by_function[fn]["tokens_out"] += entry["tokens_out"]
            by_function[fn]["cost_usd"] += entry["cost_usd"]

            mdl = entry["model"]
            if mdl not in by_model:
                by_model[mdl] = {
                    "calls": 0,
                    "tokens_in": 0,
                    "tokens_out": 0,
                    "cost_usd": 0.0,
                }
            by_model[mdl]["calls"] += 1
            by_model[mdl]["tokens_in"] += entry["tokens_in"]
            by_model[mdl]["tokens_out"] += entry["tokens_out"]
            by_model[mdl]["cost_usd"] += entry["cost_usd"]

        summary: dict[str, Any] = {
            "start_date": start_iso,
            "end_date": end_iso,
            "total_calls": len(filtered),
            "total_tokens_in": total_tokens_in,
            "total_tokens_out": total_tokens_out,
            "total_cost_usd": round(total_cost, 6),
            "by_function": by_function,
            "by_model": by_model,
        }

        self.log_completed(
            "get_usage_summary",
            total_calls=len(filtered),
            total_cost_usd=summary["total_cost_usd"],
        )
        return summary

    # ------------------------------------------------------------------
    # Response caching
    # ------------------------------------------------------------------

    async def get_cached_response(self, cache_key: str) -> str | None:
        """Check cache for a repeated AI query.

        Args:
            cache_key: Cache key derived from the query content.

        Returns:
            Cached response string or ``None`` on miss.
        """
        self.log_started("get_cached_response", cache_key=cache_key)

        entry = self._response_cache.get(cache_key)
        if entry is not None:
            response, cached_at = entry
            # Default TTL: 1 hour
            age_seconds = (
                datetime.now(timezone.utc) - cached_at
            ).total_seconds()
            if age_seconds < 3600:
                self.log_completed(
                    "get_cached_response",
                    cache_key=cache_key,
                    hit=True,
                    age_seconds=round(age_seconds),
                )
                return response

            # Expired — remove stale entry
            del self._response_cache[cache_key]

        self.log_completed(
            "get_cached_response",
            cache_key=cache_key,
            hit=False,
        )
        return None

    async def cache_response(
        self,
        cache_key: str,
        response: str,
        ttl: int = 3600,
    ) -> None:
        """Cache an AI response for future reuse.

        Args:
            cache_key: Cache key derived from the query content.
            response: AI response string to cache.
            ttl: Time-to-live in seconds (default 3600). Currently
                used for documentation; expiry is checked on read.
        """
        self.log_started("cache_response", cache_key=cache_key, ttl=ttl)

        self._response_cache[cache_key] = (
            response,
            datetime.now(timezone.utc),
        )

        self.log_completed("cache_response", cache_key=cache_key)
        _ = ttl  # reserved for Redis-backed implementation
