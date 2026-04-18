# April 16th Bug Fixes and Enhancements

**Date:** 2026-04-16
**Area:** Frontend / Leads + Customers (with backend follow-ups)

This document is the **requirements list** for 2026-04-16 bug fixes and
enhancements across the Lead and Customer flows. It is intentionally a
spec only — no source code changes are made by this document. Engineers
picking up the work should treat each section as the canonical
requirement.

The customer lifecycle defined in `instructions/update2_instructions.md`
and the `diagrams/customer-lifecycle.png` (source:
`diagrams/customer-lifecycle.excalidraw`) is the authoritative process.
A lead becomes a customer **only** through the Move to Sales / Move to
Jobs routing actions. Every change below either supports that flow or
removes legacy paths that contradict it.

## Contents

1. [Lead Detail — Action Button Cleanup](#1-lead-detail--action-button-cleanup)
2. [Lead Detail — Editable Fields](#2-lead-detail--editable-fields)
3. [Lead Detail — Status Simplification](#3-lead-detail--status-simplification)
4. [Lead Notes That Follow the Lead](#4-lead-notes-that-follow-the-lead)
5. [Customer Detail — Editable Fields](#5-customer-detail--editable-fields)
6. [Customer Create — Network Error Investigation](#6-customer-create--network-error-investigation)
7. [Customer Search — Lag and Input Clearing](#7-customer-search--lag-and-input-clearing)
8. [Universal Editability Principle](#8-universal-editability-principle)
9. [Auto-Refresh on Mutations (Cross-Tab Cache Invalidation)](#9-auto-refresh-on-mutations-cross-tab-cache-invalidation)
10. [Calendar Appointments — Richer Context, Notes, and Image Upload](#10-calendar-appointments--richer-context-notes-and-image-upload)
11. [Resolved Decisions](#11-resolved-decisions)
12. [Sales Entry — Editability and Bidirectional Notes](#12-sales-entry--editability-and-bidirectional-notes)
13. [Lead "Last Contacted" — Auto-Initialized and Editable](#13-lead-last-contacted--auto-initialized-and-editable)
14. [Lead List — Remove "Schedule" and "Follow Up" Filter Tabs](#14-lead-list--remove-schedule-and-follow-up-filter-tabs)
15. [Customers — Wire Up the Export Button (Excel)](#15-customers--wire-up-the-export-button-excel)
16. [Open Questions for the User](#16-open-questions-for-the-user)

---

## 1. Lead Detail — Action Button Cleanup

**Type:** UI enhancement

### Summary

On the Lead Detail page (e.g. the Patty Becker lead view), the top-right
action bar currently shows six buttons. Trim it to four. Remove the two
estimate/contract creation entry points that no longer belong in the
lead-stage workflow.

### Current state (screenshot reference: 2026-04-16 7:06 PM)

Buttons visible at the top of the Lead Detail page:

1. Mark as Contacted
2. Move to Jobs
3. Move to Sales
4. Create Estimate (blue outline)
5. Create Contract (purple outline)
6. Delete (red)

### Desired state

Only the following four buttons should remain:

1. Mark as Contacted
2. Move to Jobs
3. Move to Sales
4. Delete

### Buttons to remove

- **Create Estimate** — the blue outlined button with the calculator icon.
- **Create Contract** — the purple outlined button with the scroll icon.

### Rationale

Estimates and contracts belong to the Sales pipeline stage, not the Lead
stage. A lead should be routed (Mark Contacted / Move to Jobs / Move to
Sales) or removed (Delete) — not jumped straight into estimate/contract
creation from the lead view. Having those two buttons here invites users
to skip the Sales pipeline and create artifacts before the lead is
properly qualified.

### Implementation notes

File: `frontend/src/features/leads/components/LeadDetail.tsx`

- Remove the two `<Button>` blocks at lines ~350–367 (the Create Estimate
  and Create Contract buttons).
- Remove the `EstimateCreator` and `ContractCreator` component renders at
  the bottom of the file (lines ~792–793).
- Remove the related `useState` calls: `showEstimateCreator` and
  `showContractCreator` (lines ~121–122).
- Remove the imports for `EstimateCreator` and `ContractCreator` (lines
  ~77–78), and the now-unused `Calculator` and `ScrollText` icons from
  the `lucide-react` import block (lines ~38–39).
- **Delete the orphaned creator components** in the same change.
  Investigation (2026-04-16) confirms both files are only imported by
  `LeadDetail.tsx`, so after the button removal they have zero
  consumers:
  - `frontend/src/features/leads/components/EstimateCreator.tsx` — delete.
  - `frontend/src/features/leads/components/ContractCreator.tsx` — delete.
  - Remove their barrel exports at
    `frontend/src/features/leads/index.ts:15-16`.
  - **Do not touch** `frontend/src/features/schedule/components/EstimateCreator.tsx`
    — that's a separate, parallel component used by the schedule feature
    (`AppointmentDetail.tsx`). The two share a name but live in
    different folders and serve different surfaces.
- Update any LeadDetail tests that assert on the `create-estimate-btn` or
  `create-contract-btn` test IDs.

---

## 2. Lead Detail — Editable Fields

**Type:** UI enhancement

Currently only the address block is editable inline. Extend the Lead
Detail page so admins can edit every piece of lead data without going to
the database. Each field group should follow the same pattern already
used for the address block: a small Edit affordance flips the section
into a form, Save writes via the existing `useUpdateLead` mutation
(PATCH `/api/v1/leads/{id}`), and Cancel reverts.

### Editable groups

1. **Contact information**
   - `phone` (string, required, normalized to E.164 on save — reuse the
     same regex as `CreateLeadDialog`)
   - `email` (string, optional, basic email validation; allow blanking)

2. **Address** (already editable — leave as-is)
   - `address`, `city`, `state`, `zip_code`

3. **Service details**
   - `situation` (enum: `new_system`, `upgrade`, `repair`, `exploring`,
     `winterization`, `seasonal_maintenance`) — Select dropdown using
     the existing situation labels.
   - `source_site` (free-text string)
   - `lead_source` (enum: `website`, `google_form`, `phone_call`,
     `text_message`, `google_ad`, `social_media`, `qr_code`,
     `email_campaign`, `text_campaign`, `referral`, `other`) — Select.
   - `source_detail` (free-text, optional)
   - `intake_tag` (enum: `schedule`, `follow_up`, or null) — Select with
     a "None" option.

4. **Notes**
   - `notes` (multi-line textarea, optional, allow blanking). See
     Section 4 for the requirement that these notes persist through
     the lead → sales → customer transition.

5. **Consent status** (the three consents tracked on the lead — no
   separate CallRail flag; `sms_consent` is what gates CallRail
   outbound)
   - `sms_consent` (boolean) — Switch
   - `email_marketing_consent` (boolean) — Switch
   - `terms_accepted` (boolean) — Switch (the "Terms and Conditions"
     consent)

### Implementation notes

- Use the existing `useUpdateLead` hook (already imported in
  `LeadDetail.tsx`) for every save. Each section can PATCH only the
  fields it owns.
- Backend `LeadUpdate` Pydantic schema already accepts most of these
  fields — verify in `backend/app/schemas/lead.py` (or wherever the
  schema lives) and add any missing fields. In particular confirm
  `sms_consent`, `email_marketing_consent`, `terms_accepted`,
  `intake_tag`, `source_site`, `source_detail`, and `lead_source` are
  patchable. Add them if they aren't.
- Toast on success ("Contact info updated", "Consent updated", etc.)
  using the same `sonner` pattern already in the file.
- Invalidate the lead query on success so the page re-renders with the
  saved values.
- Each editable section should expose stable `data-testid` attributes
  on its Edit / Save / Cancel buttons and on each input so we can write
  tests.

### Audit / TCPA consideration

Toggling `sms_consent` or `terms_accepted` is TCPA-relevant. When an
admin flips either of these, the backend must write an `AuditLog` entry
capturing the actor, the lead, the field, the old value, the new value,
and a timestamp. Reuse the same audit pattern used elsewhere
(`audit_logs` table). Surface a small "Last changed by ___ on ___"
hint under each consent toggle.

---

## 3. Lead Detail — Status Simplification

**Type:** Workflow correction (frontend + backend follow-up)

The Change Status dropdown on the right side of the Lead Detail page
currently exposes the full status machine. Per the lifecycle diagram,
a Lead has only two meaningful states from the admin's perspective:

- **Not contacted** (default, what we currently call `new`)
- **Contacted** (what we currently call `contacted`)

All other statuses must be removed from the lead workflow:

- ❌ `qualified` — not part of the lifecycle. A lead either gets routed
  (Move to Sales / Move to Jobs) or it doesn't.
- ❌ `converted` — conversion happens implicitly via Move to Sales /
  Move to Jobs. There is no separate "converted" lead state.
- ❌ Mark as Lost / Mark as Spam buttons — out of scope for the new
  flow. Removing a lead is a Delete action; there is no "lost" or
  "spam" intermediate state.

### Frontend changes (`LeadDetail.tsx` and supporting files)

- Change Status dropdown options collapse to only:
  - "Not Contacted" (writes `status: 'new'`)
  - "Contacted" (writes `status: 'contacted'`)
- Remove the **Convert to Customer** button (the teal `canConvert`
  block at lines ~340–349).
- Remove the **Mark as Lost** and **Mark as Spam** action paths from
  the Lead Detail page entirely (handlers `handleMarkLost`,
  `handleMarkSpam`, the `canMarkLost` / `canMarkSpam` flags, and the
  buttons that render them).
- Remove the `ConvertLeadDialog` import + render and the
  `showConvertDialog` state.
- Remove the `canConvert` and `availableTransitions` flags now that the
  status machine is binary.
- Update the `VALID_TRANSITIONS` map at lines 84–91 to only:
  ```ts
  const VALID_TRANSITIONS: Record<LeadStatus, LeadStatus[]> = {
    new: ['contacted'],
    contacted: ['new'],
    // legacy values kept on the type until the backend enum is narrowed:
    qualified: [],
    converted: [],
    lost: [],
    spam: [],
  };
  ```
  (or, preferably, narrow `LeadStatus` itself to `'new' | 'contacted'`
   once the backend cleanup below lands.)
- Update `LeadStatusBadge` so any legacy status value coming from old
  rows still renders without crashing — fall back to a neutral
  "Archived" pill or similar.
- Audit `LeadsList`, `LeadConversionConflictModal`, and any other
  caller of the old statuses to remove dead code paths. The CR-6
  duplicate-conflict modal must continue to work for Move to
  Sales / Move to Jobs (those are still valid actions).
- **Remove every UI surface that filters or bulk-acts on Lost / Spam.**
  Specifically: any list-level Lost / Spam filter pill or dropdown
  option in `LeadsList`, and any bulk-action menu items that mark
  selected leads as Lost or Spam. Confirmed by the user — Delete is
  the only removal action; Lost and Spam are no longer part of the
  flow at any level.

### Backend changes (defer to a follow-up commit if needed)

- The `LeadStatus` Postgres enum currently includes `qualified`,
  `converted`, `lost`, `spam`. Do **not** drop those values from the
  enum yet — existing rows may still hold them. Instead:
  1. Narrow the `LeadUpdate` schema validation so PATCH requests can
     only set `status` to `new` or `contacted`. Reject the others with
     422 + a `lead_status_deprecated` error code.
  2. Mark the convert-to-customer endpoint
     (`POST /api/v1/leads/{id}/convert`) as deprecated. Keep it
     reachable so any in-flight automation doesn't 404, but remove its
     UI entry points. Schedule actual removal for a later sweep.
  3. Add a one-shot migration plan (not run yet) to remap any
     historical `qualified`/`converted` rows to `new` once we've
     confirmed nothing reads from them.
- Add a regression test asserting that PATCH `/api/v1/leads/{id}` with
  `status: 'qualified'` returns 422.

### Tests to update / add

- `LeadDetail.test.tsx`: drop tests asserting on the qualify/convert
  buttons; add tests for each new editable section's save path; add a
  test that the status dropdown only renders the two new options.
- `useLeadRoutingActions.test.tsx`: no change expected (it already
  covers Mark Contacted / Move to Jobs / Move to Sales / Delete).
- Backend lead-update tests: assert 422 on legacy status writes.

---

## 4. Lead Notes That Follow the Lead

**Type:** Feature (UI + data persistence)

### Requirement

Admins must be able to add notes to a lead at any point in its
lifecycle. When that lead is routed forward — Move to Sales (becomes a
sales-pipeline entry) or Move to Jobs (becomes a customer + job) — the
notes must travel with it. The notes should remain visible and editable
on the resulting Sales pipeline entry and on the resulting Customer
record.

### UX

- On the Lead Detail page, the Notes section (already covered as an
  editable field in Section 2) must support multi-line free-text and
  multiple sequential notes (a notes timeline) — not just a single
  field that overwrites prior content.
- Each note entry should capture: author (current user), timestamp, and
  body. Render newest-first.
- On the resulting Sales entry and Customer detail page, the same notes
  timeline must be visible and continue to accept new entries. New
  entries added on the customer record persist back to the same
  underlying note history.
- Visual distinction: show which notes were added during the Lead
  stage vs the Sales stage vs the Customer stage (a small "Lead",
  "Sales", "Customer" tag on each entry).

### Data model

The current `Lead.notes` column is a single nullable string. That isn't
sufficient — it forces overwrites and has no author/timestamp metadata.
The recommended approach:

- Introduce a `notes` table (or reuse an existing one if there is a
  general-purpose notes/comments table — investigate before creating a
  new one) with columns:
  - `id` (uuid, pk)
  - `subject_type` (enum: `lead`, `sales_entry`, `customer`)
  - `subject_id` (uuid, fk depending on subject_type)
  - `author_id` (uuid, fk → users)
  - `body` (text)
  - `created_at` (timestamptz)
  - `updated_at` (timestamptz)
  - `origin_lead_id` (uuid, nullable, fk → leads) — the lead the note
    started on, so notes carry forward across stage changes.
- When a lead is routed via Move to Sales / Move to Jobs, the routing
  action should:
  - For Move to Sales: insert a "stage transition" system note on the
    new sales entry referencing the lead, then make the existing
    lead-stage notes queryable from the sales entry by joining on
    `origin_lead_id`.
  - For Move to Jobs: same, but the resulting customer record is the
    new subject.
- Alternative (simpler, less ideal): keep `Lead.notes` as the canonical
  store and copy the string into `Customer.notes` / sales-entry notes
  on routing. This loses author/timestamp granularity and breaks
  edit-after-routing. Only consider if the schema change above is too
  expensive.

### API surface

- `GET /api/v1/leads/{id}/notes` — list notes attached to the lead
  (and, if the lead has been routed, any notes on the downstream
  sales entry / customer that share `origin_lead_id`).
- `POST /api/v1/leads/{id}/notes` — append a new note.
- Equivalent endpoints for `/api/v1/sales/{id}/notes` and
  `/api/v1/customers/{id}/notes` that return the same merged timeline
  when an `origin_lead_id` link exists.
- `PATCH /api/v1/notes/{id}` — edit a note (only the original author
  or an admin role).
- `DELETE /api/v1/notes/{id}` — soft-delete (or hard, depending on
  audit requirements; recommend soft to preserve history).

### Frontend wiring

- Replace the single "Notes" field on Lead Detail / Customer Detail /
  Sales entry with a `<NotesTimeline>` component that renders the
  merged history and exposes an "Add note" form.
- When viewing the Customer record for a customer that originated as a
  lead, the timeline shows the original lead notes inline — labeled
  with their original Lead stage.

### Data-model latitude

Implementer's call. If the codebase already has a generic `comments` /
`notes` table that fits the requirements above (one timeline,
multi-subject, author + timestamp + body, supports `origin_lead_id`-
style cross-stage threading), extend it. If not, build the table per
the schema above. Either way, the requirements in this section are
binding — the table choice is not.

---

## 5. Customer Detail — Editable Fields

**Type:** UI enhancement (mirrors Section 2 for customers)

The Customer detail page today does not let admins edit basic customer
data inline. Specifically the user reports being unable to update:

- Contact information: `phone`, `email`
- Address fields
- Communication preferences (`sms_opt_in`, `email_opt_in`, plus any
  marketing consent flags)
- `lead_source`

All of these — and any other field present on the Customer record —
must become editable from the Customer detail page using the same
inline-edit pattern proposed for Leads (Edit affordance per section,
Save / Cancel, toast on success, query invalidation on success).

### Editable groups (Customer detail page)

1. **Basic info**
   - `first_name` (required)
   - `last_name` (required)
   - `phone` (required, validated + normalized to 10-digit NA format
     by the backend `normalize_phone` validator already in
     `src/grins_platform/schemas/customer.py`)
   - `email` (optional, RFC 5322 via `EmailStr`)

2. **Primary Address** (sourced from the customer's primary property)
   - The "Address" field shown on the customer detail page is the
     address of the customer's **primary** property — not a separate
     column on `customers`. Editing this field PATCHes the underlying
     primary property row.
   - Fields editable here: `address`, `city`, `state`, `zip_code`.
   - If the customer has no primary property yet, the section shows an
     "Add primary property" affordance that creates one and links it.
   - See the new **Properties** group (#7 below) for managing the full
     property list and switching which property is primary.

3. **Communication preferences**
   - `sms_opt_in` (boolean) — Switch
   - `email_opt_in` (boolean) — Switch
   - Surface and write any TCPA audit metadata the same way as
     leads (Section 2 audit requirement).

4. **Lead source**
   - `lead_source` (enum: `LeadSource` — same values as the lead's
     `lead_source`). Select dropdown.
   - `lead_source_details` (free-text or structured, depending on
     what the existing schema accepts).

5. **Customer flags**
   - `is_priority`, `is_red_flag`, `is_slow_payer` — Switches.
   - `custom_flags` array (already partially supported on the
     frontend; confirm backend acceptance — see Section 6's
     investigation note about extra fields the FE currently sends
     that the BE schema may not declare).

6. **Status / lifecycle**
   - `status` (enum: `CustomerStatus`) — Select. Admins can flip the
     status manually to **any** value in the enum (confirmed by the
     user). The dropdown should expose every `CustomerStatus` value
     with no transition guard. Backend should accept any value-to-
     value transition. Audit-log every manual change (actor, customer,
     old → new value, timestamp) since lifecycle changes are
     consequential.

7. **Properties** (multiple addresses per customer)
   - A customer can have one or more linked properties. Each property
     appears in a Properties section on the customer detail page,
     listed under the Primary Address block.
   - Exactly one property per customer is flagged **primary**. The
     primary property's address is what populates the "Primary
     Address" block in #2. Promoting a secondary property to primary
     is an admin-editable action (`Set as primary` button on each
     non-primary row).
   - **Every field on every property is editable from this section**,
     including but not limited to: `address`, `city`, `state`,
     `zip_code`, `gate_code`, `access_instructions`,
     `has_dogs`/`dogs_on_property`, `property_type`, lot size, notes,
     and any other column the property model exposes.
   - Add / Edit / Delete property actions all available inline. Adding
     a property opens an inline form; editing flips a row into edit
     mode; deleting a property prompts a confirmation (and is blocked
     server-side if the property is the only one and the customer has
     active jobs/agreements tied to it).
   - When a non-primary property is edited, the "Primary Address"
     block in #2 does **not** change. When the primary property is
     edited, the Primary Address block reflects the new value
     immediately (Section 9 invalidation).
   - Backend: every property field must be patchable via
     `PATCH /api/v1/properties/{id}` (or whatever the existing route
     is — verify and extend the schema if any field is currently
     read-only).

### Implementation notes

- Use a `useUpdateCustomer` mutation hook (already exists at
  `frontend/src/features/customers/hooks/useCustomerMutations.ts`) for
  every save. Each section can PATCH only the fields it owns by
  calling `customerApi.update(id, partial)`.
- Verify the backend `CustomerUpdate` schema (in
  `src/grins_platform/schemas/customer.py`) accepts every field above
  as optional. Add any missing optional fields.
- If address fields actually live on the Property model, route the
  address edit through the property-update endpoint instead, and reuse
  the existing PUT path the property feature already exposes.
- Cross-check Section 6 — extra-field bleed (FE sends fields the BE
  doesn't declare) must be cleaned up before adding more editable
  fields, or the same mismatch will multiply.

### Audit / TCPA consideration

`sms_opt_in` and `email_opt_in` are TCPA-relevant on customers exactly
the same way `sms_consent` is on leads. Same audit-log requirement
applies — write an `audit_logs` row on every toggle.

---

## 6. Customer Create — Network Error (Root Cause Confirmed)

**Type:** Bug fix (root cause confirmed via code investigation
2026-04-16)

### Reported symptom

When an admin opens the Customers tab → "Create Customer" → fills the
form → submits, the request fails. The toast shown to the user is the
generic "Failed to create customer" message produced by the empty
`catch {}` in `frontend/src/features/customers/components/CustomerForm.tsx:168`.
The user describes this as a "network error."

### Confirmed root cause: `lead_source` enum mismatch

The frontend `CustomerForm.tsx` `LEAD_SOURCES` list (lines 59-68)
exposes 8 dropdown options:

```ts
{ value: 'website',   label: 'Website' },
{ value: 'google',    label: 'Google' },
{ value: 'referral',  label: 'Referral' },
{ value: 'facebook',  label: 'Facebook' },
{ value: 'nextdoor',  label: 'Nextdoor' },
{ value: 'yard_sign', label: 'Yard Sign' },
{ value: 'repeat',    label: 'Repeat Customer' },
{ value: 'other',     label: 'Other' },
```

The backend `CustomerCreate` schema validates `lead_source` against
the `LeadSource` enum at
`src/grins_platform/models/enums.py:36-46`, which only has 5 values:

```python
class LeadSource(str, Enum):
    WEBSITE = "website"
    GOOGLE = "google"
    REFERRAL = "referral"
    AD = "ad"
    WORD_OF_MOUTH = "word_of_mouth"
```

**Five of the eight FE options are not in the BE enum**: `facebook`,
`nextdoor`, `yard_sign`, `repeat`, `other`. Selecting any of those
produces a 422 from Pydantic on the `lead_source` field. That's a
~62% failure rate purely from the dropdown.

The 422 is masked from the user as a generic "Failed to create
customer" toast because `CustomerForm.tsx:168` discards error details
in an empty `catch {}`, which is why the user described the symptom
as a "network error."

There's also a parallel `LeadSourceExtended` enum in the same file
(`enums.py:392-409`) with 12 values — this is the wider, newer set
the frontend is implicitly designed against. The customer-create
schema was never migrated to use it.

### Required fix

1. **Backend schema fix (the substantive fix).** Migrate
   `CustomerCreate` (and `CustomerUpdate`) in
   `src/grins_platform/schemas/customer.py` to validate `lead_source`
   against `LeadSourceExtended`, not the legacy `LeadSource`. This
   matches the lead-side semantics and the wider FE option list.
   - Update the import on `customer.py:18` from `LeadSource` to
     `LeadSourceExtended`.
   - Backfill: confirm no existing customer rows hold a value the
     widened enum would reject. (It's a pure superset where it
     overlaps, so existing rows should be safe.)
   - Reconcile FE `LEAD_SOURCES` so its values exactly match
     `LeadSourceExtended` membership. **Investigation 2026-04-16
     confirms the lead-intake side never collected `facebook` /
     `nextdoor` / `repeat` distinctly** — the strings exist in
     exactly one file (`CustomerForm.tsx:59-68`), not in either
     backend enum, not in the lead form, not in `LEAD_SOURCE_LABELS`,
     and not in any lead-side analytics. The lead system buckets all
     social channels into `social_media`. So:
     - `facebook` → drop, use `social_media`.
     - `nextdoor` → drop, use `social_media`.
     - `yard_sign` → already in `LeadSourceExtended`, keep as-is.
     - `repeat` → drop, use `referral` (or `other` if the product
       genuinely wants a "repeat customer" flag, but that's a
       separate concept that belongs on the customer record, not
       in the lead-source channel).
     - `other` → already in `LeadSourceExtended`, keep as-is.
   - Net result: the customer-create dropdown matches the
     `LeadSourceExtended` enum exactly, every lead-source value used
     anywhere in the system is consistent, and any analytics that
     group by source no longer has divergent customer-side strings
     to reconcile.
2. **Always-do fix (error surfacing).** Replace the empty
   `catch {}` at `CustomerForm.tsx:168` with:
   ```ts
   } catch (err) {
     toast.error(isEditing ? 'Failed to update customer' : 'Failed to create customer', {
       description: getErrorMessage(err),
     });
   }
   ```
   so future server errors surface their actual messages. This is
   small, safe, and would have made the original bug self-diagnosing.
3. **Schema alignment cleanup (data-loss bug, separate from the
   network error).** The FE `CustomerCreate` type
   (`frontend/src/features/customers/types/index.ts:172-183`) sends
   `is_priority`, `is_red_flag`, and `is_slow_payer`, none of which
   are in the BE `CustomerCreate` Pydantic schema. Pydantic v2's
   default `extra='ignore'` silently drops them, so customers are
   created with those flags lost. Add the three fields to the BE
   `CustomerCreate` schema (they're already on the model and on
   `CustomerUpdate`). This isn't the cause of the 422 — but it IS
   a data-loss bug worth fixing in the same change.

### Tests to add

- `POST /api/v1/customers` with `lead_source: 'facebook'`:
  before fix → 422; after fix → 201 (or 422 with a clear message
  if `facebook` is intentionally not supported).
- A FE test that submits the form with each `LEAD_SOURCES` value and
  asserts no toast error fires.
- A FE test that confirms `is_priority`, `is_red_flag`, and
  `is_slow_payer` round-trip (set on create → present in the GET
  response).

### Other candidate causes (unlikely, but verify if the lead_source fix doesn't resolve it)

- **Phone validation 400 (DuplicateCustomerError)** — the BE returns
  400 if the phone already exists for an active customer
  (`customers.py:141-151`). Possible if the admin reused a phone
  number already in the dev DB.
- **Phone normalization edge case** — the BE
  `normalize_phone` validator (`customer.py:24-47`) requires exactly
  10 digits (or 11 with a leading 1). The FE accepts 10–20 chars
  matching `/^[\d\s\-()]+$/`. A submission like
  `(555) 123-4567 ext. 99` would pass FE Zod and fail BE validation.
- **Auth 401** — `CurrentActiveUser` dependency rejects
  unauthenticated or inactive sessions; expired session → 401.
- **CORS / wrong API base URL** — if `VITE_API_URL` points at the
  wrong host, fetch fails before getting an HTTP response. This is
  the only candidate that produces a true browser-level "network
  error" with no HTTP status.

---

## 7. Customer Search — Lag and Input Clearing

**Type:** Bug fix (root cause confirmed)

### Reported symptoms

1. Typing a name into the customer search is laggy / not smooth.
2. Search "starts halfway through" — i.e. only fires after some
   characters are dropped.
3. The text in the search input is wiped after the list refreshes —
   what the admin typed disappears mid-typing.

### Confirmed root cause

File: `frontend/src/features/customers/components/CustomerList.tsx:248-249`

```tsx
if (isLoading) {
  return <LoadingPage message="Loading customers..." />;
}
```

Combined with `useCustomers` at `frontend/src/features/customers/hooks/useCustomers.ts:36-41`,
which has **no `placeholderData` / `keepPreviousData` option**, this
produces the following cascade on every keystroke:

1. User types a character → `CustomerSearch`'s local debounced value
   updates after 300ms.
2. `CustomerSearch`'s `useEffect` calls `onSearch(debouncedValue)` →
   parent `setSearchQuery(...)` → parent re-renders with new
   `searchQuery`.
3. New `searchQuery` is added to the `useCustomers` query params, so
   `customerKeys.list(params)` produces a new query key.
4. React Query treats this as a brand new query: `data` becomes
   `undefined` and `isLoading` flips to `true`.
5. `CustomerList` returns `<LoadingPage>` early — **the entire
   `<CustomerSearch>` component unmounts**.
6. When the query resolves, `CustomerSearch` remounts fresh with
   `initialValue=''` (the default — `CustomerList` never passes a
   value through to it), wiping the user's typing.

Net effect:
- "Lag" = the 300ms debounce.
- "Starts halfway" = the user's first burst of characters survives
  until debounce fires; everything after that point is wiped on the
  unmount.
- "Clears on refresh" = the unmount → remount cycle on every
  successful query refresh.

### Required fix

1. **Add `placeholderData: keepPreviousData`** to the `useCustomers`
   hook so the list doesn't drop into the loading branch on every
   refetch:
   ```ts
   import { useQuery, keepPreviousData } from '@tanstack/react-query';
   // ...
   return useQuery({
     queryKey: customerKeys.list(params),
     queryFn: () => customerApi.list(params),
     placeholderData: keepPreviousData,
   });
   ```
2. **Stop returning `<LoadingPage>` for refetches** — only show the
   loading screen on the first load (when there is no prior data).
   With `placeholderData` set, gate the early return on
   `isLoading && !data` (or equivalently `isPending`).
3. **Hoist the debounce / search state to the parent** so even if
   `CustomerSearch` did unmount, the typed value would survive. The
   simplest change: `CustomerList` owns the raw input value, and
   passes it as a controlled `value` prop down to `CustomerSearch`,
   with the debounced derivative used only for the query param.
4. **Optional but recommended**: persist the search query into the
   URL (e.g. `?q=patty`) so reloads and back-button navigation
   preserve the search.
5. **Consider raising the debounce to 400-500ms** if the perceived
   "lag" persists after the unmount fix. The unmount/remount cycle is
   probably what the user is calling "lag," not the debounce itself.

### Tests to add

- A `CustomerList` test that renders the component, types into the
  search, lets the query settle, and asserts the input value is still
  visible after the list refreshes.
- A `useCustomers` test confirming `placeholderData` is set so prior
  data is retained across refetches.

---

## 8. Universal Editability Principle

**Type:** Cross-cutting requirement

Anything visible on a Lead detail page or a Customer detail page
should be editable from that page by an admin. If a field is read-only
today, that's a gap to close — not a design decision.

This applies to (non-exhaustive):

- Every field listed in Section 2 (Lead) and Section 5 (Customer).
- Any property-level fields surfaced on Customer detail (gate code,
  access instructions, dogs flag, etc.) — confirm whether those PATCH
  the property or the customer.
- Any preference / consent toggle.
- Any tag / flag / status displayed on the page.

The only exceptions are derived/computed fields (e.g. `created_at`,
totals, lifetime metrics) and audit-trail fields (e.g.
`last_contacted_at` set by system actions). Those should be visibly
labeled as system-managed.

When a future spec mentions a field on either page, the default
assumption is that it must be editable unless explicitly carved out as
an exception.

---

## 9. Auto-Refresh on Mutations (Cross-Tab Cache Invalidation)

**Type:** Cross-cutting bug fix + requirement

### Reported symptom

When the admin performs an action that changes data in another tab —
e.g. clicks **Move to Jobs** on a Lead — the source tab (Leads list)
updates, but the **Jobs** tab still shows the old data. The admin has
to do a full browser refresh to see the new job appear. Same issue
when **Move to Sales** is clicked: the Sales pipeline tab doesn't
reflect the new entry without a full page reload. Same class of issue
applies to any mutation that affects multiple lists across the app.

### Confirmed root cause

The TanStack Query mutation hooks today invalidate the **same-feature**
caches but not the **downstream-feature** caches. For example,
`frontend/src/features/leads/hooks/useLeadMutations.ts:55-65`
(`useMoveToJobs`) does:

```ts
onSuccess: (_data, variables) => {
  queryClient.removeQueries({ queryKey: leadKeys.detail(variables.id) });
  queryClient.invalidateQueries({ queryKey: leadKeys.lists() });
  queryClient.invalidateQueries({ queryKey: leadKeys.followUpQueue() });
},
```

It invalidates lead caches but never touches `jobKeys.lists()` or any
job-related query key. So when the admin switches to the Jobs tab,
React Query serves the stale cached list and only refetches on the
next stale-time tick or on a manual refresh.

`useMoveToSales` (`useLeadMutations.ts:67-80`) has the same gap for
sales-pipeline queries. The pattern repeats across other cross-tab
mutations (e.g. completing a job from on-site doesn't invalidate the
customer's invoice list, paying an invoice doesn't always refresh the
dashboard summary, etc.).

### Required fix — concrete invalidation matrix

Every mutation must invalidate the cache of every list/view its result
will appear on. The minimum required matrix for the cases the user
called out, and a few obvious adjacencies:

| Mutation                       | Must invalidate (in addition to today)                                    |
| ------------------------------ | ------------------------------------------------------------------------- |
| `useMoveToJobs`                | `jobKeys.lists()`, `customerKeys.lists()`, `dashboardKeys.summary()`       |
| `useMoveToSales`               | `salesKeys.lists()`, `dashboardKeys.summary()` (already partial)           |
| `useMarkContacted`             | `dashboardKeys.summary()` (so contacted-count tile updates)                |
| `useDeleteLead`                | already invalidates leads; confirm dashboard summary also drops the lead   |
| `useCreateManualLead`          | already invalidates leads + dashboard; confirm                            |
| `useCreateCustomer`            | `customerKeys.lists()`, `dashboardKeys.summary()`                          |
| `useUpdateCustomer`            | `customerKeys.detail(id)`, `customerKeys.lists()`                          |
| `useRecordPayment` / invoice mutations | `customerInvoiceKeys.byCustomer(id)`, `dashboardKeys.summary()`     |
| Job lifecycle mutations (start/complete/cancel) | `jobKeys.lists()`, `customerKeys.detail(customerId)`, `dashboardKeys.summary()` |
| Sales-pipeline transitions     | `salesKeys.lists()`, and on conversion to job: `jobKeys.lists()` + `customerKeys.lists()` |

The implementer should expand this matrix to cover every mutation hook
in the codebase. The rule: **a mutation's `onSuccess` must invalidate
every query whose data it could plausibly change**, not just queries
within the same feature folder.

### Implementation guidance

1. **Audit every `useMutation` in `frontend/src/features/**/hooks/`**
   and verify its `onSuccess` invalidates every relevant key. Prefer
   over-invalidation to under-invalidation; React Query is cheap to
   re-fetch and the dev server is fast.
2. **Extract a shared helper** like
   `invalidateAfterLeadRouting(queryClient, target: 'jobs' | 'sales')`
   that calls the right combination of `invalidateQueries` for each
   destination. This keeps the matrix above out of every individual
   mutation hook.
3. **Set sane defaults on the QueryClient.** In the root provider
   (likely `frontend/src/core/api/queryClient.ts` or the
   QueryClientProvider setup), confirm:
   - `refetchOnWindowFocus: true` (so switching tabs in the OS
     refreshes whatever's stale).
   - `staleTime: 30s` or so for list queries (balances "always fresh"
     against "spam the API").
4. **Avoid the polling shortcut.** A few queries already use
   `refetchInterval: 30_000` (e.g. `useCustomerInvoices`) as a safety
   net for cross-mutation freshness. That's fine as a backstop, but
   it must NOT be the primary mechanism — invalidate on mutation as
   the rule, poll only for things that change without an in-app
   action (e.g. webhooks).
5. **Cross-feature invalidation is OK and expected.** It's normal for
   `useMoveToJobs` (in the leads feature) to import `jobKeys` from
   the jobs feature and invalidate it. That's not a layering
   violation — it's the cross-cutting nature of the data.

### Tests to add

- Each mutation hook should have a test that mocks the query client
  and asserts every required key was invalidated on success.
- An integration-style test for the Move-to-Jobs flow that:
  1. Pre-populates the jobs list cache with N jobs.
  2. Triggers the move-to-jobs mutation for a lead.
  3. Asserts the jobs list cache is marked stale (or the mocked
     `invalidateQueries` was called with `jobKeys.lists()`).

### Why this matters

The user's mental model — and the correct one — is that the app's tabs
should always reflect the truth without a manual refresh. Every place
where they currently have to F5 to see their own action's result is a
bug in this matrix. Closing every gap in this matrix is the
requirement.

---

## 10. Calendar Appointments — Richer Context, Notes, and Image Upload

**Type:** Feature enhancement
**Screenshot reference:** 2026-04-16 7:48 PM ("Edit Appointment" modal
on the sales calendar — `Sales Entry: testing 4 — exploring`,
`Title: Estimate - testing 4`, with Date / Start Time / End Time /
Notes / Delete / Cancel / Save).

### Background

The calendar is the primary place admins reference what jobs and
estimate appointments exist for the day/week. Today the Edit
Appointment modal exposes only the bare scheduling fields (sales
entry, title, date, times, notes). That's not enough context to act on
an appointment without bouncing back to the customer or sales record.

This applies to **both** appointment classes:

- **Estimate appointments** (sales-pipeline appointments) — the modal
  shown in the screenshot, rendered by
  `frontend/src/features/sales/components/SalesCalendar.tsx`. These
  link to a `sales_entry_id`.
- **Job appointments** (scheduled work) — rendered by
  `frontend/src/features/schedule/components/AppointmentForm.tsx`.
  These link to a `job_id` and a `customer`.

Both need the additions below; the implementer should add them to
each form.

### Requirement A — Show customer context in the appointment modal

Every appointment, regardless of class, should surface as much
relevant customer/property context as the data model can provide
(read-only display fields above the editable form fields). Per the
user, "include all the details" — the appointment is the daily
reference surface, so the more context the better. Minimum required:

- Customer name
- Customer phone number (tap-to-call link on mobile)
- Customer (primary) address (with a small "Open in maps" link)
- Job type / service description (for estimate appointments, this is
  the lead's `situation`; for job appointments, the job's `job_type`).
- `last_contacted_at` (so the admin knows when the customer was last
  contacted before this appointment).
- `preferred_service_time` (if set on the customer / agreement).
- `is_priority` badge (if the customer is flagged priority).
- `dogs_on_property` / `has_dogs` safety warning (visually
  distinctive — this is a tech-on-site safety concern).
- `gate_code` and `access_instructions` if present on the property
  (so the technician arriving on-site has them inline without
  drilling into the customer record).
- `is_red_flag` / `is_slow_payer` warnings if set (small inline pill
  near the customer name).
- Any open invoice balance summary, if cheaply derivable.
- Notes timeline excerpt (Section 4 / Requirement D below).

Render the context as a compact info block at the top of the modal,
not as a wall of text. Group safety/operational warnings (dogs, gate
code, priority, red flag) visually separate from biographical info
(name, phone, address). These fields are read-only on the appointment
form — they're context, not edit targets. To change them, the admin
clicks the link in Requirement B.

### Requirement B — Link back to the original sales entry / customer

Each appointment modal should include a clickable link to the
record it belongs to:

- **Estimate appointments** → link to the corresponding **Sales entry**
  detail page (`/sales/{sales_entry_id}` or whatever the route is).
  The sales entry is the canonical source of customer, lead, and
  pipeline state; this is where the admin goes to see/edit the deeper
  context (notes timeline, lead history, pipeline stage, attached
  documents, etc.).
- **Job appointments** → link to the corresponding **Customer detail
  page** (`/customers/{customer_id}`) and, secondarily, to the **Job
  detail** if there is one.

The link is the way to drill into "all that sort of stuff on top of
already shown in the appointment itself" — phone, job type, last
contact, plus the full lead/sales history. The appointment modal
shows the headline; the linked page shows the full record.

UX: render the link as a small "View sales entry →" or "View customer
→" button at the top of the modal, near the read-only context block.

### Requirement C — File upload on appointments (any file type)

Admins must be able to attach **any file type** directly to an
appointment — images, PDFs, Word docs, anything (confirmed by the
user). The calendar is where they reference what work exists for the
day, so attaching a photo (e.g. a property photo, a "before" shot, a
reference image of the equipment), a signed estimate PDF, or any
other supporting document at the appointment level makes that context
available without hunting through the customer record.

Specifically:

- An "Attach files" affordance in the Edit Appointment modal.
- Multiple files per appointment.
- Accept any MIME type. The UI should render an appropriate preview
  per type:
  - Images → thumbnail preview, click to enlarge.
  - PDFs → file-icon tile with the filename, click to open inline
    or download.
  - Other (docx, xlsx, txt, etc.) → file-icon tile with filename
    and extension, click to download.
- Per-file size cap: ≤25 MB (PDFs and signed docs run larger than
  photos; revisit if the existing customer/lead upload flow already
  allows larger).
- Files persist server-side (S3 or whichever object store is already
  used for customer photos and lead attachments — reuse the same
  bucket and presign flow, do not introduce a new upload pipeline).
  The existing lead attachment system at
  `frontend/src/features/leads/components/AttachmentPanel.tsx`
  already supports general file types (`AttachmentType`:
  `ESTIMATE | CONTRACT | OTHER`); reuse its pipeline.
- Attached files should also surface on the appointment "card" in
  the calendar grid (a small attachment-count badge or a thumbnail
  strip for image attachments) so the admin can see at-a-glance
  which appointments have supporting context attached.

### Requirement D — Notes integration with the lead/customer notes timeline

The current Notes textarea in the modal is a single string per
appointment. Per Section 4 (Lead Notes That Follow the Lead), the
broader system is moving to a notes timeline that follows the lead →
sales → customer chain. Appointment notes should join that timeline,
not live in isolation:

- Each note added on an appointment is recorded against the
  appointment **and** is visible on the linked sales entry / customer
  notes timeline with a `subject_type: 'appointment'` (or similar)
  tag and an `origin_appointment_id` reference.
- Conversely, the appointment modal shows the relevant slice of the
  parent notes timeline (read-only, with a "View full timeline →"
  link) so the admin sees historical context before adding a new
  note.

If Section 4's notes table is not yet built when this work is picked
up, a transitional approach is acceptable: store appointment notes
locally on the appointment row, and migrate them into the unified
notes table once it lands.

### Data model

- New table or columns on the existing appointments tables for image
  attachments. Recommend a generic `appointment_attachments` table:
  - `id` (uuid, pk)
  - `appointment_id` (uuid, fk — supports both estimate and job
    appointment tables, OR add a `subject_type` discriminator if both
    classes share an attachments table)
  - `file_key` (string — S3 object key)
  - `file_name`, `file_size`, `content_type`
  - `uploaded_by` (uuid, fk → users)
  - `created_at`
- If the codebase already has a generic attachments table (e.g. the
  one used for lead attachments at
  `frontend/src/features/leads/components/AttachmentPanel.tsx`),
  extend it instead of creating a new one. Investigate before
  building.

### API surface

For each appointment class:

- `GET /api/v1/appointments/{id}/attachments` — list.
- `POST /api/v1/appointments/{id}/attachments` — upload (presign +
  finalize, mirroring the existing customer/lead upload flow).
- `DELETE /api/v1/appointments/{id}/attachments/{attachment_id}` — delete.
- `GET /api/v1/appointments/{id}/context` — convenience endpoint that
  returns the customer, address, last_contacted_at, job_type, sales
  entry summary needed for Requirement A. Optional — if existing
  endpoints already return enough joined data, the FE can compose it
  client-side.

### Implementation notes

- Estimate-appointment modal:
  `frontend/src/features/sales/components/SalesCalendar.tsx`
  (lines around 258 / 275 — the "Edit Appointment" dialog and the
  `salesEntryId` Select).
- Job-appointment modal:
  `frontend/src/features/schedule/components/AppointmentForm.tsx`.
- Image-upload UI: reuse the pattern in
  `frontend/src/features/leads/components/AttachmentPanel.tsx` and
  `frontend/src/features/customers/components/PhotoGallery.tsx`.
  Don't reinvent the presign flow.
- Auto-refresh requirement (Section 9) applies: uploading or
  deleting an appointment attachment must invalidate
  `appointmentKeys.detail(id)` and the calendar list query so the
  thumbnails appear without a manual refresh.
- Editability principle (Section 8) applies: the read-only context
  block in Requirement A is the exception — those fields are
  intentionally not edited from the appointment form. They are
  edited on the linked sales entry / customer record (Requirement B).

### Tests to add

- AppointmentForm renders customer name, phone, address, job type,
  last_contacted_at when an appointment is opened.
- "View sales entry →" link navigates to the correct route.
- Image upload happy path: select file → preview → save → appears in
  list. Bad-MIME and oversize rejections.
- Deleting an attachment invalidates the appointment query.

---

## 11. Resolved Decisions

Confirmed by the user on 2026-04-16:

1. **Consent fields** — the three consents to surface on the Lead
   Detail page are `sms_consent`, `email_marketing_consent`, and
   `terms_accepted`. There is no separate CallRail consent flag; SMS
   consent is what gates CallRail outbound.
2. **Historical leads in `qualified` / `converted` / `lost` / `spam`** —
   leave them at their current status. Render them as a neutral
   "Archived" badge in the UI. Stop allowing new writes to those
   statuses (PATCH 422 as described in Section 3). No data migration.
3. **Mark as Lost / Mark as Spam removal** — confirmed. Remove both
   from the Lead Detail page. Delete is the only removal action.
4. **Universal editability** — anything present on Lead detail or
   Customer detail must be editable (Section 8). Customer contact
   info, address, communication preferences, and lead source are
   explicit must-haves.
5. **Lead notes follow the lead** — notes added at the Lead stage must
   persist and remain visible/editable on the resulting Sales entry
   and Customer record (Section 4).
6. **Auto-refresh on mutation** — every action that mutates data must
   invalidate every cache that surfaces that data, so all tabs reflect
   the change without a manual page refresh (Section 9).

7. **Sales entries are fully editable + bidirectional notes** — every
   field on a Sales pipeline entry (customer name, phone number, job
   type, last contacted, etc.) must be admin-editable from the Sales
   entry detail page. Notes added on a Sales entry propagate into the
   appointment(s) tied to that entry, and notes added on an
   appointment propagate back to the parent Sales entry — both
   directions, same shared timeline (Section 12).
8. **Notes data model = implementer's choice** — extend an existing
   comments/notes table if one fits the requirements in Section 4;
   otherwise build the proposed table. The shape is not prescribed;
   only the behavior (one timeline, multi-subject, follows the
   lead → sales → appointment → customer chain) is binding.
9. **Customer address comes from the primary property** — addresses
   live on the `properties` table, not on `customers`. A customer can
   have multiple properties; exactly one is flagged primary. The
   "Primary Address" shown on the Customer detail page is the primary
   property's address; editing that block PATCHes the primary
   property row. All other properties are managed in a Properties
   section on the same page and every field on every property is
   editable. Promoting a secondary property to primary is an admin
   action (Section 5, group #7).
10. **Sales entry edits flow through to the source-of-truth row**
    (Section 12) — editing customer phone, name, or any other
    customer-sourced field from a Sales entry detail page PATCHes
    the underlying Customer row, so the change reflects everywhere.
    No snapshot/freeze of historical sales-entry views.
11. **`last_contacted_at` auto-stamp scope** (Section 13) — only the
    explicit Mark as Contacted button and the status dropdown change
    to Contacted auto-stamp `last_contacted_at`. We are NOT
    auto-stamping on outbound SMS, inbound CallRail calls, or sent
    emails. The field is fully manually editable; that's the
    primary requirement.
12. **Lost / Spam removed at every level** (Section 3) — Mark as
    Lost / Mark as Spam buttons removed from Lead detail; bulk
    actions removed from Lead list; Lost/Spam list filters removed.
    Delete is the only removal action, full stop.
13. **Appointment file upload accepts any MIME type** (Section 10C)
    — images, PDFs, Word docs, anything. ≤25 MB per file. UI renders
    appropriate previews per type.
14. **Calendar appointment context = "include all the details"**
    (Section 10A) — surface every useful field the data model can
    provide: name, phone, address, job type, last_contacted,
    preferred_service_time, is_priority, dogs_on_property safety
    warning, gate_code, access_instructions, red_flag/slow_payer
    warnings, open balance summary if cheap.
15. **Customer status fully admin-editable** (Section 5, group #6) —
    admins can flip `CustomerStatus` to any value with no transition
    guard. Audit-log every manual change.
16. **`EstimateCreator` / `ContractCreator` orphan check** (Section 1)
    — investigation 2026-04-16 confirms both
    `frontend/src/features/leads/components/EstimateCreator.tsx` and
    `frontend/src/features/leads/components/ContractCreator.tsx` are
    only imported by `LeadDetail.tsx`. After Section 1's button
    removal they're true orphans; delete both files and remove their
    barrel exports at `frontend/src/features/leads/index.ts:15-16` in
    the same change. The schedule-side
    `frontend/src/features/schedule/components/EstimateCreator.tsx`
    is a parallel, unaffected component (used by `AppointmentDetail.tsx`)
    and must be left alone.
17. **Customer create network error — root cause confirmed**
    (Section 6) — the FE `LEAD_SOURCES` dropdown exposes 8 options
    (`website`, `google`, `referral`, `facebook`, `nextdoor`,
    `yard_sign`, `repeat`, `other`); the BE `LeadSource` enum it
    validates against has only 5 (`website`, `google`, `referral`,
    `ad`, `word_of_mouth`). Selecting any of the 5 mismatched values
    (`facebook`, `nextdoor`, `yard_sign`, `repeat`, `other`) returns
    a 422 that's masked as a generic "Failed to create customer"
    toast by the empty `catch {}` at `CustomerForm.tsx:168`. Fix:
    migrate the customer-create schema to validate against
    `LeadSourceExtended`, surface server error messages in the
    catch block, and align `LEAD_SOURCES` with the new BE enum
    membership (Section 6 spells out the implementation).
18. **Lead-source value alignment — no new enum members needed**
    (Section 6 follow-up) — investigation 2026-04-16 confirms the
    lead-intake side never collected `facebook` / `nextdoor` /
    `repeat` as distinct values. Those strings exist only in the
    customer-create form's hand-rolled list, not in either backend
    enum, not in the public lead form, not in `LEAD_SOURCE_LABELS`,
    not in any lead-side analytics. The lead system's
    `LeadSourceExtended` enum buckets all social channels into
    `social_media`. The customer-create dropdown should match that
    same enum exactly: `facebook`/`nextdoor` collapse into
    `social_media`, `repeat` collapses into `referral`, `yard_sign`
    + `other` are already in `LeadSourceExtended` and stay as-is.
    No new enum values need to be added.

### Core constraint (the user's headline concern)

**Everything visible on a Lead or a Customer — and on every record
reachable from those (Sales entry, Appointment, Property) — must be
admin-editable from the page that displays it, and every edit must
persist correctly in the underlying database.**

The universal-editability principle (Section 8) is the spec; the
auto-refresh requirement (Section 9) and the source-of-truth-edit-
through requirement (Section 12) together guarantee that the persisted
change is reflected accurately in every view that surfaces it. Any
field that is visible but not editable, or any edit that saves to one
view but not another, is a bug against this requirement and a blocker
for shipping.

This applies to every field touched by Sections 2 (Lead),
5 (Customer + Properties), 12 (Sales entry), 10 (Appointment),
and 13 (Last Contacted). Implementers should treat this as the
acceptance criterion: walk every field on every Lead and Customer
detail page (and every page reachable from them), confirm it is
editable from that page, save an edit, and confirm the new value is
visible everywhere else it should be.

## 12. Sales Entry — Editability and Bidirectional Notes

**Type:** Feature requirement (extends Sections 4, 5, 8, 10)

### Editable fields on a Sales entry

Every field present on a Sales pipeline entry must be editable from
the Sales entry detail page using the same inline-edit pattern
proposed for Lead detail (Section 2) and Customer detail (Section 5).
Explicit must-haves the user called out:

- Customer name (first / last)
- Customer phone number (validated + normalized like every other
  phone field)
- Job type / service description
- `last_contacted_at`

Plus, by the universal-editability principle (Section 8), every other
field surfaced on the Sales entry — pipeline stage, assigned staff,
estimate amount, attached documents, dates, address, etc. The only
exceptions are derived/computed values and audit-trail timestamps set
by system actions.

Where a field is sourced from the underlying Lead or Customer record
(e.g. customer name and phone really live on `customers`, not on the
sales entry), the edit must PATCH the source-of-truth row and the
Sales entry should re-render with the updated value. The implementer
must NOT duplicate the data onto the sales entry — that creates
drift. If the schema currently denormalizes any of these fields onto
the sales entry, fix the read path to join through to the canonical
row instead.

### Bidirectional notes between Sales entries and appointments

Notes form a single shared timeline across the Lead, Sales entry,
linked Customer, and any Appointment(s) attached to the Sales entry
or Customer. This is the same notes timeline introduced in Section 4
and extended for appointments in Section 10 — restating here for
clarity:

- A note added on the Sales entry appears on every appointment tied
  to that Sales entry, tagged with the Sales-stage origin.
- A note added on an appointment appears on the parent Sales entry
  (and on the Customer if the Sales entry has converted), tagged
  with the Appointment-stage origin and an `origin_appointment_id`.
- The notes timeline is the same underlying record set viewed from
  different "subjects." Adding a note from any view inserts into the
  same store; the view filters/sorts/tags it.

### Implementation note

This is not three separate notes systems — it's one notes table
(Section 4) viewed from four contexts (Lead, Sales entry,
Appointment, Customer). The implementer must build one timeline
component and one API surface, parameterized by subject type. Do not
ship per-feature notes endpoints that diverge.

### Tests to add

- Editing the customer phone from the Sales entry page persists to
  the underlying customer row and is reflected back on the Customer
  detail page.
- Adding a note on the Sales entry shows up on every appointment
  tied to that entry without a manual refresh (Section 9
  invalidation matrix applies).
- Adding a note on an appointment shows up on the parent Sales entry
  without a manual refresh.

---

## 13. Lead "Last Contacted" — Auto-Initialized and Editable

**Type:** UI enhancement + small data-flow fix

### Scope decision (resolved)

`last_contacted_at` is auto-stamped only by the **explicit admin
contact action** — the "Mark as Contacted" button and the status
dropdown changing from Not Contacted → Contacted. We are **not**
auto-stamping on other touchpoints (outbound SMS, inbound CallRail
calls, email opens). The user's priority is full manual editability
plus the explicit Mark as Contacted stamp; cross-system auto-stamping
is deferred.

### Requirement

The Lead detail page surfaces a "Last Contacted" date. Two changes:

1. **Auto-initialization on first contact.** When a lead is moved to
   the `contacted` status — whether via the **Mark as Contacted**
   button or via the new "Not Contacted → Contacted" dropdown change
   from Section 3 — the system must populate the lead's "last
   contacted" timestamp with the moment of that transition. This is
   the seed value; without it the field stays blank until someone
   manually edits it, which defeats the point.
2. **Admin-editable.** The "Last Contacted" date must be editable
   from the Lead detail page using the same inline-edit pattern as
   the other editable sections in Section 2. An admin who actually
   spoke to the customer at a different time (e.g. caught them on a
   follow-up call after the system stamp) should be able to update
   the date without needing the database.

This satisfies the Section 8 universal-editability principle for
this specific field, and closes the gap where today's
`last_contacted_at` is purely system-set.

### Backend / data model notes

The `Lead` model already has two related fields (per
`frontend/src/features/leads/types/index.ts`):

- `contacted_at` — when the lead was first marked contacted.
- `last_contacted_at` — most recent contact timestamp.

Required behavior:

- `useMarkContacted` (`useLeadMutations.ts:83-94`) and any
  status-dropdown write that transitions to `contacted` must set
  **both** `contacted_at` (only if currently null — first transition
  only) and `last_contacted_at` (every transition) to `now()` on the
  backend. Confirm the backend already does this; if it only sets
  `contacted_at`, extend it to also stamp `last_contacted_at`.
- `LeadUpdate` Pydantic schema (or whichever schema backs PATCH
  `/api/v1/leads/{id}`) must accept `last_contacted_at` as an
  editable optional field. Validate as a timezone-aware ISO-8601
  datetime, not in the future, not before the lead's `created_at`.
- Audit-log the manual edit (actor, lead, old value, new value,
  timestamp) — same pattern as the Section 2 consent toggles, since
  this is a meaningful provenance change.

### Frontend notes

- Add the editable "Last Contacted" field to the Lead detail
  editable groups in Section 2 (Service details or its own block —
  whichever the implementer thinks reads cleanest).
- Use a date-time picker (date + time, not date-only) since
  `last_contacted_at` is a timestamp, not a date.
- Show a small system-generated indicator next to the value when it
  was set by the system (i.e. equal to the most recent
  `Mark as Contacted` action) vs manually overridden, so admins know
  whether they're looking at an automatic stamp or a human edit.
- Auto-refresh per Section 9: after a manual edit or after a Mark
  Contacted action, invalidate `leadKeys.detail(id)` and
  `leadKeys.lists()` so any list view that surfaces "Last Contacted"
  updates immediately.

### Tests to add

- Marking a lead contacted for the first time stamps both
  `contacted_at` and `last_contacted_at`.
- Marking an already-contacted lead contacted again only updates
  `last_contacted_at`, not `contacted_at`.
- PATCH `/api/v1/leads/{id}` with `last_contacted_at` in the future
  → 422.
- PATCH with `last_contacted_at` before `created_at` → 422.
- Manual edit on the Lead detail page persists and the list view
  reflects the new value without a manual refresh.

---

## 14. Lead List — Remove "Schedule" and "Follow Up" Filter Tabs

**Type:** UI cleanup
**Screenshot reference:** 2026-04-16 7:57 PM (Leads tab header — three
filter pills "All", "Schedule", "Follow Up" sit above the search bar).

### Requirement

On the Leads list page, remove the **Schedule** and **Follow Up**
filter pills next to **All**. Only **All** should remain (and at that
point the single tab serves no filtering purpose, so the implementer
should consider removing the tab row entirely and just rendering the
unfiltered list).

### Implementation notes

File: `frontend/src/features/leads/components/LeadFilters.tsx`

- The `INTAKE_TABS` array at lines 23-27 declares the three pills:
  ```ts
  const INTAKE_TABS = [
    { label: 'All', value: 'all' },
    { label: 'Schedule', value: 'schedule' },
    { label: 'Follow Up', value: 'follow_up' },
  ] as const;
  ```
  Drop the `'schedule'` and `'follow_up'` entries. If `'all'` is the
  only option remaining, remove the tab row markup at lines ~110-126
  entirely.
- The `intake_tag` query param (line 84) is no longer driven by this
  UI. Confirm no other UI surface depends on filtering by
  `intake_tag` before removing the param-write logic. The param
  itself can stay in `LeadListParams` for now — the backend filter
  may still be useful for power-user queries or future surfaces.
- Update `LeadFilters.test.tsx` and `LeadsList.test.tsx` to drop
  assertions about the removed pills.

### Related cleanup — recommended path (user deferred to recommendation)

The `intake_tag` enum (`'schedule' | 'follow_up'`) is still listed as
an editable field in Section 2 and surfaces via `IntakeTagBadge` and
`FollowUpQueue`. The user wasn't sure about the full scope of the
concept and asked the implementer to investigate and recommend.

**Recommendation (do this unless investigation surfaces a blocker):**

1. **Investigate first.** Before removing anything, grep for every
   reader of `intake_tag` across `frontend/src` and the backend.
   Specifically check:
   - `frontend/src/features/leads/components/FollowUpQueue.tsx` —
     does the queue depend on `intake_tag === 'follow_up'`, or is
     it driven by something else (e.g. action tags, status, or
     date-since-contact)?
   - Backend lead-routing logic — does any auto-routing read the
     tag (e.g. "schedule" intake routes straight to scheduling)?
   - Any reporting / analytics surface that groups by intake tag.
2. **If `intake_tag` is only surfaced via the badge + the
   now-removed pills:** retire the concept entirely.
   - Remove the `IntakeTagBadge` from Lead detail and lead-row views.
   - Remove `intake_tag` from the editable fields in Section 2.
   - Leave the column on the Lead model (and the `IntakeTag` type
     in `types/index.ts`) as a no-op for the immediate landing —
     drop the column in a follow-up migration once a release cycle
     has confirmed no consumer regressed.
3. **If `FollowUpQueue` or backend routing depends on it:** keep the
   field internally, but still remove the badge and the editable
   surface (so admins don't see/edit a tag the system controls).
   Document the system-driven semantics inline.

This narrow section's binding ask is the two filter pills (above).
The recommendation above is the implementer's default path for the
broader retirement; deviate only if the investigation surfaces a
real consumer.

---

## 15. Customers — Wire Up the Export Button (Excel)

**Type:** Bug fix + small backend extension

### Reported symptom

On the Customers tab there is an "Export" button (next to the
filters / new-customer controls). Clicking it does nothing.

### Investigation findings

- **Frontend dead button.** `frontend/src/features/customers/components/CustomerList.tsx:343-346`
  renders the button with no `onClick` handler:
  ```tsx
  <Button variant="outline" size="sm" className="gap-2">
    <Download className="h-4 w-4" />
    Export
  </Button>
  ```
- **Backend endpoint exists** but is CSV-only and capped at 1,000
  rows: `POST /api/v1/customers/export` at
  `src/grins_platform/api/v1/customers.py:867-919`. Returns
  `text/csv` with a `customers.csv` filename.
- **No auth guard on the export endpoint.** The route signature
  (`customers.py:876-888`) declares only `service` and the two query
  params — there's no `CurrentActiveUser` dependency. Every other
  customer endpoint in this file requires authentication. This is a
  security gap and must be fixed in the same change.

### Requirement

Clicking the Export button on the Customers tab downloads an Excel
file containing **all customers** (subject to the open question
below about whether active list filters should apply).

### Implementation

**Backend (extend the existing endpoint):**

1. Add `CurrentActiveUser` auth dependency to
   `export_customers` (`customers.py:876-888`) — match the auth
   pattern used by every other customer endpoint. Without this,
   anyone with the URL can export the entire customer table.
2. Raise the row cap. The current `limit ≤ 1000` blocks "export all"
   for any tenant past 1,000 customers. Either:
   - Remove the cap and stream the response (recommended for
     scalability — chunked CSV/XLSX writer, not load-all-then-send).
   - Keep a higher cap (e.g. 50,000) with a 400 if exceeded and a
     clear message telling the admin to add a filter.
3. Add an Excel format option. The cleanest path:
   - Accept a `?format=xlsx` query param (default `csv` for
     backward compatibility, or default `xlsx` since the user
     explicitly asked for Excel — choose one).
   - When `format=xlsx`, build the workbook with `openpyxl`
     (already a stable, widely-used Python lib; verify it's already
     in `pyproject.toml` / `requirements.txt` before adding).
   - Return `Content-Type:
     application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
     and `Content-Disposition: attachment; filename=customers-YYYY-MM-DD.xlsx`.
4. Confirm the column set. The CSV writer in
   `service.export_customers_csv` defines the columns; mirror those
   exactly in the XLSX writer (or, better, share a single
   row-projection function that both formats consume) so the two
   exports stay in sync. At minimum the export should include every
   column an admin can see in the Customers list view: name, phone,
   email, lead source, status, primary address, customer flags
   (`is_priority`, `is_red_flag`, `is_slow_payer`), `created_at`,
   `last_contacted_at`. If the admin opens the file expecting "the
   data they see in the table," the columns must match.

**Frontend (wire the button up):**

1. Add an `exportCustomers` method to
   `frontend/src/features/customers/api/customerApi.ts` that POSTs to
   `/customers/export?format=xlsx` and returns the response as a
   `Blob`. Use the existing `apiClient` so auth is attached
   correctly.
2. Add a `useExportCustomers` mutation hook (or just a
   `useMutation` wrapper) in
   `frontend/src/features/customers/hooks/`. On success: trigger a
   browser download via the standard
   `URL.createObjectURL(blob)` → anchor-click pattern, with the
   filename pulled from the `Content-Disposition` header (or a
   client-built fallback like `customers-2026-04-16.xlsx`).
3. Wire the Export button in
   `frontend/src/features/customers/components/CustomerList.tsx:343-346`:
   - `onClick={handleExport}` calling the mutation.
   - Disable the button + show a small spinner while
     `mutation.isPending` is true.
   - Toast on success ("Exported N customers") and on failure (use
     the same `getErrorMessage(err)` pattern from Section 6's
     `catch` fix so any 4xx surfaces a real message).
4. Auto-refresh principle (Section 9) does **not** apply here — the
   export reads data, doesn't mutate it.

### Open questions for the implementer to surface

1. **Honor active filters or always export all?** The user said
   "export all the customers." The existing BE endpoint accepts a
   `city` filter (and the FE list has a search + property filter
   popover). Default recommendation: **always export every
   customer** when the button is clicked, ignoring the list-level
   filters — that matches the user's stated intent. Optionally add a
   "Export filtered (N rows)" secondary action later if admins ask
   for it.
2. **CSV vs XLSX vs both.** User said Excel. CSV opens in Excel
   natively, but XLSX is the unambiguous "Excel file" the user
   asked for. Recommend XLSX as the only output (drop CSV from the
   FE button; keep the BE CSV path available for any scripted /
   API consumer that already relies on it).

### Tests to add

- Backend: `POST /api/v1/customers/export?format=xlsx` returns
  status 200, the correct content-type, and a non-empty workbook.
- Backend: same endpoint without auth returns 401 (regression test
  for the security gap).
- Frontend: clicking Export triggers the mutation and the download
  pattern is invoked. Mock the blob response and assert the
  `<a>.click()` was called with the correct filename.

---

## 16. Open Questions for the User

All previously open questions have been resolved or answered via
investigation (see Resolved Decisions, items #1–#18).

No outstanding product decisions remain. The doc is implementation-ready.
