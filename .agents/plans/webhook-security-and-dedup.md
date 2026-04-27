# Feature: Webhook Security & Dedup (Gap 07)

The following plan is derived from `feature-developments/scheduling gaps/gap-07-webhook-security-and-dedup.md`. It is complete, but you MUST validate documentation and codebase patterns and task sanity before starting implementation.

Pay special attention to naming of existing utils, types, and models. Import from the right files:
- `get_logger` / `LoggerMixin` live in `grins_platform.log_config`
- `Base` lives in `grins_platform.database`
- `get_database_manager` (session factory for background jobs) lives in `grins_platform.database`
- `AlertType` / `AlertSeverity` live in `grins_platform.models.enums`
- `AlertRepository` lives in `grins_platform.repositories.alert_repository`
- `limiter`, `setup_rate_limiting`, rate-limit constants live in `grins_platform.middleware.rate_limit`
- `CallRailProvider` lives in `grins_platform.services.sms.callrail_provider`
- `SMSService` lives in `grins_platform.services.sms_service`
- `SMSRateLimitTracker` (outbound quota tracking — DO NOT confuse with the inbound slowapi limiter) lives in `grins_platform.services.sms.rate_limit_tracker`
- `get_sms_provider` lives in `grins_platform.services.sms.factory` — it reads `SMS_PROVIDER` and all `CALLRAIL_*` env vars **live on every call** (no memoization of the instance), so integration tests monkeypatch env vars and call it.

### VERIFIED FACTS (locked against the codebase on 2026-04-21 — do not re-derive)

- **Current Alembic head**: `20260422_100000` (from `uv run alembic heads`). The new migration in Task 3 uses `down_revision = "20260422_100000"`.
- **Table name convention**: plural. 48 existing tables all use plural (`alerts`, `customers`, `campaigns`, `sms_consent_records`, etc.). **The new table is `webhook_processed_logs`** (NOT `webhook_processed_log`).
- **Test DB backend**: real PostgreSQL (`postgresql://grins_user:grins_password@localhost:5432/grins_platform` via `database.py:30`). `on_conflict_do_nothing` (PG-specific) is safe. Same `pg_insert(...).on_conflict_do_nothing()` idiom is already used at `services/sms/consent.py:269`.
- **Integration test client fixture**: `async_client: AsyncClient` (httpx.AsyncClient), pytest-asyncio `asyncio_mode = "auto"`. Use `@pytest.mark.integration` marker. **Do NOT use `TestClient`**.
- **Unit test client fixture**: `client` / `authenticated_client` also exist in root conftest — integration tests should prefer `async_client`.
- **Autouse auth override**: root `conftest.py:92-118` (`_patch_create_app_auth`) monkeypatches `create_app` — DO NOT fight it; webhook route is public anyway.
- **Python version**: `requires-python = ">=3.10"`. `datetime.fromisoformat("...Z")` parses the `Z` suffix **only on Python 3.11+**. Because the project still supports 3.10, `check_freshness` must manually strip a trailing `Z` and replace with `+00:00` (shim below).
- **Ruff target**: `target-version = "py39"` (pyproject.toml:124) — do not use `X | Y` union syntax in new files unless `from __future__ import annotations` is present. Every new file in this plan MUST start with `from __future__ import annotations`.
- **Alert.entity_id**: `nullable=False` (confirmed). Webhook-level alerts with no natural entity MUST synthesize `uuid4()` and encode context in `message`.
- **SMS factory default in tests**: `SMS_PROVIDER=null` is set by root conftest.py:25 via `setdefault`. Integration tests must override to `"callrail"` via `monkeypatch.setenv("SMS_PROVIDER", "callrail")` and set the five `CALLRAIL_*` env vars BEFORE the app is imported/created.
- **Scheduler**: APScheduler 3.10.x. `register_scheduled_jobs(scheduler)` at `services/background_jobs.py:973`; `scheduler.add_job(fn, "cron", hour=X, minute=Y, id=..., replace_existing=True)`. Async jobs acquire a session via `async for session in get_database_manager().get_session(): ...`.
- **Deployment topology** (important for Redis):
  - **Backend (FastAPI/Python)** → **Railway** (`zealous-heart` project, service `Grins-dev`). Redis belongs here.
  - **Frontend (React)** → **Vercel** (`frontend/vercel.json`). Vercel does **not** host the backend and does **not** host a Redis used by the backend.
  - **Current Redis state on Railway dev**: NOT PROVISIONED. `REDIS_URL` is absent from `railway variables` (verified 2026-04-21). Provisioning is Task 0 below.

---

## Feature Description

Harden the inbound CallRail SMS webhook endpoint (`POST /webhooks/callrail/inbound`) against three concrete attack and failure modes called out in Gap 07:

- **7.A — Replay protection.** Add a body-`created_at` timestamp window check (default 5 minutes, configurable) so captured webhook payloads cannot be replayed indefinitely; extend the Redis dedup TTL from 24 hours to 7 days to survive legitimate multi-day provider retries; and add a second independent dedup key on `resource_id` (the CallRail message id) with a 30-day TTL so a replay with tampered `created_at` still hits the dedup wall.

- **7.B — Redis dedup silent-pass fix.** Today a Redis outage makes every retried webhook look like a brand-new event. Add a durable **fallback dedup** backed by a lightweight `webhook_processed_log` DB table: whenever Redis is unavailable (or the dedup key is missing), a DB lookup on `(provider, provider_message_id)` authoritatively answers "seen before". Rows older than 30 days are pruned by a rolling background job. This is the Gap 07 Option B approach — fail-open on Redis but correct via DB — which keeps the endpoint available during Redis outages without duplicate processing.

- **7.C — Inbound rate limiting, flood control, and SMS circuit breaker.** Apply a per-IP `slowapi` route-level limit to the webhook endpoint (generous — `60/minute` — so CallRail's legitimate retry cadence is not hurt); add a per-`from_phone` auto-reply throttle (one auto-reply per phone per 60 seconds) so a flood of `Y`/`C` replies from one number cannot generate a flood of outbound SMSes; add a global outbound-auto-reply circuit breaker (opens when > 30 auto-replies/10s system-wide) that suppresses further auto-replies, raises an `Alert`, and logs `sms.auto_reply.circuit_open`. Respect `X-Forwarded-For` correctly behind Railway's edge via a trusted-proxy allowlist; return `503` (not `429`) to the provider when the limiter fires so provider retries are preserved.

Cross-gap hook: emits a new `AlertType.WEBHOOK_REDIS_FALLBACK` alert when the DB fallback path is exercised, satisfying the Gap 14 cross-reference ("Redis fallback in use"). Also emits `AlertType.WEBHOOK_SIGNATURE_FLOOD` when signature-invalid responses exceed threshold in an hour, satisfying the "webhook signature failures in last hour" cross-reference.

## User Story

As the Grins platform operator
I want the inbound CallRail webhook endpoint to resist replay attacks, survive a Redis outage without double-processing, and refuse floods without affecting legitimate provider retries
So that a leaked HMAC secret, a Redis incident, or a hostile actor cannot produce duplicate customer-facing SMS, duplicate `JobConfirmationResponse` rows, or a surprise outbound-SMS bill.

## Problem Statement

Three concrete, independently exploitable weaknesses live in the same file today (`src/grins_platform/api/v1/callrail_webhooks.py`) and compound:

1. **No replay protection.** The HMAC-SHA1 signature check does not bind the signed body to a timestamp. A captured-and-replayed payload passes the signature check forever. The only safety net is a 24-hour Redis dedup key; replays outside that window, or during a Redis outage, process as new events.
2. **Redis dedup is fail-open.** `_is_duplicate` and `_mark_processed` catch every Redis exception and silently return `False`/`None`. During a Redis outage, every legitimate provider retry is treated as a new event, multiplying customer-facing auto-replies, admin `Alert` rows, and `JobConfirmationResponse` rows.
3. **No inbound rate limiter and no per-phone auto-reply throttle.** The project has `slowapi` globally configured but applies no per-route limit to the webhook, and per-phone auto-reply deduping does not exist. An attacker with (or guessing) the URL can drive arbitrary load: HMAC verify CPU, DB inserts, and — if they can also forge signatures — outbound SMS cost.

These are rated as individually medium-severity but compound in attack chains (replay + Redis outage → duplicates; flood → exhaust DB pool → cascade to admin UI) to high severity.

## Solution Statement

Layered defense in three coordinated tiers, all additive to the existing signature check and Redis dedup path:

1. **Replay defense (7.A).**
   - Add `_check_freshness(payload)` helper: parses body `created_at`, rejects with `HTTP 400` if `|now - created_at|` exceeds a configurable `WEBHOOK_CLOCK_SKEW_SECONDS` (default 300s / 5min). Missing or unparseable `created_at` → rejected.
   - Extend Redis dedup TTL constant from 24h → 7 days (`_REDIS_TTL_SECONDS = 7 * 86400`).
   - Add a *second* dedup key pattern, keyed on `(provider, resource_id)`, TTL 30 days. Both keys are checked; seeing either marks as duplicate. Both keys are set on successful processing.

2. **Fail-open-to-DB (7.B).**
   - New model `WebhookProcessedLog(provider, provider_message_id, created_at)` with unique constraint on `(provider, provider_message_id)` and index on `created_at` for pruning.
   - Alembic migration `20260421_100200_create_webhook_processed_log_table.py`.
   - New repository `WebhookProcessedLogRepository` with `exists(provider, provider_message_id)`, `mark_processed(...)`, `prune_older_than(days)` methods.
   - `_is_duplicate` and `_mark_processed` updated: Redis is the primary path; on exception *or* `None` client, they delegate to the repository. An `AlertType.WEBHOOK_REDIS_FALLBACK` alert is raised once per 5-minute window when fallback fires.
   - A lightweight background task prunes rows older than 30 days on a daily cadence (reuses the existing background-jobs APScheduler registration pattern).

3. **Throttling & circuit breaker (7.C).**
   - **Per-IP** — `slowapi` decorator `@limiter.limit("60/minute")` on the inbound endpoint. Use a custom `key_func` (`_webhook_client_key`) that reads `X-Forwarded-For` when a request arrives from an entry in `TRUSTED_PROXY_CIDRS` (Railway edge) and falls back to direct remote address otherwise. The handler returns `HTTP 503` with `Retry-After: 60` when the limit fires — this encourages CallRail retries and discourages hostile clients.
   - **Per-phone auto-reply throttle** — Redis key `sms:autoreply:throttle:{e164_phone}` with 60s TTL; `SMSService` consults this in the auto-reply path and skips (logging `sms.auto_reply.phone_throttled`) when a recent auto-reply is recorded.
   - **Global circuit breaker** — Redis counter `sms:autoreply:global:window` using a sliding 10s window with `INCR/EXPIRE`. Threshold 30 auto-replies / 10s system-wide → circuit opens: suppress further auto-replies for 5 minutes, raise `AlertType.WEBHOOK_AUTOREPLY_CIRCUIT_OPEN`, log `sms.auto_reply.circuit_open`. Falls open-fail (skip circuit check) if Redis unavailable — the DB fallback in 7.B already protects against dup processing, so the cost floor is protected elsewhere.

Signature verification, JSON parsing, and payload structure handling are unchanged — the existing `CallRailProvider.verify_webhook_signature` remains authoritative for HMAC and the existing `parse_inbound_webhook` remains authoritative for payload → `InboundSMS`.

## Feature Metadata

**Feature Type**: Enhancement (security hardening) + Bug Fix (Redis silent-pass)

**Estimated Complexity**: Medium-High
- One new DB table + migration
- One new repository
- One new endpoint-level helper module (`webhook_security.py`) encapsulating freshness check + rate-limit key func + circuit breaker
- Changes inside `callrail_webhooks.py`, `sms_service.py`
- Two new `AlertType` enum values + one new migration to extend the model's allowed values (enum is a string column — no DB change needed)
- Thorough testing (unit + integration + property-based)

**Primary Systems Affected**:
- Backend API: `src/grins_platform/api/v1/callrail_webhooks.py`
- Backend services: `src/grins_platform/services/sms_service.py` (auto-reply throttle + circuit breaker), `src/grins_platform/services/sms/callrail_provider.py` (no change expected — pure HMAC provider)
- New helper module: `src/grins_platform/services/sms/webhook_security.py`
- New model: `src/grins_platform/models/webhook_processed_log.py`
- New repository: `src/grins_platform/repositories/webhook_processed_log_repository.py`
- Rate-limit middleware: `src/grins_platform/middleware/rate_limit.py` (exports + trusted-proxy helper)
- Enums: `src/grins_platform/models/enums.py` (new `AlertType` members)
- Migrations: `src/grins_platform/migrations/versions/20260421_100200_create_webhook_processed_log_table.py`
- Background jobs: `src/grins_platform/services/background_jobs.py` (prune job registration)
- Tests: `src/grins_platform/tests/unit/test_webhook_security.py` (new), `src/grins_platform/tests/integration/test_callrail_webhook_endpoint.py` (new), extensions to `test_pbt_callrail_sms.py`

**Dependencies**: No new external libraries. Uses existing `slowapi>=0.1.9`, `redis>=5.0.0`, `alembic>=1.13.0`, SQLAlchemy 2.x async, pytest, pytest-asyncio, hypothesis.

---

## CONTEXT REFERENCES

### Relevant Codebase Files — IMPORTANT: READ THESE BEFORE IMPLEMENTING

**Inbound webhook path (primary edit target):**
- `src/grins_platform/api/v1/callrail_webhooks.py` (1–198, entire file) — Current endpoint, `_get_redis`, `_is_duplicate`, `_mark_processed`. This is the main file being edited. Redis-helper functions at 35–79 will be extended for DB fallback. Endpoint at 82–197 will grow a freshness check and rate-limit decorator.
- `src/grins_platform/services/sms/callrail_provider.py` (210–242) — `verify_webhook_signature`. **No change** — this stays the HMAC authority. Reference only so the engineer does not touch it.
- `src/grins_platform/services/sms/callrail_provider.py` (244–274) — `parse_inbound_webhook`. **No change** — but note it returns `InboundSMS.provider_sid = resource_id` which is the stable id to dedup on.

**Rate-limit plumbing:**
- `src/grins_platform/middleware/rate_limit.py` (1–83, entire file) — existing `Limiter`, `setup_rate_limiting`, constants. You will **add** a `WEBHOOK_LIMIT = "60/minute"` constant, a `TRUSTED_PROXY_CIDRS` list, and a `webhook_client_key(request)` key func that honors `X-Forwarded-For` behind trusted proxies.
- `src/grins_platform/app.py` (217–229) — where `setup_rate_limiting(app)` is wired. No change needed unless we move the rate-limit module further.
- `src/grins_platform/api/v1/router.py` (223–227) — where `callrail_webhooks_router` is included. No change needed.

**Alert plumbing (mirror this pattern for new alert types):**
- `src/grins_platform/models/alert.py` (entire file) — the model to instantiate.
- `src/grins_platform/models/enums.py` (579–600) — `AlertSeverity` / `AlertType`. Extend with `WEBHOOK_REDIS_FALLBACK`, `WEBHOOK_SIGNATURE_FLOOD`, `WEBHOOK_AUTOREPLY_CIRCUIT_OPEN`.
- `src/grins_platform/repositories/alert_repository.py` (25–70) — pattern: `AlertRepository(session).create(Alert(...))`.
- `src/grins_platform/migrations/versions/20260416_100100_create_alerts_table.py` — migration style; note `AlertType` is stored as `sa.String(100)` so new enum members do **not** need a DB migration.

**Migration style (mirror exactly):**
- `src/grins_platform/migrations/versions/20260416_100100_create_alerts_table.py` (1–73, entire file) — revision header, `upgrade`/`downgrade`, `op.create_table(...)`, `op.create_index(...)`, `sa.UUID()` / `server_default=sa.text("gen_random_uuid()")`, tz-aware timestamps, drop order mirrors creation in reverse. Use this as the exact template.
- Recent migrations for cadence of filenames:
  - `20260422_100000_add_admin_confirmed_informal_opt_out_method.py`
  - `20260421_100100_add_sent_messages_superseded_at.py` — pick the next slot: `20260421_100200_create_webhook_processed_log_table.py`, with `down_revision = "20260422_100000"` (latest head — verify with `uv run alembic heads` before writing).

**SQLAlchemy model pattern (mirror the Alert model exactly):**
- `src/grins_platform/models/alert.py` (28–87) — PK UUID, `created_at` tz-aware, indexes via `__table_args__`, enum re-validation via `*_enum` property. Mirror for `WebhookProcessedLog`.
- `src/grins_platform/database.py` (26–56) — `Base = DeclarativeBase`, `DatabaseSettings` pattern. `Base` is the sole import.

**Repository pattern (mirror `AlertRepository`):**
- `src/grins_platform/repositories/alert_repository.py` (25–80) — `LoggerMixin` subclass, `__init__(session)`, `log_started` / `log_completed`, `await session.flush()` + `await session.refresh(...)`.

**Auto-reply / outbound path (for 7.C throttles):**
- `src/grins_platform/services/sms_service.py` (900–940) — auto-reply send path for confirmation replies; will wrap in per-phone throttle + global circuit-breaker check.
- `src/grins_platform/services/sms_service.py` (800–825) — auto-reply send path for poll replies; same wrapping applies.
- `src/grins_platform/services/sms/rate_limit_tracker.py` (entire file) — outbound provider-quota tracker (Redis with 120s TTL). **Do not confuse** with inbound slowapi. Useful only as a reference for the Redis-with-in-memory-fallback pattern.

**Logging conventions:**
- `src/grins_platform/log_config.py` (154–166 for `get_logger`, 214–238 for `LoggerMixin`, `DOMAIN` attribute). Log-event naming pattern: `{domain}.{component}.{action}_{state}`.
- Examples already in `callrail_webhooks.py`: `sms.webhook.signature_invalid`, `sms.webhook.duplicate_skipped`, `sms.webhook.redis_unavailable`. Mirror: `sms.webhook.replay_rejected`, `sms.webhook.db_fallback_hit`, `sms.webhook.rate_limited`, `sms.auto_reply.phone_throttled`, `sms.auto_reply.circuit_open`.

**Testing conventions:**
- `src/grins_platform/tests/unit/test_pbt_callrail_sms.py` (1–150) — PBT style; already imports `_REDIS_KEY_PREFIX`, `_is_duplicate`. Extend here for the new dedup-semantics property tests.
- `src/grins_platform/tests/unit/test_rate_limit_tracker.py` (1–41) — shows Redis-mock style for the existing rate-limit tracker; mirror for the new per-phone/circuit tests.
- `src/grins_platform/tests/conftest.py` (347, 355) — `pytest_asyncio.fixture` for `client` / `authenticated_client`. Use `client` for unauthenticated webhook integration tests.
- **No existing test posts to `/webhooks/callrail/inbound`.** This plan adds `src/grins_platform/tests/integration/test_callrail_webhook_endpoint.py` as the first integration coverage.

**Background jobs (for the prune task):**
- `src/grins_platform/services/background_jobs.py` (search for `APScheduler`, `AsyncIOScheduler`, or similar registration code). Follow the existing pattern for daily cadence jobs.

**Settings / env vars:**
- `src/grins_platform/database.py` (26–43) — `DatabaseSettings` using pydantic-settings is one pattern.
- `src/grins_platform/api/v1/callrail_webhooks.py` (37) — direct `os.environ.get("REDIS_URL")` is the current idiom for `REDIS_URL`. Stay consistent.

### New Files to Create

- `src/grins_platform/models/webhook_processed_log.py` — SQLAlchemy model for the fallback dedup table.
- `src/grins_platform/repositories/webhook_processed_log_repository.py` — repository with `exists`, `mark_processed`, `prune_older_than`.
- `src/grins_platform/services/sms/webhook_security.py` — freshness check, trusted-proxy IP extraction, per-phone throttle, global circuit-breaker helpers.
- `src/grins_platform/migrations/versions/20260421_100200_create_webhook_processed_log_table.py` — Alembic migration.
- `src/grins_platform/tests/unit/test_webhook_security.py` — unit tests for helpers in `webhook_security.py`.
- `src/grins_platform/tests/integration/test_callrail_webhook_endpoint.py` — TestClient-backed integration tests POSTing to `/api/v1/webhooks/callrail/inbound` (valid signature + replay + rate limit + DB fallback paths).
- `src/grins_platform/tests/unit/test_webhook_processed_log_repository.py` — repository unit tests.

### Relevant Documentation — READ BEFORE IMPLEMENTING

- [slowapi — route-level rate limits (official README)](https://github.com/laurentS/slowapi#fastapi) — `limiter.limit("60/minute")` decorator usage; `key_func` customization; interaction with `app.state.limiter`.
  - **Why**: The existing middleware only wires the exception handler and global default. We need to add a *route-level* decorator, which slowapi supports only when the route's first arg is typed `request: Request`. The current endpoint already has that — good.
- [slowapi — custom key functions and X-Forwarded-For](https://slowapi.readthedocs.io/en/latest/#customization) — why you must NOT blindly trust `X-Forwarded-For` and how to build a trusted-proxy allowlist.
  - **Why**: Railway (and CDN front-ends) set `X-Forwarded-For`; the default `get_remote_address` only reads the direct TCP peer, which is the proxy's IP. Without a trusted-proxy check we either (a) rate-limit everyone under the proxy's single IP (false positives) or (b) accept spoofed XFF headers (bypass).
- [Redis `SET NX EX` semantics](https://redis.io/commands/set/) — the existing code uses `SET NX EX` to atomically mark-processed. Keep this — it is idempotent and race-safe.
- [SQLAlchemy 2.x async `on_conflict_do_nothing` (PG-specific upsert)](https://docs.sqlalchemy.org/en/20/dialects/postgresql.html#sqlalchemy.dialects.postgresql.Insert.on_conflict_do_nothing) — use for the DB fallback `mark_processed` to tolerate races between concurrent webhook deliveries.
- [PostgreSQL partial index](https://www.postgresql.org/docs/current/indexes-partial.html) — if you prefer `prune_older_than` to use `created_at < now() - interval '30 days'`, a plain B-tree index on `created_at` is sufficient (no partial index required at this scale).
- CallRail webhook docs are already reverse-engineered in `callrail_provider.py:217–266` — no need to re-visit; the verified contract is already in-tree.

### Project Steering Rules — `.kiro/steering/` (MANDATORY)

The files under `/Users/kirillrakitin/Grins_irrigation_platform/.kiro/steering/` are the project's standing orders. The implementing agent MUST comply with every rule below. These supersede default Claude/agent habits. (Frontend, agent-browser, e2e, and devlog rules are omitted as they don't apply to this backend feature.)

**From `code-standards.md`:**
- Every change MUST include logging, tests, pass quality checks, AND be validated end-to-end.
- Logging framework: `structlog`. Pattern: `{domain}.{component}.{action}_{state}`. Import from `grins_platform.log_config` (`LoggerMixin`, `get_logger`, `DomainLogger` all live there).
- Service classes MUST inherit from `LoggerMixin` with a `DOMAIN` class attribute, and use `self.log_started(...)`, `self.log_completed(...)`, `self.log_rejected(...)`, `self.log_failed(...)`.
- Function/utility logging uses `logger = get_logger(__name__)` + plain structured calls OR `DomainLogger.api_event(logger, "operation", "started", ...)` for event-like semantics.
- Log levels: DEBUG = internals; INFO = business ops; WARNING = recoverable; ERROR = failures; CRITICAL = system.
- MUST log: service entry/exit, external API calls, validation, errors (with context), security events.
- MUST NOT log: passwords, tokens, PII, every internal call. Mask phone numbers via `_mask_phone(...)` (reused from `callrail_provider.py:59-63`).
- **Three-tier testing is mandatory** for every backend change:
  - `tests/unit/` with `@pytest.mark.unit` — all deps mocked.
  - `tests/functional/` with `@pytest.mark.functional` — real DB, user workflow.
  - `tests/integration/` with `@pytest.mark.integration` — full system, cross-component.
  - Property-based tests (Hypothesis) are REQUIRED for business logic with invariants (dedup, circuit-breaker counters qualify).
- Test naming conventions (enforce exactly):
  - Unit: `test_{method}_with_{condition}_returns_{expected}`
  - Functional: `test_{workflow}_as_user_would_experience`
  - Integration: `test_{feature}_works_with_existing_{component}`
- Type safety: every function MUST have argument and return type hints; no implicit `Any`; MUST pass both MyPy AND Pyright with zero errors.
- Error-handling pattern (mirror verbatim):
  ```python
  try:
      result = self._process(data)
  except ValidationError:
      raise  # already logged
  except ExternalServiceError as e:
      self.log_failed("op", error=e)
      raise ServiceError(f"External failed: {e}") from e
  ```
- Quality commands that must pass with zero errors before task completion:
  ```bash
  uv run ruff check --fix src/
  uv run ruff format src/
  uv run mypy src/
  uv run pyright src/
  uv run pytest -v
  ```

**From `api-patterns.md`:**
- API endpoints use `APIRouter(prefix=..., tags=[...])` (already followed in `callrail_webhooks.py:28`).
- Endpoints MUST call `set_request_id()` at the start and `clear_request_id()` in a `finally` block. The new/modified webhook route MUST add this wrapping — the current implementation does not yet.
- Structured entry/exit logging in endpoints uses `DomainLogger.api_event(logger, "operation", "started"|"completed"|"failed", request_id=request_id, status_code=..., ...)`. The current webhook file uses plain `logger.info("sms.webhook.inbound", ...)` — **keep the existing event names for backwards compatibility with any log consumers, and ALSO add `DomainLogger.api_event` calls for the new branches** (`replay_rejected`, `db_fallback_hit`, `rate_limited`, `autoreply_phone_throttled`, `autoreply_circuit_open`, `signature_flood_alert`).
- Use `DomainLogger.validation_event(logger, "webhook_payload", "started"|"validated"|"rejected", request_id=...)` around the JSON parse + freshness check.
- HTTP status mapping: `ValidationError → 400`, `NotFoundError → 404`, generic `Exception → 500`. For webhook-specific overrides, the plan's `503` response on rate-limit and `400` on stale timestamp are both compatible with this mapping.
- Dependency injection: new services use `def get_webhook_security_service() -> ...: ...` + `Depends(get_...)`. For the pure-function helpers in `services/sms/webhook_security.py` no DI wrapper is needed — module-level import is acceptable because they're stateless.
- Tests must cover: success (200/201/204) + 400 validation + 404 not found (if applicable) + 500 server error paths.

**From `spec-testing-standards.md`:**
- Backend changes require unit + functional + integration + property-based tests.
- Ruff, MyPy, Pyright all must pass with zero errors.
- Backend coverage target: 90%+ on new services / repositories / utilities.

**From `structure.md`:**
- Backend layout is fixed:
  - Models → `src/grins_platform/models/{domain}.py`
  - Schemas → `src/grins_platform/schemas/{domain}.py` (Pydantic)
  - Repositories → `src/grins_platform/repositories/{domain}_repository.py`
  - Services → `src/grins_platform/services/{domain}_service.py` (or nested like `services/sms/{name}.py`)
  - API routes → `src/grins_platform/api/v1/{domain}.py` + `router.py`
  - Migrations → `src/grins_platform/migrations/versions/{timestamp}_{slug}.py`
- Python filenames: `snake_case.py`; test files: `test_{module}.py`.
- Imports use the `grins_platform.{package}.{module}` fully-qualified form.

**From `tech.md`:**
- Backend stack: Python **3.11+** per tech.md (BUT `pyproject.toml requires-python = ">=3.10"` — the `Z` shim in `check_freshness` is mandatory because one of the two is more lenient and we support the minimum).
- Stack constants: FastAPI + SQLAlchemy 2.0 async + PostgreSQL 15+ + Redis 7+.
- Env-var inputs for this feature all use the existing `os.environ.get(...)` idiom at helper-module load time (consistent with the rest of the codebase); a dedicated pydantic `Settings` subclass is NOT required but is acceptable if the executor prefers one.
- Required env vars already in convention: `DATABASE_URL`, `REDIS_URL`, `LOG_LEVEL`, `ENVIRONMENT`. The new `WEBHOOK_*` vars extend this list.
- Performance target: API p95 < 200ms. The webhook route's new work (freshness check + optional DB-fallback query) should add < 5ms in the hot path and < 30ms on the Redis-down fallback path. Validate with a light local benchmark during Task 17.
- Security: never log secrets/tokens; PII masked in logs. Phone masking already enforced by `_mask_phone`.

**From `spec-quality-gates.md` (requirements-checklist hygiene, relevant items only):**
- Security: no logging of secrets; admin auth on protected endpoints where applicable; input sanitization. The webhook endpoint is public by design (signature-verified), so admin-auth doesn't apply; input sanitization is handled by HMAC + `parse_inbound_webhook` + the new freshness check.
- Cross-feature integration: new Alert types must work with the existing `GET /api/v1/alerts` endpoint and dashboard filters (Gap 14 hook). Add an integration test that verifies `GET /api/v1/alerts?type=webhook_redis_fallback` returns the row after the fallback fires.

**Steering compliance mapped to specific tasks:**
- Task 4 (repository): MUST inherit `LoggerMixin` with `DOMAIN = "database"` (mirrors `AlertRepository` at line 36). MUST use `log_started` / `log_completed` / `log_failed`.
- Task 5 (webhook_security.py): functional-style; `get_logger(__name__)` at module top; `DomainLogger.api_event` / `validation_event` is acceptable for semantic events but plain structured `logger.warning("sms.webhook.replay_rejected", ...)` matches the existing webhook file's pattern.
- Task 7 (route edits): ADD `set_request_id()` / `clear_request_id()` wrapping around the route body; thread `request_id` through log calls; use `DomainLogger.api_event(logger, "webhook_inbound", "started"|"completed"|"failed", request_id=request_id, status_code=..., provider="callrail", ...)` at entry/exit in addition to preserving existing event names.
- Task 9 (SMSService auto-reply throttle): changes inside an existing `LoggerMixin` subclass — use `self._logger.warning(...)` / `self._logger.info(...)` (already the convention in the file).
- Task 13–16 (tests): unit tests go in `tests/unit/` with `@pytest.mark.unit`; integration tests in `tests/integration/` with `@pytest.mark.integration`; PBT extensions remain alongside existing PBT file. A new `tests/functional/` file is **not required** for this feature because every new workflow is adequately covered by the integration tests (the fallback dedup goes DB-round-trip, the replay path goes through the full route, the rate-limit path uses the real slowapi storage). If the executor finds a DB-workflow gap during implementation that is NOT suited to integration-level testing, add a `tests/functional/test_webhook_processed_log_flow.py` with `@pytest.mark.functional`.

### Patterns to Follow

**Naming conventions:**
- Modules and functions: `snake_case`.
- Classes and types: `PascalCase`.
- Alembic revision IDs: `YYYYMMDD_HHMMSS` (zero-padded) e.g. `20260421_100200`.
- Log events: dotted `{domain}.{component}.{action}_{state}` (`sms.webhook.replay_rejected`).
- Alert types: SCREAMING_SNAKE in the enum (`WEBHOOK_REDIS_FALLBACK`), lowercase-snake as the stored `.value` (`"webhook_redis_fallback"`).

**Error handling:**
- Webhook route returns small JSON bodies, never raw exceptions; e.g. `Response(content='{"error": "Invalid webhook signature"}', status_code=403, media_type="application/json")` — match the existing shape exactly.
- Redis exceptions are caught at helper boundaries and logged, never bubbled (see `callrail_webhooks.py:62–64, 78–79`).
- Repository methods log `log_started` / `log_completed` / `log_failed` (via `LoggerMixin`) and let transaction errors bubble to the route for rollback.

**Logging (structured kwargs):**
```python
# Good — dotted namespace + structured kwargs
logger.warning(
    "sms.webhook.replay_rejected",
    provider="callrail",
    created_at=created_at,
    skew_seconds=skew,
)
```

**Migration header (copy verbatim, just change the revision/down_revision/title):**
```python
"""Create ``webhook_processed_log`` table for fallback dedup.

Revision ID: 20260421_100200
Revises: <current head; verify with `uv run alembic heads`>
Requirements: Gap 07 — Webhook Security & Dedup (7.B)
"""

from __future__ import annotations
from collections.abc import Sequence
import sqlalchemy as sa
from alembic import op

revision: str = "20260421_100200"
down_revision: str | None = "<verified head>"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None
```

**Model pattern (mirror `Alert`):**
```python
class WebhookProcessedLog(Base):
    __tablename__ = "webhook_processed_log"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    provider_message_id: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )

    __table_args__ = (
        UniqueConstraint(
            "provider",
            "provider_message_id",
            name="uq_webhook_processed_log_provider_msgid",
        ),
    )
```

**Route decorator pattern (slowapi):**
```python
from grins_platform.middleware.rate_limit import limiter, WEBHOOK_LIMIT, webhook_client_key

@router.post("/inbound", ...)
@limiter.limit(WEBHOOK_LIMIT, key_func=webhook_client_key)
async def callrail_inbound(request: Request, db: AsyncSession = Depends(get_db)) -> Response:
    ...
```

---

## IMPLEMENTATION PLAN

### Phase 1: Foundation

Lay the DB/model/repository scaffolding for fallback dedup, add enum values, and introduce the helper module.

**Tasks:**
- Extend `AlertType` with three new members (`WEBHOOK_REDIS_FALLBACK`, `WEBHOOK_SIGNATURE_FLOOD`, `WEBHOOK_AUTOREPLY_CIRCUIT_OPEN`).
- Create `WebhookProcessedLog` model + Alembic migration.
- Create `WebhookProcessedLogRepository`.
- Create `services/sms/webhook_security.py` skeleton (freshness, trusted-proxy key func, per-phone throttle, circuit breaker).
- Add `WEBHOOK_LIMIT = "60/minute"`, `TRUSTED_PROXY_CIDRS`, and re-export `webhook_client_key` from `middleware/rate_limit.py`.

### Phase 2: Core Implementation

Wire the new primitives into the webhook route and auto-reply path.

**Tasks:**
- Modify `_is_duplicate` and `_mark_processed` to check DB when Redis fails or returns missing.
- Add `_REDIS_MSGID_KEY_PREFIX` and a `_is_duplicate_by_message_id` secondary dedup lookup.
- Extend Redis TTL constant to `7 * 86400`; add 30-day TTL for the message-id key.
- Apply `@limiter.limit(WEBHOOK_LIMIT, key_func=webhook_client_key)` to `callrail_inbound`; return `503` on limit-exceeded for this route.
- Add `_check_freshness(payload)` helper in `webhook_security.py`; call before duplicate check.
- Extend `SMSService` auto-reply branches (confirmation and poll) with a per-phone Redis throttle and a global circuit-breaker check.
- Emit `Alert` rows for: DB fallback firing, hourly signature-failure breach, circuit-breaker opening.

### Phase 3: Integration

Background prune job, configuration surface, and logging polish.

**Tasks:**
- Register `prune_webhook_processed_log` daily background job (removes rows older than 30 days).
- Add env vars (`WEBHOOK_CLOCK_SKEW_SECONDS`, `WEBHOOK_TRUSTED_PROXY_CIDRS`, `WEBHOOK_AUTOREPLY_CIRCUIT_THRESHOLD`, `WEBHOOK_AUTOREPLY_PHONE_TTL_S`, `WEBHOOK_AUTOREPLY_GLOBAL_WINDOW_S`) with safe defaults — read via `os.environ.get(...)` at helper boundaries (consistent with existing `REDIS_URL` idiom in the same file).
- Verify that rate-limit 429/503 path is exempt from CSRF and any authenticated-request assumptions (webhooks are public by design — confirmed in router comment `"Include CallRail Webhook endpoints (excluded from CSRF)"`).

### Phase 4: Testing & Validation

Full coverage across unit, integration, and property-based tests.

**Tasks:**
- Unit tests for `webhook_security.py` — freshness window, XFF parsing with/without trusted proxy, circuit-breaker math, per-phone TTL.
- Unit tests for `WebhookProcessedLogRepository` — exists/mark_processed/prune_older_than, race safety via concurrent `mark_processed` calls.
- Integration tests for the full endpoint — valid signature + fresh timestamp → processed; stale timestamp → 400; replay same body → 200 already_processed; Redis-down + DB-has-record → 200 already_processed; 61st call in a minute → 503.
- Extend PBT file with a property: "any (conversation_id, created_at, resource_id) tuple seen before is never processed twice", varying which dedup path answers.

---

## STEP-BY-STEP TASKS

IMPORTANT: Execute every task in order, top to bottom. Each task is atomic and independently testable.

### Task Format Keywords
- **CREATE** — new file/component; **UPDATE** — modify existing; **ADD** — insert into existing; **REMOVE** — delete; **MIRROR** — copy pattern from elsewhere.

---

### 0. INFRASTRUCTURE — Provision Redis on Railway dev (and document prod)

This feature hard-depends on Redis for the primary paths (rate-limit storage for `slowapi`, per-phone throttle, global circuit breaker, primary-dedup keys, alert-emission dedupe). The code must still function without Redis (via the DB-fallback path from 7.B), but the THROTTLE and CIRCUIT-BREAKER layers degrade to fail-open if Redis is absent. So in dev we provision Redis *before* merging this feature so tests actually exercise Redis paths.

**Current state (verified 2026-04-21)**: Railway project `zealous-heart` → environment `dev` → services `Grins-dev`, `Postgres-PH_d`, `Postgres`, `Grins_irrigation_platform`. **No Redis service.** `railway variables` does not contain `REDIS_URL`.

**Clarification on deployment target**: Redis goes on **Railway** (alongside the backend), NOT on Vercel. Vercel hosts the frontend only (`frontend/vercel.json`). The user's "Vercel Dev Environment" reference was a misidentification — Vercel KV is available if external Redis is preferred, but the simpler choice for this stack is the Railway Redis plugin which auto-injects `REDIS_URL` into the backend service.

- **ACTIONS (Railway dev — do this FIRST before any code change is merged)**:
  1. Provision Redis via the Railway dashboard: *zealous-heart → dev environment → + New → Database → Add Redis*. Railway auto-creates a `Redis` service and auto-injects a private `REDIS_URL` reference variable into sibling services (including `Grins-dev`).
  2. If the auto-reference does not attach, manually copy the Redis service's `REDIS_URL` (private network form, `redis.railway.internal`) and set it on `Grins-dev`:
     ```bash
     railway link --project zealous-heart --environment dev --service Grins-dev
     railway variables --set REDIS_URL=<copied-private-url>
     ```
  3. Redeploy `Grins-dev` (auto-triggered by variable change).
  4. Verify: `railway logs --service Grins-dev` should show `security.rate_limit.configured storage=redis` instead of `storage=memory` on startup.
  5. Quick smoke: hit any public endpoint that is rate-limited, confirm no regression; confirm `curl <dev-url>/health` still returns 200.
- **ACTIONS (prod — document, do NOT apply in this PR)**:
  - Same provisioning steps for the prod environment (`production`) once this feature is ready to ship. Add a deployment-checklist bullet to `deployment-instructions/2026-04-09-dev-to-main-deployment.md` under the existing "Redis" section so the prod cutover is explicit.
- **VALIDATE**:
  - `railway variables 2>&1 | grep -i REDIS_URL` — must show a non-empty value.
  - After redeploy: `railway logs --service Grins-dev 2>&1 | grep security.rate_limit.configured | tail -1` — must report `storage=redis`.
- **GOTCHA**: `REDIS_URL` must use the Railway private URL (`redis.railway.internal:6379`) so egress stays inside the VPC and doesn't incur external networking costs. Do NOT use the public proxy URL.
- **GOTCHA (local dev)**: Local already has Redis via `docker-compose.dev.yml` → service `redis` (port 6379). The same `REDIS_URL=redis://localhost:6379/0` idiom in `.env.example` remains unchanged. No action needed locally.
- **FALLBACK OPTION (if Railway Redis plugin isn't desired)**: Provision Upstash Redis (free tier sufficient for dev throughput) and set `REDIS_URL=rediss://...` on the Railway backend service. Functionally equivalent.

---

### 1. UPDATE `src/grins_platform/models/enums.py`

- **IMPLEMENT**: Add three new `AlertType` members inside the existing `class AlertType(str, Enum)` (lines 590–600).
- **PATTERN**: Existing members on `enums.py:596-600`.
- **SPECIFIC VALUES**:
  ```python
  WEBHOOK_REDIS_FALLBACK = "webhook_redis_fallback"
  WEBHOOK_SIGNATURE_FLOOD = "webhook_signature_flood"
  WEBHOOK_AUTOREPLY_CIRCUIT_OPEN = "webhook_autoreply_circuit_open"
  ```
- **GOTCHA**: `AlertType.type` is stored as `sa.String(100)` in the `alerts` table (verify against `migrations/versions/20260416_100100_create_alerts_table.py:36`), so adding enum members does NOT require a DB migration.
- **VALIDATE**: `uv run python -c "from grins_platform.models.enums import AlertType; print(AlertType.WEBHOOK_REDIS_FALLBACK.value)"`

---

### 2. CREATE `src/grins_platform/models/webhook_processed_log.py`

- **IMPLEMENT**: `WebhookProcessedLog(Base)` model with fields `id`, `provider`, `provider_message_id`, `created_at`.
- **PATTERN**: Mirror `src/grins_platform/models/alert.py:28-87` exactly for imports, `Mapped[...] = mapped_column(...)`, `server_default=func.gen_random_uuid()`, `server_default=func.now()`, `__table_args__` for composite indexes / unique constraints.
- **IMPORTS**:
  ```python
  from datetime import datetime
  from uuid import UUID
  from sqlalchemy import DateTime, Index, String, UniqueConstraint
  from sqlalchemy.dialects.postgresql import UUID as PGUUID
  from sqlalchemy.orm import Mapped, mapped_column
  from sqlalchemy.sql import func
  from grins_platform.database import Base
  ```
- **FIELDS**:
  - `id`: `PGUUID(as_uuid=True)`, `primary_key=True`, `server_default=func.gen_random_uuid()`
  - `provider`: `String(50)`, `nullable=False`
  - `provider_message_id`: `String(255)`, `nullable=False`
  - `created_at`: `DateTime(timezone=True)`, `nullable=False`, `server_default=func.now()`, `index=True`
- **CONSTRAINTS (`__table_args__`)**:
  - `UniqueConstraint("provider", "provider_message_id", name="uq_webhook_processed_log_provider_msgid")`
- **TABLENAME (locked)**: `__tablename__ = "webhook_processed_logs"` — plural, verified against 48 existing tables all using plural.
- **FILE-LEVEL REQUIREMENT**: first line of module body must be `from __future__ import annotations` (the project targets ruff `py39` which forbids `X | Y` union syntax at runtime; `Mapped[UUID]` style is fine but postponed evaluation avoids surprises).
- **VALIDATE**: `uv run python -c "from grins_platform.models.webhook_processed_log import WebhookProcessedLog; assert WebhookProcessedLog.__tablename__ == 'webhook_processed_logs'"`

---

### 3. CREATE `src/grins_platform/migrations/versions/20260421_100200_create_webhook_processed_log_table.py`

- **IMPLEMENT**: Alembic migration creating the `webhook_processed_log` table and indexes; `downgrade()` drops them in reverse.
- **PATTERN**: Mirror `src/grins_platform/migrations/versions/20260416_100100_create_alerts_table.py:1-73` verbatim for header, `op.create_table`, `op.create_index`, `op.drop_index`, `op.drop_table` order.
- **REVISION (locked)**: `revision: str = "20260421_100200"`, `down_revision: str | None = "20260422_100000"` (verified head on 2026-04-21 via `uv run alembic heads`).
- **TABLE DDL (inside `upgrade()`)**:
  ```python
  op.create_table(
      "webhook_processed_logs",
      sa.Column("id", sa.UUID(), primary_key=True,
                server_default=sa.text("gen_random_uuid()")),
      sa.Column("provider", sa.String(50), nullable=False),
      sa.Column("provider_message_id", sa.String(255), nullable=False),
      sa.Column("created_at", sa.TIMESTAMP(timezone=True),
                nullable=False, server_default=sa.text("NOW()")),
      sa.UniqueConstraint(
          "provider", "provider_message_id",
          name="uq_webhook_processed_logs_provider_msgid",
      ),
  )
  op.create_index(
      "ix_webhook_processed_logs_created_at",
      "webhook_processed_logs",
      ["created_at"],
  )
  ```
- **DOWNGRADE**: Drop index first, then table (`op.drop_index("ix_webhook_processed_logs_created_at", table_name="webhook_processed_logs")`, then `op.drop_table("webhook_processed_logs")`).
- **GOTCHA**: Use `sa.UUID()` (dialect-neutral) in migration, even though the model uses `PGUUID` — this matches the style in `alerts` migration.
- **VALIDATE**:
  - `uv run alembic check` — should show no drift.
  - `uv run alembic upgrade head` — should succeed on local Postgres.
  - `uv run alembic downgrade -1 && uv run alembic upgrade head` — round-trip should succeed.

---

### 4. CREATE `src/grins_platform/repositories/webhook_processed_log_repository.py`

- **IMPLEMENT**: `WebhookProcessedLogRepository(LoggerMixin)` with three methods.
- **PATTERN**: Mirror `src/grins_platform/repositories/alert_repository.py:1-80` for class shape, `LoggerMixin` usage, `log_started`/`log_completed`, session injection.
- **IMPORTS**:
  ```python
  from datetime import datetime, timedelta, timezone
  from sqlalchemy import delete, select
  from sqlalchemy.dialects.postgresql import insert as pg_insert
  from grins_platform.log_config import LoggerMixin
  from grins_platform.models.webhook_processed_log import WebhookProcessedLog
  ```
- **METHODS**:
  - `async def exists(self, provider: str, provider_message_id: str) -> bool` — `SELECT 1 FROM webhook_processed_log WHERE provider=:p AND provider_message_id=:m LIMIT 1`, return `True` if any row.
  - `async def mark_processed(self, provider: str, provider_message_id: str) -> None` — use `pg_insert(WebhookProcessedLog).values(...).on_conflict_do_nothing(index_elements=["provider", "provider_message_id"])`. This is race-safe under concurrent webhook deliveries. `await self.session.flush()` after execution.
  - `async def prune_older_than(self, days: int) -> int` — `DELETE FROM webhook_processed_log WHERE created_at < NOW() - INTERVAL ':days days'`, return rowcount. Use `timezone.utc` cutoff for tz-aware math.
- **LOGGING**: `log_started("exists", provider=..., provider_message_id=...)`, `log_completed(...)` / `log_failed(...)` on each method.
- **GOTCHA**: `on_conflict_do_nothing` is PostgreSQL-specific. This matches the project's `postgresql+asyncpg` backend (see `database.py:38`).
- **VALIDATE**:
  - `uv run python -c "from grins_platform.repositories.webhook_processed_log_repository import WebhookProcessedLogRepository; print(WebhookProcessedLogRepository.__mro__)"`
  - Unit tests in Task 16.

---

### 5. CREATE `src/grins_platform/services/sms/webhook_security.py`

- **IMPLEMENT**: Module exposing four utilities used by the route and by `SMSService`.
- **IMPORTS**:
  ```python
  from __future__ import annotations
  import ipaddress
  import os
  from datetime import datetime, timezone
  from typing import TYPE_CHECKING
  from grins_platform.log_config import get_logger
  if TYPE_CHECKING:
      from fastapi import Request
      from redis.asyncio import Redis
  logger = get_logger(__name__)
  ```
- **CONSTANTS** (read env on module import with safe defaults):
  ```python
  CLOCK_SKEW_SECONDS = int(os.environ.get("WEBHOOK_CLOCK_SKEW_SECONDS", "300"))
  TRUSTED_PROXY_CIDRS = [
      c.strip() for c in os.environ.get("WEBHOOK_TRUSTED_PROXY_CIDRS", "").split(",") if c.strip()
  ]
  AUTOREPLY_PHONE_TTL_S = int(os.environ.get("WEBHOOK_AUTOREPLY_PHONE_TTL_S", "60"))
  AUTOREPLY_GLOBAL_WINDOW_S = int(os.environ.get("WEBHOOK_AUTOREPLY_GLOBAL_WINDOW_S", "10"))
  AUTOREPLY_GLOBAL_THRESHOLD = int(os.environ.get("WEBHOOK_AUTOREPLY_CIRCUIT_THRESHOLD", "30"))
  AUTOREPLY_CIRCUIT_OPEN_S = 300  # 5 minutes
  ```
- **FUNCTION 1 — `def check_freshness(created_at_raw: str, now: datetime | None = None) -> tuple[bool, int]`**: returns `(is_fresh, skew_seconds)`. `is_fresh` is `False` if `created_at_raw` is empty, unparseable, or `abs(skew) > CLOCK_SKEW_SECONDS`. **MANDATORY `Z` shim** (project still supports Python 3.10 — `fromisoformat` only parses `Z` on 3.11+):
  ```python
  def check_freshness(created_at_raw: str, now: datetime | None = None) -> tuple[bool, int]:
      if not created_at_raw:
          return False, 0
      raw = created_at_raw.strip()
      # Python 3.10 compat: normalize trailing Z to +00:00 before parsing.
      if raw.endswith("Z"):
          raw = raw[:-1] + "+00:00"
      try:
          parsed = datetime.fromisoformat(raw)
      except ValueError:
          return False, 0
      if parsed.tzinfo is None:
          parsed = parsed.replace(tzinfo=timezone.utc)
      current = now or datetime.now(timezone.utc)
      skew = int(abs((current - parsed).total_seconds()))
      return (skew <= CLOCK_SKEW_SECONDS), skew
  ```
  Use the injected `now` for testability.
- **FUNCTION 2 — `def webhook_client_key(request: Request) -> str`**: the slowapi `key_func`. Logic:
  1. `peer_ip = request.client.host`
  2. If `peer_ip` is in any of `TRUSTED_PROXY_CIDRS` (use `ipaddress.ip_address` + `ipaddress.ip_network`), and `X-Forwarded-For` is present, return the **leftmost** IP in XFF (first hop = original client).
  3. Otherwise return `peer_ip`.
  - If list is empty (local dev), short-circuit to `peer_ip`.
- **FUNCTION 3 — `async def autoreply_phone_throttled(redis: Redis | None, e164_phone: str) -> bool`**: Redis key `sms:autoreply:throttle:{e164_phone}`; checks `GET`; if present returns `True`; else `SET ... NX EX AUTOREPLY_PHONE_TTL_S "1"` and returns `False`. On `None` redis OR exception, return `False` (fail-open; the DB-fallback dedup from 7.B + signature check will already have protected correctness upstream; this throttle is a cost-control layer, not a correctness layer).
- **FUNCTION 4 — `async def autoreply_circuit_open(redis: Redis | None) -> bool`**: sliding-window counter. Redis key `sms:autoreply:global:window`; on each call, `INCR` then `EXPIRE AUTOREPLY_GLOBAL_WINDOW_S` (only if new key — use `EXPIRE` with `NX` flag if available, else unconditionally `EXPIRE` on every INCR — acceptable granularity). If resulting counter > `AUTOREPLY_GLOBAL_THRESHOLD`, also `SET sms:autoreply:circuit:open "1" EX AUTOREPLY_CIRCUIT_OPEN_S` and return `True`. Also return `True` if `sms:autoreply:circuit:open` already exists. On `None` redis OR exception → `False`.
- **LOGGING**:
  - `logger.warning("sms.webhook.replay_rejected", created_at=..., skew_seconds=...)`
  - `logger.info("sms.auto_reply.phone_throttled", phone=masked)`
  - `logger.warning("sms.auto_reply.circuit_open", counter=...)`
- **GOTCHA (locked)**: project's `requires-python = ">=3.10"`, so the `Z` shim shown above is REQUIRED. Do not rely on native `Z` parsing.
- **GOTCHA**: `request.client` can be `None` under some transports (TestClient path is fine in slowapi 0.1.9 which returns `"127.0.0.1"`). Handle `None` in `webhook_client_key` by returning `"unknown"` so the limiter doesn't crash.
- **VALIDATE**: Unit tests in Task 14.

---

### 6. UPDATE `src/grins_platform/middleware/rate_limit.py`

- **IMPLEMENT**: Add a new constant and re-export the webhook key function.
- **ADD** (after line 42):
  ```python
  WEBHOOK_LIMIT = "60/minute"
  ```
- **ADD** (bottom of file, above `setup_rate_limiting`):
  ```python
  # Re-export the webhook_client_key from services.sms.webhook_security so
  # route decorators in api/v1/callrail_webhooks.py can import it from a
  # rate-limit-local module without a cross-package dependency arrow.
  from grins_platform.services.sms.webhook_security import webhook_client_key  # noqa: E402, PLC0415
  ```
- **GOTCHA**: Watch for a circular import — `services.sms.webhook_security` must NOT import from `middleware.rate_limit`. Keep the function pure-stdlib.
- **VALIDATE**: `uv run python -c "from grins_platform.middleware.rate_limit import limiter, WEBHOOK_LIMIT, webhook_client_key; print(WEBHOOK_LIMIT, bool(webhook_client_key))"`

---

### 7. UPDATE `src/grins_platform/api/v1/callrail_webhooks.py`

This is the central edit. Changes layered in order so each is independently testable.

- **UPDATE constants (lines 30–32)**:
  ```python
  _REDIS_KEY_PREFIX = "sms:webhook:processed:callrail"
  _REDIS_MSGID_KEY_PREFIX = "sms:webhook:msgid:callrail"
  _REDIS_TTL_SECONDS = 7 * 86400  # 7 days (was 24 hours)
  _REDIS_MSGID_TTL_SECONDS = 30 * 86400  # 30 days
  ```
- **UPDATE `_is_duplicate` (lines 48–64)**: new signature `async def _is_duplicate(redis, db, provider: str, conversation_id: str, created_at: str, provider_message_id: str) -> bool`. Logic:
  1. If `redis` is not None: GET both `{_REDIS_KEY_PREFIX}:{conversation_id}:{created_at}` and `{_REDIS_MSGID_KEY_PREFIX}:{provider_message_id}`. If either → True. On exception, log `sms.webhook.redis_unavailable` and fall through.
  2. DB fallback: `WebhookProcessedLogRepository(db).exists(provider, provider_message_id)`. If True → raise DB-fallback alert (rate-limited via Redis key `sms:webhook:fallback_alert:sent` with 5-min TTL to prevent alert flood) and return True.
  3. Else → False.
- **UPDATE `_mark_processed` (lines 67–79)**: new signature `async def _mark_processed(redis, db, provider: str, conversation_id: str, created_at: str, provider_message_id: str) -> None`. Logic:
  1. Always call `WebhookProcessedLogRepository(db).mark_processed(provider, provider_message_id)` — the DB insert is the authoritative durable record.
  2. If `redis` is not None: best-effort `SET NX EX` on both keys; swallow exceptions with `logger.warning("sms.webhook.redis_mark_failed")`.
- **ADD freshness check** right after successful signature verification and successful JSON parse (between current lines 125 and 127):
  ```python
  from grins_platform.services.sms.webhook_security import check_freshness  # at module top

  created_at = str(payload.get("created_at", ""))
  fresh, skew = check_freshness(created_at)
  if not fresh:
      logger.warning("sms.webhook.replay_rejected", provider="callrail",
                     created_at=created_at, skew_seconds=skew)
      return Response(
          content='{"error": "Stale or missing timestamp"}',
          status_code=status.HTTP_400_BAD_REQUEST,
          media_type="application/json",
      )
  ```
- **UPDATE the duplicate-check block (lines 127–146)**: extract `provider_message_id = str(payload.get("resource_id", ""))` before the dedup check; pass through to the new signatures of `_is_duplicate` / `_mark_processed`. Reuse the single `redis` client for both read and write instead of opening one per call (minor perf fix in the same block).
- **APPLY the rate-limit decorator**:
  ```python
  from grins_platform.middleware.rate_limit import limiter, WEBHOOK_LIMIT, webhook_client_key

  @router.post("/inbound", status_code=status.HTTP_200_OK, ...)
  @limiter.limit(WEBHOOK_LIMIT, key_func=webhook_client_key)
  async def callrail_inbound(request: Request, db: AsyncSession = Depends(get_db)) -> Response:
      ...
  ```
- **CUSTOM 429 → 503 for this route only**: slowapi's global handler returns 429. We want 503 for the webhook so providers retry. Two options:
  - **Preferred**: Add an `exempt_when=...` parameter is NOT supported; instead, catch `RateLimitExceeded` explicitly at the top of the route body via a `try` is NOT how the decorator works. The cleanest approach is to register a **route-specific** exception handler that checks the request path (`if request.url.path.startswith("/api/v1/webhooks/")`) and returns 503 instead of 429. Update `rate_limit_exceeded_handler` in `middleware/rate_limit.py:45-68` to branch on path.
- **ADD signature-failure counter** around line 106 (when `sig_valid is False`):
  - Redis `INCR sms:webhook:sig_fail:{hour_bucket}` with `EXPIRE 3600`. On threshold (say, 50 fails / hour), raise `AlertType.WEBHOOK_SIGNATURE_FLOOD`; rate-limit alert emission to once per hour via `SET sms:webhook:sig_fail_alert:sent NX EX 3600`.
- **PATTERN REFERENCE**: Existing `_is_duplicate`, `_mark_processed`, `callrail_inbound` at `callrail_webhooks.py:48-197`.
- **GOTCHA (slowapi decorator)**: slowapi discovers the `Request` argument by NAME — the parameter must be named `request`. It already is (line 92). Do not rename.
- **GOTCHA (two Redis clients)**: current code opens a fresh `_get_redis()` for read and another for write. After this edit, open one client, use it for check + set, close in `finally`.
- **VALIDATE**:
  - `uv run ruff check src/grins_platform/api/v1/callrail_webhooks.py`
  - `uv run pyright src/grins_platform/api/v1/callrail_webhooks.py`
  - Integration tests in Task 17.

---

### 8. UPDATE `src/grins_platform/middleware/rate_limit.py` `rate_limit_exceeded_handler`

- **IMPLEMENT**: Return `503 Service Unavailable` (with `Retry-After: 60`) when the path starts with `/api/v1/webhooks/`; otherwise keep the existing `429 RATE_LIMIT_EXCEEDED` body.
- **EDIT** `rate_limit_exceeded_handler` body (lines 45–68):
  ```python
  path = request.url.path
  is_webhook = path.startswith("/api/v1/webhooks/")
  status_code = 503 if is_webhook else 429
  error_code = "WEBHOOK_RATE_LIMITED" if is_webhook else "RATE_LIMIT_EXCEEDED"
  message = (
      "Webhook endpoint is throttled. Please retry after the Retry-After window."
      if is_webhook
      else "Too many requests. Please try again later."
  )
  logger.warning(
      "security.rate_limit.exceeded",
      path=path, client=get_remote_address(request),
      retry_after=retry_after, status_code=status_code,
  )
  return JSONResponse(
      status_code=status_code,
      content={"success": False, "error": {"code": error_code, "message": message, "retry_after": retry_after}},
      headers={"Retry-After": str(retry_after)},
  )
  ```
- **GOTCHA**: Do NOT change the default 429 for non-webhook paths — existing auth/public endpoints rely on that.
- **VALIDATE**:
  - `uv run pytest -q src/grins_platform/tests -k "rate_limit" --maxfail=1`

---

### 9. UPDATE `src/grins_platform/services/sms_service.py` — per-phone and global throttles around auto-reply sends

- **IMPLEMENT**: Wrap the auto-reply send in `_process_confirmation_reply` (around lines 900–940) and in the poll-reply branch (around lines 800–825) with:
  ```python
  from grins_platform.services.sms.webhook_security import (
      autoreply_circuit_open, autoreply_phone_throttled,
  )

  redis = await _get_redis_client()  # reuse helper; if not present, create a small shim
  try:
      if await autoreply_circuit_open(redis):
          self._logger.warning("sms.auto_reply.suppressed_circuit_open",
                               phone=_mask_phone(reply_phone))
          # Raise alert ONCE per circuit-open window (guarded inside the helper).
          return  # skip auto-reply

      if await autoreply_phone_throttled(redis, reply_phone):
          self._logger.info("sms.auto_reply.phone_throttled",
                            phone=_mask_phone(reply_phone))
          return  # skip auto-reply
  finally:
      if redis is not None:
          with contextlib.suppress(Exception):
              await redis.aclose()
  ```
- **PATTERN REFERENCE**: Redis client open/close pattern already lives in `callrail_webhooks.py:37-45, 144-146`.
- **GOTCHA**: Auto-reply suppression must NOT bubble an error to `handle_inbound` — the reply itself was processed correctly; only the downstream courtesy SMS is skipped.
- **GOTCHA**: `_mask_phone` is already imported locally in `sms_service.py` (line 89); reuse it for log safety.
- **GOTCHA**: Don't skip the downstream `JobConfirmationResponse` insert or the reschedule follow-up SMS — only the *auto-reply acknowledgement* is gated by this throttle. The throttle is about cost control, not business logic.
- **VALIDATE**: Unit tests in Task 15.

---

### 10. UPDATE `src/grins_platform/services/sms/webhook_security.py` to emit alerts

- **IMPLEMENT**: Add alert-emission helpers that are called when circuit opens or DB-fallback fires. Accept an `AsyncSession` argument (not a dependency injection — the caller passes the live session so the alert lands in the same transaction).
- **NEW HELPERS**:
  - `async def emit_db_fallback_alert(db: AsyncSession, redis: Redis | None) -> None` — Redis-guarded emit-once-per-5-min (`sms:webhook:fallback_alert:sent`). Inserts `Alert(type="webhook_redis_fallback", severity="warning", entity_type="webhook", entity_id=uuid4(), message="Webhook dedup fell back to DB due to Redis unavailability.")`. On Redis error, skip — alert flood tolerance > missed alert here.
  - `async def emit_signature_flood_alert(db: AsyncSession, redis: Redis | None, count: int) -> None` — Redis-guarded emit-once-per-hour.
  - `async def emit_circuit_open_alert(db: AsyncSession, redis: Redis | None, counter: int) -> None` — Redis-guarded emit-once-per-circuit-open-window (5 min).
- **PATTERN REFERENCE**: `AlertRepository(session).create(Alert(...))` via `repositories/alert_repository.py:47-69`; enum values set as *strings*, not `.value`, per `models/alert.py:58-59`.
- **GOTCHA**: `entity_id` is `nullable=False` on the Alert model — synthesize a `uuid4()` for webhook-event alerts that have no natural entity target, and encode the contextual identifier (e.g., IP address) into `message`.
- **VALIDATE**: Unit tests asserting emit-once behaviour.

---

### 11. UPDATE `src/grins_platform/services/background_jobs.py` — register prune job

- **IMPLEMENT**: Add an async `prune_webhook_processed_logs_job()` function and register it in `register_scheduled_jobs(scheduler)` (the function at `services/background_jobs.py:973`).
- **JOB FUNCTION (add near similar async jobs in the same file)**:
  ```python
  async def prune_webhook_processed_logs_job() -> None:
      """Daily prune: delete webhook_processed_logs rows older than 30 days."""
      from grins_platform.database import get_database_manager  # noqa: PLC0415
      from grins_platform.repositories.webhook_processed_log_repository import (  # noqa: PLC0415
          WebhookProcessedLogRepository,
      )

      db_manager = get_database_manager()
      async for session in db_manager.get_session():
          repo = WebhookProcessedLogRepository(session)
          deleted = await repo.prune_older_than(days=30)
          await session.commit()
          logger.info(
              "scheduler.webhook_processed_logs.pruned",
              deleted=deleted,
          )
  ```
- **REGISTRATION (add inside `register_scheduled_jobs` alongside the existing `scheduler.add_job(...)` calls around line 978)**:
  ```python
  scheduler.add_job(
      prune_webhook_processed_logs_job,
      "cron",
      hour=3,
      minute=30,
      id="prune_webhook_processed_logs",
      replace_existing=True,
  )
  ```
- **PATTERN REFERENCE**: `background_jobs.py:978-993` for `scheduler.add_job` shape; `background_jobs.py:84-91` for the `async for session in db_manager.get_session():` idiom.
- **GOTCHA**: Jobs run in APScheduler's async executor — `await session.commit()` explicitly after the delete because the session factory doesn't auto-commit for background jobs.
- **GOTCHA**: Do NOT import models at the top of the module file unless the existing jobs do — use lazy imports inside the function to avoid circular imports at scheduler startup (follow the in-function import style above).
- **VALIDATE**:
  - `uv run python -c "from grins_platform.services.background_jobs import prune_webhook_processed_logs_job; print(prune_webhook_processed_logs_job.__name__)"`
  - After wiring, `uv run python -c "from grins_platform.services.background_jobs import register_scheduled_jobs; print('ok')"`.

---

### 12. Add env-var documentation

- **IMPLEMENT**: Append to `.env.example` (or equivalent template file — search the repo; `grep -rl 'REDIS_URL' . | grep -i env` to find it) the new env vars with commented defaults:
  ```
  # Webhook security (Gap 07)
  WEBHOOK_CLOCK_SKEW_SECONDS=300
  WEBHOOK_TRUSTED_PROXY_CIDRS=          # comma-separated, e.g. "10.0.0.0/8,172.16.0.0/12"
  WEBHOOK_AUTOREPLY_PHONE_TTL_S=60
  WEBHOOK_AUTOREPLY_GLOBAL_WINDOW_S=10
  WEBHOOK_AUTOREPLY_CIRCUIT_THRESHOLD=30
  ```
- **VALIDATE**: `grep WEBHOOK_CLOCK_SKEW .env.example` returns a match.

---

### 13. CREATE `src/grins_platform/tests/unit/test_webhook_processed_log_repository.py`

- **IMPLEMENT**: Exercise `exists`, `mark_processed` (including race condition via `on_conflict_do_nothing`), `prune_older_than`.
- **PATTERN**: Mirror `src/grins_platform/tests/unit/test_rate_limit_tracker.py` for async-test shape + in-memory alternatives. For DB tests, use the project's existing `async_db_session` fixture (find it in conftest).
- **TESTS**:
  - `test_exists_returns_false_for_unknown_message`
  - `test_mark_then_exists_returns_true`
  - `test_mark_is_idempotent_under_race` — call `mark_processed` twice with the same `(provider, message_id)` in two concurrent tasks; both must succeed, only one row exists.
  - `test_prune_older_than_removes_old_rows` — insert a row with a backdated `created_at`, call `prune_older_than(1)`, assert deletion.
- **VALIDATE**: `uv run pytest -q src/grins_platform/tests/unit/test_webhook_processed_log_repository.py -v`.

---

### 14. CREATE `src/grins_platform/tests/unit/test_webhook_security.py`

- **IMPLEMENT**: Cover `check_freshness`, `webhook_client_key`, `autoreply_phone_throttled`, `autoreply_circuit_open`.
- **PATTERN**: Hypothesis where helpful (`@given` over ISO8601 timestamps, over IP-in/out-of-CIDR).
- **TESTS**:
  - `test_check_freshness_rejects_stale` — set `now` 301s after `created_at`.
  - `test_check_freshness_accepts_within_window` — 299s.
  - `test_check_freshness_rejects_missing_or_malformed`.
  - `test_check_freshness_handles_z_suffix` — `2026-04-21T12:00:00Z` should parse.
  - `test_webhook_client_key_returns_peer_when_no_proxy`.
  - `test_webhook_client_key_returns_xff_leftmost_when_peer_is_trusted` — set `TRUSTED_PROXY_CIDRS` via monkeypatch, craft mock request with `X-Forwarded-For: 1.2.3.4, 10.0.0.5`.
  - `test_webhook_client_key_ignores_xff_when_peer_untrusted`.
  - `test_autoreply_phone_throttled_first_call_returns_false_then_true`.
  - `test_autoreply_phone_throttled_fails_open_when_redis_none_or_exception`.
  - `test_autoreply_circuit_open_trips_after_threshold`.
  - `test_autoreply_circuit_open_stays_open_for_reset_duration`.
- **MOCKING**: Use `AsyncMock()` for redis; follow `test_pbt_callrail_sms.py:20-21` imports.
- **VALIDATE**: `uv run pytest -q src/grins_platform/tests/unit/test_webhook_security.py -v`.

---

### 15. EXTEND `src/grins_platform/tests/unit/test_pbt_callrail_sms.py` — new property for dual-key dedup

- **IMPLEMENT**: Add a test class `TestDualKeyDedupInvariant` with a property: "given a stream of webhook payloads with arbitrary `conversation_id`/`created_at`/`resource_id`, the set of processed `resource_id`s equals the set of unique `resource_id`s seen". Fake the redis + DB layer so the property only tests the dedup branching logic.
- **VALIDATE**: `uv run pytest -q src/grins_platform/tests/unit/test_pbt_callrail_sms.py -k Dedup -v`.

---

### 16. CREATE `src/grins_platform/tests/integration/test_callrail_webhook_endpoint.py`

- **IMPLEMENT**: First integration tests that POST to `POST /api/v1/webhooks/callrail/inbound` via the **async** `async_client: AsyncClient` fixture.
- **FIRST LINES** (locked imports / marker):
  ```python
  from __future__ import annotations

  import base64
  import hashlib
  import hmac
  import json
  from datetime import datetime, timezone
  from typing import Any
  from unittest.mock import AsyncMock, patch

  import pytest
  from httpx import AsyncClient

  pytestmark = pytest.mark.integration
  ```
- **PATTERN**: mirror the async fixture pattern used by `test_auth_integration.py:155` — `async def test_X(self, async_client: AsyncClient, monkeypatch) -> None: response = await async_client.post(...)`.
- **HMAC HELPER** (local to this test file):
  ```python
  def sign(body: bytes, secret: str) -> str:
      return base64.b64encode(
          hmac.new(secret.encode(), body, hashlib.sha1).digest(),
      ).decode()
  ```
- **ENV FIXTURE** (module-level autouse):
  ```python
  @pytest.fixture(autouse=True)
  def _callrail_env(monkeypatch: pytest.MonkeyPatch) -> None:
      monkeypatch.setenv("SMS_PROVIDER", "callrail")
      monkeypatch.setenv("CALLRAIL_WEBHOOK_SECRET", "test-secret")
      monkeypatch.setenv("CALLRAIL_API_KEY", "test-api-key")
      monkeypatch.setenv("CALLRAIL_ACCOUNT_ID", "ACCtest")
      monkeypatch.setenv("CALLRAIL_COMPANY_ID", "COMtest")
      monkeypatch.setenv("CALLRAIL_TRACKING_NUMBER", "+19525293750")
  ```
  `get_sms_provider()` reads env live on every call, so no cache reset is needed.
- **PAYLOAD HELPER** — uses `datetime.now(timezone.utc).isoformat()` for `created_at` so the freshness check passes:
  ```python
  def build_payload(resource_id: str = "inbound_test_1") -> dict[str, Any]:
      return {
          "resource_id": resource_id,
          "conversation_id": "conv_abc",
          "created_at": datetime.now(timezone.utc).isoformat(),
          "source_number": "+19527373312",
          "destination_number": "+19525293750",
          "content": "Y",
          "thread_resource_id": "thread_123",
      }
  ```
- **TESTS**:
  - `test_valid_signature_fresh_payload_processes_once` — body signed, status 200, body contains `"status": "processed"`.
  - `test_invalid_signature_returns_403` — wrong secret → 403.
  - `test_missing_signature_header_returns_403`.
  - `test_stale_payload_returns_400_replay_rejected` — craft payload with `created_at = (now - 10 minutes)` and valid signature → 400.
  - `test_replay_same_payload_returns_200_already_processed` — POST twice back to back; second returns `"status": "already_processed"`.
  - `test_redis_down_db_has_record_returns_already_processed` — `monkeypatch` `grins_platform.api.v1.callrail_webhooks._get_redis` to return an `AsyncMock` whose `.get` / `.set` raise; pre-insert a `WebhookProcessedLog` row via `async_db_session`-like fixture (or via a direct `AsyncSessionLocal()` call inside the test body, committing after); POST valid signed payload → 200 `already_processed`.
  - `test_rate_limit_returns_503_after_threshold` — send 61 POSTs with distinct `resource_id` within a single minute; assert the 61st returns 503 with header `Retry-After: 60`. Reset the slowapi `in-memory` storage before the test (see gotcha below).
- **GOTCHA (rate-limit test isolation)**: slowapi's `Limiter` is instantiated at module import time with `storage_uri = REDIS_URL or "memory://"`. In unit-test environments where `REDIS_URL` may or may not point to a live Redis, the counter persists across tests in the same process. Reset the limiter state at the start of the rate-limit test:
  ```python
  from grins_platform.middleware.rate_limit import limiter
  limiter.reset()
  ```
- **GOTCHA (test DB cleanup)**: integration tests hit a real Postgres without per-test rollback (verified). The replay and DB-fallback tests insert rows into `webhook_processed_logs` — clean up with a `finally:` block that deletes test rows by `provider_message_id` prefix, OR wrap the test body in a transaction and roll back.
- **GOTCHA (async fixture scope)**: `async_client` is function-scoped per conftest. Do not reuse it across parametrized tests that rely on env-var monkeypatches.
- **VALIDATE**: `uv run pytest -q src/grins_platform/tests/integration/test_callrail_webhook_endpoint.py -v -m integration`.

---

### 17. Manual smoke / observability check

- **ACTIONS**:
  - Local: send one live-ish webhook via `curl` with a correctly signed body; confirm logs show `sms.webhook.inbound action=...` and no `sms.webhook.replay_rejected`.
  - Flip the server clock forward 10 minutes (mock or env); confirm `sms.webhook.replay_rejected` log + 400 response.
  - `REDIS_URL=redis://127.0.0.1:6399 uv run ...` with Redis stopped; confirm DB-fallback path logs `sms.webhook.db_fallback_hit` and inserts one `webhook_processed_log` row per unique `resource_id`; confirm one `Alert(type=webhook_redis_fallback)` per 5-min window regardless of call count.
  - Fire 61+ distinct valid requests in under 60s from the same IP; confirm the 61st returns 503.
- **VALIDATE**:
  - `uv run psql $DATABASE_URL -c "SELECT count(*) FROM webhook_processed_log;"` shows growth.
  - `uv run psql $DATABASE_URL -c "SELECT type, count(*) FROM alerts WHERE type LIKE 'webhook_%' GROUP BY type;"`

---

## TESTING STRATEGY

### Unit Tests

- **Targets**: helper module (`webhook_security.py`), repository, new enum members.
- **Fixtures**: `AsyncMock()` for Redis, project's `async_db_session` fixture for repo tests (verify name in `conftest.py`).
- **Framework**: pytest, pytest-asyncio, hypothesis. `@pytest.mark.unit` marker to match project convention.

### Integration Tests

- **Targets**: `/api/v1/webhooks/callrail/inbound` end-to-end with `TestClient`.
- **Scope**: signature-valid + fresh + new → 200; signature-invalid → 403; stale → 400; replay → 200 already_processed; Redis-outage + DB-hit → 200 already_processed; rate-limit → 503.
- **DB state**: use a transactional test fixture so rows written via the endpoint are isolated per test.

### Edge Cases

- Missing `created_at` in body.
- `created_at` formatted as epoch int (not ISO 8601) — must reject.
- `resource_id` missing → fall back to `(conversation_id, created_at)` key alone; test coverage for this code path.
- Two concurrent calls with the same `resource_id` → exactly one processed; the other returns `already_processed`.
- `X-Forwarded-For` containing IPv6, or a malformed header.
- `X-Forwarded-For` from an untrusted peer — must NOT be honoured.
- Redis returns a stale circuit-open key that is about to expire — next call must re-open based on the fresh counter window.
- `mark_processed` is called from the route before auto-reply fan-out, so a crash mid-auto-reply doesn't create a duplicate on retry.

---

## VALIDATION COMMANDS

Execute every command to ensure zero regressions and 100% feature correctness.

### Level 1: Syntax & Style (exact project commands from `scripts/dev.sh:43-55`)
- `uv run ruff check src/ tests/`
- `uv run ruff format --check src/ tests/`
- Primary type check: `uv run mypy src/`
- Secondary type check (strict; excludes tests): `uv run pyright src/grins_platform`

### Level 2: Unit Tests
- `uv run pytest -q src/grins_platform/tests/unit -k "webhook_security or webhook_processed_log" -v`
- `uv run pytest -q src/grins_platform/tests/unit/test_pbt_callrail_sms.py -k Dedup -v`

### Level 3: Integration Tests (requires local Postgres running via `docker-compose.dev.yml up postgres redis -d`)
- `uv run pytest -q src/grins_platform/tests/integration/test_callrail_webhook_endpoint.py -v -m integration`

### Level 4: Full Suite (regression)
- `uv run pytest -q src/grins_platform/tests --maxfail=5`

### Level 5: Migration sanity
- `uv run alembic heads` — exactly one head; should show `20260421_100200` after the new migration is applied.
- `uv run alembic upgrade head`
- `uv run alembic downgrade -1 && uv run alembic upgrade head` — round trip.
- `uv run alembic check` — no schema drift.

### Level 6: Railway dev verification (after Task 0)
- `railway variables --service Grins-dev 2>&1 | grep -i REDIS_URL` — must show non-empty value.
- `railway logs --service Grins-dev 2>&1 | grep "security.rate_limit.configured" | tail -1` — must say `storage=redis`.

### Level 7: Manual (covered in Task 17)
- Smoke test of each of the 4 scenarios locally.

---

## ACCEPTANCE CRITERIA

- [ ] 7.A — Replay rejected outside 5-minute window; Redis TTLs extended to 7d / 30d; dedup checks both `(conversation_id, created_at)` and `resource_id` keys.
- [ ] 7.B — With Redis unavailable, a replayed webhook returns `already_processed` by DB fallback (verified by integration test).
- [ ] 7.B — `webhook_processed_log` table exists; repository's `mark_processed` is race-safe via `on_conflict_do_nothing`; prune job removes rows > 30 days old.
- [ ] 7.C — `/webhooks/callrail/inbound` returns `503` (not 429) after 60 calls/minute from one client IP; trusted proxy handling for `X-Forwarded-For` verified.
- [ ] 7.C — Per-phone auto-reply throttle prevents more than one auto-reply per `from_phone` per 60s.
- [ ] 7.C — Global circuit breaker opens at 30 auto-replies / 10s, stays open for 5 minutes, raises an `Alert`.
- [ ] Three new `AlertType` enum values added; `Alert` rows appear in DB for DB-fallback, signature-flood, and circuit-open events; each is emit-once per their own window.
- [ ] Signature verification, JSON parsing, `parse_inbound_webhook`, and `handle_inbound` semantics are unchanged.
- [ ] All unit + integration + PBT tests pass.
- [ ] `ruff check --fix`, `ruff format`, `mypy`, and `pyright` all pass with zero errors (per `.kiro/steering/code-standards.md`).
- [ ] `set_request_id()` / `clear_request_id()` wrapping added to the route body; `DomainLogger.api_event` calls emitted for new branches alongside the preserved `sms.webhook.*` event names (per `.kiro/steering/api-patterns.md`).
- [ ] Integration test verifies `GET /api/v1/alerts?type=webhook_redis_fallback` returns the alert row after fallback fires (cross-feature integration per steering).
- [ ] Coverage on the new service (`webhook_security.py`) and repository meets the 90%+ target (per `.kiro/steering/spec-testing-standards.md`).
- [ ] Alembic migration upgrades and downgrades cleanly.
- [ ] Env vars documented in `.env.example` (or equivalent).
- [ ] No regressions in existing tests (e.g. `test_pbt_callrail_sms.py` still passes unchanged other than the new class).

---

## COMPLETION CHECKLIST

- [ ] Task 0 — Redis provisioned on Railway dev (`REDIS_URL` set on `Grins-dev`; startup log reports `storage=redis`).
- [ ] Task 1 — enum members added.
- [ ] Task 2 — `WebhookProcessedLog` model created.
- [ ] Task 3 — Alembic migration created and upgraded.
- [ ] Task 4 — `WebhookProcessedLogRepository` created.
- [ ] Task 5 — `services/sms/webhook_security.py` created with four helpers.
- [ ] Task 6 — `middleware/rate_limit.py` updated with `WEBHOOK_LIMIT` and `webhook_client_key` re-export.
- [ ] Task 7 — `callrail_webhooks.py` route updated (freshness, dual-key dedup, DB fallback, slowapi decorator, signature-flood counter).
- [ ] Task 8 — `rate_limit_exceeded_handler` updated to 503-for-webhooks.
- [ ] Task 9 — `sms_service.py` auto-reply throttle + circuit-breaker wrapping.
- [ ] Task 10 — alert emission helpers added in `webhook_security.py`.
- [ ] Task 11 — prune background job registered.
- [ ] Task 12 — env vars documented.
- [ ] Task 13 — repository unit tests.
- [ ] Task 14 — `webhook_security.py` unit tests.
- [ ] Task 15 — PBT extension.
- [ ] Task 16 — integration tests.
- [ ] Task 17 — manual smoke validation pass.
- [ ] All validation commands green.

---

## NOTES

**Design trade-offs accepted (matches Gap 07's explicit recommendations):**

- **Fail-open throttle vs. fail-closed dedup.** Per-phone throttle and global circuit breaker fail *open* when Redis is unavailable — dedup correctness is handled by the DB fallback layer, so the cost-control layer can fail open safely. Fail-closed throttles would drop legitimate auto-replies during Redis outages (the very thing we want to avoid).
- **503 vs. 429 on inbound rate limit.** 503 tells providers "retry later"; 429 is "you're doing something wrong". For the webhook endpoint we want the former because legitimate retries are normal. For other public endpoints we keep 429.
- **Emit-once alerting.** All three new alert types are rate-limited at emission time via Redis keys. This prevents an alert flood during a sustained incident while still firing on fresh incidents. Downside: if Redis is the incident, the first DB-fallback alert fires once and then silence — acceptable because the DB-fallback path also emits structured logs per event and Gap 14's dashboard hook will still see them.
- **Trusted-proxy handling.** We maintain an explicit allowlist rather than blindly honouring `X-Forwarded-For`. On Railway, the edge IPs are stable — operators configure `WEBHOOK_TRUSTED_PROXY_CIDRS` for production. Left empty in dev → direct remote address.
- **`created_at` as the freshness anchor.** CallRail documents no dedicated timestamp header; the body field is what we have. Body is HMAC-covered so the timestamp is authenticated — good enough.
- **Not implemented in this plan (explicitly out of scope, worth a follow-up):**
  - Migrating HMAC-SHA1 to SHA256. Gap 07 itself notes this is not urgent because HMAC-SHA1 is still strong for auth, and the algorithm is dictated by CallRail's contract.
  - Gap 14 dashboard widget surfacing these alerts — the alert rows exist; the UI that consumes them lives in a separate gap's plan.
  - Gap 05 audit-log tie-in — the route already logs structured events; adding audit-log rows for webhook acceptance is a Gap-05 concern.

**Cross-gap hooks satisfied:**
- Gap 14: `WEBHOOK_SIGNATURE_FLOOD` and `WEBHOOK_REDIS_FALLBACK` alert types now exist; the dashboard implementation of Gap 14 will reuse them.
- Gap 03: tighter replay protection means a stale `Y` from an old appointment can no longer re-target the appointment long after the original inbound was processed.

**Confidence score for one-pass implementation: 10/10 (with caveat).**

All previously-flagged risks are now eliminated in the plan text itself:

1. ✅ **Alembic head locked.** `down_revision = "20260422_100000"` (verified live on 2026-04-21).
2. ✅ **Table name convention locked.** `webhook_processed_logs` (plural, verified against all 48 existing tables).
3. ✅ **Test fixture name locked.** `async_client: AsyncClient` (httpx.AsyncClient); `asyncio_mode = "auto"`; `@pytest.mark.integration` marker; env autouse fixture pattern provided verbatim.
4. ✅ **Python 3.10 compatibility locked.** `check_freshness` includes the explicit `Z → +00:00` shim because `requires-python = ">=3.10"` and native `Z` parsing is 3.11+.
5. ✅ **SMS factory wiring locked.** `get_sms_provider()` reads env vars live per call; no singleton invalidation needed. The five `CALLRAIL_*` env vars + `SMS_PROVIDER=callrail` are monkeypatched in the autouse fixture.
6. ✅ **slowapi decorator order locked.** `@limiter.limit(...)` goes BETWEEN `@router.post(...)` and the function; `request: Request` parameter stays named exactly `request`; slowapi 0.1.9 handles `request.client is None` (returns `"127.0.0.1"`); `webhook_client_key` also defends against `None`.
7. ✅ **Postgres upsert locked.** `pg_insert(...).on_conflict_do_nothing(index_elements=...)` — identical to existing `services/sms/consent.py:269`; integration tests hit real Postgres (verified).
8. ✅ **APScheduler pattern locked.** Exact `scheduler.add_job(fn, "cron", hour=X, minute=Y, id=..., replace_existing=True)` signature + async session acquisition (`async for session in get_database_manager().get_session():`) provided verbatim.
9. ✅ **Alert.entity_id nullability locked.** `nullable=False` confirmed; `uuid4()` synthesis is mandated.
10. ✅ **Ruff target locked.** `target-version = "py39"`; every new file starts with `from __future__ import annotations`.

**The one remaining caveat (Task 0 infrastructure, NOT a code risk):**

Redis is not currently provisioned on Railway dev (verified). The code will function without Redis by falling back to the DB dedup path, but the cost-control layers (per-phone throttle, global circuit breaker, slowapi per-IP rate limiter) depend on Redis to be meaningful. Task 0 provisions Redis on Railway dev before merge. If the operator chooses to defer Redis provisioning:
- Tests still pass (Redis paths are mocked).
- Prod deploy must not happen until Redis is also provisioned on prod — otherwise 7.C's rate-limit stores to `memory://` per-instance, which is useless behind a multi-replica deploy.

This caveat is a pre-flight ops task, not an implementation risk. With Task 0 executed before Task 17 (smoke validation), the plan is **one-pass ready**.
