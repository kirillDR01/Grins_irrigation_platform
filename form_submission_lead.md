# Lead Capture: Website Form Submission Plan

## Overview

When a visitor fills out the "Get Your Free Design" form on the Grin's Irrigation landing page (grins-irrigation.vercel.app), the submission needs to hit our backend API, store the lead in a new `leads` table, and trigger notifications (dashboard + email).

The landing page frontend lives in a **separate repo** — this plan covers the backend changes needed in this repo (grins_platform) AND the admin dashboard frontend changes (leads management tab).

---

## Current Form Fields (from live site)

| Field | Type | Placeholder/Options | Required |
|-------|------|---------------------|----------|
| Your Name | text | "John Doe" | Yes |
| Phone Number | text | "(612) 555-0123" | Yes |
| Zip Code | text | "55424" | Yes |
| What best describes your situation? | dropdown | 4 options (see below) | Yes |

**Dropdown options:**
1. "I don't have a sprinkler system yet"
2. "I want to upgrade/replace my current system"
3. "I need service or repair"
4. "Just exploring options"

**Submit button:** "Send My Free Design Request"

---

## Form Structure (Decided)

Keep the existing 4 required fields. Add `email` and `notes` as optional. Skip `property_address` and `how_heard` for now — they add friction and Viktor can ask during the follow-up call.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| name | string | Yes | Full name (single field, split on backend during conversion) |
| phone | string | Yes | Normalized to 10 digits on backend |
| email | string | No | Optional but valuable for follow-up |
| zip_code | string | Yes | 5-digit MN zip code |
| situation | enum | Yes | Maps to the 4 dropdown options |
| notes | string | No | "Anything else we should know?" — free text |
| source_site | string | No | Defaults to "residential", set by the calling site |
| honeypot | string | No | Hidden field — reject submission if filled (bot detection) |

**Rationale:** Email is valuable when provided but optional to keep the form low-friction. Notes gives the lead a way to add context. `property_address` and `how_heard` deferred to a future iteration — Viktor gets those during the follow-up call anyway.

---

## New Database: `leads` Table

Separate from the `customers` table. A lead is a prospect — not yet a confirmed customer.

### Schema

```
leads
├── id                  UUID        PK, auto-generated
├── name                VARCHAR(200) NOT NULL
├── phone               VARCHAR(20)  NOT NULL
├── email               VARCHAR(255) NULL
├── zip_code            VARCHAR(10)  NOT NULL
├── situation           VARCHAR(50)  NOT NULL  (enum: new_system, upgrade, repair, exploring)
├── notes               TEXT         NULL
├── source_site         VARCHAR(100) NOT NULL DEFAULT 'residential'
├── status              VARCHAR(20)  NOT NULL DEFAULT 'new'
├── assigned_to         UUID         NULL, FK → staff.id
├── customer_id         UUID         NULL, FK → customers.id  (linked when converted)
├── contacted_at        TIMESTAMP    NULL  (when first follow-up happened)
├── converted_at        TIMESTAMP    NULL  (when converted to customer + job)
├── created_at          TIMESTAMP    NOT NULL, server default now()
├── updated_at          TIMESTAMP    NOT NULL, server default now()
```

### Lead Status Enum

```python
class LeadStatus(str, Enum):
    NEW = "new"              # Just submitted, not yet reviewed
    CONTACTED = "contacted"  # Viktor/staff reached out
    QUALIFIED = "qualified"  # Good lead, ready to schedule estimate
    CONVERTED = "converted"  # Became a customer + job created
    LOST = "lost"            # Didn't convert (went with competitor, etc.)
    SPAM = "spam"            # Junk submission
```

### Lead Situation Enum

Maps directly to the dropdown options on the form:

```python
class LeadSituation(str, Enum):
    NEW_SYSTEM = "new_system"        # "I don't have a sprinkler system yet"
    UPGRADE = "upgrade"              # "I want to upgrade/replace my current system"
    REPAIR = "repair"                # "I need service or repair"
    EXPLORING = "exploring"          # "Just exploring options"
```

### Source Site Field

`source_site` is a **free string**, not an enum. Defaults to `"residential"` for the current landing page. Future sites (commercial, partner pages, Google Ads landing pages) can pass their own identifier. No need to update backend code when a new site is added.

---

## Resolved Decisions

These were identified during brainstorming and resolved before implementation:

### 1. Duplicate Detection

**Decision:** Check by phone number during submission.

- If a lead with the same phone exists with status `new` or `contacted` → **update the existing lead** (refresh `updated_at`, merge any new fields like email/notes)
- If a lead with the same phone exists with status `converted` or `lost` → **create a new lead** (they're coming back, treat as fresh opportunity)
- If status is `qualified` → **update existing** (still in pipeline)
- If status is `spam` → **create new** (give them another chance, maybe the first was a false positive)

**Rationale:** Prevents duplicate leads from the same person refreshing the form, while allowing re-engagement from past leads.

### 2. Rate Limiting

**Decision:** Defer rate limiting middleware to a future iteration.

For v1, the honeypot field provides basic bot protection. The platform doesn't currently have any rate limiting infrastructure (`slowapi` or similar). Adding it just for this endpoint would be premature — if spam becomes a problem, we'll add `slowapi` globally.

**v1 protection:** Honeypot field + basic input validation (phone format, zip code format).

### 3. Email Notification

**Decision:** Dashboard-only for v1. Email notification = phase 2.

No email infrastructure exists in the codebase (no SendGrid, SES, or SMTP config). Building email delivery just for lead notifications is out of scope for the initial implementation.

**v1 behavior:**
- New lead appears in dashboard metrics (`new_leads_today`, `uncontacted_leads`)
- New lead appears in recent activity feed (`lead_submitted` activity type)
- Dedicated "New Leads" card on dashboard with count + link to leads page

**Phase 2:** Add email/SMS notification when a lead is submitted (requires Twilio/SendGrid integration).

### 4. Dashboard Integration

**Decision:** Add lead metrics to the existing dashboard.

Changes to `DashboardMetrics` schema:
- Add `new_leads_today: int` — leads submitted today with status `new`
- Add `uncontacted_leads: int` — leads with status `new` (never contacted)

Changes to `RecentActivityItem`:
- Add `lead_submitted` as a valid `activity_type`
- Activity description: "New lead from {name} ({situation})"

Dashboard UI:
- Add a "New Leads" card/widget showing count of uncontacted leads
- Card links to the new Leads management tab
- Color-coded: red if > 5 uncontacted leads (Viktor needs to follow up)

### 5. Auth on Public Endpoint

**Decision:** The `POST /api/v1/leads` endpoint MUST be public (no auth required).

The landing page is a public website — visitors aren't authenticated. This endpoint must be explicitly excluded from any auth middleware. All other lead endpoints (GET, PATCH, DELETE) require admin auth.

Implementation: In the router, the public POST endpoint is registered without the auth dependency. The remaining CRUD endpoints use `Depends(get_current_user)` as usual.

### 6. Honeypot Field

**Decision:** Include a honeypot field in the form submission.

The form includes a hidden field (e.g., `website` or `company`) that is:
- Hidden via CSS (`display: none` or `position: absolute; left: -9999px`)
- Not visible to real users
- Filled in by bots that parse all form fields

**Backend behavior:** If the honeypot field has any value, return `201 Created` (fake success) but do NOT store the lead. Log it as `lead.spam_detected`.

**Rationale:** Zero-cost bot protection. Catches the majority of simple spam bots. No CAPTCHA friction for real users.

### 7. Name Splitting (During Conversion)

**Decision:** Split on first space when converting lead → customer.

- `"John Doe"` → first_name: `"John"`, last_name: `"Doe"`
- `"John Michael Doe"` → first_name: `"John"`, last_name: `"Michael Doe"`
- `"Viktor"` → first_name: `"Viktor"`, last_name: `""` (empty string)

The split happens during the conversion flow, not at submission time. The `leads` table stores the full name as-is. Viktor can edit the first/last name during conversion if the auto-split isn't right.

---

## Backend Components to Build

### 1. Alembic Migration

Create `leads` table with all columns from the schema above. Add indexes on:
- `phone` (for duplicate detection lookups)
- `status` (for filtering by status)
- `created_at` (for sorting by newest)
- `zip_code` (for geographic filtering)

### 2. SQLAlchemy Model (`models/lead.py`)

Follow existing patterns from `models/customer.py` and `models/appointment.py`:
- UUID primary key
- Relationship to `Staff` (assigned_to) and `Customer` (customer_id)
- `TimestampMixin` or explicit `created_at`/`updated_at` with server defaults

### 3. Enums (`models/enums.py`)

Add `LeadStatus` and `LeadSituation` enums to the existing enums file, following the established pattern (section header comment, docstring with `Validates:` reference).

### 4. Pydantic Schemas (`schemas/lead.py`)

Follow existing patterns from `schemas/appointment.py`:

- `LeadSubmission` — public form submission (name, phone, email?, zip_code, situation, notes?, source_site?, honeypot?)
- `LeadResponse` — full lead data returned from API
- `LeadListResponse` — paginated list with `items` and `total`
- `LeadUpdate` — admin updates (status, assigned_to, notes)
- `LeadConvertRequest` — conversion payload (optional first_name/last_name overrides, job details)
- `LeadFilters` — query params for filtering (status, situation, date range, zip_code)

### 5. Repository (`repositories/lead_repository.py`)

Follow existing patterns from `repositories/appointment_repository.py`:

- `create(lead_data)` → Lead
- `get_by_id(lead_id)` → Lead | None
- `get_by_phone(phone)` → Lead | None (for duplicate detection)
- `list(filters, skip, limit)` → list[Lead]
- `count(filters)` → int
- `update(lead_id, update_data)` → Lead
- `delete(lead_id)` → None
- `get_metrics()` → dict (new_today, uncontacted count)

### 6. Service (`services/lead_service.py`)

Follow existing patterns from `services/appointment_service.py`:

- `submit_lead(data)` → LeadResponse
  - Honeypot check (reject silently if filled)
  - Phone normalization (strip non-digits, validate 10 digits)
  - Duplicate detection (check existing leads by phone)
  - Create or update lead based on duplicate rules
  - Log `lead.submitted` event
- `get_lead(lead_id)` → LeadResponse
- `list_leads(filters)` → LeadListResponse
- `update_lead(lead_id, data)` → LeadResponse
  - Status transition validation
  - Set `contacted_at` when status changes to `contacted`
- `convert_lead(lead_id, convert_data)` → dict with customer_id and job_id
  - Split name into first/last (or use overrides from request)
  - Create customer via CustomerService
  - Create job via JobService (if job details provided)
  - Update lead status to `converted`, set `converted_at` and `customer_id`
- `get_dashboard_metrics()` → dict with new_today and uncontacted counts

### 7. API Endpoints (`api/v1/leads.py`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/leads` | **Public** | Submit new lead from form |
| GET | `/api/v1/leads` | Admin | List leads with filters |
| GET | `/api/v1/leads/{id}` | Admin | Get lead details |
| PATCH | `/api/v1/leads/{id}` | Admin | Update lead (status, assignment, notes) |
| POST | `/api/v1/leads/{id}/convert` | Admin | Convert lead to customer + job |
| DELETE | `/api/v1/leads/{id}` | Admin | Delete lead (soft delete or hard delete) |

### 8. Exception Classes (`exceptions/__init__.py`)

Add to existing exceptions:
- `LeadNotFoundError(lead_id)` — 404
- `LeadAlreadyConvertedError(lead_id)` — 400 (can't convert twice)
- `InvalidLeadStatusTransitionError(current, requested)` — 400

### 9. Router Registration (`api/v1/router.py`)

Register the leads router in the existing API router. The public POST endpoint must NOT go through the auth dependency.

---

## CORS Configuration

**No changes needed.** The existing CORS setup in `app.py` reads from the `CORS_ORIGINS` environment variable. The landing page domain (`grins-irrigation.vercel.app`) is already included in the production `CORS_ORIGINS` value. If not, just add it to the env var — no code change required.

---

## Conversion Flow: Lead → Customer + Job

When Viktor clicks "Convert to Customer" on a lead:

```
Lead (name="John Doe", phone="6125551234", situation="new_system", zip_code="55424")
    │
    ▼
1. Auto-split name: first_name="John", last_name="Doe"
   (Viktor can override in the conversion dialog)
    │
    ▼
2. Create Customer via CustomerService.create_customer()
   - first_name, last_name, phone from lead
   - email from lead (if provided)
   - source = "website" (LeadSource enum)
    │
    ▼
3. Optionally create Job via JobService
   - Map situation → job type:
     - new_system → "Installation Estimate" (requires_estimate)
     - upgrade → "System Upgrade Estimate" (requires_estimate)
     - repair → "Repair Request" (ready_to_schedule)
     - exploring → "Consultation" (requires_estimate)
   - Link to newly created customer
    │
    ▼
4. Update Lead
   - status = "converted"
   - converted_at = now()
   - customer_id = new customer's ID
```

---

## Frontend: Admin Dashboard — Leads Management Tab

### New Navigation Tab

Add a "Leads" tab to the admin dashboard sidebar navigation, between "Customers" and "Jobs" (or wherever makes sense in the nav order). Use a funnel or inbox icon.

Badge on the tab showing count of `new` (uncontacted) leads — disappears when count is 0.

### Leads List Page (`/leads`)

Main view when clicking the Leads tab.

**Layout:**
- Page header: "Leads" with subtitle showing total count
- Filter bar at top (same pattern as Jobs list)
- Data table below

**Filters:**
- Status dropdown (All, New, Contacted, Qualified, Converted, Lost, Spam)
- Situation dropdown (All, New System, Upgrade, Repair, Exploring)
- Date range picker (submitted date)
- Search by name or phone

**Table Columns:**
| Column | Description |
|--------|-------------|
| Name | Lead's full name |
| Phone | Phone number (clickable to call on mobile) |
| Situation | Badge with situation label |
| Status | Color-coded status badge |
| Zip Code | Zip code |
| Submitted | Relative time ("2 hours ago", "Yesterday") |
| Assigned To | Staff name or "Unassigned" |

**Status Badge Colors:**
- `new` → blue (needs attention)
- `contacted` → yellow (in progress)
- `qualified` → purple (ready for estimate)
- `converted` → green (success)
- `lost` → gray (closed)
- `spam` → red (junk)

**Row Actions:**
- Click row → navigate to lead detail view
- Quick action buttons: Mark as Contacted, Assign to Staff

**Sorting:** Default sort by `created_at` descending (newest first).

### Lead Detail View (`/leads/:id`)

Shows full lead information with action buttons.

**Sections:**

1. **Lead Info Card**
   - Name, phone, email, zip code
   - Situation (with description)
   - Notes (if any)
   - Source site
   - Submitted date/time

2. **Status & Assignment**
   - Current status with change dropdown
   - Assigned to with staff selector
   - Contacted at timestamp (auto-set when status → contacted)
   - Converted at timestamp (if converted)

3. **Action Buttons**
   - "Mark as Contacted" (if status is `new`)
   - "Convert to Customer" → opens conversion dialog
   - "Mark as Lost" → opens reason dialog (optional reason field)
   - "Mark as Spam"
   - "Delete Lead"

4. **Conversion Dialog** (modal)
   - Pre-filled first name / last name (auto-split from full name)
   - Editable fields so Viktor can correct the split
   - Option to create a job during conversion:
     - Auto-suggested job type based on situation
     - Job description (pre-filled based on situation)
     - "Create job" checkbox (default: checked)
   - "Convert" button → calls `POST /api/v1/leads/{id}/convert`
   - On success: navigate to the new customer's detail page

5. **Linked Customer** (if converted)
   - Link to customer detail page
   - Link to created job (if any)

### Dashboard Integration

On the main Dashboard page:

- Add a "New Leads" summary card/widget
- Shows: `X new leads today` and `Y uncontacted leads`
- Card is color-coded:
  - Green: 0 uncontacted leads
  - Yellow: 1-5 uncontacted leads
  - Red: 6+ uncontacted leads
- Clicking the card navigates to the Leads list page filtered by status=new

In the Recent Activity feed:
- Show `lead_submitted` events: "New lead from John Doe (New System)"
- Clicking the activity item navigates to the lead detail page

### Frontend File Structure

Following the existing VSA pattern:

```
frontend/src/features/leads/
├── components/
│   ├── LeadsList.tsx           # Main list page with table + filters
│   ├── LeadDetail.tsx          # Lead detail view
│   ├── LeadStatusBadge.tsx     # Color-coded status badge
│   ├── LeadSituationBadge.tsx  # Situation label badge
│   ├── ConvertLeadDialog.tsx   # Conversion modal
│   └── LeadFilters.tsx         # Filter bar component
├── hooks/
│   ├── useLeads.ts             # TanStack Query hook for list
│   ├── useLead.ts              # TanStack Query hook for single lead
│   ├── useCreateLead.ts        # Mutation hook (not used in admin, but for completeness)
│   ├── useUpdateLead.ts        # Mutation hook for status/assignment updates
│   └── useConvertLead.ts       # Mutation hook for conversion
├── api/
│   └── leadApi.ts              # API client functions
├── types/
│   └── index.ts                # Lead TypeScript types
└── index.ts                    # Public exports
```

### Query Key Factory

```typescript
export const leadKeys = {
  all: ['leads'] as const,
  lists: () => [...leadKeys.all, 'list'] as const,
  list: (params: LeadListParams) => [...leadKeys.lists(), params] as const,
  details: () => [...leadKeys.all, 'detail'] as const,
  detail: (id: string) => [...leadKeys.details(), id] as const,
  metrics: () => [...leadKeys.all, 'metrics'] as const,
};
```

---

## Landing Page Changes (Separate Repo)

The landing page at `grins-irrigation.vercel.app` needs minimal changes:

1. Add hidden honeypot field to the form
2. Add optional `email` and `notes` fields
3. Change form submission to POST to `{API_BASE_URL}/api/v1/leads`
4. Add `source_site: "residential"` to the payload
5. Handle success/error responses (show thank-you message or error)

**These changes are in a separate repo and NOT part of this implementation plan.** Document the expected API contract so the landing page developer knows what to send.

### Expected API Contract

**Request:**
```json
POST /api/v1/leads
Content-Type: application/json

{
  "name": "John Doe",
  "phone": "(612) 555-0123",
  "zip_code": "55424",
  "situation": "new_system",
  "email": "john@example.com",       // optional
  "notes": "I have a large backyard", // optional
  "source_site": "residential",       // optional, defaults to "residential"
  "website": ""                        // honeypot field, must be empty
}
```

**Success Response:**
```json
HTTP 201 Created
{
  "success": true,
  "message": "Thank you! We'll be in touch within 24 hours.",
  "lead_id": "uuid-here"
}
```

**Validation Error Response:**
```json
HTTP 422 Unprocessable Entity
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": [...]
  }
}
```

---

## Security Considerations

1. **Public endpoint** — no auth, so validate everything:
   - Phone: must be 10 digits after stripping non-numeric chars
   - Zip code: must be 5 digits, optionally validate against MN zip codes
   - Name: 1-200 chars, strip HTML/script tags
   - Email: standard email validation if provided
   - Notes: max 1000 chars, strip HTML/script tags
   - Situation: must be one of the 4 enum values

2. **Honeypot** — silent rejection (return 201 but don't store)

3. **Input sanitization** — strip any HTML tags from name, notes fields to prevent stored XSS

4. **No PII in logs** — log lead events with lead_id, not with phone/email/name

5. **CORS** — already configured, landing page domain must be in `CORS_ORIGINS`

6. **Rate limiting** — deferred to phase 2. If spam becomes a problem before then, add `slowapi` with a per-IP limit on the POST endpoint.

---

## Implementation Order

Suggested order for building this feature:

1. **Enums** — Add `LeadStatus` and `LeadSituation` to `models/enums.py`
2. **Model** — Create `models/lead.py` with SQLAlchemy model
3. **Migration** — Create Alembic migration for `leads` table
4. **Schemas** — Create `schemas/lead.py` with all Pydantic models
5. **Exceptions** — Add lead-specific exceptions
6. **Repository** — Create `repositories/lead_repository.py`
7. **Service** — Create `services/lead_service.py` with all business logic
8. **API Endpoints** — Create `api/v1/leads.py` with public + admin routes
9. **Router Registration** — Register in `api/v1/router.py`
10. **Exception Handlers** — Register lead exception handlers in `app.py`
11. **Dashboard Integration** — Update dashboard metrics + activity feed
12. **Tests** — Unit, functional, integration (three-tier)
13. **Frontend: Types + API client** — TypeScript types and API functions
14. **Frontend: Leads List page** — Table with filters
15. **Frontend: Lead Detail page** — Detail view with actions
16. **Frontend: Convert Dialog** — Conversion modal
17. **Frontend: Dashboard widget** — New Leads card
18. **Frontend: Navigation** — Add Leads tab to sidebar

---

## Out of Scope (Future Iterations)

- Email/SMS notifications on new lead submission
- Rate limiting middleware
- Lead scoring / priority ranking
- Automated follow-up sequences
- `property_address` and `how_heard` form fields
- Lead analytics / conversion funnel reporting
- Bulk lead import from spreadsheet
- Lead assignment rules (auto-assign based on zip code or availability)
