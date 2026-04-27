# 04 — Other Pages Audit

A survey of the rest of the admin dashboard. Less depth per file than the Schedule/Modal sections — these are pages technicians visit occasionally, but office staff are the primary users.

**TL;DR:** Most pages are 70–85% usable on mobile already, but every list page has the same two issues (fixed-width tables, fixed-width filter rows). One pattern fix in shared components solves the problem across all of them.

---

## 1. Pages Surveyed

```
Dashboard.tsx                Communications.tsx
Customers.tsx                ContractRenewals.tsx
Leads.tsx                    Marketing.tsx
Jobs.tsx           ←-- 11.9 KB, complex
Sales.tsx          ←-- pipeline view, broken
Invoices.tsx
Agreements.tsx
Accounting.tsx
Settings.tsx       ←-- 18.7 KB, very large
Staff.tsx
WorkRequests.tsx
ScheduleGenerate.tsx (already covered in Schedule deep-dive)
```

---

## 2. Page-by-Page Findings

### Dashboard — ✅ Good
Top-of-app metrics + quick-action cards. Uses `grid-cols-1 md:grid-cols-2 lg:grid-cols-4` pattern correctly. Recharts via `ResponsiveContainer` (good). Minor issue: chart heights are fixed (e.g., `h-80`). Phase 2.

### Customers — ✅ Mostly Good
Uses TanStack Table. The `Table` primitive wraps in `overflow-x-auto`. Toolbar uses `flex-wrap`. Bulk-action bar at line ~459 uses `fixed bottom-6 left-1/2 -translate-x-1/2 z-50` — works on mobile but obscures table content. **Polish item:** make bulk bar full-width pinned to bottom on mobile.

### Leads — ✅ Mostly Good
Similar pattern to Customers. Probably fine. Verify in QA.

### Jobs — ⚠️ Needs Work
`Jobs.tsx` is 11.9 KB, the second-largest non-settings page. Issues:
- 12-column table (`JobList.tsx`)
- Filter toolbar: 7 Select dropdowns in `flex gap-4 items-center flex-wrap` (line 482+). They wrap, but the wrap behavior creates a wall of dropdowns 4 rows deep on iPhone — visually overwhelming.
- Job detail dialog: `max-w-lg` content with deep nested forms.

**Fix direction:**
- Hide non-essential columns at `< md` (`hidden md:table-cell` on `created_at`, `equipment_required`, `notes_summary`, etc.).
- Replace filter dropdown wall with a single "Filters" button on mobile that opens a Sheet (same pattern as FacetRail).
- Keep the detail dialog as-is; verify it scrolls.

### Sales — ❌ Broken
`SalesPipeline` table at `~SalesPipeline.tsx:179-184`:
```tsx
<TableHead className="w-[140px]">Phone</TableHead>
<TableHead className="w-[160px]">Job Type</TableHead>
<TableHead className="w-[120px]">Tags</TableHead>
<TableHead className="w-[140px]">Price</TableHead>
<TableHead className="w-[160px]">Stage</TableHead>
<TableHead className="w-[120px]">Updated</TableHead>
```
Total ~840 px before the customer-name column and the stage-action column. Pipeline visualization (separate component) is a horizontal Kanban — possibly already mobile-aware via `overflow-x-auto` but spot-check needed.

**Fix direction:** Same as JobTable — wrap in `overflow-x-auto`, replace `w-[]` with `min-w-[]`, hide low-priority cols at `< md`. For the Kanban view, acknowledge it's desktop-only and route mobile users to a list view.

### Invoices — ✅ Mostly Good
Tab-based layout (paid/pending/overdue). Tables wrap. Forms in dialogs. Probably fine.

### Agreements / Contract Renewals — ✅ Mostly Good
Card-based layouts. Filter toolbars. Probably fine — spot-check in QA.

### Accounting — ⚠️ Charts squish in landscape
- `SpendingChart h-80` (320 px) — fits in portrait, gets squished in landscape iPhone (812 × 375).
- `BarChart` and `PieChart` via recharts `ResponsiveContainer` — width adapts but height is fixed.

**Fix direction:** `h-64 md:h-80` and ensure pie-chart label collision logic handles narrow widths.

### Marketing — Same as Accounting
Charts. Same fixes apply.

### Communications — ✅ Likely Good
SMS/email logs. Card-based. Probably fine.

### Settings — ⚠️ Long but workable
18.7 KB — a single page with many sections. Uses `grid-cols-1 md:grid-cols-2` for two-column form layouts. Long vertical scroll on mobile. **Functional but tedious.**

**Fix direction (Phase 2 nice-to-have):**
- Split into a tabbed layout — General / Integrations / Team / Billing / Branding.
- Or: collapse sections into Accordions on mobile.
- Either way: reduces vertical scroll by ~80%.

### Staff — ✅ Mostly Good
Probably fine. Spot-check.

### Work Requests — ✅ Mostly Good
Probably fine. Spot-check.

---

## 3. Cross-Cutting Patterns

### Pattern A — Tables with hard-coded `w-[NNNpx]`
**Where:**
- `JobTable.tsx:101-108` (Schedule)
- `SalesPipeline.tsx:179-184`
- `JobList.tsx` (Jobs page)
- `JobPickerPopup.tsx:270+`
- `AppointmentList.tsx:347` (cells)

**Fix recipe (apply uniformly):**
```diff
- <TableHead className="w-[180px]">Job Type</TableHead>
+ <TableHead className="min-w-[140px]">Job Type</TableHead>
```
Plus wrap the `<Table>` in `<div className="overflow-x-auto">` (the Table primitive does this already; verify usage).
Plus add `hidden md:table-cell` on low-priority columns.

### Pattern B — Filter rows with fixed-width `Select`/`Input`
**Where:** AppointmentList, JobList, JobPickerPopup, SalesPipeline filters.

**Fix recipe:**
```diff
- <Select className="w-48">...
+ <Select className="w-full sm:w-48">...

- <Input type="date" className="w-40" />
+ <Input type="date" className="w-full sm:w-40" />
```

For dense filter rows, replace with a Sheet trigger on mobile:
```tsx
{/* Mobile: button opens Sheet with filters */}
<Sheet>
  <SheetTrigger className="md:hidden">Filters</SheetTrigger>
  <SheetContent side="bottom" className="h-[80vh]">
    <Filters />
  </SheetContent>
</Sheet>

{/* Desktop: inline filters */}
<div className="hidden md:flex flex-wrap gap-3">
  <Filters />
</div>
```

### Pattern C — Charts with fixed height
**Where:** SpendingChart, dashboard charts, marketing charts.

**Fix recipe:**
```diff
- <div className="h-80">
+ <div className="h-64 md:h-80">
   <ResponsiveContainer ...>
```

### Pattern D — Multi-column grids skipping `sm:`
**Where:** Most dashboard card grids (`grid-cols-1 md:grid-cols-2 lg:grid-cols-4`).

**Verdict:** Actually fine. The `sm:` breakpoint is at 640 px; mobile phones are typically 320-430 px (below `sm`). Skipping `sm:` means phones get 1 column (correct) and tablets+ get 2-4. Works as designed.

**Where it's actually a problem:** when `sm:grid-cols-1` is missing on layouts that *should* stay 1-column on small tablets. Rare.

---

## 4. Page-by-Page Mobile Readiness Estimate

| Page | iPhone | iPad | Phase |
|---|---|---|---|
| Dashboard | 80% | 95% | 2 |
| Customers | 70% | 90% | 2 |
| Leads | 70% | 85% | 2 |
| Jobs | 50% | 75% | 2 |
| Sales | 40% | 65% | 2 |
| Invoices | 75% | 90% | 2 |
| Agreements | 75% | 85% | 2 |
| Contract Renewals | 75% | 85% | 2 |
| Accounting | 65% | 85% | 2 |
| Marketing | 65% | 85% | 2 |
| Communications | 75% | 85% | 2 |
| Settings | 80% | 90% | 3 (UX revamp) |
| Staff | 80% | 90% | 2 |

---

## 5. Shared Components Used Across Pages

### `FilterPanel.tsx` (`shared/components/FilterPanel.tsx`)
12.8 KB filter panel reused across many pages. Uses `grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4`. **Mostly responsive already.**

Issue: `PopoverContent` for date pickers might overflow viewport edges on mobile. Phase 2 verify.

### `GlobalSearch.tsx`
Hidden on `< lg` already (`hidden lg:flex` in Layout). Mobile users get sidebar nav instead. **No mobile-specific work needed**, but eventually mobile users *should* have a search affordance — consider a search icon in the mobile header.

### `WeekPicker.tsx`
Used in date filtering. ~3.7 KB. Probably fine on mobile (calendar popover from react-day-picker is already mobile-aware). Spot-check.

### Shared UI primitives (shadcn)
Reviewed in detail in `01_CURRENT_RESPONSIVE_STATE.md`:
- Dialog, Sheet, Table, Popover, DropdownMenu, Tabs, Select — all responsive by default.
- The exception is `Table` cells — they have `whitespace-nowrap` (line 71, 84 of `table.tsx`), which combined with `px-6 py-4` makes cells wide. **This is intentional for desktop** but causes horizontal scroll on mobile. Document this as expected behavior.

---

## 6. Maps & Location

### `StaffLocationMap.tsx`
Google Maps via `@react-google-maps/api`. Not deep-reviewed but Google Maps Web is touch-friendly by default. Probably works. Marker clustering via `@googlemaps/markerclusterer` should also work.

**QA item:** verify pinch-zoom and pan work in iOS Safari.

### Address fields on customer/property forms
Use Google Maps autocomplete? Not investigated. QA item.

---

## 7. Forms in Modals — A Recurring Pattern

Many pages have a "Create X" button that opens a dialog with a long form (CustomerForm, JobForm, EstimateBuilder, AppointmentForm).

**Pattern:** the Dialog primitive caps width but not height. Long forms in tall dialogs require scrolling. Most dialogs use `max-h-[85vh] overflow-y-auto` or similar.

**Specific issue:** `EstimateBuilder` line items use a `grid grid-cols-12` layout for line-item rows. **On mobile this is unusable** — 12 columns on 375 px = ~30 px each. This needs to be a stacked card layout on mobile.

---

## 8. Top 5 Quick Wins for Phase 2

1. **Wrap every `<Table>` in `overflow-x-auto`** — search for `<Table` and add the wrapper where missing. Most use the shared primitive which already has it.
2. **Hide low-priority columns at `< md:`** — apply the `hidden md:table-cell` pattern uniformly.
3. **Replace filter rows with Sheet on mobile** — single shared component, opens from a "Filters" button. Saves vertical real estate.
4. **Replace fixed `h-80` chart heights with `h-64 md:h-80`** — global find/replace.
5. **Audit and standardize touch targets** — anywhere `h-8` (32 px) is on a clickable button, bump to `h-11` (44 px).

---

**Next:** `05_RECOMMENDED_APPROACH.md` for the implementation plan.
