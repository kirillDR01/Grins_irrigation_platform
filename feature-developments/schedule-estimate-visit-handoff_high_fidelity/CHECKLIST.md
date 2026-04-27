# Schedule Estimate Visit — QA Checklist

Run this before opening the PR. The reference HTML is the visual ground truth —
side-by-side compare anything you're unsure about.

## Visual parity

- [ ] Modal width ~960px, two-column layout matches reference
- [ ] Customer card: dashed border, label-then-value rows, no edit affordance
- [ ] Form labels are uppercase 12px tracked, matches reference
- [ ] Calendar header: week label + "Mon Apr 20 – Sun Apr 26, 2026" range
- [ ] Day-of-week headers; today's date number is highlighted
- [ ] Time gutter shows hours only (no half-hour labels)
- [ ] 30-min slots, 6 AM – 8 PM; row height = 22px
- [ ] Past slots have diagonal stripe shading
- [ ] Now-line is a red 2px line with a dot at the left
- [ ] Existing estimates render hatched/tan with name + time + meta
- [ ] Selected pick renders solid orange with name + time + duration
- [ ] Conflicting pick + estimates flip to red

## Interaction

- [ ] Click empty slot → pick snaps to that slot, end = slot + current duration
- [ ] Drag across slots → pick spans the dragged range, end = last slot + 30min
- [ ] Drag is constrained to its origin day (cursor leaving column doesn't
      change which day the pick is on)
- [ ] Past slots are non-clickable (cursor: not-allowed)
- [ ] Form Date change moves calendar to that week if needed
- [ ] Form Start time change re-derives `end = start + currentDuration`
- [ ] Form Duration change re-derives `end = start + duration`; calendar updates
- [ ] Prev/Next/Today buttons navigate weeks; pick stays put
- [ ] Esc closes the modal; warns if pick is dirty
- [ ] Tab order matches §6.7 of SPEC

## Data

- [ ] Customer block reads from `entry.customer` — never editable here
- [ ] On open, fetch existing estimates for visible week (per §4.1)
- [ ] On week change, fetch (or hit cache) for the new `weekStart`
- [ ] On submit, POST per §4.2; replace entry in store with returned entry;
      advance stepper visibly
- [ ] On 409, surface the conflict warn area, re-fetch, keep modal open
- [ ] Re-schedule path (status = `estimate_scheduled`) uses PUT and pre-fills

## Conflict

- [ ] Pick that overlaps any same-date estimate flips colors AND shows banner
- [ ] Confirm button stays **enabled** in conflict state
- [ ] Non-overlapping picks on the same date do not flag conflict

## Accessibility

- [ ] Focus trap inside modal
- [ ] Esc closes
- [ ] Customer card has `role="group"` + label "Customer information"
- [ ] Conflict banner is `role="alert"`
- [ ] Form fields are labeled via `<label htmlFor>`, not just placeholder
- [ ] Calendar is not keyboard-navigable in v1; documented in `SALES-512`

## Responsive

- [ ] <720px: customer card → calendar → form fields, in that order
- [ ] Day columns stay readable at min width (test with calendar collapsed)
- [ ] Modal scrolls vertically when content exceeds viewport

## Telemetry

- [ ] Emit `sales.schedule_visit.opened` on mount with `{entryId, status}`
- [ ] Emit `sales.schedule_visit.pick` on each pick change with `{source: 'click'|'drag'|'field'}`
- [ ] Emit `sales.schedule_visit.confirmed` on successful submit
- [ ] Emit `sales.schedule_visit.cancelled` on dismiss-without-submit
