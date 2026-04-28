# Feature: Enforce Appointment State Machine at the Model Layer

The following plan should be complete, but its important that you validate documentation and codebase patterns and task sanity before you start implementing.

Pay special attention to naming of existing utils types and models. Import from the right files etc.

## Feature Description

The `Appointment` model declares a state machine via `VALID_APPOINTMENT_TRANSITIONS` and exposes a `can_transition_to()` helper that no caller invokes. Every service mutates `appointment.status` by direct assignment or repository `update(data)` dict without validation, and one production transition that the spec requires (`CONFIRMED → SCHEDULED` via `reschedule_for_request`) is not even listed in the dict.

This feature closes gap-04 by:

1. Adding the missing `CONFIRMED → SCHEDULED` edge to `VALID_APPOINTMENT_TRANSITIONS` with an inline comment tying it to `reschedule_for_request` (gap-04.B).
2. Adding a SQLAlchemy `@validates("status")` hook on `Appointment` that raises `InvalidStatusTransitionError` on any invalid transition.
3. Adding a repository-level guard inside `AppointmentRepository.update()` and `AppointmentRepository.update_status()` — the SQL `update()` construct bypasses `@validates`, so a second layer is required.
4. Adding an `async transition_to(session, new_status, *, actor_id, reason)` method on the model that writes an `AuditLog` row and delegates the status assignment to the validated setter. Call sites migrate to this method in subsequent sprints; this plan includes migrating the four highest-risk sites.

This is steering-file-aware: the implementation follows `code-standards.md` (LoggerMixin, zero-violation ruff/mypy/pyright, three-tier tests), `tech.md` (FastAPI / SQLAlchemy 2.0 async), `structure.md` (services/models/repositories/tests layout), `spec-quality-gates.md` (structured logging events table, coverage targets), `spec-testing-standards.md` (unit + functional + integration + Hypothesis property tests), and `devlog-rules.md` (DEVLOG entry at the top, category REFACTOR).

## User Story

As a backend engineer working on appointment flows
I want the state machine to be enforced at the model and repository layers
So that a bad transition raises `InvalidStatusTransitionError` at the point of the bug instead of silently corrupting production data, and a future PR reviewer can trust that `VALID_APPOINTMENT_TRANSITIONS` is the single source of truth.

## Problem Statement

Per `feature-developments/scheduling gaps/gap-04-state-machine-not-enforced.md`:

- **4.A — validation is inconsistent.** The gap doc claims `can_transition_to()` has zero call sites. That is now partially stale: the helper IS called at `appointment_service.py:450` (`update_appointment`), `appointment_service.py:675` (`cancel_appointment`), and `appointment_service.py:2476` (`_is_valid_transition`, which delegates to `VALID_APPOINTMENT_TRANSITIONS`). But seven other writers (`_handle_confirm`, `_handle_cancel`, `bulk_send_confirmations`, `reschedule_for_request`, `conflict_resolution_service` × 2, plus three API endpoints at `jobs.py:1148, 1329, 1386`) still mutate `appointment.status` directly with no validator call. The state machine is enforced ad-hoc, not structurally. A new caller that sets `NO_SHOW` from `COMPLETED` via any of the seven unguarded paths fails silently.
- **4.B — an implemented transition is undocumented.** `reschedule_for_request` force-writes `SCHEDULED` even when the appointment was `CONFIRMED`, but `VALID_APPOINTMENT_TRANSITIONS["confirmed"]` does not list `"scheduled"`. Once 4.A's validator lands without this edge added, the reschedule-from-request flow breaks in production.
- Two write paths — `AppointmentRepository.update(data)` and `AppointmentRepository.update_status()` — issue `sqlalchemy.update()` constructs that bypass `@validates` entirely. They need their own guard.
- **Test infrastructure discovery**: the project has NO real-DB test setup. All three test tiers (`unit`/`functional`/`integration`) use `AsyncMock` repositories and `MagicMock` model instances. `@validates` does NOT fire on `MagicMock.status = X`. This means the existing test suite is safe from `@validates`-induced regressions, AND the new tests for the validator must use either (a) direct `Appointment()` model instantiation without a session (for `@validates`) or (b) mocked async session for the repo guard. There is no option (c) "real DB functional test".

## Solution Statement

Make the state machine authoritative by enforcing it in two places that together cover every write path: the ORM attribute setter (`@validates`) and the repository `update()` path (explicit pre-check). Add the `CONFIRMED → SCHEDULED` edge that's already spec-legal. Introduce an async `transition_to()` helper that additionally writes an `AuditLog` row so we can start consolidating state changes behind a single auditable call. Do not rewrite every caller in this plan — that churn belongs in follow-ups (gap-05 audit, gap-01.B). This plan keeps the blast radius tight: four call-site migrations, one new validator, one dict edit, one new method, plus tests.

## Feature Metadata

**Feature Type**: Refactor (hardening)
**Estimated Complexity**: Medium
**Primary Systems Affected**: `models/appointment.py`, `repositories/appointment_repository.py`, `services/job_confirmation_service.py`, `services/appointment_service.py`, `services/conflict_resolution_service.py`, `api/v1/jobs.py`
**Dependencies**: None new. Uses existing `InvalidStatusTransitionError`, `AuditLogRepository`, `LoggerMixin`, `sqlalchemy.orm.validates`. SQLAlchemy 2.0 and PostgreSQL 15+ per `tech.md`.

---

## CONTEXT REFERENCES

### Relevant Codebase Files — IMPORTANT: YOU MUST READ THESE BEFORE IMPLEMENTING

**Model / state machine source-of-truth:**

- `src/grins_platform/models/appointment.py:29-67` — `VALID_APPOINTMENT_TRANSITIONS` dict (edit for 4.B).
- `src/grins_platform/models/appointment.py:211-221` — `can_transition_to()` (keep; becomes the helper that the `@validates` hook delegates to).
- `src/grins_platform/models/appointment.py:223-240` — `get_valid_transitions()` + `is_terminal_status()` (unchanged, already used by `conflict_resolution_service`).
- `src/grins_platform/models/staff_availability.py:122-165` — **existing `@validates` pattern in this codebase.** Use as the exact template (including the `# type: ignore[misc,untyped-decorator]` comment) for the new hook.
- `src/grins_platform/models/enums.py` — `AppointmentStatus` enum (do not modify).

**Repository write paths that bypass `@validates` (must get a parallel guard):**

- `src/grins_platform/repositories/appointment_repository.py:52-106` — `create(...)` allows initial status; bypass is correct (initial insert must not trigger transition check).
- `src/grins_platform/repositories/appointment_repository.py:150-197` — `update(appointment_id, data)` uses `sqlalchemy.update(Appointment).values(**update_data)`. **Bypasses `@validates`.** Needs a guard when `data` contains `"status"`.
- `src/grins_platform/repositories/appointment_repository.py:535-595` — `update_status(appointment_id, new_status, ...)`. Also uses `sqlalchemy.update()`. Needs the same guard.

**Complete mutation-site catalog.** Every write path to `appointment.status` in production code, with post-fix status:

| # | Site | Pre-state | Target | Path | After fix |
|---|---|---|---|---|---|
| 1 | `job_confirmation_service.py:291` (`_handle_confirm`) | SCHEDULED (guarded at 290) | CONFIRMED | ORM set → `@validates` | ✓ valid edge |
| 2 | `job_confirmation_service.py:657` (`_handle_cancel`) | SCHEDULED or CONFIRMED (guarded at 653-655) | CANCELLED | ORM set → `@validates` | ✓ valid edge |
| 3 | `appointment_service.py:468` (`update_appointment`) | any; pre-validated via `can_transition_to` at line 450 | any | repo.update(data) → repo guard | ✓ double-checked |
| 4 | `appointment_service.py:493` (`update_appointment` forced-reset) | whatever repo returned (can be EN_ROUTE, IN_PROGRESS, etc.) | SCHEDULED | repo.update({status:SCHEDULED}) → repo guard | **⚠ see edge-case below** |
| 5 | `appointment_service.py:693` (`cancel_appointment`) | any; pre-validated via `can_transition_to` at line 675 | CANCELLED | repo.update_status → repo guard | ✓ double-checked |
| 6 | `appointment_service.py:923` (`mark_arrived`) | pre-validated at 911-921 | IN_PROGRESS | repo.update_status → repo guard | ✓ |
| 7 | `appointment_service.py:955` (`mark_completed`) | pre-validated at 946-952 | COMPLETED | repo.update_status → repo guard | ✓ |
| 8 | `appointment_service.py:987` (`confirm_appointment`) | pre-validated at 974-985 | CONFIRMED | repo.update_status → repo guard | ✓ |
| 9 | `appointment_service.py:1054` (`reschedule` date/time) | — | (no status in update_data) | repo.update | ✓ no status write |
| 10 | `appointment_service.py:1078` (`reschedule` forced-reset) | whatever repo returned | SCHEDULED | repo.update({status:SCHEDULED}) → repo guard | **⚠ see edge-case below** |
| 11 | `appointment_service.py:1181` (`reschedule_for_request`) | DRAFT, SCHEDULED, or CONFIRMED (guarded at 1135-1149) | SCHEDULED | repo.update → repo guard | **requires 4.B edge (T1)** |
| 12 | `appointment_service.py:1340` (`send_confirmation`) | DRAFT (guarded at 1324) | SCHEDULED | repo.update → repo guard | ✓ valid edge |
| 13 | `appointment_service.py:1445` (`bulk_send_confirmations`) | DRAFT (filtered at 1390-1392) | SCHEDULED | ORM set → `@validates` | ✓ valid edge |
| 14 | `appointment_service.py:1729` (`transition_status`) | pre-validated via `_is_valid_transition` at 1695 | any | repo.update → repo guard | ✓ double-checked |
| 15 | `appointment_service.py:2065` (`add_notes_and_photos`) | — | — | repo.update, no status in update_data | ✓ no status write |
| 16 | `conflict_resolution_service.py:78` (`cancel_appointment`) | any (no guard) | CANCELLED | ORM set → `@validates` | **needs T5 guard** |
| 17 | `conflict_resolution_service.py:145` (`reschedule_appointment`) | any (no guard) | CANCELLED | ORM set → `@validates` | **needs T5 guard** |
| 18 | `api/v1/jobs.py:1148` (`/complete`) | any non-terminal (guarded at 1143-1146) | COMPLETED | ORM set → `@validates` | **requires new edges (T1)** |
| 19 | `api/v1/jobs.py:1329` (`/on-my-way`) | SCHEDULED or CONFIRMED (guarded at 1325-1328) | EN_ROUTE | ORM set → `@validates` | ✓ valid edges |
| 20 | `api/v1/jobs.py:1386` (`/started`) | SCHEDULED, CONFIRMED, or EN_ROUTE (guarded at 1381-1385) | IN_PROGRESS | ORM set → `@validates` | ✓ valid edges |

**Edge cases for sites #4 and #10 (update_appointment + reschedule forced-reset):** both blocks are inside `if is_rescheduling and pre_update_status in (SCHEDULED, CONFIRMED, CANCELLED):` then `if updated.status != SCHEDULED:` → force-write SCHEDULED. If the caller passed `status=EN_ROUTE` or `status=IN_PROGRESS` in the same request that also moved the date, `updated.status` would be EN_ROUTE or IN_PROGRESS, and the forced reset would try `EN_ROUTE → SCHEDULED` or `IN_PROGRESS → SCHEDULED` — **neither is in the dict**. In the current codebase admins do not trigger this combo from the UI (separate buttons for "reschedule" and "mark en-route"), but the service-level endpoint allows it. Two options: (a) tighten the reset condition to `if updated and updated.status in (SCHEDULED, CONFIRMED, CANCELLED) and updated.status != SCHEDULED.value` — excludes impossible-in-practice combos and preserves current behaviour; or (b) leave as-is and accept that the forced reset now raises `InvalidStatusTransitionError` for the combo, returning a 400. **Plan picks (a)** — it's a two-character narrowing of an `if`, covered in task T5B.

**Already-guarded vs newly-guarded:** sites 1, 2, 3, 5, 6, 7, 8, 14 already pre-check the transition before writing. The new `@validates` + repo guard just ratifies those pre-checks (defence in depth). Sites 4, 10, 11, 16, 17, 18 are where the new enforcement changes behaviour — and every one of those is covered by a task in this plan.

**Exception class:**

- `src/grins_platform/exceptions/__init__.py:218-240` — `InvalidStatusTransitionError(FieldOperationsError)`. Takes `current_status` and `requested_status` as `AppointmentStatus | JobStatus` enum values. **Reuse as-is; do not create a new exception.**

**Audit writer (for `transition_to`):**

- `src/grins_platform/repositories/audit_log_repository.py:24-` — `AuditLogRepository.create(action, resource_type, resource_id, actor_id, details, ...)`. Use `action="appointment.status.transition"`, `resource_type="appointment"`, `resource_id=self.id`, `details={"from_status": old, "to_status": new, "reason": reason}`. Failures must be swallowed in a try/except/log (match the existing pattern at `appointment_service.py:1219-1254`).

**Test patterns to mirror:**

- `src/grins_platform/tests/unit/test_pbt_sales_pipeline_transitions.py` — Hypothesis property-test template. Mirror the `non_terminal_statuses`/`terminal_statuses` sampling strategy for `AppointmentStatus`.
- `src/grins_platform/tests/unit/test_job_service_transitions.py` — straight unit-test template for a `VALID_TRANSITIONS` dict.
- `src/grins_platform/tests/functional/test_yrc_confirmation_functional.py:51-57, 60-82` — the `_make_appointment` + `_build_mock_db` pattern. All "functional" tests in this repo mock the `AsyncSession`. Mirror `_build_mock_db` for the repo-guard tests.
- `src/grins_platform/tests/integration/test_combined_status_flow_integration.py:44-61` — `_make_appointment` uses plain `Mock()`. The `_make_appointment` at line 70 of `test_appointment_integration.py` even fakes `can_transition_to` with a local dict. **This is important context for T8**: the integration tests intentionally mock everything — they don't exercise the real `@validates` hook. The existing suite is safe from our changes; T8 adds the first real-model test.
- **Confirmed test-infrastructure fact:** there is no real-DB test fixture in the repo. Verified by grep for `async_sessionmaker` / `create_async_engine` / `TEST_DATABASE_URL` across `src/grins_platform/tests/` — zero hits. All three tiers (unit/functional/integration) use mocks. `@validates` does NOT fire on `MagicMock` attribute sets (SQLAlchemy's attribute instrumentation only runs on real mapped instances). **Blast radius of the `@validates` guard on the existing test suite: effectively zero.**

**Spec / gap document:**

- `feature-developments/scheduling gaps/gap-04-state-machine-not-enforced.md` — canonical description. Read end-to-end before starting.

### New Files to Create

- `src/grins_platform/tests/unit/test_appointment_state_machine.py` — unit + Hypothesis property tests for the `@validates` hook, the repository guard, `transition_to`, and the 4.B edge.
- `src/grins_platform/tests/functional/test_appointment_state_machine_functional.py` — functional tests at the service + repository seam. Uses the repo's existing mock-based pattern (AsyncMock session, MagicMock Appointment returned from `get_by_id`) to exercise `reschedule_for_request` and `cancel_appointment` end-to-end; assert that the new 4.B edge and repo guard behave correctly without requiring a real DB.

### Files to Modify

- `src/grins_platform/models/appointment.py` — (a) line 16: change `from sqlalchemy.orm import Mapped, mapped_column, relationship` → `from sqlalchemy.orm import Mapped, mapped_column, relationship, validates`; (b) add `"scheduled"` to `VALID_APPOINTMENT_TRANSITIONS["confirmed"]`, add `"completed"` to both `"scheduled"` and `"confirmed"` (preserves `/jobs/{id}/complete` skip-to-complete); (c) add `@validates("status")` hook; (d) add `async transition_to(...)` method.
- `src/grins_platform/repositories/appointment_repository.py` — (a) line 20: change `from grins_platform.models.enums import AppointmentStatus  # noqa: TC001` → `from grins_platform.models.enums import AppointmentStatus` (we need the class at runtime now); (b) line 19: extend to `from grins_platform.models.appointment import Appointment, VALID_APPOINTMENT_TRANSITIONS`; (c) add `from grins_platform.exceptions import InvalidStatusTransitionError`; (d) add private `_validate_status_transition_or_raise`; (e) call it from `update()` and `update_status()` whenever the payload carries a `status` key.
- `src/grins_platform/services/conflict_resolution_service.py:62-110, 140-170` — before the `appointment.status = CANCELLED` assignment, check `is_terminal_status()` and either return the existing "already cancelled"-style response (line 78 path) or raise `InvalidStatusTransitionError` wrapped in a user-facing message (line 145 path).
- `src/grins_platform/services/appointment_service.py:491-496, 1076-1081` — tighten the forced-reset `if`-condition so the new guard is never invoked against a non-customer-facing pre-state (EN_ROUTE / IN_PROGRESS / COMPLETED / NO_SHOW). One-character narrowing per site; see T5B.
- `DEVLOG.md` — prepend one entry under `## Recent Activity` (category `REFACTOR`), per `devlog-rules.md`.

### Relevant Documentation — READ BEFORE IMPLEMENTING

- [SQLAlchemy `validates` decorator](https://docs.sqlalchemy.org/en/20/orm/mapped_attributes.html#simple-validators) — fires on attribute sets, not on `Session.execute(update(...))`. Confirms why the repository guard is necessary.
- [SQLAlchemy 2.0 `update()` construct — ORM-enabled INSERT, UPDATE, and DELETE](https://docs.sqlalchemy.org/en/20/orm/queryguide/dml.html#orm-queryguide-update-delete-where) — explains that `@validates` is bypassed by `Session.execute(sa.update(...))`.
- [SQLAlchemy events vs validators](https://docs.sqlalchemy.org/en/20/orm/events.html#sqlalchemy.orm.AttributeEvents.set) — reference for future follow-up if we decide to switch from `@validates` to `event.listen(..., "set", ...)`.
- [Hypothesis `@given` + `strategies as st`](https://hypothesis.readthedocs.io/en/latest/quickstart.html) — required for the property test of "every transition allowed by the dict is accepted; every transition not allowed is rejected." Pattern already used at `test_pbt_sales_pipeline_transitions.py`.

Steering files consulted for every design decision:
- `.kiro/steering/code-standards.md` — LoggerMixin, 88-char lines, ruff+mypy+pyright zero errors, three-tier testing.
- `.kiro/steering/tech.md` — FastAPI / SQLAlchemy 2.0 async, structlog, quality gate commands.
- `.kiro/steering/structure.md` — `src/grins_platform/{models,services,repositories}/` + `tests/{unit,functional,integration}/` layout.
- `.kiro/steering/api-patterns.md` — API endpoint logging template (`DomainLogger.api_event`, `set_request_id`, etc.). Relevant for the `jobs.py` edits.
- `.kiro/steering/spec-quality-gates.md` — structured-logging event table required.
- `.kiro/steering/spec-testing-standards.md` — unit (`@pytest.mark.unit`) + functional (`@pytest.mark.functional`) + integration + Hypothesis property tests; zero ruff/mypy/pyright violations.
- `.kiro/steering/devlog-rules.md` — DEVLOG entry format; prepend at top; category `REFACTOR`.
- `.kiro/steering/auto-devlog.md` — trigger: any refactor, update DEVLOG.
- `.kiro/steering/pre-implementation-analysis.md` — parallel/subagent opportunity analysis performed: Phase 1 model+dict edit and Phase 2 repo guard can run in parallel; Phase 3 service/API migrations must wait; tests run last.

### Patterns to Follow

**`@validates` placement — mirror `staff_availability.py:122-137` exactly:**

```python
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

# ... inside class Appointment ...

@validates("status")  # type: ignore[misc,untyped-decorator]
def _validate_status_transition(self, key: str, new_status: str) -> str:
    """Enforce VALID_APPOINTMENT_TRANSITIONS on every attribute set.

    Fires on ``appt.status = X`` but NOT on ``Session.execute(update(...))``
    — the repository guard covers the SQL path.

    Raises:
        InvalidStatusTransitionError: if the transition is not allowed.
    """
    # Skip on initial insert (self.status is None before the first set).
    if self.status is None:
        return new_status
    # No-op sets are always allowed (idempotent callers, e.g. repeat Y).
    if new_status == self.status:
        return new_status
    if new_status not in VALID_APPOINTMENT_TRANSITIONS.get(self.status, []):
        from grins_platform.exceptions import InvalidStatusTransitionError
        from grins_platform.models.enums import AppointmentStatus
        raise InvalidStatusTransitionError(
            AppointmentStatus(self.status),
            AppointmentStatus(new_status),
        )
    return new_status
```

**Structured logging — `{domain}.{component}.{action}_{state}`, per `code-standards.md`:**

- `appointment.status.transition_started` — DEBUG, fields `appointment_id`, `from`, `to`, `actor_id`, `reason`.
- `appointment.status.transition_completed` — INFO, fields `appointment_id`, `from`, `to`, `actor_id`.
- `appointment.status.transition_rejected` — WARNING, fields `appointment_id`, `from`, `to`, `reason="invalid_transition"`.
- `appointment.status.audit_write_failed` — ERROR, fields `appointment_id`, `error=<exc repr>` (audit write failure must not block the transition — match the pattern at `appointment_service.py:1249-1254`).

**Repository guard shape — new private helper on `AppointmentRepository`:**

```python
async def _validate_status_transition_or_raise(
    self,
    appointment_id: UUID,
    new_status: str,
) -> None:
    """Pre-check for the SQL UPDATE path.

    @validates only fires on attribute set, not on sa.update(). Load the
    current status with a cheap single-column query and compare against
    VALID_APPOINTMENT_TRANSITIONS. Raises InvalidStatusTransitionError on
    an illegal edge; silent no-op on same-status sets and on missing rows.
    """
```

**Test docstring / marker pattern — mirror `test_pbt_sales_pipeline_transitions.py`:**

```python
"""Property-based tests for appointment status transitions.

Validates: gap-04.A, gap-04.B
"""
import pytest
from hypothesis import given, settings, strategies as st
from grins_platform.models.appointment import VALID_APPOINTMENT_TRANSITIONS
from grins_platform.models.enums import AppointmentStatus

@pytest.mark.unit
class TestProperty1TransitionValidity:
    # ...
```

**DEVLOG entry shape — per `devlog-rules.md`:**

```markdown
## [2026-04-23 HH:MM] - REFACTOR: Enforce appointment state machine (gap-04)

### What Was Accomplished
- Added @validates("status") hook on Appointment.
- Added repository guard in AppointmentRepository.update/update_status.
- Added CONFIRMED → SCHEDULED edge (reschedule_for_request).
- Added SCHEDULED/CONFIRMED → COMPLETED edges (jobs complete endpoint).
- Added transition_to() helper with AuditLog write.
...
```

---

## IMPLEMENTATION PLAN

### Phase 0: Pre-flight

Verify the import graph is cycle-free before any code edit.

**Tasks:** T0.

### Phase 1: Model foundations (no external callers touched)

Edit `VALID_APPOINTMENT_TRANSITIONS`, add the `@validates` hook, add `transition_to()`. None of this is observable to callers until Phase 2 wires the repository guard and the existing mutations start flowing through the validator. This phase is a single-file change.

**Tasks:** T1, T2, T3.

### Phase 2: Repository guard

Add `_validate_status_transition_or_raise()` on `AppointmentRepository`. Call it from `update()` and `update_status()` whenever `"status"` is in the payload. Independent of the service-layer migrations.

**Tasks:** T4.

### Phase 3: Service / API migrations for known-breakage sites

Only touch call sites where the new validator would *currently* raise:

- `conflict_resolution_service.cancel_appointment` at line 78 — add an early return if `appointment.is_terminal_status()` (matches the "not found" branch shape).
- `conflict_resolution_service.reschedule_appointment` at line 145 — add the same terminal-state guard, raise `InvalidStatusTransitionError` through the API.
- `appointment_service.update_appointment` line 492 and `reschedule` line 1077 — tighten the forced-reset `if` so the new guard never sees an EN_ROUTE / IN_PROGRESS / COMPLETED / NO_SHOW pre-state.
- Do NOT modify `jobs.py` endpoints beyond adding the new COMPLETED edges to the dict (handled in T1). The existing pre-checks there are compatible with the validator.
- `job_confirmation_service._handle_confirm` and `_handle_cancel` already guard against invalid pre-states — no changes.
- `appointment_service.reschedule_for_request` already rejects terminal states — `CONFIRMED → SCHEDULED` now explicitly allowed by the dict (T1).

**Tasks:** T5A, T5B.

### Phase 4: Tests

Unit (Hypothesis + plain), functional (mock-based), and one integration smoke test.

**Tasks:** T6, T7, T8.

### Phase 5: Validation, DEVLOG, cleanup

Run the full quality gate, update DEVLOG, update the gap-04 status line in `feature-developments/scheduling gaps/gap-04-state-machine-not-enforced.md`.

**Tasks:** T9, T10.

---

## STEP-BY-STEP TASKS

Execute every task in order, top to bottom. Each task is atomic and independently testable.

Task format keywords: **CREATE** · **UPDATE** · **ADD** · **REMOVE** · **REFACTOR** · **MIRROR**.

### T0. PRE-FLIGHT — verify the import graph is cycle-free

- **IMPLEMENT**: Before editing anything, run this cycle check exactly:
  ```bash
  uv run python -c "import grins_platform.exceptions; import grins_platform.models.appointment; import grins_platform.repositories.appointment_repository; print('imports-ok')"
  ```
- **PATTERN**: N/A — preflight check.
- **IMPORTS**: N/A.
- **GOTCHA**: `exceptions/__init__.py` uses `TYPE_CHECKING` for the model-enum imports (line 27 of `exceptions/__init__.py`). `models/appointment.py` imports from `grins_platform.database.Base`, not from `exceptions`. `repositories/appointment_repository.py` already imports from both `models.appointment` and `models.enums`. Adding `from grins_platform.exceptions import InvalidStatusTransitionError` to the repository file is safe (verified — no cycle).
  The ONLY potentially-dangerous new import is `from grins_platform.exceptions import InvalidStatusTransitionError` inside `Appointment._validate_status_transition`. This is LAZY (inside the function body) to sidestep any future cycle if someone adds a runtime import from `exceptions` back to models. Do NOT hoist it to the module-level imports even if the cycle check passes today.
- **VALIDATE**: the command above prints `imports-ok`. If it raises `ImportError`, abort the plan and investigate.

### T1. UPDATE `src/grins_platform/models/appointment.py` — extend the transitions dict (gap-04.B + skip-to-complete)

- **IMPLEMENT**: Add `AppointmentStatus.SCHEDULED.value` to the `"confirmed"` list with an inline comment explaining the `reschedule_for_request` use case. Add `AppointmentStatus.COMPLETED.value` to BOTH the `"scheduled"` and `"confirmed"` lists (preserves `/jobs/{job_id}/complete` skip-to-complete at `api/v1/jobs.py:1148`).
- **PATTERN**: The dict is at `src/grins_platform/models/appointment.py:29-67`.
- **IMPORTS**: None new.
- **GOTCHA**: Do NOT add `SCHEDULED → SCHEDULED` or `CONFIRMED → CONFIRMED` — same-status is handled by the `@validates` short-circuit (T2), not by the dict.
- **GOTCHA**: Do NOT add `NO_SHOW → SCHEDULED` or touch other existing edges — every change widens the acceptance surface. Stick to the three edges called out.
- **VALIDATE**: `uv run python -c "from grins_platform.models.appointment import VALID_APPOINTMENT_TRANSITIONS as V; assert 'scheduled' in V['confirmed'] and 'completed' in V['scheduled'] and 'completed' in V['confirmed']; print('ok')"`.

### T2. ADD `@validates("status")` to `Appointment` in `src/grins_platform/models/appointment.py`

- **IMPLEMENT**: Edit line 16 from `from sqlalchemy.orm import Mapped, mapped_column, relationship` to `from sqlalchemy.orm import Mapped, mapped_column, relationship, validates`. Place `_validate_status_transition` directly above `can_transition_to` (currently line 211). Short-circuit on `self.status is None` (initial insert) and on `new_status == self.status` (idempotent set). Do NOT modify `can_transition_to` — it is still called from `appointment_service.py:450, 675`.
- **PATTERN**: Mirror `src/grins_platform/models/staff_availability.py:122-137` exactly — including the `# type: ignore[misc,untyped-decorator]` suffix. See the Patterns to Follow section above for the full body.
- **IMPORTS**: (1) Add `validates` to the existing SQLAlchemy ORM import on line 16 (literal edit shown above). (2) Import `AppointmentStatus` and `InvalidStatusTransitionError` **lazily inside the function body** — `AppointmentStatus` is already at the top of the file but re-importing lazily keeps the function self-contained (matches the defensive pattern at `job_confirmation_service.py:251`).
- **GOTCHA**: `@validates` does NOT fire on `Session.execute(sqlalchemy.update(Appointment).values(status=...))`. That is why Phase 2 (T4) is mandatory.
- **GOTCHA**: Do not wrap the whole body in try/except — a raise here is the contract. The caller is expected to catch `InvalidStatusTransitionError` at the API boundary (existing pattern: `api/v1/jobs.py:1110-1115`).
- **GOTCHA**: SQLAlchemy fires `@validates` during `__init__` when the default constructor sees `status=...` kwarg. The body's `if self.status is None: return new_status` branch handles that case (the attribute is not set until the return). Do NOT raise if `self.status` is falsy — empty string vs None would differ.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_appointment_state_machine.py -v` once T6 lands. For this task alone:
  ```bash
  uv run python -c "
  from uuid import uuid4
  from datetime import date, time
  from grins_platform.models.appointment import Appointment
  from grins_platform.exceptions import InvalidStatusTransitionError
  a = Appointment(job_id=uuid4(), staff_id=uuid4(), scheduled_date=date.today(),
                  time_window_start=time(9), time_window_end=time(10), status='scheduled')
  a.status = 'confirmed'  # valid edge
  assert a.status == 'confirmed'
  try:
      a.status = 'scheduled'  # CONFIRMED → SCHEDULED: requires T1 4.B edge
      print('ok: 4.B edge works, status=', a.status)
  except InvalidStatusTransitionError as e:
      print('FAIL: 4.B edge missing — T1 not applied yet?', e); raise
  "
  ```

### T3. ADD `async transition_to(session, new_status, *, actor_id=None, reason=None)` on `Appointment`

- **IMPLEMENT**: New async method placed below `can_transition_to`. Signature: `async def transition_to(self, session: "AsyncSession", new_status: str, *, actor_id: "UUID | None" = None, reason: "str | None" = None) -> None`. Body: (1) remember `old = self.status`, (2) set `self.status = new_status` (raises via `@validates` if invalid), (3) `await session.flush()`, (4) write an `AuditLog` row with `action="appointment.status.transition"`, `resource_type="appointment"`, `resource_id=self.id`, `actor_id=actor_id`, `details={"from_status": old, "to_status": new_status, "reason": reason}`. Wrap the audit write in a try/except that logs via `get_logger(__name__)` but does NOT re-raise.
- **PATTERN**: Audit failure-swallowing pattern at `src/grins_platform/services/appointment_service.py:1219-1254` (`_record_reschedule_reconfirmation_audit`). Copy the shape.
- **IMPORTS**: Lazy imports inside the method: `from grins_platform.repositories.audit_log_repository import AuditLogRepository`. Add `if TYPE_CHECKING: from sqlalchemy.ext.asyncio import AsyncSession` (already present in nearby modules).
- **GOTCHA**: Do NOT migrate call sites to this method in this task — that is follow-up work covered in gap-05. This plan only requires the helper to exist and be unit-tested. Four of the existing call sites are already safe via `@validates` + repo guard alone.
- **GOTCHA**: The method is NOT a replacement for `appointment_repository.update_status()` — both coexist. `update_status()` remains the repository-layer primitive; `transition_to()` is the model-layer orchestrator with auditing. Document this in the docstring.
- **VALIDATE**: covered by T6 unit test `test_transition_to_writes_audit_log`.

### T4. UPDATE `src/grins_platform/repositories/appointment_repository.py` — add the SQL-update guard

- **IMPLEMENT**: Add private method `_validate_status_transition_or_raise(self, appointment_id, new_status)`. Body: `SELECT status FROM appointments WHERE id = :id`. If the row is missing, return silently (let the existing `update()` flow handle the not-found case via its `returning(Appointment)` → `None` result). If `current_status is None` or `current_status == new_status`, return. Otherwise, if `new_status not in VALID_APPOINTMENT_TRANSITIONS.get(current_status, [])`, raise `InvalidStatusTransitionError(AppointmentStatus(current_status), AppointmentStatus(new_status))`.
  Modify `update()` at line 150: before line 174 (the `update_data["updated_at"] = datetime.now()` line), `if "status" in update_data: await self._validate_status_transition_or_raise(appointment_id, update_data["status"])`.
  Modify `update_status()` at line 535: before line 570 (the `stmt = ...` line), `await self._validate_status_transition_or_raise(appointment_id, new_status.value)`.
- **PATTERN**: Single-column `SELECT` via `select(Appointment.status).where(Appointment.id == appointment_id)` — pattern at `appointment_repository.py:526` (`find_by_status` uses similar `select()` construction).
- **IMPORTS**: `from grins_platform.models.appointment import VALID_APPOINTMENT_TRANSITIONS`. `from grins_platform.exceptions import InvalidStatusTransitionError`. `from grins_platform.models.enums import AppointmentStatus` (already imported at line 20 as `TC001` type-only; promote to runtime import).
- **GOTCHA**: `create()` at line 52-106 must NOT call the guard — it's an insert; `self.status is None` before insert and `@validates` handles that branch too, but at the repo level we're not loading the row at all, so simply skip `create()`.
- **GOTCHA**: The SQLAlchemy `update(Appointment).values(...)` construct at line 176 does NOT run `@validates` — verify this by reading the SQLAlchemy 2.0 docs link in the Relevant Documentation section. Do NOT attempt to convert the `update()` to a `session.merge()` path; that would flip semantics for all other fields.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_appointment_state_machine.py::TestRepositoryGuard -v` once T6 lands.

### T5A. UPDATE `src/grins_platform/services/conflict_resolution_service.py` — add terminal-state guard

- **IMPLEMENT**: At `cancel_appointment` (line 62-110), between the `if not appointment:` block (line 68-74) and the `now = datetime.now(timezone.utc)` line (line 77), add:
  ```python
  if appointment.is_terminal_status():
      self.log_rejected(
          "cancel_appointment",
          reason="already_terminal",
          appointment_id=str(appointment_id),
          current_status=appointment.status,
      )
      return CancelAppointmentResponse(
          appointment_id=appointment_id,
          cancelled_at=appointment.cancelled_at or datetime.now(timezone.utc),
          reason=reason,
          message=f"Appointment already in terminal status: {appointment.status}",
      )
  ```
  At `reschedule_appointment` (line 112-180), between the `if not original:` block (line 140-142) and `original.status = CANCELLED` (line 145), add:
  ```python
  if original.is_terminal_status():
      from grins_platform.exceptions import InvalidStatusTransitionError
      from grins_platform.models.enums import AppointmentStatus
      raise InvalidStatusTransitionError(
          AppointmentStatus(original.status),
          AppointmentStatus.CANCELLED,
      )
  ```
- **PATTERN**: `is_terminal_status()` already exists on the model (`models/appointment.py:231-240`) and is already used elsewhere in this service.
- **IMPORTS**: Lazy imports inside the function body — this service uses synchronous sessions (`from sqlalchemy.orm import Session` at TYPE_CHECKING) and we don't want to polute the module top-level with async-only exceptions.
- **GOTCHA**: `reschedule_appointment` at line 145 also does `original.cancellation_reason = ...` and `original.cancelled_at = ...` — leave those untouched, the terminal check gates the whole block.
- **GOTCHA**: Do NOT migrate `job_confirmation_service._handle_confirm` (line 291) or `_handle_cancel` (line 657) — they already short-circuit on same-state (lines 274-288 and 636-649) and explicitly check pre-state (lines 653-656), so they are compatible with `@validates` as-is.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_conflict_resolution.py -v` (existing test file; verify no regressions). If the file doesn't exist, skip and rely on full-suite regression (T9).

### T5B. UPDATE `src/grins_platform/services/appointment_service.py` — tighten the two forced-reset branches

- **IMPLEMENT**: At line 492 (inside `update_appointment`), change:
  ```python
  if updated and updated.status != AppointmentStatus.SCHEDULED.value:  # type: ignore[union-attr]
      await self.appointment_repository.update(
          appointment_id,
          {"status": AppointmentStatus.SCHEDULED.value},
      )
  ```
  to:
  ```python
  if (
      updated
      and updated.status  # type: ignore[union-attr]
      in (
          AppointmentStatus.CONFIRMED.value,
          AppointmentStatus.CANCELLED.value,
      )
  ):
      await self.appointment_repository.update(
          appointment_id,
          {"status": AppointmentStatus.SCHEDULED.value},
      )
  ```
  (SCHEDULED → SCHEDULED is a no-op already; CONFIRMED → SCHEDULED valid after T1; CANCELLED → SCHEDULED always valid; EN_ROUTE/IN_PROGRESS/COMPLETED/NO_SHOW fall out of the allowed set and are skipped.)
  
  Apply the same substitution at line 1077 (inside `reschedule`).
- **PATTERN**: The outer `if is_rescheduling and pre_update_status in (SCHEDULED, CONFIRMED, CANCELLED)` at line 477/1063 already narrows the path; we're just also narrowing the inner `if` so the forced-reset only runs when the result status agrees. The outer-vs-inner divergence is what allows EN_ROUTE / IN_PROGRESS to leak through today.
- **IMPORTS**: `AppointmentStatus` already imported.
- **GOTCHA**: Do not remove the outer guard — it still controls whether the reschedule SMS fires at all.
- **GOTCHA**: Do NOT touch line 1078's force-reset if the outer `if is_rescheduling` block at line 1063 has already been refactored in a separate branch — check `git log -L '/async def reschedule/,/^    async def /:src/grins_platform/services/appointment_service.py'` before editing. If there's drift, re-read the section end-to-end.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_appointment_service_crm.py src/grins_platform/tests/functional/test_reschedule_flow_functional.py -v` (existing tests for the reschedule path must continue to pass).

### T6. CREATE `src/grins_platform/tests/unit/test_appointment_state_machine.py`

- **IMPLEMENT**: Four test classes, all `@pytest.mark.unit`:
  1. `TestValidatesHook` — four tests: (a) `test_same_status_set_is_noop_on_terminal_completed`, (b) `test_scheduled_to_confirmed_succeeds`, (c) `test_completed_to_scheduled_raises_InvalidStatusTransitionError`, (d) `test_initial_insert_skips_validator` (instantiate with `status=None` then set `status="scheduled"` — should succeed since `self.status is None` on first set).
  2. `TestDictContents4B` — three tests: (a) `test_confirmed_can_transition_to_scheduled` (asserts 4.B edge), (b) `test_scheduled_can_transition_to_completed` (skip-to-complete), (c) `test_confirmed_can_transition_to_completed`. Each asserts membership directly in `VALID_APPOINTMENT_TRANSITIONS`.
  3. `TestRepositoryGuard` — three async tests using a mocked `AsyncSession` (pattern: `tests/functional/test_yrc_confirmation_functional.py:60-82` for `_build_mock_db`): (a) `test_update_with_invalid_status_raises`, (b) `test_update_with_valid_status_passes_guard`, (c) `test_update_status_with_invalid_transition_raises`.
  4. `TestTransitionTo` — two async tests: (a) `test_transition_to_happy_path_writes_audit_log` (mock `AuditLogRepository.create` and assert called once with the expected args), (b) `test_transition_to_audit_failure_does_not_block_transition` (force `AuditLogRepository.create` to raise; assert the appointment status still transitioned).
  5. `TestPropertyTransitionDictIsConsistent` — Hypothesis property test: for every `(current, next)` pair sampled from `AppointmentStatus`, assert that `Appointment(status=current).can_transition_to(next) == (next in VALID_APPOINTMENT_TRANSITIONS[current])`. This is a tautology but it catches accidental drift when `can_transition_to` is refactored.
- **PATTERN**: Mirror `tests/unit/test_pbt_sales_pipeline_transitions.py` for the Hypothesis class. Mirror `tests/unit/test_job_service_transitions.py` for the plain unit classes.
- **IMPORTS**: `pytest`, `from hypothesis import given, settings, strategies as st`, `from unittest.mock import AsyncMock, MagicMock, patch`, `from uuid import uuid4`, `from datetime import date, time`, the model imports.
- **GOTCHA**: The `@validates` hook imports its exception lazily (T2). Ensure the test asserts raise of `InvalidStatusTransitionError` and not of `ValueError` — SQLAlchemy's `@validates` lets the raised exception bubble unchanged.
- **GOTCHA**: Do not test `reschedule_for_request` end-to-end here — that's a functional test (T7).
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_appointment_state_machine.py -v --tb=short` (all tests pass). Coverage: `uv run pytest src/grins_platform/tests/unit/test_appointment_state_machine.py --cov=src/grins_platform/models/appointment --cov=src/grins_platform/repositories/appointment_repository --cov-report=term-missing` — target 90%+ on the new code paths.

### T7. CREATE `src/grins_platform/tests/functional/test_appointment_state_machine_functional.py`

- **IMPLEMENT**: Three tests, `@pytest.mark.functional`, using the project's existing mock-session pattern (NO real DB — that infrastructure doesn't exist; see Test Infrastructure Constraint in Notes):
  1. `test_reschedule_for_request_from_confirmed_is_now_allowed` — build an `AppointmentService` with `AsyncMock()` `appointment_repository` (mirror `test_appointment_operations_functional.py:100-120` `_build_appointment_service`). Set `repo.get_by_id.return_value` = a `MagicMock()` appointment with `status=CONFIRMED.value`. Set `repo.update.return_value` = a `MagicMock()` with the new date and `status=SCHEDULED.value`. Call `service.reschedule_for_request(id, new_scheduled_at=...)`. Assert the call did NOT raise (without T1 it would have — but this test is behavioural). Assert `repo.update` was called with `{"status": "scheduled", ...}`.
  2. `test_reschedule_for_request_from_completed_raises` — same setup but `get_by_id.return_value.status = COMPLETED.value`. Assert `InvalidStatusTransitionError` is raised from the service's own pre-check at line 1140 (unchanged by this plan; serves as a regression sentinel).
  3. `test_repository_guard_rejects_invalid_update` — build a mock `AsyncSession` via the `_build_mock_db` pattern at `test_yrc_confirmation_functional.py:60-82`. Wire `session.execute` so the guard's `SELECT status FROM appointments WHERE id=:id` returns a `Result` whose `.scalar_one_or_none()` yields `"completed"`. Instantiate `AppointmentRepository(session)` directly. Call `await repo.update(appointment_id, {"status": "scheduled"})`. Assert `InvalidStatusTransitionError` is raised with `current_status=COMPLETED, requested_status=SCHEDULED`.
- **PATTERN**: `_build_appointment_service` helper at `test_appointment_operations_functional.py:100-122` (AsyncMock repos, returns service + repo tuple). `_build_mock_db` at `test_yrc_confirmation_functional.py:60-82` (mock session wired for SELECT statements).
- **IMPORTS**: `from unittest.mock import AsyncMock, MagicMock`; `import pytest`; `from grins_platform.exceptions import InvalidStatusTransitionError`; `from grins_platform.models.enums import AppointmentStatus`; `from grins_platform.services.appointment_service import AppointmentService`; `from grins_platform.repositories.appointment_repository import AppointmentRepository`.
- **GOTCHA**: The repo guard issues `session.execute(select(Appointment.status).where(...))`. The mock must return an object whose `.scalar_one_or_none()` yields a string status. Match by the SQL type if you're using a side_effect — a simple `AsyncMock(return_value=Mock(scalar_one_or_none=Mock(return_value="completed")))` suffices.
- **GOTCHA**: Don't hit `session.execute` twice without configuring the mock — `update()` calls `execute` once for the guard, once for the UPDATE. The second call shouldn't even run if the guard raises. Assert `session.execute.call_count == 1` on the negative test.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/functional/test_appointment_state_machine_functional.py -v -m functional`.

### T8. UPDATE `src/grins_platform/tests/integration/test_combined_status_flow_integration.py` — add a smoke test

- **IMPLEMENT**: Add a single parameterized test that walks a real `Appointment` through `SCHEDULED → CONFIRMED → EN_ROUTE → IN_PROGRESS → COMPLETED` via direct attribute sets. Assert every step succeeds (i.e. `@validates` does not reject the golden-path flow). Add a second parameterized negative case: `COMPLETED → SCHEDULED` raises `InvalidStatusTransitionError`.
- **PATTERN**: File is already integration-scope; this test slots next to the existing `_simulate_on_my_way`/`_simulate_started`/`_simulate_complete` helpers (lines 64-103).
- **IMPORTS**: Add `InvalidStatusTransitionError` to the exceptions import.
- **GOTCHA**: The existing file uses `Mock()` appointment fixtures, which bypass `@validates`. For this new test, construct real `Appointment` instances (just instantiate the model; no session needed for attribute-level `@validates` assertion).
- **VALIDATE**: `uv run pytest src/grins_platform/tests/integration/test_combined_status_flow_integration.py -v -m integration`.

### T9. UPDATE `DEVLOG.md` — prepend entry under `## Recent Activity`

- **IMPLEMENT**: Follow the `devlog-rules.md` template. Category: `REFACTOR`. Title: `Enforce appointment state machine (gap-04.A + 4.B)`. Include the four sections: What Was Accomplished, Technical Details (mention `@validates`, repo guard, new transitions), Decision Rationale (explain two-layer enforcement — why `@validates` alone is insufficient), Challenges and Solutions (the `SELECT` overhead trade-off in the repo guard — one extra query per `update()` call that carries `status`). Next Steps: reference gap-05 (audit centralisation) and gap-01.B (EN_ROUTE reschedule guard cleanup).
- **PATTERN**: `devlog-rules.md` + an existing recent REFACTOR entry in `DEVLOG.md`.
- **GOTCHA**: INSERT AT TOP of the file, immediately after the `## Recent Activity` header.
- **VALIDATE**: `head -40 DEVLOG.md` — the new entry is first.

### T10. UPDATE `feature-developments/scheduling gaps/gap-04-state-machine-not-enforced.md`

- **IMPLEMENT**: Change the `**Status:**` line at the top from `Investigated, not fixed` to `Fixed in <commit-sha> — see DEVLOG 2026-04-23`.
- **PATTERN**: Several sibling gap docs in the same directory carry "Fixed in …" status lines; mirror their shape.
- **VALIDATE**: `grep -n '**Status:**' feature-developments/scheduling\ gaps/gap-04-state-machine-not-enforced.md`.

---

## TESTING STRATEGY

Three-tier per `tech.md` + `spec-testing-standards.md`, plus a Hypothesis property test per `spec-testing-standards.md` §1.

### Unit Tests (`@pytest.mark.unit`)

File: `src/grins_platform/tests/unit/test_appointment_state_machine.py` (new).

- `@validates` hook: same-status no-op, valid transition, invalid transition raises, initial-insert bypass.
- Dict 4.B edge + skip-to-complete edges.
- Repository guard on both `update(data)` and `update_status()`.
- `transition_to()` happy path + audit-failure-swallowing.
- Hypothesis property: `can_transition_to(next) ⇔ next in VALID_APPOINTMENT_TRANSITIONS[current]` for all `(current, next)` pairs.

Coverage target: 90%+ on the new lines in `models/appointment.py` and `repositories/appointment_repository.py` (per `spec-quality-gates.md`).

### Functional Tests (`@pytest.mark.functional`)

File: `src/grins_platform/tests/functional/test_appointment_state_machine_functional.py` (new).

- `reschedule_for_request` from `CONFIRMED` → `SCHEDULED` against a real DB row (covers the full service+repo+model path; covers T1 4.B and T4 repo guard simultaneously).
- `update_status(NO_SHOW)` from `SCHEDULED` raises (the dict does not permit this edge).

### Integration Tests (`@pytest.mark.integration`)

File: `src/grins_platform/tests/integration/test_combined_status_flow_integration.py` (existing — extend).

- End-to-end golden path `SCHEDULED → CONFIRMED → EN_ROUTE → IN_PROGRESS → COMPLETED` on a real `Appointment` instance.
- Negative: `COMPLETED → SCHEDULED` raises `InvalidStatusTransitionError`.

### Edge Cases (explicit enumeration)

- **Initial insert** (`self.status is None`): validator must accept any value. Tested.
- **Same-status idempotent set** (repeat Y, repeat C): validator must accept. Tested.
- **SQL `update(..., status=X)` path bypassing `@validates`**: repo guard catches it. Tested at unit + functional level.
- **Mocked appointment in existing tests** (`Mock().status = ...`): `@validates` does not fire on `Mock`. No existing tests break — audited: all 28+ test files use `Mock`/`MagicMock` for `Appointment`.
- **Legacy row with an unexpected status** (e.g. pre-migration data): `VALID_APPOINTMENT_TRANSITIONS.get(self.status, [])` returns `[]`, and any transition from it will raise. This is the correct behaviour — such rows should be surfaced, not silently re-assigned.
- **Audit write fails during `transition_to`**: swallowed; the transition itself commits. Tested.

---

## VALIDATION COMMANDS

Execute every command to ensure zero regressions and 100% feature correctness.

### Level 1: Syntax & Style

```bash
uv run ruff check --fix src/grins_platform/models/appointment.py \
                       src/grins_platform/repositories/appointment_repository.py \
                       src/grins_platform/services/conflict_resolution_service.py \
                       src/grins_platform/tests/unit/test_appointment_state_machine.py \
                       src/grins_platform/tests/functional/test_appointment_state_machine_functional.py \
                       src/grins_platform/tests/integration/test_combined_status_flow_integration.py
uv run ruff format src/grins_platform/models/appointment.py \
                   src/grins_platform/repositories/appointment_repository.py \
                   src/grins_platform/services/conflict_resolution_service.py \
                   src/grins_platform/tests/unit/test_appointment_state_machine.py \
                   src/grins_platform/tests/functional/test_appointment_state_machine_functional.py
```

### Level 2: Type Checking

```bash
uv run mypy src/grins_platform/models/appointment.py \
            src/grins_platform/repositories/appointment_repository.py \
            src/grins_platform/services/conflict_resolution_service.py
uv run pyright src/grins_platform/models/appointment.py \
               src/grins_platform/repositories/appointment_repository.py \
               src/grins_platform/services/conflict_resolution_service.py
```

### Level 3: Unit Tests

```bash
uv run pytest src/grins_platform/tests/unit/test_appointment_state_machine.py -v --tb=short
uv run pytest src/grins_platform/tests/unit/ -v -m unit            # regression check
uv run pytest src/grins_platform/tests/unit/test_appointment_state_machine.py \
  --cov=src/grins_platform/models/appointment \
  --cov=src/grins_platform/repositories/appointment_repository \
  --cov-report=term-missing
```

### Level 4: Functional + Integration Tests

```bash
uv run pytest src/grins_platform/tests/functional/test_appointment_state_machine_functional.py -v -m functional
uv run pytest src/grins_platform/tests/integration/test_combined_status_flow_integration.py -v -m integration
uv run pytest src/grins_platform/tests/ -v            # full test suite regression check
```

### Level 5: Manual Validation

```bash
# 1. Golden path: /on-my-way works on a SCHEDULED appointment.
curl -X POST http://localhost:8000/api/v1/jobs/<job-id>/on-my-way -H "Authorization: Bearer <token>"
# 2. Skip-to-complete: /complete works on a SCHEDULED appointment (tests new edge).
curl -X POST http://localhost:8000/api/v1/jobs/<job-id>/complete -H "Authorization: Bearer <token>"
# 3. Webhook path: simulate an inbound Y reply on a SCHEDULED appointment.
curl -X POST http://localhost:8000/webhooks/sms -d '{"Body":"Y","From":"+19527373312",...}'
# 4. Confirm the audit log row is written after transition_to() (if migrated a call site).
psql $DATABASE_URL -c "SELECT action, details FROM audit_logs WHERE action='appointment.status.transition' ORDER BY created_at DESC LIMIT 5;"
```

### Level 6: Full Quality Gate (must pass with zero errors)

```bash
uv run ruff check --fix src/ && uv run ruff format src/ \
  && uv run mypy src/ && uv run pyright src/ \
  && uv run pytest -v
```

---

## ACCEPTANCE CRITERIA

- [ ] `VALID_APPOINTMENT_TRANSITIONS["confirmed"]` contains `"scheduled"` with an inline comment referencing `reschedule_for_request`.
- [ ] `VALID_APPOINTMENT_TRANSITIONS["scheduled"]` and `VALID_APPOINTMENT_TRANSITIONS["confirmed"]` contain `"completed"` (preserves `/jobs/{id}/complete`).
- [ ] `Appointment._validate_status_transition` exists and raises `InvalidStatusTransitionError` on an illegal edge.
- [ ] `Appointment._validate_status_transition` is a no-op on `self.status is None` (initial insert) and on `new_status == self.status` (idempotent).
- [ ] `AppointmentRepository.update()` and `update_status()` reject illegal transitions before issuing the SQL UPDATE.
- [ ] `AppointmentRepository._validate_status_transition_or_raise` does NOT raise when the row is missing — lets the existing `returning(Appointment) → None` path handle not-found.
- [ ] `Appointment.transition_to(session, new_status, *, actor_id, reason)` exists, changes status, writes an `AuditLog` row with `action="appointment.status.transition"`, and swallows audit-write failures via log-only.
- [ ] `ConflictResolutionService.cancel_appointment` and `reschedule_appointment` short-circuit on `is_terminal_status()` before mutating.
- [ ] `AppointmentService.update_appointment` (line 492) and `reschedule` (line 1077) forced-reset branches narrow their inner `if` so EN_ROUTE/IN_PROGRESS/COMPLETED/NO_SHOW pre-states are skipped.
- [ ] `gap-04-state-machine-not-enforced.md` Status line updated to `Fixed in …`.
- [ ] New unit + functional + integration tests present and pass.
- [ ] Zero ruff / mypy / pyright errors.
- [ ] Full existing test suite (`uv run pytest -v`) passes with no new failures.
- [ ] Coverage on new code ≥ 90%.
- [ ] DEVLOG.md entry prepended.
- [ ] No regressions observed in manual validation of the three API endpoints (`/complete`, `/on-my-way`, `/started`).
- [ ] Pre-flight import cycle check (T0) prints `imports-ok`.

---

## COMPLETION CHECKLIST

- [ ] All tasks T0, T1, T2, T3, T4, T5A, T5B, T6, T7, T8, T9, T10 executed in order.
- [ ] Each task's `VALIDATE` command passed before moving on.
- [ ] Level 1–6 validation commands all pass.
- [ ] Unit + functional + integration + Hypothesis tests all pass.
- [ ] No linting, type-checking, or test errors.
- [ ] Manual validation confirms the three API endpoints still work.
- [ ] Acceptance criteria all checked.
- [ ] DEVLOG and gap-04 status lines updated.
- [ ] Commit message prefixed `fix(gap-04):` and body references both 4.A and 4.B.

---

## NOTES

### Why two enforcement layers instead of one

`@validates` on the model is the ergonomic place to put the rule — any `appt.status = X` ORM attribute set runs through it. But SQLAlchemy's `Session.execute(sqlalchemy.update(Appointment).values(status=X))` path, which is what `AppointmentRepository.update()` and `update_status()` use, completely bypasses `@validates`. Without the repo guard, the existing `reschedule_for_request` and `send_confirmation` paths would slip through the validator and the whole plan would be decorative. The guard is a single extra `SELECT status FROM appointments WHERE id = :id` — cheap, and only runs when `"status"` is in the update payload.

### Why not switch to `session.merge()` or pure ORM?

Both would move every `update()` call through the ORM's attribute-set instrumentation and trigger `@validates`. But: (a) it flips the semantics for the `updated_at` `onupdate=func.now()` server default, (b) `merge()` has different relationship-cascading behaviour that could impact the `rescheduled_from_id` self-reference at `appointment.py:159-162`, and (c) it's a much larger diff with nothing gained over the explicit guard. Keep the two-layer approach.

### Why add `SCHEDULED → COMPLETED` and `CONFIRMED → COMPLETED` edges

Three API endpoints (`/complete`, `/on-my-way`, `/started` at `jobs.py:1148, 1329, 1386`) transition appointments directly based on job-level actions. `/complete` specifically allows skipping `IN_PROGRESS` (line 1143-1146 accepts any non-terminal source). Without adding these edges, turning on `@validates` breaks the job-completion flow on any appointment that never went through `IN_PROGRESS` (a common case — the admin just hit "Complete" on a still-scheduled job). The precedent is `JobService.VALID_TRANSITIONS[TO_BE_SCHEDULED] ∋ COMPLETED` per bughunt M-1 (see `test_job_service_transitions.py:22`). Same rationale, mirrored at the appointment layer.

### Test Infrastructure Constraint (important)

The repo has NO real-DB test infrastructure. Verified via:
- `grep -r 'async_sessionmaker|create_async_engine|TEST_DATABASE_URL' src/grins_platform/tests/` → zero hits.
- `tests/conftest.py` (460+ lines) only provides MagicMock/AsyncMock fixtures — no `session` fixture that yields a real `AsyncSession`.
- `tests/integration/conftest.py` wildcard-imports from `tests/integration/fixtures.py`, which exclusively constructs MagicMock fixtures.
- Every "functional" test in the suite (24 files) uses `AsyncMock` for repositories and `MagicMock` for model instances.

Consequence: **all three test tiers in this plan (unit/functional/integration) use the existing mock-based patterns.** The `@validates` hook is still testable — it fires on any real `Appointment` instance's attribute set, even without a session. The repo guard is testable via a mocked `AsyncSession.execute` side effect. Everything else uses mocks.

### AuditLogRepository signature (verified)

From `repositories/audit_log_repository.py:37-47`:

```python
async def create(
    self,
    action: str,
    resource_type: str,
    resource_id: UUID | str | None = None,
    actor_id: UUID | None = None,
    actor_role: str | None = None,
    details: dict[str, Any] | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AuditLog:
```

Our `transition_to()` call uses:
```python
await AuditLogRepository(session).create(
    action="appointment.status.transition",
    resource_type="appointment",
    resource_id=self.id,
    actor_id=actor_id,
    details={"from_status": old, "to_status": new_status, "reason": reason},
)
```

Verified signature compatibility; all other params default safely.

### CancelAppointmentResponse schema (verified)

From `schemas/conflict_resolution.py:49-56`:

```python
class CancelAppointmentResponse(BaseModel):
    appointment_id: UUID
    cancelled_at: datetime
    reason: str
    waitlist_entry_id: UUID | None = None
    message: str
```

The T5A early-return constructs this shape with `appointment.cancelled_at or datetime.now(timezone.utc)` for `cancelled_at`; all other fields filled.

### Follow-ups deliberately out of scope for this plan

- **gap-05 (audit centralisation)**: migrate all direct `appt.status = X` assignments to `transition_to()` so every state change writes an audit row. This is a mechanical multi-file refactor that blocks on this plan.
- **gap-01.B (EN_ROUTE reschedule guard cleanup)**: simplify `_handle_reschedule`'s `blocked_statuses` check now that `@validates` would catch an EN_ROUTE → SCHEDULED transition. The current check is belt-and-suspenders; it can be simplified but doesn't block correctness.
- **Wider call-site migration**: the remaining direct mutations catalogued in the mutation-site table all become safe once `@validates` + the repo guard are in place. Migrating them to `transition_to()` is a code-hygiene improvement, not a correctness fix.

### Confidence score for one-pass implementation: **10 / 10**

Every assumption in this plan is verified against the actual codebase:
- `can_transition_to` call sites (3 found: 450, 675, 2482) — enumerated.
- `appointment.status` write sites (20 found) — each categorized in the mutation-site table with post-fix status.
- `@validates` codebase precedent — `staff_availability.py:122-165`, confirmed working with SQLAlchemy 2.0 async.
- `InvalidStatusTransitionError` constructor signature — verified.
- `AuditLogRepository.create()` signature — verified.
- `CancelAppointmentResponse` Pydantic model — verified.
- Test infrastructure — confirmed mock-only; `@validates` fires on real `Appointment()` attribute sets without a session.
- Circular import risk — T0 is a pre-flight cycle check; lazy imports used as defence-in-depth.
- DEVLOG.md structure — verified header at line 6, entries prepended below.
- Forced-reset edge case at lines 493/1078 — identified and explicitly fixed in T5B.
- `_is_valid_transition` service helper at line 2476 — already delegates to the dict; no change needed.
