# Mobile-viewport bug audit — Grin's Irrigation platform

> **Handoff prompt** — paste this as the first message in a fresh Claude
> session. Self-contained: no prior context required.

You are picking up an investigation that started in a separate session. Goal:
**find every mobile-viewport rendering bug that affects the technician iPhone
flow** in the Grin's Irrigation platform. Analysis only — DO NOT fix anything.

## Project layout

- Repo root: `/Users/kirillrakitin/Grins_irrigation_platform`
- Backend: FastAPI at `http://localhost:8000` (`uv run uvicorn …`, already running)
- Frontend: Vite + React at `http://localhost:5173` (already running)
- Admin login: `admin` / `admin123`
- Tech-mobile route: `/tech` (phone-only landing) plus the standard
  `/schedule`, `/invoices`, customer portal at `/portal/estimates/{token}`
- Test recipient (allowlist + redirect mode): SMS `+19527373312`,
  email `kirillrakitinsecond@gmail.com` — all dev sends are rewritten here
  via `SMS_TEST_REDIRECT_TO` / `EMAIL_TEST_REDIRECT_TO` in `.env`

## Confirmed bug (already found — use as a starting point, not a target)

`frontend/src/shared/components/SheetContainer.tsx:26` hardcodes
`w-[560px]` with no responsive breakpoint and no `max-w-full` clamp.

**Why it clips on iPhone:** the parent `AppointmentModal.tsx:374` is correctly
`max-sm:w-full` (~390 px on iPhone 12 Pro), but the child `SheetContainer`
demands 560 px inside an `overflow-hidden` parent. Excess is clipped instead
of wrapped or scrolled. The same `SheetContainer` is consumed by three
wrappers — every one of them clips on mobile:

- `frontend/src/features/schedule/components/AppointmentModal/EstimateSheetWrapper.tsx`
- `frontend/src/features/schedule/components/AppointmentModal/PaymentSheetWrapper.tsx`
- `frontend/src/features/schedule/components/AppointmentModal/TagEditorSheet.tsx`

**Visual evidence** (PNGs you can `Read` to see the clipping pattern):
`/Users/kirillrakitin/Grins_irrigation_platform/e2e-screenshots/appointment-modal-umbrella-tech-mobile-2026-05-02/phase-3/`
  - `04-send-estimate-clicked.png` — "Send Estima" cut mid-CTA
  - `05-pricelist-picker-open.png` — offering rows clipped
  - `06-search-spring.png` — search results clipped
  - `07-spring-startup-picked.png` — "Ad" instead of "Add"
  - `12-tree-detail.png` — line-item columns clipped

The desktop responsive shots (`responsive/*-desktop.png`) hide the bug because
modal width = sheet width at sm+ breakpoints. Bug only manifests below ~600 px
viewport — exactly the tech/mobile audience.

## Your assignment

Find **every other** mobile-viewport bug in the technician-facing surface.
The goal is a complete audit so we can fix them in one pass. Do not stop at
the first hit.

### Scope — investigate at minimum:

1. All three sheet wrappers (EstimateSheetWrapper, PaymentSheetWrapper,
   TagEditorSheet) — inspect the inner forms (`PaymentCollector.tsx`,
   `EstimateCreator.tsx`, etc.) for any hardcoded widths or `min-w-[Npx]`
   that exceed an iPhone viewport.
2. Every shadcn `Dialog` / `Drawer` / `Sheet` / `Popover` / `Command` mount in
   the appointment modal flow (`grep -rn "DialogContent\|SheetContent\|PopoverContent\|CommandDialog"
   frontend/src/features/schedule frontend/src/features/customers
   frontend/src/features/leads`).
3. The customer portal estimate review at `/portal/estimates/{token}` —
   `frontend/src/pages/portal/EstimateReview.tsx` and friends.
4. The Tech Companion landing — `frontend/src/pages/tech/*` and any
   `features/tech-companion/*` slice.
5. `MapsPickerPopover.tsx`, line-item picker (`LineItemPicker.tsx`), size/yard/variant
   sub-pickers — popover width assumptions on small screens.
6. Action track / Action card sublabels for truncation under 390 px.
7. `frontend/src/pages/Invoices.tsx` and the `frontend/src/features/pricelist/*`
   editor — does the table scroll horizontally cleanly, or does it spill?
8. Any list/table that uses `min-w-[Npx]` columns with no horizontal scroll wrapper.

### How to investigate — combine three signals:

a) **Static analysis** in `frontend/src/`. Useful greps:
   - `rg "w-\[\d{3,}(?:px|rem)\]" frontend/src` — fixed widths ≥100 px
   - `rg "min-w-\[\d{3,}px\]" frontend/src` — fixed min-widths
   - `rg "max-w-(?!full|none|screen)\w+" frontend/src` — bounded max-w with no full-width fallback
   - `rg "overflow-hidden" frontend/src/features/schedule frontend/src/shared/components` — combined with fixed-width children, this is the clipping pattern
   - `rg "min-h-\[\d{2,}px\]" frontend/src` — touch-target audit (must be ≥44 px per Apple HIG)

b) **Live capture with `agent-browser`.** A daemon is already configured.
   Use viewport `390 844` (iPhone 12 Pro — what real techs use). Save your
   screenshots to a NEW folder so you don't overwrite anyone else's work:
   `/Users/kirillrakitin/Grins_irrigation_platform/e2e-screenshots/mobile-bug-audit-{today}/`.

   Reference helper script: `e2e/_lib.sh` (sources login + ab wrapper).
   Example session prelude:
   ```bash
   source e2e/_lib.sh
   require_tooling
   require_servers
   agent-browser --session mobile-audit set viewport 390 844
   login_admin   # uses umbrella-e2e session by default — pass SESSION=mobile-audit
   ```

   Open each candidate page, screenshot, and compare to its desktop sibling.

c) **DOM-level overflow probe.** When a screenshot looks suspicious, run:
   ```js
   document.body.scrollWidth - document.body.clientWidth
   ```
   via `agent-browser eval`. A non-zero value = the page itself overflows
   the viewport. Then:
   ```js
   Array.from(document.querySelectorAll('*'))
     .filter(el => el.scrollWidth > el.clientWidth + 1
                || el.getBoundingClientRect().right > window.innerWidth)
     .map(el => ({tag: el.tagName, cls: el.className.toString().slice(0,80)}))
   ```
   to enumerate the overflowing nodes by class. This pinpoints the
   container without guessing.

### Tooling reference — use this if your `ab click` retries flake

The canonical `ab click` wrapper in `e2e/_lib.sh` retries 3× on agent-browser
daemon EAGAIN errors, then falls back to `document.querySelector(...).click()`
via eval. This works for most clicks but **breaks down on shadcn/Radix
`Select` triggers** when the daemon has been live for a while — each retry
costs ~30 s and the variant-drawer loop in Phase 2 stalled for ~16 minutes
before being killed in an earlier session.

A working pattern lives in `e2e/phase-2-pricelist-editor-fast.sh`. It bypasses
the retry loop by going through direct `agent-browser eval` calls for every
dropdown interaction:

```bash
# Open a Radix Select trigger
agent-browser --session "$SESSION" eval \
  "document.querySelector('[data-testid=offering-pricing-model-trigger]')?.click()"
sleep 1
# Pick the option whose data-value or visible text matches
agent-browser --session "$SESSION" eval \
  "Array.from(document.querySelectorAll('[role=option]')).find(e => e.getAttribute('data-value')==='flat' || e.textContent.includes('flat'))?.click()"
sleep 1
agent-browser --session "$SESSION" press Escape  # close any leftover dropdown
```

Each variant drawer captures in ~2 s instead of stalling. Use this pattern
when capturing iPhone-viewport screenshots of any Radix Select / Combobox /
Dropdown — the PaymentCollector method picker, the LineItemPicker
customer-type filter, the size/yard/variant sub-pickers in EstimateCreator,
and the pricelist filter dropdowns all use Radix Select under the hood.

If the daemon still flakes, kill it and start fresh: `pkill -f "agent-browser-darwin-arm64" ; pkill -f "node.*agent-browser.*daemon"`.

### Out of scope

- Don't fix anything. Don't write migrations. Don't edit React components.
- Don't touch backend code. The bug is purely frontend layout.
- Don't re-run the umbrella E2E suite — the existing rerun-2 sign-off is
  already complete (`e2e-screenshots/appointment-modal-umbrella-rerun-2-2026-05-02/`).

### Deliverable

Write a Markdown report to
`/Users/kirillrakitin/Grins_irrigation_platform/bughunt/{today}-mobile-viewport-audit.md`.
For each bug found, include:

1. **Symptom** — what the user sees (clipping, overflow, unreadable text,
   tiny touch target, etc.)
2. **Root cause** — file:line of the offending CSS/Tailwind class. Cite the
   exact class string.
3. **Affected viewports** — confirm with explicit width measurements (e.g.
   "manifests below 600 px; iPhone 12 Pro 390×844 shows X px of right-edge
   clipping").
4. **Reproduction** — minimum click path from `/` to the broken state.
5. **Evidence** — relative path to a screenshot you captured, plus DOM-probe
   output if you ran step (c).
6. **Severity** — `P0` (blocks tech from completing job), `P1` (degraded but
   workable), `P2` (cosmetic).
7. **Suggested fix sketch** — one line on what would resolve it (so the
   eventual fix author has a starting point). Do not write the fix.

Open the report with a one-paragraph executive summary listing the top-3
P0 bugs. End with a checklist mapping each bug to a candidate fix file.

Aim for thoroughness over speed — assume you have an hour and the user
wants every bug enumerated, not just the obvious ones.
