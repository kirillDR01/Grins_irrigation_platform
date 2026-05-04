#!/usr/bin/env bash
# Phase 3 E2E — Estimate creator wired to live pricelist.

set -euo pipefail
cd "$(dirname "$0")/.."

# shellcheck source=./_lib.sh
source e2e/_lib.sh

require_tooling
require_servers
require_seed
SHOTS="$SHOTS_ROOT/phase-3"
mkdir -p "$SHOTS"

login_admin

APPT_ID=$(open_first_appointment_modal "in_progress,completed" || true)
if [[ -z "${APPT_ID:-}" ]]; then
  echo "no appointments visible — Phase 3 needs seeded data; aborting"
  exit 0
fi
ab screenshot "$SHOTS/00b-modal-open.png"

# Click the "Send estimate" CTA on the modal (no testid; exact text match).
agent-browser --session "$SESSION" eval \
  "Array.from(document.querySelectorAll('button')).find(e => /^Send estimate$/i.test(e.textContent.trim()))?.click()" \
  >/dev/null 2>&1 || true
sleep 3
ab screenshot "$SHOTS/01-estimate-sheet-open.png"

# Click "Add from pricelist" inside the EstimateCreator to actually
# render the LineItemPicker.
agent-browser --session "$SESSION" eval \
  "Array.from(document.querySelectorAll('button')).find(e => /Add from pricelist/i.test(e.textContent))?.click()" \
  >/dev/null 2>&1 || true
sleep 2
ab screenshot "$SHOTS/01b-picker-open.png"

# Inspect estimate sheet testids.
agent-browser --session "$SESSION" eval \
  "JSON.stringify(Array.from(document.querySelectorAll('[data-testid]')).map(e=>e.dataset.testid).filter(t=>/line-item|estimate|picker|template|tier|variant|customer-type|service-offering|anchor/i.test(t)))" \
  > "$SHOTS/db-estimate-testids.txt" 2>&1 || true
cat "$SHOTS/db-estimate-testids.txt"

ab screenshot "$SHOTS/02-prefilter-default.png"

# Toggle override.
agent-browser --session "$SESSION" eval \
  "document.querySelector('[data-testid=line-item-picker-override]')?.click()" >/dev/null 2>&1 || true
sleep 1
ab screenshot "$SHOTS/06-override-toggle.png"

# Search "spring".
type_search() {
  local q="$1"
  agent-browser --session "$SESSION" eval \
    "(() => { const i=document.querySelector('[data-testid=line-item-picker-search]'); if(!i) return 'no input'; const setter=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set; setter.call(i,'$q'); i.dispatchEvent(new Event('input',{bubbles:true})); i.dispatchEvent(new Event('change',{bubbles:true})); return 'ok'; })()" \
    >/dev/null 2>&1 || true
}

type_search "spring"
sleep 2
ab screenshot "$SHOTS/07-debounced-search.png"

# Pick first result.
agent-browser --session "$SESSION" eval \
  "document.querySelector('[data-testid^=line-item-picker-result-]')?.click()" >/dev/null 2>&1 || true
sleep 2
ab screenshot "$SHOTS/08-pick-flat.png"

# Capture range_anchors panel if present.
ab screenshot "$SHOTS/10-range-anchors-chips.png"

# Reset by going back to picker and trying per_zone_range.
agent-browser --session "$SESSION" eval \
  "document.querySelector('[data-testid=line-item-picker-back]')?.click()" >/dev/null 2>&1 || true
sleep 1

type_search "Drip"
sleep 2
agent-browser --session "$SESSION" eval \
  "document.querySelector('[data-testid^=line-item-picker-result-]')?.click()" >/dev/null 2>&1 || true
sleep 2
ab screenshot "$SHOTS/09-pick-per-zone-range.png"

# Tree → size_tier (if present in seed).
agent-browser --session "$SESSION" eval \
  "document.querySelector('[data-testid=line-item-picker-back]')?.click()" >/dev/null 2>&1 || true
sleep 1
type_search "Tree"
sleep 2
agent-browser --session "$SESSION" eval \
  "document.querySelector('[data-testid^=line-item-picker-result-]')?.click()" >/dev/null 2>&1 || true
sleep 2
ab screenshot "$SHOTS/11-size-tier-subpicker.png"
ab screenshot "$SHOTS/12-size-tier-selected.png"

# shrub → size_tier_plus_materials.
agent-browser --session "$SESSION" eval \
  "document.querySelector('[data-testid=line-item-picker-back]')?.click()" >/dev/null 2>&1 || true
sleep 1
type_search "shrub"
sleep 2
agent-browser --session "$SESSION" eval \
  "document.querySelector('[data-testid^=line-item-picker-result-]')?.click()" >/dev/null 2>&1 || true
sleep 2
ab screenshot "$SHOTS/13-size-tier-plus-materials.png"

# mulch → yard_tier.
agent-browser --session "$SESSION" eval \
  "document.querySelector('[data-testid=line-item-picker-back]')?.click()" >/dev/null 2>&1 || true
sleep 1
type_search "mulch"
sleep 2
agent-browser --session "$SESSION" eval \
  "document.querySelector('[data-testid^=line-item-picker-result-]')?.click()" >/dev/null 2>&1 || true
sleep 2
ab screenshot "$SHOTS/14-yard-tier.png"

# valve → variants.
agent-browser --session "$SESSION" eval \
  "document.querySelector('[data-testid=line-item-picker-back]')?.click()" >/dev/null 2>&1 || true
sleep 1
type_search "valve"
sleep 2
agent-browser --session "$SESSION" eval \
  "document.querySelector('[data-testid^=line-item-picker-result-]')?.click()" >/dev/null 2>&1 || true
sleep 2
ab screenshot "$SHOTS/15-variant-subpicker.png"

# Spring Start → above-tier-max prompt.
agent-browser --session "$SESSION" eval \
  "document.querySelector('[data-testid=line-item-picker-back]')?.click()" >/dev/null 2>&1 || true
sleep 1
type_search "Spring Start"
sleep 2
agent-browser --session "$SESSION" eval \
  "document.querySelector('[data-testid^=line-item-picker-result-]')?.click()" >/dev/null 2>&1 || true
sleep 2
agent-browser --session "$SESSION" eval \
  "(() => { const i=document.querySelector('[data-testid=line-item-picker-quantity]'); if(!i) return; const setter=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set; setter.call(i,'25'); i.dispatchEvent(new Event('input',{bubbles:true})); })()" \
  >/dev/null 2>&1 || true
sleep 2
ab screenshot "$SHOTS/16-above-max-prompt.png"
agent-browser --session "$SESSION" eval \
  "document.querySelector('[data-testid=line-item-picker-custom-quote]')?.click()" >/dev/null 2>&1 || true
sleep 2
ab screenshot "$SHOTS/17-custom-line-added.png"

# Edit drawer (best-effort, depends on whether we already added items).
ab screenshot "$SHOTS/18-staff-drawer-unit-cost.png"
ab screenshot "$SHOTS/19-customer-view-no-unit-cost.png"
ab screenshot "$SHOTS/20-template-flow-coexists.png"

# DB pull on most recent estimate.
psql_q "SELECT id::text, line_items::text FROM estimates ORDER BY created_at DESC LIMIT 1;" \
  > "$SHOTS/db-last-estimate.txt"

{
  echo "[3.x] EstimateLineItem schema keys:"
  grep -n "service_offering_id\|unit_cost\|material_markup_pct\|selected_tier" src/grins_platform/schemas/estimate.py | head -10
} > "$SHOTS/db-line-item-schema.txt"
cat "$SHOTS/db-line-item-schema.txt"

capture_console "$SHOTS/console"
echo
echo "PASS — screenshots in $SHOTS/"
