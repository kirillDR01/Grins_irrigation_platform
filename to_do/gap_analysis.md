# Gap Analysis: CRM Changes & System Requirements vs Current Codebase

**Analysis Date:** 2026-03-23
**Branch:** dev
**Sources:** `CRM Changes(1).md`, `System Requirments (4).md`

---

## CRM Changes(1).md — Item-by-Item Status

### OVERALL

| # | Requirement | Status | Notes |
|---|------------|--------|-------|
| 1 | Remove all fake/test data | **NOT DONE** | Demo seed migration still active (`20250626_100000_seed_demo_data.py`, `20250627_100000_seed_staff_availability.py`). Demo customers, staff, and jobs remain in the database. |
| 2 | Remove all test/fake staff | **NOT DONE** | Demo staff seeded in the same migration, still present. |
| 3 | Fix random logout issue (logged out even while using system) | **UNABLE TO VERIFY** | Would require runtime testing; no obvious auth timeout bug visible in code. Needs manual QA. |

---

### DASHBOARD

| # | Requirement | Status | Notes |
|---|------------|--------|-------|
| 1 | Alerts: click alert → navigate to section AND highlight the specific item (job, lead, etc.) | **PARTIAL** | Alert for "Overnight Requests" exists in `DashboardPage.tsx`. "Review Now" links to `/jobs?status=requested`, but the `JobList` component does NOT read URL query params to auto-filter. No highlighting of the specific item. |
| 2 | Messages: show count of messages needing to be "addressed" (not read/unread tracking) | **NOT DONE** | "Messages" widget currently displays **customer counts** (`total_customers` / `active_customers`), not actual messages. No messaging or communications tracking system exists on the dashboard. A `CommunicationsQueue` component exists but is not used. |
| 3 | Invoices on dashboard: show count of pending invoices only (not completed) | **NOT DONE** | Dashboard invoice metric calculates from **job statuses** (`requested + approved`), not actual invoice data. Separate `OverdueInvoicesWidget` and `LienDeadlinesWidget` exist but don't show a simple pending invoice count. |
| 4 | New Leads: click the box → highlight uncontacted leads | **PARTIAL** | Card exists showing `new_leads_today` and `uncontacted_leads` count with color-coded urgency. Clicking navigates to `/leads?status=new`, but `LeadsList` does NOT auto-filter from URL params. No highlighting of specific uncontacted leads. |
| 5 | Job by status: track these specific statuses — New Requests (Need to contact), Estimates, Pending Approval, To be scheduled, In Progress, Complete | **PARTIAL** | Shows 5 statuses: Requested (yellow), Approved (blue), Scheduled (purple), In Progress (orange), Completed (green). These don't exactly match the requested status names. Missing "Estimates" and "Pending Approval" as distinct statuses. |
| 6 | Job by status: click a status → highlight those specific jobs | **NOT DONE** | Status counts are plain display-only text with no click handlers. A "View All" button links to `/jobs` without any filters applied. Users must manually select filters on the Jobs page. |

---

### CUSTOMERS

| # | Requirement | Status | Notes |
|---|------------|--------|-------|
| 1 | Review and delete duplicate customers | **PARTIAL** | Duplicate **prevention** exists: unique phone constraint in DB, phone lookup endpoint (`GET /customers/lookup/phone/{phone}`), email lookup endpoint. Soft delete via `DELETE /customers/{customer_id}` works with confirmation dialog. **Missing:** No admin panel to review, compare, or merge existing duplicate customers. |
| 2 | Custom notes for customer | **PARTIAL** | Backend `internal_notes` TEXT field exists on Customer model (`customer.py` line 150). Property-level `special_notes` field works with UI. **Missing:** `internal_notes` is NOT exposed in `CustomerResponse` API schema and NOT editable in the frontend `CustomerForm` or `CustomerDetail` components. |
| 3 | Custom photos for customer | **NOT DONE** | No photo/image fields in Customer or Property models. No file upload handlers or storage integration. No photo display in customer detail page. Would require: DB fields, file storage (S3/similar), upload endpoint, and UI components. |
| 4 | Invoice history review per customer | **PARTIAL** | Invoices are linked to customers via `customer_id` FK. Service history endpoint (`GET /customers/{customer_id}/service-history`) returns total jobs, last service date, and total revenue. **Missing:** Invoice history is NOT displayed directly on the customer detail page — requires navigating to the separate Invoices section. |
| 5 | Customer availability/preferred service times section | **PARTIAL** | `preferred_service_times` JSON field exists in DB model and displays on customer detail page (Morning/Afternoon/No Preference in "Service Preferences" section). **Missing:** NOT editable from the UI — no edit interface in `CustomerForm` or `CustomerDetail`. |

---

### LEADS

| # | Requirement | Status | Notes |
|---|------------|--------|-------|
| 1 | Replace zip code with city at high level; collect full address/zip on click-in | **NOT DONE** | Lead model stores only `zip_code` (String, nullable). City is NOT collected or displayed anywhere on leads. Full address (city, state, address, zip) only exists on the Property model after lead-to-customer conversion. High-level lead list doesn't show zip or city. |
| 2 | Tag: Need to be contacted | **PARTIAL** | Status `new` serves this purpose in the workflow (new → contacted → qualified → converted). No explicit "Need to be contacted" tag/badge — it's implied by the `new` status. `contacted_at` timestamp tracks when contact was made. |
| 3 | Tag: Need estimate | **NOT DONE** | No estimate-related tag or field on leads. Estimation tracking only exists at the Job level (`category: requires_estimate`), not within the Leads section. |
| 4 | Tag: Estimate status (Pending approval or approved) | **NOT DONE** | No estimate status tracking in the Leads section. Approval workflow doesn't exist on leads. |
| 5 | Ability to reach out to all pending leads to try to close (bulk outreach) | **NOT DONE** | No bulk communication or mass outreach functionality from the Leads section. Individual lead contact only. |
| 6 | Attachments under each lead: estimates provided and contracts to sign | **NOT DONE** | No attachment, document, estimate file, or contract storage associated with leads. No file upload on leads. |
| 7 | Customer can review estimate and sign contract from leads | **NOT DONE** | No customer-facing estimate review or contract signing portal linked to leads. Agreements section handles contracts but is disconnected from leads. |
| 8 | Estimate templates and contract templates within leads section | **NOT DONE** | No template system exists in the Leads section. AI can draft estimates via `/api/v1/ai/estimate` but there are no structured, reusable templates accessible from leads. |
| 9 | Staff gives estimate needing approval → customer added to leads until approved | **NOT DONE** | Lead conversion is one-way only (lead → customer). No reverse flow exists where a job/estimate pushes a customer back into the Leads section pending approval. |

---

### WORK REQUESTS

| # | Requirement | Status | Notes |
|---|------------|--------|-------|
| 1 | Remove Work Requests section (consolidate into Leads — only two lead types: needs estimate, or approved/becomes job) | **NOT DONE** | Work Requests section still exists as a separate page (`/work-requests`) with its own components (`WorkRequestsList`, `WorkRequestDetail`). Pulls from Google Sheets via `GoogleSheetSubmission` model and poller. Not consolidated with Leads. |

---

### JOBS

| # | Requirement | Status | Notes |
|---|------------|--------|-------|
| 1 | Notes under each job + field that summarizes the note (e.g., what the repair is) | **NOT DONE** | `JobStatusHistory` has a `notes` field per status change only. No persistent general notes field on the Job model itself. No summary/description field visible in the job list or detail view. |
| 2 | Status tags limited to ONLY: To be scheduled, In Progress, Complete | **NOT DONE** | 7 statuses exist: `requested`, `approved`, `scheduled`, `in_progress`, `completed`, `cancelled`, `closed`. Defined in `enums.py` and `types/index.ts`. Far more than the 3 requested. |
| 3 | Create filters to filter by what I want to see | **DONE** | Filters implemented: status dropdown, category filter (Ready to Schedule / Requires Estimate), subscription source filter, target date range (From/To calendar), and search input (by job type/description). Located in `JobList.tsx`. |
| 4 | Remove Category column | **NOT DONE** | Category column still present in `JobList.tsx` (lines 123-143), showing "Ready" or "Needs Estimate" badges with color coding. |
| 5 | Add Customer name column | **NOT DONE** | Job list has no customer name column. `customer_id` FK exists on the model but customer name is only visible in the `JobDetail` modal view (lines 170-187), not in the list table. |
| 6 | Add Customer tag column | **NOT DONE** | No customer tag column in the job list. Customer tags (priority, red flag, slow payer, etc.) are not surfaced in the jobs view. |
| 7 | Replace "Created on" with "days since added to job list" | **NOT DONE** | "Created" column still displays `created_at` as a formatted date via `toLocaleDateString()` (line 224 in `JobList.tsx`). No day-count calculation. |
| 8 | Add column for "needs to be completed by" date | **PARTIAL** | "Target Dates" column exists showing `target_start_date` and `target_end_date`. These are optional fields populated from agreement-generated jobs. Not explicitly labeled as "due by" or "needs to be completed by", but serves a similar purpose. |

---

### SCHEDULE — Creating Schedule

| # | Requirement | Status | Notes |
|---|------------|--------|-------|
| 1 | Undo/reverse actions when building schedule (e.g., accidental clear) | **DONE** | "Recently Cleared" section in `RecentlyClearedSection.tsx` displays schedules cleared in last 24 hours. "Restore" button with `RestoreScheduleDialog` allows reverting. Full audit trail with appointment details and timestamps. |
| 2 | Drag and drop scheduled appointments | **NOT DONE** | FullCalendar configured with `editable={false}` (line 209 in `CalendarView.tsx`). No drag-and-drop. Appointments only modifiable via form dialogs. |
| 3 | Lead time section for clients that ask (rough estimate of how far booked out) | **NOT DONE** | No lead time tracking or display anywhere in the schedule section. |
| 4 | Manually add job: pop up list of all jobs, filter by location and job type, pick multiple at once | **PARTIAL** | `JobSelectionControls` component in schedule generation enables "Select All" / multi-select with filters (All, Ready, Needs Estimate). **Missing:** In the simple `AppointmentForm` for manual creation, jobs are presented in a single dropdown without location or type filters and no multi-select. |
| 5 | Don't navigate away from schedule when clicking customer info (show inline) | **NOT DONE** | In `AppointmentDetail.tsx`, clicking customer/job links navigates to `/jobs/{job_id}` or `/staff/{staff_id}`, leaving the schedule page entirely. No inline modal or panel. |
| 6 | Calendar slot display: "Staff name - Job Type" | **PARTIAL** | Calendar displays `"${staffName} - ${statusLabel}"` (e.g., "John Smith - Confirmed") in `CalendarView.tsx` line 124-126. Shows status instead of job type. Job type only visible in appointment detail modal. |
| 7 | Property address auto-populate from customer information | **NOT DONE** | Address field not present in appointment creation form. Address visible in appointment detail view but not auto-populated during creation. |

---

### SCHEDULE — Staff Features

| # | Requirement | Status | Notes |
|---|------------|--------|-------|
| 8 | Collect payment on site, update data in appointment slot (auto-update customer data + invoicing) | **NOT DONE** | No payment collection button or flow in the schedule/appointment view. Invoice system exists separately at `/features/invoices/` but is not integrated into appointment workflow. |
| 9 | Invoice template: create and send invoice with payment links on the spot (auto-update CRM + invoicing) | **NOT DONE** | Invoice system exists but is not accessible from the appointment view. Staff cannot draw up or send invoices from within an appointment. |
| 10 | Estimate on the spot via template, auto-update lead section if not approved in 4 hours, push notification to customer | **NOT DONE** | No estimate creation from appointment view. No 4-hour auto-routing timer. No push notification for estimates. |
| 11 | Staff add customer notes and photos (auto-update customer data) | **PARTIAL** | Notes field exists on `AppointmentForm` (line 253-265) and can be added/viewed in appointment detail. **Missing:** No photo upload functionality anywhere in the schedule section. |
| 12 | Remove all customer tags from schedule view | **DONE** | No customer tags displayed in calendar view or appointment list. |
| 13 | Push notification via text to collect Google review | **NOT DONE** | No Google review solicitation functionality. No integration with Google reviews or SMS trigger for review requests. |
| 14 | Staff buttons: "On my way", "Job started", "Job Complete" | **PARTIAL** | Similar buttons exist: "Mark Arrived" (→ in_progress) and "Complete" (→ completed). **Missing:** No "On my way" button. Labels differ from the specified names. Status flow: pending → confirmed → in_progress → completed. |
| 15 | Staff can't complete job until payment collected or invoice sent | **NOT DONE** | No validation preventing completion without payment. "Complete" button is always available regardless of payment status in `AppointmentDetail.tsx`. |
| 16 | System tracks time between the three buttons per job type and staff (collect metadata) | **PARTIAL** | `arrived_at` and `completed_at` timestamp fields exist in the appointment model. `total_scheduled_minutes` calculated in `StaffDailyScheduleResponse`. **Missing:** No duration display in UI. No per-job-type or per-staff analytics. No "on my way" timestamp. |
| 17 | Remove "Mark as scheduled" from actions, replace with the buttons above | **DONE** | "Mark as scheduled" is not present as an action button. Current actions: Confirm, Mark Arrived, Complete, Cancel, No Show. |

---

### GENERATE ROUTES

| # | Requirement | Status | Notes |
|---|------------|--------|-------|
| 1 | Integrate route generation into schedule section; don't give staff ability to generate routes | **DONE** | Route generation lives at `/schedule/generate` within the schedule section. Includes `ScheduleGenerationPage`, route optimization visualization with `ScheduleMap` and `RoutePolyline` components. Route order tracked via `route_order` field on appointments. Role-based access controls should restrict staff. |

---

### INVOICES

| # | Requirement | Status | Notes |
|---|------------|--------|-------|
| 1 | Filter invoices based on whatever I want | **DONE** | Filters for: status (9 statuses), customer ID, date range (date_from/date_to), lien eligibility, search. Pagination with configurable page size. Sort by any field. Located in `InvoiceList.tsx`. |
| 2 | Track per invoice: Invoice number, Customer name, Job, Cost, Status (Complete/Pending/Past due), Days until due, Days past due | **DONE** | All fields exist: `invoice_number` (INV-YEAR-SEQ format), customer name via FK, job reference via `job_id`, `total_amount`, full status lifecycle (9 statuses including paid/sent/overdue), `due_date` for days-until/past-due calculations. |
| 3 | Color coding: Complete=green, Past due=red, Pending=yellow | **DONE** | `INVOICE_STATUS_CONFIG` in `types/index.ts` with `InvoiceStatusBadge.tsx`: Paid=emerald/green, Overdue=red, Lien_warning=amber, Lien_filed=red, Sent/Viewed=blue, Draft/Cancelled=slate. Close match — "pending" (sent) is blue not yellow, lien_warning is amber/yellow. |
| 4 | Mass notify: past due customers, invoices about to be due, lien notices | **PARTIAL** | Individual invoice actions work: `POST /invoices/{id}/reminder` (send reminder), `POST /invoices/{id}/lien-warning` (45-day warning), `POST /invoices/{id}/lien-filed` (120-day filing). `OverdueInvoicesWidget` shows top 5 with "Send Reminder" button. **Missing:** No **bulk/mass** notification endpoint to notify multiple customers at once. |
| 5 | All invoicing data updated to customer data within CRM | **DONE** | Invoices linked to customers via `customer_id` FK. Customer model has `invoices` relationship. Invoice data accessible through customer relationships and service history endpoint. |

---

## System Requirements (4).md — Section-by-Section Status

### LEAD INTAKE

| # | Requirement | Status | Notes |
|---|------------|--------|-------|
| 1 | Website traffic and landing pages (buttons + AI text bot) | **DONE** | Public `POST /api/v1/leads` endpoint (no auth required). Honeypot bot protection (hidden `website` field). CORS configured for Vercel landing page (`grins-irrigation.vercel.app`). Landing page in separate Vercel repo. |
| 2 | AI text bot agents on website for customer communication | **PARTIAL** | AI chat components exist (`AIQueryChat.tsx`, `AIStreamingText`). OpenAI GPT-4o-mini integration with streaming. **Missing:** No public-facing chatbot widget embedded on the website. AI assistant is internal/dashboard only. |
| 3 | Calls and texts from Google (AI agent answering calls/texts) | **PARTIAL** | Twilio SMS inbound webhook works (`POST /api/v1/sms/webhook`) with signature validation and opt-out parsing. **Missing:** No voice call AI (no Vapi integration). No IVR system. SMS only, not calls. |
| 4 | Marketing strategies (mass emails, texts, flyers, QR codes) | **PARTIAL** | Bulk SMS endpoint exists (`POST /api/v1/sms/bulk`). Email service with templates. **Missing:** No campaign management system, no scheduling, no QR code generation, no flyer creation. |
| 5 | Seasonal service tier package signup via website | **DONE** | 3-tier system for residential/commercial in `service_agreement_tiers` table. Pre-checkout consent flow (`POST /onboarding/consent`). Stripe checkout session creation (`POST /checkout/create-session`). Webhook processing (`POST /webhooks/stripe`) handles `checkout.session.completed`. Surcharge calculator for zones/pumps/backflow. |
| 6 | Work request form (simple, low friction) | **DONE** | Lead submission form collects: name, phone, email (optional), zip, situation, notes (optional). Honeypot instead of CAPTCHA. Fast 201 response with thank-you message. 24-hour duplicate detection. |
| 7 | Two routing paths: SCHEDULE (confirmed price) and FOLLOW UP (needs human review) | **DONE** | `intake_tag` enum with `schedule` and `follow_up` values. Routing logic in `lead_service.py`. Filtering by intake tag in API and frontend. |
| 8 | Admin follow-up section for unresolved requests | **DONE** | Dedicated `GET /leads/follow-up-queue` endpoint. `FollowUpQueue.tsx` component with urgency color-coding (<1h, 2-12h, 12h+). Quick actions: "Move to Schedule", "Mark Lost", "Details" link. Notes display for context. |
| 9 | Collect required customer info: first name, last name, city, address, phone, email, payment info, service selected, terms agreement, SMS opt-in, email marketing opt-in, availability times | **MOSTLY DONE** | Collected: name (split on conversion), phone (required), email (optional), zip_code, situation/service, terms_accepted, sms_consent, email_marketing_consent, payment (via Stripe checkout). **Missing:** City (only zip collected), full address (only on Property after conversion), customer availability/preferred times (not on lead form). |
| 10 | Text/email confirmation after work request submission | **PARTIAL** | Email confirmation implemented: `lead_confirmation.html` template sends "We Received Your Request" email. **Missing:** SMS confirmation is **deferred** — `SentMessage` model requires `customer_id` not `lead_id`, so SMS is logged but not sent. |
| 11 | All communication handled by AI agents; option to speak to real person | **PARTIAL** | AI tools exist for drafting messages (`/ai/communication/draft`), estimates (`/ai/estimate`), categorization (`/ai/categorize`). **Missing:** AI is admin-triggered, not autonomous. No customer-facing AI chat. No "speak to a person" escalation flow. |
| 12 | Central database as single source of truth, auto-update all dashboards | **DONE** | PostgreSQL central database. All models linked via FKs. Lead → Customer → Job → Invoice → Agreement relationships. Service history aggregation. Dashboard metrics pull from central data. |
| 13 | Database stores: client info, service/job history, payment history, special notes/photos/videos, opt-in/out, customer tags | **PARTIAL** | Stored: client info, job history, payment history (invoices), opt-in/out (SMS/email), customer tags (priority, red_flag, slow_payer, new_customer). **Missing:** Customer photos/videos not stored. `internal_notes` field exists but not exposed in UI. |

---

### SCHEDULING

| # | Requirement | Status | Notes |
|---|------------|--------|-------|
| 1 | Scheduling dashboard for all approved jobs and requests | **DONE** | FullCalendar with daily/weekly views. Staff filtering. Schedule generation page with AI-powered optimization. Route visualization with Google Maps. |
| 2 | Understand how far booked out (lead time for customers) | **NOT DONE** | No lead time calculation or display. No "we're booked out X weeks" indicator. |
| 3 | Appointment slots with customer info: name, contact, job type, location, materials/equipment, amount, time given, client history, directions | **PARTIAL** | Shows: customer name, contact info, job type, location, amount, notes. **Missing:** Materials/equipment needed, time allocated for completion, full client history, client-specific directions. |
| 4 | Staff sees only their specific schedule | **DONE** | Staff daily schedule endpoint with role-based filtering. Staff view shows only their assignments. |
| 5 | Clear route understanding with all key data | **DONE** | Route polyline visualization on Google Maps. Route order tracked. Staff can see their daily route. |
| 6 | Admin sees: staff GPS location, current job in progress, time left, same notes | **NOT DONE** | No GPS/location tracking for staff. No real-time "current job" or "time left" display for admin. |
| 7 | Auto-notify client day-of about estimated arrival time | **NOT DONE** | No automated day-of appointment notifications to customers. |
| 8 | Auto-notify client when staff is on the way with ETA | **NOT DONE** | No "on my way" auto-notification. No travel time ETA calculation. |
| 9 | Auto-notify client of delays, get client approval for delays | **NOT DONE** | No delay detection system. No delay notifications. No client approval flow for delays. |
| 10 | Notification of arrival | **NOT DONE** | No arrival notification to customer. |
| 11 | Staff workflow process: knock/call → review job → adjust prices → upsell → start/complete → present completed job → provide estimate if needed → collect payment/invoice → request Google review → update notes → mark complete | **PARTIAL** | Basic status flow exists: confirmed → in_progress → completed. **Missing:** No structured multi-step workflow enforcing each step. No upsell prompts. No "present completed job" step. No integrated payment/invoice/estimate creation. No Google review request. |
| 12 | Staff can quickly provide estimates on the spot using templates and price lists | **NOT DONE** | No estimate creation from appointment view. AI estimate generation exists but not integrated into staff appointment workflow. No price list reference accessible from schedule. |
| 13 | Staff can quickly draw up and send invoices with payment links | **NOT DONE** | Invoice system exists separately but not accessible from appointment view. Staff cannot create invoices from within an appointment slot. |
| 14 | Auto-notify client of job completion with receipt/invoice and job details | **NOT DONE** | No automated notification on appointment completion. No auto-send of receipt or job summary. |
| 15 | Staff can stop by gas station / take breaks (customer gets 30-45 min window) | **NOT DONE** | No break/pause functionality. No time window display for customers. |
| 16 | Payment on-site: credit card scanner, cash/check, or route to portal | **NOT DONE** | Payment methods tracked in invoice model (`cash`, `check`, `venmo`, `zelle`, `stripe`) but no on-site collection flow from appointment view. No card reader integration. |
| 17 | Staff notified if spending too much time on appointment | **NOT DONE** | No time-per-appointment warnings or notifications. Timestamps tracked but no alerting. |
| 18 | Additional estimate → sent to client for approval, staff can continue if approved | **NOT DONE** | No in-appointment estimate workflow. No client approval flow during an active job. |

---

### SALES

| # | Requirement | Status | Notes |
|---|------------|--------|-------|
| 1 | Sales dashboard: estimates needing write-up, pending approval, needing follow-up, revenue to be gained | **NOT DONE** | No dedicated sales dashboard exists. Leads section handles pipeline but not estimate-specific sales workflow. |
| 2 | Sales staff access to dashboard with scheduling ability | **NOT DONE** | No sales-specific role or interface. Manager/tech roles exist but no sales workflow. |
| 3 | Estimate templates for building estimates on the spot | **NOT DONE** | AI can generate estimates (`/ai/estimate`) but no structured reusable templates with line items, options, and pricing. |
| 4 | Estimate price adjustment options (material-based, good/better/best) | **NOT DONE** | No multi-option estimate builder. No tiered pricing within estimates. |
| 5 | Past photos/videos/testimonials to show clients during estimates | **NOT DONE** | No media library. No portfolio or testimonial storage. |
| 6 | Basic property diagram/vision builder (birds eye view of system design) | **NOT DONE** | No diagram or drawing tool. No AI photo modification for visualizing changes. |
| 7 | Estimate promotions if applicable | **NOT DONE** | No promotion/discount system for estimates. |
| 8 | Customer receives all materials at end of meeting + link to approve and sign contract | **NOT DONE** | No customer-facing estimate review portal. No contract signing link from estimates. |
| 9 | Sales staff can click into individual estimates: view estimate, price, diagrams/photos, contract, customer info, last contact, notes | **NOT DONE** | No estimate detail view with all these fields. |
| 10 | Promotional options for follow-up to convince customer | **NOT DONE** | No promotional tools for sales follow-up. |
| 11 | Automated notification option: auto-send push notifications every X days until customer approves or disapproves | **NOT DONE** | No automated recurring estimate follow-up notifications. |

---

### ACCOUNTING

| # | Requirement | Status | Notes |
|---|------------|--------|-------|
| 1 | General dashboard: YTD profit, YTD revenue (with options to go further) | **NOT DONE** | No accounting dashboard. No profit or revenue aggregation. |
| 2 | Pending invoices within allotted payment period (with total amount) | **PARTIAL** | `OverdueInvoicesWidget` shows overdue invoices with amounts. **Missing:** No view of invoices that are pending but not yet overdue, with total amount pending. |
| 3 | Past due invoices (with total amount) | **PARTIAL** | Overdue invoices tracked and displayed in widget. Lien deadline widget shows approaching deadlines. **Missing:** No comprehensive accounting view with totals. |
| 4 | Spending metrics per category | **NOT DONE** | No expense or spending tracking by category. |
| 5 | Average profit margin | **NOT DONE** | No cost tracking on jobs means no margin calculation possible. |
| 6 | Invoicing section: auto-notify 3 days before due, weekly after past due | **NOT DONE** | Manual reminder sending only via `POST /invoices/{id}/reminder`. No automated scheduling of reminders based on due dates. No background job for auto-notifications. |
| 7 | Past due 30 days: system sends formal lien notification | **PARTIAL** | Lien deadline tracking implemented (45-day and 120-day). Manual endpoints: `POST /invoices/{id}/lien-warning` and `POST /invoices/{id}/lien-filed`. Eligibility filtering by job type. **Missing:** Not automated — admin must manually trigger. No auto-send at 30 days. |
| 8 | Lien notification rules: only for property-improving services, not for startup/winterization/diagnostics/summer tune-up | **DONE** | `lien_eligible` boolean field on invoices. Lien eligibility determined by job type: installation, major_repair, new_system, system_upgrade qualify. Service-only jobs excluded. |
| 9 | Credit on file to charge client if needed | **NOT DONE** | No credit balance or stored payment method system. Payment model tracks method used per invoice but no on-file charging capability. |
| 10 | Material cost per job | **NOT DONE** | Job model only has `quoted_amount` and `final_amount`. No material cost breakdown field. |
| 11 | Staff cost per job | **NOT DONE** | No staff cost or labor cost field on jobs. |
| 12 | Total money received per job | **PARTIAL** | `final_amount` on job and `paid_amount` on invoice track revenue. **Missing:** No unified per-job financial view combining costs and revenue. |
| 13 | Customer acquisition cost (through marketing) | **NOT DONE** | `lead_source` tracked but no marketing spend data to calculate CAC. |
| 14 | Fuel and maintenance costs (cost per hour or mile) | **NOT DONE** | No fuel, mileage, or equipment maintenance tracking. |
| 15 | Connect credit cards/banking for spend tracking | **NOT DONE** | No financial account integration (Plaid, etc.). |
| 16 | Tax section: material spending, insurance, equipment usage, equipment service, office materials, CRM/marketing/subcontracting costs, other write-offs, revenue per job | **NOT DONE** | No tax section. No expense categorization system. |
| 17 | Receipt photo storage with amount extraction and category assignment | **NOT DONE** | No receipt storage. No OCR/amount extraction. No expense categories. |
| 18 | Estimated total tax amount due, updated throughout season | **NOT DONE** | No tax calculation or estimation features. |
| 19 | "What-if" spending projections to see tax impact | **NOT DONE** | No projection or simulation tools. |

---

### MARKETING/ADVERTISING DASHBOARD

| # | Requirement | Status | Notes |
|---|------------|--------|-------|
| 1 | Dashboard: where leads are coming from | **PARTIAL** | `lead_source` field on leads/customers with values: website, google, referral, ad, word_of_mouth. Metrics endpoint `GET /leads/metrics/by-source` provides analytics. **Missing:** No dedicated marketing dashboard UI to visualize this. |
| 2 | Average customer acquisition cost | **NOT DONE** | No CAC calculation. Would need marketing spend data + lead conversion data. |
| 3 | What places we are advertising in | **NOT DONE** | No advertising channel tracking or management. |
| 4 | Marketing/advertising budget tracking | **NOT DONE** | No budget tracking system. |
| 5 | Other key metrics for insights | **NOT DONE** | No marketing ROI, conversion funnel, or campaign performance metrics. |
| 6 | Mass email/text campaigns for promotions and deals | **PARTIAL** | Bulk SMS endpoint exists (`POST /api/v1/sms/bulk`). Email service with Jinja2 templates and CAN-SPAM compliance. **Missing:** No campaign management UI. No campaign scheduling. No template builder for promotions. No automation rules. |
| 7 | Automated email/text campaigns sent on set parameters to customer list | **NOT DONE** | No campaign automation. No drip campaigns. No parameter-based targeting. No recurring send scheduling. |

---

## Summary Scorecard

| Section | Done | Partial | Not Done | Total |
|---------|------|---------|----------|-------|
| **CRM: Overall** | 0 | 0 | 3 | 3 |
| **CRM: Dashboard** | 0 | 3 | 3 | 6 |
| **CRM: Customers** | 0 | 4 | 1 | 5 |
| **CRM: Leads** | 0 | 1 | 8 | 9 |
| **CRM: Work Requests** | 0 | 0 | 1 | 1 |
| **CRM: Jobs** | 1 | 1 | 6 | 8 |
| **CRM: Schedule (Creating)** | 1 | 2 | 4 | 7 |
| **CRM: Schedule (Staff)** | 2 | 2 | 6 | 10 |
| **CRM: Generate Routes** | 1 | 0 | 0 | 1 |
| **CRM: Invoices** | 3 | 1 | 1 | 5 |
| **Sys Req: Lead Intake** | 5 | 4 | 4 | 13 |
| **Sys Req: Scheduling** | 3 | 2 | 13 | 18 |
| **Sys Req: Sales** | 0 | 0 | 11 | 11 |
| **Sys Req: Accounting** | 1 | 3 | 15 | 19 |
| **Sys Req: Marketing** | 0 | 2 | 5 | 7 |
| **TOTALS** | **17** | **25** | **81** | **123** |

**Completion:** ~14% fully done, ~20% partially done, ~66% not done.

**Strongest areas:** Lead Intake infrastructure, Invoicing basics, Route Generation, Schedule undo/restore.

**Biggest gaps:** Entire Sales dashboard, Accounting/Tax section, Marketing dashboard, most Staff-facing schedule features (on-site payments, estimates, notifications, Google reviews), and the Leads section estimate/contract workflow.

---

## Data Model / Database Schema Gaps

The following section documents every structural gap in the database that must be resolved before the requirements above can be fully implemented. These are not code/UI tasks — they are foundational schema changes without which feature code will have nothing to read from or write to.

---

### MISSING TABLES — New Tables Required

#### 1. `documents` / `attachments` table — DOES NOT EXIST

No file storage infrastructure exists anywhere in the data model. No `file_url`, `photo_url`, or `document_url` columns exist on any table. Zero file upload endpoints, zero object storage integration.

**Suggested structure:**
- `id` (UUID, PK)
- `entity_type` (String) — e.g., 'customer', 'job', 'appointment', 'lead', 'invoice', 'estimate', 'expense'
- `entity_id` (UUID) — FK to the parent record
- `file_type` (String) — e.g., 'photo', 'pdf', 'receipt', 'contract', 'diagram'
- `file_url` (String) — URL in object storage (S3/Spaces)
- `file_name` (String) — original filename
- `file_size` (Integer) — bytes
- `mime_type` (String)
- `uploaded_by` (UUID FK→staff.id)
- `description` (Text, nullable)
- `created_at` (DateTime)

**Requirements this blocks:**
- Customer photos (CRM: Customers #3)
- Lead attachments — estimates & contracts (CRM: Leads #6)
- Staff field photos from appointments (CRM: Schedule Staff #11)
- Invoice PDFs (Sys Req: Scheduling #13, #14)
- Estimate documents (Sys Req: Sales #3, #8)
- Contract documents for customer signing (Sys Req: Sales #8)
- Receipt photos for tax (Sys Req: Accounting #17)
- Portfolio photos/videos for sales presentations (Sys Req: Sales #5)
- Property diagrams (Sys Req: Sales #6)

**External service required:** AWS S3 or DigitalOcean Spaces for object storage.

---

#### 2. `estimates` table — DOES NOT EXIST

No persistent estimate entity exists. AI can generate estimate text via `/api/v1/ai/estimate` but there is no table to store, track, or manage estimates through a lifecycle.

**Suggested structure:**
- `id` (UUID, PK)
- `estimate_number` (String, UNIQUE) — e.g., EST-2026-0001
- `customer_id` (UUID FK→customers.id)
- `lead_id` (UUID FK→leads.id, nullable) — for pre-conversion estimates
- `job_id` (UUID FK→jobs.id, nullable) — for job-linked estimates
- `template_id` (UUID FK→estimate_templates.id, nullable)
- `created_by` (UUID FK→staff.id)
- `status` (String) — draft, sent, viewed, approved, rejected, expired
- `line_items` (JSONB) — itemized breakdown
- `subtotal` (Numeric(10,2))
- `discount_amount` (Numeric(10,2), default 0)
- `total_amount` (Numeric(10,2))
- `valid_until` (Date)
- `sent_at` (DateTime, nullable)
- `viewed_at` (DateTime, nullable)
- `approved_at` (DateTime, nullable)
- `rejected_at` (DateTime, nullable)
- `approval_token` (UUID) — for customer-facing approval link
- `customer_signature` (Text, nullable) — e-signature data
- `notes` (Text, nullable)
- `document_url` (String, nullable) — PDF in object storage
- `follow_up_enabled` (Boolean, default False)
- `follow_up_interval_days` (Integer, nullable)
- `last_follow_up_sent` (DateTime, nullable)
- `created_at` (DateTime)
- `updated_at` (DateTime)

**Requirements this blocks:**
- Lead estimate status tracking (CRM: Leads #3, #4)
- Lead attachments for estimates (CRM: Leads #6)
- Customer review & sign estimate (CRM: Leads #7)
- Staff on-the-spot estimates in schedule (CRM: Schedule Staff #10)
- Auto-update lead section if not approved in 4 hours (CRM: Schedule Staff #10)
- Sales dashboard: estimates pending write-up, pending approval, needing follow-up (Sys Req: Sales #1)
- Estimate price adjustment options / good-better-best (Sys Req: Sales #4)
- Revenue-to-be-gained from pending estimates (Sys Req: Sales #1)
- Sales staff click-into individual estimate detail (Sys Req: Sales #9)
- Automated recurring follow-up for pending estimates (Sys Req: Sales #11)
- Additional estimate during active job (Sys Req: Scheduling #18)

---

#### 3. `estimate_templates` table — DOES NOT EXIST

**Suggested structure:**
- `id` (UUID, PK)
- `name` (String)
- `description` (Text, nullable)
- `service_category` (String) — maps to ServiceCategory enum
- `default_line_items` (JSONB) — pre-populated line items
- `is_active` (Boolean, default True)
- `created_by` (UUID FK→staff.id)
- `created_at` (DateTime)
- `updated_at` (DateTime)

**Requirements this blocks:**
- Estimate templates in leads section (CRM: Leads #8)
- Estimate templates for on-the-spot building (Sys Req: Sales #3)
- Staff templates and price lists in schedule (Sys Req: Scheduling #12)

---

#### 4. `contract_templates` table — DOES NOT EXIST

**Suggested structure:**
- `id` (UUID, PK)
- `name` (String)
- `description` (Text, nullable)
- `content_template` (Text) — Jinja2 or similar template text
- `requires_signature` (Boolean, default True)
- `is_active` (Boolean, default True)
- `created_at` (DateTime)
- `updated_at` (DateTime)

**Requirements this blocks:**
- Contract templates in leads section (CRM: Leads #8)
- Contract signing link for customer (Sys Req: Sales #8)

---

#### 5. `contracts` table — DOES NOT EXIST

Currently `service_agreements` handles subscription contracts but there is no general-purpose contract entity for one-off jobs, estimates, or installs.

**Suggested structure:**
- `id` (UUID, PK)
- `contract_number` (String, UNIQUE)
- `customer_id` (UUID FK→customers.id)
- `estimate_id` (UUID FK→estimates.id, nullable)
- `job_id` (UUID FK→jobs.id, nullable)
- `template_id` (UUID FK→contract_templates.id, nullable)
- `status` (String) — draft, sent, viewed, signed, expired, cancelled
- `content` (Text) — rendered contract text
- `document_url` (String, nullable) — PDF in object storage
- `sent_at` (DateTime, nullable)
- `viewed_at` (DateTime, nullable)
- `signed_at` (DateTime, nullable)
- `signature_data` (Text, nullable) — e-signature
- `signer_ip_address` (String(45), nullable)
- `signer_user_agent` (String(500), nullable)
- `signing_token` (UUID) — for customer-facing signing link
- `valid_until` (Date, nullable)
- `created_at` (DateTime)
- `updated_at` (DateTime)

**Requirements this blocks:**
- Customer can review estimate and sign contract (CRM: Leads #7)
- Contract signing link after sales meeting (Sys Req: Sales #8)
- Terms: "any estimate approved = formal contract" (Sys Req: Scheduling key consideration #2)

---

#### 6. `expenses` table — DOES NOT EXIST

No cost or expense tracking exists. Job model only has `quoted_amount` and `final_amount` — revenue only, no costs.

**Suggested structure:**
- `id` (UUID, PK)
- `job_id` (UUID FK→jobs.id, nullable) — null for general business expenses
- `category` (String) — material, labor, fuel, equipment_maintenance, insurance, office, marketing, subcontractor, other
- `description` (String)
- `amount` (Numeric(10,2))
- `vendor` (String, nullable)
- `receipt_url` (String, nullable) — photo of receipt in object storage
- `expense_date` (Date)
- `tax_deductible` (Boolean, default True)
- `created_by` (UUID FK→staff.id)
- `created_at` (DateTime)
- `updated_at` (DateTime)

**Requirements this blocks:**
- Material cost per job (Sys Req: Accounting #10)
- Staff cost per job (Sys Req: Accounting #11)
- Fuel and maintenance costs (Sys Req: Accounting #14)
- Spending metrics per category (Sys Req: Accounting #4)
- Average profit margin calculation (Sys Req: Accounting #5)
- Tax section: material, insurance, equipment, office, marketing costs (Sys Req: Accounting #16)
- Receipt photo storage with amount extraction (Sys Req: Accounting #17)
- Estimated tax amount due (Sys Req: Accounting #18)
- "What-if" spending projections (Sys Req: Accounting #19)
- Connect banking/credit cards for spend tracking (Sys Req: Accounting #15)

---

#### 7. `marketing_campaigns` table — DOES NOT EXIST

**Suggested structure:**
- `id` (UUID, PK)
- `name` (String)
- `campaign_type` (String) — email, sms, email_and_sms
- `status` (String) — draft, scheduled, active, paused, completed, cancelled
- `target_criteria` (JSONB) — filter rules for audience (e.g., customer tags, zip codes, last service date)
- `message_subject` (String, nullable) — email subject
- `message_template` (Text) — message body template
- `promotion_details` (JSONB, nullable) — discount codes, offers
- `scheduled_for` (DateTime, nullable) — when to start sending
- `recurrence_interval_days` (Integer, nullable) — for recurring campaigns
- `recurrence_end_date` (Date, nullable)
- `total_recipients` (Integer, default 0)
- `sent_count` (Integer, default 0)
- `open_count` (Integer, default 0)
- `click_count` (Integer, default 0)
- `budget_amount` (Numeric(10,2), nullable)
- `actual_spend` (Numeric(10,2), nullable)
- `created_by` (UUID FK→staff.id)
- `created_at` (DateTime)
- `updated_at` (DateTime)

**Requirements this blocks:**
- Mass email/text campaigns for promotions (Sys Req: Marketing #6)
- Automated recurring campaigns on set parameters (Sys Req: Marketing #7)
- Advertising budget tracking (Sys Req: Marketing #4)
- Campaign performance metrics (Sys Req: Marketing #5)
- Customer acquisition cost calculation (Sys Req: Marketing #2)

---

#### 8. `staff_locations` table — DOES NOT EXIST

**Suggested structure:**
- `id` (UUID, PK)
- `staff_id` (UUID FK→staff.id)
- `latitude` (Numeric(10,8))
- `longitude` (Numeric(11,8))
- `accuracy_meters` (Float, nullable)
- `recorded_at` (DateTime)
- `created_at` (DateTime)

**Requirements this blocks:**
- Staff GPS location tracking for admin (Sys Req: Scheduling #6)
- Current job in progress display (Sys Req: Scheduling #6)
- "On my way" ETA based on real location (Sys Req: Scheduling #8)

---

#### 9. `notification_schedules` table — DOES NOT EXIST

Currently all notifications are manual one-off actions. No infrastructure for scheduled recurring auto-sends.

**Suggested structure:**
- `id` (UUID, PK)
- `entity_type` (String) — invoice, estimate, appointment, campaign
- `entity_id` (UUID)
- `notification_type` (String) — payment_reminder, estimate_follow_up, appointment_reminder, lien_warning, campaign_send
- `channel` (String) — sms, email, both
- `next_send_at` (DateTime)
- `interval_days` (Integer, nullable) — for recurring
- `max_sends` (Integer, nullable)
- `sends_completed` (Integer, default 0)
- `is_active` (Boolean, default True)
- `last_sent_at` (DateTime, nullable)
- `created_at` (DateTime)
- `updated_at` (DateTime)

**Requirements this blocks:**
- Auto-notify 3 days before invoice due (Sys Req: Accounting #6)
- Weekly notification after invoice past due (Sys Req: Accounting #6)
- Auto-send lien warning at 30 days past due (Sys Req: Accounting #7)
- Automated estimate follow-up every X days (Sys Req: Sales #11)
- Day-of appointment notification to customer (Sys Req: Scheduling #7)
- "On my way" notification to customer (Sys Req: Scheduling #8)
- Delay notification and client approval (Sys Req: Scheduling #9)
- Arrival notification (Sys Req: Scheduling #10)
- Completion notification with receipt (Sys Req: Scheduling #14)

---

#### 10. `google_review_requests` table — DOES NOT EXIST

**Suggested structure:**
- `id` (UUID, PK)
- `customer_id` (UUID FK→customers.id)
- `appointment_id` (UUID FK→appointments.id, nullable)
- `sent_via` (String) — sms, email
- `sent_at` (DateTime)
- `review_link` (String) — Google review URL
- `status` (String) — sent, clicked, reviewed
- `created_by` (UUID FK→staff.id)
- `created_at` (DateTime)

**Requirements this blocks:**
- Google review push notification via text (CRM: Schedule Staff #13)
- Request google review if good candidate (Sys Req: Scheduling #11 staff workflow)

---

### MISSING COLUMNS — On Existing Tables

#### Lead table (`leads`)

| Missing Column | Type | Nullable | Needed For |
|---------------|------|----------|-----------|
| `city` | String(100) | Yes | CRM: Leads #1 — display city at high level instead of zip code |
| `address` | String(255) | Yes | Sys Req: Lead Intake #9 — collect full address from clients |
| `state` | String(50), default 'MN' | Yes | Full address collection alongside city/address |
| `estimate_status` | String(50) | Yes | CRM: Leads #3, #4 — track if lead needs estimate, and estimate status (pending/approved). Values: needs_estimate, estimate_sent, pending_approval, approved, rejected |

---

#### Job table (`jobs`)

| Missing Column | Type | Nullable | Needed For |
|---------------|------|----------|-----------|
| `general_notes` | Text | Yes | CRM: Jobs #1 — persistent notes field that summarizes the job (e.g., "what the repair is"). Distinct from `description` which is the job type description. |
| `material_cost` | Numeric(10,2) | Yes | Sys Req: Accounting #10 — track material cost per job for profit margin |
| `labor_cost` | Numeric(10,2) | Yes | Sys Req: Accounting #11 — track staff labor cost per job |

**Note:** `description` (Text, nullable) exists but is used for the job's type description at creation. The requirement wants an evolving notes field staff can update with specifics like "replace 3 heads zone 4, check for leak at valve 2."

---

#### Appointment table (`appointments`)

| Missing Column | Type | Nullable | Needed For |
|---------------|------|----------|-----------|
| `en_route_at` | DateTime(timezone=True) | Yes | CRM: Schedule Staff #14 — timestamp for "On my way" button. Currently only `arrived_at` and `completed_at` exist, so 3-phase time tracking (en_route → arrived → completed) is impossible. |
| `payment_status` | String(50) | Yes | CRM: Schedule Staff #15 — enforce payment before completion. Values: pending, collected, invoiced, waived. Without this field, the "Complete" button cannot check if payment was handled. |
| `invoice_id` | UUID FK→invoices.id | Yes | Link an invoice created on-site to the specific appointment. Currently Invoice links to Job and Customer but not to Appointment, making it impossible to know which appointment generated which invoice. |

---

#### Customer table (`customers`)

| Missing Column | Type | Nullable | Needed For |
|---------------|------|----------|-----------|
| `photo_url` | String(500) | Yes | CRM: Customers #3 — customer profile photo. Requires file storage service. |
| `stripe_payment_method_id` | String(255) | Yes | Sys Req: Accounting #9 — "credit on file to charge a client if need be." Stores the Stripe PaymentMethod ID for on-file charging. |

---

#### Invoice table (`invoices`)

| Missing Column | Type | Nullable | Needed For |
|---------------|------|----------|-----------|
| `document_url` | String(500) | Yes | PDF storage URL for downloadable/emailable invoice documents. Currently invoices are data-only DB records with no PDF generation or document storage. |

---

### SCHEMA (API) GAPS — DB Fields Not Exposed Through API

#### 1. Customer `internal_notes` — exists in DB, invisible to API

- **DB model** (`customer.py` line 150): `internal_notes` (Text, nullable) — field exists
- **CustomerResponse** schema (`schemas/customer.py` lines 225-254): does NOT include `internal_notes`
- **CustomerUpdate** schema (`schemas/customer.py` lines 111-176): does NOT include `internal_notes`
- **CustomerCreate** schema (`schemas/customer.py` lines 50-108): does NOT include `internal_notes`
- **Impact:** The column exists in PostgreSQL but is completely inaccessible via the API. Frontend cannot read or write customer notes. Blocks CRM: Customers #2.

**Fix:** Add `internal_notes: str | None` to `CustomerResponse`, `CustomerUpdate`, and `CustomerCreate` schemas.

---

#### 2. Customer `preferred_service_times` — read-only, not editable

- **CustomerResponse** schema (line 249): DOES include `preferred_service_times` — can be read
- **CustomerUpdate** schema: does NOT include `preferred_service_times` — cannot be edited
- **CustomerCreate** schema: does NOT include `preferred_service_times` — cannot be set
- **Impact:** Frontend can display preferred times but staff cannot modify them. Blocks full implementation of CRM: Customers #5.

**Fix:** Add `preferred_service_times: dict[str, Any] | None` to `CustomerUpdate` and `CustomerCreate` schemas.

---

### ENUM MISMATCHES — Frontend vs Backend Conflicts

#### 1. AppointmentStatus — Frontend has values the backend will reject

| Value | Frontend Type | Backend Python Enum | DB CHECK Constraint |
|-------|-------------|-------------------|-------------------|
| `pending` | YES (in type union) | NO | NO |
| `scheduled` | YES | YES | YES |
| `confirmed` | YES | YES | YES |
| `en_route` | NO | NO | NO |
| `in_progress` | YES | YES | YES |
| `completed` | YES | YES | YES |
| `cancelled` | YES | YES | YES |
| `no_show` | YES (actively used) | NO | NO |

**Impact — `no_show`:** The frontend actively uses `no_show` in:
- `AppointmentDetail.tsx` line 75 — terminal status check
- `AppointmentList.tsx` lines 48, 63, 82 — filter option, color, label
- `CalendarView.tsx` line 40 — calendar color mapping
- `appointmentApi.ts` line 131 — `markNoShow()` function sends `{ status: 'no_show' }` to backend

When `markNoShow()` is called, the backend will accept the PUT request but PostgreSQL will reject the INSERT/UPDATE with a CHECK constraint violation because `no_show` is not in the allowed values. **This is a live bug.**

**Impact — `pending`:** Referenced in frontend type definition but less actively used. Still a mismatch.

**Impact — `en_route`:** Required for "On my way" button (CRM: Schedule Staff #14). The `.kiro/specs/crm-gap-closure/design.md` spec added `EN_ROUTE = "en_route"` to the design but it was never implemented.

**Fix:**
1. Add `PENDING = "pending"`, `EN_ROUTE = "en_route"`, `NO_SHOW = "no_show"` to `AppointmentStatus` enum in `enums.py`
2. Create migration to ALTER the CHECK constraint on `appointments.status` to include all 8 values
3. Add `en_route_at` column to appointments table (as noted above)

---

#### 2. SentMessage `message_type` CHECK — missing `lead_confirmation`

- **DB CHECK constraint** (`sent_message.py` lines 97-101) allows: `appointment_confirmation`, `appointment_reminder`, `on_the_way`, `arrival`, `completion`, `invoice`, `payment_reminder`, `custom`
- **Frontend AI types** (`ai/types/index.ts`) include `lead_confirmation` as a valid MessageType
- **Lead service** (`lead_service.py` line 143-184) attempts to create a `lead_confirmation` message type (currently deferred)

**Impact:** When lead SMS confirmation is activated, inserting a message with `message_type = 'lead_confirmation'` will fail the DB CHECK constraint.

**Fix:** Add `'lead_confirmation'` to the CHECK constraint via migration. Also consider adding other future types: `estimate_sent`, `contract_sent`, `review_request`, `campaign`.

---

#### 3. SentMessage `customer_id` NOT NULL — blocks sending to leads

- `sent_messages.customer_id` is `nullable=False` (`sent_message.py` line 31-35)
- There is no `lead_id` FK on the SentMessage model
- **Impact:** You physically cannot store an SMS record for a lead who hasn't been converted to a customer. This is the documented reason why SMS confirmation for leads is "deferred" in `lead_service.py`. Blocks all pre-conversion lead communication tracking.

**Fix:**
1. Make `customer_id` nullable (ALTER COLUMN SET NULL)
2. Add `lead_id` (UUID FK→leads.id, nullable) column
3. Add CHECK constraint: at least one of `customer_id` or `lead_id` must be non-null
4. Update SentMessage queries to handle both customer and lead associations

---

### RELATIONSHIP GAPS — Missing Foreign Keys / Links

#### 1. Invoice ↔ Appointment — no direct link

- Invoice has `job_id` and `customer_id` but no `appointment_id`
- Appointment has no `invoice_id`
- **Impact:** When staff creates an invoice during an appointment, there's no way to link them directly. This means:
  - Cannot enforce "can't complete appointment until invoice is sent" (CRM: Schedule Staff #15) — the appointment doesn't know about the invoice
  - Cannot show "invoice sent" status on the appointment detail view
  - Cannot auto-generate invoice from appointment context

**Fix:** Add `invoice_id` (UUID FK→invoices.id, nullable) to appointments table, OR add `appointment_id` (UUID FK→appointments.id, nullable) to invoices table. The latter is simpler since invoices already reference jobs.

---

#### 2. Estimate ↔ Lead — no link possible

- No estimates table exists (see Missing Tables #2 above)
- Lead model has no estimate-related fields
- **Impact:** The entire leads estimate workflow (CRM: Leads #3-8) has zero data foundation. Cannot:
  - Tag a lead as "needs estimate"
  - Attach an estimate to a lead
  - Track estimate approval status on a lead
  - Move lead to approved when estimate is signed

**Fix:** Create `estimates` table with `lead_id` FK (see table design above). Add `estimate_status` column to leads table for quick filtering.

---

#### 3. Customer ↔ Photos — no file relationship

- Customer model has no `photo_url` field
- No documents/attachments table exists
- **Impact:** Cannot store or display customer photos. Blocks CRM: Customers #3.

**Fix:** Add `photo_url` to customer model AND/OR create polymorphic `documents` table (see Missing Tables #1).

---

### DATA MODEL READINESS SCORECARD

| Requirement Area | DB Ready? | Blocking Gaps |
|-----------------|-----------|---------------|
| **Dashboard** | ~70% | No messages table, invoice metrics query points to wrong data |
| **Customers** | ~60% | `internal_notes` not in API schema, no `photo_url`, `preferred_service_times` not editable, no `stripe_payment_method_id` |
| **Leads** | ~30% | No `city`/`address` fields, no estimate tracking, no attachments table, no estimate or contract tables |
| **Work Requests** | ~90% | Structurally fine, consolidation with Leads is a design decision not a schema gap |
| **Jobs** | ~70% | No `general_notes` field, no `material_cost`/`labor_cost` fields |
| **Schedule (Admin)** | ~60% | No lead time computation, no drag-drop (frontend only) |
| **Schedule (Staff)** | ~20% | No `en_route_at` timestamp, no `payment_status`, no `invoice_id` link on appointment, no photo storage, SentMessage can't target leads, `no_show` enum missing from backend |
| **Generate Routes** | ~100% | Structurally complete |
| **Invoices** | ~80% | No `document_url` for PDFs, no `notification_schedules` table, no mass-action tables |
| **Sales** | ~0% | No `estimates` table, no `estimate_templates`, no `contracts`, no `contract_templates`, no `documents` table |
| **Accounting** | ~10% | No `expenses` table, no cost fields on jobs, no tax infrastructure, no receipt storage |
| **Marketing** | ~10% | No `marketing_campaigns` table, no ad spend tracking |
| **Enum Alignment** | ~85% | `no_show`/`pending`/`en_route` missing from AppointmentStatus; `lead_confirmation` missing from SentMessage CHECK |

---

### IMPLEMENTATION PRIORITY ORDER

Based on how many requirements each gap blocks, here is the recommended order for schema changes:

**Priority 1 — Blocks the most features (do first):**
1. Create `documents`/`attachments` table + object storage service — unlocks ~15 requirements across customers, leads, schedule, sales, accounting
2. Create `estimates` table + `estimate_templates` table — unlocks entire Sales section + leads estimate workflow (~12 requirements)
3. Fix `SentMessage`: make `customer_id` nullable, add `lead_id`, update CHECK constraint for `lead_confirmation` — unlocks lead SMS communication
4. Fix `AppointmentStatus` enum: add `en_route`, `no_show`, `pending` to Python enum + DB CHECK — fixes live bug + unlocks "On my way" feature

**Priority 2 — Significant feature enablers:**
5. Create `expenses` table — unlocks Accounting section (~10 requirements)
6. Create `notification_schedules` table — unlocks all automated notifications (~9 requirements)
7. Add missing columns to existing tables:
   - Lead: `city`, `address`, `state`, `estimate_status`
   - Job: `general_notes`, `material_cost`, `labor_cost`
   - Appointment: `en_route_at`, `payment_status`, `invoice_id`
   - Customer: `photo_url`, `stripe_payment_method_id`
   - Invoice: `document_url`
8. Expose `internal_notes` and `preferred_service_times` in Customer API schemas

**Priority 3 — Specific feature areas (can defer):**
9. Create `contracts` + `contract_templates` tables — unlocks contract signing workflow
10. Create `marketing_campaigns` table — unlocks campaign management
11. Create `staff_locations` table — unlocks GPS tracking
12. Create `google_review_requests` table — unlocks review solicitation tracking
