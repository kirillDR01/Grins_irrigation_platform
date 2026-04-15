#!/bin/bash
# E2E Test: Session Persistence Verification
# Validates: Requirement 2.7
#
# Logs in, waits for a configurable period, performs an action,
# and verifies the session remains active without redirect to /login.
# This confirms the token refresh logic keeps sessions alive during
# active use.
#
# Usage:
#   bash scripts/e2e/test-session-persistence.sh [--headed]
#
# Prerequisites:
#   - Frontend running at http://localhost:5173
#   - Backend running at http://localhost:8000
#   - agent-browser installed
#   - Valid admin credentials in environment or defaults

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCREENSHOT_DIR="e2e-screenshots/session-persistence"
BASE_URL="http://localhost:5173"
HEADED_FLAG=""

# Configurable wait time (ms) between login and action
WAIT_AFTER_LOGIN_MS="${E2E_SESSION_WAIT_MS:-5000}"

# Admin credentials (from env or defaults for dev)
ADMIN_EMAIL="${E2E_ADMIN_EMAIL:-admin}"
ADMIN_PASSWORD="${E2E_ADMIN_PASSWORD:-admin123}"

# Parse arguments
for arg in "$@"; do
  case $arg in
    --headed) HEADED_FLAG="--headed" ;;
  esac
done

mkdir -p "$SCREENSHOT_DIR"

echo "🧪 E2E Test: Session Persistence (Req 2.7)"
echo "============================================"

PASS_COUNT=0
FAIL_COUNT=0

# ---------------------------------------------------------------------------
# Step 1: Navigate to login page
# ---------------------------------------------------------------------------
echo ""
echo "Step 1: Navigating to login page..."
agent-browser $HEADED_FLAG open "${BASE_URL}/login"
agent-browser wait --load networkidle
agent-browser wait 1000
agent-browser screenshot "$SCREENSHOT_DIR/01-login-page.png"
echo "  ✓ Login page loaded"

# ---------------------------------------------------------------------------
# Step 2: Perform login
# ---------------------------------------------------------------------------
echo ""
echo "Step 2: Logging in as admin..."

# Use snapshot to find interactive elements
agent-browser snapshot -i > /dev/null 2>&1

# Fill email field — try data-testid first, fall back to input selectors
if agent-browser is visible "[data-testid='username-input']" 2>/dev/null; then
  agent-browser fill "[data-testid='username-input']" "$ADMIN_EMAIL"
elif agent-browser is visible "[name='email']" 2>/dev/null; then
  agent-browser fill "[name='email']" "$ADMIN_EMAIL"
elif agent-browser is visible "input[type='email']" 2>/dev/null; then
  agent-browser fill "input[type='email']" "$ADMIN_EMAIL"
else
  # Fall back to snapshot refs
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

agent-browser screenshot "$SCREENSHOT_DIR/02-credentials-filled.png"

# Click login button
if agent-browser is visible "[data-testid='login-btn']" 2>/dev/null; then
  agent-browser click "[data-testid='login-btn']"
elif agent-browser is visible "[data-testid='submit-btn']" 2>/dev/null; then
  agent-browser click "[data-testid='submit-btn']"
else
  agent-browser click "button[type='submit']"
fi

# Wait for navigation away from login
agent-browser wait --load networkidle
agent-browser wait 2000

CURRENT_URL=$(agent-browser get url 2>/dev/null || echo "")
agent-browser screenshot "$SCREENSHOT_DIR/03-after-login.png"

if echo "$CURRENT_URL" | grep -qi "/login"; then
  echo "  ✗ FAIL: Still on login page after login attempt"
  FAIL_COUNT=$((FAIL_COUNT + 1))
  echo ""
  echo "-------------------------------------------------------"
  echo "Session Persistence Results: $PASS_COUNT passed, $FAIL_COUNT failed"
  echo "-------------------------------------------------------"
  echo "❌ FAIL: Could not log in"
  exit 1
fi

echo "  ✓ Login successful — navigated to: $CURRENT_URL"
PASS_COUNT=$((PASS_COUNT + 1))

# ---------------------------------------------------------------------------
# Step 3: Wait for configurable period (simulating idle time)
# ---------------------------------------------------------------------------
echo ""
echo "Step 3: Waiting ${WAIT_AFTER_LOGIN_MS}ms to simulate session idle..."
agent-browser wait "$WAIT_AFTER_LOGIN_MS"
echo "  ✓ Wait complete"

# ---------------------------------------------------------------------------
# Step 4: Perform an action — navigate to /customers
# ---------------------------------------------------------------------------
echo ""
echo "Step 4: Performing action — navigating to /customers..."
agent-browser open "${BASE_URL}/customers"
agent-browser wait --load networkidle
agent-browser wait 2000
agent-browser screenshot "$SCREENSHOT_DIR/04-customers-after-wait.png"

CURRENT_URL=$(agent-browser get url 2>/dev/null || echo "")

if echo "$CURRENT_URL" | grep -qi "/login"; then
  echo "  ✗ FAIL: Redirected to login — session expired"
  FAIL_COUNT=$((FAIL_COUNT + 1))
else
  echo "  ✓ Session active — on /customers page (URL: $CURRENT_URL)"
  PASS_COUNT=$((PASS_COUNT + 1))
fi

# ---------------------------------------------------------------------------
# Step 5: Perform another action — navigate to /dashboard
# ---------------------------------------------------------------------------
echo ""
echo "Step 5: Performing second action — navigating to /dashboard..."
agent-browser open "${BASE_URL}/dashboard"
agent-browser wait --load networkidle
agent-browser wait 2000
agent-browser screenshot "$SCREENSHOT_DIR/05-dashboard-after-wait.png"

CURRENT_URL=$(agent-browser get url 2>/dev/null || echo "")

if echo "$CURRENT_URL" | grep -qi "/login"; then
  echo "  ✗ FAIL: Redirected to login — session expired on second action"
  FAIL_COUNT=$((FAIL_COUNT + 1))
else
  echo "  ✓ Session still active — on /dashboard page (URL: $CURRENT_URL)"
  PASS_COUNT=$((PASS_COUNT + 1))
fi

# ---------------------------------------------------------------------------
# Step 6: Verify page content loaded (not just a redirect-free URL)
# ---------------------------------------------------------------------------
echo ""
echo "Step 6: Verifying dashboard content loaded with active session..."

# Check that some dashboard content is visible (not an empty/error page)
PAGE_TEXT=$(agent-browser get text "body" 2>/dev/null || echo "")

if [ -n "$PAGE_TEXT" ] && [ ${#PAGE_TEXT} -gt 50 ]; then
  echo "  ✓ Dashboard content loaded (${#PAGE_TEXT} chars)"
  PASS_COUNT=$((PASS_COUNT + 1))
else
  echo "  ✗ FAIL: Dashboard content appears empty or minimal"
  FAIL_COUNT=$((FAIL_COUNT + 1))
fi

agent-browser screenshot "$SCREENSHOT_DIR/06-final-state.png"

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "-------------------------------------------------------"
echo "Session Persistence Results: $PASS_COUNT passed, $FAIL_COUNT failed"
echo "Screenshots saved to: $SCREENSHOT_DIR/"
echo "-------------------------------------------------------"

if [ "$FAIL_COUNT" -gt 0 ]; then
  echo "❌ FAIL: Session persistence issues detected"
  exit 1
fi

echo "✅ PASS: Session remains active throughout test"
exit 0
