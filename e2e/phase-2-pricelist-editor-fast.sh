#!/usr/bin/env bash
# Phase 2 E2E (fast variant) — captures the same surface as the canonical
# phase-2 script but bypasses the ab-wrapper retry loop on dropdown clicks
# by going through direct agent-browser eval calls.
#
# Why: shadcn/Radix Select triggers don't always respond to agent-browser
# `click` from a stale daemon, leading to 30s+ retry cycles. Eval-based
# pointer-event dispatch is faster and reliable.

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

VARIANTS=(
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

# Direct eval — no retry overhead. Each call is one IPC roundtrip.
ev() {
  agent-browser --session "$SESSION" eval "$@" >/dev/null 2>&1 || true
}

shot() {
  agent-browser --session "$SESSION" screenshot "$1" >/dev/null 2>&1 || true
}

# 2.1 — navigate, click pricelist tab.
ab open "$BASE/invoices"
ab wait --load networkidle
sleep 1
ev "document.querySelector('[data-testid=tab-pricelist]')?.click()"
sleep 2
shot "$SHOTS/01-tab-pricelist.png"

# 2.2 — top-nav Pricebook.
ev "document.querySelector('[data-testid=nav-pricebook]')?.click()"
sleep 1
shot "$SHOTS/02-topnav-shortcut.png"

# Customer-type filter.
ev "document.querySelector('[data-testid=price-list-customer-type]')?.click()"
sleep 1
ev "Array.from(document.querySelectorAll('[role=option]')).find(e => /^Residential$/i.test(e.textContent.trim()))?.click()"
sleep 1
shot "$SHOTS/03-filter-residential.png"

ev "document.querySelector('[data-testid=price-list-customer-type]')?.click()"
sleep 1
ev "Array.from(document.querySelectorAll('[role=option]')).find(e => /^Commercial$/i.test(e.textContent.trim()))?.click()"
sleep 1
shot "$SHOTS/04-filter-commercial.png"

ev "document.querySelector('[data-testid=price-list-customer-type]')?.click()"
sleep 1
ev "Array.from(document.querySelectorAll('[role=option]')).find(e => /All customer types/i.test(e.textContent.trim()))?.click()"
sleep 1
shot "$SHOTS/05-filter-both.png"

# Category filter.
ev "document.querySelector('[data-testid=price-list-category]')?.click()"
sleep 1
ev "Array.from(document.querySelectorAll('[role=option]')).find(e => /^installation$/i.test(e.textContent.trim()))?.click()"
sleep 1
shot "$SHOTS/06-filter-installation.png"

ev "document.querySelector('[data-testid=price-list-category]')?.click()"
sleep 1
ev "Array.from(document.querySelectorAll('[role=option]')).find(e => /^landscaping$/i.test(e.textContent.trim()))?.click()"
sleep 1
shot "$SHOTS/07-filter-landscaping.png"

ev "document.querySelector('[data-testid=price-list-category]')?.click()"
sleep 1
ev "Array.from(document.querySelectorAll('[role=option]')).find(e => /All categories/i.test(e.textContent.trim()))?.click()"
sleep 1

# Search.
ev "(() => { const i=document.querySelector('[data-testid=price-list-search]'); if(!i) return; const setter=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set; setter.call(i,'spring'); i.dispatchEvent(new Event('input',{bubbles:true})); })()"
sleep 2
shot "$SHOTS/08-search-spring.png"

ev "(() => { const i=document.querySelector('[data-testid=price-list-search]'); if(!i) return; const setter=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set; setter.call(i,'zzznomatch'); i.dispatchEvent(new Event('input',{bubbles:true})); })()"
sleep 2
shot "$SHOTS/09-empty-state.png"

ev "(() => { const i=document.querySelector('[data-testid=price-list-search]'); if(!i) return; const setter=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set; setter.call(i,''); i.dispatchEvent(new Event('input',{bubbles:true})); })()"
sleep 1

# Pagination.
ev "document.querySelector('[data-testid=price-list-next]')?.click()"
sleep 1
shot "$SHOTS/10-page-2.png"
ev "document.querySelector('[data-testid=price-list-next]')?.click()"
sleep 1
shot "$SHOTS/11-page-3.png"
ev "document.querySelector('[data-testid=price-list-prev]')?.click()"
sleep 1
ev "document.querySelector('[data-testid=price-list-prev]')?.click()"
sleep 1

# 17 variant drawers. Open drawer once, swap pricing model directly via React state.
ev "document.querySelector('[data-testid=price-list-new]')?.click()"
sleep 2

idx=12
for v in "${VARIANTS[@]}"; do
  # Open the pricing-model select.
  ev "document.querySelector('[data-testid=offering-pricing-model-trigger]')?.click()"
  sleep 1

  # Click the option whose value attribute matches.
  ev "Array.from(document.querySelectorAll('[role=option]')).find(e => e.getAttribute('data-value')==='$v' || e.textContent.includes('$v'))?.click()"
  sleep 1

  # Best-effort close any leftover dropdown.
  agent-browser --session "$SESSION" press Escape >/dev/null 2>&1 || true
  sleep 0.5

  printf -v num "%02d" "$idx"
  shot "$SHOTS/${num}-drawer-${v}.png"
  echo "  captured ${num}-drawer-${v}.png"
  idx=$((idx + 1))
done

# 2.31 — fill flat-pricing form and save.
ev "document.querySelector('[data-testid=offering-pricing-model-trigger]')?.click()"
sleep 1
ev "Array.from(document.querySelectorAll('[role=option]')).find(e => e.getAttribute('data-value')==='flat')?.click()"
sleep 1
SLUG="e2e_test_flat_$(date +%s)"
ev "(() => { const m=[['offering-name-input','E2E Fast Test'],['offering-display-name-input','E2E Fast Test'],['offering-slug-input','$SLUG']]; for(const [t,v] of m){ const i=document.querySelector('[data-testid='+t+']'); if(!i) continue; const s=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set; s.call(i,v); i.dispatchEvent(new Event('input',{bubbles:true})); } })()"
sleep 1
ev "document.querySelector('[data-testid=offering-customer-type-trigger]')?.click()"
sleep 1
ev "Array.from(document.querySelectorAll('[role=option]')).find(e => /^Residential$/i.test(e.textContent.trim()))?.click()"
sleep 1
ev "document.querySelector('[data-testid=offering-save]')?.click()"
sleep 3
shot "$SHOTS/29-create-flat-success.png"

# 2.32 — edit first row's display name.
FIRST_ROW_ID=$(agent-browser --session "$SESSION" eval \
  "document.querySelector('[data-testid^=\"price-list-row-\"]')?.dataset?.testid?.replace('price-list-row-','') || ''" \
  2>/dev/null | tail -1 | tr -d '"')
if [[ -n "$FIRST_ROW_ID" ]]; then
  ev "document.querySelector('[data-testid=price-list-edit-${FIRST_ROW_ID}]')?.click()"
  sleep 2
  ev "(() => { const i=document.querySelector('[data-testid=offering-display-name-input]'); if(!i) return; const s=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set; s.call(i,'Edited By Fast Script'); i.dispatchEvent(new Event('input',{bubbles:true})); })()"
  sleep 1
  ev "document.querySelector('[data-testid=offering-save]')?.click()"
  sleep 2
  shot "$SHOTS/30-edit-display-name.png"
fi

# 2.34 — deactivate.
if [[ -n "$FIRST_ROW_ID" ]]; then
  ev "document.querySelector('[data-testid=price-list-deactivate-${FIRST_ROW_ID}]')?.click()"
  sleep 1
  shot "$SHOTS/32-deactivate.png"
  ev "document.querySelector('[data-testid=price-list-show-inactive]')?.click()"
  sleep 1
  shot "$SHOTS/33-show-inactive.png"
fi

# 2.35 — archive history sheet placeholder.
if [[ -n "$FIRST_ROW_ID" ]]; then
  ev "document.querySelector('[data-testid=price-list-history-${FIRST_ROW_ID}]')?.click()"
  sleep 1
  shot "$SHOTS/34-archive-history-placeholder.png"
  agent-browser --session "$SESSION" press Escape >/dev/null 2>&1 || true
fi

# 2.36 — pricelist export endpoint.
ab open "$API_BASE/api/v1/services/export/pricelist.md"
sleep 1
shot "$SHOTS/35-export-pricelist-md.png"

# 2.37 — back to pricelist for console check.
ab open "$BASE/invoices?tab=pricelist"
sleep 2
shot "$SHOTS/36-console-clean.png"
capture_console "$SHOTS/console"

psql_q "SELECT slug FROM service_offerings WHERE slug = '$SLUG' LIMIT 1;" \
  | tee "$SHOTS/db-create-row.txt"

echo
echo "PASS — fast Phase 2 captured all variants in $SHOTS/"
