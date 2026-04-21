# Gap 04 — Appointment State Machine Not Enforced

**Severity:** 3 (medium — latent risk)
**Area:** Backend (models + services)
**Status:** Investigated, not fixed
**Related files:**
- `src/grins_platform/models/appointment.py:29-67` — `VALID_APPOINTMENT_TRANSITIONS`
- `src/grins_platform/models/appointment.py:211-221` — `can_transition_to` (defined, unused)
- `src/grins_platform/services/job_confirmation_service.py:189, 199, 314` — direct status assignments
- `src/grins_platform/services/appointment_service.py:1181-1189, 1194` — `reschedule_for_request` direct update
- `src/grins_platform/services/conflict_resolution_service.py:78, 145` — direct CANCELLED assignment

---

## Summary

The appointment state machine is described declaratively in `VALID_APPOINTMENT_TRANSITIONS` (a dict mapping status → allowed next statuses) and a `can_transition_to()` helper exists on the model. But **no code path calls `can_transition_to()` before mutating `appointment.status`**. Every service that changes status does so via direct assignment, bypassing the declared state machine.

Two symptomatic gaps:

- **4.A:** Direct mutations happen everywhere (`_handle_confirm`, `_handle_cancel`, `reschedule_for_request`, `conflict_resolution_service`) without validation. If a service sets an invalid transition, nothing catches it at runtime.
- **4.B:** The `CONFIRMED → SCHEDULED` transition that `reschedule_for_request` performs is **not listed** in `VALID_APPOINTMENT_TRANSITIONS`. Spec-valid, but undocumented in code. A future dev reading the dict would conclude CONFIRMED → SCHEDULED is disallowed and refuse to write the reschedule-from-request flow.

---

## 4.A — `can_transition_to` is declared but never called

### Current behavior

`models/appointment.py:211-221`:

```python
def can_transition_to(self, new_status: str) -> bool:
    """Check if appointment can transition to the given status."""
    valid_transitions = VALID_APPOINTMENT_TRANSITIONS.get(self.status, [])
    return new_status in valid_transitions
```

Grep for `can_transition_to` across the repo → **zero call sites**. The method is dead code.

Meanwhile, these sites all mutate `appointment.status` directly with no validation:

| File:line | Mutation | Source state | Target state |
|---|---|---|---|
| `job_confirmation_service.py:199` | `appt.status = AppointmentStatus.CONFIRMED.value` | Assumed SCHEDULED | CONFIRMED |
| `job_confirmation_service.py:314` | `appt.status = AppointmentStatus.CANCELLED.value` | Assumed SCHEDULED/CONFIRMED | CANCELLED |
| `appointment_service.py:1181-1189` (repo update dict) | `"status": AppointmentStatus.SCHEDULED.value` | CONFIRMED or DRAFT/SCHEDULED | SCHEDULED |
| `conflict_resolution_service.py:78, 145` | `appointment.status = AppointmentStatus.CANCELLED.value` | Any | CANCELLED |

SQLAlchemy does not emit any hook on scalar assignment; there's no ORM-level guard. The `can_transition_to` function is purely advisory and not wired.

### Why it's a problem (even though it mostly works today)

- **Invisible brittleness:** if a new service is added that does `appt.status = NO_SHOW` from an arbitrary current state, nothing fails until production data looks weird.
- **Tests can't rely on invariants:** a test that assumes "no appointment ever goes from COMPLETED back to SCHEDULED" is based on the dict, not enforcement.
- **Code review burden:** every PR that touches appointment status has to re-check the dict manually.

### Proposed fix

Two-part:

1. **Enforce in the setter.** Use SQLAlchemy `validates` or a setter method, e.g.:

   ```python
   @validates("status")
   def _validate_status_transition(self, key, new_status):
       if self.status is None:
           return new_status  # initial insert
       if new_status == self.status:
           return new_status  # no-op
       if new_status not in VALID_APPOINTMENT_TRANSITIONS.get(self.status, []):
           raise InvalidStatusTransitionError(
               f"Cannot transition {self.status} → {new_status}"
           )
       return new_status
   ```

   This catches everything at the model layer, regardless of which service is the caller.

2. **Expose a well-named `transition_to` method that audits:**

   ```python
   async def transition_to(self, new_status: str, *, actor_id=None, reason=None):
       old = self.status
       self.status = new_status  # validated by @validates
       # hook point: audit log, state-change event
   ```

   Gradually migrate callers off raw assignment.

### Migration concerns

- Existing production data may contain rows in states the dict wouldn't predict (legacy rows, prior bug patches). The validator should only fire on *transitions*, not on initial load. Using `@validates` on `status` triggers only on assignment after load, not on SELECT.
- Tests need fixtures with explicit `bypass=True` kwarg for test setup where the state machine isn't the subject.

### Edge cases to verify

- Concurrent writers: two coroutines load the same appointment at SCHEDULED, both transition to CONFIRMED (one per Y reply). Both pass validation (SCHEDULED → CONFIRMED is valid). Last writer wins. That's fine — Gap 02 discusses dedup separately.
- Batch updates via `appointment_repository.update(appointment_id, status=...)` do NOT go through the ORM validator — they're a separate code path. Need to audit and either route them through the model or add parallel validation.

---

## 4.B — `CONFIRMED → SCHEDULED` is undocumented

### Summary

`VALID_APPOINTMENT_TRANSITIONS` lists only these outbound edges from CONFIRMED:

```python
"confirmed": [
    "en_route",
    "in_progress",
    "cancelled",
    "no_show",
],
```

But `reschedule_for_request` (the admin-resolves-R path, `appointment_service.py:1086-1217`) resets a CONFIRMED appointment to SCHEDULED:

```python
allowed_statuses = {
    AppointmentStatus.DRAFT.value,
    AppointmentStatus.SCHEDULED.value,
    AppointmentStatus.CONFIRMED.value,  # ← accepted as input
}
# ... later ...
update_data = {
    "scheduled_date": new_date,
    "time_window_start": ...,
    "status": AppointmentStatus.SCHEDULED.value,  # ← force-written regardless of pre-state
}
```

And the spec says reschedule should re-require re-confirmation (`update2_instructions.md:1071`: *"the customer re-confirms with Y/R/C"*).

So CONFIRMED → SCHEDULED is **spec-correct**, **code-implemented**, **undocumented**.

### Why it matters

- A dev debugging "why doesn't the state machine allow this?" might wrongly conclude there's a bug and "fix" it by blocking the transition.
- If/when 4.A's validator is added, this transition will start raising unless the dict is updated.
- Future admin actions that legitimately need CONFIRMED → SCHEDULED (e.g., "un-confirm" button) have no code pattern to follow.

### Proposed fix

Add the transition to the dict:

```python
"confirmed": [
    "scheduled",       # NEW: reschedule-from-request returns to pre-confirm state
    "en_route",
    "in_progress",
    "cancelled",
    "no_show",
],
```

And document the context next to it:

```python
# CONFIRMED → SCHEDULED: triggered by reschedule_for_request when admin resolves
# a customer's R reply by picking a new date. Appointment goes back to awaiting
# re-confirmation. See AppointmentService.reschedule_for_request.
```

### Tests

- `test_can_transition_confirmed_to_scheduled` — asserts the dict allows it.
- `test_reschedule_from_request_from_confirmed` — end-to-end: appointment at CONFIRMED, admin picks new date, appointment lands at SCHEDULED with new date, new confirmation SMS queued.

---

## Cross-references

- **Gap 01.B** — the EN_ROUTE → reschedule rejection uses the same pattern as 4.A (direct status check, no model enforcement). Fixing 4.A makes 1.B's solution cleaner.
- **Gap 05 (audit)** — once transitions are centralized via `transition_to`, the audit log hook is trivially placed there.
