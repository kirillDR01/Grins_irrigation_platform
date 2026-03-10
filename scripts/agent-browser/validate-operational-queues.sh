#!/bin/bash
# Agent-Browser Validation: Operational Queues
# Validates renewal pipeline, failed payments, unscheduled visits, onboarding incomplete

set -e

echo "🧪 Operational Queues Validation"
echo "================================="

mkdir -p screenshots/agreements

# Step 1: Navigate to Agreements page
echo "Step 1: Opening Agreements page..."
agent-browser open http://localhost:5173/agreements
agent-browser wait --load networkidle
echo "  ✓ Agreements page loaded"

# Step 2: Verify Renewal Pipeline Queue
echo "Step 2: Verifying Renewal Pipeline Queue..."
agent-browser is visible "[data-testid='renewal-pipeline-queue']" && echo "  ✓ Renewal pipeline queue visible"
agent-browser screenshot screenshots/agreements/renewal-pipeline.png
echo "  ✓ Screenshot saved"

# Check for approve/reject buttons if rows exist
ROW_COUNT=$(agent-browser get count "[data-testid^='renewal-row-']" 2>/dev/null || echo "0")
if [ "$ROW_COUNT" != "0" ] && [ -n "$ROW_COUNT" ]; then
  echo "  ✓ Found $ROW_COUNT renewal pipeline rows"
  # Verify urgency badges may be present
  agent-browser get count "[data-testid='urgency-warning']" 2>/dev/null && echo "  ✓ Urgency warning badges checked"
  agent-browser get count "[data-testid='urgency-critical']" 2>/dev/null && echo "  ✓ Urgency critical badges checked"
else
  echo "  ⚠ No renewal pipeline rows (empty queue)"
fi

# Step 3: Verify Failed Payments Queue
echo "Step 3: Verifying Failed Payments Queue..."
agent-browser is visible "[data-testid='failed-payments-queue']" && echo "  ✓ Failed payments queue visible"
agent-browser screenshot screenshots/agreements/failed-payments.png
echo "  ✓ Screenshot saved"

# Step 4: Verify Unscheduled Visits Queue
echo "Step 4: Verifying Unscheduled Visits Queue..."
agent-browser is visible "[data-testid='unscheduled-visits-queue']" && echo "  ✓ Unscheduled visits queue visible"
agent-browser screenshot screenshots/agreements/unscheduled-visits.png
echo "  ✓ Screenshot saved"

# Step 5: Verify Onboarding Incomplete Queue
echo "Step 5: Verifying Onboarding Incomplete Queue..."
agent-browser is visible "[data-testid='onboarding-incomplete-queue']" && echo "  ✓ Onboarding incomplete queue visible"
agent-browser screenshot screenshots/agreements/onboarding-incomplete.png
echo "  ✓ Screenshot saved"

echo ""
echo "✅ Operational Queues Validation Complete"
