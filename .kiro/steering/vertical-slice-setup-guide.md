# Vertical Slice Architecture Guide

Full reference: `docs/vertical-slice-setup-guide-full.md`

## Project Layout
```
app/
├── core/           # Foundation infrastructure (exists before features)
├── shared/         # Cross-feature utilities (3+ features use it)
└── {feature}/      # Self-contained feature slices
```

## core/ — Universal Infrastructure
Put here if removing any feature slice would still require this code.
```
core/
├── config.py          # Pydantic BaseSettings, @lru_cache get_settings()
├── database.py        # Engine, SessionLocal, Base, get_db() dependency
├── logging.py         # structlog setup, get_logger(), request_id correlation
├── middleware.py       # CORS, request logging with correlation ID
├── exceptions.py      # Base exception classes
├── dependencies.py    # Global FastAPI deps (get_current_user, require_admin)
├── health.py          # Health checks (DB, Redis)
└── rate_limit.py      # Rate limiting
```

## shared/ — Cross-Feature Code
Move here when **3+ features** need it. Until then, duplicate.
```
shared/
├── models.py          # TimestampMixin, base models
├── schemas.py         # PaginationParams, PaginatedResponse[T]
├── utils.py           # Generic helpers (date, string)
├── validators.py      # Reusable validators
└── integrations/      # External clients (email, storage, payment) used by 3+ features
```

## Feature Slice Structure
```
{feature}/
├── routes.py          # FastAPI endpoints
├── service.py         # Business logic
├── repository.py      # Data access
├── models.py          # SQLAlchemy models
├── schemas.py         # Pydantic request/response
├── exceptions.py      # Feature-specific exceptions
├── dependencies.py    # Feature-specific FastAPI deps (optional)
├── tasks.py           # Background jobs (optional)
├── cache.py           # Feature caching (optional)
└── test_*.py          # Tests
```
Start minimal: routes.py + service.py + schemas.py. Add others as needed.

## Implementation Order (new feature)
1. schemas.py → define request/response shapes
2. routes.py → define endpoints, wire to service
3. service.py → business logic
4. repository.py → data access (if needed)
5. models.py → DB models (if needed)
6. Register router in main.py: `app.include_router(feature_router)`
7. Write tests

## Key Decisions

**Duplication vs DRY**: Duplicate for 1-2 features. Extract to shared/ at 3rd usage.

**Cross-feature data access**: Feature A can READ from Feature B's repository. Never WRITE to another feature's tables.

**Cross-feature transactions**: Use orchestrating service that shares one DB session across repositories.
```python
class OrderService:
    def __init__(self, db: Session):
        self.products = ProductRepository(db)
        self.inventory = InventoryRepository(db)
        self.orders = OrderRepository(db)
    # All repos share session = single transaction
```

**Auth**: Feature slice for login/register in `auth/`. Global deps (`get_current_user`) in `core/dependencies.py`.

**External APIs**: 1 feature → inside feature dir. 3+ features → `shared/integrations/`.

**Large features (20+ files)**: Split into sub-features. Wire via `__init__.py`:
```python
# products/__init__.py
router = APIRouter(prefix="/products")
router.include_router(routes.router)
router.include_router(catalog_routes.router, prefix="/catalog")
router.include_router(pricing_routes.router, prefix="/pricing")
```

**Router registration in main.py**:
```python
app.include_router(feature.router, prefix="/v1/feature", tags=["feature"])
```

**API versioning**: `{feature}/v1/routes.py`, `{feature}/v2/routes.py`. Shared service/repository.

**Migrations**: Centralized in `alembic/versions/`, named `{num}_{feature}_{description}.py`.

**Feature-specific config**: <5 settings → add to `core/config.py`. 5+ settings → create `{feature}/config.py` with `env_prefix`.

**Circular dependencies between features**: Extract shared interface to `shared/` or use domain events (`shared/events.py` EventBus pattern). Never have Feature A import from Feature B and vice versa.

**Cross-feature tests**: Tests spanning multiple features go in `tests/integration/`, NOT inside any single feature slice.

**Test infrastructure**: `tests/conftest.py` provides shared fixtures (db session, test client). Per-feature `conftest.py` for feature-specific fixtures.

## Logging Convention
Event naming: `{domain}.{action}.{status}` (e.g., `product.create.failed`)
```python
logger = get_logger(__name__)
logger.info("product.create.started", sku=data.sku)
logger.error("product.create.failed", error=str(e), exc_info=True)
```
