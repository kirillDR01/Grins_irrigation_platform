# Schedule Estimate Visit — Spec

> Companion to `reference/Schedule-Estimate-Visit-Reference.html`. The HTML is
> the visual + interaction source of truth; this doc covers behavior, data,
> and edge cases the HTML doesn't make obvious.

---

## 1. Entry point

Triggered from the **Sales pipeline → entry detail** screen, Stage 1
("Schedule Estimate"), Now-card primary action:

```
[ 📅 Schedule visit ]   [ ✉ Text appointment confirmation ]
```

The button is enabled iff `entry.status === 'lead_captured'` (or
`'estimate_scheduled'` for re-schedule — see §6.4).

## 2. Layout

Two-column modal, ~960px wide, centered. **Left column (340px fixed)**:
read-only customer card + scheduling form fields. **Right column (fluid)**:
week calendar.

Mobile breakpoint (<720px): stack — customer card, then **calendar above
fields** (the calendar is the primary input). The form fields below the
calendar function as a "confirm what I picked" view.

## 3. State

There is **one** piece of derived state for the picked slot:

```ts
type Pick = {
  date: string;   // 'YYYY-MM-DD'
  start: number;  // minutes from midnight (e.g. 14:00 → 840)
  end: number;    // minutes from midnight, exclusive
} | null;
```

The form fields (`date`, `time`, `duration`, `assignee`) and the calendar
visualization are both **views** of `pick`. Mutations:

- Click an empty slot in the calendar → `pick = {date, start: slotMin, end: slotMin + currentDurationField}`.
- Drag across slots in the calendar → `pick = {date, start: minOfRange, end: maxOfRange + slotSize}`.
- Change the `Date` field → `pick.date = newDate`; if the new date is in a
  different week, scroll the calendar to that week.
- Change the `Start time` field → `pick.start = newMins`; `pick.end = newMins + currentDuration`.
- Change the `Duration` select → `pick.end = pick.start + newDuration`.
- Click "Today" → calendar week jumps to today. `pick` is **not** changed.
- Click "Prev/Next week" → calendar scrolls. `pick` is **not** changed.

If `pick` is `null`, the Confirm button is disabled and the calendar shows no
orange block.

## 4. Server contract

### 4.1 On open

No request needed if the entry detail page already has the customer block.
**Do** fetch existing estimate slots for the visible week:

```
GET /api/sales/estimates/calendar?weekStart=YYYY-MM-DD&assignee=:userId
→ 200
{
  estimates: Array<{
    id: string;
    date: string;            // 'YYYY-MM-DD'
    start: number;           // minutes from midnight
    end: number;
    customer_name: string;
    job_summary: string;     // e.g. "Spring startup"
    assigned_to: string;     // user id
  }>
}
```

Re-fetch when `weekStart` changes (Prev/Next/Today and form-field-driven jumps).
Cache by week — a session-lived `Map<weekStart, estimates[]>` is fine; no need
to invalidate during the modal session except on submit success.

### 4.2 On submit

```
POST /api/sales/:entryId/schedule-visit
{
  date: string;          // 'YYYY-MM-DD'
  start: number;         // minutes from midnight
  end: number;
  assigned_to: string;
  internal_notes?: string;
  send_confirmation_text?: boolean;  // toggle (default: true)
}
→ 200
{
  appointment_id: string;
  entry: SalesEntry;     // full updated entry; status is now 'estimate_scheduled'
}
```

On success: close modal, replace entry in the parent's store with the
returned `entry` (which advances the stepper), and toast
`"Visit scheduled for {fmtLongDate}, {fmtHM}"`.

On 409 (race — slot taken): show inline error in the conflict-warn area,
re-fetch the week, do **not** close the modal.

On other 4xx/5xx: toast `"Couldn't schedule. Try again or check connection."`,
modal stays open.

## 5. Calendar specifics

- **Hours:** 6 AM – 8 PM, fixed. (Out-of-hours requests are rare; one of the
  open Qs in §8 asks whether to add a "Show 24h" toggle.)
- **Slot size:** 30 minutes. All snapping is to 30-min boundaries.
- **Now-line:** red horizontal line on today's column at the current time.
  Updates on a 60s interval while the modal is open.
- **Past slots:** diagonal-stripe shaded; not clickable. (The reference HTML
  shades but still permits clicks; production should disable.)
- **Existing estimates:** rendered hatched/tan, read-only. Hover should show a
  tooltip with full info (`name · meta · time range`). Reference HTML doesn't
  do tooltips yet.
- **Conflict detection:** an estimate "conflicts" with the pick iff
  `!(estimate.end <= pick.start || estimate.start >= pick.end)` AND same date.
  When conflicting:
  - the pick block turns red (`.wkcal-pick.warn`)
  - the conflicting estimate block(s) get a red border (`.wkcal-evt.conflict`)
  - the inline warn banner appears under the form fields
  - **Confirm is still enabled** — overlap is allowed but called out. (Sales
    occasionally wants to double-book, e.g. Mike + Kirill split a 2hr.)
- **Conflict checks ignore assignee** in v1. If we add per-assignee filtering
  later (§8), conflict logic should restrict to the same `assigned_to`.

## 6. Edge cases

### 6.1 Pick falls outside currently-rendered week
When the user types a date (form field) that's not in the visible week, jump
the calendar to that week. Don't ask for confirmation.

### 6.2 Drag exits the day column
Drag is constrained to the day it started in. Moving the cursor to another
column does nothing — only the row index of the cursor's slot in the *origin*
column updates the end. (This matches how Google Calendar drag-create behaves.)

### 6.3 Drag into past slots
Allowed in the reference but **disallow in prod**: drag's range is clipped so
neither end goes earlier than `now` for today, or earlier than 6am for any day.

### 6.4 Re-schedule (existing appointment)
If `entry.status === 'estimate_scheduled'`, the modal opens with `pick`
pre-set to the existing appointment, the calendar scrolled to that week, and
the title reads **"Reschedule estimate visit"**. Submit hits
`PUT /api/sales/:entryId/schedule-visit` (same payload shape) instead of POST.

### 6.5 Empty-state — no estimates this week
Just show the empty grid. No "no events" copy needed.

### 6.6 Loading existing estimates
Show a thin shimmer band across the calendar body while fetching the first
time. Subsequent week navigations: skeleton bars in event positions only if
fetch takes >300ms, otherwise no flash.

### 6.7 Keyboard
- Esc closes the modal (warn if `pick` is set and dirty since open).
- Tab order: customer card (skip — read only) → date → time → assignee →
  duration → notes → cancel → confirm.
- Calendar is **not** keyboard-navigable in v1. Acknowledged a11y debt — the
  form fields are the keyboard-accessible path. Track as `SALES-512`.

### 6.8 Time zones
Server stores everything in the **business's local TZ**. The modal does not
expose TZ to the user — `start`/`end` minutes are local to that business.
Multi-TZ businesses are out of scope.

## 7. Copy

| Slot | Copy |
|---|---|
| Modal title | `Schedule estimate visit` (or `Reschedule estimate visit` — §6.4) |
| Subtitle | `Auto-populated from the lead record. Pick a time on the calendar — click a slot for a start time, or drag to set both start & duration.` |
| Pre-fill source label | `from Leads tab` |
| Confirm button | `📅 Confirm & advance to Send Estimate` (re-schedule: `📅 Update appointment`) |
| Cancel | `Cancel` |
| Conflict warn | `⚠ Overlaps with an existing estimate. You can still proceed, but double-check.` |
| Empty pick summary | `No time picked yet — click or drag on the calendar →` |
| Filled pick summary | `{LongDate} · {start}–{end} · {duration}` |
| Success toast | `Visit scheduled for {LongDate}, {start}` |

## 8. Open questions

1. **Per-assignee filtering of existing estimates.** v1 shows everyone's. Do
   we hide other assignees' blocks when an assignee is selected? (Recommend:
   show but desaturate.)
2. **Show 24h toggle.** A few customers do early/late visits. Worth adding now
   or wait for a request?
3. **Resize handles on the pick block.** Currently you can only resize via the
   Duration select. Reference is fine without; mention if user research wants it.

