# Implementation Plan: CallRail Scheduling Poll & Response Collection

## Overview

This plan implements the scheduling poll feature in 6 phases (A–F), layering on top of the already-complete CallRail SMS integration. Each phase builds incrementally: data model → service layer → API endpoints → frontend wizard → frontend responses view → smoke test. Backend is Python/FastAPI/SQLAlchemy async; frontend is React 19/TypeScript. Property-based tests use Hypothesis; unit tests use pytest; frontend tests use Vitest.

## Tasks

- [x] 1. Phase A — Data Model (Migration, ORM Model, Schemas)
  - [x] 1.1 Create Alembic migration for `campaigns.poll_options` column and `campaign_responses` table
    - Add `poll_options JSONB NULL` column to `campaigns` table
    - Create `campaign_responses` table with all columns per design: `id`, `campaign_id`, `sent_message_id`, `customer_id`, `lead_id`, `phone`, `recipient_name`, `recipient_address`, `selected_option_key`, `selected_option_label`, `raw_reply_body`, `provider_message_id`, `status`, `received_at`, `created_at`
    - Add CHECK constraint `ck_campaign_responses_status` for `('parsed', 'needs_review', 'opted_out', 'orphan')`
    - Create indexes: `ix_campaign_responses_campaign_id`, `ix_campaign_responses_phone_received_at`, `ix_campaign_responses_status`
    - All FKs use `ON DELETE SET NULL`
    - Include `downgrade()` that drops table and column in reverse order
    - Single migration file for atomic rollback
    - _Requirements: 1.6, 2.1, 2.2, 2.3, 2.4, 2.7_

  - [x] 1.2 Create `CampaignResponse` ORM model
    - File: `src/grins_platform/models/campaign_response.py`
    - Define all mapped columns matching the migration schema
    - Define relationships to Campaign, SentMessage, Customer, Lead (all `lazy="selectin"`)
    - Register model in `models/__init__.py`
    - _Requirements: 15.4_

  - [x] 1.3 Create Pydantic schemas for poll responses
    - File: `src/grins_platform/schemas/campaign_response.py`
    - `PollOption` with key (Literal `"1"`–`"5"`), label (1–120 chars), start_date, end_date, and `end_date >= start_date` validator
    - `CampaignResponseOut`, `CampaignResponseBucket`, `CampaignResponseSummary`, `CampaignResponseCsvRow`
    - _Requirements: 15.1, 15.2, 15.3_

  - [x] 1.4 Extend `CampaignCreate` and `CampaignUpdate` schemas with `poll_options`
    - Add `poll_options: list[PollOption] | None = None` field to both schemas in `schemas/campaign.py`
    - Add list validator: 2–5 entries with sequential keys starting from `"1"` when present
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 15.2_

  - [x] 1.5 Add `poll_options` mapped column to Campaign ORM model
    - Add `poll_options: Mapped[dict | None]` JSONB column to `models/campaign.py`
    - _Requirements: 1.1_

  - [x] 1.6 Write property test for PollOption validation round-trip
    - **Property 1: PollOption validation round-trip**
    - Test that valid PollOptions round-trip through JSON serialization/deserialization
    - Test that `end_date < start_date` is rejected
    - Test that list validator accepts only 2–5 entries with sequential keys
    - **Validates: Requirements 1.1, 1.2, 1.3, 15.1**

- [x] 2. Checkpoint — Phase A complete
  - Ensure all tests pass, ask the user if questions arise.
  - Verify: migration applies and rolls back cleanly, ORM model loads, schemas validate correctly

- [x] 3. Phase B — Response Service + Inbound Routing
  - [x] 3.1 Create `CampaignResponseRepository`
    - File: `src/grins_platform/repositories/campaign_response_repository.py`
    - Implement `add(row)` — insert a new campaign_responses row
    - Implement `get_latest_for_campaign(campaign_id)` — `DISTINCT ON (campaign_id, phone) ORDER BY received_at DESC`
    - Implement `list_for_campaign(campaign_id, option_key, status, page, page_size)` — paginated with latest-wins applied before pagination
    - Implement `iter_for_export(campaign_id, option_key)` — stream rows in batches of 100
    - Implement `count_by_status_and_option(campaign_id)` — grouped counts for summary
    - _Requirements: 14.1, 14.2, 14.3, 14.4, 14.5_

  - [x] 3.2 Create `CampaignResponseService`
    - File: `src/grins_platform/services/campaign_response_service.py`
    - Implement `correlate_reply(thread_resource_id)` — query `sent_messages WHERE provider_thread_id = :thread_id AND delivery_status = 'sent' ORDER BY created_at DESC LIMIT 1`
    - Implement `parse_poll_reply(body, poll_options)` — strip whitespace/punctuation, match single digit or `"Option N"` pattern, return ParseResult
    - Implement `record_poll_reply(inbound)` — orchestrate correlation → parsing → snapshot → insert
    - Implement `record_opt_out_as_response(inbound)` — correlate via thread_id, insert `status='opted_out'` row if campaign found
    - Implement `get_response_summary(campaign_id)` — latest-wins query grouped by option
    - Implement `iter_csv_rows(campaign_id, option_key)` — stream CSV rows with name split logic
    - Add structured logging: `campaign.response.received`, `campaign.response.correlated`, `campaign.response.orphan`, `campaign.response.parse_failed`
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 16.1, 16.2, 16.3, 16.4_

  - [x] 3.3 Wire `SMSService.handle_inbound()` to poll reply path
    - Modify `src/grins_platform/services/sms_service.py`
    - After STOP handling: call `record_opt_out_as_response()` for bookkeeping when `thread_id` is present
    - After informal opt-out: add poll reply branch — call `record_poll_reply()` when `thread_id` is present
    - If result is `parsed` or `needs_review`: return without writing to communications table
    - If result is `orphan`: fall through to existing `handle_webhook` handler
    - Ensure STOP bookkeeping is independent — failure does not block consent revocation
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 7.1, 7.2, 7.3, 7.4_

  - [x] 3.4 Write property tests for reply parser (Properties 2, 3, 4)
    - **Property 2: Reply parser valid-key round-trip** — for any valid option key K, `parse_poll_reply(K, options)` returns parsed with that key; also holds for whitespace/punctuation/`"Option N"` variants
    - **Property 3: Reply parser idempotence** — parsing same input twice produces identical results
    - **Property 4: Reply parser rejects unrecognized input** — non-digit, non-`"Option N"` strings return `needs_review`
    - **Validates: Requirements 4.1, 4.2, 4.3, 4.5, 17.4, 17.5**

  - [x] 3.5 Write property test for thread-based correlation (Property 5)
    - **Property 5: Thread-based correlation correctness** — returns most recent sent_message with matching `provider_thread_id` and `delivery_status='sent'`; null if none exists
    - **Validates: Requirements 3.2, 3.3, 3.5, 19.3**

  - [x] 3.6 Write property test for response status mapping (Property 6)
    - **Property 6: Response status mapping** — orphan when no campaign, needs_review when non-poll campaign, parsed/needs_review based on parser result for poll campaigns
    - **Validates: Requirements 5.1, 5.2, 5.3, 5.4**

  - [x] 3.7 Write property test for audit trail and raw body preservation (Property 7)
    - **Property 7: Append-only audit trail with raw body preservation** — N replies produce N rows, each with verbatim `raw_reply_body`, no rows deleted or updated
    - **Validates: Requirements 2.5, 5.6, 8.1, 8.4**

  - [x] 3.8 Write property test for latest-wins deduplication (Property 8)
    - **Property 8: Latest-wins deduplication** — `DISTINCT ON` query returns exactly one row per phone with the most recent `received_at`
    - **Validates: Requirements 8.2, 8.3, 10.3, 11.6**

  - [x] 3.9 Write property test for STOP bookkeeping independence (Property 12)
    - **Property 12: STOP bookkeeping independence** — STOP reply creates `opted_out` row; bookkeeping failure does not prevent consent revocation
    - **Validates: Requirements 6.2, 6.4**

  - [x] 3.10 Write property test for routing (Property 13)
    - **Property 13: Routing — parsed/needs_review replies don't duplicate to communications** — parsed/needs_review replies are not written to communications table; orphans are written to both
    - **Validates: Requirements 7.2, 7.3, 7.4**

  - [x] 3.11 Write unit tests for `parse_poll_reply`, `correlate_reply`, and `record_poll_reply`
    - File: `src/grins_platform/tests/unit/test_campaign_response_service.py`
    - Parametrized parser tests: valid digits, whitespace/punctuation, `"Option N"`, out-of-range, empty, ambiguous, unicode digits, spelled-out
    - Correlator tests: happy path, no match, failed delivery excluded, most recent wins
    - Recorder tests: orphan, non-poll campaign, parsed reply, needs_review reply, STOP bookkeeping
    - _Requirements: 17.1, 17.2, 17.3_

- [x] 4. Checkpoint — Phase B complete
  - Ensure all tests pass, ask the user if questions arise.
  - Verify: inbound replies are correctly correlated, parsed, and stored; STOP dual-recording works; orphans fall through to communications

- [x] 5. Phase C — API Endpoints
  - [x] 5.1 Add response summary endpoint
    - `GET /v1/campaigns/{id}/responses/summary` → `CampaignResponseSummary`
    - Returns `campaign_id`, `total_sent`, `total_replied`, `buckets` array with per-option counts
    - Uses latest-wins query for accurate counts
    - Requires Manager or Admin permission
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_

  - [x] 5.2 Add response list endpoint
    - `GET /v1/campaigns/{id}/responses` with optional `option_key`, `status`, `page`, `page_size` query params
    - Returns paginated `CampaignResponseOut` list
    - Applies latest-wins deduplication before pagination
    - Requires Manager or Admin permission
    - _Requirements: 10.1, 10.2, 10.3, 10.4_

  - [x] 5.3 Add CSV export endpoint
    - `GET /v1/campaigns/{id}/responses/export.csv` with optional `option_key` query param
    - Stream CSV with columns: `first_name`, `last_name`, `phone`, `selected_option_label`, `raw_reply`, `received_at`
    - Set `Content-Disposition: attachment; filename=campaign_{slug}_{date}_responses.csv`
    - Apply latest-wins deduplication; split lead names on first whitespace
    - Emit `campaign.response.csv_exported` structured log event with `campaign_id`, `row_count`, `actor_id`
    - Requires Manager or Admin permission
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6, 11.7, 11.8, 11.9, 16.5_

  - [x] 5.4 Write property tests for summary and CSV (Properties 9, 10, 11)
    - **Property 9: Summary bucket counts match latest-wins data** — bucket counts sum to `total_replied`, each count matches latest-wins rows for that `(status, option_key)`
    - **Property 10: CSV export content and filtering** — one row per latest-wins response, correct columns, `option_key` filter works
    - **Property 11: Lead name split for CSV** — first whitespace split produces correct `first_name`/`last_name`; single-token → empty last; null → both empty
    - **Validates: Requirements 9.2, 9.3, 11.2, 11.3, 11.4, 11.7, 14.5**

  - [x] 5.5 Write integration tests for poll response flow
    - File: `src/grins_platform/tests/integration/test_campaign_poll_responses_flow.py`
    - Test 1: Full webhook-to-response flow — create poll campaign, process recipient, synthesize inbound with body `"2"`, POST to webhook, verify `campaign_responses` row
    - Test 2: Summary endpoint — multiple replies → verify correct bucket counts
    - Test 3: CSV export — verify CSV content, column headers, `Content-Disposition` filename
    - Test 4: STOP dual-recording — verify both consent revocation and `opted_out` campaign_responses row
    - Test 5: Latest-wins deduplication — two replies from same phone → only most recent in summary and CSV
    - _Requirements: 18.1, 18.2, 18.3, 18.4, 18.5_

- [x] 6. Checkpoint — Phase C complete
  - Ensure all tests pass, ask the user if questions arise.
  - Verify: all 3 API endpoints return correct data, permissions enforced, CSV downloads correctly, integration tests pass

- [x] 7. Phase D — Frontend: Poll Options Editor
  - [x] 7.1 Add TypeScript types for poll options and responses
    - Extend `frontend/src/features/communications/types/campaign.ts` with `PollOption`, `CampaignResponseRow`, `CampaignResponseBucket`, `CampaignResponseSummary`
    - Extend `CampaignCreate` and `CampaignUpdate` types with `poll_options`
    - _Requirements: 12.7, 15.2_

  - [x] 7.2 Create `PollOptionsEditor` component
    - File: `frontend/src/features/communications/components/PollOptionsEditor.tsx`
    - "Collect poll responses" toggle at top of Message step
    - Editable list of 2–5 option rows: label input (auto-generated as `"Week of {start_date}"`), two date pickers, remove button
    - Remove button disabled at count == 2; "Add option" disabled at count == 5
    - Live preview of numbered options block appended to message body
    - Segment counter updated to include rendered options
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6_

  - [x] 7.3 Integrate `PollOptionsEditor` into campaign wizard
    - Wire into `MessageComposer` / `NewTextCampaignModal` Message step
    - Pass `poll_options` through campaign create/update API calls
    - _Requirements: 12.7_

  - [x] 7.4 Write component tests for `PollOptionsEditor`
    - Test toggle enables/disables the options editor
    - Test add/remove option buttons respect 2–5 limits
    - Test date validation (end >= start)
    - Test live preview renders correctly
    - _Requirements: 12.1, 12.2, 12.3, 12.4_

- [x] 8. Checkpoint — Phase D complete
  - Ensure all tests pass, ask the user if questions arise.
  - Verify: poll options editor renders correctly, options pass through to API, segment counter accounts for options

- [x] 9. Phase E — Frontend: Campaign Responses View
  - [x] 9.1 Create React Query hooks for response endpoints
    - File: `frontend/src/features/communications/hooks/useCampaignResponses.ts`
    - `useCampaignResponseSummary(campaignId)` — fetches summary endpoint
    - `useCampaignResponses(campaignId, params)` — fetches paginated response list
    - Query key factory for cache invalidation
    - _Requirements: 9.1, 10.1_

  - [x] 9.2 Create `CampaignResponsesView` component
    - File: `frontend/src/features/communications/components/CampaignResponsesView.tsx`
    - Header: total sent, total replied, total parsed, needs_review, opted_out counts
    - Per-option buckets: option key, label, count, "View" button, "CSV" button
    - Separate buckets for "Needs review" and "Opted out" with "View" buttons
    - "Export all responses as CSV" button via `<a href download>` anchor
    - Click "View" → drill-down table with columns: Name, Phone, Raw Reply, Received At
    - _Requirements: 13.1, 13.2, 13.3, 13.4, 13.5, 13.6_

  - [x] 9.3 Integrate `CampaignResponsesView` into communications dashboard
    - When a poll campaign is selected (`poll_options != null`), render `CampaignResponsesView`
    - Add "Responses" count column to `CampaignsList` for poll campaigns
    - Do not render for non-poll campaigns (`poll_options == null`)
    - _Requirements: 13.7_

  - [x] 9.4 Write component tests for `CampaignResponsesView`
    - Test summary header renders correct counts
    - Test per-option buckets display correctly
    - Test drill-down table renders on "View" click
    - Test CSV download link has correct href
    - Test component not rendered when `poll_options` is null
    - _Requirements: 13.1, 13.2, 13.3, 13.6, 13.7_

- [x] 10. Checkpoint — Phase E complete
  - Ensure all tests pass, ask the user if questions arise.
  - Verify: responses view renders summary and buckets, drill-down works, CSV download triggers correctly

- [x] 11. Phase F — Structured Logging + Final Polish
  - [x] 11.1 Verify all structured logging events are emitted
    - Confirm `campaign.response.received`, `campaign.response.correlated`, `campaign.response.orphan`, `campaign.response.parse_failed`, `campaign.response.csv_exported` events fire at correct points
    - Verify all phone fields use `_mask_phone()` helper — never log raw phone numbers
    - _Requirements: 16.1, 16.2, 16.3, 16.4, 16.5, 16.6_

  - [x] 11.2 Verify thread_resource_id storage on outbound sends
    - Confirm `CallRailProvider.send_text()` extracts `thread_resource_id` from `recent_messages[0].sms_thread.id` and stores as `provider_thread_id` on `SentMessage`
    - Confirm existing `provider_thread_id` column is populated for all campaign sends
    - _Requirements: 19.1, 19.2, 19.3_

- [x] 12. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.
  - Verify end-to-end: poll campaign creation → outbound send → inbound reply → correlation → parsing → response storage → summary view → CSV export
  - Confirm all 19 requirements are covered by implementation tasks
  - Confirm all 13 correctness properties have corresponding test tasks

## Notes

- All tasks are required
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation between phases
- Property tests validate universal correctness properties from the design document (Properties 1–13)
- Unit tests validate specific examples and edge cases from the parser table and correlator scenarios
- Integration tests validate the full webhook-to-CSV pipeline
- The design uses Python (FastAPI/SQLAlchemy) — no language selection needed
