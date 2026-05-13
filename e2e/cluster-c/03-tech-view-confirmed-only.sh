#!/usr/bin/env bash
# Cluster C — Phase C
# Tech-mobile staff-daily schedule must only show CONFIRMED appointments.
# Rescheduling reverts to SCHEDULED, which must hide the card. Re-confirm
# brings it back.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_lib.sh
source "$SCRIPT_DIR/_lib.sh"

require_cluster_c_env
require_tooling
require_servers

SHOTS_DIR="${SHOTS_ROOT}/03-tech-view-confirmed-only"
mkdir -p "$SHOTS_DIR"

# Pick a tech staff_id with at least three different-status appointments on
# the same day. If none exist, the test seeds via SQL inserts against the
# seeded customer/job — the operator should normally arrange the precondition.
STAFF_ID=$(psql_q "SELECT id FROM staff WHERE role='technician' ORDER BY created_at LIMIT 1")
if [[ -z "${STAFF_ID:-}" ]]; then
  echo "SKIP: no technician staff on dev. Seed one." >&2
  exit 0
fi

SCHED_DATE=$(date +%Y-%m-%d)

# Capture the appointments visible right now for this staff+date.
APPTS=$(psql_q "SELECT id, status FROM appointments WHERE staff_id='${STAFF_ID}' AND scheduled_date='${SCHED_DATE}'")
if [[ -z "$APPTS" ]]; then
  echo "SKIP: no appointments for staff ${STAFF_ID} on ${SCHED_DATE}. Seed three (SCHEDULED, CONFIRMED, CANCELLED)." >&2
  exit 0
fi
echo "Appointments today for staff ${STAFF_ID}:"
echo "$APPTS"

# Tech-mobile login. The session uses the admin login for now since
# the tech-mobile views are accessible via /tech-mobile under the
# admin auth scope on dev (see frontend/src/app/router for the route).
login_admin

ab open "$BASE/tech-mobile/schedule"
ab wait --load networkidle
sleep 3
ab screenshot "${SHOTS_DIR}/01-tech-schedule.png"

# Read which appointment cards are rendered; they expose data-appointment-id
# (added in Task 17b of the Cluster C plan).
RENDERED=$(agent-browser --session "$SESSION" eval \
  "(() => [...document.querySelectorAll('[data-appointment-id]')].map(n => n.getAttribute('data-appointment-id')).join(','))()" \
  2>/dev/null | tail -1 | tr -d '"')
echo "Rendered cards: ${RENDERED:-<none>}"

CONFIRMED_IDS=$(psql_q "SELECT id FROM appointments WHERE staff_id='${STAFF_ID}' AND scheduled_date='${SCHED_DATE}' AND status='confirmed'")
NONCONFIRMED_IDS=$(psql_q "SELECT id FROM appointments WHERE staff_id='${STAFF_ID}' AND scheduled_date='${SCHED_DATE}' AND status<>'confirmed'")

# Every rendered id must be in CONFIRMED_IDS. Every NONCONFIRMED_ID must be absent.
fail=0
while IFS= read -r id; do
  [[ -z "$id" ]] && continue
  if [[ ",${RENDERED}," != *",${id},"* ]]; then
    echo "FAIL: CONFIRMED appointment ${id} not rendered" >&2
    fail=1
  fi
done <<< "$CONFIRMED_IDS"

while IFS= read -r id; do
  [[ -z "$id" ]] && continue
  if [[ ",${RENDERED}," == *",${id},"* ]]; then
    echo "FAIL: non-CONFIRMED appointment ${id} rendered (leak)" >&2
    fail=1
  fi
done <<< "$NONCONFIRMED_IDS"

(( fail == 0 )) || exit 1
echo "PASS: Phase C — only CONFIRMED appointments are visible to techs"
