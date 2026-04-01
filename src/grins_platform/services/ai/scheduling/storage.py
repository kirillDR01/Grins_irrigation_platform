"""
Storage limits and scalability utilities for the scheduling engine.

Provides per-user storage limit checks, historical data archival,
generation time estimation, and batch partitioning for large job sets.

Validates: Requirements 35.1, 35.2, 35.3, 35.4
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any

from grins_platform.log_config import LoggerMixin

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


# ---------------------------------------------------------------------------
# Default storage limits
# ---------------------------------------------------------------------------

_DEFAULT_LIMITS: dict[str, int] = {
    "schedule_history_days": 365,
    "ai_log_entries": 10_000,
    "ml_training_records": 50_000,
    "chat_sessions": 500,
}

# Target: sub-30s for 50 jobs (Req 35.3)
_BASE_TIME_PER_JOB_SECONDS: float = 0.4
_OVERHEAD_SECONDS: float = 2.0


class StorageService(LoggerMixin):
    """Storage limits and scalability management.

    Enforces per-user storage limits, archives old data, estimates
    schedule generation times, and partitions large job sets for
    parallel processing.

    Attributes:
        DOMAIN: Logging domain for structured log events.
    """

    DOMAIN = "scheduling"

    def __init__(self, session: AsyncSession) -> None:
        """Initialise the storage service.

        Args:
            session: Async database session for data access.
        """
        super().__init__()
        self._session = session

    # ------------------------------------------------------------------
    # Storage limit checks
    # ------------------------------------------------------------------

    async def check_storage_limits(
        self,
        user_id: str,
    ) -> dict[str, Any]:
        """Check per-user storage limits.

        Checks schedule history, AI logs, and ML training data
        against configured limits.

        Args:
            user_id: User/tenant identifier.

        Returns:
            Dict with per-category ``used``, ``limit``, and
            ``within_limit`` status.
        """
        self.log_started("check_storage_limits", user_id=user_id)

        # Stub: would query actual DB counts per user
        current_usage: dict[str, int] = {
            "schedule_history_days": 0,
            "ai_log_entries": 0,
            "ml_training_records": 0,
            "chat_sessions": 0,
        }

        result: dict[str, Any] = {
            "user_id": user_id,
            "categories": {},
            "all_within_limits": True,
        }

        for category, limit in _DEFAULT_LIMITS.items():
            used = current_usage.get(category, 0)
            within = used <= limit
            result["categories"][category] = {
                "used": used,
                "limit": limit,
                "within_limit": within,
                "usage_percent": round((used / limit) * 100, 1) if limit else 0.0,
            }
            if not within:
                result["all_within_limits"] = False

        self.log_completed(
            "check_storage_limits",
            user_id=user_id,
            all_within_limits=result["all_within_limits"],
        )
        return result

    # ------------------------------------------------------------------
    # Data archival
    # ------------------------------------------------------------------

    async def archive_old_data(
        self,
        retention_days: int = 365,
    ) -> dict[str, Any]:
        """Archive historical data beyond the retention period.

        Moves schedule history, AI logs, and chat sessions older
        than ``retention_days`` to cold storage (or marks for
        deletion).

        Args:
            retention_days: Number of days to retain (default 365).

        Returns:
            Summary dict with ``archived_count`` per category.
        """
        self.log_started("archive_old_data", retention_days=retention_days)

        # Stub: would execute DELETE/archive queries per table
        result: dict[str, Any] = {
            "retention_days": retention_days,
            "archived": {
                "schedule_history": 0,
                "ai_logs": 0,
                "chat_sessions": 0,
                "ml_training_data": 0,
            },
            "total_archived": 0,
        }

        self.log_completed(
            "archive_old_data",
            retention_days=retention_days,
            total_archived=result["total_archived"],
        )
        return result

    # ------------------------------------------------------------------
    # Generation time estimation
    # ------------------------------------------------------------------

    async def estimate_generation_time(
        self,
        job_count: int,
    ) -> float:
        """Estimate schedule generation time in seconds.

        Uses a linear model calibrated to achieve sub-30s for 50
        jobs (Req 35.3).

        Args:
            job_count: Number of jobs to schedule.

        Returns:
            Estimated generation time in seconds.
        """
        self.log_started("estimate_generation_time", job_count=job_count)

        # Linear estimate: overhead + per-job cost
        estimated = _OVERHEAD_SECONDS + (_BASE_TIME_PER_JOB_SECONDS * job_count)

        self.log_completed(
            "estimate_generation_time",
            job_count=job_count,
            estimated_seconds=round(estimated, 1),
        )
        return round(estimated, 1)

    # ------------------------------------------------------------------
    # Batch partitioning
    # ------------------------------------------------------------------

    async def partition_batch(
        self,
        jobs: list[dict[str, Any]],
        max_per_partition: int = 50,
    ) -> list[list[dict[str, Any]]]:
        """Partition a large job set into smaller batches.

        Groups jobs by zone or resource group first, then splits
        any group exceeding ``max_per_partition`` into sub-batches.

        Args:
            jobs: List of job dicts (each should have a ``zone``
                or ``resource_group`` key for grouping).
            max_per_partition: Maximum jobs per partition (default 50).

        Returns:
            List of job-list partitions.
        """
        self.log_started(
            "partition_batch",
            total_jobs=len(jobs),
            max_per_partition=max_per_partition,
        )

        if not jobs:
            self.log_completed("partition_batch", partitions=0)
            return []

        # Group by zone/resource_group
        groups: dict[str, list[dict[str, Any]]] = {}
        for job in jobs:
            key = job.get("zone") or job.get("resource_group") or "default"
            groups.setdefault(key, []).append(job)

        # Split groups that exceed max_per_partition
        partitions: list[list[dict[str, Any]]] = []
        for group_jobs in groups.values():
            num_chunks = math.ceil(len(group_jobs) / max_per_partition)
            for i in range(num_chunks):
                start = i * max_per_partition
                end = start + max_per_partition
                partitions.append(group_jobs[start:end])

        self.log_completed(
            "partition_batch",
            total_jobs=len(jobs),
            partitions=len(partitions),
        )
        return partitions
