# Code Quality Standards

## CRITICAL: Quality by Default

Every code change MUST include logging, testing, pass quality checks, AND be validated end-to-end.
This is not optional. These are requirements for task completion.

**Fundamental Principle: If you can't demonstrate it working, it's not done.**

Unit tests prove code correctness. End-to-end validation proves the feature works as users experience it.

---

## 1. Structured Logging (MANDATORY)

### Framework
- Use `structlog` with hybrid dotted namespace pattern
- Import from: `from grins_platform.logging import LoggerMixin, get_logger`

### Namespace Pattern
```
{domain}.{component}.{action}_{state}
```

**Domains**: user, database, api, validation, business, system
**States**: _started, _completed, _failed, _validated, _rejected

### Class-Based Logging (Services, Handlers)
```python
from grins_platform.logging import LoggerMixin

class MyService(LoggerMixin):
    DOMAIN = "business"  # Set appropriate domain
    
    def operation(self, param: str) -> Result:
        self.log_started("operation", param=param)
        try:
            result = self._do_work(param)
            self.log_completed("operation", result_id=result.id)
            return result
        except ValidationError as e:
            self.log_rejected("operation", reason=str(e), param=param)
            raise
        except Exception as e:
            self.log_failed("operation", error=e, param=param)
            raise
```

### Function-Based Logging (Utilities, Helpers)
```python
from grins_platform.logging import get_logger, DomainLogger

logger = get_logger(__name__)

def process_data(data: dict) -> Result:
    DomainLogger.api_event(logger, "processing", "started", data_size=len(data))
    try:
        result = transform(data)
        DomainLogger.api_event(logger, "processing", "completed", result_id=result.id)
        return result
    except Exception as e:
        DomainLogger.api_event(logger, "processing", "failed", error=str(e))
        raise
```

### Log Levels
- **DEBUG**: Internal details, query execution, verbose info
- **INFO**: Business operations, API calls, state changes
- **WARNING**: Recoverable issues, deprecations, validation rejections
- **ERROR**: Failures requiring attention, exceptions
- **CRITICAL**: System-level failures, data corruption

### What to Log
- ✅ Service method entry/exit (INFO)
- ✅ External API calls (INFO)
- ✅ Database operations (DEBUG)
- ✅ Validation results (INFO/WARNING)
- ✅ Errors with full context (ERROR)
- ✅ Security events (WARNING/ERROR)

### What NOT to Log
- ❌ Sensitive data (passwords, tokens, PII)
- ❌ Every internal function call
- ❌ High-frequency operations without sampling
- ❌ Redundant information

---

## 2. Three-Tier Testing Strategy (MANDATORY)

Every task MUST include all three tiers of testing. This is not optional.

### The Three Tiers

| Tier | Test Type | Purpose | Dependencies | Marker |
|------|-----------|---------|--------------|--------|
| 1 | **Unit Tests** | Code correctness in isolation | Mocked | `@pytest.mark.unit` |
| 2 | **Functional Tests** | Feature works as user expects | Real infrastructure | `@pytest.mark.functional` |
| 3 | **Integration Tests** | New code works with existing system | Real system | `@pytest.mark.integration` |

### Framework
- Use `pytest` with `pytest-cov`, `pytest-asyncio`
- Run all tests: `uv run pytest -v`
- Run by tier: `uv run pytest -m unit`, `uv run pytest -m functional`, `uv run pytest -m integration`
- Run with coverage: `uv run pytest --cov=src/grins_platform`

### Test File Organization
```
src/grins_platform/tests/
├── __init__.py
├── conftest.py              # Shared fixtures for all test types
├── unit/                    # Tier 1: Isolated tests with mocks
│   ├── __init__.py
│   ├── test_customer_service.py
│   └── test_property_service.py
├── functional/              # Tier 2: Real infrastructure tests
│   ├── __init__.py
│   ├── test_customer_workflows.py
│   └── test_property_workflows.py
└── integration/             # Tier 3: Cross-component tests
    ├── __init__.py
    ├── test_customer_api_integration.py
    └── test_full_lifecycle.py
```

---

### Tier 1: Unit Tests (MANDATORY)

**Purpose**: Test individual functions/methods in isolation with mocked dependencies.

**Characteristics**:
- Fast execution (milliseconds)
- No external dependencies (database, network, filesystem)
- All dependencies are mocked
- Test one thing at a time

**When to Write**: For every public method in services, repositories, and utilities.

**Example**:
```python
@pytest.mark.unit
class TestCustomerService:
    """Unit tests for CustomerService with mocked repository."""
    
    @pytest.fixture
    def mock_repository(self) -> Mock:
        return Mock(spec=CustomerRepository)
    
    @pytest.fixture
    def service(self, mock_repository: Mock) -> CustomerService:
        return CustomerService(mock_repository)
    
    async def test_create_customer_calls_repository(
        self, service: CustomerService, mock_repository: Mock
    ) -> None:
        """Test that create_customer calls repository.create."""
        mock_repository.find_by_phone.return_value = None
        mock_repository.create.return_value = Mock(id=uuid4())
        
        data = CustomerCreate(first_name="John", last_name="Doe", phone="6125551234")
        await service.create_customer(data)
        
        mock_repository.create.assert_called_once()
    
    async def test_create_customer_rejects_duplicate_phone(
        self, service: CustomerService, mock_repository: Mock
    ) -> None:
        """Test that duplicate phone raises DuplicateCustomerError."""
        mock_repository.find_by_phone.return_value = Mock(id=uuid4())
        
        data = CustomerCreate(first_name="John", last_name="Doe", phone="6125551234")
        
        with pytest.raises(DuplicateCustomerError):
            await service.create_customer(data)
```

---

### Tier 2: Functional Tests (MANDATORY)

**Purpose**: Test features as a user would experience them, with real infrastructure.

**Characteristics**:
- Uses real database (PostgreSQL)
- Uses real services (not mocked)
- Tests complete user workflows
- Verifies data persists correctly

**When to Write**: For every feature that a user would interact with.

**Example**:
```python
@pytest.mark.functional
class TestCustomerWorkflows:
    """Functional tests for customer workflows with real database."""
    
    @pytest.fixture
    async def db_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get real database session."""
        async for session in get_db_session():
            yield session
    
    async def test_create_customer_workflow(self, db_session: AsyncSession) -> None:
        """Test complete customer creation as user would experience it."""
        # Arrange
        repo = CustomerRepository(db_session)
        service = CustomerService(repo)
        unique_phone = f"612555{uuid4().int % 10000:04d}"
        
        # Act - Create customer
        data = CustomerCreate(
            first_name="Functional",
            last_name="Test",
            phone=unique_phone,
            email="functional@test.com",
        )
        result = await service.create_customer(data)
        
        # Assert - Customer created with correct data
        assert result.id is not None
        assert result.first_name == "Functional"
        assert result.phone == unique_phone
        
        # Assert - Customer persisted in database
        fetched = await repo.get_by_id(result.id)
        assert fetched is not None
        assert fetched.first_name == "Functional"
        
        # Assert - Defaults applied correctly (Property 5)
        assert result.sms_opt_in is False
        assert result.email_opt_in is False
    
    async def test_duplicate_phone_rejected(self, db_session: AsyncSession) -> None:
        """Test that duplicate phone is rejected as user would experience."""
        repo = CustomerRepository(db_session)
        service = CustomerService(repo)
        unique_phone = f"612555{uuid4().int % 10000:04d}"
        
        # Create first customer
        data1 = CustomerCreate(first_name="First", last_name="User", phone=unique_phone)
        await service.create_customer(data1)
        
        # Try to create second customer with same phone
        data2 = CustomerCreate(first_name="Second", last_name="User", phone=unique_phone)
        
        with pytest.raises(DuplicateCustomerError):
            await service.create_customer(data2)
```

---

### Tier 3: Integration Tests (MANDATORY)

**Purpose**: Verify new code works correctly with existing system components.

**Characteristics**:
- Tests interactions between multiple components
- Uses real database with seeded test data
- Verifies new features don't break existing functionality
- Tests complete API flows end-to-end

**When to Write**: For every task that adds or modifies functionality.

**Example**:
```python
@pytest.mark.integration
class TestCustomerAPIIntegration:
    """Integration tests for customer API with existing system."""
    
    @pytest.fixture
    async def seeded_database(self, db_session: AsyncSession) -> list[Customer]:
        """Seed database with existing customers."""
        repo = CustomerRepository(db_session)
        customers = []
        for i in range(5):
            customer = await repo.create(
                first_name=f"Existing{i}",
                last_name="Customer",
                phone=f"612555{1000 + i}",
            )
            customers.append(customer)
        await db_session.commit()
        return customers
    
    async def test_new_customer_works_with_existing(
        self, client: AsyncClient, seeded_database: list[Customer]
    ) -> None:
        """Test creating new customer doesn't affect existing customers."""
        # Create new customer via API
        response = await client.post("/api/v1/customers", json={
            "first_name": "New",
            "last_name": "Customer",
            "phone": "6125559999",
        })
        assert response.status_code == 201
        
        # Verify existing customers still accessible
        for existing in seeded_database:
            response = await client.get(f"/api/v1/customers/{existing.id}")
            assert response.status_code == 200
            assert response.json()["first_name"] == existing.first_name
    
    async def test_list_includes_new_and_existing(
        self, client: AsyncClient, seeded_database: list[Customer]
    ) -> None:
        """Test list endpoint returns both new and existing customers."""
        # Create new customer
        await client.post("/api/v1/customers", json={
            "first_name": "New",
            "last_name": "Customer", 
            "phone": "6125559999",
        })
        
        # List all customers
        response = await client.get("/api/v1/customers")
        assert response.status_code == 200
        
        data = response.json()
        assert data["total"] == len(seeded_database) + 1
```

---

### Task Testing Sub-Task Pattern

Every major implementation task MUST include a dedicated testing sub-task that covers all three tiers:

```markdown
## Task X: [Feature Name]

- [ ] X.1 Implement [component A]
- [ ] X.2 Implement [component B]
- [ ] X.3 Implement [component C]
- [ ] X.4 Write tests (unit, functional, integration)
      - Unit tests: Test each method in isolation with mocks
      - Functional tests: Test feature workflows with real database
      - Integration tests: Verify works with existing system
```

---

### Coverage Targets

| Component | Unit | Functional | Integration |
|-----------|------|------------|-------------|
| Services | 85%+ | 80%+ | 70%+ |
| API endpoints | 80%+ | 85%+ | 80%+ |
| Repositories | 80%+ | 70%+ | 60%+ |
| Models | 60%+ | N/A | N/A |

### Test Naming Convention
```python
# Unit tests
def test_{method}_with_{condition}_returns_{expected}():
def test_{method}_with_{condition}_raises_{exception}():

# Functional tests  
def test_{workflow}_as_user_would_experience():
def test_{feature}_with_real_database():

# Integration tests
def test_{feature}_works_with_existing_{component}():
def test_{new_feature}_does_not_break_{existing_feature}():
```

### Running Tests by Tier
```bash
# All tests
uv run pytest -v

# Unit tests only (fast)
uv run pytest -m unit -v

# Functional tests only (requires database)
uv run pytest -m functional -v

# Integration tests only (requires full system)
uv run pytest -m integration -v

# With coverage
uv run pytest --cov=src/grins_platform --cov-report=term-missing
```

---

## 3. Type Safety (MANDATORY)

### Requirements
- All functions MUST have type hints
- All return types MUST be specified
- No implicit `Any` allowed
- Must pass both MyPy and Pyright with zero errors

### Type Hint Patterns
```python
from typing import Optional, Union

def process(data: dict[str, Any], options: Optional[ProcessOptions] = None) -> ProcessResult:
    """Process data with optional configuration."""
    ...

def get_user(user_id: int) -> Optional[User]:
    """Get user by ID, returns None if not found."""
    ...

def validate(value: Union[str, int]) -> bool:
    """Validate string or integer value."""
    ...
```

### Running Type Checks
```bash
uv run mypy src/grins_platform/
uv run pyright src/grins_platform/
```

---

## 4. Error Handling (MANDATORY)

### Custom Exceptions
```python
class ServiceError(Exception):
    """Base exception for service errors."""
    pass

class ValidationError(ServiceError):
    """Raised when validation fails."""
    pass

class NotFoundError(ServiceError):
    """Raised when resource is not found."""
    pass
```

### Error Handling Pattern
```python
def operation(self, data: dict) -> Result:
    self.log_started("operation", data_keys=list(data.keys()))
    
    try:
        # Validation
        if not self._validate(data):
            self.log_rejected("operation", reason="validation_failed")
            raise ValidationError("Invalid data")
        
        # Processing
        result = self._process(data)
        self.log_completed("operation", result_id=result.id)
        return result
        
    except ValidationError:
        # Already logged, re-raise
        raise
    except ExternalServiceError as e:
        self.log_failed("operation", error=e, service="external")
        raise ServiceError(f"External service failed: {e}") from e
    except Exception as e:
        self.log_failed("operation", error=e)
        raise ServiceError(f"Unexpected error: {e}") from e
```

---

## 5. Code Quality (MANDATORY)

### Linting
- Use Ruff with 800+ rules
- Must pass with zero violations
- Run: `uv run ruff check src/`
- Auto-fix: `uv run ruff check --fix src/`

### Formatting
- Line length: 88 characters
- Use Ruff formatter
- Run: `uv run ruff format src/`

### Documentation
- All public functions need docstrings
- Use Google-style docstrings
- Include Args, Returns, Raises sections

```python
def process_payment(amount: Decimal, currency: str) -> PaymentResult:
    """Process a payment transaction.
    
    Args:
        amount: Payment amount in smallest currency unit
        currency: ISO 4217 currency code (e.g., "USD")
    
    Returns:
        PaymentResult with transaction ID and status
    
    Raises:
        ValidationError: If amount is negative or currency is invalid
        PaymentError: If payment processing fails
    """
```

---

## 6. Quality Workflow (MANDATORY)

### FUNDAMENTAL PRINCIPLE: If You Can't Demonstrate It Working, It's Not Done

Unit tests verify code correctness in isolation. End-to-end validation proves the feature works as a user would experience it. Both are required.

### The 6-Step Process

Every task follows this workflow:

```
1. WRITE CODE
   ├── Include LoggerMixin for classes
   ├── Add logging to key operations
   ├── Add type hints to all functions
   └── Follow patterns from steering files

2. WRITE TESTS
   ├── Create test file in tests/ directory
   ├── Write unit tests for public methods
   ├── Write integration tests for workflows
   └── Write edge case tests

3. RUN QUALITY CHECKS
   ├── uv run ruff check --fix src/
   ├── uv run mypy src/
   ├── uv run pyright src/
   └── uv run pytest -v

4. FIX ISSUES
   ├── Fix all Ruff violations
   ├── Fix all type errors
   ├── Fix all test failures
   └── Iterate until zero errors

5. VALIDATE END-TO-END
   ├── Start required infrastructure (database, services)
   ├── Test the feature as a user would use it
   ├── Verify real data flows through the system
   └── Document validation steps performed

6. REPORT COMPLETION
   ├── Summary of what was created
   ├── Test results (X/X passing)
   ├── Quality check results (zero violations)
   ├── End-to-end validation results
   └── Ready for use
```

### End-to-End Validation Strategies

Choose the appropriate validation strategy based on what you're implementing:

| Change Type | Validation Strategy | Example Commands |
|-------------|---------------------|------------------|
| **API Endpoints** | Start server + database, test via curl/httpie | `docker-compose up -d db` → `uv run uvicorn` → `curl localhost:8000/api/v1/...` |
| **Database/Migrations** | Run migrations, verify tables exist, test queries | `alembic upgrade head` → verify schema → test CRUD |
| **Services/Business Logic** | Integration tests with real dependencies | Start database, run service methods, verify results |
| **CLI Tools/Scripts** | Run command, verify output and side effects | Execute script, check output, verify files/data created |
| **Configuration Changes** | Start application, verify config loaded correctly | Start app, check logs for config values, test affected features |
| **Background Jobs/Workers** | Start worker, trigger job, verify completion | Start Celery worker, enqueue task, check results |
| **External Integrations** | Test with sandbox/staging APIs | Configure test credentials, make real API calls |

### Validation Checklist by Component

**API Endpoints:**
- [ ] Server starts without errors
- [ ] Endpoint responds to requests
- [ ] Request validation works (reject bad input)
- [ ] Response format matches schema
- [ ] Database operations persist correctly
- [ ] Error responses are appropriate

**Database Changes:**
- [ ] Migrations run successfully
- [ ] Tables/columns created correctly
- [ ] Constraints enforced (unique, foreign keys)
- [ ] Indexes created for performance
- [ ] Rollback works if needed

**Services:**
- [ ] Service instantiates correctly
- [ ] Methods execute with real data
- [ ] Errors handled appropriately
- [ ] Logging captures key events
- [ ] Side effects occur as expected

**Configuration:**
- [ ] Application starts with new config
- [ ] Config values loaded correctly
- [ ] Invalid config rejected with clear error
- [ ] Defaults work when config omitted

### Task Completion Criteria

A task is NOT complete until:
- ✅ Code has appropriate logging
- ✅ Tests exist and pass
- ✅ Ruff reports zero violations
- ✅ MyPy reports zero errors
- ✅ Pyright reports zero errors
- ✅ All tests pass
- ✅ End-to-end validation performed
- ✅ Feature tested as a user would use it

---

## 7. Quick Reference

### Imports
```python
# Logging
from grins_platform.logging import LoggerMixin, get_logger, DomainLogger
from grins_platform.logging import set_request_id, clear_request_id

# Testing
import pytest
from unittest.mock import Mock, patch
```

### Commands
```bash
# Quality checks
uv run ruff check --fix src/
uv run mypy src/
uv run pyright src/
uv run pytest -v

# Full validation (tests only)
uv run ruff check src/ && uv run mypy src/ && uv run pyright src/ && uv run pytest -v

# End-to-end validation (API)
docker-compose up -d db                    # Start database
uv run alembic upgrade head                # Run migrations
uv run uvicorn grins_platform.main:app     # Start server
curl http://localhost:8000/api/v1/...      # Test endpoints

# End-to-end validation (Database)
docker-compose up -d db                    # Start database
uv run alembic upgrade head                # Run migrations
docker exec -it grins-db psql -U grins -d grins_platform -c "\\dt"  # Verify tables
```

### File Structure
```
src/grins_platform/
├── __init__.py
├── logging.py              # Logging infrastructure
├── my_module.py            # Source code
└── tests/
    ├── __init__.py
    ├── conftest.py         # Shared fixtures
    └── test_my_module.py   # Tests
```
