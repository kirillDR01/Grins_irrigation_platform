#!/usr/bin/env python3
"""
Structured logging configuration with hybrid dotted namespace pattern.

This module provides AI-parseable JSON logging with request ID correlation
and a standardized namespace pattern: {domain}.{component}.{action}_{state}

Examples:
    - user.registration_started
    - database.connection_initialized
    - api.request_completed
    - validation.schema_failed
"""

import contextvars
import logging
import sys
import uuid
from typing import Any, Callable, Optional, Union

import structlog

# Lazy import to avoid circular dependency (services/__init__.py imports log_config)
# The actual import happens in configure_logging() which runs after all modules load
_pii_masking_processor = None


def _get_pii_masking_processor() -> (
    "Callable[[Any, str, dict[str, Any]], dict[str, Any]]"
):
    """Lazy-load PII masking processor to avoid circular imports."""
    global _pii_masking_processor  # noqa: PLW0603
    if _pii_masking_processor is None:
        from grins_platform.services.pii_masking import (  # noqa: PLC0415
            pii_masking_processor,
        )

        _pii_masking_processor = pii_masking_processor
    return _pii_masking_processor


def _pii_masking_wrapper(
    logger: Union[logging.Logger, "structlog.stdlib.BoundLogger"],
    method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """Wrapper that lazy-loads the PII masking processor."""
    processor = _get_pii_masking_processor()
    return processor(logger, method_name, event_dict)


# Context variable for request ID correlation
request_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "request_id",
    default=None,
)


def add_request_id(
    _logger: Union[logging.Logger, structlog.stdlib.BoundLogger],
    _method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """Add request ID to log entries for correlation."""
    request_id = request_id_var.get()
    if request_id:
        event_dict["request_id"] = request_id
    return event_dict


def add_timestamp(
    logger: Union[logging.Logger, structlog.stdlib.BoundLogger],
    method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """Add ISO timestamp to log entries."""
    event_dict["timestamp"] = structlog.stdlib.add_log_level(
        logger,
        method_name,
        event_dict,
    )
    return event_dict


def configure_logging(
    level: str = "INFO",
    json_output: bool = True,
    include_stdlib: bool = True,
) -> None:
    """
    Configure structured logging with hybrid dotted namespace pattern.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_output: Whether to output JSON format (True) or human-readable (False)
        include_stdlib: Whether to configure standard library logging
    """
    # Configure processors for structured logging
    processors = [
        # Add log level to event dict
        structlog.stdlib.add_log_level,
        # Add logger name
        structlog.stdlib.add_logger_name,
        # Add request ID correlation
        add_request_id,
        # Add timestamp
        structlog.processors.TimeStamper(fmt="iso"),
        # Stack info processor for exceptions
        structlog.processors.StackInfoRenderer(),
        # Exception formatting
        structlog.dev.set_exc_info,
        # PII masking — must be after all context is added, before rendering
        _pii_masking_wrapper,
    ]

    if json_output:
        # JSON output for production/AI parsing
        processors.append(structlog.processors.JSONRenderer())  # pyright: ignore[reportArgumentType]
    else:
        # Human-readable output for development
        processors.append(
            structlog.dev.ConsoleRenderer(  # pyright: ignore[reportArgumentType]
                colors=True,
                exception_formatter=structlog.dev.plain_traceback,
            ),
        )

    # Configure structlog
    structlog.configure(
        processors=processors,  # type: ignore[arg-type]
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        context_class=dict,
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging if requested
    if include_stdlib:
        logging.basicConfig(
            format="%(message)s",
            stream=sys.stdout,
            level=getattr(logging, level.upper()),
        )

        # Configure root logger to use structlog
        root_logger = logging.getLogger()
        root_logger.handlers.clear()
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("%(message)s"))
        root_logger.addHandler(handler)
        root_logger.setLevel(getattr(logging, level.upper()))


def get_logger(
    name: Optional[str] = None,
) -> Any:  # noqa: ANN401
    """
    Get a structured logger instance.

    Args:
        name: Logger name (optional, defaults to calling module)

    Returns:
        Configured structlog logger
    """
    return structlog.get_logger(name)


def set_request_id(request_id: Optional[str] = None) -> str:
    """
    Set request ID for correlation across log entries.

    Args:
        request_id: Request ID to set (generates UUID if None)

    Returns:
        The request ID that was set
    """
    if request_id is None:
        request_id = str(uuid.uuid4())

    _ = request_id_var.set(request_id)
    return request_id


def clear_request_id() -> None:
    """Clear the current request ID."""
    _ = request_id_var.set(None)


def log_event(
    logger: structlog.stdlib.BoundLogger,
    event: str,
    level: str = "info",
    **kwargs: Any,
) -> None:
    """
    Log an event using the hybrid dotted namespace pattern.

    Args:
        logger: Structlog logger instance
        event: Event name in format {domain}.{component}.{action}_{state}
        level: Log level (debug, info, warning, error, critical)
        **kwargs: Additional context data

    Examples:
        log_event(logger, "user.registration_started", email="user@example.com")
        log_event(logger, "database.connection_failed", error="Connection timeout")
    """
    log_method = getattr(logger, level.lower())
    log_method(event, **kwargs)


class LoggerMixin:
    """Mixin class to add structured logging to any class."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.logger = get_logger(self.__class__.__name__)

    def log_started(self, action: str, **kwargs: Any) -> None:
        """Log action started event."""
        domain = getattr(self, "DOMAIN", "app")
        component = self.__class__.__name__.lower()
        event = f"{domain}.{component}.{action}_started"
        self.logger.info(event, **kwargs)

    def log_completed(self, action: str, **kwargs: Any) -> None:
        """Log action completed event."""
        domain = getattr(self, "DOMAIN", "app")
        component = self.__class__.__name__.lower()
        event = f"{domain}.{component}.{action}_completed"
        self.logger.info(event, **kwargs)

    def log_failed(
        self,
        action: str,
        error: Optional[Exception] = None,
        **kwargs: Any,
    ) -> None:
        """Log action failed event."""
        domain = getattr(self, "DOMAIN", "app")
        component = self.__class__.__name__.lower()
        event = f"{domain}.{component}.{action}_failed"

        if error:
            kwargs["error"] = str(error)
            kwargs["error_type"] = error.__class__.__name__

        self.logger.error(event, exc_info=error is not None, **kwargs)

    def log_validated(self, action: str, **kwargs: Any) -> None:
        """Log validation success event."""
        domain = getattr(self, "DOMAIN", "app")
        component = self.__class__.__name__.lower()
        event = f"{domain}.{component}.{action}_validated"
        self.logger.info(event, **kwargs)

    def log_rejected(self, action: str, reason: str, **kwargs: Any) -> None:
        """Log validation rejection event."""
        domain = getattr(self, "DOMAIN", "app")
        component = self.__class__.__name__.lower()
        event = f"{domain}.{component}.{action}_rejected"
        self.logger.warning(event, reason=reason, **kwargs)


# Common logging patterns for different domains
class DomainLogger:
    """Domain-specific logging helpers."""

    @staticmethod
    def user_event(
        logger: structlog.stdlib.BoundLogger,
        action: str,
        state: str,
        **kwargs: Any,
    ) -> None:
        """Log user domain events."""
        event = f"user.auth.{action}_{state}"
        log_event(logger, event, **kwargs)

    @staticmethod
    def database_event(
        logger: structlog.stdlib.BoundLogger,
        action: str,
        state: str,
        **kwargs: Any,
    ) -> None:
        """Log database domain events."""
        event = f"database.connection.{action}_{state}"
        log_event(logger, event, **kwargs)

    @staticmethod
    def api_event(
        logger: structlog.stdlib.BoundLogger,
        action: str,
        state: str,
        **kwargs: Any,
    ) -> None:
        """Log API domain events."""
        event = f"api.request.{action}_{state}"
        log_event(logger, event, **kwargs)

    @staticmethod
    def validation_event(
        logger: structlog.stdlib.BoundLogger,
        action: str,
        state: str,
        **kwargs: Any,
    ) -> None:
        """Log validation domain events."""
        event = f"validation.schema.{action}_{state}"
        log_event(logger, event, **kwargs)


# Initialize logging on module import
configure_logging()
