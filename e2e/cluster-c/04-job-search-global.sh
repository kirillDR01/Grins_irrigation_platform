#!/usr/bin/env bash
# Cluster C — Phase D
# Jobs tab uses <GlobalSearch scope="job" />. The old feature-local
# <Input data-testid="job-search"> is gone. Click result navigates to
# /jobs/{id}.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_lib.sh
source "$SCRIPT_DIR/_lib.sh"

require_cluster_c_env
require_tooling
require_servers

SHOTS_DIR="${SHOTS_ROOT}/04-job-search-global"
mkdir -p "$SHOTS_DIR"

login_admin

ab open "$BASE/jobs"
ab wait --load networkidle
sleep 2
ab screenshot "${SHOTS_DIR}/01-jobs-list.png"

# Old job-local search input must be gone.
OLD_INPUT=$(agent-browser --session "$SESSION" eval \
  "document.querySelector('[data-testid=job-search]') ? 'present' : 'absent'" \
  2>/dev/null | tail -1 | tr -d '"')
if [[ "$OLD_INPUT" != "absent" ]]; then
  echo "FAIL: legacy [data-testid=job-search] is still present" >&2
  exit 1
fi

# The global-search input must be inside the jobs page toolbar.
NEW_INPUT=$(agent-browser --session "$SESSION" eval \
  "document.querySelector('[data-testid=job-list] [data-testid=global-search-input]') ? 'present' : 'absent'" \
  2>/dev/null | tail -1 | tr -d '"')
if [[ "$NEW_INPUT" != "present" ]]; then
  echo "FAIL: <GlobalSearch scope='job'> input not found inside [data-testid=job-list]" >&2
  exit 1
fi

# Type a known fragment. We grep for a job_type substring that exists in DB.
KNOWN_TYPE=$(psql_q "SELECT job_type FROM jobs ORDER BY created_at DESC LIMIT 1")
if [[ -z "$KNOWN_TYPE" ]]; then
  echo "SKIP: no jobs in DB to search against." >&2
  exit 0
fi

ab fill "[data-testid=global-search-input]" "${KNOWN_TYPE:0:6}"
sleep 2
ab screenshot "${SHOTS_DIR}/02-search-results.png"

# Click first job result, expect navigation to /jobs/{id}.
agent-browser --session "$SESSION" eval \
  "document.querySelector('[data-testid^=search-result-job-]')?.click()" >/dev/null
sleep 3
ab screenshot "${SHOTS_DIR}/03-job-detail.png"

CUR_PATH=$(agent-browser --session "$SESSION" eval "location.pathname" 2>/dev/null | tail -1 | tr -d '"')
if [[ "$CUR_PATH" != /jobs/* ]]; then
  echo "FAIL: expected /jobs/{id}, got ${CUR_PATH}" >&2
  exit 1
fi
echo "PASS: Phase D — global search scope=job navigates to ${CUR_PATH}"
