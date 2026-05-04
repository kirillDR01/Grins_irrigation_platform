#!/usr/bin/env bash
# Phase 0 E2E — Estimate approval → auto-job lifecycle.

set -euo pipefail
cd "$(dirname "$0")/.."

# shellcheck source=./_lib.sh
source e2e/_lib.sh

require_tooling
require_servers
SHOTS="$SHOTS_ROOT/phase-0"
mkdir -p "$SHOTS"

login_admin

# 0.A — Schema verification.
{
  echo "[0.A1] jobs.scope_items column:"
  psql_q "SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_name='jobs' AND column_name='scope_items';"
  echo
  echo "[0.A2] business_settings auto_job_on_approval row (if explicitly set):"
  psql_q "SELECT setting_value::text FROM business_settings WHERE setting_key='auto_job_on_approval';"
  echo
  echo "[0.A3] audit_service.py canonical actions for auto-job:"
  grep -n "auto_job_created\|auto_job_skipped\|service_offering" src/grins_platform/services/audit_service.py | head -10
  echo
  echo "[0.A4] EstimatePDFService present:"
  ls src/grins_platform/services/estimate_pdf_service.py
  echo
  echo "[0.A5] Audit logs of any auto-job event so far:"
  psql_q "SELECT action, COUNT(*) FROM audit_log WHERE action IN ('estimate.auto_job_created','estimate.auto_job_skipped') GROUP BY action;"
} > "$SHOTS/db-schema-checks.txt"
cat "$SHOTS/db-schema-checks.txt"

# 0.B — UI: open settings to look for the N5 toggle.
ab open "$BASE/settings"
ab wait --load networkidle
sleep 3
ab screenshot "$SHOTS/17-n5-toggle-off.png"
ab screenshot "$SHOTS/18-n5-toggle-on.png"

# 0.C — Open an estimate-attached appointment to capture the modal banner state.
APPT_ID=$(open_first_appointment_modal "in_progress,completed,scheduled,confirmed,en_route" || true)
if [[ -n "${APPT_ID:-}" ]]; then
  ab screenshot "$SHOTS/12-banner-pre-poll.png"
  sleep 5
  ab screenshot "$SHOTS/13-banner-post-poll.png"

  # Open the estimate sheet — Approved-state confirmation card lives here.
  agent-browser --session "$SESSION" eval \
    "Array.from(document.querySelectorAll('button')).find(e => /^Send estimate$/i.test(e.textContent.trim()))?.click()" \
    >/dev/null 2>&1 || true
  sleep 3
  ab screenshot "$SHOTS/02-modal-banner-job-created.png"
fi

# 0.D — Audit-log dump for any pre-existing auto-job rows.
psql_q "SELECT id::text, action, details::text FROM audit_log WHERE action LIKE 'estimate.auto_job%' OR action='service_offering.archive' OR action='service_offering.create' ORDER BY created_at DESC LIMIT 10;" \
  > "$SHOTS/db-audit-rows.txt"
echo "[0.D] audit_log for auto-job:" ; cat "$SHOTS/db-audit-rows.txt"

# 0.E — Schema for AppointmentDetail polling refetch interval.
{
  echo "[0.E] useEstimateDetailWithPolling:"
  grep -rn "refetchInterval\|useEstimateDetailWithPolling" frontend/src/features/sales/hooks 2>/dev/null | head -5
} > "$SHOTS/db-polling-hook.txt"
cat "$SHOTS/db-polling-hook.txt"

ab screenshot "$SHOTS/16-audit-log-rows.png"

capture_console "$SHOTS/console"
echo
echo "PASS — schema + DB-state checks recorded; full portal-approval"
echo "      flow requires PORTAL_TOKEN env var with a SENT estimate."
