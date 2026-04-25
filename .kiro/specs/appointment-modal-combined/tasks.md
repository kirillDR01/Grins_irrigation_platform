# Implementation Plan: Combined Appointment Modal

## Overview

This plan replaces the existing `AppointmentDetail.tsx` (~941 lines) with a high-fidelity, design-spec-driven `AppointmentModal` that consolidates the entire on-site appointment workflow. The backend gains a `customer_tags` table with CRUD endpoints. The frontend gains ~18 new components, 3 hooks, and shared primitives (TagChip, SheetContainer). All existing functionality (communication timeline, reschedule banners, no-reply review, opt-out badge, cancel dialog, edit flow, payment, estimates) is preserved.

**Phase ordering:** Backend (migration → model → schemas → repository → service → API) → Shared components → Frontend modal sections → Modal assembly → Testing → E2E validation.

## Tasks

- [x] 1. Backend: Database migration and CustomerTag model
  - [x] 1.1 Create Alembic migration for `customer_tags` table
    - Create `migrations/versions/xxx_add_customer_tags_table.py`
    - Table columns: `id` (UUID PK), `customer_id` (UUID FK → customers.id ON DELETE CASCADE), `label` (VARCHAR(32) NOT NULL), `tone` (VARCHAR(10) NOT NULL, CHECK IN neutral/blue/green/amber/violet), `source` (VARCHAR(10) NOT NULL, CHECK IN manual/system, DEFAULT 'manual'), `created_at` (TIMESTAMPTZ NOT NULL DEFAULT now())
    - Add UNIQUE constraint on `(customer_id, label)`
    - Add index on `customer_id`
    - _Requirements: 12.1, 12.2, 12.3_

  - [x] 1.2 Create CustomerTag SQLAlchemy model
    - Create `src/grins_platform/models/customer_tag.py` with all columns, constraints, and relationship to Customer
    - Add `tags` relationship to `Customer` model in `src/grins_platform/models/customer.py` (back_populates, cascade delete-orphan, lazy selectin)
    - Register model in `models/__init__.py` if needed
    - _Requirements: 12.1, 12.2, 12.3_

  - [x] 1.3 Create Pydantic schemas for customer tags
    - Create `src/grins_platform/schemas/customer_tag.py`
    - Define `TagTone` enum, `TagSource` enum, `CustomerTagResponse`, `TagInput`, `CustomerTagsUpdateRequest`, `CustomerTagsUpdateResponse`
    - Validate label length 1–32, tone in allowed values, max 50 tags per request
    - _Requirements: 12.7_

- [x] 2. Backend: Repository, service, and API endpoints for customer tags
  - [x] 2.1 Create CustomerTagRepository
    - Create `src/grins_platform/repositories/customer_tag_repository.py`
    - Methods: `get_by_customer_id`, `create`, `delete_by_ids`, `get_by_customer_and_label`
    - _Requirements: 12.4, 12.5_

  - [x] 2.2 Create CustomerTagService
    - Create `src/grins_platform/services/customer_tag_service.py`
    - Implement diff-based save: compare incoming manual tags vs existing, insert new, delete removed, preserve system tags
    - Validate duplicate labels within request (reject with 422)
    - Use LoggerMixin with DOMAIN = "customer_tags"
    - _Requirements: 12.5, 12.6, 12.7_

  - [x] 2.3 Add tag endpoints to customers API
    - Extend `src/grins_platform/api/v1/customers.py` with:
      - `GET /api/v1/customers/{customer_id}/tags` → returns list of CustomerTagResponse
      - `PUT /api/v1/customers/{customer_id}/tags` → accepts CustomerTagsUpdateRequest, returns CustomerTagsUpdateResponse
    - Handle 404 (customer not found), 422 (validation), 409 (race condition unique violation)
    - _Requirements: 12.4, 12.5, 12.6, 12.7_

- [x] 3. Backend: Unit tests for customer tags
  - [x] 3.1 Write unit tests for CustomerTag model
    - Create `src/grins_platform/tests/unit/test_customer_tag_model.py`
    - Test model creation, field validation, relationship to Customer
    - _Requirements: 12.1, 12.2_

  - [x] 3.2 Write unit tests for CustomerTagService
    - Create `src/grins_platform/tests/unit/test_customer_tag_service.py`
    - Test diff logic, system tag preservation, validation, duplicate detection
    - _Requirements: 12.5, 12.6, 12.7_

  - [x] 3.3 Write unit tests for tag API endpoints
    - Create `src/grins_platform/tests/unit/test_customer_tag_api.py`
    - Test GET/PUT endpoints, error responses (404, 422, 409)
    - _Requirements: 12.4, 12.5, 12.6, 12.7_

- [x] 4. Checkpoint — Backend tags complete
  - Ensure all backend unit tests pass, ask the user if questions arise.

- [x] 5. Frontend: Shared components (TagChip, SheetContainer, LinkButton)
  - [x] 5.1 Create TagChip shared component
    - Create `frontend/src/shared/components/TagChip.tsx`
    - Inline-flex pill with 999px radius, tone-based colors per design tokens §7.1
    - Static variant (padding 5px 10px) and removable variant (padding 5px 6px 5px 10px with 18×18 remove-X circle)
    - `white-space: nowrap`, 12.5px / weight 800 / -0.1 letter-spacing
    - Remove-X has `aria-label="Remove tag: [label]"`
    - System tags render remove-X as disabled with tooltip
    - _Requirements: 17.1, 17.2, 17.3, 17.4, 17.5, 18.4_

  - [x] 5.2 Create SheetContainer shared component
    - Create `frontend/src/shared/components/SheetContainer.tsx`
    - 560px width, white bg, 20px top radius, 1px border, modal shadow
    - 44×5px grab handle, optional back button, close button, title/subtitle header
    - Scrollable body (overflow auto, flex 1), sticky footer (bg #F9FAFB, 1px top border)
    - _Requirements: 14.1, 14.2, 14.3, 14.4, 14.5_

  - [x] 5.3 Create LinkButton component
    - Create `frontend/src/features/schedule/components/AppointmentModal/LinkButton.tsx`
    - 44px min-height, 12px radius, 1.5px border, default/active/destructive variants
    - Icon optional: 16px, stroke 2.2, 6px gap before label
    - _Requirements: 5.5, 11.1_

- [x] 6. Frontend: Tag types and hooks
  - [x] 6.1 Add Tag types to schedule and customer type files
    - Add `TagTone`, `TagSource`, `CustomerTag`, `TagSaveRequest`, `TagSaveResponse` to `frontend/src/features/schedule/types/index.ts`
    - Add same types to `frontend/src/features/customers/types/index.ts`
    - _Requirements: 12.1, 17.2_

  - [x] 6.2 Create useCustomerTags hook
    - Create `frontend/src/features/schedule/hooks/useCustomerTags.ts`
    - `useCustomerTags(customerId)` — GET query for customer tags
    - `useSaveCustomerTags()` — PUT mutation with optimistic update on customer tags query
    - _Requirements: 12.4, 12.5, 13.9, 13.10_

  - [x] 6.3 Create useModalState hook
    - Create `frontend/src/features/schedule/hooks/useModalState.ts`
    - Local state: `openSheet` (null | 'payment' | 'estimate' | 'tags'), `mapsPopoverOpen`
    - `deriveStep(status)` pure function: confirmed/scheduled → 0, en_route → 1, in_progress → 2, completed → 3, others → null
    - _Requirements: 6.4, 16.1_

- [x] 7. Frontend: Modal sub-components (header, timeline, action track)
  - [x] 7.1 Create ModalHeader component
    - Create `frontend/src/features/schedule/components/AppointmentModal/ModalHeader.tsx`
    - Status badge pill with design-spec color mapping, meta chips (property type, appointment ID), H1 job title (26px/800/-0.8), schedule line (15px/600), 40×40 close button
    - Hide status badge for pending/draft statuses
    - `aria-label="Status: [status text]"` on badge
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 18.1_

  - [x] 7.2 Create TimelineStrip component
    - Create `frontend/src/features/schedule/components/AppointmentModal/TimelineStrip.tsx`
    - 4 evenly-distributed dots (Booked, En route, On site, Done) connected by 2px lines
    - Dot states: completed (filled dark, white checkmark), current (filled dark, blue inner dot, outer ring), inactive (white fill, gray border)
    - Timestamps in mono font below reached steps, "—" for unreached
    - Responsive: < 360px reduces min-width to 60px, enables horizontal scroll
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7_

  - [x] 7.3 Create ActionCard component
    - Create `frontend/src/features/schedule/components/AppointmentModal/ActionCard.tsx`
    - Three states: active (stage color fill, white text, 36×36 icon bubble), disabled (opacity 0.4, cursor not-allowed), done (white bg, green border, checkmark, timestamp)
    - `<button>` with full accessible labels, `aria-live="polite"` for completion
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.7, 18.2_

  - [x] 7.4 Create ActionTrack component
    - Create `frontend/src/features/schedule/components/AppointmentModal/ActionTrack.tsx`
    - 3 side-by-side ActionCards with 8px gap, flex-1, min-height 104px
    - Optimistic update on tap: advance step, update timeline, call backend mutation
    - Revert on failure with error toast
    - Hidden for pending/draft statuses
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8_

  - [x] 7.5 Create SecondaryActionsStrip component
    - Create `frontend/src/features/schedule/components/AppointmentModal/SecondaryActionsStrip.tsx`
    - 4 LinkButtons: Add photo, Notes, Review, Edit tags
    - Edit tags button toggles active state (violet bg/border/text) when tag editor is open
    - No AI draft button
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [x] 8. Frontend: Modal sub-components (customer, property, scope, tech, footer)
  - [x] 8.1 Create CustomerHero component
    - Create `frontend/src/features/schedule/components/AppointmentModal/CustomerHero.tsx`
    - Teal header strip with 44×44 avatar circle, customer name (18px/800), history summary
    - Tags row with "TAGS" caps label and TagChip components; hidden when zero tags
    - Phone row with blue icon badge, mono phone number (17px/800), "Call" chip linking to tel:
    - Email row with soft-bg icon badge, mailto: link
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6_

  - [x] 8.2 Create PropertyDirectionsCard component
    - Create `frontend/src/features/schedule/components/AppointmentModal/PropertyDirectionsCard.tsx`
    - "PROPERTY" caps label, street address (19px/800), city/state/zip (15px/600)
    - Full-width "Get directions" button (#1D4ED8 bg, white text)
    - Triggers MapsPickerPopover on tap
    - _Requirements: 8.1, 8.2, 8.3_

  - [x] 8.3 Create MapsPickerPopover component
    - Create `frontend/src/features/schedule/components/AppointmentModal/MapsPickerPopover.tsx`
    - Popover with 14px radius, "OPEN IN" header, Apple Maps row (teal), Google Maps row (blue)
    - `role="menu"` with `role="menuitem"` rows, Escape closes, focus management
    - Apple Maps URL: `maps://?daddr=<encoded>` fallback to `https://maps.apple.com/?daddr=<encoded>`
    - Google Maps URL: `https://www.google.com/maps/dir/?api=1&destination=<encoded>`, prefer lat/lng when available
    - "Remember my choice" button (deferred — picker appears every tap)
    - _Requirements: 8.4, 8.5, 8.6, 8.7, 8.8, 18.3_

  - [x] 8.4 Create ScopeMaterialsCard component
    - Create `frontend/src/features/schedule/components/AppointmentModal/ScopeMaterialsCard.tsx`
    - "SCOPE" caps label, job scope description (17px/800)
    - Neutral pills for duration and staff count, amber pill for priority
    - "MATERIALS" section with wrap row of material tags
    - _Requirements: 9.1, 9.2, 9.3_

  - [x] 8.5 Create AssignedTechCard component
    - Create `frontend/src/features/schedule/components/AppointmentModal/AssignedTechCard.tsx`
    - User icon, "ASSIGNED TECH" caps label, tech name and route number
    - "Reassign" LinkButton (hidden for tech role users)
    - _Requirements: 10.1, 10.2_

  - [x] 8.6 Create ModalFooter component
    - Create `frontend/src/features/schedule/components/AppointmentModal/ModalFooter.tsx`
    - Footer bar (bg #F9FAFB, 1px top border) with Edit, No show, Cancel LinkButtons
    - Cancel uses destructive variant (text #B91C1C, border #FCA5A5)
    - Hidden for terminal states (completed, cancelled, no_show)
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5_

- [x] 9. Frontend: Tag Editor and Payment/Estimate sheet wrappers
  - [x] 9.1 Create TagEditorSheet component
    - Create `frontend/src/features/schedule/components/AppointmentModal/TagEditorSheet.tsx`
    - Uses SheetContainer with title "Edit tags" and subtitle "Tags apply to [Customer Name] across every job — past and future"
    - "CURRENT TAGS" section with removable TagChips in #F9FAFB container, "Add custom" dashed-border button
    - System tags render remove-X disabled with tooltip
    - "SUGGESTED" section with predefined suggestions (Repeat customer, Commercial, Difficult access, Dog on property, Prefers text, Gate code needed, Corner lot), filtering out already-applied tags
    - Custom tag input capped at 32 characters
    - Info banner (blue, #DBEAFE bg) explaining customer-scoped save behavior
    - Footer: Cancel button + "Save tags · applies everywhere" button
    - On save: call PUT endpoint, optimistic update tags row, close sheet, emit customer-updated event
    - On failure: toast "Couldn't save tags — try again", restore previous state
    - _Requirements: 13.1, 13.2, 13.3, 13.4, 13.5, 13.6, 13.7, 13.8, 13.9, 13.10, 13.11, 13.12_

  - [x] 9.2 Create PaymentSheetWrapper component
    - Create `frontend/src/features/schedule/components/AppointmentModal/PaymentSheetWrapper.tsx`
    - Wraps existing PaymentCollector inside SheetContainer
    - Reuses `useCollectPayment()` hook
    - _Requirements: 6.2_

  - [x] 9.3 Create EstimateSheetWrapper component
    - Create `frontend/src/features/schedule/components/AppointmentModal/EstimateSheetWrapper.tsx`
    - Wraps existing EstimateCreator inside SheetContainer
    - Reuses `useCreateEstimateFromAppointment()` hook
    - _Requirements: 6.3_

- [x] 10. Frontend: Assemble AppointmentModal and wire into SchedulePage
  - [x] 10.1 Create AppointmentModal root component
    - Create `frontend/src/features/schedule/components/AppointmentModal/AppointmentModal.tsx`
    - Dialog with `role="dialog"`, `aria-modal="true"`, labeled by job title, initial focus on close button
    - 560px fixed width on desktop (≥640px), full-width bottom sheet on mobile (<640px)
    - 18px border-radius, 1px #E5E7EB border, white bg, modal shadow, backdrop rgba(11,18,32,0.4) with blur(4px)
    - Focus trap while open, return focus to trigger on close
    - Dismiss on close button, backdrop click, or Escape
    - Compose all sub-components: ModalHeader, RescheduleBanner (conditional), NoReplyBanner (conditional), TimelineStrip, ActionTrack + SecondaryActionsStrip, PaymentEstimateCTAs, CustomerHero, PropertyDirectionsCard, ScopeMaterialsCard, AssignedTechCard, CommunicationTimeline, DurationMetrics (conditional), ModalFooter
    - Single-sheet exclusivity: opening any sheet closes others
    - Preserve all existing functionality: SendConfirmationButton for drafts, OptOutBadge, cancel dialog, edit flow
    - Reuse all existing hooks: useAppointment, useAppointmentTimeline, all mutation hooks
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 6.1, 6.4, 6.5, 6.6, 15.1, 15.2, 15.3, 15.4, 15.5, 15.6, 15.7, 15.8, 16.1, 16.2, 16.3, 16.4, 18.5, 18.6, 19.1, 19.2, 19.3, 19.4, 19.5_

  - [x] 10.2 Create AppointmentModal barrel export
    - Create `frontend/src/features/schedule/components/AppointmentModal/index.ts`
    - Export AppointmentModal as default and named export
    - _Requirements: 1.1_

  - [x] 10.3 Wire AppointmentModal into SchedulePage
    - Modify `frontend/src/features/schedule/components/SchedulePage.tsx`
    - Replace AppointmentDetail usage with AppointmentModal
    - Ensure calendar chip onClick opens AppointmentModal with correct appointmentId
    - _Requirements: 1.1, 15.1_

- [x] 11. Checkpoint — Frontend modal assembled
  - Ensure all components compile without errors, ask the user if questions arise.

- [x] 12. Backend: Functional and integration tests for customer tags
  - [x] 12.1 Write functional tests for tag lifecycle
    - Create `src/grins_platform/tests/functional/test_tag_lifecycle_functional.py`
    - Test: create tags → read → update (add/remove) → read → verify diff
    - Test: system tag protection (create system tag → PUT without it → verify preserved)
    - Test: unique constraint enforcement (create tag → create duplicate → verify 409/422)
    - Test: cascade delete (create customer with tags → delete customer → verify tags gone)
    - Test: tag validation (invalid labels, invalid tones, empty request → verify 422)
    - _Requirements: 12.1, 12.2, 12.3, 12.5, 12.6, 12.7_

  - [x] 12.2 Write integration tests for tags with appointment detail
    - Create `src/grins_platform/tests/integration/test_tag_appointment_integration.py`
    - Test: create customer with tags → create appointment → fetch appointment detail → verify tags present via customer relationship
    - Test: update tags → fetch appointment → verify new tags reflected
    - _Requirements: 12.4, 12.5_

- [x] 13. Frontend: Unit tests for new components
  - [x] 13.1 Write unit tests for AppointmentModal
    - Create `frontend/src/features/schedule/components/AppointmentModal/AppointmentModal.test.tsx`
    - Test: renders all sections, opens/closes correctly, ARIA attributes, focus management
    - Test: pending/draft statuses hide timeline and action track
    - Test: terminal states hide footer actions
    - _Requirements: 1.5, 1.6, 2.6, 11.5, 16.2_

  - [x] 13.2 Write unit tests for TagChip
    - Create `frontend/src/shared/components/TagChip.test.tsx`
    - Test: all 5 tone colors render correct text/bg/border
    - Test: static vs removable variants
    - Test: aria-label on remove button
    - Test: white-space nowrap
    - _Requirements: 17.1, 17.2, 17.3, 17.4, 17.5, 18.4_

  - [x] 13.3 Write unit tests for TagEditorSheet
    - Create `frontend/src/features/schedule/components/AppointmentModal/TagEditorSheet.test.tsx`
    - Test: current tags display, suggested filtering (no overlap with current), add/remove draft, save flow, system tag protection
    - _Requirements: 13.1, 13.2, 13.3, 13.4, 13.5, 13.6, 13.7, 13.9, 13.10, 13.12_

  - [x] 13.4 Write unit tests for TimelineStrip
    - Create `frontend/src/features/schedule/components/AppointmentModal/TimelineStrip.test.tsx`
    - Test: dot states for each step value (0–3), timestamp display, responsive behavior
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

  - [x] 13.5 Write unit tests for ActionTrack
    - Create `frontend/src/features/schedule/components/AppointmentModal/ActionTrack.test.tsx`
    - Test: card states for each step, tap handlers call correct mutations, disabled states
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.7_

  - [x] 13.6 Write unit tests for MapsPickerPopover
    - Create `frontend/src/features/schedule/components/AppointmentModal/MapsPickerPopover.test.tsx`
    - Test: URL generation for both map apps, ARIA roles, keyboard navigation
    - _Requirements: 8.4, 8.5, 8.6, 8.7, 18.3_

- [x] 14. Checkpoint — All unit tests pass
  - Ensure all backend and frontend unit tests pass, ask the user if questions arise.

- [x] 15. Property-based tests
  - [x] 15.1 Write PBT for tag label uniqueness per customer (Property 7)
    - **Property 7: Tag label uniqueness per customer**
    - **Validates: Requirements 12.2**
    - Add to `src/grins_platform/tests/unit/test_pbt_appointment_modal.py`
    - Generate random (customer_id, label) pairs, insert, attempt duplicate, verify constraint violation

  - [x] 15.2 Write PBT for system tag preservation (Property 8)
    - **Property 8: Tag save performs diff and preserves system tags**
    - **Validates: Requirements 12.5, 12.6**
    - Add to `src/grins_platform/tests/unit/test_pbt_appointment_modal.py`
    - Generate random tag sets with system tags, PUT new manual tags, verify system tags preserved

  - [x] 15.3 Write PBT for tag input validation (Property 9)
    - **Property 9: Tag input validation rejects invalid data**
    - **Validates: Requirements 12.7**
    - Add to `src/grins_platform/tests/unit/test_pbt_appointment_modal.py`
    - Generate random invalid labels/tones, verify 422 rejection

  - [x] 15.4 Write PBT for status-to-step mapping (Property 11)
    - **Property 11: Status-to-step mapping is deterministic and correct**
    - **Validates: Requirements 16.1**
    - Add to `src/grins_platform/tests/unit/test_pbt_appointment_modal.py`
    - Generate all valid statuses, verify deterministic mapping

  - [x] 15.5 Write PBT for step transition linearity (Property 12)
    - **Property 12: Step transitions are strictly linear**
    - **Validates: Requirements 16.3, 16.4**
    - Add to `src/grins_platform/tests/unit/test_pbt_appointment_modal.py`
    - Generate random step sequences, verify only +1 transitions allowed

  - [x] 15.6 Write PBT for tone-to-color mapping completeness (Property 13)
    - **Property 13: Tone-to-color mapping is complete and correct**
    - **Validates: Requirements 17.2, 17.5**
    - Add to `src/grins_platform/tests/unit/test_pbt_appointment_modal.py`
    - Generate all valid tones, verify correct color triplet returned

- [x] 16. Checkpoint — All tests pass
  - Ensure all unit, functional, integration, and property-based tests pass with zero failures, ask the user if questions arise.

- [x] 17. E2E: Deploy to Vercel and validate with agent-browser
  - [x] 17.1 Deploy frontend to Vercel
    - Run Vercel deployment and wait for successful build
    - Verify deployment URL is accessible
    - _Requirements: 20.6_

  - [x] 17.2 Validate modal rendering via agent-browser
    - Navigate to schedule page → open an appointment → verify modal renders with header, timeline, action track, customer hero, property card, scope card, footer
    - Capture screenshots to `e2e-screenshots/appointment-modal/`
    - _Requirements: 20.7_

  - [x] 17.3 Validate tag editor flow via agent-browser
    - Open Edit tags sheet → add a suggested tag → remove a tag → verify save behavior
    - Capture screenshots to `e2e-screenshots/appointment-modal/`
    - _Requirements: 20.8_

  - [x] 17.4 Validate maps picker via agent-browser
    - Tap "Get directions" → verify popover renders with Apple Maps and Google Maps options
    - Capture screenshots to `e2e-screenshots/appointment-modal/`
    - _Requirements: 20.9_

  - [x] 17.5 Validate responsive behavior via agent-browser
    - Set viewport to 375×812 → verify modal renders as bottom sheet with grab handle
    - Capture screenshots to `e2e-screenshots/appointment-modal/`
    - _Requirements: 20.10_

  - [x] 17.6 Check for JavaScript errors via agent-browser
    - Run `agent-browser console` and `agent-browser errors` during all interactions
    - Verify zero JS errors and uncaught exceptions
    - _Requirements: 20.11_

- [x] 18. Final checkpoint — All tests pass, feature complete
  - Ensure all tests (unit, functional, integration, property-based, and E2E) pass with zero failures before the feature is considered complete.
  - _Requirements: 20.12_

## Notes

- All tasks are required — none are optional
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- Backend must be completed before frontend tag hooks can be wired
- Shared components (TagChip, SheetContainer) must exist before modal sub-components that use them
- The AppointmentModal assembly (task 10) depends on all sub-components being created first
- E2E testing (task 17) requires all code changes to be complete and deployed
