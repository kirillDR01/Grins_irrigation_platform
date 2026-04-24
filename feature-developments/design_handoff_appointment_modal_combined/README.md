# Handoff · Appointment Modal (Combined)

_Grin's Irrigation — scheduling tab · appointment detail modal with combined Payment + Estimate actions, editable Customer Tags, and a Maps-app picker._

---

## 1. Overview

This package specifies the **combined appointment modal** that opens when staff (admin or technician) tap an appointment in the scheduling calendar. One modal handles the entire on-site workflow:

- Status + timeline of the visit (Booked → En route → On site → Done)
- Big three-stage action track (`On my way` / `Job started` / `Job complete`)
- Secondary actions: Add photo, Notes, Review, **Edit tags** _(new)_
- **Collect payment** button (teal outline) → opens full payment sheet flow
- **Send estimate** button (violet outline) → opens full estimate sheet flow
- Customer hero (avatar, history, **tags row** _(new)_, phone, email)
- Property block with **Get directions** → Apple Maps / Google Maps picker _(new)_
- Scope + materials list
- Assigned tech + reassignment
- Footer: Edit, No show, Cancel

### What's different vs. the two predecessor prototypes

| | Redesign | With Estimates | **Combined (this file)** |
|---|---|---|---|
| Collect payment | ✓ | ✓ | ✓ |
| Send estimate | — | ✓ | ✓ |
| AI draft button | ✓ (violet) | ✓ (violet) | **✗ removed** |
| Edit tags button | — | — | **✓ added** (next to Review) |
| Tags row in customer block | — | — | **✓ added** |
| Get directions behavior | opens default map | opens default map | **✓ Apple / Google picker** |

Tags written here are **customer-scoped**, not appointment-scoped — they appear on the customer profile and auto-apply to every past and future job.

---

## 2. About the design files

The files in `source/` are **design references written in HTML + inline JSX via in-browser Babel**. They are prototypes that demonstrate intended look and behavior — they are **not** production code to ship as-is.

Your task is to **recreate these designs inside the Grin's Irrigation app's existing codebase** using whatever its production framework, component library, and styling system are (React + Tailwind, Vue, Svelte, SwiftUI, etc.). Match the design tokens (colors, type, spacing, radii) exactly; match the component structure closely enough that the UI is pixel-faithful. Use existing primitives where available — don't re-invent buttons, sheets, or chips if the codebase already has them.

If no production environment exists yet, React + Tailwind CSS is a safe default — the JSX in `source/` is already React-flavored.

---

## 3. Fidelity

**High-fidelity.** Colors, typography, spacing, border-radii, shadows, and interaction patterns are final. Copy measurements and hex values exactly. Behavior descriptions in §8 are authoritative.

---

## 4. Design tokens

### 4.1 Color palette (raw hex)

Apply these as CSS variables / design tokens.

| Token | Hex | Use |
|---|---|---|
| `ink` | `#0B1220` | Primary text, filled dark buttons |
| `ink-2` | `#1F2937` | Secondary text, body copy |
| `ink-3` | `#4B5563` | Tertiary text, metadata |
| `ink-4` | `#6B7280` | Quiet labels (uppercase caps) |
| `line` | `#E5E7EB` | Primary borders, dividers |
| `line-2` | `#F3F4F6` | Neutral pill backgrounds |
| `surface` | `#FFFFFF` | Modal body, cards |
| `soft` | `#F9FAFB` | Section fills, footer bar |
| `blue` | `#1D4ED8` | Phone/Call chip, directions CTA, "on the way" stage |
| `blue-bg` | `#DBEAFE` | Blue chip/pill background |
| `orange` | `#C2410C` | On-site stage badge, arrival action |
| `orange-bg` | `#FFEDD5` | Orange chip background |
| `green` | `#047857` | Complete stage, success, "Repeat customer" tag |
| `green-bg` | `#D1FAE5` | Green chip background |
| `teal` | `#0F766E` | **Collect payment** outline, avatar accent |
| `teal-bg` | `#CCFBF1` | Customer hero tinted header |
| `red` | `#B91C1C` | Destructive ("Cancel", "Decline") |
| `red-bg` | `#FEE2E2` | Destructive chip background |
| `amber` | `#B45309` | "Normal priority" pill, "Back gate" tag |
| `amber-bg` | `#FEF3C7` | Amber chip background |
| `violet` | `#6D28D9` | **Send estimate** outline, new customer tag accent |
| `violet-bg` | `#EDE9FE` | Violet chip background, active state for Edit tags button |
| `tag-chip-border-blue` | `#93C5FD` | Tag chip outline (blue tone) |
| `tag-chip-border-green` | `#86EFAC` | Tag chip outline (green tone) |
| `tag-chip-border-amber` | `#FCD34D` | Tag chip outline (amber tone) |
| `tag-chip-border-violet` | `#C4B5FD` | Tag chip outline (violet tone) |
| `tag-chip-border-neutral` | `#E5E7EB` | Tag chip outline (neutral) |
| Shadow — overlay soft | `0 1px 0 rgba(0,0,0,.1), 0 4px 8px rgba(0,0,0,.06)` | Stage action buttons |
| Shadow — modal | `0 30px 60px rgba(10,15,30,.12), 0 4px 12px rgba(10,15,30,.05)` | Modal container |
| Shadow — popover | `0 20px 40px rgba(10,15,30,.18), 0 4px 8px rgba(10,15,30,.08)` | Maps picker |

### 4.2 Typography

- **UI stack**: `"Inter", -apple-system, BlinkMacSystemFont, system-ui, sans-serif`
- **Mono stack**: `"JetBrains Mono", ui-monospace, "SF Mono", Menlo, monospace`
- **Weights loaded**: 400, 500, 600, 700, 800

Named styles used in the modal (reference these by role):

| Role | Size | Weight | Letter-spacing | Line-height |
|---|---|---|---|---|
| Modal H1 (job title) | 26 | 800 | -0.8 | 1.1 |
| Section title (sheet H1) | 22 | 800 | -0.5 | 1.1 |
| Primary label on buttons | 17 | 800 | -0.2 | 1 |
| Body strong | 17 | 800 | -0.3 | 1.25 |
| Body | 15 | 600 | -0.2 | 1.25 |
| Action label | 15 | 800 | -0.2 | 1 |
| Link button | 14 | 700 | 0 | — |
| Small body | 13.5 | 600 | 0 | 1.4 |
| Chip / pill | 12.5 | 800 | -0.1 | — |
| Section caps | 12 | 800 | 1 (tracking) UPPERCASE | — |
| Label caps (tags, etc.) | 11.5 | 700–800 | 0.8 UPPERCASE | — |
| Mono timestamps | 11.5–17 | 600–800 | -0.2 | — |

### 4.3 Spacing & radii

- Base unit: **4 px**, with heavy use of 8 / 10 / 12 / 14 / 16 / 20.
- Modal outer padding: **20 px** horizontal inside cards, **16 px** vertical between blocks.
- Standard card radius: **14 px**.
- Modal container radius: **18 px**.
- Bottom sheet radius: **20 px** (top corners).
- Button radius: **12 px** (link/outline), **14 px** (big CTAs).
- Pill/chip radius: **999 px** (full).
- Hit targets: link buttons `min-height 44 px`; primary CTAs `min-height 52–60 px`; action track cards `min-height 104 px`.

### 4.4 Modal dimensions

- Width: **560 px** (fixed, centered) on desktop. Mobile: full-width with 16 px side gutter and the outer radius flattened at top.
- Max height: viewport height with internal scroll. On mobile, present as a **bottom sheet** with 20 px top radius and a 44×5 px grab handle.

---

## 5. File map

```
source/
├─ Appointment Modal Combined.html   # the HTML shell + <script> loaders + App() canvas
├─ combined-modal.jsx                # the NEW combined modal + tag editor + maps popover
├─ payment-sheet.jsx                 # existing payment flow (reused unchanged)
├─ estimate-sheet.jsx                # existing estimate flow (reused unchanged)
└─ design-canvas.jsx                 # pan/zoom canvas shell — not part of the product
```

When recreating in a real codebase, you only need to port:

1. **The modal** (`combined-modal.jsx` — `CombinedModal`)
2. **The tag editor sheet** (`combined-modal.jsx` — `CKTagEditor`)
3. **The maps picker popover** (`combined-modal.jsx` — `CKDirectionsPopover`)
4. **The payment flow** (`payment-sheet.jsx` — `State_Start`, `State_PayMethod`, `State_TapWaiting`, `State_Paid`, `State_InvoiceSent`, etc.)
5. **The estimate flow** (`estimate-sheet.jsx` — `E1_Start` through `E8_Declined`)

`design-canvas.jsx` is the design-review frame and should be discarded.

---

## 6. The modal — anatomy from top to bottom

Read `source/combined-modal.jsx` → `CombinedModal` for exact values. Below is the structural spec.

### 6.1 Container

- `width: 560px; background: #fff; border-radius: 18px; border: 1px solid #E5E7EB;`
- Box-shadow: `0 30px 60px rgba(10,15,30,.12), 0 4px 12px rgba(10,15,30,.05)`
- `overflow: hidden`
- Font-family: UI stack.

### 6.2 Header block (padding `20px 20px 16px`)

Row 1 — meta chips (gap 8 px, wrap allowed):
- **Status badge** — size `lg`, padding `4px 12px`, font `13/700`. One of:
  - Scheduled — bg `#DBEAFE`, text `#1D4ED8`
  - On the way — bg `#DBEAFE`, text `#1D4ED8`
  - On site — bg `#FFEDD5`, text `#C2410C`
  - Complete — bg `#D1FAE5`, text `#047857`
  - _All pills must `white-space: nowrap` — "On site" previously wrapped without this._
- **"Residential"** — neutral pill, bg `#F3F4F6`, text `#1F2937`.
- **"#APT-2086"** — neutral pill, same styling.

Row 2 — H1: _"Spring startup · zone check"_ (26 / 800 / -0.8 tracking / 1.1 line-height / `#0B1220`).

Row 3 — date/time: _"Thu, Apr 23 · 9:00 – 10:30 AM"_ (15 / 600 / `#4B5563`).

Right side — close button: 40×40, radius 12, 1.5 px `#E5E7EB` border, white bg, X icon 18 px stroke 2.4.

### 6.3 Timeline strip (padding `4px 20px 16px`)

Four evenly-distributed dots (min-width 72 px each) connected by 2 px horizontal lines.

Per dot:
- 22 px circle. Active (`i <= step`) fill `#0B1220` + 2 px `#0B1220` border. Inactive fill `#fff` + 2 px `#E5E7EB` border.
- If this is the current step (and not final): add outer ring `box-shadow: 0 0 0 4px #DBEAFE` and a blue 8 px inner dot (`#1D4ED8`). Otherwise, active dots show a white 12 px checkmark (stroke 3.2).
- Label (12.5 / 700 / nowrap) below the dot, 8 px gap.
- Mono time (11.5 / 600 / `#6B7280`) below label, 1 px gap.
- Connector line between dots: 2 px tall. Completed side `#0B1220`; otherwise `#E5E7EB`. `margin-top: 10 px` to align with dot center.

Labels are fixed as `Booked · En route · On site · Done`; times come from step: `9:00 / 8:42 / 9:06 / 10:48` or `—` when not yet reached.

### 6.4 Primary actions band (padding `16px 20px`, bg `#F9FAFB`, 1 px border top + bottom `#E5E7EB`)

Small caps heading: _"ON-SITE OPERATIONS"_ — 12 / 800 / 1 tracking / `#4B5563` / margin-bottom 10.

Then `<CKActionTrack>` — three side-by-side cards, gap 8 px, flex 1 each:

**Each card** — border-radius 14, min-height 104 px, padding `14px 10px`, flex column centered, gap 6, font UI stack, box-shadow `0 1px 0 rgba(0,0,0,.1), 0 4px 8px rgba(0,0,0,.06)`:

- State "active / ready": solid fill in stage color. Inner 36×36 icon bubble uses `rgba(255,255,255,.18)` bg.
- State "disabled": `opacity: 0.4; cursor: not-allowed;` no shadow.
- State "done": white bg, 2 px green border (`#047857`), green text, inner icon bubble is white with 2 px green border and a green checkmark.

| Slot | Fill color | Icon | Label | Sub (pre) | Sub (done) |
|---|---|---|---|---|---|
| 1 | `#1D4ED8` | paper-plane/nav | `On my way` | `Text customer` | `8:42 AM` |
| 2 | `#C2410C` | play | `Job started` | `Log arrival` | `9:06 AM` |
| 3 | `#047857` | check-circle | `Job complete` | `Close out` | `10:48 AM` |

Icon: 20 px, stroke width 2.6. Label: 15 / 800 / -0.2 / nowrap. Sub: 12 / 700 / nowrap — mono font when in "done" state, UI font otherwise.

Disabled rule: slot 2 disabled when `step < 1`; slot 3 disabled when `step < 2`.

**Second row** — link-button strip, gap 8, margin-top 10, wrap allowed. Four buttons in this order:

1. `Add photo` — photo icon
2. `Notes` — doc icon
3. `Review` — star icon
4. **`Edit tags`** — tag icon. When the tag editor is open, this button goes to an "active" state: bg `#EDE9FE`, border `#6D28D9`, text `#6D28D9`.

> **⚠ The former `AI draft` button (violet, sparkle icon) is removed.**

Each link button: min-height 44, padding `0 14px`, radius 12, 1.5 px border `#E5E7EB`, white bg, text 14 / 700 / `#0B1220`, 6 px gap between icon (16 px stroke 2.2) and label.

### 6.5 Payment + Estimate CTAs (padding `16px 20px 0`, flex column, gap 10)

Two stacked full-width outline buttons. Each: full width, min-height 60, radius 14, 2 px solid border in its color, white bg, text 16 / 800, gap 10, icon 22 px stroke 2.2.

- **Collect payment** — border + text `#0F766E` (teal), icon = credit card.
- **Send estimate** — border + text `#6D28D9` (violet), icon = doc.

Both are always visible (no role / step gating in this modal).

**Click behavior:**

- _Collect payment_ → opens `PaymentSheet` over the modal as a bottom sheet. Initial state = `State_Start` (if an agreement job) or the one-off variant, per the existing payment-sheet decision logic.
- _Send estimate_ → opens `EstimateSheet` over the modal as a bottom sheet. Initial state = `E1_Start` (empty line items).

### 6.6 Customer hero card (margin `16px 20px 16px`, radius 14, 1.5 px border `#E5E7EB`, overflow hidden)

**Header strip** (padding `14px 16px`, bg `#CCFBF1`, 1 px bottom border `#E5E7EB`):
- 44×44 white avatar circle with 2 px teal border, text "TU" / 16 / 800 / `#0F766E`.
- Name "Test User" — 18 / 800 / -0.3.
- History — "1 previous job · Last service Oct 2025" — 12.5 / 600 / `#4B5563`.

**Tags row** _(new)_ (padding `12px 16px`, bg `#fff`, 1 px bottom border `#E5E7EB`):
- Left label "TAGS" — 11.5 / 800 / `#6B7280` / 0.8 tracking / flex-shrink 0.
- Right: flex row, gap 6, wrap allowed. Each chip: see §7 (Tag chip).
- Default chips in this mock:
  - "Repeat customer" — green tone
  - "Back gate — side yard" — amber tone
  - "Prefers text" — blue tone

**Phone row** (padding `14px 16px`, bg `#fff`, 1 px bottom border):
- 36×36 blue-bg (`#DBEAFE`) icon badge, phone icon 18 px, text `#1D4ED8`.
- "PHONE" caps label.
- `(952) 737-3312` — 17 / 800 / mono / -0.2.
- Right-aligned **Call chip**: padding `8px 14px`, radius 10, bg `#1D4ED8`, text `#fff`, 13 / 800, "Call" label with 14 px phone icon.
- Row is an `<a href="tel:…">`.

**Email row** (padding `14px 16px`, bg `#fff`):
- 36×36 soft-bg icon badge (`#F9FAFB`), mail icon 18.
- Plain 14 / 600 / `#1F2937`.
- `<a href="mailto:…">` wraps the row.

### 6.7 Property / directions card (margin `0 20px 16px`, radius 14, 1.5 px border)

**Top section** (padding `14px 16px`, bg `#fff`):
- Caps label "PROPERTY" with a 12 px pin icon.
- Address line 1: "1 Test Street" — 19 / 800 / -0.3 / 1.2 line-height.
- Address line 2: "Eden Prairie, MN 55344" — 15 / 600 / `#1F2937`.

**Get directions CTA** (relative-positioned parent so the popover anchors above):
- Full-width blue button, padding `14px 16px`, bg `#1D4ED8`, text `#fff` 16 / 800, centered content, gap 8, nav icon 20 / stroke 2.4. Bottom-left / bottom-right radius 12 px so the CTA's base matches the card.

**When tapped — Maps picker popover** (§7 spec):
- Anchors `position: absolute; left: 16; right: 16; bottom: calc(100% + 8px)`.
- Radius 14, bg `#fff`, 1.5 px border, popover shadow.
- Caps header "OPEN IN" (padding `10px 14px`, bg `#F9FAFB`, 1 px bottom border).
- Two rows, identical structure — each a full-width button with:
  - 36×36 tinted icon badge (teal for Apple, blue for Google), nav icon 18 stroke 2.4.
  - Label 14.5 / 800 / -0.2.
  - Sub 12.5 / 600 / `#6B7280`.
  - External-link icon 14 / `#6B7280` on the right.
  - Row 1 — **Apple Maps** — bg `#CCFBF1`, icon text `#0F766E`, sub "Default iOS maps app".
  - Row 2 — **Google Maps** — bg `#DBEAFE`, icon text `#1D4ED8`, sub "Opens in Google Maps app".
  - Divider 1 px `#E5E7EB` between the rows.
- Footer row (padding `8px 10px`, bg `#F9FAFB`, 1 px top border): a full-width transparent button "Remember my choice" — 12.5 / 700 / `#6B7280`.

**Open handlers** (app side — see §8.3 for deep links):
- Apple Maps → `https://maps.apple.com/?daddr=…` (or `maps://` on iOS).
- Google Maps → `https://www.google.com/maps/dir/?api=1&destination=…`.

### 6.8 Scope + materials card (margin `0 20px 16px`, radius 14, 1.5 px border, bg `#fff`)

- Row: tools icon, caps label "SCOPE", value "Full spring startup & zone check" in **strong** style (17 / 800 / -0.2). Right side empty. 1 px bottom border.
- Row: three neutral pills — "~90 min", "1 staff", and amber "Normal" priority. 1 px bottom border.
- Row: caps "MATERIALS" with a 12 px box icon. Below, a wrap row of 4 tags, each `padding 8px 12px`, radius 10, bg `#F9FAFB`, 1.5 px border `#E5E7EB`, text 13.5 / 700 / `#0B1220`.

### 6.9 Assigned tech card (margin `0 20px 16px`, radius 14, 1.5 px border, bg `#fff`)

- Single row. User icon. Caps "ASSIGNED TECH". Value "Viktor K. · Route #3". Right side: a `Reassign` link button.

### 6.10 Footer (padding `14px 20px 18px`, bg `#F9FAFB`, 1 px top border)

Flex row, gap 8, wrap allowed:

1. `Edit` (pencil icon) — neutral link button.
2. `No show` (alert icon) — neutral link button.
3. `Cancel` (X icon) — destructive: text `#B91C1C`, border `#FCA5A5`.

---

## 7. Sub-components — exact specs

### 7.1 Tag chip

Inline-flex pill used in the customer tags row and the tag editor.

- Radius **999**.
- Padding: `5px 10px` when static; `5px 6px 5px 10px` when removable.
- Font: 12.5 / 800 / -0.1, UI stack, `white-space: nowrap`.
- Border: 1.5 px solid (color per tone, see §4.1).
- Gap 6 px between label and remove-X.
- Remove-X: 18×18 circle, `background: rgba(0,0,0,.08)`, color matches text tone. Inner icon 11 / stroke 3.
- Tone palette:

| Tone | Text | Bg | Border |
|---|---|---|---|
| neutral | `#1F2937` | `#F3F4F6` | `#E5E7EB` |
| blue | `#1D4ED8` | `#DBEAFE` | `#93C5FD` |
| green | `#047857` | `#D1FAE5` | `#86EFAC` |
| amber | `#B45309` | `#FEF3C7` | `#FCD34D` |
| violet | `#6D28D9` | `#EDE9FE` | `#C4B5FD` |

Tone assignment rule: assign by tag category, not by vibe. Suggested mapping:

- **green** — loyalty / positive customer attributes ("Repeat customer", "VIP")
- **amber** — caution / job-site conditions ("Back gate — side yard", "Difficult access", "Gate code needed")
- **blue** — communication preferences ("Prefers text")
- **violet** — newly added / unreviewed tags
- **neutral** — anything else / custom

### 7.2 Link button (`CKLinkBtn`)

- `min-height 44`, padding `0 14px`, radius 12, border 1.5 px.
- Default: white bg, `#E5E7EB` border, `#0B1220` text.
- **Active state** (used on Edit tags when editor is open): bg `#EDE9FE`, border `#6D28D9`, text `#6D28D9`.
- Destructive variant: text `#B91C1C`, border `#FCA5A5`.
- Icon optional: 16 px, stroke 2.2, 6 px gap before label.

### 7.3 Sheet container (used for Tag editor, Payment sheet, Estimate sheet)

- Width 560 (match modal).
- bg `#fff`, radius **20** top, 1 px border `#E5E7EB`, shadow matches modal.
- Grab handle at top: 44×5, radius 3, bg `#E5E7EB`, centered, padding `10px 0 4px`.
- Header row (padding `4px 20px 16px`, align-items center, gap 12):
  - Optional Back button (44×44, 1.5 px border, radius 12, back-arrow icon 20 / stroke 2.4).
  - Title 22 / 800 / -0.5.
  - Optional subtitle 13.5 / 600 / `#4B5563`.
  - Close button — same styling as the Back button, X icon.
- Body: padding `0 20px 20px`, `overflow: auto`, `flex: 1`.
- Footer: padding `14px 20px 18px`, bg `#F9FAFB`, 1 px top border.

### 7.4 Maps picker popover

See §6.7. Anchors above the Get directions button. Closes on outside click, `Esc`, or row selection.

---

## 8. Interactions & behavior

### 8.1 Modal open/close

- Opens from the scheduling calendar appointment chip.
- Dismiss: X in header, backdrop click, `Esc`. Backdrop: `rgba(11,18,32,.4)` with a subtle blur (`backdrop-filter: blur(4px)`) if the stack supports it.
- On mobile, enter as a bottom sheet (slide up, 220 ms ease-out); on desktop, fade + scale (180 ms).

### 8.2 Stage action track

- Tapping `On my way` → stage becomes `done`, sub flips to the timestamp (format `h:mm A` local), and the second card becomes enabled. Optimistic update; on API failure, revert + toast.
- `Job started` → same pattern, enables `Job complete`.
- `Job complete` → transitions modal status badge to "Complete" and reveals a receipt / summary strip (see Redesign prototype for that detail).
- Each transition also posts to the timeline strip (dot flips from current-blue to black-check).

### 8.3 Get directions → Maps picker

**Open behavior**

- First tap on Get directions opens the popover (do **not** deep-link straight to a map). This is a deliberate decision so staff can choose their preferred app.
- If the user has previously checked "Remember my choice" (stored per-user in settings), skip the popover and open directly. Still show the popover on long-press / right-click for re-choice.

**URLs to open**

- Apple Maps: `maps://?daddr=<encoded address>` on iOS → falls back to `https://maps.apple.com/?daddr=<encoded address>`.
- Google Maps (universal): `https://www.google.com/maps/dir/?api=1&destination=<encoded address>`. On Android, let the OS route the intent to the Google Maps app; on iOS, use `comgooglemaps://?daddr=<encoded address>` first and fall back to the https URL if the app isn't installed.

Address encoding uses `encodeURIComponent("1 Test Street, Eden Prairie, MN 55344")`. If the customer record has a lat/long, prefer `destination=<lat>,<lng>` with `destination_place_id=<id>` for Google Maps.

**Remember my choice**

- Persist to the authenticated user's settings (e.g. `user.preferred_maps_app = "apple" | "google"`).
- Not device-scoped unless the app has no server sync; in that case, localStorage.

### 8.4 Edit tags sheet

**Open trigger**

- Tap "Edit tags" link button in the action strip.
- Button enters active state (§7.2).
- Sheet opens as a bottom sheet (modal over modal is fine — layer z-index above).

**Sheet layout**

- Title: "Edit tags". Subtitle: "Tags apply to Test User across every job — past and future".
- **Current tags** section:
  - Section caps label "CURRENT TAGS".
  - Container: padding 12, radius 12, bg `#F9FAFB`, 1.5 px border, flex wrap, gap 8, `min-height 58 px`, align-items center.
  - Each tag is rendered removable (see §7.1).
  - End-of-row "Add custom" button: padding `5px 10px`, 1.5 px dashed `#6B7280` border, transparent bg, text `#4B5563`, 12.5 / 700, with a 12 px plus icon.
- **Suggested** section:
  - Caps label "SUGGESTED" (margin `18px 0 10px`).
  - Flex-wrap row, gap 8. Each suggestion is a white button: padding `8px 12px`, radius 999, 1.5 px `#E5E7EB` border, `#1F2937` text, 13 / 700, 12 px plus icon + label, gap 6.
  - Suggestions to seed: `Repeat customer`, `Commercial`, `Difficult access`, `Dog on property`, `Prefers text`, `Gate code needed`, `Corner lot`. Filter out any that are already applied.
- **Info banner**:
  - Padding 14, radius 12, bg `#DBEAFE`, 1.5 px `#1D4ED8` border.
  - 28×28 blue icon circle (user icon), text `#1D4ED8`, 13 / 700 / 1.45 line-height:
  - Copy: "Changes save to Test User's customer profile. Next job auto-inherits these tags — techs will see them on the route card."

**Footer**

- Two buttons. 10 gap.
- `Cancel` — flex 1, white bg, 2 px `#E5E7EB` border, `#1F2937` text, 15 / 800, min-height 52, radius 12.
- `Save tags · applies everywhere` — flex 2, bg `#0B1220`, white text, 15 / 800, min-height 52, radius 12, check icon 18 px stroke 2.6.

**Save behavior (critical — this is the requirements core)**

1. Collect the current tag list from local editor state.
2. PATCH to the **customer** resource (not the appointment): e.g. `PATCH /customers/:id { tags: [...] }`.
3. On success:
   - Emit a customer-updated event so any open views (customer tab, future jobs list) refresh.
   - Update the tags row in the appointment modal (optimistic update first; reconcile after response).
   - The customer's future appointments automatically reflect the new tags — no copy is stored on individual appointments.
4. On failure: toast "Couldn't save tags — try again" and restore previous state.

**Data model note**

- Tags live on `customers.tags: Tag[]`. An individual appointment should **not** duplicate the tag data — read tags via `appointment.customer.tags` so a customer-level edit is reflected everywhere without a migration.
- A `Tag` is `{ id: string; label: string; tone: "neutral" | "blue" | "green" | "amber" | "violet"; source: "manual" | "system"; }`. Reserved system tags (e.g. auto-applied "Overdue balance") are not removable from this sheet — render the remove-X disabled with a tooltip explaining why.

### 8.5 Collect payment → Payment sheet

- Opens the existing payment flow unchanged. Entry state depends on whether the job belongs to a service agreement (see `source/payment-sheet.jsx` → `State_Start`).
- Close of the payment sheet returns focus to the appointment modal.
- On successful payment, the modal's payment CTA should collapse into a "Paid — $NNN · $method" confirmation card (green styling, as in the prior redesign).

### 8.6 Send estimate → Estimate sheet

- Opens `E1_Start`. Full flow in `source/estimate-sheet.jsx`:
  - Add line items from catalog or custom input
  - Review total
  - Send via SMS (default) or email
  - Await customer YES/NO reply
  - Receive approval/decline
- On send, post the estimate to the backend; track its state so returning to the appointment shows the most recent estimate status banner (e.g. "Estimate #EST-0142 sent · awaiting reply").

### 8.7 Timeline & status machine

```
state step  status badge   timeline dots filled   ActionTrack disabled past
  0   "Scheduled"         1                       none
  1   "On the way"        2                       —
  2   "On site"           3                       —
  3   "Complete"          4                       all three "done"
```

Advance states only via the big action buttons; never skip.

---

## 9. Accessibility

- The modal must be a proper dialog: `role="dialog" aria-modal="true"`, labeled by the job title, initial focus on the close button.
- Trap focus inside the modal while open. Return focus to the triggering calendar chip on close.
- Status badges: include `aria-label="Status: On site"` so screen readers don't miss the pill semantics.
- The action-track buttons are **not** toggles — they are a linear workflow. Use `<button>` elements, label them fully ("On my way, text customer"), and announce the result via `aria-live="polite"` when a stage completes.
- Tag chips: the remove-X needs an accessible label like `aria-label="Remove tag: Repeat customer"`.
- Maps picker popover: render in a `role="menu"` with `role="menuitem"` rows. `Esc` closes. Manage focus: first menu item on open, return to trigger on close.
- The "Remember my choice" control needs to be reachable by keyboard and describe state ("checked" / "not checked"). If it's a button in the design, make it a `<button aria-pressed>` or convert to a real checkbox.
- Hit targets meet 44×44 minimum everywhere. Do not shrink on compact viewports.
- Color alone never encodes meaning: tag tones are paired with distinct labels; status is always paired with text.

---

## 10. Responsive behavior

- ≥ 640 px: centered modal, 560 px wide, 24 px gutter.
- < 640 px: bottom sheet, full viewport width, top radius 20, drag handle visible, sheet fills up to 92 vh with internal scroll. Header becomes sticky.
- Timeline strip: at < 360 px width, reduce per-dot min-width to 60 px, drop the mono time to 11 px, and let it scroll horizontally rather than squish labels.
- Payment/Estimate CTAs stay full-width on all breakpoints.
- The customer hero avatar and name never truncate; the history line uses `text-overflow: ellipsis` on overflow.

---

## 11. Content / copy used in the prototype

Strings appear in English and should be localized. Keys suggested below — production content should use i18n resources, not hard-coded strings.

| Key | Copy |
|---|---|
| `modal.job_title` | `Spring startup · zone check` |
| `modal.schedule_line` | `Thu, Apr 23 · 9:00 – 10:30 AM` |
| `modal.status.scheduled` | `Scheduled` |
| `modal.status.on_the_way` | `On the way` |
| `modal.status.on_site` | `On site` |
| `modal.status.complete` | `Complete` |
| `modal.ops_heading` | `ON-SITE OPERATIONS` |
| `action.on_my_way.label` | `On my way` |
| `action.on_my_way.sub_pre` | `Text customer` |
| `action.job_started.label` | `Job started` |
| `action.job_started.sub_pre` | `Log arrival` |
| `action.job_complete.label` | `Job complete` |
| `action.job_complete.sub_pre` | `Close out` |
| `link.add_photo` | `Add photo` |
| `link.notes` | `Notes` |
| `link.review` | `Review` |
| `link.edit_tags` | `Edit tags` |
| `cta.collect_payment` | `Collect payment` |
| `cta.send_estimate` | `Send estimate` |
| `customer.tags_label` | `TAGS` |
| `section.scope_label` | `SCOPE` |
| `section.materials_label` | `MATERIALS` |
| `footer.edit` | `Edit` |
| `footer.no_show` | `No show` |
| `footer.cancel` | `Cancel` |
| `maps.header` | `OPEN IN` |
| `maps.apple.label` | `Apple Maps` |
| `maps.apple.sub` | `Default iOS maps app` |
| `maps.google.label` | `Google Maps` |
| `maps.google.sub` | `Opens in Google Maps app` |
| `maps.remember` | `Remember my choice` |
| `tags.sheet.title` | `Edit tags` |
| `tags.sheet.subtitle` | `Tags apply to Test User across every job — past and future` |
| `tags.current_heading` | `CURRENT TAGS` |
| `tags.suggested_heading` | `SUGGESTED` |
| `tags.add_custom` | `Add custom` |
| `tags.save_info` | `Changes save to Test User's customer profile. Next job auto-inherits these tags — techs will see them on the route card.` |
| `tags.save_button` | `Save tags · applies everywhere` |
| `tags.cancel_button` | `Cancel` |

---

## 12. State management (recommended shape)

```ts
type AppointmentModalState = {
  appointmentId: string;
  step: 0 | 1 | 2 | 3;               // 0 scheduled, 1 on the way, 2 on site, 3 complete
  openSheet: null | "payment" | "estimate" | "tags";
  mapsPopover: { open: boolean; rememberChoice: boolean; choice: "apple" | "google" | null };
};

type Customer = {
  id: string;
  name: string;
  phone: string;
  email: string;
  tags: Tag[];                       // single source of truth — not denormalized to appointments
  history: CustomerHistorySummary;
};

type Tag = {
  id: string;
  label: string;
  tone: "neutral" | "blue" | "green" | "amber" | "violet";
  source: "manual" | "system";
};

// Edit tags sheet local state
type TagEditorState = {
  draftTags: Tag[];
  customInput: string;
  dirty: boolean;
  saving: boolean;
  error: string | null;
};
```

Mutations:

- `advanceStage(appointmentId, nextStep)` — PATCH `/appointments/:id { status }`.
- `saveCustomerTags(customerId, tags)` — PATCH `/customers/:id { tags }`. Invalidate any query that reads this customer.
- `openMapsFor(address, choice)` — pure navigation; no server call.

---

## 13. Assets

- Icons are rendered as inline SVG via a small `Icon` component (see `source/combined-modal.jsx`). All paths/coordinates are in that file. You can replace them with your codebase's existing icon set (Lucide, Phosphor, Heroicons — all of these have equivalents for every icon used: phone, mail, pin, nav, play, check-circle, star, card, box, doc, pencil, x, alert-circle, tools/wrench, plus, photo, user, tag, external-link).
- No bitmap images are used.
- Fonts: Inter + JetBrains Mono from Google Fonts. If your codebase hosts its own copy, swap accordingly.

---

## 14. Known edge cases / things to handle

- **Customer with zero tags**: hide the tags row entirely (or show a subtle "No tags · Add" ghost button — design preference, surface to PM).
- **Long address**: address lines wrap cleanly; don't truncate. The Get directions CTA remains full width.
- **Long tag labels**: tags use `white-space: nowrap` — they cannot wrap inside a chip. If a user types a very long custom tag, cap at 32 chars on input.
- **Offline**: Get directions picker still works (URLs just hand off to the OS). Save-tags fails gracefully with a toast.
- **Multiple simultaneous sheet opens**: not allowed. Opening Payment closes Tag editor, etc. Use the single `openSheet` enum above.
- **Role**: the mock renders the same modal for both admin and tech roles. The only role-gated control in this design is "Reassign" on the tech row — hide for tech users.

---

## 15. Out of scope for this handoff

- The scheduling calendar view that opens the modal.
- The customer profile page (where these tags also appear) — design exists separately; ensure the same `Tag` visual system is reused.
- Route card on the tech app — tags should render there using the same chip component, but layout is its own spec.
- The full payment / estimate flows' logic — already specced in their respective source files.

---

## 16. How to verify your implementation

Open `source/Appointment Modal Combined.html` in a browser and compare side-by-side with your build. The HTML uses a design-canvas wrapper — ignore the canvas chrome; the nested modal artboards are the authoritative reference.

Artboards to match:
- `combined / c-default` — baseline modal, tags visible, maps popover closed.
- `combined / c-maps` — maps popover open above Get directions.
- `combined / c-tags-active` — Edit tags button in active state.
- `tag-editor / tg-empty` — sheet with three default tags.
- `tag-editor / tg-edited` — sheet after adding "Dog on property".
- `payment-flow / p1–p4` — payment flow (sheet).
- `estimate-flow / e1–e8` — estimate flow (sheet + customer-phone SMS view).
