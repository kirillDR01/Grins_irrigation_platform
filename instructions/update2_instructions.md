# Grins Irrigation CRM — System Operations Guide

*CRM Changes Update 2 — New Employee Training Manual*

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Logging In and Security](#2-logging-in-and-security)
3. [Dashboard — Your Daily Starting Point](#3-dashboard--your-daily-starting-point)
4. [The Customer Lifecycle — How Everything Connects](#4-the-customer-lifecycle--how-everything-connects)
5. [Leads Tab — New Inbound Requests](#5-leads-tab--new-inbound-requests)
6. [Sales Tab — Estimates and the Sales Pipeline](#6-sales-tab--estimates-and-the-sales-pipeline)
7. [Customers Tab — The Master Customer Record](#7-customers-tab--the-master-customer-record)
8. [Jobs Tab — Approved Work Ready to Schedule](#8-jobs-tab--approved-work-ready-to-schedule)
9. [Schedule Tab — Building and Managing the Daily Schedule](#9-schedule-tab--building-and-managing-the-daily-schedule)
10. [On-Site Job Operations — The Field Workflow](#10-on-site-job-operations--the-field-workflow)
11. [Invoices Tab — Billing and Collections](#11-invoices-tab--billing-and-collections)
12. [Service Packages and Onboarding — Subscription Customers](#12-service-packages-and-onboarding--subscription-customers)
13. [Contract Renewals — Annual Renewal Review](#13-contract-renewals--annual-renewal-review)
14. [Duplicate Customer Management](#14-duplicate-customer-management)
15. [SMS and Customer Communication](#15-sms-and-customer-communication)
16. [Quick Reference — Common Workflows](#16-quick-reference--common-workflows)

---

## 1. System Overview

The Grins Irrigation CRM is an all-in-one platform for managing the full lifecycle of irrigation customers — from the moment a lead comes in, through estimating, scheduling, performing the job, invoicing, and managing ongoing service contracts.

**The main tabs in the navigation are:**

| Tab | Purpose |
|-----|---------|
| **Dashboard** | Daily overview — alerts, metrics, today's schedule |
| **Leads** | New inbound requests that haven't been contacted yet |
| **Sales** | Leads that need estimates before they become jobs |
| **Customers** | Master record for every customer — one-stop shop for all their data |
| **Jobs** | Approved work that is ready to be scheduled |
| **Schedule** | The daily/weekly calendar for assigning jobs to dates and staff |
| **Invoices** | All billing — pending, paid, and past-due invoices |
| **Contract Renewals** | Review queue for auto-renewed service contracts |

**Key concept:** Records flow through the system in a specific order. Understanding this flow is the single most important thing for using the CRM effectively. The next section walks through it end to end.

---

## 2. Logging In and Security

- Navigate to the CRM URL and log in with your admin credentials.
- The system uses a secure password (minimum 16 characters, mixed case, digits, and symbols).
- Your session lasts **60 minutes** for the access token, with a **30-day** refresh token. You should not be randomly logged out during normal use. If you experience premature logouts, report it — this was a known bug that has been investigated and fixed.
- There is currently a **single admin** login. All logged-in users have full admin privileges. There is no staff vs. admin role distinction in this version — that is planned for a future update.

---

## 3. Dashboard — Your Daily Starting Point

When you log in, you land on the **Dashboard**. This is your morning briefing.

### What You See

- **Morning Briefing** — a summary of what needs attention today
- **Metrics Cards** — high-level numbers (active jobs, pending invoices, etc.)
- **Job Status Grid** — visual breakdown of jobs by status
- **Today's Schedule** — what's on the calendar for today
- **Invoice Widgets** — outstanding billing at a glance
- **Quick Actions** — shortcuts to common tasks
- **Recent Activity** — latest changes across the system
- **Alerts** — actionable notifications about things that need your attention

### Alerts and Navigation

Alerts are the most important part of the Dashboard. When you see an alert:

- **Single-record alerts** (e.g., "1 new job came in"): Click the alert and it takes you **directly to that record's detail page**.
- **Multi-record alerts** (e.g., "3 invoices past due"): Click the alert and it takes you to the **filtered list** showing only those records. The matching rows will briefly **highlight in amber/yellow** (a pulse that fades over about 3 seconds) so you can immediately see which records the alert is referring to.
- The highlight is encoded in the URL (`?highlight=<id>`), so if you refresh the page or share the link, the highlight will still work.

### What's NOT on the Dashboard

The Dashboard intentionally does **not** show:
- A dedicated "Estimates" section — estimates live in the **Sales** tab
- A "New Leads" section — leads live in the **Leads** tab

This keeps the Dashboard focused on alerts and metrics rather than duplicating what other tabs already show.

---

## 4. The Customer Lifecycle — How Everything Connects

This is the core flow of how a customer moves through the system. Every record eventually traces back to this lifecycle.

```
                    +-----------+
                    |  New Lead |  (Inbound request arrives — status: New)
                    +-----+-----+
                          |
                  Review the lead
                  (check Job Requested, City, Address)
                          |
                  Contact the lead
                  (call or text them)
                          |
                  Click "Mark Contacted"
                  (status: Contacted, Awaiting Response)
                          |
                  Wait for their response
                          |
              +-----------+-----------+-----------+
              |                       |           |
     Job is confirmed,         Needs an       Not
     ready to schedule?        estimate?    interested?
              |                       |           |
              v                       v           v
    +-------------------+    +-----------------+  Delete
    | Move to Jobs Tab  |    | Move to Sales   |  lead
    |                   |    +--------+--------+
    | NOTE: If lead's   |            |
    | situation maps to |   ======= SALES PIPELINE =======
    | "requires_estimate"            |
    | a warning modal   |   Status: "Schedule Estimate"
    | appears with 3    |   Click action button -> opens
    | options:          |   calendar event form pre-filled
    |  - Move to Jobs   |   with customer/property details.
    |    (proceed)      |   Saving the event auto-advances
    |  - Move to Sales  |   the entry to "Estimate Scheduled."
    |    (redirect)     |            |
    |  - Cancel         |   Status: "Estimate Scheduled"
    +--------+----------+   Go to the property, assess the job
             |                        |
             |               Status: "Send Estimate"
             |               Create estimate OUTSIDE the CRM
             |               (Word, PDF editor, estimating software)
             |               Upload finished PDF to the Documents
             |               section in the sales entry detail view
             |                        |
             |               Send for signature:
             |                 - Email (remote signing via SignWell)
             |                 - On-Site (embedded signing iframe)
             |               NOTE: Signing buttons are DISABLED
             |               until a document is uploaded.
             |               Uses the real uploaded document
             |               (S3 presigned URL), not a placeholder.
             |                        |
             |               Status: "Pending Approval"
             |               Waiting for customer to sign
             |                        |
             |               Customer signs?
             |                  Yes -> "Send Contract" -> "Closed-Won"
             |                         Click "Convert to Job"
             |                  No  -> "Closed-Lost"
             |                        |
             v                        v
    +-------------------------------------------+
    |            Jobs Tab                       |
    |   (Approved work, ready to schedule)      |
    |   Job status: TO BE SCHEDULED             |
    |   Week Of: target week assigned           |
    |   "Estimate Needed" badge on jobs that    |
    |   bypassed the estimate workflow           |
    |   "Prepaid" badge on service agreement    |
    |   jobs (no payment collection needed)     |
    |   "Schedule" button on each job row       |
    |   opens appointment form pre-filled       |
    +---------------------+---------------------+
                          |
             ========= SCHEDULING =========
             (Schedule tab — assign to a
              specific date, time, and staff)
                          |
                  Appointment created on calendar
                  (Job status: TO BE SCHEDULED -> SCHEDULED)
                  (Appointment status: DRAFT)
                  (Dotted border, grayed-out on calendar)
                  (NO SMS sent yet — draft is silent)
                          |
             ========= DRAFT MODE =========
             Admin can move/delete draft appointments
             freely — no SMS is ever sent for drafts.
             When ready, admin clicks "Send Confirmation"
             (per-appointment, per-day, or bulk "Send All").
                          |
             ========= SMS #1: CONFIRMATION REQUEST =========
                          |
                  Admin clicks "Send Confirmation"
                  (Appointment status: DRAFT -> SCHEDULED)
                  (Dashed border, muted color on calendar)
                          |
                  [SYSTEM -> CUSTOMER]
                  "Your appointment on [date] [time] has been
                  scheduled. Reply Y to confirm, R to reschedule,
                  or C to cancel."
                          |
                  Waiting for customer reply...
                          |
              +-----------+-----------+-----------+-----------+
              |           |           |           |
           Customer    Customer    Customer    No reply
           texts "Y"   texts "R"   texts "C"   within
              |           |           |        expected window
              |           |           |           |
              v           v           v           v
                                                Logged as
                                                "needs review"
                                                for manual
                                                follow-up
              |           |           |
              |           |           |
              v           v           v
   ......................................
   : SMS #1a:  : SMS #1b:  : SMS #1c:  :
   : CONFIRM   : RESCHED   : CANCEL    :
   : REPLY     : REPLY     : REPLY     :
   :...........: :...........: :...........:
              |           |           |
   [SYSTEM -> CUSTOMER]   |           |
   "Your appointment      |           |
    has been confirmed.    |           |
    See you on [date]      |           |
    at [time]!"            |           |
              |           |           |
   Appointment status     |    [SYSTEM -> CUSTOMER]
   -> CONFIRMED           |    "Your [service type] appointment
   (solid border,         |     on [date] at [time] has been
    full color on         |     cancelled. If you'd like to
    calendar)             |     reschedule, please call us
              |           |     at [business phone]."
              |           |           |
              |           |    Appointment status
              |           |    -> CANCELLED
              |           |    (If was SCHEDULED/CONFIRMED,
              |           |     cancellation SMS sent.
              |           |     If was DRAFT, no SMS.)
              |           |    On-site timestamps cleared.
              |           |    If last appointment for job,
              |           |    job reverts: SCHEDULED -> TO BE SCHEDULED.
              |           |    Admin is notified
              |           |
              |    [SYSTEM -> CUSTOMER]
              |    "We've received your reschedule
              |     request. We'll be in touch
              |     with a new time."
              |           |
              |    THEN a follow-up SMS:
              |    "We'd be happy to reschedule.
              |     Please reply with 2-3 dates
              |     and times that work for you
              |     and we'll get you set up."
              |           |
              |    Reschedule request created
              |    -> appears in admin Reschedule
              |       Requests queue
              |    -> customer's reply with
              |       alternative times captured
              |       in requested_alternatives
              |    -> admin reviews, picks new
              |       date/time, and reschedules
              |    -> when rescheduled, a NEW
              |       confirmation SMS (#1) is
              |       sent and the cycle repeats
              |
             ========= DAY OF JOB =========
              |
             ========= SMS #2: ON MY WAY =========
              |
          Admin clicks "On My Way" button
              |
          [SYSTEM -> CUSTOMER]
          "We're on our way! Your technician is
           heading to your location now."
              |
          (No customer reply expected)
          Logs on_my_way_at timestamp.
          Job status: SCHEDULED (unchanged)
          Appointment: CONFIRMED -> EN_ROUTE
          (also works from SCHEDULED if unconfirmed)
              |
          "Job Started" -> Logs started_at timestamp.
              |             No SMS sent.
              |             Job: SCHEDULED -> IN PROGRESS
              |             Appointment: EN_ROUTE -> IN PROGRESS
              |             (or CONFIRMED -> IN PROGRESS if
              |              On My Way was skipped)
              |
          During the visit:
              |  - Add notes and photos
              |  - Service agreement jobs show "Covered by
              |    [Agreement Name]" — no payment needed,
              |    payment buttons hidden
              |  - One-off jobs show payment options:
              |    * "Pay with Card (Tap to Pay)" — Stripe
              |      Terminal NFC payment via phone
              |    * "Record Other Payment" — Cash, Check,
              |      Venmo, Zelle (manual recording)
              |    * "Create Invoice" — send invoice later
              |  - Jobs with invoice sent show invoice details
              |    with status badge + "Collect Payment"
              |  - Jobs with payment collected show
              |    "Payment collected — $X via [method]"
              |
          "Job Complete" -> Job: IN PROGRESS -> COMPLETED
              |              Appointment: IN PROGRESS -> COMPLETED
              |              (or directly from any non-terminal
              |               status if steps were skipped)
              |              Payment check order:
              |              1. Active service agreement? -> skip warning
              |              2. Payment collected on site? -> skip warning
              |              3. Invoice exists? -> skip warning
              |              4. None of above? -> show warning
              |              On-site timestamps cleared on cancel.
              |
             ========= SMS #3: GOOGLE REVIEW (Optional) =========
              |
          Admin clicks "Google Review" button
              |
          [SYSTEM -> CUSTOMER]
          "Thanks for choosing Grins Irrigation!
           We'd appreciate a quick review:
           [Google review deep link URL]"
              |
          (No customer reply expected)
              |
           Done!


========= SMS OUTSIDE THE JOB LIFECYCLE =========

The following SMS messages are triggered from the Invoices tab
and are NOT part of the single-job lifecycle above. They can
be sent at any time, in bulk, to multiple customers at once.

SMS #4: PAST-DUE INVOICE NOTICE (Mass notification)
  Trigger: Admin clicks mass notification on Invoices tab,
           filtered to past-due invoices
  [SYSTEM -> CUSTOMER]
  Template-based message with merge fields:
  "[Customer name], invoice #[number] for $[amount] was due
   on [date] and is now past due. Please remit payment at
   your earliest convenience."
  (No automated reply handling — replies go to general inbox)

SMS #5: UPCOMING-DUE INVOICE REMINDER (Mass notification)
  Trigger: Admin clicks mass notification on Invoices tab,
           filtered to upcoming-due invoices
  [SYSTEM -> CUSTOMER]
  Template-based message with merge fields:
  "[Customer name], this is a reminder that invoice #[number]
   for $[amount] is due on [date]."
  (No automated reply handling — replies go to general inbox)

SMS #6: LIEN NOTICE ELIGIBILITY FLAG
  Trigger: System flags customers 60+ days past due AND
           owing over $500 (thresholds configurable).
           This is a flag for admin review — the SMS
           itself is sent manually after admin decides
           to proceed.
```

### The Correct Sequence: Always Contact First, Then Route

**The Leads tab exists for one reason: to track people who haven't been contacted yet.** You should always contact the lead *before* deciding where to send them. The conversation is what tells you whether they need an estimate or are ready to schedule.

Here's the step-by-step:

1. **A new lead arrives** — it appears in the Leads tab with status "New"
2. **Review the lead** — check the Job Requested, City, and Address columns so you know what they want before you call
3. **Contact them** — call or text the lead
4. **Click "Mark Contacted"** — this changes the status to "Contacted (Awaiting Response)" and timestamps the contact
5. **Based on the conversation**, route them:
   - **"Move to Jobs"** — The job is confirmed and ready to schedule. The system auto-creates a customer record and a job with status "To Be Scheduled." The lead disappears from the Leads tab. **Note:** If the lead's situation maps to "requires estimate" (e.g., Exploring, New System, Upgrade), the system will show a confirmation modal: "This job type typically requires an estimate. Move to Jobs anyway, or move to Sales for the estimate workflow?" with three options: Move to Jobs (proceed with override), Move to Sales (redirect to Sales pipeline), or Cancel.
   - **"Move to Sales"** — They need an estimate before committing. The system auto-creates a customer record and a Sales pipeline entry with status "Schedule Estimate." The lead disappears from the Leads tab.
   - **Delete** — They're not interested or it's spam.

**Why this order matters:** You can't know whether someone needs an estimate or is ready to schedule until you've actually talked to them. The "Job Requested" column gives you context for the call, but the routing decision comes *after* the conversation.

### The Subscription Path (Service Packages)

There's a separate flow for subscription customers who purchase service packages through the onboarding form:

```
Customer fills out onboarding form
    -> Selects service package
    -> Picks preferred weeks for each service
    -> Completes Stripe checkout
    -> System creates: Customer + Service Agreement + Jobs (one per service)
    -> Jobs auto-populated with the customer's preferred weeks
```

When their contract renews the following year, the system generates **proposed jobs** for admin review instead of creating them directly. See [Section 13: Contract Renewals](#13-contract-renewals--annual-renewal-review) for details.

### Understanding the Two Status Tracks: Jobs vs. Appointments

One important concept: **job status and appointment status are two separate things** that progress independently.

**Job status** tracks the overall lifecycle of the work:

| Status | Meaning |
|--------|---------|
| **To Be Scheduled** | Job exists but no appointment has been placed on the calendar yet. |
| **Scheduled** | An appointment has been created on the calendar for this job. Auto-set when appointment is created, reverts if last appointment is cancelled. |
| **In Progress** | Technician has started work on the job (set by clicking "Job Started"). |
| **Completed** | Work is done (triggered by clicking "Job Complete"). Both job and appointment transition to Completed together. |
| **Cancelled** | Job was cancelled. On-site timestamps are cleared. |

**Status progression:** Creating an appointment transitions the job from "To Be Scheduled" to "Scheduled." "On My Way" does not change the job status — it transitions the appointment to "En Route." "Job Started" transitions the job to "In Progress" and the appointment to "In Progress." "Job Complete" transitions both job and appointment to "Completed." Cancelling the last appointment reverts the job from "Scheduled" back to "To Be Scheduled."

**Appointment status** tracks the scheduling and field progression:

| Status | Meaning |
|--------|---------|
| **Draft** | Appointment placed on the calendar but customer has NOT been notified yet. No SMS sent. Shows as dotted border, grayed-out on calendar. Admin can move/delete silently. |
| **Scheduled** | Confirmation SMS has been sent, waiting for customer response (shows as dashed border, muted color). Set when admin clicks "Send Confirmation." |
| **Confirmed** | Customer replied "Y" (shows as solid border, full color) |
| **En Route** | Admin clicked "On My Way" — technician is heading to the property. Set automatically from Confirmed or Scheduled. |
| **In Progress** | Admin clicked "Job Started" — work has begun. Set automatically from En Route (or Confirmed if On My Way was skipped). |
| **Completed** | Admin clicked "Job Complete" — work is done. Set automatically alongside job completion. |
| **Cancelled** | Customer replied "C" or admin cancelled. If was Draft, no SMS sent. If was Scheduled/Confirmed, cancellation SMS sent with appointment details. On-site timestamps cleared. |

**Key points:**
- Appointments now start as **Draft** (not Scheduled). No SMS is sent until the admin explicitly clicks "Send Confirmation."
- Moving a Draft appointment on the calendar is silent — no SMS. Moving a Scheduled or Confirmed appointment sends a reschedule notification SMS and resets to Scheduled.
- Deleting a Draft appointment is silent. Deleting a Scheduled or Confirmed appointment sends a cancellation SMS.
- "On My Way" transitions the appointment to En Route. "Job Started" transitions both job and appointment to In Progress. "Job Complete" transitions both to Completed.
- Job and appointment statuses now progress together through the on-site workflow. Skip scenarios are handled gracefully (e.g., clicking "Job Complete" without "Job Started" still completes both).
- Service agreement jobs show "Covered by [Agreement Name]" and skip the payment warning on completion.

---

## 5. Leads Tab — New Inbound Requests

The Leads tab is where **every new request lives before you contact the person**. This is the first step in the pipeline — you review leads, contact them, and then based on the conversation you route them to either the Jobs tab or the Sales tab. A lead should **always be contacted before being moved** to another tab.

### Columns

| Column | What It Shows |
|--------|---------------|
| **Name** | Customer name (clickable to view details) |
| **Phone** | Contact phone number |
| **Job Address** | Where the work would be performed |
| **City** | City derived from the address — helps with scheduling by area |
| **Job Requested** | What service they're asking for — you can see this at a glance without clicking in |
| **Status** | Either "New" or "Contacted (Awaiting Response)" |
| **Last Contacted Date** | When you last reached out (auto-updates from SMS when messaging is active) |
| **Source** | Where the lead came from (far right column, no color highlighting) |

### Statuses

There are only **two** lead statuses — intentionally simple:

- **New** — Default. This lead has not been contacted yet.
- **Contacted (Awaiting Response)** — You've reached out and are waiting to hear back.

### Actions Available Per Lead

Each lead row has action buttons. The intended order of operations is: **Mark Contacted first, then route the lead based on the conversation.**

| Button | When to Use | What It Does |
|--------|-------------|--------------|
| **Mark Contacted** | **Always do this first** — after you call or text the lead | Changes status to "Contacted (Awaiting Response)" and sets the Last Contacted Date to right now |
| **Move to Jobs** | After contacting — the customer confirmed the job and is ready to schedule | Auto-creates a customer (if one doesn't exist for this lead), creates a job with status "To Be Scheduled", removes the lead from this list |
| **Move to Sales** | After contacting — the customer needs an estimate before committing | Auto-creates a customer (if one doesn't exist for this lead), creates a Sales pipeline entry with status "Schedule Estimate", removes the lead from this list |
| **Delete** | The lead is spam, a duplicate, or they're not interested | Permanently deletes the lead (shows a confirmation modal — this cannot be undone) |

### Important Behavior

- **Always contact before routing.** The Leads tab is for tracking people who haven't been reached yet. "Mark Contacted" should come before "Move to Jobs" or "Move to Sales."
- When you "Move to Jobs" or "Move to Sales," the lead **automatically disappears** from the Leads tab. You don't need to manually delete it.
- If a customer record already exists (matching phone or email), the system will show a **"Possible match found"** warning so you can link to the existing customer instead of creating a duplicate.

---

## 6. Sales Tab — Estimates and the Sales Pipeline

The Sales tab is for **leads that need an estimate before the work can begin**. Every lead that you send here from the Leads tab lives in this pipeline until they either sign and become a job, or they're marked as lost.

### Pipeline Overview

At the top of the Sales tab you'll see **4 summary boxes** showing counts of entries in key stages (Needs Estimate, Pending Approval, Needs Follow-Up, Revenue Pipeline).

Below that is the **pipeline list** with these columns:

| Column | What It Shows |
|--------|---------------|
| **Customer Name** | The customer's name |
| **Phone** | Their phone number |
| **Address** | Property address |
| **Job Type** | What service they need |
| **Status** | Current pipeline stage (see below) |
| **Last Contact Date** | When you last interacted with this entry |

### Pipeline Statuses (In Order)

The pipeline progresses through these stages. Each stage has an **action button** that advances it to the next step:

| Status | What It Means | What You Do | Action Button |
|--------|--------------|-------------|---------------|
| **Schedule Estimate** | Need to set up an estimate visit | Schedule the visit on the Estimate Calendar | Click to advance to "Estimate Scheduled" |
| **Estimate Scheduled** | Estimate visit is on the calendar | Go to the property, assess the job | (Advance after the visit) |
| **Send Estimate** | Visit done, need to send the written estimate | Create the estimate externally, upload it to the Documents section, then send for signature | Click to advance to "Pending Approval" |
| **Pending Approval** | Estimate sent to customer, waiting for them to sign | Wait for the customer to sign | (Advances automatically when they sign via SignWell) |
| **Send Contract** | Estimate approved, need to send the final contract | Send the final contract for signature | Click to advance |
| **Closed-Won** | Customer signed, ready to convert to a Job | Click "Convert to Job" | Terminal state |
| **Closed-Lost** | Customer declined or went elsewhere | — | Terminal state |

**How status advances work:**
- Click the action button on a row and the status moves **exactly one step forward**. You can't skip steps.
- If a customer signs via email or the embedded signing iframe, the system **automatically** advances from "Pending Approval" to "Send Contract."
- You can **manually override** the status via a dropdown for exceptional cases.
- You can click **"Mark Lost"** on any entry at any stage to move it to Closed-Lost.

### Creating Estimates and Contracts

**The CRM does not have a built-in estimate or contract builder.** You create your estimates and contracts **outside the CRM** using whatever tool you prefer (Word, PDF editor, estimating software, etc.), then upload the finished document into the CRM for storage and signature.

Here's the full process:

1. **Go to the property** and assess the job (while the entry is at "Estimate Scheduled")
2. **Create the estimate** in your external tool based on what you saw on-site
3. **Click into the sales entry** to open the detail view
4. **Upload the estimate PDF** in the **Documents Section** (supports PDFs, images, and docs up to 25 MB)
5. **Advance the status** to "Send Estimate"
6. **Send for signature** using one of two methods:
   - **"Send Estimate for Signature (Email)"** — sends the document to the customer's email for remote digital signature via SignWell. This button is disabled if the customer has no email on file.
   - **"Sign On-Site (Embedded)"** — opens an embedded signing iframe on your device so the customer can sign in person (useful if you're still at the property).
7. The status advances to **"Pending Approval"** while waiting for the customer to sign
8. When the customer signs, the system automatically stores the signed copy and advances to **"Send Contract"**

The same process applies for contracts — create externally, upload to Documents, send for signature through the CRM.

### Sales Detail View

Click any sales entry row to expand it. The detail view gives you:

- **Documents Section** — This is where you upload your externally-created estimates, contracts, and any supporting documents (site photos, diagrams, reference materials). You can upload, download, preview, and delete files. Supports PDFs, images, and common doc types up to 25 MB each. When a customer signs a document through SignWell, the signed copy is automatically saved here as well.
- **Send Estimate for Signature (Email)** — Sends the document to the customer's email for digital signature via SignWell. Disabled if the customer has no email on file.
- **Sign On-Site (Embedded)** — Opens an embedded signing iframe so the customer can sign on your device in person. Useful for when you're at the property.
- **Convert to Job** — Creates a real Job from this sales entry. This button is **disabled until the customer has signed** (tooltip: "Waiting for customer signature").
- **Force Convert to Job** — Bypasses the signature requirement. Shows a confirmation warning. The system logs this override with a flag on the record.

### Sales Calendar (Estimate Calendar)

The Sales tab has its own **separate calendar** (under the "Estimate Calendar" tab) for scheduling estimate visits. This is independent from the main Jobs schedule — estimate appointments don't show up on the job calendar and vice versa.

To schedule an estimate visit:
1. Go to the Sales tab and switch to the Estimate Calendar view
2. Click to create a new appointment
3. Select the sales entry from the dropdown, fill in the date, time, and notes
4. Save — the appointment appears on the sales calendar

**Automatic status sync:** When you create a calendar event for a sales entry that is at "Schedule Estimate" status, the system **automatically advances** the entry to "Estimate Scheduled." You no longer need to manually advance the status — saving the calendar event handles it. If the entry is already at "Estimate Scheduled" or later, no status change occurs (no double-advance).

**Alternative:** You can also schedule an estimate directly from the pipeline list by clicking the "Schedule Estimate" action button on a sales entry. This opens a calendar event creation form pre-filled with the customer's name and property address. Saving the event creates the calendar appointment and auto-advances the status in one step.

---

## 7. Customers Tab — The Master Customer Record

The Customers tab is the **one-stop shop for all customer data**. Every customer has a detail page that aggregates everything: their properties, jobs, invoices, service agreements, notes, photos, communications, and preferences.

### Customer Detail Page

When you click into a customer, you see:

- **Contact information** — name, phone, email, address
- **Properties** — each property tagged with:
  - **Residential** or **Commercial** badge
  - **HOA** badge (if the property is in an HOA)
  - **Subscription** badge (if the property has an active service agreement)
- **Jobs** — all jobs associated with this customer
- **Invoices** — all invoices for this customer (updates in real-time when invoice status changes)
- **Service Agreements** — active subscription contracts
- **Communications** — SMS/email history
- **Notes and Photos** — any notes or photos added from job visits
- **Documents** — uploaded files (estimates, contracts, signed documents)

### Service Preferences

Each customer can have **multiple service preferences** — structured scheduling hints that tell you when they prefer to have specific services done.

To manage preferences:
1. Go to the customer detail page
2. Scroll to the **"Service Preferences"** section
3. Click **"Add Preference"** to open the form

Each preference includes:
- **Service Type** — dropdown: Spring Startup, Mid-Season Inspection, Fall Winterization, Monthly Visit, or Custom
- **Preferred Week** — a week picker for which week of the year they want the service
- **Preferred Date** — optional, overrides the week with a specific date
- **Time Window** — Morning, Afternoon, Evening, or Any
- **Notes** — free text for special instructions (e.g., "Only available MWF after 1 PM")

**How preferences connect to jobs:** When you create a job for a customer and the job's service type matches one of their preferences, the system **auto-populates the "Week Of" field** from the preference. The preference notes also appear as a **read-only hint** on the job detail view so you can see their constraints while scheduling.

### Property Type Tags

Every property is tagged with one or more visual badges:

| Tag | Meaning |
|-----|---------|
| **Residential** | Residential property |
| **Commercial** | Commercial property |
| **HOA** | Property is in a homeowners association |
| **Subscription** (or "Sub") | Property has an active service agreement |

These tags appear on the property list, customer detail, job detail, and job list views. You can **filter** by any combination of these tags on the Customers, Jobs, and Sales lists.

---

## 8. Jobs Tab — Approved Work Ready to Schedule

The Jobs tab contains **only jobs that are approved and ready to be scheduled**. If a job still needs an estimate, it should be in the Sales tab, not here.

### Job List Columns

The job list shows:
- **Job Type** — what service is being performed
- **Customer** — who the job is for
- **Address** — where the work will happen
- **Week Of** — the target week for the job (displayed as "Week of M/D/YYYY" where the date is always the Monday of that week)
- **Status** — current job status
- **Property Tags** — Residential/Commercial, HOA, Subscription badges on each row

### The "Week Of" Concept — Two-Step Scheduling

Instead of a specific due date, jobs use a **two-step scheduling** process:

**Step 1 — Week-level target (Jobs tab):** When a job is created, it gets a "Week Of" assignment — a target week for when the work should happen. You set this using the **Week Picker**, a calendar that highlights entire Monday-through-Sunday weeks. The display shows "Week of 4/20/2026" (always the Monday date). This is a **planning target**, not a firm appointment.

**Step 2 — Specific date/time/staff (Schedule tab):** As the target week approaches, you go to the Schedule tab and use the Job Picker to find jobs targeting that week. You assign each job to a **specific date, time, and staff member**, which creates an appointment on the calendar. This is when the customer gets the SMS confirmation.

Think of it this way: "Week Of" answers *"which week should this get done?"* and the Schedule tab answers *"what day, what time, and who's doing it?"*

If the customer has service preferences on file (e.g., "only available MWF after 1 PM"), those preferences appear as hints when you're making the specific date/time assignment.

### Filtering

You can filter the Jobs list by:
- **Status** — To Be Scheduled, In Progress, Completed, etc.
- **Property type** — Residential, Commercial
- **HOA** — Yes/No
- **Subscription** — Yes/No
- **Week** — specific week ranges
- Combinations of the above (filters combine as AND)

---

## 9. Schedule Tab — Building and Managing the Daily Schedule

The Schedule tab is where you take jobs from the Jobs tab and assign them to **specific dates, times, and staff**. This is the second step of the two-step scheduling process — the job already has a "Week Of" target from the Jobs tab, and now you're pinning it to an exact slot on the calendar.

### Adding Jobs to the Schedule

There are two ways to add jobs to the schedule:

**From the Schedule tab:**
1. Click to add jobs manually. A **Job Picker Popup** appears.
2. The popup looks exactly like the Jobs tab — same columns, same filters, same search. Filter by "Week Of" to find jobs targeting the upcoming week.
3. **Single job**: Select a job and assign it a date, time, and staff member.
4. **Bulk assignment**: Select **multiple jobs** at once, then assign all of them to a specific date and staff member with a global time allocation per job. After the bulk assignment, you can adjust the time for each job individually.

**From the Jobs tab:**
- Each job in TO_BE_SCHEDULED or SCHEDULED status has a **"Schedule" button** on its row. Clicking it navigates directly to the Schedule tab with the appointment creation form pre-filled with that job's customer, job type, and address.

When creating an appointment, the **job selector** is a searchable combobox that shows each job as "Customer Name — Job Type (Week of M/D)" with the customer's address, property tags (Residential, HOA, Subscription), and service preference notes. You can search by customer name, job type, or address, and sort by Week Of date, customer name, or area.

When you assign a job, the system creates an **appointment** on the calendar in **DRAFT** status. No SMS is sent yet — the appointment appears with a dotted border and grayed-out styling. You send confirmations when you're ready (see Draft Mode below).

### Draft Mode and Appointment Visual States

Appointments on the calendar have three visual states:

| Appearance | Status | Meaning |
|------------|--------|---------|
| **Dotted border, grayed-out** | Draft | On the calendar but customer has NOT been notified. No SMS sent. Can be moved/deleted silently. |
| **Dashed border, muted background** | Scheduled (Unconfirmed) | Confirmation SMS sent, waiting for customer reply. |
| **Solid border, full color** | Confirmed | Customer replied "Y" to the confirmation SMS. |

Service agreement jobs also show a **"PREPAID"** badge on their calendar card and a green left-border accent.

### Sending Confirmations

Draft appointments don't send any SMS until you explicitly trigger it. There are three ways to send confirmations:

1. **Per-appointment**: Click the "Send Confirmation" button on an individual draft appointment card.
2. **Per-day**: Click "Send Confirmations for [Day]" on a day column header to send for all drafts on that day.
3. **Bulk**: Click "Send All Confirmations" at the top of the Schedule tab. A summary modal shows the count, customer names, and dates. Click "Send All" to confirm.

When a confirmation is sent, the appointment transitions from DRAFT to SCHEDULED and the visual changes from dotted/grayed to dashed/muted.

### Appointment Editing

Click on any appointment to open the **Appointment Details** modal. From there, click **"Edit"** to modify the appointment's date, time, staff, or notes. The edit form opens pre-populated with the current data. Saving refreshes the calendar view.

If you edit a SCHEDULED or CONFIRMED appointment's date or time, the system automatically sends a **reschedule notification SMS** to the customer and resets the status to SCHEDULED. Editing a DRAFT appointment is silent — no SMS.

### Appointment Confirmation Flow (Y/R/C)

When you send a confirmation (via the "Send Confirmation" button, per-day, or bulk), the system sends an SMS to the customer:

> "Your appointment on [date] [time] has been scheduled. Reply Y to confirm, R to reschedule, or C to cancel."

The customer replies by text:

| Reply | What Happens |
|-------|-------------|
| **Y** (or yes, confirm, ok, okay) | Appointment status changes from Unconfirmed to **Confirmed**. Customer gets a confirmation reply. The job card on the schedule switches to solid border/full color. |
| **R** (or reschedule, different time, change time) | A **reschedule request** is created and appears in your Reschedule Requests queue. The customer receives a reply acknowledging their request. |
| **C** (or cancel, cancelled) | The appointment is **cancelled**. The customer gets a cancellation reply. You are notified. |
| **Anything else** | Logged as "needs review" for you to handle manually. |

### Reschedule Requests Queue

Accessible from the Schedule tab, this queue shows all customer reschedule requests:

- **Customer name** and original appointment details
- **Requested alternatives** — what dates/times the customer asked for (parsed or raw text)
- **"Reschedule to Alternative"** — opens the appointment editor pre-filled with the customer's requested time
- **"Mark Resolved"** — closes the request after you've handled it

---

## 10. On-Site Job Operations — The Field Workflow

When you're out in the field performing a job, the job detail view gives you everything you need to manage the visit from start to finish.

### Status Progression Buttons

The job detail view has three status buttons that track the lifecycle of a field visit. These buttons are used in order during the visit:

| Button | What It Does | Job Status Change | Appointment Status Change |
|--------|-------------|-------------------|--------------------------|
| **On My Way** | Sends an SMS to the customer: "We're on our way!" Logs the `on_my_way_at` timestamp. | No change | CONFIRMED → EN_ROUTE (or SCHEDULED → EN_ROUTE) |
| **Job Started** | Logs the `started_at` timestamp. | **SCHEDULED → In Progress** | EN_ROUTE → IN_PROGRESS (or CONFIRMED → IN_PROGRESS if On My Way skipped) |
| **Job Complete** | Marks the job as complete (with a payment check — see below). Logs the `completed_at` timestamp. | **In Progress → Completed** | IN_PROGRESS → COMPLETED (or any non-terminal → COMPLETED if steps skipped) |

**Important:** "On My Way" does **not** change the job's status — it only transitions the appointment to EN_ROUTE, logs a timestamp, and sends an SMS. "Job Started" transitions both the job to "In Progress" and the appointment to "In Progress." "Job Complete" transitions both to "Completed." Steps can be skipped — clicking "Job Complete" without "Job Started" still completes both.

**Time tracking:** The system automatically calculates the time elapsed between these three timestamps — travel time (On My Way to Started), work time (Started to Complete), and total time. This metadata is stored per job type and staff member for future scheduling optimization.

### Payment Warning on Completion

When you click **"Job Complete"**, the system checks in this order:

1. **Active service agreement?** → Skip warning entirely (job is pre-paid)
2. **Payment collected on site?** → Skip warning
3. **Invoice exists?** → Skip warning (regardless of invoice status)
4. **None of the above?** → Warning modal appears: **"No Payment or Invoice on File"** with two options:
   - **Cancel** — go back, collect payment or create an invoice first
   - **Complete Anyway** — completes the job without payment (this override is logged for audit purposes)

### Other On-Site Actions

| Action | What It Does |
|--------|-------------|
| **Create Invoice** | Generates an invoice pre-filled with customer and job data. The invoice appears in the Invoices tab. Hidden for service agreement jobs. |
| **Add Notes** | Add text notes to the job. Notes sync to the customer record and are linked to this specific job for context. |
| **Add Photos** | Upload photos from the job site. On mobile, tapping "Add Photo" opens the camera directly. Photos sync to the customer record and are linked to this job. |
| **Google Review Push** | Sends an SMS to the customer with a link to leave a Google review. Uses the configurable `GOOGLE_REVIEW_URL` environment variable. |
| **Collect Payment** | Two options: **"Pay with Card (Tap to Pay)"** uses Stripe Terminal NFC for contactless card payments via your phone. **"Record Other Payment"** lets you manually record cash, check, Venmo, or Zelle payments. After a successful tap-to-pay, the system offers to send an SMS or email receipt. |

### Payment Path Differentiation

The job detail view shows different payment sections depending on the job's payment situation:

| Situation | What You See |
|-----------|-------------|
| **Service agreement job** | "Covered by [Agreement Name] — no payment needed" with green checkmark. Create Invoice and Collect Payment buttons are hidden. |
| **One-off job, no invoice** | Both "Create Invoice" and "Collect Payment" buttons are visible. |
| **One-off job, invoice sent** | "Invoice #[number] — Sent on [date], $[amount]" with status badge. "Collect Payment" still available (customer may want to pay on-site). |
| **One-off job, paid on-site** | "Payment collected — $[amount] via [method]" with green checkmark. No payment buttons shown. |

On the Schedule tab calendar, service agreement jobs show a **"PREPAID"** badge so you can see at a glance which appointments need payment collection during the day's route.

### After Job Completion

When a job is marked as complete:
- The job status changes to **Completed**
- The appointment status also changes to **Completed** (both transition together)
- It **archives out of the active schedule view** (no longer clutters the daily calendar)
- It **remains visible in the Jobs tab** under the "Completed" status filter
- The customer's record is updated with the completion data
- Time tracking metadata is calculated (travel time, work time, total time)

---

## 11. Invoices Tab — Billing and Collections

The Invoices tab is where you manage all billing — track what's owed, what's paid, and what's overdue.

### Invoice List Columns

| Column | What It Shows |
|--------|---------------|
| **Invoice Number** | Unique invoice identifier |
| **Customer Name** | Who owes |
| **Job** | Clickable link to the related job |
| **Cost** | Invoice amount |
| **Status** | Color-coded badge (see below) |
| **Days Until Due** | For pending invoices |
| **Days Past Due** | For overdue invoices |
| **Payment Type** | Credit Card, Cash, Check, ACH, Other |

### Status Colors

| Color | Status |
|-------|--------|
| **Green** | Complete (paid) |
| **Yellow** | Pending (sent but not yet paid) |
| **Red** | Past Due |

### Filtering (9 Axes)

The Invoices tab has the most powerful filtering in the system. Click the **filter panel** (collapsible sidebar) and you can filter on **any combination** of:

1. **Date range** — by created date, due date, or paid date
2. **Status** — Complete, Pending, Past Due, etc.
3. **Customer** — searchable dropdown
4. **Job** — searchable dropdown
5. **Amount range** — min and/or max dollar amount
6. **Payment type** — multi-select (Credit Card, Cash, Check, ACH, Other)
7. **Days until due** — numeric range
8. **Days past due** — numeric range
9. **Invoice number** — exact match

**How filtering works:**
- Active filters appear as **removable chip badges** above the list. Click the X on a chip to remove that filter.
- Filters combine as **AND** — each filter you add narrows the results further.
- **"Clear all filters"** button resets to the full unfiltered list.
- Filter state is saved in the **URL** — you can bookmark a filtered view or share the link and the recipient sees the same filters applied.
- You can **save filter combinations** for quick reuse.

### Mass Notifications

The Invoices tab supports bulk outreach to customers:

- **Past-due notices** — notify all customers with past-due invoices
- **Upcoming-due reminders** — notify customers with invoices due within a configurable window
- **Lien notice eligibility** — flag customers who are 60+ days past due AND owe over $500 (thresholds are configurable)

Mass notifications are sent via SMS using configurable templates with merge fields (customer name, invoice number, amount, due date).

---

## 12. Service Packages and Onboarding — Subscription Customers

When a customer purchases a service package through the online onboarding form, a specific flow kicks off:

### The Onboarding Flow

1. **Customer fills out the onboarding form** on the customer-facing website
2. **Session verification** — the system validates the customer's session and returns the available services with types
3. **Service week selection** — for each service in their package, the customer picks their **preferred week** using a dropdown (e.g., "Week of April 20" for Spring Startup, "Week of October 12" for Winterization)
4. **Stripe checkout** — customer completes payment
5. **Stripe webhook fires** — the system receives confirmation of payment

### What the System Creates Automatically

After the Stripe checkout webhook fires:

- **Customer record** — with contact info from the onboarding form
- **Service Agreement** — the subscription contract linking the customer to the package, with the `service_week_preferences` stored as structured data
- **Jobs** — one job per service in the package, each with:
  - **Week Of** set to the customer's selected week (Monday-Sunday range)
  - Service type matching the package service
  - Status: To Be Scheduled

### Week Preference Logic

- If the customer selected preferred weeks during onboarding, jobs are created with those exact weeks as the target.
- If no week preferences were provided (null), the system falls back to **default calendar-month ranges** for each service type.

### After Onboarding

The created jobs appear in the **Jobs tab** with a **"Sub" (Subscription)** tag, ready to be assigned to the schedule. The service agreement appears on the customer's detail page.

---

## 13. Contract Renewals — Annual Renewal Review

When a subscription customer's service contract auto-renews (annual renewal via Stripe), the system does **NOT** create jobs directly. Instead, it creates a **renewal proposal** for you to review.

### Why Proposals Instead of Automatic Jobs

This gives you a chance to:
- Verify the renewal is correct (not an accidental charge)
- Adjust the week assignments for the new year
- Add notes about any changes
- Reject individual services the customer no longer wants
- Reject the entire renewal if it fired in error

### The Renewal Flow

1. **Stripe `invoice.paid` webhook fires** for an auto-renewing service agreement
2. System creates a **Renewal Proposal** containing proposed jobs for the new contract year
3. Each proposed job's target date is **rolled forward by one year** from the prior year's week preferences
4. A **dashboard alert** fires: "1 contract renewal ready for review: [customer name]"
5. You review the proposal on the **Contract Renewals** page

### Contract Renewals Page

The page shows a list of pending proposals with:

| Column | What It Shows |
|--------|---------------|
| **Customer** | Customer name |
| **Agreement** | Service agreement name/number |
| **Proposed Job Count** | How many jobs in this renewal batch |
| **Created Date** | When the proposal was generated |
| **Status** | Pending, Approved, Partially Approved, Rejected |
| **Actions** | Approve All, Reject All, or click in for per-job review |

### Reviewing a Proposal

Click into a proposal to see each proposed job individually. For each proposed job you can:

| Action | What It Does |
|--------|-------------|
| **Approve** | Creates a real Job record with the proposed dates. The job appears in the Jobs tab. |
| **Reject** | Marks this proposed job as rejected. No job is created. |
| **Modify** | Change the Week Of target using the week picker, add admin notes, then approve with the modified dates. |
| **Add Notes** | Free-text annotation field on each proposed job. |

**Bulk actions:**
- **Approve All** — approves every proposed job in the batch at once, creating real jobs for all of them.
- **Reject All** — rejects the entire proposal. No jobs created. Useful when the renewal webhook fired in error or the customer isn't actually renewing.

**Partial approval:** You can approve some jobs and reject others. The proposal status will show as "Partially Approved."

### Date Rolling Logic

When the system generates proposed jobs from a renewal:
- If the agreement has prior-year week preferences (e.g., customer picked "Week of April 20, 2026" last year), the new year's job targets "Week of April 21, 2027" (the closest Monday one year later).
- If no prior preferences exist, it falls back to default calendar-month ranges per service type.

---

## 14. Duplicate Customer Management

The system automatically detects potential duplicate customer records overnight and gives you tools to review and merge them.

### How Duplicate Detection Works

A **nightly background job** runs at 1:30 AM and scans all active customers. It compares pairs using weighted signals:

| Signal | Points |
|--------|--------|
| Same phone number (normalized) | +60 |
| Same email address (lowercase) | +50 |
| Very similar name (Jaro-Winkler score >= 0.92) | +25 |
| Same street address (normalized) | +20 |
| Same ZIP + same last name | +10 |

Scores are capped at 100. Pairs scoring **80+** are flagged as "High confidence duplicate." Pairs scoring **50-79** are flagged as "Possible duplicate." Below 50, no flag.

**Important:** The system **never auto-merges** customers, even at a perfect 100 score. All merges require your explicit action.

### Reviewing Duplicates

1. Go to the **Customers** tab
2. Click the **"Review Duplicates"** button (shows a count badge of pending pairs)
3. The review queue shows duplicate pairs sorted by confidence score (highest first)
4. Click a pair to open the **side-by-side comparison modal**

### The Merge Modal

The comparison modal shows both records side by side with every field. For each conflicting field:
- Radio buttons let you choose which value to keep
- The primary record's value is selected by default
- If one record has an empty field and the other has a value, the non-empty value is defaulted

### Merge Rules

- **Jobs, invoices, notes, communications, agreements, and properties** from the duplicate record are all **reassigned** to the surviving record. No data is lost.
- The duplicate record is **soft-deleted** (marked with `merged_into_customer_id`). It is not permanently destroyed.
- An **audit log entry** records who performed the merge, when, and which values survived.

### Merge Blockers

The system will **block a merge** if both customers have active Stripe subscriptions. You'll see an error: "Both customers have active Stripe subscriptions. Cancel one subscription before merging." This prevents accidental billing issues.

### Real-Time Duplicate Warning

When you create a new customer or convert a lead, the system does a **real-time check** for Tier 1 matches (exact phone or email). If a match is found, you'll see an inline **"Possible match found"** warning with a **"Use existing customer"** button, so you can link to the existing record instead of creating a duplicate.

---

## 15. SMS and Customer Communication

The CRM uses SMS (currently via CallRail) for several automated and manual communication flows:

### Automated SMS

| Trigger | Message Sent |
|---------|-------------|
| **"Send Confirmation" clicked** | Confirmation request: "Reply Y to confirm, R to reschedule, C to cancel" (transitions DRAFT → SCHEDULED) |
| **"On My Way" button clicked** | "We're on our way! Your technician is heading to your location now." |
| **Customer confirms (Y)** | Auto-reply confirming the appointment |
| **Customer reschedules (R)** | Acknowledgment reply + follow-up: "We'd be happy to reschedule. Please reply with 2-3 dates and times that work for you and we'll get you set up." |
| **Customer cancels (C)** | Detailed cancellation: "Your [service type] appointment on [date] at [time] has been cancelled. If you'd like to reschedule, please call us at [business phone]." |
| **Appointment rescheduled** | Reschedule notification sent to customer (only for SCHEDULED/CONFIRMED appointments, not DRAFT) |
| **Appointment deleted** | Cancellation SMS sent (only for SCHEDULED/CONFIRMED appointments, not DRAFT) |
| **Mass invoice notification** | Template-based reminder with invoice details and amount |

### Manual SMS Triggers

| Action | Where |
|--------|-------|
| **Google Review Push** | Job detail view — sends a review link via SMS using the configurable `GOOGLE_REVIEW_URL`. Respects 30-day dedup and SMS consent. |

### How Reply Correlation Works

When the system sends an appointment confirmation SMS, it tracks the message with a **thread ID** from the SMS provider. When the customer replies, the inbound message is matched back to the original confirmation via that thread ID. This is how the system knows which appointment a "Y" or "R" or "C" reply is about.

---

## 16. Quick Reference — Common Workflows

### "A new lead just came in — what do I do?"

1. Go to **Leads** tab
2. Review the lead — check Job Requested, City, and Address so you know what they want before calling
3. **Contact the customer** — call or text them
4. Click **"Mark Contacted"** to update the status to "Contacted (Awaiting Response)" and timestamp it
5. When they respond, route them based on the conversation:
   - They're ready to schedule -> click **"Move to Jobs"**
   - They need an estimate first -> click **"Move to Sales"**
   - They're not interested -> click **Delete**

**Remember:** Always contact first, then route. You can't know whether they need an estimate or are ready to go until you've talked to them.

### "I need to give a customer an estimate"

1. The lead should already be in the **Sales** tab (you contacted them first in the Leads tab, then clicked "Move to Sales")
2. Schedule the estimate visit:
   - Go to the **Estimate Calendar** tab within Sales
   - Create an appointment for this sales entry with a date and time
   - Back on the pipeline list, click the action button to advance to **"Estimate Scheduled"**
3. **Go to the property** and assess the job
4. **Create the estimate** in your external tool (Word, PDF editor, estimating software, etc.) — the CRM does not have a built-in estimate builder
5. Click into the sales entry detail view and **upload the estimate PDF** in the **Documents** section
6. Click the action button to advance to **"Send Estimate"**
7. Send for signature:
   - **"Send Estimate for Signature (Email)"** — if the customer is remote
   - **"Sign On-Site"** — if the customer is in front of you
8. Status moves to **"Pending Approval"** — wait for the customer to sign
9. When they sign, status auto-advances to **"Send Contract"**
10. Once everything is signed, click **"Convert to Job"** to create a real job in the Jobs tab

### "I need to schedule jobs for the week"

1. Go to **Schedule** tab
2. Click to add jobs — the Job Picker Popup appears
3. Filter by **Week Of** to find jobs targeting the upcoming week (also filter by area, property type, etc.)
4. Select multiple jobs for bulk assignment
5. Choose the date, staff member, and time allocation
6. Fine-tune individual job times after bulk assignment
7. All appointments are created as **DRAFT** — no SMS sent yet
8. Review the week's schedule, move appointments around as needed (silent — no SMS for drafts)
9. When satisfied, click **"Send All Confirmations"** to send SMS to all customers at once (or send per-day or per-appointment)
10. Watch the calendar for confirmations — appointments switch from dashed (unconfirmed) to solid (confirmed) as customers reply "Y"
11. Check the **Reschedule Requests** queue for any "R" replies that need attention

### "A customer wants to reschedule"

1. Check the **Reschedule Requests** queue in the Schedule tab
2. Review the customer's requested alternatives
3. Click **"Reschedule to Alternative"** to open the appointment editor pre-filled with their preferred time
4. Save the new appointment
5. Click **"Mark Resolved"** to close the request

### "I'm at a job site — what's the workflow?"

1. Open the job detail on your device
2. Click **"On My Way"** — sends SMS to customer ("We're on our way!"), logs your departure time
3. Arrive at site, click **"Job Started"** — logs your arrival time, transitions job status to "In Progress" (no SMS sent)
4. Perform the work
5. Add **notes** and **photos** from the job during the visit
6. **Collect payment** on site if possible:
   - **Service agreement jobs**: No payment needed — shows "Covered by [Agreement Name]"
   - **One-off jobs**: Use "Pay with Card (Tap to Pay)" for contactless card payment via Stripe Terminal, or "Record Other Payment" for Cash, Check, Venmo, Zelle
   - After tap-to-pay, option to send SMS or email receipt
7. Or **create an invoice** to send later if they're not paying on the spot (hidden for service agreement jobs)
8. Click **"Job Complete"** — system checks for payment/invoice first:
   - If payment was collected or invoice was sent: job completes (status → Completed)
   - If neither: warning modal appears — you can "Complete Anyway" or go back
9. Optionally send a **Google Review** request via SMS

**Note:** "On My Way" doesn't change the job status — it just logs a timestamp and sends an SMS. "Job Started" transitions the job to "In Progress." "Job Complete" transitions from "In Progress" to "Completed." The system calculates travel time, work time, and total time from these three timestamps.

### "I need to find a specific invoice"

1. Go to **Invoices** tab
2. Open the **Filter Panel**
3. Use any combination of the 9 filter axes
4. Active filters show as chip badges — click X to remove one
5. Bookmark the URL to save the filtered view

### "A subscription customer renewed — now what?"

1. You'll see a **dashboard alert**: "1 contract renewal ready for review"
2. Go to **Contract Renewals** page
3. Click into the proposal
4. Review each proposed job — check the dates, add notes if needed
5. **Approve All** if everything looks good, or approve/reject/modify individual jobs
6. Approved jobs appear in the **Jobs** tab ready to schedule

---

*Last updated: April 14, 2026 — Smoothing Out After Update 2 (Draft mode, Scheduled status, on-site status wiring, cancellation cleanup, payment UI differentiation, Stripe Tap-to-Pay, estimate calendar sync, signing wiring, no-estimate enforcement, reschedule follow-up SMS, mobile-friendly on-site view)*
