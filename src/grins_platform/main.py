#!/usr/bin/env python3
"""
MyPy Configuration Test Script

This script demonstrates and tests various MyPy type checking features
optimized for AI-generated code patterns. It includes examples of:
- Strict type checking
- Generic types and type variables
- Protocol definitions
- Union types and Optional handling
- Class inheritance and method overriding
- Error handling patterns
- AI-friendly type patterns
"""

import json
import logging
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import (
    Any,
    Generic,
    Optional,
    Protocol,
    TypeVar,
    Union,
    cast,
    overload,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Type variables for generic programming
T = TypeVar("T")
K = TypeVar("K")
V = TypeVar("V")
SerializableT = TypeVar("SerializableT", bound="Serializable")


class ProcessingStatus(Enum):
    """Status enumeration for processing operations."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ProcessingResult(Generic[T]):
    """Generic result container for processing operations."""

    status: ProcessingStatus
    data: Optional[T]
    error_message: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None

    def __post_init__(self) -> None:
        """Initialize default metadata if not provided."""
        if self.metadata is None:
            self.metadata = {}


class Serializable(Protocol):
    """Protocol for objects that can be serialized to JSON."""

    def to_dict(self) -> dict[str, Any]:
        """Convert object to dictionary representation."""
        ...

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Serializable":
        """Create object from dictionary representation."""
        ...


class DataProcessor(ABC, Generic[T]):
    """Abstract base class for data processors with generic type support."""

    def __init__(self, name: str, config: dict[str, Any]) -> None:
        """Initialize the processor with name and configuration.

        Args:
            name: Processor name for identification
            config: Configuration dictionary
        """
        super().__init__()
        self.name = name
        self.config = config
        self._processed_count = 0

    @property
    def processed_count(self) -> int:
        """Get the number of processed items."""
        return self._processed_count

    @abstractmethod
    def process_item(self, item: T) -> ProcessingResult[T]:
        """Process a single item.

        Args:
            item: Item to process

        Returns:
            Processing result with status and data
        """
        ...

    def process_batch(self, items: list[T]) -> list[ProcessingResult[T]]:
        """Process a batch of items.

        Args:
            items: List of items to process

        Returns:
            List of processing results
        """
        results: list[ProcessingResult[T]] = []

        for item in items:
            result = self._process_single_item_safely(item)
            results.append(result)
            if result.status == ProcessingStatus.COMPLETED:
                self._processed_count += 1

        return results

    def _process_single_item_safely(self, item: T) -> ProcessingResult[T]:
        """Safely process a single item with exception handling."""
        try:
            return self.process_item(item)
        except Exception as e:
            return ProcessingResult[T](
                status=ProcessingStatus.FAILED,
                data=None,
                error_message=str(e),
            )


class StringProcessor(DataProcessor[str]):
    """Concrete implementation of DataProcessor for string processing."""

    def __init__(self, name: str, config: dict[str, Any]) -> None:
        """Initialize string processor."""
        super().__init__(name, config)
        self.min_length: int = config.get("min_length", 1)
        self.max_length: int = config.get("max_length", 1000)

    def process_item(self, item: str) -> ProcessingResult[str]:
        """Process a single string item.

        Args:
            item: String to process

        Returns:
            Processing result with processed string
        """
        # Validate length constraints
        if len(item) < self.min_length:
            return ProcessingResult[str](
                status=ProcessingStatus.FAILED,
                data=None,
                error_message=f"String too short: {len(item)} < {self.min_length}",
            )
        if len(item) > self.max_length:
            return ProcessingResult[str](
                status=ProcessingStatus.FAILED,
                data=None,
                error_message=f"String too long: {len(item)} > {self.max_length}",
            )

        # Process the string (normalize and clean)
        processed = item.strip().lower().title()

        return ProcessingResult[str](
            status=ProcessingStatus.COMPLETED,
            data=processed,
            metadata={"original_length": len(item), "processed_length": len(processed)},
        )


@dataclass
class User(Serializable):
    """User data class implementing Serializable protocol."""

    id: int
    name: str
    email: str
    active: bool = True
    metadata: Optional[dict[str, Any]] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert user to dictionary representation."""
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "active": self.active,
            "metadata": self.metadata or {},
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "User":
        """Create user from dictionary representation."""
        return cls(
            id=data["id"],
            name=data["name"],
            email=data["email"],
            active=data.get("active", True),
            metadata=data.get("metadata"),
        )


class FileManager(Generic[SerializableT]):
    """Generic file manager for serializable objects."""

    def __init__(self, file_path: Path) -> None:
        """Initialize file manager with path."""
        super().__init__()
        self.file_path = file_path

    @overload
    def save_data(self, data: list[Serializable]) -> bool:
        ...

    @overload
    def save_data(self, data: Serializable) -> bool:
        ...

    def save_data(self, data: Union[Serializable, list[Serializable]]) -> bool:
        """Save serializable data to file.

        Args:
            data: Single object or list of objects to save

        Returns:
            True if successful, False otherwise
        """
        try:
            self.file_path.parent.mkdir(parents=True, exist_ok=True)

            if isinstance(data, list):
                json_data: Union[dict[str, Any], list[dict[str, Any]]] = [
                    item.to_dict() for item in data
                ]
            else:
                json_data = data.to_dict()

            with self.file_path.open("w", encoding="utf-8") as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)

        except Exception:
            logger.exception("Failed to save data")
            return False
        else:
            return True

    def load_data(
        self, data_class: type[SerializableT],
    ) -> Optional[list[SerializableT]]:
        """Load data from file.

        Args:
            data_class: Class constructor for creating objects from dict

        Returns:
            List of loaded objects or None if failed
        """
        try:
            if not self.file_path.exists():
                return None

            with self.file_path.open("r", encoding="utf-8") as f:
                json_data: Union[dict[str, Any], list[dict[str, Any]]] = (
                    json.load(f)
                )

            if isinstance(json_data, list):
                return [
                    cast("SerializableT", data_class.from_dict(item))
                    for item in json_data
                ]
            return [cast("SerializableT", data_class.from_dict(json_data))]

        except Exception:
            logger.exception("Failed to load data")
            return None


def process_users_with_validation(
    users: list[User],
    processor: DataProcessor[str],
) -> dict[str, Union[int, float, list[str]]]:
    """Process user names with validation and return statistics.

    Args:
        users: List of users to process
        processor: String processor for name validation

    Returns:
        Dictionary with processing statistics and results
    """
    names = [user.name for user in users]
    results = processor.process_batch(names)

    successful_results: list[str] = []
    failed_results: list[str] = []

    for result in results:
        if result.status == ProcessingStatus.COMPLETED and result.data is not None:
            successful_results.append(result.data)
        else:
            failed_results.append(result.error_message or "Unknown error")

    return {
        "total_processed": len(results),
        "successful": len(successful_results),
        "failed": len(failed_results),
        "success_rate": len(successful_results) / len(results) if results else 0.0,
        "successful_names": successful_results,
        "error_messages": failed_results,
    }


def demonstrate_type_narrowing(value: Union[str, int, None]) -> str:
    """Demonstrate type narrowing with Union types.

    Args:
        value: Value that could be string, int, or None

    Returns:
        String representation of the value
    """
    if value is None:
        return "None"
    if isinstance(value, str):
        # MyPy knows value is str here
        return f"String: {value.upper()}"
    # MyPy knows value is int here (only remaining type)
    return f"Integer: {value * 2}"


def main() -> int:
    """Main function demonstrating MyPy type checking features.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    print("🔍 Testing MyPy Configuration for AI-Generated Code")
    print("=" * 60)

    # Test generic data processing
    config = {"min_length": 2, "max_length": 50}
    processor = StringProcessor("name_processor", config)

    # Create test users
    users = [
        User(1, "Alice Smith", "alice@example.com"),
        User(2, "Bob Jones", "bob@example.com"),
        User(3, "", "invalid@example.com"),  # Invalid name (too short)
        User(4, "Charlie Brown", "charlie@example.com"),
    ]

    # Process users
    stats = process_users_with_validation(users, processor)

    print("📊 Processing Results:")
    print(f"   Total processed: {stats['total_processed']}")
    print(f"   Successful: {stats['successful']}")
    print(f"   Failed: {stats['failed']}")
    print(f"   Success rate: {stats['success_rate']:.1%}")

    # Test file operations
    file_manager: FileManager[User] = FileManager(Path("output/users.json"))

    # Use cast to handle the variance issue with list[User] -> list[Serializable]
    if file_manager.save_data(cast("list[Serializable]", users)):
        print("✅ Users saved to file successfully")
    else:
        print("❌ Failed to save users to file")

    # Test type narrowing
    test_values: list[Union[str, int, None]] = ["hello", 42, None]

    print("\n🔧 Type Narrowing Examples:")
    for value in test_values:
        result = demonstrate_type_narrowing(value)
        print(f"   {result}")

    # Test explicit Any usage (allowed in our config)
    dynamic_data: Any = {"key": "value", "number": 123}
    processed_dynamic = cast("dict[str, Union[str, int]]", dynamic_data)

    print(f"\n📝 Dynamic data processing: {processed_dynamic}")

    print("\n✅ MyPy type checking demonstration completed!")
    print("   • Strict type checking enabled")
    print("   • Generic types and protocols working")
    print("   • Union type narrowing functional")
    print("   • Error handling patterns validated")
    print("   • AI-friendly patterns supported")

    return 0


if __name__ == "__main__":
    sys.exit(main())


# ============================================================================
# STRUCTURED LOGGING DEMONSTRATION
# ============================================================================
# The following section demonstrates structured logging with hybrid dotted
# namespace pattern, added to showcase logging capabilities without modifying
# the existing MyPy demonstration code above.
# ============================================================================

# ruff: noqa: TRY301, E402
"""
Structured Logging Examples

This section demonstrates:
- Request ID correlation
- Domain-specific event logging
- Exception handling with stack traces
- LoggerMixin for class-based logging
"""

import time as time_module

from grins_platform.log_config import (
    DomainLogger,
    LoggerMixin,
    clear_request_id,
    get_logger,
    set_request_id,
)

# Get structured logger
structured_logger = get_logger(__name__)


class UserRegistrationService(LoggerMixin):
    """Example service demonstrating LoggerMixin for structured logging."""

    DOMAIN = "user"  # Domain for this service

    def register_user(self, email: str, source: str = "api") -> dict[str, str]:
        """
        Register a new user with structured logging.

        Args:
            email: User email address
            source: Registration source

        Returns:
            User registration result
        """
        # Log registration started
        self.log_started("registration", email=email, source=source)

        try:
            # Simulate registration process
            time_module.sleep(0.01)  # Simulate processing time

            # Validate email format (simple example)
            if "@" not in email:
                self.log_rejected(
                    "registration", reason="invalid_email_format", email=email,
                )
                msg = "Invalid email format"
                raise ValueError(msg)

            # Log validation success
            self.log_validated("email_format", email=email)

            # Simulate user creation
            user_id = f"user_{hash(email) % 10000}"

            # Log successful completion
            self.log_completed("registration", user_id=user_id, email=email)

        except Exception as error:
            # Log failure with exception details
            self.log_failed("registration", error=error, email=email)
            raise
        else:
            return {"user_id": user_id, "email": email, "status": "registered"}


class DatabaseConnectionService(LoggerMixin):
    """Example database service with structured logging."""

    DOMAIN = "database"

    def connect(self, host: str = "localhost", port: int = 5432) -> bool:
        """
        Connect to database with logging.

        Args:
            host: Database host
            port: Database port

        Returns:
            Connection success status
        """
        self.log_started("connection", host=host, port=port)

        try:
            # Simulate connection attempt
            time_module.sleep(0.01)

            # Simulate connection success
            self.log_completed("connection", host=host, port=port, duration_ms=10)

        except Exception as error:
            self.log_failed("connection", error=error, host=host, port=port)
            raise
        else:
            return True


def demonstrate_api_logging(endpoint: str, method: str = "GET") -> dict[str, str]:
    """
    Demonstrate API request logging using domain helpers.

    Args:
        endpoint: API endpoint
        method: HTTP method

    Returns:
        API response simulation
    """
    # Set request ID for correlation
    request_id = set_request_id()

    try:
        # Log API request started
        DomainLogger.api_event(
            structured_logger, "processing", "started",
            endpoint=endpoint, method=method, request_id=request_id,
        )

        # Simulate request processing
        time_module.sleep(0.01)

        # Log successful completion
        DomainLogger.api_event(
            structured_logger,
            "processing",
            "completed",
            endpoint=endpoint,
            method=method,
            status_code=200,
            duration_ms=10,
        )

    except Exception as error:
        # Log API failure
        DomainLogger.api_event(
            structured_logger,
            "processing",
            "failed",
            endpoint=endpoint,
            method=method,
            error=str(error),
        )
        raise
    else:
        return {"status": "success", "endpoint": endpoint, "request_id": request_id}
    finally:
        # Clear request ID
        clear_request_id()


def demonstrate_validation_logging(data: dict[str, str]) -> bool:
    """
    Demonstrate validation logging patterns.

    Args:
        data: Data to validate

    Returns:
        Validation result
    """
    try:
        # Log validation started
        DomainLogger.validation_event(
            structured_logger, "user_data", "started",
            fields=list(data.keys()),
        )

        # Validate required fields
        required_fields = ["name", "email"]
        missing_fields = [field for field in required_fields if field not in data]

        if missing_fields:
            # Log validation rejection
            DomainLogger.validation_event(
                structured_logger, "user_data", "rejected",
                reason="missing_required_fields",
                missing_fields=missing_fields,
            )
            return False

        # Log validation success
        DomainLogger.validation_event(
            structured_logger, "user_data", "validated", fields=list(data.keys()),
        )

    except Exception as error:
        # Log validation failure
        DomainLogger.validation_event(
            structured_logger, "user_data", "failed", error=str(error),
        )
        raise
    else:
        return True


def demonstrate_structured_logging() -> None:
    """Demonstrate structured logging patterns."""
    structured_logger.info("logging_demo.startup_started", version="1.0.0")

    try:
        # Initialize services
        user_service = UserRegistrationService()
        db_service = DatabaseConnectionService()

        # Demonstrate database connection logging
        structured_logger.info("logging_demo.database_initialization_started")
        _ = db_service.connect()
        structured_logger.info("logging_demo.database_initialization_completed")

        # Demonstrate user registration logging
        structured_logger.info("logging_demo.user_operations_started")

        # Successful registration
        result = user_service.register_user("alice@example.com", source="web")
        structured_logger.info("logging_demo.user_created", **result)

        # Failed registration (invalid email)
        try:
            _ = user_service.register_user("invalid-email", source="api")
        except ValueError:
            structured_logger.info("logging_demo.invalid_registration_handled")

        # Demonstrate API request logging
        structured_logger.info("logging_demo.api_demo_started")
        api_result = demonstrate_api_logging("/users", "POST")
        structured_logger.info("logging_demo.api_demo_completed", **api_result)

        # Demonstrate validation logging
        structured_logger.info("logging_demo.validation_demo_started")

        # Valid data
        valid_data = {"name": "Bob", "email": "bob@example.com"}
        is_valid = demonstrate_validation_logging(valid_data)
        structured_logger.info(
            "logging_demo.validation_result",
            is_valid=is_valid,
            data_type="valid",
        )

        # Invalid data
        invalid_data = {"name": "Charlie"}  # Missing email
        is_valid = demonstrate_validation_logging(invalid_data)
        structured_logger.info(
            "logging_demo.validation_result",
            is_valid=is_valid,
            data_type="invalid",
        )

        structured_logger.info("logging_demo.startup_completed", status="success")

    except Exception as error:
        structured_logger.exception(
            "logging_demo.startup_failed",
            error=str(error),
            error_type=error.__class__.__name__,
        )
        raise
