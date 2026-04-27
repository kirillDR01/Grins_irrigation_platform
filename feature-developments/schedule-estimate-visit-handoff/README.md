# Schedule Estimate Visit — Developer Handoff

Hand-off package for the **Schedule estimate visit** modal that opens from the
Sales pipeline detail view (Stage 1 — *Schedule Estimate*).

## What's in this folder

```
schedule-estimate-visit-handoff/
├── README.md                ← you are here. start here.
├── SPEC.md                  ← detailed behavior, edge cases, copy
├── CHECKLIST.md             ← QA checklist before merge
├── reference/
│   └── Schedule-Estimate-Visit-Reference.html
│       ← clickable HTML/CSS reference. open in a browser.
│         drag/click on the calendar to pick a slot.
│         this is the source of truth for visual + interaction
│         until the React port is shipped.
└── scaffold/
    ├── data-shapes.ts       ← TS types for props, payloads, server contract
    ├── ScheduleVisitModal.tsx       ← top-level scaffold w/ state machine
    ├── PrefilledCustomerCard.tsx    ← read-only customer block (left col)
    ├── ScheduleFields.tsx           ← date / time / duration / assignee inputs
    ├── WeekCalendar.tsx             ← the 7-day grid (right col)
    └── useScheduleVisit.ts          ← shared hook: state, conflict check,
                                       persistence, submit
```

## Quick orientation (for the impl. dev)

This modal does **three things**:

1. **Show the user who they're scheduling for.** Customer/job pulled from the
   lead row; read-only here (edits live on the lead detail screen).
2. **Let them pick a time.** Two ways: type into the date/time/duration fields,
   *or* click/drag on the week calendar. Both views stay in sync.
3. **Confirm + advance.** On submit, write the appointment, advance the sales
   entry from `lead_captured` → `estimate_scheduled`, and close.

The hairy part is **#2**. See `SPEC.md` for the full state diagram. Short
version: there's one `pick` value (`{date, start, end}`) that's the source of
truth — both the form fields and the calendar are derived views, and edits to
either re-derive the other.

## How to use this package

1. Open `reference/Schedule-Estimate-Visit-Reference.html` in a browser. Click
   around. Drag on the calendar. Resize the window. This is the reference
   implementation — it's vanilla JS so you can read the source directly.
2. Read `SPEC.md` end-to-end before you start. It documents the state machine,
   the API contract, and a dozen edge cases you would otherwise hit at PR review.
3. Use the files in `scaffold/` as your starting skeleton. They aren't drop-in
   final code, but they fix the component decomposition, prop shapes, and naming
   so reviewers don't have to relitigate that.
4. Run through `CHECKLIST.md` before opening the PR.

## Out of scope (don't build these here)

- Editing customer/lead info (separate screen)
- Sending the appointment-confirmation SMS (already exists; this modal just
  fires the existing action on submit if the toggle is on)
- Calendar sync to Google/Outlook (tracked separately as `SALES-441`)
- Recurring appointments
- Multi-day appointments

## Questions / contacts

- **Design:** comments on this Claude project, or @design-systems on Slack
- **Backend contract:** see `SPEC.md` §4. If something there doesn't match the
  API, treat the API as truth and ping backend.
- **Existing components to reuse:** the app already has a `<Modal>`,
  `<Button variant="primary">`, `<TextField>`, `<Select>`, `<DateInput>`,
  and `<TextArea>`. Use those — the reference HTML inlines styles only because
  it's a standalone preview.
