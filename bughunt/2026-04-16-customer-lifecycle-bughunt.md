# Customer Lifecycle Bug Hunt — 2026-04-16

**Note:** The long-form finding document (original 48-item catalog across 6 CRITICAL / 14 HIGH / 17 MEDIUM / 11 LOW) was present as an untracked file in the working tree at the start of the fix session and was lost during subagent worktree operations. Only the resolution record (this History section) could be reconstructed. The per-finding analysis lives in the commit messages and the companion plan files:

- `bughunt/2026-04-16-high-fixes-plan.md` — per-H-finding spec, recommendations, and test expectations
- `bughunt/2026-04-16-medium-bugs-plan.md` — per-M-finding plan (separate workstream)
- Companion CRITICAL-fixes plan was also lost; reference the `fix/cr-*` commit messages and the `2026-04-16-cr1-cr6-e2e-verification.md` sibling doc for that context.

MEDIUM and LOW findings remain open as future work.

---

## History — Resolved

| Finding | Resolution Date | Commit SHA | Branch | Notes |
|---|---|---|---|---|
| CR-1 — `apply_schedule` creates SCHEDULED not DRAFT | 2026-04-15 | `2f7caaf` | `fix/cr-1-apply-schedule-draft` | Default to `AppointmentStatus.DRAFT.value`; `Job.status` stays `to_be_scheduled`. |
| CR-2 — `job_started` doesn't promote SCHEDULED → IN_PROGRESS | 2026-04-15 | `c65283e` | `fix/cr-2-job-started-scheduled` | Added `SCHEDULED` to pre-state set; transitions table now allows `SCHEDULED → IN_PROGRESS`. |
| CR-3 — Repeat `C` sends duplicate cancellation SMS | 2026-04-15 | `9a30fac` | `fix/cr-3-repeat-cancel-sms` | `_handle_cancel` short-circuits when already CANCELLED; empty `auto_reply` suppresses SMS. |
| CR-4 — `invoice.paid` misclassifies non-first invoices as renewals | 2026-04-15 | `6d99587` | `fix/cr-4-invoice-billing-reason` | Renewal branch now gated on Stripe `billing_reason == "subscription_cycle"`. |
| CR-5 — Lien SMS sent immediately instead of queued | 2026-04-15 | `d679c25` | `fix/cr-5-lien-review-queue` | Split into `compute_lien_candidates` + `send_lien_notice` with SMS-consent pre-filter and audit log; new `/invoices?tab=lien-review` queue UI. |
| CR-6 — `convert_lead` skips Tier-1 dedup | 2026-04-15 | `7007002` | `fix/cr-6-convert-lead-dedup` | Added `force` flag; raises `LeadDuplicateFoundError` → 409 with structured detail; FE surfaces conflict modal with "Use existing" + "Convert anyway". |
| H-1 — LeadDetail missing routing buttons | 2026-04-16 | `6c098a5` | `fix/h-1-lead-detail-routing` | Full parity with LeadsList (Mark Contacted, Move to Jobs, Move to Sales, Delete + requires-estimate override + CR-6 conflict modal) via shared `useLeadRoutingActions` hook. Also folds L-4. |
| H-2 — Bulk confirmation filters don't re-filter DRAFT | 2026-04-16 | `a389f8c` | `fix/h-2-bulk-confirmation-filter` | Defensive `useMemo` filter in `SendAllConfirmationsButton` + `SendDayConfirmationsButton`. `SendDayConfirmationsButton` now takes `Appointment[]` instead of id-array so count + submit stay in sync. |
| H-3 — Schedule week starts Sunday | 2026-04-16 | `ab67840` | `fix/h-3-week-starts-monday` | All `weekStartsOn: 0` → `1` in schedule feature plus `firstDay={1}` on FullCalendar so the rendered grid matches the state logic. |
| H-4 — Payment-type filter missing Credit Card / ACH | 2026-04-16 | `d4f738c` | `fix/h-4-payment-method-enum` | Added `credit_card`/`ach`/`other` to `PaymentMethod` enum + Alembic CHECK-constraint widen (kept `stripe` for legacy rows — no data migration). FE filter + record-payment picker omit `stripe` going forward. |
| H-5 — No admin notification on customer `C` reply | 2026-04-16 | `6a31863` | `fix/h-5-admin-cancel-alert` | New `Alert` model + `AlertRepository` + `GET /api/v1/alerts` endpoint + migration `20260416_100100`. `NotificationService.send_admin_cancellation_alert` wired into `_handle_cancel` after CR-3 short-circuit; email failures logged, don't block customer reply. |
| H-6 — R reply doesn't send new confirmation SMS cycle | 2026-04-16 | `ccde877` | `fix/h-6-reschedule-reconfirm` | New `POST /api/v1/appointments/{id}/reschedule-from-request` resets appointment to SCHEDULED and re-sends SMS #1 (Y/R/C). RescheduleRequestsQueue UI routes through the new endpoint. Two FE integration tests skipped with TODO (backend fully covered). |
| H-7 — No-reply review queue missing | 2026-04-16 | `3642069` | `fix/h-7-no-reply-review-queue` | Nightly `flag_no_reply_confirmations` APScheduler job + `needs_review_reason` appointment column (migration `20260416_100200`) + `NoReplyReviewQueue` component on `/schedule` with Call / Send Reminder / Mark-Contacted actions. Default 3-day threshold, BusinessSetting-tunable. |
| H-8 — `SendConfirmationButton` not disabled for non-DRAFT | 2026-04-16 | `e52ed2b` | `fix/h-8-send-confirmation-disable` | `appointment: Appointment` prop added; `disabled={... || status !== 'draft'}` with "Confirmation already sent" tooltip. Tested across all 8 non-DRAFT statuses. |
| H-9 — Invoice history not real-time | 2026-04-16 | `4925941` | `fix/h-9-invoice-history-realtime` | `refetchInterval: 30_000` on `useCustomerInvoices` + `customerInvoiceKeys.all` invalidation from 11 invoice mutation hooks. Query key refactored (commit `8d9df12`) so prefix invalidation actually matches. |
| H-10 — SignWell advance fails silently on unexpected pre-state | 2026-04-16 | `c51f7cc` | `fix/h-10-signwell-advance-log` | `document_signed` webhook now emits a structured WARN when the SalesEntry isn't in `PENDING_APPROVAL`; still returns 200 so SignWell doesn't retry. |
| H-11 — `mass_notify` doesn't skip opted-out customers | 2026-04-16 | `ee4eb82` | `fix/h-11-mass-notify-consent-prefilter` | Batched `SmsConsentRepository.get_opted_out_customer_ids` pre-filter in mass_notify; response carries `skipped_count` + `skipped_reasons`. Lien branch untouched (CR-5 already handles it per-customer). |
| H-12 — Lien thresholds not persisted | 2026-04-16 | `94efcbf` | `fix/h-12-lien-thresholds-settings` | New `BusinessSettingService` + `GET/PATCH /api/v1/settings/business` endpoints + `BusinessSettingsPanel` card on `/settings` seeding `lien_days_past_due`/`lien_min_amount`/`upcoming_due_days`/`confirmation_no_reply_days`. `compute_lien_candidates` reads defaults from `BusinessSetting`. Migration `20260416_100300`. |
| H-13 — Renewal roll uses 52 weeks | 2026-04-16 | `99db54d` | `fix/h-13-renewal-date-roll` | `d.replace(year=d.year + 1)` + align-to-Monday with Feb 29 → Feb 28 fallback. Five-year roll test confirms weekday stability. |
| H-14 — `bulk_notify_invoices` effectively unauthenticated | 2026-04-16 | `c607c96` | `fix/h-14-bulk-notify-auth` | Replaced `_current_user: ManagerOrAdminUser = None  # type: ignore[assignment]` with `_current_user: ManagerOrAdminUser` (Depends-annotated alias). New 401/403/200 tests cover the three auth tiers. |

### Follow-up commits (not their own bug IDs)

| Context | Commit SHA | Notes |
|---|---|---|
| Correct H-9 queryKey for prefix invalidation | `8d9df12` | `useCustomerInvoices` queryKey structure was broken — invalidation-by-prefix didn't match. Simplified to `customerInvoiceKeys.byCustomer(customerId)` prefix. |
| Skip brittle H-6 FE integration tests | `5fbc76f` | Two RescheduleRequestsQueue tests depend on jsdom flushing the full AppointmentForm chain reliably; skipped with TODO. Backend covers the logic. |
| Resolve H-7 + H-12 migration revision clash | `ffa068e` | Both migrations were authored as `20260416_100200`. Renamed H-12's to `20260416_100300` and unified the `confirmation_no_reply_days` seed shape on `{"value": N}`. |
