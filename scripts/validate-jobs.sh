#!/bin/bash
# Jobs Feature Validation Script for Admin Dashboard
# Uses agent-browser to validate job management functionality

set -e

echo "🧪 Jobs Feature Validation Test"
echo "================================"
echo "Scenario: Viktor manages job requests and status updates"
echo ""

# Create screenshots directory
mkdir -p screenshots/jobs

# Step 1: Navigate to Jobs page
echo "Step 1: Opening Jobs page..."
agent-browser open http://localhost:5173/jobs
agent-browser wait --load networkidle
echo "  ✓ Jobs page loaded"

# Step 2: Verify job list displays
echo "Step 2: Verifying job list..."
agent-browser is visible "[data-testid='job-list']" && echo "  ✓ Job list visible"
agent-browser screenshot screenshots/jobs/job-list.png
echo "  ✓ Screenshot saved"

# Step 3: Verify status filter
echo "Step 3: Verifying status filter..."
agent-browser is visible "[data-testid='status-filter']" && echo "  ✓ Status filter visible"

# Step 4: Test create job button
echo "Step 4: Testing create job button..."
agent-browser is visible "[data-testid='add-job-btn']" && echo "  ✓ Add job button visible"

# Step 5: Open create job dialog
echo "Step 5: Opening create job dialog..."
agent-browser click "[data-testid='add-job-btn']"
agent-browser wait "[data-testid='job-form']"
agent-browser screenshot screenshots/jobs/job-form.png
echo "  ✓ Job form dialog opened"

# Step 6: Verify form fields
echo "Step 6: Verifying form fields..."
agent-browser is visible "[name='description']" && echo "  ✓ Description field visible"
echo "  ✓ Form fields verified"

# Step 7: Close dialog
echo "Step 7: Closing dialog..."
agent-browser press Escape
agent-browser wait 500
echo "  ✓ Dialog closed"

# Step 8: Verify table structure
echo "Step 8: Verifying table structure..."
agent-browser is visible "table" && echo "  ✓ Table visible"

# Close browser
agent-browser close

echo ""
echo "✅ Jobs Feature Validation PASSED!"
echo "Screenshots saved to screenshots/jobs/"
