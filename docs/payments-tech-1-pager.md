# Payments — One-Page Guide for Techs

**Architecture C: Stripe Payment Links via SMS.** Last updated 2026-04-28.

## The whole flow in one sentence

Tap **Send Payment Link** in the appointment → the customer gets an SMS → they tap the link and pay (Apple Pay, Google Pay, or card) → the invoice flips to **Paid** automatically and Stripe emails them a receipt.

You don't enter card numbers. You don't take a card. You don't need a reader.

## When to use what

| Customer paying with… | What you do |
|---|---|
| Apple Pay / Google Pay / credit card | **Send Payment Link** (in the appointment modal) |
| Cash | **Record Other Payment** → Cash |
| Check | **Record Other Payment** → Check |
| Venmo / Zelle | **Record Other Payment** → choose channel |
| Service-agreement covered | Nothing — invoice is already covered. The CTA is hidden. |

## Send Payment Link — step by step

1. Open the appointment.
2. Tap **Send Payment Link**.
3. Wait for the "Sent" confirmation. The screen will keep polling and flip to **Paid** on its own.
4. If the customer doesn't pay before you leave, that's fine — the link stays valid. The office or you can re-send it later.

## What to say

> "I'm sending you a text with a payment link. Tap it and pay with Apple Pay, Google Pay, or a card. You'll get a receipt by email."

## Resending a link

- Open the invoice (Appointment modal **or** Invoices page).
- Tap **Resend Payment Link**. Same link, fresh SMS. No charge to you to resend.

## Customer says they didn't get a receipt

You don't do anything. **Tell the office.** They (or anyone with Stripe Dashboard access) resend it from the charge detail in Stripe — no action in Grin's.

## Refunds and disputes

You don't handle these. The office issues refunds and responds to disputes from the Stripe Dashboard. The invoice updates itself when they do.

## Common questions

- **"Why don't we tap their card on the phone anymore?"** Apple Pay / Google Pay are faster, work on every modern phone, and we don't touch card data — fewer compliance headaches.
- **"What if there's no cell signal?"** Read the URL aloud, or have the customer pay later from home. The link doesn't expire just because they're driving away.
- **"What if the customer wants a paper receipt?"** They get an emailed receipt automatically. Forwarding it or printing it is on them.
- **"What if they want to pay part now and part later?"** Send the link for the full amount. They pay what they pay; the invoice tracks remaining balance and the office sends a follow-up.

## Reference

- Full operational runbook: [`docs/payments-runbook.md`](payments-runbook.md)
- Plan-of-record: `.agents/plans/stripe-tap-to-pay-and-invoicing.md`
