#!/bin/bash
# Run all validation scripts for Admin Dashboard
# Requires frontend to be running on localhost:5173

set -e

echo "🧪 Admin Dashboard Full Validation Suite"
echo "========================================="
echo ""
echo "Prerequisites:"
echo "  - Frontend running: cd frontend && npm run dev"
echo "  - Backend running: uv run uvicorn grins_platform.main:app --reload"
echo ""

# Check if frontend is running
if ! curl -s http://localhost:5173 > /dev/null 2>&1; then
    echo "❌ Error: Frontend is not running on localhost:5173"
    echo "   Please start the frontend first: cd frontend && npm run dev"
    exit 1
fi

echo "✓ Frontend is running"
echo ""

# Run all validation scripts
echo "Running Layout Validation..."
bash scripts/validate-layout.sh
echo ""

echo "Running Customer Validation..."
bash scripts/validate-customers.sh
echo ""

echo "Running Jobs Validation..."
bash scripts/validate-jobs.sh
echo ""

echo "Running Schedule Validation..."
bash scripts/validate-schedule.sh
echo ""

echo "Running Integration Validation..."
bash scripts/validate-integration.sh
echo ""

echo "========================================="
echo "✅ ALL VALIDATIONS PASSED!"
echo "========================================="
echo ""
echo "Screenshots saved to:"
echo "  - screenshots/layout/"
echo "  - screenshots/customers/"
echo "  - screenshots/jobs/"
echo "  - screenshots/schedule/"
echo "  - screenshots/integration/"
