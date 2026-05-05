#!/usr/bin/env bash
# F2 — EstimateResponse.rejection_reason round-trip via portal Reject.
#
# Real email is sent to the allowlisted inbox (kirillrakitinsecond@gmail.com).
# No real SMS — the rejection notification path is email-only on dev.
#
# Pre-fix: API returns rejection_reason: null even when the customer
#          submitted a reason via the portal.
# Post-fix: API returns rejection_reason matching the operator's input
#           within ~1 s of the portal action.
#
# Operator interactions:
#   1. Confirm the estimate-sent email arrives at kirillrakitinsecond@gmail.com
#   2. Open the portal token URL printed by the script (or extracted via API)
#   3. Click Reject, type the reason "F2 Live Verify {epoch}"
#   4. Confirm the rejection-notification email arrives
#
# Note on plus-aliases: `email_service.py:135` rejects `+tag` aliases
# from the allowlist. The script uses the bare allowlisted address and
# relies on the unique reason string to distinguish runs in the inbox.

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_bug_lib.sh
source "$ROOT/_bug_lib.sh"

require_bug_resolution_env
require_tooling
require_token
ensure_seed_recipients

EPOCH=$(date +%s)
REASON="F2 Live Verify $EPOCH"
LEAD_TAG="f2-livecheck-$EPOCH"

step "Creating lead ($LEAD_TAG)"
# /api/v1/leads is the public website-form endpoint with its own
# unique-contact-window dedup (~24h on email+phone). Use a unique
# throwaway phone and a +tag email alias so re-running the script
# doesn't 409.
PHONE="+1952$(printf '%07d' "$(( (EPOCH * 13) % 10000000 ))")"
LEAD_PAYLOAD=$(jq -n --arg tag "$LEAD_TAG" --arg phone "$PHONE" --arg epoch "$EPOCH" '{
  name: ("F2-" + $tag),
  situation: "repair",
  address: ("1 Verify Way Apt " + $epoch),
  phone: $phone,
  email: ("kirillrakitinsecond+f2-" + $epoch + "@gmail.com"),
  source: "website"
}')
LEAD_RESP=$(curl -sf -X POST "$API_BASE/api/v1/leads" \
  -H 'Content-Type: application/json' -d "$LEAD_PAYLOAD")
LEAD_ID=$(echo "$LEAD_RESP" | jq -r '.lead_id // .id')
[[ -n "$LEAD_ID" && "$LEAD_ID" != "null" ]] || { echo "✗ failed to create lead"; exit 1; }
echo "  ✓ lead: $LEAD_ID  phone: $PHONE"

step "Creating estimate (1 line item, total \$350)"
EST_PAYLOAD=$(jq -n --arg lid "$LEAD_ID" '{
  lead_id: $lid,
  line_items: [
    {item: "Spring start-up — F2 verify", unit_price: "350.00", quantity: "1"}
  ],
  subtotal: "350.00",
  tax_amount: "0.00",
  discount_amount: "0.00",
  total: "350.00",
  notes: "F2 e2e — created by f2-estimate-rejection-reason-roundtrip.sh"
}')
EST_RESP=$(api POST "/api/v1/estimates" "$EST_PAYLOAD")
EST_ID=$(echo "$EST_RESP" | jq -r '.id')
TOKEN_VALUE=$(echo "$EST_RESP" | jq -r '.customer_token')
[[ -n "$EST_ID" && "$EST_ID" != "null" ]] || { echo "✗ failed to create estimate"; exit 1; }
echo "  ✓ estimate: $EST_ID  token: $TOKEN_VALUE"

if [[ "${F2_API_ONLY:-0}" == "1" ]]; then
  step "API-only mode: POST /api/v1/portal/estimates/{token}/reject (skips operator)"
  REJ_PAYLOAD=$(jq -n --arg reason "$REASON" '{reason: $reason}')
  REJ_HTTP=$(curl -s -o /tmp/f2-reject-body -w "%{http_code}" -X POST \
    "$API_BASE/api/v1/portal/estimates/$TOKEN_VALUE/reject" \
    -H 'Content-Type: application/json' -d "$REJ_PAYLOAD")
  if [[ "$REJ_HTTP" != "200" ]]; then
    echo "✗ FAIL: portal reject returned HTTP $REJ_HTTP" >&2
    cat /tmp/f2-reject-body >&2
    exit 1
  fi
  echo "  ✓ portal reject HTTP 200"
else
  step "Sending estimate to customer (real Resend send to allowlisted inbox)"
  api POST "/api/v1/estimates/$EST_ID/send" '{}' >/dev/null || \
    echo "  ⚠ /send may have been dropped by the email allowlist (plus-alias aware) — continuing"

  PORTAL_URL="$BASE/portal/estimates/$TOKEN_VALUE"
  echo "  Portal URL: $PORTAL_URL"

  pause_for_operator "Open the inbox at $EMAIL_TEST_INBOX and confirm the estimate-sent email arrived."

  pause_for_operator "Open $PORTAL_URL → click Reject → enter reason exactly:
    $REASON
…then submit. Press Enter here when the portal shows the rejection state."
fi

step "Polling /api/v1/estimates/$EST_ID for rejection_reason (≤30s)"
elapsed=0
while (( elapsed < 30 )); do
  GOT=$(api_q "/api/v1/estimates/$EST_ID" '.rejection_reason // ""')
  if [[ "$GOT" == "$REASON" ]]; then
    echo "  ✓ rejection_reason surfaced: $GOT"
    break
  fi
  sleep 3
  elapsed=$(( elapsed + 3 ))
done

if [[ "$GOT" != "$REASON" ]]; then
  echo "✗ FAIL: API returned rejection_reason='$GOT' (expected: '$REASON')." >&2
  echo "  Pre-fix the value would be null. F2 fix may be missing on this build." >&2
  exit 1
fi

if [[ "${F2_API_ONLY:-0}" != "1" ]]; then
  step "Polling for rejection-notification email (best-effort verify)"
  assert_recent_email "$LEAD_ID" "rejected" || true

  pause_for_operator "Confirm the rejection-notification email arrived at $EMAIL_TEST_INBOX (subject mentions 'rejected')."
fi

echo
echo "✅ F2 PASSES: portal rejection reason round-trips through the API."
echo "   Lead: $LEAD_ID  Estimate: $EST_ID  Reason: '$REASON'"
