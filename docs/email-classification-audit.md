# `_classify_email` Audit

**Date:** 2026-05-14
**Scope:** Cluster H §13.1 — verify every `email_type` string passed to
`EmailService._send_email` is classified correctly so that
(a) suppression behavior matches CAN-SPAM intent, and
(b) we don't accidentally send a commercial promo via the transactional
path or, conversely, gate a transactional confirmation behind opt-in.

## Method

Source enumerated by `grep -n 'email_type=' src/grins_platform/services/email_service.py`.
Every callsite passes a hardcoded literal. Classification source of truth:
`EmailService._classify_email` (lines 184–210). Suppression source of truth:
`EmailService.check_suppression_and_opt_in` (lines 1097–1127).

`_classify_email` returns `EmailType.TRANSACTIONAL` for any string in its
hardcoded `transactional_types` set; otherwise `EmailType.COMMERCIAL`.
Commercial sends are gated by suppression list + opt-in; transactional
sends bypass both (CAN-SPAM permits transactional bypass of opt-out).

## Findings

| email_type | callsite (line) | classification | suppression behavior | issue? |
|---|---|---|---|---|
| `welcome` | 441 | TRANSACTIONAL | bypasses suppression / opt-out | none — onboarding-required |
| `estimate_sent` | 511 | TRANSACTIONAL | bypasses | none — customer-initiated estimate |
| `estimate_approved` | 607 | TRANSACTIONAL | bypasses | none — confirmation of a customer action |
| `payment_receipt` | 708 | TRANSACTIONAL | bypasses | none — receipt is CAN-SPAM transactional |
| `internal_estimate_decision` | 753 | TRANSACTIONAL | bypasses | none — internal staff alert, BCC suppressed |
| `internal_estimate_bounce` | 782 | TRANSACTIONAL | bypasses | none — internal staff alert, BCC suppressed |
| `confirmation` | 832 | TRANSACTIONAL | bypasses | none — MN auto-renewal confirmation |
| `renewal_notice` | 886 | TRANSACTIONAL | bypasses | none — MN-required renewal notice |
| `annual_notice` | 934 | TRANSACTIONAL | bypasses | none — annual recurring-billing notice (regulatory) |
| `cancellation_conf` | 991 | TRANSACTIONAL | bypasses | none — confirmation of customer-initiated cancellation |
| `lead_confirmation` | 1043 | TRANSACTIONAL | bypasses | none — confirmation of form submission |
| `sales_pipeline_nudge` | 1088 | TRANSACTIONAL | bypasses | **flag** — see below |
| `subscription_management` | 1128 | COMMERCIAL | gated by suppression + opt-in | none — unsubscribe / preferences UI; opt-out compliance correct |

## Discussion

### `sales_pipeline_nudge` (line 1088)

`_classify_email` includes `sales_pipeline_nudge` in `transactional_types`,
which means it bypasses suppression + opt-in. The naming "nudge" is
suggestive of a follow-up email; need to verify whether this is:

1. A response to a customer's pending estimate (customer-initiated → fine
   as transactional), OR
2. An unsolicited promotional reminder (commercial → should respect
   opt-out).

A quick read of the callers (`send_sales_pipeline_nudge_email` body)
points to a sales-rep-driven follow-up to an existing pending estimate
the customer has not yet decided on. The customer requested the estimate,
so the nudge is technically a transactional follow-up on a customer-
initiated transaction. Classification is **defensible** but borderline.

**Recommendation:** Leave as TRANSACTIONAL for now. Re-evaluate if the
"nudge" copy ever becomes templated promo content (e.g. "we miss you /
here's 10% off"); at that point it crosses into COMMERCIAL territory and
should be reclassified.

### `subscription_management` (line 1128)

This is the only COMMERCIAL classification. It is the unsubscribe /
preference-center email. Gating on `check_suppression_and_opt_in` is
**correct** — if a customer is already suppressed, we don't send them
another mail about managing preferences. If they want back in, they
click a re-opt-in link from a previous touchpoint.

### Internal helpers (`internal_estimate_decision`, `internal_estimate_bounce`)

Both pass `allow_bcc=False` after the Cluster H §12 changes — they are
internal staff alerts, not customer-facing, so they intentionally do not
BCC `info@grinsirrigation.com` even when `OUTBOUND_BCC_EMAIL` is set in
prod.

## Conclusion

No misclassifications require a code change in this pass. `sales_pipeline_nudge`
flagged for re-review if the copy ever becomes promotional. **Audit-only
deliverable; no PR-side fixes needed.**
