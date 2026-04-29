# Payments Runbook — Stripe Payment Links via SMS (Architecture C)

Operational reference for office staff and engineers. Last updated 2026-04-28.

For the field-tech version, see [`payments-tech-1-pager.md`](payments-tech-1-pager.md).
For the architectural plan, see [`.agents/plans/stripe-tap-to-pay-and-invoicing.md`](../.agents/plans/stripe-tap-to-pay-and-invoicing.md).

---

## How payment works (one paragraph)

Every invoice with a balance gets a hosted Stripe Payment Link. We send the link to the customer over SMS (or email as fallback). The customer pays at the Stripe-hosted page using Apple Pay, Google Pay, or a card. Stripe fires a webhook back to the platform; the webhook handler looks up the invoice via `metadata.invoice_id` we set ourselves, marks it **Paid**, and Stripe emails the customer a receipt. No card data ever touches our servers. Cash, check, Venmo, and Zelle bypass Stripe entirely and use **Record Other Payment**.

---

## Monitoring

| Cadence | Check | Where |
|---|---|---|
| Daily | Spot-check 5 random PAID invoices against Stripe Dashboard charges | Stripe Dashboard → Payments |
| Daily | Look for `processing_status='failed'` rows in `stripe_webhook_events` (target: zero) | DB / admin SQL |
| Weekly | Conversion rate: count(invoices.paid_at) / count(payment_link_sent_count > 0) over the last 7 days. Target: ≥70%. | DB / metrics |
| On-call | Any `charge.dispute.created` should page the on-call admin. Stripe gives ~7 days to respond. | Webhook → alert |

---

## Reading link state on an invoice

Each invoice carries five fields that describe its payment-link lifecycle:

| Column | Meaning |
|---|---|
| `stripe_payment_link_id` | The Stripe Payment Link object id (`plink_…`). Null until first create. |
| `stripe_payment_link_url` | The customer-facing URL we send over SMS. Null until first create. |
| `stripe_payment_link_active` | False after the link is consumed (paid) or invalidated by a regenerate. |
| `payment_link_sent_at` | Last time we successfully sent the link to the customer. |
| `payment_link_sent_count` | Total send attempts (initial + every resend). Used for the conversion ratio. |

**Quick interpretations:**
- `_active=true`, `paid_at=null` → link is live, customer hasn't paid yet.
- `_active=false`, `paid_at` set → customer paid; link is consumed. Don't resend.
- `_active=false`, `paid_at=null` → link was invalidated (line items changed, regenerate ran). A new link should already exist on the row.

---

## Resending a payment link

From the office:
1. Open the invoice (Invoices page → row → detail; or the Appointment modal).
2. Tap **Resend Payment Link**.
3. SMS is sent again. The same URL is reused unless the invoice was updated since last send (in which case a new link is regenerated automatically before the SMS goes out).

Field staff can do the same from the Appointment modal — both surfaces hit the same endpoint.

---

## Customer says they didn't get a receipt (CG-19)

**No Grin's-side action.** Receipts are emailed by Stripe automatically.

1. Stripe Dashboard → Payments → click the charge.
2. Click **Resend receipt**.
3. If the customer's email is wrong, update it in the same dialog before resending.

---

## Refunds

Always initiated from the Stripe Dashboard:

1. Stripe Dashboard → Payments → click the charge.
2. **Refund** → choose full or partial amount → confirm.
3. Wait. The `charge.refunded` webhook auto-reconciles back to the invoice:
   - Full refund → invoice transitions to **REFUNDED**, `Job.payment_collected_on_site = False`.
   - Partial refund → invoice transitions to **PARTIAL** with the remaining balance recomputed.
4. Verify the invoice flipped within ~30 seconds. If not, check `stripe_webhook_events` for the event id and see [Webhook troubleshooting](#webhook-troubleshooting).

---

## Disputes

Time-sensitive — Stripe's response window is hard.

1. On `charge.dispute.created`, the on-call admin is paged and the invoice transitions to **DISPUTED**.
2. Open the dispute in Stripe Dashboard → Disputes.
3. Submit evidence (work order, signed estimate, photos, SMS history) inside Stripe.
4. Add a free-text note on the Grin's invoice for internal context.
5. The dispute outcome (`charge.dispute.closed`) is **not** wired to a webhook in Architecture C. Update the invoice manually after Stripe rules.

---

## When the auto-create-link hook fails on invoice creation

By design, Payment Link creation is best-effort: a Stripe outage or rate-limit at invoice-creation time does **not** block the invoice. Watch for log entry `payment_link.create_failed_at_invoice_creation`.

- The link gets created on the first **Send Payment Link** click instead.
- No manual action is required unless you're seeing many failures back-to-back. In that case check Stripe status (status.stripe.com) and look for a deploy that bumped `stripe_api_version`.

---

## Webhook troubleshooting

The webhook endpoint is `POST /api/v1/webhooks/stripe`. Every event is logged to the `stripe_webhook_events` table with one of:
- `processing_status='completed'` — handled successfully, idempotent on replay.
- `processing_status='failed'` — handler raised; check the `error` column.
- `processing_status='ignored'` — event type we don't handle (expected for many event types).

Common symptoms:
- **Invoice didn't flip to PAID after a known successful charge** → look up the event by `payment_intent.id`. If `processing_status='failed'`, read `error`. If the row is missing entirely, Stripe never delivered — check the endpoint health in Stripe Dashboard → Developers → Webhooks.
- **`metadata.invoice_id` missing on the PaymentIntent** → the matcher falls back to charge-description heuristics (CG-7/CG-13). If both miss, the event lands in `processing_status='failed'` with reason `invoice_id_unresolved`. Manual reconciliation: find the invoice by customer + amount + recent date, then run the admin "mark paid" action.
- **Subscription invoice landing on a service-agreement invoice path** → CG-7 short-circuit on `event.data.object.invoice` non-null prevents this. If you see the failure, the short-circuit regressed.

---

## Webhook secret rotation

Run this on a quiet hour. The endpoint will reject events for a few seconds during the swap.

1. Stripe Dashboard → Developers → Webhooks → endpoint → **Roll signing secret**.
2. Copy the new `whsec_…` value.
3. Update `STRIPE_WEBHOOK_SECRET` in Railway (production env first, then staging/dev).
4. Restart the backend service in Railway.
5. Verify with `stripe trigger payment_intent.succeeded` and confirm a `processing_status='completed'` row in `stripe_webhook_events`.

---

## Stripe API version bump

The version is pinned at `StripeSettings.stripe_api_version` (`src/grins_platform/services/stripe_config.py`). Currently `2025-03-31.basil`.

Bumping is a deliberate PR, not a config change:
1. Read the Stripe API changelog between current version and target.
2. Identify event-shape changes touching: `payment_intent.succeeded`, `charge.refunded`, `charge.dispute.created`, `customer.subscription.*`, `payment_link.*`.
3. Update fixtures in `tests/integration/test_payment_link_flow_integration.py` if shapes changed.
4. Bump `stripe_api_version` default and re-run the webhook integration suite.
5. Deploy to dev → run `stripe trigger` for each subscribed event type → verify all land as `completed`.
6. Deploy to staging, then production.

Do **not** unpin (i.e. set to empty / "latest"). Stripe rolls breaking changes silently into "latest"; we hold the line.

---

## Adding a new tech

Architecture C requires **no Stripe Dashboard access** for techs. Only office admins handling refunds and disputes need Dashboard logins.

1. Create the Grin's account with role = Technician.
2. Standard onboarding (mobile app login, push permissions, schedule walk-through).
3. Hand them [`payments-tech-1-pager.md`](payments-tech-1-pager.md) — that's the entire payments training.

---

## Edge cases reference

- **$0 invoice** → no link is created (F11). The Send Payment Link CTA is hidden.
- **Service-agreement-covered job** → no link, no CTA. Subscription billing handles it.
- **Lead-only appointment (no customer)** → CTA hidden + backend safety net rejects the request.
- **Cancelled-while-pending** (CG-8) → if a webhook arrives after the invoice was cancelled, the handler refuses, logs `payment_link.charge_against_cancelled_invoice`, and pages an admin to issue a manual refund.
- **Two-payment installment** (CG-10) → matcher recognizes the PARTIAL → balance state and applies the second payment to the remaining amount.
- **Bare `pi_*` reference in admin search** (CG-13) → search auto-prefixes with `stripe:` so it matches stored references.

---

## Related files (for engineers)

- Service: `src/grins_platform/services/stripe_payment_link_service.py`
- Webhook handler: `src/grins_platform/api/v1/webhooks.py`
- Config: `src/grins_platform/services/stripe_config.py`
- Invoice model fields: `src/grins_platform/models/invoice.py:179-198`
- Frontend hook: `frontend/src/features/invoices/hooks/useInvoiceMutations.ts`
- E2E script: `e2e/payment-links-flow.sh` (added in Phase 6 of the rollout plan)

---

## Deprecated / legacy

The following modules predate Architecture C and exist only as a placeholder for a possible future Capacitor-wrapped Tap-to-Pay flow:

- `src/grins_platform/services/stripe_terminal.py`
- `src/grins_platform/api/v1/stripe_terminal.py`
- `frontend/src/features/schedule/api/stripeTerminalApi.ts`

Do **not** import these in new code. They will be removed in a follow-up cleanup PR once it is confirmed no Capacitor work is upcoming.
