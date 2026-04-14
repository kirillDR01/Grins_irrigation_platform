#!/usr/bin/env bash
# Smoke test for the public lead submission endpoint.
#
# Usage:
#   BASE_URL=https://grins-dev-dev.up.railway.app ./scripts/smoke/test_public_lead.sh
#
# The script POSTs a minimal payload that passes Pydantic validation and
# asserts a 201 Created (plus echoes the X-Request-ID for log correlation).
# Exits non-zero on any other status.

set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
PHONE_E164="${PHONE_E164:-+19527373312}"   # dev allowlist
SOURCE_SITE="${SOURCE_SITE:-grins-irrigation.com}"

echo "POST ${BASE_URL}/api/v1/leads"

response=$(curl --silent --show-error \
  --write-out $'\n__STATUS__%{http_code}\n__HEADER_X_REQUEST_ID__%header{x-request-id}' \
  --request POST "${BASE_URL}/api/v1/leads" \
  --header "Content-Type: application/json" \
  --header "Origin: https://grins-irrigation.com" \
  --data @- <<JSON
{
  "name": "Smoke Test",
  "phone": "${PHONE_E164}",
  "email": "smoke-test@example.com",
  "service_type": "spring_startup",
  "source_site": "${SOURCE_SITE}",
  "notes": "Automated smoke test from scripts/smoke/test_public_lead.sh"
}
JSON
)

body="${response%__STATUS__*}"
status_line="${response#*__STATUS__}"
status="${status_line%%$'\n'*}"
request_id_line="${status_line#*__HEADER_X_REQUEST_ID__}"
request_id="${request_id_line%%$'\n'*}"

echo "Response status: ${status}"
echo "X-Request-ID:    ${request_id}"
echo "Body:            ${body}"

if [[ "${status}" != "201" ]]; then
  echo "FAIL: expected 201, got ${status}" >&2
  exit 1
fi

echo "PASS: public lead submission returned 201."
