# Obsidian Notes Enhancements — Investigation Summary

**Date:** 2026-04-23
**Scope:** Audit of 13 feature requests from voice-note transcript against current codebase state.
**Rule:** Analysis only. No code changes. Anything uncertain is logged as a clarification question.

---

## Legend
- ✅ **IMPLEMENTED** — Feature works as described.
- 🟡 **PARTIAL** — Some pieces exist; gaps documented.
- ❌ **NOT IMPLEMENTED** — No code found for this.
- ❓ **CLARIFICATION NEEDED** — See `99-clarification-questions.md`.

---

## Feature Scorecard

| # | Request | Status | Evidence | TODO file |
|---|---------|--------|----------|-----------|
| 1 | Customer tags propagate to jobs | ❌ | `job.py` has no tags field/relationship | [01](./01-customer-tags-to-jobs.md) |
| 2 | Every part of a job editable (incl. "week of") | 🟡 | `target_start/end_date` editable only while status = `TO_BE_SCHEDULED` | [02](./02-job-full-editability.md) |
| 3 | Staff logins / per-user session isolation / 7-day auto-login | 🟡 | Roles + 30-day refresh exist; UI filter state is local-only; target was 7-day | [03](./03-staff-auth-and-session.md) |
| 4 | Lead → inspection → estimate → SignWell → customer lifecycle | 🟡 | SignWell webhook + conversion function exist, but conversion is manual and webhook does not trigger it | [04](./04-lead-to-customer-lifecycle.md) |
| 5 | Node 4: docs carry from lead → customer automatically | ❌ | `convert_lead()` does not transfer `LeadAttachment` → `CustomerDocument` | [05](./05-node4-document-carryover.md) |
| 6 | On-site payment collection (cash / check / Stripe reader) | 🟡 | Collect Payment button + Stripe Terminal exist; method-specific notes on appointment unclear | [06](./06-onsite-payment-collection.md) |
| 7 | Estimate button (under Collect Payment) → SMS/email Yes/No → auto-job | 🟡 | Estimate creator + templates exist; auto-job-on-approval flow not confirmed | [07](./07-estimate-button-autojob.md) |
| 8 | Invoices tab as source of truth + filters + reminders + 3% Stripe fee + 2-wk due | 🟡 | Invoices page + filters + reminder fields exist; scheduled follow-ups + 3% surcharge + default 2-wk due missing | [08](./08-invoices-source-of-truth.md) |
| 9 | Admin-editable price list (UI, not code changes) | ❌ | `ServiceOffering` table + API exist; no admin UI in frontend | [09](./09-admin-editable-pricelist.md) |
| 10 | Multi-staff calendar overlay toggles in Schedules tab | 🟡 | Map view has staff filter; week/month calendar view does not | [10](./10-schedule-multi-staff-overlay.md) |
| 11 | Auto-notify next customer of rough ETA | ❌ | `ON_THE_WAY` template + `send_arrival_notification()` exist; no next-in-route auto-trigger | [11](./11-next-customer-eta-notify.md) |
| 12 | Get Directions toggles Google Maps ↔ Apple Maps | ✅ | `MapsPickerPopover.tsx` — user picks either | [12](./12-directions-maps-toggle.md) |
| 13 | Staff edit tags from appointment modal → propagate to customer + future jobs | 🟡 | Tag editor in modal writes to Customer ✅; Job has no tags so "future jobs" is moot until #1 is done | [01](./01-customer-tags-to-jobs.md) |

---

## Master TODO (everything still to do)

Grouped by priority tier. Cross-reference the linked per-feature notes for full detail.

### Tier A — Blocks stated workflows

- [ ] **TODO-01a** Add `tags` relationship on `Job` (many-to-many via `JobTag`) mirroring `CustomerTag`. See [01](./01-customer-tags-to-jobs.md).
- [ ] **TODO-01b** On job creation in `JobService.create_job` (`src/grins_platform/services/job_service.py:223`), copy the parent customer's tag set onto the new job.
- [ ] **TODO-01c** When `CustomerTagService` mutates tags, cascade the change to all open/future jobs of that customer (decide: only `TO_BE_SCHEDULED`? also `SCHEDULED`?). ❓
- [ ] **TODO-04a** Auto-trigger `LeadService.convert_lead()` from `signwell_webhooks.py` on `document_completed` (currently only advances the sales stage). ❓ (user may want manual review first)
- [ ] **TODO-05a** In `convert_lead()` (`src/grins_platform/services/lead_service.py:938`), transfer `LeadAttachment` rows to `CustomerDocument` so estimate/contract/misc uploads show up on the customer detail page.
- [ ] **TODO-05b** Confirm that estimate PDFs produced pre-signature are linked to the lead (not the sales_entry) so they get carried over. ❓
- [ ] **TODO-07a** Implement "customer approves estimate → auto-create Job in Jobs tab, linked to customer and targeted to the week entered on the estimate." Needs a customer-facing approval page + endpoint + Job auto-insert.
- [ ] **TODO-10a** Bring the staff-filter toggle from Map view into Calendar (week/month) view of the Schedules tab. Allow single / multi / all-staff overlay with distinct colors.

### Tier B — Automation gaps

- [ ] **TODO-03a** Shorten refresh-token lifetime from 30 days → 7 days (`src/grins_platform/services/auth_service.py:41`). Confirm this is what "re-login Mondays at 8am" maps to. ❓
- [ ] **TODO-03b** Decide whether each staff member should have their own login, or everyone logs in as admin and just toggles view. Current code already supports multi-user with roles → recommend the real multi-user path. ❓
- [ ] **TODO-03c** Persist per-user UI state (selected staff toggles, calendar filters) to the backend so it is per-account, not per-device localStorage. Confirms Kirill's phone view doesn't bleed into Voss's phone view.
- [ ] **TODO-04b** Wire `EstimateService.process_follow_ups()` into the background-job scheduler (APScheduler or equivalent) so Day 3/7/14/21 reminders actually send. Currently scheduled rows are created but never processed.
- [ ] **TODO-08a** Add scheduled invoice reminders: +10-11 days after send, day-before-due, then weekly past-due. Needs a cron/APScheduler job. Frequency should be researched/confirmed. ❓
- [ ] **TODO-08b** Add per-invoice (or global) toggle to enable/disable auto-follow-ups.
- [ ] **TODO-08c** Default invoice due date to `created + 14 days` unless overridden.
- [ ] **TODO-08d** Add 3% surcharge when payment method = Stripe (credit card), waive for cash/check/ACH/Zelle/Venmo. Needs UI disclosure + amount math + line item on the invoice.
- [ ] **TODO-11a** Implement "auto-notify next customer of rough ETA." Two choices: (a) on-route ETA button the tech taps when leaving current job, (b) derive automatically from appointment delay on status change. Recommend (a) for first cut — uses existing `notification_service.send_arrival_notification`. ❓
- [ ] **TODO-06a** Confirm cash/check flows record the amount + free-text note on the appointment or customer timeline (not only as an invoice). ❓

### Tier C — Admin UX

- [ ] **TODO-09a** Build an admin-only "Price List" settings page that CRUDs `ServiceOffering` rows (base_price, per-zone, pricing_model, category, is_active). Backend API already exists at `/api/v1/services`.
- [ ] **TODO-09b** Decide whether the same UI also drives the Estimate + Invoice templates' dropdown options so price edits flow through to Collect Payment and Send Estimate. ❓

### Tier D — Already done / small follow-ups

- [ ] **TODO-02a** Decide whether job target week ("week of") should remain locked post-scheduling or allow edit with an explicit reschedule side-effect. Current code throws `JobTargetDateEditNotAllowedError`. ❓
- [ ] **TODO-12a** (verify) Confirm Apple Maps link falls back gracefully on Android and Google Maps link works on iOS — nothing needed unless you want the toggle to auto-default by device.

---

## Files in this folder

- `00-investigation-summary.md` — this file
- `01-customer-tags-to-jobs.md`
- `02-job-full-editability.md`
- `03-staff-auth-and-session.md`
- `04-lead-to-customer-lifecycle.md`
- `05-node4-document-carryover.md`
- `06-onsite-payment-collection.md`
- `07-estimate-button-autojob.md`
- `08-invoices-source-of-truth.md`
- `09-admin-editable-pricelist.md`
- `10-schedule-multi-staff-overlay.md`
- `11-next-customer-eta-notify.md`
- `12-directions-maps-toggle.md`
- `99-clarification-questions.md` — consolidated list of ❓ items requiring your input before any coding
