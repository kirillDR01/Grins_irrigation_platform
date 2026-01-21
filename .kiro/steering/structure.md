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
├── frontend/                   # React Admin Dashboard (Phase 3+)
│   ├── public/                 # Static assets, PWA manifest
│   ├── src/
│   │   ├── core/               # Foundation (API client, providers, router)
│   │   ├── shared/             # Cross-feature components and utilities
│   │   └── features/           # Feature slices (customers, jobs, schedule)
│   ├── package.json
│   ├── vite.config.ts
│   └── tsconfig.json
│
├── src/                        # Backend source code (Python)
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
│       └── tests/              # Test files (three-tier structure)
│           ├── __init__.py
│           ├── conftest.py     # Shared fixtures
│           ├── unit/           # Tier 1: Isolated tests with mocks
│           ├── functional/     # Tier 2: Real infrastructure tests
│           └── integration/    # Tier 3: Cross-component tests
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

## Frontend Structure (Phase 3+)

The frontend uses Vertical Slice Architecture (VSA) with React + TypeScript.

### Frontend Directory Layout
```
frontend/
├── public/
│   ├── manifest.json           # PWA manifest
│   └── icons/                  # App icons
├── src/
│   ├── main.tsx                # Entry point
│   ├── App.tsx                 # Root component with providers
│   │
│   ├── core/                   # Foundation (exists before features)
│   │   ├── api/
│   │   │   ├── client.ts       # Axios instance with interceptors
│   │   │   └── types.ts        # API response types
│   │   ├── config/
│   │   │   └── index.ts        # Environment configuration
│   │   ├── providers/
│   │   │   ├── QueryProvider.tsx    # TanStack Query setup
│   │   │   └── ThemeProvider.tsx    # Theme context
│   │   └── router/
│   │       └── index.tsx       # Route definitions
│   │
│   ├── shared/                 # Cross-feature utilities (3+ features)
│   │   ├── components/
│   │   │   ├── ui/             # shadcn/ui components
│   │   │   ├── Layout.tsx      # Main layout with sidebar
│   │   │   ├── PageHeader.tsx  # Consistent page headers
│   │   │   └── StatusBadge.tsx # Status indicators
│   │   ├── hooks/
│   │   │   ├── useDebounce.ts
│   │   │   └── usePagination.ts
│   │   └── utils/
│   │       ├── formatters.ts   # Date, currency formatting
│   │       └── validators.ts   # Zod schemas
│   │
│   └── features/               # Feature slices (self-contained)
│       ├── dashboard/
│       │   ├── components/
│       │   ├── hooks/
│       │   └── index.ts        # Public exports
│       ├── customers/
│       │   ├── components/
│       │   ├── hooks/
│       │   ├── api/
│       │   ├── types/
│       │   └── index.ts
│       ├── jobs/
│       │   └── ...
│       ├── staff/
│       │   └── ...
│       └── schedule/
│           └── ...
│
├── index.html
├── vite.config.ts
├── tailwind.config.js
├── tsconfig.json
└── package.json
```

### Frontend File Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Components | PascalCase.tsx | `CustomerList.tsx` |
| Hooks | camelCase with `use` prefix | `useCustomers.ts` |
| API files | camelCase with `Api` suffix | `customerApi.ts` |
| Types | camelCase or PascalCase | `types/index.ts` |
| Utils | camelCase | `formatters.ts` |

### Frontend Import Patterns
```typescript
// Core imports
import { apiClient } from '@/core/api/client';
import { QueryProvider } from '@/core/providers/QueryProvider';

// Shared imports
import { Button, Card } from '@/shared/components/ui';
import { Layout } from '@/shared/components/Layout';
import { useDebounce } from '@/shared/hooks/useDebounce';

// Feature imports (from public index.ts)
import { CustomerList, useCustomers } from '@/features/customers';
import { JobDetail, useJob } from '@/features/jobs';
```

### VSA Principles for Frontend

1. **Feature Isolation**: Each feature (customers, jobs, staff, schedule) is self-contained
2. **Core Foundation**: API client, providers, router exist before features
3. **Shared Components**: UI components used by 3+ features go in `shared/`
4. **Duplication Until Proven Shared**: Start with feature-specific code, extract when pattern emerges
5. **Clear Dependencies**: Features can import from `core/` and `shared/`, not from each other

## Test File Structure

### Three-Tier Test Organization
Tests are organized into three tiers based on their purpose and dependencies:

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

### Test Tiers

| Tier | Directory | Purpose | Marker |
|------|-----------|---------|--------|
| 1 | `tests/unit/` | Isolated tests with mocked dependencies | `@pytest.mark.unit` |
| 2 | `tests/functional/` | Real infrastructure, user workflows | `@pytest.mark.functional` |
| 3 | `tests/integration/` | Cross-component, existing system | `@pytest.mark.integration` |

### Test File Template
```python
"""Tests for {module_name}."""

import pytest
from unittest.mock import Mock, patch

from grins_platform.{module} import {Class}


@pytest.mark.unit  # or @pytest.mark.functional or @pytest.mark.integration
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

### Running Tests by Tier
```bash
# All tests
uv run pytest -v

# Unit tests only (fast, no dependencies)
uv run pytest -m unit -v

# Functional tests (requires database)
uv run pytest -m functional -v

# Integration tests (requires full system)
uv run pytest -m integration -v
```

## Configuration Files

| File | Purpose |
|------|---------|
| `pyproject.toml` | Backend: Project metadata, dependencies, tool config |
| `frontend/package.json` | Frontend: Dependencies and scripts |
| `frontend/vite.config.ts` | Frontend: Vite build configuration |
| `frontend/tsconfig.json` | Frontend: TypeScript configuration |
| `frontend/tailwind.config.js` | Frontend: Tailwind CSS configuration |
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
# Backend
.venv/              # Virtual environment
.mypy_cache/        # MyPy cache
.pytest_cache/      # Pytest cache
.ruff_cache/        # Ruff cache
__pycache__/        # Python bytecode
*.egg-info/         # Package metadata
dist/               # Built packages
build/              # Build output

# Frontend
frontend/node_modules/   # Node dependencies
frontend/dist/           # Production build output
frontend/.vite/          # Vite cache
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
