# Project Structure

## Directory Layout

```
grins-irrigation-platform/
├── .kiro/                      # Kiro configuration
│   ├── agents/                 # Custom agents
│   ├── hooks/                  # Automation hooks
│   ├── prompts/                # Custom prompts
│   ├── settings/               # MCP and other settings
│   ├── specs/                  # Feature specifications
│   └── steering/               # Steering documents
│
├── src/                        # Source code
│   └── grins_platform/         # Main package
│       ├── __init__.py
│       ├── logging.py          # Logging infrastructure
│       ├── main.py             # Application entry point
│       ├── api/                # API endpoints
│       │   ├── __init__.py
│       │   └── routes.py
│       ├── services/           # Business logic
│       │   ├── __init__.py
│       │   └── user_service.py
│       ├── models/             # Data models
│       │   ├── __init__.py
│       │   └── user.py
│       ├── repositories/       # Data access
│       │   ├── __init__.py
│       │   └── user_repository.py
│       └── tests/              # Test files
│           ├── __init__.py
│           ├── conftest.py     # Shared fixtures
│           ├── test_logging.py
│           └── test_main.py
│
├── app/                        # Legacy/reference code
│   └── core/                   # Core utilities
│
├── config/                     # Configuration files
├── data/                       # Data files
├── logs/                       # Log output
├── output/                     # Generated output
├── scripts/                    # Utility scripts
│   ├── setup.sh
│   ├── dev.sh
│   └── init-db.sql
│
├── .env                        # Environment variables
├── .gitignore                  # Git ignore rules
├── docker-compose.yml          # Docker services
├── Dockerfile                  # Container build
├── pyproject.toml              # Project configuration
├── README.md                   # Project documentation
└── DEVLOG.md                   # Development log
```

## File Naming Conventions

### Python Files
- **Modules**: `snake_case.py` (e.g., `user_service.py`)
- **Test files**: `test_{module}.py` (e.g., `test_user_service.py`)
- **Init files**: `__init__.py` (required for packages)

### Directories
- **Packages**: `snake_case` (e.g., `grins_platform`)
- **Test directories**: `tests/` within each package

### Configuration
- **YAML/JSON**: `kebab-case.yml` or `kebab-case.json`
- **Environment**: `.env`, `.env.example`

## Module Organization

### Package Structure
```
grins_platform/
├── __init__.py         # Package exports
├── logging.py          # Cross-cutting: logging
├── exceptions.py       # Cross-cutting: custom exceptions
├── config.py           # Cross-cutting: configuration
│
├── api/                # Presentation layer
│   ├── __init__.py
│   ├── routes.py       # Route definitions
│   ├── middleware.py   # Request middleware
│   └── dependencies.py # Dependency injection
│
├── services/           # Business logic layer
│   ├── __init__.py
│   └── {domain}_service.py
│
├── models/             # Domain models
│   ├── __init__.py
│   └── {domain}.py
│
├── repositories/       # Data access layer
│   ├── __init__.py
│   └── {domain}_repository.py
│
└── tests/              # Test files
    ├── __init__.py
    ├── conftest.py
    └── test_{module}.py
```

### Import Patterns
```python
# Cross-cutting concerns
from grins_platform.logging import LoggerMixin, get_logger
from grins_platform.exceptions import ValidationError, NotFoundError

# Services
from grins_platform.services.user_service import UserService

# Models
from grins_platform.models.user import User, UserCreate

# Repositories
from grins_platform.repositories.user_repository import UserRepository
```

## Test File Structure

### Location
Tests live in `tests/` subdirectory within each package:
```
src/grins_platform/
├── user_service.py
└── tests/
    └── test_user_service.py
```

### Test File Template
```python
"""Tests for {module_name}."""

import pytest
from unittest.mock import Mock, patch

from grins_platform.{module} import {Class}


class Test{Class}:
    """Test suite for {Class}."""
    
    @pytest.fixture
    def instance(self) -> {Class}:
        """Create instance for testing."""
        return {Class}()
    
    def test_method_with_valid_input(self, instance: {Class}) -> None:
        """Test method with valid input."""
        pass
```

### Shared Fixtures
Common fixtures go in `tests/conftest.py`:
```python
"""Shared test fixtures."""

import pytest
from unittest.mock import Mock


@pytest.fixture
def mock_database() -> Mock:
    """Create mock database connection."""
    return Mock()


@pytest.fixture
def sample_user_data() -> dict:
    """Create sample user data."""
    return {
        "name": "Test User",
        "email": "test@example.com",
    }
```

## Configuration Files

| File | Purpose |
|------|---------|
| `pyproject.toml` | Project metadata, dependencies, tool config |
| `.env` | Environment variables (not committed) |
| `.env.example` | Environment variable template |
| `docker-compose.yml` | Docker service definitions |
| `Dockerfile` | Container build instructions |

## Documentation Structure

| Location | Content |
|----------|---------|
| `README.md` | Project overview, setup, usage |
| `DEVLOG.md` | Development progress log |
| `.kiro/steering/` | Development standards and patterns |
| `docs/` | Additional documentation (future) |

## Build Artifacts

### Ignored Directories
```
.venv/              # Virtual environment
.mypy_cache/        # MyPy cache
.pytest_cache/      # Pytest cache
.ruff_cache/        # Ruff cache
__pycache__/        # Python bytecode
*.egg-info/         # Package metadata
dist/               # Built packages
build/              # Build output
```

### Output Directories
```
logs/               # Application logs
output/             # Generated files
coverage/           # Test coverage reports
```

## Environment-Specific Files

### Development
- `.env` with development settings
- `docker-compose.yml` for local services
- Debug logging enabled

### Staging
- Environment variables from CI/CD
- Staging database connection
- Info logging level

### Production
- Environment variables from secrets manager
- Production database connection
- Warning logging level
- Error tracking enabled
