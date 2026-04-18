# Design Document: Internal Notes Simplification

## Overview

This spec reverts the user-facing notes experience to the single-blob Edit/Save pattern that shipped on main, and establishes one source-of-truth column (`customers.internal_notes` for customers, `leads.notes` for leads) read from — and edited on — every surface where that individual is rendered. The multi-entry `notes` table, `NoteService`, notes API, `NotesTimeline` component, and `useNotes` hook introduced in the April 16th release (commit `fd049e1`) are removed. A new shared `InternalNotesCard` component is introduced so Customer Detail, Lead Detail, Sales Entry Detail, and both Appointment modals render identical markup and behavior.

The core themes are:

1. **Remove the timeline** — Delete every user-facing and backend surface of the `NotesTimeline` / `NoteService` / notes-API stack, plus the `notes` table, with a safe fold of any existing rows into the simple blob columns.
2. **One shared component** — `InternalNotesCard` encapsulates the Edit/Save shell and is the sole implementation used by every surface.
3. **Source-of-truth reads** — Sales Entry Detail and Appointment modals do not store their own notes; they render the customer's `internal_notes` and, on Save, PATCH the customer row. Query invalidation makes the change visible on every other open surface immediately.
4. **Lead-to-customer carry-forward** — On Move to Sales / Move to Jobs, `leads.notes` is folded into `customers.internal_notes` once, with a merge rule that avoids overwriting existing content.

```mermaid
graph TD
    subgraph "Source-of-Truth Columns"
        LN[leads.notes]
        CN[customers.internal_notes]
    end

    subgraph "Surfaces (all use InternalNotesCard)"
        LD[Lead Detail]
        CD[Customer Detail]
        SD[Sales Entry Detail]
        JA[Job Appointment Modal]
        EA[Estimate Appointment Modal]
    end

    LD -- read/edit --> LN
    CD -- read/edit --> CN
    SD -- read/edit --> CN
    JA -- read/edit --> CN
    EA -- read/edit --> CN

    LN -. fold on Move to Sales/Jobs .-> CN

    subgraph "Removed"
        X1[notes table]
        X2[NoteService]
        X3[/api/v1/.../notes endpoints]
        X4[NotesTimeline + useNotes]
    end

    style X1 stroke-dasharray: 4 2
    style X2 stroke-dasharray: 4 2
    style X3 stroke-dasharray: 4 2
    style X4 stroke-dasharray: 4 2
```

## Architecture

### Backend Changes

Backend follows the existing vertical-slice layout at `src/grins_platform/`.

1. **Removals**
   - Delete `models/note.py`, `schemas/note.py`, `services/note_service.py`, `api/v1/notes.py`.
   - Unregister `Note` from `models/__init__.py` and the notes router from `api/v1/router.py`.
   - Remove the `create_stage_transition_note` call chain from `LeadService.move_to_sales` and `LeadService.move_to_jobs` (and any other service that invokes `NoteService`).

2. **Column confirmations (no new columns needed)**
   - `customers.internal_notes` already exists (`src/grins_platform/models/customer.py:149`).
   - `leads.notes` already exists (`src/grins_platform/models/lead.py:75`).

3. **Schema extensions**
   - `CustomerUpdate` already accepts `internal_notes` (confirm). If missing, add it.
   - `LeadUpdate` already accepts `notes` (confirm). If missing, add it.
   - `SalesEntryResponse` and `AppointmentResponse`: ensure the embedded `customer` object (or a `customer_internal_notes` passthrough) is included so Sales and Appointment surfaces can render the card without a second fetch.

4. **Lead routing carry-forward**
   - `LeadService.move_to_sales` and `LeadService.move_to_jobs` gain a `_carry_forward_lead_notes(lead, customer)` helper implementing the merge rule (see Components section). Called after the customer row is resolved (either the new customer or the merged customer).

5. **Migration chain**
   - New Alembic revision `20260418_<seq>_fold_notes_table_into_internal_notes.py` chained off the current head (`20260416_100600_create_appointment_attachments_table`).
   - Steps inside the migration's `upgrade()`:
     a. Read every `notes` row grouped by `(subject_type, subject_id)` ordered by `created_at`.
     b. For `subject_type = 'customer'`: `UPDATE customers SET internal_notes = COALESCE(internal_notes, '') || '<folded body>' WHERE id = :id`, using a separator rule that produces a clean blank-line-delimited output and is idempotent.
     c. For `subject_type = 'lead'`: same fold into `leads.notes`.
     d. For `subject_type IN ('sales_entry', 'appointment')`: count + log a sample (first 10 bodies to stderr via `op.get_context().impl.static_output`), then discard.
     e. `op.drop_table('notes')`.
   - `downgrade()` recreates the table shell but SHALL NOT attempt to reconstruct rows (one-way fold).

### Frontend Changes

Frontend follows the existing VSA pattern at `frontend/src/features/`.

1. **New shared component**
   - `frontend/src/shared/components/InternalNotesCard.tsx` — encapsulates the collapsed/expanded state, the Edit button, the textarea, and the Cancel/Save buttons. Exports `InternalNotesCard` and a `InternalNotesCardProps` type.
   - `frontend/src/shared/components/InternalNotesCard.test.tsx` — covers collapsed/expanded flow, toasts, readOnly mode, testid threading.
   - Export added to `frontend/src/shared/components/index.ts`.

2. **Removals**
   - Delete `frontend/src/shared/components/NotesTimeline.tsx` and its test file.
   - Delete `frontend/src/shared/hooks/useNotes.ts`.
   - Remove `NotesTimeline` / `useNotes` barrel exports from `frontend/src/shared/components/index.ts` and `frontend/src/shared/hooks/index.ts`.

3. **Consumer wiring**
   - `CustomerDetail.tsx`: replace the current `<NotesTimeline subjectType="customer" subjectId={id} />` render with `<InternalNotesCard value={customer.internal_notes} onSave={handleSaveCustomerNotes} isSaving={updateMutation.isPending} data-testid-prefix="customer-" />`. `handleSaveCustomerNotes` calls `useUpdateCustomer` with `{ internal_notes }`.
   - `LeadDetail.tsx`: same wiring, bound to `lead.notes` via `useUpdateLead` with `{ notes }`.
   - `SalesDetail.tsx`: renders `<InternalNotesCard value={salesEntry.customer?.internal_notes ?? null} onSave={handleSaveSalesEntryNotes} ... />`. `handleSaveSalesEntryNotes` calls `useUpdateCustomer` on `salesEntry.customer.id` and uses the shared invalidation helper to refresh both sales and customer queries.
   - `AppointmentForm.tsx` (job appointment modal): renders the card inside or adjacent to the existing `CustomerContextBlock`, bound to the customer's `internal_notes` reachable via the appointment's customer relationship.
   - `SalesCalendar.tsx` estimate-appointment edit dialog: same wiring; if the estimate's sales entry has no customer yet, render the "Notes will appear here once the customer is created" placeholder instead of the card.
   - `CustomerContextBlock.tsx`: optionally wrap the card internally so every surface that mounts the context block gets notes for free.

4. **Invalidation matrix addition**
   - In `frontend/src/shared/utils/invalidationHelpers.ts`, add (or extend) `invalidateAfterCustomerInternalNotesSave(queryClient, customerId)` that invalidates `customerKeys.detail(id)`, `customerKeys.lists()`, `salesKeys.lists()`, `salesKeys.detail(any-scoped-to-id)`, `appointmentKeys.lists()`, and the scoped appointment detail keys. Called from every `handleSaveXxxNotes` handler.

## Components and Interfaces

### Backend Components

#### 1. Lead Routing — Notes Carry-Forward Helper

```python
# src/grins_platform/services/lead_service.py (addition)

async def _carry_forward_lead_notes(
    self,
    lead: Lead,
    customer: Customer,
) -> None:
    """
    Fold leads.notes into customers.internal_notes per Requirement 5.

    Rules (in order):
      1. lead.notes is null/empty  -> no-op
      2. customer is newly created -> customer.internal_notes = lead.notes
      3. customer.internal_notes is null/empty -> overwrite with lead.notes
      4. both populated            -> append lead.notes to customer.internal_notes
                                      separated by "\n\n--- From lead (<date>) ---\n"
    """
    if not lead.notes or not lead.notes.strip():
        return

    existing = (customer.internal_notes or "").strip()
    if not existing:
        customer.internal_notes = lead.notes
    else:
        divider = f"\n\n--- From lead ({lead.created_at:%Y-%m-%d}) ---\n"
        customer.internal_notes = f"{existing}{divider}{lead.notes}"

    await self.audit_service.record(
        actor_id=self.actor_id,
        subject_type="customer",
        subject_id=customer.id,
        action="internal_notes.carry_forward",
        metadata={
            "lead_id": str(lead.id),
            "old_value_len": len(existing),
            "new_value_len": len(customer.internal_notes or ""),
        },
    )
```

Called at the end of `move_to_sales` and `move_to_jobs`, once the target customer is resolved.

#### 2. Fold Migration Shell

```python
# src/grins_platform/migrations/versions/20260418_<seq>_fold_notes_table_into_internal_notes.py

revision = "20260418_<seq>"
down_revision = "20260416_100600"

def upgrade() -> None:
    conn = op.get_bind()

    # Fold customer notes
    conn.execute(text("""
        UPDATE customers c
        SET internal_notes = COALESCE(NULLIF(TRIM(c.internal_notes), ''), '')
                           || CASE WHEN COALESCE(TRIM(c.internal_notes), '') = '' THEN '' ELSE E'\n\n' END
                           || folded.body
        FROM (
            SELECT subject_id, string_agg(body, E'\n\n' ORDER BY created_at) AS body
            FROM notes
            WHERE subject_type = 'customer' AND is_deleted = false
            GROUP BY subject_id
        ) folded
        WHERE c.id = folded.subject_id
    """))

    # Fold lead notes (into leads.notes column, same pattern)
    conn.execute(text("""UPDATE leads l SET notes = ... FROM (...) ... """))

    # Log-and-discard for sales_entry / appointment subject types
    sample = conn.execute(text("""
        SELECT subject_type, count(*), string_agg(substring(body, 1, 80), ' | ')
          FROM notes
         WHERE subject_type IN ('sales_entry', 'appointment') AND is_deleted = false
      GROUP BY subject_type
    """)).all()
    for subject_type, n, preview in sample:
        print(f"[fold] discarding {n} {subject_type} notes; sample: {preview}")

    op.drop_table("notes")
```

Idempotency note: the `CASE WHEN` guard on the customer fold prevents a double-prepended blank line on re-run, and the `string_agg` deterministically produces the same output for the same input set; however in practice this migration is one-shot because `notes` is dropped at the end.

### Frontend Components

#### 1. InternalNotesCard

```tsx
// frontend/src/shared/components/InternalNotesCard.tsx

export interface InternalNotesCardProps {
  value: string | null;
  onSave: (next: string | null) => Promise<void>;
  isSaving: boolean;
  readOnly?: boolean;
  placeholder?: string;
  'data-testid-prefix'?: string;
}

export function InternalNotesCard({
  value,
  onSave,
  isSaving,
  readOnly = false,
  placeholder = 'No internal notes',
  'data-testid-prefix': testIdPrefix = '',
}: InternalNotesCardProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [draft, setDraft] = useState<string>('');
  // ... handleEdit, handleCancel, handleSave (toasts)
}
```

Renders:

- **Collapsed**: `Card > CardHeader { "Internal Notes" + Edit button } > CardContent { <p> value or placeholder </p> }`
- **Expanded**: `Card > CardHeader { "Internal Notes" } > CardContent { <Textarea rows=5> + <div> Cancel + Save Notes </div> }`

Save handler:

```tsx
const handleSave = async () => {
  try {
    await onSave(draft.trim() === '' ? null : draft);
    setIsEditing(false);
    toast.success('Notes saved');
  } catch (err) {
    toast.error('Failed to save notes', { description: getErrorMessage(err) });
  }
};
```

#### 2. Consumer handlers (example — CustomerDetail)

```tsx
const updateMutation = useUpdateCustomer();

const handleSaveCustomerNotes = useCallback(
  async (next: string | null) => {
    await updateMutation.mutateAsync({
      id: customer.id,
      data: { internal_notes: next },
    });
  },
  [customer.id, updateMutation],
);

// Render:
<InternalNotesCard
  value={customer.internal_notes}
  onSave={handleSaveCustomerNotes}
  isSaving={updateMutation.isPending}
  data-testid-prefix="customer-"
/>
```

#### 3. Consumer handler (SalesDetail — cross-entity PATCH)

```tsx
const updateCustomerMutation = useUpdateCustomer();
const queryClient = useQueryClient();

const handleSaveSalesEntryNotes = useCallback(
  async (next: string | null) => {
    if (!salesEntry.customer?.id) return;
    await updateCustomerMutation.mutateAsync({
      id: salesEntry.customer.id,
      data: { internal_notes: next },
    });
    invalidateAfterCustomerInternalNotesSave(queryClient, salesEntry.customer.id);
  },
  [salesEntry.customer?.id, updateCustomerMutation, queryClient],
);
```

## Data Model

No new tables. No new columns. The migration **drops** the `notes` table introduced in `20260416_100500`.

Existing columns used:

| Table       | Column           | Type | Nullable |
|-------------|------------------|------|----------|
| `leads`     | `notes`          | text | yes      |
| `customers` | `internal_notes` | text | yes      |

No column is added to `sales_entries`, `appointments`, `jobs`, or `invoices` — those surfaces render the customer's blob by reference.

## API

No new endpoints. The following endpoints are **deleted**:

- `GET  /api/v1/leads/{id}/notes`
- `POST /api/v1/leads/{id}/notes`
- `GET  /api/v1/sales/{id}/notes`
- `POST /api/v1/sales/{id}/notes`
- `GET  /api/v1/customers/{id}/notes`
- `POST /api/v1/customers/{id}/notes`
- `PATCH /api/v1/notes/{id}`
- `DELETE /api/v1/notes/{id}`

The following endpoints gain (or confirm) the notes field in their response payloads:

- `GET /api/v1/customers/{id}` — already includes `internal_notes`.
- `GET /api/v1/leads/{id}` — already includes `notes`.
- `GET /api/v1/sales/{id}` — include a `customer` object with `{ id, internal_notes, ... }`, or a `customer_internal_notes` passthrough.
- `GET /api/v1/appointments/{id}` — same as above.

The following endpoints continue to accept `internal_notes` / `notes` in their PATCH payloads:

- `PATCH /api/v1/customers/{id}` — `internal_notes: string | null`.
- `PATCH /api/v1/leads/{id}` — `notes: string | null`.

## Error Handling

- **Save failure on any surface**: `InternalNotesCard` keeps the expanded state with the user's draft intact, shows a `toast.error('Failed to save notes', { description: getErrorMessage(err) })`. No partial UI state; the Cancel button still reverts.
- **Empty string on Save**: `InternalNotesCard` normalizes empty/whitespace-only drafts to `null` so the column goes null rather than storing `""`.
- **Sales entry without a customer** (estimate pre–Move to Jobs): the placeholder "Notes will appear here once the customer is created" is rendered; no Edit/Save affordance is exposed. This avoids orphan writes.
- **Fold migration on empty `notes` table**: the migration's fold queries are all safe no-ops when the source table is empty; the `DROP TABLE` at the end still succeeds.

## Testing Strategy

### Backend

- `tests/unit/test_internal_notes_merge.py` — covers the `_carry_forward_lead_notes` helper against the four merge branches (Requirement 5 items 2, 3, 4, and the null-notes no-op from item 7).
- `tests/integration/test_lead_routing_notes.py` — end-to-end: create lead with notes, route via Move_to_Jobs, GET customer, assert `internal_notes` matches the expected merge output.
- `tests/integration/test_fold_notes_migration.py` — applies the fold migration against a seeded `notes` table with one customer entry, one lead entry, one sales_entry entry, one appointment entry; asserts customer + lead columns updated and the latter two entries logged + discarded, and the table dropped.
- Delete: `test_pbt_april_16th.py::Property_7`, `Property_8`, `Property_9`; any direct `NoteService` tests in `test_april_16th_functional.py` and `test_april_16th_integration.py`.

### Frontend

- `shared/components/InternalNotesCard.test.tsx` — collapsed/expanded rendering for populated + null values; Edit → Cancel reverts; Edit → type → Save invokes `onSave` with the typed value; `isSaving` disables the button and swaps label; `readOnly` hides Edit; `data-testid-prefix` threads through.
- `customers/components/CustomerDetail.test.tsx` — asserts card renders with customer's `internal_notes`; Save wires to `useUpdateCustomer`.
- `leads/components/LeadDetail.test.tsx` — same pattern against `useUpdateLead` and `lead.notes`.
- `sales/components/SalesDetail.test.tsx` — card reads `salesEntry.customer.internal_notes`; Save calls `useUpdateCustomer` on `salesEntry.customer.id`; invalidation helper invoked on success.
- `schedule/components/AppointmentForm.test.tsx` and `sales/components/SalesCalendar.test.tsx` — card renders in the modal; Save PATCHes the customer; placeholder renders when the estimate has no customer.
- Delete: `NotesTimeline.test.tsx`, `useNotes.test.tsx` if present, and any `april16th.pbt.test.ts` properties targeting timeline semantics.

## Open Questions & Assumptions

1. **Append divider format.** This spec proposes `\n\n--- From lead (YYYY-MM-DD) ---\n` as the separator when a lead's notes are appended to a pre-populated customer. Flag if a different format is preferred (e.g. no divider, a different label).
2. **Lead blob after routing.** This spec leaves `leads.notes` unchanged on the lead row after routing, for historical reference. Flag if the preferred behavior is to clear the lead blob once folded.
3. **Jobs / Invoices surfaces.** These are not listed in Requirement 4. If the Jobs Detail page or Invoice Detail page renders a customer card and should also show/edit the customer's `internal_notes`, extend the consumer wiring to them too. The shared component makes this trivial.
4. **Fold for `sales_entry` / `appointment` subject types.** This spec discards those timeline entries (the simplified model has no per-sales-entry or per-appointment notes column). If it turns out dev has valuable notes written against those subject types, either add columns for them before folding or extend the fold to append those entries into `customers.internal_notes` (with a "(Sales entry 2026-04-17)" divider). The dev DB should be inspected before running the migration.
5. **Cross-tab propagation timing.** The design relies on TanStack Query invalidation, which only refreshes the tab that triggered the mutation. Open tabs in other browser windows will not see the update until they refetch on window focus. If strict real-time propagation across windows is required, this spec does not cover that (Requirement 6 reads as "via Query_Invalidation"); a follow-up would need a websocket or polling channel.
