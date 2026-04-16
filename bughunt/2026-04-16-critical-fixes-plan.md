# Customer Lifecycle Bug Hunt 2026-04-16 — Fix the 6 Critical Findings

## Plan file locations
- Primary (Claude session plan): `/Users/kirillrakitin/.claude/plans/sprightly-mixing-lynx.md`
- Project copy (for team / later reference): `bughunt/2026-04-16-critical-fixes-plan.md` — copied once this plan is approved and we exit plan mode. The two are kept in sync manually; the bug-hunt History section (below) is the canonical record of what merged.

## Handoff prompt (paste into a new context session to execute this plan)

```
I need you to execute a pre-approved implementation plan for fixing 6 critical bugs in the Grins Irrigation Platform customer lifecycle (from bughunt/2026-04-16-customer-lifecycle-bughunt.md).

Working directory: /Users/kirillrakitin/Grins_irrigation_platform
Branch base: dev (merges target main later)
Git user: kirillDR01

STEP 1 — Read the full plan before doing anything else:
  /Users/kirillrakitin/.claude/plans/sprightly-mixing-lynx.md

This plan is already approved. It covers CR-1..CR-6 from the 2026-04-16 bug hunt, organized into three waves, with per-CR file edits, tests, E2E flows, quality gates, and the bug-hunt History section to append after merges.

STEP 2 — HARD SAFETY CONSTRAINTS (see the plan's "Testing safety constraints" section):
  - NEVER send SMS to any phone number other than +19527373312 (user's personal number). That is the ONLY allowed real recipient.
  - NEVER send an email to a real customer in the dev database. Use mocks or a user-supplied test inbox. Ask the user for the test inbox address before any flow that could fire an email.
  - Before any manual or agent-browser E2E flow: seed a dedicated test customer with phone='+19527373312' and the user-supplied test email. Filter out any pre-existing lien-eligible / duplicate rows so the test surface shows only the seed.
  - Tail `docker-compose logs -f api | rg 'sms\.send\.|email\.send\.'` during every manual flow. Abort immediately if a non-allowed recipient appears.

STEP 3 — Copy the plan into the project for team reference:
  cp /Users/kirillrakitin/.claude/plans/sprightly-mixing-lynx.md bughunt/2026-04-16-critical-fixes-plan.md

STEP 4 — Execute in the waves the plan specifies:
  Wave 1 (parallel subagents): CR-2, CR-3, CR-4  — backend-only, one file each
  Wave 2 (parallel subagents): CR-1, CR-6         — backend-only (CR-1) or a contained FE+BE slice (CR-6)
  Wave 3 (sequential, alone):  CR-5              — largest blast radius
  Only advance to the next wave after the prior wave has merged to dev.

For each CR:
  1. Create branch fix/cr-<N>-<short-name> (exact names in the plan).
  2. Make the code changes specified in the plan's per-CR section — do not deviate; if a line number drifted, follow the intent and amend the plan file to reflect reality.
  3. Add/modify tests exactly as listed.
  4. Run the full quality gates before opening a PR:
       uv run ruff check src tests
       uv run mypy src
       uv run pyright src
       uv run pytest src/grins_platform/tests/unit -m unit -q
       uv run pytest src/grins_platform/tests/functional -q
       uv run pytest src/grins_platform/tests/integration -q
       cd frontend && npm run lint && npm run typecheck && npm test -- --run
  5. Commit with a message that references the CR ID and bughunt file. Use the repo's standard commit message style (check recent commits on dev).

STEP 5 — After all six branches are merged to dev:
  - Append the "History — Resolved" table to bughunt/2026-04-16-customer-lifecycle-bughunt.md per the plan. Fill date + commit SHA per branch via `git log -1 --format='%ai %H' <branch>`.
  - Add the BUGFIX DEVLOG entry at the top of DEVLOG.md per the sketch in the plan.

STEP 6 — Run the numbered 1-10 Verification checklist at the end of the plan. Run the three agent-browser E2E flows (CR-1, CR-5, CR-6) under the safety constraints and screenshot to e2e-screenshots/.

RULES:
  - Do not deviate from the plan without telling me first.
  - If you find an ambiguity that requires a product decision, ask me — do not guess.
  - If the code has drifted since the plan was written and a line number or snippet is off, preserve the plan's intent and update the plan file to record the correction.
  - Memory: the user's /Users/kirillrakitin/.claude/projects/-Users-kirillrakitin-Grins-irrigation-platform/memory/ already has an SMS test-number feedback memory. Also add a matching feedback memory for the no-real-customer-email rule.

Begin with STEP 1.
```

## Context

`bughunt/2026-04-16-customer-lifecycle-bughunt.md` produced 48 findings against the customer lifecycle. Six are marked CRITICAL: three are true spec divergences in newly-written code (CR-1, CR-4, CR-5), two are OPEN survivors from the 2026-04-14 hunt (CR-2, CR-3), and one is a missing guard on a high-traffic path (CR-6). Together they break three of the lifecycle's load-bearing promises: Draft Mode silence (CR-1), "steps can be skipped" (CR-2), "repeat C is a no-op" (CR-3), genuine renewals only (CR-4), admin-gated lien notices (CR-5), and real-time dedup on lead conversion (CR-6). This plan fixes all six and appends a resolution history to the bug-hunt document so future reviewers can see which findings are closed without digging through git.

Scope is intentionally CRITICAL-only — the 14 HIGH / 17 MEDIUM / 11 LOW findings are out of scope here.

## Decisions (confirmed with user)

- **CR-1**: `Job.status` stays `to_be_scheduled` and `Job.scheduled_at` stays `None` when `apply_schedule` creates DRAFT appointments. Promotion happens later, when the admin sends confirmation.
- **CR-2**: Add only `AppointmentStatus.SCHEDULED.value` to `job_started`'s appointment pre-state set; DRAFT stays blocked.
- **CR-5**: New **tab** on `/invoices` for the Lien Review Queue (not a new top-level route or dashboard card).
- **CR-5 scope**: MVP — new endpoints + queue UI + per-row Send Notice + client-side-only Dismiss. Include an SMS-consent pre-filter in `send_lien_notice` (trivial; overlaps H-11). **No** backend dismiss persistence in this PR.

---

## ⚠️ Testing safety constraints — NO messages to real customers

The dev database contains real customer records. During any testing, debugging, or E2E validation performed against the dev environment:

- **SMS**: **NEVER** send a real SMS to any customer phone number in the DB. The **only** phone number that may receive real SMS is **`+19527373312`** (user's personal number; user will respond as needed for the test).
- **Email**: **NEVER** send a real email to any customer email address in the DB. Either mock the email sender or override the recipient to a test inbox the user controls (ask the user for the test inbox before relying on it).

### How to comply
- **Unit tests**: mock `SMSService.send_message`, `provider.send_text`, and any email sender (`email_service.send_*`). Assert on the mock's call args — do not actually dispatch.
- **Functional / integration tests**: use the existing test fixtures that stub `SMSProvider` and the email backend. If a test needs a real provider round-trip, parametrise the recipient to `+19527373312` and the email to a user-supplied test inbox — never to seeded customer records.
- **Agent-browser E2E flows (CR-1, CR-5, CR-6)**: before executing the flow, **seed a dedicated test customer** whose `phone='+19527373312'` and `email=<user-supplied test inbox>`. Do **not** drive the flow against any pre-existing seeded customer.
- **CR-5 Send Notice flow**: verify the recipient is `+19527373312` before clicking Confirm. Any other number = abort.
- **CR-6 force-convert flow**: when testing, create both the seed customer A and the duplicate lead B under the `+19527373312` phone. When `force=true` creates a new customer, a welcome email may fire — confirm the email path is mocked or the recipient is a user-supplied test inbox.
- **Log verification**: tail `docker-compose logs -f api | rg 'sms\.send\.|email\.send\.'` during every manual flow and abort immediately if a non-allowed recipient appears.

### Pre-flight checklist for every manual/E2E run
1. Confirm the dev DB has a seed customer with `phone='+19527373312'` and a user-supplied test email.
2. Confirm any template-based SMS/email test exercises point at that seed customer only.
3. Confirm SMS/email sender mocks are installed in the test runner for automated runs.
4. Never run `mass_notify`, `send_lien_notice`, or the bulk confirmation endpoints against the unfiltered dev DB.

## Implementation order (three waves, branch-per-CR)

| Wave | CRs | Why |
|---|---|---|
| **1** — parallel (3 agents) | CR-2, CR-3, CR-4 | Backend-only, single file each, no shared types |
| **2** — parallel (2 agents) | CR-1, CR-6 | Backend-only (CR-1) or contained FE+BE slice (CR-6) |
| **3** — sequential (1 agent) | CR-5 | Largest blast radius: new schemas, two new endpoints, new FE component, `invoiceApi.ts` + `MassNotifyPanel.tsx` edits |

Branch names: `fix/cr-1-apply-schedule-draft`, `fix/cr-2-job-started-scheduled`, `fix/cr-3-repeat-cancel-sms`, `fix/cr-4-invoice-billing-reason`, `fix/cr-5-lien-review-queue`, `fix/cr-6-convert-lead-dedup`.

---

## CR-1 — `apply_schedule` creates DRAFT, not SCHEDULED

### Code changes
**File:** `src/grins_platform/api/v1/schedule.py` (`apply_schedule`, lines 542–610)

- Add import (if missing): `from grins_platform.models.enums import AppointmentStatus`.
- Line 559: `status="scheduled"` → `status=AppointmentStatus.DRAFT.value`.
- Lines 573–578: **remove** the `if job_record:` block that flips `job.status = "scheduled"` and sets `job.scheduled_at`. Leave `job.status` at `to_be_scheduled`.
- Add one structured log line before `db.commit()`: `_endpoints.log_started("apply_schedule.created_as_draft", count=len(created_ids))`.

### Tests
- `src/grins_platform/tests/unit/test_draft_mode.py` (modify)
  - `test_apply_schedule_creates_draft_appointments_not_scheduled`
  - `test_apply_schedule_does_not_promote_job_status`
  - `test_apply_schedule_does_not_set_job_scheduled_at`
- `src/grins_platform/tests/integration/test_appointment_integration.py` (modify)
  - `test_apply_schedule_endpoint_returns_draft_appointments`
  - `test_apply_schedule_emits_no_sms` (assert SMS provider stub not called)

---

## CR-2 — `job_started` promotes SCHEDULED → IN_PROGRESS

### Code changes
**File 1:** `src/grins_platform/models/appointment.py` (`VALID_APPOINTMENT_TRANSITIONS`, lines 39–43)
- Add `AppointmentStatus.IN_PROGRESS.value` to the list under `AppointmentStatus.SCHEDULED.value` (alongside `CONFIRMED`, `EN_ROUTE`, `CANCELLED`).

**File 2:** `src/grins_platform/api/v1/jobs.py` (`job_started`, lines 1379–1386)
- Update the pre-state tuple to `(SCHEDULED, CONFIRMED, EN_ROUTE)`. Do **not** add DRAFT (per decision).

### Tests
- `src/grins_platform/tests/unit/test_on_site_status_progression.py` (modify)
  - `test_job_started_promotes_scheduled_appointment_to_in_progress`
  - `test_job_started_still_promotes_confirmed_to_in_progress` (regression)
  - `test_job_started_still_promotes_en_route_to_in_progress` (regression)
  - `test_job_started_does_not_promote_draft_appointment`
  - `test_job_started_does_not_regress_completed_appointment`
- `src/grins_platform/tests/unit/test_appointment_service_crm.py` (modify)
  - `test_valid_transitions_includes_scheduled_to_in_progress`
- `src/grins_platform/tests/integration/test_combined_status_flow_integration.py` (modify)
  - `test_end_to_end_skip_confirm_and_on_my_way_flow`

---

## CR-3 — Repeat `C` short-circuits (no duplicate SMS)

### Code changes
**File:** `src/grins_platform/services/job_confirmation_service.py` (`_handle_cancel`, lines 232–269)

At the top of the function, after the `appt = await self.db.get(...)` fetch (line 244), insert:

```python
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

`sms_service._try_confirmation_reply` at `src/grins_platform/services/sms_service.py:810-822` already guards with `if auto_reply:`, so an empty string suppresses the dispatch. No change there.

### Tests
- `src/grins_platform/tests/unit/test_job_confirmation_service.py` (modify)
  - `test_handle_cancel_short_circuits_when_already_cancelled`
  - `test_handle_cancel_does_not_rebuild_message_when_already_cancelled` (patch `_build_cancellation_message`, assert `assert_not_called`)
  - `test_handle_cancel_still_cancels_from_scheduled` (regression)
  - `test_handle_cancel_still_cancels_from_confirmed` (regression)
- `src/grins_platform/tests/unit/test_cancellation_sms.py` (modify)
  - `test_repeat_c_reply_produces_empty_auto_reply`
- `src/grins_platform/tests/functional/test_yrc_confirmation_functional.py` (modify)
  - `test_two_consecutive_c_replies_send_exactly_one_sms`

---

## CR-4 — `invoice.paid` renewal gated on `billing_reason`

### Code changes
**File:** `src/grins_platform/api/v1/webhooks.py` (`_handle_invoice_paid`, lines 480–592)

Below the agreement lookup (line 521) compute:

```python
billing_reason = (invoice_obj.get("billing_reason") or "").strip()
is_renewal_cycle = billing_reason == "subscription_cycle"
is_first_invoice = (
    agreement.last_payment_date is None
    and billing_reason in ("subscription_create", "", "manual")
)
```

Rewrite the dispatch at lines 534–572 as a three-branch structure:

1. `if is_first_invoice:` — keep the existing PENDING → ACTIVE transition (lines 536–542).
2. `elif is_renewal_cycle:` — existing renewal logic (ACTIVE transition, `end_date`/`renewal_date` roll, `generate_proposal` or `generate_jobs`).
3. `else:` — log `webhook_invoice_paid_noncycle` with `billing_reason` and skip renewal logic. Payment-fields update (lines 575–582) still runs.

Add `billing_reason` and `is_renewal_cycle` to the final `log_completed` call.

### Tests
**File:** `src/grins_platform/tests/unit/test_webhook_handlers.py` (modify; confirm this is the right test file — the Stripe webhook fixtures live there per `_make_event()` / `_make_agreement()` pattern)

- `test_invoice_paid_subscription_create_transitions_to_active_no_renewal`
- `test_invoice_paid_subscription_cycle_triggers_renewal_proposal`
- `test_invoice_paid_subscription_cycle_without_auto_renew_generates_jobs`
- `test_invoice_paid_subscription_update_skips_renewal_logic`
- `test_invoice_paid_manual_skips_renewal_logic`
- `test_invoice_paid_always_updates_payment_fields` (parametrize all four `billing_reason` values)
- `test_invoice_paid_missing_billing_reason_first_payment_activates_agreement`

---

## CR-5 — Lien notices moved to admin review queue

### Backend — new service methods

**File:** `src/grins_platform/services/invoice_service.py` (add below `mass_notify`, around line 930)

- `compute_lien_candidates(*, days_past_due: int = 60, min_amount: float = 500.0) -> list[LienCandidateResponse]`:
  - Reuse `self.invoice_repository.find_lien_eligible(days_past_due, Decimal(str(min_amount)))`.
  - Group by `customer_id`. Per group: `oldest_invoice_age_days` = max per-invoice days past due; `total_past_due_amount` = sum `total_amount`; collect invoice IDs and numbers.
  - Wrap with `self.log_started` / `self.log_completed`.

- `send_lien_notice(*, customer_id: UUID, admin_user_id: UUID) -> LienNoticeResult`:
  - Re-run `find_lien_eligible_for_customer(customer_id, days_past_due, min_amount)` (new repo method; add to `InvoiceRepository` mirroring the existing `find_lien_eligible`).
  - **SMS-consent pre-filter**: query `SmsConsentRecord` for the customer. If opted out, return `LienNoticeResult(success=False, message="customer_opted_out", ...)` without sending.
  - Otherwise build the lien message body from the existing `_DEFAULT_TEMPLATES` template and dispatch via `SMSService.send_message(message_type=MessageType.PAYMENT_REMINDER, consent_type="transactional")`.
  - Write an `AuditLog` entry using the pattern from `appointment_service.py:595` (`_record_cancellation_audit`). Action: `invoice.lien_notice.sent`. Details: `admin_user_id`, `customer_id`, `invoice_ids`, `sent_at`, `sms_message_id`.

- **Deprecate `mass_notify("lien_eligible")`**: raise a new `LienMassNotifyDeprecatedError` near the top of `mass_notify`. The endpoint catches it and returns 400 with a message pointing at the new endpoints. (Do not raise `HTTPException` inside the service — translate in the router layer per codebase convention.)

### Backend — new schemas

**File:** `src/grins_platform/schemas/invoice.py`

```python
class LienCandidateResponse(BaseModel):
    customer_id: UUID
    customer_name: str
    customer_phone: str | None
    oldest_invoice_age_days: int
    total_past_due_amount: Decimal
    invoice_ids: list[UUID]
    invoice_numbers: list[str]

class LienNoticeResult(BaseModel):
    success: bool
    customer_id: UUID
    sent_at: datetime | None
    sms_message_id: UUID | None
    message: str
```

### Backend — new endpoints

**File:** `src/grins_platform/api/v1/invoices.py` (next to the existing `mass_notify` route)

- `GET /api/v1/invoices/lien-candidates?days_past_due=60&min_amount=500` → `list[LienCandidateResponse]`. Auth: `ManagerOrAdminUser`.
- `POST /api/v1/invoices/lien-notices/{customer_id}/send` → `LienNoticeResult`. Auth: `ManagerOrAdminUser`. Passes `user.id` to `send_lien_notice` for audit.
- Both wrapped with the standard `_endpoints.log_started/log_completed/log_failed` pattern.

### Frontend — new types

**File:** `frontend/src/features/invoices/types/index.ts`

```typescript
export interface LienCandidate {
  customer_id: string;
  customer_name: string;
  customer_phone: string | null;
  oldest_invoice_age_days: number;
  total_past_due_amount: string;
  invoice_ids: string[];
  invoice_numbers: string[];
}

export interface LienNoticeResult {
  success: boolean;
  customer_id: string;
  sent_at: string | null;
  sms_message_id: string | null;
  message: string;
}
```

### Frontend — API + hooks

- `frontend/src/features/invoices/api/invoiceApi.ts`: add `lienCandidates(params)` and `sendLienNotice(customerId)`.
- `frontend/src/features/invoices/hooks/useLienReview.ts` (new):
  - `useLienCandidates(params)` — `useQuery` keyed by `invoiceKeys.lienCandidates(params)`; extend the key factory in `useInvoices.ts`.
  - `useSendLienNotice()` — `useMutation`. On success, invalidate `invoiceKeys.lienCandidates()`, `invoiceKeys.overdue()`, `invoiceKeys.lists()` and `toast.success`.

### Frontend — components

- `frontend/src/features/invoices/components/LienReviewQueue.tsx` (new) — model after `frontend/src/features/schedule/components/RescheduleRequestsQueue.tsx`. Cards layout, each row shows customer name, phone, oldest age, total past-due, invoice chips. Per-row buttons: **Send Notice** (opens confirm dialog) and **Dismiss** (client-side local state). Empty state, skeleton loading, error message. `data-testid` attributes: `lien-queue`, `lien-candidate-row-{customerId}`, `send-lien-btn-{customerId}`, `dismiss-lien-btn-{customerId}`, `confirm-send-lien-btn`.

- `frontend/src/features/invoices/components/MassNotifyPanel.tsx` (edit) — remove the `lien_eligible` option from the select and delete the lien-days / lien-amount inputs (lines 108–131).

- **Placement**: wrap `InvoiceList` in a `<Tabs>` component with two tabs: "All Invoices" and "Lien Review". Tab panel state via React Router search param (e.g., `?tab=lien-review`) to keep the router consistent with steering's route-state guidance.

### Tests

**Backend:**
- `src/grins_platform/tests/unit/test_invoice_service.py` (modify)
  - `test_compute_lien_candidates_groups_by_customer`
  - `test_compute_lien_candidates_filters_by_days_past_due`
  - `test_compute_lien_candidates_filters_by_min_amount`
  - `test_send_lien_notice_sends_sms_and_writes_audit`
  - `test_send_lien_notice_fails_when_customer_opted_out`
  - `test_send_lien_notice_fails_when_customer_has_no_phone`
  - `test_mass_notify_lien_eligible_raises_deprecation_error`
- `src/grins_platform/tests/integration/test_invoice_integration.py` (modify)
  - `test_get_lien_candidates_endpoint_returns_review_list`
  - `test_send_lien_notice_endpoint_sends_sms_and_returns_success`

**Frontend:**
- `frontend/src/features/invoices/components/LienReviewQueue.test.tsx` (new) — `renders candidate cards from API data`, `calls sendLienNotice on confirm click`, `hides row after dismiss`, `renders empty state when no candidates`.
- `frontend/src/features/invoices/components/MassNotifyPanel.test.tsx` (new) — `does not offer lien_eligible option`.
- `frontend/src/features/invoices/hooks/useLienReview.test.tsx` (new) — `useLienCandidates fetches and returns array`, `useSendLienNotice invalidates lien-candidates on success`.

---

## CR-6 — `convert_lead` runs Tier-1 dedup with force override

### Backend — service

**File:** `src/grins_platform/services/lead_service.py` (module-top + `convert_lead` at lines 909–962)

- Add exception at module top:
  ```python
  class LeadDuplicateFoundError(Exception):
      def __init__(
          self,
          lead_id: UUID,
          duplicates: list[CustomerResponse],
          phone: str | None,
          email: str | None,
      ) -> None:
          self.lead_id = lead_id
          self.duplicates = duplicates
          self.phone = phone
          self.email = email
          super().__init__(f"Duplicate customers found for lead {lead_id}")
  ```
- Inside `convert_lead`, between step 3 (name split, line 948) and step 4 (`create_customer`, line 962), call:
  ```python
  dups = await self.customer_service.check_tier1_duplicates(
      phone=lead.phone, email=lead.email,
  )
  if dups and not data.force:
      raise LeadDuplicateFoundError(
          lead_id=lead_id, duplicates=dups,
          phone=lead.phone, email=lead.email,
      )
  if dups and data.force:
      # Audit the override (mirror _record_cancellation_audit pattern)
      await self._audit_log_convert_override(
          lead_id=lead_id,
          duplicate_customer_ids=[d.id for d in dups],
      )
  ```
- Add helper `_audit_log_convert_override` at the end of `LeadService` modeled after `appointment_service._record_cancellation_audit` (AuditLog row, action=`lead.convert.duplicate_override`, details include `lead_id`, `duplicate_customer_ids`, `forced=True`).

### Backend — schema

**File:** `src/grins_platform/schemas/lead.py` (`LeadConversionRequest`, lines 501–525)

```python
force: bool = Field(
    default=False,
    description="Override Tier-1 duplicate check — create a new customer even if an existing customer shares phone or email.",
)
```

### Backend — endpoint

**File:** `src/grins_platform/api/v1/leads.py` (`convert_lead`, lines 482–509)

- Import `LeadDuplicateFoundError`.
- Wrap the service call in try/except. On `LeadDuplicateFoundError`, raise:
  ```python
  raise HTTPException(
      status_code=status.HTTP_409_CONFLICT,
      detail={
          "error": "duplicate_found",
          "lead_id": str(e.lead_id),
          "phone": e.phone,
          "email": e.email,
          "duplicates": [d.model_dump(mode="json") for d in e.duplicates],
      },
  )
  ```
- Update `@router.post` decorator with `responses={409: {"description": "Duplicate customer found"}}`.
- Add `_endpoints.log_rejected("convert_lead", reason="duplicate_found", ...)` before the HTTPException raise.

### Frontend

- `frontend/src/features/leads/types/index.ts` — add `force?: boolean` to `LeadConversionRequest`; add `DuplicateConflictError` interface mirroring the 409 `detail` shape.
- `frontend/src/features/leads/utils/isDuplicateConflict.ts` (new) — typeguard returning `err is AxiosError<{detail: DuplicateConflictError}>`.
- `frontend/src/features/leads/components/LeadConversionConflictModal.tsx` (new) — wraps `<DuplicateWarning>` (from `features/customers/components/DuplicateWarning.tsx`) in a `<Dialog>`. Props: `{open, onClose, duplicates, onUseExisting, onConvertAnyway}`. Footer: "Cancel" + "Convert anyway". `data-testid`: `lead-conversion-conflict-modal`, `convert-anyway-btn`, `cancel-convert-btn`.
- `frontend/src/features/leads/components/LeadsList.tsx` (edit) — in the handlers that call `useConvertLead().mutateAsync` / `useMoveToJobs().mutateAsync` / `useMoveToSales().mutateAsync`, wrap in `try { ... } catch (err) { if (isDuplicateConflict(err)) { setConflictState({...}); return; } throw err; }`. Render `<LeadConversionConflictModal>` when `conflictState !== null`. `onConvertAnyway` retries the mutation with `force: true`. `onUseExisting(customer)` calls `navigate(\`/customers/\${customer.id}\`)`.

### Tests

**Backend:**
- `src/grins_platform/tests/unit/test_lead_api.py` (modify)
  - `test_convert_lead_no_duplicates_returns_success`
  - `test_convert_lead_with_duplicates_and_force_false_returns_409`
  - `test_convert_lead_with_duplicates_and_force_true_creates_customer`
  - `test_convert_lead_409_detail_contains_duplicate_list`
  - `test_convert_lead_force_true_writes_audit_log`
- `src/grins_platform/tests/unit/test_lead_service.py` (modify)
  - `test_convert_lead_calls_check_tier1_duplicates` (mock assertion)
- `src/grins_platform/tests/functional/test_lead_operations_functional.py` (modify)
  - `test_convert_lead_full_flow_with_real_duplicate_returns_409`
  - `test_convert_lead_force_override_full_flow`

**Frontend:**
- `frontend/src/features/leads/components/LeadsList.test.tsx` (modify)
  - `shows duplicate conflict modal when convert returns 409`
  - `retries with force=true when user clicks Convert anyway`
  - `navigates to customer detail when user clicks Use existing`
- `frontend/src/features/leads/components/LeadConversionConflictModal.test.tsx` (new)
  - `renders list of duplicate customers`
  - `fires onConvertAnyway when button clicked`
  - `fires onUseExisting with correct customer id`

---

## Cross-cutting quality gates

Run per-branch and again on an integration branch before merging to `dev`:

```bash
cd /Users/kirillrakitin/Grins_irrigation_platform
uv run ruff check src tests
uv run mypy src
uv run pyright src
uv run pytest src/grins_platform/tests/unit -m unit -q
uv run pytest src/grins_platform/tests/functional -q
uv run pytest src/grins_platform/tests/integration -q

cd frontend
npm run lint
npm run typecheck
npm test -- --run
```

All gates must pass with zero errors per `spec-quality-gates.md` and `code-standards.md`.

---

## E2E / agent-browser validation

Only CRs with user-visible surfaces need browser flows. Start `docker-compose up` + `cd frontend && npm run dev` before each.

**Before any flow below:** complete the pre-flight checklist in the Testing safety constraints section. Every customer touched by these flows must either be a fresh seed tied to `+19527373312` + a user-supplied test inbox, or behind a mock. If any flow would dispatch an SMS to a pre-existing dev-DB customer, abort and re-seed.

### CR-1 — draft calendar rendering
1. Seed a test customer with `phone='+19527373312'`. Open a Job on that customer.
2. Open `http://localhost:5173/schedule`.
3. Generate + Apply Schedule.
4. Assert calendar cards render with **dotted** DRAFT border for all newly-created appointments.
5. Open `AppointmentDetail` on one card — assert `status = "draft"` badge, no confirmation-sent timestamp.
6. Tail `docker-compose logs -f api | rg 'sms\.'` — assert no `sms.send.started` during apply.
7. Click "Send Confirmation" on one card — appointment flips to SCHEDULED, SMS fires **to `+19527373312` only** (the seed customer's number), border becomes solid. Abort if the log shows any other recipient.

### CR-5 — lien queue UI
1. Seed **one** test customer with `phone='+19527373312'` owning a >60-day past-due ≥$500 invoice. Delete or filter out any other lien-eligible rows before the test so the queue shows only the seed.
2. Open `http://localhost:5173/invoices?tab=lien-review`.
3. Assert exactly one candidate card renders — the seed customer.
4. Click **Send Notice** → confirm dialog → verify recipient preview shows `+19527373312` → confirm.
5. Assert toast "Lien notice sent", row refetches out, SMS log shows exactly one outbound to `+19527373312`.
6. Open `MassNotifyPanel` — assert `lien_eligible` no longer listed.
7. Screenshot each step to `e2e-screenshots/cr5-lien-*.png`.

### CR-6 — duplicate-warning modal on convert
1. Seed customer A with phone `+19527373312` and a user-supplied test email.
2. Create lead B with the **same** phone `+19527373312`.
3. Open `/leads` → click **Move to Jobs** on lead B.
4. Assert `<LeadConversionConflictModal>` opens with customer A listed.
5. Click **Use existing** → assert navigation to `/customers/{A.id}`.
6. Return → click **Move to Jobs** again → click **Convert anyway** → assert success toast + customer count increments. Confirm any welcome email path is mocked or the email target is the user-supplied test inbox.
7. Assert `AuditLog` contains `lead.convert.duplicate_override` entry.

No browser validation required for CR-2, CR-3, CR-4 — functional/integration tests cover them.

---

## Update the bug hunt document — History section

**File:** `bughunt/2026-04-16-customer-lifecycle-bughunt.md`

Append at the **very bottom**, after the existing "Summary table" section:

```markdown

---

## History — Resolved

| Finding | Resolution Date | Commit SHA | Branch | Notes |
|---|---|---|---|---|
| CR-1 — `apply_schedule` creates SCHEDULED not DRAFT | YYYY-MM-DD | `<sha>` | `fix/cr-1-apply-schedule-draft` | Default to `AppointmentStatus.DRAFT.value`; `Job.status` stays `to_be_scheduled`. |
| CR-2 — `job_started` doesn't promote SCHEDULED → IN_PROGRESS | YYYY-MM-DD | `<sha>` | `fix/cr-2-job-started-scheduled` | Added `SCHEDULED` to pre-state set; transitions table now allows `SCHEDULED → IN_PROGRESS`. |
| CR-3 — Repeat `C` sends duplicate cancellation SMS | YYYY-MM-DD | `<sha>` | `fix/cr-3-repeat-cancel-sms` | `_handle_cancel` short-circuits when already CANCELLED; empty `auto_reply` suppresses SMS. |
| CR-4 — `invoice.paid` misclassifies non-first invoices as renewals | YYYY-MM-DD | `<sha>` | `fix/cr-4-invoice-billing-reason` | Renewal branch now gated on Stripe `billing_reason == "subscription_cycle"`. |
| CR-5 — Lien SMS sent immediately instead of queued | YYYY-MM-DD | `<sha>` | `fix/cr-5-lien-review-queue` | Split into `compute_lien_candidates` + `send_lien_notice` with SMS-consent pre-filter and audit log; new `/invoices?tab=lien-review` queue UI. `mass_notify("lien_eligible")` now returns 400. |
| CR-6 — `convert_lead` skips Tier-1 dedup | YYYY-MM-DD | `<sha>` | `fix/cr-6-convert-lead-dedup` | Added `force` flag; raises `LeadDuplicateFoundError` → 409 with structured detail; FE surfaces conflict modal with "Use existing" + "Convert anyway". |
```

Replace `YYYY-MM-DD` and `<sha>` with the output of `git log -1 --format='%ai %H' <branch>` at merge time.

---

## DEVLOG entry (sketch)

Insert at the top of `DEVLOG.md` under `## Recent Activity`, before the existing `## [2026-02-07 21:30]` block:

```markdown
## [2026-04-16 HH:MM] - BUGFIX: 6 Critical Customer Lifecycle Fixes (CR-1..CR-6)

### What Was Accomplished
Closed all 6 CRITICAL findings from the 2026-04-16 customer-lifecycle bug hunt.

### Technical Details
(fill from per-CR diffs)

### Files Created
- src/grins_platform/schemas/invoice.py (LienCandidateResponse, LienNoticeResult)
- frontend/src/features/invoices/components/LienReviewQueue.tsx + test
- frontend/src/features/invoices/hooks/useLienReview.ts + test
- frontend/src/features/leads/components/LeadConversionConflictModal.tsx + test
- frontend/src/features/leads/utils/isDuplicateConflict.ts

### Files Modified
(enumerate per branch)

### Quality Check Results
- Ruff / MyPy / Pyright: 0 errors
- Backend unit + functional + integration: green
- Frontend lint + typecheck + tests: green
- agent-browser flows verified for CR-1, CR-5, CR-6

### Decisions
- CR-1: Job status stays `to_be_scheduled` during DRAFT creation.
- CR-2: DRAFT cannot skip to IN_PROGRESS; only SCHEDULED can.
- CR-5: Lien Review Queue is a tab on `/invoices`; client-side dismiss only.
- CR-6: 409 detail uses a structured dict keyed `error: "duplicate_found"`.

### Next Steps
- Address HIGH findings H-1..H-14 from the same hunt.
- Persist lien-candidate dismissals server-side (follow-up).
```

---

## Risks and rollback

| CR | Risk | Rollback |
|---|---|---|
| CR-1 | Admins previously relied on `apply_schedule` pushing jobs visibly to "scheduled"; now all cards look like drafts until they click Send Confirmation. Communication / training needed. | Revert branch — no data migration. |
| CR-2 | Low. Additive transition. | Revert branch. |
| CR-3 | Low. If `CANCELLED → SCHEDULED` re-activation occurs and a new `C` arrives, it still sends once (transitions table allows `CANCELLED → SCHEDULED`, line 60–62). Guard is only tripped on `status == CANCELLED`. | Revert branch. |
| CR-4 | Medium. Manually-created Stripe invoices that used to spawn renewal proposals will stop. Before merge, query `SELECT billing_reason, COUNT(*) FROM stripe_events WHERE type='invoice.paid' GROUP BY billing_reason` in the Stripe dashboard to quantify. | Revert branch — no migration. Run a one-off to regenerate any missed proposals if the rollback happens post-deploy. |
| CR-5 | **High.** `mass_notify("lien_eligible")` returning 400 breaks any internal script or scheduler calling that branch. Frontend tab reorganization is visible. SMS-consent pre-filter changes behavior for opted-out customers. | Revert the whole CR-5 branch. Restore the old branch in `mass_notify`. New endpoints stay dormant. |
| CR-6 | Medium. 409 is a new failure mode. If FE catch is incomplete, admins see an unhelpful toast. | Revert branch. Hotfix mitigation: ship BE with `force` defaulting to `True` if the FE handler breaks. |

**Pre-merge safety nets:**
- Snapshot prod DB before CR-5 deploy (`pg_dump`).
- For CR-1 and CR-2, `SELECT status, COUNT(*) FROM appointments GROUP BY status` pre- and post-deploy — confirm no silent regressions.

---

## Critical files (ready reference)

**Backend:**
- `src/grins_platform/api/v1/schedule.py` (CR-1)
- `src/grins_platform/api/v1/jobs.py` (CR-2)
- `src/grins_platform/models/appointment.py` (CR-2 transitions table)
- `src/grins_platform/services/job_confirmation_service.py` (CR-3)
- `src/grins_platform/api/v1/webhooks.py` (CR-4)
- `src/grins_platform/services/invoice_service.py` (CR-5)
- `src/grins_platform/schemas/invoice.py` (CR-5 new schemas)
- `src/grins_platform/api/v1/invoices.py` (CR-5 new endpoints)
- `src/grins_platform/services/lead_service.py` (CR-6)
- `src/grins_platform/schemas/lead.py` (CR-6 `force` field)
- `src/grins_platform/api/v1/leads.py` (CR-6 endpoint 409 translation)

**Frontend:**
- `frontend/src/features/invoices/components/LienReviewQueue.tsx` (new, CR-5)
- `frontend/src/features/invoices/hooks/useLienReview.ts` (new, CR-5)
- `frontend/src/features/invoices/components/MassNotifyPanel.tsx` (CR-5 edit)
- `frontend/src/features/invoices/api/invoiceApi.ts` (CR-5 additions)
- `frontend/src/features/invoices/types/index.ts` (CR-5 types)
- `frontend/src/features/leads/components/LeadConversionConflictModal.tsx` (new, CR-6)
- `frontend/src/features/leads/utils/isDuplicateConflict.ts` (new, CR-6)
- `frontend/src/features/leads/components/LeadsList.tsx` (CR-6 edit)
- `frontend/src/features/leads/types/index.ts` (CR-6 types)

**Docs:**
- `bughunt/2026-04-16-customer-lifecycle-bughunt.md` (History section)
- `DEVLOG.md` (BUGFIX entry at top)

---

## Verification checklist (run in order once all 6 branches are merged)

1. `git log --oneline dev -10` — confirm all six `fix/cr-*` commits present.
2. Backend gates: Ruff, MyPy, Pyright, then all three pytest tiers — each reports 0 errors / all green.
3. Frontend gates: `npm run lint && npm run typecheck && npm test -- --run` — all green.
4. **Safety pre-flight**: complete the Testing safety constraints checklist. Confirm the seed customer exists on `+19527373312` + test inbox, and that no dev-DB real customer can receive an SMS or email during the E2E run.
5. Start dev stack (`docker-compose up` + `npm run dev`).
6. Run agent-browser flows for CR-1, CR-5, CR-6 (see E2E section). Capture screenshots to `e2e-screenshots/`.
7. Tail `api` logs during each flow (`docker-compose logs -f api | rg 'sms\.send\.|email\.send\.'`) — abort if any non-`+19527373312`, non-test-inbox recipient appears.
8. Open the bug-hunt doc and confirm the History — Resolved section has all six rows with real dates + SHAs.
9. Open `DEVLOG.md` and confirm the BUGFIX entry is at the top and accurate.
10. DB sanity: `SELECT status, COUNT(*) FROM appointments GROUP BY status;` — no unexpected spikes in DRAFT or CANCELLED.
