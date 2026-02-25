# Code Quality Standards

Every code change MUST include logging, testing, pass quality checks, AND be validated end-to-end.

## 1. Structured Logging (mandatory)

Framework: `structlog` | Pattern: `{domain}.{component}.{action}_{state}`
Import: `from grins_platform.logging import LoggerMixin, get_logger, DomainLogger`

### Class-based (services)
```python
class MyService(LoggerMixin):
    DOMAIN = "business"
    def operation(self, param):
        self.log_started("operation", param=param)
        try:
            result = self._do_work(param)
            self.log_completed("operation", result_id=result.id)
            return result
        except ValidationError as e:
            self.log_rejected("operation", reason=str(e))
            raise
        except Exception as e:
            self.log_failed("operation", error=e)
            raise
```

### Function-based (utilities)
```python
logger = get_logger(__name__)
DomainLogger.api_event(logger, "processing", "started", data_size=len(data))
```

Log levels: DEBUG=internals | INFO=business ops | WARNING=recoverable | ERROR=failures | CRITICAL=system
Log: service entry/exit, external API calls, validation, errors with context, security events
Never log: passwords, tokens, PII, every internal call

## 2. Three-Tier Testing (mandatory)

| Tier | Dir | Marker | Deps |
|------|-----|--------|------|
| Unit | tests/unit/ | `@pytest.mark.unit` | All mocked |
| Functional | tests/functional/ | `@pytest.mark.functional` | Real DB |
| Integration | tests/integration/ | `@pytest.mark.integration` | Full system |

```bash
uv run pytest -m unit -v        # fast, no deps
uv run pytest -m functional -v  # requires DB
uv run pytest -m integration -v # requires full system
uv run pytest --cov=src/grins_platform
```

Test naming: `test_{method}_with_{condition}_returns_{expected}` (unit) | `test_{workflow}_as_user_would_experience` (functional) | `test_{feature}_works_with_existing_{component}` (integration)

## 3. Type Safety (mandatory)
All functions: type hints + return types. No implicit `Any`. Must pass MyPy AND Pyright with zero errors.

## 4. Error Handling
```python
try:
    result = self._process(data)
except ValidationError:
    raise  # already logged
except ExternalServiceError as e:
    self.log_failed("op", error=e)
    raise ServiceError(f"External failed: {e}") from e
```

## 5. Quality Commands
```bash
uv run ruff check --fix src/   # lint (zero violations required)
uv run ruff format src/        # format (88 char lines)
uv run mypy src/               # type check
uv run pyright src/             # type check
uv run pytest -v               # tests
```

## 6. Task Completion Checklist
- [ ] Logging with LoggerMixin/get_logger
- [ ] Tests: unit + functional + integration
- [ ] Ruff: zero violations
- [ ] MyPy + Pyright: zero errors
- [ ] All tests passing
- [ ] End-to-end validation (start server, test via curl/API)
