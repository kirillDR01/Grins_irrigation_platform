# 07 — Estimate button in appointment modal → SMS/email Yes/No → auto-job on approval

**Request (paraphrased):**
> Add an Estimate button right below Collect Payment. Works like Collect Payment: dropdown of common job-types/prices, option to add custom line items. Send to customer via SMS or email — not fancy. Customer clicks Yes/No. On Yes, auto-create a job in the Jobs tab for the week specified on the estimate, linked to this customer.

**Status:** 🟡 PARTIAL

---

## What exists today

- "Send Estimate" button visible in appointment modal (violet outline) alongside Collect Payment.
- `Estimate` model (`models/estimate.py:1-167`) with customer-facing approval token (`estimate.py:103-111`).
- `EstimateTemplate` model (`models/estimate_template.py`) — pre-defined job types/prices usable as a dropdown.
- `EstimateCreator.tsx` (`frontend/src/features/schedule/components/EstimateCreator.tsx:1-80`) — line item editor with custom add/remove.
- Estimate delivery via SMS/email implemented within `EstimateService`.

## Gaps

1. **Auto-job-on-approval:** The design handoff (`feature-developments/design_handoff_appointment_modal_combined/README.md §8.6`) calls for auto-creating a Job on customer "Yes." No code path was found that consumes the approval event and inserts into the Jobs table.
2. **Target week on the estimate:** The estimate likely doesn't currently carry a "week of" field that would drive the auto-job's `target_start_date`/`target_end_date`. ❓
3. **Approval landing page:** the customer-facing Yes/No page needs to exist (may already — didn't verify).

## TODOs

- [ ] **TODO-07a** Add a "target week" field to the estimate (single week or range).
- [ ] **TODO-07b** Build / verify the customer-facing estimate approval page (token-auth'd URL from the SMS/email).
- [ ] **TODO-07c** On approval, create a `Job` linked to `estimate.customer_id`, with `target_start_date` / `target_end_date` from the estimate's week, status `TO_BE_SCHEDULED`. Attach the line items as the job's scope.
- [ ] **TODO-07d** On rejection, record the reason (optional), close the estimate, no job created.
- [ ] **TODO-07e** Dropdown of common prices in the Estimate modal must read from the same source as #09 admin price list (so edits flow through).

## Clarification questions ❓

1. **Line item format in SMS:** you said "can honestly not even be anything good looking." OK — plain text: `Estimate from Grins: Sprinkler Head Repair — $75; Drip Line — $150. Reply YES to approve or view details here: <link>`. Confirm or refine.
2. **Who signs?** Is a customer's "Yes" click enough, or does an approved estimate need to flow into SignWell for formal signature before becoming a job? You've been using SignWell for contracts — does it apply here too?
3. **Edit after approval:** if the estimate is approved but the customer later wants changes, can the estimate be re-issued (new token, new job) or is it locked?
