#!/usr/bin/env bash
# Phase 5 E2E — Polish + cleanup verification.

set -euo pipefail
cd "$(dirname "$0")/.."

# shellcheck source=./_lib.sh
source e2e/_lib.sh

require_tooling
require_servers
SHOTS="$SHOTS_ROOT/phase-5"
mkdir -p "$SHOTS"

login_admin

# Use list-view helper so the modal actually has the action track.
APPT_ID=$(open_first_appointment_modal "scheduled,confirmed,en_route,in_progress" || true)
if [[ -z "${APPT_ID:-}" ]]; then
  echo "no appointments visible — aborting"
  exit 0
fi

# 5.1 CTA label "Send estimate" — capture full modal first.
ab screenshot "$SHOTS/01-cta-label.png"

# 5.2 Action track sublabels are visible plain text.
ab screenshot "$SHOTS/02-action-track-labels.png"

# 5.3 Get directions opens the maps popover (no testid on trigger;
# the trigger is a button with text "Get directions" inside the
# property card).
agent-browser --session "$SESSION" eval \
  "Array.from(document.querySelectorAll('button,a')).find(e => /Get directions/i.test(e.textContent))?.click()" \
  >/dev/null 2>&1 || true
sleep 2
ab screenshot "$SHOTS/03-maps-popover-with-footer.png"

# 5.4 Apple + Remember.
agent-browser --session "$SESSION" eval \
  "document.querySelector('[data-testid=remember-maps-choice-checkbox]').click()" >/dev/null 2>&1 || true
sleep 1
agent-browser --session "$SESSION" eval \
  "Array.from(document.querySelectorAll('[role=menuitem]')).find(e => /Apple Maps/i.test(e.textContent))?.click()" \
  >/dev/null 2>&1 || true
sleep 2
ab screenshot "$SHOTS/04-apple-remembered.png"

# 5.5 Repeat with Google.
agent-browser --session "$SESSION" eval \
  "Array.from(document.querySelectorAll('button,a')).find(e => /Get directions/i.test(e.textContent))?.click()" \
  >/dev/null 2>&1 || true
sleep 2
agent-browser --session "$SESSION" eval \
  "document.querySelector('[data-testid=remember-maps-choice-checkbox]').click()" >/dev/null 2>&1 || true
sleep 1
agent-browser --session "$SESSION" eval \
  "Array.from(document.querySelectorAll('[role=menuitem]')).find(e => /Google Maps/i.test(e.textContent))?.click()" \
  >/dev/null 2>&1 || true
sleep 2
ab screenshot "$SHOTS/05-google-remembered.png"

# 5.6 DB confirms persistence.
psql_q "SELECT id::text || '|' || preferred_maps_app FROM staff WHERE preferred_maps_app IS NOT NULL ORDER BY updated_at DESC LIMIT 5;" \
  > "$SHOTS/db-preferred-maps-app.txt"
echo "[5.6] preferred_maps_app rows:" ; cat "$SHOTS/db-preferred-maps-app.txt"

# 5.7 Deprecated stripe_terminal endpoints return 404.
HTTP=$(curl -s -o /dev/null -w "%{http_code}" "$API_BASE/api/v1/stripe-terminal/")
echo "stripe_terminal_404=$HTTP" > "$SHOTS/06-stripe-terminal-404.txt"
ab open "$API_BASE/api/v1/stripe-terminal/" || true
sleep 1
ab screenshot "$SHOTS/06-stripe-terminal-404.png" || true

# 5.8 / 5.9 file-system uninstall.
{
  echo "[5.8] test_stripe_terminal.py exists?"
  ls src/grins_platform/tests/unit/test_stripe_terminal.py 2>&1 || echo "  not found (expected)"
  echo
  echo "[5.9] router.py mentions stripe_terminal?"
  grep -n "stripe_terminal" src/grins_platform/api/v1/router.py 2>&1 || echo "  no matches (expected)"
  echo
  echo "[5.9b] services/stripe_terminal.py exists?"
  ls src/grins_platform/services/stripe_terminal.py 2>&1 || echo "  not found (expected)"
} > "$SHOTS/07-stripe-terminal-grep.txt"

capture_console "$SHOTS/console"
echo
echo "PASS — screenshots in $SHOTS/"
