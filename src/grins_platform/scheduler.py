"""Background job scheduler infrastructure using APScheduler.

Provides a singleton scheduler with structured logging
and FastAPI lifespan integration.

Validates: Requirements 16.1, 16.2, 16.4
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from apscheduler.events import (  # type: ignore[import-untyped]
    EVENT_JOB_ERROR,
    EVENT_JOB_EXECUTED,
    JobEvent,
)
from apscheduler.schedulers.asyncio import (
    AsyncIOScheduler,  # type: ignore[import-untyped]
)

from grins_platform.log_config import LoggerMixin, get_logger

if TYPE_CHECKING:
    from apscheduler.job import Job  # type: ignore[import-untyped]

logger = get_logger(__name__)

_scheduler: BackgroundScheduler | None = None


class BackgroundScheduler(LoggerMixin):
    """Manages APScheduler lifecycle with structured logging.

    Validates: Requirements 16.1, 16.2, 16.4
    """

    DOMAIN = "scheduler"

    def __init__(self) -> None:
        super().__init__()
        self._scheduler = AsyncIOScheduler(
            job_defaults={
                "coalesce": True,
                "max_instances": 1,
                "misfire_grace_time": 3600,
            },
        )
        self._scheduler.add_listener(self._on_job_executed, EVENT_JOB_EXECUTED)
        self._scheduler.add_listener(self._on_job_error, EVENT_JOB_ERROR)

    @property
    def scheduler(self) -> AsyncIOScheduler:
        """Access the underlying APScheduler instance."""
        return self._scheduler

    def _on_job_executed(self, event: JobEvent) -> None:
        logger.info(
            "scheduler.job.executed",
            job_id=event.job_id,
        )

    def _on_job_error(self, event: JobEvent) -> None:
        exc = getattr(event, "exception", None)
        logger.error(
            "scheduler.job.failed",
            job_id=event.job_id,
            exception=str(exc) if exc else None,
        )

    def start(self) -> None:
        """Start the scheduler."""
        self.log_started("start")
        self._scheduler.start()
        self.log_completed("start")

    def shutdown(self, wait: bool = True) -> None:
        """Gracefully shut down the scheduler."""
        self.log_started("shutdown")
        self._scheduler.shutdown(wait=wait)
        self.log_completed("shutdown")

    def add_job(
        self,
        func: Callable[..., Any],
        trigger: str,
        **kwargs: Any,
    ) -> Job:
        """Add a job to the scheduler."""
        return self._scheduler.add_job(func, trigger, **kwargs)


def get_scheduler() -> BackgroundScheduler:
    """Get or create the global scheduler singleton."""
    global _scheduler  # noqa: PLW0603
    if _scheduler is None:
        _scheduler = BackgroundScheduler()
    return _scheduler
