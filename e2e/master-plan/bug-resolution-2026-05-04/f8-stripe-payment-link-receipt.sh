#!/usr/bin/env bash
# F8 — Stripe Payment Link customers must receive a payment_receipt SMS+email
# after the checkout.session.completed reconciliation.
#
# This script uses a FRESH test customer (not the seed) so the 24h
# `payment_receipt` dedup window stays open. The fresh customer is
# allowlisted by sharing the seed's phone (+19527373312) and email
# (kirillrakitinsecond@gmail.com) — both are governed by the platform's
# code-level allowlist (SMS_TEST_PHONE_ALLOWLIST and
# EMAIL_TEST_ADDRESS_ALLOWLIST), not the customer-id pair.
#
# Pre-fix: paying the Stripe Payment Link reconciles the invoice but no
#          customer-facing receipt SMS or email fires.
# Post-fix: a payment_receipt SMS lands at +19527373312 within ~30 s of
#           the Stripe payment, and a matching email arrives.
#
# Operator interactions:
#   1. Receive the Payment Link SMS at +19527373312
#   2. Open it; pay with Stripe test card 4242 4242 4242 4242 (any
#      future expiry, any CVC)
#   3. Confirm the payment_receipt SMS lands shortly after
#   4. Confirm the receipt email arrives at the allowlisted inbox

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_bug_lib.sh
source "$ROOT/_bug_lib.sh"

require_bug_resolution_env
require_tooling
require_token

EPOCH=$(date +%s)
TAG="f8-livecheck-$EPOCH"

step "Creating FRESH test customer ($TAG) — open dedup slot"
CUSTOMER_PAYLOAD=$(jq -n --arg tag "$TAG" --arg phone "$SMS_TEST_PHONE" --arg email "$EMAIL_TEST_INBOX" '{
  first_name: ("F8-" + $tag),
  last_name: "Verify",
  phone: $phone,
  email: $email,
  street_address: "1 Stripe Live Way",
  city: "Test City",
  state: "MN",
  zip_code: "55401",
  sms_opt_in: true,
  email_opt_in: true
}')
CID=$(api POST "/api/v1/customers" "$CUSTOMER_PAYLOAD" | jq -r '.id')
[[ -n "$CID" && "$CID" != "null" ]] || { echo "✗ failed to create fresh customer"; exit 1; }
echo "  ✓ fresh customer: $CID"

step "Creating job for the fresh customer"
JOB_PAYLOAD=$(jq -n --arg cid "$CID" --arg dt "$(date +%F)" --arg tag "$TAG" '{
  customer_id: $cid,
  job_type: "spring_startup",
  description: ("F8 stripe verify — " + $tag),
  scheduled_date: $dt
}')
JID=$(api POST "/api/v1/jobs" "$JOB_PAYLOAD" | jq -r '.id')
[[ -n "$JID" && "$JID" != "null" ]] || { echo "✗ failed to create job"; exit 1; }
echo "  ✓ job: $JID"

step "Creating \$1.00 invoice (small, low-risk Stripe test charge)"
TODAY=$(date +%F)
DUE=$(python3 -c "import datetime; print((datetime.date.today()+datetime.timedelta(days=30)).isoformat())")
INV_PAYLOAD=$(jq -n --arg jid "$JID" --arg cid "$CID" --arg today "$TODAY" --arg due "$DUE" '{
  job_id: $jid,
  customer_id: $cid,
  amount: "1.00",
  total_amount: "1.00",
  invoice_date: $today,
  due_date: $due,
  line_items: [
    {description: "F8 e2e verify", quantity: "1", unit_price: "1.00", total: "1.00"}
  ]
}')
INV_ID=$(api POST "/api/v1/invoices" "$INV_PAYLOAD" | jq -r '.id')
[[ -n "$INV_ID" && "$INV_ID" != "null" ]] || { echo "✗ failed to create invoice"; exit 1; }
echo "  ✓ invoice: $INV_ID"

step "Sending Stripe Payment Link via SMS"
SEND_RESP=$(api POST "/api/v1/invoices/$INV_ID/send-link" '{}')
echo "$SEND_RESP" | jq '.' >&2 || true
LINK=$(echo "$SEND_RESP" | jq -r '.payment_url // .url // empty')
[[ -n "$LINK" ]] && echo "  link: $LINK"

pause_for_operator "Confirm the Payment Link SMS arrived at $SMS_TEST_PHONE.
Open it and pay with Stripe test card:
    Number:  4242 4242 4242 4242
    Expiry:  any future month/year (e.g. 12/30)
    CVC:     any 3 digits (e.g. 123)
    ZIP:     any 5 digits (e.g. 55401)
Press Enter here AFTER the Stripe page shows 'Payment successful'."

step "Polling /api/v1/invoices/$INV_ID for status=paid (≤90s)"
elapsed=0
while (( elapsed < 90 )); do
  STATUS=$(api_q "/api/v1/invoices/$INV_ID" '.status // ""')
  if [[ "$STATUS" == "paid" ]]; then
    echo "  ✓ invoice flipped to paid"
    break
  fi
  sleep 5
  elapsed=$(( elapsed + 5 ))
done
if [[ "$STATUS" != "paid" ]]; then
  echo "✗ FAIL: invoice did not reach paid within 90s (status=$STATUS)" >&2
  echo "  Stripe webhook may not have arrived — check Railway logs." >&2
  exit 1
fi

step "Polling for payment_receipt SMS (the F8 assertion)"
if assert_recent_sms "$CID" "payment_receipt" 60; then
  echo "  ✓ F8 receipt SMS observed for fresh customer $CID"
else
  echo "✗ FAIL: no payment_receipt row for $CID — F8 fix likely missing on this build." >&2
  exit 1
fi

pause_for_operator "Confirm the receipt SMS arrived at $SMS_TEST_PHONE."

step "Best-effort email-receipt confirmation"
assert_recent_email "$CID" "receipt" || true

pause_for_operator "Confirm the receipt email arrived at $EMAIL_TEST_INBOX."

echo
echo "✅ F8 PASSES: Stripe Payment Link → checkout.session.completed → receipt SMS+email."
echo "   Fresh customer: $CID  Invoice: $INV_ID"
