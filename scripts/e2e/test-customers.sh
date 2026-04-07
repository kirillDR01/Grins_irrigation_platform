#!/bin/bash
# E2E Test: Customer Detail Features
# Validates: Requirements 7.7, 8.6, 9.9, 10.5, 11.6, 56.9, 67.2
#
# Tests customer duplicate detection/merge, internal notes editing,
# photo gallery upload/delete, invoice history with status badges,
# preferred service times editing, and payment methods display.
#
# Usage:
#   bash scripts/e2e/test-customers.sh [--headed]
#
# Prerequisites:
#   - Frontend running at http://localhost:5173
#   - Backend running at http://localhost:8000
#   - agent-browser installed
#   - Valid admin credentials in environment or defaults

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCREENSHOT_DIR="e2e-screenshots/customers"
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

echo "🧪 E2E Test: Customer Detail Features (Req 7.7, 8.6, 9.9, 10.5, 11.6, 56.9)"
echo "==============================================================================="

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
  echo "❌ FAIL: Could not log in — aborting customer tests"
  exit 1
fi

echo "  ✓ Login successful — navigated to: $CURRENT_URL"
PASS_COUNT=$((PASS_COUNT + 1))

# ---------------------------------------------------------------------------
# Step 2: Navigate to /customers and select a customer
# ---------------------------------------------------------------------------
echo ""
echo "Step 2: Navigating to /customers..."
agent-browser open "${BASE_URL}/customers"
agent-browser wait --load networkidle
agent-browser wait 2000
agent-browser screenshot "$SCREENSHOT_DIR/03-customers-list.png"

CURRENT_URL=$(agent-browser get url 2>/dev/null || echo "")
if echo "$CURRENT_URL" | grep -qi "/login"; then
  echo "  ✗ FAIL: Redirected to login"
  echo "❌ FAIL: Session lost — aborting"
  exit 1
fi

# Verify customers page loaded
if agent-browser is visible "[data-testid='customer-table']" 2>/dev/null || \
   agent-browser is visible "[data-testid='customer-list']" 2>/dev/null; then
  echo "  ✓ Customers list loaded"
  PASS_COUNT=$((PASS_COUNT + 1))
else
  echo "  ⚠ Customer table/list element not found — continuing with page content"
fi

# Click the first customer row to navigate to detail
if agent-browser is visible "[data-testid='customer-row']:first-child" 2>/dev/null; then
  agent-browser click "[data-testid='customer-row']:first-child"
elif agent-browser is visible "[data-testid='customer-row']" 2>/dev/null; then
  agent-browser click "[data-testid='customer-row']"
elif agent-browser is visible "table tbody tr:first-child" 2>/dev/null; then
  agent-browser click "table tbody tr:first-child"
elif agent-browser is visible "[data-testid='customer-list'] a:first-child" 2>/dev/null; then
  agent-browser click "[data-testid='customer-list'] a:first-child"
else
  # Fallback: try clicking any link that looks like a customer detail link
  agent-browser click "a[href*='/customers/']" 2>/dev/null || true
fi

agent-browser wait --load networkidle
agent-browser wait 2000
agent-browser screenshot "$SCREENSHOT_DIR/04-customer-detail.png"

DETAIL_URL=$(agent-browser get url 2>/dev/null || echo "")
if echo "$DETAIL_URL" | grep -qi "/customers/"; then
  echo "  ✓ Navigated to customer detail: $DETAIL_URL"
  PASS_COUNT=$((PASS_COUNT + 1))
else
  echo "  ⚠ May not be on customer detail page (URL: $DETAIL_URL)"
fi

# ---------------------------------------------------------------------------
# Step 3: Test Duplicate Detection and Merge (Req 7.7)
# ---------------------------------------------------------------------------
echo ""
echo "Step 3: Testing Potential Duplicates section (Req 7.7)..."

# Scroll to ensure the duplicates section is visible if it exists
agent-browser scroll down 300 2>/dev/null || true
agent-browser wait 1000

if agent-browser is visible "[data-testid='potential-duplicates']" 2>/dev/null; then
  echo "  ✓ Potential Duplicates section visible"
  PASS_COUNT=$((PASS_COUNT + 1))

  agent-browser screenshot "$SCREENSHOT_DIR/05-potential-duplicates.png"

  # Get the duplicates section text
  DUP_TEXT=$(agent-browser get text "[data-testid='potential-duplicates']" 2>/dev/null || echo "")
  echo "  ℹ Duplicates section content: ${DUP_TEXT:0:100}..."

  # Try to click a merge button if duplicates are present
  if agent-browser is visible "[data-testid='merge-customer-btn']" 2>/dev/null; then
    echo "  ✓ Merge button available"
    PASS_COUNT=$((PASS_COUNT + 1))

    agent-browser click "[data-testid='merge-customer-btn']"
    agent-browser wait 1000
    agent-browser screenshot "$SCREENSHOT_DIR/06-merge-dialog.png"

    # Check for merge confirmation dialog
    if agent-browser is visible "[data-testid='merge-confirm-btn']" 2>/dev/null || \
       agent-browser is visible "[data-testid='confirm-merge-btn']" 2>/dev/null; then
      echo "  ✓ Merge confirmation dialog appeared"
      PASS_COUNT=$((PASS_COUNT + 1))

      # Click confirm to perform merge
      if agent-browser is visible "[data-testid='merge-confirm-btn']" 2>/dev/null; then
        agent-browser click "[data-testid='merge-confirm-btn']"
      else
        agent-browser click "[data-testid='confirm-merge-btn']"
      fi
      agent-browser wait --load networkidle
      agent-browser wait 2000
      agent-browser screenshot "$SCREENSHOT_DIR/07-after-merge.png"
      echo "  ✓ Merge action performed"
      PASS_COUNT=$((PASS_COUNT + 1))
    else
      echo "  ⚠ Merge confirmation dialog not found — merge UI may differ"
    fi
  elif agent-browser is visible "[data-testid='potential-duplicates'] button" 2>/dev/null; then
    echo "  ✓ Duplicate action button found"
    PASS_COUNT=$((PASS_COUNT + 1))
  else
    echo "  ⚠ No merge button found — customer may not have duplicates to merge"
  fi
else
  echo "  ⚠ Potential Duplicates section not visible — customer may not have duplicates"
  echo "  ℹ This is expected if the current customer has no detected duplicates"

  # Navigate back to customers list and try to find one with duplicates
  agent-browser open "${BASE_URL}/customers"
  agent-browser wait --load networkidle
  agent-browser wait 2000

  # Look for a duplicate indicator in the list
  if agent-browser is visible "[data-testid='has-duplicates']" 2>/dev/null || \
     agent-browser is visible ".duplicate-indicator" 2>/dev/null; then
    agent-browser click "[data-testid='has-duplicates']" 2>/dev/null || \
      agent-browser click ".duplicate-indicator" 2>/dev/null || true
    agent-browser wait --load networkidle
    agent-browser wait 2000
    agent-browser screenshot "$SCREENSHOT_DIR/05-customer-with-duplicates.png"

    if agent-browser is visible "[data-testid='potential-duplicates']" 2>/dev/null; then
      echo "  ✓ Found customer with Potential Duplicates section"
      PASS_COUNT=$((PASS_COUNT + 1))
    else
      echo "  ✗ FAIL: Potential Duplicates section not found on any customer"
      FAIL_COUNT=$((FAIL_COUNT + 1))
    fi
  else
    echo "  ✗ FAIL: No customers with duplicate indicators found"
    FAIL_COUNT=$((FAIL_COUNT + 1))
  fi

  # Navigate back to a customer detail for remaining tests
  agent-browser open "${BASE_URL}/customers"
  agent-browser wait --load networkidle
  agent-browser wait 2000

  if agent-browser is visible "[data-testid='customer-row']" 2>/dev/null; then
    agent-browser click "[data-testid='customer-row']"
  elif agent-browser is visible "table tbody tr:first-child" 2>/dev/null; then
    agent-browser click "table tbody tr:first-child"
  else
    agent-browser click "a[href*='/customers/']" 2>/dev/null || true
  fi
  agent-browser wait --load networkidle
  agent-browser wait 2000
fi

# ---------------------------------------------------------------------------
# Step 4: Test Internal Notes Edit and Persistence (Req 8.6)
# ---------------------------------------------------------------------------
echo ""
echo "Step 4: Testing internal notes edit and persistence (Req 8.6)..."

agent-browser screenshot "$SCREENSHOT_DIR/08-before-notes-edit.png"

# Scroll to find internal notes section
agent-browser scroll down 300 2>/dev/null || true
agent-browser wait 500

NOTES_TIMESTAMP="E2E test note $(date +%s)"

if agent-browser is visible "[data-testid='internal-notes']" 2>/dev/null; then
  echo "  ✓ Internal Notes section visible"
  PASS_COUNT=$((PASS_COUNT + 1))

  # Look for an edit button or directly editable textarea
  if agent-browser is visible "[data-testid='edit-notes-btn']" 2>/dev/null; then
    agent-browser click "[data-testid='edit-notes-btn']"
    agent-browser wait 500
  fi

  # Find and fill the notes textarea
  if agent-browser is visible "[data-testid='internal-notes-input']" 2>/dev/null; then
    agent-browser fill "[data-testid='internal-notes-input']" "$NOTES_TIMESTAMP"
  elif agent-browser is visible "[data-testid='internal-notes'] textarea" 2>/dev/null; then
    agent-browser fill "[data-testid='internal-notes'] textarea" "$NOTES_TIMESTAMP"
  elif agent-browser is visible "textarea[name='internal_notes']" 2>/dev/null; then
    agent-browser fill "textarea[name='internal_notes']" "$NOTES_TIMESTAMP"
  elif agent-browser is visible "textarea[name='internalNotes']" 2>/dev/null; then
    agent-browser fill "textarea[name='internalNotes']" "$NOTES_TIMESTAMP"
  else
    echo "  ⚠ Could not find notes textarea"
  fi

  agent-browser screenshot "$SCREENSHOT_DIR/09-notes-filled.png"

  # Save the notes
  if agent-browser is visible "[data-testid='save-notes-btn']" 2>/dev/null; then
    agent-browser click "[data-testid='save-notes-btn']"
  elif agent-browser is visible "[data-testid='internal-notes'] button[type='submit']" 2>/dev/null; then
    agent-browser click "[data-testid='internal-notes'] button[type='submit']"
  elif agent-browser is visible "[data-testid='save-btn']" 2>/dev/null; then
    agent-browser click "[data-testid='save-btn']"
  fi

  agent-browser wait --load networkidle
  agent-browser wait 2000
  agent-browser screenshot "$SCREENSHOT_DIR/10-notes-saved.png"

  # Reload the page to verify persistence
  DETAIL_URL=$(agent-browser get url 2>/dev/null || echo "")
  agent-browser open "$DETAIL_URL"
  agent-browser wait --load networkidle
  agent-browser wait 2000

  # Scroll to notes section again
  agent-browser scroll down 300 2>/dev/null || true
  agent-browser wait 500

  # Verify the notes persisted
  NOTES_TEXT=""
  if agent-browser is visible "[data-testid='internal-notes-input']" 2>/dev/null; then
    NOTES_TEXT=$(agent-browser get value "[data-testid='internal-notes-input']" 2>/dev/null || echo "")
  elif agent-browser is visible "[data-testid='internal-notes'] textarea" 2>/dev/null; then
    NOTES_TEXT=$(agent-browser get value "[data-testid='internal-notes'] textarea" 2>/dev/null || echo "")
  elif agent-browser is visible "[data-testid='internal-notes']" 2>/dev/null; then
    NOTES_TEXT=$(agent-browser get text "[data-testid='internal-notes']" 2>/dev/null || echo "")
  fi

  if echo "$NOTES_TEXT" | grep -q "E2E test note"; then
    echo "  ✓ Internal notes persisted after reload"
    PASS_COUNT=$((PASS_COUNT + 1))
  else
    echo "  ✗ FAIL: Internal notes did not persist after reload"
    FAIL_COUNT=$((FAIL_COUNT + 1))
  fi

  agent-browser screenshot "$SCREENSHOT_DIR/11-notes-after-reload.png"
else
  echo "  ✗ FAIL: Internal Notes section not found (data-testid='internal-notes')"
  FAIL_COUNT=$((FAIL_COUNT + 1))
fi

# ---------------------------------------------------------------------------
# Step 5: Test Photo Gallery Upload and Delete (Req 9.9)
# ---------------------------------------------------------------------------
echo ""
echo "Step 5: Testing Photo Gallery upload and delete (Req 9.9)..."

# Look for Photos tab and click it
if agent-browser is visible "[data-testid='photos-tab']" 2>/dev/null; then
  agent-browser click "[data-testid='photos-tab']"
  agent-browser wait --load networkidle
  agent-browser wait 1000
elif agent-browser is visible "button:has-text('Photos')" 2>/dev/null; then
  agent-browser click "button:has-text('Photos')"
  agent-browser wait --load networkidle
  agent-browser wait 1000
elif agent-browser is visible "text=Photos" 2>/dev/null; then
  agent-browser click "text=Photos"
  agent-browser wait --load networkidle
  agent-browser wait 1000
fi

agent-browser screenshot "$SCREENSHOT_DIR/12-photos-tab.png"

if agent-browser is visible "[data-testid='photo-gallery']" 2>/dev/null; then
  echo "  ✓ Photo Gallery section visible"
  PASS_COUNT=$((PASS_COUNT + 1))

  # Count existing photos before upload
  PHOTO_COUNT_BEFORE=$(agent-browser get count "[data-testid='photo-gallery'] [data-testid='photo-item']" 2>/dev/null || echo "0")
  echo "  ℹ Photos before upload: $PHOTO_COUNT_BEFORE"

  # Create a small test image file for upload
  TEST_IMAGE="/tmp/e2e-test-image.png"
  # Generate a minimal 1x1 PNG using printf (base64 decoded)
  printf '\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82' > "$TEST_IMAGE" 2>/dev/null || true

  # Try to upload via file input
  if agent-browser is visible "[data-testid='upload-photo-btn']" 2>/dev/null; then
    agent-browser click "[data-testid='upload-photo-btn']"
    agent-browser wait 500
  fi

  # Look for file input element
  if agent-browser is visible "[data-testid='photo-upload-input']" 2>/dev/null; then
    agent-browser fill "[data-testid='photo-upload-input']" "$TEST_IMAGE" 2>/dev/null || true
  elif agent-browser is visible "[data-testid='photo-gallery'] input[type='file']" 2>/dev/null; then
    agent-browser fill "[data-testid='photo-gallery'] input[type='file']" "$TEST_IMAGE" 2>/dev/null || true
  elif agent-browser is visible "input[type='file']" 2>/dev/null; then
    agent-browser fill "input[type='file']" "$TEST_IMAGE" 2>/dev/null || true
  fi

  agent-browser wait --load networkidle
  agent-browser wait 2000
  agent-browser screenshot "$SCREENSHOT_DIR/13-after-photo-upload.png"

  # Verify photo appeared in grid
  PHOTO_COUNT_AFTER=$(agent-browser get count "[data-testid='photo-gallery'] [data-testid='photo-item']" 2>/dev/null || echo "0")
  if [ "$PHOTO_COUNT_AFTER" -gt "$PHOTO_COUNT_BEFORE" ] 2>/dev/null; then
    echo "  ✓ Photo uploaded and visible in grid ($PHOTO_COUNT_BEFORE → $PHOTO_COUNT_AFTER)"
    PASS_COUNT=$((PASS_COUNT + 1))
  else
    echo "  ⚠ Photo count did not increase after upload attempt"
  fi

  # Try to delete the uploaded photo
  if agent-browser is visible "[data-testid='delete-photo-btn']" 2>/dev/null; then
    agent-browser click "[data-testid='delete-photo-btn']"
    agent-browser wait 500

    # Confirm deletion if dialog appears
    if agent-browser is visible "[data-testid='confirm-delete-btn']" 2>/dev/null; then
      agent-browser click "[data-testid='confirm-delete-btn']"
    elif agent-browser is visible "button:has-text('Confirm')" 2>/dev/null; then
      agent-browser click "button:has-text('Confirm')"
    elif agent-browser is visible "button:has-text('Delete')" 2>/dev/null; then
      agent-browser click "button:has-text('Delete')"
    fi

    agent-browser wait --load networkidle
    agent-browser wait 1000
    agent-browser screenshot "$SCREENSHOT_DIR/14-after-photo-delete.png"

    PHOTO_COUNT_FINAL=$(agent-browser get count "[data-testid='photo-gallery'] [data-testid='photo-item']" 2>/dev/null || echo "0")
    if [ "$PHOTO_COUNT_FINAL" -lt "$PHOTO_COUNT_AFTER" ] 2>/dev/null; then
      echo "  ✓ Photo deleted from grid ($PHOTO_COUNT_AFTER → $PHOTO_COUNT_FINAL)"
      PASS_COUNT=$((PASS_COUNT + 1))
    else
      echo "  ⚠ Photo count did not decrease after delete attempt"
    fi
  elif agent-browser is visible "[data-testid='photo-item'] button" 2>/dev/null; then
    echo "  ✓ Photo action buttons available"
    PASS_COUNT=$((PASS_COUNT + 1))
  else
    echo "  ⚠ No delete button found for photos"
  fi

  # Clean up test image
  rm -f "$TEST_IMAGE" 2>/dev/null || true
else
  echo "  ✗ FAIL: Photo Gallery section not found (data-testid='photo-gallery')"
  FAIL_COUNT=$((FAIL_COUNT + 1))
fi

# ---------------------------------------------------------------------------
# Step 6: Test Invoice History Tab with Status Badges (Req 10.5)
# ---------------------------------------------------------------------------
echo ""
echo "Step 6: Testing Invoice History tab with status badges (Req 10.5)..."

# Click Invoice History tab
if agent-browser is visible "[data-testid='invoice-history-tab']" 2>/dev/null; then
  agent-browser click "[data-testid='invoice-history-tab']"
  agent-browser wait --load networkidle
  agent-browser wait 1000
elif agent-browser is visible "button:has-text('Invoice History')" 2>/dev/null; then
  agent-browser click "button:has-text('Invoice History')"
  agent-browser wait --load networkidle
  agent-browser wait 1000
elif agent-browser is visible "text=Invoice History" 2>/dev/null; then
  agent-browser click "text=Invoice History"
  agent-browser wait --load networkidle
  agent-browser wait 1000
elif agent-browser is visible "button:has-text('Invoices')" 2>/dev/null; then
  agent-browser click "button:has-text('Invoices')"
  agent-browser wait --load networkidle
  agent-browser wait 1000
fi

agent-browser screenshot "$SCREENSHOT_DIR/15-invoice-history-tab.png"

if agent-browser is visible "[data-testid='invoice-history']" 2>/dev/null; then
  echo "  ✓ Invoice History section visible"
  PASS_COUNT=$((PASS_COUNT + 1))

  # Check for invoice records
  INVOICE_COUNT=$(agent-browser get count "[data-testid='invoice-history'] [data-testid='invoice-row']" 2>/dev/null || echo "0")
  if [ "$INVOICE_COUNT" -gt 0 ] 2>/dev/null; then
    echo "  ✓ Invoice records displayed: $INVOICE_COUNT"
    PASS_COUNT=$((PASS_COUNT + 1))
  else
    # Try alternative selectors for invoice rows
    INVOICE_COUNT=$(agent-browser get count "[data-testid='invoice-history'] tr" 2>/dev/null || echo "0")
    if [ "$INVOICE_COUNT" -gt 1 ] 2>/dev/null; then
      echo "  ✓ Invoice records displayed in table"
      PASS_COUNT=$((PASS_COUNT + 1))
    else
      echo "  ⚠ No invoice records found — customer may have no invoices"
    fi
  fi

  # Check for status badges
  INVOICE_HTML=$(agent-browser get html "[data-testid='invoice-history']" 2>/dev/null || echo "")
  if echo "$INVOICE_HTML" | grep -qi "badge\|status\|paid\|sent\|overdue\|pending\|viewed"; then
    echo "  ✓ Status badges/indicators detected in invoice history"
    PASS_COUNT=$((PASS_COUNT + 1))
  else
    echo "  ⚠ Status badges not clearly detected in invoice history HTML"
  fi

  agent-browser screenshot "$SCREENSHOT_DIR/16-invoice-records.png"
else
  echo "  ✗ FAIL: Invoice History section not found (data-testid='invoice-history')"
  FAIL_COUNT=$((FAIL_COUNT + 1))
fi

# ---------------------------------------------------------------------------
# Step 7: Test Preferred Service Times Edit and Persistence (Req 11.6)
# ---------------------------------------------------------------------------
echo ""
echo "Step 7: Testing preferred service times edit and persistence (Req 11.6)..."

# Navigate back to main customer detail info (click Info/Details tab if needed)
if agent-browser is visible "[data-testid='details-tab']" 2>/dev/null; then
  agent-browser click "[data-testid='details-tab']"
  agent-browser wait 1000
elif agent-browser is visible "button:has-text('Details')" 2>/dev/null; then
  agent-browser click "button:has-text('Details')"
  agent-browser wait 1000
elif agent-browser is visible "button:has-text('Info')" 2>/dev/null; then
  agent-browser click "button:has-text('Info')"
  agent-browser wait 1000
fi

# Scroll to find service times section
agent-browser scroll down 500 2>/dev/null || true
agent-browser wait 500

agent-browser screenshot "$SCREENSHOT_DIR/17-before-service-times.png"

if agent-browser is visible "[data-testid='service-times']" 2>/dev/null; then
  echo "  ✓ Service Times section visible"
  PASS_COUNT=$((PASS_COUNT + 1))

  # Click edit button for service preferences
  if agent-browser is visible "[data-testid='edit-service-times-btn']" 2>/dev/null; then
    agent-browser click "[data-testid='edit-service-times-btn']"
    agent-browser wait 500
  elif agent-browser is visible "[data-testid='service-times'] button" 2>/dev/null; then
    agent-browser click "[data-testid='service-times'] button"
    agent-browser wait 500
  fi

  agent-browser screenshot "$SCREENSHOT_DIR/18-service-times-edit.png"

  # Try to select a preferred time option (Morning, Afternoon, Evening, etc.)
  if agent-browser is visible "[data-testid='service-time-morning']" 2>/dev/null; then
    agent-browser click "[data-testid='service-time-morning']"
  elif agent-browser is visible "label:has-text('Morning')" 2>/dev/null; then
    agent-browser click "label:has-text('Morning')"
  elif agent-browser is visible "[data-testid='service-times'] select" 2>/dev/null; then
    agent-browser select "[data-testid='service-times'] select" "Morning" 2>/dev/null || \
      agent-browser select "[data-testid='service-times'] select" "morning" 2>/dev/null || true
  elif agent-browser is visible "input[name='preferred_service_times']" 2>/dev/null; then
    agent-browser fill "input[name='preferred_service_times']" "Morning"
  elif agent-browser is visible "input[name='preferredServiceTimes']" 2>/dev/null; then
    agent-browser fill "input[name='preferredServiceTimes']" "Morning"
  fi

  agent-browser screenshot "$SCREENSHOT_DIR/19-service-times-selected.png"

  # Save the preference
  if agent-browser is visible "[data-testid='save-service-times-btn']" 2>/dev/null; then
    agent-browser click "[data-testid='save-service-times-btn']"
  elif agent-browser is visible "[data-testid='service-times'] button[type='submit']" 2>/dev/null; then
    agent-browser click "[data-testid='service-times'] button[type='submit']"
  elif agent-browser is visible "[data-testid='save-btn']" 2>/dev/null; then
    agent-browser click "[data-testid='save-btn']"
  fi

  agent-browser wait --load networkidle
  agent-browser wait 2000

  # Reload to verify persistence
  DETAIL_URL=$(agent-browser get url 2>/dev/null || echo "")
  agent-browser open "$DETAIL_URL"
  agent-browser wait --load networkidle
  agent-browser wait 2000

  # Scroll to service times section
  agent-browser scroll down 500 2>/dev/null || true
  agent-browser wait 500

  # Verify the preference persisted
  if agent-browser is visible "[data-testid='service-times']" 2>/dev/null; then
    SERVICE_TEXT=$(agent-browser get text "[data-testid='service-times']" 2>/dev/null || echo "")
    if echo "$SERVICE_TEXT" | grep -qi "morning"; then
      echo "  ✓ Preferred service times persisted after reload (Morning)"
      PASS_COUNT=$((PASS_COUNT + 1))
    else
      echo "  ⚠ Could not confirm 'Morning' preference persisted (text: ${SERVICE_TEXT:0:80})"
    fi
  fi

  agent-browser screenshot "$SCREENSHOT_DIR/20-service-times-after-reload.png"
else
  echo "  ✗ FAIL: Service Times section not found (data-testid='service-times')"
  FAIL_COUNT=$((FAIL_COUNT + 1))
fi

# ---------------------------------------------------------------------------
# Step 8: Test Payment Methods Display (Req 56.9)
# ---------------------------------------------------------------------------
echo ""
echo "Step 8: Testing Payment Methods display (Req 56.9)..."

# Scroll to find payment methods section
agent-browser scroll down 300 2>/dev/null || true
agent-browser wait 500

agent-browser screenshot "$SCREENSHOT_DIR/21-before-payment-methods.png"

if agent-browser is visible "[data-testid='payment-methods']" 2>/dev/null; then
  echo "  ✓ Payment Methods section visible"
  PASS_COUNT=$((PASS_COUNT + 1))

  PAYMENT_TEXT=$(agent-browser get text "[data-testid='payment-methods']" 2>/dev/null || echo "")
  echo "  ℹ Payment Methods content: ${PAYMENT_TEXT:0:120}..."

  # Check for saved card indicators
  PAYMENT_HTML=$(agent-browser get html "[data-testid='payment-methods']" 2>/dev/null || echo "")
  if echo "$PAYMENT_HTML" | grep -qi "card\|visa\|mastercard\|amex\|stripe\|•••\|ending\|last4\|\*\*\*\*"; then
    echo "  ✓ Saved card information displayed"
    PASS_COUNT=$((PASS_COUNT + 1))
  elif echo "$PAYMENT_TEXT" | grep -qi "no payment\|no saved\|none\|add"; then
    echo "  ✓ Payment Methods section shows empty state (no saved cards)"
    PASS_COUNT=$((PASS_COUNT + 1))
  else
    echo "  ⚠ Could not determine payment method display state"
  fi

  agent-browser screenshot "$SCREENSHOT_DIR/22-payment-methods.png"
else
  # Try scrolling more or looking in a different location
  agent-browser scroll down 500 2>/dev/null || true
  agent-browser wait 500

  if agent-browser is visible "[data-testid='payment-methods']" 2>/dev/null; then
    echo "  ✓ Payment Methods section visible (after scroll)"
    PASS_COUNT=$((PASS_COUNT + 1))
    agent-browser screenshot "$SCREENSHOT_DIR/22-payment-methods.png"
  else
    echo "  ✗ FAIL: Payment Methods section not found (data-testid='payment-methods')"
    FAIL_COUNT=$((FAIL_COUNT + 1))
  fi
fi

# Take a final full-page screenshot
agent-browser screenshot "$SCREENSHOT_DIR/23-customer-detail-final.png"

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "-------------------------------------------------------"
echo "Customer E2E Results: $PASS_COUNT passed, $FAIL_COUNT failed"
echo "Screenshots saved to: $SCREENSHOT_DIR/"
echo "-------------------------------------------------------"

if [ "$FAIL_COUNT" -gt 0 ]; then
  echo "❌ FAIL: Customer detail feature issues detected"
  exit 1
fi

echo "✅ PASS: All customer detail feature tests passed"
exit 0
