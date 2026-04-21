# SPEC — Pipeline List

**Route:** `/sales` (replaces current `SalesPipeline.tsx` render)
**File to replace:** `frontend/src/features/sales/components/SalesPipeline.tsx`
**Visual ground truth:** `reference/Sales-Reference.html` → tab "② Pipeline list" · screenshot `02-pipeline-list.png`

---

## 1. Intent

The current list has no health signal — every row looks the same. The only hint of trouble is the "Needs Follow-Up" count at the top. This redesign adds **age-in-stage chips** next to the status pill so stuck entries surface inline, with per-stage thresholds. The same threshold logic drives the summary box count.

**One-line principle:** *age is a derived property on every row, visible always, tuned per stage.*

---

## 2. Layout

```
┌────────────────────────────────────────────────────────────────────────┐
│  breadcrumb: Sales / Pipeline                                          │
│                                                                        │
│  ┌──────────┬──────────┬─────────────┬──────────────┐                  │
│  │ Needs    │ Pending  │ Needs       │ Revenue      │   4 summary      │
│  │ Estimate │ Approval │ Follow-Up   │ Pipeline     │   cards          │
│  │    7     │    4     │    3 ▲2     │  $42,700     │                  │
│  └──────────┴──────────┴─────────────┴──────────────┘                  │
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ Customer │ Phone │ Job Type │ Status       │ Last Contact │ Act │  │
│  ├──────────────────────────────────────────────────────────────────┤  │
│  │ Viktor P │ ...   │ Sprink   │ [Pending]⚡12d│ 2d ago       │ [N] │  │
│  │ Marcella │ ...   │ Spring   │ [Sched]⚡5d  │ 5d ago       │ [S] │  │
│  │ Andrew K │ ...   │ Upgrade  │ [Send]●1d   │ just now     │ [S] │  │
│  │ ...                                                                │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│  pagination                                                            │
└────────────────────────────────────────────────────────────────────────┘
```

Keep the 2-col left-sidebar app shell that exists today. Do **not** rebuild the shell.

---

## 3. Summary cards (top row)

Keep the 4 cards that already exist in `SalesPipeline.tsx`. Two changes:

| Card | Count source (new) | Click behaviour |
|---|---|---|
| **Needs Estimate** | `summary.schedule_estimate` (unchanged) | Toggle `statusFilter = 'schedule_estimate'` |
| **Pending Approval** | `summary.pending_approval` (unchanged) | Toggle `statusFilter = 'pending_approval'` |
| **Needs Follow-Up** | **`COUNT(rows WHERE age.bucket === 'stuck')`** — computed client-side over all rows, NOT just the current page. See §6. | Toggle a synthetic filter `ageBucket = 'stuck'` (client-side filter, no API param) |
| **Revenue Pipeline** | `metrics.total_pipeline_revenue` (unchanged) | No click (cursor-default). |

The **Needs Follow-Up** card additionally shows a delta below the count:
- Text: `▲ N since last week` in amber, or `▼ N since last week` in green, or `— same as last week` in slate.
- Source: persist last week's count in `localStorage.setItem('sales_followup_prev_count', value)` with a weekly reset keyed on ISO week. Fine to leave empty on first render.
- Card gets `bg-amber-50` background to stand out.

### Active filter banner

Keep the existing `statusFilter` banner. Extend it to render a second chip when `ageBucket === 'stuck'` is active: `⚡ Stuck entries only` with a clear button. Chips stack horizontally.

---

## 4. Table columns

| # | Header | Width hint | Cell content |
|---|---|---|---|
| 1 | CUSTOMER | `min-w-[180px]` | **bold** `customer_name`, or italic `Unknown` |
| 2 | PHONE | `w-[140px]` | `<Phone>` icon + `customer_phone`, or italic `N/A` |
| 3 | JOB TYPE | `w-[160px]` | `job_type`, or italic `N/A` |
| 4 | STATUS | `min-w-[260px]` | Status pill **+ age chip** (see §5) **+ override ⚠ icon** if `override_flag` |
| 5 | LAST CONTACT | `w-[140px]` | `formatDistanceToNow(last_contact_date)`, or italic `Never` |
| 6 | ACTIONS | `w-[120px]` | Compact primary button (see §7) + ghost `✕` dismiss |

**Dropped columns vs. current code:** `Address`. The current table shows `property_address`; the redesign drops it to make room for the wider Status column. Move address into the hover tooltip on `customer_name` (use a shadcn `<Tooltip>`).

**Row hover:** `bg-slate-50/80`. **Row click:** navigate to `/sales/:id` (unchanged).

---

## 5. Age chip — the main new thing

Rendered immediately to the right of the status pill, inside the same `<td>`, same line.

### Visual

```
[Pending Approval]  ⚡ STUCK 12d     ← red, bordered
[Schedule Estimate] ⚡ STALE 5d      ← amber, bordered
[Send Estimate]     ● FRESH 1d       ← green, bordered
```

- Pill shape: `rounded-full`, `1.5px` border, `px-2 py-0.5`, `text-[11px]`, `font-semibold`, `uppercase`, `tracking-[0.04em]`.
- Leading glyph: `●` for fresh, `⚡` for stale & stuck (unicode, not an icon font).
- Number format: `{n}d` (days). `< 1d` is still rendered as `1d` — rows younger than a day are shown as fresh regardless.

### Colour map (Tailwind classes)

| Bucket | Text | Bg | Border |
|---|---|---|---|
| `fresh` | `text-emerald-700` | `bg-emerald-50` | `border-emerald-500` |
| `stale` | `text-amber-700`   | `bg-amber-50`   | `border-amber-500`   |
| `stuck` | `text-red-700`     | `bg-red-50`     | `border-red-500`     |

### Threshold rules (source of truth: `data-shapes.ts` → `AGE_THRESHOLDS`)

| Stage | fresh | stale | stuck |
|---|---|---|---|
| `schedule_estimate` | ≤ 3d | 4–7d | > 7d |
| `estimate_scheduled` | (same as `schedule_estimate`) | | |
| `send_estimate` | ≤ 3d | 4–7d | > 7d |
| `pending_approval` | ≤ 4d | 5–10d | > 10d |
| `send_contract` | ≤ 3d | 4–7d | > 7d |
| `closed_won` / `closed_lost` | — chip not rendered — | | |

### Computing "age"

Age = days since the entry **entered the current stage** — **not** days since `updated_at` (any edit would reset it) and **not** days since `last_contact_date` (a phone call shouldn't reset age).

**v1 implementation (no backend change):**
1. If a stage-transition event exists in a notes/activity log, use that timestamp.
2. Otherwise fall back to `updated_at`.
3. Wrap in a hook `useStageAge(entry)` so we can swap the source later.

```ts
function daysSince(iso: string): number {
  return Math.floor((Date.now() - new Date(iso).getTime()) / 86_400_000);
}
```

Document this fallback in a code comment — Claude Code should leave a `TODO(backend)` noting that the proper source is a `stage_entered_at` column.

---

## 6. "Needs Follow-Up" count

Counted as:
```ts
rows.filter(r => useStageAge(r).bucket === 'stuck').length
```

Because the current API paginates at 50, this count is **correct for the current page only** in v1. Acceptable — document in the card tooltip: *"Based on loaded page. Increase page size or add server-side count later."* Add a `TODO(backend)` for a proper aggregate endpoint.

Do **not** use the existing `metrics.needs_followup_count` — that field currently maps to `summary.send_estimate` which is wrong.

---

## 7. Action button (column 6)

Replaces the current `StatusActionButton` *visually* only — the same mutation wiring stays. Compact size, no leading icon, label per stage:

| Stage | Label |
|---|---|
| `schedule_estimate` | **Schedule** |
| `estimate_scheduled` | **Send** |
| `send_estimate` | **Send** |
| `pending_approval` | **Nudge** |
| `send_contract` | **Convert** |
| `closed_won` | `View job` (ghost, not primary) |
| `closed_lost` | *(no button)* |

Click → triggers the same default action as the current `StatusActionButton` transition.
A secondary `✕` ghost button dismisses the row (only visual — wires to nothing in v1; `TODO` comment).

---

## 8. Data hooks

```ts
// Unchanged:
useSalesPipeline({ skip, limit, status })
useSalesMetrics()

// New, all client-side:
useStageAge(entry: SalesEntry): StageAge
useFollowupCount(rows: SalesEntry[]): number    // memoised
useFollowupDelta(currentCount: number): { dir: 'up'|'down'|'flat'; n: number } | null
```

---

## 9. Test IDs (required)

Every new interactive element gets a `data-testid`:

| Element | testid |
|---|---|
| Root | `pipeline-list-page` |
| Summary card · Needs Estimate | `pipeline-summary-needs-estimate` (unchanged) |
| Summary card · Pending Approval | `pipeline-summary-pending-approval` |
| Summary card · Needs Follow-Up | `pipeline-summary-needs-followup` |
| Summary card · Revenue | `pipeline-summary-revenue` |
| Delta label | `pipeline-summary-followup-delta` |
| Age-bucket filter chip (active) | `pipeline-filter-age-stuck` |
| Row | `pipeline-row-{id}` |
| Age chip on row | `pipeline-row-age-{id}` (value = `fresh|stale|stuck`) |
| Row primary action | `pipeline-row-action-{id}` |
| Row dismiss | `pipeline-row-dismiss-{id}` |

---

## 10. Empty & loading states

- Loading: existing `<LoadingPage />`, no change.
- Error: existing `<ErrorMessage />`, no change.
- Empty (no rows): existing `<Inbox>` illustration, no change.

---

## 11. Accessibility

- Age chip has `aria-label="{bucket} — {n} days in {stage}"`.
- Row is a native `<tr>` with `role="row"` (Radix Table handles this).
- Keyboard: `Enter` on a focused row navigates to detail (Radix Table default).
- Respect `prefers-reduced-motion` — disable the row hover transition.

---

## 12. Done when

- [ ] All 7 rows in the reference HTML render identically (minus fonts — app uses `Inter`, reference uses `Kalam`).
- [ ] Clicking **Needs Follow-Up** filters to rows where `age.bucket === 'stuck'`.
- [ ] Changing `statusFilter` preserves `ageBucket` filter and vice versa.
- [ ] Every row shows a coloured age chip of the correct bucket.
- [ ] `pending_approval` rows use the 4/10 thresholds, not 3/7.
- [ ] Address column is gone; hovering customer name shows address in a tooltip.
- [ ] `data-testid` on every element listed in §9.
- [ ] No TypeScript errors; existing `useSalesPipeline` unchanged.
