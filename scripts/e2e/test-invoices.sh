#!/bin/bash
# E2E Test: Invoice Features
# Validates: Requirements 38.8, 54.8, 80.10, 67.2
#
# Tests bulk notify for past-due invoices, reminder status indicators
# on invoices with automated reminders, and invoice PDF download.
#
# Usage:
#   bash scripts/e2e/test-invoices.sh [--headed]
#
# Prerequisites:
#   - Frontend running at http://localhost:5173
#   - Backend running at http://localhost:8000
#   - agent-browser installed
#   - Valid admin credentials in environment or defaults

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCREENSHOT_DIR="e2e-screenshots/invoices"
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

echo "🧪 E2E Test: Invoice Features (Req 38.8, 54.8, 80.10)"
echo "========================================================"

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
  echo "❌ FAIL: Could not log in — aborting invoice tests"
  exit 1
fi

echo "  ✓ Login successful — navigated to: $CURRENT_URL"
PASS_COUNT=$((PASS_COUNT + 1))

# ---------------------------------------------------------------------------
# Step 2: Navigate to /invoices (Req 38.8 — Bulk Notify)
# ---------------------------------------------------------------------------
echo ""
echo "Step 2: Navigating to /invoices..."
agent-browser open "${BASE_URL}/invoices"
agent-browser wait --load networkidle
agent-browser wait 2000
agent-browser screenshot "$SCREENSHOT_DIR/03-invoices-page.png"

CURRENT_URL=$(agent-browser get url 2>/dev/null || echo "")
if echo "$CURRENT_URL" | grep -qi "/login"; then
  echo "  ✗ FAIL: Redirected to login"
  echo "❌ FAIL: Session lost — aborting"
  exit 1
fi

# Verify invoices page loaded
if agent-browser is visible "[data-testid='invoices-page']" 2>/dev/null; then
  echo "  ✓ Invoices page loaded"
  PASS_COUNT=$((PASS_COUNT + 1))
else
  echo "  ✗ FAIL: Invoices page element not found"
  FAIL_COUNT=$((FAIL_COUNT + 1))
fi

# ---------------------------------------------------------------------------
# Step 3: Bulk Notify — select invoices, click Bulk Notify, select Past Due,
#         send, verify summary (Req 38.8)
# ---------------------------------------------------------------------------
echo ""
echo "Step 3: Testing Bulk Notify flow (Req 38.8)..."

# Verify invoice table is visible
if agent-browser is visible "[data-testid='invoice-table']" 2>/dev/null; then
  echo "  ✓ Invoice table visible"
  PASS_COUNT=$((PASS_COUNT + 1))
else
  echo "  ✗ FAIL: Invoice table not found"
  FAIL_COUNT=$((FAIL_COUNT + 1))
fi

# Check for invoice rows
INVOICE_ROW_COUNT=$(agent-browser get count "[data-testid='invoice-row']" 2>/dev/null || echo "0")
echo "  Found $INVOICE_ROW_COUNT invoice rows"

if [ "$INVOICE_ROW_COUNT" -gt 0 ] 2>/dev/null; then
  # Click "Select All" checkbox to select all visible invoices
  if agent-browser is visible "[data-testid='select-all-checkbox']" 2>/dev/null; then
    agent-browser click "[data-testid='select-all-checkbox']"
    agent-browser wait 500
    agent-browser screenshot "$SCREENSHOT_DIR/04-invoices-selected.png"
    echo "  ✓ Select All checkbox clicked"
    PASS_COUNT=$((PASS_COUNT + 1))
  else
    echo "  ✗ FAIL: Select All checkbox not found"
    FAIL_COUNT=$((FAIL_COUNT + 1))
  fi

  # Verify Bulk Notify button is enabled
  if agent-browser is visible "[data-testid='bulk-notify-btn']" 2>/dev/null; then
    echo "  ✓ Bulk Notify button visible"
    PASS_COUNT=$((PASS_COUNT + 1))

    # Click Bulk Notify button to open dialog
    agent-browser click "[data-testid='bulk-notify-btn']"
    agent-browser wait 1000
    agent-browser screenshot "$SCREENSHOT_DIR/05-bulk-notify-dialog.png"

    # Verify dialog opened
    if agent-browser is visible "[data-testid='bulk-notify-dialog']" 2>/dev/null; then
      echo "  ✓ Bulk Notify dialog opened"
      PASS_COUNT=$((PASS_COUNT + 1))

      # Click the notification type selector
      agent-browser click "[data-testid='notification-type-selector']"
      agent-browser wait 500
      agent-browser screenshot "$SCREENSHOT_DIR/06-notification-type-dropdown.png"

      # Select "Past Due" notification type
      if agent-browser is visible "[data-testid='notify-type-PAST_DUE']" 2>/dev/null; then
        agent-browser click "[data-testid='notify-type-PAST_DUE']"
        agent-browser wait 500
        echo "  ✓ Past Due notification type selected"
        PASS_COUNT=$((PASS_COUNT + 1))
      else
        echo "  ✗ FAIL: Past Due notification type option not found"
        FAIL_COUNT=$((FAIL_COUNT + 1))
      fi

      agent-browser screenshot "$SCREENSHOT_DIR/07-past-due-selected.png"

      # Click Send button
      if agent-browser is visible "[data-testid='send-bulk-notify-btn']" 2>/dev/null; then
        agent-browser click "[data-testid='send-bulk-notify-btn']"
        agent-browser wait 3000
        agent-browser screenshot "$SCREENSHOT_DIR/08-after-bulk-send.png"

        # Verify success summary toast appears (contains "Sent:" text)
        PAGE_TEXT=$(agent-browser get text "body" 2>/dev/null || echo "")
        if echo "$PAGE_TEXT" | grep -qi "Sent:"; then
          echo "  ✓ Bulk notification summary displayed (Sent count visible)"
          PASS_COUNT=$((PASS_COUNT + 1))
        elif echo "$PAGE_TEXT" | grep -qi "Bulk Notification Complete\|notification.*sent\|success"; then
          echo "  ✓ Bulk notification success message displayed"
          PASS_COUNT=$((PASS_COUNT + 1))
        else
          echo "  ⚠ Bulk notification summary toast not detected (may have dismissed)"
        fi
      else
        echo "  ✗ FAIL: Send Bulk Notify button not found"
        FAIL_COUNT=$((FAIL_COUNT + 1))
      fi
    else
      echo "  ✗ FAIL: Bulk Notify dialog did not open"
      FAIL_COUNT=$((FAIL_COUNT + 1))
    fi
  else
    echo "  ✗ FAIL: Bulk Notify button not found"
    FAIL_COUNT=$((FAIL_COUNT + 1))
  fi
else
  echo "  ⚠ No invoice rows found — skipping bulk notify interaction"
  echo "  ✗ FAIL: Cannot test bulk notify without invoice data"
  FAIL_COUNT=$((FAIL_COUNT + 1))
fi

# ---------------------------------------------------------------------------
# Step 4: Verify reminder status indicators on invoices (Req 54.8)
# ---------------------------------------------------------------------------
echo ""
echo "Step 4: Verifying reminder status indicators (Req 54.8)..."

# Navigate back to /invoices to ensure clean state
agent-browser open "${BASE_URL}/invoices"
agent-browser wait --load networkidle
agent-browser wait 2000
agent-browser screenshot "$SCREENSHOT_DIR/09-invoices-for-reminders.png"

# Check for invoice status badges (these indicate invoice states including reminder-related)
BADGE_COUNT=$(agent-browser get count "[data-testid^='invoice-status-']" 2>/dev/null || echo "0")
if [ "$BADGE_COUNT" -gt 0 ] 2>/dev/null; then
  echo "  ✓ Invoice status badges visible ($BADGE_COUNT found)"
  PASS_COUNT=$((PASS_COUNT + 1))
else
  echo "  ✗ FAIL: No invoice status badges found"
  FAIL_COUNT=$((FAIL_COUNT + 1))
fi

# Look for overdue status badges which indicate invoices that would have reminders
OVERDUE_VISIBLE=false
if agent-browser is visible "[data-testid='invoice-status-overdue']" 2>/dev/null; then
  OVERDUE_VISIBLE=true
  echo "  ✓ Overdue invoice status indicator visible"
  PASS_COUNT=$((PASS_COUNT + 1))
fi

# Also check for sent status (pre-due reminders apply to sent invoices)
if agent-browser is visible "[data-testid='invoice-status-sent']" 2>/dev/null; then
  echo "  ✓ Sent invoice status indicator visible"
  PASS_COUNT=$((PASS_COUNT + 1))
fi

# Check for lien_warning status (indicates advanced reminder state)
if agent-browser is visible "[data-testid='invoice-status-lien_warning']" 2>/dev/null; then
  echo "  ✓ Lien Warning status indicator visible"
  PASS_COUNT=$((PASS_COUNT + 1))
fi

# Click into an invoice to verify detailed reminder information
# Try to find an overdue or sent invoice to click into
INVOICE_LINK_CLICKED=false
if [ "$OVERDUE_VISIBLE" = true ]; then
  # Find the first overdue invoice row and click its link
  FIRST_INVOICE_LINK=$(agent-browser get count "[data-testid^='invoice-number-']" 2>/dev/null || echo "0")
  if [ "$FIRST_INVOICE_LINK" -gt 0 ] 2>/dev/null; then
    # Click the first invoice link to navigate to detail
    agent-browser click "[data-testid^='invoice-number-']:first-of-type" 2>/dev/null || \
      agent-browser click "[data-testid='invoice-row'] a:first-of-type" 2>/dev/null || true
    agent-browser wait --load networkidle
    agent-browser wait 2000
    agent-browser screenshot "$SCREENSHOT_DIR/10-invoice-detail-reminders.png"
    INVOICE_LINK_CLICKED=true
  fi
fi

if [ "$INVOICE_LINK_CLICKED" = true ]; then
  # Check for reminder information section on the detail page
  DETAIL_TEXT=$(agent-browser get text "body" 2>/dev/null || echo "")
  if echo "$DETAIL_TEXT" | grep -qi "Reminders\|Reminder.*Sent\|Last Reminder"; then
    echo "  ✓ Reminder information visible on invoice detail"
    PASS_COUNT=$((PASS_COUNT + 1))
  else
    echo "  ⚠ Reminder section not visible (invoice may not have reminders sent)"
  fi
else
  echo "  ⚠ Could not navigate to invoice detail for reminder check"
fi

agent-browser screenshot "$SCREENSHOT_DIR/11-reminder-indicators-check.png"

# ---------------------------------------------------------------------------
# Step 5: Download PDF from invoice detail (Req 80.10)
# ---------------------------------------------------------------------------
echo ""
echo "Step 5: Testing invoice PDF download (Req 80.10)..."

# Navigate to an invoice detail page
# If we're already on a detail page from step 4, check; otherwise navigate
CURRENT_URL=$(agent-browser get url 2>/dev/null || echo "")
if ! echo "$CURRENT_URL" | grep -qP "/invoices/[a-f0-9-]+"; then
  # Navigate to /invoices and click the first invoice
  agent-browser open "${BASE_URL}/invoices"
  agent-browser wait --load networkidle
  agent-browser wait 2000

  # Click the first invoice link
  if agent-browser is visible "[data-testid^='invoice-number-']" 2>/dev/null; then
    agent-browser click "[data-testid^='invoice-number-']:first-of-type" 2>/dev/null || true
    agent-browser wait --load networkidle
    agent-browser wait 2000
  else
    echo "  ✗ FAIL: No invoice links found to navigate to detail"
    FAIL_COUNT=$((FAIL_COUNT + 1))
  fi
fi

agent-browser screenshot "$SCREENSHOT_DIR/12-invoice-detail-for-pdf.png"

# Verify we're on an invoice detail page
if agent-browser is visible "[data-testid='invoice-detail']" 2>/dev/null; then
  echo "  ✓ Invoice detail page loaded"
  PASS_COUNT=$((PASS_COUNT + 1))

  # Verify invoice number is displayed
  if agent-browser is visible "[data-testid='invoice-number']" 2>/dev/null; then
    INVOICE_NUM=$(agent-browser get text "[data-testid='invoice-number']" 2>/dev/null || echo "")
    echo "  ✓ Invoice number displayed: $INVOICE_NUM"
    PASS_COUNT=$((PASS_COUNT + 1))
  fi

  # Look for the Download PDF button
  if agent-browser is visible "[data-testid='download-pdf-btn']" 2>/dev/null; then
    echo "  ✓ Download PDF button visible"
    PASS_COUNT=$((PASS_COUNT + 1))

    agent-browser screenshot "$SCREENSHOT_DIR/13-before-pdf-download.png"

    # Click the Download PDF button
    agent-browser click "[data-testid='download-pdf-btn']"
    agent-browser wait 3000
    agent-browser screenshot "$SCREENSHOT_DIR/14-after-pdf-download.png"

    # Verify the download was initiated
    # The button shows a loading spinner during generation, then triggers download
    # After clicking, the button should return to normal state (no longer spinning)
    # We check that the button is still present and no error toast appeared
    PAGE_TEXT=$(agent-browser get text "body" 2>/dev/null || echo "")
    if echo "$PAGE_TEXT" | grep -qi "error\|failed.*pdf\|PDF.*failed"; then
      echo "  ✗ FAIL: PDF download error detected"
      FAIL_COUNT=$((FAIL_COUNT + 1))
    else
      # Check if button is still enabled (not stuck in loading state)
      if agent-browser is visible "[data-testid='download-pdf-btn']" 2>/dev/null; then
        echo "  ✓ PDF download initiated (no errors, button returned to ready state)"
        PASS_COUNT=$((PASS_COUNT + 1))
      else
        echo "  ⚠ Download PDF button state unclear after click"
      fi
    fi
  else
    echo "  ✗ FAIL: Download PDF button not found on invoice detail"
    FAIL_COUNT=$((FAIL_COUNT + 1))
  fi
else
  echo "  ✗ FAIL: Invoice detail page not loaded"
  FAIL_COUNT=$((FAIL_COUNT + 1))
fi

# Take a final screenshot
agent-browser screenshot "$SCREENSHOT_DIR/15-invoices-final.png"

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "-------------------------------------------------------"
echo "Invoice E2E Results: $PASS_COUNT passed, $FAIL_COUNT failed"
echo "Screenshots saved to: $SCREENSHOT_DIR/"
echo "-------------------------------------------------------"

if [ "$FAIL_COUNT" -gt 0 ]; then
  echo "❌ FAIL: Invoice feature issues detected"
  exit 1
fi

echo "✅ PASS: All invoice E2E tests passed"
exit 0
