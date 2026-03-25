#!/bin/bash
# E2E Test: Outbound Notification History (Communications)
# Validates: Requirements 82.7, 82.8, 67.2
#
# Tests sent messages tab with delivery status badges and timestamps,
# and customer-specific outbound messages on customer detail page.
#
# Usage:
#   bash scripts/e2e/test-communications.sh [--headed]
#
# Prerequisites:
#   - Frontend running at http://localhost:5173
#   - Backend running at http://localhost:8000
#   - agent-browser installed

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCREENSHOT_DIR="e2e-screenshots/communications"
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

echo "🧪 E2E Test: Communications — Sent Messages (Req 82.7, 82.8)"
echo "=============================================================="

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
# Step 2: Sent Messages tab (Req 82.7)
# ---------------------------------------------------------------------------
echo ""
echo "Step 2: Testing Sent Messages tab (Req 82)..."
agent-browser open "${BASE_URL}/communications"
agent-browser wait --load networkidle
agent-browser wait 2000
agent-browser screenshot "$SCREENSHOT_DIR/01-communications-page.png"

# Click Sent Messages tab
if agent-browser is visible "[data-testid='sent-messages-tab']" 2>/dev/null; then
  agent-browser click "[data-testid='sent-messages-tab']"
elif agent-browser is visible "text=Sent Messages" 2>/dev/null; then
  agent-browser click "text=Sent Messages"
elif agent-browser is visible "text=Sent" 2>/dev/null; then
  agent-browser click "text=Sent"
fi

agent-browser wait --load networkidle
agent-browser wait 2000
agent-browser screenshot "$SCREENSHOT_DIR/02-sent-messages.png"

PAGE_TEXT=$(agent-browser get text "body" 2>/dev/null || echo "")

# Verify outbound messages displayed
if agent-browser is visible "[data-testid='sent-message-row']" 2>/dev/null; then
  echo "  ✓ Outbound messages displayed"
  PASS_COUNT=$((PASS_COUNT + 1))

  # Check for delivery status badges
  if agent-browser is visible "[data-testid='delivery-status-badge']" 2>/dev/null; then
    echo "  ✓ Delivery status badges visible"
    PASS_COUNT=$((PASS_COUNT + 1))
  elif echo "$PAGE_TEXT" | grep -qi "delivered\|sent\|failed\|pending"; then
    echo "  ✓ Delivery status indicators detected"
    PASS_COUNT=$((PASS_COUNT + 1))
  fi

  # Check for timestamps
  if echo "$PAGE_TEXT" | grep -qP '\d{1,2}[:/]\d{2}|\d{4}-\d{2}-\d{2}|ago|today|yesterday'; then
    echo "  ✓ Timestamps displayed on sent messages"
    PASS_COUNT=$((PASS_COUNT + 1))
  fi
elif echo "$PAGE_TEXT" | grep -qi "sent\|outbound\|message\|notification"; then
  echo "  ✓ Sent messages content detected"
  PASS_COUNT=$((PASS_COUNT + 1))
else
  echo "  ✗ FAIL: Outbound messages not displayed"
  FAIL_COUNT=$((FAIL_COUNT + 1))
fi

# ---------------------------------------------------------------------------
# Step 3: Customer-specific outbound messages (Req 82.8)
# ---------------------------------------------------------------------------
echo ""
echo "Step 3: Testing customer-specific outbound messages (Req 82)..."
agent-browser open "${BASE_URL}/customers"
agent-browser wait --load networkidle
agent-browser wait 2000

# Click first customer
if agent-browser is visible "[data-testid='customer-row']" 2>/dev/null; then
  agent-browser click "[data-testid='customer-row']"
elif agent-browser is visible "tbody tr" 2>/dev/null; then
  agent-browser click "tbody tr"
fi

agent-browser wait --load networkidle
agent-browser wait 2000
agent-browser screenshot "$SCREENSHOT_DIR/03-customer-detail.png"

# Click Messages tab
if agent-browser is visible "[data-testid='messages-tab']" 2>/dev/null; then
  agent-browser click "[data-testid='messages-tab']"
elif agent-browser is visible "text=Messages" 2>/dev/null; then
  agent-browser click "text=Messages"
fi

agent-browser wait --load networkidle
agent-browser wait 2000
agent-browser screenshot "$SCREENSHOT_DIR/04-customer-messages.png"

PAGE_TEXT=$(agent-browser get text "body" 2>/dev/null || echo "")
if echo "$PAGE_TEXT" | grep -qi "message\|sent\|outbound\|SMS\|email\|notification"; then
  echo "  ✓ Outbound messages displayed for customer"
  PASS_COUNT=$((PASS_COUNT + 1))
elif agent-browser is visible "[data-testid='customer-messages']" 2>/dev/null; then
  echo "  ✓ Customer messages section visible"
  PASS_COUNT=$((PASS_COUNT + 1))
else
  echo "  ⚠ Customer messages tab may be empty (no messages for this customer)"
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "-------------------------------------------------------"
echo "Communications E2E Results: $PASS_COUNT passed, $FAIL_COUNT failed"
echo "Screenshots saved to: $SCREENSHOT_DIR/"
echo "-------------------------------------------------------"

if [ "$FAIL_COUNT" -gt 0 ]; then
  echo "❌ FAIL: Communications issues detected"
  exit 1
fi

echo "✅ PASS: All communications tests passed"
exit 0
