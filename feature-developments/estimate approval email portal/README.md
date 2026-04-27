# Estimate Approval via Email + Tokenized Portal Link

**Status:** Planning, not yet started
**Author:** 2026-04-25 investigation pass
**Scope:** Send the customer an email with a tokenized portal link so they can approve or reject an estimate from their browser. Capture the approve/reject decision with timestamp + IP + user agent for an audit trail.

## TL;DR

Most of this feature is already built. The Estimate model has all the columns, the public portal API is live, the frontend route + page exist, and admin already has a `/send` endpoint. The single missing link is **outbound email** — `EmailService._send_email` is a logger stub with no provider plugged in, and there is no `estimate_sent.html` template.

In other words: the right framing is "wire email to the existing portal flow" — not "build an approval portal."

## Documents in this folder

| File | Purpose |
|---|---|
| [`current-state.md`](current-state.md) | What's already wired vs. what's missing, with file:line citations |
| [`design.md`](design.md) | Design decisions for the missing pieces (template, URL config, post-approval handoff, security) |
| [`vendor-decision.md`](vendor-decision.md) | Email vendor pricing refresh (April 2026) + code-fit analysis. **Decided: Resend, starting on free tier (3K/mo, 100/day).** |
| [`build-plan.md`](build-plan.md) | Phased tasks from "decide vendor" through "ship to prod" with rough sizes |
| [`open-questions.md`](open-questions.md) | Questions to settle with the user before building |

## Related prior work

- `../email and signing stack/stack-research-and-recommendations.md` — full vendor research; concludes Resend free tier (with AWS SES as fallback) for outbound email. **This is the source of truth for the vendor question — don't re-litigate it here.**
- `../signing document/signing-document-panel.md` — the SignWell signing flow that runs **after** estimate approval. Signing is a separate stage from estimate approval.

## What this feature is NOT

- It is not a customer payment portal — invoices have a separate `invoice_token` flow already. Pay-an-invoice is out of scope here.
- It is not the contract signing flow — that's SignWell, triggered after the estimate is approved.
- It is not a generic email-system rebuild — only the work needed to make the existing estimate flow actually send a styled email.
- It does not change the data model. Schema is already correct.

## Touched code (preview)

| Area | Existing | Will change | Will add |
|---|---|---|---|
| Backend service | `EmailService` (`email_service.py`) | `_send_email` body, `__init__` provider init | `send_estimate_email(...)` public method |
| Backend service | `EstimateService.send_estimate` | Replace the `estimate.email.queued` log with a real call | — |
| Templates | `templates/emails/welcome.html`, etc. | — | `estimate_sent.html` (and likely `estimate_approval_received.html` for the office) |
| Settings | `EmailSettings`, `EstimateService` ctor | Move `portal_base_url` from a hardcoded default into settings | `RESEND_API_KEY` (or `AWS_SES_*`) env wiring |
| Frontend | `EstimateReview.tsx`, `portalApi.ts` | Maybe — verify rendering of all line-item shapes; a11y pass | None (route/page already exist) |

No DB migration is required.
