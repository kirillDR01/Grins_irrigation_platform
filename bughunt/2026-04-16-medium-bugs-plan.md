# Medium Bugs Resolution Plan — 2026-04-16

**Scope:** Resolve all 17 MEDIUM bugs (M-1 through M-17) from `2026-04-16-customer-lifecycle-bughunt.md`.
**Strategy:** Single PR stack on `fix/medium-bughunt-batch` off `dev`. 7 phases, parallelized where safe.
**Testing rules:** Mock email sender in all tests; the only phone allowed to receive a real SMS is `+19527373312`; OK to seed one throwaway test customer in dev DB.

---

## Bug → Phase map

| Phase | Bug | File | One-line fix |
|---|---|---|---|
| 1 | M-3 | `services/job_confirmation_service.py:38` | Extend Y/R/C keyword map with `ok, okay, yup, yeah, 1, different time, change time` |
| 1 | M-4 | `services/job_confirmation_service.py:51` | Parameterize confirm auto-reply with `{date}` and `{time}` |
| 1 | M-5 | `services/job_confirmation_service.py:52-55` | Replace reschedule ack text with spec-exact wording |
| 1 | M-6 | `api/v1/jobs.py:1583-1588` | Replace Google Review SMS with spec text; fix `Grin's Irrigations` typo |
| 2 | M-7 | `services/appointment_service.py:382-482` | Add audit log for update + reactivate paths |
| 2 | M-8 | `services/job_confirmation_service.py:_handle_cancel` | Audit customer-SMS cancel with `source="customer_sms"` |
| 3 | M-9 | `services/sms_service.py:810-837` | Route auto-replies through `send_message()` to create `SentMessage` rows |
| 4 | M-1 | `frontend/.../AppointmentDetail.tsx` | Render Send Confirmation button for DRAFT appointments |
| 4 | M-2 | `frontend/.../CancelAppointmentDialog.tsx:159` | Keep both buttons on DRAFT; disable SMS one with tooltip |
| 5 | M-12 | `schemas/invoice.py` + `frontend/.../InvoiceList.tsx:128-146` | Return `days_until_due` / `days_past_due` server-side |
| 5 | M-14 | `services/invoice_service.py:794-876` | Canonical merge keys + template validation |
| 5 | M-15 | `api/v1/webhooks.py:950-956` | 503 on missing secret, 400 only on signature mismatch |
| 6 | M-10 | `frontend/.../StatusActionButton.tsx:37-144` | Call `convertToJob` first on happy path, fall back to `advance` on error |
| 6 | M-11 | `api/v1/sales_pipeline.py:57-115` | Drop customer-scope fallback in `_get_signing_document` |
| 7 | M-13 | `services/contract_renewal_service.py:391-411` | Set PARTIALLY_APPROVED whenever APPROVED + (REJECTED or PENDING) |
| 7 | M-16 | `services/photo_service.py:278` | Enforce 25 MB + MIME allow-list server-side |
| 7 | M-17 | `frontend/.../DocumentsSection.tsx:34-59` | Resolve presign at render; hide buttons when null/expired |

---

## Phase order and parallelization

- **Phase 1** (SMS text + keywords): M-3, M-4, M-5, M-6 — 2 parallel subagents (SMS service + jobs.py).
- **Phase 2** (audit logs): M-7, M-8 — 1 subagent covering both (same pattern).
- **Phase 3** (sent_messages audit trail): M-9 — sequential after Phase 1 (shares helpers).
- **Phase 4** (schedule FE): M-1, M-2 — parallel with Phase 5 + 6.
- **Phase 5** (invoices): M-12, M-14, M-15 — parallel with Phase 4 + 6.
- **Phase 6** (sales pipeline): M-10, M-11 — parallel with Phase 4 + 5.
- **Phase 7** (renewal, uploads, docs): M-13, M-16, M-17 — 3 parallel subagents.

After each phase: `ruff check --fix`, `mypy`, `pyright`, `pytest -m unit`, `pytest -m functional` on touched modules. Zero violations required.

---

## Manual end-to-end SMS test plan

Only phone: **+19527373312**. Seed one test customer in dev (`phone=+19527373312`, `email=test-mock@example.invalid`, `is_test=True`). All other mass-notify / email paths use mocks.

| Step | Trigger | Reply | Verify |
|---|---|---|---|
| 1 | Send confirmation SMS | `Y` | M-4: auto-reply contains date & time |
| 2 | New appt, confirmation | `ok` | M-3: `ok` → CONFIRM |
| 3 | New appt, confirmation | `yup` | M-3: `yup` → CONFIRM |
| 4 | New appt, confirmation | `1` | M-3: `1` → CONFIRM |
| 5 | New appt, confirmation | `R` | M-5: spec-exact reschedule text |
| 6 | Wait for reschedule follow-up | `different time` | M-3: synonym; M-9: SentMessage row created |
| 7 | New appt, confirmation | `C` then `C` again | M-8: audit entry on first C; CR-3 short-circuit on second |
| 8 | Trigger Job Complete → Google Review | (no reply) | M-6: spec text, no apostrophe typo |

---

## Definition of done

- [ ] All 17 M-bugs have commits on `fix/medium-bughunt-batch`
- [ ] All unit + functional + frontend tests pass
- [ ] Ruff / MyPy / Pyright / tsc / eslint clean
- [ ] Manual E2E table above completed via `+19527373312`
- [ ] PR opened to `dev` with body listing each M-X and commit link
- [ ] `SentMessage` audit trail contains only `+19527373312` entries from this work

---

## Implementation prompt (paste into a fresh session)

````markdown
# Task: Resolve all 17 MEDIUM bugs from the 2026-04-16 customer lifecycle bughunt

## Repo
- Working dir: `/Users/kirillrakitin/Grins_irrigation_platform`
- Base branch: `dev` (integration branch, recent CR-1/CR-4/CR-6 merges are there)
- Work branch: create `fix/medium-bughunt-batch` off `dev`
- Land all 17 fixes as ONE PR stack on this single branch (not one PR per phase)

## Required reading (in this order)
1. `bughunt/2026-04-16-customer-lifecycle-bughunt.md` — sections `## MEDIUM` (M-1 through M-17). Treat each finding's **File**, **Evidence**, and **Fix** lines as authoritative scope.
2. `bughunt/2026-04-16-medium-bugs-plan.md` — this plan doc (phase order, bug→file map, test plan).
3. `.kiro/steering/code-standards.md`, `.kiro/steering/tech.md`, `.kiro/steering/structure.md`, `.kiro/steering/api-patterns.md`, `.kiro/steering/frontend-patterns.md`, `.kiro/steering/parallel-execution.md` — every change must follow these.
4. `instructions/update2_instructions.md` — the spec the bughunt was derived from. Reference when a fix requires "spec-exact" wording (M-4, M-5, M-6, M-14).

## Absolute testing rules (non-negotiable)
- **No real customer phone numbers or emails may receive any traffic during testing — ever.**
- The ONLY phone number allowed to receive a real SMS is `+19527373312` (the user's personal phone).
- Email: use a mock email sender in all tests (`@pytest.fixture` that stubs `email_service.send`). No real inbox.
- For end-to-end verification: seed ONE throwaway test customer in the dev DB with `phone="+19527373312"`, `email="test-mock@example.invalid"`, first_name="Test", last_name="User", `is_test=True` (so prod filters can exclude).
- Mass-notify paths (M-14) must filter to that single test customer or use mocks. Never iterate prod-shaped customer data.

## The 17 bugs — fixes to apply

### Phase 1 — SMS text & keyword alignment (parallel)
- **M-3** `src/grins_platform/services/job_confirmation_service.py:38` — extend `_KEYWORD_MAP` with `ok, okay, yup, yeah, 1` → CONFIRM; `2, different time, change time` → RESCHEDULE. Do NOT map `stop` (collides with compliance keyword).
- **M-4** `services/job_confirmation_service.py:51` — parameterize CONFIRM auto-reply: `"Your appointment has been confirmed. See you on {date} at {time}!"`. Build via helper reading `appt.scheduled_date` + `appt.time_window_start`. Mirror `format_sms_time_12h` already used in `_build_cancellation_message`.
- **M-5** `services/job_confirmation_service.py:52-55` — reschedule text must be exactly: `"We've received your reschedule request. We'll be in touch with a new time."`.
- **M-6** `src/grins_platform/api/v1/jobs.py:1583-1588` — replace Google Review SMS with: `"Thanks for choosing Grins Irrigation! We'd appreciate a quick review: {review_url}"`. Fix apostrophe + plural.

### Phase 2 — Audit log additions (parallel with Phase 1)
- **M-7** `services/appointment_service.py:382-482` — add `_record_update_audit` and `_record_reactivate_audit` mirroring the existing `_record_cancellation_audit`. Capture pre/post values and `notify_customer`. Call from both normal-update and the CANCELLED→SCHEDULED reactivation branch at line 418.
- **M-8** `services/job_confirmation_service.py:_handle_cancel` (around flush at line 281) — audit with `source="customer_sms"`. Reuse admin helper if signature allows, else create sibling.

### Phase 3 — Sent-messages audit trail (depends on Phase 1)
- **M-9** `services/sms_service.py:810-837` — route auto-reply and follow-up through `SMSService.send_message()` so `SentMessage` rows are created. Preserve the `recipient_phone` override (CallRail-masked inbound). Use `MessageType.APPOINTMENT_CONFIRMATION_REPLY` (create enum if missing) and `MessageType.RESCHEDULE_FOLLOWUP`.

### Phase 4 — Schedule frontend UX (parallel with Phase 5/6)
- **M-1** `frontend/src/features/schedule/components/AppointmentDetail.tsx` — conditionally render `SendConfirmationButton` when `appointment.status === 'draft'`.
- **M-2** `frontend/src/features/schedule/components/CancelAppointmentDialog.tsx:159` — on DRAFT, keep BOTH buttons; disable "Cancel & text customer" with tooltip `"Draft was never sent, no text needed."`. Do not collapse.

### Phase 5 — Invoices (parallel with Phase 4/6)
- **M-12** add `days_until_due: int | None` and `days_past_due: int | None` to `InvoiceResponse` (grep `InvoiceResponse` in `src/grins_platform/schemas/`). Compute server-side from `due_date` UTC-midnight. Remove `daysDiff(due_date)` branch in `frontend/src/features/invoices/components/InvoiceList.tsx:128-146`.
- **M-14** `services/invoice_service.py:794-876` — introduce canonical merge keys `{customer_name}, {invoice_number}, {amount}, {due_date}` in a shared `render_invoice_template()`. Map spec's `[Customer name]`-style brackets to canonical keys. Validate admin templates; reject 400 if required keys missing.
- **M-15** `src/grins_platform/api/v1/webhooks.py:950-956` — return `503` when webhook secret env var missing (infra — retry + page). Keep `400` only for signature-verification failures.

### Phase 6 — Sales pipeline (parallel with Phase 4/5)
- **M-10** `frontend/src/features/sales/components/StatusActionButton.tsx:37-144` — when status is `SEND_CONTRACT`, call `convertToJob.mutate()` first. Fall back to `advance` only on unexpected-state error.
- **M-11** `src/grins_platform/api/v1/sales_pipeline.py:57-115` `_get_signing_document` — remove `sales_entry_id IS NULL` fallback for active ops. If a legacy-read path is needed, gate behind explicit `include_legacy=True` param used only by reporting reads.

### Phase 7 — Renewal, uploads, document validation (final)
- **M-13** `services/contract_renewal_service.py:391-411` — set `PARTIALLY_APPROVED` whenever `APPROVED ∈ statuses AND (REJECTED ∈ statuses OR PENDING ∈ statuses)`. Keep terminal cases for all-APPROVED / all-REJECTED.
- **M-16** `services/photo_service.py` `upload_file()` (around line 278) — enforce 25 MB cap + MIME allow-list server-side at entry. Raise `ValueError` for size, `TypeError` for MIME. API layer maps to 413 / 415.
- **M-17** `frontend/src/features/sales/components/DocumentsSection.tsx:34-59` — resolve presigned URL at render via new `usePresignedUrl(file_key)` hook (TanStack Query). Hide/disable signing buttons when `file_key` null or presign returns 404/expired.

## Quality gates (every phase)
```bash
uv run ruff check --fix src/
uv run ruff format src/
uv run mypy src/
uv run pyright src/
uv run pytest -m unit -v
uv run pytest -m functional -v
cd frontend && npm run lint && npm run typecheck && npm run test
```
Zero violations / zero errors before commit.

## Tests (mandatory per code-standards.md §2)
Per fix, add minimum:
- Unit test (tests/unit/, `@pytest.mark.unit`, all deps mocked)
- Functional test (tests/functional/, real DB) for service-layer changes
- Frontend: RTL test per component change

Unit naming: `test_{method}_with_{condition}_returns_{expected}`.

## Manual E2E verification (ASK THE USER, do not invent)
After Phases 1+2+3 land:
1. Seed throwaway test customer (phone `+19527373312`, `is_test=True`).
2. Create test job + appointment.
3. For each step below, trigger the outbound SMS then STOP and ask the user to reply from their phone. Verify DB + SentMessage row + auto-reply content before next step.

| Step | Trigger | Ask user to reply | Verify |
|---|---|---|---|
| 1 | Send confirmation | `Y` | M-4: auto-reply has date & time |
| 2 | New appt, confirmation | `ok` | M-3: CONFIRM |
| 3 | New appt, confirmation | `yup` | M-3: CONFIRM |
| 4 | New appt, confirmation | `1` | M-3: CONFIRM |
| 5 | New appt, confirmation | `R` | M-5: exact spec text |
| 6 | Wait for reschedule follow-up | `different time` | M-3 + M-9: SentMessage row |
| 7 | New appt, confirmation | `C` then `C` again | M-8 audit; CR-3 short-circuit still holds |
| 8 | Job Complete → Google Review | (no reply) | M-6: spec text, no apostrophe |

Do NOT skip. If user unavailable, pause and wait.

## Parallelization
- Phase 1 → 2 parallel subagents (SMS service + jobs.py)
- Phase 2 → 1 subagent (both bugs share pattern)
- Phase 3 → sequential after Phase 1
- Phases 4+5+6 → 3 parallel subagents
- Phase 7 → 3 parallel subagents

Use `TaskCreate` to track all 17 items. Mark completed as each commit lands.

## Commit style
`fix(<area>): <imperative summary> (M-X)`
Example: `fix(sms): include appointment date/time in Y auto-reply (M-4)`

## Definition of done
- [ ] All 17 M-bugs have commits on `fix/medium-bughunt-batch`
- [ ] Unit + functional + frontend tests pass
- [ ] Ruff / MyPy / Pyright / tsc / eslint clean
- [ ] Manual E2E table completed via `+19527373312`
- [ ] PR opened to `dev` with body listing each M-X and commit link
- [ ] No real customer phones/emails touched — `SentMessage` query shows only `+19527373312`

Start by reading the bughunt doc and this plan in full, then create the branch and the TaskList.
````
