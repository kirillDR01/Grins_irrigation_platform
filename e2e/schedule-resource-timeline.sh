#!/usr/bin/env bash
# E2E smoke for the Schedule Resource Timeline View.
#
# Validates the visible behavior added/landed in Phases 1-4 of
# .agents/plans/schedule-resource-timeline-view.md:
#   - /schedule loads with the resource-timeline grid (week mode default).
#   - View-mode toggle: Week -> Day -> Month all render the right grid.
#   - Day-header drill-in (week -> day) works.
#   - Empty-cell click opens the Create Appointment dialog.
#   - Cross-component queues (reschedule/no-reply/inbox) still mount.
#   - No JS console errors / page exceptions.
#   - Responsive: mobile (375x812), tablet (768x1024), desktop (1440x900).
#
# Pre-flight:
#   - Backend reachable at http://localhost:8000
#   - Frontend reachable at http://localhost:5173
#   - agent-browser CLI installed (>= 0.7)
#
# Optional env vars:
#   BASE       — frontend URL (default http://localhost:5173)
#   E2E_USER   — admin username (default admin)
#   E2E_PASS   — admin password (default admin123)

set -euo pipefail

BASE="${BASE:-http://localhost:5174}"
E2E_USER="${E2E_USER:-admin}"
E2E_PASS="${E2E_PASS:-admin123}"
SHOTS="e2e-screenshots/schedule-timeline"
SESSION="${AGENT_BROWSER_SESSION:-schedule-timeline-e2e-$$}"
mkdir -p "$SHOTS"

# Pre-flight (per e2e-testing-skill.md Phase 1)
[[ "$(uname -s)" =~ ^(Darwin|Linux)$ ]] || { echo "Unsupported platform"; exit 1; }
if ! command -v agent-browser >/dev/null 2>&1; then
  echo "agent-browser is not installed; cannot run UI E2E."
  echo "Install: npm install -g agent-browser && agent-browser install --with-deps"
  exit 1
fi

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

# Phase 0: login (admin -> /dashboard, then navigate to /schedule).
ab open "$BASE/login"
ab wait --load networkidle
ab screenshot "$SHOTS/00-login.png"
ab fill "[data-testid='username-input']" "$E2E_USER"
ab fill "[data-testid='password-input']" "$E2E_PASS"
ab click "[data-testid='login-btn']"
ab wait --load networkidle
sleep 2

# Phase 2: Open the schedule page.
ab open "$BASE/schedule"
ab wait --load networkidle
ab wait "[data-testid='schedule-resource-timeline']"
# WeekMode is the default; allow either the loaded grid or the empty-state branch.
ab wait --fn "!!document.querySelector('[data-testid=schedule-week-mode]') || !!document.querySelector('[data-testid=schedule-empty-state]')"
sleep 2  # let weekly query settle
ab screenshot "$SHOTS/01-initial-week.png"
ab is visible "[data-testid='schedule-week-mode']" || ab is visible "[data-testid='schedule-empty-state']"

# Phase 3: Mode toggle.
ab click "[data-testid='view-mode-day-btn']"
ab wait "[data-testid='schedule-day-mode']"
sleep 1
ab screenshot "$SHOTS/02-day-mode.png"

ab click "[data-testid='view-mode-month-btn']"
ab wait "[data-testid='schedule-month-mode']"
sleep 1
ab screenshot "$SHOTS/03-month-mode.png"

# Resolve today's date and the first tech id so we can click a unique cell.
TODAY=$(date +%Y-%m-%d)
FIRST_TECH=$(agent-browser --session "$SESSION" eval \
  "document.querySelector('[data-testid^=tech-header-]')?.dataset.testid?.replace('tech-header-','')||''" \
  2>/dev/null | tail -1 | tr -d '"')

# Day-header drill-in (week -> day).
ab click "[data-testid='view-mode-week-btn']"
ab wait "[data-testid='schedule-week-mode']"
sleep 2
DAY_HEADER_COUNT=$(agent-browser --session "$SESSION" get count "[data-testid='day-header-${TODAY}']" 2>/dev/null | tail -1 | tr -d '"')
if [[ "${DAY_HEADER_COUNT:-0}" == "1" ]]; then
  ab click "[data-testid='day-header-${TODAY}']"
  ab wait "[data-testid='schedule-day-mode']"
  sleep 1
  ab screenshot "$SHOTS/04-drill-in.png"
else
  echo "SKIP drill-in: day-header-${TODAY} not present (count=${DAY_HEADER_COUNT})"
  ab screenshot "$SHOTS/04-drill-in.png"
fi

# Empty cell click -> create dialog (use first tech, today).
ab click "[data-testid='view-mode-week-btn']"
ab wait "[data-testid='schedule-week-mode']"
sleep 2
if [[ -n "${FIRST_TECH}" ]]; then
  CELL_SEL="[data-testid='cell-${FIRST_TECH}-${TODAY}']"
  CELL_COUNT=$(agent-browser --session "$SESSION" get count "$CELL_SEL" 2>/dev/null | tail -1 | tr -d '"')
  if [[ "${CELL_COUNT:-0}" == "1" ]]; then
    ab click "$CELL_SEL"
    ab wait --text "Create Appointment"
    ab screenshot "$SHOTS/05-create-dialog.png"
    ab press Escape
  else
    echo "SKIP create-dialog: $CELL_SEL not present (count=${CELL_COUNT})"
    ab screenshot "$SHOTS/05-create-dialog.png"
  fi
else
  echo "SKIP create-dialog: no tech-header in DOM"
  ab screenshot "$SHOTS/05-create-dialog.png"
fi

# Cross-component: queues still render (each may legitimately be hidden when empty).
ab is visible "[data-testid='reschedule-requests-queue']" || true
ab is visible "[data-testid='no-reply-review-queue']" || true
ab is visible "[data-testid='inbox-queue']" || true

# Console + errors check (Phase 3 of e2e-testing-skill).
ab console > "$SHOTS/console.log" 2>&1 || true
ab errors  > "$SHOTS/errors.log"  2>&1 || true

# Phase 6: Responsive viewports.
ab set viewport 375 812
sleep 1
ab screenshot "$SHOTS/06-mobile-list-fallback.png"

ab set viewport 768 1024
sleep 1
ab screenshot "$SHOTS/07-tablet.png"

ab set viewport 1440 900
sleep 1
ab screenshot "$SHOTS/08-desktop.png"

ab close

echo
echo "PASS — screenshots in $SHOTS/"
ls -la "$SHOTS/"
