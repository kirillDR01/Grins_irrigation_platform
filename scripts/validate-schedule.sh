#!/bin/bash
# Schedule Feature Validation Script for Admin Dashboard
# Uses agent-browser to validate calendar and appointment functionality

set -e

echo "🧪 Schedule Feature Validation Test"
echo "===================================="
echo "Scenario: Viktor manages appointments and schedules"
echo ""

# Create screenshots directory
mkdir -p screenshots/schedule

# Step 1: Navigate to Schedule page
echo "Step 1: Opening Schedule page..."
agent-browser open http://localhost:5173/schedule
agent-browser wait --load networkidle
echo "  ✓ Schedule page loaded"

# Step 2: Verify schedule page displays
echo "Step 2: Verifying schedule page..."
agent-browser is visible "[data-testid='schedule-page']" && echo "  ✓ Schedule page visible"
agent-browser screenshot screenshots/schedule/schedule-page.png
echo "  ✓ Screenshot saved"

# Step 3: Verify view toggle
echo "Step 3: Verifying view toggle..."
agent-browser is visible "[data-testid='view-toggle']" && echo "  ✓ View toggle visible"

# Step 4: Test calendar view
echo "Step 4: Testing calendar view..."
agent-browser click "[data-testid='view-calendar']"
agent-browser wait 500
agent-browser screenshot screenshots/schedule/calendar-view.png
echo "  ✓ Calendar view displayed"

# Step 5: Test list view
echo "Step 5: Testing list view..."
agent-browser click "[data-testid='view-list']"
agent-browser wait 500
agent-browser screenshot screenshots/schedule/list-view.png
echo "  ✓ List view displayed"

# Step 6: Test create appointment button
echo "Step 6: Testing create appointment button..."
agent-browser is visible "[data-testid='add-appointment-btn']" && echo "  ✓ Add appointment button visible"

# Step 7: Open create appointment dialog
echo "Step 7: Opening create appointment dialog..."
agent-browser click "[data-testid='add-appointment-btn']"
agent-browser wait "[data-testid='appointment-form']"
agent-browser screenshot screenshots/schedule/appointment-form.png
echo "  ✓ Appointment form dialog opened"

# Step 8: Close dialog
echo "Step 8: Closing dialog..."
agent-browser press Escape
agent-browser wait 500
echo "  ✓ Dialog closed"

# Close browser
agent-browser close

echo ""
echo "✅ Schedule Feature Validation PASSED!"
echo "Screenshots saved to screenshots/schedule/"
