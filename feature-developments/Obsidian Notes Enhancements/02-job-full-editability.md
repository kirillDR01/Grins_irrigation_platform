# 02 — Every part of a job editable (especially "week of")

**Request (paraphrased):**
> Make sure every part of the jobs is able to be modified, like the week of.

**Status:** 🟡 PARTIAL

---

## What exists today

- `JobUpdate` schema (`src/grins_platform/schemas/job.py:196-212`) includes `target_start_date` and `target_end_date` as optional editable fields, plus customer/property/service/notes.
- `JobService.update_job` (`src/grins_platform/services/job_service.py:356-416`) handles partial updates.

## The restriction

- `src/grins_platform/services/job_service.py:387-397` — edits to `target_start_date` / `target_end_date` are **only allowed while `job.status == TO_BE_SCHEDULED`**.
- Comment at lines 382-386 explains the reason: once an appointment is attached, moving the target window would desync the appointment.
- Raises `JobTargetDateEditNotAllowedError` otherwise.

## What this means for "edit the week of"

- Before scheduling: works.
- After scheduling / in-progress / completed: blocked.

## TODOs

- [ ] **TODO-02a** Decide desired behavior when a scheduled job needs its target week changed:
  - Option A: keep the lock; users must unschedule first (cancel/move appointment), then edit.
  - Option B: allow edit, and auto-reschedule or detach the attached appointment with an explicit confirm dialog.
  - Option C: allow edit on any status, but require a reason string for audit.

## Clarification question ❓

1. Which of the above options matches what you meant by "every part of the job is modifiable"? If (B) or (C), what should happen to an existing scheduled appointment when the window changes — keep it, move it, or require user to reschedule manually?
