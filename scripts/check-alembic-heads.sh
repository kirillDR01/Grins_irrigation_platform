#!/usr/bin/env bash
# Fail if Alembic has more than one head. Bug 1 follow-up
# (bughunt 2026-04-28) — see DEVLOG entry from this fix.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
HEADS=$(uv run alembic heads 2>/dev/null | grep -c '(head)' || true)
if [[ "$HEADS" -ne 1 ]]; then
  echo "ERROR: alembic has $HEADS heads (expected 1). Create a merge revision:" >&2
  echo "  uv run alembic merge -m 'merge heads' <head1> <head2>" >&2
  uv run alembic heads >&2
  exit 1
fi
echo "OK: single alembic head."
