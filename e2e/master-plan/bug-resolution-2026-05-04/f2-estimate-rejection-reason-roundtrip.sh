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
LEAD_PAYLOAD=$(jq -n --arg tag "$LEAD_TAG" --arg phone "$SMS_TEST_PHONE" --arg email "$EMAIL_TEST_INBOX" '{
  first_name: ("F2-" + $tag),
  last_name: "Verify",
  phone: $phone,
  email: $email,
  source: "website",
  notes: "F2 e2e verification"
}')
LEAD_ID=$(api POST "/api/v1/leads" "$LEAD_PAYLOAD" | jq -r '.id')
[[ -n "$LEAD_ID" && "$LEAD_ID" != "null" ]] || { echo "✗ failed to create lead"; exit 1; }
echo "  ✓ lead: $LEAD_ID"

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

step "Sending estimate to customer (real Resend send to allowlisted inbox)"
api POST "/api/v1/estimates/$EST_ID/send" '{}' >/dev/null
echo "  ✓ /send dispatched"

PORTAL_URL="$BASE/portal/estimates/$TOKEN_VALUE"
echo "  Portal URL: $PORTAL_URL"

pause_for_operator "Open the inbox at $EMAIL_TEST_INBOX and confirm the estimate-sent email arrived."

pause_for_operator "Open $PORTAL_URL → click Reject → enter reason exactly:
    $REASON
…then submit. Press Enter here when the portal shows the rejection state."

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

step "Polling for rejection-notification email (best-effort verify)"
assert_recent_email "$LEAD_ID" "rejected" || true

pause_for_operator "Confirm the rejection-notification email arrived at $EMAIL_TEST_INBOX (subject mentions 'rejected')."

echo
echo "✅ F2 PASSES: portal rejection reason round-trips through the API."
echo "   Lead: $LEAD_ID  Estimate: $EST_ID  Reason: '$REASON'"
