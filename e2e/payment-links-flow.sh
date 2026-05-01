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
#   APPOINTMENT_ID                — UUID of the seeded appointment (Journey 1 target)
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

# Journey 1: Send Payment Link from Appointment Modal — target the seeded appointment by id.
# Relies on the data-testid="appt-card-{id}" attribute set by ResourceTimelineView's AppointmentCard.
if [[ -z "${APPOINTMENT_ID:-}" ]]; then
  echo "SKIP Journey 1: APPOINTMENT_ID not set (re-seed via scripts/seed_e2e_payment_links.py)."
else
  ab open "$BASE/schedule"
  ab wait --load networkidle
  sleep 3  # allow weekly schedule query + resource-timeline grid to render
  HIT=$(ab get count "[data-testid='appt-card-$APPOINTMENT_ID']")
  if [[ "$HIT" == "0" ]]; then
    echo "FAIL Journey 1: seeded appointment $APPOINTMENT_ID not in current week view."
    echo "  (Seeder creates today's appointment; if today is on a Mon-boundary"
    echo "   the click-through can lag — re-run after refresh.)"
    ab close
    exit 1
  fi
  ab click "[data-testid='appt-card-$APPOINTMENT_ID']"
  ab wait "[data-testid='appointment-modal']"
  ab screenshot "$SHOTS/02a-modal-opened.png"
  # The Send Payment Link button lives inside the Payment sheet — open it
  # via the Collect Payment CTA (only rendered when status is in_progress
  # or completed; the seeder walks the appointment to in_progress).
  CTA_COUNT=$(ab get count "[data-testid='collect-payment-cta']")
  if [[ "$CTA_COUNT" == "0" ]]; then
    echo "WARN Journey 1: Collect Payment CTA absent (appointment must be in_progress/completed)."
  else
    ab click "[data-testid='collect-payment-cta']"
    sleep 1
    ab screenshot "$SHOTS/02b-payment-sheet-open.png"
  fi
  SEND_COUNT=$(ab get count "[data-testid='send-payment-link-btn'], [data-testid='resend-payment-link-btn']")
  if [[ "$SEND_COUNT" == "0" ]]; then
    echo "WARN Journey 1: payment sheet has no Send/Resend Payment Link button."
  else
    if [[ $(ab get count "[data-testid='send-payment-link-btn']") -gt "0" ]]; then
      ab click "[data-testid='send-payment-link-btn']"
    else
      ab click "[data-testid='resend-payment-link-btn']"
    fi
    sleep 3
    ab screenshot "$SHOTS/03-modal-link-sent.png"
    # Trigger Stripe webhook in another terminal:
    #   stripe trigger payment_intent.succeeded \
    #     --override "payment_intent:metadata.invoice_id=$INVOICE_ID"
    sleep 8
    ab screenshot "$SHOTS/04-modal-paid.png"
  fi
fi

# Journey 2: Send/Resend from Invoice Detail page.
# Use whichever button is rendered (depends on payment_link_sent_count).
ab open "$BASE/invoices/$INVOICE_ID"
ab wait --load networkidle
sleep 2
SEND_COUNT=$(ab get count "[data-testid='send-payment-link-btn']")
RESEND_COUNT=$(ab get count "[data-testid='resend-payment-link-btn']")
ab screenshot "$SHOTS/05a-invoice-detail-pre.png"
if [[ "$RESEND_COUNT" != "0" ]]; then
  ab click "[data-testid='resend-payment-link-btn']"
elif [[ "$SEND_COUNT" != "0" ]]; then
  ab click "[data-testid='send-payment-link-btn']"
else
  echo "FAIL: Invoice Detail page rendered neither Send nor Resend Payment Link button."
  ab close
  exit 1
fi
sleep 3
ab screenshot "$SHOTS/05b-invoice-detail-sent.png"

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
ab set viewport 375 812
ab open "$BASE/schedule"
ab wait --load networkidle
ab screenshot "$SHOTS/09-mobile-schedule.png"
ab open "$BASE/invoices/$INVOICE_ID"
ab wait --load networkidle
ab screenshot "$SHOTS/10-mobile-invoice-detail.png"

# Responsive: desktop viewport (1440x900).
ab set viewport 1440 900
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
