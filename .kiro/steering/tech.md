# Technical Architecture

## Technology Stack

### Core
- **Language**: Python 3.11+
- **Package Manager**: uv (10-100x faster than pip)
- **Build System**: Hatchling

### Frameworks
- **Web Framework**: FastAPI (async, type-safe)
- **Database**: PostgreSQL 15+ with asyncpg
- **Cache**: Redis 7+
- **Task Queue**: Celery (future)

### Quality Tools
- **Linting**: Ruff (800+ rules)
- **Type Checking**: MyPy + Pyright (dual validation)
- **Testing**: pytest with pytest-cov, pytest-asyncio
- **Logging**: structlog (JSON output)

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      API Layer                              │
│  FastAPI endpoints with request correlation                 │
├─────────────────────────────────────────────────────────────┤
│                    Service Layer                            │
│  Business logic with LoggerMixin                            │
├─────────────────────────────────────────────────────────────┤
│                   Repository Layer                          │
│  Data access with query logging                             │
├─────────────────────────────────────────────────────────────┤
│                    Database Layer                           │
│  PostgreSQL + Redis                                         │
└─────────────────────────────────────────────────────────────┘
```

## Development Environment

### Required Tools
- Python 3.11+
- uv package manager
- Docker & Docker Compose
- Git

### Setup
```bash
# Clone and setup
git clone <repo>
cd <repo>
./scripts/setup.sh

# Activate environment
source .venv/bin/activate

# Run development server
./scripts/dev.sh
```

### Environment Variables
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)
- `ENVIRONMENT`: Environment name (development, staging, production)

## Code Standards

### Style Guide
- Follow PEP 8 with Ruff enforcement
- Line length: 88 characters
- Use Google-style docstrings
- Type hints on all functions

### Naming Conventions
- Classes: PascalCase
- Functions/variables: snake_case
- Constants: UPPER_SNAKE_CASE
- Private: _leading_underscore

### Import Order (Ruff enforced)
1. Standard library
2. Third-party packages
3. Local imports

## Testing Strategy

### Framework
- **pytest**: Core testing framework
- **pytest-cov**: Coverage reporting
- **pytest-asyncio**: Async test support
- **pytest-Faker**: Test data generation

### Test Types
| Type | Purpose | Location |
|------|---------|----------|
| Unit | Individual functions/methods | `tests/test_*.py` |
| Integration | Component interactions | `tests/integration/` |
| Property | Data transformations | `tests/test_*.py` |
| API | Endpoint testing | `tests/test_*_api.py` |

### Coverage Targets
- Services: 85%+
- API endpoints: 80%+
- Utilities: 70%+
- Models: 60%+

### Running Tests
```bash
# All tests
uv run pytest -v

# With coverage
uv run pytest --cov=src/grins_platform --cov-report=term-missing

# Specific file
uv run pytest tests/test_my_module.py -v
```

## Logging Strategy

### Framework
- **structlog**: Structured JSON logging
- **Pattern**: `{domain}.{component}.{action}_{state}`

### Log Levels
| Level | Usage |
|-------|-------|
| DEBUG | Internal details, queries |
| INFO | Business operations, API calls |
| WARNING | Recoverable issues, rejections |
| ERROR | Failures requiring attention |
| CRITICAL | System-level failures |

### Implementation
- Services: Use `LoggerMixin` class
- Functions: Use `get_logger()` and `DomainLogger`
- APIs: Use request ID correlation

### Reference
See `code-standards.md` for detailed logging patterns.

## Quality Checks

### Tools
| Tool | Purpose | Command |
|------|---------|---------|
| Ruff | Linting + formatting | `uv run ruff check --fix src/` |
| MyPy | Type checking | `uv run mypy src/` |
| Pyright | Type checking | `uv run pyright src/` |
| pytest | Testing | `uv run pytest -v` |

### Full Validation
```bash
uv run ruff check src/ && uv run mypy src/ && uv run pyright src/ && uv run pytest -v
```

### Requirements
- Zero Ruff violations
- Zero MyPy errors
- Zero Pyright errors
- All tests passing

## Deployment Process

### Containerization
- Multi-stage Docker builds
- Non-root user execution
- Health checks enabled

### Services
- PostgreSQL 15-alpine
- Redis 7-alpine
- Application container

### Commands
```bash
# Build and run
docker-compose up --build

# Production build
docker build -t grins-platform:latest .
```

## Performance Requirements

### Response Times
- API endpoints: < 200ms (p95)
- Database queries: < 50ms (p95)
- Cache operations: < 10ms (p95)

### Scalability
- Horizontal scaling via container orchestration
- Connection pooling for database
- Redis caching for frequent queries

## Security Considerations

### Authentication
- JWT tokens for API authentication
- Secure password hashing (bcrypt)
- Token refresh mechanism

### Data Protection
- HTTPS only in production
- Sensitive data encryption at rest
- PII masking in logs

### Logging Security
- Never log passwords or tokens
- Mask PII in log output
- Request ID for audit trails
