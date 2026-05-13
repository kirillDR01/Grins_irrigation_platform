#!/usr/bin/env bash
# Cluster C — Phase B
# A Job created via convert_to_job (Phase A) must NOT render the
# "Estimate Needed" badge in JobDetail. Category must be ready_to_schedule.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_lib.sh
source "$SCRIPT_DIR/_lib.sh"

require_cluster_c_env
require_tooling
require_servers

SHOTS_DIR="${SHOTS_ROOT}/02-needs-estimate-badge-clears"
mkdir -p "$SHOTS_DIR"

login_admin

# Pick the most recent Job whose source-of-creation was a sales-pipeline
# conversion. We approximate that by selecting the newest ready_to_schedule
# job whose customer has a recent closed_won entry.
JOB_ID=$(psql_q "SELECT j.id FROM jobs j JOIN sales_entries s ON s.customer_id = j.customer_id WHERE s.status='closed_won' AND j.category='ready_to_schedule' ORDER BY j.created_at DESC LIMIT 1")
if [[ -z "${JOB_ID:-}" ]]; then
  echo "SKIP: no ready_to_schedule job found from a closed_won sales entry. Run Phase A first." >&2
  exit 0
fi

echo "Verifying badge for job: $JOB_ID"

ab open "$BASE/jobs/${JOB_ID}"
ab wait --load networkidle
sleep 2
ab screenshot "${SHOTS_DIR}/01-job-detail.png"

# Assert the "Estimate Needed" badge does NOT render. The component at
# JobDetail.tsx uses the AlertTriangle icon + "Estimate Needed" text and
# does not have a data-testid today. Match by text instead.
BADGE_PRESENT=$(agent-browser --session "$SESSION" eval \
  "(() => Array.from(document.querySelectorAll('span,div')).some(el => /Estimate Needed/i.test(el.textContent || '')))()" \
  2>/dev/null | tail -1)
if [[ "$BADGE_PRESENT" == "true" ]]; then
  echo "FAIL: 'Estimate Needed' badge still rendered on job ${JOB_ID}" >&2
  ab screenshot "${SHOTS_DIR}/02-job-detail-FAIL.png"
  exit 1
fi

ab screenshot "${SHOTS_DIR}/02-job-detail-annotated.png"

assert_job_category "$JOB_ID" "ready_to_schedule"
echo "PASS: Phase B — badge absent, category=ready_to_schedule"
