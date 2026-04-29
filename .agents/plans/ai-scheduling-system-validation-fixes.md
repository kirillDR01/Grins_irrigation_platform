# Feature: AI Scheduling System — Validation Bug-Hunt Fixes (8 Bugs + Cross-Cutting)

The following plan should be complete, but it's important that you validate documentation and codebase patterns and task sanity before you start implementing.

Pay special attention to naming of existing utils, types and models. Import from the right files etc.

## Feature Description

Close out the eight ship-blocking bugs (4 × P0, 3 × P1, 1 × P2) surfaced by the 2026-04-29 audit of the AI Scheduling System (`bughunt/2026-04-29-ai-scheduling-system-validation.md`), plus the three cross-cutting cleanups called out in the same report. The audit confirms that every individual quality gate is green (`ruff`, `mypy`, `pyright`, `pytest -m unit`, `pytest -m functional|integration`, `vitest`, `vite build`) but the AI Scheduling spec is not actually wired up end-to-end:

- Admin schedule grid (`/schedule/generate`) renders **blank** because `AIScheduleView` hard-codes empty arrays into `ScheduleOverviewEnhanced` (Bug 1).
- Resource mobile page (`/schedule/mobile`) ships a TS error masked by the build pipeline (Bug 2).
- `POST /ai-scheduling/evaluate` is a no-op — always returns zeroes regardless of DB state (Bug 3).
- `ChatResponse` schema diverges between Pydantic (4 fields) and TypeScript (7 fields) — multi-turn chat sessions never persist, criteria badges and schedule summaries never render (Bug 4).
- `GET /capacity` was never extended with the 30-criteria fields the spec demands (Bug 5).
- `POST /chat` has no rate-limit despite Req 28.7 (Bug 6).
- View-mode buttons can't drive the parent date selector (Bug 7).
- `/scheduling-alerts/` lists suggestions before critical alerts because the API sorts severity as a raw string descending, where `"suggestion" > "critical"` (Bug 8).
- Cross-cutting: `npm run build` doesn't gate on `tsc`; `evaluate_schedule` uses an `Annotated[..., Depends()] = None` typing hack; `dismiss_alert` accepts any active alert (not just suggestions); activity log overstates completion.

This plan returns the surface from "looks complete" to "actually complete," with end-to-end integration tests, a CI gate that prevents future Bug-2-class regressions, and an updated activity log/devlog entry.

## User Story

As an Admin (and as a Technician on a phone),
I want the AI scheduling pages to render real data, the chat to remember my conversation, and the API to evaluate / forecast / dispatch alerts truthfully,
So that the planned 30-criteria scheduling workflow actually drives daily operations instead of failing silently.

## Problem Statement

Spec drift: between requirements (41), correctness properties (27), the activity log marking 24/24 phases complete, and the actual `dev` branch, the integration seams were never exercised. Tests mock the very child components that hold the wiring; `npm run build` skips `tsc -p tsconfig.app.json --noEmit`; the activity log was updated based on import-only / mock-only / file-existence checks instead of running the wired code. Eight concrete defects shipped under that cover, four of them ship-broken.

## Solution Statement

Fix the eight defects in dependency-aware order (build gate → schema parity → data wiring → endpoint correctness → API ordering → cleanups), add integration tests that exercise each previously-mocked seam (real HTTP through `POST /chat` and `POST /evaluate`, real data through `AIScheduleView`, real props through `ResourceMobileView`), and harden CI so the build can never green-light TS errors again. Update the activity log and DEVLOG so future audits can trust the completion claims.

## Feature Metadata

**Feature Type**: Bug Fix (multi-bug remediation)
**Estimated Complexity**: **High** — 4 P0 / 3 P1 / 1 P2 across full stack, plus CI gate change and shared-state propagation
**Primary Systems Affected**:
- Backend: `api/v1/ai_scheduling.py`, `api/v1/scheduling_alerts.py`, `api/v1/schedule.py`, `services/ai/scheduling/criteria_evaluator.py`, `services/ai/scheduling/chat_service.py`, `schemas/ai_scheduling.py`, `schemas/schedule_generation.py`
- Frontend: `features/schedule/components/AIScheduleView.tsx`, `features/schedule/components/ScheduleOverviewEnhanced.tsx`, `features/resource-mobile/components/ResourceMobileView.tsx`, `features/ai/types/aiScheduling.ts`, `features/ai/hooks/useSchedulingChat.ts`, `features/ai/components/SchedulingChat.tsx`, `frontend/package.json`
- Infrastructure: backend rate-limit reuse (`services/ai/rate_limiter.py`), CI build script

**Dependencies**: None new. All fixes reuse existing primitives already in the repo (`RateLimitService`, `Appointment` ORM, `useResourceSchedule`, `useUtilizationReport`, `aiSchedulingKeys`, `slowapi.Limiter`, etc.).

---

## CONTEXT REFERENCES

### Steering Docs (read these — they define the project conventions every fix must follow)

- `.kiro/steering/tech.md` — Stack, quality gates command bundle, performance targets, three-tier testing matrix.
- `.kiro/steering/code-standards.md` — `LoggerMixin` pattern, `DomainLogger` pattern, three-tier test layout, error-handling chain (`raise X from e`), quality command bundle.
- `.kiro/steering/api-patterns.md` — Endpoint template (set_request_id → log_started → try/except with logging → clear_request_id in `finally`), DI pattern (`Depends(get_service)`), test fixture pattern (`app.dependency_overrides[get_service] = lambda: mock_service`).
- `.kiro/steering/structure.md` — Backend `services/`, `models/`, `schemas/`, `repositories/` layout; frontend VSA `core/` / `shared/` / `features/{f}/` layout. Imports through feature `index.ts` barrels.
- `.kiro/steering/frontend-patterns.md` — TanStack Query key factory, `data-testid` convention (`{feature}-page`, `{feature}-table`, `{feature}-row`, `{action}-{feature}-btn`, `nav-{feature}`, `status-{value}`), import conventions (`@/core/`, `@/shared/`, `@/features/{name}`).
- `.kiro/steering/frontend-testing.md` — Vitest + RTL, co-located tests, `QueryProvider` wrapper, coverage targets (Components 80%, Hooks 85%, Utils 90%).
- `.kiro/steering/spec-quality-gates.md` — Mandatory sections every spec needs (logging events, data-testid map, agent-browser scripts, quality-gate commands, fixtures, coverage table, integration tests).
- `.kiro/steering/spec-testing-standards.md` — Three required testing requirements per spec (backend Hypothesis, frontend Vitest, agent-browser E2E).
- `.kiro/steering/agent-browser.md` — agent-browser command reference for E2E validation.
- `.kiro/steering/e2e-testing-skill.md` — End-to-end testing methodology (Phase 1 parallel research, Phase 2 start app, Phase 3 browser flow, Phase 4 DB validation, Phase 6 responsive at 375/768/1440).
- `.kiro/steering/devlog-rules.md` — DEVLOG.md entry format (heading, What/Tech/Decision/Challenges/Next, top-of-file insertion, BUGFIX category).
- `.kiro/steering/auto-devlog.md` — DEVLOG update is mandatory after BUGFIX work.
- `.kiro/steering/parallel-execution.md` — Sequential phases between dependency tiers; parallel within a tier.
- `.kiro/steering/pre-implementation-analysis.md` — Identify parallel groups, subagents, prompts before starting.
- `.kiro/steering/frontend-patterns.md` — `cn()` for conditional classes; status-color records.
- `.kiro/steering/vertical-slice-setup-guide.md` — Cross-feature reads via repository OK; never write across feature boundaries.
- `.kiro/steering/knowledge-management.md` — semantic search reference.

### Source-of-Truth Files — IMPORTANT: READ BEFORE IMPLEMENTING

#### Backend — bug surfaces

- `src/grins_platform/api/v1/ai_scheduling.py` (210 lines)
  - Lines 73–119: `chat` handler — **Bug 6** (no rate limit), **cross-cutting** (passes `request.session_id` to `service.chat`, but never returns the resolved session id back to client because `ChatResponse` lacks `session_id`).
  - Lines 122–162: `evaluate_schedule` handler — **Bug 3** (creates empty `ScheduleSolution` and trusts a comment that lies). Uses `Annotated[..., Depends()] = None` hack — **cross-cutting**.
  - Lines 22–39: imports map (`ChatRequest`, `ChatResponse`, `CriterionResult`, `ScheduleEvaluation`, `SchedulingConfig`, `SchedulingContext`).
- `src/grins_platform/api/v1/scheduling_alerts.py` (440 lines)
  - Lines 75–104: `_alert_to_response`, `_cr_to_response` helpers — pattern to mirror.
  - Lines 164–168: `list_alerts` severity sort — **Bug 8** (string desc puts `"suggestion"` before `"critical"`).
  - Lines 249–292: `dismiss_alert` — **cross-cutting** (no severity guard).
- `src/grins_platform/services/ai/scheduling/criteria_evaluator.py` (713 lines)
  - Lines 293–372: `evaluate_schedule(solution, context)` — **Bug 3 layer 2** (iterates `solution.assignments` which is always `[]` from the API).
  - `evaluate_assignment` accepts `(job, staff, context)`; reuse for the new DB-load path.
  - `_aggregate_criterion_averages()` (lines 666–697) — produces the per-criterion result list used by the new capacity fields (Bug 5).
- `src/grins_platform/services/ai/scheduling/chat_service.py` (857 lines)
  - Lines ~595–655: `_handle_admin_message` — returns `ChatResponse(response=..., schedule_changes=..., clarifying_questions=...)` only. **Bug 4** mitigation lives here: must populate `session_id`, `criteria_used`, `schedule_summary`.
  - Lines ~657–716: `_handle_resource_message` — same pattern; must populate `session_id`.
  - `session_obj.id` is already known internally — emit it.
- `src/grins_platform/services/schedule_domain.py` (175 lines)
  - Lines ~10–70: `ScheduleLocation`, `ScheduleJob`, `ScheduleStaff` dataclasses.
  - Lines ~95–115: `ScheduleAssignment` (id, staff, jobs).
  - Lines ~120–140: `ScheduleSolution(schedule_date, jobs, staff, assignments, hard_score, soft_score)` — needs an adapter from `Appointment` rows.
- `src/grins_platform/schemas/ai_scheduling.py` (727 lines)
  - Lines 185–199: `ChatRequest` (message, session_id).
  - Lines 202–227: `ChatResponse` — **Bug 4 backend half**: missing `session_id`, `criteria_used`, `schedule_summary`.
  - Lines 152–182: `ScheduleChange`.
  - Lines 91–119: `ScheduleEvaluation`.
  - Lines 650–679: `CapacityForecast` (already has `criteria_analysis`, `forecast_confidence`) — **dead code** today; relevant to Bug 5.
  - Lines 28–67: `CriterionResult` — re-use as the shape for the chat `criteria_used`.
- `src/grins_platform/api/v1/schedule.py` (lines 187–215)
  - `get_capacity` handler — **Bug 5** (never extended). Uses `ScheduleCapacityResponse`.
- `src/grins_platform/schemas/schedule_generation.py` (lines 77–86)
  - `ScheduleCapacityResponse` — extend additively (per spec contract: do **not** rename / remove existing keys).
- `src/grins_platform/services/ai/rate_limiter.py` (136 lines)
  - `RateLimitService.check_limit(user_id) → bool`, `record_usage(user_id, …)` — already used by `api/v1/ai.py:77–94`.
  - `RateLimitError` raised; pattern: catch in handler and convert to HTTP 429.
- `src/grins_platform/api/v1/ai.py` (lines 38, 77–94) — **reference pattern** for catching `RateLimitError` and re-raising as `HTTPException(429)`.
- `src/grins_platform/middleware/rate_limit.py` (122 lines)
  - `slowapi` `Limiter` with Redis storage; constants `AUTHENTICATED_LIMIT = "200/minute"`, `AUTH_LIMIT = "5/minute"`, etc. (alternative to `RateLimitService` if a per-IP middleware-level limit is preferred).
- `src/grins_platform/api/v1/dependencies.py` — DI pattern reference.
- `src/grins_platform/models/scheduling_alert.py` (155 lines) — `SchedulingAlert.severity` is `String(20)` with values `'critical'` / `'suggestion'`; `status` is `'active' | 'resolved' | 'dismissed' | 'expired'`.
- `src/grins_platform/models/appointment.py` — `Appointment` columns: `id`, `job_id`, `staff_id`, `scheduled_date`, `time_window_start`, `time_window_end`, `status`, `route_order`, `estimated_arrival`. Use these to build `ScheduleAssignment`s for Bug 3.

#### Backend — test files to extend

- `src/grins_platform/tests/integration/test_ai_scheduling_integration.py` — add (a) a `POST /evaluate` test that seeds a job + appointment with a violated hard constraint (e.g. `compliance_deadline` in the past for criterion 21), (b) a multi-turn chat test that sends two messages and asserts `session_id` round-trips and only one `SchedulingChatSession` row is created, (c) an alert-ordering test, (d) an extended `/capacity` test asserting new optional fields.
- `src/grins_platform/tests/integration/test_business_component_wiring.py` — pattern for cross-component wiring tests (this is where the alert ordering + chat session continuity should also be asserted at the wiring level).
- `src/grins_platform/tests/functional/test_ai_scheduling_functional.py` — add functional flow: admin posts to `/chat` twice → second response has the same `session_id` → `scheduling_chat_sessions` table has exactly one row for that user.
- `src/grins_platform/tests/unit/test_ai_scheduling_services.py` — add unit test that the chat service emits `session_id` on the response shape.
- `src/grins_platform/tests/unit/test_ai_scheduling.py` — add unit test for the new `_appointment_to_schedule_assignment` helper (or whichever name is chosen) used in Bug 3.
- `src/grins_platform/tests/unit/test_pbt_ai_scheduling.py` and `test_pbt_ai_scheduling_p12_22.py` — add a Hypothesis property: for any `severity ∈ {'critical', 'suggestion'}` mix in any order, the API response orders all `'critical'` rows before all `'suggestion'` rows (ties broken by `created_at` desc).

#### Frontend — bug surfaces

- `frontend/src/features/schedule/components/AIScheduleView.tsx` (76 lines)
  - **Bug 1**: hard-codes `resources={[]}`, `days={[]}`, `capacityDays={[]}`. Must call `useUtilizationReport` (or `useDailySchedule` / `useWeeklySchedule`) and map response to the three shapes `ScheduleOverviewEnhanced` expects.
  - **Bug 7**: `handleViewModeChange(mode, date?)` declares an unused `date` parameter the child never sends.
- `frontend/src/features/schedule/components/AIScheduleView.test.tsx` — **must be updated**: today it mocks `ScheduleOverviewEnhanced` and only asserts presence; new asserts must verify a real resource row renders and that view-mode change with date propagates `setScheduleDate`.
- `frontend/src/features/schedule/components/ScheduleOverviewEnhanced.tsx` (~250 lines)
  - Lines 41–49: `ScheduleOverviewEnhancedProps` (callback signature already accepts `date?` — child just never sends it).
  - Lines 122–125: `handleViewMode(mode)` → `onViewModeChange?.(mode)` — **Bug 7**, sender never emits `date`.
  - Lines 136–149: button onClick wiring — emit a real date from a date picker / nav arrow OR update the prop signature to drop `date`.
- `frontend/src/features/schedule/hooks/useAIScheduling.ts` (184 lines)
  - `aiSchedulingKeys` factory; `useCapacityForecast`, `useUtilizationReport`, `useEvaluateSchedule`, `useCriteriaConfig`, `useBatchGenerate` — already orphaned; wire these from `AIScheduleView`.
- `frontend/src/features/resource-mobile/components/ResourceMobileView.tsx` — **Bug 2**: renders `<ResourceScheduleView />` with **no props**; must call `useResourceSchedule()` and pass `schedule={data}` after handling loading + error states.
- `frontend/src/features/resource-mobile/components/ResourceScheduleView.tsx` — `interface Props { schedule: ResourceSchedule }` (required).
- `frontend/src/features/resource-mobile/components/ResourceMobileView.test.tsx` — currently mocks `ResourceScheduleView`; replace with a hook mock so the real component instantiates and asserts at least one `route_order` cell renders.
- `frontend/src/features/resource-mobile/hooks/useResourceSchedule.ts` — already exported; wire into the view.
- `frontend/src/features/scheduling-alerts/components/AlertsPanel.tsx` — already client-side filters by severity; do **not** change the UI; document the contract once Bug 8 is fixed (the client filter becomes redundant but harmless).
- `frontend/src/features/ai/types/aiScheduling.ts` (lines 30–50)
  - **Bug 4 frontend half**: TS `ChatResponse` declares `session_id`, `criteria_used`, `schedule_summary` that the backend currently doesn't return. Pick path A (extend backend) so this file becomes truthful, or path B (delete the orphan fields). Plan goes with **path A** (matches spec text).
- `frontend/src/features/ai/hooks/useSchedulingChat.ts` (line 41)
  - `setSessionId(data.session_id)` — currently always `undefined`. Will work after path A.
- `frontend/src/features/ai/components/SchedulingChat.tsx` (lines 28–113)
  - Renders `criteriaUsed` badges and `scheduleSummary` block conditionally — neither field is currently populated; both will activate once path A is in.
- `frontend/src/features/ai/components/SchedulingChat.test.tsx` — currently feeds shape-matching mocks; add an integration-level test (against a `MSW`-mocked or real fetch) so this kind of contract drift can't recur.
- `frontend/package.json` — `"build": "vite build"` — change to `"build": "tsc -b && vite build"` **OR** add a `"typecheck"` script and gate CI on it (cross-cutting fix).

#### Frontend — test files to extend

- `frontend/src/features/schedule/components/AIScheduleView.test.tsx` — assert at least one `[data-testid^="resource-row-"]` renders given mocked hook data.
- `frontend/src/features/resource-mobile/components/ResourceMobileView.test.tsx` — replace `vi.mock('./ResourceScheduleView')` with a `vi.mock` of the `useResourceSchedule` hook; render the real `ResourceScheduleView`; assert `route_order` cell.
- `frontend/src/features/ai/components/SchedulingChat.test.tsx` — when `useSchedulingChat` returns a response with `criteriaUsed: [{ number: 1, name: 'Proximity' }]`, assert the badge renders.
- `frontend/src/features/ai/hooks/useSchedulingChat.test.tsx` (new file) — assert that on second `mutate` call after a successful first call, the `session_id` from the first response is included in the second request body.

#### Spec / Activity files to update

- `.kiro/specs/ai-scheduling-system/activity.md` — append a new top entry describing the audit findings, the fixes landed, the new tests, and the CI gate. Re-mark tasks 7.1, 7.3, 8, 11.1, 13A as **`[!]` audited & remediated** (not just `[x]`) so the bookkeeping matches reality.
- `.kiro/specs/ai-scheduling-system/tasks.md` — same `[!]` annotation on the affected sub-tasks.
- `DEVLOG.md` — add a top entry under `## Recent Activity` per `.kiro/steering/devlog-rules.md`: `## [2026-04-29 HH:MM] - BUGFIX: AI scheduling spec validation — 8 bugs closed`.

#### E2E scripts (already exist; extend for new asserts)

- `scripts/e2e/test-ai-scheduling-overview.sh` — after Bug 1 fix, add an assertion for at least one resource row visible.
- `scripts/e2e/test-ai-scheduling-resource.sh` — after Bug 2 fix, add an assertion for at least one route card visible.
- `scripts/e2e/test-ai-scheduling-chat.sh` — after Bug 4 fix, send two messages, assert second uses the same session_id (read browser console for the network request payload, or use `agent-browser eval` to inspect a window-level capture).
- `scripts/e2e/test-ai-scheduling-alerts.sh` — after Bug 8 fix, assert that the first card returned by `GET /scheduling-alerts/?schedule_date=…` (raw `fetch` from the browser console) has `severity === 'critical'` when both kinds exist.

### New Files to Create

- `src/grins_platform/services/ai/scheduling/appointment_loader.py` — small async helper that loads `Appointment` rows for a given `schedule_date` and converts them to `ScheduleAssignment` instances (used by Bug 3 fix and Bug 5 capacity extension). Pure adapter, no business logic.
- `src/grins_platform/tests/unit/test_appointment_loader.py` — unit tests for the new loader (mocked session).
- `frontend/src/features/ai/hooks/useSchedulingChat.test.tsx` — new test asserting session_id round-trip across two messages.
- `frontend/src/features/schedule/components/AIScheduleView.integration.test.tsx` — RTL + MSW (or hook mock) test that mounts the real `ScheduleOverviewEnhanced` and asserts a real resource row.
- (Optional) `frontend/scripts/typecheck.sh` — wraps `tsc -p tsconfig.app.json --noEmit` for CI hookability.

### Relevant Documentation — READ BEFORE IMPLEMENTING

- FastAPI → Dependency injection with `Annotated`: <https://fastapi.tiangolo.com/tutorial/dependencies/#dependencies-with-yield-and-httpexception>
  - Why: clean replacement for the `Annotated[..., Depends()] = None # type: ignore` hack used in `evaluate_schedule`. Switching that route to take a `POST` body removes the parameter-ordering issue and ends the `# type: ignore`.
- FastAPI → Background tasks / 429 handling: <https://fastapi.tiangolo.com/tutorial/handling-errors/>
  - Why: pattern for raising `HTTPException(status_code=429, detail=..., headers={"Retry-After": "60"})` from the chat handler after `RateLimitError`.
- slowapi (already a dep) — limiter usage: <https://slowapi.readthedocs.io/en/latest/#fastapi>
  - Why: alternative to `RateLimitService` for per-IP/per-route limiting on `POST /chat`.
- TanStack Query v5 → mutations + cache invalidation: <https://tanstack.com/query/latest/docs/framework/react/guides/mutations>
  - Why: pattern for the `useSchedulingChat` mutation (already in repo) — extend `onSuccess` to update the local session id from `data.session_id` after Bug 4 fix.
- React Router v7 → lazy routes: <https://reactrouter.com/start/data/route-objects>
  - Why: confirm `/schedule/mobile` and `/schedule/generate` lazy imports continue working after the data-fetching changes.
- Vitest → mocking modules: <https://vitest.dev/api/vi.html#vi-mock>
  - Why: replace `vi.mock('./ResourceScheduleView')` with `vi.mock('../hooks/useResourceSchedule')` to test the real component.
- SQLAlchemy 2.0 (async) → `select(...).order_by(case(...))`: <https://docs.sqlalchemy.org/en/20/core/sqlelement.html#sqlalchemy.sql.expression.case>
  - Why: replacement for the broken `severity.desc()` string sort in `list_alerts`.
- agent-browser (`docs/agent-browser.md` and `.kiro/steering/agent-browser.md`) — already loaded in steering.
- `bughunt/2026-04-29-ai-scheduling-system-validation.md` — the canonical bug spec.

### Patterns to Follow

(Pulled directly from the steering files and existing source. Reuse — don't reinvent.)

#### Backend service pattern (LoggerMixin, from `code-standards.md`)

```python
class SchedulingChatService(LoggerMixin):
    DOMAIN = "scheduling"

    async def chat(self, *, user_id: UUID, role: str, message: str,
                   session_id: UUID | None = None) -> ChatResponse:
        self.log_started("chat", user_id=str(user_id), role=role)
        try:
            response = await self._dispatch(role, message, session_id)
            self.log_completed("chat", user_id=str(user_id))
            return response
        except RateLimitError as e:
            self.log_rejected("chat", reason=str(e))
            raise
        except Exception as e:
            self.log_failed("chat", error=e)
            raise
```

#### API endpoint pattern (from `api-patterns.md` and existing `api/v1/ai.py:77-94`)

```python
@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    current_user: CurrentActiveUser,
    service: Annotated[SchedulingChatService, Depends(get_chat_service)],
    rate_limiter: Annotated[RateLimitService, Depends(get_rate_limit_service)],
) -> ChatResponse:
    request_id = set_request_id()
    DomainLogger.api_event(_log, "chat", "started",
                            request_id=request_id, user_id=str(current_user.id))
    try:
        await rate_limiter.check_limit(current_user.id)        # ← Bug 6 fix
        response = await service.chat(
            user_id=current_user.id,
            role=current_user.role,
            message=request.message,
            session_id=request.session_id,
        )
        await rate_limiter.record_usage(current_user.id, input_tokens=0, output_tokens=0)
        DomainLogger.api_event(_log, "chat", "completed",
                                request_id=request_id, status_code=200)
        return response
    except RateLimitError as e:
        DomainLogger.api_event(_log, "chat", "failed",
                                request_id=request_id, error=str(e), status_code=429)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(e),
            headers={"Retry-After": "60"},
        ) from e
    finally:
        clear_request_id()
```

#### Pydantic schema extension pattern (additive, non-breaking — Bug 4 backend, Bug 5)

```python
# schemas/ai_scheduling.py — extend ChatResponse
class ChatResponse(BaseModel):
    response: str
    schedule_changes: list[ScheduleChange] | None = None
    clarifying_questions: list[str] | None = None
    change_request_id: UUID | None = None
    # NEW (Bug 4):
    session_id: UUID | None = Field(default=None,
        description="Persistent session id for multi-turn conversations")
    criteria_used: list[CriterionUsage] | None = Field(default=None,
        description="Criteria that drove this response (number + name)")
    schedule_summary: str | None = Field(default=None,
        description="Inline schedule summary (e.g. 'Mon: 10 jobs, Tue: 8 jobs')")

class CriterionUsage(BaseModel):
    number: int
    name: str
```

```python
# schemas/schedule_generation.py — extend ScheduleCapacityResponse (Bug 5, additive)
class ScheduleCapacityResponse(BaseModel):
    schedule_date: date
    total_staff: int
    available_staff: int
    total_capacity_minutes: int
    scheduled_minutes: int
    remaining_capacity_minutes: int
    can_accept_more: bool
    # NEW (Bug 5) — every field optional, defaults preserve back-compat:
    criteria_triggered: list[int] | None = None
    forecast_confidence_low: float | None = None
    forecast_confidence_high: float | None = None
    per_criterion_utilization: dict[int, float] | None = None
```

#### SQL ordering pattern (Bug 8)

```python
from sqlalchemy import case
severity_priority = case(
    (SchedulingAlert.severity == "critical", 0),
    (SchedulingAlert.severity == "suggestion", 1),
    else_=2,
)
stmt = (
    select(SchedulingAlert)
    .where(SchedulingAlert.status == "active")
    .order_by(severity_priority, SchedulingAlert.created_at.desc())
)
```

#### Adapter pattern: Appointment → ScheduleAssignment (Bug 3)

```python
# services/ai/scheduling/appointment_loader.py
async def load_assignments_for_date(
    session: AsyncSession, schedule_date: date
) -> list[ScheduleAssignment]:
    stmt = (
        select(Appointment)
        .where(Appointment.scheduled_date == schedule_date)
        .where(Appointment.status != "cancelled")
        .options(selectinload(Appointment.staff), selectinload(Appointment.job))
    )
    appts = (await session.execute(stmt)).scalars().all()
    by_staff: dict[UUID, ScheduleAssignment] = {}
    for appt in appts:
        if appt.staff_id not in by_staff:
            by_staff[appt.staff_id] = ScheduleAssignment(
                id=uuid4(),
                staff=_staff_to_schedule_staff(appt.staff),
                jobs=[],
            )
        by_staff[appt.staff_id].jobs.append(_job_to_schedule_job(appt.job))
    return list(by_staff.values())
```

#### Frontend data-wiring pattern (Bug 1, Bug 2)

```tsx
// AIScheduleView.tsx — pattern lifted from frontend-patterns.md "List" example
export function AIScheduleView() {
  const [scheduleDate, setScheduleDate] = useState<string>(
    () => new Date().toISOString().split('T')[0]
  );
  const utilization = useUtilizationReport({
    start_date: scheduleDate,
    end_date: scheduleDate,  // single-day for now; extend later
  });
  const capacity = useCapacityForecast(scheduleDate);

  const { resources, days, capacityDays } = useMemo(
    () => mapToOverviewShape(utilization.data, capacity.data),
    [utilization.data, capacity.data]
  );

  if (utilization.isLoading || capacity.isLoading) return <LoadingSpinner />;
  if (utilization.error || capacity.error) return <ErrorMessage error={utilization.error ?? capacity.error} />;

  return (
    <div className="grid h-full" style={{ gridTemplateColumns: '1fr 380px' }}
         data-testid="ai-schedule-page">
      <main className="flex flex-col overflow-auto">
        <ScheduleOverviewEnhanced
          weekTitle={`Schedule Overview — Week of ${scheduleDate}`}
          resources={resources}
          days={days}
          capacityDays={capacityDays}
          onViewModeChange={(mode, date) => date && setScheduleDate(date)}
        />
        <AlertsPanel scheduleDate={scheduleDate} />
      </main>
      <ErrorBoundary fallback={<div>Chat unavailable</div>}>
        <SchedulingChat onPublishSchedule={handlePublishSchedule} />
      </ErrorBoundary>
    </div>
  );
}
```

#### data-testid (from `frontend-patterns.md`)

- `ai-schedule-page` (already exists), `resource-row-{staffId}`, `day-col-{ISO_DATE}`, `view-mode-day-btn` / `view-mode-week-btn` / `view-mode-month-btn`, `resource-mobile-page` (exists), `route-card-{routeOrder}`, `chat-message-{n}`, `chat-criteria-badge-{criterionNumber}`, `chat-schedule-summary`, `chat-publish-btn`.

#### Logging events (per `code-standards.md` and `spec-quality-gates.md`)

| Event name | Level | Where | Context fields |
|---|---|---|---|
| `scheduling.chat.rate_limit_rejected` | WARNING | `ai_scheduling.py:chat` | user_id, request_id |
| `scheduling.evaluate.started` | INFO | `ai_scheduling.py:evaluate_schedule` | schedule_date, request_id |
| `scheduling.evaluate.assignments_loaded` | INFO | `appointment_loader.py` | schedule_date, count |
| `scheduling.evaluate.completed` | INFO | `ai_scheduling.py:evaluate_schedule` | schedule_date, hard_violations, total_score |
| `scheduling.alert.list_started` | INFO | `scheduling_alerts.py:list_alerts` | filters, request_id |
| `scheduling.alert.dismiss_rejected` | WARNING | `scheduling_alerts.py:dismiss_alert` | alert_id, severity, reason |
| `scheduling.capacity.criteria_overlay_started` | DEBUG | `schedule.py:get_capacity` | schedule_date |

---

## IMPLEMENTATION PLAN

### Phase 1: Build-gate hardening (cross-cutting, P0 enabler)

Without this, Bug 2's class of error keeps shipping. Do this first so subsequent TS edits surface their own errors immediately.

**Tasks:**

- Switch `frontend/package.json#scripts.build` to `"tsc -p tsconfig.app.json --noEmit && vite build"` so `npm run build` fails on TS errors. (Do **not** use `tsc -b` — `tsconfig.app.json` has `composite: true` and `noEmit: true`, which conflict in build mode.)
- Add a separate `"typecheck"` script (`tsc -p tsconfig.app.json --noEmit`) for CI.
- Append the **exact 29 file paths** to `tsconfig.app.json#exclude` (verified list lives in Task 1). 154 pre-existing errors → 0. Do **not** exclude `ResourceMobileView.tsx` — that's the file Task 12 fixes.
- Document the 30 excluded files in `bughunt/2026-04-29-pre-existing-tsc-errors.md` so the next audit picks them up.
- Files this plan touches must pass `tsc` cleanly before merge: ResourceMobileView, AIScheduleView, ScheduleOverviewEnhanced, SchedulingChat, useSchedulingChat, useResourceSchedule, aiScheduling.ts.

### Phase 2: Schema parity (Bug 4 backend half — unlocks tests for chat)

- Extend `schemas/ai_scheduling.py:ChatResponse` with `session_id: UUID | None`, `criteria_used: list[CriterionUsage] | None`, `schedule_summary: str | None`. Add `CriterionUsage` mini-class.
- Update `chat_service._handle_admin_message` and `_handle_resource_message` to populate all three new fields:
  - `session_id` ← `session_obj.id` (always present internally).
  - `criteria_used` ← list of `CriterionUsage(number, name)` derived from `_aggregate_criterion_averages()` filtered to those that drove the routing decision (mock with the top-3 by absolute weight if no decision was driven).
  - `schedule_summary` ← computed via a small renderer that reads `solution.assignments` (when available) or returns `None`.
- Backend tests: extend `tests/unit/test_ai_scheduling_services.py` to assert all three fields are present and non-`None` on a happy-path admin message; assert `session_id` round-trips when `request.session_id` is provided.

### Phase 3: Endpoint correctness (Bug 3, Bug 6 — unlocks Bug 5)

- **Bug 3** — Create `services/ai/scheduling/appointment_loader.py` with `load_assignments_for_date(session, schedule_date) → list[ScheduleAssignment]`. Add unit test (mocked session) and integration test (seeded DB).
- Update `api/v1/ai_scheduling.py:evaluate_schedule` to convert from query param to a `EvaluateRequest` body model (cleans the `Annotated[..., Depends()] = None` hack — cross-cutting fix), call `load_assignments_for_date`, build `ScheduleSolution(schedule_date=…, assignments=loaded)`, then pass to `evaluator.evaluate_schedule`.
- Frontend `useEvaluateSchedule` hook: change request method/body shape to match. The hook is currently orphaned — confirm the change is invisible to other callers.
- **Bug 6** — Wire `RateLimitService` (already used by `api/v1/ai.py`). Add `get_rate_limit_service` to `api/v1/dependencies.py`. In `chat` handler, call `await rate_limiter.check_limit(user_id)` before dispatch, catch `RateLimitError`, raise `HTTPException(429)` with `Retry-After`. Record usage on success.
- Add a `tests/integration/test_ai_scheduling_integration.py::test_chat_rate_limited_after_burst` that fires 31 calls and asserts the 31st is 429 (limit constant `DAILY_REQUEST_LIMIT = 100`; for the test, monkeypatch to a low number so it runs fast).

### Phase 4: Capacity extension (Bug 5 — depends on Phase 3 evaluator)

- Extend `schemas/schedule_generation.py:ScheduleCapacityResponse` additively (see pattern above). Do **not** change existing fields. Confirm with the existing test suite (`tests/unit/test_schedule_generation_service.py` if present) that the existing behavior is unchanged.
- Update `api/v1/schedule.py:get_capacity` to: after computing the basic capacity, instantiate `CriteriaEvaluator`, run `evaluator.evaluate_schedule(load_assignments_for_date(...))`, harvest `criteria_triggered` (list of criterion numbers with `is_hard and not is_satisfied` averaged across assignments), `forecast_confidence_low/high` (mean ± std-dev of `total_score` across the day's assignments), and `per_criterion_utilization` (dict[int, float] from `_aggregate_criterion_averages`).
- Or alternatively: switch `get_capacity` to return the existing `CapacityForecast` schema (which already has `criteria_analysis` and `forecast_confidence`) and remove the dead-code `CapacityForecast` class. **Pick this only if no existing consumer reads the original keys.** Audit consumers first via repo-wide grep.
- Add an integration test that seeds a job + appointment with a hard-constraint violation and asserts `criteria_triggered` includes the violated criterion number.

### Phase 5: API ordering + dismiss guard (Bug 8 + cross-cutting)

- Replace the `severity.desc()` sort in `scheduling_alerts.py:list_alerts` with a `case`-based priority (see pattern above). Adjust the comment to match.
- In `dismiss_alert`, after the existing `alert.status != "active"` guard, add: if `alert.severity != "suggestion"`, raise `HTTPException(400, "Only suggestions can be dismissed; resolve critical alerts via /resolve.")`.
- Tests: integration tests for both — alert ordering + dismiss-guard rejecting a `critical` severity alert with 400.

### Phase 6: Frontend data wiring (Bug 1, Bug 2 — depend on Phases 1, 4)

- **Bug 1** — Update `AIScheduleView.tsx`:
  - Import `useUtilizationReport`, `useCapacityForecast` from `../hooks/useAIScheduling`.
  - Add a small adapter function `mapToOverviewShape(utilization, capacity)` that returns `{ resources, days, capacityDays }` shaped for `ScheduleOverviewEnhanced`. Place inline inside the component file (no `shared/` until the adapter is reused 3+ times — see vertical-slice-setup-guide.md).
  - Loading + error states with `<LoadingSpinner />` and `<ErrorMessage />` from `@/shared/components`.
  - Wrap the main pane in the `ErrorBoundary` (currently only wrapping the chat).
  - Add `data-testid="resource-row-{staffId}"` on each row in `ScheduleOverviewEnhanced`.
- **Bug 2** — Update `ResourceMobileView.tsx`:
  - Call `useResourceSchedule()`; render loading / error states; pass `<ResourceScheduleView schedule={data} />` only when data is ready.
  - Wrap in `<ErrorBoundary fallback={<div>Schedule unavailable</div>}>`.
- **Bug 7** — Decide between (a) drop `date` from `ScheduleOverviewEnhanced.onViewModeChange` signature (smaller change, accepts that view-mode is display-only), or (b) add a real date picker / arrow nav that emits a date. Go with **(b)** because the spec mock-up shows arrows next to the title; implement minimal `<button>← →</button>` controls in `ScheduleOverviewEnhanced` that emit `onViewModeChange(viewMode, newDateISO)`.
- **Bug 4 frontend half** — `aiScheduling.ts`: now that the backend returns the three fields, the existing TS type is finally accurate. No edit needed beyond verifying the types match the new Pydantic schema (or, ideally, regenerate from OpenAPI).
- Update tests (`AIScheduleView.test.tsx`, `ResourceMobileView.test.tsx`, `SchedulingChat.test.tsx`, plus new `useSchedulingChat.test.tsx`) per the test-file inventory above.

### Phase 7: Test coverage + activity log + DEVLOG

- Backend: add three new property-based tests (Hypothesis):
  1. Alert ordering: for any mix of severities, critical rows come first.
  2. Chat session continuity: any number of `chat` calls with the same `session_id` produce exactly one row.
  3. Capacity extension: `criteria_triggered` is a subset of `range(1, 31)`.
- Frontend: extend the four test files (above) and add the new `useSchedulingChat.test.tsx`.
- E2E: extend the four scripts (above) per their notes.
- Update `.kiro/specs/ai-scheduling-system/activity.md` (top entry; mark previously-overstated tasks as `[!]` audited & remediated; cite the bughunt file).
- Update `.kiro/specs/ai-scheduling-system/tasks.md` — same `[!]` annotations on 7.1, 7.3, 8, 11.1, 13A.
- Update `DEVLOG.md` — top entry under `## Recent Activity` with `BUGFIX` category. Use the format from `.kiro/steering/devlog-rules.md`.

### Phase 8: Quality gates + agent-browser validation

- Run the full backend bundle: `uv run ruff check --fix src/ && uv run ruff format src/ && uv run mypy src/ && uv run pyright src/ && uv run pytest -v`.
- Run the full frontend bundle: `cd frontend && npm run lint && npm run typecheck && npm test && npm run build`.
- Run the five updated E2E scripts: `for s in scripts/e2e/test-ai-scheduling-{overview,alerts,chat,resource,responsive}.sh; do bash "$s"; done`.
- Manual agent-browser validation per `.kiro/steering/e2e-testing-skill.md` Phase 6 (responsive at 375 / 768 / 1440).

---

## STEP-BY-STEP TASKS

Execute every task in order. Each is atomic and independently testable.

### 1. UPDATE `frontend/package.json` + `frontend/tsconfig.app.json` — add `tsc` to build pipeline (cross-cutting, P0 enabler)

- **IMPLEMENT**:
  - In `frontend/package.json`: change `"build": "vite build"` to `"build": "tsc -p tsconfig.app.json --noEmit && vite build"`. Add `"typecheck": "tsc -p tsconfig.app.json --noEmit"`. **Do NOT use `tsc -b`** — `tsconfig.app.json` has `composite: true` and `noEmit: true` which conflict in build mode; use the `-p ... --noEmit` form instead.
  - In `frontend/tsconfig.app.json`, append the **exact list of 29 pre-existing-error files** to the `"exclude"` array (verified by running `cd frontend && npx tsc -p tsconfig.app.json --noEmit` on `dev` HEAD on 2026-04-29 — 154 errors total). Files to add to `exclude`:
    ```json
    "src/features/accounting/components/ReceiptCapture.tsx",
    "src/features/accounting/components/SpendingChart.tsx",
    "src/features/agreements/components/MrrChart.tsx",
    "src/features/agreements/index.ts",
    "src/features/ai/components/MorningBriefing.tsx",
    "src/features/communications/components/CampaignResponsesView.tsx",
    "src/features/customers/components/CustomerForm.tsx",
    "src/features/customers/components/InvoiceHistory.tsx",
    "src/features/customers/components/MergeComparisonModal.tsx",
    "src/features/invoices/components/CreateInvoiceDialog.tsx",
    "src/features/jobs/components/JobWeekEditor.tsx",
    "src/features/jobs/components/PaymentSection.tsx",
    "src/features/jobs/index.ts",
    "src/features/leads/components/AttachmentPanel.tsx",
    "src/features/leads/components/LeadDetail.tsx",
    "src/features/leads/components/SheetsSync.tsx",
    "src/features/marketing/components/CACChart.tsx",
    "src/features/sales/components/SalesCalendar.tsx",
    "src/features/sales/components/SalesDashboard.tsx",
    "src/features/schedule/components/AppointmentForm.tsx",
    "src/features/schedule/components/AppointmentModal/PhotosPanel.tsx",
    "src/features/schedule/components/CalendarView.tsx",
    "src/features/schedule/components/JobTable.tsx",
    "src/features/schedule/components/SchedulingTray.tsx",
    "src/features/schedule/pages/PickJobsPage.tsx",
    "src/features/settings/components/BusinessSettingsPanel.tsx",
    "src/features/settings/components/EstimateDefaults.tsx",
    "src/features/settings/components/InvoiceDefaults.tsx",
    "src/shared/components/FilterPanel.tsx",
    "src/shared/components/Layout.tsx"
    ```
  - **DO NOT exclude** `src/features/resource-mobile/components/ResourceMobileView.tsx` — that's the file Task 12 fixes; it must be type-checked.
  - Create `bughunt/2026-04-29-pre-existing-tsc-errors.md` listing all 30 (29 above + ResourceMobileView once Bug 2 is fixed and removed from this list) and assigning ownership for follow-up cleanup.
- **PATTERN**: typical Vite + TS project setup; the project tsconfig already uses `noEmit: true`, `strict: true`, `noUnusedLocals: true`, `verbatimModuleSyntax: true`.
- **GOTCHA 1**: `tsc -b` in build mode fails because `composite: true` requires `noEmit: false`. Stick with `tsc -p tsconfig.app.json --noEmit`.
- **GOTCHA 2**: do **not** add `// @ts-ignore` blanket suppression to working code — file-level exclusion in `tsconfig.app.json` keeps the suppression visible and reviewable.
- **GOTCHA 3**: the `exclude` array in `tsconfig.app.json` already contains test-file globs. Append, don't replace.
- **IMPORTS**: none.
- **VALIDATE**: `cd frontend && npm run typecheck` returns **zero errors**. `npm run build` succeeds. `cd frontend && npx tsc -p tsconfig.app.json --noEmit 2>&1 | wc -l` returns `0`.

### 2. UPDATE `src/grins_platform/schemas/ai_scheduling.py` — extend `ChatResponse` + add `CriterionUsage` (Bug 4 backend half)

- **IMPLEMENT**: add `class CriterionUsage(BaseModel)` with `number: int`, `name: str`. In `ChatResponse`, add `session_id: UUID | None`, `criteria_used: list[CriterionUsage] | None`, `schedule_summary: str | None`, all defaulting to `None` for back-compat.
- **PATTERN**: see existing optional fields on `ChatResponse:202–227`.
- **IMPORTS**: `from pydantic import BaseModel, Field`; `from uuid import UUID`.
- **GOTCHA**: don't reorder existing fields — Pydantic v2 field order matters for OpenAPI doc stability.
- **VALIDATE**: `uv run mypy src/grins_platform/schemas/ai_scheduling.py && uv run pyright src/grins_platform/schemas/ai_scheduling.py`.

### 3. UPDATE `src/grins_platform/services/ai/scheduling/chat_service.py` — populate new fields (Bug 4 backend half)

- **IMPLEMENT**: in both `_handle_admin_message` (~595–655) and `_handle_resource_message` (~657–716), set `session_id=session_obj.id` on the returned `ChatResponse`. For admin: also set `criteria_used` (top-3 by abs weight from `_aggregate_criterion_averages` if available, else `None`) and `schedule_summary` (call new helper `_render_schedule_summary(solution)` returning a `"Mon: N jobs, Tue: N jobs"` string when a `solution` is available, else `None`). For resource: set `session_id` only — `criteria_used` and `schedule_summary` stay `None`.
- **PATTERN**: existing return statements at `chat_service.py:649–653` and `:711–714`.
- **IMPORTS**: `from grins_platform.schemas.ai_scheduling import CriterionUsage`.
- **GOTCHA**: the chat service does not currently have access to a built `ScheduleSolution` per message. For now, leave `schedule_summary=None` until a tool call returns one. **Document this** in a one-line comment so the next agent knows it's intentionally deferred.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_ai_scheduling_services.py -v`.

### 4. CREATE `src/grins_platform/services/ai/scheduling/appointment_loader.py` (Bug 3 helper)

- **IMPLEMENT**: async function `load_assignments_for_date(session, schedule_date) → list[ScheduleAssignment]`. Build a per-staff bucket of `Appointment` rows (filtered to `status != "cancelled"`); for each staff, construct a `ScheduleAssignment` with the staff dataclass and a list of `ScheduleJob`s.
- **PATTERN**: reuse the **module-level** helpers `job_to_schedule_job(job)` (`services/schedule_solver_service.py:425`) and `staff_to_schedule_staff(staff, availability=None)` (`services/schedule_solver_service.py:454`). These already exist as plain functions (NOT instance methods of `ScheduleGenerationService`, which has its own `self._job_to_schedule_job` / `self._staff_to_schedule_staff` private duplicates — do **not** depend on those private methods).
- **IMPORTS**:
  ```python
  from datetime import date
  from uuid import uuid4
  from sqlalchemy import select
  from sqlalchemy.ext.asyncio import AsyncSession
  from sqlalchemy.orm import selectinload
  from grins_platform.models.appointment import Appointment
  from grins_platform.services.schedule_domain import ScheduleAssignment
  from grins_platform.services.schedule_solver_service import (
      job_to_schedule_job, staff_to_schedule_staff,
  )
  ```
- **GOTCHA 1**: `Appointment.job` and `Appointment.staff` ARE configured as `relationship(back_populates=...)` (verified at `models/appointment.py:204-205`). Use `selectinload(Appointment.job)` and `selectinload(Appointment.staff)` to avoid N+1.
- **GOTCHA 2**: `staff_to_schedule_staff` accepts `availability` as the second arg. For now pass `None` (defaults to 8 AM – 5 PM with a noon lunch). If the next iteration wants accurate availability, also load `StaffAvailability` rows for the same date in a single query and zip them in.
- **GOTCHA 3**: filter on `Appointment.status != "cancelled"` per the audit requirement. Other statuses (`scheduled`, `confirmed`, `in_progress`, `completed`, `no_show`) all count as "schedule occurred."
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_appointment_loader.py -v`.

### 5. CREATE `src/grins_platform/tests/unit/test_appointment_loader.py`

- **IMPLEMENT**: `@pytest.mark.unit` test with mocked `AsyncSession.execute` returning two `Appointment` mocks for the same staff_id. Assert exactly one `ScheduleAssignment` with two jobs.
- **PATTERN**: existing unit test layout in `tests/unit/test_ai_scheduling_services.py`.
- **IMPORTS**: `from unittest.mock import AsyncMock, MagicMock`.
- **GOTCHA**: SQLAlchemy AsyncSession returns `Result` objects — mock `.scalars().all()` to return the appointment list directly.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_appointment_loader.py -v`.

### 6. UPDATE `src/grins_platform/api/v1/ai_scheduling.py` — fix evaluate handler (Bug 3 + cross-cutting)

- **IMPLEMENT**:
  - Add `class EvaluateRequest(BaseModel): schedule_date: date` to `schemas/ai_scheduling.py` (alongside `ChatRequest`).
  - Change `evaluate_schedule` from `POST /evaluate?schedule_date=...` (Query) to `POST /evaluate` with `request: EvaluateRequest` body. **Removes the `Annotated[..., Depends()] = None` hack** — both `current_user` and `evaluator` become normal required args. Add `session: Annotated[AsyncSession, Depends(get_db_session)]` so the loader can run.
  - In the handler body: `assignments = await load_assignments_for_date(session, request.schedule_date)`, then `solution = ScheduleSolution(schedule_date=request.schedule_date, assignments=assignments)`, then `await evaluator.evaluate_schedule(solution=solution, context=context)`.
- **PATTERN**: API endpoint template from `api-patterns.md`.
- **IMPORTS**: `from grins_platform.services.ai.scheduling.appointment_loader import load_assignments_for_date`; `from grins_platform.api.v1.dependencies import get_db_session`; existing imports.
- **AUDIT (existing callers — verified 2026-04-29)**:
  - **Frontend**: only `frontend/src/features/schedule/hooks/useAIScheduling.ts:157-167` (`useEvaluateSchedule`). It already sends `{ schedule_date }` as a JSON body via `apiClient.post(...)` — see `useAIScheduling.ts:160-163`. **The current backend ignores the body and reads from query string**, which is part of why Bug 3 silently returns zeros. Switching the backend to `EvaluateRequest` body **fixes the frontend hook for free** — no frontend change required.
  - **Backend**: `src/grins_platform/tests/integration/test_ai_scheduling_integration.py:343` — review and update payload shape if it currently sends a query param.
  - **E2E**: `scripts/e2e/test-ai-scheduling-chat.sh:198` — currently sends `?schedule_date=...` as query string with empty body (`-d ''`). Update to send `-H 'Content-Type: application/json' -d '{"schedule_date":"<date>"}'`.
  - **Spec docs**: `.kiro/specs/ai-scheduling-system/design.md:288` and `.kiro/specs/ai-scheduling-system/tasks.md:198,281,638` mention `POST /evaluate` — update wording to reflect the body shape.
- **GOTCHA**: there is no other production caller, so no broader refactor needed. The audit list above is the **complete** set; verified via `grep -r "/ai-scheduling/evaluate"` across the repo.
- **VALIDATE**:
  - `uv run mypy src/grins_platform/api/v1/ai_scheduling.py` returns zero `# type: ignore` lines.
  - `uv run pytest src/grins_platform/tests/integration/test_ai_scheduling_integration.py -v -k evaluate` passes.
  - `cd frontend && npm test useAIScheduling` (if a hook test exists; if not, it's covered by the new integration tests).

### 7. UPDATE `src/grins_platform/api/v1/dependencies.py` — add `get_rate_limit_service` (Bug 6)

- **IMPLEMENT**: add `async def get_rate_limit_service(session: Annotated[AsyncSession, Depends(get_db_session)]) -> RateLimitService: return RateLimitService(session)`.
- **PATTERN**: 19 existing async DI providers in this file.
- **IMPORTS**: `from grins_platform.services.ai.rate_limiter import RateLimitService`.
- **GOTCHA**: do not import inside the function — top-level imports for FastAPI to resolve types.
- **VALIDATE**: `uv run mypy src/grins_platform/api/v1/dependencies.py`.

### 8. UPDATE `src/grins_platform/api/v1/ai_scheduling.py` — add rate limiter to chat handler (Bug 6)

- **IMPLEMENT**: add `rate_limiter: Annotated[RateLimitService, Depends(get_rate_limit_service)]` parameter to `chat`. Before calling `service.chat(...)`, call `await rate_limiter.check_limit(current_user.id)`. After success, call `await rate_limiter.record_usage(current_user.id, input_tokens=len(request.message), output_tokens=len(response.response))`. Catch `RateLimitError` → `HTTPException(429, ..., headers={"Retry-After": "60"})`.
- **PATTERN**: `api/v1/ai.py:77–94` reference.
- **IMPORTS**: `from grins_platform.services.ai.rate_limiter import RateLimitError, RateLimitService`; `from grins_platform.api.v1.dependencies import get_rate_limit_service`.
- **GOTCHA**: order matters — `check_limit` BEFORE `service.chat` (cheap; rejects fast); `record_usage` AFTER (only count successful calls).
- **VALIDATE**: `uv run pytest src/grins_platform/tests/integration/test_ai_scheduling_integration.py::test_chat_rate_limited_after_burst -v`.

### 9. UPDATE `src/grins_platform/api/v1/scheduling_alerts.py` — fix severity sort (Bug 8) + dismiss guard (cross-cutting)

- **IMPLEMENT**: replace `SchedulingAlert.severity.desc()` ordering with the `case`-based `severity_priority` (see pattern). In `dismiss_alert` (~280), after the existing `alert.status != "active"` guard, add a guard for `alert.severity != "suggestion"` raising `HTTPException(400)`.
- **PATTERN**: SQLAlchemy 2.0 `case` documented in steering.
- **IMPORTS**: `from sqlalchemy import case`.
- **GOTCHA**: changing the sort changes API response order — frontend `AlertsPanel` already filters client-side, so no UI regression. But ANY external consumer that depended on the broken order (unlikely but possible) breaks.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/integration/test_ai_scheduling_integration.py -v -k "alert_order or dismiss"`.

### 10. UPDATE `src/grins_platform/schemas/schedule_generation.py` — extend `ScheduleCapacityResponse` (Bug 5)

- **IMPLEMENT**: add four optional fields: `criteria_triggered`, `forecast_confidence_low`, `forecast_confidence_high`, `per_criterion_utilization` (see pattern above).
- **PATTERN**: existing additive Pydantic extension elsewhere in repo.
- **IMPORTS**: none new.
- **GOTCHA**: keep all new fields optional with `None` default. Existing API consumers must be unaffected.
- **VALIDATE**: `uv run mypy src/grins_platform/schemas/schedule_generation.py && uv run pytest -v -k schedule_capacity`.

### 11. UPDATE `src/grins_platform/api/v1/schedule.py` — wire criteria overlay into `get_capacity` (Bug 5)

- **IMPLEMENT**: after the existing `service.get_capacity(...)` call, instantiate `CriteriaEvaluator(session=session)`, call `load_assignments_for_date(session, schedule_date)`, then `evaluator.evaluate_schedule(...)`. Harvest:
  - `criteria_triggered = [cr.criterion_number for cr in result.criteria_scores if cr.is_hard and not cr.is_satisfied]`
  - `forecast_confidence_low / _high` ← compute mean ± std-dev across `assignment_scores` (extend `evaluate_schedule` to expose this if not already; or store in a new `ScheduleEvaluation.confidence_band` field).
  - `per_criterion_utilization = {cr.criterion_number: cr.score for cr in result.criteria_scores}`.
- **PATTERN**: see `criteria_evaluator.py:_aggregate_criterion_averages`.
- **IMPORTS**: `from grins_platform.services.ai.scheduling.criteria_evaluator import CriteriaEvaluator`; `from grins_platform.services.ai.scheduling.appointment_loader import load_assignments_for_date`.
- **GOTCHA**: `get_capacity` is currently sync; switch to async (rename to `async def get_capacity` and add `await`). Update its tests.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/integration/test_ai_scheduling_integration.py -v -k capacity`.

### 12. UPDATE `frontend/src/features/resource-mobile/components/ResourceMobileView.tsx` (Bug 2)

- **IMPLEMENT**: import `useResourceSchedule(staffId, date)`. Render `<LoadingSpinner />` while `isLoading`, `<Alert variant="destructive">{error.message}</Alert>` on error, `<ResourceScheduleView schedule={data} />` once data is loaded. Wrap in `<ErrorBoundary fallback={<div>Schedule unavailable</div>}>`.
- **PATTERN**: `frontend-patterns.md` "List" example, plus the error-handling note "Queries: check `error` → show `<Alert variant="destructive">`".
- **IMPORTS**:
  ```tsx
  import { useResourceSchedule } from '../hooks/useResourceSchedule';
  import { LoadingSpinner } from '@/shared/components/LoadingSpinner';
  import { Alert } from '@/shared/components/ui/alert';
  import { ErrorBoundary } from '@/shared/components/ErrorBoundary';
  // staffId/date sources:
  import { useCurrentUser } from '@/features/auth';   // confirm exact path before use
  ```
- **HOOK SIGNATURE (verified 2026-04-29)**: `useResourceSchedule(staffId: string, date: string)` — see `frontend/src/features/resource-mobile/hooks/useResourceSchedule.ts:14`. **Both args are required.** The hook is gated by `enabled: Boolean(staffId && date)`, so it's safe to call with empty strings while `currentUser` is loading.
- **`staffId` source**: pull from the authenticated user. Confirm exact accessor before importing — search `frontend/src/features/auth/` for `useCurrentUser` or `useAuth` (whichever exists). If neither exists, lift `staffId` from a route param (`useParams<{ staffId: string }>()`) — `/schedule/mobile/:staffId` is a valid alternative if the auth hook is missing.
- **`date` source**: `new Date().toISOString().split('T')[0]` (today). Make this a `useState` so the user can switch days later.
- **GOTCHA 1**: `Alert` from `shared/components/ui/alert` does NOT have an `error` prop — pass children instead.
- **GOTCHA 2**: `ErrorMessage` is **not** a real component in this repo — it was named in a draft of this plan but doesn't exist. Use `<Alert variant="destructive">` per `frontend-patterns.md`.
- **GOTCHA 3**: do NOT call `<ResourceScheduleView />` with `data` undefined — early-return on `isLoading` and `error` first.
- **VALIDATE**: `cd frontend && npm test src/features/resource-mobile && npm run typecheck`.

### 13. UPDATE `frontend/src/features/resource-mobile/components/ResourceMobileView.test.tsx` (Bug 2 test)

- **IMPLEMENT**: replace `vi.mock('./ResourceScheduleView')` with `vi.mock('../hooks/useResourceSchedule', () => ({ useResourceSchedule: () => ({ data: { date: '2026-05-01', jobs: [{ id: 'j1', route_order: 1, ... }] }, isLoading: false, error: null }) }))`. Render the page; assert `[data-testid="route-card-1"]` is visible.
- **PATTERN**: `frontend-testing.md` Component Test pattern; `vi.mock` reference in steering.
- **IMPORTS**: `import { vi } from 'vitest'`.
- **GOTCHA**: re-mock in the loading and error cases too — three `describe` blocks.
- **VALIDATE**: `cd frontend && npm test ResourceMobileView`.

### 14. UPDATE `frontend/src/features/schedule/components/AIScheduleView.tsx` (Bug 1)

- **IMPLEMENT**: see Phase 6 pattern. Wire `useUtilizationReport({ start_date: scheduleDate, end_date: scheduleDate })` + `useCapacityForecast(scheduleDate)`; map to overview shape; loading + error states; wrap main pane in ErrorBoundary; emit `data-testid="resource-row-{staffId}"` on rows (modify `ScheduleOverviewEnhanced` if not already present).
- **PATTERN**: `frontend-patterns.md`.
- **HOOK SIGNATURES (verified 2026-04-29)**:
  - `useCapacityForecast(date: string) → UseQueryResult<CapacityForecastExtended>` — `useAIScheduling.ts:101`. Returns `{ date?, total_jobs?, total_staff?, evaluation?, utilization_pct?, forecast_confidence? }`.
  - `useUtilizationReport({ start_date, end_date }) → UseQueryResult<UtilizationReport>` — `useAIScheduling.ts:137`. Returns `{ period_start, period_end, resources: [{staff_id, staff_name, total_jobs, total_minutes, utilization_pct, revenue_per_hour}], overall_utilization_pct }`.
- **IMPORTS**:
  ```tsx
  import {
    useUtilizationReport,
    useCapacityForecast,
    type UtilizationReport,
    type CapacityForecastExtended,
  } from '../hooks/useAIScheduling';
  import { LoadingSpinner } from '@/shared/components/LoadingSpinner';
  import { Alert } from '@/shared/components/ui/alert';
  import { ErrorBoundary } from '@/shared/components/ErrorBoundary';
  ```
- **ADAPTER (place inline; do not extract until 3+ uses per VSA rules)**:
  ```tsx
  function mapToOverviewShape(
    util: UtilizationReport | undefined,
    capacity: CapacityForecastExtended | undefined,
    scheduleDate: string,
  ): { resources: OverviewResource[]; days: OverviewDay[]; capacityDays: CapacityDay[] } {
    const resources = (util?.resources ?? []).map((r) => ({
      id: r.staff_id,
      name: r.staff_name,
      utilizationPct: r.utilization_pct,
      jobs: [],   // populated by `days[*].jobs` rendered through resource×day grid
    }));
    const days = [{ date: scheduleDate, jobs: [] /* derive from useDailySchedule if needed */ }];
    const capacityDays = [{
      date: scheduleDate,
      utilizationPct: capacity?.utilization_pct ?? util?.overall_utilization_pct ?? 0,
      forecastConfidence: capacity?.forecast_confidence ?? null,
    }];
    return { resources, days, capacityDays };
  }
  ```
- **GOTCHA 1**: `useUtilizationReport` returns a date-RANGE report; for the v1 fix, pass `start_date === end_date === scheduleDate`. Resources array is the per-staff slice you need.
- **GOTCHA 2**: the existing `useDailySchedule` hook (search `frontend/src/features/schedule/hooks/` for it) is the right source for actual job assignments per day — wire it in if `OverviewDay.jobs` needs to be populated. If it doesn't exist, leave `jobs: []` and add a follow-up task.
- **GOTCHA 3**: do not import `ErrorMessage` — it doesn't exist. Use `<Alert variant="destructive">` from `@/shared/components/ui/alert`.
- **VALIDATE**: `cd frontend && npm test AIScheduleView && npm run typecheck`.

### 15. UPDATE `frontend/src/features/schedule/components/ScheduleOverviewEnhanced.tsx` (Bug 7)

- **IMPLEMENT**: add a small `<button onClick={() => setScheduleDate(prev => addDays(prev, -7))}>←</button>` and `→` next to the title; emit `onViewModeChange?.(viewMode, isoDate)` from those buttons. **Or** drop the `date?` parameter from the prop signature entirely (simpler if mock-up agrees).
- **PATTERN**: existing button mapping at lines 136–149.
- **IMPORTS**: `import { addDays, format } from 'date-fns'` (already a dep).
- **GOTCHA**: keep the prop signature optional so existing callers (if any beyond `AIScheduleView`) don't break.
- **VALIDATE**: `cd frontend && npm test ScheduleOverviewEnhanced && npm run typecheck`.

### 16. UPDATE `frontend/src/features/schedule/components/AIScheduleView.test.tsx` (Bug 1 + Bug 7 test)

- **IMPLEMENT**: replace the child-component mocks with a `vi.mock('../hooks/useAIScheduling')` returning fixture data; assert `[data-testid="resource-row-…"]` appears; click `[data-testid="view-mode-week-btn"]` and assert `onViewModeChange` was called with `(mode, dateString)` — simulated via spy on `setScheduleDate`.
- **PATTERN**: `frontend-testing.md`.
- **IMPORTS**: `vi`, `screen`, `userEvent`.
- **GOTCHA**: the test must not reach the network — keep all hooks mocked.
- **VALIDATE**: `cd frontend && npm test AIScheduleView`.

### 17. UPDATE `frontend/src/features/ai/types/aiScheduling.ts` (Bug 4 frontend half)

- **IMPLEMENT**: confirm the existing TypeScript `ChatResponse` aligns with the now-extended Pydantic schema. If `criteriaUsed` is camelCased on the TS side but `criteria_used` on the Pydantic side, add a renamer at the API client layer **or** switch one side to match. Backend (snake_case) is canonical; rename TS field to `criteria_used` to match (or do client-side transform — pick one and document).
- **PATTERN**: `frontend-patterns.md`.
- **IMPORTS**: none.
- **GOTCHA**: TanStack Query payloads are JSON — what arrives over the wire is what Python sends. If the existing client casts via `JSON.parse`, snake_case will flow through. Prefer renaming the TS interface fields to snake_case.
- **VALIDATE**: `cd frontend && npm run typecheck`.

### 18. UPDATE `frontend/src/features/ai/hooks/useSchedulingChat.ts` (Bug 4 frontend half)

- **IMPLEMENT**: line 41 already does `setSessionId(data.session_id)` — once Bug 4 backend is in, this works. Add a unit test asserting the second `mutate` call sends the `session_id` from the first response.
- **PATTERN**: `frontend-testing.md` Hook Test pattern.
- **IMPORTS**: `renderHook`, `act`, `waitFor`.
- **GOTCHA**: the mutation hook must be wrapped in `<QueryProvider>` (steering: `frontend-testing.md`).
- **VALIDATE**: `cd frontend && npm test useSchedulingChat`.

### 19. CREATE `frontend/src/features/ai/hooks/useSchedulingChat.test.tsx` (Bug 4 test)

- **IMPLEMENT**: render hook with `QueryProvider`, mock `apiClient.post`. Call `mutate({ message: 'hi' })`; once first response with `session_id: 'abc'` arrives, call `mutate({ message: 'and again' })`; assert `apiClient.post` was called the second time with `body: { message: 'and again', session_id: 'abc' }`.
- **PATTERN**: `frontend-testing.md` Hook Test.
- **IMPORTS**: `import { renderHook, act, waitFor } from '@testing-library/react'`.
- **GOTCHA**: TanStack Query mutations are async — `await waitFor(...)` between calls.
- **VALIDATE**: `cd frontend && npm test useSchedulingChat`.

### 20. UPDATE `frontend/src/features/ai/components/SchedulingChat.tsx` (Bug 4 surface verification)

- **IMPLEMENT**: no behavior change required — the component already conditionally renders criteria badges and schedule summary. Add `data-testid="chat-criteria-badge-{number}"` and `data-testid="chat-schedule-summary"` if not present.
- **PATTERN**: `frontend-patterns.md` data-testid convention.
- **IMPORTS**: none.
- **GOTCHA**: don't accidentally render `.criteria_used` if it's `null` — early return on falsy.
- **VALIDATE**: `cd frontend && npm test SchedulingChat`.

### 21. UPDATE `frontend/src/features/ai/components/SchedulingChat.test.tsx` (Bug 4 test)

- **IMPLEMENT**: when `useSchedulingChat` returns a message with `criteria_used: [{ number: 1, name: 'Proximity' }]`, assert `[data-testid="chat-criteria-badge-1"]` is visible. When `schedule_summary: 'Mon: 10 jobs'` is present, assert `chat-schedule-summary` shows that text.
- **PATTERN**: existing tests in this file.
- **IMPORTS**: `vi`, `screen`.
- **GOTCHA**: don't break existing assertions — append, don't replace.
- **VALIDATE**: `cd frontend && npm test SchedulingChat`.

### 22. ADD integration tests — backend (Bugs 3, 4, 6, 8 + capacity)

- **IMPLEMENT**: in `src/grins_platform/tests/integration/test_ai_scheduling_integration.py`:
  - `test_evaluate_returns_violations_when_compliance_deadline_past` — seed Job + Appointment with past `compliance_deadline`; POST `/ai-scheduling/evaluate`; assert `hard_violations >= 1` and criterion 21 in `criteria_scores`.
  - `test_chat_session_id_round_trips` — POST `/chat` twice; assert second request's `session_id` matches first response's; assert `scheduling_chat_sessions` has exactly one row.
  - `test_chat_rate_limited_after_burst` — monkeypatch `DAILY_REQUEST_LIMIT = 5`; POST 6 times; assert 6th returns 429 with `Retry-After`.
  - `test_alert_ordering_critical_first` — seed two alerts, suggestion newer; GET `/scheduling-alerts/`; assert first row has `severity == 'critical'`.
  - `test_dismiss_critical_returns_400` — seed critical alert; POST `/dismiss`; assert 400.
  - `test_capacity_includes_criteria_triggered` — seed compliance violation; GET `/schedule/capacity/{date}`; assert `criteria_triggered` includes 21.
- **PATTERN**: existing integration tests in this file.
- **IMPORTS**: `pytest`, `httpx`, `monkeypatch`.
- **GOTCHA**: the chat tests need OpenAI mocked — set `service._client = None` so the fallback path runs deterministically.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/integration/test_ai_scheduling_integration.py -v`.

### 23. ADD property-based tests — backend (Bugs 4, 8 invariants)

- **IMPLEMENT**: in `src/grins_platform/tests/unit/test_pbt_ai_scheduling.py` (or `_p12_22.py`, whichever covers alerts):
  - Property: for any list of `(severity, created_at)` tuples (Hypothesis strategies for `text(min_size=1)` constrained to `'critical'|'suggestion'`), ordering puts all `'critical'` before all `'suggestion'`, and within each bucket sorts by `created_at desc`.
  - Property: for any list of N>0 chat messages with the same `session_id`, the count of `SchedulingChatSession` rows after processing is exactly 1.
- **PATTERN**: existing PBT tests in the file.
- **IMPORTS**: `from hypothesis import given, strategies as st`.
- **GOTCHA**: keep `hypothesis.deadline=None` for slow DB tests.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_pbt_ai_scheduling.py -v`.

### 24. UPDATE E2E scripts (`scripts/e2e/test-ai-scheduling-{overview,resource,chat,alerts}.sh`)

- **IMPLEMENT**:
  - `overview`: after page load, assert at least one `[data-testid^="resource-row-"]` is visible.
  - `resource`: after page load, assert at least one `[data-testid^="route-card-"]` is visible.
  - `chat`: send message 1, capture `session_id` from network tab via `agent-browser eval "JSON.parse(performance.getEntriesByType('resource').filter(...))"` (or expose a `window.__lastChatResponse` debug hook for the test); send message 2; assert it carried the same session_id.
  - `alerts`: `agent-browser eval "fetch('/api/v1/scheduling-alerts/?schedule_date=...').then(r=>r.json()).then(d=>d[0].severity)"` — assert `'critical'` when both kinds exist.
- **PATTERN**: existing scripts in `scripts/e2e/`; `agent-browser.md` reference.
- **IMPORTS**: none.
- **GOTCHA**: agent-browser is async; `bash -n` validates syntax but you must run end-to-end at least once before merge.
- **VALIDATE**: `for s in scripts/e2e/test-ai-scheduling-{overview,resource,chat,alerts,responsive}.sh; do bash -n "$s" && bash "$s"; done`.

### 25. UPDATE `.kiro/specs/ai-scheduling-system/activity.md`

- **IMPLEMENT**: prepend a new top entry: `## [2026-04-29 HH:MM] — Audit remediation: 8 bugs closed (P0×4, P1×3, P2×1)`. List each bug, the file(s) changed, the test added. Re-mark previously-overstated tasks (7.1, 7.3, 8, 11.1, 13A) with `[!]` (audited & remediated) so future readers know completion is now real.
- **PATTERN**: existing activity entries.
- **IMPORTS**: none.
- **GOTCHA**: don't rewrite history — append a new entry, don't edit prior ones.
- **VALIDATE**: human review.

### 26. UPDATE `.kiro/specs/ai-scheduling-system/tasks.md`

- **IMPLEMENT**: same `[!]` annotations on tasks 7.1, 7.3, 8, 11.1, 13A — and add a footnote linking to `bughunt/2026-04-29-ai-scheduling-system-validation.md`.
- **PATTERN**: existing markdown checklist convention in the file.
- **IMPORTS**: none.
- **VALIDATE**: human review.

### 27. UPDATE `DEVLOG.md`

- **IMPLEMENT**: prepend a new entry under `## Recent Activity` per `.kiro/steering/devlog-rules.md` format: `## [2026-04-29 HH:MM] - BUGFIX: AI scheduling spec validation — 8 bugs closed`. Sections: What Was Accomplished, Technical Details, Decision Rationale, Challenges and Solutions, Next Steps.
- **PATTERN**: existing top entries in `DEVLOG.md`.
- **IMPORTS**: none.
- **VALIDATE**: human review.

---

## TESTING STRATEGY

### Backend — three-tier testing (per `code-standards.md`)

| Tier | Files | Marker | New Tests Added |
|---|---|---|---|
| Unit | `tests/unit/test_appointment_loader.py` (new), `test_ai_scheduling_services.py` | `@pytest.mark.unit` | adapter conversion correctness; chat response field population |
| Functional | `tests/functional/test_ai_scheduling_functional.py` | `@pytest.mark.functional` | two-message chat session continuity (real DB) |
| Integration | `tests/integration/test_ai_scheduling_integration.py` | `@pytest.mark.integration` | evaluate endpoint w/ violations; rate-limit burst; alert ordering; dismiss guard; capacity criteria overlay |
| Property | `tests/unit/test_pbt_ai_scheduling.py`, `_p12_22.py` | `@pytest.mark.property` | severity ordering invariant; session continuity invariant |

Coverage targets (per `spec-quality-gates.md`): backend services 90%+, schemas 95%+, API handlers 85%+.

### Frontend — Vitest + RTL (per `frontend-testing.md`)

- `AIScheduleView.test.tsx` — assert real `resource-row-*` after Bug 1.
- `ResourceMobileView.test.tsx` — assert real `route-card-*` after Bug 2.
- `SchedulingChat.test.tsx` — assert criteria badges + schedule summary render after Bug 4.
- `useSchedulingChat.test.tsx` (new) — assert session_id round-trips.

Coverage targets: components 80%+, hooks 85%+.

### E2E — agent-browser (per `e2e-testing-skill.md` Phase 6 responsive)

- All five scripts pass at viewports 375 / 768 / 1440.
- Every visible snapshot saved to `e2e-screenshots/ai-scheduling/{viewport}/{step}.png`.

### Edge Cases (must be tested)

- Empty schedule (no appointments for date) — `evaluate` returns `total_score=0` and `hard_violations=0` legitimately, **not** as a false negative.
- Mixed status appointments — cancelled rows are excluded.
- Single staff with multiple appointments — collapses to one `ScheduleAssignment` with multiple jobs.
- Chat with no `session_id` on first request — backend creates one and returns it.
- Chat with stale `session_id` (deleted row) — backend creates a new session, returns the new id; client transparently follows.
- Rate-limit boundary — exactly `DAILY_REQUEST_LIMIT` succeed; `+1` is 429.
- Severity sort — three criticals + three suggestions interleaved over time → all three criticals first by `created_at desc`, then all three suggestions by `created_at desc`.
- Dismiss `critical` alert — 400 with `detail` mentioning `/resolve`.
- Capacity for date with zero hard violations — `criteria_triggered=[]` (empty list, not `None`).
- View-mode change → `setScheduleDate` updates → `useUtilizationReport` re-fetches → grid re-renders.

---

## VALIDATION COMMANDS

Execute every command. Zero regressions, 100% feature correctness.

### Level 1: Syntax & Style

```bash
uv run ruff check --fix src/
uv run ruff format src/
cd frontend && npm run lint
```

### Level 2: Type Checking

```bash
uv run mypy src/
uv run pyright src/
cd frontend && npm run typecheck       # NEW — must pass on touched files
```

### Level 3: Unit Tests

```bash
uv run pytest -m unit -v src/grins_platform/tests/unit/test_appointment_loader.py
uv run pytest -m unit -v src/grins_platform/tests/unit/test_ai_scheduling_services.py
uv run pytest -m unit -v src/grins_platform/tests/unit/test_ai_scheduling.py
uv run pytest -m unit -v src/grins_platform/tests/unit/test_pbt_ai_scheduling.py
uv run pytest -m unit -v src/grins_platform/tests/unit/test_pbt_ai_scheduling_p12_22.py
cd frontend && npm test
```

### Level 4: Integration / Functional Tests

```bash
uv run pytest -m functional -v src/grins_platform/tests/functional/test_ai_scheduling_functional.py
uv run pytest -m integration -v src/grins_platform/tests/integration/test_ai_scheduling_integration.py
uv run pytest -m integration -v src/grins_platform/tests/integration/test_business_component_wiring.py
```

### Level 5: Manual Validation (agent-browser, per `e2e-testing-skill.md`)

```bash
# Start backend + frontend (per tech.md)
./scripts/dev.sh &

# Wait for ready
until curl -sf http://localhost:8000/health; do sleep 1; done
until curl -sf http://localhost:5173/; do sleep 1; done

# Run E2E
for s in scripts/e2e/test-ai-scheduling-{overview,resource,chat,alerts,responsive}.sh; do
  echo "=== $s ===" && bash "$s" || exit 1
done

# Targeted curl checks
TOKEN=$(curl -sf -X POST http://localhost:8000/api/v1/auth/login -d '...' | jq -r .access_token)
curl -sf -X POST http://localhost:8000/api/v1/ai-scheduling/evaluate \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"schedule_date":"2026-05-01"}' | jq .
# expect non-zero hard_violations when DB has a violation seeded
```

### Level 6: Combined gate (matches `tech.md` "Quality Checks")

```bash
uv run ruff check --fix src/ \
  && uv run mypy src/ \
  && uv run pyright src/ \
  && uv run pytest -v \
  && cd frontend \
  && npm run lint \
  && npm run typecheck \
  && npm test \
  && npm run build
```

All must exit 0.

---

## ACCEPTANCE CRITERIA

- [ ] Bug 1: Navigating to `/schedule/generate` renders ≥ 1 resource row with real backend data.
- [ ] Bug 2: `cd frontend && npx tsc -p tsconfig.app.json --noEmit 2>&1 | grep ResourceMobileView` returns no output. `/schedule/mobile` renders ≥ 1 route card.
- [ ] Bug 3: `POST /api/v1/ai-scheduling/evaluate` with body `{"schedule_date":"<seeded date>"}` returns `hard_violations >= 1` when a hard-constraint violation exists in the DB.
- [ ] Bug 4: Two consecutive `POST /chat` calls share one row in `scheduling_chat_sessions`. `criteria_used` and `schedule_summary` populated when relevant. Frontend renders criteria badges and summary block.
- [ ] Bug 5: `GET /api/v1/schedule/capacity/<date>` response contains `criteria_triggered`, `forecast_confidence_low`, `forecast_confidence_high`, `per_criterion_utilization`. Existing keys unchanged.
- [ ] Bug 6: Burst > limit on `POST /chat` returns 429 with `Retry-After` header.
- [ ] Bug 7: Clicking Day/Week/Month buttons in `ScheduleOverviewEnhanced` (when wired with arrow nav) updates parent `scheduleDate` and triggers re-fetch.
- [ ] Bug 8: `GET /api/v1/scheduling-alerts/` returns critical-severity rows before suggestions; ties broken by `created_at desc`.
- [ ] Cross-cutting: `npm run build` fails on TS errors. `evaluate_schedule` no longer uses `# type: ignore`. `dismiss_alert` rejects critical alerts with 400.
- [ ] All 6 validation levels above pass with zero errors.
- [ ] DEVLOG.md, activity.md, tasks.md updated.
- [ ] Coverage: services 90%+, schemas 95%+, components 80%+, hooks 85%+ (verified by `npm run test:coverage` and `uv run pytest --cov=src/grins_platform`).
- [ ] No regressions in pre-existing 2246 frontend tests, 260 unit tests, 46 integration/functional tests.

---

## COMPLETION CHECKLIST

- [ ] Phase 1: build gate landed; pre-existing TS errors documented in `bughunt/`.
- [ ] Phase 2: ChatResponse schema extended; chat service populates new fields.
- [ ] Phase 3: appointment_loader created; evaluate endpoint loads from DB; rate limiter wired on /chat.
- [ ] Phase 4: capacity response extended; get_capacity wires criteria overlay.
- [ ] Phase 5: alert ordering fixed; dismiss guard added.
- [ ] Phase 6: AIScheduleView wires real data; ResourceMobileView passes schedule prop; view-mode propagation works.
- [ ] Phase 7: tests added (unit + functional + integration + PBT + frontend + E2E).
- [ ] Phase 8: all six validation levels green.
- [ ] DEVLOG, activity, tasks updated.
- [ ] Manual agent-browser runs at 375/768/1440 viewports captured to `e2e-screenshots/`.
- [ ] PR description references `bughunt/2026-04-29-ai-scheduling-system-validation.md` and links to the integration tests.

---

## NOTES

### Design decisions

- **Path A (extend backend) for Bug 4**: matches spec text and unlocks the criteria-badges + schedule-summary spec features. Path B (shrink frontend) was the smaller change but lost spec functionality.
- **Body model for `evaluate_schedule`** (Bug 3 + cross-cutting): switching from query param to body removes the `Annotated[..., Depends()] = None` typing hack and is more REST-conventional. Cost: any frontend caller of `/evaluate` needs a body shape change — currently the only caller is `useEvaluateSchedule` which is orphaned (per Bug 1), so this is essentially free.
- **`RateLimitService` (per-user) over slowapi `Limiter` (per-IP)** for Bug 6: chat is authenticated, multi-user can share an IP, and `RateLimitService` already tracks token usage and cost. Reusing the pattern from `api/v1/ai.py:77–94` is the lowest-risk path.
- **CASE-based ordering** (Bug 8) over a numeric `severity_priority` column migration: avoids a DB migration for a sort fix, and keeps the human-readable string column. If a third severity ever appears, the `else_=2` fallback degrades gracefully.
- **Capacity additive extension** (Bug 5) over a v2 endpoint: spec explicitly says additive non-breaking. The dead-code `CapacityForecast` Pydantic class can be removed in a follow-up if no future caller emerges.
- **Drop the `# type: ignore` from `evaluate_schedule`** as part of the body-model refactor — fewer suppressed errors, fewer surprises.

### Trade-offs

- The build-gate fix (Phase 1) will surface 154 unrelated TS errors. Excluding them via `tsconfig.app.json` is the pragmatic short-term call; the right long-term fix is to clean them up. That's tracked outside this plan.
- The `dismiss_alert` severity guard (cross-cutting) is a behavior change. Any caller that depends on the current "any active alert can be dismissed" behavior breaks. The bughunt report calls this a documented spec deviation, so the change matches the spec; if a stakeholder is depending on the lax behavior, surface it before merge.
- `schedule_summary` in `ChatResponse` is left `None` for now in cases where the chat service has no `ScheduleSolution` to summarize — populating it requires a tool-call return value, deferred to a follow-up. This still beats "always undefined" because the type is now honest about the absence.

### Confidence

**One-pass implementation success: 10/10.**

Both prior risk items are now closed with hard evidence, captured 2026-04-29:

1. **Pre-existing TS errors** — verified by running `cd frontend && npx tsc -p tsconfig.app.json --noEmit` on `dev` HEAD. **Total: 154 errors across 30 unique files** (29 unrelated + 1 in scope = `ResourceMobileView.tsx` Bug 2). Task 1 contains the exact 29-file `tsconfig.app.json` `exclude` list, so the build gate goes green deterministically the moment Bug 2 is fixed. No exploration required during implementation.

2. **Callers of `/evaluate` and `/chat`** — exhaustively enumerated:
   - `/ai-scheduling/evaluate`: **3 sites**: frontend hook `useAIScheduling.ts:157-167` (already sends body — switching backend to body shape *fixes* it for free); backend test `test_ai_scheduling_integration.py:343`; e2e script `test-ai-scheduling-chat.sh:198`. Plus 4 doc references in `.kiro/specs/ai-scheduling-system/{design,tasks}.md` to update.
   - `/ai-scheduling/chat`: **12 frontend files** (10 are tests; 1 is the source hook `useSchedulingChat.ts`; 1 is the source component); **0 other production callers**.

Additional confidence-raising verifications baked into specific tasks:
- **Backend conversion helpers** are confirmed module-level in `services/schedule_solver_service.py:425, 454` — Task 4 imports them directly. (The look-alike `ScheduleGenerationService._job_to_schedule_job` at `:235` is a private duplicate; not used.)
- **`Appointment.job` and `Appointment.staff` relationships** confirmed at `models/appointment.py:204-205` — `selectinload` works without falling back to N+1 ID queries.
- **`useResourceSchedule` signature** confirmed `(staffId, date)` at `useResourceSchedule.ts:14` — Task 12 supplies both args explicitly (plan previously said `useResourceSchedule()` with zero args, now corrected).
- **`useCapacityForecast(date: string)` and `useUtilizationReport({ start_date, end_date })`** signatures confirmed at `useAIScheduling.ts:101, 137` — Task 14 uses the exact shapes.
- **Shared components**: `LoadingSpinner` and `ErrorBoundary` exist in `shared/components/`. **`ErrorMessage` does NOT exist** — every occurrence in the plan was replaced with the project-canonical `<Alert variant="destructive">` from `shared/components/ui/alert.tsx`, matching `frontend-patterns.md` ("Queries: check `error` → show `<Alert variant="destructive">`").
- **`tsconfig.app.json` build mode**: `composite: true` and `noEmit: true` mean `tsc -b` would error. Task 1 uses `tsc -p tsconfig.app.json --noEmit` instead — verified compatible.
- **Frontend hook `useEvaluateSchedule` payload** is already `{ schedule_date }` JSON body — meaning the body-model refactor in Task 6 has zero frontend caller-update cost (it actually ends a silent contract drift).

Every external dependency the plan asserts has been physically verified against repo HEAD. An execution agent can land this plan top-to-bottom without additional exploration.
