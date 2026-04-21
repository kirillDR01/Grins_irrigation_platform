# Pick Jobs to Schedule — Persistent Tray (Combo 3)

Handoff package for building a new full-page job picker in the Grin's Irrigation Platform frontend.

## What this is

A design spec + scaffolded implementation for **`/schedule/pick-jobs`** — a full-page replacement for the current dialog-based job picker (`JobPickerPopup`). The key difference is a **persistent scheduling tray** pinned to the bottom of the viewport at all times, instead of a conditional popup that appears after selection.

## What's in this folder

| File | Purpose |
|---|---|
| `README.md` | You are here. Start-of-task orientation. |
| `SPEC.md` | **The meat.** Granular layout, state, interaction, and styling spec. |
| `CHECKLIST.md` | Walkable "done when…" list. Tick items as you build. |
| `combo3-reference.html` | Visual wireframe reference (open in a browser). Click the "★ Combo 3" tab to see the target design. Other tabs are alternative concepts — ignore them. |
| `data-shape.ts` | TypeScript types (re-exports from existing `features/schedule/types` where possible) + a mock data constant for local development. |
| `src-scaffold/` | Drop-in React/TSX scaffolds for the new page + sub-components. Uses real shadcn/ui imports and the existing hooks from `features/schedule/hooks`. |
| `screenshots/` | Key states: default, filtered, one selected, many selected, per-job adjustments open, empty state. |

## Order to build in

1. Read **SPEC.md** top to bottom.
2. Skim `combo3-reference.html` in a browser (click the Combo 3 tab) to see the wireframe. This is aesthetic reference only — the real implementation uses Tailwind + shadcn per the existing codebase.
3. Open the scaffolds in `src-scaffold/` and copy them into `frontend/src/features/schedule/`:
   - `src-scaffold/pages/PickJobsPage.tsx` → `frontend/src/features/schedule/pages/PickJobsPage.tsx`
   - `src-scaffold/components/FacetRail.tsx` → `frontend/src/features/schedule/components/FacetRail.tsx`
   - `src-scaffold/components/JobTable.tsx` → `frontend/src/features/schedule/components/JobTable.tsx`
   - `src-scaffold/components/SchedulingTray.tsx` → `frontend/src/features/schedule/components/SchedulingTray.tsx`
4. Wire up the route in the router (see SPEC §2).
5. Fill in the pieces marked `// TODO` in the scaffolds using the interaction rules in SPEC §4–§6.
6. Walk the **CHECKLIST.md** to verify.
7. Add tests mirroring the patterns in the existing `JobPickerPopup.test.tsx`.

## Existing code to reuse (do not reimplement)

| Existing export | Location | Use for |
|---|---|---|
| `useJobsReadyToSchedule()` | `features/schedule/hooks/useJobsReadyToSchedule.ts` | Fetching the job list |
| `useStaff({ is_active: true })` | `features/staff/hooks/useStaff.ts` | Staff dropdown |
| `useCreateAppointment()` | `features/schedule/hooks/useAppointmentMutations.ts` | Assigning selected jobs |
| `JobReadyToSchedule` type | `features/schedule/types.ts` | Job row shape |
| All `@/components/ui/*` shadcn primitives | `components/ui/` | Inputs, buttons, checkboxes, popovers, etc. |
| `LoadingSpinner` | `shared/components/LoadingSpinner.tsx` | Loading state in the table |
| `toast` from `sonner` | — | Success / failure feedback on assign |

## Existing code to deprecate (after the new page ships)

- `features/schedule/components/JobPickerPopup.tsx` — the old dialog. Mark as deprecated with a JSDoc note pointing at `/schedule/pick-jobs`. Do not delete in the same PR; leave one release for migration.
- Any callsites that open `JobPickerPopup` — change them to `navigate('/schedule/pick-jobs')` instead. Audit with a project-wide search for `JobPickerPopup`.

## Stack recap (confirmed from the repo)

- React 19 + TypeScript + Vite
- Tailwind v4, shadcn/ui (New York style), Radix primitives
- TanStack Query, react-hook-form + zod
- lucide-react icons, sonner toasts
- Inter font, teal-500 primary, slate-50 background, `rounded-lg/2xl`
- Feature-sliced folder layout (`features/<domain>/{api,components,hooks,types}`)
- `data-testid` on every interactive element (match existing conventions)

## Questions / deviations

If you need to deviate from the SPEC, leave a `// DEVIATION: <reason>` comment at the site of the change and add a bullet to a `DEVIATIONS.md` in this folder so the design reviewer can resolve it during review.
