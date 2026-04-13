# Smoothing Out After Update 2

Post-CRM Changes Update 2 — remaining gaps, suggested improvements, and integration work needed to bring the platform to full production readiness.

---

## 1. Job Status: Add "Scheduled" Status

### The Problem

Currently, a job's status stays **"To Be Scheduled"** from the moment it's created all the way until someone clicks "Job Started" on-site. When you look at the Jobs tab, there's no way to distinguish between:
- Jobs that haven't been assigned to the schedule yet
- Jobs that are already on the calendar with a date, time, and staff member

This makes it hard to know what still needs your attention when building the weekly schedule.

### Proposed Change

Add a **"Scheduled"** job status between "To Be Scheduled" and "In Progress."

**New job status flow:**
```
TO_BE_SCHEDULED  →  SCHEDULED  →  IN_PROGRESS  →  COMPLETED
                                                →  CANCELLED (from any non-terminal)
```

**When the transition happens:** When an appointment is created on the Schedule tab (job is assigned to a specific date, time, and staff member), the job status automatically changes from "To Be Scheduled" to "Scheduled."

**Why this trigger and not customer confirmation:** Whether the customer has confirmed (replied "Y") is already tracked by the appointment status and the visual styling on the calendar (dashed = unconfirmed, solid = confirmed). The job status should answer "has this been put on the calendar?" — not "has the customer replied to the SMS?" Those are two different questions.

### Implementation Scope

**Backend:**
- Add `SCHEDULED` to the `JobStatus` enum in `src/grins_platform/models/enums.py`
- Update `VALID_JOB_TRANSITIONS` to: `TO_BE_SCHEDULED → {SCHEDULED, CANCELLED}`, `SCHEDULED → {IN_PROGRESS, TO_BE_SCHEDULED, CANCELLED}`, `IN_PROGRESS → {COMPLETED, CANCELLED}`
- In the appointment creation flow (`src/grins_platform/services/appointment_service.py` or `src/grins_platform/api/v1/appointments.py`), after creating the appointment, update the associated job's status to `SCHEDULED`
- Handle edge case: if an appointment is cancelled and it was the job's only appointment, should the job revert to `TO_BE_SCHEDULED`? (Suggested: yes, if no other active appointments exist for that job)
- Alembic migration to add the new enum value

**Frontend:**
- Update the Jobs tab status filter to include "Scheduled"
- Update any status badge rendering to show "Scheduled" with an appropriate color
- No changes needed to the Schedule tab — appointment creation already works, it just needs to trigger the job status change on the backend

**Tests:**
- Update property-based tests for job status transitions
- Test: creating appointment → job moves to SCHEDULED
- Test: cancelling the only appointment → job reverts to TO_BE_SCHEDULED
- Test: cancelling one of multiple appointments → job stays SCHEDULED

### Effort Estimate

Small-medium. The status enum change and transition logic are straightforward. The main work is wiring the appointment creation to also update the job status, and deciding on the cancellation revert behavior.

---

## 2. On-Site Status Progression: "On My Way" and "Job Started" Don't Change Status

### The Problem

The source doc describes "On My Way," "Job Started," and "Job Complete" as a status progression — three steps tracking the field visit from departure to completion. But in the current implementation, **only "Job Complete" changes any status**. The other two are pure timestamp loggers:

| Button | What the source doc implies | What the code actually does |
|--------|----------------------------|-----------------------------|
| **On My Way** | Progression step — technician is en route | Logs `on_my_way_at` timestamp, sends SMS. **No job or appointment status change.** |
| **Job Started** | Progression step — work has begun | Logs `started_at` timestamp. **No job or appointment status change.** |
| **Job Complete** | Final step — work is done | Changes job status TO_BE_SCHEDULED → COMPLETED. Checks payment/invoice. Calculates time tracking. |

This means:
- The job jumps directly from **"To Be Scheduled" to "Completed"** — it never enters "In Progress" even though the status exists in the enum
- The appointment stays **"Confirmed"** through the entire visit and even after the job is completed — "On My Way" doesn't move it to "En Route," and job completion doesn't auto-complete the appointment
- The valid appointment statuses EN_ROUTE and IN_PROGRESS exist in the model but are never set by any automated flow

### Impact

- The Jobs tab can't distinguish between "jobs waiting to be scheduled" and "jobs actively being worked on right now" — both show as "To Be Scheduled"
- The Schedule tab can't show which technician is en route vs. on site — appointments just stay "Confirmed"
- After a job is completed, the appointment still appears as "Confirmed" unless someone manually updates it

### Recommended Fixes

**Fix 1 — "On My Way" should transition the appointment to EN_ROUTE:**
When the technician clicks "On My Way," in addition to logging the timestamp and sending SMS, the appointment status should change from CONFIRMED → EN_ROUTE. This gives the schedule real-time visibility into who's traveling.

**Fix 2 — "Job Started" should transition both statuses:**
- Job: TO_BE_SCHEDULED → IN_PROGRESS (the status exists but is never used)
- Appointment: EN_ROUTE → IN_PROGRESS
This clearly signals that work has begun.

**Fix 3 — "Job Complete" should auto-complete the appointment:**
When the job is marked complete, the associated appointment should also transition to COMPLETED. There's no reason to leave the appointment hanging in a non-terminal state after the job is done.

**Combined flow after fixes:**

```
"On My Way"    → Job: TO_BE_SCHEDULED (no change)
                 Appointment: CONFIRMED → EN_ROUTE
                 SMS sent

"Job Started"  → Job: TO_BE_SCHEDULED → IN_PROGRESS
                 Appointment: EN_ROUTE → IN_PROGRESS

"Job Complete" → Job: IN_PROGRESS → COMPLETED
                 Appointment: IN_PROGRESS → COMPLETED
                 Payment/invoice check
                 Time tracking calculated
```

### Relationship to Item 1 (Job "Scheduled" Status)

This pairs with the "Scheduled" status proposal. Together, the full job status flow would become:

```
TO_BE_SCHEDULED → SCHEDULED → IN_PROGRESS → COMPLETED
     (created)    (appt made)  (Job Started)  (Job Complete)
                                             → CANCELLED (from any non-terminal)
```

Each status clearly answers a different question:
- **To Be Scheduled** — "Does this job have a date on the calendar?" → No
- **Scheduled** — "Is this on the calendar?" → Yes, waiting for the visit
- **In Progress** — "Is someone working on this right now?" → Yes
- **Completed** — "Is this done?" → Yes

### Implementation Scope

**Backend:**
- Modify `POST /api/v1/jobs/{id}/on-my-way` to also transition the appointment to EN_ROUTE
- Modify `POST /api/v1/jobs/{id}/started` to transition job to IN_PROGRESS and appointment to IN_PROGRESS
- Modify `POST /api/v1/jobs/{id}/complete` to also transition the appointment to COMPLETED
- Update `VALID_JOB_TRANSITIONS` to include: `SCHEDULED → {IN_PROGRESS, CANCELLED}` (if combined with Item 1)
- Handle edge cases: what if "On My Way" is clicked but appointment is still SCHEDULED (not yet confirmed)? Suggested: allow EN_ROUTE from both CONFIRMED and SCHEDULED.

**Frontend:**
- No UI changes needed — the buttons already exist. The status changes happen on the backend.
- The Jobs tab and Schedule tab will naturally show the updated statuses in their existing badge/filter UI.

**Tests:**
- Test the full progression: On My Way → Job Started → Job Complete and verify both job and appointment statuses at each step
- Test edge cases: clicking Job Complete directly (skipping On My Way/Job Started)

### Effort Estimate

Small. The endpoints already exist. The change is adding status transition calls alongside the existing timestamp logging. The appointment transition logic is already implemented in `AppointmentService.transition_status()`.

### Priority

**High.** This is directly related to Item 1 and should be implemented together. The on-site buttons should actually do what their names imply — progress the status through the visit lifecycle.

---

## 3. Email Provider Integration — Invoice and Estimate Sending

### The Gap

The "Send Invoice" action (`POST /api/v1/invoices/{id}/send`) currently **only changes the invoice status in the database** from DRAFT to SENT. No email is actually sent to the customer.

The `EmailService._send_email()` method in `src/grins_platform/services/email_service.py` has a comment at line ~186: `# Production: call email provider API here.` It logs the send as completed but doesn't call any external service.

This affects:
- Sending invoices to customers by email
- Sending estimates to customers by email (outside of the SignWell signing flow)
- Any other email-based communication

### What's Needed

1. **Choose an email provider** — AWS SES, SendGrid, or Postmark are the standard options. SES is cheapest if you're already on AWS. SendGrid has the easiest setup.
2. **Implement `_send_email()` in `email_service.py`** — Replace the placeholder with actual API calls to the chosen provider
3. **Set `EMAIL_API_KEY` environment variable** — Provider credentials
4. **Configure sender domain** — DNS records (SPF, DKIM, DMARC) for deliverability
5. **Template system** — The invoice PDF generation (WeasyPrint) already works. The email just needs to attach the PDF and include a payment link.

### What Already Works

- Invoice PDF generation via WeasyPrint — fully functional
- Invoice record creation with invoice numbers, line items, amounts, due dates
- S3 storage for generated PDFs (conditional on S3 config)
- Email service structure and template rendering — everything except the actual send

### Priority

**High.** Without email sending, invoices can be generated but not delivered to customers electronically. This is a core business operation.

---

## 4. SignWell E-Signature — API Key Provisioning

### The Gap

The SignWell integration is **fully implemented in code** — real httpx calls, webhook verification, embedded iframe signing, PDF retrieval. But it requires two environment variables to be set:

- `SIGNWELL_API_KEY` — for authenticating API calls
- `SIGNWELL_WEBHOOK_SECRET` — for verifying inbound webhook signatures

Without these, the "Send Estimate for Signature (Email)" and "Sign On-Site" buttons in the Sales pipeline will fail.

### What's Needed

1. **Create a SignWell account** at signwell.com (PAYG pricing — pay per document)
2. **Get the API key** from the SignWell dashboard
3. **Configure the webhook** — point it to `https://<your-domain>/api/v1/webhooks/signwell` and get the webhook secret
4. **Set environment variables** in the deployment environment:
   ```
   SIGNWELL_API_KEY=<your-key>
   SIGNWELL_WEBHOOK_SECRET=<your-secret>
   ```
5. **Test the full flow** — upload a PDF estimate, send for email signature, verify the webhook fires and the signed PDF is stored

### What Already Works

- `SignWellClient` service with all 5 API methods (create for email, create for embedded, get URL, fetch PDF, verify signature)
- Webhook endpoint with HMAC-SHA256 verification
- Signed PDF storage as `CustomerDocument` with type `signed_contract`
- Automatic status advancement (Pending Approval → Send Contract) on signature
- Frontend embedded signing iframe with postMessage event handling
- Comprehensive test coverage

### Priority

**High.** The entire Sales pipeline estimate-to-contract flow depends on this. Without it, you can't send estimates for signature or use the on-site signing feature.

---

## 5. Google Review Push SMS — Bug Fix

### The Gap

The "Google Review" button on the job detail view **appears to work but doesn't actually send an SMS**. The function `appointment_service.request_google_review()` checks consent and deduplication (30-day window) but never calls `sms_service.send_message()`. It returns `sent=True` without sending anything.

This is a bug, not a design choice — the function has all the scaffolding but the actual send call is missing.

### What's Needed

1. **Add the `sms_service.send_message()` call** inside `request_google_review()` in `src/grins_platform/services/appointment_service.py` (around line ~670-710)
2. **Configure the Google review deep link URL** — the SMS template needs the actual Google Business Profile review link
3. **Message type:** `MessageType.GOOGLE_REVIEW_REQUEST` (already exists in the enum)
4. **Test** the full flow: click button → SMS sent → customer receives link

### Priority

**Medium.** Nice-to-have for collecting reviews, but not blocking core operations.

---

## 6. Reschedule Follow-Up SMS

### The Gap

When a customer replies "R" (reschedule) to a confirmation SMS:
- A `reschedule_request` record is created in the database
- The request appears in the admin Reschedule Requests queue
- An auto-reply is sent acknowledging the request

**But:** The spec (Requirement 24.3) says the system should "send a follow-up SMS asking for 2-5 alternative date/time options." This follow-up SMS is not sent. The customer replies "R" and gets a generic acknowledgment, but is never asked for their preferred alternative times.

### What's Needed

1. **Add a follow-up SMS** in `JobConfirmationService._handle_reschedule()` after creating the reschedule request
2. **SMS content:** Something like "We'd be happy to reschedule. Please reply with 2-3 dates and times that work for you and we'll get you set up."
3. **Parse the reply** — the customer's follow-up response with alternative times should be captured in the `requested_alternatives` field on the reschedule request (this field exists in the model but won't be populated without the follow-up prompt)

### What Already Works

- Reschedule request creation and admin queue
- The "R" keyword detection and routing
- The `requested_alternatives` JSONB field on the model
- The admin "Reschedule to Alternative" action in the queue UI

### Priority

**Medium.** The reschedule flow works in a basic sense (request is captured, admin can see it), but the customer experience is incomplete without the follow-up asking for their preferences.

---

## 7. Cancellation Confirmation SMS

### The Gap

When a customer replies "C" (cancel):
- The appointment is cancelled
- An auto-reply is sent
- The admin is notified

The auto-reply is generic. There's no explicit cancellation confirmation SMS with details (e.g., "Your appointment for [service] on [date] has been cancelled. If you'd like to reschedule, please call us at [number].").

### What's Needed

1. **Improve the cancellation auto-reply** in the confirmation handler to include appointment details and a callback number
2. Minor change — just a template update in the SMS send call

### Priority

**Low.** The basic flow works. This is a customer experience polish item.

---

## 8. Sales Pipeline: Connect Estimate Calendar to Pipeline Status

### The Problem

The Sales pipeline status advancement and the Estimate Calendar are completely disconnected. They're two independent manual operations:

- Clicking the action button on "Schedule Estimate" → just flips the status text to "Estimate Scheduled." Nothing else happens — no calendar opens, no appointment is prompted.
- Creating an event on the Estimate Calendar → just puts a date on the calendar. Doesn't touch the sales entry status.

This means you can:
- Advance to "Estimate Scheduled" without ever actually scheduling an appointment (the status is a lie)
- Create a calendar appointment for an entry that still says "Schedule Estimate" (the calendar and status are out of sync)
- Forget to do one or the other because they're separate clicks in separate places

Every step in the pipeline is a separate manual action with zero automation connecting them.

### Current Flow (What Happens Today)

```
1. Sales entry at "Schedule Estimate"
2. Manually click action button → status changes to "Estimate Scheduled" (nothing else)
3. Separately navigate to Estimate Calendar tab
4. Separately create a calendar event, selecting this sales entry from a dropdown
5. Go do the estimate visit
6. Come back, manually click action button → "Send Estimate"
7. Upload and send the estimate document
8. ...continue through pipeline
```

### Recommended Change

**Make the calendar event and the status advancement a single action.**

**Recommendation A — Clicking "Schedule Estimate" opens the calendar event form:**
Instead of just flipping the status, the action button should open a dialog or navigate to the calendar with a pre-filled event creation form for this sales entry. When you save the event, the status automatically advances to "Estimate Scheduled." This makes the action button do what its label actually says — schedule the estimate.

**Recommendation B — Creating a calendar event auto-advances the status:**
If a calendar event is created for a sales entry that's still in "Schedule Estimate," the status automatically advances to "Estimate Scheduled." This way, if someone goes to the calendar first (instead of clicking the action button), the pipeline still stays in sync.

**Ideally, implement both.** They cover the two ways a user might approach the task — either starting from the pipeline list or starting from the calendar.

**What should stay manual:**
- **"Estimate Scheduled" → "Send Estimate"** — This should remain a manual click. Just because the appointment date has passed doesn't mean the estimate is ready to send. The admin needs to prepare the estimate document, upload it, and then advance. Automating this based on date would be unreliable (appointments get rescheduled, cancelled, etc.).
- **Everything after "Send Estimate"** — The signing flow (Pending Approval → Send Contract) is already partially automated via SignWell webhooks. The rest are intentional human decision points.

### Optional Enhancement: Estimate Visit Confirmation SMS

The Jobs schedule has Y/R/C SMS confirmation for appointments. The estimate calendar currently has no customer communication. Consider adding a lighter version:

- When an estimate appointment is created, send an SMS: "We have your estimate visit scheduled for [date] at [time]. Reply Y to confirm or R to request a different time."
- This is not critical — estimate visits are typically shorter-notice and more informal than job appointments — but it would improve the customer experience and reduce no-shows.
- If implemented, this should use the same `SMSService` infrastructure and follow the same Y/R/C pattern.

This is a nice-to-have, not a blocker.

### Implementation Scope

**Backend:**
- Modify `SalesPipelineService.advance_status()` or the sales calendar event creation endpoint to auto-advance status when a calendar event is created for a "Schedule Estimate" entry
- Add a check in the calendar event creation: if the linked sales entry is at "schedule_estimate," advance it to "estimate_scheduled"

**Frontend:**
- Modify `StatusActionButton.tsx`: when the current status is "schedule_estimate," instead of calling `advance()` directly, open the calendar event creation dialog pre-filled with the sales entry's customer and details
- On successful event creation, the backend handles the status advance
- Alternatively, navigate to the Estimate Calendar tab with a query param that triggers the event creation form

**Tests:**
- Test: creating calendar event for "schedule_estimate" entry → status auto-advances
- Test: creating calendar event for an entry already at "estimate_scheduled" → no double-advance
- Test: action button opens calendar form instead of just advancing

### Effort Estimate

Small-medium. The main work is in the frontend — changing the action button behavior from a simple API call to opening a form. The backend auto-advance is a few lines added to the calendar event creation endpoint.

### Priority

**Medium-high.** This is a workflow quality issue. The current disconnected flow is usable but error-prone — statuses can get out of sync with reality.

---

## 9. Sales Pipeline: Wire Signing to Uploaded Documents

### The Problem

When you click "Send Estimate for Signature (Email)" or "Sign On-Site" on a sales entry, the signing endpoint sends a **hardcoded placeholder URL** (`/api/v1/sales/{entry_id}/contract.pdf`) to SignWell — not an actual uploaded document from the Documents section.

This means the Documents section and the signing flow are disconnected:
- You can upload estimate PDFs, contracts, photos, and reference docs to the Documents section — that works
- But when you trigger the signing action, it doesn't pull from those uploaded documents
- There's no way to designate which uploaded document is "the estimate to be signed"

### Current Workaround

Right now the flow works at a storage level — you upload documents for record-keeping and can download/preview them. But the e-signature sending is not connected to a specific uploaded file. This needs to be wired up before the SignWell signing flow is production-ready.

### What's Needed

1. **Add a "document to sign" selection** — when the user clicks "Send for Signature," either:
   - Prompt them to select which uploaded document to send, or
   - Add a `document_type` filter so the system automatically picks the document tagged as `estimate` or `contract`
2. **Pass the real document to SignWell** — replace the hardcoded `/api/v1/sales/{entry_id}/contract.pdf` URL in `src/grins_platform/api/v1/sales_pipeline.py` (lines ~241 and ~282) with the actual S3 presigned URL or file content of the selected document
3. **Validate a document exists before signing** — disable the signing buttons if no estimate/contract document has been uploaded yet, with a tooltip like "Upload an estimate document first"

### What Already Works

- Documents section — upload, download, preview, delete all functional
- SignWell client — all API methods implemented and tested
- SignWell webhook — receives signed PDF, stores it as a `signed_contract` document, advances status
- The only missing piece is the connection between "uploaded document" and "document sent to SignWell"

### Priority

**High.** This is a dependency for the SignWell signing flow. Even after API keys are provisioned (Item 3), the signing won't work correctly without this wiring.

---

## 10. Twilio SMS Provider — Stub Implementation (Not Needed Now)

### The Gap

The Twilio provider at `src/grins_platform/services/sms/twilio_provider.py` is a **stub**:
- Generates fake message SIDs (`SM{timestamp}`)
- Never makes real API calls
- `verify_webhook_signature()` always returns `False`
- Comment: "stub ported from SMSService._send_via_twilio()"

The CallRail provider is fully functional and is the active provider.

### What's Needed (Only If Switching to Twilio)

1. **Install the Twilio SDK** or use httpx to call the Twilio REST API
2. **Implement `send_text()`** with real Twilio API calls
3. **Implement `verify_webhook_signature()`** using Twilio's request validation
4. **Implement `parse_inbound_webhook()`** to convert Twilio's webhook payload to the `InboundSMS` dataclass
5. **Set environment variables:** `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER`

### Priority

**Not needed unless switching from CallRail.** CallRail is fully functional. Only implement if there's a business reason to change providers.

---

## 11. S3 Configuration for Production

### The Gap

Both `InvoicePDFService` and `PhotoService` use a graceful degradation pattern — if S3 credentials aren't configured, they generate placeholder URLs instead of actually uploading files. This works for local development but means files aren't actually stored in production without proper config.

### What's Needed

1. **Create an S3 bucket** (or verify the existing `grins-platform-files` bucket exists)
2. **Set environment variables:**
   ```
   S3_BUCKET_NAME=grins-platform-files
   S3_REGION=us-east-1
   AWS_ACCESS_KEY_ID=<key>
   AWS_SECRET_ACCESS_KEY=<secret>
   ```
3. **Configure CORS on the bucket** if documents need to be previewed in-browser
4. **Set a lifecycle policy** for old files if storage costs are a concern

### What Already Works

- Upload/download logic in `PhotoService` — fully implemented with `boto3`
- Invoice PDF generation and S3 upload path in `InvoicePDFService`
- Customer document upload/download/delete endpoints
- Presigned URL generation for secure downloads (1-hour expiry)

### Priority

**High for production deployment.** Without S3, uploaded photos, documents, and generated invoice PDFs aren't actually persisted.

---

## 12. Enforce "No Unestimated Jobs in the Jobs Tab" Rule

### The Problem

The source doc is explicit: *"Jobs: Should be all the jobs that are approved and need to be scheduled, should not have any jobs here that need to be estimated."*

But the system doesn't enforce this. There are **three ways** an unestimated job can end up in the Jobs tab:

**Path 1 — "New Job" button on the Jobs tab:**
There's a direct job creation button on the Jobs tab (`POST /api/v1/jobs`). Anyone can click it and create a job regardless of whether the work has been estimated. The system auto-categorizes the job as `REQUIRES_ESTIMATE` based on the job type, but creates it in the Jobs tab anyway. The category is just a label — it doesn't prevent the job from appearing or being scheduled.

**Path 2 — "Move to Jobs" from the Leads tab:**
When you click "Move to Jobs" on a lead, the system maps the lead's situation to a job type. Most lead situations (new system installs, upgrades, consultations) map to `requires_estimate`. So the system *knows* it needs an estimate, but creates the job in the Jobs tab without any warning. There's no prompt saying "this lead needs an estimate — did you mean Move to Sales?"

**Path 3 — Unauthenticated job creation endpoint:**
`POST /api/v1/jobs` has **no authentication requirement**. This is also a security concern — anyone who knows the endpoint can create job records.

### Real-World Impact

This has already caused confusion — unestimated jobs are appearing in the Jobs tab alongside approved work, making it unclear which jobs are ready to schedule and which still need estimates. Example: Job #45457895 for JEMI RAK is in the Jobs tab but needs an estimate.

### Recommended Fixes

**Fix 1 — Add a guard to "Move to Jobs" (High priority):**
When a lead's situation maps to `requires_estimate`, the "Move to Jobs" button should either:
- **Block the action** with a message: "This lead needs an estimate. Use 'Move to Sales' instead."
- Or **show a warning modal** letting the admin confirm: "This job type typically requires an estimate. Move to Jobs anyway, or move to Sales for the estimate workflow?"

The second option is more flexible — there may be cases where the customer already has a quote from a previous visit and just needs scheduling.

**Fix 2 — Gate or remove direct job creation (Medium priority):**
Options:
- **Remove the "New Job" button** from the Jobs tab entirely. Jobs should only enter through the defined paths (Leads → Jobs, Sales → Convert to Job, Onboarding, Renewals).
- Or **add estimate validation**: if the job type would be categorized as `REQUIRES_ESTIMATE` and no `quoted_amount` is provided, block creation and direct the user to the Sales tab.
- Or **add a confirmation warning**: "This job type typically requires an estimate. Create it anyway?" with an audit log if they proceed.

**Fix 3 — Add authentication to POST /api/v1/jobs (High priority):**
This endpoint is currently public — no `CurrentActiveUser` dependency. Add the same auth guard used on every other endpoint. This is a straightforward security fix regardless of the estimate enforcement question.

**Fix 4 — Surface REQUIRES_ESTIMATE jobs visually (Quick win):**
If unestimated jobs do end up in the Jobs tab (via override or edge cases), make them visually distinct:
- Add an "Estimate Needed" badge/tag (similar to PropertyTags) on jobs where `category = REQUIRES_ESTIMATE`
- Color the row differently (e.g., amber background) so they stand out
- Add a filter option so admins can filter the Jobs list to see only `REQUIRES_ESTIMATE` jobs and clean them up

### Implementation Scope

**Fix 1 (Move to Jobs guard):**
- Backend: Add a response field or warning flag to `POST /api/v1/leads/{id}/move-to-jobs` when the job type maps to `requires_estimate`
- Frontend: Show a confirmation modal in the Leads tab when the backend returns the warning
- Effort: Small

**Fix 2 (Direct creation gate):**
- Backend: Add validation to `POST /api/v1/jobs` that checks the auto-categorization result and blocks/warns if `REQUIRES_ESTIMATE`
- Frontend: Remove the "New Job" button or add the confirmation modal
- Effort: Small

**Fix 3 (Auth fix):**
- Backend: Add `_user: CurrentActiveUser` dependency to the `POST /api/v1/jobs` endpoint
- Effort: Trivial (one line)

**Fix 4 (Visual distinction):**
- Frontend: Add an "Estimate Needed" badge to `JobList.tsx` when `category === "requires_estimate"`
- Effort: Small

### Priority

**High.** This violates a core workflow rule from the source doc and is actively causing confusion with real data. Fix 3 (auth) is a security issue that should be done immediately. Fix 1 (Move to Jobs guard) prevents the most common path for the problem. Fix 4 (visual distinction) is a quick safety net.

---

## 13. Mobile-Friendly On-Site Job View

### The Problem

The on-site job workflow — On My Way, Job Started, Job Complete, Add Photos, Add Notes, Create Invoice, Google Review Push — is primarily used **in the field on a phone**. You're at the customer's property, pulling out your phone to tap through the job steps. But the current frontend was built desktop-first and hasn't been optimized for mobile viewports.

On a phone screen:
- Buttons may be too small or too close together to tap reliably
- The job detail layout may require excessive scrolling to reach the action buttons
- Photo upload from the phone camera should be seamless (tap, take photo, auto-upload)
- The status progression buttons (On My Way → Job Started → Job Complete) should be the most prominent elements, not buried below other content
- The payment warning modal needs to be readable and dismissable on a small screen

### What Should Be Mobile-Friendly

The **job detail view** when accessed from a phone needs a mobile-optimized layout. Specifically:

**Primary actions (must be immediately accessible, no scrolling):**
- **On My Way** button — large, easy to tap
- **Job Started** button — large, easy to tap
- **Job Complete** button — large, easy to tap, with the payment warning modal working cleanly on mobile

**Secondary actions (accessible with minimal scrolling):**
- **Add Photo** — should open the phone's camera directly (not just a file picker). Tap → camera opens → take photo → auto-uploads
- **Add Notes** — text input that works well with the mobile keyboard
- **Create Invoice** — form should be usable on a small screen
- **Google Review Push** — simple tap to send
- **Collect Payment** — payment form usable on mobile

**Information display:**
- Customer name, address, and phone number visible at the top (tap-to-call on the phone number)
- Property tags (Residential/Commercial, HOA, Subscription) visible without scrolling
- Service preference notes visible as a hint
- Job type and Week Of visible

### Recommended Approach

**Option A — Responsive CSS for the existing job detail view:**
Add media queries and responsive layout adjustments so the job detail page works well at mobile viewport widths (< 768px). This is the minimum viable approach.

Key changes:
- Stack the status buttons vertically and make them full-width on mobile
- Move the status buttons to the top of the page (above job details) on mobile so they're immediately accessible
- Make the photo upload button trigger the device camera via `capture="environment"` on the file input
- Ensure the payment warning modal is properly sized for mobile
- Make the customer phone number a `tel:` link for tap-to-call

**Option B — Dedicated mobile field view:**
Create a simplified `/jobs/{id}/field` view stripped down to just the on-site workflow. Desktop users see the full detail page; mobile users (detected by viewport or user agent) get redirected to the field view. This is more work but gives a cleaner mobile experience.

Key elements of the field view:
- Large status buttons at the top (the primary UI)
- Quick-action icons below: camera, notes, invoice, review
- Minimal information display — just what's needed in the field
- No filters, tables, or admin-heavy UI

**Recommendation:** Start with **Option A** (responsive CSS). It's lower effort and doesn't require maintaining a separate view. If the mobile experience still isn't good enough after responsive adjustments, then build the dedicated field view (Option B) as a follow-up.

### Implementation Scope

**Option A (Responsive CSS):**
- Frontend: Add responsive breakpoints to `JobDetail.tsx` and `OnSiteOperations.tsx`
- CSS: Media queries for status buttons, action buttons, photo upload, modal sizing
- HTML: Add `capture="environment"` to photo input, `tel:` links for phone numbers
- Testing: Test on actual phone (iPhone Safari, Android Chrome) — not just browser DevTools resize
- Effort: Small-medium

**Option B (Dedicated field view):**
- Frontend: New `JobFieldView.tsx` component with simplified mobile-first layout
- Router: Add `/jobs/{id}/field` route
- Effort: Medium

### Priority

**Medium-high.** This directly affects the day-to-day field workflow. Every job site visit involves tapping through these buttons on a phone. A clunky mobile experience slows down every technician on every job.

---

## 14. Onboarding: Consolidate Week Selection and Fix Tier Mapping

### The Problem

The onboarding flow currently has **two separate timing preference systems**, and the per-service week selection is not fully wired up. This creates confusion for the customer and potential data issues.

**Issue 1 — Two places asking about timing:**

The onboarding form collects:
- `preferred_schedule` — a general preference: ASAP, 1-2 Weeks, 3-4 Weeks, or Other. This is displayed in the agreement detail view.
- `service_week_preferences` — a per-service JSON mapping each service type to a specific week (e.g., Spring Startup = Week of 4/6, Fall Winterization = Week of 10/5).

The relationship between these two is undefined. If a customer selects "ASAP" AND picks specific weeks per service, which one wins? There should be **one place** to select timing preferences, not two competing systems.

**Issue 2 — Per-service week picker not fully integrated:**

There are two week picker components that both partially exist:
- `WeekPickerStep.tsx` in the platform frontend (`frontend/src/features/portal/components/`) — a polished component with calendar popovers restricted to valid month ranges per service type. **But it's orphaned — exported but never imported or used anywhere.**
- `ServiceWeekPreferences.tsx` in the Grins_irrigation landing page — uses select dropdowns for week selection. This component exists in the onboarding flow.

The result is that the customer may see an incomplete or inconsistent week selection experience.

**Issue 3 — Tier-to-service mapping must be correct:**

Each tier includes different services, and the week picker should only show options for the services in the customer's selected tier:

| Tier | Services | Week Pickers Shown |
|------|----------|--------------------|
| **Essential** | Spring Startup, Fall Winterization | 2 |
| **Professional** | Spring Startup, Mid-Season Inspection, Fall Winterization | 3 |
| **Premium** | Spring Startup, Monthly Visit (May-Sep), Fall Winterization | 7 |

Each service has a valid month range for week selection:
- Spring Startup: March–May
- Mid-Season Inspection: June–August
- Fall Winterization: September–November
- Monthly Visits: restricted to their specific month

The week picker must only show services that match the customer's selected tier, and each picker must be restricted to the correct month range. No service should appear twice, and no extra pickers should show for a lower tier.

### Recommended Fix

**Consolidate into a single, per-service week selection:**

1. **Remove the general `preferred_schedule` field** (ASAP / 1-2 Weeks / etc.) from the onboarding form — or repurpose it as a fallback only shown if the customer skips the week selection step. The per-service week picker is more specific and more useful for job generation.

2. **Wire up `WeekPickerStep.tsx`** (or consolidate with `ServiceWeekPreferences.tsx`) as the single week selection step in the onboarding flow. Only one component should exist for this — pick the better one and remove the other.

3. **Ensure tier-correct service lists:** The week selection step must dynamically show only the services included in the customer's selected tier. The backend already returns `services_with_types` from the `verify-session` endpoint — use this to drive which pickers appear.

4. **Validate month ranges per service:** Each week picker should be restricted to the valid months for that service type. The `WeekPickerStep` component already has this logic — make sure the active component uses it.

5. **Handle the "no preference" case:** If the customer doesn't want to pick specific weeks, provide a "No preference" or "Assign for me" option that leaves `service_week_preferences` as null. The job generator already falls back to default calendar-month ranges when preferences are null.

### Implementation Scope

- **Grins_irrigation repo (landing page):** Consolidate the week selection UI — ensure only one component handles it, fed by the correct tier services list
- **Platform frontend:** Decide whether `WeekPickerStep.tsx` replaces `ServiceWeekPreferences.tsx` or vice versa, then remove the unused one
- **Backend:** Potentially deprecate `preferred_schedule` or make it secondary to `service_week_preferences`
- **Testing:** Test each tier (Essential, Professional, Premium) to verify the correct number of week pickers appear with the correct month ranges
- Effort: Medium

### Priority

**Medium.** The onboarding flow works end-to-end (customer can purchase, jobs are generated), but the duplicate preference collection creates confusion and the week picker may not correctly reflect the customer's tier.

---

## 15. Schedule Tab: Improve the Job Selector When Scheduling Appointments

### The Problem

When you click "Schedule an Appointment" on the Schedule tab, the job selector dropdown is hard to use. It shows job records but **doesn't include the customer name**, so you're looking at a list of job types and IDs with no easy way to tell whose job is whose. If you have 20 jobs in "To Be Scheduled" status, you're guessing or cross-referencing back to the Jobs tab to figure out which one to pick.

This makes what should be a quick action — pick a job, assign a date/time/staff — into a multi-step lookup process.

### What's Wrong with the Current Selector

- **No customer name displayed** — the most important piece of context for identifying a job is missing from the selector
- **Too many clicks / too much friction** — scheduling a job should be fast. Right now, you have to remember (or look up) which job belongs to which customer before you can select it from the dropdown
- **No search or filtering** — if the list is long, there's no way to type a customer name or address to narrow it down
- **Minimal job context** — beyond the job type, there's little information to help you distinguish between similar jobs (e.g., two "Spring Startup" jobs for different customers)

### Recommended Improvements

**Improvement 1 — Show customer name in the job selector (Must-have):**
Each option in the job selector dropdown should display the **customer name** prominently, alongside the job type. Format suggestion:
```
John Smith — Spring Startup (Week of 4/6)
Jane Doe — Fall Winterization (Week of 10/5)
ABC Commercial — Backflow Test (Week of 5/1)
```
The customer name should come first since that's what you're scanning for when picking a job to schedule.

**Improvement 2 — Add search/filter to the selector:**
Replace the plain dropdown with a searchable select (combobox). As you type, it filters the list by customer name, job type, or address. This is critical once you have more than ~10 jobs in the queue — scrolling through a flat list doesn't scale.

**Improvement 3 — Show additional context in each option:**
Beyond customer name and job type, consider showing:
- Customer address (or at least city/area) — helpful for route-based scheduling
- Property tags (Residential/Commercial, HOA) — affects scheduling decisions
- Service preference notes — "AM only," "call before arriving," etc.
- Week Of — so you can see when the customer expects the job

**Improvement 4 — Group or sort jobs intelligently:**
Instead of a flat list, group jobs by:
- **Area/zip code** — makes it easy to schedule geographically close jobs on the same day
- **Week Of** — shows which jobs are due soonest
- **Job type** — batch similar work together (all Spring Startups, then all Winterizations, etc.)

Allow sorting by any of these dimensions so the scheduler can organize the list in the way that matches how they're building the day's route.

**Improvement 5 — Quick-schedule from the Jobs tab:**
Add a "Schedule" action button directly on jobs in the Jobs tab (for jobs in "To Be Scheduled" status). Clicking it opens the appointment creation form pre-filled with that job's details — customer, job type, address. This avoids the selector entirely for the common flow of "I'm looking at a job and I want to put it on the calendar."

This is the inverse of the current flow — instead of going to the Schedule tab and hunting for a job, you go to the job and say "schedule this one." Both paths should exist.

### Implementation Scope

**Backend:**
- Ensure the jobs list endpoint used by the scheduler returns customer name, address, property tags, and service preferences along with the job data (may already be included via joins — verify)
- If not, add `customer_name`, `customer_address`, and relevant property info to the job list serializer used by the appointment creation form

**Frontend:**
- Replace the plain job selector dropdown with a searchable combobox component (e.g., using a `Combobox` from your UI library or a `react-select`-style component)
- Update the option rendering to show customer name + job type + additional context
- Add grouping/sorting options to the selector
- Optionally add a "Schedule" quick-action button to `JobList.tsx` for "To Be Scheduled" jobs
- Wire the quick-schedule button to open the appointment form pre-filled with the job's data

**Tests:**
- Test: job selector displays customer name for each job
- Test: search/filter narrows results by customer name
- Test: quick-schedule from Jobs tab opens pre-filled appointment form

### Effort Estimate

Small-medium. The main work is the frontend selector component upgrade and wiring in the additional job data. The backend likely already returns most of the needed data — just needs to be surfaced in the selector UI.

### Priority

**Medium-high.** This is a daily-use workflow friction point. Every time someone builds the schedule, they interact with this selector. Making it faster and more informative directly speeds up the scheduling process.

---

## 16. Job Cancellation: Clear On-Site Operations Data from the Database

### The Problem

When you cancel or delete a job and then recreate it (or create a new appointment for the same job), the old on-site operations data **persists in the database** and shows up on the new job. For example:

1. Schedule a job, click "On My Way" (timestamps `on_my_way_at`)
2. Cancel the job
3. Recreate the job or create a new appointment
4. The system still shows the old "On My Way" timestamp as if it already happened

The cancellation only updates the UI state (appointment status → CANCELLED) but doesn't clean up the on-site operation timestamps and related data stored on the job or appointment record. This means stale data from a previous attempt carries over, making it look like field operations already happened when they haven't.

### What Should Be Cleared on Cancellation

When a job is cancelled, the following fields should be **reset to null** in the database:

- `on_my_way_at` — the "On My Way" timestamp
- `started_at` — the "Job Started" timestamp
- `completed_at` — the "Job Complete" timestamp
- Any associated "On My Way" SMS send records for that appointment (so the system doesn't think the customer was already notified)
- Payment/invoice warning override flags (if the job was previously completed with a "Complete Anyway" override, that flag shouldn't carry over)

When an **appointment** is cancelled (but the job itself still exists for rescheduling):

- The appointment's on-site timestamps should be cleared on that appointment record
- If a new appointment is created for the same job, it should start clean with no inherited timestamps
- The job-level timestamps should also be cleared if they were set from the now-cancelled appointment

### Why This Matters

This isn't just a cosmetic issue — it causes real confusion:
- The admin sees "On My Way" already recorded and thinks the tech is en route when they haven't left yet
- Time tracking calculations (travel time, work time) will be wrong because they're using stale timestamps from a cancelled visit
- The payment/invoice warning on "Job Complete" might not fire correctly if the system thinks a previous payment interaction already happened

### Recommended Fix

**Option A — Clear timestamps on cancellation (Recommended):**
When a job or appointment is cancelled, explicitly set all on-site operation fields back to null in the database. This is the cleanest approach — a cancelled job should have no record of field activity.

**Option B — Scope timestamps to the appointment, not the job:**
If on-site timestamps are stored on the appointment record (not the job record), then cancelling the appointment naturally orphans the old data. A new appointment starts clean. This is a slightly larger refactor but prevents the problem structurally.

### Implementation Scope

**Backend:**
- In the job cancellation endpoint/service: add a step that nullifies `on_my_way_at`, `started_at`, `completed_at`, and any related flags
- In the appointment cancellation handler (both admin-initiated and SMS "C" reply): clear on-site timestamps on the appointment record
- If timestamps live on the job record: also clear them when the associated appointment is cancelled
- Ensure the "On My Way" SMS log doesn't prevent a new "On My Way" SMS from being sent for the replacement appointment

**Frontend:**
- No frontend changes needed if the backend properly clears the data — the UI reads from the database, so it will show the correct (empty) state

**Tests:**
- Test: cancel a job that has on_my_way_at set → on_my_way_at is null after cancellation
- Test: cancel an appointment, create a new one for the same job → new appointment has no inherited timestamps
- Test: "On My Way" button works on the new appointment after the old one was cancelled

### Effort Estimate

Small. The fix is adding null-setting logic to the existing cancellation handlers. No new endpoints or UI changes needed.

### Priority

**High.** This is a data integrity bug that causes incorrect state to persist across job attempts. It directly affects the reliability of the on-site workflow and time tracking.

---

## 17. Payment Flow: Differentiate Pre-Paid, Invoice, and On-Site Stripe Payments

### The Problem

The system currently treats all jobs the same when it comes to payment — regardless of whether the customer already paid through a service agreement, whether they'll get an invoice to pay later, or whether they're paying on the spot with a card. This creates confusion at multiple points in the workflow, especially at job completion when the "No Payment or Invoice on File" warning fires even for jobs that are already covered by a subscription.

There are **three distinct payment paths** a job can take, and the system needs to clearly differentiate between them — both in the data model and in the UI.

### The Three Payment Paths

**Path 1 — Pre-Paid via Service Agreement (Subscription Customers)**

These are jobs generated from a service agreement (onboarding purchase or contract renewal). The customer already paid when they purchased their service package through Stripe. There is nothing to collect — the work is covered.

**Current state:** Jobs linked to a service agreement have a `service_agreement_id` field, but that's it. There is no explicit "this job is pre-paid" flag. The job completion check (`POST /api/v1/jobs/{id}/complete`) **does not look at the service agreement** — it only checks `payment_collected_on_site` (a boolean) and whether any invoice records exist. So for a subscription customer's Spring Startup job, the system will still pop the "No Payment or Invoice on File" warning even though they already paid $599 for the full package. The admin has to click "Complete Anyway" every time, which is annoying and trains people to ignore the warning.

**What needs to change:**
- The job completion check should recognize that a job with an active `service_agreement_id` is already paid. Skip the payment warning entirely for these jobs.
- The job detail view should show a clear visual indicator: "Covered by Service Agreement — [Agreement Name]" so the admin never wonders "do I need to invoice this customer?"
- Invoicing should be **disabled or hidden** for agreement-covered jobs — there's nothing to bill.
- The Jobs tab and Schedule tab should visually distinguish pre-paid jobs (e.g., a "Prepaid" or "Agreement" badge alongside the existing "Sub" tag) so you can see at a glance which jobs on today's schedule need payment handling and which don't.

---

**Path 2 — Invoice Sent, Customer Pays Later**

These are one-off jobs (not from a service agreement) where the admin creates an invoice and sends it to the customer. The customer pays after the fact — maybe the same day, maybe a week later. Payment comes in via the payment portal link, a mailed check, Venmo, Zelle, etc.

**Current state:** This path mostly works. An invoice can be created from the job detail view (`POST /api/v1/jobs/{job_id}/invoice`) or from the on-site view (`POST /api/v1/appointments/{id}/create-invoice`). The invoice generates a Stripe payment link so the customer can pay online. Status tracks through `draft → sent → viewed → paid`.

**What needs to change:**
- **Email sending is not implemented** (see Item 3 — Email Provider Integration). The "Send Invoice" action only flips the status in the database. Until the email provider is wired up, invoices can be generated but not delivered electronically. This is already documented but worth noting here because it's the primary delivery mechanism for this payment path.
- The job completion flow should handle this gracefully: if an invoice exists in `sent` status, that's fine — the customer will pay later. The warning should only fire if there's truly no invoice AND no payment.
- Consider adding a "Send Invoice" quick action to the on-site workflow so the admin can generate and email the invoice before leaving the property, while the job details are fresh.

---

**Path 3 — On-Site Stripe Payment (Tap to Pay)**

These are jobs where the customer pays at the property with a card — either tap-to-pay via Stripe Terminal on the admin's phone or a manual card entry. Payment is collected immediately, in person.

**Current state:** The "Collect Payment" action on the on-site view (`PaymentCollector.tsx`) is a **manual form** — the admin selects a payment method (cash, check, venmo, zelle, credit_card), enters the amount and a reference number, and the system records it. For "credit_card," the system just logs the record — **it does not actually process a Stripe charge.** There is no Stripe Terminal integration, no tap-to-pay, no real-time card processing.

**What needs to change to support real Stripe tap-to-pay:**

1. **Stripe Terminal SDK integration** — Add the Stripe Terminal JavaScript SDK to the frontend. This handles the connection between the browser/app and the physical card reader (or the phone's built-in tap-to-pay via Stripe's mobile reader).

2. **Backend: create a PaymentIntent** — When the admin clicks "Collect Payment" and chooses card/tap-to-pay, the backend needs to create a Stripe `PaymentIntent` for the invoice amount. This is the standard Stripe flow for in-person payments.

3. **Connect to a Stripe Terminal reader** — Options:
   - **Stripe Tap to Pay on iPhone** — uses the phone's NFC chip as a card reader. No additional hardware needed. Requires Stripe Terminal SDK with `tap_to_pay` as the discovery method.
   - **Stripe Reader M2 or S700** — dedicated Bluetooth card reader that pairs with the phone. More reliable for high-volume use.
   - Either way, the frontend needs a reader discovery and connection flow.

4. **Process the payment in real time** — Once the card is tapped/inserted, the Stripe Terminal SDK handles the charge, returns a confirmed `PaymentIntent`, and the backend records the payment on the invoice as `PAID` with `payment_method: stripe_terminal`.

5. **Update the "Collect Payment" UI** — The current form should be split into:
   - **"Pay with Card (Tap to Pay)"** — triggers the Stripe Terminal flow. The admin taps "Pay," the customer taps their card, done.
   - **"Record Other Payment"** — the existing manual form for cash, check, Venmo, Zelle. This is still needed for non-card payments.

6. **Stripe Terminal Location** — Stripe Terminal requires a "Location" resource for the reader. This should be configured once (the business address) and stored as an env var or in the database.

7. **Receipts** — After a successful tap-to-pay charge, the system should offer to send an SMS or email receipt. Stripe can generate receipts automatically, or the system can use the existing invoice PDF.

### How the Job Completion Check Should Work (All Three Paths)

The current check is too simplistic. It should account for all three payment paths:

```
When "Job Complete" is clicked:

1. Does this job have an active service_agreement_id?
   → YES: Job is pre-paid. No warning. Complete immediately.

2. Has payment been collected on-site (cash, check, Stripe tap-to-pay)?
   → YES: Payment is recorded. No warning. Complete immediately.

3. Does an invoice exist for this job?
   → YES (status: paid): No warning. Complete.
   → YES (status: sent/draft): Invoice exists but unpaid.
      No warning — customer will pay later. Complete.
   → NO: No payment and no invoice.
      Show warning: "No Payment or Invoice on File"
      Options: "Create Invoice" / "Collect Payment" / "Complete Anyway"
```

This eliminates the false warning for subscription jobs and gives the admin clear options when payment truly hasn't been handled.

### How the UI Should Differentiate the Three Paths

**On the job detail / on-site view, the payment section should show:**

| Job Type | What the Admin Sees |
|----------|-------------------|
| **Service agreement job** | "Covered by [Agreement Name] — no payment needed" with a green checkmark. No invoice or payment buttons shown. |
| **One-off job, no invoice yet** | "Create Invoice" and "Collect Payment" buttons both available. |
| **One-off job, invoice sent** | "Invoice #1234 — Sent on 4/10, $350.00" with status badge. "Collect Payment" still available if customer wants to pay on-site instead. |
| **One-off job, paid on-site** | "Payment collected — $350.00 via Stripe Tap-to-Pay" with green checkmark. |

**On the Schedule tab calendar view:**
- Pre-paid jobs should have a visual indicator (badge or icon) so when you're looking at the day's appointments, you immediately know which ones need payment collection and which don't.

### Implementation Scope

**Phase A — Fix the completion check for service agreement jobs (Quick win):**
- Backend: Modify the job completion check to skip the payment warning when `service_agreement_id` is present and the agreement is active
- Frontend: Show "Covered by Service Agreement" on the job detail view for agreement-linked jobs
- Hide/disable the invoice and payment buttons for these jobs
- Effort: Small

**Phase B — Stripe Tap-to-Pay integration (New feature):**
- Backend: Stripe Terminal connection token endpoint, PaymentIntent creation endpoint, payment confirmation webhook
- Frontend: Stripe Terminal SDK setup, reader discovery, tap-to-pay flow in `PaymentCollector.tsx`
- Stripe Dashboard: Create a Terminal Location, order/register readers (or enable Tap to Pay on iPhone)
- Environment variables: `STRIPE_TERMINAL_LOCATION_ID`
- Testing: End-to-end test with a real or simulated reader in Stripe test mode
- Effort: Medium-large

**Phase C — UI differentiation across all three paths:**
- Frontend: Conditional rendering in the payment section based on job type (agreement vs. one-off) and payment state
- Schedule tab: Add pre-paid indicator to calendar appointment cards
- Effort: Small-medium

### Priority

**Phase A is High** — it's a small fix that eliminates a daily annoyance (false payment warnings on every subscription job). Phase B (Stripe tap-to-pay) is **Medium-high** — it's a real feature that enables professional on-site card collection instead of manual record-keeping. Phase C is **Medium** — visual polish that helps the admin work faster.

---

## 18. Schedule Tab: Draft Mode — Don't Send SMS Until the Schedule is Finalized

### The Problem

Currently, the system sends a confirmation SMS to the customer **the instant** an appointment is created on the Schedule tab. This means:

- While you're spending 20-30 minutes building out a week's schedule, customers are receiving one-off texts in real time as you assign jobs
- If you place a job on Tuesday, then realize it should be Thursday and move it, the customer has already received a text for Tuesday — and now gets a second one for Thursday
- If you change your mind and remove a job from the schedule entirely, the customer already got a confirmation for an appointment that no longer exists
- You can't "draft" a schedule, review the whole picture, and then communicate it to customers all at once

The admin has no control over *when* the confirmations go out. The SMS is tightly coupled to the appointment creation action, which means the schedule isn't truly finalized until you stop touching it — but customers are being notified of every intermediate state.

### Proposed Change: Decouple Appointment Creation from SMS Sending

**Core idea:** Creating an appointment on the calendar should be a **silent, internal action**. The confirmation SMS should only go out when the admin explicitly decides the schedule is ready.

### How It Would Work

**Step 1 — Build the schedule (no SMS sent):**
The admin assigns jobs to dates, times, and staff the same way they do today. Appointments are created in the database, they show up on the calendar — but **no SMS is sent**. These appointments are in a "draft" or "unsent" state.

**Step 2 — Review the schedule:**
The admin looks at the calendar for the week, verifies the route makes sense, checks for conflicts, adjusts times. All of this happens without any customer communication.

**Step 3 — Send confirmations:**
When the admin is satisfied, they send confirmations. Three options for how:

**Option A — Send per individual appointment:**
Each appointment card on the calendar has a "Send Confirmation" button (or icon). The admin clicks it on a specific appointment, and that one customer gets the confirmation SMS. The appointment visual changes from "draft" to "sent/unconfirmed."

Good for: Sending confirmations as you finalize each one, even while others are still being adjusted. Useful if you're sure about Monday's schedule but still working on Friday.

**Option B — Send per day:**
A "Send Confirmations for [Day]" button at the top of each day column on the calendar. Clicking it sends SMS confirmations to all unsent appointments on that day.

Good for: Finalizing and communicating one day at a time. Monday is locked in — send Monday's. Come back tomorrow and finalize Tuesday.

**Option C — Bulk send for the week:**
A "Send All Confirmations" button (prominently placed at the top of the Schedule tab) that sends SMS confirmations for all unsent appointments in the current calendar view (week or date range).

Good for: Building the entire week's schedule in one session, reviewing it, and blasting out all confirmations at once.

**Recommendation: Implement all three.** They're not mutually exclusive — they're just different scopes of the same action (send confirmation for 1 appointment / 1 day / all). The backend logic is the same either way — it sends SMS for each selected unsent appointment.

### New Appointment Lifecycle

```
Appointment created on calendar
    (Status: DRAFT — no SMS sent, no customer notification)
    (Visual: dotted border, grayed out — clearly "not yet communicated")
        |
    Admin reviews and adjusts the schedule freely
    (move appointments, change times, swap days — no SMS consequences)
        |
    Admin clicks "Send Confirmation" (per job, per day, or bulk)
        |
    SMS sent: "Reply Y to confirm, R to reschedule, C to cancel"
    (Status: SCHEDULED / UNCONFIRMED — dashed border, muted color)
        |
    Customer replies Y / R / C
    (same flow as today — Y=Confirmed, R=Reschedule request, C=Cancel)
        |
    If confirmed:
    (Status: CONFIRMED — solid border, full color)
```

This adds a **third visual state** to the calendar:

| Visual Style | Meaning |
|-------------|---------|
| **Dotted border, grayed out** | **Draft** — placed on calendar but customer has NOT been notified yet. Safe to move/delete without consequences. |
| **Dashed border, muted color** | **Unconfirmed** — SMS sent, waiting for customer reply |
| **Solid border, full color** | **Confirmed** — customer replied "Y" |

### Edge Cases to Think Through

**What if the admin moves an appointment AFTER confirmation was sent?**
If an appointment has already been sent (status: UNCONFIRMED or CONFIRMED) and the admin moves it to a different day/time, the system should:
- Automatically send a **reschedule notification** SMS: "Your appointment has been moved to [new date] at [new time]. Reply Y to confirm, R to reschedule, or C to cancel."
- Reset the appointment status to UNCONFIRMED (since the customer confirmed the old time, not the new one)
- This is different from the draft phase where moves are silent

**What if the admin deletes a draft appointment?**
No SMS needed — the customer was never told about it. Just remove it from the calendar.

**What if the admin deletes a sent/confirmed appointment?**
Send a cancellation SMS: "Your appointment on [date] has been cancelled. We'll be in touch to reschedule."

**What about the "Send All" button — should it have a confirmation step?**
Yes. Clicking "Send All Confirmations" should show a summary modal:
- "You are about to send confirmation texts to 12 customers for the week of April 20."
- List of customer names and appointment dates
- "Send All" / "Cancel" buttons
This prevents accidental mass-sends.

**Should the schedule be editable after sending?**
Yes, always. The admin should always be able to move, reschedule, or cancel appointments. The difference is just that post-send changes trigger customer notification, while pre-send changes are silent.

### How This Connects to Other Items

- **Item 1 (Job "Scheduled" status):** The job status should change to "Scheduled" when the appointment is created (draft), not when the SMS is sent. The job is on the calendar — that's what "Scheduled" means. Whether the customer has been notified is tracked by the appointment status (DRAFT vs. UNCONFIRMED vs. CONFIRMED).
- **Item 15 (Job selector improvements):** The improved job selector feeds into this — better job selection makes building the draft schedule faster.
- **SMS #1 in the lifecycle diagram (update2_instructions.md):** The confirmation SMS trigger changes from "appointment created" to "admin clicks send." The diagram should be updated when this is implemented.

### Implementation Scope

**Backend:**
- Add a `DRAFT` status to the appointment status enum (before SCHEDULED)
- Modify appointment creation to set status to `DRAFT` instead of `SCHEDULED`
- Remove the automatic SMS send from the appointment creation endpoint
- Add a new endpoint: `POST /api/v1/appointments/{id}/send-confirmation` — sends the SMS and changes status from DRAFT to SCHEDULED
- Add a bulk endpoint: `POST /api/v1/appointments/send-confirmations` — accepts a list of appointment IDs (or a date range filter) and sends confirmations for all DRAFT appointments in the set
- Add logic for post-send rescheduling: if a SCHEDULED or CONFIRMED appointment's date/time is changed, auto-send a reschedule notification

**Frontend:**
- Add the "draft" visual state to the calendar (dotted border, grayed out)
- Add "Send Confirmation" button/icon on each draft appointment card
- Add "Send Confirmations for [Day]" button on each day column header
- Add "Send All Confirmations" button at the top of the Schedule tab (with count badge showing how many unsent appointments exist)
- Add the confirmation summary modal for bulk sends
- Update the existing bulk assignment flow: after bulk-assigning jobs, show a prompt like "12 appointments created. Send confirmations now, or review first?"

**Tests:**
- Test: creating appointment does NOT send SMS (status = DRAFT)
- Test: clicking "Send Confirmation" sends SMS and changes status to SCHEDULED
- Test: bulk send sends SMS for all DRAFT appointments in range
- Test: moving a DRAFT appointment does not send SMS
- Test: moving a SCHEDULED/CONFIRMED appointment sends reschedule notification
- Test: deleting a DRAFT appointment does not send SMS
- Test: deleting a SCHEDULED/CONFIRMED appointment sends cancellation SMS

### Effort Estimate

Medium. The main work is adding the DRAFT status, decoupling SMS from appointment creation, building the send buttons/modal on the frontend, and handling the post-send reschedule logic. The SMS sending logic itself already exists — it's just being moved behind a manual trigger.

### Priority

**High.** This is a fundamental workflow improvement. The current behavior of sending SMS on appointment creation gives the admin zero control over customer communication timing. Every schedule-building session currently generates a stream of premature notifications. This should be implemented alongside or shortly after the "Scheduled" job status (Item 1) since both change the appointment creation flow.

---

## 19. Summary — Priority Order

| # | Item | Type | Priority | Effort |
|---|------|------|----------|--------|
| 1 | **Enforce no-estimate-jobs rule** | Workflow enforcement + security | High | Small (auth fix trivial, guards small) |
| 2 | **On-site status progression fix** | Status model gap | High | Small (add transitions to existing endpoints) |
| 3 | **Job cancellation: clear on-site data** | Data integrity bug | High | Small |
| 4 | **Payment: skip warning for agreement jobs** | Payment flow fix | High | Small |
| 5 | **Schedule draft mode — decouple SMS from appointment creation** | Workflow improvement | High | Medium |
| 6 | **Wire signing to uploaded documents** | Missing wiring | High | Small |
| 7 | **Email provider integration** | Missing integration | High | Medium |
| 8 | **SignWell API keys** | Configuration | High | Low (signup + env vars) |
| 9 | **S3 configuration** | Configuration | High (for prod) | Low (AWS setup) |
| 10 | **Job "Scheduled" status** | Feature improvement | High | Small-medium |
| 11 | **Payment: Stripe Tap-to-Pay integration** | New feature | Medium-high | Medium-large |
| 12 | **Mobile-friendly on-site job view** | UX improvement | Medium-high | Small-medium |
| 13 | **Estimate calendar + pipeline sync** | Workflow improvement | Medium-high | Small-medium |
| 14 | **Improve job selector when scheduling** | UX / workflow improvement | Medium-high | Small-medium |
| 15 | **Payment: UI differentiation (3 paths)** | UX improvement | Medium | Small-medium |
| 16 | **Onboarding week selection consolidation** | UX / data integrity | Medium | Medium |
| 17 | **Google Review SMS bug** | Bug fix | Medium | Low (add one function call) |
| 18 | **Reschedule follow-up SMS** | Feature gap | Medium | Low |
| 19 | **Cancellation confirmation SMS** | Polish | Low | Low |
| 20 | **Twilio provider** | Stub | Not needed now | Medium (if needed) |

### Suggested Order of Execution

**Phase 1 — Unblock Production (config + critical fixes):**
- Enforce no-estimate-jobs rule — auth fix on POST /api/v1/jobs (security), Move to Jobs guard (workflow), visual badge for REQUIRES_ESTIMATE (safety net)
- Job cancellation: clear on-site operations data — nullify on_my_way_at, started_at, completed_at when a job or appointment is cancelled so stale timestamps don't carry over to rescheduled work
- Payment: skip the "No Payment or Invoice" warning for jobs linked to an active service agreement — these are pre-paid, show "Covered by Service Agreement" on the job detail view instead
- S3 configuration (needed for any file storage — documents, photos, invoice PDFs)
- Wire signing to uploaded documents (connect Documents section to SignWell sending)
- SignWell API key provisioning (unblocks entire Sales pipeline signing flow)
- Email provider integration (unblocks invoice delivery)

**Phase 2 — Status and Workflow Improvements (implement together):**
- Add "Scheduled" job status + on-site status progression fix — same status model overhaul. Combined flow: TO_BE_SCHEDULED → SCHEDULED (appt created) → IN_PROGRESS (Job Started) → COMPLETED (Job Complete). Also wire On My Way → appointment EN_ROUTE and Job Complete → appointment COMPLETED.
- Schedule draft mode — add DRAFT appointment status, decouple SMS from appointment creation, add "Send Confirmation" per-job / per-day / bulk buttons. Implement alongside the "Scheduled" status since both change the appointment creation flow.
- Connect estimate calendar to pipeline status (prevents status/calendar getting out of sync)
- Improve job selector when scheduling appointments (show customer name, searchable dropdown, quick-schedule from Jobs tab)
- Mobile-friendly on-site job view (responsive CSS for field workflow)
- Stripe Tap-to-Pay integration — add Stripe Terminal SDK for real on-site card payments, split "Collect Payment" into card (tap-to-pay) vs. manual (cash/check/Venmo/Zelle)
- Payment UI differentiation — conditional payment section on job detail based on whether job is agreement-covered, invoiced, or needs on-site collection

**Phase 3 — Onboarding and SMS Polish:**
- Onboarding week selection consolidation (single per-service picker, correct tier mapping, remove duplicate preference fields)
- Google Review SMS bug fix (one missing function call)
- Reschedule follow-up SMS (better customer experience)
- Cancellation confirmation SMS (template improvement)
