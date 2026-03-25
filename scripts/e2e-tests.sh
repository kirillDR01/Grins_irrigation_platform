#!/bin/bash
# E2E Test Runner — CRM Gap Closure
# Validates: Requirements 67.1, 67.3, 67.4, 67.5, 67.7
#
# Executes all agent-browser E2E validation scripts sequentially,
# reports pass/fail for each, and outputs a summary report.
#
# Usage:
#   bash scripts/e2e-tests.sh              # run all tests (headless)
#   bash scripts/e2e-tests.sh --headed     # run with visible browser (debugging)
#   bash scripts/e2e-tests.sh --test NAME  # run a single test by name
#
# Prerequisites:
#   - Frontend running at http://localhost:5173
#   - Backend running at http://localhost:8000
#   - agent-browser installed (npm install -g agent-browser)
#
# Exit codes:
#   0 — all tests passed
#   1 — one or more tests failed

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SCREENSHOT_DIR="$PROJECT_ROOT/e2e-screenshots"
HEADED_FLAG=""
SINGLE_TEST=""

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --headed)
      HEADED_FLAG="--headed"
      shift
      ;;
    --test)
      SINGLE_TEST="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1"
      echo "Usage: $0 [--headed] [--test TEST_NAME]"
      exit 1
      ;;
  esac
done

# ---------------------------------------------------------------------------
# Test registry — add new E2E test scripts here
# Format: "name|path|description"
# ---------------------------------------------------------------------------
TESTS=(
  "seed-data-cleanup|scripts/e2e/test-seed-data-cleanup.sh|Verify no demo seed data on /customers, /staff, /jobs (Req 1.7)"
  "session-persistence|scripts/e2e/test-session-persistence.sh|Login, wait, act, verify session stays active (Req 2.7)"
  "dashboard|scripts/e2e/test-dashboard.sh|Dashboard alerts, messages, invoices, job status widgets (Req 3.8, 4.8, 5.5, 6.5)"
  "customers|scripts/e2e/test-customers.sh|Customer duplicates, notes, photos, invoices, service times, payments (Req 7.7, 8.6, 9.9, 10.5, 11.6, 56.9)"
  "leads|scripts/e2e/test-leads.sh|Lead city/address, tags, bulk outreach, attachments, portal estimate, estimate creation, work-requests redirect (Req 12.8, 13.11, 14.8, 15.8, 16.10, 17.9, 18.6, 19.9)"
  "jobs|scripts/e2e/test-jobs.sh|Job summary, notes, simplified statuses, column changes, due-by dates, financials (Req 20.7, 21.6, 22.7, 23.6, 57.5)"
  "schedule|scripts/e2e/test-schedule.sh|Schedule drag-drop, lead time, job filter, inline panel, event labels, address auto-populate, payment, invoice, estimate, notes, review, workflow buttons, duration, enrichment, staff map, breaks (Req 24.8, 25.5, 26.6, 27.4, 28.3, 29.5, 30.9, 31.8, 32.10, 33.8, 34.8, 35.10, 36.7, 37.7, 40.6, 41.8, 42.7)"
  "invoices|scripts/e2e/test-invoices.sh|Invoice bulk notify, reminder status indicators, PDF download (Req 38.8, 54.8, 80.10)"
  "notifications|scripts/e2e/test-notifications.sh|On My Way notification queued on appointment (Req 39.12)"
  "sales|scripts/e2e/test-sales.sh|Sales pipeline, estimate builder, media library, diagram, follow-ups (Req 47.8, 48.10, 49.7, 50.7, 51.9)"
  "accounting|scripts/e2e/test-accounting.sh|Accounting metrics, expenses, tax prep, receipt OCR, projections, connected accounts, audit log (Req 52.9, 53.11, 59.6, 60.7, 61.6, 62.8, 74.7)"
  "marketing|scripts/e2e/test-marketing.sh|Lead sources, campaigns, budget tracking, QR codes, CAC (Req 45.13, 58.6, 63.9, 64.6, 65.6)"
  "navigation-security|scripts/e2e/test-navigation-security.sh|Sidebar nav, rate limit, security headers, auth token, portal security (Req 66.5, 69.6, 70.5, 71.8, 78.9)"
  "agreement-flow|scripts/e2e/test-agreement-flow.sh|Service package tier selection, checkout redirect, agreements display (Req 68.9)"
  "sms-lead|scripts/e2e/test-sms-lead.sh|Lead creation with SMS confirmation logged (Req 46.7)"
  "communications|scripts/e2e/test-communications.sh|Sent messages tab, delivery status badges, customer messages (Req 82.7, 82.8)"
  "estimate-detail|scripts/e2e/test-estimate-detail.sh|Estimate detail line items, status badge, activity timeline, resend (Req 83.8, 83.9)"
  "invoice-portal|scripts/e2e/test-invoice-portal.sh|Portal invoice view, Pay Now button, no internal IDs (Req 84.12)"
  "rate-limit|scripts/e2e/test-rate-limit.sh|Rate limit toast with Too many requests message and wait time (Req 85.6, 85.7)"
  "mobile-staff|scripts/e2e/test-mobile-staff.sh|Mobile viewport workflow buttons, bottom sheet customer panel (Req 86.9, 86.10)"
  "settings|scripts/e2e/test-settings.sh|Business info edit persistence, payment terms default on invoices (Req 87.10, 87.11)"
)

# ---------------------------------------------------------------------------
# Pre-flight checks
# ---------------------------------------------------------------------------
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║          E2E Test Suite — CRM Gap Closure                   ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Check agent-browser
if ! command -v agent-browser &> /dev/null; then
  echo "❌ agent-browser not found. Install with: npm install -g agent-browser"
  exit 1
fi
echo "✓ agent-browser found: $(agent-browser --version 2>/dev/null || echo 'installed')"

# Check frontend
echo -n "Checking frontend at http://localhost:5173... "
if curl -s --max-time 5 http://localhost:5173 > /dev/null 2>&1; then
  echo "✓ running"
else
  echo "✗"
  echo "❌ Frontend is not running on http://localhost:5173"
  echo "   Start it with: cd frontend && npm run dev"
  exit 1
fi

# Check backend
echo -n "Checking backend at http://localhost:8000... "
if curl -s --max-time 5 http://localhost:8000/docs > /dev/null 2>&1 || \
   curl -s --max-time 5 http://localhost:8000/api/v1/health > /dev/null 2>&1 || \
   curl -s --max-time 5 http://localhost:8000 > /dev/null 2>&1; then
  echo "✓ running"
else
  echo "✗"
  echo "❌ Backend is not running on http://localhost:8000"
  echo "   Start it with: uv run uvicorn grins_platform.main:app --reload"
  exit 1
fi

# Create screenshot directory
mkdir -p "$SCREENSHOT_DIR"

if [ -n "$HEADED_FLAG" ]; then
  echo ""
  echo "🖥  Running in HEADED mode (visible browser)"
fi

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo ""

# ---------------------------------------------------------------------------
# Execute tests
# ---------------------------------------------------------------------------
TOTAL=0
PASSED=0
FAILED=0
SKIPPED=0
FAILED_TESTS=()
START_TIME=$(date +%s)

for test_entry in "${TESTS[@]}"; do
  IFS='|' read -r test_name test_path test_desc <<< "$test_entry"

  # If --test flag is set, skip non-matching tests
  if [ -n "$SINGLE_TEST" ] && [ "$test_name" != "$SINGLE_TEST" ]; then
    continue
  fi

  TOTAL=$((TOTAL + 1))

  echo "┌─────────────────────────────────────────────────────────────"
  echo "│ [$TOTAL] $test_name"
  echo "│ $test_desc"
  echo "└─────────────────────────────────────────────────────────────"

  # Check script exists
  if [ ! -f "$PROJECT_ROOT/$test_path" ]; then
    echo "  ⚠ SKIPPED: Script not found at $test_path"
    SKIPPED=$((SKIPPED + 1))
    echo ""
    continue
  fi

  # Run the test script, passing --headed if set
  TEST_START=$(date +%s)
  if bash "$PROJECT_ROOT/$test_path" $HEADED_FLAG; then
    TEST_END=$(date +%s)
    TEST_DURATION=$((TEST_END - TEST_START))
    echo "  ✅ PASSED (${TEST_DURATION}s)"
    PASSED=$((PASSED + 1))
  else
    TEST_END=$(date +%s)
    TEST_DURATION=$((TEST_END - TEST_START))
    echo "  ❌ FAILED (${TEST_DURATION}s)"
    FAILED=$((FAILED + 1))
    FAILED_TESTS+=("$test_name")
    # Take a failure screenshot
    agent-browser screenshot "$SCREENSHOT_DIR/FAILURE-${test_name}.png" 2>/dev/null || true
  fi

  echo ""
done

END_TIME=$(date +%s)
TOTAL_DURATION=$((END_TIME - START_TIME))

# ---------------------------------------------------------------------------
# Summary report (Req 67.3)
# ---------------------------------------------------------------------------
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "📊 E2E Test Suite Summary"
echo "───────────────────────────────────────────────────────────────"
echo "  Total:   $TOTAL"
echo "  Passed:  $PASSED"
echo "  Failed:  $FAILED"
echo "  Skipped: $SKIPPED"
echo "  Time:    ${TOTAL_DURATION}s"
echo "───────────────────────────────────────────────────────────────"

if [ ${#FAILED_TESTS[@]} -gt 0 ]; then
  echo ""
  echo "  Failed tests:"
  for ft in "${FAILED_TESTS[@]}"; do
    echo "    • $ft"
  done
  echo ""
  echo "  Failure screenshots saved to: $SCREENSHOT_DIR/FAILURE-*.png"
fi

echo ""
echo "  All screenshots: $SCREENSHOT_DIR/"
echo ""

if [ "$FAILED" -gt 0 ]; then
  echo "❌ $FAILED of $TOTAL tests FAILED"
  exit 1
fi

if [ "$TOTAL" -eq 0 ]; then
  echo "⚠ No tests were executed"
  if [ -n "$SINGLE_TEST" ]; then
    echo "  Test '$SINGLE_TEST' not found in registry."
    echo "  Available tests:"
    for test_entry in "${TESTS[@]}"; do
      IFS='|' read -r test_name _ _ <<< "$test_entry"
      echo "    • $test_name"
    done
  fi
  exit 1
fi

echo "✅ All $PASSED tests PASSED"
exit 0
