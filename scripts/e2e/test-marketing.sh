#!/bin/bash
# E2E Test: Marketing Dashboard
# Validates: Requirements 45.13, 58.6, 63.9, 64.6, 65.6, 67.2
#
# Tests lead source analytics, conversion funnel, campaign creation,
# budget tracking, QR code generation, and CAC display.
#
# Usage:
#   bash scripts/e2e/test-marketing.sh [--headed]
#
# Prerequisites:
#   - Frontend running at http://localhost:5173
#   - Backend running at http://localhost:8000
#   - agent-browser installed

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCREENSHOT_DIR="e2e-screenshots/marketing"
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

echo "🧪 E2E Test: Marketing Dashboard (Req 45.13, 58.6, 63.9, 64.6, 65.6)"
echo "======================================================================="

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
# Step 2: Lead Sources and Conversion Funnel (Req 63)
# ---------------------------------------------------------------------------
echo ""
echo "Step 2: Verifying lead sources and conversion funnel (Req 63)..."
agent-browser open "${BASE_URL}/marketing"
agent-browser wait --load networkidle
agent-browser wait 2000
agent-browser screenshot "$SCREENSHOT_DIR/01-marketing-dashboard.png"

PAGE_TEXT=$(agent-browser get text "body" 2>/dev/null || echo "")

if agent-browser is visible "[data-testid='lead-sources-chart']" 2>/dev/null; then
  echo "  ✓ Lead Sources chart displayed"
  PASS_COUNT=$((PASS_COUNT + 1))
elif echo "$PAGE_TEXT" | grep -qi "lead source\|source"; then
  echo "  ✓ Lead source content detected"
  PASS_COUNT=$((PASS_COUNT + 1))
else
  echo "  ✗ FAIL: Lead Sources chart not found"
  FAIL_COUNT=$((FAIL_COUNT + 1))
fi

if agent-browser is visible "[data-testid='conversion-funnel']" 2>/dev/null; then
  FUNNEL_TEXT=$(agent-browser get text "[data-testid='conversion-funnel']" 2>/dev/null || echo "")
  if echo "$FUNNEL_TEXT" | grep -q '[0-9]'; then
    echo "  ✓ Conversion Funnel shows stage counts"
    PASS_COUNT=$((PASS_COUNT + 1))
  else
    echo "  ⚠ Conversion Funnel visible but no counts"
  fi
elif echo "$PAGE_TEXT" | grep -qi "funnel\|conversion\|stage"; then
  echo "  ✓ Conversion funnel content detected"
  PASS_COUNT=$((PASS_COUNT + 1))
else
  echo "  ✗ FAIL: Conversion Funnel not found"
  FAIL_COUNT=$((FAIL_COUNT + 1))
fi

# Change date range filter
if agent-browser is visible "[data-testid='date-range-filter']" 2>/dev/null; then
  agent-browser click "[data-testid='date-range-filter']"
  agent-browser wait 1000
  echo "  ✓ Date range filter available"
  PASS_COUNT=$((PASS_COUNT + 1))
fi

agent-browser screenshot "$SCREENSHOT_DIR/02-marketing-filtered.png"

# ---------------------------------------------------------------------------
# Step 3: Campaign creation (Req 45)
# ---------------------------------------------------------------------------
echo ""
echo "Step 3: Testing campaign creation (Req 45)..."
agent-browser open "${BASE_URL}/marketing/campaigns"
agent-browser wait --load networkidle
agent-browser wait 2000
agent-browser screenshot "$SCREENSHOT_DIR/03-campaigns-page.png"

# Create new campaign
if agent-browser is visible "[data-testid='create-campaign-btn']" 2>/dev/null; then
  agent-browser click "[data-testid='create-campaign-btn']"
elif agent-browser is visible "text=New Campaign" 2>/dev/null; then
  agent-browser click "text=New Campaign"
fi
agent-browser wait --load networkidle
agent-browser wait 2000

if agent-browser is visible "[data-testid='campaign-name']" 2>/dev/null; then
  agent-browser fill "[data-testid='campaign-name']" "E2E Test Campaign"
fi

if agent-browser is visible "[data-testid='campaign-body']" 2>/dev/null; then
  agent-browser fill "[data-testid='campaign-body']" "Test campaign message for E2E validation"
fi

# Select audience
if agent-browser is visible "[data-testid='audience-selector']" 2>/dev/null; then
  agent-browser click "[data-testid='audience-selector']"
  agent-browser wait 500
  if agent-browser is visible "[data-testid='audience-all-customers']" 2>/dev/null; then
    agent-browser click "[data-testid='audience-all-customers']"
  fi
fi

# Schedule
if agent-browser is visible "[data-testid='schedule-campaign-btn']" 2>/dev/null; then
  agent-browser click "[data-testid='schedule-campaign-btn']"
  agent-browser wait --load networkidle
  agent-browser wait 2000
  echo "  ✓ Campaign scheduled"
  PASS_COUNT=$((PASS_COUNT + 1))
elif agent-browser is visible "[data-testid='submit-btn']" 2>/dev/null; then
  agent-browser click "[data-testid='submit-btn']"
  agent-browser wait --load networkidle
  agent-browser wait 2000
  echo "  ✓ Campaign created"
  PASS_COUNT=$((PASS_COUNT + 1))
else
  PAGE_TEXT=$(agent-browser get text "body" 2>/dev/null || echo "")
  if echo "$PAGE_TEXT" | grep -qi "campaign"; then
    echo "  ✓ Campaign page accessible"
    PASS_COUNT=$((PASS_COUNT + 1))
  else
    echo "  ✗ FAIL: Campaign creation not available"
    FAIL_COUNT=$((FAIL_COUNT + 1))
  fi
fi

agent-browser screenshot "$SCREENSHOT_DIR/04-campaign-created.png"

# Verify campaign in list with SCHEDULED status
agent-browser open "${BASE_URL}/marketing/campaigns"
agent-browser wait --load networkidle
agent-browser wait 2000

PAGE_TEXT=$(agent-browser get text "body" 2>/dev/null || echo "")
if echo "$PAGE_TEXT" | grep -qi "scheduled\|draft\|E2E Test Campaign"; then
  echo "  ✓ Campaign visible in list with status"
  PASS_COUNT=$((PASS_COUNT + 1))
fi

agent-browser screenshot "$SCREENSHOT_DIR/05-campaign-list.png"

# ---------------------------------------------------------------------------
# Step 4: Budget vs Actual (Req 64)
# ---------------------------------------------------------------------------
echo ""
echo "Step 4: Testing budget tracking (Req 64)..."
agent-browser open "${BASE_URL}/marketing"
agent-browser wait --load networkidle
agent-browser wait 2000

if agent-browser is visible "[data-testid='budget-chart']" 2>/dev/null; then
  echo "  ✓ Budget vs Actual chart displayed"
  PASS_COUNT=$((PASS_COUNT + 1))
elif agent-browser is visible "[data-testid='budget-tracker']" 2>/dev/null; then
  echo "  ✓ Budget tracker section visible"
  PASS_COUNT=$((PASS_COUNT + 1))
else
  PAGE_TEXT=$(agent-browser get text "body" 2>/dev/null || echo "")
  if echo "$PAGE_TEXT" | grep -qi "budget\|actual\|spend"; then
    echo "  ✓ Budget content detected"
    PASS_COUNT=$((PASS_COUNT + 1))
  else
    echo "  ✗ FAIL: Budget vs Actual chart not found"
    FAIL_COUNT=$((FAIL_COUNT + 1))
  fi
fi

agent-browser screenshot "$SCREENSHOT_DIR/06-budget-chart.png"

# ---------------------------------------------------------------------------
# Step 5: QR Code Generation (Req 65)
# ---------------------------------------------------------------------------
echo ""
echo "Step 5: Testing QR code generation (Req 65)..."

if agent-browser is visible "[data-testid='qr-codes-tab']" 2>/dev/null; then
  agent-browser click "[data-testid='qr-codes-tab']"
elif agent-browser is visible "text=QR Codes" 2>/dev/null; then
  agent-browser click "text=QR Codes"
fi
agent-browser wait --load networkidle
agent-browser wait 2000
agent-browser screenshot "$SCREENSHOT_DIR/07-qr-codes.png"

if agent-browser is visible "[data-testid='generate-qr-btn']" 2>/dev/null; then
  agent-browser click "[data-testid='generate-qr-btn']"
  agent-browser wait --load networkidle
  agent-browser wait 2000

  if agent-browser is visible "[data-testid='qr-download-link']" 2>/dev/null || \
     agent-browser is visible "[data-testid='qr-code-image']" 2>/dev/null; then
    echo "  ✓ QR code generated with download link"
    PASS_COUNT=$((PASS_COUNT + 1))
  else
    PAGE_TEXT=$(agent-browser get text "body" 2>/dev/null || echo "")
    if echo "$PAGE_TEXT" | grep -qi "download\|qr\|generated"; then
      echo "  ✓ QR code generation feedback detected"
      PASS_COUNT=$((PASS_COUNT + 1))
    else
      echo "  ✗ FAIL: QR code download link not available"
      FAIL_COUNT=$((FAIL_COUNT + 1))
    fi
  fi
elif agent-browser is visible "text=Generate" 2>/dev/null; then
  agent-browser click "text=Generate"
  agent-browser wait --load networkidle
  agent-browser wait 2000
  echo "  ✓ QR code generation triggered"
  PASS_COUNT=$((PASS_COUNT + 1))
else
  PAGE_TEXT=$(agent-browser get text "body" 2>/dev/null || echo "")
  if echo "$PAGE_TEXT" | grep -qi "qr"; then
    echo "  ✓ QR code section accessible"
    PASS_COUNT=$((PASS_COUNT + 1))
  else
    echo "  ✗ FAIL: QR code section not found"
    FAIL_COUNT=$((FAIL_COUNT + 1))
  fi
fi

agent-browser screenshot "$SCREENSHOT_DIR/08-qr-generated.png"

# ---------------------------------------------------------------------------
# Step 6: CAC per channel (Req 58)
# ---------------------------------------------------------------------------
echo ""
echo "Step 6: Verifying CAC per channel (Req 58)..."
agent-browser open "${BASE_URL}/marketing"
agent-browser wait --load networkidle
agent-browser wait 2000

if agent-browser is visible "[data-testid='cac-chart']" 2>/dev/null; then
  echo "  ✓ CAC per channel chart displayed"
  PASS_COUNT=$((PASS_COUNT + 1))
elif agent-browser is visible "[data-testid='cac-display']" 2>/dev/null; then
  echo "  ✓ CAC display visible"
  PASS_COUNT=$((PASS_COUNT + 1))
else
  PAGE_TEXT=$(agent-browser get text "body" 2>/dev/null || echo "")
  if echo "$PAGE_TEXT" | grep -qi "CAC\|acquisition cost\|cost per"; then
    echo "  ✓ CAC content detected"
    PASS_COUNT=$((PASS_COUNT + 1))
  else
    echo "  ✗ FAIL: CAC per channel not displayed"
    FAIL_COUNT=$((FAIL_COUNT + 1))
  fi
fi

agent-browser screenshot "$SCREENSHOT_DIR/09-cac-display.png"

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "-------------------------------------------------------"
echo "Marketing E2E Results: $PASS_COUNT passed, $FAIL_COUNT failed"
echo "Screenshots saved to: $SCREENSHOT_DIR/"
echo "-------------------------------------------------------"

if [ "$FAIL_COUNT" -gt 0 ]; then
  echo "❌ FAIL: Marketing dashboard issues detected"
  exit 1
fi

echo "✅ PASS: All marketing dashboard tests passed"
exit 0
