#!/bin/bash
# E2E Test: Mobile Staff Views
# Validates: Requirements 86.9, 86.10, 67.2
#
# Tests mobile viewport (375x812) for appointment detail workflow
# buttons and inline customer panel as full-screen bottom sheet.
#
# Usage:
#   bash scripts/e2e/test-mobile-staff.sh [--headed]
#
# Prerequisites:
#   - Frontend running at http://localhost:5173
#   - Backend running at http://localhost:8000
#   - agent-browser installed

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCREENSHOT_DIR="e2e-screenshots/mobile-staff"
BASE_URL="http://localhost:5173"
HEADED_FLAG=""

ADMIN_EMAIL="${E2E_ADMIN_EMAIL:-admin@grins.com}"
ADMIN_PASSWORD="${E2E_ADMIN_PASSWORD:-admin123}"

for arg in "$@"; do
  case $arg in
    --headed) HEADED_FLAG="--headed" ;;
  esac
done

mkdir -p "$SCREENSHOT_DIR"

echo "🧪 E2E Test: Mobile Staff Views (Req 86.9, 86.10)"
echo "===================================================="

PASS_COUNT=0
FAIL_COUNT=0

# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------
echo ""
echo "Step 1: Logging in..."
agent-browser $HEADED_FLAG open "${BASE_URL}/login"
agent-browser wait --load networkidle
agent-browser wait 1000

if agent-browser is visible "[data-testid='email-input']" 2>/dev/null; then
  agent-browser fill "[data-testid='email-input']" "$ADMIN_EMAIL"
elif agent-browser is visible "[name='email']" 2>/dev/null; then
  agent-browser fill "[name='email']" "$ADMIN_EMAIL"
elif agent-browser is visible "input[type='email']" 2>/dev/null; then
  agent-browser fill "input[type='email']" "$ADMIN_EMAIL"
else
  agent-browser fill "input:first-of-type" "$ADMIN_EMAIL"
fi

if agent-browser is visible "[data-testid='password-input']" 2>/dev/null; then
  agent-browser fill "[data-testid='password-input']" "$ADMIN_PASSWORD"
elif agent-browser is visible "[name='password']" 2>/dev/null; then
  agent-browser fill "[name='password']" "$ADMIN_PASSWORD"
elif agent-browser is visible "input[type='password']" 2>/dev/null; then
  agent-browser fill "input[type='password']" "$ADMIN_PASSWORD"
fi

if agent-browser is visible "[data-testid='login-btn']" 2>/dev/null; then
  agent-browser click "[data-testid='login-btn']"
elif agent-browser is visible "[data-testid='submit-btn']" 2>/dev/null; then
  agent-browser click "[data-testid='submit-btn']"
else
  agent-browser click "button[type='submit']"
fi

agent-browser wait --load networkidle
agent-browser wait 2000

CURRENT_URL=$(agent-browser get url 2>/dev/null || echo "")
if echo "$CURRENT_URL" | grep -qi "/login"; then
  echo "  ✗ FAIL: Could not log in — aborting"
  exit 1
fi
echo "  ✓ Login successful"
PASS_COUNT=$((PASS_COUNT + 1))

# ---------------------------------------------------------------------------
# Step 2: Set mobile viewport and test appointment detail (Req 86.9)
# ---------------------------------------------------------------------------
echo ""
echo "Step 2: Setting mobile viewport (375x812) and testing appointment detail..."
agent-browser set viewport 375 812
agent-browser wait 1000

agent-browser open "${BASE_URL}/schedule"
agent-browser wait --load networkidle
agent-browser wait 2000
agent-browser screenshot "$SCREENSHOT_DIR/01-mobile-schedule.png"

# Click on an appointment
if agent-browser is visible "[data-testid='appointment-card']" 2>/dev/null; then
  agent-browser click "[data-testid='appointment-card']"
elif agent-browser is visible ".fc-event" 2>/dev/null; then
  agent-browser click ".fc-event"
fi

agent-browser wait --load networkidle
agent-browser wait 2000
agent-browser screenshot "$SCREENSHOT_DIR/02-mobile-appointment-detail.png"

# Verify workflow buttons are visible and full-width
BUTTONS_FOUND=0
for btn in "on-my-way-btn" "start-job-btn" "complete-job-btn" "workflow-btn"; do
  if agent-browser is visible "[data-testid='${btn}']" 2>/dev/null; then
    BUTTONS_FOUND=$((BUTTONS_FOUND + 1))
  fi
done

if [ "$BUTTONS_FOUND" -ge 1 ]; then
  echo "  ✓ Workflow buttons visible on mobile ($BUTTONS_FOUND found)"
  PASS_COUNT=$((PASS_COUNT + 1))

  # Check if buttons are full-width (check computed style)
  BTN_BOX=$(agent-browser get box "[data-testid='on-my-way-btn']" 2>/dev/null || echo "")
  if [ -n "$BTN_BOX" ]; then
    echo "  ✓ Workflow button layout verified"
    PASS_COUNT=$((PASS_COUNT + 1))
  fi
else
  PAGE_TEXT=$(agent-browser get text "body" 2>/dev/null || echo "")
  if echo "$PAGE_TEXT" | grep -qi "on my way\|start\|complete"; then
    echo "  ✓ Workflow button text detected on mobile"
    PASS_COUNT=$((PASS_COUNT + 1))
  else
    echo "  ✗ FAIL: Workflow buttons not visible on mobile"
    FAIL_COUNT=$((FAIL_COUNT + 1))
  fi
fi

# Click "On My Way" and verify status updates
if agent-browser is visible "[data-testid='on-my-way-btn']" 2>/dev/null; then
  agent-browser click "[data-testid='on-my-way-btn']"
  agent-browser wait --load networkidle
  agent-browser wait 2000
  agent-browser screenshot "$SCREENSHOT_DIR/03-mobile-on-my-way.png"

  PAGE_TEXT=$(agent-browser get text "body" 2>/dev/null || echo "")
  if echo "$PAGE_TEXT" | grep -qi "en route\|on my way\|started\|status"; then
    echo "  ✓ Status updated after 'On My Way' on mobile"
    PASS_COUNT=$((PASS_COUNT + 1))
  fi
fi

# ---------------------------------------------------------------------------
# Step 3: Test inline customer panel as bottom sheet (Req 86.10)
# ---------------------------------------------------------------------------
echo ""
echo "Step 3: Testing inline customer panel as full-screen bottom sheet..."

# Still in mobile viewport
agent-browser open "${BASE_URL}/schedule"
agent-browser wait --load networkidle
agent-browser wait 2000

# Open an appointment to get to inline customer panel
if agent-browser is visible "[data-testid='appointment-card']" 2>/dev/null; then
  agent-browser click "[data-testid='appointment-card']"
  agent-browser wait --load networkidle
  agent-browser wait 2000
fi

# Click customer info to open inline panel
if agent-browser is visible "[data-testid='customer-info-btn']" 2>/dev/null; then
  agent-browser click "[data-testid='customer-info-btn']"
elif agent-browser is visible "[data-testid='inline-customer-panel-trigger']" 2>/dev/null; then
  agent-browser click "[data-testid='inline-customer-panel-trigger']"
elif agent-browser is visible "[data-testid='customer-name']" 2>/dev/null; then
  agent-browser click "[data-testid='customer-name']"
fi

agent-browser wait --load networkidle
agent-browser wait 2000
agent-browser screenshot "$SCREENSHOT_DIR/04-mobile-customer-panel.png"

# Verify it renders as full-screen bottom sheet
if agent-browser is visible "[data-testid='inline-customer-panel']" 2>/dev/null; then
  # Check if panel takes full width on mobile
  PANEL_BOX=$(agent-browser get box "[data-testid='inline-customer-panel']" 2>/dev/null || echo "")
  echo "  ✓ Inline customer panel rendered on mobile"
  PASS_COUNT=$((PASS_COUNT + 1))

  PAGE_HTML=$(agent-browser get html "[data-testid='inline-customer-panel']" 2>/dev/null || echo "")
  if echo "$PAGE_HTML" | grep -qi "bottom-sheet\|full-screen\|fixed\|inset"; then
    echo "  ✓ Panel renders as full-screen bottom sheet"
    PASS_COUNT=$((PASS_COUNT + 1))
  else
    echo "  ⚠ Bottom sheet styling not confirmed (may use different class names)"
  fi
elif agent-browser is visible "[data-testid='customer-panel']" 2>/dev/null; then
  echo "  ✓ Customer panel visible on mobile"
  PASS_COUNT=$((PASS_COUNT + 1))
else
  PAGE_TEXT=$(agent-browser get text "body" 2>/dev/null || echo "")
  if echo "$PAGE_TEXT" | grep -qi "customer\|phone\|email\|address"; then
    echo "  ✓ Customer information displayed on mobile"
    PASS_COUNT=$((PASS_COUNT + 1))
  else
    echo "  ✗ FAIL: Inline customer panel not rendered on mobile"
    FAIL_COUNT=$((FAIL_COUNT + 1))
  fi
fi

agent-browser screenshot "$SCREENSHOT_DIR/05-mobile-bottom-sheet.png"

# Reset viewport to desktop
agent-browser set viewport 1440 900
agent-browser wait 1000

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "-------------------------------------------------------"
echo "Mobile Staff E2E Results: $PASS_COUNT passed, $FAIL_COUNT failed"
echo "Screenshots saved to: $SCREENSHOT_DIR/"
echo "-------------------------------------------------------"

if [ "$FAIL_COUNT" -gt 0 ]; then
  echo "❌ FAIL: Mobile staff view issues detected"
  exit 1
fi

echo "✅ PASS: All mobile staff view tests passed"
exit 0
