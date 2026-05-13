#!/usr/bin/env bash
# Cluster C — shared helpers for the Job Creation + SignWell removal E2E
# suite. Sourced from each phase script (`01-..05-`).
#
# Hard rules (refuse to run if violated):
#   * SMS only to +19527373312
#   * Email only to kirillrakitinsecond@gmail.com
#   * Dev-only execution (BASE/API_BASE must point at *-dev-* hosts when
#     ENVIRONMENT=dev). Local runs allowed when ENVIRONMENT=local but the
#     recipient allowlist still applies.

set -euo pipefail

export PATH="/opt/homebrew/opt/libpq/bin:$PATH"

ENVIRONMENT="${ENVIRONMENT:-dev}"
export ENVIRONMENT

SMS_TEST_PHONE="${SMS_TEST_PHONE:-+19527373312}"
EMAIL_TEST_INBOX="${EMAIL_TEST_INBOX:-kirillrakitinsecond@gmail.com}"
export SMS_TEST_PHONE EMAIL_TEST_INBOX

BASE="${BASE:-http://localhost:5173}"
API_BASE="${API_BASE:-http://localhost:8000}"
E2E_USER="${E2E_USER:-admin}"
E2E_PASS="${E2E_PASS:-admin123}"
SESSION="${AGENT_BROWSER_SESSION:-cluster-c-e2e}"

DATABASE_URL="${DATABASE_URL:-postgresql://grins_user:grins_password@localhost:5432/grins_platform}"
export DATABASE_URL

SHOTS_ROOT="${SHOTS_ROOT:-e2e-screenshots/cluster-c}"

require_cluster_c_env() {
  if [[ "$SMS_TEST_PHONE" != "+19527373312" ]]; then
    echo "Refusing to run: SMS_TEST_PHONE must be +19527373312 (got: $SMS_TEST_PHONE)." >&2
    exit 1
  fi
  if [[ "$EMAIL_TEST_INBOX" != "kirillrakitinsecond@gmail.com" ]]; then
    echo "Refusing to run: EMAIL_TEST_INBOX must be kirillrakitinsecond@gmail.com (got: $EMAIL_TEST_INBOX)." >&2
    exit 1
  fi
  if [[ "$ENVIRONMENT" != "dev" && "$ENVIRONMENT" != "local" ]]; then
    echo "Refusing to run: ENVIRONMENT must be dev or local (got: $ENVIRONMENT)." >&2
    exit 1
  fi
}

require_tooling() {
  [[ "$(uname -s)" =~ ^(Darwin|Linux)$ ]] || { echo "unsupported platform"; exit 1; }
  command -v agent-browser >/dev/null || {
    echo "agent-browser missing. Install: npm install -g agent-browser && agent-browser install --with-deps" >&2
    exit 1
  }
  command -v psql >/dev/null || { echo "psql missing"; exit 1; }
  command -v curl >/dev/null || { echo "curl missing"; exit 1; }
  command -v jq >/dev/null || { echo "jq missing"; exit 1; }
}

require_servers() {
  curl -sf "$API_BASE/health" >/dev/null || { echo "backend not reachable at $API_BASE"; exit 1; }
  curl -sf "$BASE" >/dev/null || { echo "frontend not reachable at $BASE"; exit 1; }
}

ab() {
  local tries=0
  while (( tries < 3 )); do
    if agent-browser --session "$SESSION" "$@" 2>/tmp/ab.err; then
      return 0
    fi
    tries=$((tries + 1))
    echo "  (retry $tries/3) $*" >&2
    sleep 2
  done
  if [[ "$1" == "click" && -n "${2:-}" ]]; then
    agent-browser --session "$SESSION" eval \
      "document.querySelector(\"$2\")?.click()" \
      >/dev/null 2>&1 && return 0
  fi
  return 1
}

psql_q() {
  psql "$DATABASE_URL" -tAc "$1"
}

login_admin() {
  ab open "$BASE/login"
  ab wait --load networkidle
  ab fill "[data-testid='username-input']" "$E2E_USER"
  ab fill "[data-testid='password-input']" "$E2E_PASS"
  ab click "[data-testid='login-btn']"
  ab wait --load networkidle
  sleep 2
}

# Assert the appointment row in the DB has the expected status. Exits
# non-zero if drift is detected so the calling script aborts.
assert_appointment_status() {
  local appointment_id="$1"
  local expected="$2"
  local actual
  actual=$(psql_q "SELECT status FROM appointments WHERE id='${appointment_id}'")
  if [[ "$actual" != "$expected" ]]; then
    echo "FAIL: appointment ${appointment_id} status=${actual}, expected ${expected}" >&2
    exit 1
  fi
}

# Assert a job row has the given category. Used by Phase A + B.
assert_job_category() {
  local job_id="$1"
  local expected="$2"
  local actual
  actual=$(psql_q "SELECT category FROM jobs WHERE id='${job_id}'")
  if [[ "$actual" != "$expected" ]]; then
    echo "FAIL: job ${job_id} category=${actual}, expected ${expected}" >&2
    exit 1
  fi
}

# Sourced — do not exit on early-return from helpers.
return 0 2>/dev/null || true
