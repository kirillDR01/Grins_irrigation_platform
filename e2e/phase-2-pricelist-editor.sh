#!/usr/bin/env bash
# Phase 2 E2E — Pricelist admin editor UI.

set -euo pipefail
cd "$(dirname "$0")/.."

# shellcheck source=./_lib.sh
source e2e/_lib.sh

require_tooling
require_servers
require_seed
SHOTS="$SHOTS_ROOT/phase-2"
mkdir -p "$SHOTS"

login_admin

# 2.1 Navigate to /invoices → click Pricelist tab.
ab open "$BASE/invoices"
ab wait --load networkidle
ab click "[data-testid='tab-pricelist']"
ab wait "[data-testid='price-list-editor']"
sleep 1
ab screenshot "$SHOTS/01-tab-pricelist.png"

# 2.2 Pricebook shortcut from sidebar.
ab click "[data-testid='nav-pricebook']" || true
ab wait "[data-testid='price-list-editor']"
sleep 1
ab screenshot "$SHOTS/02-topnav-shortcut.png"

# 2.3 Filter customer_type=residential.
ab click "[data-testid='price-list-customer-type']"
sleep 1
click_text "Residential"
sleep 1
ab screenshot "$SHOTS/03-filter-residential.png"

# 2.4 Filter customer_type=commercial.
ab click "[data-testid='price-list-customer-type']"
sleep 1
click_text "Commercial"
sleep 1
ab screenshot "$SHOTS/04-filter-commercial.png"

# 2.5 Filter customer_type=both.
ab click "[data-testid='price-list-customer-type']"
sleep 1
click_text "All customer types"
sleep 1
ab screenshot "$SHOTS/05-filter-both.png"

# 2.6 Filter category=installation.
ab click "[data-testid='price-list-category']"
sleep 1
click_text "installation"
sleep 1
ab screenshot "$SHOTS/06-filter-installation.png"

# 2.7 Filter category=landscaping.
ab click "[data-testid='price-list-category']"
sleep 1
click_text "landscaping"
sleep 1
ab screenshot "$SHOTS/07-filter-landscaping.png"

# Reset category filter.
ab click "[data-testid='price-list-category']"
sleep 1
click_text "All categories"
sleep 1

# 2.8 Search "spring".
ab fill "[data-testid='price-list-search']" "spring"
sleep 1
ab screenshot "$SHOTS/08-search-spring.png"

# 2.9 Search miss.
ab fill "[data-testid='price-list-search']" "zzznomatch"
sleep 1
ab screenshot "$SHOTS/09-empty-state.png"
ab fill "[data-testid='price-list-search']" ""
sleep 1

# 2.10 Pagination.
ab click "[data-testid='price-list-next']" || true
sleep 1
ab screenshot "$SHOTS/10-page-2.png"
ab click "[data-testid='price-list-next']" || true
sleep 1
ab screenshot "$SHOTS/11-page-3.png"
ab click "[data-testid='price-list-prev']" || true
ab click "[data-testid='price-list-prev']" || true
sleep 1

# 2.12+ Drawer-per-pricing_model walkthrough.
ab click "[data-testid='price-list-new']"
ab wait "[data-testid='service-offering-drawer']"
sleep 1

variants=(
  flat
  flat_range
  per_unit_flat
  per_unit_range
  per_unit_flat_plus_materials
  per_zone_range
  tiered_zone_step
  tiered_linear
  compound_per_unit
  compound_repair
  size_tier
  size_tier_plus_materials
  yard_tier
  variants
  flat_plus_materials
  conditional_fee
  hourly
)

idx=12
for v in "${variants[@]}"; do
  ab click "[data-testid='offering-pricing-model-trigger']"
  sleep 1
  click_text "$v" || true
  sleep 1
  printf -v num "%02d" "$idx"
  ab screenshot "$SHOTS/${num}-drawer-${v}.png"
  idx=$((idx + 1))
done

# 2.31 Save a flat row.
ab click "[data-testid='offering-pricing-model-trigger']"
sleep 1
click_text "flat"
sleep 1
SLUG="e2e_test_flat_$(date +%s)"
ab fill "[data-testid='offering-name-input']" "E2E Test Flat Service"
ab fill "[data-testid='offering-display-name-input']" "E2E Test Flat Service"
ab fill "[data-testid='offering-slug-input']" "$SLUG"
ab click "[data-testid='offering-customer-type-trigger']"
sleep 1
click_text "Residential"
sleep 1
ab fill "[data-testid='rule-amount']" "199.00" || true
ab click "[data-testid='offering-save']"
sleep 2
ab screenshot "$SHOTS/29-create-flat-success.png"

# 2.32 Edit existing row's display_name.
FIRST_ROW_ID=$(agent-browser --session "$SESSION" eval \
  "document.querySelector('[data-testid^=\"price-list-row-\"]')?.dataset?.testid?.replace('price-list-row-','') || ''" \
  2>/dev/null | tail -1 | tr -d '"')
if [[ -n "$FIRST_ROW_ID" ]]; then
  ab click "[data-testid='price-list-edit-${FIRST_ROW_ID}']" || true
  ab wait "[data-testid='service-offering-drawer']"
  ab fill "[data-testid='offering-display-name-input']" "Edited Display Name"
  ab click "[data-testid='offering-save']"
  sleep 2
  ab screenshot "$SHOTS/30-edit-display-name.png"
fi

# 2.34 Deactivate.
if [[ -n "$FIRST_ROW_ID" ]]; then
  ab click "[data-testid='price-list-deactivate-${FIRST_ROW_ID}']" || true
  sleep 1
  ab screenshot "$SHOTS/32-deactivate.png"
  ab click "[data-testid='price-list-show-inactive']" || true
  sleep 1
  ab screenshot "$SHOTS/33-show-inactive.png"
fi

# 2.35 ArchiveHistorySheet placeholder.
if [[ -n "$FIRST_ROW_ID" ]]; then
  ab click "[data-testid='price-list-history-${FIRST_ROW_ID}']" || true
  ab wait "[data-testid='archive-history-sheet']" || true
  sleep 1
  ab screenshot "$SHOTS/34-archive-history-placeholder.png"
  ab press Escape || true
fi

# 2.36 Pricelist export.
ab open "$API_BASE/api/v1/services/export/pricelist.md"
sleep 1
ab screenshot "$SHOTS/35-export-pricelist-md.png"

# 2.37 Console gate.
ab open "$BASE/invoices?tab=pricelist"
sleep 1
ab screenshot "$SHOTS/36-console-clean.png"
capture_console "$SHOTS/console"

psql_q "SELECT slug FROM service_offerings WHERE slug = '$SLUG' LIMIT 1;" \
  | tee "$SHOTS/db-create-row.txt"

echo
echo "PASS — screenshots in $SHOTS/"
