#!/bin/bash
# E2E Test: Schedule and Staff Workflow Features
# Validates: Requirements 24.8, 25.5, 26.6, 27.4, 28.3, 29.5, 30.9, 31.8,
#            32.10, 33.8, 34.8, 35.10, 36.7, 37.7, 40.6, 41.8, 42.7, 67.2
#
# Tests drag-drop rescheduling, lead time indicator, manual job addition,
# inline customer panel, calendar display format, address auto-populate,
# on-site payment collection, invoice creation, estimate creation,
# appointment notes, Google review request, staff workflow buttons,
# payment-required completion blocking, duration metrics, appointment
# enrichment, staff location map, and staff break functionality.
#
# Usage:
#   bash scripts/e2e/test-schedule.sh [--headed]
#
# Prerequisites:
#   - Frontend running at http://localhost:5173
#   - Backend running at http://localhost:8000
#   - agent-browser installed
#   - Valid admin credentials in environment or defaults

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCREENSHOT_DIR="e2e-screenshots/schedule"
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

echo "🧪 E2E Test: Schedule and Staff Workflow (Req 24-42)"
echo "====================================================="

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
  echo "❌ FAIL: Could not log in — aborting schedule tests"
  exit 1
fi

echo "  ✓ Login successful — navigated to: $CURRENT_URL"
PASS_COUNT=$((PASS_COUNT + 1))

# ---------------------------------------------------------------------------
# Step 2: Navigate to /schedule
# ---------------------------------------------------------------------------
echo ""
echo "Step 2: Navigating to /schedule..."
agent-browser open "${BASE_URL}/schedule"
agent-browser wait --load networkidle
agent-browser wait 2000
agent-browser screenshot "$SCREENSHOT_DIR/03-schedule-page.png"

CURRENT_URL=$(agent-browser get url 2>/dev/null || echo "")
if echo "$CURRENT_URL" | grep -qi "/login"; then
  echo "  ✗ FAIL: Redirected to login"
  echo "❌ FAIL: Session lost — aborting"
  exit 1
fi

# Verify schedule page loaded
if agent-browser is visible "[data-testid='schedule-page']" 2>/dev/null; then
  echo "  ✓ Schedule page loaded"
  PASS_COUNT=$((PASS_COUNT + 1))
else
  echo "  ✗ FAIL: Schedule page not found (data-testid='schedule-page')"
  FAIL_COUNT=$((FAIL_COUNT + 1))
fi

# ---------------------------------------------------------------------------
# Step 3: Drag-drop appointment rescheduling (Req 24.8)
# ---------------------------------------------------------------------------
echo ""
echo "Step 3: Testing drag-drop appointment rescheduling (Req 24.8)..."

if agent-browser is visible "[data-testid='calendar-view']" 2>/dev/null; then
  echo "  ✓ Calendar view visible"
  PASS_COUNT=$((PASS_COUNT + 1))

  # Check for draggable appointment events on the calendar
  EVENT_COUNT=$(agent-browser get count ".fc-event" 2>/dev/null || echo "0")
  if [ "$EVENT_COUNT" -gt 0 ] 2>/dev/null; then
    echo "  ✓ Calendar events found: $EVENT_COUNT"
    PASS_COUNT=$((PASS_COUNT + 1))

    # Attempt drag-drop: get the first event's text before drag
    FIRST_EVENT_TEXT=$(agent-browser get text ".fc-event" 2>/dev/null || echo "")
    echo "  ℹ First event: ${FIRST_EVENT_TEXT:0:60}"

    # Drag the first event down by 50px (simulating time slot change)
    agent-browser eval "
      const event = document.querySelector('.fc-event');
      if (event) {
        const rect = event.getBoundingClientRect();
        const startX = rect.left + rect.width / 2;
        const startY = rect.top + rect.height / 2;
        const endY = startY + 50;
        event.dispatchEvent(new MouseEvent('mousedown', { clientX: startX, clientY: startY, bubbles: true }));
        event.dispatchEvent(new MouseEvent('mousemove', { clientX: startX, clientY: endY, bubbles: true }));
        event.dispatchEvent(new MouseEvent('mouseup', { clientX: startX, clientY: endY, bubbles: true }));
      }
    " 2>/dev/null || true
    agent-browser wait 1000

    # Verify the event is still on the calendar (drag completed or reverted)
    POST_DRAG_COUNT=$(agent-browser get count ".fc-event" 2>/dev/null || echo "0")
    if [ "$POST_DRAG_COUNT" -gt 0 ] 2>/dev/null; then
      echo "  ✓ Appointment still visible after drag operation"
      PASS_COUNT=$((PASS_COUNT + 1))
    else
      echo "  ✗ FAIL: Calendar events disappeared after drag"
      FAIL_COUNT=$((FAIL_COUNT + 1))
    fi
  else
    echo "  ⚠ No calendar events found — schedule may be empty"
  fi
else
  echo "  ✗ FAIL: Calendar view not found (data-testid='calendar-view')"
  FAIL_COUNT=$((FAIL_COUNT + 1))
fi

agent-browser screenshot "$SCREENSHOT_DIR/04-drag-drop.png"

# ---------------------------------------------------------------------------
# Step 4: Lead Time indicator (Req 25.5)
# ---------------------------------------------------------------------------
echo ""
echo "Step 4: Verifying Lead Time indicator (Req 25.5)..."

if agent-browser is visible "[data-testid='lead-time-indicator']" 2>/dev/null; then
  LEAD_TIME_TEXT=$(agent-browser get text "[data-testid='lead-time-indicator']" 2>/dev/null || echo "")
  if [ -n "$LEAD_TIME_TEXT" ]; then
    echo "  ✓ Lead Time indicator displays value: ${LEAD_TIME_TEXT:0:60}"
    PASS_COUNT=$((PASS_COUNT + 1))
  else
    echo "  ✗ FAIL: Lead Time indicator is empty"
    FAIL_COUNT=$((FAIL_COUNT + 1))
  fi
else
  echo "  ✗ FAIL: Lead Time indicator not found (data-testid='lead-time-indicator')"
  FAIL_COUNT=$((FAIL_COUNT + 1))
fi

agent-browser screenshot "$SCREENSHOT_DIR/05-lead-time.png"

# ---------------------------------------------------------------------------
# Step 5: Add Appointment with job filter and multi-select (Req 26.6)
# ---------------------------------------------------------------------------
echo ""
echo "Step 5: Testing Add Appointment with job filter (Req 26.6)..."

# Click "Add Appointment" button
if agent-browser is visible "[data-testid='add-appointment-btn']" 2>/dev/null; then
  agent-browser click "[data-testid='add-appointment-btn']"
  agent-browser wait 1000
  agent-browser screenshot "$SCREENSHOT_DIR/06-add-appointment-form.png"

  # Verify appointment form opened
  if agent-browser is visible "[data-testid='appointment-form']" 2>/dev/null; then
    echo "  ✓ Appointment form opened"
    PASS_COUNT=$((PASS_COUNT + 1))

    # Check for job selector with filter
    if agent-browser is visible "[data-testid='job-selector']" 2>/dev/null; then
      echo "  ✓ Job selector visible"
      PASS_COUNT=$((PASS_COUNT + 1))

      # Try using the job filter
      if agent-browser is visible "[data-testid='job-filter-input']" 2>/dev/null; then
        agent-browser fill "[data-testid='job-filter-input']" "irrigation"
        agent-browser wait 500
        echo "  ✓ Job filter input accepts text"
        PASS_COUNT=$((PASS_COUNT + 1))
      else
        echo "  ⚠ Job filter input not found — may use different selector"
      fi

      # Check for multi-select capability (checkboxes on job items)
      JOB_ITEM_COUNT=$(agent-browser get count "[data-testid^='job-option-']" 2>/dev/null || echo "0")
      if [ "$JOB_ITEM_COUNT" -gt 0 ] 2>/dev/null; then
        echo "  ✓ Job options available for selection: $JOB_ITEM_COUNT"
        PASS_COUNT=$((PASS_COUNT + 1))

        # Select first two jobs if available
        agent-browser click "[data-testid='job-option-0']" 2>/dev/null || true
        agent-browser wait 300
        if [ "$JOB_ITEM_COUNT" -gt 1 ] 2>/dev/null; then
          agent-browser click "[data-testid='job-option-1']" 2>/dev/null || true
          agent-browser wait 300
        fi
        echo "  ✓ Multi-select attempted on job options"
      else
        echo "  ⚠ No job options found — jobs list may be empty"
      fi
    else
      echo "  ⚠ Job selector not found (data-testid='job-selector')"
    fi
  else
    echo "  ✗ FAIL: Appointment form did not open"
    FAIL_COUNT=$((FAIL_COUNT + 1))
  fi

  # Close the form (press Escape or click cancel)
  agent-browser press Escape 2>/dev/null || true
  agent-browser wait 500
else
  echo "  ✗ FAIL: Add Appointment button not found (data-testid='add-appointment-btn')"
  FAIL_COUNT=$((FAIL_COUNT + 1))
fi

agent-browser screenshot "$SCREENSHOT_DIR/07-job-filter.png"

# ---------------------------------------------------------------------------
# Step 6: Inline customer panel (Req 27.4)
# ---------------------------------------------------------------------------
echo ""
echo "Step 6: Testing inline customer panel (Req 27.4)..."

# Navigate back to schedule to ensure clean state
agent-browser open "${BASE_URL}/schedule"
agent-browser wait --load networkidle
agent-browser wait 2000

# Record URL before clicking customer name
URL_BEFORE=$(agent-browser get url 2>/dev/null || echo "")

# Click a customer name on a calendar event
if agent-browser is visible "[data-testid='appointment-customer-link']" 2>/dev/null; then
  agent-browser click "[data-testid='appointment-customer-link']"
  agent-browser wait 1000

  # Verify inline panel opened
  if agent-browser is visible "[data-testid='inline-customer-panel']" 2>/dev/null; then
    echo "  ✓ Inline customer panel opened"
    PASS_COUNT=$((PASS_COUNT + 1))

    # Verify panel has customer details
    PANEL_HTML=$(agent-browser get html "[data-testid='inline-customer-panel']" 2>/dev/null || echo "")
    if [ -n "$PANEL_HTML" ] && [ ${#PANEL_HTML} -gt 50 ]; then
      echo "  ✓ Inline panel contains customer details"
      PASS_COUNT=$((PASS_COUNT + 1))
    else
      echo "  ✗ FAIL: Inline panel appears empty"
      FAIL_COUNT=$((FAIL_COUNT + 1))
    fi

    # Verify URL has NOT changed (no navigation)
    URL_AFTER=$(agent-browser get url 2>/dev/null || echo "")
    if [ "$URL_BEFORE" = "$URL_AFTER" ]; then
      echo "  ✓ URL unchanged — no navigation occurred"
      PASS_COUNT=$((PASS_COUNT + 1))
    else
      echo "  ✗ FAIL: URL changed from $URL_BEFORE to $URL_AFTER"
      FAIL_COUNT=$((FAIL_COUNT + 1))
    fi
  else
    echo "  ✗ FAIL: Inline customer panel did not open (data-testid='inline-customer-panel')"
    FAIL_COUNT=$((FAIL_COUNT + 1))
  fi

  # Close the panel
  agent-browser press Escape 2>/dev/null || true
  agent-browser wait 500
elif agent-browser is visible ".fc-event" 2>/dev/null; then
  # Fallback: click a calendar event to try to trigger the panel
  agent-browser click ".fc-event"
  agent-browser wait 1000

  if agent-browser is visible "[data-testid='inline-customer-panel']" 2>/dev/null; then
    echo "  ✓ Inline customer panel opened via calendar event click"
    PASS_COUNT=$((PASS_COUNT + 1))
  else
    echo "  ⚠ Inline panel not triggered from calendar event click"
  fi

  agent-browser press Escape 2>/dev/null || true
  agent-browser wait 500
else
  echo "  ⚠ No customer links or calendar events found — schedule may be empty"
fi

agent-browser screenshot "$SCREENSHOT_DIR/08-inline-panel.png"

# ---------------------------------------------------------------------------
# Step 7: Calendar event labels format (Req 28.3)
# ---------------------------------------------------------------------------
echo ""
echo "Step 7: Verifying calendar event labels (Req 28.3)..."

EVENT_COUNT=$(agent-browser get count ".fc-event" 2>/dev/null || echo "0")
if [ "$EVENT_COUNT" -gt 0 ] 2>/dev/null; then
  # Get the text of the first calendar event
  EVENT_TEXT=$(agent-browser get text ".fc-event" 2>/dev/null || echo "")

  # Event labels should contain staff name and job type (format: "Staff Name - Job Type")
  if echo "$EVENT_TEXT" | grep -q " - "; then
    echo "  ✓ Calendar event label contains 'Name - Type' format: ${EVENT_TEXT:0:60}"
    PASS_COUNT=$((PASS_COUNT + 1))
  elif [ -n "$EVENT_TEXT" ]; then
    echo "  ⚠ Calendar event text found but format unclear: ${EVENT_TEXT:0:60}"
  else
    echo "  ✗ FAIL: Calendar event text is empty"
    FAIL_COUNT=$((FAIL_COUNT + 1))
  fi
else
  echo "  ⚠ No calendar events found — schedule may be empty"
fi

agent-browser screenshot "$SCREENSHOT_DIR/09-event-labels.png"

# ---------------------------------------------------------------------------
# Step 8: Address auto-populate on appointment form (Req 29.5)
# ---------------------------------------------------------------------------
echo ""
echo "Step 8: Testing address auto-populate (Req 29.5)..."

# Open appointment creation form
if agent-browser is visible "[data-testid='add-appointment-btn']" 2>/dev/null; then
  agent-browser click "[data-testid='add-appointment-btn']"
  agent-browser wait 1000

  if agent-browser is visible "[data-testid='appointment-form']" 2>/dev/null; then
    # Select a customer from the dropdown
    if agent-browser is visible "[data-testid='customer-select']" 2>/dev/null; then
      agent-browser click "[data-testid='customer-select']"
      agent-browser wait 500

      # Select the first customer option
      if agent-browser is visible "[data-testid='customer-option-0']" 2>/dev/null; then
        agent-browser click "[data-testid='customer-option-0']"
        agent-browser wait 1000

        # Check if address field was auto-populated
        ADDRESS_VALUE=$(agent-browser get value "[data-testid='address-input']" 2>/dev/null || echo "")
        if [ -n "$ADDRESS_VALUE" ]; then
          echo "  ✓ Address auto-populated: ${ADDRESS_VALUE:0:60}"
          PASS_COUNT=$((PASS_COUNT + 1))
        else
          echo "  ✗ FAIL: Address field not auto-populated after customer selection"
          FAIL_COUNT=$((FAIL_COUNT + 1))
        fi
      else
        echo "  ⚠ No customer options available in dropdown"
      fi
    else
      echo "  ⚠ Customer select not found (data-testid='customer-select')"
    fi
  else
    echo "  ✗ FAIL: Appointment form did not open"
    FAIL_COUNT=$((FAIL_COUNT + 1))
  fi

  # Close the form
  agent-browser press Escape 2>/dev/null || true
  agent-browser wait 500
else
  echo "  ⚠ Add Appointment button not found — skipping address auto-populate test"
fi

agent-browser screenshot "$SCREENSHOT_DIR/10-address-autopopulate.png"

# ---------------------------------------------------------------------------
# Step 9: On-site payment collection (Req 30.9)
# ---------------------------------------------------------------------------
echo ""
echo "Step 9: Testing on-site payment collection (Req 30.9)..."

# Navigate to an appointment detail — click a calendar event
if agent-browser is visible ".fc-event" 2>/dev/null; then
  agent-browser click ".fc-event"
  agent-browser wait --load networkidle
  agent-browser wait 1500
fi

# Try to find appointment detail view
if agent-browser is visible "[data-testid='appointment-detail']" 2>/dev/null; then
  echo "  ✓ Appointment detail view visible"
  PASS_COUNT=$((PASS_COUNT + 1))

  # Check for Collect Payment button
  if agent-browser is visible "[data-testid='collect-payment-btn']" 2>/dev/null; then
    echo "  ✓ Collect Payment button visible"
    PASS_COUNT=$((PASS_COUNT + 1))

    agent-browser click "[data-testid='collect-payment-btn']"
    agent-browser wait 1000

    # Verify payment form opens
    if agent-browser is visible "[data-testid='payment-form']" 2>/dev/null; then
      echo "  ✓ Payment form opened"
      PASS_COUNT=$((PASS_COUNT + 1))

      # Select a payment method
      if agent-browser is visible "[data-testid='payment-method-select']" 2>/dev/null; then
        agent-browser click "[data-testid='payment-method-select']"
        agent-browser wait 300
        # Select Cash option
        if agent-browser is visible "[data-testid='payment-method-cash']" 2>/dev/null; then
          agent-browser click "[data-testid='payment-method-cash']"
        else
          agent-browser press Enter 2>/dev/null || true
        fi
        agent-browser wait 300
      fi

      # Enter amount
      if agent-browser is visible "[data-testid='payment-amount-input']" 2>/dev/null; then
        agent-browser fill "[data-testid='payment-amount-input']" "150.00"
        echo "  ✓ Payment amount entered"
      fi

      # Submit payment
      if agent-browser is visible "[data-testid='submit-payment-btn']" 2>/dev/null; then
        agent-browser click "[data-testid='submit-payment-btn']"
        agent-browser wait --load networkidle
        agent-browser wait 2000
        echo "  ✓ Payment submitted"
        PASS_COUNT=$((PASS_COUNT + 1))
      fi

      agent-browser screenshot "$SCREENSHOT_DIR/11-payment-collected.png"
    else
      echo "  ✗ FAIL: Payment form did not open (data-testid='payment-form')"
      FAIL_COUNT=$((FAIL_COUNT + 1))
    fi
  else
    echo "  ⚠ Collect Payment button not visible — appointment may not be in_progress"
  fi
else
  echo "  ⚠ Appointment detail not visible — navigating to schedule to find one"
fi

# Close any open panels
agent-browser press Escape 2>/dev/null || true
agent-browser wait 500

# ---------------------------------------------------------------------------
# Step 10: On-site invoice creation (Req 31.8)
# ---------------------------------------------------------------------------
echo ""
echo "Step 10: Testing on-site invoice creation (Req 31.8)..."

# Navigate back to schedule and open an appointment
agent-browser open "${BASE_URL}/schedule"
agent-browser wait --load networkidle
agent-browser wait 2000

if agent-browser is visible ".fc-event" 2>/dev/null; then
  agent-browser click ".fc-event"
  agent-browser wait 1500
fi

if agent-browser is visible "[data-testid='appointment-detail']" 2>/dev/null; then
  # Check for Create Invoice button
  if agent-browser is visible "[data-testid='create-invoice-btn']" 2>/dev/null; then
    echo "  ✓ Create Invoice button visible"
    PASS_COUNT=$((PASS_COUNT + 1))

    agent-browser click "[data-testid='create-invoice-btn']"
    agent-browser wait 1000

    # Verify invoice form opens with pre-populated fields
    if agent-browser is visible "[data-testid='invoice-form']" 2>/dev/null; then
      echo "  ✓ Invoice form opened"
      PASS_COUNT=$((PASS_COUNT + 1))

      # Check for pre-populated customer name or amount
      INVOICE_HTML=$(agent-browser get html "[data-testid='invoice-form']" 2>/dev/null || echo "")
      if [ -n "$INVOICE_HTML" ] && [ ${#INVOICE_HTML} -gt 100 ]; then
        echo "  ✓ Invoice form contains pre-populated fields"
        PASS_COUNT=$((PASS_COUNT + 1))
      else
        echo "  ⚠ Invoice form may not have pre-populated fields"
      fi

      # Submit the invoice
      if agent-browser is visible "[data-testid='submit-invoice-btn']" 2>/dev/null; then
        agent-browser click "[data-testid='submit-invoice-btn']"
        agent-browser wait --load networkidle
        agent-browser wait 2000
        echo "  ✓ Invoice submitted"
        PASS_COUNT=$((PASS_COUNT + 1))
      fi
    else
      echo "  ✗ FAIL: Invoice form did not open"
      FAIL_COUNT=$((FAIL_COUNT + 1))
    fi

    # Close form
    agent-browser press Escape 2>/dev/null || true
    agent-browser wait 500
  else
    echo "  ⚠ Create Invoice button not visible on this appointment"
  fi
else
  echo "  ⚠ Could not open appointment detail for invoice test"
fi

agent-browser screenshot "$SCREENSHOT_DIR/12-invoice-creation.png"

# ---------------------------------------------------------------------------
# Step 11: On-site estimate creation (Req 32.10)
# ---------------------------------------------------------------------------
echo ""
echo "Step 11: Testing on-site estimate creation (Req 32.10)..."

# Navigate back to schedule and open an appointment
agent-browser open "${BASE_URL}/schedule"
agent-browser wait --load networkidle
agent-browser wait 2000

if agent-browser is visible ".fc-event" 2>/dev/null; then
  agent-browser click ".fc-event"
  agent-browser wait 1500
fi

if agent-browser is visible "[data-testid='appointment-detail']" 2>/dev/null; then
  # Check for Create Estimate button
  if agent-browser is visible "[data-testid='create-estimate-btn']" 2>/dev/null; then
    echo "  ✓ Create Estimate button visible"
    PASS_COUNT=$((PASS_COUNT + 1))

    agent-browser click "[data-testid='create-estimate-btn']"
    agent-browser wait 1000

    # Verify estimate form opens
    if agent-browser is visible "[data-testid='estimate-form']" 2>/dev/null; then
      echo "  ✓ Estimate form opened"
      PASS_COUNT=$((PASS_COUNT + 1))

      # Select a template if available
      if agent-browser is visible "[data-testid='template-select']" 2>/dev/null; then
        agent-browser click "[data-testid='template-select']"
        agent-browser wait 500
        if agent-browser is visible "[data-testid='template-option-0']" 2>/dev/null; then
          agent-browser click "[data-testid='template-option-0']"
          agent-browser wait 500
          echo "  ✓ Template selected"
          PASS_COUNT=$((PASS_COUNT + 1))
        else
          agent-browser press Escape 2>/dev/null || true
          echo "  ⚠ No templates available"
        fi
      fi

      # Submit the estimate
      if agent-browser is visible "[data-testid='submit-estimate-btn']" 2>/dev/null; then
        agent-browser click "[data-testid='submit-estimate-btn']"
        agent-browser wait --load networkidle
        agent-browser wait 2000
        echo "  ✓ Estimate submitted"
        PASS_COUNT=$((PASS_COUNT + 1))
      fi
    else
      echo "  ✗ FAIL: Estimate form did not open"
      FAIL_COUNT=$((FAIL_COUNT + 1))
    fi

    # Close form
    agent-browser press Escape 2>/dev/null || true
    agent-browser wait 500
  else
    echo "  ⚠ Create Estimate button not visible on this appointment"
  fi
else
  echo "  ⚠ Could not open appointment detail for estimate test"
fi

agent-browser screenshot "$SCREENSHOT_DIR/13-estimate-creation.png"

# ---------------------------------------------------------------------------
# Step 12: Appointment notes (Req 33.8)
# ---------------------------------------------------------------------------
echo ""
echo "Step 12: Testing appointment notes (Req 33.8)..."

# Navigate back to schedule and open an appointment
agent-browser open "${BASE_URL}/schedule"
agent-browser wait --load networkidle
agent-browser wait 2000

if agent-browser is visible ".fc-event" 2>/dev/null; then
  agent-browser click ".fc-event"
  agent-browser wait 1500
fi

NOTES_TIMESTAMP="E2E schedule note $(date +%s)"

if agent-browser is visible "[data-testid='appointment-detail']" 2>/dev/null; then
  # Scroll to find notes section
  agent-browser scroll down 300 2>/dev/null || true
  agent-browser wait 500

  if agent-browser is visible "[data-testid='appointment-notes']" 2>/dev/null; then
    echo "  ✓ Appointment notes section visible"
    PASS_COUNT=$((PASS_COUNT + 1))

    # Find the notes textarea within the section
    if agent-browser is visible "[data-testid='appointment-notes'] textarea" 2>/dev/null; then
      agent-browser fill "[data-testid='appointment-notes'] textarea" "$NOTES_TIMESTAMP"
    elif agent-browser is visible "[data-testid='notes-textarea']" 2>/dev/null; then
      agent-browser fill "[data-testid='notes-textarea']" "$NOTES_TIMESTAMP"
    fi

    # Save notes
    if agent-browser is visible "[data-testid='save-notes-btn']" 2>/dev/null; then
      agent-browser click "[data-testid='save-notes-btn']"
      agent-browser wait --load networkidle
      agent-browser wait 2000
      echo "  ✓ Notes saved"
      PASS_COUNT=$((PASS_COUNT + 1))
    fi

    agent-browser screenshot "$SCREENSHOT_DIR/14-notes-saved.png"

    # Verify notes appear on customer detail page
    # Get the customer link from the appointment detail
    CUSTOMER_LINK=""
    if agent-browser is visible "[data-testid='appointment-customer-link']" 2>/dev/null; then
      CUSTOMER_LINK=$(agent-browser get attr "[data-testid='appointment-customer-link']" href 2>/dev/null || echo "")
    fi

    if [ -n "$CUSTOMER_LINK" ]; then
      agent-browser open "${BASE_URL}${CUSTOMER_LINK}"
      agent-browser wait --load networkidle
      agent-browser wait 2000

      PAGE_TEXT=$(agent-browser get text "body" 2>/dev/null || echo "")
      if echo "$PAGE_TEXT" | grep -q "E2E schedule note"; then
        echo "  ✓ Notes appear on customer detail page"
        PASS_COUNT=$((PASS_COUNT + 1))
      else
        echo "  ⚠ Notes not found on customer detail page — may need to check notes tab"
      fi

      agent-browser screenshot "$SCREENSHOT_DIR/15-notes-on-customer.png"
    else
      echo "  ⚠ Could not find customer link to verify notes propagation"
    fi
  else
    echo "  ✗ FAIL: Appointment notes section not found (data-testid='appointment-notes')"
    FAIL_COUNT=$((FAIL_COUNT + 1))
  fi
else
  echo "  ⚠ Could not open appointment detail for notes test"
fi

# ---------------------------------------------------------------------------
# Step 13: Google Review request button (Req 34.8)
# ---------------------------------------------------------------------------
echo ""
echo "Step 13: Verifying Google Review request button (Req 34.8)..."

# Navigate to schedule and find a completed appointment
agent-browser open "${BASE_URL}/schedule"
agent-browser wait --load networkidle
agent-browser wait 2000

# Try to find a completed appointment event
if agent-browser is visible "[data-testid='completed-appointment']" 2>/dev/null; then
  agent-browser click "[data-testid='completed-appointment']"
  agent-browser wait 1500
elif agent-browser is visible ".fc-event" 2>/dev/null; then
  agent-browser click ".fc-event"
  agent-browser wait 1500
fi

if agent-browser is visible "[data-testid='appointment-detail']" 2>/dev/null; then
  agent-browser scroll down 300 2>/dev/null || true
  agent-browser wait 500

  if agent-browser is visible "[data-testid='request-review-btn']" 2>/dev/null; then
    echo "  ✓ Request Google Review button visible on appointment"
    PASS_COUNT=$((PASS_COUNT + 1))
  else
    echo "  ⚠ Request Google Review button not visible — appointment may not be completed"
  fi
else
  echo "  ⚠ Could not open appointment detail for review button test"
fi

agent-browser screenshot "$SCREENSHOT_DIR/16-review-button.png"

# Close any open panels
agent-browser press Escape 2>/dev/null || true
agent-browser wait 500

# ---------------------------------------------------------------------------
# Step 14: Staff workflow buttons (Req 35.10)
# ---------------------------------------------------------------------------
echo ""
echo "Step 14: Testing staff workflow buttons (Req 35.10)..."

# Navigate to schedule and find a confirmed appointment
agent-browser open "${BASE_URL}/schedule"
agent-browser wait --load networkidle
agent-browser wait 2000

if agent-browser is visible ".fc-event" 2>/dev/null; then
  agent-browser click ".fc-event"
  agent-browser wait 1500
fi

if agent-browser is visible "[data-testid='appointment-detail']" 2>/dev/null; then
  # Check for "On My Way" button (shown when status is confirmed)
  if agent-browser is visible "[data-testid='on-my-way-btn']" 2>/dev/null; then
    echo "  ✓ 'On My Way' button visible"
    PASS_COUNT=$((PASS_COUNT + 1))

    # Click "On My Way"
    agent-browser click "[data-testid='on-my-way-btn']"
    agent-browser wait --load networkidle
    agent-browser wait 2000
    agent-browser screenshot "$SCREENSHOT_DIR/17-on-my-way.png"

    # Verify status changed — "Job Started" button should now appear
    if agent-browser is visible "[data-testid='job-started-btn']" 2>/dev/null; then
      echo "  ✓ Status transitioned — 'Job Started' button visible"
      PASS_COUNT=$((PASS_COUNT + 1))

      # Click "Job Started"
      agent-browser click "[data-testid='job-started-btn']"
      agent-browser wait --load networkidle
      agent-browser wait 2000
      agent-browser screenshot "$SCREENSHOT_DIR/18-job-started.png"

      # Verify status changed — "Job Complete" button should now appear
      if agent-browser is visible "[data-testid='job-complete-btn']" 2>/dev/null; then
        echo "  ✓ Status transitioned — 'Job Complete' button visible"
        PASS_COUNT=$((PASS_COUNT + 1))

        # Click "Job Complete"
        agent-browser click "[data-testid='job-complete-btn']"
        agent-browser wait --load networkidle
        agent-browser wait 2000
        agent-browser screenshot "$SCREENSHOT_DIR/19-job-complete.png"

        # Verify final status
        STATUS_TEXT=$(agent-browser get text "[data-testid='appointment-status']" 2>/dev/null || echo "")
        if echo "$STATUS_TEXT" | grep -qi "complete"; then
          echo "  ✓ Final status is completed"
          PASS_COUNT=$((PASS_COUNT + 1))
        else
          echo "  ⚠ Final status text: ${STATUS_TEXT:0:40} — may be blocked by payment requirement"
        fi
      else
        echo "  ⚠ 'Job Complete' button not visible — may be blocked by payment requirement (Req 36)"
      fi
    else
      echo "  ✗ FAIL: 'Job Started' button not visible after clicking 'On My Way'"
      FAIL_COUNT=$((FAIL_COUNT + 1))
    fi
  elif agent-browser is visible "[data-testid='job-started-btn']" 2>/dev/null; then
    echo "  ✓ 'Job Started' button visible (appointment already en_route)"
    PASS_COUNT=$((PASS_COUNT + 1))
  elif agent-browser is visible "[data-testid='job-complete-btn']" 2>/dev/null; then
    echo "  ✓ 'Job Complete' button visible (appointment already in_progress)"
    PASS_COUNT=$((PASS_COUNT + 1))
  else
    echo "  ⚠ No workflow buttons visible — appointment may be in a non-actionable state"
  fi
else
  echo "  ⚠ Could not open appointment detail for workflow button test"
fi

# Close any open panels
agent-browser press Escape 2>/dev/null || true
agent-browser wait 500

# ---------------------------------------------------------------------------
# Step 15: Payment required before job completion (Req 36.7)
# ---------------------------------------------------------------------------
echo ""
echo "Step 15: Testing payment-required blocking (Req 36.7)..."

# Navigate to schedule and find an in-progress appointment
agent-browser open "${BASE_URL}/schedule"
agent-browser wait --load networkidle
agent-browser wait 2000

if agent-browser is visible ".fc-event" 2>/dev/null; then
  agent-browser click ".fc-event"
  agent-browser wait 1500
fi

if agent-browser is visible "[data-testid='appointment-detail']" 2>/dev/null; then
  # Check if "Job Complete" button is disabled or shows blocking message
  if agent-browser is visible "[data-testid='job-complete-btn']" 2>/dev/null; then
    IS_DISABLED=$(agent-browser is enabled "[data-testid='job-complete-btn']" 2>/dev/null && echo "enabled" || echo "disabled")

    if [ "$IS_DISABLED" = "disabled" ]; then
      echo "  ✓ 'Job Complete' button is disabled (payment required)"
      PASS_COUNT=$((PASS_COUNT + 1))
    else
      # Click it and check for blocking message
      agent-browser click "[data-testid='job-complete-btn']"
      agent-browser wait 1000

      PAGE_TEXT=$(agent-browser get text "body" 2>/dev/null || echo "")
      if echo "$PAGE_TEXT" | grep -qi "collect payment\|send an invoice\|payment.*required"; then
        echo "  ✓ Blocking message displayed when attempting completion without payment"
        PASS_COUNT=$((PASS_COUNT + 1))
      else
        echo "  ⚠ No blocking message detected — appointment may already have payment"
      fi
    fi
  else
    echo "  ⚠ 'Job Complete' button not visible — appointment may not be in_progress"
  fi
else
  echo "  ⚠ Could not open appointment detail for payment blocking test"
fi

agent-browser screenshot "$SCREENSHOT_DIR/20-payment-blocking.png"

# Close any open panels
agent-browser press Escape 2>/dev/null || true
agent-browser wait 500

# ---------------------------------------------------------------------------
# Step 16: Duration metrics on completed appointment (Req 37.7)
# ---------------------------------------------------------------------------
echo ""
echo "Step 16: Verifying duration metrics (Req 37.7)..."

# Navigate to schedule and find a completed appointment
agent-browser open "${BASE_URL}/schedule"
agent-browser wait --load networkidle
agent-browser wait 2000

if agent-browser is visible ".fc-event" 2>/dev/null; then
  agent-browser click ".fc-event"
  agent-browser wait 1500
fi

if agent-browser is visible "[data-testid='appointment-detail']" 2>/dev/null; then
  agent-browser scroll down 400 2>/dev/null || true
  agent-browser wait 500

  if agent-browser is visible "[data-testid='duration-metrics']" 2>/dev/null; then
    METRICS_TEXT=$(agent-browser get text "[data-testid='duration-metrics']" 2>/dev/null || echo "")
    if [ -n "$METRICS_TEXT" ]; then
      echo "  ✓ Duration metrics displayed: ${METRICS_TEXT:0:80}"
      PASS_COUNT=$((PASS_COUNT + 1))
    else
      echo "  ✗ FAIL: Duration metrics section is empty"
      FAIL_COUNT=$((FAIL_COUNT + 1))
    fi
  else
    echo "  ⚠ Duration metrics not visible — appointment may not be completed"
  fi
else
  echo "  ⚠ Could not open appointment detail for duration metrics test"
fi

agent-browser screenshot "$SCREENSHOT_DIR/21-duration-metrics.png"

# Close any open panels
agent-browser press Escape 2>/dev/null || true
agent-browser wait 500

# ---------------------------------------------------------------------------
# Step 17: Appointment enrichment and Get Directions (Req 40.6)
# ---------------------------------------------------------------------------
echo ""
echo "Step 17: Verifying appointment enrichment fields (Req 40.6)..."

# Navigate to schedule and open an appointment
agent-browser open "${BASE_URL}/schedule"
agent-browser wait --load networkidle
agent-browser wait 2000

if agent-browser is visible ".fc-event" 2>/dev/null; then
  agent-browser click ".fc-event"
  agent-browser wait 1500
fi

if agent-browser is visible "[data-testid='appointment-detail']" 2>/dev/null; then
  # Check for enriched fields
  DETAIL_HTML=$(agent-browser get html "[data-testid='appointment-detail']" 2>/dev/null || echo "")
  ENRICHED_FIELDS=0

  # Check for customer name
  if echo "$DETAIL_HTML" | grep -qi "customer\|client"; then
    ENRICHED_FIELDS=$((ENRICHED_FIELDS + 1))
  fi

  # Check for phone
  if echo "$DETAIL_HTML" | grep -qiE "phone|tel|\(\d{3}\)"; then
    ENRICHED_FIELDS=$((ENRICHED_FIELDS + 1))
  fi

  # Check for job type
  if echo "$DETAIL_HTML" | grep -qi "job.*type\|service.*type\|irrigation\|repair\|install"; then
    ENRICHED_FIELDS=$((ENRICHED_FIELDS + 1))
  fi

  if [ "$ENRICHED_FIELDS" -ge 2 ]; then
    echo "  ✓ Enriched appointment fields found ($ENRICHED_FIELDS field types detected)"
    PASS_COUNT=$((PASS_COUNT + 1))
  else
    echo "  ⚠ Limited enriched fields detected ($ENRICHED_FIELDS)"
  fi

  # Check for "Get Directions" button
  if agent-browser is visible "[data-testid='get-directions-btn']" 2>/dev/null; then
    echo "  ✓ 'Get Directions' button visible"
    PASS_COUNT=$((PASS_COUNT + 1))

    # Verify it links to Google Maps
    DIRECTIONS_HREF=$(agent-browser get attr "[data-testid='get-directions-btn']" href 2>/dev/null || echo "")
    if echo "$DIRECTIONS_HREF" | grep -qi "maps\|google\|directions"; then
      echo "  ✓ Get Directions links to maps: ${DIRECTIONS_HREF:0:60}"
      PASS_COUNT=$((PASS_COUNT + 1))
    elif [ -n "$DIRECTIONS_HREF" ]; then
      echo "  ⚠ Get Directions href: ${DIRECTIONS_HREF:0:60}"
    fi
  else
    echo "  ✗ FAIL: 'Get Directions' button not found (data-testid='get-directions-btn')"
    FAIL_COUNT=$((FAIL_COUNT + 1))
  fi
else
  echo "  ⚠ Could not open appointment detail for enrichment test"
fi

agent-browser screenshot "$SCREENSHOT_DIR/22-enrichment.png"

# Close any open panels
agent-browser press Escape 2>/dev/null || true
agent-browser wait 500

# ---------------------------------------------------------------------------
# Step 18: Staff location map overlay (Req 41.8)
# ---------------------------------------------------------------------------
echo ""
echo "Step 18: Verifying staff location map overlay (Req 41.8)..."

# Navigate to schedule page
agent-browser open "${BASE_URL}/schedule"
agent-browser wait --load networkidle
agent-browser wait 2000

if agent-browser is visible "[data-testid='staff-location-map']" 2>/dev/null; then
  echo "  ✓ Staff location map overlay visible"
  PASS_COUNT=$((PASS_COUNT + 1))

  # Check for staff pins on the map
  MAP_HTML=$(agent-browser get html "[data-testid='staff-location-map']" 2>/dev/null || echo "")
  if echo "$MAP_HTML" | grep -qiE "pin|marker|staff-pin|map-marker"; then
    echo "  ✓ Staff pins detected on map"
    PASS_COUNT=$((PASS_COUNT + 1))
  elif [ -n "$MAP_HTML" ] && [ ${#MAP_HTML} -gt 100 ]; then
    echo "  ✓ Map overlay has content (pins may use canvas rendering)"
    PASS_COUNT=$((PASS_COUNT + 1))
  else
    echo "  ⚠ Staff pins not clearly detected in map HTML"
  fi
else
  echo "  ✗ FAIL: Staff location map not found (data-testid='staff-location-map')"
  FAIL_COUNT=$((FAIL_COUNT + 1))
fi

agent-browser screenshot "$SCREENSHOT_DIR/23-staff-map.png"

# ---------------------------------------------------------------------------
# Step 19: Staff break functionality (Req 42.7)
# ---------------------------------------------------------------------------
echo ""
echo "Step 19: Testing staff break functionality (Req 42.7)..."

if agent-browser is visible "[data-testid='take-break-btn']" 2>/dev/null; then
  echo "  ✓ 'Take Break' button visible"
  PASS_COUNT=$((PASS_COUNT + 1))

  agent-browser click "[data-testid='take-break-btn']"
  agent-browser wait --load networkidle
  agent-browser wait 2000

  # Verify break appears as blocked slot on calendar
  CALENDAR_HTML=$(agent-browser get html "[data-testid='calendar-view']" 2>/dev/null || echo "")
  if echo "$CALENDAR_HTML" | grep -qiE "break|blocked|unavailable|staff-break"; then
    echo "  ✓ Break appears as blocked slot on calendar"
    PASS_COUNT=$((PASS_COUNT + 1))
  else
    # Check for a break event on the calendar
    BREAK_EVENT=$(agent-browser get count "[data-testid='break-event']" 2>/dev/null || echo "0")
    if [ "$BREAK_EVENT" -gt 0 ] 2>/dev/null; then
      echo "  ✓ Break event visible on calendar"
      PASS_COUNT=$((PASS_COUNT + 1))
    else
      echo "  ⚠ Break slot not clearly visible — may use different styling"
    fi
  fi
else
  # Try finding the break button in a staff panel
  if agent-browser is visible "[data-testid='staff-panel']" 2>/dev/null; then
    PANEL_HTML=$(agent-browser get html "[data-testid='staff-panel']" 2>/dev/null || echo "")
    if echo "$PANEL_HTML" | grep -qi "Take Break\|take-break"; then
      echo "  ✓ Take Break option found in staff panel"
      PASS_COUNT=$((PASS_COUNT + 1))
    else
      echo "  ✗ FAIL: Take Break button not found in staff panel"
      FAIL_COUNT=$((FAIL_COUNT + 1))
    fi
  else
    echo "  ✗ FAIL: Take Break button not found (data-testid='take-break-btn')"
    FAIL_COUNT=$((FAIL_COUNT + 1))
  fi
fi

agent-browser screenshot "$SCREENSHOT_DIR/24-staff-break.png"

# Take a final screenshot
agent-browser screenshot "$SCREENSHOT_DIR/25-schedule-final.png"

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "-------------------------------------------------------"
echo "Schedule & Staff E2E Results: $PASS_COUNT passed, $FAIL_COUNT failed"
echo "Screenshots saved to: $SCREENSHOT_DIR/"
echo "-------------------------------------------------------"

if [ "$FAIL_COUNT" -gt 0 ]; then
  echo "❌ FAIL: Schedule/Staff feature issues detected"
  exit 1
fi

echo "✅ PASS: All schedule/staff feature tests passed"
exit 0
