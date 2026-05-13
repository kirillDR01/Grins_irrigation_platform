#!/usr/bin/env bash
# Cluster C — sequenced runner. Sources _lib.sh, runs phase 01..06 in
# order, aborts at first non-zero exit. Operator must be present at the
# allowlisted phone/inbox throughout (the scripts themselves do not send
# SMS or email — they exercise the deterministic UI/DB surfaces).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_lib.sh
source "$SCRIPT_DIR/_lib.sh"

require_cluster_c_env
require_tooling
require_servers

echo "===== Cluster C — running 6 phase scripts ====="

for phase in \
  01-create-job-modal.sh \
  02-needs-estimate-badge-clears.sh \
  03-tech-view-confirmed-only.sh \
  04-job-search-global.sh \
  05-signwell-removed.sh \
  06-scope-renamed-notes.sh
do
  echo
  echo "----- Phase: $phase -----"
  bash "$SCRIPT_DIR/$phase" || {
    echo
    echo "===== ABORT: $phase failed =====" >&2
    exit 1
  }
done

echo
echo "===== Cluster C — all 6 phases passed ====="
