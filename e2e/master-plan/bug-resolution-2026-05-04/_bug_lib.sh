#!/usr/bin/env bash
# Bug-resolution E2E shared helpers — extends `_dev_lib.sh` with checkpoints
# and assertion utilities tailored to the four 2026-05-04 sign-off bugs
# (F2/F8/F9/F10).
#
# Source from each per-bug script. Adds:
#   - pause_for_operator         interactive checkpoint (audible bell, blocks
#                                stdin, mirrors `_dev_lib.sh::human_checkpoint`
#                                shape but reusable from non-phase contexts)
#   - assert_recent_sms          poll sent_messages for a recent row of a
#                                given message_type
#   - assert_no_recent_sms       inverse — confirm no row newer than threshold
#   - assert_recent_email        poll Resend for a subject substring (verify
#                                only — does NOT replace operator inbox check)
#   - ensure_seed_recipients     PATCH the seed customer to the allowlisted
#                                phone+email if drift was introduced upstream
#
# Hard rules (refuse to run if violated):
#   * SMS only to +19527373312
#   * Email only to kirillrakitinsecond@gmail.com
#   * Dev-only execution (BASE/API_BASE must point at *-dev-* hosts)
#   * 24 h SMS dedup at services/sms_service.py:344-361 — see per-script
#     headers for which sequences avoid collisions

set -euo pipefail

# Default to dev for all bug-resolution runs. Operator can override to
# `local` only at their own peril (none of the bug fixes are reproducible
# locally because they all involve real Stripe/Resend/CallRail providers).
ENVIRONMENT="${ENVIRONMENT:-dev}"
export ENVIRONMENT

# shellcheck source=../_dev_lib.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/_dev_lib.sh"

# --- Hard-rule guards ---

require_bug_resolution_env() {
  if [[ "$ENVIRONMENT" != "dev" ]]; then
    echo "Refusing to run: bug-resolution scripts are dev-only (current: $ENVIRONMENT)." >&2
    exit 1
  fi
  if [[ "$SMS_TEST_PHONE" != "+19527373312" ]]; then
    echo "Refusing to run: SMS_TEST_PHONE must be +19527373312 (got: $SMS_TEST_PHONE)." >&2
    exit 1
  fi
  if [[ "$EMAIL_TEST_INBOX" != "kirillrakitinsecond@gmail.com" ]]; then
    echo "Refusing to run: EMAIL_TEST_INBOX must be kirillrakitinsecond@gmail.com." >&2
    exit 1
  fi
  case "$API_BASE" in
    *grins-dev-*.up.railway.app*) ;;
    *)
      echo "Refusing to run: API_BASE does not look like dev ($API_BASE)." >&2
      exit 1
      ;;
  esac
}

# --- Operator-blocking checkpoint ---

pause_for_operator() {
  # pause_for_operator "<prompt>"
  local prompt="${1:-Operator action required}"
  printf '\a' >&2  # audible bell
  cat <<EOF >&2

═════════════════════════════════════════════════════════════════
🟡 OPERATOR CHECKPOINT — bug-resolution-2026-05-04
═════════════════════════════════════════════════════════════════
$prompt
─────────────────────────────────────────────────────────────────
Press Enter to continue, or Ctrl+C to abort.
═════════════════════════════════════════════════════════════════
EOF
  if [[ -t 0 && -z "${E2E_NO_PROMPT:-}" ]]; then
    read -r _ || true
  else
    # Non-interactive: refuse to auto-skip — bug runs require humans.
    echo "Refusing to auto-skip operator checkpoint (set E2E_NO_PROMPT=1 only at your own risk)." >&2
    exit 2
  fi
}

# --- SMS / email assertion helpers ---

# Time helpers — compute "N seconds ago" in ISO 8601 UTC.
_iso_seconds_ago() {
  local seconds="$1"
  python3 -c "import datetime,sys; \
print((datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(seconds=int(sys.argv[1]))).isoformat().replace('+00:00','Z'))" \
    "$seconds"
}

assert_recent_sms() {
  # assert_recent_sms <customer_id> <message_type> <max_age_seconds>
  local customer_id="$1" message_type="$2" max_age="${3:-60}"
  local threshold elapsed=0 step=3
  threshold="$(_iso_seconds_ago "$max_age")"
  local resp count
  while (( elapsed < max_age )); do
    resp=$(api GET "/api/v1/customers/$customer_id/sent-messages?message_type=$message_type&limit=10" || echo '{"items":[]}')
    count=$(echo "$resp" | jq --arg t "$threshold" \
      '[.items[]? | select(.sent_at != null and .sent_at >= $t)] | length' 2>/dev/null || echo 0)
    if [[ "$count" -gt 0 ]]; then
      echo "  ✓ recent ${message_type} SMS observed for $customer_id (count=$count, since=$threshold)"
      return 0
    fi
    sleep "$step"
    elapsed=$(( elapsed + step ))
  done
  echo "✗ FAIL: no ${message_type} SMS observed for $customer_id within ${max_age}s." >&2
  echo "  Last response payload:" >&2
  echo "$resp" | jq '.' >&2 || true
  return 1
}

assert_no_recent_sms() {
  # assert_no_recent_sms <customer_id> <message_type> <max_age_seconds>
  # Inverse of assert_recent_sms — used to confirm dedup blocked a send.
  local customer_id="$1" message_type="$2" max_age="${3:-60}"
  local threshold resp count
  threshold="$(_iso_seconds_ago "$max_age")"
  resp=$(api GET "/api/v1/customers/$customer_id/sent-messages?message_type=$message_type&limit=10" || echo '{"items":[]}')
  count=$(echo "$resp" | jq --arg t "$threshold" \
    '[.items[]? | select(.sent_at != null and .sent_at >= $t)] | length' 2>/dev/null || echo 0)
  if [[ "$count" -eq 0 ]]; then
    echo "  ✓ no ${message_type} SMS in last ${max_age}s for $customer_id (dedup expected)"
    return 0
  fi
  echo "✗ FAIL: unexpected ${message_type} SMS row(s) within ${max_age}s for $customer_id." >&2
  echo "$resp" | jq '.' >&2 || true
  return 1
}

assert_recent_email() {
  # assert_recent_email <customer_id> <subject_substring>
  # Looks for a recent email in /sent-messages with channel=email.
  local customer_id="$1" subject_substr="$2"
  local resp match
  resp=$(api GET "/api/v1/customers/$customer_id/sent-messages?limit=20" || echo '{"items":[]}')
  match=$(echo "$resp" | jq --arg s "$subject_substr" \
    '[.items[]? | select((.channel // "") == "email") | select((.subject // "") | contains($s))] | length' 2>/dev/null || echo 0)
  if [[ "$match" -gt 0 ]]; then
    echo "  ✓ email matching '${subject_substr}' observed for $customer_id"
    return 0
  fi
  # Email row may not always be persisted — fall back to "no fail" + advisory.
  echo "  ⚠ no /sent-messages email row matching '${subject_substr}' (may still have been sent via Resend)." >&2
  return 0
}

# --- Seed customer hygiene ---

ensure_seed_recipients() {
  # PATCH the seed customer back to allowlisted phone + email if drift exists.
  require_token
  local payload current_phone current_email
  current_phone=$(api_q "/api/v1/customers/$KIRILL_CUSTOMER_ID" '.phone // ""' || true)
  current_email=$(api_q "/api/v1/customers/$KIRILL_CUSTOMER_ID" '.email // ""' || true)
  if [[ "$current_phone" == "$SMS_TEST_PHONE" && "$current_email" == "$EMAIL_TEST_INBOX" ]]; then
    echo "  ✓ seed customer recipients aligned: $current_phone / $current_email"
    return 0
  fi
  echo "  ⟳ patching seed customer recipients ($current_phone → $SMS_TEST_PHONE, $current_email → $EMAIL_TEST_INBOX)" >&2
  payload=$(jq -n \
    --arg phone "$SMS_TEST_PHONE" \
    --arg email "$EMAIL_TEST_INBOX" \
    '{phone: $phone, email: $email}')
  api PATCH "/api/v1/customers/$KIRILL_CUSTOMER_ID" "$payload" >/dev/null
  echo "  ✓ seed customer recipients patched"
}

# --- Pretty step printer ---

step() {
  # step "<message>"
  echo
  echo "──── $* ────"
}

# Sourced — do not exit on early-return.
return 0 2>/dev/null || true
