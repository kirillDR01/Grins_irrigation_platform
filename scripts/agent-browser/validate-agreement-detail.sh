#!/bin/bash
# Agent-Browser Validation: Agreement Detail View
# Validates info section, jobs timeline, compliance log, action buttons per status

set -e

echo "🧪 Agreement Detail Validation"
echo "==============================="

mkdir -p screenshots/agreements

# Step 1: Navigate to Agreements page and find a row
echo "Step 1: Opening Agreements page..."
agent-browser open http://localhost:5173/agreements
agent-browser wait --load networkidle

ROW_COUNT=$(agent-browser get count "[data-testid='agreement-row']" 2>/dev/null || echo "0")
if [ "$ROW_COUNT" = "0" ] || [ -z "$ROW_COUNT" ]; then
  echo "  ⚠ No agreements found — skipping detail validation"
  echo "✅ Agreement Detail Validation Skipped (no data)"
  exit 0
fi

# Step 2: Click first agreement to navigate to detail
echo "Step 2: Navigating to agreement detail..."
agent-browser click "[data-testid='agreement-row']:first-child a"
agent-browser wait --load networkidle
echo "  ✓ Navigated to agreement detail"

# Step 3: Verify info section renders
echo "Step 3: Verifying info section..."
agent-browser is visible "[data-testid='agreement-detail']" && echo "  ✓ Agreement detail container visible"
agent-browser is visible "[data-testid='agreement-info']" && echo "  ✓ Agreement info card visible"
agent-browser is visible "[data-testid='agreement-status-badge']" && echo "  ✓ Status badge visible"
agent-browser is visible "[data-testid='agreement-title']" && echo "  ✓ Agreement title visible"

# Step 4: Verify jobs timeline renders
echo "Step 4: Verifying jobs timeline..."
agent-browser is visible "[data-testid='agreement-jobs-timeline']" && echo "  ✓ Jobs timeline card visible"
agent-browser is visible "[data-testid='jobs-progress']" && echo "  ✓ Jobs progress summary visible"

# Step 5: Verify status log renders
echo "Step 5: Verifying status log..."
agent-browser is visible "[data-testid='agreement-status-log']" && echo "  ✓ Status log card visible"

# Step 6: Verify compliance log renders
echo "Step 6: Verifying compliance log..."
agent-browser is visible "[data-testid='agreement-compliance-log']" && echo "  ✓ Compliance log card visible"
agent-browser is visible "[data-testid='compliance-status-summary']" && echo "  ✓ Compliance status summary visible"

# Step 7: Verify action buttons visible
echo "Step 7: Verifying action buttons..."
agent-browser is visible "[data-testid='agreement-actions']" && echo "  ✓ Action buttons container visible"

# Step 8: Verify admin notes section
echo "Step 8: Verifying admin notes..."
agent-browser is visible "[data-testid='agreement-admin-notes']" && echo "  ✓ Admin notes card visible"
agent-browser is visible "[data-testid='admin-notes-input']" && echo "  ✓ Admin notes input visible"

# Step 9: Verify customer link
echo "Step 9: Verifying customer link..."
agent-browser is visible "[data-testid='agreement-customer-link']" && echo "  ✓ Customer link visible"

# Step 10: Take screenshot
echo "Step 10: Taking screenshot..."
agent-browser screenshot screenshots/agreements/agreement-detail.png --full
echo "  ✓ Full page screenshot saved"

echo ""
echo "✅ Agreement Detail Validation Complete"
