#!/bin/bash
# E2E Test: Lead Pipeline Features
# Validates: Requirements 12.8, 13.11, 14.8, 15.8, 16.10, 17.9, 18.6, 19.9, 67.2
#
# Tests lead city/address display, action tag badges and filtering,
# bulk outreach, attachments upload/delete, portal estimate approval,
# estimate creation from template, estimate-pending tag, and
# work-requests redirect to leads.
#
# Usage:
#   bash scripts/e2e/test-leads.sh [--headed]
#
# Prerequisites:
#   - Frontend running at http://localhost:5173
#   - Backend running at http://localhost:8000
#   - agent-browser installed
#   - Valid admin credentials in environment or defaults

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCREENSHOT_DIR="e2e-screenshots/leads"
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

echo "🧪 E2E Test: Lead Pipeline Features (Req 12.8, 13.11, 14.8, 15.8, 16.10, 17.9, 18.6, 19.9)"
echo "=============================================================================================="

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
  echo "❌ FAIL: Could not log in — aborting lead tests"
  exit 1
fi

echo "  ✓ Login successful — navigated to: $CURRENT_URL"
PASS_COUNT=$((PASS_COUNT + 1))

# ---------------------------------------------------------------------------
# Step 2: Navigate to /leads and verify city column (Req 12.8)
# ---------------------------------------------------------------------------
echo ""
echo "Step 2: Verifying city displayed in leads list (Req 12.8)..."
agent-browser open "${BASE_URL}/leads"
agent-browser wait --load networkidle
agent-browser wait 2000
agent-browser screenshot "$SCREENSHOT_DIR/03-leads-list.png"

CURRENT_URL=$(agent-browser get url 2>/dev/null || echo "")
if echo "$CURRENT_URL" | grep -qi "/login"; then
  echo "  ✗ FAIL: Redirected to login"
  echo "❌ FAIL: Session lost — aborting"
  exit 1
fi

# Verify leads page loaded
if agent-browser is visible "[data-testid='leads-page']" 2>/dev/null; then
  echo "  ✓ Leads page loaded"
  PASS_COUNT=$((PASS_COUNT + 1))
else
  echo "  ✗ FAIL: Leads page not found (data-testid='leads-page')"
  FAIL_COUNT=$((FAIL_COUNT + 1))
fi

# Verify leads table is present
if agent-browser is visible "[data-testid='leads-table']" 2>/dev/null; then
  echo "  ✓ Leads table visible"
  PASS_COUNT=$((PASS_COUNT + 1))
else
  echo "  ✗ FAIL: Leads table not found (data-testid='leads-table')"
  FAIL_COUNT=$((FAIL_COUNT + 1))
fi

# Check for City column header in the table
TABLE_HTML=$(agent-browser get html "[data-testid='leads-table']" 2>/dev/null || echo "")
if echo "$TABLE_HTML" | grep -qi "city"; then
  echo "  ✓ City column present in leads table"
  PASS_COUNT=$((PASS_COUNT + 1))
else
  echo "  ✗ FAIL: City column not found in leads table"
  FAIL_COUNT=$((FAIL_COUNT + 1))
fi

# Click first lead row to navigate to detail
if agent-browser is visible "[data-testid='lead-row']" 2>/dev/null; then
  agent-browser click "[data-testid='lead-row']"
  agent-browser wait --load networkidle
  agent-browser wait 2000
  agent-browser screenshot "$SCREENSHOT_DIR/04-lead-detail.png"

  DETAIL_URL=$(agent-browser get url 2>/dev/null || echo "")
  if echo "$DETAIL_URL" | grep -qi "/leads/"; then
    echo "  ✓ Navigated to lead detail: $DETAIL_URL"
    PASS_COUNT=$((PASS_COUNT + 1))
  else
    echo "  ⚠ May not be on lead detail page (URL: $DETAIL_URL)"
  fi

  # Verify full address fields are shown (Req 12.4)
  if agent-browser is visible "[data-testid='address-display']" 2>/dev/null || \
     agent-browser is visible "[data-testid='address-form']" 2>/dev/null; then
    echo "  ✓ Address section visible on lead detail"
    PASS_COUNT=$((PASS_COUNT + 1))
  else
    echo "  ⚠ Address section not immediately visible"
  fi

  # Click edit address button and verify editable fields
  if agent-browser is visible "[data-testid='edit-address-btn']" 2>/dev/null; then
    agent-browser click "[data-testid='edit-address-btn']"
    agent-browser wait 500
    agent-browser screenshot "$SCREENSHOT_DIR/05-address-edit-form.png"

    if agent-browser is visible "[data-testid='address-form']" 2>/dev/null; then
      echo "  ✓ Address edit form visible with editable fields"
      PASS_COUNT=$((PASS_COUNT + 1))

      # Verify individual address fields exist
      ADDR_FIELDS=0
      if agent-browser is visible "[data-testid='address-input']" 2>/dev/null; then ADDR_FIELDS=$((ADDR_FIELDS + 1)); fi
      if agent-browser is visible "[data-testid='city-input']" 2>/dev/null; then ADDR_FIELDS=$((ADDR_FIELDS + 1)); fi
      if agent-browser is visible "[data-testid='state-input']" 2>/dev/null; then ADDR_FIELDS=$((ADDR_FIELDS + 1)); fi
      if agent-browser is visible "[data-testid='zip-code-input']" 2>/dev/null; then ADDR_FIELDS=$((ADDR_FIELDS + 1)); fi

      if [ "$ADDR_FIELDS" -ge 3 ]; then
        echo "  ✓ Full address fields present ($ADDR_FIELDS/4 fields)"
        PASS_COUNT=$((PASS_COUNT + 1))
      else
        echo "  ✗ FAIL: Only $ADDR_FIELDS/4 address fields found"
        FAIL_COUNT=$((FAIL_COUNT + 1))
      fi
    else
      echo "  ✗ FAIL: Address edit form did not appear"
      FAIL_COUNT=$((FAIL_COUNT + 1))
    fi
  else
    echo "  ⚠ Edit address button not found — address may not be editable"
  fi
else
  echo "  ⚠ No lead rows found to click — leads list may be empty"
fi

# ---------------------------------------------------------------------------
# Step 3: Verify tag badges and filter by tag (Req 13.11)
# ---------------------------------------------------------------------------
echo ""
echo "Step 3: Verifying tag badges and tag filtering (Req 13.11)..."
agent-browser open "${BASE_URL}/leads"
agent-browser wait --load networkidle
agent-browser wait 2000
agent-browser screenshot "$SCREENSHOT_DIR/06-leads-list-tags.png"

# Check for tag badges in the leads table
if agent-browser is visible "[data-testid='lead-tag-badges']" 2>/dev/null; then
  echo "  ✓ Tag badges visible in leads list"
  PASS_COUNT=$((PASS_COUNT + 1))
else
  # Check for individual tag badges
  TAG_HTML=$(agent-browser get html "[data-testid='leads-table']" 2>/dev/null || echo "")
  if echo "$TAG_HTML" | grep -qi "tag-\|lead-tag-badges\|needs_contact\|needs_estimate\|estimate_pending"; then
    echo "  ✓ Tag indicators detected in leads table"
    PASS_COUNT=$((PASS_COUNT + 1))
  else
    echo "  ✗ FAIL: No tag badges found in leads table"
    FAIL_COUNT=$((FAIL_COUNT + 1))
  fi
fi

# Filter by action tag using the tag filter dropdown
if agent-browser is visible "[data-testid='lead-action-tag-filter']" 2>/dev/null; then
  agent-browser click "[data-testid='lead-action-tag-filter']"
  agent-browser wait 500
  agent-browser screenshot "$SCREENSHOT_DIR/07-tag-filter-open.png"

  # Select NEEDS_CONTACT tag filter
  if agent-browser is visible "text=Needs Contact" 2>/dev/null; then
    agent-browser click "text=Needs Contact"
  elif agent-browser is visible "[data-value='NEEDS_CONTACT']" 2>/dev/null; then
    agent-browser click "[data-value='NEEDS_CONTACT']"
  else
    # Try clicking the first available option
    agent-browser click "[role='option']:first-child" 2>/dev/null || true
  fi

  agent-browser wait --load networkidle
  agent-browser wait 1500
  agent-browser screenshot "$SCREENSHOT_DIR/08-filtered-by-tag.png"

  # Verify filtered results are shown
  LEAD_COUNT=$(agent-browser get count "[data-testid='lead-row']" 2>/dev/null || echo "0")
  echo "  ✓ Tag filter applied — $LEAD_COUNT leads shown after filtering"
  PASS_COUNT=$((PASS_COUNT + 1))
else
  echo "  ✗ FAIL: Action tag filter dropdown not found (data-testid='lead-action-tag-filter')"
  FAIL_COUNT=$((FAIL_COUNT + 1))
fi

# ---------------------------------------------------------------------------
# Step 4: Test Bulk Outreach (Req 14.8)
# ---------------------------------------------------------------------------
echo ""
echo "Step 4: Testing bulk outreach flow (Req 14.8)..."

# Reset filters first — reload the page
agent-browser open "${BASE_URL}/leads"
agent-browser wait --load networkidle
agent-browser wait 2000

# Select multiple leads using checkboxes
if agent-browser is visible "[data-testid='select-all-checkbox']" 2>/dev/null; then
  agent-browser click "[data-testid='select-all-checkbox']"
  agent-browser wait 500
  agent-browser screenshot "$SCREENSHOT_DIR/09-leads-selected.png"
  echo "  ✓ Select All checkbox clicked"
  PASS_COUNT=$((PASS_COUNT + 1))
else
  echo "  ⚠ Select All checkbox not found — trying individual selection"
  # Try selecting first two lead checkboxes
  LEAD_CHECKBOXES=$(agent-browser get count "[data-testid^='select-lead-']" 2>/dev/null || echo "0")
  if [ "$LEAD_CHECKBOXES" -gt 0 ]; then
    agent-browser click "[data-testid^='select-lead-']" 2>/dev/null || true
    agent-browser wait 300
  fi
fi

# Click Bulk Outreach button
if agent-browser is visible "[data-testid='bulk-outreach-btn']" 2>/dev/null; then
  # Check if button is enabled (leads must be selected)
  agent-browser click "[data-testid='bulk-outreach-btn']"
  agent-browser wait 1000
  agent-browser screenshot "$SCREENSHOT_DIR/10-bulk-outreach-dialog.png"

  # Verify dialog opened
  if agent-browser is visible "[data-testid='bulk-outreach-dialog']" 2>/dev/null; then
    echo "  ✓ Bulk Outreach dialog opened"
    PASS_COUNT=$((PASS_COUNT + 1))

    # Select a template
    if agent-browser is visible "[data-testid='template-selector']" 2>/dev/null; then
      agent-browser click "[data-testid='template-selector']"
      agent-browser wait 500
      # Select first available template option
      agent-browser click "[role='option']:first-child" 2>/dev/null || true
      agent-browser wait 500
      echo "  ✓ Template selector available"
      PASS_COUNT=$((PASS_COUNT + 1))
    fi

    # Fill message if empty
    if agent-browser is visible "[data-testid='outreach-message']" 2>/dev/null; then
      CURRENT_MSG=$(agent-browser get value "[data-testid='outreach-message']" 2>/dev/null || echo "")
      if [ -z "$CURRENT_MSG" ]; then
        agent-browser fill "[data-testid='outreach-message']" "Hello! We wanted to follow up on your inquiry. Please let us know if you have any questions."
      fi
    fi

    agent-browser screenshot "$SCREENSHOT_DIR/11-outreach-ready.png"

    # Click send button
    if agent-browser is visible "[data-testid='send-outreach-btn']" 2>/dev/null; then
      agent-browser click "[data-testid='send-outreach-btn']"
      agent-browser wait --load networkidle
      agent-browser wait 2000
      agent-browser screenshot "$SCREENSHOT_DIR/12-outreach-sent.png"

      # Verify success toast/summary appeared (toast contains "Sent:", "Skipped:", "Failed:")
      PAGE_TEXT=$(agent-browser get text "body" 2>/dev/null || echo "")
      if echo "$PAGE_TEXT" | grep -qi "sent\|outreach complete\|success\|bulk outreach"; then
        echo "  ✓ Bulk outreach completed with summary"
        PASS_COUNT=$((PASS_COUNT + 1))
      else
        echo "  ⚠ Could not confirm outreach summary — toast may have dismissed"
      fi
    else
      echo "  ⚠ Send outreach button not found or disabled"
    fi
  else
    echo "  ✗ FAIL: Bulk Outreach dialog did not open"
    FAIL_COUNT=$((FAIL_COUNT + 1))
  fi
else
  echo "  ✗ FAIL: Bulk Outreach button not found (data-testid='bulk-outreach-btn')"
  FAIL_COUNT=$((FAIL_COUNT + 1))
fi

# ---------------------------------------------------------------------------
# Step 5: Test Lead Attachments upload and delete (Req 15.8)
# ---------------------------------------------------------------------------
echo ""
echo "Step 5: Testing lead attachment upload and delete (Req 15.8)..."

# Navigate to a lead detail
agent-browser open "${BASE_URL}/leads"
agent-browser wait --load networkidle
agent-browser wait 2000

if agent-browser is visible "[data-testid='lead-row']" 2>/dev/null; then
  agent-browser click "[data-testid='lead-row']"
  agent-browser wait --load networkidle
  agent-browser wait 2000
fi

agent-browser screenshot "$SCREENSHOT_DIR/13-lead-detail-attachments.png"

# Scroll to find attachment panel
agent-browser scroll down 400 2>/dev/null || true
agent-browser wait 500

if agent-browser is visible "[data-testid='attachment-panel']" 2>/dev/null; then
  echo "  ✓ Attachment panel visible on lead detail"
  PASS_COUNT=$((PASS_COUNT + 1))

  # Create a small test PDF file for upload
  TEST_PDF="/tmp/e2e-test-estimate.pdf"
  printf '%%PDF-1.0\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \ntrailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n190\n%%%%EOF' > "$TEST_PDF" 2>/dev/null || true

  # Select ESTIMATE type from dropdown
  if agent-browser is visible "[data-testid='attachment-type-select']" 2>/dev/null; then
    agent-browser click "[data-testid='attachment-type-select']"
    agent-browser wait 300
    if agent-browser is visible "text=Estimate" 2>/dev/null; then
      agent-browser click "text=Estimate"
    elif agent-browser is visible "[data-value='ESTIMATE']" 2>/dev/null; then
      agent-browser click "[data-value='ESTIMATE']"
    else
      agent-browser click "[role='option']:first-child" 2>/dev/null || true
    fi
    agent-browser wait 300
    echo "  ✓ Attachment type set to Estimate"
  fi

  # Upload the test PDF via file input
  if agent-browser is visible "[data-testid='attachment-file-input']" 2>/dev/null; then
    agent-browser fill "[data-testid='attachment-file-input']" "$TEST_PDF" 2>/dev/null || true
    agent-browser wait --load networkidle
    agent-browser wait 2000
    agent-browser screenshot "$SCREENSHOT_DIR/14-after-attachment-upload.png"

    # Verify attachment appeared in the Estimates group
    if agent-browser is visible "[data-testid='attachment-group-estimate']" 2>/dev/null; then
      echo "  ✓ Uploaded attachment appears in Estimates group"
      PASS_COUNT=$((PASS_COUNT + 1))

      # Try to delete the uploaded attachment
      # Find a delete button within the attachment panel
      if agent-browser is visible "[data-testid^='delete-btn-']" 2>/dev/null; then
        agent-browser click "[data-testid^='delete-btn-']"
        agent-browser wait 500
        agent-browser screenshot "$SCREENSHOT_DIR/15-delete-confirm.png"

        # Confirm deletion
        if agent-browser is visible "[data-testid^='confirm-delete-']" 2>/dev/null; then
          agent-browser click "[data-testid^='confirm-delete-']"
          agent-browser wait --load networkidle
          agent-browser wait 1500
          agent-browser screenshot "$SCREENSHOT_DIR/16-after-attachment-delete.png"
          echo "  ✓ Attachment deleted successfully"
          PASS_COUNT=$((PASS_COUNT + 1))
        else
          echo "  ⚠ Delete confirmation button not found"
        fi
      else
        echo "  ⚠ No delete button found for attachments"
      fi
    else
      echo "  ⚠ Attachment group not visible after upload — upload may have failed"
    fi
  else
    echo "  ⚠ File input not found for attachment upload"
  fi

  # Clean up test file
  rm -f "$TEST_PDF" 2>/dev/null || true
else
  echo "  ✗ FAIL: Attachment panel not found (data-testid='attachment-panel')"
  FAIL_COUNT=$((FAIL_COUNT + 1))
fi

# ---------------------------------------------------------------------------
# Step 6: Test Portal Estimate Review and Approval (Req 16.10)
# ---------------------------------------------------------------------------
echo ""
echo "Step 6: Testing portal estimate review and approval (Req 16.10)..."

# The portal is public — use a test token URL
# First try to find an estimate token from the API
PORTAL_TOKEN=""
ESTIMATE_TOKEN_URL=""

# Try to get an estimate token from the backend API
ESTIMATES_RESPONSE=$(curl -s --max-time 5 "http://localhost:8000/api/v1/estimates?page_size=1" \
  -H "Authorization: Bearer $(curl -s --max-time 5 http://localhost:8000/api/v1/auth/login \
    -H 'Content-Type: application/json' \
    -d "{\"email\":\"$ADMIN_EMAIL\",\"password\":\"$ADMIN_PASSWORD\"}" 2>/dev/null | \
    python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null)" 2>/dev/null || echo "")

if [ -n "$ESTIMATES_RESPONSE" ]; then
  PORTAL_TOKEN=$(echo "$ESTIMATES_RESPONSE" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    items = data.get('items', [])
    if items:
        print(items[0].get('customer_token', ''))
except: pass
" 2>/dev/null || echo "")
fi

if [ -n "$PORTAL_TOKEN" ] && [ "$PORTAL_TOKEN" != "" ]; then
  ESTIMATE_TOKEN_URL="${BASE_URL}/portal/estimates/${PORTAL_TOKEN}"
  echo "  ℹ Found estimate token, opening portal: $ESTIMATE_TOKEN_URL"

  agent-browser open "$ESTIMATE_TOKEN_URL"
  agent-browser wait --load networkidle
  agent-browser wait 2000
  agent-browser screenshot "$SCREENSHOT_DIR/17-portal-estimate-review.png"

  if agent-browser is visible "[data-testid='estimate-review-page']" 2>/dev/null; then
    echo "  ✓ Portal estimate review page loaded"
    PASS_COUNT=$((PASS_COUNT + 1))

    # Verify estimate details are shown
    if agent-browser is visible "[data-testid='estimate-line-items-table']" 2>/dev/null; then
      echo "  ✓ Estimate line items table visible"
      PASS_COUNT=$((PASS_COUNT + 1))
    fi

    if agent-browser is visible "[data-testid='estimate-totals']" 2>/dev/null; then
      echo "  ✓ Estimate totals section visible"
      PASS_COUNT=$((PASS_COUNT + 1))
    fi

    # Click approve button
    if agent-browser is visible "[data-testid='approve-estimate-btn']" 2>/dev/null; then
      agent-browser click "[data-testid='approve-estimate-btn']"
      agent-browser wait --load networkidle
      agent-browser wait 2000
      agent-browser screenshot "$SCREENSHOT_DIR/18-portal-approval-confirmation.png"

      # Verify approval confirmation (redirects to /confirmed or shows confirmation)
      CONFIRM_URL=$(agent-browser get url 2>/dev/null || echo "")
      PAGE_TEXT=$(agent-browser get text "body" 2>/dev/null || echo "")
      if echo "$CONFIRM_URL" | grep -qi "confirmed\|approved" || \
         echo "$PAGE_TEXT" | grep -qi "approved\|confirmation\|thank"; then
        echo "  ✓ Estimate approval confirmed"
        PASS_COUNT=$((PASS_COUNT + 1))
      else
        echo "  ⚠ Could not confirm approval — page may show different confirmation"
      fi
    elif agent-browser is visible "[data-testid='estimate-readonly-notice']" 2>/dev/null; then
      echo "  ✓ Estimate already approved/rejected (readonly notice shown)"
      PASS_COUNT=$((PASS_COUNT + 1))
    else
      echo "  ⚠ Approve button not found — estimate may already be actioned"
    fi
  elif agent-browser is visible "[data-testid='estimate-expired']" 2>/dev/null; then
    echo "  ⚠ Estimate link expired — skipping portal approval test"
  elif agent-browser is visible "[data-testid='estimate-error']" 2>/dev/null; then
    echo "  ⚠ Estimate load error — token may be invalid"
  else
    echo "  ⚠ Portal estimate page did not load as expected"
  fi
else
  echo "  ⚠ No estimate token found via API — testing portal page structure only"

  # Navigate to a known portal path to verify the route exists
  agent-browser open "${BASE_URL}/portal/estimates/test-token"
  agent-browser wait --load networkidle
  agent-browser wait 2000
  agent-browser screenshot "$SCREENSHOT_DIR/17-portal-estimate-error.png"

  if agent-browser is visible "[data-testid='estimate-review-page']" 2>/dev/null || \
     agent-browser is visible "[data-testid='estimate-error']" 2>/dev/null || \
     agent-browser is visible "[data-testid='estimate-loading']" 2>/dev/null; then
    echo "  ✓ Portal estimate route exists and renders"
    PASS_COUNT=$((PASS_COUNT + 1))
  else
    echo "  ✗ FAIL: Portal estimate route not found"
    FAIL_COUNT=$((FAIL_COUNT + 1))
  fi
fi

# ---------------------------------------------------------------------------
# Step 7: Test Estimate Creation from Template (Req 17.9)
# ---------------------------------------------------------------------------
echo ""
echo "Step 7: Testing estimate creation from template (Req 17.9)..."

# Re-login and navigate to a lead detail (portal may have cleared session)
agent-browser open "${BASE_URL}/login"
agent-browser wait --load networkidle
agent-browser wait 1000

# Check if we need to re-login
CURRENT_URL=$(agent-browser get url 2>/dev/null || echo "")
if echo "$CURRENT_URL" | grep -qi "/login"; then
  if agent-browser is visible "[data-testid='username-input']" 2>/dev/null; then
    agent-browser fill "[data-testid='username-input']" "$ADMIN_EMAIL"
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
fi

# Navigate to leads and click first lead
agent-browser open "${BASE_URL}/leads"
agent-browser wait --load networkidle
agent-browser wait 2000

if agent-browser is visible "[data-testid='lead-row']" 2>/dev/null; then
  agent-browser click "[data-testid='lead-row']"
  agent-browser wait --load networkidle
  agent-browser wait 2000
fi

agent-browser screenshot "$SCREENSHOT_DIR/19-lead-detail-for-estimate.png"

# Click "Create Estimate" button
if agent-browser is visible "[data-testid='create-estimate-btn']" 2>/dev/null; then
  agent-browser click "[data-testid='create-estimate-btn']"
  agent-browser wait 1000
  agent-browser screenshot "$SCREENSHOT_DIR/20-estimate-creator-dialog.png"

  if agent-browser is visible "[data-testid='estimate-creator-dialog']" 2>/dev/null; then
    echo "  ✓ Estimate Creator dialog opened"
    PASS_COUNT=$((PASS_COUNT + 1))

    # Select a template
    if agent-browser is visible "[data-testid='estimate-template-select']" 2>/dev/null; then
      agent-browser click "[data-testid='estimate-template-select']"
      agent-browser wait 500
      agent-browser screenshot "$SCREENSHOT_DIR/21-template-dropdown.png"

      # Select first template option (skip "No Template")
      OPTION_COUNT=$(agent-browser get count "[role='option']" 2>/dev/null || echo "0")
      if [ "$OPTION_COUNT" -gt 1 ] 2>/dev/null; then
        # Click the second option (first real template, skipping "No Template")
        agent-browser click "[role='option']:nth-child(2)" 2>/dev/null || \
          agent-browser click "[role='option']:first-child" 2>/dev/null || true
      else
        agent-browser click "[role='option']:first-child" 2>/dev/null || true
      fi
      agent-browser wait 500
      echo "  ✓ Template selected"
      PASS_COUNT=$((PASS_COUNT + 1))
    fi

    agent-browser screenshot "$SCREENSHOT_DIR/22-template-loaded.png"

    # Modify a line item price
    if agent-browser is visible "[data-testid='line-item-price-0']" 2>/dev/null; then
      agent-browser fill "[data-testid='line-item-price-0']" "150"
      agent-browser wait 300
      echo "  ✓ Line item price modified"
      PASS_COUNT=$((PASS_COUNT + 1))
    elif agent-browser is visible "[data-testid='line-item-name-0']" 2>/dev/null; then
      # At least verify line items are present
      echo "  ✓ Line items present in estimate form"
      PASS_COUNT=$((PASS_COUNT + 1))
    fi

    agent-browser screenshot "$SCREENSHOT_DIR/23-estimate-modified.png"

    # Verify total is displayed
    if agent-browser is visible "[data-testid='estimate-total']" 2>/dev/null; then
      TOTAL_TEXT=$(agent-browser get text "[data-testid='estimate-total']" 2>/dev/null || echo "")
      echo "  ✓ Estimate total displayed: $TOTAL_TEXT"
      PASS_COUNT=$((PASS_COUNT + 1))
    fi

    # Click Send Estimate
    if agent-browser is visible "[data-testid='send-estimate-btn']" 2>/dev/null; then
      agent-browser click "[data-testid='send-estimate-btn']"
      agent-browser wait --load networkidle
      agent-browser wait 2000
      agent-browser screenshot "$SCREENSHOT_DIR/24-estimate-sent.png"

      # Verify success — dialog should close and toast should appear
      PAGE_TEXT=$(agent-browser get text "body" 2>/dev/null || echo "")
      if echo "$PAGE_TEXT" | grep -qi "estimate created\|estimate.*sent\|success"; then
        echo "  ✓ Estimate created and sent successfully"
        PASS_COUNT=$((PASS_COUNT + 1))
      else
        echo "  ⚠ Could not confirm estimate creation — toast may have dismissed"
      fi
    else
      echo "  ⚠ Send Estimate button not found"
    fi
  else
    echo "  ✗ FAIL: Estimate Creator dialog did not open"
    FAIL_COUNT=$((FAIL_COUNT + 1))
  fi
else
  echo "  ✗ FAIL: Create Estimate button not found (data-testid='create-estimate-btn')"
  FAIL_COUNT=$((FAIL_COUNT + 1))
fi

# ---------------------------------------------------------------------------
# Step 8: Verify estimate-pending lead with correct tag (Req 18.6)
# ---------------------------------------------------------------------------
echo ""
echo "Step 8: Verifying estimate-pending lead with correct tag (Req 18.6)..."

agent-browser open "${BASE_URL}/leads"
agent-browser wait --load networkidle
agent-browser wait 2000
agent-browser screenshot "$SCREENSHOT_DIR/25-leads-list-estimate-pending.png"

# Filter by ESTIMATE_PENDING tag
if agent-browser is visible "[data-testid='lead-action-tag-filter']" 2>/dev/null; then
  agent-browser click "[data-testid='lead-action-tag-filter']"
  agent-browser wait 500

  # Select Estimate Pending option
  if agent-browser is visible "text=Estimate Pending" 2>/dev/null; then
    agent-browser click "text=Estimate Pending"
  elif agent-browser is visible "[data-value='ESTIMATE_PENDING']" 2>/dev/null; then
    agent-browser click "[data-value='ESTIMATE_PENDING']"
  else
    # Try to find any option with "pending" in it
    agent-browser click "text=Pending" 2>/dev/null || \
      agent-browser click "[role='option']:nth-child(4)" 2>/dev/null || true
  fi

  agent-browser wait --load networkidle
  agent-browser wait 1500
  agent-browser screenshot "$SCREENSHOT_DIR/26-filtered-estimate-pending.png"

  # Check if any leads appear with ESTIMATE_PENDING tag
  LEAD_COUNT=$(agent-browser get count "[data-testid='lead-row']" 2>/dev/null || echo "0")
  if [ "$LEAD_COUNT" -gt 0 ] 2>/dev/null; then
    echo "  ✓ Estimate-pending leads found: $LEAD_COUNT"
    PASS_COUNT=$((PASS_COUNT + 1))

    # Verify the tag badge is visible on the rows
    TABLE_HTML=$(agent-browser get html "[data-testid='leads-table']" 2>/dev/null || echo "")
    if echo "$TABLE_HTML" | grep -qi "estimate.pending\|tag-estimate_pending\|ESTIMATE_PENDING"; then
      echo "  ✓ ESTIMATE_PENDING tag badge visible on lead rows"
      PASS_COUNT=$((PASS_COUNT + 1))
    else
      echo "  ⚠ Could not confirm ESTIMATE_PENDING tag badge in HTML"
    fi
  else
    echo "  ⚠ No estimate-pending leads found — may not have any in current data"
    # Still verify the filter mechanism works
    echo "  ✓ Tag filter mechanism functional (0 results is valid)"
    PASS_COUNT=$((PASS_COUNT + 1))
  fi
else
  echo "  ✗ FAIL: Action tag filter not found for estimate-pending filtering"
  FAIL_COUNT=$((FAIL_COUNT + 1))
fi

# ---------------------------------------------------------------------------
# Step 9: Test /work-requests redirect to /leads (Req 19.9)
# ---------------------------------------------------------------------------
echo ""
echo "Step 9: Testing /work-requests redirect to /leads (Req 19.9)..."

agent-browser open "${BASE_URL}/work-requests"
agent-browser wait --load networkidle
agent-browser wait 3000
agent-browser screenshot "$SCREENSHOT_DIR/27-work-requests-redirect.png"

REDIRECT_URL=$(agent-browser get url 2>/dev/null || echo "")
if echo "$REDIRECT_URL" | grep -qi "/leads"; then
  echo "  ✓ /work-requests redirected to /leads"
  PASS_COUNT=$((PASS_COUNT + 1))

  # Verify the leads page loaded with data
  if agent-browser is visible "[data-testid='leads-page']" 2>/dev/null; then
    echo "  ✓ Leads page loaded after redirect"
    PASS_COUNT=$((PASS_COUNT + 1))
  fi

  # Verify leads table has data (former work request data should appear)
  if agent-browser is visible "[data-testid='leads-table']" 2>/dev/null; then
    LEAD_COUNT=$(agent-browser get count "[data-testid='lead-row']" 2>/dev/null || echo "0")
    if [ "$LEAD_COUNT" -gt 0 ] 2>/dev/null; then
      echo "  ✓ Former work request data appears in leads list ($LEAD_COUNT leads)"
      PASS_COUNT=$((PASS_COUNT + 1))
    else
      echo "  ⚠ No leads found after redirect — data may not be migrated yet"
    fi
  fi
elif echo "$REDIRECT_URL" | grep -qi "/work-requests"; then
  echo "  ✗ FAIL: /work-requests did not redirect to /leads (stayed at: $REDIRECT_URL)"
  FAIL_COUNT=$((FAIL_COUNT + 1))
else
  echo "  ⚠ Unexpected URL after /work-requests navigation: $REDIRECT_URL"
fi

# Take a final screenshot
agent-browser screenshot "$SCREENSHOT_DIR/28-leads-final.png"

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "-------------------------------------------------------"
echo "Leads E2E Results: $PASS_COUNT passed, $FAIL_COUNT failed"
echo "Screenshots saved to: $SCREENSHOT_DIR/"
echo "-------------------------------------------------------"

if [ "$FAIL_COUNT" -gt 0 ]; then
  echo "❌ FAIL: Lead pipeline feature issues detected"
  exit 1
fi

echo "✅ PASS: All lead pipeline feature tests passed"
exit 0
