# Requirements Document — CallRail Scheduling Poll & Response Collection

**Status:** Design phase — inbound webhook prerequisite verified (2026-04-08)
**Last updated:** 2026-04-09
**Parent spec:** `.kiro/specs/callrail-sms-integration/` (Phase 0–3 complete)

## Introduction

This feature extends the existing CallRail SMS integration to support scheduling poll campaigns. Staff compose a campaign with 2–5 numbered date-range options, send it to ~300 existing customers via the already-working outbound path, collect inbound SMS replies, parse digit-only responses, and export results as CSV for manual appointment scheduling. No auto-booking.

The inbound webhook is already scaffolded and verified against a real CallRail payload as of 2026-04-08 (see §11 of the reference document). Phone numbers are masked in CallRail inbound webhooks — correlation uses `thread_resource_id` matched to `sent_messages.provider_thread_id`, not phone-based lookup.

### Relationship to Parent Spec

This spec layers on top of `callrail-sms-integration`. The following are already complete and reused as-is:
- Provider abstraction (`BaseSMSProvider` / `CallRailProvider` / `NullProvider`)
- Outbound campaign send path (campaign worker, state machine, rate limit tracker)
- Inbound webhook route with HMAC-SHA1 signature verification
- `SMSService.handle_inbound()` with STOP/opt-out handling
- Unified `Recipient` model, consent system, templating, phone normalization
- `SentMessage` with `provider_thread_id` column (the correlation key)

### What This Spec Adds

1. Poll campaign creation (2–5 numbered date-range options stored as `poll_options` JSONB on `campaigns`)
2. Inbound reply parsing and correlation via `thread_resource_id`
3. `campaign_responses` table for storing parsed replies
4. Response viewing UI with per-option buckets and CSV export
5. STOP-as-opt-out bookkeeping in `campaign_responses`
6. Latest-wins deduplication at read time

## Glossary

- **Platform**: The Grin's Irrigation Platform CRM (FastAPI backend + React frontend)
- **Poll_Campaign**: A Campaign record with non-null `poll_options` JSONB column containing 2–5 numbered scheduling options
- **Poll_Option**: A single scheduling choice within a Poll_Campaign, identified by a digit key (`"1"`–`"5"`), a human-readable label, and a date range (start_date, end_date)
- **Campaign_Response**: A row in the `campaign_responses` table representing one inbound SMS reply correlated to a campaign
- **Reply_Parser**: The `parse_poll_reply()` function that extracts a digit option key from an inbound SMS body
- **Correlator**: The `correlate_reply()` function that matches an inbound SMS to a campaign via `thread_resource_id`
- **Response_Service**: The `CampaignResponseService` that orchestrates correlation, parsing, snapshotting, and persistence of poll replies
- **Thread_Resource_ID**: CallRail's per-conversation thread identifier (`SMT` + hex string), stable across all messages in a conversation, used as the canonical correlation key
- **Latest_Wins_Query**: A `DISTINCT ON (campaign_id, phone) ORDER BY received_at DESC` window query that resolves duplicate replies by keeping only the most recent per phone per campaign
- **Webhook_Endpoint**: The existing `POST /api/v1/webhooks/callrail/inbound` route that receives CallRail inbound SMS payloads
- **CSV_Export**: A streaming endpoint that produces a downloadable CSV file with columns: first_name, last_name, phone, selected_option_label, raw_reply, received_at

## Requirements

### Requirement 1: Poll Campaign Data Model

**User Story:** As a staff member, I want to create campaigns with numbered scheduling options, so that customers can reply with a digit to indicate their preferred date range.

#### Acceptance Criteria

1. WHEN a campaign is created with `poll_options` set, THE Platform SHALL store the poll_options as a JSONB column on the `campaigns` table containing an array of Poll_Option objects
2. THE Platform SHALL validate that each Poll_Option contains a `key` (digit string `"1"`–`"5"`), a `label` (1–120 characters), a `start_date`, and an `end_date`
3. WHEN poll_options are provided, THE Platform SHALL validate that the list contains between 2 and 5 entries with sequential keys starting from `"1"`
4. WHEN a Poll_Option has `end_date` earlier than `start_date`, THE Platform SHALL reject the campaign creation with a descriptive validation error
5. WHEN poll_options is null, THE Platform SHALL treat the campaign as a standard (non-poll) campaign with no change to existing behavior
6. THE Platform SHALL create an Alembic migration that adds the `poll_options JSONB` nullable column to the `campaigns` table

### Requirement 2: Campaign Responses Table

**User Story:** As a staff member, I want every inbound reply to be stored with the recipient's details and parsed option, so that I have a complete audit trail of poll responses.

#### Acceptance Criteria

1. THE Platform SHALL create a `campaign_responses` table with columns: `id` (UUID PK), `campaign_id` (nullable FK to campaigns), `sent_message_id` (nullable FK to sent_messages), `customer_id` (nullable FK to customers), `lead_id` (nullable FK to leads), `phone` (VARCHAR(32) NOT NULL, E.164), `recipient_name` (VARCHAR(200) nullable), `recipient_address` (TEXT nullable), `selected_option_key` (VARCHAR(8) nullable), `selected_option_label` (TEXT nullable), `raw_reply_body` (TEXT NOT NULL), `provider_message_id` (VARCHAR(100) nullable), `status` (VARCHAR(20) NOT NULL), `received_at` (TIMESTAMPTZ NOT NULL), `created_at` (TIMESTAMPTZ NOT NULL DEFAULT NOW())
2. THE Platform SHALL enforce a CHECK constraint on `status` allowing only the values: `parsed`, `needs_review`, `opted_out`, `orphan`
3. THE Platform SHALL create indexes on `campaign_responses` for: `campaign_id`, `(phone, received_at DESC)`, and `status`
4. THE Platform SHALL set all foreign keys to `ON DELETE SET NULL` so that audit data outlives deleted entities
5. THE Platform SHALL always store the verbatim inbound text in `raw_reply_body` regardless of parse outcome
6. THE Platform SHALL snapshot `recipient_name` and `recipient_address` at reply-receive time rather than joining on read, so that later customer edits do not alter historical records
7. THE Platform SHALL create an Alembic migration for the `campaign_responses` table and its indexes in the same migration file as the `poll_options` column addition


### Requirement 3: Inbound Reply Correlation via Thread Resource ID

**User Story:** As a staff member, I want inbound SMS replies to be automatically matched to the correct poll campaign, so that responses are attributed to the right campaign without manual intervention.

#### Acceptance Criteria

1. WHEN an inbound SMS arrives, THE Correlator SHALL extract the `thread_resource_id` field from the CallRail webhook payload
2. THE Correlator SHALL query `sent_messages WHERE provider_thread_id = :thread_resource_id ORDER BY created_at DESC LIMIT 1` to find the matching outbound message
3. WHEN a matching sent_message with a non-null `campaign_id` is found, THE Correlator SHALL return the associated Campaign and SentMessage
4. WHEN no matching sent_message is found, THE Correlator SHALL return a null result indicating an orphan reply
5. THE Correlator SHALL only consider outbound messages with `delivery_status` in (`sent`) as valid matches, excluding `failed` and `pending` rows
6. THE Correlator SHALL NOT use phone-based correlation because CallRail masks `source_number` in inbound webhooks (only last 4 digits visible)

### Requirement 4: Reply Parsing Rules

**User Story:** As a staff member, I want customer replies to be automatically parsed into option selections, so that I can see aggregated results without manually reading each reply.

#### Acceptance Criteria

1. WHEN parsing a reply, THE Reply_Parser SHALL strip leading and trailing whitespace and common punctuation (`.`, `,`, `!`, `)`) from the reply body
2. WHEN the cleaned reply is exactly a single digit `1`–`5` that matches a valid key in the campaign's poll_options, THE Reply_Parser SHALL return a `parsed` result with the matched option key
3. WHEN the cleaned reply starts with `"option "` (case-insensitive) followed by a single valid digit, THE Reply_Parser SHALL return a `parsed` result with the matched option key
4. WHEN the cleaned reply is a digit that does not match any key in the campaign's poll_options (e.g., `"6"` for a 3-option campaign), THE Reply_Parser SHALL return a `needs_review` result
5. WHEN the cleaned reply does not match any recognized pattern, THE Reply_Parser SHALL return a `needs_review` result
6. THE Reply_Parser SHALL NOT perform natural language parsing, fuzzy date matching, or multi-digit extraction from longer sentences
7. WHEN the reply contains ambiguous content such as `"2 or 3"`, THE Reply_Parser SHALL return a `needs_review` result rather than guessing

### Requirement 5: Response Recording Orchestration

**User Story:** As a staff member, I want every inbound reply to be recorded with the correct status and recipient details, so that the response summary is accurate and complete.

#### Acceptance Criteria

1. WHEN an inbound SMS is received and the Correlator finds no matching campaign, THE Response_Service SHALL insert a Campaign_Response row with `status='orphan'` and `campaign_id=NULL`
2. WHEN the Correlator finds a matching campaign that has null `poll_options`, THE Response_Service SHALL insert a Campaign_Response row with `status='needs_review'`
3. WHEN the Correlator finds a matching Poll_Campaign and the Reply_Parser returns a parsed result, THE Response_Service SHALL insert a Campaign_Response row with `status='parsed'`, the matched `selected_option_key`, and the corresponding `selected_option_label` snapshot
4. WHEN the Correlator finds a matching Poll_Campaign and the Reply_Parser returns a needs_review result, THE Response_Service SHALL insert a Campaign_Response row with `status='needs_review'` and `selected_option_key=NULL`
5. THE Response_Service SHALL snapshot the recipient's name and address from the matched customer or lead record at insert time
6. THE Response_Service SHALL always insert a new row on each inbound reply, preserving the full audit trail without overwriting previous responses

### Requirement 6: STOP Handling with Campaign Response Bookkeeping

**User Story:** As a staff member, I want STOP replies to both revoke consent and appear in the campaign response summary, so that I can see how many people opted out in response to a specific poll campaign.

#### Acceptance Criteria

1. WHEN an inbound SMS contains a STOP keyword, THE Platform SHALL continue to process the opt-out through the existing consent revocation path in `SMSService._process_exact_opt_out()`
2. WHEN an inbound STOP reply correlates to a campaign via thread_resource_id, THE Response_Service SHALL also insert a Campaign_Response row with `status='opted_out'` for that campaign
3. WHEN an inbound STOP reply does not correlate to any campaign, THE Platform SHALL process the opt-out normally without creating a Campaign_Response row
4. THE Platform SHALL ensure that the consent revocation and the Campaign_Response bookkeeping row are independent operations — failure to insert the bookkeeping row SHALL NOT prevent the consent revocation

### Requirement 7: Inbound Webhook Routing for Poll Replies

**User Story:** As a developer, I want the existing inbound webhook handler to route poll replies to the Response_Service, so that replies are processed without duplicating them in the generic communications table.

#### Acceptance Criteria

1. WHEN `SMSService.handle_inbound()` receives a non-STOP, non-opt-out inbound SMS, THE Platform SHALL call `Response_Service.record_poll_reply()` to attempt correlation and parsing
2. WHEN `record_poll_reply()` returns a Campaign_Response with `status` of `parsed` or `needs_review`, THE Platform SHALL return the response result without also writing to the generic communications table
3. WHEN `record_poll_reply()` returns a Campaign_Response with `status='orphan'`, THE Platform SHALL fall through to the existing generic `handle_webhook` handler so the reply lands in the communications inbox for staff review
4. THE Platform SHALL ensure that orphan replies are recorded in both the `campaign_responses` table (with `status='orphan'`) and the generic `communications` table

### Requirement 8: Latest-Wins Deduplication

**User Story:** As a staff member, I want to see only the most recent reply from each customer per campaign, so that the response summary reflects their final choice.

#### Acceptance Criteria

1. THE Platform SHALL always insert new Campaign_Response rows on each inbound reply without deleting or updating previous rows
2. WHEN querying responses for display or export, THE Platform SHALL apply a latest-wins window function: `DISTINCT ON (campaign_id, phone) ORDER BY received_at DESC` to return only the most recent reply per phone per campaign
3. THE Platform SHALL use the latest-wins query for the response summary counts, the per-option bucket lists, and the CSV export
4. THE Platform SHALL preserve all historical rows in the `campaign_responses` table for audit purposes regardless of the latest-wins filtering

### Requirement 9: Response Summary Endpoint

**User Story:** As a staff member, I want to see an overview of poll responses grouped by option with counts, so that I can quickly assess scheduling demand.

#### Acceptance Criteria

1. THE Platform SHALL expose a `GET /campaigns/{id}/responses/summary` endpoint that returns a `CampaignResponseSummary` payload
2. THE CampaignResponseSummary SHALL include: `campaign_id`, `total_sent` (count of campaign recipients), `total_replied` (count of unique phones that replied), and a `buckets` array
3. WHEN generating buckets, THE Platform SHALL group latest-wins responses by `selected_option_key` for parsed responses, plus separate buckets for `needs_review` and `opted_out` statuses
4. WHEN the campaign has no responses, THE Platform SHALL return a summary with `total_replied=0` and empty buckets
5. THE Platform SHALL require Manager or Admin permission to access the summary endpoint

### Requirement 10: Response List Endpoint

**User Story:** As a staff member, I want to drill down into individual responses filtered by option or status, so that I can review specific replies.

#### Acceptance Criteria

1. THE Platform SHALL expose a `GET /campaigns/{id}/responses` endpoint with optional query parameters: `option_key` (filter by selected option), `status` (filter by response status), `page`, and `page_size`
2. THE Platform SHALL return paginated `CampaignResponseOut` objects containing: id, campaign_id, phone, recipient_name, recipient_address, selected_option_key, selected_option_label, raw_reply_body, status, received_at
3. THE Platform SHALL apply the latest-wins deduplication before pagination
4. THE Platform SHALL require Manager or Admin permission to access the response list endpoint

### Requirement 11: CSV Export Endpoint

**User Story:** As a staff member, I want to export poll responses as a CSV file, so that I can manually schedule appointments from the results.

#### Acceptance Criteria

1. THE Platform SHALL expose a `GET /campaigns/{id}/responses/export.csv` endpoint that streams a CSV file
2. THE CSV SHALL contain columns: `first_name`, `last_name`, `phone`, `selected_option_label`, `raw_reply`, `received_at`
3. WHEN an optional `option_key` query parameter is provided, THE Platform SHALL export only responses matching that option
4. WHEN no `option_key` is provided, THE Platform SHALL export all responses (all statuses combined)
5. THE Platform SHALL set the `Content-Disposition` header to `attachment; filename=campaign_{slug}_{date}_responses.csv`
6. THE Platform SHALL apply the latest-wins deduplication before generating the CSV
7. THE Platform SHALL split recipient names for the CSV: Customer records use `first_name`/`last_name` directly; Lead records split on first whitespace (`first = tokens[0]`, `last = " ".join(tokens[1:])`)
8. THE Platform SHALL require Manager or Admin permission to access the CSV export endpoint
9. THE Platform SHALL emit a `campaign.response.csv_exported` structured log event with `campaign_id`, `row_count`, and `actor_id` for audit


### Requirement 12: Poll Options Wizard UI

**User Story:** As a staff member, I want to compose poll campaigns with a visual option editor in the campaign wizard, so that I can define scheduling choices with date ranges.

#### Acceptance Criteria

1. WHEN the "Collect poll responses" toggle is enabled in the Message step of the campaign wizard, THE Platform SHALL display an editable list of 2–5 option rows
2. THE Platform SHALL render each option row with: a label input (default auto-generated as `"Week of {start_date}"`), two date pickers for start and end dates, and a remove button
3. WHEN the option count is 2, THE Platform SHALL disable the remove button to enforce the minimum
4. WHEN the option count is 5, THE Platform SHALL disable the "Add option" button to enforce the maximum
5. THE Platform SHALL render a live preview of how the numbered options will appear in the message body, including the `"Reply with 1, 2, or N:"` instruction line
6. THE Platform SHALL update the SMS segment counter to account for the rendered options block appended to the message body
7. THE Platform SHALL pass the `poll_options` array through the campaign create/update API calls

### Requirement 13: Campaign Responses View UI

**User Story:** As a staff member, I want to view poll responses in the Communications tab under the campaign detail, so that I can see which options customers selected.

#### Acceptance Criteria

1. WHEN a poll campaign is selected in the campaign list, THE Platform SHALL render a `CampaignResponsesView` component showing the response summary
2. THE CampaignResponsesView SHALL display a header with: total sent, total replied, total parsed, total needs_review, and total opted_out counts
3. THE CampaignResponsesView SHALL display per-option buckets with: option key, option label, response count, a "View" button, and a "CSV" export button
4. THE CampaignResponsesView SHALL display separate buckets for "Needs review" and "Opted out" responses with "View" buttons
5. WHEN a "View" button is clicked, THE Platform SHALL display a drill-down table of individual responses with columns: Name, Phone, Raw Reply, Received At
6. THE CampaignResponsesView SHALL include an "Export all responses as CSV" button that triggers a browser download via the CSV export endpoint
7. WHEN a campaign has `poll_options = null`, THE Platform SHALL NOT render the CampaignResponsesView

### Requirement 14: Campaign Responses Repository

**User Story:** As a developer, I want a dedicated repository for campaign response data access, so that queries are encapsulated and reusable.

#### Acceptance Criteria

1. THE Platform SHALL implement a `CampaignResponseRepository` with methods: `add(row)`, `get_latest_for_campaign(campaign_id)`, `list_for_campaign(campaign_id, option_key, status, page, page_size)`, `iter_for_export(campaign_id, option_key)`, and `count_by_status_and_option(campaign_id)`
2. THE `get_latest_for_campaign` method SHALL execute the latest-wins `DISTINCT ON` query returning only the most recent response per phone per campaign
3. THE `list_for_campaign` method SHALL apply latest-wins deduplication before pagination and support optional filtering by `option_key` and `status`
4. THE `iter_for_export` method SHALL stream rows in batches of 100 to avoid loading all responses into memory
5. THE `count_by_status_and_option` method SHALL return a dictionary of counts grouped by status and option key for the summary endpoint

### Requirement 15: Pydantic Schemas for Poll Responses

**User Story:** As a developer, I want well-defined request and response schemas for poll campaign data, so that API contracts are validated and documented.

#### Acceptance Criteria

1. THE Platform SHALL define a `PollOption` Pydantic model with fields: `key` (Literal `"1"`–`"5"`), `label` (str, 1–120 chars), `start_date` (date), `end_date` (date), with a validator ensuring `end_date >= start_date`
2. THE Platform SHALL extend `CampaignCreate` and `CampaignUpdate` schemas with an optional `poll_options: list[PollOption] | None` field, validated to contain 2–5 entries with sequential keys when present
3. THE Platform SHALL define `CampaignResponseOut`, `CampaignResponseBucket`, `CampaignResponseSummary`, and `CampaignResponseCsvRow` schemas for the response API endpoints
4. THE Platform SHALL define a `CampaignResponse` SQLAlchemy ORM model with relationships to Campaign, SentMessage, Customer, and Lead

### Requirement 16: Structured Logging for Poll Responses

**User Story:** As a developer, I want structured log events for poll response processing, so that I can monitor and debug the inbound reply pipeline.

#### Acceptance Criteria

1. WHEN a campaign response is received, THE Platform SHALL emit a `campaign.response.received` INFO log event with `phone_masked`, `campaign_id`, `status`, and `option_key`
2. WHEN the Correlator successfully matches a reply to a campaign, THE Platform SHALL emit a `campaign.response.correlated` INFO log event with `phone_masked`, `campaign_id`, `sent_message_id`, and `thread_resource_id`
3. WHEN a reply cannot be correlated to any campaign, THE Platform SHALL emit a `campaign.response.orphan` INFO log event with `phone_masked`
4. WHEN the Reply_Parser cannot parse a reply, THE Platform SHALL emit a `campaign.response.parse_failed` INFO log event with `phone_masked`, `campaign_id`, and `reply_preview` (first 40 characters)
5. WHEN a CSV export is performed, THE Platform SHALL emit a `campaign.response.csv_exported` INFO log event with `campaign_id`, `row_count`, and `actor_id`
6. THE Platform SHALL use the existing `_mask_phone()` helper for all phone fields in log events, never logging raw phone numbers

### Requirement 17: Unit Tests for Poll Response Service

**User Story:** As a developer, I want comprehensive unit tests for the reply parser, correlator, and response recorder, so that correctness is verified before integration.

#### Acceptance Criteria

1. THE Platform SHALL include parametrized unit tests for `parse_poll_reply` covering: valid single digits, digits with whitespace/punctuation, `"Option N"` format (case-insensitive), out-of-range digits, empty strings, whitespace-only strings, ambiguous multi-digit replies, and non-digit text
2. THE Platform SHALL include unit tests for `correlate_reply` covering: happy path match via thread_resource_id, no matching sent_message, matched sent_message with `delivery_status='failed'` (excluded), and multiple sent_messages returning the most recent
3. THE Platform SHALL include unit tests for `record_poll_reply` covering: orphan (no campaign match), non-poll campaign match, poll campaign with parsed reply, poll campaign with needs_review reply, and STOP bookkeeping row
4. THE Platform SHALL include a property-based test verifying that `parse_poll_reply` is idempotent: parsing the same input twice produces the same result
5. THE Platform SHALL include a property-based test verifying the round-trip property: for any valid option key in a campaign's poll_options, `parse_poll_reply(key, options)` returns `parsed` with that key

### Requirement 18: Integration Tests for Poll Response Flow

**User Story:** As a developer, I want end-to-end integration tests for the full webhook-to-CSV flow, so that the entire pipeline is validated against a real database.

#### Acceptance Criteria

1. THE Platform SHALL include an integration test that: creates a poll campaign with 3 options, processes one recipient via the NullProvider, synthesizes an inbound webhook payload with body `"2"`, POSTs to the webhook endpoint with a valid HMAC signature, and verifies a `campaign_responses` row with `status='parsed'` and `selected_option_key='2'`
2. THE Platform SHALL include an integration test that calls `GET /campaigns/{id}/responses/summary` and verifies correct bucket counts after multiple replies
3. THE Platform SHALL include an integration test that calls `GET /campaigns/{id}/responses/export.csv` and verifies the CSV content and `Content-Disposition` filename header
4. THE Platform SHALL include an integration test verifying that a STOP reply creates both a consent revocation record and a `campaign_responses` row with `status='opted_out'`
5. THE Platform SHALL include an integration test verifying latest-wins deduplication: two replies from the same phone result in only the most recent appearing in the summary and CSV export

### Requirement 19: Thread-Based Correlation Key Storage

**User Story:** As a developer, I want the correlation key to be reliably stored on outbound messages, so that inbound replies can be matched accurately.

#### Acceptance Criteria

1. WHEN `CallRailProvider.send_text()` returns a successful response, THE Platform SHALL extract `thread_resource_id` (from `recent_messages[0].sms_thread.id` in the outbound response) and store it as `provider_thread_id` on the `SentMessage` row
2. THE Platform SHALL verify that the existing `provider_thread_id` column on `sent_messages` (added in the parent spec's Phase 1 migration) is populated for all campaign sends
3. WHEN the Correlator queries by `thread_resource_id`, THE Platform SHALL match against `sent_messages.provider_thread_id` using an exact string comparison

