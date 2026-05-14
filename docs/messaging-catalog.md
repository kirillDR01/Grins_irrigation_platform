# Client-Facing Messaging Catalog

Every system-templated email and SMS the platform can send to a **customer or lead**. Internal staff alerts and marketing-campaign bodies (which staff compose at send time) are out of scope and listed at the end for reference only.

> **Status as of 2026-05-14, branch `dev`.** Wording is pulled directly from templates and source. Where a body contains optional fragments, both forms are shown.

---

## How to read this doc

Each entry has:

- **ID** — stable kebab-case key, e.g. `estimate.sent.email`
- **Channel** — Email, SMS, or **Portal** (rendered HTML the customer sees after clicking a tokenized link)
- **Trigger** — what fires the send / render
- **Recipient** — customer or lead
- **Sender** — `file:line` of the function (backend) or component (frontend) that builds the message
- **Template** — file path (Jinja HTML / .txt) or "inline f-string" / "React JSX" if assembled in code
- **Subject** — emails only (portal entries have no subject)
- **Raw body** — the template text exactly as it lives in code (placeholders kept as `{name}` or `{{ name }}`)
- **Wire body** — for SMS only, the body *as the recipient receives it* after the system prefix and STOP footer are applied (see SMS Conventions below). Portal entries have **no wire body** (no carrier wrapping).
- **Sample** — one rendered example with realistic values
- **Notes** — gating, dedup, fallbacks, follow-ups, attachments, env-var allowlists

---

## SMS conventions

All outbound SMS that goes through `SMSService.send_message()` / `send_automated_message()` is automatically wrapped:

```
{prefix}{message body}{footer}
```

- **Prefix:** `Grin's Irrigation: ` (configurable via `SMS_SENDER_PREFIX`; defined at `services/sms_service.py:148`)
- **Footer:** ` Reply STOP to opt out.` (defined at `services/sms_service.py:149`)

Two flows skip the prefix/footer because they call the provider directly via `_send_via_provider(...)`:

1. **STOP / START / poll-reply auto-replies** — sent verbatim (carrier-mandated, no extra footer).
2. **Internal staff alerts** — out of scope.

Every other SMS in this doc gets the prefix and footer. The "Wire body" line shows the final form.

## Email conventions

- All transactional email goes through `EmailService._send_email()` → Resend.
- Sender: `noreply@grinsirrigation.com` (transactional) or `info@grinsirrigation.com` (commercial).
- Templates live at `src/grins_platform/templates/emails/` (Jinja). Some emails fall back to inline HTML if a template is missing.
- **Dev/staging guards:** `EMAIL_TEST_ADDRESS_ALLOWLIST` enforces a hard recipient allowlist; `EMAIL_TEST_REDIRECT_TO` rewrites the to-address to a fixed inbox. Production leaves both unset.
- Resend webhooks (`email.bounced`, `email.complained`) trigger an **internal** staff alert — no customer-facing message on bounce.

## Time-window and consent gating

- **SMS time window:** 8 AM–9 PM Central Time (`services/sms_service.py`, CT). Outside the window the send is deferred to a `SentMessage` row with `status=SCHEDULED`.
- **SMS consent scopes:** `transactional` / `marketing` / `operational`. Hard-STOP precedence across all three.
- **Email opt-in / suppression:** checked via `check_suppression_and_opt_in()` before any send.
- **Test phone allowlist (dev only):** `SMS_TEST_PHONE_ALLOWLIST` — only `+19527373312` allowed in dev.

---

## 1. Lead intake

### `lead.confirmation.email`

| | |
|---|---|
| **Channel** | Email |
| **Trigger** | Lead form submission (`POST /api/v1/leads`) |
| **Recipient** | Lead |
| **Sender** | `EmailService.send_lead_confirmation()` — `services/email_service.py:964` |
| **Template** | `templates/emails/lead_confirmation.html` |
| **Subject** | `We Received Your Request — Grin's Irrigation` |

**Raw body (template):**

```
We Received Your Request

Dear {{ customer_name }},

Thank you for reaching out to {{ business_name }}! We have received your service request and will be in touch shortly.

Our typical response time is within one business day.

Questions? Contact us at {{ business_phone }} or {{ business_email }}.

— {{ business_name }}
```

**Sample:**

> Subject: We Received Your Request — Grin's Irrigation
>
> Dear Jane Doe,
>
> Thank you for reaching out to Grin's Irrigation! We have received your service request and will be in touch shortly.
>
> Our typical response time is within one business day.
>
> Questions? Contact us at (952) 818-1020 or info@grinsirrigation.com.
>
> — Grin's Irrigation

**Notes:** Sent only if the lead form provided an email. Sent post-commit on a fresh background session.

---

### `lead.confirmation.sms`

| | |
|---|---|
| **Channel** | SMS |
| **Trigger** | Lead form submission with phone + `sms_consent=true` |
| **Recipient** | Lead |
| **Sender** | `LeadService.send_confirmation_sms()` — `services/lead_service.py:356` |
| **Template** | inline string |

**Raw body:**

```
Thanks for reaching out! We received your request and will be in touch soon.
```

**Wire body (with prefix + footer):**

```
Grin's Irrigation: Thanks for reaching out! We received your request and will be in touch soon. Reply STOP to opt out.
```

**Sample:** Identical to wire body — no merge fields.

**Notes:** Respects 8 AM–9 PM CT window; deferred (`SCHEDULED`) if outside. `MessageType=LEAD_CONFIRMATION`.

---

## 2. Sales pipeline / estimates

### `estimate.sent.email`

| | |
|---|---|
| **Channel** | Email |
| **Trigger** | Staff sends estimate via `POST /api/v1/estimates/{id}/send` or pipeline `POST /api/v1/pipeline/{entry_id}/send-estimate` |
| **Recipient** | Customer or Lead |
| **Sender** | `EmailService.send_estimate_email()` — `services/email_service.py:413` |
| **Template** | `templates/emails/estimate_sent.html` (HTML) + `estimate_sent.txt` (plain) |
| **Subject** | `Your estimate from Grin's Irrigation` |

**Raw body — HTML (visible prose):**

```
Your estimate is ready

Hi {{ customer_name }},

Thanks for considering {{ business_name }}. Your estimate is ready for review. The total comes to ${{ total }}{% if valid_until %}, and pricing is valid through {{ valid_until }}{% endif %}.

[Button: Review your estimate]

Or paste this link into your browser:
{{ portal_url }}

Reply to this email or call {{ business_phone }} with any questions — we're happy to walk through the details.

—
{{ business_name }}
{{ business_phone }} · {{ business_email }}
```

**Raw body — text variant (`estimate_sent.txt`):**

```
Your estimate from {{ business_name }}

Hi {{ customer_name }},

Thanks for considering {{ business_name }}. Your estimate is ready for review.
Total: ${{ total }}
{% if valid_until %}Valid through: {{ valid_until }}
{% endif %}
Review your estimate:

{{ portal_url }}

Reply to this email or call {{ business_phone }} with any questions.

— {{ business_name }}
{{ business_phone }} | {{ business_email }}
```

**Sample (rendered):**

> Subject: Your estimate from Grin's Irrigation
>
> Hi Jane Doe,
>
> Thanks for considering Grin's Irrigation. Your estimate is ready for review. The total comes to $4,250.00, and pricing is valid through June 8, 2026.
>
> [Review your estimate] → https://portal.grinsirrigation.com/estimates/abc-123
>
> Reply to this email or call (952) 818-1020 with any questions.

**Notes:** Schedules four follow-up SMS nudges at D3 / D7 / D14 / D21 (see `estimate.followup.sms`). `valid_until` paragraph drops out if the estimate has no expiration.

---

### `estimate.sent.sms`

| | |
|---|---|
| **Channel** | SMS |
| **Trigger** | Same as `estimate.sent.email`, when the customer/lead has a phone |
| **Recipient** | Customer or Lead |
| **Sender** | `EstimateService.send_estimate()` → `SMSService.send_automated_message()` — `services/estimate_service.py:318` |
| **Template** | inline f-string |

**Raw body:**

```
Your estimate is ready! Review it here: {portal_url}
```

**Wire body:**

```
Grin's Irrigation: Your estimate is ready! Review it here: {portal_url} Reply STOP to opt out.
```

**Sample:**

> Grin's Irrigation: Your estimate is ready! Review it here: https://portal.grinsirrigation.com/estimates/abc-123 Reply STOP to opt out.

**Notes:** Sent immediately after the email path completes if a phone is on file. `MessageType=ESTIMATE_SENT`.

---

### `estimate.approved.email` (signed-PDF delivery)

| | |
|---|---|
| **Channel** | Email + PDF attachment |
| **Trigger** | Customer approves estimate via portal — `POST /portal/estimates/{token}/approve` |
| **Recipient** | Customer or Lead |
| **Sender** | `EmailService.send_estimate_approved_email()` — `services/email_service.py:491` |
| **Template** | `estimate_approved.html` if present, else inline fallback at `services/email_service.py:535` |
| **Subject** | `Your signed estimate from Grin's Irrigation` |

**Raw body (inline fallback, used today):**

```
Hi {customer_name},

Thanks for approving your estimate from Grin's Irrigation. Your signed copy is attached for your records. We will reach out shortly to schedule the work.

Total: ${total}

View your estimate online: {portal_url}
```

**Sample:**

> Subject: Your signed estimate from Grin's Irrigation
>
> Hi Jane Doe,
>
> Thanks for approving your estimate from Grin's Irrigation. Your signed copy is attached for your records. We will reach out shortly to schedule the work.
>
> Total: $4,250.00
>
> View your estimate online: https://portal.grinsirrigation.com/estimates/abc-123
>
> [📎 estimate-abc-123.pdf]

**Notes:** PDF attachment generated by `EstimatePDFService` and capped at 500 KB / 40 MB Resend limit.

---

### `estimate.followup.sms`  (D3 / D7 / D14 / D21)

| | |
|---|---|
| **Channel** | SMS |
| **Trigger** | `EstimateFollowUpJob` fires nightly, picks up `estimate_follow_up` rows whose `scheduled_at` ≤ now AND parent estimate is still pending |
| **Recipient** | Customer or Lead |
| **Sender** | `EstimateService.process_follow_ups()` — `services/estimate_service.py:1088` |
| **Template** | inline f-string (default) or per-row `estimate_follow_up.message` if set |

**Raw body — default (when no custom message stored):**

```
Reminder: Your estimate is waiting for your review. View it here: {portal_url}
```

**Wire body (with prefix + footer):**

```
Grin's Irrigation: Reminder: Your estimate is waiting for your review. View it here: {portal_url} Reply STOP to opt out.
```

**Notes:** Cadence is **SMS-only** — no email companion exists today. Cancelled when the estimate is approved or rejected. **No discount or promo code is ever included** — the auto-attach was removed by design. The body is always the canonical "Reminder: …" form shown above. Future-scheduled rows live in the `estimate_follow_up` table.

---

### `sales_pipeline.nudge.email`  (stale entries)

| | |
|---|---|
| **Channel** | Email |
| **Trigger** | `SalesPipelineNudgeJob` finds `SalesEntry` rows in status `SEND_ESTIMATE` / `PENDING_APPROVAL` / `SEND_CONTRACT` whose `last_contact_date` is > 3 days ago and `nudges_paused_until` is null/past |
| **Recipient** | Customer |
| **Sender** | `EmailService.send_sales_pipeline_nudge()` — `services/email_service.py:1013` |
| **Template** | `templates/emails/sales_pipeline_nudge.html` |
| **Subject** | `Just checking in on your estimate` |

**Raw body (visible prose):**

```
Just checking in

Hi {{ customer_first_name|default("there") }},

We wanted to circle back on the estimate we sent recently. If you have any questions or need a moment to think it over, that's perfectly fine — we're here whenever you're ready.

{% if estimate_total %}
Your estimate total is ${{ "%.2f"|format(estimate_total) }}.
{% endif %}

{% if portal_url %}
[Button: Review your estimate]

Or paste this link into your browser:
{{ portal_url }}
{% endif %}

Reply to this email or call {{ business_phone }} if you'd like to chat — no pressure, no obligation.

—
{{ company_name|default(business_name) }}
{{ business_phone }} · {{ business_email }}
```

**Sample:**

> Subject: Just checking in on your estimate
>
> Hi Jane,
>
> We wanted to circle back on the estimate we sent recently. If you have any questions or need a moment to think it over, that's perfectly fine — we're here whenever you're ready.
>
> Your estimate total is $4,250.00.
>
> [Review your estimate] → https://portal.grinsirrigation.com/estimates/abc-123
>
> Reply to this email or call (952) 818-1020 if you'd like to chat — no pressure, no obligation.

**Notes:** Updates `last_contact_date` on send, audited via `AuditService.log_action()`. Stops automatically when entry leaves the eligible statuses. `estimate_total` and `portal_url` blocks both omit cleanly when missing.

---

## 3. Appointment & scheduling lifecycle

### `appointment.confirmation.sms`  (Y/R/C prompt — initial)

| | |
|---|---|
| **Channel** | SMS |
| **Trigger** | New appointment scheduled |
| **Recipient** | Customer |
| **Sender** | `AppointmentService._send_confirmation_sms()` — `services/appointment_service.py:1781` |
| **Template** | inline f-string |

**Raw body:**

```
Your appointment on {date_str}{time_part}{service_clause} has been scheduled. Reply Y to confirm, R to reschedule, or C to cancel.
```

- `date_str` — weekday + date, e.g. `Monday, May 19, 2026` (`format_sms_date`)
- `time_part` — ` from 10:00 AM to 12:00 PM` if a time window exists, else empty (`format_sms_time_window`)
- `service_clause` — ` for your Spring Cleanup` if job type known, else empty (`format_job_type_display`)

**Wire body (full window + service):**

```
Grin's Irrigation: Your appointment on Monday, May 19, 2026 from 10:00 AM to 12:00 PM for your Spring Cleanup has been scheduled. Reply Y to confirm, R to reschedule, or C to cancel. Reply STOP to opt out.
```

**Wire body (no service type, no time window):**

```
Grin's Irrigation: Your appointment on Monday, May 19, 2026 has been scheduled. Reply Y to confirm, R to reschedule, or C to cancel. Reply STOP to opt out.
```

**Notes:** Raises `CustomerHasNoPhoneError` when no phone on file. Deduped per `appointment_id` within 24 h (Gap 03.B). Earlier confirmation rows for the same appointment are tombstoned (`superseded_at`) when a reschedule fires.

---

### `appointment.confirmation.reply.y.sms`  (auto-reply on "Y")

| | |
|---|---|
| **Channel** | SMS |
| **Trigger** | Customer texts back `Y`, `yes`, `confirm`, `ok`, `okay`, `yup`, `yeah`, or `1` |
| **Recipient** | Customer |
| **Sender** | `JobConfirmationService._build_confirm_message()` — `services/job_confirmation_service.py:418` → `_send_via_provider(bypass_consent=True, bypass_reason='appointment_confirmation_reply')` |
| **Template** | inline f-string |

**Raw body — when date + time known:**

```
Your appointment has been confirmed. See you on {date_str} at {time_str}!
```

**Raw body — fallback (date or time missing):**

```
Your appointment has been confirmed. See you then!
```

**Wire body:** sent verbatim (no prefix/footer added on inbound auto-replies).

**Sample:**

> Your appointment has been confirmed. See you on May 19, 2026 at 2:00 PM!

**Notes:** Transitions appointment to `CONFIRMED`.

---

### `appointment.confirmation.reply.r.sms`  (auto-reply on "R")

| | |
|---|---|
| **Channel** | SMS |
| **Trigger** | Customer texts `R`, `reschedule`, `different time`, `change time`, or `2` |
| **Recipient** | Customer |
| **Sender** | `_AUTO_REPLIES[ConfirmationKeyword.RESCHEDULE]` — `services/job_confirmation_service.py:76` |
| **Template** | static string |

**Raw body:**

```
We'd be happy to reschedule. Please reply with 2-3 dates and times that work for you and we'll get you booked.
```

**Wire body:** sent verbatim.

**Notes:** Creates a `RescheduleRequest` row; idempotent against duplicate open requests (Gap 1.A). If the appointment is already `EN_ROUTE` / `IN_PROGRESS` / `COMPLETED`, a `_build_late_reschedule_reply()` message is sent instead and a late-reschedule alert fires to staff.

---

### `appointment.confirmation.reply.c.sms`  (auto-reply on "C")

| | |
|---|---|
| **Channel** | SMS |
| **Trigger** | Customer texts `C` or `cancel` |
| **Recipient** | Customer |
| **Sender** | `JobConfirmationService._build_cancellation_message()` — `services/job_confirmation_service.py:1098` |
| **Template** | inline f-string |

**Raw body — full info available:**

```
Your {service_display} appointment on {date_str} at {time_str} has been cancelled. If you'd like to reschedule, please call us at {business_phone}.
```

**Raw body — `business_phone` not configured:**

```
Your {service_display} appointment on {date_str} at {time_str} has been cancelled. Please contact us if you'd like to reschedule.
```

**Raw body — fallback (service or date/time missing):**

```
Your appointment has been cancelled. Please contact us if you'd like to reschedule.
```

**Wire body:** sent verbatim.

**Sample:**

> Your Spring Cleanup appointment on May 19, 2026 at 2:00 PM has been cancelled. If you'd like to reschedule, please call us at (952) 818-1020.

**Notes:** Transitions appointment to `CANCELLED`. `business_phone` from env `BUSINESS_PHONE_NUMBER`.

---

### `appointment.reschedule.sms`  (admin moved appointment)

| | |
|---|---|
| **Channel** | SMS |
| **Trigger** | Admin moves an appointment to a new date/time |
| **Recipient** | Customer |
| **Sender** | `AppointmentService._send_reschedule_sms()` — `services/appointment_service.py:1838` |
| **Template** | inline f-string |

**Raw body:**

```
{subject} has been rescheduled to {date_str}{time_part}. Reply Y to confirm, R to reschedule, or C to cancel.
```

- `subject` — `Your Spring Cleanup appointment` if service known, else `Your appointment`

**Wire body:**

```
Grin's Irrigation: Your Spring Cleanup appointment has been rescheduled to Tuesday, May 20, 2026 from 10:00 AM to 12:00 PM. Reply Y to confirm, R to reschedule, or C to cancel. Reply STOP to opt out.
```

**Notes:** `MessageType=APPOINTMENT_RESCHEDULE`. Earlier confirmation/cancellation rows for the same `appointment_id` are tombstoned.

---

### `appointment.reminder.sms`  (day-of)

| | |
|---|---|
| **Channel** | SMS |
| **Trigger** | Day-of cron (`NotificationService.send_day_of_reminders`) for today's appointments |
| **Recipient** | Customer |
| **Sender** | `services/notification_service.py:409` |
| **Template** | inline f-string |

**Raw body:**

```
Reminder: You have an appointment today between {window_start} and {window_end}. {staff_name} will be your technician.
```

**Wire body:**

```
Grin's Irrigation: Reminder: You have an appointment today between 2:00 PM and 4:00 PM. John will be your technician. Reply STOP to opt out.
```

---

### `appointment.reminder.email`  (day-of)

| | |
|---|---|
| **Channel** | Email |
| **Trigger** | Same as SMS reminder |
| **Recipient** | Customer |
| **Sender** | `services/notification_service.py:414` |
| **Template** | inline HTML |
| **Subject** | `Appointment Reminder — Grin's Irrigation` |

**Raw body (HTML):**

```html
<p>This is a reminder that you have an appointment scheduled today with Grin's Irrigation.</p>
<p><strong>Time window:</strong> {window_start} - {window_end}</p>
<p><strong>Technician:</strong> {staff_name}</p>
```

**Sample:**

> This is a reminder that you have an appointment scheduled today with Grin's Irrigation.
>
> **Time window:** 2:00 PM - 4:00 PM
> **Technician:** John

---

### `appointment.on_the_way.sms`

| | |
|---|---|
| **Channel** | SMS |
| **Trigger** | Tech / dispatcher marks appointment as en route |
| **Recipient** | Customer |
| **Sender** | `services/notification_service.py:492` |
| **Template** | inline f-string |

**Raw body — without ETA:**

```
{staff_name} is on the way to your appointment!
```

**Raw body — with ETA:**

```
{staff_name} is on the way to your appointment! Estimated arrival in {eta_minutes} minutes.
```

**Wire body (with ETA):**

```
Grin's Irrigation: John is on the way to your appointment! Estimated arrival in 15 minutes. Reply STOP to opt out.
```

---

### `appointment.on_the_way.email`

| | |
|---|---|
| **Channel** | Email |
| **Trigger** | Same as SMS |
| **Sender** | `services/notification_service.py:496` |
| **Template** | inline HTML |
| **Subject** | `Your Technician Is On The Way — Grin's Irrigation` |

**Raw body (HTML):**

```html
<p><strong>{staff_name}</strong> from Grin's Irrigation is on the way to your appointment.</p>
<p>{eta_text}</p>
```

`eta_text` = `Estimated arrival in 15 minutes.` or empty.

---

### `appointment.arrival.sms`

| | |
|---|---|
| **Channel** | SMS |
| **Trigger** | Tech marks appointment as arrived |
| **Recipient** | Customer |
| **Sender** | `services/notification_service.py:553` |
| **Template** | inline f-string |

**Raw body:**

```
{staff_name} has arrived for your appointment.
```

**Wire body:**

```
Grin's Irrigation: John has arrived for your appointment. Reply STOP to opt out.
```

---

### `appointment.arrival.email`

| | |
|---|---|
| **Channel** | Email |
| **Trigger** | Same as SMS |
| **Sender** | `services/notification_service.py:556` |
| **Template** | inline HTML |
| **Subject** | `Your Technician Has Arrived — Grin's Irrigation` |

**Raw body (HTML):**

```html
<p><strong>{staff_name}</strong> from Grin's Irrigation has arrived for your scheduled appointment.</p>
```

---

### `appointment.delay.sms`

| | |
|---|---|
| **Channel** | SMS |
| **Trigger** | Appointment running >15 min past end |
| **Recipient** | Customer |
| **Sender** | `services/notification_service.py:618` |
| **Template** | inline f-string |

**Raw body — without revised ETA:**

```
Your appointment is running a bit longer than expected. We apologize for the delay.
```

**Raw body — with revised ETA:**

```
Your appointment is running a bit longer than expected. We apologize for the delay. We now expect to finish around {new_eta_time}.
```

**Wire body (with revised ETA):**

```
Grin's Irrigation: Your appointment is running a bit longer than expected. We apologize for the delay. We now expect to finish around 4:15 PM. Reply STOP to opt out.
```

---

### `appointment.delay.email`

| | |
|---|---|
| **Channel** | Email |
| **Sender** | `services/notification_service.py:622` |
| **Template** | inline HTML |
| **Subject** | `Appointment Update — Grin's Irrigation` |

**Raw body (HTML):**

```html
<p>Your Grin's Irrigation appointment is running longer than expected. We apologize for the inconvenience.</p>
<p>{eta_text}</p>
```

---

### `appointment.completion.sms`

| | |
|---|---|
| **Channel** | SMS |
| **Trigger** | Tech marks appointment as completed |
| **Recipient** | Customer |
| **Sender** | `services/notification_service.py:681` |
| **Template** | inline f-string |

**Raw body — minimal:**

```
Your appointment is complete! {job_summary}
```

**Raw body — with invoice link:**

```
Your appointment is complete! {job_summary} View your invoice: {invoice_url}
```

**Raw body — with invoice + review link:**

```
Your appointment is complete! {job_summary} View your invoice: {invoice_url} We'd love your feedback: {google_review_url}
```

**Wire body (full):**

```
Grin's Irrigation: Your appointment is complete! Cleaned spray heads on zones 1–3, replaced backflow valve. View your invoice: https://portal.grinsirrigation.com/invoices/inv-001 We'd love your feedback: https://g.page/r/grins-irrigation Reply STOP to opt out.
```

**Notes:** `google_review_url` from env `GOOGLE_REVIEW_URL` or service override; omitted block if not configured.

---

### `appointment.completion.email`

| | |
|---|---|
| **Channel** | Email |
| **Sender** | `services/notification_service.py:686` |
| **Template** | inline HTML built from parts |
| **Subject** | `Appointment Complete — Grin's Irrigation` |

**Raw body (HTML, parts joined as available):**

```html
<p>Your Grin's Irrigation appointment has been completed.</p>
<p>{job_summary}</p>                       <!-- if summary present -->
<p><a href="{invoice_url}">View Invoice</a></p>     <!-- if invoice URL present -->
<p><a href="{review_url}">Leave a Review</a></p>    <!-- if review URL present -->
```

---

### `review_request.sms`  (manual review request)

| | |
|---|---|
| **Channel** | SMS |
| **Trigger** | Staff calls `AppointmentService.request_google_review()` (manual button) |
| **Recipient** | Customer |
| **Sender** | `services/appointment_service.py:2629` |
| **Template** | inline f-string |

**Raw body:**

```
Hi {first_name}! Thank you for choosing Grin's Irrigation. We'd love your feedback - please leave a Google review: {review_url}
```

**Wire body:**

```
Grin's Irrigation: Hi Jane! Thank you for choosing Grin's Irrigation. We'd love your feedback - please leave a Google review: https://g.page/r/grins-irrigation Reply STOP to opt out.
```

**Notes:** Requires `GOOGLE_REVIEW_URL` (or per-call override). Deduped: 30-day cooldown per customer (`ReviewAlreadyRequestedError` if violated). `MessageType=REVIEW_REQUEST`, transactional consent.

---

## 4. Invoicing & payments

### `payment_link.sms`  (Stripe Payment Link via SMS)

| | |
|---|---|
| **Channel** | SMS |
| **Trigger** | Staff taps **Send Payment Link**, or automation calls `InvoiceService.send_payment_link()` |
| **Recipient** | Customer |
| **Sender** | `_build_payment_link_sms_body()` — `services/invoice_service.py:1124` |
| **Template** | inline f-string |

**Raw body:**

```
Hi {first_name}, your invoice for ${total_amount} is ready: {stripe_payment_link_url}
```

**Wire body:**

```
Grin's Irrigation: Hi Jane, your invoice for $4,250.00 is ready: https://buy.stripe.com/xxx Reply STOP to opt out.
```

**Notes:** Stripe Payment Link auto-created at invoice creation; this just sends it. Webhook `checkout.session.completed` reconciles via `metadata.invoice_id`.

---

### `payment_link.email`

| | |
|---|---|
| **Channel** | Email |
| **Trigger** | Same as SMS |
| **Recipient** | Customer |
| **Sender** | `services/invoice_service.py:1083` → `EmailService._send_email()` |
| **Template** | `templates/emails/payment_link_email.html` (HTML) + `payment_link_email.txt` |
| **Subject** | `Your invoice from Grin's Irrigation` |

**Raw body — HTML (visible prose):**

```
Your invoice is ready

Hi {{ customer_first_name }},

Your invoice {{ invoice_number }} from {{ business_name }} is ready. The total comes to ${{ total_amount }}.

[Button: Pay invoice]

Or paste this link into your browser:
{{ payment_link_url }}

Reply to this email or call {{ business_phone }} with any questions — we're happy to help.

—
{{ business_name }}
{{ business_phone }} · {{ business_email }}
```

**Raw body — text variant:**

```
Your invoice from {{ business_name }}

Hi {{ customer_first_name }},

Your invoice {{ invoice_number }} from {{ business_name }} is ready.
Total: ${{ total_amount }}

Pay here:

{{ payment_link_url }}

Reply to this email or call {{ business_phone }} with any questions.

— {{ business_name }}
{{ business_phone }} | {{ business_email }}
```

---

### `payment_reminder.sms.pre_due`

| | |
|---|---|
| **Channel** | SMS |
| **Trigger** | Cron, ~3 days before due (configurable via `business_settings.pre_due_reminder_days`); fires once per invoice |
| **Recipient** | Customer |
| **Sender** | `NotificationService._send_pre_due_reminder()` — `services/notification_service.py:883` |
| **Template** | inline f-string |

**Raw body — no portal link:**

```
Your invoice {invoice_number} for ${total_amount} is due on {due_date}.
```

**Raw body — with portal link:**

```
Your invoice {invoice_number} for ${total_amount} is due on {due_date}. View your invoice: {portal_link}
```

**Wire body:**

```
Grin's Irrigation: Your invoice INV-2026-001234 for $4,250.00 is due on May 25, 2026. View your invoice: https://portal.grinsirrigation.com/invoices/xyz Reply STOP to opt out.
```

---

### `payment_reminder.email.pre_due`

| | |
|---|---|
| **Channel** | Email |
| **Sender** | `services/notification_service.py:888` |
| **Template** | inline HTML |
| **Subject** | `Invoice {invoice_number} Due Soon` |

**Raw body (HTML):**

```html
<p>This is a friendly reminder that your invoice <strong>{invoice_number}</strong> for <strong>${total_amount}</strong> is due on <strong>{due_date}</strong>.</p>
<p>Please arrange payment at your earliest convenience.</p>
<p><a href="{portal_link}">View Invoice</a></p>   <!-- only if portal link present -->
```

---

### `payment_reminder.sms.past_due`  (weekly)

| | |
|---|---|
| **Channel** | SMS |
| **Trigger** | Cron, daily; sends if `days_past_due > 0` and last past-due send was ≥ `business_settings.past_due_interval_days` (default 7) ago, while `days_past_due < lien_threshold` |
| **Recipient** | Customer |
| **Sender** | `NotificationService._send_past_due_reminder()` — `services/notification_service.py:938` |
| **Template** | inline f-string |

**Raw body — minimal:**

```
Your invoice {invoice_number} for ${total_amount} is past due. Please pay at your earliest convenience.
```

**Raw body — with Stripe Payment Link and portal:**

```
Your invoice {invoice_number} for ${total_amount} is past due. Please pay at your earliest convenience. Pay now: {stripe_pay_link} View and pay: {portal_link}
```

**Wire body:**

```
Grin's Irrigation: Your invoice INV-2026-001234 for $4,250.00 is past due. Please pay at your earliest convenience. Pay now: https://buy.stripe.com/xxx View and pay: https://portal.grinsirrigation.com/invoices/xyz Reply STOP to opt out.
```

---

### `payment_reminder.email.past_due`

| | |
|---|---|
| **Channel** | Email |
| **Sender** | `services/notification_service.py:944` |
| **Template** | inline HTML |
| **Subject** | `Invoice {invoice_number} Past Due` |

**Raw body (HTML):**

```html
<p>Your invoice <strong>{invoice_number}</strong> for <strong>${total_amount}</strong> is past due.</p>
<p>Please arrange payment at your earliest convenience to avoid additional fees.</p>
<p><a href="{stripe_pay_link}">Pay Invoice</a></p>          <!-- if Stripe link active -->
<p><a href="{portal_link}">View and Pay Invoice</a></p>     <!-- if portal link -->
```

---

### `payment_reminder.sms.lien_warning`  (45+ days past due)

| | |
|---|---|
| **Channel** | SMS |
| **Trigger** | Cron, when invoice is `lien_eligible=true` and `days_past_due >= 45` (default) and `lien_warning_sent` is null |
| **Recipient** | Customer |
| **Sender** | `NotificationService._send_lien_notification()` — `services/notification_service.py:999` |
| **Template** | inline f-string |

**Raw body:**

```
IMPORTANT: Invoice {invoice_number} for ${total_amount} is 30+ days past due. A lien may be filed against {address} if payment is not received by {lien_deadline}.{stripe_pay_link_text}{portal_text}
```

- `{address}` = customer's primary property address (`123 Maple St, Edina MN 55424`) or fallback `the service property`
- `{lien_deadline}` = `due_date + 90 days`, formatted `%B %d, %Y`
- Optional fragments append `Pay now: {url}` and ` View and pay: {url}` if those links exist

**Wire body (full):**

```
Grin's Irrigation: IMPORTANT: Invoice INV-2026-001234 for $4,250.00 is 30+ days past due. A lien may be filed against 123 Maple St, Edina MN 55424 if payment is not received by August 28, 2026. Pay now: https://buy.stripe.com/xxx View and pay: https://portal.grinsirrigation.com/invoices/xyz Reply STOP to opt out.
```

**Notes:** Sent **once per invoice** (`lien_warning_sent` flagged after send). Status transitions to `LIEN_WARNING`. Compliance: Req 55.2–55.5.

---

### `payment_reminder.email.lien_warning`

| | |
|---|---|
| **Channel** | Email |
| **Sender** | `services/notification_service.py:1006` |
| **Template** | inline HTML |
| **Subject** | `Formal Lien Notice — Invoice {invoice_number}` |

**Raw body (HTML):**

```html
<p><strong>Formal Lien Notice</strong></p>
<p>Invoice <strong>{invoice_number}</strong> for <strong>${total_amount}</strong> is more than 30 days past due.</p>
<p><strong>Property:</strong> {address}</p>
<p><strong>Invoice Amount:</strong> ${total_amount}</p>
<p><strong>Lien Filing Deadline:</strong> {lien_deadline}</p>
<p>Please arrange immediate payment to avoid a lien being filed against the property.</p>
<p><a href="{stripe_pay_link}">Pay Invoice</a></p>     <!-- if active -->
<p><a href="{portal_link}">Pay Invoice Now</a></p>     <!-- if portal -->
```

---

### `payment_receipt.email`  (post-payment confirmation)

| | |
|---|---|
| **Channel** | Email |
| **Trigger** | Successful payment recorded (Stripe webhook OR cash/check/Venmo/Zelle entry) |
| **Recipient** | Customer |
| **Sender** | `EmailService.send_payment_receipt_email()` — `services/email_service.py:586` |
| **Template** | `templates/emails/payment_receipt_email.html` |
| **Subject** | `Receipt for invoice {invoice_number} — Grin's Irrigation` |

**Raw body (HTML, visible prose):**

```
Payment received

Hi {{ customer_first_name }},

Thank you — we received your payment of ${{ amount_paid }} via {{ payment_method_display }} on {{ paid_at_display }}.

[ Invoice            | {{ invoice_number }}        ]
[ Amount paid        | ${{ amount_paid }}          ]
[ Method             | {{ payment_method_display }}]
[ Reference          | {{ payment_reference }}     ]   <!-- only if present -->
[ Status             | {{ invoice_status }}        ]

This is Grin's receipt for your records. Reply to this email or call {{ business_phone }} with any questions.

—
{{ business_name }}
{{ business_phone }} · {{ business_email }}
```

**Sample:**

> Subject: Receipt for invoice INV-2026-001234 — Grin's Irrigation
>
> Hi Jane,
>
> Thank you — we received your payment of $4,250.00 via Stripe Card on May 20, 2026.
>
> | Invoice | INV-2026-001234 |
> | Amount paid | $4,250.00 |
> | Method | Stripe Card |
> | Reference | pi_3Pxxx... |
> | Status | Paid |

**Notes:** `payment_method_display` = title-cased method (`stripe_card` → `Stripe Card`). Reference row hidden if `payment_reference` empty.

---

## 5. Agreements / subscriptions

### `subscription.welcome.email`

| | |
|---|---|
| **Channel** | Email |
| **Trigger** | `ServiceAgreement` created after subscription purchase |
| **Recipient** | Customer |
| **Sender** | `EmailService.send_welcome_email()` — `services/email_service.py:351` |
| **Template** | `templates/emails/welcome.html` |
| **Subject** | `Welcome to Grin's Irrigation {tier_name} Plan!` |

**Raw body (visible prose):**

```
Welcome to {{ business_name }} {{ tier_name }} Plan!

Dear {{ customer_name }},

Thank you for choosing {{ business_name }}! Your {{ tier_name }} ({{ package_type }}) subscription is now active.

Subscription Details
- Plan: {{ tier_name }} ({{ package_type }})
- Annual Price: ${{ annual_price }}
- Start Date: {{ start_date }}     <!-- omitted if missing -->

Included Services
- {{ svc.service_type }}{% if svc.description %} — {{ svc.description }}{% endif %}
- ...

Next Steps

Please complete your property details so we can schedule your visits:
[Manage Your Subscription]   <!-- only rendered if session_id present -->

Questions? Contact us at {{ business_phone }} or {{ business_email }}.

— {{ business_name }}
```

**Sample:**

> Subject: Welcome to Grin's Irrigation Premium Plan!
>
> Dear Jane Doe,
>
> Thank you for choosing Grin's Irrigation! Your Premium (Annual) subscription is now active.
>
> **Subscription Details**
> - Plan: Premium (Annual)
> - Annual Price: $1,800.00
> - Start Date: May 1, 2026
>
> **Included Services**
> - Spring Cleanup — Backflow test + zone audit
> - Mid-Season Tune-Up
> - Winterization

---

### `subscription.confirmation.email`  (MN auto-renewal compliance — Statute 325G.56–325G.62)

| | |
|---|---|
| **Channel** | Email |
| **Trigger** | `ServiceAgreement` confirmed/created |
| **Recipient** | Customer |
| **Sender** | `EmailService.send_confirmation_email()` — `services/email_service.py:744` |
| **Template** | `templates/emails/confirmation.html` |
| **Subject** | `Your Grin's Irrigation Service Agreement Confirmation` |

**Raw body (visible prose):**

```
Service Agreement Confirmation

Dear {{ customer_name }},

This confirms your {{ tier_name }} service agreement with {{ business_name }}. Per Minnesota Statute 325G.56–325G.62, please review the following terms:

Auto-Renewal Terms
1. Continuation: Your service continues automatically until you terminate it.
2. Cancellation Policy: You may cancel at any time via the Stripe Customer Portal, by calling {{ business_phone }}, or by emailing {{ business_email }}.
3. Recurring Charge: ${{ annual_price }} billed {{ billing_frequency }}.
4. Renewal Term: Your agreement renews for successive one-year terms (next renewal: {{ renewal_date }}).
5. Minimum Purchase: No minimum purchase obligations beyond the subscription price.

Included Services
- {{ svc.service_type }}
- ...

Manage your subscription: [Stripe Customer Portal]

Questions? Contact us at {{ business_phone }} or {{ business_email }}.

— {{ business_name }}
```

**Notes:** Disclosure type: `CONFIRMATION`. All five MN statutory terms required — do not edit copy without legal review.

---

### `subscription.renewal_notice.email`  (pre-renewal, default ~14 days)

| | |
|---|---|
| **Channel** | Email |
| **Trigger** | Cron N days before `renewal_date` (configurable, default 14) |
| **Recipient** | Customer |
| **Sender** | `EmailService.send_renewal_notice()` — `services/email_service.py:806` |
| **Template** | `templates/emails/renewal_notice.html` |
| **Subject** | `Your Grin's Irrigation Service Agreement Renewal Notice` |

**Raw body (visible prose):**

```
Service Agreement Renewal Notice

Dear {{ customer_name }},

Your {{ business_name }} service agreement is approaching renewal.

Renewal Details
- Renewal Date: {{ renewal_date }}
- Renewal Price: ${{ annual_price }}

Cancellation Instructions

If you do not wish to renew, you may cancel before the renewal date:
- Stripe Customer Portal
- Phone: {{ business_phone }}
- Email: {{ business_email }}

Services Provided This Term      <!-- only if completed_jobs present -->
- {{ job.name }} — {{ job.date }}
- ...

Manage your subscription: [Stripe Customer Portal]

— {{ business_name }}
```

**Notes:** Disclosure type: `RENEWAL_NOTICE`. MN compliance Req 39B.4.

---

### `subscription.annual_notice.email`  (MN Statute 325G.59)

| | |
|---|---|
| **Channel** | Email |
| **Trigger** | Annual cron at agreement anniversary |
| **Recipient** | Customer |
| **Sender** | `EmailService.send_annual_notice()` — `services/email_service.py:856` |
| **Template** | `templates/emails/annual_notice.html` |
| **Subject** | `Annual Notice — Your Grin's Irrigation Service Agreement` |

**Raw body (visible prose):**

```
Annual Notice — Your Service Agreement

Dear {{ customer_name }},

Per Minnesota Statute 325G.59, this is your annual notice regarding your {{ business_name }} {{ tier_name }} service agreement.

Current Terms
- Plan: {{ tier_name }}
- Annual Price: ${{ annual_price }}
- Auto-Renewal: Your service continues automatically until you terminate it.

Included Services           <!-- only if list present -->
- {{ svc }}
- ...

How to Terminate or Manage Your Subscription

You may cancel or manage your subscription at any time:
- Stripe Customer Portal
- Phone: {{ business_phone }}
- Email: {{ business_email }}

— {{ business_name }}
```

**Notes:** Disclosure type: `ANNUAL_NOTICE`. MN compliance Req 39B.5.

---

### `subscription.cancellation_confirmation.email`

| | |
|---|---|
| **Channel** | Email |
| **Trigger** | `ServiceAgreement` cancelled (customer or staff) |
| **Recipient** | Customer |
| **Sender** | `EmailService.send_cancellation_confirmation()` — `services/email_service.py:904` |
| **Template** | `templates/emails/cancellation_conf.html` |
| **Subject** | `Grin's Irrigation Service Agreement Cancellation Confirmation` |

**Raw body (visible prose):**

```
Service Agreement Cancellation Confirmation

Dear {{ customer_name }},

This confirms the cancellation of your {{ business_name }} service agreement.

Cancellation Details
- Effective Date: {{ cancellation_date }}
- Reason: {{ cancellation_reason }}        <!-- omitted if not provided -->
- Prorated Refund: ${{ refund_amount }}    <!-- omitted if zero/None -->

Any remaining scheduled visits will be honored as planned.

Questions? Contact us at {{ business_phone }} or {{ business_email }}.

— {{ business_name }}
```

**Notes:** Disclosure type: `CANCELLATION_CONF`. MN compliance Req 39B.6.

---

### `subscription.manage.email`  (one-time portal session link)

| | |
|---|---|
| **Channel** | Email |
| **Trigger** | Customer requests "Manage subscription" link from public site → backend creates a Stripe billing-portal session and emails the URL |
| **Recipient** | Customer |
| **Sender** | `EmailService.send_subscription_management_email()` — `services/email_service.py:1057` |
| **Template** | `templates/emails/subscription_manage.html` |
| **Subject** | `Manage Your Grin's Irrigation Subscription` |

**Raw body (visible prose):**

```
Manage Your Subscription

Hello,

You requested access to manage your {{ business_name }} subscription. Click the link below to view and manage your billing details:

[Manage My Subscription]

This link will expire shortly. If it has expired, you can request a new one from our website.

What You Can Do
- View your current plan and billing details
- Update your payment method
- View past invoices
- Cancel your subscription

If you did not request this email, you can safely ignore it.

Questions? Contact us at {{ business_phone }} or {{ business_email }}.

— {{ business_name }}
```

**Notes:** Stripe billing-portal sessions expire on a short window — the email explicitly says so.

---

## 6. Portal copy

Customer-facing screens rendered by the React app at `/portal/...` after the customer clicks a tokenized link (estimate / invoice / contract / subscription / scheduling-poll) delivered via SMS or email. These entries have **no Wire body** (no SMS prefix/footer wrapping) and **no Subject** (rendered page, not email). The Sender is the React component file:line; copy lives in JSX, not Jinja.

Scope is the same as elsewhere in the catalog: customer-facing screens only. Internal admin / staff screens (`/admin`, `/dashboard`, etc.) are out of scope.

### `portal.estimate_review.copy`

| | |
|---|---|
| **Channel** | Portal (rendered HTML) |
| **Trigger** | Customer/lead clicks the `portal_url` link in `estimate.sent.email` / `estimate.sent.sms` and lands on `/portal/estimates/{token}` |
| **Recipient** | Customer or Lead |
| **Sender (file:line)** | `frontend/src/features/portal/components/EstimateReview.tsx:133-359` |
| **Template** | React JSX (no Jinja) |

**Raw strings (visible to customer):**

- Header business name: `{estimate.company_name ?? 'Grin's Irrigation'}` (line 148)
- Header phone (optional): `{estimate.company_phone}` (line 151)
- Estimate label: `Estimate {estimate.estimate_number}` (line 164)
- Status badge: dynamic — renders `APPROVED` / `REJECTED` / `PENDING` (line 171)
- Label: `Prepared for:` (line 177)
- Label: `Date:` (line 185)
- Label: `Valid until:` (line 192)
- Section heading: `Select an Option` (line 205) — only shown when `estimate.tiers` is populated
- Section heading: `Line Items` (line 233) — or `{selectedTier} — Line Items` (line 234) when a tier is selected
- Totals labels: `Subtotal` (249), `Tax` (254), `Discount {promotion_code?}` (260), `Total` (265)
- Notes block: `Notes` heading (273) + `{estimate.notes}` body (274) — only when notes are present
- Error alert: `We couldn't save that action. Please try again or call us at the number above.` (line 285)
- Approve CTA: `Approve Estimate` (line 302)
- Reject CTA: `Reject` (line 311)
- Reject-form heading: `Reason for Rejection (optional)` (line 316)
- Reject-form placeholder: `Let us know why you're declining this estimate...` (line 320)
- Reject-form confirm CTA: `Confirm Rejection` (line 332) — or spinner (`Loader2`) while pending
- Reject-form cancel CTA: `Cancel` (line 343)
- Readonly notice: `This estimate has already been {status.toLowerCase()}.` (line 353)

**Notes:** Approve/Reject CTAs are hidden when `estimate.is_readonly` is true (already approved/rejected). Tier selection is required before Approve becomes enabled when `estimate.tiers` is populated. Sticky-mobile CTA layout is tracked separately under Cluster H §13. After submit, the customer is redirected to `portal.estimate_approval_confirmation.copy` (see below).

---

### `portal.estimate_approval_confirmation.copy`

| | |
|---|---|
| **Channel** | Portal (rendered HTML) |
| **Trigger** | After `EstimateReview` submits Approve or Reject — `react-router` `navigate('/portal/estimates/confirmation', { state: { action } })` |
| **Recipient** | Customer or Lead |
| **Sender (file:line)** | `frontend/src/features/portal/components/ApprovalConfirmation.tsx:13-89` |
| **Template** | React JSX |

**Raw strings (visible to customer):**

- **action = `approved`** (lines 13-23):
  - Title: `Estimate Approved!`
  - Message: `Thank you for approving the estimate. We appreciate your business.`
  - Next steps:
    - `You will receive a confirmation email shortly.`
    - `Our team will reach out to schedule the work.`
    - `A contract may be sent for your signature.`
- **action = `rejected`** (lines 24-33):
  - Title: `Estimate Declined`
  - Message: `We understand. Thank you for letting us know.`
  - Next steps:
    - `If you change your mind, please contact us.`
    - `We can prepare a revised estimate if needed.`
- **action = `signed`** (lines 34-44):
  - Title: `Contract Signed!`
  - Message: `Thank you for signing the contract. We look forward to working with you.`
  - Next steps:
    - `You will receive a copy of the signed contract via email.`
    - `Our team will begin scheduling the work.`
    - `You can reach out anytime with questions.`
- Section heading: `Next Steps` (line 70)
- Footer: `You may close this page.` (line 83)

**Notes:** Action read from `location.state.action`; defaults to `approved` if state is missing (e.g., user navigated here directly).

---

### `portal.invoice_payment.copy`

| | |
|---|---|
| **Channel** | Portal (rendered HTML) |
| **Trigger** | Customer clicks the Stripe-Payment-Link / portal-payment URL in `payment_link.sms` / `payment_link.email` and lands on `/portal/invoices/{token}` |
| **Recipient** | Customer |
| **Sender (file:line)** | `frontend/src/features/portal/components/InvoicePortal.tsx:1-241` |
| **Template** | React JSX |

**Raw strings (visible to customer):**

- Header business name: `{invoice.company_name ?? 'Grin's Irrigation'}` (line 102)
- Optional header `{invoice.company_address}` (line 105) and `{invoice.company_phone}` (line 108)
- Body: `Invoice {invoice.invoice_number}` (line 121)
- Status badge labels via `statusConfig` (lines 27-34): `Paid`, `Partially Paid`, `Sent`, `Viewed`, `Overdue`, `Draft`
- Label: `Bill to:` (line 131)
- Label: `Invoice date:` (line 135)
- Label: `Due date:` (line 141)
- Section heading: `Line Items` (line 157)
- Table headers: `Description` / `Qty` / `Unit Price` / `Total` (lines 162-165)
- Totals: `Total Amount` (184), `Amount Paid` (189), `Balance Due` (197)
- Paid state (lines 205-209): heading `Paid in Full` + body `Thank you for your payment.`
- Pay CTA: `Pay Now — {balance}` (line 219)
- Payment-unavailable fallback (lines 223-235): `Online payment is not available for this invoice. Please contact the business to arrange payment.`
- **Expired-link state** (HTTP 410, lines 51-67): heading `Link Expired`, body `This invoice link has expired (over 90 days old). Please contact the business for assistance.`, contact-card body `Contact us for an updated invoice link.`
- **Generic error state** (lines 70-81): heading `Unable to Load Invoice`, body `We couldn't load this invoice. The link may be invalid or expired.`

**Notes:** Pay-Now CTA is only rendered when `invoice.payment_url` is set (Stripe-Payment-Link path). Loading state shows a spinner only — no copy. The portal does NOT collect payment directly; it links out to a Stripe-hosted page (see plan/architecture C in memory `project_stripe_payment_links_arch_c`).

---

### `portal.contract_signing.copy`

| | |
|---|---|
| **Channel** | Portal (rendered HTML) |
| **Trigger** | Customer clicks the contract link in `estimate.approved.email` (or admin-sent contract email) and lands on `/portal/contracts/{token}` |
| **Recipient** | Customer |
| **Sender (file:line)** | `frontend/src/features/portal/components/ContractSigning.tsx:1-264` |
| **Template** | React JSX (signature pad via `react-signature-canvas`) |

**Raw strings (visible to customer):**

- Header business name: `{contract.company_name ?? 'Grin's Irrigation'}` (line 158)
- Optional header `{contract.company_phone}` (line 161)
- Body label: `Prepared for` (line 170) + `{contract.customer_name}` (line 171)
- Body content: HTML via `dangerouslySetInnerHTML` from `contract.contract_body` (server-supplied; not in catalog scope)
- Section heading: `Terms & Conditions` (line 187) — only when terms are present
- Error alert: `We couldn't save your signature. Please try again or call us at the number above.` (line 204)
- Signature-pad label: `Your Signature` (line 211)
- Signature-pad clear CTA: `Clear` (line 216)
- Signature-pad placeholder: `Draw your signature here` (line 236)
- Submit CTA: `Sign Contract` (line 252)
- Signed-state body: `This contract was signed on {date}.` (line 257)
- **Expired-link state** (lines 115-127): heading `Link Expired`, body `This contract link has expired. Please contact the business for an updated link.`
- **Generic error state** (lines 129-141): heading `Unable to Load Contract`, body `We couldn't load this contract. The link may be invalid or expired.`

**Notes:** On successful sign, redirects to `portal.estimate_approval_confirmation.copy` with `action='signed'`.

---

### `portal.subscription_management.copy`

| | |
|---|---|
| **Channel** | Portal (rendered HTML) |
| **Trigger** | Customer clicks the manage-subscription link in `subscription.manage.email`, or navigates to `/portal/subscription/manage` directly |
| **Recipient** | Customer |
| **Sender (file:line)** | `frontend/src/features/portal/components/SubscriptionManagement.tsx:1-130` |
| **Template** | React JSX |

**Raw strings (visible to customer):**

- Card title: `Manage Your Subscription` (line 50)
- Form prompt: `Enter the email address associated with your subscription and we'll send you a link to manage your billing.` (lines 56-58)
- Email input placeholder: `your@email.com` (line 64)
- Submit CTA: `Send Login Email` (line 84) — or `Sending...` (line 81) while pending
- **Success state** (lines 91-105):
  - Heading: `Email Sent!`
  - Body: `We've sent a login link to <strong>{email}</strong>. Please check your inbox and spam folder.`
  - CTA: `Resend Email`
- **Error state:** server-supplied `errorMessage` (fallback `Something went wrong. Please try again.`), CTA `Try Again` (line 121)

**Notes:** This is a magic-link flow — the email itself (`subscription.manage.email`) carries the actual portal session URL.

---

### `portal.week_picker.copy`

| | |
|---|---|
| **Channel** | Portal (rendered HTML) |
| **Trigger** | Customer clicks the scheduling-poll link in a date-range SMS / email and lands on the week-picker step |
| **Recipient** | Customer |
| **Sender (file:line)** | `frontend/src/features/portal/components/WeekPickerStep.tsx:1-305` |
| **Template** | React JSX |

**Raw strings (visible to customer):**

- Heading: `Choose your preferred weeks` (line 148)
- Subhead: `Select the week you'd like each service performed, or choose "No preference" to let us assign the best available week.` (lines 149-152)
- Per-row service labels from `SERVICE_MONTH_RANGES` (lines 14-23): `Spring Startup`, `Mid-Season Inspection`, `Fall Winterization`, `Monthly Visit — May`, `Monthly Visit — June`, `Monthly Visit — July`, `Monthly Visit — August`, `Monthly Visit — September`
- Per-row CTAs: `Pick a week` / `No preference` (line 190)
- No-preference active label: `Assign for me` (line 163)
- Week trigger: `Week of {M/d/yyyy}` (line 272) — or placeholder `Select week` (line 273)

**Notes:** Each row independently togglable between "no preference" and a specific week-of date.

---

### `portal.onboarding_consent.copy`

| | |
|---|---|
| **Channel** | Portal (rendered HTML — server-rendered via FastAPI Jinja) |
| **Trigger** | Lead lands on the public signup / onboarding page |
| **Recipient** | Lead |
| **Sender (file:line)** | `src/grins_platform/api/v1/onboarding.py:61-69` |
| **Template** | Inline string constants returned by the endpoint |

**Raw strings (visible to lead):**

- SMS-consent attestation (lines 61-64): `I agree to receive SMS messages from Grin's Irrigations regarding my service agreement, appointments, and account updates.`
- Pre-sale disclosure (lines 66-69): `Pre-sale disclosure: By proceeding, you acknowledge the terms of service and consent to SMS communications from Grin's Irrigations.`

**Notes:** Both strings currently read `Grin's Irrigations` (plural with trailing `s`), inconsistent with `BUSINESS_NAME = "Grin's Irrigation"` (singular) at `services/email_service.py:51` and the rest of the catalog. Flagged for the broad SMS-polish pass; one-token fix in two strings.

---

## 7. Opt-in / opt-out auto-replies

These are sent verbatim via `_send_via_provider(bypass_consent=True)` and **do not** receive the `Grin's Irrigation: ` prefix or ` Reply STOP to opt out.` footer (carrier requirement: STOP confirmations must be unambiguous).

### `opt_out.confirmation.sms`

| | |
|---|---|
| **Trigger** | Inbound `STOP` / `QUIT` / `CANCEL` / `UNSUBSCRIBE` / `END` / `REVOKE` (case-insensitive, exact match) |
| **Sender** | `services/sms_service.py:1459` |
| **Constant** | `OPT_OUT_CONFIRMATION_MSG` — `services/sms_service.py:95` |

**Raw body (sent verbatim):**

```
You've been unsubscribed from Grin's Irrigation texts. Reply START to re-subscribe.
```

**Notes:** Idempotent — repeated STOPs do not re-send. Phone marked hard-STOP in `SmsConsentRecord`.

---

### `opt_in.confirmation.sms`

| | |
|---|---|
| **Trigger** | Inbound `START` / `UNSTOP` / `SUBSCRIBE` (case-insensitive) |
| **Sender** | `services/sms_service.py:1557` |
| **Constant** | `OPT_IN_CONFIRMATION_MSG` — `services/sms_service.py:101` |

**Raw body (sent verbatim):**

```
You're re-subscribed to Grin's Irrigation texts. Reply STOP to unsubscribe.
```

---

### `poll_reply.confirmed.sms`  (parsed scheduling-poll reply)

| | |
|---|---|
| **Trigger** | Inbound reply to a poll/reschedule SMS that successfully parses to a known option |
| **Sender** | `services/sms_service.py:1103` |
| **Constant** | `POLL_REPLY_CONFIRMED_MSG` — `services/sms_service.py:106` |

**Raw body:**

```
Thanks! We received your response: {option_label}. We'll be in touch to confirm your appointment.
```

**Sample:**

> Thanks! We received your response: Tuesday, May 20 at 2 PM. We'll be in touch to confirm your appointment.

---

### `poll_reply.unclear.sms`  (unparsed reply)

| | |
|---|---|
| **Trigger** | Inbound reply that doesn't match a poll option |
| **Sender** | `services/sms_service.py:1108` |
| **Constant** | `POLL_REPLY_UNCLEAR_MSG` |

**Raw body:**

```
Thanks for your reply! We received your message and will follow up shortly.
```

---

## 8. Compliance / regulatory index

Subset of the catalog above that exists specifically to meet a legal requirement. Wording in these messages should not be altered without legal review.

| Message | Regulation |
|---|---|
| `subscription.confirmation.email` | MN Statute 325G.56–325G.62 (auto-renewal) — Req 39B.3, 70.1–70.3 |
| `subscription.renewal_notice.email` | MN auto-renewal pre-notice — Req 39B.4 |
| `subscription.annual_notice.email` | MN Statute 325G.59 (annual disclosure) — Req 39B.5 |
| `subscription.cancellation_confirmation.email` | MN auto-renewal cancellation receipt — Req 39B.6 |
| `payment_reminder.sms.lien_warning` / `.email.lien_warning` | MN mechanic's-lien filing notice — Req 55.2–55.5 |
| `opt_out.confirmation.sms` / `opt_in.confirmation.sms` | TCPA + 10DLC carrier mandate |

---

## 9. What's intentionally not in this catalog

- **Internal staff alerts** (`INTERNAL_NOTIFICATION_EMAIL` / `INTERNAL_NOTIFICATION_PHONE`) — estimate decision notifications, lien-filing alerts, late-reschedule alerts, Resend bounce alerts. Not customer-facing.
- **Marketing / campaign SMS** — staff compose the body at send time in the campaign wizard. The system doesn't ship a fixed wording for these; merge fields (`{first_name}`, `{customer_first_name}`, etc.) are templated, but the body is whatever staff type.
- **Inbox direct-reply messages** — staff-typed conversational replies. Not templated.
- **Auth flows** (password reset, email verification, biometric/passkey enrollment) — none of these currently send customer-facing email or SMS. Auth in `services/auth_service.py` is staff-only today.

---

## 10. File-by-file index

| Type | Path |
|---|---|
| Email service | `src/grins_platform/services/email_service.py` |
| SMS service | `src/grins_platform/services/sms_service.py` |
| Notification service (appointments + invoices) | `src/grins_platform/services/notification_service.py` |
| Estimate service | `src/grins_platform/services/estimate_service.py` |
| Estimate follow-up cron | `src/grins_platform/services/estimate_follow_up_job.py` |
| Sales pipeline nudge cron | `src/grins_platform/services/sales_pipeline_nudge_job.py` |
| Job confirmation (Y/R/C lifecycle) | `src/grins_platform/services/job_confirmation_service.py` |
| Email templates | `src/grins_platform/templates/emails/*.html` (+ `.txt`) |
| Lead service | `src/grins_platform/services/lead_service.py` |
| Invoice service | `src/grins_platform/services/invoice_service.py` |
| Appointment service | `src/grins_platform/services/appointment_service.py` |
| Portal components (React) | `frontend/src/features/portal/components/*.tsx` |
| Onboarding endpoint (consent strings) | `src/grins_platform/api/v1/onboarding.py` |
