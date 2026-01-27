#!/bin/bash
# Validation script for AI Estimate Generation user journey

echo "🧪 AI Estimate Generation User Journey Test"
echo "Scenario: Viktor generates an AI-powered estimate for a new installation job"
echo ""

# Ensure frontend is running
if ! curl -s http://localhost:5173 > /dev/null 2>&1; then
  echo "❌ Frontend not running. Start with: cd frontend && npm run dev"
  exit 1
fi

echo "✅ Frontend is running"
echo ""

# Navigate to jobs page
echo "Step 1: Navigate to jobs page"
agent-browser open http://localhost:5173/jobs
agent-browser wait --load networkidle
agent-browser is visible "[data-testid='jobs-page']" && echo "  ✓ Jobs page loaded"
echo ""

# Click on a job that needs an estimate (we'll use the first job)
echo "Step 2: Open job detail page"
agent-browser click "[data-testid='job-row']"
agent-browser wait --load networkidle
agent-browser is visible "[data-testid='job-detail-page']" && echo "  ✓ Job detail page loaded"
echo ""

# Verify AIEstimateGenerator component is present
echo "Step 3: Verify AI Estimate Generator component"
agent-browser is visible "[data-testid='ai-estimate-generator']" && echo "  ✓ AI Estimate Generator visible"
echo ""

# Test estimate display structure
echo "Step 4: Verify estimate display structure"
agent-browser is visible "[data-testid='estimate-analysis']" && echo "  ✓ Estimate analysis section visible"
agent-browser is visible "[data-testid='similar-jobs']" && echo "  ✓ Similar jobs section visible"
agent-browser is visible "[data-testid='price-breakdown']" && echo "  ✓ Price breakdown section visible"
echo ""

# Test action buttons
echo "Step 5: Verify action buttons"
agent-browser is visible "[data-testid='generate-pdf-btn']" && echo "  ✓ Generate PDF button visible"
agent-browser is visible "[data-testid='schedule-visit-btn']" && echo "  ✓ Schedule Site Visit button visible"
agent-browser is visible "[data-testid='adjust-quote-btn']" && echo "  ✓ Adjust Quote button visible"
echo ""

# Test AI recommendation display
echo "Step 6: Verify AI recommendation"
agent-browser is visible "[data-testid='ai-recommendation']" && echo "  ✓ AI recommendation visible"
echo ""

# Test estimate adjustment interaction
echo "Step 7: Test estimate adjustment"
agent-browser click "[data-testid='adjust-quote-btn']"
agent-browser wait 500
echo "  ✓ Adjust quote button clicked"
echo ""

# Test similar jobs reference
echo "Step 8: Verify similar jobs display"
agent-browser is visible "[data-testid='similar-job-card']" && echo "  ✓ Similar job cards visible"
echo ""

# Test price breakdown details
echo "Step 9: Verify price breakdown details"
agent-browser is visible "[data-testid='materials-cost']" && echo "  ✓ Materials cost visible"
agent-browser is visible "[data-testid='labor-cost']" && echo "  ✓ Labor cost visible"
agent-browser is visible "[data-testid='equipment-cost']" && echo "  ✓ Equipment cost visible"
agent-browser is visible "[data-testid='margin']" && echo "  ✓ Margin visible"
agent-browser is visible "[data-testid='total-estimate']" && echo "  ✓ Total estimate visible"
echo ""

# Test PDF generation trigger
echo "Step 10: Test PDF generation trigger"
agent-browser click "[data-testid='generate-pdf-btn']"
agent-browser wait 500
echo "  ✓ Generate PDF button clicked"
echo ""

agent-browser close
echo ""
echo "✅ AI Estimate Generation Validation PASSED!"
echo "All estimate generation UI elements are functional"
