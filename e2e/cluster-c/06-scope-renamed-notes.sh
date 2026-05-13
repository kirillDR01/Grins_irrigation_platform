#!/usr/bin/env bash
# Cluster C — Phase F
# AppointmentModal's ScopeMaterialsCard label must read "Notes", not
# "Scope". Verifies the UI-only rename.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_lib.sh
source "$SCRIPT_DIR/_lib.sh"

require_cluster_c_env
require_tooling
require_servers

SHOTS_DIR="${SHOTS_ROOT}/06-scope-renamed-notes"
mkdir -p "$SHOTS_DIR"

login_admin

ab open "$BASE/schedule"
ab wait --load networkidle
sleep 3

# Open the first appointment row.
agent-browser --session "$SESSION" eval \
  "document.querySelector('[data-testid=view-list]')?.click()" >/dev/null
sleep 2
agent-browser --session "$SESSION" eval \
  "document.querySelector('[data-testid^=view-appointment-]')?.click()" >/dev/null
sleep 3
ab screenshot "${SHOTS_DIR}/01-appointment-modal.png"

HAS_NOTES=$(agent-browser --session "$SESSION" eval \
  "(() => Array.from(document.querySelectorAll('p,span,div')).some(el => /^Notes$/i.test((el.textContent||'').trim())))()" \
  2>/dev/null | tail -1)
HAS_SCOPE=$(agent-browser --session "$SESSION" eval \
  "(() => Array.from(document.querySelectorAll('p,span,div')).some(el => /^Scope$/i.test((el.textContent||'').trim())))()" \
  2>/dev/null | tail -1)

if [[ "$HAS_SCOPE" == "true" ]]; then
  echo "FAIL: AppointmentModal still shows the legacy 'Scope' label" >&2
  exit 1
fi
if [[ "$HAS_NOTES" != "true" ]]; then
  echo "FAIL: expected 'Notes' label not found (could not open an appointment with a scope card)" >&2
  exit 1
fi

ab screenshot "${SHOTS_DIR}/02-notes-label-annotated.png"
echo "PASS: Phase F — label renamed Scope → Notes"
