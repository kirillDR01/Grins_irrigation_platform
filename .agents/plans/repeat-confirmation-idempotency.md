# Feature: Repeat Confirmation Idempotency (Gap 02)

This plan is derived from `feature-developments/scheduling gaps/gap-02-repeat-confirmation-idempotency.md`. It is complete, but it is still important to validate documentation and codebase patterns and task sanity before starting. Pay special attention to naming of existing utilities, models, enums, and fixtures — import from the right files (e.g. `AppointmentStatus` lives in `grins_platform.models.enums`; `MessageType.APPOINTMENT_CONFIRMATION_REPLY` already exists and is re-used, **do not invent a new enum value**).

## Feature Description

When a customer replies a second (or Nth) `Y`/`yes`/`confirm` to the same confirmation SMS — because they forgot they already replied, or because the provider redelivered the inbound, or because they want reassurance — `JobConfirmationService._handle_confirm` silently creates another `JobConfirmationResponse(status='confirmed')` row and returns a full auto-reply dict anyway. The transition branch (SCHEDULED → CONFIRMED) is skipped because the appointment is already `CONFIRMED`, so the outbound auto-reply is built from an already-confirmed appt but the caller has no idempotency signal. The customer gets repeat "Your appointment has been confirmed. See you on X at Y!" SMSes (subject to the 60s per-phone throttle), duplicate DB rows pile up, and reliability analytics are wrong.

Compare `_handle_cancel` (lines 561–574 of `job_confirmation_service.py`) which explicitly short-circuits on `appt.status == CANCELLED` with `auto_reply=""` (falsy so `sms_service._try_confirmation_reply` suppresses the outbound send) and a `log_rejected("handle_cancel", reason="already_cancelled", ...)` audit line. `_handle_confirm` has no analogous block.

This feature adds that symmetric short-circuit to `_handle_confirm` with one deliberate design change from the cancel flow: **for repeat-Y we DO send a brief reassurance reply** (not silence). Confirmation is about trust — a customer who texts a second `Y` because they are unsure whether the first landed must get a short acknowledgement, or the doubt compounds. Silence is right for repeat-C (don't re-imply cancellation) but wrong for repeat-Y.

## User Story

As a customer who just confirmed an appointment by SMS
I want a brief acknowledgement if I accidentally reply `Y` twice
So that I know my reply landed and I do not repeatedly text or call support to check.

As an ops / data engineer
I want one authoritative "customer confirmed" record per appointment and a traceable idempotency audit line for repeat replies
So that downstream analytics and reply counts are correct, and so support calls about "did you get my confirmation?" drop.

## Problem Statement

`_handle_confirm` currently:

1. Always writes a fresh `JobConfirmationResponse(status='confirmed')` row on every inbound Y, even when the appointment is already `CONFIRMED`. 
2. Returns a full `auto_reply` built from `_build_confirm_message(appt)` regardless of whether the state actually transitioned, so `sms_service._try_confirmation_reply` sends the same long confirmation SMS again (modulo the 60s per-phone throttle in `_autoreply_suppressed`).
3. Emits no `log_rejected` audit line distinguishing repeat-Y from first-Y, so the log timeline cannot answer "did we accidentally send the confirmation SMS twice?"
4. Does nothing special for the race where two Y webhooks resolve the same thread concurrently — both can observe `status == SCHEDULED`, both transition, and two response rows persist with identical bodies.

The asymmetry vs `_handle_cancel` is the root: the CANCEL handler audits the repeat and suppresses the second SMS; the CONFIRM handler does neither.

## Solution Statement

Mirror the `_handle_cancel` repeat-case pattern in `_handle_confirm`, with three deliberate differences that reflect confirmation-specific semantics:

1. **Short-circuit on `appt.status == CONFIRMED`.** After loading the appointment, if the status is already `CONFIRMED` (or any terminal "not re-confirmable" state, see edge cases below), mark the response as `status='confirmed_repeat'` (a new distinguishing response status, which fits in the existing `VARCHAR(50)` column — no migration needed), stamp `processed_at`, call `log_rejected("handle_confirm", reason="already_confirmed", ...)`, and return a result dict with a **short reassurance** `auto_reply` string and `"dedup": True`.
2. **Send a short reassurance SMS** (not silence). The text deliberately differs from `_build_confirm_message` — shorter, explicit "you're already confirmed", no "state changed" phrasing. Re-use the existing `MessageType.APPOINTMENT_CONFIRMATION_REPLY` for the outbound (no new `MessageType` value, no enum / CHECK-constraint migration). The existing `_autoreply_suppressed` 60s per-phone throttle in `sms_service.py` naturally rate-limits a customer spamming `Y`.
3. **Add a race-safe row-level lock.** Change the `await self.db.get(Appointment, appointment_id)` in `_handle_confirm` to a `SELECT ... FOR UPDATE` on the same row so two concurrent Y webhooks serialize through the status check and the loser sees `CONFIRMED` and takes the short-circuit branch. This closes the "two Y webhooks arrive concurrently → two transitions, two ack SMSes" edge case without a unique constraint on `(appointment_id, reply_keyword, raw_reply_body)` (which would reject legitimate "Y then R then Y" sequences from the same phone).

Also **parallel-fix** the equivalent `_handle_confirm` behaviour for the race-window of *concurrent* first-Ys and add comprehensive repeat-Y unit tests that mirror the existing `TestRepeatCancelIsNoOp` class structure.

## Feature Metadata

**Feature Type**: Bug Fix + Hardening
**Estimated Complexity**: Low
**Primary Systems Affected**:
- Backend service: `JobConfirmationService._handle_confirm` (primary)
- Tests: unit (`test_job_confirmation_service.py`) + one functional slice
- No schema migration, no enum changes, no API changes, no frontend changes

**Dependencies**: No new libraries. Uses existing SQLAlchemy 2.x async (`with_for_update`), pytest-asyncio, existing `LoggerMixin`.

---

## CONTEXT REFERENCES

### Relevant Codebase Files — IMPORTANT: READ THESE BEFORE IMPLEMENTING

- `src/grins_platform/services/job_confirmation_service.py` (lines 233–280) — `_handle_confirm` — the primary insertion point. Currently does unconditional transition-gated write. Mirror the `_handle_cancel` repeat block from lines 561–574 here.
- `src/grins_platform/services/job_confirmation_service.py` (lines 543–627) — `_handle_cancel` — the reference pattern. Lines 561–574 are the exact already-cancelled short-circuit to mirror (with the two deliberate deltas: non-empty auto_reply, `confirmed_repeat` response status).
- `src/grins_platform/services/job_confirmation_service.py` (lines 186–227) — `handle_confirmation` — the dispatcher that pre-creates the `JobConfirmationResponse(status='pending')` row before calling `_handle_confirm`. No change required, but understand that the response row exists before the short-circuit runs so our short-circuit mutates an existing row (not creates a new one). This preserves the audit-row-per-inbound invariant.
- `src/grins_platform/services/job_confirmation_service.py` (lines 256–280) — `_build_confirm_message` — the current first-Y reply builder. Leave untouched and do NOT reuse it for repeat-Y; write a new, shorter `_build_confirm_reassurance_message` helper alongside it.
- `src/grins_platform/services/sms_service.py` (lines 895–1038) — `_try_confirmation_reply` — the caller. Confirm the `if auto_reply:` guard at line 979 (falsy suppresses send); our non-empty reassurance auto_reply will flow through `send_message(..., message_type=MessageType.APPOINTMENT_CONFIRMATION_REPLY, ...)` at line 989. Note the `_autoreply_suppressed` check at line 980 (60s per-phone throttle, Gap 07.C circuit breaker) — this is our rate-limit; no new rate-limit helper needed.
- `src/grins_platform/services/sms_service.py` (line 747) — `_autoreply_suppressed` — reference only; no change required. Provides the rate-limit guarantee called out as a "Key design choice" in the gap doc.
- `src/grins_platform/models/job_confirmation.py` (lines 27–100) — `JobConfirmationResponse` model. `status` is `String(50)` so `'confirmed_repeat'` (16 chars) fits — **no migration required**. Verify by reading lines 64–71.
- `src/grins_platform/models/enums.py` (lines 162–177) — `AppointmentStatus` values: `PENDING, DRAFT, SCHEDULED, CONFIRMED, EN_ROUTE, IN_PROGRESS, COMPLETED, CANCELLED, NO_SHOW`. Short-circuit triggers on `CONFIRMED` primarily; see **Edge Case #2** for EN_ROUTE/IN_PROGRESS/COMPLETED handling.
- `src/grins_platform/models/enums.py` (lines 716–744) — `MessageType` — `APPOINTMENT_CONFIRMATION_REPLY` already exists (bughunt M-9). Re-use it; do NOT add a `CONFIRMATION_REASSURANCE` value.
- `src/grins_platform/log_config.py` (lines 214–264) — `LoggerMixin`: `log_started`, `log_rejected(action, reason, **kwargs)`, `log_completed`, `log_failed`. Call `self.log_rejected("handle_confirm", reason="already_confirmed", appointment_id=str(appointment_id))` in the short-circuit branch to match the `_handle_cancel` line 565–569 pattern exactly.
- `src/grins_platform/tests/unit/test_job_confirmation_service.py` (lines 1–140) — test-module imports, `_make_sent_message`, `_make_appointment`, `mock_db` fixture. Re-use verbatim; do NOT duplicate these helpers in a new file.
- `src/grins_platform/tests/unit/test_job_confirmation_service.py` (lines 556–740) — `TestRepeatCancelIsNoOp` class. This is the exact structure to mirror for `TestRepeatConfirmIsIdempotent`. Pay special attention to:
  - `test_handle_cancel_short_circuits_when_already_cancelled` (lines 572–593) — naming + mock setup
  - `test_handle_cancel_does_not_rebuild_message_when_already_cancelled` (lines 597–625) — `monkeypatch.setattr(JobConfirmationService, "_build_cancellation_message", staticmethod(build_mock))` — mirror this exactly for `_build_confirm_message`
  - `test_handle_cancel_still_cancels_from_scheduled` (lines 629–663) — regression test pattern
  - `test_handle_cancel_still_cancels_from_confirmed` (lines 667–720 approx) — second happy-path regression
- `src/grins_platform/tests/functional/test_yrc_confirmation_functional.py` — functional slice (uses real DB). Add a Y,Y repeat test here to prove the SAVEPOINT / row lock behaviour end-to-end against PostgreSQL.
- `instructions/update2_instructions.md` (line 1070) — spec line for repeat-C no-op; document here that the Y rule is intentionally different (reassurance, not silence).
- `CHANGELOG.md` — add a one-line entry under the current unreleased section referencing gap-02 after implementation.

### New Files to Create

None. All changes land in existing files:

- Edit `src/grins_platform/services/job_confirmation_service.py` — add short-circuit + reassurance helper + `with_for_update()` on the appointment fetch.
- Edit `src/grins_platform/tests/unit/test_job_confirmation_service.py` — add `TestRepeatConfirmIsIdempotent` class (append to end of file to minimise diff noise).
- Edit `src/grins_platform/tests/functional/test_yrc_confirmation_functional.py` — add one end-to-end `test_repeat_confirm_is_idempotent` test.
- Edit `CHANGELOG.md` — one-line entry.

No new migration. No new enum value. No new service class.

### Relevant Documentation — READ THESE BEFORE IMPLEMENTING

- SQLAlchemy async `with_for_update`:
  - [SQLAlchemy 2.x Core — `Select.with_for_update`](https://docs.sqlalchemy.org/en/20/core/selectable.html#sqlalchemy.sql.expression.Select.with_for_update) — syntax + caveats when used outside an explicit transaction.
  - Why: the race-safety upgrade changes `db.get(Appointment, id)` to `(select(Appointment).where(...).with_for_update()).scalar_one_or_none()` so two concurrent Y webhooks serialize.
- [SQLAlchemy async best practice: row-level locking inside an `AsyncSession`](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html#synopsis-core) — `with_for_update()` works inside the session transaction opened by the FastAPI dependency; no extra `begin()` required.
- Repo pattern: the codebase already uses `with_for_update()` — check `src/grins_platform/services/appointment_service.py` for examples before implementing.

### Patterns to Follow

**Naming convention (Python, service methods):**

```python
# Private handlers: snake_case with leading underscore, named by keyword.
async def _handle_confirm(self, response, appointment_id) -> dict[str, Any]: ...
async def _handle_cancel(self, response, appointment_id) -> dict[str, Any]: ...

# Private static helpers: snake_case with leading underscore, verb_subject.
@staticmethod
def _build_confirm_message(appt) -> str: ...
@staticmethod
def _build_cancellation_message(appt, job) -> str: ...

# New helper for this feature — place adjacent to _build_confirm_message.
@staticmethod
def _build_confirm_reassurance_message(appt) -> str: ...
```

**Short-circuit pattern (mirror from `_handle_cancel` lines 561–574):**

```python
# _handle_cancel reference — repeat-C is silence:
if appt and appt.status == AppointmentStatus.CANCELLED.value:
    response.status = "cancelled"
    response.processed_at = datetime.now(tz=timezone.utc)
    await self.db.flush()
    self.log_rejected(
        "handle_cancel",
        reason="already_cancelled",
        appointment_id=str(appointment_id),
    )
    return {
        "action": "cancelled",
        "appointment_id": str(appointment_id),
        "auto_reply": "",  # falsy → sms_service._try_confirmation_reply skips send
    }
```

**Short-circuit to ADD in `_handle_confirm` (deliberate deltas: non-empty reassurance, new response status, `dedup` flag):**

```python
if appt and appt.status == AppointmentStatus.CONFIRMED.value:
    response.status = "confirmed_repeat"  # new status — distinguishes repeat from first-Y
    response.processed_at = datetime.now(tz=timezone.utc)
    await self.db.flush()
    self.log_rejected(
        "handle_confirm",
        reason="already_confirmed",
        appointment_id=str(appointment_id),
    )
    return {
        "action": "confirmed",
        "appointment_id": str(appointment_id),
        "auto_reply": self._build_confirm_reassurance_message(appt),
        "dedup": True,  # informational; sms_service does not consume it today
    }
```

**Error handling:** the existing `_handle_confirm` has no try/except — neither should the short-circuit. Follow the pattern: rely on `handle_confirmation`'s caller (`SMSService._try_confirmation_reply`) to catch any `send_message` failures.

**Logging pattern (from `_handle_cancel` + `LoggerMixin`):**

```python
self.log_started("handle_confirmation", thread_id=..., keyword=...)
# ... work ...
self.log_rejected("handle_confirm", reason="already_confirmed", appointment_id=str(appointment_id))
# ... OR on happy path ...
self.log_completed("handle_confirmation", result_action=result.get("action"), appointment_id=str(appointment_id))
```

**Row-level locking pattern:** SQLAlchemy 2.x async, mirrors `appointment_service.py`:

```python
from sqlalchemy import select
from grins_platform.models.appointment import Appointment

stmt = (
    select(Appointment)
    .where(Appointment.id == appointment_id)
    .with_for_update()
)
appt = (await self.db.execute(stmt)).scalar_one_or_none()
```

Replaces the `appt = await self.db.get(Appointment, appointment_id)` line at `_handle_confirm` line 241.

**Test-file patterns (from `test_job_confirmation_service.py`):**

- Reuse `_make_sent_message()`, `_make_appointment(status=...)`, `mock_db` fixture verbatim — do **not** duplicate in a new file.
- Mark every test: `@pytest.mark.unit` + `@pytest.mark.asyncio`.
- Use `AsyncMock` for `db.execute`, `db.flush`, `db.get`; use `MagicMock` for the result object returned from `db.execute` so `.scalar_one_or_none()` is a sync method on an async call.
- For row-lock tests: `db.execute` must now return an appointment for the select-with-for-update query. Either extend `_make_sent_message` path or branch via `side_effect` on the mock. Prefer `side_effect = [message_result_mock, appointment_result_mock]` so the first execute returns the SentMessage and the second returns the Appointment.
- Naming: `test_handle_confirm_short_circuits_when_already_confirmed`, `test_handle_confirm_does_not_rebuild_full_message_when_already_confirmed`, `test_handle_confirm_returns_reassurance_auto_reply_on_repeat`, `test_handle_confirm_still_transitions_from_scheduled` (regression), `test_handle_confirm_marks_response_status_confirmed_repeat`.

---

## IMPLEMENTATION PLAN

### Phase 1: Foundation

Extend the already-confirmed short-circuit contract and add the reassurance message helper. No schema/enum work — deliberately scoped to zero-migration to keep the diff tight.

**Tasks:**

- Add `_build_confirm_reassurance_message(appt)` static helper alongside the existing `_build_confirm_message`.
- Decide final reassurance text (see Phase 2 Task 2). Target ~100–140 chars so it stays single-segment SMS.

### Phase 2: Core Implementation

Add the short-circuit branch in `_handle_confirm` and swap the appointment fetch to `select ... with_for_update()` so concurrent webhooks serialize.

**Tasks:**

- Replace `appt = await self.db.get(Appointment, appointment_id)` with a `select ... with_for_update()` at `_handle_confirm` line 241.
- Insert the repeat-case short-circuit block before the current `if appt and appt.status == SCHEDULED` check.
- Set `response.status = "confirmed_repeat"` in that branch so the inbound row is distinguishable from first-Y rows for analytics.
- Emit `self.log_rejected("handle_confirm", reason="already_confirmed", ...)` matching `_handle_cancel` log pattern.
- Return a dict with `"auto_reply": self._build_confirm_reassurance_message(appt)` and `"dedup": True`.

### Phase 3: Integration

No service wiring changes needed. `sms_service._try_confirmation_reply` already does the right thing:

- Line 979 `if auto_reply:` — a non-empty reassurance string triggers `send_message` with `MessageType.APPOINTMENT_CONFIRMATION_REPLY`.
- Line 980 `_autoreply_suppressed` — 60s per-phone throttle already rate-limits a customer spamming `Y`.
- Line 989 `send_message` — persists a `SentMessage` audit row with `message_type='appointment_confirmation_reply'` so the audit trail distinguishes first-Y reply from reassurance reply (both carry the same MessageType; the distinguishing signal is `JobConfirmationResponse.status='confirmed_repeat'` linked via `sent_message_id`).

**Verify (no code change, just inspection):** that `sms_service._try_confirmation_reply` does not branch on the `dedup` key. Current behaviour: it doesn't. The `dedup: True` in our return dict is purely informational (tests + logs).

### Phase 4: Testing & Validation

Add a full `TestRepeatConfirmIsIdempotent` unit-test class and a single functional slice.

**Tasks:**

- Unit tests (append to `test_job_confirmation_service.py`):
  1. `test_handle_confirm_short_circuits_when_already_confirmed` — `auto_reply` is the reassurance string, `action == 'confirmed'`, `response.status == 'confirmed_repeat'`.
  2. `test_handle_confirm_does_not_rebuild_full_message_when_already_confirmed` — monkeypatch `_build_confirm_message` to assert it is NOT called on repeat.
  3. `test_handle_confirm_does_rebuild_reassurance_message_when_already_confirmed` — monkeypatch `_build_confirm_reassurance_message` to assert it IS called exactly once.
  4. `test_handle_confirm_marks_response_status_confirmed_repeat` — assert `response.status == 'confirmed_repeat'`, `processed_at` is tz-aware UTC.
  5. `test_handle_confirm_returns_dedup_flag_on_repeat` — assert `result.get('dedup') is True`.
  6. `test_handle_confirm_still_transitions_from_scheduled` — regression: first-Y still flips SCHEDULED → CONFIRMED and uses full `_build_confirm_message` text.
  7. `test_handle_confirm_noop_when_appointment_missing` — `db.execute` returns `None` for the appointment; handler must not raise, must still set `response.status = 'confirmed'` (no guard-rail regression).
- Functional test (append to `test_yrc_confirmation_functional.py`):
  1. `test_repeat_confirm_is_idempotent` — create appointment, send first `Y` → assert status → CONFIRMED + one `JobConfirmationResponse(status='confirmed')`. Send second `Y` → assert status stays CONFIRMED, second `JobConfirmationResponse(status='confirmed_repeat')`, exactly two outbound `SentMessage` rows of type `APPOINTMENT_CONFIRMATION_REPLY` (first = full, second = reassurance) OR one if the 60s throttle fires (assert on either, based on time spacing in the test).

---

## STEP-BY-STEP TASKS

Execute every task in order, top to bottom. Each task is atomic and independently testable.

### 1. UPDATE `src/grins_platform/services/job_confirmation_service.py`

- **IMPLEMENT**: Add a new static helper `_build_confirm_reassurance_message(appt)` placed directly after `_build_confirm_message` (after line 280). The function takes the same `appt` argument, formats the date/time via `format_sms_time_12h` (same import path as `_build_confirm_message`), and returns a short reassurance string. Suggested wording:
  ```python
  @staticmethod
  def _build_confirm_reassurance_message(appt: Any | None) -> str:  # noqa: ANN401
      """Build the reassurance SMS for a repeat ``Y`` on an already-confirmed appt.

      Shorter than :meth:`_build_confirm_message` — the customer already received
      the full confirmation on their first Y. This reply exists only to reassure
      them the second Y landed, without re-implying a state change.

      Validates: gap-02.
      """
      from grins_platform.services.sms.formatters import (  # noqa: PLC0415
          format_sms_time_12h,
      )

      appt_date = getattr(appt, "scheduled_date", None) if appt else None
      appt_time = getattr(appt, "time_window_start", None) if appt else None
      date_str = appt_date.strftime("%B %d, %Y") if appt_date else None
      time_str = format_sms_time_12h(appt_time) if appt_time else None

      if date_str and time_str:
          return f"You're already confirmed for {date_str} at {time_str}. See you then!"
      return "You're already confirmed. See you then!"
  ```
- **PATTERN**: Mirrors `_build_confirm_message` at `job_confirmation_service.py:256-280` including the `noqa: ANN401` on `Any` and the `noqa: PLC0415` on the deferred import.
- **IMPORTS**: None new — `format_sms_time_12h` already imported via the deferred pattern used by `_build_confirm_message`.
- **GOTCHA**: Do NOT add a new `MessageType` value. The outbound SMS re-uses `MessageType.APPOINTMENT_CONFIRMATION_REPLY` (set by `sms_service._try_confirmation_reply`). Keep SMS under 160 chars to stay single-segment.
- **VALIDATE**: `ruff check src/grins_platform/services/job_confirmation_service.py` must pass.

### 2. UPDATE `src/grins_platform/services/job_confirmation_service.py`

- **IMPLEMENT**: Replace the `await self.db.get(Appointment, appointment_id)` call at line 241 inside `_handle_confirm` with a `select ... with_for_update()` to serialize concurrent Y webhooks. Exact replacement:
  ```python
  # Was:
  # appt = await self.db.get(Appointment, appointment_id)
  # Now — row-level lock so concurrent Y webhooks serialize through the
  # status check. Without this, two webhooks can both observe
  # ``SCHEDULED`` and both try to transition, creating two response rows
  # with ``status='confirmed'`` (not ``'confirmed_repeat'``).
  stmt = (
      select(Appointment)
      .where(Appointment.id == appointment_id)
      .with_for_update()
  )
  appt = (await self.db.execute(stmt)).scalar_one_or_none()
  ```
- **PATTERN**: `select(...).with_for_update()` pattern from `appointment_service.py` (grep for `with_for_update` to confirm; use an existing callsite as the exact import shape).
- **IMPORTS**: `from sqlalchemy import select` is already imported at line 15 of the file. `Appointment` is already imported inside `_handle_confirm` at line 239 via `from grins_platform.models.appointment import Appointment  # noqa: PLC0415`.
- **GOTCHA**: Do NOT wrap this in a `begin_nested()` SAVEPOINT — the FastAPI session dependency already opens a transaction for the request, which is what `with_for_update` needs. Outside a transaction, `with_for_update` raises `InvalidRequestError`.
- **VALIDATE**: `pytest src/grins_platform/tests/unit/test_job_confirmation_service.py -k "test_handle_confirmation" -x` — existing tests must continue to pass. The test fixtures already stub `db.execute` via `AsyncMock(return_value=result_mock)` which handles both the `find_confirmation_message` select and the new appointment select; existing tests may need `db.get` → `db.execute` adjustments (see Task 8).

### 3. UPDATE `src/grins_platform/services/job_confirmation_service.py`

- **IMPLEMENT**: Insert the already-confirmed short-circuit block inside `_handle_confirm` BEFORE the existing `if appt and appt.status == AppointmentStatus.SCHEDULED.value:` check (line 242 in the current file — after the row-lock fetch from Task 2). Exact block:
  ```python
  # Gap 02 — repeat Y on an already-confirmed appointment. Mirror of the
  # ``_handle_cancel`` short-circuit at job_confirmation_service.py:561-574
  # with two deliberate deltas:
  #   1. ``auto_reply`` is NON-empty — a short reassurance (confirmation
  #      is about trust; silence after a repeat Y reinforces the doubt
  #      that prompted it).
  #   2. ``response.status`` is ``'confirmed_repeat'`` (not plain
  #      ``'confirmed'``) so analytics and support can tell first-Y
  #      apart from repeat-Y rows.
  if appt and appt.status == AppointmentStatus.CONFIRMED.value:
      response.status = "confirmed_repeat"
      response.processed_at = datetime.now(tz=timezone.utc)
      await self.db.flush()
      self.log_rejected(
          "handle_confirm",
          reason="already_confirmed",
          appointment_id=str(appointment_id),
      )
      return {
          "action": "confirmed",
          "appointment_id": str(appointment_id),
          "auto_reply": self._build_confirm_reassurance_message(appt),
          "dedup": True,
      }
  ```
- **PATTERN**: Directly mirrors `_handle_cancel` lines 561–574. Read those lines first, then write this block with the two documented deltas.
- **IMPORTS**: None new.
- **GOTCHA**: The `response` row was created in `handle_confirmation` (line 186–198) BEFORE `_handle_confirm` is called, so this branch mutates an existing row, not creates a new one. Do NOT `self.db.add(response)` here — already done upstream.
- **GOTCHA**: The `'confirmed_repeat'` string is 16 chars, well under `VARCHAR(50)` (see `job_confirmation.py:68-71`). No migration.
- **VALIDATE**: `ruff check src/grins_platform/services/job_confirmation_service.py` + `mypy src/grins_platform/services/job_confirmation_service.py`.

### 4. UPDATE `src/grins_platform/services/job_confirmation_service.py`

- **IMPLEMENT**: Update the `_handle_confirm` docstring to reflect the new short-circuit behaviour. Replace:
  ```python
  """CONFIRM: SCHEDULED → CONFIRMED + auto-reply."""
  ```
  with:
  ```python
  """CONFIRM: SCHEDULED → CONFIRMED + auto-reply.

  Gap 02: a repeat ``Y`` on an already-CONFIRMED appointment short-circuits
  to a reassurance reply (mirror of ``_handle_cancel`` at lines 561-574,
  with a non-empty reassurance ``auto_reply`` instead of silence because
  confirmation is about trust).

  Row-level lock on the appointment fetch serializes concurrent Y
  webhooks so only one can observe ``SCHEDULED`` and transition; the
  loser takes the repeat branch.
  """
  ```
- **PATTERN**: Docstring style from `_handle_reschedule` at lines 290–302 + `_handle_cancel` at line 548.
- **VALIDATE**: `ruff check` + visual diff review for docstring rendering.

### 5. ADD unit tests in `src/grins_platform/tests/unit/test_job_confirmation_service.py`

- **IMPLEMENT**: Append a new class `TestRepeatConfirmIsIdempotent` at the end of the file, mirroring `TestRepeatCancelIsNoOp` (lines 556–720 approx). Include at minimum:
  - `test_handle_confirm_short_circuits_when_already_confirmed`
  - `test_handle_confirm_does_not_rebuild_full_message_when_already_confirmed` (monkeypatch `_build_confirm_message` → assert not called)
  - `test_handle_confirm_does_rebuild_reassurance_message_when_already_confirmed` (monkeypatch `_build_confirm_reassurance_message` → assert called once)
  - `test_handle_confirm_marks_response_status_confirmed_repeat`
  - `test_handle_confirm_returns_dedup_flag_on_repeat` — asserts `result.get('dedup') is True`
  - `test_handle_confirm_still_transitions_from_scheduled` (regression; happy path)
  - `test_handle_confirm_reassurance_message_contains_date_and_time` (content assertion on the reassurance text)
- **PATTERN**: Exact structure from `TestRepeatCancelIsNoOp` (`test_job_confirmation_service.py:556-720`). Re-use `_make_sent_message`, `_make_appointment(status=AppointmentStatus.CONFIRMED.value)`, and the `mock_db` fixture from the top of the file.
- **IMPORTS**: All already imported at the top of the file: `AppointmentStatus`, `ConfirmationKeyword`, `JobConfirmationService`, `AsyncMock`, `MagicMock`, `Mock`, `pytest`, `datetime`, `timezone`, `uuid4`.
- **GOTCHA**: Since Task 2 swapped `db.get` → `db.execute(select(Appointment).with_for_update())` for the appointment fetch, the mock now needs two `db.execute` calls (one for the SentMessage lookup, one for the Appointment). Use `mock_db.execute = AsyncMock(side_effect=[sent_result, appt_result])` where each is a `MagicMock` with `.scalar_one_or_none.return_value` set appropriately.
- **GOTCHA**: `_handle_cancel` tests still use `mock_db.get = AsyncMock(...)` for the Appointment fetch. **Do NOT retrofit cancel tests** in this task — scope stays tight to `_handle_confirm`. If any cancel test breaks because of a shared fixture change, note it and handle in Task 8.
- **VALIDATE**: `pytest src/grins_platform/tests/unit/test_job_confirmation_service.py::TestRepeatConfirmIsIdempotent -v` — all tests pass.

### 6. ADD functional test in `src/grins_platform/tests/functional/test_yrc_confirmation_functional.py`

- **IMPLEMENT**: Add `test_repeat_confirm_is_idempotent` — create appointment → send first Y (real service stack, real PostgreSQL) → send second Y → assert:
  - `appointment.status == CONFIRMED` (unchanged from first Y)
  - Exactly 2 `JobConfirmationResponse` rows for this appointment: first with `status='confirmed'`, second with `status='confirmed_repeat'`
  - At least 1 (up to 2 depending on throttle) `SentMessage` rows with `message_type=APPOINTMENT_CONFIRMATION_REPLY` — if the test sleeps < 60s between Ys, only 1 outbound (throttle hit); if the test mocks out the throttle, 2 outbounds (first = full, second = reassurance).
  - Reassurance message text matches the `_build_confirm_reassurance_message` output (assert substring `"already confirmed"`).
- **PATTERN**: Follow existing functional-test patterns in `test_yrc_confirmation_functional.py`. If this file already has a `test_confirm_transitions_scheduled_to_confirmed`, place the new test directly after it.
- **IMPORTS**: Match the existing file's import block.
- **GOTCHA**: Functional tests may run against real Postgres — `with_for_update` requires an active transaction. Confirm the test fixture opens a session; reuse the fixture, do not invent a new one.
- **GOTCHA**: If the throttle is active in the functional environment, the second outbound may be suppressed. Either (a) bypass the throttle via a test-fixture flag, (b) sleep 61s (slow test — avoid), or (c) assert "first outbound present + log line 'auto_reply_suppressed' present for second" — prefer (a).
- **VALIDATE**: `pytest src/grins_platform/tests/functional/test_yrc_confirmation_functional.py::test_repeat_confirm_is_idempotent -v` — test passes against the functional test DB.

### 7. UPDATE `CHANGELOG.md`

- **IMPLEMENT**: Add a one-line entry under the current unreleased section (follow the existing format for other gap fixes):
  ```markdown
  - fix(gap-02): repeat confirmation idempotency — short-circuit ``Y`` on already-confirmed appointments with a reassurance reply, mirroring the repeat-``C`` no-op. Row-level lock closes the concurrent-webhook race.
  ```
- **PATTERN**: Check the most recent commits in `git log --oneline -20` and the current CHANGELOG.md top section for phrasing style (e.g. `fix(gap-06)`, `feat(gap-07)`).
- **VALIDATE**: Visual inspection + `git diff CHANGELOG.md`.

### 8. UPDATE existing `_handle_cancel` tests IF they break after Task 2

- **IMPLEMENT**: If the Task-2 row-lock change for `_handle_confirm` (but NOT `_handle_cancel`) accidentally broke any existing test due to shared fixture interference, audit and repair.
- **VALIDATE**: `pytest src/grins_platform/tests/unit/test_job_confirmation_service.py -v` — full file green.
- **GOTCHA**: `_handle_cancel` still uses `db.get(Appointment, ...)` so its tests should be unaffected. Only `_handle_confirm` tests that relied on `db.get` for the appointment need adjusting (if any). The existing `TestHandleConfirmation` cases may need `db.execute` side_effect extensions.

### 9. RUN full validation suite

- **IMPLEMENT**: Execute all commands in **VALIDATION COMMANDS** below, top to bottom, fixing any issues before moving on.
- **VALIDATE**: All commands exit 0.

---

## TESTING STRATEGY

### Unit Tests

Scope: pure-Python behaviour of `_handle_confirm` and `_build_confirm_reassurance_message` with mocked `AsyncSession`. Target ≥95% line coverage on the new code paths.

Approach: append to `src/grins_platform/tests/unit/test_job_confirmation_service.py`, re-using the module-scoped `_make_sent_message`, `_make_appointment`, and `mock_db` fixtures. Mirror `TestRepeatCancelIsNoOp` exactly for structure, assertions, and monkeypatching style.

### Integration / Functional Tests

Scope: end-to-end verification against a real PostgreSQL backend that the `SELECT ... FOR UPDATE` actually locks the row and that `JobConfirmationResponse(status='confirmed_repeat')` persists with the correct FK linkage.

Approach: add one test to `src/grins_platform/tests/functional/test_yrc_confirmation_functional.py` that sends two Y webhooks via the existing functional harness.

### Edge Cases to Test Explicitly

1. **Y → Y** (happy path for this feature) — first transitions, second short-circuits with reassurance. Covered by Unit #1, #5 and Functional #1.
2. **Y → R → Y** — first Y transitions SCHEDULED → CONFIRMED; R creates an open RescheduleRequest but DOES NOT change appointment status (verify in `_handle_reschedule` at lines 282–404 — it only creates a RescheduleRequest); the second Y sees status=CONFIRMED and short-circuits with reassurance. Document this explicitly — the gap doc raises it as edge case #1 and proposes re-confirming, but the correct behaviour given the current state machine is "reassure + leave the open RescheduleRequest alone" (admin handles the reschedule resolution). If product wants "Y after R closes the open RescheduleRequest", that is a separate feature — out of scope here. Add a unit test `test_handle_confirm_reassures_when_reschedule_is_open` that asserts: response.status='confirmed_repeat', RescheduleRequest row untouched.
3. **Y on EN_ROUTE / IN_PROGRESS / COMPLETED / NO_SHOW** — currently the state-gated branch silently skips, and after this fix the appointment is NOT `CONFIRMED` so the new short-circuit ALSO does not fire → we fall through to the bottom of `_handle_confirm` which sets `response.status = 'confirmed'` without transitioning. This is the pre-feature behaviour and is acceptable (arguably correct: EN_ROUTE means the tech is already coming; "confirmed" is still truthful). **Do not expand the short-circuit to these states in this feature** — scope creep. Add a unit test `test_handle_confirm_no_transition_from_terminal_states_sets_confirmed` that documents the intended no-op behaviour.
4. **Y when appointment row is deleted** — `db.execute(select(...).with_for_update()).scalar_one_or_none()` returns None; the handler falls through to the existing branch which sets `response.status='confirmed'` and builds a generic reply. Covered by Unit #7.
5. **Y,Y concurrent webhooks** — both arrive inside overlapping transactions. The `FOR UPDATE` serializes them: first transitions (SCHEDULED → CONFIRMED, response #1 = 'confirmed'), second blocks until the first commits, then sees CONFIRMED and short-circuits (response #2 = 'confirmed_repeat'). Covered by Functional #1 (if the test can simulate concurrency; otherwise document with a property test or skip-but-note).
6. **Rate-limited reassurance** — second Y arrives within 60s, `_autoreply_suppressed` fires, no outbound SMS sent, but response row still persists with `status='confirmed_repeat'`. Assert in the functional test that the `sms.confirmation.auto_reply_suppressed` log line is emitted when appropriate.

---

## VALIDATION COMMANDS

Execute every command. Each must exit 0 with zero new regressions.

### Level 1: Syntax & Style

```bash
ruff check src/grins_platform/services/job_confirmation_service.py
ruff check src/grins_platform/tests/unit/test_job_confirmation_service.py
ruff check src/grins_platform/tests/functional/test_yrc_confirmation_functional.py
ruff format --check src/grins_platform/services/job_confirmation_service.py
mypy src/grins_platform/services/job_confirmation_service.py
```

### Level 2: Unit Tests (new + regression)

```bash
# New repeat-Y suite
pytest src/grins_platform/tests/unit/test_job_confirmation_service.py::TestRepeatConfirmIsIdempotent -v

# Full JobConfirmationService unit tests (regression)
pytest src/grins_platform/tests/unit/test_job_confirmation_service.py -v

# Property-based reply-parser tests (regression — must stay green)
pytest src/grins_platform/tests/unit/test_pbt_yrc_keyword_parser.py -v
```

### Level 3: Integration / Functional Tests

```bash
# Functional YRC flow (new test + regression)
pytest src/grins_platform/tests/functional/test_yrc_confirmation_functional.py -v

# Combined status-flow integration
pytest src/grins_platform/tests/integration/test_combined_status_flow_integration.py -v
```

### Level 4: Manual Validation

1. **Local run, two Y replies:**
   ```bash
   docker compose -f docker-compose.dev.yml up -d postgres redis
   uv run uvicorn grins_platform.main:app --reload --port 8000
   # In another terminal: seed an appointment + send a confirmation SMS via the admin endpoint
   # Then simulate two inbound Y webhooks 5s apart via the callrail_webhooks endpoint
   curl -X POST http://localhost:8000/api/v1/webhooks/callrail/inbound -H 'content-type: application/json' \
     -d '{"from":"+19527373312","to":"+1...","body":"Y","thread_id":"thread-abc","sid":"sid-1"}'
   curl -X POST http://localhost:8000/api/v1/webhooks/callrail/inbound -H 'content-type: application/json' \
     -d '{"from":"+19527373312","to":"+1...","body":"yes","thread_id":"thread-abc","sid":"sid-2"}'
   ```
   **IMPORTANT:** per `~/.claude/.../memory/feedback_sms_test_number.md`, only `+19527373312` may receive real SMS during testing/debugging.
2. **DB inspection:**
   ```sql
   SELECT id, reply_keyword, status, raw_reply_body, received_at
   FROM job_confirmation_responses
   WHERE appointment_id = '<id>'
   ORDER BY received_at;
   -- Expect 2 rows: first status='confirmed', second status='confirmed_repeat'.

   SELECT id, message_type, body, created_at
   FROM sent_messages
   WHERE appointment_id = '<id>' AND message_type = 'appointment_confirmation_reply'
   ORDER BY created_at;
   -- Expect 1 (throttled) or 2 (full + reassurance) rows depending on spacing.
   ```
3. **Log inspection:** grep the server log for `handle_confirm_rejected` with `reason=already_confirmed` — it must be present for the second webhook.

### Level 5: Regression Surface Check (Optional but Recommended)

```bash
# Run the full backend test suite to catch any incidental breakage in related
# paths (SMS service, webhook handler, appointment service).
pytest src/grins_platform/tests -x -q
```

---

## ACCEPTANCE CRITERIA

- [ ] A repeat `Y` on a CONFIRMED appointment does NOT call `_build_confirm_message` (verified by monkeypatch).
- [ ] A repeat `Y` DOES call `_build_confirm_reassurance_message` exactly once (verified by monkeypatch).
- [ ] The repeat-Y `JobConfirmationResponse` row persists with `status='confirmed_repeat'` and non-null `processed_at`.
- [ ] The repeat-Y return dict contains `"dedup": True`, `"action": "confirmed"`, and a non-empty `"auto_reply"` (reassurance text).
- [ ] The first-Y happy path (SCHEDULED → CONFIRMED) is unchanged in behaviour and auto-reply wording.
- [ ] A `log_rejected("handle_confirm", reason="already_confirmed", ...)` line is emitted on every repeat-Y.
- [ ] Concurrent Y webhooks serialize via `with_for_update`: one transitions, the other short-circuits. Verified by the functional test.
- [ ] 60s per-phone throttle in `sms_service._autoreply_suppressed` naturally suppresses rapid-fire reassurances without additional code.
- [ ] All Level 1 / 2 / 3 validation commands exit 0.
- [ ] `CHANGELOG.md` has a one-line gap-02 entry.
- [ ] No new migration file. No new `MessageType` or enum value. No new service class. No frontend changes.
- [ ] No regression in existing `TestHandleConfirmation`, `TestRepeatCancelIsNoOp`, or property-based reply-parser tests.

---

## COMPLETION CHECKLIST

- [ ] All 9 tasks completed in order
- [ ] Each task's VALIDATE command passed before moving on
- [ ] All Level 1–3 validation commands executed successfully
- [ ] Manual Level 4 validation run against local dev stack (optional but strongly encouraged before opening PR)
- [ ] Unit-test coverage on new code paths ≥ 95%
- [ ] No ruff / mypy warnings introduced
- [ ] CHANGELOG entry added
- [ ] Branch created from `dev`, commit message follows repo convention (`fix(gap-02): ...`)

---

## NOTES

### Scope decisions (what is NOT in this plan)

- **No new `MessageType.CONFIRMATION_REASSURANCE` value.** Gap doc proposes it; this plan rejects it to avoid a schema migration (the `sent_messages.message_type` CHECK constraint would need widening). Re-using `APPOINTMENT_CONFIRMATION_REPLY` is semantically fine — both the first-Y auto-reply and the reassurance reply are "the customer's Y got an acknowledgement". The distinguishing signal lives in `JobConfirmationResponse.status` (`confirmed` vs `confirmed_repeat`), which IS sufficient for analytics.
- **No explicit second-level rate limit.** The existing `_autoreply_suppressed` 60s per-phone throttle in `sms_service.py:747` already handles the "customer spams Y" case. Adding a dedicated `last_sent_within(message_type, appointment_id, minutes)` helper would be scope creep; revisit only if production telemetry shows repeat-Y reassurances exceed expected volume.
- **Y after R does not close the open RescheduleRequest.** Gap doc's edge case #1 proposes this, but it is a behaviour change in the state machine (not an idempotency fix). Keep it separate: the current fix reassures the customer without touching the pending reschedule. An admin still resolves the RescheduleRequest. If the product team wants the "Y cancels a pending R" semantics, file a follow-up.
- **No Postgres unique constraint on `(appointment_id, reply_keyword, raw_reply_body)`.** Gap doc considers this; rejected because a legitimate "Y ... R ... Y" sequence would collide. The row-level lock (Task 2) is the correct concurrency primitive.

### Design decisions

- **Why `"confirmed_repeat"` and not keep `"confirmed"`?** Analytics: counting `SELECT COUNT(*) FROM job_confirmation_responses WHERE status='confirmed'` as "unique customer confirmations per appointment" currently double-counts. The new status makes the query correct without requiring a `DISTINCT ON (appointment_id)` rewrite.
- **Why send reassurance, not silence (unlike `_handle_cancel`)?** Confirmation is about trust. A customer texting `Y` twice is likely uncertain the first landed. Silence reinforces uncertainty. Cancellation is final — a repeat `C` does not need another "confirmed cancelled" SMS.
- **Why `with_for_update` and not optimistic concurrency?** The transition is a single status column assignment; the win/lose semantics are clear (first writer wins, loser sees CONFIRMED and short-circuits). `FOR UPDATE` is the simplest primitive that achieves this. Optimistic concurrency with a `version` column would be over-engineering for a single field.
- **Why no functional unique index?** A partial unique index on `(appointment_id) WHERE status='confirmed'` on `job_confirmation_responses` would reject the *second* response row. That's wrong — the row is an audit trail entry, not a state record. We DO want the second row; what we don't want is the second status transition.

### Confidence score

**Confidence: 9/10** for one-pass success.

Reasoning for the deduction:
- The row-level-lock change (Task 2) requires that existing `TestHandleConfirmation` unit tests that mock `db.get` continue to pass after being migrated to `db.execute` side_effect. Task 8 catches this, but the exact number of touched tests is unknown until the edit runs.
- Functional test concurrency simulation is harness-dependent; the test may need to use a threaded subtest to truly prove serialization. If the harness runs sequentially by default, a comment + skip for true-concurrency is acceptable.

All other surface area is mechanical pattern-mirroring of `_handle_cancel` / `TestRepeatCancelIsNoOp`.
