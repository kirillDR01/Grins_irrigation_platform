# CallRail Inbound SMS Webhook Setup

This runbook documents how to configure CallRail's inbound SMS webhook for each environment. The webhook receives inbound texts (including STOP opt-outs) and routes them to the platform's `SMSService.handle_inbound()`.

## Webhook Endpoint

| Environment | URL |
|---|---|
| Local dev | `https://<ngrok-subdomain>.ngrok.io/api/v1/webhooks/callrail/inbound` |
| Staging | `https://staging.grinsirrigation.com/api/v1/webhooks/callrail/inbound` |
| Production | `https://grinsirrigationplatform-production.up.railway.app/api/v1/webhooks/callrail/inbound` |

## Prerequisites

- Admin access to CallRail dashboard
- `CALLRAIL_WEBHOOK_SECRET` value (generate a random 32+ character string, e.g. `openssl rand -hex 32`)
- The backend must be deployed and reachable at the target URL before configuring the webhook

## Step 1: Generate a Webhook Secret

```bash
# Generate a secure random secret
openssl rand -hex 32
```

Save this value — you'll paste it in both CallRail and your environment variables.

## Step 2: Set the Environment Variable

Add `CALLRAIL_WEBHOOK_SECRET` to the target environment:

**Local dev** — add to `.env`:
```
CALLRAIL_WEBHOOK_SECRET=<your-generated-secret>
```

**Railway (staging/production)** — set via Railway dashboard or CLI:
```bash
railway variables set CALLRAIL_WEBHOOK_SECRET=<your-generated-secret>
```

Restart the backend after setting the variable.

## Step 3: Configure the Webhook in CallRail

1. Log in to [CallRail](https://app.callrail.com)
2. Navigate to **Account Settings → Integrations → Webhooks**
3. Click **Add Webhook** (or edit existing)
4. Configure:
   - **URL**: paste the environment-specific URL from the table above
   - **Events**: select **Inbound SMS** (text message received)
   - **Signing Secret**: paste the same secret from Step 1
5. Save the webhook configuration

## Step 4: Verify the Webhook

Send a test SMS to the CallRail tracking number (`+19525293750`) and confirm:

1. CallRail delivers the webhook (check CallRail's webhook delivery log in the dashboard)
2. The backend returns HTTP 200 (check Railway logs for `sms.webhook.inbound` event)
3. If the text was "STOP", verify an `SmsConsentRecord` row was created with `consent_given=false`

```bash
# Quick log check (Railway)
railway logs --filter "sms.webhook"
```

## Local Development with ngrok

For local testing, use ngrok to expose your local backend:

```bash
# Start ngrok tunnel
ngrok http 8000

# Copy the https URL (e.g. https://abc123.ngrok.io)
# Full webhook URL: https://abc123.ngrok.io/api/v1/webhooks/callrail/inbound
```

Update the CallRail webhook URL to the ngrok URL. Remember that ngrok URLs change on restart (unless you have a paid plan with a reserved subdomain).

## Signature Verification

The endpoint verifies inbound webhooks using HMAC-SHA256:
- Header: `x-callrail-signature`
- Algorithm: HMAC-SHA256 of the raw request body using `CALLRAIL_WEBHOOK_SECRET`
- Invalid signatures return HTTP 403

If `CALLRAIL_WEBHOOK_SECRET` is empty or unset, all webhooks are rejected (403).

## Idempotency

CallRail may retry on 5xx or timeout. The endpoint deduplicates using Redis:
- Key: `sms:webhook:processed:callrail:{conversation_id}:{created_at}`
- TTL: 24 hours
- If Redis is unavailable, the webhook still processes (prefers occasional duplicate over missed STOP opt-out)

## Domain Migration Procedure

When changing the backend hostname (e.g. moving from Railway to a custom domain):

1. Deploy the backend at the new URL and verify it's reachable
2. Set `CALLRAIL_WEBHOOK_SECRET` in the new environment (same value)
3. Update the webhook URL in CallRail dashboard (Step 3 above)
4. Send a test SMS to verify (Step 4 above)
5. Decommission the old endpoint only after confirming the new one works

There is no downtime risk — CallRail queues retries for a short window. Complete the migration within a few minutes to avoid missed inbound messages.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| HTTP 403 on all webhooks | Secret mismatch or unset | Verify `CALLRAIL_WEBHOOK_SECRET` matches in both CallRail and env vars |
| HTTP 400 malformed payload | CallRail payload format changed | Check `sms.webhook.parse_failed` logs; update `parse_inbound_webhook()` |
| Duplicate processing | Redis down | Check Redis connectivity; duplicates are harmless but noisy |
| No webhooks arriving | Wrong URL in CallRail | Verify the URL in CallRail dashboard matches the environment |
| STOP not creating consent record | Webhook works but handle_inbound logic issue | Check `sms.webhook.inbound` log for `action` field |
