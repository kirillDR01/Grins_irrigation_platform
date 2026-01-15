# ruff: noqa: TRY301
"""
Unit tests for structured logging with hybrid dotted namespace pattern.

Tests cover:
- Logger configuration and initialization
- Request ID correlation
- Hybrid dotted namespace pattern
- LoggerMixin functionality
- Domain-specific logging helpers
- Exception handling and stack traces
"""

import json
import uuid

import pytest
from _pytest.logging import LogCaptureFixture

from grins_platform.log_config import (
    DomainLogger,
    LoggerMixin,
    clear_request_id,
    configure_logging,
    get_logger,
    log_event,
    request_id_var,
    set_request_id,
)


class TestLoggingConfiguration:
    """Test logging configuration and setup."""

    def test_configure_logging_json_output(
        self, capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Test JSON output configuration."""
        configure_logging(level="DEBUG", json_output=True)
        logger = get_logger("test")

        # Log a message
        logger.info("test.configuration_validated", test_param="value")

        # Capture output
        captured = capsys.readouterr()
        output = captured.out.strip()

        # Parse JSON output
        log_data = json.loads(output)

        assert log_data["event"] == "test.configuration_validated"
        assert log_data["test_param"] == "value"
        assert log_data["level"] == "info"
        assert "timestamp" in log_data

    def test_configure_logging_human_readable(
        self, capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Test human-readable output configuration."""
        configure_logging(level="INFO", json_output=False)
        logger = get_logger("test")

        logger.info("test.human_readable_validated", test_param="value")

        # Capture output
        captured = capsys.readouterr()
        output = captured.out

        # Human-readable output should contain the event and parameter
        assert "test.human_readable_validated" in output
        assert "test_param" in output
        assert "value" in output

    def test_get_logger_returns_bound_logger(self) -> None:
        """Test that get_logger returns a properly configured logger."""
        logger = get_logger("test_module")

        # Logger is a BoundLoggerLazyProxy which wraps BoundLogger
        assert hasattr(logger, "info")
        assert hasattr(logger, "error")
        assert hasattr(logger, "warning")


class TestRequestIdCorrelation:
    """Test request ID correlation functionality."""

    def test_set_request_id_with_custom_id(self) -> None:
        """Test setting a custom request ID."""
        custom_id = "custom-request-123"
        result_id = set_request_id(custom_id)

        assert result_id == custom_id
        assert request_id_var.get() == custom_id

    def test_set_request_id_generates_uuid(self) -> None:
        """Test that set_request_id generates UUID when no ID provided."""
        result_id = set_request_id()

        # Should be a valid UUID string
        uuid.UUID(result_id)  # Will raise ValueError if invalid
        assert request_id_var.get() == result_id

    def test_clear_request_id(self) -> None:
        """Test clearing request ID."""
        set_request_id("test-id")
        assert request_id_var.get() == "test-id"

        clear_request_id()
        assert request_id_var.get() is None

    def test_request_id_in_log_output(
        self, capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Test that request ID appears in log output."""
        configure_logging(json_output=True)
        logger = get_logger("test")

        request_id = set_request_id("test-correlation-123")

        logger.info("test.correlation_validated", message="test")

        # Capture output
        captured = capsys.readouterr()
        output = captured.out.strip()

        log_data = json.loads(output)
        assert log_data["request_id"] == request_id

        clear_request_id()


class TestHybridDottedNamespace:
    """Test hybrid dotted namespace pattern."""

    def test_log_event_basic_pattern(
        self, capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Test basic event logging with dotted namespace."""
        configure_logging(json_output=True)
        logger = get_logger("test")

        log_event(logger, "user.registration_started", email="test@example.com")

        # Capture output
        captured = capsys.readouterr()
        output = captured.out.strip()

        log_data = json.loads(output)
        assert log_data["event"] == "user.registration_started"
        assert log_data["email"] == "test@example.com"
        assert log_data["level"] == "info"

    def test_log_event_different_levels(
        self, capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Test logging events at different levels."""
        configure_logging(level="DEBUG", json_output=True)
        logger = get_logger("test")

        test_cases = [
            ("debug", "database.connection_started"),
            ("info", "api.request_completed"),
            ("warning", "validation.schema_rejected"),
            ("error", "user.authentication_failed"),
        ]

        for level, event in test_cases:
            # Clear previous output
            capsys.readouterr()

            # Log the event
            log_event(logger, event, level=level, test_data="value")

            # Capture and verify output exists
            captured = capsys.readouterr()
            output = captured.out.strip()

            # Verify we got output (logging is working)
            assert len(output) > 0
            # Verify it's valid JSON
            log_data = json.loads(output)
            assert log_data["event"] == event
            assert log_data["level"] == level
            assert log_data["test_data"] == "value"

    def test_namespace_pattern_validation(
        self, capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Test various namespace patterns."""
        configure_logging(json_output=True)
        logger = get_logger("test")

        valid_patterns = [
            "user.auth.login_started",
            "database.connection.established_completed",
            "api.request.validation_failed",
            "system.startup.initialization_validated",
            "cache.redis.connection_rejected",
        ]

        for pattern in valid_patterns:
            log_event(logger, pattern, test_pattern=pattern)

            # Capture output
            captured = capsys.readouterr()
            output = captured.out.strip()

            log_data = json.loads(output)
            assert log_data["event"] == pattern

            # Verify pattern structure (domain.component.action_state)
            parts = pattern.split(".")
            assert len(parts) >= 3  # At least domain.component.action_state
            assert "_" in parts[-1]  # Last part should contain action_state


class TestLoggerMixin:
    """Test LoggerMixin functionality."""

    def setup_method(self) -> None:
        """Set up test environment."""
        configure_logging(json_output=True)

    def test_logger_mixin_initialization(self) -> None:
        """Test LoggerMixin initializes logger correctly."""

        class TestService(LoggerMixin):
            DOMAIN = "test"

        service = TestService()
        assert hasattr(service, "logger")
        assert hasattr(service.logger, "info")
        assert hasattr(service.logger, "error")

    def test_log_started_method(self, caplog: LogCaptureFixture) -> None:
        """Test log_started method."""

        class TestService(LoggerMixin):
            DOMAIN = "test"

        service = TestService()
        service.log_started("operation", param1="value1")

        assert len(caplog.records) > 0
        log_data = json.loads(caplog.records[0].message)
        assert log_data["event"] == "test.testservice.operation_started"
        assert log_data["param1"] == "value1"
        assert log_data["level"] == "info"

    def test_log_completed_method(self, caplog: LogCaptureFixture) -> None:
        """Test log_completed method."""

        class TestService(LoggerMixin):
            DOMAIN = "user"

        service = TestService()
        service.log_completed("registration", user_id="123")

        assert len(caplog.records) > 0
        log_data = json.loads(caplog.records[0].message)
        assert log_data["event"] == "user.testservice.registration_completed"
        assert log_data["user_id"] == "123"
        assert log_data["level"] == "info"

    def test_log_failed_method_with_exception(
        self, caplog: LogCaptureFixture,
    ) -> None:
        """Test log_failed method with exception."""

        class TestService(LoggerMixin):
            DOMAIN = "database"

        service = TestService()
        test_error = ValueError("Connection failed")

        service.log_failed("connection", error=test_error, host="localhost")

        assert len(caplog.records) > 0
        log_data = json.loads(caplog.records[0].message)
        assert log_data["event"] == "database.testservice.connection_failed"
        assert log_data["error"] == "Connection failed"
        assert log_data["error_type"] == "ValueError"
        assert log_data["host"] == "localhost"
        assert log_data["level"] == "error"

    def test_log_validated_method(self, caplog: LogCaptureFixture) -> None:
        """Test log_validated method."""

        class TestService(LoggerMixin):
            DOMAIN = "validation"

        service = TestService()
        service.log_validated("schema", fields=["name", "email"])

        assert len(caplog.records) > 0
        log_data = json.loads(caplog.records[0].message)
        assert log_data["event"] == "validation.testservice.schema_validated"
        assert log_data["fields"] == ["name", "email"]
        assert log_data["level"] == "info"

    def test_log_rejected_method(self, caplog: LogCaptureFixture) -> None:
        """Test log_rejected method."""

        class TestService(LoggerMixin):
            DOMAIN = "api"

        service = TestService()
        service.log_rejected("request", reason="invalid_token", endpoint="/users")

        assert len(caplog.records) > 0
        log_data = json.loads(caplog.records[0].message)
        assert log_data["event"] == "api.testservice.request_rejected"
        assert log_data["reason"] == "invalid_token"
        assert log_data["endpoint"] == "/users"
        assert log_data["level"] == "warning"

    def test_default_domain_when_not_specified(
        self, caplog: LogCaptureFixture,
    ) -> None:
        """Test default domain when DOMAIN not specified."""

        class TestService(LoggerMixin):
            pass  # No DOMAIN specified

        service = TestService()
        service.log_started("operation")

        assert len(caplog.records) > 0
        log_data = json.loads(caplog.records[0].message)
        assert log_data["event"] == "app.testservice.operation_started"


class TestDomainLogger:
    """Test domain-specific logging helpers."""

    def setup_method(self) -> None:
        """Set up test environment."""
        configure_logging(json_output=True)
        self.logger = get_logger("test")

    def test_user_event_logging(self, caplog: LogCaptureFixture) -> None:
        """Test user domain event logging."""
        DomainLogger.user_event(
            self.logger, "login", "started",
            email="user@example.com", source="web",
        )

        assert len(caplog.records) > 0
        log_data = json.loads(caplog.records[0].message)
        assert log_data["event"] == "user.auth.login_started"
        assert log_data["email"] == "user@example.com"
        assert log_data["source"] == "web"

    def test_database_event_logging(self, caplog: LogCaptureFixture) -> None:
        """Test database domain event logging."""
        DomainLogger.database_event(
            self.logger, "query", "completed",
            table="users", duration_ms=150,
        )

        assert len(caplog.records) > 0
        log_data = json.loads(caplog.records[0].message)
        assert log_data["event"] == "database.connection.query_completed"
        assert log_data["table"] == "users"
        assert log_data["duration_ms"] == 150

    def test_api_event_logging(self, caplog: LogCaptureFixture) -> None:
        """Test API domain event logging."""
        DomainLogger.api_event(
            self.logger, "processing", "failed",
            endpoint="/api/users", status_code=500,
        )

        assert len(caplog.records) > 0
        log_data = json.loads(caplog.records[0].message)
        assert log_data["event"] == "api.request.processing_failed"
        assert log_data["endpoint"] == "/api/users"
        assert log_data["status_code"] == 500

    def test_validation_event_logging(self, caplog: LogCaptureFixture) -> None:
        """Test validation domain events logging."""
        DomainLogger.validation_event(
            self.logger, "user_data", "rejected",
            reason="missing_fields", fields=["email"],
        )

        assert len(caplog.records) > 0
        log_data = json.loads(caplog.records[0].message)
        assert log_data["event"] == "validation.schema.user_data_rejected"
        assert log_data["reason"] == "missing_fields"
        assert log_data["fields"] == ["email"]


class TestExceptionHandling:
    """Test exception handling and stack traces."""

    def setup_method(self) -> None:
        """Set up test environment."""
        configure_logging(json_output=True)
        self.logger = get_logger("test")

    def test_exception_logging_with_stack_trace(
        self, caplog: LogCaptureFixture,
    ) -> None:
        """Test logging exceptions with stack traces."""
        try:
            msg = "Test exception for logging"
            raise ValueError(msg)
        except ValueError as e:
            self.logger.exception(
                "test.exception_handling_failed",
                error=str(e),
            )

        assert len(caplog.records) > 0
        log_data = json.loads(caplog.records[0].message)
        assert log_data["event"] == "test.exception_handling_failed"
        assert log_data["error"] == "Test exception for logging"
        assert log_data["level"] == "error"
        # Stack trace should be included
        assert log_data.get("exc_info") is True

    def test_logger_mixin_exception_handling(
        self, caplog: LogCaptureFixture,
    ) -> None:
        """Test LoggerMixin exception handling."""

        class TestService(LoggerMixin):
            DOMAIN = "test"

        service = TestService()
        test_exception = ConnectionError("Database connection failed")

        service.log_failed("database_operation", error=test_exception)

        assert len(caplog.records) > 0
        log_data = json.loads(caplog.records[0].message)
        assert log_data["event"] == "test.testservice.database_operation_failed"
        assert log_data["error"] == "Database connection failed"
        assert log_data["error_type"] == "ConnectionError"
        assert log_data["level"] == "error"


class TestIntegration:
    """Integration tests for complete logging workflow."""

    def test_complete_logging_workflow(
        self, capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Test complete logging workflow with request correlation."""
        configure_logging(json_output=True)

        class UserService(LoggerMixin):
            DOMAIN = "user"

            def process_user(self, email: str) -> dict[str, str]:
                self.log_started("processing", email=email)

                try:
                    # Simulate processing
                    if "@" not in email:
                        self.log_rejected(
                            "processing", reason="invalid_email", email=email,
                        )
                        msg = "Invalid email"
                        raise ValueError(msg)

                    self.log_validated("email", email=email)
                    user_id = f"user_{hash(email) % 1000}"
                    self.log_completed("processing", user_id=user_id, email=email)

                except Exception as error:
                    self.log_failed("processing", error=error, email=email)
                    raise
                else:
                    return {"user_id": user_id, "email": email}

        # Set request ID for correlation
        request_id = set_request_id("integration-test-123")

        try:
            service = UserService()
            result = service.process_user("test@example.com")

            # Capture all log output
            captured = capsys.readouterr()
            output = captured.out

            # Parse all log entries
            log_entries = [
                json.loads(line) for line in output.strip().split("\n") if line
            ]

            # Verify log sequence
            assert len(log_entries) == 3  # started, validated, completed

            # Check started event
            assert log_entries[0]["event"] == "user.userservice.processing_started"
            assert log_entries[0]["email"] == "test@example.com"
            assert log_entries[0]["request_id"] == request_id

            # Check validated event
            assert log_entries[1]["event"] == "user.userservice.email_validated"
            assert log_entries[1]["email"] == "test@example.com"
            assert log_entries[1]["request_id"] == request_id

            # Check completed event
            assert log_entries[2]["event"] == "user.userservice.processing_completed"
            assert log_entries[2]["email"] == "test@example.com"
            assert log_entries[2]["request_id"] == request_id
            assert "user_id" in log_entries[2]

            # Verify result
            assert result["email"] == "test@example.com"
            assert "user_id" in result

        finally:
            clear_request_id()


if __name__ == "__main__":
    pytest.main([__file__])
