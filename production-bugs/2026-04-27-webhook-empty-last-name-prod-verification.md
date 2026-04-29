# PROD-BUG-001: Production verification runbook for the empty-`last_name` webhook fix

**Companion to:** `2026-04-26-webhook-empty-last-name-orphaned-agreements.md` (root-cause investigation)
**Author:** Claude Code (Opus 4.7) + user
**Created:** 2026-04-27
**Use when:** After merging `fix/webhook-empty-last-name` → `main` and the production deploy goes live.
**Purpose:** Prove on production that the fix actually resolves the original crash for a real mononym/empty-name input.

---

## What this runbook proves

The unit-test suite already proves the fix in isolation (5 new tests on `webhooks.py` covering Madonna / empty / whitespace / two-word / three-word inputs). The dev-environment E2E run on 2026-04-27 proved the surrounding webhook pipeline works for 6 different tier × cardholder-name combinations, but did **not** directly invoke the patched `CustomerCreate(last_name="-")` call on dev because the existing dev customer with phone `9527373312` matched first via `find_by_phone` and short-circuited the create branch.

This runbook closes that gap by exercising the exact production code path that previously crashed.

---

## Pre-merge checklist

- [ ] PR `fix/webhook-empty-last-name` → `main` reviewed and merged.
- [ ] Railway prod deploy SUCCESS for the merge commit (check `mcp__railway__list-deployments` / Railway dashboard).
- [ ] Confirm `EMAIL_TEST_ADDRESS_ALLOWLIST` is **unset** in prod env vars (it should be — production has never had this guard active; it is a dev/staging hardening only).
- [ ] Have access to:
  - Stripe Dashboard (live mode)
  - Railway logs for the prod service
  - Prod DB read access (for the verification queries)
  - Admin dashboard login

---

## Option A — Replay a known-bug event from Stripe (recommended)

This is the strongest possible verification: it re-runs the exact event payload that originally crashed in production.

### A.1 Pick a target event

The investigation identified 3 confirmed-mononym subscriptions whose `checkout.session.completed` events crashed with `ValidationError` on `last_name`:

| Subscription ID                          | Date (approx) |
| ---------------------------------------- | ------------- |
| `sub_1TQTVLG1xK8dFlaf3fN2xE1G`           | 2026-04-25    |
| `sub_1TQILUG1xK8dFlafDLMNIIt3`           | 2026-04-23    |
| `sub_1TQELWG1xK8dFlafeg0JTAGI`           | 2026-04-22    |

Stripe retains events for 30 days. **Acting before 2026-05-22 is required for `sub_1TQTVLG…`; earlier dates expire sooner.** Newer mononym events that may have appeared after 2026-04-26 are equally valid — use the most recent if any.

### A.2 Resend the event

1. Stripe Dashboard (live mode) → **Developers → Events**.
2. Filter: `event type = checkout.session.completed`, search by the subscription ID above (or use the failure event ID from the original Railway log line).
3. Open the event → **Resend** to your prod webhook endpoint (`https://<your-prod-domain>/api/v1/webhooks/stripe`).

### A.3 Verify in Railway prod logs

Filter the deploy logs for the resend window. Expected entries (in order):

```
event=stripe.stripewebhookhandler.webhook_customer_placeholder_last_name
  first_name=<the customer's first name>
  full_name_provided=true

event=stripe.stripewebhookhandler.webhook_checkout_completed
  agreement_id=<UUID>
  customer_id=<UUID>
  stripe_event_id=<the resent event id>
```

**Failure signal (must NOT see):**
- `webhook_checkout_session_completed_failed` with `error_type=ValidationError` and `error` mentioning `last_name`.
- `webhook_invoice_paid_failed` with `error="No agreement for subscription sub_1TQ…"` after the resend.

### A.4 Verify in prod DB

```sql
-- Customer row created with placeholder last_name
SELECT id, first_name, last_name, email, phone, created_at
FROM customers
WHERE last_name = '-'
ORDER BY created_at DESC
LIMIT 5;

-- Agreement row exists for the resent subscription
SELECT id, agreement_number, status, stripe_subscription_id, customer_id, created_at
FROM service_agreements
WHERE stripe_subscription_id = 'sub_1TQTVLG1xK8dFlaf3fN2xE1G'  -- replace with chosen sub
LIMIT 1;

-- Jobs were generated
SELECT count(*) FROM jobs
WHERE service_agreement_id = '<agreement.id from above>';
```

Expected: customer row with `last_name = '-'`, agreement row with `status = 'active'` (or `pending` then activated by the subsequent `invoice.paid`), and jobs count appropriate to the tier (Essential 2, Professional 3, Premium 7, Winterization 1).

### A.5 Verify the customer-facing endpoint

```
GET https://<prod-domain>/api/v1/onboarding/verify-session?session_id=<cs_live_…>
GET https://<prod-domain>/api/v1/onboarding/complete  (POST, with the form payload)
```

Both should return 200, not 404. The previously locked-out customer can now finish onboarding.

---

## Option B — Real prod mononym checkout (fallback)

Use this if all 3 historical events have aged out of Stripe's 30-day window and no fresh mononym has appeared organically.

### B.1 Pre-flight (avoid colliding with existing prod data)

```sql
-- Confirm the test phone and email are NOT already in production
SELECT id, first_name, last_name FROM customers
WHERE phone = '<TEST_PHONE>' OR email = '<TEST_EMAIL>';
-- Must return 0 rows; if not, pick a different phone/email
```

Use a phone you actually own (so the SMS optin from the consent flow goes somewhere real) and an email you actually control.

### B.2 Run the checkout

1. Open the live `/service-packages` page in a clean browser session (incognito recommended — avoids Stripe Link auto-fill).
2. Pick the cheapest tier (Winterization Only Residential, $85/yr) to minimize charge size.
3. Fill the pre-checkout modal: phone, SMS consent, Confirm Subscription.
4. On Stripe Checkout (live mode): use a real card. Set **Cardholder name = `Madonna`** (single word — this is the bug-triggering input). Complete the charge.
5. Land on `/onboarding?session_id=cs_live_…`. Fill the onboarding form. Click **Complete Onboarding**.
6. **Success page must render** — "Manage Your Subscription" + "Back to Homepage" buttons. NOT the red "We couldn't find your session. Please contact us." error.

### B.3 Verify (same as A.3 / A.4 / A.5)

Same expected log lines, same DB queries (substitute the new subscription ID), same endpoint checks.

### B.4 Cleanup

1. Stripe Dashboard → **Customers** → find the test customer → cancel the subscription → issue a full refund on the charge.
2. (Optional) prod DB: soft-delete or hard-delete the test customer + agreement + jobs created by the test. If you keep them, leave a note in `internal_notes`: `[VERIFICATION TEST 2026-MM-DD — empty-last-name fix]`.

---

## Acceptance criteria — all five must hold

- [ ] **`webhook_customer_placeholder_last_name`** log line present immediately before `webhook_checkout_completed`.
- [ ] **`webhook_checkout_completed`** log line present, no `_failed` variant for the same `stripe_event_id`.
- [ ] **Customer row** in `customers` with `first_name = <single word>` and `last_name = '-'`.
- [ ] **Agreement row** in `service_agreements` with `stripe_subscription_id` matching the resent/new event and `status` ≠ `cancelled`.
- [ ] **`POST /api/v1/onboarding/complete`** with that session_id returns **200** (not 404).

If all five hold, the production fix is verified end-to-end against a real bug-triggering input.

---

## Rollback plan

If A.3 or A.4 reveals the same `ValidationError` (extremely unlikely given unit-test coverage, but plan for it):

1. **Revert the merge commit on `main`** — `git revert <merge-sha>` and push. Railway redeploys to the prior commit within ~5 min.
2. Monitor logs to confirm the revert is live and the old behavior (crash) is restored.
3. Re-open `fix/webhook-empty-last-name`, reproduce locally, and add the missing test case before re-attempting the merge.

There is no DB migration in this fix, so there is nothing to roll back at the schema level. Customers created with `last_name = '-'` during the test are valid rows — they just have a placeholder name that the admin can rename in-place if needed.

---

## Recovery of historically-orphaned customers (out of scope for this verification)

The investigation report identified **5 confirmed-orphaned subscriptions** (Bucket A: 3 mononyms + Bucket C: 2 admin-created). After this fix is verified in production, follow up with the recovery options described in section 16 of `2026-04-26-webhook-empty-last-name-orphaned-agreements.md` for those existing customers — that work is independent of and complementary to this verification.

---

## Confidence after verification

- Pre-verification: 9.5/10 (unit tests + adjacent E2E proves the surrounding pipeline; only the exact `CustomerCreate(last_name="-")` call lacks a live witness).
- Post-Option-A success: **10/10** — fix is proven against an actual production input that originally crashed.
- Post-Option-B success: 10/10 — fix is proven against a controlled bug-triggering input on real production infra.
