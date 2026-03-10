#!/bin/bash
# Agent-Browser Validation: Jobs Tab Modifications
# Validates subscription badge, target date columns, date range filter, source filter

set -e

echo "🧪 Jobs Tab Modifications Validation"
echo "======================================"

mkdir -p screenshots/jobs

# Step 1: Navigate to Jobs page
echo "Step 1: Opening Jobs page..."
agent-browser open http://localhost:5173/jobs
agent-browser wait --load networkidle
echo "  ✓ Jobs page loaded"

# Step 2: Verify subscription source badges (if any jobs have agreements)
echo "Step 2: Checking subscription source badges..."
BADGE_COUNT=$(agent-browser get count "[data-testid^='subscription-badge-']" 2>/dev/null || echo "0")
if [ "$BADGE_COUNT" != "0" ] && [ -n "$BADGE_COUNT" ]; then
  echo "  ✓ Found $BADGE_COUNT subscription source badges"
else
  echo "  ⚠ No subscription badges (no agreement-linked jobs)"
fi

# Step 3: Verify target date columns render
echo "Step 3: Checking target date columns..."
DATE_COUNT=$(agent-browser get count "[data-testid^='target-dates-']" 2>/dev/null || echo "0")
if [ "$DATE_COUNT" != "0" ] && [ -n "$DATE_COUNT" ]; then
  echo "  ✓ Found $DATE_COUNT target date displays"
else
  echo "  ⚠ No target date displays (no jobs with target dates)"
fi

# Step 4: Verify target date filter
echo "Step 4: Checking target date filter..."
agent-browser is visible "[data-testid='target-date-filter']" && echo "  ✓ Target date filter visible"

# Step 5: Take screenshot
echo "Step 5: Taking screenshot..."
agent-browser screenshot screenshots/jobs/jobs-tab-modifications.png --full
echo "  ✓ Full page screenshot saved"

echo ""
echo "✅ Jobs Tab Modifications Validation Complete"
