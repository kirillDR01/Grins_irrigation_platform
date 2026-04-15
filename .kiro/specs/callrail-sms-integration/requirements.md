# Requirements Document — CallRail SMS Integration

**Status:** Phase 0 + Phase 0.5 complete — policy decisions locked — cleared to begin Phase 1
**Last updated:** 2026-04-07 (critical review pass + Phase 0.5 live API verification)

## Introduction

Grins Irrigation has an existing CallRail account used for call tracking. This feature leverages CallRail's outbound SMS API to text ~300 current customers to get their jobs scheduled, and more broadly, turns CallRail into the SMS delivery backbone for all customer-facing texts sent from the Grin's Irrigation Platform CRM — appointment reminders, confirmations, marketing campaigns, and one-off blasts.

The sender number is `(952) 529-3750`, stored as `CALLRAIL_TRACKING_NUMBER` in E.164 format (`+19525293750`).

The integration must live inside the existing platform so that sends are tracked in the same `sent_messages` table, opt-in/opt-out consent rules apply uniformly, staff can launch campaigns from the Communications tab (and bulk-select from the Customers/Leads tabs) without leaving the CRM, and replies land back in the CRM inbox rather than in CallRail only.

**Scope decision (2026-04-07):** A single campaign may mix customers, leads, and ad-hoc phone numbers with no source restrictions. Ad-hoc phones from CSV uploads auto-create "ghost leads" (`Lead` rows with `lead_source='campaign_import'`, `status='new'`, `sms_consent=false`). This preserves the `SentMessage` check constraint without a schema migration.

**Policy decisions locked (2026-04-07):** Eight critical policy questions are resolved with defaults — campaign dedupe scoping (B4), ad-hoc CSV consent via staff attestation (S10), type-scoped consent semantics (S11), delivery receipts unsupported (S12), webhook config via env var + manual dashboard setup, Admin/Manager/Technician RBAC with 50-recipient threshold, recipient state machine with orphan recovery (S13), CT-only time window for MVP. See Requirement 29.

**Live API verified (2026-04-07):** Real SMS sent via `POST /v3/a/{account_id}/text-messages.json` returned HTTP 200 and arrived on the owner's phone. See Requirement 38 for the canonical CallRail API contract, including rate-limit response headers (simplifies S2), conversation-oriented response model (new DB columns needed), and confirmation that CallRail does not expose delivery status callbacks (resolves S12).

### Existing Platform Scaffolding (~80% existing + ~20% new wiring)

**Backend services already built:**
- `SMSService` with `send_message()` (consent + dedupe + record + send), `send_automated_message()` (adds 8AM–9PM CT time window), `handle_inbound()` — STOP / informal opt-out detection, `_process_exact_opt_out()` — creates `SmsConsentRecord` + sends confirmation, `check_sms_consent()` — per-phone consent lookup, `enforce_time_window()` — defers automated messages to 8AM CT if out of window. `_send_via_twilio()` is a PLACEHOLDER STUB at line 228–243 that just returns a fake SID — this is the exact swap-in point for CallRail.
- `CampaignService` with consent gating, CAN-SPAM unsubscribe, campaign lifecycle, recipient expansion from `target_audience` JSONB.
- `background_jobs.py` — existing background job runner.
- `notification_service.py` — generic notification dispatcher.

**Backend models already built:**
- `SentMessage` — FK to `customer_id`, `lead_id`, `job_id`, `appointment_id`; `message_type` includes `'campaign'`; `delivery_status`: pending|scheduled|sent|delivered|failed|cancelled; `twilio_sid`, `error_message`, `scheduled_for`, `sent_at` columns already exist (can store CallRail IDs, may rename to `provider_message_id` in follow-up). No schema change needed. Check constraint: `customer_id IS NOT NULL OR lead_id IS NOT NULL`.
- `Campaign` + `CampaignRecipient` — `target_audience` JSONB, `campaign_type`, `status`, `scheduled_at`, `sent_at`. `CampaignRecipient` has `channel`, `delivery_status`, `sent_at`, `error_message`, and both `customer_id` and `lead_id` FKs.
- `SmsConsentRecord` — full consent audit trail per phone number (phone-keyed, works uniformly for any recipient type).

**Backend API routes already present:**
- `sms.py` — `POST /v1/sms/send`, `BulkSendRequest`, `BulkSendResponse`, communications queue endpoint, inbound webhook.
- `campaigns.py` — campaign CRUD + send.
- `communications.py`, `sent_messages.py` — sent message log, `webhooks.py` — inbound webhook handlers (Twilio format today; needs CallRail variant added).

**Frontend already built:**
- Communications page with `CommunicationsDashboard`, `CommunicationsQueue`, `SentMessagesLog`.
- Marketing page with `CampaignManager`.
- Customers page, Leads page.
- React Query + axios + 401 refresh in `frontend/src/core/api/client.ts`.
- shadcn/ui components + Dialog pattern.

**What is NOT yet built:**
- CallRail HTTP client module.
- Provider abstraction (currently hard-wired to Twilio stub).
- CallRail-specific rate limiter (150/hr + 1,000/day).
- CallRail inbound webhook route + signature verification.
- "New Text Campaign" modal on Communications tab.
- "Text Selected" bulk action on Customers tab and Leads tab.

### Credentials & Secrets

All CallRail credentials live in the root `.env` file (gitignored). The backend reads them at runtime via environment variables:

| Variable | Purpose | Status |
|---|---|---|
| `CALLRAIL_API_KEY` | REST API authentication token | Set in `.env` |
| `CALLRAIL_ACCOUNT_ID` | Account scope for API calls | Fetched: `ACC019c31a27df478178fe0f381d863bf7d` |
| `CALLRAIL_COMPANY_ID` | Company scope for SMS sends | Fetched: `COM019c31a27f5b732b9d214e04eaa3061f` |
| `CALLRAIL_TRACKING_NUMBER` | Sender number (`+19525293750`) | Set in `.env` |

### CallRail API Capabilities (verified 2026-04-07 via Phase 0.5 live send)

- Base URL: `https://api.callrail.com/v3/`
- Auth header: `Authorization: Token token="YOUR_API_KEY"`
- Format: REST, JSON, standard HTTP verbs
- Send endpoint: `POST /v3/a/{account_id}/text-messages.json` — returns HTTP **200** (not 201)
- Required body fields (verified): `company_id`, `tracking_number` (E.164 phone, NOT tracker_id), `customer_phone_number` (E.164), `content`
- List endpoints available for: accounts, companies, tracking numbers, text message history
- **Rate limits returned in response headers** on every call: `x-rate-limit-hourly-allowed`, `x-rate-limit-hourly-used`, `x-rate-limit-daily-allowed`, `x-rate-limit-daily-used`
  - SMS Send: 150/hour, 1,000/day — confirmed
  - General API: 1,000/hour, 10,000/day
- **Response is conversation-oriented**, not message-oriented. Top-level `id` is the conversation ID (e.g., `"k8mc8"`), NOT a message ID. Individual messages live in `recent_messages[]` with no per-message ID — only `direction`, `content`, `created_at`, `sms_thread.id`, `type`, `media_urls`. Implication: `SentMessage` needs TWO new columns, `provider_conversation_id` AND `provider_thread_id`.
- **No delivery status callbacks.** Response has no `status`, `delivery_status`, or `callback_url` field. CallRail does not emit delivery webhooks. `sent` is the terminal happy state. UI does NOT claim "Delivered" anywhere.
- **Idempotency-Key header: inconclusive.** We sent one and CallRail did not echo it back. Do not rely on provider-side dedupe — the recipient state machine (S13) is the sole double-send protection.
- Implication for 300-customer blast: 1,000/day cap is fine for a single day; 150/hour cap forces at least a ~2-hour throttled drip for all 300
- No official CLI — use `httpx` (already in the project's async stack) directly
- 10DLC registration is mandatory for any business sending outbound A2P SMS. Unregistered messages are blocked outright by US carriers in 2026, not just surcharged. **VERIFIED 2026-04-07:** `brand_status: "registered_in_twilio"` via API + campaign-level registration confirmed in CallRail Compliance Home dashboard.
- CallRail will auto-append STOP language on first contact if none is included, but we bake it into our templates.
- Observed latency on send: 606ms round-trip, 275ms CallRail-side processing.

### API Reference Sources

- https://apidocs.callrail.com/
- https://support.callrail.com/hc/en-us/articles/30896711642253-Sending-text-messages-in-CallRail
- https://support.callrail.com/hc/en-us/articles/18593904382221-Text-Message-Compliance-10DLC-regulations-and-guidelines
- https://support.callrail.com/hc/en-us/articles/34065659566221-Message-Flows
- https://rollout.com/integration-guides/call-rail/api-essentials

### Deep Repo Analysis — Gap Report (3 BLOCKERS + 9 structural gaps)

This section is the authoritative gap list produced by a full backend + frontend audit. It supersedes the more optimistic "80% built" framing — the scaffolding exists but has three structural bugs and several missing pieces that must be resolved before the Communications tab can actually send SMS via CallRail.

**Verdict:** NOT ready to connect as-is. Three blockers must be fixed or campaigns will silently fail even with a perfect CallRail client. One of the blockers is a pre-existing bug unrelated to CallRail.

**BLOCKERS (must fix first):**
- **B1:** `CampaignService` is never handed an `SMSService` instance — Location: `src/grins_platform/api/v1/campaigns.py:54`. Route instantiates `CampaignService(campaign_repository=repo)` without passing `sms_service` or `email_service`. Inside `_send_to_recipient()` there's a `if self.sms_service is not None:` guard → SMS path is skipped entirely. Campaign send endpoint returns success with 0 sent.
- **B2:** Campaign sends bypass `SmsConsentRecord` consent check — Location: `src/grins_platform/services/campaign_service.py` around lines 592–600. Campaigns read `Customer.sms_opt_in` directly and pass `sms_opt_in=True` into `SMSService.send_message()`, which skips `check_sms_consent()`. A customer who previously replied STOP (creating an `SmsConsentRecord` row) will still be texted by a campaign. TCPA compliance risk.
- **B3:** `POST /sms/send-bulk` runs synchronously in the HTTP request thread — Location: `src/grins_platform/api/v1/sms.py:199–250`. Iterates recipients sequentially, no throttling, no queue, no rate limit. For 300 customers: (a) blows past CallRail's 150/hr cap → 429s, (b) holds the HTTP request open for minutes → proxy timeout.
- **B4:** 24-hour dedupe in `SMSService.send_message()` silently blocks back-to-back campaigns — Location: `src/grins_platform/services/sms_service.py:113–134`. Every `send_message()` call checks `get_by_customer_and_type(customer_id, message_type, hours_back=24)` and returns `success: false` if a match is found. Campaign sends use `message_type='campaign'`. Consequence: running a second campaign within 24h silently fails for every customer who got the first one. UI shows "sent" but nothing goes out. Also breaks retry-failed-recipients within the same campaign. **Severity: Critical — silent data loss on any second-same-day campaign.**

**Structural gaps:**
- **S1:** No SMS provider abstraction — Location: `src/grins_platform/services/sms_service.py`. Class is named `SMSService` and `_send_via_twilio()` is a method on it. Grep for `class.*Provider|BaseSMSProvider|SmsProvider|provider_factory|get_sms_provider` in `src/` returns no matches. Need Strategy pattern with `BaseSMSProvider` Protocol, `CallRailProvider`, `TwilioProvider`, `NullProvider`, factory.
- **S2:** ~~No outbound SMS rate limiter~~ → **SIMPLIFIED 2026-04-07:** CallRail returns authoritative rate-limit state on every response (`x-rate-limit-*` headers). Replaced the Redis sliding-window counter with a `rate_limit_tracker.py` module that parses headers, caches values in Redis 120s, and defers new sends when `hourly_remaining <= 5`. See Requirement 39.
- **S3:** Background jobs use in-process APScheduler, not worker-safe — Location: `src/grins_platform/services/background_jobs.py`. APScheduler with cron jobs registered in-process. Jobs are daily/weekly maintenance tasks (escalate_failed_payments, check_upcoming_renewals, etc.). No worker pool, no persistent queue, no distributed job state. A 300-recipient throttled campaign dripping over 2+ hours would block a FastAPI worker and lose progress on pod restart. MVP fix: APScheduler interval job. Proper follow-up: ARQ (async Redis queue).
- **S4:** No CallRail inbound webhook route — Location: `src/grins_platform/api/v1/webhooks.py:988–1040` handles `POST /webhooks/twilio-inbound` with Twilio's form-encoded payload + `X-Twilio-Signature`. CallRail's payload shape and signature mechanism are different. Must ship with Phase 1 for STOP compliance. Webhook signature mechanism still needs live verification during Phase 1 smoke testing (requires receiving a real inbound message).
- **S5:** Audience filter is nearly empty — Location: `campaign_service._filter_recipients()` lines 468–529. Supported today: `lead_source`, `is_active`, `no_appointment_in_days`. That's it. Missing: `sms_opt_in` (critical), `ids_include`, `cities`, `last_service_between`, `tags_include`.
- **S6:** No merge-field templating — Location: `SMSService.send_message()` accepts a pre-rendered string. Can't personalize `{first_name}` / `{last_name}` / `{next_appointment_date}` at send time.
- **S7:** No multi-select/bulk action on Customers list — Location: `frontend/src/features/customers/components/CustomerList.tsx` uses TanStack Table but has no checkbox column or bulk-action toolbar.
- **S8:** Communications tab has no compose/send UI — Location: `frontend/src/pages/Communications.tsx` + `features/communications/components/CommunicationsDashboard.tsx`. Current state: exactly two tabs — `CommunicationsQueue` (inbound unaddressed messages) and `SentMessagesLog` (outbound history). Zero compose, zero audience picker, zero preview, zero "New Campaign" button.
- **S9:** `SMSService` and `CampaignService` only accept Customers, not Leads or ad-hoc phones — CRITICAL, promotes to blocker since 300 recipients may be mixed. Location: `campaign_service._filter_recipients()` returns `list[Customer]`, only queries the Customer table. `_send_to_recipient(customer: Customer, ...)` only accepts a Customer. Data model reality check: `SentMessage` has BOTH `customer_id` and `lead_id` FK columns with check constraint. `CampaignRecipient` likewise has both FKs. `SmsConsentRecord` is keyed by phone number. The model is ready; the services are not. Consent field naming asymmetry: `Customer.sms_opt_in` (bool) vs `Lead.sms_consent` (bool) — semantically identical, named differently.
- **S10:** Ad-hoc CSV uploads have no real consent gate — Ghost leads created from CSV uploads start with `sms_consent=false`, but `check_sms_consent()` is phone-keyed against `SmsConsentRecord` and returns `True` when no records exist (default allow). A brand-new ghost lead therefore passes the consent check despite `Lead.sms_consent=false`. TCPA gray zone. **Fix:** Staff attestation model — CSV upload UI checkbox, backend auto-creates `SmsConsentRecord` rows with `consent_method='csv_upload_staff_attestation'`. See Requirement 25.
- **S11:** `consent_type` is ignored by `check_sms_consent()` — The `SmsConsentRecord` model has a mandatory `consent_type` column but the query ignores it. Conflates marketing and transactional consent. A customer who replied STOP to a marketing blast would also be blocked from receiving appointment reminders (wrong). **Fix:** Three consent types (`marketing`/`transactional`/`operational`) with type-scoped check logic. See Requirement 26.
- **S12:** ~~No delivery status webhook~~ → **RESOLVED 2026-04-07:** CallRail does not expose delivery status callbacks (confirmed via live send). Response body has no `status` / `delivery_status` / `callback_url` field. `sent` IS the terminal happy state. UI labels "Sent" not "Delivered." No webhook route needed. See Requirement 27.
- **S13:** Campaign recipient state machine is undefined → double-send risk on crash — Without an explicit `sending` intermediate state, a worker crash between CallRail 200 response and DB update causes a second send on restart. **Fix:** Explicit `pending → sending → sent/failed/cancelled` state machine with `sending_started_at` timestamp and 5-minute orphan recovery. See Requirement 28.

### What's Actually Ready (Reusable As-Is)

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

### Severity Matrix

| ID | Severity | Blocks 300-recipient blast? | Blocks UI? | Blocks Twilio swap? |
|----|----------|:-:|:-:|:-:|
| B1 | Critical | ✅ | ✅ | — |
| B2 | Critical (compliance) | ✅ | ✅ | — |
| B3 | Critical | ✅ | ✅ | — |
| **B4** | **Critical (silent data loss)** | **✅** | **✅** | — |
| S1 | High | — | — | ✅ |
| S2 | **Low** (simplified via headers 2026-04-07) | — | — | — |
| S3 | High | ✅ | ✅ | — |
| S4 | High (compliance) | ✅ | ✅ | — |
| S5 | Medium | — | ✅ | — |
| S6 | Medium | — | ✅ | — |
| S7 | Low | — | partial | — |
| S8 | High | — | ✅ | — |
| S9 | Critical | ✅ | ✅ | — |
| **S10** | **Critical (TCPA)** | **✅ (if any ad-hoc)** | **✅** | — |
| **S11** | **High (compliance nuance)** | — | **✅** | — |
| **S12** | **Resolved 2026-04-07** — `sent` is terminal | — | — | — |
| **S13** | **Critical (double-send risk)** | **✅** | **✅** | — |
| M1–M5 | Low | — | — | — |

**Scope clarification (2026-04-07):** The 300-recipient scheduling outreach may be any mix of customers, leads, or ad-hoc phone numbers. One campaign must support all three sources simultaneously. No artificial restrictions. This promotes S9 from "feature" to "blocker."

**Minimum to unblock 300-recipient blast:** B1, B2, B3, **B4**, S1 (simplified), S3 (MVP tick job), S4, S9, **S10** (if any ad-hoc), **S13**
**Minimum to ship full Communications UI:** everything above + S5, S6, S8, **S11**
**Minimum for Twilio swap:** just S1 (provider abstraction)
**Minimum for regulatory defense on audit:** B4, S10, S11, plus Requirement 36 compliance enforcement

### Implementation Phases

- **Phase 0:** Pre-flight (COMPLETE) — 10DLC verified (brand confirmed via API: `brand_status: "registered_in_twilio"`; campaign-level registration confirmed visually in CallRail Compliance Home dashboard 2026-04-07). All CallRail IDs captured: `CALLRAIL_ACCOUNT_ID=ACC019c31a27df478178fe0f381d863bf7d`, `CALLRAIL_COMPANY_ID=COM019c31a27f5b732b9d214e04eaa3061f`. Tracker `TRK019c5f8c1c3279f98b678fb73d04887e` verified with `sms_supported=true`, `sms_enabled=true`. All values written to `.env` (gitignored, verified via `git check-ignore`). Cleared to begin Phase 1.
- **Phase 1:** Provider abstraction + CallRail client + Recipient unification (backend only).
- **Phase 2:** Unblock 300-customer blast (interim CSV script).
- **Phase 3:** Background job for throttled campaign sends.
- **Phase 4:** Audience filter extensions (multi-source).
- **Phase 5:** Communications tab full UI (3-step wizard: AudienceBuilder, MessageComposer, CampaignReview).
- **Phase 6:** Customers tab AND Leads tab entry points (bulk select + "Text Selected").
- **Phase 7:** Polish & Twilio swap readiness.

Each phase is independently shippable.

### Tab Architecture

- **Customers tab** — bulk "Text Selected" action on the customer table. Multi-select rows → click action → opens `NewTextCampaignModal` with selection pre-loaded into the audience builder. Same modal, different entry point.
- **Communications tab** — primary home: `New Text Campaign` button, active/scheduled campaign list, `CommunicationsQueue`, `SentMessagesLog`.
- **Marketing tab** — continues to own the multi-channel campaign manager (`CampaignManager.tsx`). If its audience UI is generic enough, Communications' modal can share it. Otherwise keep them separate: Communications = tactical one-off blasts, Marketing = multi-touch campaigns.

### Twilio Swap Procedure (post-Phase 1)

Once the provider abstraction lands in Phase 1, switching from CallRail to Twilio is a zero-code operation:

1. Verify Twilio 10DLC registration is live
2. In `.env`: Set `SMS_PROVIDER=twilio`, `TWILIO_ACCOUNT_SID=...`, `TWILIO_AUTH_TOKEN=...`, `TWILIO_PHONE_NUMBER=...`. Leave `CALLRAIL_*` vars in place as fallback.
3. Update Twilio's inbound webhook URL in the Twilio console → `https://<host>/api/v1/webhooks/twilio-inbound`
4. Restart the backend. `get_sms_provider()` now returns `TwilioProvider` on boot.
5. Smoke test: send one text, reply STOP, verify `SmsConsentRecord` created.
6. Rate-limiter key automatically namespaces by `provider_name`, so CallRail's counters don't leak into Twilio's window.

No changes to `SMSService`, `CampaignService`, `Communications` UI, or any business logic.

### Open Questions & Decisions (from source document)

1. **Reply handling** — when a customer replies "YES schedule me", where does it land? CallRail inbox + platform inbox + Slack ping to owner + auto-create a job-scheduling task? (STILL OPEN — addressed tactically by inbound webhook, but routing/notification policy TBD by business)
2. **Sender identity format** — **LOCKED 2026-04-07:** literal `"Grins Irrigation: "` (no apostrophe, trailing space), configurable via `SMS_SENDER_PREFIX` env var
3. **Message template for the 300-customer blast** — still pending owner draft
4. **Tracking number strategy** — **MVP: one dedicated SMS number** (`+19525293750` Website). Account has 4 active SMS-enabled trackers (Website/Facebook/Instagram/Google My Business) — rotation deferred to Phase 7+ if rate limits become tight.

### Ghost Lead Design Rationale

For unmatched phones in a CSV upload, auto-create a `Lead` row. Benefits:
- Preserves `SentMessage` check constraint (`customer_id IS NOT NULL OR lead_id IS NOT NULL`) — zero schema migration
- Ad-hoc contacts automatically become trackable leads for future follow-up
- Consent tracking via `SmsConsentRecord` (phone-keyed) works out of the box
- Staff can filter them out of the main leads view with `lead_source=campaign_import`
- Consistent with the platform's existing intake model — any externally-sourced contact is a Lead

Alternatives rejected:
- Relaxing `SentMessage` check constraint to allow fully orphaned messages → loses the audit invariant that every message traces to a CRM entity
- New `campaign_contacts` table → third contact type, creates join complexity, overkill for MVP

### Risk Matrix

| Risk | Impact | Mitigation |
|------|--------|------------|
| 10DLC not registered → silent delivery failures | 300 customers never get texted | Verify registration before go-live; startup health check (MITIGATED — verified) |
| Rate-limit overruns → 429 errors | Messages stuck in pending | Rate limiter with retry + `scheduled_for` fallback |
| Sending to opted-out customers → TCPA fines | Compliance violation | Consent check in `SMSService.send_message()` before any provider call |
| Time-window violations → customer complaints | Automated sends outside 8AM–9PM CT | `enforce_time_window()` already exists; verify on campaign path |
| Replies lost in CallRail inbox → missed scheduling requests | Customers ask to schedule, we miss it | CallRail inbound webhook → `handle_inbound()` → persist + notify staff |
| Phone format inconsistencies → failed sends | Sends fail or go to wrong number | `_format_phone()` normalizes to E.164; dry-run reports un-normalizable phones |
| CallRail API outage mid-campaign → partial send | Stuck state | Status-driven resumable job; failed sends retried with exponential backoff |
| Cost surprise from high volume → unexpected bills | Unexpected CallRail bill | Hard-cap daily sends at 1,000; alert owner if campaign exceeds 500 recipients |

## Glossary

### Key File References

**Existing files (touch or reuse):**
- `src/grins_platform/services/sms_service.py` (line 228 `_send_via_twilio` stub)
- `src/grins_platform/services/campaign_service.py`
- `src/grins_platform/services/background_jobs.py`
- `src/grins_platform/services/notification_service.py`
- `src/grins_platform/models/sent_message.py`
- `src/grins_platform/models/campaign.py`
- `src/grins_platform/models/sms_consent_record.py`
- `src/grins_platform/api/v1/sms.py`
- `src/grins_platform/api/v1/campaigns.py`
- `src/grins_platform/api/v1/webhooks.py`
- `src/grins_platform/api/v1/communications.py`
- `src/grins_platform/schemas/campaign.py`
- `frontend/src/pages/Communications.tsx`
- `frontend/src/pages/Customers.tsx`
- `frontend/src/features/communications/components/CommunicationsDashboard.tsx`
- `frontend/src/features/communications/components/CommunicationsQueue.tsx`
- `frontend/src/features/communications/components/SentMessagesLog.tsx`
- `frontend/src/features/marketing/components/CampaignManager.tsx`

**New files (to create):**

Backend — provider abstraction package:
- `src/grins_platform/services/sms/__init__.py`
- `src/grins_platform/services/sms/base.py` — `BaseSMSProvider` Protocol + `ProviderSendResult`, `InboundSMS` dataclasses
- `src/grins_platform/services/sms/callrail_provider.py` — `CallRailProvider` (httpx client + webhook parser)
- `src/grins_platform/services/sms/twilio_provider.py` — `TwilioProvider` (ports current stub)
- `src/grins_platform/services/sms/null_provider.py` — `NullProvider` (tests / dry-run)
- `src/grins_platform/services/sms/factory.py` — `get_sms_provider()` reads `SMS_PROVIDER` env
- `src/grins_platform/services/sms/rate_limit_tracker.py` — Reads CallRail's `x-rate-limit-*` response headers, caches `(hourly_remaining, daily_remaining, fetched_at)` in Redis 120s, refuses new sends when `hourly_remaining <= 5`. (Simplified 2026-04-07 from Redis sliding-window counter.)
- `src/grins_platform/services/sms/templating.py` — `render_template(body, context)` merge-field util
- `src/grins_platform/services/sms/recipient.py` — `Recipient` dataclass + `from_customer()`, `from_lead()`, `from_adhoc()` factories
- `src/grins_platform/services/sms/ghost_lead.py` — `create_or_get(phone, first_name, last_name)` helper with row-level lock
- `src/grins_platform/services/sms/consent.py` — `check_sms_consent(phone, consent_type)` with type-scoped semantics + bulk-insert helper for CSV attestation
- `src/grins_platform/services/sms/state_machine.py` — `RecipientState` enum + `transition()` validator + orphan recovery query
- `src/grins_platform/services/sms/segment_counter.py` — GSM-7 vs UCS-2 detection, segment count calculator (mirrored in frontend for composer)
- `src/grins_platform/services/sms/phone_normalizer.py` — E.164 normalizer with bogus-phone rejection + area-code-to-timezone lookup for UI warning

Backend — other:
- `src/grins_platform/api/dependencies.py` — `get_campaign_service()` DI helper (fixes B1), `require_admin()`, `require_admin_or_manager()`, `require_campaign_send_authority()` permission dependencies
- New route in `src/grins_platform/api/v1/webhooks.py`:
  - `POST /webhooks/callrail/inbound` (STOP + inbound replies)
  - (No delivery-status webhook — CallRail doesn't emit them; confirmed 2026-04-07)
- New endpoints in `src/grins_platform/api/v1/campaigns.py`:
  - `POST /campaigns/audience/preview`
  - `POST /campaigns/audience/csv` (with staff attestation in the request body)
  - `POST /campaigns/{id}/cancel`
  - `POST /campaigns/{id}/retry-failed`
  - `GET /campaigns/worker-health`
- `scripts/send_callrail_campaign.py` — one-off CSV blaster with dry-run mode
- Alembic migrations (5 new columns, all nullable, non-breaking):
  - `campaign_recipients.sending_started_at` (for S13 state machine + orphan recovery)
  - `sms_consent_records.created_by_staff_id` (for S10 CSV attestation audit trail)
  - `sent_messages.campaign_id` (for B4 dedupe scoping)
  - `sent_messages.provider_conversation_id` (for CallRail conversation-oriented response)
  - `sent_messages.provider_thread_id` (for CallRail sms_thread identifier)

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

Frontend — Customers/Leads tab entry points (Phase 6):
- Edit `frontend/src/features/customers/components/CustomerList.tsx` to add checkbox column + bulk-action bar
- Edit `frontend/src/features/leads/components/LeadsList.tsx` to add checkbox column + bulk-action bar

Configuration:
- Edit `.env.example` to add `SMS_PROVIDER=`, `CALLRAIL_*`, `TWILIO_*` placeholders
- New `src/grins_platform/config/settings.py` (Phase 7 cleanup) with `pydantic-settings`

## Glossary

- **Platform**: The Grin's Irrigation Platform CRM — the full-stack web application (FastAPI backend + React frontend) that manages customers, leads, jobs, appointments, invoices, and communications.
- **CallRail_Client**: The async HTTP client module (`callrail_provider.py`) that communicates with the CallRail REST API using `httpx.AsyncClient`.
- **SMS_Provider**: An implementation of the `BaseSMSProvider` Protocol — one of `CallRailProvider`, `TwilioProvider`, or `NullProvider` — selected at runtime via the `SMS_PROVIDER` environment variable.
- **Provider_Factory**: The `get_sms_provider()` function in `factory.py` that reads the `SMS_PROVIDER` env var and returns the appropriate `SMS_Provider` instance.
- **SMS_Service**: The `SMSService` class — the central business-logic layer for all outbound and inbound SMS. Owns consent checking, time-window enforcement, deduplication, message persistence, and provider dispatch.
- **Campaign_Service**: The `CampaignService` class — manages campaign lifecycle (create, schedule, send, complete), recipient expansion from `target_audience` JSONB, and per-recipient send orchestration.
- **Rate_Limiter**: The Redis-backed sliding-window counter (`rate_limiter.py`) that enforces CallRail's 150/hour and 1,000/day outbound SMS caps per provider account.
- **Recipient**: A frozen dataclass (`recipient.py`) that unifies customers, leads, and ad-hoc phone numbers into a single value object with `from_customer()`, `from_lead()`, and `from_adhoc()` factory methods.
- **Ghost_Lead**: A `Lead` row auto-created for unmatched ad-hoc phone numbers from CSV uploads, with `lead_source='campaign_import'`, `status='new'`, `sms_consent=false`.
- **Consent_Record**: An `SmsConsentRecord` row — the authoritative consent audit trail keyed by phone number (E.164). Consulted on ALL send paths.
- **Campaign_Recipient**: A row in the `campaign_recipients` table linking a `Campaign` to a specific recipient with `delivery_status`, `sent_at`, `error_message`, and FKs to both `customer_id` and `lead_id`.
- **Sent_Message**: A row in the `sent_messages` table recording every outbound SMS with FKs to `customer_id`, `lead_id`, `job_id`, `appointment_id`, delivery status, and provider message ID.
- **Target_Audience**: A JSONB field on `Campaign` defining the audience filter with three top-level keys: `customers`, `leads`, `ad_hoc`.
- **Audience_Builder**: The frontend component (step 1 of the campaign wizard) that lets staff build a mixed-source recipient list from customers, leads, and ad-hoc CSV uploads.
- **Message_Composer**: The frontend component (step 2 of the campaign wizard) for template editing with merge fields, character counter, and live preview.
- **Campaign_Review**: The frontend component (step 3 of the campaign wizard) showing final recipient count, estimated completion time, and send/schedule options.
- **Time_Window**: The 8AM–9PM Central Time window enforced for all automated SMS sends.
- **10DLC**: 10-Digit Long Code — the US carrier registration requirement for A2P (application-to-person) SMS. Unregistered messages are blocked outright by carriers in 2026.
- **E164_Format**: The international phone number format (`+19525293750`) used for all phone storage and API calls.
- **Merge_Field**: A placeholder token in message templates (e.g., `{first_name}`, `{last_name}`) that is replaced with recipient-specific values at send time.
- **STOP_Keywords**: The set of opt-out keywords (STOP, CANCEL, UNSUBSCRIBE, QUIT, END) that trigger automatic consent revocation.
- **Sender_Prefix**: The required identification string ("Grins Irrigation:") prepended to every outbound SMS for compliance.
- **Background_Worker**: The APScheduler interval job (`process_pending_campaign_recipients`) that runs every 60 seconds to drain pending campaign recipients under rate limits.
- **CSV_Blast_Script**: The one-off admin script (`scripts/send_callrail_campaign.py`) for the interim 300-customer scheduling outreach with dry-run mode.
- **DI_Helper**: The dependency injection helper (`api/dependencies.py`) that wires `SMSService` and `EmailService` into `CampaignService` for FastAPI route injection.

## Requirements


### Requirement 1: SMS Provider Abstraction (Strategy Pattern)

**User Story:** As a developer, I want a pluggable SMS provider abstraction so that the platform can switch between CallRail, Twilio, and a test provider without changing business logic.

#### Acceptance Criteria

1. THE Platform SHALL define a `BaseSMSProvider` Protocol with methods: `send_text(to: str, body: str) -> ProviderSendResult`, `verify_webhook_signature(headers, raw_body) -> bool`, `parse_inbound_webhook(payload: dict) -> InboundSMS`, and a `provider_name` property.
2. THE Platform SHALL implement `CallRailProvider`, `TwilioProvider`, and `NullProvider` classes that conform to the `BaseSMSProvider` Protocol.
3. THE Provider_Factory SHALL read the `SMS_PROVIDER` environment variable and return the corresponding SMS_Provider instance (`callrail`, `twilio`, or `null`).
4. WHEN `SMS_PROVIDER` is not set, THE Provider_Factory SHALL default to `callrail`.
5. THE SMS_Service SHALL accept an SMS_Provider via its constructor and delegate all provider-specific operations to the injected provider.
6. THE SMS_Service SHALL rename `_send_via_twilio()` to `_send_via_provider()` and delegate to the injected provider's `send_text()` method.
7. THE Platform SHALL organize the provider package at `src/grins_platform/services/sms/` with files: `__init__.py`, `base.py`, `callrail_provider.py`, `twilio_provider.py`, `null_provider.py`, `factory.py`, `rate_limiter.py`, `templating.py`, `recipient.py`, `ghost_lead.py`.
8. THE `TwilioProvider` SHALL port the current `_send_via_twilio()` stub verbatim with no behavior change.
9. THE `NullProvider` SHALL record all send attempts in memory and return synthetic success results for use in tests and dry-run mode.
10. WHEN the `SMS_PROVIDER` env var is changed and the backend is restarted, THE Platform SHALL route all SMS through the new provider with zero code changes (Twilio swap procedure).

### Requirement 2: CallRail HTTP Client

**User Story:** As a developer, I want a thin async HTTP client for the CallRail REST API so that the platform can send outbound SMS, list tracking numbers, and verify inbound webhook signatures.

#### Acceptance Criteria

1. THE CallRail_Client SHALL use `httpx.AsyncClient` to communicate with the CallRail REST API at base URL `https://api.callrail.com/v3/`.
2. THE CallRail_Client SHALL authenticate using the `Authorization: Token token="YOUR_API_KEY"` header, reading `CALLRAIL_API_KEY` from environment variables.
3. WHEN `send_text(to, body)` is called, THE CallRail_Client SHALL POST to `/v3/a/{account_id}/text-messages.json` with body fields `company_id` (from `CALLRAIL_ACCOUNT_ID`), `tracking_number` (from `CALLRAIL_TRACKING_NUMBER`), `customer_phone_number` (the `to` parameter), and `content` (the `body` parameter).
4. THE CallRail_Client SHALL read `CALLRAIL_ACCOUNT_ID` (`ACC019c31a27df478178fe0f381d863bf7d`), `CALLRAIL_COMPANY_ID` (`COM019c31a27f5b732b9d214e04eaa3061f`), and `CALLRAIL_TRACKING_NUMBER` (`+19525293750`) from environment variables.
5. IF the CallRail API returns a 401 status, THEN THE CallRail_Client SHALL raise a typed `CallRailAuthError` exception.
6. IF the CallRail API returns a 429 status, THEN THE CallRail_Client SHALL raise a typed `CallRailRateLimitError` exception with the `retry_after` value from the response headers.
7. IF the CallRail API returns a 422 or 400 status, THEN THE CallRail_Client SHALL raise a typed `CallRailValidationError` exception with the error details from the response body.
8. THE CallRail_Client SHALL use structured logging via `LoggerMixin` for all API calls, errors, and retries.
9. THE CallRail_Client SHALL store the CallRail message ID from successful send responses in the existing `twilio_sid` column of `SentMessage` (to be renamed to `provider_message_id` in Phase 7).
10. THE CallRail_Client SHALL provide a `list_tracking_numbers()` method that calls `GET /v3/a/{account_id}/trackers.json` and returns a list of tracking numbers.

### Requirement 3: Outbound SMS Rate Limiter

**User Story:** As a developer, I want a rate limiter that enforces CallRail's outbound SMS caps so that the platform never exceeds 150 sends/hour or 1,000 sends/day.

#### Acceptance Criteria

1. THE Rate_Limiter SHALL enforce two simultaneous sliding windows: 150 sends per hour AND 1,000 sends per day, per provider account.
2. THE Rate_Limiter SHALL be backed by Redis (already running in the platform for middleware rate limiting).
3. THE Rate_Limiter SHALL key counters by `(provider_name, account_id)` so that CallRail and Twilio counters do not interfere with each other.
4. WHEN `acquire()` is called and both windows have capacity, THE Rate_Limiter SHALL return `(allowed=True, retry_after_seconds=0)`.
5. WHEN `acquire()` is called and either window is exhausted, THE Rate_Limiter SHALL return `(allowed=False, retry_after_seconds=N)` where N is the number of seconds until the next send slot opens.
6. WHEN the Rate_Limiter denies a send, THE SMS_Service SHALL persist the message with `delivery_status='scheduled'` and `scheduled_for=now + retry_after_seconds`.
7. THE Rate_Limiter SHALL hard-cap daily sends at 1,000 to prevent cost surprises.

### Requirement 4: Unified Recipient Model

**User Story:** As a developer, I want a unified Recipient abstraction so that all SMS send paths can handle customers, leads, and ad-hoc phone numbers uniformly without source-specific branching.

#### Acceptance Criteria

1. THE Platform SHALL define a frozen `Recipient` dataclass with fields: `phone` (E.164, required), `source_type` (literal: "customer", "lead", "ad_hoc"), `customer_id` (UUID, optional), `lead_id` (UUID, optional), `first_name` (optional), `last_name` (optional).
2. THE Recipient SHALL provide a `from_customer(customer)` class method that creates a Recipient with `source_type="customer"` and `customer_id` set.
3. THE Recipient SHALL provide a `from_lead(lead)` class method that creates a Recipient with `source_type="lead"` and `lead_id` set.
4. THE Recipient SHALL provide a `from_adhoc(phone, first_name, last_name)` class method that creates a Ghost_Lead row and returns a Recipient with `source_type="ad_hoc"` and `lead_id` set to the ghost lead's ID.
5. THE SMS_Service SHALL accept a `Recipient` parameter instead of `customer_id` in `send_message()`.
6. WHEN persisting a Sent_Message, THE SMS_Service SHALL populate `customer_id` or `lead_id` based on the Recipient's `source_type`, preserving the existing check constraint (`customer_id IS NOT NULL OR lead_id IS NOT NULL`).
7. THE Platform SHALL update ALL existing callers of `SMSService.send_message()` to pass `Recipient.from_customer(...)`: `api/v1/sms.py` send + send-bulk endpoints, appointment reminder call sites, invoice notification call sites, and `notification_service.py`.
8. THE Campaign_Service SHALL refactor `_send_to_recipient()` to accept a `Recipient` instead of a `Customer`, populating `CampaignRecipient.customer_id` or `lead_id` based on `recipient.source_type`.

### Requirement 5: Ghost Lead Creation for Ad-Hoc Phones

**User Story:** As a staff member, I want unmatched phone numbers from CSV uploads to automatically become trackable leads so that every SMS is tied to a CRM entity and ad-hoc contacts can be followed up on later.

#### Acceptance Criteria

1. WHEN an ad-hoc phone number from a CSV upload does not match any existing Customer or Lead, THE Platform SHALL auto-create a `Lead` row with: `phone` (normalized to E.164), `name` (from CSV if present, else empty string), `lead_source='campaign_import'`, `status='new'`, `sms_consent=false`, `source_site='campaign_csv_import'`.
2. THE `ghost_lead.create_or_get(phone, first_name, last_name)` helper SHALL normalize the phone to E.164 and deduplicate by phone — returning the existing Lead if one already exists with that phone number.
3. THE Ghost_Lead creation SHALL preserve the `SentMessage` check constraint (`customer_id IS NOT NULL OR lead_id IS NOT NULL`) with zero schema migration.
4. WHEN staff view the Leads list, THE Platform SHALL allow filtering by `lead_source='campaign_import'` so ghost leads can be separated from organic leads.
5. THE Consent_Record tracking (phone-keyed via `SmsConsentRecord`) SHALL work identically for ghost leads as for customers and organic leads.

### Requirement 6: Blocker Fix — CampaignService Dependency Injection (B1)

**User Story:** As a developer, I want `CampaignService` to receive its `SMSService` and `EmailService` dependencies via injection so that campaign sends actually dispatch SMS messages.

#### Acceptance Criteria

1. THE Platform SHALL create a DI_Helper in `api/dependencies.py` (e.g., `get_campaign_service()`) that wires `SMSService(db)` and `EmailService(db)` into `CampaignService`.
2. THE `api/v1/campaigns.py` route SHALL use the DI_Helper instead of instantiating `CampaignService(campaign_repository=repo)` without service dependencies.
3. WHEN `POST /v1/campaigns/{id}/send` is called, THE Campaign_Service SHALL have a non-None `sms_service` and the SMS path in `_send_to_recipient()` SHALL execute.

### Requirement 7: Blocker Fix — Consent Check Centralization (B2)

**User Story:** As a compliance officer, I want every SMS send path to consult `SmsConsentRecord` so that customers who replied STOP are never texted by any campaign, preventing TCPA violations.

#### Acceptance Criteria

1. THE SMS_Service SHALL call `check_sms_consent(phone)` before every provider dispatch — for automated, manual, and campaign sends without exception.
2. THE Campaign_Service SHALL remove the direct read of `Customer.sms_opt_in` that bypasses `SmsConsentRecord` in the campaign send loop.
3. WHEN a customer has an `SmsConsentRecord` row indicating opt-out, THE SMS_Service SHALL refuse to send regardless of the value of `Customer.sms_opt_in` or `Lead.sms_consent`.
4. THE consent check SHALL be phone-keyed (E.164) so it works uniformly for customers, leads, and ad-hoc recipients.

### Requirement 8: Blocker Fix — Async Bulk Send with Queuing (B3)

**User Story:** As a developer, I want `POST /sms/send-bulk` to enqueue recipients for background processing so that bulk sends respect rate limits and do not block the HTTP request thread.

#### Acceptance Criteria

1. WHEN `POST /sms/send-bulk` is called, THE Platform SHALL persist recipients as `CampaignRecipient` rows with `delivery_status='pending'` and return HTTP 202 immediately.
2. THE Background_Worker SHALL drain pending recipients under the Rate_Limiter's constraints (150/hr + 1,000/day).
3. THE Platform SHALL NOT iterate recipients synchronously in the HTTP request thread.
4. WHEN `POST /v1/campaigns/{id}/send` is called, THE Platform SHALL enqueue recipients for background processing instead of blocking.

### Requirement 9: CallRail Inbound Webhook

**User Story:** As a staff member, I want inbound SMS replies from customers to land in the CRM inbox so that STOP replies are processed for compliance and scheduling requests are not missed.

#### Acceptance Criteria

1. THE Platform SHALL expose a `POST /v1/webhooks/callrail/inbound` route that accepts CallRail's inbound SMS payload format.
2. WHEN an inbound webhook is received, THE Platform SHALL verify the webhook signature via `CallRailProvider.verify_webhook_signature(headers, raw_body)`.
3. IF signature verification fails, THEN THE Platform SHALL return HTTP 403 and log the rejection.
4. WHEN a valid inbound SMS is received, THE Platform SHALL parse the CallRail payload via `CallRailProvider.parse_inbound_webhook(payload)` and pass the result to `SMSService.handle_inbound(from_phone, body, provider_sid)`.
5. THE existing `handle_inbound()` logic (STOP/informal opt-out detection, `SmsConsentRecord` creation, forward-to-admin) SHALL process CallRail inbound messages identically to Twilio inbound messages.
6. THE CallRail inbound webhook route SHALL ship with Phase 1 — otherwise STOP replies are lost and opt-out compliance is violated.

### Requirement 10: Background Campaign Worker

**User Story:** As a developer, I want a background job that drains pending campaign recipients at a throttled rate so that campaigns complete reliably without exceeding rate limits or losing progress on restart.

#### Acceptance Criteria

1. THE Platform SHALL add a `process_pending_campaign_recipients` APScheduler interval job that runs every 60 seconds.
2. WHEN the job ticks, THE Background_Worker SHALL poll `campaign_recipients WHERE delivery_status='pending'` and send up to N recipients per tick (N chosen to stay under 140/hr effective rate).
3. FOR EACH recipient, THE Background_Worker SHALL perform: consent check → time-window check → `SMSService.send_message()` → update `CampaignRecipient.delivery_status` + create `SentMessage` row.
4. THE Background_Worker SHALL be resumable on crash — state is DB-persistent via `delivery_status`, not step-counter based.
5. THE Background_Worker SHALL emit progress events readable by the existing `CommunicationsQueue` frontend component.
6. THE Background_Worker SHALL honor `Campaign.scheduled_at` for future sends — campaigns scheduled for a future time SHALL NOT begin sending until that time arrives.
7. THE Background_Worker SHALL respect the 8AM–9PM CT Time_Window for all automated sends.

### Requirement 11: Compliance — 10DLC, Sender ID, and Opt-Out

**User Story:** As a compliance officer, I want every outbound SMS to comply with 2026 US carrier regulations so that messages are delivered successfully and the business avoids fines.

#### Acceptance Criteria

1. THE Platform SHALL verify 10DLC registration on the Grins CallRail account for `(952) 529-3750` before any production sends. (VERIFIED COMPLETE: brand registered via API, campaign-level registration confirmed in CallRail Compliance Home dashboard.)
2. THE Platform SHALL prepend the Sender_Prefix ("Grins Irrigation:") to every outbound SMS message.
3. THE Platform SHALL include opt-out language in every outbound SMS. Approved STOP_Keywords: STOP, CANCEL, UNSUBSCRIBE, QUIT, END.
4. WHEN an inbound message contains any STOP_Keyword, THE SMS_Service SHALL immediately create an `SmsConsentRecord` opt-out row and send a confirmation reply.
5. THE Platform SHALL enforce the 8AM–9PM CT Time_Window for all automated sends via `enforce_time_window()`. Messages outside the window SHALL be deferred to 8AM CT the next day.
6. THE Platform SHALL consult `SmsConsentRecord` on ALL send paths — automated, manual, campaign, and script — before any provider dispatch.
7. IF 10DLC is not registered, THEN THE Platform SHALL fail loudly at startup with a health check error rather than silently failing to deliver messages.

### Requirement 12: CSV Blast Script (Interim 300-Customer Outreach)

**User Story:** As an admin, I want a one-off CLI script to send throttled SMS to ~300 customers from a CSV file so that the scheduling outreach can happen immediately before the full UI is built.

#### Acceptance Criteria

1. THE CSV_Blast_Script SHALL read a CSV file with columns: `phone`, `first_name`, `last_name`.
2. THE CSV_Blast_Script SHALL read the message template from a file or CLI argument.
3. THE CSV_Blast_Script SHALL support a dry-run mode that prints every rendered message without sending — dry-run SHALL be run first for owner review.
4. THE CSV_Blast_Script SHALL support a live mode activated with a `--confirm` flag.
5. WHEN running in live mode, THE CSV_Blast_Script SHALL throttle sends at ~140/hour to stay under the 150/hr rate limit.
6. THE CSV_Blast_Script SHALL skip recipients who have opted out (via `SmsConsentRecord`).
7. THE CSV_Blast_Script SHALL persist every send attempt as a `SentMessage` row tied to the matched customer or ghost lead.
8. THE CSV_Blast_Script SHALL write progress logs to stdout.
9. THE CSV_Blast_Script SHALL report any phone numbers that cannot be normalized to E.164 format.
10. THE CSV_Blast_Script SHALL be located at `scripts/send_callrail_campaign.py`.

### Requirement 13: Audience Filter Extensions (Multi-Source)

**User Story:** As a staff member, I want to build campaign audiences from customers, leads, and ad-hoc CSV uploads with rich filters so that I can target the right recipients for each campaign.

#### Acceptance Criteria

1. THE Campaign_Service SHALL refactor `_filter_recipients()` to return `list[Recipient]` from a UNION of Customer + Lead + ad-hoc sources.
2. THE Target_Audience JSON schema SHALL support three top-level keys: `customers`, `leads`, `ad_hoc`.
3. THE `customers` filter SHALL support: `sms_opt_in`, `ids_include`, `cities`, `last_service_between`, `tags_include`, `lead_source`, `is_active`, `no_appointment_in_days`.
4. THE `leads` filter SHALL support: `sms_consent`, `ids_include`, `statuses` (new/contacted/qualified), `lead_source`, `intake_tag`, `action_tags_include`, `cities`, `created_between`.
5. THE `ad_hoc` filter SHALL support: `csv_upload_id` pointing to a staged upload; the resolver SHALL create ghost leads on the fly at send time (not at upload time).
6. THE Campaign_Service SHALL deduplicate by E.164 phone across all three sources — if a phone appears as both a customer and a lead, the customer record SHALL win.
7. THE Platform SHALL schema-validate `target_audience` in `CampaignCreate` via Pydantic.
8. THE Platform SHALL expose `POST /campaigns/audience/preview` that accepts a `target_audience` dict and returns: total count, per-source breakdown, and first 20 matches with name/phone/source.
9. THE Platform SHALL expose `POST /campaigns/audience/csv` that uploads a CSV, stages it, and returns: `upload_id`, matched/unmatched/duplicate breakdown. Ghost leads SHALL NOT be created until final send.

### Requirement 14: Merge-Field Templating

**User Story:** As a staff member, I want to personalize SMS messages with recipient-specific fields like first name and last name so that outreach feels personal rather than generic.

#### Acceptance Criteria

1. THE Platform SHALL provide a `render_template(body, context)` utility in `services/sms/templating.py` using `str.format_map()` with a safe default dict.
2. WHEN a merge field key is missing from the context, THE templating utility SHALL render it as an empty string rather than raising a `KeyError`.
3. THE Platform SHALL support merge fields: `{first_name}`, `{last_name}`.
4. THE Background_Worker SHALL render the template per recipient before the provider call.
5. THE templating utility SHALL NOT use Jinja, conditionals, or loops — it SHALL remain a simple key-value substitution.

### Requirement 15: Communications Tab — New Text Campaign Wizard

**User Story:** As a staff member, I want to build an audience, compose a message, preview it, and launch a throttled send from the Communications tab so that I can run SMS campaigns without developer assistance.

#### Acceptance Criteria

1. THE Platform SHALL add a primary "New Text Campaign" button to the Communications page.
2. WHEN the "New Text Campaign" button is clicked, THE Platform SHALL open a `NewTextCampaignModal` — a 3-step wizard using shadcn Dialog.
3. THE Audience_Builder (step 1) SHALL provide three additive source panels that can all be used in one campaign:
   - Customers panel: search + filter (SMS opt-in default on, city, last service date range, tags, lead source) + multi-select table with checkboxes showing selected count.
   - Leads panel: search + filter (SMS consent default on, status, lead source, intake tag, city, created date) + multi-select table showing selected count.
   - Ad-hoc panel: CSV upload (columns: `phone`, `first_name`, `last_name`) OR paste phones directly, showing matched-to-customer / matched-to-lead / new (will become ghost lead) breakdown.
4. THE Audience_Builder SHALL display a running total: "X customers + Y leads + Z ad-hoc = N total recipients (M after consent filter)".
5. THE Audience_Builder SHALL support pass-through for `ids_include` when opened from the Customers tab or Leads tab (pre-populating the correct panel).
6. THE Audience_Builder SHALL show a dedupe warning when a phone appears in multiple sources ("N phones are in both your Customers selection and your CSV — they'll only be texted once").
7. THE Audience_Builder SHALL display a live preview count via `POST /campaigns/audience/preview`.
8. THE Message_Composer (step 2) SHALL provide a template textarea with merge-field insertion buttons (`{first_name}`, `{last_name}`).
9. THE Message_Composer SHALL display a character counter and SMS segment count.
10. THE Message_Composer SHALL show a live preview panel with the auto-appended STOP footer and "Grins Irrigation:" Sender_Prefix.
11. THE Campaign_Review (step 3) SHALL show: recipient count after consent filter, estimated completion time (recipients ÷ 140/hr), and options to send now (respecting Time_Window) or schedule for a specific date/time.
12. WHEN the user confirms, THE Platform SHALL create `Campaign` + `CampaignRecipient` rows and enqueue a background job.
13. THE Platform SHALL add a third tab to `CommunicationsDashboard`: "Campaigns" showing active/scheduled/completed campaigns with progress bars.

### Requirement 16: Customers Tab and Leads Tab Bulk SMS Entry Points

**User Story:** As a staff member, I want to select multiple customers or leads from their respective list views and launch a text campaign so that I can quickly reach specific groups without switching to the Communications tab.

#### Acceptance Criteria

1. THE Platform SHALL add a checkbox column to `CustomerList.tsx` via TanStack Table's row-selection API.
2. WHEN one or more customers are selected, THE Platform SHALL display a sticky bulk-action bar with a "Text Selected" button.
3. WHEN "Text Selected" is clicked on the Customers tab, THE Platform SHALL open `NewTextCampaignModal` with the selected customer IDs pre-loaded into the Customers panel of the Audience_Builder.
4. THE Platform SHALL add a checkbox column and bulk-action bar to the Leads list (`LeadsList.tsx`).
5. WHEN "Text Selected" is clicked on the Leads tab, THE Platform SHALL open `NewTextCampaignModal` with the selected lead IDs pre-loaded into the Leads panel of the Audience_Builder.
6. BOTH entry points SHALL open the same `NewTextCampaignModal`; the modal SHALL pre-select the appropriate source panel.

### Requirement 17: Twilio Swap Readiness

**User Story:** As a developer, I want the platform to support a zero-code provider swap from CallRail to Twilio so that the business can switch SMS providers by changing a single environment variable.

#### Acceptance Criteria

1. WHEN `SMS_PROVIDER=twilio` is set in `.env` and the backend is restarted, THE Provider_Factory SHALL return a `TwilioProvider` instance.
2. THE Rate_Limiter SHALL automatically namespace counters by `provider_name` so CallRail's counters do not leak into Twilio's window.
3. THE Platform SHALL document the Twilio swap procedure in `README.md`: verify Twilio 10DLC, set env vars (`SMS_PROVIDER=twilio`, `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER`), update Twilio inbound webhook URL, restart backend, smoke test.
4. THE swap SHALL require zero changes to `SMSService`, `CampaignService`, Communications UI, or any business logic.

### Requirement 18: Environment Configuration

**User Story:** As a developer, I want all CallRail and provider configuration managed via environment variables so that secrets are never committed and provider switching is a config-only change.

#### Acceptance Criteria

1. THE Platform SHALL update `.env.example` with placeholder entries: `SMS_PROVIDER=`, `CALLRAIL_API_KEY=`, `CALLRAIL_ACCOUNT_ID=`, `CALLRAIL_COMPANY_ID=`, `CALLRAIL_TRACKING_NUMBER=`, and document that `TWILIO_*` vars become optional.
2. THE Platform SHALL read all CallRail credentials from environment variables at runtime — `CALLRAIL_API_KEY`, `CALLRAIL_ACCOUNT_ID`, `CALLRAIL_COMPANY_ID`, `CALLRAIL_TRACKING_NUMBER`.
3. THE Platform SHALL add an `SMS_PROVIDER` env var that defaults to `callrail`.
4. THE Platform SHALL never commit API keys, secrets, or real credential values into tracked files.

### Requirement 19: Consent Field Unification

**User Story:** As a developer, I want the consent field naming asymmetry between `Customer.sms_opt_in` and `Lead.sms_consent` handled at the service layer so that downstream code never sees the inconsistency.

#### Acceptance Criteria

1. THE Campaign_Service `_filter_recipients()` SHALL map both `Customer.sms_opt_in` and `Lead.sms_consent` to a single boolean when building Recipient objects.
2. THE `Customer.sms_opt_in` and `Lead.sms_consent` model fields SHALL remain as-is with no migration required.
3. THE Recipient dataclass SHALL NOT expose the source-specific consent field name — all consent checking SHALL go through `SmsConsentRecord` (phone-keyed).

### Requirement 20: Phone Number Normalization

**User Story:** As a developer, I want all phone numbers normalized to E.164 format before any SMS operation so that sends do not fail due to format inconsistencies.

#### Acceptance Criteria

1. THE Platform SHALL normalize all phone numbers to E164_Format (`+1XXXXXXXXXX`) before any provider call, consent check, or deduplication operation.
2. THE CSV_Blast_Script SHALL report any phone numbers that cannot be normalized to E.164 format and skip them.
3. THE Ghost_Lead helper SHALL normalize the phone to E.164 before creating or looking up a Lead row.
4. THE Audience_Builder CSV upload SHALL validate and normalize phone numbers, reporting invalid entries to the user.

### Requirement 21: Campaign Resilience and Error Handling

**User Story:** As a developer, I want campaigns to be resilient to API outages and restartable after crashes so that partial sends complete reliably.

#### Acceptance Criteria

1. THE Background_Worker SHALL be status-driven (using `delivery_status` on `CampaignRecipient`) so that progress is DB-persistent and restarts are safe.
2. WHEN a send fails due to a provider error, THE Background_Worker SHALL retry the send up to N times with exponential backoff.
3. IF the CallRail API returns a 429 rate-limit error, THEN THE Background_Worker SHALL respect the `retry_after` value and pause sending.
4. THE Background_Worker SHALL update `CampaignRecipient.delivery_status` and `CampaignRecipient.error_message` for every send attempt (success or failure).
5. WHEN all recipients in a campaign have been processed (sent, failed after max retries, or skipped due to consent), THE Background_Worker SHALL update `Campaign.status` to `'completed'`.

### Requirement 22: Key Files to Create

**User Story:** As a developer, I want a clear manifest of all new files and edits required so that implementation is traceable and complete.

#### Acceptance Criteria

1. THE Platform SHALL create the following backend provider package files: `services/sms/__init__.py`, `services/sms/base.py`, `services/sms/callrail_provider.py`, `services/sms/twilio_provider.py`, `services/sms/null_provider.py`, `services/sms/factory.py`, `services/sms/rate_limiter.py`, `services/sms/templating.py`, `services/sms/recipient.py`, `services/sms/ghost_lead.py`.
2. THE Platform SHALL create `api/dependencies.py` as the DI_Helper for wiring services.
3. THE Platform SHALL add the CallRail inbound webhook route to `api/v1/webhooks.py`.
4. THE Platform SHALL add audience preview and CSV upload endpoints to `api/v1/campaigns.py`.
5. THE Platform SHALL create `scripts/send_callrail_campaign.py` as the CSV_Blast_Script.
6. THE Platform SHALL create the following frontend files: `NewTextCampaignModal.tsx`, `AudienceBuilder.tsx`, `MessageComposer.tsx`, `CampaignReview.tsx`, `CampaignsList.tsx`, and hooks (`useCreateCampaign.ts`, `useSendCampaign.ts`, `useAudiencePreview.ts`, `useAudienceCsv.ts`, `useCampaignProgress.ts`), API client (`campaignsApi.ts`), and types (`campaign.ts`) in `frontend/src/features/communications/`.
7. THE Platform SHALL edit `CustomerList.tsx` to add checkbox column + bulk-action bar.
8. THE Platform SHALL edit `LeadsList.tsx` to add checkbox column + bulk-action bar.

### Requirement 23: Minor Gaps and Future Improvements

**User Story:** As a developer, I want minor gaps documented for future phases so that they are tracked but do not block the MVP.

#### Acceptance Criteria

1. THE Platform SHALL rename `SentMessage.twilio_sid` to `provider_message_id` in a Phase 7 migration (M3).
2. THE Platform SHALL introduce `pydantic-settings` for typed config in `config/settings.py` in Phase 7 (M1).
3. THE Platform SHALL honor `Campaign.scheduled_at` in the Background_Worker — this is automatically fixed by the Phase 3 interval job (M5).
4. WHERE a runtime provider toggle is needed in the future, THE Platform SHALL add a `BusinessSetting` key `sms_provider` + admin Settings UI toggle (M2 — skip for MVP, env-var swap is sufficient).
5. THE Platform SHALL add a `POST /campaigns/audience/csv` endpoint for CSV upload in Phase 4 (M4).

### Requirement 24: Blocker Fix — Campaign-Scoped Dedupe (B4)

**User Story:** As a developer, I want campaign sends to bypass the 24-hour message-type dedupe so that back-to-back campaigns and retry-failed flows do not silently fail.

#### Acceptance Criteria

1. THE SMS_Service `send_message()` SHALL accept an optional `campaign_id: UUID | None = None` parameter.
2. WHEN `campaign_id` is set, THE SMS_Service SHALL scope the dedupe query to `(recipient, campaign_id)` rather than `(customer_id, message_type)`.
3. WHEN `campaign_id` is None, THE SMS_Service SHALL preserve the existing 24-hour `(customer_id, message_type)` dedupe behavior for non-campaign sends (appointment reminders, etc.).
4. THE Campaign_Recipient state machine (see Requirement 28) SHALL additionally enforce per-recipient-per-campaign dedupe: a row in state `sent` or `sending` SHALL NOT be re-picked by the worker.
5. WHEN two different campaigns target the same recipient within 24 hours, BOTH campaigns SHALL succeed.
6. WHEN the same campaign attempts to send to the same recipient twice, the second attempt SHALL be blocked by the state machine, not by the dedupe.
7. THE Platform SHALL add a Phase 1 Alembic migration to add a `campaign_id` UUID FK column to `sent_messages` (nullable, indexed) if not already present.

### Requirement 25: Staff Attestation for Ad-Hoc CSV Consent (S10)

**User Story:** As a compliance officer, I want CSV uploads of ad-hoc phone numbers to require staff attestation so that ad-hoc recipients have a documented consent record before any SMS is sent.

#### Acceptance Criteria

1. THE Audience_Builder CSV upload UI SHALL display a staff attestation checkbox with text: "I confirm that every contact in this file has an established business relationship with Grins Irrigation and has consented to receive SMS from us. I understand this attestation is logged and auditable."
2. THE Platform SHALL disable the CSV upload "Confirm" button until the attestation checkbox is checked.
3. WHEN staff confirm the CSV upload, THE Platform SHALL auto-create an `SmsConsentRecord` row per distinct E.164 phone number in the upload batch with: `consent_type='marketing'`, `consent_given=true`, `consent_method='csv_upload_staff_attestation'`, `consent_language_shown=<verbatim attestation text>`, `consent_form_version='CSV_ATTESTATION_V1'`, `consent_timestamp=now()`, `created_by_staff_id=<uploading staff user id>`, `customer_id` OR `lead_id` populated after ghost lead creation.
4. THE Platform SHALL add a Phase 1 Alembic migration to add `created_by_staff_id` UUID FK column (nullable) to `sms_consent_records`.
5. THE Platform SHALL emit an `sms.csv_attestation.submitted` audit log event with actor, upload_id, phone count, and attestation version.
6. THE Platform SHALL store the exact attestation language verbatim as `consent_language_shown` so it is auditable even if future UI text changes.

### Requirement 26: Type-Scoped Consent Semantics (S11)

**User Story:** As a compliance officer, I want consent checks to distinguish marketing from transactional from operational messages so that a STOP to a marketing blast does not silently block appointment reminders.

#### Acceptance Criteria

1. THE Platform SHALL define three `consent_type` values: `marketing`, `transactional`, `operational`.
2. WHERE a message is `marketing` (campaigns, promos, newsletters), THE SMS_Service SHALL require explicit opt-in via form consent, START keyword, or CSV staff attestation.
3. WHERE a message is `transactional` (appointment reminders, confirmations, invoices, on-the-way, completion), THE SMS_Service SHALL allow sending under the TCPA "established business relationship" exemption without explicit marketing opt-in.
4. WHERE a message is `operational` (STOP confirmations, legally-required notices), THE SMS_Service SHALL always allow sending.
5. THE `check_sms_consent(phone, consent_type)` function SHALL implement hard-STOP precedence: if any `SmsConsentRecord` row exists for the phone with `consent_method='text_stop'` and `consent_given=false`, deny ALL outbound sends except `operational`.
6. WHERE the message is `marketing` and no hard-STOP exists, THE SMS_Service SHALL require either a recent `marketing`-type `SmsConsentRecord` with `consent_given=true` OR a fallback boolean match on `Customer.sms_opt_in=true` or `Lead.sms_consent=true`.
7. THE SMS_Service `send_message()` SHALL accept an optional `consent_type` parameter (defaulting to `transactional` for safety).
8. Campaign sends SHALL pass `consent_type='marketing'`; STOP confirmations SHALL pass `consent_type='operational'`; all other business flows SHALL pass `consent_type='transactional'`.

### Requirement 27: Delivery Status — `sent` Is Terminal (S12 resolved)

**User Story:** As a product owner, I want the system to accurately reflect that we cannot track delivery to the handset so that staff and customers are not misled by false "Delivered" labels.

#### Acceptance Criteria

1. THE Platform SHALL treat `sent` as the terminal happy state for outbound SMS. No `sent → delivered` transition exists.
2. THE UI SHALL use the label **"Sent"** and SHALL NOT use "Delivered" or "Received" anywhere in the campaign or message history views.
3. THE Platform SHALL show a tooltip on the "Sent" badge explaining: "Handed off to CallRail successfully. Delivery to the recipient's handset is not tracked."
4. THE Platform SHALL NOT expose any `POST /webhooks/callrail/delivery-status` route since CallRail does not emit delivery callbacks (verified 2026-04-07).
5. WHERE a future CallRail API version adds delivery callbacks, THE Platform SHALL treat it as an additive, non-breaking enhancement — no redesign required.
6. THE `CampaignRecipient.delivery_status` enum SHALL include `pending`, `sending`, `sent`, `failed`, `cancelled` — but NOT `delivered`.

### Requirement 28: Recipient State Machine and Orphan Recovery (S13)

**User Story:** As a developer, I want an explicit recipient state machine with orphan recovery so that worker crashes mid-send do not cause duplicate messages to the same recipient.

#### Acceptance Criteria

1. THE Platform SHALL define the `RecipientState` enum with values: `pending`, `sending`, `sent`, `failed`, `cancelled`.
2. THE Platform SHALL implement the following allowed transitions (all others raise `InvalidStateTransitionError`):
   - `pending → sending` (worker picks recipient)
   - `pending → cancelled` (campaign cancelled by staff)
   - `sending → sent` (provider returned 200)
   - `sending → failed` (provider error, consent denied, or time-window blocked)
   - `sending → cancelled` (admin force-cancel)
   - `sending → failed (worker_interrupted)` (orphan recovery — stuck >5 min)
   - `failed → pending` (manual retry — creates a new row; original stays for audit)
3. `sent` and `cancelled` are terminal — transitions OUT of them are forbidden.
4. THE Background_Worker SHALL transition `pending → sending` and record `sending_started_at` BEFORE calling the provider.
5. ON WORKER STARTUP and on each interval tick BEFORE claiming new work, THE Background_Worker SHALL run an orphan recovery query: `UPDATE campaign_recipients SET delivery_status='failed', error_message='worker_interrupted' WHERE delivery_status='sending' AND sending_started_at < now() - interval '5 minutes'`.
6. WHERE concurrent workers exist, THE Background_Worker SHALL use `SELECT ... FOR UPDATE SKIP LOCKED` when claiming `pending` rows to prevent double-claim.
7. THE Platform SHALL add a Phase 1 Alembic migration to add `sending_started_at TIMESTAMPTZ` column (nullable, indexed) to `campaign_recipients`.
8. THE Platform SHALL expose "Retry selected" and "Cancel campaign" actions in the Phase 5 UI that transition recipients through the allowed states only.

### Requirement 29: Locked Policy Decisions Reference

**User Story:** As a developer reading this spec for the first time, I want a single place to see all policy decisions locked in so that I don't need to re-derive them from scattered discussion.

#### Acceptance Criteria

1. THE Platform SHALL document and implement all eight locked policy decisions:
   - **C1 / B4:** Campaign sends pass `campaign_id` to `send_message()`, dedupe scoped to `(recipient, campaign_id)` — see Requirement 24.
   - **C3 / S10:** Staff attestation model for ad-hoc CSV consent — see Requirement 25.
   - **C4 / S11:** Three consent types (`marketing`/`transactional`/`operational`), hard-STOP precedence — see Requirement 26.
   - **C5 / S12:** CallRail has no delivery callbacks; `sent` is terminal — see Requirement 27.
   - **C6:** `CALLRAIL_WEBHOOK_SECRET` env var, manual dashboard paste per environment, Redis idempotency dedupe on conversation ID — see Requirement 30.
   - **C7:** Admin/Manager/Technician RBAC with 50-recipient threshold — see Requirement 31.
   - **C8 / S13:** Explicit `pending → sending → sent/failed/cancelled` state machine with orphan recovery — see Requirement 28.
   - **H1:** CT-only time window for MVP, UI warns on non-CT area codes, per-recipient TZ enforcement deferred — see Requirement 36.

### Requirement 30: External Configuration and Deployment

**User Story:** As an operator, I want all external configuration (env vars, webhook URLs, secrets) documented and automated where possible so that deploying to a new environment does not silently fail due to missing config.

#### Acceptance Criteria

1. THE Platform SHALL document the full env var list including `SMS_PROVIDER`, `CALLRAIL_API_KEY`, `CALLRAIL_ACCOUNT_ID`, `CALLRAIL_COMPANY_ID`, `CALLRAIL_TRACKING_NUMBER`, `CALLRAIL_TRACKER_ID`, `CALLRAIL_WEBHOOK_SECRET`, `SMS_SENDER_PREFIX`, `SMS_TIME_WINDOW_TIMEZONE`, `SMS_TIME_WINDOW_START`, `SMS_TIME_WINDOW_END`.
2. THE Platform SHALL NOT require `CALLRAIL_DELIVERY_WEBHOOK_ENABLED`, `SMS_RATE_LIMIT_HOURLY`, or `SMS_RATE_LIMIT_DAILY` — these were removed after Phase 0.5 because CallRail dictates rate limits via response headers.
3. THE Platform SHALL provide a per-environment webhook URL configuration runbook at `deployment-instructions/callrail-webhook-setup.md` covering: local dev (ngrok), staging, and production URLs.
4. WHERE a webhook URL needs to be paste into the CallRail dashboard, THE runbook SHALL explicitly document the dashboard path ("CallRail → Account Settings → Integrations → Webhooks").
5. THE `POST /v1/webhooks/callrail/inbound` route SHALL verify webhook signatures using `CALLRAIL_WEBHOOK_SECRET`.
6. THE webhook route SHALL be idempotent via a Redis dedupe set keyed on `(conversation_id, created_at)` with 24h TTL. Replays of the same payload SHALL NOT cause duplicate side effects.
7. WHERE Redis is unavailable, THE webhook handler SHALL still process the payload but log a warning (preferring occasional duplicate handling to missed opt-outs).
8. WHERE the platform hostname changes, THE runbook SHALL document the procedure for updating the webhook URL in the CallRail dashboard.

### Requirement 31: Permission Matrix (RBAC)

**User Story:** As an admin, I want role-based permission enforcement on all SMS and campaign actions so that only authorized staff can send large blasts or configure provider settings.

#### Acceptance Criteria

1. THE Platform SHALL enforce the following permission matrix via FastAPI dependency functions:
   - View `SentMessagesLog`: Admin + Manager (not Technician)
   - View `CommunicationsQueue`: Admin + Manager + Technician
   - Mark inbound communication as addressed: Admin + Manager + Technician
   - View Campaigns list: Admin + Manager
   - Create campaign draft: Admin + Manager
   - Edit draft campaign: Admin + Manager (own drafts only)
   - Upload CSV audience file: **Admin only**
   - Provide CSV staff attestation: **Admin only**
   - Send campaign <50 recipients: Admin + Manager
   - Send campaign ≥50 recipients: **Admin only**
   - Schedule campaign for future: Admin + Manager (<50 recipients)
   - Cancel campaign in progress: Admin + Manager (own campaigns)
   - Retry failed recipients: Admin + Manager
   - Delete campaign (soft): Admin only
   - Change SMS provider env var: Admin only (infra-level)
   - View audit log: Admin only
   - Access worker health endpoint: Admin + Manager
2. THE Platform SHALL implement `require_admin()`, `require_admin_or_manager()`, and `require_campaign_send_authority(campaign_id)` dependency functions in `api/dependencies.py`.
3. THE `require_campaign_send_authority` dependency SHALL count recipients and enforce the 50-recipient threshold: Manager can send <50, Admin required for 50+.
4. WHERE an unauthorized role attempts a forbidden action, THE Platform SHALL return HTTP 403 with a message indicating the required role.
5. THE Platform SHALL write route-level integration tests for every permission boundary.

### Requirement 32: Monitoring, Metrics, and Alerts

**User Story:** As an operator, I want structured logging and alerts for the SMS subsystem so that silent failures and compliance issues surface promptly.

#### Acceptance Criteria

1. THE Platform SHALL emit structured log events via `LoggerMixin`:
   - `sms.send.requested` (INFO) with `provider`, `recipient_phone_masked`, `consent_type`, `campaign_id`
   - `sms.send.succeeded` (INFO) with `provider_conversation_id`, `provider_thread_id`, `latency_ms`, `hourly_remaining`, `daily_remaining`
   - `sms.send.failed` (WARN/ERROR) with `error_code`, `error_message`, `retry_count`
   - `sms.rate_limit.tracker_updated` (DEBUG) with `hourly_used`, `hourly_allowed`, `daily_used`, `daily_allowed`
   - `sms.rate_limit.denied` (WARN) with `retry_after_seconds`, `hourly_remaining`, `daily_remaining`
   - `sms.consent.denied` (INFO) with `phone_masked`, `consent_type`, `reason`
   - `sms.webhook.inbound` (INFO) with `provider`, `from_phone_masked`, `action`
   - `sms.webhook.signature_invalid` (WARN) with `provider`, `headers_seen` summary
   - `campaign.created` (INFO), `campaign.sent` (INFO), `campaign.cancelled` (WARN)
   - `campaign.worker.tick` (DEBUG) with `recipients_processed`, `tick_duration_ms`
   - `campaign.worker.orphan_recovered` (WARN) with `recipient_ids`, `count`
2. THE Platform SHALL mask phone numbers in logs to the last 4 digits (`+1XXX***XXXX`) to minimize PII exposure.
3. THE Platform SHALL configure alerts for:
   - `sms.webhook.signature_invalid` > 3 in 5 min → page oncall
   - CallRail API returns 401 → page oncall + auto-disable provider
   - `sms.rate_limit.denied` > 10 in 1 hr → Slack notification
   - `campaign.worker.orphan_recovered` > 0 → Slack notification
   - Worker tick gap > 5 min → admin dashboard banner
   - Campaign failure rate > 10% → campaign detail view + email to creator
   - Daily SMS send count > 800 (80% of 1k cap) → admin email heads-up
4. THE Platform SHALL expose `GET /api/v1/campaigns/worker-health` returning `last_tick_at`, `last_tick_duration_ms`, `last_tick_recipients_processed`, `pending_count`, `sending_count`, `orphans_recovered_last_hour`, `rate_limit` block from CallRail headers, `status` (`healthy` or `stale`).
5. THE frontend Campaigns tab SHALL poll the worker health endpoint every 30 seconds and display a green/red status dot.

### Requirement 33: UX Specifications — Confirmation Friction and Draft Persistence

**User Story:** As a staff member, I want UI friction proportional to campaign blast radius and draft persistence so that accidental large sends are prevented and my work is never lost.

#### Acceptance Criteria

1. WHERE a campaign has <50 recipients, THE Platform SHALL show a standard confirm dialog: "Send to N recipients? [Cancel] [Send]".
2. WHERE a campaign has ≥50 recipients, THE Platform SHALL require typed confirmation: "You are about to send SMS to **N people**. This cannot be undone. Type **SEND N** below to confirm." The submit button SHALL remain disabled until the typed string matches exactly (case-sensitive).
3. WHERE a campaign is scheduled for the future, THE Platform SHALL show an additional line: "Scheduled for {timestamp in CT}. You can still cancel before it starts."
4. THE `NewTextCampaignModal` wizard SHALL auto-save its state to `localStorage` under key `comms:draft_campaign:{staff_id}` on every field change (debounced 500ms).
5. ON modal re-open, WHERE a draft exists, THE Platform SHALL prompt: "You have an unsaved draft from {relative time} — [Continue] [Discard]".
6. ON first "Next" click (after audience is built), THE Platform SHALL persist the draft as a `Campaign` row with `status='draft'` so it survives browser cache clears.
7. THE Platform SHALL soft-delete drafts older than 7 days.

### Requirement 34: Message Composer Behaviors

**User Story:** As a staff member, I want a message composer that accurately shows segment count, character limits, and merge-field previews so that I understand the cost and appearance of each message before sending.

#### Acceptance Criteria

1. THE Message_Composer SHALL detect GSM-7 vs UCS-2 encoding based on message content and automatically switch modes when any non-GSM character (including emoji) is present.
2. THE Message_Composer SHALL display segment count using the correct per-segment thresholds:
   - GSM-7: 160 chars for 1 segment, 306 for 2 (153 each), 459 for 3, etc.
   - UCS-2: 70 chars for 1 segment, 134 for 2 (67 each), 201 for 3, etc.
3. THE Message_Composer SHALL display a warning color on the segment count badge when message exceeds 1 segment with text: "This message will send as N SMS segments per recipient — cost multiplies by N".
4. THE Message_Composer SHALL linter-check merge fields — any `{token}` not in the allowed list (`first_name`, `last_name`, `next_appointment_date`) SHALL be underlined in red.
5. THE Message_Composer SHALL provide click-to-insert buttons above the textarea for each allowed merge field.
6. THE live preview panel SHALL fetch the first 3 recipients from the current audience via `POST /campaigns/audience/preview` and render the message per recipient showing `"Grins Irrigation: " + body + <STOP footer>`.
7. WHERE any recipient in the preview has an empty merge field, THE Platform SHALL display an inline warning: "N recipients have no first_name — their message will say 'Hi ,'".
8. THE sender prefix SHALL be the literal string `"Grins Irrigation: "` (configurable via `SMS_SENDER_PREFIX` env var for test environments).
9. THE STOP footer SHALL be auto-appended if not already present in the body (text: ` Reply STOP to opt out.`).

### Requirement 35: CSV Upload Specifications

**User Story:** As a staff member, I want CSV upload to handle common file formats gracefully so that I can upload contact lists exported from Excel, Google Sheets, or legacy CRMs without reformatting.

#### Acceptance Criteria

1. THE Audience_Builder CSV upload SHALL accept files up to 2 MB and 5,000 rows.
2. THE Platform SHALL auto-detect encodings: UTF-8, UTF-8-BOM, Latin-1, Windows-1252.
3. THE Platform SHALL require a `phone` column (case-insensitive, label-matched, order-independent) and accept optional `first_name` and `last_name` columns.
4. THE Platform SHALL normalize phone numbers by stripping all non-digits and prefixing `+1` if 10 digits; otherwise reject the row.
5. THE Platform SHALL skip and report malformed rows rather than failing the whole upload, showing an expandable "N rows skipped — see details" list.
6. THE Platform SHALL collapse duplicate phones within the same file to first occurrence and show the duplicate count.
7. THE staged upload endpoint SHALL return `upload_id` + matched-to-customer / matched-to-lead / will-become-ghost-lead / rejected breakdown.
8. THE Platform SHALL NOT create ghost leads at upload time — only on final campaign send to avoid orphan leads from abandoned wizards.
9. THE Platform SHALL require the staff attestation checkbox to be checked before the upload is confirmed (see Requirement 25).

### Requirement 36: Time Window and Area-Code Timezone Warning

**User Story:** As a compliance officer, I want the system to respect TCPA time windows and warn staff about out-of-state recipients so that sends occur within the recipient's local 8 AM – 9 PM window wherever feasible.

#### Acceptance Criteria

1. THE Platform SHALL enforce the 8 AM – 9 PM Central Time window for all automated SMS sends via `SMSService.enforce_time_window()`.
2. WHERE a send attempts outside the CT window, THE Platform SHALL defer by setting `scheduled_for` to the next 8 AM CT.
3. THE Platform SHALL include a NANP area-code → timezone lookup table in `services/sms/phone_normalizer.py`.
4. THE Campaign_Review step SHALL compute and display a count of recipients whose area codes indicate non-CT timezones with the warning: "P recipients have non-Central area codes. They will be texted within CT hours (8 AM – 9 PM Central) — this may fall outside their local window. Per-recipient timezone enforcement is deferred to a future phase."
5. Manual one-off sends (`message_type='custom'`) SHALL bypass the time window per existing code.
6. Per-recipient timezone enforcement IS deferred to Phase 7+ and SHALL NOT block MVP.

### Requirement 37: Error Recovery and Campaign Management UI

**User Story:** As a staff member, I want to see which recipients failed, retry them, cancel in-progress campaigns, and manage failures so that partial failures do not require developer intervention.

#### Acceptance Criteria

1. THE Campaigns tab SHALL display failed campaigns with red "Failed" or yellow "Partial" badges.
2. WHERE a campaign has failed recipients, THE Platform SHALL show a detail view listing each failure with: phone (masked last 4), source (customer/lead/ghost), failure reason, timestamp.
3. THE detail view SHALL expose bulk actions: "Retry selected" and "Mark all as do not retry".
4. WHEN "Retry selected" is clicked, THE Platform SHALL create new `CampaignRecipient` rows tied to the same campaign with fresh `pending` state; original failed rows SHALL stay for audit.
5. WHEN a campaign is cancelled mid-send, THE Platform SHALL transition all remaining `pending` rows to `cancelled`; rows in `sending` state SHALL be allowed to finish naturally.
6. THE Platform SHALL expose `POST /v1/campaigns/{id}/cancel` and `POST /v1/campaigns/{id}/retry-failed` endpoints.

### Requirement 38: Verified CallRail API Contract (Phase 0.5)

**User Story:** As a developer implementing `CallRailProvider`, I want the exact request/response contract verified on a live production call so that I implement against ground truth, not docs guesses.

#### Acceptance Criteria

1. THE `CallRailProvider.send_text()` method SHALL POST to `https://api.callrail.com/v3/a/{account_id}/text-messages.json` with headers `Authorization: Token token="<api_key>"` and `Content-Type: application/json`.
2. THE request body SHALL contain exactly: `company_id` (COM ID), `tracking_number` (E.164 phone, NOT tracker_id), `customer_phone_number` (E.164), `content` (plain text).
3. THE response body on success SHALL be the full conversation object with the new message prepended to `recent_messages[]`. The top-level `id` field is the CONVERSATION ID (e.g., `"k8mc8"`), NOT a message ID.
4. Individual messages in `recent_messages[]` SHALL have no unique per-message ID — only `direction`, `content`, `created_at`, `type`, `media_urls`, and a shared `sms_thread.id` (e.g., `"SMT019d..."`).
5. THE `CallRailProvider.send_text()` method SHALL return a `ProviderSendResult` with both `provider_conversation_id` (the top-level `id`) and `provider_thread_id` (from `recent_messages[0].sms_thread.id`).
6. THE `SentMessage` model SHALL receive a Phase 1 migration adding `provider_conversation_id` VARCHAR(50) and `provider_thread_id` VARCHAR(50) columns, both nullable.
7. THE `CallRailProvider.send_text()` method SHALL parse rate-limit headers from every response and update the `rate_limit_tracker`: `x-rate-limit-hourly-allowed`, `x-rate-limit-hourly-used`, `x-rate-limit-daily-allowed`, `x-rate-limit-daily-used`.
8. THE observed latency budget for a send SHALL be approximately 275 ms CallRail-side processing, 600 ms total round-trip.
9. The `x-request-id` response header SHALL be captured and logged per send for CallRail support escalation.
10. THE Platform SHALL NOT rely on client-side idempotency keys — CallRail's honoring of the `Idempotency-Key` header is inconclusive (inconclusive 2026-04-07), so the state machine (Requirement 28) is the sole double-send protection.

### Requirement 39: Rate Limit Tracker (replaces traditional rate limiter)

**User Story:** As a developer, I want the platform to respect CallRail's rate limits by reading the response headers rather than maintaining a parallel counter so that the limiter stays in sync with CallRail's actual state.

#### Acceptance Criteria

1. THE Platform SHALL implement `services/sms/rate_limit_tracker.py` that parses `x-rate-limit-*` headers from CallRail responses.
2. WHEN `CallRailProvider.send_text()` receives a response, it SHALL update the tracker with the current `hourly_used`, `hourly_allowed`, `daily_used`, `daily_allowed`, and `fetched_at` timestamp.
3. THE tracker SHALL cache values in a single Redis key: `sms:rl:{provider}:{account_id}` with TTL 120 seconds and JSON value.
4. THE Background_Worker SHALL consult the tracker before claiming the next recipient and refuse new sends when `hourly_remaining <= 5` OR `daily_remaining <= 5`.
5. WHEN blocked, the tracker SHALL compute `retry_after_seconds` as: seconds until the next hour (for hourly) or seconds until next midnight UTC (for daily).
6. WHERE Redis is unavailable, THE tracker SHALL fall back to the in-process memory copy from the last send. Accept up to one worker's-worth of over-aggression until the next successful response refreshes the value.
7. THE tracker SHALL log `sms.rate_limit.tracker_updated` on each update and `sms.rate_limit.denied` when refusing.

### Requirement 40: Database Migrations (Phase 1)

**User Story:** As a developer, I want all Phase 1 schema changes bundled as a single migration batch so that staging and production deployments are atomic.

#### Acceptance Criteria

1. THE Platform SHALL create an Alembic migration that adds `campaign_recipients.sending_started_at TIMESTAMPTZ` (nullable, indexed) for the state machine.
2. THE Platform SHALL create an Alembic migration that adds `sms_consent_records.created_by_staff_id UUID` (nullable, FK to `staff.id`, indexed) for the CSV attestation audit trail.
3. THE Platform SHALL create an Alembic migration that adds `sent_messages.campaign_id UUID` (nullable, FK to `campaigns.id`, indexed) for the B4 dedupe scoping — if not already present.
4. THE Platform SHALL create an Alembic migration that adds `sent_messages.provider_conversation_id VARCHAR(50)` (nullable) for CallRail conversation reference.
5. THE Platform SHALL create an Alembic migration that adds `sent_messages.provider_thread_id VARCHAR(50)` (nullable) for CallRail sms_thread reference.
6. All Phase 1 migrations SHALL be nullable / non-breaking so that the Twilio provider (unaffected by CallRail-specific columns) continues to work.
7. THE migrations SHALL include `down_revision` paths for rollback.

### Requirement 41: Audit Log Wiring

**User Story:** As a compliance auditor, I want a durable audit log of all SMS and campaign lifecycle events so that post-hoc investigations have a clear trail.

#### Acceptance Criteria

1. THE Platform SHALL emit audit log events via the existing `audit_log.py` model for:
   - `sms.provider.switched` with actor, old provider, new provider
   - `sms.campaign.created` with actor, campaign_id, recipient_count
   - `sms.campaign.sent_initiated` with actor, campaign_id
   - `sms.campaign.cancelled` with actor, campaign_id, reason
   - `sms.csv_attestation.submitted` with actor, upload_id, phone_count, attestation_version
   - `sms.consent.hard_stop_received` with phone_masked, source (inbound webhook)
   - `sms.config.webhook_secret_rotated` with actor, environment
2. THE audit log entries SHALL persist indefinitely and SHALL NOT be deleted by any cleanup job.
3. THE Platform SHALL expose a read-only audit log view in the admin Settings page (Phase 7).

### Requirement 42: Structured Logging Standards

**User Story:** As an operator, I want all SMS log events to use structured logging with consistent field names so that log queries and alerting are reliable.

#### Acceptance Criteria

1. THE Platform SHALL use `LoggerMixin` for all SMS-related log emission.
2. THE Platform SHALL implement a `_mask_phone(phone)` helper that returns the last 4 digits only (e.g., `+1XXX***XXXX`).
3. THE Platform SHALL never log raw phone numbers, message content, or API keys.
4. THE Platform SHALL log `provider_conversation_id`, `provider_thread_id`, and CallRail `x-request-id` on every successful send for support escalation.
5. THE log field naming SHALL follow the events in Requirement 32.

### Requirement 43: SMS Segment Counting (GSM-7 vs UCS-2)

**User Story:** As a developer, I want shared segment-counting logic so that the frontend composer and the backend validation agree on the cost of every message.

#### Acceptance Criteria

1. THE Platform SHALL implement `services/sms/segment_counter.py` with a pure function that takes message text and returns `(encoding: Literal["GSM-7","UCS-2"], segment_count: int, total_chars: int)`.
2. THE function SHALL detect UCS-2 by scanning for any character outside the GSM-7 basic + extension alphabet.
3. THE frontend SHALL port the same detection logic so the composer's segment count matches the backend's calculation.
4. THE segment count SHALL be calculated as: GSM-7 → `ceil(total_chars / 160)` if 1 segment else `ceil(total_chars / 153)`; UCS-2 → `ceil(total_chars / 70)` if 1 segment else `ceil(total_chars / 67)`.
5. THE segment count SHALL include the auto-appended STOP footer and sender prefix in the total character count.

### Requirement 44: Webhook Signature Verification

**User Story:** As a compliance officer, I want inbound webhooks signature-verified so that a malicious actor cannot forge STOP replies or spoof customer messages.

#### Acceptance Criteria

1. THE `CallRailProvider.verify_webhook_signature(headers, raw_body)` method SHALL implement HMAC signature verification using `CALLRAIL_WEBHOOK_SECRET`.
2. WHERE the signature header is missing or invalid, THE `POST /webhooks/callrail/inbound` route SHALL return HTTP 403 and log `sms.webhook.signature_invalid`.
3. WHERE the signature is valid, THE route SHALL parse the payload via `parse_inbound_webhook(payload)` and call `SMSService.handle_inbound()`.
4. THE webhook signature mechanism SHALL be verified during Phase 1 smoke testing with a real inbound message, since the exact header name and HMAC algorithm are not yet verified (Phase 0.5 did not include an inbound test).
5. IF the webhook signature verification cannot be implemented from documentation alone, THE developer SHALL coordinate with CallRail support to obtain the signing spec during Phase 1.

### Requirement 45: Testing Strategy Enhancements

**User Story:** As a developer, I want comprehensive test coverage including load tests, race conditions, and CSV edge cases so that production surprises are minimized.

#### Acceptance Criteria

1. THE Platform SHALL include load tests that upload a 5,000-row CSV within the 2 MB limit and verify parsing completes within 5 seconds.
2. THE Platform SHALL include load tests that create a 1,000-recipient campaign and verify the audience preview endpoint returns in <1 second and the send-initiate endpoint returns 202 immediately.
3. THE Platform SHALL include race-condition tests:
   - Two concurrent CSV uploads with overlapping phones → ghost lead dedupe exactly one Lead row per phone via row-level lock
   - Two workers running against the same campaign simultaneously → `sending_started_at` + `FOR UPDATE SKIP LOCKED` claim, no double-send
   - Inbound STOP webhook arrives while a campaign is actively sending → mid-campaign consent check catches STOP, remaining `pending` rows for that phone transition to `failed` with reason `consent_denied`
4. THE Platform SHALL commit CSV test fixtures in `tests/fixtures/csv/`:
   - `valid_basic.csv`, `valid_with_bom.csv`, `valid_latin1.csv`, `malformed_phones.csv`, `mixed_formats.csv`, `duplicate_phones.csv`, `no_header.csv`, `extra_columns.csv`, `empty_file.csv`, `too_large.csv`, `too_many_rows.csv`
5. THE Platform SHALL include an end-to-end integration test: mixed audience (1 customer + 1 lead + 1 ad-hoc CSV row) → create → audience preview → send → verify 3 `SentMessage` rows with correct FKs + `campaign_id`, 1 new ghost Lead, 1 bulk-inserted `SmsConsentRecord` with attestation metadata, `CampaignRecipient` state machine transitions end-to-end.
6. THE Platform SHALL include an integration test for orphan recovery: set a `CampaignRecipient` to `sending` with old `sending_started_at` → run worker startup hook → verify transition to `failed` with `worker_interrupted` reason.
7. THE Platform SHALL include a permission enforcement test matrix: Technician POST `/campaigns` → 403; Manager POST send for 51 recipients → 403; Admin succeeds.
8. THE Platform SHALL include a webhook idempotency test: POST the same inbound payload twice → only one side effect.
