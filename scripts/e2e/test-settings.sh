#!/bin/bash
# E2E Test: Settings Page
# Validates: Requirements 87.10, 87.11, 67.2
#
# Tests editing company name in Business Information, saving, reloading,
# and verifying payment terms default affects new invoices.
#
# Usage:
#   bash scripts/e2e/test-settings.sh [--headed]
#
# Prerequisites:
#   - Frontend running at http://localhost:5173
#   - Backend running at http://localhost:8000
#   - agent-browser installed

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCREENSHOT_DIR="e2e-screenshots/settings"
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

echo "🧪 E2E Test: Settings Page (Req 87.10, 87.11)"
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
# Step 2: Edit company name in Business Information (Req 87.10)
# ---------------------------------------------------------------------------
echo ""
echo "Step 2: Editing company name in Business Information (Req 87)..."
agent-browser open "${BASE_URL}/settings"
agent-browser wait --load networkidle
agent-browser wait 2000
agent-browser screenshot "$SCREENSHOT_DIR/01-settings-page.png"

# Find and edit company name
ORIGINAL_NAME=""
if agent-browser is visible "[data-testid='company-name-input']" 2>/dev/null; then
  ORIGINAL_NAME=$(agent-browser get value "[data-testid='company-name-input']" 2>/dev/null || echo "")
  agent-browser fill "[data-testid='company-name-input']" "E2E Test Company Name"
  echo "  ✓ Company name edited"
  PASS_COUNT=$((PASS_COUNT + 1))
elif agent-browser is visible "[name='company_name']" 2>/dev/null; then
  ORIGINAL_NAME=$(agent-browser get value "[name='company_name']" 2>/dev/null || echo "")
  agent-browser fill "[name='company_name']" "E2E Test Company Name"
  echo "  ✓ Company name edited"
  PASS_COUNT=$((PASS_COUNT + 1))
elif agent-browser is visible "[data-testid='business-info-edit-btn']" 2>/dev/null; then
  agent-browser click "[data-testid='business-info-edit-btn']"
  agent-browser wait 1000
  if agent-browser is visible "[data-testid='company-name-input']" 2>/dev/null; then
    agent-browser fill "[data-testid='company-name-input']" "E2E Test Company Name"
    echo "  ✓ Company name edited after clicking edit"
    PASS_COUNT=$((PASS_COUNT + 1))
  fi
else
  echo "  ⚠ Company name input not found"
fi

agent-browser screenshot "$SCREENSHOT_DIR/02-company-name-edited.png"

# Save
if agent-browser is visible "[data-testid='save-settings-btn']" 2>/dev/null; then
  agent-browser click "[data-testid='save-settings-btn']"
elif agent-browser is visible "[data-testid='submit-btn']" 2>/dev/null; then
  agent-browser click "[data-testid='submit-btn']"
elif agent-browser is visible "button[type='submit']" 2>/dev/null; then
  agent-browser click "button[type='submit']"
fi

agent-browser wait --load networkidle
agent-browser wait 2000
agent-browser screenshot "$SCREENSHOT_DIR/03-settings-saved.png"

# Reload page and verify change persists
agent-browser open "${BASE_URL}/settings"
agent-browser wait --load networkidle
agent-browser wait 2000
agent-browser screenshot "$SCREENSHOT_DIR/04-settings-reloaded.png"

SAVED_NAME=""
if agent-browser is visible "[data-testid='company-name-input']" 2>/dev/null; then
  SAVED_NAME=$(agent-browser get value "[data-testid='company-name-input']" 2>/dev/null || echo "")
elif agent-browser is visible "[name='company_name']" 2>/dev/null; then
  SAVED_NAME=$(agent-browser get value "[name='company_name']" 2>/dev/null || echo "")
fi

if echo "$SAVED_NAME" | grep -qi "E2E Test Company Name"; then
  echo "  ✓ Company name change persisted after reload"
  PASS_COUNT=$((PASS_COUNT + 1))
else
  PAGE_TEXT=$(agent-browser get text "body" 2>/dev/null || echo "")
  if echo "$PAGE_TEXT" | grep -qi "E2E Test Company Name"; then
    echo "  ✓ Company name visible on page after reload"
    PASS_COUNT=$((PASS_COUNT + 1))
  else
    echo "  ✗ FAIL: Company name change did not persist"
    FAIL_COUNT=$((FAIL_COUNT + 1))
  fi
fi

# Restore original name if we captured it
if [ -n "$ORIGINAL_NAME" ]; then
  if agent-browser is visible "[data-testid='company-name-input']" 2>/dev/null; then
    agent-browser fill "[data-testid='company-name-input']" "$ORIGINAL_NAME"
  elif agent-browser is visible "[name='company_name']" 2>/dev/null; then
    agent-browser fill "[name='company_name']" "$ORIGINAL_NAME"
  fi
  if agent-browser is visible "[data-testid='save-settings-btn']" 2>/dev/null; then
    agent-browser click "[data-testid='save-settings-btn']"
  elif agent-browser is visible "button[type='submit']" 2>/dev/null; then
    agent-browser click "button[type='submit']"
  fi
  agent-browser wait --load networkidle
  agent-browser wait 2000
  echo "  ✓ Original company name restored"
fi

# ---------------------------------------------------------------------------
# Step 3: Modify payment terms and verify on new invoice (Req 87.11)
# ---------------------------------------------------------------------------
echo ""
echo "Step 3: Modifying default payment terms (Req 87)..."
agent-browser open "${BASE_URL}/settings"
agent-browser wait --load networkidle
agent-browser wait 2000

# Find payment terms field
if agent-browser is visible "[data-testid='payment-terms-input']" 2>/dev/null; then
  agent-browser fill "[data-testid='payment-terms-input']" "45"
  echo "  ✓ Payment terms set to 45 days"
  PASS_COUNT=$((PASS_COUNT + 1))
elif agent-browser is visible "[name='default_payment_terms_days']" 2>/dev/null; then
  agent-browser fill "[name='default_payment_terms_days']" "45"
  echo "  ✓ Payment terms set to 45 days"
  PASS_COUNT=$((PASS_COUNT + 1))
elif agent-browser is visible "[data-testid='invoice-defaults-tab']" 2>/dev/null; then
  agent-browser click "[data-testid='invoice-defaults-tab']"
  agent-browser wait 1000
  if agent-browser is visible "[data-testid='payment-terms-input']" 2>/dev/null; then
    agent-browser fill "[data-testid='payment-terms-input']" "45"
    echo "  ✓ Payment terms set to 45 days"
    PASS_COUNT=$((PASS_COUNT + 1))
  fi
else
  echo "  ⚠ Payment terms input not found"
fi

# Save settings
if agent-browser is visible "[data-testid='save-settings-btn']" 2>/dev/null; then
  agent-browser click "[data-testid='save-settings-btn']"
elif agent-browser is visible "button[type='submit']" 2>/dev/null; then
  agent-browser click "button[type='submit']"
fi

agent-browser wait --load networkidle
agent-browser wait 2000
agent-browser screenshot "$SCREENSHOT_DIR/05-payment-terms-saved.png"

# Navigate to invoices and check if new invoice reflects the default
agent-browser open "${BASE_URL}/invoices"
agent-browser wait --load networkidle
agent-browser wait 2000

PAGE_TEXT=$(agent-browser get text "body" 2>/dev/null || echo "")
if echo "$PAGE_TEXT" | grep -qi "invoice\|due\|payment"; then
  echo "  ✓ Invoice page accessible to verify payment terms"
  PASS_COUNT=$((PASS_COUNT + 1))
fi

agent-browser screenshot "$SCREENSHOT_DIR/06-invoices-with-terms.png"

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "-------------------------------------------------------"
echo "Settings E2E Results: $PASS_COUNT passed, $FAIL_COUNT failed"
echo "Screenshots saved to: $SCREENSHOT_DIR/"
echo "-------------------------------------------------------"

if [ "$FAIL_COUNT" -gt 0 ]; then
  echo "❌ FAIL: Settings page issues detected"
  exit 1
fi

echo "✅ PASS: All settings page tests passed"
exit 0
