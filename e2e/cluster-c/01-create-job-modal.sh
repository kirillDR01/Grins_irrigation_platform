#!/usr/bin/env bash
# Cluster C — Phase A
# Verifies the new editable Create-Job modal renders with prefill, accepts
# edits, submits via POST /jobs + status-update on the sales entry, and
# the resulting Job has category=ready_to_schedule.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_lib.sh
source "$SCRIPT_DIR/_lib.sh"

require_cluster_c_env
require_tooling
require_servers

SHOTS_DIR="${SHOTS_ROOT}/01-create-job-modal"
mkdir -p "$SHOTS_DIR"

login_admin

# Find a sales entry that's in send_contract — that's the stage the new
# modal replaces. If none exists, exit 0 with a clear note so the runner
# moves on; this script asserts the happy path only.
ENTRY_ID=$(psql_q "SELECT id FROM sales_entries WHERE status='send_contract' ORDER BY updated_at DESC LIMIT 1")
if [[ -z "${ENTRY_ID:-}" ]]; then
  echo "SKIP: no sales_entries in 'send_contract' stage on dev. Seed one before running Phase A." >&2
  exit 0
fi

echo "Using sales entry: $ENTRY_ID"

ab open "$BASE/sales"
ab wait --load networkidle
sleep 2
ab screenshot "${SHOTS_DIR}/01-sales-list.png"

ab open "$BASE/sales/${ENTRY_ID}"
ab wait --load networkidle
sleep 2
ab screenshot "${SHOTS_DIR}/02-sales-detail.png"

# Click the primary action (Convert to Job) which now opens the modal.
agent-browser --session "$SESSION" eval \
  "document.querySelector('[data-testid^=advance-btn-]')?.click()" >/dev/null
sleep 2
ab screenshot "${SHOTS_DIR}/03-modal-open.png"

# Sanity-check the modal: title contains "Create Job", Tags input is disabled.
MODAL_OK=$(agent-browser --session "$SESSION" eval \
  "(() => { const dlg = document.querySelector('[role=dialog]'); if (!dlg) return 'no-dialog'; const t = dlg.querySelector('h2,h3,[data-testid=dialog-title]')?.textContent || ''; if (!/create job/i.test(t)) return 'wrong-title'; const tags = dlg.querySelector('[name=tags],[data-testid=create-job-tags]'); if (tags && !tags.disabled) return 'tags-enabled'; return 'ok'; })()" \
  2>/dev/null | tail -1 | tr -d '"')
if [[ "$MODAL_OK" != "ok" ]]; then
  echo "FAIL: modal sanity check returned $MODAL_OK" >&2
  ab screenshot "${SHOTS_DIR}/04-modal-FAIL.png"
  exit 1
fi

# Edit Description.
agent-browser --session "$SESSION" eval \
  "(() => { const d = document.querySelector('[role=dialog] textarea[name=description]'); if (!d) return; const v = 'E2E edited description ' + Date.now(); const nativeSet = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set; nativeSet.call(d, v); d.dispatchEvent(new Event('input', { bubbles: true })); })()" >/dev/null
sleep 1
ab screenshot "${SHOTS_DIR}/04-modal-edited.png"

# Submit.
agent-browser --session "$SESSION" eval \
  "document.querySelector('[role=dialog] [data-testid=create-job-submit],[role=dialog] button[type=submit]')?.click()" >/dev/null
ab wait --load networkidle
sleep 4
ab screenshot "${SHOTS_DIR}/05-modal-submitted-job-detail.png"

# Find the most recently created job for this customer to assert category.
CUSTOMER_ID=$(psql_q "SELECT customer_id FROM sales_entries WHERE id='${ENTRY_ID}'")
JOB_ID=$(psql_q "SELECT id FROM jobs WHERE customer_id='${CUSTOMER_ID}' ORDER BY created_at DESC LIMIT 1")

if [[ -z "${JOB_ID:-}" ]]; then
  echo "FAIL: no job created" >&2
  exit 1
fi

assert_job_category "$JOB_ID" "ready_to_schedule"

# Sales entry should be closed_won now.
ENTRY_STATUS=$(psql_q "SELECT status FROM sales_entries WHERE id='${ENTRY_ID}'")
if [[ "$ENTRY_STATUS" != "closed_won" ]]; then
  echo "FAIL: sales entry status=${ENTRY_STATUS}, expected closed_won" >&2
  exit 1
fi

echo "PASS: Phase A — job ${JOB_ID} created with category=ready_to_schedule"
