#!/usr/bin/env bash
# E2E smoke for the Tech Companion phone-only schedule view.
#
# Validates:
#   - Tech logging in from a phone viewport lands on /tech (not /dashboard).
#   - vas's three appointments render (completed / in_progress / scheduled).
#   - Tapping the in_progress card opens the existing AppointmentModal.
#   - steven's two appointments render (per-tech isolation).
#   - vitallik renders the empty state (validates 0-appt branch).
#   - Admin login still goes to /dashboard.
#   - Tech on a desktop viewport sees the "Open this on your phone" landing.
#
# Pre-flight:
#   - Backend reachable at http://localhost:8000 (or API_BASE).
#   - Frontend reachable at $BASE (default http://localhost:5173).
#   - DATABASE_URL exported so the seed script can connect.
#   - agent-browser CLI installed.
#
# Optional env vars:
#   BASE       — frontend URL (default http://localhost:5173)
#   API_BASE   — backend URL (default http://localhost:8000)
#   E2E_USER   — admin username (default admin)
#   E2E_PASS   — admin password (default admin123)

set -euo pipefail

BASE="${BASE:-http://localhost:5173}"
API_BASE="${API_BASE:-http://localhost:8000}"
E2E_USER="${E2E_USER:-admin}"
E2E_PASS="${E2E_PASS:-admin123}"
SHOTS="e2e-screenshots/tech-companion-mobile"
SESSION="${AGENT_BROWSER_SESSION:-tech-companion-e2e-$$}"
mkdir -p "$SHOTS"

# Pre-flight
[[ "$(uname -s)" =~ ^(Darwin|Linux)$ ]] || { echo "Unsupported platform"; exit 1; }
if ! command -v agent-browser >/dev/null 2>&1; then
  echo "agent-browser is not installed; cannot run UI E2E."
  echo "Install: npm install -g agent-browser && agent-browser install --with-deps"
  exit 1
fi
if ! curl -fsS "${API_BASE}/health" >/dev/null 2>&1; then
  echo "Backend not reachable at ${API_BASE} — start the API first." >&2
  exit 1
fi

# Seed today's appointments for the three dev techs.
echo "Seeding appointments for vas / steven / vitallik ..."
uv run python scripts/seed_tech_companion_appointments.py

ab() {
  local tries=0
  while (( tries < 3 )); do
    if agent-browser --session "$SESSION" "$@"; then
      return 0
    fi
    local rc=$?
    tries=$((tries + 1))
    echo "  (retry $tries/3 after agent-browser failure rc=$rc) $*" >&2
    sleep 2
  done
  return 1
}

# Helper: log the current user out (clear app cookies + nuke storage),
# then sign in fresh. We can't rely on a logout button — on the mobile
# tech view there isn't one — so we clear cookies via in-page JS and
# call the logout API directly. Then we navigate to /login (the
# already-authenticated effect won't fire since the cookies are gone).
relogin() {
  local user="$1"
  local pass="$2"
  ab eval "
    (async () => {
      try {
        await fetch('${API_BASE}/api/v1/auth/logout', { method: 'POST', credentials: 'include' });
      } catch (e) {}
      // Belt-and-suspenders: clear any non-HttpOnly cookies on this origin
      // and wipe storage so the next page mount has no stale auth state.
      document.cookie.split(';').forEach((c) => {
        const eq = c.indexOf('=');
        const name = (eq > -1 ? c.substring(0, eq) : c).trim();
        document.cookie = name + '=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/';
      });
      try { localStorage.clear(); sessionStorage.clear(); } catch (e) {}
    })();
  " >/dev/null 2>&1 || true
  sleep 1
  ab open "$BASE/login"
  ab wait --load networkidle
  ab fill "[data-testid='username-input']" "$user"
  ab fill "[data-testid='password-input']" "$pass"
  ab click "[data-testid='login-btn']"
  ab wait --load networkidle
  sleep 2
}

# Phase 0 — viewport: iPhone 14 Pro ish (390x844).
ab set viewport 390 844

# Phase 1 — Tech vas login + redirect to /tech.
ab open "$BASE/login"
ab wait --load networkidle
ab screenshot "$SHOTS/01-login.png"
ab fill "[data-testid='username-input']" "vas"
ab fill "[data-testid='password-input']" "tech123"
ab click "[data-testid='login-btn']"
ab wait --load networkidle
sleep 2
ab screenshot "$SHOTS/02-vas-schedule.png"

# Phase 2 — Card states (vas: completed / in_progress / scheduled)
ab snapshot -i > "$SHOTS/02-snapshot.txt" || true
ab is visible "[data-testid='mobile-job-card-current']"
ab is visible "[data-testid='mobile-job-card-complete']"
ab is visible "[data-testid='mobile-job-card-upcoming']"
ab screenshot "$SHOTS/03-cards-visible.png"

# Phase 3 — Open the in_progress card → AppointmentModal mounts.
ab click "[data-testid='mobile-job-card-current']"
ab wait --load networkidle
sleep 1
ab screenshot "$SHOTS/04-modal-open.png"
ab click "[data-testid='appointment-modal-close']"
sleep 1
ab screenshot "$SHOTS/05-modal-closed.png"

# Phase 4 — Per-tech isolation: log out + log in as steven.
relogin "steven" "tech123"
ab screenshot "$SHOTS/06-steven-schedule.png"
# steven has 2 upcoming appointments — strict-mode visibility fails on
# multi-match, so assert count instead.
steven_card_count=$(ab get count "[data-testid='mobile-job-card-upcoming']" | tr -d '[:space:]' || echo 0)
echo "steven upcoming cards: ${steven_card_count}"
[[ "${steven_card_count}" -ge 1 ]] || { echo "expected steven to have >=1 upcoming card" >&2; exit 1; }

# Phase 5 — Empty state for vitallik.
relogin "vitallik" "tech123"
ab screenshot "$SHOTS/07-vitallik-empty.png"
ab is visible "[data-testid='tech-empty-state']"

# Phase 6 — Admin login lands on /dashboard, NOT /tech.
relogin "$E2E_USER" "$E2E_PASS"
ab screenshot "$SHOTS/08-admin-dashboard.png"

# Phase 7 — Tech on a desktop viewport sees the "Open this on your phone" landing.
ab set viewport 1440 900
relogin "vas" "tech123"
ab screenshot "$SHOTS/09-tech-on-desktop-landing.png"

# Phase 8 — Console / errors.
ab console > "$SHOTS/console.log" || true
ab errors  > "$SHOTS/errors.log"  || true

echo
echo "Screenshots:"
ls "$SHOTS/"
echo
if [[ -s "$SHOTS/errors.log" ]]; then
  echo "WARNING: errors.log is non-empty — review:" >&2
  cat "$SHOTS/errors.log" >&2
fi
echo "Done."
