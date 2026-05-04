#!/usr/bin/env bash
# Shared helpers for the appointment-modal-umbrella E2E suite.
#
# Source from each phase script. Provides:
#   - ab           wrapper around agent-browser with retry
#   - psql_q       psql -tAc against $DATABASE_URL with sane PATH
#   - require_*    pre-flight assertions
#   - SHOTS_ROOT   e2e-screenshots/appointment-modal-umbrella

set -euo pipefail

export PATH="/opt/homebrew/opt/libpq/bin:$PATH"

BASE="${BASE:-http://localhost:5173}"
API_BASE="${API_BASE:-http://localhost:8000}"
E2E_USER="${E2E_USER:-admin}"
E2E_PASS="${E2E_PASS:-admin123}"
SESSION="${AGENT_BROWSER_SESSION:-umbrella-e2e}"

DATABASE_URL="${DATABASE_URL:-postgresql://grins_user:grins_password@localhost:5432/grins_platform}"
export DATABASE_URL

SHOTS_ROOT="${SHOTS_ROOT:-e2e-screenshots/appointment-modal-umbrella}"

require_tooling() {
  [[ "$(uname -s)" =~ ^(Darwin|Linux)$ ]] || { echo "unsupported platform"; exit 1; }
  command -v agent-browser >/dev/null || { echo "agent-browser missing"; exit 1; }
  command -v psql >/dev/null || { echo "psql missing"; exit 1; }
}

require_servers() {
  curl -sf "$API_BASE/health" >/dev/null || { echo "backend not reachable at $API_BASE"; exit 1; }
  curl -sf "$BASE" >/dev/null || { echo "frontend not reachable at $BASE"; exit 1; }
}

require_seed() {
  local count
  count=$(psql_q "SELECT COUNT(*) FROM service_offerings WHERE slug IS NOT NULL;")
  [[ "$count" == "73" ]] || { echo "expected 73 seeded rows, got '$count'"; exit 1; }
}

ab() {
  local tries=0
  while (( tries < 3 )); do
    if agent-browser --session "$SESSION" "$@" 2>/tmp/ab.err; then
      return 0
    fi
    local rc=$?
    tries=$((tries + 1))
    echo "  (retry $tries/3 after agent-browser failure rc=$rc) $*" >&2
    sleep 2
  done

  # Final fallback for click — bypass agent-browser's own eventing and
  # call .click() via eval. This fixes the recurring EAGAIN flake where
  # the daemon's IPC drops mid-call.
  if [[ "$1" == "click" && -n "${2:-}" ]]; then
    local sel="$2"
    if [[ "$sel" =~ ^//* ]]; then
      agent-browser --session "$SESSION" eval \
        "document.evaluate(\"$sel\",document,null,XPathResult.FIRST_ORDERED_NODE_TYPE,null).singleNodeValue?.click()" \
        >/dev/null 2>&1 && return 0
    else
      agent-browser --session "$SESSION" eval \
        "document.querySelector(\"$sel\")?.click()" \
        >/dev/null 2>&1 && return 0
    fi
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

capture_console() {
  local target="$1"
  ab console > "${target}.console.log" 2>&1 || true
  ab errors  > "${target}.errors.log"  2>&1 || true
}

# Click a Radix select option whose visible text matches. Uses eval
# so we never collide with sibling matches in the underlying page.
click_text() {
  local needle="$1"
  agent-browser --session "$SESSION" eval \
    "Array.from(document.querySelectorAll('[role=option]')).find(e => e.textContent && e.textContent.trim().includes('$needle'))?.click()" \
    >/dev/null 2>&1 || true
}

# Click any element (button/option/menuitem) whose visible text matches.
click_any_text() {
  local needle="$1"
  agent-browser --session "$SESSION" eval \
    "Array.from(document.querySelectorAll('[role=option],[role=menuitem],button,a')).find(e => e.textContent && e.textContent.trim().includes('$needle'))?.click()" \
    >/dev/null 2>&1 || true
}

# Switch the schedule page to list view and open the first
# appointment whose status is in the desired set. Returns the
# appointment id via stdout for downstream use, or empty string
# on failure.
open_first_appointment_modal() {
  local statuses="${1:-scheduled,en_route,confirmed,in_progress}"
  ab open "$BASE/schedule"
  ab wait --load networkidle
  sleep 2
  agent-browser --session "$SESSION" eval \
    "document.querySelector('[data-testid=view-list]')?.click()" >/dev/null 2>&1 || true
  sleep 2
  local appt_id
  appt_id=$(agent-browser --session "$SESSION" eval \
    "(() => { const wanted = '${statuses}'.split(','); const rows = Array.from(document.querySelectorAll('[data-testid=appointment-row]')); for (const row of rows) { const status = Array.from(row.querySelectorAll('[data-testid^=status-]')).map(e=>e.dataset.testid.replace('status-',''))[0]; if (!status || wanted.includes(status)) { const link = row.querySelector('[data-testid^=view-appointment-]'); if (link) return link.dataset.testid.replace('view-appointment-',''); } } return ''; })()" \
    2>/dev/null | tail -1 | tr -d '"')
  if [[ -z "$appt_id" ]]; then
    echo ""
    return 1
  fi
  agent-browser --session "$SESSION" eval \
    "document.querySelector('[data-testid=view-appointment-${appt_id}]')?.click()" \
    >/dev/null 2>&1 || true
  sleep 4
  echo "$appt_id"
}

# Click the first element whose data-testid prefix matches.
click_first_testid() {
  local prefix="$1"
  agent-browser --session "$SESSION" eval \
    "document.querySelector('[data-testid^=\"$prefix\"]')?.click()" >/dev/null 2>&1 || true
}

# Sourced — do not exit on early-return from helpers.
return 0 2>/dev/null || true
