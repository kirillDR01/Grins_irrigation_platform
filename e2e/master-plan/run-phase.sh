#!/usr/bin/env bash
# Master-plan single-phase dispatcher.
#
# Usage:
#   ENVIRONMENT=dev e2e/master-plan/run-phase.sh 4
#   e2e/master-plan/run-phase.sh 9         # local
#
# Phases are 0..24. Each phase has a corresponding markdown body in
# .agents/plans/master-e2e-testing-plan.md. Per-phase shell scripts are
# placed at e2e/master-plan/phase-NN-*.sh — runners delegate here.
#
# This dispatcher does NOT contain the per-phase steps; it loads _dev_lib.sh
# and dispatches to the matching phase shell. Per-phase shells are authored
# incrementally; missing ones print a helpful "manual phase" notice and exit.

set -euo pipefail

PHASE_NUM="${1:?usage: run-phase.sh <0-24>}"

cd "$(dirname "$0")/../.."

# shellcheck source=./_dev_lib.sh
source e2e/master-plan/_dev_lib.sh

PHASE=$(printf 'phase-%02d' "$PHASE_NUM")
export PHASE
SHOT_DIR="$SHOTS_ROOT/$PHASE"
export SHOT_DIR
mkdir -p "$SHOT_DIR"

# Find a phase script by prefix. Tolerates any descriptive suffix.
PHASE_SCRIPT=$(ls e2e/master-plan/phase-$(printf '%02d' "$PHASE_NUM")-*.sh 2>/dev/null | head -1 || true)

if [[ -z "$PHASE_SCRIPT" ]]; then
  cat <<EOF
═════════════════════════════════════════════════════════════════
Phase $PHASE_NUM has no automation shell yet.

Open .agents/plans/master-e2e-testing-plan.md and walk Phase $PHASE_NUM
manually using the documented steps. The plan body is the source of
truth — agent-browser commands and verification curls are inline.

To author automation, create:
  e2e/master-plan/phase-$(printf '%02d' "$PHASE_NUM")-<slug>.sh

Source e2e/master-plan/_dev_lib.sh from the new script and reuse:
  - login_admin / login_tech
  - api / api_q
  - shot / shot_full
  - sim/* HMAC-signed webhook helpers
═════════════════════════════════════════════════════════════════
EOF
  exit 0
fi

require_tooling
require_servers
require_token
require_dev_railway_link

echo "═══ Phase $PHASE_NUM ($PHASE_SCRIPT) — starting ($(date)) ═══" >&2
"$PHASE_SCRIPT"
RC=$?
if (( RC == 0 )); then
  echo "═══ Phase $PHASE_NUM PASS ═══" >&2
else
  echo "═══ Phase $PHASE_NUM FAIL rc=$RC ═══" >&2
fi
exit $RC
