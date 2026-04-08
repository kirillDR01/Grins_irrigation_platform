# CallRail SMS Integration — Feature Development Spec

**Status:** Phase 0 + 0.5 (API smoke test) complete — policy decisions locked — cleared to begin Phase 1
**Created:** 2026-04-07
**Last updated:** 2026-04-07 (Phase 0.5 live verification: real SMS send confirmed 200, §10.9 findings added, S2/S12 simplified)
**Owner:** TBD
**Scope decision (2026-04-07):** A single campaign may mix customers, leads, and ad-hoc phone numbers. No source restrictions. Ad-hoc phones from CSV auto-create ghost leads with `lead_source='campaign_import'`.
**Policy decisions locked (2026-04-07):** See §10.5b. All eight critical policy questions (dedupe, ad-hoc consent, consent_type, delivery receipts, webhook config, permissions, state machine, time window) are resolved with defaults.
**Live API verified (2026-04-07):** Real SMS sent via `POST /v3/a/{account_id}/text-messages.json` returned HTTP 200 and arrived on the owner's phone. See §10.9 for the full field-by-field contract + simplifications this enables.

### Spec organization (where to find what)

| Slice | Where it lives |
|---|---|
| **Context & goal** | §1 |
| **API & compliance research** | §2 |
| **Existing scaffolding inventory** | §3 |
| **Architectural design** | §4 (layers), §10.3 (structural gaps with fix specs), §10.5a (Recipient model), §14 (state machines), §12 (external config), §15 (ops) |
| **Requirements (policy + compliance)** | §10.5b (locked decisions), §13 (permissions), §17 (compliance details) |
| **Requirements (UX)** | §16 (UX specifications), Phase 5 in §10.6 |
| **Tasks (implementation checklists)** | §10.6 Phase 0 → Phase 7 |
| **Testing strategy** | §18 |
| **File references** | §11 |
| **Severity + priority matrix** | §10.8 |
| **Risks** | §8 |
**Primary business driver:** Send scheduling outreach SMS to ~300 existing customers who are ready to book jobs, using the Grins CallRail account rather than introducing a new vendor.

---

## 1. Context & Goal

Grins has an existing CallRail account used for call tracking. We want to leverage CallRail's outbound SMS API to text ~300 current customers to get their jobs scheduled — and more broadly, to turn CallRail into the SMS delivery backbone for all customer-facing texts sent from the Grin's Irrigation Platform CRM (appointment reminders, confirmations, marketing campaigns, one-off blasts).

**Sender number:** `(952) 529-3750` — this is the Grins website phone number and will be used as the CallRail tracking number that all outbound SMS originate from. Stored as `CALLRAIL_TRACKING_NUMBER` in E.164 format (`+19525293750`).

### 1.1 Credentials & Secrets
All CallRail credentials live in the root `.env` file (gitignored). **Do not commit any API keys or secrets into this markdown or any tracked file.** The backend reads them at runtime via environment variables:

| Variable | Purpose | Status |
|---|---|---|
| `CALLRAIL_API_KEY` | REST API authentication token | **Set in `.env`** |
| `CALLRAIL_ACCOUNT_ID` | Account scope for API calls | TBD — fetch via account list endpoint |
| `CALLRAIL_COMPANY_ID` | Company scope for SMS sends | TBD — fetch via company list endpoint |
| `CALLRAIL_TRACKING_NUMBER` | Sender number for outbound SMS | **Set in `.env`** → `+19525293750` |

To verify the `.env` entry isn't tracked:
```bash
git check-ignore -v .env    # should print: .gitignore:29:.env  .env
```

If the API key ever needs to be rotated, update it in `.env` locally and redeploy — never paste it into docs, commits, Slack, or screenshots.

The integration must live inside the existing platform so that:

- Sends are tracked in the same `sent_messages` table as all other customer comms
- Opt-in/opt-out consent rules continue to apply uniformly
- Staff can launch campaigns from the Communications tab (and bulk-select from the Customers tab) without leaving the CRM
- Replies land back in the CRM inbox rather than in CallRail only

---

## 2. CallRail API Capabilities — Research Summary

### 2.1 API basics
- **Base URL:** `https://api.callrail.com/v3/`
- **Auth header:** `Authorization: Token token="YOUR_API_KEY"`
- **Format:** REST, JSON, standard HTTP verbs
- **Send endpoint (expected):** `POST /v3/a/{account_id}/text-messages.json`
- **Required body fields (expected):** `company_id`, `tracking_number`, `customer_phone_number`, `content`
- **List endpoints available for:** accounts, companies, tracking numbers, text message history

### 2.2 Rate limits (critical)
| Scope       | Hourly       | Daily          |
|-------------|--------------|----------------|
| SMS Send    | 150/hour     | 1,000/day      |
| General API | 1,000/hour   | 10,000/day     |

**Implication for 300-customer blast:**
- 1,000/day cap → fine for a single day
- 150/hour cap → forces at least a ~2-hour throttled drip for all 300
- We must build a rate-limiter that tracks both windows per-tenant

### 2.3 Compliance requirements (2026)
- **10DLC registration is mandatory** for any business sending outbound A2P SMS. Unregistered messages are **blocked outright** by US carriers in 2026, not just surcharged. Registration happens through CallRail → Settings → Text Messaging Compliance. Registration fee: ~$1.50/mo mixed-use campaign.
- **Sender identification** is required in every message ("Grins Irrigation:" prefix).
- **Opt-out keyword** must be present. CallRail will auto-append STOP language on first contact if none is included, but we should bake it into our templates. Approved keywords: STOP, CANCEL, UNSUBSCRIBE, QUIT, END.
- **Hard blocker:** if 10DLC is not registered on the Grins CallRail account, messages will silently fail to deliver even though the API returns 200. This must be verified before go-live.

### 2.4 No official CLI
CallRail does not ship a dedicated CLI tool. We'll talk to the REST API directly from Python using `httpx` (already in the project's async stack).

### 2.5 Sources
- https://apidocs.callrail.com/
- https://support.callrail.com/hc/en-us/articles/30896711642253-Sending-text-messages-in-CallRail
- https://support.callrail.com/hc/en-us/articles/18593904382221-Text-Message-Compliance-10DLC-regulations-and-guidelines
- https://support.callrail.com/hc/en-us/articles/34065659566221-Message-Flows
- https://rollout.com/integration-guides/call-rail/api-essentials

---

## 3. Existing Platform Scaffolding (Already Built)

This integration is **~80% existing scaffolding + ~20% new wiring**. Inventory of what's already in place:

### 3.1 Backend — services
- `src/grins_platform/services/sms_service.py` — `SMSService` class with:
  - `send_message()` (consent + dedupe + record + send)
  - `send_automated_message()` (adds 8AM–9PM CT time window)
  - `handle_inbound()` — STOP / informal opt-out detection
  - `_process_exact_opt_out()` — creates `SmsConsentRecord`, sends confirmation
  - `check_sms_consent()` — per-phone consent lookup
  - `enforce_time_window()` — defers automated messages to 8AM CT if out of window
  - **`_send_via_twilio()` is a placeholder stub** at line 228–243 that just returns a fake SID — **this is the exact swap-in point for CallRail**.
- `src/grins_platform/services/campaign_service.py` — `CampaignService` with consent gating, CAN-SPAM unsubscribe auto-append, campaign lifecycle management, recipient expansion from `target_audience` JSONB.
- `src/grins_platform/services/background_jobs.py` — existing background job runner (target for throttled campaign sender).
- `src/grins_platform/services/notification_service.py` — generic notification dispatcher.

### 3.2 Backend — models
- `src/grins_platform/models/sent_message.py` — `SentMessage`:
  - FK to `customer_id`, `lead_id`, `job_id`, `appointment_id`
  - `message_type` allowed values already include `'campaign'`
  - `delivery_status`: `pending | scheduled | sent | delivered | failed | cancelled`
  - `twilio_sid`, `error_message`, `scheduled_for`, `sent_at` columns already exist
  - **No schema change needed** — `twilio_sid` column can store CallRail message IDs (may rename to `provider_message_id` in a follow-up)
- `src/grins_platform/models/campaign.py` — `Campaign` + `CampaignRecipient`:
  - `target_audience` JSONB for filter definition
  - `campaign_type`, `status`, `scheduled_at`, `sent_at`
  - `CampaignRecipient` has `channel`, `delivery_status`, `sent_at`, `error_message`
- `src/grins_platform/models/sms_consent_record.py` — full consent audit trail per phone number

### 3.3 Backend — API routes
Already present in `src/grins_platform/api/v1/`:
- `sms.py` — `POST /v1/sms/send`, `BulkSendRequest`, `BulkSendResponse`, communications queue endpoint, inbound webhook
- `campaigns.py` — campaign CRUD + send
- `communications.py` — communications feature API
- `sent_messages.py` — sent message log
- `webhooks.py` — inbound webhook handlers (Twilio format today; needs CallRail variant added)

### 3.4 Frontend — pages & features
- `frontend/src/pages/Communications.tsx` + `features/communications/components/`:
  - `CommunicationsDashboard.tsx`
  - `CommunicationsQueue.tsx`
  - `SentMessagesLog.tsx`
- `frontend/src/pages/Marketing.tsx` + `features/marketing/components/CampaignManager.tsx`
- `frontend/src/pages/Customers.tsx` + `features/customers/` (for bulk-select entry point)

### 3.5 What is NOT yet built
- CallRail HTTP client module
- Provider abstraction (currently hard-wired to a Twilio stub)
- CallRail-specific rate limiter (150/hr + 1,000/day per account)
- CallRail inbound webhook route + signature verification
- "New Text Campaign" modal on Communications tab
- "Text Selected" bulk action on Customers tab
- Env vars: `CALLRAIL_API_KEY`, `CALLRAIL_ACCOUNT_ID`, `CALLRAIL_COMPANY_ID`, `CALLRAIL_TRACKING_NUMBER`

---

## 4. Integration Architecture — Two Layers

### Layer 1 — Provider swap (foundation)
**Goal:** Replace the Twilio stub with a real CallRail client. Zero UI changes. Every existing caller of `SMSService.send_message()` (appointment reminders, confirmations, etc.) starts going through CallRail automatically.

**Files to touch:**

1. **NEW** `src/grins_platform/services/callrail_client.py`
   - Thin async HTTP client using `httpx.AsyncClient`
   - Methods:
     - `async send_text(to: str, body: str) -> CallRailSendResult`
     - `async list_tracking_numbers() -> list[TrackingNumber]`
     - `async verify_webhook_signature(headers, raw_body) -> bool`
   - Reads env: `CALLRAIL_API_KEY`, `CALLRAIL_ACCOUNT_ID`, `CALLRAIL_COMPANY_ID`, `CALLRAIL_TRACKING_NUMBER`
   - Raises typed exceptions: `CallRailAuthError`, `CallRailRateLimitError`, `CallRailValidationError`
   - Structured logging via `LoggerMixin`

2. **NEW** `src/grins_platform/services/rate_limiter.py` (or add to `background_jobs.py`)
   - Sliding-window limiter tracking both 150/hr and 1,000/day per CallRail account
   - Backed by DB counter table OR in-memory for MVP (acceptable given single-worker dev)
   - `acquire()` returns `(allowed: bool, retry_after_seconds: int)`

3. **EDIT** `src/grins_platform/services/sms_service.py`
   - Rewrite `_send_via_twilio()` to delegate to `CallRailClient.send_text()`
   - Keep method name initially to avoid cascading refactors; rename in a follow-up PR
   - Store CallRail message ID in the existing `twilio_sid` column
   - Wrap the send in the rate limiter; if blocked, persist the message with `delivery_status='scheduled'` and `scheduled_for=now + retry_after`

4. **EDIT** `src/grins_platform/api/v1/webhooks.py`
   - Add `POST /v1/webhooks/callrail/inbound` route
   - Verify signature via `CallRailClient.verify_webhook_signature()`
   - Parse CallRail's inbound SMS payload → call existing `SMSService.handle_inbound()` (which already handles STOP / informal opt-out / forward-to-admin)

5. **EDIT** `.env.example`
   - Add `CALLRAIL_API_KEY=`, `CALLRAIL_ACCOUNT_ID=`, `CALLRAIL_COMPANY_ID=`, `CALLRAIL_TRACKING_NUMBER=` (placeholder values only, no real secrets)
   - Document that `TWILIO_*` vars become optional
   - **Real values live only in the gitignored `.env`** — `CALLRAIL_API_KEY` and `CALLRAIL_TRACKING_NUMBER=+19525293750` are already set there

6. **EDIT** `src/grins_platform/services/campaign_service.py`
   - No code change required — it already depends on `SMSService`. Once Layer 1 is done, campaigns flow through CallRail automatically.

**Layer 1 unlocks:** Every existing SMS path in the platform now sends through CallRail. This alone is enough to unblock a one-off CSV-driven script for the 300-customer blast.

---

### Layer 2 — Bulk campaign UI (300-customer use case)

**Goal:** Non-developer staff can build an audience, compose a message, preview it, and launch a throttled send — all from the Communications tab. Customers tab gets a "Text Selected" shortcut into the same flow.

**User flow:**
1. Staff opens Communications tab → clicks **New Text Campaign** (primary CTA)
2. **Audience builder** (modal step 1 of 3) — three ways to build the recipient list:
   - Search/filter existing customers by tag, last service date, opt-in status, city, property type
   - Paste or upload CSV of phone numbers (auto-matches to existing customers by phone; unmatched rows create a campaign-only recipient)
   - Select a saved segment (future enhancement, not MVP)
3. **Message composer** (modal step 2 of 3):
   - Template with `{first_name}` / `{last_name}` merge fields
   - Character counter + segment count (SMS vs MMS)
   - Live preview showing the sender prefix ("Grins Irrigation:") and auto-appended STOP footer
4. **Review & schedule** (modal step 3 of 3):
   - Shows total recipients, how many will actually send after consent filter drops opted-out customers
   - Estimated completion time (based on 140/hr send rate)
   - Choose: Send now (respecting time window) OR Schedule for later
5. **Confirm** → creates `Campaign` + `CampaignRecipient` rows, enqueues a background job

**Backend job:**
- `process_campaign_batch(campaign_id)` runs on interval
- Dequeues up to N recipients (N chosen to stay under 140/hr cap)
- For each recipient: consent check → time-window check → `SMSService.send_message()` → update `CampaignRecipient.delivery_status` + create `SentMessage` row
- Resumable on crash (status-driven, not step-counter)
- Emits progress events readable by the existing `CommunicationsQueue` component

**Files to touch:**

Backend:
- **EDIT** `src/grins_platform/services/campaign_service.py` — add `send_campaign_throttled()` method that respects CallRail limits (if not already handled generically at the SMSService layer)
- **EDIT** `src/grins_platform/services/background_jobs.py` — add `process_campaign_batch()` job
- **EDIT** `src/grins_platform/api/v1/campaigns.py` — ensure `POST /v1/campaigns/{id}/send` endpoint is fully wired
- **EDIT** `src/grins_platform/schemas/campaign.py` — add schemas for CSV upload + audience preview if not already present

Frontend:
- **NEW** `frontend/src/features/communications/components/NewTextCampaignModal.tsx` — 3-step wizard
- **NEW** `frontend/src/features/communications/components/AudienceBuilder.tsx` — customer filter/search + CSV import
- **NEW** `frontend/src/features/communications/components/MessageComposer.tsx` — template + preview
- **NEW** `frontend/src/features/communications/components/CampaignReview.tsx` — final review + schedule
- **EDIT** `frontend/src/pages/Communications.tsx` — add "New Campaign" button
- **EDIT** `frontend/src/pages/Customers.tsx` — add "Text Selected" bulk action that opens `NewTextCampaignModal` with selection pre-loaded
- **EDIT** `frontend/src/features/communications/api/` — add API client calls for campaign create/send
- **REUSE** `features/marketing/components/CampaignManager.tsx` — evaluate whether its audience UI is generic enough to extend instead of duplicating

---

## 5. Minimum Viable Path — Unblock the 300 Customers This Week

If the 300-customer scheduling outreach is time-critical, ship in this order:

1. **Layer 1 backend (provider swap)** — ~2 hours of work
   - `callrail_client.py`
   - Rewrite `_send_via_twilio()`
   - Rate limiter (in-memory is fine for MVP)
   - Env vars + `.env.example`
2. **One-off admin script** `scripts/send_callrail_campaign.py`
   - Reads CSV (`phone,first_name,last_name`)
   - Reads message template from a file or CLI arg
   - Dry-run mode (prints every message without sending) — **run this first and have the owner eyeball the output**
   - Live mode with `--confirm` flag
   - Throttles at ~140/hr
   - Writes progress log to stdout + persists every attempt as a `SentMessage` row tied to the matched customer
   - Skips customers who have opted out (via `SmsConsentRecord`)
3. **Monitor via existing UI** — `SentMessagesLog` component auto-populates from the `sent_messages` table

**Then Layer 2 (the full Communications-tab UI) happens next week as a proper feature PR.**

---

## 6. Where Each Tab Fits

- **Customers tab** — bulk "Text Selected" action on the customer table. Multi-select rows → click action → opens `NewTextCampaignModal` with selection pre-loaded into the audience builder. Same modal, different entry point.
- **Communications tab** — primary home: `New Text Campaign` button, active/scheduled campaign list, `CommunicationsQueue`, `SentMessagesLog`.
- **Marketing tab** — continues to own the multi-channel campaign manager (`CampaignManager.tsx`). If its audience UI is generic enough, Communications' modal can share it. Otherwise keep them separate: Communications = tactical one-off blasts, Marketing = multi-touch campaigns.

---

## 7. Open Questions & Decisions Needed from Owner

1. **CallRail credentials** — ✅ API key set in `.env`. ✅ Tracking number set: `+19525293750` (website line). ⏳ Still need `account_id` and `company_id` — these can be fetched on first run by hitting `GET /v3/a.json` and `GET /v3/a/{account_id}/companies.json` with the API key.
2. **10DLC registration status** — is the Grins CallRail account already registered for the `(952) 529-3750` tracking number? **Hard blocker** if not.
3. **MVP path vs full UI** — ship Layer 1 + CSV script first to unblock the 300 customers, or go straight to full UI?
4. **Where do the 300 customers live?** — already in `customers` table, or still in a sheet/CSV? If the latter, import first so consent tracking + history attach cleanly.
5. **Keep Twilio alongside?** — is Twilio wired up in prod anywhere, or still just the stub? This determines whether we replace-in-place or add a provider abstraction.
6. **Reply handling** — when a customer replies "YES schedule me", where does it land? CallRail inbox + platform inbox + Slack ping to owner + auto-create a job-scheduling task?
7. **Sender identity format** — exact prefix for every message? ("Grins Irrigation:" vs "Grin's Irrigation Co:" vs something else)
8. **Message template for the 300-customer blast** — draft copy so we can dry-run it.
9. **Tracking number strategy** — one dedicated SMS number, or rotate across several to smooth rate limits and reduce spam-filter risk?

---

## 8. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| 10DLC not registered → silent delivery failures | 300 customers never get texted, we don't know it failed | Verify registration in CallRail dashboard BEFORE Layer 1 ships. Add a startup health check that fails loudly if not registered. |
| Rate-limit overruns (151st send in an hour) | CallRail returns 429, message stuck in "pending" | Rate limiter with retry + `scheduled_for` fallback. Test with a synthetic 200-message run in dev. |
| Sending to opted-out customers | Compliance violation, TCPA fines | Consent check happens inside `SMSService.send_message()` before any CallRail call — already coded. Add an integration test. |
| Time-window violations (automated sends before 8AM / after 9PM CT) | Customer complaints | `enforce_time_window()` already exists — re-verify it's called on the campaign path. |
| Replies lost in CallRail inbox | Customers ask to schedule, we miss it | CallRail inbound webhook → `handle_inbound()` → persist to platform inbox + notify staff. **Must ship with Layer 1**, not Layer 2. |
| Customer phone format inconsistencies in DB | Sends fail or go to wrong number | `_format_phone()` already normalizes to E.164. Dry-run script should report any phones that can't be normalized. |
| CallRail API outage mid-campaign | Partial send, stuck state | Status-driven resumable job. Failed sends get retried up to N times with exponential backoff. |
| Cost surprise from MMS / international / high volume | Unexpected CallRail bill | Hard-cap daily sends at 1,000 in the rate limiter. Alert owner via email if any campaign exceeds 500 recipients. |

---

## 9. Implementation Checklist

### Layer 1 — Provider swap
- [ ] Verify 10DLC registration on Grins CallRail account for `(952) 529-3750`
- [x] `CALLRAIL_API_KEY` stored in `.env` (gitignored)
- [x] `CALLRAIL_TRACKING_NUMBER=+19525293750` stored in `.env`
- [ ] Fetch + store `CALLRAIL_ACCOUNT_ID` and `CALLRAIL_COMPANY_ID` from API
- [ ] Create `services/callrail_client.py` with `send_text` + `verify_webhook_signature`
- [ ] Create rate limiter (150/hr + 1,000/day sliding window)
- [ ] Rewrite `SMSService._send_via_twilio()` to delegate to CallRail
- [ ] Add CallRail inbound webhook route in `api/v1/webhooks.py`
- [ ] Update `.env.example`
- [ ] Unit tests: client happy path, auth error, rate-limit error, signature verification
- [ ] Integration test: full `SMSService.send_message()` path against a CallRail sandbox/test number
- [ ] Manual smoke test: send one real SMS to owner's phone, verify inbound STOP reply creates `SmsConsentRecord`

### Immediate unblock — CSV script
- [ ] Create `scripts/send_callrail_campaign.py` with dry-run mode
- [ ] Prep the 300-customer CSV (from wherever they live today)
- [ ] Draft message template, reviewed by owner
- [ ] Dry-run → owner review → live run with `--confirm`
- [ ] Verify replies land correctly via webhook

### Layer 2 — Campaign UI
- [ ] Audit `CampaignManager.tsx` for reusable audience UI
- [ ] Build `NewTextCampaignModal` 3-step wizard
- [ ] Build `AudienceBuilder`, `MessageComposer`, `CampaignReview` components
- [ ] Add "New Campaign" button to Communications tab
- [ ] Add "Text Selected" bulk action to Customers tab
- [ ] Wire `process_campaign_batch` background job
- [ ] E2E test: build audience → send → verify `SentMessagesLog` populates → verify delivery statuses
- [ ] Documentation update in README / DEVLOG

---

## 10. Deep Repo Analysis — Gap Report (2026-04-07)

This section is the authoritative gap list produced by a full backend + frontend audit. It supersedes the more optimistic "80% built" framing in §3 — the scaffolding exists but has three structural bugs and several missing pieces that must be resolved before the Communications tab can actually send SMS via CallRail.

### 10.1 Verdict

**NOT ready to connect as-is.** Three blockers must be fixed or campaigns will silently fail even with a perfect CallRail client. One of the blockers is a pre-existing bug unrelated to CallRail.

### 10.2 Blockers (must fix first)

#### B1 — `CampaignService` is never handed an `SMSService` instance
- **Location:** `src/grins_platform/api/v1/campaigns.py:54`
- **Symptom:** Route instantiates `CampaignService(campaign_repository=repo)` without passing `sms_service` or `email_service`. Inside `_send_to_recipient()` there's a `if self.sms_service is not None:` guard → SMS path is skipped entirely. Campaign send endpoint returns success with 0 sent.
- **Fix:** Add a DI helper in `api/dependencies.py` (e.g. `get_campaign_service()`) that wires `SMSService(db)` and `EmailService(db)` into `CampaignService`. Update the route to depend on it.

#### B2 — Campaign sends bypass `SmsConsentRecord` consent check
- **Location:** `src/grins_platform/services/campaign_service.py` around lines 592–600
- **Symptom:** Campaigns read `Customer.sms_opt_in` directly and pass `sms_opt_in=True` into `SMSService.send_message()`, which skips `check_sms_consent()`. A customer who previously replied STOP (creating an `SmsConsentRecord` row) will still be texted by a campaign. **TCPA compliance risk.**
- **Fix:** Centralize the consent check in `SMSService` so every send path — automated, manual, campaign — hits `check_sms_consent(phone)` before provider dispatch. Remove the `sms_opt_in` parameter override path in the campaign loop.

#### B3 — `POST /sms/send-bulk` runs synchronously in the HTTP request thread
- **Location:** `src/grins_platform/api/v1/sms.py:199–250`
- **Symptom:** Iterates recipients sequentially, no throttling, no queue, no rate limit. For 300 customers: (a) blows past CallRail's 150/hr cap → 429s, (b) holds the HTTP request open for minutes → proxy timeout.
- **Fix:** Refactor to "create + enqueue": persist recipients as `CampaignRecipient` rows, return 202 immediately, let a background worker drain the queue under rate limit.

#### B4 — 24-hour dedupe in `SMSService.send_message()` silently blocks back-to-back campaigns
- **Location:** `src/grins_platform/services/sms_service.py:113–134`
- **Symptom:** Every `send_message()` call checks `get_by_customer_and_type(customer_id, message_type, hours_back=24)` and returns `success: false` if a match is found. Campaign sends use `message_type='campaign'`. **Consequence:** if you run a campaign today and run a second one tomorrow (within 24h), every customer who got the first one silently fails on the second. The UI shows "success" but the SMS never goes out. Also breaks retry-failed-recipients flow within the same campaign.
- **Fix:** Introduce `campaign_id: UUID | None = None` parameter on `send_message()`. When `campaign_id` is set, the dedupe check is scoped to `(customer_id_or_lead_id, campaign_id)` — preventing double-send of the same campaign to the same recipient — instead of `(customer_id, message_type)`. Per-recipient-per-campaign dedupe is additionally enforced by the `CampaignRecipient` state machine (see S13): a row in state `sent` or `sending` cannot be re-picked by the worker.
- **Severity:** Critical — silent data loss on any second-same-day campaign.

### 10.3 Structural gaps (required for clean CallRail wiring + future Twilio swap)

#### S1 — No SMS provider abstraction
- **Location:** `src/grins_platform/services/sms_service.py` — class is named `SMSService` and `_send_via_twilio()` is a method on it. Grep for `class.*Provider|BaseSMSProvider|SmsProvider|provider_factory|get_sms_provider` in `src/` returns **no matches**.
- **Fix — Strategy pattern:**
  ```
  src/grins_platform/services/sms/
  ├── __init__.py
  ├── base.py              # BaseSMSProvider Protocol
  ├── callrail_provider.py # CallRailProvider
  ├── twilio_provider.py   # TwilioProvider (preserves current stub)
  ├── null_provider.py     # NullProvider for tests / dry-run
  └── factory.py           # get_sms_provider() reads SMS_PROVIDER env, returns instance
  ```
  **`BaseSMSProvider` Protocol (minimal surface):**
  ```python
  class BaseSMSProvider(Protocol):
      @property
      def provider_name(self) -> str: ...
      async def send_text(self, to: str, body: str) -> ProviderSendResult: ...
      async def verify_webhook_signature(self, headers, raw_body) -> bool: ...
      def parse_inbound_webhook(self, payload: dict) -> InboundSMS: ...
  ```
  **`SMSService` becomes provider-agnostic** — keeps ALL business logic (consent, time window, dedupe, persistence) and takes a provider via constructor:
  ```python
  class SMSService:
      def __init__(self, session, provider: BaseSMSProvider | None = None):
          self.provider = provider or get_sms_provider()
  ```
  **Swap procedure after Phase 1:** set `SMS_PROVIDER=twilio` (or `callrail`) in `.env`. No code changes.

#### S2 — ~~No outbound SMS rate limiter~~ → Read CallRail response headers (simplified 2026-04-07)
- **Original concern:** Nothing enforces CallRail's 150/hr + 1,000/day outbound send caps. Originally planned as a Redis sliding-window counter.
- **Phase 0.5 finding:** CallRail returns authoritative rate-limit state on **every response**:
  ```
  x-rate-limit-hourly-allowed: 150
  x-rate-limit-hourly-used: 1
  x-rate-limit-daily-allowed: 1000
  x-rate-limit-daily-used: 1
  ```
- **Simplified fix:** `CallRailProvider.send_text()` parses these headers on every response and updates an in-memory + Redis-cached tuple `(hourly_remaining, daily_remaining, fetched_at)`. Other workers read this before claiming the next recipient. If remaining < threshold (e.g., 5), defer new sends and let the window reset.
- No sliding-window math, no atomic counters, no race conditions on our side — CallRail is the source of truth.
- Redis is only used as a shared cache for other workers to see the latest known values; a stale read only causes minor over-aggression, and the next send will correct it via the fresh header.
- **New file name:** `services/sms/rate_limit_tracker.py` (not `rate_limiter.py`) — it's a TRACKER that reads headers, not a LIMITER that maintains its own counters.
- **Blocking behavior:** If `hourly_remaining <= 5`, refuse new sends and return `retry_after_seconds = seconds_until_next_hour`. Same for daily.

#### S3 — Background jobs use in-process APScheduler, not worker-safe
- **Location:** `src/grins_platform/services/background_jobs.py`
- **Current state:** APScheduler with cron jobs registered in-process. Jobs are daily/weekly maintenance tasks (escalate_failed_payments, check_upcoming_renewals, etc.). No worker pool, no persistent queue, no distributed job state.
- **Problem:** A 300-recipient throttled campaign dripping over 2+ hours would block a FastAPI worker and lose progress on pod restart.
- **Fix options:**
  - **MVP (chosen):** Add an APScheduler interval job `process_pending_campaign_recipients` that runs every 60 seconds, polls `campaign_recipients WHERE delivery_status='pending'`, sends up to N per tick under the rate limiter, updates status in DB. State is DB-persistent so restarts are safe. Imprecise throttle but fine for 140/hr target.
  - **Proper (follow-up):** ARQ (async Redis queue). Redis already running → minimal infra cost. First-class retries, distributed workers, persistent job state. ~4 hours to wire. Do this after the 300-customer blast ships.

#### S4 — No CallRail inbound webhook route
- **Location:** `src/grins_platform/api/v1/webhooks.py:988–1040` handles `POST /webhooks/twilio-inbound` with Twilio's form-encoded payload + `X-Twilio-Signature`. CallRail's payload shape and signature mechanism are different.
- **Fix:** Add `POST /webhooks/callrail/inbound`. In the new provider abstraction, `verify_webhook_signature()` and `parse_inbound_webhook()` belong on the provider, so the route is thin:
  ```python
  provider = get_sms_provider()
  await provider.verify_webhook_signature(request.headers, raw_body)
  inbound = provider.parse_inbound_webhook(payload)
  return await sms_service.handle_inbound(inbound.from_phone, inbound.body, inbound.provider_sid)
  ```
  **Must ship with Phase 1** — otherwise STOP replies get lost and we violate opt-out compliance.

#### S5 — Audience filter is nearly empty
- **Location:** `campaign_service._filter_recipients()` lines 468–529
- **Supported today:** `lead_source`, `is_active`, `no_appointment_in_days`. That's it.
- **Missing filters needed:** `sms_opt_in=true` (critical), `ids_include=[...]` (for bulk-select passthrough from Customers tab), `cities=[...]`, `last_service_between=[...]`, `tags_include=[...]`.
- **Fix:** Extend `_filter_recipients()` with a query-builder dict schema. Schema-validate `target_audience` in `CampaignCreate` (currently arbitrary JSONB). Add joins for Appointment (date filters) and Property (city filters).

#### S6 — No merge-field templating
- **Location:** `SMSService.send_message()` accepts a pre-rendered string.
- **Problem:** Can't personalize `{first_name}` / `{last_name}` / `{next_appointment_date}` at send time.
- **Fix:** New `services/sms/templating.py` util using `str.format_map()` with a safe default dict (missing keys render as empty string, not `KeyError`). Campaign worker renders per recipient before the provider call. Keep the render function small — no Jinja, no conditionals, no loops.

#### S7 — No multi-select / bulk action on Customers list
- **Location:** `frontend/src/features/customers/components/CustomerList.tsx` uses TanStack Table but has no checkbox column or bulk-action toolbar.
- **Problem:** The "Text Selected from Customers tab" entry point can't work until this exists.
- **Fix:** Add a checkbox column via TanStack Table's row-selection API. Add a sticky bulk-action bar that appears on selection with "Text Selected" button. Pass selected customer IDs into `NewTextCampaignModal` via `ids_include` pre-load.

#### S8 — Communications tab has no compose/send UI
- **Location:** `frontend/src/pages/Communications.tsx` + `features/communications/components/CommunicationsDashboard.tsx`
- **Current state:** Exactly two tabs — `CommunicationsQueue` (inbound unaddressed messages) and `SentMessagesLog` (outbound history). Zero compose, zero audience picker, zero preview, zero "New Campaign" button.
- **Fix:** See §10.5 Phase 5 below — full wizard modal + new "Campaigns" tab.

#### S10 — Ad-hoc CSV uploads have no real consent gate
- **Location:** `src/grins_platform/services/sms_service.py:394–417` — `check_sms_consent()` is phone-keyed against `SmsConsentRecord` and returns `True` (default allow) when no records exist.
- **Problem:** A ghost lead created from a CSV upload has no `SmsConsentRecord` row → `check_sms_consent()` returns True → the send proceeds even though `Lead.sms_consent=false`. The "consent required" language in the original §10.5a is **technically false** for ad-hoc uploads. TCPA gray zone.
- **Fix (locked decision — see §10.5b):** Staff attestation model. The CSV upload UI in Phase 5 requires the uploading staff user to check a box affirming each contact has an established business relationship with Grins and has consented to receive SMS. On upload confirmation, the backend auto-creates an `SmsConsentRecord` row per distinct phone with:
  - `consent_type = 'marketing'`
  - `consent_given = true`
  - `consent_method = 'csv_upload_staff_attestation'`
  - `consent_language_shown = "<attestation text>"` (stored verbatim for audit)
  - `consent_form_version = <version string>`
  - `consent_timestamp = now()`
  - `customer_id` or `lead_id` populated once the ghost lead is created
- This creates a permanent audit trail of who attested for which phones and when.

#### S11 — `consent_type` is ignored by the current `check_sms_consent()` path
- **Location:** `sms_service.py:394–417` — query fetches the most-recent `SmsConsentRecord.consent_given` for a phone, ignoring `consent_type`.
- **Problem:** The model has a mandatory `consent_type` column. The existing opt-out code writes `"marketing"`. Transactional messages (appointment reminders) and marketing campaigns have different legal bars — TCPA allows transactional messages under the "established business relationship" exemption even without explicit marketing consent. The current code conflates them. Also: a customer who replied STOP to a marketing blast would also be blocked from receiving appointment reminders, which is wrong.
- **Fix (locked decision — see §10.5b):** Three consent types with explicit semantics:
  - `marketing` — promotional content, campaigns, newsletters. Requires explicit opt-in (either form consent, text START, or staff CSV attestation). Opt-out via STOP blocks all future marketing.
  - `transactional` — appointment confirmations, reminders, on-the-way, completion, invoices. Allowed under EBR without explicit marketing consent. Only blocked by a HARD-STOP signal (global opt-out).
  - `operational` — STOP confirmations, fraud alerts, legally-required service notifications. Always allowed.
- `check_sms_consent(phone, consent_type)` becomes:
  1. If a hard-STOP record exists (`consent_method='text_stop'` with `consent_given=false`) → deny ALL outbound to this phone forever except `operational`.
  2. For `marketing`: require the most recent `marketing`-type record to have `consent_given=true`, OR fall back to `Customer.sms_opt_in=true` / `Lead.sms_consent=true`. No records + no flag = deny (strict).
  3. For `transactional`: default allow, but respect hard-STOP.
  4. For `operational`: always allow.

#### S12 — No delivery status webhook → `sent` IS the terminal happy state (confirmed 2026-04-07)
- **Phase 0.5 finding:** CallRail's send response has NO `delivery_status` / `status` / `callback_url` field. No reference to delivery webhooks in any response header. **CallRail does not expose delivery status callbacks.** Confirmed via live send on 2026-04-07.
- **Decision:** `sent` is the terminal happy state. UI labels say "Sent" not "Delivered." No delivery webhook route is needed.
- The `CALLRAIL_DELIVERY_WEBHOOK_ENABLED` env var is REMOVED from the plan.
- The `POST /webhooks/callrail/delivery-status` route is REMOVED from Phase 1.
- The `sent → delivered` transition is REMOVED from the state machine (§14).
- If CallRail ever adds delivery callbacks in a future API version, we re-evaluate — it's a non-breaking additive change, not a hard design dependency.
- **Observable states remain:** `pending → sending → sent / failed / cancelled`. Failed transitions come from API errors at send time, consent denials, or orphan recovery — NOT from post-send carrier feedback.

#### S13 — Campaign recipient state machine is undefined → double-send risk on crash
- **Location:** Implicit — spec previously said "resumable on crash, status-driven, not step-counter" without defining states or transitions.
- **Problem:** Without an intermediate "sending" state, a worker crash after the CallRail API returns 200 but before updating `CampaignRecipient.delivery_status='sent'` causes a second send on restart. Customer gets two identical texts.
- **Fix (locked decision — see §10.5b):** Explicit state machine, see §14 below:
  ```
  pending → sending → sent
                    ↘ failed
             ↘ cancelled
  ```
  - Worker transitions `pending` → `sending` and records `sending_started_at` BEFORE calling the provider
  - On success, transitions `sending` → `sent` with `sent_at` timestamp
  - On provider error, transitions `sending` → `failed` with `error_message`
  - **Orphan recovery at worker startup:** query for rows in `sending` state where `sending_started_at < now() - 5 minutes` → transition to `failed` with `error_message='worker_interrupted'`. Operator can manually retry those via the Phase 5 UI.
  - **Provider-side idempotency:** if CallRail supports an idempotency key header, pass a deterministic UUID (e.g., `CampaignRecipient.id`) so re-tries after transient failure don't double-charge. Verify in the live smoke test.

#### S9 — `SMSService` and `CampaignService` only accept Customers, not Leads or ad-hoc phones
- **Location:**
  - `src/grins_platform/services/sms_service.py:73` — `send_message(customer_id: UUID, phone: str, ...)` signature has no `lead_id` parameter. Grep for `lead_id|Lead` in the service returns zero matches.
  - `src/grins_platform/services/campaign_service.py:468–529` — `_filter_recipients()` returns `list[Customer]`, only queries the Customer table. Leads cannot be an audience.
  - `src/grins_platform/services/campaign_service.py:568` — `_send_to_recipient(customer: Customer, ...)` only accepts a Customer.
- **Data model reality check:** `SentMessage` has BOTH `customer_id` and `lead_id` FK columns with a check constraint `customer_id IS NOT NULL OR lead_id IS NOT NULL`. `CampaignRecipient` likewise has both FKs. `SmsConsentRecord` is keyed by phone number (not customer_id), so it works uniformly for any recipient type. The model is ready; the services are not.
- **Consent field naming asymmetry:** `Customer.sms_opt_in` (bool) vs `Lead.sms_consent` (bool). Semantically identical, named differently. Must be unified at the service layer.
- **Business requirement:** A single campaign must be able to mix customers, leads, and ad-hoc phone numbers (e.g., from a CSV upload) with no artificial restrictions. The 300-customer scheduling outreach may be any mix of sources.
- **Fix — unified `Recipient` value object:** See §10.5a below.

### 10.5a Unified Recipient Model (new architectural decision)

The fix for S9 introduces a `Recipient` abstraction that all send paths flow through. This replaces the customer-only API of `SMSService.send_message()`.

**Design:**
```python
# src/grins_platform/services/sms/recipient.py
from dataclasses import dataclass
from typing import Literal
from uuid import UUID

SourceType = Literal["customer", "lead", "ad_hoc"]

@dataclass(frozen=True)
class Recipient:
    """Unified target for all SMS sends — customer, lead, or ad-hoc phone."""
    phone: str                          # E.164, always required
    source_type: SourceType
    customer_id: UUID | None = None     # set only if source_type == "customer"
    lead_id: UUID | None = None         # set for "lead" AND "ad_hoc" (ghost lead)
    first_name: str | None = None
    last_name: str | None = None

    @classmethod
    def from_customer(cls, customer) -> "Recipient": ...

    @classmethod
    def from_lead(cls, lead) -> "Recipient": ...

    @classmethod
    def from_adhoc(cls, phone: str, first_name: str | None = None, ...) -> "Recipient":
        """Creates a ghost Lead row then returns a Recipient bound to its lead_id."""
        ...
```

**`SMSService.send_message()` becomes recipient-based:**
```python
async def send_message(
    self,
    recipient: Recipient,
    message: str,
    message_type: MessageType,
    job_id: UUID | None = None,
    appointment_id: UUID | None = None,
) -> dict[str, Any]:
    # Consent check is phone-based — works for all source types
    has_consent = await self.check_sms_consent(recipient.phone)
    ...
    # Persist SentMessage with whichever FK applies
    await self.message_repo.create(
        customer_id=recipient.customer_id,
        lead_id=recipient.lead_id,
        recipient_phone=recipient.phone,
        message_type=message_type,
        ...
    )
    return await self.provider.send_text(recipient.phone, rendered_message)
```

**Ad-hoc CSV phones → ghost leads (chosen approach):**

For unmatched phones in a CSV upload, auto-create a `Lead` row with:
- `phone` (normalized to E.164)
- `name` (from CSV if present, else empty string)
- `lead_source = "campaign_import"`
- `status = "new"`
- `sms_consent = false` initially — the campaign send path still requires consent, so opted-out phones won't get texted. Consent can be granted separately via an opt-in flow later.
- `source_site = "campaign_csv_import"`

Benefits:
- Preserves `SentMessage` check constraint (`customer_id IS NOT NULL OR lead_id IS NOT NULL`) — zero schema migration
- Ad-hoc contacts automatically become trackable leads for future follow-up
- Consent tracking via `SmsConsentRecord` (phone-keyed) works out of the box
- Staff can filter them out of the main leads view with `lead_source=campaign_import` if they want a cleaner inbox
- Consistent with the platform's existing intake model — any externally-sourced contact is a Lead

Alternatives rejected:
- **Relaxing `SentMessage` check constraint** to allow fully orphaned messages → loses the audit invariant that every message traces to a CRM entity
- **New `campaign_contacts` table** → third contact type, creates join complexity, overkill for MVP

**`CampaignService._filter_recipients()` refactor:**
- Returns `list[Recipient]` (not `list[Customer]`)
- Interprets a new `target_audience` schema that supports pulling from multiple sources in one campaign:
  ```json
  {
    "customers": {
      "sms_opt_in": true,
      "ids_include": ["uuid1", "uuid2"],
      "cities": ["Edina", "Eden Prairie"],
      "last_service_between": ["2025-04-01", "2025-10-31"]
    },
    "leads": {
      "sms_consent": true,
      "ids_include": ["uuid3"],
      "statuses": ["new", "contacted", "qualified"],
      "lead_source": "website"
    },
    "ad_hoc": {
      "csv_upload_id": "upload-uuid"
    }
  }
  ```
- UNIONs the three sources, dedupes by phone (E.164 normalized), applies consent filter, returns unified `list[Recipient]`

**Consent field unification:**
- `Customer.sms_opt_in` and `Lead.sms_consent` stay as-is in the models (no migration)
- `_filter_recipients()` maps both to a single boolean when building `Recipient` objects
- Downstream code never sees the asymmetry

### 10.5b Locked Policy Decisions (2026-04-07)

After the critical review pass, the following eight policy decisions are locked with defaults. Each can be overridden later, but these are the assumptions Phase 1 code is written against.

| ID | Question | Decision | Location of detail |
|----|----------|----------|---------------------|
| **C1 / B4** | How do we prevent campaign dedupe collisions with the 24h message-type dedupe? | Add `campaign_id` parameter to `send_message()`; dedupe scope becomes `(recipient, campaign_id)` when set. Per-campaign per-recipient dedupe enforced additionally by `CampaignRecipient` state machine. | §10.2 B4 |
| **C3 / S10** | What's the consent gate for ad-hoc CSV phones? | Staff attestation model: uploader checks a box, backend auto-creates `SmsConsentRecord` rows with `consent_method='csv_upload_staff_attestation'`, `consent_given=true`, and the staff user ID. Permanent audit trail. | §10.3 S10 |
| **C4 / S11** | How does `consent_type` work? | Three types: `marketing` / `transactional` / `operational`. STOP = hard block for all future sends except `operational`. Marketing requires explicit opt-in (form, START keyword, or CSV attestation). Transactional allowed under EBR. | §10.3 S11 |
| **C5 / S12** | Do we support delivery status callbacks? | Ship the route + handler + env flag in Phase 1. Actual payload parsing is a stub until we verify what CallRail sends. If unsupported, `sent` stays terminal and UI labels accordingly. | §10.3 S12 |
| **C6** | Webhook URL + signing secret story | New `CALLRAIL_WEBHOOK_SECRET` env var. Manual dashboard paste per environment (ngrok for dev, staging URL, prod URL). Idempotency via Redis dedupe keyed on CallRail message ID, 24h TTL. | §12 |
| **C7** | Who can do what? | Admin/Manager/Technician tiers. Manager can send campaigns up to 50 recipients; 50+ requires Admin. Technician has read-only access to sent-message log. CSV upload is Admin-only. | §13 |
| **C8 / S13** | Recipient state machine + double-send protection | Explicit `pending → sending → sent/failed/cancelled` with `sending_started_at`. Orphan recovery after 5 min. Provider idempotency key = `CampaignRecipient.id` if CallRail supports it. | §10.3 S13, §14 |
| **H1** | Time window for out-of-state recipients | CT-only for MVP. UI shows a yellow warning on any recipient whose area code maps to a non-CT timezone. Per-recipient TZ enforcement deferred to Phase 7+. | §17 |

### 10.4 Minor gaps (nice-to-have, not blocking)

| ID | Gap | Decision |
|----|-----|----------|
| M1 | No `pydantic-settings` module; env vars read via raw `os.getenv()` scattered across services | Add typed `config/settings.py` as cleanup in Phase 7 — not required for MVP |
| M2 | No admin Settings UI to toggle provider at runtime | Skip for MVP. Env-var swap is fine. Revisit when runtime switching is actually needed |
| M3 | `SentMessage.twilio_sid` column is provider-specific | Rename to `provider_message_id` in a follow-up migration. Non-urgent |
| M4 | No CSV upload endpoint for audience | Required for Phase 4. New `POST /campaigns/audience/csv` |
| M5 | `Campaign.scheduled_at` field is ignored by send logic | Fixed automatically by Phase 3 background tick job |

### 10.5 What's actually ready (reusable as-is)

| Layer | Status | Notes |
|---|---|---|
| `SentMessage` data model | ✅ | All needed columns; rename `twilio_sid` later |
| `Campaign` + `CampaignRecipient` data models | ✅ | Ready as-is |
| `SmsConsentRecord` data model | ✅ | Just needs to actually be consulted on campaign sends (fix B2) |
| `SMSService` business logic (consent, time window, dedupe) | ✅ | Reusable once abstracted in S1 |
| STOP keyword + opt-out handling | ✅ | Works, just needs a CallRail payload adapter |
| Frontend: React Query + axios + 401 refresh | ✅ | `frontend/src/core/api/client.ts` — solid pattern |
| Frontend: shadcn/ui components + Dialog pattern | ✅ | Everything needed for the wizard modal |
| `CommunicationsQueue` + `SentMessagesLog` components | ✅ | Will light up automatically once backend writes rows |
| `GET /customers` search/filter endpoint | ⚠️ | Works for basic filters; needs SMS opt-in + location filters added |
| `GET /sent-messages` filters | ✅ | Already drives the sent log UI |
| Redis | ✅ | Already running → free infra for rate limiter + future ARQ queue |

### 10.6 Implementation order (supersedes §5)

This is the canonical build order. Each phase is independently shippable.

#### Phase 0 — Pre-flight (no code) ✅ COMPLETE
- [x] Verify 10DLC registration on CallRail account for `(952) 529-3750` — Brand confirmed via API (`brand_status: "registered_in_twilio"`); Campaign-level registration confirmed visually in CallRail Compliance Home dashboard (2026-04-07)
- [x] `GET /v3/a.json` with API key → captured `CALLRAIL_ACCOUNT_ID=ACC019c31a27df478178fe0f381d863bf7d`
- [x] `GET /v3/a/{id}/companies.json` → captured `CALLRAIL_COMPANY_ID=COM019c31a27f5b732b9d214e04eaa3061f`
- [x] `GET /v3/a/{id}/trackers.json` → verified tracker `TRK019c5f8c1c3279f98b678fb73d04887e` with `sms_supported=true`, `sms_enabled=true`
- [x] All values written to `.env` (gitignored, verified via `git check-ignore`)

**Phase 0 outcome:** All CallRail identifiers resolved and written to `.env`. Account brand is registered with The Campaign Registry via Twilio. The website number `+19525293750` is SMS-enabled on an active tracker. **Cleared to begin Phase 1.**

#### Phase 1 — Provider abstraction + CallRail client + Recipient unification + policy fixes (backend only)
**Package scaffolding:**
- [ ] Create `services/sms/` package: `base.py`, `callrail_provider.py`, `twilio_provider.py`, `null_provider.py`, `factory.py`, `recipient.py`, `ghost_lead.py`, `rate_limiter.py`, `templating.py`, **`consent.py`** (type-scoped consent module — see S11), **`state_machine.py`** (recipient state transitions — see S13)
- [ ] Port current Twilio stub into `twilio_provider.py` verbatim (no behavior change)
- [ ] Implement `callrail_provider.py` with `httpx.AsyncClient`, including `verify_webhook_signature()` using `CALLRAIL_WEBHOOK_SECRET`
- [ ] Add `SMS_PROVIDER` env var; default `callrail`
- [ ] Add `CALLRAIL_WEBHOOK_SECRET` env var + document expected format in `.env.example`
- [ ] Add `CALLRAIL_DELIVERY_WEBHOOK_ENABLED` env var (default `false`)

**Recipient abstraction (S9):**
- [ ] Introduce `Recipient` value object with `from_customer()`, `from_lead()`, `from_adhoc()` factories
- [ ] Implement `ghost_lead.create_or_get(phone, first_name, last_name)` helper — normalizes phone to E.164, dedupes by phone using a DB `SELECT ... FOR UPDATE` to avoid race conditions on concurrent uploads, creates Lead with `lead_source='campaign_import'`, `status='new'`, `sms_consent=false`
- [ ] Refactor `SMSService.send_message()` signature to `(recipient: Recipient, message, message_type, campaign_id=None, consent_type='transactional', job_id=None, appointment_id=None)`
- [ ] Refactor `SMSService` constructor to take provider injection; rename `_send_via_twilio` → `_send_via_provider`
- [ ] Update ALL existing callers of `SMSService.send_message()` to pass `Recipient.from_customer(...)` and the correct `consent_type`:
  - `api/v1/sms.py` send + send-bulk endpoints
  - Appointment reminder + confirmation + on-the-way + completion call sites → `consent_type='transactional'`
  - Invoice notification call sites → `consent_type='transactional'`
  - Campaign send path → `consent_type='marketing'` + `campaign_id` set
  - STOP confirmation send → `consent_type='operational'`
  - `notification_service.py` if it calls SMSService

**Consent policy (S10, S11):**
- [ ] Implement `services/sms/consent.py` with `check_sms_consent(phone, consent_type)` function matching the locked semantics in §10.5b / S11
- [ ] Replace `SMSService.check_sms_consent()` internal implementation to delegate to the new module
- [ ] Add unit tests for all consent scenarios: marketing-opted-in, marketing-opted-out, STOP-hard-block, transactional under EBR, operational always-allowed, ghost lead pre-attestation, ghost lead post-attestation
- [ ] Implement `SmsConsentRecord` bulk-insert helper for CSV attestation — creates one row per distinct E.164 phone in the upload batch with `consent_method='csv_upload_staff_attestation'`, stores the attesting `staff_id`, versioned attestation text, and timestamp
- [ ] Add a `consent_form_version` constant (`CSV_ATTESTATION_V1`) and the exact legal text baked into the module

**Dedupe fix (B4):**
- [ ] Add `campaign_id: UUID | None = None` parameter to `send_message()`
- [ ] Refactor the 24-hour dedupe query: when `campaign_id` is set, scope the check to `(customer_id OR lead_id, campaign_id)` and the `CampaignRecipient` row state; when not set, keep the current `(customer_id, message_type)` behavior
- [ ] Unit test: send two different campaigns to the same customer within 24h → both succeed; send the same campaign twice → second blocked

**State machine + orphan recovery (S13):**
- [ ] Define `RecipientState` enum: `pending | sending | sent | failed | cancelled`
- [ ] Implement `services/sms/state_machine.py` with `transition(recipient, from_state, to_state)` that validates allowed transitions
- [ ] Add `sending_started_at` timestamp to `CampaignRecipient` (migration) — OR reuse an existing timestamp if one fits semantically (verify during implementation)
- [ ] Orphan recovery query on worker startup: find `sending` rows where `sending_started_at < now() - interval '5 minutes'` → transition to `failed` with `error_message='worker_interrupted'`
- [ ] Pass `CampaignRecipient.id` as idempotency key in CallRail API calls IF CallRail supports the header (verified in smoke test)

**Blocker fixes (B1, B2, B3 preparation):**
- [ ] Fix B1 — DI helper in `api/dependencies.py` → `get_campaign_service()` that wires `SMSService` + `EmailService` into `CampaignService`
- [ ] Fix B2 — remove consent bypass in campaign loop; all sends flow through `check_sms_consent(phone, 'marketing')`
- [ ] Refactor `CampaignService._send_to_recipient()` to accept `Recipient` instead of `Customer`; populate `CampaignRecipient.customer_id` OR `lead_id` based on `recipient.source_type`; pass `campaign_id` into `send_message()`

**Rate limiter (S2):**
- [ ] Implement `services/sms/rate_limiter.py` — Redis-backed sliding window
- [ ] Two simultaneous windows: 150/hour + 1,000/day, keyed by `(provider_name, account_id)`
- [ ] Redis key format: `sms:rl:{provider}:{account_id}:hour:{YYYYMMDDHH}` and `...:day:{YYYYMMDD}` with TTL matching the window
- [ ] `acquire()` returns `(allowed: bool, retry_after_seconds: int)`
- [ ] Fallback behavior when Redis is down: **hard fail** (deny the send, log error, increment a metric). Acceptable because Redis is already critical infra for middleware rate-limiting.

**Webhook routes (S4):**
- [ ] Add `POST /webhooks/callrail/inbound` route with signature verification + idempotency dedupe on CallRail conversation ID + message timestamp (Redis set, 24h TTL — since CallRail doesn't emit per-message IDs, we dedupe on `(conversation_id, created_at)`)
- [ ] Must be idempotent (same payload replayed = no duplicate side effects)
- [ ] ~~`POST /webhooks/callrail/delivery-status` route~~ — REMOVED: confirmed 2026-04-07 that CallRail does not expose delivery status callbacks. See §10.3 S12.

**Permission enforcement (C7 / §13):**
- [ ] Create route dependencies in `api/dependencies.py`: `require_admin()`, `require_admin_or_manager()`, `require_authenticated()` — if not already present
- [ ] Apply permission dependencies to every new/edited endpoint per the matrix in §13

**Database migrations (Phase 1):**
- [ ] Alembic migration: add `sending_started_at` timestamp column to `campaign_recipients` (nullable, indexed)
- [ ] Alembic migration: add `created_by_staff_id` UUID column to `sms_consent_records` (nullable, FK to staff, indexed) — required for S10 CSV attestation audit trail per §17.2
- [ ] Alembic migration: add `campaign_id` UUID column to `sent_messages` (nullable, FK to campaigns, indexed) if not already present — required for B4 dedupe scoping
- [ ] Alembic migration: add `provider_conversation_id` (VARCHAR 50) and `provider_thread_id` (VARCHAR 50) columns to `sent_messages` — required because CallRail returns a conversation + sms_thread identifier pair, not a per-message ID (verified 2026-04-07). These columns let us cross-reference to CallRail for support escalation and potential future delivery lookups. Both nullable so Twilio provider (which returns `twilio_sid`) is unaffected.

**Audit log wiring (per §17.5):**
- [ ] Emit `sms.provider.switched` audit event when the factory resolves a different provider at boot
- [ ] Emit `sms.campaign.created` on campaign creation
- [ ] Emit `sms.campaign.sent_initiated` on send initiation
- [ ] Emit `sms.campaign.cancelled` on cancellation
- [ ] Emit `sms.csv_attestation.submitted` on CSV upload confirmation
- [ ] Emit `sms.consent.hard_stop_received` when a STOP inbound webhook creates a consent record
- [ ] Wire to existing `audit_log.py` model; reuse existing audit repository

**Structured logging (per §15.1):**
- [ ] Emit `sms.send.requested`, `sms.send.succeeded`, `sms.send.failed` events with masked phone field (`+1XXX***XXXX`)
- [ ] Emit `sms.rate_limit.acquired` and `sms.rate_limit.denied` events
- [ ] Emit `sms.consent.denied` on consent-blocked sends
- [ ] Emit `sms.webhook.inbound` and `sms.webhook.signature_invalid` events
- [ ] Implement `_mask_phone(phone)` helper (last 4 digits only)

**Manual external setup (per §12.2) — must be done by Admin in CallRail dashboard:**
- [ ] Paste inbound webhook URL into CallRail dashboard (per environment: dev ngrok, staging, prod)
- [ ] Paste delivery status webhook URL (per environment)
- [ ] Paste `CALLRAIL_WEBHOOK_SECRET` into CallRail dashboard signing config
- [ ] Document the procedure in `deployment-instructions/callrail-webhook-setup.md` (new doc)
- [ ] Add a runbook entry for domain migration: what to update in CallRail if hostname changes

**Tests:**
- [ ] Unit tests per provider (CallRail, Twilio, Null) — happy path, auth error, rate-limit error, signature verification (valid + invalid)
- [ ] Unit tests: `Recipient` factories, ghost-lead creation (concurrent race with row-level lock), consent type-scoped checks (all 4 scenarios in §17.1), state machine transitions (valid + forbidden), segment counter (GSM-7 / UCS-2 / boundaries), phone normalizer edge cases
- [ ] Unit test: dedupe fix (B4) — same campaign can't double-send, different campaigns can, retry flow works
- [ ] Integration test: `CampaignService` sending to mixed audience (1 customer + 1 lead + 1 ad-hoc) — verify 3 `SentMessage` rows with correct FKs + `campaign_id`, 1 new ghost Lead, 1 bulk-inserted `SmsConsentRecord` for the ad-hoc phone with `consent_method='csv_upload_staff_attestation'` and `created_by_staff_id` set, `CampaignRecipient` state machine transitions correctly end-to-end
- [ ] Integration test: orphan recovery — set a `CampaignRecipient` to `sending` with old `sending_started_at`, run worker startup hook, verify transition to `failed` with `worker_interrupted` reason
- [ ] Integration test: rate limiter under load — fire 200 sends in a loop, verify exactly 150 succeed in the first hour window, rest deferred via `scheduled_for`
- [ ] Integration test: STOP reply webhook → `handle_inbound()` → `SmsConsentRecord` with `consent_given=false` → subsequent send to same phone (any `consent_type` except operational) denied
- [ ] Integration test: delivery status webhook → `SentMessage.delivery_status` transitions `sent` → `delivered`
- [ ] Integration test: webhook idempotency — POST same inbound payload twice → only one side effect
- [ ] Integration test: permission enforcement — Technician POST `/campaigns` → 403; Manager POST send for 51 recipients → 403; Admin succeeds on both

#### Phase 2 — Unblock 300-customer blast (interim script)
- [ ] `scripts/send_callrail_campaign.py` — CSV + template + throttled loop + dry-run mode
- [ ] Dry-run → owner review → live run with `--confirm`
- [ ] Monitor via existing `SentMessagesLog` component

#### Phase 3 — Background job for throttled campaign sends
- [ ] Add `process_pending_campaign_recipients` APScheduler interval job (60s tick)
- [ ] Worker respects rate limiter + 8AM–9PM CT time window
- [ ] Worker uses `FOR UPDATE SKIP LOCKED` when claiming recipients (prevents double-claim with concurrent workers, per §18.4)
- [ ] Worker transitions `pending → sending → sent/failed` via state machine helpers
- [ ] Worker emits `campaign.worker.tick` log events with `recipients_processed` + `tick_duration_ms`
- [ ] Worker records `last_tick_at` in Redis (key: `sms:worker:last_tick`) with 5 min TTL so the health endpoint can detect staleness
- [ ] Worker runs orphan recovery query on each tick before claiming new work
- [ ] Honors `Campaign.scheduled_at` for future sends (fixes M5)
- [ ] Refactor `POST /sms/send-bulk` to enqueue instead of loop (fixes B3)
- [ ] Refactor `POST /campaigns/{id}/send` to enqueue instead of blocking — returns 202 with campaign_id
- [ ] Add `GET /campaigns/worker-health` endpoint returning the JSON shape in §15.3
- [ ] Derived `Campaign.status` query helper (sent vs partial_failed based on aggregate recipient states, per §14.2)
- [ ] Integration test: 200 synthetic recipients, verify throttle stays under 150/hr
- [ ] Integration test: campaign cancelled mid-send → remaining `pending` transition to `cancelled`, `sending` finish naturally
- [ ] Integration test: two workers running concurrently (simulated) → no double-send on any recipient

#### Phase 4 — Audience filter extensions (multi-source)
- [ ] Refactor `_filter_recipients()` to return `list[Recipient]` from a UNION of Customer + Lead + ad-hoc sources
- [ ] Define new `target_audience` JSON schema with three top-level keys: `customers`, `leads`, `ad_hoc` (see §10.5a)
- [ ] Schema-validate `target_audience` in `CampaignCreate` via Pydantic
- [ ] **Customer filters:** `sms_opt_in`, `ids_include`, `cities`, `last_service_between`, `tags_include`, `lead_source`, `is_active`, `no_appointment_in_days`
- [ ] **Lead filters:** `sms_consent`, `ids_include`, `statuses` (new/contacted/qualified), `lead_source`, `intake_tag`, `action_tags_include`, `cities`, `created_between`
- [ ] **Ad-hoc source:** `csv_upload_id` pointing to a staged upload; resolver creates ghost leads on the fly
- [ ] Dedupe by E.164 phone across all three sources (if a phone appears as both a customer and a lead, customer wins)
- [ ] Add `POST /campaigns/audience/preview` → accepts a `target_audience` dict, returns total count, per-source breakdown, and first 20 matches with name/phone/source
- [ ] Add `POST /campaigns/audience/csv` → uploads CSV, stages it, returns upload_id + matched/unmatched/duplicate breakdown (doesn't create ghost leads yet — only happens on final send)

#### Phase 5 — Communications tab full UI
- [ ] Add primary "New Text Campaign" button to `Communications.tsx`
- [ ] `NewTextCampaignModal` — 3-step wizard using shadcn Dialog + react-hook-form + zod
- [ ] **Step 1** `AudienceBuilder.tsx` — **mixed-source recipient picker:**
  - **Three additive source panels, any or all can be used in one campaign:**
    1. **Customers panel** — search + filter (SMS opt-in default on, city, last service date range, tags, lead source) + multi-select table with checkboxes. Shows selected count.
    2. **Leads panel** — search + filter (SMS consent default on, status new/contacted/qualified, lead source, intake tag, city, created date) + multi-select table. Shows selected count.
    3. **Ad-hoc panel** — CSV upload (columns: `phone`, `first_name`, `last_name`) OR paste phones directly. Shows matched-to-customer / matched-to-lead / new (will become ghost lead) breakdown.
  - Running total at top: "X customers + Y leads + Z ad-hoc = N total recipients (M after consent filter)"
  - Pass-through for `ids_include` when opened from Customers tab OR Leads tab (opens the correct panel pre-populated)
  - Dedupe warning if a phone appears in multiple sources ("3 phones are in both your Customers selection and your CSV — they'll only be texted once")
  - Live preview count via `POST /campaigns/audience/preview`
- [ ] **Step 2** `MessageComposer.tsx`:
  - Template textarea with merge-field insertion buttons ({first_name}, {last_name})
  - **Dual character counter:** GSM-7 mode (160/153 per segment) with automatic switch to UCS-2 mode (70/67 per segment) if any non-GSM char (including emoji) is detected
  - Segment count badge with warning color above 1 segment ("This message will send as 2 SMS segments per recipient — cost doubles")
  - Merge-field linter: flag any `{field}` not in the allowed list (`first_name`, `last_name`, `next_appointment_date`)
  - **Live preview panel using REAL data** — pulls the first 3 recipients from the current audience (via `useAudiencePreview`) and renders the message for each so staff see actual merge output including the auto-appended STOP footer + "Grins Irrigation:" prefix
  - Warning banner if any merge field is empty for any previewed recipient ("3 recipients have no first_name — their message will say 'Hi ,'")
  - 2026-04-07 decision: sender prefix is literally `"Grins Irrigation: "` (no apostrophe, with trailing space) — locked until product says otherwise
- [ ] **Step 3** `CampaignReview.tsx`:
  - **Per-source breakdown:** "X customers + Y leads + Z ad-hoc = N total"
  - **Consent filter breakdown:** "N total → M will send after consent filter (K blocked)"
  - **Time-zone warning** (H1): "P recipients have non-Central area codes. They will still be texted during the 8 AM–9 PM CT window. Per-recipient timezone enforcement is not yet supported."
  - Estimated completion time (recipients ÷ 140/hr), accounting for time-window gaps (if the send would cross 9 PM CT, show "will pause overnight and resume at 8 AM CT")
  - Send now (respects time window) OR schedule for specific date/time — timezone shown is CT, with a note "All send times are in Central Time"
  - **Send confirmation friction (H4):** for audiences ≥50 recipients, require typed confirmation. Modal shows "You are about to send SMS to N people. Type **SEND N** below to confirm." Submit button stays disabled until the typed string matches exactly. Under 50 recipients, just a standard confirm dialog.
  - Final confirm button is destructive-styled (red) to match the blast radius
- [ ] **CSV upload behaviors in the Ad-hoc panel (H6, S10):**
  - Max file size: 2 MB, max 5,000 rows
  - Accepted encodings: UTF-8, UTF-8-BOM, Latin-1, Windows-1252 (auto-detect)
  - Required columns: `phone` (mandatory), `first_name` (optional), `last_name` (optional) — column headers are case-insensitive, order-independent, matched by label not position
  - Phone normalization: strip all non-digits, prefix `+1` if 10 digits, otherwise reject row
  - Skip + report malformed rows rather than failing the whole upload; show inline "3 rows skipped: see details" with expandable error list
  - Duplicate phones within the same file: collapse to first occurrence, show count
  - Staged upload returns `upload_id` + preview breakdown: matched-to-customer / matched-to-lead / will-become-ghost-lead / rejected
  - **Staff attestation checkbox** (S10): "I confirm that every contact in this file has an established business relationship with Grins Irrigation and has consented to receive SMS from us. I understand this attestation is logged and auditable." — submit button on the CSV upload step is disabled until checked. Attestation text + staff user ID + timestamp are saved when the upload is confirmed.
- [ ] **Draft persistence (H5):** wizard state auto-saves to localStorage on every field change + every panel change. Key: `comms:draft_campaign:{staff_id}`. On modal re-open, prompt "You have an unsaved draft from 2h ago — continue or start over?". Draft also saved to backend as `Campaign` row with `status='draft'` on first "Next" click so it survives cache clears.
- [ ] **Failed recipients view (H3):** Add a "Failed" filter + badge to the CampaignsList tab. Clicking a failed campaign shows a detail view with: per-recipient failure reason, bulk "Retry selected" button (creates a new `CampaignRecipient` set tied to the same campaign), individual "mark as do not retry" option, cancel-in-progress button (transitions remaining `pending` to `cancelled`).
- [ ] Hooks: `useCreateCampaign`, `useSendCampaign`, `useAudiencePreview`, `useAudienceCsv`, `useCampaignProgress`, `useCampaignFailures`, `useRetryFailedRecipients`, `useCancelCampaign`, `useDraftCampaign`, `useWorkerHealth`
- [ ] Add third tab to `CommunicationsDashboard`: "Campaigns" showing active/scheduled/completed list with live progress bars (polling via `useCampaignProgress`)
- [ ] Worker health indicator in the Campaigns tab header: green dot if the interval job ticked within the last 2 minutes, red if not — backed by a lightweight `GET /campaigns/worker-health` endpoint
- [ ] Frontend port of `segment_counter` logic — reuse the same GSM-7 vs UCS-2 detection rules as the backend so composer and backend agree
- [ ] Frontend port of area-code → timezone lookup for the Review step warning (H1)

**Phase 5 tests:**
- [ ] Component test: `MessageComposer` segment counter — GSM-7 boundaries, UCS-2 switch on emoji, merge-field linter
- [ ] Component test: `AudienceBuilder` — multi-source selection, dedupe warning, CSV upload happy + error cases
- [ ] Component test: `CampaignReview` — typed confirmation friction ≥50 recipients, TZ warning, schedule-in-past rejection
- [ ] Component test: draft persistence — localStorage round-trip, DB draft survival across cache clear
- [ ] E2E (Playwright) wizard flow: open modal from Communications tab → build mixed audience → compose → review → send → verify `SentMessagesLog` populates
- [ ] E2E from Customers tab: multi-select rows → "Text Selected" → modal opens with customers panel pre-populated → send
- [ ] E2E from Leads tab: same flow for leads
- [ ] E2E CSV upload: staff attestation checkbox → upload 20-row fixture → verify ghost leads + `SmsConsentRecord` rows created on send

#### Phase 6 — Customers tab AND Leads tab entry points
- [ ] Add checkbox column + bulk-action bar to `CustomerList.tsx` via TanStack Table row-selection
- [ ] "Text Selected" button opens `NewTextCampaignModal` with selected customer IDs pre-loaded into the Customers panel
- [ ] Add checkbox column + bulk-action bar to the Leads list (`frontend/src/features/leads/` — likely `LeadsList.tsx` or similar)
- [ ] "Text Selected" on the Leads tab opens `NewTextCampaignModal` with selected lead IDs pre-loaded into the Leads panel
- [ ] Both entry points open the same modal; the modal just pre-selects the right panel

#### Phase 7 — Polish & Twilio swap readiness
- [ ] Migration: rename `sent_messages.twilio_sid` → `provider_message_id`
- [ ] `BusinessSetting` key `sms_provider` + admin Settings UI toggle
- [ ] Introduce `pydantic-settings` for typed config in `config/settings.py`
- [ ] E2E test: build audience → send → verify drip → verify `SentMessagesLog` populates
- [ ] Document the `SMS_PROVIDER=twilio` swap procedure in `README.md`

### 10.9 Phase 0.5 Live API Verification (2026-04-07)

Performed live smoke test against production CallRail API using the Grins account. **Test succeeded — real SMS delivered to owner's phone.** Findings below are the canonical contract Phase 1 code must match.

#### Verified endpoint

```
POST https://api.callrail.com/v3/a/ACC019c31a27df478178fe0f381d863bf7d/text-messages.json
```

**Required headers:**
```
Authorization: Token token="<api_key>"
Content-Type: application/json
```

**Request body (exact field names confirmed):**
```json
{
  "company_id": "COM019c31a27f5b732b9d214e04eaa3061f",
  "tracking_number": "+19525293750",
  "customer_phone_number": "+19527373312",
  "content": "Grins Irrigation: ... Reply STOP to opt out."
}
```

- `tracking_number` is an E.164 phone number, **NOT** a tracker ID
- `customer_phone_number` is E.164
- `content` accepts plain text up to a segment-length cap (not yet tested for ceiling — recommend staying under 1600 chars)

**Response:** HTTP **200** (not 201). Body is the entire conversation object:

```json
{
  "id": "k8mc8",
  "initial_tracker_id": "TRK...",
  "current_tracker_id": "TRK...",
  "customer_name": "DMITRI RAKITIN",
  "customer_phone_number": "+19527373312",
  "initial_tracking_number": "+19525293750",
  "current_tracking_number": "+19525293750",
  "last_message_at": "2026-04-07T22:25:04.953-04:00",
  "state": "active",
  "formatted_customer_phone_number": "952-737-3312",
  "formatted_initial_tracking_number": "952-529-3750",
  "formatted_current_tracking_number": "952-529-3750",
  "formatted_customer_name": "Dmitri Rakitin",
  "company_time_zone": "America/Indiana/Knox",
  "tracker_name": "Website",
  "company_name": "Grin's Irrigation & Landscaping",
  "company_id": "COM019c31a27f5b732b9d214e04eaa3061f",
  "recent_messages": [
    {
      "direction": "outgoing",
      "content": "...",
      "created_at": "2026-04-07T22:25:04.953-04:00",
      "sms_thread": {
        "id": "SMT019d69f77fb472829bfb403cc4104584",
        "notes": null,
        "tags": [],
        "value": null,
        "lead_qualification": null
      },
      "type": "sms",
      "media_urls": []
    }
  ]
}
```

#### Critical findings

**1. No per-message ID.** The response has a conversation-level `id` (short, e.g. `"k8mc8"`) and a thread-level `sms_thread.id` (e.g., `"SMT019d..."`), but **no unique per-message ID**. Our newly-sent message sits in `recent_messages[]` identified only by `created_at` timestamp + `direction='outgoing'`.

**Implications:**
- `SentMessage` must store BOTH `provider_conversation_id` (the `"k8mc8"` value) AND `provider_thread_id` (the `"SMT..."` value) — see Phase 1 migrations
- There is no way to look up "this specific message" from CallRail later via a stable ID
- For support escalation, we pair `(provider_conversation_id, created_at, x-request-id)` as the tuple uniquely identifying a send

**2. Rate limit state in response headers (huge simplification).** Every response includes:
```
x-rate-limit-hourly-allowed: 150
x-rate-limit-hourly-used: 1
x-rate-limit-daily-allowed: 1000
x-rate-limit-daily-used: 1
```
CallRail is the source of truth. See §12.4 for the simplified tracker design. This removes the need for S2's original Redis sliding-window counter.

**3. No delivery status mechanism.** Response body has no `status`, `delivery_status`, or `callback_url` field. No mention of delivery webhooks anywhere. **`sent` is the terminal happy state.** See S12 resolution in §10.3.

**4. Idempotency-Key header: inconclusive.** Sent `Idempotency-Key: E420A53C-...`. CallRail did not echo it back in any response header. We don't know if they honored, ignored, or parse under a different name. **Recommendation:** do NOT rely on client-side idempotency keys. Use the state machine (§14) + orphan recovery as the sole double-send prevention mechanism.

**5. Performance.** Observed round-trip `606ms`, server-side processing `275ms`. Healthy for real-time sends. Rate of ~140/hr is well within the server's capacity — the ceiling is policy, not latency.

**6. Webhook signature mechanism: NOT YET VERIFIED.** We have not yet received an inbound webhook from CallRail, so we have not verified the signature header format or HMAC algorithm. `CallRailProvider.verify_webhook_signature()` needs to be written against CallRail's documented webhook format; recommend verifying with a real inbound STOP reply during Phase 1 smoke testing.

**7. Other useful response headers:**
- `x-request-id: 9871dfb3-c9f3-419a-a181-364cdf6309b1` → log this on every send for CallRail support escalation
- `x-runtime: 0.275445` → CallRail-side processing time
- `set-cookie: _call_rpt_session=...` → ignore, not useful for API clients
- `etag` present → caching supported on read endpoints (not useful for POSTs)

#### What Phase 0.5 changes in the spec

| Area | Before | After |
|---|---|---|
| S2 rate limiter | Redis sliding window | Read CallRail headers (§12.4) |
| S12 delivery receipts | Stub handler in Phase 1 | Removed entirely; `sent` is terminal |
| New files | `rate_limiter.py` | `rate_limit_tracker.py` |
| `SentMessage` schema | `provider_message_id` column | `provider_conversation_id` + `provider_thread_id` columns |
| State machine | `sent → delivered` transition | Removed; `sent` is terminal |
| UI labels | "Sent" / "Delivered" | "Sent" only; no "Delivered" bucket |
| Env vars | `CALLRAIL_DELIVERY_WEBHOOK_ENABLED`, `SMS_RATE_LIMIT_HOURLY`, `SMS_RATE_LIMIT_DAILY` | Removed (CallRail dictates) |
| Webhook routes | `/inbound` + `/delivery-status` | `/inbound` only |

**Net effect:** Phase 1 scope is smaller, not larger, thanks to the live verification. Two modules removed, one env var group removed, one state transition removed, one webhook route removed.

### 10.7 Twilio swap procedure (post-Phase 1)

Once the provider abstraction lands in Phase 1, switching from CallRail to Twilio is a zero-code operation:

1. Verify Twilio 10DLC registration is live
2. In `.env`:
   - Set `SMS_PROVIDER=twilio`
   - Set `TWILIO_ACCOUNT_SID=...`, `TWILIO_AUTH_TOKEN=...`, `TWILIO_PHONE_NUMBER=...`
   - Leave `CALLRAIL_*` vars in place as fallback
3. Update Twilio's inbound webhook URL in the Twilio console → `https://<host>/api/v1/webhooks/twilio-inbound`
4. Restart the backend. `get_sms_provider()` now returns `TwilioProvider` on boot.
5. Smoke test: send one text, reply STOP, verify `SmsConsentRecord` created.
6. Rate-limiter key automatically namespaces by `provider_name`, so CallRail's counters don't leak into Twilio's window.

No changes to `SMSService`, `CampaignService`, `Communications` UI, or any business logic. That's the whole point of S1.

### 10.8 Severity matrix (quick reference)

| ID | Severity | Blocks 300-recipient blast? | Blocks UI? | Blocks Twilio swap? |
|----|----------|:-:|:-:|:-:|
| B1 | Critical | ✅ | ✅ | — |
| B2 | Critical (compliance) | ✅ | ✅ | — |
| B3 | Critical | ✅ | ✅ | — |
| **B4** | **Critical (silent data loss)** | **✅** | **✅** | — |
| S1 | High | — | — | ✅ |
| S2 | **Low** (simplified via CallRail headers 2026-04-07) | — | — | — |
| S3 | High | ✅ | ✅ | — |
| S4 | High (compliance) | ✅ | ✅ | — |
| S5 | Medium | — | ✅ | — |
| S6 | Medium | — | ✅ | — |
| S7 | Low | — | partial | — |
| S8 | High | — | ✅ | — |
| S9 | Critical | ✅ | ✅ | — |
| S10 | Critical (TCPA) | ✅ (if any ad-hoc) | ✅ | — |
| S11 | High (compliance nuance) | — | ✅ | — |
| S12 | **Resolved** — CallRail has no delivery callbacks, `sent` is terminal (2026-04-07) | — | — | — |
| S13 | Critical (double-send risk) | ✅ | ✅ | — |
| M1–M5 | Low | — | — | — |

**Scope clarification (2026-04-07):** The 300-recipient scheduling outreach may be any mix of customers, leads, or ad-hoc phone numbers. One campaign must support all three sources simultaneously. No artificial restrictions.

**Minimum to unblock 300-recipient blast:** B1, B2, B3, B4, S1 (simplified), S3 (MVP tick job), S4, S9, S10 (if any ad-hoc), S13
**Minimum to ship full Communications UI:** everything above + S5, S6, S8, S11
**Minimum for Twilio swap:** just S1 (provider abstraction)
**Minimum for regulatory defense on audit:** B4, S10, S11, plus §17 Compliance Details enforcement

---

## 11. Key File References

**Existing (touch or reuse):**
- `src/grins_platform/services/sms_service.py` (line 228 `_send_via_twilio` stub)
- `src/grins_platform/services/campaign_service.py`
- `src/grins_platform/services/background_jobs.py`
- `src/grins_platform/models/sent_message.py`
- `src/grins_platform/models/campaign.py`
- `src/grins_platform/models/sms_consent_record.py`
- `src/grins_platform/api/v1/sms.py`
- `src/grins_platform/api/v1/campaigns.py`
- `src/grins_platform/api/v1/webhooks.py`
- `src/grins_platform/api/v1/communications.py`
- `frontend/src/pages/Communications.tsx`
- `frontend/src/pages/Customers.tsx`
- `frontend/src/features/communications/components/CommunicationsDashboard.tsx`
- `frontend/src/features/communications/components/CommunicationsQueue.tsx`
- `frontend/src/features/communications/components/SentMessagesLog.tsx`
- `frontend/src/features/marketing/components/CampaignManager.tsx`

**New (to create):**

Backend — provider abstraction package:
- `src/grins_platform/services/sms/__init__.py`
- `src/grins_platform/services/sms/base.py` — `BaseSMSProvider` Protocol + `ProviderSendResult`, `InboundSMS` dataclasses
- `src/grins_platform/services/sms/callrail_provider.py` — `CallRailProvider` (httpx client + webhook parser)
- `src/grins_platform/services/sms/twilio_provider.py` — `TwilioProvider` (ports current stub)
- `src/grins_platform/services/sms/null_provider.py` — `NullProvider` (tests / dry-run)
- `src/grins_platform/services/sms/factory.py` — `get_sms_provider()` reads `SMS_PROVIDER` env
- `src/grins_platform/services/sms/rate_limit_tracker.py` — Reads CallRail's `x-rate-limit-*` response headers, caches `(hourly_remaining, daily_remaining, fetched_at)` in Redis for cross-worker visibility. Refuses new sends when `hourly_remaining <= 5`. (Simplified from the original Redis sliding-window counter after Phase 0.5 confirmed CallRail returns authoritative rate-limit headers on every response.)
- `src/grins_platform/services/sms/templating.py` — `render_template(body, context)` merge-field util
- **`src/grins_platform/services/sms/recipient.py`** — `Recipient` dataclass + `from_customer()`, `from_lead()`, `from_adhoc()` factories
- **`src/grins_platform/services/sms/ghost_lead.py`** — `create_or_get(phone, first_name, last_name)` helper that normalizes phone to E.164, dedupes by phone (row-level lock), creates `Lead` with `lead_source='campaign_import'`
- **`src/grins_platform/services/sms/consent.py`** — `check_sms_consent(phone, consent_type)` with type-scoped semantics (see S11), bulk-insert helper for CSV attestation
- **`src/grins_platform/services/sms/state_machine.py`** — `RecipientState` enum + `transition()` validator + orphan recovery query
- **`src/grins_platform/services/sms/segment_counter.py`** — GSM-7 vs UCS-2 detection, segment count calculator (mirrored in frontend for composer)
- **`src/grins_platform/services/sms/phone_normalizer.py`** — E.164 normalizer with bogus-phone rejection (000-..., 555-0100, etc.), area-code-to-timezone lookup used by the UI warning (H1)

Backend — other:
- `src/grins_platform/api/dependencies.py` — `get_campaign_service()` DI helper (fixes B1), `require_admin()`, `require_admin_or_manager()` permission dependencies
- New route in `src/grins_platform/api/v1/webhooks.py`:
  - `POST /webhooks/callrail/inbound` (STOP + inbound replies)
- New endpoints in `src/grins_platform/api/v1/campaigns.py`:
  - `POST /campaigns/audience/preview`
  - `POST /campaigns/audience/csv` (with staff attestation in the request body)
  - `POST /campaigns/{id}/cancel`
  - `POST /campaigns/{id}/retry-failed`
  - `GET /campaigns/worker-health` (for the green/red dot in the UI)
- `scripts/send_callrail_campaign.py` — one-off CSV blaster with dry-run mode

Frontend — Communications wizard:
- `frontend/src/features/communications/components/NewTextCampaignModal.tsx`
- `frontend/src/features/communications/components/AudienceBuilder.tsx`
- `frontend/src/features/communications/components/MessageComposer.tsx`
- `frontend/src/features/communications/components/CampaignReview.tsx`
- `frontend/src/features/communications/components/CampaignsList.tsx` (third tab in dashboard)
- `frontend/src/features/communications/hooks/useCreateCampaign.ts`
- `frontend/src/features/communications/hooks/useSendCampaign.ts`
- `frontend/src/features/communications/hooks/useAudiencePreview.ts`
- `frontend/src/features/communications/hooks/useAudienceCsv.ts`
- `frontend/src/features/communications/hooks/useCampaignProgress.ts`
- `frontend/src/features/communications/api/campaignsApi.ts`
- `frontend/src/features/communications/types/campaign.ts`

Frontend — Customers tab entry point (Phase 6):
- Edit `frontend/src/features/customers/components/CustomerList.tsx` to add checkbox column + bulk-action bar

Configuration:
- Edit `.env.example` to add `SMS_PROVIDER=`, `CALLRAIL_*` (including `CALLRAIL_WEBHOOK_SECRET` and `CALLRAIL_DELIVERY_WEBHOOK_ENABLED`), `TWILIO_*` placeholders
- New `src/grins_platform/config/settings.py` (Phase 7 cleanup) with `pydantic-settings`

---

## 12. External Configuration & Deployment

This section covers everything that lives OUTSIDE the codebase but is required for SMS to actually flow. Missing any of these is a silent failure — the code will appear to work in dev but nothing reaches phones in prod.

### 12.1 Environment variables (full list)

All variables live in `.env` (gitignored) for local dev and in the platform secret store for staging/prod. Populate real values per environment; never commit.

| Variable | Purpose | Required | Default |
|---|---|:-:|---|
| `SMS_PROVIDER` | Which provider to route sends through: `callrail` \| `twilio` \| `null` | ✅ | `callrail` |
| `CALLRAIL_API_KEY` | CallRail REST API token | ✅ (if provider=callrail) | — |
| `CALLRAIL_ACCOUNT_ID` | Account-scope identifier | ✅ | — |
| `CALLRAIL_COMPANY_ID` | Company-scope identifier | ✅ | — |
| `CALLRAIL_TRACKING_NUMBER` | Sender number in E.164 | ✅ | — |
| `CALLRAIL_TRACKER_ID` | Tracker identifier (for idempotency + logs) | ⚠️ recommended | — |
| `CALLRAIL_WEBHOOK_SECRET` | HMAC secret for verifying inbound webhooks | ✅ | — |
| ~~`CALLRAIL_DELIVERY_WEBHOOK_ENABLED`~~ | **REMOVED** — CallRail has no delivery callbacks (confirmed 2026-04-07) | — | — |
| `TWILIO_ACCOUNT_SID` / `TWILIO_AUTH_TOKEN` / `TWILIO_PHONE_NUMBER` | Twilio equivalents | optional | — |
| ~~`SMS_RATE_LIMIT_HOURLY` / `SMS_RATE_LIMIT_DAILY`~~ | **REMOVED** — CallRail dictates via response headers (confirmed 2026-04-07) | — | — |
| `SMS_SENDER_PREFIX` | Literal prefix prepended to every outbound message | optional | `"Grins Irrigation: "` |
| `SMS_TIME_WINDOW_TIMEZONE` | IANA TZ for the send window (H1) | optional | `America/Chicago` |
| `SMS_TIME_WINDOW_START` | Start hour (0–23) | optional | `8` |
| `SMS_TIME_WINDOW_END` | End hour (0–23) | optional | `21` |

### 12.2 CallRail dashboard configuration (manual, per environment)

Someone (typically Admin) must log into CallRail and point inbound webhooks at our platform. This is NOT automated and must be done once per environment plus whenever the hostname changes.

**Path:** CallRail → Account Settings → Integrations → Webhooks (exact location may vary; search "webhook" in-app)

**URLs to configure (per environment):**

| Environment | Inbound SMS webhook | Delivery status webhook |
|---|---|---|
| Local dev | `https://<ngrok-subdomain>.ngrok.io/api/v1/webhooks/callrail/inbound` | `...delivery-status` |
| Staging | `https://staging.grinsirrigation.com/api/v1/webhooks/callrail/inbound` | `...delivery-status` |
| Production | `https://app.grinsirrigation.com/api/v1/webhooks/callrail/inbound` | `...delivery-status` |

Also paste the `CALLRAIL_WEBHOOK_SECRET` value into the CallRail dashboard's webhook signing config (exact field name TBD). This same secret must live in the corresponding environment's `.env`/secret store.

**Runbook entry required:** document the webhook URL swap procedure for domain migrations. If we move from `grinsirrigation.com` to a new host, someone must update CallRail or every inbound STOP will silently fail.

### 12.3 Webhook idempotency

CallRail may retry webhooks on our 5xx or timeouts. Both webhook handlers MUST be idempotent:

- Dedupe store: Redis set `sms:webhook:processed:{provider}:{message_id}` with 24h TTL
- Handler flow: (1) verify signature, (2) `SADD` the dedupe key, (3) if `SADD` returns 0, skip processing and return 200, (4) otherwise proceed
- Failure mode: if Redis is down, the handler should still process the payload but log a warning. Occasional duplicate side effects (an `SmsConsentRecord` inserted twice) are preferable to missing opt-outs.

### 12.4 Rate limit tracker — Redis layout (simplified 2026-04-07)

CallRail returns authoritative rate-limit state on every response (confirmed Phase 0.5). We do NOT maintain our own sliding window — we mirror CallRail's counters.

- Single cache key: `sms:rl:{provider}:{account_id}` with TTL = 120 seconds
- Value: JSON blob `{"hourly_used": int, "hourly_allowed": int, "daily_used": int, "daily_allowed": int, "fetched_at": iso8601}`
- Updated by `CallRailProvider.send_text()` after every response using the `x-rate-limit-*` response headers
- Read by workers before claiming the next recipient
- **Block decision:** refuse new sends when `hourly_allowed - hourly_used <= 5` OR `daily_allowed - daily_used <= 5`. Compute `retry_after_seconds` as seconds until the next hour (for hourly) or next midnight UTC (for daily).
- **Redis down:** fall back to reading the in-process memory copy from the last send. Accept up to one worker's-worth of over-aggression until the next successful response refreshes the value. No hard fail — CallRail will itself return 429 if we truly overrun.

---

## 13. Permission Matrix

RBAC mapping for every SMS- and campaign-related action. Routes enforce these via FastAPI dependency functions in `api/dependencies.py`.

| Action | Admin | Manager | Technician |
|---|:-:|:-:|:-:|
| View `SentMessagesLog` (sent message history) | ✅ | ✅ | ❌ |
| View `CommunicationsQueue` (inbound unaddressed) | ✅ | ✅ | ✅ |
| Mark inbound communication as addressed | ✅ | ✅ | ✅ |
| View Campaigns list | ✅ | ✅ | ❌ |
| View single campaign detail | ✅ | ✅ | ❌ |
| Create campaign (draft) | ✅ | ✅ | ❌ |
| Edit draft campaign | ✅ | ✅ (own drafts) | ❌ |
| Upload CSV audience file | ✅ | ❌ | ❌ |
| Provide CSV staff attestation | ✅ | ❌ | ❌ |
| Send campaign to <50 recipients | ✅ | ✅ | ❌ |
| Send campaign to ≥50 recipients | ✅ | ❌ | ❌ |
| Schedule campaign for future | ✅ | ✅ (<50 recipients) | ❌ |
| Cancel campaign in progress | ✅ | ✅ (own campaigns) | ❌ |
| Retry failed recipients | ✅ | ✅ | ❌ |
| Delete campaign (soft) | ✅ | ❌ | ❌ |
| Change SMS provider (env var) | ✅ (infra-level) | ❌ | ❌ |
| View audit log | ✅ | ❌ | ❌ |
| Access worker health endpoint | ✅ | ✅ | ❌ |

**50-recipient threshold rationale:** Managers can self-serve most tactical outreach. Campaigns that reach 50+ people (roughly our entire active-customer base for a weekly nudge) require Admin sign-off to protect against accidental blast-radius errors and to provide a second set of eyes for compliance.

**Route dependency implementation:**
```python
# api/dependencies.py
def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(403, "Admin required")
    return user

def require_admin_or_manager(user: User = Depends(get_current_user)) -> User:
    if user.role not in ("admin", "manager"):
        raise HTTPException(403, "Admin or Manager required")
    return user

def require_campaign_send_authority(
    campaign_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> User:
    """Enforces the <50 vs ≥50 recipient threshold on send."""
    recipient_count = await count_recipients(db, campaign_id)
    if recipient_count >= 50 and user.role != "admin":
        raise HTTPException(403, "Admin required for campaigns ≥50 recipients")
    if user.role not in ("admin", "manager"):
        raise HTTPException(403, "Admin or Manager required")
    return user
```

**Per-route application:** every new endpoint listed in §11 "New Files → Backend — other" gets the correct dependency. Route tests must include a 403 case for each unauthorized role.

---

## 14. State Machines

### 14.1 `CampaignRecipient` lifecycle

```
                        ┌─────────────┐
                        │   pending   │  ← initial state on creation
                        └──────┬──────┘
                               │ worker picks
                               ▼
                        ┌─────────────┐
                        │   sending   │  ← sending_started_at set; provider API called
                        └──┬────┬─────┘
                           │    │
              success ┌────┘    └────┐ error
                      ▼              ▼
              ┌─────────────┐ ┌─────────────┐
              │    sent     │ │   failed    │  ← error_message populated
              └─────────────┘ └─────────────┘
                  (terminal)

       At any time (if from pending or sending stuck in interrupt):
       ┌──────────────┐
       │   cancelled  │  ← via POST /campaigns/{id}/cancel
       └──────────────┘
```

**`sent` is terminal.** CallRail does not provide delivery status callbacks (confirmed in Phase 0.5 smoke test), so there is no `delivered` state and no post-send carrier-feedback transitions. Any downgrade from `sent` would require a new data source we don't have.

**Allowed transitions:**

| From | To | Trigger |
|---|---|---|
| `pending` | `sending` | Worker picks recipient for processing |
| `pending` | `cancelled` | Campaign cancelled by staff |
| `sending` | `sent` | Provider returned 200 |
| `sending` | `failed` | Provider error / consent denied / time-window blocked |
| `sending` | `cancelled` | Rare — admin force-cancel during processing |
| `sending` | `failed` (`worker_interrupted`) | Orphan recovery job — stuck >5 min |
| `failed` | `pending` | Manual retry via "Retry failed recipients" (creates a new `CampaignRecipient` row; original stays `failed` for audit) |

**Invalid transitions** (attempt raises `InvalidStateTransitionError`):
- `sent` → anything
- `cancelled` → anything

### 14.2 `Campaign` lifecycle

```
draft → scheduled → sending → sent
   └──────────────────────── cancelled
                         └── partial_failed  ← some recipients failed
```

**States:**
- `draft` — being composed; not yet queued. Can be freely edited.
- `scheduled` — has `scheduled_at` in the future; frozen for edits; waiting on worker interval job to pick up.
- `sending` — worker is actively dequeuing recipients.
- `sent` — all recipients in terminal states, at least one `sent` or `delivered`, no `failed`.
- `partial_failed` — all recipients in terminal states, at least one `failed`.
- `cancelled` — user-initiated stop; any remaining `pending` recipients transition to `cancelled`.

**Derived on query** rather than stored explicitly: `sent` vs `partial_failed` is computed from aggregate recipient statuses at read time, to avoid the "what if a delivery webhook arrives after we marked the campaign done" race.

### 14.3 Orphan recovery

Runs on every worker startup and on each interval tick:

```sql
UPDATE campaign_recipients
SET delivery_status = 'failed',
    error_message = 'worker_interrupted',
    sent_at = NULL
WHERE delivery_status = 'sending'
  AND sending_started_at < now() - interval '5 minutes';
```

Interrupted recipients show up in the "Failed" filter of the campaign detail view with a distinct reason. Staff can retry them with a single click.

---

## 15. Operational Concerns

### 15.1 Monitoring metrics

Structured log events (emit via existing `LoggerMixin`):

| Event | Level | Fields | Purpose |
|---|---|---|---|
| `sms.send.requested` | INFO | `provider`, `recipient_phone_masked`, `consent_type`, `campaign_id?` | Audit every call |
| `sms.send.succeeded` | INFO | `provider_conversation_id`, `provider_thread_id`, `latency_ms`, `hourly_remaining`, `daily_remaining` | Success rate + live rate capacity |
| `sms.send.failed` | WARN/ERROR | `error_code`, `error_message`, `retry_count` | Failure rate |
| `sms.rate_limit.tracker_updated` | DEBUG | `hourly_used`, `hourly_allowed`, `daily_used`, `daily_allowed` | Capacity visibility (from CallRail response headers) |
| `sms.rate_limit.denied` | WARN | `retry_after_seconds`, `hourly_remaining`, `daily_remaining` | Hitting ceiling |
| `sms.consent.denied` | INFO | `phone_masked`, `consent_type`, `reason` | Compliance trail |
| `sms.webhook.inbound` | INFO | `provider`, `from_phone_masked`, `action` | Inbound activity |
| `sms.webhook.signature_invalid` | WARN | `provider`, `headers_seen` | Security concern |
| `campaign.created` | INFO | `campaign_id`, `created_by`, `recipient_count` | Audit trail |
| `campaign.sent` | INFO | `campaign_id`, `sent_count`, `failed_count`, `duration_s` | Post-hoc report |
| `campaign.cancelled` | WARN | `campaign_id`, `cancelled_by`, `pending_count` | Audit |
| `campaign.worker.tick` | DEBUG | `recipients_processed`, `tick_duration_ms` | Worker health |
| `campaign.worker.orphan_recovered` | WARN | `recipient_ids`, `count` | Crash recovery events |

Phone numbers are masked in logs: `+1952***3750` (last 4 digits only) to minimize PII exposure.

### 15.2 Alert thresholds

Configure in the platform's existing alerting stack (Sentry / Datadog / whatever is in use). If none exists, at minimum log at ERROR level and surface in the admin dashboard.

| Condition | Severity | Channel |
|---|---|---|
| `sms.webhook.signature_invalid` > 3 in 5 min | Critical | Page oncall |
| CallRail API returns 401 (auth error) | Critical | Page oncall + disable provider automatically |
| `sms.rate_limit.denied` > 10 in 1 hr | Warning | Slack notification |
| `campaign.worker.orphan_recovered` > 0 | Warning | Slack notification |
| Worker tick gap > 5 min | Warning | Admin dashboard banner |
| Campaign failure rate > 10% | Warning | Campaign detail view + email to campaign creator |
| Daily SMS send count > 800 (80% of 1k cap) | Info | Admin email heads-up |

### 15.3 Worker health endpoint

`GET /api/v1/campaigns/worker-health` returns:
```json
{
  "last_tick_at": "2026-04-07T14:30:12Z",
  "last_tick_duration_ms": 847,
  "last_tick_recipients_processed": 12,
  "pending_count": 147,
  "sending_count": 0,
  "orphans_recovered_last_hour": 0,
  "rate_limit": {
    "provider": "callrail",
    "hourly_used": 43,
    "hourly_allowed": 150,
    "daily_used": 127,
    "daily_allowed": 1000,
    "fetched_at": "2026-04-07T14:30:08Z"
  },
  "status": "healthy"  // or "stale" if last_tick_at > 2 min ago
}
```

Values under `rate_limit` are sourced from CallRail's response headers on the most recent successful send (per §12.4), not from an internal counter.

UI polls this every 30 seconds while the Campaigns tab is open and renders the green/red status dot.

---

## 16. UX Specifications

### 16.1 Confirmation friction for large sends

- **<50 recipients:** Standard confirm dialog: "Send to N recipients? [Cancel] [Send]"
- **≥50 recipients:** Typed confirmation. Dialog text: "You are about to send SMS to **N people**. This cannot be undone. Type **SEND N** below to confirm." Submit button stays disabled until the typed string matches exactly (case-sensitive).
- **Any size, scheduled future:** Additional line: "Scheduled for {timestamp in CT}. You can still cancel before it starts."

### 16.2 Draft persistence

- Wizard state auto-saves to `localStorage` under key `comms:draft_campaign:{staff_id}` on every field change (debounced 500ms)
- On modal re-open, if a draft exists: modal opens with a banner "You have an unsaved draft from {relative time} — [Continue] [Discard]"
- On "Next" click from Step 1 (after audience is built), also persist as a `Campaign` row in the DB with `status='draft'` so the draft survives browser cache clears
- Drafts auto-expire after 7 days (soft delete job)

### 16.3 Message composer behaviors

- **Character counter:** GSM-7 mode by default. Detects non-GSM chars (including any emoji) and switches to UCS-2 mode — badge changes color and shows new segment limits.
- **Segment thresholds:**
  - GSM-7: 160 / 306 (2 seg @ 153) / 459 (3 seg @ 153) / ...
  - UCS-2: 70 / 134 (2 seg @ 67) / 201 (3 seg @ 67) / ...
- **Merge fields:** fixed allowed list for MVP: `{first_name}`, `{last_name}`. Linter underlines any other `{token}` in red. Insert-merge-field buttons above the textarea.
- **Live preview panel:** fetches first 3 recipients from current audience via `POST /campaigns/audience/preview` and renders the message per recipient showing `"Grins Irrigation: " + body + <STOP footer>`. Shows empty-merge-field warnings inline.
- **Sender prefix:** literal `"Grins Irrigation: "` (configurable via `SMS_SENDER_PREFIX` env var for test environments).
- **STOP footer:** auto-appended if not already present in body. Text: ` Reply STOP to opt out.` (with leading space). Character counter includes it in its totals.

### 16.4 CSV upload behaviors

Fully spec'd in Phase 5 checklist under "CSV upload behaviors in the Ad-hoc panel." Summary reference:
- 2 MB file size cap, 5,000-row cap
- Auto-detect encoding (UTF-8 / UTF-8-BOM / Latin-1 / Windows-1252)
- Required column: `phone`. Optional: `first_name`, `last_name`. Case-insensitive headers, any order.
- Phone normalization: strip non-digits, prefix `+1` if 10 digits. Reject otherwise with row-level error.
- Staged upload returns `upload_id` + breakdown. Ghost leads are NOT created at upload time — only on final campaign send.
- Staff attestation checkbox required before confirmation.

### 16.5 Error recovery views

- Failed campaigns show in the Campaigns tab with a red "Failed" or "Partial" badge
- Detail view lists each failed recipient with: phone (masked), source (customer/lead/ghost), failure reason, timestamp
- Bulk actions: "Retry selected", "Mark all as do not retry"
- Retrying creates new `CampaignRecipient` rows tied to the same campaign with fresh `pending` state; original failed rows stay put for audit
- Cancelling a mid-send campaign: transitions all remaining `pending` rows to `cancelled`; `sending` rows are allowed to finish naturally (we don't kill mid-send)

### 16.6 UI status labels (updated 2026-04-07)

Because CallRail does not emit delivery status callbacks, the platform has no way to know whether an SMS actually reached the handset — only whether CallRail accepted the request. UI copy reflects this honestly:

| State | UI label | Tooltip |
|---|---|---|
| `pending` | **Queued** | "Waiting for the worker to process this recipient." |
| `sending` | **Sending** | "Currently handing off to CallRail." |
| `sent` | **Sent** | "Handed off to CallRail successfully. Delivery to the recipient's handset is not tracked." |
| `failed` | **Failed** | "CallRail rejected the request. See error detail." |
| `cancelled` | **Cancelled** | "Cancelled before sending." |

**Do NOT use labels like "Delivered" or "Received"** — they imply delivery confirmation we do not have. Stats cards aggregate these into "Sent / Failed / Cancelled / Queued" buckets, no "Delivered" bucket.

---

## 17. Compliance Details

### 17.1 TCPA consent_type semantics

See §10.3 S11 for full definitions. Quick reference:

| Type | When | Requires |
|---|---|---|
| `marketing` | Campaigns, promos, newsletters | Explicit opt-in (form, START, or CSV attestation). STOP = hard block. |
| `transactional` | Appointment reminders, confirmations, invoices | EBR exemption allowed. STOP = hard block. |
| `operational` | STOP confirmations, legally-required notices | Always allowed. |

**Hard-STOP rule:** any `SmsConsentRecord` row with `consent_method='text_stop'` and `consent_given=false` blocks ALL outbound sends to that phone forever, regardless of consent_type — EXCEPT the STOP confirmation itself, which is operational and legally required to send in response.

### 17.2 CSV staff attestation — audit trail

Every CSV upload via the Ad-hoc panel creates:
- One `Lead` row per unmatched phone (ghost lead)
- One `SmsConsentRecord` row per distinct phone with:
  - `consent_type = 'marketing'`
  - `consent_given = true`
  - `consent_method = 'csv_upload_staff_attestation'`
  - `consent_language_shown = <verbatim attestation text shown in the UI>`
  - `consent_form_version = 'CSV_ATTESTATION_V1'`
  - `consent_timestamp = now()`
  - `customer_id` OR `lead_id` populated
  - Staff user ID recorded via a new JSONB metadata field OR by storing it in `consent_ip_address` (misuse — prefer adding a `created_by_staff_id` column in a Phase 1 migration)
- One `audit_log` row with event type `sms.csv_attestation.submitted`, actor = staff user, payload = `{upload_id, phone_count, attestation_version}`

**Retention:** 7 years minimum per `SmsConsentRecord` model comment (TCPA requirement). A retention sweep job must NOT delete these rows before 7 years elapse.

### 17.3 Time window (H1)

- All automated/campaign sends enforced in Central Time (8 AM – 9 PM) via `SMSService.enforce_time_window()`
- Manual one-off sends (`message_type='custom'`) can bypass the window per existing code
- **Known limitation:** we do not currently resolve recipient-local timezones. An out-of-state phone number (e.g., a Twin Cities customer with a Colorado area code) receives Grins SMS during CT window, which may fall outside their local 8 AM – 9 PM.
- **Mitigation for Phase 5:** UI warning in the Review step: "P recipients have non-Central area codes. They will be texted within CT hours (8 AM – 9 PM Central) — this may fall outside their local window. Per-recipient timezone enforcement is deferred to a future phase."
- `services/sms/phone_normalizer.py` includes an area-code → timezone lookup table (NANP area codes) to feed the UI warning count.
- Full per-recipient TZ enforcement is deferred to Phase 7+.

### 17.4 Data retention & deletion

- `SentMessage` rows: kept indefinitely as part of communications audit log. No automatic deletion.
- `SmsConsentRecord` rows: **7-year minimum retention** per TCPA. Never deleted via any normal code path. A future GDPR right-to-delete flow must explicitly exempt these or mask PII in place.
- `Campaign` + `CampaignRecipient` rows: retained indefinitely.
- `Lead` rows (including ghost leads): follow existing lead retention policy (not changed by this feature).
- **GDPR delete request:** out of scope for this spec. Document as a known gap; address in a separate spec when needed. When implemented, deletion must NULL out PII fields (phone, name, message content) while preserving the row structure for audit.

### 17.5 Audit log wiring

The platform already has `audit_log.py`. Wire the following events:
- `sms.provider.switched` — actor, old provider, new provider
- `sms.campaign.created` — actor, campaign_id, recipient_count
- `sms.campaign.sent_initiated` — actor, campaign_id
- `sms.campaign.cancelled` — actor, campaign_id, reason
- `sms.csv_attestation.submitted` — actor, upload_id, phone_count, attestation_version
- `sms.consent.hard_stop_received` — phone_masked, source (inbound webhook)
- `sms.config.webhook_secret_rotated` — actor, environment

---

## 18. Testing Strategy

### 18.1 Unit test coverage targets

Per module:

| Module | Target | Key cases |
|---|---|---|
| `callrail_provider.py` | 100% | send happy path, 4xx auth, 429 rate limit, 5xx retry logic, webhook signature verify (valid/invalid), payload parse |
| `twilio_provider.py` | 100% | same as above (ports current stub faithfully) |
| `recipient.py` | 100% | all three factories, equality, phone normalization on construction |
| `ghost_lead.py` | 100% | new phone creates lead, existing phone returns existing lead, concurrent-call race (two threads, same phone → one lead) |
| `consent.py` | 100% | marketing opt-in/opt-out, transactional under EBR, operational always-allowed, hard-STOP precedence, type-scoping |
| `state_machine.py` | 100% | every allowed transition, every forbidden transition raises, orphan recovery SQL |
| `rate_limiter.py` | 100% | under limit, at limit, over limit, window rollover, Redis-down hard-fail |
| `segment_counter.py` | 100% | GSM-7 single/multi, UCS-2 single/multi, emoji triggers UCS-2 mode, boundary edge cases (160, 161, 306, 307, 70, 71) |
| `phone_normalizer.py` | 100% | US 10-digit, US 11-digit, E.164, international, bogus (000-, 555-01xx), extensions, letters |

### 18.2 Integration test scenarios

1. **End-to-end campaign, mixed audience:** 1 customer + 1 lead + 1 ad-hoc CSV row → create → audience preview → send → verify 3 `SentMessage` rows with correct FKs, 1 new ghost Lead, 1 new `SmsConsentRecord` for the ad-hoc phone, all `CampaignRecipient` rows in `sent` state, `Campaign.status='sent'`.
2. **Consent enforcement:** customer A has hard-STOP record → campaign send to audience containing A → A's `CampaignRecipient` ends in `failed` with reason `consent_denied`, others succeed.
3. **B4 regression test:** same recipient across two different campaigns within 24h → both succeed. Same campaign tried twice → second is blocked.
4. **Orphan recovery:** manually set a `CampaignRecipient` to `sending` with `sending_started_at = now() - 10 minutes` → run worker startup hook → verify transition to `failed` with `error_message='worker_interrupted'`.
5. **Rate limiter under load:** fire 200 `send_message` calls in a tight loop → verify exactly 150 succeed in the first hour window, 50 are deferred with `scheduled_for` set, worker processes the rest in the next hour window.
6. **Inbound STOP flow:** POST a simulated CallRail webhook to `/webhooks/callrail/inbound` with body "STOP" → verify `SmsConsentRecord` created with `consent_given=false` → attempt to send a new campaign to that phone → verify it's blocked.
7. **CSV attestation flow:** POST a staged CSV upload (3 phones: 1 existing customer, 1 existing lead, 1 new) with attestation → send campaign → verify 3 `SentMessage` rows with correct source attribution (1 customer_id, 2 lead_id), verify 3 new `SmsConsentRecord` rows with `consent_method='csv_upload_staff_attestation'`.
8. **Permission enforcement:** Technician user attempts to POST `/campaigns` → 403. Manager attempts to send a campaign with 51 recipients → 403. Admin succeeds in both.
9. **Delivery status callback:** POST a simulated delivery webhook with status=`delivered` → verify `SentMessage.delivery_status` transitions from `sent` to `delivered`.
10. **Time window enforcement:** attempt a `transactional` send at 10 PM CT → verify deferred with `scheduled_for` set to 8 AM CT next day.

### 18.3 Load tests

- Upload a 5,000-row CSV → verify parsing completes within 5 seconds, 2 MB limit enforced, memory usage bounded
- Create a campaign with 1,000 recipients → verify audience preview endpoint returns in <1 second, send-initiate endpoint returns 202 immediately (not blocking on worker)
- 4 campaigns running concurrently → verify rate limiter correctly splits the 150/hr budget across them

### 18.4 Race condition tests

- Two concurrent CSV uploads with overlapping phones → ghost lead dedupe uses row-level lock, exactly one `Lead` row per phone
- Two workers running against the same campaign simultaneously → `sending_started_at` + `FOR UPDATE SKIP LOCKED` claim, no double-send
- Inbound STOP webhook arrives while a campaign is actively sending → mid-campaign consent check catches the STOP, remaining `pending` recipients for that phone transition to `failed` with reason `consent_denied`

### 18.5 CSV edge-case fixtures

Committed in `tests/fixtures/csv/`:
- `valid_basic.csv` — 10 US phones, UTF-8
- `valid_with_bom.csv` — UTF-8-BOM Excel export
- `valid_latin1.csv` — legacy encoding
- `malformed_phones.csv` — 5 bad rows among 20 good
- `mixed_formats.csv` — phones as `(952) 529-3750`, `952.529.3750`, `9525293750`, `+19525293750`, `1-952-529-3750`
- `duplicate_phones.csv` — same phone 3 times
- `no_header.csv` — should be rejected with helpful error
- `extra_columns.csv` — phone + first_name + last_name + notes (notes ignored)
- `empty_file.csv` — rejected
- `too_large.csv` — >2 MB rejected
- `too_many_rows.csv` — >5,000 rows rejected

---
