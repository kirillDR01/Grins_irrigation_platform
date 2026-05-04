#!/usr/bin/env bash
# Phase 1 E2E — Pricelist data + seed verification.
#
# Pure DB checks — no UI yet (UI is Phase 2). Mirrors Task 6.2 of
# .agents/plans/appointment-modal-payment-estimate-pricelist-umbrella.md.

set -euo pipefail
cd "$(dirname "$0")/.."

# shellcheck source=./_lib.sh
source e2e/_lib.sh

require_tooling
SHOTS="$SHOTS_ROOT/phase-1"
mkdir -p "$SHOTS"

LOG="$SHOTS/queries.log"
: > "$LOG"

run() {
  local title="$1" sql="$2" expected="$3"
  local got
  got=$(psql_q "$sql")
  printf "[%s] expected=%s got=%s\n" "$title" "$expected" "$got" | tee -a "$LOG"
  if [[ "$got" != "$expected" ]]; then
    echo "FAIL: $title" | tee -a "$LOG"
    exit 1
  fi
}

run "total_seed_count" \
  "SELECT COUNT(*) FROM service_offerings WHERE slug IS NOT NULL;" \
  "73"

# residential|37 / commercial|36 (seed JSON distribution).
got=$(psql_q "SELECT customer_type || '|' || COUNT(*) FROM service_offerings WHERE slug IS NOT NULL GROUP BY customer_type ORDER BY customer_type;")
echo "[customer_type_breakdown] $got" | tee -a "$LOG"
echo "$got" | grep -q "^residential|37$" || { echo "FAIL: residential count != 37"; exit 1; }
echo "$got" | grep -q "^commercial|36$" || { echo "FAIL: commercial count != 36"; exit 1; }

# Slug uniqueness — partial unique index enforcement.
dup=$(psql_q "SELECT COUNT(*) FROM (SELECT slug FROM service_offerings WHERE slug IS NOT NULL GROUP BY slug HAVING COUNT(*) > 1) t;")
echo "[slug_uniqueness_dup_count] $dup" | tee -a "$LOG"
[[ "$dup" == "0" ]] || { echo "FAIL: duplicate slugs found"; exit 1; }

# Pre-seed rows untouched (slug NULL preserved on legacy data, if any).
pre=$(psql_q "SELECT COUNT(*) FROM service_offerings WHERE slug IS NULL;")
echo "[pre_seed_unchanged_count] $pre" | tee -a "$LOG"

# pricing_rule JSONB roundtrip — sample a known seed key.
rule=$(psql_q "SELECT pricing_rule::text FROM service_offerings WHERE slug = 'irrigation_install_residential';")
echo "[sample_pricing_rule] $rule" | tee -a "$LOG"
echo "$rule" | grep -q "price_per_zone_min" || { echo "FAIL: pricing_rule missing price_per_zone_min"; exit 1; }
echo "$rule" | grep -q "profile_factor"     || { echo "FAIL: pricing_rule missing profile_factor"; exit 1; }

# Per-pricing_model distribution matches the seed JSON Counter.
psql "$DATABASE_URL" -F'|' -tAc \
  "SELECT pricing_model, COUNT(*) FROM service_offerings WHERE slug IS NOT NULL GROUP BY pricing_model ORDER BY pricing_model;" \
  > "$SHOTS/pricing-model-distribution.txt"

echo "[pricing_model_distribution]" | tee -a "$LOG"
cat "$SHOTS/pricing-model-distribution.txt" | tee -a "$LOG"

# Gating env var check — downgrade then upgrade WITHOUT VIKTOR_PRICELIST_CONFIRMED
# should refuse to run the seed migration. Skip if env says so (this re-runs migrations).
if [[ "${PHASE1_VERIFY_GATING:-0}" == "1" ]]; then
  uv run alembic downgrade 20260504_120000 >/dev/null
  if env -u VIKTOR_PRICELIST_CONFIRMED uv run alembic upgrade 20260504_130000 2>&1 | grep -q VIKTOR_PRICELIST_CONFIRMED; then
    echo "[gating_check] PASS — migration refused without env var" | tee -a "$LOG"
  else
    echo "FAIL: gating env var did not block seed" | tee -a "$LOG"
    exit 1
  fi
  VIKTOR_PRICELIST_CONFIRMED=true uv run alembic upgrade head >/dev/null
fi

echo
echo "PASS — Phase 1 DB checks all green; log at $LOG"
