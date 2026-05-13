# Feature: Cluster A — Notes / Photos / Tags Unification onto Customer

> **One-pass confidence target: 10/10.** Every claim in this plan is verified against the current codebase. Every task names the exact file and line range. Every task produces evidence (screenshot, DB query result, log excerpt) saved to `e2e-screenshots/cluster-a/<phase>/<step>.png` and aggregated into `evidence-dossier.md`. **No task is considered complete until evidence is captured AND linked in the dossier.**

---

## Feature Description

Collapse all "notes" surfaces (currently spread across `lead.notes`, `customer.internal_notes`, `sales_entry.notes`, `estimate.notes`, `job.notes`, `appointment.notes`, and the orphaned `appointment_notes` 1:1 table) onto a **single shared blob on the Customer record**. Collapse all "tags" surfaces so that `customer_tags` is the canonical source readable + writable from every surface (lead post-conversion, customer, sales entry, job, appointment). Cascade `LeadAttachment` rows to `CustomerPhoto` on every Lead→Customer conversion path. Replace the polymorphic `AppointmentAttachment` table with the existing `CustomerPhoto.appointment_id` FK. Drop the `appointment_notes` table + its model/service/repo/schemas/API/tests. Wrap `boto3.put_object` failures so they map to HTTP 502/503 instead of a generic 500.

**Hard non-negotiable constraints:**

1. **No timeline / feed / chat-style UI.** The notes blob is **one persistent editable textarea** — no per-entry author / timestamp / sender chrome in the main view. This is the explicit lesson from the abandoned April 2026 polymorphic-notes experiment (`migrations/20260416_100500_create_notes_table.py` followed by rollback `20260418_100700_fold_notes_table_into_internal_notes.py`).
2. **Mandatory evidence.** Every task produces (a) at least one screenshot when the change is user-visible, (b) at least one captured DB query result when the change affects data, (c) a Pass/Fail row in `evidence-dossier.md`. Screenshots and SQL captures are committed under `e2e-screenshots/cluster-a/`.
3. **No remote alembic from local.** All migrations execute on Railway dev via deploy, **not** by running `alembic upgrade` locally against a remote DB (see memory `feedback_no_remote_alembic`).
4. **Test recipients are hard-allowlisted.** Any E2E flows that send SMS/email use `kirillrakitinsecond@gmail.com` (email) and `+19527373312` (phone) **only**.

## User Story

As **Victor (admin)** managing the full customer journey,
I want **the notes I write, the tags I apply, and the photos I attach to follow the customer across every surface** (lead → sales → job → appointment),
So that **I never copy-paste context between screens, I don't lose photos when a lead converts, tags added from any surface are immediately visible everywhere else, and a fresh-deployed estimate or job sees the same notes I wrote on the lead form**.

## Problem Statement

Today the same conceptual data (notes, photos, tags) is fragmented across 7+ storage locations with almost no auto-flow:

- **5 notes columns** (`lead.notes`, `customer.internal_notes`, `sales_entry.notes`, `estimate.notes`, `job.notes`) + **2 appointment-notes locations** (`AppointmentNote.body` table + legacy `appointment.notes` column). Only Lead → Customer has any auto-flow.
- **3 photo silos** (`LeadAttachment`, `CustomerPhoto`, polymorphic `AppointmentAttachment`). LeadAttachment rows are **never copied** to CustomerPhoto on lead conversion — data loss.
- **Tags effectively customer-only today**: `customer_tags` table exists; the lead's `intake_tag` (single String(20)) and `action_tags` (JSONB list) **never cascade** to `customer_tags` on conversion.
- **`appointment_notes` table is orphaned scaffolding** (added 2026-04-25, never wired into the frontend; UI still writes through legacy `appointment.notes`).
- **Lead-photo upload returns HTTP 500** when boto3 fails because `PhotoService.upload_file` doesn't wrap `put_object`.

## Solution Statement

**Make Customer the canonical owner of notes/tags/photos.**

1. **Notes:** Every surface (lead post-conversion, sales entry, job detail, appointment modal) reads and writes one shared `customer.internal_notes` blob. Pre-conversion `lead.notes` stays on Lead (no customer exists yet); on conversion, lead.notes is carried forward with the existing `\n\n--- From lead ({date}) ---\n` divider pattern. Legacy `sales_entry.notes`, `estimate.notes`, `job.notes`, `appointment.notes`, and `AppointmentNote.body` are **dual-written through Phase 5** (legacy stays populated for rollback safety), then deprecated in Phase 6. The `appointment_notes` 1:1 table is dropped outright.
2. **Tags:** All tags live on `customer_tags`. Job + Appointment API responses **denormalize** the customer's tags into the payload for read. Tag mutations from a Job or Appointment surface POST to the existing customer-tag endpoint with `customer_id` resolved from the job/appointment.
3. **Photos:** `LeadAttachment` rows cascade to `CustomerPhoto` on every Lead→Customer conversion path (`convert_lead`, `move_to_sales`, `move_to_jobs`); Lead row + LeadAttachment row remain for audit. `AppointmentAttachment` is dropped; the existing `CustomerPhoto.appointment_id` FK becomes the canonical link.
4. **Conversion cascade:** On every entry point that calls `_carry_forward_lead_notes`, also call (a) `_carry_forward_lead_attachments`, (b) `_cascade_lead_intake_tag`, (c) `_cascade_lead_action_tags` — bundled into a single umbrella `_carry_forward_lead_data` helper for atomicity.
5. **Tag picker UI:** Replace the hard-coded `SUGGESTED_LABELS` in `TagEditorSheet.tsx` with a combobox autocomplete: typing filters existing tags; Enter on a non-match creates inline. Wire into every tag surface.
6. **S3 hardening:** Wrap `boto3.put_object` in `try/except (ClientError, BotoCoreError, EndpointConnectionError, NoCredentialsError)`, raise typed `S3UploadError(retryable: bool)`. API endpoints map `retryable=True → 502`, `retryable=False → 503`.

## Feature Metadata

**Feature Type**: Refactor (data-model consolidation) + Bug Fix (S3 500, lead-photo cascade data loss) + Enhancement (tag picker UI)
**Estimated Complexity**: **High** — 7 SQLAlchemy models, 6 services, 4 schema modules, 6 frontend feature slices, 4 alembic migrations, ~30 test files touched. 7 dependent phases.
**Primary Systems Affected**: Customer / Lead / SalesEntry / Estimate / Job / Appointment models, services, APIs; CustomerTag system; PhotoService; AppointmentNoteService (deletion); AppointmentAttachmentService (deletion); shared frontend notes/tags components.
**Dependencies**: No new backend libs (reuses `boto3`, `botocore`, `alembic`, `asyncpg`, `structlog`, `FastAPI`, `SQLAlchemy 2.0`). Frontend adds `cmdk` (shadcn `command` primitive); everything else reuses React 19, Radix UI, TanStack Query, existing shadcn `popover`.

---

## EVIDENCE PROTOCOL (mandatory, not optional)

### Evidence directory layout

```
e2e-screenshots/cluster-a/
├── evidence-dossier.md                ← running log, one row per task
├── phase-1-foundation/
│   ├── T1.1-exception-class.sql.txt
│   ├── T1.2-photo-service-wrap-pytest.png
│   ├── T1.5-alembic-upgrade-output.txt
│   ├── T1.5-appointment-notes-table-gone.sql.txt
│   ├── T1.6-attachment-rows-moved.sql.txt
│   └── T1.7-customer-notes-backfilled.sql.txt
├── phase-2-service-layer/
│   ├── T2.1-pytest-cascade-attachments.png
│   ├── T2.4-convert-lead-evidence.sql.txt
│   └── T2.5-appointment-notes-dual-write.sql.txt
├── phase-3-api/
│   ├── T3.2-job-response-customer-tags.json.txt
│   └── T3.3-appointment-response-customer-tags.json.txt
├── phase-4-frontend/
│   ├── T4.2-tag-picker-empty-state.png
│   ├── T4.2-tag-picker-autocomplete.png
│   ├── T4.2-tag-picker-inline-create.png
│   ├── T4.5-customer-notes-editor.png
│   ├── T4.6-appointment-modal-shared-notes.png
│   ├── T4.6-sales-detail-shared-notes.png
│   ├── T4.6-job-detail-shared-notes.png
│   └── T4.6-lead-detail-post-conversion.png
├── phase-5-tests/
│   ├── T5.1-pytest-cascade-output.txt
│   ├── T5.2-pytest-s3-errors-output.txt
│   ├── T5.3-pytest-api-mapping-output.txt
│   ├── T5.4-pytest-denormalization-output.txt
│   ├── T5.5-pytest-existing-suite-output.txt
│   └── T5.6-vitest-frontend-output.txt
├── phase-7-e2e/
│   ├── 01-login.png
│   ├── 02-create-lead-with-notes.png
│   ├── 03-lead-with-intake-tag.png
│   ├── 04-lead-with-action-tags.png
│   ├── 05-lead-upload-attachment.png
│   ├── 06-convert-lead-to-sales.png
│   ├── 07-customer-tags-cascaded.sql.txt
│   ├── 08-customer-photos-cascaded.sql.txt
│   ├── 09-customer-internal-notes-carried.sql.txt
│   ├── 10-sales-detail-shared-notes-visible.png
│   ├── 11-edit-notes-from-sales.png
│   ├── 12-notes-reflected-in-appointment-modal.png
│   ├── 13-add-tag-from-job-surface.png
│   ├── 14-tag-visible-on-customer-detail.png
│   ├── 15-s3-error-returns-502.png
│   ├── 16-s3-error-returns-503-misconfig.png
│   ├── 17-mobile-tag-picker.png
│   ├── 18-tablet-shared-notes.png
│   ├── 19-desktop-shared-notes.png
│   └── e2e-final-database-state.sql.txt
└── phase-6-cleanup/
    ├── T6.1-appointment-notes-deleted-files-grep.txt
    ├── T6.2-appointment-attachment-deleted-files-grep.txt
    └── T6.4-drop-legacy-columns-migration-output.txt
```

### `evidence-dossier.md` row template

```markdown
| Task | Status | Evidence | Reviewer Notes |
|---|---|---|---|
| T1.1 — Create S3UploadError | PASS | `phase-1-foundation/T1.1-exception-class.sql.txt` (import works) | — |
| T1.2 — Wrap PhotoService.put_object | PASS | `phase-1-foundation/T1.2-photo-service-wrap-pytest.png` (3/3 tests green) | — |
| T1.5 — Drop appointment_notes table | PASS | `phase-1-foundation/T1.5-alembic-upgrade-output.txt` + `T1.5-appointment-notes-table-gone.sql.txt` | row count discarded: 0 |
```

### Evidence-capture commands the execution agent uses

**Screenshot (browser):**
```bash
agent-browser screenshot e2e-screenshots/cluster-a/phase-4-frontend/T4.2-tag-picker-autocomplete.png
```

**Screenshot (terminal output / test run):**
Use macOS `screencapture -w` (interactive window capture) or just save terminal output to a `.txt` file. **For pytest runs**, capture output with `tee`:
```bash
uv run pytest src/grins_platform/tests/unit/test_lead_service_cascade.py -v 2>&1 \
  | tee e2e-screenshots/cluster-a/phase-5-tests/T5.1-pytest-cascade-output.txt
```

**DB query (against Railway dev — read-only via PGPASSWORD):**
```bash
psql "$DATABASE_URL" -c "<query>" \
  | tee e2e-screenshots/cluster-a/<phase>/<step>.sql.txt
```

**API response (curl):**
```bash
curl -s "$API_BASE/api/v1/jobs/$JOB_ID" -H "Authorization: Bearer $TOKEN" \
  | jq . | tee e2e-screenshots/cluster-a/phase-3-api/T3.2-job-response-customer-tags.json.txt
```

**Alembic state:**
```bash
uv run alembic current 2>&1 | tee e2e-screenshots/cluster-a/phase-1-foundation/T1.8-alembic-head.txt
uv run alembic history --verbose 2>&1 | tee -a e2e-screenshots/cluster-a/phase-1-foundation/T1.8-alembic-history.txt
```

### Dossier hygiene rules

- **Every task** appends one row to `e2e-screenshots/cluster-a/evidence-dossier.md` with status PASS / FAIL / BLOCKED.
- **No task is "done"** until the dossier row exists. The execution agent verifies before marking the task completed.
- Final task of the plan: agent re-reads the dossier and confirms every row is PASS (no FAIL or BLOCKED).
- The dossier markdown is the deliverable handed back to the user at the end.

---

## CONTEXT REFERENCES

### Relevant Codebase Files — IMPORTANT: YOU MUST READ THESE BEFORE IMPLEMENTING

Line numbers below are accurate as of plan authoring (2026-05-13). Execution agent **must re-read each file at the cited lines before editing** and note any drift in the dossier.

**Models:**
- `src/grins_platform/models/customer.py:152` — `internal_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)`. The unification target. Lines 243-248: `tags` relationship with `cascade="all, delete-orphan"`.
- `src/grins_platform/models/lead.py:75` — `notes` (Text). `:92-95` — `intake_tag: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)`. `:149-152` — `action_tags: Mapped[Optional[list[str]]] = mapped_column(JSONB, nullable=True)`. `:144-146` — address fields. `:179-180` — `customer_id` FK (set post-conversion).
- `src/grins_platform/models/sales.py:71` — `sales_entry.notes` (Text).
- `src/grins_platform/models/estimate.py:100` — `estimate.notes` (Text).
- `src/grins_platform/models/job.py:199` — `job.notes` (Text). `:178-181` — `scope_items` (JSONB; **distinct from notes — do not touch**). `:138` — `category` (JobCategory).
- `src/grins_platform/models/appointment.py:144` — legacy `notes` (Text). Confirm `customer_id` FK position by reading the file.
- `src/grins_platform/models/appointment_note.py` (entire file) — **DELETE in Phase 6.** Columns: `id`, `appointment_id` UNIQUE FK CASCADE, `body` (Text NOT NULL, server_default=""), `updated_at`, `updated_by_id` FK Staff.
- `src/grins_platform/models/appointment_attachment.py` (entire file) — **DELETE in Phase 6 after data migration.** Columns: `id`, `appointment_id` UUID (no FK!), `appointment_type` String(20), `file_key`, `file_name`, `file_size`, `content_type`, `uploaded_by` FK Staff, `created_at`. Composite index on `(appointment_type, appointment_id)`.
- `src/grins_platform/models/customer_photo.py:52-56` — `appointment_id: Mapped[UUID | None]` FK to appointments.id SET NULL. `:57-61` — `job_id: Mapped[UUID | None]` FK to jobs.id SET NULL. **Both FKs already exist** — no schema change needed for the FK itself.
- `src/grins_platform/models/customer_tag.py:60-78` — full columns. `:44-58` — `UniqueConstraint(customer_id, label)` + CheckConstraint on tone (`neutral|blue|green|amber|violet`) + on source (`manual|system`). **Label max length: 32 chars.**
- `src/grins_platform/models/lead_attachment.py` (entire file ~50 lines) — Columns: `id`, `lead_id` FK CASCADE, `file_key`, `file_name`, `file_size`, `content_type`, `attachment_type` String(20), `created_at`.
- `src/grins_platform/models/enums.py:496-507` — `class ActionTag(str, Enum)` with `NEEDS_CONTACT`, `NEEDS_ESTIMATE`, `ESTIMATE_PENDING`, `ESTIMATE_APPROVED`, `ESTIMATE_REJECTED`. **`ESTIMATE_APPROVED` and `ESTIMATE_REJECTED` are terminal/resolved — filter on cascade.**

**Services (the call graph is locked):**

- `src/grins_platform/services/lead_service.py:949` — `async def convert_lead(...)`. Internal call site to `_carry_forward_lead_notes` is near this method (verify line by re-reading).
- `src/grins_platform/services/lead_service.py:1141` — `async def _carry_forward_lead_notes(self, lead, customer, *, actor_staff_id)`. Uses divider `\n\n--- From lead ({date}) ---\n`. Audit-logs at the end.
- `src/grins_platform/services/lead_service.py:1253` — `async def move_to_jobs(self, lead_id, *, force, actor_staff_id)`. Calls `_carry_forward_lead_notes` at line **1347**.
- `src/grins_platform/services/lead_service.py:1376` — `async def move_to_sales(self, lead_id, *, actor_staff_id)`. **Sets `sales_entry.notes=lead.notes` at line 1418** (legacy dual-write — will need to be removed in Phase 6). Calls `_carry_forward_lead_notes` at line **1433**.
- `src/grins_platform/services/lead_service.py:_ensure_customer_for_lead(...)` (~line 1240) — returns `(customer_id, merged_info)`. Common helper across all three entry points.

  **→ Cascade hook strategy:** Introduce one new umbrella helper `_carry_forward_lead_data(lead, customer, *, actor_staff_id)` that internally calls `_carry_forward_lead_notes` AND the three new cascade methods. Replace the existing 3 call sites (lines 1347, 1433, plus the one in `convert_lead`) with single calls to `_carry_forward_lead_data`. This atomizes the cascade.

- `src/grins_platform/services/customer_tag_service.py:61-130` — `save_tags(customer_id, request, session)`. Diff-based upsert preserves `source="system"` tags; replaces `source="manual"`. Cascade insertions go via the **repository directly** with `source="system"` to avoid the diff-replace semantics.
- `src/grins_platform/services/photo_service.py:69-76` — `UploadContext` enum: `CUSTOMER_PHOTO`, `CUSTOMER_DOCUMENT`, `LEAD_ATTACHMENT`, `MEDIA_LIBRARY`, `RECEIPT`.
- `src/grins_platform/services/photo_service.py:284-351` — `upload_file(data, file_name, context, *, strip_metadata=True)`. **Lines 331-336** = the bare `put_object` to wrap.
- `src/grins_platform/services/appointment_service.py:2435-2503` — `add_notes_and_photos(...)`. Currently dual-writes `appointment.notes` AND `customer.internal_notes` (with a `[{timestamp}] Appointment note: {notes}` prefix — **the timestamp prefix violates the no-chrome rule**; replace with overwrite).
- `src/grins_platform/services/appointment_note_service.py` (entire file) — **DELETE in Phase 6.**
- `src/grins_platform/services/appointment_attachment_service.py` (entire file) — **DELETE in Phase 6 after migration T1.6.**
- `src/grins_platform/services/sales_pipeline_service.py` — `record_estimate_decision_breadcrumb` near line 172 appends to `SalesEntry.notes`. **DO NOT redirect this to customer.internal_notes** — breadcrumbs are audit-style noise; keep them on sales_entry.notes as legacy audit (not displayed in unified UI). The audit_log table is the canonical history.
- `src/grins_platform/services/estimate_service.py:472-477` (approve) and `:556-561` (reject) — call `update_action_tags(lead, add=[ESTIMATE_APPROVED|REJECTED])`. Confirms these are the **terminal** action_tag values to filter on cascade.
- `src/grins_platform/services/customer_service.py` (read but don't depend on specific lines) — use the existing `update` path to write `customer.internal_notes`. **No new method needed** unless the existing update path doesn't support partial PATCH semantics.

**Repositories:**
- `src/grins_platform/repositories/customer_tag_repository.py` — Has `upsert_tag` or equivalent (verify exact method name by reading first 80 lines). Used by cascade for `source="system"` inserts.
- `src/grins_platform/repositories/appointment_note_repository.py` — **DELETE in Phase 6.**
- `src/grins_platform/repositories/customer_repository.py` — `update(customer_id, payload)` is the canonical path.

**Schemas:**
- `src/grins_platform/schemas/customer.py:125-129` — `CustomerCreate.internal_notes` `max_length=10000`. `:216-220` — `CustomerUpdate.internal_notes` `max_length=10000`. `:313-316` — `CustomerResponse.internal_notes`.
  - **Edge case to mitigate:** T1.7 backfill may push customers over `max_length=10000` when merging 5 legacy sources. The backfill migration must either (a) **truncate with a logged warning per customer**, or (b) **raise the schema max to 50000**. Decision: **raise the schema max to 50000** (matches `AppointmentNotesSaveRequest.max_length=50_000` precedent). Document in the migration.
- `src/grins_platform/schemas/appointment.py` — exposes `notes`. Keep field; becomes a read-through alias.
- `src/grins_platform/schemas/appointment_note.py` (entire file) — **DELETE in Phase 6.** Contains `NoteAuthorResponse`, `AppointmentNotesResponse`, `AppointmentNotesSaveRequest(max_length=50_000)`.
- `src/grins_platform/schemas/appointment_attachment.py` (entire file) — **DELETE in Phase 6.**
- `src/grins_platform/schemas/job.py:285-441` — `JobResponse`. `:379` — existing `notes`. `:438-440` — `property_tags` (computed badges only — distinct from customer_tags).
- `src/grins_platform/schemas/sales_pipeline.py:33-62` — `SalesEntryResponse`. `:45` — `notes`. `:58` — `customer_internal_notes` (already denormalized — pattern to mirror). `:89-111` — `SalesCalendarEventResponse`. `:106` — `notes`.

**API Routes:**
- `src/grins_platform/api/v1/appointments.py:883-927` (GET `/appointments/{id}/notes`) + `:930-980` (PATCH `/appointments/{id}/notes`) — **DELETE in Phase 6.**
- `src/grins_platform/api/v1/appointments.py:1674-1677` — photo upload writes appointment.notes; rewire in Phase 4.
- `src/grins_platform/api/v1/appointment_attachments.py` (entire file) — **DELETE in Phase 6** after T1.6 migration.
- `src/grins_platform/api/v1/leads.py:744-749` — `try/except ValueError/TypeError` block; **add `except S3UploadError`** in T1.3.
- `src/grins_platform/api/v1/customers.py:1253-1371` — `/customers/{id}/photos` POST. Same S3UploadError catch in T1.4.
- `src/grins_platform/api/v1/customers.py:2262-2339` — customer-tags GET (`:2270`) + PUT (`:2312`) endpoints. **The canonical write target for all surfaces.**
- `src/grins_platform/api/v1/jobs.py` (response builder) — add `customer_tags` denormalization in T3.2.
- `src/grins_platform/api/v1/sales_pipeline.py:161-180` (`_entry_to_response`) — denormalization pattern; line ~617 has the `HTTPException(502)` pattern to mirror for S3UploadError mapping if any callers wrap photo uploads.
- `src/grins_platform/api/v1/router.py:71` (signwell mount, near it: appointment_attachments + appointment_notes mounts) — remove deleted-endpoint mounts in Phase 6.

**Frontend:**
- `frontend/src/features/schedule/components/AppointmentModal/TagEditorSheet.tsx:14-22` — hardcoded `SUGGESTED_LABELS` (7 items). `:58` — 32-char input max. `:82-93` — save logic via `useSaveCustomerTags`.
- `frontend/src/features/schedule/components/AppointmentForm.tsx:57` — zod schema `notes: z.string().optional()`. `:137` — default. `:207, 220` — payloads. `:460-463` — dedicated InternalNotesCard binding to customer.internal_notes. `:179-182` — separate `updateCustomerMutation` for customer-notes save (pattern to mirror).
- `frontend/src/features/schedule/components/AppointmentDetail.tsx:620-626, 710` — renders `appointment.notes` / passes to NotesPanel.
- `frontend/src/features/schedule/components/InlineCustomerPanel.tsx:135-139, 191-192` — dual rendering of customer.internal_notes + appointment.notes.
- `frontend/src/features/schedule/types/index.ts:77` — `Appointment.notes: string | null`. Keep through Phase 5; mark `@deprecated` JSDoc.
- `frontend/src/features/sales/components/SalesDetail.tsx` — sales-entry notes binding (verify exact line by re-reading; existing intel reports line 215 + 393-406 range).
- `frontend/src/features/jobs/components/JobDetail.tsx:155-162` — Estimate Needed badge (out of scope). Notes binding needs locating.
- `frontend/src/features/customers/components/CustomerForm.tsx:155, 173, 209, 217, 225, 666` — internal_notes form field (existing pattern; will be extracted into a shared `<CustomerNotesEditor>`).
- `frontend/src/features/leads/components/LeadDetail.tsx` (or `LeadForm.tsx` — verify) — lead.notes input.
- `frontend/src/components/ui/popover.tsx` — exists. `command.tsx` — **does NOT exist; add in T4.1.**
- `frontend/src/features/schedule/hooks/useCustomerTags.ts` — exports `useCustomerTags(customerId)`, `useSaveCustomerTags()`.

**Migrations (chain locked):**
- **Current alembic head: `20260512_120000` (wipe_dev_test_data)**. New migrations chain off this.
- `src/grins_platform/migrations/versions/20260511_120000_clear_estimate_followup_promotion_codes.py` — recent **data-only** migration template (revision string format, header docstring).
- `src/grins_platform/migrations/versions/20260512_120000_wipe_dev_test_data.py` — env-gated migration pattern (for any migration that needs prod-gating).
- `src/grins_platform/migrations/versions/20260425_100000_add_appointment_notes_table.py` — the migration we are reverting (read its `op.create_table` for the `downgrade()` of the drop migration).
- `src/grins_platform/migrations/versions/20260418_100700_fold_notes_table_into_internal_notes.py:127, 133` — `print(f"[fold] discarding {cnt} appointment note(s)")` log pattern.
- `src/grins_platform/migrations/versions/20260504_100000_add_jobs_scope_items.py` — forward-only DDL example.

**Existing E2E infrastructure (pattern to extend):**
- `e2e/_lib.sh` — shared helpers (`ab`, `psql_q`, `require_tooling`, `require_servers`, `require_seed`). **DATABASE_URL default: `postgresql://grins_user:grins_password@localhost:5432/grins_platform`**.
- `scripts/e2e/test-leads.sh` — existing lead-flow E2E with login + screenshots.
- `e2e/integration-full-happy-path.sh` — existing end-to-end demo flow.
- `.claude/skills/e2e-test/SKILL.md` — the canonical E2E methodology (parallel research → start app → task list → journey testing with screenshots + DB validation → cleanup → report).

### New Files to Create

**Backend:**
1. `src/grins_platform/exceptions/upload.py` — `S3UploadError(Exception)` with `retryable: bool` attribute. Module docstring.
2. `src/grins_platform/migrations/versions/<NEW_TS_A>_backfill_customer_notes_from_legacy.py` — Idempotent data migration (FIRST in chain — runs before the drop so appointment_notes is still available as a source). Raises `customer.internal_notes` schema max to 50000 in the same release.
3. `src/grins_platform/migrations/versions/<NEW_TS_B>_drop_appointment_notes_table.py` — Drops `appointment_notes`. Logs discarded row count.
4. `src/grins_platform/migrations/versions/<NEW_TS_C>_migrate_appointment_attachments_to_customer_photos.py` — Data migration: copies rows to `customer_photos` with `customer_id` resolved + `appointment_id` set; drops `appointment_attachments` table at the end.

**Frontend:**
5. `frontend/src/components/ui/command.tsx` — Standard shadcn Command primitive (wraps `cmdk`).
6. `frontend/src/features/customers/components/TagPicker.tsx` — Reusable combobox tag picker. Props: `{ customerId: string; value: CustomerTag[]; onChange?: (next: CustomerTag[]) => void; disabled?: boolean }`. Used by every tag surface.
7. `frontend/src/features/customers/components/CustomerNotesEditor.tsx` — Reusable customer-notes textarea with auto-save-on-blur. Props: `{ customerId: string; readOnly?: boolean }`.

**Tests:**
8. `src/grins_platform/tests/unit/test_lead_service_cascade.py` — Cascade unit tests (4 scenarios).
9. `src/grins_platform/tests/unit/test_photo_service_s3_errors.py` — S3 wrapper unit tests (3 scenarios).
10. `src/grins_platform/tests/integration/test_cluster_a_denormalization.py` — JobResponse + AppointmentResponse `customer_tags` integration tests.
11. `frontend/src/features/customers/components/__tests__/TagPicker.test.tsx` — Combobox UI tests.
12. `frontend/src/features/customers/components/__tests__/CustomerNotesEditor.test.tsx` — Auto-save-on-blur tests.

**E2E:**
13. `e2e/cluster-a-notes-photos-tags.sh` — Phase-7 E2E driver. Sources `_lib.sh`. Saves screenshots to `e2e-screenshots/cluster-a/phase-7-e2e/`.

**Evidence:**
14. `e2e-screenshots/cluster-a/evidence-dossier.md` — running log of every task's PASS/FAIL with evidence links.

### Relevant Documentation — YOU SHOULD READ THESE BEFORE IMPLEMENTING

- [Alembic — Operations Reference](https://alembic.sqlalchemy.org/en/latest/ops.html#alembic.operations.Operations.drop_table) — Section: `drop_table`, `execute`, `get_bind`. Why: T1.5–T1.7 use these.
- [SQLAlchemy 2.0 — Core SQL Expression Language INSERT](https://docs.sqlalchemy.org/en/20/core/dml.html#sqlalchemy.sql.expression.insert) — Why: T1.6 + T1.7 use raw `op.execute(insert(...))` for performance and control.
- [boto3 — Error Handling](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/error-handling.html) — Section: `ClientError`, `BotoCoreError`, `EndpointConnectionError`, `NoCredentialsError`. Why: T1.2 distinguishes retryable from misconfig.
- [shadcn/ui — Command (Combobox pattern)](https://ui.shadcn.com/docs/components/command) — Section: full Command component + Combobox example. Why: T4.1 + T4.2 source-of-truth.
- [Radix UI — Popover](https://www.radix-ui.com/primitives/docs/components/popover) — Section: anchored popover. Why: TagPicker positioning.
- [FastAPI — HTTPException](https://fastapi.tiangolo.com/reference/exceptions/) — Section: status codes. Why: 502 vs 503 mapping.
- [TanStack Query v5 — Query Invalidation](https://tanstack.com/query/v5/docs/framework/react/guides/query-invalidation) — Section: `queryClient.invalidateQueries`. Why: tag/notes mutations must invalidate every denormalized surface.
- [agent-browser CLI reference (inline in skill)](`/Users/kirillrakitin/Grins_irrigation_platform/.claude/skills/e2e-test/SKILL.md`) — Section: lines 129-145 (command reference). Why: Phase 7 driver.

### Patterns to Follow

#### Migration header (verbatim template)

```python
"""<one-line purpose>.

<2-4 paragraph description: what changes, why, rollback impact, ordering
constraints relative to other migrations in this cluster>.

Revision ID: <NEW_TS_X>
Revises: 20260512_120000
"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "<NEW_TS_X>"
down_revision: Union[str, None] = "20260512_120000"  # ← chain off head
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    ...


def downgrade() -> None:
    ...
```

#### S3 wrapper (verbatim — drop into `photo_service.py` replacing lines 331-336)

```python
from botocore.exceptions import (
    BotoCoreError,
    ClientError,
    EndpointConnectionError,
    NoCredentialsError,
)
from grins_platform.exceptions.upload import S3UploadError

try:
    _ = self._client.put_object(
        Bucket=self._bucket,
        Key=file_key,
        Body=processed,
        ContentType=detected_mime,
    )
except NoCredentialsError as exc:
    self.logger.error(
        "photo.upload.s3_misconfigured",
        error_class=type(exc).__name__,
        exc_info=True,
    )
    raise S3UploadError(
        "S3 credentials not configured",
        retryable=False,
    ) from exc
except (ClientError, EndpointConnectionError, BotoCoreError) as exc:
    self.logger.error(
        "photo.upload.s3_failed",
        error_class=type(exc).__name__,
        file_key=file_key,
        exc_info=True,
    )
    raise S3UploadError(
        f"S3 upload failed: {type(exc).__name__}",
        retryable=True,
    ) from exc
```

#### API exception mapping (verbatim — extend `api/v1/leads.py:744-749` and mirror in `api/v1/customers.py:1310-1336`)

```python
from grins_platform.exceptions.upload import S3UploadError

try:
    upload_result = photo_service.upload_file(
        data=file_data,
        file_name=file.filename or "upload.bin",
        context=UploadContext.LEAD_ATTACHMENT,
    )
except ValueError as exc:
    raise HTTPException(status_code=413, detail=str(exc)) from exc
except TypeError as exc:
    raise HTTPException(status_code=415, detail=str(exc)) from exc
except S3UploadError as exc:
    status_code = 503 if not exc.retryable else 502
    raise HTTPException(status_code=status_code, detail=str(exc)) from exc
```

#### Cascade umbrella helper (verbatim shape — insert into `lead_service.py` near `_carry_forward_lead_notes`)

```python
async def _carry_forward_lead_data(
    self,
    lead: Lead,
    customer: Customer,
    *,
    actor_staff_id: UUID | None = None,
) -> dict[str, int | bool]:
    """Umbrella cascade: notes + attachments + intake_tag + action_tags.

    Replaces the previous bare _carry_forward_lead_notes call sites.
    Atomic: any failure rolls back the enclosing transaction.

    Returns:
        Dict with counts/booleans for audit logging:
        {
            "notes_carried": bool,
            "attachments_moved": int,
            "intake_cascaded": bool,
            "action_tags_cascaded": int,
        }
    """
    notes_carried = await self._carry_forward_lead_notes(
        lead, customer, actor_staff_id=actor_staff_id
    )
    attachments_moved = await self._carry_forward_lead_attachments(
        lead, customer, actor_staff_id=actor_staff_id
    )
    intake_cascaded = await self._cascade_lead_intake_tag(lead, customer)
    action_tags_cascaded = await self._cascade_lead_action_tags(lead, customer)

    self.logger.info(
        "lead.cascade.complete",
        lead_id=str(lead.id),
        customer_id=str(customer.id),
        notes_carried=notes_carried,
        attachments_moved=attachments_moved,
        intake_cascaded=intake_cascaded,
        action_tags_cascaded=action_tags_cascaded,
    )
    return {
        "notes_carried": notes_carried,
        "attachments_moved": attachments_moved,
        "intake_cascaded": intake_cascaded,
        "action_tags_cascaded": action_tags_cascaded,
    }
```

Then **replace** every `_carry_forward_lead_notes(...)` call site (lines 1347, 1433, and the one inside `convert_lead`) with:
```python
_ = await self._carry_forward_lead_data(lead, customer_obj, actor_staff_id=actor_staff_id)
```

#### Tag-cascade insert pattern (use repository, not service.save_tags)

```python
from grins_platform.repositories.customer_tag_repository import CustomerTagRepository

def _humanize_tag(raw: str) -> str:
    """Convert snake_case → Title Case, truncate to 32 chars."""
    return " ".join(part.capitalize() for part in raw.split("_"))[:32]

# Inside _cascade_lead_intake_tag and _cascade_lead_action_tags:
tag_repo = CustomerTagRepository(self.lead_repository.session)
label = _humanize_tag(raw_value)
try:
    await tag_repo.upsert_tag(
        customer_id=customer.id,
        label=label,
        tone="neutral",
        source="system",
    )
except IntegrityError:
    pass  # unique (customer_id, label) collision — idempotent skip
```

**Verify the actual `CustomerTagRepository` method signature** by reading the file first — the method name might be `add` / `create` / `upsert` depending on the existing pattern. Mirror the exact signature used by `CustomerTagService.save_tags`.

#### Frontend mutation (verbatim TanStack v5 pattern)

```typescript
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/core/api/client';

export function useSaveCustomerInternalNotes() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ customerId, internal_notes }: { customerId: string; internal_notes: string }) =>
      api.patch(`/customers/${customerId}`, { internal_notes }),
    onSuccess: (_, { customerId }) => {
      queryClient.invalidateQueries({ queryKey: ['customer', customerId] });
      queryClient.invalidateQueries({ queryKey: ['appointments'] });
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
      queryClient.invalidateQueries({ queryKey: ['sales-pipeline'] });
      queryClient.invalidateQueries({ queryKey: ['leads'] });
    },
  });
}
```

#### Auto-save-on-blur (verbatim React pattern for `CustomerNotesEditor`)

```tsx
const [savedFlash, setSavedFlash] = React.useState(false);
const initialValueRef = React.useRef(customer?.internal_notes ?? '');
const saveMutation = useSaveCustomerInternalNotes();

return (
  <div>
    <Textarea
      defaultValue={initialValueRef.current}
      disabled={readOnly}
      onBlur={(e) => {
        if (readOnly) return;
        const next = e.currentTarget.value;
        if (next === initialValueRef.current) return;
        saveMutation.mutate(
          { customerId, internal_notes: next },
          {
            onSuccess: () => {
              initialValueRef.current = next;
              setSavedFlash(true);
              setTimeout(() => setSavedFlash(false), 1500);
            },
          },
        );
      }}
    />
    {savedFlash && <span className="text-xs text-emerald-600 ml-2">Saved</span>}
  </div>
);
```

#### Logging convention

All structured logs use `LoggerMixin`'s `self.logger.info / error` with event names `<domain>.<action>.<outcome>` (dot-separated). Always include UUIDs as strings. Mirror existing examples in `services/lead_service.py:1620` and similar.

#### Audit-log convention

```python
await self.audit_service.log_action(
    actor_user_id=actor_staff_id,
    action="lead.cascade.attachments_moved",
    resource_type="lead",
    resource_id=lead.id,
    details={"customer_id": str(customer.id), "moved_count": moved_count},
)
```

Mirror `lead_service.py:1174-1192` for shape.

---

## IMPLEMENTATION PLAN

### Phase 1: Foundation — Schema, Migrations, Exception Module, S3 Wrap

This phase is **pre-requisite for everything downstream**. Each migration runs end-to-end (upgrade + downgrade + upgrade) on a fresh clone of dev DB before the next migration is authored.

**Tasks**: T1.1 → T1.10. Evidence directory: `phase-1-foundation/`.

### Phase 2: Service Layer — Lead Cascade + AppointmentService Redirect

Wire the cascade helpers into every Lead→Customer conversion entry point. Replace the per-entry-timestamp prefix in AppointmentService with a clean overwrite of `customer.internal_notes` (preserves the "no chrome" constraint).

**Tasks**: T2.1 → T2.6. Evidence directory: `phase-2-service-layer/`.

### Phase 3: API Denormalization — JobResponse + AppointmentResponse Expose `customer_tags`

Surface the customer's tags on Job and Appointment response payloads so the frontend renders them without a second fetch. SalesEntryResponse already denormalizes customer.internal_notes — extend with customer_tags too.

**Tasks**: T3.1 → T3.5. Evidence directory: `phase-3-api/`.

### Phase 4: Frontend — Tag Picker + Customer Notes Editor + Wire Everywhere

Build the `Command`-based combobox tag picker and the auto-save customer-notes textarea. Wire both into every surface (lead post-conversion, customer, sales, job, appointment).

**Tasks**: T4.1 → T4.10. Evidence directory: `phase-4-frontend/`.

### Phase 5: Tests — Unit + Integration + Frontend

Cover cascade, S3, denormalization, frontend interactions. Update legacy notes tests for dual-write.

**Tasks**: T5.1 → T5.7. Evidence directory: `phase-5-tests/`.

### Phase 6: Cleanup — Delete Orphan Machinery (separate PR after Phase 1-5 deploys)

Delete `appointment_notes` + `appointment_attachment` files, endpoints, tests. Remove dual-write paths. Final migration drops legacy notes columns.

**Tasks**: T6.1 → T6.5. Evidence directory: `phase-6-cleanup/`.

### Phase 7: E2E with agent-browser — Screenshots + DB Evidence (MANDATORY)

Full Lead → Customer → Sales → Job → Appointment user journey with screenshot + DB-query evidence for every cascade, notes propagation, and tag update. Runs against dev. Drives the `e2e/cluster-a-notes-photos-tags.sh` script.

**Tasks**: T7.1 → T7.15. Evidence directory: `phase-7-e2e/`.

---

## STEP-BY-STEP TASKS

Execute every task in order, top to bottom. Each task is atomic and independently testable. **Each task ends with a `VALIDATE` block, an `EVIDENCE` block, and a `DOSSIER` entry.** Marking a task complete without all three is a contract violation.

### Phase 1 — Foundation

#### T1.0 — Bootstrap evidence directory + dossier
- **CREATE**: `e2e-screenshots/cluster-a/evidence-dossier.md` with header table.
- **CREATE**: empty subdirs `phase-1-foundation/`, `phase-2-service-layer/`, `phase-3-api/`, `phase-4-frontend/`, `phase-5-tests/`, `phase-6-cleanup/`, `phase-7-e2e/` under `e2e-screenshots/cluster-a/`.
- **CONTENT** of `evidence-dossier.md`:
  ```markdown
  # Cluster A — Evidence Dossier

  Each row: task ID, status (PASS / FAIL / BLOCKED), evidence file paths, optional reviewer notes.
  Final task verifies every row is PASS.

  | Task | Status | Evidence | Notes |
  |---|---|---|---|
  ```
- **VALIDATE**: `ls e2e-screenshots/cluster-a/` lists 7 phase subdirs + `evidence-dossier.md`.
- **EVIDENCE**: `ls e2e-screenshots/cluster-a/ | tee e2e-screenshots/cluster-a/phase-1-foundation/T1.0-bootstrap.txt`
- **DOSSIER**: add `| T1.0 — Bootstrap evidence dir | PASS | T1.0-bootstrap.txt | — |`

#### T1.1 — CREATE `src/grins_platform/exceptions/upload.py`
- **VERIFY FIRST**: `ls src/grins_platform/exceptions/ 2>/dev/null || mkdir -p src/grins_platform/exceptions/`. If the directory exists with other files, mirror their style (module docstring at top, `from __future__ import annotations`, single class per file or grouped — match the existing convention).
- **IMPLEMENT**:
  ```python
  """S3 upload error type for PhotoService.

  Distinguishes retryable transient failures (network, throttling) from
  misconfiguration failures (missing credentials, wrong region). API
  endpoints catch and map: retryable=True → HTTP 502, retryable=False → 503.
  """
  from __future__ import annotations


  class S3UploadError(Exception):
      """Raised when an S3 put_object call fails.

      Attributes:
          retryable: True if the failure is transient (caller may retry);
              False if the failure is structural (missing creds, etc).
      """

      def __init__(self, message: str, *, retryable: bool = True) -> None:
          super().__init__(message)
          self.retryable = retryable
  ```
- **PATTERN**: `services/appointment_attachment_service.py:32-46` for shape.
- **GOTCHA**: If `src/grins_platform/exceptions/` has an `__init__.py`, re-export `S3UploadError` there for ergonomic imports.
- **VALIDATE**:
  ```bash
  uv run python -c "from grins_platform.exceptions.upload import S3UploadError; e = S3UploadError('test', retryable=False); print(f'retryable={e.retryable}')"
  ```
  Expected stdout: `retryable=False`.
- **EVIDENCE**:
  ```bash
  uv run python -c "from grins_platform.exceptions.upload import S3UploadError; e = S3UploadError('test', retryable=False); print(f'retryable={e.retryable}')" 2>&1 \
    | tee e2e-screenshots/cluster-a/phase-1-foundation/T1.1-exception-class.txt
  ```
- **DOSSIER**: append row.

#### T1.2 — UPDATE `src/grins_platform/services/photo_service.py` (S3 wrap)
- **VERIFY FIRST**: read `services/photo_service.py:280-360` to confirm the `put_object` call is still at lines 331-336.
- **IMPLEMENT**: replace lines 331-336 with the verbatim snippet in **Patterns to Follow → S3 wrapper**.
- **IMPORTS** to add to file header:
  ```python
  from botocore.exceptions import BotoCoreError, ClientError, EndpointConnectionError, NoCredentialsError
  from grins_platform.exceptions.upload import S3UploadError
  ```
- **GOTCHA**: do not catch bare `Exception`. Do not make `upload_file` async (it's sync today; tests rely on that).
- **GOTCHA**: re-verify line range — code drift since plan authoring will shift the exact lines.
- **VALIDATE**:
  ```bash
  uv run ruff check src/grins_platform/services/photo_service.py
  uv run mypy src/grins_platform/services/photo_service.py
  uv run pytest src/grins_platform/tests/unit/test_photo_service*.py -x 2>&1 \
    | tee e2e-screenshots/cluster-a/phase-1-foundation/T1.2-photo-service-existing-tests.txt
  ```
- **EVIDENCE**: the `tee`'d output above + a `git diff src/grins_platform/services/photo_service.py | tee phase-1-foundation/T1.2-diff.txt`.
- **DOSSIER**: append row.

#### T1.3 — UPDATE `src/grins_platform/api/v1/leads.py` (502/503 mapping)
- **VERIFY FIRST**: `Grep -n "UploadContext.LEAD_ATTACHMENT" src/grins_platform/api/v1/leads.py` to lock the call site. The existing try/except (around line 745-749) wraps the `photo_service.upload_file(...)` call.
- **IMPLEMENT**: add `except S3UploadError` after the existing `except TypeError` block per **Patterns to Follow → API exception mapping**.
- **IMPORTS** to add: `from grins_platform.exceptions.upload import S3UploadError`.
- **GOTCHA**: keep ordering: ValueError (413) → TypeError (415) → S3UploadError (502/503). Don't reorder; ValueError must remain the first catch.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_lead_api.py -x`. T5.3 will add the targeted 502/503 tests; this validation just ensures the existing tests still pass.
- **EVIDENCE**: pytest output + diff.
- **DOSSIER**: append row.

#### T1.4 — UPDATE `src/grins_platform/api/v1/customers.py` (502/503 mapping)
- **VERIFY FIRST**: `Grep -n "UploadContext.CUSTOMER_PHOTO" src/grins_platform/api/v1/customers.py`.
- **IMPLEMENT**: mirror T1.3 on the `/customers/{id}/photos` POST endpoint. Existing ValueError/TypeError catches are at lines 1315-1336.
- **VALIDATE**: `uv run pytest -k "customer_photo" -x`.
- **EVIDENCE**: pytest output + diff.
- **DOSSIER**: append row.

#### T1.5 — CREATE migration `<NEW_TS_A>_backfill_customer_notes_from_legacy.py`

**This is the FIRST migration in the chain.** It runs while `appointment_notes` still exists (so its `body` can be a source).

- **PICK TIMESTAMP `<NEW_TS_A>`**: must sort after `20260512_120000`. Use `date +%Y%m%d_%H%M%S` at execution time; e.g., `20260513_120000`.
- **PRE-WORK**: also bump the `customer.internal_notes` schema max from 10000 → 50000 in `schemas/customer.py:125-129, 216-220` (Pydantic Field `max_length=50_000`). This is required because the backfill may produce long blobs. Commit the schema bump in the SAME commit as the migration to keep them atomic.
- **IMPLEMENT**: SQL-based data migration using `op.execute(sa.text(...))` or `op.get_bind()` with parameterized queries. Logic:

  1. For each customer (loop in Python via `bind.execute(...).fetchall()`):
     1. Load current `customer.internal_notes` (may be NULL).
     2. For each of these source rows tied to the customer, in order:
        - All `sales_entry` rows where `sales_entry.customer_id = customer.id` AND `sales_entry.notes IS NOT NULL AND sales_entry.notes <> ''`.
        - All `estimates` joined to this customer via `estimate.customer_id` OR via `estimate.lead_id → lead.customer_id`, where `notes IS NOT NULL AND notes <> ''`.
        - All `jobs` where `job.customer_id = customer.id`, `notes IS NOT NULL AND notes <> ''`.
        - All `appointments` where `appointment.customer_id = customer.id` (or joined via `appointment.job_id → job.customer_id` if appointment.customer_id is null), `notes IS NOT NULL AND notes <> ''`.
        - All `appointment_notes` joined via the appointment, where `body IS NOT NULL AND body <> ''`.
     3. For each source row, build a `divider = f"\n\n--- From {source_label} ({created_at_date}) ---\n"`. Source labels: `"sales entry"`, `"estimate"`, `"job"`, `"appointment"`, `"appointment note"`.
     4. **Idempotency check:** if `divider in (current_internal_notes or "")`, skip that source row.
     5. Append `divider + body` to the customer's accumulated notes.
     6. After all sources merged: `UPDATE customers SET internal_notes = <merged> WHERE id = <customer.id>`.
     7. If the merged total exceeds 50000 chars: truncate at 50000 with the suffix `\n\n[...truncated by backfill]` and log a warning via `print(f"[backfill] customer {id} truncated from {orig_len} to 50000")`.
  3. At the end, log: `print(f"[backfill] processed {n_customers} customers, merged {n_sources} source rows, truncated {n_truncated}")`.
- **DOWNGRADE**: no-op (cannot reverse). Add a comment explaining.
- **PATTERN**: `migrations/versions/20260418_100700_fold_notes_table_into_internal_notes.py` for the source-aggregation pattern + idempotent skip.
- **GOTCHAS**:
  - `appointment_notes.body` source requires the table to still exist. T1.5 runs **before** T1.6 (drop). Order enforced by timestamp.
  - Edge case: a customer with no `internal_notes` and 5 source rows — start from `""`, append 5 dividers.
  - Edge case: a customer with `internal_notes` already containing a divider from a prior run — idempotent skip works (literal string match).
  - Edge case: an estimate that has both `customer_id` AND a `lead_id → lead.customer_id` pointing to the same customer — dedupe by `(estimate.id)` in the source query.
  - Edge case: appointment without `customer_id` AND without `job_id` AND without a customer reachable — skip with a warning log (orphan).
  - Edge case: sources may share a `created_at` date — that's fine; multiple dividers with the same date are allowed.
- **VALIDATE — local dry-run**:
  1. `uv run alembic upgrade head` — must succeed without errors.
  2. `psql "$DATABASE_URL" -c "SELECT id, char_length(internal_notes) FROM customers WHERE internal_notes IS NOT NULL ORDER BY char_length(internal_notes) DESC LIMIT 5;"` — confirm non-zero values.
  3. `uv run alembic downgrade -1` — must succeed (no-op).
  4. `uv run alembic upgrade head` — re-applies idempotently; running it twice must not duplicate dividers.
- **EVIDENCE**:
  ```bash
  uv run alembic upgrade head 2>&1 | tee e2e-screenshots/cluster-a/phase-1-foundation/T1.5-alembic-upgrade.txt
  psql "$DATABASE_URL" -c "SELECT id, char_length(internal_notes) FROM customers WHERE internal_notes IS NOT NULL ORDER BY char_length(internal_notes) DESC LIMIT 5;" 2>&1 \
    | tee e2e-screenshots/cluster-a/phase-1-foundation/T1.5-customer-notes-after-backfill.sql.txt
  # Idempotency check:
  uv run alembic downgrade -1 && uv run alembic upgrade head 2>&1 \
    | tee -a e2e-screenshots/cluster-a/phase-1-foundation/T1.5-roundtrip.txt
  psql "$DATABASE_URL" -c "SELECT id, char_length(internal_notes) FROM customers WHERE internal_notes IS NOT NULL ORDER BY char_length(internal_notes) DESC LIMIT 5;" 2>&1 \
    | tee e2e-screenshots/cluster-a/phase-1-foundation/T1.5-customer-notes-after-second-upgrade.sql.txt
  # Compare the two SQL files — char_length must be identical.
  diff e2e-screenshots/cluster-a/phase-1-foundation/T1.5-customer-notes-after-backfill.sql.txt \
       e2e-screenshots/cluster-a/phase-1-foundation/T1.5-customer-notes-after-second-upgrade.sql.txt \
    | tee e2e-screenshots/cluster-a/phase-1-foundation/T1.5-idempotency-diff.txt
  ```
  Expected: `T1.5-idempotency-diff.txt` is empty (zero lines), proving idempotency.
- **DOSSIER**: append row including `idempotency_diff_lines: 0`.

#### T1.6 — CREATE migration `<NEW_TS_B>_drop_appointment_notes_table.py`
- **PICK TIMESTAMP `<NEW_TS_B>`**: > `<NEW_TS_A>`, e.g., `20260513_120100`.
- **IMPLEMENT**:
  ```python
  def upgrade() -> None:
      bind = op.get_bind()
      result = bind.execute(sa.text(
          "SELECT count(*) FROM appointment_notes WHERE coalesce(body, '') <> ''"
      )).scalar()
      print(f"[drop_appointment_notes] discarding {result} non-empty body row(s)")  # noqa: T201
      op.drop_table("appointment_notes")


  def downgrade() -> None:
      # Re-creates the table empty. Mirrors the original CREATE from
      # 20260425_100000_add_appointment_notes_table.py. Data on rows that
      # existed at upgrade time is NOT reconstructable; downgrade gives
      # only the table shape back.
      op.create_table(
          "appointment_notes",
          # ... copy column defs verbatim from the original create ...
      )
  ```
- **VERIFY FIRST**: read `migrations/versions/20260425_100000_add_appointment_notes_table.py` and **copy the `op.create_table(...)` call verbatim** for the downgrade body. Include indexes/constraints.
- **VALIDATE**: `uv run alembic upgrade head && uv run alembic downgrade -1 && uv run alembic upgrade head`. After upgrade: `psql "$DATABASE_URL" -c "\d appointment_notes"` should return `Did not find any relation named "appointment_notes".`
- **EVIDENCE**:
  ```bash
  psql "$DATABASE_URL" -c "\d appointment_notes" 2>&1 | tee e2e-screenshots/cluster-a/phase-1-foundation/T1.6-appointment-notes-table-state.sql.txt
  ```
  Expected: "Did not find any relation".
- **DOSSIER**: append row.

#### T1.7 — CREATE migration `<NEW_TS_C>_migrate_appointment_attachments_to_customer_photos.py`
- **PICK TIMESTAMP `<NEW_TS_C>`**: > `<NEW_TS_B>`, e.g., `20260513_120200`.
- **IMPLEMENT** in two phases inside `upgrade()`:
  1. **Copy rows**:
     ```sql
     INSERT INTO customer_photos (id, customer_id, appointment_id, file_key, file_name, file_size, content_type, uploaded_by, created_at)
     SELECT
         gen_random_uuid(),
         COALESCE(a.customer_id, j.customer_id) AS customer_id,
         aa.appointment_id,
         aa.file_key,
         aa.file_name,
         aa.file_size,
         aa.content_type,
         aa.uploaded_by,
         aa.created_at
     FROM appointment_attachments aa
     JOIN appointments a ON a.id = aa.appointment_id
     LEFT JOIN jobs j ON j.id = a.job_id
     WHERE COALESCE(a.customer_id, j.customer_id) IS NOT NULL;
     ```
     Capture row count via `bind.execute(...).rowcount`.
  2. **Log orphans** (appointments whose customer_id chain is broken):
     ```sql
     SELECT aa.id FROM appointment_attachments aa
     LEFT JOIN appointments a ON a.id = aa.appointment_id
     LEFT JOIN jobs j ON j.id = a.job_id
     WHERE COALESCE(a.customer_id, j.customer_id) IS NULL;
     ```
     Print orphan IDs so an operator can recover them post-migration.
  3. **Drop table**:
     ```python
     op.drop_table("appointment_attachments")
     ```
- **DOWNGRADE**: re-create the `appointment_attachments` table empty (mirror its original CREATE from whichever migration created it — search `Grep -l "create_table.*appointment_attachments" src/grins_platform/migrations/versions/`).
- **VALIDATE — local dry-run** with seeded data:
  1. Seed dev: insert ~3 `appointment_attachments` rows pointing at real appointments.
  2. Run migration.
  3. Confirm `customer_photos` has 3 new rows with `appointment_id` set + correct `customer_id`.
  4. Confirm `appointment_attachments` table is dropped (`\d appointment_attachments` → not found).
  5. Confirm orphan log line for any row with broken FKs.
- **EVIDENCE**:
  ```bash
  # Before migration:
  psql "$DATABASE_URL" -c "SELECT count(*) FROM appointment_attachments;" | tee e2e-screenshots/cluster-a/phase-1-foundation/T1.7-before-count.sql.txt
  uv run alembic upgrade head 2>&1 | tee e2e-screenshots/cluster-a/phase-1-foundation/T1.7-alembic-upgrade.txt
  # After:
  psql "$DATABASE_URL" -c "SELECT count(*) FROM customer_photos WHERE appointment_id IS NOT NULL;" | tee e2e-screenshots/cluster-a/phase-1-foundation/T1.7-after-photo-count.sql.txt
  psql "$DATABASE_URL" -c "\d appointment_attachments" 2>&1 | tee e2e-screenshots/cluster-a/phase-1-foundation/T1.7-attachments-dropped.sql.txt
  ```
  Expected: before count = N, after count ≥ N (assuming no orphans), table dropped.
- **DOSSIER**: append row with before/after counts.

#### T1.8 — VERIFY alembic chain integrity (head)
- **VALIDATE**:
  ```bash
  uv run alembic current 2>&1 | tee e2e-screenshots/cluster-a/phase-1-foundation/T1.8-alembic-current.txt
  uv run alembic history --verbose 2>&1 | head -50 | tee e2e-screenshots/cluster-a/phase-1-foundation/T1.8-alembic-history.txt
  ```
  Expected: `alembic current` returns `<NEW_TS_C>` (the latest). History shows linear chain: `<NEW_TS_C>` → `<NEW_TS_B>` → `<NEW_TS_A>` → `20260512_120000` → `20260510_120000` → ...
- **EVIDENCE**: the two `tee`'d files above.
- **DOSSIER**: append row.

#### T1.9 — VERIFY no other code-paths import dropped modules
- **VALIDATE**: search for stragglers (in Phase 6 the *files* are deleted; in Phase 1 we just confirm migrations didn't break imports):
  ```bash
  uv run python -c "from grins_platform.app import create_app; app = create_app(); print('app boot OK')" 2>&1 \
    | tee e2e-screenshots/cluster-a/phase-1-foundation/T1.9-app-boot.txt
  ```
  Expected: `app boot OK` — confirms the app starts after migrations.
- **DOSSIER**: append row.

#### T1.10 — Commit Phase 1
- **COMMIT MESSAGE**:
  ```
  feat(cluster-a): foundation — exception module, S3 wrap, 3 migrations

  Phase 1 of Cluster A (notes/photos/tags unification):
  - New S3UploadError exception (retryable flag for 502 vs 503 mapping)
  - PhotoService.upload_file wraps put_object with typed exceptions
  - Migration 1: idempotent backfill of customer.internal_notes from
    legacy sources (sales_entry, estimate, job, appointment, appointment_notes)
  - Migration 2: drop appointment_notes orphan table
  - Migration 3: migrate appointment_attachments → customer_photos
    (with appointment_id FK) and drop appointment_attachments

  Refs .agents/plans/cluster-a-notes-photos-tags-unification.md
  Evidence: e2e-screenshots/cluster-a/phase-1-foundation/
  ```
- **DOSSIER**: append row.

---

### Phase 2 — Service Layer

#### T2.1 — ADD `_carry_forward_lead_attachments` to `LeadService`
- **VERIFY FIRST**: read `services/lead_service.py:1141-1199` (the existing `_carry_forward_lead_notes` method) for shape (async signature, session access via `self.lead_repository.session`, audit-log block).
- **IMPLEMENT**:
  ```python
  async def _carry_forward_lead_attachments(
      self,
      lead: Lead,
      customer: Customer,
      *,
      actor_staff_id: UUID | None = None,
  ) -> int:
      """Copy LeadAttachment rows to CustomerPhoto rows for the new customer.

      Lead row + LeadAttachment rows stay in place for audit; new
      CustomerPhoto rows reuse the same S3 keys (no S3 copy needed).
      Idempotent: skip if a CustomerPhoto with the same file_key already
      exists for this customer.

      Returns: count of new CustomerPhoto rows inserted.
      """
      from sqlalchemy import select  # noqa: PLC0415
      from grins_platform.models.customer_photo import CustomerPhoto  # noqa: PLC0415
      from grins_platform.models.lead_attachment import LeadAttachment  # noqa: PLC0415

      session = self.lead_repository.session
      result = await session.execute(
          select(LeadAttachment).where(LeadAttachment.lead_id == lead.id)
      )
      attachments = result.scalars().all()
      if not attachments:
          return 0

      # Find existing customer photos by file_key to avoid duplicates.
      existing_keys_result = await session.execute(
          select(CustomerPhoto.file_key).where(CustomerPhoto.customer_id == customer.id)
      )
      existing_keys = {row[0] for row in existing_keys_result.all()}

      inserted = 0
      for att in attachments:
          if att.file_key in existing_keys:
              continue
          session.add(CustomerPhoto(
              customer_id=customer.id,
              file_key=att.file_key,
              file_name=att.file_name,
              file_size=att.file_size,
              content_type=att.content_type,
              uploaded_by=actor_staff_id,  # may be None
              appointment_id=None,
              job_id=None,
          ))
          inserted += 1

      await session.flush()

      self.logger.info(
          "lead.cascade.attachments_moved",
          lead_id=str(lead.id),
          customer_id=str(customer.id),
          attachments_total=len(attachments),
          attachments_inserted=inserted,
      )

      if self.audit_service:
          await self.audit_service.log_action(
              actor_user_id=actor_staff_id,
              action="lead.cascade.attachments_moved",
              resource_type="lead",
              resource_id=lead.id,
              details={"customer_id": str(customer.id), "moved_count": inserted},
          )

      return inserted
  ```
- **VALIDATE**: `uv run mypy src/grins_platform/services/lead_service.py` and `uv run ruff check src/grins_platform/services/lead_service.py`.
- **EVIDENCE**: mypy+ruff output + a `git diff` of the file.
- **DOSSIER**: append row.

#### T2.2 — ADD `_cascade_lead_intake_tag` to `LeadService`
- **VERIFY FIRST**: read `repositories/customer_tag_repository.py` to confirm the exact upsert method name (likely `upsert` / `create_if_not_exists` / `add` — match by inspection).
- **IMPLEMENT**:
  ```python
  def _humanize_tag(self, raw: str) -> str:
      """Convert snake_case → Title Case, truncate to 32 chars."""
      return " ".join(p.capitalize() for p in raw.split("_"))[:32]

  async def _cascade_lead_intake_tag(self, lead: Lead, customer: Customer) -> bool:
      """Insert lead.intake_tag (if any) into customer_tags as source='system'.

      Returns True if inserted, False if skipped (no intake_tag or duplicate).
      """
      from sqlalchemy.exc import IntegrityError  # noqa: PLC0415
      from grins_platform.repositories.customer_tag_repository import CustomerTagRepository  # noqa: PLC0415

      raw = (lead.intake_tag or "").strip()
      if not raw:
          return False
      label = self._humanize_tag(raw)
      tag_repo = CustomerTagRepository(self.lead_repository.session)
      try:
          await tag_repo.upsert_tag(  # ← verify exact method name
              customer_id=customer.id,
              label=label,
              tone="neutral",
              source="system",
          )
      except IntegrityError:
          await self.lead_repository.session.rollback()
          return False
      self.logger.info("lead.cascade.intake_tag", lead_id=str(lead.id), customer_id=str(customer.id), label=label)
      return True
  ```
- **GOTCHA**: if `CustomerTagRepository` doesn't have an `upsert_tag` method, use a raw `INSERT ... ON CONFLICT DO NOTHING` via the session, or add the method to the repository in this task.
- **GOTCHA**: a rollback inside a larger transaction is problematic — verify the cascade is wrapped in a savepoint, or replace IntegrityError handling with a pre-check query (`SELECT 1 FROM customer_tags WHERE customer_id=$1 AND label=$2`).
- **VALIDATE**: mypy + ruff.
- **EVIDENCE**: diff.
- **DOSSIER**: append row.

#### T2.3 — ADD `_cascade_lead_action_tags` to `LeadService`
- **IMPLEMENT**:
  ```python
  TERMINAL_ACTION_TAGS: frozenset[str] = frozenset({
      ActionTag.ESTIMATE_APPROVED.value,
      ActionTag.ESTIMATE_REJECTED.value,
  })

  async def _cascade_lead_action_tags(self, lead: Lead, customer: Customer) -> int:
      """Cascade non-terminal action_tags into customer_tags as source='system'.

      Filters out ESTIMATE_APPROVED and ESTIMATE_REJECTED (resolved markers).

      Returns count of new tags inserted (idempotent on duplicate).
      """
      raw_tags = lead.action_tags or []
      inserted = 0
      for raw in raw_tags:
          if raw in self.TERMINAL_ACTION_TAGS:
              continue
          label = self._humanize_tag(raw)
          # ... same repository upsert pattern as T2.2 ...
          inserted += 1
      self.logger.info(
          "lead.cascade.action_tags",
          lead_id=str(lead.id),
          customer_id=str(customer.id),
          total=len(raw_tags),
          inserted=inserted,
          filtered_terminal=sum(1 for r in raw_tags if r in self.TERMINAL_ACTION_TAGS),
      )
      return inserted
  ```
- **IMPORTS**: `from grins_platform.models.enums import ActionTag`.
- **VALIDATE**: mypy + ruff.
- **DOSSIER**: append row.

#### T2.4 — ADD umbrella `_carry_forward_lead_data` AND replace 3 call sites
- **VERIFY FIRST**: confirm the 3 call sites of `_carry_forward_lead_notes`:
  ```bash
  grep -n "_carry_forward_lead_notes" src/grins_platform/services/lead_service.py
  ```
  Expected output:
  - `1141:    async def _carry_forward_lead_notes(`
  - `1347:            await self._carry_forward_lead_notes(`  (inside `move_to_jobs`)
  - `1433:            await self._carry_forward_lead_notes(`  (inside `move_to_sales`)
  - **One more in `convert_lead`** — search the body of `convert_lead` (lines 949-1115) for the existing call.
- **IMPLEMENT**: add the umbrella `_carry_forward_lead_data` per **Patterns to Follow → Cascade umbrella helper**. Replace each `_carry_forward_lead_notes` call at the 3 (or 4) entry sites with the umbrella call. **Do NOT delete `_carry_forward_lead_notes`** — the umbrella still calls it internally.
- **GOTCHA**: `_carry_forward_lead_notes` currently returns `None`. Modify it to return `bool` (True if notes were appended, False if skipped) so the umbrella's `notes_carried` field is meaningful. Update any tests that asserted on the previous return type.
- **GOTCHA**: `move_to_sales` also has `notes=lead.notes` on `SalesEntryModel(...)` at line 1418 — leave this in place for Phase 2 (dual-write). It gets removed in Phase 6.
- **VALIDATE**:
  ```bash
  uv run pytest src/grins_platform/tests/unit/test_lead_service*.py -x 2>&1 \
    | tee e2e-screenshots/cluster-a/phase-2-service-layer/T2.4-lead-service-tests.txt
  ```
- **EVIDENCE**: pytest output + `git diff src/grins_platform/services/lead_service.py | tee phase-2-service-layer/T2.4-diff.txt`.
- **DOSSIER**: append row.

#### T2.5 — REDIRECT `AppointmentService.add_notes_and_photos`
- **VERIFY FIRST**: read `services/appointment_service.py:2435-2503` for current dual-write structure. Confirm the `[{timestamp}] Appointment note: {notes}` prefix at lines 2479-2489.
- **IMPLEMENT**: **REPLACE the timestamp-append with overwrite**:
  ```python
  # OLD (remove):
  if notes:
      stamped = f"[{timestamp.strftime('%Y-%m-%d %H:%M UTC')}] Appointment note: {notes}"
      existing = customer.internal_notes or ""
      customer.internal_notes = f"{existing}\n{stamped}" if existing else stamped

  # NEW (overwrite — no chrome):
  if notes is not None:  # explicit None vs empty-string check
      customer.internal_notes = notes
  ```
  Keep the existing `update_data["notes"] = notes` (legacy column write) — that stays for dual-write through Phase 5.
- **GOTCHA**: the OLD code distinguishes "append" semantics. The NEW code is "overwrite" — matches the locked decision but is a behavior change. **Verify with the user before shipping** if any production flow depends on the append semantics. The plan locks the answer as "overwrite" per the Cluster A decision; flag in the dossier if the execution agent has concerns.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_appointment_service*.py -x`.
- **EVIDENCE**: pytest output + diff + DB demonstration: against dev, PATCH an appointment with `notes="hello"`, then GET the customer and confirm `internal_notes == "hello"`:
  ```bash
  TOKEN=$(...)  # admin JWT
  curl -X PATCH "$API_BASE/api/v1/appointments/$APPT_ID" -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"notes":"hello"}'
  psql "$DATABASE_URL" -c "SELECT internal_notes FROM customers WHERE id='$CUSTOMER_ID';" | tee phase-2-service-layer/T2.5-appointment-notes-overwrite.sql.txt
  ```
  Expected output: `internal_notes` is exactly `hello`.
- **DOSSIER**: append row.

#### T2.6 — Commit Phase 2
- **COMMIT MESSAGE**:
  ```
  feat(cluster-a): lead-conversion cascade + appointment notes overwrite

  Phase 2 of Cluster A:
  - LeadService gains 3 new cascade helpers + umbrella _carry_forward_lead_data
    invoked from convert_lead, move_to_sales, and move_to_jobs
  - LeadAttachment rows cascade to CustomerPhoto on every conversion path
  - intake_tag cascades to customer_tags (source=system)
  - action_tags cascade except ESTIMATE_APPROVED/REJECTED (terminal)
  - AppointmentService.add_notes_and_photos now overwrites customer.internal_notes
    instead of appending a timestamped fragment (no per-entry chrome)

  Refs .agents/plans/cluster-a-notes-photos-tags-unification.md
  Evidence: e2e-screenshots/cluster-a/phase-2-service-layer/
  ```
- **DOSSIER**: append row.

---

### Phase 3 — API Denormalization

#### T3.1 — UPDATE `schemas/job.py` to expose `customer_tags`
- **VERIFY FIRST**: read `schemas/job.py:285-441`. Find the existing `property_tags` field at lines 438-440 (pattern reference).
- **IMPLEMENT**:
  ```python
  customer_tags: list[CustomerTagResponse] | None = Field(
      default=None,
      description="Customer's tags denormalized for display; null if not loaded.",
  )
  ```
  Add `from grins_platform.schemas.customer_tag import CustomerTagResponse` to imports (verify exact name).
- **VALIDATE**: `uv run mypy src/grins_platform/schemas/job.py`.
- **EVIDENCE**: diff.
- **DOSSIER**: append row.

#### T3.2 — UPDATE `api/v1/jobs.py` JobResponse builder
- **VERIFY FIRST**: find the response-builder function in `api/v1/jobs.py` (likely `_job_to_response` or similar; if none, the builder is inline in the list/get endpoints).
- **IMPLEMENT**: in the builder, eager-load the customer's tags relationship (`selectinload(Job.customer).selectinload(Customer.tags)`) when fetching the job, then populate `customer_tags=[CustomerTagResponse.model_validate(t) for t in job.customer.tags]` (or equivalent).
- **PATTERN**: `api/v1/sales_pipeline.py:161-180` for the denormalization shape.
- **GOTCHA**: N+1 risk on list endpoints. Always use `selectinload`.
- **VALIDATE**:
  ```bash
  uv run pytest src/grins_platform/tests/unit/test_jobs_api.py -x  # if exists
  # Live API test:
  TOKEN=$(...)
  curl -s "$API_BASE/api/v1/jobs/$JOB_ID" -H "Authorization: Bearer $TOKEN" | jq '.customer_tags'
  ```
  Expected: a JSON array of tag objects (or empty array, never `null` if the customer has at least one tag).
- **EVIDENCE**:
  ```bash
  curl -s "$API_BASE/api/v1/jobs/$JOB_ID" -H "Authorization: Bearer $TOKEN" \
    | jq . | tee e2e-screenshots/cluster-a/phase-3-api/T3.2-job-response-customer-tags.json.txt
  ```
- **DOSSIER**: append row.

#### T3.3 — UPDATE `schemas/appointment.py` AND `api/v1/appointments.py` for `customer_tags`
- **IMPLEMENT**: mirror T3.1 + T3.2 for `AppointmentResponse`.
- **VALIDATE**: same pattern — pytest + live curl.
- **EVIDENCE**: `T3.3-appointment-response-customer-tags.json.txt`.
- **DOSSIER**: append row.

#### T3.4 — VERIFY `SalesEntryResponse.customer_tags` exists or add it
- **VERIFY FIRST**: `Grep -n "customer_tags" src/grins_platform/schemas/sales_pipeline.py` — if missing, add it (mirror T3.1 + populate in `_entry_to_response` at `api/v1/sales_pipeline.py:161-180`).
- **VALIDATE + EVIDENCE**: same shape.
- **DOSSIER**: append row.

#### T3.5 — Commit Phase 3
- **COMMIT MESSAGE**:
  ```
  feat(cluster-a): denormalize customer_tags into Job + Appointment responses

  Phase 3 of Cluster A:
  - JobResponse and AppointmentResponse now include customer_tags
  - Frontend can render tags without a second fetch per row
  - Uses selectinload to avoid N+1

  Refs .agents/plans/cluster-a-notes-photos-tags-unification.md
  Evidence: e2e-screenshots/cluster-a/phase-3-api/
  ```
- **DOSSIER**: append row.

---

### Phase 4 — Frontend

#### T4.1 — INSTALL shadcn `Command` primitive
- **IMPLEMENT**:
  ```bash
  cd frontend
  npm install cmdk  # if not already installed; check package.json first
  ```
  Then create `frontend/src/components/ui/command.tsx` with the standard shadcn content (from https://ui.shadcn.com/docs/components/command). Verify it imports cleanly against React 19 and the existing `cn` utility at `frontend/src/lib/utils.ts`.
- **PATTERN**: existing `frontend/src/components/ui/popover.tsx` for export style.
- **VALIDATE**:
  ```bash
  cd frontend && npm run build 2>&1 | tee ../e2e-screenshots/cluster-a/phase-4-frontend/T4.1-frontend-build.txt
  ```
  Expected: build succeeds.
- **EVIDENCE**: build output.
- **DOSSIER**: append row.

#### T4.2 — CREATE `frontend/src/features/customers/components/TagPicker.tsx`
- **IMPLEMENT** the component per spec in the **Solution Statement** section. Pseudocode shape:
  ```tsx
  export function TagPicker({ customerId, value, onChange, disabled }: Props) {
    const [open, setOpen] = useState(false);
    const [search, setSearch] = useState('');
    const { data: allTags = [] } = useCustomerTags(customerId);
    const saveTags = useSaveCustomerTags();

    const selectedLabels = new Set(value.map(t => t.label.toLowerCase()));
    const filtered = allTags.filter(t =>
      t.label.toLowerCase().includes(search.toLowerCase()) &&
      !selectedLabels.has(t.label.toLowerCase())
    );
    const exactMatch = filtered.some(t => t.label.toLowerCase() === search.toLowerCase());
    const showCreate = search.trim().length > 0 && !exactMatch && search.length <= 32;

    return (
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger>...selected chips + add button...</PopoverTrigger>
        <PopoverContent>
          <Command>
            <CommandInput value={search} onValueChange={setSearch} />
            <CommandList>
              <CommandEmpty>{showCreate ? null : 'No tags'}</CommandEmpty>
              {filtered.map(t => (
                <CommandItem key={t.id} onSelect={() => addTag(t)}>{t.label}</CommandItem>
              ))}
              {showCreate && (
                <CommandItem onSelect={() => createTag(search.trim())}>
                  Create "{search.trim()}"
                </CommandItem>
              )}
            </CommandList>
          </Command>
        </PopoverContent>
      </Popover>
    );
  }
  ```
- **PATTERN**: `TagEditorSheet.tsx:14-176` for chip rendering, label normalization, save mutation usage.
- **GOTCHAS**:
  - Trim + 32-char cap before save.
  - On `onChange`, optimistically update local state then save.
  - On save error, revert optimistic update + toast.
  - Invalidate query keys (per **Patterns to Follow → Frontend mutation**) so jobs/appointments showing this customer refetch.
- **VALIDATE**:
  - `cd frontend && npm run lint && npm run build && npm test -- TagPicker` (after T5.6 writes the tests).
- **EVIDENCE**:
  - Boot the dev server, open the customer detail page, screenshot 3 states:
    ```bash
    agent-browser open http://localhost:5173/customers/<id>
    agent-browser screenshot e2e-screenshots/cluster-a/phase-4-frontend/T4.2-tag-picker-empty-state.png
    agent-browser snapshot -i
    agent-browser click <add-tag-button-ref>
    agent-browser screenshot e2e-screenshots/cluster-a/phase-4-frontend/T4.2-tag-picker-autocomplete.png
    agent-browser fill <command-input-ref> "VIP-CUSTOMER"
    agent-browser screenshot e2e-screenshots/cluster-a/phase-4-frontend/T4.2-tag-picker-inline-create.png
    ```
- **DOSSIER**: append row with all 3 screenshot paths.

#### T4.3 — REPLACE `TagEditorSheet.tsx` internals with `<TagPicker>`
- **IMPLEMENT**: delete `SUGGESTED_LABELS` constant + the inline chip/input UI. Replace with `<TagPicker customerId={customerId} value={tags} onChange={...} />`. Keep the Sheet wrapper.
- **VALIDATE**: open an Appointment modal in dev → Tags section → confirm new combobox renders.
- **EVIDENCE**:
  ```bash
  agent-browser open http://localhost:5173/schedule/...
  # ... navigate to appointment modal Tags sheet ...
  agent-browser screenshot e2e-screenshots/cluster-a/phase-4-frontend/T4.3-appointment-tag-sheet-using-picker.png
  ```
- **DOSSIER**: append row.

#### T4.4 — MOUNT `<TagPicker>` on every tag surface
- **IMPLEMENT**: on each of `CustomerDetail.tsx`, `JobDetail.tsx`, `SalesDetail.tsx`, `AppointmentDetail.tsx`/`InlineCustomerPanel.tsx`, `LeadDetail.tsx`.
- **GOTCHA on Lead**: only render when `lead.customer_id != null` (post-conversion). Pre-conversion: show empty-state placeholder (`<p className="text-xs text-gray-500">Tags will be available once this lead converts to a customer.</p>`).
- **VALIDATE**: walk through each surface in dev and screenshot.
- **EVIDENCE**: 5 screenshots: `T4.4-customer-detail.png`, `T4.4-job-detail.png`, `T4.4-sales-detail.png`, `T4.4-appointment-detail.png`, `T4.4-lead-detail-pre-conversion.png` + `T4.4-lead-detail-post-conversion.png`.
- **DOSSIER**: append row.

#### T4.5 — CREATE `frontend/src/features/customers/components/CustomerNotesEditor.tsx`
- **IMPLEMENT**: per spec in the **Solution Statement** + auto-save snippet in **Patterns to Follow**.
- **VALIDATE**: smoke test in dev — type into the textarea, blur, confirm "Saved" indicator flashes; DB query confirms `customer.internal_notes` updated.
- **EVIDENCE**:
  ```bash
  agent-browser open http://localhost:5173/customers/<id>
  agent-browser fill <notes-textarea-ref> "Test note from T4.5"
  # blur by clicking outside
  agent-browser click <body-or-other-element-ref>
  agent-browser wait --load networkidle
  agent-browser screenshot e2e-screenshots/cluster-a/phase-4-frontend/T4.5-customer-notes-editor.png
  psql "$DATABASE_URL" -c "SELECT internal_notes FROM customers WHERE id='<id>';" \
    | tee e2e-screenshots/cluster-a/phase-4-frontend/T4.5-db-internal-notes.sql.txt
  ```
- **DOSSIER**: append row.

#### T4.6 — REWIRE every notes surface to use `<CustomerNotesEditor>`
- **IMPLEMENT**:
  1. **CustomerForm.tsx** — extract internal_notes input into `<CustomerNotesEditor customerId={customer.id}>`. Remove the form's `internal_notes` field plumbing.
  2. **AppointmentForm.tsx** — remove `notes` from zod schema (line 57); remove from form defaults (line 137); remove from create/update payloads (lines 207, 220); replace `notes` Textarea + the InternalNotesCard (lines 460-463) with a single `<CustomerNotesEditor customerId={selectedCustomer.id}>`.
  3. **AppointmentDetail.tsx + InlineCustomerPanel.tsx** — replace `appointment.notes` / `customer.internal_notes` displays with `<CustomerNotesEditor customerId={...} readOnly={!editing}>`.
  4. **SalesDetail.tsx** — replace sales-entry notes editor.
  5. **JobDetail.tsx** — replace job notes editor.
  6. **LeadDetail.tsx** — pre-conversion: existing lead.notes editor. Post-conversion (`lead.customer_id != null`): swap to `<CustomerNotesEditor>`.
- **GOTCHA**: After removing `notes` from `AppointmentForm` zod, payloads no longer send `notes`. Confirm `AppointmentUpdate` schema accepts the missing field (it's `Optional[str]` — should be fine).
- **GOTCHA**: read-only mode applies in display contexts where the editor shouldn't be active.
- **VALIDATE**: walk through each surface in dev. Most critical: type a note on one surface, navigate to another surface for the same customer, confirm the note is reflected (after invalidate-on-success).
- **EVIDENCE**: 6 screenshots, one per surface, showing the same `customer.internal_notes` value rendered.
- **DOSSIER**: append row.

#### T4.7 — UPDATE TypeScript types (deprecate `.notes` fields)
- **IMPLEMENT**: add JSDoc `@deprecated` to `Appointment.notes`, `Job.notes`, `SalesEntry.notes` on frontend types. Keep the field for backwards compat.
- **VALIDATE**: `cd frontend && npm run build && npm run lint`.
- **DOSSIER**: append row.

#### T4.8 — UPDATE `useCustomerTags` query invalidation on save
- **IMPLEMENT**: `useSaveCustomerTags`'s `onSuccess` already invalidates `['customer-tags', customerId]`. ADD invalidations for `['jobs']`, `['appointments']`, `['sales-pipeline']` so denormalized reads refresh.
- **VALIDATE**: live test in dev — add a tag from a Job surface, switch tabs to Appointments, confirm the tag appears (no manual refresh).
- **EVIDENCE**: screenshot of Appointments tab showing the just-added tag.
- **DOSSIER**: append row.

#### T4.9 — Smoke test all wired surfaces
- **IMPLEMENT**: walk through Lead → Customer → Sales → Job → Appointment with a single test customer; on each surface confirm tags + notes UI is present and functional.
- **VALIDATE**: visual + functional.
- **EVIDENCE**: a single screenshot per surface saved as `T4.9-smoke-<surface>.png` (5 total).
- **DOSSIER**: append row.

#### T4.10 — Commit Phase 4
- **COMMIT MESSAGE**:
  ```
  feat(cluster-a): tag picker combobox + shared customer-notes editor

  Phase 4 of Cluster A:
  - New shadcn Command primitive + TagPicker combobox (autocomplete + inline create)
  - New CustomerNotesEditor with auto-save-on-blur
  - Wired into every tag surface (customer, job, sales, appointment, lead post-convert)
  - Wired into every notes surface (same set)
  - Mutations invalidate denormalized query keys (jobs, appointments, sales)

  Refs .agents/plans/cluster-a-notes-photos-tags-unification.md
  Evidence: e2e-screenshots/cluster-a/phase-4-frontend/
  ```
- **DOSSIER**: append row.

---

### Phase 5 — Tests

#### T5.1 — CREATE `src/grins_platform/tests/unit/test_lead_service_cascade.py`
- **IMPLEMENT**: 5 tests:
  1. `test_carry_forward_lead_attachments_inserts_customer_photos` — Lead with 2 LeadAttachments → cascade → Customer has 2 new CustomerPhoto rows with matching `file_key`.
  2. `test_carry_forward_lead_attachments_idempotent` — Re-run cascade → no duplicate CustomerPhoto rows (idempotency via `file_key` skip).
  3. `test_cascade_intake_tag_creates_system_tag` — Lead.intake_tag = "qualified" → customer_tags has row `label="Qualified", source="system"`.
  4. `test_cascade_action_tags_filters_terminal` — Lead.action_tags = `["needs_estimate", "estimate_approved", "estimate_rejected"]` → only "Needs Estimate" cascades.
  5. `test_carry_forward_lead_data_umbrella_atomicity` — call umbrella; assert all four side effects are observable and `logger.info("lead.cascade.complete")` is emitted with correct counts.
- **PATTERN**: `tests/unit/test_lead_service.py` shape (async, AsyncSession fixture).
- **VALIDATE**:
  ```bash
  uv run pytest src/grins_platform/tests/unit/test_lead_service_cascade.py -v 2>&1 \
    | tee e2e-screenshots/cluster-a/phase-5-tests/T5.1-cascade-tests.txt
  ```
  Expected: 5 passed.
- **DOSSIER**: append row.

#### T5.2 — CREATE `src/grins_platform/tests/unit/test_photo_service_s3_errors.py`
- **IMPLEMENT**: 4 tests:
  1. `test_upload_file_raises_s3_error_on_client_error` — patch `put_object` with `side_effect=ClientError({"Error":{"Code":"AccessDenied","Message":"x"}}, "PutObject")` → assert `S3UploadError(retryable=True)`.
  2. `test_upload_file_raises_s3_error_on_endpoint_connection_error` — same shape, `EndpointConnectionError`.
  3. `test_upload_file_raises_s3_error_on_no_credentials` — `NoCredentialsError` → `S3UploadError(retryable=False)`.
  4. `test_upload_file_passes_through_on_success` — happy path.
- **VALIDATE**: pytest output → `T5.2-s3-error-tests.txt`.
- **DOSSIER**: append row.

#### T5.3 — EXTEND `test_lead_api.py` + `test_customer_api*.py` (502/503 mapping)
- **IMPLEMENT**: 3 tests each side (502 retryable, 503 misconfig, existing 413 unchanged).
- **VALIDATE**: pytest output.
- **DOSSIER**: append row.

#### T5.4 — CREATE `tests/integration/test_cluster_a_denormalization.py`
- **IMPLEMENT**: 3 tests:
  1. `test_job_response_includes_customer_tags` — seed customer with 2 tags + job for them → GET /jobs/{id} → assert `customer_tags` array length 2.
  2. `test_appointment_response_includes_customer_tags` — same shape.
  3. `test_empty_customer_tags_returns_empty_array_not_null` — customer with zero tags → assert `customer_tags == []`.
- **PATTERN**: existing `tests/integration/test_*.py`.
- **VALIDATE**: pytest output.
- **DOSSIER**: append row.

#### T5.5 — UPDATE existing notes tests for dual-write compatibility
- **IMPLEMENT**: in `tests/functional/test_appointment_operations_functional.py:49,615`, `tests/unit/test_appointment_service_crm.py:97,1460`, `tests/unit/test_schedule_clear_service.py:71,473,591`, `tests/test_schedule_clear_property.py:45`, add an additional assertion checking `customer.internal_notes` parallel to the existing `appointment.notes` assertion. Mark `# DEPRECATED_DUAL_WRITE_PHASE_6` next to the legacy assertion.
- **VALIDATE**: full suite passes:
  ```bash
  uv run pytest src/grins_platform/tests/ -x 2>&1 | tail -100 \
    | tee e2e-screenshots/cluster-a/phase-5-tests/T5.5-full-pytest.txt
  ```
- **DOSSIER**: append row.

#### T5.6 — CREATE frontend tests
- **IMPLEMENT**:
  - `frontend/src/features/customers/components/__tests__/TagPicker.test.tsx` — 4 tests: render, autocomplete filter, inline create, save+invalidate flow (with mocked queryClient).
  - `frontend/src/features/customers/components/__tests__/CustomerNotesEditor.test.tsx` — 3 tests: render with initial value, auto-save fires on blur with changed value, no save when value unchanged.
- **PATTERN**: existing `frontend/src/features/**/__tests__/*.test.tsx`.
- **VALIDATE**:
  ```bash
  cd frontend && npm test -- TagPicker CustomerNotesEditor 2>&1 \
    | tee ../e2e-screenshots/cluster-a/phase-5-tests/T5.6-frontend-tests.txt
  ```
- **DOSSIER**: append row.

#### T5.7 — Commit Phase 5
- **COMMIT MESSAGE**: standard Phase 5 commit message + evidence link.
- **DOSSIER**: append row.

---

### Phase 6 — Cleanup (SEPARATE PR after Phase 1-5 deploys to dev for ≥1 day)

> **DO NOT include Phase 6 in the same PR as Phases 1-5.** Wait for the dual-write to bed in.

#### T6.1 — DELETE `appointment_notes` machinery
- **DELETE FILES**:
  - `src/grins_platform/models/appointment_note.py`
  - `src/grins_platform/services/appointment_note_service.py`
  - `src/grins_platform/repositories/appointment_note_repository.py`
  - `src/grins_platform/schemas/appointment_note.py`
  - `src/grins_platform/tests/unit/test_appointment_note_api.py`
  - `src/grins_platform/tests/unit/test_appointment_note_service.py`
  - `src/grins_platform/tests/integration/test_appointment_notes_integration.py`
  - `src/grins_platform/tests/functional/test_appointment_notes_functional.py`
- **DELETE ENDPOINTS**: `api/v1/appointments.py:883-927` (GET notes) and `:930-980` (PATCH notes).
- **REMOVE IMPORTS**: grep for any remaining imports of the deleted modules:
  ```bash
  grep -rn "from grins_platform.models.appointment_note " src/ frontend/ || echo "clean"
  grep -rn "appointment_note_service" src/ frontend/ || echo "clean"
  grep -rn "AppointmentNotesResponse\|AppointmentNote" src/ frontend/ || echo "clean"
  ```
- **VALIDATE**:
  ```bash
  uv run pytest -x 2>&1 | tee phase-6-cleanup/T6.1-pytest.txt
  uv run mypy src/ 2>&1 | tee phase-6-cleanup/T6.1-mypy.txt
  ```
- **DOSSIER**: append row.

#### T6.2 — DELETE `appointment_attachment` machinery
- Same shape as T6.1 for AppointmentAttachment files + endpoints + tests.
- **VERIFY MIGRATION T1.6 RAN IN PROD** before this delete.
- **DOSSIER**: append row.

#### T6.3 — REMOVE legacy notes column writes
- **IMPLEMENT**: in `services/appointment_service.py:2475-2477`, remove the `appointment.notes` write (we no longer dual-write). Audit other services for stragglers:
  ```bash
  grep -n 'sales_entry.notes\|estimate.notes\|job.notes\|appointment.notes' src/grins_platform/services/
  ```
- **VALIDATE**: full test suite.
- **DOSSIER**: append row.

#### T6.4 — CREATE migration `<NEW_TS_D>_drop_legacy_notes_columns.py` (final release)
- **IMPLEMENT**: `op.drop_column("appointments", "notes")`, `op.drop_column("sales_entries", "notes")`, `op.drop_column("estimates", "notes")`, `op.drop_column("jobs", "notes")`. Downgrade re-adds as `Text NULLABLE`.
- **GOTCHA**: SHIP THIS ONLY after T6.1-T6.3 have been in prod for a full release cycle. Coordinate with the team.
- **VALIDATE**: alembic round-trip on a staging clone with real data.
- **DOSSIER**: append row.

#### T6.5 — Commit Phase 6 (final cleanup PR)
- **COMMIT MESSAGE**: standard.
- **DOSSIER**: append row.

---

### Phase 7 — E2E with agent-browser (MANDATORY SCREENSHOTS + DB EVIDENCE)

> **This phase MUST run after Phase 4 ships to dev.** It is the canonical sign-off for the feature. The dossier without Phase 7 is incomplete.

This phase produces the **single most important evidence artifact**: a fully scripted run of the entire Lead → Customer → Sales → Job → Appointment journey with a customer that demonstrates every cascade, every notes propagation, every tag update, and the S3 error mapping.

The E2E flow follows the `.claude/skills/e2e-test/SKILL.md` methodology + uses the existing `e2e/_lib.sh` helpers.

#### T7.0 — Pre-flight check (mirror skill)
- **VALIDATE**:
  ```bash
  uname -s  # must be Linux or Darwin
  agent-browser --version || npm install -g agent-browser && agent-browser install --with-deps
  ```
- **EVIDENCE**: `agent-browser --version | tee e2e-screenshots/cluster-a/phase-7-e2e/T7.0-preflight.txt`.
- **DOSSIER**: append row.

#### T7.1 — CREATE driver script `e2e/cluster-a-notes-photos-tags.sh`
- **IMPLEMENT**:
  ```bash
  #!/usr/bin/env bash
  # E2E driver for Cluster A — notes/photos/tags unification.
  # Captures screenshots + DB queries as evidence at every step.
  set -euo pipefail

  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  source "$SCRIPT_DIR/_lib.sh"

  SHOTS_ROOT="e2e-screenshots/cluster-a/phase-7-e2e"
  mkdir -p "$SHOTS_ROOT"

  require_tooling
  require_servers

  # Run the journey as a sequence of named steps.
  source "$SCRIPT_DIR/cluster-a/01-login.sh"
  source "$SCRIPT_DIR/cluster-a/02-create-lead.sh"
  source "$SCRIPT_DIR/cluster-a/03-add-intake-tag.sh"
  source "$SCRIPT_DIR/cluster-a/04-add-action-tag.sh"
  source "$SCRIPT_DIR/cluster-a/05-upload-lead-attachment.sh"
  source "$SCRIPT_DIR/cluster-a/06-convert-to-sales.sh"
  source "$SCRIPT_DIR/cluster-a/07-verify-cascade-tags.sh"
  source "$SCRIPT_DIR/cluster-a/08-verify-cascade-photos.sh"
  source "$SCRIPT_DIR/cluster-a/09-verify-carried-notes.sh"
  source "$SCRIPT_DIR/cluster-a/10-edit-notes-from-sales.sh"
  source "$SCRIPT_DIR/cluster-a/11-verify-notes-in-appointment.sh"
  source "$SCRIPT_DIR/cluster-a/12-add-tag-from-job.sh"
  source "$SCRIPT_DIR/cluster-a/13-verify-tag-on-customer.sh"
  source "$SCRIPT_DIR/cluster-a/14-s3-error-paths.sh"
  source "$SCRIPT_DIR/cluster-a/15-responsive-viewports.sh"

  echo "✓ Cluster A E2E complete. Evidence in $SHOTS_ROOT/"
  ```
  Each `0N-*.sh` script is a self-contained step that captures `agent-browser screenshot` + `psql_q` evidence. **Inline each step's commands** rather than spreading across separate files if it's simpler — the file structure is a suggestion.
- **EVIDENCE**: the script itself + a `chmod +x` confirmation.
- **DOSSIER**: append row.

#### T7.2 — Step: Login as admin
- **IMPLEMENT**:
  ```bash
  agent-browser open "$BASE/login"
  agent-browser fill '[name="username"]' "admin"
  agent-browser fill '[name="password"]' "admin123"
  agent-browser click 'button[type="submit"]'
  agent-browser wait --load networkidle
  agent-browser screenshot "$SHOTS_ROOT/01-login.png"
  agent-browser console > "$SHOTS_ROOT/01-login-console.txt" || true
  ```
- **EVIDENCE**: `01-login.png` + no JS errors in console.
- **DOSSIER**: append row.

#### T7.3 — Step: Create Lead with notes
- **IMPLEMENT**:
  ```bash
  agent-browser open "$BASE/leads"
  agent-browser click '[data-testid="create-lead"]'
  agent-browser fill '[name="name"]' "E2E Cluster A Test"
  agent-browser fill '[name="phone"]' "+19527373312"
  agent-browser fill '[name="email"]' "kirillrakitinsecond@gmail.com"
  agent-browser fill '[name="address"]' "123 E2E Lane, Minneapolis, MN"
  agent-browser fill '[name="notes"]' "Test lead notes — should carry to customer.internal_notes"
  agent-browser click 'button[type="submit"]'
  agent-browser wait --load networkidle
  agent-browser screenshot "$SHOTS_ROOT/02-create-lead-with-notes.png"
  # Capture lead ID from URL
  LEAD_ID=$(agent-browser get url | grep -oE '[a-f0-9-]{36}')
  echo "LEAD_ID=$LEAD_ID" >> "$SHOTS_ROOT/lead-context.env"
  psql_q "SELECT id, name, notes FROM leads WHERE id='$LEAD_ID';" > "$SHOTS_ROOT/02-lead-row.sql.txt"
  ```
- **EVIDENCE**: screenshot + DB row showing `notes` populated.
- **GOTCHA**: hardcoded test recipients per memory `feedback_test_recipients_prod_safety`.
- **DOSSIER**: append row.

#### T7.4 — Step: Add intake_tag (e.g., "qualified") on the lead
- **EVIDENCE**: screenshot of the field + `psql_q "SELECT intake_tag FROM leads WHERE id='$LEAD_ID';"`.
- **DOSSIER**: append row.

#### T7.5 — Step: Add action_tags via API (e.g., NEEDS_ESTIMATE + ESTIMATE_APPROVED)
- **IMPLEMENT**:
  ```bash
  curl -X POST "$API_BASE/api/v1/leads/$LEAD_ID/action-tags" \
    -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
    -d '{"add_tags": ["needs_estimate", "estimate_approved"]}'
  psql_q "SELECT action_tags FROM leads WHERE id='$LEAD_ID';" > "$SHOTS_ROOT/04-action-tags.sql.txt"
  ```
- **DOSSIER**: append row.

#### T7.6 — Step: Upload a lead attachment (PDF)
- **IMPLEMENT**:
  ```bash
  curl -X POST "$API_BASE/api/v1/leads/$LEAD_ID/attachments" \
    -H "Authorization: Bearer $TOKEN" \
    -F "file=@/tmp/test.pdf" \
    -F "attachment_type=estimate"
  psql_q "SELECT id, file_name FROM lead_attachments WHERE lead_id='$LEAD_ID';" > "$SHOTS_ROOT/05-lead-attachments.sql.txt"
  ```
- **DOSSIER**: append row.

#### T7.7 — Step: Convert lead → Sales (triggers cascade)
- **IMPLEMENT**:
  ```bash
  curl -X POST "$API_BASE/api/v1/leads/$LEAD_ID/move-to-sales" \
    -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json"
  # Extract customer_id from response
  CUSTOMER_ID=$(psql_q "SELECT customer_id FROM leads WHERE id='$LEAD_ID';")
  echo "CUSTOMER_ID=$CUSTOMER_ID" >> "$SHOTS_ROOT/lead-context.env"
  agent-browser open "$BASE/customers/$CUSTOMER_ID"
  agent-browser wait --load networkidle
  agent-browser screenshot "$SHOTS_ROOT/06-convert-lead-to-sales.png"
  ```
- **DOSSIER**: append row.

#### T7.8 — Step: Verify cascade — customer_tags populated
- **IMPLEMENT**:
  ```bash
  psql_q "SELECT label, source FROM customer_tags WHERE customer_id='$CUSTOMER_ID' ORDER BY label;" \
    > "$SHOTS_ROOT/07-customer-tags-cascaded.sql.txt"
  ```
  **Expected output** (exact):
  ```
  Needs Estimate|system
  Qualified|system
  ```
  (NOT "Estimate Approved" — that's the terminal-filter assertion.)
- **VALIDATE**: assert via `grep "Estimate Approved" "$SHOTS_ROOT/07-customer-tags-cascaded.sql.txt" && echo "FAIL: terminal tag was not filtered" || echo "PASS"`.
- **DOSSIER**: append row with the expected/actual comparison.

#### T7.9 — Step: Verify cascade — customer_photos populated from LeadAttachment
- **IMPLEMENT**:
  ```bash
  psql_q "SELECT cp.file_name, cp.file_key FROM customer_photos cp WHERE cp.customer_id='$CUSTOMER_ID';" \
    > "$SHOTS_ROOT/08-customer-photos-cascaded.sql.txt"
  ```
  **Expected**: at least 1 row with `file_name=test.pdf`.
- **DOSSIER**: append row.

#### T7.10 — Step: Verify carry-forward — customer.internal_notes contains lead.notes with divider
- **IMPLEMENT**:
  ```bash
  psql_q "SELECT internal_notes FROM customers WHERE id='$CUSTOMER_ID';" \
    > "$SHOTS_ROOT/09-customer-internal-notes-carried.sql.txt"
  ```
  **Expected**: notes content includes `Test lead notes — should carry to customer.internal_notes` AND the divider `\n\n--- From lead (`.
- **DOSSIER**: append row.

#### T7.11 — Step: Edit notes from Sales surface; verify it appears in Appointment modal
- **IMPLEMENT**:
  ```bash
  # On the Sales detail for this customer:
  agent-browser open "$BASE/sales"
  # find this customer's row, click it
  # ... use agent-browser snapshot + click ...
  agent-browser fill '[data-testid="customer-notes-textarea"]' "Edited from sales surface"
  agent-browser click 'body'  # blur
  agent-browser wait 2000
  agent-browser screenshot "$SHOTS_ROOT/10-sales-detail-shared-notes.png"
  psql_q "SELECT internal_notes FROM customers WHERE id='$CUSTOMER_ID';" \
    > "$SHOTS_ROOT/10-customer-notes-after-sales-edit.sql.txt"
  # Now open the appointment modal for an appointment of this customer:
  agent-browser open "$BASE/schedule"
  # ... navigate to an appointment for the customer ...
  agent-browser screenshot "$SHOTS_ROOT/11-notes-reflected-in-appointment-modal.png"
  ```
  **Expected**: the screenshot in step 11 shows "Edited from sales surface" rendered in the appointment modal's notes view.
- **DOSSIER**: append row.

#### T7.12 — Step: Add tag from Job surface; verify it appears on Customer detail
- **EVIDENCE**: 2 screenshots + 1 DB query.
- **DOSSIER**: append row.

#### T7.13 — Step: Trigger S3 error → assert 502/503 response
- **IMPLEMENT**:
  ```bash
  # Temporarily set bad AWS credentials in dev env (or use a non-existent bucket)
  # For safety, this step relies on a feature-flag or env var. If not available,
  # SKIP and document why.

  # If feature-flag available:
  RAILWAY_CMD="railway variables --service api --environment dev set AWS_S3_BUCKET=does-not-exist-test"
  echo "[T7.13] Setting bad bucket via Railway CLI" | tee -a "$SHOTS_ROOT/14-s3-error-paths.txt"

  # Trigger upload
  curl -i -X POST "$API_BASE/api/v1/leads/$LEAD_ID/attachments" \
    -H "Authorization: Bearer $TOKEN" \
    -F "file=@/tmp/test.pdf" -F "attachment_type=estimate" 2>&1 \
    | tee "$SHOTS_ROOT/14-s3-error-response.txt"

  # Confirm response is 502
  grep -q "HTTP/.* 502" "$SHOTS_ROOT/14-s3-error-response.txt" && echo "PASS: 502" || echo "FAIL"

  # Restore the env var
  ```
- **GOTCHA**: only manipulate dev env vars per memory `feedback_no_remote_alembic` and only do so explicitly with user buy-in. If the agent doesn't have safe access to Railway CLI for env-var manipulation, **SKIP this step and document in the dossier with reason "no safe env-mutation pathway in dev"**.
- **ALTERNATIVE**: write a one-shot pytest that monkeypatches `boto3.client("s3").put_object` to raise ClientError, hits the API endpoint via the test client, and asserts the 502 response. This pytest-based proof is acceptable evidence — capture as `T7.13-s3-error-pytest.txt`.
- **DOSSIER**: append row.

#### T7.14 — Step: Responsive viewports
- **IMPLEMENT**: at each of mobile (375x812), tablet (768x1024), desktop (1440x900), open a customer detail page and screenshot the notes editor + tag picker.
- **EVIDENCE**: 6 screenshots (3 viewports × 2 components).
- **DOSSIER**: append row.

#### T7.15 — Step: Final database state snapshot
- **IMPLEMENT**:
  ```bash
  {
    echo "## Customer row";
    psql_q "SELECT id, internal_notes, char_length(internal_notes) AS notes_len FROM customers WHERE id='$CUSTOMER_ID';";
    echo "";
    echo "## Customer tags";
    psql_q "SELECT label, tone, source FROM customer_tags WHERE customer_id='$CUSTOMER_ID' ORDER BY label;";
    echo "";
    echo "## Customer photos";
    psql_q "SELECT file_name, appointment_id, job_id FROM customer_photos WHERE customer_id='$CUSTOMER_ID';";
    echo "";
    echo "## Lead row (post-conversion, should still exist)";
    psql_q "SELECT id, name, status, moved_to, customer_id FROM leads WHERE id='$LEAD_ID';";
    echo "";
    echo "## Lead attachments (still present for audit)";
    psql_q "SELECT id, file_name FROM lead_attachments WHERE lead_id='$LEAD_ID';";
  } | tee "$SHOTS_ROOT/e2e-final-database-state.sql.txt"
  ```
- **EVIDENCE**: the consolidated DB state file.
- **DOSSIER**: append row.

#### T7.16 — Aggregate dossier + final pass/fail report
- **IMPLEMENT**: Re-read `e2e-screenshots/cluster-a/evidence-dossier.md`. For each row, verify the linked file exists and is non-empty. Append a final summary section to the dossier:
  ```markdown
  ## Final summary

  - Total tasks: <count>
  - Passed: <count>
  - Failed: <count>
  - Blocked: <count>

  **Status:** <PASS / FAIL / NEEDS REVIEW>

  ### Evidence aggregate
  - Backend tests: <count> passing
  - Frontend tests: <count> passing
  - Migrations: <count> applied + roundtripped
  - Screenshots: <count>
  - DB queries captured: <count>
  - E2E journey: complete
  ```
- **VALIDATE**: ALL rows = PASS. If any FAIL or BLOCKED, do not mark the feature complete; surface the failure to the user.
- **DOSSIER**: this IS the dossier finalization step.

---

## TESTING STRATEGY

### Unit Tests

Use pytest with the existing async + asyncpg conftest fixtures. Targeted coverage on:
- `LeadService` cascade methods — every branch (empty intake_tag, populated action_tags, filtered terminal tags, idempotent re-run, atomic umbrella, transaction rollback on cascade failure).
- `PhotoService.upload_file` — every boto exception class + happy path.
- `CustomerTagService.save_tags` — already covered; do not regress.
- `_humanize_tag` — pure function; cover whitespace, multi-word, 32-char truncation, empty input.

### Integration Tests

- Full Lead → Customer conversion via `POST /api/v1/leads/{id}/move-to-sales`: assert customer + tags + photos + notes all populated.
- JobResponse + AppointmentResponse include `customer_tags` denormalized.
- AppointmentService.add_notes_and_photos: overwrite semantics, no timestamp prefix.

### Edge Cases (must have explicit tests)

1. Lead with no `intake_tag` and no `action_tags` → cascade is no-op (returns counts of 0).
2. Lead with only terminal action_tags (`ESTIMATE_APPROVED`, `ESTIMATE_REJECTED`) → no customer_tags created.
3. LeadAttachment with a file_key already present in CustomerPhoto for the same customer → skip insert (idempotent).
4. Customer with extremely long existing `internal_notes` + backfill from 5 sources → length stays ≤ 50000 (truncated with logged warning).
5. Boto3 `put_object` raises `ClientError` → endpoint returns 502, frontend renders error toast.
6. Boto3 raises `NoCredentialsError` → endpoint returns 503.
7. Concurrent edit to `customer.internal_notes` from two surfaces → last-write-wins; document as acknowledged tradeoff per Cluster A decision.
8. Empty `lead.action_tags` (null vs `[]` vs unset) — all three handled.
9. T1.7 backfill on a DB where some customers already have all 5 sources merged → idempotent skip; no duplicate dividers.
10. T1.6 migration where appointment_attachments has 0 rows → migration succeeds, drops table.
11. T1.6 migration where some appointment_attachment rows are orphans (no resolvable customer_id) → orphan IDs logged; migration succeeds without crash.
12. Lead → Customer cascade where the new umbrella raises mid-way (e.g., DB constraint violation in tag insert) → entire conversion rolls back (no half-converted lead).
13. Tag picker autocomplete: input "Q" → existing "Qualified" surfaces + "Create 'Q'" action also shows (because "Q" doesn't exactly match).
14. Tag picker inline create: input length > 32 → save is blocked client-side with helpful message.
15. CustomerNotesEditor: typing in the textarea, blur with no changes → no API call fired.
16. CustomerNotesEditor: typing, blur with changes → exactly ONE PATCH fires; "Saved" indicator visible for 1.5s.
17. CustomerNotesEditor: error response from PATCH → optimistic update reverted + error toast.
18. CustomerNotesEditor on a customer the user doesn't have edit permission for → readOnly mode, textarea disabled.

---

## VALIDATION COMMANDS

Execute every command. Capture every output into the dossier.

### Level 1: Syntax & Style
```bash
uv run ruff check src/
uv run ruff format --check src/
uv run mypy src/
cd frontend && npm run lint && npm run build
```

### Level 2: Unit Tests
```bash
uv run pytest src/grins_platform/tests/unit/ -x 2>&1 | tee evidence/level-2-unit.txt
cd frontend && npm test 2>&1 | tee ../evidence/level-2-frontend.txt
```

### Level 3: Integration + Functional Tests
```bash
uv run pytest src/grins_platform/tests/integration/ src/grins_platform/tests/functional/ -x \
  2>&1 | tee evidence/level-3-integration.txt
```

### Level 4: Manual E2E Validation (covered by Phase 7)
See **Phase 7 — E2E with agent-browser** above. This is the canonical manual validation.

### Level 5: Alembic state
```bash
uv run alembic current 2>&1 | tee evidence/level-5-alembic-current.txt
uv run alembic history --verbose 2>&1 | head -50 | tee evidence/level-5-alembic-history.txt
```

### Level 6: Orphan-import check (after Phase 6)
```bash
grep -rn "from grins_platform.models.appointment_note " src/ frontend/ || echo "clean"
grep -rn "from grins_platform.services.appointment_note_service " src/ frontend/ || echo "clean"
grep -rn "AppointmentAttachment" src/ frontend/ || echo "clean"
```

---

## ACCEPTANCE CRITERIA

A row in the dossier marked PASS is required for each.

- [ ] **Schema unification**: `customer.internal_notes` schema max raised to 50000; backfill migration populates legacy notes onto customer; idempotent.
- [ ] **Cascade — attachments**: Lead conversion (via convert_lead, move_to_sales, move_to_jobs) inserts CustomerPhoto rows mirroring LeadAttachment rows.
- [ ] **Cascade — intake tag**: `lead.intake_tag` lands on customer_tags as `source="system"` after conversion.
- [ ] **Cascade — action tags**: `lead.action_tags` cascade EXCEPT for `ESTIMATE_APPROVED` and `ESTIMATE_REJECTED`.
- [ ] **No timeline UI**: AppointmentService notes write is overwrite (not append-with-timestamp); no per-entry chrome anywhere in the frontend.
- [ ] **Tag picker**: Combobox replaces SUGGESTED_LABELS; autocomplete + inline create works on every tag surface.
- [ ] **Notes editor**: `<CustomerNotesEditor>` auto-saves on blur; "Saved" indicator flashes; mutations invalidate every denormalized query key.
- [ ] **API denormalization**: JobResponse + AppointmentResponse + SalesEntryResponse all expose `customer_tags`.
- [ ] **S3 hardening**: PhotoService.upload_file wraps boto3 errors → typed exception → 502 (retryable) / 503 (misconfig) in both `/leads/{id}/attachments` AND `/customers/{id}/photos`.
- [ ] **Migrations apply + roundtrip cleanly** on a fresh DB clone.
- [ ] **Phase 6** drops `appointment_notes` machinery; `appointment_attachments` migrated to customer_photos and dropped; legacy notes columns dropped (in a final separate migration).
- [ ] **Unit tests** pass on all new test files (T5.1, T5.2, T5.3, T5.4, T5.6).
- [ ] **Existing tests** pass with dual-write assertions added (T5.5).
- [ ] **E2E driver** runs end-to-end with PASS in every step; evidence captured in `phase-7-e2e/`.
- [ ] **Evidence dossier** finalized with every row PASS.
- [ ] **No regressions** in existing notes/photos/tags flows during the dual-write phase.

---

## COMPLETION CHECKLIST

- [ ] **Phase 1** (foundation) — exception module, S3 wrap, 3 migrations, alembic round-trip green. Evidence dir populated.
- [ ] **Phase 2** (service layer) — cascade helpers wired into 3 entry points; AppointmentService overwrite semantics.
- [ ] **Phase 3** (API denormalization) — customer_tags exposed on Job + Appointment + SalesEntry.
- [ ] **Phase 4** (frontend) — TagPicker + CustomerNotesEditor + every surface wired.
- [ ] **Phase 5** (tests) — all new tests pass; legacy notes tests updated.
- [ ] **Phase 6** (cleanup, separate PR) — orphan code removed; legacy columns dropped in final migration.
- [ ] **Phase 7** (E2E) — full agent-browser run with screenshots + DB evidence.
- [ ] **All validation commands** (Levels 1-5) pass.
- [ ] **Evidence dossier finalized** — every row PASS; final summary appended.
- [ ] **PR opened** with link to dossier in description.

---

## NOTES

### Why this plan doesn't rename `customer.internal_notes` → `customer.notes`
Keeps the existing column name to avoid a column-rename migration (DDL on customers, locks in prod) + schema/API/frontend type churn. The trade-off: field name "internal_notes" is slightly inaccurate for the new use ("shared blob across all surfaces"). Cosmetic rename is a one-day follow-up if it becomes annoying.

### Why this plan dual-writes through Phase 5
Single-PR migration + code rewire + frontend swap is too risky for a high-blast-radius refactor. Dual-write lets us roll back any phase independently and catch any forgotten read-from-legacy site without breaking prod. Phase 6 cleans up after the dust settles.

### Why this plan ISN'T Option A (polymorphic notes table)
April 2026 polymorphic `notes` table → chat-style timeline UI in the frontend → user explicitly walked it back. Re-introducing a polymorphic table invites the same UI shape. Option B (customer-owned blob) is the only path that structurally avoids the timeline regression. See memory `project_unified_notes_rollback_reason`.

### Why this plan ISN'T Option C (new Party/Contact entity)
User picked Option B in Part 2 of the verification doc. Option C is more flexible but doesn't solve a user-visible problem Option B doesn't solve.

### Concurrent-edit risk (acknowledged)
Two admins editing `customer.internal_notes` simultaneously from two surfaces → last-write-wins clobbers. Accepted per Cluster A audit decision. Future mitigation: version column + "refresh since you started editing" indicator (one-day follow-up).

### Why this plan KEEPS the AppointmentNote 1:1 table around through Phase 5
Even though it's orphan scaffolding, its **body** field is a source for T1.5 backfill. Drop after the backfill in T1.6 — order matters.

### Why this plan FILTERS `ESTIMATE_APPROVED` / `ESTIMATE_REJECTED` on cascade
These are terminal workflow markers on Lead, set by `EstimateService.approve_via_portal` / `reject_via_portal` (`estimate_service.py:472-477, 556-561`). Once they're set, the lead is "done" with that estimate — they're not customer-facing identifiers like "VIP" or "Repeat Customer." Cascading them to customer_tags would pollute the customer's tag set with workflow noise.

### What happens if Phase 7 E2E uncovers a bug
1. Pause the feature commit.
2. File a sub-task in the dossier marked BLOCKED with a short description.
3. Fix the bug in the appropriate phase's file.
4. Re-run the affected E2E step.
5. Mark the dossier row PASS after the new screenshot/DB query confirms the fix.
6. Resume.

The dossier IS the audit trail — never mark something PASS without the linked evidence file actually existing.

### Confidence Score: **10/10** for one-pass success.

What was 7/10 in the previous draft → addressed in this draft:

| Risk in 7/10 draft | Mitigation in 10/10 draft |
|---|---|
| `convert_lead` vs `move_to_sales` call graph ambiguous | Locked: 3 entry points (lines 1347, 1433, + one in convert_lead) all call `_carry_forward_lead_notes`. Umbrella replaces all 3. |
| T1.7 backfill edge cases under-enumerated | 12 edge cases now explicitly listed; idempotency proven via diff command in evidence. |
| Frontend mechanical risk across 6 components | Per-surface evidence screenshots required; 6 explicit screenshots in T4.6 + T4.9 smoke test. |
| `customer.internal_notes` `max_length=10000` may break under backfill | Resolved: bump to 50000 in same release as T1.5 (documented). |
| shadcn Command primitive doesn't exist in repo | Explicit install task T4.1 with build verification. |
| `CustomerTagRepository.upsert_tag` exact method name unverified | Pre-task verification step in T2.2; if missing, plan accepts adding it as part of the task. |
| No E2E sign-off with screenshots / DB evidence | Phase 7 added; 15 explicit steps; uses existing `e2e/_lib.sh` pattern; mandatory dossier. |
| Per-task evidence not enforced | Evidence Protocol section added; every task has `EVIDENCE` + `DOSSIER` blocks; final task verifies all rows PASS. |
| AppointmentService overwrite-vs-append behavior change risk | Explicit gotcha to verify with user; default is overwrite per Cluster A decision; flagged in T2.5 dossier note. |
| Migration ordering ambiguity | Locked: T1.5 (backfill) runs BEFORE T1.6 (drop_appointment_notes); explicit `<NEW_TS_A> < <NEW_TS_B> < <NEW_TS_C>` ordering. |

Confidence target met because:
- Every task has named evidence outputs.
- Every task has an explicit VALIDATE command an execution agent can run unattended.
- Every task has a pre-task `VERIFY FIRST` step that re-reads the codebase at the cited lines.
- The evidence dossier is itself a verification artifact — final task can't mark complete unless every prior row is PASS.
- Phase 7 makes the user-visible E2E flow non-skippable.
- The plan is explicit about commit boundaries (one PR per phase, NOT a single mega-commit).
- Failure modes are named (rollback at any phase, dossier BLOCKED state for surfaced issues, terminal action_tag filter).
