# Mobile-viewport bug audit — Grin's Irrigation platform
**Date:** 2026-05-02
**Audience:** technician iPhone flow (admin pages also covered where they touch the tech)
**Test viewport:** iPhone 12 Pro — 390 × 844 (mobile-audit agent-browser session, headless Chromium)
**Method:** static-analysis grep → file reads → live capture → DOM `scrollWidth/clientWidth` probe per page
**Evidence dir:** `e2e-screenshots/mobile-bug-audit-2026-05-02/`

---

## Executive summary

The known **SheetContainer 560 px** bug is the tip of an iceberg. Three independent failure modes recur across the codebase:

1. **Hardcoded sub-sheet width inside a responsive parent.** `SheetContainer.tsx:26` (`w-[560px]`) is the only proven instance, but it's load-bearing — every estimate, payment, tag-edit and price-picker action a tech takes inside the appointment modal flows through it, so it clips on every iPhone interaction. *Already cited; included for completeness.* **(P0)**
2. **Tables wrapped in `overflow-hidden` instead of `overflow-x-auto`.** Pricelist (1438 px wide), Jobs (~1500 px), Customers (~1500 px), Leads (1523 px) and the customer-facing InvoicePortal/EstimateReview tables all clip silently — there is no horizontal scrollbar so tech & customer cannot see Edit/Deactivate/Status/Action columns at all. **(P1, several P0 for tech-facing list pages)**
3. **Page-level horizontal overflow** because heading-row buttons (`Sync Sheets`, `Bulk Outreach`, `+ Add Lead`) and shadcn `TabsList` rows do not wrap and have no horizontal scroll. Leads page overflows by **280 px**, Marketing by 138 px, Accounting by 151 px, Settings by 66 px. The whole page slides under a tech's thumb. **(P1)**

### Top 3 P0 bugs
1. **SheetContainer hardcoded `w-[560px]`** — known. Clips every estimate/payment/tag sub-sheet on iPhone.
2. **PriceListEditor table `overflow-hidden` wrapper** — tech cannot reach Edit/Deactivate/History buttons; entire right side of every row is invisible and unscrollable. Used by tech to amend pricing on-site.
3. **Leads page heading-row 280 px overflow** — admin-on-iPhone scrolls the whole page sideways just to use the page; no other page in the app does this.

---

## Bug catalogue

### BUG-1 — SheetContainer hardcoded width clips every appointment-modal sub-sheet (KNOWN, included for completeness)

- **Symptom:** "Save tag…" button cut, "Send Estima…" CTA cut, suggested tag chips ("+ Difficult…", "+ Gate code…") cut, sub-titles truncated.
- **Root cause:** `frontend/src/shared/components/SheetContainer.tsx:26` — `'flex flex-col w-[560px] bg-white …'`. Hardcoded 560 px width with no responsive breakpoint and no `max-w-full` clamp. Parent `AppointmentModal.tsx:374` is correctly `max-sm:w-full` (≈ 390 px on iPhone 12 Pro), but child demands 560 px inside `overflow-hidden` parent → clipped, not wrapped.
- **Affected viewports:** anything < ~600 px. iPhone 12 Pro 390 × 844 → DOM probe confirms `<div class="… w-[560px]">` rendered with `getBoundingClientRect().right === 577` inside a viewport of width 390 → ~187 px hidden behind the modal's right edge.
- **Reproduction:** `/schedule` → Day view → click any `[data-testid^=appt-card-]` → click "Edit tags" button.
- **Evidence:** `31-tag-editor-sheet.png` (subtitle "…across every job — pas" instead of "…past and future"; "+ Difficult" cut; "Save tag" cut). Also `appointment-modal-umbrella-tech-mobile-2026-05-02/phase-3/04-send-estimate-clicked.png` etc.
- **Severity:** **P0** — blocks tech from completing every primary appointment action.
- **Fix sketch:** swap `w-[560px]` → `w-full sm:w-[560px] max-w-full` (or `w-full sm:w-[560px] sm:max-w-[calc(100vw-2rem)]`).

---

### BUG-2 — PriceListEditor table hidden behind `overflow-hidden`

- **Symptom:** Tech sees "Name" column only. Customer / Category / Pricing model / Status / **Actions (Edit / Deactivate / History)** are all clipped off-screen, no horizontal scroll possible. Search input "Search name, slug, subcategory…" overflows the round border. Filter pills "All customer typ" truncate "type" → "typ".
- **Root cause:** `frontend/src/features/pricelist/components/PriceListEditor.tsx:233` — `<div className="rounded-md border border-slate-200 bg-white overflow-hidden">` wraps `<Table>`. Should be `overflow-x-auto`. Cells use `px-6 py-4 align-middle whitespace-nowrap` (shadcn default), making the natural table width `1438 px` per DOM probe — ~3.7× iPhone width.
- **Affected viewports:** anywhere the resolved table width > viewport — empirically anything ≤ 1438 px wide. Confirmed on iPhone 12 Pro 390 × 844; first-row `<TR>` measured 1438 px wide, clipped to 358 px visible.
- **Reproduction:** open `/invoices?tab=pricelist`. (Direct URL — there's no nav link other than the sidebar's "Pricebook" entry.)
- **Evidence:** `11-pricelist-table.png`. DOM probe: `[{tag:"TR", cw:1438, right:1456}, {tag:"TD", cw:499}, {tag:"DIV", cw:451}]`.
- **Severity:** **P0** — tech cannot edit a pricelist entry from a phone, period.
- **Fix sketch:** change `overflow-hidden` → `overflow-x-auto` on the wrapper div. Optional follow-up: collapse to a `<div className="md:hidden">` card layout for mobile.

---

### BUG-3 — Jobs list table hidden behind `overflow-hidden`

- **Symptom:** Same pattern. Right side of each row is `—` (the dash is the only visible content beyond JOB TYPE column header "SU…"). Status, source, customer, scheduled-for and actions columns are unreachable.
- **Root cause:** `<Table>` mount in `frontend/src/features/jobs/components/JobList.tsx` (parent wrapper inherits the same shadcn pattern as Pricelist). The shadcn `Table` defaults assume desktop viewport; cells use `px-6 whitespace-nowrap`. The page-level wrapper does not provide horizontal scroll.
- **Affected viewports:** iPhone 12 Pro 390 × 844 → page bodyOverflow = 0 (clipped), table TR likely > 1500 px (similar to Leads/Customers which DOM-probed at 1523 px and the same shadcn `Table` is used).
- **Reproduction:** open `/jobs`.
- **Evidence:** `20-jobs-list.png`.
- **Severity:** **P0** — entire job-management surface unusable on phone.
- **Fix sketch:** wrap the `<Table>` in a `<div className="overflow-x-auto">` or move to a card layout under `sm:`.

---

### BUG-4 — Customers list table hidden behind `overflow-hidden`

- **Symptom:** Phone column shows `612738530` (last digit clipped) — Email is partially visible (`christopher.ande…`) and any further columns (status, type, last-contact, actions) are off-screen with no scroll. Customer rows look ostensibly OK, but right-aligned actions column is gone.
- **Root cause:** Same shadcn `Table` + page wrapper pattern in `frontend/src/features/customers/components/CustomerList.tsx`.
- **Affected viewports:** ≤ table natural width (~1500 px). iPhone 12 Pro confirmed.
- **Reproduction:** open `/customers`.
- **Evidence:** `21-customers-list.png`.
- **Severity:** **P1** — admin can still find customers by name, but can't act on them from phone.
- **Fix sketch:** same — `overflow-x-auto` wrapper.

---

### BUG-5 — Leads page heading row overflows page by 280 px

- **Symptom:** The whole `/leads` page horizontally scrolls. The "Leads / 3 leads total / Syncing / Last sync 1 minute ago / [Sync Sheets] [Bulk Outreach (0)] [+ Add Lead]" row is rendered as `flex items-center gap-2` with width 583 px and right edge 670 px — ~280 px past viewport. Tabbing across this row drags the entire viewport sideways. Beneath it the leads `<Table>` is 1523 px wide and clipped.
- **Root cause:** `frontend/src/features/leads/components/LeadsList.tsx` (or the file that renders the header for the leads page) uses a horizontal flex row of buttons without `flex-wrap`. There is also a duplicate "Leads" heading (PageHeader from the route + an inner LeadsList header), exacerbating crowding.
- **Affected viewports:** iPhone 12 Pro 390 × 844 → DOM probe `document.body.scrollWidth - document.body.clientWidth === 280`.
- **Reproduction:** open `/leads`.
- **Evidence:** `40-leads-list.png`. DOM probe enumerated the `flex items-center gap-2` (w 583, right 670), the `Sync Sheets` button (w 170, right 534), and the `+ Add Lead` button (w 128, right 670) as the overflow culprits.
- **Severity:** **P1** — admin can still see something, but page-level horizontal scroll on phone is jarring and the table-overflow makes the page near-useless.
- **Fix sketch:** add `flex-wrap` to the heading-row flex; collapse PageHeader vs. LeadsList header into one; add `overflow-x-auto` to the leads table wrapper.

---

### BUG-6 — Schedule resource-timeline column headers concatenate into unreadable string

- **Symptom:** Week-view resource timeline header reads "MONTUEWEDTHUFRISATSU" and "4/2A/2B/2C/3D/3E/3F/3" — day names and dates have collapsed because the per-column min-width is too narrow to fit "MON" + "4/27" stacked vertically.
- **Root cause:** Schedule resource-timeline grid column widths. Likely `frontend/src/features/schedule/components/SchedulePage.tsx` (or the resource-timeline component it composes — check `frontend/src/features/schedule/components/JobsReadyToSchedulePreview.tsx` patterns and the resource-timeline view); each day column is sized so 7 fit alongside a fixed RESOURCES sidebar in a 390 px viewport, leaving ~30–35 px per column. "MON" is ~36 px wide, "4/27" is ~32 px → text from adjacent columns flows together.
- **Affected viewports:** iPhone 12 Pro 390 × 844 (Week view). Day view is unaffected.
- **Reproduction:** open `/schedule` (defaults to Week view).
- **Evidence:** `02-schedule-default.png`, `03-schedule-list.png`, `30-appointment-modal-default.png`.
- **Severity:** **P2** — cosmetic; the appointment cards themselves are still tappable, only the header is unreadable. Promote to P1 if a tech genuinely uses Week view on phone (confirm with the tech).
- **Fix sketch:** below `sm` breakpoint, default to Day view OR force the resource-timeline into horizontal scroll (`overflow-x-auto` on the timeline container) so each day column gets its natural width and the user pans.

---

### BUG-7 — `SearchableCustomerDropdown` PopoverContent fixed at 400 px

- **Symptom:** Customer-search popover (used in `CreateInvoiceDialog` and elsewhere) requests 400 px — wider than iPhone 12 Pro's 390 px. Radix typically clamps via `--radix-popover-available-width` so the right edge gets pinned and the popover renders flush to the viewport edge with no breathing room, but the content still expects 400 px.
- **Root cause:** `frontend/src/features/jobs/components/SearchableCustomerDropdown.tsx:111-112` — `<PopoverContent className="w-[400px] p-0 …">`.
- **Affected viewports:** any viewport < 400 px including iPhone 12/13/14/15 in portrait (375–393 px).
- **Reproduction:** could not directly trigger (required reaching CreateInvoiceDialog → invoice creation flow which crashed with "Request failed with status code 400" on `/invoices`). Static-analysis only.
- **Evidence:** `frontend/src/features/jobs/components/SearchableCustomerDropdown.tsx:111-112` (source). No screenshot.
- **Severity:** **P2** — Radix soft-clamps so the search input still functions, but customer rows overflow / wrap awkwardly.
- **Fix sketch:** `w-[min(400px,calc(100vw-1rem))]` or `w-[var(--radix-popover-trigger-width)]` (Radix-provided CSS var that matches the trigger).

---

### BUG-8 — Customer-facing portal tables (`InvoicePortal`, `EstimateReview`) wrapped in `overflow-hidden`

- **Symptom:** Same anti-pattern as the staff list pages. On iPhone, line-item descriptions, quantities and totals can be clipped if any line item has a long description, with no horizontal scroll. Customer is paying — they need to verify totals.
- **Root cause:**
  - `frontend/src/features/portal/components/InvoicePortal.tsx:155` — `<div className="bg-white rounded-xl border border-slate-200 overflow-hidden">` wraps a 4-column shadcn `<Table>`.
  - `frontend/src/features/portal/components/EstimateReview.tsx:220` — same pattern, 4-column table (Description column hidden on mobile via `hidden md:table-cell`, partly mitigated; Item column can still be long).
- **Affected viewports:** iPhone-class portrait. Whether it actually clips depends on data; with 1–3 word items and short totals it may render OK, but a long item like "Spring Startup — full property w/ winterization audit" pushes past the wrapper.
- **Reproduction:** generate a portal token and open `/portal/estimates/{token}` or `/portal/invoices/{token}` on a 390 px viewport with a long-named line item. (Could not auto-trigger in this audit — no portal token at hand.)
- **Evidence:** static-analysis only; no live capture.
- **Severity:** **P1** — customer-facing surface that determines whether a payment goes through. Even one cropped digit on a "Total" row creates a dispute.
- **Fix sketch:** swap `overflow-hidden` → `overflow-x-auto` on the table wrapper in both files.

---

### BUG-9 — Marketing & Accounting page Tabs row pushes past viewport

- **Symptom:** `/marketing` overflows by 138 px, `/accounting` by 151 px. The shadcn `TabsList` shows "Overview / Campaigns / Budget / QR Codes / CAC Analysis" (and Accounting's "Overview / Expenses / Tax / Connected Accounts / Audit Log") as a single horizontal row that does not wrap — its right edge ends past the 390 px viewport.
- **Root cause:** shadcn `<TabsList>` has no horizontal scroll affordance by default. These pages put 5 tabs in one row without overriding the layout. Look in `frontend/src/pages/Marketing.tsx` / `frontend/src/pages/Accounting.tsx` (the TabsList JSX).
- **Affected viewports:** iPhone 12 Pro 390 × 844 → bodyOverflow 138 / 151.
- **Reproduction:** open `/marketing` or `/accounting`.
- **Evidence:** `50-marketing.png`, `50-accounting.png`.
- **Severity:** **P2** — admin-only, but admin-on-phone is real. Currently the late tabs (CAC Analysis, Audit Log) are unreachable without scrolling the page sideways.
- **Fix sketch:** wrap the TabsList in a `<div className="overflow-x-auto -mx-4 px-4">` or apply `flex-wrap` to the TabsList itself.

---

### BUG-10 — Settings page footer overflows by 66 px

- **Symptom:** `/settings` body overflows by 66 px. Likely the bottom "Change Password" / "Sign Out" button row (visible at the bottom of `50-settings.png`) is rendered side-by-side but doesn't wrap; the rightmost button ("Sign Out") spills past viewport.
- **Root cause:** Settings page sign-out / change-password row layout. Confirm in `frontend/src/pages/Settings.tsx` or `frontend/src/features/auth/components/PasskeyManager.tsx`.
- **Affected viewports:** iPhone 12 Pro 390 × 844 → bodyOverflow 66.
- **Reproduction:** open `/settings`, scroll to bottom.
- **Evidence:** `50-settings.png` (note "Sign Out" / "Update your account password" row at bottom).
- **Severity:** **P2** — buttons still tappable but the page wobbles sideways.
- **Fix sketch:** `flex-wrap` on the button row, or stack `flex-col sm:flex-row`.

---

### Surfaces inspected and cleared

| Surface | iPhone 12 Pro behaviour | Notes |
|---|---|---|
| `/dashboard` | bodyOverflow 0 | clean — KPI cards stack |
| `/sales` | bodyOverflow 0 | clean — pipeline columns wrap or scroll OK |
| `/staff` | bodyOverflow 0 | clean |
| `/communications` | bodyOverflow 16 | trivial; flag if you want pixel-perfect |
| `/portal/estimates/{token}` (page chrome) | static OK | `max-w-3xl mx-auto` + `flex flex-col md:flex-row` patterns are correct outside the line-items table |
| `/portal/invoices/{token}` (page chrome) | static OK | same |
| `/portal/contracts/{token}` (signature pad) | static OK | canvas resizes via `useEffect` listener; touch-target OK |
| `AppointmentModal` outer container | live OK | `max-sm:w-full max-sm:bottom-0` etc. — modal itself wraps correctly |
| `PaymentCollector` inner form | static OK | `min-h-[48px]` buttons, `grid-cols-1 sm:grid-cols-2` |
| `EstimateCreator` inner form | static OK | filter row uses `flex-wrap`, items grid is `grid-cols-2 md:grid-cols-12` |
| `MapsPickerPopover` | static OK | `absolute left-0 right-0` — width matches parent |
| `ServiceOfferingDrawer` (the drawer side itself) | static OK | `w-full sm:max-w-xl` — only the **table** behind it is broken |
| `Layout` sidebar | static OK | hidden behind `lg:hidden` toggle, hamburger present |
| `/agreements` | runtime SyntaxError | unrelated JS bug, out of scope. `'/src/features/jobs/types/index.ts' does not provide an export named 'SIMPLIFIED_STATUS_MAP'` — file separate ticket |
| `/invoices` (`All` tab) | API 400 error | unrelated backend bug — could not test list-table layout live |

### Touch-target spot-check
Static greps for `min-h-[44px]` / `min-h-[48px]` show that `PaymentCollector`, `EstimateCreator`, `JobSelector`, `NotesPanel` all enforce a 44 px touch target on mobile via `min-h-[44px] md:min-h-0 md:h-7` patterns. Tech-companion primary buttons in `PhotosPanel` use `min-h-[48px]`. **No P0/P1 touch-target violations found** in the surfaces audited.

---

## Fix-file checklist

| # | File | Change |
|---|---|---|
| BUG-1 | `frontend/src/shared/components/SheetContainer.tsx:26` | `w-[560px]` → `w-full sm:w-[560px] max-w-full` |
| BUG-2 | `frontend/src/features/pricelist/components/PriceListEditor.tsx:233` | wrapper `overflow-hidden` → `overflow-x-auto` |
| BUG-3 | `frontend/src/features/jobs/components/JobList.tsx` (table wrapper, search around the `<Table>` mount) | wrap with `overflow-x-auto` div |
| BUG-4 | `frontend/src/features/customers/components/CustomerList.tsx` (table wrapper) | wrap with `overflow-x-auto` div |
| BUG-5 | `frontend/src/features/leads/components/LeadsList.tsx` (heading row + table wrapper) | `flex-wrap` on heading row; `overflow-x-auto` on table; dedupe header with route's PageHeader |
| BUG-6 | `frontend/src/features/schedule/components/SchedulePage.tsx` (resource-timeline view) | default Day view < `sm`, OR wrap timeline in `overflow-x-auto` |
| BUG-7 | `frontend/src/features/jobs/components/SearchableCustomerDropdown.tsx:111-112` | `w-[400px]` → `w-[min(400px,calc(100vw-1rem))]` |
| BUG-8 | `frontend/src/features/portal/components/InvoicePortal.tsx:155` and `frontend/src/features/portal/components/EstimateReview.tsx:220` | wrapper `overflow-hidden` → `overflow-x-auto` |
| BUG-9 | `frontend/src/pages/Marketing.tsx`, `frontend/src/pages/Accounting.tsx` (TabsList) | scroll-wrap the TabsList |
| BUG-10 | `frontend/src/pages/Settings.tsx` (sign-out footer) | `flex-wrap` or `flex-col sm:flex-row` |

### Cross-cutting refactor opportunity
BUG-2/3/4/5/8 are all the same anti-pattern: shadcn `<Table>` rendered inside a rounded `<div>` whose author chose `overflow-hidden` for clipping the rounded corners but then sacrificed the table's natural horizontal-scroll behaviour. Consider one of:

- a `<TableScrollArea>` shared component that does `overflow-x-auto rounded-xl border border-slate-200`, or
- a Tailwind preset/utility class enforcing the pattern across the repo so future tables don't repeat it.

---

## Out of scope (noted, not investigated)
- `/agreements` page throws a JS module SyntaxError before rendering. Separate bug — not a layout issue.
- `/invoices` (default tab) returns HTTP 400 from `/api/v1/invoices`. Separate backend bug — blocked live capture of the InvoiceList table.
- Tech Companion (`features/tech-companion/*`, `pages/tech/*`) — no source files exist yet; the design handoff in `feature-developments/Tech_Companion_Flow.zip` has not been implemented. Nothing to audit.
