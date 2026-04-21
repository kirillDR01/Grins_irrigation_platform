# Sales — Stage Walkthrough + Pipeline List · Handoff Package

**Target repo:** `kirillDR01/Grins_irrigation_platform`
**Branch to fork from:** `main`
**Frontend stack:** React 19 + TypeScript + Tailwind 4 + shadcn (Radix) + TanStack Query + date-fns + lucide-react + sonner
**Files touched:** `frontend/src/features/sales/**`

---

## What's in this package

| File | Purpose |
|---|---|
| `README.md` | You are here. Orientation + order of work. |
| `CHECKLIST.md` | Pull-request checklist. Every item must be checked before merge. |
| `SPEC-pipeline-list.md` | **Pipeline List** — full spec: data, columns, age-chip logic, filters, interactions, test IDs. |
| `SPEC-stage-walkthrough.md` | **Stage Walkthrough** — full spec: stepper, Now card per stage, activity strip, auto-nudge schedule. |
| `data-shapes.ts` | TypeScript types (source of truth — copy into `features/sales/types/`). |
| `reference/Sales-Reference.html` | **Standalone clickable reference.** Open in a browser; switch between the two panels with the top tabs. Use as visual ground truth. |
| `reference/screenshots/*.png` | Static screenshots of each panel + the key states. |
| `scaffold/PipelineList.tsx` | Drop-in replacement for `SalesPipeline.tsx`. |
| `scaffold/StageStepper.tsx` | Reusable 5-step stage stepper. |
| `scaffold/NowCard.tsx` | The stage-driven "Now" card. |
| `scaffold/ActivityStrip.tsx` | One-line activity feed. |
| `scaffold/AutoNudgeSchedule.tsx` | The `pending_approval` nudge block. |
| `scaffold/ageChip.tsx` | Age-in-stage chip + threshold helpers. |
| `scaffold/useStageAge.ts` | Hook: derive age + bucket from `updated_at`. |

> The **scaffold/** files are starter implementations that follow the repo's existing patterns (shadcn `Button`, `Card`, `Table`; lucide icons; Tailwind utility classes; `data-testid` on every interactive element). They compile against the repo as-is after copying into `frontend/src/features/sales/components/`.

---

## Recommended order of work

1. **Read** `SPEC-pipeline-list.md` and `SPEC-stage-walkthrough.md` end-to-end.
2. **Open** `reference/Sales-Reference.html` in a browser. Click every tab and every control. This is the ground truth for visual + interaction behaviour.
3. **Copy** `data-shapes.ts` into `frontend/src/features/sales/types/pipeline.ts` — merging with what's already there (new fields are additive; do not remove existing fields).
4. **Implement** the Pipeline List first — it's self-contained and blocks fewer things.
   - Replace `SalesPipeline.tsx` with `scaffold/PipelineList.tsx`.
   - Add `ageChip.tsx` + `useStageAge.ts`.
   - Verify against `reference/screenshots/02-pipeline-list.png`.
5. **Implement** Stage Walkthrough on top of `SalesDetail.tsx`.
   - Add `StageStepper`, `NowCard`, `ActivityStrip`, `AutoNudgeSchedule`.
   - Replace the current header block + action row in `SalesDetail.tsx` with the stepper + Now card.
   - Verify each stage against `reference/screenshots/03-walk-*.png`.
6. **Run** `CHECKLIST.md` before opening a PR.

---

## What this touches in the existing code

| Current file | Change |
|---|---|
| `frontend/src/features/sales/components/SalesPipeline.tsx` | **Replace** contents with new table (extra columns, age chips, compact action button). Summary cards on top stay. |
| `frontend/src/features/sales/components/SalesDetail.tsx` | **Insert** `<StageStepper />` + `<NowCard />` + `<ActivityStrip />` between header card and `DocumentsSection`. Keep `StatusActionButton` — it moves *inside* `NowCard` as the primary action. |
| `frontend/src/features/sales/types/pipeline.ts` | **Extend** with new stage `convert_to_job` (maps to existing `send_contract`), age thresholds, activity-event union. Existing statuses preserved. |
| `frontend/src/features/sales/hooks/` | **Add** `useStageAge.ts`, `useActivityFeed.ts`. No changes to `useSalesPipeline`. |

No backend changes required for v1. The activity strip consumes the existing `last_contact_date` + `updated_at` fields plus any `notes` timeline; the nudge schedule is client-side-computed from `updated_at`.

---

## Stage name reconciliation

The wireframe uses **`convert_to_job`** as the 4th stage. The repo currently calls this **`send_contract`**. We keep the DB enum untouched and add a display-layer alias:

```ts
// In SALES_STATUS_CONFIG
send_contract: {
  label: 'Convert to Job',   // <-- was 'Send Contract'
  className: 'bg-teal-100 text-teal-700',
  action: 'Convert to Job',
},
```

This is a **label-only change** — no migration, no API change. The word "Convert to Job" appears throughout the spec; in code it's still `send_contract`.

---

## What's deliberately **out of scope** for this package

- The scheduler modal (separate handoff).
- The Leads → Sales tab migration.
- Any backend / API / enum changes.
- Email/SMS nudge delivery (the UI just *shows* the schedule; wiring the cron job is a separate ticket).
- The tab chrome around the panels in the reference HTML (top "Detail / List / Walkthrough" tabs exist only in the wireframe for side-by-side comparison; the real app already has routing).
