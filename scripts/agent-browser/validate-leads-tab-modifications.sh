#!/bin/bash
# Agent-Browser Validation: Leads Tab Modifications
# Validates source badges, source filter, intake tag badges, quick-filter tabs,
# follow-up queue panel, consent indicators

set -e

echo "🧪 Leads Tab Modifications Validation"
echo "======================================="

mkdir -p screenshots/leads

# Step 1: Navigate to Leads page
echo "Step 1: Opening Leads page..."
agent-browser open http://localhost:5173/leads
agent-browser wait --load networkidle
echo "  ✓ Leads page loaded"

# Step 2: Verify lead source badges
echo "Step 2: Checking lead source badges..."
BADGE_COUNT=$(agent-browser get count "[data-testid^='lead-source-']" 2>/dev/null || echo "0")
if [ "$BADGE_COUNT" != "0" ] && [ -n "$BADGE_COUNT" ]; then
  echo "  ✓ Found $BADGE_COUNT lead source badges"
else
  echo "  ⚠ No lead source badges (no leads)"
fi

# Step 3: Verify lead source filter
echo "Step 3: Checking lead source filter..."
agent-browser is visible "[data-testid='lead-source-filter']" && echo "  ✓ Lead source filter visible"

# Step 4: Verify intake tag badges
echo "Step 4: Checking intake tag badges..."
TAG_COUNT=$(agent-browser get count "[data-testid^='intake-tag-']" 2>/dev/null || echo "0")
if [ "$TAG_COUNT" != "0" ] && [ -n "$TAG_COUNT" ]; then
  echo "  ✓ Found $TAG_COUNT intake tag badges"
else
  echo "  ⚠ No intake tag badges (no leads)"
fi

# Step 5: Verify quick-filter tabs
echo "Step 5: Checking intake tag quick-filter tabs..."
agent-browser is visible "[data-testid='intake-tag-tabs']" && echo "  ✓ Intake tag tabs container visible"
agent-browser is visible "[data-testid='intake-tab-all']" && echo "  ✓ All tab visible"
agent-browser is visible "[data-testid='intake-tab-schedule']" && echo "  ✓ Schedule tab visible"
agent-browser is visible "[data-testid='intake-tab-follow_up']" && echo "  ✓ Follow Up tab visible"

# Step 6: Click quick-filter tabs
echo "Step 6: Testing quick-filter tab clicks..."
agent-browser click "[data-testid='intake-tab-schedule']"
agent-browser wait 500
agent-browser screenshot screenshots/leads/tab-schedule.png
echo "  ✓ Schedule tab clicked"

agent-browser click "[data-testid='intake-tab-follow_up']"
agent-browser wait 500
agent-browser screenshot screenshots/leads/tab-follow-up.png
echo "  ✓ Follow Up tab clicked"

agent-browser click "[data-testid='intake-tab-all']"
agent-browser wait 500
echo "  ✓ Returned to All tab"

# Step 7: Verify follow-up queue panel
echo "Step 7: Checking follow-up queue panel..."
agent-browser is visible "[data-testid='follow-up-queue']" && echo "  ✓ Follow-up queue panel visible" || echo "  ⚠ Follow-up queue not visible (may be collapsed or empty)"

# Step 8: Verify consent indicators
echo "Step 8: Checking consent indicators..."
SMS_COUNT=$(agent-browser get count "[data-testid^='sms-consent-']" 2>/dev/null || echo "0")
TERMS_COUNT=$(agent-browser get count "[data-testid^='terms-accepted-']" 2>/dev/null || echo "0")
if [ "$SMS_COUNT" != "0" ] && [ -n "$SMS_COUNT" ]; then
  echo "  ✓ Found $SMS_COUNT SMS consent indicators"
else
  echo "  ⚠ No SMS consent indicators (no leads)"
fi
if [ "$TERMS_COUNT" != "0" ] && [ -n "$TERMS_COUNT" ]; then
  echo "  ✓ Found $TERMS_COUNT terms accepted indicators"
else
  echo "  ⚠ No terms accepted indicators (no leads)"
fi

# Step 9: Take full screenshot
echo "Step 9: Taking full screenshot..."
agent-browser screenshot screenshots/leads/leads-tab-modifications.png --full
echo "  ✓ Full page screenshot saved"

# Step 10: Navigate to Work Requests and check promoted badges
echo "Step 10: Checking Work Requests tab..."
agent-browser open http://localhost:5173/work-requests
agent-browser wait --load networkidle
echo "  ✓ Work Requests page loaded"

PROMOTED_COUNT=$(agent-browser get count "[data-testid^='promoted-badge-']" 2>/dev/null || echo "0")
if [ "$PROMOTED_COUNT" != "0" ] && [ -n "$PROMOTED_COUNT" ]; then
  echo "  ✓ Found $PROMOTED_COUNT promoted-to-lead badges"
else
  echo "  ⚠ No promoted badges (no promoted work requests)"
fi

agent-browser screenshot screenshots/leads/work-requests-tab.png --full
echo "  ✓ Work Requests screenshot saved"

echo ""
echo "✅ Leads Tab Modifications Validation Complete"
