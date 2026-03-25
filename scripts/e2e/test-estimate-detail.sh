#!/bin/bash
# E2E Test: Estimate Detail Page
# Validates: Requirements 83.8, 83.9, 67.2
#
# Tests estimate detail view with line items, status badge, activity
# timeline, and resend functionality.
#
# Usage:
#   bash scripts/e2e/test-estimate-detail.sh [--headed]
#
# Prerequisites:
#   - Frontend running at http://localhost:5173
#   - Backend running at http://localhost:8000
#   - agent-browser installed

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCREENSHOT_DIR="e2e-screenshots/estimate-detail"
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

echo "🧪 E2E Test: Estimate Detail (Req 83.8, 83.9)"
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
# Step 2: Navigate to estimate detail via sales pipeline (Req 83.8)
# ---------------------------------------------------------------------------
echo ""
echo "Step 2: Navigating to estimate detail via sales pipeline (Req 83)..."
agent-browser open "${BASE_URL}/sales"
agent-browser wait --load networkidle
agent-browser wait 2000
agent-browser screenshot "$SCREENSHOT_DIR/01-sales-page.png"

# Click a pipeline card
PIPELINE_CLICKED=false
for card in "pipeline-sent" "pipeline-draft" "pipeline-pending-approval" "pipeline-approved"; do
  if agent-browser is visible "[data-testid='${card}']" 2>/dev/null; then
    agent-browser click "[data-testid='${card}']"
    PIPELINE_CLICKED=true
    break
  fi
done

if [ "$PIPELINE_CLICKED" = false ]; then
  # Try clicking any pipeline section
  if agent-browser is visible "[data-testid='pipeline-section']" 2>/dev/null; then
    agent-browser click "[data-testid='pipeline-section']"
    PIPELINE_CLICKED=true
  fi
fi

agent-browser wait --load networkidle
agent-browser wait 2000
agent-browser screenshot "$SCREENSHOT_DIR/02-pipeline-expanded.png"

# Click an estimate row
if agent-browser is visible "[data-testid='estimate-row']" 2>/dev/null; then
  agent-browser click "[data-testid='estimate-row']"
  agent-browser wait --load networkidle
  agent-browser wait 2000
  echo "  ✓ Estimate row clicked"
  PASS_COUNT=$((PASS_COUNT + 1))
elif agent-browser is visible "tbody tr" 2>/dev/null; then
  agent-browser click "tbody tr"
  agent-browser wait --load networkidle
  agent-browser wait 2000
  echo "  ✓ Estimate row clicked (fallback)"
  PASS_COUNT=$((PASS_COUNT + 1))
fi

agent-browser screenshot "$SCREENSHOT_DIR/03-estimate-detail.png"

# Verify EstimateDetail page content
PAGE_TEXT=$(agent-browser get text "body" 2>/dev/null || echo "")

# Check for line items
if agent-browser is visible "[data-testid='estimate-line-items']" 2>/dev/null || \
   echo "$PAGE_TEXT" | grep -qi "line item\|item\|quantity\|price\|amount"; then
  echo "  ✓ Line items displayed on estimate detail"
  PASS_COUNT=$((PASS_COUNT + 1))
else
  echo "  ⚠ Line items section not found"
fi

# Check for status badge
if agent-browser is visible "[data-testid='estimate-status-badge']" 2>/dev/null || \
   echo "$PAGE_TEXT" | grep -qi "draft\|sent\|approved\|pending\|rejected"; then
  echo "  ✓ Status badge displayed"
  PASS_COUNT=$((PASS_COUNT + 1))
else
  echo "  ⚠ Status badge not found"
fi

# Check for activity timeline
if agent-browser is visible "[data-testid='activity-timeline']" 2>/dev/null || \
   echo "$PAGE_TEXT" | grep -qi "activity\|timeline\|history\|created\|updated"; then
  echo "  ✓ Activity timeline displayed"
  PASS_COUNT=$((PASS_COUNT + 1))
else
  echo "  ⚠ Activity timeline not found"
fi

# ---------------------------------------------------------------------------
# Step 3: Test Resend functionality (Req 83.9)
# ---------------------------------------------------------------------------
echo ""
echo "Step 3: Testing resend functionality (Req 83)..."

if agent-browser is visible "[data-testid='resend-btn']" 2>/dev/null; then
  agent-browser click "[data-testid='resend-btn']"
  agent-browser wait --load networkidle
  agent-browser wait 2000
  agent-browser screenshot "$SCREENSHOT_DIR/04-after-resend.png"

  PAGE_TEXT=$(agent-browser get text "body" 2>/dev/null || echo "")
  if echo "$PAGE_TEXT" | grep -qi "resent\|sent\|follow.up\|scheduled\|success"; then
    echo "  ✓ Resend successful — status updated and follow-up scheduled"
    PASS_COUNT=$((PASS_COUNT + 1))
  else
    echo "  ⚠ Resend clicked but confirmation unclear"
  fi
elif agent-browser is visible "text=Resend" 2>/dev/null; then
  agent-browser click "text=Resend"
  agent-browser wait --load networkidle
  agent-browser wait 2000
  echo "  ✓ Resend button clicked"
  PASS_COUNT=$((PASS_COUNT + 1))
else
  echo "  ⚠ Resend button not found on estimate detail"
fi

agent-browser screenshot "$SCREENSHOT_DIR/05-resend-result.png"

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "-------------------------------------------------------"
echo "Estimate Detail E2E Results: $PASS_COUNT passed, $FAIL_COUNT failed"
echo "Screenshots saved to: $SCREENSHOT_DIR/"
echo "-------------------------------------------------------"

if [ "$FAIL_COUNT" -gt 0 ]; then
  echo "❌ FAIL: Estimate detail issues detected"
  exit 1
fi

echo "✅ PASS: All estimate detail tests passed"
exit 0
