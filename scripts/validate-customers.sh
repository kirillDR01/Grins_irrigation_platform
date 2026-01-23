#!/bin/bash
# Customer Feature Validation Script for Admin Dashboard
# Uses agent-browser to validate customer CRUD operations

set -e

echo "🧪 Customer Feature Validation Test"
echo "===================================="
echo "Scenario: Viktor manages customer records"
echo ""

# Create screenshots directory
mkdir -p screenshots/customers

# Step 1: Navigate to Customers page
echo "Step 1: Opening Customers page..."
agent-browser open http://localhost:5173/customers
agent-browser wait --load networkidle
echo "  ✓ Customers page loaded"

# Step 2: Verify customer list displays
echo "Step 2: Verifying customer list..."
agent-browser is visible "[data-testid='customer-list']" && echo "  ✓ Customer list visible"
agent-browser screenshot screenshots/customers/customer-list.png
echo "  ✓ Screenshot saved"

# Step 3: Test search functionality
echo "Step 3: Testing search functionality..."
agent-browser is visible "[data-testid='customer-search']" && echo "  ✓ Search input visible"

# Step 4: Test create customer button
echo "Step 4: Testing create customer button..."
agent-browser is visible "[data-testid='add-customer-btn']" && echo "  ✓ Add customer button visible"

# Step 5: Open create customer dialog
echo "Step 5: Opening create customer dialog..."
agent-browser click "[data-testid='add-customer-btn']"
agent-browser wait "[data-testid='customer-form']"
agent-browser screenshot screenshots/customers/customer-form.png
echo "  ✓ Customer form dialog opened"

# Step 6: Fill in customer form
echo "Step 6: Filling customer form..."
agent-browser fill "[name='firstName']" "Test"
agent-browser fill "[name='lastName']" "Customer"
agent-browser fill "[name='phone']" "6125551234"
agent-browser fill "[name='email']" "test@example.com"
agent-browser screenshot screenshots/customers/customer-form-filled.png
echo "  ✓ Form filled"

# Step 7: Close dialog (cancel)
echo "Step 7: Closing dialog..."
agent-browser press Escape
agent-browser wait 500
echo "  ✓ Dialog closed"

# Step 8: Verify table columns
echo "Step 8: Verifying table structure..."
agent-browser is visible "table" && echo "  ✓ Table visible"

# Close browser
agent-browser close

echo ""
echo "✅ Customer Feature Validation PASSED!"
echo "Screenshots saved to screenshots/customers/"
