# Feature: E2E Sign-off Bug Resolution (run 2026-05-04)

The following plan should be complete, but it's important that you validate documentation and codebase patterns and task sanity before you start implementing.

Pay special attention to naming of existing utils, types, and models. Import from the right files etc.

## Feature Description

Resolve all six bugs documented in the master E2E sign-off report at
`e2e-screenshots/master-plan/runs/2026-05-04/E2E-SIGNOFF-REPORT.md`. The
report blocks the dev release. Two HIGH-severity bugs (B-1, B-2) and one
MEDIUM bug (B-3) all share the same anti-pattern — uncaught service-layer
exceptions or shape drift — that leak as HTTP 500. B-4 is a missing
state-machine guard. B-5 is a missing audit-log emission. B-6 is the same
uncaught-exception pattern as B-3. The end state: every bug resolved with
a regression test, dev DB cleaned of poisoned invoices, full unit-test
suite green (or at least no net regression vs prior baseline 49).

## User Story

As a release manager
I want every defect candidate from the 2026-05-04 sign-off run resolved with
regression coverage and the dev DB cleaned of poisoned data
So that the release gate is unblocked, monitoring stops mis-classifying
business errors as 5xx, and tech-mobile cash collection produces
readable invoices.

## Problem Statement

Six defect candidates were verified with 100% confidence in the 2026-05-04
sign-off run. Two HIGH bugs block the tech-mobile collection path and the
operator-facing invoice list. Two MEDIUM bugs cause data-integrity drift
(rescheduling EN_ROUTE appointments) and silent operational gaps (no audit
trail on lead routing). Two LOW–MED bugs leak business-logic errors as 5xx
and break test/operator cleanup. Net release-readiness: **BLOCK**.

## Solution Statement

For each bug, mirror an existing pattern in the codebase rather than
inventing new error-handling shapes:

- **B-1** Match the strict `InvoiceLineItem` schema in the writer
  + backfill the dev DB with a one-shot data migration.
- **B-2** Collapse the duplicate `InvalidInvoiceOperationError` /
  `InvoiceNotFoundError` definitions onto the canonical
  `grins_platform.exceptions` versions (re-export from `invoice_service`
  for backward compatibility with tests).
- **B-3** Mirror the soft-fail SMS pattern from
  `invoice_service.send_payment_link` — translate `SMSError` to HTTP 422
  with `attempted_channels` + `sms_failure_reason`.
- **B-4** Add an allowed-set status guard at the top of
  `AppointmentService.reschedule`, raise `InvalidStatusTransitionError`,
  surface as 422.
- **B-5** Mirror `_audit_log_convert_override` — wire
  `AuditLogRepository.create` into the success branches of `move_to_jobs`,
  `move_to_sales`, `mark_contacted`, plus the estimate-override branch.
- **B-6** Catch `IntegrityError` in `LeadService.delete_lead` like
  `customer_tag_service.save_tags` does and re-raise as a domain
  exception that the route surfaces as HTTP 409.

## ⚠ ENVIRONMENT SCOPE — DEV ONLY

**Every change in this plan lands on the `dev` branch and the dev environment ONLY. Production is untouched.**

Hard rules for the implementation agent:

1. **Branch**: All commits go on a feature branch off `dev`, then merged into `dev`. **Do not** open a PR into `main` or push to `main` as part of this work. Master/prod promotion is a separate, deliberate step gated on QA sign-off after dev burn-in.
2. **Database**: The new alembic migration (`20260506_120000_repair_invoice_line_items_shape.py`) applies via Railway's automatic `alembic upgrade head` on dev deploy. **Do not** run `alembic` against the production Railway DB from local or CI. The `env.py` guard at `src/grins_platform/migrations/env.py` already refuses any `*.railway.{app,internal,up.railway.app}` host unless `ALEMBIC_ALLOW_REMOTE=1`. **Do not set that flag.**
3. **Live verification (Task 18)**: Hit only the dev API URL: `https://grins-dev-dev.up.railway.app` (or the matching Vercel preview/dev FE). **Do not** issue verification curls or DELETEs against any prod or staging URL.
4. **No data backfill on prod**: The `UPDATE invoices ...` in the migration runs only where alembic runs — i.e., only on dev. If prod ever needs the same backfill, it will be a deliberate, separately-reviewed maintenance window.
5. **No prod tokens or env vars** in any test, log, or repro artifact. Tests and curls use the dev `admin/admin123` credentials only.
6. **Test allowlists stay in place**: SMS allowlist (`+19527373312`) and email allowlist (`kirillrakitinsecond@gmail.com`) per the standing project guardrails. **Do not** disable, bypass, or widen them as part of this work.

If at any point you find yourself authenticated against a non-dev URL, or your `.env` points at a non-dev DB, stop immediately and re-confirm with the user before proceeding.

---

## Feature Metadata

**Feature Type**: Bug Fix (umbrella; six discrete defects)
**Estimated Complexity**: Medium (low-risk individually; coordinated rollout)
**Target Environment**: **dev only** (see the ENVIRONMENT SCOPE section above).
**Primary Systems Affected**:
- `services/appointment_service.py` (collect_payment, reschedule)
- `services/invoice_service.py` (exception consolidation)
- `services/lead_service.py` (audit log + delete error path)
- `api/v1/appointments.py` (SMS soft-fail, status-guard 422)
- `api/v1/leads.py` (DELETE error handler)
- `migrations/versions/` (one new data-fixup migration)

**Dependencies**: No new libraries. Reuses existing `AuditLogRepository`,
`InvoiceLineItem` schema, `SMSError` hierarchy, `InvalidStatusTransitionError`.

---

## CONTEXT REFERENCES

### Relevant Codebase Files **IMPORTANT: YOU MUST READ THESE FILES BEFORE IMPLEMENTING!**

**B-1 (collect_payment line_items):**
- `src/grins_platform/services/appointment_service.py:2070-2095` — bad write site (`line_items=[{"description":..., "amount":...}]`).
- `src/grins_platform/schemas/invoice.py:26-68` — strict `InvoiceLineItem` schema requiring `description, quantity, unit_price, total`.
- `src/grins_platform/schemas/invoice.py:208-211` — `InvoiceResponse.line_items` typed as `list[InvoiceLineItem] | None`. This is what blows up on serialization.
- `src/grins_platform/models/invoice.py:165-170` — `Invoice.line_items` is `JSONB list[dict]`, schema-less at the DB layer.
- `src/grins_platform/repositories/invoice_repository.py:44-85` — `create()` accepts `line_items: list[dict[str, Any]] | None`.
- `src/grins_platform/services/stripe_payment_link_service.py:166-240` (`_build_line_items`) — already tolerates **both** shapes (`{description, amount}` legacy AND `{description, quantity, unit_price, total}` strict). Fixing the writer **does not** break Stripe.
- `src/grins_platform/services/invoice_service.py:308-366` — `create_invoice` writes correct shape (precedent).

**B-2 (InvalidInvoiceOperationError shadow):**
- `src/grins_platform/exceptions/__init__.py:393-421` — canonical `InvoiceNotFoundError` + `InvalidInvoiceOperationError` (subclass `FieldOperationsError`).
- `src/grins_platform/services/invoice_service.py:75-87` — duplicate local definitions (`class InvalidInvoiceOperationError(Exception)` and `class InvoiceNotFoundError(Exception)`).
- `src/grins_platform/services/__init__.py:14-18` — re-exports from `invoice_service` (must keep working).
- `src/grins_platform/api/v1/invoices.py:25-30, 182, 384, 564, 640, 763` — five `except InvalidInvoiceOperationError` clauses tied to canonical class.
- `src/grins_platform/api/v1/jobs.py:40, 1229` — also catches canonical version.
- `src/grins_platform/services/invoice_pdf_service.py:44` — separate `InvoiceNotFoundError` for PDF. Already aliased in `api/v1/invoices.py:1015` (`as PDFInvoiceNotFoundError`). **Leave alone** — different domain.
- Tests that import the local versions (must still resolve after fix):
  `tests/unit/test_invoice_service.py:26-27`,
  `tests/unit/test_invoice_service_send_link.py:20-21`,
  `tests/unit/test_invoice_bulk_notify_and_sales_metrics.py:20`,
  `tests/test_invoice_api.py:29-30`,
  `tests/integration/test_invoice_integration.py:28`,
  `tests/unit/test_remaining_services.py:39`,
  `tests/unit/test_job_actions.py:23`.

**B-3 (send-confirmation SMSError):**
- `src/grins_platform/api/v1/appointments.py:1180-1216` — only catches `AppointmentNotFoundError` and `InvalidStatusTransitionError`. Add `SMSError` catch.
- `src/grins_platform/services/sms_service.py:162-176` — `class SMSError(Exception)` plus `SMSConsentDeniedError(SMSError)`, `SMSRateLimitDeniedError(SMSError)`.
- `src/grins_platform/services/sms_service.py:484-506` — `send_message` raises `SMSError` from any provider failure (including upstream `RecipientNotAllowedError` from `sms/base.py:17, 102-129`).
- `src/grins_platform/services/invoice_service.py:961-1018` — **soft-fail pattern to mirror**: track `attempted_channels` and `sms_failure_reason`, return them in response.

**B-4 (reschedule status guard):**
- `src/grins_platform/services/appointment_service.py:1173-1240` — `reschedule()`. Currently checks only `not_found` + `staff_conflict`.
- `src/grins_platform/models/enums.py:188-202` — `AppointmentStatus`: PENDING, DRAFT, SCHEDULED, CONFIRMED, EN_ROUTE, IN_PROGRESS, COMPLETED, CANCELLED, NO_SHOW.
- `src/grins_platform/exceptions/__init__.py:222-244` — `InvalidStatusTransitionError(current_status, requested_status)` (already wired in route).
- `src/grins_platform/api/v1/appointments.py:1224-1277` — route. Already imports `InvalidStatusTransitionError` (used by `send_confirmation`); can `except` here too.
- `src/grins_platform/schemas/appointment_ops.py:20-35` — `RescheduleRequest` schema.

**B-5 (lead audit log):**
- `src/grins_platform/services/lead_service.py:2061-2096` — pattern to mirror (`_audit_log_convert_override`).
- `src/grins_platform/services/lead_service.py:1235-1340` — `move_to_jobs` (no audit emission anywhere).
- `src/grins_platform/services/lead_service.py:1342-1420` — `move_to_sales`.
- `src/grins_platform/services/lead_service.py:1587-1617` — `mark_contacted` (currently no `actor_staff_id` parameter — must add).
- `src/grins_platform/api/v1/leads.py:577-633, 641-662` — routes. `move_to_jobs`/`move_to_sales` already pass `_current_user.id`; `mark_lead_contacted` does NOT (line 660).
- `src/grins_platform/repositories/audit_log_repository.py:37-62` — `create()` signature: `action`, `resource_type`, `resource_id`, `actor_id`, `details`, etc.

**B-6 (DELETE lead IntegrityError):**
- `src/grins_platform/api/v1/leads.py:550-569` — route has zero error handling around `service.delete_lead`.
- `src/grins_platform/services/lead_service.py:1106-1121` — service. Repo `delete()` will trigger DB FK violation when SMS consent rows reference the lead.
- `src/grins_platform/services/customer_tag_service.py:99-119` — **pattern to mirror**: `try / except IntegrityError → HTTPException(409)`.
- `src/grins_platform/exceptions/__init__.py` — does NOT yet have a `LeadHasReferencesError`. Plan adds one (subclass of `FieldOperationsError`) for clean route catch.

### New Files to Create

- `src/grins_platform/migrations/versions/20260506_120000_repair_invoice_line_items_shape.py`
  — One-shot data migration: rewrite any `invoices.line_items` rows whose first element has `{description, amount}` shape into the strict `{description, quantity, unit_price, total}` shape. Idempotent (checks `quantity` key absence). `downgrade()` is a no-op (data fixup only).
- `src/grins_platform/tests/unit/test_collect_payment_invoice_shape.py`
  — Regression test: call `AppointmentService.collect_payment(...)`, then `InvoiceResponse.model_validate(result_invoice)` MUST not raise.
- `src/grins_platform/tests/unit/test_send_confirmation_sms_softfail.py`
  — Regression test: `send_confirmation` route returns 422 (not 500) when `SMSService.send_message` raises `SMSError`.
- `src/grins_platform/tests/unit/test_reschedule_status_guard.py`
  — Regression test (matrix): allowed transitions return 200; EN_ROUTE / IN_PROGRESS / COMPLETED / CANCELLED / NO_SHOW return 422 with `InvalidStatusTransitionError` message.
- `src/grins_platform/tests/unit/test_lead_routing_audit_log.py`
  — Regression test: after `move_to_sales` / `move_to_jobs` (with and without force) / `mark_contacted`, `AuditLogRepository.create` was called with the expected `action` value and `actor_id`.
- `src/grins_platform/tests/unit/test_delete_lead_integrity_error.py`
  — Regression test: `delete_lead` with FK-referenced lead → 409 (not 500).

### Relevant Documentation **YOU SHOULD READ THESE BEFORE IMPLEMENTING!**

- [Pydantic v2 — Models / Validation](https://docs.pydantic.dev/latest/concepts/models/#validating-data)
  — Why: `InvoiceLineItem.model_validate` runs the field validators on every list item; the writer must satisfy `quantity > 0`, `unit_price >= 0`, `total >= 0`.
- [SQLAlchemy 2.0 — `IntegrityError`](https://docs.sqlalchemy.org/en/20/errors.html#error-9h9h)
  — Why: distinguishes FK / unique / check / not-null violations. We catch the broad class and surface 409; we do NOT try to introspect `__cause__`.
- [Alembic — Data migrations](https://alembic.sqlalchemy.org/en/latest/cookbook.html#conditional-migration-elements)
  — Why: one-shot fixup pattern using `op.execute(text(...))` + `connection.execute(...)` without ORM coupling.
- [FastAPI — `HTTPException`](https://fastapi.tiangolo.com/reference/exceptions/#fastapi.HTTPException)
  — Why: 422 vs 409 vs 400 semantics. We use 422 for "request was understood but business state forbids it" (status-machine guard, SMS soft-fail), 409 for "FK conflict prevents deletion".
- Local: `.kiro/steering/code-standards.md` — mandatory three-tier testing, structlog patterns, pyright/mypy/ruff zero-error gates.
- Local: `.kiro/steering/api-patterns.md` — endpoint template (`set_request_id`, `DomainLogger.api_event`, `try/except → HTTPException`).
- Local: `DEVLOG.md` (top entry, 2026-05-02) — captures the alembic-against-Railway footgun. Do NOT run alembic against `*.railway.{app,internal}` from local; rely on the env.py guard.

### Patterns to Follow

**Soft-fail SMS pattern (mirror for B-3):** `invoice_service.send_payment_link` builds `attempted_channels: list[Literal["sms","email"]]` and `sms_failure_reason: Literal["consent","rate_limit","provider_error","no_phone"] | None`, then on terminal failure raises `HTTPException(422, detail={message, attempted_channels, sms_failure_reason})`. The same vocabulary should be used in the appointment route so the FE error handler is uniform.

**Audit-log emission pattern (mirror for B-5):**
```python
async def _audit_log_convert_override(...):
    try:
        session = self.lead_repository.session
        repo = AuditLogRepository(session)
        await repo.create(
            action="lead.convert.duplicate_override",
            resource_type="lead",
            resource_id=lead_id,
            actor_id=actor_staff_id,           # propagate; do not None-out
            details={...},
        )
    except Exception:
        self.log_failed("convert_override_audit", lead_id=str(lead_id))
```
**Audit failures must NEVER block the operation.** Catch `Exception`, log, swallow.

**IntegrityError → 409 pattern (mirror for B-6):**
```python
from sqlalchemy.exc import IntegrityError
try:
    await self.repo.delete(...)
    await session.flush()
except IntegrityError as e:
    await session.rollback()
    self.log_failed("delete", error=e)
    raise LeadHasReferencesError(lead_id) from e
```

**Status-guard pattern (mirror for B-4):**
```python
ALLOWED_RESCHEDULE = {
    AppointmentStatus.DRAFT.value,
    AppointmentStatus.SCHEDULED.value,
    AppointmentStatus.CONFIRMED.value,
    AppointmentStatus.PENDING.value,  # no Y/R/C cycle yet
}
if appointment.status not in ALLOWED_RESCHEDULE:
    self.log_rejected("reschedule", reason="invalid_status",
                      current=appointment.status)
    raise InvalidStatusTransitionError(
        current_status=AppointmentStatus(appointment.status),
        requested_status=AppointmentStatus.SCHEDULED,
    )
```
**Note:** `confirmation_sent` is NOT a real `AppointmentStatus` enum value (the report mentioned it but the enum has no such value). Use the four above.

**Naming Conventions:**
- Audit actions for B-5: `lead.move_to_jobs`, `lead.move_to_jobs.estimate_override`, `lead.move_to_sales`, `lead.contacted`. Match existing dot-namespace style (`lead.convert.duplicate_override`, `appointment.cancel`, `sms.provider.switched`).
- Migration filename: `YYYYMMDD_HHMMSS_<short_description>.py`. Use `20260506_120000` (next slot after `20260505_130000`).

**Error Handling:** Per `.kiro/steering/code-standards.md` §4: log once at the throw site, re-raise; the API layer logs at the 4xx/5xx classification site. Never `log.exception(...)` inside the route on a known 4xx path — it pollutes 5xx alerts.

**Logging:**
- Use `LoggerMixin.log_started / log_rejected / log_completed / log_failed` for service-level events.
- Include the actor staff id in audit emissions; never log raw PII.

---

## IMPLEMENTATION PLAN

### Phase 1: Foundation — Exception consolidation (B-2)

Removes the import shadow that masks every business validation as 5xx.
Must land first because B-3, B-4, B-6 all wire new exception paths and we
want a single canonical class set.

**Tasks:**
- Delete the local `InvoiceNotFoundError` and `InvalidInvoiceOperationError` defs in `services/invoice_service.py`.
- Re-import the canonical names from `grins_platform.exceptions` so existing `from grins_platform.services.invoice_service import …` imports still resolve.
- Add a new domain exception `LeadHasReferencesError(FieldOperationsError)` in `exceptions/__init__.py` for B-6.
- Verify `services/__init__.py` re-export still works.

### Phase 2: Service-layer fixes (B-1, B-4, B-5, B-6)

**Tasks:**
- B-1: Fix `appointment_service.py:2079-2084` literal — pass `quantity=1`, `unit_price=str(payment.amount)`, `total=str(payment.amount)`.
- B-4: Add status guard at the top of `appointment_service.reschedule` (after the not-found check, before the staff-conflict check).
- B-5: Add `_audit_log_*` helper and call it from `move_to_jobs` (success + estimate_override branches), `move_to_sales`, `mark_contacted` (also: add `actor_staff_id` parameter to `mark_contacted`).
- B-6: Catch `IntegrityError` in `lead_service.delete_lead`, raise `LeadHasReferencesError`.

### Phase 3: API-layer fixes (B-3, B-6 plumbing)

**Tasks:**
- B-3: Add `except SMSError as e:` to `api/v1/appointments.py:send_confirmation` mirroring the soft-fail pattern; build `attempted_channels` + `sms_failure_reason`.
- B-6 plumbing: Catch `LeadHasReferencesError` in `api/v1/leads.py:delete_lead` → `HTTPException(409, ...)`.
- B-5 plumbing: Pass `actor_staff_id=_current_user.id` from `mark_lead_contacted` route to service.

### Phase 4: Data migration + tests (B-1 backfill, regression coverage)

**Tasks:**
- New alembic revision `20260506_120000_repair_invoice_line_items_shape.py`.
- Five new unit tests (one per bug; B-2 is implicitly covered because B-3/6 tests now expect 4xx instead of 5xx).
- Update one existing test that currently asserts 200 on EN_ROUTE reschedule (`test_schedule_appointment_api.py::TestRescheduleAppointment::test_reschedule_with_valid_data_returns_200` — listed as failing in the report; verify and either fix the test fixture's status or accept the new 422 contract).

### Phase 5: Validation + dev cleanup

**Tasks:**
- Run `uv run pytest -m unit -v` — confirm net failure count <= 49 (prior baseline).
- Run `uv run ruff check src/`, `uv run mypy src/`, `uv run pyright src/`.
- Push branch; let Railway run alembic.
- Spot-check live dev: re-issue the 6 repro `curl` commands from the report and confirm each now returns the corrected status code.
- Manual revert of polluted production-data drift: appointment `36c87d28-3dc1-4002-9d14-85a8d297565d` rescheduled by the report's repro; needs operator-assisted restoration to its original date (out of scope of code changes — flag in DEVLOG).

---

## STEP-BY-STEP TASKS

**IMPORTANT: Execute every task in order, top to bottom. Each task is atomic and independently testable.**

---

### Task 1: UPDATE `src/grins_platform/exceptions/__init__.py` — add `LeadHasReferencesError` (B-6 plumbing)

- **IMPLEMENT**: Add a new class after `InvalidInvoiceOperationError` (~line 421):
  ```python
  class LeadHasReferencesError(FieldOperationsError):
      """Raised when a lead cannot be deleted due to FK references.

      Validates: bughunt 2026-05-04 B-6.
      """

      def __init__(self, lead_id: UUID) -> None:
          self.lead_id = lead_id
          super().__init__(
              f"Cannot delete lead {lead_id}: associated SMS consent or "
              f"campaign records prevent deletion (FK).",
          )
  ```
- **PATTERN**: `exceptions/__init__.py:399-406` (`InvoiceNotFoundError`).
- **IMPORTS**: Already in scope: `from uuid import UUID`. `FieldOperationsError` is the base class used by sibling exceptions in this file.
- **GOTCHA**: Add `"LeadHasReferencesError"` to the `__all__` tuple at the bottom of the file (search for the existing `"InvalidInvoiceOperationError"` entry around line 927 and add nearby alphabetically).
- **VALIDATE**: `uv run python -c "from grins_platform.exceptions import LeadHasReferencesError; print(LeadHasReferencesError.__mro__)"`

---

### Task 2: REFACTOR `src/grins_platform/services/invoice_service.py` — kill local exception shadow (B-2)

- **IMPLEMENT**: Delete lines 75-87 (the two `class InvoiceNotFoundError(Exception)` and `class InvalidInvoiceOperationError(Exception)` definitions). Replace by extending the existing import block at lines 16-19:
  ```python
  from grins_platform.exceptions import (
      InvalidInvoiceOperationError,
      InvoiceNotFoundError,
      LeadOnlyInvoiceError,
      NoContactMethodError,
  )
  ```
- **PATTERN**: `api/v1/invoices.py:25-30` (canonical import already used by routes).
- **IMPORTS**: Two new symbols pulled from `grins_platform.exceptions`.
- **GOTCHA**:
  1. Keep `LienMassNotifyDeprecatedError` (it's still locally defined and re-exported by `services/__init__.py` — actually verify, it isn't. Just leave it as-is at its current location).
  2. Tests import `from grins_platform.services.invoice_service import InvalidInvoiceOperationError` — this still resolves to the canonical class via the new import. No test file edits required.
  3. `services/__init__.py:14-18` re-exports — these continue to work because Python re-exports the re-imported symbol.
- **VALIDATE**:
  ```bash
  uv run python -c "from grins_platform.services.invoice_service import InvalidInvoiceOperationError, InvoiceNotFoundError; \
      from grins_platform.exceptions import InvalidInvoiceOperationError as E1, InvoiceNotFoundError as E2; \
      assert InvalidInvoiceOperationError is E1; assert InvoiceNotFoundError is E2; print('OK')"
  uv run pytest -m unit src/grins_platform/tests/unit/test_invoice_service.py -x -q
  ```

---

### Task 3: UPDATE `src/grins_platform/services/appointment_service.py:2079-2084` — fix line_items shape (B-1)

- **IMPLEMENT**: Replace the `line_items=[…]` literal:
  ```python
  line_items=[
      {
          "description": f"{job.job_type} service",
          "quantity": "1",
          "unit_price": str(payment.amount),
          "total": str(payment.amount),
      },
  ],
  ```
- **PATTERN**: `schemas/invoice.py:26-68` (`InvoiceLineItem` field requirements). Strings are correct: Pydantic v2 coerces decimal strings to `Decimal`.
- **IMPORTS**: None new.
- **GOTCHA**:
  - `payment.amount` is `Decimal`. Use `str(payment.amount)` to keep JSONB human-readable.
  - The Stripe `_build_line_items` helper at `stripe_payment_link_service.py:166-240` already understands BOTH the legacy `{description, amount}` and the strict `{description, quantity, unit_price, total}` shape, so this fix does not break Stripe Payment Link generation.
- **VALIDATE**:
  ```bash
  uv run pytest -m unit src/grins_platform/tests/unit/test_stripe_payment_link_service.py -x -q
  uv run pytest -m unit -k collect_payment -q
  ```

---

### Task 4: CREATE `src/grins_platform/migrations/versions/20260506_120000_repair_invoice_line_items_shape.py` — backfill broken rows (B-1)

- **IMPLEMENT**:
  ```python
  """Repair invoices.line_items rows missing strict-shape fields.

  Bug B-1 (2026-05-04 sign-off): collect_payment wrote
  ``{description, amount}`` items, but ``InvoiceLineItem`` schema requires
  ``{description, quantity, unit_price, total}``. Existing dev rows are
  un-serializable. Rewrite each item missing 'quantity' into the strict
  shape using ``amount`` (or invoice ``total_amount`` as last resort) for
  ``unit_price`` and ``total``, ``"1"`` for ``quantity``.

  Idempotent: rows whose first item already has 'quantity' are untouched.
  Downgrade is a no-op (data fixup only; no column changes).

  Revision ID: 20260506_120000
  Revises: 20260505_130000
  """

  from collections.abc import Sequence
  from typing import Union

  from alembic import op
  from sqlalchemy import text

  revision: str = "20260506_120000"
  down_revision: Union[str, None] = "20260505_130000"
  branch_labels: Union[str, Sequence[str], None] = None
  depends_on: Union[str, Sequence[str], None] = None


  def upgrade() -> None:
      conn = op.get_bind()
      conn.execute(
          text(
              """
              UPDATE invoices i
              SET line_items = sub.fixed
              FROM (
                  SELECT
                      id,
                      jsonb_agg(
                          CASE
                              WHEN item ? 'quantity'
                                  THEN item
                              ELSE jsonb_build_object(
                                  'description', COALESCE(item->>'description', 'Service'),
                                  'quantity',    '1',
                                  'unit_price',  COALESCE(item->>'amount', total_amount::text),
                                  'total',       COALESCE(item->>'amount', total_amount::text)
                              )
                          END
                          ORDER BY ord
                      ) AS fixed
                  FROM invoices,
                       LATERAL jsonb_array_elements(invoices.line_items)
                           WITH ORDINALITY AS t(item, ord)
                  WHERE invoices.line_items IS NOT NULL
                    AND jsonb_array_length(invoices.line_items) > 0
                    AND NOT (invoices.line_items->0 ? 'quantity')
                  GROUP BY invoices.id, invoices.total_amount
              ) AS sub
              WHERE i.id = sub.id
              """
          )
      )


  def downgrade() -> None:
      # No-op: this is a one-shot data fixup. Reverting would re-break
      # historical rows; if needed, run a manual SQL UPDATE.
      pass
  ```
- **PATTERN**: `migrations/versions/20260505_130000_widen_pricing_model_check.py` — same structure (revision id, down_revision, op.execute, no-op-ish downgrade).
- **IMPORTS**: `from sqlalchemy import text`.
- **GOTCHA**:
  - **DO NOT run `alembic upgrade head` against the deployed Railway DB locally** (per `feedback_no_remote_alembic.md`). Push the branch and let Railway apply the migration on deploy.
  - The query is idempotent: re-running is safe.
  - We GROUP BY `invoices.total_amount` because we use it inside the CASE.
  - The `LATERAL jsonb_array_elements ... WITH ORDINALITY` preserves item order.
- **VALIDATE**:
  ```bash
  # locally only (against a disposable DB):
  uv run alembic upgrade 20260506_120000 --sql > /tmp/migration.sql
  cat /tmp/migration.sql  # eyeball the generated DDL
  ```

---

### Task 5: UPDATE `src/grins_platform/services/appointment_service.py:1207` — add reschedule status guard (B-4)

- **IMPLEMENT**: After the `not appointment` check (line 1208-1210) and before the staff-conflict check (line 1213), insert:
  ```python
  ALLOWED_RESCHEDULE_STATUSES = frozenset({
      AppointmentStatus.PENDING.value,
      AppointmentStatus.DRAFT.value,
      AppointmentStatus.SCHEDULED.value,
      AppointmentStatus.CONFIRMED.value,
  })
  if appointment.status not in ALLOWED_RESCHEDULE_STATUSES:
      self.log_rejected(
          "reschedule",
          reason="invalid_status",
          current=appointment.status,
      )
      raise InvalidStatusTransitionError(
          current_status=AppointmentStatus(appointment.status),
          requested_status=AppointmentStatus.SCHEDULED,
      )
  ```
- **PATTERN**: `services/appointment_service.py` already raises `InvalidStatusTransitionError` from `send_confirmation` for status-machine guards.
- **IMPORTS**: `AppointmentStatus` is already imported at the top of the file. `InvalidStatusTransitionError` may not be — check and add to the existing exceptions import block:
  ```python
  from grins_platform.exceptions import (
      AppointmentNotFoundError,
      InvalidStatusTransitionError,  # add if not present
      StaffConflictError,
      ...
  )
  ```
- **GOTCHA**:
  - Use `frozenset({...})` so it's defined once at function scope. Do NOT make it a module constant — the report's wording suggests this is a one-off guard.
  - `AppointmentStatus(appointment.status)` will fail if the column has a value not in the enum (defensive: column is constrained, but if drift, `ValueError` becomes 5xx). If concerned, wrap in `try / except ValueError`. Skip for now — the column has a CHECK constraint.
- **VALIDATE**:
  ```bash
  uv run pytest -m unit -k reschedule -q
  ```

---

### Task 6: UPDATE `src/grins_platform/api/v1/appointments.py:1191-1209` — add SMSError soft-fail (B-3)

- **IMPLEMENT**: Extend the existing `try/except` in `send_confirmation`:
  ```python
  try:
      result = await service.send_confirmation(appointment_id)
  except AppointmentNotFoundError as e:
      _endpoints.log_rejected("send_confirmation", reason="not_found")
      raise HTTPException(
          status_code=status.HTTP_404_NOT_FOUND,
          detail=f"Appointment not found: {e.appointment_id}",
      ) from e
  except InvalidStatusTransitionError as e:
      _endpoints.log_rejected(
          "send_confirmation",
          reason="not_draft",
          current=e.current_status.value,
      )
      raise HTTPException(
          status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
          detail=f"Appointment must be in DRAFT status to send confirmation. "
          f"Current status: {e.current_status.value}",
      ) from e
  except SMSConsentDeniedError as e:
      _endpoints.log_rejected("send_confirmation", reason="sms_consent")
      raise HTTPException(
          status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
          detail={
              "message": "SMS confirmation could not be delivered.",
              "attempted_channels": ["sms"],
              "sms_failure_reason": "consent",
          },
      ) from e
  except SMSRateLimitDeniedError as e:
      _endpoints.log_rejected("send_confirmation", reason="sms_rate_limit")
      raise HTTPException(
          status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
          detail={
              "message": "SMS confirmation could not be delivered.",
              "attempted_channels": ["sms"],
              "sms_failure_reason": "rate_limit",
          },
      ) from e
  except SMSError as e:
      _endpoints.log_rejected("send_confirmation", reason="sms_provider_error")
      raise HTTPException(
          status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
          detail={
              "message": "SMS confirmation could not be delivered.",
              "attempted_channels": ["sms"],
              "sms_failure_reason": "provider_error",
          },
      ) from e
  ```
- **PATTERN**: `services/invoice_service.py:961-1018` (soft-fail vocabulary).
- **IMPORTS**: Add to the file's imports:
  ```python
  from grins_platform.services.sms_service import (
      SMSConsentDeniedError,
      SMSError,
      SMSRateLimitDeniedError,
  )
  ```
  (Verify they're not already imported; the file imports `SMSService` but probably not the error classes.)
- **GOTCHA**:
  - **Catch order matters**: subclasses (`SMSConsentDeniedError`, `SMSRateLimitDeniedError`) before the base (`SMSError`).
  - The `result.status` mapping at line 1212-1216 assumes the call succeeded. Keep the success branch unchanged.
  - The original report mentioned `RecipientNotAllowedError` from `sms/base.py:17`. That gets wrapped into `SMSError` at `sms_service.py:484-506`, so the broad `except SMSError` covers it.
- **VALIDATE**:
  ```bash
  uv run pytest -m unit -k send_confirmation -q
  ```

---

### Task 7: UPDATE `src/grins_platform/services/lead_service.py` — add audit-log emissions (B-5)

- **IMPLEMENT**:
  1. Add helper near `_audit_log_convert_override` (~line 2100):
     ```python
     async def _audit_log_lead_routing(
         self,
         *,
         action: str,
         lead_id: UUID,
         actor_staff_id: UUID | None,
         details: dict[str, Any] | None = None,
     ) -> None:
         """Record a lead-routing AuditLog entry; never blocks the operation."""
         from grins_platform.repositories.audit_log_repository import (  # noqa: PLC0415
             AuditLogRepository,
         )
         try:
             session = self.lead_repository.session
             repo = AuditLogRepository(session)
             await repo.create(
                 action=action,
                 resource_type="lead",
                 resource_id=lead_id,
                 actor_id=actor_staff_id,
                 details={"lead_id": str(lead_id), **(details or {})},
             )
         except Exception:
             self.log_failed(action, lead_id=str(lead_id))
     ```
  2. In `move_to_jobs` (~line 1328 just before `self.log_completed("move_to_jobs", ...)`), add:
     ```python
     await self._audit_log_lead_routing(
         action="lead.move_to_jobs",
         lead_id=lead_id,
         actor_staff_id=actor_staff_id,
         details={"job_id": str(job.id), "customer_id": str(customer_id),
                  "forced": force},
     )
     ```
     Also: in the `_category == "requires_estimate" and force` branch (~line 1283), additionally emit `action="lead.move_to_jobs.estimate_override"` with `details={"situation": situation_key}` BEFORE the customer is created — i.e., right inside the `if` block. Or fold both into the post-create call by adding an `if force and _category == "requires_estimate":` flag in the details.
  3. In `move_to_sales` (~line 1404), add:
     ```python
     await self._audit_log_lead_routing(
         action="lead.move_to_sales",
         lead_id=lead_id,
         actor_staff_id=actor_staff_id,
         details={"sales_entry_id": str(sales_entry.id),
                  "customer_id": str(customer_id)},
     )
     ```
  4. In `mark_contacted` (~line 1587):
     - Add `actor_staff_id: UUID | None = None` parameter (keyword-only via `*,`).
     - At the end, emit `lead.contacted` audit:
       ```python
       await self._audit_log_lead_routing(
           action="lead.contacted",
           lead_id=lead_id,
           actor_staff_id=actor_staff_id,
       )
       ```
- **PATTERN**: `lead_service.py:2061-2096` (`_audit_log_convert_override`).
- **IMPORTS**: `from typing import Any` already present (the file uses `Any` extensively). `AuditLogRepository` is imported lazily inside the helper to avoid the circular import this pattern was originally designed around.
- **GOTCHA**:
  - **Audit must be best-effort.** `try / except Exception / log` and proceed. NEVER let an audit failure roll back the routing operation. The existing `_audit_log_convert_override` does this exactly.
  - `actor_id=None` is currently used by `_audit_log_convert_override`. We have a real actor here — pass it through.
  - The action vocabulary is dot-namespaced (per existing list in the report).
- **VALIDATE**:
  ```bash
  uv run pytest -m unit -k "lead and (move_to or contacted)" -q
  ```

---

### Task 8: UPDATE `src/grins_platform/api/v1/leads.py:660` — pass actor_staff_id to mark_contacted (B-5 plumbing)

- **IMPLEMENT**: Replace `result = await service.mark_contacted(lead_id)` with `result = await service.mark_contacted(lead_id, actor_staff_id=_current_user.id)`.
- **PATTERN**: `api/v1/leads.py:599-601, 631` (already passes `_current_user.id` to `move_to_*`).
- **IMPORTS**: None new.
- **GOTCHA**: Verify `_current_user.id` is a `UUID` (it is — `CurrentActiveUser` returns the `User` model; `User.id` is `Mapped[UUID]`). Match existing call sites.
- **VALIDATE**:
  ```bash
  uv run pyright src/grins_platform/api/v1/leads.py
  ```

---

### Task 9: UPDATE `src/grins_platform/services/lead_service.py:1106-1121` — IntegrityError → LeadHasReferencesError (B-6)

- **IMPLEMENT**:
  ```python
  async def delete_lead(self, lead_id: UUID) -> None:
      """Delete a lead record.

      Validates: Requirement 5.9, CRM2 Req 9.1, bughunt 2026-05-04 B-6.
      """
      lead = await self.lead_repository.get_by_id(lead_id)
      if not lead:
          raise LeadNotFoundError(lead_id)

      try:
          await self.lead_repository.delete(lead_id)
          await self.lead_repository.session.flush()
      except IntegrityError as e:
          await self.lead_repository.session.rollback()
          self.log_failed("delete_lead", error=e, lead_id=str(lead_id))
          raise LeadHasReferencesError(lead_id) from e
  ```
- **PATTERN**: `customer_tag_service.py:99-119` (the IntegrityError → 409 pattern).
- **IMPORTS**: Add `from sqlalchemy.exc import IntegrityError` to the lead_service.py imports. Add `LeadHasReferencesError` to the existing `from grins_platform.exceptions import …` block.
- **GOTCHA**:
  - `await session.rollback()` is required to recover the transaction, otherwise subsequent ops in the same session fail with `PendingRollbackError`.
  - Raising the domain exception (not `HTTPException`) keeps the service layer transport-agnostic — that's enforced by `.kiro/steering/api-patterns.md`.
- **VALIDATE**:
  ```bash
  uv run pytest -m unit -k delete_lead -q
  uv run mypy src/grins_platform/services/lead_service.py
  ```

---

### Task 10: UPDATE `src/grins_platform/api/v1/leads.py:550-569` — catch LeadHasReferencesError → 409 (B-6 plumbing)

- **IMPLEMENT**:
  ```python
  async def delete_lead(
      lead_id: UUID,
      _current_user: CurrentActiveUser,
      service: Annotated[LeadService, Depends(_get_lead_service)],
  ) -> None:
      _endpoints.log_started("delete_lead", lead_id=str(lead_id))
      try:
          await service.delete_lead(lead_id)
      except LeadNotFoundError as e:
          _endpoints.log_rejected("delete_lead", reason="not_found")
          raise HTTPException(
              status_code=status.HTTP_404_NOT_FOUND,
              detail=f"Lead not found: {e.lead_id}",
          ) from e
      except LeadHasReferencesError as e:
          _endpoints.log_rejected("delete_lead", reason="fk_violation")
          raise HTTPException(
              status_code=status.HTTP_409_CONFLICT,
              detail=str(e),
          ) from e
      _endpoints.log_completed("delete_lead", lead_id=str(lead_id))
  ```
- **PATTERN**: `api/v1/invoices.py` 4xx classification on service exceptions.
- **IMPORTS**: Add `LeadHasReferencesError` to the existing `from grins_platform.exceptions import …` block in `leads.py`. Verify `LeadNotFoundError` is imported (if not, add).
- **GOTCHA**: The current route never caught `LeadNotFoundError` either — that means non-existent IDs were 500 too. Adding the `404` branch is also a fix (mention in the PR).
- **VALIDATE**:
  ```bash
  curl -s -o /dev/null -w "%{http_code}" -X DELETE \
      "$API/api/v1/leads/00000000-0000-0000-0000-000000000000" \
      -H "Authorization: Bearer $TOKEN"
  # → 404
  ```

---

### Task 11: CREATE `src/grins_platform/tests/unit/test_collect_payment_invoice_shape.py` — B-1 regression

- **IMPLEMENT**: Test that calls `AppointmentService.collect_payment(...)` and then `InvoiceResponse.model_validate(invoice)` — the validation must NOT raise.
  ```python
  import pytest
  from decimal import Decimal
  from grins_platform.schemas.invoice import InvoiceResponse, InvoiceLineItem

  @pytest.mark.unit
  class TestCollectPaymentInvoiceShape:
      async def test_invoice_created_via_collect_payment_serializes(
          self, appointment_service_with_mocks, ...
      ):
          # Arrange: mocks set up so service.collect_payment writes an invoice
          # Act
          result = await service.collect_payment(...)
          invoice = await invoice_repo.get_by_id(result.invoice_id)
          # Assert: model_validate must not raise
          response = InvoiceResponse.model_validate(invoice)
          # And the line item has the strict shape
          assert response.line_items[0].quantity == Decimal("1")
          assert response.line_items[0].unit_price == result.amount_paid
          assert response.line_items[0].total == result.amount_paid
  ```
- **PATTERN**: `tests/unit/test_invoice_service.py` for fixture style; `.kiro/steering/code-standards.md` §2 for tier markers.
- **IMPORTS**: `pytest`, `Decimal`, schemas.
- **GOTCHA**: Use `@pytest.mark.unit` and `@pytest.mark.asyncio` (or `pytest-asyncio` auto mode if configured globally — check `pyproject.toml`).
- **VALIDATE**:
  ```bash
  uv run pytest -m unit src/grins_platform/tests/unit/test_collect_payment_invoice_shape.py -v
  ```

---

### Task 12: CREATE `src/grins_platform/tests/unit/test_send_confirmation_sms_softfail.py` — B-3 regression

- **IMPLEMENT**: TestClient hits `POST /api/v1/appointments/{id}/send-confirmation` with mocked service that raises `SMSError` (and one each for `SMSConsentDeniedError`, `SMSRateLimitDeniedError`). Assert response status `422` and JSON body has `attempted_channels=["sms"]` and the right `sms_failure_reason`.
- **PATTERN**: `tests/test_invoice_api.py` patterns (TestClient + dependency_overrides).
- **GOTCHA**: The detail field is a dict — assert `response.json()["detail"]["sms_failure_reason"] == "provider_error"` etc.
- **VALIDATE**: `uv run pytest -m unit -k sms_softfail -v`

---

### Task 13: CREATE `src/grins_platform/tests/unit/test_reschedule_status_guard.py` — B-4 regression

- **IMPLEMENT**: Parametrize over `AppointmentStatus`. Allowed (PENDING, DRAFT, SCHEDULED, CONFIRMED) → service call succeeds. Disallowed (EN_ROUTE, IN_PROGRESS, COMPLETED, CANCELLED, NO_SHOW) → `InvalidStatusTransitionError` raised; route returns 422.
- **PATTERN**: `tests/unit/test_appointment_service.py` if it exists, else `tests/test_appointment_api.py`.
- **GOTCHA**: There's an existing `test_schedule_appointment_api.py::TestRescheduleAppointment::test_reschedule_with_valid_data_returns_200` that the report flagged as failing in the unit run. Inspect it: if its fixture seeds an EN_ROUTE appointment, change the fixture to SCHEDULED. If it already used SCHEDULED, the failure was a different issue — leave alone.
- **VALIDATE**:
  ```bash
  uv run pytest -m unit -k "reschedule and status" -v
  uv run pytest -m unit src/grins_platform/tests/test_schedule_appointment_api.py -v
  ```

---

### Task 14: CREATE `src/grins_platform/tests/unit/test_lead_routing_audit_log.py` — B-5 regression

- **IMPLEMENT**: Three tests, one each for `move_to_jobs`, `move_to_sales`, `mark_contacted`. Use `unittest.mock.patch` on `AuditLogRepository.create`. Call the service method, then assert `mock_create.call_args.kwargs["action"]` equals the expected action string and `actor_id` matches the test fixture's UUID.
  - One additional test: `move_to_jobs(force=True)` on a `requires_estimate` lead → expect TWO audit calls (`lead.move_to_jobs.estimate_override` + `lead.move_to_jobs`).
- **PATTERN**: `tests/unit/test_invoice_service.py` mock-style.
- **GOTCHA**: The audit helper uses a lazy import (`from … import AuditLogRepository` inside the function). Patching must target `grins_platform.repositories.audit_log_repository.AuditLogRepository` (the module-level class) so the lazy import resolves to the mock.
- **VALIDATE**: `uv run pytest -m unit -k "lead and audit" -v`

---

### Task 15: CREATE `src/grins_platform/tests/unit/test_delete_lead_integrity_error.py` — B-6 regression

- **IMPLEMENT**: Two tests:
  1. `delete_lead` on a non-existent ID → `LeadNotFoundError` → route 404.
  2. `delete_lead` where `repo.delete` raises `IntegrityError` → service raises `LeadHasReferencesError` → route 409 with descriptive detail.
- **PATTERN**: `tests/unit/test_customer_tag_service.py:172-183` for IntegrityError mocking.
- **VALIDATE**: `uv run pytest -m unit -k "delete_lead" -v`

---

### Task 16: SKIP — confirmed unrelated

The flagged failing test `test_schedule_appointment_api.py::TestRescheduleAppointment::test_reschedule_with_valid_data_returns_200` was inspected and locally re-run during plan finalization. Its fixture uses `mock_appointment.status = "scheduled"` (which is in `ALLOWED_RESCHEDULE_STATUSES`) AND fully mocks `mock_service.reschedule.return_value` so the new service-layer guard never fires for this test. The test's actual failure is a pre-existing Pydantic `ValidationError` for missing nested fields (`reply_state`, `property_summary.*`, `service_agreement_id`) on the MagicMock fixture — unrelated to B-4 and out of scope. **Do not touch this test.**

---

### Task 17: VALIDATE — full unit suite + lints + types

- **VALIDATE**:
  ```bash
  uv run ruff check src/
  uv run ruff format --check src/
  uv run mypy src/
  uv run pyright src/
  uv run pytest -m unit -v 2>&1 | tail -20
  ```
- **GOTCHA**: Net unit failure count must be **<= 49** (prior baseline). Don't try to chase the +29 pre-existing PBT regressions in this plan.

---

### Task 18: DEPLOY — push to **dev only**, verify live

- **IMPLEMENT**:
  - `git push origin <feature-branch>` (a topic branch off `dev`).
  - Open a PR targeting `dev` (NOT `main`). Merge after CI passes.
  - Railway dev service `zealous-heart/dev/Grins-dev` auto-deploys from the `dev` branch and runs `alembic upgrade head` on container start, applying `20260506_120000`.
  - **Do not** push, fast-forward, or merge into `main` as part of this task. Production promotion is a separate, post-burn-in step.
- **VALIDATE**: Re-run the six repro `curl` blocks from the report against `API=https://grins-dev-dev.up.railway.app` ONLY. Each must now return the corrected status code:
  - B-1: `GET /api/v1/invoices/<new id>` → 200; `GET /api/v1/invoices?page_size=10` → 200.
  - B-2: `POST /api/v1/invoices/$INV0/send-link` (zero-amount) → 400 with reason string.
  - B-3: `POST /api/v1/appointments/<non-allowlist>/send-confirmation` → 422 with `sms_failure_reason`.
  - B-4: `PATCH /api/v1/appointments/<en_route>/reschedule` → 422.
  - B-5: After `move-to-sales`, `GET /api/v1/audit-log` shows `lead.move_to_sales` entry.
  - B-6: `DELETE /api/v1/leads/<sms-consented>` → 409.
- **GOTCHA**: If `git push` shows `main` or any non-dev branch as the upstream target, abort and reset. The deployed Vercel FE for dev tracks `dev` (Preview environment); do not push frontend-only changes to `main`.

---

### Task 19: UPDATE `DEVLOG.md` — log the bug-resolution batch

- **IMPLEMENT**: Add an entry at the top (per `.kiro/steering/devlog-rules.md`) under `## Recent Activity`. Category `BUGFIX`. Document the six bugs, the migration backfill, and the residual cleanup item (the production-data drift on appointment `36c87d28-3dc1-4002-9d14-85a8d297565d` needs operator-assisted manual revert — this plan does NOT touch live data via SQL).

---

## TESTING STRATEGY

### Unit Tests (`@pytest.mark.unit`)

- **B-1**: `test_collect_payment_invoice_shape.py` — strict serialization round-trip.
- **B-2**: implicit (existing invoice tests already verify business 4xx; they were silently mis-classifying. After B-2, those tests still pass + B-3 / B-6 tests now pass).
- **B-3**: `test_send_confirmation_sms_softfail.py` — three SMS error subclasses + base class.
- **B-4**: `test_reschedule_status_guard.py` — parametrized over `AppointmentStatus`.
- **B-5**: `test_lead_routing_audit_log.py` — three routing operations + estimate-override branch.
- **B-6**: `test_delete_lead_integrity_error.py` — 404 and 409 paths.

### Functional Tests (`@pytest.mark.functional`)

Optional. The dev-environment live-curl validation in Task 18 substitutes for functional coverage.

### Integration Tests

Not required. Each bug is local to a single service/route boundary.

### Edge Cases

- B-1: `payment.amount = Decimal("0.01")` (smallest non-zero) → strict shape still validates.
- B-1 backfill: rows with `line_items = []` (empty array) → not touched (filter `jsonb_array_length > 0`).
- B-1 backfill: rows with `line_items = NULL` → not touched (filter `IS NOT NULL`).
- B-3: customer with NO phone at all → `SMSService.send_message` short-circuits before raising. Behavior depends on `send_confirmation` service body — verify it raises `SMSError` in that case too, otherwise add a separate handling branch.
- B-4: `appointment.status` value not in the `AppointmentStatus` enum (DB drift) → `AppointmentStatus(value)` raises `ValueError` → 500. Acceptable for now (column has CHECK constraint).
- B-5: audit emission fails (e.g. DB transient) — operation must still succeed. The `try/except` swallow is the expected behavior.
- B-6: lead deletion on a lead with NO references — happy path, returns 204 unchanged.

---

## VALIDATION COMMANDS

Execute every command to ensure zero regressions and 100% feature correctness.

### Level 1: Syntax & Style

```bash
uv run ruff check src/
uv run ruff format --check src/
```

### Level 2: Unit Tests

```bash
uv run pytest -m unit -v 2>&1 | tail -30
# Net failures MUST be <= 49 (prior baseline).
```

### Level 3: Type Checking

```bash
uv run mypy src/
uv run pyright src/
# These were 300 mypy / pre-existing in the report. Don't increase the count.
```

### Level 4: Manual Validation (live dev)

After Railway redeploys with the migration applied, run the six repro `curl` blocks from the original report. Each must return its corrected status code (see Task 18).

### Level 5: Frontend smoke

```bash
cd frontend && npm run typecheck && npm test --run
# Should remain at PASS / 1 fail / 2510 pass (no new regressions).
```

---

## ACCEPTANCE CRITERIA

- [ ] B-1: New `collect_payment` invoices serialize via `InvoiceResponse.model_validate` without raising.
- [ ] B-1: `GET /api/v1/invoices?page_size=10` returns 200 (no poisoned rows).
- [ ] B-1: New alembic migration applied on dev; idempotent re-run leaves state unchanged.
- [ ] B-2: Local `InvalidInvoiceOperationError` and `InvoiceNotFoundError` definitions removed from `invoice_service.py`.
- [ ] B-2: `POST /api/v1/invoices/<zero-amount>/send-link` returns 400 (not 500).
- [ ] B-3: `POST /api/v1/appointments/<id>/send-confirmation` returns 422 with `attempted_channels` + `sms_failure_reason` when SMS provider rejects.
- [ ] B-4: `PATCH /api/v1/appointments/<en_route>/reschedule` returns 422.
- [ ] B-5: `move_to_jobs`, `move_to_sales`, `mark_contacted` each emit one audit log entry; estimate-override path emits two.
- [ ] B-6: `DELETE /api/v1/leads/<consented>` returns 409 (not 500); 404 still works for missing IDs.
- [ ] All five new test files added and passing.
- [ ] Net unit failure count <= 49.
- [ ] Ruff zero violations on changed files; no new mypy/pyright errors on changed files.
- [ ] DEVLOG.md updated with a BUGFIX entry covering all six bugs.

---

## COMPLETION CHECKLIST

- [ ] Task 1 — `LeadHasReferencesError` added.
- [ ] Task 2 — exception shadow killed.
- [ ] Task 3 — collect_payment line_items shape fixed.
- [ ] Task 4 — backfill migration created.
- [ ] Task 5 — reschedule status guard added.
- [ ] Task 6 — send-confirmation SMS soft-fail added.
- [ ] Task 7 — lead audit-log emissions wired.
- [ ] Task 8 — `mark_contacted` actor plumbing.
- [ ] Task 9 — `delete_lead` IntegrityError handling.
- [ ] Task 10 — `delete_lead` route 4xx classification.
- [ ] Task 11 — B-1 regression test.
- [ ] Task 12 — B-3 regression test.
- [ ] Task 13 — B-4 regression test.
- [ ] Task 14 — B-5 regression test.
- [ ] Task 15 — B-6 regression test.
- [ ] Task 16 — existing reschedule test fixture verified/updated.
- [ ] Task 17 — full validation suite green.
- [ ] Task 18 — live dev verification of all six repro paths.
- [ ] Task 19 — DEVLOG entry written.

---

## NOTES

**Out of scope:**
- Pre-existing +29 unit-test regression vs baseline 49 (mostly PBT failures across 12 files). Document but do not fix here.
- `mypy` 300 errors / `ruff` 107 errors residual debt.
- The polluted-data appointment `36c87d28-3dc1-4002-9d14-85a8d297565d` rescheduled by the original B-4 repro: this plan adds the guard but does NOT roll back the existing rescheduled state on dev. Manual operator action required (note in DEVLOG).
- Live SignWell e-signature flows, real Stripe webhook event triggers, and customer-portal approve/reject paths.
- **Production rollout. This plan ships to `dev` only.** Promotion of these fixes to `main`/prod is a separate, deliberate step that must be initiated after dev burn-in and is not authorized by this plan.

**Design decisions:**
- **Shape choice for B-1 backfill**: We use `total_amount` as the fallback when an item has neither `amount` nor `quantity`. This is a defensive default; in practice the bad-shape rows always have `amount` because that's what the writer emitted. We pick `total_amount::text` (not the actual numeric `total`) so JSONB stays string-typed, matching the schema fields.
- **Audit log emission point**: After the operation completes (after `self.log_completed(...)`). If the operation fails, no audit entry is written — which is correct (audit logs *successful* state transitions).
- **`LeadHasReferencesError` as a distinct exception** rather than reusing `IntegrityError` directly in the route: keeps the API layer transport-agnostic and lets us evolve to soft-delete later without changing route handlers (just change the service body).
- **No soft-delete migration in this plan**: the `leads` table has no `deleted_at` column. Adding one is a larger schema change that should be its own plan.
- **No new module-level constants for `ALLOWED_RESCHEDULE_STATUSES`**: scoped inside the function. If it's needed in two places later, promote then.
- **Subclass catch order in B-3 send-confirmation**: subclasses (`SMSConsentDeniedError`, `SMSRateLimitDeniedError`) must precede the base (`SMSError`) — Python's `except` checks linearly.

**Known gotchas:**
- The dev DB had B-1 rows accumulated. The migration MUST run before P12/P13 verification curls.
- Alembic must NOT be run from local against `*.railway.{app,internal}` (env.py guard refuses without `ALEMBIC_ALLOW_REMOTE=1`). Push branch; Railway applies on deploy.
- The `_audit_log_convert_override` helper lazy-imports `AuditLogRepository` inside the function — keep this pattern in `_audit_log_lead_routing` too. Otherwise we pull every model into module scope at import time and trigger the circular import this pattern was created to avoid.

---

**Confidence Score: 10/10** for one-pass implementation success.

All previously-flagged risks have been resolved by direct code inspection:

- ✅ **AuditLog `actor_id` accepts the value we pass.** Confirmed at `src/grins_platform/models/audit_log.py:34-38`: column is `Mapped[UUID | None]` with `ForeignKey("staff.id", ondelete="SET NULL")`. And `CurrentActiveUser` resolves to a `Staff` instance (see `src/grins_platform/api/v1/auth_dependencies.py:301`: `CurrentActiveUser = Annotated[Staff, Depends(get_current_active_user)]`). Thus `_current_user.id` IS a `staff.id` — FK satisfied.

- ✅ **The flagged failing reschedule test is unrelated to B-4.** Confirmed by reading `src/grins_platform/tests/unit/test_schedule_appointment_api.py:51-121`: the test mocks `mock_appointment.status = "scheduled"` (which is in our `ALLOWED_RESCHEDULE_STATUSES`) AND the test fully mocks `service.reschedule.return_value` so the new service-layer guard never fires. The actual failure is an unrelated Pydantic `model_validate` error from missing required fields (`reply_state`, `property_summary.*`, `service_agreement_id`) on the MagicMock — pre-existing tech debt in the +29 PBT regression bucket. **Task 16 in the original plan is dropped — leave the test alone.** Re-confirmed by running it locally: it fails with `ValidationError: property_summary.address — Input should be a valid string`, NOT a status-related 422.

Additional verifications performed (lock in plan correctness):

- ✅ B-3: `services/sms_service.py:162-176` defines `SMSError`, `SMSConsentDeniedError`, `SMSRateLimitDeniedError`. The route file `api/v1/appointments.py` already imports `LoggerMixin` and uses `_endpoints = AppointmentEndpoints()` (line 109). Adding the SMS error imports is a one-line change.
- ✅ B-4: `appointment_service.py:23` already imports `InvalidStatusTransitionError` from `grins_platform.exceptions`. No import changes needed in the service file.
- ✅ B-5: Only 4 callers of `mark_contacted` exist (api/v1/leads.py:660 + 3 test files: `test_lead_service_crm.py:529, 627`, `test_lead_operations_functional.py:303`). Adding a keyword-only `*, actor_staff_id: UUID | None = None` parameter is backwards-compatible with all callers.
- ✅ B-5: `_audit_log_convert_override` uses lazy import of `AuditLogRepository` inside the function. `_audit_log_lead_routing` mirrors that exactly — no top-of-file import needed.
- ✅ B-1 backfill SQL: simulated against representative inputs (broken `{description, amount}`, strict `{description, quantity, unit_price, total}`, mixed). All produce schema-valid output. `total_amount` column is `Numeric(10,2) NOT NULL` (`models/invoice.py:99-102`), so `::text` cast and COALESCE fallback are safe — no NULL leakage to `unit_price`/`total`.
- ✅ B-1: ONLY ONE production writer of `Invoice.line_items` with the broken shape — `appointment_service.py:2079`. The other three matches (`checkout_service.py:315`, `ai/tools/estimates.py:133`, `stripe_payment_link_service.py:101`) are unrelated `line_items` keys (Stripe Checkout sessions, not Invoice JSONB). Fix is surgical.
- ✅ B-2: `services/__init__.py:14-18` re-exports `from grins_platform.services.invoice_service import InvalidInvoiceOperationError, InvoiceNotFoundError`. After our change, those names re-import the canonical classes — re-export still works because Python re-exports the bound name regardless of origin. Tests at `tests/unit/test_invoice_service.py:26-27` and seven other test files importing via `from grins_platform.services.invoice_service import ...` continue to resolve.
- ✅ B-3: Service-level `send_confirmation` tests (`tests/unit/test_send_confirmation.py`) and `test_draft_mode.py` are at the service layer and will not be affected by the route-layer SMSError catches.
- ✅ pyproject.toml has `asyncio_mode = "auto"` (line 592), so new async tests don't need explicit `@pytest.mark.asyncio` decoration. Match the existing test files' style for consistency.
