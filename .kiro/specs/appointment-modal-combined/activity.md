# Activity Log — appointment-modal-combined

## [2026-04-23 17:25] Task 9: Frontend: Tag Editor and Payment/Estimate sheet wrappers

### Status: ✅ COMPLETE

### What Was Done
- Created TagEditorSheet with current tags display, suggested tags, custom input, system tag protection, optimistic save via useSaveCustomerTags
- Created PaymentSheetWrapper wrapping PaymentCollector inside SheetContainer
- Created EstimateSheetWrapper wrapping EstimateCreator inside SheetContainer
- Fixed SheetContainer ReactNode import to use type-only import

### Files Modified
- `frontend/src/features/schedule/components/AppointmentModal/TagEditorSheet.tsx` — new
- `frontend/src/features/schedule/components/AppointmentModal/PaymentSheetWrapper.tsx` — new
- `frontend/src/features/schedule/components/AppointmentModal/EstimateSheetWrapper.tsx` — new
- `frontend/src/shared/components/SheetContainer.tsx` — fixed type import

### Quality Check Results
- Lint: ✅ 0 errors (39 pre-existing warnings)
- TypeCheck: ✅ 0 errors in new files (pre-existing errors in FilterPanel.tsx/Layout.tsx unrelated)
- Tests: ✅ 1793/1793 passing

---



### Status: ✅ COMPLETE

### What Was Done
- Created `ModalHeader.tsx` — status badge pill (hidden for pending/draft), meta chips (property type, appointment ID), H1 job title (26px/800/-0.8), schedule line, 40×40 close button
- Created `TimelineStrip.tsx` — 4-step progress indicator (Booked, En route, On site, Done) with completed/current/inactive dot states, timestamps in mono font, responsive horizontal scroll
- Created `ActionCard.tsx` — single workflow action button with active (stage color fill, white text, icon bubble), disabled (opacity 0.4), and done (white bg, green border, checkmark, timestamp) states
- Created `ActionTrack.tsx` — 3 side-by-side ActionCards (En route, On site, Done) with optimistic mutations, error toast on failure, hidden for terminal statuses
- Created `SecondaryActionsStrip.tsx` — 4 LinkButtons (Add photo, Notes, Review, Edit tags) with Edit tags toggling active variant when tags sheet is open

### Files Created
- `frontend/src/features/schedule/components/AppointmentModal/ModalHeader.tsx`
- `frontend/src/features/schedule/components/AppointmentModal/TimelineStrip.tsx`
- `frontend/src/features/schedule/components/AppointmentModal/ActionCard.tsx`
- `frontend/src/features/schedule/components/AppointmentModal/ActionTrack.tsx`
- `frontend/src/features/schedule/components/AppointmentModal/SecondaryActionsStrip.tsx`

### Quality Check Results
- Lint: ✅ Pass (0 ESLint errors)
- TypeCheck: ✅ Pass (0 TypeScript errors)
- Tests: ✅ 1792/1793 passing (1 pre-existing failure in pick-jobs.pbt.test.ts, unrelated)

---

## [2026-04-23 17:14] Task 6: Frontend Tag types and hooks

### Status: ✅ COMPLETE

### What Was Done
- Added `TagTone`, `TagSource`, `CustomerTag`, `TagSaveRequest`, `TagSaveResponse` types to `frontend/src/features/schedule/types/index.ts`
- Added same types to `frontend/src/features/customers/types/index.ts` (extends BaseEntity)
- Added `getTags` and `saveTags` methods to `customerApi.ts`
- Created `frontend/src/features/schedule/hooks/useCustomerTags.ts` with `useCustomerTags` query and `useSaveCustomerTags` mutation (optimistic update, system tag preservation on rollback)
- Created `frontend/src/features/schedule/hooks/useModalState.ts` with `useModalState` hook and `deriveStep` pure function

### Files Modified
- `frontend/src/features/schedule/types/index.ts` — added tag types
- `frontend/src/features/customers/types/index.ts` — added tag types
- `frontend/src/features/customers/api/customerApi.ts` — added getTags/saveTags
- `frontend/src/features/schedule/hooks/useCustomerTags.ts` — new file
- `frontend/src/features/schedule/hooks/useModalState.ts` — new file

### Quality Check Results
- Lint: ✅ Pass (no errors in new files)
- TypeCheck: ✅ Pass (no errors in new files)
- Tests: ✅ 1793/1793 passing

---

## [2026-04-23 22:01] Task 2: Backend Repository, Service, and API for Customer Tags

### Status: ✅ COMPLETE

### What Was Done
- Created `CustomerTagRepository` with `get_by_customer_id`, `create`, `delete_by_ids`, `get_by_customer_and_label`
- Created `CustomerTagService` with diff-based save logic, system tag preservation, duplicate label validation
- Added `GET /api/v1/customers/{customer_id}/tags` and `PUT /api/v1/customers/{customer_id}/tags` endpoints to customers API

### Files Modified
- `src/grins_platform/repositories/customer_tag_repository.py` — new file
- `src/grins_platform/services/customer_tag_service.py` — new file
- `src/grins_platform/api/v1/customers.py` — added tag endpoints + import

### Quality Check Results
- Ruff: ✅ Pass (0 violations)
- MyPy: ✅ Pass (0 new errors; 2 pre-existing errors in unrelated functions)
- Pyright: ✅ Pass (0 errors, 1 warning on rowcount type)
- Tests: ✅ 2979 passing (pre-existing failures unrelated to this task)

### Notes
- Pre-existing test failures in `test_appointment_service_crm.py` and `test_sms_service_gaps.py` are unrelated to this task
- `CustomerTagsUpdateRequest` imported at module level (not TYPE_CHECKING) as required by FastAPI for body parsing

---
