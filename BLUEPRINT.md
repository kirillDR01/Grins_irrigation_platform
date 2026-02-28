# Repository Foundation Blueprint

> **Purpose**: This document is a seed prompt for bootstrapping a new full-stack application repository. It captures the architectural decisions, infrastructure patterns, and tooling conventions extracted from a production field-service management platform. All patterns are described stack-agnostically with generic templates — adapt to your chosen language and framework.

---

## Table of Contents

1. [Project Structure](#1-project-structure)
2. [Containerization](#2-containerization)
3. [Database Layer](#3-database-layer)
4. [Backend Architecture](#4-backend-architecture)
5. [Frontend Architecture](#5-frontend-architecture)
6. [API Design](#6-api-design)
7. [Authentication & Authorization](#7-authentication--authorization)
8. [Type Safety](#8-type-safety)
9. [Linting & Formatting](#9-linting--formatting)
10. [Testing](#10-testing)
11. [Environment & Configuration](#11-environment--configuration)
12. [Dependency Management](#12-dependency-management)
13. [Logging & Observability](#13-logging--observability)
14. [External Service Integration](#14-external-service-integration)
15. [Architectural Patterns Summary](#15-architectural-patterns-summary)

---

## 1. Project Structure

### Principle

Monorepo with clear separation between backend, frontend, infrastructure, and tooling. Every directory has a single responsibility. Backend code lives under a `src/` directory with a named package. Frontend lives in its own top-level directory with its own dependency management.

### Generic Template

```
project-root/
├── src/                          # Backend source code
│   └── <app_package>/            # Named Python/Go/Rust package
│       ├── main.py               # Entry point
│       ├── app.py                # Application factory
│       ├── database.py           # DB connection & session management
│       ├── api/                  # API endpoints (versioned)
│       │   └── v1/
│       │       ├── router.py     # Aggregates all sub-routers
│       │       ├── auth.py
│       │       ├── customers.py
│       │       └── dependencies.py
│       ├── models/               # ORM models (one file per entity)
│       │   ├── enums.py          # All enums in one place
│       │   ├── customer.py
│       │   └── job.py
│       ├── schemas/              # Request/response DTOs (one file per entity)
│       │   ├── customer.py
│       │   └── job.py
│       ├── repositories/         # Data access layer (one file per entity)
│       │   ├── customer_repository.py
│       │   └── job_repository.py
│       ├── services/             # Business logic layer (one file per domain)
│       │   ├── auth_service.py
│       │   ├── customer_service.py
│       │   └── ai/              # Complex subsystems get subdirectories
│       │       ├── agent.py
│       │       ├── prompts/
│       │       └── tools/
│       ├── middleware/            # Request/response middleware
│       ├── exceptions/           # Custom exception hierarchy
│       ├── migrations/           # Database migration files
│       │   └── versions/
│       ├── utils/                # Shared utilities (keep small)
│       └── tests/                # Test suite (mirrors src structure)
│           ├── conftest.py       # Shared fixtures
│           ├── unit/
│           ├── functional/
│           └── integration/
│
├── frontend/                     # Frontend application
│   ├── src/
│   │   ├── core/                 # Infrastructure (API client, providers, router)
│   │   │   ├── api/
│   │   │   ├── config/
│   │   │   ├── providers/
│   │   │   └── router/
│   │   ├── features/             # Feature-based organization
│   │   │   └── <feature>/
│   │   │       ├── api/
│   │   │       ├── components/
│   │   │       ├── hooks/
│   │   │       └── types/
│   │   └── test/
│   ├── public/
│   └── package.json
│
├── scripts/                      # Helper scripts (DB init, seeding, validation)
│   └── init-db.sql
├── config/                       # Application configuration files
├── data/                         # Static data files
├── docs/                         # Documentation
├── logs/                         # Application logs (gitignored)
├── output/                       # Generated output (gitignored)
│
├── Dockerfile
├── docker-compose.yml            # Production compose
├── docker-compose.dev.yml        # Development overrides
├── .dockerignore
├── .gitignore
├── .env.example                  # Environment variable template
├── pyproject.toml                # Backend project config (or equivalent)
└── README.md
```

### Key Decisions

- **One model/schema/repository file per entity** — avoids merge conflicts and improves discoverability.
- **Tests live inside the backend package** — co-located with the code they test.
- **Feature-based frontend organization** — each feature is self-contained with its own API calls, components, hooks, and types.
- **Subsystems get subdirectories** — when a service grows complex (e.g., AI agent with prompts, tools, context builders), it gets its own directory under `services/`.

---

## 2. Containerization

### Principle

Single-stage Dockerfile optimized for production with a separate dev compose override. Use the fastest available package manager. Run as a non-root user. Implement health checks. Cache dependency installation separately from code changes.

### Generic Dockerfile Template

```dockerfile
# --- Production Image ---
FROM <language>:<version>-slim AS production

# 1. System dependencies (minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

# 2. Fast package manager (uv for Python, pnpm for Node, etc.)
RUN pip install uv  # or: npm install -g pnpm

# 3. Non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

# 4. DEPENDENCY LAYER (cached separately from code)
COPY <dependency-manifest> <lock-file> ./
RUN <install-dependencies-only>
# Example (Python/uv):  uv sync --frozen --no-install-project --no-dev
# Example (Node/pnpm):  pnpm install --frozen-lockfile --prod

# 5. APPLICATION CODE
COPY . /app
RUN <install-project-itself>
# Example (Python/uv):  uv sync --frozen --no-editable --no-dev

# 6. Directories & permissions
RUN mkdir -p /app/output /app/logs && chown -R appuser:appuser /app

# 7. Switch to non-root
USER appuser

# 8. Environment
ENV PYTHONUNBUFFERED=1
ENV PATH="/app/.venv/bin:$PATH"

# 9. Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000
CMD ["<server-command>", "--host", "0.0.0.0", "--port", "8000"]
```

### Generic docker-compose.yml Template

```yaml
version: "3.8"

services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
      cache_from:
        - <image-name>:latest
    image: <image-name>:latest
    container_name: <project>-app
    ports:
      - "8000:8000"
    volumes:
      - ./src:/app/src:ro          # Source code (read-only in prod-like)
      - ./config:/app/config:ro    # Config files (read-only)
      - /app/.venv                 # Persist virtual env (anonymous volume)
      - app_output:/app/output     # Persistent output
      - app_logs:/app/logs         # Persistent logs
    environment:
      - PYTHONPATH=/app/src
      - ENVIRONMENT=development
      - LOG_LEVEL=INFO
      - DATABASE_URL=<async-driver>://<user>:<pass>@postgres:5432/<db_name>
    restart: unless-stopped
    depends_on:
      postgres:
        condition: service_healthy

  postgres:
    image: postgres:15-alpine
    container_name: <project>-db
    ports:
      - "5432:5432"
    environment:
      - POSTGRES_DB=<db_name>
      - POSTGRES_USER=<db_user>
      - POSTGRES_PASSWORD=<db_password>
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/init-db.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U <db_user> -d <db_name>"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  # redis:                          # Uncomment when needed
  #   image: redis:7-alpine
  #   ports: ["6379:6379"]
  #   volumes: [redis_data:/data]
  #   healthcheck:
  #     test: ["CMD", "redis-cli", "ping"]

volumes:
  app_output:
  app_logs:
  postgres_data:
```

### Generic docker-compose.dev.yml Template

```yaml
# Usage: docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
services:
  app:
    volumes:
      - .:/app                     # Mount entire project for hot reload
      - /app/.venv                 # Preserve virtual environment
    environment:
      - ENVIRONMENT=development
      - LOG_LEVEL=DEBUG
      - PYTHONDONTWRITEBYTECODE=1  # No .pyc files in dev
    command: <dev-server-with-hot-reload>
    # Example: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Key Decisions

- **Dependency layer cached before code** — rebuilds only install new deps when code changes, not all deps.
- **Non-root user** — reduces container attack surface.
- **Read-only source mounts in production compose** — prevents accidental writes.
- **Anonymous volume for venv** — persists virtual environment between container restarts without polluting host.
- **Health check dependency chain** — app waits for database to be ready before starting.
- **`unless-stopped` restart policy** — auto-recovers from crashes but respects explicit stops.
- **Alpine images for infrastructure services** (Postgres, Redis) — minimal footprint.
- **Slim images for application** — balance between size and compatibility.

### .dockerignore Template

Aggressively exclude everything not needed at build time:

```
# Runtime artifacts
__pycache__/
*.py[cod]
.venv/
venv/
node_modules/

# Testing & quality
.pytest_cache/
.coverage
htmlcov/
.mypy_cache/
.ruff_cache/

# IDE & OS
.vscode/
.idea/
.DS_Store

# Git & CI
.git/
.github/

# Documentation (except README)
docs/
*.md
!README.md

# Environment (secrets)
.env
.env.*
!.env.example

# Build artifacts
dist/
build/
*.egg-info/

# Logs & output
logs/
output/

# Docker files (prevent recursive context)
Dockerfile*
docker-compose*
.dockerignore
```

---

## 3. Database Layer

### Principle

Use an async ORM with connection pooling, UUID primary keys, automatic timestamps, and a migration tool. Initialize the database with extensions, schemas, indexes, and seed data via an entrypoint script that runs on first container startup.

### Connection Management Template

```
Settings:
  pool_size: 5                    # Base connections in pool
  max_overflow: 10                # Extra connections under load
  pool_timeout: 30                # Seconds to wait for a connection
  pool_recycle: 1800              # Recycle connections every 30 minutes

Health check:
  GET /health → returns DB connection status
```

### Database Init Script Template (`scripts/init-db.sql`)

```sql
-- 1. Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";      -- UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";        -- Password hashing

-- 2. Schemas (namespace isolation)
CREATE SCHEMA IF NOT EXISTS <app_schema>;

-- 3. Core tables with standard columns
CREATE TABLE <app_schema>.<entity> (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    -- entity-specific columns --
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 4. Auto-update trigger for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_<entity>_updated_at
    BEFORE UPDATE ON <app_schema>.<entity>
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 5. Indexes on frequently queried columns
CREATE INDEX idx_<entity>_<column> ON <app_schema>.<entity>(<column>);

-- 6. Seed data (services catalog, default admin, etc.)
INSERT INTO <app_schema>.staff (username, email, password_hash, role)
VALUES ('admin', 'admin@example.com', crypt('changeme', gen_salt('bf')), 'admin');

-- 7. Permissions
GRANT ALL PRIVILEGES ON SCHEMA <app_schema> TO <db_user>;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA <app_schema> TO <db_user>;
```

### Model Conventions

Every model follows these conventions:

| Convention | Pattern |
|---|---|
| **Primary key** | UUID, server-generated (`gen_random_uuid()`) |
| **Timestamps** | `created_at` (immutable), `updated_at` (auto-updated via trigger) |
| **Soft delete** | `is_deleted` boolean + `deleted_at` timestamp (never hard-delete user data) |
| **Status fields** | Use enums, never raw strings |
| **Relationships** | Explicit foreign keys with cascade rules |
| **One file per model** | `models/customer.py`, `models/job.py`, etc. |
| **Enums in one file** | `models/enums.py` contains all status/type enums |

### Migration Conventions

- **Tool**: Alembic (Python), Flyway (Java), goose (Go), or equivalent
- **File naming**: `YYYYMMDD_HHMMSS_<description>.py`
- **One migration per schema change** — never batch unrelated changes
- **Always include rollback** — every `upgrade()` has a corresponding `downgrade()`
- **Migrations directory**: `src/<package>/migrations/versions/`

---

## 4. Backend Architecture

### Principle

Clean layered architecture with strict unidirectional dependencies. Each layer only knows about the layer directly below it. Business logic never leaks into API endpoints or database queries.

### Layer Diagram

```
┌─────────────────────────────────────────────────┐
│  API Layer (Endpoints / Controllers)             │
│  Receives HTTP requests, validates input,        │
│  delegates to services, returns responses         │
├─────────────────────────────────────────────────┤
│  Schema Layer (DTOs / Validators)                │
│  Defines request/response shapes, validates      │
│  input, transforms data between layers           │
├─────────────────────────────────────────────────┤
│  Service Layer (Business Logic)                  │
│  Orchestrates operations, enforces rules,        │
│  coordinates between repositories                │
├─────────────────────────────────────────────────┤
│  Repository Layer (Data Access)                  │
│  Abstracts database queries, returns model       │
│  instances, handles pagination/filtering         │
├─────────────────────────────────────────────────┤
│  Model Layer (ORM Entities)                      │
│  Defines database schema, relationships,         │
│  constraints, column types                       │
└─────────────────────────────────────────────────┘
```

### Layer Rules

| Layer | Can call | Cannot call |
|---|---|---|
| API | Schemas, Services | Repositories, Models directly |
| Services | Repositories, other Services, Schemas | API layer |
| Repositories | Models, Database session | Services, API |
| Models | Nothing (passive data structures) | Everything |

### Dependency Injection Pattern

Use the framework's dependency injection to wire layers together:

```
# Pseudocode
endpoint(request) ->
    service = inject(ServiceClass) ->
        repository = inject(RepositoryClass) ->
            db_session = inject(get_session)
```

### One File Per Entity Per Layer

```
For entity "Customer":
  models/customer.py           → ORM model
  schemas/customer.py          → Create, Update, Response, ListParams DTOs
  repositories/customer_repository.py  → CRUD queries
  services/customer_service.py → Business logic
  api/v1/customers.py          → HTTP endpoints
  tests/unit/test_customer_service.py  → Unit tests
```

### Exception Hierarchy

Define a custom exception hierarchy for clean error handling:

```
AppException (base)
├── NotFoundError           → 404
├── ConflictError           → 409
├── ValidationError         → 422
├── AuthenticationError     → 401
│   ├── InvalidCredentials
│   ├── TokenExpired
│   └── AccountLocked
├── AuthorizationError      → 403
└── ExternalServiceError    → 502
```

Register a global exception handler that maps these to HTTP status codes and consistent error response bodies.

---

## 5. Frontend Architecture

### Principle

Feature-based organization with a clear `core/` infrastructure layer. Server state management via a query/cache library (not global state). Type-safe API calls. Component composition with accessibility-first primitives.

### Technology Stack Pattern

| Concern | Pattern | Example Tools |
|---|---|---|
| **Framework** | Component-based SPA | React, Vue, Svelte |
| **Language** | Strict TypeScript | TypeScript with `strict: true` |
| **Build tool** | Fast dev server + bundler | Vite, Turbopack, esbuild |
| **Routing** | File or config-based | React Router, Next.js, SvelteKit |
| **Server state** | Query/cache library | TanStack Query, SWR |
| **Forms** | Schema-validated forms | React Hook Form + Zod |
| **Styling** | Utility-first CSS | Tailwind CSS |
| **UI primitives** | Accessibility-first | Radix UI, Headless UI |
| **HTTP client** | Interceptor-capable | Axios, ky |
| **Testing** | Vitest + Testing Library | Vitest, Jest, Playwright |

### Core Infrastructure (`src/core/`)

```
core/
├── api/
│   ├── client.ts          # HTTP client instance with interceptors
│   │                        - Base URL from env config
│   │                        - Request interceptor: attach auth token
│   │                        - Response interceptor: handle 401/403/5xx
│   └── types.ts           # Shared API response types
│
├── config/
│   └── index.ts           # Environment-based configuration
│                            - API base URL
│                            - API version
│                            - Feature flags
│
├── providers/
│   ├── QueryProvider.tsx   # Server state cache configuration
│   │                        - Stale time, retry logic, error handling
│   └── ThemeProvider.tsx   # Dark/light mode
│
└── router/
    └── index.tsx           # Route definitions, guards, layouts
```

### Feature Module Pattern (`src/features/<feature>/`)

Each feature is self-contained:

```
features/<feature>/
├── api/
│   └── <feature>Api.ts    # API call functions (typed)
├── components/
│   ├── <Feature>List.tsx   # List view
│   ├── <Feature>Form.tsx   # Create/edit form
│   ├── <Feature>Detail.tsx # Detail view
│   └── <Feature>Search.tsx # Search/filter
├── hooks/
│   ├── use<Feature>s.ts    # Query hook (list)
│   └── use<Feature>Mutations.ts  # Mutation hooks (create/update/delete)
└── types/
    └── index.ts            # Feature-specific types
```

### API Client Template

```typescript
// core/api/client.ts (pseudocode)
const client = createHttpClient({
  baseURL: `${config.apiBaseUrl}/api/${config.apiVersion}`,
});

// Request interceptor: attach auth token
client.interceptors.request.use((config) => {
  const token = storage.get("access_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Response interceptor: handle errors globally
client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.status === 401) redirectToLogin();
    if (error.status === 403) showForbiddenNotice();
    throw error;
  }
);
```

---

## 6. API Design

### Principle

RESTful JSON API with URL-based versioning. Consistent response envelope. Pydantic/Zod-style schema validation on both sides. Standardized error codes.

### URL Structure

```
/api/v1/<resource>                    # Collection
/api/v1/<resource>/{id}               # Individual resource
/api/v1/<resource>/{id}/<sub-resource> # Nested resources
/api/v1/<resource>/{id}/status        # Status transitions
/api/v1/<resource>/bulk-update        # Bulk operations
```

### Response Envelope

```json
// Success (200, 201)
{
  "success": true,
  "data": { ... }
}

// Success (list)
{
  "success": true,
  "data": [ ... ],
  "total": 42,
  "page": 1,
  "page_size": 20
}

// Error (4xx, 5xx)
{
  "success": false,
  "error": {
    "code": "CUSTOMER_NOT_FOUND",
    "message": "Customer not found: {uuid}"
  }
}
```

### Schema Validation Pattern

Every endpoint has typed input/output schemas:

```
POST /customers
  Input:  CustomerCreate  { first_name, last_name, phone, email? }
  Output: CustomerResponse { id, first_name, last_name, phone, status, created_at }

PUT /customers/{id}
  Input:  CustomerUpdate  { first_name?, last_name?, phone?, email? }
  Output: CustomerResponse

GET /customers
  Query:  CustomerListParams { page, page_size, search?, status?, sort_by? }
  Output: PaginatedResponse<CustomerResponse>
```

### Validation Rules

- **Phone numbers**: Normalize to digits-only, validate length
- **Email**: RFC-compliant validation
- **String fields**: Min/max length constraints
- **Status transitions**: Validate against allowed state machine transitions
- **UUIDs**: Validate format on all ID parameters

---

## 7. Authentication & Authorization

### Principle

JWT access tokens (short-lived) + refresh tokens (httpOnly cookie, long-lived). CSRF protection on state-changing requests. Role-based access control.

### Auth Flow

```
1. POST /auth/login { username, password }
   ↓
2. Validate credentials (bcrypt hash comparison)
   ↓
3. Generate tokens:
   - access_token (JWT, ~15-30min expiry, in response body)
   - refresh_token (JWT, ~7 days expiry, in httpOnly cookie)
   - csrf_token (in regular cookie, sent as X-CSRF-Token header)
   ↓
4. Client stores access_token in memory/localStorage
   ↓
5. Subsequent requests: Authorization: Bearer {access_token}
   ↓
6. On 401: POST /auth/refresh (uses refresh_token cookie)
```

### JWT Claims

```json
{
  "sub": "<user-id>",
  "exp": "<expiration-timestamp>",
  "type": "access|refresh"
}
```

### CSRF Protection

- State-changing requests (POST, PUT, DELETE) require `X-CSRF-Token` header
- Token validated against cookie value using constant-time comparison
- Exempt paths: login, health check, public docs

### Role-Based Access Control

```
Roles:
  admin       → Full system access
  manager     → Operations, scheduling, limited finance
  technician  → View assigned work, update status

Implementation:
  - Role stored on user/staff model
  - Checked via dependency injection in endpoint definitions
  - Service layer can also enforce role checks for complex rules
```

---

## 8. Type Safety

### Principle

Dual type checkers on the backend for maximum coverage. Strict mode everywhere. Relaxed rules only for test files and third-party library interop. Frontend uses strict TypeScript with a split tsconfig (app vs. node).

### 8.1 Backend Type Checker #1: MyPy (Exact Config)

Copy this verbatim into `pyproject.toml`. Every non-obvious setting is annotated.

```toml
[tool.mypy]
# ── Basic Settings ──
python_version = "3.11"
platform = "linux"
show_error_codes = true
show_column_numbers = true
show_error_context = true
color_output = true
error_summary = true
pretty = true

# ── Strict Mode ──
# Enables: disallow_any_generics, disallow_untyped_defs, warn_return_any, etc.
strict = true

# ── Additional Warnings Beyond strict=true ──
warn_unused_configs = true
warn_redundant_casts = true
warn_unused_ignores = false          # RATIONALE: False avoids noise when mypy vs pyright disagree on which ignores are needed
warn_return_any = true
warn_unreachable = true              # Catches dead code after early returns/raises
warn_no_return = true

# ── Any Type Controls ──
disallow_any_generics = true
disallow_any_unimported = false      # RATIONALE: Third-party libs with skipped imports would break everything
disallow_any_expr = false            # RATIONALE: ORM query results often produce Any; too noisy if enabled
disallow_any_decorated = false       # RATIONALE: pytest decorators (@pytest.fixture, @pytest.mark.*) aren't fully typed
disallow_any_explicit = false        # RATIONALE: Sometimes you need explicit Any for dynamic patterns (JSON parsing, etc.)
disallow_subclassing_any = false     # RATIONALE: SQLAlchemy's declarative_base() returns Any; all models subclass it

# ── Function & Method Checking ──
disallow_untyped_calls = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
disallow_untyped_decorators = true

# ── None & Optional Handling ──
no_implicit_optional = true          # `def f(x: str = None)` is an error — must write `x: str | None = None`
strict_optional = true

# ── Import & Module Handling ──
no_implicit_reexport = true          # Forces explicit `__all__` or re-export via `from x import y as y`
strict_equality = true
strict_bytes = true
extra_checks = true

# ── Error Reporting ──
show_traceback = true
raise_exceptions = false

# ── Cache & Performance ──
cache_dir = ".mypy_cache"
sqlite_cache = true                  # Faster than file-based cache for large projects
incremental = true                   # Only re-check changed files

# ────────────────────────────────────────────────
# Per-Module Overrides
# ────────────────────────────────────────────────

# TESTS (top-level tests.* pattern)
[[tool.mypy.overrides]]
module = "tests.*"
disallow_untyped_defs = false        # Test functions don't need return type annotations
disallow_incomplete_defs = false
disallow_any_expr = true             # Still catch Any leaks in tests
warn_return_any = false
disallow_untyped_decorators = false  # pytest decorators aren't typed

# TESTS (package-qualified path)
[[tool.mypy.overrides]]
module = "grins_platform.tests.*"
disallow_untyped_defs = false
disallow_incomplete_defs = false
disallow_any_expr = false
warn_return_any = false
disallow_untyped_decorators = false
disable_error_code = [
    "comparison-overlap",            # RATIONALE: Mock comparisons trigger false positives
    "method-assign",                 # RATIONALE: MagicMock attribute assignments
    "misc",                          # RATIONALE: Catch-all for test-specific patterns
]

# EXAMPLES — relaxed for demo code
[[tool.mypy.overrides]]
module = "examples.*"
disallow_untyped_defs = false
disallow_incomplete_defs = false
disallow_any_expr = true
warn_return_any = false

# SCRIPTS — moderate (still type-check bodies, but don't require annotations)
[[tool.mypy.overrides]]
module = "scripts.*"
disallow_untyped_defs = false
check_untyped_defs = true            # Check function bodies even without type annotations
warn_return_any = false

# THIRD-PARTY LIBRARIES — ignore missing stubs
# ADAPTATION NOTE: Add your framework's modules here. These are common in FastAPI/SQLAlchemy projects.
[[tool.mypy.overrides]]
module = [
    "fastapi.*",
    "pydantic.*",
    "sqlalchemy.*",
    "uvicorn.*",
    "pytest.*",
    "_pytest.*",
    "alembic.*",
    "asyncpg.*",
    "structlog.*",
]
ignore_missing_imports = true
follow_imports = "skip"              # Don't type-check third-party source code

# API ENDPOINT MODULES — relax decorator checking
# RATIONALE: FastAPI's @app.get(), @router.post() decorators are not fully typed in mypy
[[tool.mypy.overrides]]
module = "grins_platform.api.v1.*"
disallow_untyped_decorators = false
```

**ADAPTATION NOTES (MyPy):**
- Replace `grins_platform` with your package name
- The third-party module list should match your actual dependencies
- If using Django instead of FastAPI, add `django.*`, `rest_framework.*` to ignored modules
- If not using SQLAlchemy, you can re-enable `disallow_subclassing_any = true`

### 8.2 Backend Type Checker #2: Pyright (Exact Config)

Copy this verbatim into `pyproject.toml`. Pyright catches different error classes than mypy.

```toml
[tool.pyright]
# ── Basic Settings ──
pythonVersion = "3.11"
pythonPlatform = "All"
include = ["src"]
exclude = [
    "**/__pycache__",
    "**/.pytest_cache",
    "**/.mypy_cache",
    "**/node_modules",
    "**/.venv",
    "**/venv",
    "build",
    "dist",
    "**/tests/**",                   # RATIONALE: Tests are excluded from strict pyright (mypy handles them)
]

# ── Type Checking Mode ──
typeCheckingMode = "strict"

# ── Strict Inference Settings ──
strictListInference = true           # [1, "a"] inferred as list[int | str], not list[int] | list[str]
strictDictionaryInference = true     # {"a": 1, "b": "x"} properly typed
strictSetInference = true
strictParameterNoneValue = true      # None must be explicitly in the type union

# ── Diagnostic Rules: ERRORS (these must be fixed) ──
reportMissingImports = "error"
reportOptionalSubscript = "error"          # x[0] where x could be None
reportOptionalMemberAccess = "error"       # x.foo where x could be None
reportOptionalCall = "error"               # x() where x could be None
reportOptionalIterable = "error"           # for i in x where x could be None
reportOptionalContextManager = "error"     # with x where x could be None
reportOptionalOperand = "error"            # x + 1 where x could be None
reportTypedDictNotRequiredAccess = "error"
reportConstantRedefinition = "error"
reportIncompatibleMethodOverride = "error"
reportIncompatibleVariableOverride = "error"
reportInconsistentConstructor = "error"
reportOverlappingOverload = "error"
reportUninitializedInstanceVariable = "error"
reportInvalidStringEscapeSequence = "error"
reportUnknownLambdaType = "error"
reportMissingParameterType = "error"
reportMissingTypeArgument = "error"
reportInvalidTypeVarUse = "error"
reportUndefinedVariable = "error"
reportUnboundVariable = "error"
reportInvalidStubStatement = "error"
reportIncompleteStub = "error"
reportUnusedCoroutine = "error"            # Forgetting to await an async call
reportPropertyTypeMismatch = "error"
reportFunctionMemberAccess = "error"

# ── Diagnostic Rules: WARNINGS (should be fixed but won't block) ──
reportMissingTypeStubs = "warning"
reportImportCycles = "warning"             # RATIONALE: SQLAlchemy model files often have circular imports via relationships
reportUnusedImport = "warning"
reportUnusedClass = "warning"
reportUnusedFunction = "warning"
reportUnusedVariable = "warning"
reportDuplicateImport = "warning"
reportWildcardImportFromLibrary = "warning"
reportPrivateImportUsage = "warning"
reportMissingSuperCall = "warning"
reportUnknownParameterType = "warning"     # RATIONALE: SQLAlchemy Column() types are complex; error would be too noisy
reportUnknownArgumentType = "warning"      # RATIONALE: Pydantic Field() has dynamic defaults
reportUnknownVariableType = "warning"      # RATIONALE: SQLAlchemy query results
reportUnknownMemberType = "warning"        # RATIONALE: SQLAlchemy column attributes (.value, .in_(), etc.)
reportUnnecessaryIsInstance = "warning"
reportUnnecessaryCast = "warning"
reportUnnecessaryContains = "warning"
reportAssertAlwaysTrue = "warning"
reportSelfClsParameterName = "warning"
reportImplicitStringConcatenation = "warning"
reportUnsupportedDunderAll = "warning"
reportUnusedCallResult = "warning"
reportUnusedExpression = "warning"
reportMatchNotExhaustive = "warning"

# ── Diagnostic Rules: DISABLED (intentional) ──
reportCallInDefaultInitializer = "none"    # RATIONALE: FastAPI/Pydantic use Query(), Field(), Depends() in parameter defaults
reportUnnecessaryComparison = "none"       # RATIONALE: SQLAlchemy validators have runtime checks that look unnecessary to pyright
reportUnnecessaryTypeIgnoreComment = "none" # RATIONALE: mypy needs `# type: ignore` comments that pyright doesn't; can't remove them

# ── Performance & Completion ──
autoImportCompletions = true
indexing = true
useLibraryCodeForTypes = true

# ── Stub Path ──
stubPath = "typings"                       # Place custom .pyi stubs here for untyped libraries

# ── Execution Environments ──
# RATIONALE: Per-root overrides to relax rules that conflict with ORM patterns in source code
executionEnvironments = [
    { root = "src", pythonVersion = "3.11", pythonPlatform = "All", reportPrivateUsage = "none", reportUninitializedInstanceVariable = "none" },
]
```

**ADAPTATION NOTES (Pyright):**
- The `reportUnknown*Type = "warning"` rules are relaxed specifically for SQLAlchemy/Pydantic. If using a different ORM (Prisma, TypeORM, etc.), you may be able to set these to `"error"`.
- `reportCallInDefaultInitializer = "none"` is specifically for FastAPI's dependency injection pattern (`def endpoint(db: Session = Depends(get_db))`). If your framework doesn't use this pattern, set to `"warning"`.
- Tests are fully excluded from pyright. MyPy handles test type checking with its own relaxed overrides.

### 8.3 Why Two Type Checkers?

| Aspect | MyPy | Pyright |
|---|---|---|
| **Speed** | Slower (incremental helps) | Very fast |
| **Plugin ecosystem** | Rich (SQLAlchemy, Django, Pydantic plugins) | Limited |
| **Strictness granularity** | Per-module overrides | Per-root execution environments |
| **Test coverage** | Checks tests with relaxed rules | Excludes tests entirely |
| **Error classes caught** | Better at inference, `Any` propagation | Better at Optional safety, exhaustiveness |
| **IDE integration** | Good (most editors) | Excellent (VS Code native) |

The overlap is intentional — each catches bugs the other misses. In practice, ~10% of errors are caught by only one checker.

### 8.4 Frontend Type Checking: TypeScript (Exact Configs)

**Root tsconfig.json** — Project references pattern (separate configs for app code vs. build tooling):

```json
{
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"]
    }
  },
  "files": [],
  "references": [
    { "path": "./tsconfig.app.json" },
    { "path": "./tsconfig.node.json" }
  ]
}
```

**tsconfig.app.json** — Application code (strict):

```json
{
  "compilerOptions": {
    "composite": true,
    "tsBuildInfoFile": "./node_modules/.tmp/tsconfig.app.tsbuildinfo",
    "target": "ES2022",
    "useDefineForClassFields": true,
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "types": ["vite/client"],
    "skipLibCheck": true,

    /* Bundler mode */
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "verbatimModuleSyntax": true,
    "moduleDetection": "force",
    "noEmit": true,
    "jsx": "react-jsx",

    /* Linting — all strict checks enabled */
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "erasableSyntaxOnly": true,
    "noFallthroughCasesInSwitch": true,
    "noUncheckedSideEffectImports": true,

    /* Path aliases */
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"]
    }
  },
  "include": ["src"],
  "exclude": [
    "src/**/*.test.ts",
    "src/**/*.test.tsx",
    "src/**/*.spec.ts",
    "src/**/*.spec.tsx",
    "src/test/**/*"
  ]
}
```

**tsconfig.node.json** — Build tooling config (Vite config, etc.):

```json
{
  "compilerOptions": {
    "composite": true,
    "tsBuildInfoFile": "./node_modules/.tmp/tsconfig.node.tsbuildinfo",
    "target": "ES2023",
    "lib": ["ES2023"],
    "module": "ESNext",
    "types": ["node"],
    "skipLibCheck": true,

    /* Bundler mode */
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "verbatimModuleSyntax": true,
    "moduleDetection": "force",
    "noEmit": true,

    /* Linting */
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "erasableSyntaxOnly": true,
    "noFallthroughCasesInSwitch": true,
    "noUncheckedSideEffectImports": true
  },
  "include": ["vite.config.ts"]
}
```

**ADAPTATION NOTES (TypeScript):**
- `"moduleResolution": "bundler"` is for Vite/esbuild. Use `"node"` for Node.js backends, `"nodenext"` for ESM-first Node.
- `"jsx": "react-jsx"` is React-specific. Use `"preserve"` for other JSX frameworks.
- `"types": ["vite/client"]` provides type defs for `import.meta.env`. Replace with your build tool's types.
- `"erasableSyntaxOnly": true` prevents TypeScript-only features (enums, namespaces) that don't exist in JavaScript.
- The test file exclusions match the pattern `*.test.ts(x)` and `*.spec.ts(x)` — adjust if your test runner uses different naming.
- The split tsconfig pattern (app vs. node) prevents Node.js types from leaking into browser code and vice versa.

---

## 9. Linting & Formatting

### Principle

One fast, comprehensive linter per language. Formatting is non-negotiable and handled by the linter's built-in formatter (or a standalone formatter). All config lives in the project manifest — no scattered `.flake8`, `.pylintrc`, etc.

### 9.1 Backend Linting: Ruff (Exact Config)

Copy this entire block into `pyproject.toml`. Every rule selection and ignore is annotated.

```toml
[tool.ruff]
target-version = "py39"              # Minimum Python version for syntax rules
line-length = 88                     # Black-compatible line length
indent-width = 4

# Directories excluded from linting
exclude = [
    ".bzr", ".direnv", ".eggs", ".git", ".git-rewrite", ".hg",
    ".mypy_cache", ".nox", ".pants.d", ".pyenv", ".pytest_cache",
    ".pytype", ".ruff_cache", ".svn", ".tox", ".venv", ".vscode",
    "__pypackages__", "_build", "buck-out", "build", "dist",
    "node_modules", "site-packages", "venv",
]

[tool.ruff.lint]
# ── Rule Selection (30 categories, 40+ individual rule sets) ──
select = [
    "F",      # Pyflakes — catches undefined names, unused imports, redefined variables
    "E",      # pycodestyle errors — whitespace, indentation, line length
    "W",      # pycodestyle warnings — deprecated features, trailing whitespace
    "I",      # isort — import sorting and organization
    "N",      # pep8-naming — class, function, variable naming conventions
    "UP",     # pyupgrade — replaces old syntax with modern Python equivalents
    "B",      # flake8-bugbear — common bugs (mutable defaults, assert False, etc.)
    "SIM",    # flake8-simplify — simplifiable if/else, context managers, etc.
    "C4",     # flake8-comprehensions — unnecessary list()/dict() calls
    "PL",     # Pylint — comprehensive static analysis (complexity, design, errors)
    "PIE",    # flake8-pie — miscellaneous improvements (unnecessary pass, etc.)
    "RET",    # flake8-return — unnecessary else after return, implicit return None
    "ARG",    # flake8-unused-arguments — unused function/method arguments
    "PTH",    # flake8-use-pathlib — os.path → pathlib.Path modernization
    "RUF",    # Ruff-specific — ambiguous characters, collection literals, etc.
    "ANN",    # flake8-annotations — missing type annotations on public functions
    "S",      # flake8-bandit — SECURITY: hardcoded passwords, SQL injection, eval(), etc.
    "FBT",    # flake8-boolean-trap — boolean positional args (def f(True) is confusing)
    "A",      # flake8-builtins — shadowing Python builtins (id, type, list, etc.)
    "COM",    # flake8-commas — trailing comma consistency
    "EM",     # flake8-errmsg — exception messages should be variables, not f-strings
    "G",      # flake8-logging-format — logging best practices (lazy % formatting)
    "ISC",    # flake8-implicit-str-concat — catches accidental string concatenation
    "T20",    # flake8-print — CATCHES PRINT STATEMENTS (must remove before prod)
    "Q",      # flake8-quotes — enforces consistent quote style
    "SLF",    # flake8-self — accessing private members from outside the class
    "TC",     # flake8-type-checking — moves imports into TYPE_CHECKING blocks
    "TRY",    # tryceratops — broad except, re-raising, exception handling patterns
    "PERF",   # Perflint — performance anti-patterns (unnecessary list(), etc.)
    "FURB",   # refurb — code modernization suggestions
]

# ── Ignored Rules (with rationale for each) ──
ignore = [
    "T201",    # Allow print() — we use print in main.py and scripts; T20 still catches in other files via per-file config
    "FIX002",  # Allow TODO comments — active development uses TODOs as markers
    "S101",    # Allow assert — used in tests and Pydantic validators
    "S105",    # Allow hardcoded password strings — needed in tests and examples
    "S106",    # Allow hardcoded password arguments — same as S105
    "S107",    # Allow hardcoded password defaults — same as S105
    "S602",    # Allow subprocess with shell=True — needed for system integration scripts
    "S603",    # Allow subprocess without shell — same context
    "S604",    # Allow subprocess function calls — same context
    "S605",    # Allow os.system — same context
    "S606",    # Allow os.popen — same context
    "S607",    # Allow partial executable paths — same context
    "PLR2004", # Allow magic values — common in config, HTTP status codes, etc.
    "PLR0913", # Allow >5 function arguments — services/repos often need many params
    "PLR0912", # Allow >12 branches — complex business logic sometimes requires it
    "PLR0915", # Allow >50 statements — comprehensive functions in services
    "ANN002",  # Don't require *args type annotation — rarely informative
    "ANN003",  # Don't require **kwargs type annotation — same reason
    "ANN202",  # Don't require return type on private functions — mypy handles this
    "FBT001",  # Allow boolean positional args — FastAPI query params use booleans
    "FBT002",  # Allow boolean default values — same context
    "FBT003",  # Allow boolean positional values in calls — same context
    "TC003",   # Allow runtime TYPE_CHECKING imports — we use `from __future__ import annotations`
]

# Enable auto-fix for ALL fixable rules
fixable = ["ALL"]
unfixable = []

# Allow underscore-prefixed variables to be unused
dummy-variable-rgx = "^(_+|(_+[a-zA-Z0-9_]*[a-zA-Z0-9]+?))$"

# ── Per-File Overrides ──
[tool.ruff.lint.per-file-ignores]
# Test files get full freedom
"test_*.py" = [
    "S101",    # Assert statements are the core of tests
    "PLR2004", # Magic values in assertions (assert x == 42)
    "ANN",     # No type annotations required in tests
    "SLF001",  # Tests need to access private members for verification
]
"tests/*.py" = [
    "S101", "PLR2004", "ANN", "SLF001",
]
# Example/demo files are relaxed
"examples/*.py" = [
    "T201",    # Print statements for demonstration
    "S101",    # Assert for inline verification
    "PLR2004", # Magic values in examples
    "ANN",     # No type annotations in examples
]
# Entry point can use print for startup messages
"main.py" = [
    "T201",    # Print statements for startup/shutdown messages
]

# ── Sub-tool Configurations ──

[tool.ruff.lint.flake8-annotations]
allow-star-arg-any = true            # Allow *args: Any
ignore-fully-untyped = true          # Don't enforce annotations on fully untyped functions

[tool.ruff.lint.flake8-bandit]
check-typed-exception = true         # Flag `except Exception` (prefer specific exceptions)

[tool.ruff.lint.flake8-bugbear]
# Tell bugbear these functions return immutable values (safe as defaults)
extend-immutable-calls = ["fastapi.Depends", "fastapi.Query"]

[tool.ruff.lint.flake8-quotes]
inline-quotes = "double"
multiline-quotes = "double"
docstring-quotes = "double"
avoid-escape = true                  # Use opposite quote to avoid \" escaping

[tool.ruff.lint.isort]
combine-as-imports = true            # Combine `from x import a, b` with `from x import c as d`
force-wrap-aliases = true            # Always wrap aliased imports
known-first-party = ["app", "src"]   # ADAPTATION: Replace with your package names
section-order = ["future", "standard-library", "third-party", "first-party", "local-folder"]

[tool.ruff.lint.pylint]
max-args = 8                         # Functions with >8 args should be refactored
max-branches = 15                    # Complex branching suggests extraction needed
max-returns = 8                      # Functions with >8 return paths are too complex
max-statements = 60                  # Functions with >60 statements should be split
```

### 9.2 Backend Formatting: Ruff Format (Exact Config)

```toml
[tool.ruff.format]
quote-style = "double"               # Consistent with flake8-quotes above
indent-style = "space"               # Spaces, not tabs
skip-magic-trailing-comma = false    # Respect trailing commas for multi-line formatting
line-ending = "auto"                 # OS-native line endings
docstring-code-format = true         # Format code blocks inside docstrings
docstring-code-line-length = "dynamic" # Match the file's line length
```

**ADAPTATION NOTES (Ruff):**
- Replace `known-first-party = ["app", "src"]` with your actual package names
- The `S602`–`S607` subprocess ignores are only needed if you call system processes. For pure web apps, keep these as errors.
- The `PLR0913` (too many args) ignore is common in service-layer code. If you use a "parameter object" pattern, you can re-enable this.
- `extend-immutable-calls` should list your framework's DI functions (FastAPI: `Depends`, `Query`; Django: N/A)

### 9.3 Frontend Linting: ESLint (Exact Config)

```javascript
// eslint.config.js — ESLint 9+ flat config format
import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'
import { defineConfig, globalIgnores } from 'eslint/config'

export default defineConfig([
  globalIgnores(['dist']),               // Never lint build output
  {
    files: ['**/*.{ts,tsx}'],            // Only lint TypeScript files
    extends: [
      js.configs.recommended,            // ESLint core recommended rules
      tseslint.configs.recommended,       // TypeScript-specific rules
      reactHooks.configs.flat.recommended, // Rules of Hooks enforcement
      reactRefresh.configs.vite,          // Fast Refresh compatibility
    ],
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,          // Browser globals (window, document, etc.)
    },
    rules: {
      // Warn on unused vars EXCEPT those prefixed with _ (common for ignored params)
      '@typescript-eslint/no-unused-vars': ['warn', { argsIgnorePattern: '^_' }],
      // Warn if non-component items are exported (breaks Fast Refresh)
      'react-refresh/only-export-components': ['warn', { allowConstantExport: true }],
    },
  },
])
```

**ADAPTATION NOTES (ESLint):**
- This uses ESLint 9's flat config. If using ESLint 8, convert to `.eslintrc.js` format.
- `reactHooks` and `reactRefresh` are React-specific. Replace with Vue/Svelte/Angular equivalents.
- `globals.browser` assumes client-side code. For SSR/Node, add `globals.node`.

### 9.4 Frontend Formatting: Prettier (Exact Config)

```json
{
  "semi": true,
  "singleQuote": true,
  "tabWidth": 2,
  "trailingComma": "es5",
  "printWidth": 90,
  "bracketSpacing": true,
  "arrowParens": "always",
  "endOfLine": "lf"
}
```

| Setting | Value | Rationale |
|---|---|---|
| `semi` | `true` | Explicit semicolons prevent ASI edge cases |
| `singleQuote` | `true` | Reduces visual noise; common in JS/TS ecosystem |
| `tabWidth` | `2` | Frontend standard (vs. 4 for Python) |
| `trailingComma` | `"es5"` | Cleaner git diffs; valid in ES5+ |
| `printWidth` | `90` | Slightly wider than default 80 for modern screens |
| `bracketSpacing` | `true` | `{ foo }` not `{foo}` |
| `arrowParens` | `"always"` | `(x) => x` not `x => x` — consistent, easier to add params |
| `endOfLine` | `"lf"` | Unix line endings everywhere (prevents git diff noise) |

### 9.5 Frontend NPM Scripts for Quality

```json
{
  "scripts": {
    "lint": "eslint .",
    "lint:fix": "eslint . --fix",
    "typecheck": "tsc -p tsconfig.app.json --noEmit",
    "format": "prettier --write \"src/**/*.{ts,tsx,css,json}\"",
    "format:check": "prettier --check \"src/**/*.{ts,tsx,css,json}\""
  }
}
```

---

## 10. Testing

### Principle

Three-tier test pyramid: unit (fast, isolated), functional (component interactions), integration (real DB/services). Async-first test runner. Factory fixtures for test data. Mock external services, never mock your own code unless necessary. Each test tier has its own `conftest.py` with fixtures scoped to that tier.

### 10.1 Pytest Configuration (Exact Config)

Copy into `pyproject.toml`:

```toml
[tool.pytest.ini_options]
testpaths = ["src/grins_platform/tests"]   # ADAPTATION: Replace with your package path
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
asyncio_mode = "auto"                      # Auto-detect async test functions — no need for @pytest.mark.asyncio
asyncio_default_fixture_loop_scope = "function"  # Each test function gets its own event loop (prevents cross-test pollution)

# Directories to skip during test collection
norecursedirs = ["scripts", ".git", ".venv", "node_modules", "__pycache__"]
```

**ADAPTATION NOTES:**
- `asyncio_mode = "auto"` requires `pytest-asyncio>=0.21.0`. This eliminates the need to decorate every async test with `@pytest.mark.asyncio`.
- `asyncio_default_fixture_loop_scope = "function"` means async fixtures are re-created per test. Use `"session"` for expensive fixtures (like database connections) that should be shared.

### 10.2 Custom Test Markers

Registered programmatically in the root `conftest.py`:

```python
def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests (Tier 1)")
    config.addinivalue_line("markers", "functional: Functional tests (Tier 2)")
    config.addinivalue_line("markers", "integration: Integration tests (Tier 3)")
```

**Usage:** `pytest -m unit` runs only unit tests. `pytest -m "not integration"` skips slow tests.

### 10.3 Test Tier Strategy

| Tier | Name | Speed | Scope | Dependencies | Directory |
|---|---|---|---|---|---|
| 1 | Unit | < 1s each | Single function/class | All deps mocked | `tests/unit/` |
| 2 | Functional | < 5s each | Service + repository | DB mocked, schemas real | `tests/functional/` |
| 3 | Integration | < 30s each | Full HTTP endpoint | Real app, mocked externals | `tests/integration/` |

### 10.4 Test Directory Structure

```
tests/
├── __init__.py
├── conftest.py                  # Root fixtures (shared across all tiers)
│
├── unit/                        # Tier 1: isolated, fast
│   ├── __init__.py
│   ├── test_customer_service.py
│   ├── test_job_service.py
│   ├── test_auth_service.py
│   └── ...
│
├── functional/                  # Tier 2: component interactions
│   ├── __init__.py
│   ├── test_customer_workflow.py
│   └── ...
│
└── integration/                 # Tier 3: full endpoint tests
    ├── __init__.py
    ├── conftest.py              # Integration-specific fixtures (re-exports from fixtures.py)
    ├── fixtures.py              # Heavy fixtures: role-based clients, complex mock data
    ├── test_auth_endpoints.py
    ├── test_customer_endpoints.py
    ├── test_invoice_endpoints.py
    └── ...
```

### 10.5 Root conftest.py (Exact Code — Shared Fixtures)

This is the actual `conftest.py` used across all test tiers:

```python
"""
Shared test fixtures for all test tiers.
"""
from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator, Generator
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from grins_platform.main import app
from grins_platform.models.enums import (
    CustomerStatus,
    LeadSource,
    PropertyType,
    SystemType,
)
from grins_platform.schemas.customer import CustomerCreate, CustomerResponse
from grins_platform.schemas.property import PropertyCreate, PropertyResponse


# =============================================================================
# Pytest Configuration
# =============================================================================

def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests (Tier 1)")
    config.addinivalue_line("markers", "functional: Functional tests (Tier 2)")
    config.addinivalue_line("markers", "integration: Integration tests (Tier 3)")


# =============================================================================
# Sample Data Generators
# =============================================================================

@pytest.fixture
def sample_customer_id() -> uuid.UUID:
    """Generate a sample customer UUID."""
    return uuid.uuid4()


@pytest.fixture
def sample_property_id() -> uuid.UUID:
    """Generate a sample property UUID."""
    return uuid.uuid4()


@pytest.fixture
def sample_customer_create() -> CustomerCreate:
    """Create a sample CustomerCreate schema — static data for simple tests."""
    return CustomerCreate(
        first_name="John",
        last_name="Doe",
        phone="6125551234",
        email="john.doe@example.com",
        lead_source=LeadSource.WEBSITE,
    )


# =============================================================================
# Factory Fixtures (for unique data per test)
# =============================================================================

@pytest.fixture
def sample_customer_create_factory() -> Generator[CustomerCreate, None, None]:
    """Factory fixture — each call returns a unique CustomerCreate.

    PATTERN: Use a counter to generate unique phone/email per invocation.
    This prevents database unique constraint violations in integration tests.
    """
    counter = 0

    def _create(
        first_name: str = "Test",
        last_name: str = "User",
        phone: str | None = None,
        email: str | None = None,
        lead_source: LeadSource | None = LeadSource.WEBSITE,
    ) -> CustomerCreate:
        nonlocal counter
        counter += 1
        return CustomerCreate(
            first_name=first_name,
            last_name=last_name,
            phone=phone or f"612555{counter:04d}",
            email=email or f"test{counter}@example.com",
            lead_source=lead_source,
        )

    yield _create  # type: ignore[misc]


@pytest.fixture
def sample_property_create_factory() -> Generator[PropertyCreate, None, None]:
    """Factory fixture for unique PropertyCreate instances."""
    counter = 0

    def _create(
        address: str | None = None,
        city: str = "Eden Prairie",
        state: str = "MN",
        zip_code: str = "55344",
        zone_count: int = 6,
        system_type: SystemType = SystemType.STANDARD,
        property_type: PropertyType = PropertyType.RESIDENTIAL,
        is_primary: bool = False,
    ) -> PropertyCreate:
        nonlocal counter
        counter += 1
        return PropertyCreate(
            address=address or f"{counter} Test Street",
            city=city,
            state=state,
            zip_code=zip_code,
            zone_count=zone_count,
            system_type=system_type,
            property_type=property_type,
            is_primary=is_primary,
        )

    yield _create  # type: ignore[misc]


# =============================================================================
# Response Fixtures (for asserting expected shapes)
# =============================================================================

@pytest.fixture
def sample_customer_response(sample_customer_id: uuid.UUID) -> CustomerResponse:
    """Pre-built response object for assertion comparisons."""
    return CustomerResponse(
        id=sample_customer_id,
        first_name="John",
        last_name="Doe",
        phone="6125551234",
        email="john.doe@example.com",
        status=CustomerStatus.ACTIVE,
        is_priority=False,
        is_red_flag=False,
        is_slow_payer=False,
        is_new_customer=True,
        sms_opt_in=False,
        email_opt_in=False,
        lead_source=LeadSource.WEBSITE,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


# =============================================================================
# Mock Fixtures for Unit Tests
# =============================================================================

@pytest.fixture
def mock_customer_repository() -> AsyncMock:
    """Mock repository — unit tests inject this instead of real DB access."""
    return AsyncMock()


@pytest.fixture
def mock_property_repository() -> AsyncMock:
    """Mock repository for properties."""
    return AsyncMock()


@pytest.fixture
def mock_customer_model(sample_customer_id: uuid.UUID) -> MagicMock:
    """Mock ORM model instance — simulates what the DB would return.

    PATTERN: Set every field explicitly. MagicMock auto-creates attributes,
    which can hide bugs where code accesses non-existent columns.
    """
    customer = MagicMock()
    customer.id = sample_customer_id
    customer.first_name = "John"
    customer.last_name = "Doe"
    customer.phone = "6125551234"
    customer.email = "john.doe@example.com"
    customer.status = CustomerStatus.ACTIVE.value
    customer.is_priority = False
    customer.is_red_flag = False
    customer.is_slow_payer = False
    customer.is_new_customer = True
    customer.sms_opt_in = False
    customer.email_opt_in = False
    customer.lead_source = LeadSource.WEBSITE.value
    customer.created_at = datetime.now()
    customer.updated_at = datetime.now()
    customer.properties = []
    customer.is_deleted = False
    return customer


# =============================================================================
# HTTP Client Fixtures (Async)
# =============================================================================

@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Unauthenticated async HTTP client — tests the app as a real HTTP client would.

    PATTERN: ASGITransport lets httpx talk directly to the ASGI app
    without starting a real server. Much faster than TestClient.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def authenticated_client() -> AsyncGenerator[AsyncClient, None]:
    """Pre-authenticated client — skips login flow for endpoint tests."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ac.headers.update({"Authorization": "Bearer test-token"})
        yield ac
```

### 10.6 Integration conftest.py (Exact Code — Tier-Specific Fixtures)

Integration tests have a separate `conftest.py` that imports from a `fixtures.py` file:

```python
# tests/integration/conftest.py
"""Import all fixtures from fixtures.py to make them available to integration tests."""
from grins_platform.tests.integration.fixtures import *  # noqa: F403
```

The `fixtures.py` file provides role-based clients and complex domain fixtures:

```python
# tests/integration/fixtures.py
"""
Integration test fixtures for:
- Authentication (login, tokens, RBAC)
- Role-based HTTP clients (admin, manager, tech)
- Complex domain objects (invoices, jobs, schedule audits)
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from grins_platform.main import app
from grins_platform.models.enums import (
    InvoiceStatus,
    JobStatus,
    PaymentMethod,
    StaffRole,
    UserRole,
)

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


# ── Role-Based Mock Staff Fixtures ──

@pytest.fixture
def sample_staff_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def sample_admin_staff(sample_staff_id: uuid.UUID) -> MagicMock:
    """Admin staff member — full system access."""
    staff = MagicMock()
    staff.id = sample_staff_id
    staff.name = "Admin User"
    staff.phone = "6125550001"
    staff.email = "admin@grins.com"
    staff.role = StaffRole.ADMIN.value
    staff.username = "admin"
    staff.password_hash = "$2b$12$test_hash"
    staff.is_login_enabled = True
    staff.is_active = True
    staff.last_login = None
    staff.failed_login_attempts = 0
    staff.locked_until = None
    staff.created_at = datetime.now(timezone.utc)
    staff.updated_at = datetime.now(timezone.utc)
    return staff


@pytest.fixture
def sample_manager_staff() -> MagicMock:
    """Manager staff — operations access, limited finance."""
    staff = MagicMock()
    staff.id = uuid.uuid4()
    staff.name = "Manager User"
    staff.role = UserRole.MANAGER.value
    staff.username = "manager"
    staff.password_hash = "$2b$12$test_hash"
    staff.is_login_enabled = True
    staff.is_active = True
    staff.failed_login_attempts = 0
    staff.locked_until = None
    staff.created_at = datetime.now(timezone.utc)
    staff.updated_at = datetime.now(timezone.utc)
    return staff


@pytest.fixture
def sample_tech_staff() -> MagicMock:
    """Technician staff — view assigned work only."""
    staff = MagicMock()
    staff.id = uuid.uuid4()
    staff.name = "Tech User"
    staff.role = StaffRole.TECH.value
    staff.username = "tech"
    staff.password_hash = "$2b$12$test_hash"
    staff.is_login_enabled = True
    staff.is_active = True
    staff.failed_login_attempts = 0
    staff.locked_until = None
    staff.created_at = datetime.now(timezone.utc)
    staff.updated_at = datetime.now(timezone.utc)
    return staff


# ── Edge Case Staff Fixtures ──

@pytest.fixture
def sample_locked_staff() -> MagicMock:
    """Staff with account locked after too many failed login attempts."""
    staff = MagicMock()
    staff.id = uuid.uuid4()
    staff.name = "Locked User"
    staff.role = StaffRole.TECH.value
    staff.username = "locked"
    staff.is_login_enabled = True
    staff.is_active = True
    staff.failed_login_attempts = 5
    staff.locked_until = datetime.now(timezone.utc) + timedelta(minutes=15)
    return staff


@pytest.fixture
def sample_disabled_staff() -> MagicMock:
    """Staff with login explicitly disabled by admin."""
    staff = MagicMock()
    staff.id = uuid.uuid4()
    staff.name = "Disabled User"
    staff.role = StaffRole.TECH.value
    staff.username = "disabled"
    staff.is_login_enabled = False
    staff.is_active = True
    staff.failed_login_attempts = 0
    staff.locked_until = None
    return staff


# ── Token Fixtures ──

@pytest.fixture
def valid_access_token() -> str:
    return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test_access_token"

@pytest.fixture
def valid_refresh_token() -> str:
    return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test_refresh_token"

@pytest.fixture
def expired_access_token() -> str:
    return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.expired_token"


# ── Role-Based HTTP Client Fixtures ──
# PATTERN: Each role gets its own pre-authenticated client with appropriate headers.

@pytest_asyncio.fixture
async def auth_client_admin() -> AsyncGenerator[AsyncClient, None]:
    """Admin HTTP client — includes both auth and CSRF headers."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ac.headers.update({
            "Authorization": "Bearer admin-test-token",
            "X-CSRF-Token": "test-csrf-token",
        })
        yield ac


@pytest_asyncio.fixture
async def auth_client_manager() -> AsyncGenerator[AsyncClient, None]:
    """Manager HTTP client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ac.headers.update({
            "Authorization": "Bearer manager-test-token",
            "X-CSRF-Token": "test-csrf-token",
        })
        yield ac


@pytest_asyncio.fixture
async def auth_client_tech() -> AsyncGenerator[AsyncClient, None]:
    """Technician HTTP client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ac.headers.update({
            "Authorization": "Bearer tech-test-token",
            "X-CSRF-Token": "test-csrf-token",
        })
        yield ac


@pytest_asyncio.fixture
async def unauthenticated_client() -> AsyncGenerator[AsyncClient, None]:
    """No auth headers — tests that protected endpoints reject anonymous requests."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ── Complex Domain Fixtures (Invoices, Jobs, etc.) ──
# PATTERN: Build fixtures by composing simpler fixtures. Use MagicMock for ORM models
# and set every field explicitly to prevent auto-generated attributes from hiding bugs.

@pytest.fixture
def sample_draft_invoice(
    sample_invoice_id: uuid.UUID,
    sample_job_id: uuid.UUID,
    sample_customer_id: uuid.UUID,
    sample_line_items: list[dict[str, Any]],
) -> MagicMock:
    """Base invoice fixture — draft status. Other statuses derive from this."""
    invoice = MagicMock()
    invoice.id = sample_invoice_id
    invoice.job_id = sample_job_id
    invoice.customer_id = sample_customer_id
    invoice.invoice_number = "INV-2025-0001"
    invoice.amount = Decimal("250.00")
    invoice.status = InvoiceStatus.DRAFT.value
    invoice.payment_method = None
    invoice.paid_at = None
    invoice.paid_amount = Decimal("0.00")
    invoice.line_items = sample_line_items
    invoice.created_at = datetime.now(timezone.utc)
    invoice.updated_at = datetime.now(timezone.utc)
    return invoice


@pytest.fixture
def sample_paid_invoice(sample_draft_invoice: MagicMock) -> MagicMock:
    """PATTERN: Derive status variants from the base fixture by mutation."""
    invoice = sample_draft_invoice
    invoice.status = InvoiceStatus.PAID.value
    invoice.payment_method = PaymentMethod.VENMO.value
    invoice.paid_at = datetime.now(timezone.utc)
    invoice.paid_amount = Decimal("250.00")
    return invoice


@pytest.fixture
def sample_overdue_invoice(sample_draft_invoice: MagicMock) -> MagicMock:
    """Overdue invoice with reminder history."""
    invoice = sample_draft_invoice
    invoice.status = InvoiceStatus.OVERDUE.value
    invoice.due_date = date.today() - timedelta(days=7)
    invoice.reminder_count = 2
    invoice.last_reminder_sent = datetime.now(timezone.utc) - timedelta(days=3)
    return invoice
```

### 10.7 Test Dependencies (Exact Versions)

```toml
# In pyproject.toml [project.optional-dependencies]
test = [
    "pytest>=7.0.0",                # Test runner
    "pytest-cov>=4.0.0",            # Coverage reporting
    "pytest-asyncio>=0.21.0",       # Async test support (auto mode)
    "httpx>=0.24.0",                # Async HTTP client for endpoint testing
    "faker>=19.0.0",                # Realistic fake data generation
    "hypothesis>=6.92.0",           # Property-based testing for complex business logic
]
```

### 10.8 Frontend Testing: Vitest (Exact Config)

**vitest.config.ts:**

```typescript
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',            // Simulates browser DOM
    setupFiles: ['./src/test/setup.ts'],
    globals: true,                   // vi, describe, it, expect available without import
    css: true,                       // Process CSS imports (prevents errors in component tests)
    coverage: {
      provider: 'v8',               // Fast native coverage
      reporter: ['text', 'html', 'lcov'],  // Terminal + HTML report + CI-compatible
      exclude: [
        'node_modules/',
        'src/test/',                 // Don't measure coverage of test utilities
        '**/*.d.ts',                 // Type definitions
        '**/*.config.*',             // Config files
        '**/index.ts',               // Barrel exports (no logic)
      ],
    },
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),  // Match tsconfig path alias
    },
  },
});
```

**src/test/setup.ts** — Global test setup (runs before every test file):

```typescript
import '@testing-library/jest-dom';    // Adds .toBeInTheDocument(), .toHaveTextContent(), etc.
import { afterEach } from 'vitest';
import { cleanup } from '@testing-library/react';

// Clean up rendered components after each test
afterEach(() => {
  cleanup();
});

// Mock window.matchMedia — required by responsive design components
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  }),
});

// Mock ResizeObserver — required by auto-sizing components (tables, charts)
window.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
};
```

### 10.9 Frontend NPM Scripts

```json
{
  "test": "vitest run",              // Single run (CI)
  "test:watch": "vitest",            // Watch mode (development)
  "test:coverage": "vitest run --coverage"  // With coverage report
}
```

### 10.10 Key Testing Patterns Summary

| Pattern | Where | Why |
|---|---|---|
| **Factory fixtures** | Root conftest.py | Unique data per test prevents constraint violations |
| **Static fixtures** | Root conftest.py | Quick setup for tests that don't need uniqueness |
| **Response fixtures** | Root conftest.py | Pre-built expected values for assertion |
| **Mock repositories** | Root conftest.py (AsyncMock) | Unit tests don't touch the DB |
| **Mock ORM models** | Root conftest.py (MagicMock) | Explicit field setting prevents MagicMock auto-attribute hiding bugs |
| **Fixture composition** | Integration fixtures.py | Derive status variants (draft → paid → overdue) by mutating base |
| **Role-based clients** | Integration fixtures.py | One pre-authed client per RBAC role |
| **Edge-case fixtures** | Integration fixtures.py | Locked accounts, disabled users, expired tokens |
| **ASGITransport** | Client fixtures | Tests FastAPI app without starting a real server |
| **Browser API mocks** | Frontend setup.ts | matchMedia, ResizeObserver for component rendering |

**ADAPTATION NOTES:**
- Replace `ASGITransport(app=app)` with your framework's test client pattern (Django: `TestCase.client`, Express: `supertest`)
- The factory fixture pattern (counter + `nonlocal`) works in any language — the key idea is generating unique data per call
- Role-based client fixtures scale with your RBAC system — add one fixture per role
- `pytest-asyncio` with `asyncio_mode = "auto"` eliminates boilerplate; equivalent in JS is Vitest's built-in async support

---

## 11. Environment & Configuration

### Principle

All configuration via environment variables. `.env` files for local development only. `.env.example` committed to repo as documentation. Secrets never hardcoded in source. Pydantic/Zod settings classes for type-safe config loading.

### Environment Variable Categories

| Category | Variables | Notes |
|---|---|---|
| **Database** | `DATABASE_URL` | Full connection string with async driver |
| **Application** | `ENVIRONMENT`, `LOG_LEVEL`, `CORS_ORIGINS` | Runtime behavior |
| **Auth** | `JWT_SECRET_KEY` | MUST be overridden in production |
| **External APIs** | `OPENAI_API_KEY`, `GOOGLE_MAPS_API_KEY` | Third-party integrations |
| **Communications** | `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER` | SMS service |
| **Python runtime** | `PYTHONPATH`, `PYTHONUNBUFFERED`, `PYTHONDONTWRITEBYTECODE` | Interpreter behavior |
| **Frontend** | `VITE_API_BASE_URL`, `VITE_GOOGLE_MAPS_API_KEY` | Prefixed for build tool injection |

### .env.example Template

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/app_db

# Application
ENVIRONMENT=development
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:5173,http://localhost:3000

# Authentication (CHANGE IN PRODUCTION)
JWT_SECRET_KEY=dev-secret-key-change-in-production

# External APIs
OPENAI_API_KEY=your-openai-api-key
GOOGLE_MAPS_API_KEY=your-google-maps-key

# SMS (optional)
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_PHONE_NUMBER=
```

### Type-Safe Settings Pattern

```python
# Pseudocode — use Pydantic BaseSettings or equivalent
class DatabaseSettings(BaseSettings):
    database_url: str = "sqlite:///./dev.db"
    pool_size: int = 5
    max_overflow: int = 10
    pool_timeout: int = 30
    pool_recycle: int = 1800

    class Config:
        env_file = ".env"
```

### Key Decisions

- **Default to safe fallbacks** — `DATABASE_URL` defaults to SQLite for zero-config local development.
- **Frontend env vars prefixed** — `VITE_` prefix ensures only intended vars are exposed to the browser bundle.
- **No secret management system for local dev** — `.env` files are sufficient. Production should use cloud secrets (AWS Secrets Manager, GCP Secret Manager, etc.).
- **dotenv loaded at startup** — environment variables are loaded once at application boot, not per-request.

---

## 12. Dependency Management

### Principle

Use the fastest available package manager with a lock file for reproducible builds. Separate production, dev, and test dependency groups. Pin exact versions in the lock file, use compatible ranges in the manifest.

### Backend Dependencies Template

```toml
# pyproject.toml (Python example — adapt for other languages)
[project]
name = "<project-name>"
version = "0.1.0"
requires-python = ">=3.11"

dependencies = [
    # Web framework
    "<framework>>=x.y.z",

    # Database
    "<orm>>=x.y.z",
    "<async-driver>>=x.y.z",
    "<migration-tool>>=x.y.z",

    # Validation
    "<schema-lib>>=x.y.z",

    # Auth
    "<jwt-lib>>=x.y.z",
    "<password-hashing>>=x.y.z",

    # HTTP client
    "<async-http>>=x.y.z",

    # Logging
    "<structured-logging>>=x.y.z",

    # Environment
    "<dotenv>>=x.y.z",
]

[project.optional-dependencies]
dev = [
    "<type-checker>>=x.y.z",
    "<linter>>=x.y.z",
    "<formatter>>=x.y.z",
    "<pre-commit>>=x.y.z",
]
test = [
    "<test-runner>>=x.y.z",
    "<coverage>>=x.y.z",
    "<async-test-plugin>>=x.y.z",
    "<faker>>=x.y.z",
    "<property-testing>>=x.y.z",
]
```

### Frontend Dependencies Pattern

```json
{
  "dependencies": {
    "<framework>": "^x.y.z",
    "<router>": "^x.y.z",
    "<server-state>": "^x.y.z",
    "<http-client>": "^x.y.z",
    "<form-lib>": "^x.y.z",
    "<schema-validation>": "^x.y.z",
    "<ui-primitives>": "^x.y.z",
    "<css-framework>": "^x.y.z"
  },
  "devDependencies": {
    "<build-tool>": "^x.y.z",
    "<test-runner>": "^x.y.z",
    "<testing-library>": "^x.y.z",
    "<linter>": "^x.y.z",
    "<formatter>": "^x.y.z",
    "<typescript>": "~x.y.z"
  }
}
```

### Key Decisions

- **`uv` for Python** — 100x faster than pip for dependency resolution and installation.
- **Lock files committed** — `uv.lock` and `package-lock.json` ensure reproducible builds across machines.
- **Compatible version ranges** (`>=x.y.z`) in manifest, exact versions in lock file.
- **Separate dependency groups** — production images don't include test/dev tools.
- **`--frozen` flag in Docker** — prevents accidental dependency changes during container builds.

---

## 13. Logging & Observability

### Principle

Structured JSON logging from day one. Every log event follows a hybrid dotted namespace pattern (`{domain}.{component}.{action}_{state}`) that is both human-readable and machine-parseable. Every class in the system inherits a `LoggerMixin` that enforces this pattern automatically. Request correlation IDs flow through all log entries via context variables. Print statements are banned by the linter (`T20` rule).

### 13.1 Architecture Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│                        Logging Architecture                          │
│                                                                      │
│  Every class (API, Service, Repository, DB) inherits LoggerMixin     │
│                            │                                         │
│                            ▼                                         │
│  log_started / log_completed / log_failed / log_validated / log_rejected
│                            │                                         │
│                            ▼                                         │
│  Event format: "{domain}.{component}.{action}_{state}"               │
│  Example:      "business.customerservice.create_customer_completed"  │
│                            │                                         │
│                            ▼                                         │
│  Processor Pipeline (7 steps):                                       │
│    1. add_log_level        → adds "level": "info"                   │
│    2. add_logger_name      → adds "logger": "CustomerService"       │
│    3. add_request_id       → adds "request_id": "uuid" (if set)     │
│    4. TimeStamper(iso)     → adds "timestamp": "2024-01-01T..."     │
│    5. StackInfoRenderer    → adds stack trace (if exception)         │
│    6. set_exc_info         → formats exception info                  │
│    7. JSONRenderer         → serializes to JSON (prod)               │
│       OR ConsoleRenderer   → human-readable with colors (dev)        │
│                            │                                         │
│                            ▼                                         │
│                        stdout                                        │
└──────────────────────────────────────────────────────────────────────┘
```

### 13.2 The Hybrid Dotted Namespace Pattern

Every log event follows this format:

```
{domain}.{component}.{action}_{state}
```

| Segment | Description | Examples |
|---|---|---|
| `domain` | Business area or architectural layer | `business`, `database`, `api`, `auth`, `ai`, `schedule`, `lead`, `invoice` |
| `component` | Class name (lowercased automatically) | `customerservice`, `jobrepository`, `customerendpoints` |
| `action` | What operation is being performed | `create_customer`, `get_by_id`, `login`, `connection` |
| `state` | Lifecycle state of the action | `started`, `completed`, `failed`, `validated`, `rejected` |

**Real examples from the codebase:**
```
business.customerservice.create_customer_started      ← service begins creating a customer
business.customerservice.create_customer_rejected      ← duplicate phone number found
business.customerservice.create_customer_completed     ← customer created successfully
database.customerrepository.get_by_id_started          ← repository queries the database
api.customerendpoints.create_customer_rejected         ← endpoint returns error to client
auth.authservice.login_started                         ← login attempt begins
auth.authservice.login_failed                          ← wrong password
```

### 13.3 Log Configuration (Exact Code)

```python
import contextvars
import logging
import sys
import uuid
from typing import Any, Optional, Union

import structlog

# ── Context variable for request ID correlation ──
# This is a thread-safe, async-safe variable that flows through all log entries
# within a single request lifecycle.
request_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "request_id",
    default=None,
)


def add_request_id(
    _logger: Union[logging.Logger, structlog.stdlib.BoundLogger],
    _method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """Processor: injects request_id into every log entry if one is set."""
    request_id = request_id_var.get()
    if request_id:
        event_dict["request_id"] = request_id
    return event_dict


def configure_logging(
    level: str = "INFO",
    json_output: bool = True,
    include_stdlib: bool = True,
) -> None:
    """
    Configure structured logging.

    Args:
        level: DEBUG, INFO, WARNING, ERROR, CRITICAL
        json_output: True → JSON (production/AI parsing), False → colored console (dev)
        include_stdlib: Whether to also configure Python's stdlib logging
    """
    # ── Processor Pipeline ──
    # Each processor transforms the event dict before it reaches the renderer.
    # Order matters: early processors add fields, late processors format output.
    processors = [
        structlog.stdlib.add_log_level,           # 1. Add "level" field
        structlog.stdlib.add_logger_name,          # 2. Add "logger" field
        add_request_id,                            # 3. Add "request_id" (custom)
        structlog.processors.TimeStamper(fmt="iso"), # 4. Add ISO 8601 timestamp
        structlog.processors.StackInfoRenderer(),  # 5. Render stack traces
        structlog.dev.set_exc_info,                # 6. Format exception info
    ]

    # ── Output Renderer (last processor) ──
    if json_output:
        # Production: one JSON object per line, parseable by log aggregation tools
        processors.append(structlog.processors.JSONRenderer())
    else:
        # Development: colored, human-readable output with full tracebacks
        processors.append(
            structlog.dev.ConsoleRenderer(
                colors=True,
                exception_formatter=structlog.dev.plain_traceback,
            ),
        )

    # ── Configure structlog ──
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        context_class=dict,
        cache_logger_on_first_use=True,  # Performance: don't re-resolve logger per call
    )

    # ── Bridge stdlib logging to structlog ──
    if include_stdlib:
        logging.basicConfig(
            format="%(message)s",
            stream=sys.stdout,
            level=getattr(logging, level.upper()),
        )
        root_logger = logging.getLogger()
        root_logger.handlers.clear()
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("%(message)s"))
        root_logger.addHandler(handler)
        root_logger.setLevel(getattr(logging, level.upper()))


# Initialize logging on module import (runs once when any module imports log_config)
configure_logging()
```

### 13.4 Request ID Correlation

Every HTTP request gets a unique UUID that flows through all log entries in that request's lifecycle. This lets you trace a single request across API → Service → Repository layers.

```python
def set_request_id(request_id: Optional[str] = None) -> str:
    """Set request ID. Generates UUID if none provided."""
    if request_id is None:
        request_id = str(uuid.uuid4())
    _ = request_id_var.set(request_id)
    return request_id


def clear_request_id() -> None:
    """Clear request ID (call at end of request lifecycle)."""
    _ = request_id_var.set(None)
```

**Usage in middleware or dependency:**
```python
# At the start of each request:
request_id = set_request_id()  # Auto-generates UUID

# All subsequent log calls in this async context automatically include:
# {"request_id": "550e8400-e29b-41d4-a716-446655440000", ...}

# At the end of the request:
clear_request_id()
```

**Example correlated log output (single request):**
```json
{"event": "api.customerendpoints.create_customer_started", "request_id": "abc-123", "phone": "1234", "level": "info", "timestamp": "2024-01-01T10:00:00Z"}
{"event": "business.customerservice.create_customer_started", "request_id": "abc-123", "phone": "1234", "level": "info", "timestamp": "2024-01-01T10:00:00Z"}
{"event": "database.customerrepository.find_by_phone_started", "request_id": "abc-123", "level": "info", "timestamp": "2024-01-01T10:00:00Z"}
{"event": "database.customerrepository.find_by_phone_completed", "request_id": "abc-123", "level": "info", "timestamp": "2024-01-01T10:00:00Z"}
{"event": "database.customerrepository.create_completed", "request_id": "abc-123", "customer_id": "uuid-456", "level": "info", "timestamp": "2024-01-01T10:00:01Z"}
{"event": "business.customerservice.create_customer_completed", "request_id": "abc-123", "customer_id": "uuid-456", "level": "info", "timestamp": "2024-01-01T10:00:01Z"}
{"event": "api.customerendpoints.create_customer_completed", "request_id": "abc-123", "customer_id": "uuid-456", "level": "info", "timestamp": "2024-01-01T10:00:01Z"}
```

### 13.5 LoggerMixin Base Class (Exact Code)

This mixin is inherited by **every class in the system** — 55+ classes across all layers. It enforces the dotted namespace pattern and provides lifecycle logging methods.

```python
class LoggerMixin:
    """Mixin class to add structured logging to any class.

    Subclasses set DOMAIN to categorize their logs:
        class CustomerService(LoggerMixin):
            DOMAIN = "business"

        class CustomerRepository(LoggerMixin):
            DOMAIN = "database"

        class CustomerEndpoints(LoggerMixin):
            DOMAIN = "api"
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.logger = get_logger(self.__class__.__name__)

    def log_started(self, action: str, **kwargs: Any) -> None:
        """Log that an action has begun. Level: INFO."""
        domain = getattr(self, "DOMAIN", "app")
        component = self.__class__.__name__.lower()
        event = f"{domain}.{component}.{action}_started"
        self.logger.info(event, **kwargs)

    def log_completed(self, action: str, **kwargs: Any) -> None:
        """Log that an action finished successfully. Level: INFO."""
        domain = getattr(self, "DOMAIN", "app")
        component = self.__class__.__name__.lower()
        event = f"{domain}.{component}.{action}_completed"
        self.logger.info(event, **kwargs)

    def log_failed(
        self,
        action: str,
        error: Optional[Exception] = None,
        **kwargs: Any,
    ) -> None:
        """Log that an action failed. Level: ERROR.
        Automatically includes error message, error type, and stack trace.
        """
        domain = getattr(self, "DOMAIN", "app")
        component = self.__class__.__name__.lower()
        event = f"{domain}.{component}.{action}_failed"

        if error:
            kwargs["error"] = str(error)
            kwargs["error_type"] = error.__class__.__name__

        self.logger.error(event, exc_info=error is not None, **kwargs)

    def log_validated(self, action: str, **kwargs: Any) -> None:
        """Log that validation passed. Level: INFO."""
        domain = getattr(self, "DOMAIN", "app")
        component = self.__class__.__name__.lower()
        event = f"{domain}.{component}.{action}_validated"
        self.logger.info(event, **kwargs)

    def log_rejected(self, action: str, reason: str, **kwargs: Any) -> None:
        """Log that an action was rejected (business rule violation). Level: WARNING.
        Always includes a 'reason' field explaining why.
        """
        domain = getattr(self, "DOMAIN", "app")
        component = self.__class__.__name__.lower()
        event = f"{domain}.{component}.{action}_rejected"
        self.logger.warning(event, reason=reason, **kwargs)
```

### 13.6 DOMAIN Values Used Across the Codebase

| DOMAIN | Layer | Used By |
|---|---|---|
| `"api"` | API endpoints | `CustomerEndpoints`, `JobEndpoints`, `LeadEndpoints`, `ScheduleEndpoints`, `StaffEndpoints`, `AppointmentEndpoints`, `DashboardEndpoints`, `PropertyEndpoints`, `ServiceOfferingEndpoints`, `StaffAvailabilityEndpoints`, `ConflictEndpoints`, `ReassignmentEndpoints` |
| `"business"` | Service layer (general) | `CustomerService`, `PropertyService`, `StaffReassignmentService`, `TravelTimeService`, `ConflictResolutionService`, `ScheduleSolverService`, `ScheduleGenerationService`, `SMSService`, `StaffAvailabilityService`, `AIAgentService`, `ConstraintParserService`, `ScheduleExplanationService`, `RateLimitService`, `AuditService`, `ContextBuilder`, `UnassignedJobAnalyzer`, all AI tool classes |
| `"database"` | Repository layer | `CustomerRepository`, `JobRepository`, `StaffRepository`, `PropertyRepository`, `ServiceOfferingRepository`, `LeadRepository`, `AppointmentRepository`, `StaffAvailabilityRepository`, `InvoiceRepository`, `ScheduleClearAuditRepository`, `AIUsageRepository`, `AIAuditLogRepository`, `SentMessageRepository`, `DatabaseManager` |
| `"auth"` | Authentication | `AuthService` |
| `"ai"` | AI subsystem | `ChatSession` |
| `"job"` | Job management | `JobService` |
| `"lead"` | Lead management | `LeadService` |
| `"invoice"` | Invoice management | `InvoiceService` |
| `"schedule"` | Scheduling | `ScheduleClearService` |
| `"dashboard"` | Dashboard | `DashboardService` |
| `"staff"` | Staff management | `StaffService` |
| `"service"` | Service offerings | `ServiceOfferingService` |
| `"appointment"` | Appointments | `AppointmentService` |
| `"app"` | Default (fallback) | Any class that doesn't set `DOMAIN` |

### 13.7 DomainLogger Static Helpers

For code that isn't in a class (standalone functions, scripts), use `DomainLogger`:

```python
class DomainLogger:
    """Domain-specific logging helpers for standalone code."""

    @staticmethod
    def user_event(logger, action: str, state: str, **kwargs) -> None:
        """Log user domain events → 'user.auth.{action}_{state}'"""
        log_event(logger, f"user.auth.{action}_{state}", **kwargs)

    @staticmethod
    def database_event(logger, action: str, state: str, **kwargs) -> None:
        """Log database events → 'database.connection.{action}_{state}'"""
        log_event(logger, f"database.connection.{action}_{state}", **kwargs)

    @staticmethod
    def api_event(logger, action: str, state: str, **kwargs) -> None:
        """Log API events → 'api.request.{action}_{state}'"""
        log_event(logger, f"api.request.{action}_{state}", **kwargs)

    @staticmethod
    def validation_event(logger, action: str, state: str, **kwargs) -> None:
        """Log validation events → 'validation.schema.{action}_{state}'"""
        log_event(logger, f"validation.schema.{action}_{state}", **kwargs)
```

### 13.8 Real Usage Pattern (Service Layer)

This is how logging looks in actual service code:

```python
class CustomerService(LoggerMixin):
    DOMAIN = "business"

    async def create_customer(self, data: CustomerCreate) -> CustomerResponse:
        # 1. Log the start — include identifying info but redact sensitive data
        self.log_started("create_customer", phone=data.phone[-4:])

        # 2. Check business rules — log rejection with reason
        existing = await self.repository.find_by_phone(data.phone)
        if existing:
            self.log_rejected(
                "create_customer",
                reason="duplicate_phone",
                existing_id=str(existing.id),
            )
            raise DuplicateCustomerError(existing.id, data.phone)

        # 3. Perform the operation
        customer = await self.repository.create(...)

        # 4. Log success with result identifiers
        self.log_completed("create_customer", customer_id=str(customer.id))

        return CustomerResponse.model_validate(customer)
```

**What this produces (JSON output):**
```json
{"event": "business.customerservice.create_customer_started", "phone": "1234", "level": "info", "timestamp": "..."}
{"event": "business.customerservice.create_customer_completed", "customer_id": "uuid-456", "level": "info", "timestamp": "..."}
```

**Or on duplicate (rejection):**
```json
{"event": "business.customerservice.create_customer_started", "phone": "1234", "level": "info", "timestamp": "..."}
{"event": "business.customerservice.create_customer_rejected", "reason": "duplicate_phone", "existing_id": "uuid-789", "level": "warning", "timestamp": "..."}
```

### 13.9 Lifecycle State Reference

| Method | State Suffix | Log Level | When to Use |
|---|---|---|---|
| `log_started()` | `_started` | INFO | Beginning of any operation |
| `log_completed()` | `_completed` | INFO | Successful completion |
| `log_failed()` | `_failed` | ERROR | Unexpected errors (exceptions, crashes) |
| `log_validated()` | `_validated` | INFO | Input/data passed validation |
| `log_rejected()` | `_rejected` | WARNING | Business rule violation (not an error, but denied) |

**Key distinction:** `_failed` is for unexpected errors (bugs, infrastructure). `_rejected` is for expected denials (duplicate data, invalid transitions, unauthorized access).

### 13.10 Output Modes

**Production (JSON)** — one parseable JSON object per line:
```json
{"event": "business.customerservice.create_customer_started", "phone": "1234", "level": "info", "logger": "CustomerService", "timestamp": "2024-01-01T10:00:00.000000Z"}
```

**Development (Console)** — colored, human-readable:
```
2024-01-01T10:00:00 [info     ] business.customerservice.create_customer_started phone=1234
```

Controlled by the `json_output` parameter to `configure_logging()`. Typically wired to the `ENVIRONMENT` env var:
```python
configure_logging(
    level=os.getenv("LOG_LEVEL", "INFO"),
    json_output=os.getenv("ENVIRONMENT") != "development",
)
```

### 13.11 Testing the Logging System (Exact Tests)

The logging system itself has a dedicated test file (`tests/test_logging.py`) covering:

```python
class TestLoggingConfiguration:
    """Test JSON vs console output modes."""

    def test_configure_logging_json_output(self, capsys):
        configure_logging(level="DEBUG", json_output=True)
        logger = get_logger("test")
        logger.info("test.configuration_validated", test_param="value")

        captured = capsys.readouterr()
        log_data = json.loads(captured.out.strip())

        assert log_data["event"] == "test.configuration_validated"
        assert log_data["test_param"] == "value"
        assert log_data["level"] == "info"
        assert "timestamp" in log_data


class TestRequestIdCorrelation:
    """Test that request IDs flow through all log entries."""

    def test_request_id_in_log_output(self, capsys):
        configure_logging(json_output=True)
        logger = get_logger("test")
        request_id = set_request_id("test-correlation-123")
        logger.info("test.correlation_validated", message="test")

        log_data = json.loads(capsys.readouterr().out.strip())
        assert log_data["request_id"] == request_id

        clear_request_id()


class TestHybridDottedNamespace:
    """Test namespace pattern: domain.component.action_state."""

    def test_namespace_pattern_validation(self, capsys):
        configure_logging(json_output=True)
        logger = get_logger("test")

        valid_patterns = [
            "user.auth.login_started",
            "database.connection.established_completed",
            "api.request.validation_failed",
        ]
        for pattern in valid_patterns:
            log_event(logger, pattern, test_pattern=pattern)
            log_data = json.loads(capsys.readouterr().out.strip())
            assert log_data["event"] == pattern
            # Verify structure: at least 3 parts, underscore in last part
            parts = pattern.split(".")
            assert len(parts) >= 3
            assert "_" in parts[-1]


class TestLoggerMixin:
    """Test each lifecycle method."""

    def test_log_started_method(self, caplog):
        class TestService(LoggerMixin):
            DOMAIN = "test"

        service = TestService()
        service.log_started("operation", param1="value1")

        log_data = json.loads(caplog.records[0].message)
        assert log_data["event"] == "test.testservice.operation_started"
        assert log_data["param1"] == "value1"
        assert log_data["level"] == "info"

    def test_log_failed_method_with_exception(self, caplog):
        class TestService(LoggerMixin):
            DOMAIN = "database"

        service = TestService()
        service.log_failed("connection", error=ValueError("Connection failed"), host="localhost")

        log_data = json.loads(caplog.records[0].message)
        assert log_data["event"] == "database.testservice.connection_failed"
        assert log_data["error"] == "Connection failed"
        assert log_data["error_type"] == "ValueError"
        assert log_data["level"] == "error"

    def test_log_rejected_method(self, caplog):
        class TestService(LoggerMixin):
            DOMAIN = "api"

        service = TestService()
        service.log_rejected("request", reason="invalid_token", endpoint="/users")

        log_data = json.loads(caplog.records[0].message)
        assert log_data["event"] == "api.testservice.request_rejected"
        assert log_data["reason"] == "invalid_token"
        assert log_data["level"] == "warning"

    def test_default_domain_when_not_specified(self, caplog):
        class TestService(LoggerMixin):
            pass  # No DOMAIN — defaults to "app"

        service = TestService()
        service.log_started("operation")

        log_data = json.loads(caplog.records[0].message)
        assert log_data["event"] == "app.testservice.operation_started"


class TestIntegration:
    """End-to-end test: request correlation across a full service call."""

    def test_complete_logging_workflow(self, capsys):
        configure_logging(json_output=True)

        class UserService(LoggerMixin):
            DOMAIN = "user"

            def process_user(self, email: str) -> dict[str, str]:
                self.log_started("processing", email=email)
                if "@" not in email:
                    self.log_rejected("processing", reason="invalid_email", email=email)
                    raise ValueError("Invalid email")
                self.log_validated("email", email=email)
                user_id = f"user_{hash(email) % 1000}"
                self.log_completed("processing", user_id=user_id, email=email)
                return {"user_id": user_id, "email": email}

        request_id = set_request_id("integration-test-123")
        try:
            service = UserService()
            service.process_user("test@example.com")

            log_entries = [
                json.loads(line)
                for line in capsys.readouterr().out.strip().split("\n") if line
            ]

            # Verify 3-event lifecycle: started → validated → completed
            assert len(log_entries) == 3
            assert log_entries[0]["event"] == "user.userservice.processing_started"
            assert log_entries[1]["event"] == "user.userservice.email_validated"
            assert log_entries[2]["event"] == "user.userservice.processing_completed"

            # All entries share the same request_id
            for entry in log_entries:
                assert entry["request_id"] == request_id
        finally:
            clear_request_id()
```

### 13.12 Health Check Endpoint

```python
@app.get("/health", tags=["health"])
async def health_check() -> dict[str, Any]:
    db_manager = get_database_manager()
    db_health = await db_manager.health_check()
    return {
        "status": "healthy" if db_health["status"] == "healthy" else "degraded",
        "version": "1.0.0",
        "database": db_health,
    }
```

Used by Docker HEALTHCHECK (`curl -f http://localhost:8000/health || exit 1`), load balancers, and monitoring.

### 13.13 ADAPTATION NOTES

- **Different language/framework?** The core ideas are portable:
  - **Dotted namespace pattern** works in any language — just concatenate strings
  - **LoggerMixin** becomes a trait (Rust), mixin (Ruby), or base class (Java/Go embedded struct)
  - **Context variables** map to Go's `context.Context`, Java's `MDC`, Node's `AsyncLocalStorage`
  - **Processor pipeline** maps to Winston transports (Node), logback filters (Java), or slog handlers (Go)
- **structlog** is Python-specific. Equivalents: Winston (Node), slog (Go), Logback (Java), tracing (Rust)
- **The key insight**: having a `LoggerMixin` that every class inherits means logging is never forgotten — it's built into the architecture, not bolted on.

---

## 14. External Service Integration

### Principle

All external service calls go through dedicated service classes. Never call external APIs directly from endpoints. Implement rate limiting, error handling, and audit logging for every external integration.

### Integration Pattern

```
External Service Integration Checklist:
  [ ] Dedicated service class (e.g., SmsService, AiService)
  [ ] Environment variables for credentials
  [ ] Rate limiting (requests per minute/hour)
  [ ] Error handling with fallback behavior
  [ ] Audit logging (who called what, when, result)
  [ ] Usage tracking (tokens, cost, volume)
  [ ] Timeout configuration
  [ ] Retry logic with exponential backoff
```

### Integrations in This Platform

| Service | Purpose | Pattern |
|---|---|---|
| **OpenAI API** | AI assistant chat, scheduling explanations | Async HTTP, rate-limited, audited, token-tracked |
| **Twilio API** | SMS notifications to customers | Async HTTP, message history logged |
| **Google Maps API** | Travel time calculations between properties | HTTP, results cached |

### AI Integration Pattern

When integrating an LLM/AI service:

```
ai/
├── agent.py              # Main orchestrator
├── session.py            # Multi-turn conversation state
├── audit.py              # Operation logging
├── rate_limiter.py       # Per-user rate limits
├── security.py           # PII detection/redaction
├── prompts/              # System/user prompt templates
│   ├── system.py
│   ├── scheduling.py
│   └── communication.py
├── tools/                # Function-calling tool definitions
│   ├── scheduling.py
│   └── queries.py
└── context/
    └── builder.py        # Context assembly for prompts
```

---

## 15. Architectural Patterns Summary

### Design Patterns Used

| Pattern | Where | Why |
|---|---|---|
| **Repository** | Data access layer | Abstracts DB queries, enables testing without DB |
| **Service** | Business logic layer | Encapsulates rules, orchestrates repositories |
| **Dependency Injection** | API → Service → Repository | Loose coupling, testability |
| **DTO/Schema** | Request/response boundaries | Type-safe validation, decouples API from DB |
| **Factory** | Test fixtures | Unique test data per test run |
| **Enum** | Status fields | Type-safe state machines |
| **Soft Delete** | User-facing entities | Data recovery, audit compliance |
| **Audit Trail** | Status changes, AI operations | Accountability, debugging |
| **Feature Module** | Frontend organization | Self-contained features, parallel development |
| **Interceptor** | HTTP client | Cross-cutting concerns (auth, error handling) |

### What's NOT Included (By Design)

| Omission | Reason |
|---|---|
| **CI/CD pipelines** | Out of scope (local dev focus) |
| **Deployment configs** | Platform-specific (Railway, Vercel, AWS, etc.) |
| **Message queues** | Add when you need async job processing |
| **Caching layer** | Add Redis when you have performance bottlenecks |
| **API rate limiting** | Add at infrastructure level (nginx, API gateway) |
| **Secret management** | Use your cloud provider's secret service in production |
| **Pre-commit hooks** | Listed as dependency but not configured — set up based on team preference |
| **Monorepo tooling** | Not needed until multiple packages share code |

---

## How to Use This Blueprint

1. **Read through the entire document** to understand the architectural philosophy.
2. **Adapt to your stack** — replace Python/FastAPI/React specifics with your chosen tools.
3. **Start with the project structure** (Section 1) — create the directory skeleton.
4. **Set up containerization** (Section 2) — get Docker running first.
5. **Build the database layer** (Section 3) — schema, migrations, seed data.
6. **Implement layers bottom-up** — Models → Repositories → Services → API.
7. **Add the frontend** (Section 5) — core infrastructure first, then features.
8. **Configure quality tools** (Sections 8-10) — type checking, linting, tests.
9. **Wire up environment config** (Section 11) — `.env` files and settings classes.

The goal is to have a production-grade foundation from day one, not to add infrastructure retroactively.

---

## Appendix: Future Documentation

The following gaps have been identified but not yet documented in this blueprint. They are organized by priority for future expansion.

### Significant Gaps

- Alembic async migration setup (async engine, URL conversion, NullPool, model auto-detection)
- Full exception hierarchy + global handler registration
- CSRF middleware implementation (token generation, exempt paths, constant-time comparison)
- Application factory & lifespan manager (startup/shutdown, middleware ordering, exception handler registration)
- Database session management (DatabaseManager class, lazy init, dual async/sync sessions, pool config rationale)
- CORS merge pattern (environment variable parsing + hardcoded defaults)

### Implementation Details Missing

- Repository method signatures (pagination tuple, soft delete filtering, eager loading, bulk operations)
- Service layer conventions (model_validate conversion, log_started/completed/rejected at every boundary, MAX_BULK_RECORDS, bulk return format)
- API endpoint conventions (try-except-else pattern, Query parameter conventions with alias, static routes before dynamic, comment-header organization)
- Dependency injection chain (exact Annotated + Depends 3-level wiring, async generator pattern, type aliases)
- Pydantic schema conventions (from_attributes=True, schema type hierarchy per entity, field validators, normalize helper functions)
- Enum pattern (str+Enum dual inheritance, snake_case values, domain grouping)
- Frontend TanStack Query hooks (query key factory pattern, hierarchical cache keys, conditional queries)
- Frontend API module pattern (object-based API with typed methods, BASE_PATH constant, .data extraction)
- Frontend routing (ProtectedLayoutWrapper, React.lazy code splitting, public vs protected route separation, nested layouts)

### Minor Gaps

- `__main__.py` entry point (dotenv loaded before imports)
- Vercel deployment config (frontend/vercel.json)
- Build system (hatchling backend, uv.lock)
- VS Code workspace settings (MCP agent config)
- Utils (Protocol-based typing for equipment checking)
