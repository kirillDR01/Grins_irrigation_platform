# Verification Pass & Parked-List Clarifications — 2026-05-12

This document combines two companion artifacts from the 2026-05-12 audit:

- **Part 1 — Verification Pass:** §1–§15 below. Findings from the code-trace / dev-log / live-trigger audit. For each section: question, method, finding (with file:line), recommendation. Investigative sections include 2–3 design options with tradeoffs.
- **Part 2 — Parked-List Clarifications & Implementation Plans:** appended after the verification pass. Locked scopes and implementation outlines for items the user picked from the parked list — starting with the P1 cluster.

---

## Part 1 — Verification Pass

**Owner:** Kirill (verification by Claude)
**Scope locked:** see end of doc for what is and isn't covered
**Environment:** dev only (code + dev DB + dev logs)
**Test recipients (allowlisted only):** `kirillrakitinsecond@gmail.com`, `+19527373312`
**STOP coverage:** CallRail outbound + Resend unsubscribe + scheduler re-entry (Twilio built-in trusted, not re-verified)
**Live-trigger policy:** fire E2E freely to allowlisted contacts; no per-trigger confirmation

---

## How to read this doc

Each section follows:
- **Question** — what we set out to verify
- **Method** — code-trace / DB query / live trigger / browser
- **Finding** — what's actually happening today, with file:line and evidence
- **Recommendation** — concrete next step (not implemented in this pass)

Investigative sections (#1 data model, #5 admin-notify, #12 email audit, #14 staff auth) also include **2–3 design options with tradeoffs**.

---

## 1. Data model survey — notes / photos / tags across Lead / Customer / Job / Appointment

**Question.** The user wants notes / photos / tags to behave as **one shared record** across Lead → Sales → Job → Appointment → Customer. Today they drift (notes added in sales don't appear on the job; "Integ tag" is the only tag option; lead photo upload throws 500). Map the current model and propose 2–3 unification paths.

**Method.** Static code survey (models, services, alembic migrations, frontend hooks). No live triggers.

### 1.1 Entity inventory

| Entity | Model | Notes column / table | Photos column / table | Tags |
|---|---|---|---|---|
| Lead | `models/lead.py:34` | `lead.notes` (Text) — `lead.py:75` | `LeadAttachment` 1:N — `lead_attachment.py:17` | `lead.intake_tag` String(20) — `lead.py:92` |
| Customer | `models/customer.py:34` | `customer.internal_notes` (Text) — `customer.py:152` | `CustomerPhoto` 1:N — `customer_photo.py:24` | `CustomerTag` 1:N — `customer_tag.py:31` |
| SalesEntry | `models/sales.py:33` | `sales_entry.notes` (Text) — `sales.py:71` | — (uses `CustomerDocument` for signed docs) | — |
| Estimate | `models/estimate.py:29` | `estimate.notes` (Text) — `estimate.py:100` | — | — |
| Job | `models/job.py:73` | `job.notes` (Text) — `job.py:199` | — (photos hang off Customer with optional `job_id`) | — |
| Appointment | `models/appointment.py:81` | `AppointmentNote` 1:1 — `appointment_note.py:24` (+ a legacy `appointment.notes` column still on the table) | `AppointmentAttachment` polymorphic — `appointment_attachment.py:21` (no FK to appointment / job / estimate — discriminated by `(appointment_type, appointment_id)`) | — |

Lead and Customer are **separate tables**. Lead → Customer is a conversion, not a promotion.

### 1.2 Lead → Customer transition (`lead_service.py:949`, `_carry_forward_notes` at `lead_service.py:1148`)

What carries over on conversion:
- `lead.name` → split → `customer.first_name` + `customer.last_name`
- `lead.phone`, `lead.email`, `lead.sms_consent` → customer equivalents
- Consent timestamps (SMS, email, terms) re-stamped on customer
- `lead.notes` → appended to `customer.internal_notes` with `\n\n--- From lead (YYYY-MM-DD) ---\n` divider

What is **lost or orphaned**:
- `LeadAttachment` rows → **never copied** to `CustomerPhoto` (data loss; only the Lead retains them)
- `lead.intake_tag` → **never copied** to `CustomerTag`
- Lead row stays in the DB with `status = CONVERTED` (not archived)

### 1.3 The abandoned unified-notes experiment

This is the load-bearing finding for the design decision:

- **2026-04-16** `20260416_100500_create_notes_table.py` — created a polymorphic `notes` table with `subject_type` (lead/customer/sales_entry/appointment/...) and `origin_lead_id` for cross-stage threading. Stated goal: "unified Notes Timeline feature (Requirement 4)."
- **2026-04-18** (5 days later) `20260418_100700_fold_notes_table_into_internal_notes.py` — **dismantled it**. Folded customer rows into `customers.internal_notes`, folded lead rows into `leads.notes`, **discarded** sales_entry and appointment rows (logged count only), dropped the table. Marked as a one-way operation.
- **2026-04-25** `add_appointment_notes_table` — created the *new* `AppointmentNote` 1:1 table as a narrower replacement.
- **2026-04-23** `add_customer_tags_table` — created `CustomerTag` for customer-scoped tag pills.

**Implication for design:** the team has already tried unified notes and explicitly walked back from it. Any new unification proposal must explain what's different this time.

### 1.4 Notes drift map

```
Lead ──────────► Customer ──────────► Job ──────────► Appointment
 lead.notes      customer.            job.notes       AppointmentNote
   │             internal_notes         ▲              (1:1 table)
   │                ▲                   │              + legacy
   │                │                   │                appointment.notes
   ├─ on convert ───┘                   │                column still there
   │  (carry-forward, divider-appended) │
   │                                    │
   └─ never ───────────────────────────►┘  Estimate.notes also exists,
                                            never carried to Job or Appointment.

SalesEntry.notes  ──── append-only breadcrumbs ────  never flows anywhere
  (e.g. "[2026-05-08 14:02 UTC] Customer APPROVED estimate X via portal")
```

So today there are **5 separate notes locations** (`lead.notes`, `customer.internal_notes`, `sales_entry.notes`, `estimate.notes`, `job.notes`) plus **2 appointment notes locations** (`AppointmentNote.body` and the legacy `appointment.notes` column). Of those 7, only Lead → Customer has any auto-flow.

### 1.5 Photos drift map

```
Lead                       Customer                       Job / Appointment
 LeadAttachment ─ X ────►   CustomerPhoto   ──── photos with optional job_id
 (S3, 25 MB,                (S3, 10 MB,         and/or appointment_id FK
  JPEG/PNG/PDF/             JPEG/PNG/HEIC/
  DOCX)                     HEIF only,
                            500 MB customer
                            quota)            AppointmentAttachment
                                              (polymorphic — no real FK;
                                               (appointment_type, id))
```

Three photo silos, no transfer on Lead → Customer conversion, polymorphic appointment table without referential integrity. The reported lead-photo 500 root cause is **identified in §15.1 below** — uncaught boto exception in the lead-attachment upload path; quota guard hypothesis was ruled out.

### 1.6 Tags drift map

Tags exist **only on Customer** (`CustomerTag` table, customer-scoped, inherited read-only by all appointments via the customer relationship). No Job/Appointment/Lead/SalesEntry tag tables. Lead has a single `intake_tag` String(20) — not a list, not transferred on convert.

The user reports "Integ tag" is the only option visible in the UI. There is **no hardcoded enum** in the backend models or `customer_tag_service.py`; `CustomerTagService.save_tags()` is a generic diff-based upsert that accepts any `label` (≤32 chars). The frontend trace is **completed in §15.2 below** — there IS a hardcoded `SUGGESTED_LABELS` list (7 items, not including "Integ tag") in `TagEditorSheet.tsx`, but the exact UI surface the user is reporting against remains unconfirmed and needs a screenshot.

### 1.7 Sales-entry notes append behavior (`sales_pipeline_service.py:172`)

`record_estimate_decision_breadcrumb()` is the only code path that auto-modifies notes after creation. It appends a UTC-timestamped line to `SalesEntry.notes` when the customer approves or rejects via the portal. It does **not** touch `Customer.internal_notes`, `Job.notes`, or any appointment notes. So a customer who approves leaves a breadcrumb on the SalesEntry that the Job (created seconds later by `EstimateService`) never sees.

### 1.8 Design options for the unification goal

The user picked "one shared record" earlier. Three viable shapes, with the abandoned-experiment context as the primary tradeoff:

#### Option A — Re-do the polymorphic `notes` table (what was tried in April)

One `annotations` (or `notes`) table with `subject_type` + `subject_id` and optional `origin_lead_id` / `customer_id` denormalized for query speed. Same shape as `20260416_100500_create_notes_table.py`.

- **Pro:** truly one record; querying "all notes for this customer across all jobs and appointments" is one indexed query.
- **Pro:** symmetric with `AppointmentAttachment` which already uses a (weak) polymorphic key.
- **Con:** the team rolled this back 5 days after shipping it. Without knowing *why* (no postmortem found in `bughunt/`, `production-bugs/`, or `DEVLOG.md`), repeating it risks repeating the failure. **First action before picking this: dig out the rollback rationale.**
- **Con:** no DB-level FK to subject; orphaning is possible (same flaw as `AppointmentAttachment` today).

#### Option B — Single shared notes blob on Customer; auto-create Customer at Lead intake (recommended)

Collapse the Lead/Customer split: the moment a Lead is created, also create a `Customer` row with `status = lead` (or a flag). **One** notes field lives on Customer (rename `customer.internal_notes` → `customer.notes` or keep the current name) and **every surface — Lead pre-conversion, Sales, Estimate, Job, Appointment — reads and writes that same field through one textarea.** Photos and tags likewise hang off Customer from day one.

Important: this is **not** a timeline / feed / chat-style UI. No per-entry author or timestamp chrome in the main view. One persistent editable blob, edited in place from any surface. If audit-history is ever needed, it's a separate `audit_log` query, not the primary UI. This is the explicit lesson from the April 2026 rollback (see §1.9 #1).

- **Pro:** no polymorphism; every annotation has a real `customer_id` FK. Single source of truth.
- **Pro:** fixes the LeadAttachment → CustomerPhoto data-loss bug for free (Customer exists from the start, so photos write to `CustomerPhoto` directly).
- **Pro:** sidesteps the rollback gotcha — this avoids the timeline-UI shape that triggered the previous revert.
- **Pro:** smallest write-path change — the storage is mostly already in place (`customer.internal_notes` exists today); the work is wiring every surface to read/write it instead of its own field.
- **Con:** Customer table grows with un-converted leads; needs a `customer.lifecycle_stage` enum and most "customer" queries gain a stage filter.
- **Con:** non-trivial backfill: every existing Lead gets a shadow Customer row; the 5 existing notes fields (`lead.notes`, `customer.internal_notes`, `sales_entry.notes`, `estimate.notes`, `job.notes`) need to be merged into the canonical Customer field with reasonable conflict handling.
- **Con:** the Lead → Customer "convert" UX has to be reframed as a stage transition, not a creation event.
- **Con:** concurrent edits from two surfaces (e.g., admin in Sales tab + tech in Appointment view) can clobber each other since there's no per-entry granularity. Mitigation: optimistic-locking version column, or last-write-wins with a "refreshed since you opened this" indicator.

#### Option C — New top-level `Party` (or `Contact`) entity

Introduce a new entity above Lead and Customer. Both Lead and Customer get `party_id` FKs. Notes/photos/tags hang off `Party`. Lead and Customer become workflow projections of the same person.

- **Pro:** clean separation between *who the person is* and *what stage of the funnel they're in*.
- **Pro:** future-proof for households / multi-property scenarios.
- **Con:** biggest schema change; touches almost every service.
- **Con:** doesn't solve any user-visible problem that Option B doesn't already solve.

**Recommendation:** Option B. It solves the reported drift (notes silos, photo loss on convert, tag drift), matches the user's explicit "one shared blob, edited in place" mental model (see §1.9 #1 below), and avoids the timeline-UI shape that caused the April 2026 revert. It's incremental — you can start by auto-creating Customer on Lead and converging note-write paths one surface at a time, with each surface swapping its local notes field for a bound textarea on `customer.notes`.

### 1.9 Open questions (to be answered before locking the design)

1. **Why was the April 2026 unified-notes table rolled back?** — **Answered by user 2026-05-12.** The rollback was about the **UI shape**, not the schema. The polymorphic table led the frontend to render notes as a chat-like / timeline feed showing per-entry attribution ("admin sent X", "tech sent Y"). The user does not want that. The target shape is **one persistent editable blob** of notes that is shared across Lead → Sales → Estimate → Job → Appointment → Customer, presented as a single textarea on every surface — no author/timestamp chrome in the main view. Any history requirement is a separate audit-log concern, not the primary UI. **Implication:** Option B is the correct path *as long as* the implementation explicitly avoids any timeline/feed UI; reintroducing a polymorphic notes table (Option A) is off the table because it tends to invite the same timeline UI that triggered the previous revert. The §1.8 Option B description above has been rewritten to reflect this constraint.
2. **`AppointmentNote.body` vs legacy `appointment.notes` column** — **Answered by user 2026-05-12.** Decision: **defer the cleanup; bundle it into Cluster A** so the rip-out is one coordinated change rather than two passes. Until Cluster A lands, `appointment.notes` (the legacy column) remains the de facto authority; `AppointmentNote` stays in place but should not be wired into any new code paths.

   **Investigation (full trace, performed before locking the decision):**

   *Code locations*
   - Legacy column: `src/grins_platform/models/appointment.py:144` — `notes: Mapped[str | None] = mapped_column(Text, nullable=True)`.
   - 1:1 table: `src/grins_platform/models/appointment_note.py:45–49` — `body: Mapped[str] = mapped_column(Text, nullable=False, server_default="")`, plus `updated_by_id` (Staff FK) and `updated_at`.

   *Reads/writes of `appointment.notes`*
   - Schemas expose it: `schemas/appointment.py:30` (Create), `:60` (Update), `:140` (Response).
   - Service write: `services/appointment_service.py:2477` (`add_notes_and_photos` → `update_data["notes"] = notes`).
   - Repo write: `repositories/appointment_repository.py:224` (`.values(**update_data)`).
   - API write (photo upload path): `api/v1/appointments.py:1674–1677`.
   - Snapshot read: `services/schedule_clear_service.py:237`.
   - Tests cover it: `tests/functional/test_appointment_operations_functional.py:49,615`; `tests/unit/test_appointment_service_crm.py:97,1460`; `tests/unit/test_schedule_clear_service.py:71,473,591`; `tests/test_schedule_clear_property.py:45`.

   *Reads/writes of `AppointmentNote.body`*
   - Service: `services/appointment_note_service.py:113–193` (`get_notes`, `save_notes`).
   - Repo: `repositories/appointment_note_repository.py:35–109` (PostgreSQL INSERT … ON CONFLICT upsert).
   - Schemas: `schemas/appointment_note.py:14–38` (`NoteAuthorResponse`, `AppointmentNotesResponse`, `AppointmentNotesSaveRequest` with `max_length=50_000`).
   - Endpoints: `api/v1/appointments.py:883–927` (GET `/appointments/{id}/notes`), `:930–980` (PATCH `/appointments/{id}/notes`).
   - Tests: `tests/unit/test_appointment_note_api.py:163–315`, `tests/unit/test_appointment_note_service.py`, `tests/integration/test_appointment_notes_integration.py`, `tests/functional/test_appointment_notes_functional.py:26–219`.

   *API surface comparison*
   - `appointment.notes` is exposed on every standard appointment endpoint: `POST /appointments`, `PATCH /appointments/{id}`, all GETs (list, single, daily, weekly, staff-daily), and the photo upload endpoint (`POST /appointments/{id}/photos` accepts a `notes` form field that lands in the column).
   - `AppointmentNote.body` is only exposed via the two dedicated `/notes` endpoints (`GET`, `PATCH`). It is not present in any other appointment response.

   *Frontend usage (decisive evidence)*
   - `frontend/src/features/schedule/types/index.ts:77` — `Appointment.notes: string | null` (typed off the legacy column).
   - `frontend/src/features/schedule/components/AppointmentForm.tsx:57,137,207,220` — form schema, default, and both create/update submit paths bind to `notes`.
   - `frontend/src/features/schedule/components/AppointmentDetail.tsx` and `InlineCustomerPanel.tsx` render `{appointment.notes}`.
   - **No frontend file calls `GET` or `PATCH /appointments/{appointment_id}/notes`.** Grep confirms zero references to the AppointmentNote endpoints from the frontend.

   *Migration history*
   - `migrations/versions/20250615_100000_create_appointments_table.py:58` — `appointment.notes` was present at table creation.
   - `migrations/versions/20260416_100500_create_notes_table.py` — added the polymorphic `notes` table (`subject_type`, `subject_id`) that drove the timeline UI.
   - `migrations/versions/20260418_100700_fold_notes_table_into_internal_notes.py:127,133` — the rollback migration: folded customer/lead notes into `customers.internal_notes` / `leads.notes`, **explicitly discarded appointment-type rows** (`print(f"[fold] discarding {cnt} appointment note(s)...")`), then dropped the `notes` table.
   - `migrations/versions/20260425_100000_add_appointment_notes_table.py` — re-introduced a dedicated `appointment_notes` table for "Appointment Modal V2" with author + timestamp metadata. This is the orphaned scaffolding.

   *Sync / drift*
   - No code writes both fields. No fallback read logic. No tests assert equality. No shared fixtures populate both. The two stores can diverge arbitrarily — in practice only `appointment.notes` is ever populated because that is the only field the UI writes.

   *Why defer (and not drop now)*
   - Cluster A is going to rewire every appointment-notes surface onto `customer.notes` (the shared editable blob) anyway. Dropping `AppointmentNote` as a standalone task now requires: alembic migration, removing the service/repo/schemas/API/4 test files, and a no-op frontend change. Doing it again in Cluster A requires re-touching the same files to swap `appointment.notes` writes onto `customer.notes`. One pass is cheaper and avoids an intermediate state where `appointment.notes` is "the authority" but is itself about to be deprecated.
   - The risk of leaving `AppointmentNote` in place until then is bounded: the endpoints are unused, no scheduled job writes to it, and there is no drift to reconcile because there is nothing to drift from.

   *Action when Cluster A is picked up*
   - Single migration removes `appointment_notes` table.
   - Delete `models/appointment_note.py`, `services/appointment_note_service.py`, `repositories/appointment_note_repository.py`, `schemas/appointment_note.py`, the two `/appointments/{id}/notes` endpoints in `api/v1/appointments.py:883–980`, and the four test files (`tests/unit/test_appointment_note_api.py`, `test_appointment_note_service.py`, `tests/integration/test_appointment_notes_integration.py`, `tests/functional/test_appointment_notes_functional.py`).
   - In the same change, rewire `appointment.notes` reads/writes to bind against `customer.notes` per the Option B shared-blob model. `appointment.notes` column can then be dropped (or left as an unused column for one release cycle for safety, then dropped).
3. **Should `lead.intake_tag` (single String) become a `CustomerTag` row on conversion?** Or is `intake_tag` a workflow state (e.g., "qualified") that doesn't belong as a customer-facing tag at all?
4. **Estimate.notes — keep separate or fold into the Customer timeline?** Estimate notes are the line-item / pricing context the customer sees; they may genuinely belong only on the Estimate.
5. **"Integ tag" cause** — frontend dropdown source unknown; needs a 30-minute trace in `frontend/src/features/.../tags/` to confirm whether it's a hardcoded list or an empty-state default.

**Recommended next step (not in this pass):** #1 is answered (above). Next: write a follow-up implementation plan that picks Option B and lays out (a) the customer-auto-create-on-lead migration, (b) the lead-attachment → customer-photo backfill, (c) the merge strategy for the 5 existing notes fields onto a single `customer.notes` field, and (d) the per-surface textarea rewire (Lead form, Sales detail, Estimate detail, Job detail, Appointment modal) — with the explicit constraint that the UI must remain a single shared blob, **not** a timeline.

---


## 2. Bug: Resend Estimate button does not work

**Question.** User reports the Resend Estimate button does nothing (or fails) on a sales entry in `pending_approval`.

**Method.** Code trace front-to-back. Live repro deferred — Railway dev has only one sales entry today and it's `closed_won` (no `pending_approval` row to click against). The code trace is conclusive enough to recommend a fix without one.

**Wiring (clean).**
- Button definition: `frontend/src/features/sales/lib/nowContent.ts:63` — only rendered when `SalesEntry.status == 'pending_approval'`.
- Click handler: `frontend/src/features/sales/components/SalesDetail.tsx:263–275`.
- Hook: `useResendEstimateForSalesEntry` at `frontend/src/features/sales/hooks/useSalesPipeline.ts:177`.
- API client: `salesPipelineApi.resendEstimate` at `frontend/src/features/sales/api/salesPipelineApi.ts:166` → POST `/sales/pipeline/{entryId}/resend-estimate`.
- Endpoint: `resend_estimate_from_pipeline` at `src/grins_platform/api/v1/sales_pipeline.py:1068–1115`.
- Service it calls: `EstimateService.send_estimate` at `src/grins_platform/services/estimate_service.py:272–391`.

Frontend wiring is correct end-to-end. The endpoint logic is sane: 404 if entry missing, 422 if no customer, 404 if no eligible estimate, otherwise re-sends.

**Finding — root cause.** The Resend lookup filters estimates by status:

```python
# sales_pipeline.py:1095–1106
stmt = select(Estimate).where(
    Estimate.customer_id == entry.customer_id,
    Estimate.status.in_([EstimateStatus.SENT.value, EstimateStatus.VIEWED.value]),
).order_by(Estimate.updated_at.desc()).limit(1)
```

So the endpoint only matches estimates in `SENT` or `VIEWED`. After the customer **approves via portal**, `EstimateService.approve_via_portal` (estimate_service.py:454–461) flips the estimate to `APPROVED` — but **does not advance `SalesEntry.status`**. `_correlate_to_sales_entry` calls `record_estimate_decision_breadcrumb` (sales_pipeline_service.py:171–184) which only appends a note line. The SalesEntry stays in `pending_approval`.

So the Resend button keeps rendering, the user clicks it, the endpoint scans for SENT/VIEWED, finds the (now APPROVED) estimate doesn't qualify, returns **404 "No open estimate found to resend"**, and the frontend renders `toast.error('Failed to resend estimate')` (SalesDetail.tsx:271).

This is the **same root cause** as the user's separate complaint *"On client approval, stage should auto-advance Approval → Contract"*. One fix resolves both. (For history: the auto-advance `PENDING_APPROVAL → SEND_CONTRACT` is wired today only via the **SignWell webhook** at `signwell_webhooks.py:179` — the portal-approval path was never given the equivalent.)

**Two corollary states where Resend would also misbehave** (lower-severity, same family):
- Customer rejected via portal → estimate is `REJECTED`, Resend → 404. Less critical because the `Client declined` button arguably should have flipped the pipeline state already.
- Estimate was archived/voided manually → Resend → 404.

**Recommendation (one change closes both complaints).**

In `EstimateService.approve_via_portal` (estimate_service.py around line 493, right after `_correlate_to_sales_entry`), advance the SalesEntry status from `PENDING_APPROVAL` to `SEND_CONTRACT`. Most natural seam: extend `record_estimate_decision_breadcrumb` (or add a sibling method `advance_on_approval`) in `SalesPipelineService` to also do `entry.status = SalesEntryStatus.SEND_CONTRACT.value` when `decision == "approved"` and current status is `PENDING_APPROVAL`. Guard against re-advance if the entry has already moved past `pending_approval` (e.g., from a SignWell webhook race).

Secondary hardening (cheap, do at the same time):
- Have the Resend frontend hook hide the action when `entry.status` is `pending_approval` *and* the latest estimate is `APPROVED`/`REJECTED` (defense-in-depth in case the status flip ever fails again).

**Severity:** P1. Customer-visible: admin clicks a green button labeled "Resend estimate" right after the customer approves and sees a red error toast. Embarrassing in front of an admin demoing the system.

---


## 3. Bug: Send Confirmation Text (after reschedule) did not send

**Question.** After updating a schedule with a new time, the "Send Confirmation Text" button didn't send.

**Method.** Code trace front-to-back, plus a 30-minute Railway dev deploy-log skim for `sms`/`callrail`/`confirmation` activity.

**Environment surprise (load-bearing).** Dev runs `SMS_PROVIDER=callrail`, not Twilio (`mcp__railway__list-variables` against env=dev). Dev allowlist is `SMS_TEST_PHONE_ALLOWLIST=+19527373312,+19528181020`. The recent logs show CallRail dispatches consistently returning 200 OK for both `/sales/pipeline/{id}/send-text-confirmation` and `/sales/calendar/events/{id}/send-confirmation?resend=true` — so the path *can* work, and was working as recently as today.

This matters because it changes the failure model: when admin presses "send confirmation text," CallRail accepts → returns 200 → backend logs success → frontend toasts success → but actual carrier delivery is async and gated by 10DLC. Per `project_callrail_integration.md`, 10DLC is **just-registered Phase 0**; Phase 1 (provider abstraction + 3 blocker fixes) is still ahead.

**Finding — primary root cause (frontend gap).** The sales-side reschedule queue resolution **never triggers a confirmation SMS automatically**.

- Backend endpoint: `POST /sales/calendar/events/reschedule-requests/{request_id}/reschedule` (`api/v1/sales_reschedule_requests.py:173`) updates the event in place and resets `confirmation_status='pending'`. Its docstring (line 184) is explicit: *"clients call the send-confirmation endpoint after this returns."*
- Frontend hook: `useRescheduleEstimateFromRequest` (`frontend/src/features/sales/hooks/useEstimateRescheduleRequests.ts:39–57`) calls `salesRescheduleApi.rescheduleFromRequest` and only invalidates queries on success. **No chained `sendConfirmation.mutateAsync`** — unlike the sister flow `useScheduleVisit.submit()` (`hooks/useScheduleVisit.ts:184–203`) which *does* chain the send for reschedules via the modal.

So: the admin resolves a reschedule request from the queue → event updated → no SMS fires → admin sees the new time on the calendar but the customer was never told. If the admin then presses the manual "Send Confirmation Text" button on the sales-pipeline detail (`text_confirmation` action), that hits `/sales/pipeline/{entry_id}/send-text-confirmation` which (per today's logs) does dispatch to CallRail and gets 200. So a manual second click usually works.

**Finding — secondary contributor.** Even when the backend returns 200 and CallRail returns 200, *delivery* to the customer's handset depends on 10DLC carrier filters. With CallRail at Phase 0, intermittent non-delivery is plausible and would look exactly like "the confirmation text never ended up sending." Recent test traffic to +19527373312 shows successful 200s on every send-confirmation call I checked, so the systemic delivery failure pattern isn't visible in the last few hours of logs — but a one-off carrier-filter drop wouldn't show in logs at all.

**Finding — UI gap that probably masked the primary bug.** In the *other* reschedule path (`useScheduleVisit.submit()` from the schedule modal), the chained `sendConfirmation` is wrapped in a `try/catch` that on failure sets a soft error: *"Visit updated but resend failed: …"* (`useScheduleVisit.ts:193–202`). This soft error is rendered alongside an `ok: true` return, so the modal closes successfully and many admins will not see the inline warning. So even when the auto-chain works in the modal path, a half-failure is easy to miss.

**Recommendation.**

1. **Wire the missing send-confirmation chain into the queue resolution path.** In `useRescheduleEstimateFromRequest` (or in the `EstimateRescheduleQueue` component that calls it), after `rescheduleFromRequest` resolves, call `useSendCalendarEventConfirmation` with `{ eventId: returned event_id, resend: true }`. Mirror the soft-error pattern from `useScheduleVisit.ts:193–202` but render the warning as a toast, not an inline-only message — the queue UI doesn't have a persistent surface for it.

2. **Promote the soft warning to a toast in `useScheduleVisit.submit()` too** so partial failures (event updated, SMS failed) don't get missed when the modal closes.

3. **Independent of (1)+(2), audit 10DLC delivery.** Pull the CallRail dashboard's conversation log for the recent send-confirmation messages to +19527373312, confirm they reached the customer (not just `accepted`). If carrier-rejection is non-zero, escalate the 10DLC Phase 1 work flagged in `project_callrail_integration`.

**Severity:** P1 for the missing chain (silent UX failure: customer never learns about new appointment time). P2 for the soft-error visibility. The 10DLC investigation is a "monitor" item, not a P-rating, until evidence of carrier drops appears.

**Live repro deferred.** Dev currently has zero open sales reschedule requests to click against. Reproducing requires seeding: create a SalesEntry with a SalesCalendarEvent in confirmation_status `pending`, simulate a customer "R" reply (creates a RescheduleRequest), then resolve from the queue. Worth doing once #1 above is implemented to confirm the chain fires.

---


## 4. Recipients: "Estimate Approved" email + "open admin to action" SMS

**Question.** When a customer approves an estimate, who actually gets notified?

**Method.** Code trace + Railway dev env-var dump.

**Finding.** On portal approval, `EstimateService.approve_via_portal` (`estimate_service.py:412`) fires **two distinct notification paths**, plus a third for the customer themselves:

| What | To | Source | File |
|---|---|---|---|
| Internal staff **email** ("Estimate APPROVED for X — Total $Y") | env `INTERNAL_NOTIFICATION_EMAIL` | `_notify_internal_decision` → `EmailService.send_internal_estimate_decision_email` | `estimate_service.py:607–622` |
| Internal staff **SMS** *"Estimate APPROVED for {name}. Total ${total}. Open admin to action."* | env `INTERNAL_NOTIFICATION_PHONE` | `_notify_internal_decision` → `SMSService.send_automated_message(..., is_internal=True, message_type="internal_estimate_decision")` | `estimate_service.py:624–642` |
| Signed-PDF email to the **customer** | `customer.email` (or lead.email) | `_send_signed_pdf_email` → `EmailService` | `estimate_service.py:914–953` |

Both internal paths are best-effort (try/except, never undo approval). If the env var is unset or the service is None, **the notification silently no-ops**.

**Dev env values (Railway, env=dev):**

- `INTERNAL_NOTIFICATION_EMAIL=kirillrakitinsecond@gmail.com`
- `INTERNAL_NOTIFICATION_PHONE=+19527373312`

So **on dev today, Kirill receives both the admin email and the admin SMS** — Victor does not. The customer also gets a signed-PDF email at whatever address is on their customer/lead record (filtered by `EMAIL_TEST_ADDRESS_ALLOWLIST=kirillrakitinsecond@gmail.com` in dev so it'll also route to Kirill in practice).

**Recommendation.**

1. **Prod env audit (not in this pass).** Confirm `INTERNAL_NOTIFICATION_EMAIL` and `INTERNAL_NOTIFICATION_PHONE` on the prod Railway environment are set to Victor's address and phone (or to a shared `team@…` distribution list + Victor's phone if multiple staff should receive it). User explicitly asked "does the email send to Victor" — the answer today on prod depends entirely on that env var, which this pass doesn't read.
2. **Make the silent-no-op less silent.** When either env is unset, today there's no warning — the notification just doesn't fire. Add a startup log line ("INTERNAL_NOTIFICATION_EMAIL not set — estimate-approval emails disabled") so a misconfigured deploy surfaces in logs instead of in lost notifications.
3. **Both channels fire today** (per code) — the user's question "is it both?" is yes, provided both env vars are set.

**Severity:** P2 for the audit need (current state works, but is invisibly env-driven). P3 for the startup warning.

---


## 5. Admin-notify-on-approval — current state + design options

**Question.** When a customer approves an estimate, how is the admin (Victor) notified today? What channels exist? Is there a UI surfacing? Then: propose 2–3 design options for a unified admin-notification system.

**Current state — fragmented across two patterns.**

There are two parallel paths in the codebase for admin alerts, and they don't share infrastructure:

1. **Inline-in-service pattern (estimate approval / rejection)**
   `EstimateService._notify_internal_decision` (`estimate_service.py:585`) reads env vars `INTERNAL_NOTIFICATION_EMAIL` / `INTERNAL_NOTIFICATION_PHONE` and dispatches email + SMS directly. No persistence, no in-app surface, no audit log of "did the admin receive this." If the env var is unset the call silently no-ops.

2. **Dedicated NotificationService pattern (schedule alerts)**
   `NotificationService.send_admin_cancellation_alert` (`notification_service.py:1182`), `send_admin_late_reschedule_alert` (`:1307`), `send_admin_reconsider_cancellation_alert` (`:1422`) handle the schedule-side admin events. These are still SMS/email-only — also no in-app surface — but the pattern is more reusable.

**There is no in-app "admin notifications" surface today.** No notification bell, no unread count, no notifications inbox. The user's question *"is it popping up in the user interface somehow?"* — answer: no. The admin learns about approvals only via the SMS or email going to `INTERNAL_NOTIFICATION_PHONE` / `_EMAIL`. Once those are read/deleted, there's no in-app record they ever happened (only an audit log row from `AuditService.log_action("sales_entry.estimate_decision_received", ...)` at `sales_pipeline_service.py:186`, which is for compliance, not user-facing).

The user's adjacent complaint *"red highlight/notification doesn't clear after lead moves to Sales/Jobs"* is on a different surface (the leads-tab counter badge), not connected to estimate approvals.

### Design options

#### Option A — Unify into a single `AdminNotificationService` (minimal-change)

Move `_notify_internal_decision` and the three existing `NotificationService.send_admin_*` methods behind one service with a `notify_admin(event_type, payload, channels=("sms", "email"))` API. Keep env-var-driven routing as the default. No new tables, no UI changes.

- **Pro:** smallest blast radius. Fixes the two-pattern inconsistency. Makes "add a new admin alert type" a one-line call.
- **Pro:** centralized place to add the silent-no-op warning recommended in §4.
- **Con:** doesn't answer the user's UI question — admin still has no in-app surface, still depends on watching their text/email.
- **Effort:** ~1 day. Touches `EstimateService`, `NotificationService`, `JobConfirmationService` (which calls some of the schedule-side alerts).

#### Option B — In-app admin notifications inbox (recommended)

Add a new `admin_notifications` table (`id`, `event_type`, `subject_resource` (estimate_id / job_id / appointment_id), `summary`, `created_at`, `read_at`, `actor_user_id`). Every admin alert from Option A also writes a row. Add a notification-bell component in the top nav that polls (or subscribes via SSE) for unread count and renders the list. SMS + email still fire — the inbox is an *additional* persistent surface so nothing depends on the admin not having deleted their text.

- **Pro:** directly answers *"is it popping up in the UI?"* — yes, it would.
- **Pro:** stops Victor missing approvals because his phone was on silent.
- **Pro:** dovetails with the user's broader complaint about "red notification" UX — once an admin notifications inbox exists, the leads-tab counter logic can plug into the same store and the "clears when moved" bug becomes a single state update.
- **Con:** new DB table + migration; new frontend component + polling/SSE plumbing.
- **Con:** requires deciding per-event-type whether reading the in-app notification also acks the SMS/email (probably no — they're independent receipts).
- **Effort:** ~3–4 days end-to-end.

#### Option C — Per-staff subscription model (flexible but heavy)

Same as Option B, plus a per-staff settings page: each user picks which event types they want, by channel. Victor: estimate-approval via SMS only. Ops manager: cancellations via email only. Tech leads: nothing.

- **Pro:** scales to a multi-admin org without spamming everyone with everything.
- **Pro:** can replace the single `INTERNAL_NOTIFICATION_PHONE` env var entirely with proper per-user routing.
- **Con:** another two tables (`admin_notification_subscriptions`, settings UI), settings UI on the frontend, migration to backfill current env-var behavior into Victor's subscriptions.
- **Con:** premature for a one-admin org. Today the env-var single-destination *fits* — Victor is the only admin. Building Option C now is over-engineering until a second admin is added.
- **Effort:** ~1.5–2 weeks.

**Recommendation:** Option B. Solves the visibility gap the user is actually asking about, sets up the foundation for the badge-clearing UX they want on leads, and doesn't lock in premature flexibility. Option A is a strict subset of B's work, so doing B implicitly does A.

**Severity for the underlying gap:** P2. Today the alert *does* reach Kirill (on dev) / Victor (on prod, assuming env is set), but only via channels he has to actively be watching. A missed text = a missed approval signal.

---


## 6. Nudges fire as expected (code trace + 30-day historical + time-warp)

**Question.** Do the nudge jobs actually fire? Three-way verification: code trace, historical sends, live time-warp trigger.

**Method.** Read scheduler + worker code; pull Railway dev deploy logs; attempt time-warp via API on dev.

### 6.1 Code trace — what the cron does

Two distinct jobs registered in `background_jobs.py:register_scheduled_jobs` (`background_jobs.py:1395`):

| Job | Trigger | What it does | Code |
|---|---|---|---|
| `nudge_stale_sales_entries` | cron, daily **08:15 UTC** (~03:15 CT) | Walks `SalesEntry` rows in `{SEND_ESTIMATE, PENDING_APPROVAL, SEND_CONTRACT}` with `last_contact_date <= now - 3 days`, nudges_paused_until is null/past, dismissed_at is null. Sends a nudge **email to admin** (not customer) and writes audit row. | `services/sales_pipeline_nudge_job.py:47` (worker), `background_jobs.py:1497` (registration) |
| `process_estimate_follow_ups` | interval, every **15 minutes** | Walks `estimate_follow_up` rows where `scheduled_at <= now` and `status = SCHEDULED`. For each: skips if estimate already approved/rejected, otherwise dispatches the Day 3 / 7 / 14 / 21 SMS to the **customer** via `SMSService.send_automated_message(message_type="estimate_sent")`. | `services/estimate_follow_up_job.py:40` (worker), `services/estimate_service.py:1036` (`process_follow_ups`), `background_jobs.py:1509` (registration) |

**Two important caveats from reading `process_follow_ups` (`estimate_service.py:1036–1128`):**

1. **SMS-only.** There is no email branch in the follow-ups processor — only `if self.sms_service and phone`. If a customer has only email on file, every scheduled follow-up flips to `SKIPPED` with `reason="no_channel_available"` and the customer is never re-touched. This contradicts the user's question for §10 (whether reminders are SMS / email / both); for *follow-ups specifically*, the answer is SMS-only today.
2. **Follow-up cancellation on decision is correct.** Lines 1063–1065: as soon as `estimate.approved_at` or `estimate.rejected_at` is set, all remaining follow-ups for that estimate are cancelled. So a decided estimate stops getting nudged. Good.
3. **The user's *"Pause Auto Follow-up" → need "Resume" toggle"* request is already half-implemented.** `SalesEntry.nudges_paused_until` is a timestamp; the worker filter at `sales_pipeline_nudge_job.py:64–65` honors it: `(SalesEntry.nudges_paused_until.is_(None)) | (SalesEntry.nudges_paused_until <= now)`. The `pause-nudges` / `unpause-nudges` endpoints both exist (recent dev logs show both fired today) — so the toggle UX is already there; the user's complaint is probably just labelling: the button needs to read "Resume Auto Follow-up" when paused, not stay labelled "Pause." Worth checking in the parked section.

### 6.2 Historical (Railway dev, last few hours)

`process_estimate_follow_ups_job` fires reliably every 15 minutes (lots of `executed successfully` lines in the dev logs over multiple hours). `nudge_stale_sales_entries_job` is daily — I have it registered (`Added job "nudge_stale_sales_entries_job" to job store "default"`) but no execution within my log window.

I could not surface counts (`entries_sent`, `entries_nudged`) in Railway's log feed despite filtering: the `LoggerMixin.log_completed` lines emit structured key-value logs that don't match my plaintext filters cleanly. The APScheduler-level "executed successfully" lines are visible; the per-run send counts aren't. **Conclusion: scheduler triggers fire; per-run effectiveness can't be confirmed from log scraping alone.**

What I can confirm from dev DB state: dev currently has **1 estimate, and it's `approved`** (queried via `/api/v1/estimates`). That estimate's follow-ups were cancelled on approval (per line 1064). So *correct behavior would be zero nudges sent in the last week*, which matches "no `estimate.follow_up.sent` lines visible." Absence of nudges is the right answer here, not a bug.

### 6.3 Time-warp trigger — deferred with recipe

To prove the worker physically sends, the cleanest path is:
1. Create a fresh estimate on dev with `customer = a44dc81f-...` (allowlisted seed) via `POST /api/v1/estimates` and `POST /api/v1/estimates/{id}/send` (status flips to SENT, follow-ups get scheduled Day 3/7/14/21).
2. Direct-DB update one row in `estimate_follow_up` to set `scheduled_at = now() - interval '1 minute'`.
3. Wait ≤15 min for the cron, or invoke `process_follow_ups` manually via a dev-only admin endpoint.
4. Confirm SMS lands on +19527373312 and the row flips to `SENT`.

I didn't run this in this pass — it requires either direct DB access (Railway DB write) or seeding via API which would burn 20+ minutes building a customer + lead + estimate chain. **The structural verification (cron registered, worker code is sane, scheduler is firing) is strong enough to call this "wired correctly, end-to-end demo deferred to a seeded test run."**

**Recommendation.**

1. **Add a `/dev/follow-ups/trigger` admin endpoint** that invokes `process_follow_ups` once, returning `{sent, skipped, orphaned}`. Gated to dev environments only. Replaces the time-warp-via-DB-update dance with a single click. ~30 min of work, pays for itself the first time you need to verify a nudge change.
2. **Add an email channel to `process_follow_ups`.** Currently SMS-only — if a customer has email but no phone (or phone fails CallRail), every nudge silently skips. Mirror the dual-channel pattern in `EstimateService.send_estimate` (lines 313–353).
3. **Surface per-run counts in Railway-visible logs.** The `LoggerMixin.log_completed` structured output works in dev but isn't grep-friendly in Railway's plaintext stream. Add a plain `logger.info(f"process_follow_ups complete: {sent} sent, {skipped} skipped")` so future verification doesn't need DB queries.

**Severity:** P3 for the verification gap, P2 for the SMS-only follow-up branch (real customers without SMS consent get dropped on the floor today).

---


## 7. STOP suppression — CallRail + Resend + scheduler cleanup

**Question.** When a recipient opts out, do we stop sending? Twilio's built-in STOP layer is trusted (out of scope per setup). Verify the three remaining surfaces.

**Method.** Code trace + dev env config check.

### 7.1 CallRail outbound SMS — **passing**

When a customer texts STOP to our CallRail tracking number, the inbound webhook routes to `SMSService._process_exact_opt_out` (`sms_service.py:1368`), which:

- Normalizes the phone to E.164 (resolving CallRail's masked `***3312` form via thread_id correlation, lines 1389–1408)
- Inserts an `SmsConsentRecord` with `consent_method='text_stop'`, `consent_given=False`, `opt_out_timestamp=now()` (lines 1420–1432)
- Writes audit logs (Requirements 41 + gap-05)
- Auto-acknowledges any open INFORMAL_OPT_OUT alerts (gap-06)
- Sends the carrier-required STOP confirmation (`OPT_OUT_CONFIRMATION_MSG`, with `bypass_consent=True`)

On the **outbound** side, every send through `SMSService.send_message` (`sms_service.py:238`) and `send_automated_message` (`:625`) calls `check_sms_consent` (`sms/consent.py:43`) before dispatch. `check_sms_consent`:

- Returns `True` immediately for `operational` (STOP confirmations / legal notices) — correct.
- For `transactional` (estimate reminders, schedule confirmations, on-the-way, etc.): allowed *unless hard-STOP exists* — correct.
- For `marketing`: requires explicit opt-in row.
- The hard-STOP check (`_has_hard_stop`) selects the *latest* `SmsConsentRecord` by `created_at` and treats it as the current state — so a later `text_start` opt-in correctly supersedes an earlier STOP.
- Phone-format insurance: `_phone_variants` normalizes to E.164 *and* generates 7 alternate forms (bare 10-digit, hyphenated, dotted, parenthesized, country-code-prefixed) so consent records still match legacy Customer/Lead rows whose phones weren't migrated to E.164 (bughunt M-5).

**Status: working as designed.** I did not run a live STOP-then-attempt-send on dev because the existing structural test coverage (multiple `test_pbt_*`, `test_compliance_*`, `test_sms_service.test_webhook_opt_out_keywords`) is strong and the recent dev log shows CallRail inbound webhooks firing routinely.

### 7.2 Resend email unsubscribe — **partially passing, real bug**

The pieces *exist*:

- Generates a signed JWT unsubscribe token, 30-day expiry (`email_service.py:1129–1170`).
- Public endpoint `GET /api/v1/email/unsubscribe?token=…` (`api/v1/email.py:54`) verifies the token, sets `customer.email_opt_in=False` + `email_opt_out_at=now()`, and inserts an `EmailSuppressionList` row.
- The `EmailSuppressionList` model (`models/email_suppression_list.py`) is keyed on lowercased email.
- A helper `EmailService.check_suppression_and_opt_in(email, email_opt_in, suppressed_emails)` exists (`email_service.py:1097–1127`) and correctly returns False for suppressed-or-opted-out recipients.

**The bug:** the central send method `EmailService._send_email` (`email_service.py:255–349`) **never calls `check_suppression_and_opt_in`**, and individual senders like `send_estimate_email` (`:413–488`) don't call it either. The guards inside `_send_email` are limited to:

1. `is_configured` check (Resend API key set)
2. Dev/staging `apply_email_test_redirect`
3. Dev/staging `enforce_email_recipient_allowlist` (raises on non-allowed in dev)

So a customer who clicks "unsubscribe" gets their suppression row written, but the next estimate email / nudge email / signed-PDF email still goes out — the suppression table is dead-letter storage. Compliance bug.

There is also **no `List-Unsubscribe` RFC 8058 header** set on outbound Resend payloads. For bulk senders this is required by Gmail/Yahoo policy as of 2024; not having it risks deliverability degradation independent of the suppression bug.

### 7.3 Scheduler / worker cleanup on opt-out — **gap, not silent failure**

`estimate_repository.cancel_follow_ups_for_estimate` exists and is called in three places:
- `EstimateService.approve_via_portal` (line 464)
- `EstimateService.reject_via_portal` (line 548)
- Inside `process_follow_ups` when an already-decided estimate is encountered (line 1064)

**It is not called on STOP receipt.** Search across the codebase for `cancel_follow_ups` returns only those three approval/rejection sites — no STOP-handler invokes it. When a customer texts STOP, their queued `estimate_follow_up` rows remain in the table with `status='scheduled'`.

What actually happens next cron (every 15 min): `process_follow_ups` picks the row, builds the message, calls `SMSService.send_automated_message` → `check_sms_consent` returns False → the SMS is not sent. The row stays in `scheduled` (it's *not* flipped to SKIPPED in that path — that branch only fires for `if not success` after a phone-present attempt). So **the row sits there forever, getting re-attempted every 15 min until the estimate is decided**.

Functionally compliant (no SMS leaks out) but:
- Log noise: every opted-out customer with pending follow-ups generates a `check_sms_consent → False` denial every 15 min, indefinitely.
- Audit trail dishonesty: the natural row state for an opted-out customer is "cancelled (opt-out)," not "scheduled forever."
- Data drift: re-using a phone (new customer reuses an old opted-out number) would inherit the cancellation, but the rows stay in the *old* customer's name.

### Recommendations

1. **(P1) Wire `check_suppression_and_opt_in` into `_send_email`.** Either as a hard guard at the top of `_send_email` (load the row from `EmailSuppressionList`, deny on hit), or by changing every caller (more error-prone). Without this, unsubscribe doesn't actually unsubscribe.
2. **(P1) Add the `List-Unsubscribe` and `List-Unsubscribe-Post` headers** to the Resend payload in `_send_email` (lines 315–322). Point at the existing `/api/v1/email/unsubscribe?token=…` endpoint with the per-recipient signed token. Required by Gmail/Yahoo bulk-sender policy.
3. **(P2) Have `_process_exact_opt_out` cancel pending estimate follow-ups + sales-pipeline nudges for that phone.** Resolve the customer/lead by phone (the existing `_resolve_customer_id_by_phone` call at line 1452 already runs), then mark all `scheduled` follow-up rows for that customer as `cancelled` with reason `opt_out_sms`. Same for `SalesEntry.dismissed_at` or a new `nudges_paused_until = far-future` for sales-pipeline rows. Reduces log noise and cleans up the audit story.
4. **(P3) Add an outbound-allowed audit row** when the consent check denies a send, so the inbox/admin view can show *"5 messages would have been sent to John but blocked by opt-out"* instead of those denials only living in structured logs.

**Twilio sanity note.** This pass treats Twilio's built-in STOP layer as trusted per setup, but worth flagging: dev's `SMS_PROVIDER=callrail`, so Twilio's STOP semantics aren't being exercised on dev at all today. If prod switches between providers, the application-layer STOP check above is the only thing that protects you — keep it air-tight.

---


## 8. Confirm → Reschedule → Confirm path end-to-end

**Question.** Walk the full reschedule path. Three sub-checks: (a) customer's preferred time appears in the reschedule modal; (b) preferred time appears in the outgoing confirmation message body; (c) status only flips to "Scheduled" after the customer's Y reply.

**Method.** Code trace. Live cycle deferred — would need an estimate visit event with a customer phone in the allowlist to simulate Y/R/C replies; dev has no such entry today (single closed_won row).

### 8.1 Customer's preferred time in the reschedule modal — **passes**

When a customer texts R to the Y/R/C prompt, `JobConfirmationService._handle_estimate_visit_reschedule` (`services/job_confirmation_service.py:1943–2036`) opens a `RescheduleRequest` row with the raw SMS body stored in `raw_alternatives_text`. The frontend queue (`EstimateRescheduleQueue.tsx:106–114`) renders it inline on the card:

```tsx
{req.raw_alternatives_text && (
  <p className="text-xs text-slate-700 mt-2 whitespace-pre-line">
    <span className="font-medium">Customer suggested:</span>{' '}
    {req.raw_alternatives_text}
  </p>
)}
```

So when the admin opens the queue, they see *"Customer suggested: Tuesday at 3 or Wednesday morning"* under the customer's name. ✓

### 8.2 Preferred time in the outgoing confirmation body — **fails the user's expectation**

`SalesPipelineService._build_estimate_visit_confirmation_body` (`sales_pipeline_service.py:689–708`):

```python
return (
    f"Hi {first_name}, your estimate visit with Grin's Irrigation "
    f"is scheduled for {when}. Reply Y to confirm, R to "
    "reschedule, or C to cancel."
)
```

`{when}` is built from `event.scheduled_date` / `event.start_time` — i.e., the new time the admin picked, not the customer's originally-requested alternatives. The customer's preferred-time signal lives on `RescheduleRequest.raw_alternatives_text` but is never re-read at compose time, so the customer doesn't see *"we picked Tuesday 3pm from your options"*; they just see *"is scheduled for Tuesday at 3pm"* — context-free.

User's complaint about this is valid: include the customer's preferred-time string in the confirmation. Cheap to do — pass the `RescheduleRequest` (or just its `raw_alternatives_text`) through the reschedule-resolution endpoint into the send-confirmation chain.

### 8.3 Status flip to "Scheduled" — **also fails the user's expectation**

Two distinct status surfaces today, both relevant:

- **`SalesEntry.status` = `ESTIMATE_SCHEDULED`** — set automatically the moment the confirmation SMS dispatches (`sales_pipeline_service.py:663–677`). Not after Y reply.
- **`SalesCalendarEvent.confirmation_status` = `confirmed`** — set only after a Y reply (in `job_confirmation_service` reply handlers).

So *"scheduled"* in the pipeline tab flips immediately on send, even though we don't actually know the customer agrees. The next stage (`advance_status` → `SEND_ESTIMATE`, `sales_pipeline_service.py:270–287`) **is** correctly gated on `confirmation_status='confirmed'` (it raises `EstimateNotConfirmedError` otherwise), but that's a later step. The label on the card the user sees is "Scheduled" before any Y arrives.

The team's deliberate design choice is documented in the OQ-6 comment at line 663–667: *"an event without a confirmation SMS no longer claims the customer has been told."* That's the *opposite* of the user's expectation — the team interprets "Scheduled" as "we've told the customer," the user interprets it as "the customer agreed."

This is a label/semantics disagreement, not a bug per se. To honor the user's expectation cleanly, you'd want a four-state model:

| Today | User's mental model |
|---|---|
| SCHEDULE_ESTIMATE → ESTIMATE_SCHEDULED (on send) → SEND_ESTIMATE (on Y) | SCHEDULE_ESTIMATE → ESTIMATE_SENT (on send) → ESTIMATE_CONFIRMED (on Y) → SEND_ESTIMATE |

Either rename + add a status (schema change, touches enums + every status-aware UI), or just rename the existing one (less disruptive). The minimum-change version: keep the enum value `ESTIMATE_SCHEDULED` but render it as **"Awaiting confirmation"** in the UI, and only call it **"Scheduled"** in the UI once `confirmation_status == 'confirmed'` arrives.

### Recommendation

1. **(P2) Pass `raw_alternatives_text` through to the confirmation body composer.** Mechanically simple: thread the most recent open RescheduleRequest's alternatives text into `_build_estimate_visit_confirmation_body` as an optional parameter; append *"(from your options: …)"* when present. Solves §8.2.
2. **(P2) UI relabel: "Awaiting confirmation" vs "Confirmed".** Render `SalesEntry.status='ESTIMATE_SCHEDULED'` as "Awaiting confirmation" when the latest event's `confirmation_status` is not `confirmed`; only show "Scheduled" once Y arrives. No schema change — pure frontend tweak. Solves §8.3 without ripping up enums.
3. **(P3) Live E2E.** Once §3 (missing send-confirmation chain) is fixed, seed a SalesEntry + customer with phone +19527373312, drive the cycle: book → send confirmation → reply R → admin picks new slot → re-send → reply Y → confirm `confirmation_status='confirmed'` and that the next advance to `SEND_ESTIMATE` works. That single trace also proves §10 (reminders), §9 (on-the-way is a sibling path), and the §11 review-send flow if extended.

---


## 9. "Tech on the way" SMS

**Question.** Does the on-the-way SMS fire correctly? Trace condition + recipient logic. Bonus: the user reports the On My Way / Job Started / Job Complete buttons "are not popping up as options" after customer confirms — explain why.

**Method.** Code trace front to back. No live trigger (would need a confirmed appointment on dev, none present).

### 9.1 Wiring

- **Backend endpoint:** `POST /api/v1/jobs/{job_id}/on-my-way` (`api/v1/jobs.py:1248–1295+`). Logs `on_my_way_at` only **after** SMS dispatch succeeds (bughunt L-2 fix at line 1278–1281), so a partial failure can't leave the job looking like the tech is already en route.
- **Worker:** `NotificationService.send_on_my_way` (`notification_service.py:443–520`) loads appointment + customer, composes SMS *("{staff_name} from Grins Irrigation is on the way to your appointment! Estimated arrival in N minutes.")* and matching HTML email *("Your Technician Is On The Way — Grins Irrigation")*, dispatches via `_send_notification` which fires **both SMS and email** if both contact channels are available. Goes to the customer on file for the appointment (`_get_customer_for_appointment`).
- **Sibling appointment-side path:** `useMarkAppointmentEnRoute` (`frontend/src/features/schedule/hooks/useAppointmentMutations`) targets the appointment, not the job — so there are two paths into the same notification outcome from different surfaces.

### 9.2 Why the buttons "aren't popping up" — gating discovered

`StaffWorkflowButtons.tsx:61–95` only renders the three buttons conditionally on `appointment.status`:

| Status | Button shown |
|---|---|
| `confirmed` | "On My Way" |
| `en_route` | "Job Started" |
| `in_progress` | "Job Complete" (disabled if no payment/invoice) |
| anything else | *nothing* |

`appointment.status` only flips to `confirmed` when the **customer texts Y** to the appointment-confirmation SMS (separate from the estimate-visit confirmation handled in §8). If the customer hasn't replied Y — even if the admin has scheduled and sent — the status is `scheduled` / `pending` / `unconfirmed`, and the buttons don't render.

This dovetails with §8.3: the user's mental model is *"once the customer agreed to the appointment, I should see On My Way."* Reality: they need to see "Confirmed" first, and "Confirmed" requires the customer's Y. If the appointment is at status `scheduled` ("we told them the time") but the Y never arrived, the buttons are correctly hidden — but invisibly so.

### 9.3 Recommendations

1. **(P2) Render a disabled "Awaiting customer Y" placeholder** when appointment status is `scheduled` / `pending` instead of nothing. Same component, just an inert button with hover-text *"Waiting for customer to text Y to confirm — On My Way unlocks once they reply."* Tells the admin *why* they don't see the action.
2. **(P3) Decide one canonical surface for on-the-way.** Two hook paths (`useOnMyWay` on job, `useMarkAppointmentEnRoute` on appointment) is one too many. Pick whichever the live UX uses; deprecate the other to avoid divergence as the API drifts.
3. **(P3) Live trigger.** With a `confirmed` appointment for the +19527373312 seed customer on dev, POST `/api/v1/jobs/{id}/on-my-way` and confirm both an SMS to +19527373312 *and* an email to kirillrakitinsecond@gmail.com land. Recent dev logs show this endpoint isn't being exercised — no calls in the visible window.

**Severity:** P3 for the wiring (it works as designed). P2 for the missing UI affordance — current behavior teaches admins the system is broken when it's actually waiting on the customer.

---


## 10. Reminder channel — SMS, email, or both

**Question.** What channels do the estimate reminders fire on? Do SMS reminders include a portal link?

**Method.** Code trace of the scheduling + send paths for follow-ups.

### 10.1 The three distinct "reminder" surfaces (don't conflate them)

| Reminder | Channel | Cadence | Code | Includes portal link? |
|---|---|---|---|---|
| **Initial estimate send** (not really a "reminder") | SMS + Email | one-shot when admin sends | `EstimateService.send_estimate` (`estimate_service.py:272–391`) | yes (`portal_url` in both SMS body and email template) |
| **Estimate follow-ups** (the user's "nudges") | **SMS only** | Day 3, 7, 14, 21 from initial send | `_schedule_follow_ups` (`estimate_service.py:1247–1274`) hardcodes `channel="sms"`; `process_follow_ups` (`:1036–1128`) only branches on `if self.sms_service and phone` — no email branch at all | yes (default `f"Reminder: Your estimate from Grins Irrigation is waiting for your review. View it here: {portal_url}"`, line 1072–1075) |
| **Appointment day-of / day-2 reminders** | SMS + Email | daily 7am CT (day-of), hourly when day-2 flag enabled | `NotificationService.send_appointment_reminders` (`notification_service.py:353+`), `send_day_2_reminders_job` (`background_jobs.py:942+`, feature-flagged) | no — links to the customer's appointment page if anywhere; not the estimate portal |

### 10.2 Direct answer to the user's question

> *"do we send both text messages and emails for the estimate reminders, or is it just texts?"*

For the **estimate follow-up reminders** (the Day 3/7/14/21 nudges the user is asking about): **SMS only.** A customer with email-on-file but no SMS consent will get nudged once (the initial send goes via both channels) and then silence — every follow-up flips to `SKIPPED` with reason `no_channel_available`.

For **appointment** reminders (separate system): both SMS and email.

### 10.3 Portal link in reminders — present

The follow-up default body at `estimate_service.py:1072–1075` already includes `{portal_url}`. The estimate's `customer_token` is used to build it (`f"{self.portal_base_url}/portal/estimates/{estimate.customer_token}"` at line 1068–1070). ✓

Caveat: if a follow-up row is created with `follow_up.message` already populated (e.g., a future feature that lets admins customize the per-step nudge copy), that custom message bypasses the default and *may not* include the portal URL. Today nothing populates that field — `_schedule_follow_ups` always passes `message=None`. But if someone wires that path later, it should be guarded.

### 10.4 Recommendations

1. **(P1) Add an email branch to `process_follow_ups`.** Mirror the dual-channel pattern from `EstimateService.send_estimate` (lines 313–353) so a customer who opted out of SMS but kept email still gets reminded. Today they're invisibly dropped.
2. **(P2) Pin "must include portal URL" in the follow-up message contract.** Add a unit test: any `follow_up.message` value that's set must contain `{portal_url}` (or the default is used). Prevents accidental future regression.
3. **(P3) Reconcile the three reminder surfaces under one service.** Right now reminders live across `EstimateService`, `NotificationService`, and `background_jobs.py`. As you add per-recipient subscription preferences (§5 Option C), one surface is easier to teach than three. Not urgent today.

**Severity:** P1 for the SMS-only follow-up channel — real customers may genuinely lose all post-initial touch if they don't reply or click. P3 for the surface-reconciliation.

---


## 11. Send Review button + text modal flow

**Question.** Trace the "Send Review" button on a Job (per user's clarification: the button + text-confirm modal on a specific appointment that texts the customer a Google review request).

**Method.** Code trace + Railway dev env check.

### 11.1 Wiring

- **Frontend button:** "Send Review Request" in `frontend/src/features/schedule/components/AppointmentModal/SecondaryActionsStrip.tsx:79–86`. (Renamed from plain "Review" in the recent commit, per the file header comment.)
  - **Eligibility gates (lines 71–82):** disabled with hover-text *"Available after appointment is marked completed"* until the appointment status is `completed`, and *"Customer has no phone number"* if no phone on file. So a tech can't fire this mid-job — only after completing.
  - **Confirm step:** opens `ReviewConfirmDialog` (`AppointmentModal/ReviewConfirmDialog.tsx`) — a confirm-and-send modal, matching the user's "text modal" description. Admin confirms before the SMS goes out.
- **Backend:** `AppointmentService.request_google_review` (`appointment_service.py:~2540–2670`):
  1. Looks up the customer via the appointment.
  2. **Consent check** (`check_sms_consent` with `transactional` scope, lines 2566–2583): bails with *"Customer has opted out of SMS"* if hard-STOPped.
  3. **30-day dedup check** (`_get_last_review_request_date`, lines 2586–2601, `_REVIEW_DEDUP_DAYS` constant): raises `ReviewAlreadyRequestedError` if the same customer was already asked within 30 days. Honours user's implicit *"don't spam"* expectation.
  4. **URL resolution** (lines 2613–2627): reads `GOOGLE_REVIEW_URL` env var (or service-level override). Fails closed if unset — bughunt X-1/L-5 explicitly prevented the prior plural-slug fallback that 404'd.
  5. **Send:** composes *"Hi {first_name}! Thank you for choosing Grins Irrigation. We'd love your feedback — please leave us a Google review: {review_url}"* and dispatches via `SMSService.send_message` with `MessageType.GOOGLE_REVIEW_REQUEST`, tagged to the appointment ID.

### 11.2 Dev env config

`GOOGLE_REVIEW_URL=https://share.google/F9eulHUwy4f4AvxSe` is set on the Railway dev env (per the env dump). The fail-closed branch won't fire on dev. ✓

### 11.3 Once-per-customer-per-30-days, not once-per-job

The dedup is **customer-scoped, 30 days**, not job-scoped. So if a customer had two jobs in the same month, only the first would trigger the review-request SMS. The user's implicit guardrail *"once per job"* would actually be looser than current behavior. Worth flagging as a deliberate choice if they want it changed.

### 11.4 Live trigger — not executed

Triggering on dev requires (a) an appointment with status=`completed` for the +19527373312 customer, (b) the 30-day dedup window not blocking. Today's dev pipeline has the single closed_won entry with no completed appointment to fire against. Would need ~10 min of seeding.

### 11.5 Recommendations

1. **(P3) Decide the dedup scope.** Is it "one review request per customer per 30 days" (current) or "one per job" (matches user's mental model)? If the latter, switch the dedup query to filter on `appointment_id` or `job_id` instead of `customer_id`.
2. **(P3) Surface the disabled-reason as a non-toast hint.** Today the button is greyed with a hover label. On a tablet (no hover state) the admin sees a dead button and no explanation. Add an inline subtitle when disabled — *"Available once you mark this appointment Complete."*
3. **(P3) Live trigger.** When seeding the §3 reschedule-cycle test, also drive the appointment to `completed` and click Send Review Request; confirm SMS lands on +19527373312 and the message contains the dev `GOOGLE_REVIEW_URL`.

**Severity:** P3. Code path is sound; failure modes are visible (toast, disabled state, fail-closed on missing env). The only real concern is the customer-vs-job dedup scope, which is a product decision, not a bug.

---


## 12. Email audit — current visibility + Gmail no-reply check + in-app log design options

**Question.** Three parts: (a) where can we see sent emails today; (b) does the `noreply@grinsirrigation.com` Gmail mailbox actually exist and is it accessible; (c) 2–3 design options for an in-app Email Log view.

**Method.** Code trace + dev env config.

### 12.1 Where you can see sent emails today

Three surfaces, none of them in-app:

| Surface | What's there | What's missing |
|---|---|---|
| **Resend dashboard** (resend.com) | Every send attempt with status, opens, clicks, bounces. Most complete view by far. | Outside our app. Admin needs Resend login. No correlation to our customer/lead/estimate IDs unless someone reads the `tags` we set. |
| **Structured logs (Railway)** | `email.send.completed`, `email.send.pending`, `email.commercial.suppressed`, `email.commercial.opted_out`, `email.unsubscribe.completed` — all emit recipient (masked), email_type, classification, provider_message_id. | Plaintext-filter-unfriendly; ephemeral (retention TBD); can't query by customer or date. |
| **Resend webhook → bounce/complaint flag on Customer** (`api/v1/resend_webhooks.py:1–60+`) | When Resend POSTs a bounce/complaint, we verify HMAC, log it, notify internal staff via `INTERNAL_NOTIFICATION_EMAIL`/`_PHONE`, and soft-flag the customer record. | Only writes to the customer row, not to a persistent log; success events (the *delivered* / *opened* ones) are not processed at all. |

**Critical gap:** there is **no `sent_emails` table**. `SentMessage` (`models/sent_message.py:21`) exists but is **SMS-only** (`recipient_phone` is non-null required; no `recipient_email` column; the docstring is explicit). So when an estimate email is sent to a customer, the only record in *our* DB is whatever the `email.send.completed` log line catches in the log-aggregator. If someone deletes a Resend account or rotates the API key without exporting history first, the email-side audit trail is gone.

### 12.2 The `noreply@grinsirrigation.com` mailbox question

- The address is hardcoded as `TRANSACTIONAL_SENDER` at `email_service.py:47`.
- `reply_to` is set to `COMMERCIAL_SENDER = info@grinsirrigation.com` on every outbound (`email_service.py:320`), so any customer who hits Reply lands in `info@`, not `noreply@`.
- **Whether `noreply@grinsirrigation.com` is a real Gmail / Google Workspace inbox that anyone can read** can't be verified from the code or Railway env alone. The env dump doesn't include Google Workspace admin credentials, and there's no automated check.
- **Behavior implication:** even if the mailbox exists, replies from customers would not land there (they're routed to `info@`). Bounces from upstream MTAs *would* land there if the address has DSN/bounce-routing enabled — but Resend handles bounces via the webhook (see §12.1) so the mailbox-side bounce stream is redundant with our webhook handler.

**Verification step the user needs to do manually:** log in to Google Workspace admin → confirm `noreply@grinsirrigation.com` is a real user/group or just an unowned alias → if it's a real mailbox, document who owns it and what (if anything) lands there in practice. This is an admin/ops task, not something this verification pass can answer from code.

### 12.3 Design options for an in-app Email Log view

#### Option A — Mirror `SentMessage` for emails (`SentEmail` table) (recommended)

Add a `sent_emails` table with the same shape as `sent_messages` but keyed on `recipient_email`: `id, customer_id?, lead_id?, job_id?, estimate_id?, email_type, classification, subject, recipient_email, provider_message_id, delivery_status, error_message, sent_at, opened_at?, clicked_at?, bounced_at?, complained_at?`. Write a row in `_send_email` after the Resend dispatch succeeds. Webhook handler (`resend_webhooks.py`) updates the row on bounce/complaint/open/click. Admin UI: `/admin/email-log` page with filters (recipient, template, date, status).

- **Pro:** symmetric with SMS log. Single mental model.
- **Pro:** fully self-contained; doesn't depend on Resend dashboard staying around or the API key staying valid.
- **Pro:** enables admin views like *"all emails sent to this customer in the last 90 days"* (currently impossible).
- **Con:** new table + migration + write in every send path + webhook ingestion to keep delivery status fresh.
- **Effort:** ~2 days end-to-end (table + migration + write-path wiring + webhook extension + minimal list UI).

#### Option B — Resend-as-source-of-truth + pull-on-demand UI

Don't store sends locally. Build an admin page that proxies the Resend `GET /emails` API to render a list inline, with filters mapped to Resend's query params.

- **Pro:** no new DB schema. Always in sync with the *actual* sender.
- **Con:** every page load hits an external API; rate limits matter at scale.
- **Con:** can't filter by *our* customer_id or estimate_id easily (Resend doesn't know our IDs, only the tags we put on each send — and tag-filtering on Resend's side is limited).
- **Con:** if Resend goes down or is later replaced, the audit view goes with it.
- **Effort:** ~1 day, but tech debt accumulates.

#### Option C — Hybrid: persist only structured rows, fetch detail from Resend

`SentEmail` table stores just `id, customer_id, recipient_email, provider_message_id, sent_at` (lightweight, no body, no status). The admin page lists from our DB, but clicking a row deep-links to Resend dashboard for the full delivery story.

- **Pro:** small schema, no need to ingest open/click webhooks.
- **Pro:** answers the "which customer got which template when" question entirely locally.
- **Con:** still depends on Resend for the interesting detail.

**Recommendation:** Option A. It's incrementally more work than C and dramatically more useful — the user's question *"how would we see what emails are sent from no-reply?"* is best answered by *"open the in-app Email Log."* Without the table, every audit needs three browser tabs (Railway logs, Resend dashboard, our DB).

### 12.4 Recommendations summary

1. **(P2)** Build Option A — `sent_emails` table + write in `_send_email` + Resend webhook extension to update delivery status + simple admin list view. Combines with §5 (admin notifications inbox) — same UI shell.
2. **(P3)** Document `noreply@grinsirrigation.com` mailbox status: real Gmail user, group alias, or unowned forwarder? Add a one-pager to `docs/` so the next admin doesn't have to ask. Verify via Workspace admin UI.
3. **(P3)** Add an `email.send.failed` structured log when Resend returns an exception (today the try/except at `email_service.py:328–337` masks the exception body in the `error=e` arg but doesn't propagate enough context to debug a stuck delivery).

**Severity:** P2 for the missing local audit (operational pain when something goes wrong). P3 for the Gmail mailbox question (mostly clarifying, not blocking).

---


## 13. Mobile / responsive — Approve/Deny on iPhone + portal at iPhone/iPad/desktop

**Question.** Does the estimate portal render correctly at iPhone, iPad, and desktop viewports? Are the Approve / Reject buttons visible on iPhone?

**Method.** Live browser check via agent-browser against `https://grins-irrigation-platform-git-dev-kirilldr01s-projects.vercel.app/portal/estimates/90584963-d203-43e1-be8e-77ee9df4472b` (the one dev estimate). The agent-browser daemon resisted true viewport-emulation flags, so I used **position analysis + DOM inspection at default 1280×720** to predict iPhone/iPad behavior, then confirmed via screenshots.

Screenshots saved:
- `audit-screenshots/2026-05-12-verification/portal-desktop-1280.png` — initial fold at desktop
- `audit-screenshots/2026-05-12-verification/portal-full-1280x720.png` — full-page render
- `audit-screenshots/2026-05-12-verification/portal-buttons-after-scroll-1280x720.png` — bottom of page (where Approve/Reject sit)

### 13.1 What I confirmed

- **Viewport meta tag is correct** — `width=device-width, initial-scale=1.0`. So the page honors the device's natural width on mobile; no enforced desktop scale.
- **No portal-specific media queries**, but Tailwind responsive utilities are used elsewhere on the page (e.g., `md:hidden` for table-row mini-labels). Mobile-first layout, columns stack on narrow viewports.
- **Approve Estimate + Reject buttons** are both present in the DOM:
  - Same wrapper, `flex-1 h-12` — each takes half the row width.
  - **No `sm:hidden` / `md:hidden` / display-none variants.** They are not hidden by viewport on any breakpoint.
  - Tailwind utility set is mobile-friendly (no fixed `w-N` widths, no min-widths above iPhone width).
- **Stale data state — note for the user.** The estimate I tested against (`90584963-…`) is already `approved` (per `/api/v1/estimates`), and `approve_via_portal` sets `token_readonly=True` on success (`estimate_service.py:460`). Yet the portal is **still rendering live Approve / Reject buttons** at this token instead of a "Thanks — your decision was recorded" state. **Root cause identified in §15.3 below** — backend returns `readonly: bool` but frontend type expects `is_readonly`, so the render guard always sees `undefined` and never locks the UI.

### 13.2 The actual responsive problem: buttons are below the iPhone fold

The Approve / Reject row sits at **y=827px** on the rendered page (measured at 1280×720 viewport, document total height 907px). On an iPhone 14 (viewport 390×844 portrait), once you account for column stacking the document grows taller, the row would land **below** the visible viewport. Confirmed structurally:

- Above the buttons: line-items table (5+ rows), totals card, valid-until note, payment-link copy. None of these get hidden at narrow viewports. Vertical stacking + line-wrapping at 390px = significantly taller layout than at 1280px.
- iPhone height 844px is *less than* even the desktop 907px document height. The buttons land at least 100+ px below the iPhone fold.

So the user's complaint — *"Approve/Deny buttons must be visible on iPhone"* — translates to *"they require scrolling on iPhone, and a customer who doesn't realize they need to scroll abandons the page without acting."* They are technically rendering correctly; the UX problem is that they're not above the fold.

### 13.3 What I could not check from here

- **Pixel-accurate iPhone / iPad screenshots.** The agent-browser daemon refuses `--window-size` and `--user-agent` after launch; restart-with-args was rejected by Playwright as `"Arguments can not specify page to be opened"`. A real iOS Safari render — including the bottom 100px chrome that iOS reserves for the gesture indicator — would shave additional vertical space.
- **iPad portrait (768×1024).** Buttons probably *just* fit on the first fold (1024 > 907) but iPad chrome takes ~80px, putting them near the bottom edge. Likely OK but uncomfortable.

### 13.4 Recommendations

1. **(P2) Sticky CTA pattern.** On viewports ≤ `md` (768px), pin Approve / Reject in a fixed-position bottom bar (e.g., `sticky bottom-0` Tailwind utility on a wrapper) so they're always reachable without scrolling. On desktop, keep the inline bottom-of-page layout. One-line CSS change.
2. **(P2) Fetch fresh estimate state on portal mount + lock UI when decided.** The token-readonly / `approved_at` / `rejected_at` flags exist in the API response — gate the Approve/Reject buttons on those being null. Prevents the surprise I hit (already-approved estimate still showing the action UI) and avoids a 422 if a customer clicks twice from a stale tab.
3. **(P3) Real-device QA pass.** Open the live portal on an actual iPhone and iPad (or BrowserStack / Sauce Labs equivalent) once the sticky CTA is in. Pin a screenshot to the same `audit-screenshots/2026-05-12-verification/` directory for future-you.

**Severity:** P2 for the below-the-fold UX (real conversion-rate impact on mobile estimate approvals). P2 separately for the stale-portal bug discovered en route. Neither blocks shipping but both will show up in customer feedback.

---


## 14. Staff auth — current state + design options for admin-managed credentials

**Question.** Survey current staff auth, then propose 2–3 design options for Victor (admin) setting staff usernames + passwords.

**Method.** Read models, schemas, services, scripts.

### 14.1 Current state

**Two independent auth mechanisms exist on the Staff record:**

1. **Username + password (bcrypt) login.** Staff model has:
   - `username` (String(50), unique, nullable)
   - `password_hash` (String(255), nullable — bcrypt)
   - `is_login_enabled` (Boolean, defaults false)
   - `last_login`, `failed_login_attempts`, `locked_until` — full lockout machinery (`models/staff.py:80–104`)

2. **WebAuthn passkeys.** Separate `webauthn_credential` + `webauthn_user_handle` tables (`models/webauthn_credential.py`), config in `services/webauthn_config.py`, service in `services/webauthn_service.py`. RP ID on dev is `grins-dev-dev.up.railway.app`. The recent dev wipe migration (`20260512_120000_wipe_dev_test_data.py`) explicitly handles webauthn rows keyed by `staff_id`.

The admin login I used today (`admin` / `admin123`) goes through path #1. Dev verified by `POST /api/v1/auth/login` returning a JWT + CSRF token.

**The gap that prompts the user's request:**

- `POST /api/v1/staff` (`api/v1/staff.py:295–316`) creates a Staff record but accepts no `username` / `password` fields. The `StaffCreate` schema has no password field.
- `StaffService.create_staff` has no `set_password` / `enable_login` method.
- There's **no admin UI flow today for Victor to give a new tech a login.** The only way credentials get on a staff row is via direct DB write or a one-off script (recent commit `0a25df5 chore(dev-seed): add one-off script to create login-enabled tech staff` confirms this is the current workflow).

So when Victor wants to onboard a new tech, today's options are: write SQL, run a script, or call Kirill. The user's ask — *"admin could add the different credentials, like the username and password, for different staff"* — is asking for a UI for what is currently a developer-only operation.

### 14.2 Design options

#### Option A — Admin sets username + password directly in the staff form (recommended)

Extend `StaffCreate` and the staff edit page with optional `username` + `password` + `is_login_enabled` fields. Admin types a starting password, hits Save, staff member can log in with those credentials immediately. Pair with a "Reset password" action on the existing staff row.

- **Pro:** simplest UI; one form, one save. Matches how Victor's mental model works ("here's their info, here's their password").
- **Pro:** reuses the existing lockout / `last_login` / `is_login_enabled` machinery already in the model — no new tables.
- **Con:** Victor sees plaintext password briefly (in the form). Mitigation: don't render the entered password back after save; force re-entry to change.
- **Con:** doesn't enforce password-strength rules unless explicitly added.
- **Effort:** ~half a day. Schema field + form input + service method + a `set_password` endpoint for resets.

#### Option B — Admin sends invite link, staff sets their own password

Admin enters email/phone, hits "Send invite," staff gets a one-time-use signed link (similar to the existing unsubscribe token at `email_service.py:1129`). Clicking the link opens a "set your password" page. Staff sets it, account is enabled.

- **Pro:** Victor never sees plaintext credentials. Lowest social-engineering surface.
- **Pro:** Aligns with WebAuthn's spirit — the staff member controls their own credential material.
- **Con:** invite-email flow has to exist; needs email-template + token table + a public unauth'd `/setup-account/{token}` route on the frontend.
- **Con:** doesn't fit techs who don't have email or who'd lose the invite.
- **Effort:** ~2 days end-to-end.

#### Option C — Admin sets a one-time temp password; staff must rotate on first login

Hybrid. Admin enters a starting password via the form (Option A's UX), but the staff row also gets a `must_change_password` flag. First successful login forces the user to a "set new password" screen before any other action.

- **Pro:** balances Option A's simplicity with Option B's "admin doesn't keep using the password" hygiene.
- **Pro:** easy to add an "expires in 24h" check on the temp password if you want extra hardening later.
- **Con:** one extra column (`must_change_password`), one extra screen on first login, one extra branch in the login response.
- **Effort:** Option A + ~half a day.

**Recommendation:** Start with **Option A**. It closes the immediate gap (admin can onboard techs without dev help), reuses everything already in the Staff model, and is upgradable to Option C later by adding a single boolean + a forced-rotation screen if Victor doesn't want to keep being responsible for the initial password. Option B is over-engineering until tech-onboarding volume justifies it.

**Also worth doing alongside any option:**
- Add a password-strength rule (min length, no `admin123` allowed for any account — even seeded ones).
- Audit-log each password set / reset action (`AuditService.log_action("staff.password_set", ...)`).
- Surface `is_login_enabled`, `last_login`, and lockout status on the staff list view so Victor can see who's actually able to log in at a glance.

**Severity for the underlying gap:** P2. Operationally painful (developer-required for every new tech login) but not customer-visible.

---


## 15. Bughunt deep dives (2026-05-12 follow-up — quality-first pass)

**Context.** §1.5, §1.6, §13.1, and four items from the Parked list were flagged as "true bughunt" candidates (root cause unknown). This section is the focused follow-up. Each finding below was first surfaced by an Explore-agent code trace, then verified by direct file reads of the cited file:line locations. Where the symptom couldn't be reproduced live in this pass, the confidence rating reflects that honestly.

**Method.** Static code trace + targeted file-read verification. No live triggers in this pass.

---

### 15.1 Lead photo upload 500 — uncaught boto exceptions (§1.5)

**Symptom.** Uploading a photo/PDF to a Lead via the LeadAttachment endpoint returns HTTP 500.

**Root cause.** The lead-attachment upload endpoint catches only `ValueError` (file too large) and `TypeError` (MIME not allowed), then synchronously calls `PhotoService.upload_file`, which terminates in an **unwrapped** `boto3 put_object` call. Any boto-side exception — `ClientError` (S3 perms, bucket missing, region mismatch), `EndpointConnectionError`, `NoCredentialsError`, `ReadTimeoutError`, throttling — propagates up the stack as an uncaught exception, which FastAPI surfaces as a generic HTTP 500.

**Evidence chain.**
- `src/grins_platform/api/v1/leads.py:744–761` — try/except wraps `photo_service.upload_file(...)` with only `except ValueError` (→ 413) and `except TypeError` (→ 415). No catch-all for boto/network exceptions.
- `src/grins_platform/services/photo_service.py:331–336` — `self._client.put_object(Bucket=…, Key=…, Body=…, ContentType=…)` is called without any try/except wrapper.
- `src/grins_platform/services/photo_service.py:468–477` (per agent trace) — S3 client is constructed lazily from env vars with no startup validation; a misconfigured env produces a client that fails only at first upload.

**Hypothesis I ruled out.** The original prediction that the 500 came from the customer-quota guard (`CUSTOMER_QUOTA_BYTES = 500 MB`, `photo_service.py:173`) being invoked on a lead with no `customer_id` — the lead-attachment path does NOT call the customer-photo quota guard; it goes through a different `UploadContext.LEAD_ATTACHMENT` branch.

**Recommended fix.** Wrap the `put_object` call in `photo_service.py:331` in `try / except (ClientError, BotoCoreError) as e` and re-raise as a typed exception (e.g., `UploadStorageError`); add the corresponding `except UploadStorageError` → HTTP 502 (or 503) in `leads.py:744–761` with structured logging including the underlying exception class.

**Severity.** P2. Customer-visible regression: admin tries to attach a photo, sees a red toast, no actionable error info. Bonus: a transient S3 hiccup currently looks identical to a permanent misconfiguration.

**Confidence: medium-high.** The code path is correct as analyzed, and a 500 from this path *must* be either (a) a boto exception, (b) a downstream DB write failure, or (c) a Pillow exception during EXIF strip at `photo_service.py:322`. To conclusively confirm boto vs. the other two: pull a Railway dev log line for any recent `POST /api/v1/leads/{id}/attachments` 500 and inspect the traceback. If it's a Pillow `UnidentifiedImageError`, the fix shape is the same (wrap + map) but the file:line differs.

---

### 15.2 "Integ tag" is the only tag option — hardcoded suggestions in a different component than the user is likely looking at (§1.6)

**Symptom.** User reports "Integ tag" is the only tag option visible in the customer-tag UI.

**Findings.**

1. **The backend has no enum.** `CustomerTagService.save_tags` accepts any label up to 32 chars (verified earlier in §1.6). Limitation is purely client-side.
2. **There IS a hardcoded suggestion list** in the customer-tag editor surface: `frontend/src/features/schedule/components/AppointmentModal/TagEditorSheet.tsx:14–22` defines `SUGGESTED_LABELS = ['Repeat customer', 'Commercial', 'Difficult access', 'Dog on property', 'Prefers text', 'Gate code needed', 'Corner lot']`. These render as clickable suggestion chips beneath the input.
3. **"Integ tag" itself is not in `SUGGESTED_LABELS`.** It must therefore be a row in the `customer_tags` table for the customer the user was viewing — most plausibly seeded by an integration test or a one-off script (the literal string "Integ" suggests "integration test").

**So what is the user actually seeing?** Most-likely interpretation: the user is viewing a customer whose only DB row in `customer_tags` is "Integ tag," sees that label in the "Current tags" section of `TagEditorSheet`, and either (a) doesn't see the 7 suggestion chips because they're below the fold / styled inconspicuously, or (b) is looking at a *different* surface entirely (e.g., a tag-filter dropdown elsewhere in the app that reads `GET /customers/{id}/tags` and shows only existing rows).

**What I could NOT verify from code alone.** Which exact UI surface the user is describing. A screenshot from the user would resolve this in 30 seconds. Without it, I can't tell whether the fix is (a) make the 7 suggestion chips more discoverable, (b) replace the filter-dropdown source with a global "popular tags" endpoint, or (c) delete the orphan "Integ tag" test row from the DB and the perception evaporates.

**Recommended next step (not a fix yet).** Ask the user for a screenshot, then either:
- If they're in `TagEditorSheet`: replace the hardcoded `SUGGESTED_LABELS` with a backend-driven popular-tags endpoint (e.g., `GET /customers/tags/suggestions` returning top-N labels across all customers); ~half a day of work.
- If they're in a tag-filter elsewhere: the fix targets that component instead — schema is fine.

**Severity.** P3 until the surface is identified. The data model is healthy; this is a UI-discoverability bug, not a backend bug.

**Confidence: medium.** Strong on what the code does. Weak on which surface the user is reporting against.

---

### 15.3 Stale portal Approve/Reject buttons after approval — backend/frontend field-name mismatch (§13.1)

**Symptom.** Customer approves an estimate via the portal. The portal continues to render live Approve / Reject buttons on subsequent loads instead of locking out the action UI.

**Root cause — a one-character schema drift bug.** The backend returns the read-only flag as `readonly`. The frontend TypeScript type expects `is_readonly`. The render guard reads `estimate.is_readonly`, which is therefore always `undefined`, and `!undefined` is `true` — so the Approve/Reject block always renders.

**Evidence chain.**
- **Backend response schema:** `src/grins_platform/schemas/portal.py:75–78` — `readonly: bool = Field(default=False, description="Whether estimate is read-only (already approved)")`.
- **Frontend type definition:** `frontend/src/features/portal/types/index.ts:31` — `is_readonly: boolean;` (note the `is_` prefix that the backend never sends).
- **Render guard:** `frontend/src/features/portal/components/EstimateReview.tsx:279` — `{!estimate.is_readonly && (` opens the action block. With `is_readonly === undefined`, the guard evaluates truthy → buttons render.

**Why this slipped through.** TypeScript treats the missing field as `boolean` per the declared type without runtime validation (no Zod/io-ts guard on the API response). Local dev never tested an already-approved estimate render — the §13 live test was the first time anyone hit this path with a real APPROVED row in the DB.

**Recommended fix.** Single-line change: rename the field in `frontend/src/features/portal/types/index.ts:31` from `is_readonly: boolean` → `readonly: boolean`, then update the one reference at `EstimateReview.tsx:279` from `!estimate.is_readonly` → `!estimate.readonly`. (`readonly` is a TypeScript reserved-ish keyword in interface declarations but is permitted as a property name in object types; verify no lint rule complains, otherwise alias on parse.)

**Defense-in-depth additions worth considering:**
- Also gate the buttons on `estimate.status === 'approved' || estimate.status === 'rejected'` (which IS already in the response — `types/index.ts:20` has `status: string`). Two independent guards beat one.
- Add a Zod schema for the portal-estimate response so future field renames fail at parse time rather than silently mis-binding.

**Severity.** P2. A customer who approves, gets confused, refreshes, and approves again would hit a 422 from `EstimateAlreadyDecidedError` — embarrassing but not actually harmful. A customer who rejects after approving would hit the same. The real risk is a customer abandoning when they re-open the portal and think their approval didn't take.

**Confidence: high.** Three file:line citations, mechanism is deterministic.

---

### 15.4 Edit lead/customer name from Sales errors out — empty `last_name` violates `min_length=1` (Parked: "Editing a lead's name from the Sales entry returns an error")

**Symptom.** Admin opens the Sales entry, edits the customer's name, hits Save → red "Update failed" toast.

**Root cause.** The Sales-entry edit form splits a single name string on whitespace and submits the result. When the user types a single name with no space (e.g., correcting a typo to "John"), the split yields `firstName = "John"`, `lastName = ""`. The backend's `CustomerUpdate` Pydantic schema requires `last_name` to be either omitted (null) **or** a string of `min_length=1`. The empty string `""` matches neither, so Pydantic returns HTTP 422.

**Evidence chain.**
- **Frontend split + send:** `frontend/src/features/sales/components/SalesDetail.tsx:393–406`:
  ```ts
  const parts = customerInfoForm.customer_name.trim().split(/\s+/);
  const firstName = parts[0] || '';
  const lastName = parts.slice(1).join(' ') || '';
  await updateCustomer.mutateAsync({
    id: entry.customer_id,
    data: { first_name: firstName, last_name: lastName, phone: ... },
  });
  ```
  For input "John" → `parts = ["John"]` → `firstName = "John"`, `lastName = ""` (the `|| ''` makes the empty-array `.join('')` an empty string, explicitly).
- **Backend schema:** `src/grins_platform/schemas/customer.py:168–172` — `last_name: str | None = Field(default=None, min_length=1, max_length=100, ...)`. The `min_length=1` is the trap: it does NOT allow `""`. (`first_name` has the same constraint at lines 162–167, so a leading-whitespace input would fail symmetrically, but the common case is the no-space input failing on `last_name`.)
- **HTTP outcome:** 422 with body `{"detail": [{"type": "string_too_short", "loc": ["body", "last_name"], "msg": "String should have at least 1 character", "input": ""}]}`.
- **User-visible:** `SalesDetail.tsx:411` catches and renders `toast.error('Update failed', { description: getErrorMessage(err) })`. Whether the description shows the Pydantic msg depends on `getErrorMessage`'s parsing; in the worst case the admin sees just "Update failed" with no clue.

**Recommended fix.** Single-line change in `SalesDetail.tsx:398`: change `const lastName = parts.slice(1).join(' ') || '';` to `const lastName = parts.slice(1).join(' ') || null;` (and update the TypeScript type on the update payload if it currently insists on `string`). This sends `last_name: null` for single-word names, which the schema's `default=None` accepts.

**Edge case worth noting.** What does the *Customer* model itself permit? `src/grins_platform/models/customer.py:75–76` declares both `first_name` and `last_name` as `Mapped[str] = mapped_column(String(100), nullable=False)` — i.e., **non-null in the DB**. So sending `null` from the frontend would still fail if the Pydantic schema then tried to set the column to null. *But*: in a PATCH-style update, sending `null` for an optional field typically means "don't touch this column" rather than "set it to null." Verify the service layer's update logic (`src/grins_platform/services/customer_service.py:237` per the prior agent trace) honors that — if it doesn't, the cleanest fix is for the frontend to omit the field entirely when empty (`const data = { first_name: firstName, ...(lastName && { last_name: lastName }), phone: ... }`).

**Severity.** P2. Easy to hit in normal use (any typo correction on a one-word name), opaque error toast.

**Confidence: high.** Direct file:line evidence at both ends of the wire. The 422 response shape is a Pydantic standard.

---

### 15.5 Drag-and-drop PDF upload to Sales pipeline — `dragLeave` race on child elements (Parked: "Drag-and-drop PDF upload to sales pipeline doesn't work")

**Symptom.** Dragging a PDF onto the Sales pipeline area appears to "not work" — the drop zone visually flickers but the file never uploads, or the drop event never fires at all.

**Root cause.** The dropzone has `preventDefault()` on `onDragOver` (correctly enabling drop), but its `onDragLeave` handler unconditionally resets the over-state. When the dragged file's pointer moves over a *child* element of the dropzone (text, icon, inner div), the browser fires `dragleave` on the parent even though the pointer is still inside the dropzone region. That resets `setOver(false)`, which in some path also tears down the drop-receptive styling/state. The drop ultimately either fires on an unexpected target or doesn't fire at all because the pointer leaves the visually-active region.

**Evidence chain.** `frontend/src/features/sales/components/NowCard.tsx:220–230`:
```tsx
<div
  role="button"
  tabIndex={0}
  onClick={() => inputRef.current?.click()}
  onDragOver={(e) => { e.preventDefault(); setOver(true); }}
  onDragLeave={() => setOver(false)}
  onDrop={(e) => {
    e.preventDefault();
    setOver(false);
    handleFiles(e.dataTransfer.files);
  }}
  ...
>
  <div className="text-2xl ...">↓</div>
  <div className="text-sm ...">Drag the {label} here</div>
  <div className="text-xs ...">or <u>click to browse</u> · PDF only</div>
</div>
```
The three nested `<div>`s inside the dropzone are children of the drop target. Moving the dragged pointer across the parent→child boundary fires `dragleave` on the parent.

**Why click-to-browse works but drop doesn't.** The hidden `<input type="file" accept="application/pdf">` at lines 215–219 is a separate, fully-working code path: click → `inputRef.current?.click()` → native file picker → `onChange={handleFiles(...)}`. None of the drag/drop event machinery is exercised. So the user can use the upload feature *if they click*, which probably masked how broken the drop path is.

**Recommended fix.** Add an `onDragEnter` handler that mirrors `onDragOver`, and replace the naive `onDragLeave` with one that checks `e.currentTarget.contains(e.relatedTarget as Node)` and only sets `over=false` when the pointer has actually left the dropzone bounds. Minimal version:
```tsx
onDragEnter={(e) => { e.preventDefault(); setOver(true); }}
onDragOver={(e) => { e.preventDefault(); setOver(true); }}
onDragLeave={(e) => {
  if (!e.currentTarget.contains(e.relatedTarget as Node | null)) {
    setOver(false);
  }
}}
```

**Same pattern bug elsewhere.** Per the agent's parallel trace, `frontend/src/features/sales/components/MediaLibrary.tsx:126–128` has the identical handler shape and would benefit from the same fix.

**Severity.** P3. Click-to-browse works, so the feature is reachable; DnD is the discoverability/ergonomics layer that's broken.

**Confidence: medium-high.** Mechanism is well-known browser behavior. To conclusively confirm, drop a PDF on the live dropzone with browser DevTools' Event Listener panel open and watch the `dragleave`/`drop` sequence. The fix is so cheap it's worth shipping without that confirmation.

---

### 15.6 Lead → Sales transfer "missing phone, address, email" — address is genuinely absent; phone/email should be present (Parked)

**Symptom (user-reported).** When a Lead converts and shows up in the Sales pipeline, phone, address, and email are missing from the Sales detail view.

**Findings — split decision, not one bug.**

**(a) Address is *genuinely* missing — by data model.**
- `Lead` has address fields: `models/lead.py:144–146` — `city`, `state`, `address` (all nullable).
- `Customer` has **no address columns at all** — `models/customer.py:74–104` shows only name, phone, email, status flags, comms-prefs. No address/city/state/zip.
- Address lives on the `Property` model, joined via `SalesEntry.property_id`.
- `Lead → Customer` conversion (`lead_service.py:949 + 1148`) copies name/phone/email/consent. It does **not** create a `Property` row from the lead's address fields, nor does it copy the address anywhere else.
- The Sales detail response build (`api/v1/sales_pipeline.py:161–180`) constructs `property_address` from `entry.property.address|city|state|zip_code` (lines 170–172). If `entry.property_id` is null (which it is for a freshly-converted lead with no property yet), `property_address` is null.

**(b) Phone and email *should* be present per the conversion path.**
- `_entry_to_response` at `sales_pipeline.py:168, 175–176` sets `customer_phone = customer.phone if customer else None` and `customer_email = customer.email if customer else None`. The lead conversion at `lead_service.py:949` writes `customer.phone` and `customer.email` from the lead. So these fields should be populated end-to-end.

**(c) Possible explanations for the user's "phone/email missing" report.**
1. The user was looking at a SalesEntry created *directly* (not via lead conversion), where `customer.phone`/`customer.email` were never populated.
2. The frontend doesn't render `customer_phone` / `customer_email` even when present (would need to grep `SalesDetail.tsx` for those exact fields). Quick spot-check: per the agent's earlier note, `SalesDetail.tsx:532–540` references `entry.customer_phone` and `entry.customer_email` — so they're rendered.
3. The user may have been describing only the address gap and lumped phone/email in colloquially.

**Recommended fix.**
- **Primary (address):** Modify the Lead → Customer conversion (`lead_service.py:949 + neighbors`) to also create a `Property` row when the Lead has any of `address/city/state`, linking it to the new SalesEntry's `property_id`. Backfill existing converted leads via a one-time migration.
- **Secondary (phone/email):** Live-verify whether the user's specific Sales entry actually has empty `customer.phone` / `customer.email` in the DB. If yes, that's a *different* bug in either the conversion (lead-side fields were never filled) or a manual SalesEntry creation path. If no, this is reporter confusion — close as resolved.

**Severity.** P2 for the address gap (real user-facing data loss). P3-pending-investigation for the phone/email portion.

**Confidence: high on (a), medium on (b)/(c).** Customer model and conversion path were read directly. The "phone/email actually missing" claim from the user needs DB confirmation before pattern-matching it to any specific bug.

---

### 15.7 "10% off estimate sequence misfires" — resolved by commit d20a67c, with a narrow theoretical gap (Parked)

**Original bug.** Earlier in the project (pre-commit `4e87cf4` from mid-March), `EstimateService._schedule_follow_ups` auto-attached the promotion code `SAVE10` to Day 14+ follow-ups and `process_follow_ups` appended *"Use code SAVE10 for a discount!"* to those SMS bodies. The auto-discount practice was then removed from the codebase, but rows already queued in `estimate_follow_ups` with `promotion_code='SAVE10'` and `status='scheduled'` survived the code change and would still fire the discount message when their `scheduled_at` came due — misfiring the 10% off sequence against estimates that should not have received it.

**The d20a67c fix.** Commit `d20a67c chore(estimate-followups): clear queued promotion_code on scheduled follow-ups` pairs:
1. **A data migration** (`alembic/versions/20260511_120000_clear_estimate_followup_promotion_codes.py`) — `UPDATE estimate_follow_ups SET promotion_code = NULL WHERE status = 'scheduled' AND promotion_code IS NOT NULL;`. Wipes the queued SAVE10 rows. Doesn't touch already-SENT rows (preserves historical audit).
2. **Code changes** — `_schedule_follow_ups` (`estimate_service.py:1247–1268`) now passes `promotion_code=None` explicitly (line 1266 — verified in the live file). The processor's default reminder message at `process_follow_ups` (lines ~1072–1075) no longer appends the discount sentence.

**Status: fully resolved for the single-send flow.**

**Remaining theoretical gap.** If a re-send path is ever added later (e.g., a "resend this estimate fresh, scheduling a new follow-up sequence"), it would call `_schedule_follow_ups` correctly (with `promotion_code=None`) but would *not* cancel the prior estimate's queued rows. Today no such endpoint exists — `cancel_follow_ups_for_estimate` is invoked only on portal-approve (`estimate_service.py:464`), portal-reject (`:548`), and on the already-decided check inside the processor itself (`:1064`). If a future feature adds re-send-from-pending, it must explicitly `cancel_follow_ups_for_estimate` first, otherwise duplicate sequences will fire.

**Recommended action.** No code change required today. Re-verify with the user that the original "10% off misfires" report is no longer reproducible since `d20a67c` deployed; if they confirm, close. If they don't, the most likely residual is an estimate sent *before* the migration ran whose follow-up was already in flight (the migration only wipes `status='scheduled'`; rows that flipped to `SENT` before the deploy kept their SAVE10).

**Severity.** P3 (resolved-pending-confirmation). Not a P-ratable bug today.

**Confidence: high.** Migration SQL + code-change pair was read directly; the gap is well-bounded.

---

## 15.8 Summary table

| # | Bughunt | Root cause | Confidence | Recommended fix size |
|---|---|---|---|---|
| 15.1 | Lead photo upload 500 | Unwrapped `boto3.put_object` exception in `photo_service.py:331` | med-high | ~10 LOC try/except + map |
| 15.2 | "Integ tag" only option | Hardcoded `SUGGESTED_LABELS` in `TagEditorSheet.tsx`; the "Integ tag" row is an existing customer-tag entry; user's exact surface unconfirmed | medium | Half-day + screenshot first |
| 15.3 | Stale portal Approve/Reject | Field name mismatch: backend `readonly` vs frontend `is_readonly` | high | 1-line type rename |
| 15.4 | Edit name from Sales errors | Frontend sends `last_name: ""` for one-word names; schema requires `min_length=1` | high | 1-line frontend change |
| 15.5 | Sales DnD PDF upload | `onDragLeave` resets state on child-element exits; no `onDragEnter`; missing `relatedTarget` check | med-high | ~5-line handler rewrite (×2 sites) |
| 15.6 | Lead → Sales missing fields | Address: no Customer column, conversion doesn't create Property. Phone/email: should work — verify live | high (address) / medium (phone/email) | Conversion + migration for address |
| 15.7 | 10% off misfires | Already fixed by commit `d20a67c` (migration + code) | high | None — re-verify with user |

---

---

## Parked — implementation phase (NOT covered by this pass)

Every item from the user's original message that was *not* verified above. Order roughly follows the user's mental model (Leads → Sales → Estimate → Convert → Job → Schedule → Invoice → Cross-cutting). No priority is assigned — that's the next conversation.

Several items here have *partial answers* already in the verified sections above; the cross-reference notes which section to read.

### Staff / Auth
- **Add a "Text" button alongside the "Call" button** so techs can text the customer from the same surface. Backend SMS plumbing already exists (CallRail provider, `SMSService.send_message`); this is a frontend addition.

### Schedule Estimate Modal
- **Modal isn't scrollable — can't reach Submit.** Add overflow-y on the modal body wrapper or constrain the modal max-height so the inner form scrolls.
- **"Internal notes (optional)" field has no Save button.** Either auto-save on blur or add an explicit Save inside the notes section.

### Leads → Sales
- **Editing a lead's name from the Sales entry returns an error.** **Root cause identified in §15.4 below** — frontend sends `last_name: ""` for one-word names; `CustomerUpdate` schema requires `min_length=1` → 422.
- **Red highlight / notification counter doesn't clear** after a lead moves to Sales/Jobs. Suggested fix sits inside §5 Option B (admin notifications inbox + shared state for counters).
- **Lead → Sales transfer is missing phone, address, email** and other lead details. **Investigated in §15.6 below** — address is genuinely absent (Customer has no address columns; conversion never creates a Property from the lead's address fields). Phone/email *should* be present per the conversion path — needs live DB confirmation on the user's specific entry to rule out reporter conflation vs. a separate bug.
- **Drag-and-drop PDF upload to sales pipeline doesn't work.** **Root cause identified in §15.5 below** — `onDragLeave` resets state on child-element exits (no `relatedTarget` containment check), no `onDragEnter`; same bug pattern in `MediaLibrary.tsx`. `preventDefault` *is* present on `dragover` (the original hypothesis); the actual culprit is the leave-handler race.
- **Address autocomplete as you type.** Wire Google Places (or equivalent) into the address input on the lead + customer form.
- **Free-form tags (not just "Integ tag")** that propagate Sales → Jobs → Customers. Per §1, `CustomerTagService.save_tags` already accepts any label up to 32 chars — the limitation is in the frontend dropdown. Find the dropdown source and unblock it.
- **Gray "waiting for customer response" box** may be unnecessary post-Mark-Contacted. Product decision: remove the box or relabel it.

### Estimate Lifecycle (items not already covered in §2–§7, §10–§11)
- **Pause Auto Follow-up button needs a "Resume Auto Follow-up" label when paused.** §6 confirmed the backend toggle exists and the unpause endpoint fires; the issue is purely the button label not flipping.
- **10% off estimate sequence misfires.** **Investigated in §15.7 below** — resolved by commit `d20a67c` (migration clears queued `SAVE10` rows + code change passes `promotion_code=None` to new follow-ups). Needs re-verification only.

### SignWell / Convert to Job
- **Remove the "Kirill already signed via SignWell" gate.** Per the user's memory `project_signwell_not_used`, SignWell is scaffolded but not actually used; the gate is dead code path. Drop the conditional in `frontend/src/features/sales/lib/nowContent.ts:73–82` and let "Convert to Job" be the standard flow once a signed agreement PDF is uploaded.
- **Convert to Job with a signed agreement should be the standard flow**, not a forced SignWell step. Same change as above.

### Job Creation
- **Create-Job popup with full details** (description, job type, priority, staff required, duration, lead source, tags). Either modal or step-form. Today's auto-job-on-approval (`_maybe_auto_create_job` at `estimate_service.py:489`) creates a Job with sparse defaults — give the admin a confirm/edit step.
- **Remove the "Needs Estimate" job type** since uploaded PDF = estimate exists. Audit `JobType` enum, find any UI that exposes "needs estimate," remove.
- **Editable tags on the created job.** Per §1, no `JobTag` table exists today — needs schema addition OR plug into the customer-owned timeline proposal (§1 Option B).
- **Notes from sales entry flow into job description as one shared blob.** Per §1, this is the load-bearing data-model question; whatever you pick there determines this implementation.
- **Rename "Scope" → "Notes"** on the job detail surface. UI relabel.
- **Jobs only appear in tech view after full approval; admin-only before that.** Add a status filter to the tech-side job list to exclude jobs whose parent sales-entry status is not `closed_won` (or whatever your "fully approved" marker is).
- **Streamline Job search to match the top global search bar.** UX harmonization; probably one shared search component.

### Scheduling / Confirmations
- **Drag-and-drop between schedule areas must NOT auto-send.** Find the drag-drop handler on the schedule board, confirm it dispatches a send today, gate it on an explicit Send action instead.
- **Status should NOT flip to "Scheduled" until customer Y.** Covered in §8.3 as a label/semantics decision; the recommendation there (UI-only relabel to "Awaiting confirmation") is the smallest fix.
- **After confirmation, On-My-Way / Job-Start / Job-Complete actions should appear.** Covered in §9 — they DO appear once `appointment.status === 'confirmed'`. The fix is the "Awaiting customer Y" placeholder so the gating is visible.
- **Daily schedule builder should use the slide/drop UX from the estimate view.** Larger UX project — copy the calendar interaction pattern from the estimate visit booking surface into the daily schedule.

### Notes / Photos / Tags (cross-cutting)
- **Notes interconnected across Leads, Sales, Jobs, Appointments.** Covered by §1; resolved once one of the three design options is picked.
- **Photos attached to the customer; notes attached to the customer.** Same — §1 Option B (customer-owned timeline) directly solves this.
- **Lead photo upload throws a 500** (user reported this as already resolved per their earlier message — keep parked here as a sanity-check item: verify the fix once the §1 unification work lands so the upload path doesn't regress).

### Invoices / Payments
- **Invoices interconnected with Stripe** — on payment, Invoices tab shows customer, job, date, full Stripe detail. Likely needs a `payment_event_id` FK from Invoice to a `stripe_event` ingest table + a Stripe webhook handler that fans out to the invoice surface. Confirm whether the existing `services/stripe_payment_link_service.py` already writes the linking row.

### Reviews / Messaging copy
- **Narrow down exact copy of all SMS + email templates.** Build the template catalog (`docs/messaging-catalog.md` already exists per the working tree — extend it).
- **"Thanks for considering Grin's Irrigation" → "Thank you for considering Grin's Irrigation."** Find the exact string in templates; one-line text fix.

### Other audit / verification gaps surfaced during this pass (not in the original message but worth tracking)
- **Stale-portal bug** discovered in §13.1, root-caused in §15.3: frontend type expects `is_readonly` but backend sends `readonly` — one-line type rename fixes it (plus defense-in-depth gate on `estimate.status`).
- **Email send paths bypass the suppression list** (§7.2). P1 compliance fix.
- **`List-Unsubscribe` RFC 8058 header missing** on Resend payloads (§7.2). Bulk-sender deliverability risk.
- **Estimate follow-ups are SMS-only** (§6, §10). Customers without SMS consent silently never get nudged.
- **`SentMessage` is SMS-only — no equivalent `SentEmail` table** (§12). No local email audit trail.
- **No in-app admin notifications surface** (§5). Approvals are only delivered as text/email.
- **Two on-the-way hook paths** (`useOnMyWay` on job, `useMarkAppointmentEnRoute` on appointment) — pick one (§9).
- **Customer-vs-job dedup scope for Send Review Request** — current is 30-day customer dedup, user likely wants per-job (§11).

---

## Severity rollup

P1 items (compliance / customer-visible failures):
- §2 Resend Estimate button — fix advance-on-approval, also resolves "Approval → Contract auto-advance" complaint
- §3 Missing send-confirmation chain after reschedule queue resolution
- §7 Email send paths don't honour suppression list (compliance)
- §7 Missing `List-Unsubscribe` header (deliverability)
- §10 SMS-only estimate follow-ups (customers without SMS dropped)

P2 items (operational / UX with workarounds):
- §4 Audit `INTERNAL_NOTIFICATION_EMAIL`/`_PHONE` on prod
- §5 Build admin notifications inbox (Option B)
- §6 SMS-only follow-ups (also P1 above)
- §7 Cancel scheduled nudges on opt-out
- §8 Pass preferred-time to confirmation body
- §8 Relabel "Scheduled" → "Awaiting confirmation"
- §9 "Awaiting customer Y" placeholder for staff workflow buttons
- §12 Build `sent_emails` table + Email Log view
- §13 Sticky Approve/Reject CTA on mobile + lock-out post-decision
- §14 Admin form to set staff username + password (Option A)
- §15.1 Wrap boto exceptions in lead-attachment upload (also surfaces transient S3 errors)
- §15.3 Rename frontend portal type `is_readonly` → `readonly`; add status defense-in-depth
- §15.4 Frontend: send `last_name: null` (or omit) instead of `""` for one-word names
- §15.6 Lead→Customer conversion must also create a Property row from lead's address fields

P3 items (nice-to-have / documentation):
- §4 Startup warning on missing internal-notify env
- §6 `/dev/follow-ups/trigger` endpoint + Railway-visible counts
- §9 Pick one on-the-way hook path
- §11 Decide customer-vs-job dedup
- §12 Document `noreply@` mailbox status
- §15.2 Replace hardcoded `SUGGESTED_LABELS` with backend-driven popular-tags (after screenshot confirms surface)
- §15.5 Fix `onDragLeave` race in `NowCard.tsx` and `MediaLibrary.tsx`
- §15.7 Re-verify "10% off misfires" is no longer reproducible post-`d20a67c`

---

_End of Part 1 (verification pass)._

---

## Part 2 — Parked-List Clarifications & Implementation Plans

Companion to Part 1 above. Each cluster below captures: (a) what was clarified in this conversation, (b) the locked scope, (c) the implementation outline (files to touch, test approach) — **not code, no PRs opened yet**.

Clusters are filled in as the user picks them. Order so far:

1. **P1 verified bugs** — Approve auto-advance, email suppression bypass (this round)
2. _(future clusters appended below as picked)_


## Cluster 1 — P1 verified bugs

### 1.1 Estimate auto-advance on portal approve + Resend-button defense + SignWell webhook removal

**Origin.** Verification-pass §2. User reports "Resend Estimate button does not work" — root cause was that portal approve doesn't advance the SalesEntry, so the Resend lookup (which filters on SENT/VIEWED) 404s when the estimate is already APPROVED. Same root cause also leaves the pipeline stuck in `pending_approval` after the customer approved (user's separate "On client approval, stage should auto-advance Approval → Contract" complaint).

**Locked scope (decided in this round):**

| Decision | Choice | Rationale |
|---|---|---|
| Bundle Resend-button hide? | **Yes** — bundle frontend guard | Belt + suspenders; cheap to add at the same time |
| Handle SignWell webhook race? | **Remove SignWell webhook advance entirely** | Per `project_signwell_not_used` memory — single canonical path |
| Auto-advance on REJECT too? | **No** — keep reject manual | Admin reviews rejections, decides next action |

**Files to touch (backend):**

- `src/grins_platform/services/estimate_service.py` — `approve_via_portal` (line 412). After `_correlate_to_sales_entry`, call a new helper `_advance_sales_entry_on_approval(estimate)` that:
  - Resolves the active SalesEntry via existing `_resolve_active_sales_entry_for_estimate` (or extend `record_estimate_decision_breadcrumb` to return the resolved entry so we don't re-query).
  - Guards: if `entry.status != PENDING_APPROVAL`, log `sales.estimate_advance.skipped` and return (idempotency — covers the case where SignWell already advanced or admin manually moved it).
  - Sets `entry.status = SEND_CONTRACT`, updates `updated_at`, flushes.
  - Audit row via `AuditService.log_action("sales_entry.auto_advance_on_approval", ...)`.
- `src/grins_platform/services/sales_pipeline_service.py` — extend `record_estimate_decision_breadcrumb` to return the resolved entry (currently returns the entry but only as the breadcrumb side-effect). Alternative: add a separate `advance_on_approval(db, sales_entry_id)` method on the service.
- `src/grins_platform/api/v1/signwell_webhooks.py:179` — **delete the auto-advance block** (the comment "6. Advance sales entry status: pending_approval → send_contract"). SignWell webhook becomes a pure no-op for the advance side. Log a warning that the codepath is deprecated.

**Files to touch (frontend):**

- `frontend/src/features/sales/lib/nowContent.ts:62–66` — `pending_approval` actions list. Replace the always-rendered `act('outline', 'Resend estimate', ...)` with conditional rendering: when `latestEstimate?.status` is `APPROVED` or `REJECTED`, drop the action. Probably means threading `latest_estimate_status` into the entry object surfaced to the now-content composer.
- `frontend/src/features/sales/types/pipeline.ts` — add `latest_estimate_status` field to the `SalesEntryDetail` (or equivalent) interface.
- Backend response: extend `SalesEntryResponse` (or the detail variant) to include the latest estimate's status. Currently the entry detail doesn't surface this; need to add it via the existing entry → estimate join in the API layer.

**Tests:**

- New unit test: `test_approve_via_portal_advances_sales_entry` — call `approve_via_portal` against a fixture SalesEntry in PENDING_APPROVAL, assert it's now SEND_CONTRACT.
- New unit test: `test_approve_via_portal_idempotent_when_already_advanced` — set entry to SEND_CONTRACT first, call approve, assert no state change + skip log emitted.
- Update existing `test_signwell_webhooks.test_document_signed_advances_when_pending_approval` — the auto-advance is gone; test should now assert NO status change happens from the webhook (and possibly assert deprecation warning is logged).
- Frontend: update `SalesDetail.test.tsx:457` to cover the case where Resend action is hidden when `latest_estimate_status='APPROVED'`.

**Manual verification (post-deploy to dev):**

1. Seed a customer + estimate, send via portal flow (status SENT).
2. Approve via portal (POST /api/v1/portal/estimates/{token}/approve).
3. Refetch SalesEntry: status should be SEND_CONTRACT.
4. Visit the sales detail UI: confirm the "Resend estimate" action is absent.
5. Repeat with reject — confirm status stays in PENDING_APPROVAL (no auto-advance on reject).

**Open questions remaining:** none. Ready for implementation.

---

### 1.2 Email suppression list — wire `_send_email` to honour it

**Origin.** Verification-pass §7. User-facing unsubscribe endpoint writes to `EmailSuppressionList`, but `EmailService._send_email` never reads from it. Customers who unsubscribe keep getting emails. Compliance bug.

**Locked scope (decided in this round):**

| Decision | Choice | Rationale |
|---|---|---|
| Hard-guard behaviour | **Silent deny + structured log** | Matches SMS `check_sms_consent` pattern. Callers don't need to change. |
| Internal/admin notifications | **Bypass via `bypass_suppression=True` param** | Victor's approval-notification emails still fire even if his address ever got suppressed |
| `customer.email_opt_in=False` also block? | **No — suppression list only** | One canonical source of truth; opt_in flag is treated as legacy soft signal |
| Apply to all classifications? | **Yes, both transactional and commercial unless bypassed** | Suppression is a hard opt-out; legal carve-outs for transactional belong on the caller side via `bypass_suppression`, not on the central guard |

**Files to touch:**

- `src/grins_platform/services/email_service.py`:
  - Add a private helper `_is_recipient_suppressed(email: str) -> bool` that queries `EmailSuppressionList` by lowercased email. Synchronous against the existing `self.session` (note: `_send_email` is sync today; if it needs a session it'll need to be reworked or use a sync DB call — verify).
  - Extend `_send_email` signature with `bypass_suppression: bool = False` (default False).
  - At the top of `_send_email` (after the `is_configured` check, before the allowlist enforcement at line 307), insert:
    ```python
    if not bypass_suppression and self._is_recipient_suppressed(to_email):
        self.logger.info(
            "email.send.suppressed",
            recipient=_mask_email(to_email),
            email_type=email_type,
            reason="suppression_list",
        )
        return False
    ```
  - Update `_notify_internal_decision` (`estimate_service.py:609`) and `api/v1/resend_webhooks.py:134` (internal notification on bounce) callers to pass `bypass_suppression=True` when calling `send_internal_estimate_decision_email` (or whichever internal-notification path is exposed on `EmailService`).
  - Audit every `EmailService.send_*` caller to confirm whether it's customer-facing (no bypass) or internal-facing (bypass). Specifically check: `send_estimate_email`, `send_welcome_email`, `send_renewal_notice`, `send_invoice_email`, `send_signed_estimate_pdf_email`, all internal-* methods.

- **Session access concern:** `EmailService._send_email` is currently fully sync. The suppression check requires a DB query, which means either:
  - Add an async wrapper `_send_email_async` and migrate callers, OR
  - Pre-fetch the suppression set once per request and pass it in (matches the existing `check_suppression_and_opt_in` helper signature at line 1097 which already accepts `suppressed_emails: set[str]`).

  The pre-fetch approach is simpler — at the top of each send-driving method (e.g., `send_estimate_email`), fetch the suppression status for the one recipient via the session and pass into `_send_email`. Avoids the async migration.

  **Recommended implementation path:** change `_send_email` to accept `is_suppressed: bool = False` (caller pre-checks). Add a single helper on `EmailService` `async def is_suppressed(email)` that callers invoke. Async stays async; sync `_send_email` stays sync.

**Tests:**

- Unit: `test_send_email_denies_when_suppressed` — insert a suppression row, attempt send, assert `_send_email` returns False and `email.send.suppressed` is logged.
- Unit: `test_send_email_sends_when_bypass_true` — same setup, pass `bypass_suppression=True`, assert send proceeds.
- Unit: `test_notify_internal_decision_bypasses_suppression` — suppress the `INTERNAL_NOTIFICATION_EMAIL`, fire approval notification, assert email still sends (proves the bypass wiring works end-to-end).
- Update `test_email_unsubscribe.py` (if exists) or add new test: full round-trip — POST `/api/v1/email/unsubscribe?token=...`, then attempt `send_estimate_email` to that recipient, assert it's blocked.

**Manual verification (post-deploy to dev):**

1. Generate an unsubscribe token for `kirillrakitinsecond@gmail.com` (via the existing token generator).
2. Hit `/api/v1/email/unsubscribe?token=…` to add the address to the suppression list.
3. Trigger `send_estimate_email` to that customer (via the resend-estimate flow or direct API).
4. Verify Resend dashboard shows NO new send for that recipient.
5. Verify Railway logs show `email.send.suppressed` at the time of attempt.
6. Trigger `_notify_internal_decision` (approve an estimate). Verify the admin notification DOES land in the inbox (proving bypass works).

**Open questions remaining:** none. Ready for implementation.

---

## Cross-cluster notes

- **Both items target backend + frontend.** §1.1 needs schema response extension; §1.2 is pure service-layer + caller audit.
- **Suggested PR order:** §1.2 first (no schema work, low risk, big compliance win), then §1.1 (touches more files, has the frontend coupling).
- **Implementation policy reminder:** per the user's choice in this round, **plan only — no code yet**. These plans are ready to hand to the implementation phase when greenlit.

---

## Remaining items still to clarify

Checklist of every parked item that has not yet had its scope locked. Grouped by cluster, in the order suggested for tackling them. Each item lists *what needs deciding* so future rounds can be sized accurately. Items in the verification pass that already have locked recommendations (and just need implementation plans, not more decisions) are tagged `[plan-ready]`.

### Deferred from this round (P1 cluster spillover)

- [ ] **§3 Reschedule queue: missing auto-send-confirmation chain** — explicitly skipped after we determined the manual button still works; revisit when the queue UX gets attention.
- [ ] **§8.2 Customer's preferred time in confirmation body** — bundled with §3; skipped together.
- [ ] **§8.4 Promote soft-error to toast** in `useScheduleVisit.submit` — bundled with §3.
- [ ] **§7 `List-Unsubscribe` header** — header-only (GET) vs header + one-click POST (RFC 8058); apply to commercial vs all classifications.
- [ ] **§10 Estimate follow-ups: add email branch** — channel strategy (parallel / fallback / per-step) explicitly skipped this round.

### Cluster A — Notes / Photos / Tags unification (data model)

Highest leverage; unblocks ~8 parked items downstream. The `project_unified_notes_rollback_reason` memory ("user wants one shared editable blob, no per-entry author/timestamp chrome") locks the design philosophy: not a timeline of entries, but a **single editable text blob per customer** that surfaces on every screen.

**User clarifications captured 2026-05-13:**

- [ ] **Notes design shape — customer-owned blob, surfaces everywhere** — **Decision (user, 2026-05-13):** **single shared blob on `customer.notes`** is the canonical source. Renders editably on **lead detail** (post-conversion lead links to customer), **customer detail**, **sales entry**, **job detail**, AND **appointment modal** — every surface shows the same field. Editing on any surface mutates the same row. Per the rollback-reason memory, **no per-entry author/timestamp chrome** in the UI (last-write-wins; see audit decision below). **Implementation implications:**
  - **`SalesEntry.notes` → absorbed into `customer.notes`.** No separate sales-entry notes column going forward; the sales-entry surface reads/writes `customer.notes`.
  - **`Job.notes` → absorbed into `customer.notes`.** Same pattern. Job-detail's notes panel binds to `customer.notes`.
  - **`Appointment.notes` legacy column** — keep the column physically but rewire reads/writes through `customer.notes` (so the appointment modal edits the shared blob). The `appointment_notes` table cleanup below still happens.
  - **Pre-conversion `lead.notes`** stays on the lead model (no customer exists yet); on Lead→Customer conversion, `lead.notes` is **carried forward into `customer.notes` with the divider** that already exists at `lead_service.py:1170`.
- [ ] **Tag inheritance — shared single set, read-write from every surface** — **Decision (user, 2026-05-13):** all tags physically live on the **customer** record. **Every surface (lead post-conversion, customer, job, appointment) can read AND write the same set.** Adding a tag from a Job surface writes to the customer's tags; adding a tag from an Appointment surface writes to the customer's tags; etc. All other surfaces showing that customer immediately see the new tag. **Practical implementation:**
  - Single `customer_tags` table (already exists at `models/customer_tag.py`); no `JobTag` / `AppointmentTag` tables.
  - Job and Appointment API responses denormalize the customer's tags into the response payload so the UI can render them without an extra fetch.
  - Tag-add mutations from a Job/Appointment surface POST to the customer-tag endpoint with the customer_id resolved from the job/appointment.
  - **Pre-conversion lead tags** stay on the lead (no customer yet); cascade to customer-tags on conversion per the intake-tag decision below.
- [ ] **Tag picker UI** — **Locked 2026-05-12 (Cluster A explicit requirement).** Combobox with autocomplete from existing tags + inline creation when the typed value doesn't match. Replaces today's "Integ tag"-only dropdown wherever tags appear (lead, customer, sales entry, job, appointment). This is the canonical fix for the "Integ tag" item below.
- [ ] **Lead-photo cascade on Lead→Customer conversion** — **Decision (user, 2026-05-13):** **cascade: move `LeadAttachment` rows to `CustomerPhoto` on conversion.** Lead row stays for audit; photos now "live" on the customer. No duplication. **Implementation:** during `move_to_sales` / `convert_to_customer` in `LeadService`, re-insert or re-point each LeadAttachment as a CustomerPhoto row keyed to the new customer_id. Preserve `created_at`, mime type, S3 key, etc. Mark the LeadAttachment row as "migrated" or delete it (TBD during planning).
- [ ] **Photo upload context during an appointment** — **Decision (user, 2026-05-13):** **`CustomerPhoto` with optional `appointment_id` FK.** Single table; photo lives on the customer (visible from every customer surface), but the optional FK lets the appointment modal filter to "photos from this visit." Drop any plans for a separate `AppointmentAttachment` table.
- [ ] **`lead.intake_tag` + lead action_tags cascade on conversion** — **Decision (user, 2026-05-13):** **cascade both** to `customer_tags` on Lead→Customer conversion. Filter out **already-resolved action tags** before cascade (e.g., `Estimate Approved`, `Estimate Rejected` — workflow markers that are no longer actionable post-conversion). Active markers (`Needs Estimate` if estimate not yet sent, etc.) and the manually-set `intake_tag` carry over. Symmetric with the photo cascade. **Implementation:** during conversion, build a filtered tag list from `lead.intake_tag` + `lead.action_tags` (excluding completed-state tags) → upsert into `customer_tags`.
- [ ] **Audit / versioning policy** — **Decision (user, 2026-05-13):** **None — last-write-wins** for v1. Matches the rollback memory ("no per-entry author/timestamp chrome"). No edit history stored for notes / tags / photos. Trade-off accepted: if someone wipes important notes, they're gone. Revisit if loss becomes a recurring problem.
- [ ] **`appointment_notes` table drop** — Locked 2026-05-12 (see §1.9 #2). Drop the table + model/service/repo/schemas/API/4 test files in the same change that rewires the appointment notes panel onto `customer.notes`.
- [ ] **"Integ tag"-only dropdown** — **Subsumed by the Tag Picker UI requirement above.** Once the new picker ships, the "Integ tag" dropdown is replaced everywhere. No separate fix needed.
- [ ] **Lead-photo upload 500 — root cause identified (2026-05-13)** — **High confidence.** `PhotoService.upload_file` at `services/photo_service.py:331–336` makes an unwrapped `boto3.put_object` call. Any S3-side failure (`ClientError`, `EndpointConnectionError`, `NoCredentialsError`, `ReadTimeoutError`, throttling) propagates uncaught → FastAPI returns a generic 500. The endpoint at `api/v1/leads.py:744–761` only catches `ValueError` (size) and `TypeError` (MIME); no catch-all for boto failures. **Fix:** wrap the `put_object` call in a try/except, log the underlying exception with full context, and raise a typed `S3UploadError` (or similar) that the endpoint maps to **HTTP 502 / 503** instead of 500. Same gap exists in the customer-photo endpoint (`api/v1/customers.py:1309–1336`) — fix both paths together since `PhotoService.upload_file` is shared. Matches §15.1 of this verification doc.

**Cluster A — all decisions captured 2026-05-13. No remaining open questions.** Ready for implementation planning.

**Suggested execution order for Cluster A** (no commitment, just sequencing):
1. **Schema migration**: add `customer.notes` (or repurpose existing column), ensure `customer_tags` covers all tag-add surfaces, add `appointment_id` FK to `customer_photos`. Drop `appointment_notes` table.
2. **Service layer**: rewire `SalesEntryService` / `JobService` / `AppointmentService` notes paths to read/write through `customer.notes`. Rewire tag-add paths from Job/Appointment to the customer-tag endpoint. Update Lead→Customer conversion to cascade attachments + tags.
3. **API layer**: denormalize tags into Job and Appointment response payloads. Update lead-photo + customer-photo endpoints to map S3 errors to 502/503.
4. **Frontend**: build the new tag picker component (autocomplete + inline create); wire it into every tag surface. Wire the customer-notes textarea into every notes surface (lead detail, sales entry, job detail, appointment modal).
5. **Cleanup**: drop the `appointment_notes` table + model/service/repo/schemas/API/tests.
6. **Verify**: run end-to-end Lead→Customer conversion; confirm tags, notes, and photos all carry over and surface correctly on every screen.

### Cluster B — Sales Pipeline UX (Leads → Sales + Schedule modal)

Most user-facing pain, smallest items.

**User clarifications captured 2026-05-12:**

- [ ] **Lead name edit error in Sales entry** — Root cause already identified in §15.4: frontend sends `last_name: ""` for one-word names; `CustomerUpdate` schema rejects with 422. **Decision (user, 2026-05-12):** fix at the schema by allowing empty `last_name` (loosen `min_length=1` constraint on `CustomerUpdate.last_name`). `[plan-ready]`.
- [ ] **Red highlight / notification counter doesn't clear** when lead moves to Sales/Jobs. **Decision (user, 2026-05-12):** standalone fix now, do not wait for §5 inbox. **Semantics:** counter must *decrement by the moved lead's contribution*, not reset to zero. Example: 3 unread leads → move 1 → badge shows 2. Existing clear paths (opening/reading a lead) keep working unchanged.
- [ ] **Lead → Sales transfer missing phone / address / email** in the detail view. **Investigation (2026-05-12):** verified the conversion path end-to-end:
  - **Phone & email:** transferred correctly (lead_service.py:1238–1239 → `Customer.phone` / `Customer.email`; surfaced in `SalesEntryResponse.customer_phone` / `customer_email` at sales_pipeline.py:168,176; rendered conditionally at `frontend/.../SalesDetail.tsx:532–536`).
  - **Address:** intentionally moved to the `Property` model, not `Customer` (Customer has no address columns). `move_to_sales` calls `ensure_property_for_lead` (lead_service.py:1406–1410) which parses lead.address and creates/links a Property. If `property_address` shows blank in the UI, either the lead had no address or `ensure_property_for_lead` was guarded out (property_service.py:506–512).
  - **Genuine data losses still on conversion (separate items):** LeadAttachment photos, `intake_tag`, `action_tags` JSON, all 5 UTM fields, `source_detail`, `page_url`, `customer_type`, `property_type`, `email_marketing_consent`, `consent_timestamp`.
  - **Action:** if the user still sees missing phone/email on a specific lead's Sales entry, capture the lead id + Customer row state for live DB verification (likely a manual-entry SalesEntry, not a lead-conversion case).
- [ ] **Drag-and-drop PDF upload broken** — Root cause already identified in §15.5: `onDragLeave` in `MediaLibrary.tsx` resets state on child-element exits (no `relatedTarget` containment check), no `onDragEnter`. **Decision (user, 2026-05-12):** proceed with the recommended fix (add `relatedTarget` containment check + `onDragEnter`). `[plan-ready]`.
- [ ] **Address autocomplete** — **Decision (user, 2026-05-12):** use **Mapbox** (cheapest at expected volume: free up to ~100k requests/month, then ~$0.75 per 1k; vs Google Places at ~$17 per 1k after $200/mo credit). Apply to the address input on the lead form and the customer/sales address input.
- [ ] **Free-form tags propagation** — Backend already accepts any ≤32-char label (per §1); frontend dropdown is the only block. **Decision (user, 2026-05-12):** **defer to Cluster A.** Do not ship a frontend-only quick fix; the proper tag picker (autocomplete existing + inline new-tag creation) will land as part of Cluster A's tag-picker requirement and replace today's "Integ tag"-only dropdown in one coordinated change.
- [ ] **Gray "waiting for customer response" box** — **Source:** this item came from the user's own feedback message, not the `instructions/` diagrams or `update2_instructions.md`. It refers to a real UI element on the sales pipeline page (likely tied to the "Contacted (Awaiting Response)" status label per `instructions/update2_instructions.md:512`). **Decision (user, 2026-05-12):** **deferred — ignored for now.** Do not investigate or change until the user re-raises it. Leaving the item parked here so it isn't lost.
- [ ] **Schedule estimate modal isn't scrollable** — **Clarification (user, 2026-05-12):** this is the modal that opens when scheduling from the **sales pipeline** (Schedule-Estimate flow), distinct from the reschedule dialog tracked in `.agents/plans/reschedule-dialog-scrollable-body.md`. CSS-only fix on the sales-pipeline schedule modal body wrapper (constrain max-height + `overflow-y: auto`).
- [ ] **"Internal notes (optional)" missing Save button** — **Decision (user, 2026-05-12):** auto-save on blur (field saves silently when it loses focus — no Save button needed). Matches the single-blob notes model from Cluster A.
- [ ] **Pause Nudges → Resume Auto Follow-up button label flip** — `[plan-ready]` per §6, just a button-text conditional.

### Cluster C — Job Creation + SignWell removal

**User clarifications captured 2026-05-12:**

- [x] **Create-Job popup design** — **Decision (user, 2026-05-12):** **single modal** (one scrollable modal with all fields visible at once; not a multi-step wizard, not a full-page form). **Field set + pre-fill behavior locked 2026-05-12:**
  - **Fields (in order):**
    - `Customer` — readonly, pre-filled from sales-entry's customer.
    - `Property` — picker, pre-selected from customer's primary property (admin can change).
    - `Job type` — select, **required**.
    - `Description` — textarea, pre-filled from sales-entry notes.
    - `Priority` — Normal / High / Urgent, default **Normal**.
    - `Duration` — minutes (estimated).
    - `Staffing` — count, default **1**.
    - `Target week` — date picker styled "Week of M/D".
    - `Lead source` — readonly, inherited from customer.
    - `Tags` — Cluster A placeholder, **disabled** until Cluster A's tag picker lands.
  - **Pre-fill policy:** **aggressive pre-fill.** Description from sales-entry notes; job type inferred from sales-entry `job_type` / `situation`; lead source inherited from customer; property pre-selected from customer's primary property; priority defaults Normal; staffing defaults 1. **Admin can override any field.** No "prefilled" visual marker per field (kept the UI clean).
  - **Excluded from this modal (deferred / handled elsewhere):** weather_sensitive, equipment_required, materials_required, quoted_amount, summary, category (auto-derived). These remain editable on the job-detail page post-creation.
  - **Mapping to `Job` columns** (`models/job.py`): all selected fields map 1:1 to existing columns — no schema changes needed. `customer_id`, `property_id`, `job_type`, `description`, `priority_level` (0/1/2), `estimated_duration_minutes`, `staffing_required`, `target_start_date`/`target_end_date` (Monday of target week → Sunday), `source`. `Job.category` is auto-derived server-side.
- [x] **"Needs Estimate" badge stuck on Job after sales flow completes** — **Reframe #2 (user, 2026-05-12):** the badge the user is seeing on the **admin Job detail page in the Jobs tab** is **NOT** an action tag from the leads system. It is the **"Estimate Needed" badge at `frontend/src/features/jobs/components/JobDetail.tsx:155–162`**, which renders whenever `job.category === 'requires_estimate'`. The render is driven by the `Job.category` column (`models/job.py:138`, `JobCategory` enum).
  - **Confirmed by code trace (2026-05-12):** the admin Job detail does **not** read `action_tags` from `Lead` or `Customer`. The `JobResponse` schema (`schemas/job.py:285–442`) has no `action_tags` field. The "Needs Estimate" rendering path is exclusively the category-driven badge.
  - **Root cause (to verify):** `SalesPipelineService.convert_to_job` (`sales_pipeline_service.py:410`) and/or `EstimateService._maybe_auto_create_job` (`estimate_service.py:489`) is creating the Job with `category = 'requires_estimate'` even when the sales-pipeline path has already produced a signed/approved estimate. By definition, a job spawned from a completed sales-pipeline conversion no longer needs an estimate — the category should be `ready_to_schedule` at creation time.
  - **Fix location:** the Job-creation paths from the sales pipeline (`convert_to_job` and any auto-create-from-approval helpers) must set `category = JobCategory.READY_TO_SCHEDULE` instead of `REQUIRES_ESTIMATE`. No frontend change needed — the badge will naturally disappear once `job.category` is correct.
  - **Action tag side note:** the lead's `action_tags` (`lead.py:149`) may also still contain `NEEDS_ESTIMATE` post-conversion (separate gap), but that's irrelevant to *this* surface; clean-up of lead action tags is its own item (still applies if a Leads-tab row shows stale tags). For Cluster C, only the Job-detail badge fix is in scope.
- [ ] **Editable tags on job** — depends on Cluster A's tag picker requirement (see Cluster A bullet). Deferred to Cluster A.
- [ ] **Notes shared blob in job description** — depends on Cluster A's unified-notes model. Deferred to Cluster A.
- [x] **Rename "Scope" → "Notes"** on job detail — **Decision (user, 2026-05-12):** **UI label only.** Keep `Job.scope` column name; no DB migration, no API/schema break. `[plan-ready]`.
- [x] **Jobs only in tech view after schedule confirmation** — **Reframe (user, 2026-05-12):** "approved" here does **not** mean estimate-approved or `closed_won`. It means **the appointment for that job has been confirmed by the customer for a specific time slot** (`Appointment.status = CONFIRMED`, set after the customer replies "Y" to the confirmation SMS — see `instructions/update2_instructions.md:466–475`). **Investigation (2026-05-12):**
  - Tech-mobile schedule endpoint: `GET /api/v1/appointments/staff/{staff_id}/daily/{schedule_date}` at `appointments.py:308`.
  - Backend repository query at `appointment_repository.py:394` does **not** filter by status today; returns all appointments for the staff member on the date.
  - Frontend `deriveCardState()` at `frontend/src/features/tech-mobile/utils/cardState.ts:5` filters only `cancelled` / `no_show` — bypassable client-side filter.
  - **Right fix location:** add a backend filter `Appointment.status == AppointmentStatus.CONFIRMED.value` to the staff-daily query.
  - **Decision (user, 2026-05-12) — multi-appointment case:** show in tech view if **ANY** appointment for the job is CONFIRMED. (Per-appointment filter naturally satisfies this since tech view is appointment-keyed: only CONFIRMED appointments render; jobs with unconfirmed appointments simply don't surface on those slots.)
  - **Decision (user, 2026-05-12) — reschedule case:** **hide again until re-confirmed.** If a CONFIRMED appointment is rescheduled and drops back to SCHEDULED (awaiting new customer Y), it disappears from the tech view until the customer re-confirms. Strict status-driven visibility — no stickiness.
- [x] **Job search streamlining** — **Decision (user, 2026-05-12):** **reuse the global search component**, scoped to jobs. UX parity with the top-bar search, lowest implementation effort. No job-specific custom search.
- [x] **Remove SignWell "Kirill already signed via SignWell" gate** — `[plan-ready]` per parked list; per `project_signwell_not_used` memory, drop the conditional at `frontend/src/features/sales/lib/nowContent.ts:73–82`.
- [x] **SignWell — surgical interference-only removal (Decision, user 2026-05-12)** — **Do NOT fully rip out SignWell.** Rationale: it may be re-used or repurposed in the future (e.g., for a future e-sign vendor). Strategy: remove only the parts that **actively interfere** with the current portal-Approve flow; leave the dormant scaffolding in place. **Specific changes:**
  - **REMOVE (interference) ✂️:**
    - Webhook auto-advance `pending_approval → send_contract` in `api/v1/signwell_webhooks.py` — competes with portal-Approve as the canonical advance path. Either delete the route or short-circuit the handler.
    - `signwell_document_id` signature gate on `convert_to_job` at `sales_pipeline_service.py:439–440` — replace with a "signed agreement PDF uploaded to Documents" check (or simply drop the gate and rely on admin discretion). Without this change, "Convert to Job" still demands a SignWell doc id.
    - `frontend/src/features/sales/lib/nowContent.ts:73–82` — the "Kirill already signed via SignWell" conditional. Drop the copy.
    - `SignWellEmbeddedSigner` iframe rendered at `SalesDetail.tsx:649` — remove the render (or gate it behind a feature flag that's off). User isn't using it; it's visible at `send_contract` stage and creates confusion.
  - **KEEP (dormant, no interference) 💤:**
    - `services/signwell/config.py`, `services/signwell/client.py`, `services/signwell/__init__.py` — service-layer scaffolding. Unimported by active paths after the above removals.
    - `SalesEntry.signwell_document_id` column + migration — keep the column so historical rows aren't lost and a future e-sign integration can reuse the field.
    - Exception handlers in `app.py:67–70, 739–810` — harmless when no SignWell code path fires.
    - `.env.example:94–98` env vars — documentation only.
    - Backend signing endpoints `POST /sales/pipeline/{id}/sign/email` and `/sign/embedded` (`api/v1/sales_pipeline.py:330–441`) — keep behind no UI surface. Optionally add `@deprecated` decorator/comment.
    - Frontend hooks `useGetEmbeddedSigningUrl`, `useTriggerEmailSigning` in `useSalesPipeline.ts` and corresponding API client methods — dormant once unused; safe to leave.
    - Migration `20260411_100300_crm2_sales_pipeline.py` — history is immutable anyway.
    - Enum comments at `models/enums.py:653–667` — documentation, no runtime effect.
  - **TESTS:** prune only the tests that cover the removed paths (webhook auto-advance, `signwell_document_id` convert_to_job gate, embedded signer iframe rendering). Keep dormant-path tests if they still pass; remove if they assert removed behavior.
  - **Net effect:** SignWell becomes "wired up but inert" — no automated state advance, no UI surface, no gating logic. Easy to revive for a real e-sign integration later by re-enabling endpoints and adding back a UI.
  - **Reference scope (full inventory of touchpoints, for awareness):** 58 touchpoints across 20+ files. Categorized findings below — items marked ✂️ are in the removal set above; everything else is in the keep set.
  - **Backend service:** `services/signwell/config.py`, `services/signwell/client.py`, `services/signwell/__init__.py`.
  - **Backend models / DB:** `SalesEntry.signwell_document_id` column (`models/sales.py:78–81`); schema field at `schemas/sales_pipeline.py:48`; migration `20260411_100300_crm2_sales_pipeline.py:66`.
  - **Backend routes / webhooks:** `api/v1/signwell_webhooks.py` (full file, 206 lines, HMAC verify + document_completed handler that auto-advances `pending_approval → send_contract`); `api/v1/sales_pipeline.py:330–382` (`POST /sales/pipeline/{id}/sign/email`); `:385–441` (`POST /sales/pipeline/{id}/sign/embedded`); router mount at `api/v1/router.py:71`.
  - **Backend exception handlers:** `app.py:67–70` (imports), `:739–780`, `:764–806`, `:789–810` (3 SignWell-specific exception handlers).
  - **Backend env / config:** `.env.example:94–98` (`SIGNWELL_API_KEY`, `SIGNWELL_WEBHOOK_SECRET`, `SIGNWELL_API_BASE_URL`).
  - **Backend gating logic:** `sales_pipeline_service.py:439–440` — `convert_to_job` checks `signwell_document_id` unless `force`. **Load-bearing** until we replace it with a "signed agreement PDF uploaded" check.
  - **Frontend components:** `SignWellEmbeddedSigner.tsx` (full file, 87 lines); imported + rendered at `SalesDetail.tsx:53,649`; re-exported via `features/sales/components/index.ts` and `features/sales/index.ts`.
  - **Frontend hooks / API:** `useSalesPipeline.ts:187–191` (`useGetEmbeddedSigningUrl`), `:150–158` (`useTriggerEmailSigning`); `salesPipelineApi.ts:175–192` (`triggerEmailSigning`, `getEmbeddedSigningUrl`).
  - **Frontend copy:** `nowContent.ts:73–82` (the known "Kirill already signed via SignWell" conditional).
  - **Tests:** `tests/unit/test_signwell_webhooks.py`, `tests/unit/test_sales_pipeline_and_signwell.py`, `tests/unit/test_signing_document_wiring.py`, `tests/unit/test_pbt_crm_changes_update_2.py`, `tests/integration/test_signwell_webhook_integration.py`, plus mentions in `test_estimate_visit_confirmation.py`, `test_lead_sales_job_pipeline_integration.py:238,385`, `test_send_estimate_from_pipeline.py`, `test_sales_pipeline_functional.py`.
  - **Enum comments:** `models/enums.py:653–667` (SalesEntryStatus enum has SignWell-referencing comments at :656).
  - **Critical path / load-bearing:** webhook auto-advance (`pending_approval → send_contract`), `signwell_document_id` gate on `convert_to_job`, embedded signer iframe at `send_contract` stage. These three need replacement logic (e.g., "signed agreement PDF uploaded to Documents" check) before removal.

**Cluster C — all decisions captured 2026-05-12. No remaining open questions.** Ready for implementation planning.

### Cluster D — Scheduling / Confirmations

Many items here have locked recommendations from the verification pass; just need implementation plans.

**User clarifications captured 2026-05-12:**

- [ ] **Drag-drop scheduling auto-send** — **Decision (user, 2026-05-12):** drag-drop must **never** auto-send SMS. **If a CONFIRMED appointment is dragged to a new slot, status reverts to SCHEDULED** (not DRAFT — keeps the appointment visually "on the calendar" but un-confirmed). Customer is no longer confirmed for the new time. Admin must explicitly click Send to dispatch a fresh confirmation SMS, and customer must reply Y again to return to CONFIRMED. **Implementation:** find the drag-drop handler on the schedule board; on drop, dispatch a status update to SCHEDULED + clear `confirmation_status`; do **not** call any send-confirmation endpoint as a side effect. `[plan-ready]`.
- [ ] **Status label "Awaiting confirmation" vs "Scheduled"** — `[plan-ready]` per §8.3. **Decision (user, 2026-05-12):** apply the relabel rule to **both sales entries AND appointments** for consistency. UI shows "Awaiting confirmation" whenever the entity's status is `ESTIMATE_SCHEDULED` / `SCHEDULED` but `confirmation_status != 'confirmed'`; flips to "Scheduled" once customer replies Y. Pure frontend — no schema change.
- [ ] **On-My-Way / Job-Start / Job-Complete placeholder** when appointment status is not yet `confirmed` — `[plan-ready]` per §9. **Decision (user, 2026-05-12):** render a **visible info banner above the buttons** (not a disabled button). Banner copy: explain that these actions unlock once the customer replies Y. Buttons themselves are hidden until the appointment is `CONFIRMED`. Banner replaces today's silent gating that left admins confused about why the buttons weren't showing.
- [ ] **Daily schedule slide/drop UX** — port the estimate-view calendar interaction. **Decision (user, 2026-05-12):** **source** is the sales-pipeline estimate calendar at `frontend/src/features/sales/components/ScheduleVisitModal/WeekCalendar.tsx` (week-view layout with click-to-pick + drag-across-slots, configured via `lib/scheduleVisitUtils` for `HOUR_START`, `HOUR_END`, `SLOT_MIN`, `SLOT_PX`; supports `onSlotClick` + `onSlotDrag`, assignee tone coloring, conflict detection). **Target** is the current daily schedule surface at `frontend/src/features/schedule/components/ResourceTimelineView/DayMode.tsx`. **Scope of the port:** lift the slot grid + drag-to-create-range interaction from `WeekCalendar` and apply it to `DayMode` so admins can slide/drop to define an appointment block on the daily schedule the same way they pick estimate slots today. Visual consistency is the win; the existing data model and mutation hooks on `DayMode` stay.
- [ ] **Canonical on-the-way hook path** — **Decision (user, 2026-05-12):** **keep `useOnMyWay` (job-side)**, deprecate `useMarkAppointmentEnRoute` (appointment-side). Rationale: job-side path already has audit logging on `job.on_my_way_at` (`api/v1/jobs.py:1248–1295+`), bughunt L-2 fix ensures `on_my_way_at` is only logged after SMS dispatch succeeds (jobs.py:1278–1281). Remove the appointment-side hook and any callsites; redirect all on-the-way actions through the job endpoint.

**Cluster D — all decisions captured 2026-05-12. No remaining open questions.** Ready for implementation planning.

### Cluster E — Invoices / Stripe interconnection

**User clarifications captured 2026-05-13:**

- [x] **Invoice ↔ Stripe linkage already implemented (verified 2026-05-13).** Architecture C is live. **No schema changes needed.** Findings:
  - Webhook handler at `api/v1/webhooks.py:1194–1320` reconciles `payment_intent.succeeded` events by reading `metadata.invoice_id` (deterministic; no fuzzy matching). Set during payment-link creation at `services/stripe_payment_link_service.py:102–114`.
  - Invoice carries five Stripe-related columns (`models/invoice.py:179–200`): `stripe_payment_link_id`, `stripe_payment_link_url`, `stripe_payment_link_active`, `payment_link_sent_at`, `payment_link_sent_count`.
  - Webhook updates on payment success (`webhooks.py:1309–1320`): calls `InvoiceService.record_payment(payment_reference=f"stripe:{intent_id}")`, flips `stripe_payment_link_active=False`, sets `Job.payment_collected_on_site=True`.
  - Separate audit trail in `stripe_webhook_event` model (`models/stripe_webhook_event.py`); no need for a separate `stripe_events` linking table.
  - **`InvoiceResponse` schema** (`schemas/invoice.py:163–266`) already exposes all 39 fields needed; UI just needs to start rendering the right subset.
- [ ] **Invoice fields to surface in the admin list view post-payment** — **Decision (user, 2026-05-13):** **minimal addition.** Keep existing columns (invoice #, customer, job, amount, status, method, days-due/days-past-due) and add **two columns**: `paid_at` (rendered as a date), and `payment_reference` (the Stripe charge id like `pi_3Oa...`, click-to-copy). No payment-link-state columns (sent count, link active) and no fee-breakdown / late-fee / lien columns in this pass. **File to edit:** `frontend/src/features/invoices/components/InvoiceList.tsx`.
- [ ] **UI surface — where Stripe details show** — **Decision (user, 2026-05-13):** **both list view AND job-detail inline.** Confirmed both surfaces are **admin-only** (customers never see them; the customer's only payment touchpoint is the Stripe-hosted Payment Link via SMS). **Changes:**
  - **Invoices tab list view** (`InvoiceList.tsx`): add `paid_at` + `payment_reference` columns per above.
  - **JobDetail PaymentSection** (`frontend/src/features/jobs/components/PaymentSection.tsx:109–159`): extend today's compact tile (invoice #, sent date, total, status badge) to also show `paid_at` and the Stripe charge id when `status === 'paid'`. Same admin-only audience; consistent detail across both entry points.

**Cluster E — all decisions captured 2026-05-13. No remaining open questions.** Ready for implementation planning. **Note:** item #1 (linkage row) was already implemented — only the UI surfacing work remains.

### Cluster F — Staff Auth UI

**User clarifications captured 2026-05-13:**

- [ ] **§14 Option A locked — admin form sets username + password directly.** `[plan-ready]`. Implementation plan covers:
  - Extend `StaffCreate` schema with optional `username`, `password`, `is_login_enabled` fields (model already has these columns at `models/staff.py:80–104`).
  - Staff create/edit form: add inputs for username, password (write-only, never echoed back after save), enable-login toggle.
  - Service method to hash with bcrypt and persist; do not render password back on subsequent edits.
  - Reset password endpoint (admin-only) on the staff row: triggers a fresh `set_password` flow.
  - Reuses existing lockout / `last_login` / `failed_login_attempts` / `locked_until` machinery — no new tables.
- [ ] **Password strength rules** — **Decision (user, 2026-05-13):** **Standard.** Enforce: **minimum 8 characters**, **at least one letter and one number**, **block a weak-password list** (`admin123`, `password`, `qwerty`, the staff's own username, anything in a small built-in blocklist). **No** symbol / uppercase / lowercase complexity requirement. Applied on both initial set and admin-triggered reset. Server-side validation; matching client-side hint for usability.
- [ ] **Staff list view auth-state indicators** — **Decision (user, 2026-05-13):** **Standard.** Add three indicators to each staff row in the existing staff list:
  - `is_login_enabled` badge (green "Login enabled" vs gray "No login").
  - `last_login` rendered as relative time (e.g. "3 days ago"; "Never" if null).
  - Lockout indicator (red "Locked" badge if `locked_until > now()`).
  - **No** `failed_login_attempts` count and **no** stale-login warning in this pass.
- [ ] **Audit log for password actions** — **Decision (user, 2026-05-13):** **Standard.** Log two event names: `staff.password_set` (initial admin-set password) and `staff.password_reset` (admin-triggered reset on existing account). Each row captures:
  - Actor (admin `staff_id` performing the action).
  - Target (staff whose password is being set/reset).
  - Timestamp.
  - Request IP address.
  - Success/failure outcome (success once bcrypt write commits; failure on validation error like weak password).
  - **Not** in scope: separate audit rows for collateral state changes (e.g., simultaneously flipping `is_login_enabled` or changing username — those flow through existing staff-edit audit paths).
  - Use existing `AuditService.log_action(...)` pattern; no new audit infrastructure.

**Cluster F — all decisions captured 2026-05-13. No remaining open questions.** Ready for implementation planning.

### Cluster G — Reviews / Messaging copy

**User clarifications captured 2026-05-13:**

- [ ] **Extend `docs/messaging-catalog.md` to be the authoritative template catalog** — **Decision (user, 2026-05-13):** broadest scope. **Cover SMS + email + portal copy.** Every customer-facing string the platform can send or display. Existing file dated 2026-05-08 covers SMS + email — needs an email-coverage audit (any templates missing?) and a new portal-copy section for customer-facing portal UI strings (estimate-portal screens, payment-link confirmation pages, opt-in / consent pages, etc.). Catalog entry shape stays as-is (ID, trigger, recipient, sender file:line, template path, raw body, wire body for SMS, sample, notes).
- [ ] **"Thanks for considering Grin's Irrigation" → "Thank you for considering Grin's Irrigation"** — single-line copy change. Once the catalog is updated, the exact `file:line` for this string is one lookup away. Plan-ready as a one-line edit; bundled into the broad polish pass below.
- [ ] **Review-send button dedup scope** — **Decision (user, 2026-05-13):** **per-job dedup.** Allow one review request per **job** (not per customer). A customer with 3 separate jobs over the year can receive 3 review requests — one each. 30-day window applies *within a single job* (so two duplicate sends on the same job within 30 days are blocked, but a new job's request is allowed even if a previous job got a request 5 days ago). **Implementation:** change the dedup key in the Send Review gating logic from `customer_id` to `(customer_id, job_id)`; keep the 30-day window.
- [ ] **"Grin's" vs "Grins" canonical spelling** — **Decision (user, 2026-05-13):** **"Grin's" (with apostrophe)** is canonical. Audit every template + portal copy string for the no-apostrophe form and replace. Email domains (`noreply@grinsirrigation.com`) stay as-is — apostrophe applies to display copy only, not to email addresses or URLs.
- [ ] **Customer-facing SMS content review** — **Decision (user, 2026-05-13):** **broad polish pass.** Re-read every customer-facing SMS template once the catalog is complete; propose copy improvements per template for user approval (one batch per template type, e.g. confirmations / reminders / payment links / reviews / on-the-way / nudges). User signs off on each before any code change. Bundle the "Thanks for considering" fix and the "Grin's" apostrophe sweep into this pass so it's one coordinated copy update, not many small ones.

**Cluster G — all decisions captured 2026-05-13. No remaining open questions.** Ready for implementation planning.

**Suggested execution order for Cluster G** (no commitment, just sequencing):
1. Audit & extend `messaging-catalog.md` to cover SMS + email + portal copy (the working artifact).
2. Per-job dedup change for Send Review (single backend tweak, ships independently).
3. Broad SMS polish pass, batched by template type, user-approved per batch.
4. "Grin's" apostrophe sweep applied to all approved copy at the same time.
5. Final regression: re-render catalog and confirm no drift.

### Cluster H — Other audit gaps surfaced in verification

**User clarifications captured 2026-05-13:**

- [ ] **Stale-portal bug (§13.1)** — `[plan-ready]`. Approve/Reject buttons still render on the customer portal after the estimate is APPROVED. Per §15.3: frontend type expects `is_readonly` but backend sends `readonly` — one-line type rename. Add defense-in-depth: also gate the UI on `estimate.status === 'approved' || 'rejected'`. No user decision needed.
- [ ] **Admin notifications inbox (§5 Option B confirmed) — minimal first cut** — **Decision (user, 2026-05-13):** Option B is locked. **Scope:**
  - **What it is:** an **in-app UI element** (top-nav bell with unread count + dropdown showing recent admin events). Separate from SMS/email — those still fire. The inbox is an *additional* persistent surface inside the admin web app so admins can catch up on missed approvals/cancellations even if their phone was on silent or the text/email was deleted.
  - **Schema:** new `admin_notifications` table — `id`, `event_type`, `subject_resource` (estimate_id / job_id / appointment_id), `summary` (short human string), `created_at`, `read_at`, `actor_user_id`.
  - **Events captured in v1:** estimate approved, estimate rejected, appointment cancelled, late reschedule. (Each existing admin-alert dispatch in `EstimateService`, `NotificationService`, `JobConfirmationService` writes a row in addition to firing SMS/email.)
  - **UI:** bell icon in the top nav with red unread count, dropdown showing last 20 events (click an event → navigate to the subject resource; marks the row read on click). **No dedicated `/admin/notifications` page in v1.** No per-event-type mute preferences in v1.
  - **Delivery:** **polling** the unread-count endpoint every 30s via React Query. No SSE in v1; revisit if notifications become chatty.
  - **Dovetail:** the leads-tab red-counter-clearing item (Cluster B) plugs into the same store once this lands, so the "clears when moved" bug becomes one state update.
- [ ] **Email audit — BCC `info@` on every customer email (lightweight alternative to `sent_emails` table)** — **Decision (user, 2026-05-13):** **do NOT build the `sent_emails` table.** Instead, **BCC `info@grinsirrigation.com` on every customer-facing outbound email** (transactional sends from `noreply@` and commercial sends from `info@` alike). Rationale:
  - `info@` is already the `reply_to` for every send (`email_service.py:320`) and the `COMMERCIAL_SENDER`, so customer replies, bounces (DSN), and outbound copies all converge in one inbox.
  - Lightweight: no new DB table, no new UI, no Resend webhook extension for open/click.
  - **Implementation:** add `bcc=["info@grinsirrigation.com"]` (or a new env var `OUTBOUND_BCC_EMAIL` defaulting to that value) to the Resend payload in `EmailService._send_email`. Apply to all customer-facing sends only — internal staff alerts unchanged.
  - **Tradeoffs the user accepted:** can't filter by customer/job in-app; no opens/clicks tracking; doesn't scale beyond a single admin team without using a Google group. Bounce/complaint Resend webhook (`resend_webhooks.py`) keeps handling compliance separately — BCC does NOT replace that.
  - **Dev/staging guard:** the existing `EMAIL_TEST_ADDRESS_ALLOWLIST` enforcement at `_send_email` must also apply to the BCC; never BCC `info@` in dev/staging. Either skip BCC entirely when allowlist is active, or redirect BCC through `EMAIL_TEST_REDIRECT_TO`.
- [ ] **`sent_emails` table (§12 Option A)** — **Decision (user, 2026-05-13):** **deferred.** BCC-on-`info@` is the v1 audit strategy. Revisit if the team outgrows BCC (e.g. multiple admins need queryable visibility by customer/job, or compliance requires a structured local audit log).
- [ ] **Sticky Approve/Reject CTA on mobile (§13)** — `[plan-ready]`. Single CSS class on the customer-portal Approve/Reject button row to pin it to the bottom of the mobile viewport. No user decision needed.
- [ ] **Document `noreply@grinsirrigation.com` mailbox status** — **Decision (user, 2026-05-13):** **user will do a quick Google Workspace admin check now and report back.** Verification steps for the user: log into Google Workspace admin → search for `noreply@grinsirrigation.com` → confirm whether it's (a) a real user mailbox, (b) a Google Group / alias, or (c) unowned. Note who owns it and what (if anything) lands there. **Action:** once user reports back, I'll record findings in `docs/noreply-mailbox-status.md`. **Important:** this is informational only — the BCC-to-`info@` decision above means we no longer depend on the `noreply@` mailbox for outbound visibility.
- [ ] **`_classify_email` audit for `commercial` vs `transactional`** — quick code audit, no design needed. Walk through every `email_type` passed into `EmailService._send_email`, verify the classification correctly routes through `check_suppression_and_opt_in` so transactional sends (estimates, receipts, password reset) aren't accidentally blocked by an opt-out gate intended for commercial copy. Output: short doc-section listing each `email_type` → classification → suppression-list behaviour. No code change unless misclassifications are found. `[plan-ready]`.

**Cluster H — all decisions captured 2026-05-13. No remaining open questions.** Ready for implementation planning. Two action items awaiting user follow-up:
1. **User to perform Google Workspace check** on `noreply@grinsirrigation.com` and report findings (see item above).

---

## Next cluster to pick (user decides)

Suggested order (highest leverage → lowest):

1. **Cluster A — Notes/Photos/Tags unification** (load-bearing; unblocks B, C, others)
2. **Cluster B — Sales pipeline UX** (most user-facing pain, smallest items)
3. **Cluster C — Job creation + SignWell removal** (depends on A for tags/notes)
4. **Cluster D — Scheduling / confirmations**
5. **Cluster F — Staff auth UI** (mostly plan-ready already)
6. **Cluster H — Audit gaps from verification** (mostly plan-ready already)
7. **Cluster E — Invoices/Stripe**
8. **Cluster G — Reviews/messaging copy** (smallest, easy to slot in any time)
