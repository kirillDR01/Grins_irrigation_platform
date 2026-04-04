#!/bin/bash
# E2E Test: AI Scheduling Page Routing
# Validates: Requirements 1.1, 1.2, 1.3, 1.4, 2.1, 3.1, 3.2, 3.3, 4.1, 6.1, 6.2
#
# Tests the AI Schedule admin page (/schedule/generate) and Resource Mobile page
# (/schedule/mobile) compositions, verifying component rendering, responsive
# layouts, and absence of console errors.
#
# Usage:
#   bash scripts/e2e/test-ai-scheduling-pages.sh [--headed]
#
# Prerequisites:
#   - Frontend running at http://localhost:5173
#   - agent-browser installed

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
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

echo "🧪 E2E Test: AI Scheduling Page Routing (Req 1-4, 6)"
echo "======================================================="

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

# Fill email field
if agent-browser is visible "[data-testid='email-input']" 2>/dev/null; then
  agent-browser fill "[data-testid='email-input']" "$ADMIN_EMAIL"
elif agent-browser is visible "[name='email']" 2>/dev/null; then
  agent-browser fill "[name='email']" "$ADMIN_EMAIL"
elif agent-browser is visible "input[type='email']" 2>/dev/null; then
  agent-browser fill "input[type='email']" "$ADMIN_EMAIL"
else
  agent-browser fill "input:first-of-type" "$ADMIN_EMAIL"
fi

# Fill password field
if agent-browser is visible "[data-testid='password-input']" 2>/dev/null; then
  agent-browser fill "[data-testid='password-input']" "$ADMIN_PASSWORD"
elif agent-browser is visible "[name='password']" 2>/dev/null; then
  agent-browser fill "[name='password']" "$ADMIN_PASSWORD"
elif agent-browser is visible "input[type='password']" 2>/dev/null; then
  agent-browser fill "input[type='password']" "$ADMIN_PASSWORD"
fi

# Click login button
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
agent-browser screenshot "$SCREENSHOT_DIR/01-after-login.png"

if echo "$CURRENT_URL" | grep -qi "/login"; then
  echo "  ✗ FAIL: Still on login page after login attempt"
  echo "❌ FAIL: Could not log in — aborting AI scheduling tests"
  agent-browser close 2>/dev/null || true
  exit 1
fi

echo "  ✓ Login successful"
PASS_COUNT=$((PASS_COUNT + 1))

# ---------------------------------------------------------------------------
# Step 2: Navigate to /schedule/generate — AI Schedule Admin Page (Req 1, 2, 6.1)
# ---------------------------------------------------------------------------
echo ""
echo "Step 2: Opening /schedule/generate (AI Schedule Admin Page)..."
agent-browser open "${BASE_URL}/schedule/generate"
agent-browser wait --load networkidle
agent-browser wait 2000

# Take snapshot to verify components render
agent-browser snapshot -i > /dev/null 2>&1 || true

# Check for data-testid="ai-schedule-page" visibility (Req 6.1)
if agent-browser is visible "[data-testid='ai-schedule-page']" 2>/dev/null; then
  echo "  ✓ AI Schedule page root element visible (data-testid='ai-schedule-page')"
  PASS_COUNT=$((PASS_COUNT + 1))
else
  echo "  ✗ FAIL: AI Schedule page root not found (data-testid='ai-schedule-page')"
  FAIL_COUNT=$((FAIL_COUNT + 1))
fi

# Verify main landmark with overview and alerts (Req 1.1, 1.2)
if agent-browser is visible "main" 2>/dev/null; then
  echo "  ✓ <main> landmark present"
  PASS_COUNT=$((PASS_COUNT + 1))
else
  echo "  ✗ FAIL: <main> landmark not found"
  FAIL_COUNT=$((FAIL_COUNT + 1))
fi

# Verify aside landmark with chat sidebar (Req 1.3)
if agent-browser is visible "aside" 2>/dev/null; then
  echo "  ✓ <aside> landmark present (chat sidebar)"
  PASS_COUNT=$((PASS_COUNT + 1))
else
  echo "  ✗ FAIL: <aside> landmark not found"
  FAIL_COUNT=$((FAIL_COUNT + 1))
fi

# Take desktop screenshot
agent-browser screenshot "$SCREENSHOT_DIR/ai-schedule-page-desktop.png"
echo "  📸 Screenshot: ai-schedule-page-desktop.png"

# ---------------------------------------------------------------------------
# Step 3: Navigate to /schedule/mobile — Resource Mobile Page (Req 3, 4, 6.2)
# ---------------------------------------------------------------------------
echo ""
echo "Step 3: Opening /schedule/mobile (Resource Mobile Page)..."
agent-browser open "${BASE_URL}/schedule/mobile"
agent-browser wait --load networkidle
agent-browser wait 2000

# Take snapshot to verify components render
agent-browser snapshot -i > /dev/null 2>&1 || true

# Check for data-testid="resource-mobile-page" visibility (Req 6.2)
if agent-browser is visible "[data-testid='resource-mobile-page']" 2>/dev/null; then
  echo "  ✓ Resource Mobile page root element visible (data-testid='resource-mobile-page')"
  PASS_COUNT=$((PASS_COUNT + 1))
else
  echo "  ✗ FAIL: Resource Mobile page root not found (data-testid='resource-mobile-page')"
  FAIL_COUNT=$((FAIL_COUNT + 1))
fi

# Take desktop screenshot
agent-browser screenshot "$SCREENSHOT_DIR/resource-mobile-page-desktop.png"
echo "  📸 Screenshot: resource-mobile-page-desktop.png"

# ---------------------------------------------------------------------------
# Step 4: Responsive viewport testing — Mobile (375x812)
# ---------------------------------------------------------------------------
echo ""
echo "Step 4: Testing responsive viewports — Mobile (375x812)..."
agent-browser set viewport 375 812

# Mobile: AI Schedule page
agent-browser open "${BASE_URL}/schedule/generate"
agent-browser wait --load networkidle
agent-browser wait 2000

if agent-browser is visible "[data-testid='ai-schedule-page']" 2>/dev/null; then
  echo "  ✓ AI Schedule page renders at mobile viewport"
  PASS_COUNT=$((PASS_COUNT + 1))
else
  echo "  ✗ FAIL: AI Schedule page not visible at mobile viewport"
  FAIL_COUNT=$((FAIL_COUNT + 1))
fi
agent-browser screenshot "$SCREENSHOT_DIR/ai-schedule-page-mobile-375x812.png"
echo "  📸 Screenshot: ai-schedule-page-mobile-375x812.png"

# Mobile: Resource Mobile page
agent-browser open "${BASE_URL}/schedule/mobile"
agent-browser wait --load networkidle
agent-browser wait 2000

if agent-browser is visible "[data-testid='resource-mobile-page']" 2>/dev/null; then
  echo "  ✓ Resource Mobile page renders at mobile viewport"
  PASS_COUNT=$((PASS_COUNT + 1))
else
  echo "  ✗ FAIL: Resource Mobile page not visible at mobile viewport"
  FAIL_COUNT=$((FAIL_COUNT + 1))
fi
agent-browser screenshot "$SCREENSHOT_DIR/resource-mobile-page-mobile-375x812.png"
echo "  📸 Screenshot: resource-mobile-page-mobile-375x812.png"

# ---------------------------------------------------------------------------
# Step 5: Responsive viewport testing — Tablet (768x1024)
# ---------------------------------------------------------------------------
echo ""
echo "Step 5: Testing responsive viewports — Tablet (768x1024)..."
agent-browser set viewport 768 1024

# Tablet: AI Schedule page
agent-browser open "${BASE_URL}/schedule/generate"
agent-browser wait --load networkidle
agent-browser wait 2000

if agent-browser is visible "[data-testid='ai-schedule-page']" 2>/dev/null; then
  echo "  ✓ AI Schedule page renders at tablet viewport"
  PASS_COUNT=$((PASS_COUNT + 1))
else
  echo "  ✗ FAIL: AI Schedule page not visible at tablet viewport"
  FAIL_COUNT=$((FAIL_COUNT + 1))
fi
agent-browser screenshot "$SCREENSHOT_DIR/ai-schedule-page-tablet-768x1024.png"
echo "  📸 Screenshot: ai-schedule-page-tablet-768x1024.png"

# Tablet: Resource Mobile page
agent-browser open "${BASE_URL}/schedule/mobile"
agent-browser wait --load networkidle
agent-browser wait 2000

if agent-browser is visible "[data-testid='resource-mobile-page']" 2>/dev/null; then
  echo "  ✓ Resource Mobile page renders at tablet viewport"
  PASS_COUNT=$((PASS_COUNT + 1))
else
  echo "  ✗ FAIL: Resource Mobile page not visible at tablet viewport"
  FAIL_COUNT=$((FAIL_COUNT + 1))
fi
agent-browser screenshot "$SCREENSHOT_DIR/resource-mobile-page-tablet-768x1024.png"
echo "  📸 Screenshot: resource-mobile-page-tablet-768x1024.png"

# ---------------------------------------------------------------------------
# Step 6: Responsive viewport testing — Desktop (1440x900)
# ---------------------------------------------------------------------------
echo ""
echo "Step 6: Testing responsive viewports — Desktop (1440x900)..."
agent-browser set viewport 1440 900

# Desktop: AI Schedule page
agent-browser open "${BASE_URL}/schedule/generate"
agent-browser wait --load networkidle
agent-browser wait 2000

if agent-browser is visible "[data-testid='ai-schedule-page']" 2>/dev/null; then
  echo "  ✓ AI Schedule page renders at desktop viewport"
  PASS_COUNT=$((PASS_COUNT + 1))
else
  echo "  ✗ FAIL: AI Schedule page not visible at desktop viewport"
  FAIL_COUNT=$((FAIL_COUNT + 1))
fi
agent-browser screenshot "$SCREENSHOT_DIR/ai-schedule-page-desktop-1440x900.png"
echo "  📸 Screenshot: ai-schedule-page-desktop-1440x900.png"

# Desktop: Resource Mobile page
agent-browser open "${BASE_URL}/schedule/mobile"
agent-browser wait --load networkidle
agent-browser wait 2000

if agent-browser is visible "[data-testid='resource-mobile-page']" 2>/dev/null; then
  echo "  ✓ Resource Mobile page renders at desktop viewport"
  PASS_COUNT=$((PASS_COUNT + 1))
else
  echo "  ✗ FAIL: Resource Mobile page not visible at desktop viewport"
  FAIL_COUNT=$((FAIL_COUNT + 1))
fi
agent-browser screenshot "$SCREENSHOT_DIR/resource-mobile-page-desktop-1440x900.png"
echo "  📸 Screenshot: resource-mobile-page-desktop-1440x900.png"

# ---------------------------------------------------------------------------
# Step 7: Check for console errors on both pages
# ---------------------------------------------------------------------------
echo ""
echo "Step 7: Checking for console errors..."

# Check AI Schedule page
agent-browser open "${BASE_URL}/schedule/generate"
agent-browser wait --load networkidle
agent-browser wait 2000

CONSOLE_OUTPUT=$(agent-browser console 2>/dev/null || echo "")
ERROR_OUTPUT=$(agent-browser errors 2>/dev/null || echo "")

if [ -z "$ERROR_OUTPUT" ] || echo "$ERROR_OUTPUT" | grep -qi "no errors"; then
  echo "  ✓ No uncaught errors on /schedule/generate"
  PASS_COUNT=$((PASS_COUNT + 1))
else
  echo "  ⚠ Errors detected on /schedule/generate:"
  echo "    ${ERROR_OUTPUT:0:200}"
  FAIL_COUNT=$((FAIL_COUNT + 1))
fi

# Check Resource Mobile page
agent-browser open "${BASE_URL}/schedule/mobile"
agent-browser wait --load networkidle
agent-browser wait 2000

CONSOLE_OUTPUT=$(agent-browser console 2>/dev/null || echo "")
ERROR_OUTPUT=$(agent-browser errors 2>/dev/null || echo "")

if [ -z "$ERROR_OUTPUT" ] || echo "$ERROR_OUTPUT" | grep -qi "no errors"; then
  echo "  ✓ No uncaught errors on /schedule/mobile"
  PASS_COUNT=$((PASS_COUNT + 1))
else
  echo "  ⚠ Errors detected on /schedule/mobile:"
  echo "    ${ERROR_OUTPUT:0:200}"
  FAIL_COUNT=$((FAIL_COUNT + 1))
fi

# ---------------------------------------------------------------------------
# Step 8: Close browser and report results
# ---------------------------------------------------------------------------
echo ""
echo "Step 8: Closing browser..."
agent-browser close 2>/dev/null || true

TOTAL=$((PASS_COUNT + FAIL_COUNT))
echo ""
echo "======================================================="
echo "🧪 AI Scheduling Page Routing E2E Results"
echo "======================================================="
echo "  ✓ Passed: $PASS_COUNT"
echo "  ✗ Failed: $FAIL_COUNT"
echo "  Total:   $TOTAL"
echo ""
echo "📸 Screenshots saved to: $SCREENSHOT_DIR/"
echo ""

if [ "$FAIL_COUNT" -gt 0 ]; then
  echo "❌ SOME TESTS FAILED"
  exit 1
else
  echo "✅ ALL TESTS PASSED"
  exit 0
fi
