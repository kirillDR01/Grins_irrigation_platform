# 2026-04-29 — Pre-existing TS errors suppressed by `// @ts-nocheck`

## Context

As part of the AI Scheduling System validation (`bughunt/2026-04-29-ai-scheduling-system-validation.md`),
`frontend/package.json#scripts.build` was changed from `vite build` to
`tsc -p tsconfig.app.json --noEmit && vite build` so the frontend build now fails
on TypeScript errors. This catches Bug-2-class regressions (TS errors masked by Vite's
no-typecheck build pipeline).

`tsc -p tsconfig.app.json --noEmit` on `dev` HEAD on 2026-04-29 surfaced **154 errors
across 31 unique files** that pre-date the AI scheduling work. These are unrelated to
the audit and need to be cleaned up by the owning feature teams.

## Why `// @ts-nocheck` instead of `tsconfig.app.json#exclude`

The original plan called for adding the 30 files to `tsconfig.app.json#exclude`. That
approach **does not work** in this repo because `tsconfig.app.json` has
`composite: true` (required by the root `tsconfig.json#references` setup). Under
composite mode, TypeScript re-includes any excluded file the moment another in-program
file imports it, raising a TS6307 error
(`File '...' is not listed within the file list of project '...'`). Verified
empirically: `shared/components/index.ts` re-imports `FilterPanel.tsx` and `Layout.tsx`
through `./FilterPanel` and `./Layout`, so excluding those files surfaces TS6307.

`// @ts-nocheck` is the documented TypeScript way to skip per-file type checking and
works correctly under `composite: true`. Each comment is one line at the top of a file,
greppable, and reviewable.

## Suppressed files (31)

Each file received a top-of-file marker:
`// @ts-nocheck — pre-existing TS errors documented in bughunt/2026-04-29-pre-existing-tsc-errors.md`

| File | Owning feature | Notes |
|---|---|---|
| `src/features/accounting/components/ReceiptCapture.tsx` | accounting | Unused `cn` import |
| `src/features/accounting/components/SpendingChart.tsx` | accounting | Recharts `Formatter` typing drift |
| `src/features/agreements/components/MrrChart.tsx` | agreements | Recharts `Formatter` typing drift |
| `src/features/agreements/index.ts` | agreements | Duplicate `AgreementDetail` export |
| `src/features/ai/components/MorningBriefing.tsx` | ai | `JobsByStatusResponse.requested` missing |
| `src/features/communications/components/CampaignResponsesView.tsx` | communications | Unused `downloadCsv` |
| `src/features/customers/components/CustomerForm.tsx` | customers | `id` access on `never` |
| `src/features/customers/components/InvoiceHistory.tsx` | customers | `CustomerInvoice.invoice_date` missing |
| `src/features/customers/components/MergeComparisonModal.tsx` | customers | `Record<string, unknown>` cast on `Customer` |
| `src/features/invoices/components/CreateInvoiceDialog.tsx` | invoices | `'closed'` not in `JobStatus` |
| `src/features/jobs/components/JobWeekEditor.tsx` | jobs | Unused `effectiveEnd` |
| `src/features/jobs/components/PaymentSection.tsx` | jobs | Unused `ShieldCheck` |
| `src/features/jobs/index.ts` | jobs | Stale `SimplifiedJobStatus`/`SIMPLIFIED_STATUS_*` re-exports |
| `src/features/leads/components/AttachmentPanel.tsx` | leads | `unknown` cast |
| `src/features/leads/components/LeadDetail.tsx` | leads | `string \| null` not assignable to `string \| undefined`; unused `FileText` |
| `src/features/leads/components/SheetsSync.tsx` | leads | Unused `status` |
| `src/features/marketing/components/CACChart.tsx` | marketing | Recharts `Formatter` typing drift |
| `src/features/resource-mobile/components/ResourceMobileView.tsx` | resource-mobile | **Bug 2 from validation audit** — fix in Phase 6 of plan, then remove `// @ts-nocheck` |
| `src/features/sales/components/SalesCalendar.tsx` | sales | `dogs_on_property`, `last_contacted_at` missing |
| `src/features/sales/components/SalesDashboard.tsx` | sales | Recharts `Formatter` typing drift |
| `src/features/schedule/components/AppointmentForm.tsx` | schedule | `last_contacted_at`, `preferred_service_time`, `dogs_on_property` |
| `src/features/schedule/components/AppointmentModal/PhotosPanel.tsx` | schedule | Unused `appointmentId` |
| `src/features/schedule/components/CalendarView.tsx` | schedule | `EventDropArg` rename in `@fullcalendar/interaction` |
| `src/features/schedule/components/JobTable.tsx` | schedule | `JobReadyToSchedule` missing; `verbatimModuleSyntax` type-only import |
| `src/features/schedule/components/SchedulingTray.tsx` | schedule | `JobReadyToSchedule` missing |
| `src/features/schedule/pages/PickJobsPage.tsx` | schedule | `JobReadyToSchedule` missing; `RefObject` nullability |
| `src/features/settings/components/BusinessSettingsPanel.tsx` | settings | `react-hook-form` resolver generics drift |
| `src/features/settings/components/EstimateDefaults.tsx` | settings | `react-hook-form` resolver generics drift |
| `src/features/settings/components/InvoiceDefaults.tsx` | settings | `react-hook-form` resolver generics drift |
| `src/shared/components/FilterPanel.tsx` | shared | `string \| undefined` index access (~25 violations) |
| `src/shared/components/Layout.tsx` | shared | `JobsByStatusResponse.requested` missing |

## Action items

- **AI scheduling Phase 6 (Bug 2)**: After `ResourceMobileView.tsx` is rewired to call
  `useResourceSchedule()` and pass `schedule={data}`, remove its `// @ts-nocheck` line.
- **Owning feature teams**: clean up the suppressed errors. Priority order suggested:
  1. `customers` (touches CRM core paths)
  2. `schedule` (overlap with AI scheduling)
  3. `settings` (multiple `react-hook-form` resolver issues — likely a single root cause)
  4. `shared/FilterPanel.tsx` (~25 violations, likely one fix pattern repeated)
  5. Recharts `Formatter` drift across `SpendingChart`, `MrrChart`, `CACChart`,
     `SalesDashboard` — one shared fix
- **Track**: link follow-up tickets here when filed.

## Verification

```bash
cd frontend && npx tsc -p tsconfig.app.json --noEmit; echo "exit=$?"
# Expected: 0 errors, exit=0
cd frontend && npm run build; echo "exit=$?"
# Expected: build succeeds, exit=0
```
