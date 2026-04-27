# Open Questions

These need answers from the user before Phase 1 of `build-plan.md` starts. Roughly ordered by blocking-power.

## Q1. Email vendor — ✅ ANSWERED

**Decision (2026-04-25):** **Resend**, starting on the free tier (3,000 emails/mo, 100/day cap, no expiration). User confirmed monthly volume is well under 3,000 emails. Upgrade to Pro $20/mo if we ever hit either cap. Full rationale in [`vendor-decision.md`](vendor-decision.md).

## Q2. Production portal domain — ✅ ANSWERED

**Decision (2026-04-25):** **`portal.grinsirrigation.com`**. Subdomain of the existing business domain. Builds anti-spam trust signal (link domain matches sender domain), keeps marketing site on the root, and matches the closest to the existing hardcoded `portal.grins.com` default so the code change is minimal.

**Setup actions for Phase 5 (production cutover):**
1. Add `portal` CNAME (or A record) on `grinsirrigation.com` DNS pointing at the React app deployment.
2. Provision TLS cert (Let's Encrypt auto, or whatever the deploy host issues).
3. Set `PORTAL_BASE_URL=https://portal.grinsirrigation.com` in production env.

## Q3. DNS access for `grinsirrigation.com` — ✅ ANSWERED

**Confirmed (2026-04-25):** User controls the `grinsirrigation.com` domain and can add records directly. No external contractor in the loop.

**Records to add during Phase 5 cutover** (Resend dashboard generates the exact values):
- SPF: `TXT @ "v=spf1 include:resend.io ~all"` (or merged into existing SPF if there is one)
- DKIM: 1–2 CNAME records pointed at Resend's signing keys
- DMARC: `TXT _dmarc "v=DMARC1; p=quarantine; rua=mailto:dmarc@grinsirrigation.com"`
- `portal` CNAME or A record (per Q2 answer)

No longer the schedule-risk it was — same-day turnaround is realistic.

## Q4. Test inbox for dev / staging — ✅ ANSWERED + UPGRADED TO HARD GUARD

**Decision (2026-04-25):**
- **Test inbox:** `kirillrakitinsecond@gmail.com`.
- **Hard requirement:** Implement a code-level email allowlist mirroring the existing `SMS_TEST_PHONE_ALLOWLIST` guard at `src/grins_platform/services/sms/base.py:18–92`. In dev and staging, attempts to send to any address other than the allowlist must be refused before any network I/O to Resend, with a raised `EmailRecipientNotAllowedError` and a structured log line. Production leaves the env var unset → guard is a no-op there.

**Implementation (now a Phase 1 task in `build-plan.md`):**
- New env var `EMAIL_TEST_ADDRESS_ALLOWLIST` (comma-separated, default empty).
- New exception `EmailRecipientNotAllowedError` in `email_service.py` (or `services/email/base.py` to match the SMS module structure).
- Guard called at top of `EmailService._send_email` before the Resend SDK call.
- Normalize on lowercase + strip whitespace.
- Dev / staging `.env` ships with `EMAIL_TEST_ADDRESS_ALLOWLIST=kirillrakitinsecond@gmail.com`.
- Production `.env` does NOT set the var.
- Add to `.env.example` with the same comment style as the SMS allowlist.

**Why this is a hard guard, not just a convention:** The dev database contains real customer records. A bug in test code that walks the customer table and fires an email would reach the actual customer. The SMS rule already prevents that for SMS — email needs the same enforcement, especially the moment Resend is actually plugged in and `_send_email` stops being a logger stub.

## Q5. Sales-team notification on approve / reject — ✅ ANSWERED

**Decision (2026-04-25):** Send **both** an internal email **and** an internal SMS when a customer approves or rejects an estimate.

| Env | Internal email recipient | Internal SMS recipient |
|---|---|---|
| Dev / staging | `kirillrakitinsecond@gmail.com` | `+19527373312` |
| Production | TBD (user will provide before Phase 5 cutover) | TBD (user will provide before Phase 5 cutover) |

**Implementation (Phase 4 v1 task in `build-plan.md`):**
- Two new env vars: `INTERNAL_NOTIFICATION_EMAIL`, `INTERNAL_NOTIFICATION_PHONE`. Both empty in code default; dev `.env` ships with the values above.
- New method on `EstimateService`: `_notify_internal_decision(estimate, decision)` called at the end of `approve_via_portal` and `reject_via_portal` after the DB update commits.
- Failures (vendor outage, no recipients configured) are logged but **do not** undo the customer-side decision — never roll back an approval because the staff notification failed.
- Subject for approve: `Estimate APPROVED for {customer_name}` — body includes total, link to admin estimate detail, "ready to send for signature."
- Subject for reject: `Estimate REJECTED for {customer_name}` — body includes the customer's reason if provided.
- Both notifications are subject to the existing dev allowlists (email allowlist from Q4, SMS_TEST_PHONE_ALLOWLIST). Since `+19527373312` and `kirillrakitinsecond@gmail.com` are already on those lists, no extra wiring needed.

**Open follow-up before Phase 5:** Get the production email + phone recipients from the user.

## Q6. Reply handling for `noreply@` — ✅ ANSWERED

**Decision (2026-04-25):** Auto-respond. The auto-reply tells the customer to use the link; if they're still stuck, to call.

**Implementation (Phase 5 task — email infrastructure, not Python code):**
- Set up `noreply@grinsirrigation.com` as a real mailbox in the user's email host (Google Workspace, etc.).
- Enable vacation/auto-responder on that mailbox with a body like:
  > "Thanks for your reply. To approve or reject your estimate, please use the **Review your estimate** link in the original email. If you're having trouble with the link or have questions, call us at (952) 818-1020. — Grin's Irrigation"
- **Belt-and-suspenders:** also set `Reply-To: info@grinsirrigation.com` on outgoing estimate emails so any reply that somehow bypasses the auto-responder still reaches a monitored inbox.

The auto-responder is a one-time domain-admin setup, not part of the code build. Tracked in Phase 5 cutover.

## Q7. Token expiry — ✅ ANSWERED

**Decision (2026-04-25):** **60 days.**

**Implementation (Phase 1 task):** Update `TOKEN_VALIDITY_DAYS = 60` at `estimate_service.py:48`. Also update the matching `valid_until` default at `estimate_service.py:156` from `now + 30d` to `now + 60d` so the access token and the price-validity window stay aligned (otherwise a customer could view at day 45, see a "valid until" date that already passed, and still be able to approve).

If user later wants the two to diverge (e.g., longer access window than price guarantee), that's a one-line change.

## Q8. Auto-create SignWell document on approval? — ✅ ANSWERED

**Decision (2026-04-25):** **Manual.** Sales rep sees the internal notification (per Q5), clicks "send for signature" themselves. No automatic SignWell document creation on approval.

## Q9. Volume sanity check — ✅ ANSWERED (partial)

**Confirmed (2026-04-25):** monthly email volume well under 3,000. That's enough to lock the vendor decision (Q1 → Resend free tier) but the exact estimate count and seasonal peak shape are still unknown. Not blocking. Revisit if/when we approach the 100/day or 3,000/mo cap.

## Q10. Bounce / suppression handling — ✅ ANSWERED, promoted to v1

**Decision (2026-04-25):** When a customer email hard-bounces, fire an internal notification to staff so they can follow up by phone. **This is now a v1 requirement, not v2.**

**Implementation (Phase 4 v1 task in `build-plan.md`):**
- New endpoint: `POST /api/v1/webhooks/resend` that receives Resend webhook events.
- Verify webhook signature using Resend's signing secret (env: `RESEND_WEBHOOK_SECRET`).
- Handle event type `email.bounced` (and `email.complained` for spam-reports as a bonus).
- For each bounce, look up the original recipient + email_type from the event payload, then call the same `_notify_internal_decision`-style helper as Q5: send an internal email + SMS to staff with subject `Estimate email BOUNCED for {customer_email}` and the bounce reason.
- Optionally mark the customer record with `email_bounced_at = now`, so future estimate sends to that customer log a warning. **Recommendation:** add the column but only flag soft — don't block sends; the staff member needs to know but a transient bounce shouldn't permanently disable a customer.
- Reuse the existing internal-notification recipient env vars (`INTERNAL_NOTIFICATION_EMAIL`, `INTERNAL_NOTIFICATION_PHONE` from Q5).

**Why v1 not v2:** Estimates are a high-value moment. A silent delivery failure means the customer never sees the estimate, the rep doesn't know to call, and the deal goes cold. The cost of building this is one webhook endpoint (~½ day), well worth it.

---

## Answers (to be filled in)

| Q | Answer | Date | Confirmed by |
|---|---|---|---|
| Q1 | Resend, free tier to start (3K/mo, 100/day) | 2026-04-25 | user |
| Q2 | `portal.grinsirrigation.com` | 2026-04-25 | user |
| Q3 | User controls DNS, will add records directly | 2026-04-25 | user |
| Q4 | `kirillrakitinsecond@gmail.com` + hard code-level allowlist guard | 2026-04-25 | user |
| Q5 | Internal email + SMS; dev → kirillrakitinsecond@gmail.com + +19527373312; prod TBD | 2026-04-25 | user |
| Q6 | Auto-respond on noreply@ pointing to link, fall-back to phone | 2026-04-25 | user |
| Q7 | 60 days (extending both token and valid_until defaults) | 2026-04-25 | user |
| Q8 | Stay manual — rep clicks send-for-signature after internal notification | 2026-04-25 | user |
| Q9 | Volume confirmed under 3K emails/mo (vendor sizing only) | 2026-04-25 | user |
| Q10 | v1 — fire internal email+SMS to staff on hard bounce via Resend webhook | 2026-04-25 | user |
