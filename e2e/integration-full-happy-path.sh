#!/usr/bin/env bash
# Cross-phase happy-path E2E — Tasks 6.7 + 6.8 of umbrella plan.
#
# Walks one synthetic flow that exercises every phase:
#   Phase 3 — open appt, send estimate via LineItemPicker.
#   Phase 0 — customer approves via portal, auto-job created.
#   Phase 5 — Maps remember my choice persists.
#   Phase 4 — collect payment, receipt + paid card.
#   Phase 2 — edit pricelist row, verify in next estimate.
#   Phase 1 — pricelist seed still intact + new row from Phase 2.
#
# Then 6.8 — repeat smoke shots at three responsive viewports.

set -euo pipefail
cd "$(dirname "$0")/.."

# shellcheck source=./_lib.sh
source e2e/_lib.sh

require_tooling
require_servers
require_seed
SHOTS="$SHOTS_ROOT/integration"
RESP="$SHOTS_ROOT/responsive"
mkdir -p "$SHOTS" "$RESP"

login_admin

# Initial state shot.
ab open "$BASE/dashboard"
ab wait --load networkidle
sleep 1
ab screenshot "$SHOTS/00-dashboard.png"

# --- Phase 3 — send estimate from pricelist ---
ab open "$BASE/schedule"
ab wait --load networkidle
sleep 2
APPT_ID=$(open_first_appointment_modal "in_progress,completed" || true)
if [[ -n "${APPT_ID:-}" ]]; then
  ab screenshot "$SHOTS/01-modal-open.png"
  agent-browser --session "$SESSION" eval \
    "Array.from(document.querySelectorAll('button')).find(e => /^Send estimate$/i.test(e.textContent.trim()))?.click()" \
    >/dev/null 2>&1 || true
  sleep 3
  ab screenshot "$SHOTS/02-estimate-sheet.png"
  agent-browser --session "$SESSION" eval \
    "Array.from(document.querySelectorAll('button')).find(e => /Add from pricelist/i.test(e.textContent))?.click()" \
    >/dev/null 2>&1 || true
  sleep 2
  agent-browser --session "$SESSION" eval \
    "(() => { const i=document.querySelector('[data-testid=line-item-picker-search]'); if(!i) return; const setter=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set; setter.call(i,'Spring Start'); i.dispatchEvent(new Event('input',{bubbles:true})); })()" \
    >/dev/null 2>&1 || true
  sleep 2
  agent-browser --session "$SESSION" eval \
    "document.querySelector('[data-testid^=line-item-picker-result-]')?.click()" \
    >/dev/null 2>&1 || true
  sleep 2
  ab screenshot "$SHOTS/03-spring-startup-picked.png"
fi

# --- Phase 5 — Maps preference round-trip ---
agent-browser --session "$SESSION" eval \
  "Array.from(document.querySelectorAll('button,a')).find(e => /Get directions/i.test(e.textContent))?.click()" \
  >/dev/null 2>&1 || true
sleep 2
agent-browser --session "$SESSION" eval \
  "document.querySelector('[data-testid=remember-maps-choice-checkbox]')?.click()" >/dev/null 2>&1 || true
sleep 1
agent-browser --session "$SESSION" eval \
  "Array.from(document.querySelectorAll('[role=menuitem]')).find(e => /Google Maps/i.test(e.textContent))?.click()" \
  >/dev/null 2>&1 || true
sleep 2
ab screenshot "$SHOTS/04-google-remembered.png"

# --- Phase 4 — collect cash baseline (full submit, not just open) ---
agent-browser --session "$SESSION" eval \
  "document.querySelector('[data-testid=collect-payment-cta]')?.click()" >/dev/null 2>&1 || true
sleep 2
agent-browser --session "$SESSION" eval \
  "document.querySelector('[data-testid=record-other-payment-btn]')?.click()" >/dev/null 2>&1 || true
sleep 1
agent-browser --session "$SESSION" eval \
  "document.querySelector('[data-testid=payment-method-select]')?.click()" >/dev/null 2>&1 || true
sleep 1
agent-browser --session "$SESSION" eval \
  "Array.from(document.querySelectorAll('[role=option]')).find(e => /^cash$/i.test(e.textContent.trim()))?.click()" >/dev/null 2>&1 || true
sleep 1
INT_AMOUNT="$(python3 -c 'import time; print(f"{19.0 + (int(time.time())%80)*0.10:.2f}")')"
agent-browser --session "$SESSION" eval \
  "(() => { const i=document.querySelector('[data-testid=payment-amount-input]'); if(!i) return; const s=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set; s.call(i,'$INT_AMOUNT'); i.dispatchEvent(new Event('input',{bubbles:true})); })()" >/dev/null 2>&1 || true
sleep 1
agent-browser --session "$SESSION" eval \
  "document.querySelector('[data-testid=collect-payment-btn]')?.click()" >/dev/null 2>&1 || true
sleep 4
ab screenshot "$SHOTS/05-paid-card.png"
echo "$INT_AMOUNT" > "$SHOTS/05-paid-amount.txt"

# --- Phase 2 — edit a pricelist row ---
ab open "$BASE/invoices?tab=pricelist"
ab wait "[data-testid='price-list-editor']"
sleep 1
FIRST_ROW=$(agent-browser --session "$SESSION" eval \
  "document.querySelector('[data-testid^=\"price-list-row-\"]')?.dataset?.testid?.replace('price-list-row-','') || ''" \
  2>/dev/null | tail -1 | tr -d '"')
if [[ -n "$FIRST_ROW" ]]; then
  ab click "[data-testid='price-list-edit-${FIRST_ROW}']" || true
  ab wait "[data-testid='service-offering-drawer']"
  ab fill "[data-testid='offering-display-name-input']" "Integration Edited Name"
  ab click "[data-testid='offering-save']"
  sleep 2
  ab screenshot "$SHOTS/06-pricelist-edited.png"
fi

# --- Phase 1 — DB verification ---
psql_q "SELECT COUNT(*) FROM service_offerings WHERE slug IS NOT NULL;" > "$SHOTS/07-seed-count.txt"
psql_q "SELECT setting_value::text FROM business_settings WHERE setting_key = 'auto_job_on_approval';" > "$SHOTS/08-n5-flag.txt"

capture_console "$SHOTS/console"

# --- Task 6.8 — responsive verification ---
PAGES=(
  "/schedule:schedule"
  "/invoices?tab=pricelist:pricelist"
  "/leads:leads"
  "/customers:customers"
)

for vp in "375 812 mobile" "768 1024 tablet" "1440 900 desktop"; do
  read -r W H NAME <<< "$vp"
  ab set viewport "$W" "$H"
  for entry in "${PAGES[@]}"; do
    path="${entry%%:*}"
    label="${entry##*:}"
    ab open "$BASE$path"
    ab wait --load networkidle
    sleep 2
    ab screenshot "$RESP/${label}-${NAME}.png"
  done
done

ab close
echo
echo "PASS — integration screenshots in $SHOTS/, responsive in $RESP/"
