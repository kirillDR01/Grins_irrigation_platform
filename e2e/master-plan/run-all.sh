#!/usr/bin/env bash
# Master-plan sequential phase runner.
#
# Runs phases 0..24 in order. Each phase is its own dispatcher invocation;
# any phase that lacks an automation shell prints a manual notice and the
# runner pauses for the operator to walk that phase from the plan markdown,
# then continues.
#
# Usage:
#   ENVIRONMENT=dev e2e/master-plan/run-all.sh
#   ENVIRONMENT=dev e2e/master-plan/run-all.sh 7 14   # only run 7..14
#
# Stop on first failure (set -e). Re-run individual phases via run-phase.sh.

set -euo pipefail

cd "$(dirname "$0")/../.."

# shellcheck source=./_dev_lib.sh
source e2e/master-plan/_dev_lib.sh

START="${1:-0}"
END="${2:-24}"

require_tooling
require_servers
require_token
require_dev_railway_link

LOG="$SHOTS_ROOT/run-all-$(date +%Y%m%d-%H%M%S).log"
mkdir -p "$SHOTS_ROOT"
echo "Logging to $LOG"

for n in $(seq "$START" "$END"); do
  echo "═══ run-all → phase $n ($(date)) ═══" | tee -a "$LOG"
  e2e/master-plan/run-phase.sh "$n" 2>&1 | tee -a "$LOG"
done

echo "═══ run-all done ($(date)) ═══" | tee -a "$LOG"
echo "Screenshots in: $SHOTS_ROOT/"
echo "Run log:        $LOG"
