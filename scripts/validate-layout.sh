#!/bin/bash
# Layout Validation Script for Admin Dashboard
# Uses agent-browser to validate main layout renders correctly

set -e

echo "🧪 Layout Validation Test"
echo "========================="
echo "Scenario: Verify main layout renders with sidebar and navigation"
echo ""

# Create screenshots directory
mkdir -p screenshots/layout

# Step 1: Open the dashboard
echo "Step 1: Opening dashboard..."
agent-browser open http://localhost:5173
agent-browser wait --load networkidle
echo "  ✓ Dashboard loaded"

# Step 2: Verify sidebar is visible
echo "Step 2: Verifying sidebar navigation..."
agent-browser is visible "[data-testid='sidebar']" && echo "  ✓ Sidebar visible"

# Step 3: Verify navigation links
echo "Step 3: Verifying navigation links..."
agent-browser is visible "[data-testid='nav-dashboard']" && echo "  ✓ Dashboard nav link visible"
agent-browser is visible "[data-testid='nav-customers']" && echo "  ✓ Customers nav link visible"
agent-browser is visible "[data-testid='nav-jobs']" && echo "  ✓ Jobs nav link visible"
agent-browser is visible "[data-testid='nav-schedule']" && echo "  ✓ Schedule nav link visible"
agent-browser is visible "[data-testid='nav-staff']" && echo "  ✓ Staff nav link visible"

# Step 4: Take screenshot
echo "Step 4: Taking screenshot..."
agent-browser screenshot screenshots/layout/dashboard-layout.png
echo "  ✓ Screenshot saved to screenshots/layout/dashboard-layout.png"

# Step 5: Test navigation to Customers
echo "Step 5: Testing navigation to Customers..."
agent-browser click "[data-testid='nav-customers']"
agent-browser wait --load networkidle
agent-browser screenshot screenshots/layout/customers-page.png
echo "  ✓ Navigated to Customers page"

# Step 6: Test navigation to Jobs
echo "Step 6: Testing navigation to Jobs..."
agent-browser click "[data-testid='nav-jobs']"
agent-browser wait --load networkidle
agent-browser screenshot screenshots/layout/jobs-page.png
echo "  ✓ Navigated to Jobs page"

# Step 7: Test navigation to Schedule
echo "Step 7: Testing navigation to Schedule..."
agent-browser click "[data-testid='nav-schedule']"
agent-browser wait --load networkidle
agent-browser screenshot screenshots/layout/schedule-page.png
echo "  ✓ Navigated to Schedule page"

# Step 8: Test navigation to Staff
echo "Step 8: Testing navigation to Staff..."
agent-browser click "[data-testid='nav-staff']"
agent-browser wait --load networkidle
agent-browser screenshot screenshots/layout/staff-page.png
echo "  ✓ Navigated to Staff page"

# Step 9: Return to Dashboard
echo "Step 9: Returning to Dashboard..."
agent-browser click "[data-testid='nav-dashboard']"
agent-browser wait --load networkidle
echo "  ✓ Returned to Dashboard"

# Close browser
agent-browser close

echo ""
echo "✅ Layout Validation PASSED!"
echo "Screenshots saved to screenshots/layout/"
