# Feature: Reschedule Request Lifecycle Hardening (Gap 01)

The following plan is derived from `feature-developments/scheduling gaps/gap-01-reschedule-request-lifecycle.md`. It is complete, but it's important that you validate documentation and codebase patterns and task sanity before you start implementing.

Pay special attention to naming of existing utils, types, and models. Import from the right files (e.g. `AlertType` lives in `grins_platform.models.enums`; `AlertRepository` lives in `grins_platform.repositories.alert_repository`).

## Feature Description

The customer-facing reschedule flow (triggered when a customer replies "R" to a confirmation SMS) has three lifecycle defects:

1. **1.A — Duplicate RescheduleRequest rows**: A second "R" for the same appointment creates a second `status='open'` row, producing duplicate queue items that admins cannot resolve together.
2. **1.B — "R" accepted during field-work states**: A customer texting "R" while the tech is already `EN_ROUTE`/`IN_PROGRESS` produces an unresolvable queue entry (the admin resolve endpoint rejects those source statuses) and a misleading "we'll reschedule" auto-reply.
3. **1.C — Free-text alternatives attachment is fragile**: The follow-up SMS asking for "2–3 dates" is sent with `message_type='reschedule_followup'`, but `find_confirmation_message` filters to `APPOINTMENT_CONFIRMATION` only, so replies on the follow-up thread fall through to the orphan path and never attach to the `RescheduleRequest.requested_alternatives`.

This feature closes all three defects with a two-layer defense (application-level idempotency + DB-level partial unique index), a state guard with tailored auto-replies, and broader thread correlation for follow-up capture.

## User Story

As an admin resolving customer reschedule requests
I want one, actionable RescheduleRequest per appointment with state-aware intake and reliable follow-up capture
So that I can resolve customer-initiated reschedules without dead queue items, duplicate rows, or missing alternative-date text.

## Problem Statement

The reschedule lifecycle leaks in three places: (a) it accepts repeated "R" replies without deduplicating, (b) it accepts "R" in states the resolve path refuses, and (c) it correlates follow-up text via the wrong `message_type` filter. The result is duplicate/unresolvable queue entries and silent data loss of customer-provided alternative dates.

## Solution Statement

Fix in three coordinated layers:

- **Service layer (`JobConfirmationService`)**: add an idempotent open-request lookup inside `_handle_reschedule`; add a state guard that rejects `{EN_ROUTE, IN_PROGRESS, COMPLETED, CANCELLED, NO_SHOW}` with state-specific auto-replies and raises a `late_reschedule_attempt` Alert; widen `find_confirmation_message` (or add a sibling) to also match `RESCHEDULE_FOLLOWUP` for thread resolution; keep appending follow-up replies to `requested_alternatives.entries`.
- **Schema layer**: add a partial unique index `WHERE status = 'open'` on `reschedule_requests.appointment_id` as a DB-level safety net.
- **Enum/Alert wiring**: add `AlertType.LATE_RESCHEDULE_ATTEMPT` and a `NotificationService.send_admin_late_reschedule_alert` method mirroring `send_admin_cancellation_alert`.

No frontend changes are required for 1.A or 1.B (the queue already handles one row correctly and the blocked state never creates a row). 1.C is a backend-only correlation fix.

## Feature Metadata

**Feature Type**: Bug Fix + Enhancement (hardening)
**Estimated Complexity**: Medium
**Primary Systems Affected**:
- Backend service: `JobConfirmationService` (reschedule + needs_review paths)
- Backend service: `NotificationService` (new alert type)
- DB schema: `reschedule_requests` (new partial unique index)
- Enums: `AlertType` (new member)
- Tests: unit + integration coverage

**Dependencies**: No new external libraries. Uses existing SQLAlchemy 2.x async, Alembic, pytest-asyncio.

---

## CONTEXT REFERENCES

### Relevant Codebase Files — IMPORTANT: READ THESE BEFORE IMPLEMENTING

- `src/grins_platform/services/job_confirmation_service.py` (lines 238–273) — `_handle_reschedule` — the primary insertion point for idempotency + state guard.
- `src/grins_platform/services/job_confirmation_service.py` (lines 540–608) — `_handle_needs_review` — where the follow-up text is currently appended to `requested_alternatives.entries`; the existing append logic is fine, but correlation (`find_confirmation_message`) is the upstream bug.
- `src/grins_platform/services/job_confirmation_service.py` (lines 614–643) — `find_confirmation_message` — filters to `APPOINTMENT_CONFIRMATION` only; needs widening (or a sibling `find_reschedule_thread`).
- `src/grins_platform/services/job_confirmation_service.py` (lines 399–453) — `_dispatch_admin_cancellation_alert` — mirror this exactly for the new late-reschedule alert dispatch.
- `src/grins_platform/models/job_confirmation.py` (lines 103–172) — `RescheduleRequest` model + `__table_args__`. No model change required (index lives in migration).
- `src/grins_platform/models/alert.py` (full file) — Alert model structure. No change required.
- `src/grins_platform/models/enums.py` (lines 590–598) — `AlertType` enum — add new member here. Also lines 162–177 for `AppointmentStatus` values.
- `src/grins_platform/models/enums.py` (lines 709–738) — `MessageType` enum — `RESCHEDULE_FOLLOWUP` already exists.
- `src/grins_platform/services/notification_service.py` (lines 1154–1278) — `send_admin_cancellation_alert` — exact pattern to mirror for `send_admin_late_reschedule_alert`.
- `src/grins_platform/repositories/alert_repository.py` (lines 45–67) — `AlertRepository.create` — used by the notification helper.
- `src/grins_platform/services/sms_service.py` (lines 770–862) — `_try_confirmation_reply`, outbound auto-reply + follow-up `send_message` calls. The follow-up is persisted with `MessageType.RESCHEDULE_FOLLOWUP` at line 852 — **verify `provider_thread_id` flows onto that row** via `send_message`.
- `src/grins_platform/services/appointment_service.py` (lines 1086–1217) — `reschedule_for_request` — `allowed_statuses` set at 1135–1149. Not directly modified, but the state guard in `_handle_reschedule` must keep this contract intact (admins still only see queue items that are resolvable).
- `src/grins_platform/api/v1/appointments.py` (lines 1037–1105) — `POST /{appointment_id}/reschedule-from-request`. No change required.
- `src/grins_platform/api/v1/callrail_webhooks.py` (lines 30–80, 127–145) — Redis dedup key format `{prefix}:{conversation_id}:{created_at}`, TTL 24h. Context only — no change.
- `src/grins_platform/tests/unit/test_job_confirmation_service.py` (lines 1–470) — existing mock pattern. **Mirror the `AsyncMock` + `MagicMock` fixture style exactly.**
- `src/grins_platform/migrations/versions/20260418_100700_fold_notes_table_into_internal_notes.py` — head migration revision `20260418_100700`; your new migration revises this.
- `src/grins_platform/migrations/versions/20260416_100100_create_alerts_table.py` (lines 1–73) — migration template style (imports, revision/down_revision, op.create_index calls). Mirror this format.
- `frontend/src/features/schedule/components/RescheduleRequestsQueue.tsx` — **no frontend changes required**; documented here so the execution agent knows not to touch it.
- `src/grins_platform/tests/unit/test_reschedule_detection.py` — existing reschedule unit tests; review before adding new ones to avoid duplication.

### New Files to Create

- `src/grins_platform/migrations/versions/20260421_100000_reschedule_request_unique_open_index.py` — partial unique index on `reschedule_requests(appointment_id) WHERE status='open'`.
- `src/grins_platform/tests/unit/test_reschedule_lifecycle.py` — new unit tests covering 1.A idempotency, 1.B state guard + alert, 1.C follow-up correlation. (Alternative: append to `test_job_confirmation_service.py`. See **DECISION** below.)

**DECISION — test file layout**: Add a new file `test_reschedule_lifecycle.py` dedicated to the lifecycle concerns (dedup + state guard + correlation widening). `test_job_confirmation_service.py` is already ~900+ lines; keeping the lifecycle test file separate improves discoverability when a future gap fix needs to reuse fixtures. Import helpers (`_make_sent_message`, `_make_appointment`, `mock_db`) by copying the factory shape rather than sharing via `conftest.py` (existing tests use module-local factories).

### Relevant Documentation — READ BEFORE IMPLEMENTING

- [PostgreSQL partial indexes](https://www.postgresql.org/docs/16/indexes-partial.html) — we need `CREATE UNIQUE INDEX ... WHERE status='open'`.
  - Why: The unique index must be *partial*, not full, so that multiple `resolved`/`cancelled` rows for the same appointment coexist.
- [SQLAlchemy 2.x async session IntegrityError handling](https://docs.sqlalchemy.org/en/20/orm/session_basics.html#saving-new-objects) — pattern for catching `IntegrityError` on flush when the partial-index race fires.
  - Why: Task 3 needs to treat an `IntegrityError` as a dedup hit (another concurrent webhook won the race).
- [Alembic autogenerate vs. manual migrations](https://alembic.sqlalchemy.org/en/latest/autogenerate.html#partial-indexes) — partial indexes typically need `postgresql_where` on `op.create_index`.
  - Why: Task 1's migration must use `postgresql_where=sa.text("status = 'open'")`, not autogenerate, to get the `WHERE` clause.

### Patterns to Follow

Specific patterns extracted from the codebase — mirror exactly, do not invent new shapes.

**Alembic migration header (mirror `20260416_100100_create_alerts_table.py`):**

```python
"""<Short description>.

<Longer context — what motivated the change>.

Revision ID: 20260421_100000
Revises: 20260418_100700
Requirements: gap-01 (reschedule request lifecycle)
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260421_100000"
down_revision: str | None = "20260418_100700"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None
```

**Partial unique index creation (PostgreSQL):**

```python
op.create_index(
    "uq_reschedule_requests_open_per_appointment",
    "reschedule_requests",
    ["appointment_id"],
    unique=True,
    postgresql_where=sa.text("status = 'open'"),
)
```

**Naming conventions:**
- Models: `snake_case` table names, `CamelCase` classes.
- Index names: `idx_<table>_<cols>` for non-unique; `uq_<table>_<cols>[_cond]` for unique.
- Enum values: `SCREAMING_SNAKE_CASE` for the member, lowercase string value (see `AlertType.CUSTOMER_CANCELLED_APPOINTMENT = "customer_cancelled_appointment"`).
- Service internal methods: `_handle_*`, `_dispatch_*`, `_record_*` prefixes.
- Log event names: `<service_domain>.<action>` (e.g., `handle_cancel.admin_notification_failed`). The `LoggerMixin.log_started/log_completed/log_rejected/log_failed` API is the canonical way to emit structured logs (see `JobConfirmationService` and `NotificationService`).

**Error handling / alert dispatch (mirror `_dispatch_admin_cancellation_alert`, lines 399–453 of `job_confirmation_service.py`):**

```python
try:
    customer = await self.db.get(Customer, customer_id)
    if customer is None:
        self.log_rejected(
            "handle_reschedule.late_alert",
            reason="customer_not_found",
            customer_id=str(customer_id),
        )
        return
    notification_svc = NotificationService(email_service=self._build_email_service())
    await notification_svc.send_admin_late_reschedule_alert(
        self.db,
        appointment_id=appointment_id,
        customer_id=customer_id,
        customer_name=customer.full_name,
        scheduled_at=self._resolve_scheduled_at(appt),
        current_status=appt.status,
    )
except Exception as exc:
    self.log_failed(
        "handle_reschedule.late_alert_failed",
        error=exc,
        appointment_id=str(appointment_id),
    )
```

**Alert row persistence (mirror `NotificationService.send_admin_cancellation_alert`, lines 1246–1273):**

```python
try:
    from grins_platform.models.alert import Alert  # noqa: PLC0415
    from grins_platform.models.enums import AlertSeverity, AlertType  # noqa: PLC0415
    from grins_platform.repositories.alert_repository import AlertRepository  # noqa: PLC0415

    alert_repo = AlertRepository(db)
    alert = Alert(
        type=AlertType.LATE_RESCHEDULE_ATTEMPT.value,
        severity=AlertSeverity.WARNING.value,
        entity_type="appointment",
        entity_id=appointment_id,
        message=message,
    )
    await alert_repo.create(alert)
except Exception as exc:
    self.log_failed(
        "send_admin_late_reschedule_alert.alert_row",
        error=exc,
        appointment_id=str(appointment_id),
    )
```

**Test fixture pattern (mirror `test_job_confirmation_service.py` lines 98–127):**

```python
def _make_sent_message(*, appointment_id=None, job_id=None, customer_id=None,
                      message_type=MessageType.APPOINTMENT_CONFIRMATION.value) -> Mock:
    msg = Mock()
    msg.id = uuid4()
    msg.appointment_id = appointment_id or uuid4()
    msg.job_id = job_id or uuid4()
    msg.customer_id = customer_id or uuid4()
    msg.message_type = message_type
    msg.provider_thread_id = "thread-123"
    msg.created_at = datetime.now(tz=timezone.utc)
    return msg
```

**Business phone lookup:** current code reads `os.environ.get("BUSINESS_PHONE_NUMBER", "")` directly (see `_build_cancellation_message` at `job_confirmation_service.py:513`). Use the same approach in the new auto-reply templates — do **not** introduce a new settings abstraction.

---

## IMPLEMENTATION PLAN

### Phase 1: Foundation (enum + migration + notification helper)

Set up the new enum member, the DB safety net, and the notification helper so the service-layer changes can cleanly reference them.

**Tasks:**
- Add `AlertType.LATE_RESCHEDULE_ATTEMPT = "late_reschedule_attempt"` to `enums.py`.
- Create Alembic migration adding the partial unique index.
- Add `NotificationService.send_admin_late_reschedule_alert` mirroring `send_admin_cancellation_alert`.

### Phase 2: Core Implementation (service layer)

Harden `_handle_reschedule` and broaden thread correlation.

**Tasks:**
- **1.A**: Idempotency check inside `_handle_reschedule` — query for existing open request before insert; on match, reuse + append to `raw_alternatives_text`.
- **1.A (safety net)**: wrap the `db.flush()` in a try/except `IntegrityError` so a concurrent-webhook race is caught and treated as a dedup hit.
- **1.B**: State guard — reject `{EN_ROUTE, IN_PROGRESS, COMPLETED, CANCELLED, NO_SHOW}`; branch on state to build the right auto-reply; fire `LATE_RESCHEDULE_ATTEMPT` alert.
- **1.B**: mark the `JobConfirmationResponse` with `status='reschedule_rejected'` for audit visibility (no schema change; `status` column is already `String(50)`).
- **1.C**: Widen `find_confirmation_message` to also match `MessageType.RESCHEDULE_FOLLOWUP` **or** add a sibling method `find_reschedule_thread` and dispatch from `_try_confirmation_reply` when the primary lookup misses. See **DECISION** in Task 6.

### Phase 3: Integration

Thread the new alert through the notification service and confirm the follow-up SMS carries `provider_thread_id`.

**Tasks:**
- Verify `sms_service.send_message` persists `provider_thread_id` on the `RESCHEDULE_FOLLOWUP` SentMessage — if not, that is a dependent fix (log it; do not silently skip).
- Wire the new alert dispatch into `_handle_reschedule`.

### Phase 4: Testing & Validation

Add unit + integration coverage for all three sub-gaps; re-run the existing confirmation test suite for regressions.

**Tasks:**
- Unit tests for 1.A idempotent insert, 1.A race (IntegrityError), 1.B state guard per status, 1.B alert dispatch, 1.C follow-up correlation, 1.C multi-reply append.
- Integration test: webhook-level double-R scenario → exactly one queue row.
- Migration test: two inserts with `status='open'` for the same `appointment_id` → second raises IntegrityError.

---

## STEP-BY-STEP TASKS

IMPORTANT: Execute every task in order, top to bottom. Each task is atomic and independently testable.

### Task 1 — ADD `AlertType.LATE_RESCHEDULE_ATTEMPT` enum member

- **IMPLEMENT**: Add one new member after `CONFIRMATION_NO_REPLY` in `AlertType`.
- **PATTERN**: `enums.py:590-598` — existing `AlertType` members are `SCREAMING_SNAKE = "snake_case"`.
- **FILE**: `src/grins_platform/models/enums.py`
- **IMPORTS**: None new.
- **GOTCHA**: The `Alert.type` column is `String(100)` with no DB check constraint (see `models/alert.py:58`), so no migration is needed for the enum value itself — just the Python code.
- **VALIDATE**: `uv run python -c "from grins_platform.models.enums import AlertType; print(AlertType.LATE_RESCHEDULE_ATTEMPT.value)"` → `late_reschedule_attempt`.

### Task 2 — CREATE Alembic migration for partial unique index

- **IMPLEMENT**: New file `src/grins_platform/migrations/versions/20260421_100000_reschedule_request_unique_open_index.py`. In `upgrade()`: `op.create_index("uq_reschedule_requests_open_per_appointment", "reschedule_requests", ["appointment_id"], unique=True, postgresql_where=sa.text("status = 'open'"))`. In `downgrade()`: `op.drop_index("uq_reschedule_requests_open_per_appointment", table_name="reschedule_requests")`.
- **PATTERN**: `migrations/versions/20260416_100100_create_alerts_table.py` (header, revision id format, op.create_index style).
- **IMPORTS**: `from __future__ import annotations`; `from collections.abc import Sequence`; `import sqlalchemy as sa`; `from alembic import op`.
- **GOTCHA**: Head revision before your migration is `20260418_100700`. Set `down_revision = "20260418_100700"`. Timestamp prefix format is `YYYYMMDD_HHMMSS` — use `20260421_100000` (current date is 2026-04-20 per context; pick the next day's 10:00:00 slot to match the existing cadence).
- **GOTCHA**: Before running the migration in dev/staging, execute the dedup SQL below to avoid the index creation failing on existing duplicate rows:
  ```sql
  WITH ranked AS (
    SELECT id, ROW_NUMBER() OVER (PARTITION BY appointment_id ORDER BY created_at ASC) AS rn
    FROM reschedule_requests
    WHERE status = 'open'
  )
  UPDATE reschedule_requests SET status = 'superseded', resolved_at = NOW()
  WHERE id IN (SELECT id FROM ranked WHERE rn > 1);
  ```
  Include this as a **comment block** at the top of the migration file (do NOT run it from within the migration — it's a data-state fix, not schema). Leave a TODO noting the dev/staging DB needs this pre-step.
- **VALIDATE**: `uv run alembic upgrade head` then `uv run alembic downgrade -1 && uv run alembic upgrade head`. Confirm index exists via `psql -c "\d reschedule_requests"`.

### Task 3 — ADD idempotent open-request lookup in `_handle_reschedule` (Gap 1.A)

- **IMPLEMENT**: Inside `_handle_reschedule` (`job_confirmation_service.py:238-273`), **before** constructing `RescheduleRequest(...)`, run:
  ```python
  stmt = (
      select(RescheduleRequest)
      .where(
          RescheduleRequest.appointment_id == appointment_id,
          RescheduleRequest.status == "open",
      )
      .order_by(RescheduleRequest.created_at.asc())
      .limit(1)
  )
  existing = (await self.db.execute(stmt)).scalar_one_or_none()
  if existing is not None:
      # Append the new raw text so the admin sees both reply bodies.
      existing.raw_alternatives_text = (
          f"{existing.raw_alternatives_text or ''}\n---\n{raw_body}".strip()
      )
      response.status = "reschedule_requested"
      response.processed_at = datetime.now(tz=timezone.utc)
      await self.db.flush()
      self.log_rejected(
          "handle_reschedule",
          reason="duplicate_open_request",
          appointment_id=str(appointment_id),
          existing_request_id=str(existing.id),
      )
      return {
          "action": "reschedule_requested",
          "appointment_id": str(appointment_id),
          "reschedule_request_id": str(existing.id),
          "auto_reply": _AUTO_REPLIES[ConfirmationKeyword.RESCHEDULE],
          # Do NOT re-send follow-up SMS on duplicate R — deliberately omit "follow_up_sms".
          "duplicate": True,
      }
  ```
  Then keep the existing insert path for the first R. Wrap the `await self.db.flush()` *after* `self.db.add(reschedule)` in a try/except `IntegrityError`:
  ```python
  from sqlalchemy.exc import IntegrityError  # top of file
  try:
      await self.db.flush()
  except IntegrityError:
      await self.db.rollback()
      # Re-run the lookup; treat the winner's row as ours.
      existing = (await self.db.execute(stmt)).scalar_one_or_none()
      if existing is None:
          raise
      # ... mirror the duplicate branch return above.
  ```
  **Important**: `self.db.rollback()` discards the entire session state including the `JobConfirmationResponse` row added earlier. Instead, re-raise and let the caller handle, OR use a `SAVEPOINT` via `async with self.db.begin_nested():` around the single-row insert so only that insert is rolled back. **Prefer the savepoint approach** — it preserves the response row.
- **PATTERN**: Duplicate-guard pattern mirrors `_handle_cancel`'s "already cancelled" short-circuit at `job_confirmation_service.py:292-306`.
- **IMPORTS**: `from sqlalchemy.exc import IntegrityError`.
- **GOTCHA**: The existing `handle_confirmation` caller expects `auto_reply` to exist; returning an empty string suppresses the send (see comment in `_handle_cancel` about `"auto_reply": ""`). For a duplicate R we *do* want to re-send the acknowledgment "We've received your reschedule request…" but **not** the follow-up, because the follow-up was already sent on R#1. Omit `follow_up_sms` from the return dict to suppress the follow-up send in `sms_service._try_confirmation_reply` (see line 846: `follow_up_sms = result.get("follow_up_sms")` — `if follow_up_sms:` gates the send).
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_reschedule_lifecycle.py::TestRescheduleIdempotency -q` (tests from Task 8).

### Task 4 — ADD state guard with branched auto-replies in `_handle_reschedule` (Gap 1.B)

- **IMPLEMENT**: At the **start** of `_handle_reschedule` (before the idempotency lookup from Task 3), fetch the appointment and branch:
  ```python
  from grins_platform.models.appointment import Appointment  # noqa: PLC0415
  appt = await self.db.get(Appointment, appointment_id)
  blocked_statuses = {
      AppointmentStatus.EN_ROUTE.value,
      AppointmentStatus.IN_PROGRESS.value,
      AppointmentStatus.COMPLETED.value,
      AppointmentStatus.CANCELLED.value,
      AppointmentStatus.NO_SHOW.value,
  }
  if appt is not None and appt.status in blocked_statuses:
      response.status = "reschedule_rejected"
      response.processed_at = datetime.now(tz=timezone.utc)
      await self.db.flush()
      await self._dispatch_late_reschedule_alert(
          appointment_id=appointment_id,
          customer_id=customer_id,
          appt=appt,
      )
      self.log_rejected(
          "handle_reschedule",
          reason="invalid_state",
          appointment_id=str(appointment_id),
          current_status=appt.status,
      )
      return {
          "action": "reschedule_rejected",
          "appointment_id": str(appointment_id),
          "current_status": appt.status,
          "auto_reply": self._build_late_reschedule_reply(appt),
      }
  ```
- **ADD** helper `_build_late_reschedule_reply(appt)` — a static method returning one of these templates, selecting by `appt.status`:
  - `EN_ROUTE` / `IN_PROGRESS`: `"Your technician is already {enroute_or_onsite}. Please call us at {business_phone} if you need to make a change."` (where `enroute_or_onsite = "on the way"` vs. `"on site"`).
  - `COMPLETED`: `"Your appointment was completed on {date}. To book a new service, call {business_phone} or reply with details."`
  - `CANCELLED` / `NO_SHOW`: `"This appointment is no longer active. Please call {business_phone}."`
  - Use `os.environ.get("BUSINESS_PHONE_NUMBER", "")` to populate `{business_phone}`; if empty, drop "at …" gracefully (mirror the style of `_build_cancellation_message` at `job_confirmation_service.py:529-534`).
- **ADD** helper `_dispatch_late_reschedule_alert(*, appointment_id, customer_id, appt)` — structurally identical to `_dispatch_admin_cancellation_alert` (`job_confirmation_service.py:399-453`), delegating to a new `NotificationService.send_admin_late_reschedule_alert` (Task 5).
- **PATTERN**: `_handle_cancel` at `job_confirmation_service.py:275-359` for the shape of "short-circuit in an invalid state, still audit the response, still run the admin dispatch after the early return."
- **IMPORTS**: `from grins_platform.models.enums import AppointmentStatus` is already at top of file — reuse.
- **GOTCHA**: The response row must still be inserted (the `self.db.add(response)` at `handle_confirmation:153` runs before `_handle_reschedule` is called, so the response row already exists in the session). Just set `status='reschedule_rejected'` and flush.
- **GOTCHA**: If `appt` is `None` (edge case: appointment was hard-deleted between confirmation SMS and reply), fall through to the normal R handling rather than crashing — the existing code path handles `appt is None` silently. Test this branch.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_reschedule_lifecycle.py::TestRescheduleStateGuard -q`.

### Task 5 — ADD `NotificationService.send_admin_late_reschedule_alert`

- **IMPLEMENT**: New method on `NotificationService` (after `send_admin_cancellation_alert` at `notification_service.py:1279`). Signature:
  ```python
  async def send_admin_late_reschedule_alert(
      self,
      db: AsyncSession,
      *,
      appointment_id: UUID,
      customer_id: UUID,
      customer_name: str,
      scheduled_at: datetime,
      current_status: str,
  ) -> None:
  ```
  Body: mirror `send_admin_cancellation_alert` verbatim, changing:
  - Alert type: `AlertType.LATE_RESCHEDULE_ATTEMPT.value`
  - Severity: `AlertSeverity.WARNING.value`
  - Message: `f"{customer_name} attempted to reschedule via SMS while appointment was in {current_status} state ({scheduled_at:%Y-%m-%d %H:%M})"`
  - Email subject: `f"Late reschedule attempt — {customer_name} ({current_status})"`
  - Email html_body: include `current_status`, `appointment_id`, `customer_id`.
  - Log event names: `send_admin_late_reschedule_alert.*`.
- **PATTERN**: `notification_service.py:1154-1278` — mirror exactly, including the two independent try/except blocks (email first, Alert row second) and the "log and swallow" error handling contract.
- **FILE**: `src/grins_platform/services/notification_service.py`
- **IMPORTS**: None new (everything used is already lazy-imported in the cancellation version).
- **GOTCHA**: Per-spec contract: **never re-raise** from this method. Admin notification must never block the customer-facing reply.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_reschedule_lifecycle.py::TestLateRescheduleAlert -q`.

### Task 6 — WIDEN thread correlation for follow-up replies (Gap 1.C)

**DECISION — add a sibling, don't widen the existing method.** `find_confirmation_message` is used by `_try_confirmation_reply` at `sms_service.py:791` to gate *whether* this is a Y/R/C reply at all. Widening its filter would make bare inbound text on a follow-up thread match as "confirmation reply" and dispatch through the keyword parser — which could false-positive on a "2" (maps to RESCHEDULE) or "1" (maps to CONFIRM) in a free-text date. Keep the original method for Y/R/C gating; add a sibling for follow-up attribution.

- **IMPLEMENT**: Add new method `find_reschedule_thread(self, thread_id)` on `JobConfirmationService`:
  ```python
  async def find_reschedule_thread(self, thread_id: str) -> SentMessage | None:
      """Find the most recent confirmation OR reschedule-followup SMS
      on this thread. Used to attribute free-text follow-up replies
      (containing alternative dates) to the right RescheduleRequest.
      """
      stmt = (
          select(SentMessage)
          .where(
              SentMessage.provider_thread_id == thread_id,
              SentMessage.message_type.in_([
                  MessageType.APPOINTMENT_CONFIRMATION.value,
                  MessageType.RESCHEDULE_FOLLOWUP.value,
              ]),
          )
          .order_by(SentMessage.created_at.desc())
          .limit(1)
      )
      return (await self.db.execute(stmt)).scalar_one_or_none()
  ```
- **UPDATE** `_try_confirmation_reply` in `src/grins_platform/services/sms_service.py` (lines 770-802): after the existing `find_confirmation_message` lookup, if `original is None`, call `svc.find_reschedule_thread(thread_id)` as a fallback **only for non-keyword bodies**:
  ```python
  original = await svc.find_confirmation_message(thread_id)
  if original is None:
      # Gap 1.C: free-text on the reschedule follow-up thread.
      # Only fall through to reschedule correlation when the body is
      # NOT a Y/R/C keyword (otherwise "1" on a free-text thread would
      # be misparsed as CONFIRM).
      keyword = parse_confirmation_reply(body)
      if keyword is not None:
          return None  # let the original orphan-fallback path handle it
      original = await svc.find_reschedule_thread(thread_id)
      if original is None:
          return None
  ```
- **UPDATE** `handle_confirmation` at `job_confirmation_service.py:106-183`: the method uses `find_confirmation_message` at line 128 and returns `no_match` if it's None. Widen that same lookup to accept follow-up threads for `_handle_needs_review` dispatch only — simplest: if primary lookup fails, call `find_reschedule_thread` and only proceed if `keyword is None`. Implementation sketch:
  ```python
  original = await self.find_confirmation_message(thread_id)
  if original is None:
      if keyword is not None:
          # Y/R/C keywords must route through the confirmation thread only.
          self.log_rejected("handle_confirmation", reason="no_matching_confirmation", thread_id=thread_id)
          return {"action": "no_match", "thread_id": thread_id}
      original = await self.find_reschedule_thread(thread_id)
      if original is None:
          self.log_rejected("handle_confirmation", reason="no_matching_thread", thread_id=thread_id)
          return {"action": "no_match", "thread_id": thread_id}
  ```
- **PATTERN**: `find_confirmation_message` body (lines 614-638) — copy the shape, swap the `where` filter.
- **FILES**: `src/grins_platform/services/job_confirmation_service.py`, `src/grins_platform/services/sms_service.py`.
- **IMPORTS**: None new (all present).
- **GOTCHA**: The existing `_find_confirmation_message` alias at line 643 is kept for backward-compat. Do not remove.
- **GOTCHA**: `_handle_needs_review` at lines 549-558 already uses `order_by(RescheduleRequest.created_at.desc()).limit(1)` — with 1.A's idempotency fix, there should only ever be one open request per appointment, but keep the `order_by` as defensive code in case an admin manually reopens a request.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_reschedule_lifecycle.py::TestFollowupCorrelation -q`.

### Task 7 — VERIFY `RESCHEDULE_FOLLOWUP` SentMessage rows carry `provider_thread_id`

- **IMPLEMENT**: Read-only verification task. Confirm that `SMSService.send_message` (search for the method in `sms_service.py`) sets `provider_thread_id` on the SentMessage row for `MessageType.RESCHEDULE_FOLLOWUP` (line 849-856 is the call site). If it doesn't — because the provider hasn't returned a thread id yet when sending an outbound, or `send_message` only sets thread_id from the inbound — **stop and report**: Task 6's `find_reschedule_thread` depends on this column being populated.
- **EXPECTED BEHAVIOR**: When the follow-up SMS is sent via `send_message`, it should either (a) persist the inbound thread_id that triggered the outbound onto the new SentMessage row, or (b) capture the provider-assigned thread id from the response. Verify which one happens.
- **PATTERN**: Look at the existing `APPOINTMENT_CONFIRMATION_REPLY` path (line 830-837) — how does that row get its `provider_thread_id`? Mirror that for the follow-up if missing.
- **IMPORTS**: None.
- **GOTCHA**: If `provider_thread_id` is not persisted on outbound rows, there is a dependent fix needed in `SMSService.send_message`. Add to the implementation report — do not silently skip.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_sms_service.py -k "thread_id" -v` and inspect one row after an end-to-end test:
  ```sql
  SELECT message_type, provider_thread_id FROM sent_messages WHERE message_type = 'reschedule_followup' ORDER BY created_at DESC LIMIT 5;
  ```

### Task 8 — CREATE `test_reschedule_lifecycle.py` with unit tests

- **IMPLEMENT**: New file `src/grins_platform/tests/unit/test_reschedule_lifecycle.py`. Test classes (mirror the shape of `test_job_confirmation_service.py`):
  - `TestRescheduleIdempotency` (Gap 1.A):
    - `test_second_r_reply_reuses_open_request` — 2 sequential calls; `db.add(RescheduleRequest)` called exactly once; `raw_alternatives_text` appended.
    - `test_second_r_reply_omits_followup_sms` — result dict has no `follow_up_sms` key.
    - `test_resolved_request_does_not_block_new_r` — when existing request has `status='resolved'`, a new open row is created.
    - `test_integrity_error_on_race_treated_as_dedup` — simulate `IntegrityError` on flush; handler returns the existing row's id. (Requires `async with self.db.begin_nested()` savepoint OR a rollback-and-reread path; write the test to whichever you implemented.)
  - `TestRescheduleStateGuard` (Gap 1.B):
    - `test_r_in_en_route_returns_late_reply_and_no_request` — no `RescheduleRequest` row created; response `status='reschedule_rejected'`.
    - `test_r_in_in_progress_returns_on_site_message` — auto-reply contains "on site".
    - `test_r_in_completed_returns_completed_message` — auto-reply references completion.
    - `test_r_in_cancelled_returns_inactive_message`.
    - `test_r_in_no_show_returns_inactive_message`.
    - `test_late_reschedule_dispatches_alert` — `NotificationService.send_admin_late_reschedule_alert` invoked with correct args.
    - `test_r_with_missing_appointment_falls_through_to_normal_path` — `db.get(Appointment, ...)` returns `None` → creates request as normal.
    - `test_r_in_scheduled_still_works` — sanity check: happy path not broken.
  - `TestFollowupCorrelation` (Gap 1.C):
    - `test_followup_thread_lookup_matches_reschedule_followup_message_type` — `find_reschedule_thread` returns the follow-up SentMessage.
    - `test_free_text_reply_on_followup_thread_attaches_to_open_request` — `handle_confirmation(keyword=None, thread_id=...)` appends to `requested_alternatives.entries`.
    - `test_keyword_reply_on_followup_thread_ignored_for_confirmation` — "R" body on a follow-up-only thread returns `no_match` (doesn't reopen).
    - `test_multiple_followup_replies_all_append` — three sequential non-keyword replies → 3 entries on the same request.
  - `TestLateRescheduleAlert` (Task 5):
    - `test_alert_row_persisted_with_correct_type_and_severity`.
    - `test_alert_email_has_current_status_in_subject`.
    - `test_alert_dispatch_never_raises` — raise inside `AlertRepository.create`; method returns None.
- **PATTERN**: Reuse the `_make_sent_message`, `_make_appointment`, `mock_db` helper shapes from `test_job_confirmation_service.py:98-127`.
- **IMPORTS**: `from unittest.mock import AsyncMock, MagicMock, Mock`; `from uuid import uuid4`; `import pytest`; `from grins_platform.models.enums import AppointmentStatus, AlertType, MessageType, ConfirmationKeyword`; `from grins_platform.services.job_confirmation_service import JobConfirmationService`.
- **GOTCHA**: `db.execute` side_effect must be an *ordered list* — multiple query queries run inside `_handle_reschedule` (appt fetch via `db.get`, existing-request lookup via `db.execute`). Trace the order of DB calls before building the mock queue.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_reschedule_lifecycle.py -v`.

### Task 9 — ADD integration test for webhook-level dedup

- **IMPLEMENT**: Append a test to `src/grins_platform/tests/integration/test_appointment_integration.py` (or create `test_reschedule_lifecycle_integration.py` if the file is too large — prefer appending). Test: fire two CallRail-shaped inbound webhook payloads with different `created_at` timestamps but the same conversation_id + body "R" for the same confirmation thread; assert exactly one `reschedule_requests` row at `status='open'`.
- **PATTERN**: Existing webhook integration tests in `tests/integration/` use fastapi TestClient + an engineered test DB. Find a recent webhook integration test and mirror its setup.
- **IMPORTS**: TestClient, test DB fixture.
- **GOTCHA**: Redis dedup may intercept the second request if your test hits the same conversation_id/created_at. Use *different* `created_at` timestamps so Redis passes it through and application-level idempotency is the thing under test.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/integration/test_appointment_integration.py::test_double_r_creates_one_request -v`.

### Task 10 — ADD migration test for partial unique index

- **IMPLEMENT**: Add test to `src/grins_platform/tests/test_models.py` or nearby: seed one `RescheduleRequest(status='open', appointment_id=X)`, attempt to insert a second with the same `appointment_id` and `status='open'` → expect `IntegrityError`. Then update the first to `status='resolved'`; inserting a new open row with the same `appointment_id` succeeds.
- **PATTERN**: Look for existing constraint-validation tests in `test_constraint_validation_property.py` or `test_models.py`.
- **IMPORTS**: `from sqlalchemy.exc import IntegrityError`.
- **GOTCHA**: This test must run against a real Postgres DB (the partial-index constraint is Postgres-specific). Confirm the test runner uses `pytest.mark.integration` or equivalent so it doesn't run against SQLite.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/test_models.py -k "reschedule_unique" -v`.

### Task 11 — RUN full validation suite

- **IMPLEMENT**: Execute Level 1–4 commands below. Fix any regressions before declaring complete.
- **VALIDATE**: See **VALIDATION COMMANDS** section.

---

## TESTING STRATEGY

### Unit Tests

Project uses pytest with `asyncio_mode = "auto"`. Tests live under `src/grins_platform/tests/unit/`. Use `AsyncMock`/`MagicMock` for the DB session (see `test_job_confirmation_service.py` for the exact mock shape). Each test is marked with `@pytest.mark.unit` and `@pytest.mark.asyncio`.

Coverage target (per existing project defaults): each new branch in `_handle_reschedule` must have at least one test. Aim for 100% line coverage of the modified methods.

### Integration Tests

Place in `src/grins_platform/tests/integration/`. Prefer appending to an existing file unless the tests are lifecycle-specific enough to warrant a new module. Use the fastapi TestClient pattern already used by the cancellation-webhook integration tests.

### Edge Cases

- Two open requests already exist (legacy / pre-fix data) — the lookup must pick the oldest and append to it; leave duplicates as a one-time cleanup via the pre-migration SQL (Task 2).
- Appointment is hard-deleted between confirmation SMS and R reply → `appt is None` → fall through to normal path (do not crash, do not alert).
- Follow-up thread lookup returns a message whose `appointment_id` is NULL on the SentMessage row → defensive: if `response.appointment_id` can't be resolved, fall through to `needs_review` with a log warning.
- Race: two webhooks arrive at the same millisecond, both pass Redis dedup (different `created_at`), both reach `_handle_reschedule`. The savepoint-catching-IntegrityError path must treat the loser as a duplicate hit. Test with a mocked `flush` that raises `IntegrityError` on second call.
- "R" when appt status is `DRAFT` — not in the blocked set, not in the admin-resolver's `allowed_statuses` set (DRAFT, SCHEDULED, CONFIRMED). Per gap doc 1.B, this is legitimate (customer replies before admin clicks "Send Confirmation" — edge case but possible). Let it pass; admin resolves DRAFT via the existing path.
- Duplicate R *after* a cancel (`C` reply → CANCELLED, then `R`) — the Task 4 state guard blocks it with the "no longer active" message. Verified by `test_r_in_cancelled_returns_inactive_message`.

---

## VALIDATION COMMANDS

Execute every command. Zero regressions required.

### Level 1: Syntax & Style

```bash
uv run ruff check src/grins_platform/services/job_confirmation_service.py \
                  src/grins_platform/services/notification_service.py \
                  src/grins_platform/services/sms_service.py \
                  src/grins_platform/models/enums.py \
                  src/grins_platform/migrations/versions/20260421_100000_reschedule_request_unique_open_index.py \
                  src/grins_platform/tests/unit/test_reschedule_lifecycle.py
uv run ruff format --check src/grins_platform/services/job_confirmation_service.py \
                            src/grins_platform/services/notification_service.py \
                            src/grins_platform/models/enums.py
```

### Level 2: Unit Tests

```bash
uv run pytest src/grins_platform/tests/unit/test_reschedule_lifecycle.py -v
uv run pytest src/grins_platform/tests/unit/test_job_confirmation_service.py -v    # regression check
uv run pytest src/grins_platform/tests/unit/test_reschedule_detection.py -v         # regression check
```

### Level 3: Integration Tests

```bash
uv run pytest src/grins_platform/tests/integration/test_appointment_integration.py -v -k "reschedule"
uv run pytest src/grins_platform/tests/test_sms_service.py -v -k "confirmation"
```

### Level 4: Migration Validation

```bash
uv run alembic upgrade head
uv run alembic downgrade -1
uv run alembic upgrade head
# Confirm index in Postgres:
psql "$DATABASE_URL" -c "\d reschedule_requests" | grep -i "uq_reschedule_requests_open_per_appointment"
```

### Level 5: Manual Validation (staging/dev)

1. Send a confirmation SMS for appointment A (status=SCHEDULED). Text "R" from the customer number. Assert one open request appears in the queue.
2. Text "R" again from the same number. Assert the queue still shows one row (no duplicate).
3. Move appointment B into `EN_ROUTE`. Text "R". Assert (a) no new request row, (b) auto-reply says "technician is already on the way", (c) a `late_reschedule_attempt` alert row was created, (d) admin email received.
4. For open request on appointment C, text "Tuesday at 2pm" as a free-text follow-up reply. Assert the `requested_alternatives.entries` on the open request now contains that text.
5. Pre-check index by inserting two open rows for the same `appointment_id` via `psql` → expect `duplicate key value violates unique constraint`.

---

## ACCEPTANCE CRITERIA

- [ ] Second identical "R" reply for the same appointment does NOT create a second `reschedule_requests` row (1.A unit + integration tests pass).
- [ ] Second "R" does not re-send the follow-up SMS.
- [ ] Partial unique index `uq_reschedule_requests_open_per_appointment` exists in Postgres after `alembic upgrade head`.
- [ ] "R" reply while appointment is `EN_ROUTE` / `IN_PROGRESS` / `COMPLETED` / `CANCELLED` / `NO_SHOW` does NOT create a `reschedule_requests` row (1.B unit tests pass).
- [ ] State-specific auto-reply text is returned for each blocked state.
- [ ] A `late_reschedule_attempt` Alert row is inserted for every blocked R attempt.
- [ ] Admin notification email is dispatched (failure is logged, never raised).
- [ ] Free-text reply on a `reschedule_followup` thread attaches to the correct open `RescheduleRequest.requested_alternatives.entries` (1.C unit tests pass).
- [ ] `find_reschedule_thread` is additive — `find_confirmation_message` behavior is unchanged (existing Y/R/C tests still pass).
- [ ] All existing tests in `test_job_confirmation_service.py` and `test_reschedule_detection.py` continue to pass (no regressions).
- [ ] Ruff lint + format pass on modified files.
- [ ] Migration upgrade + downgrade + upgrade cycle succeeds.
- [ ] `RescheduleRequestsQueue.tsx` is untouched (no frontend changes).

---

## COMPLETION CHECKLIST

- [ ] Task 1: `AlertType.LATE_RESCHEDULE_ATTEMPT` enum member added.
- [ ] Task 2: Partial unique-index migration created and reversible.
- [ ] Task 3: Idempotent open-request lookup in `_handle_reschedule` + IntegrityError savepoint.
- [ ] Task 4: State guard + branched auto-replies in `_handle_reschedule`.
- [ ] Task 5: `NotificationService.send_admin_late_reschedule_alert` implemented.
- [ ] Task 6: `find_reschedule_thread` added; `_try_confirmation_reply` + `handle_confirmation` updated.
- [ ] Task 7: `provider_thread_id` on `RESCHEDULE_FOLLOWUP` SentMessage rows verified / fixed.
- [ ] Task 8: `test_reschedule_lifecycle.py` with full unit coverage.
- [ ] Task 9: Integration test for double-R webhook dedup.
- [ ] Task 10: Migration test for partial unique index.
- [ ] Task 11: Level 1–5 validation executed; all green.

---

## NOTES

**Design decision — application-level check first, DB constraint second.** The gap doc proposes the same two-layer approach. App-level lookup is the primary guard because it handles the "append to existing `raw_alternatives_text`" behavior gracefully (a DB constraint alone would just raise on insert, losing the second message body). The partial unique index is a safety net for races.

**Design decision — savepoint, not full rollback, for IntegrityError.** The `JobConfirmationResponse` row is added earlier in `handle_confirmation` (line 153) and must persist even when the `RescheduleRequest` insert races. A `SAVEPOINT` via `async with self.db.begin_nested():` keeps the response row. Full session rollback would drop it, breaking audit trail.

**Design decision — sibling `find_reschedule_thread`, not widened `find_confirmation_message`.** Prevents false-positive keyword parsing (e.g., a "2" inside a free-text date) on follow-up threads.

**Non-goals:**
- Date parsing of free-text alternatives (mentioned as "optional" in gap 1.C). Out of scope for this fix — tracked as a separate enhancement.
- Frontend queue changes. The queue already handles single rows correctly; with 1.A fixed there will not be duplicates to display.
- Cross-referenced gaps (Gap 02 idempotency for Y, Gap 03 thread correlation, Gap 11 appointment-detail inbound visibility) — out of scope.

**Risks:**
- Existing production/staging data may already have duplicate open rows. The pre-migration SQL in Task 2 handles this, but must be run manually before `alembic upgrade head` in environments where duplicates exist.
- `provider_thread_id` population on `RESCHEDULE_FOLLOWUP` outbound rows (Task 7) is a dependency — if it's missing today, Task 6's correlation won't work. Verify early.
- CallRail's provider behavior of reusing thread ids across appointment-confirmation and reschedule-follow-up within the same conversation is assumed. If CallRail assigns a new thread id to the outbound follow-up, correlation of subsequent replies on the old thread would still go to `find_confirmation_message` — which is fine, the widening is safety. But if it assigns a new thread id *and* the customer replies on the new thread, `find_reschedule_thread` is required.

**Confidence score for one-pass success: 8/10.** The plan is complete, the patterns are firmly grounded in existing code (cancellation alert, migration shape, test shape), and the three sub-gaps are well-scoped. The 2 points of risk: (a) Task 7 may require a dependent fix in `SMSService.send_message` that the plan cannot fully anticipate without the file open in front of you, and (b) the savepoint-with-IntegrityError pattern is subtle and the first implementation may need one iteration against a real Postgres test DB.
