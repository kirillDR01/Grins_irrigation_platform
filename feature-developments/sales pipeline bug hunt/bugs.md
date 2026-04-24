# Bugs — Sales Pipeline Walkthrough

All bugs confirmed via live browser test + code review on branch `dev`, against
commit `8693b6d` (as of 2026-04-23).

---

## Bug #1 — `Skip — advance manually` always fails (Critical, user-reported)

### Symptom
Clicking the **Skip — advance manually** button in the `send_estimate` NowCard flashes
a toast "❌ Failed to advance" and the status does NOT change.

Reproduced live on two entries:
- Testing Viktor (`e5690e69-…`) — screenshot `02-after-skip-click.png`, `08-skip-advance-on-send-estimate.png`
- Brooke Jore (`5607f5ca-…`) after progressing her to `send_estimate` — same toast

### Root cause
`SalesDetail.tsx:187-192` wires `skip_advance` to `advance.mutate(entryId)`:

```tsx
case 'skip_advance':
  advance.mutate(entryId, {
    onSuccess: () => { toast.success('Status advanced'); refetch(); },
    onError: () => toast.error('Failed to advance'),
  });
  break;
```

The `/sales-pipeline/{id}/advance` endpoint runs `advance_status()` in
`src/grins_platform/services/sales_pipeline_service.py:115-164`, which has this guard
(added by bughunt M-10):

```python
if (
    target == SalesEntryStatus.PENDING_APPROVAL
    and not entry.signwell_document_id
):
    raise MissingSigningDocumentError(entry_id)
```

So advancing `send_estimate → pending_approval` is rejected server-side whenever the
user doesn't have an estimate PDF on file — which is **exactly the situation the
"Skip — advance manually" button is intended to solve**. Frontend and backend have
opposing intents.

### Fix
Replace `advance.mutate` with `overrideStatus.mutateAsync` for the skip path, so the
user bypasses the state-machine guard instead of triggering it:

```tsx
case 'skip_advance':
  overrideStatus.mutateAsync({
    id: entryId,
    body: { status: 'pending_approval' },
  })
    .then(() => { toast.success('Advanced to Pending Approval'); refetch(); })
    .catch(() => toast.error('Failed to advance'));
  break;
```

This matches the user intent ("Skip means skip the guard") and the design decision that
manual overrides are explicitly allowed to bypass document gates.

**Files**
- `frontend/src/features/sales/components/SalesDetail.tsx:187-192`

---

## Bug #2 — `Schedule visit` doesn't open a schedule modal (Critical, spec violation)

### Symptom
Clicking **Schedule visit** in the Plan-stage NowCard just flips the entry status
(`schedule_estimate` → `estimate_scheduled`). No calendar picker opens, no way to pick a
date/time.

Reproduced on Brooke Jore: screenshot `05-plan-stage-brooke.png` → click →
`06-after-schedule-visit.png` shows the status change only.

### Root cause
`SalesDetail.tsx:141-146` wires `schedule_visit` to `advance.mutate` — the same call
used by `skip_advance`:

```tsx
case 'schedule_visit':
  advance.mutate(entryId, {
    onSuccess: () => { toast.success('Estimate scheduled'); refetch(); },
    onError: () => toast.error('Failed to schedule'),
  });
  break;
```

### Expected (from Req 15.1 and spec §"NowCard Content Contract")
> WHEN the `schedule_visit` action is triggered, THE SalesDetail host SHALL open the
> schedule modal.

The NowCard body copy even says:
> "Schedule visit" opens the calendar with Brooke's info pre-filled from the lead
> record.

But no such modal exists.

### Fix
Introduce a schedule modal (likely reusing `SalesCalendar` logic or a
`ScheduleVisitModal` component with a `Calendar` + crew picker) and replace the advance
call with an `openScheduleModal()` state toggle.

**Files**
- `frontend/src/features/sales/components/SalesDetail.tsx:141-146`
- New: `frontend/src/features/sales/components/ScheduleVisitModal.tsx` (to be created)

---

## Bug #3 — Pipeline-list row action buttons have no `onClick` (High)

### Symptom
The "Schedule", "Send", "Nudge", "Convert", "View job", and "✕" dismiss buttons on each
row of `/sales` do **nothing** when clicked. Clicking a button has no visual effect
(no navigation, no toast, no state change). Clicking the rest of the row does navigate
correctly to `/sales/{id}`.

Reproduced by clicking the "Schedule" button on Brooke Jore's row (screenshot
`04-schedule-btn-click.png`) — URL unchanged.

### Root cause
`SalesPipeline.tsx:306-326` renders the buttons inside a `<TableCell>` that
`stopPropagation`s, preventing row-click navigation from firing as a fallback, but the
buttons themselves never received an `onClick`:

```tsx
<TableCell className="px-6 py-4" onClick={e => e.stopPropagation()}>
  <div className="flex items-center gap-1">
    {actionLabel && (
      <Button
        size="sm"
        variant={entry.status === 'closed_won' ? 'ghost' : 'default'}
        data-testid={`pipeline-row-action-${entry.id}`}
        // TODO(wiring): route to real mutation / modal opener
      >
        {actionLabel}
      </Button>
    )}
    <Button
      size="icon"
      variant="ghost"
      className="h-7 w-7"
      data-testid={`pipeline-row-dismiss-${entry.id}`}
      // TODO(backend): wire dismiss endpoint
    >
      <X className="h-3.5 w-3.5 text-slate-400" />
    </Button>
  </div>
</TableCell>
```

Both `// TODO(wiring)` and `// TODO(backend)` comments confirm this is incomplete.

### Fix
Two acceptable options:

**Option A** (simplest): route all action-button clicks to the detail view so the
NowCard handles the real action — remove `stopPropagation` and make the buttons
navigate same as the row:

```tsx
<TableCell className="px-6 py-4">
  <div className="flex items-center gap-1">
    {actionLabel && (
      <Button
        size="sm"
        onClick={(e) => { e.stopPropagation(); onRowClick(entry); }}
        ...
```

**Option B**: wire each label to its intended inline action (more UX but harder —
mirrors NowCard's switch).

Dismiss (✕) needs backend work per Req 17.4 (no endpoint exists), so wire it to a
sonner toast "Not wired yet — TODO" with a `TODO(backend)` comment, matching the spec
pattern.

**Files**
- `frontend/src/features/sales/components/SalesPipeline.tsx:306-328`

---

## Bug #4 — `+ pick date…` chip is a no-op (High, spec violation)

### Symptom
Clicking **+ pick date…** in the Week-Of picker does nothing — no popover, no
calendar. The chip is styled like a button but has no behaviour.

Reproduced on Brooke's `send_contract` NowCard (screenshot `12-pick-date-click.png`).

### Root cause
`NowCard.tsx:278-286` has an unwired placeholder:

```tsx
<button
  type="button"
  data-testid="now-card-weekof-pick"
  className="..."
  // TODO: open shadcn Popover + Calendar
>
  + pick date…
</button>
```

### Expected (from Req 14.2)
> THE WeekOf_Picker SHALL render an additional "+ pick date…" chip that opens a shadcn
> Popover with a Calendar for custom date selection.

### Fix
Wrap the chip in a `<Popover>` from `@/components/ui/popover` and render
`<Calendar mode="single" …/>` inside — on select, call `onChange(format(date))` and close.

**Files**
- `frontend/src/features/sales/components/NowCard.tsx:278-286`

---

## Bug #5 — `⋯ change stage manually` button is a no-op (High)

### Symptom
Clicking **⋯ change stage manually** in the StageStepper footer does nothing — no
modal, no UI change. (Users can still use the "Change stage…" combobox in the header,
but the footer button is misleading since it looks interactive.)

Reproduced on Brooke's `send_contract` view (screenshot `13-change-stage-manually-click.png`).

### Root cause
`SalesDetail.tsx:96` stores the boolean in a discarded variable:

```tsx
const [_showOverrideSelect, setShowOverrideSelect] = useState(false);
```

The leading underscore means "intentionally unused" — and sure enough, **nothing in the
component reads `_showOverrideSelect`**. The StageStepper's `onOverrideClick` callback
flips it to `true`, but no UI ever renders conditionally on it.

### Fix
Either:
1. **Delete the button** from `StageStepper` + remove the dead state (simplest; the
   header combobox covers the same use case); or
2. **Render a modal / select popover** gated on `showOverrideSelect === true` that
   mirrors the header combobox's options.

Option 1 is preferred since the header already provides the same control and having two
UI paths for one action is noise.

**Files**
- `frontend/src/features/sales/components/SalesDetail.tsx:96, 531`
- `frontend/src/features/sales/components/StageStepper.tsx` (if we keep the button, wire
  it; if we remove it, delete the corresponding prop)

---

## Bug #6 — `AutoNudgeSchedule` never renders (High, spec violation)

### Symptom
On the `pending_approval` stage, the NowCard shows the title "Waiting on Brooke to
approve or decline." but **does not render the nudge schedule** (day 0 / 2 / 5 / 8 +
weekly loop). Screenshot `09-pending-approval.png` confirms: the space between body
copy and action buttons has nothing.

### Root cause
`NowCard.tsx:86-88` gates the AutoNudgeSchedule on `estimateSentAt` being truthy:

```tsx
{content.showNudgeSchedule && estimateSentAt && (
  <AutoNudgeSchedule estimateSentAt={estimateSentAt} paused={nudgesPaused} />
)}
```

But the host (`SalesDetail.tsx:546-554`) **never passes `estimateSentAt` or
`nudgesPaused`**:

```tsx
<NowCard
  stageKey={stageKey}
  content={nowCardContent}
  onAction={handleNowAction}
  onFileDrop={handleFileDrop}
  weekOfValue={weekOfValue}
  onWeekOfChange={handleWeekOfChange}
/>
```

Task 11.4 in `tasks.md` says:
> Pass `estimateSentAt` and `nudgesPaused` to NowCard for AutoNudgeSchedule

…but the implementation left those props omitted.

### Expected (from Req 9.6, 11.1–11.6)
The AutoNudgeSchedule must render on `pending_approval` with rows for day 0, 2, 5, 8
plus a weekly loop.

### Fix
Pass a fallback timestamp for now (spec Req 17.5 already blesses the `updated_at`
fallback pattern with a `TODO(backend)` comment) plus a placeholder `nudgesPaused`:

```tsx
<NowCard
  ...
  estimateSentAt={entry.updated_at ?? entry.created_at}  // TODO(backend): use real estimate_sent_at
  nudgesPaused={false}  // TODO(backend): persist pause state
/>
```

**Files**
- `frontend/src/features/sales/components/SalesDetail.tsx:546-554`

---

## Bug #7 — `View Job` navigates to the SignWell doc id, not a job id (Medium)

### Symptom
On a `closed_won` entry, clicking **View Job** navigates to `/jobs/{signwell_document_id}`
when that id is set, otherwise falls back to `/jobs`. The SignWell document id is not a
job id, so the URL 404s in the first case. Tested: Brooke didn't have a SignWell doc,
so the fallback fired → URL `/jobs` (screenshot `17-view-job.png`).

### Root cause
`SalesDetail.tsx:161-167`:

```tsx
case 'view_job':
  if (entry?.signwell_document_id) {
    navigate(`/jobs/${entry.signwell_document_id}`);
  } else {
    navigate('/jobs');
  }
  break;
```

### Expected (from Req 15.4)
> WHEN the `view_job` action is triggered, THE SalesDetail host SHALL navigate to
> `/jobs/{entry.job_id}`.

### Fix
Either:
1. Extend the `SalesEntry` type + API to include a `job_id` field populated when the
   convert-to-job mutation runs; OR
2. Resolve the job via the customer id (look up the latest job for that customer).

Minimum fix: replace the incorrect `signwell_document_id` reference with the real job
id once it's exposed by the API. Until then, keep the fallback to `/jobs` as-is.

**Files**
- `frontend/src/features/sales/components/SalesDetail.tsx:161-167`

---

## Bug #8 — Dropzone file upload is a TODO stub (Medium)

### Symptom
Dragging a PDF into the estimate or signed-agreement dropzone shows the toast
"Not wired yet — TODO" and no document is uploaded. As a result, the only way to
"upload & send an estimate" is to use the pre-existing Documents upload above, then
refresh — and even then, the entry's existing documents may not be typed as `estimate`.

### Root cause
`SalesDetail.tsx:219-225`:

```tsx
const handleFileDrop = useCallback(
  (_file: File, _kind: 'estimate' | 'agreement') => {
    // TODO(backend): wire to useUploadSalesDocument when backend ready
    toast.info('Not wired yet — TODO');
  },
  [],
);
```

The `useUploadSalesDocument` hook already exists (see
`frontend/src/features/sales/hooks/useSalesPipeline.ts:130-148`). No backend work is
actually required — the TODO comment is misleading.

### Fix
```tsx
const uploadDoc = useUploadSalesDocument();
const handleFileDrop = useCallback(
  async (file: File, kind: 'estimate' | 'agreement') => {
    if (!entry?.customer_id) return;
    try {
      await uploadDoc.mutateAsync({
        customerId: entry.customer_id,
        file,
        documentType: kind === 'agreement' ? 'contract' : 'estimate',
      });
      toast.success(`${kind === 'agreement' ? 'Agreement' : 'Estimate'} uploaded`);
      refetch();
    } catch {
      toast.error('Upload failed');
    }
  },
  [entry, uploadDoc, refetch],
);
```

**Files**
- `frontend/src/features/sales/components/SalesDetail.tsx:219-225`

---

## Bug #9 — `hasSignedAgreement` matches unrelated contract docs (Low)

### Symptom
Any document with `document_type === 'contract'` on the customer makes `hasSignedAgreement`
true, even if it's not the signed counter-signed agreement for this sales entry. On Testing
Viktor's record, `palm.pdf` (contract) triggers this and would unlock the "Convert to Job"
button prematurely.

### Root cause
`SalesDetail.tsx:229-230`:

```tsx
const hasEstimateDoc = signingDocs.some((d) => d.document_type === 'estimate');
const hasSignedAgreement = signingDocs.some((d) => d.document_type === 'contract');
```

The detection is a broad "any contract doc on this customer" — not "a signed agreement
uploaded for this sales entry".

### Fix
Ideally tie documents to the sales entry id (not just the customer). Short-term: narrow
the filter to docs created after the entry entered `send_contract`, or require a naming
convention (e.g., filename starts with `signed_`). Track as a separate enhancement.

**Files**
- `frontend/src/features/sales/components/SalesDetail.tsx:229-230`

---

## Bug #10 — Pagination shows unfiltered total when filter hides all rows (Low)

### Symptom
On `/sales` with the stuck filter active and 0 matching rows, the footer still reads
"Showing 1 to 24 of 24 entries" — the pagination math uses the un-client-side-filtered
API total.

Reproduced: screenshot `23-followup-filter.png`.

### Root cause
`SalesPipeline.tsx:211-214` computes the range from `data.total`, but the stuck filter
is applied client-side on top of the loaded rows.

### Fix
When `stuckFilter` is true, show `visibleRows.length` instead of the API total, or hide
the pagination footer when zero rows are visible.

**Files**
- `frontend/src/features/sales/components/SalesPipeline.tsx:209-225`

---

## Bug #11 — `Mark Lost` button stays live on `closed_won`, fails with no-op toast (Low)

### Symptom
On a `closed_won` entry the StageStepper footer still shows **✕ Mark Lost**. Clicking
it fires `markLost.mutate`, which the backend rejects (`InvalidSalesTransitionError`
for terminal → terminal), so the user sees "Failed to mark as lost" with no
explanation.

Reproduced on Brooke Jore (in closed_won state, screenshot `19-after-mark-lost.png`).

### Root cause
`StageStepper.tsx` unconditionally renders the Mark Lost button, and `SalesDetail.tsx`
doesn't hide the stepper for terminal statuses other than `closed_lost`.

### Fix
Hide the StageStepper (or at least the Mark Lost button) for `closed_won` as well,
mirroring the `closed_lost` path — once in a terminal state, no transitions are valid.
Or disable the button with a tooltip ("Already closed — cannot mark lost").

**Files**
- `frontend/src/features/sales/components/SalesDetail.tsx:525-560` (hide stepper for
  closed_won too)
- OR `frontend/src/features/sales/components/StageStepper.tsx` (disable Mark Lost when
  `currentStage === 'closed_won'`)
