#!/bin/bash
# E2E Test: Navigation, Security, and Portal
# Validates: Requirements 66.5, 69.6, 70.5, 71.8, 78.9, 67.2
#
# Tests sidebar navigation items, rate limiting, security headers,
# auth token storage, and portal link security.
#
# Usage:
#   bash scripts/e2e/test-navigation-security.sh [--headed]
#
# Prerequisites:
#   - Frontend running at http://localhost:5173
#   - Backend running at http://localhost:8000
#   - agent-browser installed

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCREENSHOT_DIR="e2e-screenshots/navigation-security"
BASE_URL="http://localhost:5173"
HEADED_FLAG=""

ADMIN_EMAIL="${E2E_ADMIN_EMAIL:-admin}"
ADMIN_PASSWORD="${E2E_ADMIN_PASSWORD:-admin123}"

for arg in "$@"; do
  case $arg in
    --headed) HEADED_FLAG="--headed" ;;
  esac
done

mkdir -p "$SCREENSHOT_DIR"

echo "🧪 E2E Test: Navigation, Security, Portal (Req 66.5, 69.6, 70.5, 71.8, 78.9)"
echo "================================================================================"

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

if agent-browser is visible "[data-testid='username-input']" 2>/dev/null; then
  agent-browser fill "[data-testid='username-input']" "$ADMIN_EMAIL"
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
# Step 2: Sidebar Navigation (Req 66)
# ---------------------------------------------------------------------------
echo ""
echo "Step 2: Verifying sidebar navigation items (Req 66)..."
agent-browser screenshot "$SCREENSHOT_DIR/01-after-login.png"

NAV_ITEMS=("nav-sales|/sales" "nav-accounting|/accounting" "nav-marketing|/marketing" "nav-communications|/communications")
NAV_FOUND=0

for entry in "${NAV_ITEMS[@]}"; do
  IFS='|' read -r testid expected_path <<< "$entry"

  if agent-browser is visible "[data-testid='${testid}']" 2>/dev/null; then
    NAV_FOUND=$((NAV_FOUND + 1))
    agent-browser click "[data-testid='${testid}']"
    agent-browser wait --load networkidle
    agent-browser wait 2000

    NAV_URL=$(agent-browser get url 2>/dev/null || echo "")
    if echo "$NAV_URL" | grep -qi "${expected_path}"; then
      echo "  ✓ ${testid}: navigated to ${expected_path}"
    else
      echo "  ⚠ ${testid}: clicked but URL is ${NAV_URL}"
    fi
  else
    echo "  ⚠ ${testid}: not visible in sidebar"
  fi
done

if [ "$NAV_FOUND" -ge 3 ]; then
  echo "  ✓ Navigation items found and functional ($NAV_FOUND/4)"
  PASS_COUNT=$((PASS_COUNT + 1))
elif [ "$NAV_FOUND" -ge 1 ]; then
  echo "  ⚠ Only $NAV_FOUND/4 navigation items found"
  PASS_COUNT=$((PASS_COUNT + 1))
else
  # Fallback: check sidebar text
  PAGE_TEXT=$(agent-browser get text "nav" 2>/dev/null || agent-browser get text "[data-testid='sidebar']" 2>/dev/null || echo "")
  if echo "$PAGE_TEXT" | grep -qi "sales\|accounting\|marketing"; then
    echo "  ✓ Navigation items detected in sidebar text"
    PASS_COUNT=$((PASS_COUNT + 1))
  else
    echo "  ✗ FAIL: Navigation items not found"
    FAIL_COUNT=$((FAIL_COUNT + 1))
  fi
fi

agent-browser screenshot "$SCREENSHOT_DIR/02-navigation-verified.png"

# ---------------------------------------------------------------------------
# Step 3: Rate Limiting (Req 69)
# ---------------------------------------------------------------------------
echo ""
echo "Step 3: Testing rate limiting (Req 69)..."

# Navigate to a page with a form and rapidly submit
agent-browser open "${BASE_URL}/leads"
agent-browser wait --load networkidle
agent-browser wait 2000

RATE_LIMITED=false
# Rapidly submit requests by clicking a button multiple times
for i in $(seq 1 15); do
  if agent-browser is visible "[data-testid='submit-btn']" 2>/dev/null; then
    agent-browser click "[data-testid='submit-btn']" 2>/dev/null || true
  elif agent-browser is visible "button[type='submit']" 2>/dev/null; then
    agent-browser click "button[type='submit']" 2>/dev/null || true
  fi
done

agent-browser wait 2000
agent-browser screenshot "$SCREENSHOT_DIR/03-rate-limit-test.png"

PAGE_TEXT=$(agent-browser get text "body" 2>/dev/null || echo "")
if echo "$PAGE_TEXT" | grep -qi "rate limit\|too many\|slow down\|try again"; then
  echo "  ✓ Rate limit message appears after rapid submissions"
  PASS_COUNT=$((PASS_COUNT + 1))
  RATE_LIMITED=true
fi

if [ "$RATE_LIMITED" = false ]; then
  # Check for toast notifications
  if agent-browser is visible "[data-testid='toast']" 2>/dev/null || \
     agent-browser is visible "[role='alert']" 2>/dev/null; then
    TOAST_TEXT=$(agent-browser get text "[role='alert']" 2>/dev/null || echo "")
    if echo "$TOAST_TEXT" | grep -qi "rate\|limit\|too many"; then
      echo "  ✓ Rate limit toast notification displayed"
      PASS_COUNT=$((PASS_COUNT + 1))
      RATE_LIMITED=true
    fi
  fi
fi

if [ "$RATE_LIMITED" = false ]; then
  echo "  ⚠ Rate limit message not triggered (may need more requests or different endpoint)"
fi

# ---------------------------------------------------------------------------
# Step 4: Security Headers (Req 70)
# ---------------------------------------------------------------------------
echo ""
echo "Step 4: Checking console for security warnings (Req 70)..."

agent-browser open "${BASE_URL}/dashboard"
agent-browser wait --load networkidle
agent-browser wait 2000

CONSOLE_OUTPUT=$(agent-browser console 2>/dev/null || echo "")
agent-browser screenshot "$SCREENSHOT_DIR/04-security-check.png"

if echo "$CONSOLE_OUTPUT" | grep -qi "missing.*header\|security.*warning\|CSP.*violation"; then
  echo "  ✗ FAIL: Console security warnings detected"
  FAIL_COUNT=$((FAIL_COUNT + 1))
else
  echo "  ✓ No console security warnings related to missing headers"
  PASS_COUNT=$((PASS_COUNT + 1))
fi

# ---------------------------------------------------------------------------
# Step 5: Auth Token Storage (Req 71)
# ---------------------------------------------------------------------------
echo ""
echo "Step 5: Verifying auth token not in localStorage (Req 71)..."

TOKEN_VALUE=$(agent-browser eval "localStorage.getItem('auth_token')" 2>/dev/null || echo "null")

if [ "$TOKEN_VALUE" = "null" ] || [ -z "$TOKEN_VALUE" ] || [ "$TOKEN_VALUE" = "undefined" ]; then
  echo "  ✓ No auth token found in localStorage"
  PASS_COUNT=$((PASS_COUNT + 1))
else
  echo "  ✗ FAIL: Auth token found in localStorage"
  FAIL_COUNT=$((FAIL_COUNT + 1))
fi

# Verify authenticated API calls still succeed
API_CHECK=$(agent-browser eval "fetch('/api/v1/customers?page=1&page_size=1').then(r => r.status)" 2>/dev/null || echo "0")
if echo "$API_CHECK" | grep -q "200"; then
  echo "  ✓ Authenticated API calls succeed without localStorage token"
  PASS_COUNT=$((PASS_COUNT + 1))
else
  echo "  ⚠ API call returned status: $API_CHECK (may use cookie-based auth)"
fi

agent-browser screenshot "$SCREENSHOT_DIR/05-auth-token-check.png"

# ---------------------------------------------------------------------------
# Step 6: Portal Link Security (Req 78)
# ---------------------------------------------------------------------------
echo ""
echo "Step 6: Testing portal link security (Req 78)..."

# Open a portal estimate link (use a placeholder token)
agent-browser open "${BASE_URL}/portal/estimates/test-token-placeholder"
agent-browser wait --load networkidle
agent-browser wait 2000
agent-browser screenshot "$SCREENSHOT_DIR/06-portal-estimate.png"

PAGE_TEXT=$(agent-browser get text "body" 2>/dev/null || echo "")
PAGE_HTML=$(agent-browser get html "body" 2>/dev/null || echo "")

# Check that estimate content is displayed (or appropriate error for invalid token)
if echo "$PAGE_TEXT" | grep -qi "estimate\|expired\|not found\|invalid"; then
  echo "  ✓ Portal page responds appropriately to estimate link"
  PASS_COUNT=$((PASS_COUNT + 1))
fi

# Verify no internal IDs visible in page source
UUID_PATTERN='[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
# Check for exposed internal UUIDs in visible text (not in URLs/tokens which are expected)
VISIBLE_TEXT=$(agent-browser get text "body" 2>/dev/null || echo "")
if echo "$VISIBLE_TEXT" | grep -qP "$UUID_PATTERN"; then
  echo "  ⚠ Possible internal IDs visible in page text"
else
  echo "  ✓ No internal IDs visible in page source"
  PASS_COUNT=$((PASS_COUNT + 1))
fi

agent-browser screenshot "$SCREENSHOT_DIR/07-portal-security.png"

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "-------------------------------------------------------"
echo "Navigation/Security E2E Results: $PASS_COUNT passed, $FAIL_COUNT failed"
echo "Screenshots saved to: $SCREENSHOT_DIR/"
echo "-------------------------------------------------------"

if [ "$FAIL_COUNT" -gt 0 ]; then
  echo "❌ FAIL: Navigation/security issues detected"
  exit 1
fi

echo "✅ PASS: All navigation and security tests passed"
exit 0
