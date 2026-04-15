# Grins Irrigation Platform — End-to-End Testing Procedure

This folder is the **replayable runbook** for the full customer-lifecycle E2E
test on the Railway `dev` environment. It's written so a future engineer (or
agent) can execute it top-to-bottom without needing prior context.

## Files

- **`00-preflight.md`** — environment, access, account setup, pre-test cleanup SQL.
- **`01-path-a-lead-intake.md`** — A1 public form, A2 E.164 + Winterization, A3 messy phone.
- **`02-path-b-lead-to-sales.md`** — B1 net-new customer, B2 auto-merge, B3 requires-estimate warning.
- **`03-path-c-sales-pipeline.md`** — C2 no-doc block, C4 force-convert.
- **`04-path-d-e-confirmation-yrc.md`** — D1/E1 Y, E3 R, E4/E5 alternatives (M-3), E6/E7 C, E8/E9 STOP/START.
- **`05-path-f-onsite.md`** — F1 On My Way, F2 Started skip, F3/F4 Complete, F5/F6 Google Review.
- **`06-path-g-admin-cancel.md`** — G1 admin cancel, G3 reactivate (H-8).
- **`07-path-h-year-rollover.md`** — M-4 November onboarding → next year.
- **`08-path-i-dashboard.md`** — E-BUG-J sidebar counter invalidation.
- **`09-path-j-schedule-all.md`** — bulk-schedule every TB_SCHEDULED job + bulk-confirm.
- **`10-customer-landing-flow.md`** — Path L (Service Packages purchase, 8 tiers + Stripe + onboarding 7-week-pickers) and Path Q (Free Quote lead intake, 5 scenarios across consent matrix + dedupe + validation). New 2026-04-14.
- **`99-cleanup.md`** — teardown SQL for E2E records.
- **`scripts/`** — ready-to-copy Python helpers (`clear_consent.py`, `cleanup.py`).

## Golden rules

1. **Only `+19527373312` may receive real SMS.** `SMS_TEST_PHONE_ALLOWLIST` enforces this at `services/sms/base.py`. Do not change it.
2. **Never touch production.** Railway CLI must be linked to project `zealous-heart`, environment `dev`. Verify with `railway status` before every session.
3. **Agent pairs with a real phone.** Paths D-G need someone at +19527373312 to read/reply to SMS. Tell them *exactly* what to reply on each step.
4. **Use the REST API for most verifications.** The dev Postgres runs on `postgres-phd.railway.internal` which isn't reachable from a laptop. Use `railway ssh --service Grins-dev --environment dev python3 ...` only for DB reads/writes that the API can't do.
5. **Each Path has three parts**: setup (create the records you need), trigger (perform the admin action via API or UI), verify (hit the API + optionally check the phone). Follow them in order.

## How to run a full session

```bash
# From the repo root, with Railway CLI linked to the dev env:
cd "/Users/kirillrakitin/Grins_irrigation_platform"
railway status                 # confirm: zealous-heart / dev / Grins-dev
railway redeploy --service Grins-dev --yes   # optional, if you need a fresh container
curl -s https://grins-dev-dev.up.railway.app/health | jq .

# Each path file below assumes $TOKEN is exported:
TOKEN=$(curl -s https://grins-dev-dev.up.railway.app/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin123"}' \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')
export TOKEN
```

Then walk the `01-...` → `09-...` files in order. Each has copy-pasteable
`curl` commands and the exact expected response shape.

## If something looks wrong

- The `bughunt/2026-04-14-customer-lifecycle-deep-dive.md` file ends with an
  "E2E discovery" section listing every bug surfaced by live testing on
  2026-04-14 — cross-reference before filing a new one.
- Unit-test baseline is `28 failures` (logged in the Sprint handoff). If a
  new E2E run surfaces a different count, something regressed.

## Kirill-the-seed reference

| Thing | Value |
|---|---|
| Customer name | Kirill Rakitin |
| Customer ID | `e7ba9b51-580e-407d-86a4-06fd4e059380` |
| Phone (allowlisted) | `+19527373312` |
| Email | `kirillrakitinsecond@gmail.com` |
| Default staff (Admin User) | `0bb0466d-ce5e-477a-9292-7d4b9673a7f6` |

These are stable across sessions. If any of them stop resolving, re-run
`preflight` to re-create the seed customer.
