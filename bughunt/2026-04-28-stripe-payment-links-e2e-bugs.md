# Stripe Payment Links (Architecture C) — E2E bug hunt — 2026-04-28

End-to-end validation run of the Stripe Payment Links flow against the dev
Vercel admin dashboard + Railway backend, per
`.agents/plans/stripe-tap-to-pay-and-invoicing.md` Phase 6 §End-to-end manual
validation.

Deployments:
- **Backend:** Railway `Grins-dev` deployment `1f1c4096-5abe-472f-b70e-580792c38148`
  (commit `102df83`, SUCCESS after the fix below).
- **Frontend:** Vercel `grins-irrigation-platform-git-dev-kirilldr01s-projects.vercel.app`
  (commit `4796376`, READY at run time).

Base URLs:
- API: https://grins-dev-dev.up.railway.app
- FE:  https://grins-irrigation-platform-git-dev-kirilldr01s-projects.vercel.app

Auth: `admin` / `admin123`. SMS safety:
`SMS_TEST_PHONE_ALLOWLIST=+19527373312,+19528181020`. Email safety:
`EMAIL_TEST_ADDRESS_ALLOWLIST=kirillrakitinsecond@gmail.com`.

Screenshots: `e2e-screenshots/payment-links-architecture-c/00..11-*.png` (13
files).

Seeded fixtures (from `scripts/seed_e2e_payment_links.py`):
- customer `a44dc81f-ce81-4a6f-81f5-4676886cef1a` (reused via phone lookup)
- $50 invoice `7070645d-0c89-44a5-92c9-3da84c49980c` with auto-attached
  Stripe Payment Link `plink_1TRMsgQDNzCTp6j5755egJj6` →
  `https://buy.stripe.com/test_dRmeVfdmgc367vK9iqeQM0o`
- $0 invoice `e16d9b61-ff14-48b1-a716-52bef9d33c65` (F11 hide test)
- appointment `99327c38-8388-4e49-b152-76714dfbc1af` (in_progress)

---

## Summary

| # | Severity | Title | Status |
|---|----------|-------|--------|
| 1 | **P0 (blocker)** | Alembic multi-head: `4796376` deploy crashed Railway dev | **FIXED** in `102df83` |
| 2 | **P1** | `send_payment_link` raises 500 on email-allowlist hard-block (should be 422) | open |
| 3 | **P1** | `send_payment_link` SMS soft-fail path falls through to email even when SMS is the customer's allowlisted channel | open |
| 4 | **P2** | CORS headers missing on 5xx responses → frontend sees opaque "Network Error" instead of the real status | open |
| 5 | **P2** | `seed_e2e_payment_links.py` reuses a customer found by phone but doesn't refresh email/opt-ins; bypasses the dev allowlist check unintentionally | open |
| 6 | **P3** | `e2e/payment-links-flow.sh` Journey 1 clicks the *first* `.fc-event` rather than the seeded appointment, so it tests an unrelated invoice and masks the seeded-invoice failure | open |
| 7 | **P3** | Build-meta drift: latest deploy reports `serviceManifest.build.builder = "RAILPACK"` even though Railway still consumed the in-repo `Dockerfile` to build (cosmetic, but makes future "did anyone change Railway's builder?" audits harder) | open |

---

## Bug 1 — Alembic multi-head crashed dev backend  ★ FIXED

**Severity:** P0 — production-equivalent. Whole dev backend was down (HTTP 502
on every endpoint) until fixed.

**Symptom:** Railway dev deployment `05d1bc9f` (commit `4796376` —
*"fix(payments): widen sent_messages CHECK to include 'payment_link'"*) was
**CRASHED**. Subsequent calls to `/health`, `/api/v1/healthcheck`, and any API
path returned `502 Bad Gateway`. The previous good deployment had been
removed, so there was no failover.

**Root cause:** The repo had **two simultaneous Alembic heads**:

```
20260501_120000 ──┬── 20260428_140000 ── 20260428_150000  (head — Phase 2)
                  └── 20260502_100000                       (head — Phase 6 fix)
```

Both descended from `20260501_120000`, neither merged. On startup the entrypoint
ran `alembic upgrade head` and Alembic refused with:

```
ERROR [alembic.util.messaging] Multiple head revisions are present for given
argument 'head'; please specify a specific target revision, '<branchname>@head'
to narrow to a specific head, or 'heads' for all heads
```

…in a tight retry loop (12+ failures captured in the build logs before the
container gave up).

**Fix:** No-op merge revision committed and pushed.
`src/grins_platform/migrations/versions/20260502_120000_merge_payment_link_branches.py`
(commit `102df83`). New deploy `1f1c4096` came up SUCCESS; deploy logs confirm:

```
INFO [alembic.runtime.migration] Running upgrade 20260428_150000,
     20260502_100000 -> 20260502_120000, Merge two heads created during the
     payment-link work.
```

**Why this slipped through:** the Phase 6 fix migration was authored in
isolation against a single-head local checkout; the developer didn't run
`uv run alembic heads` before pushing, and there's no pre-commit/CI gate that
asserts a single head. **Recommendation:** add a pre-push or CI step that
fails on `alembic heads | wc -l > 1`.

---

## Bug 2 — `send_payment_link` returns 500 on email-allowlist guard

**Severity:** P1 — user-visible 500. Surfaces in the live UI as a *"Send
failed — Network Error"* toast (see screenshot
`05b-invoice-detail-sent.png`).

**Reproduction (recorded in this run):**

```bash
$ TOKEN=$(curl ... /api/v1/auth/login | jq -r .access_token)
$ curl -X POST -H "Authorization: Bearer $TOKEN" \
    https://grins-dev-dev.up.railway.app/api/v1/invoices/7070645d.../send-link
Internal Server Error
[HTTP 500]
```

**Backend trace (full Exception Group in Railway logs):**

```
File "/app/src/grins_platform/api/v1/invoices.py", line 749, in send_payment_link
    return await service.send_payment_link(invoice_id)
File "/app/src/grins_platform/services/invoice_service.py", line 1002, in send_payment_link
    sent = self.email_service._send_email(
        to_email=customer.email,
        ...
    )
grins_platform.services.email_service.EmailRecipientNotAllowedError:
    recipient_not_in_email_allowlist: provider=resend (set
    EMAIL_TEST_ADDRESS_ALLOWLIST to override for dev/staging; leave unset in
    production)
```

**Root cause:** at `services/invoice_service.py:1002`, `_send_email` is called
synchronously inside a `try`-less block. The dev/staging email-allowlist guard
raises `EmailRecipientNotAllowedError` (good — that's what we want it to do),
but the caller doesn't catch it and it propagates all the way out to the FastAPI
handler at `api/v1/invoices.py:749`, which has no specific handler for it
either, so Starlette's error middleware emits a generic 500.

The plan's edge-case 8 explicitly says:

> *"SMS provider hard-fails — fallback to Resend email (D6). If both fail
> (no phone, no email, OR provider outage), endpoint returns 422
> `NoContactMethodError`."*

So the spec'd contract for an unsendable customer is **422 + structured error
body**, not 500. The same path also raises `NoContactMethodError` four lines
later (line 1020) when `customer.email` is null — that branch *would* return
the correct 422. The bug is purely the missing `try/except` around the
`_send_email` call.

**Suggested fix (1-liner-ish):**

```python
# services/invoice_service.py around line 1002
try:
    sent = self.email_service._send_email(...)
except EmailRecipientNotAllowedError:
    self.logger.warning(
        "payment.send_link.email_blocked_by_allowlist",
        invoice_id=str(invoice.id),
        recipient_last4=customer.email[-4:] if customer.email else None,
    )
    sent = False
if sent:
    return await self._record_link_sent(invoice, channel="email")
```

…and let the existing `NoContactMethodError` raise on line 1020. That makes
the API return the 422 the spec calls for, and the toast becomes the
already-implemented *"Cannot send: customer has no phone or email."* warning.

**Tests to add (per S1 three-tier rule):**
- Unit: `test_send_payment_link_email_allowlist_blocked_returns_no_contact`
- Integration: hit `/send-link` against a customer whose email is outside the
  allowlist; assert 422 with `error_code = "no_contact_method"`.

---

## Bug 3 — SMS soft-fail falls through to email even when SMS is the
intended dev channel

**Severity:** P1 — masks bug 2 in normal dev runs and produces confusing
"why is dev sending email when I set SMS allowlist?" behavior.

**Symptom:** Two consecutive sends to the same customer in this run:

```
POST /api/v1/invoices/34697927-.../send-link    HTTP 200 OK   (modal)   ← SMS path
POST /api/v1/invoices/7070645d-.../send-link    HTTP 500     (detail)   ← email path
```

Same customer (`a44dc81f`), same phone (`9527373312` → canonical
`+19527373312`, in `SMS_TEST_PHONE_ALLOWLIST`). The first call succeeded via
SMS. The second call, ~2 seconds later, took the *email fallback* path, which
then tripped bug 2.

**Most likely cause:** CallRail (or the wrapping `SMSService`) is rate-limiting
two outbound transactional sends to the same number within the same second.
The `send_payment_link` SMS branch logs `payment.send_link.sms_failed_soft`
on `result["success"] is False` (line 978–982 of `invoice_service.py`) and
silently falls through. Verifying the warning was actually emitted requires
re-running with `LOG_LEVEL=DEBUG` on Railway — not done in this session.

**Why it's a P1, not just "expected fallback":** in dev, where the SMS
allowlist is set explicitly to make SMS testable, falling through to email
is almost never what we want. We should at least surface *why* SMS failed
in the API response so the caller (or the test harness) can distinguish
"customer hard-STOP'd" from "rate limit".

**Suggested fix:**
1. Make the `SendPaymentLinkResponse` carry an `attempted_channels` field
   (already partially structured for this in `types.SendPaymentLinkResponse`):

   ```ts
   { channel: "sms", attempted_channels: ["sms"], ... }   // happy path
   { channel: "email", attempted_channels: ["sms", "email"], sms_failure_reason: "rate_limit", ... }
   ```

2. Surface the `sms_failure_reason` in the modal/detail toast — *"Sent via
   email (SMS rate-limited; will retry shortly)"* is much better dev
   ergonomics than the current silent fallthrough.

3. Optional: when `ENVIRONMENT=development` and the customer phone is in
   the SMS allowlist, **don't** fall through to email on transient SMS
   failures — surface them. That keeps the dev test loop honest about what
   the SMS provider is doing.

---

## Bug 4 — CORS headers absent on 5xx responses

**Severity:** P2 — doesn't change the underlying bug, but actively hides it
from frontend developers and forces a server-side investigation every time.

**Symptom (browser console captured in
`e2e-screenshots/payment-links-architecture-c/console.log`):**

```
Access to XMLHttpRequest at
'https://grins-dev-dev.up.railway.app/api/v1/invoices/7070645d.../send-link'
from origin 'https://grins-irrigation-platform-git-dev-kirilldr01s-projects.vercel.app'
has been blocked by CORS policy: No 'Access-Control-Allow-Origin' header is
present on the requested resource.
Network error - no response received
Failed to load resource: net::ERR_FAILED
```

The actual backend response is HTTP 500 with a body. But because Starlette's
`ServerErrorMiddleware` runs *before* `CORSMiddleware` for unhandled exceptions,
the error response goes out without CORS headers. Browsers then refuse to
expose the response — the frontend's axios interceptor sees `error.response =
undefined` and falls back to its generic *"Network Error"* string.

**Root cause:** middleware ordering in `app.py` (or wherever the FastAPI app
is constructed). The fix is one of:

1. Add `CORSMiddleware` *outside* (added later than) `ServerErrorMiddleware`
   so CORS headers wrap even crash responses, OR
2. Catch broad exceptions in a top-level handler and return a JSON 500 with
   the CORS headers via `JSONResponse(...)` (FastAPI/Starlette will then
   honor the CORS middleware).

Either way, fixing this means a real 500 will say "500" in the browser
console, and the frontend's *"Send failed — {reason}"* toast can show the
actual server-provided reason instead of *"Network Error."*

**Audit value:** this same pattern silently hides every other backend 500
from the frontend, not just this endpoint. Worth fixing once globally.

---

## Bug 5 — `seed_e2e_payment_links.py` reuses a customer without
re-asserting the email/opt-ins

**Severity:** P2 — quietly corrupts the test conditions for any follow-up
flow that depends on the email allowlist.

**Symptom:** seeder output:

```
# customer a44dc81f-ce81-4a6f-81f5-4676886cef1a (reused)
```

Looking up the customer:

```
{
  "id": "a44dc81f-...",
  "first_name": "Test",
  "last_name":  "User",
  "phone": "9527373312",
  "email": "test-mock@example.com",   ← NOT in EMAIL_TEST_ADDRESS_ALLOWLIST
  "email_opt_in": false
}
```

The seeder's *create* path sets `email=kirillrakitinsecond@gmail.com` and
`email_opt_in=True`, but the *reuse* branch (when phone lookup hits) does
nothing. So once *any* previous run created a customer with this phone but
a different email, every subsequent E2E run inherits the wrong email and
silently breaks the email-fallback assertion.

**Root cause:** `scripts/seed_e2e_payment_links.py:55-73`. The reuse branch
returns `customer_id` immediately without a `PUT /customers/{id}` to
normalize the fields the test relies on.

**Suggested fix:** after the reuse branch finds an existing customer, force
the test invariants:

```python
existing = call("GET", f"/customers/lookup/phone/{PHONE}", None, token)
if isinstance(existing, list) and existing:
    customer_id = existing[0]["id"]
    call("PUT", f"/customers/{customer_id}", {
        "email": EMAIL,
        "email_opt_in": True,
        "sms_opt_in": True,
    }, token)
    print(f"# customer {customer_id} (reused, refreshed)", file=sys.stderr)
```

---

## Bug 6 — `payment-links-flow.sh` Journey 1 clicks the wrong appointment

**Severity:** P3 — produces a misleadingly-green run.

**Symptom:** the script's selector falls back to the first `.fc-event` it
finds on the calendar, not the seeded appointment:

```bash
ab eval "const e = document.querySelector('.fc-event.appointment-confirmed')
            || document.querySelector('.fc-event'); ..."
```

In this run the calendar already had a "Test User" appointment that is
unrelated to the seeded invoice. The script clicked it, sent a payment link
for *that* invoice (`34697927-...`), got a green toast, and recorded
"Journey 1 PASS." Meanwhile, the actual seeded invoice
(`7070645d-...`) was never exercised through the modal path at all — only
through the Invoice Detail path (Journey 2), which is where bug 2 surfaced.

**Why it matters:** if the calendar happens to be empty in CI, Journey 1
silently SKIPs (`echo "SKIP Journey 1: no visible appointments this week."`);
if it has unrelated test data, Journey 1 PASSes for the wrong reason. Both
outcomes can hide real failures of the modal flow against the seeded
fixture.

**Suggested fix:** the seeder already exports `APPOINTMENT_ID`. Have the
e2e script navigate to `/schedule?focus=$APPOINTMENT_ID` and rely on the
deep-link route to scroll/open the right card, **or** add a `data-testid`
that includes the appointment id (e.g., `data-testid="fc-event-{id}"`)
and click that selector explicitly:

```bash
ab click "[data-testid='fc-event-${APPOINTMENT_ID}']"
```

---

## Bug 7 — Build-manifest drift: deploy reports `RAILPACK` for a
Dockerfile build

**Severity:** P3 — cosmetic, but creates noise during deploy investigations.

**Symptom:** the latest dev deployment's `serviceManifest.build` shows:

```json
{
  "builder": "RAILPACK",
  "dockerfilePath": null,
  "buildEnvironment": "V3"
}
```

But the build *actually* used the in-repo `Dockerfile`:

```
[DBUG] found 'Dockerfile' at 'Dockerfile'
[INFO] [internal] load build definition from Dockerfile
[INFO] [ 1/10] FROM docker.io/library/python:3.12-slim-bookworm@sha256:...
```

…and ran the same 10 stages (`apt-get install` → `uv sync` → etc.) as the
previous DOCKERFILE-builder deploy. So the manifest is misleading: the
service is configured for "RAILPACK" autodetection, Railway autodetected
the Dockerfile, and built it. Both deploy logs show two parallel sets of
Docker stages (1–10 + 1–10) which is consistent with Railway running both
the autodetected and the Dockerfile builds, deduping at the cache layer.

**Why it matters:** during the bug 1 investigation I initially flagged the
RAILPACK switch as a possible cause of the crashed deploy (figured someone
might have flipped the Railway service to autodetect and broken the build).
That cost ~10 minutes of triage. A consistent manifest would have ruled
that out immediately.

**Suggested fix:** in the Railway service settings, pin the builder back to
DOCKERFILE explicitly. Cosmetic, but worth doing once.

---

## What worked end-to-end (positive evidence)

Items that the run actively exercised and passed:

1. **Alembic merge migration applied cleanly on a real Postgres** — confirmed
   in the deploy logs.
2. **Invoice auto-create hook generated a Stripe Payment Link** —
   `plink_1TRMsgQDNzCTp6j5755egJj6` populated on invoice creation, captured
   from the seeder API response.
3. **Payment Link panel renders on Invoice Detail** with URL, Copy button,
   sent count, last sent, and Active state pill (`05a-invoice-detail-pre.png`,
   `05b-invoice-detail-sent.png`).
4. **`$0` invoice hides the Send Payment Link CTA** as required by F11
   (`08-zero-invoice-no-cta.png`). InvoiceDetail rendered the line items but
   no Send button.
5. **Channel pill renders in InvoiceList** (`06-invoice-list-channel-pill.png`).
6. **Mobile (375×812) and desktop (1440×900) responsive** views render
   without obvious layout breakage (`09-mobile-schedule.png`,
   `10-mobile-invoice-detail.png`, `11-desktop-invoice-list.png`).
7. **Modal-side Send Payment Link** delivered via SMS for an unrelated
   in-progress appointment, with the *"Payment Link sent — Sent via SMS"*
   toast (`03-modal-link-sent.png`).
8. **Backend webhook subscription** survived the deploy (idempotency table
   intact, no replay issues observed in the deploy logs during the run).

---

## Follow-up checklist (suggested order)

- [ ] **Bug 2** — wrap `_send_email` in `try/except EmailRecipientNotAllowedError`,
      let the existing `NoContactMethodError` 422 path handle it. Add unit +
      integration test.
- [ ] **Bug 4** — fix CORS-on-5xx middleware ordering once globally; this fix
      is reusable for every future 500 the frontend ever sees.
- [ ] **Bug 5** — patch `seed_e2e_payment_links.py` to refresh email/opt-ins
      on the reuse branch.
- [ ] **Bug 6** — make `payment-links-flow.sh` Journey 1 target the seeded
      appointment by id (deep link or `data-testid` lookup).
- [ ] **Bug 3** — add `attempted_channels` + `sms_failure_reason` to the
      send-link API response and surface in the toast.
- [ ] **Bug 7** — pin Railway service builder back to DOCKERFILE.
- [ ] **Process** — add CI step asserting `alembic heads | wc -l == 1` so
      bug 1 cannot recur silently.
