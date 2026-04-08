# CallRail Scheduling Poll & Response Collection — Feature Development Plan

**Status:** Design locked — blocked on inbound webhook prerequisite (see §2)
**Created:** 2026-04-08
**Owner:** TBD
**Primary business driver:** Text ~300 existing customers with 2–5 candidate date-range options for scheduling (e.g. "Week of Apr 13 / Week of Apr 20 / Week of Apr 27"), collect their picks via inbound SMS replies, and export the results as a CSV for staff to manually schedule appointments from. No auto-booking.

**Relationship to parent spec:** This is a narrow feature layered on top of `feature-developments/callrail/CallRail_SMS_Integration.md`. Phase 0 + 0.5 (outbound smoke test), Phase 1 blocker fixes, and the campaign worker are already complete and verified end-to-end as of 2026-04-08. This plan only adds the outbound "poll" shape, the inbound reply handling, the response store, and the CSV export.

---

## 1. Scope & Non-Goals

### 1.1 In scope

- Compose a campaign whose body contains 2–5 numbered scheduling options, each option labeled with a date range (start + end dates picked in the wizard).
- Send the campaign via the existing outbound path (already working).
- Receive inbound SMS replies via the CallRail inbound webhook.
- Parse digit-only replies (`1`, `2`, `3`) and correlate each reply back to the most recent campaign sent to that phone number within the last 14 days.
- Store each parsed reply as a row in a new `campaign_responses` table with the recipient's name, phone, address, selected option, and the raw reply body for audit.
- Surface the results in the Communications tab under the campaign's detail view: per-option buckets + counts, an individual list, and a one-click CSV export containing **first name, last name, phone, and selected option**.
- Continue honoring `STOP` as an opt-out regardless of whether the campaign was a poll. STOP replies record both the opt-out (existing consent path) AND a `campaign_responses` row with `status='opted_out'` for bookkeeping.

### 1.2 Non-goals (explicit)

- **No auto-scheduling.** The feature ends at "staff exports CSV and manually creates appointments." No Job, Appointment, or JobSlot records are auto-populated.
- **No natural language parsing.** `"the 20th works for me"` → needs_review. We only auto-categorize when the reply starts with or consists of a single digit that maps to a valid option.
- **No two-way conversation threading.** A separate conversations/inbox feature is tracked as a follow-up (see §10 Sequencing). This feature is one-shot poll replies only.
- **No per-recipient time window customization.** Reuses the existing CT-only 8 AM–9 PM enforcement from the parent spec.
- **No email channel.** SMS only. The existing `campaign_type` can still be `sms` or `both`, but poll options are only collected from SMS replies.

---

## 2. Hard Prerequisite: Inbound Webhook Must Be Wired Up

**This blocks the entire feature.** CallRail delivers inbound SMS only via webhook — there is no polling API for inbound messages. Until the webhook is configured and verified against a real inbound message, we cannot collect any replies, and nothing in §§3–8 below can be tested end-to-end.

### 2.1 What needs to happen before implementation starts

| Step | Owner | Notes |
|---|---|---|
| 1. Stand up a publicly reachable HTTPS URL that routes to `POST /api/v1/callrail/webhooks/sms/inbound` on the dev backend | Kirill + Claude | For dev: cloudflared or ngrok tunnel pointed at `localhost:8000`. For prod: deploy and use the deployed URL. |
| 2. Paste that URL into the CallRail dashboard under **Account Settings → Integrations → Webhooks → Text Messages** | Kirill (CallRail dashboard credentials) | Must be repeated per environment. |
| 3. Generate `CALLRAIL_WEBHOOK_SECRET`, paste into CallRail dashboard + `.env`, restart app | Kirill | Random 32+ char string. CallRail uses this to sign webhook payloads with HMAC-SHA256. |
| 4. Send a test outbound (we already have a working path) and reply from the allow-listed test phone `+19527373312` | Kirill | This is the one real inbound that pins down the exact payload shape. |
| 5. Capture the raw request body + headers from the app logs, save to `feature-developments/CallRail collection/sample_inbound_payload.json` | Claude | This becomes the golden fixture for all tests. |
| 6. Verify HMAC signature header name and algorithm against the captured sample | Claude | The parent spec's `CallRailProvider.verify_webhook_signature` assumes `x-callrail-signature` + HMAC-SHA256, but that's a guess. Must be confirmed against a real payload. |
| 7. Document exact payload field names (`customer_phone_number`, `content`, etc.) in §11 below once confirmed | Claude | Replaces the current guess in `callrail_provider.parse_inbound_webhook`. |

**No code in §§3–8 below should land on `main` until steps 1–7 are complete.** Implementing against an unverified payload shape risks silent parsing bugs that would only surface when a customer replies — exactly the moment we cannot afford to lose data.

### 2.2 Current state of the inbound path

Already scaffolded (from the overnight Ralph Wiggum run, commit `2e0a15f`):

- `src/grins_platform/api/v1/callrail_webhooks.py` — POST route exists
- `src/grins_platform/services/sms/callrail_provider.py::verify_webhook_signature` — HMAC verifier (unverified against real payload)
- `src/grins_platform/services/sms/callrail_provider.py::parse_inbound_webhook` — field extractor (unverified)
- `src/grins_platform/services/sms_service.py::handle_inbound` — routes exact STOP keywords through `_process_exact_opt_out`, fuzzy phrases through `_flag_informal_opt_out`, and everything else through `handle_webhook`

The poll-response handler in §5.3 plugs in as the *last* branch before the generic `handle_webhook` fallback.

---

## 3. Use Case Walkthrough (end-to-end)

**Staff flow (outbound):**
1. Staff opens Communications → "New Text Campaign"
2. Audience step: selects recipients (existing flow — customers / leads / CSV)
3. Message step:
   - New toggle: **"Collect poll responses"**
   - When enabled: shows a list input for 2–5 options, each with a label and a date-range picker (start date + end date)
   - The wizard auto-renders the options into the message body preview and computes segment count so the composer sees the final character budget
   - The raw message body can still be edited; the options block is inserted between the greeting and the `Reply STOP` footer
4. Review step: shows the final message, recipient count, and a reminder that replies will be collected for 14 days
5. Staff clicks "Send Now" → existing worker path delivers the SMS

**Customer flow (inbound):**
1. Customer receives the SMS:
   ```
   Grins Irrigation: Hi Jane! When would you like to schedule your spring startup? Reply with 1, 2, or 3:
   1 — Week of Apr 13
   2 — Week of Apr 20
   3 — Week of Apr 27
   Reply STOP to opt out.
   ```
2. Customer replies `2` (or `" 2 "`, `"2."`, `"Option 2"`)
3. CallRail POSTs the inbound to our webhook
4. Webhook verifies the HMAC signature, parses the payload, and calls `SMSService.handle_inbound()`
5. `handle_inbound` runs through its branches:
   - STOP / opt-out keywords → existing path (also records a `campaign_responses` row with `status='opted_out'`)
   - Poll reply path (new) → `CampaignResponseService.record_poll_reply()`
   - Fallback → existing generic `handle_webhook` writes to the `communications` table as an inbound message
6. `record_poll_reply` looks up the most recent `SentMessage` to this phone with `campaign_id IS NOT NULL` within the last 14 days
7. If a campaign is found AND it has `poll_options` configured AND the reply parses to a valid option → insert a `campaign_responses` row with `status='parsed'`
8. If not parseable → insert with `status='needs_review'` (and still captures the raw body)
9. If no matching campaign within 14 days → fall through to the generic inbound handler; the reply lands in `communications` but not in `campaign_responses`

**Staff flow (reviewing responses):**
1. Communications tab → Campaigns sub-tab → click the poll campaign
2. New "Responses" sub-view shows:
   ```
   Sent: 300   Replied: 47   Parsed: 42   Needs review: 3   Opted out: 2

   [Option 1] Week of Apr 13   — 18 responses   [View] [Export CSV]
   [Option 2] Week of Apr 20   — 14 responses   [View] [Export CSV]
   [Option 3] Week of Apr 27   — 10 responses   [View] [Export CSV]
   [Needs review]              —  3 responses   [View]
   [Opted out]                 —  2 responses   [View]

   [Export all responses as CSV]
   ```
3. Staff clicks "Export all responses as CSV" → browser downloads `campaign_<name>_<date>_responses.csv` with columns: `first_name, last_name, phone, selected_option_label, raw_reply, received_at`
4. Staff opens the CSV and manually schedules each person in their calendar / dispatch tool

---

## 4. Data Model

### 4.1 Extend `campaigns` table

Add one new column:

```sql
ALTER TABLE campaigns
  ADD COLUMN poll_options JSONB NULL;
```

- `NULL` means "not a poll campaign" (existing behavior preserved).
- When populated, schema is:
  ```json
  [
    {"key": "1", "label": "Week of Apr 13", "start_date": "2026-04-13", "end_date": "2026-04-19"},
    {"key": "2", "label": "Week of Apr 20", "start_date": "2026-04-20", "end_date": "2026-04-26"},
    {"key": "3", "label": "Week of Apr 27", "start_date": "2026-04-27", "end_date": "2026-05-03"}
  ]
  ```
- Constraint: the list must have between 2 and 5 entries; keys must be unique digit strings `"1"`–`"5"`; `start_date <= end_date`. Enforced in Pydantic on create, not as a DB CHECK constraint (dates are too awkward to express in CHECK).

### 4.2 New `campaign_responses` table

```sql
CREATE TABLE campaign_responses (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id         UUID NULL REFERENCES campaigns(id) ON DELETE SET NULL,
    sent_message_id     UUID NULL REFERENCES sent_messages(id) ON DELETE SET NULL,
    customer_id         UUID NULL REFERENCES customers(id) ON DELETE SET NULL,
    lead_id             UUID NULL REFERENCES leads(id) ON DELETE SET NULL,

    phone               VARCHAR(32) NOT NULL,            -- E.164, required
    recipient_name      VARCHAR(200) NULL,               -- snapshot at reply time
    recipient_address   TEXT NULL,                       -- snapshot at reply time
    selected_option_key VARCHAR(8) NULL,                 -- "1".."5" or NULL if needs_review
    selected_option_label TEXT NULL,                     -- "Week of Apr 20" snapshot

    raw_reply_body      TEXT NOT NULL,                   -- verbatim, never null
    provider_message_id VARCHAR(100) NULL,               -- CallRail's inbound message id

    status              VARCHAR(20) NOT NULL,            -- see §4.3
    received_at         TIMESTAMPTZ NOT NULL,            -- provider-reported receive time if available, else now()
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT ck_campaign_responses_status CHECK (
        status IN ('parsed', 'needs_review', 'opted_out', 'orphan')
    )
);

CREATE INDEX ix_campaign_responses_campaign_id ON campaign_responses(campaign_id);
CREATE INDEX ix_campaign_responses_phone_received_at ON campaign_responses(phone, received_at DESC);
CREATE INDEX ix_campaign_responses_status ON campaign_responses(status);
```

**Design choices:**
- **Snapshot fields** (`recipient_name`, `recipient_address`, `selected_option_label`) are captured at reply-receive time rather than joined on read. This protects the historical record from later customer edits (e.g. if the customer later changes their address, the booking response still shows what the address was when they replied).
- **All FKs are `ON DELETE SET NULL`** because audit data should outlive the entities it references. A deleted customer doesn't invalidate the fact that they responded.
- **`phone` is the only required identifier** — ad-hoc inbounds from phones not in our customer/lead tables still land here with `customer_id = lead_id = NULL`, matching the user's "just store the raw response" requirement from the brainstorm.
- **`raw_reply_body NOT NULL`** — we always keep the verbatim text even if parsing succeeded. Cheap insurance against parser bugs.

### 4.3 `status` enum values

| Value | Meaning | Creation path |
|---|---|---|
| `parsed` | Reply mapped cleanly to an option key defined in the matched campaign | Poll parser success |
| `needs_review` | We matched a campaign within the 14-day window but couldn't parse the reply to a valid option | Poll parser could not extract a digit OR digit was out of range for this campaign's options |
| `opted_out` | Reply was an opt-out keyword; recorded for the matched campaign as a bookkeeping entry | STOP path also inserts this |
| `orphan` | No campaign matched within the 14-day window. `campaign_id` is NULL. Stored for audit but not surfaced in the per-campaign response view. | Fallback when correlator finds nothing |

"Orphan" is new compared to the brainstorm; rationale: we still want to know *that* a reply came in even if we can't attribute it. It shows up in a separate "Unmatched replies" list on the main Communications page (not per-campaign). Alternatively we drop orphans entirely and let them land only in the generic `communications` table — flag this as an open question for Kirill.

### 4.4 What about duplicates? (latest wins)

Per the brainstorm, latest reply wins. Implementation: we **always insert** a new `campaign_responses` row on each inbound. Duplicates are resolved at **read time** via a window function that picks the most recent row per (phone, campaign_id). This preserves the full audit trail while giving the UI a "latest-wins" default. CSV export also uses the latest-wins view.

```sql
-- Read-time "latest per phone/campaign" view
SELECT DISTINCT ON (campaign_id, phone) *
FROM campaign_responses
WHERE campaign_id = :cid
ORDER BY campaign_id, phone, received_at DESC;
```

### 4.5 Alembic migration

New file: `src/grins_platform/migrations/versions/<timestamp>_add_campaign_poll_options_and_responses.py`

Contains:
1. `ALTER TABLE campaigns ADD COLUMN poll_options JSONB`
2. `CREATE TABLE campaign_responses ...`
3. The three indexes
4. `downgrade()` drops both in reverse order

---

## 5. Backend Design

### 5.1 Schema layer

New + modified Pydantic models in `src/grins_platform/schemas/campaign.py`:

```python
class PollOption(BaseModel):
    key: Literal["1", "2", "3", "4", "5"]
    label: str = Field(..., min_length=1, max_length=120)
    start_date: date
    end_date: date

    @model_validator(mode="after")
    def _check_date_order(self) -> "PollOption":
        if self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self


class CampaignCreate(...):
    ...
    poll_options: list[PollOption] | None = None

    @field_validator("poll_options")
    @classmethod
    def _validate_options(cls, v):
        if v is None:
            return v
        if not (2 <= len(v) <= 5):
            raise ValueError("poll_options must contain 2–5 entries")
        keys = [o.key for o in v]
        if keys != [str(i + 1) for i in range(len(v))]:
            raise ValueError("poll_option keys must be sequential '1', '2', ...")
        return v
```

New schemas:
- `CampaignResponseOut` — single response row (for detail lists)
- `CampaignResponseBucket` — one bucket in the summary (`option_key`, `option_label`, `count`, `responses`)
- `CampaignResponseSummary` — the full summary payload the Responses view renders
- `CampaignResponseCsvRow` — minimal row shape for the export endpoint (first_name, last_name, phone, selected_option_label, raw_reply, received_at)

### 5.2 New service: `CampaignResponseService`

File: `src/grins_platform/services/campaign_response_service.py`

Responsibilities:
1. **Correlate** an incoming reply to a campaign
2. **Parse** the reply text into an option key
3. **Snapshot** recipient name + address from the matched customer/lead
4. **Insert** a `campaign_responses` row with the correct `status`
5. **Query** responses grouped by option for the UI
6. **Stream** CSV rows for export

#### 5.2.1 `correlate_reply(session, phone, received_at) -> CorrelationResult`

Pseudocode:

```
e164 = normalize_to_e164(phone)
window_start = received_at - timedelta(days=14)

# Find the most recent outbound SentMessage to this phone with a
# campaign_id, sent within the 14d window.
stmt = (
    select(SentMessage)
    .where(
        SentMessage.campaign_id.is_not(None),
        SentMessage.recipient_phone.in_(_phone_variants(e164)),
        SentMessage.created_at >= window_start,
        SentMessage.delivery_status.in_(("sent", "delivered")),
    )
    .order_by(SentMessage.created_at.desc())
    .limit(1)
)
row = (await session.execute(stmt)).scalar_one_or_none()
if row is None:
    return CorrelationResult(campaign=None, sent_message=None)

campaign = await session.get(Campaign, row.campaign_id)
return CorrelationResult(campaign=campaign, sent_message=row)
```

Notes:
- Uses the same `_phone_variants` helper from `services/sms/consent.py` so bare 10-digit historical rows still match.
- Only considers outbound rows that actually reached the provider (`sent` / `delivered`), not `failed` / `pending` — a customer can't reply to a text that never left.
- `campaign.poll_options` being `None` is fine — the caller decides what to do with a non-poll campaign match (it just means the status will be `needs_review` for any non-STOP reply).

#### 5.2.2 `parse_poll_reply(body, options) -> ParseResult`

Rules (in order):
1. Strip whitespace and common punctuation (`.`, `,`, `!`, `)`, trailing period).
2. If the cleaned string is **exactly** a single digit `1`–`5` and that digit is a valid key in `options` → parsed, return that option.
3. If the cleaned string starts with `"option "` (case-insensitive) followed by a single valid digit → parsed.
4. Otherwise → needs_review.

**Deliberately not doing** (to avoid silent mis-categorization): fuzzy date matching, natural language parsing, yes/no detection, multi-digit extraction from longer sentences.

Examples:
| Reply | Cleaned | Result |
|---|---|---|
| `"2"` | `2` | parsed → key=2 |
| `"  2.  "` | `2` | parsed → key=2 |
| `"Option 2"` | `option 2` | parsed → key=2 |
| `"6"` (only 3 options exist) | `6` | needs_review |
| `"yes"` | `yes` | needs_review |
| `"the 20th works"` | `the 20th works` | needs_review |
| `"2 or 3"` | `2 or 3` | needs_review (refuses ambiguity) |
| `"STOP"` | n/a | routed to opt-out path before parser runs |

#### 5.2.3 `record_poll_reply(session, inbound: InboundSMS) -> CampaignResponse`

Orchestrates the full inbound-to-row flow:

```
1. e164 = normalize(inbound.from_phone)
2. corr = correlate_reply(session, e164, inbound.received_at or now)
3. if corr.campaign is None:
       status = 'orphan'
       option = None
       campaign_id = None
       sent_message_id = None
   elif corr.campaign.poll_options is None:
       # Matched a campaign but it's not a poll — still record as needs_review
       # so staff can see something came in
       status = 'needs_review'
       option = None
   else:
       parse = parse_poll_reply(inbound.body, corr.campaign.poll_options)
       status = 'parsed' if parse.ok else 'needs_review'
       option = parse.option if parse.ok else None

4. snapshot_name, snapshot_addr = snapshot_recipient(session, e164)
5. insert row, flush, return
```

Called from `SMSService.handle_inbound()` in the new "poll" branch (§5.3).

#### 5.2.4 `record_opt_out_as_response(session, inbound: InboundSMS) -> None`

Called from the **existing** STOP path inside `SMSService._process_exact_opt_out`. Runs correlation against the same 14-day window, and if a campaign matches, inserts a `campaign_responses` row with `status='opted_out'`. Does not touch consent records — that's still the existing code's responsibility.

#### 5.2.5 `get_response_summary(session, campaign_id) -> CampaignResponseSummary`

Runs the latest-wins window query from §4.4, groups by `selected_option_key`, and returns counts + per-bucket lists.

#### 5.2.6 `iter_csv_rows(session, campaign_id, option_key=None) -> AsyncIterator[CampaignResponseCsvRow]`

Streams rows for CSV export. `option_key=None` means "all responses" (all statuses combined). Fetches a sensible batch size (100) at a time so we can export a 300-customer response set without loading everything into memory.

**CSV format** (user-requested columns only):
```
first_name,last_name,phone,selected_option_label,raw_reply,received_at
Jane,Doe,+19527373312,Week of Apr 20,2,2026-04-10T14:22:03Z
John,Smith,+16125551212,Week of Apr 13,Option 1,2026-04-10T14:25:17Z
```

`first_name` / `last_name` split logic for the CSV (since leads store a single `name` column):
- Customer → use `customer.first_name` / `customer.last_name`
- Lead → split on first whitespace: `first = tokens[0]`, `last = " ".join(tokens[1:])` (handles `"Maria De La Cruz"` → `first="Maria"`, `last="De La Cruz"`)
- Ad-hoc / no match → empty strings
- If `recipient_name` snapshot is present (preferred), use that; fall back to live lookup only if snapshot is null

### 5.3 Wire `handle_inbound` to the new path

Modify `src/grins_platform/services/sms_service.py::handle_inbound`:

```python
async def handle_inbound(
    self,
    from_phone: str,
    body: str,
    provider_sid: str,
    received_at: datetime | None = None,
) -> dict[str, Any]:
    ...
    body_stripped = body.strip()
    body_lower = body_stripped.lower()

    # 1. Exact STOP keyword (existing)
    if body_lower in EXACT_OPT_OUT_KEYWORDS:
        result = await self._process_exact_opt_out(from_phone, body_lower)
        # NEW: also record as a campaign_responses bookkeeping row
        await self._response_service.record_opt_out_as_response(
            self.session,
            InboundSMS(
                from_phone=from_phone,
                body=body,
                provider_sid=provider_sid,
                received_at=received_at,
            ),
        )
        return result

    # 2. Informal opt-out (existing)
    if self._matches_informal_opt_out(body_lower):
        return await self._flag_informal_opt_out(from_phone, body_stripped)

    # 3. NEW: poll reply — try to correlate + parse
    poll_row = await self._response_service.record_poll_reply(
        self.session,
        InboundSMS(
            from_phone=from_phone,
            body=body,
            provider_sid=provider_sid,
            received_at=received_at,
        ),
    )
    if poll_row.status in ("parsed", "needs_review"):
        # We recognized this as a reply to a tracked campaign — don't
        # double-record it in the generic communications table.
        return {
            "success": True,
            "campaign_response_id": str(poll_row.id),
            "status": poll_row.status,
        }

    # 4. Fallback: generic inbound handler (existing) — used for orphans
    return await self.handle_webhook(from_phone, body, provider_sid)
```

Two subtle decisions here:
- **Orphans still fall through to `handle_webhook`** so they land in the `communications` inbox for staff review. They also get a `campaign_responses` row with `status='orphan'`, which is redundant with `communications` but lets the "all responses" CSV include them without the UI having to join two tables.
- **STOP double-records** intentionally — the opt-out path is the authoritative consent action, and the `campaign_responses` row is purely bookkeeping so staff can see "X people opted out in response to this campaign" in the summary view.

### 5.4 New API endpoints

All under `src/grins_platform/api/v1/campaigns.py`:

```
GET  /campaigns/{id}/responses/summary
     → CampaignResponseSummary (counts + per-bucket response lists)

GET  /campaigns/{id}/responses
     ?option_key=1|2|3|4|5     (optional)
     &status=parsed|needs_review|opted_out    (optional)
     &page, &page_size
     → paginated CampaignResponseOut list

GET  /campaigns/{id}/responses/export.csv
     ?option_key=1|2|3|4|5     (optional — export just one bucket, default all)
     → CSV stream with columns: first_name, last_name, phone, selected_option_label, raw_reply, received_at
        Filename: campaign_{slug(name)}_{date}_responses.csv
```

Also:

```
POST /callrail/webhooks/sms/inbound
     (existing route from overnight scaffolding — wire it to actually call
      SMSService.handle_inbound after signature verification)
```

**Permissions:** summary + list endpoints require `ManagerOrAdmin`. Export endpoint requires `ManagerOrAdmin`. The webhook endpoint is unauthenticated but HMAC-verified.

### 5.5 Repositories

New file: `src/grins_platform/repositories/campaign_response_repository.py`

Methods:
- `add(row: CampaignResponse) -> CampaignResponse`
- `get_latest_for_campaign(campaign_id) -> list[CampaignResponse]` (runs the `DISTINCT ON` query from §4.4)
- `list_for_campaign(campaign_id, *, option_key=None, status=None, page, page_size)` — paginated, already latest-wins filtered
- `iter_for_export(campaign_id, *, option_key=None) -> AsyncIterator[CampaignResponse]`
- `count_by_status_and_option(campaign_id) -> dict[str, int]` — for the summary header

### 5.6 Structured logging events (append to §10.5b of parent spec's event catalogue)

| Event | Level | Fields | Purpose |
|---|---|---|---|
| `campaign.response.received` | INFO | `phone_masked`, `campaign_id`, `status`, `option_key` | Observability |
| `campaign.response.correlated` | INFO | `phone_masked`, `campaign_id`, `sent_message_id`, `days_since_send` | Confirms correlator found a match |
| `campaign.response.orphan` | INFO | `phone_masked` | Reply came in with no matching campaign within 14 days |
| `campaign.response.parse_failed` | INFO | `phone_masked`, `campaign_id`, `reply_preview` (first 40 chars) | For tuning the parser later |
| `campaign.response.csv_exported` | INFO | `campaign_id`, `row_count`, `actor_id` | Audit trail for data exfiltration |

All phone fields use `_mask_phone` from the existing SMS service.

---

## 6. Frontend Design

### 6.1 Wizard changes — `NewTextCampaignModal.tsx` + Step 1 (`MessageComposer`)

Add a "Collect poll responses" toggle at the top of the Message step. When enabled, show:

- An editable list of 2–5 option rows, each with:
  - A label input (default `"Week of <start>"`, editable)
  - Two date pickers for start and end
  - A remove button (disabled when count == 2)
- An "Add option" button (disabled when count == 5)
- A live preview of how the options will be appended to the message body
- Segment counter that accounts for the rendered options

New TypeScript types in `frontend/src/features/communications/types/campaign.ts`:

```typescript
export interface PollOption {
  key: '1' | '2' | '3' | '4' | '5';
  label: string;
  start_date: string;  // ISO yyyy-mm-dd
  end_date: string;
}

export interface CampaignResponseRow {
  id: string;
  campaign_id: string;
  phone: string;
  recipient_name: string | null;
  recipient_address: string | null;
  selected_option_key: string | null;
  selected_option_label: string | null;
  raw_reply_body: string;
  status: 'parsed' | 'needs_review' | 'opted_out' | 'orphan';
  received_at: string;
}

export interface CampaignResponseBucket {
  option_key: string | null;
  option_label: string | null;
  count: number;
  status: 'parsed' | 'needs_review' | 'opted_out';
}

export interface CampaignResponseSummary {
  campaign_id: string;
  total_sent: number;
  total_replied: number;
  buckets: CampaignResponseBucket[];
}
```

Extend `CampaignCreate` and `CampaignUpdate` with `poll_options?: PollOption[] | null`.

### 6.2 New component: `CampaignResponsesView.tsx`

Rendered when staff clicks into a campaign that has `poll_options != null`. Layout:

```
┌─────────────────────────────────────────────────────┐
│  Responses for "SMS Campaign 4/10/2026"             │
│  Sent: 300    Replied: 47    Parsed: 42    Review: 3│
│                                    [Export all CSV] │
├─────────────────────────────────────────────────────┤
│  Option 1 — Week of Apr 13         18   [View] [CSV]│
│  Option 2 — Week of Apr 20         14   [View] [CSV]│
│  Option 3 — Week of Apr 27         10   [View] [CSV]│
│  Needs review                       3   [View]      │
│  Opted out                          2   [View]      │
└─────────────────────────────────────────────────────┘
```

Click a `[View]` → drill down to a filtered table of responses with columns: Name, Phone, Raw Reply, Received At. Table reuses the same styling as `SentMessagesLog`.

[View] and [Export CSV] buttons hit the endpoints in §5.4.

### 6.3 Integration with existing components

- `CampaignsList.tsx` — add a "Responses" count column (only shown if `campaign.poll_options != null`)
- `CommunicationsDashboard.tsx` — when a campaign is selected and it has `poll_options`, render `CampaignResponsesView` instead of `FailedRecipientsDetail` (or add a tabbed view showing both)

### 6.4 CSV download UX

Use a plain `<a href="/api/v1/campaigns/{id}/responses/export.csv" download>` anchor (not fetch), so the browser handles the file save natively and we don't have to blob it through the JS side. The endpoint sets `Content-Disposition: attachment; filename=...`.

---

## 7. Testing Strategy

### 7.1 Unit tests

File: `src/grins_platform/tests/unit/test_campaign_response_service.py`

- `parse_poll_reply` — parametrized test with every row from the table in §5.2.2, plus:
  - Empty string → needs_review
  - Whitespace only → needs_review
  - Unicode digits (`"２"`) → needs_review (we don't normalize exotic digit forms)
  - Lowercase `"option 1"` → parsed
  - `"Option One"` (spelled out) → needs_review (we said digit-only)
- `correlate_reply` — uses an in-memory SQLite session + fixtures:
  - Happy path: one campaign sent 2 days ago → matches
  - No campaigns → no match
  - Campaign sent 15 days ago → no match (outside window)
  - Two campaigns sent 1 day and 5 days ago → matches the 1-day one
  - Campaign sent but `delivery_status='failed'` → no match (can't reply to a failure)
  - Phone in bare 10-digit form in DB but e164 inbound → matches (phone variants)
- `record_poll_reply` — for each of: orphan, non-poll campaign matched, poll campaign matched + parsed, poll campaign matched + needs_review, STOP path bookkeeping row

### 7.2 Integration tests

File: `src/grins_platform/tests/integration/test_campaign_poll_responses_flow.py`

Full flow using the real Postgres test database:
1. Create a campaign with 3 poll options
2. Enqueue + process one recipient (worker path, no real CallRail call — uses the `NullProvider`)
3. Synthesize an inbound webhook payload for that phone with body `"2"`
4. POST to the webhook endpoint (with HMAC signature)
5. Verify `campaign_responses` row was created with `status='parsed'`, `selected_option_key='2'`
6. Call `/campaigns/{id}/responses/summary` and assert bucket counts
7. Call `/campaigns/{id}/responses/export.csv` and assert content + filename header

### 7.3 Manual smoke test plan (run after inbound webhook is wired up)

On the allow-listed test phone `+19527373312`:

1. Create a 3-option poll campaign, send to the test lead
2. Reply `2` from the phone → verify `campaign_responses` row lands with `status='parsed'`, option 2
3. Reply `nonsense` → verify a second row lands with `status='needs_review'`, latest-wins query returns this row (not the first one)
4. Reply `STOP` → verify opt-out consent record is created AND a `campaign_responses` row with `status='opted_out'` is inserted AND future outbounds to this number get blocked
5. Export CSV → verify the file downloads with the correct columns and the latest-wins row (the STOP one, since it's most recent)
6. Reset opt-out for test phone, repeat 2–5 with a 4-option campaign to verify the 2–5 range

### 7.4 What we deliberately are *not* testing in v1

- Concurrent inbound deliveries of the same reply (CallRail is the only sender; we trust single delivery)
- Rate limiting on inbound webhook (CallRail won't spam us; if it does that's a ops issue, not a correctness issue)
- Reply from international numbers (spec is CT-only, US numbers)

---

## 8. Open Questions for Kirill

Answered in the brainstorm, restated here for the record:

| # | Question | Decision |
|---|---|---|
| 1 | Options format — digits or letters? | Digits only (`1`–`5`) |
| 2 | Correlation window | 14 days |
| 3 | What counts as needs_review? | Claude's recommendation: anything that isn't a single digit (after stripping punctuation/whitespace) or `"option <digit>"`. No fuzzy matching. |
| 4 | Ad-hoc phones with no customer/lead match | Store raw response; `status='orphan'` if no campaign matches, otherwise `status='parsed'/'needs_review'` with `customer_id = lead_id = NULL` |
| 5 | STOP handling | Claude's recommendation: STOP runs through existing opt-out path AND writes a `campaign_responses` bookkeeping row with `status='opted_out'` |
| 6 | Auto-create Jobs/Appointments from responses? | No. v1 stops at CSV export. |
| 7 | Number of options | Configurable 2–5 |
| 8 | Duplicate replies | Latest wins (enforced at read time via `DISTINCT ON` window query) |

Still open / nice to confirm:

- **Q-A:** Should "orphan" responses surface anywhere in the UI, or are they invisible/audit-only? (Proposal: surface in a separate "Unmatched replies" section on the main Communications page, low priority.)
- **Q-B:** Should the CSV filename include the option label when exporting a single bucket, e.g. `campaign_spring_startup_option_2_week_of_apr_20.csv`? (Proposal: yes — less confusing when staff has multiple exports open.)
- **Q-C:** Should the `poll_options` UI let staff pre-fill the option label from the date range (e.g. auto-generate `"Week of Apr 13"` from `start_date=2026-04-13`)? (Proposal: yes, with an edit button to override.)

---

## 9. Out-of-Scope Follow-Ups (tracked here, not built)

These came up in the brainstorm but are explicitly deferred:

1. **Two-way conversation inbox** — a full threaded view of every SMS thread we've had with every phone number. The `campaign_responses` table handles the narrow poll case, but a general "conversations" feature would need a different surface. Tracked for a future session.
2. **Auto-creating appointments** from responses — would require date ranges to collide with a routing/dispatch engine. Not relevant until Grins has that engine.
3. **Fuzzy / NLP reply parsing** — would catch `"yes the 20th works"` and auto-assign. High risk of mis-categorization, low ROI on a 300-customer blast where staff can review the 3–5 needs_review replies by hand.
4. **Reply from the platform** (staff typing a custom reply back) — technically one POST to the existing CallRail send endpoint, but opens permission and rate-limit-accounting questions.
5. **Normalizing `customers.phone` to E.164 on write** — the consent-check workaround in `services/sms/consent.py::_phone_variants` handles both forms for now. A one-shot migration that rewrites all 112 customer rows to E.164 would let us delete the workaround. Low urgency since the workaround is 4 lines.
6. **Email poll responses** — the same mechanism could work for email with `EMAIL_OPT_OUT` tokens, but email reply-handling infra doesn't exist yet.

---

## 10. Sequencing (implementation order)

Rough phases once the blocking prerequisite (§2) is complete:

### Phase A — Data model (1–2 hours)
- [ ] Write Alembic migration for `campaigns.poll_options` + `campaign_responses` table
- [ ] Add `PollOption`, `CampaignResponseOut`, `CampaignResponseBucket`, `CampaignResponseSummary`, `CampaignResponseCsvRow` schemas
- [ ] Add `CampaignResponse` ORM model + relationships
- [ ] Run migration against dev DB, verify schema

### Phase B — Response service + inbound routing (3–4 hours)
- [ ] New `CampaignResponseRepository`
- [ ] New `CampaignResponseService` with `correlate_reply`, `parse_poll_reply`, `record_poll_reply`, `record_opt_out_as_response`, `get_response_summary`, `iter_csv_rows`
- [ ] Wire `SMSService.handle_inbound` to call the new service in the poll branch
- [ ] Unit tests for the service (§7.1)

### Phase C — API endpoints (2–3 hours)
- [ ] `GET /campaigns/{id}/responses/summary`
- [ ] `GET /campaigns/{id}/responses` (paginated, filtered)
- [ ] `GET /campaigns/{id}/responses/export.csv` (streaming)
- [ ] Hook up the already-scaffolded `POST /callrail/webhooks/sms/inbound` to invoke `handle_inbound` with the real webhook payload
- [ ] Integration test (§7.2)

### Phase D — Frontend wizard (2–3 hours)
- [ ] Extend `CampaignCreate` / `CampaignUpdate` TS types with `poll_options`
- [ ] Add "Collect poll responses" toggle + option editor to Message step
- [ ] Date range pickers per option row
- [ ] Live preview + segment counter update
- [ ] Ship the `PollOption[]` through the create/update calls

### Phase E — Frontend responses view (2–3 hours)
- [ ] `CampaignResponsesView` component
- [ ] Summary header with counts
- [ ] Bucket list with View / Export buttons
- [ ] Drill-down table (reuses `SentMessagesLog` styling)
- [ ] Download anchor for CSV export
- [ ] Wire into `CommunicationsDashboard` routing

### Phase F — Smoke test + polish (1–2 hours)
- [ ] Run §7.3 manual plan on the allow-listed test phone
- [ ] Fix whatever falls out
- [ ] Update this doc with "Status: Shipped" + a link to the merged PR

**Total rough estimate:** 11–17 focused hours spread over 2–3 days, assuming the inbound webhook prerequisite (§2) is resolved first.

---

## 11. Inbound Webhook Payload Reference (TO BE FILLED IN)

> This section is a placeholder. After step 4 in §2.1, paste the raw captured payload here and annotate each field with its meaning and the name our parser uses.

Expected fields (guessed from CallRail docs — unconfirmed):

| Field | Our parser uses | Notes |
|---|---|---|
| `customer_phone_number` | `inbound.from_phone` | The customer's phone (who sent the reply) |
| `content` | `inbound.body` | The reply text |
| `id` (or `message_id`?) | `inbound.provider_sid` | For idempotency/dedup (24h Redis key per parent spec) |
| `tracking_phone_number` | `inbound.to_phone` | Our CallRail tracking number (+19525293750) |
| `created_at` | `inbound.received_at` | Provider-reported receive time |
| `sms_thread.id` | TBD | Correlate to the outbound conversation thread |

HMAC signature header — **unconfirmed**. Currently assumed to be `x-callrail-signature` with HMAC-SHA256. To verify: check headers of the real inbound POST against `CALLRAIL_WEBHOOK_SECRET` using the `CallRailProvider.verify_webhook_signature` helper.

---

## 12. File Locations

Files that will be created or modified. Cross-reference when implementing.

**New files:**
- `src/grins_platform/migrations/versions/<timestamp>_add_campaign_poll_options_and_responses.py`
- `src/grins_platform/models/campaign_response.py`
- `src/grins_platform/schemas/campaign_response.py` *(or extend `schemas/campaign.py` — TBD)*
- `src/grins_platform/repositories/campaign_response_repository.py`
- `src/grins_platform/services/campaign_response_service.py`
- `src/grins_platform/tests/unit/test_campaign_response_service.py`
- `src/grins_platform/tests/integration/test_campaign_poll_responses_flow.py`
- `frontend/src/features/communications/components/CampaignResponsesView.tsx`
- `frontend/src/features/communications/components/PollOptionsEditor.tsx`
- `frontend/src/features/communications/hooks/useCampaignResponses.ts`

**Modified files:**
- `src/grins_platform/models/campaign.py` — add `poll_options: Mapped[dict | None]`
- `src/grins_platform/schemas/campaign.py` — add `PollOption`, extend `CampaignCreate` / `CampaignUpdate` with `poll_options`
- `src/grins_platform/services/sms_service.py::handle_inbound` — new branch calling `CampaignResponseService.record_poll_reply`
- `src/grins_platform/services/sms_service.py::_process_exact_opt_out` — call `record_opt_out_as_response` after recording the consent
- `src/grins_platform/api/v1/campaigns.py` — 3 new endpoints
- `src/grins_platform/api/v1/callrail_webhooks.py` — wire the existing POST route to `handle_inbound`
- `frontend/src/features/communications/types/campaign.ts` — add `PollOption`, `CampaignResponseRow`, `CampaignResponseBucket`, `CampaignResponseSummary`; extend `CampaignCreate` / `CampaignUpdate`
- `frontend/src/features/communications/components/NewTextCampaignModal.tsx` — pass poll options through create/update mutations
- `frontend/src/features/communications/components/MessageComposer.tsx` — render the `PollOptionsEditor`, update preview + segment counter
- `frontend/src/features/communications/components/CommunicationsDashboard.tsx` — route into `CampaignResponsesView` when a poll campaign is selected
- `frontend/src/features/communications/components/CampaignsList.tsx` — show "Responses" count column for poll campaigns

---

## 13. Revision Log

| Date | Author | Change |
|---|---|---|
| 2026-04-08 | Claude (Opus 4.6) | Initial plan based on brainstorm with Kirill. Scope, data model, service design, frontend design, testing strategy, sequencing all drafted. Blocked on inbound webhook prerequisite. |
