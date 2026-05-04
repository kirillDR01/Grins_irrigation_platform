#!/usr/bin/env bash
# Resend email retrieval helper.
#
# Fetches recent emails sent through Resend so phase scripts can verify email
# delivery without a human reading the inbox. Used by Phase 5 (estimate email
# portal), Phase 14 (payment-link receipt email), Phase 4 (SignWell email).
#
# Two modes:
#   list        list recent sends with id/to/subject/status
#   get <id>    fetch a single email by Resend message id
#   poll <to> <substring> [timeout_seconds]
#               wait until an email to <to> with subject containing <substring>
#               appears (or timeout). Prints the message id on success.
#
# Env:
#   RESEND_API_KEY    required — read-only API key works for retrieve
#
# Reference:
#   - https://resend.com/docs/api-reference/emails/retrieve-email
#   - https://resend.com/docs/api-reference/emails/list-emails (if available)
#
# NOTE: As of writing, Resend's email-list endpoint is in beta. The simplest
# stable approach is to record the message id at send time (the
# `services/email_service.py:_send_email` returns the resend id) and call
# the retrieve endpoint by id.
#
# This helper supports a `poll` mode that hits the `sent_messages` API on the
# Grins backend (which mirrors Resend send results) instead of Resend's API
# directly when a token + customer id are known. That's the robust path.
#
# Usage examples:
#   sim/resend_email_check.sh poll kirillrakitinsecond@gmail.com "Your estimate"
#   sim/resend_email_check.sh get re_abc123

set -euo pipefail

MODE="${1:?usage: sim/resend_email_check.sh <list|get|poll> ...}"
shift || true

API_BASE="${API_BASE:-http://localhost:8000}"
RESEND_API_KEY="${RESEND_API_KEY:-}"

case "$MODE" in
  get)
    RESEND_ID="${1:?usage: get <resend_message_id>}"
    [[ -n "$RESEND_API_KEY" ]] || { echo "RESEND_API_KEY required for get"; exit 1; }
    curl -sS \
      -H "Authorization: Bearer $RESEND_API_KEY" \
      "https://api.resend.com/emails/$RESEND_ID"
    ;;

  list)
    [[ -n "$RESEND_API_KEY" ]] || { echo "RESEND_API_KEY required for list"; exit 1; }
    # If list endpoint is unavailable, fall back to grins_platform sent_messages.
    curl -sS \
      -H "Authorization: Bearer $RESEND_API_KEY" \
      "https://api.resend.com/emails?limit=50" 2>/dev/null \
      || {
        echo "Resend list endpoint unavailable; querying backend sent_messages instead." >&2
        : "${TOKEN:?TOKEN must be set when using sent_messages fallback}"
        curl -sS -H "Authorization: Bearer $TOKEN" \
          "$API_BASE/api/v1/sent-messages?channel=email&limit=50"
      }
    ;;

  poll)
    TO_ADDR="${1:?usage: poll <to_address> <subject_substring> [timeout]}"
    SUBJECT_SUBSTR="${2:?usage: poll <to_address> <subject_substring> [timeout]}"
    TIMEOUT="${3:-90}"
    : "${TOKEN:?TOKEN must be set so we can query sent_messages}"

    # Polls backend sent_messages for an outbound email matching the criteria.
    # This is more reliable than Resend's list endpoint and works through the
    # email-allowlist guard.
    DEADLINE=$(( $(date +%s) + TIMEOUT ))
    while (( $(date +%s) < DEADLINE )); do
      RESULT=$(curl -sS -H "Authorization: Bearer $TOKEN" \
        "$API_BASE/api/v1/sent-messages?channel=email&limit=20" \
        | jq -r --arg to "$TO_ADDR" --arg sub "$SUBJECT_SUBSTR" \
          '.items[] | select(.recipient == $to or .recipient_email == $to) | select(.subject // "" | contains($sub)) | .id' \
        | head -1)
      if [[ -n "$RESULT" ]]; then
        echo "$RESULT"
        exit 0
      fi
      sleep 3
    done
    echo "TIMEOUT: no matching email after ${TIMEOUT}s" >&2
    exit 1
    ;;

  *)
    echo "Unknown mode: $MODE (expected: list | get | poll)" >&2
    exit 1
    ;;
esac
