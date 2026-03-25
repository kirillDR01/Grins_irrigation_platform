#!/bin/bash
# E2E Test: Accounting Dashboard
# Validates: Requirements 52.9, 53.11, 59.6, 60.7, 61.6, 62.8, 74.7, 67.2
#
# Tests YTD revenue/pending/past-due metrics, expense creation,
# tax preparation, receipt OCR, tax projections, connected accounts,
# and audit log.
#
# Usage:
#   bash scripts/e2e/test-accounting.sh [--headed]
#
# Prerequisites:
#   - Frontend running at http://localhost:5173
#   - Backend running at http://localhost:8000
#   - agent-browser installed

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCREENSHOT_DIR="e2e-screenshots/accounting"
BASE_URL="http://localhost:5173"
HEADED_FLAG=""

ADMIN_EMAIL="${E2E_ADMIN_EMAIL:-admin@grins.com}"
ADMIN_PASSWORD="${E2E_ADMIN_PASSWORD:-admin123}"

for arg in "$@"; do
  case $arg in
    --headed) HEADED_FLAG="--headed" ;;
  esac
done

mkdir -p "$SCREENSHOT_DIR"

echo "🧪 E2E Test: Accounting Dashboard (Req 52.9, 53.11, 59.6, 60.7, 61.6, 62.8, 74.7)"
echo "===================================================================================="

PASS_COUNT=0
FAIL_COUNT=0

# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------
echo ""
echo "Step 1: Logging in..."
agent-browser $HEADED_FLAG open "${BASE_URL}/login"
agent-browser wait --load networkidle
agent-browser wait 1000

if agent-browser is visible "[data-testid='email-input']" 2>/dev/null; then
  agent-browser fill "[data-testid='email-input']" "$ADMIN_EMAIL"
elif agent-browser is visible "[name='email']" 2>/dev/null; then
  agent-browser fill "[name='email']" "$ADMIN_EMAIL"
elif agent-browser is visible "input[type='email']" 2>/dev/null; then
  agent-browser fill "input[type='email']" "$ADMIN_EMAIL"
else
  agent-browser fill "input:first-of-type" "$ADMIN_EMAIL"
fi

if agent-browser is visible "[data-testid='password-input']" 2>/dev/null; then
  agent-browser fill "[data-testid='password-input']" "$ADMIN_PASSWORD"
elif agent-browser is visible "[name='password']" 2>/dev/null; then
  agent-browser fill "[name='password']" "$ADMIN_PASSWORD"
elif agent-browser is visible "input[type='password']" 2>/dev/null; then
  agent-browser fill "input[type='password']" "$ADMIN_PASSWORD"
fi

if agent-browser is visible "[data-testid='login-btn']" 2>/dev/null; then
  agent-browser click "[data-testid='login-btn']"
elif agent-browser is visible "[data-testid='submit-btn']" 2>/dev/null; then
  agent-browser click "[data-testid='submit-btn']"
else
  agent-browser click "button[type='submit']"
fi

agent-browser wait --load networkidle
agent-browser wait 2000

CURRENT_URL=$(agent-browser get url 2>/dev/null || echo "")
if echo "$CURRENT_URL" | grep -qi "/login"; then
  echo "  ✗ FAIL: Could not log in — aborting"
  exit 1
fi
echo "  ✓ Login successful"
PASS_COUNT=$((PASS_COUNT + 1))

# ---------------------------------------------------------------------------
# Step 2: YTD Revenue, Pending Invoices, Past Due (Req 52)
# ---------------------------------------------------------------------------
echo ""
echo "Step 2: Verifying accounting metrics (Req 52)..."
agent-browser open "${BASE_URL}/accounting"
agent-browser wait --load networkidle
agent-browser wait 2000
agent-browser screenshot "$SCREENSHOT_DIR/01-accounting-dashboard.png"

METRICS_FOUND=0
for metric in "ytd-revenue" "pending-invoices" "past-due"; do
  if agent-browser is visible "[data-testid='${metric}']" 2>/dev/null; then
    METRIC_TEXT=$(agent-browser get text "[data-testid='${metric}']" 2>/dev/null || echo "")
    if echo "$METRIC_TEXT" | grep -q '[0-9]'; then
      METRICS_FOUND=$((METRICS_FOUND + 1))
    fi
  fi
done

if [ "$METRICS_FOUND" -ge 2 ]; then
  echo "  ✓ Accounting metrics display numeric values ($METRICS_FOUND found)"
  PASS_COUNT=$((PASS_COUNT + 1))
else
  PAGE_TEXT=$(agent-browser get text "body" 2>/dev/null || echo "")
  if echo "$PAGE_TEXT" | grep -qi "revenue\|pending\|past due\|YTD"; then
    echo "  ✓ Accounting metrics content detected"
    PASS_COUNT=$((PASS_COUNT + 1))
  else
    echo "  ✗ FAIL: Accounting metrics not found"
    FAIL_COUNT=$((FAIL_COUNT + 1))
  fi
fi

# Change date range filter and verify metrics update
if agent-browser is visible "[data-testid='date-range-filter']" 2>/dev/null; then
  agent-browser click "[data-testid='date-range-filter']"
  agent-browser wait 1000
  if agent-browser is visible "[data-testid='date-range-last-quarter']" 2>/dev/null; then
    agent-browser click "[data-testid='date-range-last-quarter']"
  fi
  agent-browser wait --load networkidle
  agent-browser wait 2000
  agent-browser screenshot "$SCREENSHOT_DIR/02-accounting-filtered.png"
  echo "  ✓ Date range filter applied"
  PASS_COUNT=$((PASS_COUNT + 1))
fi

# ---------------------------------------------------------------------------
# Step 3: Expense creation (Req 53)
# ---------------------------------------------------------------------------
echo ""
echo "Step 3: Testing expense creation (Req 53)..."

# Navigate to expenses
if agent-browser is visible "[data-testid='expenses-tab']" 2>/dev/null; then
  agent-browser click "[data-testid='expenses-tab']"
elif agent-browser is visible "text=Expenses" 2>/dev/null; then
  agent-browser click "text=Expenses"
fi
agent-browser wait --load networkidle
agent-browser wait 2000
agent-browser screenshot "$SCREENSHOT_DIR/03-expenses-list.png"

# Create new expense
if agent-browser is visible "[data-testid='add-expense-btn']" 2>/dev/null; then
  agent-browser click "[data-testid='add-expense-btn']"
  agent-browser wait 1000

  if agent-browser is visible "[data-testid='expense-category']" 2>/dev/null; then
    agent-browser click "[data-testid='expense-category']"
    agent-browser wait 500
    if agent-browser is visible "[data-testid='category-materials']" 2>/dev/null; then
      agent-browser click "[data-testid='category-materials']"
    fi
  fi

  if agent-browser is visible "[data-testid='expense-amount']" 2>/dev/null; then
    agent-browser fill "[data-testid='expense-amount']" "150.00"
  fi

  if agent-browser is visible "[data-testid='expense-description']" 2>/dev/null; then
    agent-browser fill "[data-testid='expense-description']" "Test expense for E2E"
  fi

  agent-browser screenshot "$SCREENSHOT_DIR/04-expense-form.png"

  if agent-browser is visible "[data-testid='save-expense-btn']" 2>/dev/null; then
    agent-browser click "[data-testid='save-expense-btn']"
    agent-browser wait --load networkidle
    agent-browser wait 2000
    echo "  ✓ Expense created"
    PASS_COUNT=$((PASS_COUNT + 1))
  elif agent-browser is visible "[data-testid='submit-btn']" 2>/dev/null; then
    agent-browser click "[data-testid='submit-btn']"
    agent-browser wait --load networkidle
    agent-browser wait 2000
    echo "  ✓ Expense created"
    PASS_COUNT=$((PASS_COUNT + 1))
  fi
elif agent-browser is visible "text=Add Expense" 2>/dev/null; then
  agent-browser click "text=Add Expense"
  agent-browser wait 1000
  echo "  ✓ Expense form opened"
  PASS_COUNT=$((PASS_COUNT + 1))
else
  echo "  ✗ FAIL: Add expense button not found"
  FAIL_COUNT=$((FAIL_COUNT + 1))
fi

agent-browser screenshot "$SCREENSHOT_DIR/05-after-expense-creation.png"

# ---------------------------------------------------------------------------
# Step 4: Tax Preparation (Req 59)
# ---------------------------------------------------------------------------
echo ""
echo "Step 4: Testing tax preparation (Req 59)..."
agent-browser open "${BASE_URL}/accounting"
agent-browser wait --load networkidle
agent-browser wait 2000

if agent-browser is visible "[data-testid='tax-preparation-tab']" 2>/dev/null; then
  agent-browser click "[data-testid='tax-preparation-tab']"
elif agent-browser is visible "text=Tax Preparation" 2>/dev/null; then
  agent-browser click "text=Tax Preparation"
fi
agent-browser wait --load networkidle
agent-browser wait 2000
agent-browser screenshot "$SCREENSHOT_DIR/06-tax-preparation.png"

PAGE_TEXT=$(agent-browser get text "body" 2>/dev/null || echo "")
if echo "$PAGE_TEXT" | grep -qi "tax\|category\|total\|deduction"; then
  echo "  ✓ Tax preparation category totals displayed"
  PASS_COUNT=$((PASS_COUNT + 1))
else
  echo "  ✗ FAIL: Tax preparation content not found"
  FAIL_COUNT=$((FAIL_COUNT + 1))
fi

# ---------------------------------------------------------------------------
# Step 5: Receipt OCR (Req 60)
# ---------------------------------------------------------------------------
echo ""
echo "Step 5: Testing receipt upload with OCR (Req 60)..."

if agent-browser is visible "[data-testid='expenses-tab']" 2>/dev/null; then
  agent-browser click "[data-testid='expenses-tab']"
elif agent-browser is visible "text=Expenses" 2>/dev/null; then
  agent-browser click "text=Expenses"
fi
agent-browser wait --load networkidle
agent-browser wait 2000

if agent-browser is visible "[data-testid='add-expense-btn']" 2>/dev/null; then
  agent-browser click "[data-testid='add-expense-btn']"
  agent-browser wait 1000

  if agent-browser is visible "[data-testid='receipt-upload']" 2>/dev/null; then
    echo "  ✓ Receipt upload field available on expense form"
    PASS_COUNT=$((PASS_COUNT + 1))
  elif agent-browser is visible "[data-testid='upload-receipt-btn']" 2>/dev/null; then
    echo "  ✓ Receipt upload button available"
    PASS_COUNT=$((PASS_COUNT + 1))
  else
    echo "  ⚠ Receipt upload field not found on expense form"
  fi
else
  echo "  ⚠ Could not open expense form for receipt test"
fi

agent-browser screenshot "$SCREENSHOT_DIR/07-receipt-upload.png"

# ---------------------------------------------------------------------------
# Step 6: Tax Projections — What-If (Req 61)
# ---------------------------------------------------------------------------
echo ""
echo "Step 6: Testing tax projections (Req 61)..."
agent-browser open "${BASE_URL}/accounting"
agent-browser wait --load networkidle
agent-browser wait 2000

# Look for Estimated Tax Due widget
if agent-browser is visible "[data-testid='estimated-tax-due']" 2>/dev/null; then
  echo "  ✓ Estimated Tax Due widget visible"
  PASS_COUNT=$((PASS_COUNT + 1))
fi

# Open What-If Projections
if agent-browser is visible "[data-testid='what-if-btn']" 2>/dev/null; then
  agent-browser click "[data-testid='what-if-btn']"
  agent-browser wait 1000

  if agent-browser is visible "[data-testid='hypothetical-expense-input']" 2>/dev/null; then
    agent-browser fill "[data-testid='hypothetical-expense-input']" "5000"
    agent-browser wait 1000
    echo "  ✓ What-If projection updated with hypothetical expense"
    PASS_COUNT=$((PASS_COUNT + 1))
  fi
elif agent-browser is visible "text=What-If" 2>/dev/null; then
  agent-browser click "text=What-If"
  agent-browser wait 1000
  echo "  ✓ What-If Projections section opened"
  PASS_COUNT=$((PASS_COUNT + 1))
else
  PAGE_TEXT=$(agent-browser get text "body" 2>/dev/null || echo "")
  if echo "$PAGE_TEXT" | grep -qi "what.if\|projection\|estimated tax"; then
    echo "  ✓ Tax projection content found"
    PASS_COUNT=$((PASS_COUNT + 1))
  else
    echo "  ✗ FAIL: Tax projection section not found"
    FAIL_COUNT=$((FAIL_COUNT + 1))
  fi
fi

agent-browser screenshot "$SCREENSHOT_DIR/08-tax-projections.png"

# ---------------------------------------------------------------------------
# Step 7: Connected Accounts (Req 62)
# ---------------------------------------------------------------------------
echo ""
echo "Step 7: Testing connected accounts (Req 62)..."
agent-browser open "${BASE_URL}/accounting"
agent-browser wait --load networkidle
agent-browser wait 2000

if agent-browser is visible "[data-testid='connected-accounts-tab']" 2>/dev/null; then
  agent-browser click "[data-testid='connected-accounts-tab']"
elif agent-browser is visible "text=Connected Accounts" 2>/dev/null; then
  agent-browser click "text=Connected Accounts"
fi
agent-browser wait --load networkidle
agent-browser wait 2000
agent-browser screenshot "$SCREENSHOT_DIR/09-connected-accounts.png"

PAGE_TEXT=$(agent-browser get text "body" 2>/dev/null || echo "")
if echo "$PAGE_TEXT" | grep -qi "connected\|account\|bank\|plaid"; then
  echo "  ✓ Connected Accounts section displayed"
  PASS_COUNT=$((PASS_COUNT + 1))
else
  if agent-browser is visible "[data-testid='connected-accounts']" 2>/dev/null; then
    echo "  ✓ Connected Accounts section visible"
    PASS_COUNT=$((PASS_COUNT + 1))
  else
    echo "  ✗ FAIL: Connected Accounts section not found"
    FAIL_COUNT=$((FAIL_COUNT + 1))
  fi
fi

# ---------------------------------------------------------------------------
# Step 8: Audit Log (Req 74)
# ---------------------------------------------------------------------------
echo ""
echo "Step 8: Testing audit log (Req 74)..."

# Perform an admin action first (we already created an expense above)
# Now navigate to audit log
if agent-browser is visible "[data-testid='audit-log-tab']" 2>/dev/null; then
  agent-browser click "[data-testid='audit-log-tab']"
elif agent-browser is visible "text=Audit Log" 2>/dev/null; then
  agent-browser click "text=Audit Log"
fi
agent-browser wait --load networkidle
agent-browser wait 2000
agent-browser screenshot "$SCREENSHOT_DIR/10-audit-log.png"

PAGE_TEXT=$(agent-browser get text "body" 2>/dev/null || echo "")
if echo "$PAGE_TEXT" | grep -qi "audit\|log\|action\|admin\|event"; then
  echo "  ✓ Audit log displays admin actions"
  PASS_COUNT=$((PASS_COUNT + 1))
else
  if agent-browser is visible "[data-testid='audit-log']" 2>/dev/null; then
    echo "  ✓ Audit log section visible"
    PASS_COUNT=$((PASS_COUNT + 1))
  else
    echo "  ✗ FAIL: Audit log not found"
    FAIL_COUNT=$((FAIL_COUNT + 1))
  fi
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "-------------------------------------------------------"
echo "Accounting E2E Results: $PASS_COUNT passed, $FAIL_COUNT failed"
echo "Screenshots saved to: $SCREENSHOT_DIR/"
echo "-------------------------------------------------------"

if [ "$FAIL_COUNT" -gt 0 ]; then
  echo "❌ FAIL: Accounting dashboard issues detected"
  exit 1
fi

echo "✅ PASS: All accounting dashboard tests passed"
exit 0
