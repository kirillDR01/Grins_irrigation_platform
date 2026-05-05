#!/usr/bin/env bash
# F10 — collect_payment must set Job.payment_collected_on_site for
# cash/check/Venmo/Zelle and the duplicate-invoice guard must then refuse
# /invoices/generate-from-job/{job_id}.
#
# Strategy (per plan): only `cash` triggers a real-SMS receipt check.
# `check`, `venmo`, `zelle` are exercised API-only — the 24h dedup window
# at services/sms_service.py:344-361 would silence their receipts on the
# same phone within the same run, so the script asserts the FLAG and the
# DUPLICATE-INVOICE GUARD without expecting a real SMS for those three.
#
# Pre-fix: flag is `false` after a non-Stripe collect_payment;
#          /invoices/generate-from-job/{job} returns 201 (duplicate created).
# Post-fix: flag is `true`; /invoices/generate-from-job/{job} returns
#           4xx with "payment was collected on site".
#
# Operator interactions:
#   - For the `cash` run: confirm the receipt SMS arrived at +19527373312.
#   - For the other 3 methods: no SMS expected (dedup); operator just
#     supervises the script.

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_bug_lib.sh
source "$ROOT/_bug_lib.sh"

require_bug_resolution_env
require_tooling
require_seed_customer
require_token
ensure_seed_recipients

# Pick a tech for appointment scheduling.
STAFF_ID=$(api_q "/api/v1/staff?role=tech&limit=1" '.items[0].id // .items[0].staff_id // ""')
[[ -n "$STAFF_ID" ]] || { echo "✗ no tech staff present"; exit 1; }

run_one_method() {
  # run_one_method <method:str> <amount:str> <expect_sms:bool> [<reference:str>]
  local method="$1" amount="$2" expect_sms="$3" reference="${4:-}"
  local epoch
  epoch=$(date +%s)
  local label="$method-$epoch"
  echo
  echo "════ Method: $method  amount: \$$amount  expect_sms: $expect_sms ════"

  # 1. Create a fresh job for the seed customer.
  local job_payload jid
  job_payload=$(jq -n --arg cid "$KIRILL_CUSTOMER_ID" --arg dt "$(date +%F)" --arg label "$label" '{
    customer_id: $cid,
    job_type: "spring_startup",
    description: ("F10 verify — " + $label),
    scheduled_date: $dt
  }')
  jid=$(api POST "/api/v1/jobs" "$job_payload" | jq -r '.id')
  [[ -n "$jid" && "$jid" != "null" ]] || { echo "✗ failed to create job"; return 1; }
  echo "  ✓ job: $jid"

  # 2. Schedule an appointment for that job (today).
  local apt_payload apt_id
  apt_payload=$(jq -n --arg jid "$jid" --arg sid "$STAFF_ID" --arg dt "$(date +%F)" '{
    job_id: $jid,
    staff_id: $sid,
    scheduled_date: $dt,
    time_window_start: "09:00:00",
    time_window_end: "11:00:00"
  }')
  apt_id=$(api POST "/api/v1/appointments" "$apt_payload" | jq -r '.id')
  [[ -n "$apt_id" && "$apt_id" != "null" ]] || { echo "✗ failed to create appointment"; return 1; }
  echo "  ✓ appointment: $apt_id"

  # 3. POST collect-payment.
  local pay_payload
  if [[ -n "$reference" ]]; then
    pay_payload=$(jq -n --arg m "$method" --arg a "$amount" --arg r "$reference" '{
      payment_method: $m,
      amount: ($a | tonumber),
      reference_number: $r
    }')
  else
    pay_payload=$(jq -n --arg m "$method" --arg a "$amount" '{
      payment_method: $m,
      amount: ($a | tonumber)
    }')
  fi
  api POST "/api/v1/appointments/$apt_id/collect-payment" "$pay_payload" >/dev/null
  echo "  ✓ collect-payment dispatched ($method, \$$amount)"

  # 4. Receipt assertion.
  if [[ "$expect_sms" == "true" ]]; then
    assert_recent_sms "$KIRILL_CUSTOMER_ID" "payment_receipt" 60
    pause_for_operator "Confirm the cash receipt SMS arrived at $SMS_TEST_PHONE."
  else
    echo "  (skipping real-SMS assertion — 24h dedup expected for $method on same run)"
  fi

  # 5. Flag assertion.
  local flag
  flag=$(api_q "/api/v1/jobs/$jid" '.payment_collected_on_site // false')
  if [[ "$flag" != "true" ]]; then
    echo "✗ FAIL: payment_collected_on_site is '$flag' for $method (expected true)." >&2
    echo "  Pre-fix this is the bug — F10 fix not deployed." >&2
    return 1
  fi
  echo "  ✓ payment_collected_on_site=true on $jid"

  # 6. Duplicate-invoice guard assertion.
  local dup_resp dup_status
  set +e
  dup_resp=$(curl -sf -w "\n%{http_code}" -X POST "$API_BASE/api/v1/invoices/generate-from-job/$jid" \
    -H "Authorization: Bearer $TOKEN" 2>&1)
  rc=$?
  set -e
  dup_status=$(echo "$dup_resp" | tail -n 1)
  dup_body=$(echo "$dup_resp" | head -n -1)
  if [[ "$rc" -eq 0 && "$dup_status" =~ ^2 ]]; then
    echo "✗ FAIL: duplicate-invoice generation succeeded with HTTP $dup_status — F10 guard bypassed." >&2
    echo "$dup_body" | jq '.' >&2 || true
    return 1
  fi
  if [[ "$dup_status" =~ ^4 ]] || echo "$dup_body" | grep -qi "collected on site"; then
    echo "  ✓ duplicate-invoice generation refused (status=$dup_status)"
  else
    echo "✗ FAIL: duplicate-invoice generation returned unexpected status='$dup_status' body=" >&2
    echo "$dup_body" >&2
    return 1
  fi
}

# Execute the 4-method matrix. Only `cash` is real-SMS; the others are
# API-only assertions (dedup-blocked SMS is expected).
run_one_method cash  "50.00" true
run_one_method check "40.00" false "CHK-1234-$(date +%s)"
run_one_method venmo "30.00" false "VENMO-abc-$(date +%s)"
run_one_method zelle "25.00" false "ZELLE-zzz-$(date +%s)"

echo
echo "✅ F10 PASSES: flag set + duplicate-invoice guard fires for all 4 non-Stripe methods."
