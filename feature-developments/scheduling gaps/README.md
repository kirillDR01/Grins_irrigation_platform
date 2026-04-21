# Scheduling Gaps — Inbound SMS & Confirmation Flow

**Date:** 2026-04-20
**Scope:** Post-confirmation reschedule flow, Y/R/C handling, inbound correlation, UI surfacing.
**Source investigations:**
- Two parallel code-level audits (backend services, schema, webhook, audit; and frontend components, polling, queues).
- Instructions reference: `instructions/update2_instructions.md`.
- Seed concern: "if a user accepts but then in the future they want to reschedule and they press R even after pressing confirmation, we need to still be able to track their responses."

---

## How to read this folder

Each `gap-NN-*.md` is a **standalone incident spec**: reproduction, current behavior with file:line references, why it fails, downstream impact, proposed fix, edge cases, cross-references. Written to support either scoped fix PRs or broader feature planning.

Read in any order. Start with a gap relevant to the work you're planning, or start with the severity-1 items below.

---

## Severity matrix

**Severity scale**
- **1 (highest)** — Customer-facing bug with concrete repro and wrong outcome. Should be fixed soon.
- **2 (high)** — Correctness or UX gap with real operational cost. Plan a fix.
- **3 (medium)** — Gap that's tolerable today but should be fixed as part of normal feature work.
- **4 (low)** — Edge case, minor polish, or longer-term.

| Gap | Title | Severity | Area |
|---|---|---|---|
| [01](gap-01-reschedule-request-lifecycle.md) | Reschedule request lifecycle (duplicates, active-appt, free-text capture) | **1** | Backend |
| [02](gap-02-repeat-confirmation-idempotency.md) | Repeat confirmation idempotency | 3 | Backend |
| [03](gap-03-thread-correlation.md) | Thread correlation bugs (stale + missing thread_id on reschedule/cancel) | **2** | Backend |
| [04](gap-04-state-machine-not-enforced.md) | Appointment state machine not enforced | 3 | Backend |
| [05](gap-05-audit-trail-gaps.md) | Audit trail asymmetry (Y/R and opt-out not audited) | 3 | Backend |
| [06](gap-06-opt-out-management.md) | Opt-out management & visibility | **2** | Backend + UI |
| [07](gap-07-webhook-security-and-dedup.md) | Webhook security, Redis dedup, inbound rate limit | **2** | Backend |
| [08](gap-08-inbound-time-window.md) | Inbound time-window quiet-hours | 4 | Backend |
| [09](gap-09-mms-unicode-i18n.md) | MMS, unicode, non-English replies | 4 | Backend |
| [10](gap-10-static-no-reply-escalation.md) | Static no-reply escalation | 3 | Backend + UI |
| [11](gap-11-appointment-detail-inbound-blind.md) | AppointmentDetail modal is inbound-blind | **2** | Frontend |
| [12](gap-12-calendar-card-reply-state.md) | Calendar cards lack reply-state badges | 3 | Frontend |
| [13](gap-13-customer-messages-outbound-only.md) | CustomerMessages tab is outbound-only | 3 | Frontend |
| [14](gap-14-dashboard-alert-coverage.md) | Dashboard alert coverage (only 2 types defined) | 3 | Backend + Frontend |
| [15](gap-15-queue-freshness-and-realtime.md) | Queue freshness, no polling on key queues | 3 | Frontend |
| [16](gap-16-unified-sms-inbox.md) | No unified SMS inbox | 3 | Backend + Frontend |

---

## Reading orders by theme

### "Does the post-Y → then R flow work?" (the seed question)

Start here: [01](gap-01-reschedule-request-lifecycle.md) → [02](gap-02-repeat-confirmation-idempotency.md) → [03](gap-03-thread-correlation.md) → [04](gap-04-state-machine-not-enforced.md).

Short answer: the happy path works, but there are uniqueness, late-reschedule, and stale-thread failure modes that can misroute or duplicate replies.

### "What's customer-invisible but we should fix first?"

Severity-1 and 2 backend items: [01](gap-01-reschedule-request-lifecycle.md), [03](gap-03-thread-correlation.md), [06](gap-06-opt-out-management.md), [07](gap-07-webhook-security-and-dedup.md).

### "What's customer-visible but the admin can't see?"

[11](gap-11-appointment-detail-inbound-blind.md) → [12](gap-12-calendar-card-reply-state.md) → [13](gap-13-customer-messages-outbound-only.md) → [15](gap-15-queue-freshness-and-realtime.md) → [16](gap-16-unified-sms-inbox.md).

### "Compliance / opt-out / 10DLC concerns"

[06](gap-06-opt-out-management.md) → [05](gap-05-audit-trail-gaps.md) → [14](gap-14-dashboard-alert-coverage.md).

### "Robustness, security, edge cases"

[07](gap-07-webhook-security-and-dedup.md) → [04](gap-04-state-machine-not-enforced.md) → [08](gap-08-inbound-time-window.md) → [09](gap-09-mms-unicode-i18n.md) → [10](gap-10-static-no-reply-escalation.md).

---

## Suggested prioritization (opinionated)

This is a working suggestion, not a mandate. Dependencies matter — e.g., Gap 11 (AppointmentDetail) benefits heavily from Gap 05 (audit coverage), so do them near each other.

### Sprint 1 — safety net (~1 week)

Small, high-value fixes. Minimal design surface.

1. **Gap 01.A** — add partial unique index + application-level check on `RescheduleRequest(appointment_id) WHERE status='open'`.
2. **Gap 01.B** — add state guard in `_handle_reschedule` so EN_ROUTE/IN_PROGRESS replies branch to "call admin" rather than creating unresolvable requests.
3. **Gap 02** — mirror `_handle_cancel` dedup pattern in `_handle_confirm`; send reassurance SMS on repeat Y (rate-limited).
4. **Gap 03.A** — set `provider_thread_id` on reschedule/cancellation outbound SMSes; widen `find_confirmation_message` filter.

### Sprint 2 — correctness and compliance (~1-2 weeks)

5. **Gap 03.B** — add `superseded_at` to `sent_messages`; update `find_confirmation_message`; stale-reply handler.
6. **Gap 04** — enforce state transitions via `@validates("status")` on model; add CONFIRMED→SCHEDULED to the dict; centralize transitions.
7. **Gap 05 (partial)** — add `AuditLog` entries for the customer reply events missing today (Y, R, opt-out, admin-triggered reschedule notification).
8. **Gap 07** — add timestamp check to webhook signature; extend Redis TTL; fail-closed or DB-fallback dedup.

### Sprint 3 — UX lift (~2 weeks)

9. **Gap 11** — AppointmentDetail gets a "Communication" section reading from a new `/timeline` endpoint.
10. **Gap 12** — calendar cards get badges for pending reschedule, no-reply flagged, opted-out.
11. **Gap 06 (UI part)** — informal-opt-out triage page + OptOutBadge component.
12. **Gap 14** — add new alert types (pending reschedule, informal opt-out, unrecognized reply); dashboard widgets.
13. **Gap 15** — add polling to `RescheduleRequestsQueue`, `NoReplyReviewQueue`, `CustomerMessages`.

### Sprint 4+ — larger features

14. **Gap 13** — rebuild CustomerMessages as a threaded conversation view.
15. **Gap 10** — automated multi-stage no-reply escalation.
16. **Gap 16** — unified SMS inbox.
17. **Gap 09** — emoji / shorthand keyword expansion; MMS handling.
18. **Gap 08** — quiet-hours deferral for alerts and non-urgent inbound processing.

---

## Cross-gap dependencies (concise)

```
         Gap 05 (audit)
         /       \
      Gap 11    Gap 16 (inbox)
      /              \
Gap 12               Gap 13
   |                    |
   └──Gap 14 (alerts)───┘
        |
      Gap 15 (realtime/polling)

Gap 04 (state machine) underpins Gap 01.B, Gap 02
Gap 03 (thread correlation) underpins Gap 01.C, Gap 11, Gap 16
Gap 07 (webhook) underpins Gap 14 alerts for health
Gap 06 (opt-out) depends on Gap 05 for history; feeds Gap 11, 12, 14
```

---

## Not in scope

This investigation focused on the confirmation-reply flow (Y/R/C, reschedule, opt-out) and its surfaces. Out of scope:

- Scheduling poll feature (tracked separately in `feature-developments/CallRail collection/`).
- Outbound SMS rate-limit / quota management (working as intended).
- Email/signing flows (`feature-developments/email and signing stack/`).
- Voice/call integration.
- Invoice notification SMSes (separate lifecycle, minimal inbound).

---

## Terminology

- **Inbound / outbound** — direction of SMS relative to our system.
- **Confirmation SMS** — the initial Y/R/C prompt sent when admin clicks "Send Confirmation."
- **Reply / response** — inbound message from the customer. Often parsed to a keyword.
- **Reschedule request** — the queue item created when a customer replies R.
- **No-reply flag** — `needs_review_reason='no_confirmation_response'` set by nightly job.
- **Needs review** — a response that couldn't be parsed and has no open RescheduleRequest to attach to.
- **Orphan** — inbound that couldn't be correlated to any outbound.
- **Stale thread** — thread_id that refers to an outbound whose appointment has moved on.
- **Informal opt-out** — customer message matching a "please stop" phrase (not the exact STOP keyword).
