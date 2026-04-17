# Lead Detail — Action Button Cleanup

**Date:** 2026-04-16
**Area:** Frontend / Leads
**Type:** UI enhancement

## Summary

On the Lead Detail page (e.g. the Patty Becker lead view), the top-right
action bar currently shows six buttons. Trim it to four. Remove the two
estimate/contract creation entry points that no longer belong in the
lead-stage workflow.

## Current state (screenshot reference: 2026-04-16 7:06 PM)

Buttons visible at the top of the Lead Detail page:

1. Mark as Contacted
2. Move to Jobs
3. Move to Sales
4. Create Estimate (blue outline)
5. Create Contract (purple outline)
6. Delete (red)

## Desired state

Only the following four buttons should remain:

1. Mark as Contacted
2. Move to Jobs
3. Move to Sales
4. Delete

## Buttons to remove

- **Create Estimate** — the blue outlined button with the calculator icon.
- **Create Contract** — the purple outlined button with the scroll icon.

## Rationale

Estimates and contracts belong to the Sales pipeline stage, not the Lead
stage. A lead should be routed (Mark Contacted / Move to Jobs / Move to
Sales) or removed (Delete) — not jumped straight into estimate/contract
creation from the lead view. Having those two buttons here invites users
to skip the Sales pipeline and create artifacts before the lead is
properly qualified.

## Implementation notes (for the engineer who picks this up)

File: `frontend/src/features/leads/components/LeadDetail.tsx`

- Remove the two `<Button>` blocks at lines ~350–367 (the Create Estimate
  and Create Contract buttons).
- Remove the `EstimateCreator` and `ContractCreator` component renders at
  the bottom of the file (lines ~792–793).
- Remove the related `useState` calls: `showEstimateCreator` and
  `showContractCreator` (lines ~121–122).
- Remove the imports for `EstimateCreator` and `ContractCreator` (lines
  ~77–78), and the now-unused `Calculator` and `ScrollText` icons from
  the `lucide-react` import block (lines ~38–39).
- Do **not** delete `EstimateCreator.tsx` / `ContractCreator.tsx` themselves
  yet — confirm with the user whether those creators are reachable from the
  Sales pipeline before removing the components. If they are orphaned after
  this change, that's a follow-up cleanup, not part of this task.
- Update any LeadDetail tests that assert on the `create-estimate-btn` or
  `create-contract-btn` test IDs.
