# Implementation Tasks: Internal Notes Simplification

## Phase 1: Shared Component Foundation (Sequential — everything else depends on this)

- [x] 1.1 Create `frontend/src/shared/components/InternalNotesCard.tsx` with the `InternalNotesCardProps` interface from design.md. Implement collapsed state (CardHeader with "Internal Notes" + Edit ghost button, CardContent with `<p whitespace-pre-wrap>` value or muted placeholder). Implement expanded state (CardHeader without button, CardContent with `<Textarea rows=5>` + right-aligned `<Button variant="outline">Cancel</Button>` and `<Button>Save Notes</Button>`). Encapsulate `isEditing` and `draft` state via `useState`. Normalize empty/whitespace drafts to `null` in the save handler. Wire success toast ("Notes saved") and error toast ("Failed to save notes", description via `getErrorMessage(err)`).
- [x] 1.2 Export `InternalNotesCard` from `frontend/src/shared/components/index.ts`.
- [x] 1.3 Create `frontend/src/shared/components/InternalNotesCard.test.tsx` covering: collapsed renders value or placeholder; Edit button flips to expanded with draft prefilled; Cancel returns to collapsed and discards changes; Save invokes `onSave` with the typed string (or null when empty); `isSaving=true` disables button and shows "Saving..."; `readOnly=true` hides the Edit button; `data-testid-prefix` threads through to `edit-notes-btn`, `internal-notes-textarea`, `save-notes-btn`, `internal-notes-display`, `notes-editor`.

## Phase 2: Shared Invalidation Helper (Parallel with Phase 1)

- [x] 2.1 In `frontend/src/shared/utils/invalidationHelpers.ts`, add `invalidateAfterCustomerInternalNotesSave(queryClient, customerId)` that invalidates: `customerKeys.detail(customerId)`, `customerKeys.lists()`, `salesKeys.lists()`, any `salesKeys.detail(...)` scoped to this customer (use predicate-based invalidation if IDs unknown), `appointmentKeys.lists()`, and predicate-invalidate appointment detail keys whose data references this customer. Keep the existing `invalidateAfterCustomerMutation` helper intact for other callers.

## Phase 3: Remove the Notes Timeline — Frontend (Parallel after Phase 1)

- [x] 3.1 Delete `frontend/src/shared/components/NotesTimeline.tsx` and `frontend/src/shared/components/NotesTimeline.test.tsx`.
- [x] 3.2 Delete `frontend/src/shared/hooks/useNotes.ts` and any related test file.
- [x] 3.3 Remove `NotesTimeline` and `useNotes` / `useCreateNote` exports from `frontend/src/shared/components/index.ts` and `frontend/src/shared/hooks/index.ts`.
- [x] 3.4 Remove any NotesTimeline renders that aren't replaced in Phase 4 — i.e. any lingering usage in Jobs, Invoices, or ad-hoc views not covered by the consumer wiring below.

## Phase 4: Wire Consumers to InternalNotesCard (Parallel after Phase 1 + Phase 3)

- [x] 4.1 `frontend/src/features/customers/components/CustomerDetail.tsx` — replace the `NotesTimeline` render on the Overview tab with `<InternalNotesCard value={customer.internal_notes} onSave={handleSaveCustomerNotes} isSaving={updateMutation.isPending} data-testid-prefix="customer-" />`. Implement `handleSaveCustomerNotes` using `useUpdateCustomer().mutateAsync({ id: customer.id, data: { internal_notes: next } })`. Remove the imports of `NotesTimeline` and any timeline-only state/helpers.
- [x] 4.2 `frontend/src/features/leads/components/LeadDetail.tsx` — same wiring, bound to `lead.notes` via `useUpdateLead().mutateAsync({ id: lead.id, data: { notes: next } })`. Use `data-testid-prefix="lead-"`.
- [x] 4.3 `frontend/src/features/sales/components/SalesDetail.tsx` — render `<InternalNotesCard value={salesEntry.customer?.internal_notes ?? null} onSave={handleSaveSalesEntryNotes} isSaving={updateCustomerMutation.isPending} readOnly={!salesEntry.customer?.id} data-testid-prefix="sales-" />`. Implement `handleSaveSalesEntryNotes` to PATCH the customer via `useUpdateCustomer`, then call `invalidateAfterCustomerInternalNotesSave(queryClient, salesEntry.customer.id)` on success.
- [x] 4.4 `frontend/src/features/schedule/components/AppointmentForm.tsx` — add the `InternalNotesCard` inside or below the `CustomerContextBlock`, bound to the appointment's customer's `internal_notes`. Same save path as 4.3 (PATCH customer + invalidate). Use `data-testid-prefix="appointment-"`.
- [x] 4.5 `frontend/src/features/sales/components/SalesCalendar.tsx` — add the card to the estimate-appointment edit dialog. When `salesEntry.customer?.id` is falsy, render a muted "Notes will appear here once the customer is created" placeholder instead of the card.
- [x] 4.6 `frontend/src/shared/components/CustomerContextBlock.tsx` — optional but recommended: mount the `InternalNotesCard` inside the block so every future surface that uses the block gets notes for free. Document the Save handler prop on the block.

## Phase 5: Remove the Notes Timeline — Backend (Parallel after Phase 4 deploys, so live app doesn't 404)

Ordering note: ship Phase 4 to dev first so the UI no longer calls the notes endpoints, then ship Phase 5 to remove the endpoints. (Or ship them in one go if the dev environment's admins agree to a coordinated deploy.)

- [x] 5.1 Delete `src/grins_platform/api/v1/notes.py`. Remove its router include from `src/grins_platform/api/v1/router.py`.
- [x] 5.2 Delete `src/grins_platform/services/note_service.py`.
- [x] 5.3 Delete `src/grins_platform/schemas/note.py`.
- [x] 5.4 Delete `src/grins_platform/models/note.py`. Unregister the `Note` import from `src/grins_platform/models/__init__.py`.
- [x] 5.5 `src/grins_platform/services/lead_service.py` — remove the `create_stage_transition_note` call (and the `NoteService` import) from the `move_to_sales` and `move_to_jobs` paths and anywhere else it is invoked.
- [x] 5.6 `src/grins_platform/services/note_service.py`-dependent imports — grep the repo for `note_service`, `NoteService`, `from .note import` — remove every remaining reference.

## Phase 6: Lead-to-Customer Notes Carry-Forward (After Phase 5)

- [x] 6.1 In `src/grins_platform/services/lead_service.py`, add the `_carry_forward_lead_notes(self, lead, customer)` helper from design.md. The helper implements Requirement 5's four-branch merge rule and writes one audit entry via `AuditService`.
- [x] 6.2 Call `_carry_forward_lead_notes` at the end of `move_to_sales` (after the target customer is resolved — new or merged) and at the end of `move_to_jobs` (after the target customer is resolved). Ensure the call happens within the same transaction so the fold is atomic with the routing.
- [x] 6.3 Confirm `CustomerUpdate` and `LeadUpdate` schemas include `internal_notes` and `notes` as optional patchable fields. Add them if missing.
- [x] 6.4 Confirm `SalesEntryResponse` embeds a `customer` object containing `internal_notes` (or a `customer_internal_notes` passthrough) so `SalesDetail.tsx` has the value without a second fetch. Extend if missing.
- [x] 6.5 Confirm `AppointmentResponse` (job + estimate variants) exposes the customer's `internal_notes` similarly. Extend if missing.

## Phase 7: Fold Migration (After Phase 6)

- [x] 7.1 Create `src/grins_platform/migrations/versions/20260418_<seq>_fold_notes_table_into_internal_notes.py` chained off the current head (`20260416_100600_create_appointment_attachments_table`).
- [x] 7.2 Implement `upgrade()` per design.md: `UPDATE customers` fold for `subject_type='customer'`, `UPDATE leads` fold for `subject_type='lead'`, print-then-discard for `subject_type IN ('sales_entry','appointment')` (emit count + first-10 body preview to migration output), then `op.drop_table('notes')`.
- [x] 7.3 Implement `downgrade()` to recreate the empty `notes` table shell (column definitions + indexes) without attempting to reconstruct rows — document this is a one-way fold.
- [x] 7.4 Run the migration locally against a dev-like database seeded with the dev DB's notes rows (if any exist). Verify customers and leads columns are populated correctly, non-customer/non-lead entries are logged, and the drop succeeds.
- [x] 7.5 Before applying in the dev environment, run an inspection query on dev to count `notes` rows per `subject_type`. If any sales_entry / appointment counts are non-trivial, raise a flag and wait for product direction before running the drop.

## Phase 8: Tests — Backend (After Phases 5, 6, 7)

- [x] 8.1 Create `src/grins_platform/tests/unit/test_internal_notes_merge.py` — unit tests for `_carry_forward_lead_notes` covering: empty lead notes no-op (Req 5.7); newly created customer overwrite (Req 5.2); empty customer overwrite (Req 5.3); appended customer with divider (Req 5.4); audit entry written with correct actor/subject/old-len/new-len.
- [x] 8.2 Create `src/grins_platform/tests/integration/test_lead_routing_notes.py` — full flow: create lead with `notes='original lead context'`, route via Move_to_Jobs to a fresh customer → GET customer, assert `internal_notes == 'original lead context'`. Repeat with Move_to_Sales. Repeat with an existing merged-customer branch.
- [x] 8.3 Create `src/grins_platform/tests/integration/test_fold_notes_migration.py` — apply the fold migration against a seeded `notes` table (one customer entry, one lead entry, one sales_entry entry, one appointment entry), assert customers + leads columns updated with the expected text, sales_entry + appointment entries were not migrated but were logged, and the `notes` table has been dropped.
- [x] 8.4 Delete `src/grins_platform/tests/unit/test_pbt_april_16th.py::Property_7`, `Property_8`, `Property_9` cases. Delete any direct `NoteService` tests in `test_april_16th_functional.py` and `test_april_16th_integration.py`. Leave all other April-16 tests intact.
- [x] 8.5 Grep for `NoteService`, `useNotes`, `NotesTimeline`, `/notes` API references in tests and remove any stragglers.

## Phase 9: Tests — Frontend (After Phases 1, 4)

- [x] 9.1 Add `CustomerDetail.test.tsx` assertions: `InternalNotesCard` renders with `customer.internal_notes`; Edit → type → Save triggers `useUpdateCustomer` with `{ internal_notes: <typed> }`; Cancel reverts.
- [x] 9.2 Add `LeadDetail.test.tsx` assertions: card renders with `lead.notes`; Save triggers `useUpdateLead` with `{ notes: <typed> }`.
- [x] 9.3 Add `SalesDetail.test.tsx` assertions: card renders `salesEntry.customer.internal_notes`; Save calls `useUpdateCustomer` on `salesEntry.customer.id`; invalidation helper invoked on success; `readOnly` placeholder when customer missing.
- [x] 9.4 Add `AppointmentForm.test.tsx` assertions: card renders for job appointments; Save PATCHes the customer; invalidation happens.
- [x] 9.5 Add `SalesCalendar.test.tsx` assertions for the estimate-appointment edit dialog: card + placeholder scenarios.
- [x] 9.6 Delete `frontend/src/shared/components/NotesTimeline.test.tsx` and any `useNotes.test.tsx` if present. Delete any properties targeting timeline semantics in `april16th.pbt.test.ts` (keep only those still applicable).

## Phase 10: Cleanup & Documentation (After all prior phases)

- [x] 10.1 Update `DEVLOG.md` with a short entry: reason for the revert, summary of what was removed vs. kept, fold-migration revision id, and the count of `notes` rows migrated per subject_type.
- [x] 10.2 Search the repo for stray documentation references to `NotesTimeline` or the notes API and update or remove them (bughunt docs, feature-developments markdown, etc.).
- [x] 10.3 Remove the April-16 requirement that introduced the notes timeline from the `april-16th-fixes-enhancements` spec's tasks.md status (mark Requirement 4 as "superseded by internal-notes-simplification" with a pointer to this spec), so future readers understand the timeline was intentionally reverted.
- [x] 10.4 Run `uv run ruff check`, `uv run mypy`, `uv run pyright`, and the full backend test suite — confirm zero regressions from the deletions.
- [x] 10.5 Run `npm --prefix frontend run lint`, `npm --prefix frontend run typecheck`, and `npm --prefix frontend test` — confirm zero regressions.
- [x] 10.6 Smoke-test on dev: open a customer, edit the notes, save, confirm toast and persistence; open the customer's sales entry, edit the notes there, save, switch back to the customer — the blob matches; open an appointment modal for that customer and confirm the same.

## Acceptance Gate

Before marking this spec as complete:

- All phases 1–10 are checked off.
- The `notes` table no longer exists in the dev DB.
- `NotesTimeline` returns zero grep hits across `frontend/` and `src/`.
- `NoteService` and `useNotes` return zero grep hits.
- Each of the four consumer surfaces (Customer Detail, Lead Detail, Sales Detail, Appointment Modal) shows the Edit / type / Save Notes pattern and nothing else.
- Lead notes carry-forward verified manually on dev with at least one newly-routed lead.
