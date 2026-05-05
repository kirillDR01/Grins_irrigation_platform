# Bug-resolution E2E scripts — 2026-05-04 sign-off run

These scripts recreate the live end-to-end exercises that originally surfaced
F2, F8, F9, and F10 in the master-plan run at
`e2e-screenshots/master-plan/runs/2026-05-04-full-real-emails/`. They use **real
SMS** to `+19527373312` and **real email** to `kirillrakitinsecond@gmail.com`
against the dev environment — no simulator short-cuts.

The aim is to confirm each fix stays fixed under real carrier + Stripe + Resend
conditions. Run after deploying changes to dev and before sign-off.

## Hard rules

- **SMS only to `+19527373312`.** **Email only to `kirillrakitinsecond@gmail.com`.**
- **Dev only.** `_bug_lib.sh::require_bug_resolution_env` refuses to run unless
  `ENVIRONMENT=dev` and `API_BASE` resolves to `*-dev-*.up.railway.app`.
- An operator must be present at the phone and the inbox throughout. Scripts
  block at every operator checkpoint and refuse to auto-skip.
- No commits, pushes, or main merges. Per ENVIRONMENT SAFETY rules in
  `master-e2e-testing-plan.md`.

## Files

| File | Purpose |
| --- | --- |
| `_bug_lib.sh` | Shared helpers (sources `../_dev_lib.sh`). Adds `pause_for_operator`, `assert_recent_sms`, `assert_no_recent_sms`, `assert_recent_email`, `ensure_seed_recipients`. |
| `f9-appointments-customer-id-filter.sh` | F9. Pure API, no SMS, no email. Creates 2 customers + jobs + appointments and verifies `?customer_id=` narrows. |
| `f2-estimate-rejection-reason-roundtrip.sh` | F2. Real email send to allowlisted inbox; operator clicks Reject in the portal; script asserts API returns the typed reason. |
| `f10-collect-payment-flag-and-duplicate-guard.sh` | F10. Real `payment_receipt` SMS for `cash`; `check`/`venmo`/`zelle` are API-only (24 h dedup blocks their SMS on the same run). All four assert flag + duplicate-invoice guard. |
| `f8-stripe-payment-link-receipt.sh` | F8. Real Stripe Payment Link pay; operator pays with test card `4242 4242 4242 4242`; script asserts `payment_receipt` SMS arrives. Uses a FRESH customer to dodge dedup. |
| `run-all.sh` | Sequenced one-shot runner: F9 → F2 → F10 → F8. Aborts at first failure with which fix is missing. |

## How to run on dev

```bash
# 1. Source dev env vars (BASE, API_BASE, allowlist defaults).
source e2e/master-plan/_dev_lib.sh

# 2. Set your admin creds.
export E2E_USER=admin@grinsirrigation.com
export E2E_PASS=<dev_admin_password>

# 3. Single-script (during iteration):
e2e/master-plan/bug-resolution-2026-05-04/f9-appointments-customer-id-filter.sh

# Or one-shot ordered run (preferred for sign-off):
e2e/master-plan/bug-resolution-2026-05-04/run-all.sh
```

## Operator interactions per script

| Script | SMS at +1952…7312 | Email at kirill…@gmail | Stripe Checkout |
| --- | --- | --- | --- |
| F9 | none | none | none |
| F2 | none | estimate-sent + estimate-rejected | none |
| F10 | one `payment_receipt` (cash run only) | none expected for runs 2–4 | none |
| F8 | `payment_link_sent` + `payment_receipt` | receipt email | YES — pay with `4242 4242 4242 4242` |

## Why HUMAN-mode (not the simulator)

Per `e2e/master-plan/sim/_README.md`, simulators bypass real CallRail / Stripe /
Resend. The four bugs in scope all involve customer-facing notifications or
external-service reconciliation — simulators would mask the very behavior we
need to confirm.

## Dedup management

`services/sms_service.py:344-361` enforces 24 h per-`(customer_id, message_type)`
SMS dedup. The default order (F9 → F2 → F10 → F8) and F8's fresh-customer
strategy avoid collisions in a single run. Re-running within 24 h on the same
seed customer will silently skip the F10 cash receipt — use a different seed
customer or wait the dedup window.

## Cleanup

- F9 leaves two customers in dev as fixture data, tagged
  `f9-livecheck-{epoch}`.
- F2 leaves a lead + estimate.
- F10 leaves four jobs + four appointments under the seed customer.
- F8 leaves one customer + invoice (paid).

These can be GC'd later by name pattern but are intentionally not deleted by
the scripts so the trail remains for dispute investigation.
