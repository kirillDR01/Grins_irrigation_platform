#!/usr/bin/env bash
# F9 — GET /api/v1/appointments?customer_id=<uuid> filter narrows results.
#
# Pure API exercise: no SMS, no email, no Stripe — safe to run any time and
# always first in the sequence. Reproduces the bug observed in
# `e2e-screenshots/master-plan/runs/2026-05-04-full-real-emails/E2E-SIGNOFF-REPORT.md`
# where the endpoint silently dropped `customer_id` and returned the global
# appointment list.
#
# Pre-fix: filtered call returns rows from OTHER customers.
# Post-fix: filtered call returns only the targeted customer's rows.
#
# Cleanup: leaves the two created customers in dev as fixture data — the
# script tags them with the slug `f9-livecheck-{epoch}` so they are easy
# to grep / GC later.

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_bug_lib.sh
source "$ROOT/_bug_lib.sh"

require_bug_resolution_env
require_tooling
require_seed_customer
require_token

EPOCH=$(date +%s)
TAG="f9-livecheck-$EPOCH"

step "Creating customer A ($TAG-A)"
PAYLOAD_A=$(jq -n --arg tag "$TAG-A" --arg phone "$SMS_TEST_PHONE" --arg email "$EMAIL_TEST_INBOX" '{
  first_name: ("F9-" + $tag),
  last_name: "Verify",
  phone: $phone,
  email: $email,
  street_address: "1 Verify Way",
  city: "Test City",
  state: "MN",
  zip_code: "55401",
  sms_opt_in: true,
  email_opt_in: true
}')
CID_A=$(api POST "/api/v1/customers" "$PAYLOAD_A" | jq -r '.id')
[[ -n "$CID_A" && "$CID_A" != "null" ]] || { echo "✗ failed to create customer A"; exit 1; }
echo "  ✓ customer A: $CID_A"

step "Creating customer B ($TAG-B)"
PAYLOAD_B=$(jq -n --arg tag "$TAG-B" --arg phone "$SMS_TEST_PHONE" --arg email "$EMAIL_TEST_INBOX" '{
  first_name: ("F9-" + $tag),
  last_name: "Verify",
  phone: $phone,
  email: $email,
  street_address: "2 Verify Way",
  city: "Test City",
  state: "MN",
  zip_code: "55401",
  sms_opt_in: true,
  email_opt_in: true
}')
CID_B=$(api POST "/api/v1/customers" "$PAYLOAD_B" | jq -r '.id')
[[ -n "$CID_B" && "$CID_B" != "null" ]] || { echo "✗ failed to create customer B"; exit 1; }
echo "  ✓ customer B: $CID_B"

step "Creating job + appointment for each customer"
TODAY=$(date +%F)
TOMORROW=$(python3 -c "import datetime; print((datetime.date.today() + datetime.timedelta(days=1)).isoformat())")

for label in A B; do
  if [[ "$label" == "A" ]]; then
    cid="$CID_A"
  else
    cid="$CID_B"
  fi
  JOB_PAYLOAD=$(jq -n --arg cid "$cid" --arg dt "$TODAY" '{
    customer_id: $cid,
    job_type: "spring_startup",
    description: ("F9 verify job for customer " + $cid),
    scheduled_date: $dt
  }')
  JID=$(api POST "/api/v1/jobs" "$JOB_PAYLOAD" | jq -r '.id')
  [[ -n "$JID" && "$JID" != "null" ]] || { echo "✗ failed to create job for $label"; exit 1; }
  echo "  ✓ job ($label): $JID"

  STAFF_ID=$(api_q "/api/v1/staff?role=tech&limit=1" '.items[0].id // .items[0].staff_id // ""')
  [[ -n "$STAFF_ID" ]] || { echo "✗ no tech staff present"; exit 1; }

  APT_PAYLOAD=$(jq -n --arg jid "$JID" --arg sid "$STAFF_ID" --arg dt "$TOMORROW" '{
    job_id: $jid,
    staff_id: $sid,
    scheduled_date: $dt,
    time_window_start: "09:00:00",
    time_window_end: "11:00:00"
  }')
  APT_ID=$(api POST "/api/v1/appointments" "$APT_PAYLOAD" | jq -r '.id')
  [[ -n "$APT_ID" && "$APT_ID" != "null" ]] || { echo "✗ failed to create appointment for $label"; exit 1; }
  echo "  ✓ appointment ($label): $APT_ID"
  if [[ "$label" == "A" ]]; then
    APT_A="$APT_ID"
  else
    APT_B="$APT_ID"
  fi
done

step "Filter A: GET /api/v1/appointments?customer_id=$CID_A"
RESP_A=$(api GET "/api/v1/appointments?customer_id=$CID_A&page_size=20")
COUNT_A=$(echo "$RESP_A" | jq '.items | length')
OTHER_A=$(echo "$RESP_A" | jq --arg c "$CID_A" '[.items[] | select(.job.customer_id != $c)] | length')
echo "  items=$COUNT_A, items-not-belonging-to-A=$OTHER_A"
if [[ "$OTHER_A" -gt 0 ]]; then
  echo "✗ FAIL: customer-id filter returned $OTHER_A row(s) for OTHER customers — F9 fix likely missing." >&2
  echo "$RESP_A" | jq '.items[] | {id, "customer_id_on_job": (.job.customer_id)}' >&2
  exit 1
fi

step "Filter B: GET /api/v1/appointments?customer_id=$CID_B"
RESP_B=$(api GET "/api/v1/appointments?customer_id=$CID_B&page_size=20")
COUNT_B=$(echo "$RESP_B" | jq '.items | length')
OTHER_B=$(echo "$RESP_B" | jq --arg c "$CID_B" '[.items[] | select(.job.customer_id != $c)] | length')
echo "  items=$COUNT_B, items-not-belonging-to-B=$OTHER_B"
if [[ "$OTHER_B" -gt 0 ]]; then
  echo "✗ FAIL: customer-id filter for B returned rows from other customers." >&2
  exit 1
fi

step "No filter: GET /api/v1/appointments → both customers must appear"
RESP_ALL=$(api GET "/api/v1/appointments?page_size=100")
SAW_A=$(echo "$RESP_ALL" | jq --arg c "$CID_A" '[.items[] | select(.job.customer_id == $c)] | length')
SAW_B=$(echo "$RESP_ALL" | jq --arg c "$CID_B" '[.items[] | select(.job.customer_id == $c)] | length')
if [[ "$SAW_A" -lt 1 || "$SAW_B" -lt 1 ]]; then
  echo "⚠ unfiltered list missing one of the new customers (A=$SAW_A, B=$SAW_B). May be paginated past page 1." >&2
fi

echo
echo "✅ F9 PASSES: customer_id filter narrows results post-fix. Created customers (kept as fixtures): $CID_A, $CID_B"
