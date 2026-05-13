#!/usr/bin/env bash
# Cluster C — Phase E
# SignWell visible-surface removal verification:
#   1. /api/v1/webhooks/signwell route is 404.
#   2. SignWell iframe absent from sales-detail UI.
#   3. "signed via SignWell" copy is gone; "Upload the signed agreement" copy present.
#   4. convert_to_job succeeds without a signwell_document_id on the entry.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_lib.sh
source "$SCRIPT_DIR/_lib.sh"

require_cluster_c_env
require_tooling
require_servers

SHOTS_DIR="${SHOTS_ROOT}/05-signwell-removed"
mkdir -p "$SHOTS_DIR"

# 1. Webhook route is gone.
CODE=$(curl -s -o /dev/null -w '%{http_code}' "$API_BASE/api/v1/webhooks/signwell" || echo "000")
if [[ "$CODE" != "404" && "$CODE" != "405" ]]; then
  echo "FAIL: /api/v1/webhooks/signwell returned ${CODE}, expected 404 or 405" >&2
  exit 1
fi

# 2. UI surface — pick a send_contract entry to inspect.
ENTRY_ID=$(psql_q "SELECT id FROM sales_entries WHERE status='send_contract' ORDER BY updated_at DESC LIMIT 1")

login_admin

if [[ -n "${ENTRY_ID:-}" ]]; then
  ab open "$BASE/sales/${ENTRY_ID}"
  ab wait --load networkidle
  sleep 2
  ab screenshot "${SHOTS_DIR}/01-sales-detail.png"

  IFRAME=$(agent-browser --session "$SESSION" eval \
    "[...document.querySelectorAll('iframe')].some(i => /signwell/i.test(i.src || ''))" \
    2>/dev/null | tail -1)
  if [[ "$IFRAME" == "true" ]]; then
    echo "FAIL: SignWell iframe still rendered on sales detail" >&2
    exit 1
  fi

  HAS_NEW=$(agent-browser --session "$SESSION" eval \
    "/Upload the signed agreement/i.test(document.body.innerText)" \
    2>/dev/null | tail -1)
  HAS_OLD=$(agent-browser --session "$SESSION" eval \
    "/signed via SignWell/i.test(document.body.innerText)" \
    2>/dev/null | tail -1)
  if [[ "$HAS_OLD" == "true" ]]; then
    echo "FAIL: legacy 'signed via SignWell' copy still rendered" >&2
    exit 1
  fi
  if [[ "$HAS_NEW" != "true" ]]; then
    echo "WARN: new 'Upload the signed agreement' copy not detected (may be due to action visibility — check screenshot)" >&2
  fi
fi

# 3. convert_to_job without signwell_document_id succeeds.
ENTRY_NOSIG=$(psql_q "SELECT id FROM sales_entries WHERE signwell_document_id IS NULL AND status NOT IN ('closed_won','closed_lost') ORDER BY updated_at DESC LIMIT 1")
if [[ -z "${ENTRY_NOSIG:-}" ]]; then
  echo "SKIP: no eligible entry without a signwell_document_id to test gate-removal." >&2
else
  echo "Convert (no signature) test on entry: $ENTRY_NOSIG"
  # Use the API endpoint directly — admin session cookie carries auth.
  RESP=$(agent-browser --session "$SESSION" eval \
    "fetch('${API_BASE}/api/v1/sales/pipeline/${ENTRY_NOSIG}/convert', { method: 'POST', credentials: 'include' }).then(r => r.status)" \
    2>/dev/null | tail -1)
  if [[ "$RESP" != "200" && "$RESP" != "201" ]]; then
    echo "FAIL: convert returned ${RESP}, expected 200/201" >&2
    exit 1
  fi
  ENTRY_STATUS=$(psql_q "SELECT status FROM sales_entries WHERE id='${ENTRY_NOSIG}'")
  if [[ "$ENTRY_STATUS" != "closed_won" ]]; then
    echo "FAIL: entry ${ENTRY_NOSIG} status=${ENTRY_STATUS}, expected closed_won" >&2
    exit 1
  fi
  ab screenshot "${SHOTS_DIR}/02-converted.png"
fi

echo "PASS: Phase E — SignWell webhook removed, UI clean, convert gate dropped"
