# Smoothing Out After Update 3

Deferred items and potential gaps identified during the Smoothing Out After Update 2 spec review. These are intentionally excluded from Update 2's smoothing-out scope and should be addressed in a future update.

---

## 1. Staff/Admin Role-Based Access Control (RBAC)

### The Gap

The source doc (`CRM_Changes_Update_2.md`) specifies that staff should be able to see everything the admin sees but "cannot delete/remove jobs." Both crm-changes-update-2 (Req 38) and smoothing-out-after-update2 (Req 21) explicitly defer this — all logged-in users currently have full admin privileges.

### What's Needed

1. **Define role-based permissions** — which actions are admin-only vs. available to staff (at minimum: job deletion, customer deletion, staff management)
2. **Add RBAC middleware** — enforce role checks on protected endpoints
3. **Staff management UI** — create/edit/delete staff accounts, assign roles
4. **Existing `staff` table** — already has `admin`, `sales`, `tech` role values in the database; they're just not enforced

### Why It Was Deferred

Single-admin operation — only one person uses the system right now. Once staff/technicians are added as separate users, this becomes critical.

### Priority

**High once staff users are onboarded.** Not needed while operating as a single admin.

---

## 2. Lien Notice Delivery

### The Gap

The source doc mentions the ability to "send lien notices to customers." The crm-changes-update-2 spec implemented the mass notification infrastructure with lien eligibility criteria (60+ days past due AND over $500, configurable) and a configurable template. However, actual lien notice **delivery** depends on the email provider integration, which is out of scope in both specs.

### What's Needed

1. **Email provider integration** must be completed first (AWS SES, SendGrid, or Postmark wired into `email_service.py`)
2. **Lien notice template** — may need legal review for compliance with state lien notice requirements
3. **Delivery tracking** — confirm the lien notice was sent and record it for legal purposes
4. **Certified mail option** — some jurisdictions require lien notices via certified mail, not just email/SMS. This may need a physical mail integration (e.g., Lob API) or a manual workflow.

### What Already Works

- Lien eligibility filtering (60+ days, >$500) in the invoice mass notification system
- Configurable template for the lien notice message
- The "Send" button exists in the UI — it just doesn't deliver electronically yet

### Priority

**Medium.** The filtering and targeting work. Delivery is blocked by the email provider integration.

---

## 3. Estimate Visit Confirmation SMS

### The Gap

The smoothing-out-after-update2 source doc (Item 8, Optional Enhancement) proposes adding a lighter version of the Y/R/C SMS confirmation flow for estimate appointments on the Sales calendar — similar to how job appointments get confirmation texts.

Currently, only job appointments (main Schedule tab) send Y/R/C confirmation SMS. Estimate appointments (Sales calendar) have no customer communication.

### What's Needed

1. **Send a confirmation SMS when an estimate appointment is created** — "We have your estimate visit scheduled for [date] at [time]. Reply Y to confirm or R to request a different time."
2. **Use the same Y/R/C flow** — reuse the existing `JobConfirmationService` infrastructure and `SMSService` abstraction
3. **Handle replies** — Y = confirmed, R = reschedule request surfaced in the admin queue, C = cancel

### Why It Was Deferred

The source doc itself says: "This is a nice-to-have, not a blocker." Estimate visits are typically shorter-notice and more informal than job appointments.

### Priority

**Low-medium.** Nice customer experience improvement, not blocking any workflow.

---

## 4. Email Provider Integration

### The Gap

The `EmailService._send_email()` method in `src/grins_platform/services/email_service.py` is a placeholder — it logs the send as completed but doesn't call any external service. This blocks:

- Sending invoices to customers by email
- Sending estimates to customers by email (outside SignWell)
- Lien notice delivery (Item 2 above)
- Any other email-based customer communication

### What's Needed

1. **Choose an email provider** — AWS SES (cheapest on AWS), SendGrid (easiest setup), or Postmark (best deliverability)
2. **Implement `_send_email()`** — replace placeholder with real API calls
3. **Set `EMAIL_API_KEY` environment variable**
4. **Configure sender domain** — DNS records (SPF, DKIM, DMARC) for deliverability
5. **Template system** — invoice PDF attachment + payment link in body

### What Already Works

- Invoice PDF generation (WeasyPrint) — fully functional
- Email service structure and template rendering — everything except the actual send
- S3 storage for generated PDFs (conditional on S3 config)

### Priority

**High.** Core business operation — invoices can be generated but not delivered electronically.

---

## 5. SignWell API Key Provisioning

### The Gap

The SignWell integration is fully implemented in code (httpx calls, webhook verification, embedded iframe signing, PDF retrieval) but requires two environment variables to be set:

- `SIGNWELL_API_KEY`
- `SIGNWELL_WEBHOOK_SECRET`

Without these, the Sales pipeline signing flow ("Send Estimate for Signature" and "Sign On-Site") will fail.

### What's Needed

1. Create a SignWell account at signwell.com (PAYG pricing)
2. Get the API key from the dashboard
3. Configure the webhook URL and get the secret
4. Set environment variables in the deployment environment
5. Test the full flow end-to-end

### Priority

**High.** Blocks the entire Sales pipeline estimate-to-contract flow.

---

## 6. S3 Configuration for Production

### The Gap

Both `InvoicePDFService` and `PhotoService` use graceful degradation — if S3 credentials aren't configured, they generate placeholder URLs. Files aren't actually persisted in production without proper config.

### What's Needed

1. Create or verify the `grins-platform-files` S3 bucket
2. Set environment variables: `S3_BUCKET_NAME`, `S3_REGION`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
3. Configure CORS if documents need in-browser preview
4. Set lifecycle policy for old files if storage costs are a concern

### Priority

**High for production.** Without S3, uploaded photos, documents, and invoice PDFs aren't persisted.

---

## 7. Generate Routes / AI Scheduling

### The Gap

The source doc mentions "Generate Routes" as a feature awaiting testing. This is being built by a separate team and is independent of both CRM Changes Update 2 and the smoothing-out work.

### Status

Waiting for test coverage from upstream team. Not blocked by any CRM work.

### Priority

**Separate track.** Not in scope for smoothing-out updates.

---

## 8. Marketing & Accounting Features

### The Gap

Both are mentioned in the source doc as "awaiting testing" and "lower priority than Generate Routes & Messaging."

### Status

No implementation work has been done. These are future features with no defined requirements yet.

### Priority

**Low.** Flagged as lower priority by the source doc itself.

---

## Summary — Priority Order for Update 3

| # | Item | Type | Priority | Depends On |
|---|------|------|----------|------------|
| 1 | Email provider integration | Missing integration | High | — |
| 2 | SignWell API key provisioning | Configuration | High | — |
| 3 | S3 configuration | Configuration | High (prod) | — |
| 4 | Staff/Admin RBAC | Feature | High (when staff onboarded) | — |
| 5 | Lien notice delivery | Feature completion | Medium | Email provider (#1) |
| 6 | Estimate visit confirmation SMS | Enhancement | Low-medium | — |
| 7 | Generate Routes / AI scheduling | Feature | Separate track | Upstream team |
| 8 | Marketing & Accounting | Features | Low | No requirements defined |
