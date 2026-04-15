# Implementation Plan: CallRail SMS Integration

## Overview

This plan implements a 7-phase, independently shippable SMS integration that transforms the platform from a hard-wired Twilio stub into a pluggable, provider-agnostic architecture with CallRail as the first real provider. Each phase builds incrementally on the previous, with checkpoints to validate progress. Backend uses Python/FastAPI/SQLAlchemy async; frontend uses React 19/TypeScript. Property-based tests use Hypothesis; unit tests use pytest; frontend tests use Vitest.

**Phase 0 status (2026-04-07):** ✅ **COMPLETE** — 10DLC verified (brand `registered_in_twilio` via API, campaign-level confirmed in CallRail Compliance Home dashboard). CallRail IDs captured: `ACCOUNT_ID=ACC019c31a27df478178fe0f381d863bf7d`, `COMPANY_ID=COM019c31a27f5b732b9d214e04eaa3061f`, `TRACKER_ID=TRK019c5f8c1c3279f98b678fb73d04887e`, tracking number `+19525293750`. All values in `.env` (gitignored).

**Phase 0.5 status (2026-04-07):** ✅ **COMPLETE** — Live SMS send verified via `POST /v3/a/{account_id}/text-messages.json` → HTTP 200, real text delivered to owner's phone. Canonical API contract captured in design.md §"Phase 0.5 Verified CallRail API Contract". Key findings that modify Phase 1 scope:
- CallRail returns rate-limit state in `x-rate-limit-*` response headers — **S2 simplified**: replaced Redis sliding-window counter with a `rate_limit_tracker.py` module that parses headers and caches 120s
- Response is conversation-oriented, not message-oriented: need `provider_conversation_id` + `provider_thread_id` columns on `SentMessage`
- CallRail has NO delivery status callbacks: **S12 resolved**, no `/webhooks/callrail/delivery-status` route, `sent` is terminal, UI labels "Sent" not "Delivered"
- Idempotency-Key header inconclusive: do NOT rely on provider-side dedupe; use state machine (S13)

## Tasks

- [x] 0. Phase 0 — Pre-flight (COMPLETE)
  - [x] Verify 10DLC brand + campaign registration via API + CallRail Compliance Home dashboard
  - [x] Capture `CALLRAIL_ACCOUNT_ID`, `CALLRAIL_COMPANY_ID`, `CALLRAIL_TRACKING_NUMBER`, `CALLRAIL_TRACKER_ID` → `.env`
  - [x] Verify `.env` is gitignored (`.gitignore:29`)

- [x] 0.5. Phase 0.5 — Live API smoke test (COMPLETE)
  - [x] Send one real SMS via `POST /v3/a/{account_id}/text-messages.json` → HTTP 200, delivered to owner's phone
  - [x] Capture exact request/response contract (documented in design.md §"Phase 0.5 Verified CallRail API Contract")
  - [x] Confirm rate-limit headers are returned on every response → simplifies S2
  - [x] Confirm CallRail has no delivery status callbacks → resolves S12
  - [x] Confirm response is conversation-oriented with no per-message ID → requires `provider_conversation_id` + `provider_thread_id` columns

- [x] 1. Phase 1 — Provider Abstraction, CallRail Client, Recipient Unification, and Policy Fixes

  - [x] 1.0 Create Phase 1 Alembic migrations (batch)
    - Add `campaign_recipients.sending_started_at TIMESTAMPTZ` nullable indexed column (for S13 state machine + orphan recovery)
    - Add `sms_consent_records.created_by_staff_id UUID` nullable FK-to-staff indexed column (for S10 CSV attestation audit trail per Requirement 25)
    - Add `sent_messages.campaign_id UUID` nullable FK-to-campaigns indexed column (for B4 dedupe scoping per Requirement 24)
    - Add `sent_messages.provider_conversation_id VARCHAR(50)` nullable column (for CallRail conversation ID per Requirement 38)
    - Add `sent_messages.provider_thread_id VARCHAR(50)` nullable column (for CallRail `sms_thread.id` per Requirement 38)
    - All migrations must be non-breaking so Twilio provider continues to work
    - Include `down_revision` paths for rollback
    - _Requirements: 24, 25, 28, 38, 40_

  - [x] 1.1 Create the `services/sms/` package with `base.py` defining `BaseSMSProvider` Protocol, `ProviderSendResult`, and `InboundSMS` frozen dataclasses
    - Define `BaseSMSProvider` Protocol with `send_text()`, `verify_webhook_signature()`, `parse_inbound_webhook()`, `provider_name`
    - Define `ProviderSendResult(provider_message_id, provider_conversation_id, provider_thread_id, status, raw_response, request_id)` — includes CallRail-specific fields
    - Define `InboundSMS(from_phone, body, provider_sid, to_phone)`
    - Create `services/sms/__init__.py` with public exports
    - _Requirements: 1.1, 1.7, 22.1, 38_

  - [x] 1.2 Implement `NullProvider` in `services/sms/null_provider.py`
    - Record all send attempts in an in-memory list
    - Return synthetic `ProviderSendResult(provider_message_id=uuid, status="sent")`
    - Implement `verify_webhook_signature()` returning True and `parse_inbound_webhook()` returning a test `InboundSMS`
    - _Requirements: 1.9_

  - [x] 1.3 Write property test for NullProvider (Property 1)
    - **Property 1: NullProvider records all sends**
    - **Validates: Requirements 1.9**

  - [x] 1.4 Implement `CallRailProvider` in `services/sms/callrail_provider.py` per verified contract (Requirement 38)
    - Use `httpx.AsyncClient` with `Authorization: Token token="{api_key}"` header
    - Implement `send_text()` → POST to `/v3/a/{account_id}/text-messages.json` with `company_id`, `tracking_number` (E.164), `customer_phone_number` (E.164), `content`
    - Parse response: extract top-level `id` as `provider_conversation_id`, `recent_messages[0].sms_thread.id` as `provider_thread_id`, capture `x-request-id` header for logging
    - Call `rate_limit_tracker.update_from_headers(response.headers)` after every response to cache `x-rate-limit-*` values in Redis
    - Implement `list_tracking_numbers()` → GET `/v3/a/{account_id}/trackers.json`
    - Implement `verify_webhook_signature()` using HMAC with `CALLRAIL_WEBHOOK_SECRET` — exact header name + algorithm to be confirmed during Phase 1 smoke test with a real inbound
    - Implement `parse_inbound_webhook()` to handle CallRail's inbound SMS payload shape
    - Define typed exceptions: `CallRailAuthError` (401), `CallRailRateLimitError` (429), `CallRailValidationError` (400/422)
    - Add structured logging via `LoggerMixin` with phone masking
    - **Do NOT rely on Idempotency-Key header** (Phase 0.5 inconclusive) — idempotency is provided by the state machine only
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.10, 38, 44_

  - [x] 1.5 Write property test for CallRail send_text payload structure (Property 2)
    - **Property 2: CallRail send_text payload structure**
    - **Validates: Requirements 2.3**

  - [x] 1.6 Implement `TwilioProvider` in `services/sms/twilio_provider.py`
    - Port the existing `_send_via_twilio()` stub verbatim with no behavior change
    - Conform to `BaseSMSProvider` Protocol
    - _Requirements: 1.2, 1.8_

  - [x] 1.7 Implement `factory.py` with `get_sms_provider()` reading `SMS_PROVIDER` env var
    - Default to `callrail` when env var is not set
    - Match `callrail` → `CallRailProvider`, `twilio` → `TwilioProvider`, `null` → `NullProvider`
    - Raise `ValueError` for unknown provider names
    - _Requirements: 1.3, 1.4_

  - [x] 1.8 Implement `Recipient` frozen dataclass in `services/sms/recipient.py`
    - Fields: `phone` (E.164), `source_type` (Literal["customer", "lead", "ad_hoc"]), `customer_id`, `lead_id`, `first_name`, `last_name`
    - Factory methods: `from_customer()`, `from_lead()`, `from_adhoc()`
    - _Requirements: 4.1, 4.2, 4.3, 4.4_

  - [x] 1.9 Write property test for Recipient factory correctness (Property 5)
    - **Property 5: Recipient factory correctness**
    - **Validates: Requirements 4.2, 4.3, 4.4**

  - [x] 1.10 Implement `ghost_lead.py` with `create_or_get(session, phone, first_name, last_name)`
    - Normalize phone to E.164 via `phone_normalizer.py`
    - Use `SELECT ... FOR UPDATE` row-level lock to prevent race conditions on concurrent uploads
    - Find existing Lead by phone, or create ghost lead with `lead_source='campaign_import'`, `status='new'`, `sms_consent=false`, `source_site='campaign_csv_import'`
    - Return existing Lead if phone already has one (idempotent)
    - _Requirements: 5.1, 5.2, 5.3, 45 (race condition)_

  - [x] 1.11 Write property tests for ghost lead (Properties 7, 8)
    - **Property 7: Ghost lead creation invariants**
    - **Property 8: Ghost lead phone deduplication (idempotence)**
    - **Validates: Requirements 5.1, 5.2, 5.4**

  - [x] 1.12 Implement `rate_limit_tracker.py` with header-based rate limit tracking (simplified from sliding-window counter per Phase 0.5 findings)
    - `SMSRateLimitTracker` class with `update_from_headers(response_headers)` and `check()` methods
    - Parses `x-rate-limit-hourly-allowed`, `x-rate-limit-hourly-used`, `x-rate-limit-daily-allowed`, `x-rate-limit-daily-used` from CallRail responses
    - Caches in Redis as `sms:rl:{provider}:{account_id}` with 120s TTL + in-memory fallback if Redis is down
    - `check()` returns `(allowed, retry_after_seconds, state)` — refuses when `hourly_remaining <= 5` OR `daily_remaining <= 5`
    - Computes `retry_after_seconds` as seconds until next hour (hourly) or next UTC midnight (daily)
    - Does NOT maintain its own counters — CallRail is the source of truth
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.7, 39_

  - [x] 1.13 Write property tests for rate limit tracker (Properties 37, 38)
    - **Property 37: Rate limit tracker blocks at threshold**
    - **Property 38: Rate limit tracker header round-trip**
    - **Validates: Requirements 39**

  - [x] 1.14 Implement `templating.py` with `render_template(body, context)` using `SafeDict`
    - Missing keys render as empty string (never `KeyError`)
    - No Jinja, no conditionals, no loops
    - _Requirements: 14.1, 14.2, 14.3, 14.5_

  - [x] 1.15 Write property test for template rendering (Property 24)
    - **Property 24: Template rendering with safe defaults**
    - **Validates: Requirements 14.1, 14.2**

  - [x] 1.16 Implement `phone_normalizer.py` with E.164 normalization and area-code timezone lookup
    - Handle formats: `(952) 529-3750`, `952-529-3750`, `9525293750`, `+19525293750` → `+19525293750`
    - Reject bogus phones (000-..., 555-01xx, extensions, letters)
    - Raise error or return failure for invalid phone strings
    - Include NANP area-code → IANA timezone lookup table for the UI warning (H1)
    - `lookup_timezone(e164_phone) -> str` returns the IANA timezone for a US phone, used by Campaign Review to count non-CT recipients
    - _Requirements: 20.1, 20.3, 36_

  - [x] 1.17 Write property tests for phone normalization and area-code lookup (Properties 20, 48)
    - **Property 20: Phone normalization to E.164**
    - **Property 48: Area-code timezone lookup**
    - **Validates: Requirements 20.1, 12.9, 20.3, 36**

  - [x] 1.18 Implement `consent.py` with type-scoped consent check (S11)
    - `check_sms_consent(phone, consent_type)` function with three consent types
    - **Hard-STOP precedence:** if any `SmsConsentRecord` row for phone has `consent_method='text_stop'` and `consent_given=false`, deny all except `operational`
    - **Marketing:** require explicit opt-in via form consent, START keyword, or CSV attestation; fallback to `Customer.sms_opt_in` / `Lead.sms_consent` boolean
    - **Transactional:** default allow under EBR exemption, respect hard-STOP
    - **Operational:** always allow
    - `bulk_insert_attestation_consent(staff_id, phones, attestation_version, attestation_text)` helper for CSV upload confirmation
    - _Requirements: 26, 25_

  - [x] 1.19 Write property tests for consent checks (Properties 32, 33)
    - **Property 32: Hard-STOP precedence**
    - **Property 33: Type-scoped consent (S11)**
    - **Validates: Requirements 26**

  - [x] 1.20 Implement `state_machine.py` with `RecipientState` enum and `transition()` validator (S13)
    - `RecipientState`: `pending`, `sending`, `sent`, `failed`, `cancelled`
    - `transition(recipient, from_state, to_state)` validates allowed transitions, raises `InvalidStateTransitionError` on forbidden ones
    - `orphan_recovery_query()` SQL: `UPDATE campaign_recipients SET delivery_status='failed', error_message='worker_interrupted' WHERE delivery_status='sending' AND sending_started_at < now() - interval '5 minutes'`
    - _Requirements: 28_

  - [x] 1.21 Write property tests for state machine (Properties 35, 36, 49)
    - **Property 35: State machine transition invariants**
    - **Property 36: Orphan recovery**
    - **Property 49: Sending state before provider call**
    - **Validates: Requirements 28**

  - [x] 1.22 Implement `segment_counter.py` for GSM-7 vs UCS-2 detection
    - Pure function: `count_segments(text) -> tuple[encoding, segments, chars]`
    - GSM-7 thresholds: 160/153, UCS-2 thresholds: 70/67
    - Detects UCS-2 by scanning for any character outside GSM-7 basic + extension alphabet
    - Includes auto-appended STOP footer and sender prefix in the count
    - _Requirements: 43_

  - [x] 1.23 Write property test for SMS segment count (Properties 25, 47)
    - **Property 25: SMS segment count** (original)
    - **Property 47: SMS segment count for GSM-7 and UCS-2** (extended per H8)
    - **Validates: Requirements 15.9, 43**

- [x] 2. Phase 1 continued — Refactor SMSService + Fix Blockers B1, B2, B3, B4
  - [x] 2.1 Refactor `SMSService` to accept `BaseSMSProvider` via constructor and delegate to it
    - Replace `_send_via_twilio()` with `_send_via_provider()` delegating to `self.provider.send_text()`
    - New signature: `send_message(recipient: Recipient, message, message_type, consent_type='transactional', campaign_id=None, job_id=None, appointment_id=None)`
    - Accept `Recipient` parameter instead of `customer_id`
    - **B4 fix:** Accept `campaign_id` parameter — when set, scope the dedupe check to `(recipient, campaign_id)` instead of `(customer_id, message_type)`
    - **S11 fix:** Call `check_sms_consent(phone, consent_type)` instead of the type-agnostic version
    - Populate `SentMessage.customer_id` or `lead_id` based on `Recipient.source_type`
    - Populate `SentMessage.campaign_id` when provided
    - Populate `SentMessage.provider_conversation_id` and `provider_thread_id` from the provider result
    - Integrate rate limit tracker: call `tracker.check()` before provider dispatch; on denial, set `delivery_status='scheduled'` with `scheduled_for=now + retry_after`
    - Integrate templating: render merge fields before provider call
    - Prepend "Grins Irrigation:" sender prefix and append STOP footer to all outbound messages
    - _Requirements: 1.5, 1.6, 4.5, 4.6, 11.2, 11.3, 24, 26, 38, 39_

  - [x] 2.2 Write property tests for SMSService send path (Properties 6, 9, 15, 19)
    - **Property 6: SentMessage FK from Recipient source_type**
    - **Property 9: Universal phone-keyed consent check**
    - **Property 15: Outbound message formatting**
    - **Property 19: Send persistence round-trip**
    - **Validates: Requirements 4.6, 5.3, 7.1, 7.3, 7.4, 11.2, 11.3, 11.6, 5.5, 2.9, 12.7**

  - [x] 2.3 Create `api/dependencies.py` with `get_campaign_service()` DI helper (fixes B1)
    - Wire `SMSService(db, provider)` and `EmailService(db)` into `CampaignService`
    - _Requirements: 6.1, 6.2_

  - [x] 2.4 Fix B2 — Centralize consent check in `SMSService`, remove direct `Customer.sms_opt_in` bypass in `CampaignService`
    - Remove the `sms_opt_in=True` override in `_send_to_recipient()`
    - All consent goes through `check_sms_consent(phone)` on `SmsConsentRecord`
    - _Requirements: 7.1, 7.2, 7.3, 7.4_

  - [x] 2.5 Fix B3 — Refactor `POST /sms/send-bulk` to enqueue + return 202
    - Persist recipients as `CampaignRecipient` rows with `delivery_status='pending'`
    - Return HTTP 202 immediately; background worker drains
    - _Requirements: 8.1, 8.2, 8.3, 8.4_

  - [x] 2.6 Update `api/v1/campaigns.py` to use `get_campaign_service()` DI helper
    - Replace `CampaignService(campaign_repository=repo)` with DI-injected version
    - _Requirements: 6.2, 6.3_

  - [x] 2.7 Update ALL existing callers of `SMSService.send_message()` to pass `Recipient.from_customer(...)` AND the correct `consent_type`
    - Update `api/v1/sms.py` send + send-bulk endpoints → `consent_type='transactional'` for generic sends
    - Update appointment reminder/confirmation/on-the-way/completion call sites → `consent_type='transactional'`
    - Update invoice + payment reminder call sites → `consent_type='transactional'`
    - Update campaign send path → `consent_type='marketing'` + `campaign_id` set
    - Update STOP confirmation reply path → `consent_type='operational'`
    - Update `notification_service.py` if it calls SMSService
    - _Requirements: 4.7, 26_

  - [x] 2.8 Refactor `CampaignService._send_to_recipient()` to accept `Recipient` instead of `Customer`
    - Populate `CampaignRecipient.customer_id` or `lead_id` based on `recipient.source_type`
    - Map `Customer.sms_opt_in` and `Lead.sms_consent` to unified boolean when building Recipients
    - _Requirements: 4.8, 19.1_

  - [x] 2.9 Write property test for consent field mapping (Property 27)
    - **Property 27: Consent field mapping**
    - **Validates: Requirements 19.1**

  - [x] 2.10 Add CallRail inbound webhook route `POST /v1/webhooks/callrail/inbound`
    - Verify webhook signature via `CallRailProvider.verify_webhook_signature()` using `CALLRAIL_WEBHOOK_SECRET`
    - **Idempotency dedupe:** `SADD sms:webhook:processed:{provider}:{conversation_id}:{created_at}` in Redis with 24h TTL; if already present, skip + return 200
    - Parse payload via `parse_inbound_webhook()` → pass to `SMSService.handle_inbound()`
    - Return 403 on invalid signature, 400 on malformed payload
    - Emit `sms.webhook.inbound` and `sms.webhook.signature_invalid` structured log events
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 30 (idempotency), 44_

  - [x] 2.11 Write property tests for inbound webhook and STOP handling (Properties 10, 16, 42, 43)
    - **Property 10: Inbound webhook parsing**
    - **Property 16: STOP keyword consent revocation**
    - **Property 42: Webhook signature rejection**
    - **Property 43: Webhook idempotency**
    - **Validates: Requirements 9.2, 9.4, 9.5, 11.4, 30, 44**

  - [x] 2.12 Update `.env.example` with SMS provider, CallRail, and webhook placeholder entries
    - Add: `SMS_PROVIDER=`, `CALLRAIL_API_KEY=`, `CALLRAIL_ACCOUNT_ID=`, `CALLRAIL_COMPANY_ID=`, `CALLRAIL_TRACKING_NUMBER=`, `CALLRAIL_TRACKER_ID=`, `CALLRAIL_WEBHOOK_SECRET=`, `SMS_SENDER_PREFIX=`
    - Document that `TWILIO_*` vars become optional
    - Document that `CALLRAIL_DELIVERY_WEBHOOK_ENABLED`, `SMS_RATE_LIMIT_HOURLY`, `SMS_RATE_LIMIT_DAILY` are NOT used (removed after Phase 0.5 per Requirement 30.2)
    - _Requirements: 18.1, 18.2, 18.3, 18.4, 30_

  - [x] 2.13 Create `api/dependencies.py` permission dependency functions
    - `require_admin(user)` → 403 if not admin
    - `require_admin_or_manager(user)` → 403 if neither
    - `require_campaign_send_authority(campaign_id, db, user)` → counts recipients, enforces <50 manager / ≥50 admin threshold (Requirement 31)
    - Apply these dependencies to every campaign + CSV upload + provider-switching endpoint per the permission matrix
    - _Requirements: 31_

  - [x] 2.14 Wire audit log events
    - Emit `sms.provider.switched` when factory resolves a different provider at boot
    - Emit `sms.campaign.created` on campaign creation (requires DI in campaign route)
    - Emit `sms.campaign.sent_initiated` on send initiation
    - Emit `sms.campaign.cancelled` on cancellation
    - Emit `sms.csv_attestation.submitted` on CSV upload confirmation
    - Emit `sms.consent.hard_stop_received` when STOP inbound creates a consent record
    - Reuse existing `audit_log.py` model + repository
    - _Requirements: 41_

  - [x] 2.15 Wire structured logging events per §15.1 / Requirement 32
    - Emit `sms.send.requested`, `sms.send.succeeded` (with `provider_conversation_id`, `provider_thread_id`, `latency_ms`, `hourly_remaining`, `daily_remaining`, `x_request_id`), `sms.send.failed`
    - Emit `sms.rate_limit.tracker_updated`, `sms.rate_limit.denied`
    - Emit `sms.consent.denied`
    - Implement `_mask_phone(phone)` helper — returns `+1XXX***XXXX`
    - Never log raw phone numbers, message content, or API keys
    - _Requirements: 32, 42, 46_

  - [x] 2.16 Write property test for phone masking in logs (Property 46)
    - **Property 46: Phone masking in logs**
    - **Validates: Requirement 42**

  - [x] 2.17 Create `deployment-instructions/callrail-webhook-setup.md` runbook
    - Document per-environment webhook URLs (local ngrok, staging, prod)
    - Document CallRail dashboard navigation: Account Settings → Integrations → Webhooks
    - Document `CALLRAIL_WEBHOOK_SECRET` paste procedure
    - Document domain migration procedure
    - _Requirements: 30_

- [x] 3. Checkpoint — Phase 1 complete
  - Ensure all tests pass, ask the user if questions arise.
  - Verify:
    - Provider abstraction works, all 3 providers conform to Protocol
    - SMSService delegates correctly with new signature (Recipient + consent_type + campaign_id)
    - Blockers B1/B2/B3/B4 all fixed (campaign DI, consent centralized, bulk send enqueued, campaign-scoped dedupe)
    - S9 fixed (mixed customer/lead/ad-hoc sends end-to-end)
    - S10 fixed (CSV staff attestation creates proper `SmsConsentRecord` rows with `created_by_staff_id`)
    - S11 fixed (type-scoped consent with hard-STOP precedence)
    - S13 fixed (state machine + orphan recovery)
    - Inbound webhook route live with signature verification + idempotency dedupe
    - Rate limit tracker functional (reads CallRail headers, Redis-cached)
    - All 5 Alembic migrations applied and reversible
    - Audit log events emitting
    - Structured logging events emitting with phone masking
    - Permission dependencies enforced on new endpoints
    - Manual smoke test: send one live text, reply STOP, verify `SmsConsentRecord` with `consent_given=false` created

- [x] 4. Phase 2 — Interim CSV Blast Script
  - [x] 4.1 Create `scripts/send_callrail_campaign.py` CSV blast script
    - Read CSV with columns: `phone`, `first_name`, `last_name`
    - Read message template from file or CLI argument
    - Dry-run mode: print every rendered message without sending (default)
    - Live mode: activated with `--confirm` flag, throttle at ~140/hr
    - Skip opted-out recipients via `SmsConsentRecord`
    - Persist every send as `SentMessage` tied to matched customer or ghost lead
    - Report un-normalizable phone numbers
    - Progress logs to stdout
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6, 12.7, 12.8, 12.9, 12.10_

  - [x] 4.2 Write property tests for CSV script (Properties 17, 18)
    - **Property 17: CSV row parsing**
    - **Property 18: Dry-run zero sends**
    - **Validates: Requirements 12.1, 12.3**

- [x] 5. Checkpoint — Phase 2 complete
  - Ensure all tests pass, ask the user if questions arise.
  - Verify: CSV script dry-run produces correct output, live mode throttles correctly, ghost leads created for unmatched phones.

- [x] 6. Phase 3 — Background Campaign Worker with State Machine
  - [x] 6.1 Implement `process_pending_campaign_recipients` APScheduler interval job in `background_jobs.py`
    - 60-second tick interval
    - **Orphan recovery first:** run `orphan_recovery_query()` on every tick before claiming new work
    - **Concurrent-safe claim:** use `SELECT ... FOR UPDATE SKIP LOCKED` when claiming `pending` rows
    - Poll `campaign_recipients WHERE delivery_status='pending' AND campaign.scheduled_at <= now() AND campaign.status='sending'` with LIMIT N (N ≤ ~2 per tick to stay under 140/hr effective)
    - **State machine transition: `pending → sending`** with `sending_started_at = now()` BEFORE provider call
    - For each recipient:
      - Check rate limit tracker (`check()` reads Redis cache of CallRail headers)
      - Consent check (type-scoped, defaults to `marketing` for campaign sends)
      - Time-window check (CT 8AM–9PM)
      - Render merge fields via `templating.render_template(body, context)`
      - Call `SMSService.send_message(recipient, body, 'campaign', consent_type='marketing', campaign_id=campaign.id)`
      - On success: `sending → sent`, set `sent_at`, create `SentMessage` with `provider_conversation_id` + `provider_thread_id`
      - On provider error: `sending → failed`, set `error_message`, retry with exponential backoff up to N attempts
    - Record `last_tick_at` in Redis key `sms:worker:last_tick` (for worker health endpoint)
    - Emit `campaign.worker.tick` structured log event with `recipients_processed`, `tick_duration_ms`
    - Emit `campaign.worker.orphan_recovered` when orphans found
    - Compute `Campaign.status` as derived (sent vs partial_failed) from aggregate recipient states
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7, 21.1, 21.2, 21.3, 21.4, 21.5, 28, 32_

  - [x] 6.2 Write property tests for background worker (Properties 11, 12, 13, 14, 28, 29, 30, 35, 36, 45, 49)
    - **Property 11: Background worker respects rate limits**
    - **Property 12: Worker resumability**
    - **Property 13: Worker honors scheduled_at**
    - **Property 14: Time window enforcement**
    - **Property 28: Exponential backoff on retry**
    - **Property 29: CampaignRecipient status tracking**
    - **Property 30: Campaign completion detection**
    - **Property 35: State machine transition invariants**
    - **Property 36: Orphan recovery**
    - **Property 45: Concurrent worker claim uniqueness**
    - **Property 49: Sending state before provider call**
    - **Validates: Requirements 8.2, 10.2, 10.4, 10.6, 10.7, 11.5, 21.1, 21.2, 21.4, 21.5, 28**

  - [x] 6.3 Add `GET /api/v1/campaigns/worker-health` endpoint per Requirement 32
    - Returns JSON: `last_tick_at`, `last_tick_duration_ms`, `last_tick_recipients_processed`, `pending_count`, `sending_count`, `orphans_recovered_last_hour`, `rate_limit` block from tracker, `status` (`healthy` or `stale` if last_tick_at > 2 min ago)
    - Requires Admin or Manager permission (Requirement 31)

  - [x] 6.4 Add `POST /v1/campaigns/{id}/cancel` endpoint
    - Transitions all `pending` rows to `cancelled`
    - `sending` rows allowed to finish naturally
    - Requires `require_admin_or_manager` (own campaigns for Manager)
    - Emits `sms.campaign.cancelled` audit event
    - _Requirements: 28, 31, 37, 41_

  - [x] 6.5 Refactor `POST /sms/send-bulk` to enqueue + return 202 (B3 fix completion)
    - Persist recipients as `CampaignRecipient` rows with `delivery_status='pending'`
    - Return HTTP 202 immediately; background worker drains
    - _Requirements: 8.1, 8.2, 8.3, 8.4_

  - [x] 6.6 Refactor `POST /v1/campaigns/{id}/send` to enqueue + return 202
    - Replaces the current synchronous send path
    - Validates via `require_campaign_send_authority` (enforces 50-recipient threshold)
    - Emits `sms.campaign.sent_initiated` audit event
    - _Requirements: 8.4, 31, 41_

- [x] 7. Checkpoint — Phase 3 complete
  - Ensure all tests pass, ask the user if questions arise.
  - Verify: background worker drains pending recipients under rate limits, campaigns resume after restart, scheduled campaigns wait, time window enforced.

- [x] 8. Phase 4 — Audience Filter Extensions (Multi-Source) + Enhanced CSV Upload
  - [x] 8.1 Create Pydantic models for `TargetAudience` validation in `schemas/campaign.py`
    - `CustomerAudienceFilter`: `sms_opt_in`, `ids_include`, `cities`, `last_service_between`, `tags_include`, `lead_source`, `is_active`, `no_appointment_in_days`
    - `LeadAudienceFilter`: `sms_consent`, `ids_include`, `statuses`, `lead_source`, `intake_tag`, `action_tags_include`, `cities`, `created_between`
    - `AdHocAudienceFilter`: `csv_upload_id`, `staff_attestation_confirmed: bool`, `attestation_text_shown: str`, `attestation_version: str`
    - Compose into `TargetAudience` with three top-level keys
    - _Requirements: 13.2, 13.3, 13.4, 13.5, 13.7, 25_

  - [x] 8.2 Write property test for target audience schema validation (Property 23)
    - **Property 23: Target audience schema validation**
    - **Validates: Requirements 13.7**

  - [x] 8.3 Refactor `CampaignService._filter_recipients()` to return `list[Recipient]` from UNION of Customer + Lead + ad-hoc sources
    - Query Customer table with all filter criteria
    - Query Lead table with all filter criteria
    - Resolve ad-hoc CSV via ghost lead creation
    - Deduplicate by E.164 phone — customer record wins on collision
    - _Requirements: 13.1, 13.6, 5.5_

  - [x] 8.4 Write property tests for audience filter (Properties 21, 22)
    - **Property 21: Audience filter correctness**
    - **Property 22: Audience deduplication — customer wins**
    - **Validates: Requirements 13.1, 13.3, 13.4, 13.6, 13.8**

  - [x] 8.5 Add `POST /campaigns/audience/preview` endpoint
    - Accept `target_audience` dict, return total count, per-source breakdown, first 20 matches
    - _Requirements: 13.8_

  - [x] 8.6 Add `POST /campaigns/audience/csv` endpoint per Requirement 35
    - Accept multipart upload; enforce **2 MB file size limit, 5,000 row limit**
    - **Auto-detect encoding:** UTF-8, UTF-8-BOM, Latin-1, Windows-1252
    - Require `phone` column (case-insensitive, label-matched, order-independent); optional `first_name`, `last_name`
    - Normalize phones via `phone_normalizer.py`; skip malformed rows with row-level error reporting
    - Dedupe within file to first occurrence; report duplicate count
    - Return `upload_id`, matched-to-customer / matched-to-lead / will-become-ghost-lead / rejected breakdown
    - Ghost leads NOT created until final send (to avoid orphans from abandoned wizards)
    - **Staff attestation:** request body must include `staff_attestation_confirmed=true`, `attestation_text_shown`, `attestation_version`. On final send confirmation, call `consent.bulk_insert_attestation_consent(staff_id, phones, attestation_version, attestation_text)` to create `SmsConsentRecord` rows
    - Require `require_admin` permission dependency (Admin only per Requirement 31)
    - Emit `sms.csv_attestation.submitted` audit event with actor, upload_id, phone_count, attestation_version
    - _Requirements: 13.9, 23.5, 25, 30, 31, 35, 41_

  - [x] 8.7 Write property test for CSV staff attestation (Property 34)
    - **Property 34: CSV staff attestation creates consent records**
    - **Validates: Requirement 25**

  - [x] 8.8 Commit CSV test fixtures in `tests/fixtures/csv/`
    - `valid_basic.csv`, `valid_with_bom.csv`, `valid_latin1.csv`, `malformed_phones.csv`, `mixed_formats.csv`, `duplicate_phones.csv`, `no_header.csv`, `extra_columns.csv`, `empty_file.csv`, `too_large.csv`, `too_many_rows.csv`
    - _Requirements: 45 (acceptance criteria 4)_

- [x] 9. Checkpoint — Phase 4 complete
  - Ensure all tests pass, ask the user if questions arise.
  - Verify: audience filters work for all three sources, deduplication correct, preview endpoint returns accurate counts, CSV upload stages correctly.

- [x] 10. Phase 5 — Communications Tab Full UI (3-Step Wizard)
  - [x] 10.1 Create frontend types in `features/communications/types/campaign.ts`
    - Define TypeScript interfaces: `Campaign`, `CampaignRecipient`, `TargetAudience`, `CustomerAudienceFilter`, `LeadAudienceFilter`, `AdHocAudienceFilter`, `AudiencePreview`, `CsvUploadResult`
    - _Requirements: 15.1, 22.6_

  - [x] 10.2 Create `features/communications/api/campaignsApi.ts` API client
    - Functions: `createCampaign()`, `sendCampaign()`, `previewAudience()`, `uploadCsv()`, `getCampaignProgress()`, `listCampaigns()`
    - _Requirements: 22.6_

  - [x] 10.3 Create React Query hooks in `features/communications/hooks/`
    - `useCreateCampaign.ts`, `useSendCampaign.ts`, `useAudiencePreview.ts`, `useAudienceCsv.ts`, `useCampaignProgress.ts`
    - _Requirements: 22.6_

  - [x] 10.4 Implement `AudienceBuilder.tsx` (Step 1 of wizard) — mixed-source recipient picker
    - Three additive source panels: Customers, Leads, Ad-hoc CSV (any or all can be used in one campaign)
    - **Customers panel:** search + filter (SMS opt-in default on, city, last service date range, tags, lead source) + multi-select table with checkboxes showing selected count
    - **Leads panel:** search + filter (SMS consent default on, status, lead source, intake tag, city, created date) + multi-select table with checkboxes showing selected count
    - **Ad-hoc panel:** CSV upload (2 MB/5000 row limits per Requirement 35) OR paste phones directly; shows matched-to-customer / matched-to-lead / will-become-ghost-lead breakdown
    - **Staff attestation checkbox** on the Ad-hoc panel with verbatim legal text (required per Requirement 25) — disabled Confirm button until checked
    - Running total at top: "X customers + Y leads + Z ad-hoc = N total (M after consent filter)"
    - Live preview via `POST /campaigns/audience/preview`
    - Dedupe warning for cross-source phone collisions ("N phones are in both your Customers selection and your CSV — they'll only be texted once")
    - Support `ids_include` pass-through for pre-populated selections from Customers/Leads tabs
    - _Requirements: 15.3, 15.4, 15.5, 15.6, 15.7, 25, 35_

  - [x] 10.5 Implement `MessageComposer.tsx` (Step 2 of wizard) per Requirement 34
    - Template textarea with merge-field insertion buttons (`{first_name}`, `{last_name}`)
    - **Dual character counter:** GSM-7 mode by default (160/153 per segment), auto-switch to UCS-2 mode (70/67 per segment) on any non-GSM char (including emoji)
    - Segment count badge with warning color above 1 segment: "This message will send as N segments per recipient — cost multiplies by N"
    - **Merge-field linter:** flag any `{token}` not in allowed list (`first_name`, `last_name`, `next_appointment_date`) underlined in red
    - **Live preview panel using REAL data:** fetch first 3 recipients from the current audience via `POST /campaigns/audience/preview` and render message per-recipient showing `"Grins Irrigation: " + body + STOP footer`
    - Empty merge field warning: "N recipients have no first_name — their message will say 'Hi ,'"
    - Sender prefix hardcoded to `"Grins Irrigation: "` (configurable via `SMS_SENDER_PREFIX` env var)
    - STOP footer auto-appended if not already present
    - Frontend segment counting logic MUST match backend `segment_counter.py` for consistency
    - _Requirements: 15.8, 15.9, 15.10, 34, 43_

  - [x] 10.6 Write property test for SMS segment count (Properties 25, 47)
    - **Property 25: SMS segment count**
    - **Property 47: SMS segment count for GSM-7 and UCS-2**
    - **Validates: Requirements 15.9, 43**

  - [x] 10.7 Implement `CampaignReview.tsx` (Step 3 of wizard) per Requirements 33, 36
    - **Per-source breakdown:** "X customers + Y leads + Z ad-hoc = N total"
    - **Consent filter breakdown:** "N total → M will send after consent filter (K blocked)"
    - **Time-zone warning (H1):** "P recipients have non-Central area codes. They will still be texted during the 8 AM–9 PM CT window. Per-recipient timezone enforcement is not yet supported." (uses `phone_normalizer.lookup_timezone()` to count)
    - Estimated completion time (recipients ÷ 140/hr), accounting for time-window gaps
    - Send now (respects time window) OR schedule for specific date/time — displayed in CT with note
    - **Send confirmation friction:** for audiences <50 recipients, standard confirm dialog; for ≥50, typed confirmation "Type **SEND N** below to confirm" with disabled button until match (Requirement 33)
    - Final confirm button is destructive-styled (red)
    - _Requirements: 15.11, 15.12, 33, 36_

  - [x] 10.8 Write property test for campaign time estimate (Property 26)
    - **Property 26: Campaign time estimate**
    - **Validates: Requirements 15.11**

  - [x] 10.9 Implement `NewTextCampaignModal.tsx` — 3-step wizard using shadcn Dialog
    - Wire AudienceBuilder → MessageComposer → CampaignReview with react-hook-form + zod validation
    - Step navigation with back/next/confirm
    - **Draft persistence (Requirement 33):** auto-save wizard state to `localStorage` under `comms:draft_campaign:{staff_id}` on every field change (debounced 500ms); on re-open prompt "You have an unsaved draft from {relative time} — Continue / Discard"; on first "Next" click also persist as DB `Campaign` row with `status='draft'` for cache-clear survival
    - Use UI status labels from Requirement 27 / §UX Specifications: "Queued" (pending), "Sending", "Sent" (NOT "Delivered"), "Failed", "Cancelled"
    - _Requirements: 15.2, 27, 33_

  - [x] 10.10 Implement `CampaignsList.tsx` — campaign list with progress bars and worker health indicator
    - Show active/scheduled/completed campaigns with status, recipient count, progress
    - **Worker health indicator:** green dot if `GET /campaigns/worker-health` shows `last_tick_at` within 2 min, red otherwise (polled every 30s via `useWorkerHealth` hook)
    - Use the Sent label (not "Delivered") with tooltip explaining we don't track handset delivery
    - Show rate limit status from worker-health response (e.g., "43/150 this hour")
    - _Requirements: 15.13, 27, 32_

  - [x] 10.11 Implement failed recipients / error recovery UI per Requirement 37
    - Failed campaigns display red "Failed" or yellow "Partial" badges in the list
    - Clicking a failed campaign opens detail view with per-recipient phone (masked last 4), source (customer/lead/ghost), failure reason, timestamp
    - Bulk actions: "Retry selected" (creates new `CampaignRecipient` rows with fresh `pending` state; original failed rows stay for audit) and "Mark all as do not retry"
    - "Cancel campaign" button transitions remaining `pending` rows to `cancelled`; `sending` rows allowed to finish naturally
    - Calls `POST /v1/campaigns/{id}/cancel` and `POST /v1/campaigns/{id}/retry-failed`
    - _Requirements: 37_

  - [x] 10.12 Edit `CommunicationsDashboard.tsx` to add "New Text Campaign" button and Campaigns tab
    - Add primary "New Text Campaign" button that opens `NewTextCampaignModal`
    - Add third tab: "Campaigns" showing `CampaignsList` + failed campaign details
    - _Requirements: 15.1, 15.13_

  - [x] 10.13 Write Vitest tests for campaign wizard components
    - Test wizard step navigation, AudienceBuilder panel switching and running total, MessageComposer character count (GSM-7 + UCS-2 boundaries), CampaignReview time estimate, typed confirmation friction for ≥50 recipients, draft persistence round-trip, form validation
    - Test worker health indicator (green/red states)
    - Test "Text Selected" entry from Customers tab and Leads tab
    - Test CSV upload with staff attestation checkbox
    - _Requirements: 15.2, 15.3, 15.8, 15.11, 33, 34_

  - [x] 10.14 Write property test for draft persistence (Property 50)
    - **Property 50: Draft auto-save round-trip**
    - **Validates: Requirement 33**

- [x] 11. Checkpoint — Phase 5 complete
  - Ensure all tests pass, ask the user if questions arise.
  - Verify: campaign wizard opens, audience builder works with all 3 sources, message composer shows preview, review step shows correct estimates, campaigns list displays progress.

- [x] 12. Phase 6 — Customers/Leads Tab Bulk Select Entry Points
  - [x] 12.1 Edit `CustomerList.tsx` to add checkbox column via TanStack Table row-selection API + sticky bulk-action bar with "Text Selected" button
    - When clicked, open `NewTextCampaignModal` with selected customer IDs pre-loaded into Customers panel
    - _Requirements: 16.1, 16.2, 16.3_

  - [x] 12.2 Edit `LeadsList.tsx` to add checkbox column + bulk-action bar with "Text Selected" button
    - When clicked, open `NewTextCampaignModal` with selected lead IDs pre-loaded into Leads panel
    - _Requirements: 16.4, 16.5, 16.6_

  - [x] 12.3 Write Vitest tests for bulk-select components
    - Test checkbox column rendering, bulk-action bar visibility, modal opening with pre-loaded IDs
    - _Requirements: 16.1, 16.4_

- [x] 13. Checkpoint — Phase 6 complete
  - Ensure all tests pass, ask the user if questions arise.
  - Verify: bulk select works on both Customers and Leads tabs, "Text Selected" opens wizard with correct pre-populated selections.

- [x] 14. Phase 7 — Polish and Twilio Swap Readiness
  - [x] 14.1 Rename `SentMessage.twilio_sid` → `provider_message_id` via Alembic migration
    - Non-breaking — column is nullable
    - _Requirements: 23.1_

  - [x] 14.2 Verify Twilio swap procedure works end-to-end
    - Set `SMS_PROVIDER=twilio`, restart, confirm `TwilioProvider` returned by factory
    - Verify rate limiter keys namespace by provider_name
    - _Requirements: 17.1, 17.2, 17.4_

  - [x] 14.3 Document Twilio swap procedure in README.md
    - Steps: verify 10DLC, set env vars, update webhook URL, restart, smoke test
    - _Requirements: 17.3_

- [x] 15. Final Checkpoint — All phases complete
  - Ensure all tests pass, ask the user if questions arise.
  - Run full test suite: `uv run pytest -v` (backend) and `npm test` (frontend)
  - Verify all **45 requirements** have coverage, all **50 correctness properties** have property-based tests, all **4 blockers (B1–B4)** resolved, all **13 structural gaps (S1–S13)** addressed (S2 simplified, S12 resolved).

## Notes

- Tasks marked with `*` were previously optional but are now all required
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation between phases
- Property tests validate universal correctness properties from the design document (Properties 1–50)
- All property-based tests go in `src/grins_platform/tests/unit/test_pbt_callrail_sms.py`
- Unit tests go in `src/grins_platform/tests/unit/`, functional tests in `tests/functional/`, integration tests in `tests/integration/`
- Frontend tests are co-located with components per project convention
- Phases are independently shippable — Phase 2 (CSV blast) can ship as soon as Phase 1 is complete
- **Phase 0 + 0.5 are COMPLETE** (2026-04-07). CallRail IDs captured, live API verified, state machine and policy decisions locked.
- **Phase 1 scope shrank after Phase 0.5:** removed the Redis sliding-window rate limiter (replaced with header-based tracker), removed the delivery-status webhook route (CallRail doesn't emit them), removed 3 env vars, removed the `sent → delivered` state transition. Added: `sending_started_at` migration, state machine module, consent type module, 5 Alembic migrations, audit log wiring, structured logging with phone masking, permission dependency functions, CSV staff attestation, row-level ghost lead lock, phone normalizer with area-code TZ lookup.
