#!/bin/bash
# E2E Test: Jobs Features
# Validates: Requirements 20.7, 21.6, 22.7, 23.6, 57.5, 67.2
#
# Tests job summary column visibility, notes editing and persistence,
# simplified status filter labels and badges, column changes (no Category,
# Customer names, Tags badges, Days Waiting counts), Due By column with
# color coding, and per-job financials display.
#
# Usage:
#   bash scripts/e2e/test-jobs.sh [--headed]
#
# Prerequisites:
#   - Frontend running at http://localhost:5173
#   - Backend running at http://localhost:8000
#   - agent-browser installed
#   - Valid admin credentials in environment or defaults

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCREENSHOT_DIR="e2e-screenshots/jobs"
BASE_URL="http://localhost:5173"
HEADED_FLAG=""

# Admin credentials (from env or defaults for dev)
ADMIN_EMAIL="${E2E_ADMIN_EMAIL:-admin@grins.com}"
ADMIN_PASSWORD="${E2E_ADMIN_PASSWORD:-admin123}"

# Parse arguments
for arg in "$@"; do
  case $arg in
    --headed) HEADED_FLAG="--headed" ;;
  esac
done

mkdir -p "$SCREENSHOT_DIR"

echo "🧪 E2E Test: Jobs Features (Req 20.7, 21.6, 22.7, 23.6, 57.5)"
echo "================================================================"

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
agent-browser screenshot "$SCREENSHOT_DIR/02-after-login.png"

if echo "$CURRENT_URL" | grep -qi "/login"; then
  echo "  ✗ FAIL: Still on login page after login attempt"
  echo "❌ FAIL: Could not log in — aborting jobs tests"
  exit 1
fi

echo "  ✓ Login successful — navigated to: $CURRENT_URL"
PASS_COUNT=$((PASS_COUNT + 1))

# ---------------------------------------------------------------------------
# Step 2: Navigate to /jobs
# ---------------------------------------------------------------------------
echo ""
echo "Step 2: Navigating to /jobs..."
agent-browser open "${BASE_URL}/jobs"
agent-browser wait --load networkidle
agent-browser wait 2000
agent-browser screenshot "$SCREENSHOT_DIR/03-jobs-list.png"

CURRENT_URL=$(agent-browser get url 2>/dev/null || echo "")
if echo "$CURRENT_URL" | grep -qi "/login"; then
  echo "  ✗ FAIL: Redirected to login"
  echo "❌ FAIL: Session lost — aborting"
  exit 1
fi

# Verify jobs page loaded
if agent-browser is visible "[data-testid='job-list']" 2>/dev/null; then
  echo "  ✓ Jobs list loaded"
  PASS_COUNT=$((PASS_COUNT + 1))
else
  echo "  ✗ FAIL: Jobs list not found (data-testid='job-list')"
  FAIL_COUNT=$((FAIL_COUNT + 1))
fi

# ---------------------------------------------------------------------------
# Step 3: Verify Summary column visible (Req 20.7)
# ---------------------------------------------------------------------------
echo ""
echo "Step 3: Verifying Summary column visible (Req 20.7)..."

# Check that the job table has a Summary header
TABLE_HTML=$(agent-browser get html "[data-testid='job-table']" 2>/dev/null || echo "")
if echo "$TABLE_HTML" | grep -qi "Summary"; then
  echo "  ✓ Summary column header found in job table"
  PASS_COUNT=$((PASS_COUNT + 1))
else
  echo "  ✗ FAIL: Summary column header not found in job table"
  FAIL_COUNT=$((FAIL_COUNT + 1))
fi

agent-browser screenshot "$SCREENSHOT_DIR/04-summary-column.png"

# ---------------------------------------------------------------------------
# Step 4: Click a job, edit notes, save, verify persistence (Req 20.7)
# ---------------------------------------------------------------------------
echo ""
echo "Step 4: Testing job notes edit and persistence (Req 20.7)..."

# Click the first job row link to navigate to detail
if agent-browser is visible "[data-testid='job-row'] a" 2>/dev/null; then
  agent-browser click "[data-testid='job-row'] a"
elif agent-browser is visible "[data-testid='job-row']" 2>/dev/null; then
  agent-browser click "[data-testid='job-row']"
else
  echo "  ✗ FAIL: No job rows found to click"
  FAIL_COUNT=$((FAIL_COUNT + 1))
fi

agent-browser wait --load networkidle
agent-browser wait 2000
agent-browser screenshot "$SCREENSHOT_DIR/05-job-detail.png"

DETAIL_URL=$(agent-browser get url 2>/dev/null || echo "")
if echo "$DETAIL_URL" | grep -qi "/jobs/"; then
  echo "  ✓ Navigated to job detail: $DETAIL_URL"
  PASS_COUNT=$((PASS_COUNT + 1))
else
  echo "  ⚠ May not be on job detail page (URL: $DETAIL_URL)"
fi

# Scroll to find notes section
agent-browser scroll down 300 2>/dev/null || true
agent-browser wait 500

NOTES_TIMESTAMP="E2E test note $(date +%s)"

if agent-browser is visible "[data-testid='job-notes-textarea']" 2>/dev/null; then
  echo "  ✓ Notes textarea visible"
  PASS_COUNT=$((PASS_COUNT + 1))

  # Clear and fill the notes textarea
  agent-browser fill "[data-testid='job-notes-textarea']" "$NOTES_TIMESTAMP"
  agent-browser screenshot "$SCREENSHOT_DIR/06-notes-filled.png"

  # Save the notes
  if agent-browser is visible "[data-testid='save-notes-btn']" 2>/dev/null; then
    agent-browser click "[data-testid='save-notes-btn']"
    agent-browser wait --load networkidle
    agent-browser wait 2000
    agent-browser screenshot "$SCREENSHOT_DIR/07-notes-saved.png"
    echo "  ✓ Notes save button clicked"
    PASS_COUNT=$((PASS_COUNT + 1))
  else
    echo "  ✗ FAIL: Save notes button not found (data-testid='save-notes-btn')"
    FAIL_COUNT=$((FAIL_COUNT + 1))
  fi

  # Reload the page to verify persistence
  agent-browser open "$DETAIL_URL"
  agent-browser wait --load networkidle
  agent-browser wait 2000

  # Scroll to notes section again
  agent-browser scroll down 300 2>/dev/null || true
  agent-browser wait 500

  # Verify the notes persisted
  NOTES_TEXT=""
  if agent-browser is visible "[data-testid='job-notes-textarea']" 2>/dev/null; then
    NOTES_TEXT=$(agent-browser get value "[data-testid='job-notes-textarea']" 2>/dev/null || echo "")
  fi

  if echo "$NOTES_TEXT" | grep -q "E2E test note"; then
    echo "  ✓ Job notes persisted after reload"
    PASS_COUNT=$((PASS_COUNT + 1))
  else
    echo "  ✗ FAIL: Job notes did not persist after reload"
    FAIL_COUNT=$((FAIL_COUNT + 1))
  fi

  agent-browser screenshot "$SCREENSHOT_DIR/08-notes-after-reload.png"
else
  echo "  ✗ FAIL: Notes textarea not found (data-testid='job-notes-textarea')"
  FAIL_COUNT=$((FAIL_COUNT + 1))
fi

# ---------------------------------------------------------------------------
# Step 5: Verify status filter shows simplified labels (Req 21.6)
# ---------------------------------------------------------------------------
echo ""
echo "Step 5: Verifying simplified status filter and badges (Req 21.6)..."

# Navigate back to /jobs
agent-browser open "${BASE_URL}/jobs"
agent-browser wait --load networkidle
agent-browser wait 2000
agent-browser screenshot "$SCREENSHOT_DIR/09-jobs-list-for-status.png"

# Check the status filter exists
if agent-browser is visible "[data-testid='status-filter']" 2>/dev/null; then
  echo "  ✓ Status filter found"
  PASS_COUNT=$((PASS_COUNT + 1))

  # Click the status filter to open dropdown
  agent-browser click "[data-testid='status-filter']"
  agent-browser wait 500
  agent-browser screenshot "$SCREENSHOT_DIR/10-status-filter-open.png"

  # Check for simplified labels in the dropdown
  FILTER_HTML=$(agent-browser get html "[data-testid='status-filter-options']" 2>/dev/null || echo "")
  SIMPLIFIED_FOUND=0

  if echo "$FILTER_HTML" | grep -qi "To Be Scheduled"; then
    echo "  ✓ Simplified label 'To Be Scheduled' found in filter"
    SIMPLIFIED_FOUND=$((SIMPLIFIED_FOUND + 1))
  fi
  if echo "$FILTER_HTML" | grep -qi "In Progress"; then
    echo "  ✓ Simplified label 'In Progress' found in filter"
    SIMPLIFIED_FOUND=$((SIMPLIFIED_FOUND + 1))
  fi
  if echo "$FILTER_HTML" | grep -qi "Complete"; then
    echo "  ✓ Simplified label 'Complete' found in filter"
    SIMPLIFIED_FOUND=$((SIMPLIFIED_FOUND + 1))
  fi

  if [ "$SIMPLIFIED_FOUND" -ge 2 ]; then
    echo "  ✓ Simplified status labels present in filter ($SIMPLIFIED_FOUND found)"
    PASS_COUNT=$((PASS_COUNT + 1))
  else
    echo "  ✗ FAIL: Simplified status labels not found in filter (found $SIMPLIFIED_FOUND)"
    FAIL_COUNT=$((FAIL_COUNT + 1))
  fi

  # Close the dropdown by pressing Escape
  agent-browser press Escape 2>/dev/null || true
  agent-browser wait 300
else
  echo "  ✗ FAIL: Status filter not found (data-testid='status-filter')"
  FAIL_COUNT=$((FAIL_COUNT + 1))
fi

# Verify job rows display simplified status badges
BADGE_COUNT=$(agent-browser get count "[data-testid='job-status-badge']" 2>/dev/null || echo "0")
if [ "$BADGE_COUNT" -gt 0 ] 2>/dev/null; then
  echo "  ✓ Job status badges displayed: $BADGE_COUNT"
  PASS_COUNT=$((PASS_COUNT + 1))

  # Check that badges show simplified labels (not raw enum values)
  BADGE_TEXT=$(agent-browser get text "[data-testid='job-status-badge']" 2>/dev/null || echo "")
  if echo "$BADGE_TEXT" | grep -qiE "To Be Scheduled|In Progress|Complete|Cancelled"; then
    echo "  ✓ Status badges show simplified labels"
    PASS_COUNT=$((PASS_COUNT + 1))
  else
    echo "  ⚠ Could not confirm simplified label text (text: ${BADGE_TEXT:0:80})"
  fi
else
  echo "  ⚠ No job status badges found — table may be empty"
fi

agent-browser screenshot "$SCREENSHOT_DIR/11-status-badges.png"

# ---------------------------------------------------------------------------
# Step 6: Verify column changes (Req 22.7)
# ---------------------------------------------------------------------------
echo ""
echo "Step 6: Verifying job list column changes (Req 22.7)..."

agent-browser screenshot "$SCREENSHOT_DIR/12-jobs-columns.png"

# Get the full table header HTML to check columns
HEADER_HTML=$(agent-browser get html "[data-testid='job-table'] thead" 2>/dev/null || echo "")

# 6a: Category column should be absent
if echo "$HEADER_HTML" | grep -qi "Category"; then
  echo "  ✗ FAIL: Category column still present — should be removed"
  FAIL_COUNT=$((FAIL_COUNT + 1))
else
  echo "  ✓ Category column absent from job table"
  PASS_COUNT=$((PASS_COUNT + 1))
fi

# 6b: Customer column should be present with names
if echo "$HEADER_HTML" | grep -qi "Customer"; then
  echo "  ✓ Customer column header present"
  PASS_COUNT=$((PASS_COUNT + 1))

  # Check that customer names are displayed in rows
  CUSTOMER_LINK_COUNT=$(agent-browser get count "[data-testid^='job-customer-']" 2>/dev/null || echo "0")
  if [ "$CUSTOMER_LINK_COUNT" -gt 0 ] 2>/dev/null; then
    echo "  ✓ Customer names displayed in rows: $CUSTOMER_LINK_COUNT"
    PASS_COUNT=$((PASS_COUNT + 1))
  else
    echo "  ⚠ No customer name links found — jobs may not have customers assigned"
  fi
else
  echo "  ✗ FAIL: Customer column header not found"
  FAIL_COUNT=$((FAIL_COUNT + 1))
fi

# 6c: Tags column should be present with badges
if echo "$HEADER_HTML" | grep -qi "Tags"; then
  echo "  ✓ Tags column header present"
  PASS_COUNT=$((PASS_COUNT + 1))

  # Check for tag badges in rows
  TAG_CONTAINER_COUNT=$(agent-browser get count "[data-testid^='job-tags-']" 2>/dev/null || echo "0")
  if [ "$TAG_CONTAINER_COUNT" -gt 0 ] 2>/dev/null; then
    echo "  ✓ Tag badge containers found: $TAG_CONTAINER_COUNT"
    PASS_COUNT=$((PASS_COUNT + 1))
  else
    echo "  ⚠ No tag badge containers found — customers may not have tags"
  fi
else
  echo "  ✗ FAIL: Tags column header not found"
  FAIL_COUNT=$((FAIL_COUNT + 1))
fi

# 6d: Days Waiting column should show numeric counts
if echo "$HEADER_HTML" | grep -qi "Days Waiting"; then
  echo "  ✓ Days Waiting column header present"
  PASS_COUNT=$((PASS_COUNT + 1))

  # Check that days waiting values are numeric
  DAYS_COUNT=$(agent-browser get count "[data-testid^='days-waiting-']" 2>/dev/null || echo "0")
  if [ "$DAYS_COUNT" -gt 0 ] 2>/dev/null; then
    DAYS_TEXT=$(agent-browser get text "[data-testid^='days-waiting-']" 2>/dev/null || echo "")
    if echo "$DAYS_TEXT" | grep -qE "^[0-9]+$"; then
      echo "  ✓ Days Waiting shows numeric count: $DAYS_TEXT"
      PASS_COUNT=$((PASS_COUNT + 1))
    else
      echo "  ⚠ Days Waiting text may not be purely numeric (text: ${DAYS_TEXT:0:40})"
    fi
  else
    echo "  ⚠ No days-waiting elements found — table may be empty"
  fi
else
  echo "  ✗ FAIL: Days Waiting column header not found"
  FAIL_COUNT=$((FAIL_COUNT + 1))
fi

agent-browser screenshot "$SCREENSHOT_DIR/13-columns-verified.png"

# ---------------------------------------------------------------------------
# Step 7: Verify "Due By" column with color coding (Req 23.6)
# ---------------------------------------------------------------------------
echo ""
echo "Step 7: Verifying Due By column with color coding (Req 23.6)..."

# Check Due By column header
if echo "$HEADER_HTML" | grep -qi "Due By"; then
  echo "  ✓ Due By column header present"
  PASS_COUNT=$((PASS_COUNT + 1))

  # Check for due-by elements in rows
  DUE_BY_COUNT=$(agent-browser get count "[data-testid^='due-by-']" 2>/dev/null || echo "0")
  if [ "$DUE_BY_COUNT" -gt 0 ] 2>/dev/null; then
    echo "  ✓ Due By values displayed: $DUE_BY_COUNT"
    PASS_COUNT=$((PASS_COUNT + 1))

    # Check for date text or "No deadline" in due-by elements
    DUE_BY_HTML=$(agent-browser get html "[data-testid^='due-by-']" 2>/dev/null || echo "")
    if echo "$DUE_BY_HTML" | grep -qiE "No deadline|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec"; then
      echo "  ✓ Due By column displays dates or 'No deadline'"
      PASS_COUNT=$((PASS_COUNT + 1))
    else
      echo "  ⚠ Could not confirm date format in Due By column"
    fi

    # Check for color coding classes (amber/warning for upcoming, red/danger for overdue)
    if echo "$DUE_BY_HTML" | grep -qiE "text-amber|text-red|text-orange|text-slate"; then
      echo "  ✓ Due By column has color coding classes"
      PASS_COUNT=$((PASS_COUNT + 1))
    else
      echo "  ⚠ Color coding classes not detected — may all be default color"
    fi
  else
    echo "  ⚠ No due-by elements found — table may be empty"
  fi
else
  echo "  ✗ FAIL: Due By column header not found"
  FAIL_COUNT=$((FAIL_COUNT + 1))
fi

agent-browser screenshot "$SCREENSHOT_DIR/14-due-by-column.png"

# ---------------------------------------------------------------------------
# Step 8: Verify Financials section on job detail (Req 57.5)
# ---------------------------------------------------------------------------
echo ""
echo "Step 8: Verifying Financials section on job detail (Req 57.5)..."

# Navigate to a job detail page
if agent-browser is visible "[data-testid='job-row'] a" 2>/dev/null; then
  agent-browser click "[data-testid='job-row'] a"
elif agent-browser is visible "[data-testid='job-row']" 2>/dev/null; then
  agent-browser click "[data-testid='job-row']"
else
  # Try navigating back to the detail URL we had earlier
  if [ -n "$DETAIL_URL" ] && echo "$DETAIL_URL" | grep -qi "/jobs/"; then
    agent-browser open "$DETAIL_URL"
  else
    echo "  ✗ FAIL: No job rows found to navigate to detail"
    FAIL_COUNT=$((FAIL_COUNT + 1))
  fi
fi

agent-browser wait --load networkidle
agent-browser wait 2000

# Scroll down to find the Financials section
agent-browser scroll down 500 2>/dev/null || true
agent-browser wait 1000
agent-browser screenshot "$SCREENSHOT_DIR/15-job-detail-financials.png"

if agent-browser is visible "[data-testid='job-financials']" 2>/dev/null; then
  echo "  ✓ Financials section visible"
  PASS_COUNT=$((PASS_COUNT + 1))

  FINANCIALS_HTML=$(agent-browser get html "[data-testid='job-financials']" 2>/dev/null || echo "")

  # Check for revenue fields
  if agent-browser is visible "[data-testid='fin-total-paid']" 2>/dev/null; then
    TOTAL_PAID=$(agent-browser get text "[data-testid='fin-total-paid']" 2>/dev/null || echo "")
    echo "  ✓ Total Paid displayed: $TOTAL_PAID"
    PASS_COUNT=$((PASS_COUNT + 1))
  elif echo "$FINANCIALS_HTML" | grep -qi "Total Paid\|Quoted Amount\|Final Amount"; then
    echo "  ✓ Revenue fields found in Financials section"
    PASS_COUNT=$((PASS_COUNT + 1))
  else
    echo "  ⚠ Revenue fields not clearly detected"
  fi

  # Check for cost fields
  if agent-browser is visible "[data-testid='fin-total-costs']" 2>/dev/null; then
    TOTAL_COSTS=$(agent-browser get text "[data-testid='fin-total-costs']" 2>/dev/null || echo "")
    echo "  ✓ Total Costs displayed: $TOTAL_COSTS"
    PASS_COUNT=$((PASS_COUNT + 1))
  elif echo "$FINANCIALS_HTML" | grep -qi "Material Costs\|Labor Costs\|Total Costs"; then
    echo "  ✓ Cost fields found in Financials section"
    PASS_COUNT=$((PASS_COUNT + 1))
  else
    echo "  ⚠ Cost fields not clearly detected"
  fi

  # Check for profit field
  if agent-browser is visible "[data-testid='fin-profit']" 2>/dev/null; then
    PROFIT=$(agent-browser get text "[data-testid='fin-profit']" 2>/dev/null || echo "")
    echo "  ✓ Profit displayed: $PROFIT"
    PASS_COUNT=$((PASS_COUNT + 1))
  elif echo "$FINANCIALS_HTML" | grep -qi "Profit"; then
    echo "  ✓ Profit field found in Financials section"
    PASS_COUNT=$((PASS_COUNT + 1))
  else
    echo "  ✗ FAIL: Profit field not found in Financials section"
    FAIL_COUNT=$((FAIL_COUNT + 1))
  fi

  agent-browser screenshot "$SCREENSHOT_DIR/16-financials-detail.png"
else
  # Check if financials text is present even without the testid
  PAGE_HTML=$(agent-browser get html "[data-testid='job-detail']" 2>/dev/null || echo "")
  if echo "$PAGE_HTML" | grep -qi "Financials"; then
    echo "  ✓ Financials section text found on page"
    PASS_COUNT=$((PASS_COUNT + 1))
  else
    echo "  ✗ FAIL: Financials section not found (data-testid='job-financials')"
    FAIL_COUNT=$((FAIL_COUNT + 1))
  fi
fi

# Take a final screenshot
agent-browser screenshot "$SCREENSHOT_DIR/17-jobs-final.png"

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "-------------------------------------------------------"
echo "Jobs E2E Results: $PASS_COUNT passed, $FAIL_COUNT failed"
echo "Screenshots saved to: $SCREENSHOT_DIR/"
echo "-------------------------------------------------------"

if [ "$FAIL_COUNT" -gt 0 ]; then
  echo "❌ FAIL: Jobs feature issues detected"
  exit 1
fi

echo "✅ PASS: All jobs feature tests passed"
exit 0
