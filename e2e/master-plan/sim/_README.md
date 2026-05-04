# Master-Plan Webhook Simulators

These scripts post HMAC-signed webhook payloads at the backend so phase
scripts can drive flows without depending on a human at +19527373312 or
on real third-party callbacks.

| Script | Purpose | Eliminates HUMAN dep in |
|---|---|---|
| `callrail_inbound.sh` | Inbound SMS reply (Y/R/C/STOP/etc.) | Phase 9 (Y/R/C), Phase 10 (alternatives) |
| `signwell_signed.sh` | Document signed event | Phase 4 (auto-advance from Pending Approval) |
| `stripe_event.sh` | Stripe test event trigger via stripe CLI | Phase 14 (payment), Phase 16 (renewal) |
| `resend_email_check.sh` | Programmatic email retrieval | Phase 5 (portal email), Phase 4 (SignWell email) |

## CRITICAL: HMAC verification is preserved

The simulators sign payloads with the same secret the backend uses
(`CALLRAIL_WEBHOOK_SECRET`, `SIGNWELL_WEBHOOK_SECRET`, `STRIPE_WEBHOOK_SECRET`).
A simulator with the wrong secret will fail with 401/403 — that is the
correctness signal we want. **Never** add a "skip HMAC" flag.

## Endpoint paths (verified against current source)

- CallRail inbound: `POST /api/v1/webhooks/callrail/inbound` (`callrail_webhooks.py:211`)
- SignWell:        `POST /api/v1/webhooks/signwell`         (`signwell_webhooks.py:48`)
- Stripe:          `POST /api/v1/webhooks/stripe`           (`webhooks.py:1386`)
- Resend (bounce): `POST /api/v1/webhooks/resend`           (`resend_webhooks.py:65`)

## When NOT to use a simulator

- For pre-release smoke tests, run **with a human** at +19527373312 to
  catch carrier-level issues that simulators bypass (CallRail STOP behavior,
  rate-limit responses, etc.).
- For first-time changes to the SMS/email/webhook code, simulators alone
  are insufficient — the integration with the real provider must also be
  exercised.

## How to keep secrets in sync

Set in your shell before running phase scripts:
```bash
export CALLRAIL_WEBHOOK_SECRET="$(railway variables get CALLRAIL_WEBHOOK_SECRET --service Grins-dev --environment dev)"
export SIGNWELL_WEBHOOK_SECRET="$(railway variables get SIGNWELL_WEBHOOK_SECRET --service Grins-dev --environment dev)"
export STRIPE_WEBHOOK_SECRET="$(railway variables get STRIPE_WEBHOOK_SECRET --service Grins-dev --environment dev)"
```

For local backend, use the values from your local `.env`.
