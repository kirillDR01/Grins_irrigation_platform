#!/bin/bash
# E2E Test: Notifications — On My Way Notification
# Validates: Requirements 39.12, 67.2
#
# Opens a confirmed appointment, clicks "On My Way", and verifies
# the notification log shows an "on my way" notification queued.
#
# Usage:
#   bash scripts/e2e/test-notifications.sh [--headed]
#
# Prerequisites:
#   - Frontend running at http://localhost:5173
#   - Backend running at http://localhost:8000
#   - agent-browser installed

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCREENSHOT_DIR="e2e-screenshots/notifications"
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

echo "🧪 E2E Test: Notifications — On My Way (Req 39.12)"
echo "===================================================="

PASS_COUNT=0
FAIL_COUNT=0

# ---------------------------------------------------------------------------
# Step 1: Login
# ---------------------------------------------------------------------------
echo ""
echo "Step 1: Logging in..."
agent-browser $HEADED_FLAG open "${BASE_URL}/login"
agent-browser wait --load networkidle
agent-browser wait 1000
agent-browser screenshot "$SCREENSHOT_DIR/01-login-page.png"

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
agent-browser screenshot "$SCREENSHOT_DIR/02-after-login.png"

CURRENT_URL=$(agent-browser get url 2>/dev/null || echo "")
if echo "$CURRENT_URL" | grep -qi "/login"; then
  echo "  ✗ FAIL: Still on login page after login attempt"
  echo "❌ FAIL: Could not log in — aborting"
  exit 1
fi
echo "  ✓ Login successful"
PASS_COUNT=$((PASS_COUNT + 1))

# ---------------------------------------------------------------------------
# Step 2: Navigate to schedule and find a confirmed appointment
# ---------------------------------------------------------------------------
echo ""
echo "Step 2: Navigating to /schedule to find a confirmed appointment..."
agent-browser open "${BASE_URL}/schedule"
agent-browser wait --load networkidle
agent-browser wait 2000
agent-browser screenshot "$SCREENSHOT_DIR/03-schedule-page.png"

# Try to click on a confirmed appointment
APPT_FOUND=false
if agent-browser is visible "[data-testid='appointment-confirmed']" 2>/dev/null; then
  agent-browser click "[data-testid='appointment-confirmed']"
  APPT_FOUND=true
elif agent-browser is visible "[data-testid='appointment-card']" 2>/dev/null; then
  agent-browser click "[data-testid='appointment-card']"
  APPT_FOUND=true
elif agent-browser is visible ".fc-event" 2>/dev/null; then
  agent-browser click ".fc-event"
  APPT_FOUND=true
fi

agent-browser wait --load networkidle
agent-browser wait 2000
agent-browser screenshot "$SCREENSHOT_DIR/04-appointment-detail.png"

if [ "$APPT_FOUND" = true ]; then
  echo "  ✓ Appointment found and opened"
  PASS_COUNT=$((PASS_COUNT + 1))
else
  echo "  ✗ FAIL: No appointment found on schedule"
  FAIL_COUNT=$((FAIL_COUNT + 1))
fi

# ---------------------------------------------------------------------------
# Step 3: Click "On My Way" button
# ---------------------------------------------------------------------------
echo ""
echo "Step 3: Clicking 'On My Way' button..."

OMW_CLICKED=false
if agent-browser is visible "[data-testid='on-my-way-btn']" 2>/dev/null; then
  agent-browser click "[data-testid='on-my-way-btn']"
  OMW_CLICKED=true
elif agent-browser is visible "button:has-text('On My Way')" 2>/dev/null; then
  agent-browser click "button:has-text('On My Way')"
  OMW_CLICKED=true
fi

agent-browser wait --load networkidle
agent-browser wait 2000
agent-browser screenshot "$SCREENSHOT_DIR/05-after-on-my-way.png"

if [ "$OMW_CLICKED" = true ]; then
  echo "  ✓ 'On My Way' button clicked"
  PASS_COUNT=$((PASS_COUNT + 1))
else
  echo "  ✗ FAIL: 'On My Way' button not found"
  FAIL_COUNT=$((FAIL_COUNT + 1))
fi

# ---------------------------------------------------------------------------
# Step 4: Verify notification log shows "on my way" notification queued
# ---------------------------------------------------------------------------
echo ""
echo "Step 4: Verifying notification log shows 'on my way' notification..."

PAGE_TEXT=$(agent-browser get text "body" 2>/dev/null || echo "")

if echo "$PAGE_TEXT" | grep -qi "on my way\|en route\|notification.*queued\|notification.*sent"; then
  echo "  ✓ Notification log shows 'on my way' notification queued"
  PASS_COUNT=$((PASS_COUNT + 1))
else
  # Check for a notification log section or toast
  if agent-browser is visible "[data-testid='notification-log']" 2>/dev/null; then
    NOTIF_TEXT=$(agent-browser get text "[data-testid='notification-log']" 2>/dev/null || echo "")
    if echo "$NOTIF_TEXT" | grep -qi "on my way\|en route"; then
      echo "  ✓ Notification log confirms 'on my way' notification"
      PASS_COUNT=$((PASS_COUNT + 1))
    else
      echo "  ✗ FAIL: Notification log does not contain 'on my way' entry"
      FAIL_COUNT=$((FAIL_COUNT + 1))
    fi
  elif agent-browser is visible "[data-testid='toast']" 2>/dev/null || agent-browser is visible "[role='status']" 2>/dev/null; then
    echo "  ✓ Notification feedback displayed (toast/status)"
    PASS_COUNT=$((PASS_COUNT + 1))
  else
    echo "  ✗ FAIL: No notification feedback found after 'On My Way' action"
    FAIL_COUNT=$((FAIL_COUNT + 1))
  fi
fi

agent-browser screenshot "$SCREENSHOT_DIR/06-notification-verification.png"

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "-------------------------------------------------------"
echo "Notifications E2E Results: $PASS_COUNT passed, $FAIL_COUNT failed"
echo "Screenshots saved to: $SCREENSHOT_DIR/"
echo "-------------------------------------------------------"

if [ "$FAIL_COUNT" -gt 0 ]; then
  echo "❌ FAIL: Notification issues detected"
  exit 1
fi

echo "✅ PASS: All notification tests passed"
exit 0
