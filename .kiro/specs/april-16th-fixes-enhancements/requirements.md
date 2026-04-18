# Requirements Document

## Introduction

This document specifies the complete set of bug fixes and enhancements for the April 16th release across Lead and Customer flows in the Grins Platform CRM. The changes span frontend (React/TypeScript) and backend (Python/FastAPI) and cover: action button cleanup, inline field editability across Lead/Customer/Sales Entry/Appointment detail pages, lead status simplification, a unified notes timeline system, bug fixes for customer creation and search, cross-tab cache invalidation, calendar appointment enrichment with file uploads, customer Excel export, and filter cleanup. The customer lifecycle defined in `instructions/update2_instructions.md` and `diagrams/customer-lifecycle.excalidraw` is the authoritative process. A lead becomes a customer only through the Move to Sales / Move to Jobs routing actions.

## Glossary

- **Platform**: The Grins Platform CRM application (FastAPI backend + React frontend)
- **Lead_Detail_Page**: The frontend page at `frontend/src/features/leads/components/LeadDetail.tsx` displaying a single lead record
- **Customer_Detail_Page**: The frontend page at `frontend/src/features/customers/components/CustomerDetail.tsx` displaying a single customer record
- **Sales_Entry_Detail_Page**: The frontend page displaying a single sales pipeline entry record
- **Appointment_Modal**: The edit dialog for calendar appointments (estimate appointments via `SalesCalendar.tsx`, job appointments via `AppointmentForm.tsx`)
- **Lead_List_Page**: The frontend page at `frontend/src/features/leads/components/LeadsList.tsx` displaying the filterable list of leads
- **Customer_List_Page**: The frontend page at `frontend/src/features/customers/components/CustomerList.tsx` displaying the searchable list of customers
- **Inline_Edit_Pattern**: A UI pattern where a small Edit affordance flips a section into a form, Save writes via a PATCH mutation, Cancel reverts, and a toast confirms success
- **Notes_Timeline**: A unified, multi-subject notes system that follows the lead → sales entry → customer chain, showing author, timestamp, body, and stage tags per entry
- **TCPA_Audit_Log**: An `audit_logs` table entry capturing actor, subject, field, old value, new value, and timestamp for consent-relevant field changes
- **LeadSource_Extended**: The `LeadSourceExtended` enum at `src/grins_platform/models/enums.py` containing the canonical set of lead source values
- **Query_Invalidation**: The TanStack Query mechanism where a mutation's `onSuccess` callback calls `invalidateQueries` on every query key whose data the mutation could affect
- **Primary_Property**: The single property record per customer flagged as primary, whose address populates the Customer Detail Page address block
- **CustomerStatus**: The backend enum representing all valid customer lifecycle states
- **LeadStatus**: The backend enum for lead states; only `new` and `contacted` are valid for new writes
- **Appointment_Attachment**: A file (any MIME type, ≤25 MB) uploaded and linked to a calendar appointment record

## Requirements

### Requirement 1: Lead Detail — Action Button Cleanup

**User Story:** As an admin, I want the Lead Detail page to show only workflow-relevant action buttons, so that I am not tempted to skip the Sales pipeline by creating estimates or contracts directly from a lead.

#### Acceptance Criteria

1. THE Lead_Detail_Page SHALL display only the following action buttons: Mark as Contacted, Move to Jobs, Move to Sales, and Delete.
2. WHEN the Lead_Detail_Page renders, THE Platform SHALL NOT display a Create Estimate button or a Create Contract button.
3. WHEN the Create Estimate and Create Contract buttons are removed, THE Platform SHALL delete the orphaned component files `frontend/src/features/leads/components/EstimateCreator.tsx` and `frontend/src/features/leads/components/ContractCreator.tsx`.
4. WHEN the orphaned component files are deleted, THE Platform SHALL remove their barrel exports from `frontend/src/features/leads/index.ts`.
5. THE Platform SHALL leave `frontend/src/features/schedule/components/EstimateCreator.tsx` unmodified, as it is a separate component used by the schedule feature.
6. WHEN the buttons are removed, THE Platform SHALL remove all related state variables (`showEstimateCreator`, `showContractCreator`), imports (`EstimateCreator`, `ContractCreator`, `Calculator`, `ScrollText`), and component renders from `LeadDetail.tsx`.

### Requirement 2: Lead Detail — Editable Fields

**User Story:** As an admin, I want to edit every lead field inline on the Lead Detail page, so that I can correct or update lead data without accessing the database directly.

#### Acceptance Criteria

1. THE Lead_Detail_Page SHALL provide the Inline_Edit_Pattern for the contact information group: `phone` (required, normalized to E.164) and `email` (optional, basic email validation, allow blanking).
2. THE Lead_Detail_Page SHALL provide the Inline_Edit_Pattern for the service details group: `situation` (enum select), `source_site` (free-text), `lead_source` (enum select matching LeadSource_Extended values), `source_detail` (free-text, optional), and `intake_tag` (enum select with a None option).
3. THE Lead_Detail_Page SHALL provide the Inline_Edit_Pattern for the notes field as a multi-line textarea that allows blanking.
4. THE Lead_Detail_Page SHALL provide the Inline_Edit_Pattern for the consent group: `sms_consent` (boolean switch), `email_marketing_consent` (boolean switch), and `terms_accepted` (boolean switch).
5. WHEN an admin saves an edit in any section, THE Platform SHALL PATCH only the fields owned by that section via the existing `useUpdateLead` mutation to `PATCH /api/v1/leads/{id}`.
6. WHEN a save succeeds, THE Platform SHALL display a toast message identifying the updated section and invalidate the lead query so the page re-renders with saved values.
7. WHEN an admin toggles `sms_consent`, `email_marketing_consent`, or `terms_accepted`, THE Platform SHALL write a TCPA_Audit_Log entry capturing the actor, lead, field name, old value, new value, and timestamp.
8. WHILE a consent toggle has been audit-logged, THE Lead_Detail_Page SHALL display a "Last changed by [actor] on [timestamp]" hint under each consent toggle.
9. THE Platform SHALL verify the backend `LeadUpdate` Pydantic schema accepts `sms_consent`, `email_marketing_consent`, `terms_accepted`, `intake_tag`, `source_site`, `source_detail`, and `lead_source` as patchable optional fields, and add any that are missing.
10. THE Lead_Detail_Page SHALL expose stable `data-testid` attributes on every Edit, Save, and Cancel button and on every input field in each editable section.

### Requirement 3: Lead Detail — Status Simplification

**User Story:** As an admin, I want the lead status workflow reduced to only "Not Contacted" and "Contacted," so that the status model matches the actual lifecycle where leads are routed via Move to Sales / Move to Jobs rather than through intermediate statuses.

#### Acceptance Criteria

1. THE Lead_Detail_Page status dropdown SHALL expose only two options: "Not Contacted" (writes `status: 'new'`) and "Contacted" (writes `status: 'contacted'`).
2. THE Lead_Detail_Page SHALL NOT display a Convert to Customer button, a Mark as Lost button, or a Mark as Spam button.
3. WHEN the status dropdown is simplified, THE Platform SHALL remove all related handlers (`handleMarkLost`, `handleMarkSpam`), flags (`canConvert`, `canMarkLost`, `canMarkSpam`, `availableTransitions`), the `ConvertLeadDialog` import and render, and the `showConvertDialog` state from `LeadDetail.tsx`.
4. WHEN a lead record contains a legacy status value (`qualified`, `converted`, `lost`, `spam`), THE Lead_Detail_Page SHALL render a neutral "Archived" badge without crashing.
5. THE Lead_List_Page SHALL NOT display any filter pill, dropdown option, or bulk-action menu item for Lost or Spam statuses.
6. WHEN a PATCH request to `/api/v1/leads/{id}` sets `status` to any value other than `new` or `contacted`, THE Platform SHALL reject the request with HTTP 422 and a `lead_status_deprecated` error code.
7. THE Platform SHALL mark the `POST /api/v1/leads/{id}/convert` endpoint as deprecated, keeping it reachable to avoid 404s for in-flight automation, while removing all UI entry points.
8. THE Platform SHALL update the `VALID_TRANSITIONS` map in `LeadDetail.tsx` so that `new` transitions only to `contacted`, `contacted` transitions only to `new`, and all legacy statuses have empty transition arrays.

### Requirement 4: Lead Notes That Follow the Lead

**User Story:** As an admin, I want to add timestamped notes to a lead and have those notes persist and remain visible when the lead is routed to a Sales entry or Customer record, so that context is never lost across lifecycle stages.

#### Acceptance Criteria

1. THE Platform SHALL provide a `notes` table (or extend an existing general-purpose notes/comments table) with columns: `id` (uuid, pk), `subject_type` (enum: lead, sales_entry, customer, appointment), `subject_id` (uuid), `author_id` (uuid, fk → users), `body` (text), `created_at` (timestamptz), `updated_at` (timestamptz), and `origin_lead_id` (uuid, nullable, fk → leads).
2. THE Lead_Detail_Page SHALL display a Notes_Timeline component rendering all notes for the lead, newest-first, with each entry showing author, timestamp, and body.
3. WHEN an admin submits a new note on the Lead_Detail_Page, THE Platform SHALL create a note record via `POST /api/v1/leads/{id}/notes` with the current user as author.
4. WHEN a lead is routed via Move to Sales, THE Platform SHALL insert a system "stage transition" note on the new sales entry and make existing lead-stage notes queryable from the sales entry by joining on `origin_lead_id`.
5. WHEN a lead is routed via Move to Jobs, THE Platform SHALL make existing lead-stage notes queryable from the resulting customer record by joining on `origin_lead_id`.
6. THE Notes_Timeline SHALL visually distinguish notes by stage using small tags: "Lead", "Sales", "Customer", or "Appointment" on each entry.
7. THE Platform SHALL expose the following API endpoints: `GET /api/v1/leads/{id}/notes`, `POST /api/v1/leads/{id}/notes`, equivalent endpoints for `/api/v1/sales/{id}/notes` and `/api/v1/customers/{id}/notes` returning merged timelines when an `origin_lead_id` link exists, `PATCH /api/v1/notes/{id}` (edit, restricted to original author or admin), and `DELETE /api/v1/notes/{id}` (soft-delete recommended).
8. THE Sales_Entry_Detail_Page and Customer_Detail_Page SHALL display the same Notes_Timeline component showing the merged note history from all linked stages and accepting new entries.

### Requirement 5: Customer Detail — Editable Fields

**User Story:** As an admin, I want to edit every customer field inline on the Customer Detail page, so that I can update contact info, preferences, flags, status, and properties without accessing the database.

#### Acceptance Criteria

1. THE Customer_Detail_Page SHALL provide the Inline_Edit_Pattern for basic info: `first_name` (required), `last_name` (required), `phone` (required, normalized to 10-digit NA format), and `email` (optional, RFC 5322).
2. THE Customer_Detail_Page SHALL provide the Inline_Edit_Pattern for the primary address block, where edits PATCH the underlying Primary_Property row fields: `address`, `city`, `state`, `zip_code`.
3. IF a customer has no Primary_Property, THEN THE Customer_Detail_Page SHALL display an "Add primary property" affordance that creates a property and links it as primary.
4. THE Customer_Detail_Page SHALL provide the Inline_Edit_Pattern for communication preferences: `sms_opt_in` (boolean switch) and `email_opt_in` (boolean switch).
5. WHEN an admin toggles `sms_opt_in` or `email_opt_in`, THE Platform SHALL write a TCPA_Audit_Log entry capturing the actor, customer, field name, old value, new value, and timestamp.
6. THE Customer_Detail_Page SHALL provide the Inline_Edit_Pattern for `lead_source` (enum select matching LeadSource_Extended) and `lead_source_details` (free-text).
7. THE Customer_Detail_Page SHALL provide the Inline_Edit_Pattern for customer flags: `is_priority`, `is_red_flag`, `is_slow_payer` (boolean switches), and `custom_flags` (array).
8. THE Customer_Detail_Page SHALL provide the Inline_Edit_Pattern for `status` as a select dropdown exposing every CustomerStatus enum value with no transition guard.
9. WHEN an admin changes the customer `status`, THE Platform SHALL write an audit log entry capturing the actor, customer, old status, new status, and timestamp.
10. THE Customer_Detail_Page SHALL display a Properties section listing all linked properties, with exactly one flagged as primary.
11. THE Customer_Detail_Page SHALL provide inline Add, Edit, Delete, and "Set as primary" actions for properties, where every field on every property is editable (including `address`, `city`, `state`, `zip_code`, `gate_code`, `access_instructions`, `dogs_on_property`, `property_type`, lot size, notes, and any other column the property model exposes).
12. IF an admin attempts to delete the only property linked to a customer with active jobs or agreements, THEN THE Platform SHALL block the deletion server-side and display an error message.
13. WHEN the Primary_Property is edited, THE Customer_Detail_Page primary address block SHALL reflect the new values immediately via Query_Invalidation.
14. THE Platform SHALL verify the backend `CustomerUpdate` schema accepts every field listed above as optional and add any missing fields.

### Requirement 6: Customer Create — Network Error Fix

**User Story:** As an admin, I want customer creation to succeed regardless of which lead source I select, so that I am not blocked by a hidden enum mismatch between the frontend dropdown and the backend validation.

#### Acceptance Criteria

1. THE Platform SHALL migrate the `CustomerCreate` and `CustomerUpdate` backend schemas to validate `lead_source` against LeadSource_Extended instead of the legacy `LeadSource` enum.
2. THE Platform SHALL align the frontend `LEAD_SOURCES` dropdown in `CustomerForm.tsx` to exactly match LeadSource_Extended membership: `facebook` and `nextdoor` collapse into `social_media`, `repeat` collapses into `referral`, `yard_sign` and `other` remain as-is.
3. WHEN a customer creation or update request fails, THE Platform SHALL display the server error message in the toast notification by replacing the empty `catch {}` block in `CustomerForm.tsx` with error extraction using `getErrorMessage(err)`.
4. THE Platform SHALL add `is_priority`, `is_red_flag`, and `is_slow_payer` to the backend `CustomerCreate` Pydantic schema so these fields are persisted on creation instead of being silently dropped.
5. WHEN a customer is created with `is_priority`, `is_red_flag`, or `is_slow_payer` set, THE Platform SHALL persist those values and return them in the subsequent GET response (round-trip correctness).

### Requirement 7: Customer Search — Lag and Input Clearing Fix

**User Story:** As an admin, I want the customer search to feel responsive and retain my typed query across list refreshes, so that I can find customers without the input clearing or lagging.

#### Acceptance Criteria

1. THE Platform SHALL add `placeholderData: keepPreviousData` to the `useCustomers` TanStack Query hook so the customer list retains previous data during refetches.
2. WHEN the customer list is refetching (not initial load), THE Customer_List_Page SHALL NOT unmount the search component by returning a full-page loading screen; the loading screen SHALL only appear when there is no prior data.
3. THE Platform SHALL hoist the search input state to the `CustomerList` parent component and pass it as a controlled `value` prop to `CustomerSearch`, so the typed value survives any component remount.
4. WHEN a search query is active and the list refreshes, THE Customer_List_Page SHALL retain the user's typed search text in the input field.

### Requirement 8: Universal Editability Principle

**User Story:** As an admin, I want every field visible on a Lead, Customer, Sales Entry, Appointment, or Property detail page to be editable from that page, so that I never need direct database access to correct data.

#### Acceptance Criteria

1. THE Platform SHALL ensure that every field displayed on the Lead_Detail_Page, Customer_Detail_Page, Sales_Entry_Detail_Page, Appointment_Modal, and any property section is admin-editable using the Inline_Edit_Pattern, with the sole exceptions of derived/computed fields (e.g., `created_at`, totals, lifetime metrics) and audit-trail timestamps set by system actions.
2. WHEN a field is an exception to editability (derived or system-managed), THE Platform SHALL visually label the field as system-managed.
3. WHEN an edit is saved on any detail page, THE Platform SHALL persist the change to the correct source-of-truth database row and reflect the updated value in every other view that surfaces the same data via Query_Invalidation.


### Requirement 9: Auto-Refresh on Mutations (Cross-Tab Cache Invalidation)

**User Story:** As an admin, I want every tab and view in the app to reflect my actions immediately without a manual page refresh, so that I trust the data I see is current.

#### Acceptance Criteria

1. WHEN a mutation succeeds, THE Platform SHALL invalidate every TanStack Query cache key whose data the mutation could affect, not just queries within the same feature folder.
2. THE Platform SHALL implement the following minimum invalidation matrix:
   - `useMoveToJobs` invalidates `jobKeys.lists()`, `customerKeys.lists()`, `dashboardKeys.summary()`
   - `useMoveToSales` invalidates `salesKeys.lists()`, `dashboardKeys.summary()`
   - `useMarkContacted` invalidates `dashboardKeys.summary()`
   - `useCreateCustomer` invalidates `customerKeys.lists()`, `dashboardKeys.summary()`
   - `useUpdateCustomer` invalidates `customerKeys.detail(id)`, `customerKeys.lists()`
   - `useRecordPayment` and invoice mutations invalidate `customerInvoiceKeys.byCustomer(id)`, `dashboardKeys.summary()`
   - Job lifecycle mutations invalidate `jobKeys.lists()`, `customerKeys.detail(customerId)`, `dashboardKeys.summary()`
   - Sales-pipeline transitions invalidate `salesKeys.lists()`, and on conversion to job: `jobKeys.lists()`, `customerKeys.lists()`
3. THE Platform SHALL extract shared invalidation helpers (e.g., `invalidateAfterLeadRouting(queryClient, target)`) to centralize the invalidation matrix and keep it out of individual mutation hooks.
4. THE Platform SHALL configure the root QueryClient with `refetchOnWindowFocus: true` and `staleTime: 30000` (30 seconds) for list queries.
5. THE Platform SHALL NOT rely on polling (`refetchInterval`) as the primary freshness mechanism; polling is acceptable only as a backstop for data that changes without an in-app action.

### Requirement 10: Calendar Appointments — Richer Context, Notes, and File Upload

**User Story:** As an admin, I want the calendar appointment modal to show full customer context, link back to the source record, support file attachments of any type, and integrate with the unified notes timeline, so that the calendar is a self-sufficient daily reference surface.

#### Acceptance Criteria

**Sub-requirement 10A — Customer Context in Appointment Modal:**

1. WHEN an appointment modal opens (estimate or job class), THE Appointment_Modal SHALL display a read-only context block showing: customer name, customer phone (tap-to-call on mobile), primary address (with "Open in maps" link), job type or service description, `last_contacted_at`, `preferred_service_time` (if set), `is_priority` badge, `dogs_on_property` safety warning (visually distinctive), `gate_code`, `access_instructions`, `is_red_flag` and `is_slow_payer` warning pills, and open invoice balance summary (if cheaply derivable).
2. THE Appointment_Modal SHALL group safety/operational warnings (dogs, gate code, priority, red flag, slow payer) visually separate from biographical info (name, phone, address).

**Sub-requirement 10B — Link Back to Source Record:**

3. WHEN an estimate appointment modal opens, THE Appointment_Modal SHALL display a clickable "View sales entry →" link navigating to the corresponding Sales_Entry_Detail_Page.
4. WHEN a job appointment modal opens, THE Appointment_Modal SHALL display a clickable "View customer →" link navigating to the corresponding Customer_Detail_Page, and optionally a "View job →" link to the job detail.

**Sub-requirement 10C — File Upload on Appointments:**

5. THE Appointment_Modal SHALL provide an "Attach files" affordance supporting multiple files per appointment, accepting any MIME type, with a per-file size cap of 25 MB.
6. WHEN an image file is attached, THE Appointment_Modal SHALL render a thumbnail preview with click-to-enlarge. WHEN a PDF is attached, THE Appointment_Modal SHALL render a file-icon tile with filename and click-to-open/download. WHEN any other file type is attached, THE Appointment_Modal SHALL render a file-icon tile with filename and extension and click-to-download.
7. THE Platform SHALL persist appointment attachments server-side using the existing object store and presign flow (reusing the pipeline from `AttachmentPanel.tsx`), stored in an `appointment_attachments` table with columns: `id`, `appointment_id`, `file_key`, `file_name`, `file_size`, `content_type`, `uploaded_by`, `created_at`.
8. THE Platform SHALL expose API endpoints: `GET /api/v1/appointments/{id}/attachments`, `POST /api/v1/appointments/{id}/attachments`, and `DELETE /api/v1/appointments/{id}/attachments/{attachment_id}`.
9. WHEN an attachment is uploaded or deleted, THE Platform SHALL invalidate `appointmentKeys.detail(id)` and the calendar list query so changes appear without a manual refresh.
10. THE calendar grid SHALL display a small attachment-count badge or thumbnail strip on appointment cards that have attachments.

**Sub-requirement 10D — Notes Integration:**

11. THE Appointment_Modal SHALL display a relevant slice of the parent Notes_Timeline (read-only) with a "View full timeline →" link.
12. WHEN an admin adds a note on an appointment, THE Platform SHALL record the note with `subject_type: 'appointment'` and make it visible on the linked sales entry or customer Notes_Timeline.

### Requirement 11: Resolved Decisions (Binding Constraints)

**User Story:** As an implementer, I want a single authoritative list of all product decisions confirmed on 2026-04-16, so that I do not need to re-ask questions that have already been answered.

#### Acceptance Criteria

1. THE Platform SHALL treat the following as binding constraints during implementation:
   - Consent fields on leads are `sms_consent`, `email_marketing_consent`, and `terms_accepted`; there is no separate CallRail consent flag.
   - Historical leads in `qualified`/`converted`/`lost`/`spam` remain at their current status, rendered as "Archived" badges; no data migration is required.
   - Mark as Lost and Mark as Spam are removed at every level (detail page, list filters, bulk actions); Delete is the only removal action.
   - Universal editability (Requirement 8) applies to all detail pages.
   - Notes follow the lead → sales → customer chain (Requirement 4).
   - Auto-refresh on mutation (Requirement 9) applies to every mutation.
   - Sales entries are fully editable with bidirectional notes (Requirement 12).
   - Notes data model is implementer's choice as long as behavior matches Requirement 4.
   - Customer address comes from the Primary_Property; editing the address block PATCHes the property row.
   - Sales entry edits to customer-sourced fields (name, phone) PATCH the underlying Customer row.
   - `last_contacted_at` auto-stamps only on explicit Mark as Contacted and status dropdown change to Contacted; no auto-stamp on SMS, calls, or emails.
   - Appointment file upload accepts any MIME type ≤25 MB (Requirement 10C).
   - Calendar appointment context includes all available customer/property details (Requirement 10A).
   - Customer status is fully admin-editable with no transition guard, audit-logged (Requirement 5, group 8-9).
   - `EstimateCreator.tsx` and `ContractCreator.tsx` in leads/components are confirmed orphans after Requirement 1; delete them.
   - Customer create network error root cause is the `lead_source` enum mismatch (Requirement 6).
   - No new enum members needed for LeadSource_Extended; `facebook`/`nextdoor` → `social_media`, `repeat` → `referral`.

### Requirement 12: Sales Entry — Editability and Bidirectional Notes

**User Story:** As an admin, I want to edit every field on a Sales entry from its detail page and have notes flow bidirectionally between the Sales entry and its linked appointments, so that the Sales pipeline is a fully functional workspace.

#### Acceptance Criteria

1. THE Sales_Entry_Detail_Page SHALL provide the Inline_Edit_Pattern for every field present on the sales entry, including but not limited to: customer name, customer phone, job type/service description, `last_contacted_at`, pipeline stage, assigned staff, estimate amount, attached documents, dates, and address.
2. WHEN an admin edits a customer-sourced field (e.g., customer name, phone) from the Sales_Entry_Detail_Page, THE Platform SHALL PATCH the underlying Customer row (source-of-truth) and re-render the Sales entry with the updated value.
3. THE Platform SHALL NOT duplicate customer-sourced data onto the sales entry row; the read path SHALL join through to the canonical Customer row.
4. IF the schema currently denormalizes customer-sourced fields onto the sales entry, THEN THE Platform SHALL fix the read path to join through to the canonical row instead.
5. WHEN an admin adds a note on the Sales_Entry_Detail_Page, THE Platform SHALL make that note visible on every appointment tied to that sales entry, tagged with the Sales-stage origin.
6. WHEN an admin adds a note on an appointment, THE Platform SHALL make that note visible on the parent Sales entry, tagged with the Appointment-stage origin and an `origin_appointment_id`.
7. THE Notes_Timeline on the Sales_Entry_Detail_Page SHALL display the merged note history from all linked stages (Lead, Sales, Appointment, Customer) as a single unified timeline.

### Requirement 13: Lead "Last Contacted" — Auto-Initialized and Editable

**User Story:** As an admin, I want the "Last Contacted" timestamp to auto-populate when I mark a lead as contacted and to be manually editable with a date-time picker, so that I always have an accurate record of when a lead was last reached.

#### Acceptance Criteria

1. WHEN a lead transitions to `contacted` status via the Mark as Contacted button or the status dropdown, THE Platform SHALL set `last_contacted_at` to the current timestamp on the backend.
2. WHEN a lead transitions to `contacted` for the first time, THE Platform SHALL also set `contacted_at` to the current timestamp (only if `contacted_at` is currently null).
3. WHEN a lead that is already `contacted` is marked contacted again, THE Platform SHALL update only `last_contacted_at`, leaving `contacted_at` unchanged.
4. THE Lead_Detail_Page SHALL provide an editable "Last Contacted" field using a date-time picker (date + time, not date-only).
5. WHEN an admin manually edits `last_contacted_at`, THE Platform SHALL validate that the value is a timezone-aware ISO-8601 datetime, is not in the future, and is not before the lead's `created_at`.
6. IF a manual edit of `last_contacted_at` violates the validation rules, THEN THE Platform SHALL reject the request with HTTP 422.
7. WHEN `last_contacted_at` is manually edited, THE Platform SHALL write an audit log entry capturing the actor, lead, old value, new value, and timestamp.
8. THE Lead_Detail_Page SHALL display a small indicator next to the "Last Contacted" value showing whether it was set by the system (auto-stamp) or manually overridden by an admin.
9. WHEN `last_contacted_at` is updated (manually or via Mark as Contacted), THE Platform SHALL invalidate `leadKeys.detail(id)` and `leadKeys.lists()` so list views reflect the new value without a manual refresh.

### Requirement 14: Lead List — Remove "Schedule" and "Follow Up" Filter Tabs

**User Story:** As an admin, I want the Leads list to show only the "All" filter (or no filter tabs at all), so that the removed Schedule and Follow Up pills do not clutter the interface with unused filtering options.

#### Acceptance Criteria

1. THE Lead_List_Page SHALL NOT display "Schedule" or "Follow Up" filter pills in the `INTAKE_TABS` array.
2. IF "All" is the only remaining tab option, THEN THE Platform SHALL remove the tab row markup entirely and render the unfiltered list directly.
3. WHEN the filter pills are removed, THE Platform SHALL investigate all readers of `intake_tag` across frontend and backend (including `FollowUpQueue.tsx`, backend lead-routing logic, and reporting surfaces) and document findings before removing the field itself.
4. IF `intake_tag` is only surfaced via the badge and the now-removed pills, THEN THE Platform SHALL retire the `IntakeTagBadge` from Lead detail and lead-row views and remove `intake_tag` from the editable fields in Requirement 2, leaving the database column for a follow-up migration.
5. IF `FollowUpQueue` or backend routing depends on `intake_tag`, THEN THE Platform SHALL keep the field internally but remove the badge and editable surface from the admin UI.

### Requirement 15: Customers — Wire Up Export Button (Excel)

**User Story:** As an admin, I want the Export button on the Customers tab to download an Excel file containing all customers, so that I can work with customer data in a spreadsheet.

#### Acceptance Criteria

1. WHEN an admin clicks the Export button on the Customer_List_Page, THE Platform SHALL trigger a download of an XLSX file containing all customers.
2. THE Platform SHALL add `CurrentActiveUser` auth dependency to the `export_customers` backend endpoint so that unauthenticated requests return HTTP 401.
3. THE Platform SHALL raise or remove the current 1,000-row cap on the export endpoint so that all customers can be exported.
4. THE Platform SHALL accept a `?format=xlsx` query parameter on the export endpoint and generate the workbook using `openpyxl`, returning `Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` and `Content-Disposition: attachment; filename=customers-YYYY-MM-DD.xlsx`.
5. THE exported XLSX SHALL include every column visible in the Customers list view: name, phone, email, lead source, status, primary address, `is_priority`, `is_red_flag`, `is_slow_payer`, `created_at`, and `last_contacted_at`.
6. THE Platform SHALL keep the existing CSV export path available for backward compatibility with scripted or API consumers.
7. WHEN the export is in progress, THE Customer_List_Page SHALL disable the Export button and display a spinner.
8. WHEN the export succeeds, THE Platform SHALL trigger a browser download via `URL.createObjectURL(blob)` with the filename from the `Content-Disposition` header or a client-built fallback.
9. IF the export fails, THEN THE Platform SHALL display the server error message in a toast notification using the `getErrorMessage(err)` pattern.
10. THE Platform SHALL export all customers regardless of active list filters (matching the user's stated intent of "export all").

### Requirement 16: Open Questions

**User Story:** As an implementer, I want confirmation that all product questions have been resolved, so that I can proceed with implementation without ambiguity.

#### Acceptance Criteria

1. THE Platform SHALL treat all 18 resolved decisions in Requirement 11 as binding and implementation-ready.
2. THE only remaining open question is whether `facebook` and `nextdoor` should be added to LeadSource_Extended as distinct values or collapsed into `social_media`. THE resolved decision (Requirement 11, item 18) confirms they collapse into `social_media`; no new enum members are needed.
