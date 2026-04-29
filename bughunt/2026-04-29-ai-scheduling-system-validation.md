# AI Scheduling System — Spec validation bug hunt — 2026-04-29

End-to-end validation of the AI Scheduling System spec at
`.kiro/specs/ai-scheduling-system/` (requirements.md, design.md, tasks.md,
activity.md) against the actual `dev`-branch implementation.

Spec: 41 requirements, 27 correctness properties, 6 backend services, 6 new
tables + 4 model extensions, all API routes, all frontend components, page
composition + routing.

Status of `tasks.md` per activity log: **all 24 phases marked `[x]`
complete** (last entry 2026-04-29 11:00). Activity log claims:
- TypeScript: 0 errors, ESLint: 0 errors, Build: pass
- Tests: 2246/2246 frontend, 260 unit, 46 integration/functional
- Ruff/MyPy/Pyright: clean on AI scheduling code

Reality from this audit: the surface looks complete (file inventory,
quality gates, mocked tests) but **eight real bugs** are present, four of
them critical, and three claimed-complete tasks are not actually wired up.

Auditor commands (reproduction):
- `uv run ruff check src/grins_platform/services/ai/scheduling/ src/grins_platform/api/v1/ai_scheduling.py src/grins_platform/api/v1/scheduling_alerts.py src/grins_platform/schemas/ai_scheduling.py`
- `uv run mypy src/grins_platform/services/ai/scheduling/ src/grins_platform/api/v1/ai_scheduling.py src/grins_platform/api/v1/scheduling_alerts.py src/grins_platform/schemas/ai_scheduling.py`
- `uv run pytest -v src/grins_platform/tests/unit/test_pbt_ai_scheduling.py src/grins_platform/tests/unit/test_pbt_ai_scheduling_p12_22.py src/grins_platform/tests/unit/test_ai_scheduling.py src/grins_platform/tests/unit/test_ai_scheduling_services.py`
- `uv run pytest src/grins_platform/tests/integration/test_ai_scheduling_integration.py src/grins_platform/tests/functional/test_ai_scheduling_functional.py`
- `cd frontend && npx tsc -p tsconfig.app.json --noEmit`
- `cd frontend && npm run build`
- `cd frontend && npm test -- --run src/features/resource-mobile src/features/scheduling-alerts src/features/schedule/components/AIScheduleView src/features/ai/components/SchedulingChat src/features/ai/components/ResourceMobileChat src/features/ai/components/PreJobChecklist`
- `for f in scripts/e2e/test-ai-scheduling-{overview,alerts,chat,resource,responsive}.sh; do bash -n "$f"; done`

---

## Summary

| # | Severity | Title | Surface that masked it | Status |
|---|----------|-------|------------------------|--------|
| 1 | **P0 — Critical** | `AIScheduleView` passes empty arrays to `ScheduleOverviewEnhanced`; admin schedule grid renders blank in production | Tests mock the child component; no integration test loads the page with real data | open |
| 2 | **P0 — Critical** | `ResourceMobileView` renders `<ResourceScheduleView />` without the required `schedule` prop (TS2741) | `npm run build` is `vite build` only — no `tsc --noEmit` gate; tests mock `ResourceScheduleView` | open |
| 3 | **P0 — Critical** | `POST /api/v1/ai-scheduling/evaluate` is a no-op — always returns zeros; never loads assignments from DB | Activity log claimed "evaluator loads from DB" — but the evaluator only iterates `solution.assignments` and the endpoint passes an empty solution | open |
| 4 | **P0 — Critical** | Frontend/backend `ChatResponse` schema mismatch: `session_id`, `criteria_used`, `schedule_summary` declared in TS but never returned by Pydantic; multi-turn chat broken | TypeScript has no runtime API contract validation; backend tests use Pydantic schema directly | open |
| 5 | **P1 — High** | Task 7.3 not implemented: existing `GET /capacity/{date}` was never extended with 30-criteria analysis fields | Activity log claimed "Extended schedule.py" but only `/batch-generate` and `/utilization` were added | open |
| 6 | **P1 — High** | Task 7.1 not implemented: no rate limiting on `POST /chat` despite Req 28.7 | Activity log marked complete; rate-limit infrastructure exists in repo but was never imported here | open |
| 7 | **P1 — High** | View-mode change in `ScheduleOverviewEnhanced` never propagates the `date` argument back to `AIScheduleView`; Day/Week/Month buttons can't drive the date selector | Frontend test only checks DOM ordering; date propagation isn't asserted | open |
| 8 | **P2 — Medium** | `GET /api/v1/scheduling-alerts/` sorts by `severity.desc()` (string sort) — `"suggestion" > "critical"` alphabetically, so suggestions come BEFORE alerts in the API response | Frontend `AlertsPanel` re-filters client-side, hiding the bug for the in-app UI but breaking the documented API contract | open |

Quality-gate results during this audit:

| Gate | Result |
|------|--------|
| `ruff check` (AI scheduling files) | ✅ all checks passed |
| `mypy` (AI scheduling files) | ✅ no issues found in 22 source files |
| `pytest -m unit` (AI scheduling) | ✅ 260 passed |
| `pytest` (AI scheduling integration + functional) | ✅ 46 passed |
| `vitest run` (new feature tests) | ✅ 98/98 passed across 13 files |
| `vite build` | ✅ built in 5.96s |
| `tsc -p tsconfig.app.json --noEmit` | ❌ **154 errors total** (mostly pre-existing, but 1 new in `ResourceMobileView.tsx` — see Bug 2) |
| `bash -n` on 5 e2e scripts | ✅ all parse |

What this means: every individual quality gate the activity log cites is
green except for `tsc`, which is *not* run by `npm run build`. The bugs
below are reachable only by reading the code, running the integrated app,
or running `tsc` directly.

---

## Bug 1 — `AIScheduleView` renders an empty schedule grid in production

**Severity:** P0 — the entire admin AI schedule page is functionally
non-existent. The grid that's the centerpiece of Req 10.1–10.10 is blank.

**File:** `frontend/src/features/schedule/components/AIScheduleView.tsx`

**Symptom:** When a user navigates to `/schedule/generate`, the
two-column layout renders. The `<aside>` (chat) works because
`SchedulingChat` fetches its own data via `useSchedulingChat`. The
`<main>` shows:
- A header band ("Schedule Overview — Week of YYYY-MM-DD")
- A legend bar (5 colored dots)
- An **empty grid** — no resource rows, no day columns, no jobs
- A `CapacityHeatMap` row with **no cells**
- The `AlertsPanel` (which works, because it has its own `useAlerts` hook)

**Root cause:** `AIScheduleView.tsx:58-64` hard-codes empty arrays into
`ScheduleOverviewEnhanced`'s data props, and never imports any of the
five `useAIScheduling` hooks (`useCapacityForecast`,
`useUtilizationReport`, `useEvaluateSchedule`, `useCriteriaConfig`,
`useBatchGenerate`) that were created in task 9.4 specifically for this
component.

```tsx
// frontend/src/features/schedule/components/AIScheduleView.tsx (current)
import { useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { ScheduleOverviewEnhanced } from './ScheduleOverviewEnhanced';
import { AlertsPanel } from '@/features/scheduling-alerts';
import { SchedulingChat } from '@/features/ai';
import { ErrorBoundary } from '@/shared/components/ErrorBoundary';
import { aiSchedulingKeys } from '../hooks/useAIScheduling';
import { alertKeys } from '@/features/scheduling-alerts';
import type { ScheduleChange } from '@/features/ai';

// …

export function AIScheduleView() {
  const queryClient = useQueryClient();
  const [scheduleDate, setScheduleDate] = useState<string>(
    () => new Date().toISOString().split('T')[0]
  );

  // …

  return (
    <div className="grid h-full" style={{ gridTemplateColumns: '1fr 380px' }}
         data-testid="ai-schedule-page">
      <h1 className="sr-only">AI Schedule</h1>
      <main className="flex flex-col overflow-auto">
        <ScheduleOverviewEnhanced
          weekTitle={`Schedule Overview — Week of ${scheduleDate}`}
          resources={[]}                  /* ← hard-coded empty array */
          days={[]}                       /* ← hard-coded empty array */
          capacityDays={[]}               /* ← hard-coded empty array */
          onViewModeChange={handleViewModeChange}
        />
        <AlertsPanel scheduleDate={scheduleDate} />
      </main>
      …
    </div>
  );
}
```

`ScheduleOverviewEnhanced` is purely presentational — it has no internal
data fetching. The contract (file
`frontend/src/features/schedule/components/ScheduleOverviewEnhanced.tsx:41-49`)
expects the parent to pass `resources: OverviewResource[]`,
`days: OverviewDay[]`, `capacityDays: CapacityDay[]`. Nothing populates
those.

**Why tests didn't catch it:** `AIScheduleView.test.tsx` mocks
`ScheduleOverviewEnhanced` (and `AlertsPanel` and `SchedulingChat`) so
the test only verifies that the three children are rendered in the
correct landmarks. It never asserts that real data flows in. From
`activity.md` 2026-04-29 08:21: "renders all three child components,
data-testid present, semantic landmarks, error boundary catches chat
crash" — none of which exercises the data wiring.

**Tasks misrepresented:** Task 13A.1 says "Manage shared `scheduleDate`
state" but doesn't explicitly require fetching data. Task 9.4 created
the hooks but they are imports-only orphans now — the only place
`aiSchedulingKeys` is referenced is in `handlePublishSchedule` for query
invalidation, never for actually running a query. Task 9.2 says
"Each row = one resource" but provides no fetching contract. The spec
implicitly assumes a parent will wire data in.

**Fix outline (sketch):**
1. In `AIScheduleView.tsx`, call `useUtilizationReport({ schedule_date })`
   and the existing `useDailySchedule(scheduleDate)` (or
   `useWeeklySchedule`) to source assignments and resource info.
2. Map the API responses to `OverviewResource[]`, `OverviewDay[]`,
   `CapacityDay[]` shapes that `ScheduleOverviewEnhanced` expects.
3. Add a loading skeleton + error fallback (the `ErrorBoundary` only
   wraps the chat sidebar, not the main pane).
4. Update `AIScheduleView.test.tsx` to mock the hooks and assert at least
   one resource row appears.
5. Add a real integration test (Cypress/Playwright/agent-browser) that
   logs in as admin, navigates to `/schedule/generate`, and asserts at
   least one `[data-testid^="resource-row-"]` is present.

---

## Bug 2 — `ResourceMobileView` ships a TypeScript error to production

**Severity:** P0 — the resource mobile page either crashes or silently
fails to render the route card depending on how strictly the runtime
treats `undefined` props.

**File:** `frontend/src/features/resource-mobile/components/ResourceMobileView.tsx`

**Symptom:** When `/schedule/mobile` is opened, the page renders the
chat (which has its own data fetching) but the schedule view crashes or
shows no content because `schedule` is `undefined` and
`ResourceScheduleView` immediately reads `schedule.date`,
`schedule.jobs.length`, etc.

**Root cause:** Definition mismatch — the declared prop is required, the
caller doesn't pass it.

```tsx
// frontend/src/features/resource-mobile/components/ResourceScheduleView.tsx
interface Props {
  schedule: ResourceSchedule;     // ← required
}

export function ResourceScheduleView({ schedule }: Props) {
  return (
    <div data-testid="resource-schedule-view" …>
      …
      Today's Route — {schedule.date}        // ← will throw if schedule undefined
      {schedule.jobs.length === 0 ? …}
      …
    </div>
  );
}
```

```tsx
// frontend/src/features/resource-mobile/components/ResourceMobileView.tsx
export function ResourceMobileView() {
  return (
    <div className="flex flex-col min-h-screen bg-slate-50"
         data-testid="resource-mobile-page">
      <ResourceScheduleView />          // ← no props passed
      <ResourceMobileChat />
    </div>
  );
}
```

**Auditor reproduction:**

```
$ cd frontend && npx tsc -p tsconfig.app.json --noEmit 2>&1 | grep ResourceMobileView
src/features/resource-mobile/components/ResourceMobileView.tsx(15,8): error TS2741:
Property 'schedule' is missing in type '{}' but required in type 'Props'.
```

**Why the build doesn't catch this:** `frontend/package.json` has

```
"build": "vite build"
```

(verified). `vite build` does not run `tsc --noEmit`. It transpiles TS
and skips type errors. The shipped bundle therefore contains code that
will hit `Cannot read property 'date' of undefined` at runtime.

**Why the activity log says "Build: ✅ Pass":** the activity log entries
all run `npm run build` (= `vite build`) and `tsc --noEmit` from
`frontend/` root with no `-p`. The latter resolves to the root
`tsconfig.json` which has `"files": []` and no `include`, so it type-
checks essentially nothing and exits 0. The activity entry from
2026-04-29 08:21 says "TypeScript: ✅ Pass (0 errors)" — that is
literally true for the bare `tsconfig.json` but false for the actual
app project (`tsconfig.app.json`).

**Why frontend tests pass:** `ResourceMobileView.test.tsx` mocks
`ResourceScheduleView`:

```tsx
vi.mock('./ResourceScheduleView', () => ({
  ResourceScheduleView: () => <div data-testid="resource-schedule-view" />,
}));
```

So the test never instantiates the real component and never sees the
required prop.

**Fix outline:**
1. Make `ResourceMobileView` fetch the schedule via the existing
   `useResourceSchedule` hook (it's already exported from
   `frontend/src/features/resource-mobile/hooks/useResourceSchedule.ts`).
2. Pass `schedule` to `<ResourceScheduleView schedule={data} />`. Render
   loading/error states for the un-resolved cases.
3. Either flip the build script to `"build": "tsc -b && vite build"`
   (project-wide) or add a CI gate that runs `tsc -p tsconfig.app.json`
   so this class of error stops shipping.
4. Update `ResourceMobileView.test.tsx` to render the real component
   with a mocked hook and assert the `route_order` for at least one
   job appears.

**Side finding:** `tsc -p tsconfig.app.json` reports **154 errors total**
in the project. Most are pre-existing in unrelated files (`FilterPanel`,
`Layout`, `AppointmentForm`, `CalendarView`, `JobTable`,
`SchedulingTray`, `PickJobsPage`, etc.) but they're all silently
shipping for the same reason. Out of scope for this audit, but worth
flagging.

---

## Bug 3 — `POST /api/v1/ai-scheduling/evaluate` is a no-op

**Severity:** P0 — the endpoint listed under task 7.1 and req 23.1/23.2
exists, mypy- and ruff-clean, has tests, and always returns
`{"total_score": 0.0, "hard_violations": 0, "alerts": [], "criteria_scores": []}`
regardless of what's in the database.

**Files:**
- `src/grins_platform/api/v1/ai_scheduling.py:122-162`
- `src/grins_platform/services/ai/scheduling/criteria_evaluator.py:293-372`
- `src/grins_platform/services/schedule_domain.py:126-135` (ScheduleSolution)

**Symptom:** Calling

```
POST /api/v1/ai-scheduling/evaluate?schedule_date=2026-05-01
```

returns:

```json
{
  "schedule_date": "2026-05-01",
  "total_score": 0.0,
  "hard_violations": 0,
  "criteria_scores": [],
  "alerts": []
}
```

…even when there are appointments, jobs, hard-constraint violations,
weather conflicts, or anything else in the DB for that date.

**Root cause:** Two-layer defect.

Layer 1 — the endpoint creates an empty `ScheduleSolution`:

```python
# src/grins_platform/api/v1/ai_scheduling.py:144-148
context = SchedulingContext(schedule_date=schedule_date)
# Build an empty solution for the given date; the evaluator will
# load assignments from the DB via the session.
solution = ScheduleSolution(schedule_date=schedule_date)
result = await evaluator.evaluate_schedule(solution=solution, context=context)
```

The comment says "the evaluator will load assignments from the DB via
the session." This is **false**. Activity log entry from 2026-04-29
(API checkpoint) says: "evaluate_schedule endpoint creates an empty
ScheduleSolution for the given date; evaluator loads assignments from
DB". Also false.

Layer 2 — the evaluator never queries the DB:

```python
# src/grins_platform/services/ai/scheduling/criteria_evaluator.py:319-340
total_hard_violations = 0
assignment_scores: list[float] = []
alerts: list[str] = []

for assignment in solution.assignments:           # ← solution.assignments == []
    for job in assignment.jobs:
        score = await self.evaluate_assignment(job, assignment.staff, context)
        assignment_scores.append(score.total_score)
        total_hard_violations += score.hard_violations

        alerts.extend(
            f"[Criterion {cr.criterion_number}] "
            f"{cr.criterion_name}: {cr.explanation}"
            for cr in score.criteria_scores
            if cr.is_hard and not cr.is_satisfied
        )
```

`solution.assignments` is the empty list constructed in the API. The
`for` loop body never executes. The score arrays stay empty. The result
falls through to:

```python
total_score = (
    sum(assignment_scores) / len(assignment_scores)
    if assignment_scores
    else 0.0                  # ← always this branch
)
```

`ScheduleSolution` is defined at `services/schedule_domain.py:126-135`:

```python
@dataclass
class ScheduleSolution:
    schedule_date: date
    jobs: list[ScheduleJob] = field(default_factory=list)
    staff: list[ScheduleStaff] = field(default_factory=list)
    assignments: list[ScheduleAssignment] = field(default_factory=list)
    hard_score: int = 0
    soft_score: int = 0
```

There is no method on `ScheduleSolution` that populates from the DB,
and `CriteriaEvaluator.evaluate_schedule` does not accept a session for
backfilling.

**Why tests didn't catch it:** Integration tests build their own
`ScheduleSolution` with explicit `assignments` and pass it directly to
`evaluator.evaluate_schedule`. They don't go through the
`POST /evaluate` HTTP endpoint with realistic DB state. So the unit
tests prove the evaluator works *given populated data*, but never prove
the API endpoint hands it populated data.

**Fix outline:**
1. Either change `evaluate_schedule(solution, context)` to also accept
   an `AsyncSession` and load `Appointment` rows for `schedule_date`,
   converting them to `ScheduleAssignment`s — or
2. Have the API endpoint do the load itself: query
   `Appointment.scheduled_date == schedule_date`, build the
   `ScheduleSolution`, and pass that to the evaluator.
3. Add an integration test that:
   - inserts a `Job` with `compliance_deadline` in the past
   - inserts an `Appointment` linking that job to a staff
   - calls `POST /api/v1/ai-scheduling/evaluate?schedule_date=…`
   - asserts `hard_violations >= 1` (criterion 21 should fire)

---

## Bug 4 — Backend/frontend `ChatResponse` schema mismatch breaks chat features

**Severity:** P0 — three documented chat features silently never render,
multi-turn conversation is broken because session_id is never returned.

**Files:**
- Backend: `src/grins_platform/schemas/ai_scheduling.py:202-227`
- Frontend types: `frontend/src/features/ai/types/aiScheduling.ts:34-42`
- Frontend hook: `frontend/src/features/ai/hooks/useSchedulingChat.ts:32-54`

**Backend schema (Pydantic, source of truth at runtime):**

```python
class ChatResponse(BaseModel):
    response: str
    schedule_changes: list[ScheduleChange] | None = None
    clarifying_questions: list[str] | None = None
    change_request_id: UUID | None = None
```

**Frontend type (TypeScript, never validated against runtime):**

```typescript
export interface ChatResponse {
  response: string;
  session_id: string;               // ← NEVER returned
  schedule_changes: ScheduleChange[];
  clarifying_questions: string[];
  change_request_id: string | null;
  criteria_used: Array<{ number: number; name: string }>;   // ← NEVER returned
  schedule_summary: string | null;                          // ← NEVER returned
}
```

**Symptoms:**

| User-facing feature | Spec ref | What actually happens |
|---|---|---|
| **Multi-turn chat session continuity** | task 11.1 ("session management"), schema design line 562-570 | `useSchedulingChat.ts:41` does `setSessionId(data.session_id)` but `data.session_id` is always `undefined`. Each new `sendMessage` call sends `session_id: undefined`, so the backend creates a brand new `SchedulingChatSession` row every turn. Conversation history never persists. |
| **Inline criteria tag badges** ("Criteria #1 Proximity", "Criteria #26 Weather") | Req 1.6, task 11.1 ("AI responses include inline criteria tag badges") | `MessageBubble` at `SchedulingChat.tsx:55-60` renders only when `message.criteriaUsed && message.criteriaUsed.length > 0`. `criteriaUsed` is always undefined. Badges never appear. |
| **Inline schedule summary block** ("Mon: 10 jobs, Tue: 10 jobs…") | task 11.1 ("Schedule summary display inline") | `SchedulingChat.tsx:73-78` renders only when `message.scheduleSummary` is truthy. Always falsy. Block never appears. |

**What does work** (because backend really does return these):
- The plain text `response` string ✅
- `clarifying_questions` ✅ (rendered as numbered list)
- `schedule_changes` + the "Publish Schedule →" button ✅
- `change_request_id` (used by resource flow) ✅

**Why tests didn't catch it:** `SchedulingChat.test.tsx` populates the
`useSchedulingChat` hook's return value with shape-matched mocks
including the missing fields, then asserts they render — it tests the
UI, not the API contract. The Pydantic backend tests test the schema in
isolation. Nothing tests the wire format end-to-end.

**Why TypeScript didn't catch it:** TypeScript doesn't validate at
runtime. There is no runtime schema-validation library
(io-ts/zod/effect-schema) on the frontend for this endpoint, so a TS
type that lies about the API is invisible.

**Fix outline:**
1. Decide which side is canonical. Two reasonable paths:
   - **A (extend backend):** add `session_id`, `criteria_used`,
     `schedule_summary` to `schemas/ai_scheduling.py:ChatResponse` and
     populate them in `chat_service.py:_handle_admin_message` /
     `_handle_resource_message`. The session_id is already known
     internally (`session_obj.id`); criteria_used can be lifted from the
     last `evaluate_assignment` call's `CriterionResult` list;
     schedule_summary needs a renderer pass.
   - **B (shrink frontend):** remove `session_id`, `criteria_used`,
     `schedule_summary` from the TS type and the `MessageBubble`
     renderers; document that those features are deferred. This is the
     smaller change but loses spec features.
2. Path A is consistent with the spec text — pick A.
3. Add an integration test: call `POST /chat`, parse the body as JSON,
   assert all 7 keys exist.
4. Consider generating frontend types from the Pydantic schemas
   (`fastapi.openapi.utils.get_openapi` → `openapi-typescript`).

---

## Bug 5 — Task 7.3 partially incomplete: `GET /capacity` not extended

**Severity:** P1 — a documented spec deliverable is unimplemented but
marked complete. Frontend has hooks (`useCapacityForecast`) wired to
this endpoint expecting forecast confidence intervals,
criteria-triggered alerts, etc.

**Files:**
- `src/grins_platform/api/v1/schedule.py:187-215` (the unchanged
  `get_capacity` handler)
- `src/grins_platform/schemas/schedule_generation.py:77-86`
  (`ScheduleCapacityResponse` — unchanged)
- `src/grins_platform/schemas/ai_scheduling.py:650+` (`CapacityForecast`
  schema — defined but unused)

**Spec contract** (`tasks.md` task 7.3, design.md L300):

> Extend the existing `GET /capacity` endpoint (which already exists as
> `get_capacity` and currently returns basic daily capacity) by adding
> 30-criteria analysis fields to the `CapacityForecast` response.
> Additive, non-breaking: do NOT replace the handler or change the
> existing response keys — only add new optional fields.
> _Requirements: 9.4, 9.7, 10.4, 10.7, 23.5_

**Reality:**

```python
# src/grins_platform/api/v1/schedule.py:187-215 (unchanged from pre-spec)
@router.get(
    "/capacity/{schedule_date}",
    response_model=ScheduleCapacityResponse,
)
def get_capacity(
    schedule_date: date,
    service: ScheduleGenerationService = Depends(get_schedule_service),
) -> ScheduleCapacityResponse:
    """Get scheduling capacity for a date.

    GET /api/v1/schedule/capacity/{date}
    """
    endpoints.log_started("get_capacity", schedule_date=str(schedule_date))

    try:
        response = service.get_capacity(schedule_date)
    except Exception as e:
        endpoints.log_failed("get_capacity", error=e)
        raise HTTPException(…) from e
    else:
        endpoints.log_completed(…)
        return response
```

```python
# src/grins_platform/schemas/schedule_generation.py:77-86 (unchanged)
class ScheduleCapacityResponse(BaseModel):
    """Response for schedule capacity check."""

    schedule_date: date
    total_staff: int
    available_staff: int
    total_capacity_minutes: int
    scheduled_minutes: int
    remaining_capacity_minutes: int
    can_accept_more: bool
```

No `criteria_triggered`, no `forecast_confidence`, no per-criterion
utilization, no `criteria_scores` list. The `CapacityForecast` Pydantic
class added in `schemas/ai_scheduling.py:650+` is dead code — nothing
uses it as a response model.

What *was* added in task 7.3 (correctly): `POST /batch-generate`
(line 729) and `GET /utilization` (line 811). Both work. Just the
extension of the pre-existing capacity endpoint is missing.

**Why activity log says "Task 7 complete":** The 2026-04-29 09:00 entry
reads "Extended `src/grins_platform/api/v1/schedule.py` — Added
POST /batch-generate and GET /utilization endpoints." It doesn't claim
the capacity extension was done — it just didn't address it — and then
checked the box.

**Fix outline:**
1. Add optional fields to `ScheduleCapacityResponse` (don't replace it —
   the spec demands non-breaking):

   ```python
   criteria_triggered: list[int] | None = None
   forecast_confidence_low: float | None = None
   forecast_confidence_high: float | None = None
   per_criterion_utilization: dict[int, float] | None = None
   ```

2. In `get_capacity`, after computing the basic capacity, instantiate a
   `CriteriaEvaluator` and run `evaluate_schedule` (once Bug 3 is fixed)
   for the date; harvest the per-criterion averages and triggered alert
   numbers; populate the new optional fields.
3. Or use `CapacityForecast` (already exists) as the response model and
   ensure its required fields cover the originals plus extensions.

---

## Bug 6 — Task 7.1 not implemented: no rate limiting on `POST /chat`

**Severity:** P1 — an explicit spec deliverable, called out at task 7.1,
backed by Req 28.7. Backend ships rate-limit infrastructure but it's
not wired here.

**Files:**
- `src/grins_platform/api/v1/ai_scheduling.py:73-119` (chat handler,
  no rate-limit decorator)
- `src/grins_platform/middleware/rate_limit.py` (exists)
- `src/grins_platform/services/ai/rate_limiter.py` (exists)
- `src/grins_platform/services/sms/rate_limit_tracker.py` (exists)

**Spec contract** (tasks.md task 7.1):

> Add rate limiting on chat endpoint (Req 28.7)

**Reality:**

```python
# src/grins_platform/api/v1/ai_scheduling.py:73
@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Role-aware AI scheduling chat",
)
async def chat(
    request: ChatRequest,
    current_user: CurrentActiveUser,
    service: Annotated[SchedulingChatService, Depends(get_chat_service)],
) -> ChatResponse:
    """Process a natural-language scheduling message.
    …
    """
    _log.log_started("chat", …)
    try:
        response = await service.chat(…)
    except Exception as exc:
        …
```

There is no `Depends(rate_limit_dependency)`, no decorator import, no
manual `RateLimiter.check(user_id)` call. The endpoint is a free
firehose for any authenticated user.

The codebase has working rate-limit primitives:
- `middleware/rate_limit.py` — middleware-level limiter
- `services/ai/rate_limiter.py` — AI-specific token-bucket
- `services/sms/rate_limit_tracker.py` — already used by
  `api/v1/sms.py`

Any of those would be a one-import fix.

**Why activity log says complete:** activity entry 2026-04-29 09:00
says: "Created `src/grins_platform/api/v1/ai_scheduling.py` — AI
scheduling router with POST /chat, POST /evaluate, GET /criteria" —
but doesn't mention rate limiting. Box ticked.

**Fix outline:**
1. Pick `services/ai/rate_limiter.py` (already used by `api/v1/ai.py`).
2. Add a per-user bucket on `chat`: e.g. 30 requests/minute, 200/hour.
3. Return HTTP 429 with `Retry-After` header on burst exceed.
4. Add a unit test in
   `src/grins_platform/tests/integration/test_ai_scheduling_integration.py`
   under section 18.5 ("rate limiting on AI-powered endpoints") that
   currently passes with a stub assertion — make it actually call the
   endpoint 31 times and assert the 31st returns 429.

---

## Bug 7 — `ScheduleOverviewEnhanced` view-mode change drops the `date` argument

**Severity:** P1 — once Bug 1 is fixed and the grid renders real data,
the Day/Week/Month buttons still won't work because clicking them
doesn't update the date the parent uses.

**Files:**
- `frontend/src/features/schedule/components/ScheduleOverviewEnhanced.tsx:120-125`
  (sender)
- `frontend/src/features/schedule/components/AIScheduleView.tsx:36-41`
  (receiver, expects optional `date`)

**Sender:**

```tsx
// ScheduleOverviewEnhanced.tsx
function handleViewMode(mode: 'day' | 'week' | 'month') {
  setViewMode(mode);
  onViewModeChange?.(mode);          // ← only passes `mode`; never `date`
}
```

```tsx
// (button onClick wiring at line 139)
onClick={() => handleViewMode(m)}
```

**Receiver:**

```tsx
// AIScheduleView.tsx
function handleViewModeChange(
  _mode: 'day' | 'week' | 'month',
  date?: string                       // ← parameter declared but never reaches it
) {
  if (date) setScheduleDate(date);   // ← `date` is always undefined; setter never fires
}
```

Result: the prop signature pretends the parent can react to date
changes from the child, but the child never has a date to send. Clicks
on Day/Week/Month change the visual button highlight but the
`scheduleDate` state in `AIScheduleView` (and therefore the data passed
to `AlertsPanel` and any future `ScheduleOverviewEnhanced` data hook)
never updates.

**Fix outline:**
1. Either remove the `date` parameter from the interface and accept
   that view-mode is a display-only toggle, or
2. Add a real date picker/navigation in `ScheduleOverviewEnhanced` (the
   spec mockup shows arrows next to the title and a calendar dropdown)
   and emit a `date` value from those.
3. Add a frontend test that clicks Day → asserts
   `onViewModeChange` callback was called with two arguments.

---

## Bug 8 — `list_alerts` returns suggestions before alerts (string sort gotcha)

**Severity:** P2 — direct API consumers see the wrong order; in-app UI
is unaffected because `AlertsPanel` re-filters client-side.

**File:** `src/grins_platform/api/v1/scheduling_alerts.py:164-168`

**Code:**

```python
stmt = select(SchedulingAlert).order_by(
    # Alerts (critical) before suggestions
    SchedulingAlert.severity.desc(),
    SchedulingAlert.created_at.desc(),
)
```

**The bug:** `severity` is a `String(20)` column with values
`"critical"` (alerts) and `"suggestion"` (suggestions). PostgreSQL
descending lexicographic sort orders these as:

```
"suggestion"   ← comes first (s > c)
"critical"     ← comes second
```

So suggestions appear **before** alerts in the API response. The
comment ("Alerts before suggestions") and the spec contract (task 7.2:
"alerts (red/critical) before suggestions (green)") are both violated.

**Why the UI looks fine:** `AlertsPanel.tsx:15-16` re-filters client-
side:

```tsx
const hardAlerts = alerts.filter((a) => a.severity !== 'suggestion');
const suggestions = alerts.filter((a) => a.severity === 'suggestion');
```

…and then renders `hardAlerts` first, `suggestions` second. The visual
order is correct. But any other consumer (e2e test asserting first card
in the response is critical, future analytics dashboard, the e2e
script `test-ai-scheduling-alerts.sh` if it ever validates JSON order)
will see the wrong order.

**Fix outline:**

```python
from sqlalchemy import case

severity_priority = case(
    (SchedulingAlert.severity == 'critical', 0),
    (SchedulingAlert.severity == 'suggestion', 1),
    else_=2,
)

stmt = select(SchedulingAlert).order_by(
    severity_priority,                       # 0 = critical first
    SchedulingAlert.created_at.desc(),
)
```

Or — simpler — keep the API contract documented as "ordered by
created_at desc" only, and rely on the client to bucket. Either is
valid, but the current state (lying via comment + lying via order) is
the worst option.

Add a regression test in `test_ai_scheduling_integration.py` that
seeds two alerts (one `critical`, one `suggestion`) at different
timestamps and asserts the response order.

---

## Cross-cutting issues (not standalone bugs but worth fixing)

### CI: `npm run build` doesn't gate on `tsc`

This is what allowed Bug 2 to ship. Recommended:

```diff
- "build": "vite build",
+ "build": "tsc -b && vite build",
```

…or add a separate `"typecheck": "tsc -p tsconfig.app.json --noEmit"`
script and wire it into pre-commit + CI.

### `evaluate_schedule` parameter ordering hack

`api/v1/ai_scheduling.py:127-130`:

```python
async def evaluate_schedule(
    schedule_date: date = Query(..., description="Schedule date to evaluate"),
    current_user: CurrentActiveUser = None,  # type: ignore[assignment]  # noqa: ARG001
    evaluator: Annotated[CriteriaEvaluator, Depends(get_criteria_evaluator)] = None,  # type: ignore[assignment]
) -> ScheduleEvaluation:
```

Setting `Annotated[…, Depends(…)] = None` and `# type: ignore` is a
workaround for FastAPI parameter-ordering. It works at runtime because
FastAPI's DI system resolves the dependencies, but the type annotation
lies (says `None` is acceptable) and `mypy` is muted by the `ignore`.

Cleanup: take the schedule_date as a request body
(`POST` with body) — that's more REST-conventional anyway and
sidesteps the ordering issue:

```python
class EvaluateRequest(BaseModel):
    schedule_date: date

async def evaluate_schedule(
    request: EvaluateRequest,
    current_user: CurrentActiveUser,
    evaluator: Annotated[CriteriaEvaluator, Depends(get_criteria_evaluator)],
) -> ScheduleEvaluation:
    …
```

### `dismiss_alert` doesn't enforce that the alert is a "suggestion"

Spec task 7.2: `POST /{id}/dismiss — dismiss a suggestion`.

Implementation (`scheduling_alerts.py:249-292`) accepts any active
alert. Critical alerts can be dismissed via the dismiss path,
side-stepping the `resolve` requirement. Add a `if alert.severity != 'suggestion':`
guard, or document the deviation explicitly.

### Activity log overstated completion

Phases that activity.md marks complete but were not fully implemented:

- **7.1 (rate limiting)** — Bug 6
- **7.3 (capacity extension)** — Bug 5
- **8 (API checkpoint)** — checkpoint passed but the
  `/evaluate` endpoint is a no-op (Bug 3)
- **11.1 (criteria badges + schedule summary in chat)** — Bug 4
- **13A (page composition)** — `AIScheduleView` and
  `ResourceMobileView` don't actually render data — Bugs 1, 2

Recommendation: when a checkpoint runs, exercise the wired path
end-to-end (login → page → see data → click button → verify behavior),
not just import-only / mock-only / file-existence checks.

---

## Severity legend

- **P0 — Critical**: ship-broken; user can't complete the documented
  workflow.
- **P1 — High**: spec deliverable missing or wrong; visible feature gap
  for any consumer that goes off the in-app happy path.
- **P2 — Medium**: cosmetic or order/contract drift; in-app UI papers
  over it.
- **P3 — Low**: cleanup / future-friction items.

---

## Suggested fix order

1. **Bug 2** (TS error in `ResourceMobileView`) — smallest fix, biggest
   risk reduction.
2. **CI gate fix** — add `tsc -p tsconfig.app.json --noEmit` to build,
   so future Bug-2-class issues stop landing.
3. **Bug 4** (ChatResponse schema) — restoring multi-turn chat unlocks
   correct testing for everything chat-related.
4. **Bug 1** (`AIScheduleView` data wiring) — page is currently
   end-to-end useless without this.
5. **Bug 3** (`/evaluate` no-op) — depends on `Appointment` ↔
   `ScheduleSolution` adapter; likely 1–2 hours of work.
6. **Bug 5** (capacity extension) — depends on Bug 3 since the new
   fields require evaluator output.
7. **Bug 6** (rate limit) — independent, ~15 minutes to wire existing
   limiter.
8. **Bug 7** (date propagation) — wait until Bug 1 is in.
9. **Bug 8** (alert ordering) — small, no dependency.
10. **Cross-cutting cleanups** as time permits.

End of report.
