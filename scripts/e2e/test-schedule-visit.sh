#!/bin/bash
# E2E Test: Schedule Estimate Visit Modal
# Validates: feature-developments/schedule-estimate-visit-handoff/CHECKLIST.md
#
# Usage: bash scripts/e2e/test-schedule-visit.sh [--headed]
# Prereqs: backend at :8000, frontend at :5173, agent-browser installed.

set -euo pipefail
SCREENSHOT_DIR="e2e-screenshots/schedule-visit"
BASE_URL="http://localhost:5173"
HEADED_FLAG=""
ADMIN_EMAIL="${E2E_ADMIN_EMAIL:-admin@grins.com}"
ADMIN_PASSWORD="${E2E_ADMIN_PASSWORD:-admin123}"
for arg in "$@"; do case $arg in --headed) HEADED_FLAG="--headed" ;; esac; done
mkdir -p "$SCREENSHOT_DIR"

echo "🧪 E2E Test: Schedule Estimate Visit Modal"
echo "==========================================="

# ── Login (mirrored from scripts/e2e/test-sales.sh) ──
agent-browser $HEADED_FLAG open "${BASE_URL}/login"
agent-browser wait --load networkidle
agent-browser wait 1000

if   agent-browser is visible "[data-testid='email-input']" 2>/dev/null; then agent-browser fill "[data-testid='email-input']" "$ADMIN_EMAIL"
elif agent-browser is visible "[name='email']" 2>/dev/null; then agent-browser fill "[name='email']" "$ADMIN_EMAIL"
else agent-browser fill "input[type='email']" "$ADMIN_EMAIL"
fi
if   agent-browser is visible "[data-testid='password-input']" 2>/dev/null; then agent-browser fill "[data-testid='password-input']" "$ADMIN_PASSWORD"
else agent-browser fill "input[type='password']" "$ADMIN_PASSWORD"
fi
if   agent-browser is visible "[data-testid='login-btn']" 2>/dev/null; then agent-browser click "[data-testid='login-btn']"
else agent-browser click "button[type='submit']"
fi
agent-browser wait --load networkidle
agent-browser wait 2000
CURRENT_URL=$(agent-browser get url 2>/dev/null || echo "")
if echo "$CURRENT_URL" | grep -qi "/login"; then echo "✗ FAIL: Could not log in"; exit 1; fi
echo "✓ Login successful"

# ── Navigate to a sales entry ──
agent-browser open "${BASE_URL}/sales"
agent-browser wait --load networkidle
agent-browser screenshot "$SCREENSHOT_DIR/01-pipeline.png"

if agent-browser is visible "[data-testid='pipeline-row-0']" 2>/dev/null; then
  agent-browser click "[data-testid='pipeline-row-0']"
else
  agent-browser click "a[href*='/sales/']"
fi
agent-browser wait --load networkidle
agent-browser screenshot "$SCREENSHOT_DIR/02-detail.png"

# ── Open modal ──
agent-browser click "[data-testid='now-action-schedule']"
agent-browser wait "[data-testid='schedule-visit-modal']"
agent-browser screenshot "$SCREENSHOT_DIR/03-modal-open.png"

if agent-browser is visible "[data-testid='schedule-visit-customer-card']"; then echo "✓ customer card visible"; else echo "✗ customer card MISSING"; exit 1; fi
if agent-browser is visible "[data-testid='schedule-visit-calendar']"; then echo "✓ calendar visible"; else echo "✗ calendar MISSING"; exit 1; fi

CONFIRM_DISABLED=$(agent-browser get attr "[data-testid='schedule-visit-confirm-btn']" "disabled" 2>/dev/null || echo "")
if [ -n "$CONFIRM_DISABLED" ]; then echo "✓ Confirm disabled before pick"; fi

# ── Click a slot (Mon 2pm = day 0, slot 16) ──
agent-browser click "[data-testid='schedule-visit-slot-0-16']"
agent-browser wait "[data-testid='schedule-visit-pick']"
agent-browser screenshot "$SCREENSHOT_DIR/04-pick.png"

# ── Confirm ──
agent-browser click "[data-testid='schedule-visit-confirm-btn']"
agent-browser wait --text "Visit scheduled"
agent-browser screenshot "$SCREENSHOT_DIR/05-after-confirm.png"

# ── Verify the entry advanced (visible signal: visit_scheduled activity badge) ──
if agent-browser is visible "[data-testid='activity-event-visit_scheduled']" 2>/dev/null; then
  echo "✓ Activity strip shows 'visit_scheduled' badge — entry advanced"
else
  echo "✗ FAIL: 'visit_scheduled' activity badge missing"
  exit 1
fi

agent-browser close
echo ""
echo "✓ E2E complete. Screenshots: $SCREENSHOT_DIR/"
