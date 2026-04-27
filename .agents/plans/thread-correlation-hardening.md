# Feature: Thread Correlation Hardening (Gap 03)

The following plan is derived from `feature-developments/scheduling gaps/gap-03-thread-correlation.md`. It closes two latent bugs in how inbound Y/R/C SMS replies are correlated back to their outbound confirmation/reschedule/cancellation messages via `sent_messages.provider_thread_id`.

The plan is complete, but you MUST still validate documentation and codebase patterns and task sanity before implementing. Pay special attention to naming of existing utils, types, and models. Import from the right files (e.g. `AlertType` lives in `grins_platform.models.enums`; `AlertRepository` lives in `grins_platform.repositories.alert_repository`; `NotificationService.send_admin_*_alert` helpers live in `grins_platform.services.notification_service`).

## Feature Description

Inbound SMS replies (Y/R/C + free text) are correlated back to the original outbound message via `sent_messages.provider_thread_id` plus a `message_type` filter. Gap 03 identifies two defects in that correlation:

- **3.A — Narrow `message_type` filter in `find_confirmation_message`:** When an admin reschedules or cancels an appointment, `_send_reschedule_sms` / `_send_cancellation_sms` emit a new SMS that *also* invites "Y / R / C". The `send_message` code path persists `provider_thread_id` unconditionally (already verified — see `sms_service.py:352`), but `find_confirmation_message` hard-filters `message_type == APPOINTMENT_CONFIRMATION`. Replies to a reschedule-notification SMS therefore miss correlation and fall through to orphan/needs-review. Replies to a cancellation-notification SMS (customer changing their mind) are likewise lost.
- **3.B — Stale confirmation threads remain authoritative:** `find_confirmation_message` only orders by `created_at DESC` against a thread_id — it has no concept of "this thread is no longer the active confirmation." A customer who replies "Y" to last week's thread after a reschedule silently confirms a date they never saw.

The fix composes three coordinated layers: widen correlation for confirmation-like outbounds, flag prior messages as superseded when a newer confirmation-like SMS is sent for the same appointment, and add a post-cancellation reply handler that treats "R" as a new reschedule request and "Y" as a reactivation-attempt admin alert.

## User Story

As a customer who replies Y/R/C (or free text) to the most recent appointment SMS I received
I want my reply to route to the *current* appointment state and action
So that my confirmation/reschedule/cancellation intent is never silently lost and I'm not accidentally confirming an outdated date.

As an admin monitoring customer-initiated flips
I want stale-thread replies and post-cancellation reconsiderations to surface as actionable events (alerts or new reschedule requests)
So that the system doesn't silently drop signal when a customer replies to an older thread or changes their mind after cancelling.

## Problem Statement

Thread correlation currently fails in three composable ways:

1. **Reschedule-notification Y/R/C is uncorrelatable.** Admin drags appointment → customer gets "We moved you to Wed, reply Y" → customer replies Y → system writes orphan and leaves status=SCHEDULED forever.
2. **Cancellation-notification Y/R is uncorrelatable.** Admin cancels → customer replies "R" within minutes ("wait, no, I still want it") → system writes orphan and customer thinks they un-cancelled; system disagrees.
3. **Stale thread auto-confirms new date.** Customer replies Y to a thread from before the reschedule → `find_confirmation_message` picks the old row → handler sees `status=SCHEDULED` (reset by reschedule) and transitions to CONFIRMED on the new date the customer never saw.

All three are composable: a rescheduled appointment might have *both* a stale confirmation thread and a new reschedule thread that cannot be correlated — replies to either route badly.

## Solution Statement

Three coordinated fixes:

1. **Widen `find_confirmation_message` to a confirmation-like set** (`APPOINTMENT_CONFIRMATION`, `APPOINTMENT_RESCHEDULE`, `APPOINTMENT_REMINDER`). Explicitly **exclude** `APPOINTMENT_CANCELLATION` — a reply to a cancellation notification means something semantically different and routes through a new handler.
2. **Add `superseded_at` to `sent_messages`.** When a new confirmation-like SMS (`APPOINTMENT_CONFIRMATION` / `APPOINTMENT_RESCHEDULE` / `APPOINTMENT_CANCELLATION` / `APPOINTMENT_REMINDER`) is sent for an `appointment_id`, mark all prior confirmation-like rows for that appointment with `superseded_at = NOW()`. `find_confirmation_message` then filters `superseded_at IS NULL`. A lookup that only matches a superseded row returns a `stale_thread_reply` response with a courteous auto-reply.
3. **Add a post-cancellation reply handler.** A separate `find_cancellation_thread` + new handler path (`_handle_post_cancellation_reply`) so that:
   - "R" on a cancellation thread → open a new `RescheduleRequest` (through the existing state guard) for admin to resolve.
   - "Y" on a cancellation thread → raise a new `CUSTOMER_RECONSIDER_CANCELLATION` admin alert (not an auto-transition; admin reviews manually).
   - Anything else → `needs_review`.

No frontend changes. No API changes. DB migration adds one column + indexes.

## Feature Metadata

**Feature Type**: Bug Fix + Enhancement (hardening)
**Estimated Complexity**: Medium
**Primary Systems Affected**:
- Backend service: `JobConfirmationService` (correlation + post-cancel handler)
- Backend service: `SMSService.send_message` (supersession marker on outbound)
- Backend service: `NotificationService` (new alert dispatch)
- DB schema: `sent_messages.superseded_at` column + partial index
- Enums: `AlertType` (new member for reconsideration)
- Tests: unit (3-tier convention) + functional + integration coverage

**Dependencies**: No new external libraries. Uses existing SQLAlchemy 2.x async, Alembic, pytest-asyncio, Hypothesis.

---

## CONTEXT REFERENCES

### Relevant Codebase Files — IMPORTANT: READ THESE BEFORE IMPLEMENTING

**Correlation hotspots:**
- `src/grins_platform/services/job_confirmation_service.py:107-198` — `handle_confirmation` orchestrator (dispatches to handle_confirm / reschedule / cancel / needs_review). Must gain a post-cancellation reply branch when `find_confirmation_message` misses and `find_cancellation_thread` matches.
- `src/grins_platform/services/job_confirmation_service.py:853-877` — `find_confirmation_message` — hard-filters on `APPOINTMENT_CONFIRMATION`. Widen + add `superseded_at IS NULL`.
- `src/grins_platform/services/job_confirmation_service.py:879-916` — `find_reschedule_thread` (gap-01 sibling). Pattern to follow when building `find_cancellation_thread`.
- `src/grins_platform/services/job_confirmation_service.py:514-598` — `_handle_cancel` (SCHEDULED/CONFIRMED → CANCELLED) — the sibling handler to mirror when building `_handle_post_cancellation_reply`.
- `src/grins_platform/services/job_confirmation_service.py:253-375` — `_handle_reschedule` — open-request dedup + state guard (gap-01). Post-cancel "R" path should call into the same reschedule insert (but through a pre-check that differs: the appointment is already CANCELLED, state guard would currently reject — so branch BEFORE the guard).
- `src/grins_platform/services/job_confirmation_service.py:464-512` — `_dispatch_late_reschedule_alert` — exact pattern to mirror for `_dispatch_reconsider_cancellation_alert`.

**Outbound-send hotspots:**
- `src/grins_platform/services/sms_service.py:280-378` — `send_message` core path. Already persists `provider_thread_id` unconditionally at line 352 — DO NOT re-wire that. Instead, after line 354 (after `sent_message.provider_thread_id` is set and flush completes), add a post-flush hook that marks prior confirmation-like `sent_messages(appointment_id=X)` with `superseded_at = NOW()` when the new row is itself confirmation-like and has a non-null `appointment_id`.
- `src/grins_platform/services/sms_service.py:770-811` — `_try_confirmation_reply` dispatcher. Add a fallback: when `find_confirmation_message` returns None and `find_reschedule_thread` returns None, try `find_cancellation_thread`; if that matches, dispatch through `handle_confirmation` with a `cancellation_context=True` flag (or a separate service entry — see Task 4 DECISION).

**Models / enums:**
- `src/grins_platform/models/sent_message.py:21-158` — add `superseded_at` column; add partial index.
- `src/grins_platform/models/enums.py:590-598` — `AlertType` — add `CUSTOMER_RECONSIDER_CANCELLATION = "customer_reconsider_cancellation"` member. Leave existing members in place.
- `src/grins_platform/models/enums.py:710-738` — `MessageType` — **no changes**; already has all five confirmation-like values.
- `src/grins_platform/models/enums.py:162-177` — `AppointmentStatus` — reference only for the post-cancel state checks.

**Notification / alert:**
- `src/grins_platform/services/notification_service.py:1154-1278` — `send_admin_cancellation_alert` — mirror EXACTLY (both email + Alert row channels, independent try/except, log-and-swallow contract) for new `send_admin_reconsider_cancellation_alert`.
- `src/grins_platform/services/notification_service.py:1279-1392` — `send_admin_late_reschedule_alert` — the closer sibling (gap-01). Use this as the direct pattern.
- `src/grins_platform/repositories/alert_repository.py` — `AlertRepository.create` — no change required.

**Tests to mirror:**
- `src/grins_platform/tests/unit/test_reschedule_lifecycle.py` (lines 1-550) — MOST IMPORTANT reference. Mirror fixture shapes (`_make_sent_message`, `_make_appointment`, `_make_open_request`, `mock_db`, `_make_execute_side_effect`) exactly. `test_reschedule_lifecycle.py` was authored against gap-01 and is the current gold standard for lifecycle unit tests.
- `src/grins_platform/tests/unit/test_job_confirmation_service.py:98-131` — the original helper shapes the reschedule test file derived from.
- `src/grins_platform/tests/unit/test_sms_service_gaps.py:360-440` — precedent for testing `_try_confirmation_reply` dispatch with mocked `find_confirmation_message` / `find_reschedule_thread`. The fallback to `find_cancellation_thread` should be added to this file (not a new one — it keeps the dispatcher behavior tests co-located).
- `src/grins_platform/tests/unit/test_thread_id_storage.py` (full file) — the existing unit for `provider_thread_id` persistence on outbound. Extend here for the supersession marker.
- `src/grins_platform/tests/functional/test_yrc_confirmation_functional.py:36-108` — mock DB factory pattern to mirror for functional tests.
- `src/grins_platform/tests/integration/test_reschedule_lifecycle_integration.py:32-148` — `_StatefulDb` pattern. For a post-cancel integration test, extend this file or create a sibling `test_thread_correlation_integration.py` (prefer the latter; the existing file is lifecycle-1A-specific).

**Migrations:**
- `src/grins_platform/migrations/versions/20260421_100000_reschedule_request_unique_open_index.py` — revision chain head (`20260421_100000`). Your new migration will revise from this.
- `src/grins_platform/migrations/versions/20260414_100500_widen_sent_messages_for_reschedule_cancellation.py` — precedent for modifying `sent_messages` CHECK constraints. Instructive only — this plan does not touch that constraint.
- `src/grins_platform/migrations/versions/20260416_100100_create_alerts_table.py` — migration header template (revision / down_revision / branch_labels / depends_on).

**Frontend:**
- `frontend/src/features/schedule/components/RescheduleRequestsQueue.tsx` — **no changes required**; post-cancel-reconsider alerts surface via the existing admin alerts dashboard, not the reschedule queue.

**Steering documents** (under `.kiro/steering/`) that bound this plan:
- `code-standards.md` — LoggerMixin domain logging; three-tier tests (`unit/` + `functional/` + `integration/`); naming `test_{method}_with_{condition}_returns_{expected}`; type hints + MyPy + Pyright zero errors; 88-char lines; ruff lint & format gate.
- `api-patterns.md` — no API endpoints here, so only relevant for the future admin-alert UI (out of scope).
- `structure.md` — path conventions already reflected above.
- `tech.md` — `uv run ...` toolchain.
- `spec-testing-standards.md` — unit + functional + integration + property-based tests where appropriate; coverage target 90% for services.
- `spec-quality-gates.md` — requirements file must include Logging Events, data-testid map (frontend-only, n/a here), quality-gate commands (provided in **VALIDATION COMMANDS** section).
- `auto-devlog.md` + `devlog-rules.md` — append a `DEVLOG.md` entry under "Recent Activity" after implementation lands (template in devlog-rules.md).

### New Files to Create

- `src/grins_platform/migrations/versions/20260421_100100_add_sent_messages_superseded_at.py` — adds `superseded_at TIMESTAMPTZ NULL` to `sent_messages` plus a partial index on `(appointment_id, message_type) WHERE superseded_at IS NULL`.
- `src/grins_platform/tests/unit/test_thread_correlation_lifecycle.py` — unit tests for widened `find_confirmation_message`, `find_cancellation_thread`, supersession filter, post-cancel handler dispatch, reconsider-alert dispatch.
- `src/grins_platform/tests/functional/test_post_cancellation_reply_functional.py` — functional tests for the end-to-end post-cancel reply flows with the mock-DB factory.
- `src/grins_platform/tests/integration/test_thread_correlation_integration.py` — integration test using the `_StatefulDb` pattern for supersession + stale-thread replies.

**DECISION — dispatcher layering.** The service entry point (`JobConfirmationService.handle_confirmation`) currently assumes the matched row is confirmation-like. For post-cancellation replies, we need a different handler tree. Three options:

- (A) Add a second service method `handle_post_cancellation_reply` and dispatch at `_try_confirmation_reply` level.
- (B) Keep `handle_confirmation` as the single entry; have it branch internally on `original.message_type == APPOINTMENT_CANCELLATION`.
- (C) Inline at `sms_service._try_confirmation_reply`.

**Choose (A).** Rationale: keeps `handle_confirmation`'s single responsibility (confirmation-like thread dispatch) intact, mirrors the `find_confirmation_message` / `find_reschedule_thread` split that gap-01 established, and keeps the new handler's tests narrow. The dispatcher in `sms_service._try_confirmation_reply` already has a fallback ladder (confirmation → reschedule-follow-up); add cancellation as a third rung.

### Relevant Documentation — READ BEFORE IMPLEMENTING

- [PostgreSQL partial indexes](https://www.postgresql.org/docs/16/indexes-partial.html)
  - Section: "Partial Indexes"
  - Why: The supersession filter's index must be partial (`WHERE superseded_at IS NULL`) to keep lookups on active threads fast without bloating the index with tombstoned rows.
- [PostgreSQL UPDATE with CTE / transactional writes](https://www.postgresql.org/docs/16/sql-update.html)
  - Why: The supersession marker runs inside `send_message`'s open session — an `UPDATE sent_messages SET superseded_at = NOW() WHERE appointment_id = :id AND id != :new_id AND message_type IN (...)` must use the same session.
- [SQLAlchemy 2.x async session update](https://docs.sqlalchemy.org/en/20/orm/queryguide/dml.html#the-update-construct-with-orm-session)
  - Section: `session.execute(update(...))` pattern
  - Why: The supersession marker uses `sqlalchemy.update()` rather than hand-written SQL.
- [SQLAlchemy Alembic — add column with timezone-aware timestamp](https://alembic.sqlalchemy.org/en/latest/ops.html#alembic.operations.Operations.add_column)
  - Why: `op.add_column` for `superseded_at` needs `sa.TIMESTAMP(timezone=True)` — mirror the pattern at `sent_messages.sent_at` / `created_at`.

### Patterns to Follow

Specific patterns extracted from the codebase — mirror exactly, do not invent new shapes.

**Alembic migration header (mirror `20260421_100000_reschedule_request_unique_open_index.py`):**

```python
"""Add sent_messages.superseded_at column and supporting partial index.

Gap 03.B: once a new confirmation-like SMS is sent for an appointment,
prior sent_messages rows of type APPOINTMENT_CONFIRMATION /
APPOINTMENT_RESCHEDULE / APPOINTMENT_CANCELLATION / APPOINTMENT_REMINDER
are stamped with ``superseded_at = NOW()`` so `find_confirmation_message`
no longer routes a stale-thread reply to an appointment whose state has
moved on.

Revision ID: 20260421_100100
Revises: 20260421_100000
Requirements: gap-03 (thread correlation)
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260421_100100"
down_revision: str | None = "20260421_100000"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None
```

**Partial index creation (PostgreSQL, for supersession lookup):**

```python
op.add_column(
    "sent_messages",
    sa.Column(
        "superseded_at",
        sa.TIMESTAMP(timezone=True),
        nullable=True,
    ),
)
op.create_index(
    "ix_sent_messages_active_confirmation_by_appointment",
    "sent_messages",
    ["appointment_id", "message_type"],
    postgresql_where=sa.text("superseded_at IS NULL"),
)
```

**Naming conventions:**
- Models: `snake_case` table names, `CamelCase` classes.
- Index names: `idx_<table>_<cols>` for generic non-unique; `ix_<table>_<cols>[_cond]` for the supersession partial index (matches the existing `ix_sent_messages_provider_thread_id`).
- Enum values: `SCREAMING_SNAKE_CASE` member, lowercase snake string value (see `AlertType.CUSTOMER_CANCELLED_APPOINTMENT = "customer_cancelled_appointment"`).
- Service internal methods: `_handle_*`, `_dispatch_*`, `_record_*` prefixes. Public correlation helpers: `find_*`.
- Log event names: `<service_domain>.<action>[.<sub_action>]` (e.g., `send_admin_reconsider_cancellation_alert.email`). Use `LoggerMixin.log_started/log_completed/log_rejected/log_failed`.
- Test class names: `Test<FeatureArea>` (see `TestRescheduleIdempotency`, `TestRescheduleStateGuard`).
- Test method names: `test_<method>_with_<condition>_returns_<expected>` per `.kiro/steering/code-standards.md`.

**Correlation helper shape (mirror `find_reschedule_thread`, `job_confirmation_service.py:879-916`):**

```python
async def find_cancellation_thread(self, thread_id: str) -> SentMessage | None:
    """Find the most recent cancellation SMS for a thread_id.

    Used to attribute inbound replies to a cancellation notification
    (Y = reconsideration, R = new reschedule request, free text =
    needs_review). Separate from :meth:`find_confirmation_message` so
    confirmation-like Y/R/C routing never accidentally transitions a
    CANCELLED appointment.

    Validates: gap-03 (3.A post-cancellation reply).
    """
    stmt = (
        select(SentMessage)
        .where(
            SentMessage.provider_thread_id == thread_id,
            SentMessage.message_type == MessageType.APPOINTMENT_CANCELLATION.value,
            SentMessage.superseded_at.is_(None),
        )
        .order_by(SentMessage.created_at.desc())
        .limit(1)
    )
    result = await self.db.execute(stmt)
    return result.scalar_one_or_none()
```

**Widened `find_confirmation_message` (replaces existing body):**

```python
_CONFIRMATION_LIKE_TYPES: frozenset[str] = frozenset(
    {
        MessageType.APPOINTMENT_CONFIRMATION.value,
        MessageType.APPOINTMENT_RESCHEDULE.value,
        MessageType.APPOINTMENT_REMINDER.value,
    }
)

async def find_confirmation_message(self, thread_id: str) -> SentMessage | None:
    """Find the authoritative confirmation-like SMS for a thread_id.

    Gap 03:
    - Widened from APPOINTMENT_CONFIRMATION only to the confirmation-like
      set (confirmation / reschedule notification / reminder). A reply to
      any of these solicits Y/R/C and should route through the same
      handler tree.
    - Filters out rows with a non-null ``superseded_at`` so a stale-thread
      reply does not accidentally route to an appointment whose state has
      moved on.

    Cancellation notifications are intentionally NOT included here —
    :meth:`find_cancellation_thread` handles that separately through
    ``_handle_post_cancellation_reply``.

    Validates: CRM Changes Update 2 Req 24.7; gap-03 (3.A, 3.B).
    """
    stmt = (
        select(SentMessage)
        .where(
            SentMessage.provider_thread_id == thread_id,
            SentMessage.message_type.in_(_CONFIRMATION_LIKE_TYPES),
            SentMessage.superseded_at.is_(None),
        )
        .order_by(SentMessage.created_at.desc())
        .limit(1)
    )
    result = await self.db.execute(stmt)
    return result.scalar_one_or_none()
```

**Supersession marker in `send_message` (after successful outbound flush — `sms_service.py:352-354`):**

```python
# --- gap-03 (3.B): mark prior confirmation-like SMSes for the same
# appointment as superseded so `find_confirmation_message` no longer
# routes stale-thread replies to the moved appointment. Runs only for
# confirmation-like outbounds that are attached to an appointment.
_SUPERSEDABLE_TYPES = {
    MessageType.APPOINTMENT_CONFIRMATION.value,
    MessageType.APPOINTMENT_RESCHEDULE.value,
    MessageType.APPOINTMENT_CANCELLATION.value,
    MessageType.APPOINTMENT_REMINDER.value,
}

if (
    sent_message.appointment_id is not None
    and sent_message.message_type in _SUPERSEDABLE_TYPES
):
    from sqlalchemy import update as sa_update  # noqa: PLC0415
    now = datetime.now(tz=timezone.utc)
    await self.session.execute(
        sa_update(SentMessage)
        .where(
            SentMessage.appointment_id == sent_message.appointment_id,
            SentMessage.id != sent_message.id,
            SentMessage.message_type.in_(_SUPERSEDABLE_TYPES),
            SentMessage.superseded_at.is_(None),
        )
        .values(superseded_at=now)
    )
    await self.session.flush()
```

**Error-swallowing alert dispatch (mirror `_dispatch_late_reschedule_alert`, `job_confirmation_service.py:464-512`):**

```python
async def _dispatch_reconsider_cancellation_alert(
    self,
    *,
    appointment_id: UUID,
    customer_id: UUID,
    appt: Appointment | None,
) -> None:
    """Notify admin that a customer texted "Y" to a cancellation SMS.

    Mirrors :meth:`_dispatch_late_reschedule_alert`. Per-spec contract:
    exceptions are logged and swallowed so admin notification never
    blocks the customer-facing reply.

    Validates: gap-03 (3.A cancel-reconsider alert).
    """
    from grins_platform.models.customer import Customer  # noqa: PLC0415
    from grins_platform.services.notification_service import (  # noqa: PLC0415
        NotificationService,
    )
    try:
        customer = await self.db.get(Customer, customer_id)
        if customer is None:
            self.log_rejected(
                "handle_post_cancellation_reply.reconsider_alert",
                reason="customer_not_found",
                customer_id=str(customer_id),
            )
            return
        notification_svc = NotificationService(
            email_service=self._build_email_service(),
        )
        await notification_svc.send_admin_reconsider_cancellation_alert(
            self.db,
            appointment_id=appointment_id,
            customer_id=customer_id,
            customer_name=customer.full_name,
            scheduled_at=self._resolve_scheduled_at(appt),
        )
    except Exception as exc:
        self.log_failed(
            "handle_post_cancellation_reply.reconsider_alert_failed",
            error=exc,
            appointment_id=str(appointment_id),
        )
```

---

## IMPLEMENTATION PLAN

### Phase 1 — Schema + Enum Foundation

Lay down the DB column, the partial index, and the new `AlertType` member before touching any service code so supporting references compile cleanly.

**Tasks:** migration, enum update.

### Phase 2 — Correlation Helpers

Widen `find_confirmation_message`, add the supersession filter, add `find_cancellation_thread`. Keep `find_reschedule_thread` unchanged (gap-01 still owns it).

**Tasks:** rewrite `find_confirmation_message`; add `find_cancellation_thread`; add helper constant `_CONFIRMATION_LIKE_TYPES`.

### Phase 3 — Outbound Supersession

Wire the supersession marker into `SMSService.send_message` so every new confirmation-like SMS tombstones its predecessors for the same appointment.

**Tasks:** add the post-flush supersession `UPDATE`.

### Phase 4 — Post-Cancellation Handler

Add `handle_post_cancellation_reply` service method + dispatch into it from `_try_confirmation_reply` (third-rung fallback: confirmation → reschedule-followup → cancellation).

**Tasks:** build the handler (R → reschedule-request-for-cancelled-appt branch; Y → reconsider alert; else → needs_review); wire into `_try_confirmation_reply`; add `NotificationService.send_admin_reconsider_cancellation_alert`.

### Phase 5 — Stale-Reply Telemetry + Courteous Auto-Reply

When `find_confirmation_message(thread_id)` finds only a superseded row (explicit re-query is needed for this branch), write a `JobConfirmationResponse(status='stale_thread_reply')` audit row and return a courteous auto-reply telling the customer to reply to the latest message.

**Tasks:** add `find_superseded_confirmation_for_thread` helper; wire the stale-reply audit + auto-reply in `handle_confirmation` for the `original is None` branch (AFTER the reschedule-followup and cancellation fallbacks, so legitimate matches win first).

### Phase 6 — Testing & Validation

Three-tier tests per `.kiro/steering/spec-testing-standards.md`: unit (mocked DB), functional (in-memory stateful DB), integration (SQLite or `_StatefulDb`-pattern). Plus property-based tests for the correlation invariant.

**Tasks:** build `test_thread_correlation_lifecycle.py` (unit), `test_post_cancellation_reply_functional.py` (functional), `test_thread_correlation_integration.py` (integration). Extend `test_thread_id_storage.py` for supersession side effects. Extend `test_sms_service_gaps.py` for the third-rung fallback.

---

## STEP-BY-STEP TASKS

IMPORTANT: Execute every task in order, top to bottom. Each task is atomic and independently testable.

### Task 1 — ADD `AlertType.CUSTOMER_RECONSIDER_CANCELLATION` enum member

- **IMPLEMENT**: Append `CUSTOMER_RECONSIDER_CANCELLATION = "customer_reconsider_cancellation"` to the `AlertType` enum in `src/grins_platform/models/enums.py:590-598`. Do not reorder existing members — append at the end of the enum body.
- **PATTERN**: Existing entries `CUSTOMER_CANCELLED_APPOINTMENT`, `CONFIRMATION_NO_REPLY`, `LATE_RESCHEDULE_ATTEMPT` — same shape and snake-case value.
- **IMPORTS**: None new.
- **GOTCHA**: The `alerts` table's `type` column stores a free-string (no DB check constraint on type per `20260416_100100_create_alerts_table.py`). No migration needed for the new enum value.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_enums.py -q` (existing coverage); `uv run python -c "from grins_platform.models.enums import AlertType; assert AlertType.CUSTOMER_RECONSIDER_CANCELLATION.value == 'customer_reconsider_cancellation'"`.

### Task 2 — CREATE migration `20260421_100100_add_sent_messages_superseded_at.py`

- **IMPLEMENT**: New file under `src/grins_platform/migrations/versions/`. Header copies the shape of `20260421_100000_reschedule_request_unique_open_index.py` (revision `20260421_100100`, down_revision `20260421_100000`, requirements tag `gap-03`). `upgrade()` adds `superseded_at TIMESTAMPTZ NULL` to `sent_messages` and creates the partial index `ix_sent_messages_active_confirmation_by_appointment` on `(appointment_id, message_type) WHERE superseded_at IS NULL`. `downgrade()` drops both.
- **PATTERN**: Migration header at `20260421_100000_...py`; add-column shape in prior `sent_messages` migrations (`20260416_100400_widen_sent_messages_for_confirmation_reply_and_followup.py` for precedent of touching this table).
- **IMPORTS**: `from __future__ import annotations`, `from collections.abc import Sequence`, `import sqlalchemy as sa`, `from alembic import op`.
- **GOTCHA**: The partial index does NOT include `provider_thread_id` — that column is already indexed separately (`ix_sent_messages_provider_thread_id`). The new index narrows the lookup for the correlation query, which joins on `(appointment_id, message_type)` when the supersession marker runs.
- **GOTCHA — downgrade order**: drop the index first, then the column. Dropping the column with a partial index that references it will error on some PG minor versions.
- **VALIDATE**:
  ```bash
  uv run alembic upgrade head
  uv run alembic downgrade -1
  uv run alembic upgrade head
  psql "$DATABASE_URL" -c "\d sent_messages" | grep -i "superseded_at"
  psql "$DATABASE_URL" -c "\d sent_messages" | grep -i "ix_sent_messages_active_confirmation_by_appointment"
  ```

### Task 3 — UPDATE `SentMessage` model to declare `superseded_at`

- **IMPLEMENT**: Add the `superseded_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)` column to `src/grins_platform/models/sent_message.py` immediately after `updated_at` (keep `created_at`/`updated_at` last in the audit-column block — insert before them if that's the convention; otherwise append). Add a corresponding `Index("ix_sent_messages_active_confirmation_by_appointment", "appointment_id", "message_type", postgresql_where=text("superseded_at IS NULL"))` entry to `__table_args__`.
- **PATTERN**: Existing columns at `sent_message.py:66-95` — mirror `sent_at`'s Mapped[datetime | None] + `TIMESTAMP(timezone=True)` shape.
- **IMPORTS**: Add `from sqlalchemy import text` alongside existing `from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text` at line 11.
- **GOTCHA**: Don't forget the `text("...")` wrap on `postgresql_where`; a bare string is not accepted.
- **GOTCHA**: Keep the model field and the migration column in lock-step. Do NOT edit the existing `CheckConstraint` at lines 127-136 — `superseded_at` is not message-type-gated.
- **VALIDATE**: `uv run mypy src/grins_platform/models/sent_message.py`; `uv run pyright src/grins_platform/models/sent_message.py`; `uv run pytest src/grins_platform/tests/unit/test_crm_schema_model_constraints.py -q`.

### Task 4 — REWRITE `JobConfirmationService.find_confirmation_message` (widen + filter superseded)

- **IMPLEMENT**: Replace the body of `find_confirmation_message` (`job_confirmation_service.py:853-877`) with the widened version from **Patterns to Follow** above. Keep the `_find_confirmation_message = find_confirmation_message` alias at line 921 (gap L-14 back-compat).
- **ADD** a module-level constant `_CONFIRMATION_LIKE_TYPES` near the top of the file (after `_AUTO_REPLIES`) so both the widened helper and the stale-reply branch (Task 10) share a single source of truth.
- **PATTERN**: Existing `find_reschedule_thread` body at `job_confirmation_service.py:879-916`.
- **FILES**: `src/grins_platform/services/job_confirmation_service.py`.
- **IMPORTS**: None new.
- **GOTCHA**: Do NOT include `APPOINTMENT_CANCELLATION` in `_CONFIRMATION_LIKE_TYPES`. A Y on a cancellation SMS is handled separately by the post-cancel handler.
- **GOTCHA**: The existing docstring references "APPOINTMENT_CONFIRMATION" specifically (line 857). Replace with language that covers confirmation-like messages.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_thread_correlation_lifecycle.py::TestFindConfirmationMessage -v`.

### Task 5 — ADD `JobConfirmationService.find_cancellation_thread`

- **IMPLEMENT**: Add a new public method after `find_reschedule_thread`, following the **find_cancellation_thread** sketch above. Filter includes `superseded_at IS NULL` (so a cancellation that was itself superseded by a reactivation SMS is ignored). Deprecation alias not needed.
- **PATTERN**: `find_reschedule_thread` body (`job_confirmation_service.py:879-916`).
- **FILES**: `src/grins_platform/services/job_confirmation_service.py`.
- **IMPORTS**: None new.
- **GOTCHA**: A cancellation thread can itself be superseded (admin cancels, then reactivates via `update_appointment` — the reactivation sends a reschedule SMS, so the cancellation becomes stale). In that case `find_cancellation_thread` returns None, which is correct: the reschedule SMS owns the thread, and the confirmation-like path will match instead.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_thread_correlation_lifecycle.py::TestFindCancellationThread -v`.

### Task 6 — ADD supersession marker to `SMSService.send_message`

- **IMPLEMENT**: After the successful-send block at `sms_service.py:349-368` (i.e. AFTER `await self.session.flush()` at line 354 and the `logger.info("sms.send.succeeded", ...)` at lines 357-367, BEFORE the `self._touch_lead_last_contacted` call at line 371), add the supersession `UPDATE` per the **Patterns to Follow** snippet. The update runs only when the new row has a non-null `appointment_id` AND the new row's `message_type` is in `_SUPERSEDABLE_TYPES` (confirmation / reschedule / cancellation / reminder).
- **DEFINE** a module-level constant `_SUPERSEDABLE_MESSAGE_TYPES: frozenset[str]` near the top of `sms_service.py` (after existing imports, before the class definitions). Imports required: `from grins_platform.models.enums import MessageType` is already present.
- **FILES**: `src/grins_platform/services/sms_service.py`.
- **IMPORTS**: Inline `from sqlalchemy import update as sa_update` or move to module-level if `update` is not already imported (grep first). Already-present imports: `datetime`, `timezone`.
- **GOTCHA**: The `UPDATE` must exclude `sent_message.id` so the newly-inserted row is never marked as its own successor. Use `SentMessage.id != sent_message.id` in the WHERE clause.
- **GOTCHA**: Do NOT call `session.commit()` from inside `send_message` — the caller owns the transaction. Just `flush()` after the update so downstream reads see it.
- **GOTCHA**: This runs even when the send *succeeded-but-provider returned no thread_id* (thread_id is irrelevant to supersession; what matters is the appointment has a newer authoritative message). The gap-03 spec calls this out as correct.
- **GOTCHA — transactional behavior with errors**: Wrap the supersession UPDATE in a `try/except` that logs+swallows. A failure to supersede is telemetry-worthy but must not fail the outbound send (the customer already received the SMS).
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_thread_id_storage.py -v`; extend `test_thread_id_storage.py` with a test asserting that sending a second confirmation-like SMS for the same appointment stamps the first row's `superseded_at`.

### Task 7 — ADD `_handle_post_cancellation_reply` service method + `handle_post_cancellation_reply` public entry

- **IMPLEMENT**: Add two methods on `JobConfirmationService`:
  ```python
  async def handle_post_cancellation_reply(
      self,
      thread_id: str,
      keyword: ConfirmationKeyword | None,
      raw_body: str,
      from_phone: str,
      provider_sid: str | None = None,
  ) -> dict[str, Any]:
      """Route an inbound reply to a cancellation-notification SMS.

      Fired from ``SMSService._try_confirmation_reply`` when the primary
      confirmation-like lookup AND the reschedule-followup lookup both
      miss and ``find_cancellation_thread`` matches.

      - R → create a new ``RescheduleRequest`` in ``open`` state so the
        admin resolve path can bring the appointment back (the
        reschedule resolver path lives in
        ``AppointmentService.reschedule_for_request`` and handles the
        CANCELLED source state correctly when resolved).
      - Y → raise a ``CUSTOMER_RECONSIDER_CANCELLATION`` admin alert
        (no auto-transition; admin must manually review and reactivate
        via the existing "update appointment" path).
      - Any other keyword / free text → log as ``needs_review``.

      Validates: gap-03 (3.A post-cancellation reply).
      """
  ```
  Body outline:
  1. Call `await self.find_cancellation_thread(thread_id)` — if None, return `{"action": "no_match", "thread_id": thread_id}` and log `handle_post_cancellation_reply` rejected with reason `no_matching_thread`.
  2. Build a `JobConfirmationResponse(status='pending', ...)` exactly like `handle_confirmation` at lines 157-169 (same fields, `sent_message_id=original.id`).
  3. Dispatch:
     - `ConfirmationKeyword.RESCHEDULE`:
       - Load appointment via `db.get(Appointment, ...)`.
       - Create a new `RescheduleRequest(status='open', raw_alternatives_text=raw_body, original_reply_id=response.id)` using the same SAVEPOINT-around-insert pattern as `_handle_reschedule` (catch `IntegrityError` → treat as dedup against the partial unique index from gap-01).
       - Response status `reschedule_requested`.
       - Return dict: `{"action": "post_cancel_reschedule_requested", "appointment_id": ..., "reschedule_request_id": ..., "auto_reply": "Thanks — we'll be in touch with new time options.", "follow_up_sms": <ask-for-2-3-dates text>, "recipient_phone": original.recipient_phone}`.
     - `ConfirmationKeyword.CONFIRM`:
       - Do NOT transition status. Call a new `_dispatch_reconsider_cancellation_alert` helper (see Task 8).
       - Response status `cancel_reconsider_pending`.
       - Return dict: `{"action": "post_cancel_reconsider_pending", "appointment_id": ..., "auto_reply": "Got it — we've flagged this for a callback. Please call us at <BUSINESS_PHONE> to confirm a new time.", "recipient_phone": original.recipient_phone}`.
     - `ConfirmationKeyword.CANCEL` OR any other:
       - Response status `needs_review`.
       - Return dict: `{"action": "needs_review", "response_id": str(response.id), "recipient_phone": original.recipient_phone}`.
- **PATTERN**: Method shape mirrors `handle_confirmation`'s orchestrator (`job_confirmation_service.py:107-198`); reschedule-insert block mirrors `_handle_reschedule` lines 310-357; alert dispatch mirrors `_dispatch_late_reschedule_alert` lines 464-512.
- **FILES**: `src/grins_platform/services/job_confirmation_service.py`.
- **IMPORTS**: `from grins_platform.models.appointment import Appointment` (lazy inside the method to match existing convention at lines 210, 274, 520).
- **GOTCHA — partial unique index on `reschedule_requests`**: gap-01 installed `uq_reschedule_requests_open_per_appointment` (`WHERE status='open'`). If there's already an open request for the CANCELLED appointment (rare but possible), the insert will raise `IntegrityError`. Treat that as a dedup hit — append `raw_body` onto the existing row's `raw_alternatives_text` just like `_append_duplicate_open_request` (`job_confirmation_service.py:377-412`).
- **GOTCHA — R on non-CANCELLED appointment**: `find_cancellation_thread` should only match when `superseded_at IS NULL`. If the appointment was already reactivated (cancellation SMS got superseded by a new reschedule SMS), this path won't fire. Defensive: if the appointment is somehow not CANCELLED at read time, fall through to `_handle_reschedule` via the normal path rather than creating a queue item.
- **GOTCHA — BUSINESS_PHONE substitution**: Reuse the `os.environ.get("BUSINESS_PHONE_NUMBER", "")` pattern at line 426 so the auto-reply message stays consistent with `_build_late_reschedule_reply`.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_thread_correlation_lifecycle.py::TestPostCancellationHandler -v`.

### Task 8 — ADD `_dispatch_reconsider_cancellation_alert` helper + `NotificationService.send_admin_reconsider_cancellation_alert`

- **IMPLEMENT** — JobConfirmationService side: Add `_dispatch_reconsider_cancellation_alert` per the **Patterns to Follow** snippet. Place immediately after `_dispatch_late_reschedule_alert` (`job_confirmation_service.py:464-512`).
- **IMPLEMENT** — NotificationService side: Add `send_admin_reconsider_cancellation_alert` after `send_admin_late_reschedule_alert` at `notification_service.py:1279-1392`. Signature:
  ```python
  async def send_admin_reconsider_cancellation_alert(
      self,
      db: AsyncSession,
      *,
      appointment_id: UUID,
      customer_id: UUID,
      customer_name: str,
      scheduled_at: datetime,
  ) -> None:
  ```
  Body: mirror `send_admin_late_reschedule_alert` exactly, changing only:
  - Alert type: `AlertType.CUSTOMER_RECONSIDER_CANCELLATION.value`
  - Severity: `AlertSeverity.WARNING.value`
  - Message: `f"{customer_name} replied 'Y' to a cancellation SMS — wants to reactivate appointment for {scheduled_at:%Y-%m-%d %H:%M}"`
  - Email subject: `f"Customer wants to un-cancel — {customer_name} ({scheduled_at:%Y-%m-%d %H:%M})"`
  - HTML body: include `customer_name`, `scheduled_at`, `appointment_id`, `customer_id`; state "Customer replied 'Y' to their cancellation notice" explicitly.
  - Log event names: `send_admin_reconsider_cancellation_alert.*`.
- **PATTERN**: `notification_service.py:1279-1392` — mirror exactly, including the two independent try/except blocks (email first, Alert row second) and the "log and swallow" error-handling contract.
- **FILES**: `src/grins_platform/services/job_confirmation_service.py`, `src/grins_platform/services/notification_service.py`.
- **IMPORTS**: None new.
- **GOTCHA**: Per-spec contract: **never re-raise** from this method. Admin notification must never block the customer-facing reply.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_thread_correlation_lifecycle.py::TestReconsiderCancellationAlert -v`.

### Task 9 — WIRE post-cancel fallback into `SMSService._try_confirmation_reply`

- **IMPLEMENT**: In `sms_service.py:770-811`, extend the fallback ladder. After the existing `find_reschedule_thread` fallback (lines 794-803), add a third rung:
  ```python
  # gap-03 (3.A): reply on a cancellation thread — route to
  # post-cancellation handler (Y → reconsider alert, R → new
  # reschedule request, else → needs_review).
  cancellation_original = await svc.find_cancellation_thread(thread_id)
  if cancellation_original is not None:
      result = await svc.handle_post_cancellation_reply(
          thread_id=thread_id,
          keyword=keyword,
          raw_body=body,
          from_phone=from_phone,
          provider_sid=provider_sid,
      )
      # Dispatch the auto-reply + follow-up SMS via the same
      # reply_recipient machinery already in this method (reuse the
      # existing block below).
      original = cancellation_original  # so the existing auto-reply
                                        # plumbing at lines 822-870
                                        # still has a SentMessage to
                                        # derive the reply phone from.
  else:
      return None
  ```
- **REFACTOR** the existing control flow so the reply-sending plumbing (lines 822-870) only runs when we *have* a `result` dict. Cleanest shape: compute `result` in all three branches (confirmation, followup, cancellation) and fall into the shared reply block.
- **PATTERN**: Existing follow-up-thread fallback at `sms_service.py:794-803`.
- **FILES**: `src/grins_platform/services/sms_service.py`.
- **IMPORTS**: None new.
- **GOTCHA**: The cancellation-thread branch must NOT run when the primary confirmation match succeeded (avoid double-handling). Guard with the existing `if original is None:` / `if ... is None:` ladder.
- **GOTCHA — RE-PARSING the keyword**: `keyword` was already parsed earlier in the method (`parse_confirmation_reply(body)` at line 792). Reuse it — don't reparse.
- **GOTCHA — `follow_up_sms` on post-cancel R**: Task 7's handler emits a `follow_up_sms` key when the keyword is R. The existing dispatcher at lines 853-870 already consumes that key and sends via `MessageType.RESCHEDULE_FOLLOWUP`. It Just Works™ — but add a test that confirms it.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_sms_service_gaps.py -k "post_cancel" -v`.

### Task 10 — ADD stale-thread-reply telemetry in `handle_confirmation`

- **IMPLEMENT**: In `handle_confirmation` (`job_confirmation_service.py:107-198`), extend the `original is None` branch. Current behavior: return `{"action": "no_match"}`. New behavior: before returning no_match, call a new helper `_find_superseded_confirmation_for_thread(thread_id)` that re-runs the lookup WITHOUT the `superseded_at IS NULL` filter. If a superseded row matches:
  1. Write a `JobConfirmationResponse(status='stale_thread_reply', sent_message_id=superseded.id, ...)`.
  2. Return `{"action": "stale_thread_reply", "thread_id": thread_id, "auto_reply": <courteous text>, "recipient_phone": superseded.recipient_phone}`.
  3. Log `handle_confirmation.stale_thread` with the appointment_id.
- **DEFINE** the helper method:
  ```python
  async def _find_superseded_confirmation_for_thread(
      self,
      thread_id: str,
  ) -> SentMessage | None:
      """Find the most recent confirmation-like row for the thread_id,
      ignoring the ``superseded_at`` filter. Used only by the stale-reply
      telemetry branch — callers must NOT use this row to drive a status
      transition.

      Validates: gap-03 (3.B telemetry).
      """
  ```
  Filter: `provider_thread_id == thread_id AND message_type IN _CONFIRMATION_LIKE_TYPES AND superseded_at IS NOT NULL`. Order `created_at DESC LIMIT 1`.
- **AUTO-REPLY TEXT**: `"Your appointment was updated — please reply to the most recent message from us, or call us at <BUSINESS_PHONE> for help."` Use the same `BUSINESS_PHONE_NUMBER` env lookup pattern.
- **PATTERN**: Existing `find_confirmation_message` body; existing `_build_late_reschedule_reply` for the BUSINESS_PHONE lookup idiom.
- **FILES**: `src/grins_platform/services/job_confirmation_service.py`.
- **IMPORTS**: None new.
- **GOTCHA — branch ordering**: Do NOT run the stale-thread telemetry BEFORE the reschedule-followup fallback (`find_reschedule_thread`). Order: confirmation-active → reschedule-followup → cancellation → superseded-confirmation-for-telemetry. This is essential because a reschedule-followup thread could share a thread_id with a superseded confirmation — the legitimate followup match must win.
- **GOTCHA — post-cancel reply interaction**: `find_cancellation_thread` is called from `_try_confirmation_reply` in Task 9, NOT from `handle_confirmation`. Don't try to plug the post-cancel handler into `handle_confirmation` — it has its own entry point.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_thread_correlation_lifecycle.py::TestStaleThreadReply -v`.

### Task 11 — CREATE `test_thread_correlation_lifecycle.py` with unit tests

- **IMPLEMENT**: New file `src/grins_platform/tests/unit/test_thread_correlation_lifecycle.py`. Mirror the fixture shapes from `test_reschedule_lifecycle.py:34-102` (`_make_sent_message`, `_make_appointment`, `_make_open_request`, `mock_db`, `_make_execute_side_effect`). Add these test classes:

  **`TestFindConfirmationMessage`:**
  - `test_find_with_appointment_confirmation_returns_row`
  - `test_find_with_appointment_reschedule_returns_row` (gap 3.A)
  - `test_find_with_appointment_reminder_returns_row`
  - `test_find_with_appointment_cancellation_returns_none` (gap 3.A — cancellation is NOT confirmation-like)
  - `test_find_with_superseded_confirmation_returns_none` (gap 3.B)
  - `test_find_with_two_confirmations_returns_most_recent`

  **`TestFindCancellationThread`:**
  - `test_find_with_cancellation_returns_row`
  - `test_find_with_superseded_cancellation_returns_none`
  - `test_find_with_confirmation_returns_none`

  **`TestSupersessionOnSend`:** (tests live in `test_thread_id_storage.py` extension — see Task 13)

  **`TestPostCancellationHandler`:**
  - `test_r_on_cancellation_thread_opens_new_reschedule_request`
  - `test_r_on_cancellation_thread_with_existing_open_request_appends`
  - `test_y_on_cancellation_thread_dispatches_reconsider_alert_no_status_change`
  - `test_c_on_cancellation_thread_routes_needs_review`
  - `test_free_text_on_cancellation_thread_routes_needs_review`
  - `test_handler_returns_no_match_when_no_cancellation_thread`
  - `test_handler_returns_no_match_when_cancellation_thread_superseded`

  **`TestReconsiderCancellationAlert`:**
  - `test_alert_row_persisted_with_correct_type_and_severity`
  - `test_alert_dispatch_never_raises_on_email_failure`
  - `test_alert_dispatch_never_raises_on_db_failure`

  **`TestStaleThreadReply`:**
  - `test_stale_thread_returns_stale_reply_and_courteous_auto_reply` (gap 3.B)
  - `test_stale_thread_logs_audit_row` — assert `JobConfirmationResponse(status='stale_thread_reply')` row was added
  - `test_legitimate_match_does_not_run_stale_path` — active thread wins

- **PATTERN**: `test_reschedule_lifecycle.py:109-550` end-to-end.
- **IMPORTS**: `from unittest.mock import AsyncMock, MagicMock, Mock`; `from uuid import uuid4`; `import pytest`; `from sqlalchemy.exc import IntegrityError`; `from grins_platform.models.enums import AlertType, AppointmentStatus, ConfirmationKeyword, MessageType`; `from grins_platform.services.job_confirmation_service import JobConfirmationService`.
- **FILES**: New file `src/grins_platform/tests/unit/test_thread_correlation_lifecycle.py`.
- **GOTCHA**: `db.execute` side_effect must be an **ordered list** matching the actual call sequence of `handle_confirmation` / `handle_post_cancellation_reply`. Trace the order carefully — handler calls `find_*` (1), then inserts response, then may do open-request lookup (depending on branch). Mirror the bookkeeping in `test_reschedule_lifecycle.py:124-142`.
- **GOTCHA — `@pytest.mark.unit` + `@pytest.mark.asyncio`**: Every test needs both marks. `asyncio_mode = "auto"` may already be set in pyproject.toml, but marking explicitly matches the existing test file's convention.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_thread_correlation_lifecycle.py -v`.

### Task 12 — CREATE `test_post_cancellation_reply_functional.py`

- **IMPLEMENT**: New file `src/grins_platform/tests/functional/test_post_cancellation_reply_functional.py`. Mirror the `_build_mock_db` pattern at `test_yrc_confirmation_functional.py:60-107`. Test classes:
  - `TestPostCancelRescheduleFlow` (R on cancellation thread): `test_creates_reschedule_request_returns_follow_up_sms_and_auto_reply`.
  - `TestPostCancelReconsiderFlow` (Y on cancellation thread): `test_dispatches_admin_alert_and_no_status_change`.
  - `TestPostCancelNeedsReview`: `test_unknown_reply_logs_needs_review`.
- **PATTERN**: `test_yrc_confirmation_functional.py:36-300`.
- **IMPORTS**: `from grins_platform.services.job_confirmation_service import JobConfirmationService`; `from grins_platform.models.enums import ConfirmationKeyword, MessageType, AppointmentStatus`.
- **FILES**: New file.
- **GOTCHA — pytest markers**: `@pytest.mark.functional` and `@pytest.mark.asyncio`. The functional tier uses mocked DB but exercises the full service method (no mocked `find_cancellation_thread`).
- **VALIDATE**: `uv run pytest src/grins_platform/tests/functional/test_post_cancellation_reply_functional.py -v`.

### Task 13 — EXTEND `test_thread_id_storage.py` for supersession side effects

- **IMPLEMENT**: Add a new test class `TestSupersessionOnSend` at the end of `src/grins_platform/tests/unit/test_thread_id_storage.py`:
  - `test_second_confirmation_like_send_marks_first_row_superseded` — send confirmation, then reschedule, assert the confirmation row now has a non-null `superseded_at`.
  - `test_non_confirmation_like_send_does_not_mark_superseded` — send on_the_way, assert no supersession.
  - `test_send_without_appointment_id_does_not_mark_superseded` — send a lead_confirmation SMS (no appointment), assert no UPDATE fires.
  - `test_supersession_update_failure_does_not_fail_send` — mock the `session.execute(update(...))` to raise; assert the send still returns success.
- **PATTERN**: Existing `_make_service` factory in `test_thread_id_storage.py:27-50`.
- **FILES**: `src/grins_platform/tests/unit/test_thread_id_storage.py` (extend, do NOT replace).
- **IMPORTS**: Existing imports already cover this.
- **GOTCHA**: The supersession UPDATE runs inside the SAME session as the insert — mock `session.execute` carefully so both the insert-side-effect assertions AND the update-side-effect assertions work. Use `call_args_list` on `session.execute` to find the update call specifically (by checking for `update` in the stringified statement).
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_thread_id_storage.py -v`.

### Task 14 — EXTEND `test_sms_service_gaps.py` for third-rung fallback

- **IMPLEMENT**: Append tests to `src/grins_platform/tests/unit/test_sms_service_gaps.py`:
  - `test_try_confirmation_reply_falls_through_to_post_cancel_when_only_cancellation_matches` — `find_confirmation_message` returns None, `find_reschedule_thread` returns None, `find_cancellation_thread` returns a row → `handle_post_cancellation_reply` is invoked.
  - `test_try_confirmation_reply_returns_none_when_no_threads_match` — all three return None → `_try_confirmation_reply` returns None (fall through to orphan path).
  - `test_try_confirmation_reply_does_not_call_find_cancellation_when_confirmation_matches` — happy path guard against double-dispatch.
- **PATTERN**: Existing `test_sms_service_gaps.py:360-440` — same mocking approach for `find_confirmation_message`.
- **FILES**: `src/grins_platform/tests/unit/test_sms_service_gaps.py`.
- **IMPORTS**: Existing imports cover this.
- **GOTCHA**: Three-level mock — patch `JobConfirmationService.find_confirmation_message`, `find_reschedule_thread`, `find_cancellation_thread`, AND `handle_post_cancellation_reply`.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_sms_service_gaps.py -k "post_cancel or third_rung" -v`.

### Task 15 — CREATE `test_thread_correlation_integration.py`

- **IMPLEMENT**: New file `src/grins_platform/tests/integration/test_thread_correlation_integration.py`. Mirror the `_StatefulDb` pattern from `test_reschedule_lifecycle_integration.py:32-148`. Add tests:
  - `test_reschedule_notification_reply_y_confirms_new_date` (gap 3.A): seed CONFIRMATION row (`superseded_at` non-null after reschedule) + RESCHEDULE row (`superseded_at IS NULL`) on the same thread_id; a Y reply routes through RESCHEDULE and transitions SCHEDULED→CONFIRMED.
  - `test_cancellation_reply_r_opens_new_reschedule_request_for_cancelled_appt` (gap 3.A post-cancel): seed CANCELLATION row; R reply creates a RescheduleRequest open row referencing the CANCELLED appointment.
  - `test_cancellation_reply_y_raises_reconsider_alert_no_status_change` (gap 3.A post-cancel Y): seed CANCELLATION row; Y reply does not mutate `appt.status`; Alert row written.
  - `test_stale_confirmation_thread_y_reply_routes_to_stale_reply_audit` (gap 3.B): seed CONFIRMATION with `superseded_at` set + RESCHEDULE with `superseded_at IS NULL`; a Y sent to the OLD thread_id hits a thread where the only confirmation-like match is superseded → `stale_thread_reply` response row written; no status transition.
- **PATTERN**: `test_reschedule_lifecycle_integration.py:32-148`. The `_StatefulDb` class may need extension to track superseded rows separately (add a `superseded` attribute or update the `.execute` string-matching logic so the two classes of lookup return correctly).
- **FILES**: New file.
- **IMPORTS**: `from grins_platform.services.job_confirmation_service import JobConfirmationService`; `from grins_platform.models.enums import AppointmentStatus, ConfirmationKeyword, MessageType`.
- **GOTCHA**: The `_StatefulDb` string-matching in `.execute` (`if "sent_messages" in stmt_sql: ...`) is fragile. Consider inspecting the actual SQLAlchemy statement filter via `stmt.compile()` or — simpler — matching substrings like `"superseded_at is null"` vs `"superseded_at is not null"` in the compiled SQL lowercased.
- **GOTCHA — mark `@pytest.mark.integration`**: Per `.kiro/steering/code-standards.md`, integration tests use this marker.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/integration/test_thread_correlation_integration.py -v`.

### Task 16 — ADD property-based tests for the correlation invariant

- **IMPLEMENT**: Extend `src/grins_platform/tests/unit/test_correlation_properties.py` with a new test class `TestSupersessionInvariants`:
  - Hypothesis strategy: generate 2-5 sequential confirmation-like SMSes for the same `appointment_id` (types drawn from `_SUPERSEDABLE_TYPES`). Invariant: after all sends, exactly one row has `superseded_at IS NULL`, and it is the most recent by `created_at`.
  - Second property: for any thread_id tied to a superseded row, `find_confirmation_message` returns None.
- **PATTERN**: Existing `test_correlation_properties.py` (whatever Hypothesis strategies it already uses).
- **FILES**: `src/grins_platform/tests/unit/test_correlation_properties.py`.
- **IMPORTS**: `from hypothesis import given, strategies as st`; existing test imports.
- **GOTCHA**: Hypothesis in-mem tests must not actually commit to a DB — simulate the supersession logic in Python or use the `_StatefulDb` shape. Keep the test runtime < 2s (`hypothesis.settings(max_examples=50, deadline=2000)`).
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_correlation_properties.py::TestSupersessionInvariants -v`.

### Task 17 — RUN the full validation suite

- **IMPLEMENT**: Execute Level 1–5 commands below. Fix any regressions before declaring complete. Update `DEVLOG.md` with a Recent Activity entry per `.kiro/steering/devlog-rules.md` when all levels pass.
- **VALIDATE**: See **VALIDATION COMMANDS** section.

---

## TESTING STRATEGY

Three-tier per `.kiro/steering/spec-testing-standards.md`.

### Unit Tests (mocked DB)

- `test_thread_correlation_lifecycle.py` — every branch of `find_confirmation_message`, `find_cancellation_thread`, `handle_post_cancellation_reply`, `_dispatch_reconsider_cancellation_alert`, and the stale-thread telemetry path.
- `test_thread_id_storage.py` (extended) — supersession UPDATE on outbound.
- `test_sms_service_gaps.py` (extended) — third-rung fallback dispatch.
- `test_correlation_properties.py` (extended) — supersession invariants via Hypothesis.

Target: 90%+ coverage of modified methods. Each new branch in `_handle_post_cancellation_reply` and the stale-thread branch in `handle_confirmation` MUST have at least one test.

### Functional Tests (mocked DB, full service method)

- `test_post_cancellation_reply_functional.py` — end-to-end reply flows with an in-memory DB factory.

### Integration Tests (stateful DB stub)

- `test_thread_correlation_integration.py` — supersession interacting with thread-id lookup; stale-thread reply audit trail; post-cancellation R routing to `reschedule_requests`.

### Edge Cases

- **Concurrent reschedule SMSes for the same appointment** — two admins drag-drop the same appointment within ~100ms. Both sends produce rows; both supersession UPDATEs race. Invariant: AT MOST ONE row has `superseded_at IS NULL`. The later send wins; the earlier send ends up marked superseded when the later UPDATE runs. A stray scenario: both UPDATEs fire before either flush, both see the other as non-superseded, both mark the other — net effect: both rows marked superseded, no active thread. Mitigation: rely on PG row-level locking (UPDATE ... WHERE ... takes row locks). Test with a deliberate race in the integration file; document as a non-goal if the test is too flaky.
- **Reactivation from CANCELLED** — admin un-cancels via `update_appointment` (CANCELLED→SCHEDULED). `_send_reschedule_sms` fires; supersession marker tombstones the CANCELLATION SMS. `find_cancellation_thread` returns None. A Y reply on the old cancellation thread now routes to `find_confirmation_message` → stale-thread telemetry (correct — the cancellation is no longer authoritative).
- **Customer replies to a DRAFT-era SMS** — DRAFT appointments don't get confirmation SMSes (see `appointment_service.py:1444-1447`). Not a concern for this gap.
- **Lead-confirmation SMS (no appointment)** — supersession marker must NOT fire because `appointment_id IS NULL`. Test case: `test_send_without_appointment_id_does_not_mark_superseded`.
- **Reminder SMS after confirmation** — CONFIRMED appointment gets a next-day reminder (message_type=`APPOINTMENT_REMINDER`). Supersession marker fires → confirmation row gets superseded. A Y reply on the reminder thread → routes to the REMINDER SentMessage via `find_confirmation_message` (widened), handler sees the appointment is already CONFIRMED, no-op. Desired behavior — the Y is ignored (idempotent on CONFIRMED). Add a test.
- **Stale reply after two reschedules** — customer replies to the very first confirmation thread, which is now twice-superseded. The stale-thread telemetry branch still fires (finds the superseded row, writes audit, returns courteous auto-reply).
- **Cancellation thread is itself superseded by a reschedule SMS** — covered by edge case #2 above.

---

## VALIDATION COMMANDS

Execute every command. Zero regressions required.

### Level 1: Syntax & Style

```bash
uv run ruff check --fix \
    src/grins_platform/services/job_confirmation_service.py \
    src/grins_platform/services/notification_service.py \
    src/grins_platform/services/sms_service.py \
    src/grins_platform/models/enums.py \
    src/grins_platform/models/sent_message.py \
    src/grins_platform/migrations/versions/20260421_100100_add_sent_messages_superseded_at.py \
    src/grins_platform/tests/unit/test_thread_correlation_lifecycle.py \
    src/grins_platform/tests/functional/test_post_cancellation_reply_functional.py \
    src/grins_platform/tests/integration/test_thread_correlation_integration.py
uv run ruff format --check \
    src/grins_platform/services/job_confirmation_service.py \
    src/grins_platform/services/sms_service.py \
    src/grins_platform/services/notification_service.py \
    src/grins_platform/models/sent_message.py
uv run mypy src/grins_platform
uv run pyright src/grins_platform
```

### Level 2: Unit Tests

```bash
uv run pytest src/grins_platform/tests/unit/test_thread_correlation_lifecycle.py -v
uv run pytest src/grins_platform/tests/unit/test_thread_id_storage.py -v
uv run pytest src/grins_platform/tests/unit/test_sms_service_gaps.py -v
uv run pytest src/grins_platform/tests/unit/test_correlation_properties.py -v
# Regression — ensure gap-01 behavior still holds
uv run pytest src/grins_platform/tests/unit/test_reschedule_lifecycle.py -v
uv run pytest src/grins_platform/tests/unit/test_job_confirmation_service.py -v
```

### Level 3: Functional + Integration Tests

```bash
uv run pytest src/grins_platform/tests/functional/test_post_cancellation_reply_functional.py -v
uv run pytest src/grins_platform/tests/functional/test_yrc_confirmation_functional.py -v  # regression
uv run pytest src/grins_platform/tests/functional/test_reschedule_flow_functional.py -v   # regression
uv run pytest src/grins_platform/tests/integration/test_thread_correlation_integration.py -v
uv run pytest src/grins_platform/tests/integration/test_reschedule_lifecycle_integration.py -v  # regression
```

### Level 4: Migration Validation

```bash
uv run alembic upgrade head
psql "$DATABASE_URL" -c "\d sent_messages" | grep -i "superseded_at"
psql "$DATABASE_URL" -c "\d sent_messages" | grep -i "ix_sent_messages_active_confirmation_by_appointment"
uv run alembic downgrade -1
psql "$DATABASE_URL" -c "\d sent_messages" | grep -i "superseded_at" && echo "ERROR: column should be gone" && exit 1
uv run alembic upgrade head
```

### Level 5: Manual Validation (staging / dev)

**Restriction from project memory — SMS only to +19527373312.** Use that as the test customer phone.

1. Seed appointment A (status=SCHEDULED) with a confirmation SMS sent. Drag-drop A to a new date via the admin calendar; verify:
   - `sent_messages` now has 2 rows for appointment A.
   - First row has `superseded_at IS NOT NULL`.
   - Second row (the reschedule SMS) has `superseded_at IS NULL`.
2. Text "Y" from +19527373312 in reply to the reschedule SMS. Verify:
   - Appointment A transitions SCHEDULED → CONFIRMED.
   - `job_confirmation_responses` has a row with `status='confirmed'`, `sent_message_id` pointing to the RESCHEDULE row.
3. Text "Y" to the OLD (stale) thread. Verify:
   - Appointment A status does NOT change.
   - `job_confirmation_responses` has a row with `status='stale_thread_reply'`.
   - Customer receives the courteous "please reply to the most recent message" auto-reply.
4. Cancel appointment B via admin; customer replies "R" to the cancellation SMS. Verify:
   - A `reschedule_requests` row with `status='open'` exists for appointment B (still CANCELLED).
   - Customer receives the "Thanks, we'll follow up with new times" auto-reply + the "reply with 2-3 dates" follow-up SMS.
   - Admin can now resolve the request (appointment_service.reschedule_for_request) to reactivate.
5. Cancel appointment C; customer replies "Y". Verify:
   - Appointment C status stays CANCELLED.
   - An `alerts` row with `type='customer_reconsider_cancellation'` exists.
   - Admin email received.
6. Run for lead-confirmation SMS (no appointment_id) — confirm supersession UPDATE does not fire (check `sent_messages` for the lead rows).

---

## ACCEPTANCE CRITERIA

- [ ] Gap 3.A (reschedule SMS Y/R/C correlates): Y reply to an `APPOINTMENT_RESCHEDULE` SMS transitions SCHEDULED → CONFIRMED; R reply creates a reschedule request; C reply transitions to CANCELLED.
- [ ] Gap 3.A (cancellation SMS): R reply opens a new `reschedule_requests` row for the CANCELLED appointment; Y reply raises a `CUSTOMER_RECONSIDER_CANCELLATION` admin alert without changing status.
- [ ] Gap 3.B (superseded rows hidden): once a newer confirmation-like SMS is sent for the same appointment, `find_confirmation_message` no longer returns the older row.
- [ ] Stale-thread reply audit: a Y on a superseded thread writes a `job_confirmation_responses` row with `status='stale_thread_reply'` and returns a courteous auto-reply without transitioning status.
- [ ] `sent_messages.superseded_at` column exists after `alembic upgrade head` and is dropped by `alembic downgrade`.
- [ ] `ix_sent_messages_active_confirmation_by_appointment` partial index exists after upgrade.
- [ ] `AlertType.CUSTOMER_RECONSIDER_CANCELLATION` enum member is present.
- [ ] Supersession marker runs on every confirmation-like outbound with a non-null `appointment_id`; never runs for non-confirmation-like types or when `appointment_id IS NULL`.
- [ ] Supersession UPDATE failure does NOT fail the outbound send (log-and-swallow contract).
- [ ] `handle_post_cancellation_reply` handles R / Y / C / free-text correctly; emits follow-up SMS only for R; never raises when alert dispatch fails.
- [ ] `NotificationService.send_admin_reconsider_cancellation_alert` persists an `alerts` row and dispatches email; failures are logged and swallowed.
- [ ] `_try_confirmation_reply` dispatcher fallback order is: confirmation → reschedule-followup → cancellation → None.
- [ ] `find_reschedule_thread` (gap-01) behavior is unchanged.
- [ ] All existing tests in `test_job_confirmation_service.py`, `test_reschedule_lifecycle.py`, `test_thread_id_storage.py`, `test_sms_service_gaps.py`, `test_yrc_confirmation_functional.py`, `test_reschedule_flow_functional.py`, `test_reschedule_lifecycle_integration.py` pass (no regressions).
- [ ] Ruff, MyPy, Pyright pass with zero errors on modified files.
- [ ] Migration upgrade + downgrade + upgrade cycle succeeds.
- [ ] `RescheduleRequestsQueue.tsx` is untouched (no frontend changes).
- [ ] `DEVLOG.md` has a new Recent Activity entry describing the fix.

---

## COMPLETION CHECKLIST

- [ ] Task 1: `AlertType.CUSTOMER_RECONSIDER_CANCELLATION` enum added.
- [ ] Task 2: `20260421_100100_add_sent_messages_superseded_at.py` migration created and reversible.
- [ ] Task 3: `SentMessage` model has `superseded_at` + partial index.
- [ ] Task 4: `find_confirmation_message` widened + superseded filter.
- [ ] Task 5: `find_cancellation_thread` added.
- [ ] Task 6: Supersession marker in `SMSService.send_message`.
- [ ] Task 7: `handle_post_cancellation_reply` + `_handle_post_cancellation_reply` internal handlers.
- [ ] Task 8: `_dispatch_reconsider_cancellation_alert` + `NotificationService.send_admin_reconsider_cancellation_alert`.
- [ ] Task 9: `_try_confirmation_reply` third-rung fallback.
- [ ] Task 10: `handle_confirmation` stale-thread telemetry branch.
- [ ] Task 11: `test_thread_correlation_lifecycle.py` unit tests.
- [ ] Task 12: `test_post_cancellation_reply_functional.py` functional tests.
- [ ] Task 13: `test_thread_id_storage.py` extended for supersession.
- [ ] Task 14: `test_sms_service_gaps.py` extended for third-rung dispatch.
- [ ] Task 15: `test_thread_correlation_integration.py` integration tests.
- [ ] Task 16: `test_correlation_properties.py` Hypothesis extension.
- [ ] Task 17: Level 1–5 validation executed; all green.
- [ ] `DEVLOG.md` entry appended under Recent Activity (template from `.kiro/steering/devlog-rules.md`).

---

## NOTES

**Design decision — supersession marker in `send_message`, not in `AppointmentService`.** Alternatives were: (1) emit supersession from `AppointmentService.update_appointment` / `cancel_appointment` directly, (2) add a `SentMessageRepository.supersede_prior_confirmations_for_appointment(...)` helper called from every send site, (3) the current choice: implicit in `send_message`. The current choice is the most defensive — it guarantees supersession fires for EVERY confirmation-like outbound regardless of which code path sent it (admin UI, bulk resend, API, cron job). The trade is slightly more coupling between `sms_service` and `sent_messages` semantics; the test matrix in Task 13 is the safety net.

**Design decision — exclude `APPOINTMENT_CANCELLATION` from `_CONFIRMATION_LIKE_TYPES`.** A Y on a cancellation SMS does NOT mean "confirm my cancellation is final" — it means "wait no, I want to un-cancel." Routing that through the confirm handler would be silent data loss (the confirm handler requires `status=SCHEDULED` to transition, so the Y would be ignored entirely). Treating it as its own handler + alert is safer and matches the gap doc's proposal.

**Design decision — post-cancel R creates a real `reschedule_requests` row rather than a new AppointmentStatus transition.** Rationale: `reschedule_for_request` already exists (`appointment_service.py:1086+`) and handles the CANCELLED→SCHEDULED transition (`allowed_statuses` at line 1135 includes DRAFT / SCHEDULED / CONFIRMED — CANCELLED is NOT allowed). So the admin path must be extended, BUT that extension is out of scope for this gap — the new open request is still an actionable signal (admin can reactivate via `update_appointment`, then the existing queue path resolves). **Follow-up gap**: extend `reschedule_for_request`'s `allowed_statuses` to include CANCELLED (gap-05 or similar). Flagged in the acceptance criteria as a known limitation — for now the admin manually reactivates first.

**Design decision — stale-thread auto-reply is informational, not punitive.** Text: *"Your appointment was updated — please reply to the most recent message from us, or call us at <BUSINESS_PHONE> for help."* Avoids finger-pointing ("you replied to an old message"), tells them what to do, surfaces the business phone.

**Non-goals:**
- Extending `reschedule_for_request` to accept CANCELLED as a source state (tracked separately).
- Unified inbox UI (gap-16) for orphan / stale / needs_review replies.
- A real Twilio/CallRail round-trip test against the sandbox. The project memory restricts SMS tests to +19527373312 only; staging validation step 5 of the manual checklist covers real-SMS verification.
- Cleanup of legacy rows that exist before the migration runs — the migration does NOT backfill `superseded_at` because we cannot reliably determine which historical rows are newest per `appointment_id` without a separate analysis pass. Fresh appointments post-deploy behave correctly; historical appointments remain correlatable via thread_id but may have multiple active matches that `ORDER BY created_at DESC LIMIT 1` still disambiguates safely.

**Risks:**
- Supersession marker race on concurrent sends (see Edge Cases). Unlikely in practice (admin UI is single-user per action), but flaky integration test would need to be skipped or redesigned.
- Legacy `sent_messages` rows without `superseded_at` set — all pre-deploy rows have `superseded_at IS NULL`, so they all appear "active." If any appointment had multiple confirmation-like rows pre-deploy, the `ORDER BY created_at DESC LIMIT 1` still picks the right one. Not a blocker, but document as a "why don't I need to backfill?" FAQ entry for the admin team if asked.
- Post-cancel R path depends on gap-01's partial unique index (`uq_reschedule_requests_open_per_appointment`). If gap-01 is rolled back, post-cancel R will silently create duplicate open rows. Test `test_r_on_cancellation_thread_with_existing_open_request_appends` guards against this specific regression.
- CallRail thread_id reuse: if CallRail reuses the same thread_id across confirmation → reschedule → cancellation → reactivation, the supersession cascade works. If it assigns a new thread_id per outbound, the `find_*_thread` lookups each match against the thread_id of that outbound, so supersession has no effect on lookup — it only affects lookups that DO share a thread_id. Either way, the fix is safe.

**Confidence score for one-pass success: 8/10.** The patterns are firmly grounded in gap-01's existing infrastructure (partial-index migration, dispatch ladder, alert dispatch, test file layout). Main risk points: (a) the supersession UPDATE inside `send_message` interacts with the session lifecycle in ways that may surface in integration tests rather than unit tests — expect one iteration against a real PG test DB; (b) the `_StatefulDb` integration stub's `.execute` string-matching needs extension to distinguish `superseded_at IS NULL` from `superseded_at IS NOT NULL` lookups — this is the single most likely source of a first-attempt test failure.
