# Gap 06 — Opt-out Management & Visibility

**Severity:** 2 (high — compliance-adjacent)
**Area:** Backend (opt-out processing) + UI (customer & appointment surfaces)
**Status:** Investigated, not fixed
**Related files:**
- `src/grins_platform/services/sms_service.py` — opt-out exact-keyword handler + `_flag_informal_opt_out`
- `src/grins_platform/models/sms_consent_record.py:31-132` — `SmsConsentRecord`
- `src/grins_platform/models/alert.py:28-121` — `Alert` model + enum
- `frontend/src/features/customers/components/CustomerDetail.tsx:109-114` — `sms_opt_in` form field
- `frontend/src/features/schedule/components/AppointmentDetail.tsx` — missing opt-out indicator

---

## Summary

Opt-out handling has two branches:

1. **Exact-keyword opt-out (STOP, QUIT, CANCEL, UNSUBSCRIBE, END, REVOKE):** a new `SmsConsentRecord(consent_given=False, opt_out_method='text_stop')` row is inserted. The customer is opt-out compliant. Subsequent outbound sends should be blocked.

2. **Informal opt-out ("stop texting me", "please don't contact", "take me off your list"):** an `Alert(alert_type='INFORMAL_OPT_OUT')` is created for admin review. **No consent record is written.** The customer is *not* actually opted out until admin manually acts.

Two gaps follow:

- **6.A:** No UI to triage informal opt-outs. The Alert is created, but there's no dashboard widget, queue page, or list view for this alert type (see Gap 14). Admins may never see these. Meanwhile, the system continues to send SMS to customers who have explicitly asked not to be contacted.

- **6.B:** Opt-out status is invisible in almost every UI surface where it should be visible — calendar cards, appointment detail modal, no-reply review queue, reschedule requests queue, scheduling form. Admins can send a "Send Reminder SMS" to an opted-out customer without any warning.

---

## 6.A — Informal opt-out has no triage UI

### Current behavior

In `sms_service.py`, the inbound handler (`handle_inbound`, around line 587-887) tries pattern matching in this order:

1. Exact opt-out keywords → `_process_exact_opt_out()`:
   - Insert `SmsConsentRecord(consent_given=False)`.
   - Send opt-out confirmation SMS ("You have been unsubscribed...").
   - Future outbound to that phone is blocked by consent check.

2. Informal opt-out phrases → `_flag_informal_opt_out()`:
   - Create `Alert(alert_type='INFORMAL_OPT_OUT', severity='warning', entity_type='customer', entity_id=customer_id, message='Customer may have requested opt-out: [raw body]')`.
   - **No `SmsConsentRecord` written.**
   - **No auto-response SMS sent** (avoids automating a decision that needs human review).

The Alert lands in `alerts` table. The dashboard `GET /api/v1/alerts?acknowledged=false` endpoint returns it. But:
- **No dashboard widget filters for `alert_type='INFORMAL_OPT_OUT'`.**
- **No dedicated page.** The only UI that lists alerts is the dashboard's generic `AlertCard` component, which is purpose-built per alert type — and this type isn't wired.
- **No badge/count visible** anywhere admin-facing.

Result: the Alert row exists, but admins have no way to see it unless they query the DB directly.

### Why this is a compliance issue

- 10DLC messaging best practice (and some carrier-specific rules) expect operators to honor informal opt-out signals. If a customer says "stop texting me" and the operator continues sending, that's a grey-area compliance violation.
- CTIA Short Code Monitoring Handbook requires operators to treat "reasonable variations" of STOP as opt-outs.
- Our current behavior: the customer's informal request is logged to a table no one reads, and we keep texting.

### Proposed fix

1. **Dashboard widget for informal-opt-out alerts.** Add an `AlertCard` variant on the dashboard: *"N customers may have requested opt-out — review."* Click → navigates to a new `/alerts/informal-opt-out` list page.

2. **New review page:** `InformalOptOutQueue.tsx`. Columns:
   - Customer name, phone, raw body of the informal message, timestamp, alert_id.
   - Per-row actions:
     - **Confirm opt-out** → write `SmsConsentRecord(consent_given=False, opt_out_method='admin_confirmed_informal', alert_id=X)` → acknowledge the Alert → send a one-time "You've been unsubscribed" SMS.
     - **Dismiss** → acknowledge the Alert → no consent change → log `AuditLog(action='informal_opt_out.dismissed')`.
     - **Call customer** → mark Alert as "pending" (new sub-state) until admin returns.

3. **Auto-suppression window.** Between alert creation and admin action, *pause* all non-urgent outbound SMS to that phone number. An in-flight confirmation for an imminent appointment should still go (transactional / urgent tier), but promotional, reminder, and review-request SMSes should be held until resolution. This is a middle ground that protects the customer without auto-deciding compliance.

4. **Audit.** As noted in Gap 05, write an `AuditLog` entry for both the initial flag and any admin action.

### Edge cases
- Customer sends informal opt-out, then 5 minutes later sends a Y to an appointment confirmation. The Y still processes (it's a direct response to a transactional message), but the alert should stay open — the admin should still review whether to unsubscribe the customer from everything except transactional.
- Customer sends informal opt-out, then sends STOP minutes later. Exact opt-out processes normally; Alert should auto-acknowledge (since the customer has clarified their intent via the exact keyword).

---

## 6.B — Opt-out status invisible in operational UI

### Reproduction

1. Customer has `SmsConsentRecord` with `consent_given=False` as of last week.
2. Admin opens the Schedule calendar, picks today's date, sees this customer's appointment as a draft.
3. Admin clicks the card → AppointmentDetail modal opens. **No opt-out badge.**
4. Admin clicks "Send Confirmation" → backend refuses (consent check), returns an error toast.
5. Admin confused: clicks customer name → CustomerDetail page opens → sees "SMS Opt In: off" buried in the communication preferences section (line 107-114 of `CustomerDetail.tsx`).

Even best case: the admin gets a toast error. Worst case: they retry, or assume it's a transient error.

### Current UI surfaces & their opt-out visibility

| Surface | File | Shows opt-out? |
|---|---|---|
| Calendar card | `CalendarView.tsx` | **No** — only prepaid/attachment badges |
| AppointmentDetail modal | `AppointmentDetail.tsx` | **No** — no indicator, no warning |
| NoReplyReviewQueue | `NoReplyReviewQueue.tsx` | **No** — will happily prompt "Send Reminder" even if opted out |
| RescheduleRequestsQueue | `RescheduleRequestsQueue.tsx` | **No** |
| CustomerDetail | `CustomerDetail.tsx:109-114` | Partially — shows `sms_opt_in` boolean in a form, not as a visible badge |
| CustomerMessages | `CustomerMessages.tsx` | **No** — shows message history without noting the customer can't receive new ones |
| AppointmentForm (create) | Schedule tab | **No** — staff can create appointments without any "this customer cannot receive SMS" hint |

There's no history display of:
- **When** the opt-out happened (the consent record has `opt_out_timestamp` but no UI reads it).
- **Why** / how (text STOP vs. admin-set vs. informal confirmation — `opt_out_method` captures this but no UI shows it).
- Whether there's a pending informal-opt-out Alert still open.

### Proposed fix

1. **Customer-level badge component** — `<OptOutBadge customer={...} />` — renders a red/amber pill with a tooltip showing: "Opted out via [method] on [date]. Reason: [raw_body snippet if informal]." Used in every UI surface above.

2. **Pre-flight disabled state on action buttons.** "Send Confirmation", "Send Reminder SMS", "Google Review" buttons should be disabled if the customer has opted out, with a tooltip explaining why. The disabled state is driven by a consent check query (cache 30s).

3. **Confirm-before-send pattern for edge cases.** For transactional messages where legal/business reason justifies sending (e.g., job completion receipt), require admin to tick an acknowledgment: "I understand this customer has opted out. This is a transactional notification only."

4. **History section in CustomerDetail.** Show the opt-out history: a chronological list of `SmsConsentRecord` rows with consent_given/timestamp/method. This replaces the hidden boolean with a real timeline.

### Edge cases
- Customer had a previous opt-out, then texted "start" to re-subscribe — the consent history should show both events, and the current state should be derived from the most recent.
- Lead vs. customer: `SmsConsentRecord` can reference either. Ensure the opt-out badge renders in lead contexts too.
- Multiple phone numbers on one customer: consent is per phone. If the customer has 2 phones and 1 is opted out, the UI should be clear about which phone is blocked.

---

## Cross-references
- **Gap 05** — audit log coverage for opt-outs is a prerequisite for a useful opt-out history view.
- **Gap 11** — appointment detail needs the opt-out badge as part of the broader inbound-visibility effort.
- **Gap 12** — calendar cards need a second indicator slot (same place as the reschedule-pending badge).
- **Gap 14** — the informal-opt-out alert needs dashboard surfacing.
