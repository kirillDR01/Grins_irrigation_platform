#!/bin/bash
# E2E Test: Seed Data Cleanup Verification
# Validates: Requirement 1.7
#
# Navigates to /customers, /staff, /jobs and verifies no demo/test
# seed data names appear in the lists. This confirms the cleanup
# migration successfully removed all seed records.
#
# Usage:
#   bash scripts/e2e/test-seed-data-cleanup.sh [--headed]
#
# Prerequisites:
#   - Frontend running at http://localhost:5173
#   - Backend running at http://localhost:8000
#   - agent-browser installed

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCREENSHOT_DIR="e2e-screenshots/seed-data-cleanup"
BASE_URL="http://localhost:5173"
HEADED_FLAG=""

# Parse arguments
for arg in "$@"; do
  case $arg in
    --headed) HEADED_FLAG="--headed" ;;
  esac
done

mkdir -p "$SCREENSHOT_DIR"

echo "🧪 E2E Test: Seed Data Cleanup Verification (Req 1.7)"
echo "======================================================="

PASS_COUNT=0
FAIL_COUNT=0

# Helper: run a check and track pass/fail
run_check() {
  local description="$1"
  local command="$2"
  if eval "$command" > /dev/null 2>&1; then
    echo "  ✓ $description"
    PASS_COUNT=$((PASS_COUNT + 1))
  else
    echo "  ✗ $description"
    FAIL_COUNT=$((FAIL_COUNT + 1))
  fi
}

# Known demo/test seed data names to check for absence
DEMO_NAMES=("Demo Customer" "Test Staff" "Demo Staff" "Test Customer" "Seed Customer" "Seed Staff" "Jane Demo" "John Demo" "Demo User" "Test User")

# ---------------------------------------------------------------------------
# Step 1: Check /customers for demo names
# ---------------------------------------------------------------------------
echo ""
echo "Step 1: Checking /customers for demo seed data..."
agent-browser $HEADED_FLAG open "${BASE_URL}/customers"
agent-browser wait --load networkidle
agent-browser wait 2000
agent-browser screenshot "$SCREENSHOT_DIR/customers-list.png"
echo "  ✓ Customers page loaded"

# Get the page text content to search for demo names
CUSTOMERS_TEXT=$(agent-browser get text "body" 2>/dev/null || echo "")

CUSTOMERS_CLEAN=true
for name in "${DEMO_NAMES[@]}"; do
  if echo "$CUSTOMERS_TEXT" | grep -qi "$name"; then
    echo "  ✗ FAIL: Found demo name '$name' on /customers page"
    CUSTOMERS_CLEAN=false
    FAIL_COUNT=$((FAIL_COUNT + 1))
  fi
done

if [ "$CUSTOMERS_CLEAN" = true ]; then
  echo "  ✓ No demo names found on /customers page"
  PASS_COUNT=$((PASS_COUNT + 1))
fi

# ---------------------------------------------------------------------------
# Step 2: Check /staff for demo names
# ---------------------------------------------------------------------------
echo ""
echo "Step 2: Checking /staff for demo seed data..."
agent-browser $HEADED_FLAG open "${BASE_URL}/staff"
agent-browser wait --load networkidle
agent-browser wait 2000
agent-browser screenshot "$SCREENSHOT_DIR/staff-list.png"
echo "  ✓ Staff page loaded"

STAFF_TEXT=$(agent-browser get text "body" 2>/dev/null || echo "")

STAFF_CLEAN=true
for name in "${DEMO_NAMES[@]}"; do
  if echo "$STAFF_TEXT" | grep -qi "$name"; then
    echo "  ✗ FAIL: Found demo name '$name' on /staff page"
    STAFF_CLEAN=false
    FAIL_COUNT=$((FAIL_COUNT + 1))
  fi
done

if [ "$STAFF_CLEAN" = true ]; then
  echo "  ✓ No demo names found on /staff page"
  PASS_COUNT=$((PASS_COUNT + 1))
fi

# ---------------------------------------------------------------------------
# Step 3: Check /jobs for demo names
# ---------------------------------------------------------------------------
echo ""
echo "Step 3: Checking /jobs for demo seed data..."
agent-browser $HEADED_FLAG open "${BASE_URL}/jobs"
agent-browser wait --load networkidle
agent-browser wait 2000
agent-browser screenshot "$SCREENSHOT_DIR/jobs-list.png"
echo "  ✓ Jobs page loaded"

JOBS_TEXT=$(agent-browser get text "body" 2>/dev/null || echo "")

JOBS_CLEAN=true
for name in "${DEMO_NAMES[@]}"; do
  if echo "$JOBS_TEXT" | grep -qi "$name"; then
    echo "  ✗ FAIL: Found demo name '$name' on /jobs page"
    JOBS_CLEAN=false
    FAIL_COUNT=$((FAIL_COUNT + 1))
  fi
done

if [ "$JOBS_CLEAN" = true ]; then
  echo "  ✓ No demo names found on /jobs page"
  PASS_COUNT=$((PASS_COUNT + 1))
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "-------------------------------------------------------"
echo "Seed Data Cleanup Results: $PASS_COUNT passed, $FAIL_COUNT failed"
echo "Screenshots saved to: $SCREENSHOT_DIR/"
echo "-------------------------------------------------------"

if [ "$FAIL_COUNT" -gt 0 ]; then
  echo "❌ FAIL: Demo seed data still present"
  exit 1
fi

echo "✅ PASS: No demo seed data found"
exit 0
