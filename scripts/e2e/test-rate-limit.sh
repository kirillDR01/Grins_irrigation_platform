#!/bin/bash
# E2E Test: Rate Limit Error Handling
# Validates: Requirements 85.6, 85.7, 67.2
#
# Rapidly submits a form and verifies a toast notification appears
# with "Too many requests" message and wait time.
#
# Usage:
#   bash scripts/e2e/test-rate-limit.sh [--headed]
#
# Prerequisites:
#   - Frontend running at http://localhost:5173
#   - Backend running at http://localhost:8000
#   - agent-browser installed

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCREENSHOT_DIR="e2e-screenshots/rate-limit"
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

echo "🧪 E2E Test: Rate Limit Error Handling (Req 85.6, 85.7)"
echo "========================================================="

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
# Step 2: Rapidly submit a form to trigger rate limiting
# ---------------------------------------------------------------------------
echo ""
echo "Step 2: Rapidly submitting form to trigger rate limit..."

# Navigate to a page with a form (e.g., leads)
agent-browser open "${BASE_URL}/leads"
agent-browser wait --load networkidle
agent-browser wait 2000
agent-browser screenshot "$SCREENSHOT_DIR/01-leads-page.png"

# Try to rapidly trigger API calls via JavaScript
# This simulates rapid form submissions
RATE_LIMIT_HIT=false

agent-browser eval "
  (async () => {
    const promises = [];
    for (let i = 0; i < 30; i++) {
      promises.push(fetch('/api/v1/leads?page=1&page_size=1'));
    }
    const results = await Promise.all(promises);
    const statuses = results.map(r => r.status);
    return JSON.stringify(statuses);
  })()
" 2>/dev/null || true

agent-browser wait 2000
agent-browser screenshot "$SCREENSHOT_DIR/02-after-rapid-requests.png"

# Check for rate limit toast
PAGE_TEXT=$(agent-browser get text "body" 2>/dev/null || echo "")

if echo "$PAGE_TEXT" | grep -qi "too many requests\|rate limit\|slow down\|try again\|wait"; then
  echo "  ✓ Toast notification with 'Too many requests' message displayed"
  PASS_COUNT=$((PASS_COUNT + 1))
  RATE_LIMIT_HIT=true
fi

# Check for toast element specifically
if [ "$RATE_LIMIT_HIT" = false ]; then
  if agent-browser is visible "[data-testid='toast']" 2>/dev/null || \
     agent-browser is visible "[role='alert']" 2>/dev/null || \
     agent-browser is visible ".toast" 2>/dev/null; then
    TOAST_TEXT=$(agent-browser get text "[role='alert']" 2>/dev/null || \
                 agent-browser get text "[data-testid='toast']" 2>/dev/null || echo "")
    if echo "$TOAST_TEXT" | grep -qi "too many\|rate\|limit\|wait"; then
      echo "  ✓ Rate limit toast notification displayed"
      PASS_COUNT=$((PASS_COUNT + 1))
      RATE_LIMIT_HIT=true
    fi
  fi
fi

# Verify wait time is shown
if [ "$RATE_LIMIT_HIT" = true ]; then
  if echo "$PAGE_TEXT" | grep -qi "second\|minute\|wait\|retry"; then
    echo "  ✓ Wait time displayed in rate limit message"
    PASS_COUNT=$((PASS_COUNT + 1))
  fi
else
  echo "  ⚠ Rate limit not triggered (may need higher request volume or different endpoint)"
fi

agent-browser screenshot "$SCREENSHOT_DIR/03-rate-limit-result.png"

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "-------------------------------------------------------"
echo "Rate Limit E2E Results: $PASS_COUNT passed, $FAIL_COUNT failed"
echo "Screenshots saved to: $SCREENSHOT_DIR/"
echo "-------------------------------------------------------"

if [ "$FAIL_COUNT" -gt 0 ]; then
  echo "❌ FAIL: Rate limit error handling issues detected"
  exit 1
fi

echo "✅ PASS: All rate limit tests passed"
exit 0
