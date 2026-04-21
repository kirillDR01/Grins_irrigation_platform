# Gap 16 — No Unified SMS Inbox

**Severity:** 3 (medium — UX aggregation)
**Area:** Frontend (new page) + Backend (aggregating endpoint)
**Status:** Investigated, not fixed
**Related files (scattered data):**
- `job_confirmation_response` — Y/R/C parsed replies
- `reschedule_requests` — R-derived requests
- `campaign_responses` — poll replies + orphans
- `communications` — generic inbound/outbound log
- `sent_messages` — all outbound
- Various Alert types referencing these

---

## Summary

Inbound messages land in **four different tables** depending on the parse result and correlation:

1. **`job_confirmation_response`** — parsed Y/R/C to a correlated confirmation SMS.
2. **`reschedule_requests`** — R replies escalated to queue items; `requested_alternatives` on each.
3. **`campaign_responses`** — campaign-poll replies, including `status='orphan'` for inbound that couldn't be correlated.
4. **`communications`** — generic log of SMS (inbound + outbound) for historical purposes.

There's **no UI that aggregates these into a single inbound view.** Admins must triage across surfaces:

- Reschedule requests → `RescheduleRequestsQueue` on `/schedule`.
- No-reply escalations → `NoReplyReviewQueue` on `/schedule`.
- Customer-specific history → `CustomerDetail → Messages tab` (outbound-only, Gap 13).
- Orphan replies → **no UI at all.** Lives only in `campaign_responses` or `communications`.
- MMS or unrecognized replies → **no UI at all** (partially surfaced by Alert types if those exist, which they don't for most cases — Gap 14).

The "inbox" pattern that most SMS-integrated CRMs have (Gmail-like threading, everything in one place, triage and respond) is entirely absent.

---

## What's scattered across surfaces today

| Scenario | Landing table | Current UI |
|---|---|---|
| Customer Y to confirmation | `job_confirmation_response(status='confirmed')` | Indirect: appointment CONFIRMED badge. No direct reply view. |
| Customer R to confirmation | `reschedule_requests(status='open')` + `job_confirmation_response` | RescheduleRequestsQueue on /schedule |
| Customer C to confirmation | `job_confirmation_response(status='cancelled')` + Alert | CalendarView card goes gray, Alert on dashboard (once AT-1 from Gap 14 lands) |
| Customer free-text after R | `job_confirmation_response(status='reschedule_alternatives_received')` + updates `requested_alternatives` | Indirect: raw text in RescheduleRequestsQueue row |
| Customer free-text with no open request | `job_confirmation_response(status='needs_review')` | **None** — buried |
| Poll reply (parsed) | `campaign_responses(status='parsed')` | CampaignResponses export CSV (planned) |
| Poll reply (needs review) | `campaign_responses(status='needs_review')` | **None** |
| Poll reply (opt-out) | `campaign_responses(status='opted_out')` + `SmsConsentRecord` | Partial: consent record exists |
| Orphan (no correlation) | `campaign_responses(status='orphan')` | **None — completely invisible to admin** |
| STOP opt-out | `SmsConsentRecord` + dispatch | Partial: customer detail page preferences |
| Informal opt-out | `Alert(type='INFORMAL_OPT_OUT')` | **None — Gap 06** |
| MMS | Orphan or stripped text | **None — Gap 09** |
| Stale-thread replies | Routes to old appt, potentially wrong | **None — invisible bug** |

The "None" rows are the biggest gap — messages from customers that the system technically received but no admin will ever see unless they know to query the DB.

---

## Reproduction — orphan message invisibility

1. Customer replies to an old SMS thread that's been superseded but we haven't implemented superseded_at (Gap 03.B).
2. `find_confirmation_message` matches the old thread, routes to old appointment, status guard doesn't fire, `_handle_needs_review` runs, writes `job_confirmation_response(status='needs_review')`.
3. Admin never sees this. Customer expects a response. Silence.

Or:

1. Customer texts from a different number than we have on file. `handle_inbound` can't correlate to a customer. Falls through to `communications` table with `direction='inbound'` and no further action.
2. Row sits in `communications`. No one queries it.

---

## Proposed design — unified inbox page

New route: `/inbox` or `/communications/inbox`.

### Layout

Three-pane desktop (Gmail-like):

- **Left: filters / folders**
  - All
  - Needs triage (status='needs_review' | 'orphan' | new MMS)
  - Reschedule requests
  - Opt-outs pending
  - Archived / resolved
  - Per-customer search
- **Center: list**
  - Chronological list of inbound events.
  - Each row: direction icon, sender (customer name + phone), snippet, timestamp, status pill.
  - Color-coded by urgency.
- **Right: detail**
  - Full message body.
  - Correlated appointment (if any) — link to AppointmentDetail.
  - Customer profile link.
  - Action buttons: Triage, Reply (Phase 2), Archive, Link to appointment, Create reschedule request manually.

### Backend endpoint

`GET /api/v1/inbox?filter=X&cursor=Y&limit=Z` returns a merged, typed event stream:

```json
{
  "items": [
    {
      "id": "...",
      "timestamp": "2026-04-20T14:32:00Z",
      "source_table": "job_confirmation_response",
      "source_id": "uuid",
      "direction": "inbound",
      "customer_id": "uuid | null",
      "customer_name": "Jane Doe | null",
      "from_phone": "+1952...",
      "body": "Y",
      "parsed_keyword": "confirm",
      "correlated_appointment_id": "uuid | null",
      "status": "confirmed | needs_review | orphan | etc.",
      "triage_status": "pending | handled | dismissed"
    },
    ...
  ],
  "pagination": {"next_cursor": "..."}
}
```

Server-side UNION across four tables, sorted by timestamp, with pagination. Indexes on `received_at` and `status` where present.

### Triage workflow

Each inbound item has a `triage_status`: `pending | handled | dismissed`. Admin actions:

- **Triage → link to appointment** — for orphan messages, admin selects the appointment the reply is about. Backend writes a correction row (new `triage_actions` table) and updates the source row's correlation field.
- **Triage → create reschedule request** — for a "can we move it?" free-text that wasn't auto-routed.
- **Archive** — for messages that don't require action.
- **Reply** — Phase 2 with outbound compose.

---

## Data migration considerations

The four underlying tables weren't designed for a unified view. Potential work:

- Add `triage_status` + `triaged_at` + `triaged_by` columns to `job_confirmation_response`, `campaign_responses`, `communications` for admin state tracking.
- Consider a `SmsInboxView` materialized view or a `sms_events` table that's append-only and references the source.

Less disruptive: a runtime UNION via the endpoint, no schema changes. Slower at high volume but simple.

---

## Why this matters

- **Customer trust.** Currently, some customer replies vanish into the system. Even low-frequency message loss erodes trust.
- **Compliance.** 10DLC and CTIA best practices expect operators to track and respond to opt-out signals, support requests, and so on.
- **Admin efficiency.** Triaging across 3-4 UIs for a single customer's history is high-friction. A unified inbox collapses that.
- **Debugging.** Engineers troubleshooting "why didn't this confirmation work?" can start in one place.

---

## Dependencies

- **Gap 03** — without clean thread correlation, the inbox will have many orphan rows.
- **Gap 05** — audit coverage makes event sourcing cleaner.
- **Gap 06** — opt-out triage becomes an inbox folder.
- **Gap 13** — CustomerMessages is the per-customer slice of this; the inbox is the global view.
- **Gap 14** — alert-driven dashboard routes users to the relevant inbox folder.
- **Gap 15** — inbox needs realtime or aggressive polling.

---

## Phasing

1. **Inbox v0:** read-only, unified list, filter by triage_status, no reply composer. ~2 weeks.
2. **Inbox v1:** triage actions (link to appt, archive). +1 week.
3. **Inbox v2:** reply composer, template picker, consent-aware. +2 weeks.
4. **Inbox v3:** threading by customer, assignment (when multi-admin), realtime updates. +2-3 weeks.

Full effort ~6-8 weeks to get to a mature inbox. v0 provides immediate value by simply making invisible messages visible.
