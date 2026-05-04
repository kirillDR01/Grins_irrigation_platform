#!/usr/bin/env bash
# CallRail inbound-SMS webhook simulator.
#
# Posts an HMAC-signed CallRail-shaped inbound payload at the local or dev
# backend. Use to remove the human-in-the-loop dependency for Phase 9 (Y/R/C)
# and Phase 10 (alternative-time replies) when smoke-iterating.
#
# CRITICAL: This still exercises HMAC verification end-to-end. If the
# CALLRAIL_WEBHOOK_SECRET on the target backend changes, you MUST update
# the local secret before this works — that is the whole point.
#
# Usage:
#   sim/callrail_inbound.sh <thread_resource_id> <body> [from_phone]
#
# Example:
#   sim/callrail_inbound.sh CRX-thread-abc "Y"
#   sim/callrail_inbound.sh CRX-thread-abc "Tue 2pm"
#   sim/callrail_inbound.sh CRX-thread-abc "STOP"
#
# Env:
#   API_BASE                  default: http://localhost:8000 (set ENVIRONMENT=dev)
#   CALLRAIL_WEBHOOK_SECRET   required — must match backend
#   CALLRAIL_TRACKING_NUMBER  default: +19525293750 (the dev tracking number)
#   FROM_PHONE                default: +19527373312 (allowlisted seed)
#
# Path verified at: src/grins_platform/api/v1/callrail_webhooks.py
#   route: POST /api/v1/webhooks/callrail/inbound
#   HMAC verification at line 243: provider.verify_webhook_signature(...)
#
# Reference: feature-developments/CallRail collection/CallRail_Scheduling_Poll_Responses.md
#   has a real captured CallRail inbound payload to mirror the shape.

set -euo pipefail

THREAD_ID="${1:?usage: sim/callrail_inbound.sh <thread_resource_id> <body> [from_phone]}"
BODY="${2:?usage: sim/callrail_inbound.sh <thread_resource_id> <body> [from_phone]}"
FROM_PHONE="${3:-${FROM_PHONE:-+19527373312}}"

API_BASE="${API_BASE:-http://localhost:8000}"
SECRET="${CALLRAIL_WEBHOOK_SECRET:?CALLRAIL_WEBHOOK_SECRET must be set to match backend}"
TRACKING_NUMBER="${CALLRAIL_TRACKING_NUMBER:-+19525293750}"

ID="sim-$(date +%s)-$RANDOM"
TS=$(python3 -c 'import datetime;print(datetime.datetime.utcnow().isoformat()+"Z")')

# Mirror real CallRail inbound shape (per CallRail_Scheduling_Poll_Responses.md
# field captures). Phone numbers in inbound payloads are masked — last4 only.
LAST4="${FROM_PHONE: -4}"

PAYLOAD=$(jq -nc \
  --arg id "$ID" \
  --arg thread "$THREAD_ID" \
  --arg body "$BODY" \
  --arg src "***${LAST4}" \
  --arg dst "$TRACKING_NUMBER" \
  --arg ts "$TS" \
  '{
    id:               $id,
    type:             "inbound_text",
    thread_resource_id: $thread,
    direction:        "inbound",
    state:            "delivered",
    source_number:    $src,
    destination_number: $dst,
    body:             $body,
    sent_at:          $ts,
    created_at:       $ts
  }')

# CallRail uses HMAC-SHA1 (NOT SHA256) over the raw body with the shared
# secret, base64-encoded. Header name is `signature` (no `x-` prefix).
# Verified against backend at services/sms/callrail_provider.py:222-254.
SIGNATURE=$(printf '%s' "$PAYLOAD" \
  | openssl dgst -sha1 -hmac "$SECRET" -binary \
  | base64)

echo "→ POST $API_BASE/api/v1/webhooks/callrail/inbound" >&2
echo "  thread=$THREAD_ID body='$BODY' from=$FROM_PHONE" >&2

RESP=$(curl -sS -w '\nHTTP %{http_code}\n' \
  -X POST "$API_BASE/api/v1/webhooks/callrail/inbound" \
  -H 'Content-Type: application/json' \
  -H "signature: $SIGNATURE" \
  -d "$PAYLOAD")

echo "$RESP"

# Exit non-zero on non-2xx so phase scripts halt on simulator failures.
echo "$RESP" | tail -1 | grep -qE 'HTTP 2[0-9][0-9]' || exit 1
