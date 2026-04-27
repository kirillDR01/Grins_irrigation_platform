# Build Plan — Phased Tasks

Phases run sequentially. Each phase is independently shippable to dev so that human + automated testing can validate before moving on.

## Phase 0 — Pre-build decisions (~1 day, mostly waiting on the user)

Block on `open-questions.md` answers. Critical answers needed before code:

- ~~**Q1** Email vendor confirmed (Resend?)~~ ✅ Resend, free tier (3K/mo, 100/day), confirmed 2026-04-25
- ~~**Q2** Production portal domain confirmed~~ ✅ `portal.grinsirrigation.com`, confirmed 2026-04-25
- ~~**Q3** Sender domain DNS access~~ ✅ User controls DNS, will add records directly, confirmed 2026-04-25
- ~~**Q4** Approve a test inbox for dev~~ ✅ `kirillrakitinsecond@gmail.com` + hard code-level allowlist guard, confirmed 2026-04-25
- ~~**Q5** Internal notification on approve/reject~~ ✅ Both email + SMS; dev → `kirillrakitinsecond@gmail.com` + `+19527373312`; prod TBD before cutover

No code in this phase.

## Phase 1 — Wire Resend into `_send_email` + email allowlist guard + token expiry update (~1 day)

**Goal:** Existing email methods (welcome, lead_confirmation, etc.) start actually delivering. Dev/staging cannot accidentally email a real customer.

Tasks:
1. Add `resend>=1.0.0` to `pyproject.toml`. Run `uv lock`.
2. **Build the email recipient allowlist guard** (mirrors `src/grins_platform/services/sms/base.py:18–92`):
   - Add `EmailRecipientNotAllowedError` exception class.
   - Add `_load_email_allowlist()` reading `EMAIL_TEST_ADDRESS_ALLOWLIST` env var, comma-separated. Empty/unset → returns `None` (production no-op).
   - Add `_check_email_allowlist(to_email)` called at the very top of `_send_email`, before any provider call. Normalize lowercase + strip whitespace before matching. Raise `EmailRecipientNotAllowedError` with a structured log line if blocked.
   - Decide: put in `email_service.py` directly, OR carve out `src/grins_platform/services/email/base.py` to match the SMS module structure. **Recommend in-file for now** — refactor only if a second provider lands.
3. Edit `EmailService._send_email` (line 157–195):
   - Call the allowlist guard first (raises before any I/O).
   - Replace the logger-stub body with `resend.Emails.send({...})` wrapped in try/except. Return False on failure and log `email.send.failed`.
   - Keep the existing "API not configured" early return so dev without a Resend key still works (allowlist still applies).
4. Edit `EmailService.__init__`:
   - `if self.settings.is_configured: resend.api_key = self.settings.email_api_key`
5. Edit `EmailSettings` (`email_config.py`):
   - Add `RESEND_API_KEY` alias (back-compat: still accept `EMAIL_API_KEY` as fallback).
6. Update `.env.example`:
   - `RESEND_API_KEY=` (commented with usage note)
   - `EMAIL_TEST_ADDRESS_ALLOWLIST=kirillrakitinsecond@gmail.com  # leave UNSET in production`
7. Add unit tests in `test_email_service.py`:
   - Allowlist guard: blocked recipient raises `EmailRecipientNotAllowedError`, allowed recipient does not.
   - Empty env var = no restriction (production path).
   - `resend.Emails.send` is called with the expected payload from a real send method like `send_lead_confirmation`.
8. **Token expiry update (Q7):** in `src/grins_platform/services/estimate_service.py`:
   - Change `TOKEN_VALIDITY_DAYS = 30` → `60` (line 48).
   - Change the `valid_until` default `timedelta(days=30)` → `timedelta(days=60)` (line 156) to keep the price-validity window aligned with the access-token window.
   - Update the docstring at line 111–112 referencing "30 days from now."
   - Update existing tests that hardcode 30-day expiry — search for `timedelta(days=30)` in `tests/` and adjust.

Validation:
- With `EMAIL_TEST_ADDRESS_ALLOWLIST=kirillrakitinsecond@gmail.com`, attempt to send a `welcome.html` to a dev-DB customer's email → should raise `EmailRecipientNotAllowedError`.
- With same env, send to `kirillrakitinsecond@gmail.com` → arrives in inbox, renders cleanly in Gmail.

## Phase 2 — Templates + `send_estimate_email` (~½ day)

**Goal:** A new `send_estimate_email` method exists and is unit-tested. No production wiring yet.

Tasks:
1. Create `src/grins_platform/templates/emails/estimate_sent.html`. Contents per `design.md` §3. Use the same Jinja2 base structure as `welcome.html` for visual consistency.
2. Create plain-text version `estimate_sent.txt` (Resend will use it as the alternative).
3. Add `send_estimate_email` method to `EmailService`:
   ```python
   def send_estimate_email(self, *, customer, estimate, portal_url) -> dict[str, Any]:
       ...
   ```
   - Pulls `customer.email` (or `lead.email` if customer is a Lead)
   - Renders both templates with context: `customer_name`, `total`, `valid_until`, `portal_url`, `business_*`
   - Calls `_send_email` with `email_type="estimate_sent"`, classification `TRANSACTIONAL`
4. Add `"estimate_sent"` to the `transactional_types` set in `_classify_email` (line 98–112).
5. Unit tests for `send_estimate_email` — happy path, missing-email path, render-failure path.

Validation:
- Manual render test (call from a Python REPL, inspect HTML).
- Send to test inbox, eyeball the result.

## Phase 3 — Wire into `EstimateService.send_estimate` + portal URL config (~½ day)

**Goal:** Hitting `POST /api/v1/estimates/{id}/send` actually delivers an email with a working portal link.

Tasks:
1. Add `portal_base_url` to `EmailSettings` (or new `PortalSettings`) per `design.md` §5. Backed by `PORTAL_BASE_URL` env var.
2. Wherever `EstimateService` is constructed (likely `api/v1/dependencies.py`), pass `settings.portal_base_url` instead of relying on the constructor default.
3. Edit `EstimateService.send_estimate` (`estimate_service.py:300–311`):
   - Replace the `estimate.email.queued` log with the actual `self.email_service.send_estimate_email(...)` call.
   - Add the same call in the `estimate.lead` fallback block below.
   - Wrap in try/except like the SMS branch already does.
4. Update `.env.example` with `PORTAL_BASE_URL=http://localhost:5173`.
5. Update existing tests:
   - `tests/functional/test_estimate_operations_functional.py:164` — keep the inline `portal_base_url` for now; add a new test that asserts `send_estimate_email` is called.
6. Verify in dev:
   - Create an estimate via the admin UI for a test customer (test inbox)
   - Click "Send"
   - Receive email
   - Click the link — lands on the portal page
   - Approve — confirm DB row updated and lead tag changed

Validation:
- E2E test in dev environment with the test inbox per `feedback_email_test_inbox.md`.

## Phase 4 — Optional polish (~1 day total, individually small)

Pick the ones that are worth shipping in v1 vs. punting.

| Task | Size | v1 / v2 |
|---|---|---|
| Transition `SENT → VIEWED` in `get_portal_estimate` (`design.md` §7 option B) | XS | v1 |
| **Internal notification (email + SMS) to sales team on approve/reject** — see `design.md` §6.1. Adds `_notify_internal_decision` to `EstimateService`, `send_internal_estimate_decision_email` to `EmailService`. Two env vars: `INTERNAL_NOTIFICATION_EMAIL`, `INTERNAL_NOTIFICATION_PHONE`. Dev defaults set; prod recipients gathered before Phase 5 cutover. | M | v1 |
| **Resend webhook handler for bounces (Q10)** — new endpoint `POST /api/v1/webhooks/resend` with signature verification (`RESEND_WEBHOOK_SECRET`). On `email.bounced` event: fire internal email + SMS to staff (reuses Q5's recipient env vars). Add `Customer.email_bounced_at` column (nullable timestamptz) — soft-flag only, doesn't block future sends. | M | v1 |
| **`Reply-To: info@grinsirrigation.com` header** on outgoing estimate emails (Q6 belt-and-suspenders) | XS | v1 |
| Rate limiting on `/portal/estimates/*` (`design.md` §1.1) | S | v1 |
| "Email opened" pixel (Resend supports it) — write `last_opened_at` on Estimate | S | v2 |
| Resend the email from admin UI ("Resend estimate" button) | S | v2 if SMS resend doesn't already cover it |

## Phase 5 — Production cutover (~½ day + email-host setup)

Pre-flight questions (gather from user before deploy):
- Production values for `INTERNAL_NOTIFICATION_EMAIL` and `INTERNAL_NOTIFICATION_PHONE`.

Tasks:
1. Configure Resend production API key in production env vars.
2. Configure DNS on `grinsirrigation.com`:
   - SPF (TXT)
   - DKIM (1–2 CNAMEs from Resend dashboard)
   - DMARC (TXT)
   - `portal` CNAME / A record pointing at the React deployment
3. Verify sender domain in Resend dashboard.
4. Configure Resend webhook endpoint URL → `https://api.grinsirrigation.com/api/v1/webhooks/resend` (or whatever the prod API host is). Copy the webhook signing secret into prod env as `RESEND_WEBHOOK_SECRET`.
5. **Set up `noreply@grinsirrigation.com` mailbox + auto-responder (Q6):**
   - Create the `noreply@` mailbox in the user's email host (Google Workspace or equivalent).
   - Enable vacation/auto-responder with the body from `open-questions.md` Q6.
   - Verify by sending a test reply to a noreply@ message.
6. Set prod env vars: `PORTAL_BASE_URL=https://portal.grinsirrigation.com`, `INTERNAL_NOTIFICATION_EMAIL=<user-provided>`, `INTERNAL_NOTIFICATION_PHONE=<user-provided>`, `RESEND_WEBHOOK_SECRET=<from Resend dashboard>`.
7. Confirm `EMAIL_TEST_ADDRESS_ALLOWLIST` is **NOT** set in prod env (guard must be a no-op there).
8. Confirm `SMS_TEST_PHONE_ALLOWLIST` is **NOT** set in prod env (existing rule).
9. Deploy.
10. Send a single internal-team test estimate end-to-end before any real customer. Verify approve flow, internal notification, and a deliberately-bounced email triggers the bounce notification.
11. Monitor first 5–10 customer sends; check Resend dashboard for delivery + bounces.

## Total estimate

- **Phase 1–3 (must-haves):** 1.5 days of focused engineering, plus ~1 day of waiting on DNS / vendor setup.
- **Phase 4 v1 polish:** +1 day if all picked.
- **Phase 5 cutover:** ½ day.
- **End-to-end realistic timeline:** 3–4 days from kickoff if questions are answered same-day; 1 week if DNS or vendor decisions take longer.

This is small because the heavy lifting was already done — schema, portal endpoints, frontend route, admin send button. We are filling a single gap.
