# 04 — Lead → inspection → estimate → contract (SignWell) → customer

**Request (paraphrased):**
> Lead calls for install/addition. I give an inspection date, have them fill the contact form. After inspection I build estimate (Google Sheets), send it, note in system that it was sent. If they confirm within a week, I use a Google Sheets contract template and send via SignNow. On signature, system notifies me automatically and I mark project confirmed — the lead becomes a customer with a job. If no response within a week, follow up weekly until confirm/decline.

**Status:** 🟡 PARTIAL

---

## What exists today

### Lead model + conversion
- `Lead` model distinct from `Customer`, with `customer_id` FK for post-conversion linking (`models/lead.py:51, 166-169`).
- Terminal status `CONVERTED` with `converted_at` timestamp (`models/lead.py:250-259`).
- `LeadService.convert_lead()` exists (`services/lead_service.py:938-1087`) and:
  - Carries over consent fields (SMS, email, terms).
  - Checks Tier-1 duplicates; supports `force=True`.
  - Sets lead status to CONVERTED and links `customer_id`.
- **Conversion is manual** — no auto-trigger from any signing event.

### E-signature (SignWell, not SignNow)
- `services/signwell/client.py` implements SignWell API client.
- `api/v1/signwell_webhooks.py` receives `document_completed` events, verifies HMAC-SHA256, fetches signed PDF, stores to S3, and creates a `CustomerDocument` (lines 167-176).
- Sales entry advances `pending_approval → send_contract` on signature (lines 180-182).
- **But** webhook does **not** call `convert_lead()` — signature advances the sales pipeline only.

### Estimates
- `EstimateService` + `Estimate` + `EstimateTemplate` models exist. Estimates are stored in the DB.
- `EstimateFollowUp` rows scheduled at Day 3, 7, 14, 21 in `EstimateService._schedule_follow_ups()` (`services/estimate_service.py:774-806`). Day 14 includes a "SAVE10" promo.
- Google Sheets is still referenced as an external source for estimate content ❓ — worth confirming whether estimates are now fully built in-app or still copy-pasted from Sheets.

### Follow-up processing
- `EstimateService.process_follow_ups()` exists (`services/estimate_service.py:566-623`) but **is not wired to any recurring scheduler** (`services/background_jobs.py` has other jobs — payments, renewals — but no call to `process_follow_ups`). Rows are created but never fire.

## What's missing

- Auto-trigger `convert_lead()` when SignWell reports `document_completed` (or leave it manual-approve-only — per your preference).
- Recurring scheduler wired to `process_follow_ups()` so weekly reminders actually send.
- In-app estimate builder (vs Google Sheets) — unclear how complete this is today.

## TODOs

- [ ] **TODO-04a** In `api/v1/signwell_webhooks.py`, after `document_completed`, call `LeadService.convert_lead()` for the related lead (or surface a one-click "Convert to customer" admin action). ❓
- [ ] **TODO-04b** Register `EstimateService.process_follow_ups()` as a recurring background job (APScheduler in `services/background_jobs.py`). Pick cadence — likely daily at a fixed hour.
- [ ] **TODO-04c** Confirm estimate builder status: if estimates are still external (Sheets), scope an in-app estimate composer. (Overlaps with #07 "Estimate button" work.) ❓
- [ ] **TODO-04d** Add a "contract not returned within 7 days" follow-up loop (weekly) — similar to estimate follow-ups but on the `send_contract` stage.

## Clarification questions ❓

1. **Auto-convert on signature?** Should the lead → customer step fire the instant SignWell confirms signature, or should admin get a notification and click "Convert"?
2. **Estimate builder:** is the in-app estimate flow sufficient, or do you still draft in Google Sheets and just record the sent date in the system?
3. **Follow-up cadence:** you said "weekly until confirm/decline." The current scheduled rows are Day 3/7/14/21. Keep that schedule, or move to strict weekly (7/14/21/28…)?
