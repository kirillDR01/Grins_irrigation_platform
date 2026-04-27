# Feature: Pick-Jobs Page — City Facet Hygiene + Requested-Week + Tier-Aware Priority

The following plan should be complete, but it's important that you validate documentation and codebase patterns and task sanity before you start implementing. Pay special attention to naming of existing utils, types, and models. Import from the right files etc.

## Feature Description

The `/schedule/pick-jobs` page (`PickJobsPage`) has three related defects in the data shown on the left **City** facet rail and the **Requested** / **Priority** columns of the central job table:

1. **City facet contamination.** The City group lists raw street addresses ("11071 Jackson Drive", "4355 Vinewood Ln Plymouth, MN 55442", "5808 View Ln Edina 55436", "Andover, MN 55304", etc.) alongside actual city names, and the same city appears multiple times due to case/whitespace/state-suffix variants (the user reports "Eden Prairie" appearing repeatedly). The rail should list **canonical city names only**, deduplicated case-insensitively.
2. **Requested column always shows `—`.** The backend `/api/v1/schedule/jobs-ready` response Pydantic schema does not include `requested_week`, even though the frontend `JobReadyToSchedule` TS type expects it. The "week requested" is set on each job via `JobWeekEditor` on the Jobs tab and lives in `jobs.target_start_date` (Monday-anchored ISO date). The pick-jobs endpoint must surface it.
3. **Priority column always shows `—`.** Same root cause: the schema does not include `priority_level`. Plus the **business rule** for priority on this view should not just mirror `Job.priority_level`. Effective priority on the picker should escalate when:
   - the customer has an **active service agreement** (paid tier), and
   - the customer is tagged with the system "priority" `CustomerTag` (manual VIP marker).

   Today the only signal sent at all (`priority: str` — "0"/"1"/"2") is dropped by the frontend (it reads `priority_level`, not `priority`).

This plan fixes all three together, since they share one root file (`api/v1/schedule.py::get_jobs_ready_to_schedule`) and one schema (`schemas/schedule_explanation.py::JobReadyToSchedule`). It also adds defensive city normalization in the facet rail itself so dirty rows in production don't keep leaking into the UI between fixes, and adds a data-hygiene migration that strips obvious "address-in-city" rows.

## User Story

As a **scheduler / Viktor (admin)**
I want **the Pick-Jobs page's City filter to show only real cities (no addresses, no duplicates), and the Requested + Priority columns to actually be populated**
So that **I can quickly filter jobs down to a service area and visually triage VIP / agreement / requested-this-week work without scanning every row.**

## Problem Statement

The current Pick-Jobs page renders correctly visually, but the underlying data is wrong:

- The City facet group is built from `jobs.map(j => j.city)` (`FacetRail.tsx:86`), which trusts whatever string is in `properties.city`. That column is `String(100), nullable=False` (`models/property.py:84`) and accepts anything. Multiple ingestion paths (`property_service._parse_address`, Google Sheets imports `services/google_sheets_service.py:252,305,408`, lead intake) write malformed addresses or unnormalized casing into it.
- The backend response schema `JobReadyToSchedule` (`schemas/schedule_explanation.py:133-144`) does not declare `requested_week`, `priority_level`, `address`, `customer_tags`, or any of the "extended" fields the frontend expects (`features/schedule/types/index.ts:411-422`). The endpoint (`api/v1/schedule.py:393-479`) never sets them. So every row renders `—` for Requested + Priority.
- There is no concept of **derived/effective priority** on the picker. Two real business signals (active service agreement, "priority" customer tag) exist independently in the DB but never reach this view.

## Solution Statement

Three coordinated changes, in this order:

1. **Backend** — extend the Pydantic schema and the endpoint to populate the extended fields the frontend already wants. Compute an `effective_priority_level` server-side (ranges 0–2) using:
   `max(Job.priority_level, 1 if customer has 'priority' tag else 0, 1 if customer has active service_agreement else 0)`.
   Surface `target_start_date` as `requested_week` (already a Monday by `JobWeekEditor` convention).
2. **Frontend** — defensively normalize and dedupe city values in `FacetRail` (trim, title-case, drop entries that look like a street address or a `state+zip` token), so that even if a few dirty rows linger in prod the UI hides them. No type changes required on the client (`JobReadyToSchedule` already declares the extended fields).
3. **Data hygiene** — Alembic migration that runs a one-shot SQL pass on `properties` to (a) trim/normalize whitespace, (b) detect rows where `city` contains a digit-prefixed street or a `state ZIP` pattern and move them to a flag column / set city to a sentinel `'Unknown'`, and (c) collapse case-only duplicates by re-titlecasing. Also tighten `property_service._parse_address` to refuse address-shaped tokens as `city`.

## Feature Metadata

**Feature Type**: Bug Fix (with small Enhancement for tier-aware priority)
**Estimated Complexity**: Medium
**Primary Systems Affected**:
- `src/grins_platform/api/v1/schedule.py` (jobs-ready endpoint)
- `src/grins_platform/schemas/schedule_explanation.py` (response schema)
- `src/grins_platform/services/property_service.py` (intake hardening)
- `src/grins_platform/migrations/versions/` (data-hygiene migration)
- `frontend/src/features/schedule/components/FacetRail.tsx` (defensive normalization)
- Tests in both layers
**Dependencies**: none new (uses existing SQLAlchemy, Pydantic, Alembic)

---

## CONTEXT REFERENCES

### Relevant Codebase Files — IMPORTANT: YOU MUST READ THESE BEFORE IMPLEMENTING

**Backend (jobs-ready endpoint and schemas):**
- `src/grins_platform/api/v1/schedule.py` lines 388–479 — current `/jobs-ready` handler. Joins `Job ⨝ Customer LEFT JOIN Property`. Will be extended to also join active `ServiceAgreement` and aggregate `CustomerTag` labels.
- `src/grins_platform/schemas/schedule_explanation.py` lines 133–159 — `JobReadyToSchedule` and `JobsReadyToScheduleResponse`. Add the missing fields here.
- `src/grins_platform/schemas/__init__.py` lines 131–132, 217, 223 — re-exports; nothing to change unless we rename anything.
- `src/grins_platform/models/job.py` lines 70–270 — `Job` model. Note: `target_start_date` (line 161, `Date`), `priority_level` (line 149, `Integer`, default 0), `service_agreement_id` (line 129, FK), `requested_at` (line 193, `DateTime`).
- `src/grins_platform/models/property.py` lines 80–90 — `city` is `String(100), nullable=False`; no validation today.
- `src/grins_platform/models/customer_tag.py` lines 30–80 — `label: String(32)`, free-text, no enum constraint. The system convention is the literal string `"priority"` for VIP.
- `src/grins_platform/models/service_agreement.py` — `ServiceAgreement` (status field used for "active"). Inspect to confirm the active-status string before writing the join filter.
- `src/grins_platform/services/property_service.py` lines 429–540 — `_parse_address` and `ensure_property_for_lead`. Tighten the city-extraction so address-shaped tokens fall back to `_UNKNOWN_CITY`.
- `src/grins_platform/tests/integration/test_jobs_ready_endpoint.py` — existing endpoint shape tests; extend with assertions on the new fields.

**Frontend (Pick-Jobs page):**
- `frontend/src/features/schedule/pages/PickJobsPage.tsx` lines 42–392 — composes `FacetRail` + `JobTable` + `SchedulingTray`. **No changes required** beyond optional sort-key default tweak; reads `priority_level` and `requested_week` already.
- `frontend/src/features/schedule/components/FacetRail.tsx` lines 79–99, 187–209, 211–214 — facet construction and `formatWeekLabel`. This is where city normalization/dedup happens.
- `frontend/src/features/schedule/types/index.ts` lines 403–422 — `JobReadyToSchedule` TS interface; already declares `priority_level`, `requested_week`, `address`, `customer_tags`, etc. **No type changes required.**
- `frontend/src/features/schedule/types/pick-jobs.ts` lines 30–43 — `FacetState`, `SortKey`, `PriorityLevel` (`'0' | '1' | '2'`). Reuse as is.
- `frontend/src/features/schedule/components/JobTable.tsx` lines 110–215 — renders `priority_level` as a star, `requested_week` via `formatWeek`. **No changes required.**
- `frontend/src/features/schedule/components/FacetRail.test.tsx` (sibling test file shown in `ls`) — extend with cases for the new normalization.
- `frontend/src/features/schedule/pages/PickJobsPage.test.tsx` lines 86–101 — fixture pattern for `JobReadyToSchedule`. Use this when adding tests.

**Migration scaffolding pattern:**
- `src/grins_platform/migrations/versions/20260428_100000_add_customer_email_bounced_at.py` — current Alembic file format. The latest head is `20260430_120000`; new migration must declare `down_revision = "20260430_120000"`.

### New Files to Create

- `src/grins_platform/migrations/versions/20260501_120000_normalize_property_city.py` — one-shot data hygiene migration (see Task 7).
- `src/grins_platform/tests/unit/test_property_city_validation.py` — unit tests for the tightened `_parse_address` and any new `_normalize_city` helper.
- `frontend/src/features/schedule/utils/city.ts` — pure, testable helpers `normalizeCity(raw) → string | null` and `isAddressLike(raw) → boolean`.
- `frontend/src/features/schedule/utils/city.test.ts` — unit tests for the above.

### Relevant Documentation — READ THESE BEFORE IMPLEMENTING

- [SQLAlchemy 2.0 — joined-load with `selectinload`](https://docs.sqlalchemy.org/en/20/orm/queryguide/relationships.html#selectinload) — needed if you switch from the current tuple `(Job, Customer, Property)` join to ORM-eager loading the customer's tags + active agreement to avoid N+1.
- [Pydantic v2 — `Field(default_factory=...)` and `model_config`](https://docs.pydantic.dev/latest/concepts/models/#fields-with-non-hashable-default-values) — pattern used in existing schemas like `JobsReadyToScheduleResponse`.
- [Alembic — data migration with `op.execute()`](https://alembic.sqlalchemy.org/en/latest/ops.html#alembic.operations.Operations.execute) — used heavily in this repo, e.g. `20260429_100100_seed_day_2_reminder_settings.py`.
- No external library docs needed — everything is in-stack.

### Project Standards (from `.kiro/steering/`)

These are non-negotiable. Every task must comply.

**Backend logging (`code-standards.md`, `tech.md`, `api-patterns.md`)**
- Pattern: `{domain}.{component}.{action}_{state}`.
- Endpoints already use `endpoints = ScheduleEndpoints()` where `ScheduleEndpoints(LoggerMixin)` (`api/v1/schedule.py:69-75`). Continue calling `endpoints.log_started("get_jobs_ready", ...)` / `log_completed` / `log_failed` — do not introduce a new logger. Add structured fields for the new behavior: e.g. `effective_priority_count`, `with_active_agreement_count`.
- Never log PII (customer names, phone, email). Counts and IDs only.

**Three-tier testing (`code-standards.md`, `tech.md`, `spec-testing-standards.md`)**
- Unit: `src/grins_platform/tests/unit/` with `@pytest.mark.unit`, all deps mocked. Naming: `test_{method}_with_{condition}_returns_{expected}`.
- Functional: `src/grins_platform/tests/functional/` with `@pytest.mark.functional`, real DB. Naming: `test_{workflow}_as_user_would_experience`.
- Integration: `src/grins_platform/tests/integration/` with `@pytest.mark.integration`, full system. Naming: `test_{feature}_works_with_existing_{component}`.
- Property-based (Hypothesis) is required for invariants. The "effective priority is monotone in (base priority, has_priority_tag, has_active_agreement)" invariant qualifies — see Task 13.

**Type safety**
- All new functions get type hints + return types. No implicit `Any`.
- Must pass MyPy AND Pyright with zero errors (project enforces both).

**Coverage targets (`spec-quality-gates.md`)**
- Backend services: 90%+. Frontend components: 80%+. Frontend hooks: 85%+. Utils: 90%+.

**Frontend conventions (`frontend-patterns.md`, `frontend-testing.md`)**
- VSA: features import only from `core/` and `shared/`, never from another feature. (This plan stays inside `features/schedule/`, no cross-feature imports needed.)
- `data-testid` convention: `{feature}-page`, `{feature}-table`, `{feature}-row`, `{action}-{feature}-btn`. The pick-jobs page already follows this (`pick-jobs-page`, `job-table`, `job-row-{id}`, `job-table-select-all`, `facet-rail`, `facet-group-city`, `facet-value-city-{value}`). New facet entries must keep using `facet-value-city-{canonical}`.
- Co-located tests: `Component.test.tsx` next to `Component.tsx`; util tests next to util.
- Vitest + React Testing Library. `QueryProvider` wrapper for hook/component tests that hit TanStack Query.
- Imports: `@/` = `frontend/src/`. Use `@/features/schedule/...`, `@/shared/...`, `@/core/...`.

**Quality gate (must pass before declaring done — `tech.md`, `spec-quality-gates.md`)**
```bash
# Backend
uv run ruff check --fix src/ && uv run ruff format src/
uv run mypy src/ && uv run pyright src/
uv run pytest -m unit -v && uv run pytest -m functional -v && uv run pytest -m integration -v

# Frontend
cd frontend && npm run lint && npm run typecheck && npm test
```

**Performance (`tech.md`)**
- API p95 < 200ms; DB queries p95 < 50ms. The 528-row dataset already returns sub-second; the new joins must not regress this (use a single grouped subquery / EXISTS, not N+1).

**Security (`code-standards.md`, `spec-quality-gates.md`)**
- The endpoint is admin/manager-only via existing auth. No new auth surface introduced by this plan. Confirm the route stays under the same dependency that protects the rest of `/schedule/*`.
- Do not log customer names, phone numbers, addresses, or tag labels (tag labels can be PII-adjacent). Log only counts and UUIDs.

**Data migration safety (`spec-quality-gates.md` cross-feature integration)**
- Migrations must preserve backward compatibility. The hygiene migration only mutates rows with malformed `city`; rows already correct are untouched. Idempotent.

### Patterns to Follow

**Endpoint logging (mirror `get_jobs_ready_to_schedule`):**
```python
endpoints.log_started("get_jobs_ready", date_from=..., date_to=...)
try:
    ...
except Exception as e:
    endpoints.log_failed("get_jobs_ready", error=e)
    raise HTTPException(...) from e
else:
    endpoints.log_completed("get_jobs_ready", total_count=...)
    return response
```
This is the project-wide endpoints contract — keep it.

**Pydantic schema additions** — follow `Optional` fields with `Field(default=None, description=...)`, mirroring how other schemas in `schedule_explanation.py` are typed. **Critical:** on the wire we want the frontend's exact field names: `priority_level: int`, `requested_week: str | None` (ISO date as string, NOT a `date` object — frontend does `new Date(iso)`).

**Frontend pure helpers** — co-located unit tests, default-export helpers, no React imports. Mirror `frontend/src/features/schedule/types/pick-jobs.ts::computeJobTimes` pattern: pure functions with vitest tests.

**Migration file naming** — `YYYYMMDD_HHMMSS_short_snake_summary.py`, with the inner `revision` constant equal to the timestamp prefix and `down_revision` equal to the previous head.

**Naming conventions:**
- Python: `snake_case` for fields/functions, `PascalCase` for classes.
- TypeScript: `camelCase` for functions/vars, `PascalCase` for types/components. Test files mirror the module name with `.test.ts(x)` suffix.

**Error handling on the endpoint:** existing handler wraps all DB work in `try/except` and re-raises as `HTTPException(500)`. Keep that.

**Anti-patterns to avoid:**
- Do **not** add `_UNKNOWN_CITY` rows to the City facet — drop them or render in a separate "Uncategorized" affordance.
- Do **not** mutate `properties.city` in the SQL migration without a downgrade path — store the pre-normalized value in a transient `city_raw_backup` column or include it in migration logs so a rollback is possible.
- Do **not** introduce a new TypeScript field; the schema already has everything we need.

---

## IMPLEMENTATION PLAN

### Phase 1: Foundation — Schema + Helpers

Decide the on-the-wire contract before touching the handler. Add the missing fields to the Pydantic schema. Add the two pure frontend helpers (city normalization, address-likeness check) and unit-test them in isolation.

### Phase 2: Core Implementation — Endpoint Population

Rewrite the join in `get_jobs_ready_to_schedule` to additionally load: `Customer.tags` (label list, lowercased) and any `ServiceAgreement` with `status='active'` for the customer. Populate every new schema field per row, including `effective_priority_level`. Keep the existing `priority: str` field for back-compat (set to label of effective priority).

### Phase 3: Integration — Frontend Defensive Normalization

Wire `normalizeCity` + `isAddressLike` into `FacetRail`'s `groups.city` construction. Sort the deduped list. Update `formatWeekLabel` only if needed (it's already correct). No changes to `PickJobsPage` or `JobTable`.

### Phase 4: Data Hygiene + Tests

Write the Alembic migration to normalize whitespace/case and quarantine address-in-city rows. Tighten `property_service._parse_address` to refuse address-shaped tokens as `city`. Extend backend integration tests and frontend unit tests.

---

## STEP-BY-STEP TASKS

Execute every task in order, top to bottom. Each task is atomic and independently testable.

### Task 1 — UPDATE `src/grins_platform/schemas/schedule_explanation.py`

- **IMPLEMENT**: Extend `JobReadyToSchedule` to include the fields the frontend already expects, plus the new derived field. Final shape:
  ```python
  class JobReadyToSchedule(BaseModel):
      job_id: UUID
      customer_id: UUID
      customer_name: str
      job_type: str
      city: str
      priority: str  # legacy label, keep for back-compat
      estimated_duration_minutes: int
      requires_equipment: list[str] = Field(default_factory=list)
      status: str
      # NEW — extended fields the frontend already declares
      address: str | None = None
      customer_tags: list[str] = Field(default_factory=list)
      property_type: str | None = None  # 'residential' | 'commercial' | None
      property_is_hoa: bool | None = None
      property_is_subscription: bool | None = None  # mirror has_active_agreement
      requested_week: str | None = None  # ISO date string YYYY-MM-DD (Monday)
      notes: str | None = None
      priority_level: int = 0  # base Job.priority_level
      effective_priority_level: int = 0  # derived: max of base / tag / agreement
      has_active_agreement: bool = False
  ```
- **PATTERN**: Mirror `JobsReadyToScheduleResponse` for `Field(default_factory=...)` usage.
- **IMPORTS**: Already present (`BaseModel`, `Field`, `UUID`).
- **GOTCHA**: `requested_week` MUST be a `str | None` not `date | None` — the frontend does `new Date(iso)` and a `date` would serialize as `"2026-04-27"` which works, but typing `str` makes the contract explicit and avoids surprises if Pydantic versions change isoformat behavior.
- **VALIDATE**: `uv run python -c "from grins_platform.schemas import JobReadyToSchedule; print(JobReadyToSchedule.model_json_schema()['properties'].keys())"` should list every new field.

### Task 2 — UPDATE `src/grins_platform/api/v1/schedule.py` `get_jobs_ready_to_schedule`

- **IMPLEMENT**: Extend the SELECT to also fetch the customer's lowercased tag labels and any one active service agreement. Concretely:
  - Add a subquery for `customer_tags` aggregated as `array_agg(lower(label))` grouped by `customer_id`.
  - Add an `EXISTS(SELECT 1 FROM service_agreements WHERE customer_id = c.id AND status = 'active')` boolean.
  - Pull `Job.target_start_date`, `Job.notes`, `Property.address`, `Property.property_type`, `Property.is_hoa`, `Property.is_subscription` (verify the actual column names on `Property` first — read the model).
  - Build each `JobReadyToSchedule` with:
    - `requested_week=job.target_start_date.isoformat() if job.target_start_date else None`
    - `priority_level=job.priority_level`
    - `effective_priority_level=max(job.priority_level, 1 if has_priority_tag else 0, 1 if has_active_agreement else 0)`
    - `has_active_agreement=...`
    - `customer_tags=[t for t in tag_labels]` (already lowercased from the SQL agg).
- **PATTERN**: The existing handler at `api/v1/schedule.py:418-479` is the template — keep its `try/except/else` shape and `endpoints.log_*` calls.
- **IMPORTS**: Add `from sqlalchemy import exists, func, and_, literal` if not already imported. `from grins_platform.models.service_agreement import ServiceAgreement`. `from grins_platform.models.customer_tag import CustomerTag`.
- **CONFIRMED FACTS** (verified against the codebase):
  1. `ServiceAgreement.status == "active"` is the canonical literal — used in `api/v1/jobs.py:194,1064`. No enum class; just `String(30)` with `server_default="pending"`. Filter on `ServiceAgreement.status == "active"`.
  2. `Property.property_type` exists (`String(20)`, default `"residential"`, `models/property.py:103`). `Property.is_hoa` exists (`Boolean`, `models/property.py:111`). **`Property.is_subscription` does NOT exist** — the frontend's `property_is_subscription` field maps to `has_active_agreement` (the customer-level signal). Set `property_is_subscription=has_active_agreement` in the response, OR drop `property_is_subscription` from the schema and rely on `has_active_agreement` alone. Prefer the second: cleaner contract, frontend already uses both.
- **GOTCHA**:
  1. The current handler reads `priority=str(job.priority_level)`. Keep that line (back-compat). Add `priority_level=job.priority_level` and the new derived field as new separate fields.
  2. The 528-job dataset should not become slow — use `selectinload` or a single grouped subquery for tags, not per-row queries.
  3. Compare tag labels case-insensitively: `func.lower(CustomerTag.label) == "priority"`.
- **VALIDATE**:
  ```bash
  uv run pytest src/grins_platform/tests/integration/test_jobs_ready_endpoint.py -v
  curl -s http://localhost:8000/api/v1/schedule/jobs-ready | jq '.jobs[0] | keys'
  ```
  The keys list must contain `priority_level`, `requested_week`, `effective_priority_level`, `customer_tags`, `has_active_agreement`.

### Task 3 — CREATE `frontend/src/features/schedule/utils/city.ts`

- **IMPLEMENT**: Two pure helpers:
  ```ts
  /** Trim, collapse whitespace, title-case. Returns null if value is empty/garbage. */
  export function normalizeCity(raw: string | null | undefined): string | null { ... }
  /** True if the string looks like a street address (digit-prefixed) or contains a state+ZIP token. */
  export function isAddressLike(raw: string): boolean { ... }
  ```
  - `normalizeCity` rules:
    - return `null` for `null`/`undefined`/empty/`'Unknown'` (case-insensitive).
    - strip embedded `, MN 55401` tail (`/,\s*[A-Z]{2}\s+\d{5}(-\d{4})?$/`) before title-casing.
    - if `isAddressLike(raw)` → return `null`.
    - collapse internal whitespace, then title-case each word.
  - `isAddressLike` rules:
    - `/^\d/.test(trimmed)` (starts with digit) → true.
    - `/\b[A-Z]{2}\s+\d{5}\b/.test(raw)` (state+ZIP) → true.
    - Contains a street suffix as its own token (`Street|St|Ave|Avenue|Dr|Drive|Ln|Lane|Rd|Road|Blvd|Ct|Court|Way|Ter|Pl|Place|Pkwy|Cir|Circle|Trl|Trail`) → true.
- **PATTERN**: Mirror the pure-function-with-tests style in `types/pick-jobs.ts` (`computeJobTimes`, `timeToMinutes`).
- **IMPORTS**: none (pure TypeScript, no React).
- **GOTCHA**: Title-casing must NOT lower-case proper-noun words like "St. Paul" — leave words containing `.` alone, and re-introduce the period if you split on whitespace. Simpler rule: use `replace(/\w\S*/g, w => w[0].toUpperCase() + w.slice(1).toLowerCase())` and accept that "St. Paul" becomes "St. Paul" (period acts as non-word boundary).
- **VALIDATE**: Task 4's tests cover this.

### Task 4 — CREATE `frontend/src/features/schedule/utils/city.test.ts`

- **IMPLEMENT**: Vitest unit tests covering:
  - `'Eden Prairie'`, `'eden prairie'`, `' EDEN PRAIRIE  '` all normalize to `'Eden Prairie'`.
  - `'11071 Jackson Drive'`, `'5808 View Ln Edina 55436'`, `'Andover, MN 55304'`, `'4355 Vinewood Ln Plymouth, MN 55442'` all return `null`.
  - `'Unknown'`, `''`, `null`, `undefined` all return `null`.
  - `'St. Paul'` → `'St. Paul'` (preserve punctuation).
  - `isAddressLike` independently verified for each of the address-shaped strings.
- **PATTERN**: `describe`/`it` with `expect(...).toBe(...)`, the same as the existing `pick-jobs.test.ts` next door.
- **IMPORTS**: `import { describe, it, expect } from 'vitest'`; relative `./city`.
- **VALIDATE**: `cd frontend && npx vitest run src/features/schedule/utils/city.test.ts`

### Task 5 — UPDATE `frontend/src/features/schedule/components/FacetRail.tsx`

- **IMPLEMENT**: Replace the current city aggregation in the `useMemo` at lines 79–99:
  ```ts
  const groups = useMemo(() => {
    const cityMap = new Map<string, string>(); // raw → canonical
    const cities = new Set<string>();
    ...
    for (const j of jobs) {
      const canon = normalizeCity(j.city);
      if (canon) {
        cities.add(canon);
        cityMap.set(j.city, canon);  // remember the mapping so toggle still works
      }
      ...
    }
    return { city: [...cities].sort(), ... };
  }, [jobs]);
  ```
  Critical follow-on: `matches()` and `matchesValue()` (lines 187–209) currently compare `f.city.has(job.city)` — now compare against the canonical form: `f.city.has(normalizeCity(job.city) ?? '')`. Same in `PickJobsPage.tsx:120` filter.
- **PATTERN**: existing `useMemo` shape. Keep the relaxed-count logic intact.
- **IMPORTS**: `import { normalizeCity } from '../utils/city';`.
- **GOTCHA**: When the user clicks "Eden Prairie" in the rail, you must filter jobs whose **normalized** city equals "Eden Prairie", not whose raw city equals it. Otherwise the dirty rows (e.g. "eden prairie") will be excluded from the result even though their facet was clicked.
- **VALIDATE**:
  - `cd frontend && npm run typecheck`
  - `cd frontend && npx vitest run src/features/schedule/components/FacetRail.test.tsx`
  - Manual: load the page in dev, confirm the rail no longer lists addresses and "Eden Prairie" appears once.

### Task 6 — UPDATE `frontend/src/features/schedule/pages/PickJobsPage.tsx`

- **IMPLEMENT**: Update the city-filter line in the `filteredJobs` `useMemo` (line 120) to compare canonical forms:
  ```ts
  if (facets.city.size && !facets.city.has(normalizeCity(job.city) ?? '')) return false;
  ```
  No other behavioral change.
- **PATTERN**: keep the rest of `filteredJobs` untouched.
- **IMPORTS**: `import { normalizeCity } from '../utils/city';`.
- **VALIDATE**: `cd frontend && npx vitest run src/features/schedule/pages/PickJobsPage.test.tsx`

### Task 7 — CREATE `src/grins_platform/migrations/versions/20260501_120000_normalize_property_city.py`

- **IMPLEMENT**: Alembic migration that:
  1. Trims and collapses whitespace on `properties.city`.
  2. Strips a trailing `, ST 12345[-1234]` token from `properties.city` (regex via `regexp_replace`).
  3. Title-cases the result.
  4. For rows where `city` still starts with a digit OR contains a known street-suffix token, copies the value into `properties.address` (only if `address` is empty), and sets `city = 'Unknown'`.
  5. Logs counts of mutations using `op.get_bind().exec_driver_sql(...)`.
- **PATTERN**: Mirror `20260429_100100_seed_day_2_reminder_settings.py` for the `op.execute(text(...))` shape, and `20260428_100000_add_customer_email_bounced_at.py` for the file scaffolding (revision header).
- **IMPORTS**: `from alembic import op`, `import sqlalchemy as sa`, `from sqlalchemy import text`.
- **GOTCHA**:
  - `down_revision = "20260430_120000"` — verify against `alembic history` output before running.
  - Postgres regex: use `~*` for case-insensitive match. Example street-suffix detector:
    `city ~* '\\m(St|Ave|Dr|Drive|Lane|Ln|Road|Rd|Blvd|Ct|Way|Ter|Pl|Pkwy|Cir|Trl)\\M'`
  - Migration must be idempotent — running twice should leave the data unchanged after the first pass.
  - `downgrade()` cannot perfectly restore the original messy data; document this in the file's docstring and have `downgrade()` raise `NotImplementedError` (project precedent in older data-only migrations — confirm convention by reading `20260429_100100`).
- **VALIDATE**:
  ```bash
  uv run alembic upgrade head
  uv run alembic current  # → 20260501_120000
  # Spot check
  uv run python -c "from grins_platform.database import sync_session_factory; from grins_platform.models import Property; s=sync_session_factory(); print(sum(1 for p in s.query(Property).all() if p.city and p.city[0].isdigit()))"
  # → expected 0
  ```

### Task 8 — UPDATE `src/grins_platform/services/property_service.py::_parse_address`

- **IMPLEMENT**: After computing `city` (line 450) and after the existing state+zip fallback (lines 458–461), add an additional guard:
  ```python
  if city and (city[0].isdigit() or _STREET_SUFFIX_PATTERN.search(city.upper())):
      city = _UNKNOWN_CITY
  ```
  Define `_STREET_SUFFIX_PATTERN = _re.compile(r"\b(ST|AVE|DR|DRIVE|LANE|LN|ROAD|RD|BLVD|CT|WAY|TER|PL|PKWY|CIR|TRL)\b")` near the other module-level regexes.
- **PATTERN**: Match the existing `_re.compile(...)` style at the top of the module.
- **GOTCHA**: Keep the Minneapolis "Saint Paul" case working — title-case "St. Paul" matches `\bST\b` if punctuation strips. Test with `"123 Main St, St. Paul, MN 55101"` → city should stay `"St. Paul"`. Solution: match a `\bST\b` only if it's the **last** non-whitespace token of the candidate city string, not any token. Adjust regex accordingly:
  `_STREET_SUFFIX_PATTERN = _re.compile(r"\b(ST|AVE|DR|DRIVE|LANE|LN|ROAD|RD|BLVD|CT|WAY|TER|PL|PKWY|CIR|TRL)\s*$")`.
- **VALIDATE**: Task 9's tests cover this.

### Task 9 — CREATE `src/grins_platform/tests/unit/test_property_city_validation.py`

- **IMPLEMENT**: Pytest unit tests for `_parse_address` covering:
  - `"1234 Main St, Eden Prairie, MN 55344"` → city `"Eden Prairie"`.
  - `"1234 Main St, St. Paul, MN 55101"` → city `"St. Paul"` (NOT "Unknown").
  - `"5808 View Ln Edina 55436"` (no commas) → city `_UNKNOWN_CITY`.
  - `"Andover, MN 55304"` → city `_UNKNOWN_CITY` (covered by existing rule).
  - `"123 Plymouth Way"` → city `_UNKNOWN_CITY`.
- **PATTERN**: existing tests in `src/grins_platform/tests/unit/` use plain `pytest` functions; mirror their style.
- **IMPORTS**: `from grins_platform.services.property_service import _parse_address, _UNKNOWN_CITY`.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_property_city_validation.py -v`

### Task 10 — UPDATE `src/grins_platform/tests/integration/test_jobs_ready_endpoint.py`

- **IMPLEMENT**: Add a new test `test_jobs_ready_returns_extended_fields` that:
  - Creates a customer with a "priority" `CustomerTag`.
  - Creates an active `ServiceAgreement` for them.
  - Creates a `Job` with `target_start_date='2026-04-27'`, `priority_level=0`, status `approved`, no scheduled appointment.
  - Calls `/api/v1/schedule/jobs-ready`.
  - Asserts the returned job has `priority_level == 0`, `effective_priority_level >= 1`, `requested_week == "2026-04-27"`, `customer_tags` includes `"priority"`, `has_active_agreement is True`.
- **PATTERN**: existing fixtures in this test module.
- **IMPORTS**: model classes from `grins_platform.models`.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/integration/test_jobs_ready_endpoint.py::TestJobsReadyToScheduleEndpoint::test_jobs_ready_returns_extended_fields -v`

### Task 11 — UPDATE `frontend/src/features/schedule/components/FacetRail.test.tsx`

- **IMPLEMENT**: Add three test cases:
  - Given jobs with cities `['Eden Prairie', 'eden prairie ', 'EDEN PRAIRIE']`, the rail renders `Eden Prairie` exactly once.
  - Given jobs with city `'5808 View Ln Edina 55436'`, that string does NOT appear in the rail at all.
  - Clicking the `Eden Prairie` checkbox filters in jobs whose raw city is `'eden prairie '` (case-insensitive normalization respected).
- **PATTERN**: Existing `FacetRail.test.tsx` cases as the template.
- **VALIDATE**: `cd frontend && npx vitest run src/features/schedule/components/FacetRail.test.tsx`

### Task 12 — CREATE `src/grins_platform/tests/unit/test_effective_priority_property.py`

- **IMPLEMENT**: Hypothesis property-based tests for the `effective_priority_level` derivation, covering the invariants required by `spec-testing-standards.md`:
  - `effective >= base` always.
  - `effective >= 1` whenever `has_priority_tag` OR `has_active_agreement`.
  - `effective == base` when neither flag is true.
  - `effective` is monotone: adding a tag or agreement can only raise (never lower) the result.
- **PATTERN**: Mirror existing Hypothesis tests in `src/grins_platform/tests/unit/test_pbt_*.py` for fixture style. Use `@given(st.integers(min_value=0, max_value=2), st.booleans(), st.booleans())`.
- **IMPORTS**: `from hypothesis import given, strategies as st`. Import the helper extracted in Task 2 (factor the derivation into a pure module-level function `_compute_effective_priority(base: int, has_priority_tag: bool, has_active_agreement: bool) -> int` so it can be unit-tested without DB).
- **MARKER**: `@pytest.mark.unit`.
- **VALIDATE**: `uv run pytest -m unit src/grins_platform/tests/unit/test_effective_priority_property.py -v`

### Task 13 — Manual smoke + acceptance

- **IMPLEMENT**: Start the dev stack, navigate to `/schedule/pick-jobs`, verify visually that:
  - City rail shows only deduplicated, capitalized city names.
  - Each row shows a real `Wk of …` value in the Requested column for jobs that have `target_start_date` set on the Jobs tab.
  - Jobs whose customer has the `priority` tag OR an active service agreement render the amber star in the Priority column.
- **VALIDATE**: visual + tail logs for the endpoint.

---

## TESTING STRATEGY

### Unit Tests

- **Frontend** — `city.test.ts`: pure helpers, no React. Covers normalization & address-likeness rules. Vitest, ≥ 10 cases.
- **Backend** — `test_property_city_validation.py`: `_parse_address` boundary cases.
- **Frontend** — `FacetRail.test.tsx` extension: dedup + raw→canonical filter behavior.

### Integration Tests

- **Backend** — `test_jobs_ready_endpoint.py` new case: full DB round-trip with a fixture that has tags + an active agreement, asserting all new schema fields populate correctly.

### Edge Cases

- City equal to `"Unknown"` (sentinel) — should be hidden from facet rail (the dataset will likely have hundreds after the migration).
- Customer with multiple active agreements — `has_active_agreement` should still be a single boolean (use `EXISTS`).
- Customer with `'Priority'` tag (capital P) vs `'priority'` (lower) — backend SQL must compare on `lower(label)`.
- Job with `target_start_date IS NULL` — `requested_week` should be `null`, frontend renders `—`.
- Job with `priority_level = 2` (urgent) AND no agreement — `effective_priority_level` should still be `2`.
- Empty `jobs` array — facet rail renders nothing, no crashes.

---

## VALIDATION COMMANDS

Execute every command to ensure zero regressions and 100% feature correctness.

### Level 1: Syntax & Style (project quality gate)

```bash
# Backend — must produce zero violations and zero type errors
uv run ruff check --fix src/
uv run ruff format src/
uv run mypy src/
uv run pyright src/

# Frontend — must pass with zero errors
cd frontend && npm run lint
cd frontend && npm run typecheck
```

### Level 2: Unit Tests (`@pytest.mark.unit`, all deps mocked)

```bash
uv run pytest -m unit src/grins_platform/tests/unit/test_property_city_validation.py -v
uv run pytest -m unit src/grins_platform/tests/unit/test_effective_priority_property.py -v
cd frontend && npx vitest run src/features/schedule/utils/city.test.ts
cd frontend && npx vitest run src/features/schedule/components/FacetRail.test.tsx
```

### Level 3: Functional + Integration Tests

```bash
# Functional — real DB
uv run pytest -m functional -v -k "property or city or jobs_ready"

# Integration — full system
uv run pytest -m integration src/grins_platform/tests/integration/test_jobs_ready_endpoint.py -v

# Frontend integration via Vitest
cd frontend && npx vitest run src/features/schedule/pages/PickJobsPage.test.tsx
```

### Level 3b: Coverage targets (`spec-quality-gates.md`)

```bash
uv run pytest --cov=src/grins_platform --cov-report=term-missing
# Required: services 90%+, repositories 90%+
cd frontend && npm run test:coverage
# Required: components 80%+, hooks 85%+, utils 90%+
```

### Level 4: Manual Validation

1. `uv run alembic upgrade head` — apply the city-normalization migration.
2. `uv run uvicorn grins_platform.app:app --reload` (or `make dev` if defined) and `cd frontend && npm run dev`.
3. Open `http://localhost:5173/schedule/pick-jobs`.
4. Verify the City rail contains only city names, deduplicated, in title case. No string starts with a digit.
5. Pick a job whose customer has an active agreement (find one via `/agreements`). The Priority column on its row in the picker should show the amber star.
6. Open the Jobs tab, set a `target_start_date` on a different job using `JobWeekEditor`. Refresh the picker — that job's Requested column should read `Wk of <date>`.
7. Click any city checkbox. The job table should narrow to that city only, including any rows whose raw `city` differs only by case/whitespace.

### Level 5: Additional Validation

```bash
# Verify production-shape DB has been cleaned
uv run python -c "
from grins_platform.database import sync_session_factory
from grins_platform.models.property import Property
s = sync_session_factory()
bad = [p.city for p in s.query(Property).all() if p.city and p.city[0].isdigit()]
print('Address-shaped cities remaining:', len(bad), bad[:5])
"
```

---

## ACCEPTANCE CRITERIA

- [ ] City rail on `/schedule/pick-jobs` shows zero entries that begin with a digit or contain a state+ZIP token.
- [ ] City rail shows each city exactly once (case- and whitespace-insensitive).
- [ ] Clicking a city checkbox correctly filters jobs whose raw `city` is a casing/whitespace variant of the same city.
- [ ] Requested column displays `Wk of <Mon D>` for every job that has `target_start_date` set in the Jobs tab.
- [ ] Priority column shows the amber star for any job whose customer has either an active service agreement OR the system "priority" customer tag, even when `Job.priority_level == 0`.
- [ ] `JobReadyToSchedule` API response includes `priority_level`, `effective_priority_level`, `requested_week`, `customer_tags`, `has_active_agreement`, `address`, `notes`.
- [ ] All validation commands pass with zero errors.
- [ ] No regression on existing `test_jobs_ready_endpoint` tests.
- [ ] Migration is reversible to "no data corruption beyond what already existed" (downgrade is intentional NotImplementedError; document in the docstring).
- [ ] No N+1 queries introduced — endpoint stays under 500ms locally for the 528-job dataset.

---

## COMPLETION CHECKLIST

- [ ] Task 1 — schema extended.
- [ ] Task 2 — endpoint populates new fields, including derived `effective_priority_level`.
- [ ] Task 3 — `city.ts` helpers created.
- [ ] Task 4 — `city.test.ts` passes.
- [ ] Task 5 — `FacetRail` uses canonical city.
- [ ] Task 6 — `PickJobsPage` filter compares canonical city.
- [ ] Task 7 — Alembic migration written and `alembic upgrade head` succeeds.
- [ ] Task 8 — `_parse_address` rejects address-shaped tokens for `city`.
- [ ] Task 9 — backend unit tests pass.
- [ ] Task 10 — backend integration test passes.
- [ ] Task 11 — frontend FacetRail tests pass.
- [ ] Task 12 — Hypothesis property-based test on `_compute_effective_priority` passes.
- [ ] Task 13 — manual smoke confirms all three columns/rails render correctly.
- [ ] Quality gate: `ruff check`, `ruff format`, `mypy`, `pyright` — zero violations / errors (project mandate).
- [ ] Frontend: `eslint`, `tsc --noEmit` — zero errors.
- [ ] Three-tier tests: `pytest -m unit`, `pytest -m functional`, `pytest -m integration` — all green.
- [ ] Coverage: backend services ≥ 90%; frontend components ≥ 80%, hooks ≥ 85%, utils ≥ 90%.
- [ ] Logging: every new code path logs `{domain}.{component}.{action}_{state}` events with no PII.

---

## NOTES

**Why split priority into `priority_level` and `effective_priority_level`?**
Keeping the raw value separate from the derived value lets the Jobs tab keep editing `priority_level` directly without surprising the user, while the picker shows the *display* priority that reflects business reality. If the team later wants to surface "why is this priority elevated?" tooltips, both signals are present in the response.

**Why not constrain `customer_tag.label` with an enum?**
That's a larger refactor — out of scope here. We compare on `lower(label) = 'priority'` which matches the existing free-text convention. If/when the enum lands, this code becomes a one-line cleanup.

**Why title-case "Saint Paul" risk?**
Minneapolis-metro has both `St. Paul` and (rarely) `Saint Paul`. The normalizer is intentionally simple — both will appear as separate facet items and the user can filter both. A future enhancement could maintain a small alias map (`'Saint Paul' → 'St. Paul'`); deferred.

**Why a separate `effective_priority_level` instead of overwriting `priority_level`?**
Overwriting would make `Job.priority_level == 0` invisible to the frontend's existing semantics and could break the Jobs tab's own priority display. Adding a new field is additive and safe.

**Pre-verified facts (no investigation needed during execution):**
- `ServiceAgreement.status == "active"` (literal string, `String(30)`, no enum).
- `Property.property_type` — `String(20)`, default `"residential"`, present at `models/property.py:103`.
- `Property.is_hoa` — `Boolean`, present at `models/property.py:111`.
- `Property.is_subscription` — does **not** exist; populate `property_is_subscription` from `has_active_agreement` instead.
- `Job.target_start_date` — `Date`, nullable, `models/job.py:161`.
- `Job.notes` — `Text`, nullable, `models/job.py:189`.
- `CustomerTag.label` — `String(32)`, free-text, system convention is the literal `"priority"` (compare case-insensitively).
- `_UNKNOWN_CITY = "Unknown"` — `services/property_service.py:414`.
- Latest Alembic head: `20260430_120000_add_sales_entry_nudges_dismiss_columns.py`.

**Confidence**: 10/10 for one-pass implementation success. All cross-cutting unknowns resolved. The remaining risks are mechanical (regex tuning for street suffixes, Postgres `regexp_replace` syntax) and are isolated to single tasks with clear validation commands.
