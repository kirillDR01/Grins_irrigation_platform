#!/usr/bin/env bash
# E2E smoke for the WebAuthn / Passkey UI surfaces.
#
# What this validates: the visible, non-biometric parts of the flow —
# the login page button, the settings security card, and the add-passkey
# dialog's validation. The OS biometric prompt itself cannot be driven by
# Playwright/Chromium; manual hardware testing is required for that
# (see Task 29 in the spec).
#
# Pre-flight: dev servers must be running:
#   uv run uvicorn grins_platform.main:app --port 8000
#   (cd frontend && npm run dev)
#
# Required env vars: E2E_USER, E2E_PASS.

set -euo pipefail

BASE="${BASE:-http://localhost:5173}"
SHOTS="e2e-screenshots/webauthn"
mkdir -p "$SHOTS"

if ! command -v agent-browser >/dev/null 2>&1; then
  echo "agent-browser is not installed; cannot run UI E2E."
  exit 1
fi

if [[ -z "${E2E_USER:-}" || -z "${E2E_PASS:-}" ]]; then
  echo "E2E_USER and E2E_PASS must be set."
  exit 1
fi

# Phase 1: login page renders the biometric button alongside password login.
agent-browser open "$BASE/login"
agent-browser wait --load networkidle
agent-browser is visible "[data-testid='login-page']"
agent-browser is visible "[data-testid='passkey-login-btn']"
agent-browser screenshot "$SHOTS/01-login-with-passkey-btn.png"

# Phase 2: log in with password to reach the settings page.
agent-browser fill "[data-testid='username-input']" "$E2E_USER"
agent-browser fill "[data-testid='password-input']" "$E2E_PASS"
agent-browser click "[data-testid='login-btn']"
agent-browser wait --url "**/dashboard*"

# Phase 3: settings → security card visible.
agent-browser open "$BASE/settings"
agent-browser wait --load networkidle
agent-browser is visible "[data-testid='security-page']"
agent-browser screenshot "$SHOTS/02-security-page.png"

# Phase 4: add-passkey dialog opens.
agent-browser click "[data-testid='add-passkey-btn']"
agent-browser wait "[data-testid='passkey-form']"
agent-browser is visible "[data-testid='device-name-input']"
agent-browser screenshot "$SHOTS/03-add-passkey-dialog.png"

# Phase 5: empty submission shows the RHF/Zod 'Required' message.
agent-browser click "[data-testid='submit-passkey-btn']"
agent-browser wait --text "Required"
agent-browser screenshot "$SHOTS/04-validation-error.png"

# Phase 6: capture console + JS errors for diagnostics.
agent-browser console > "$SHOTS/console.log"
agent-browser errors > "$SHOTS/errors.log"
if [[ -s "$SHOTS/errors.log" ]]; then
  echo "JS errors detected during E2E:"
  cat "$SHOTS/errors.log"
  exit 1
fi

agent-browser close
echo "agent-browser E2E passed for webauthn UI surfaces."
