#!/usr/bin/env bash
# F4-REOPENED healthcheck: assert PORTAL_BASE_URL serves the React portal
# bundle (not the marketing-site bundle). The bug is "200 OK + wrong
# bundle" — a status-code-only check is insufficient. Run nightly in dev.
set -euo pipefail

: "${PORTAL_BASE_URL:?PORTAL_BASE_URL must be set}"

URL="${PORTAL_BASE_URL%/}/portal/estimates/__healthcheck__"
BODY="$(curl -sL --max-time 15 "$URL" || true)"

if printf '%s' "$BODY" | grep -q "<title>Grin's Irrigation Platform"; then
  echo "ok: React portal bundle confirmed at $URL"
  exit 0
fi

echo "ERROR: PORTAL_BASE_URL serves marketing bundle, not React portal" >&2
echo "  url=$URL" >&2
echo "  Expected <title>Grin's Irrigation Platform — got:" >&2
printf '%s' "$BODY" | grep -i '<title>' | head -1 >&2 || true
exit 1
