# CRM Changes Update 2 — Requirements Document

**Status:** Finalized — ready for implementation planning
**Source:** `to_do/CRM_Changes_Update_2.md`
**Created:** 2026-04-11
**Owner:** Kirill
**Scope:** All items in the source document are in scope for this update.

---

## Table of Contents

1. [Overall / Authentication](#1-overall--authentication)
2. [Dashboard](#2-dashboard)
3. [Customers](#3-customers)
4. [Leads](#4-leads)
5. [Work Requests → Sales](#5-work-requests--sales)
6. [Sales Tab (New)](#6-sales-tab-new)
7. [Jobs](#7-jobs)
8. [Schedule](#8-schedule)
9. [Invoice](#9-invoice)
10. [Other](#10-other)
11. [Deferred / Gated Items](#11-deferred--gated-items)
12. [Open Questions](#12-open-questions)

---

## 1. Overall / Authentication

### 1.1 Password Hardening (Required)

**Current state** (investigated):
- Default admin credentials are seeded via migration at `src/grins_platform/migrations/versions/20250625_100000_seed_default_admin_user.py` (lines 25–68).
- Current credentials: `admin` / `admin123` (bcrypt hashed, cost factor 12).
- Staff model: `src/grins_platform/models/staff.py` (lines 68–89).

**Requirement:**
- Change the seeded admin password to a significantly stronger value.
- Username `admin` remains unchanged.
- New password criteria:
  - Minimum 16 characters.
  - Mix of upper + lower + digits + 1–2 common symbols (`!`, `-`, `_`).
  - **No rare/hard-to-type symbols** (no `~`, `` ` ``, `|`, `\`, `^`, `{}`, etc.).
  - Easy to type on a standard US keyboard.
  - Memorable-ish (e.g., a 3-4 word passphrase with separators and a number/symbol).

**Proposed password (primary):** `Grins-Admin-Valve-Rain2026!`
- 27 characters — well above the 16 minimum.
- Four word segments separated by hyphens → easy to type, easy to remember.
- Mixed case, digits, one common symbol (`!`).
- Zero hard-to-type characters.
- Estimated entropy: ~120+ bits (effectively brute-force-proof).

**Alternate options** (pick whichever you prefer):
- `Grins-Irrigation-Main-2026!` — 28 chars, more brand-forward.
- `GrinsAdmin-Sprinkler-2026!` — 26 chars, camelCase variant.
- `Valve-Rain-Grins-Admin-26!` — 26 chars, word-reordered.

Kirill will confirm the final password before it's seeded. Document the chosen value in 1Password — **never** in the repo.

**Implementation notes:**
- Rotate via a new migration that updates the existing admin staff row's `password_hash` column (don't drop/recreate).
- **The plaintext must never be committed to the repo.** The migration reads the password from a one-time env var (e.g., `NEW_ADMIN_PASSWORD`) set during the deploy step, hashes it with bcrypt (cost 12), writes the hash, and the env var is then unset. The plaintext never lives on disk in any committed file.
- Existing JWT tokens continue to work until refresh (password hash changes don't invalidate signed tokens).
- After the migration runs successfully, record the new password in 1Password / a password manager as the single source of truth. Never in the repo, a comment, a commit message, or a PR description.

### 1.2 Session Timeout (Investigation Only — Likely No Change)

**Current state** (investigated):
- JWT-based auth with HttpOnly cookies.
- Access token: **60 minutes** (`ACCESS_TOKEN_EXPIRE_MINUTES=60` in `src/grins_platform/services/auth_service.py:40`).
- Refresh token: **30 days** (`REFRESH_TOKEN_EXPIRE_DAYS=30` at line 41).
- Environment-aware cookie flags (Secure + SameSite=none on HTTPS).
- Rate limiting on login: 5 attempts/minute (`src/grins_platform/middleware/rate_limit.py:38`).
- Account lockout: 15 minutes after 5 failed attempts (`auth_service.py:46–47`).
- CSRF protection via cookie + `X-CSRF-Token` header (`src/grins_platform/middleware/csrf.py`).

**Finding:** The reported "random logouts after 20 seconds in another tab" is **not** explained by the current configuration. Possible root causes to investigate:
1. Refresh token not being sent on cross-origin requests (SameSite cookie misconfiguration in local vs prod).
2. Browser tab suspension wiping the cookie on return.
3. Cookie `max-age` being overwritten somewhere unexpectedly.
4. A frontend interceptor that treats any 401 as a logout without attempting refresh.

**Requirement:**
- Investigate and reproduce the premature-logout bug before making config changes.
- If a bug is found, fix the underlying issue rather than extending timeouts.
- Document the finding in a bug-hunt note under `bughunt/`.

### 1.3 Single Admin Login (No Staff/Admin Split)

**Scope decision:** This update uses a **single admin login** for all users. There is no staff-vs-admin distinction in this release, even though the Schedule section (Section 8) describes "staff" and "admin" capabilities.

**What this means in practice:**
- The language "staff can do X" / "admin can do Y" in Section 8 should be read as "any logged-in user can do X and Y" for this update.
- The role infrastructure (`admin`, `sales`, `tech` roles at `src/grins_platform/services/auth_service.py:443`) exists in the code but is **not** exposed via UI in this update.
- All users share the `admin` login. Multi-user and role-based access are deferred to a future update.
- Any "staff cannot delete/remove a job" restriction (Section 8.2.1) is **deferred** — a single admin can do everything.

---

## 2. Dashboard

### 2.1 Alert → Record Highlighting

**Requirement:**
When a user clicks a dashboard alert (e.g., "One new job came in last night that needs something"), they must be taken directly to the referenced record with clear visual confirmation that this is the one the alert referred to.

**Design decision (based on research of Salesforce, HubSpot, ServiceTitan, Jobber, Housecall Pro):**

Use the **HubSpot pattern**:

1. **Primary behavior — single-record alerts** (e.g., "One new job came in"):
   - Navigate **directly to the job detail page**, not the list.
   - This matches ServiceTitan, Jobber, and Housecall Pro — the industry convention for field services CRMs.

2. **Secondary behavior — multi-record alerts** (e.g., "3 estimates waiting"):
   - Navigate to the list tab (Jobs / Sales / Leads) with a pre-applied filter.
   - Auto-scroll to the first matching row.
   - Apply a **soft amber/yellow background pulse that fades over 3 seconds** on matched rows.
   - Use URL query params (`?highlight=<id>`) so the highlight state is shareable and survives a refresh.

**Rejected alternatives:**
- Persistent highlight until dismissed → creates visual noise, requires manual action.
- Pinned-to-top + colored border → breaks the user's mental model of list sort order.
- Colored left border with no animation → too subtle, user may miss it.

### 2.2 Estimates Section → Moved to Sales Tab

**Requirement:**
- Remove the standalone "Estimates" card/section from the Dashboard.
- Estimates become trackable through the new Sales Tab (Section 6), where each estimate is clearly tied to a named lead.

### 2.3 Remove "New Leads" Section

**Requirement:**
- Remove the "New Leads" section from the Dashboard.
- Leads-awaiting-contact is already tracked in the Leads tab — this section is redundant.

---

## 3. Customers

### 3.1 Duplicate Review & Merge (Customer-Level)

**Current state** (investigated):
- Duplicate detection only exists on **leads** (24-hour window on phone/email match) in `src/grins_platform/services/lead_service.py`.
- **No customer-level duplicate detection exists today.**
- Customer phone field has a unique DB constraint (`src/grins_platform/models/customer.py:76`) — prevents exact-phone duplicates at insert, but doesn't catch duplicates with different formatting or missing phone.
- No `duplicate_of` or merge-tracking field on Customer.

**Requirement:**
Build a duplicate-detection + review + merge flow accessible from the Customers overview (not per-customer).

**Design (based on Salesforce + HubSpot research):**

#### 3.1.1 Matching rules (weighted scoring, 0–100)

| Signal | Points |
|---|---|
| Normalized phone exact match (E.164) | +60 |
| Normalized email exact match (lowercased) | +50 |
| Jaro-Winkler name similarity ≥ 0.92 | +25 |
| Same normalized street address | +20 |
| Same ZIP + same last name | +10 |

#### 3.1.2 Confidence thresholds

- **≥ 80 points** — "High confidence duplicate" — top of review queue, pre-selected merge fields.
- **50–79 points** — "Possible duplicate" — shown in queue, requires review.
- **< 50 points** — Not flagged.
- **Never auto-merge.** Field services data is too consequential (wrong address = truck going to wrong house).

#### 3.1.3 UX flow

- New top-level action on Customers tab: **"Review Duplicates"** button with a count badge.
- Clicking opens a review queue listing suggested pairs sorted by confidence score descending.
- Each pair is clickable → opens a side-by-side comparison modal.
- User picks one record as the **primary**; each conflicting field has radio buttons (primary value selected by default).
- Preview the merged record before confirming.
- On merge:
  - Reassign all related jobs, notes, invoices, communications, agreements, and properties to the surviving record.
  - Soft-delete the duplicate (add `merged_into_customer_id` column on `customers` table — new migration).
  - Write an audit log entry (who, when, what fields survived) for rollback requests.

#### 3.1.4 Create-time prevention (Phase 2)

On customer create (including lead-conversion), synchronously run Tier 1 matches (phone/email exact) and show an inline **"Possible match found"** warning with a "Use existing customer" button. This catches ~70% of duplicates before they're created (Salesforce/Pipedrive standard).

**Implementation notes:**
- New table: `customer_merge_candidates` (id, customer_a_id, customer_b_id, score, created_at, resolved_at, resolution) — populated by a background job.
- New migration adds `merged_into_customer_id` nullable FK on `customers`.
- Background job: nightly sweep over all active customers, batch-compute scores, upsert candidates table.
- New API endpoints: `GET /api/v1/customers/duplicates`, `POST /api/v1/customers/:id/merge`.
- New frontend page: `CustomersPage` adds "Review Duplicates (N)" button in header.

**Merge conflict resolution rules** (for non-trivial cases):
- **Active Stripe subscriptions on both records:** Block the merge with an error message *"Both customers have active Stripe subscriptions ({sub_a_id}, {sub_b_id}). Cancel one subscription before merging."* Never silently cancel or combine Stripe subscriptions during a merge.
- **Active agreements on both records:** Reassign the agreements from the duplicate to the surviving record. Both end up under the surviving customer.
- **Pending appointments / scheduled jobs on both records:** Reassign both to the surviving record. Admin reviews the schedule afterward for conflicts.
- **Conflicting Stripe customer IDs:** The surviving record keeps its `stripe_customer_id`. The duplicate's `stripe_customer_id` is stored in the audit log for reference.
- **Mismatched phone / email where one is empty:** Surviving record keeps whichever field has a value. Admin can override via the side-by-side comparison.
- If any rule is unclear during implementation, prompt the admin with a modal rather than silently picking a side.

### 3.2 Service Preferences — Multi Date + Time

**Current state** (investigated):
- Customer model has `preferred_service_times` (JSON field) at `src/grins_platform/models/customer.py:144`.
- Currently stored as arbitrary JSON like `{"preference": "MORNING"}`.
- Set during onboarding (`src/grins_platform/services/onboarding_service.py`), updated via `customer_service.update_preferred_service_times()`.
- **No active scheduling flow reads this** — it's reference-only data today.

**Requirement:**
Extend the service preferences feature so users can configure **multiple date + time preferences** per customer, each tagged with a service type.

**Data model change:**

New schema for `customer.preferred_service_times` (JSON):

```json
[
  {
    "id": "uuid",
    "service_type": "spring_startup",
    "preferred_week": "week_of_2026-04-20",
    "preferred_date": "2026-04-22",
    "preferred_time_window": "morning",
    "notes": "Only MWF after 1pm"
  },
  {
    "id": "uuid",
    "service_type": "winterization",
    "preferred_week": "week_of_2026-10-12",
    "preferred_date": null,
    "preferred_time_window": "any",
    "notes": ""
  }
]
```

#### 3.2.1 Service Preferences Feed the Jobs Tab as Hints (Confirmed)

**Decision: Level B — hint on create.** Service preferences auto-fill the "Week Of" field on new jobs but never auto-create jobs themselves. Job creation still originates from leads, agreements, or manual admin action.

Specifics:
- When a job is created for a customer and a matching service preference exists (same `service_type`), the job's **"Week Of" field auto-populates** from the preference's `preferred_week` value.
- The preference's `notes` surface as a **read-only hint** on the job detail view (e.g., "Customer prefers MWF after 1pm").
- Preferences **never** trigger automatic job creation on a schedule — no background job spawns jobs from preferences. Jobs only exist because a user action (lead conversion, agreement renewal, manual create) asked for them.
- The admin can always override the auto-filled "Week Of" before saving.

**Rejected alternatives:**
- **Level A (reference only)** — defeats the purpose of structuring date/time preferences at all.
- **Level C (auto-create jobs on a schedule)** — too aggressive. Creates jobs without user action, which conflicts with the Leads-centric origin flow and risks surprises.

#### 3.2.2 Service Preferences UI (Customer Detail Page)

**Requirement:**
- On the customer detail page, add a new **"Service Preferences"** section.
- Shows a list of existing preferences (one row per entry in the JSON array described above).
- "Add Preference" button opens a modal with fields:
  - **Service type** (dropdown: Spring Startup, Mid-Season Inspection, Fall Winterization, Monthly Visit, Custom)
  - **Preferred week** (week picker, optional)
  - **Preferred specific date** (date picker, optional — overrides week if set)
  - **Time window** (dropdown: Morning / Afternoon / Evening / Any)
  - **Notes** (free text)
- Each existing row has Edit + Delete actions.
- Saving writes back to the `customer.preferred_service_times` JSON field.

### 3.3 Property Type Tagging

**Current state** (investigated):
- `property_type` field lives on the **Property** model (`src/grins_platform/models/property.py:103`), not Customer.
- Enum currently has only `RESIDENTIAL` and `COMMERCIAL` (`src/grins_platform/models/enums.py`).
- One customer can have multiple properties with different types.

**Requirement:**
Refactor property tagging into **three orthogonal attributes** on the Property model:

| Attribute | Type | Values | Notes |
|---|---|---|---|
| `property_type` | Enum | `residential`, `commercial` | Required. Existing field — no enum change needed. |
| `is_hoa` | Boolean | `true`/`false` | New field. Independent of residential/commercial — an HOA can be either. |
| `is_subscription_property` | Boolean (derived) | `true`/`false` | **Derived**, not stored. True if the property has an active `service_agreement` link. Displayed as the "Subbed to us" / "Subscription" tag — means the property was generated from the purchase of a service package. |

**Display:**
- Property list, customer detail, and job detail should show these as visual tags: **Residential** or **Commercial**, **HOA** (if true), **Subscription** (if true).
- Filter controls on Customers, Jobs, and Sales lists should support filtering by any combination.

**Implementation notes:**
- New migration: add `is_hoa` boolean column to `properties`, default `false`.
- "Subscription" check: `exists(SELECT 1 FROM service_agreements WHERE property_id = properties.id AND status = 'active')` — computed at query time, not stored.
- No separate "active job" tag — that was an earlier interpretation and has been removed per confirmed scope.

---

## 4. Leads

Leads = new inbound requests that have **not yet been contacted**. Once contacted and sorted, they leave the Leads list (either to Jobs or to Sales).

### 4.1 Delete a Lead / Auto-Remove on Move

**Requirement:**
- A lead must be manually deletable from the Leads tab.
- When a lead is moved to the Jobs tab or the Sales tab via the action buttons (Section 4.6), it must **automatically disappear from the Leads list entirely**. The lead row should no longer appear anywhere in the Leads view after the move.

**Manual delete UI:**
- Each lead row has a delete icon (trash can) visible on row hover or in the row's action menu.
- Clicking delete opens a confirmation modal:
  > **Delete Lead**
  >
  > This will permanently delete the lead "{customer_name}" from the system. This cannot be undone.
  >
  > [Cancel] [Delete]
- On confirm, the lead row is hard-deleted from the database.

**Implementation:**
- Use soft-delete semantics under the hood for the **move-out flow** (add a `moved_to` column on the `leads` table recording whether it went to jobs/sales, plus timestamps) so the data can be audited or recovered by support if needed. From the user's perspective, the lead is gone.
- The Leads list query filters out any lead where `moved_to IS NOT NULL`.
- **Manual delete** from the Leads tab trash button is a **hard delete** (actual row removal), consistent with "delete" meaning "gone for good." If the admin wants to preserve a record, they should move to Jobs/Sales instead of delete.

### 4.2 Columns — Remove Lead Source Coloring, Reorder

**Requirement:**
- Remove all color highlighting from the lead source column.
- Move the lead source column to the **far right** of the table.
- In the column slot previously occupied by lead source, show **"Job Requested"** (the service the customer asked for) so admin can scan and prioritize without clicking into each lead.

### 4.3 Add City Column

**Requirement:**
- Add a new column immediately after **Job Address** showing just the **city**.
- Derived from the existing address; no new data entry required.
- Purpose: quick visual grouping for scheduling/route planning.

### 4.4 Remove "Intake" Column

**Requirement:**
- Remove the "Intake" column from the Leads table.

### 4.5 Status Tags — Limit to Two (Confirmed)

**Requirement:**
Replace the current status options with exactly two tags — no other statuses exist on Leads:

1. **New** (default, assigned automatically on lead creation)
2. **Contacted (Awaiting Response)**

A lead that never gets a response stays in `Contacted (Awaiting Response)` until it is either manually deleted (Section 4.1) or moved to Jobs/Sales (Section 4.6). There is no separate `No Response`, `Not Interested`, or `Bad Lead` status.

#### 4.5.1 Last Contacted Date Column

- Add a new column: **Last Contacted Date**.
- Populated in two ways:
  1. **Manual:** Admin clicks the "Contacted" action button on a lead row. Writes `last_contacted_at = NOW()` on the lead.
  2. **Automatic:** Any outbound or inbound SMS/email tied to this lead (via the existing `SMSService` infrastructure from Section 8.1.4) auto-updates `last_contacted_at`. The inbound handler in `SMSService.handle_inbound()` needs a small extension to update `Lead.last_contacted_at` when an inbound reply correlates to a lead-owned sent message.
- The messaging system is already production-ready, so both paths ship in this update — the automatic path is not deferred.

### 4.6 Move-Out Action Buttons

**Requirement:**
Two action buttons per lead row:

1. **"Move to Jobs"** — shown when the job is confirmed and ready to schedule.
   - Auto-generates a new customer record (if one doesn't already exist for this lead).
   - Creates a job in the Jobs tab with status `TO_BE_SCHEDULED`.
   - Removes the lead from the Leads list per Section 4.1.

2. **"Move to Sales"** — shown when the job needs an estimate before it can be scheduled.
   - Auto-generates a new customer record (if one doesn't already exist for this lead).
   - Creates a Sales pipeline entry (status: `Schedule Estimate` — see Section 6.2).
   - Removes the lead from the Leads list per Section 4.1.

---

## 5. Work Requests → Sales

**Requirement:**
- **Delete the Work Requests tab entirely.** It is replaced by the new Sales tab (Section 6).
- Any existing work requests data should be migrated to the Sales tab as pipeline entries.

---

## 6. Sales Tab (New)

Sales = all customers who need an estimate before their job can be scheduled. Every time a lead is moved into Sales, it lands here.

### 6.1 Top Summary Boxes

**Requirement:**
- Keep the existing 4 summary boxes at the top unchanged.

### 6.2 Pipeline List View

**Requirement:**
Below the summary boxes, show a list view of all customers in the sales pipeline. Same UX patterns as the Leads tab (filtering, search, row click to expand/detail).

**Columns:**

| Column | Notes |
|---|---|
| Customer Name | |
| Customer Number | **Phone number** (interpreting source doc `"Customer Number"` as phone, following small-business CRM convention. If Kirill meant a numeric customer ID instead, this becomes a second column.) |
| Customer Address | Primary property address |
| Job Type | What service the customer wants |
| Status | One of: `Schedule Estimate`, `Estimate Scheduled`, `Send Estimate`, `Pending Approval`, `Send Contract` |
| Last Contact Date | Same semantics as Leads tab (Section 4.5.1) |

**Status pipeline (auto-advancing):**

```
Schedule Estimate → Estimate Scheduled → Send Estimate → Pending Approval → Send Contract → [Convert to Job]
```

Status **auto-advances** when the admin clicks the corresponding action button. No manual dropdown — clicking "Send Estimate" advances to `Pending Approval`, clicking "Send Contract" advances to the Convert-to-Job stage, etc.

**Status transition rules:**

| Action button | Pre-status | Post-status |
|---|---|---|
| (automatic on move from Leads → Sales) | — | `Schedule Estimate` |
| "Schedule Estimate" | `Schedule Estimate` | `Estimate Scheduled` |
| "Send Estimate" (triggers email or embedded sign flow) | `Estimate Scheduled` | `Pending Approval` |
| Customer approves (webhook from SignWell, or manual button) | `Pending Approval` | `Send Contract` |
| "Send Contract" | `Send Contract` | (advances to Convert to Job stage) |
| "Convert to Job" | Convert stage | Closed-Won, job created (Section 6.4) |
| "Mark Lost" (manual, any stage) | any | Closed-Lost (terminal) |

The admin can still **manually override** the status via a dropdown for exceptional cases, but the normal flow is button-driven.

**Note:** `Mark Lost` / `Closed-Lost` / `Closed-Won` terminal states are additions beyond what's literally in the source doc (`CRM_Changes_Update_2.md` lists only the 5 active pipeline statuses). They're included here because a pipeline without terminal states leaves entries stuck in limbo forever. If Kirill prefers to cut them from this update and just delete sales entries that don't convert, these rows can be removed.

### 6.3 Sales Scheduling Calendar (Separate from Job Calendar)

**Requirement:**
- Add a dedicated Sales scheduling calendar inside the Sales tab.
- Scope: **manual entry only** for the MVP. No route optimization, no AI suggestions, no integration with the main Jobs calendar.
- Purpose: schedule estimate appointments without polluting the main field services schedule.
- Later iterations can merge it with the main calendar if needed.

### 6.4 Convert to Job Button

**Default trigger (happy path):**
- The **"Convert to Job"** button becomes available **only after the SignWell webhook fires** confirming the customer has signed the contract. Until then, the button is hidden or disabled with the tooltip *"Waiting for customer signature."*
- Clicking the button:
  - Creates a new job in the Jobs tab with status `TO_BE_SCHEDULED`.
  - Pre-fills job data from the sales entry (customer, property, job type, any notes).
  - Moves the sales entry to a terminal "Closed-Won" state.

**Manual override (edge cases):**
For situations where the webhook can't arrive (customer signed on paper, vendor outage, customer approved verbally and will sign later), the admin has a **"Force Convert"** button that bypasses the signature check.

**Override confirmation flow** (required):
1. Admin clicks **"Force Convert to Job."**
2. Modal pops up with the warning:

   > **⚠️ Force Override — Signature Not Confirmed**
   >
   > We have not received confirmation that the customer has signed the estimate/contract. Proceeding will create a job in the Jobs tab without a verified signature on file.
   >
   > Are you sure you want to continue?
   >
   > [Cancel] [Force Convert]

3. On confirm:
   - The job is created as normal.
   - An audit log entry is written recording the override, the admin who did it, the timestamp, and the fact that no signature was on file at the time.
   - The sales entry advances to Closed-Won with an `override_flag = true` attribute so it's visible in reporting.

**Why this matters:** The force override gives you operational flexibility without silently allowing billing leaks. Auditable overrides mean you can spot if you're overriding too often (which might signal a broken SignWell integration, or sloppy sales practices).

### 6.5 Per-Lead Expanded View

Each row in the Sales pipeline, when clicked, opens a detail view with:

#### 6.5.1 Documents Section

Section listing all documents provided to the customer (estimates, contracts, photos, diagrams, reference docs). Upload, download, delete, and preview.

**Storage decision (investigated):**

Reuse the **existing S3 / `PhotoService` infrastructure** already in the codebase. No new storage backend is needed.

- **Existing service:** `src/grins_platform/services/photo_service.py` (already uses S3-compatible object storage with magic-byte validation, EXIF stripping, presigned URL generation, per-customer storage quotas).
- **Existing patterns to mirror:**
  - `CustomerPhoto` model at `src/grins_platform/models/customer_photo.py` (images only, 10 MB max).
  - `LeadAttachment` model at `src/grins_platform/models/lead_attachment.py` (images + PDFs + Word docs, 25 MB max).
  - `InvoicePDFService` at `src/grins_platform/services/invoice_pdf_service.py` (already generates PDFs and uploads to `/invoices/{uuid}.pdf` with presigned download URLs).
- **New work required:**
  1. Create a `CustomerDocument` model mirroring `CustomerPhoto` but accepting PDFs, images, and common doc types. Fields: `id`, `customer_id`, `file_key`, `file_name`, `document_type` (estimate | contract | photo | diagram | reference | signed_contract), `mime_type`, `size_bytes`, `uploaded_at`, `uploaded_by`.
  2. Add a new `UploadContext.CUSTOMER_DOCUMENT` enum value with allowed MIME types and max size (suggest 25 MB to match `LeadAttachment`).
  3. Add API endpoints:
     - `POST /api/v1/customers/{id}/documents` — upload
     - `GET /api/v1/customers/{id}/documents` — list
     - `GET /api/v1/customers/{id}/documents/{doc_id}/download` — presigned URL
     - `DELETE /api/v1/customers/{id}/documents/{doc_id}` — delete
  4. Any logged-in admin can view/download any customer document (single-admin scope — see Section 1.3).

**Signed contracts** returned from the e-signature provider (Section 6.5.3) are stored in the same `CustomerDocument` bucket with `document_type = "signed_contract"`, keeping everything discoverable from one place.

#### 6.5.2 Send Estimate via Email (Remote Path)

- Button: "Send Estimate for Signature (Email)."
- User uploads a PDF or selects an existing one from the customer's documents section.
- System sends the document to the customer's email for remote signing via SignWell (Section 6.5.3).
- Status auto-advances to `Pending Approval` (Section 6.2).
- Logs the send action in the communications history.
- **Edge case:** If the customer record has no email on file, the button is disabled with a tooltip *"Customer email required — add one on the customer record or use the on-site embedded signing path instead."*

#### 6.5.3 E-Signature — Dual Path (Email + Embedded On-Site)

**Provider decision:** **SignWell (API plan, pay-as-you-go).** Confirmed at the target volume of 200–450 signatures/month after a second vendor recheck.

**Target volume assumption:** ~100 jobs/week × 4.33 weeks/month = ~433 jobs/month. Not every job needs a fresh contract (recurring/subscription customers don't re-sign), so the realistic contract volume is **200–450 signatures/month**.

**Pricing at target volume:**

| Monthly signatures | SignWell PAYG ($0.10/sig, 25 free) |
|---|---|
| 200 | **$17.50/mo** |
| 300 | **$27.50/mo** |
| 450 | **$42.50/mo** |

- 25 signatures/month are free — the formula is `max(0, N - 25) × $0.10`.
- 10% discount available for annual billing.
- No per-seat fees on the API plan.
- No credit card required for sandbox/dev testing.
- HIPAA + SOC 2 compliant.

**Cost comparison at 300 signatures/month** (researched and validated):

| Vendor / Plan | Cost @ 300 sigs/mo | Embedded signing? |
|---|---|---|
| **SignWell PAYG** (winner) | **$27.50** | ✅ First-class iframe, sales-workflow demos available |
| Zoho Sign API | $150 | ✅ |
| eSignatures.com | $147 | ⚠️ iframe embed only |
| BoldSign Enterprise API | $225 | ✅ (Enterprise tier only) |
| PandaDoc API | $1,080 | ✅ |
| Dropbox Sign / DocuSign / SignNow | $100+ flat | ✅ |

**SignWell is the cheapest option by a 3–5× margin at every volume in the target range.**

**Break-even analysis** (does any flat-fee plan beat SignWell PAYG at higher volume?):

- Against BoldSign Enterprise API ($30/mo + $0.75 overage): BoldSign is cheaper only below ~65 sigs/mo. Above that, BoldSign's overage rate is punishing.
- Against Signeasy Intermediate ($125/mo flat): would only break even with SignWell PAYG at **~1,275 sigs/mo**.
- **There is NO flat-fee API plan that beats SignWell PAYG below ~1,200 signatures/month.**
- Your target of 200–450 sigs/month sits comfortably below every break-even point. The volume increase *strengthens* the SignWell case, not weakens it — all the flat-fee alternatives have tiny envelope quotas ($0.50–$4/doc overages) that punish scale-up.

**Rationale** (confirmed at the new volume):
1. **Still the cheapest by a large margin** — no other API vendor comes within 3× of SignWell's pricing at 200-450 sigs/mo.
2. **Meets all hard requirements** — embedded signing is a first-class product (SignWell ships sales-workflow demos), email-link signing is the default, identical REST API drives both, webhooks for `document_completed`.
3. **No per-seat lockup** on the API plan.
4. **Low lock-in** — webhooks deliver the signed PDF back so it can be stored in our own `CustomerDocument` bucket.
5. **Trade-off: no official Python or React SDK.** Both are DIY but trivial:
   - Python: ~200-line `httpx` wrapper around SignWell's REST API.
   - Frontend: ~50 lines of iframe + `postMessage` listener.
   - One-afternoon cost vs. paying 5× more elsewhere.

**Runner-up (if SignWell's embedded flow proves unworkable on rep tablets during prototyping):** **Zoho Sign API** at $0.50/envelope flat PAYG — cleanest flat-rate backup. Documented embedded signing, webhooks, Python SDK. Expect ~5× the cost ($100–$225/mo at target volume) in exchange for a more mature UI.

**Explicitly rejected (with reasons at the new volume):**
- **Dropbox Sign / DocuSign** — too expensive at this scale ($100+/mo flat).
- **BoldSign Enterprise API** — $0.75/envelope overage destroys it above ~65 sigs/mo. Would cost $150–$337/mo at target volume.
- **Zoho Sign** — $0.50/envelope effective rate whether PAYG or subscription; 5× SignWell.
- **OpenSign / Documenso self-hosted** — operational burden (uptime, audit trail, ESIGN/UETA legal compliance) not worth saving $15/month for a small team.
- **Yousign, Signeasy, Xodo Sign (Eversign)** — disqualified on base cost or tiny envelope quotas.
- **PandaDoc** — $4/doc overage, wildly expensive at scale.

**Hidden gotchas to watch:**
- SignWell PAYG billing runs on a **30-day usage cycle**, not calendar month. Monitor your first invoice.
- The SignWell **Business UI tier** ($30/mo) is *separate* from the API plan and does NOT grant API access — don't conflate them. If you also want a rep-facing web UI for drafting documents, layer Business on top (adds $30/mo to any of the numbers above).

**Caveat:** Pricing pages change. **Verify SignWell's current API plan rate at `signwell.com/pricing` before committing.** Research date: 2026-04-11.

##### 6.5.3.1 Email Path ("Send for Signature — Email")

- Sales rep clicks "Send Estimate for Signature" → "Email to customer."
- Backend calls SignWell's `POST /documents` endpoint with the uploaded PDF + customer email recipient.
- UI shows "Sent — awaiting signature" status badge.
- Webhook fires on `document_completed` → signed PDF fetched and stored in `CustomerDocument`. Sales status auto-advances.

##### 6.5.3.2 Embedded Path ("Sign Here Now")

- Sales rep clicks "Sign on-site" while physically with the customer.
- Backend calls SignWell's embedded signing API and returns a signing URL to the frontend.
- Frontend mounts the signing URL in an **iframe overlay**. Customer signs on the rep's tablet/phone using their finger.
- Frontend listens for `postMessage` events from the iframe to detect signature completion.
- On completion, the webhook fires → signed PDF fetched and persisted to `CustomerDocument` as `document_type = "signed_contract"`.
- Sales status auto-advances to the Convert-to-Job-ready state.

##### 6.5.3.3 Backend Integration

- **No official Python SDK.** Build a thin `SignWellClient` wrapper in `src/grins_platform/services/signwell/` using `httpx`. ~200 lines. Methods: `create_document_for_email()`, `create_document_for_embedded()`, `get_embedded_url()`, `fetch_signed_pdf()`, `verify_webhook_signature()`.
- **API key:** Stored as `SIGNWELL_API_KEY` env var alongside existing Stripe / CallRail keys.
- **New endpoints:**
  - `POST /api/v1/sales/{id}/sign/email` — trigger remote email flow.
  - `POST /api/v1/sales/{id}/sign/embedded` — return embedded signing URL for iframe.
  - `POST /api/v1/webhooks/signwell` — receive `document_completed` events, fetch signed PDF, persist to `CustomerDocument`.
- **Frontend:** No official React package. Build a `<SignWellEmbeddedSigner>` React component that mounts an iframe and listens for `postMessage` completion events. ~50 lines.

**Note:** SignWell is a net-new vendor dependency. The custom wrappers (Python + React) are small but real — budget them into the implementation plan.

### 6.6 Features Being Removed from the Old Work Requests Page

The following sub-tabs/features from the old Work Requests page are **removed** and **not replaced** in this update:

- Estimate Builder
- Media Library
- Diagrams
- Follow-Up Queue
- Estimates (sub-tab)

They may return in future iterations using third-party tooling.

### 6.7 Pending-Approval Placement (Confirmed)

The source doc says: *"If a staff gives an estimate to a client that needs approval, that customer should be added into the leads section until they approve the jobs."*

**Decision:** The customer **stays in the Sales pipeline** with status `Pending Approval`. They do **not** move back to the Leads tab. Leads is strictly for not-yet-contacted inbound — putting a contacted-and-estimated customer back into Leads would break the Leads-tab purpose described in Section 4.

**Behavior:**
- Status stays in Sales as `Pending Approval`.
- Dashboard surfaces a "Pending Estimate Approvals" count/alert.
- If/when the customer approves (via SignWell webhook or manual admin button) → advance to `Send Contract` → eventually `Convert to Job`.
- If the customer declines → terminal status (`Closed-Lost`) with an optional reason field.

---

## 7. Jobs

Jobs = approved work that needs to be scheduled. Must not contain anything still in the estimate phase.

### 7.1 Job Detail View — Address and Property Tags

**Requirement:**
When a user clicks into a job from the Jobs list, the detail view must clearly show:

1. **Job location** — the full street address of the property where the job will be performed (street, city, state, ZIP).
2. **Property type tag** — either **Residential** or **Commercial** (from the Property record).
3. **HOA tag** — shown only if `is_hoa = true` on the Property.
4. **Subscription tag** — shown only if the job was generated from a service agreement (i.e., the linked Property is a `is_subscription_property`, meaning the customer purchased a service package). Labeled as **"Subscription"** or **"Subbed to us."**

These tags mirror Section 3.3's property attributes. On the Jobs **list** view, surface the same tags as compact badges next to the row so users can scan for context without clicking in.

**Filter controls** on the Jobs list should support filtering by any combination: Residential/Commercial, HOA yes/no, Subscription yes/no.

### 7.2 Replace "Due By" with "Week Of"

**Current state** (investigated):
- The Job model does **not** have a field called `due_by`. It has `target_start_date` and `target_end_date` (`src/grins_platform/models/job.py:143–144`, both `Date`, nullable).
- The frontend labels `target_end_date` as **"Due By"** in the Jobs list column (`frontend/src/features/jobs/components/JobList.tsx:290–311`).
- `target_start_date` and `target_end_date` are populated by `job_generator.py` (line 137–138) when generating jobs from service agreements — and they're already written at **week boundaries**, meaning the underlying data already represents a week-level target.
- `target_start_date` is also used by the job repository filter (`job_repository.py:443–447`) as a "Target dates" range.

**Recommendation (Option C — in-place semantic rename):**

Rename the **UI label** from "Due By" to **"Week Of"**, swap the date picker for a **week picker**, and keep the existing `target_start_date` / `target_end_date` fields under the hood. The underlying data already represents weeks — this is a presentation change, not a schema change.

**Why this wins over the alternatives:**
- **No data migration** — the existing `target_start_date` / `target_end_date` already store week-aligned dates for agreement-generated jobs.
- **Matches source doc intent** — the source says "Instead of due by, let's make this column allow us to select which week out of the year for the job." That's replacement language.
- **Preserves the two-stage workflow** — the source describes setting a "Week Of" upfront and promoting it to a specific date+time the week prior. This maps cleanly to: `target_start_date`/`target_end_date` hold the week-level target, `scheduled_at` holds the promoted day-level datetime (already exists on the Job model).
- **Minimal regression surface** — backend filtering logic and agreement generation stay the same.

**Requirement:**
- Rename the UI column label from "Due By" to **"Week Of"** in `JobList.tsx:293`.
- Replace the existing date picker with a **week picker** that selects a week and writes `target_start_date` = Monday of the week, `target_end_date` = Sunday of the week.
- Display the value as `"Week of {M/D/YYYY}"` where the date shown is the Monday of the week (e.g., "Week of 4/20/2026").
- The week selection can be **auto-populated** from:
  - The customer's service preference (Section 3.2) when a job is created for a matching service type.
  - The customer's agreement schedule (Section 10.2) when the job is generated from a renewal.
- The admin can manually set or override the Week Of value at any time.

#### 7.2.1 Promotion from Week to Specific Date

- The week before the "Week Of" target, the admin can promote the job from a week-level assignment to a **specific date + time**.
- The job's scheduling view should surface any customer date/time constraints from Service Preferences (e.g., "Only MWF after 1pm") as a hint during promotion.
- Once a specific date+time is set, it feeds the normal scheduling flow (Section 8).

### 7.3 Missing Job-Level Actions (Reported Bugs)

Two issues were noted in the source doc:

- **"I cannot invoice the customer"**
- **"Can't mark the job as complete"**

**Requirement:**
- Investigate both under a separate bug-hunt document.
- Fix both as part of this update so that Section 9 (Invoicing) can actually be tested.
- Mark these as **blockers** — Invoice tab (Section 9) cannot ship/test without them.

---

## 8. Schedule

**Scope note:** The source doc references a *"PLEASE LOOK AT SCHEDULING TASK IN ASANA"* instruction. Per Kirill's direction, this section is locked based on **only the content of `CRM_Changes_Update_2.md`**. The Asana task is **not** being consulted for this update. If the Asana task contains additional scheduling requirements that contradict or extend this spec (e.g., map/route view, travel-time optimization, staff capacity rules), those will be handled as a separate follow-up, not within CRM Changes Update 2.

### 8.1 Admin-Only Capabilities (Schedule Builder)

Ideally the "Generate Routes" AI feature handles scheduling. For manual scheduling, admin needs these tools:

#### 8.1.1 Job Picker Popup

**Requirement:**
- When adding jobs to the schedule manually, open a popup that looks **exactly like the Jobs tab list** (same columns, same filter controls, same search).
- This avoids the admin needing to cross-reference two different UIs.

#### 8.1.2 Bulk Assignment

**Requirement:**
- Select multiple jobs from the picker.
- Assign all selected to a **specific date** + **specific staff member** in one action.
- Specify a global **time allocation per job** for the whole selection (e.g., "2 hours per job").
- Support adjustments per-job after bulk assignment.

#### 8.1.3 Unconfirmed vs Confirmed Visual Distinction

**Requirement:**
- Scheduled jobs should have a clear visual indicator for `unconfirmed` vs `confirmed` state.
- Likely: dashed border + muted background for unconfirmed; solid border + full color for confirmed.

#### 8.1.4 Y/R/C Scheduling Confirmation Flow (Full Spec — Build Now)

**Decision:** Build this feature in this update. The CallRail messaging infrastructure is production-ready, so there's no blocker.

**Critical terminology clarification** (from schema investigation):
- "Confirmed" / "unconfirmed" in the source doc refers to **`Appointment.status`**, not `Job.status`.
- `Job` statuses are: `TO_BE_SCHEDULED`, `IN_PROGRESS`, `COMPLETED`, `CANCELLED`.
- `Appointment` statuses are: `PENDING`, `SCHEDULED`, `CONFIRMED`, `EN_ROUTE`, `IN_PROGRESS`, `COMPLETED`, `CANCELLED`, `NO_SHOW`.
- When an admin schedules a job, an `Appointment` record is created with status `SCHEDULED`. The Y/R/C flow transitions that appointment's status, not the parent job's.

##### 8.1.4.1 Current CallRail Infrastructure (Investigated)

**Provider abstraction already exists** — no net-new abstraction needed:
- `BaseSMSProvider` Protocol at `src/grins_platform/services/sms/base.py` — defines `send_text()`, `verify_webhook_signature()`, `parse_inbound_webhook()`.
- `CallRailProvider` at `src/grins_platform/services/sms/callrail_provider.py` (299 lines) — fully implements the Protocol.
- `TwilioProvider` stub exists at `src/grins_platform/services/sms/twilio_provider.py` — **not yet functional**, but the swap path is already wired via `factory.py` (`SMS_PROVIDER=callrail|twilio|null` env var).

**Outbound SMS:**
- Entry point: `SMSService.send_message()` in `src/grins_platform/services/sms/sms_service.py` (lines 138–367).
- Signature: `send_message(recipient, message, message_type, consent_type, campaign_id, job_id, appointment_id)`.
- **`job_id` and `appointment_id` are already parameters on `send_message()` but are currently underused** — for Y/R/C, we need to start populating them.

**Inbound SMS webhook:**
- **Active and verified** at `POST /api/v1/callrail/webhooks/inbound` in `callrail_webhooks.py` (verified with real payload on 2026-04-08).
- Signature verified via HMAC-SHA1 (CallRail-specific; Twilio uses SHA256 when the swap happens).
- Routing logic in `SMSService.handle_inbound()` (lines 471–635) already handles:
  1. Opt-out keywords (`STOP`, `QUIT`, etc.)
  2. Poll replies (via `CampaignResponseService.record_poll_reply()` when `thread_id` is present)
  3. Fallback communications log

**Correlation key:** Inbound replies correlate to outbound sends via `provider_thread_id` on the `SentMessage` model — **not** via phone number (CallRail masks customer numbers in inbound payloads as `***3312`). This is critical: the Y/R/C correlation must use `thread_id`, not phone.

##### 8.1.4.2 Twilio Swap Considerations (Long-Term)

The user has stated that CallRail will be swapped for Twilio in the long term. The existing `BaseSMSProvider` Protocol is already sufficient to handle this swap — when the time comes:
- Implement the Twilio methods in the existing `TwilioProvider` stub.
- Adjust webhook signature verification (HMAC-SHA1 → HMAC-SHA256).
- Adjust webhook field mappings (CallRail `source_number` → Twilio `From`, etc.).
- Flip the `SMS_PROVIDER` env var.

**Requirement for this feature:** Do **not** write any CallRail-specific code in the Y/R/C handler. Use the abstract `InboundSMS` dataclass returned by the Protocol (which normalizes `from_phone`, `body`, `provider_sid`, `thread_id`, `conversation_id`). This way the Y/R/C flow works unchanged when Twilio replaces CallRail.

##### 8.1.4.3 What Needs to Be Built

| Component | State | Notes |
|---|---|---|
| Provider abstraction | ✅ Exists | Reuse `BaseSMSProvider` / `CallRailProvider`. |
| Outbound SMS pipeline | ✅ Exists | Reuse `SMSService.send_message()` with `job_id` + `appointment_id` populated. |
| Inbound webhook | ✅ Active & verified | Reuse `POST /api/v1/callrail/webhooks/inbound`. |
| Y/R/C keyword parser | ❌ New | Build new parser (separate from existing digit-based poll parser). |
| `job_confirmation_responses` table | ❌ New | Audit trail table. See schema below. |
| `JobConfirmationService` | ❌ New | Orchestrate parsing + appointment status transitions. |
| Inbound routing handler | ❌ New | Extend `SMSService.handle_inbound()` with a `_try_job_confirmation_reply()` branch. |
| "Reschedule Requests" admin queue UI | ❌ New | Frontend view for `R` responses. |
| New `MessageType.APPOINTMENT_CONFIRMATION` | ❌ New | Add enum value. |

##### 8.1.4.4 Outbound Message Spec

When the admin schedules a job and creates an `Appointment`:

1. The system sends an outbound SMS via `SMSService.send_message()` with:
   - `recipient`: customer phone
   - `message_type`: `MessageType.APPOINTMENT_CONFIRMATION` (new enum value)
   - `job_id`: populated
   - `appointment_id`: populated
2. Message body template:
   ```
   Hi {first_name}, this is Grins Irrigation. We've scheduled your {service_type} for {scheduled_date} at {scheduled_time_window}.

   Reply:
   Y = Confirm
   R = Request different time
   C = Cancel

   Reply STOP to opt out.
   ```
3. The resulting `SentMessage` row is persisted with `job_id`, `appointment_id`, `provider_thread_id` — this is the correlation anchor for the reply.

##### 8.1.4.5 Inbound Reply Parsing — Keyword Rules

New parser (`parse_confirmation_reply(body) -> ConfirmationKeyword | None`):

- Strip whitespace, punctuation, and lowercase.
- Match:
  - `y`, `yes`, `confirm`, `confirmed`, `ok`, `okay` → `CONFIRM`
  - `r`, `reschedule`, `reschedule me`, `different time`, `change time` → `RESCHEDULE`
  - `c`, `cancel`, `cancel me`, `cancelled` → `CANCEL`
- Anything else → `None` (falls through to manual review queue).

Matching is intentionally permissive because customers don't always follow instructions literally. False positives are mitigated by the fact that this parser only runs when the inbound reply's `thread_id` correlates to a `SentMessage` with `message_type = APPOINTMENT_CONFIRMATION`.

##### 8.1.4.6 New Handler Spec

Add to `SMSService.handle_inbound()`:

```python
async def _try_job_confirmation_reply(
    self, from_phone: str, body: str, provider_sid: str, thread_id: str
) -> dict[str, Any] | None:
    """Route inbound as a job confirmation (Y/R/C)."""
    # 1. Correlate: find the most recent SentMessage with
    #    provider_thread_id == thread_id AND appointment_id IS NOT NULL.
    # 2. If no match → return None (fall through to next handler).
    # 3. Parse body with parse_confirmation_reply().
    # 4. Persist to job_confirmation_responses.
    # 5. Dispatch to JobConfirmationService:
    #    - CONFIRM → transition Appointment.status from SCHEDULED → CONFIRMED
    #    - RESCHEDULE → create RescheduleRequest, send follow-up SMS
    #      asking for 2-5 alternative date/time options
    #    - CANCEL → transition Appointment.status → CANCELLED, notify admin
    # 6. Send an auto-reply SMS confirming the action:
    #    - CONFIRM: "Thanks! Your appointment is confirmed. See you then."
    #    - RESCHEDULE: "Got it — please reply with 2-5 date/time options
    #      that work for you (e.g., 'Tue 4/22 9am, Thu 4/24 2pm')."
    #    - CANCEL: "Understood. Your appointment is cancelled."
```

This handler is called from `SMSService.handle_inbound()` **before** the existing poll-reply handler, so appointment confirmations take priority over generic campaign polls.

##### 8.1.4.7 New Schema

**`job_confirmation_responses` table:**

| Column | Type | Notes |
|---|---|---|
| `id` | UUID | PK |
| `job_id` | UUID | FK → `jobs.id` |
| `appointment_id` | UUID | FK → `appointments.id` |
| `sent_message_id` | UUID | FK → `sent_messages.id`, the outbound SMS that triggered this reply |
| `customer_id` | UUID | FK → `customers.id` |
| `from_phone` | String | E.164 |
| `reply_keyword` | Enum | `CONFIRM` / `RESCHEDULE` / `CANCEL` |
| `raw_reply_body` | Text | Audit trail — the exact reply text |
| `provider_sid` | String | Inbound provider message id |
| `status` | Enum | `parsed` / `needs_review` / `processed` / `failed` |
| `received_at` | Timestamp | |
| `processed_at` | Timestamp | Nullable |

**`reschedule_requests` table (for `R` replies):**

| Column | Type | Notes |
|---|---|---|
| `id` | UUID | PK |
| `job_id` | UUID | FK → `jobs.id` |
| `appointment_id` | UUID | FK → `appointments.id` |
| `customer_id` | UUID | FK → `customers.id` |
| `original_reply_id` | UUID | FK → `job_confirmation_responses.id` |
| `requested_alternatives` | JSON | Parsed alternative date/times if customer replied with them |
| `raw_alternatives_text` | Text | Raw customer follow-up reply |
| `status` | Enum | `awaiting_alternatives` / `awaiting_admin_action` / `resolved` / `abandoned` |
| `created_at` | Timestamp | |
| `resolved_at` | Timestamp | Nullable |

##### 8.1.4.8 Admin Queue — Reschedule Requests

New frontend view: **"Reschedule Requests"** (accessible from Schedule tab sidebar or a dashboard alert).

- Shows all open `reschedule_requests` grouped by status.
- Each row: customer name, original appointment, requested alternatives (parsed or raw text), received timestamp, action buttons.
- Actions: **"Reschedule to Alternative"** (opens appointment editor pre-filled with a selected alternative), **"Contact Customer"** (opens a manual SMS composer), **"Mark Resolved"** (closes the request).

##### 8.1.4.9 Dependencies Summary

- No net-new messaging infrastructure required — everything stacks on existing provider abstraction.
- New schema migrations: `job_confirmation_responses`, `reschedule_requests`.
- New enum value: `MessageType.APPOINTMENT_CONFIRMATION`.
- New service: `JobConfirmationService`.
- New frontend page: Reschedule Requests queue.

**Reference doc:** `feature-developments/CallRail collection/CallRail_Scheduling_Poll_Responses.md` — similar correlation pattern but for polls, not Y/R/C. The Y/R/C handler should sit alongside the poll handler, not replace it.

#### 8.1.5 Auto-Complete Status Update

**Requirement:**
- When a staff member marks a job as complete (Section 8.2.6 Job Complete button), the job status automatically transitions from its current state (typically `IN_PROGRESS`) to `COMPLETED`.
- Once a job is `COMPLETED`, it is archived out of the active schedule view (still visible in the Jobs tab with a "Completed" filter applied, but not in the open schedule).

### 8.2 Staff + Admin Capabilities

#### 8.2.1 View Job Details

**Requirement:**
- Any logged-in user sees the full job detail view (single-admin scope — see Section 1.3). All actions including delete are available.
- The "staff cannot delete" restriction from the source doc is **deferred** — it will return once the staff/admin split is implemented in a future update.

#### 8.2.2 On-Site Payment Collection

**Requirement:**
- Staff can collect payment on-site via the job detail view.
- Recording a payment:
  - Updates the appointment slot with payment details (amount, method, timestamp).
  - Auto-updates the customer record in the Customers tab.
  - Auto-updates the Invoice tab (Section 9).
  - Marks the job's linked invoice as paid (if one exists).

#### 8.2.3 On-Site Invoice Creation

**Requirement:**
- Staff can create an invoice on the spot using an invoice template.
- Template-based — pre-filled with customer + job data.
- Send the invoice to the customer email with a payment link.
- Auto-updates the Customer tab and the Invoice tab on creation.

#### 8.2.4 Customer Notes & Photos

**Requirement:**
- Staff can add notes and photos to the job from the job detail view.
- Both auto-sync to the Customer record in the Customers tab.

**Storage:**
- **Photos** reuse the existing `CustomerPhoto` model at `src/grins_platform/models/customer_photo.py` (images only, 10 MB max, S3-backed via `PhotoService`). Photos taken from a job are linked to the `customer_id` **and** the `job_id` for contextual retrieval — add a new nullable `job_id` FK column to `customer_photos` if it doesn't already exist.
- **Notes** are plain text entries on a new or existing `customer_notes` table with `customer_id`, `job_id` (nullable), `body`, `created_at`, `created_by` fields. If a notes model already exists, reuse it and add the `job_id` link.
- No new storage infrastructure required — everything reuses the S3 / `PhotoService` stack already investigated in Section 6.5.1.

#### 8.2.5 Google Review Push Notification

**Requirement:**
- Staff can trigger an SMS to the customer requesting a Google review with a deep link.
- Template message + tracked link (`https://g.page/r/...` or similar — review link stored in an env var / settings value).
- Sent via the existing `SMSService.send_message()` infrastructure (reuses the CallRail provider abstraction from Section 8.1.4 — no new plumbing).
- Logged in the communications history as `MessageType.GOOGLE_REVIEW_REQUEST` (new enum value).

#### 8.2.6 Job Status Buttons

**Requirement:**
Staff have three status-change buttons on the job detail view:

1. **On My Way** — notifies the customer via SMS (using the existing `SMSService.send_message()` infrastructure from Section 8.1.4 — no gating), logs timestamp.
2. **Job Started** — logs timestamp.
3. **Job Complete** — logs timestamp, transitions `Job.status` to `COMPLETED`.

**Payment-before-complete rule — Warning with Override (Confirmed):**

The rule from the source doc — *"Staff can't complete a job until payment is collected or invoice is sent"* — is enforced as a **warning with required override**, not a hard block.

Flow:
1. Admin clicks **"Job Complete."**
2. System checks: has payment been collected on this job OR has an invoice been sent?
3. If **yes** → job completes normally.
4. If **no** → confirmation modal pops up:

   > **⚠️ No Payment or Invoice on File**
   >
   > This job has no payment collected and no invoice sent. Completing it now means the customer may not be billed.
   >
   > Are you sure you want to mark this job complete?
   >
   > [Cancel] [Complete Anyway]

5. On **Complete Anyway** → job completes, audit log entry records the override (who, when, the fact that no payment/invoice was on file).

**Why not a hard block:** Field-services reality has edge cases — customer hands over cash, sales rep agrees to invoice next week, payment system is offline. A hard block creates friction in those cases. The warning + override with audit trail gives you enforcement AND flexibility AND visibility to catch abuse.

#### 8.2.7 Time Tracking (Metadata Collection)

**Requirement:**
- System automatically tracks time elapsed between each of the three status buttons (On My Way → Job Started → Job Complete).
- Track per job type + per staff member.
- Store this as structured metadata for future use:
  - Improved scheduling (better time estimates per job type).
  - Staff productivity reporting.
  - Route optimization input.
- No user-facing display required in this update — just collect the data.

---

## 9. Invoice

**Blocker:** Section 9 cannot be built or tested until the Section 7.3 bugs are fixed (`can't invoice`, `can't mark complete`). Call this out at the top of the implementation plan.

### 9.1 Invoice List View — Filtering (All Axes Supported)

**Requirement:**
Support filtering invoices on **every attribute** the invoice has. The source doc says *"Give functionality to filter invoices based on whatever I want"* — this is a literal requirement. All filter axes are equally supported; none are demoted to secondary.

**Filter axes (all primary):**

| # | Filter | Control type |
|---|---|---|
| 1 | **Date range** | Date picker (created date, due date, paid date — separate selectors) |
| 2 | **Status** | Multi-select (`Complete`, `Pending`, `Past Due`) |
| 3 | **Customer** | Searchable dropdown with autocomplete |
| 4 | **Job** | Searchable dropdown |
| 5 | **Amount / Cost** | Min/max range inputs |
| 6 | **Payment type** | Multi-select (`Credit Card`, `Cash`, `Check`, `ACH`, `Other`) |
| 7 | **Days until due** | Numeric range (e.g., "due in 0-7 days") |
| 8 | **Days past due** | Numeric range (e.g., "past due 30+ days") |
| 9 | **Invoice number** | Text input / exact match |

**UI layout:**

Because supporting 9 primary filters in a single toolbar would be overwhelming, use a **filter panel pattern**:

- Collapsible left sidebar OR top "Filters" button that opens a drawer.
- All 9 filters available simultaneously inside the panel, grouped by category.
- Active filters shown as removable chip badges above the invoice list (e.g., `[Status: Past Due ×]` `[Days past due: 30+ ×]`).
- "Clear all filters" button.
- Filter state persists in URL query params so admin can bookmark or share a filtered view.
- "Save this filter" option (persisted to the user's account) for commonly used filter combinations (e.g., "My past-due invoices over 30 days").

**Implementation notes:**
- Backend: extend the invoices list endpoint with all filter params (likely `GET /api/v1/invoices?status=past_due&days_past_due_min=30&...`).
- Frontend: reusable `FilterPanel` component that can take a filter schema and render controls automatically.
- This is genuinely a larger piece of frontend work than a simple list view — budget for it in the implementation plan.

### 9.2 Invoice List Columns

| Column |
|---|
| Invoice Number |
| Customer Name |
| Job (link to job detail) |
| Cost |
| Status (`Complete`, `Pending`, `Past Due`) |
| Days Until Due |
| Days Past Due |
| Payment Type |

### 9.3 Visual Status Colors

**Requirement:**
- `Complete` → **green**
- `Pending` → **yellow**
- `Past Due` → **red**
- Colors applied to status badge and optionally to the row background (subtle tint).

### 9.4 Mass Notification Actions

**Requirement:**
- Admin can bulk-notify:
  - All customers with past-due invoices.
  - All customers with invoices about to be due (configurable window, e.g., 3 days out).
  - All customers with lien notice eligibility (see below for eligibility definition).
- Each batch uses a configurable template.
- SMS sending reuses the existing `SMSService.send_message()` infrastructure from Section 8.1.4 — no gating, no new messaging plumbing.
- Email sending reuses the existing email infrastructure (same system that sends onboarding confirmations and terms acceptance receipts).

**Lien notice eligibility (needs product decision):**

The source doc mentions "lean notices" (typo in source) but doesn't define the criteria. Proposed default — to be confirmed in a follow-up — is: customers with at least one invoice that is **60+ days past due AND over $500**. This threshold should live in a settings/config file so it can be adjusted without a code change.

### 9.5 Customer Data Sync

**Requirement:**
- All invoice state changes (created, paid, past-due, void) must reflect in the Customer detail view in real-time.
- This is a downstream consequence of Section 8.2.2 and 8.2.3 being wired correctly — no separate work.

---

## 10. Other

### 10.1 Package Onboarding → Week-Based Job Auto-Population

**Current state** (investigated — this has to be built from scratch):

1. **No week selector exists in onboarding today.** The onboarding form (`src/grins_platform/api/v1/onboarding.py:111–142`) only captures a coarse `preferred_schedule` timeline with values `ASAP`, `ONE_TWO_WEEKS`, `THREE_FOUR_WEEKS`, `OTHER`. This is stored on the `ServiceAgreement` model but does not map to specific weeks per service.
2. **Jobs ARE auto-generated at onboarding** — the Stripe `checkout.session.completed` webhook (`src/grins_platform/api/v1/webhooks.py:217–471`, line 400 specifically) calls `job_gen.generate_jobs(agreement)` right after onboarding.
3. **BUT `target_start_date` and `target_end_date` on generated jobs are hardcoded to calendar months** (`src/grins_platform/services/job_generator.py:126–142`):
   - Spring Startup → April 1–30
   - Mid-season Inspection → July 1–31
   - Fall Winterization → October 1–31
   - Monthly visits (Premium tier) → whole calendar months
4. **There is no mechanism today to pass customer-selected week preferences into the job generator.**

**Requirement:**

Build the week selection feature end-to-end so a customer can pick a specific week for each service in their package during onboarding, and those weeks flow through to the Jobs tab as pre-populated `target_start_date` / `target_end_date` values.

##### 10.1.1 Backend Schema Change

- Add a new field to `ServiceAgreement`: `service_week_preferences: JSON` (nullable).
- Schema:
  ```json
  {
    "spring_startup": "2026-04-20",
    "mid_season_inspection": "2026-07-13",
    "fall_winterization": "2026-10-12",
    "monthly_may": "2026-05-04",
    "monthly_june": "2026-06-01"
  }
  ```
- Each key is a service type identifier; each value is the ISO date of the **Monday** of the selected week.
- New migration: add the column, default `NULL`.

##### 10.1.2 API Extension

- Extend `CompleteOnboardingRequest` schema in `src/grins_platform/api/v1/onboarding.py` with a new optional field:
  ```python
  service_week_preferences: dict[str, str] | None = Field(
      default=None,
      description="Per-service week preferences (Monday of selected week, ISO format)"
  )
  ```
- Extend `OnboardingService.complete_onboarding()` to accept and persist this to the new `ServiceAgreement.service_week_preferences` column.

##### 10.1.3 Frontend Onboarding UI

- Add a new step to the onboarding wizard (after property details, before completion): **"Pick Your Service Weeks."**
- For each service included in the customer's package (dynamically read from `ServiceAgreementTier.services` or equivalent), show a **week picker** component:
  - Calendar view showing weeks (highlight Mondays).
  - Restricted to the valid month range for that service (e.g., Spring Startup selectable only in April-May weeks).
  - Default selection: middle week of the valid range.
  - Tooltip explaining that the customer can request a specific day closer to the target week later.
- Submit all selected weeks as `service_week_preferences` in the `POST /onboarding/complete` request.

##### 10.1.4 Job Generator Update

- Modify `JobGenerator.generate_jobs(agreement)` in `src/grins_platform/services/job_generator.py`:
  - Read `agreement.service_week_preferences` (may be `None` for agreements created before this change or for customers who skip the week picker).
  - For each service being generated, **if** a matching key exists in `service_week_preferences`:
    - Set `target_start_date` = Monday of selected week.
    - Set `target_end_date` = Sunday of selected week.
  - **Otherwise** fall back to the existing calendar-month logic (preserves backward compatibility for existing agreements).
- This change is **additive** — existing agreements without week preferences continue to work exactly as before.

##### 10.1.5 Display on Jobs Tab

- No change needed to Section 7.2 — the "Week Of" column already reads from `target_start_date` / `target_end_date`, so once the job generator writes the week-aligned dates, the Jobs tab displays them correctly.
- Jobs originating from onboarding should be visually tagged as **"From Subscription"** (per Section 3.3's `is_subscription_property` derived attribute) so the admin knows which jobs came from auto-generation vs. manual/lead creation.

##### 10.1.6 Implementation Order

The work is tightly coupled and should be done in this order:

1. Schema migration for `ServiceAgreement.service_week_preferences`.
2. Backend: update `OnboardingService.complete_onboarding()` and `CompleteOnboardingRequest` schema.
3. Backend: update `JobGenerator.generate_jobs()` to respect week preferences.
4. Frontend: add the week picker step to the onboarding wizard.
5. End-to-end test: new customer signs up for Premium tier → picks weeks → jobs appear in Jobs tab with correct `target_start_date` / `target_end_date`.

### 10.2 Service Contract Auto-Renewal → Review Queue for Next-Year Jobs

**Decision: Queue for review** (not auto-create directly). When a service contract reaches its renewal date, the system generates proposed jobs for the new contract year and places them in a review queue. The admin must explicitly approve the batch before the jobs hit the Jobs tab.

**Why the review queue over auto-create:**
- Contract renewals are important enough to warrant explicit admin confirmation.
- Catches mistakes before they hit the live schedule (e.g., customer dropped a service, pricing changed, agreement was modified since last year).
- A bad auto-created batch would silently pollute the Jobs tab — admin might not notice until the day of the first job.
- The review queue is a lightweight bottleneck, not a heavy process: in the common case, the admin clicks "Approve All" and it's done.

##### 10.2.1 Trigger

The renewal trigger runs when:
- A `ServiceAgreement` has `auto_renew = true` AND its `renewal_date` has passed, OR
- An admin manually triggers a renewal from the Agreements tab.

Existing renewal flow: the Stripe `invoice.paid` webhook at `src/grins_platform/api/v1/webhooks.py:561` currently calls `job_generator.generate_jobs(agreement)` on renewal. This behavior must change for post-renewal flows: instead of writing jobs directly to the Jobs tab, the generator writes to the new review queue table described below.

##### 10.2.2 New Schema

**`contract_renewal_proposals` table:**

| Column | Type | Notes |
|---|---|---|
| `id` | UUID | PK |
| `service_agreement_id` | UUID | FK → `service_agreements.id` |
| `customer_id` | UUID | FK → `customers.id` (denormalized for fast admin queries) |
| `status` | Enum | `pending_review`, `approved`, `rejected`, `partially_approved` |
| `proposed_job_count` | Integer | Number of jobs in the batch |
| `created_at` | Timestamp | When the renewal was processed |
| `reviewed_at` | Timestamp | Nullable — when admin took action |
| `reviewed_by` | String | Admin username (single-admin scope — see Section 1.3) |

**`contract_renewal_proposed_jobs` table:**

| Column | Type | Notes |
|---|---|---|
| `id` | UUID | PK |
| `proposal_id` | UUID | FK → `contract_renewal_proposals.id` |
| `service_type` | String | Spring startup, winterization, etc. |
| `target_start_date` | Date | Monday of proposed week (from prior year's preferences) |
| `target_end_date` | Date | Sunday of proposed week |
| `status` | Enum | `pending`, `approved`, `rejected`, `modified` |
| `proposed_job_payload` | JSON | Full payload that will be used to `Job()` on approval |
| `admin_notes` | Text | Optional — admin can add notes before approving |

##### 10.2.3 Proposal Generation Logic

When a contract renews:
1. Read the prior year's `service_week_preferences` from the `ServiceAgreement` (populated at onboarding — see Section 10.1).
2. For each service in the renewed agreement, generate a proposed job:
   - `service_type` = same as prior year.
   - If prior-year week preferences exist for this service: `target_start_date` / `target_end_date` = same week-of-year as prior year, rolled forward by one year (e.g., "week of April 20, 2026" → "week of April 19, 2027").
   - **Fallback:** if the agreement has `service_week_preferences = NULL` (existing agreements from before the Section 10.1 week selector shipped), use the hardcoded calendar-month defaults from `job_generator.py` (Spring Startup = April 1–30, etc.). The admin can still edit each proposed job's Week Of before approving.
3. Write the proposal row plus one proposed-job row per service to the review queue tables.
4. Fire a dashboard alert: **"1 contract renewal ready for review: {customer_name}."**

##### 10.2.4 Admin Review UI

New page: **"Contract Renewal Reviews"** (accessible from the Agreements tab OR from a dashboard alert card).

**List view:**
- One row per pending `contract_renewal_proposals`.
- Columns: Customer, Agreement (package name), Proposed job count, Created date, Action button.
- Filters: by status, by date range.

**Detail view** (click a proposal):
- Customer info at top.
- Table of proposed jobs with editable fields:
  - Service type (read-only).
  - Week Of (editable — admin can shift to a different week).
  - Notes (free text).
  - Per-job status indicator + toggles: ✅ Approve / ❌ Reject / ✏️ Modify.
- Bulk actions:
  - **"Approve All"** — one-click approval of the whole batch; creates real `Job` records in the Jobs tab with `target_start_date` / `target_end_date` from the proposals.
  - **"Reject All"** — marks the proposal as rejected; no jobs are created. (Useful if the customer is actually not renewing and the webhook fired by mistake.)
- If admin approves some and rejects others, status becomes `partially_approved`.

##### 10.2.5 On Approval

When a proposal (or individual proposed job) is approved:
1. Real `Job` records are created via the existing `job_generator` logic, but using the proposal's week-level dates rather than the hardcoded calendar-month defaults.
2. The proposed-job row is marked `approved` with a reference to the new `Job.id`.
3. The parent proposal's status advances based on whether all children were approved or only some.
4. Jobs appear in the Jobs tab immediately, tagged as `Subscription` via Section 3.3's `is_subscription_property` check.

##### 10.2.6 Implementation Order

1. Schema migrations for `contract_renewal_proposals` + `contract_renewal_proposed_jobs`.
2. Modify `invoice.paid` webhook handler (`webhooks.py:561`) to write proposals to the review queue instead of calling `job_generator.generate_jobs()` directly.
3. New service: `ContractRenewalReviewService` — generate proposals, approve, reject, modify.
4. New API endpoints under `/api/v1/contract-renewals/`.
5. New frontend page: Contract Renewal Reviews list + detail.
6. New dashboard alert card for pending reviews.

---

## 11. Deferred / Gated Items

These items are **explicitly out of scope or gated** for this update:

| Item | Reason |
|---|---|
| Generate Routes (AI routing) | Upstream team still building — waiting to test. |
| Marketing features | Flagged lower-priority than Generate Routes + Messaging. Explicitly out of scope for this update. |
| Accounting features | Flagged lower-priority than Generate Routes + Messaging. Explicitly out of scope for this update. |
| Estimate Builder / Media Library / Diagrams / Follow-Up Queue | Removed from Work Requests, not replaced. |
| Cross-CRM calendar merge (Sales + Jobs) | Separate calendars for MVP. |
| Staff/admin role split | Deferred. Single admin login only — see Section 1.3. |
| DocuSign/HelloSign embedded e-sig | Replaced by SignWell PAYG (Section 6.5.3). |
| Asana "scheduling task" content | Not consulted for this update — see scope note at top of Section 8. |

**Note:** The messaging system is NOT deferred. The CallRail SMS provider abstraction is production-ready and the inbound webhook is verified. All SMS-related features in Sections 8.1.4, 8.2.5, 8.2.6, and 9.4 reuse the existing `SMSService` / `BaseSMSProvider` infrastructure — no new messaging plumbing is required.

---

## 12. Open Questions

### Resolved

- ~~**OQ-1** — Admin password~~ → **Resolved.** Claude proposed `Grins-Admin-Valve-Rain2026!` (primary) with alternates. Kirill to confirm final value. See Section 1.1.
- ~~**OQ-2** — Staff user management UI~~ → **Resolved.** Deferred. Single admin login only for this update. See Section 1.3.
- ~~**OQ-3** — Service preferences auto-populate~~ → **Resolved.** Level B: hint on create. Auto-fills "Week Of" on new jobs; never auto-creates jobs. See Section 3.2.1.
- ~~**OQ-4** — "Whether it's a job" property tag~~ → **Resolved.** Dropped. Only 3 tags: Residential/Commercial, HOA, Subscription. See Section 3.3.
- ~~**OQ-5** — Leads removal on move~~ → **Resolved.** Disappear entirely from view. Soft-delete under the hood for audit/recovery. See Section 4.1.
- ~~**OQ-6** — Lead status values~~ → **Resolved.** Only `New` and `Contacted (Awaiting Response)`. See Section 4.5.
- ~~**OQ-7** — Sales pipeline auto-advance~~ → **Resolved.** Auto-advance on button click, with manual-override dropdown for edge cases. See Section 6.2.
- ~~**OQ-8** — Convert to Job trigger~~ → **Resolved.** Button appears only after SignWell signature webhook fires. Force Override button available with confirmation popup (no reason field). See Section 6.4.
- ~~**OQ-9** — Document storage~~ → **Resolved.** Reuse existing S3 / `PhotoService` infrastructure. New `CustomerDocument` model mirrors `CustomerPhoto`. See Section 6.5.1.
- ~~**OQ-10** — E-signature provider~~ → **Resolved.** **SignWell** on pay-as-you-go plan ($0.10/signature, ~$5-20/mo). Custom thin wrappers for Python + React. See Section 6.5.3.
- ~~**OQ-11** — Pending Approval placement~~ → **Resolved.** Stays in Sales tab with `Pending Approval` status. Does not bounce back to Leads. See Section 6.7.
- ~~**OQ-12** — Week Of vs Due By~~ → **Resolved.** In-place semantic rename: swap UI label + date picker, keep `target_start_date`/`target_end_date` under the hood. See Section 7.2.
- ~~**OQ-14** — Y/R/C confirmation flow timing~~ → **Resolved.** Build it now in full. CallRail provider abstraction is already solid, inbound webhook is verified live, `BaseSMSProvider` Protocol handles the future Twilio swap. Full spec in Section 8.1.4.
- ~~**OQ-15** — "Can't complete without payment" enforcement~~ → **Resolved.** Warning with override confirmation popup (no reason field required). See Section 8.2.6.
- ~~**OQ-16** — Invoice filter priorities~~ → **Resolved.** All 9 filter axes supported as primary. Filter panel UI pattern. See Section 9.1.
- ~~**OQ-17** — Package onboarding flow~~ → **Resolved.** New-customer subscription purchase flow, post-Stripe-checkout onboarding wizard. Investigation confirmed: week selector does NOT exist today. Full build spec in Section 10.1.

### Still Open

None. All 18 open questions have been resolved.

### Newly Resolved (This Round)

- ~~**OQ-13** — Asana scheduling task~~ → **Resolved.** Not consulted. Section 8 is locked based on `CRM_Changes_Update_2.md` content only. Any additional requirements in the Asana task will be handled as a separate follow-up outside this update. See the scope note at the top of Section 8.
- ~~**OQ-18** — Contract auto-renewal mode~~ → **Resolved.** Review queue (not auto-create). Renewed contracts generate proposed jobs in a new review queue; admin must approve the batch before jobs hit the Jobs tab. Full spec in Section 10.2.

---

## Implementation Blockers Summary

Before much of this can ship:

1. **Section 7.3 bugs** — "can't invoice," "can't mark complete." Blocks Section 9 (Invoice tab) entirely.
2. **SignWell account provisioning** — Required for Section 6.5.3. Need API key, verify embedded signing works during prototyping, set up webhook endpoint.
3. **Messaging already production-ready** — No longer a blocker. Section 8.1.4 (Y/R/C) can be built immediately on top of the existing CallRail provider abstraction.
4. **Generate Routes upstream work** — Not a blocker for this update, but informs Schedule section final design.

---

*All 18 open questions resolved. Document is finalized and ready for implementation planning.*
