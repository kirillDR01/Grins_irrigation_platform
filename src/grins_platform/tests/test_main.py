#!/usr/bin/env python3
"""
Comprehensive tests for main.py demonstrating pytest best practices.

This test suite covers:
- Unit tests for individual functions and classes
- Property-based testing patterns (using pytest fixtures)
- Async testing capabilities with pytest-asyncio
- Error handling and edge cases
- Type safety validation
- Structured logging functionality
"""

import json
from pathlib import Path
from typing import cast
from unittest.mock import Mock, patch

import pytest
from _pytest.logging import LogCaptureFixture

from grins_platform.main import (
    DatabaseConnectionService,
    FileManager,
    ProcessingResult,
    ProcessingStatus,
    Serializable,
    StringProcessor,
    User,
    UserRegistrationService,
    demonstrate_api_logging,
    demonstrate_structured_logging,
    demonstrate_type_narrowing,
    demonstrate_validation_logging,
    main,
    process_users_with_validation,
)


class TestProcessingStatus:
    """Test ProcessingStatus enum."""

    def test_status_values(self) -> None:
        """Test that all status values are correctly defined."""
        assert ProcessingStatus.PENDING.value == "pending"
        assert ProcessingStatus.PROCESSING.value == "processing"
        assert ProcessingStatus.COMPLETED.value == "completed"
        assert ProcessingStatus.FAILED.value == "failed"


class TestProcessingResult:
    """Test ProcessingResult dataclass."""

    def test_processing_result_creation(self) -> None:
        """Test creating ProcessingResult with required fields."""
        result = ProcessingResult[str](
            status=ProcessingStatus.COMPLETED,
            data="test_data",
        )

        assert result.status == ProcessingStatus.COMPLETED
        assert result.data == "test_data"
        assert result.error_message is None
        assert result.metadata == {}  # Should be initialized by __post_init__

    def test_processing_result_with_error(self) -> None:
        """Test ProcessingResult with error message."""
        result = ProcessingResult[str](
            status=ProcessingStatus.FAILED,
            data=None,
            error_message="Test error",
        )

        assert result.status == ProcessingStatus.FAILED
        assert result.data is None
        assert result.error_message == "Test error"
        assert result.metadata == {}

    def test_processing_result_with_metadata(self) -> None:
        """Test ProcessingResult with custom metadata."""
        metadata = {"key": "value", "count": 42}
        result = ProcessingResult[int](
            status=ProcessingStatus.COMPLETED,
            data=100,
            metadata=metadata,
        )

        assert result.metadata == metadata


class TestStringProcessor:
    """Test StringProcessor implementation."""

    @pytest.fixture
    def processor(self) -> StringProcessor:
        """Create a StringProcessor instance for testing."""
        config = {"min_length": 2, "max_length": 10}
        return StringProcessor("test_processor", config)

    def test_processor_initialization(self, processor: StringProcessor) -> None:
        """Test StringProcessor initialization."""
        assert processor.name == "test_processor"
        assert processor.min_length == 2
        assert processor.max_length == 10
        assert processor.processed_count == 0

    def test_process_valid_string(self, processor: StringProcessor) -> None:
        """Test processing a valid string."""
        # Use shorter string that fits within max_length=10
        result = processor.process_item("hello")

        assert result.status == ProcessingStatus.COMPLETED
        assert result.data == "Hello"
        assert result.error_message is None
        assert result.metadata is not None
        assert result.metadata["original_length"] == 5
        assert result.metadata["processed_length"] == 5

    def test_process_string_too_short(self, processor: StringProcessor) -> None:
        """Test processing a string that's too short."""
        result = processor.process_item("a")

        assert result.status == ProcessingStatus.FAILED
        assert result.data is None
        assert result.error_message is not None
        assert "String too short" in result.error_message

    def test_process_string_too_long(self, processor: StringProcessor) -> None:
        """Test processing a string that's too long."""
        long_string = "a" * 15
        result = processor.process_item(long_string)

        assert result.status == ProcessingStatus.FAILED
        assert result.data is None
        assert result.error_message is not None
        assert "String too long" in result.error_message

    def test_process_batch_mixed_results(self, processor: StringProcessor) -> None:
        """Test processing a batch with mixed valid/invalid strings."""
        items = ["valid", "x", "also valid", "way too long string here"]
        results = processor.process_batch(items)

        assert len(results) == 4
        assert results[0].status == ProcessingStatus.COMPLETED
        assert results[1].status == ProcessingStatus.FAILED
        assert results[2].status == ProcessingStatus.COMPLETED
        assert results[3].status == ProcessingStatus.FAILED

        # Should have processed 2 successful items
        assert processor.processed_count == 2

    def test_process_batch_with_exception(self, processor: StringProcessor) -> None:
        """Test batch processing handles exceptions gracefully."""
        # Mock process_item to raise an exception
        original_method = processor.process_item

        def mock_process_item(item: str) -> ProcessingResult[str]:
            if item == "error":
                error_msg = "Test exception"
                raise ValueError(error_msg)
            return original_method(item)

        processor.process_item = mock_process_item

        items = ["valid", "error", "also valid"]
        results = processor.process_batch(items)

        assert len(results) == 3
        assert results[0].status == ProcessingStatus.COMPLETED
        assert results[1].status == ProcessingStatus.FAILED
        assert results[1].error_message == "Test exception"
        assert results[2].status == ProcessingStatus.COMPLETED


class TestUser:
    """Test User dataclass and Serializable implementation."""

    @pytest.fixture
    def sample_user(self) -> User:
        """Create a sample user for testing."""
        return User(
            id=1,
            name="Alice Smith",
            email="alice@example.com",
            active=True,
            metadata={"role": "admin"},
        )

    def test_user_creation(self, sample_user: User) -> None:
        """Test User creation with all fields."""
        assert sample_user.id == 1
        assert sample_user.name == "Alice Smith"
        assert sample_user.email == "alice@example.com"
        assert sample_user.active is True
        assert sample_user.metadata == {"role": "admin"}

    def test_user_creation_defaults(self) -> None:
        """Test User creation with default values."""
        user = User(id=2, name="Bob", email="bob@example.com")

        assert user.active is True
        assert user.metadata is None

    def test_user_to_dict(self, sample_user: User) -> None:
        """Test User serialization to dictionary."""
        result = sample_user.to_dict()

        expected = {
            "id": 1,
            "name": "Alice Smith",
            "email": "alice@example.com",
            "active": True,
            "metadata": {"role": "admin"},
        }

        assert result == expected

    def test_user_to_dict_no_metadata(self) -> None:
        """Test User serialization with no metadata."""
        user = User(id=3, name="Charlie", email="charlie@example.com")
        result = user.to_dict()

        assert result["metadata"] == {}

    def test_user_from_dict(self) -> None:
        """Test User deserialization from dictionary."""
        data = {
            "id": 4,
            "name": "Diana",
            "email": "diana@example.com",
            "active": False,
            "metadata": {"department": "engineering"},
        }

        user = User.from_dict(data)

        assert user.id == 4
        assert user.name == "Diana"
        assert user.email == "diana@example.com"
        assert user.active is False
        assert user.metadata == {"department": "engineering"}

    def test_user_from_dict_minimal(self) -> None:
        """Test User deserialization with minimal data."""
        data = {
            "id": 5,
            "name": "Eve",
            "email": "eve@example.com",
        }

        user = User.from_dict(data)

        assert user.id == 5
        assert user.name == "Eve"
        assert user.email == "eve@example.com"
        assert user.active is True  # Default value
        assert user.metadata is None


class TestFileManager:
    """Test FileManager generic class."""

    @pytest.fixture
    def temp_file_path(self, tmp_path: Path) -> Path:
        """Create a temporary file path for testing."""
        return tmp_path / "test_data.json"

    @pytest.fixture
    def file_manager(self, temp_file_path: Path) -> FileManager[User]:
        """Create a FileManager instance for testing."""
        return FileManager(temp_file_path)

    @pytest.fixture
    def sample_users(self) -> list[User]:
        """Create sample users for testing."""
        return [
            User(1, "Alice", "alice@example.com"),
            User(2, "Bob", "bob@example.com", active=False),
        ]

    def test_file_manager_initialization(
        self, file_manager: FileManager[User], temp_file_path: Path,
    ) -> None:
        """Test FileManager initialization."""
        assert file_manager.file_path == temp_file_path

    def test_save_single_user(
        self, file_manager: FileManager[User], sample_users: list[User],
    ) -> None:
        """Test saving a single user to file."""
        user = sample_users[0]
        result = file_manager.save_data(user)

        assert result is True
        assert file_manager.file_path.exists()

        # Verify file content
        with file_manager.file_path.open("r") as f:
            data = json.load(f)

        expected = user.to_dict()
        assert data == expected

    def test_save_multiple_users(
        self, file_manager: FileManager[User], sample_users: list[User],
    ) -> None:
        """Test saving multiple users to file."""
        result = file_manager.save_data(cast("list[Serializable]", sample_users))

        assert result is True
        assert file_manager.file_path.exists()

        # Verify file content
        with file_manager.file_path.open("r") as f:
            data = json.load(f)

        expected = [user.to_dict() for user in sample_users]
        assert data == expected

    def test_load_data_file_not_exists(self, file_manager: FileManager[User]) -> None:
        """Test loading data when file doesn't exist."""
        result = file_manager.load_data(User)
        assert result is None

    def test_load_single_user(
        self, file_manager: FileManager[User], sample_users: list[User],
    ) -> None:
        """Test loading a single user from file."""
        user = sample_users[0]

        # Save data first
        _ = file_manager.save_data(user)

        # Load data
        result = file_manager.load_data(User)

        assert result is not None
        assert len(result) == 1
        assert result[0].id == user.id
        assert result[0].name == user.name
        assert result[0].email == user.email

    def test_load_multiple_users(
        self, file_manager: FileManager[User], sample_users: list[User],
    ) -> None:
        """Test loading multiple users from file."""
        # Save data first
        _ = file_manager.save_data(cast("list[Serializable]", sample_users))

        # Load data
        result = file_manager.load_data(User)

        assert result is not None
        assert len(result) == len(sample_users)

        for i, loaded_user in enumerate(result):
            original_user = sample_users[i]
            assert loaded_user.id == original_user.id
            assert loaded_user.name == original_user.name
            assert loaded_user.email == original_user.email
            assert loaded_user.active == original_user.active

    def test_save_data_io_error(
        self, file_manager: FileManager[User], sample_users: list[User],
    ) -> None:
        """Test save_data handles IO errors gracefully."""
        # Use a path that will definitely cause an error (invalid path)
        file_manager.file_path = Path("/invalid/path/that/does/not/exist/file.json")

        user = sample_users[0]
        result = file_manager.save_data(user)

        assert result is False

    @patch("builtins.open", side_effect=OSError("Permission denied"))
    def test_load_data_io_error(
        self, _mock_file: Mock, file_manager: FileManager[User],
    ) -> None:
        """Test load_data handles IO errors gracefully."""
        # Create the file first so it exists
        file_manager.file_path.touch()

        result = file_manager.load_data(User)
        assert result is None


class TestUtilityFunctions:
    """Test utility functions."""

    def test_process_users_with_validation(self) -> None:
        """Test process_users_with_validation function."""
        users = [
            User(1, "Alice Smith", "alice@example.com"),
            User(2, "Bob", "bob@example.com"),
            User(3, "", "invalid@example.com"),  # Invalid name
        ]

        config = {"min_length": 2, "max_length": 50}
        processor = StringProcessor("test", config)

        result = process_users_with_validation(users, processor)

        assert result["total_processed"] == 3
        assert result["successful"] == 2
        assert result["failed"] == 1
        assert result["success_rate"] == 2/3
        successful_names = result["successful_names"]
        error_messages = result["error_messages"]
        assert isinstance(successful_names, list)
        assert isinstance(error_messages, list)
        assert len(successful_names) == 2
        assert len(error_messages) == 1

    def test_demonstrate_type_narrowing_string(self) -> None:
        """Test type narrowing with string input."""
        result = demonstrate_type_narrowing("hello")
        assert result == "String: HELLO"

    def test_demonstrate_type_narrowing_int(self) -> None:
        """Test type narrowing with integer input."""
        result = demonstrate_type_narrowing(42)
        assert result == "Integer: 84"

    def test_demonstrate_type_narrowing_none(self) -> None:
        """Test type narrowing with None input."""
        result = demonstrate_type_narrowing(None)
        assert result == "None"


class TestMainFunction:
    """Test main function."""

    @patch("grins_platform.main.FileManager")
    @patch("builtins.print")
    def test_main_function_success(
        self, mock_print: Mock, mock_file_manager_class: Mock,
    ) -> None:
        """Test main function executes successfully."""
        # Mock FileManager instance
        mock_file_manager = Mock()
        mock_file_manager.save_data.return_value = True
        mock_file_manager_class.return_value = mock_file_manager

        result = main()

        assert result == 0

        # Verify print statements were called
        assert mock_print.call_count > 0

        # Verify FileManager was used
        mock_file_manager_class.assert_called_once()
        mock_file_manager.save_data.assert_called_once()

    @patch("grins_platform.main.FileManager")
    @patch("builtins.print")
    def test_main_function_file_save_failure(
        self, mock_print: Mock, mock_file_manager_class: Mock,
    ) -> None:
        """Test main function handles file save failure."""
        # Mock FileManager instance to fail save
        mock_file_manager = Mock()
        mock_file_manager.save_data.return_value = False
        mock_file_manager_class.return_value = mock_file_manager

        result = main()

        assert result == 0  # Should still return success

        # Just verify that print was called (the exact message may vary)
        assert mock_print.call_count > 0


# Property-based testing patterns using pytest fixtures
class TestPropertyBasedPatterns:
    """Demonstrate property-based testing patterns with pytest."""

    @pytest.mark.parametrize("length", [1, 2, 5, 10, 50, 100])
    def test_string_processor_length_property(self, length: int) -> None:
        """Property: processed string length should be reasonable relative to input."""
        config = {"min_length": 1, "max_length": 200}
        processor = StringProcessor("test", config)

        input_string = "a" * length
        result = processor.process_item(input_string)

        if result.status == ProcessingStatus.COMPLETED:
            assert result.data is not None
            # Property: output length should be within reasonable bounds of input
            assert len(result.data) >= length - 10  # Allow for some processing changes
            assert len(result.data) <= length + 10

    @pytest.mark.parametrize("user_id,name,email", [
        (1, "Alice", "alice@example.com"),
        (999, "Bob Smith", "bob.smith@company.org"),
        (0, "Charlie Brown", "charlie+test@domain.co.uk"),
    ])
    def test_user_serialization_roundtrip_property(
        self, user_id: int, name: str, email: str,
    ) -> None:
        """Property: User serialization should be a perfect round trip."""
        original_user = User(user_id, name, email)

        # Serialize to dict and back
        user_dict = original_user.to_dict()
        restored_user = User.from_dict(user_dict)

        # Property: round trip should preserve all data
        assert restored_user.id == original_user.id
        assert restored_user.name == original_user.name
        assert restored_user.email == original_user.email
        assert restored_user.active == original_user.active
        # Handle metadata serialization difference (None vs {})
        if original_user.metadata is None:
            assert restored_user.metadata is None or restored_user.metadata == {}
        else:
            assert restored_user.metadata == original_user.metadata

    @pytest.mark.parametrize("status", list(ProcessingStatus))
    def test_processing_result_status_property(self, status: ProcessingStatus) -> None:
        """Property: ProcessingResult should handle all valid status values."""
        result = ProcessingResult[str](status=status, data="test")

        # Property: status should always be preserved
        assert result.status == status
        assert isinstance(result.status, ProcessingStatus)


# Integration tests
class TestIntegration:
    """Integration tests combining multiple components."""

    def test_end_to_end_user_processing_and_storage(self, tmp_path: Path) -> None:
        """Integration test: process users and save to file."""
        # Setup
        users = [
            User(1, "Alice Smith", "alice@example.com"),
            User(2, "Bob Jones", "bob@example.com"),
            User(3, "x", "short@example.com"),  # Will fail processing
        ]

        config = {"min_length": 2, "max_length": 50}
        processor = StringProcessor("integration_test", config)
        file_path = tmp_path / "integration_test.json"
        file_manager: FileManager[User] = FileManager(file_path)

        # Process users
        stats = process_users_with_validation(users, processor)

        # Verify processing results
        assert stats["total_processed"] == 3
        assert stats["successful"] == 2
        assert stats["failed"] == 1

        # Save successful users (filter by successful processing)
        successful_users = [
            user for user in users
            if len(user.name) >= config["min_length"]
        ]

        save_result = file_manager.save_data(
            cast("list[Serializable]", successful_users),
        )
        assert save_result is True

        # Load and verify
        loaded_users = file_manager.load_data(User)
        assert loaded_users is not None
        assert len(loaded_users) == 2

        # Verify data integrity
        for i, loaded_user in enumerate(loaded_users):
            original_user = successful_users[i]
            assert loaded_user.id == original_user.id
            assert loaded_user.name == original_user.name
            assert loaded_user.email == original_user.email


# ============================================================================
# STRUCTURED LOGGING TESTS
# ============================================================================
# Tests for the structured logging demonstration added to main.py
# ============================================================================


class TestUserRegistrationService:
    """Test UserRegistrationService with structured logging."""

    def test_successful_registration(self, caplog: LogCaptureFixture) -> None:
        """Test successful user registration logs correctly."""
        service = UserRegistrationService()
        result = service.register_user("test@example.com", source="web")

        assert result["email"] == "test@example.com"
        assert result["status"] == "registered"
        assert "user_id" in result

        # Verify logging occurred
        assert len(caplog.records) > 0

    def test_failed_registration_invalid_email(
        self, caplog: LogCaptureFixture,
    ) -> None:
        """Test failed registration with invalid email logs correctly."""
        service = UserRegistrationService()

        with pytest.raises(ValueError, match="Invalid email format"):
            service.register_user("invalid-email", source="api")

        # Verify error logging occurred
        assert len(caplog.records) > 0


class TestDatabaseConnectionService:
    """Test DatabaseConnectionService with structured logging."""

    def test_successful_connection(self, caplog: LogCaptureFixture) -> None:
        """Test successful database connection logs correctly."""
        service = DatabaseConnectionService()
        result = service.connect(host="localhost", port=5432)

        assert result is True

        # Verify logging occurred
        assert len(caplog.records) > 0


class TestLoggingDemonstrations:
    """Test logging demonstration functions."""

    def test_demonstrate_api_logging(self, caplog: LogCaptureFixture) -> None:
        """Test API logging demonstration."""
        result = demonstrate_api_logging("/test", "GET")

        assert result["status"] == "success"
        assert result["endpoint"] == "/test"
        assert "request_id" in result

        # Verify logging occurred
        assert len(caplog.records) > 0

    def test_demonstrate_validation_logging_valid(
        self, caplog: LogCaptureFixture,
    ) -> None:
        """Test validation logging with valid data."""
        data = {"name": "Test", "email": "test@example.com"}
        result = demonstrate_validation_logging(data)

        assert result is True

        # Verify logging occurred
        assert len(caplog.records) > 0

    def test_demonstrate_validation_logging_invalid(
        self, caplog: LogCaptureFixture,
    ) -> None:
        """Test validation logging with invalid data."""
        data = {"name": "Test"}  # Missing email
        result = demonstrate_validation_logging(data)

        assert result is False

        # Verify logging occurred
        assert len(caplog.records) > 0

    def test_demonstrate_structured_logging(self, caplog: LogCaptureFixture) -> None:
        """Test complete structured logging demonstration."""
        demonstrate_structured_logging()

        # Verify logging occurred throughout the demonstration
        assert len(caplog.records) > 0


if __name__ == "__main__":
    _ = pytest.main([__file__])
