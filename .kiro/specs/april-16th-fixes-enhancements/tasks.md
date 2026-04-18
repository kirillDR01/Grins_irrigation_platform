# Implementation Tasks: April 16th Fixes & Enhancements

## Phase 1: Backend Schema & Model Changes (Sequential Foundation)

- [x] 1.1 Create Alembic migration for `notes` table with columns: id (uuid pk), subject_type (varchar), subject_id (uuid), author_id (uuid fk→staff), body (text), origin_lead_id (uuid nullable fk→leads), origin_appointment_id (uuid nullable fk→appointments), is_system (bool), is_deleted (bool), created_at (timestamptz), updated_at (timestamptz). Add indexes on (subject_type, subject_id), origin_lead_id, and created_at.
- [x] 1.2 Create Alembic migration for `appointment_attachments` table with columns: id (uuid pk), appointment_id (uuid), appointment_type (varchar), file_key (varchar), file_name (varchar), file_size (int), content_type (varchar), uploaded_by (uuid fk→staff), created_at (timestamptz). Add index on (appointment_type, appointment_id).
- [x] 1.3 Create `src/grins_platform/models/note.py` — SQLAlchemy `Note` model matching the migration schema, with relationships to Staff (author).
- [x] 1.4 Create `src/grins_platform/models/appointment_attachment.py` — SQLAlchemy `AppointmentAttachment` model matching the migration schema, with relationship to Staff (uploaded_by).
- [x] 1.5 Register new models in `src/grins_platform/models/__init__.py`.

## Phase 2: Backend Schema Extensions (Parallel)

- [x] 2.1 Extend `LeadUpdate` schema in `src/grins_platform/schemas/lead.py`: add optional fields `sms_consent`, `email_marketing_consent`, `terms_accepted`, `lead_source` (LeadSourceExtended), `source_site`, `source_detail`, `last_contacted_at`, `phone`, `email`, `situation` (LeadSituation). Add validator on `status` to reject values not in {new, contacted} with 422 + `lead_status_deprecated`. Add validator on `last_contacted_at` to reject future dates and dates before lead's `created_at`.
- [x] 2.2 Migrate `CustomerCreate` schema in `src/grins_platform/schemas/customer.py`: change `lead_source` from `LeadSource` to `LeadSourceExtended`. Add `is_priority: bool = False`, `is_red_flag: bool = False`, `is_slow_payer: bool = False`.
- [x] 2.3 Migrate `CustomerUpdate` schema in `src/grins_platform/schemas/customer.py`: change `lead_source` from `LeadSource` to `LeadSourceExtended`. Ensure all customer fields are present as optional patchable fields (first_name, last_name, phone, email, status, is_priority, is_red_flag, is_slow_payer, sms_opt_in, email_opt_in, lead_source, lead_source_details).
- [x] 2.4 Create `src/grins_platform/schemas/note.py` — Pydantic schemas: `NoteCreate` (body: str), `NoteUpdate` (body: str), `NoteResponse` (id, subject_type, subject_id, author_id, author_name, body, origin_lead_id, is_system, created_at, updated_at, stage_tag).
- [x] 2.5 Create `src/grins_platform/schemas/appointment_attachment.py` — Pydantic schemas: `AttachmentUploadResponse`, `AttachmentListResponse`.

## Phase 3: Backend Services (Parallel after Phase 2)

- [x] 3.1 Create `src/grins_platform/services/note_service.py` — `NoteService` with methods: `list_notes(subject_type, subject_id)` returning merged timeline (direct notes + notes linked via origin_lead_id), `create_note(subject_type, subject_id, body, author_id)`, `update_note(note_id, body, actor_id)` with author/admin check, `delete_note(note_id, actor_id)` soft-delete, `create_stage_transition_note(from_type, from_id, to_type, to_id, actor_id)`.
- [x] 3.2 Create `src/grins_platform/services/appointment_attachment_service.py` — `AppointmentAttachmentService` reusing existing S3 presign pipeline from lead attachments. Methods: `list_attachments(appointment_id, appointment_type)`, `upload_attachment(appointment_id, appointment_type, file, uploaded_by)` with 25MB size check, `delete_attachment(attachment_id, actor_id)`.
- [x] 3.3 Extend `LeadService` — Add `last_contacted_at` auto-stamp logic: on status transition to `contacted`, set `last_contacted_at = now()`. If `contacted_at` is null, also set `contacted_at = now()`. If already contacted, only update `last_contacted_at`.
- [x] 3.4 Extend `AuditService` (or create audit helper) — Add TCPA audit logging for consent field toggles on leads (sms_consent, email_marketing_consent, terms_accepted) and customers (sms_opt_in, email_opt_in). Log actor, subject, field, old_value, new_value, timestamp. Also log customer status changes and lead last_contacted_at manual edits.
- [x] 3.5 Integrate `NoteService` into lead routing actions (Move to Sales, Move to Jobs) — When routing, call `create_stage_transition_note` and set `origin_lead_id` on the new entity's notes context.

## Phase 4: Backend API Endpoints (Parallel after Phase 3)

- [x] 4.1 Create notes API endpoints in `src/grins_platform/api/v1/notes.py`: `GET /api/v1/leads/{id}/notes`, `POST /api/v1/leads/{id}/notes`, `GET /api/v1/sales/{id}/notes`, `POST /api/v1/sales/{id}/notes`, `GET /api/v1/customers/{id}/notes`, `POST /api/v1/customers/{id}/notes`, `PATCH /api/v1/notes/{id}`, `DELETE /api/v1/notes/{id}`. Register router in `router.py`.
- [x] 4.2 Create appointment attachments API endpoints in `src/grins_platform/api/v1/appointment_attachments.py`: `GET /api/v1/appointments/{id}/attachments`, `POST /api/v1/appointments/{id}/attachments`, `DELETE /api/v1/appointments/{id}/attachments/{attachment_id}`. Register router in `router.py`.
- [x] 4.3 Fix customer export endpoint in `src/grins_platform/api/v1/customers.py`: add `CurrentActiveUser` auth dependency, raise/remove 1000-row cap, add `?format=xlsx` parameter using `openpyxl`, return correct Content-Type and Content-Disposition headers. Keep CSV path for backward compatibility.
- [x] 4.4 Add lead status validation to the lead PATCH endpoint — ensure the `lead_status_deprecated` 422 is returned when status is not in {new, contacted}. Mark `POST /api/v1/leads/{id}/convert` as deprecated (keep reachable, remove UI entry points).

## Phase 5: Frontend Cleanup & Bug Fixes (Parallel)

- [x] 5.1 Lead Detail action button cleanup: delete `frontend/src/features/leads/components/EstimateCreator.tsx` and `ContractCreator.tsx`. Remove their barrel exports from `frontend/src/features/leads/index.ts`. In `LeadDetail.tsx`, remove the Create Estimate and Create Contract button blocks, remove `showEstimateCreator`/`showContractCreator` state, remove `EstimateCreator`/`ContractCreator` imports and renders, remove unused `Calculator`/`ScrollText` icon imports.
- [x] 5.2 Lead Detail status simplification: update `VALID_TRANSITIONS` map to only allow new↔contacted. Remove Convert to Customer button, Mark as Lost, Mark as Spam handlers/flags/buttons. Remove `ConvertLeadDialog` import/render and `showConvertDialog` state. Remove `canConvert`, `canMarkLost`, `canMarkSpam`, `availableTransitions` flags. Update `LeadStatusBadge` to render "Archived" for legacy statuses.
- [x] 5.3 Customer create network error fix: in `CustomerForm.tsx`, replace empty `catch {}` with `catch (err) { toast.error(..., { description: getErrorMessage(err) }) }`. Align `LEAD_SOURCES` array to match `LeadSourceExtended` membership (remove facebook, nextdoor, repeat; add social_media and remaining extended values).
- [x] 5.4 Customer search fix: add `placeholderData: keepPreviousData` to `useCustomers` hook. In `CustomerList.tsx`, gate loading screen on `isLoading && !data` instead of just `isLoading`. Hoist search input state to `CustomerList` parent and pass as controlled `value` prop to `CustomerSearch`.
- [x] 5.5 Lead list filter tab removal: remove "Schedule" and "Follow Up" entries from `INTAKE_TABS` in `LeadFilters.tsx`. If "All" is the only remaining tab, remove the tab row markup entirely. Investigate `intake_tag` readers across frontend and backend; document findings. Remove `IntakeTagBadge` from Lead detail and lead-row views if intake_tag is only surfaced via badge and removed pills.

## Phase 6: Frontend Inline Edit Sections (Parallel after Phase 5)

- [x] 6.1 Lead Detail inline edit — Contact info section: add Edit/Save/Cancel pattern for phone (required, E.164) and email (optional). PATCH via `useUpdateLead`. Toast on success. Invalidate lead query. Add `data-testid` attributes.
- [x] 6.2 Lead Detail inline edit — Service details section: add Edit/Save/Cancel for situation (enum select), source_site (free-text), lead_source (enum select matching LeadSourceExtended), source_detail (free-text), intake_tag (enum select with None option). PATCH via `useUpdateLead`.
- [x] 6.3 Lead Detail inline edit — Consent section: add Edit/Save/Cancel for sms_consent, email_marketing_consent, terms_accepted (boolean switches). PATCH via `useUpdateLead`. Display "Last changed by [actor] on [timestamp]" hint under each toggle when audit data exists.
- [x] 6.4 Lead Detail inline edit — Last Contacted section: add editable date-time picker for `last_contacted_at`. Show system-set vs manually-overridden indicator. PATCH via `useUpdateLead`. Validate not-future and not-before-created_at client-side.
- [x] 6.5 Customer Detail inline edit — Basic info section: add Edit/Save/Cancel for first_name (required), last_name (required), phone (required, 10-digit NA), email (optional). PATCH via `useUpdateCustomer`.
- [x] 6.6 Customer Detail inline edit — Primary address section: edit PATCHes the primary Property row (address, city, state, zip_code). If no primary property, show "Add primary property" affordance. PATCH via property update endpoint.
- [x] 6.7 Customer Detail inline edit — Communication preferences, lead source, flags, status sections: add Edit/Save/Cancel for sms_opt_in, email_opt_in (switches), lead_source (LeadSourceExtended select), lead_source_details (free-text), is_priority, is_red_flag, is_slow_payer (switches), status (CustomerStatus select, no transition guard). PATCH via `useUpdateCustomer`. Audit-log status changes.
- [x] 6.8 Customer Detail — Properties section: list all linked properties with primary flag. Add inline Add, Edit, Delete, "Set as primary" actions. Every property field editable (address, city, state, zip_code, gate_code, access_instructions, has_dogs, property_type, zone_count, special_notes). Block deletion of only property with active jobs (server-side error surfaced in toast).

## Phase 7: Frontend Notes & Calendar Enhancements (Parallel after Phase 6)

- [x] 7.1 Create shared `NotesTimeline` component at `frontend/src/shared/components/NotesTimeline.tsx`: renders notes newest-first with author, timestamp, body, and stage tag (Lead/Sales/Customer/Appointment). Includes "Add note" form. Supports `readOnly` and `maxEntries` props for appointment modal slice. Add `useNotes` and `useCreateNote` hooks.
- [x] 7.2 Integrate `NotesTimeline` into Lead Detail, Sales Entry Detail, and Customer Detail pages. Replace single notes field with timeline component. Wire to notes API endpoints.
- [x] 7.3 Appointment modal — Customer context block: add read-only context block to both `AppointmentForm.tsx` (job appointments) and `SalesCalendar.tsx` edit dialog (estimate appointments). Display customer name, phone (tap-to-call), primary address (maps link), job type, last_contacted_at, preferred_service_time, is_priority badge, dogs_on_property warning, gate_code, access_instructions, is_red_flag/is_slow_payer pills. Group safety warnings separately.
- [x] 7.4 Appointment modal — Source record links: add "View sales entry →" link on estimate appointments, "View customer →" link on job appointments.
- [x] 7.5 Appointment modal — File upload: add "Attach files" affordance supporting multiple files, any MIME type, 25 MB cap. Render appropriate previews (image thumbnail, PDF icon, other file icon). Reuse presign pipeline from `AttachmentPanel.tsx`. Wire to appointment attachments API.
- [x] 7.6 Appointment modal — Notes integration: display read-only NotesTimeline slice with "View full timeline →" link. New notes recorded with `subject_type: 'appointment'`.
- [x] 7.7 Calendar grid — Attachment badge: display small attachment-count badge on appointment cards that have attachments.

## Phase 8: Cross-Feature Cache Invalidation (After Phase 6)

- [x] 8.1 Create shared invalidation helpers at `frontend/src/shared/utils/invalidationHelpers.ts`: `invalidateAfterLeadRouting(queryClient, target)`, `invalidateAfterCustomerMutation(queryClient, customerId)`, and other helpers per the invalidation matrix.
- [x] 8.2 Update all mutation hooks to use the invalidation matrix: `useMoveToJobs` → add jobKeys.lists(), customerKeys.lists(), dashboardKeys.summary(). `useMoveToSales` → add salesKeys.lists(), dashboardKeys.summary(). `useMarkContacted` → add dashboardKeys.summary(). `useCreateCustomer` → add customerKeys.lists(), dashboardKeys.summary(). `useUpdateCustomer` → add customerKeys.detail(id), customerKeys.lists(). Invoice/payment mutations → add customerInvoiceKeys.byCustomer(id), dashboardKeys.summary(). Job lifecycle mutations → add jobKeys.lists(), customerKeys.detail(customerId), dashboardKeys.summary(). Sales-pipeline transitions → add salesKeys.lists(), jobKeys.lists(), customerKeys.lists().
- [x] 8.3 Configure root QueryClient with `refetchOnWindowFocus: true` and `staleTime: 30000` for list queries.

## Phase 9: Customer Export Wiring (After Phase 4)

- [x] 9.1 Add `exportCustomers` method to `frontend/src/features/customers/api/customerApi.ts` that POSTs to `/customers/export?format=xlsx` and returns response as Blob.
- [x] 9.2 Add `useExportCustomers` mutation hook. Wire Export button in `CustomerList.tsx` with onClick handler, disabled state + spinner while pending, toast on success/failure using `getErrorMessage(err)`. Trigger browser download via `URL.createObjectURL(blob)`.

## Phase 10: Sales Entry Editability (After Phase 6)

- [x] 10.1 Sales Entry Detail — Inline edit for all fields: customer name, phone, job type, last_contacted_at, pipeline stage, assigned staff, estimate amount, dates, address. Customer-sourced fields (name, phone) PATCH the underlying Customer row via `useUpdateCustomer`, not the sales entry row.
- [x] 10.2 Sales Entry Detail — Bidirectional notes: integrate NotesTimeline showing merged history from all linked stages (Lead, Sales, Appointment, Customer). New notes created with `subject_type: 'sales_entry'`.

## Phase 11: Backend Tests (After Phases 3-4)

- [x] 11.1 Create `src/grins_platform/tests/unit/test_pbt_april_16th.py` — Property-based tests using Hypothesis for Properties 1, 2, 4, 5, 6, 7, 8, 9, 10, 14, 17, 18, 19, 20. Minimum 100 iterations per property. Each test tagged with `Feature: april-16th-fixes-enhancements, Property N: description`.
  - [x] 11.1.1 Property 1: Lead field edit round-trip — generate random valid lead field updates, PATCH, GET, assert values match
  - [x] 11.1.2 Property 2: Customer field edit round-trip — generate random valid customer field updates, PATCH, GET, assert values match
  - [x] 11.1.3 Property 4: TCPA audit logging — generate random consent toggles, assert audit log created with correct fields
  - [x] 11.1.4 Property 5: Lead status restriction — generate random status values, assert 422 for non-{new, contacted} and success for valid
  - [x] 11.1.5 Property 6: Legacy status rendering — for each legacy status, assert VALID_TRANSITIONS returns empty array
  - [x] 11.1.6 Property 7: Notes creation round-trip — generate random note bodies and subject types, create and list, assert match
  - [x] 11.1.7 Property 8: Cross-stage note visibility — generate lead with N notes, route, assert merged timeline has N+1 entries
  - [x] 11.1.8 Property 9: Notes timeline ordering — generate notes with random timestamps, assert returned in descending order
  - [x] 11.1.9 Property 10: Customer create with LeadSourceExtended — generate random extended source values and flags, create, GET, assert round-trip
  - [x] 11.1.10 Property 14: Attachment upload round-trip — generate random file metadata ≤25MB, upload, list, assert match; >25MB rejected
  - [x] 11.1.11 Property 17: Last contacted auto-stamp — generate leads, transition to contacted, assert timestamps set correctly
  - [x] 11.1.12 Property 18: Last contacted validation — generate random datetimes, assert future/pre-creation rejected, valid accepted
  - [x] 11.1.13 Property 19: Primary property invariant — generate property operations, assert exactly one primary after each
  - [x] 11.1.14 Property 20: Export completeness — generate N customers, export, assert N rows with all columns
- [x] 11.2 Create `src/grins_platform/tests/functional/test_april_16th_functional.py` — Functional tests for lead edit workflow, customer edit workflow, notes timeline, customer create with all LeadSourceExtended values, export XLSX generation.
- [x] 11.3 Create `src/grins_platform/tests/integration/test_april_16th_integration.py` — Integration tests for full lead lifecycle with notes carry-forward, cross-feature cache invalidation, sales entry edit → customer row update, export auth guard.

## Phase 12: Frontend Tests (After Phases 5-10)

- [x] 12.1 Update `LeadDetail.test.tsx` — Assert only 4 action buttons render; status dropdown has 2 options; legacy statuses show "Archived"; inline edit sections render and save correctly.
- [x] 12.2 Update `CustomerDetail.test.tsx` — Assert all inline edit sections render; property management CRUD works; primary property switching works.
- [x] 12.3 Update or create `CustomerForm.test.tsx` — Assert error messages display on failure; LEAD_SOURCES matches LeadSourceExtended.
- [x] 12.4 Update `CustomerList.test.tsx` — Assert search text retained across refetch; export button triggers download.
- [x] 12.5 Create `NotesTimeline.test.tsx` — Assert notes render newest-first; stage tags display; add note form works.
- [x] 12.6 Create appointment modal tests — Assert customer context block renders all fields; file upload works; notes slice displays.
- [x] 12.7 Create frontend property-based tests using fast-check for Properties 3, 11, 12, 13, 15, 16.
