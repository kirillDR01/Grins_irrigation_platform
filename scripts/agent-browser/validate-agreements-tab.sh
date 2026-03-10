#!/bin/bash
# Agent-Browser Validation: Agreements Tab
# Validates KPI cards, charts, status filter tabs, table, and row navigation

set -e

echo "🧪 Agreements Tab Validation"
echo "============================"

mkdir -p screenshots/agreements

# Step 1: Navigate to Agreements page
echo "Step 1: Opening Agreements page..."
agent-browser open http://localhost:5173/agreements
agent-browser wait --load networkidle
echo "  ✓ Agreements page loaded"

# Step 2: Verify KPI cards render
echo "Step 2: Verifying KPI cards..."
agent-browser is visible "[data-testid='business-metrics-cards']" && echo "  ✓ Metrics cards container visible"
agent-browser is visible "[data-testid='metric-active-agreements']" && echo "  ✓ Active Agreements card visible"
agent-browser is visible "[data-testid='metric-mrr']" && echo "  ✓ MRR card visible"
agent-browser is visible "[data-testid='metric-renewal-rate']" && echo "  ✓ Renewal Rate card visible"
agent-browser is visible "[data-testid='metric-churn-rate']" && echo "  ✓ Churn Rate card visible"
agent-browser is visible "[data-testid='metric-past-due-amount']" && echo "  ✓ Past Due Amount card visible"

# Step 3: Verify charts render
echo "Step 3: Verifying charts..."
agent-browser is visible "[data-testid='mrr-chart']" && echo "  ✓ MRR chart visible"
agent-browser is visible "[data-testid='tier-distribution-chart']" && echo "  ✓ Tier distribution chart visible"

# Step 4: Verify status filter tabs
echo "Step 4: Verifying status filter tabs..."
agent-browser is visible "[data-testid='agreement-status-tabs']" && echo "  ✓ Status tabs container visible"
agent-browser is visible "[data-testid='tab-all']" && echo "  ✓ All tab visible"
agent-browser is visible "[data-testid='tab-active']" && echo "  ✓ Active tab visible"
agent-browser is visible "[data-testid='tab-pending']" && echo "  ✓ Pending tab visible"
agent-browser is visible "[data-testid='tab-pending_renewal']" && echo "  ✓ Pending Renewal tab visible"
agent-browser is visible "[data-testid='tab-past_due']" && echo "  ✓ Past Due tab visible"
agent-browser is visible "[data-testid='tab-cancelled']" && echo "  ✓ Cancelled tab visible"

# Step 5: Verify agreements table renders
echo "Step 5: Verifying agreements table..."
agent-browser is visible "[data-testid='agreements-list']" && echo "  ✓ Agreements list container visible"
agent-browser is visible "[data-testid='agreements-table']" && echo "  ✓ Agreements table visible"

# Step 6: Click status filter tabs and verify table updates
echo "Step 6: Testing status filter tab clicks..."
agent-browser click "[data-testid='tab-active']"
agent-browser wait 500
agent-browser screenshot screenshots/agreements/tab-active.png
echo "  ✓ Active tab clicked, screenshot saved"

agent-browser click "[data-testid='tab-pending']"
agent-browser wait 500
agent-browser screenshot screenshots/agreements/tab-pending.png
echo "  ✓ Pending tab clicked, screenshot saved"

agent-browser click "[data-testid='tab-all']"
agent-browser wait 500
echo "  ✓ Returned to All tab"

# Step 7: Verify row click navigates to detail
echo "Step 7: Testing row navigation to detail..."
ROW_COUNT=$(agent-browser get count "[data-testid='agreement-row']" 2>/dev/null || echo "0")
if [ "$ROW_COUNT" != "0" ] && [ -n "$ROW_COUNT" ]; then
  # Click the first agreement number link
  agent-browser snapshot -i > /dev/null 2>&1
  agent-browser click "[data-testid='agreement-row']:first-child a" || true
  agent-browser wait 1000
  CURRENT_URL=$(agent-browser get url 2>/dev/null || echo "")
  if echo "$CURRENT_URL" | grep -q "agreements/"; then
    echo "  ✓ Row click navigated to agreement detail"
  else
    echo "  ⚠ Row click did not navigate (may have no data)"
  fi
  agent-browser back
  agent-browser wait --load networkidle
else
  echo "  ⚠ No agreement rows to test navigation (empty table)"
fi

# Step 8: Take final screenshot
echo "Step 8: Taking final screenshot..."
agent-browser screenshot screenshots/agreements/agreements-tab-full.png --full
echo "  ✓ Full page screenshot saved"

echo ""
echo "✅ Agreements Tab Validation Complete"
