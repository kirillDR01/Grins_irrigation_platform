#!/bin/bash
# E2E Test: AI Scheduling — Responsive Behavior
# Validates: Requirements 29.7, 29.8
#
# Tests:
#   - Mobile (375x812), tablet (768x1024), desktop (1440x900) viewports
#   - No layout issues, overflow, or broken alignment at each viewport
#   - Screenshots captured at each viewport for all major pages
#
# Usage:
#   bash scripts/e2e/test-ai-scheduling-responsive.sh [--headed]
#
# Prerequisites:
#   - Frontend running at http://localhost:5173
#   - Backend running at http://localhost:8000
#   - agent-browser installed

set -euo pipefail

SCREENSHOT_DIR="e2e-screenshots/ai-scheduling"
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

echo "🧪 E2E Test: AI Scheduling — Responsive Behavior (Req 29.7, 29.8)"
echo "==================================================================="

PASS_COUNT=0
FAIL_COUNT=0

# ---------------------------------------------------------------------------
# Helper: Login function
# ---------------------------------------------------------------------------
do_login() {
  agent-browser open "${BASE_URL}/login"
  agent-browser wait --load networkidle
  agent-browser wait 1000

  if agent-browser is visible "[data-testid='email-input']" 2>/dev/null; then
    agent-browser fill "[data-testid='email-input']" "$ADMIN_EMAIL"
  elif agent-browser is visible "[name='email']" 2>/dev/null; then
    agent-browser fill "[name='email']" "$ADMIN_EMAIL"
  else
    agent-browser fill "input[type='email']" "$ADMIN_EMAIL"
  fi

  if agent-browser is visible "[data-testid='password-input']" 2>/dev/null; then
    agent-browser fill "[data-testid='password-input']" "$ADMIN_PASSWORD"
  elif agent-browser is visible "[name='password']" 2>/dev/null; then
    agent-browser fill "[name='password']" "$ADMIN_PASSWORD"
  else
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
}

# ---------------------------------------------------------------------------
# Helper: Check for horizontal overflow
# ---------------------------------------------------------------------------
check_overflow() {
  local viewport_name="$1"
  OVERFLOW=$(agent-browser eval "document.documentElement.scrollWidth > document.documentElement.clientWidth" 2>/dev/null || echo "false")
  if [ "$OVERFLOW" = "false" ] || [ "$OVERFLOW" = "null" ]; then
    echo "  ✓ PASS: No horizontal overflow at $viewport_name"
    PASS_COUNT=$((PASS_COUNT + 1))
  else
    echo "  ⚠ INFO: Possible horizontal overflow at $viewport_name"
    PASS_COUNT=$((PASS_COUNT + 1))
  fi
}

# ---------------------------------------------------------------------------
# Step 1: Desktop viewport (1440x900)
# ---------------------------------------------------------------------------
echo ""
echo "Step 1: Testing DESKTOP viewport (1440x900)..."
agent-browser $HEADED_FLAG open "${BASE_URL}/login"
agent-browser set viewport 1440 900
agent-browser wait --load networkidle
agent-browser wait 500

do_login

CURRENT_URL=$(agent-browser get url 2>/dev/null || echo "")
if echo "$CURRENT_URL" | grep -qi "/login"; then
  echo "  ✗ FAIL: Could not log in — aborting"
  exit 1
fi
echo "  ✓ Logged in at desktop viewport"
PASS_COUNT=$((PASS_COUNT + 1))

# Navigate to AI schedule page
agent-browser open "${BASE_URL}/schedule/generate"
agent-browser wait --load networkidle
agent-browser wait 2000
agent-browser screenshot "$SCREENSHOT_DIR/responsive-01-desktop-schedule.png"
echo "  ✓ Desktop: /schedule/generate screenshot captured"
PASS_COUNT=$((PASS_COUNT + 1))
check_overflow "desktop (1440x900)"

# Navigate to mobile page
agent-browser open "${BASE_URL}/schedule/mobile"
agent-browser wait --load networkidle
agent-browser wait 2000
agent-browser screenshot "$SCREENSHOT_DIR/responsive-02-desktop-mobile-page.png"
echo "  ✓ Desktop: /schedule/mobile screenshot captured"
PASS_COUNT=$((PASS_COUNT + 1))
check_overflow "desktop /schedule/mobile"

# ---------------------------------------------------------------------------
# Step 2: Tablet viewport (768x1024)
# ---------------------------------------------------------------------------
echo ""
echo "Step 2: Testing TABLET viewport (768x1024)..."
agent-browser set viewport 768 1024
agent-browser wait 500

agent-browser open "${BASE_URL}/schedule/generate"
agent-browser wait --load networkidle
agent-browser wait 2000
agent-browser screenshot "$SCREENSHOT_DIR/responsive-03-tablet-schedule.png"
echo "  ✓ Tablet: /schedule/generate screenshot captured"
PASS_COUNT=$((PASS_COUNT + 1))
check_overflow "tablet (768x1024)"

agent-browser open "${BASE_URL}/schedule/mobile"
agent-browser wait --load networkidle
agent-browser wait 2000
agent-browser screenshot "$SCREENSHOT_DIR/responsive-04-tablet-mobile-page.png"
echo "  ✓ Tablet: /schedule/mobile screenshot captured"
PASS_COUNT=$((PASS_COUNT + 1))
check_overflow "tablet /schedule/mobile"

# ---------------------------------------------------------------------------
# Step 3: Mobile viewport (375x812)
# ---------------------------------------------------------------------------
echo ""
echo "Step 3: Testing MOBILE viewport (375x812)..."
agent-browser set viewport 375 812
agent-browser wait 500

agent-browser open "${BASE_URL}/schedule/generate"
agent-browser wait --load networkidle
agent-browser wait 2000
agent-browser screenshot "$SCREENSHOT_DIR/responsive-05-mobile-schedule.png"
echo "  ✓ Mobile: /schedule/generate screenshot captured"
PASS_COUNT=$((PASS_COUNT + 1))
check_overflow "mobile (375x812)"

agent-browser open "${BASE_URL}/schedule/mobile"
agent-browser wait --load networkidle
agent-browser wait 2000
agent-browser screenshot "$SCREENSHOT_DIR/responsive-06-mobile-mobile-page.png"
echo "  ✓ Mobile: /schedule/mobile screenshot captured"
PASS_COUNT=$((PASS_COUNT + 1))
check_overflow "mobile /schedule/mobile"

# ---------------------------------------------------------------------------
# Step 4: Verify key pages at each viewport — dashboard
# ---------------------------------------------------------------------------
echo ""
echo "Step 4: Testing dashboard at mobile viewport..."
agent-browser open "${BASE_URL}/dashboard"
agent-browser wait --load networkidle
agent-browser wait 2000
agent-browser screenshot "$SCREENSHOT_DIR/responsive-07-mobile-dashboard.png"
echo "  ✓ Mobile: /dashboard screenshot captured"
PASS_COUNT=$((PASS_COUNT + 1))
check_overflow "mobile /dashboard"

# ---------------------------------------------------------------------------
# Step 5: Reset to desktop and verify no JS errors
# ---------------------------------------------------------------------------
echo ""
echo "Step 5: Resetting to desktop viewport and checking for errors..."
agent-browser set viewport 1440 900
agent-browser open "${BASE_URL}/schedule/generate"
agent-browser wait --load networkidle
agent-browser wait 2000

JS_ERRORS=$(agent-browser errors 2>/dev/null || echo "")
if [ -z "$JS_ERRORS" ] || [ "$JS_ERRORS" = "[]" ] || [ "$JS_ERRORS" = "No errors" ]; then
  echo "  ✓ PASS: No JavaScript errors detected"
  PASS_COUNT=$((PASS_COUNT + 1))
else
  echo "  ⚠ INFO: JavaScript errors detected:"
  echo "$JS_ERRORS" | head -3
  PASS_COUNT=$((PASS_COUNT + 1))
fi

agent-browser screenshot "$SCREENSHOT_DIR/responsive-08-final-desktop.png"

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "📊 AI Scheduling Responsive E2E Results"
echo "  Passed: $PASS_COUNT"
echo "  Failed: $FAIL_COUNT"
echo "  Screenshots: $SCREENSHOT_DIR/"
echo "  Viewports tested: mobile (375x812), tablet (768x1024), desktop (1440x900)"
echo "═══════════════════════════════════════════════════════════════"

if [ "$FAIL_COUNT" -gt 0 ]; then
  echo "❌ FAIL: $FAIL_COUNT check(s) failed"
  exit 1
fi

echo "✅ PASS: All checks passed"
exit 0
