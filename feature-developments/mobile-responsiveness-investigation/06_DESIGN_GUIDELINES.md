# 06 — Design Guidelines

Patterns to apply when fixing mobile responsiveness in this codebase. Reference this document during implementation. Patterns include `before` / `after` snippets so the team can apply them mechanically.

---

## 1. Breakpoint Mental Model

Tailwind v4 default breakpoints, mapped to real devices:

| Breakpoint | Min width | Real devices |
|---|---|---|
| (default) | 0 | iPhone SE 1st gen (320 px), iPhone 13 mini (375 px), iPhone 14 (390 px), iPhone 14 Pro Max (430 px) |
| `sm:` | 640 px | iPad mini portrait (744 × 1133), iPhone landscape (~750–932) |
| `md:` | 768 px | iPad portrait (820 × 1180), Surface Go portrait |
| `lg:` | 1024 px | iPad landscape, MacBook 13" small windows |
| `xl:` | 1280 px | MacBook 13"–14" full-screen |
| `2xl:` | 1536 px | MacBook 16", external displays |

**Mental model:**
- **Default styles = phone portrait.** Mobile-first.
- **`sm:` and up = tablet portrait or phone landscape.**
- **`md:` and up = tablet+, treat as desktop-ish.**
- **`lg:` and up = real desktop.**

---

## 2. The Five Core Patterns

### Pattern 1 — Action bars wrap, then collapse to overflow menu

#### Before (broken on mobile):
```tsx
<div className="flex items-center gap-4">
  <Button>Action 1</Button>
  <Button>Action 2</Button>
  <Button>Action 3</Button>
  <Button>Action 4</Button>
  <Button>Primary Action</Button>
</div>
```

#### After:
```tsx
<div className="flex items-center gap-2 flex-wrap">
  {/* Primary: always visible */}
  <Button className="order-last md:order-none">Primary Action</Button>

  {/* Secondary: hidden on mobile, shown md:+ */}
  <Button className="hidden md:inline-flex">Action 1</Button>
  <Button className="hidden md:inline-flex">Action 2</Button>
  <Button className="hidden md:inline-flex">Action 3</Button>
  <Button className="hidden md:inline-flex">Action 4</Button>

  {/* Mobile: overflow menu */}
  <DropdownMenu>
    <DropdownMenuTrigger className="md:hidden">
      <Button variant="ghost" size="icon"><MoreHorizontal /></Button>
    </DropdownMenuTrigger>
    <DropdownMenuContent align="end">
      <DropdownMenuItem onClick={...}>Action 1</DropdownMenuItem>
      <DropdownMenuItem onClick={...}>Action 2</DropdownMenuItem>
      <DropdownMenuItem onClick={...}>Action 3</DropdownMenuItem>
      <DropdownMenuItem onClick={...}>Action 4</DropdownMenuItem>
    </DropdownMenuContent>
  </DropdownMenu>
</div>
```

**Apply to:** `SchedulePage.tsx:331-395`.

---

### Pattern 2 — Tables with `min-w` instead of `w`

#### Before:
```tsx
<TableHead className="w-[180px]">Customer</TableHead>
<TableHead className="w-[160px]">Job Type</TableHead>
<TableHead className="w-[120px]">City</TableHead>
```

#### After:
```tsx
<TableHead className="min-w-[140px]">Customer</TableHead>
<TableHead className="min-w-[120px] hidden sm:table-cell">Job Type</TableHead>
<TableHead className="min-w-[100px] hidden md:table-cell">City</TableHead>
```

**Rules:**
- `w-[NNNpx]` → `min-w-[NNNpx]` (rare exceptions: stable column widths in pinned headers).
- Hide the *least informative* column at each breakpoint:
  - `< sm`: only customer + status visible.
  - `sm-md`: add job type or amount.
  - `md+`: add metadata columns.
  - `lg+`: full table.
- Always wrap `<table>` in `overflow-x-auto`. The shared `Table` primitive at `frontend/src/components/ui/table.tsx:8` already does this — verify usage.

**Apply to:** JobTable, JobPickerPopup, SalesPipeline, JobList, AppointmentList.

---

### Pattern 3 — Filter rows: stack on mobile, sheet on small viewports

#### Before:
```tsx
<div className="flex gap-4">
  <Select className="w-48">...</Select>
  <Input className="w-40" />
  <Input className="w-40" />
</div>
```

#### After (Option A — simple stack):
```tsx
<div className="flex flex-col sm:flex-row sm:flex-wrap gap-3">
  <Select className="w-full sm:w-48">...</Select>
  <Input className="w-full sm:w-40" />
  <Input className="w-full sm:w-40" />
</div>
```

#### After (Option B — Sheet on mobile, inline on desktop):
```tsx
{/* Mobile: button opens sheet */}
<Sheet>
  <SheetTrigger asChild className="md:hidden">
    <Button variant="outline">
      <Filter className="h-4 w-4 mr-2" />
      Filters {activeCount > 0 && `(${activeCount})`}
    </Button>
  </SheetTrigger>
  <SheetContent side="bottom" className="h-[85vh]">
    <SheetHeader>
      <SheetTitle>Filters</SheetTitle>
    </SheetHeader>
    <div className="flex flex-col gap-4 mt-4">
      <FiltersForm />
    </div>
  </SheetContent>
</Sheet>

{/* Desktop: inline */}
<div className="hidden md:flex md:flex-wrap md:gap-3">
  <FiltersForm />
</div>
```

**Apply to:** AppointmentList, JobList, SalesPipeline, FilterPanel usages on dense pages.

---

### Pattern 4 — Modals: full-screen sheet on mobile, dialog on desktop

This is *exactly* what the existing `AppointmentModal v2` does:

```tsx
className={[
  'fixed z-50 ... overflow-hidden flex flex-col',

  // Desktop: centered dialog
  'sm:rounded-[18px] sm:w-[560px] sm:max-h-[90vh]',
  'sm:top-1/2 sm:left-1/2 sm:-translate-x-1/2 sm:-translate-y-1/2',

  // Mobile: bottom sheet
  'max-sm:rounded-t-[20px] max-sm:rounded-b-none',
  'max-sm:w-full max-sm:bottom-0 max-sm:left-0 max-sm:right-0 max-sm:max-h-[92vh]',
].join(' ')}
```

Plus a grab handle:
```tsx
<div className="sm:hidden flex justify-center pt-3 pb-1 flex-shrink-0">
  <div className="w-11 h-[5px] rounded-full bg-[#D1D5DB]" />
</div>
```

**Use this template** for any new dialog where the content is dense / form-heavy / technician-touched. Light-weight confirmation dialogs (using shadcn `Dialog` directly) can keep the centered layout — the Dialog primitive already has the `max-w-[calc(100%-2rem)]` floor that handles small screens.

---

### Pattern 5 — Charts with adaptive height

#### Before:
```tsx
<div className="h-80">
  <ResponsiveContainer ...>
    <BarChart ... />
  </ResponsiveContainer>
</div>
```

#### After:
```tsx
<div className="h-64 md:h-80">
  <ResponsiveContainer ...>
    <BarChart ... />
  </ResponsiveContainer>
</div>
```

For pie charts that lose label legibility on narrow widths:
```tsx
<PieChart>
  <Pie
    ...
    label={isMobile ? false : ({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
  />
  {isMobile && <Legend />}
</PieChart>
```

---

## 3. FullCalendar Mobile Configuration

```tsx
import { useMediaQuery } from '@/shared/hooks/useMediaQuery';

const isMobile = useMediaQuery('(max-width: 768px)');

<FullCalendar
  initialView={isMobile ? 'listWeek' : 'timeGridWeek'}
  headerToolbar={
    isMobile
      ? { left: 'prev,next', center: 'title', right: 'today' }
      : { left: 'prev,next today', center: 'title', right: 'dayGridMonth,timeGridWeek,timeGridDay' }
  }

  // Disable drag-drop on touch
  editable={!isMobile}
  selectable={!isMobile}

  // List view config
  views={{
    listWeek: {
      buttonText: 'List',
      noEventsContent: 'No appointments this week',
      listDayFormat: { weekday: 'long', month: 'short', day: 'numeric' },
    },
  }}

  // Touch tolerance
  longPressDelay={isMobile ? 1500 : 1000}

  // (existing config below)
  events={events}
  ...
/>
```

Plus update the CSS to reduce day-cell heights on mobile:
```css
/* CalendarView.css */
.fc .fc-daygrid-day {
  @apply min-h-[60px] sm:min-h-[120px] border-r border-b border-slate-50 p-2;
}

.fc .fc-toolbar-title {
  @apply text-base sm:text-lg font-bold text-slate-800;
}
```

---

## 4. Touch Targets — Apple HIG / Material 3

Every interactive element should be ≥ 44 × 44 px (Apple) / ≥ 48 × 48 px (Material). Tailwind cheat sheet:

| Tailwind | px | Use |
|---|---|---|
| `h-8 w-8` | 32 px | ❌ Too small |
| `h-9 w-9` | 36 px | ❌ Too small |
| `h-10 w-10` | 40 px | ⚠️ Below HIG, accept only for non-critical icons |
| `h-11 w-11` | 44 px | ✅ HIG floor |
| `h-12 w-12` | 48 px | ✅ Material |

For buttons with text:
```tsx
<Button className="min-h-[44px] px-4">Action</Button>
```

For icon-only buttons:
```tsx
<Button variant="ghost" size="icon" className="h-11 w-11">
  <Icon />
</Button>
```

---

## 5. Common Anti-Patterns to Stop Doing

### ❌ `whitespace-nowrap` on long text content
Forces horizontal scroll. Use `truncate` (single-line ellipsis) or `break-words` (wrap) instead. Exception: table headers (already in shared primitive).

### ❌ Fixed pixel widths inside flex children
```tsx
{/* bad */}
<div className="flex gap-2">
  <Card className="w-[200px]">...</Card>
  <Card className="w-[200px]">...</Card>
</div>

{/* good */}
<div className="flex gap-2 flex-wrap">
  <Card className="flex-1 min-w-[200px]">...</Card>
  <Card className="flex-1 min-w-[200px]">...</Card>
</div>
```

### ❌ `100vh` for full-screen modals
Use `100dvh` (dynamic viewport height) for modern Safari. Or use `max-h-[90vh]` and let the modal scroll internally.

### ❌ `display: none` for mobile content (vs. `hidden`)
Tailwind's `hidden` class = `display: none`. Don't use `hidden md:block` to *toggle* per-device — instead, render different components conditionally with `useMediaQuery`. Reason: hidden DOM still mounts → still runs queries, still renders → wasted work.

### ❌ Inline styles for components that need responsive variants
```tsx
{/* bad — can't apply Tailwind breakpoints */}
<div style={{ width: 180, padding: 10 }}>...</div>

{/* good */}
<div className="w-[180px] sm:w-[140px] p-2.5">...</div>
```

The PhotosPanel and NotesPanel currently violate this. Migrate during Phase 1.

### ❌ `position: absolute inset-0` for overlay sheets on mobile
The mobile bottom-sheet is `position: fixed`; nested `absolute inset-0` doesn't fill the viewport. Use Radix `Sheet` or Radix `Dialog` for proper portal-based stacking.

---

## 6. Hooks & Utilities to Add

If not already present, add these to `frontend/src/shared/hooks/`:

### `useMediaQuery.ts`
```tsx
import { useState, useEffect } from 'react';

export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(() => {
    if (typeof window === 'undefined') return false;
    return window.matchMedia(query).matches;
  });

  useEffect(() => {
    const mql = window.matchMedia(query);
    const handler = (e: MediaQueryListEvent) => setMatches(e.matches);
    mql.addEventListener('change', handler);
    return () => mql.removeEventListener('change', handler);
  }, [query]);

  return matches;
}
```

### Common breakpoint constants (optional, for ergonomics):
```tsx
export const BREAKPOINTS = {
  MOBILE: '(max-width: 767px)',           // < md
  TABLET: '(min-width: 768px) and (max-width: 1023px)',  // md-lg
  DESKTOP: '(min-width: 1024px)',          // lg+
} as const;
```

Use:
```tsx
const isMobile = useMediaQuery(BREAKPOINTS.MOBILE);
```

---

## 7. Testing Recipe

### Dev tools shortcuts (macOS Chrome / Safari)
- Cmd-Opt-I → DevTools → Toggle Device Toolbar (Cmd-Shift-M)
- Test viewport widths: 320, 375, 390, 414, 430 (phones), 744, 820 (tablets portrait), 1024 (tablet landscape / small desktop), 1280, 1440 (desktops).

### Real devices (recommended for Phase 1 sign-off)
- iPhone SE (320 px viewport in landscape, 375 in portrait) — covers smallest case.
- iPhone 13/14 (390 px) — most common modern iPhone.
- iPhone 14 Pro Max (430 px) — biggest phone.
- iPad mini (744 × 1133) or iPad Air (820 × 1180) portrait.
- iPad Air landscape (~1180 × 820).

### Browserstack
If real-device access is limited. Subscribe to a single seat.

### Specific tests for the technician workflow
1. Open `/schedule` on iPhone, see today's appointments.
2. Tap an appointment, see the modal slide up from bottom.
3. Tap "En route" — should advance status, modal stays open.
4. Tap "Take photo" — should open camera (with `capture="environment"`).
5. Tap "See attached notes" — should expand inline.
6. Edit notes, tap Save.
7. Tap "Collect Payment" → Stripe Terminal flow renders inside modal.
8. Tap close → modal dismisses to bottom.
9. Pull down on the schedule to refresh (if implemented).
10. Rotate to landscape — verify the modal still works.

---

## 8. Quick Reference Cheat Sheet

```
GRID:        grid-cols-1 sm:grid-cols-2 lg:grid-cols-4
FLEX ROW:    flex flex-col sm:flex-row gap-3
TABLE:       overflow-x-auto + min-w- not w- + hidden md:table-cell
DIALOG:      shadcn Dialog primitive (already has mobile floor)
SHEET:       Sheet side="bottom" h-[85vh] for mobile filters
TOUCH:       h-11 w-11 for icon buttons, min-h-[44px] for text buttons
HEIGHT:      h-64 md:h-80 for charts; max-h-[90vh] for tall modals
WIDTH:       w-full sm:w-48 for filters; min-w-[140px] for table cols
INLINE:      replace with className for any component that has > 1 viewport
```

---

**Next:** `07_FILE_INVENTORY.md` for the exhaustive list of every change needed, grouped by severity and file.
