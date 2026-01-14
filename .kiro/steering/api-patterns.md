---
inclusion: fileMatch
fileMatchPattern: '*{api,routes,endpoints,router}*.py'
---

# API Endpoint Patterns

You are working on API ENDPOINTS. APIs have specific requirements for request correlation, validation logging, and testing.

---

## API Endpoint Template (FastAPI)

```python
"""
API endpoints for [domain] operations.

This module provides REST API endpoints for [description].
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from grins_platform.logging import get_logger, set_request_id, clear_request_id, DomainLogger
from grins_platform.services.my_service import MyService, ValidationError, NotFoundError


router = APIRouter(prefix="/items", tags=["items"])
logger = get_logger(__name__)


# --- Request/Response Models ---

class CreateItemRequest(BaseModel):
    """Request model for creating an item."""
    name: str
    description: Optional[str] = None


class UpdateItemRequest(BaseModel):
    """Request model for updating an item."""
    name: Optional[str] = None
    description: Optional[str] = None


class ItemResponse(BaseModel):
    """Response model for item data."""
    id: str
    name: str
    description: Optional[str]
    created_at: str


class ErrorResponse(BaseModel):
    """Response model for errors."""
    detail: str
    error_code: Optional[str] = None


# --- Dependency Injection ---

def get_service() -> MyService:
    """Get service instance."""
    return MyService()


# --- Endpoints ---

@router.post(
    "/",
    response_model=ItemResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse, "description": "Validation error"},
        500: {"model": ErrorResponse, "description": "Internal error"},
    },
)
async def create_item(
    request: CreateItemRequest,
    service: MyService = Depends(get_service),
) -> ItemResponse:
    """Create a new item.
    
    Args:
        request: Item creation data
        service: Injected service instance
    
    Returns:
        Created item data
    
    Raises:
        HTTPException: On validation or processing errors
    """
    request_id = set_request_id()
    
    DomainLogger.api_event(
        logger, "create_item", "started",
        request_id=request_id,
        name=request.name,
    )
    
    try:
        # Validate request
        DomainLogger.validation_event(
            logger, "create_item_request", "started",
            request_id=request_id,
        )
        
        if not request.name.strip():
            DomainLogger.validation_event(
                logger, "create_item_request", "rejected",
                request_id=request_id,
                reason="empty_name",
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Name cannot be empty",
            )
        
        DomainLogger.validation_event(
            logger, "create_item_request", "validated",
            request_id=request_id,
        )
        
        # Process request
        item = service.create_item(request)
        
        DomainLogger.api_event(
            logger, "create_item", "completed",
            request_id=request_id,
            item_id=item.id,
            status_code=201,
        )
        
        return ItemResponse(
            id=item.id,
            name=item.name,
            description=item.description,
            created_at=item.created_at.isoformat(),
        )
        
    except ValidationError as e:
        DomainLogger.api_event(
            logger, "create_item", "failed",
            request_id=request_id,
            error=str(e),
            status_code=400,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
        
    except Exception as e:
        DomainLogger.api_event(
            logger, "create_item", "failed",
            request_id=request_id,
            error=str(e),
            error_type=type(e).__name__,
            status_code=500,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        ) from e
        
    finally:
        clear_request_id()


@router.get(
    "/{item_id}",
    response_model=ItemResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Item not found"},
    },
)
async def get_item(
    item_id: str,
    service: MyService = Depends(get_service),
) -> ItemResponse:
    """Get an item by ID.
    
    Args:
        item_id: Unique item identifier
        service: Injected service instance
    
    Returns:
        Item data
    
    Raises:
        HTTPException: If item not found
    """
    request_id = set_request_id()
    
    DomainLogger.api_event(
        logger, "get_item", "started",
        request_id=request_id,
        item_id=item_id,
    )
    
    try:
        item = service.get_item(item_id)
        
        if item is None:
            DomainLogger.api_event(
                logger, "get_item", "completed",
                request_id=request_id,
                item_id=item_id,
                found=False,
                status_code=404,
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Item {item_id} not found",
            )
        
        DomainLogger.api_event(
            logger, "get_item", "completed",
            request_id=request_id,
            item_id=item_id,
            found=True,
            status_code=200,
        )
        
        return ItemResponse(
            id=item.id,
            name=item.name,
            description=item.description,
            created_at=item.created_at.isoformat(),
        )
        
    except HTTPException:
        raise
        
    except Exception as e:
        DomainLogger.api_event(
            logger, "get_item", "failed",
            request_id=request_id,
            item_id=item_id,
            error=str(e),
            status_code=500,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        ) from e
        
    finally:
        clear_request_id()


@router.put(
    "/{item_id}",
    response_model=ItemResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Validation error"},
        404: {"model": ErrorResponse, "description": "Item not found"},
    },
)
async def update_item(
    item_id: str,
    request: UpdateItemRequest,
    service: MyService = Depends(get_service),
) -> ItemResponse:
    """Update an existing item.
    
    Args:
        item_id: Unique item identifier
        request: Update data
        service: Injected service instance
    
    Returns:
        Updated item data
    
    Raises:
        HTTPException: On validation, not found, or processing errors
    """
    request_id = set_request_id()
    
    DomainLogger.api_event(
        logger, "update_item", "started",
        request_id=request_id,
        item_id=item_id,
    )
    
    try:
        item = service.update_item(item_id, request)
        
        DomainLogger.api_event(
            logger, "update_item", "completed",
            request_id=request_id,
            item_id=item_id,
            status_code=200,
        )
        
        return ItemResponse(
            id=item.id,
            name=item.name,
            description=item.description,
            created_at=item.created_at.isoformat(),
        )
        
    except NotFoundError:
        DomainLogger.api_event(
            logger, "update_item", "failed",
            request_id=request_id,
            item_id=item_id,
            reason="not_found",
            status_code=404,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item {item_id} not found",
        )
        
    except ValidationError as e:
        DomainLogger.api_event(
            logger, "update_item", "failed",
            request_id=request_id,
            item_id=item_id,
            error=str(e),
            status_code=400,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
        
    except Exception as e:
        DomainLogger.api_event(
            logger, "update_item", "failed",
            request_id=request_id,
            item_id=item_id,
            error=str(e),
            status_code=500,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        ) from e
        
    finally:
        clear_request_id()


@router.delete(
    "/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        404: {"model": ErrorResponse, "description": "Item not found"},
    },
)
async def delete_item(
    item_id: str,
    service: MyService = Depends(get_service),
) -> None:
    """Delete an item.
    
    Args:
        item_id: Unique item identifier
        service: Injected service instance
    
    Raises:
        HTTPException: If item not found
    """
    request_id = set_request_id()
    
    DomainLogger.api_event(
        logger, "delete_item", "started",
        request_id=request_id,
        item_id=item_id,
    )
    
    try:
        deleted = service.delete_item(item_id)
        
        if not deleted:
            DomainLogger.api_event(
                logger, "delete_item", "failed",
                request_id=request_id,
                item_id=item_id,
                reason="not_found",
                status_code=404,
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Item {item_id} not found",
            )
        
        DomainLogger.api_event(
            logger, "delete_item", "completed",
            request_id=request_id,
            item_id=item_id,
            status_code=204,
        )
        
    except HTTPException:
        raise
        
    except Exception as e:
        DomainLogger.api_event(
            logger, "delete_item", "failed",
            request_id=request_id,
            item_id=item_id,
            error=str(e),
            status_code=500,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        ) from e
        
    finally:
        clear_request_id()
```

---

## API Testing Template

```python
"""Tests for item API endpoints."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch

from grins_platform.main import app
from grins_platform.api.items import get_service


@pytest.fixture
def client() -> TestClient:
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_service() -> Mock:
    """Create mock service."""
    return Mock()


@pytest.fixture
def client_with_mock_service(mock_service: Mock) -> TestClient:
    """Create test client with mocked service."""
    app.dependency_overrides[get_service] = lambda: mock_service
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


class TestCreateItem:
    """Tests for POST /items endpoint."""
    
    def test_create_item_with_valid_data_returns_201(
        self, client_with_mock_service: TestClient, mock_service: Mock
    ) -> None:
        """Test successful item creation."""
        mock_service.create_item.return_value = Item(
            id="123",
            name="Test Item",
            description=None,
            created_at=datetime.utcnow(),
        )
        
        response = client_with_mock_service.post(
            "/items/",
            json={"name": "Test Item"},
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["id"] == "123"
        assert data["name"] == "Test Item"
    
    def test_create_item_with_empty_name_returns_400(
        self, client_with_mock_service: TestClient
    ) -> None:
        """Test that empty name returns 400."""
        response = client_with_mock_service.post(
            "/items/",
            json={"name": ""},
        )
        
        assert response.status_code == 400
        assert "empty" in response.json()["detail"].lower()
    
    def test_create_item_with_service_error_returns_500(
        self, client_with_mock_service: TestClient, mock_service: Mock
    ) -> None:
        """Test that service errors return 500."""
        mock_service.create_item.side_effect = Exception("Database error")
        
        response = client_with_mock_service.post(
            "/items/",
            json={"name": "Test"},
        )
        
        assert response.status_code == 500


class TestGetItem:
    """Tests for GET /items/{item_id} endpoint."""
    
    def test_get_item_with_existing_id_returns_200(
        self, client_with_mock_service: TestClient, mock_service: Mock
    ) -> None:
        """Test getting existing item."""
        mock_service.get_item.return_value = Item(
            id="123",
            name="Test",
            description=None,
            created_at=datetime.utcnow(),
        )
        
        response = client_with_mock_service.get("/items/123")
        
        assert response.status_code == 200
        assert response.json()["id"] == "123"
    
    def test_get_item_with_nonexistent_id_returns_404(
        self, client_with_mock_service: TestClient, mock_service: Mock
    ) -> None:
        """Test getting non-existent item."""
        mock_service.get_item.return_value = None
        
        response = client_with_mock_service.get("/items/nonexistent")
        
        assert response.status_code == 404


class TestUpdateItem:
    """Tests for PUT /items/{item_id} endpoint."""
    
    def test_update_item_with_valid_data_returns_200(
        self, client_with_mock_service: TestClient, mock_service: Mock
    ) -> None:
        """Test successful item update."""
        mock_service.update_item.return_value = Item(
            id="123",
            name="Updated",
            description=None,
            created_at=datetime.utcnow(),
        )
        
        response = client_with_mock_service.put(
            "/items/123",
            json={"name": "Updated"},
        )
        
        assert response.status_code == 200
        assert response.json()["name"] == "Updated"
    
    def test_update_item_with_nonexistent_id_returns_404(
        self, client_with_mock_service: TestClient, mock_service: Mock
    ) -> None:
        """Test updating non-existent item."""
        mock_service.update_item.side_effect = NotFoundError("Not found")
        
        response = client_with_mock_service.put(
            "/items/nonexistent",
            json={"name": "Updated"},
        )
        
        assert response.status_code == 404


class TestDeleteItem:
    """Tests for DELETE /items/{item_id} endpoint."""
    
    def test_delete_item_with_existing_id_returns_204(
        self, client_with_mock_service: TestClient, mock_service: Mock
    ) -> None:
        """Test successful deletion."""
        mock_service.delete_item.return_value = True
        
        response = client_with_mock_service.delete("/items/123")
        
        assert response.status_code == 204
    
    def test_delete_item_with_nonexistent_id_returns_404(
        self, client_with_mock_service: TestClient, mock_service: Mock
    ) -> None:
        """Test deleting non-existent item."""
        mock_service.delete_item.return_value = False
        
        response = client_with_mock_service.delete("/items/nonexistent")
        
        assert response.status_code == 404
```

---

## API Logging Checklist

When writing API endpoints, ensure:

- [ ] `set_request_id()` called at start of each endpoint
- [ ] `clear_request_id()` called in `finally` block
- [ ] `DomainLogger.api_event` logs `_started` at entry
- [ ] `DomainLogger.api_event` logs `_completed` on success with status code
- [ ] `DomainLogger.api_event` logs `_failed` on errors with status code
- [ ] Validation logging with `DomainLogger.validation_event`
- [ ] Request ID included in all log events
- [ ] Sensitive data NOT logged (passwords, tokens)

---

## API Testing Checklist

When testing API endpoints, ensure:

- [ ] Test file exists at `tests/test_{api_name}.py`
- [ ] TestClient fixture for making requests
- [ ] Mock service fixture for dependency injection
- [ ] Tests for successful responses (200, 201, 204)
- [ ] Tests for validation errors (400)
- [ ] Tests for not found errors (404)
- [ ] Tests for server errors (500)
- [ ] All tests pass with `uv run pytest -v`
