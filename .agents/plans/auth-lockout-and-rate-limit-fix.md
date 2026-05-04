# Feature: Restore /auth/login lockout + per-IP rate limiting (E2E sign-off Bugs A & C)

The following plan should be complete, but it's important that you validate documentation and codebase patterns and task sanity before you start implementing.

Pay special attention to naming of existing utils, types, and models. Import from the right files etc.

## Feature Description

The 2026-05-04 master E2E sign-off run (`run-20260504-103605/E2E-SIGNOFF-REPORT-FINAL.md`) promoted four bugs (A/C/D/E). Verification on 2026-05-04 against the live `dev` branch confirmed Bugs **D** and **E** were already resolved in umbrella commit `eba4162` (`fix(e2e-signoff): umbrella resolution for 6 master-plan-run bugs`). Bugs **A** and **C** are still live in source. They compound: Bug A makes the documented 5-attempt lockout never trigger (counter rolled back on the failed-login `raise`), and Bug C leaves `/api/v1/auth/login` unthrottled (rate-limit constants defined but never applied; no global middleware registered). Together they leave `/api/v1/auth/login` fully open to brute force — credential stuffing or password spray runs unchecked.

This feature lands two surgical fixes:

1. **Bug A** — make the failed-login increment durable across the `InvalidCredentialsError` raise so the counter actually reaches `MAX_FAILED_ATTEMPTS=5` and the account locks for 15 minutes.
2. **Bug C** — apply `@limiter.limit(AUTH_LIMIT)` ("5/minute") to the login route AND register `SlowAPIMiddleware` on the app so the existing default 200/min limit fires on every other route.

## User Story

As a **platform operator**
I want **the documented lockout (5 failed attempts → 15 min) and per-IP rate limit (5/min on /auth/login, 200/min default) to actually fire**
So that **brute-force attacks against `/api/v1/auth/login` are bounded by both the per-account counter and the per-IP limiter, matching the security posture stated in `update2_instructions.md` Reqs 16.5–16.7 and 69.1–69.4**

## Problem Statement

**Bug A** (`src/grins_platform/services/auth_service.py:305-334, 405-416`):
`AuthService.authenticate` calls `await self._handle_failed_login(staff)` then immediately `raise InvalidCredentialsError`. `_handle_failed_login` delegates to `staff_repository.update_auth_fields` which only `flush()`es (line 515) — it never commits. The FastAPI session dependency `get_session` (`src/grins_platform/database.py:114-120`) wraps the request in `try: yield session; await session.commit() except: await session.rollback()`, so the propagating `InvalidCredentialsError` rolls back the failed-login UPDATE. After 5 wrong attempts, `staff.failed_login_attempts` is still `0` and `MAX_FAILED_ATTEMPTS=5` (`auth_service.py:46`) is never reached. Verified live 2026-05-04: 5 wrong + 1 correct on the dev `admin` user → HTTP 200, `failed_login_attempts=0` in DB.

Existing unit tests at `src/grins_platform/tests/unit/test_auth_service.py:398-446` pass because `mock_staff_repository.update_auth_fields` is an `AsyncMock` — there is no real session, no rollback, no regression coverage. The bug is invisible to the unit suite.

**Bug C** (`src/grins_platform/middleware/rate_limit.py:38`, `src/grins_platform/api/v1/auth.py:84`, `src/grins_platform/app.py:267`):
`AUTH_LIMIT = "5/minute"` is exported but `grep AUTH_LIMIT src/grins_platform/api` returns 0 matches. The login route has no `@limiter.limit(...)` decorator. Separately, `setup_rate_limiting(app)` only sets `app.state.limiter` and registers the exception handler — `SlowAPIMiddleware` is never added (`grep SlowAPIMiddleware src/grins_platform` → 0 matches), so `default_limits=["200/minute"]` never fires. Verified 2026-05-04: 80 sequential bad-credential POSTs to `/api/v1/auth/login` → 80×401, zero 429s.

## Solution Statement

**Bug A** — fix at the route layer (Layer 2 from CANDIDATE-FINDINGS.md option list): in `api/v1/auth.py:login`, catch `InvalidCredentialsError` from `auth_service.authenticate(...)`, **commit the session** to persist the failed-login increment, then raise the 401 `HTTPException`. This keeps the auth transaction (which is purely a SELECT + the failed-login UPDATE on the wrong-password branch) cleanly committed before propagating the error to the client. We pick the route-layer fix over a service-layer commit because the service is repository/session-agnostic and adding `await self.session.commit()` inside a domain service would invert the layer contract used elsewhere in the codebase (`get_session` is the single owner of commit/rollback). The route-layer pattern also keeps the lockout-success path untouched.

**Bug C** — two-line fix matching the existing `@limiter.limit` pattern used by `portal.py:270` and `callrail_webhooks.py:253`:
1. Decorate `POST /api/v1/auth/login` with `@limiter.limit(AUTH_LIMIT)` and add a `request: Request` (Starlette) parameter to the signature so slowapi can derive the per-IP key. Rename the existing Pydantic body parameter from `request: LoginRequest` to `body: LoginRequest` to avoid shadowing.
2. Register `SlowAPIMiddleware` in `create_app` (after `setup_rate_limiting`) so `default_limits=["200/minute"]` fires on every undecorated route.

## Feature Metadata

**Feature Type**: Bug Fix (security)
**Estimated Complexity**: Low
**Primary Systems Affected**: `api/v1/auth.py`, `middleware/rate_limit.py`, auth tests (no service-layer change)
**Dependencies**: `slowapi==0.1.9` (verified installed via `uv pip show slowapi`; declared `slowapi>=0.1.9` in `pyproject.toml:50`)

### Verified version-pinned facts

These were confirmed against the installed `slowapi==0.1.9` source on 2026-05-04 — do **not** assume; the API surface here is what to write against:

- `Limiter.reset()` is the public reset hook (`slowapi/extension.py:354`). With the default in-memory storage (`memory://`, set when `REDIS_URL` is unset, see `middleware/rate_limit.py:28-33`) it succeeds; with a Redis backend it may raise `NotImplementedError` which `reset()` swallows with a warning.
- `SlowAPIMiddleware` is a `BaseHTTPMiddleware` subclass at `slowapi/middleware.py:116`. Use `from slowapi.middleware import SlowAPIMiddleware` — **not** `SlowAPIASGIMiddleware`.
- When a route has BOTH `@limiter.limit(...)` and `SlowAPIMiddleware` is registered, the middleware exempts the route via `_should_exempt → name in limiter._route_limits` (`slowapi/middleware.py:109-111`). The decorator handles its own check; no double-counting.
- The decorator at `slowapi/extension.py:707-715` walks the function signature and **hard-requires a parameter literally named `request` or `websocket`**: `if parameter.name == "request" or parameter.name == "websocket": ...`. Renaming the existing Pydantic body param `request: LoginRequest → body: LoginRequest` is therefore mandatory; the Starlette `Request` parameter must be named `request`.
- When the decorator raises `RateLimitExceeded`, FastAPI's exception-handling layer (`ExceptionMiddleware`, registered inside the app under user middleware) catches it via `app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)` already wired at `middleware/rate_limit.py:92-95`. The resulting `JSONResponse` flows back out through user middleware as a normal Response — `_catch_unhandled_exceptions` (`app.py:229-253`) will NOT see it as an exception and will not 500-mask it.
- Verified `auth_service.repository.session` attribute chain: `AuthService.__init__` sets `self.repository = repository` (`auth_service.py:118`); `StaffRepository.__init__` sets `self.session = session` (`staff_repository.py:48`). Therefore `await auth_service.repository.session.commit()` is the correct call from the route.
- Verified no test constructs the route function directly with a keyword `request=LoginRequest(...)` — all tests POST JSON via `httpx.AsyncClient`. The `LoginRequest` instances at `tests/unit/test_auth_schemas.py:37,48,57,64,71,78,85,90` and `tests/functional/test_marketing_remaining_functional.py:516` are schema-only construction and not affected by the parameter rename.

---

## CONTEXT REFERENCES

### Relevant Codebase Files — IMPORTANT: YOU MUST READ THESE FILES BEFORE IMPLEMENTING!

- `src/grins_platform/services/auth_service.py` (lines 305-334, 355-430) — `_handle_failed_login` + `authenticate`. Bug A's call site. The exception is raised after the repository call returns; there is no try/except in `authenticate`.
- `src/grins_platform/repositories/staff_repository.py` (lines 464-528) — `update_auth_fields`: builds an UPDATE…RETURNING, executes, then `await self.session.flush()` (line 515). **Note**: no commit. The session lifecycle is owned by the FastAPI dependency.
- `src/grins_platform/database.py` (lines 108-120) — `DatabaseManager.get_session`: the commit/rollback owner. This is why a flushed-only write is lost when `authenticate` raises.
- `src/grins_platform/api/v1/auth.py` (lines 84-154) — `POST /auth/login` route. Already catches `InvalidCredentialsError` and `AccountLockedError` — extend the `InvalidCredentialsError` branch to commit before raising the 401.
- `src/grins_platform/api/v1/auth_dependencies.py` — `get_auth_service` dependency. **READ THIS** to confirm how the session is plumbed into the service so the route can call `auth_service.repository.session.commit()` (or equivalent) without breaking abstraction.
- `src/grins_platform/middleware/rate_limit.py` (entire file, ~120 lines) — defines `limiter`, `AUTH_LIMIT="5/minute"`, `setup_rate_limiting`. The fix in `setup_rate_limiting` adds `SlowAPIMiddleware`.
- `src/grins_platform/api/v1/portal.py` (lines 260-300) — canonical `@limiter.limit(PORTAL_LIMIT)` example with Starlette `Request` parameter. **MIRROR THIS PATTERN** in `auth.py:login`.
- `src/grins_platform/api/v1/callrail_webhooks.py` (lines 245-260) — second canonical `@limiter.limit` example (with `key_func=` override). Pattern reference.
- `src/grins_platform/app.py` (lines 164-307) — `create_app`. Middleware add order matters: Starlette wraps last-added first (outermost). `setup_rate_limiting(app)` is at line 267; `SlowAPIMiddleware` should be added immediately after.
- `src/grins_platform/tests/unit/test_auth_service.py` (lines 390-470) — existing lockout unit tests. They mock the repository so they cannot catch Bug A. **Add an integration-shaped test that uses a real session** (see fixtures pattern below).
- `src/grins_platform/tests/test_auth_api.py` (lines 134-230) — existing route-layer tests for `/auth/login`. **Add a new test class** `TestLoginRateLimit` that probes 6 sequential bad-credential POSTs and asserts the 6th returns 429.
- `src/grins_platform/tests/integration/test_cors_on_5xx.py` (lines 1-50) — pattern for spinning up the real `app` via `httpx.ASGITransport` for app-level integration probes. **MIRROR THIS** for the rate-limit integration test (lockout integration test follows the same pattern but mounts a real DB session).
- `src/grins_platform/tests/integration/test_auth_integration.py` (lines 1-60) — existing auth integration setup. Use as the fixture starting point for the new lockout-persistence integration test.
- `src/grins_platform/tests/integration/conftest.py` — shared fixtures for sessions/DB. Read to find the `async_session` (or equivalent) fixture name used elsewhere.
- `e2e-screenshots/master-plan/runs/run-20260504-103605/CANDIDATE-FINDINGS.md` (Bugs A and C sections, lines 1-105) — verbatim repro commands + DB snapshots. The plan's acceptance criteria mirror these repros.

### New Files to Create

- `src/grins_platform/tests/integration/test_auth_login_commit_contract.py` — integration test that proves the route awaits `auth_service.repository.session.commit()` BEFORE the 401 propagates when `authenticate` raises `InvalidCredentialsError`. Uses the same `MagicMock(spec=AuthService)` + `dependency_overrides[get_auth_service]` pattern as `test_auth_integration.py:155-205`. The test asserts `commit.await_count == 1` after the 401. (This is the deterministic, codebase-aligned shape of the Bug A regression cover; a real-DB integration test isn't possible because this codebase has no PostgreSQL test fixture — all "integration" tests mock `get_db_session`.)
- `src/grins_platform/tests/integration/test_auth_rate_limit.py` — integration test that hits `/api/v1/auth/login` 6× bad-credentials within one minute and asserts the 6th returns 429 (`AUTH_LIMIT="5/minute"`). Resets `limiter` storage in an autouse fixture so the test is hermetic across pytest runs.

### Files to Update

- `src/grins_platform/api/v1/auth.py` — add `@limiter.limit(AUTH_LIMIT)` to `login`, add Starlette `Request` parameter named `request`, rename body param to `body: LoginRequest`, commit on `InvalidCredentialsError`.
- `src/grins_platform/middleware/rate_limit.py` — `setup_rate_limiting` adds `SlowAPIMiddleware` via `app.add_middleware(SlowAPIMiddleware)`.
- `src/grins_platform/services/auth_service.py` — **NO CHANGE** to the service layer (the route-layer commit pattern keeps domain code clean). Optional doc-string note in `authenticate` referencing the route-layer commit contract.
- `src/grins_platform/tests/integration/test_auth_integration.py` — the existing `mock_auth_service` fixture (line 124) uses `MagicMock(spec=AuthService)`. With the route-layer commit fix, `test_login_invalid_credentials_returns_401` (line 207) and any other test where `authenticate` raises `InvalidCredentialsError` will now also call `await mock_auth_service.repository.session.commit()`. By default `spec=AuthService` does **not** define `repository.session.commit` — it's accessed as a regular `MagicMock` and the `await` raises `TypeError: object MagicMock can't be used in 'await' expression`. **MUST update the fixture** to attach an `AsyncMock`-shaped commit (see Task 3 below).
- `src/grins_platform/tests/test_auth_api.py` — same risk in unit-level route tests for the InvalidCredentialsError branch (line 217); same fixture-shape update needed (or override per-test).

### Relevant Documentation — YOU SHOULD READ THESE BEFORE IMPLEMENTING!

- [slowapi: usage with FastAPI](https://slowapi.readthedocs.io/en/latest/#fastapi)
  - Specific section: "Per-route limit" + "Per-app default with middleware"
  - Why: shows the exact `@limiter.limit("5/minute")` decorator pattern + the `app.add_middleware(SlowAPIMiddleware)` call needed for default_limits to fire.
- [slowapi.middleware source](https://github.com/laurents/slowapi/blob/master/slowapi/middleware.py)
  - Specific section: `class SlowAPIMiddleware(BaseHTTPMiddleware)` (line 116)
  - Why: confirms the import path used in this codebase: `from slowapi.middleware import SlowAPIMiddleware`.
- [SQLAlchemy 2.0: AsyncSession.commit](https://docs.sqlalchemy.org/en/20/orm/session_api.html#sqlalchemy.orm.Session.commit)
  - Specific section: "Committing"
  - Why: confirms semantics — flushed pending writes get persisted on commit; subsequent statements use a new transaction.
- [FastAPI: dependencies with yield](https://fastapi.tiangolo.com/tutorial/dependencies/dependencies-with-yield/)
  - Specific section: "Dependencies with yield and HTTPException"
  - Why: documents that `HTTPException` raised AFTER a yield-dependency is a normal exception, so the dependency's exception branch runs (rollback in our case). Confirms why we must commit BEFORE raising the 401.

### Patterns to Follow

**Decorating a route with @limiter.limit (mirror `portal.py:270` exactly):**

```python
from starlette.requests import Request  # NOT fastapi.Request
from grins_platform.middleware.rate_limit import AUTH_LIMIT, limiter

@router.post("/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
@limiter.limit(AUTH_LIMIT)  # pyright: ignore[reportUntypedFunctionDecorator]
async def login(
    request: Request,             # MUST be named exactly `request` — slowapi 0.1.9 hard-checks the param name (extension.py:709)
    body: LoginRequest,           # renamed from `request` (was Pydantic body)
    response: Response,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> LoginResponse:
    ...
```

**Add SlowAPIMiddleware in setup_rate_limiting (mirror existing add_middleware pattern in `app.py:255-266`):**

```python
# in middleware/rate_limit.py
from slowapi.middleware import SlowAPIMiddleware

def setup_rate_limiting(app: FastAPI) -> None:
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)  # NEW: enables default_limits + key derivation for decorated routes
    logger.info("security.rate_limit.configured", ...)
```

**Commit-before-raise on InvalidCredentialsError (route layer):**

```python
# in api/v1/auth.py:login
try:
    result = await auth_service.authenticate(body.username, body.password)
    staff, access_token, refresh_token, csrf_token = result
except InvalidCredentialsError as e:
    # Persist the failed-login increment before the session rolls back.
    # The repository flushed the UPDATE but did not commit; without this
    # commit, get_session() rolls it back and the lockout counter stays at 0.
    await auth_service.repository.session.commit()
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid username or password",
    ) from e
except AccountLockedError as e:
    # No commit needed — _is_account_locked is read-only.
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Account is locked. Please try again later.",
    ) from e
```

**Naming conventions:** snake_case for functions/vars, PascalCase for classes. Imports in groups: stdlib → third-party → first-party (`grins_platform.*`). Match the existing import order in each file you touch.

**Error handling:** Domain services raise typed exceptions from `grins_platform.exceptions.*`. Routes translate to `HTTPException`. Never raise `HTTPException` from a service.

**Logging pattern:** All service classes use `LoggerMixin` with `self.log_started/log_completed/log_rejected`. The route layer uses module-level `get_logger(__name__)` from `log_config`. Don't add new logs unless you need to track a security signal.

---

## IMPLEMENTATION PLAN

### Phase 1: Foundation — verify session ownership

Before changing the route, confirm the route can reach the session via `auth_service.repository.session`. (`AuthService.__init__` stores `self.repository = repository`; `StaffRepository.__init__` stores `self.session = session`.) **Tasks:** read `auth_dependencies.py:get_auth_service` and confirm the chain. No code changes in this phase.

### Phase 2: Bug A — commit failed-login increment in route

Add a single `await auth_service.repository.session.commit()` inside the existing `except InvalidCredentialsError` branch in `api/v1/auth.py:login`. This persists the UPDATE that `_handle_failed_login → update_auth_fields` already flushed, before the 401 propagates and `get_session` runs its rollback branch. Add a docstring note in `auth_service.authenticate` pointing readers to the route-layer commit contract so future changes don't accidentally regress.

### Phase 3: Bug C — apply @limiter.limit + register SlowAPIMiddleware

- Decorate `login` with `@limiter.limit(AUTH_LIMIT)`.
- Add Starlette `Request` to the signature, rename Pydantic body parameter `request → body`. Update the 4 internal references (`request.username`, `request.password` → `body.username`, `body.password`).
- Add `app.add_middleware(SlowAPIMiddleware)` inside `setup_rate_limiting`.

### Phase 4: Testing & Validation

- Update existing unit/route tests that referenced `request: LoginRequest` (search for `mock_auth_service.authenticate` callers in `test_auth_api.py` — they POST JSON bodies and don't depend on the parameter name, so most tests need no change; but any test that constructs `LoginRequest()` and passes it positionally must be re-checked).
- Add new integration test `test_auth_lockout_persistence.py` that verifies after 5 wrong + 1 correct, the 6th returns 401 (locked).
- Add new integration test `test_auth_rate_limit.py` that verifies after 5 bad attempts within one minute, the 6th returns 429.
- Run the full unit + integration suite and confirm no regressions.

---

## STEP-BY-STEP TASKS

IMPORTANT: Execute every task in order, top to bottom. Each task is atomic and independently testable.

### 1. UPDATE `src/grins_platform/api/v1/auth.py` — add Starlette Request, rename body, decorate, commit-before-raise

- **IMPLEMENT**:
  - Add `from starlette.requests import Request` to imports (use Starlette, not `fastapi.Request` — match `portal.py:273`).
  - Add `from grins_platform.middleware.rate_limit import AUTH_LIMIT, limiter` to imports.
  - On `login` (line 84): rename signature `request: LoginRequest` → `body: LoginRequest`; add `request: Request` parameter (Starlette) — **the parameter MUST be named exactly `request`** (slowapi 0.1.9 hard-checks the param name in `extension.py:709`); add `@limiter.limit(AUTH_LIMIT)  # pyright: ignore[reportUntypedFunctionDecorator]` between `@router.post(...)` and `async def login`.
  - Update the body of `login` to use `body.username` and `body.password` (was `request.username`, `request.password`).
  - In the existing `except InvalidCredentialsError as e:` branch, insert `await auth_service.repository.session.commit()` BEFORE the `raise HTTPException(...)`. Add a single-line comment: `# Persist failed-login increment before session rollback (Bug A).`
- **PATTERN**: `src/grins_platform/api/v1/portal.py:270-285` (Starlette Request + decorator), `src/grins_platform/api/v1/callrail_webhooks.py:253-256` (decorator placement above `async def`).
- **IMPORTS**: `from starlette.requests import Request`, `from grins_platform.middleware.rate_limit import AUTH_LIMIT, limiter`.
- **GOTCHA**: slowapi 0.1.9 inspects the function signature for a parameter literally named `request` (or `websocket`); see `slowapi/extension.py:707-715`. The Starlette `Request` MUST be named `request`. The existing Pydantic body MUST be renamed to something else (`body` is consistent with FastAPI conventions). Do not "import as" or alias to dodge the name collision — slowapi reads `parameter.name`, not the type.
- **GOTCHA**: `auth_service.repository.session.commit()` — verified attribute chain: `AuthService.repository` (`auth_service.py:118`) → `StaffRepository.session` (`staff_repository.py:48`). If reading the file you're editing shows different names, follow what's actually there but flag the divergence.
- **GOTCHA**: Do NOT also commit on the `AccountLockedError` branch — `_is_account_locked` is a read-only check that performed no UPDATE, so there's nothing to persist. A spurious commit here would not break correctness but is dead code.
- **GOTCHA**: The route now has the decorator BEFORE `async def`. With slowapi 0.1.9, the `@router.post(...)` decorator MUST be ABOVE `@limiter.limit(...)` (FastAPI's route decorator wraps slowapi's wrapper). Mirror `portal.py:259-271` exactly:
  ```
  @router.post("/login", ...)
  @limiter.limit(AUTH_LIMIT)  # pyright: ignore[reportUntypedFunctionDecorator]
  async def login(request: Request, body: LoginRequest, ...):
  ```
- **VALIDATE**: `cd /Users/kirillrakitin/Grins_irrigation_platform && uv run python -c "from grins_platform.api.v1.auth import login; import inspect; params = list(inspect.signature(login).parameters); print(params); assert 'request' in params and 'body' in params"`.

### 2. UPDATE `src/grins_platform/middleware/rate_limit.py` — register SlowAPIMiddleware

- **IMPLEMENT**:
  - Add `from slowapi.middleware import SlowAPIMiddleware` to the third-party imports block (NOT inside the `if TYPE_CHECKING:` block — it's used at runtime).
  - Inside `setup_rate_limiting`, add `app.add_middleware(SlowAPIMiddleware)` after the `add_exception_handler` call and before the `logger.info` call.
  - Add `"SlowAPIMiddleware"` to `__all__` only if you want it re-exported (optional; current `__all__` does not include third-party names — leave it out for parity with existing pattern).
- **PATTERN**: `src/grins_platform/app.py:255-266` (existing `app.add_middleware` calls for `CORSMiddleware`, `RequestSizeLimitMiddleware`, `SecurityHeadersMiddleware`).
- **IMPORTS**: `from slowapi.middleware import SlowAPIMiddleware`.
- **GOTCHA**: Order matters. Starlette wraps later-added middleware as outermost; `setup_rate_limiting` is called at `app.py:267`, AFTER `SecurityHeadersMiddleware` (line 266). Final wrap order (outermost → innermost): `_attach_request_id` (added at app.py:274) → `CORS` → `RequestSizeLimit` → `SecurityHeaders` → `SlowAPI` (innermost; closest to route). This is correct: rate-limit checks fire close to the route, but the JSON 429 response still flows back through CORS so browsers receive the right headers (validated indirectly by `test_cors_on_5xx.py`).
- **GOTCHA**: Do NOT use `SlowAPIASGIMiddleware`. Use `SlowAPIMiddleware` (`BaseHTTPMiddleware` subclass) — confirmed at `slowapi/middleware.py:116`. The ASGI variant requires manual `Limiter._auto_check` plumbing.
- **GOTCHA**: With both `@limiter.limit` and the middleware present, `SlowAPIMiddleware._should_exempt` defers to the decorator (`slowapi/middleware.py:109-111` — `if name in limiter._route_limits: return True`). No double-counting.
- **GOTCHA**: `SlowAPIMiddleware` will read `app.state.limiter`, which `setup_rate_limiting` has already set on the prior line. Order inside the function is: set limiter → add exception handler → add middleware → log.
- **VALIDATE**: `cd /Users/kirillrakitin/Grins_irrigation_platform && uv run python -c "from grins_platform.app import create_app; app = create_app(); names = [m.cls.__name__ for m in app.user_middleware]; print(names); assert 'SlowAPIMiddleware' in names"`.

### 3. UPDATE existing auth tests so `mock_auth_service.repository.session.commit` is awaitable

- **IMPLEMENT**:
  - In `src/grins_platform/tests/integration/test_auth_integration.py`, modify the `mock_auth_service` fixture (lines 123-134) by appending these two lines BEFORE `return service`:
    ```python
    service.repository = MagicMock()
    service.repository.session = MagicMock()
    service.repository.session.commit = AsyncMock()
    ```
  - In `src/grins_platform/tests/test_auth_api.py`, do the same in the `mock_auth_service` fixture (lines 110-119). Use `from unittest.mock import AsyncMock, MagicMock` if not already imported.
  - **Why**: Task 1 makes the route call `await auth_service.repository.session.commit()` on the InvalidCredentialsError branch. With `MagicMock(spec=AuthService)`, `service.repository.session.commit` is a regular `MagicMock` whose return is a `MagicMock` — `await`-ing it raises `TypeError: object MagicMock can't be used in 'await' expression`. Attaching an `AsyncMock` makes the call awaitable in tests.
  - **Search for additional sites**: `grep -rn "MagicMock(spec=AuthService)" src/grins_platform/tests` — apply the same shape fix anywhere else `authenticate.side_effect = InvalidCredentialsError(...)` is used.
- **PATTERN**: existing fixture body at `tests/integration/test_auth_integration.py:124-134`.
- **GOTCHA**: Do NOT use `MagicMock(spec=StaffRepository)` for `service.repository` — `spec` would block the `.session` attribute (StaffRepository's session attr name matches, but using bare `MagicMock` is simpler and behavior-identical for these tests).
- **GOTCHA**: Tests where `authenticate.side_effect = AccountLockedError(...)` do NOT need the awaitable commit — the locked branch does NOT call commit (the auth flow short-circuits before `_handle_failed_login`). Confirm by re-reading the route in Task 1 output.
- **VALIDATE**: `cd /Users/kirillrakitin/Grins_irrigation_platform && uv run pytest src/grins_platform/tests/integration/test_auth_integration.py src/grins_platform/tests/test_auth_api.py -q` — expect green.

### 4. CREATE `src/grins_platform/tests/integration/test_auth_login_commit_contract.py`

- **IMPLEMENT**: New integration test proving the route awaits `commit()` on the InvalidCredentialsError branch (Bug A regression cover). Real-PostgreSQL DB tests are not available in this codebase — all "integration" tests mock `get_db_session` (verified by reading `tests/integration/fixtures.py` and surrounding files). The deterministic regression cover therefore is at the route layer: assert the route awaits `auth_service.repository.session.commit()` exactly once before the 401 returns.

  Skeleton:

  ```python
  from __future__ import annotations
  from typing import TYPE_CHECKING
  from unittest.mock import AsyncMock, MagicMock

  import pytest
  from httpx import ASGITransport, AsyncClient

  from grins_platform.api.v1.auth_dependencies import get_auth_service
  from grins_platform.exceptions.auth import InvalidCredentialsError, AccountLockedError
  from grins_platform.main import app
  from grins_platform.services.auth_service import AuthService

  if TYPE_CHECKING:
      from collections.abc import AsyncGenerator


  @pytest.fixture
  async def async_client() -> AsyncGenerator[AsyncClient, None]:
      transport = ASGITransport(app=app)
      async with AsyncClient(transport=transport, base_url="http://test") as client:
          yield client


  def _make_service_with_commit_spy() -> tuple[MagicMock, AsyncMock]:
      svc = MagicMock(spec=AuthService)
      svc.authenticate = AsyncMock(side_effect=InvalidCredentialsError("bad"))
      commit_spy = AsyncMock()
      svc.repository = MagicMock()
      svc.repository.session = MagicMock()
      svc.repository.session.commit = commit_spy
      return svc, commit_spy


  @pytest.mark.integration
  @pytest.mark.asyncio
  async def test_invalid_credentials_branch_commits_before_401(
      async_client: AsyncClient,
  ) -> None:
      """Bug A regression: route MUST commit the failed-login increment
      before propagating the 401, otherwise get_session() rolls it back."""
      svc, commit_spy = _make_service_with_commit_spy()
      app.dependency_overrides[get_auth_service] = lambda: svc
      try:
          resp = await async_client.post(
              "/api/v1/auth/login",
              json={"username": "x", "password": "y"},
          )
          assert resp.status_code == 401
          assert commit_spy.await_count == 1, (
              "Route must commit the failed-login UPDATE before raising 401 "
              "(Bug A: e2e-signoff 2026-05-04)."
          )
      finally:
          app.dependency_overrides.clear()


  @pytest.mark.integration
  @pytest.mark.asyncio
  async def test_locked_branch_does_not_commit(async_client: AsyncClient) -> None:
      """The AccountLockedError branch must NOT call commit (no pending writes)."""
      svc = MagicMock(spec=AuthService)
      svc.authenticate = AsyncMock(side_effect=AccountLockedError("locked"))
      svc.repository = MagicMock()
      svc.repository.session = MagicMock()
      svc.repository.session.commit = AsyncMock()
      app.dependency_overrides[get_auth_service] = lambda: svc
      try:
          resp = await async_client.post(
              "/api/v1/auth/login",
              json={"username": "x", "password": "y"},
          )
          assert resp.status_code == 401
          assert svc.repository.session.commit.await_count == 0
      finally:
          app.dependency_overrides.clear()
  ```

- **PATTERN**: `tests/integration/test_auth_integration.py:137-235` (ASGITransport client + dependency_override pattern).
- **GOTCHA**: Mark with `@pytest.mark.integration` AND `@pytest.mark.asyncio`. `pyproject.toml:592` sets `asyncio_mode = "auto"` so the asyncio marker is technically optional, but matching existing tests is safer.
- **GOTCHA**: `app.dependency_overrides.clear()` MUST run in `finally` — otherwise leaked overrides poison subsequent tests in the same pytest session.
- **GOTCHA**: Do NOT also stub `commit` to raise — the test must prove commit succeeds before the 401. Defaulting `AsyncMock()` returns `None` on await, which is what `AsyncSession.commit()` returns in production.
- **VALIDATE**: `cd /Users/kirillrakitin/Grins_irrigation_platform && uv run pytest src/grins_platform/tests/integration/test_auth_login_commit_contract.py -q`.

### 5. CREATE `src/grins_platform/tests/integration/test_auth_rate_limit.py`

- **IMPLEMENT**: New integration test proving `@limiter.limit(AUTH_LIMIT)` fires (Bug C regression cover). Skeleton:

  ```python
  from __future__ import annotations
  from typing import TYPE_CHECKING
  from unittest.mock import AsyncMock, MagicMock

  import pytest
  from httpx import ASGITransport, AsyncClient

  from grins_platform.api.v1.auth_dependencies import get_auth_service
  from grins_platform.exceptions.auth import InvalidCredentialsError
  from grins_platform.main import app
  from grins_platform.middleware.rate_limit import limiter
  from grins_platform.services.auth_service import AuthService

  if TYPE_CHECKING:
      from collections.abc import AsyncGenerator


  @pytest.fixture(autouse=True)
  def _reset_limiter_storage() -> None:
      """Ensure each test starts with a clean per-IP bucket.

      slowapi 0.1.9 exposes Limiter.reset() at extension.py:354. With
      the in-memory backend (REDIS_URL unset) it succeeds; with a
      Redis backend it logs a warning and is a no-op.
      """
      limiter.reset()


  @pytest.fixture
  async def async_client() -> AsyncGenerator[AsyncClient, None]:
      transport = ASGITransport(app=app)
      async with AsyncClient(transport=transport, base_url="http://test") as client:
          yield client


  def _override_auth_with_invalid() -> None:
      svc = MagicMock(spec=AuthService)
      svc.authenticate = AsyncMock(side_effect=InvalidCredentialsError("bad"))
      svc.repository = MagicMock()
      svc.repository.session = MagicMock()
      svc.repository.session.commit = AsyncMock()
      app.dependency_overrides[get_auth_service] = lambda: svc


  @pytest.mark.integration
  @pytest.mark.asyncio
  async def test_login_429_after_5_attempts_per_minute(
      async_client: AsyncClient,
  ) -> None:
      """Bug C regression: 5/min on /auth/login. The 6th hit returns 429."""
      _override_auth_with_invalid()
      try:
          codes: list[int] = []
          for _ in range(6):
              r = await async_client.post(
                  "/api/v1/auth/login",
                  json={"username": "x", "password": "y"},
              )
              codes.append(r.status_code)
          assert codes[:5] == [401] * 5, codes
          assert codes[5] == 429, codes
          # And confirm the response shape matches rate_limit.py:75-86.
          last = await async_client.post(
              "/api/v1/auth/login",
              json={"username": "x", "password": "y"},
          )
          assert last.status_code == 429
          body = last.json()
          assert body["error"]["code"] == "RATE_LIMIT_EXCEEDED"
          assert "Retry-After" in {k.title() for k in last.headers.keys()}
      finally:
          app.dependency_overrides.clear()
  ```

- **PATTERN**: `tests/integration/test_cors_on_5xx.py` for the ASGITransport setup; `tests/integration/test_auth_integration.py:137-235` for dependency_override pattern.
- **GOTCHA**: The `limiter` is a module-level singleton (`middleware/rate_limit.py:31`); state persists between tests. Always reset via the autouse fixture above. **Do NOT call `limiter._storage.reset()` directly** — `Limiter.reset()` is the public API at `slowapi/extension.py:354`.
- **GOTCHA**: The route's `key_func` is `slowapi.util.get_remote_address`. Under `httpx.ASGITransport`, the `client.host` is `127.0.0.1` (or empty). All requests in one test share the same key, so the 5-attempt window applies as documented. Production uses CloudFlare/Railway IPs; same code path.
- **GOTCHA**: 6th request is the violator. Five 401s then one 429. Don't off-by-one.
- **GOTCHA**: Skip the optional "global default 200/min" probe — registering 201 sequential POSTs against `/health` (a GET) is awkward, and slowapi default_limits do also gate decorated routes (already covered by AUTH_LIMIT). Coverage of the global default can land in a follow-up plan if operators want it.
- **VALIDATE**: `cd /Users/kirillrakitin/Grins_irrigation_platform && uv run pytest src/grins_platform/tests/integration/test_auth_rate_limit.py -q`.

### 6. UPDATE `src/grins_platform/services/auth_service.py` — docstring note (optional)

- **IMPLEMENT**: In `authenticate`'s docstring, after the `Validates:` line, append a short note: `Note: route layer is responsible for committing the failed-login increment before propagating InvalidCredentialsError so the lockout counter persists across the request session boundary (Bug A, e2e-signoff 2026-05-04).`
- **PATTERN**: Existing docstring style in this file.
- **VALIDATE**: `cd /Users/kirillrakitin/Grins_irrigation_platform && uv run ruff check src/grins_platform/services/auth_service.py`.

### 7. RUN full validation suite

- **IMPLEMENT**: Run all level-1/2/3 commands listed in VALIDATION COMMANDS below.
- **VALIDATE**: All commands pass; promote no new ruff/mypy errors.

### 8. MANUAL probe against running dev (post-deploy verification, optional but recommended)

- **IMPLEMENT**: After merging to dev and Railway redeploys, replicate the original repros from `CANDIDATE-FINDINGS.md` lines 11-25 (Bug A) and lines 82-92 (Bug C).
  - Bug A repro: 5×wrong + 1×correct → 6th should now be 401 (`Account is locked`).
  - Bug C repro: 80×bad-credential POST → distribution should be 5×401 + 75×429 (or 5×401 + 1×429 + a long retry-after window depending on bucket reset semantics).
- **GOTCHA**: Resetting the locked admin user requires DB access (`UPDATE staff SET failed_login_attempts=0, locked_until=NULL WHERE username='admin';`). Per memory `feedback_no_remote_alembic`, do NOT run remote alembic; use `railway ssh` for the targeted UPDATE only.
- **VALIDATE**: 6th login returns 401 + `Account is locked. Please try again later.` body; rate-limit probe shows ≥1 429.

---

## TESTING STRATEGY

### Unit Tests

- **Existing auth_service unit tests** at `tests/unit/test_auth_service.py:390-470` continue to pass unchanged. They use mocked repositories, so they verify the increment/lockout logic in isolation. They do NOT cover Bug A (which requires a real session) — that gap is intentional and is closed by the new integration test.
- **Existing test_auth_api.py route tests** at `tests/test_auth_api.py:134-230` continue to pass; route-call shape is preserved (JSON-body POSTs are unchanged by the body→`body` rename).

### Integration Tests

- **NEW** `test_auth_login_commit_contract.py` covers Bug A's contract: route awaits `commit` exactly once on the InvalidCredentialsError branch and zero times on the AccountLockedError branch. This is the codebase-aligned shape — there's no real DB fixture to use.
- **NEW** `test_auth_rate_limit.py` covers Bug C end-to-end with the real ASGI app and the real slowapi limiter.
- **EXISTING** `test_auth_integration.py` and `test_auth_guards.py` keep passing after the fixture-shape update in Task 3.

### Edge Cases

- **Lockout while account already locked**: 5th wrong attempt locks. 6th wrong attempt should hit `_is_account_locked` and raise `AccountLockedError` (different exception, different 401 message). Confirm message is `"Account is locked. Please try again later."` not `"Invalid username or password"`.
- **Successful login after lockout window expires**: `_is_account_locked` returns false once `locked_until < now`; `_handle_successful_login` resets the counter. Cover in a follow-up integration test or rely on the existing unit-test coverage at `test_auth_service.py:471+`.
- **Rate-limit applies to bad-username too**: `/auth/login` with non-existent username also raises `InvalidCredentialsError` (auth_service.py:385) — the limiter fires before the route runs, so bad usernames count toward the 5/min bucket. Verified by the new integration test.
- **Concurrent failed logins**: two parallel requests with the same username could both flush before either commits. SQLAlchemy's default isolation level (READ COMMITTED on PostgreSQL) means one will overwrite the other's increment. Acceptable for now (counter is monotone and worst case undercounts by 1 in a brief race). Document but do NOT fix in this plan.
- **Redis storage drift**: in production the limiter uses Redis (`REDIS_URL`). Ensure tests run with in-memory backend by NOT setting `REDIS_URL` in the test env.

---

## VALIDATION COMMANDS

Execute every command to ensure zero regressions and 100% feature correctness.

### Level 1: Syntax & Style

```bash
cd /Users/kirillrakitin/Grins_irrigation_platform && uv run ruff check src/grins_platform/api/v1/auth.py src/grins_platform/middleware/rate_limit.py src/grins_platform/services/auth_service.py
```

```bash
cd /Users/kirillrakitin/Grins_irrigation_platform && uv run ruff format --check src/grins_platform/api/v1/auth.py src/grins_platform/middleware/rate_limit.py
```

### Level 2: Unit Tests

```bash
cd /Users/kirillrakitin/Grins_irrigation_platform && uv run pytest src/grins_platform/tests/unit/test_auth_service.py src/grins_platform/tests/test_auth_api.py -m unit -q
```

### Level 3: Integration Tests

```bash
cd /Users/kirillrakitin/Grins_irrigation_platform && uv run pytest src/grins_platform/tests/integration/test_auth_login_commit_contract.py src/grins_platform/tests/integration/test_auth_rate_limit.py src/grins_platform/tests/integration/test_auth_integration.py src/grins_platform/tests/integration/test_auth_guards.py -m integration -q
```

Confirm the rest of the suite is unaffected:

```bash
cd /Users/kirillrakitin/Grins_irrigation_platform && uv run pytest src/grins_platform/tests -q --ignore=src/grins_platform/tests/integration/test_auth_login_commit_contract.py --ignore=src/grins_platform/tests/integration/test_auth_rate_limit.py 2>&1 | tail -20
```

The failure delta vs the documented baseline (77 failures pre-change) MUST be ≤ 0.

### Level 4: Manual Validation (post-deploy)

Reset the test admin (one-time, via `railway ssh`):

```bash
railway ssh --service Grins-dev --environment dev "cd /app && python3 -c \"
import asyncio
from sqlalchemy import text
from grins_platform.database import get_database_manager
async def m():
    async for s in get_database_manager().get_session():
        await s.execute(text(\\\"UPDATE staff SET failed_login_attempts=0, locked_until=NULL WHERE username='admin'\\\"))
        await s.commit()
        break
asyncio.run(m())
\""
```

Bug A repro (expect 6th to be 401 locked):

```bash
for i in 1 2 3 4 5 6; do
  curl -s -X POST https://grins-dev-dev.up.railway.app/api/v1/auth/login \
    -H 'Content-Type: application/json' \
    -d "{\"username\":\"admin\",\"password\":\"wrong-$i\"}" \
    -w "\nHTTP=%{http_code}\n"
done
```

Bug C repro (expect ≥1 429):

```bash
COUNTS=""
for i in $(seq 1 80); do
  COUNTS+="$(curl -s -o /dev/null -w '%{http_code} ' -X POST https://grins-dev-dev.up.railway.app/api/v1/auth/login \
    -H 'Content-Type: application/json' -d '{"username":"x","password":"x"}')"
done
echo "$COUNTS" | tr ' ' '\n' | sort | uniq -c
# Expect: 5 401 ; 75 429   (or similar, depending on bucket reset cadence)
```

### Level 5: Additional Validation (optional)

```bash
cd /Users/kirillrakitin/Grins_irrigation_platform && uv run mypy src/grins_platform/api/v1/auth.py src/grins_platform/middleware/rate_limit.py
```

---

## ACCEPTANCE CRITERIA

- [ ] `/api/v1/auth/login` rejects the 6th attempt within 1 minute with HTTP 429 and body `error.code == "RATE_LIMIT_EXCEEDED"`.
- [ ] After 5 consecutive wrong-password POSTs, `staff.failed_login_attempts == 5` and `staff.locked_until` is set; the 6th attempt (even with the right password) returns HTTP 401 with `detail == "Account is locked. Please try again later."`.
- [ ] `app.user_middleware` after `create_app()` includes `SlowAPIMiddleware`.
- [ ] `auth.py` imports `AUTH_LIMIT` and `limiter` from `middleware.rate_limit`; `login` carries `@limiter.limit(AUTH_LIMIT)` decorator.
- [ ] Existing unit + integration tests still pass; two new integration tests added and green.
- [ ] No new ruff/mypy errors introduced (delta from baseline = 0).
- [ ] No regression in `tests/integration/test_cors_on_5xx.py` (proves the catch-all + CORS interaction still works).
- [ ] Manual repros against deployed `dev` confirm the bug is gone (post-deploy step).

---

## COMPLETION CHECKLIST

- [ ] Task 1 — auth.py decorator + commit-before-raise + body rename — applied.
- [ ] Task 2 — SlowAPIMiddleware registered in setup_rate_limiting — applied.
- [ ] Task 3 — existing tests adjusted if any used `request=LoginRequest()` keyword — verified.
- [ ] Task 4 — lockout-persistence integration test created and green.
- [ ] Task 5 — rate-limit integration test created and green.
- [ ] Task 6 — auth_service docstring note added.
- [ ] Task 7 — full validation suite green.
- [ ] Task 8 — post-deploy probes against `https://grins-dev-dev.up.railway.app` confirm both bugs gone.

---

## NOTES

- **Why route-layer commit instead of service-layer commit**: The service in this codebase doesn't own commit/rollback — `database.py:get_session` does. Adding `await self.session.commit()` inside `_handle_failed_login` works but inverts the layer contract every other service follows; new contributors would not expect a domain service to commit. The route-layer fix keeps `AuthService` repository/session-agnostic and localizes the security-critical commit at the boundary where the 401 is produced.
- **Why both decorator AND middleware**: The decorator fires `AUTH_LIMIT="5/minute"` on `/auth/login` specifically (the documented hot path). The middleware enables `default_limits=["200/minute"]` so EVERY undecorated route gets a coarse global limit too — defense in depth. Without middleware, only decorated routes throttle; that's the current state and Bug C in spirit.
- **Bug B (gap)**: The CANDIDATE-FINDINGS retracted Bug B as per-spec — `/customers` is intentionally readable by Tech per `update2_instructions.md:54`. Out of scope for this plan; logged for product/security review separately.
- **Bug D and E status**: Verified resolved in commit `eba4162` (umbrella). `send_automated_message` now accepts `customer_id`/`lead_id`/`is_internal` keyword args (`sms_service.py:532-665`); `_extract_created_at` has receipt-time fallback (`callrail_webhooks.py:75-104`); `_notify_internal_decision` uses `is_internal=True` (`estimate_service.py:631-636`). Out of scope.
- **Test-suite baseline**: The sign-off report flagged 77 failing unit tests vs documented baseline 28. That delta is unrelated to A/C and is a separate triage task — do NOT regress those numbers. After this plan's changes, the failed count should be ≤ current count + 0.
- **Slowapi version pinned at 0.1.9**: all behavior described above (parameter-name hard-check, `Limiter.reset()`, `SlowAPIMiddleware._should_exempt` deferral, `app.add_exception_handler` registration path) was verified against the installed source on 2026-05-04. If `pyproject.toml` upgrades slowapi later, re-verify each pinned fact.
- **Why no real-DB integration test**: This codebase's `tests/integration/` suite uses `app.dependency_overrides[get_db_session] = lambda: AsyncMock()` everywhere (see `test_campaign_poll_responses_flow.py:100`, `test_resource_timeline_contract.py:68`, `test_signwell_webhook_integration.py:171`, `test_appointment_notes_integration.py:94`). There is no Postgres test fixture and no Alembic migration runner in tests. The route-level commit-spy test in Task 4 is therefore the codebase-aligned shape for proving Bug A; it deterministically asserts the contract that `_handle_failed_login`'s flushed UPDATE is committed before `get_session` could roll it back. The end-to-end DB persistence is verified by the post-deploy manual probe in Task 8.

- **Confidence score**: **10/10** for one-pass implementation success. Justification:
  - Both bugs are verified live in source with exact line refs (auth_service.py:410-416 for A; rate_limit.py:38 + auth.py:84 + app.py:267 for C).
  - Each fix is a one-line behavioral change against a verified upstream API contract (slowapi 0.1.9 verified end-to-end: parameter-name check, public `Limiter.reset()`, `SlowAPIMiddleware._should_exempt` deferral, `app.add_exception_handler` chain).
  - The previously-flagged risks have been resolved with verified facts:
    - Slowapi reset hook → `Limiter.reset()` at `extension.py:354` (public, in-memory backend supported).
    - Test fixture compatibility → identified the `MagicMock(spec=AuthService).repository.session.commit` await failure mode and added Task 3 to attach an `AsyncMock` shape; documented the `AccountLockedError` branch does NOT need the same shape (no commit on that path).
    - Existing test impact → grep confirmed no callsite uses `login(request=LoginRequest(...))` keyword form, so the body parameter rename is safe.
    - Decorator/middleware interaction → `_should_exempt` defers to decorator (`middleware.py:109-111`); no double-counting.
    - Exception swallowing risk → `_catch_unhandled_exceptions` middleware (`app.py:229-253`) does NOT catch `RateLimitExceeded` because FastAPI's `ExceptionMiddleware` runs INSIDE user middleware and converts it to a JSON response before the catch-all sees it.
  - Tests are deterministic (no race conditions, no real network, no real DB) and provide direct regression coverage for both bugs.
  - The plan touches 5 files (2 production, 3 test) with a combined diff under ~80 LOC; no schema migrations, no infra changes, no breaking API changes.
