# Customer Lifecycle Bug Hunt 2026-04-16 — Fix the 14 HIGH Findings

## Plan file locations
- Project copy (canonical): `bughunt/2026-04-16-high-fixes-plan.md` (this file)
- Companion (CRITICAL fixes, already in flight or merged): `bughunt/2026-04-16-critical-fixes-plan.md`

## Handoff prompt (paste into a new context session to execute this plan)

```
I need you to execute a pre-approved implementation plan for fixing 14 HIGH-severity bugs in the Grins Irrigation Platform customer lifecycle (from bughunt/2026-04-16-customer-lifecycle-bughunt.md).

Working directory: /Users/kirillrakitin/Grins_irrigation_platform
Branch base: dev (merges target main later)
Git user: kirillDR01

STEP 1 — Read the full plan before doing anything else:
  /Users/kirillrakitin/Grins_irrigation_platform/bughunt/2026-04-16-high-fixes-plan.md

This plan is approved. It covers H-1..H-14, grouped into four waves, with per-finding file edits, tests, quality gates, and the bug-hunt History rows to append after merges.

STEP 2 — HARD SAFETY CONSTRAINTS (see the plan's "Testing safety constraints" section):
  - NEVER send SMS to any phone number other than +19527373312 (user's personal number). That is the ONLY allowed real recipient. If a test path triggers SMS, tell the user exactly what to reply before you fire the message.
  - NEVER send an email to a real customer in the dev database. Use mocks or a user-supplied test inbox. Ask the user for the test inbox address before any flow that could fire an email.
  - Before any manual or agent-browser E2E flow: seed a dedicated test customer with phone='+19527373312' and the user-supplied test email. Filter out any pre-existing duplicate rows so the test surface shows only the seed.
  - Tail `docker-compose logs -f api | rg 'sms\.send\.|email\.send\.'` during every manual flow. Abort immediately if a non-allowed recipient appears.
  - This is a reinforcement of existing memory entries (SMS test number restriction; No real-customer emails during testing).

STEP 3 — Confirm the CRITICAL plan has been merged first:
  git log --oneline dev | rg 'CR-[1-6]'
  Expect all six CR-* merge commits present on dev. Several HIGH fixes depend on CRITICAL work:
    - H-2 relies on CR-1 (DRAFT creation in apply_schedule).
    - H-5 builds on CR-3 (repeat-C short-circuit).
    - H-6 builds on CR-1 (DRAFT → SCHEDULED promotion on Send Confirmation).
    - H-11 extends CR-5's consent pre-filter to the other mass_notify branches.
  If any CR-* is still open, finish that wave before starting here.

STEP 4 — Execute in the four waves the plan specifies:
  Wave 1 (parallel): H-10, H-13, H-14     — backend, single-file, low-risk
  Wave 2 (parallel): H-2, H-3, H-4, H-8, H-9  — frontend, small, independent
  Wave 3 (parallel): H-5, H-6, H-11         — backend, medium, touch SMS/notification paths
  Wave 4 (sequential): H-1, H-7, H-12       — full-stack, new UI surfaces
  Only advance to the next wave after the prior wave has merged to dev.

For each H-<N>:
  1. Create branch fix/h-<N>-<short-name> (exact names in the plan).
  2. Make the code changes specified in the plan's per-finding section — do not deviate; if a line number drifted, follow the intent and amend the plan file to reflect reality.
  3. Add/modify tests exactly as listed.
  4. Run the full quality gates before opening a PR:
       uv run ruff check src tests
       uv run mypy src
       uv run pyright src
       uv run pytest src/grins_platform/tests/unit -m unit -q
       uv run pytest src/grins_platform/tests/functional -q
       uv run pytest src/grins_platform/tests/integration -q
       cd frontend && npm run lint && npm run typecheck && npm test -- --run
  5. Commit with a message that references the H ID and bughunt file. Match the repo's style (see recent CR-* commits on dev).

STEP 5 — After all 14 branches are merged to dev:
  - Append the "History — Resolved" rows to bughunt/2026-04-16-customer-lifecycle-bughunt.md per the plan. Fill date + SHA per branch via `git log -1 --format='%ai %H' <branch>`.
  - Add the BUGFIX DEVLOG entry at the top of DEVLOG.md per the sketch in the plan.

STEP 6 — Run the Verification checklist at the end of the plan. Run the three agent-browser E2E flows (H-1, H-7, H-12) under the safety constraints and screenshot to e2e-screenshots/.

RULES:
  - Do not deviate from the plan without telling me first.
  - If you find an ambiguity that requires a product decision, ask — do not guess.
  - If the code has drifted since the plan was written, preserve the plan's intent and update the plan file.

Begin with STEP 1.
```

---

## Context

`bughunt/2026-04-16-customer-lifecycle-bughunt.md` identified 14 HIGH-severity findings (H-1..H-14) spanning:
- Frontend connectivity gaps (H-1, H-2, H-3, H-4, H-8, H-9) — buttons, filters, real-time updates.
- Missing admin/customer notification surfaces (H-5, H-7).
- Mass-notification safety and correctness (H-11, H-12).
- Lifecycle transitions and follow-ups (H-6, H-10, H-13).
- A straight-up auth regression (H-14).

The 6 CRITICAL findings are tracked separately in `2026-04-16-critical-fixes-plan.md`. CR-1..CR-4 are merged; CR-5 and CR-6 are in flight. **This plan assumes all CRITICAL fixes have merged to `dev` before HIGH work begins** so that DRAFT state, `_handle_cancel` short-circuit, and the lien-review queue are already in place.

Scope is intentionally HIGH-only — 17 MEDIUM / 11 LOW findings are out of scope here.

---

## ⚠️ Testing safety constraints — NO messages to real customers

The dev database contains real customer records. During any testing, debugging, or E2E validation performed against the dev environment:

- **SMS**: **NEVER** send a real SMS to any customer phone number in the DB. The **only** phone number that may receive real SMS is **`+19527373312`** (user's personal number). When a test path requires an SMS round-trip, tell the user **before firing** exactly which keyword to reply (`Y`, `R`, `C`, or the custom string the test expects) and wait for them.
- **Email**: **NEVER** send a real email to any customer email address in the DB. Mock the email sender or override the recipient to a test inbox the user controls (ask the user for the test inbox before relying on it).

### How to comply
- **Unit tests**: mock `SMSService.send_message`, `provider.send_text`, and any email sender. Assert on the mock's call args — do not actually dispatch.
- **Functional / integration tests**: use the existing fixtures that stub `SMSProvider` and the email backend. If a test needs a real provider round-trip, parametrise the recipient to `+19527373312` + a user-supplied test inbox — never to seeded customer records.
- **Agent-browser E2E flows**: seed a dedicated test customer whose `phone='+19527373312'` and `email=<user-supplied test inbox>`. Do **not** drive a flow against any pre-existing seeded customer.
- **Log verification**: tail `docker-compose logs -f api | rg 'sms\.send\.|email\.send\.'` during every manual flow. Abort immediately if a non-allowed recipient appears.

### Pre-flight checklist for every manual/E2E run
1. Confirm the dev DB has a seed customer with `phone='+19527373312'` and a user-supplied test email.
2. Confirm any template-based SMS/email test exercises point at that seed customer only.
3. Confirm SMS/email sender mocks are installed for automated runs.
4. Never run `mass_notify`, the bulk confirmation endpoints, or `send_lien_notice` against the unfiltered dev DB.
5. When an E2E flow fires an SMS, post the expected reply back to the user **before** the send so they can reply on the expected window.

---

## Decisions (need user confirmation before executing)

| # | Question | Recommendation |
|---|---|---|
| D-1 | H-1: Should `LeadDetail` expose the full action set (Mark Contacted, Move to Jobs, Move to Sales, requires-estimate override modal, Delete) or a subset? | Full parity with `LeadsList.tsx`. |
| D-2 | H-3: Unify weeks to Monday everywhere? | Yes — matches backend `align_to_week()` and `JobWeekEditor`. |
| D-3 | H-4: `PaymentMethod` enum — replace `stripe` with `credit_card`, add `ach` and `other`, keep `venmo`/`zelle` for existing rows? | Add `credit_card`, `ach`, `other`; rename existing `stripe` rows to `credit_card` via Alembic data migration; retain `venmo`/`zelle` as non-spec but historically-valid options. |
| D-4 | H-5: Admin notification on customer `C` — email, in-app alert, or both? | Both. Email via `notification_service`; in-app via an `Alert` table row picked up by the dashboard. |
| D-5 | H-7: What's the no-reply timeout N (days)? | Default **3 days** from `confirmation_sent_at`. Configurable via `BusinessSetting` key `confirmation_no_reply_days`. |
| D-6 | H-12: Where in the admin UI do lien thresholds live? | New "Business Settings" tab under `/settings` (exists as `SettingsPage`). Reuse `BusinessSetting` JSONB store. |
| D-7 | H-9: Real-time strategy — polling, cross-query invalidation, or both? | Both: `refetchInterval: 30_000` as a safety net + explicit `invalidateQueries` in invoice-mutation hooks. |

Ask the user for D-1, D-3, D-5, and D-6 before writing code. D-2, D-4, D-7 align with spec and are low-risk defaults.

---

## Implementation order (four waves, branch-per-finding)

| Wave | Findings | Rationale |
|---|---|---|
| **1** — parallel (3 agents) | H-10, H-13, H-14 | Single file each, no shared types, low blast radius |
| **2** — parallel (5 agents) | H-2, H-3, H-4, H-8, H-9 | Frontend-only (H-4 includes trivial BE enum bump); independent files |
| **3** — parallel (3 agents) | H-5, H-6, H-11 | Backend medium changes touching SMS/notification paths; no overlapping files |
| **4** — sequential (1 agent each) | H-1, H-7, H-12 | Full-stack slices with new UI surfaces; safer to ship one at a time |

Branch names:
`fix/h-1-lead-detail-routing`, `fix/h-2-bulk-confirmation-filter`, `fix/h-3-week-starts-monday`, `fix/h-4-payment-method-enum`, `fix/h-5-admin-cancel-alert`, `fix/h-6-reschedule-reconfirm`, `fix/h-7-no-reply-review-queue`, `fix/h-8-send-confirmation-disable`, `fix/h-9-invoice-history-realtime`, `fix/h-10-signwell-advance-log`, `fix/h-11-mass-notify-consent-prefilter`, `fix/h-12-lien-thresholds-settings`, `fix/h-13-renewal-date-roll`, `fix/h-14-bulk-notify-auth`.

---

## H-1 — `LeadDetail` gets routing buttons + conflict modal

### Code changes
**File:** `frontend/src/features/leads/components/LeadDetail.tsx`

Add, mirroring `LeadsList.tsx`:
- Imports: `useMoveToJobs`, `useMoveToSales`, `useMarkContacted`, `useDeleteLead` from `../hooks`; `ConvertLeadDialog` (already imported); `LeadConversionConflictModal` from `./LeadConversionConflictModal` (added by CR-6); `isDuplicateConflict` from `../utils/isDuplicateConflict` (added by CR-6).
- Action-buttons row in the detail header: **Mark Contacted** (visible when `status in {new, contacted, qualified}`), **Move to Jobs**, **Move to Sales**, **Delete**.
- Requires-estimate override modal: when a user clicks Move to Jobs / Move to Sales and the lead is marked `requires_estimate`, open the same 3-option dialog used in `LeadsList.tsx` (Create Estimate / Create Contract / Override and move).
- Duplicate conflict modal: reuse CR-6's `LeadConversionConflictModal`. Wrap the `mutateAsync` calls in try/catch and surface the conflict modal on 409.
- Navigation: on success, `navigate('/jobs')` or `navigate('/sales')` respectively.

Extract the shared handler logic into a new hook `frontend/src/features/leads/hooks/useLeadRoutingActions.ts` so `LeadsList.tsx` and `LeadDetail.tsx` share a single implementation (DRY — the routing/retry/force logic is identical).

### Tests
- `frontend/src/features/leads/components/LeadDetail.test.tsx` (new)
  - `renders Move to Jobs / Move to Sales / Mark Contacted / Delete buttons`
  - `fires useMoveToJobs on click`
  - `opens requires-estimate modal when lead.requires_estimate=true`
  - `opens conflict modal when move returns 409`
  - `retries with force=true on Convert anyway`
- `frontend/src/features/leads/hooks/useLeadRoutingActions.test.ts` (new) — unit-tests the shared hook.

### Data-testids
`lead-detail-move-to-jobs-btn`, `lead-detail-move-to-sales-btn`, `lead-detail-mark-contacted-btn`, `lead-detail-delete-btn`, `lead-detail-requires-estimate-modal`.

---

## H-2 — Defensive DRAFT filter inside bulk-confirmation components

### Code changes
**File 1:** `frontend/src/features/schedule/components/SendAllConfirmationsButton.tsx`

At the top of the component, after receiving `draftAppointments`, add an idempotent re-filter:
```ts
const onlyDrafts = useMemo(
  () => draftAppointments.filter((a) => a.status === 'draft'),
  [draftAppointments],
);
const draftCount = onlyDrafts.length;
```
Use `onlyDrafts` for `ids.map`, the modal list, and the count badge. This is safe because current callers (`SchedulePage.tsx:188-193`) already filter — but defence-in-depth prevents the regression if a new caller forgets.

**File 2:** `frontend/src/features/schedule/components/SendDayConfirmationsButton.tsx`

Currently accepts `draftAppointmentIds: string[]`. Change the shape to `draftAppointments: Appointment[]` so the component controls the filter the same way as `SendAllConfirmationsButton`. Update the single caller in `CalendarView.tsx:235` to pass the full appointment objects.

### Tests
- `frontend/src/features/schedule/components/SendAllConfirmationsButton.test.tsx` (new or extend)
  - `renders correct count when all appointments are drafts`
  - `renders correct count when caller accidentally mixes in scheduled appointments`
  - `submits only draft ids when caller passes mixed list`
- `frontend/src/features/schedule/components/SendDayConfirmationsButton.test.tsx` (new or extend)
  - `renders only when there is at least one DRAFT`
  - `submits only draft ids on click`

---

## H-3 — Unify week start to Monday everywhere

### Code changes
**Files:**
- `frontend/src/features/schedule/components/SchedulePage.tsx:70` — `weekStartsOn: 0` → `1`.
- `frontend/src/features/schedule/components/CalendarView.tsx:66-67, 308` — `weekStartsOn: 0` → `1`.
- Any other `weekStartsOn: 0` occurrence inside the schedule feature. Verify nothing else in the feature passes `0`.
- `JobWeekEditor.tsx` and `WeekPicker*.tsx` are already Monday-based — leave them.

### Cross-feature sanity check
After the change, grep:
```bash
rg -n "weekStartsOn" frontend/src --glob '!node_modules'
```
Expect only `weekStartsOn: 1` in results (plus any intentionally-Sunday usages outside the schedule feature — flag them in the PR for review if found).

### Tests
- `frontend/src/features/schedule/components/CalendarView.test.tsx` (new or extend)
  - `week grid starts on Monday given a mid-week date`
  - `adjacent week navigation jumps by 7 days from Monday to Monday`

---

## H-4 — Align invoice payment-type filter with spec

### Code changes

**Backend:**
- `src/grins_platform/models/enums.py` — extend `PaymentMethod` enum with `CREDIT_CARD = "credit_card"`, `ACH = "ach"`, `OTHER = "other"`. Keep existing `CASH, CHECK, STRIPE, VENMO, ZELLE` members (STRIPE renamed to map to credit_card logically, see migration below).
- `src/grins_platform/migrations/versions/<next>_align_payment_method.py` (new Alembic revision) — `UPDATE invoices SET payment_method='credit_card' WHERE payment_method='stripe';` and drop `stripe` from the enum, or alias it. Write a down-migration that reverses.
- `src/grins_platform/schemas/invoice.py` — ensure `InvoiceResponse.payment_method` is typed as the enum (so FE receives literal values `credit_card`, `ach`, `other`).

**Frontend:**
- `frontend/src/features/invoices/components/InvoiceList.tsx:87-93` — replace the options array with:
  ```ts
  { value: 'credit_card', label: 'Credit Card' },
  { value: 'cash', label: 'Cash' },
  { value: 'check', label: 'Check' },
  { value: 'ach', label: 'ACH' },
  { value: 'venmo', label: 'Venmo' },
  { value: 'zelle', label: 'Zelle' },
  { value: 'other', label: 'Other' },
  ```

### Tests
- `src/grins_platform/tests/unit/test_enums.py` (extend) — `test_payment_method_has_credit_card_ach_other`.
- `src/grins_platform/tests/integration/test_invoice_integration.py` (extend) — `test_invoice_list_filters_by_credit_card_and_ach`.
- `frontend/src/features/invoices/components/InvoiceList.test.tsx` (extend) — `renders all spec payment method options`.

---

## H-5 — Admin notification on customer `C` reply

### Code changes

**File 1:** `src/grins_platform/services/notification_service.py`

Add a new method:
```python
async def send_admin_cancellation_alert(
    self,
    *,
    appointment_id: UUID,
    customer_id: UUID,
    customer_name: str,
    scheduled_at: datetime,
    source: str = "customer_sms",
) -> None:
    """Notify admin that a customer cancelled an appointment via SMS."""
    self.log_started("admin_cancellation_alert", appointment_id=str(appointment_id))
    # 1) email — mocked in dev/test; real in prod per EMAIL_BACKEND
    await self._email_sender.send_email(
        to=settings.ADMIN_NOTIFICATION_EMAIL,
        subject=f"Appointment cancelled by customer — {customer_name}",
        body=self._render_admin_cancel_email(appointment_id, customer_name, scheduled_at, source),
    )
    # 2) in-app alert row
    alert_repo = AlertRepository(self.session)
    await alert_repo.create(
        Alert(
            type="customer_cancelled_appointment",
            severity="warning",
            entity_type="appointment",
            entity_id=appointment_id,
            message=f"{customer_name} cancelled via SMS for {scheduled_at:%Y-%m-%d %H:%M}",
            created_at=datetime.now(tz=timezone.utc),
        )
    )
    self.log_completed("admin_cancellation_alert", appointment_id=str(appointment_id))
```

If the `Alert` model / `AlertRepository` don't yet exist, create them:
- `src/grins_platform/models/alert.py` — SQLAlchemy model (id, type, severity, entity_type, entity_id, message, created_at, acknowledged_at).
- `src/grins_platform/repositories/alert_repository.py` — CRUD + `list_unacknowledged()`.
- Alembic migration `alerts` table.
- `GET /api/v1/alerts` endpoint to back the dashboard alert bar.

**File 2:** `src/grins_platform/services/job_confirmation_service.py` (`_handle_cancel`)

After the CANCELLED flush (and before the return), call:
```python
notification_svc = NotificationService(self.db)
await notification_svc.send_admin_cancellation_alert(
    appointment_id=appt.id,
    customer_id=appt.customer_id,
    customer_name=appt.customer.name,
    scheduled_at=appt.scheduled_at,
    source="customer_sms",
)
```
Handle `Exception` with `log_failed` — admin notification failing MUST NOT block the customer-facing response.

**Skip the notification** when the `_handle_cancel` short-circuit (CR-3) fires for an already-CANCELLED appointment.

### Tests
- `src/grins_platform/tests/unit/test_job_confirmation_service.py` (extend)
  - `test_handle_cancel_notifies_admin_on_first_cancellation`
  - `test_handle_cancel_does_not_notify_admin_when_already_cancelled` (regression after CR-3)
  - `test_handle_cancel_still_responds_when_admin_notification_fails`
- `src/grins_platform/tests/unit/test_notification_service.py` (extend)
  - `test_send_admin_cancellation_alert_dispatches_email_and_creates_alert_row`
- `src/grins_platform/tests/functional/test_yrc_confirmation_functional.py` (extend)
  - `test_customer_c_reply_creates_alert_and_email_in_mock_backend`

---

## H-6 — After-R reschedule fires a NEW confirmation SMS cycle

### Code changes

**File 1:** `src/grins_platform/services/appointment_service.py`

In the reschedule code path (`update_appointment` / dedicated `reschedule_from_request`), add a flag or new public method `reschedule_for_request(appointment_id, new_scheduled_at, actor_id)`:
1. Update `scheduled_at` and reset `status=SCHEDULED` (not CONFIRMED; the customer hasn't re-confirmed yet).
2. Call the existing `_send_confirmation_sms(appointment)` — promote it to public or add a new public `send_confirmation_sms(appointment_id)` that wraps it.
3. Write an audit log entry `appointment.reschedule.reconfirmation_sent`.

The existing `_send_reschedule_sms` (fire-and-forget "We moved your appointment to …") is replaced on the R-request path by a full SMS #1 template that prompts Y/R/C again.

**File 2:** `src/grins_platform/api/v1/appointments.py`

Add endpoint `POST /api/v1/appointments/{id}/reschedule-from-request` that the FE queue calls instead of generic `update_appointment`.

**File 3:** `frontend/src/features/schedule/components/RescheduleRequestsQueue.tsx`

When admin picks the new date via the dialog, call the new endpoint (not generic `updateAppointment`). On success, toast "Reschedule sent — customer will receive a new confirmation request."

### Tests
- `src/grins_platform/tests/unit/test_appointment_service_crm.py` (extend)
  - `test_reschedule_from_request_resets_status_to_scheduled`
  - `test_reschedule_from_request_sends_confirmation_sms_not_reschedule_sms`
- `src/grins_platform/tests/functional/test_reschedule_flow_functional.py` (extend or new)
  - `test_r_reply_then_admin_reschedule_triggers_new_y_r_c_prompt` (mock SMS provider; assert two outbound sends — one R ack, one new #1)
- `frontend/src/features/schedule/components/RescheduleRequestsQueue.test.tsx` (extend)
  - `calls reschedule-from-request endpoint when admin picks new date`
  - `shows "customer will receive a new confirmation request" toast`

---

## H-7 — No-reply / confirmation-timeout needs-review path

### Code changes

**Backend (new cron job + surface):**

**File 1:** `src/grins_platform/services/background_jobs.py`

Add a nightly job near `register_scheduled_jobs`:
```python
scheduler.add_job(
    flag_no_reply_confirmations,
    CronTrigger(hour=6, minute=0),
    id="flag_no_reply_confirmations",
    replace_existing=True,
)
```

Implement `flag_no_reply_confirmations(session_factory)`:
1. Load `confirmation_no_reply_days` from `BusinessSetting` (default 3).
2. Query `Appointment` where `status=SCHEDULED` AND `confirmation_sent_at IS NOT NULL` AND `confirmation_sent_at < now() - interval '<N> days'` AND NO `SentMessage` reply exists since.
3. For each, create an `Alert(type="confirmation_no_reply", severity="info", ...)` (reuses H-5's Alert model — H-7 must land after H-5).
4. Set a new column `Appointment.needs_review_reason="no_confirmation_response"` (Alembic migration).

**File 2:** `src/grins_platform/api/v1/appointments.py`

New endpoint `GET /api/v1/appointments/needs-review?reason=no_confirmation_response` returning the flagged appointments with customer info.

**Frontend:**

**File 3:** `frontend/src/features/schedule/components/NoReplyReviewQueue.tsx` (new)

Mirrors `RescheduleRequestsQueue.tsx` layout. Per-row: appointment details + buttons **Call Customer** (opens tel:), **Send Reminder SMS** (re-triggers SMS #1), **Mark as Contacted** (clears `needs_review_reason`).

**File 4:** Placement — new tab on `/schedule` alongside the reschedule queue, or a dashboard card. Recommend the `/schedule` tab approach (least navigation churn).

### Tests
- `src/grins_platform/tests/unit/test_background_jobs.py` (extend) — `test_flag_no_reply_confirmations_creates_alert_rows_for_stale_scheduled`
- `src/grins_platform/tests/functional/test_no_reply_review_functional.py` (new) — full flow from SMS send → timer advance → alert row → queue endpoint returns the row.
- `frontend/src/features/schedule/components/NoReplyReviewQueue.test.tsx` (new) — renders rows, Send Reminder button triggers mutation, empty state.

---

## H-8 — `SendConfirmationButton` disables for non-DRAFT

### Code changes

**File:** `frontend/src/features/schedule/components/SendConfirmationButton.tsx`

Add `appointment: Appointment` or at minimum `status: AppointmentStatus` to props.

Replace `disabled={sendMutation.isPending}` with:
```tsx
disabled={sendMutation.isPending || appointment.status !== 'draft'}
title={
  appointment.status === 'draft'
    ? `Send confirmation SMS to ${appointment.customer_name}`
    : 'Confirmation already sent'
}
```

Apply both in compact and full variants.

Update callers in `CalendarView.tsx`, `AppointmentDetail.tsx` (covered separately in M-1 but this change is forward-compatible), and tests to pass the `appointment` (or `status`) prop.

### Tests
- `frontend/src/features/schedule/components/SendConfirmationButton.test.tsx` (extend or new)
  - `renders enabled for DRAFT`
  - `renders disabled with tooltip for SCHEDULED, CONFIRMED, CANCELLED, etc.`

---

## H-9 — `InvoiceHistory` real-time updates

### Code changes

**File 1:** `frontend/src/features/customers/hooks/useCustomers.ts` (`useCustomerInvoices`)

Add `refetchInterval: 30_000` as a default (overridable by callers).

**File 2:** `frontend/src/features/invoices/hooks/useInvoices.ts` (or wherever invoice mutations live)

In the `onSuccess` handlers of `useUpdateInvoice`, `useMarkPaid`, `useVoidInvoice`, etc., add:
```ts
queryClient.invalidateQueries({ queryKey: ['customers', 'invoices'] });
// or a more-specific key if one is exported
```

Export a `customerInvoiceKeys` factory from `features/customers/hooks/useCustomers.ts` so invoice mutations can invalidate precisely by `customerId`.

**File 3:** `frontend/src/features/customers/components/InvoiceHistory.tsx:26`

No signature change needed — the hook is the right extension point.

### Tests
- `frontend/src/features/customers/hooks/useCustomers.test.ts` (extend) — `useCustomerInvoices uses refetchInterval of 30s by default`.
- `frontend/src/features/invoices/hooks/useInvoices.test.ts` (extend) — `useMarkPaid invalidates customer-invoices queries on success`.
- `frontend/src/features/customers/components/InvoiceHistory.test.tsx` (extend) — `refetches when invoice mutation fires elsewhere` (mock queryClient.invalidateQueries, assert effect).

---

## H-10 — SignWell webhook logs a warning on unexpected pre-state

### Code changes

**File:** `src/grins_platform/api/v1/signwell_webhooks.py:179-184` (locate the block
by searching for `SalesEntryStatus.PENDING_APPROVAL.value` — the line number may
drift as the file evolves). The existing block is already an `if` without an
`else`; the fix adds the `else` branch.

Wrap the advance in an else branch:
```python
if entry.status == SalesEntryStatus.PENDING_APPROVAL.value:
    entry.status = SalesEntryStatus.SEND_CONTRACT.value
    entry.updated_at = datetime.now(tz=timezone.utc)
else:
    logger.warning(
        "signwell.document_signed.unexpected_pre_state",
        entry_id=str(entry.id),
        pre_state=entry.status,
        expected=SalesEntryStatus.PENDING_APPROVAL.value,
        document_id=document_id,
    )
```

Do **not** raise — SignWell retries on non-2xx. The document was received and
stored; the advance is what fails. Operator recovery is manual for now. The
optional `_record_unexpected_webhook_audit` audit-row helper is out of scope
for this minimal fix.

### Tests
- `src/grins_platform/tests/unit/test_signwell_webhooks.py` (new; the module had no
  existing unit test — mirror the fixture/mock patterns used in
  `src/grins_platform/tests/integration/test_signwell_webhook_integration.py`)
  - `test_document_signed_advances_when_pending_approval`
  - `test_document_signed_logs_warning_when_not_pending_approval` (assert structlog captures the event with expected context)
  - `test_document_signed_returns_200_even_on_unexpected_pre_state`

---

## H-11 — SMS-consent pre-filter in `mass_notify`

### Code changes

**File:** `src/grins_platform/services/invoice_service.py` (inside `mass_notify`, around lines 889-898)

Before the send loop, query opt-out status for all candidate customer IDs in one batched call:
```python
consent_repo = SmsConsentRepository(self.invoice_repository.session)
opted_out_ids = await consent_repo.get_opted_out_customer_ids(
    customer_ids=[inv.customer_id for inv in invoices]
)
```
(Add `get_opted_out_customer_ids` to `SmsConsentRepository` — one query, returns `set[UUID]`.)

Inside the loop, before `send_message`:
```python
if inv.customer_id in opted_out_ids:
    skipped_reasons.setdefault("opted_out", 0)
    skipped_reasons["opted_out"] += 1
    continue
```

Return `skipped_count` + `skipped_reasons` in the response (new field; update `MassNotifyResponse` schema).

**Note:** CR-5's `send_lien_notice` already includes this pre-filter at a per-customer granularity. H-11 extends the check to `upcoming_due` and `past_due` branches of `mass_notify`.

### Tests
- `src/grins_platform/tests/unit/test_invoice_service.py` (extend)
  - `test_mass_notify_past_due_skips_opted_out_customers`
  - `test_mass_notify_upcoming_due_skips_opted_out_customers`
  - `test_mass_notify_response_includes_skipped_count_and_reasons`
- `src/grins_platform/tests/unit/test_sms_consent_repository.py` (new or extend)
  - `test_get_opted_out_customer_ids_returns_set`

---

## H-12 — Lien thresholds live in `BusinessSetting`

### Code changes

**Backend:**

**File 1:** `src/grins_platform/services/business_setting_service.py` (new, or add methods to existing service)

Helpers to read/write typed values from the key-value store:
```python
async def get_int(self, key: str, default: int) -> int: ...
async def get_decimal(self, key: str, default: Decimal) -> Decimal: ...
async def set_value(self, key: str, value: Any, updated_by: UUID) -> None: ...
```

**File 2:** `src/grins_platform/services/invoice_service.py`

Change `compute_lien_candidates` (from CR-5) to read defaults from `BusinessSetting`:
```python
days_past_due = days_past_due or await self._settings.get_int("lien_days_past_due", 60)
min_amount = min_amount or await self._settings.get_decimal("lien_min_amount", Decimal("500"))
```
Same for `mass_notify` upcoming/past-due thresholds (`upcoming_due_days`).

**File 3:** `src/grins_platform/api/v1/settings.py` (new or extend)

Endpoints:
- `GET /api/v1/settings/business` — returns all business settings (admin-only).
- `PATCH /api/v1/settings/business` — updates one or more keys (admin-only, audit-logged).

**Migration:** seed default rows for `lien_days_past_due=60`, `lien_min_amount=500`, `upcoming_due_days=7`, `confirmation_no_reply_days=3` (used by H-7).

**Frontend:**

**File 4:** `frontend/src/features/settings/components/BusinessSettingsPanel.tsx` (new or extend existing SettingsPage)

Form with number inputs for the four keys above. On save → `PATCH /settings/business`.

**File 5:** `frontend/src/features/invoices/components/MassNotifyPanel.tsx` and `LienReviewQueue.tsx` (from CR-5)

Remove per-invocation inputs; display the current threshold values with a read-only note "configure in Business Settings." Keep an "Override once" expander that still allows a per-send override.

### Tests
- `src/grins_platform/tests/unit/test_business_setting_service.py` (new)
  - `test_get_int_returns_value_when_key_exists`
  - `test_get_int_returns_default_when_key_missing`
  - `test_set_value_writes_audit_log`
- `src/grins_platform/tests/unit/test_invoice_service.py` (extend)
  - `test_compute_lien_candidates_reads_defaults_from_business_settings`
- `frontend/src/features/settings/components/BusinessSettingsPanel.test.tsx` (new)
  - `renders current threshold values`
  - `saves changes via PATCH /settings/business`
  - `toasts success`
- `frontend/src/features/invoices/components/LienReviewQueue.test.tsx` (extend)
  - `displays read-only threshold note when used with defaults`

---

## H-13 — Renewal date roll is calendar-year + Monday-align

### Code changes

**File:** `src/grins_platform/services/contract_renewal_service.py:73-94`

Replace:
```python
new_d = d + timedelta(weeks=52)
```
with:
```python
try:
    candidate = d.replace(year=d.year + 1)
except ValueError:
    # Feb 29 in a leap year → pick Feb 28 next year.
    candidate = d.replace(year=d.year + 1, day=28)
monday = candidate - timedelta(days=candidate.weekday())
rolled[key] = monday.isoformat()
```

### Tests
- `src/grins_platform/tests/unit/test_contract_renewal_service.py` (extend)
  - `test_roll_forward_prefs_lands_on_monday_one_year_later`
  - `test_roll_forward_prefs_handles_leap_day_source`
  - `test_roll_forward_prefs_preserves_non_date_values`
  - `test_roll_forward_prefs_preserves_invalid_date_strings`
  - `test_five_year_roll_stays_on_same_weekday` (chain five calls, assert weekday stays Monday)

---

## H-14 — `bulk_notify_invoices` requires real authentication

### Code changes

**File:** `src/grins_platform/api/v1/invoices.py:776-781`

Replace:
```python
_current_user: ManagerOrAdminUser = None,  # type: ignore[assignment]
service: Annotated[InvoiceService, Depends(get_invoice_service)] = None,  # type: ignore[assignment]
```
with (matching the pattern used by other admin-gated endpoints in the same
file — `ManagerOrAdminUser` is already a type alias for
`Annotated[Staff, Depends(require_manager_or_admin)]`, so no extra
`Depends` wrapper is required):
```python
_current_user: ManagerOrAdminUser,
service: Annotated[InvoiceService, Depends(get_invoice_service)],
```

Run `uv run mypy src/grins_platform/api/v1/invoices.py` to verify no `type: ignore` is left and types align.

### Tests
- `src/grins_platform/tests/unit/test_invoice_api.py` (extend)
  - `test_bulk_notify_invoices_requires_auth` — POST without token returns 401.
  - `test_bulk_notify_invoices_rejects_non_admin` — POST as staff returns 403.
  - `test_bulk_notify_invoices_succeeds_as_admin` — returns 200.
- `src/grins_platform/tests/integration/test_invoice_integration.py` (extend)
  - `test_bulk_notify_invoices_end_to_end_admin_only`

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

All gates must pass with zero errors per `.kiro/steering/spec-quality-gates.md` and `code-standards.md`. Coverage targets: backend unit 90%+, FE components 80%+, hooks 85%+, utils 90%+ per `frontend-testing.md`.

Structured-logging requirements per `code-standards.md` §1:
- H-5, H-7, H-10, H-11, H-12 must emit `log_started` / `log_completed` / `log_rejected` / `log_failed` events at service-entry/exit and all branch decisions.
- H-14 endpoint must use `set_request_id()` + `DomainLogger.api_event(...)` per `api-patterns.md`.

---

## E2E / agent-browser validation

Only findings with new/changed user-visible surfaces need browser flows.

**Before any flow below:** complete the pre-flight checklist in the Testing safety constraints section. Every customer touched by these flows must be a fresh seed tied to `+19527373312` + a user-supplied test inbox, or behind a mock. If any flow would dispatch an SMS to a pre-existing dev-DB customer, abort and re-seed. **When an SMS test fires, tell the user which keyword to reply before sending.**

### H-1 — LeadDetail routing
1. Seed lead B tied to `+19527373312`.
2. Open `/leads/{B.id}`.
3. Assert buttons render: Mark Contacted, Move to Jobs, Move to Sales, Delete.
4. Click Move to Jobs → success → navigates to `/jobs`.
5. Repeat with a lead flagged `requires_estimate=true` → 3-option modal opens.
6. Repeat with a lead that collides with an existing customer on phone → `LeadConversionConflictModal` opens.
7. Screenshot each to `e2e-screenshots/h1-*.png`.

### H-3 — Monday-based weeks
1. Pick a Tuesday in the middle of a month.
2. Open `/schedule`.
3. Assert the first visible column header is a Monday.
4. Navigate forward one week → assert still Monday-aligned.
5. Cross-reference with `/jobs` week picker — both should show identical week boundaries.

### H-7 — No-reply review queue
1. Seed an appointment with `confirmation_sent_at = now() - 4 days` for the test customer at `+19527373312`. (Bypass the SMS by directly inserting the row with `confirmation_sent_at` set — no actual send.)
2. Run `flag_no_reply_confirmations` manually via `python -m grins_platform.scripts.run_job flag_no_reply_confirmations`.
3. Open `/schedule` → Needs Review tab → assert the seeded appointment appears.
4. Click Send Reminder SMS → **before clicking confirm**, the UI shows the recipient `+19527373312`; ask the user "reply Y when you get the reminder" and confirm.
5. Assert an outbound SMS to `+19527373312` only. User replies Y → appointment transitions to CONFIRMED.

### H-12 — Business settings panel
1. Open `/settings` → Business tab.
2. Change `lien_min_amount` from `500` → `750`; save → toast success.
3. Open `/invoices?tab=lien-review` → assert candidate list recomputes using the new threshold.
4. Revert to `500`.

No browser validation required for H-2, H-4, H-5, H-6, H-8, H-9, H-10, H-11, H-13, H-14 — functional/integration tests cover them.

---

## Update the bug hunt document — History section

**File:** `bughunt/2026-04-16-customer-lifecycle-bughunt.md`

After the CR-* rows (added by the CRITICAL plan), append:

```markdown
| H-1 — LeadDetail missing routing buttons | YYYY-MM-DD | `<sha>` | `fix/h-1-lead-detail-routing` | Parity with LeadsList; shared `useLeadRoutingActions` hook. |
| H-2 — Bulk confirmation filters don't re-filter DRAFT | YYYY-MM-DD | `<sha>` | `fix/h-2-bulk-confirmation-filter` | Defensive filter inside components; tests prove idempotence against mixed caller input. |
| H-3 — Schedule week starts Sunday | YYYY-MM-DD | `<sha>` | `fix/h-3-week-starts-monday` | All `weekStartsOn: 0` → `1` in schedule feature. |
| H-4 — Payment-type filter missing Credit Card / ACH | YYYY-MM-DD | `<sha>` | `fix/h-4-payment-method-enum` | Enum extended; Alembic renames `stripe` → `credit_card`; FE options aligned with spec. |
| H-5 — No admin notification on customer `C` reply | YYYY-MM-DD | `<sha>` | `fix/h-5-admin-cancel-alert` | `NotificationService.send_admin_cancellation_alert` + Alert model/table + /alerts endpoint. |
| H-6 — R reply doesn't send new confirmation SMS cycle | YYYY-MM-DD | `<sha>` | `fix/h-6-reschedule-reconfirm` | New endpoint `/reschedule-from-request` restarts the Y/R/C cycle. |
| H-7 — No-reply review queue missing | YYYY-MM-DD | `<sha>` | `fix/h-7-no-reply-review-queue` | Nightly `flag_no_reply_confirmations` cron + `/schedule` Needs Review tab. |
| H-8 — `SendConfirmationButton` not disabled for non-DRAFT | YYYY-MM-DD | `<sha>` | `fix/h-8-send-confirmation-disable` | `disabled={... || status !== 'draft'}` with tooltip. |
| H-9 — Invoice history not real-time | YYYY-MM-DD | `<sha>` | `fix/h-9-invoice-history-realtime` | Added `refetchInterval: 30_000` + invoice-mutation `invalidateQueries`. |
| H-10 — SignWell advance fails silently on unexpected pre-state | YYYY-MM-DD | `<sha>` | `fix/h-10-signwell-advance-log` | WARN log + audit row when pre-state isn't PENDING_APPROVAL. |
| H-11 — `mass_notify` doesn't skip opted-out customers | YYYY-MM-DD | `<sha>` | `fix/h-11-mass-notify-consent-prefilter` | Batched consent lookup + `skipped_reasons` in response. |
| H-12 — Lien thresholds not persisted | YYYY-MM-DD | `<sha>` | `fix/h-12-lien-thresholds-settings` | Stored in `BusinessSetting`; managed via new Business Settings UI. |
| H-13 — Renewal roll uses 52 weeks | YYYY-MM-DD | `<sha>` | `fix/h-13-renewal-date-roll` | `year+1 → align-to-Monday`; leap-day safe. |
| H-14 — `bulk_notify_invoices` effectively unauthenticated | YYYY-MM-DD | `<sha>` | `fix/h-14-bulk-notify-auth` | Proper `Depends(get_current_manager_or_admin_user)`; type: ignore removed. |
```

Replace `YYYY-MM-DD` and `<sha>` with `git log -1 --format='%ai %H' <branch>` at merge time.

---

## DEVLOG entry (sketch)

Insert at the top of `DEVLOG.md` under `## Recent Activity`, after the CR-* BUGFIX entry:

```markdown
## [YYYY-MM-DD HH:MM] - BUGFIX: 14 HIGH Customer Lifecycle Fixes (H-1..H-14)

### What Was Accomplished
Closed all 14 HIGH findings from the 2026-04-16 customer-lifecycle bug hunt.

### Technical Details
(fill from per-H diffs; notable: new Alert model, new no-reply cron, BusinessSetting-driven thresholds)

### Files Created
- src/grins_platform/models/alert.py
- src/grins_platform/repositories/alert_repository.py
- src/grins_platform/services/business_setting_service.py
- src/grins_platform/migrations/versions/<rev>_align_payment_method.py
- src/grins_platform/migrations/versions/<rev>_alerts_and_needs_review.py
- src/grins_platform/migrations/versions/<rev>_seed_business_settings.py
- frontend/src/features/schedule/components/NoReplyReviewQueue.tsx + test
- frontend/src/features/settings/components/BusinessSettingsPanel.tsx + test
- frontend/src/features/leads/hooks/useLeadRoutingActions.ts + test

### Files Modified
(enumerate per branch)

### Quality Check Results
- Ruff / MyPy / Pyright: 0 errors
- Backend unit + functional + integration: green
- Frontend lint + typecheck + tests: green
- agent-browser flows verified for H-1, H-3, H-7, H-12

### Decisions
- H-3: Monday-based weeks everywhere (matches backend align_to_week).
- H-4: Added `credit_card`/`ach`/`other`; migrated `stripe` rows.
- H-5: Both email + in-app Alert for admin cancel notifications.
- H-7: Default no-reply window is 3 days, overridable via BusinessSetting.
- H-12: Lien/due-soon thresholds live in BusinessSetting; per-send overrides retained.

### Next Steps
- Address MEDIUM findings M-1..M-17 from the same hunt.
- Wire inbound SMS unit into no-reply alerts so reminders that get a Y response auto-clear the alert.
```

---

## Risks and rollback

| H | Risk | Rollback |
|---|---|---|
| H-1 | Low. Additive FE. | Revert branch. |
| H-2 | Low. Defensive filter; cannot break existing callers. | Revert branch. |
| H-3 | Medium. Admins expecting Sunday-first week layouts will see a UX shift. Train in release notes. | Revert branch. |
| H-4 | Medium — data migration. `UPDATE ... SET payment_method='credit_card'` must run inside the Alembic transaction; snapshot prod DB beforehand. | Revert branch + restore snapshot. |
| H-5 | Medium. New email + alert volume. Confirm `ADMIN_NOTIFICATION_EMAIL` env var set in dev/prod and the email backend doesn't loop. | Revert branch; optionally keep the `Alert` model shipped. |
| H-6 | Medium. Changes customer-facing SMS content on the reschedule path. Communicate to ops. | Revert branch. |
| H-7 | Medium. New cron job. Confirm APScheduler registers it in prod before enabling (check `scheduler.get_jobs()` at startup). | Disable the job via feature flag; revert branch. |
| H-8 | Low. Only disables the button in a state the backend already rejects. | Revert branch. |
| H-9 | Low. Polling is cheap (30s). Watch API p95 on `/customers/{id}/invoices`. | Reduce to 60s or revert. |
| H-10 | Low. Log-only change. | Revert branch. |
| H-11 | Medium. Existing opted-out customers stop receiving past-due/upcoming-due SMS. Likely desired; confirm with ops. | Revert branch. |
| H-12 | Medium. Touches production settings storage. Seed migration must idempotently handle re-runs. | Revert branch + remove seeded rows. |
| H-13 | Low. Additive math. | Revert branch. |
| H-14 | **High.** Unauth was effectively open; unknown callers may be hitting the endpoint. `git log --all -S "bulk-notify"` for recent adopters. | Revert branch only as emergency — re-enabling unauth is unacceptable. Hotfix any blocker by issuing the caller a proper admin token. |

**Pre-merge safety nets:**
- Snapshot prod DB before H-4 and H-12 deploys.
- For H-3, screenshot the schedule week navigation pre/post-deploy and attach to the PR.
- For H-11, measure opt-out customer count before deploy and expect an equivalent drop in outbound SMS volume after.

---

## Critical files (ready reference)

**Backend:**
- `src/grins_platform/api/v1/appointments.py` (H-6 new endpoint; H-7 needs-review endpoint)
- `src/grins_platform/api/v1/invoices.py` (H-14 auth fix)
- `src/grins_platform/api/v1/settings.py` (H-12 new endpoints)
- `src/grins_platform/api/v1/signwell_webhooks.py` (H-10 log warn)
- `src/grins_platform/models/alert.py` (new — H-5, H-7)
- `src/grins_platform/models/enums.py` (H-4 PaymentMethod extension)
- `src/grins_platform/repositories/alert_repository.py` (new — H-5, H-7)
- `src/grins_platform/repositories/sms_consent_repository.py` (H-11 batch method)
- `src/grins_platform/services/appointment_service.py` (H-6)
- `src/grins_platform/services/background_jobs.py` (H-7 cron)
- `src/grins_platform/services/business_setting_service.py` (new — H-12)
- `src/grins_platform/services/contract_renewal_service.py` (H-13)
- `src/grins_platform/services/invoice_service.py` (H-11, H-12)
- `src/grins_platform/services/job_confirmation_service.py` (H-5)
- `src/grins_platform/services/notification_service.py` (H-5 new method)

**Frontend:**
- `frontend/src/features/customers/components/InvoiceHistory.tsx` (H-9)
- `frontend/src/features/customers/hooks/useCustomers.ts` (H-9)
- `frontend/src/features/invoices/components/InvoiceList.tsx` (H-4)
- `frontend/src/features/invoices/components/LienReviewQueue.tsx` (H-12 edit after CR-5)
- `frontend/src/features/invoices/components/MassNotifyPanel.tsx` (H-12 edit)
- `frontend/src/features/invoices/hooks/useInvoices.ts` (H-9 invalidations)
- `frontend/src/features/leads/components/LeadDetail.tsx` (H-1)
- `frontend/src/features/leads/hooks/useLeadRoutingActions.ts` (new — H-1)
- `frontend/src/features/schedule/components/CalendarView.tsx` (H-3)
- `frontend/src/features/schedule/components/NoReplyReviewQueue.tsx` (new — H-7)
- `frontend/src/features/schedule/components/RescheduleRequestsQueue.tsx` (H-6)
- `frontend/src/features/schedule/components/SchedulePage.tsx` (H-3)
- `frontend/src/features/schedule/components/SendAllConfirmationsButton.tsx` (H-2)
- `frontend/src/features/schedule/components/SendConfirmationButton.tsx` (H-8)
- `frontend/src/features/schedule/components/SendDayConfirmationsButton.tsx` (H-2)
- `frontend/src/features/settings/components/BusinessSettingsPanel.tsx` (new or extend — H-12)

**Migrations:**
- `<rev>_align_payment_method.py` (H-4)
- `<rev>_alerts_and_needs_review.py` (H-5, H-7)
- `<rev>_seed_business_settings.py` (H-12)

**Docs:**
- `bughunt/2026-04-16-customer-lifecycle-bughunt.md` (History rows)
- `DEVLOG.md` (BUGFIX entry at top)

---

## Verification checklist (run in order once all 14 branches are merged)

1. `git log --oneline dev -30` — confirm all 14 `fix/h-*` commits present.
2. Backend gates: Ruff, MyPy, Pyright, then all three pytest tiers — each reports 0 errors / all green.
3. Frontend gates: `npm run lint && npm run typecheck && npm test -- --run` — all green.
4. Alembic sanity: `uv run alembic upgrade head` on a fresh DB completes cleanly; `uv run alembic downgrade -1` then `upgrade head` round-trips cleanly for each new revision.
5. **Safety pre-flight**: seed a test customer at `+19527373312` + user-supplied test inbox. Confirm `ADMIN_NOTIFICATION_EMAIL` is pointed at the test inbox. No real dev-DB customer can receive SMS or email during the E2E run.
6. Start dev stack (`docker-compose up` + `cd frontend && npm run dev`).
7. Run agent-browser flows for H-1, H-3, H-7, H-12 (see E2E section). Capture screenshots to `e2e-screenshots/`.
8. Tail `api` logs during each flow (`docker-compose logs -f api | rg 'sms\.send\.|email\.send\.'`) — abort if any non-`+19527373312`, non-test-inbox recipient appears.
9. Business-settings sanity: `SELECT setting_key, setting_value FROM business_settings;` — confirm the four seeded rows exist.
10. Alert model sanity: fire a `C` reply via the test customer, assert exactly one `Alert(type="customer_cancelled_appointment")` row created, one email sent to the test inbox.
11. No-reply cron sanity: insert a stale SCHEDULED appointment for the test customer, run the cron manually, assert the `Alert(type="confirmation_no_reply")` row is created.
12. Open the bug-hunt doc and confirm the 14 History rows are present with real dates + SHAs.
13. Open `DEVLOG.md` and confirm the BUGFIX entry is at the top and accurate.
14. DB sanity: `SELECT payment_method, COUNT(*) FROM invoices GROUP BY payment_method;` — confirm no `stripe` rows remain; `credit_card` population looks right.
15. Env-var sanity: `ADMIN_NOTIFICATION_EMAIL` set in dev and prod (never a real customer address).
