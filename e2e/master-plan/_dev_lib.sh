#!/usr/bin/env bash
# Master-plan E2E shared helpers — dev/prod environment aware.
#
# Source from each phase script. Provides:
#   - ab            wrapper around agent-browser with retry + eval fallback
#   - api           authenticated curl wrapper that auto-renews $TOKEN
#   - login_admin   admin login on whichever frontend $BASE points to
#   - login_tech    tech login (vasiliy/steve/gennadiy) for Phase 11 mobile
#   - require_*     pre-flight assertions (tooling, servers, allowlists, seed)
#   - shot          screenshot helper with auto-numbered files per phase
#   - SHOTS_ROOT    e2e-screenshots/master-plan
#
# Environment defaults to LOCAL. Set ENVIRONMENT=dev to target dev Vercel +
# Railway dev. Override individual values explicitly to hit other targets.
#
# Authoritative for the dev URLs / seed identities is
# `Testing Procedure/00-preflight.md`.

set -euo pipefail

export PATH="/opt/homebrew/opt/libpq/bin:$PATH"

ENVIRONMENT="${ENVIRONMENT:-local}"

case "$ENVIRONMENT" in
  local)
    BASE="${BASE:-http://localhost:5173}"
    API_BASE="${API_BASE:-http://localhost:8000}"
    DATABASE_URL="${DATABASE_URL:-postgresql://grins_user:grins_password@localhost:5432/grins_platform}"
    ;;
  dev)
    BASE="${BASE:-https://grins-irrigation-platform-git-dev-kirilldr01s-projects.vercel.app}"
    MARKETING_BASE="${MARKETING_BASE:-https://grins-irrigation-git-dev-kirilldr01s-projects.vercel.app}"
    API_BASE="${API_BASE:-https://grins-dev-dev.up.railway.app}"
    # Direct DB unreachable from laptop on dev — use REST or `railway ssh`.
    DATABASE_URL=""
    RAILWAY_PROJECT="${RAILWAY_PROJECT:-zealous-heart}"
    RAILWAY_ENV="${RAILWAY_ENV:-dev}"
    RAILWAY_SERVICE="${RAILWAY_SERVICE:-Grins-dev}"
    ;;
  *)
    echo "Unknown ENVIRONMENT='$ENVIRONMENT' (expected: local | dev)" >&2
    exit 1
    ;;
esac

E2E_USER="${E2E_USER:-admin}"
E2E_PASS="${E2E_PASS:-admin123}"
E2E_TECH_USER="${E2E_TECH_USER:-vasiliy}"
E2E_TECH_PASS="${E2E_TECH_PASS:-tech123}"

SESSION="${AGENT_BROWSER_SESSION:-master-plan}"

# Seed identities — re-aligned 2026-05-02 after dev DB drift.
# The historical Kirill seed (e7ba9b51-...) and admin staff (0bb0466d-...) IDs
# documented in older docs are NOT present on current dev. The active E2E seed
# customer is a44dc81f-... (phone 9527373312, email kirillrakitinsecond@gmail.com,
# both opt-ins true). Admin auth uses the `admin` user account (admin/admin123)
# which has no staff_id linkage and does not need one.
KIRILL_CUSTOMER_ID="${KIRILL_CUSTOMER_ID:-a44dc81f-ce81-4a6f-81f5-4676886cef1a}"
SMS_TEST_PHONE="${SMS_TEST_PHONE:-+19527373312}"
EMAIL_TEST_INBOX="${EMAIL_TEST_INBOX:-kirillrakitinsecond@gmail.com}"

SHOTS_ROOT="${SHOTS_ROOT:-e2e-screenshots/master-plan}"
PHASE="${PHASE:-unset}"
SHOT_DIR="$SHOTS_ROOT/$PHASE"
SHOT_COUNTER=0

export BASE API_BASE E2E_USER E2E_PASS SESSION KIRILL_CUSTOMER_ID \
       SMS_TEST_PHONE EMAIL_TEST_INBOX SHOTS_ROOT PHASE SHOT_DIR \
       ENVIRONMENT MARKETING_BASE \
       DATABASE_URL E2E_TECH_USER E2E_TECH_PASS

# RAILWAY_PROJECT / RAILWAY_ENV / RAILWAY_SERVICE are intentionally NOT exported.
# Railway CLI treats those env vars as "use service-account mode" and then requires
# RAILWAY_TOKEN, which we don't set — child invocations would fail with
# "Unauthorized." Keep them as shell-local script vars; they remain visible to the
# helper functions in this lib without leaking to the railway CLI subprocess.

mkdir -p "$SHOT_DIR" 2>/dev/null || true

# --- Tooling guards ---

require_tooling() {
  [[ "$(uname -s)" =~ ^(Darwin|Linux)$ ]] || { echo "unsupported platform"; exit 1; }
  command -v agent-browser >/dev/null || { echo "agent-browser missing — npm i -g agent-browser && agent-browser install --with-deps"; exit 1; }
  command -v jq >/dev/null            || { echo "jq missing — install via brew/apt"; exit 1; }
  command -v curl >/dev/null          || { echo "curl missing"; exit 1; }
  command -v python3 >/dev/null       || { echo "python3 missing"; exit 1; }
  if [[ "$ENVIRONMENT" == "local" ]]; then
    command -v psql >/dev/null        || { echo "psql missing (local only)"; exit 1; }
  fi
  if [[ "$ENVIRONMENT" == "dev" ]]; then
    command -v railway >/dev/null     || { echo "railway CLI missing"; exit 1; }
  fi
}

require_servers() {
  curl -sf "$API_BASE/health" >/dev/null || { echo "backend not reachable at $API_BASE"; exit 1; }
  curl -sf "$BASE" >/dev/null            || { echo "frontend not reachable at $BASE"; exit 1; }
}

require_dev_railway_link() {
  [[ "$ENVIRONMENT" == "dev" ]] || return 0
  local status
  status=$(railway status 2>&1 || true)
  echo "$status" | grep -q "$RAILWAY_PROJECT"  || { echo "railway not linked to $RAILWAY_PROJECT"; exit 1; }
  echo "$status" | grep -q "$RAILWAY_ENV"      || { echo "railway not on env $RAILWAY_ENV";    exit 1; }
}

# --- Auth ---

login_get_token() {
  # Returns access_token via stdout; caller exports.
  curl -sf -X POST "$API_BASE/api/v1/auth/login" \
    -H 'Content-Type: application/json' \
    -d "{\"username\":\"${1:-$E2E_USER}\",\"password\":\"${2:-$E2E_PASS}\"}" \
    | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])'
}

require_token() {
  if [[ -z "${TOKEN:-}" || "${#TOKEN}" -lt 100 ]]; then
    TOKEN=$(login_get_token "$E2E_USER" "$E2E_PASS")
    export TOKEN
  fi
  [[ "${#TOKEN}" -gt 100 ]] || { echo "token acquisition failed"; exit 1; }
}

# --- agent-browser wrapper (proven pattern from e2e/_lib.sh) ---

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
  # Fallback for click — eval bypasses daemon eventing.
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

# Verified login pattern. LoginPage.tsx:162/182/219 — username/password/login.
login_admin() {
  ab open "$BASE/login"
  ab wait --load networkidle
  ab fill "[data-testid='username-input']" "$E2E_USER"
  ab fill "[data-testid='password-input']" "$E2E_PASS"
  ab click "[data-testid='login-btn']"
  ab wait --load networkidle
  sleep 2
}

login_tech() {
  # Tech credentials seeded via migrations/versions/20250626_100000_seed_demo_data.py.
  # Usernames: vasiliy / steve / gennadiy. Password: tech123.
  ab set viewport 375 812
  ab open "$BASE/login"
  ab wait --load networkidle
  ab fill "[data-testid='username-input']" "$E2E_TECH_USER"
  ab fill "[data-testid='password-input']" "$E2E_TECH_PASS"
  ab click "[data-testid='login-btn']"
  ab wait --load networkidle
  sleep 2
}

# --- API helpers (REST-first verification per Testing Procedure §Golden rule 4) ---

api() {
  # api METHOD PATH [DATA_JSON]
  # Returns response body via stdout.
  require_token
  local method="$1" path="$2" data="${3:-}"
  if [[ -n "$data" ]]; then
    curl -sf -X "$method" "$API_BASE$path" \
      -H "Authorization: Bearer $TOKEN" \
      -H 'Content-Type: application/json' \
      -d "$data"
  else
    curl -sf -X "$method" "$API_BASE$path" \
      -H "Authorization: Bearer $TOKEN"
  fi
}

# REST-first DB-state replacement when running on dev (no direct psql).
# Pass a JSON-path expression to extract a single field.
api_q() {
  # api_q PATH JQ_EXPR
  api GET "$1" | jq -r "$2"
}

psql_q() {
  # Local-only. On dev, prefer api_q.
  [[ -n "$DATABASE_URL" ]] || { echo "psql_q called without DATABASE_URL — dev environment? Use api_q." >&2; return 1; }
  psql "$DATABASE_URL" -tAc "$1"
}

# Run python inside the deployed container for deeper queries (dev only).
railway_python() {
  # railway_python <python source string>
  [[ "$ENVIRONMENT" == "dev" ]] || { echo "railway_python only on dev"; return 1; }
  local src_file b64
  src_file=$(mktemp)
  printf '%s' "$1" > "$src_file"
  b64=$(base64 < "$src_file" | tr -d '\n')
  rm "$src_file"
  railway ssh --service "$RAILWAY_SERVICE" --environment "$RAILWAY_ENV" \
    "python3 -c 'import base64,os; exec(base64.b64decode(\"$b64\"))'"
}

# --- Required env-var assertions (run in P0) ---

require_dev_env_vars() {
  [[ "$ENVIRONMENT" == "dev" ]] || return 0
  local kv
  kv=$(railway variables --service "$RAILWAY_SERVICE" --environment "$RAILWAY_ENV" --kv 2>/dev/null || true)
  # SignWell removed 2026-05-02 — not directly used in this stack.
  for var in SMS_PROVIDER SMS_TEST_PHONE_ALLOWLIST EMAIL_TEST_ADDRESS_ALLOWLIST CALLRAIL_TRACKING_NUMBER GOOGLE_REVIEW_URL CALLRAIL_WEBHOOK_SECRET STRIPE_WEBHOOK_SECRET; do
    echo "$kv" | grep -q "^${var}=" || { echo "missing dev env var: $var"; exit 1; }
  done
}

require_seed_customer() {
  # /customers?search= queries name fields only — phone-keyed lookup needs
  # detail GET. Re-aligned 2026-05-02 to do that directly.
  require_token
  local got
  got=$(api GET "/api/v1/customers/$KIRILL_CUSTOMER_ID" | jq -r '.id // empty')
  [[ "$got" == "$KIRILL_CUSTOMER_ID" ]] || { echo "seed customer $KIRILL_CUSTOMER_ID missing"; exit 1; }
}

# --- Screenshots ---

shot() {
  # shot <slug>  →  $SHOT_DIR/<NN>-<slug>.png
  SHOT_COUNTER=$((SHOT_COUNTER + 1))
  local slug="$1" path
  path=$(printf '%s/%02d-%s.png' "$SHOT_DIR" "$SHOT_COUNTER" "$slug")
  ab screenshot "$path"
  echo "$path"
}

shot_full() {
  SHOT_COUNTER=$((SHOT_COUNTER + 1))
  local slug="$1" path
  path=$(printf '%s/%02d-%s.png' "$SHOT_DIR" "$SHOT_COUNTER" "$slug")
  ab screenshot --full "$path"
  echo "$path"
}

capture_console() {
  local target="$1"
  ab console > "${target}.console.log" 2>&1 || true
  ab errors  > "${target}.errors.log"  2>&1 || true
}

# --- Click helpers (proven from e2e/_lib.sh) ---

click_text() {
  local needle="$1"
  agent-browser --session "$SESSION" eval \
    "Array.from(document.querySelectorAll('[role=option]')).find(e => e.textContent && e.textContent.trim().includes('$needle'))?.click()" \
    >/dev/null 2>&1 || true
}

click_any_text() {
  local needle="$1"
  agent-browser --session "$SESSION" eval \
    "Array.from(document.querySelectorAll('[role=option],[role=menuitem],button,a')).find(e => e.textContent && e.textContent.trim().includes('$needle'))?.click()" \
    >/dev/null 2>&1 || true
}

click_first_testid() {
  local prefix="$1"
  agent-browser --session "$SESSION" eval \
    "document.querySelector('[data-testid^=\"$prefix\"]')?.click()" >/dev/null 2>&1 || true
}

# --- Phase-level human checkpoint helpers ---

human_checkpoint() {
  # human_checkpoint <message>
  cat <<EOF >&2

═════════════════════════════════════════════════════════════════
🟡 HUMAN ACTION REQUIRED
═════════════════════════════════════════════════════════════════
$1
═════════════════════════════════════════════════════════════════
EOF
  if [[ -t 0 && -z "${E2E_NO_PROMPT:-}" ]]; then
    read -r -p "Press Enter when complete... " _
  else
    sleep 30  # Non-interactive: give a fixed window then continue.
  fi
}

# Sourced — do not exit on early-return from helpers.
return 0 2>/dev/null || true
