---
inclusion: fileMatch
fileMatchPattern: '*service*.py'
---

# Service Class Patterns

You are working on a SERVICE class. Services have specific requirements for logging, testing, and structure.

---

## Service Class Template

```python
"""
Service module for [domain] operations.

This module provides [description of what the service does].
"""

from typing import Optional

from grins_platform.logging import LoggerMixin


class MyService(LoggerMixin):
    """Service for handling [domain] operations.
    
    This service provides methods for [list main capabilities].
    
    Attributes:
        DOMAIN: Logging domain for this service
    
    Example:
        >>> service = MyService()
        >>> result = service.create_item(data)
        >>> print(result.id)
    """
    
    DOMAIN = "business"  # Options: user, database, api, validation, business, system
    
    def __init__(self, dependency: Optional[Dependency] = None) -> None:
        """Initialize the service.
        
        Args:
            dependency: Optional dependency injection
        """
        super().__init__()
        self.dependency = dependency or DefaultDependency()
        self.log_started("initialization")
        self.log_completed("initialization")
    
    def create_item(self, data: CreateItemRequest) -> Item:
        """Create a new item.
        
        Args:
            data: Item creation request data
        
        Returns:
            Created item with generated ID
        
        Raises:
            ValidationError: If data is invalid
            ServiceError: If creation fails
        """
        self.log_started("create_item", data_type=type(data).__name__)
        
        try:
            # Validation
            self._validate_create_request(data)
            self.log_validated("create_item", fields=list(data.__dict__.keys()))
            
            # Business logic
            item = self._build_item(data)
            saved_item = self.dependency.save(item)
            
            self.log_completed("create_item", item_id=saved_item.id)
            return saved_item
            
        except ValidationError as e:
            self.log_rejected("create_item", reason=str(e))
            raise
        except Exception as e:
            self.log_failed("create_item", error=e)
            raise ServiceError(f"Failed to create item: {e}") from e
    
    def get_item(self, item_id: str) -> Optional[Item]:
        """Get an item by ID.
        
        Args:
            item_id: Unique item identifier
        
        Returns:
            Item if found, None otherwise
        """
        self.log_started("get_item", item_id=item_id)
        
        try:
            item = self.dependency.find_by_id(item_id)
            
            if item is None:
                self.log_completed("get_item", item_id=item_id, found=False)
                return None
            
            self.log_completed("get_item", item_id=item_id, found=True)
            return item
            
        except Exception as e:
            self.log_failed("get_item", error=e, item_id=item_id)
            raise ServiceError(f"Failed to get item: {e}") from e
    
    def update_item(self, item_id: str, data: UpdateItemRequest) -> Item:
        """Update an existing item.
        
        Args:
            item_id: Unique item identifier
            data: Update request data
        
        Returns:
            Updated item
        
        Raises:
            NotFoundError: If item doesn't exist
            ValidationError: If data is invalid
            ServiceError: If update fails
        """
        self.log_started("update_item", item_id=item_id)
        
        try:
            # Check existence
            existing = self.dependency.find_by_id(item_id)
            if existing is None:
                self.log_rejected("update_item", reason="not_found", item_id=item_id)
                raise NotFoundError(f"Item {item_id} not found")
            
            # Validation
            self._validate_update_request(data)
            self.log_validated("update_item", item_id=item_id)
            
            # Update
            updated_item = self._apply_updates(existing, data)
            saved_item = self.dependency.save(updated_item)
            
            self.log_completed("update_item", item_id=item_id)
            return saved_item
            
        except (NotFoundError, ValidationError):
            raise
        except Exception as e:
            self.log_failed("update_item", error=e, item_id=item_id)
            raise ServiceError(f"Failed to update item: {e}") from e
    
    def delete_item(self, item_id: str) -> bool:
        """Delete an item.
        
        Args:
            item_id: Unique item identifier
        
        Returns:
            True if deleted, False if not found
        """
        self.log_started("delete_item", item_id=item_id)
        
        try:
            deleted = self.dependency.delete(item_id)
            
            if not deleted:
                self.log_completed("delete_item", item_id=item_id, deleted=False)
                return False
            
            self.log_completed("delete_item", item_id=item_id, deleted=True)
            return True
            
        except Exception as e:
            self.log_failed("delete_item", error=e, item_id=item_id)
            raise ServiceError(f"Failed to delete item: {e}") from e
    
    def _validate_create_request(self, data: CreateItemRequest) -> None:
        """Validate creation request data."""
        if not data.name:
            raise ValidationError("Name is required")
        if len(data.name) > 100:
            raise ValidationError("Name too long (max 100 characters)")
    
    def _validate_update_request(self, data: UpdateItemRequest) -> None:
        """Validate update request data."""
        if data.name is not None and len(data.name) > 100:
            raise ValidationError("Name too long (max 100 characters)")
    
    def _build_item(self, data: CreateItemRequest) -> Item:
        """Build item from creation request."""
        return Item(
            id=generate_id(),
            name=data.name,
            created_at=datetime.utcnow(),
        )
    
    def _apply_updates(self, item: Item, data: UpdateItemRequest) -> Item:
        """Apply updates to existing item."""
        if data.name is not None:
            item.name = data.name
        item.updated_at = datetime.utcnow()
        return item
```

---

## Service Testing Template

```python
"""Tests for MyService."""

import pytest
from unittest.mock import Mock, patch

from grins_platform.my_service import MyService, ServiceError, ValidationError, NotFoundError


class TestMyService:
    """Test suite for MyService."""
    
    @pytest.fixture
    def mock_dependency(self) -> Mock:
        """Create mock dependency."""
        return Mock()
    
    @pytest.fixture
    def service(self, mock_dependency: Mock) -> MyService:
        """Create service instance with mock dependency."""
        return MyService(dependency=mock_dependency)
    
    # --- Create Tests ---
    
    def test_create_item_with_valid_data_returns_item(
        self, service: MyService, mock_dependency: Mock
    ) -> None:
        """Test successful item creation."""
        # Arrange
        data = CreateItemRequest(name="Test Item")
        expected_item = Item(id="123", name="Test Item")
        mock_dependency.save.return_value = expected_item
        
        # Act
        result = service.create_item(data)
        
        # Assert
        assert result.id == "123"
        assert result.name == "Test Item"
        mock_dependency.save.assert_called_once()
    
    def test_create_item_with_empty_name_raises_validation_error(
        self, service: MyService
    ) -> None:
        """Test that empty name raises ValidationError."""
        data = CreateItemRequest(name="")
        
        with pytest.raises(ValidationError, match="Name is required"):
            service.create_item(data)
    
    def test_create_item_with_long_name_raises_validation_error(
        self, service: MyService
    ) -> None:
        """Test that name over 100 chars raises ValidationError."""
        data = CreateItemRequest(name="x" * 101)
        
        with pytest.raises(ValidationError, match="Name too long"):
            service.create_item(data)
    
    def test_create_item_logs_started_and_completed(
        self, service: MyService, mock_dependency: Mock, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that create_item logs appropriate events."""
        data = CreateItemRequest(name="Test")
        mock_dependency.save.return_value = Item(id="123", name="Test")
        
        service.create_item(data)
        
        # Verify logging occurred
        assert len(caplog.records) > 0
    
    # --- Get Tests ---
    
    def test_get_item_with_existing_id_returns_item(
        self, service: MyService, mock_dependency: Mock
    ) -> None:
        """Test getting existing item."""
        expected_item = Item(id="123", name="Test")
        mock_dependency.find_by_id.return_value = expected_item
        
        result = service.get_item("123")
        
        assert result is not None
        assert result.id == "123"
    
    def test_get_item_with_nonexistent_id_returns_none(
        self, service: MyService, mock_dependency: Mock
    ) -> None:
        """Test getting non-existent item."""
        mock_dependency.find_by_id.return_value = None
        
        result = service.get_item("nonexistent")
        
        assert result is None
    
    # --- Update Tests ---
    
    def test_update_item_with_valid_data_returns_updated_item(
        self, service: MyService, mock_dependency: Mock
    ) -> None:
        """Test successful item update."""
        existing = Item(id="123", name="Old Name")
        mock_dependency.find_by_id.return_value = existing
        mock_dependency.save.return_value = Item(id="123", name="New Name")
        
        data = UpdateItemRequest(name="New Name")
        result = service.update_item("123", data)
        
        assert result.name == "New Name"
    
    def test_update_item_with_nonexistent_id_raises_not_found(
        self, service: MyService, mock_dependency: Mock
    ) -> None:
        """Test updating non-existent item."""
        mock_dependency.find_by_id.return_value = None
        
        with pytest.raises(NotFoundError):
            service.update_item("nonexistent", UpdateItemRequest(name="New"))
    
    # --- Delete Tests ---
    
    def test_delete_item_with_existing_id_returns_true(
        self, service: MyService, mock_dependency: Mock
    ) -> None:
        """Test successful deletion."""
        mock_dependency.delete.return_value = True
        
        result = service.delete_item("123")
        
        assert result is True
    
    def test_delete_item_with_nonexistent_id_returns_false(
        self, service: MyService, mock_dependency: Mock
    ) -> None:
        """Test deleting non-existent item."""
        mock_dependency.delete.return_value = False
        
        result = service.delete_item("nonexistent")
        
        assert result is False
    
    # --- Error Handling Tests ---
    
    def test_create_item_with_dependency_error_raises_service_error(
        self, service: MyService, mock_dependency: Mock
    ) -> None:
        """Test that dependency errors are wrapped in ServiceError."""
        mock_dependency.save.side_effect = Exception("Database error")
        
        with pytest.raises(ServiceError, match="Failed to create item"):
            service.create_item(CreateItemRequest(name="Test"))
```

---

## Service Logging Checklist

When writing a service, ensure:

- [ ] Class inherits from `LoggerMixin`
- [ ] `DOMAIN` class attribute is set appropriately
- [ ] `__init__` calls `super().__init__()`
- [ ] Each public method logs `_started` at entry
- [ ] Each public method logs `_completed` on success
- [ ] Validation failures log `_rejected` with reason
- [ ] Exceptions log `_failed` with error details
- [ ] Log messages include relevant context (IDs, counts, etc.)

---

## Service Testing Checklist

When testing a service, ensure:

- [ ] Test file exists at `tests/test_{service_name}.py`
- [ ] Fixtures for mock dependencies
- [ ] Fixture for service instance
- [ ] Tests for successful operations
- [ ] Tests for validation errors
- [ ] Tests for not found errors
- [ ] Tests for dependency errors
- [ ] Tests for logging (using caplog)
- [ ] All tests pass with `uv run pytest -v`
