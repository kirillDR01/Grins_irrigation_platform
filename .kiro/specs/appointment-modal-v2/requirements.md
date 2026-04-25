# Requirements Document: Appointment Modal V2

## Introduction

This document specifies the requirements for the **Appointment Modal V2** — three targeted enhancements to the existing fully-implemented appointment modal (`appointment-modal-combined` spec, all tasks complete). The v2 enhancements come from a design handoff and add: (1) an inline "See attached photos" expansion panel with upload CTAs, (2) an inline "See attached notes" expansion panel replacing the old multi-author thread with a single centralized Internal Notes body, and (3) renaming the "Review" button to "Send Review Request". The existing modal structure, backend, and all v1 functionality remain intact — v2 is purely additive.

## Glossary

- **V2LinkBtn**: A new variant of the secondary action button that supports an `open` state with accent tinting, a count badge, and a rotating chevron indicator. Replaces the v1 `LinkButton` for the photos and notes actions.
- **Photos_Panel**: An inline expansion panel rendered below the secondary action row showing customer photos across all jobs, with upload CTAs (camera roll + take photo) and a horizontal scrolling photo strip.
- **Notes_Panel**: An inline expansion panel rendered below the secondary action row showing a single centralized Internal Notes body with view and edit modes. Replaces the v1 multi-author thread pattern.
- **Appointment_Notes**: The data model for per-appointment internal notes: `{ appointmentId, body, updatedAt, updatedBy: { id, name, role } }`.
- **Open_Panel**: A mutually exclusive state variable (`'photos' | 'notes' | null`) controlling which inline expansion panel is visible. Opening one closes the other.
- **Photo_Strip**: A horizontally scrolling row of photo cards (180 px wide, 134 px image area) inside the Photos_Panel.
- **SecondaryActionsStrip**: The row of action buttons below the Action Track, upgraded in v2 to include V2LinkBtn buttons for photos and notes.
- **Modal**: The existing `AppointmentModal` component from the v1 spec.
- **Customer_Photo**: The existing `CustomerPhoto` model representing photos linked to a customer, with optional `appointment_id` and `job_id` associations.
- **Design_Tokens**: The authoritative color, typography, spacing, and radius values defined in the v2 design handoff README §Design Tokens.

## Requirements

### Requirement 1: V2LinkBtn Component

**User Story:** As a developer, I want a reusable V2LinkBtn component that supports open/closed states with accent tinting, count badges, and chevron rotation, so that the photos and notes buttons match the v2 design spec.

#### Acceptance Criteria

1. THE V2LinkBtn SHALL render as an inline-flex button with min-height 44 px, padding `0 12px`, border-radius 12 px, border `1.5px solid #E5E7EB`, font 14 px / weight 700, and a 16 px icon with stroke-width 2.2.
2. WHEN the `open` prop is false, THE V2LinkBtn SHALL render with white background, `#374151` text color, and `#E5E7EB` border.
3. WHEN the `open` prop is true, THE V2LinkBtn SHALL render with the accent-tinted background, accent text color, and accent border color per the accent map: blue (`#DBEAFE` bg / `#1D4ED8` color+border), amber (`#FEF3C7` bg / `#B45309` color+border).
4. WHEN a `count` prop is provided, THE V2LinkBtn SHALL display a count badge pill (border-radius 999 px, font 11.5 px / weight 800 / mono font, min-width 20 px, centered text) after the label text.
5. WHEN the button is open, THE V2LinkBtn count badge SHALL render with the accent color background and white text; when closed, with `#F3F4F6` background and `#4B5563` text.
6. THE V2LinkBtn SHALL display a trailing chevron icon (14 px, stroke-width 2.4) that points down when closed and up when open, using the accent color when open and `#6B7280` when closed.

### Requirement 2: Secondary Actions Strip V2 Upgrade

**User Story:** As a staff member, I want the secondary action row to show "See attached photos" and "See attached notes" with count badges and inline expansion behavior, and "Send Review Request" instead of "Review", so that I can access v2 features directly from the modal.

#### Acceptance Criteria

1. THE SecondaryActionsStrip SHALL display four buttons: "See attached photos" (V2LinkBtn, blue accent, image icon), "See attached notes" (V2LinkBtn, amber accent, file-text icon), "Send Review Request" (LinkButton, star icon), and "Edit tags" (LinkButton, tag icon).
2. THE "See attached photos" V2LinkBtn SHALL display the count of customer photos as its count badge.
3. THE "See attached notes" V2LinkBtn SHALL display a count badge of `1` when notes exist for the appointment, or `0` when no notes exist.
4. WHEN the user taps "See attached photos", THE Modal SHALL toggle the Photos_Panel open (or closed if already open) and close the Notes_Panel if it was open.
5. WHEN the user taps "See attached notes", THE Modal SHALL toggle the Notes_Panel open (or closed if already open) and close the Photos_Panel if it was open.
6. THE "Review" button text SHALL be changed to "Send Review Request" across the entire modal.
7. THE "Edit tags" button SHALL remain unchanged from v1.

### Requirement 3: Mutual Exclusivity of Inline Panels

**User Story:** As a staff member, I want only one inline panel (photos or notes) open at a time, so that the modal remains uncluttered and focused.

#### Acceptance Criteria

1. THE Modal state SHALL include an `openPanel` field of type `'photos' | 'notes' | null`, defaulting to `null`.
2. WHEN `openPanel` is `'photos'`, THE Modal SHALL render the Photos_Panel inline below the secondary action row and SHALL NOT render the Notes_Panel.
3. WHEN `openPanel` is `'notes'`, THE Modal SHALL render the Notes_Panel inline below the secondary action row and SHALL NOT render the Photos_Panel.
4. WHEN `openPanel` is `null`, THE Modal SHALL render neither panel.
5. WHEN the user opens a panel that is already open, THE Modal SHALL close it (toggle to `null`).
6. THE `editingNotes` state SHALL reset to `false` whenever `openPanel` changes away from `'notes'`.

### Requirement 4: Attached Photos Panel

**User Story:** As a field technician, I want to see photos already attached to the customer file and upload new photos from my phone, so that I can document job conditions on-site.

#### Acceptance Criteria

1. THE Photos_Panel SHALL render with margin-top 10 px from the action row, border-radius 14 px, `1.5px` border `#1D4ED8` (blue), and white background.
2. THE Photos_Panel SHALL display a header bar with light-blue background `#DBEAFE`, padding `10px 14px`, containing: a photo icon (16 px, blue), "Attached photos" label (13 px / weight 800, blue), a count chip (border-radius 999 px, `#1D4ED8` background, white text, 11.5 px / weight 800 / mono font), and a right-aligned "From customer file" label (11.5 px / weight 700, blue, opacity 0.85).
3. THE Photos_Panel SHALL display an upload CTAs row with white background, padding 12 px, bottom border, containing two buttons with 8 px gap:
   - Primary: "Upload photo · camera roll" — flex-1, min-height 48 px, `#1D4ED8` background, white text, border-radius 12 px, upload icon. The "· camera roll" suffix SHALL use mono font 11.5 px, opacity 0.9.
   - Secondary: "Take photo" — white background, `1.5px` blue border, blue text, camera icon, border-radius 12 px.
4. WHEN the user taps "Upload photo · camera roll", THE Photos_Panel SHALL trigger a native file picker scoped to images via `<input type="file" accept="image/*" multiple />`.
5. WHEN the user taps "Take photo", THE Photos_Panel SHALL trigger native camera capture via `<input type="file" accept="image/*" capture="environment" />`.
6. THE Photos_Panel SHALL display a horizontally scrolling photo strip with padding 12 px, gap 10 px, and momentum scrolling (`-webkit-overflow-scrolling: touch`).
7. Each photo card in the strip SHALL be 180 px wide with a 134 px image area, `1.5px` border `#E5E7EB`, border-radius 12 px, and a caption row below the image (12 px / weight 700 caption + 10.5 px / weight 600 / mono font date).
8. THE Photo_Strip SHALL display a trailing "Add more · From library" tile (110 px wide, dashed `1.5px` border, `#F9FAFB` background, plus icon, "Add more" label 12 px / weight 800, "From library" sub-label 10.5 px / weight 600 / mono font).
9. THE Photos_Panel SHALL display a footer with `#F9FAFB` background, padding `8px 14px 10px`, top border, containing: left-aligned "Tap a photo to expand · pinch to zoom" hint (11.5 px / weight 700, `#6B7280`) and right-aligned "View all (N)" outlined button (padding `6px 10px`, border-radius 8 px, `1.5px` border `#E5E7EB`, 12 px / weight 800).
10. THE Photos_Panel SHALL fetch photos from `GET /customers/:customerId/photos` on open, using the existing customer photos API endpoint.
11. WHEN photos are uploaded, THE Photos_Panel SHALL show per-file progress, optimistically prepend thumbnails to the strip, and revert on error.
12. THE Photos_Panel SHALL use the existing `POST /customers/:customerId/photos` endpoint for uploads, attaching the current `appointmentId` so the photo is tagged to this job.

### Requirement 5: Appointment Notes Data Model (Backend)

**User Story:** As a developer, I want a structured appointment notes data model with audit tracking, so that the centralized Internal Notes panel has a proper backend.

#### Acceptance Criteria

1. THE Backend SHALL create an `appointment_notes` table with columns: `id` (UUID, PK), `appointment_id` (UUID, FK to `appointments.id`, UNIQUE, NOT NULL), `body` (TEXT, NOT NULL, default empty string), `updated_at` (TIMESTAMPTZ, NOT NULL), `updated_by_id` (UUID, FK to `staff.id`, nullable).
2. THE Backend SHALL cascade-delete notes when an appointment is deleted.
3. THE Backend SHALL expose a `GET /appointments/:id/notes` endpoint returning the appointment's notes as an `AppointmentNotesResponse` object with fields: `appointment_id`, `body`, `updated_at`, `updated_by` (object with `id`, `name`, `role` or null).
4. WHEN no notes record exists for an appointment, THE `GET /appointments/:id/notes` endpoint SHALL return a response with an empty `body`, the current timestamp as `updated_at`, and null `updated_by`.
5. THE Backend SHALL expose a `PATCH /appointments/:id/notes` endpoint accepting `{ body: string }` that upserts the notes record (creates if not exists, updates if exists), sets `updated_at` to now, and sets `updated_by_id` to the current authenticated user.
6. THE Backend SHALL validate that `body` does not exceed 50,000 characters.
7. THE Backend SHALL use structured logging with domain `appointment_notes` for all notes operations.

### Requirement 6: Internal Notes Panel (Frontend)

**User Story:** As a staff member, I want a single centralized Internal Notes panel with view and edit modes, so that everyone touching the job sees the same notes.

#### Acceptance Criteria

1. THE Notes_Panel SHALL render with margin-top 10 px, border-radius 14 px, `1.5px` border `#E5E7EB`, white background, and subtle shadow `0 1px 2px rgba(10,15,30,0.04)`.
2. THE Notes_Panel header SHALL display an "INTERNAL NOTES" eyebrow (12.5 px / weight 800 / 1.4 px tracking / uppercase, color `#64748B`) and a right-aligned "Edit" affordance (pencil icon + "Edit" text, 14 px / weight 700, color `#64748B`, transparent background, no border) visible only in view mode.
3. WHEN in view mode, THE Notes_Panel SHALL display the note body text (14.5 px / weight 500 / 1.6 line-height, color `#0B1220`, min-height 80 px) with padding `0 20px 22px`.
4. WHEN the user taps "Edit", THE Notes_Panel SHALL switch to edit mode: a full-width textarea (min-height 150 px, padding `12px 14px`, border-radius 12 px, `1.5px` border `#E5E7EB`, font 14.5 px / weight 500 / 1.5 line-height, `resize: vertical`, `outline: none`) pre-filled with the current note body, with cursor placed at the end.
5. THE Notes_Panel edit mode SHALL display a button row below the textarea (margin-top 14 px, gap 12 px, justified end) with: "Cancel" (white background, `1.5px` border `#E5E7EB`, color `#1F2937`, padding `12px 28px`, border-radius 999 px, 15 px / weight 700, min-width 120 px) and "Save Notes" (teal background `#14B8A6`, `1.5px` border `#14B8A6`, white text, padding `12px 28px`, border-radius 999 px, 15 px / weight 700, min-width 140 px).
6. WHEN the user presses Escape while editing, THE Notes_Panel SHALL cancel editing and discard local changes.
7. WHEN the user presses `⌘+Enter` (Mac) or `Ctrl+Enter` (other), THE Notes_Panel SHALL save the notes.
8. WHEN the user taps "Save Notes", THE Notes_Panel SHALL call `PATCH /appointments/:id/notes { body }`, optimistically update the view, and return to view mode on success.
9. IF the save request fails, THEN THE Notes_Panel SHALL display an error toast and remain in edit mode with the draft content preserved.
10. WHEN the user taps "Cancel", THE Notes_Panel SHALL discard local changes and return to view mode.
11. THE Notes_Panel SHALL fetch notes from `GET /appointments/:id/notes` when the panel opens.

### Requirement 7: Modal State Management Updates

**User Story:** As a developer, I want the modal state to support the new `openPanel` and `editingNotes` fields alongside the existing sheet state, so that v2 panels and v1 sheets coexist correctly.

#### Acceptance Criteria

1. THE `useModalState` hook SHALL be extended with an `openPanel` field of type `'photos' | 'notes' | null` (default `null`) and an `editingNotes` field of type `boolean` (default `false`).
2. THE `useModalState` hook SHALL provide a `togglePanel(panel: 'photos' | 'notes')` function that toggles the specified panel open/closed and closes the other panel.
3. WHEN `openPanel` changes away from `'notes'`, THE `useModalState` hook SHALL automatically reset `editingNotes` to `false`.
4. WHEN a sheet (tags, payment, estimate) is opened via `openSheetExclusive`, THE `useModalState` hook SHALL close any open panel (set `openPanel` to `null`).
5. WHEN a panel is opened via `togglePanel`, THE `useModalState` hook SHALL close any open sheet (set `openSheet` to `null`).
6. THE `useModalState` hook SHALL provide `setEditingNotes(editing: boolean)` for the Notes_Panel to control edit mode.

### Requirement 8: Frontend Hooks for Notes

**User Story:** As a developer, I want TanStack Query hooks for fetching and saving appointment notes, so that the Notes_Panel has proper data management.

#### Acceptance Criteria

1. THE `useAppointmentNotes(appointmentId)` hook SHALL fetch notes from `GET /appointments/:id/notes` and return the `AppointmentNotesResponse` data.
2. THE `useSaveAppointmentNotes()` mutation hook SHALL call `PATCH /appointments/:id/notes { body }` and invalidate the notes query on success.
3. THE `useSaveAppointmentNotes()` hook SHALL support optimistic updates: immediately update the cached notes body, revert on failure.
4. WHEN the notes query returns a 404 or empty response, THE `useAppointmentNotes` hook SHALL return a default object with empty `body`.

### Requirement 9: Photo Upload Integration

**User Story:** As a field technician, I want uploaded photos to appear immediately in the photo strip and persist to the server, so that I get instant feedback on my uploads.

#### Acceptance Criteria

1. THE Photos_Panel SHALL use the existing `POST /customers/:customerId/photos` endpoint for file uploads, passing the current `appointmentId` in the request.
2. WHEN files are selected via the file picker or camera, THE Photos_Panel SHALL create optimistic placeholder cards in the photo strip showing upload progress.
3. WHEN an upload succeeds, THE Photos_Panel SHALL replace the placeholder with the real photo data from the server response.
4. IF an upload fails, THEN THE Photos_Panel SHALL remove the placeholder card and display an error toast.
5. THE Photos_Panel SHALL invalidate the customer photos query after successful uploads so that the count badge updates.
6. THE "Add more · From library" trailing tile SHALL trigger the same file picker as the "Upload photo · camera roll" button.

### Requirement 10: Backend API Endpoints for Notes

**User Story:** As a developer, I want clean REST endpoints for appointment notes CRUD, so that the frontend can fetch and save notes reliably.

#### Acceptance Criteria

1. THE `GET /api/v1/appointments/:id/notes` endpoint SHALL return `200 OK` with an `AppointmentNotesResponse` containing `appointment_id`, `body`, `updated_at`, and `updated_by` (object or null).
2. WHEN no notes record exists, THE `GET` endpoint SHALL return a response with empty `body` and null `updated_by` rather than a 404.
3. THE `PATCH /api/v1/appointments/:id/notes` endpoint SHALL accept `{ body: string }`, upsert the notes record, and return the updated `AppointmentNotesResponse`.
4. IF the appointment does not exist, THEN both endpoints SHALL return `404 Not Found`.
5. IF the `body` exceeds 50,000 characters, THEN the `PATCH` endpoint SHALL return `422 Unprocessable Entity`.
6. THE `PATCH` endpoint SHALL set `updated_by_id` to the current authenticated user's staff ID.

### Requirement 11: Design Token Compliance

**User Story:** As a designer, I want all v2 components to use the exact design tokens from the handoff, so that the implementation is pixel-perfect.

#### Acceptance Criteria

1. THE V2LinkBtn accent map SHALL use: blue (`#1D4ED8` color, `#DBEAFE` bg), amber (`#B45309` color, `#FEF3C7` bg).
2. THE Notes_Panel eyebrow SHALL use slate color `#64748B`.
3. THE Notes_Panel "Save Notes" button SHALL use teal `#14B8A6` for background and border.
4. THE Photos_Panel border SHALL use blue `#1D4ED8`.
5. THE Photos_Panel header background SHALL use `#DBEAFE`.
6. All panel borders SHALL be `1.5px` and panel border-radii SHALL be 14 px.
7. All buttons inside the panels SHALL meet the 44 px minimum hit target.
8. THE mono font (JetBrains Mono) SHALL be used for: count badges, "· camera roll" suffix, photo dates, and timestamps.

### Requirement 12: Keyboard Accessibility

**User Story:** As a user with assistive technology, I want the v2 panels to be fully keyboard accessible, so that I can use all features without a mouse.

#### Acceptance Criteria

1. THE V2LinkBtn buttons SHALL be focusable via Tab and activatable via Enter or Space.
2. WHEN the Notes_Panel is in edit mode, pressing Escape SHALL cancel editing.
3. WHEN the Notes_Panel is in edit mode, pressing `⌘+Enter` (Mac) or `Ctrl+Enter` (other) SHALL save the notes.
4. THE Photos_Panel photo cards SHALL be focusable via Tab for keyboard navigation of the photo strip.
5. THE "Upload photo · camera roll" and "Take photo" buttons SHALL have accessible labels describing their function.
6. THE V2LinkBtn SHALL include `aria-expanded` attribute reflecting the open/closed state of its associated panel.

### Requirement 13: Unit Testing (Frontend)

**User Story:** As a developer, I want thorough Vitest unit tests for all new v2 frontend components, so that I have confidence in component correctness.

#### Acceptance Criteria

1. THE implementation SHALL include unit tests for the V2LinkBtn component covering: default state rendering, open state with accent tinting, count badge display, chevron rotation, and `aria-expanded` attribute.
2. THE implementation SHALL include unit tests for the Photos_Panel component covering: header rendering, upload CTA buttons, photo strip rendering, "Add more" tile, footer rendering, and file input triggers.
3. THE implementation SHALL include unit tests for the Notes_Panel component covering: view mode rendering, edit mode transition, textarea pre-fill, Cancel behavior, Save Notes behavior, Escape key handling, and `⌘+Enter`/`Ctrl+Enter` save shortcut.
4. THE implementation SHALL include unit tests for the updated SecondaryActionsStrip covering: V2LinkBtn rendering for photos and notes, "Send Review Request" label, count badge values, and panel toggle behavior.
5. THE implementation SHALL include unit tests for the updated `useModalState` hook covering: `openPanel` toggling, mutual exclusivity with sheets, `editingNotes` auto-reset, and `togglePanel` function.

### Requirement 14: Unit Testing (Backend)

**User Story:** As a developer, I want thorough pytest unit tests for the new appointment notes backend, so that I have confidence in API correctness.

#### Acceptance Criteria

1. THE implementation SHALL include unit tests (`@pytest.mark.unit`) for the `AppointmentNotes` model covering: creation, field validation, relationship to Appointment, and cascade delete.
2. THE implementation SHALL include unit tests for the notes service covering: get notes (existing and non-existing), save notes (create and update), body length validation, and `updated_by` tracking.
3. THE implementation SHALL include unit tests for the notes API endpoints covering: GET (existing notes, no notes, invalid appointment), PATCH (create, update, validation errors, auth).
4. THE implementation SHALL include functional tests (`@pytest.mark.functional`) for the notes lifecycle: create notes → read → update → read → verify body changed and `updated_by` updated.
5. THE implementation SHALL include integration tests (`@pytest.mark.integration`) verifying that notes are accessible when fetching appointment details.

### Requirement 15: Property-Based Testing

**User Story:** As a developer, I want property-based tests (Hypothesis) for backend correctness properties, so that I can verify invariants across many random inputs.

#### Acceptance Criteria

1. THE implementation SHALL include a PBT for notes body round-trip: for any valid string body (≤ 50,000 chars), saving via PATCH then reading via GET SHALL return the identical body.
2. THE implementation SHALL include a PBT for notes upsert idempotence: saving the same body twice SHALL produce the same result (body unchanged, `updated_at` may differ).
3. THE implementation SHALL include a PBT for notes body validation: for any string exceeding 50,000 characters, the PATCH endpoint SHALL return 422.
4. THE implementation SHALL include a PBT for panel mutual exclusivity: for any sequence of `togglePanel` calls, at most one panel SHALL be open at any time.
5. THE implementation SHALL include a PBT for `editingNotes` auto-reset: for any sequence where `openPanel` changes away from `'notes'`, `editingNotes` SHALL be `false`.

### Requirement 16: Linting and Type Checking

**User Story:** As a developer, I want all new code to pass linting and type checking with zero errors, so that code quality is maintained.

#### Acceptance Criteria

1. ALL new backend Python code SHALL pass `ruff check` and `ruff format` with zero violations.
2. ALL new backend Python code SHALL pass `mypy` and `pyright` with zero type errors.
3. ALL new frontend TypeScript code SHALL pass ESLint with zero errors.
4. ALL new frontend TypeScript code SHALL pass TypeScript strict mode compilation with zero errors.

### Requirement 17: E2E Testing and Deployment Validation

**User Story:** As a developer, I want the v2 enhancements validated end-to-end on a deployed environment, so that I have confidence the feature works in production conditions.

#### Acceptance Criteria

1. AFTER all code changes are complete, THE implementation SHALL deploy the frontend to Vercel and wait for a successful build.
2. THE agent-browser validation SHALL test the photos panel: tap "See attached photos" → verify panel opens with header, upload CTAs, photo strip → verify chevron flips up → verify notes panel is closed.
3. THE agent-browser validation SHALL test the notes panel: tap "See attached notes" → verify panel opens with "INTERNAL NOTES" eyebrow and Edit affordance → tap Edit → verify textarea appears with Cancel and Save Notes buttons → verify photos panel is closed.
4. THE agent-browser validation SHALL verify the "Send Review Request" label is displayed instead of "Review".
5. THE agent-browser validation SHALL test mutual exclusivity: open photos panel → tap "See attached notes" → verify photos panel closes and notes panel opens.
6. THE agent-browser validation SHALL check for JavaScript console errors and uncaught exceptions during all v2 interactions.
7. ALL tests (unit, functional, integration, property-based, and E2E) SHALL pass with zero failures before the feature is considered complete.
