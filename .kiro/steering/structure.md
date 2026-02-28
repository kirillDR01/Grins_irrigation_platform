# Project Structure

## Backend
```
src/grins_platform/
├── main.py / app.py        # Entry point, FastAPI app factory
├── database.py             # DB config
├── logging.py / log_config.py  # structlog setup
├── api/v1/                 # API endpoints ({domain}.py + router.py)
├── services/               # Business logic ({domain}_service.py)
│   └── ai/                 # AI services (agent, tools, prompts, context)
├── models/                 # SQLAlchemy models ({domain}.py + enums.py)
├── schemas/                # Pydantic schemas ({domain}.py)
├── repositories/           # Data access ({domain}_repository.py)
├── middleware/              # CSRF, etc.
├── exceptions/             # Custom exceptions
├── migrations/versions/    # Alembic migrations
└── tests/
    ├── conftest.py
    ├── unit/               # @pytest.mark.unit
    ├── functional/         # @pytest.mark.functional
    └── integration/        # @pytest.mark.integration
```

## Frontend (VSA)
```
frontend/src/
├── core/                   # Foundation: api/client.ts, config, providers, router
├── shared/                 # Cross-feature: ui components, hooks, utils (3+ features)
└── features/{feature}/     # Self-contained: components/, hooks/, api/, types/, index.ts
```
Rule: Features import from `core/` and `shared/` only — never from each other.

## Naming
- Python: `snake_case.py`, tests: `test_{module}.py`
- Frontend: Components `PascalCase.tsx`, hooks `use{Name}.ts`, API `{feature}Api.ts`

## Imports
```python
# Backend
from grins_platform.services.{domain}_service import {Domain}Service
from grins_platform.models.{domain} import {Model}
from grins_platform.repositories.{domain}_repository import {Domain}Repository
```
```typescript
// Frontend
import { apiClient } from '@/core/api/client';
import { Button } from '@/shared/components/ui';
import { CustomerList } from '@/features/customers';
```

## Key Config Files
`pyproject.toml` (backend) | `frontend/package.json` | `frontend/vite.config.ts` | `frontend/tsconfig.json` | `.env` | `docker-compose.yml` | `alembic.ini`
