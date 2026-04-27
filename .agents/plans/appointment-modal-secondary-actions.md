# Feature: AppointmentModal Secondary Actions — Photos, Notes, Review

The following plan should be complete, but its important that you validate documentation and codebase patterns and task sanity before you start implementing.

Pay special attention to naming of existing utils/types/models. Import from the right files etc.

---

## Feature Description

Wire the three currently-stubbed buttons in the `SecondaryActionsStrip` of the new `AppointmentModal` (Schedule tab) — **Add photo**, **Notes**, **Review** — to working sheets that match the modal's design system. The "Edit tags" button is already wired.

Behavioral contract the user asked for:

1. **Add photo** — photos attach to the job (via appointment) AND permeate to the customer so they're visible next time a new job is created for that customer.
2. **Notes** — notes attach to the job AND permeate to the customer, so the customer's record accumulates notes across every job.
3. **Review** — sends a Google review SMS to the customer's phone. The Google review link is `https://share.google/F9eulHUwy4f4AvxSe`.
4. **Edit tags** — already works; do not touch.

Photos should also surface in the **new job creation flow** (JobForm) so staff can see historical photos for the selected customer before creating the next job.

### What's already built (do not rebuild)

- **Backend photo path**: `POST /api/v1/appointments/{id}/photos` creates a `CustomerPhoto` linked to **customer, appointment, and job** simultaneously (`src/grins_platform/api/v1/appointments.py:1408-1420`). Permeation is already correct.
- **Backend list path**: `GET /api/v1/customers/{id}/photos` returns presigned URLs (`src/grins_platform/api/v1/customers.py:1384`).
- **Backend review path**: `POST /api/v1/appointments/{id}/request-review` with 30-day dedup, consent gate, 409 structured error (`src/grins_platform/api/v1/appointments.py:1452-1499`). Service at `services/appointment_service.py:2100`.
- **Frontend API + hooks**: `appointmentApi.uploadPhotos`, `appointmentApi.requestReview`, `useUploadAppointmentPhotos`, `useRequestReview`, `useUpdateAppointment` (`frontend/src/features/schedule/api/appointmentApi.ts:247,261`, `hooks/useAppointmentMutations.ts:252,266`).
- **Legacy notes+photos component**: `frontend/src/features/schedule/components/AppointmentNotes.tsx` and `ReviewRequest.tsx` already exist but use shadcn styling, not the modal's design tokens. They were built for the old `AppointmentDetail.tsx` page that the new `AppointmentModal.tsx` replaced. We will reuse their hooks but **build new design-system-matching sheets**, not adapt the old components.

### What is missing (this plan)

- Sheet components matching the modal's design (`SheetContainer`, 560px, rounded, sticky footer) for Photo/Notes/Review.
- `openSheet` state extension + handler wiring in `AppointmentModal.tsx` + `SecondaryActionsStrip`.
- Display of historical photos (from `CustomerPhoto`) inside the Photo sheet.
- Customer-scoped notes persistence that survives across jobs (see §Decision Required below).
- JobForm integration: thumbnails of customer's past photos when a customer is selected.

---

## User Story

**As a** field-operations staff member working an appointment on the Schedule tab,
**I want** to quickly capture photos, jot notes, and request a Google review from inside the appointment modal,
**So that** media and context attached to this job automatically follow the customer — letting me see past photos when I schedule their next job and letting me send a post-job review request in one tap.

---

## Problem Statement

Three of the four buttons in the redesigned `AppointmentModal`'s `SecondaryActionsStrip` are UI stubs (`onAddPhoto`, `onNotes`, `onReview` are `undefined` in `AppointmentModal.tsx:426`). Staff must either switch to the old `AppointmentDetail` path to do these actions (inconsistent UX, jarring visual shift) or leave the modal entirely. Photos currently persist against the customer via the backend, but staff can't see them when creating a new job for the same customer — so past site conditions aren't visible at the moment they matter. Notes today are single free-text fields scoped only to the appointment — they don't follow the customer from job to job.

## Solution Statement

Build three design-consistent sheets — `PhotoSheet`, `NotesSheet`, `ReviewConfirmSheet` — that slot into the existing `openSheet` state pattern (same mechanism as `TagEditorSheet`, `PaymentSheetWrapper`, `EstimateSheetWrapper`). Reuse all existing backend endpoints and frontend hooks. Add one **customer-scoped `CustomerNote` table** so notes written during an appointment persist on the customer across every future job. Add a lightweight "Past photos" thumbnail row to `JobForm` that fetches `GET /customers/{id}/photos` once a customer is selected.

---

## Feature Metadata

- **Feature Type**: Enhancement (UI wiring + one small backend addition for notes)
- **Estimated Complexity**: Medium — most backend work is already done; scope is ~3 new sheets, ~1 backend table, ~3 new hooks, and JobForm integration
- **Primary Systems Affected**:
  - Frontend: `features/schedule/components/AppointmentModal/*`, `features/schedule/hooks/*`, `features/schedule/types/*`, `features/jobs/components/JobForm.tsx`, `features/customers/api/customerApi.ts`
  - Backend: new `customer_notes` table + model + repository + service + API endpoints in `customers.py`
- **Dependencies**: None new. Uses existing `PhotoService`, `SMSService`, `SheetContainer`, `TanStack Query`, `sonner` toasts, `react-hook-form`.

---

## PROJECT STEERING STANDARDS (mandatory — from `.kiro/steering/`)

Every task in this plan inherits these non-negotiable project standards. Steering docs are the source of truth if any conflict arises with this plan.

### Structured logging — `code-standards.md`, `tech.md`, `vertical-slice-setup-guide.md`

- **Services / repositories**: inherit `LoggerMixin`, set `DOMAIN = "customer_notes"` on the class. Use `self.log_started(...)`, `self.log_completed(...)`, `self.log_rejected(reason=...)`, `self.log_failed(error=...)`. Never log PII, tokens, or passwords.
- **Utilities / non-class code**: `logger = get_logger(__name__)` + `DomainLogger.api_event(logger, "<action>", "<state>", **ctx)`.
- **Event naming**: `{domain}.{component}.{action}_{state}` — examples: `customer_notes.service.create_started`, `customer_notes.api.list_completed`.
- Imports: `from grins_platform.logging import LoggerMixin, get_logger, DomainLogger` (per steering; actual module name may be `log_config` in this repo — grep `LoggerMixin` to confirm import path before writing).

### API endpoint pattern — `api-patterns.md`

Every new endpoint follows this skeleton:

```python
@router.post("/", response_model=..., status_code=status.HTTP_201_CREATED)
async def create_item(...) -> ItemResponse:
    request_id = set_request_id()
    DomainLogger.api_event(logger, "create_item", "started", request_id=request_id, ...)
    try:
        DomainLogger.validation_event(logger, "create_item_request", "started", request_id=request_id)
        # ... validation ...
        DomainLogger.validation_event(logger, "create_item_request", "validated", request_id=request_id)
        item = await service.create_item(request)
        DomainLogger.api_event(logger, "create_item", "completed", request_id=request_id, item_id=item.id, status_code=201)
        return ItemResponse(...)
    except ValidationError as e:
        DomainLogger.api_event(logger, "create_item", "failed", request_id=request_id, error=str(e), status_code=400)
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        DomainLogger.api_event(logger, "create_item", "failed", request_id=request_id, error=str(e), status_code=500)
        raise HTTPException(status_code=500, detail="Internal server error") from e
    finally:
        clear_request_id()
```

Status codes: `GET` → 404 on missing; `PUT/PATCH` → 404 on missing, 400/422 on validation; `DELETE` → 204, 404 on missing.

### Three-tier testing (mandatory) — `code-standards.md`, `tech.md`, `spec-testing-standards.md`

| Tier | Dir | Marker | Dependencies | Purpose |
|------|-----|--------|--------------|---------|
| Unit | `src/grins_platform/tests/unit/` | `@pytest.mark.unit` | All mocked | Isolated correctness |
| Functional | `src/grins_platform/tests/functional/` | `@pytest.mark.functional` | Real DB | User workflow |
| Integration | `src/grins_platform/tests/integration/` | `@pytest.mark.integration` | Full system | Cross-component |

- **Unit naming**: `test_{method}_with_{condition}_returns_{expected}`
- **Functional naming**: `test_{workflow}_as_user_would_experience`
- **Integration naming**: `test_{feature}_works_with_existing_{component}`
- **Property-based tests**: `hypothesis` for business invariants — body length ∈ [1, 2000], cascade-delete soundness, linear chronological ordering of notes by `created_at`.

### Frontend VSA boundaries — `structure.md`, `frontend-patterns.md`, `vertical-slice-setup-guide.md`

- Features may import from `core/` and `shared/`, **never from each other** directly. `features/schedule/hooks/useCustomerNotes.ts` CAN import from `features/customers/api/customerApi.ts` only via the customers feature's public `index.ts` — verify the public surface first; otherwise promote shared API methods to `core/api/` or duplicate.
- New cross-cutting UI primitives go under `shared/components/`, feature-specific UI under `features/{feature}/components/`.
- Sheets that are specific to AppointmentModal belong under `features/schedule/components/AppointmentModal/`.

### Frontend testing & data-testid — `frontend-testing.md`, `frontend-patterns.md`

- Co-located tests: `PhotoSheet.test.tsx` next to `PhotoSheet.tsx`.
- Wrap React Query consumers with `QueryProvider` in `renderHook` / `render`: `const wrapper = ({ children }) => <QueryProvider>{children}</QueryProvider>`.
- **Coverage targets**: Components 80%+, Hooks 85%+, Utils 90%+, backend services 90%+.
- **`data-testid` convention map** (add these on every new element):
  - Pages: `{feature}-page` (e.g., `schedule-page`)
  - Tables/lists: `{feature}-table`, rows: `{feature}-row`
  - Forms: `{feature}-form`
  - Buttons: `{action}-{feature}-btn` (e.g., `upload-photo-btn`, `send-review-btn`, `save-note-btn`)
  - Nav: `nav-{feature}`
  - Status: `status-{value}`
  - **This feature adds**: `photo-sheet`, `notes-sheet`, `review-confirm-sheet`, `photo-upload-area`, `photo-file-input`, `photo-preview-{index}`, `upload-photos-btn`, `save-note-btn`, `note-card-{id}`, `note-scope-toggle`, `delete-note-{id}-btn`, `send-review-btn`, `review-message-preview`, `consent-status-badge`, `past-site-photos-section`, `past-photo-thumb-{index}`

### Type safety & lint — `code-standards.md`, `tech.md`

- All functions: type hints on parameters AND return type. No implicit `Any`.
- **Must pass all four**: `ruff check`, `ruff format --check`, `mypy`, `pyright` with zero errors.
- Frontend: `eslint` + `tsc --noEmit` strict with zero errors.
- 88-char line length (Ruff) / 100-char line length (Prettier — project default).
- Google-style docstrings on public functions/classes.

### Performance budgets — `tech.md`

- API endpoints: **<200ms p95**. The photo/notes sheets load on modal open and must not block the critical render path — fetch via Query only when the sheet is open (`enabled: openSheet === 'photo'`).
- DB queries: **<50ms p95**. Index `customer_id` AND `(customer_id, created_at DESC)` on `customer_notes`. Use `lazy="selectin"` for note relationships.
- Cache: **<10ms p95**. React Query default `staleTime` for list queries is fine; do not disable caching.

### Security — `spec-quality-gates.md`, `tech.md`

- Never log secrets, tokens, phone numbers, or note bodies (body may contain customer PII). Log only IDs.
- All new endpoints require `CurrentActiveUser` dependency (already enforced by pattern in `api/v1/appointments.py`).
- Note body and photo uploads go through existing server-side validation — do not relax them.
- Review SMS respects consent-type scope already — do not bypass.

### Quality-gate command (single source of truth) — `tech.md`

```bash
uv run ruff check --fix src/ && uv run ruff format --check src/ && uv run mypy src/ && uv run pyright src/ && uv run pytest -v
```

All five sub-commands must exit 0 before merge.

### Parallel execution opportunities — `parallel-execution.md`

Tasks can be grouped into parallel phases to save ~40-55% wall-clock time:

```
Phase A (sequential): Task 1 migration → Task 2 model → Task 3 schemas
Phase B (parallel):   Task 4 repository | Task 10 frontend types/state | Task 11 TS types
Phase C (sequential): Task 5 service → Task 6 API endpoints → Task 7 appointment endpoint
Phase D (parallel):   Task 8 backend tests | Task 12 customerApi methods | Task 13 useCustomerNotes | Task 14 useAppointmentPhotos
Phase E (sequential): Task 9 backend checkpoint
Phase F (parallel):   Task 15 PhotoSheet | Task 16 NotesSheet | Task 17 ReviewConfirmSheet
Phase G (sequential): Task 18 SecondaryActionsStrip → Task 19 AppointmentModal
Phase H (parallel):   Task 20 JobForm | Task 21 tests
Phase I (sequential): Task 22 frontend checkpoint → Task 23 E2E → Task 24 DEVLOG
```

### DEVLOG discipline — `devlog-rules.md`, `auto-devlog.md`

After the feature is complete, prepend a new entry to `DEVLOG.md` **at the top, immediately after `## Recent Activity`**. Format:

```markdown
## [2026-04-XX HH:MM] - FEATURE: AppointmentModal secondary actions (photos, notes, review)

### What Was Accomplished
- Wired Add photo / Notes / Review secondary actions in the new AppointmentModal
- Added customer_notes table scoped per-customer with optional appointment/job linkage
- Integrated past-customer photos into JobForm

### Technical Details
- New: customer_notes table + CustomerNote model/repo/service/API
- Reused: POST /appointments/{id}/photos (permeation already correct), POST /appointments/{id}/request-review (30-day dedup), appointmentApi.{uploadPhotos,requestReview}
- New frontend sheets: PhotoSheet, NotesSheet, ReviewConfirmSheet (design-token-matching)

### Decision Rationale
- Chose to REVIVE a dedicated notes table (contradicting 2026-04-18 fold-down) because per-note records with job linkage are required for customer-level accumulation
- Chose server-side review message preview endpoint to prevent template drift

### Challenges and Solutions
- [fill in discovered issues during execution]

### Next Steps
- Consider adding note search across customer detail
- Consider photo tagging / categories in a future iteration
```

Categories (pick one): FEATURE | BUGFIX | REFACTOR | CONFIG | DOCS | TESTING | RESEARCH | PLANNING | INTEGRATION | PERFORMANCE | SECURITY | DEPLOYMENT.

### E2E validation via agent-browser — `e2e-testing-skill.md`, `agent-browser.md`

- Pre-flight: confirm `agent-browser --version`; install via `npm install -g agent-browser && agent-browser install --with-deps` if missing.
- Backend at `http://localhost:8000`; frontend at `http://localhost:5173`.
- Screenshots go to `e2e-screenshots/appointment-modal-secondary-actions/` organized by journey.
- **Responsive viewports to capture**: Mobile 375×812, Tablet 768×1024, Desktop 1440×900.
- **DB validation** after any mutation: `psql "$DATABASE_URL" -c "SELECT ... FROM customer_notes ..."` confirms rows match UI input.
- **Use refs not stale selectors**: `agent-browser snapshot -i` after every navigation/DOM change.
- `agent-browser console` and `agent-browser errors` must be clean (zero JS errors, zero uncaught exceptions) at end of each journey.
- **Off-limits areas**: service agreement flow — verify it still works but do NOT modify it.

---

## 🛑 DECISION REQUIRED BEFORE IMPLEMENTATION

**The notes persistence model.** Today, notes live as single free-text blobs on `customer.internal_notes`, `job.notes`, `appointment.notes`. A dedicated `notes` table was created on 2026-04-16 and **deliberately folded away on 2026-04-18** (5 days before today — migration `20260418_100700_fold_notes_table_into_internal_notes.py`).

The user's explicit ask ("notes should permeate from the job all the way to the customer") requires **per-note records** with a job/appointment link so multiple notes can accumulate on the customer over time. This contradicts the recent fold-down direction.

**Two options — execution agent MUST confirm with user before implementing:**

- **Option A (recommended, plan is written for this):** Revive a `customer_notes` table scoped per-customer with optional `job_id` / `appointment_id` FKs. Mirrors the `CustomerTag` pattern. Leaves `customer.internal_notes` intact as the "sticky profile note" (single blob); new rows are per-appointment note entries. This is what the user asked for.
- **Option B:** Reuse existing single-blob fields. Save the note to `appointment.notes` AND append a timestamped line to `customer.internal_notes`. No schema change. **Tradeoff:** internal_notes becomes a chronological log; loses structured query, loses author, loses per-job threading.

**Execution agent must ask the user which option to take before starting Task 1.** The plan below is written for Option A.

---

## CONTEXT REFERENCES

### Relevant Codebase Files — YOU MUST READ THESE BEFORE IMPLEMENTING

**Backend — existing infra to reuse:**
- `src/grins_platform/api/v1/appointments.py:1326-1499` — `upload_appointment_photos` + `request_google_review` endpoints. **Do not duplicate these; the review/photo endpoints already work.**
- `src/grins_platform/services/appointment_service.py:2100-2200+` — `request_google_review` service method (consent check, 30-day dedup, SMS send via `sms_service.send_message`).
- `src/grins_platform/services/photo_service.py:97-275` — `PhotoService.upload_file` with magic-byte validation, EXIF strip, S3 upload. Allowed contexts: `CUSTOMER_PHOTO` (max 10MB, JPEG/PNG/HEIC/HEIF).
- `src/grins_platform/models/customer_photo.py:24-80` — `CustomerPhoto` model (already has `customer_id` required, `appointment_id`/`job_id` optional FKs, `caption`, `uploaded_by`). This is the authoritative model for "photos attached to customer".
- `src/grins_platform/api/v1/customers.py:1384` — `GET /customers/{id}/photos` returns list with presigned URLs.

**Backend — pattern to mirror for `CustomerNote` (Option A):**
- `src/grins_platform/models/customer_tag.py` — schema shape with `customer_id` FK, timestamps, cascade-delete. Mirror the column layout.
- `src/grins_platform/repositories/customer_tag_repository.py` — CRUD shape for customer-scoped resources.
- `src/grins_platform/services/customer_tag_service.py` — `LoggerMixin`, `DOMAIN = "customer_tags"`, validation.
- `src/grins_platform/api/v1/customers.py` (the tag endpoints) — `GET /customers/{id}/tags`, `PUT /customers/{id}/tags` shape. Copy error handling idioms (404 not found, 422 validation).
- `migrations/versions/20260416_100500_create_notes_table.py` — earlier attempt's columns/indexes; use as reference but scope to customer (not polymorphic `subject_type`).
- `migrations/versions/20260418_100700_fold_notes_table_into_internal_notes.py` — the fold-down migration. Read to understand what was removed and why. This is NOT what we're rebuilding; our table is purpose-built for per-customer accumulation.

**Frontend — existing infra to reuse:**
- `frontend/src/features/schedule/api/appointmentApi.ts:247-256` — `uploadPhotos(id, files[])` POST multipart. **Already works.**
- `frontend/src/features/schedule/api/appointmentApi.ts:261-267` — `requestReview(id)` POST.
- `frontend/src/features/schedule/hooks/useAppointmentMutations.ts:252,266` — `useUploadAppointmentPhotos`, `useRequestReview`. Cache invalidation patterns.
- `frontend/src/features/schedule/components/ReviewRequest.tsx:28-82` — **copy the 409/REVIEW_ALREADY_SENT handling logic verbatim** (lines 45-60). Translate into the new `ReviewConfirmSheet`.
- `frontend/src/features/schedule/components/AppointmentNotes.tsx:20-163` — **copy the file picker + selected-file preview pattern** (lines 44-66, 104-159). Translate into the new `PhotoSheet`.

**Frontend — modal design-system anchors:**
- `frontend/src/shared/components/SheetContainer.tsx` — required wrapper. Props: `title`, `subtitle?`, `onClose`, `onBack?`, `footer?`, `children`.
- `frontend/src/features/schedule/components/AppointmentModal/AppointmentModal.tsx:426-578` — where sheets slot in. Copy the `{openSheet === '...' && ...}` pattern from the tag/payment/estimate sheets.
- `frontend/src/features/schedule/components/AppointmentModal/TagEditorSheet.tsx` — **this is the reference sheet to mirror**. Copy the structure: header section with caps label → body content → footer Cancel + primary action → optimistic update on save → toast on error.
- `frontend/src/features/schedule/components/AppointmentModal/LinkButton.tsx` — use `variant={...Open ? 'active' : 'default'}` pattern for toggleable buttons (if photos/notes sheets should highlight when open).
- `frontend/src/features/schedule/hooks/useModalState.ts:9` — `ModalSheet` union type. Add `'photo' | 'notes' | 'review'`.
- `frontend/src/features/schedule/hooks/useCustomerTags.ts:19-79` — hook pattern (query + optimistic mutation). Mirror for `useCustomerNotes`.
- `frontend/src/features/schedule/components/AppointmentModal/SecondaryActionsStrip.tsx:9-45` — props signature (`onAddPhoto`, `onNotes`, `onReview` already accept `() => void`).

**Frontend — JobForm integration point:**
- `frontend/src/features/jobs/components/JobForm.tsx` — read to find the customer-selected state and where to inject a "Past photos" section. If a customer is required before saving the form, the thumbnail row should appear once `customer_id` is set.
- `frontend/src/features/customers/api/customerApi.ts` — likely already has `getPhotos(customerId)`. Confirm by grepping; if not, add it. This is the endpoint the JobForm will call.

### New Files to Create

**Backend (Option A only):**
- `src/grins_platform/migrations/versions/<timestamp>_add_customer_notes_table.py` — Alembic migration
- `src/grins_platform/models/customer_note.py` — SQLAlchemy model
- `src/grins_platform/schemas/customer_note.py` — Pydantic schemas (`CustomerNoteResponse`, `CustomerNoteCreateRequest`, `CustomerNoteUpdateRequest`)
- `src/grins_platform/repositories/customer_note_repository.py` — CRUD
- `src/grins_platform/services/customer_note_service.py` — business logic + `LoggerMixin`
- Test files: `tests/unit/test_customer_note_model.py`, `test_customer_note_service.py`, `test_customer_note_api.py`
- `tests/functional/test_customer_note_lifecycle_functional.py` — cross-request lifecycle test

**Frontend:**
- `frontend/src/features/schedule/components/AppointmentModal/PhotoSheet.tsx` — design-system photo upload + gallery
- `frontend/src/features/schedule/components/AppointmentModal/NotesSheet.tsx` — design-system notes list + editor
- `frontend/src/features/schedule/components/AppointmentModal/ReviewConfirmSheet.tsx` — confirmation sheet with message preview, consent warning, 409 handling
- `frontend/src/features/schedule/hooks/useAppointmentPhotos.ts` — query hook wrapping `GET /customers/{id}/photos` filtered by `appointment_id` — see GOTCHA §1
- `frontend/src/features/schedule/hooks/useCustomerNotes.ts` — query + mutation hooks (Option A)
- Test files:
  - `frontend/src/features/schedule/components/AppointmentModal/PhotoSheet.test.tsx`
  - `frontend/src/features/schedule/components/AppointmentModal/NotesSheet.test.tsx`
  - `frontend/src/features/schedule/components/AppointmentModal/ReviewConfirmSheet.test.tsx`

### Relevant Documentation — READ BEFORE IMPLEMENTING

- **SQLAlchemy 2.0 typed Mapped columns** — https://docs.sqlalchemy.org/en/20/orm/mapped_attributes.html#mapped-column — pattern the codebase uses everywhere (`Mapped[UUID] = mapped_column(...)`).
- **Alembic auto-generation gotcha** — https://alembic.sqlalchemy.org/en/latest/autogenerate.html#what-does-autogenerate-detect-and-what-does-it-not-detect — autogenerate will NOT detect indexes perfectly; write indexes explicitly.
- **React Hook Form with Zod** — https://react-hook-form.com/get-started#IntegratingwithUIlibraries — used throughout the codebase; see `CustomerForm.tsx` for example.
- **TanStack Query optimistic updates** — https://tanstack.com/query/latest/docs/framework/react/guides/optimistic-updates — the `useSaveCustomerTags` hook (`useCustomerTags.ts:30-79`) is the canonical project example.
- **CallRail SMS provider** — plan memory note: 10DLC registered, IDs resolved. Review SMS goes through `sms_service.send_message(..., message_type=MessageType.GOOGLE_REVIEW_REQUEST, consent_type="transactional")` per the existing service code. **Do not change the message template or consent scope** without product approval.
- **Google review link (from user)**: `https://share.google/F9eulHUwy4f4AvxSe` — confirm with user that backend's current review message template uses this exact URL before shipping. If not, surface the discrepancy; do NOT silently change the backend message.

### Patterns to Follow

**Backend module structure (mirror `customer_tag.*`):**
```python
# src/grins_platform/models/customer_note.py
class CustomerNote(Base):
    __tablename__ = "customer_notes"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    customer_id: Mapped[UUID] = mapped_column(PGUUID, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    job_id: Mapped[UUID | None] = mapped_column(PGUUID, ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True)
    appointment_id: Mapped[UUID | None] = mapped_column(PGUUID, ForeignKey("appointments.id", ondelete="SET NULL"), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    author_id: Mapped[UUID | None] = mapped_column(PGUUID, ForeignKey("staff.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
```
Index `customer_id`; composite index `(customer_id, created_at DESC)` for listing newest first; soft-delete NOT needed (we just delete rows).

**Pydantic schemas (mirror `schemas/customer_tag.py`):**
```python
class CustomerNoteResponse(BaseModel):
    id: UUID
    customer_id: UUID
    job_id: UUID | None
    appointment_id: UUID | None
    body: str
    author_id: UUID | None
    author_name: str | None  # resolved from staff relationship
    created_at: datetime
    updated_at: datetime
```

**Logger pattern:**
```python
class CustomerNoteService(LoggerMixin):
    DOMAIN = "customer_notes"
    async def create_note(self, ...): self.log_started("create_note", customer_id=...); ...
```

**Error handling:** mirror `customer_tag_service.py` — raise `CustomerNotFoundError` / custom exceptions, let the API layer translate to 404/422.

**Sheet component layout (mirror `TagEditorSheet.tsx` header/body/footer):**
```tsx
<SheetContainer title="..." subtitle="..." onClose={onClose} footer={<footerButtons />}>
  <div className="px-5 py-4 space-y-4">
    {/* caps label + content */}
  </div>
</SheetContainer>
```

**React Query invalidation after mutation (mirror `useCustomerTags.ts`):**
- On success: `queryClient.invalidateQueries({ queryKey: customerNoteKeys.byCustomer(customerId) })` AND `customerKeys.detail(customerId)` AND `appointmentKeys.detail(appointmentId)`.

**Toast patterns (project convention):**
```tsx
toast.success('Photos uploaded');
toast.error('Failed to upload — try again');
toast.info('Already requested', { description: '...' });  // for 409 dedup
```

**Color / style tokens (from existing sheets):**
- Primary action: `bg-[#0B1220] text-white`
- Destructive: `text-[#B91C1C] border-[#FCA5A5]`
- Caps labels: `text-[11px] uppercase tracking-[0.8px] text-[#6B7280] font-[700]`
- Borders: `border-[#E5E7EB]`
- Soft bg: `bg-[#F9FAFB]`

---

## IMPLEMENTATION PLAN

### Phase 0: Confirmation

Before any code, confirm with the user:
1. Option A vs Option B for notes persistence (see §Decision Required above).
2. Whether the current backend review message template contains the URL `https://share.google/F9eulHUwy4f4AvxSe`. If not, whether to update it as part of this work.

### Phase 1: Backend Foundation (Option A only)

Only execute this phase if the user confirms Option A.

- Alembic migration creates `customer_notes` table with indexes + FKs
- `CustomerNote` model with typed `Mapped` columns + relationships
- Pydantic schemas for request/response
- Repository with `get_by_customer`, `get_by_appointment`, `create`, `update`, `delete`
- Service layer with `LoggerMixin`, validation (body 1–2000 chars), author resolution
- API endpoints:
  - `GET  /api/v1/customers/{customer_id}/notes` — list, ordered newest first
  - `POST /api/v1/customers/{customer_id}/notes` — create (accepts optional `job_id`, `appointment_id`)
  - `PATCH /api/v1/customers/{customer_id}/notes/{note_id}` — update body
  - `DELETE /api/v1/customers/{customer_id}/notes/{note_id}` — delete
  - `GET  /api/v1/appointments/{appointment_id}/notes` — convenience: all notes attached to THIS appointment (for sheet initial render)

### Phase 2: Frontend Hooks & Types

- Extend `ModalSheet` union in `useModalState.ts` with `'photo' | 'notes' | 'review'`
- Add `CustomerPhoto` and `CustomerNote` TypeScript types in `features/schedule/types/index.ts` (mirror `CustomerTag`)
- Add `getNotes`, `createNote`, `updateNote`, `deleteNote` methods to `customerApi.ts`
- Create `useCustomerNotes(customerId)` + `useAppointmentNotes(appointmentId)` query hooks
- Create `useCreateCustomerNote`, `useUpdateCustomerNote`, `useDeleteCustomerNote` mutation hooks with optimistic updates — mirror `useSaveCustomerTags` pattern (`useCustomerTags.ts:30-79`)
- Create `useCustomerPhotos(customerId)` hook (or `useAppointmentPhotos(appointmentId)` that filters the customer list by `appointment_id`; the backend returns `appointment_id` on each `CustomerPhoto` so client-side filter is fine — see GOTCHA §1)

### Phase 3: Sheet Components

- `PhotoSheet.tsx`:
  - Header: "Add photos", subtitle `"Photos apply to [Customer Name] — visible on past and future jobs"`
  - Body section 1: file picker (multiple, `accept="image/*;capture=camera"`, max 10MB per file validated client-side), selected-file preview list with remove-X (mirror `AppointmentNotes.tsx:104-159`)
  - Body section 2: **This appointment's photos** — grid of thumbnails from `useAppointmentPhotos(appointmentId)` with caption + download link
  - Body section 3 (collapsed by default): **Other photos on this customer** — thumbnails from `useCustomerPhotos(customerId)` excluding the current appointment
  - Footer: Cancel + `Upload N photo(s)` primary button (disabled when empty or `mutation.isPending`)
  - On upload success: toast "Photos uploaded", clear selection, invalidate `customerKeys.photos(customerId)` and `appointmentKeys.detail(appointmentId)`
- `NotesSheet.tsx`:
  - Header: "Notes", subtitle `"Notes apply to [Customer Name] across every job — past and future"` (matches tag editor wording)
  - Body: vertically stacked `NoteCard`s with `created_at` timestamp, author name, body text. Each shows a job/appointment scope chip ("This appointment" / "Job #1234" / "Profile note") when linked.
  - Compose box at the bottom (multi-line textarea, max 2000 chars, submit via Cmd/Ctrl+Enter or button) with a scope toggle: `This appointment` (default) / `Customer profile`
  - On save: optimistic insert, toast "Note saved", invalidate customer + appointment note queries
  - Deletion: hover-action × on each card with a confirm popover
- `ReviewConfirmSheet.tsx`:
  - Header: "Send Google review request", subtitle `"We'll text [Customer Name] at [phone] the Google review link"`
  - Body: message preview box showing the exact SMS text the backend will send (pull template from a shared constant — see GOTCHA §3), consent status line ("Customer has consented to SMS" / "⚠ Customer has opted out — request cannot be sent"), last-sent indicator if in 30-day window
  - Footer: Cancel + `Send review request` primary button
  - Only render when `appointment.status === 'completed'` (mirror `ReviewRequest.tsx:31`)
  - Handle 409 `REVIEW_ALREADY_SENT` with the structured-detail pattern from `ReviewRequest.tsx:45-60`
  - Handle 2xx `sent:false` returns (no-consent case) — show the backend's `message` in the UI, not a generic error

### Phase 4: Wire into AppointmentModal

- In `AppointmentModal.tsx`:
  - Pass `onAddPhoto={() => openSheetExclusive('photo')}`, `onNotes={() => openSheetExclusive('notes')}`, `onReview={() => openSheetExclusive('review')}` to `SecondaryActionsStrip` (line 426-429)
  - Add three new `{openSheet === '...' && <Sheet ... />}` blocks after the estimate sheet (after line 578)
  - Gate `onReview` on `appointment.status === 'completed'` — either hide/disable the button or show a toast explaining the gate
- `SecondaryActionsStrip.tsx`:
  - Add `photoOpen`, `notesOpen`, `reviewOpen` boolean props mirroring `tagsOpen`
  - Use `variant="active"` on each button when its sheet is open
  - No API change to existing `onEditTags` wiring

### Phase 5: JobForm Integration

- In `JobForm.tsx`, once a customer is selected (watch `customer_id` via `react-hook-form`'s `watch`), render a "Past site photos" section:
  - Call `useCustomerPhotos(customerId)` (same hook used by PhotoSheet)
  - Render a horizontally scrolling thumbnail row (8–12 most recent) with a "See all" link that opens a lightbox/drawer
  - Empty state: hide the section (no "No photos yet" placeholder)
  - Lazy-loaded: only fetch when the section becomes visible (defer the query with `enabled: Boolean(customerId)`)

### Phase 6: Testing

- Backend unit tests for `CustomerNote` model/service/API (mirror existing `test_customer_tag_*.py` suites 1:1)
- Backend functional test: create customer → create note linked to appointment → verify visible via both `/customers/{id}/notes` and `/appointments/{id}/notes` → update → delete → verify cascade on customer delete
- Frontend component tests for PhotoSheet / NotesSheet / ReviewConfirmSheet — render, interactions, error toast paths, 409 dedup handling, optimistic-rollback on mutation failure
- Update `AppointmentModal.test.tsx` — assert the 3 new sheets open exclusively and close on backdrop/ESC
- Update `SecondaryActionsStrip.test.tsx` (if it exists — otherwise add) — assert `variant="active"` for each open sheet

### Phase 7: E2E (Vercel + agent-browser)

- Deploy frontend to Vercel
- Use `agent-browser` to: open schedule → click an appointment → click Add photo → upload a test image → verify the photo appears → reopen the same appointment → verify photo persists → navigate to customer detail → verify photo is there → navigate to new-job creation for same customer → verify thumbnail appears
- Repeat for notes: add note on appointment → verify on customer detail page
- Repeat for review: set an appointment status to `completed` (use test fixture or a pre-completed appointment) → click Review → send → verify 2nd click shows 409 "Already sent" state
- Capture screenshots in `e2e-screenshots/appointment-modal-secondary-actions/`

---

## STEP-BY-STEP TASKS

IMPORTANT: Execute every task in order, top to bottom. Each task is atomic and independently testable. Confirm §DECISION REQUIRED with user before beginning Task 1.

### Task 1 — CREATE `src/grins_platform/migrations/versions/<timestamp>_add_customer_notes_table.py`

- **IMPLEMENT**: Alembic migration creating `customer_notes` table with columns `id UUID PK server_default gen_random_uuid()`, `customer_id UUID FK→customers.id ON DELETE CASCADE NOT NULL`, `job_id UUID FK→jobs.id ON DELETE SET NULL NULL`, `appointment_id UUID FK→appointments.id ON DELETE SET NULL NULL`, `body TEXT NOT NULL`, `author_id UUID FK→staff.id ON DELETE SET NULL NULL`, `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`, `updated_at TIMESTAMPTZ NOT NULL DEFAULT now()`. Add index on `customer_id` and composite index on `(customer_id, created_at DESC)`. Include a CHECK constraint `char_length(body) BETWEEN 1 AND 2000`.
- **PATTERN**: `src/grins_platform/migrations/versions/` — find a recent `customer_tags` migration and mirror its header format
- **IMPORTS**: `alembic.op`, `sqlalchemy as sa`, `sqlalchemy.dialects.postgresql as postgresql`
- **GOTCHA**: The migration file `20260418_100700_fold_notes_table_into_internal_notes.py` dropped an earlier `notes` table. Make sure the new table name is `customer_notes` (different name) and that the new migration's `down_revision` points at the CURRENT head. Run `uv run alembic heads` first to confirm the head.
- **VALIDATE**: `uv run alembic upgrade head && uv run alembic downgrade -1 && uv run alembic upgrade head`

### Task 2 — CREATE `src/grins_platform/models/customer_note.py`

- **IMPLEMENT**: `CustomerNote` SQLAlchemy model with typed `Mapped` columns matching the migration. Add `customer`, `job`, `appointment`, `author` relationships (all `lazy="selectin"`, `nullable` where appropriate).
- **PATTERN**: `src/grins_platform/models/customer_tag.py` — direct mirror
- **IMPORTS**: `from grins_platform.database import Base`, `TYPE_CHECKING` guard for `Customer`, `Job`, `Appointment`, `Staff`
- **GOTCHA**: Register model export in `models/__init__.py` so Alembic autogenerate picks it up on future revisions.
- **VALIDATE**: `uv run python -c "from grins_platform.models.customer_note import CustomerNote; print(CustomerNote.__tablename__)"`

### Task 3 — CREATE `src/grins_platform/schemas/customer_note.py`

- **IMPLEMENT**: `CustomerNoteResponse`, `CustomerNoteCreateRequest` (body 1–2000 chars, optional `job_id` and `appointment_id`), `CustomerNoteUpdateRequest` (body only)
- **PATTERN**: `src/grins_platform/schemas/customer_tag.py`
- **VALIDATE**: `uv run pyright src/grins_platform/schemas/customer_note.py`

### Task 4 — CREATE `src/grins_platform/repositories/customer_note_repository.py`

- **IMPLEMENT**: `CustomerNoteRepository` with `get_by_customer(customer_id, limit=50, offset=0)`, `get_by_appointment(appointment_id)`, `get_by_id(note_id)`, `create(note)`, `update(note_id, body)`, `delete(note_id)`
- **PATTERN**: `src/grins_platform/repositories/customer_tag_repository.py` for async session + eager-loading idioms
- **GOTCHA**: Always `.order_by(CustomerNote.created_at.desc())` on list queries
- **VALIDATE**: `uv run pyright src/grins_platform/repositories/customer_note_repository.py`

### Task 5 — CREATE `src/grins_platform/services/customer_note_service.py`

- **IMPLEMENT**: `CustomerNoteService(LoggerMixin)` with `DOMAIN = "customer_notes"`. Methods: `list_by_customer`, `list_by_appointment`, `create_note`, `update_note`, `delete_note`. Each method calls `self.log_started(...)`, `self.log_completed(...)`, `self.log_rejected(reason=...)` / `self.log_failed(error=...)` per §PROJECT STEERING STANDARDS. Validate: body length 1–2000, customer exists (raise `CustomerNotFoundError`), appointment/job exist if provided.
- **PATTERN**: `src/grins_platform/services/customer_tag_service.py` for logging idioms, error taxonomy, and LoggerMixin usage
- **IMPORTS**: Confirm the exact logging import path by grepping: `grep -rn "class.*LoggerMixin" src/grins_platform/`. Steering docs cite `from grins_platform.logging import LoggerMixin, get_logger, DomainLogger` but repo may use `log_config` — use whatever existing services use.
- **GOTCHA**: Resolve `author_name` from the staff relationship for the response model. Do NOT call `sms_service` or any external service from here. NEVER log note body (may contain PII) — log only IDs.
- **VALIDATE**: `uv run pytest -m unit src/grins_platform/tests/unit/test_customer_note_service.py -v`

### Task 6 — UPDATE `src/grins_platform/api/v1/customers.py`

- **IMPLEMENT**: Append 4 endpoints, each following the `api-patterns.md` template verbatim (see §PROJECT STEERING STANDARDS): `set_request_id()` → `DomainLogger.api_event(..., "<action>", "started", request_id=...)` → validation event → service call → completion event with `status_code` → `except` paths with failed event → `finally: clear_request_id()`.
  - `GET  /{customer_id}/notes` → `list[CustomerNoteResponse]` (404 if customer missing)
  - `POST /{customer_id}/notes` → `CustomerNoteResponse` (201; 400/422 on validation, 404 on customer missing)
  - `PATCH /{customer_id}/notes/{note_id}` → `CustomerNoteResponse` (200; 404 if note missing, 400/422 on validation)
  - `DELETE /{customer_id}/notes/{note_id}` → `204 No Content` (404 if note missing)
- **PATTERN**: The existing `/tags` endpoints in the same file + `api-patterns.md` full template
- **IMPORTS**: `from grins_platform.services.customer_note_service import CustomerNoteService` + DI factory
- **GOTCHA**: NEVER include the note `body` in log context — only IDs, request_id, and status_code. Use `DomainLogger.validation_event` for request body shape validation, separate from `DomainLogger.api_event` for request lifecycle.
- **VALIDATE**: `uv run pytest -m unit src/grins_platform/tests/unit/test_customer_note_api.py -v`

### Task 7 — UPDATE `src/grins_platform/api/v1/appointments.py`

- **IMPLEMENT**: Add `GET /{appointment_id}/notes` endpoint delegating to `CustomerNoteService.list_by_appointment(appointment_id)`. Returns `list[CustomerNoteResponse]`. Follows the same `api-patterns.md` template (request_id correlation, start/complete/fail logging, clear_request_id in finally).
- **PATTERN**: Mirror the `upload_appointment_photos` endpoint's structure (lines 1331-1443) — auth, service DI, 404 on not-found.
- **GOTCHA**: This endpoint is a convenience for the PhotoSheet/NotesSheet's initial render; it does NOT mutate data. Still must follow the full logging template.
- **VALIDATE**: `uv run pytest -m unit src/grins_platform/tests/unit/test_customer_note_api.py::test_list_by_appointment -v`

### Task 8 — CREATE backend test files (three tiers + PBT)

- **IMPLEMENT**: Four test files covering all tiers per `code-standards.md` + `spec-testing-standards.md`:
  - `tests/unit/test_customer_note_model.py` — `@pytest.mark.unit`, all mocked; assert model instantiation, FK wiring, `__repr__`
  - `tests/unit/test_customer_note_service.py` — `@pytest.mark.unit`, mock repository; cover `create_note`, `update_note`, `delete_note`, `list_by_customer`, `list_by_appointment`, validation failures (body too long, customer missing), log events emitted
  - `tests/unit/test_customer_note_api.py` — `@pytest.mark.unit`, FastAPI TestClient with `app.dependency_overrides[get_customer_note_service] = lambda: mock_service`; assert 201/200/204/400/404/422 paths AND that `request_id` appears in logged events
  - `tests/functional/test_customer_note_lifecycle_functional.py` — `@pytest.mark.functional`, real DB; full workflow: create customer → create note linked to appointment → verify visible via both `/customers/{id}/notes` and `/appointments/{id}/notes` → update → delete → cascade-delete customer → verify notes gone
  - `tests/unit/test_customer_note_pbt.py` (new) — `@pytest.mark.unit` + Hypothesis strategies; properties to assert:
    1. Body validation: any string with 1 ≤ len ≤ 2000 is accepted; anything outside raises 422
    2. Ordering: `list_by_customer` always returns in reverse-chronological `created_at` order
    3. Scope invariant: a note created with `appointment_id=X` appears in both `list_by_customer` and `list_by_appointment(X)`; created without `appointment_id` appears only in `list_by_customer`
- **PATTERN**: `test_customer_tag_*.py` suites 1:1 for unit/functional structure; existing PBT files in `tests/unit/test_pbt_*.py` for Hypothesis idioms
- **GOTCHA**: Unit tests MUST use `@pytest.mark.unit` marker. Functional tests MUST use `@pytest.mark.functional` and a real DB fixture from `conftest.py`. Do not mix markers.
- **VALIDATE**: `uv run pytest -m unit src/grins_platform/tests/unit/test_customer_note_*.py -v && uv run pytest -m functional src/grins_platform/tests/functional/test_customer_note_lifecycle_functional.py -v`

### Task 9 — Checkpoint: backend green (mandatory quality gate from `tech.md`)

- **IMPLEMENT**: Run full quality-gate command; zero errors on all five sub-commands. Also verify coverage target: `uv run pytest --cov=src/grins_platform/services/customer_note_service --cov=src/grins_platform/repositories/customer_note_repository --cov-fail-under=90` (services 90%+ per `spec-quality-gates.md`).
- **VALIDATE**: `uv run ruff check --fix src/ && uv run ruff format --check src/ && uv run mypy src/ && uv run pyright src/ && uv run pytest -v`

### Task 10 — UPDATE `frontend/src/features/schedule/hooks/useModalState.ts`

- **IMPLEMENT**: Extend `ModalSheet` union from `'payment' | 'estimate' | 'tags'` to `'payment' | 'estimate' | 'tags' | 'photo' | 'notes' | 'review'`. No other hook logic changes.
- **VALIDATE**: `cd frontend && npm run typecheck`

### Task 11 — UPDATE `frontend/src/features/schedule/types/index.ts` and `frontend/src/features/customers/types/index.ts`

- **IMPLEMENT**: Add `CustomerNote`, `CustomerNoteCreateRequest`, `CustomerNoteUpdateRequest`, `CustomerPhoto` (if not already present — grep first) TypeScript types matching the backend schemas.
- **PATTERN**: `CustomerTag` type in the same files
- **VALIDATE**: `cd frontend && npm run typecheck`

### Task 12 — UPDATE `frontend/src/features/customers/api/customerApi.ts`

- **IMPLEMENT**: Add `getNotes(customerId)`, `createNote(customerId, payload)`, `updateNote(customerId, noteId, payload)`, `deleteNote(customerId, noteId)`, and `getPhotos(customerId)` if not already present.
- **PATTERN**: The existing `getTags` / `saveTags` methods in the same file
- **GOTCHA**: `getPhotos` may already exist (used by `CustomerDetail`'s `PhotoGallery`); grep before duplicating.
- **VALIDATE**: `cd frontend && npm run typecheck`

### Task 13 — CREATE `frontend/src/features/schedule/hooks/useCustomerNotes.ts`

- **IMPLEMENT**: Export query hooks `useCustomerNotes(customerId)`, `useAppointmentNotes(appointmentId)` and mutation hooks `useCreateCustomerNote`, `useUpdateCustomerNote`, `useDeleteCustomerNote` — each with optimistic update + rollback + cache invalidation across customer AND appointment note keys.
- **PATTERN**: `frontend/src/features/schedule/hooks/useCustomerTags.ts`
- **IMPORTS**: `useMutation`, `useQuery`, `useQueryClient` from `@tanstack/react-query`; `customerApi` from `@/features/customers/api/customerApi`
- **VALIDATE**: `cd frontend && npm run typecheck && npm test -- useCustomerNotes`

### Task 14 — CREATE `frontend/src/features/schedule/hooks/useAppointmentPhotos.ts`

- **IMPLEMENT**: `useAppointmentPhotos(appointmentId, customerId)` hook that calls `customerApi.getPhotos(customerId)` and returns two derived lists: `thisAppointment` (filtered by `appointment_id === appointmentId`) and `otherCustomerPhotos`. Use `select:` to compute.
- **PATTERN**: `useCustomerTags.ts`
- **GOTCHA**: If there's already a `useCustomerPhotos` in `features/customers/hooks`, reuse it and do the split in the PhotoSheet component; don't duplicate.
- **VALIDATE**: `cd frontend && npm run typecheck`

### Task 15 — CREATE `frontend/src/features/schedule/components/AppointmentModal/PhotoSheet.tsx`

- **IMPLEMENT**: Props `{ appointmentId: string; customerId: string; customerName: string; onClose: () => void }`. Render `SheetContainer` with title/subtitle (root gets `data-testid="photo-sheet"`). File picker section with `data-testid="photo-upload-area"`, hidden input `data-testid="photo-file-input"`, each preview row `data-testid="photo-preview-{index}"`, upload button `data-testid="upload-photos-btn"`. Two gallery sections: "This appointment" (`data-testid="this-appointment-photos"`) and "All of [customer]'s photos" (`data-testid="all-customer-photos"`). Upload calls `useUploadAppointmentPhotos().mutateAsync`. On success, toast and invalidate `customerKeys.photos(customerId)` AND `appointmentKeys.detail(appointmentId)`.
- **PATTERN**: `TagEditorSheet.tsx` for sheet layout, footer, and optimistic flow; `AppointmentNotes.tsx:104-159` for file picker UX; `frontend-patterns.md` §data-testid Convention for the naming scheme.
- **IMPORTS**: `SheetContainer` from `@/shared/components/SheetContainer`; `useUploadAppointmentPhotos` from `../../hooks/useAppointmentMutations`; hook from Task 14; `toast` from `sonner`; `Camera`, `X`, `Loader2` icons from `lucide-react`.
- **GOTCHA**: Client-side file validation: reject >10MB, reject non-`image/*` MIME. The backend will reject too (bughunt M-16 415/413) but fail faster client-side with a clearer toast. Respect VSA boundaries: if `useCustomerPhotos` lives in `features/customers`, import via its `index.ts` public surface — never via deep path.
- **VALIDATE**: `cd frontend && npm test -- PhotoSheet.test.tsx` — test loading/error/empty/success states; assert coverage ≥ 80% (Components target).

### Task 16 — CREATE `frontend/src/features/schedule/components/AppointmentModal/NotesSheet.tsx`

- **IMPLEMENT**: Props `{ appointmentId: string; jobId: string; customerId: string; customerName: string; onClose: () => void }`. Root `data-testid="notes-sheet"`, each note `data-testid="note-card-{id}"`, compose textarea `data-testid="note-compose-textarea"`, scope toggle `data-testid="note-scope-toggle"`, save button `data-testid="save-note-btn"`, delete button `data-testid="delete-note-{id}-btn"`. Fetch notes via `useCustomerNotes(customerId)`. Render chronological stack (reverse-chronological, newest first — matches backend ordering) with each note's timestamp, author, body, scope-chip. Compose box at bottom with scope toggle: Appointment (default: pass `appointment_id` + `job_id`) / Profile (pass neither). Submit via Cmd/Ctrl+Enter or button. Delete with confirm popover. Update in place on click-to-edit.
- **PATTERN**: `TagEditorSheet.tsx` for sheet shell + optimistic save flow; `frontend-patterns.md` Form pattern (React Hook Form + Zod for compose validation: body 1–2000 chars).
- **GOTCHA**: When the user selects "Appointment" scope, ALWAYS send both `appointment_id` AND `job_id` so the note is discoverable from either side. When "Profile", send neither. Invalidate queries: `customerNoteKeys.byCustomer(customerId)`, `customerNoteKeys.byAppointment(appointmentId)`, `customerKeys.detail(customerId)`, `appointmentKeys.detail(appointmentId)`.
- **VALIDATE**: `cd frontend && npm test -- NotesSheet.test.tsx` — test empty/loading/error/populated + form validation + optimistic rollback; coverage ≥ 80%.

### Task 17 — CREATE `frontend/src/features/schedule/components/AppointmentModal/ReviewConfirmSheet.tsx`

- **IMPLEMENT**: Props `{ appointmentId: string; appointmentStatus: AppointmentStatus; customerName: string; customerPhone: string | null; onClose: () => void }`. `SheetContainer` with title "Send Google review request" (root `data-testid="review-confirm-sheet"`). Body: message-preview box `data-testid="review-message-preview"`, phone line, consent-status badge `data-testid="consent-status-badge"`. Footer: Cancel + primary "Send review request" `data-testid="send-review-btn"`. On send: call `useRequestReview().mutateAsync(appointmentId)`. Handle 409/REVIEW_ALREADY_SENT exactly as `ReviewRequest.tsx:45-60` does (translate detail → `toast.info('Already requested', { description: 'Already sent within last 30 days (sent DATE)' })`). Close sheet on success.
- **GOTCHA** (§3): The SMS message text is constructed server-side inside `appointment_service.request_google_review`. The preview shown in the sheet must match the server's actual text. **Recommended**: add a backend endpoint `GET /appointments/{id}/review-preview` that returns the rendered text — follows the same `api-patterns.md` template (request_id correlation, DomainLogger events, clear_request_id in finally). Fallback: duplicate the template in a shared frontend constant with a contract test that asserts it matches a server fixture.
- **PATTERN**: `TagEditorSheet.tsx` shell; `ReviewRequest.tsx` mutation/error handling; `api-patterns.md` for the new preview endpoint.
- **VALIDATE**: `cd frontend && npm test -- ReviewConfirmSheet.test.tsx` — test completed-status gate, 409 path, 2xx sent:false consent path, disabled-when-no-phone; coverage ≥ 80%.

### Task 18 — UPDATE `frontend/src/features/schedule/components/AppointmentModal/SecondaryActionsStrip.tsx`

- **IMPLEMENT**: Add `photoOpen?: boolean`, `notesOpen?: boolean`, `reviewOpen?: boolean` props. Use `variant={photoOpen ? 'active' : 'default'}` on each corresponding `LinkButton`. Gate the Review button with a `disabled` state when `appointment.status !== 'completed'` (pass `canRequestReview?: boolean` prop from parent).
- **VALIDATE**: `cd frontend && npm test -- SecondaryActionsStrip`

### Task 19 — UPDATE `frontend/src/features/schedule/components/AppointmentModal/AppointmentModal.tsx`

- **IMPLEMENT**:
  1. Wire `onAddPhoto`, `onNotes`, `onReview`, `photoOpen`, `notesOpen`, `reviewOpen`, `canRequestReview` props to `SecondaryActionsStrip` (lines 426-429)
  2. Below line 578 (after EstimateSheet), add `{openSheet === 'photo' && customer && <div className="absolute inset-0 z-10"><PhotoSheet ... /></div>}` and equivalents for `'notes'` and `'review'`
  3. For the Review sheet, only pass `customerPhone` and set `canRequestReview = appointment.status === 'completed' && Boolean(customer?.phone)`
- **PATTERN**: The existing `{openSheet === 'tags' && customer && ...}` block (lines 551-559)
- **VALIDATE**: `cd frontend && npm test -- AppointmentModal`

### Task 20 — UPDATE `frontend/src/features/jobs/components/JobForm.tsx`

- **IMPLEMENT**: When the form's `customer_id` has a value, render a "Past site photos" section above the submit button. Use `useCustomerPhotos(customerId)` (or the new hook from Task 14). Show up to 12 thumbnails, each clickable to open a lightbox. Use `enabled: Boolean(customerId)` so the query doesn't fire until a customer is picked.
- **PATTERN**: Look for any existing thumbnail grids in `features/customers/components/PhotoGallery.tsx` and reuse/adapt.
- **GOTCHA**: This section is informational only; it does NOT bind photos to the new job. Photos bind when staff upload through the AppointmentModal of a resulting appointment.
- **VALIDATE**: `cd frontend && npm test -- JobForm`

### Task 21 — UPDATE `AppointmentModal.test.tsx` and add new test files

- **IMPLEMENT**: Assert: opening each new sheet closes any other open sheet (single-sheet exclusivity); backdrop/ESC closes the sheet; Review button is disabled for non-completed appointments; 409 review response produces "Already sent" toast.
- **VALIDATE**: `cd frontend && npm test`

### Task 22 — Checkpoint: frontend green (quality gate from `frontend-testing.md`)

- **IMPLEMENT**: Zero errors across lint + typecheck + tests. Verify coverage targets: Components 80%+, Hooks 85%+.
- **VALIDATE**: `cd frontend && npm run typecheck && npm run lint && npm run format:check && npm run test:coverage`

### Task 23 — E2E on Vercel via agent-browser (`e2e-testing-skill.md`)

- **IMPLEMENT**:
  1. Pre-flight: `agent-browser --version` (install via `npm install -g agent-browser && agent-browser install --with-deps` if missing)
  2. Deploy frontend to Vercel; grab deploy URL
  3. Use `agent-browser --session e2e-appointment-secondary open <url>` for isolation
  4. Run the journeys from §Phase 7, using `snapshot -i` → refs for each step. Re-snapshot after every navigation/form submission.
  5. Capture screenshots to `e2e-screenshots/appointment-modal-secondary-actions/` organized by journey: `01-photo-upload/`, `02-notes-create/`, `03-review-send/`, `04-review-duplicate/`, `05-jobform-past-photos/`
  6. Responsive capture at 375×812, 768×1024, 1440×900 for the modal open state
  7. DB validation after each mutation: `psql "$DATABASE_URL" -c "SELECT id, customer_id, job_id, appointment_id, LEFT(body, 40) FROM customer_notes ORDER BY created_at DESC LIMIT 5"` (do NOT SELECT full body into logs)
  8. `agent-browser console` and `agent-browser errors` after each journey — must be clean
  9. `agent-browser close` on completion
- **GOTCHA**: Per project memory, real SMS during testing MUST only go to `+19527373312`. Pick a test customer whose phone matches OR set `SMS_PROVIDER=null` on the E2E environment. Never email dev-DB customers. Service agreement flow is OFF-LIMITS — do not click into it.
- **VALIDATE**: All screenshots captured, zero console errors, zero uncaught exceptions, DB rows match UI input, responsive layouts clean at all three viewports.

### Task 24 — Update `DEVLOG.md` (`devlog-rules.md`, `auto-devlog.md`)

- **IMPLEMENT**: Insert a new `FEATURE` entry at the TOP of `DEVLOG.md`, immediately after `## Recent Activity`. Follow the template in §PROJECT STEERING STANDARDS → DEVLOG discipline. Fill in actual commit SHAs, test counts, screenshots count, and any challenges hit during execution.
- **VALIDATE**: `head -30 DEVLOG.md` shows the new entry at the top with correct date, category, and all required sections (Accomplished / Technical Details / Decision Rationale / Challenges / Next Steps).

---

## TESTING STRATEGY

Project mandates three tiers of backend tests + property-based + frontend component/hook/form tests + agent-browser E2E (`code-standards.md`, `spec-testing-standards.md`). Coverage targets: **services 90%+, components 80%+, hooks 85%+, utils 90%+**.

### Unit Tests (backend) — `@pytest.mark.unit`, all mocked

- `test_customer_note_model.py` — model instantiation, FK resolution, `__repr__`, column constraints
- `test_customer_note_service.py` — CRUD paths, validation (body length 1–2000, customer-not-found), LoggerMixin event emission (start/complete/rejected/failed), no-PII-in-logs invariant
- `test_customer_note_api.py` — all endpoints with `app.dependency_overrides[get_customer_note_service]`; assert 200/201/204/400/404/422 paths, request_id correlation in logs (captured via `caplog`)
- `test_customer_note_pbt.py` — Hypothesis properties:
  - Body length invariant: len ∈ [1, 2000] accepts; outside rejects
  - List ordering: `list_by_customer` returns notes in reverse-chronological order for all generated orderings
  - Scope invariant: appointment-scoped note appears in both endpoints; profile-scoped appears only in customer endpoint

### Functional Tests (backend) — `@pytest.mark.functional`, real DB

- `test_customer_note_lifecycle_functional.py` — create customer → upload photo via `POST /appointments/{id}/photos` → verify `CustomerPhoto` row has `customer_id` + `appointment_id` + `job_id` all populated → create note via `POST /customers/{id}/notes` with appointment_id → verify visible from both `/customers/{id}/notes` and `/appointments/{id}/notes` → update note → delete note (verify row gone) → delete customer → verify cascade-delete wipes all notes and photos
- `test_review_request_unchanged_functional.py` — regression test confirming existing `POST /appointments/{id}/request-review` behavior is unchanged (consent gate, 30-day dedup)

### Integration Tests (backend) — `@pytest.mark.integration`, full system

- `test_customer_note_with_appointment_integration.py` — full modal flow simulation: appointment lookup → customer tags fetch → notes fetch → photo list fetch — all in one session; verifies no cross-feature regressions (notes + tags + photos + timeline all co-exist).

### Frontend Tests (Vitest + React Testing Library with QueryProvider wrapper, co-located)

- `PhotoSheet.test.tsx` — loading, error, empty, populated; upload happy path; 10MB/MIME rejection; gallery section split; invalidates correct query keys; 80%+ coverage
- `NotesSheet.test.tsx` — create/edit/delete; scope toggle behavior; form validation errors; optimistic rollback on mutation failure; Cmd/Ctrl+Enter submit; 80%+ coverage
- `ReviewConfirmSheet.test.tsx` — render preview, 409 "Already sent (date)" toast, 2xx sent:false consent path, disabled-for-non-completed, disabled-when-no-phone; 80%+ coverage
- `SecondaryActionsStrip.test.tsx` — active variants per open-sheet state; each button calls the correct handler
- `AppointmentModal.test.tsx` (update) — single-sheet exclusivity for the 3 new sheets; backdrop/ESC closes sheet
- `useCustomerNotes.test.tsx` (hook test, 85%+ coverage) — query keyed by customerId; optimistic create/update/delete; rollback; correct cache invalidation
- `JobForm.test.tsx` (update) — "Past site photos" section renders when customer_id is set; hidden when not; thumbnails call getPhotos

### Edge Cases

- Photo: customer with no photos yet, customer with 100+ photos (virtualization if needed), HEIC format on iOS, file picker cancelled
- Notes: concurrent edit (two tabs), optimistic insert then mutation fails, note body exactly at 2000-char limit, body with emoji
- Review: appointment never completed (button disabled), customer has no phone (button disabled), customer opted out (2xx sent=false path), 2nd send within 30 days (409 path), CallRail rate limit (fallback error toast)
- Modal: user clicks backdrop while PhotoSheet has pending upload → prompt to confirm close
- JobForm: customer has 0 photos (section hidden), customer_id cleared after selection (section also hidden)

---

## VALIDATION COMMANDS

Aligned with `tech.md` quality-gate command and `spec-testing-standards.md` tier markers. All levels must exit 0 before merge.

### Level 1: Syntax & Style (zero violations required — `code-standards.md`)

```bash
# Backend — single pipeline, all must exit 0
cd /Users/kirillrakitin/Grins_irrigation_platform
uv run ruff check --fix src/ && \
  uv run ruff format --check src/ && \
  uv run mypy src/ && \
  uv run pyright src/

# Frontend
cd frontend
npm run lint && npm run typecheck && npm run format:check
```

### Level 2: Unit Tests (all mocked, fastest)

```bash
# Backend — marker-scoped so only unit tests run
uv run pytest -m unit src/grins_platform/tests/unit/test_customer_note_model.py \
  src/grins_platform/tests/unit/test_customer_note_service.py \
  src/grins_platform/tests/unit/test_customer_note_api.py \
  src/grins_platform/tests/unit/test_customer_note_pbt.py -v

# Frontend
cd frontend
npm test -- PhotoSheet NotesSheet ReviewConfirmSheet SecondaryActionsStrip AppointmentModal useCustomerNotes JobForm
```

### Level 3: Functional + Integration Tests (real DB / full system)

```bash
# Backend functional (real DB)
uv run pytest -m functional src/grins_platform/tests/functional/test_customer_note_lifecycle_functional.py \
  src/grins_platform/tests/functional/test_review_request_unchanged_functional.py -v

# Backend integration
uv run pytest -m integration src/grins_platform/tests/integration/test_customer_note_with_appointment_integration.py -v

# Full suites (regression guard)
uv run pytest src/grins_platform/tests -q
cd frontend && npm run test:coverage  # enforces coverage targets
```

### Level 3b: Coverage gates (`spec-testing-standards.md`, `frontend-testing.md`)

```bash
# Backend: services 90%+, overall 80%+
uv run pytest --cov=src/grins_platform/services/customer_note_service \
  --cov=src/grins_platform/repositories/customer_note_repository \
  --cov-fail-under=90

# Frontend: components 80%+, hooks 85%+ (enforced by test:coverage config)
cd frontend && npm run test:coverage
```

### Level 4: Manual Validation

```bash
# Start backend
uv run uvicorn grins_platform.app:app --reload --host 0.0.0.0 --port 8000

# Start frontend (another terminal)
cd frontend && npm run dev
```

1. Login at http://localhost:5173 → Schedule tab → click any appointment chip
2. Click **Add photo** → upload a JPEG → verify toast + thumbnail appears in "This appointment" section
3. Close modal, open the same appointment again → verify photo persists in sheet
4. Navigate to the customer's detail page → verify photo appears in `PhotoGallery`
5. Click **Create new job** for the same customer → select them in JobForm → verify the thumbnail shows in "Past site photos"
6. Back to Schedule → open appointment → click **Notes** → add two notes (one "Appointment" scope, one "Profile") → close sheet → reopen → verify both appear with correct scope chips
7. Navigate to customer detail → verify both notes are visible under a notes section
8. Advance the appointment to `completed` (use Action Track) → click **Review** → verify message preview + consent status → click Send → toast "Review requested"
9. Click **Review** again → verify "Already sent within last 30 days" toast

### Level 5: Additional Validation

```bash
# E2E on Vercel (after deploy)
# Use the agent-browser skill — see Task 23
```

---

## ACCEPTANCE CRITERIA

### Feature correctness
- [ ] Add photo sheet: staff can upload photos that are visible on the appointment, on the customer detail page, and as thumbnails in JobForm for the same customer
- [ ] Notes sheet: staff can create/edit/delete notes; notes with appointment scope appear on the appointment AND bubble up to the customer; profile-scope notes only appear on the customer
- [ ] Review sheet: works only when appointment.status === 'completed'; shows accurate server-side message preview; handles 409 dedup with "Already sent" toast including the last-sent date; handles opt-out customers with a clear message
- [ ] Single-sheet exclusivity holds for all 6 sheets (payment, estimate, tags, photo, notes, review)
- [ ] `SecondaryActionsStrip` buttons show `active` variant when their sheet is open
- [ ] All new backend endpoints return 404 for missing customer/note, 400/422 for invalid payloads, 200/201/204 for success
- [ ] All new frontend mutations have optimistic updates with rollback on failure
- [ ] No regressions in existing `AppointmentModal.test.tsx`, `TagEditorSheet.test.tsx`, or backend customer/appointment test suites

### Steering-standard compliance
- [ ] Every new endpoint follows the `api-patterns.md` template: `set_request_id()` → DomainLogger events → `clear_request_id()` in `finally`
- [ ] Every new service inherits `LoggerMixin`, sets `DOMAIN = "customer_notes"`, and emits `_started` / `_completed` / `_rejected` / `_failed` events per `code-standards.md`
- [ ] Event names follow `{domain}.{component}.{action}_{state}` pattern
- [ ] No PII / tokens / note bodies appear in any log context
- [ ] Every new test file carries the correct marker: `@pytest.mark.unit` / `@pytest.mark.functional` / `@pytest.mark.integration`
- [ ] Property-based tests cover: body length invariant, list ordering, scope invariant
- [ ] Every new frontend element has a `data-testid` following the `{feature}-{role}` / `{action}-{feature}-btn` conventions
- [ ] All new React Query hooks wrap consumers in QueryProvider during tests
- [ ] VSA boundaries respected: `features/schedule/*` imports only from `core/`, `shared/`, or via another feature's public `index.ts`

### Quality gates
- [ ] `uv run ruff check src/` — zero violations
- [ ] `uv run ruff format --check src/` — zero differences
- [ ] `uv run mypy src/` — zero errors
- [ ] `uv run pyright src/` — zero errors
- [ ] `cd frontend && npm run lint` — zero errors
- [ ] `cd frontend && npm run typecheck` — zero errors
- [ ] Backend services coverage 90%+, hooks 85%+, components 80%+
- [ ] API p95 latency unchanged or improved for affected endpoints (<200ms per `tech.md`)
- [ ] E2E flow on Vercel deploys successfully, all screenshots captured across 3 viewports, zero console errors
- [ ] `DEVLOG.md` updated with a new FEATURE entry at the top

---

## COMPLETION CHECKLIST

- [ ] Phase 0 (§Decision Required) confirmed with user
- [ ] All 24 tasks completed in order (parallel phases respected per §Parallel execution opportunities)
- [ ] Each task's validation passed before moving on
- [ ] Backend suites green: `uv run pytest -m unit` + `uv run pytest -m functional` + `uv run pytest -m integration`
- [ ] Coverage gates met: services 90%+, components 80%+, hooks 85%+
- [ ] Backend quality gate: `uv run ruff check --fix src/ && uv run ruff format --check src/ && uv run mypy src/ && uv run pyright src/` all exit 0
- [ ] Frontend quality gate: `npm run typecheck && npm run lint && npm run format:check && npm run test:coverage` all exit 0
- [ ] Manual smoke test from §Level 4 passed
- [ ] E2E screenshots in `e2e-screenshots/appointment-modal-secondary-actions/` at 3 viewports (375×812, 768×1024, 1440×900)
- [ ] `agent-browser console` and `agent-browser errors` clean during manual validation
- [ ] Every new frontend element has a `data-testid` per convention
- [ ] Every new service emits LoggerMixin events (grep `log_started` in new files)
- [ ] Every new endpoint sets/clears `request_id` (grep `set_request_id` / `clear_request_id`)
- [ ] `DEVLOG.md` updated with a new FEATURE entry at the top
- [ ] Conventional commit pattern used: `feat(appointment-modal): photos + notes + review secondary actions`

---

## NOTES

### Why we're NOT rebuilding the old components

`AppointmentNotes.tsx` and `ReviewRequest.tsx` exist at `frontend/src/features/schedule/components/` and were wired into the previous `AppointmentDetail.tsx` page. They use shadcn `Button`, `Textarea` (slate-50 rounded-xl backgrounds) and won't visually match the new modal's 560px white-bg design-token system. We keep those files alone (they may still be referenced in tests) and build three new sheets from scratch using `SheetContainer` + design tokens. Their hooks (`useUploadAppointmentPhotos`, `useRequestReview`, `useUpdateAppointment`) are fully reusable and unchanged.

### Why we chose appointment-scoped dedup for photos (not notes)

The backend photo upload endpoint stores each upload as a new `CustomerPhoto` row — there's no natural uniqueness constraint (a customer can legitimately have many photos of the same feature). Notes are similar: many notes per customer is the feature. The only dedup concern is the Review SMS, which the backend already handles with a 30-day window.

### Why server-side review preview (Task 17 GOTCHA §3)

Hardcoding the review message in the frontend risks drift whenever the backend template changes. Adding `GET /appointments/{id}/review-preview` that returns the exact composed string (including personalization like customer name, business name, Google link) is 10 lines of backend code and eliminates a class of bugs. If the execution agent hits time pressure, a contract test that pins both sides to a shared fixture is an acceptable fallback.

### Memory / environmental constraints

- Real SMS during testing only to `+19527373312` (user feedback memory). Set `SMS_PROVIDER=null` for E2E or use the test phone.
- Never email dev-DB customers (user feedback memory). Not relevant to this feature (SMS only), but keep in mind if acceptance testing incidentally triggers email confirms.
- CallRail is the default provider (per README §SMS Provider Swap). Twilio swap is zero-code at env level; no code changes in this feature should assume a specific provider.

### Confidence score: 8/10 for one-pass implementation success

Points withheld because: (1) Option A vs B decision must be made before Task 1 — a misaligned choice would mean rework; (2) server review-preview endpoint is strictly better than duplicating the template but is an additional scope decision; (3) `JobForm` integration is the least-specified piece and may surface unexpected form-state coupling. Everything else follows crisp existing patterns (CustomerTag infrastructure is a near-perfect mirror for CustomerNote).
