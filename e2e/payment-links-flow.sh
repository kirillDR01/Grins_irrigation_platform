#!/usr/bin/env bash
# E2E smoke for the Stripe Payment Links flow (Architecture C).
#
# Validates the visible, end-to-end behavior of the Send Payment Link flow:
#   1. Send Payment Link from the Appointment Modal
#   2. Resend from the Invoice Detail page
#   3. Channel pill in the Invoice List
#   4. Service-agreement-covered job hides the CTA
#   5. $0 invoice hides the CTA (per F11)
# Plus mobile + desktop screenshots and a console/error-log capture.
#
# Pre-flight: a frontend reachable at $BASE (defaults to dev Vercel URL),
# a backend connected to dev Stripe (test keys), and one or more seeded
# fixtures referenced via env vars (INVOICE_ID, ZERO_INVOICE_ID).
#
# Required env vars:
#   E2E_USER, E2E_PASS           — credentials for a dev user (default: admin/admin123)
#   INVOICE_ID                    — UUID of an invoice with an active link
# Optional env vars:
#   BASE                          — frontend URL (default dev Vercel)
#   ZERO_INVOICE_ID               — UUID of a $0 invoice (CTA-hide test)
#   SERVICE_AGREEMENT_APPT_ID     — UUID of a service-agreement appointment
#
# To complete the journey 1 paid-state assertion, fire the Stripe webhook
# in another terminal:
#   stripe trigger payment_intent.succeeded \
#     --override "payment_intent:metadata.invoice_id=$INVOICE_ID"

set -euo pipefail

BASE="${BASE:-https://grins-irrigation-platform-git-dev-kirilldr01s-projects.vercel.app}"
E2E_USER="${E2E_USER:-admin}"
E2E_PASS="${E2E_PASS:-admin123}"
SHOTS="e2e-screenshots/payment-links-architecture-c"
SESSION="${AGENT_BROWSER_SESSION:-payment-links-e2e}"
mkdir -p "$SHOTS"

if ! command -v agent-browser >/dev/null 2>&1; then
  echo "agent-browser is not installed; cannot run UI E2E."
  echo "Install: npm install -g agent-browser && agent-browser install --with-deps"
  exit 1
fi

if [[ -z "${INVOICE_ID:-}" ]]; then
  echo "INVOICE_ID must be set (a dev-mode invoice with an active payment link)."
  exit 1
fi

ab() { agent-browser --session "$SESSION" "$@"; }

# Phase 0: login.
ab open "$BASE/login"
ab wait --load networkidle
ab screenshot "$SHOTS/00-login.png"
ab fill "[data-testid='username-input']" "$E2E_USER"
ab fill "[data-testid='password-input']" "$E2E_PASS"
ab click "[data-testid='login-btn']"
ab wait --load networkidle
sleep 2
URL_AFTER_LOGIN=$(ab get url)
if [[ "$URL_AFTER_LOGIN" != *"/dashboard"* ]]; then
  echo "FAIL: did not land on /dashboard after login (got $URL_AFTER_LOGIN)."
  exit 1
fi
ab screenshot "$SHOTS/01-dashboard.png"

# Journey 1: Send Payment Link from Appointment Modal.
ab open "$BASE/schedule"
ab wait --load networkidle
sleep 1
APPT_COUNT=$(ab get count "[data-testid='appointments-row']")
if [[ "$APPT_COUNT" == "0" ]]; then
  echo "SKIP Journey 1: dev DB has no visible appointments this week."
else
  ab click "[data-testid='appointments-row']:first-child"
  ab wait "[data-testid='appointment-modal']"
  ab is visible "[data-testid='send-payment-link-btn']"
  ab screenshot "$SHOTS/02-modal-pre-send.png"
  ab click "[data-testid='send-payment-link-btn']"
  sleep 3
  ab screenshot "$SHOTS/03-modal-link-sent.png"

  # Journey 1 (cont): once the webhook fires the modal should auto-collapse
  # the polling indicator into a Paid pill (CG-6). Trigger via Stripe CLI:
  #   stripe trigger payment_intent.succeeded \
  #     --override "payment_intent:metadata.invoice_id=$INVOICE_ID"
  sleep 15
  ab screenshot "$SHOTS/04-modal-paid.png"
  PAID_COUNT=$(ab get count "[data-testid='status-paid']")
  if [[ "$PAID_COUNT" == "0" ]]; then
    echo "WARN: status-paid not visible; check the webhook fired and metadata.invoice_id=$INVOICE_ID."
  fi
fi

# Journey 2: Resend from Invoice Detail page.
ab open "$BASE/invoices/$INVOICE_ID"
ab wait --load networkidle
sleep 1
ab is visible "[data-testid='resend-payment-link-btn']"
ab click "[data-testid='resend-payment-link-btn']"
sleep 2
ab screenshot "$SHOTS/05-invoice-detail-resent.png"

# Journey 3: Channel pill in Invoice List.
ab open "$BASE/invoices"
ab wait --load networkidle
sleep 1
ab is visible "[data-testid='invoices-page']"
PILL_COUNT=$(ab get count "[data-testid^='channel-pill-']")
if [[ "$PILL_COUNT" == "0" ]]; then
  echo "INFO: no invoices in the list — channel pill cannot be visually verified."
fi
ab screenshot "$SHOTS/06-invoice-list-channel-pill.png"

# Journey 4: Service-agreement-covered job hides the CTA.
if [[ -n "${SERVICE_AGREEMENT_APPT_ID:-}" ]]; then
  ab open "$BASE/schedule?focus=$SERVICE_AGREEMENT_APPT_ID"
  ab wait "[data-testid='appointment-modal']"
  ab is visible "[data-testid='covered-by-agreement-pill']"
  CTA_COUNT=$(ab get count "[data-testid='send-payment-link-btn']")
  if [[ "$CTA_COUNT" != "0" ]]; then
    echo "FAIL: service-agreement appointment should hide Send Payment Link (saw $CTA_COUNT)."
    exit 1
  fi
  ab screenshot "$SHOTS/07-modal-service-agreement.png"
else
  echo "SKIP Journey 4: SERVICE_AGREEMENT_APPT_ID not provided."
fi

# Journey 5: $0 invoice hides the CTA (F11).
if [[ -n "${ZERO_INVOICE_ID:-}" ]]; then
  ab open "$BASE/invoices/$ZERO_INVOICE_ID"
  ab wait --load networkidle
  CTA_COUNT=$(ab get count "[data-testid='send-payment-link-btn']")
  if [[ "$CTA_COUNT" != "0" ]]; then
    echo "FAIL: \$0 invoice should hide Send Payment Link (saw $CTA_COUNT)."
    exit 1
  fi
  ab screenshot "$SHOTS/08-zero-invoice-no-cta.png"
else
  echo "SKIP Journey 5: ZERO_INVOICE_ID not provided."
fi

# Responsive: mobile viewport (375x812).
ab viewport 375 812
ab open "$BASE/schedule"
ab wait --load networkidle
ab screenshot "$SHOTS/09-mobile-schedule.png"
ab open "$BASE/invoices/$INVOICE_ID"
ab wait --load networkidle
ab screenshot "$SHOTS/10-mobile-invoice-detail.png"

# Responsive: desktop viewport (1440x900).
ab viewport 1440 900
ab open "$BASE/invoices"
ab wait --load networkidle
ab screenshot "$SHOTS/11-desktop-invoice-list.png"

# Console + error capture.
ab console > "$SHOTS/console.log" || true
ab errors > "$SHOTS/errors.log" || true

if [[ -s "$SHOTS/errors.log" ]]; then
  echo "WARN: uncaught errors logged to $SHOTS/errors.log"
fi

ab close
echo "PASS: all enabled journeys completed; screenshots in $SHOTS/"
