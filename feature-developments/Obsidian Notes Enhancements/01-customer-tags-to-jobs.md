# 01 — Customer tags propagate to jobs (+ tag edits from appointment modal)

**Request (paraphrased):**
> Permeate the tags from the customer over to any of the jobs that are created. Also: give staff the ability to update tags within the specific appointment; that update should permeate through the customer tab and any future jobs for that specific customer.

**Status:** ❌ NOT IMPLEMENTED for jobs · ✅ Tag editor-in-modal exists but only writes to Customer

---

## What exists today

- `Customer` has a tags relationship via `CustomerTag` (`src/grins_platform/models/customer.py:215-220`).
- Appointment modal has an **Edit tags** button that opens `TagEditorSheet.tsx`. Footer reads *"Save tags · applies everywhere — past and future."* Writes go through `useSaveCustomerTags` → `customer_tag_service.py` → `CustomerTag`.
- Backend: `services/customer_tag_service.py` persists tags against the Customer entity.

## What's missing

- `Job` model has **no** `tags` field or relationship (`src/grins_platform/models/job.py`, lines 1–397 scanned).
- `JobService.create_job` (`src/grins_platform/services/job_service.py:223-322`) does **not** copy the customer's tags onto the new job.
- There is therefore no "tag-permeation" to future jobs — there is nothing on the job side to permeate *to*.

## TODOs

- [ ] **TODO-01a** Add `JobTag` association table + `Job.tags` relationship mirroring `CustomerTag`.
- [ ] **TODO-01b** In `JobService.create_job`, copy the parent customer's tag set onto the new job at creation time.
- [ ] **TODO-01c** When a user edits tags via `TagEditorSheet`, cascade the change to the customer's jobs. Open question on scope — see ❓ below.
- [ ] **TODO-01d** Expose job-level tags in the jobs table / job detail view so the propagation is visible.

## Clarification questions ❓

1. **Scope of cascade on edit:** When staff edit tags on one appointment, should those edits update:
   - only `TO_BE_SCHEDULED` future jobs?
   - also `SCHEDULED` and `IN_PROGRESS` jobs?
   - historical (completed) jobs too?
   The current modal footer says "past and future" — does that mean customer-level only, or also past jobs?
2. **Job-specific tags vs inherited:** Should jobs be able to carry *extra* tags beyond the customer's tag set, or must job.tags always equal customer.tags (pure mirror)?
3. **Tag removal:** If a customer tag is deleted, should it auto-remove from all related jobs, or stay on historical jobs as an audit trail?
