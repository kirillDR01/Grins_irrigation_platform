---
inclusion: fileMatch
fileMatchPattern: '*{api,routes,endpoints,router}*.py'
---

# API Endpoint Patterns

## Endpoint Template
```python
router = APIRouter(prefix="/items", tags=["items"])
logger = get_logger(__name__)

@router.post("/", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
async def create_item(request: CreateItemRequest, service: MyService = Depends(get_service)) -> ItemResponse:
    request_id = set_request_id()
    DomainLogger.api_event(logger, "create_item", "started", request_id=request_id, name=request.name)
    try:
        # Validate
        DomainLogger.validation_event(logger, "create_item_request", "started", request_id=request_id)
        # ... validation logic ...
        DomainLogger.validation_event(logger, "create_item_request", "validated", request_id=request_id)

        # Process
        item = service.create_item(request)
        DomainLogger.api_event(logger, "create_item", "completed", request_id=request_id, item_id=item.id, status_code=201)
        return ItemResponse(...)

    except ValidationError as e:
        DomainLogger.api_event(logger, "create_item", "failed", request_id=request_id, error=str(e), status_code=400)
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        DomainLogger.api_event(logger, "create_item", "failed", request_id=request_id, error=str(e), status_code=500)
        raise HTTPException(status_code=500, detail="Internal server error") from e
    finally:
        clear_request_id()
```

All CRUD endpoints (GET, PUT, DELETE) follow same pattern: set_request_id → log started → try/except with logging → clear_request_id in finally.

GET: return 404 if not found. PUT: catch NotFoundError→404, ValidationError→400. DELETE: return 204, 404 if not found.

## Request/Response Models
```python
class CreateItemRequest(BaseModel):
    name: str
    description: Optional[str] = None

class ItemResponse(BaseModel):
    id: str
    name: str
    created_at: str
```

## Dependency Injection
```python
def get_service() -> MyService:
    return MyService()
```

## Testing
```python
@pytest.fixture
def client_with_mock_service(mock_service):
    app.dependency_overrides[get_service] = lambda: mock_service
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()

class TestCreateItem:
    def test_valid_data_returns_201(self, client_with_mock_service, mock_service):
        mock_service.create_item.return_value = Item(id="123", name="Test", ...)
        response = client_with_mock_service.post("/items/", json={"name": "Test"})
        assert response.status_code == 201

    def test_empty_name_returns_400(self, client_with_mock_service):
        response = client_with_mock_service.post("/items/", json={"name": ""})
        assert response.status_code == 400
```

## Checklist
- set_request_id() at start, clear_request_id() in finally
- DomainLogger.api_event: _started, _completed, _failed with status codes
- DomainLogger.validation_event for input validation
- Never log passwords/tokens
- Tests: 201/200/204 success + 400 validation + 404 not found + 500 server error
