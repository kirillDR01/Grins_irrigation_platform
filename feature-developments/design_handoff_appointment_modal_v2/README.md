# Handoff: Appointment Modal — Combined v2

## Overview

This is the redesigned **Appointment Detail Modal** for the Sales / Field-Service admin dashboard. It opens when a dispatcher or technician taps an appointment from the schedule view. The modal is the operational hub for a single job — it surfaces customer info, location/directions, scope, materials, the assigned tech, and provides one-tap access to the on-site workflow (On my way → Job started → Job complete), payment collection, estimate generation, customer-tag management, attached photos, and a centralized internal-notes panel.

**v2 enhancements** (over v1 `Appointment Modal Combined.html`):
1. **Inline "See attached photos" dropdown** under the secondary action row — shows photos already attached to the customer file (any past job), with a primary **Upload photo · camera roll** CTA + secondary **Take photo** CTA at the top of the panel. Designed for phone use — `Upload photo` should open the device camera roll / photo library picker.
2. **Inline "See attached notes" dropdown** that opens a single, centralized **Internal Notes** card. This **replaces** the older multi-author thread (dispatch / tech / customer). One shared note body, edited in place, used as the source of truth for everyone touching the job.
3. The old "Review" star button is now labeled **Send Review Request**.

## About the Design Files

The files in this bundle are **design references created in HTML / inline-Babel JSX**. They are prototypes showing the intended look, layout, density, and behavior — **not production code to copy directly**.

The task is to **recreate these designs in the target codebase's existing environment** (whatever framework the Sales admin dashboard uses — React, Vue, etc.) using its established component library, design tokens, and patterns. If no target environment exists yet, choose the most appropriate framework for the project and implement the designs there.

The HTML files use React 18 + inline JSX via `@babel/standalone` for ergonomic prototyping. They are **not** intended to be shipped to production.

## Fidelity

**High-fidelity (hifi).** Colors, typography, spacing, border radii, and interaction states are all final and intentional. Recreate the UI pixel-perfectly using the codebase's existing components where they exist; extend the design system where they don't. Exact tokens are listed in the **Design Tokens** section below.

## Files in This Handoff

```
designs/
├── Appointment Modal Combined v2.html       ← The v2 design (PRIMARY DELIVERABLE)
├── combined-modal-v2.jsx                    ← v2 components (V2AttachedPhotos, V2InternalNotes, V2LinkBtn, CombinedModalV2)
├── Appointment Modal Combined.html          ← v1 (reference — unchanged)
├── combined-modal.jsx                       ← v1 components — REUSED by v2 (tokens, icons, primitives)
├── Appointment Modal with Estimates.html    ← Sibling design — estimate flow context
├── Appointment Modal Redesign.html          ← Original modal redesign — context only
├── design-canvas.jsx                        ← Prototype-only canvas/artboard helper (DO NOT ship)
├── estimate-sheet.jsx                       ← Estimate flow components (referenced by combined modal)
├── payment-sheet.jsx                        ← Payment flow components (referenced by combined modal)
├── modal.jsx                                ← Original modal primitives (superseded by combined-modal.jsx)
└── receipt-tape.jsx                         ← Receipt printout component (referenced by payment flow)
```

**The deliverable is `Appointment Modal Combined v2.html`** rendered at the `v2-default` artboard (and the three other v2 artboards which show different open/edit states of the same modal).

## Screens / Views

The modal is a single composite screen with several inline expandable regions. Width is `560px` on tablet/desktop and full-width on mobile. The whole modal scrolls vertically — there is no internal scroll region.

### Modal — top to bottom

#### 1. Header
- Padding: `20px 20px 16px`
- Status badge row (`flex-wrap`, gap `8px`):
  - `<CKStatusBadge step={2} />` — orange "On site" pill (`bg #FFEDD5`, color `#C2410C`)
  - "Residential" pill (`bg #F3F4F6`, color `#1F2937`)
  - "#APT-2086" pill (same neutral)
- Title: "Spring startup · zone check" — `26px / 800 / -0.8 letter-spacing / 1.1 line-height`, color `#0B1220`
- Subtitle: "Thu, Apr 23 · 9:00 – 10:30 AM" — `15px / 600`, color `#4B5563`
- Close button: top-right, `40×40`, `12px` radius, `1.5px` border `#E5E7EB`, white bg, X icon

#### 2. Timeline strip
- Padding: `4px 20px 16px`
- 4 dots: Booked → En route → On site → Done — connected by `2px` lines
- Active dot: `22×22`, ink fill, white check
- Current dot: white fill with blue inner dot, `4px` light-blue halo
- Inactive dot: white fill, `2px` border `#E5E7EB`
- Each dot has a label (`12.5px / 700`) and a time (`11.5px / 600 / monospace`) below

#### 3. On-site operations block
- Background `#F9FAFB`, top + bottom borders `#E5E7EB`, padding `16px 20px`
- Section eyebrow: "ON-SITE OPERATIONS" — `12px / 800 / 1px tracking / uppercase`, color `#4B5563`
- **Action track**: 3 large buttons in a flex row, gap `8px`, each `min-height: 104px`, radius `14px`:
  - "On my way" — blue `#1D4ED8` (uses Send/navigation icon `M2 11l20-9-9 20-2-9-9-2Z`)
  - "Job started" — orange `#C2410C` (play icon)
  - "Job complete" — green `#047857` (checked-circle icon)
  - When `done`, button flips to white bg + colored border + check icon, time replaces sub-label, font-family for sub becomes monospace
  - Disabled states: opacity `0.4`, no shadow, `cursor: not-allowed`
  - Default shadow: `0 1px 0 rgba(0,0,0,0.1), 0 4px 8px rgba(0,0,0,0.06)`
- **Secondary action row** (margin-top `10px`, flex-wrap, gap `8px`):
  - **See attached photos** — V2LinkBtn, blue accent, count badge `5`, chevron-down (rotates to chevron-up when open)
  - **See attached notes** — V2LinkBtn, amber accent, count badge `1`, chevron-down
  - **Send Review Request** — CKLinkBtn with star icon
  - **Edit tags** — CKLinkBtn with tag icon
  - All buttons `min-height: 44px` (mobile-tappable), padding `0 12px`, radius `12px`, border `1.5px #E5E7EB`, font `14px / 700`
  - Open V2LinkBtn states (see Design Tokens > Accent map below): bg = accent's light tint, color = accent, border = accent

#### 4. Inline expansion panels (only one open at a time)

##### 4a. Attached photos panel (when "See attached photos" is open)
- Margin-top `10px` from the action row, radius `14px`, `1.5px` border `#1D4ED8`, white bg
- **Header bar**: light-blue bg `#DBEAFE`, padding `10px 14px`, photo icon + "Attached photos" + count chip (solid `#1D4ED8` bg, white text) + right-aligned "From customer file" label
- **Upload CTAs row** (NEW — primary path for phones): white bg, padding `12px`, bottom border, flex gap `8px`
  - **Upload photo · camera roll** — primary, flex-1, `min-height: 48px`, `bg #1D4ED8 / white text`, radius `12px`, upload-arrow icon. **Behavior**: triggers a native file picker scoped to the photo library — on web use `<input type="file" accept="image/*" multiple />`; on iOS Safari this opens "Photo Library" by default. The `· camera roll` suffix uses monospace `11.5px` and opacity `0.9`.
  - **Take photo** — secondary, white bg, `1.5px` blue border, blue text, camera icon. **Behavior**: triggers native camera capture — on web use `<input type="file" accept="image/*" capture="environment" />`.
- **Photo strip** (horizontal scroll, padding `12px`, gap `10px`, `-webkit-overflow-scrolling: touch`):
  - Photo cards: `180px` wide, `134px` image area, `1.5px` border `#E5E7EB`, radius `12px`
  - Image area is a striped SVG placeholder (45° diagonal stripes) tinted by `hue` (amber / teal / violet / blue / slate). The placeholder shows an uppercase mono label centered. **In production, replace with actual photo `<img>` tags**.
  - Caption row below image: `12px / 700` caption + `10.5px / 600 monospace` date
  - Trailing "Add more · From library" tile at the end of the strip — `110px` wide, dashed `1.5px` border, `+` icon
- **Footer**: `#F9FAFB` bg, padding `8px 14px 10px`, top border. Left: "Tap a photo to expand · pinch to zoom" hint. Right: "View all (5)" outlined button.

**Photo data shape**:
```ts
type Photo = {
  id: string;
  url: string;             // full-resolution image
  thumbUrl?: string;       // optional thumb for the strip
  label: string;           // short alt-text label
  caption: string;         // 1-line caption
  date: string;            // "Oct 2025" / "Mar 2024" — relative to the customer file, not necessarily this appointment
  jobId?: string;          // source appointment, for "View all" filter
};
```

##### 4b. Internal notes panel (when "See attached notes" is open)
**This replaces the v1 multi-author thread.** It is a single shared note body, no per-author entries, no role badges.

- Margin-top `10px`, radius `14px`, `1.5px` border `#E5E7EB`, white bg, subtle shadow `0 1px 2px rgba(10,15,30,0.04)`
- **Header**: padding `18px 20px 14px`, flex row
  - Eyebrow "INTERNAL NOTES" — `12.5px / 800 / 1.4px tracking / uppercase`, color `#64748B` (slate)
  - Right-aligned **Edit** affordance (only in view mode): pencil icon + "Edit" text, `14px / 700`, color `#64748B`, transparent background, no border
- **View mode**: padding `0 20px 22px`, body text `14.5px / 500 / 1.6 line-height`, color `#0B1220`, `min-height: 80px`
- **Edit mode**:
  - Textarea — full width, `min-height: 150px`, padding `12px 14px`, radius `12px`, `1.5px` border `#E5E7EB`, font `14.5px / 500 / 1.5 line-height`, `resize: vertical`, `outline: none`
  - Button row below textarea (margin-top `14px`, gap `12px`, justified end):
    - **Cancel** — white bg, `1.5px` border `#E5E7EB`, color `#1F2937`, padding `12px 28px`, radius `999px`, `15px / 700`, `min-width: 120px`
    - **Save Notes** — teal bg `#14B8A6`, `1.5px` border `#14B8A6`, white text, padding `12px 28px`, radius `999px`, `15px / 700`, `min-width: 140px`

**Internal-notes data shape**:
```ts
type AppointmentNotes = {
  appointmentId: string;
  body: string;            // single shared text blob, plain text or basic markdown
  updatedAt: string;       // ISO timestamp
  updatedBy: { id: string; name: string; role: 'dispatch' | 'tech' | 'admin' };
};
```

#### 5. Collect payment + Send estimate buttons
- Padding `16px 20px 0`, vertical stack, gap `10px`
- **Collect payment**: white bg, `2px` teal border `#0F766E`, teal text, `min-height: 60px`, radius `14px`, `16px / 800`, credit-card icon, opens the existing payment sheet flow
- **Send estimate**: white bg, `2px` violet border `#6D28D9`, violet text, same dimensions, doc icon, opens the existing estimate sheet flow

#### 6. Customer hero card
- Margin `16px 20px`, radius `14px`, `1.5px` border `#E5E7EB`, overflow hidden
- **Header strip**: teal-tint bg `#CCFBF1`, padding `14px 16px`, bottom border
  - Avatar: `44×44 round`, white bg, teal `#0F766E` text "TU", `2px` teal border
  - Name "Test User" — `18px / 800 / -0.3 letter-spacing`
  - Sub "1 previous job · Last service Oct 2025" — `12.5px / 600`, color `#4B5563`
- **Tags row**: white bg, padding `12px 16px`, bottom border, flex
  - "TAGS" eyebrow — `11.5px / 800 / 0.8px tracking / uppercase`, color `#6B7280`
  - Tag chips (CKTagChip) — flex-wrap, gap `6px`. Default chips:
    - "Repeat customer" — green tone (`bg #D1FAE5 / color #047857 / border #86EFAC`)
    - "Back gate — side yard" — amber tone (`bg #FEF3C7 / color #B45309 / border #FCD34D`)
    - "Prefers text" — blue tone (`bg #DBEAFE / color #1D4ED8 / border #93C5FD`)
- **Phone row**: `<a href="tel:...">`, white bg, padding `14px 16px`, bottom border, flex gap `12px`
  - Icon disc `36×36`, light-blue bg, blue icon
  - "PHONE" eyebrow + "(952) 737-3312" in monospace `17px / 800`
  - Trailing **Call** button: solid blue, white text, padding `8px 14px`, radius `10px`
- **Email row**: `<a>`, padding `14px 16px`, light envelope icon, "test@example.com"

#### 7. Property / Get directions block
- Margin `0 20px 16px`, radius `14px`, `1.5px` border `#E5E7EB`
- White content area, padding `14px 16px`:
  - "📍 PROPERTY" eyebrow
  - "1 Test Street" — `19px / 800`
  - "Eden Prairie, MN 55344" — `15px / 600`
- **Get directions button**: full-width, blue `#1D4ED8` bg, white text, `min-height: 52px`, navigation icon, `16px / 800`, bottom-rounded
- **When clicked**, opens a popover (`CKDirectionsPopover`) anchored above the button:
  - White card with shadow, `1.5px` border, radius `14px`, z-index `5`
  - Header chip: "OPEN IN" eyebrow on `#F9FAFB` bg
  - **Apple Maps** row — teal icon disc, "Default iOS maps app" sub
  - **Google Maps** row — blue icon disc, "Opens in Google Maps app" sub
  - Footer: "Remember my choice" link button on `#F9FAFB`
  - Each row has an external-link arrow on the right

#### 8. Job scope & materials
- Margin `0 20px 16px`, radius `14px`, white bg
- **Scope row** (CKRow): tools icon, label "SCOPE", value "Full spring startup & zone check" (strong `17px / 800`)
- **Pills row**: "~90 min", "1 staff", "Normal" (amber)
- **Materials**: "📦 MATERIALS" eyebrow, then 4 chips: "Rotor nozzles (×4)", "Pressure regulator", "Backflow kit", "Thread tape" — each chip: `8px 12px` padding, radius `10px`, `#F9FAFB` bg, `1.5px` border `#E5E7EB`, `13.5px / 700`

#### 9. Tech assignment
- Margin `0 20px 16px`, radius `14px`, `1.5px` border `#E5E7EB`, white bg
- CKRow: user icon, "ASSIGNED TECH" eyebrow, "Viktor K. · Route #3", trailing **Reassign** outlined button

#### 10. Footer actions
- Padding `14px 20px 18px`, `#F9FAFB` bg, top border, flex gap `8px`, wrap
- **Edit** (pencil), **No show** (alert circle), **Cancel** (red, X icon, `1.5px` red border `#FCA5A5`)

## Interactions & Behavior

### Action track buttons
- Tap "On my way" → POST status `en_route`, send "On my way" SMS to customer using their preferred channel, advance step to 1, button flips to "done" state with timestamp
- Tap "Job started" → POST status `on_site`, advance step to 2 (disabled until step ≥ 1)
- Tap "Job complete" → POST status `complete`, advance step to 3 (disabled until step ≥ 2). On completion, surface a toast with **Send Review Request** as a follow-up action.

### Secondary action row
- "See attached photos" / "See attached notes" — these are **mutually exclusive** inline accordions. Opening one closes the other.
- Chevron rotates: `down` (closed) → `up` (open). The button itself adopts the accent tint when open.
- The count badge reflects the number of items currently attached. Re-fetch on open if stale.
- "Send Review Request" — sends a templated SMS/email with the review link. Show a confirmation toast.
- "Edit tags" — opens the `CKTagEditor` bottom sheet (defined in `combined-modal.jsx`). Tags persist on the **customer profile**, not the appointment — they propagate to past and future jobs.

### Photos panel
- **Upload photo · camera roll**: native picker. Multiple-select allowed. Show progress per file; optimistically prepend thumbnails to the strip; revert on error.
- **Take photo**: capture `environment` camera, single shot.
- **Tap a thumbnail**: open lightbox (full-screen, pinch-to-zoom). Out of scope for v2 — wire to existing lightbox if present.
- **View all (N)**: navigate to a customer-photos index for this customer (across all their jobs).
- **Add more**: same as Upload photo.

### Internal notes panel
- **Edit**: swap to edit mode, focus the textarea, place cursor at end. ESC = Cancel. ⌘+Enter / Ctrl+Enter = Save Notes.
- **Save Notes**: PATCH `body` to the appointment's notes record. Optimistic. On success, exit edit mode and show subtle success indicator (toast or briefly tint the eyebrow).
- **Cancel**: discard local changes, exit edit mode.
- Saving updates `updatedAt` and `updatedBy` to the current user — the UI does not show these timestamps, but they should be sent to the backend for audit.

### Get directions popover
- Tap "Get directions" → toggle popover above the button.
- Tap **Apple Maps** → open `maps://?daddr=<encoded address>` (iOS) or `https://maps.apple.com/?daddr=...` (web fallback).
- Tap **Google Maps** → open `comgooglemaps://?daddr=...` if app installed, else `https://www.google.com/maps/dir/?api=1&destination=...`.
- "Remember my choice" toggles a per-user preference; subsequent taps skip the popover.

### Footer
- **Edit** → opens an appointment edit form (existing flow).
- **No show** → status `no_show`, prompt for reason.
- **Cancel** → confirm dialog, then status `cancelled`.

### Modal close
- Top-right X button, ESC key, or backdrop click closes the modal.

## State Management

```ts
type AppointmentModalState = {
  appointment: Appointment;       // server-fetched
  step: 0 | 1 | 2 | 3;             // booked → en route → on site → done
  openPanel: 'photos' | 'notes' | null;
  editingNotes: boolean;
  showMapsPopover: boolean;
  showTagsEditMode: boolean;       // controls the CKTagEditor bottom sheet
};
```

State transitions:
- `openPanel` is mutually-exclusive — opening photos closes notes, and vice versa.
- `editingNotes` resets to `false` whenever `openPanel !== 'notes'`.
- `showMapsPopover` should auto-dismiss on outside click and on selecting an option.

Data fetching:
- On modal open: `GET /appointments/:id` (full appointment), `GET /customers/:customerId/photos` (photos across all their jobs), `GET /appointments/:id/notes`.
- On notes save: `PATCH /appointments/:id/notes { body }`.
- On photo upload: `POST /customers/:customerId/photos` (multipart). Attach `appointmentId` so the photo is tagged to this job.
- On status change: `PATCH /appointments/:id/status { status }`.

## Design Tokens

### Colors

#### Ink / neutral
| Token | Hex | Usage |
|---|---|---|
| `ink` | `#0B1220` | Primary text, ink button bg |
| `ink2` | `#1F2937` | Secondary text, button labels |
| `ink3` | `#4B5563` | Tertiary text, subtitles |
| `ink4` | `#6B7280` | Muted text, eyebrow |
| `slate` | `#64748B` | Internal Notes eyebrow + Edit affordance |
| `line` | `#E5E7EB` | Default border |
| `line2` | `#F3F4F6` | Pill bg, soft divider |
| `surf` | `#FFFFFF` | Card / modal bg |
| `soft` | `#F9FAFB` | Section background tint |

#### Accents
| Token | Hex (color) | Hex (bg tint) |
|---|---|---|
| Blue | `#1D4ED8` | `#DBEAFE` |
| Orange | `#C2410C` | `#FFEDD5` |
| Green | `#047857` | `#D1FAE5` |
| Teal | `#0F766E` | `#CCFBF1` |
| Teal-primary (Save Notes) | `#14B8A6` | — |
| Red | `#B91C1C` | — (border `#FCA5A5`) |
| Amber | `#B45309` | `#FEF3C7` |
| Violet | `#6D28D9` | `#EDE9FE` |

V2LinkBtn `accent` map (when open): `{accent}Bg` for background, `{accent}` for color and border.

### Typography
- **UI font**: `"Inter", -apple-system, system-ui, sans-serif`. Weights used: 400, 500, 600, 700, 800.
- **Mono font**: `"JetBrains Mono", ui-monospace, "SF Mono", Menlo, monospace`. Weights: 500, 600, 700. Used for: phone number, dates, count chips, "· camera roll" suffix, action-track timestamps.
- **Scale used in this design**:
  - Modal title: `26px / 800 / -0.8`
  - Section eyebrow: `11.5–12.5px / 800 / +0.8 to +1.4px tracking / uppercase`
  - Card title (Property, Scope): `17–19px / 800 / -0.3`
  - Body / list text: `14–15px / 600`
  - Internal Notes body: `14.5px / 500 / 1.6 line-height`
  - Buttons (large): `15–16px / 800`
  - Buttons (small): `13–14px / 700–800`
  - Pill / chip: `11.5–13px / 700–800`

### Spacing
- Card padding: `14px 16px` (rows), `18px 20px 14px` (Internal Notes header), `20px 20px 16px` (modal header)
- Section gaps: `10px` between expansion panel and trigger, `16px` between cards
- Button gaps: `8px` (secondary row), `10px` (primary stack)

### Radii
- `8px` — small buttons (View all, role pills)
- `10px` — table-row icon discs
- `12px` — most buttons, tag chips, photo cards, textarea
- `14px` — large buttons, big cards
- `18px` — modal outer
- `999px` — pill-shaped Cancel / Save Notes buttons

### Shadows
- Modal: `0 30px 60px rgba(10,15,30,0.12), 0 4px 12px rgba(10,15,30,0.05)`
- Internal Notes card: `0 1px 2px rgba(10,15,30,0.04)`
- Action-track buttons (default): `0 1px 0 rgba(0,0,0,0.1), 0 4px 8px rgba(0,0,0,0.06)`
- Maps popover: `0 20px 40px rgba(10,15,30,0.18), 0 4px 8px rgba(10,15,30,0.08)`

### Borders
- All standard borders are `1.5px` (sometimes `2px` for action buttons and secondary CTAs). The visual rhythm depends on this — do not collapse to `1px`.

## Assets

- **Icons**: All SVG, hand-rolled in `combined-modal.jsx` under the `CI` constant. They are simple 24×24 stroke icons (`stroke-width: 2`, round caps + joins). The two new v2 icons (`CI_camRoll`, `CI_upload`) are defined in `combined-modal-v2.jsx`. In the target codebase, **substitute these for the existing icon library** — Lucide / Phosphor / Heroicons all have direct equivalents. Mapping:
  - `phone` → phone
  - `mail` → mail / envelope
  - `pin` → map-pin
  - `nav` → navigation / send
  - `play` → play
  - `check` → check
  - `checkC` → check-circle-2
  - `star` → star
  - `card` → credit-card
  - `box` → package / box
  - `doc` → file-text
  - `pencil` → pencil / edit-2 / edit-3
  - `x` → x
  - `alert` → alert-circle
  - `tools` → wrench / tool
  - `photo` → image
  - `user` → user
  - `tag` → tag
  - `plus` → plus
  - `ext` → external-link
  - `CI_camRoll` → camera
  - `CI_upload` → upload / arrow-up-tray

- **Photos**: The HTML uses striped SVG placeholders. **Replace with real `<img>` tags** sourced from the customer-photos endpoint.

- **Avatar**: Initials-based (e.g. "TU" for Test User). Upgrade to real avatar URL if available; fall back to initials.

## Implementation Notes / Watch-outs

1. **Mutual-exclusivity of the two inline panels** — opening one MUST close the other. The current prototype is rendered statically (driven by props); in production, drive both from a single `openPanel` state.
2. **Mobile viewport** — the modal is `560px` wide on the design canvas, but in production it should go full-width on phones (≤ 640px). All buttons inside are sized for `min-height: 44px` to be tappable.
3. **Internal Notes is the source of truth** — do not migrate v1's multi-author thread. If the codebase still has thread-style note records, write a migration that concatenates them into a single body, dated header per author optional. Future writes are flat-text into `body`.
4. **Photo upload accepts multiple files** — `<input multiple>`. Show per-file progress.
5. **Camera capture on web** — `accept="image/*" capture="environment"` works on iOS Safari and Android Chrome. On desktop browsers, this falls back to the file picker, which is fine.
6. **The `design-canvas.jsx` file is prototyping scaffolding only** — it provides `<DesignCanvas>`, `<DCSection>`, `<DCArtboard>`, `<DCPostIt>` for laying out variants side-by-side in the HTML preview. Do **not** ship any of it.
7. **Tag persistence**: tags edited via the `CKTagEditor` save to the **customer**, not the appointment. Future appointments for the same customer auto-inherit the current tag set.
8. **Maps deep links** — see `Get directions popover` interaction notes for URL schemes per platform.
9. **Status timestamps** — the timeline strip and action-track sub-labels both display times. These are server-authoritative — render as `format(localTime, 'h:mm A')` from the API response, not client-clock.

## Acceptance Criteria

- [ ] Tapping "See attached photos" expands the photos panel inline; chevron flips up; closes the notes panel if open.
- [ ] Photos panel shows a primary blue **Upload photo · camera roll** button that opens the device photo library.
- [ ] Photos panel shows a secondary outlined **Take photo** button that opens the camera.
- [ ] Photos strip scrolls horizontally with momentum on touch.
- [ ] Tapping "See attached notes" expands the centralized Internal Notes card.
- [ ] In view mode, the notes card shows the "INTERNAL NOTES" eyebrow and a top-right Edit affordance.
- [ ] Tapping Edit swaps to a textarea, with **Cancel** (white) and **Save Notes** (teal `#14B8A6`) buttons bottom-right.
- [ ] Saving PATCHes the body to the server and returns the panel to view mode.
- [ ] The "Review" button now reads "Send Review Request".
- [ ] All buttons inside the modal are at least 44px tall.
- [ ] The modal closes via the X button, ESC, and backdrop click.
- [ ] Tag edits saved via "Edit tags" persist on the customer and show on past and future jobs.
