# Implementation Plan: Appointment Modal V2

## Overview

This plan implements three targeted v2 enhancements to the existing fully-implemented appointment modal: (1) an inline "See attached photos" expansion panel with upload CTAs reusing existing customer photo infrastructure, (2) an inline "See attached notes" expansion panel backed by a new `appointment_notes` table with upsert API, and (3) renaming "Review" to "Send Review Request". All changes are additive — no existing functionality is modified or removed.

**Phase ordering:** Backend (migration → model → schemas → repository → service → API endpoints) → Backend tests (unit → functional → integration) → Frontend (V2LinkBtn → PhotosPanel/PhotoCard → NotesPanel → SecondaryActionsStrip update → useModalState extension → useAppointmentNotes hooks → AppointmentModal wiring) → Frontend tests (component unit → hook tests) → PBT (backend Hypothesis + frontend fast-check) → Linting (Ruff/MyPy/Pyright + ESLint/TypeScript) → E2E (Vercel deploy + agent-browser validation).

## Tasks

- [x] 1. Backend: Database migration and AppointmentNote model
  - [x] 1.1 Create Alembic migration for `appointment_notes` table
    - Create `src/grins_platform/migrations/versions/YYYYMMDD_100000_add_appointment_notes_table.py`
    - Table columns: `id` (UUID PK, default `gen_random_uuid()`), `appointment_id` (UUID FK → `appointments.id` ON DELETE CASCADE, UNIQUE, NOT NULL), `body` (TEXT NOT NULL, default empty string), `updated_at` (TIMESTAMPTZ NOT NULL, default `now()`), `updated_by_id` (UUID FK → `staff.id` ON DELETE SET NULL, nullable)
    - Add unique index `idx_appointment_notes_appointment_id` on `appointment_id`
    - _Requirements: 5.1, 5.2_

  - [x] 1.2 Create AppointmentNote SQLAlchemy model
    - Create `src/grins_platform/models/appointment_note.py` with all columns, constraints, and relationships to Appointment and Staff
    - Register model in `models/__init__.py`
    - Use `mapped_column` style consistent with existing models (e.g., `customer_tag.py`)
    - _Requirements: 5.1, 5.2_

  - [x] 1.3 Create Pydantic schemas for appointment notes
    - Create `src/grins_platform/schemas/appointment_note.py`
    - Define `NoteAuthorResponse` (id, name, role), `AppointmentNotesResponse` (appointment_id, body, updated_at, updated_by), `AppointmentNotesSaveRequest` (body with max_length=50_000)
    - Use `ConfigDict(from_attributes=True)` for ORM compatibility
    - _Requirements: 5.3, 5.6, 10.1, 10.5_

- [x] 2. Backend: Repository, service, and API endpoints for appointment notes
  - [x] 2.1 Create AppointmentNoteRepository
    - Create `src/grins_platform/repositories/appointment_note_repository.py`
    - Methods: `get_by_appointment_id(appointment_id) → AppointmentNote | None`, `upsert(appointment_id, body, updated_by_id) → AppointmentNote`
    - Use async SQLAlchemy session pattern consistent with existing repositories (e.g., `customer_tag_repository.py`)
    - _Requirements: 5.3, 5.5_

  - [x] 2.2 Create AppointmentNoteService
    - Create `src/grins_platform/services/appointment_note_service.py`
    - Methods: `get_notes(appointment_id) → AppointmentNotesResponse` (returns empty body if no record), `save_notes(appointment_id, body, updated_by_id) → AppointmentNotesResponse`
    - Use `LoggerMixin` with `DOMAIN = "appointment_notes"`
    - Log started/completed/failed events for get and save operations
    - Validate appointment exists before operations (raise 404 if not found)
    - _Requirements: 5.3, 5.4, 5.5, 5.7, 10.2, 10.4_

  - [x] 2.3 Add notes endpoints to appointments API
    - Extend `src/grins_platform/api/v1/appointments.py` with:
      - `GET /api/v1/appointments/{appointment_id}/notes` → returns `AppointmentNotesResponse` (200 OK)
      - `PATCH /api/v1/appointments/{appointment_id}/notes` → accepts `AppointmentNotesSaveRequest`, returns updated `AppointmentNotesResponse` (200 OK)
    - Handle 404 (appointment not found), 422 (body exceeds 50,000 chars), 401 (unauthenticated)
    - Set `updated_by_id` to current authenticated user's staff ID on PATCH
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6_

- [x] 3. Checkpoint — Backend notes infrastructure complete
  - Ensure migration, model, schemas, repository, service, and API endpoints compile without errors. Ask the user if questions arise.

- [x] 4. Backend: Unit tests for appointment notes
  - [x] 4.1 Write unit tests for AppointmentNote model and service
    - Create `src/grins_platform/tests/unit/test_appointment_note_service.py`
    - Test model creation, field defaults (empty body), relationship to Appointment
    - Test `get_notes` with existing record and with no record (returns empty body)
    - Test `save_notes` for create-new and update-existing scenarios
    - Test body length validation (≤ 50,000 accepted, > 50,000 rejected)
    - Test `updated_by_id` tracking on save
    - _Requirements: 14.1, 14.2_

  - [x] 4.2 Write unit tests for notes API endpoints
    - Create `src/grins_platform/tests/unit/test_appointment_note_api.py`
    - Test GET: existing notes, no notes (empty body response), invalid appointment → 404
    - Test PATCH: create new notes, update existing, body validation → 422, auth required → 401
    - _Requirements: 14.3_

- [x] 5. Backend: Functional tests for notes lifecycle
  - [x] 5.1 Write functional tests for notes lifecycle
    - Create `src/grins_platform/tests/functional/test_appointment_notes_functional.py`
    - Test: create appointment → save notes → read → update notes → read → verify body changed and `updated_by` updated
    - Test: cascade delete — create appointment with notes → delete appointment → verify notes are gone
    - Test: upsert creates on first save — new appointment → PATCH notes → verify record created
    - Test: empty body allowed — PATCH with empty string body → verify accepted and stored
    - _Requirements: 14.4_

- [x] 6. Backend: Integration tests for notes
  - [x] 6.1 Write integration tests for notes accessibility
    - Create `src/grins_platform/tests/integration/test_appointment_notes_integration.py`
    - Test: create appointment → save notes → verify notes data is accessible from appointment context
    - Test: PATCH without auth → verify 401
    - _Requirements: 14.5_

- [x] 7. Checkpoint — Backend tests complete
  - Ensure all backend unit, functional, and integration tests pass with zero failures. Ask the user if questions arise.

- [x] 8. Frontend: V2LinkBtn component
  - [x] 8.1 Create V2LinkBtn component
    - Create `frontend/src/features/schedule/components/AppointmentModal/V2LinkBtn.tsx`
    - Inline-flex button: min-height 44px, padding `0 12px`, border-radius 12px, border `1.5px solid #E5E7EB`, font 14px / weight 700
    - Props: `children`, `icon` (ReactNode), `accent` (`'blue' | 'amber'`), `open` (boolean), `count?` (number), `onClick`, `aria-label?`
    - Closed state: white bg, `#374151` text, `#E5E7EB` border
    - Open state accent map: blue (`#DBEAFE` bg / `#1D4ED8` color+border), amber (`#FEF3C7` bg / `#B45309` color+border)
    - Count badge pill: border-radius 999px, font 11.5px / weight 800 / mono, min-width 20px. Open: accent bg + white text. Closed: `#F3F4F6` bg + `#4B5563` text
    - Trailing chevron: 14px, stroke-width 2.4, points down when closed / up when open, accent color when open / `#6B7280` when closed
    - `aria-expanded` attribute reflecting open/closed state
    - Activatable via Enter and Space keys
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 12.1, 12.6_

- [x] 9. Frontend: PhotosPanel and PhotoCard components
  - [x] 9.1 Create PhotoCard component
    - Create `frontend/src/features/schedule/components/AppointmentModal/PhotoCard.tsx`
    - 180px wide card, 134px image area, `1.5px` border `#E5E7EB`, border-radius 12px
    - `<img>` tag with `object-fit: cover` for the image area
    - Caption row: 12px / weight 700 caption + 10.5px / weight 600 / mono date
    - Focusable via Tab for keyboard navigation
    - _Requirements: 4.7, 12.4_

  - [x] 9.2 Create PhotosPanel component
    - Create `frontend/src/features/schedule/components/AppointmentModal/PhotosPanel.tsx`
    - Props: `customerId`, `appointmentId`, `jobId?`
    - Panel container: margin-top 10px, border-radius 14px, `1.5px` border `#1D4ED8`, white bg
    - Header bar: `#DBEAFE` bg, padding `10px 14px`, photo icon (16px, blue), "Attached photos" label (13px / weight 800, blue), count chip (border-radius 999px, `#1D4ED8` bg, white text, 11.5px / weight 800 / mono), right-aligned "From customer file" label (11.5px / weight 700, blue, opacity 0.85)
    - Upload CTAs row: white bg, padding 12px, bottom border, 8px gap
      - Primary "Upload photo · camera roll": flex-1, min-height 48px, `#1D4ED8` bg, white text, border-radius 12px, upload icon. "· camera roll" suffix in mono 11.5px, opacity 0.9. Triggers `<input type="file" accept="image/*" multiple />`
      - Secondary "Take photo": white bg, `1.5px` blue border, blue text, camera icon, border-radius 12px. Triggers `<input type="file" accept="image/*" capture="environment" />`
    - Photo strip: horizontal scroll, padding 12px, gap 10px, `-webkit-overflow-scrolling: touch`, renders PhotoCard × N
    - Trailing "Add more · From library" tile: 110px wide, dashed `1.5px` border, `#F9FAFB` bg, plus icon, triggers same file picker as "Upload photo"
    - Footer: `#F9FAFB` bg, padding `8px 14px 10px`, top border. Left: hint text (11.5px / weight 700, `#6B7280`). Right: "View all (N)" outlined button (padding `6px 10px`, border-radius 8px, `1.5px` border `#E5E7EB`, 12px / weight 800)
    - Fetch photos from existing `useCustomerPhotos(customerId)` hook (from `@/features/customers`)
    - Upload via existing `useUploadCustomerPhotos(customerId)` hook with optimistic placeholder cards showing progress, revert on error
    - Accessible labels on upload buttons
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 4.9, 4.10, 4.11, 4.12, 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 11.4, 11.5, 11.7, 11.8, 12.5_

- [x] 10. Frontend: NotesPanel component
  - [x] 10.1 Create NotesPanel component
    - Create `frontend/src/features/schedule/components/AppointmentModal/NotesPanel.tsx`
    - Props: `appointmentId`, `editing` (boolean), `onSetEditing` (callback)
    - Panel container: margin-top 10px, border-radius 14px, `1.5px` border `#E5E7EB`, white bg, shadow `0 1px 2px rgba(10,15,30,0.04)`
    - Header: padding `18px 20px 14px`, "INTERNAL NOTES" eyebrow (12.5px / weight 800 / 1.4px tracking / uppercase, color `#64748B`), right-aligned "Edit" affordance (pencil icon + "Edit" text, 14px / weight 700, color `#64748B`, transparent bg, no border) — visible only in view mode
    - View mode: padding `0 20px 22px`, body text (14.5px / weight 500 / 1.6 line-height, color `#0B1220`, min-height 80px)
    - Edit mode: full-width textarea (min-height 150px, padding `12px 14px`, border-radius 12px, `1.5px` border `#E5E7EB`, font 14.5px / weight 500 / 1.5 line-height, `resize: vertical`, `outline: none`), pre-filled with current body, cursor at end
    - Button row below textarea (margin-top 14px, gap 12px, justify-end): "Cancel" (white bg, `1.5px` border `#E5E7EB`, color `#1F2937`, padding `12px 28px`, border-radius 999px, 15px / weight 700, min-width 120px) and "Save Notes" (teal `#14B8A6` bg+border, white text, padding `12px 28px`, border-radius 999px, 15px / weight 700, min-width 140px)
    - Escape key cancels editing, `⌘+Enter` / `Ctrl+Enter` saves
    - Save calls `useSaveAppointmentNotes` mutation, optimistic update, return to view mode on success, error toast + stay in edit mode on failure
    - Cancel discards local changes, returns to view mode
    - Fetch notes via `useAppointmentNotes(appointmentId)` hook
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8, 6.9, 6.10, 6.11, 11.2, 11.3, 12.2, 12.3_

- [x] 11. Frontend: Update SecondaryActionsStrip and useModalState
  - [x] 11.1 Update SecondaryActionsStrip for v2
    - Modify `frontend/src/features/schedule/components/AppointmentModal/SecondaryActionsStrip.tsx`
    - Replace "Add photo" LinkButton with V2LinkBtn "See attached photos" (blue accent, Image icon, count badge = photo count, chevron)
    - Replace "Notes" LinkButton with V2LinkBtn "See attached notes" (amber accent, FileText icon, count badge = 1 if notes exist / 0 if not, chevron)
    - Rename "Review" to "Send Review Request"
    - Keep "Edit tags" LinkButton unchanged
    - Update props interface: add `photosOpen`, `notesOpen`, `photoCount`, `noteCount`, `onTogglePhotos`, `onToggleNotes`
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7_

  - [x] 11.2 Extend useModalState hook for v2
    - Modify `frontend/src/features/schedule/hooks/useModalState.ts`
    - Add `openPanel` state: `'photos' | 'notes' | null` (default `null`)
    - Add `editingNotes` state: `boolean` (default `false`)
    - Add `togglePanel(panel: 'photos' | 'notes')` function: toggles specified panel, closes other panel, closes any open sheet
    - Add `setEditingNotes(editing: boolean)` function
    - Mutual exclusivity: opening a panel closes any open sheet; opening a sheet closes any open panel
    - Auto-reset: `editingNotes` resets to `false` whenever `openPanel` changes away from `'notes'`
    - Update `openSheetExclusive` to also close any open panel
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6_

- [x] 12. Frontend: useAppointmentNotes hooks
  - [x] 12.1 Create useAppointmentNotes and useSaveAppointmentNotes hooks
    - Create `frontend/src/features/schedule/hooks/useAppointmentNotes.ts`
    - `useAppointmentNotes(appointmentId)`: TanStack Query hook for `GET /appointments/:id/notes`, returns `AppointmentNotesResponse`, default empty body for missing/404
    - `useSaveAppointmentNotes()`: TanStack mutation for `PATCH /appointments/:id/notes { body }`, optimistic update on notes query cache, invalidate on success, revert on failure
    - Define query key factory: `appointmentNoteKeys.detail(appointmentId)`
    - Export from `frontend/src/features/schedule/hooks/index.ts`
    - _Requirements: 8.1, 8.2, 8.3, 8.4_

- [x] 13. Frontend: Wire v2 panels into AppointmentModal
  - [x] 13.1 Wire PhotosPanel, NotesPanel, and updated SecondaryActionsStrip into AppointmentModal
    - Modify `frontend/src/features/schedule/components/AppointmentModal/AppointmentModal.tsx`
    - Import and use extended `useModalState` (with `openPanel`, `editingNotes`, `togglePanel`, `setEditingNotes`)
    - Import `useCustomerPhotos` from `@/features/customers` for photo count
    - Import `useAppointmentNotes` for note count
    - Pass `photosOpen`, `notesOpen`, `photoCount`, `noteCount`, `onTogglePhotos`, `onToggleNotes` to SecondaryActionsStrip
    - Render PhotosPanel conditionally when `openPanel === 'photos'` (below SecondaryActionsStrip, before PaymentEstimateCTAs)
    - Render NotesPanel conditionally when `openPanel === 'notes'` (below SecondaryActionsStrip, before PaymentEstimateCTAs)
    - Pass `editing={editingNotes}` and `onSetEditing={setEditingNotes}` to NotesPanel
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

- [x] 14. Checkpoint — Frontend v2 components assembled
  - Ensure all new components compile without TypeScript errors and the modal renders correctly. Ask the user if questions arise.

- [x] 15. Frontend: Unit tests for new v2 components
  - [x] 15.1 Write unit tests for V2LinkBtn
    - Create `frontend/src/features/schedule/components/AppointmentModal/V2LinkBtn.test.tsx`
    - Test: default (closed) state rendering — white bg, correct text color, chevron down
    - Test: open state with blue accent — `#DBEAFE` bg, `#1D4ED8` text/border, chevron up
    - Test: open state with amber accent — `#FEF3C7` bg, `#B45309` text/border, chevron up
    - Test: count badge display — open style (accent bg, white text) vs closed style (`#F3F4F6` bg, `#4B5563` text)
    - Test: `aria-expanded` attribute reflects open/closed state
    - Test: click handler fires on click, Enter, and Space
    - _Requirements: 13.1_

  - [x] 15.2 Write unit tests for PhotosPanel
    - Create `frontend/src/features/schedule/components/AppointmentModal/PhotosPanel.test.tsx`
    - Test: header rendering (icon, "Attached photos" label, count chip, "From customer file")
    - Test: upload CTA buttons present with correct labels and attributes (`accept="image/*"`, `multiple`, `capture="environment"`)
    - Test: photo strip renders PhotoCard components for each photo
    - Test: "Add more · From library" trailing tile present
    - Test: footer with hint text and "View all (N)" button
    - Test: file input triggers on button click
    - _Requirements: 13.2_

  - [x] 15.3 Write unit tests for NotesPanel
    - Create `frontend/src/features/schedule/components/AppointmentModal/NotesPanel.test.tsx`
    - Test: view mode — "INTERNAL NOTES" eyebrow, body text, Edit affordance visible
    - Test: edit mode transition — textarea pre-filled with current body, cursor at end
    - Test: Cancel discards changes and returns to view mode
    - Test: Save Notes triggers mutation
    - Test: Escape key cancels editing
    - Test: `⌘+Enter` / `Ctrl+Enter` saves notes
    - Test: error toast on save failure, remains in edit mode with draft preserved
    - _Requirements: 13.3_

  - [x] 15.4 Write unit tests for updated SecondaryActionsStrip
    - Create or update `frontend/src/features/schedule/components/AppointmentModal/SecondaryActionsStrip.test.tsx`
    - Test: four buttons present — "See attached photos" (V2LinkBtn), "See attached notes" (V2LinkBtn), "Send Review Request" (LinkButton), "Edit tags" (LinkButton)
    - Test: V2LinkBtn for photos shows correct count badge
    - Test: V2LinkBtn for notes shows correct count badge (1 or 0)
    - Test: "Send Review Request" text (not "Review")
    - Test: panel toggle callbacks fire correctly
    - _Requirements: 13.4_

  - [x] 15.5 Write unit tests for extended useModalState hook
    - Create or update `frontend/src/features/schedule/hooks/useModalState.test.ts`
    - Test: initial state — `openPanel: null`, `editingNotes: false`
    - Test: `togglePanel('photos')` opens photos, toggles off on second call
    - Test: `togglePanel('notes')` opens notes, closes photos if open
    - Test: panel mutual exclusivity — only one panel open at a time
    - Test: `editingNotes` auto-resets to `false` when `openPanel` changes away from `'notes'`
    - Test: sheet-panel mutual exclusivity — opening sheet closes panel, opening panel closes sheet
    - Test: `setEditingNotes` function works correctly
    - _Requirements: 13.5_

  - [x] 15.6 Write unit tests for useAppointmentNotes hooks
    - Create `frontend/src/features/schedule/hooks/useAppointmentNotes.test.ts`
    - Test: `useAppointmentNotes` query key structure and fetch on mount
    - Test: default empty body for missing notes
    - Test: `useSaveAppointmentNotes` mutation call and cache invalidation on success
    - Test: optimistic update and revert on failure
    - _Requirements: 13.5_

- [x] 16. Checkpoint — Frontend unit tests complete
  - Ensure all frontend unit tests pass with zero failures. Ask the user if questions arise.

- [x] 17. Property-based tests (Backend — Hypothesis)
  - [x] 17.1 Write PBT for notes body round-trip (Property 1)
    - **Property 1: Notes body round-trip**
    - **Validates: Requirements 5.5, 10.3, 15.1**
    - Add to `src/grins_platform/tests/unit/test_pbt_appointment_modal_v2.py`
    - Generate random strings (0–50,000 chars, including unicode, newlines, special chars) via `hypothesis.strategies.text(max_size=50_000)`
    - PATCH then GET, verify body matches exactly
    - Minimum 100 iterations

  - [x] 17.2 Write PBT for notes upsert idempotence (Property 2)
    - **Property 2: Notes upsert idempotence**
    - **Validates: Requirements 15.2**
    - Add to `src/grins_platform/tests/unit/test_pbt_appointment_modal_v2.py`
    - Generate random body string, save twice, verify `R1.body == R2.body`
    - Minimum 100 iterations

  - [x] 17.3 Write PBT for notes body validation rejects oversized input (Property 3)
    - **Property 3: Notes body validation rejects oversized input**
    - **Validates: Requirements 5.6, 10.5, 15.3**
    - Add to `src/grins_platform/tests/unit/test_pbt_appointment_modal_v2.py`
    - Generate strings with length 50,001–100,000 via `hypothesis.strategies.text(min_size=50_001, max_size=100_000)`
    - PATCH, verify 422 response and existing record unchanged
    - Minimum 100 iterations

- [x] 18. Property-based tests (Frontend — fast-check)
  - [x] 18.1 Write PBT for panel mutual exclusivity (Property 4)
    - **Property 4: Panel mutual exclusivity**
    - **Validates: Requirements 2.4, 2.5, 3.5, 15.4**
    - Add to `frontend/src/features/schedule/hooks/useModalState.pbt.test.ts`
    - Generate random sequences of `togglePanel('photos')` and `togglePanel('notes')` calls via `fc.array(fc.oneof(fc.constant('photos'), fc.constant('notes')))`
    - After each call, verify at most one panel is open
    - Verify toggle-same-twice returns to null

  - [x] 18.2 Write PBT for editingNotes auto-reset invariant (Property 5)
    - **Property 5: editingNotes auto-reset invariant**
    - **Validates: Requirements 3.6, 7.3, 15.5**
    - Add to `frontend/src/features/schedule/hooks/useModalState.pbt.test.ts`
    - Generate random sequences of `togglePanel`, `openSheetExclusive`, `setEditingNotes(true)` calls
    - After each transition, verify: if `openPanel !== 'notes'` then `editingNotes === false`

  - [x] 18.3 Write PBT for sheet-panel mutual exclusivity (Property 6)
    - **Property 6: Sheet-panel mutual exclusivity**
    - **Validates: Requirements 7.4, 7.5**
    - Add to `frontend/src/features/schedule/hooks/useModalState.pbt.test.ts`
    - Generate random sequences of `openSheetExclusive` and `togglePanel` calls
    - After each call, verify `openSheet` and `openPanel` are never both non-null simultaneously

  - [x] 18.4 Write PBT for V2LinkBtn accent map correctness (Property 7)
    - **Property 7: V2LinkBtn accent map correctness**
    - **Validates: Requirements 1.3, 1.5, 11.1**
    - Add to `frontend/src/features/schedule/components/AppointmentModal/V2LinkBtn.pbt.test.tsx`
    - Generate all combinations of accent (`'blue'`, `'amber'`) × open (`true`, `false`) via `fc.record({ accent: fc.oneof(fc.constant('blue'), fc.constant('amber')), open: fc.boolean() })`
    - Render V2LinkBtn, verify correct background, text color, border color, and badge styling for each combination

- [x] 19. Checkpoint — All property-based tests pass
  - Ensure all backend Hypothesis and frontend fast-check property tests pass with zero failures. Ask the user if questions arise.

- [x] 20. Linting and type checking
  - [x] 20.1 Backend linting and type checking
    - Run `uv run ruff check --fix src/grins_platform/models/appointment_note.py src/grins_platform/schemas/appointment_note.py src/grins_platform/repositories/appointment_note_repository.py src/grins_platform/services/appointment_note_service.py`
    - Run `uv run ruff format` on all new backend files
    - Run `uv run mypy` on all new backend files — zero type errors
    - Run `uv run pyright` on all new backend files — zero type errors
    - _Requirements: 16.1, 16.2_

  - [x] 20.2 Frontend linting and type checking
    - Run ESLint on all new frontend files (V2LinkBtn, PhotoCard, PhotosPanel, NotesPanel, updated SecondaryActionsStrip, updated useModalState, useAppointmentNotes) — zero errors
    - Run TypeScript strict mode compilation (`npx tsc --noEmit`) — zero errors on new files
    - _Requirements: 16.3, 16.4_

- [x] 21. Checkpoint — All linting and type checks pass
  - Ensure Ruff, MyPy, Pyright, ESLint, and TypeScript all pass with zero errors. Ask the user if questions arise.

- [-] 22. E2E: Deploy to Vercel and validate with agent-browser
  - [-] 22.1 Deploy frontend to Vercel
    - Run Vercel deployment and wait for successful build
    - Verify deployment URL is accessible
    - _Requirements: 17.1_

  - [~] 22.2 Validate photos panel via agent-browser
    - Navigate to schedule → open appointment modal → tap "See attached photos"
    - Verify panel opens with header, upload CTAs, photo strip
    - Verify chevron flips up on the V2LinkBtn
    - Verify notes panel is closed
    - Screenshot to `e2e-screenshots/appointment-modal-v2/photos-panel.png`
    - _Requirements: 17.2_

  - [~] 22.3 Validate notes panel via agent-browser
    - Tap "See attached notes" → verify panel opens with "INTERNAL NOTES" eyebrow and Edit affordance
    - Tap Edit → verify textarea appears with Cancel and Save Notes buttons
    - Verify photos panel is closed
    - Screenshot to `e2e-screenshots/appointment-modal-v2/notes-panel.png`
    - _Requirements: 17.3_

  - [~] 22.4 Validate mutual exclusivity via agent-browser
    - Open photos panel → tap "See attached notes" → verify photos closes and notes opens
    - Screenshot to `e2e-screenshots/appointment-modal-v2/mutual-exclusivity.png`
    - _Requirements: 17.5_

  - [~] 22.5 Validate "Send Review Request" label via agent-browser
    - Verify "Send Review Request" label is displayed (not "Review")
    - Screenshot to `e2e-screenshots/appointment-modal-v2/send-review-request.png`
    - _Requirements: 17.4_

  - [~] 22.6 Validate responsive behavior via agent-browser
    - Set viewport to 375×812 → verify panels render correctly in mobile bottom sheet
    - Screenshot to `e2e-screenshots/appointment-modal-v2/mobile-responsive.png`

  - [~] 22.7 Check for JavaScript errors via agent-browser
    - Run `agent-browser console` and `agent-browser errors` during all v2 interactions
    - Verify zero JS errors and uncaught exceptions
    - _Requirements: 17.6_

- [ ] 23. Final checkpoint — All tests pass, feature complete
  - Ensure all tests (unit, functional, integration, property-based, linting, type checking, and E2E) pass with zero failures before the feature is considered complete.
  - _Requirements: 17.7_

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation between major phases
- Property tests validate universal correctness properties from the design document (Properties 1–7)
- Unit tests validate specific examples and edge cases
- Backend must be completed before frontend notes hooks can be wired (tasks 1–7 before 12)
- Frontend V2LinkBtn (task 8) must exist before SecondaryActionsStrip update (task 11.1)
- PhotosPanel and NotesPanel (tasks 9–10) must exist before AppointmentModal wiring (task 13)
- useModalState extension (task 11.2) and useAppointmentNotes hooks (task 12) must exist before wiring (task 13)
- Photos panel reuses existing `useCustomerPhotos` and `useUploadCustomerPhotos` hooks from `@/features/customers` — no new backend work for photos
- E2E testing (task 22) requires all code changes to be complete and deployed
- The existing modal structure, v1 functionality, and all sheet overlays remain unchanged
