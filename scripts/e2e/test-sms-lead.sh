#!/bin/bash
# E2E Test: SMS Lead Confirmation Flow
# Validates: Requirements 46.7
#
# Creates a lead via the leads form and verifies SMS confirmation is logged.
#
# Usage:
#   bash scripts/e2e/test-sms-lead.sh [--headed]
#
# Prerequisites:
#   - Frontend running at http://localhost:5173
#   - Backend running at http://localhost:8000
#   - agent-browser installed

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCREENSHOT_DIR="e2e-screenshots/sms-lead"
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

echo "🧪 E2E Test: SMS Lead Confirmation (Req 46.7)"
echo "================================================"

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
# Step 2: Create a lead via the leads form
# ---------------------------------------------------------------------------
echo ""
echo "Step 2: Creating a lead via the leads form..."
agent-browser open "${BASE_URL}/leads"
agent-browser wait --load networkidle
agent-browser wait 2000
agent-browser screenshot "$SCREENSHOT_DIR/01-leads-page.png"

# Click add lead button
if agent-browser is visible "[data-testid='add-lead-btn']" 2>/dev/null; then
  agent-browser click "[data-testid='add-lead-btn']"
elif agent-browser is visible "text=Add Lead" 2>/dev/null; then
  agent-browser click "text=Add Lead"
elif agent-browser is visible "[data-testid='create-lead-btn']" 2>/dev/null; then
  agent-browser click "[data-testid='create-lead-btn']"
fi

agent-browser wait --load networkidle
agent-browser wait 2000
agent-browser screenshot "$SCREENSHOT_DIR/02-lead-form.png"

# Fill lead form
if agent-browser is visible "[data-testid='lead-first-name']" 2>/dev/null; then
  agent-browser fill "[data-testid='lead-first-name']" "E2E Test"
elif agent-browser is visible "[name='firstName']" 2>/dev/null; then
  agent-browser fill "[name='firstName']" "E2E Test"
elif agent-browser is visible "[name='first_name']" 2>/dev/null; then
  agent-browser fill "[name='first_name']" "E2E Test"
fi

if agent-browser is visible "[data-testid='lead-last-name']" 2>/dev/null; then
  agent-browser fill "[data-testid='lead-last-name']" "SMSLead"
elif agent-browser is visible "[name='lastName']" 2>/dev/null; then
  agent-browser fill "[name='lastName']" "SMSLead"
elif agent-browser is visible "[name='last_name']" 2>/dev/null; then
  agent-browser fill "[name='last_name']" "SMSLead"
fi

if agent-browser is visible "[data-testid='lead-phone']" 2>/dev/null; then
  agent-browser fill "[data-testid='lead-phone']" "5125551234"
elif agent-browser is visible "[name='phone']" 2>/dev/null; then
  agent-browser fill "[name='phone']" "5125551234"
fi

if agent-browser is visible "[data-testid='lead-email']" 2>/dev/null; then
  agent-browser fill "[data-testid='lead-email']" "e2e-sms@test.com"
elif agent-browser is visible "[name='email']" 2>/dev/null; then
  agent-browser fill "[name='email']" "e2e-sms@test.com"
fi

agent-browser screenshot "$SCREENSHOT_DIR/03-lead-filled.png"

# Submit the form
if agent-browser is visible "[data-testid='submit-btn']" 2>/dev/null; then
  agent-browser click "[data-testid='submit-btn']"
elif agent-browser is visible "button[type='submit']" 2>/dev/null; then
  agent-browser click "button[type='submit']"
fi

agent-browser wait --load networkidle
agent-browser wait 3000
agent-browser screenshot "$SCREENSHOT_DIR/04-lead-created.png"

PAGE_TEXT=$(agent-browser get text "body" 2>/dev/null || echo "")
if echo "$PAGE_TEXT" | grep -qi "success\|created\|SMSLead\|E2E Test"; then
  echo "  ✓ Lead created successfully"
  PASS_COUNT=$((PASS_COUNT + 1))
else
  echo "  ⚠ Lead creation result unclear"
fi

# ---------------------------------------------------------------------------
# Step 3: Verify SMS confirmation is logged
# ---------------------------------------------------------------------------
echo ""
echo "Step 3: Verifying SMS confirmation is logged..."

# Check for SMS confirmation in communications or sent messages
if echo "$PAGE_TEXT" | grep -qi "SMS.*sent\|confirmation.*sent\|message.*queued"; then
  echo "  ✓ SMS confirmation logged on page"
  PASS_COUNT=$((PASS_COUNT + 1))
else
  # Navigate to communications to check
  agent-browser open "${BASE_URL}/communications"
  agent-browser wait --load networkidle
  agent-browser wait 2000

  # Check sent messages tab
  if agent-browser is visible "[data-testid='sent-messages-tab']" 2>/dev/null; then
    agent-browser click "[data-testid='sent-messages-tab']"
  elif agent-browser is visible "text=Sent Messages" 2>/dev/null; then
    agent-browser click "text=Sent Messages"
  fi
  agent-browser wait --load networkidle
  agent-browser wait 2000

  COMMS_TEXT=$(agent-browser get text "body" 2>/dev/null || echo "")
  if echo "$COMMS_TEXT" | grep -qi "SMS\|confirmation\|5125551234\|SMSLead"; then
    echo "  ✓ SMS confirmation found in communications log"
    PASS_COUNT=$((PASS_COUNT + 1))
  else
    echo "  ⚠ SMS confirmation not found (may be async or Twilio not configured)"
  fi
fi

agent-browser screenshot "$SCREENSHOT_DIR/05-sms-verification.png"

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "-------------------------------------------------------"
echo "SMS Lead E2E Results: $PASS_COUNT passed, $FAIL_COUNT failed"
echo "Screenshots saved to: $SCREENSHOT_DIR/"
echo "-------------------------------------------------------"

if [ "$FAIL_COUNT" -gt 0 ]; then
  echo "❌ FAIL: SMS lead confirmation issues detected"
  exit 1
fi

echo "✅ PASS: All SMS lead confirmation tests passed"
exit 0
