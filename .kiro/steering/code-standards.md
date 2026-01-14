# Code Quality Standards

## CRITICAL: Quality by Default

Every code change MUST include logging, testing, and pass quality checks.
This is not optional. These are requirements for task completion.

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

## 2. Comprehensive Testing (MANDATORY)

### Framework
- Use `pytest` with `pytest-cov`, `pytest-asyncio`
- Run tests: `uv run pytest -v`
- Run with coverage: `uv run pytest --cov=src/grins_platform`

### Test File Location
- Tests live in `tests/` subdirectory within each module
- Test files mirror source: `module.py` → `tests/test_module.py`
- Shared fixtures in `tests/conftest.py`

### Test Types Required

**Unit Tests** (Always required):
- Test each public method individually
- Test with valid inputs
- Test with invalid inputs
- Test edge cases

**Integration Tests** (For workflows):
- Test complete workflows
- Test component interactions
- Test with real dependencies when possible

**Property-Based Tests** (For data transformations):
- Use `pytest.mark.parametrize` for multiple inputs
- Test serialization round-trips
- Test invariants across input ranges

**Mock Tests** (For external dependencies):
- Mock external APIs
- Mock database connections
- Mock file system operations

### Coverage Targets
- Services: 85%+
- API endpoints: 80%+
- Utilities: 70%+
- Models: 60%+

### Test Naming
```python
class TestMyService:
    def test_operation_with_valid_input_returns_result(self):
        """Test that operation returns expected result with valid input."""
        
    def test_operation_with_invalid_input_raises_validation_error(self):
        """Test that operation raises ValidationError with invalid input."""
        
    def test_operation_logs_started_and_completed_events(self):
        """Test that operation logs appropriate events."""
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

### The 5-Step Process

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

5. REPORT COMPLETION
   ├── Summary of what was created
   ├── Test results (X/X passing)
   ├── Quality check results (zero violations)
   └── Ready for use
```

### Task Completion Criteria

A task is NOT complete until:
- ✅ Code has appropriate logging
- ✅ Tests exist and pass
- ✅ Ruff reports zero violations
- ✅ MyPy reports zero errors
- ✅ Pyright reports zero errors
- ✅ All tests pass

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

# Full validation
uv run ruff check src/ && uv run mypy src/ && uv run pyright src/ && uv run pytest -v
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
