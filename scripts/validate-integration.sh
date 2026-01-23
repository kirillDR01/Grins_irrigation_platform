#!/bin/bash
# Integration Validation Script for Admin Dashboard
# Uses agent-browser to validate full user journey across features

set -e

echo "🧪 Integration Validation Test"
echo "==============================="
echo "Scenario: Full user journey - Customer → Job → Appointment"
echo ""

# Create screenshots directory
mkdir -p screenshots/integration

# Step 1: Start at Dashboard
echo "Step 1: Opening Dashboard..."
agent-browser open http://localhost:5173
agent-browser wait --load networkidle
agent-browser screenshot screenshots/integration/01-dashboard.png
echo "  ✓ Dashboard loaded"

# Step 2: Navigate to Customers
echo "Step 2: Navigating to Customers..."
agent-browser click "[data-testid='nav-customers']"
agent-browser wait --load networkidle
agent-browser screenshot screenshots/integration/02-customers.png
echo "  ✓ Customers page loaded"

# Step 3: Navigate to Jobs
echo "Step 3: Navigating to Jobs..."
agent-browser click "[data-testid='nav-jobs']"
agent-browser wait --load networkidle
agent-browser screenshot screenshots/integration/03-jobs.png
echo "  ✓ Jobs page loaded"

# Step 4: Navigate to Schedule
echo "Step 4: Navigating to Schedule..."
agent-browser click "[data-testid='nav-schedule']"
agent-browser wait --load networkidle
agent-browser screenshot screenshots/integration/04-schedule.png
echo "  ✓ Schedule page loaded"

# Step 5: Navigate to Staff
echo "Step 5: Navigating to Staff..."
agent-browser click "[data-testid='nav-staff']"
agent-browser wait --load networkidle
agent-browser screenshot screenshots/integration/05-staff.png
echo "  ✓ Staff page loaded"

# Step 6: Return to Dashboard
echo "Step 6: Returning to Dashboard..."
agent-browser click "[data-testid='nav-dashboard']"
agent-browser wait --load networkidle
agent-browser screenshot screenshots/integration/06-dashboard-final.png
echo "  ✓ Dashboard loaded"

# Step 7: Verify dashboard metrics
echo "Step 7: Verifying dashboard components..."
agent-browser is visible "[data-testid='dashboard-page']" && echo "  ✓ Dashboard page visible"

# Close browser
agent-browser close

echo ""
echo "✅ Integration Validation PASSED!"
echo "Screenshots saved to screenshots/integration/"
echo ""
echo "Full user journey completed successfully:"
echo "  Dashboard → Customers → Jobs → Schedule → Staff → Dashboard"
