#!/usr/bin/env bash
# Stripe webhook event trigger.
#
# Wrapper around `stripe trigger` to fire test webhook events at the local
# or dev backend. Used by:
#   - Phase 14 (Stripe Payment Links): checkout.session.completed,
#     charge.refunded, charge.dispute.created
#   - Phase 16 (Contract Renewals): invoice.paid with billing_reason=subscription_cycle
#
# Env:
#   STRIPE_API_KEY        sk_test_... (required — use Stripe test mode key)
#   STRIPE_WEBHOOK_URL    full URL — defaults to $API_BASE/api/v1/webhooks/stripe
#                         Backend route confirmed at api/v1/webhooks.py:1386
#
# Examples:
#   sim/stripe_event.sh checkout.session.completed --add metadata.invoice_id=$INV
#   sim/stripe_event.sh invoice.paid --add billing_reason=subscription_cycle
#   sim/stripe_event.sh charge.refunded
#   sim/stripe_event.sh charge.dispute.created
#
# Requires: stripe CLI installed (`brew install stripe/stripe-cli/stripe`).

set -euo pipefail

EVENT="${1:?usage: sim/stripe_event.sh <event_name> [stripe-trigger-args...]}"
shift || true

command -v stripe >/dev/null || { echo "stripe CLI not installed"; exit 1; }
: "${STRIPE_API_KEY:?STRIPE_API_KEY (sk_test_...) required}"

API_BASE="${API_BASE:-http://localhost:8000}"
STRIPE_WEBHOOK_URL="${STRIPE_WEBHOOK_URL:-$API_BASE/api/v1/webhooks/stripe}"

echo "→ stripe trigger $EVENT (forwarding to $STRIPE_WEBHOOK_URL)" >&2

# `stripe trigger` posts directly to the configured forward URL via stripe CLI's
# listen pipeline. The simplest approach: use stripe CLI's --api-key flag and
# point the trigger at the webhook URL via STRIPE_WEBHOOK_FWD env (set by
# `stripe listen --forward-to ...` in a sibling terminal).
#
# For automated runs, prefer running `stripe listen --forward-to $STRIPE_WEBHOOK_URL`
# in the background and using `stripe trigger` here.

stripe trigger "$EVENT" --api-key "$STRIPE_API_KEY" "$@"
