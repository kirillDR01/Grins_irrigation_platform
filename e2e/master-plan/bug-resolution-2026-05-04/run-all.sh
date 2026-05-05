#!/usr/bin/env bash
# Run all four bug-resolution scripts in the order that minimizes 24h
# SMS-dedup collisions:
#
#   1. F9 — pure API, no SMS, no email (safe, fast)
#   2. F2 — real email, no real SMS
#   3. F10 — real `payment_receipt` SMS for cash; API-only for the rest
#   4. F8 — real Stripe pay → real `payment_link_sent` + `payment_receipt`
#           SMS, on a FRESH customer (so the seed customer's dedup slot
#           used by F10 doesn't matter)
#
# Each script exits non-zero on failure. This runner aborts at the first
# failure and prints which fix appears to be missing on the build.

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_bug_lib.sh
source "$ROOT/_bug_lib.sh"

require_bug_resolution_env
require_tooling
require_token

run_script() {
  # run_script <label> <script-path>
  local label="$1" path="$2"
  echo
  echo "═══════════════════════════════════════════════════════════════════"
  echo "▶ $label — $path"
  echo "═══════════════════════════════════════════════════════════════════"
  local started ended
  started=$(date +%s)
  if ! "$path"; then
    echo
    echo "✗ ABORTED: $label failed. The corresponding fix is likely missing on this build." >&2
    exit 1
  fi
  ended=$(date +%s)
  echo "✓ $label completed in $(( ended - started ))s"
}

run_script "F9 — appointments customer_id filter" "$ROOT/f9-appointments-customer-id-filter.sh"
run_script "F2 — estimate rejection_reason roundtrip" "$ROOT/f2-estimate-rejection-reason-roundtrip.sh"
run_script "F10 — collect_payment flag + duplicate guard" "$ROOT/f10-collect-payment-flag-and-duplicate-guard.sh"
run_script "F8 — Stripe Payment Link receipt" "$ROOT/f8-stripe-payment-link-receipt.sh"

echo
echo "═══════════════════════════════════════════════════════════════════"
echo "✅ ALL FOUR BUG-RESOLUTION SCRIPTS PASSED"
echo "═══════════════════════════════════════════════════════════════════"
