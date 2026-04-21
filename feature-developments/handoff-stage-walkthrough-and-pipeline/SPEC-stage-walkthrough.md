# SPEC — Stage Walkthrough

**Route:** `/sales/:id` (extends current `SalesDetail.tsx`)
**Files touched:**
- `frontend/src/features/sales/components/SalesDetail.tsx` (modified — insert new blocks)
- `frontend/src/features/sales/components/StageStepper.tsx` (new)
- `frontend/src/features/sales/components/NowCard.tsx` (new)
- `frontend/src/features/sales/components/ActivityStrip.tsx` (new)
- `frontend/src/features/sales/components/AutoNudgeSchedule.tsx` (new)

**Visual ground truth:** `reference/Sales-Reference.html` → tab "③ Stage walkthrough" · screenshots `03-walk-*.png`

---

## 1. Intent

One component, seven variations — **same stepper, same Now card shell**, different content / blocker / primary action per stage. This is the contract with the user:

> The Now card is always the truth about what to do next. If the primary button is disabled, the banner underneath tells you exactly why and how to unblock it.

The existing `SalesDetail` page has a header card and a wall of action buttons. The redesign replaces the button wall with a **stepper → Now card → activity strip** stack that makes the current stage and the next action obvious at a glance.

---

## 2. Overall layout inside `SalesDetail.tsx`

```
┌ Back to Pipeline                                          ┐
│                                                           │
│ ┌── Header card (unchanged) ─────────────────────────┐    │
│ │  Viktor Petrov · phone · address          [Pill]  │    │
│ │  Job type · last contact · notes · closed reason   │    │
│ └────────────────────────────────────────────────────┘    │
│                                                           │
│ ┌── Stepper wrap ────────────────────────────────────┐    │
│ │  Plan         Sign              Close              │    │
│ │  ①───②───③───④───⑤                                  │    │  ← StageStepper
│ │  ⋯ change stage manually        ✕ Mark Lost        │    │
│ └────────────────────────────────────────────────────┘    │
│                                                           │
│ ┌── Now card ────────────────────────────────────────┐    │
│ │  [Your move]                                       │    │
│ │  Title — the one-sentence what-to-do-next          │    │
│ │  Body copy · inline <em> for highlights            │    │
│ │  [dropzone / nudge block / week picker — optional] │    │  ← NowCard
│ │  [Primary]  [Secondary]  [Ghost]                   │    │
│ │  🔒 Lock banner (if any)                           │    │
│ └────────────────────────────────────────────────────┘    │
│                                                           │
│ ┌── Activity strip ──────────────────────────────────┐    │
│ │  🆕 Moved from Leads 6d ago · ⏳ Call Viktor to…   │    │  ← ActivityStrip
│ └────────────────────────────────────────────────────┘    │
│                                                           │
│ ┌── Documents section (existing) ────────────────────┐    │
│ │  …                                                 │    │
│ └────────────────────────────────────────────────────┘    │
└───────────────────────────────────────────────────────────┘
```

**The existing `StatusActionButton` moves inside `NowCard` as the primary action** — do not keep it in the header card.

**Closed-lost special case:** when `status === 'closed_lost'`, hide the stepper + Now card + activity strip entirely; show a single slate banner reading *"Closed Lost — {closed_reason}. No further actions."* above the Documents section.

---

## 3. `StageStepper` component

### Props

```ts
interface StageStepperProps {
  currentStage: StageKey;              // from statusToStageKey(entry.status)
  /** Fires when a user clicks the "⋯ change stage manually" affordance. */
  onOverrideClick: () => void;
  /** Fires when the user clicks "✕ Mark Lost". */
  onMarkLost: () => void;
  /** True while entry.status === 'estimate_scheduled' — renders step 1 with a calendar badge. */
  visitScheduled?: boolean;
}
```

### Render

**Row 1 — phase labels.** Three equally-spaced spans:

```
   Plan            Sign                Close
```

Phase-to-steps mapping: Plan = [step 1], Sign = [step 2, step 3], Close = [step 4, step 5].

**Row 2 — 5-step horizontal stepper.** Each step is a circle + label, connected by a 2px line. Rendered from `STAGES` (see `data-shapes.ts`).

Step visual states:

| State | Condition | Dot | Label | Line to next |
|---|---|---|---|---|
| `done`    | `index < currentStage.index` | filled emerald, shows `✓` | emerald | emerald solid |
| `active`  | `index === currentStage.index` | filled slate-900, shows `{index+1}` | slate-900 bold | slate-200 solid |
| `waiting` | active **AND** `stage === 'pending_approval'` | **dashed** amber border, slow 2.5s pulse, shows `3` | amber | slate-200 solid |
| `future`  | `index > currentStage.index` | outlined slate-300 | slate-400 | slate-200 dashed |

When `visitScheduled` is true and `currentStage === 'schedule_estimate'`, render a small `📅 Apr 19 2pm` badge below step 1's label.

The `waiting` state is the single visual cue that progress is blocked on the customer, not on us. Do not reuse it for other stages.

**Row 3 — footer.** Two tiny buttons on opposite ends:

- Left: `⋯ change stage manually` → `onOverrideClick`. Opens an existing Radix `<DropdownMenu>` with all statuses from `ALL_STATUSES`. Selecting one sets `override_flag = true`.
- Right: `✕ Mark Lost` → `onMarkLost`. Opens a small modal to collect `closed_reason` (freeform textarea, required), then transitions status to `closed_lost`.

### Test IDs

- Root: `stage-stepper`
- Each step: `stage-step-{key}` with `data-state="done|active|waiting|future"`
- Override: `stage-stepper-override`
- Mark lost: `stage-stepper-mark-lost`

### Styling tokens

- Step circle: `w-7 h-7 rounded-full flex items-center justify-center text-xs font-semibold`
- Connector: 2px, fills the gap between two circles, sits vertically-centered with the circles.
- Phase headings: `text-[11px] uppercase tracking-[0.08em] text-slate-400`

---

## 4. `NowCard` component

### Props

```ts
interface NowCardProps {
  content: NowCardContent;             // from nowContent(inputs) — pure lookup
  /** Maps NowActionId → mutation callback. Host wires these up. */
  onAction: (id: NowActionId) => void;
  /** Controlled state for dropzone. */
  onFileDrop?: (file: File, kind: 'estimate' | 'agreement') => void;
  /** Controlled state for Week-Of picker (only when showWeekOfPicker). */
  weekOfValue?: string | null;
  onWeekOfChange?: (weekOf: string) => void;
}
```

`NowCard` is **pure** — it never calls a mutation. The parent binds `onAction` to the real hooks. This keeps `nowContent(inputs)` fully testable without mocking.

### Shell

- Card: `bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-4`.
- Left border accent: `border-l-4 border-l-{pill.tone-colour}` — subtle but lets the card's "mood" register peripherally.

### Pill

Single small pill at top-left. Colours:

| tone | bg | text | accent border colour |
|---|---|---|---|
| `you`  | `bg-sky-100`     | `text-sky-700`     | `border-l-sky-400`     |
| `cust` | `bg-amber-100`   | `text-amber-700`   | `border-l-amber-400`   |
| `done` | `bg-emerald-100` | `text-emerald-700` | `border-l-emerald-400` |

### Title + copy

- Title: `text-lg font-semibold text-slate-900 text-wrap:pretty`.
- Copy: `text-sm text-slate-600 leading-relaxed`, rendered via `dangerouslySetInnerHTML` ONLY for `<em>` and `<b>` tags. Sanitise with a tiny allowlist helper (included in `scaffold/NowCard.tsx`).

### Optional blocks (rendered in this order when present)

1. **Dropzone** (`content.dropzone`) — see §4.5.
2. **AutoNudgeSchedule** (`content.showNudgeSchedule`) — see §5.
3. **Week-Of picker** (`content.showWeekOfPicker`) — see §4.6.

### Action row

Rendered as a wrapping flex row, `gap-2`. Button kinds map to shadcn variants:

| `NowAction.kind` | shadcn variant | Notes |
|---|---|---|
| `primary` | default | leading icon if provided |
| `outline` | outline | |
| `ghost`   | ghost   | |
| `danger`  | outline + `text-red-600 border-red-300 hover:bg-red-50` | |
| `locked`  | outline + `disabled` | shows 🔒 lock icon, tooltip = `reason` |

### Lock banner

When `content.lockBanner` is set, render below the action row:

```
┌──────────────────────────────────────────────────────┐
│ 🔒  No estimate PDF yet. Drag-and-drop a PDF above, │
│     or click to browse.                              │
└──────────────────────────────────────────────────────┘
```

- `bg-red-50 border border-red-200 text-red-700 rounded-md px-3 py-2 text-sm`.
- `textHtml` is sanitised allowlist HTML.

### 4.5 Dropzone sub-component

Two visual states.

**Empty:**
```
┌─────────────────────────────────────────┐
│               ↓                         │
│      Drag the estimate PDF here         │
│      or click to browse · PDF only      │
└─────────────────────────────────────────┘
```
- Dashed `2px border-dashed border-slate-300`, `rounded-lg`, `py-8 text-center`.
- Hover: `border-sky-400 bg-sky-50`.
- While dragging a file over: `border-sky-500 bg-sky-100`.

**Filled:**
```
┌─────────────────────────────────────────┐
│  📄  estimate_viktor_v2.pdf            │
│      212 KB · click to preview ·       │
│      replace · remove                   │
└─────────────────────────────────────────┘
```
- Solid `1px border-slate-200`, `rounded-lg`, `p-3`, `bg-white`.
- Click filename → opens `<FilePreviewModal>` (existing in repo).
- `replace` / `remove` — underlined links inline.

Accepts `application/pdf` only. Reject anything else with a sonner toast `"PDF only."`.

### 4.6 Week-Of picker

Renders only for the `send_contract` (a.k.a. "Convert to Job") stage.

```
📅 Rough Week Of for this job
[ Week of Apr 20 ] [ Week of Apr 27* ] [ Week of May 4 ] [ + pick date… ]
Used only as a target — pin the exact day + crew later in the Jobs tab.
```

- 5 chips: current week + next 4 weeks (computed from today with `date-fns`' `startOfWeek` Monday anchor).
- Additional "+ pick date…" chip opens a shadcn `<Popover>` with a `<Calendar>` (Radix). Selecting a date adds it as a 6th chip.
- Selected chip: `bg-slate-900 text-white`. Unselected: `bg-white border border-slate-200 text-slate-700 hover:bg-slate-50`.
- Persist the chosen week to the entry as `target_week_of` (new field — backend TODO; for v1 store in `localStorage` keyed by `entryId`).

### NowCard · test IDs

| Element | testid |
|---|---|
| Root | `now-card` (with `data-stage="{stageKey}"` attribute) |
| Pill | `now-card-pill` (with `data-tone="you|cust|done"`) |
| Title | `now-card-title` |
| Each action | value of `NowAction.testId` — passed through from content |
| Lock banner | `now-card-lock-banner` |
| Dropzone (empty) | `now-card-dropzone-empty` |
| Dropzone (filled) | `now-card-dropzone-filled` |
| Week-Of chip | `now-card-weekof-{value}` |
| Manual date popover trigger | `now-card-weekof-pick` |

---

## 5. `AutoNudgeSchedule` component

Rendered inside `NowCard` when `stage === 'pending_approval'`. Shows the fixed follow-up cadence the automation system runs.

### Props

```ts
interface AutoNudgeScheduleProps {
  /** ISO timestamp when the estimate was sent (stage entered). */
  estimateSentAt: string;
  /** Whether auto-nudges are currently paused (controls the ⏸ icon). */
  paused?: boolean;
}
```

### Render

```
⏰  Auto follow-up schedule · SMS + email
✓  Day 0 · Apr 11 · Initial estimate sent
⏰ Day 2 · Tomorrow 9 AM · "Did you receive the estimate? Any questions?"
·  Day 5 · Apr 16 9 AM · "Just checking in on the estimate"
·  Day 8 · Apr 19 9 AM · "Following up one more time"
🔁 Then every Monday · 9 AM · "Reply A to approve, R to reject" — one-letter reply auto-updates the pipeline
```

### Row state logic (computed from `estimateSentAt`)

```ts
const now = Date.now();
const sent = new Date(estimateSentAt).getTime();
const dayNum = Math.floor((now - sent) / 86_400_000);

for each NUDGE_CADENCE_DAYS offset:
  if offset <  dayNum → state = 'done'
  else if offset === next-upcoming → state = 'next'
  else                             → state = 'future'
loop row has state = 'loop' always
```

Only one row is `state === 'next'` at a time.

### Styles

- Container: `bg-slate-50 border border-slate-200 rounded-lg p-3 text-sm space-y-1`
- Header row: `text-slate-900 font-semibold`, subtitle `text-slate-500 font-normal ml-1`
- `done` row: `text-emerald-700`, leading `✓`
- `next` row: `text-amber-700 bg-amber-50 -mx-3 px-3 py-1 font-semibold` (full-bleed highlight strip), leading `⏰`
- `future` row: `text-slate-500`, leading `·`
- `loop` row: `text-slate-700 italic`, leading `🔁`, top border `pt-2 mt-1 border-t border-slate-200`
- If `paused`: strike-through all future/loop rows, show a banner at the top: *"⏸ Paused. Resume to continue auto-follow-up."*

### Test IDs

- Root: `auto-nudge-schedule`
- Each row: `auto-nudge-row-{dayOffset}` with `data-state="done|next|future|loop"`
- Paused banner: `auto-nudge-paused-banner`

---

## 6. `ActivityStrip` component

One-line horizontal strip showing the 2–4 most recent events for the current stage.

### Props

```ts
interface ActivityStripProps {
  events: ActivityEvent[];      // already ordered, already filtered to current stage
}
```

### Render

```
🆕 Moved from Leads 6d ago · ⏳ Call Viktor to agree on a date
📅 Visit Apr 19 ✓ · ⏳ Build & upload estimate
✉ Emailed Viktor Apr 11, 3:42 PM · 👁 Viewed Apr 12, 9:15 AM · ⏰ Next auto-nudge tomorrow 9 AM
✅ Client approved Apr 13, 2:04 PM · ⏳ Send agreement + pick Week Of
🛠 Converted Apr 14 · 📄 Job #4821 created · 👤 Customer record created
```

- `text-sm text-slate-600`, `flex flex-wrap items-center gap-x-2 gap-y-1`.
- Separator between events: `·` in `text-slate-300`.
- `tone = 'done'`: `text-slate-600`
- `tone = 'wait'`: `text-amber-700 font-medium`
- `tone = 'neutral'`: `text-slate-500`

### Event → label mapping

| `kind` | Leading glyph | Label template |
|---|---|---|
| `moved_from_leads` | 🆕 | `Moved from Leads {relative}` |
| `visit_scheduled` | 📅 | `Visit {date}, {time}` |
| `visit_completed` | 📅 | `Visit {date} ✓` |
| `estimate_sent` | ✉ | `Emailed customer {date}, {time}` |
| `estimate_viewed` | 👁 | `Viewed {date}, {time}` |
| `nudge_sent` | ⏰ | `Nudge sent {relative}` |
| `nudge_next` | ⏰ | `Next auto-nudge {relative}` (tone = `wait`) |
| `approved` | ✅ | `Client approved {date}, {time}` |
| `declined` | ✕ | `Client declined {date}, {time}` |
| `agreement_uploaded` | 📄 | `Signed agreement uploaded {relative}` |
| `converted` | 🛠 | `Converted {date}` |
| `job_created` | 📄 | `Job #{jobId} created` |
| `customer_created` | 👤 | `Customer record created` |

Use `formatDistanceToNow` for `{relative}`, `format(d, 'MMM d, h:mm a')` for `{date}, {time}`.

### Test IDs

- Root: `activity-strip`
- Event: `activity-event-{kind}`

---

## 7. Per-stage content — source of truth

The content of the Now card is a pure function of `(stage, hasEstimateDoc, hasSignedAgreement, hasCustomerEmail, weekOf)`. Ship it as a table in `scaffold/nowContent.ts`.

### 7.1 `schedule_estimate`

| field | value |
|---|---|
| pill | `{tone:'you', label:'Your move'}` |
| title | `Call {firstName} — agree on a date, then drop them on the schedule.` |
| copy | `"Schedule visit" opens the calendar with {firstName}'s info pre-filled from the lead record. Once booked, "Text appointment confirmation" sends a confirm with an <em>R-to-reschedule</em> reply option.` |
| dropzone | none |
| showNudgeSchedule | false |
| showWeekOfPicker | false |
| actions | `[primary:Schedule visit → schedule_visit]`, `[outline:Text appointment confirmation → text_confirmation]` |
| lockBanner | none |

### 7.2 `send_estimate` — empty (no doc uploaded)

| field | value |
|---|---|
| pill | `{tone:'you', label:'Your move'}` |
| title | `Drop the estimate PDF below, then send.` |
| copy | `Build the estimate in Google Sheets, save as PDF, drag it into the box below. "Upload & send" emails {firstName} the PDF with an Approve button and auto-advances this entry to <em>Pending Approval</em>.` |
| dropzone | `{kind:'estimate', filled:false}` |
| actions | `[locked:Upload & send estimate, reason:"upload a PDF above"]`, `[ghost:Skip — advance manually → skip_advance]` |
| lockBanner | `{textHtml:"<b>No estimate PDF yet.</b> Drag-and-drop a PDF into the box above, or click to browse."}` |

### 7.3 `send_estimate` — ready (doc uploaded)

| field | value |
|---|---|
| pill | `{tone:'you', label:'Your move'}` |
| title | `{docName} is ready — send it.` |
| copy | `Click the PDF below to review it. Hit "Upload & send" to email {firstName} the estimate with an Approve button; they'll also get an SMS with the PDF link.` |
| dropzone | `{kind:'estimate', filled:true}` |
| actions (hasCustomerEmail) | `[primary:Upload & send estimate → send_estimate_email]`, `[ghost:Skip — advance manually → skip_advance]` |
| actions (!hasCustomerEmail) | `[locked:Upload & send estimate, reason:"no email on file — add one to send"]`, `[primary:Add customer email → add_customer_email]` |

### 7.4 `pending_approval`

| field | value |
|---|---|
| pill | `{tone:'cust', label:'Waiting on customer'}` |
| title | `Waiting on {firstName} to approve or decline.` |
| copy | `Sent {sentDate}. Auto follow-up runs on day 2, 5, 8 — then every Monday it sends a one-tap SMS: <em>"Reply A to approve, R to reject"</em>. Matching replies update the pipeline automatically.` |
| showNudgeSchedule | **true** |
| actions | `[primary:Client approved (manual) → mark_approved_manual]`, `[outline:Resend estimate → resend_estimate]`, `[outline:Pause auto-follow-up → pause_nudges]`, `[danger:Client declined → mark_declined]` |

### 7.5 `send_contract` (displayed as "Convert to Job") — no agreement

| field | value |
|---|---|
| pill | `{tone:'you', label:'Your move'}` |
| title | `{firstName} approved — upload the signed agreement, then convert.` |
| copy | `{firstName} already signed via SignWell; drop the <em>counter-signed PDF</em> below for our records. Pick a <em>rough Week Of</em> target, then "Convert to Job" opens a quick prompt for job type & details — once confirmed, this lead closes and a real Job + Customer record are created.` |
| dropzone | `{kind:'agreement', filled:false}` |
| showWeekOfPicker | **true** |
| actions | `[locked:Convert to Job, reason:"upload signed agreement first"]` |

### 7.6 `send_contract` — agreement uploaded

Same as 7.5 **except**:
- dropzone `filled: true`
- actions `[primary:Convert to Job → convert_to_job]`

### 7.7 `closed_won`

| field | value |
|---|---|
| pill | `{tone:'done', label:'Complete'}` |
| title | `Job #{jobId} created — targeted for {weekOf}.` |
| copy | `{firstName} is now a <em>Customer</em>; this entry has moved out of the Sales tab. The job sits in <em>Jobs</em> with status <em>To Be Scheduled</em> — pin a day and crew on the calendar when you're ready.` |
| actions | `[primary:View Job #{jobId} → view_job]`, `[outline:View Customer profile → view_customer]`, `[outline:Jump to Schedule → jump_to_schedule]` |

---

## 8. Click-handler wiring (host `SalesDetail.tsx`)

```ts
const handleNowAction = (id: NowActionId) => {
  switch (id) {
    case 'schedule_visit':        openScheduleModal();                 break;
    case 'text_confirmation':     sendConfirmationSMS.mutate(entry.id); break;
    case 'upload_estimate':       /* triggered by dropzone, not a button */ break;
    case 'send_estimate_email':   sendEstimate.mutate(entry.id);       break;
    case 'add_customer_email':    navigate(`/customers/${entry.customer_id}/edit`); break;
    case 'skip_advance':          advanceStatus.mutate({id: entry.id, to: 'pending_approval'}); break;
    case 'mark_approved_manual':  advanceStatus.mutate({id: entry.id, to: 'send_contract'}); break;
    case 'resend_estimate':       resendEstimate.mutate(entry.id);     break;
    case 'pause_nudges':          pauseNudges.mutate(entry.id);        break;
    case 'mark_declined':         openDeclineModal();                  break;
    case 'upload_agreement':      /* triggered by dropzone */          break;
    case 'convert_to_job':        openConvertModal();                  break;
    case 'view_job':              navigate(`/jobs/${entry.job_id}`);   break;
    case 'view_customer':         navigate(`/customers/${entry.customer_id}`); break;
    case 'jump_to_schedule':      navigate('/schedule');               break;
  }
};
```

Mutations with a `TODO(backend)` comment where the endpoint doesn't exist yet:
- `sendConfirmationSMS`, `resendEstimate`, `pauseNudges`. Stub them as no-ops that show a sonner toast `"Not wired yet — TODO"`.

---

## 9. Done when

- [ ] `StageStepper` renders all 7 wireframe variations identically (screenshots `03-walk-01..07.png`).
- [ ] `pending_approval` step shows the dashed amber waiting state; no other stage does.
- [ ] `NowCard` is a pure function of its props; covered by a unit test that snapshots `nowContent(inputs)` for all 7 variations.
- [ ] Empty-vs-filled dropzone switches correctly when a PDF is dropped, and rejects non-PDFs.
- [ ] `AutoNudgeSchedule` correctly marks exactly one row as `next` and everything before it as `done` given a mock `estimateSentAt`.
- [ ] `ActivityStrip` renders for every stage with its expected events.
- [ ] `closed_lost` hides stepper + now card + activity, shows the slate banner instead.
- [ ] The existing `StatusActionButton` is removed from the header card — it lives only inside `NowCard` as the primary action now.
- [ ] All `data-testid`s present; existing detail-page tests still pass.
- [ ] No TypeScript errors; no new runtime deps.
