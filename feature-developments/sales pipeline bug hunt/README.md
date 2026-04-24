# Sales Pipeline Bug Hunt — 2026-04-23

End-to-end audit of the `handoff-stage-walkthrough-pipeline` feature against the spec at
`.kiro/specs/handoff-stage-walkthrough-pipeline/`. Tested live against the Vercel dev
deployment:

> https://grins-irrigation-platform-git-dev-kirilldr01s-projects.vercel.app/

Login: admin / admin123 (session already held).

Primary entries used for E2E walkthrough:

| Entry | ID | Role |
|---|---|---|
| Testing Viktor | `e5690e69-203b-4139-9379-87c41da8e80e` | Send Estimate → reproduce Skip bug, then Mark Lost |
| Brooke Jore | `5607f5ca-5993-4fdc-90f5-e66e738d0c38` | Full progression Plan → Sign → Approve → Close |

## TL;DR

The walkthrough **renders correctly** for all 5 stage variations and the `closed_lost`
banner. Stuck filter, status-card filter, Clear, and row navigation all work. BUT several
wiring bugs break the walkthrough end-to-end — most severe is that **"Skip — advance
manually" silently fails** (user-reported), and **"Schedule visit" doesn't open the
scheduling modal** the spec promises. The pipeline-list row action buttons are
**unwired** and do nothing when clicked. Full list in [bugs.md](./bugs.md).

## Files

| File | Purpose |
|---|---|
| [bugs.md](./bugs.md) | All bugs found, with severity, root cause, file:line, and suggested fix |
| [test-matrix.md](./test-matrix.md) | What was tested and what passed vs. failed per requirement |
| [screenshots/](./screenshots/) | 23 screenshots captured during the E2E walkthrough |

## Bug Summary

| # | Severity | Title |
|---|---|---|
| 1 | **Critical** | `Skip — advance manually` always fails (user-reported) |
| 2 | **Critical** | `Schedule visit` doesn't open a schedule modal; silently advances status |
| 3 | **High** | Pipeline-list row action buttons (Schedule/Send/Nudge/Convert/dismiss) have no `onClick` |
| 4 | **High** | `+ pick date…` chip in Week-Of picker does nothing (no Popover wired) |
| 5 | **High** | `⋯ change stage manually` stepper button does nothing (state is unused) |
| 6 | **High** | `AutoNudgeSchedule` never renders (host never passes `estimateSentAt`) |
| 7 | **Medium** | `View Job` navigates to `/jobs/{signwell_document_id}` — wrong field |
| 8 | **Medium** | Dropzone file upload is TODO stub; uploading a PDF only toasts "Not wired yet" |
| 9 | **Low** | `hasSignedAgreement` detection matches any `contract` doc, even unrelated ones |
| 10 | **Low** | Pagination text shows unfiltered total when stuck filter is active |
| 11 | **Low** | `Mark Lost` still clickable on `closed_won` entries → "Failed to mark as lost" toast |

## What Works (spec-compliant)

- Type system, `STAGES`, `AGE_THRESHOLDS`, `NUDGE_CADENCE_DAYS` constants in place
- `StageStepper` renders all 5 step states (done ✓, active, waiting w/ dashed amber for
  `pending_approval`, future); phase labels Plan / Sign / Close; calendar badge under
  Schedule when `estimate_scheduled`
- `NowCard` renders all 7 variations with correct pill tone (sky/amber/emerald), sanitised
  copy, locked+tooltip action variants
- `ActivityStrip` shows correct event glyphs per kind and accumulates events as entry
  progresses
- `AgeChip` renders correct colour + glyph per bucket; suppressed on `closed_won`/`closed_lost`
- `closed_lost` banner replaces walkthrough correctly
- Stub actions (`resend_estimate`, `pause_nudges`, `add_customer_email`,
  `text_confirmation`, file drop) toast "Not wired yet — TODO" as specified
- Client approved (manual) → `send_contract` via override mutation — works
- Client declined → `markLost` — works on non-terminal entries
- Jump to Schedule → `/schedule` — works
- View Customer profile → `/customers/{id}` — works
- Week-Of picker chip selection + localStorage persistence — works (persisted Apr 27 across
  a `closed_won` transition)
- Summary cards: Needs Estimate count, Pending Approval count, WoW delta copy, stuck filter,
  Clear filter, filter chips — all work
- Row click navigation to `/sales/{id}` — works (despite unwired action buttons)

## Known gaps from spec already acknowledged in the code

These are not bugs — the spec allows them as stubs with `TODO(backend)` comments:

- `text_confirmation`, `resend_estimate`, `pause_nudges`, `add_customer_email` — stub toasts
- `handleFileDrop` — stub toast (but the *Upload & send estimate* flow therefore has no
  way to supply the required PDF through the UI — see bug #8)
- Week-Of backend column (uses `localStorage` per design decision)
- `estimate_sent_at` / `stage_entered_at` backend columns (fall back to `updated_at`)

## Recommended fix order

1. Bug #1 (skip_advance) + Bug #5 (change stage manually) — both are direct user asks and
   both are one-line wiring fixes (swap `advance` for `overrideStatus` on skip; either wire
   or remove change-stage-manually)
2. Bug #6 (AutoNudgeSchedule never renders) — blocks a whole Req 11 sub-tree
3. Bug #3 (pipeline-list row buttons) — visually misleading; clicking a button on a row
   looks like nothing happens
4. Bug #4 (pick date) — medium effort but spec-required
5. Bug #2 (schedule modal) — medium-large effort; currently the advance-on-click behaviour
   is functional, just not spec-compliant
6. Bug #7, #8, #9, #10, #11 — follow-up polish
