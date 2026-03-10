#!/bin/bash
# Agent-Browser Validation: Dashboard Modifications
# Validates subscription widgets and lead widgets on dashboard

set -e

echo "🧪 Dashboard Modifications Validation"
echo "======================================="

mkdir -p screenshots/dashboard

# Step 1: Navigate to Dashboard
echo "Step 1: Opening Dashboard..."
agent-browser open http://localhost:5173/dashboard
agent-browser wait --load networkidle
echo "  ✓ Dashboard loaded"

# Step 2: Verify subscription dashboard widgets
echo "Step 2: Verifying subscription widgets..."
agent-browser is visible "[data-testid='subscription-dashboard-widgets']" && echo "  ✓ Subscription widgets container visible"
agent-browser is visible "[data-testid='widget-active-agreements']" && echo "  ✓ Active Agreements widget visible"
agent-browser is visible "[data-testid='widget-mrr']" && echo "  ✓ MRR widget visible"
agent-browser is visible "[data-testid='widget-renewal-pipeline']" && echo "  ✓ Renewal Pipeline widget visible"
agent-browser is visible "[data-testid='widget-failed-payments']" && echo "  ✓ Failed Payments widget visible"
agent-browser screenshot screenshots/dashboard/subscription-widgets.png
echo "  ✓ Screenshot saved"

# Step 3: Verify lead dashboard widgets
echo "Step 3: Verifying lead widgets..."
agent-browser is visible "[data-testid='widget-leads-awaiting-contact']" && echo "  ✓ Leads Awaiting Contact widget visible"
agent-browser is visible "[data-testid='widget-follow-up-queue']" && echo "  ✓ Follow-Up Queue widget visible"
agent-browser is visible "[data-testid='widget-leads-by-source']" && echo "  ✓ Leads by Source widget visible"
agent-browser screenshot screenshots/dashboard/lead-widgets.png
echo "  ✓ Screenshot saved"

# Step 4: Take full dashboard screenshot
echo "Step 4: Taking full dashboard screenshot..."
agent-browser screenshot screenshots/dashboard/dashboard-full.png --full
echo "  ✓ Full page screenshot saved"

echo ""
echo "✅ Dashboard Modifications Validation Complete"
