# Technical Architecture

## Stack
- **Backend**: Python 3.11+ / FastAPI / SQLAlchemy 2.0 (async) / PostgreSQL 15+ / Redis 7+
- **Frontend**: React 19 / TypeScript 5.9 / Vite 7 / TanStack Query v5 / Tailwind 4 / Radix UI + shadcn
- **Package mgmt**: uv (backend), npm (frontend)
- **Quality**: Ruff (lint+format) / MyPy + Pyright (types) / pytest + Vitest (tests) / structlog (logging)
- **Deployment**: Railway (backend) + Vercel (frontend)
- **External**: Twilio (SMS), Google Maps, OpenAI

## Architecture
```
API (FastAPI + request correlation)
  → Services (business logic + LoggerMixin)
    → Repositories (data access)
      → PostgreSQL + Redis
```

## Dev Setup
```bash
./scripts/setup.sh          # full setup
source .venv/bin/activate
./scripts/dev.sh            # dev server
```
Env vars: `DATABASE_URL`, `REDIS_URL`, `LOG_LEVEL`, `ENVIRONMENT`

## Quality Checks (all must pass with zero errors)
```bash
uv run ruff check --fix src/ && uv run mypy src/ && uv run pyright src/ && uv run pytest -v
```

## Code Style
PEP 8 via Ruff | 88 char lines | Google docstrings | type hints on all functions
Naming: PascalCase classes, snake_case functions/vars, UPPER_SNAKE constants

## Testing: Three Tiers (mandatory)
| Tier | Dir | Marker | Deps | Purpose |
|------|-----|--------|------|---------|
| 1 | tests/unit/ | `@pytest.mark.unit` | Mocked | Isolated correctness |
| 2 | tests/functional/ | `@pytest.mark.functional` | Real DB | User workflow |
| 3 | tests/integration/ | `@pytest.mark.integration` | Full system | Cross-component |

## Logging
structlog JSON | Pattern: `{domain}.{component}.{action}_{state}`
Services: `LoggerMixin` | Functions: `get_logger()` + `DomainLogger` | APIs: request ID correlation

## Performance Targets
API: <200ms p95 | DB queries: <50ms p95 | Cache: <10ms p95

## Security
JWT auth | bcrypt passwords | HTTPS in prod | PII masked in logs | never log passwords/tokens
