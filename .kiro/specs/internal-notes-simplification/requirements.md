# Requirements Document

## Introduction

This document specifies the simplification and unification of the internal-notes feature across Lead, Customer, Sales Entry, and Appointment surfaces in the Grins Platform CRM. The April 16th release introduced a multi-entry `Notes_Timeline` system (notes table, per-entry author/timestamp/stage-tag chrome, always-visible "Add note" textarea with a paper-airplane submit button) that proved unwieldy for day-to-day admin use. This spec reverts the user-facing notes experience to the simple single-blob edit/save pattern that shipped on main, while preserving a new cross-surface visibility guarantee: the notes blob that pertains to a given individual SHALL be displayed (and editable) wherever that individual's record is rendered — Customer Detail, Sales Entry Detail, Appointment Detail, and any surface that renders a customer context card. The goal is one source-of-truth blob per individual, one interaction pattern (Edit → type → Save Notes), shown everywhere that individual appears.

## Glossary

- **Platform**: The Grins Platform CRM application (FastAPI backend + React frontend)
- **Individual**: A Lead (before routing) or Customer (after Move to Sales / Move to Jobs). Sales Entries and Appointments are always scoped to a Customer once the lead has been routed.
- **Customer_Detail_Page**: The frontend page at `frontend/src/features/customers/components/CustomerDetail.tsx` displaying a single customer record
- **Lead_Detail_Page**: The frontend page at `frontend/src/features/leads/components/LeadDetail.tsx` displaying a single lead record
- **Sales_Entry_Detail_Page**: The frontend page at `frontend/src/features/sales/components/SalesDetail.tsx` displaying a single sales pipeline entry record
- **Appointment_Modal**: The edit dialog for calendar appointments — job appointments via `frontend/src/features/schedule/components/AppointmentForm.tsx`, estimate appointments via the edit dialog in `frontend/src/features/sales/components/SalesCalendar.tsx`
- **Customer_Context_Block**: The read-only customer-summary block rendered at the top of Appointment_Modal (and any other surface that shows customer context inside a scoped detail view)
- **Internal_Notes_Blob**: A single nullable text column on a Lead or Customer row (`leads.notes` and `customers.internal_notes`). There is exactly one blob per Individual at any point in time.
- **Internal_Notes_Card**: The shared React component that renders the Internal_Notes_Blob. Collapsed state shows the blob as plain text with an "Edit" button; expanded state shows a textarea with "Cancel" and "Save Notes" buttons. Saving PATCHes the owning row's blob and shows a toast.
- **Notes_Timeline** (deprecated): The multi-entry notes system introduced in the April 16th release. This spec removes it from the user-facing UI and from the backend.
- **Move_to_Sales** / **Move_to_Jobs**: The two routing actions that promote a Lead into the Sales or Customer stage. Defined in `src/grins_platform/services/lead_service.py`.
- **Propagation**: The act of displaying the same Internal_Notes_Blob on every surface scoped to the same Individual. This is a read-from-source-of-truth behavior, not a copy or sync. Exception: on Move_to_Sales / Move_to_Jobs, the lead's `notes` is carried forward into `customers.internal_notes` at conversion time (see Requirement 5).
- **Query_Invalidation**: The TanStack Query mechanism where a mutation's `onSuccess` callback calls `invalidateQueries` on every query key whose data the mutation could affect

## Requirements

### Requirement 1: Remove the Notes Timeline System

**User Story:** As an admin, I don't want to see a multi-entry notes timeline with per-entry author/timestamp/stage-tag chrome and a paper-airplane submit button, because the always-visible textarea and append-only history feel noisy for the day-to-day task of jotting down a few lines about a customer.

#### Acceptance Criteria

1. THE Platform SHALL remove the user-facing `NotesTimeline` component and all its call sites. No page in the admin app SHALL render the timeline-style notes UI after this spec lands.
2. THE Platform SHALL delete the following frontend files: `frontend/src/shared/components/NotesTimeline.tsx`, `frontend/src/shared/components/NotesTimeline.test.tsx`, `frontend/src/shared/hooks/useNotes.ts`, and any barrel re-exports of those symbols.
3. THE Platform SHALL delete the following backend files: `src/grins_platform/models/note.py`, `src/grins_platform/schemas/note.py`, `src/grins_platform/services/note_service.py`, and `src/grins_platform/api/v1/notes.py`.
4. THE Platform SHALL remove `NoteService`'s integration points from `LeadService` (the `create_stage_transition_note` call inside Move_to_Sales / Move_to_Jobs) and from any other service that invokes it.
5. THE Platform SHALL remove the notes router registration from `src/grins_platform/api/v1/router.py` and the `Note` model registration from `src/grins_platform/models/__init__.py`.
6. THE Platform SHALL provide an Alembic migration that drops the `notes` table created by `20260416_100500_create_notes_table.py`. The migration SHALL chain off the current head and SHALL be safely re-runnable (use `IF EXISTS` for the drop).
7. THE Platform SHALL remove the tests that target the deleted symbols (`test_pbt_april_16th.py` Properties 7, 8, 9 specifically; any direct `NoteService` / notes-API tests in `test_april_16th_functional.py` and `test_april_16th_integration.py`). Tests targeting other April-16 requirements SHALL remain.

### Requirement 2: Customer Detail — Single Internal Notes Blob with Edit/Save

**User Story:** As an admin, I want the Customer Detail page's notes section to behave exactly like it did on main — a card labeled "Internal Notes," an Edit button, a textarea that opens when I click Edit, and a Save Notes button that overwrites the blob — so that jotting down context about a customer is a one-gesture action.

#### Acceptance Criteria

1. THE Customer_Detail_Page SHALL render an Internal_Notes_Card on the Overview tab.
2. WHEN the Internal_Notes_Card is in collapsed state, THE Customer_Detail_Page SHALL display the value of `customer.internal_notes` as plain text with `whitespace-pre-wrap` formatting, or a muted "No internal notes" placeholder if the field is null or empty.
3. WHEN the Internal_Notes_Card is in collapsed state, THE Customer_Detail_Page SHALL display an "Edit" button (pencil icon, ghost variant, small size) in the card header.
4. WHEN an admin clicks Edit, THE Customer_Detail_Page SHALL switch the card into expanded state with a 5-row `Textarea` prefilled with the current `customer.internal_notes` value.
5. WHEN the card is in expanded state, THE Customer_Detail_Page SHALL display a "Cancel" button (outline variant) and a "Save Notes" button (primary variant) aligned to the right of the textarea.
6. WHEN an admin clicks Cancel, THE Customer_Detail_Page SHALL discard any unsaved textarea changes and return the card to collapsed state.
7. WHEN an admin clicks Save Notes, THE Platform SHALL PATCH `/api/v1/customers/{id}` with `{ "internal_notes": <textarea_value> || null }` via the existing `useUpdateCustomer` mutation.
8. WHEN a Save Notes request succeeds, THE Customer_Detail_Page SHALL return the card to collapsed state, invalidate the customer query so the new value renders, and display a "Notes saved" success toast.
9. WHEN a Save Notes request fails, THE Customer_Detail_Page SHALL keep the card in expanded state with the user's typed value intact and display a "Failed to save notes" error toast with the server error extracted via `getErrorMessage(err)`.
10. WHILE a Save Notes request is in flight, THE Save Notes button SHALL be disabled and display "Saving..." instead of "Save Notes."
11. THE Internal_Notes_Card SHALL expose stable `data-testid` attributes: `edit-notes-btn`, `internal-notes-textarea`, `save-notes-btn`, `internal-notes-display`, and `notes-editor`, matching the pattern used on main's CustomerDetail.
12. THE Customer_Detail_Page SHALL NOT render any paper-airplane submit icon, timeline entry row, author avatar, author name, entry timestamp, or stage tag ("Customer"/"Lead"/"Sales"/"Appointment") anywhere in the notes card.

### Requirement 3: Lead Detail — Single Internal Notes Blob with Edit/Save

**User Story:** As an admin, I want the Lead Detail page to have the same Edit → type → Save Notes interaction for lead-stage notes as the Customer Detail page, so that I learn one pattern and use it everywhere.

#### Acceptance Criteria

1. THE Lead_Detail_Page SHALL render an Internal_Notes_Card tied to the `leads.notes` column.
2. THE Internal_Notes_Card on the Lead_Detail_Page SHALL follow the same collapsed/expanded states, button semantics, and toast behavior as defined in Requirement 2 (items 2–10), with the backing field being `lead.notes` and the mutation being `useUpdateLead`.
3. WHEN an admin clicks Save Notes on the Lead_Detail_Page, THE Platform SHALL PATCH `/api/v1/leads/{id}` with `{ "notes": <textarea_value> || null }`.
4. THE Lead_Detail_Page SHALL expose the same `data-testid` attributes as Requirement 2 item 11 so shared test helpers work across both pages.
5. THE Lead_Detail_Page SHALL NOT render any paper-airplane submit icon, timeline entry row, author avatar, author name, entry timestamp, or stage tag anywhere in the notes card.

### Requirement 4: Sales Entry & Appointment — Read/Edit the Customer's Internal Notes

**User Story:** As an admin, when I open a Sales Entry or an Appointment for a customer, I want to see the same internal notes blob I wrote on the Customer Detail page, and I want to be able to edit it in place, so that I never have to navigate back to the customer to update context about them.

#### Acceptance Criteria

1. THE Sales_Entry_Detail_Page SHALL render an Internal_Notes_Card bound to the underlying `customers.internal_notes` field of the customer that the sales entry is scoped to, not to any column on the sales entry row itself.
2. WHEN an admin clicks Save Notes on the Sales_Entry_Detail_Page, THE Platform SHALL PATCH the customer's `internal_notes` (i.e. `PATCH /api/v1/customers/{customer_id}` via `useUpdateCustomer`), NOT the sales entry row.
3. WHEN a Save Notes request succeeds on the Sales_Entry_Detail_Page, THE Platform SHALL invalidate both the sales-entry query and the customer query (using the shared invalidation helpers) so that the new value is reflected on the Customer_Detail_Page and any other open tab immediately via Query_Invalidation.
4. THE Appointment_Modal SHALL render an Internal_Notes_Card inside the Customer_Context_Block (or directly below it) bound to the `customers.internal_notes` field of the customer that the appointment is scoped to. This applies to both job appointments (`AppointmentForm.tsx`) and estimate appointments (the edit dialog in `SalesCalendar.tsx`).
5. WHEN an admin clicks Save Notes on an Appointment_Modal, THE Platform SHALL PATCH the customer's `internal_notes` via `useUpdateCustomer` and invalidate the customer query plus any appointment-scoped query that renders the block.
6. IF an Appointment_Modal is opened for an estimate appointment whose sales entry has no customer yet (pre–Move to Jobs), THEN THE Platform SHALL render a muted "Notes will appear here once the customer is created" placeholder in place of the card and SHALL NOT expose Edit / Save Notes affordances.
7. THE Internal_Notes_Card on Sales_Entry_Detail_Page and Appointment_Modal SHALL expose the same stable `data-testid` attributes as Requirement 2 item 11.
8. THE Internal_Notes_Card SHALL NOT display anywhere which surface (Customer, Sales, or Appointment) the blob was last edited from. There are no per-edit attribution entries.

### Requirement 5: Lead-to-Customer Notes Propagation on Routing

**User Story:** As an admin, when I route a lead via Move to Sales or Move to Jobs, I want the notes I wrote during the lead stage to carry forward to the customer record, so that none of my context is lost at the lifecycle boundary.

#### Acceptance Criteria

1. WHEN a lead is routed via Move_to_Sales or Move_to_Jobs and the routing action creates a new Customer row (either by creating or merging), THE Platform SHALL populate the new or merged `customers.internal_notes` with the content of `leads.notes`, subject to the merge rules below.
2. IF the target customer row is newly created by the routing action, THEN THE Platform SHALL set `customers.internal_notes = leads.notes`.
3. IF the target customer row is a pre-existing merged customer AND `customers.internal_notes` is null or empty, THEN THE Platform SHALL set `customers.internal_notes = leads.notes`.
4. IF the target customer row is a pre-existing merged customer AND `customers.internal_notes` already contains text AND `leads.notes` is non-empty, THEN THE Platform SHALL append the lead's notes onto the customer's existing notes, separated by a single blank line and a line reading `--- From lead (<created_at date>) ---` so the prior-stage source is visible to the reader.
5. WHEN the routing action runs, THE Platform SHALL NOT clear or modify `leads.notes` on the original lead row; the blob remains on the lead record for historical reference.
6. WHEN a routing action appends lead notes to a customer row, THE Platform SHALL write a single audit-log entry via `AuditService` capturing actor, lead_id, customer_id, and a diff-style old/new value for `internal_notes`. No per-line or per-entry audit entries are required.
7. IF `leads.notes` is null or empty at routing time, THEN THE Platform SHALL take no action on the customer's `internal_notes` field.

### Requirement 6: Propagation Across Customer Surfaces (Read-from-Source-of-Truth)

**User Story:** As an admin, I want every view that references a customer — Sales Entry Detail, Appointment Modals, any customer context card, job detail pages — to show the current value of that customer's internal notes, so that the blob I edit on one surface is visible on every other surface without a refresh.

#### Acceptance Criteria

1. THE Platform SHALL treat `customers.internal_notes` as the single source of truth for a customer's internal notes. No surface SHALL store a copy of the blob in its own row (no duplication on sales entries, appointments, jobs, or invoices).
2. WHEN an admin edits `customers.internal_notes` from any surface (Customer_Detail_Page, Sales_Entry_Detail_Page, Appointment_Modal), THE Platform SHALL persist the change to `customers.internal_notes` and invalidate every TanStack Query key whose rendered data includes the blob.
3. THE Platform SHALL expose `internal_notes` in the following API response payloads if not already present: `GET /api/v1/customers/{id}`, `GET /api/v1/sales/{id}` (via a nested `customer` object or an explicit `customer_internal_notes` field), `GET /api/v1/appointments/{id}` (via the same mechanism), and any other endpoint that returns customer context embedded inside a scoped entity.
4. THE Customer_Context_Block SHALL render the Internal_Notes_Card using the customer object it already has in hand; it SHALL NOT issue a second fetch for notes. Any additional invalidation needed after a Save SHALL happen via the shared invalidation helpers, not via a manual refetch on the block.
5. WHEN a customer row has `internal_notes = null` or an empty string, every surface SHALL render the "No internal notes" placeholder consistently.

### Requirement 7: Shared Internal Notes Card Component

**User Story:** As a developer, I want one shared React component that implements the Edit/Save internal-notes pattern, so that every surface renders the same markup, the same styles, the same testids, and the same behavior.

#### Acceptance Criteria

1. THE Platform SHALL provide a shared component at `frontend/src/shared/components/InternalNotesCard.tsx` exporting `InternalNotesCard`.
2. THE `InternalNotesCard` component SHALL accept the following props: `value: string | null`, `onSave: (next: string | null) => Promise<void>`, `isSaving: boolean`, `readOnly?: boolean` (defaults to false), `placeholder?: string` (defaults to "No internal notes"), and `data-testid-prefix?: string` (defaults to "").
3. WHEN `readOnly` is true, THE `InternalNotesCard` SHALL render the blob as plain text and SHALL NOT display an Edit button or any expanded-state affordances.
4. THE component SHALL encapsulate the collapsed/expanded state internally (via `useState`); callers SHALL NOT need to manage the editing flag.
5. THE component SHALL emit a "Notes saved" toast on success and a "Failed to save notes" toast on failure, with the error description extracted via `getErrorMessage(err)`.
6. THE component SHALL be the single implementation used by Customer_Detail_Page, Lead_Detail_Page, Sales_Entry_Detail_Page, and Appointment_Modal. No page SHALL re-implement the Edit/Save shell inline.
7. THE component SHALL be covered by a test file at `frontend/src/shared/components/InternalNotesCard.test.tsx` asserting: collapsed-state rendering for both populated and null values, Edit flips to expanded, Cancel reverts, Save invokes `onSave` with the typed value, `isSaving` disables the button and swaps the label, `readOnly` hides edit affordances, and that `data-testid-prefix` threads through to all interactive elements.

### Requirement 8: Data Migration & Backward Compatibility

**User Story:** As an engineer shipping this spec, I want the transition off the notes timeline to be safe for any data already written in dev, so that I don't lose real customer context when the table is dropped.

#### Acceptance Criteria

1. BEFORE dropping the `notes` table, THE Platform SHALL provide a one-time data-migration step (inside the same Alembic revision or a sibling revision chained before the drop) that folds every existing `notes.body` entry whose `subject_type = 'customer'` into the corresponding `customers.internal_notes` column. The fold SHALL preserve `created_at` order and SHALL separate entries with a single blank line.
2. THE Platform SHALL apply the equivalent fold for `subject_type = 'lead'` entries into `leads.notes`.
3. THE Platform SHALL discard `subject_type = 'sales_entry'` and `subject_type = 'appointment'` entries (these had no single-blob target in the simplified model) but SHALL log their count and a sample of bodies to the migration output so nothing is silently dropped without visibility.
4. THE fold SHALL be idempotent: re-running the migration on an already-folded row SHALL NOT produce duplicate entries.
5. THE Platform SHALL update `DEVLOG.md` with a short entry documenting the fold, the count of entries migrated, and the migration revision id.

### Requirement 9: Test Updates

**User Story:** As an engineer, I want the test suite to reflect the simplified notes model, so that CI doesn't chase after deleted symbols and the new behavior is locked in.

#### Acceptance Criteria

1. THE Platform SHALL remove all tests that exercise deleted symbols: NotesTimeline rendering, useNotes/useCreateNote hook behavior, NoteService methods, the notes API endpoints, and any property-based test cases that assert timeline behavior.
2. THE Platform SHALL add tests for `InternalNotesCard` as specified in Requirement 7 item 7.
3. THE Platform SHALL add or update tests for each of the four consuming surfaces asserting: the card renders and Save wires to the correct PATCH endpoint for that surface; the "collapsed → Edit → textarea → Save → collapsed" flow completes; the Cancel path reverts unsaved changes.
4. THE Platform SHALL add a backend integration test for Requirement 5 asserting: a lead with a non-empty `notes` field routed via Move_to_Jobs results in the target customer having that content in `internal_notes` under the three merge branches defined in Requirement 5 items 2, 3, and 4.
5. THE Platform SHALL add a backend test for Requirement 8 asserting the fold migration moves data correctly for customer and lead subject types and logs discarded sales/appointment entries.
