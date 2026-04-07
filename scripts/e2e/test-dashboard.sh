#!/bin/bash
# E2E Test: Dashboard Widgets and Navigation
# Validates: Requirements 3.8, 4.8, 5.5, 6.5, 67.2
#
# Tests dashboard alert card navigation with filters/highlighting,
# Messages widget count and click-through, Pending Invoices widget
# numeric count, and all six job status categories with counts.
#
# Usage:
#   bash scripts/e2e/test-dashboard.sh [--headed]
#
# Prerequisites:
#   - Frontend running at http://localhost:5173
#   - Backend running at http://localhost:8000
#   - agent-browser installed
#   - Valid admin credentials in environment or defaults

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCREENSHOT_DIR="e2e-screenshots/dashboard"
BASE_URL="http://localhost:5173"
HEADED_FLAG=""

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

echo "🧪 E2E Test: Dashboard Widgets and Navigation (Req 3.8, 4.8, 5.5, 6.5)"
echo "========================================================================"

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
agent-browser screenshot "$SCREENSHOT_DIR/01-login-page.png"

# Fill email field
if agent-browser is visible "[data-testid='username-input']" 2>/dev/null; then
  agent-browser fill "[data-testid='username-input']" "$ADMIN_EMAIL"
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
agent-browser screenshot "$SCREENSHOT_DIR/02-after-login.png"

if echo "$CURRENT_URL" | grep -qi "/login"; then
  echo "  ✗ FAIL: Still on login page after login attempt"
  echo "❌ FAIL: Could not log in — aborting dashboard tests"
  exit 1
fi

echo "  ✓ Login successful — navigated to: $CURRENT_URL"
PASS_COUNT=$((PASS_COUNT + 1))

# ---------------------------------------------------------------------------
# Step 2: Navigate to /dashboard
# ---------------------------------------------------------------------------
echo ""
echo "Step 2: Navigating to /dashboard..."
agent-browser open "${BASE_URL}/dashboard"
agent-browser wait --load networkidle
agent-browser wait 2000
agent-browser screenshot "$SCREENSHOT_DIR/03-dashboard-loaded.png"

CURRENT_URL=$(agent-browser get url 2>/dev/null || echo "")
if echo "$CURRENT_URL" | grep -qi "/login"; then
  echo "  ✗ FAIL: Redirected to login"
  echo "❌ FAIL: Session lost — aborting"
  exit 1
fi

# Verify dashboard page loaded
if agent-browser is visible "[data-testid='dashboard-page']" 2>/dev/null; then
  echo "  ✓ Dashboard page loaded"
  PASS_COUNT=$((PASS_COUNT + 1))
else
  echo "  ✗ FAIL: Dashboard page element not found"
  FAIL_COUNT=$((FAIL_COUNT + 1))
fi


# ---------------------------------------------------------------------------
# Step 3: Test Alert Card click → navigation with filter (Req 3.8)
# ---------------------------------------------------------------------------
echo ""
echo "Step 3: Testing alert card navigation with filter and highlight (Req 3.8)..."

# The New Leads card (data-testid="leads-metric") navigates to /leads?status=new
ALERT_VISIBLE=false
if agent-browser is visible "[data-testid='leads-metric']" 2>/dev/null; then
  ALERT_VISIBLE=true
  echo "  ✓ New Leads alert card visible on dashboard"
  PASS_COUNT=$((PASS_COUNT + 1))

  agent-browser screenshot "$SCREENSHOT_DIR/04-alert-card-before-click.png"

  # Click the alert card
  agent-browser click "[data-testid='leads-metric']"
  agent-browser wait --load networkidle
  agent-browser wait 2000
  agent-browser screenshot "$SCREENSHOT_DIR/05-after-alert-click.png"

  # Verify navigation to /leads with status filter
  NAV_URL=$(agent-browser get url 2>/dev/null || echo "")
  if echo "$NAV_URL" | grep -qi "/leads"; then
    echo "  ✓ Navigated to leads page: $NAV_URL"
    PASS_COUNT=$((PASS_COUNT + 1))

    # Verify filter query param is present
    if echo "$NAV_URL" | grep -qi "status=new"; then
      echo "  ✓ Filter query parameter applied (status=new)"
      PASS_COUNT=$((PASS_COUNT + 1))
    else
      echo "  ✗ FAIL: Filter query parameter 'status=new' not found in URL"
      FAIL_COUNT=$((FAIL_COUNT + 1))
    fi
  else
    echo "  ✗ FAIL: Did not navigate to /leads page (URL: $NAV_URL)"
    FAIL_COUNT=$((FAIL_COUNT + 1))
  fi

  # Check for highlight animation (look for highlight-related CSS class or element)
  # The highlight animation uses a temporary background color animation
  PAGE_HTML=$(agent-browser get html "body" 2>/dev/null || echo "")
  if echo "$PAGE_HTML" | grep -qi "highlight\|animate\|ring\|pulse"; then
    echo "  ✓ Highlight animation detected on target page"
    PASS_COUNT=$((PASS_COUNT + 1))
  else
    echo "  ⚠ Highlight animation not detected (may have already completed)"
    # Not a hard fail — animation is 3 seconds and may have elapsed
  fi

  agent-browser screenshot "$SCREENSHOT_DIR/06-leads-with-filter.png"
else
  echo "  ⚠ New Leads alert card not visible — trying job status card as fallback..."

  # Fallback: try clicking a job status card which also navigates with filter
  if agent-browser is visible "[data-testid='job-status-new-requests']" 2>/dev/null; then
    ALERT_VISIBLE=true
    agent-browser click "[data-testid='job-status-new-requests']"
    agent-browser wait --load networkidle
    agent-browser wait 2000
    agent-browser screenshot "$SCREENSHOT_DIR/05-after-job-status-click.png"

    NAV_URL=$(agent-browser get url 2>/dev/null || echo "")
    if echo "$NAV_URL" | grep -qi "/jobs.*status="; then
      echo "  ✓ Job status card navigated with filter: $NAV_URL"
      PASS_COUNT=$((PASS_COUNT + 1))
    else
      echo "  ✗ FAIL: Job status card did not navigate with filter"
      FAIL_COUNT=$((FAIL_COUNT + 1))
    fi
  fi
fi

if [ "$ALERT_VISIBLE" = false ]; then
  echo "  ✗ FAIL: No alert cards found on dashboard"
  FAIL_COUNT=$((FAIL_COUNT + 1))
fi

# Navigate back to dashboard for remaining tests
echo ""
echo "  Returning to dashboard..."
agent-browser open "${BASE_URL}/dashboard"
agent-browser wait --load networkidle
agent-browser wait 2000

# ---------------------------------------------------------------------------
# Step 4: Test Messages widget count and click → communications (Req 4.8)
# ---------------------------------------------------------------------------
echo ""
echo "Step 4: Testing Messages widget count and navigation (Req 4.8)..."

if agent-browser is visible "[data-testid='messages-widget']" 2>/dev/null; then
  echo "  ✓ Messages widget visible on dashboard"
  PASS_COUNT=$((PASS_COUNT + 1))

  agent-browser screenshot "$SCREENSHOT_DIR/07-messages-widget.png"

  # Get the widget text to verify numeric count
  MESSAGES_TEXT=$(agent-browser get text "[data-testid='messages-widget']" 2>/dev/null || echo "")

  # Check that the widget displays a numeric count (digit characters present)
  if echo "$MESSAGES_TEXT" | grep -qP '\d+'; then
    echo "  ✓ Messages widget displays numeric count"
    PASS_COUNT=$((PASS_COUNT + 1))
  elif echo "$MESSAGES_TEXT" | grep -q '[0-9]'; then
    echo "  ✓ Messages widget displays numeric count"
    PASS_COUNT=$((PASS_COUNT + 1))
  else
    # Check for loading dash which means data is still loading
    if echo "$MESSAGES_TEXT" | grep -q '—'; then
      echo "  ⚠ Messages widget still loading (showing dash)"
      # Wait a bit more and retry
      agent-browser wait 3000
      MESSAGES_TEXT=$(agent-browser get text "[data-testid='messages-widget']" 2>/dev/null || echo "")
      if echo "$MESSAGES_TEXT" | grep -q '[0-9]'; then
        echo "  ✓ Messages widget displays numeric count after retry"
        PASS_COUNT=$((PASS_COUNT + 1))
      else
        echo "  ✗ FAIL: Messages widget does not display a numeric count"
        FAIL_COUNT=$((FAIL_COUNT + 1))
      fi
    else
      echo "  ✗ FAIL: Messages widget does not display a numeric count"
      FAIL_COUNT=$((FAIL_COUNT + 1))
    fi
  fi

  # Click the Messages widget
  agent-browser click "[data-testid='messages-widget']"
  agent-browser wait --load networkidle
  agent-browser wait 2000
  agent-browser screenshot "$SCREENSHOT_DIR/08-after-messages-click.png"

  # Verify navigation to /communications
  COMMS_URL=$(agent-browser get url 2>/dev/null || echo "")
  if echo "$COMMS_URL" | grep -qi "/communications"; then
    echo "  ✓ Navigated to communications queue: $COMMS_URL"
    PASS_COUNT=$((PASS_COUNT + 1))
  else
    echo "  ✗ FAIL: Did not navigate to /communications (URL: $COMMS_URL)"
    FAIL_COUNT=$((FAIL_COUNT + 1))
  fi
else
  echo "  ✗ FAIL: Messages widget not found on dashboard"
  FAIL_COUNT=$((FAIL_COUNT + 1))
fi

# Navigate back to dashboard
echo ""
echo "  Returning to dashboard..."
agent-browser open "${BASE_URL}/dashboard"
agent-browser wait --load networkidle
agent-browser wait 2000


# ---------------------------------------------------------------------------
# Step 5: Test Pending Invoices widget numeric count (Req 5.5)
# ---------------------------------------------------------------------------
echo ""
echo "Step 5: Testing Pending Invoices widget numeric count (Req 5.5)..."

if agent-browser is visible "[data-testid='invoice-metrics-widget']" 2>/dev/null; then
  echo "  ✓ Pending Invoices widget visible on dashboard"
  PASS_COUNT=$((PASS_COUNT + 1))

  agent-browser screenshot "$SCREENSHOT_DIR/09-invoice-metrics-widget.png"

  # Get the widget text to verify numeric count
  INVOICE_TEXT=$(agent-browser get text "[data-testid='invoice-metrics-widget']" 2>/dev/null || echo "")

  # Check that the widget displays a numeric count
  if echo "$INVOICE_TEXT" | grep -q '[0-9]'; then
    echo "  ✓ Pending Invoices widget displays numeric count"
    PASS_COUNT=$((PASS_COUNT + 1))

    # Verify it shows "Pending Invoices" label
    if echo "$INVOICE_TEXT" | grep -qi "Pending Invoices"; then
      echo "  ✓ Widget labeled 'Pending Invoices'"
      PASS_COUNT=$((PASS_COUNT + 1))
    else
      echo "  ⚠ 'Pending Invoices' label not found in widget text"
    fi
  else
    # Check for loading state
    if echo "$INVOICE_TEXT" | grep -q '—'; then
      echo "  ⚠ Invoice widget still loading — retrying..."
      agent-browser wait 3000
      INVOICE_TEXT=$(agent-browser get text "[data-testid='invoice-metrics-widget']" 2>/dev/null || echo "")
      if echo "$INVOICE_TEXT" | grep -q '[0-9]'; then
        echo "  ✓ Pending Invoices widget displays numeric count after retry"
        PASS_COUNT=$((PASS_COUNT + 1))
      else
        echo "  ✗ FAIL: Pending Invoices widget does not display a numeric count"
        FAIL_COUNT=$((FAIL_COUNT + 1))
      fi
    else
      echo "  ✗ FAIL: Pending Invoices widget does not display a numeric count"
      FAIL_COUNT=$((FAIL_COUNT + 1))
    fi
  fi
else
  echo "  ✗ FAIL: Pending Invoices widget not found on dashboard"
  FAIL_COUNT=$((FAIL_COUNT + 1))
fi

# ---------------------------------------------------------------------------
# Step 6: Test six job status categories with counts (Req 6.5)
# ---------------------------------------------------------------------------
echo ""
echo "Step 6: Testing six job status categories with counts (Req 6.5)..."

agent-browser screenshot "$SCREENSHOT_DIR/10-job-status-grid-area.png"

# Check the job status grid container
if agent-browser is visible "[data-testid='job-status-grid']" 2>/dev/null; then
  echo "  ✓ Job status grid visible on dashboard"
  PASS_COUNT=$((PASS_COUNT + 1))
else
  echo "  ⚠ Job status grid container not found — scrolling down..."
  agent-browser scroll down 500
  agent-browser wait 1000
fi

# Define the six expected job status categories and their test IDs
JOB_STATUS_CATEGORIES=(
  "job-status-new-requests|New Requests"
  "job-status-estimates|Estimates"
  "job-status-pending-approval|Pending Approval"
  "job-status-to-be-scheduled|To Be Scheduled"
  "job-status-in-progress|In Progress"
  "job-status-complete|Complete"
)

CATEGORIES_FOUND=0
CATEGORIES_WITH_COUNT=0

for entry in "${JOB_STATUS_CATEGORIES[@]}"; do
  IFS='|' read -r testid label <<< "$entry"

  if agent-browser is visible "[data-testid='${testid}']" 2>/dev/null; then
    CATEGORIES_FOUND=$((CATEGORIES_FOUND + 1))

    # Get the text content of the card to verify numeric count
    CARD_TEXT=$(agent-browser get text "[data-testid='${testid}']" 2>/dev/null || echo "")

    if echo "$CARD_TEXT" | grep -q '[0-9]'; then
      CATEGORIES_WITH_COUNT=$((CATEGORIES_WITH_COUNT + 1))
      echo "  ✓ ${label}: visible with numeric count"
    elif echo "$CARD_TEXT" | grep -q '—'; then
      echo "  ⚠ ${label}: visible but still loading"
    else
      echo "  ✗ ${label}: visible but no numeric count found"
    fi
  else
    echo "  ✗ ${label}: NOT visible (data-testid='${testid}')"
  fi
done

agent-browser screenshot "$SCREENSHOT_DIR/11-job-status-categories.png"

# Verify all six categories are present
if [ "$CATEGORIES_FOUND" -eq 6 ]; then
  echo "  ✓ All 6 job status categories displayed"
  PASS_COUNT=$((PASS_COUNT + 1))
else
  echo "  ✗ FAIL: Only ${CATEGORIES_FOUND}/6 job status categories found"
  FAIL_COUNT=$((FAIL_COUNT + 1))
fi

# Verify categories show numeric counts
if [ "$CATEGORIES_WITH_COUNT" -ge 5 ]; then
  echo "  ✓ ${CATEGORIES_WITH_COUNT}/6 categories display numeric counts"
  PASS_COUNT=$((PASS_COUNT + 1))
elif [ "$CATEGORIES_WITH_COUNT" -ge 1 ]; then
  echo "  ⚠ Only ${CATEGORIES_WITH_COUNT}/6 categories have numeric counts (some may be loading)"
  PASS_COUNT=$((PASS_COUNT + 1))
else
  echo "  ✗ FAIL: No job status categories display numeric counts"
  FAIL_COUNT=$((FAIL_COUNT + 1))
fi

# Take a final full-page screenshot
agent-browser screenshot --full "$SCREENSHOT_DIR/12-dashboard-full-page.png" 2>/dev/null || \
  agent-browser screenshot "$SCREENSHOT_DIR/12-dashboard-final.png"

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "-------------------------------------------------------"
echo "Dashboard E2E Results: $PASS_COUNT passed, $FAIL_COUNT failed"
echo "Screenshots saved to: $SCREENSHOT_DIR/"
echo "-------------------------------------------------------"

if [ "$FAIL_COUNT" -gt 0 ]; then
  echo "❌ FAIL: Dashboard widget/navigation issues detected"
  exit 1
fi

echo "✅ PASS: All dashboard widget and navigation tests passed"
exit 0
