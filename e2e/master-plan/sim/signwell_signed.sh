#!/usr/bin/env bash
# SignWell document-completed webhook simulator.
#
# Posts a signed-document webhook payload at the backend so Phase 4 / Phase 5
# can verify the auto-advance from Pending Approval → Send Contract without
# requiring a human to actually sign through the SignWell test mode.
#
# HMAC verification is enforced (signwell_webhooks.py:48). If the
# SIGNWELL_WEBHOOK_SECRET on the target backend changes, this script must
# use the same secret.
#
# Backend route: POST /api/v1/webhooks/signwell
#
# Usage:
#   sim/signwell_signed.sh <signwell_document_id> [event_type]
#
# Examples:
#   sim/signwell_signed.sh doc_abc123 document_signed
#   sim/signwell_signed.sh doc_abc123 document_completed

set -euo pipefail

DOC_ID="${1:?usage: sim/signwell_signed.sh <signwell_document_id> [event_type]}"
EVENT_TYPE="${2:-document_completed}"

API_BASE="${API_BASE:-http://localhost:8000}"
SECRET="${SIGNWELL_WEBHOOK_SECRET:?SIGNWELL_WEBHOOK_SECRET must be set}"

PAYLOAD=$(jq -nc \
  --arg type "$EVENT_TYPE" \
  --arg doc "$DOC_ID" \
  --arg id "evt-sim-$(date +%s)" \
  '{
    event:    $type,
    event_id: $id,
    data: {
      object: {
        id:     $doc,
        status: "completed"
      }
    }
  }')

# SignWell signature header name verified at signwell_webhooks.py:69.
SIGNATURE=$(printf '%s' "$PAYLOAD" \
  | openssl dgst -sha256 -hmac "$SECRET" -hex \
  | awk '{print $2}')

echo "→ POST $API_BASE/api/v1/webhooks/signwell" >&2
echo "  doc=$DOC_ID event=$EVENT_TYPE" >&2

curl -sS -w '\nHTTP %{http_code}\n' \
  -X POST "$API_BASE/api/v1/webhooks/signwell" \
  -H 'Content-Type: application/json' \
  -H "X-Signwell-Signature: $SIGNATURE" \
  -d "$PAYLOAD"
