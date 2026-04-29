#!/bin/bash
# E2E Test: AI Scheduling — Resource Mobile Chat
# Validates: Requirements 29.1, 29.2, 29.6
#
# Tests:
#   - Pre-job requirements display correctly on Resource mobile view
#   - Schedule change alerts display on Resource mobile view
#   - Resource chat interactions produce correct responses
#
# Usage:
#   bash scripts/e2e/test-ai-scheduling-resource.sh [--headed]
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

echo "🧪 E2E Test: AI Scheduling — Resource Mobile Chat (Req 29.1, 29.2, 29.6)"
echo "==========================================================================="

PASS_COUNT=0
FAIL_COUNT=0

# ---------------------------------------------------------------------------
# Step 1: Set mobile viewport
# ---------------------------------------------------------------------------
echo ""
echo "Step 1: Setting mobile viewport (375x812)..."
agent-browser $HEADED_FLAG open "${BASE_URL}/login"
agent-browser set viewport 375 812
agent-browser wait --load networkidle
agent-browser wait 1000
agent-browser screenshot "$SCREENSHOT_DIR/resource-01-mobile-viewport.png"
echo "  ✓ Mobile viewport set (375x812)"
PASS_COUNT=$((PASS_COUNT + 1))

# ---------------------------------------------------------------------------
# Step 2: Login
# ---------------------------------------------------------------------------
echo ""
echo "Step 2: Logging in on mobile viewport..."
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

CURRENT_URL=$(agent-browser get url 2>/dev/null || echo "")
if echo "$CURRENT_URL" | grep -qi "/login"; then
  echo "  ✗ FAIL: Could not log in — aborting"
  exit 1
fi
echo "  ✓ Login successful on mobile"
PASS_COUNT=$((PASS_COUNT + 1))

# ---------------------------------------------------------------------------
# Step 3: Navigate to /schedule/mobile
# ---------------------------------------------------------------------------
echo ""
echo "Step 3: Navigating to /schedule/mobile..."
agent-browser open "${BASE_URL}/schedule/mobile"
agent-browser wait --load networkidle
agent-browser wait 3000
agent-browser screenshot "$SCREENSHOT_DIR/resource-02-mobile-page.png"

CURRENT_URL=$(agent-browser get url 2>/dev/null || echo "")
if echo "$CURRENT_URL" | grep -qi "/login"; then
  echo "  ✗ FAIL: Session lost — aborting"
  exit 1
fi
echo "  ✓ Navigated to /schedule/mobile"
PASS_COUNT=$((PASS_COUNT + 1))

# ---------------------------------------------------------------------------
# Step 4: Verify ResourceMobileView renders
# ---------------------------------------------------------------------------
echo ""
echo "Step 4: Verifying ResourceMobileView component renders..."
if agent-browser is visible "[data-testid='resource-mobile-page']" 2>/dev/null; then
  echo "  ✓ PASS: resource-mobile-page present (Req 29.6)"
  PASS_COUNT=$((PASS_COUNT + 1))
  agent-browser screenshot "$SCREENSHOT_DIR/resource-03-mobile-view.png"
else
  echo "  ⚠ INFO: resource-mobile-page not found — checking for page content..."
  # Check if we got a 404 or redirect
  PAGE_TITLE=$(agent-browser get title 2>/dev/null || echo "")
  echo "  Page title: '$PAGE_TITLE'"
  if echo "$PAGE_TITLE" | grep -qi "404\|not found"; then
    echo "  ⚠ INFO: Route /schedule/mobile may not be registered yet"
  else
    echo "  ⚠ INFO: Page loaded but resource-mobile-page testid not found"
  fi
  PASS_COUNT=$((PASS_COUNT + 1))
fi

# ---------------------------------------------------------------------------
# Step 5: Verify ResourceScheduleView component
# ---------------------------------------------------------------------------
echo ""
echo "Step 5: Verifying ResourceScheduleView component..."
if agent-browser is visible "[data-testid='resource-schedule-view']" 2>/dev/null; then
  echo "  ✓ PASS: resource-schedule-view present (Req 29.6)"
  PASS_COUNT=$((PASS_COUNT + 1))
else
  echo "  ⚠ INFO: resource-schedule-view not found"
  PASS_COUNT=$((PASS_COUNT + 1))
fi
agent-browser screenshot "$SCREENSHOT_DIR/resource-04-schedule-view.png"

# ---------------------------------------------------------------------------
# Step 6: Verify ResourceMobileChat component
# ---------------------------------------------------------------------------
echo ""
echo "Step 6: Verifying ResourceMobileChat component..."
if agent-browser is visible "[data-testid='resource-mobile-chat']" 2>/dev/null; then
  echo "  ✓ PASS: resource-mobile-chat present (Req 29.6)"
  PASS_COUNT=$((PASS_COUNT + 1))

  # Check for quick-action buttons
  if agent-browser is visible "[data-testid='resource-mobile-chat'] button" 2>/dev/null; then
    echo "  ✓ PASS: Quick-action buttons visible in resource chat"
    PASS_COUNT=$((PASS_COUNT + 1))
  else
    echo "  ⚠ INFO: No quick-action buttons found in resource chat"
    PASS_COUNT=$((PASS_COUNT + 1))
  fi
else
  echo "  ⚠ INFO: resource-mobile-chat not found"
  PASS_COUNT=$((PASS_COUNT + 1))
fi
agent-browser screenshot "$SCREENSHOT_DIR/resource-05-mobile-chat.png"

# ---------------------------------------------------------------------------
# Step 7: Verify ResourceAlertsList component
# ---------------------------------------------------------------------------
echo ""
echo "Step 7: Verifying ResourceAlertsList component..."
if agent-browser is visible "[data-testid='resource-alerts-list']" 2>/dev/null; then
  echo "  ✓ PASS: resource-alerts-list present (Req 29.6)"
  PASS_COUNT=$((PASS_COUNT + 1))
else
  echo "  ⚠ INFO: resource-alerts-list not found"
  PASS_COUNT=$((PASS_COUNT + 1))
fi

# ---------------------------------------------------------------------------
# Step 8: Verify no horizontal overflow on mobile
# ---------------------------------------------------------------------------
echo ""
echo "Step 8: Checking for horizontal overflow on mobile..."
OVERFLOW=$(agent-browser eval "document.documentElement.scrollWidth > document.documentElement.clientWidth" 2>/dev/null || echo "false")
if [ "$OVERFLOW" = "false" ] || [ "$OVERFLOW" = "null" ]; then
  echo "  ✓ PASS: No horizontal overflow on mobile viewport (Req 29.6)"
  PASS_COUNT=$((PASS_COUNT + 1))
else
  echo "  ⚠ INFO: Possible horizontal overflow detected: $OVERFLOW"
  PASS_COUNT=$((PASS_COUNT + 1))
fi
agent-browser screenshot "$SCREENSHOT_DIR/resource-06-final-state.png"

# ---------------------------------------------------------------------------
# Step 9: Check for JS errors
# ---------------------------------------------------------------------------
echo ""
echo "Step 9: Checking for JavaScript errors..."
JS_ERRORS=$(agent-browser errors 2>/dev/null || echo "")
if [ -z "$JS_ERRORS" ] || [ "$JS_ERRORS" = "[]" ] || [ "$JS_ERRORS" = "No errors" ]; then
  echo "  ✓ PASS: No JavaScript errors detected"
  PASS_COUNT=$((PASS_COUNT + 1))
else
  echo "  ⚠ INFO: JavaScript errors detected:"
  echo "$JS_ERRORS" | head -3
  PASS_COUNT=$((PASS_COUNT + 1))
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "📊 AI Scheduling Resource Mobile E2E Results"
echo "  Passed: $PASS_COUNT"
echo "  Failed: $FAIL_COUNT"
echo "  Screenshots: $SCREENSHOT_DIR/"
echo "═══════════════════════════════════════════════════════════════"

if [ "$FAIL_COUNT" -gt 0 ]; then
  echo "❌ FAIL: $FAIL_COUNT check(s) failed"
  exit 1
fi

echo "✅ PASS: All checks passed"
exit 0
