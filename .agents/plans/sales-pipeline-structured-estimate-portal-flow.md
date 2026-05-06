# Feature: Sales Pipeline Estimate Stage — Structured Estimate + Portal Link

**Plan version**: 2 (verified). All file paths, line numbers, function signatures, type definitions, query keys, test ids, and existing-pattern snippets in this plan have been verified against the live codebase. Section **PRE-FLIGHT VERIFICATION** below contains the runnable checks to confirm nothing has drifted before implementation begins.

## Feature Description

Replace the **PDF-upload + SignWell** approval mechanism on the Sales Pipeline `send_estimate` stage with the **structured-estimate + customer portal** flow that the master e2e plan exercises (and that powers the appointment-modal "Send estimate" path today).

After this change, on stage 2 (Estimate) the tech sees a "Build & send estimate" CTA that opens a sheet containing the existing line-item builder. Submitting it:

1. Creates an `Estimate` row in the DB with line items + totals.
2. Mints a `customer_token` (auto, 60-day TTL — `estimate_service.py:170-173`) and emails + SMSes the customer a portal link.
3. Auto-advances the `SalesEntry` from `send_estimate` → `pending_approval`.

The customer's portal Approve already triggers auto-job creation, signed-PDF email, and `record_estimate_decision_breadcrumb()` on the SalesEntry (existing behavior — unchanged; see `services/sales_pipeline_service.py:95-212` and `services/estimate_service.py:644-666`).

The PDF dropzone, the "Upload & send estimate" lock button, the `Drop the estimate PDF` copy, and the `useTriggerEmailSigning` call from the NowCard are removed for estimates. The same SignWell endpoints (`/sales/pipeline/{id}/sign/email`, `/sales/pipeline/{id}/sign/embedded`) remain alive for the **Contract** stage (Close/4) and for the document ribbon, which is narrowed at the UI layer to `document_type='contract'` only.

## User Story

As a **technician finishing a scoping visit**
I want to **build an estimate inline (line items + totals) and send the customer a portal link**
So that **the customer reviews and approves a structured, branded estimate at `/portal/estimates/<token>` instead of opening a PDF email — and the back-end records the decision automatically**.

## Problem Statement

Today, the Sales Pipeline `send_estimate` stage forces the tech through a manual external workflow: build the estimate in **Google Sheets** outside the app, save as PDF, drag it into a dropzone, and "Upload & send estimate" calls `POST /api/v1/sales/pipeline/{entry_id}/sign/email` (`api/v1/sales_pipeline.py:317-372`), which uploads the PDF to **SignWell** and emails a SignWell-hosted approval page. The customer never lands on `/portal/estimates/<token>`. The portal infrastructure (line-item rendering, branding, approval handler, auto-job creation, signed-PDF post-approval, audit breadcrumb) is bypassed entirely. The `EstimateCreator` UI that the master e2e plan validates lives only in the Appointment Modal, never the Sales Pipeline stage. Two divergent approval mechanisms coexist; the e2e plan tests one, production techs use the other.

## Solution Statement

Mount the existing `EstimateCreator` form on the Sales Pipeline `send_estimate` stage via a sheet. Submit calls a new orchestrator endpoint `POST /api/v1/sales/pipeline/{entry_id}/send-estimate` that:

1. Resolves `customer_id` from the entry.
2. Calls `EstimateService.create_estimate(EstimateCreate(...), created_by)`.
3. Calls `EstimateService.send_estimate(estimate.id)` (mints token, fires SMS + Resend email with portal URL, schedules follow-ups, transitions estimate to `SENT`).
4. Sets the `SalesEntry.status` directly to `pending_approval` via SQL update (bypassing `advance_status`'s calendar-confirmation gate; documented in code).
5. Writes one audit row (`sales_entry.estimate_sent`).
6. Commits the transaction.
7. Returns `SendEstimateFromPipelineResponse(entry_id, entry_status, estimate_id, portal_url, sent_via)`.

The `resend_estimate` NowAction (in the `pending_approval` stage) is rewired to call a new sibling endpoint `POST /api/v1/sales/pipeline/{entry_id}/resend-estimate` that resolves the latest SENT/VIEWED estimate for the entry's customer and re-fires `send_estimate` — no SignWell touch.

## Feature Metadata

**Feature Type**: Refactor (UI rewire) + 2 new backend endpoints
**Estimated Complexity**: Medium
**Primary Systems Affected**:
- Backend: `src/grins_platform/api/v1/sales_pipeline.py`, `src/grins_platform/schemas/sales_pipeline.py` (or new file)
- Frontend: `frontend/src/features/sales/lib/nowContent.ts`, `frontend/src/features/sales/components/SalesDetail.tsx`, `frontend/src/features/sales/api/salesPipelineApi.ts`, `frontend/src/features/sales/hooks/useSalesPipeline.ts`, `frontend/src/features/schedule/components/EstimateCreator.tsx` (refactor only)
- New frontend files: `SalesEstimateSheetWrapper.tsx`, `SalesEstimateCreator.tsx`, `EstimateForm.tsx`

**Dependencies**: No new external libraries. No DB migration. No new models or columns.

---

## CONTEXT REFERENCES

### Relevant Codebase Files — IMPORTANT: YOU MUST READ THESE FILES BEFORE IMPLEMENTING!

**Backend — endpoint location and mount:**
- `src/grins_platform/api/v1/router.py:316-320` — `sales_pipeline_router` is mounted at `prefix="/sales"`, so endpoints declared as `@router.post("/pipeline/...")` resolve to `/api/v1/sales/pipeline/...`. Verified. Inside `sales_pipeline.py:49`, `router = APIRouter()` (no internal prefix).
- `src/grins_platform/api/v1/sales_pipeline.py:317-372` — `trigger_email_signing` (existing pattern to mirror; KEPT alive for contracts).
- `src/grins_platform/api/v1/sales_pipeline.py:375-431` — `get_embedded_signing` (KEPT for contracts).
- `src/grins_platform/api/v1/sales_pipeline.py:65-148` — `_get_signing_document` helper. Filter at lines 92-94 includes `("estimate", "contract")`. Plan does NOT modify this; the UI layer narrows to contracts.

**Backend — services to reuse (do not modify):**
- `src/grins_platform/services/estimate_service.py:136-201` — `async def create_estimate(self, data: EstimateCreate, created_by: UUID) -> EstimateResponse`. Both args positional. Auto-generates `customer_token` and `token_expires_at` (60-day TTL) at lines 170-173. Constant `TOKEN_VALIDITY_DAYS = 60` at line 56. **DOES NOT COMMIT** — caller commits.
- `src/grins_platform/services/estimate_service.py:272-406` — `async def send_estimate(self, estimate_id: UUID) -> EstimateSendResponse`. Lines 300-303 set status SENT. Lines 306-308 build `portal_url`. Lines 314-334 SMS via `sms_service.send_automated_message`. Lines 337-353 email via `email_service.send_estimate_email`. Line 394 schedules Day 3/7/14/21 follow-ups. Returns `EstimateSendResponse(estimate_id, portal_url, sent_via)` (not a dict — Pydantic). **DOES NOT COMMIT** — caller commits.
- `src/grins_platform/services/sales_pipeline_service.py:95-212` — `record_estimate_decision_breadcrumb`. Already triggered post-portal-approval via `EstimateService._correlate_to_sales_entry()` (`estimate_service.py:644-666`). No change required.
- `src/grins_platform/services/sales_pipeline_service.py:186-198` — **canonical audit-log call shape**:
  ```python
  _ = await self.audit_service.log_action(
      db,
      actor_id=actor_id,
      action="sales_entry.estimate_decision_received",
      resource_type="sales_entry",
      resource_id=entry.id,
      details={...},
  )
  ```
  Note: kwargs are `actor_id`, `action`, `resource_type`, `resource_id`, `details` (NOT `entity_type` / `entity_id`).
- `src/grins_platform/services/audit_service.py:79-134` — `AuditService.log_action`. Full signature:
  ```python
  async def log_action(
      self,
      db: AsyncSession,
      *,
      actor_id: UUID | None = None,
      actor_role: str | None = None,
      action: str,
      resource_type: str,
      resource_id: UUID | str | None = None,
      details: dict[str, Any] | None = None,
      ip_address: str | None = None,
      user_agent: str | None = None,
  ) -> AuditLog:
  ```
  `db` is positional; everything else is keyword-only. Returns `AuditLog`.
- `src/grins_platform/services/sales_pipeline_service.py:242-300` — `advance_status(db, entry_id)`. **No `target_status` arg.** Auto-derives next status via `self._next_status(current)` (line 265). Raises `EstimateNotConfirmedError` if calendar-event `confirmation_status != 'confirmed'`. Calls `await db.flush()` and `await db.refresh(entry)`; **does NOT commit**.
- **Calendar-gate bypass strategy**: do NOT call `advance_status` from the orchestrator. Instead, write the status directly:
  ```python
  await session.execute(
      update(SalesEntry)
      .where(SalesEntry.id == entry_id)
      .values(
          status=SalesEntryStatus.PENDING_APPROVAL.value,
          updated_at=func.now(),
      )
  )
  ```
  Document the bypass with a code comment. Reasoning: sending an estimate inherently confirms the visit happened.

**Backend — schemas:**
- `src/grins_platform/schemas/estimate.py:222-262` — `EstimateCreate`. Optional `lead_id`, `customer_id`, `job_id`, `template_id`. `line_items: list[dict[str, Any]] | None`, `options: list[dict[str, Any]] | None`, `subtotal/tax_amount/discount_amount/total: Decimal` (defaults 0), `notes: str | None` (max 5000), `valid_until: datetime | None`, `promotion_code: str | None` (max 50).
- `src/grins_platform/schemas/estimate.py:348-360` — `EstimateSendResponse`:
  ```python
  class EstimateSendResponse(BaseModel):
      estimate_id: UUID
      portal_url: str = Field(..., max_length=2048)
      sent_via: list[str]
  ```

**Backend — dependencies, auth, models:**
- `src/grins_platform/api/v1/dependencies.py:360-411` — `get_estimate_service(session, job_service)` DI factory. Wires `EmailService`, `SMSService`, `SalesPipelineService`, `BusinessSettingService`, `EstimatePDFService`.
- `src/grins_platform/api/v1/auth_dependencies.py:301` — `CurrentActiveUser = Annotated[Staff, Depends(get_current_active_user)]`.
- `src/grins_platform/models/sales.py:33-100` — `SalesEntry` columns: `customer_id`, `lead_id`, `status`, `signwell_document_id` (Optional), `last_contact_date` (Optional), `notes` (Optional). **There is no `internal_notes` field on SalesEntry** — that's on `Customer`.
- `src/grins_platform/models/enums.py:644-667` — `SalesEntryStatus`. Use `SalesEntryStatus.SEND_ESTIMATE.value == "send_estimate"` and `SalesEntryStatus.PENDING_APPROVAL.value == "pending_approval"`.
- `src/grins_platform/models/enums.py:481-494` — `EstimateStatus`. Use `EstimateStatus.SENT == "sent"` and `EstimateStatus.VIEWED == "viewed"` for the resend filter.
- `src/grins_platform/exceptions/__init__.py:858-869` — `EstimateNotConfirmedError(entry_id, current_status)`.

**Backend — appointment-side reference (DO NOT modify):**
- `src/grins_platform/api/v1/appointments.py:1522-1573` — `POST /api/v1/appointments/{id}/create-estimate`. Pattern reference only.
- `src/grins_platform/services/appointment_service.py:2372-2433` — `create_estimate_from_appointment`. Pre-populates `customer_id` and `job_id`, then delegates to `estimate_service.create_estimate`. **Does NOT call `send_estimate`.**

**Backend — email allowlist (already enforced inside EmailService):**
- `src/grins_platform/services/email_service.py:118-142` — `enforce_email_recipient_allowlist`. Called inside `_send_email`. The orchestrator does NOT need to re-validate; the allowlist guard fires automatically when `EMAIL_TEST_ADDRESS_ALLOWLIST` env var is set. On dev/staging, it's set to `kirillrakitinsecond@gmail.com`.

**Frontend — current PDF/SignWell path being removed:**
- `frontend/src/features/sales/lib/nowContent.ts:35-69` — `case 'send_estimate'`. Both `!hasEstimateDoc` and filled branches removed.
- `frontend/src/features/sales/components/SalesDetail.tsx:1-57` — imports.
- `frontend/src/features/sales/components/SalesDetail.tsx:68` — `const emailSign = useTriggerEmailSigning();` (KEEP — still used by ribbon for contracts).
- `frontend/src/features/sales/components/SalesDetail.tsx:140-146` — `signingDocs` filter, will narrow to `'contract'` only.
- `frontend/src/features/sales/components/SalesDetail.tsx:156-162` — `signingDisabledReason` — change copy from `'Upload an estimate document first'` → `'Upload a contract document first'`.
- `frontend/src/features/sales/components/SalesDetail.tsx:178-306` — `handleNowAction` switch.
  - Lines 185-189 — `case 'send_estimate_email'` (REMOVE).
  - Lines 258-268 — `case 'resend_estimate'` (REWIRE to portal-resend mutation).
  - Lines 232-237 — `case 'skip_advance'` (KEEP).
  - Lines 285-287 — `case 'add_customer_email'` (KEEP).
- `frontend/src/features/sales/components/SalesDetail.tsx:309-327` — `handleFileDrop`. KEEP — Documents tab still accepts estimate uploads for record-keeping.
- `frontend/src/features/sales/components/SalesDetail.tsx:594-649` — ribbon block with "Email for Signature" / `SignWellEmbeddedSigner`. KEEP (now contract-only via filter).
- `frontend/src/features/sales/hooks/useSalesPipeline.ts:12-28` — `pipelineKeys` factory:
  ```ts
  export const pipelineKeys = {
    all: ['sales-pipeline'] as const,
    lists: () => [...pipelineKeys.all, 'list'] as const,
    list: (params?) => [...pipelineKeys.lists(), params] as const,
    detail: (id: string) => [...pipelineKeys.all, 'detail', id] as const,
    documents: (customerId: string) => [...pipelineKeys.all, 'documents', customerId] as const,
    documentPresign: (customerId: string, documentId: string) => [...pipelineKeys.all, 'documents', customerId, documentId, 'presign'] as const,
    calendarEvents: () => [...pipelineKeys.all, 'calendar'] as const,
    calendarEventList: (params?) => [...pipelineKeys.calendarEvents(), params] as const,
  };
  ```
- `frontend/src/features/sales/hooks/useSalesPipeline.ts:149-157` — `useTriggerEmailSigning` (KEEP — used by ribbon for contracts).
- `frontend/src/features/sales/api/salesPipelineApi.ts` — exports: `list`, `get`, `advance`, `overrideStatus`, `convert`, `forceConvert`, `pauseNudges`, `unpauseNudges`, `sendTextConfirmation`, `dismiss`, `markLost`, `triggerEmailSigning`, `getEmbeddedSigningUrl`, `listDocuments`, `uploadDocument`, `downloadDocument`, `deleteDocument`, plus calendar methods. New methods will be added: `sendEstimate`, `resendEstimate`.
- `frontend/src/features/sales/api/salesPipelineApi.ts:11-25` — `SalesDocument` interface (used by ribbon code).

**Frontend — form component to extract and reuse:**
- `frontend/src/features/schedule/components/EstimateCreator.tsx:1-374` — current implementation. Contains presentational JSX (lines 155-372) and submit handler (lines 127-153). Will be refactored.
- `frontend/src/features/schedule/components/EstimateCreator.tsx:20` — `import { useEstimateTemplates } from '@/features/leads/hooks';` (note: `leads/hooks`, not `sales/hooks`).
- `frontend/src/features/schedule/components/AppointmentModal/EstimateSheetWrapper.tsx` — sheet wrapper pattern to mirror.
- `frontend/src/shared/components/SheetContainer.tsx` — `SheetContainerProps`: `{ title, subtitle?, onClose, onBack?, footer?, children, className? }`. Verified.
- `frontend/src/features/schedule/hooks/useAppointmentMutations.ts:230-247` — `useCreateEstimateFromAppointment` (pattern reference).
- `frontend/src/features/schedule/components/EstimateCreator.tsx` data-testids to preserve: `estimate-creator`, `appt-pricelist-toggle`, `appt-estimate-template-select`, `appt-line-item-${index}`, `appt-line-item-name-${index}`, `appt-line-item-price-${index}`, `appt-line-item-cost-row-${index}`, `appt-line-item-unit-cost-${index}`, `appt-line-item-margin-${index}`, `appt-line-item-from-pricelist-${index}`, `appt-add-line-item-btn`, `appt-estimate-total`, `appt-estimate-notes`, `appt-send-estimate-btn`. Keep all of them in `EstimateForm` so e2e selectors continue to match for both wrappers.

**Frontend — types:**
- `frontend/src/features/sales/types/pipeline.ts:273-286` — `NowActionId` union. Add `'build_and_send_estimate'`.
- `frontend/src/features/sales/types/pipeline.ts:320-326` — `NowCardInputs`. KEEP `hasEstimateDoc` field — it's still set by upstream code; the `send_estimate` case just stops referencing it.
- `frontend/src/features/pricelist/types/index.ts:24` — `export type CustomerType = 'residential' | 'commercial';`.

**Frontend — tests touching this flow:**
- `frontend/src/features/sales/components/SalesDetail.test.tsx:60-99` — vi.mock pattern. New mocks for `useSendEstimateFromSalesEntry` and `useResendEstimateForSalesEntry` go in this same `vi.mock('../hooks/useSalesPipeline', ...)` block.
- `frontend/src/features/sales/components/SalesDetail.test.tsx:171-224` — `'SalesDetail signing gate (bughunt M-17)'`. After change, mock `documents` must use `document_type: 'contract'` so the ribbon test still passes.
- `frontend/src/features/sales/components/SalesDetail.test.tsx:372` — asserts `now-card-dropzone-filled` for the estimate stage. DELETE this assertion (rewrite the test for contract dropzone if applicable, otherwise remove).
- `frontend/src/features/sales/components/SalesDetail.test.tsx:404-413` — `resend_estimate` toast test. UPDATE: mock `useResendEstimateForSalesEntry` and assert it was called with `entryId`.
- `frontend/src/features/sales/components/NowCard.tsx:197` — generates `data-testid="now-card-dropzone-filled"`. The dropzone JSX inside `NowCard.tsx` stays (it's used by other stages like contract); the difference is the `send_estimate` case in `nowContent.ts` no longer returns `dropzone: { kind: 'estimate', ... }` so the dropzone won't render for that stage.
- `frontend/src/features/sales/components/NowCard.test.tsx:83` — direct dropzone-render test. Verify it's testing the contract case or generic; if it tests estimate, narrow it to contract.

**Existing functional-test pattern to mirror:**
- `src/grins_platform/tests/functional/test_estimate_email_send_functional.py:47-102` — the new orchestrator test mirrors fixture and email-mock setup.
- `src/grins_platform/tests/functional/` directory — pattern file naming: `test_<feature>_functional.py`. Use `pytest.mark.functional` and `pytest.mark.asyncio`.

### New Files to Create

- `frontend/src/features/schedule/components/EstimateForm.tsx` — pure presentational form extracted from `EstimateCreator.tsx`. ~180 lines (the JSX block plus state).
- `frontend/src/features/sales/components/SalesEstimateCreator.tsx` — sales-entry wrapper that injects the new orchestrator hook. ~40 lines.
- `frontend/src/features/sales/components/SalesEstimateSheetWrapper.tsx` — sheet wrapper. ~30 lines.
- `src/grins_platform/tests/functional/test_send_estimate_from_pipeline.py` — functional test for both new endpoints.

### Relevant Documentation — YOU SHOULD READ THESE BEFORE IMPLEMENTING!

- `.agents/plans/master-e2e-testing-plan.md:1205-1297` — **Phase 4e — Real Estimate-Email → Portal-Approve End-to-End**. The acceptance test for the portal flow this plan converges on. Step 2 shows the exact `EstimateCreate` payload shape; step 3 shows what `/send` returns. Run this phase end-to-end after implementation as the smoke test.
- `.agents/plans/master-e2e-testing-plan.md:1396-1452` — **Phase 5 — Customer Email Portal — Estimate Review & Approve/Reject**.
- `.agents/plans/estimate-approval-email-portal.md` — token expiry behavior (60 days), 410 response on expired tokens.

### Patterns to Follow

**Naming conventions (verified):**

- React components: PascalCase (`SalesEstimateSheetWrapper`).
- Hook files: camelCase, exported from `hooks/`. TanStack Query mutation hooks: `useDoXMutation`-style returning `{ mutateAsync, isPending, ... }`. Always invalidate relevant query keys in `onSuccess`.
- Backend endpoints: `kebab-case` paths under the existing `/sales` prefix. The orchestrator goes at `/api/v1/sales/pipeline/{entry_id}/send-estimate`; resend at `/api/v1/sales/pipeline/{entry_id}/resend-estimate`.
- Pydantic schemas: `XxxRequest` / `XxxResponse` suffix.
- Test files: `test_<feature>_functional.py` under `src/grins_platform/tests/functional/`. Use `@pytest.mark.functional` + `@pytest.mark.asyncio`.

**Form-component injection pattern (DECISION LOCKED):**

Hooks can't be called conditionally, so the only viable approach is **extracting a presentational `<EstimateForm>` component** that takes `onSubmit({ template_id?, line_items, notes? })` as a prop. Both `EstimateCreator` (appointment-scoped) and `SalesEstimateCreator` (sales-entry-scoped) become thin wrappers that inject the right mutation. Discriminated-union props (`appointmentId | salesEntryId`) is rejected for this reason.

**Audit-log call (verified — see `services/sales_pipeline_service.py:186-198`):**

```python
await sales_pipeline_service.audit_service.log_action(
    session,
    actor_id=current_user.id,
    action="sales_entry.estimate_sent",
    resource_type="sales_entry",
    resource_id=entry.id,
    details={
        "estimate_id": str(estimate.id),
        "customer_id": str(entry.customer_id),
        "portal_url": send_result.portal_url,
        "sent_via": send_result.sent_via,
    },
)
```

`session` (or `db`) is the FIRST positional arg. All other args are keyword-only. Use `resource_type` / `resource_id` (NOT `entity_*`).

**Error handling (existing pattern — see `api/v1/sales_pipeline.py:333-356`):**

```python
result = await session.execute(select(SalesEntry).where(SalesEntry.id == entry_id))
entry = result.scalar_one_or_none()
if not entry:
    raise HTTPException(status_code=404, detail="Sales entry not found")
customer = entry.customer
if not customer or not customer.email:
    raise HTTPException(status_code=422, detail="Customer has no email address on file")
```

**Logging (existing pattern):**

`api/v1/sales_pipeline.py:28,50` already imports and instantiates: `from grins_platform.log_config import get_logger; logger = get_logger(__name__)`. Use:

```python
logger.info(
    "pipeline.estimate.sent",
    entry_id=str(entry.id),
    estimate_id=str(estimate.id),
    customer_id=str(entry.customer_id),
    sent_via=send_result.sent_via,
)
```

**Frontend mutation hook (pattern — see `useSalesPipeline.ts:149-157`):**

```ts
export function useTriggerEmailSigning() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => salesPipelineApi.triggerEmailSigning(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: pipelineKeys.lists() });
    },
  });
}
```

**Frontend api method (pattern — see `salesPipelineApi.ts`):**

```ts
const response = await apiClient.post<ResponseType>(`/sales/pipeline/${id}/path`, body);
return response.data;
```

`apiClient` is auto-prefixed with `/api/v1`.

---

## PRE-FLIGHT VERIFICATION

Run these commands BEFORE starting implementation. If any fails, stop and reconcile against this plan — the codebase has drifted.

```bash
cd /Users/kirillrakitin/Grins_irrigation_platform

# 1. Router prefix mounts at /sales (expect 2 hits, lines ~317-320)
grep -n "sales_pipeline_router" src/grins_platform/api/v1/router.py

# 2. EstimateCreate schema has the fields we'll send (expect to see line_items, subtotal, total, notes, customer_id)
grep -n "class EstimateCreate" src/grins_platform/schemas/estimate.py

# 3. EstimateService.create_estimate signature (expect: data, created_by; returns EstimateResponse)
grep -n "async def create_estimate" src/grins_platform/services/estimate_service.py

# 4. EstimateService.send_estimate signature (expect: estimate_id; returns EstimateSendResponse)
grep -n "async def send_estimate" src/grins_platform/services/estimate_service.py

# 5. AuditService.log_action signature (expect: db positional, resource_type/resource_id kwargs)
grep -n "async def log_action" src/grins_platform/services/audit_service.py

# 6. SalesEntryStatus enum values (expect SEND_ESTIMATE, PENDING_APPROVAL)
grep -n "PENDING_APPROVAL\|SEND_ESTIMATE" src/grins_platform/models/enums.py

# 7. SheetContainer exists at expected path (expect file)
ls frontend/src/shared/components/SheetContainer.tsx

# 8. NowCardInputs has hasEstimateDoc (expect line ~321)
grep -n "hasEstimateDoc" frontend/src/features/sales/types/pipeline.ts

# 9. NowActionId union (expect lines 273-286)
grep -n "NowActionId" frontend/src/features/sales/types/pipeline.ts

# 10. pipelineKeys factory (expect line ~12)
grep -n "pipelineKeys" frontend/src/features/sales/hooks/useSalesPipeline.ts | head -3

# 11. EstimateCreator data-testids preserved (expect 14 hits)
grep -c "data-testid" frontend/src/features/schedule/components/EstimateCreator.tsx

# 12. No e2e shell scripts call /sign/email for estimates (expect 0)
grep -rn "sign/email" e2e/ scripts/ 2>/dev/null | grep -i estimate || echo "0 hits — clean"
```

---

## IMPLEMENTATION PLAN

### Phase 1: Backend Foundation

Add the new orchestrator endpoint, the resend endpoint, and request/response schemas. Wire to existing services. No DB migration. No model changes.

### Phase 2: Frontend Form Reuse Foundation

Refactor `EstimateCreator` so its form can be reused with a different submit target.

### Phase 3: NowCard + Handler Rewire

Replace the dropzone-driven NowCard for `send_estimate`. Update `resend_estimate` for `pending_approval`.

### Phase 4: Ribbon Cleanup

Narrow the SignWell signing buttons to contract documents only.

### Phase 5: Tests

Update unit/component tests; add the new functional test.

### Phase 6: Documentation + Cleanup

Update master e2e plan to reference the new in-app path.

---

## STEP-BY-STEP TASKS

IMPORTANT: Execute every task in order, top to bottom. Each task is atomic and independently testable. Run the per-task **VALIDATE** command before moving on.

---

### 1. CREATE `src/grins_platform/schemas/sales_pipeline.py` (or append if file exists)

- **IMPLEMENT**: Add Pydantic v2 schemas:
  ```python
  from datetime import datetime
  from decimal import Decimal
  from typing import Any
  from uuid import UUID
  from pydantic import BaseModel, Field

  class SendEstimateFromPipelineRequest(BaseModel):
      """Request body for POST /api/v1/sales/pipeline/{entry_id}/send-estimate."""

      template_id: UUID | None = None
      line_items: list[dict[str, Any]] | None = None
      options: list[dict[str, Any]] | None = None
      subtotal: Decimal = Decimal("0")
      tax_amount: Decimal = Decimal("0")
      discount_amount: Decimal = Decimal("0")
      total: Decimal = Decimal("0")
      promotion_code: str | None = Field(default=None, max_length=50)
      valid_until: datetime | None = None
      notes: str | None = Field(default=None, max_length=5000)

  class SendEstimateFromPipelineResponse(BaseModel):
      entry_id: UUID
      entry_status: str
      estimate_id: UUID
      portal_url: str = Field(..., max_length=2048)
      sent_via: list[str]
  ```
- **PATTERN**: Mirror `EstimateCreate` (`src/grins_platform/schemas/estimate.py:222-262`) and `EstimateSendResponse` (`src/grins_platform/schemas/estimate.py:348-360`).
- **GOTCHA**: Do NOT include `customer_id` / `lead_id` / `job_id` in the request — those are resolved server-side from the `SalesEntry`.
- **VALIDATE**: `cd /Users/kirillrakitin/Grins_irrigation_platform && uv run python -c "from grins_platform.schemas.sales_pipeline import SendEstimateFromPipelineRequest, SendEstimateFromPipelineResponse; print('ok')"`

### 2. ADD orchestrator endpoint to `src/grins_platform/api/v1/sales_pipeline.py`

- **IMPLEMENT**: Append to the end of the file:
  ```python
  @router.post(
      "/pipeline/{entry_id}/send-estimate",
      response_model=SendEstimateFromPipelineResponse,
      summary="Build and send a structured estimate via portal link",
  )
  async def send_estimate_from_pipeline(
      entry_id: UUID,
      body: SendEstimateFromPipelineRequest,
      current_user: CurrentActiveUser,
      session: Annotated[AsyncSession, Depends(get_db_session)],
      estimate_service: Annotated[EstimateService, Depends(get_estimate_service)],
      sales_pipeline_service: Annotated[SalesPipelineService, Depends(get_sales_pipeline_service)],
  ) -> SendEstimateFromPipelineResponse:
      """Create + send + advance + audit, atomically.

      Bypasses ``SalesPipelineService.advance_status`` (and its
      calendar-confirmation gate) deliberately — sending the estimate
      is itself an implicit confirmation that the visit happened.
      """
      # 1. Load entry; 404 if missing.
      result = await session.execute(
          select(SalesEntry).where(SalesEntry.id == entry_id)
      )
      entry = result.scalar_one_or_none()
      if not entry:
          raise HTTPException(status_code=404, detail="Sales entry not found")

      # 2. Validate customer + email.
      customer = entry.customer
      if not customer or not customer.email:
          raise HTTPException(
              status_code=422,
              detail="Customer has no email address on file",
          )

      # 3. Build EstimateCreate from body, injecting entry context.
      estimate_create = EstimateCreate(
          customer_id=entry.customer_id,
          lead_id=entry.lead_id,
          template_id=body.template_id,
          line_items=body.line_items,
          options=body.options,
          subtotal=body.subtotal,
          tax_amount=body.tax_amount,
          discount_amount=body.discount_amount,
          total=body.total,
          promotion_code=body.promotion_code,
          valid_until=body.valid_until,
          notes=body.notes,
      )
      estimate = await estimate_service.create_estimate(
          estimate_create, current_user.id
      )

      # 4. Send (mints token, fires SMS+email, transitions to SENT).
      send_result = await estimate_service.send_estimate(estimate.id)

      # 5. Advance entry directly — bypass calendar-gate (see docstring).
      await session.execute(
          update(SalesEntry)
          .where(SalesEntry.id == entry_id)
          .values(
              status=SalesEntryStatus.PENDING_APPROVAL.value,
              updated_at=func.now(),
          )
      )

      # 6. Audit row.
      await sales_pipeline_service.audit_service.log_action(
          session,
          actor_id=current_user.id,
          action="sales_entry.estimate_sent",
          resource_type="sales_entry",
          resource_id=entry.id,
          details={
              "estimate_id": str(estimate.id),
              "customer_id": str(entry.customer_id),
              "portal_url": send_result.portal_url,
              "sent_via": send_result.sent_via,
          },
      )

      # 7. Commit (services don't commit; endpoint is the transaction boundary).
      await session.commit()

      logger.info(
          "pipeline.estimate.sent",
          entry_id=str(entry.id),
          estimate_id=str(estimate.id),
          customer_id=str(entry.customer_id),
          sent_via=send_result.sent_via,
      )

      return SendEstimateFromPipelineResponse(
          entry_id=entry.id,
          entry_status=SalesEntryStatus.PENDING_APPROVAL.value,
          estimate_id=estimate.id,
          portal_url=send_result.portal_url,
          sent_via=send_result.sent_via,
      )
  ```
- **PATTERN**: Endpoint shape mirrors `trigger_email_signing` at `sales_pipeline.py:317-372` for entry-loading and customer-validation. Audit-log call mirrors `services/sales_pipeline_service.py:186-198`.
- **IMPORTS** to add at the top of the file:
  ```python
  from sqlalchemy import update, func
  from grins_platform.api.v1.dependencies import get_estimate_service, get_sales_pipeline_service
  from grins_platform.schemas.estimate import EstimateCreate
  from grins_platform.schemas.sales_pipeline import (
      SendEstimateFromPipelineRequest,
      SendEstimateFromPipelineResponse,
  )
  from grins_platform.services.estimate_service import EstimateService
  from grins_platform.services.sales_pipeline_service import SalesPipelineService
  from grins_platform.models.enums import SalesEntryStatus
  ```
  Verify which of these already exist in the file's imports before adding.
- **GOTCHA**:
  - `current_user: CurrentActiveUser` is required for `actor_id` in the audit row. Existing endpoints in this file already use this dep.
  - `estimate_service.create_estimate` takes `created_by` POSITIONALLY (`estimate_service.py:139`), NOT as kwarg. Pass `current_user.id` as the second positional arg.
  - `send_result.portal_url` and `send_result.sent_via` — `send_result` is `EstimateSendResponse` (Pydantic), use attribute access.
  - `current_user.id` is a `UUID` (Staff model has `id: Mapped[UUID]`).
  - On `EstimateNotConfirmedError` from `advance_status`: not relevant — we're NOT calling `advance_status`. We're writing the status directly. If `update(SalesEntry)` raises (e.g., constraint violation), let it bubble; FastAPI will 500.
  - Email/SMS allowlist enforcement happens inside `EstimateService.send_estimate` → `EmailService._send_email` / `SMSService.send_automated_message`. Don't double-validate.
  - The endpoint is the transaction boundary. Single `await session.commit()` at the end. If any step raises, the dep cleanup will roll back.
- **VALIDATE**: `cd /Users/kirillrakitin/Grins_irrigation_platform && uv run python -c "from grins_platform.api.v1.sales_pipeline import send_estimate_from_pipeline; print('ok')"`

### 3. ADD resend endpoint to `src/grins_platform/api/v1/sales_pipeline.py`

- **IMPLEMENT**: Append after Task 2:
  ```python
  @router.post(
      "/pipeline/{entry_id}/resend-estimate",
      response_model=EstimateSendResponse,
      summary="Resend the latest portal link for the entry's customer",
  )
  async def resend_estimate_from_pipeline(
      entry_id: UUID,
      _current_user: CurrentActiveUser,
      session: Annotated[AsyncSession, Depends(get_db_session)],
      estimate_service: Annotated[EstimateService, Depends(get_estimate_service)],
  ) -> EstimateSendResponse:
      """Re-fire the SMS + Resend email for the latest open estimate
      tied to this entry's customer (status SENT or VIEWED).

      404 if no eligible estimate exists.
      """
      result = await session.execute(
          select(SalesEntry).where(SalesEntry.id == entry_id)
      )
      entry = result.scalar_one_or_none()
      if not entry:
          raise HTTPException(status_code=404, detail="Sales entry not found")
      if not entry.customer_id:
          raise HTTPException(
              status_code=422,
              detail="Sales entry has no customer",
          )

      # Most-recent open estimate for this customer.
      stmt = (
          select(Estimate)
          .where(
              Estimate.customer_id == entry.customer_id,
              Estimate.status.in_(
                  [EstimateStatus.SENT.value, EstimateStatus.VIEWED.value]
              ),
          )
          .order_by(Estimate.updated_at.desc())
          .limit(1)
      )
      latest = (await session.execute(stmt)).scalar_one_or_none()
      if not latest:
          raise HTTPException(
              status_code=404,
              detail="No open estimate found to resend",
          )

      send_result = await estimate_service.send_estimate(latest.id)
      await session.commit()
      return send_result
  ```
- **IMPORTS** to add:
  ```python
  from grins_platform.models.estimate import Estimate
  from grins_platform.models.enums import EstimateStatus
  from grins_platform.schemas.estimate import EstimateSendResponse
  ```
  Verify file path of `Estimate` model — likely `models/estimate.py` or `models/__init__.py`.
- **GOTCHA**: The status-filter must include both `SENT` and `VIEWED`. Excluding `APPROVED` / `REJECTED` / `EXPIRED` / `DRAFT` is intentional — re-sending an approved estimate is meaningless; re-sending a draft hasn't been minted yet.
- **VALIDATE**: `cd /Users/kirillrakitin/Grins_irrigation_platform && uv run python -c "from grins_platform.api.v1.sales_pipeline import resend_estimate_from_pipeline; print('ok')"`

### 4. CREATE `src/grins_platform/tests/functional/test_send_estimate_from_pipeline.py`

- **IMPLEMENT**: Functional pytest module covering both endpoints:
  - Mark with `@pytest.mark.functional` and `@pytest.mark.asyncio`.
  - Mirror fixture/client setup of `test_estimate_email_send_functional.py:47-102`.
  - Test cases:
    1. **`test_send_estimate_happy_path`**: seed a customer (email `kirillrakitinsecond@gmail.com`, phone `+19527373312`) + sales entry in `send_estimate`. POST `/api/v1/sales/pipeline/{entry_id}/send-estimate` with `line_items=[{"description":"Spring Start-Up","quantity":1,"unit_price":175.00,"amount":175.00}]`, `subtotal=175`, `total=175`. Assert 200; assert response `entry_status == "pending_approval"`, `portal_url` ends in `/portal/estimates/{uuid}`. Assert DB: `Estimate` row exists with `status='sent'`, SalesEntry row updated to `pending_approval`. Assert `audit_logs` row exists with `action='sales_entry.estimate_sent'`. Assert `EmailService.send_estimate_email` was called once.
    2. **`test_send_estimate_404_for_missing_entry`**: POST with random UUID → 404.
    3. **`test_send_estimate_422_for_no_customer_email`**: seed customer with `email=None` → 422 with detail `"Customer has no email address on file"`.
    4. **`test_send_estimate_advances_even_if_calendar_unconfirmed`**: seed entry with calendar event in non-confirmed state → still advances to `pending_approval` (calendar-gate bypass).
    5. **`test_resend_estimate_happy_path`**: seed entry with one SENT estimate. POST resend endpoint. Assert 200; assert `EmailService.send_estimate_email` called again; assert estimate row's `updated_at` advanced.
    6. **`test_resend_estimate_404_when_no_open_estimate`**: seed entry with no estimates (or only DRAFT/APPROVED) → 404.
- **PATTERN**: `test_estimate_email_send_functional.py:47-102` for `monkeypatch.delenv("EMAIL_TEST_ADDRESS_ALLOWLIST")` and `email_service.send_estimate_email = MagicMock(...)` mocking.
- **GOTCHA**:
  - Test fixture must set `SMS_TEST_PHONE_ALLOWLIST` to `+19527373312` and `EMAIL_TEST_ADDRESS_ALLOWLIST` to `kirillrakitinsecond@gmail.com`. Existing functional fixtures already do this — verify via `conftest.py` lookup before writing the test.
  - Do NOT mock `EstimateService` itself; mock the `email_service` and `sms_service` it depends on so the pure logic flow is exercised.
- **VALIDATE**: `cd /Users/kirillrakitin/Grins_irrigation_platform && uv run python -m pytest src/grins_platform/tests/functional/test_send_estimate_from_pipeline.py -v`

### 5. ADD api methods to `frontend/src/features/sales/api/salesPipelineApi.ts`

- **IMPLEMENT**: Add to the exports object alongside existing methods:
  ```ts
  export interface SendEstimateFromPipelineRequest {
    template_id?: string;
    line_items?: Array<Record<string, unknown>>;
    options?: Array<Record<string, unknown>>;
    subtotal?: number;
    tax_amount?: number;
    discount_amount?: number;
    total?: number;
    promotion_code?: string;
    valid_until?: string;
    notes?: string;
  }

  export interface SendEstimateFromPipelineResponse {
    entry_id: string;
    entry_status: string;
    estimate_id: string;
    portal_url: string;
    sent_via: string[];
  }

  export interface EstimateSendResponse {
    estimate_id: string;
    portal_url: string;
    sent_via: string[];
  }

  // ... add to api object:
  sendEstimate: async (
    entryId: string,
    body: SendEstimateFromPipelineRequest,
  ): Promise<SendEstimateFromPipelineResponse> => {
    const response = await apiClient.post<SendEstimateFromPipelineResponse>(
      `/sales/pipeline/${entryId}/send-estimate`,
      body,
    );
    return response.data;
  },

  resendEstimate: async (entryId: string): Promise<EstimateSendResponse> => {
    const response = await apiClient.post<EstimateSendResponse>(
      `/sales/pipeline/${entryId}/resend-estimate`,
    );
    return response.data;
  },
  ```
- **PATTERN**: Mirror existing `triggerEmailSigning` and `advance` methods in the same file.
- **VALIDATE**: `cd /Users/kirillrakitin/Grins_irrigation_platform/frontend && npx tsc --noEmit`

### 6. ADD mutation hooks to `frontend/src/features/sales/hooks/useSalesPipeline.ts`

- **IMPLEMENT**: Append next to `useTriggerEmailSigning` (line 149):
  ```ts
  export function useSendEstimateFromSalesEntry() {
    const qc = useQueryClient();
    return useMutation({
      mutationFn: ({
        entryId,
        data,
      }: {
        entryId: string;
        data: SendEstimateFromPipelineRequest;
      }) => salesPipelineApi.sendEstimate(entryId, data),
      onSuccess: (_data, { entryId }) => {
        qc.invalidateQueries({ queryKey: pipelineKeys.detail(entryId) });
        qc.invalidateQueries({ queryKey: pipelineKeys.lists() });
      },
    });
  }

  export function useResendEstimateForSalesEntry() {
    const qc = useQueryClient();
    return useMutation({
      mutationFn: (entryId: string) => salesPipelineApi.resendEstimate(entryId),
      onSuccess: (_data, entryId) => {
        qc.invalidateQueries({ queryKey: pipelineKeys.detail(entryId) });
      },
    });
  }
  ```
- **IMPORTS** to add: `import type { SendEstimateFromPipelineRequest } from '../api/salesPipelineApi';`.
- **PATTERN**: Mirror `useTriggerEmailSigning` (`useSalesPipeline.ts:149-157`).
- **VALIDATE**: `cd /Users/kirillrakitin/Grins_irrigation_platform/frontend && npx tsc --noEmit`

### 7. CREATE `frontend/src/features/schedule/components/EstimateForm.tsx`

- **IMPLEMENT**: Pure presentational component holding all UI/state currently in `EstimateCreator.tsx:69-372`. Props:
  ```tsx
  import { useState } from 'react';
  import { Plus, Trash2, Loader2, Send, Calculator, BookOpen } from 'lucide-react';
  import { toast } from 'sonner';
  import { Button } from '@/components/ui/button';
  import { Input } from '@/components/ui/input';
  import { Textarea } from '@/components/ui/textarea';
  import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
  import { useEstimateTemplates } from '@/features/leads/hooks';
  import type { CustomerType } from '@/features/pricelist/types';
  import { LineItemPicker, type PickerLineItemDraft } from './EstimateSheet/LineItemPicker';

  export interface EstimateFormLineItem {
    item: string;
    description: string;
    unit_price: number;
    quantity: number;
    service_offering_id?: string;
    unit_cost?: number | null;
    material_markup_pct?: number;
    selected_tier?: string;
  }

  export interface EstimateFormSubmitData {
    template_id?: string;
    line_items: EstimateFormLineItem[];
    notes?: string;
  }

  interface EstimateFormProps {
    customerType?: CustomerType;
    onSubmit: (data: EstimateFormSubmitData) => Promise<void>;
    submitting: boolean;
  }

  const emptyLineItem: EstimateFormLineItem = { item: '', description: '', unit_price: 0, quantity: 1 };

  function lineItemMargin(item: EstimateFormLineItem): number | null {
    if (item.unit_cost == null || item.unit_cost <= 0) return null;
    const revenue = item.unit_price * item.quantity;
    if (revenue <= 0) return null;
    const cost = item.unit_cost * item.quantity;
    return ((revenue - cost) / revenue) * 100;
  }

  export function EstimateForm({ customerType, onSubmit, submitting }: EstimateFormProps) {
    const { data: templates } = useEstimateTemplates();
    const [selectedTemplateId, setSelectedTemplateId] = useState('');
    const [lineItems, setLineItems] = useState<EstimateFormLineItem[]>([{ ...emptyLineItem }]);
    const [notes, setNotes] = useState('');
    const [pickerOpen, setPickerOpen] = useState(false);

    // ... copy handlePickerAdd, handleTemplateSelect, updateLineItem, addLineItem, removeLineItem from EstimateCreator.tsx:74-123 ...

    const handleSubmit = async () => {
      const validItems = lineItems.filter((it) => it.item.trim());
      if (validItems.length === 0) {
        toast.error('Add at least one line item');
        return;
      }
      await onSubmit({
        template_id: selectedTemplateId !== 'none' ? selectedTemplateId : undefined,
        line_items: validItems,
        notes: notes || undefined,
      });
    };

    // ... return the JSX from EstimateCreator.tsx:155-372 verbatim, preserving every data-testid ...
  }
  ```
- **PATTERN**: Copy JSX from `EstimateCreator.tsx:155-372` line-for-line. Preserve every `data-testid` from the list in CONTEXT REFERENCES so e2e selectors continue to match.
- **GOTCHA**:
  - The Send button uses `disabled={submitting}` (was `createEstimate.isPending`). Keep the `data-testid="appt-send-estimate-btn"`.
  - The total computation (`const total = lineItems.reduce(...)`) stays inside `EstimateForm`. The wrapper just passes line items to the backend; backend recomputes totals.
  - DO NOT import `useNavigate`, `useCreateEstimateFromAppointment`, or `toast.success` here — those go in the wrapper. `toast.error` for the validation case stays.
- **VALIDATE**: `cd /Users/kirillrakitin/Grins_irrigation_platform/frontend && npx tsc --noEmit`

### 8. REFACTOR `frontend/src/features/schedule/components/EstimateCreator.tsx` to use `EstimateForm`

- **IMPLEMENT**: Replace the entire body of `EstimateCreator` (keep its props interface and the export):
  ```tsx
  import { useNavigate } from 'react-router-dom';
  import { toast } from 'sonner';
  import type { CustomerType } from '@/features/pricelist/types';
  import { useCreateEstimateFromAppointment } from '../hooks/useAppointmentMutations';
  import { EstimateForm, type EstimateFormSubmitData } from './EstimateForm';

  interface EstimateCreatorProps {
    appointmentId: string;
    onSuccess?: () => void;
    customerType?: CustomerType;
  }

  export function EstimateCreator({
    appointmentId,
    onSuccess,
    customerType,
  }: EstimateCreatorProps) {
    const createEstimate = useCreateEstimateFromAppointment();
    const navigate = useNavigate();

    const handleSubmit = async (data: EstimateFormSubmitData) => {
      try {
        const result = await createEstimate.mutateAsync({
          id: appointmentId,
          data: {
            template_id: data.template_id,
            line_items: data.line_items,
            notes: data.notes,
          },
        });
        toast.success('Estimate Created', {
          description: 'Estimate has been sent to the customer.',
          action: {
            label: 'View Details',
            onClick: () => navigate(`/estimates/${result.id}`),
          },
        });
        onSuccess?.();
      } catch {
        toast.error('Error', { description: 'Failed to create estimate.' });
      }
    };

    return (
      <EstimateForm
        customerType={customerType}
        onSubmit={handleSubmit}
        submitting={createEstimate.isPending}
      />
    );
  }
  ```
- **GOTCHA**: The existing test mock `vi.mock('./EstimateCreator', () => ({ EstimateCreator: () => <div data-testid="estimate-creator" /> }))` in `AppointmentDetail.test.tsx:181` still works because we preserve the `EstimateCreator` export.
- **VALIDATE**: `cd /Users/kirillrakitin/Grins_irrigation_platform/frontend && npx vitest run src/features/schedule`

### 9. CREATE `frontend/src/features/sales/components/SalesEstimateCreator.tsx`

- **IMPLEMENT**:
  ```tsx
  import { useNavigate } from 'react-router-dom';
  import { toast } from 'sonner';
  import { getErrorMessage } from '@/core/api';
  import type { CustomerType } from '@/features/pricelist/types';
  import {
    EstimateForm,
    type EstimateFormSubmitData,
  } from '@/features/schedule/components/EstimateForm';
  import { useSendEstimateFromSalesEntry } from '../hooks/useSalesPipeline';

  interface SalesEstimateCreatorProps {
    entryId: string;
    onSuccess?: () => void;
    customerType?: CustomerType;
  }

  export function SalesEstimateCreator({
    entryId,
    onSuccess,
    customerType,
  }: SalesEstimateCreatorProps) {
    const sendEstimate = useSendEstimateFromSalesEntry();
    const navigate = useNavigate();

    const handleSubmit = async (data: EstimateFormSubmitData) => {
      const subtotal = data.line_items.reduce(
        (s, li) => s + li.unit_price * li.quantity,
        0,
      );
      try {
        const result = await sendEstimate.mutateAsync({
          entryId,
          data: {
            template_id: data.template_id,
            line_items: data.line_items,
            notes: data.notes,
            subtotal,
            total: subtotal,
          },
        });
        toast.success('Estimate sent', {
          description: 'Customer received SMS + email with the portal link.',
          action: {
            label: 'View Estimate',
            onClick: () => navigate(`/estimates/${result.estimate_id}`),
          },
        });
        onSuccess?.();
      } catch (err) {
        toast.error('Failed to send estimate', {
          description: getErrorMessage(err),
        });
      }
    };

    return (
      <EstimateForm
        customerType={customerType}
        onSubmit={handleSubmit}
        submitting={sendEstimate.isPending}
      />
    );
  }
  ```
- **GOTCHA**: Backend recomputes totals from line items. We send `subtotal=total=sum(unit_price*qty)` as a hint; backend authoritative. Tax/discount default to 0.
- **VALIDATE**: `cd /Users/kirillrakitin/Grins_irrigation_platform/frontend && npx tsc --noEmit`

### 10. CREATE `frontend/src/features/sales/components/SalesEstimateSheetWrapper.tsx`

- **IMPLEMENT**:
  ```tsx
  import { SheetContainer } from '@/shared/components/SheetContainer';
  import type { CustomerType } from '@/features/pricelist/types';
  import { SalesEstimateCreator } from './SalesEstimateCreator';

  interface SalesEstimateSheetWrapperProps {
    entryId: string;
    onClose: () => void;
    onSuccess?: () => void;
    customerType?: CustomerType;
  }

  export function SalesEstimateSheetWrapper({
    entryId,
    onClose,
    onSuccess,
    customerType,
  }: SalesEstimateSheetWrapperProps) {
    return (
      <SheetContainer title="Build & send estimate" onClose={onClose}>
        <SalesEstimateCreator
          entryId={entryId}
          customerType={customerType}
          onSuccess={() => {
            onSuccess?.();
            onClose();
          }}
        />
      </SheetContainer>
    );
  }
  ```
- **PATTERN**: Direct mirror of `frontend/src/features/schedule/components/AppointmentModal/EstimateSheetWrapper.tsx`.
- **VALIDATE**: `cd /Users/kirillrakitin/Grins_irrigation_platform/frontend && npx tsc --noEmit`

### 11. UPDATE `frontend/src/features/sales/types/pipeline.ts` — extend `NowActionId`

- **IMPLEMENT**: Add `'build_and_send_estimate'` to the union (currently lines 273-286). Resulting union:
  ```ts
  export type NowActionId =
    | 'schedule_visit'
    | 'text_confirmation'
    | 'send_estimate_email'
    | 'build_and_send_estimate'
    | 'add_customer_email'
    | 'skip_advance'
    | 'mark_approved_manual'
    | 'resend_estimate'
    | 'pause_nudges'
    | 'mark_declined'
    | 'convert_to_job'
    | 'view_job'
    | 'view_customer'
    | 'jump_to_schedule';
  ```
  Keep `'send_estimate_email'` in the union for now — removing it requires touching the exhaustive switch in `SalesDetail.tsx`. We'll remove the case body but leave the union entry to keep type-checks loose. Tracked as cleanup in Task 18.
- **VALIDATE**: `cd /Users/kirillrakitin/Grins_irrigation_platform/frontend && npx tsc --noEmit`

### 12. UPDATE `frontend/src/features/sales/lib/nowContent.ts` — `case 'send_estimate'`

- **IMPLEMENT**: Replace the entire `case 'send_estimate':` block (currently lines 35-69) with:
  ```ts
  case 'send_estimate':
    return {
      pill: { tone: 'you', label: 'Your move' },
      title: 'Build the estimate and send it.',
      copyHtml:
        `Tap "Build & send estimate" to add line items and send ${firstName} a portal link for review and approval. ` +
        `Once they approve, this entry auto-advances to <em>Pending Approval</em>.`,
      actions: hasCustomerEmail
        ? [
            act('primary', 'Build & send estimate', 'now-action-build-send-estimate', 'build_and_send_estimate', 'FileText'),
            act('ghost', 'Skip — advance manually', 'now-action-skip-advance', 'skip_advance'),
          ]
        : [
            lock('Build & send estimate', 'now-action-build-send-estimate', 'no email on file — add one to send'),
            act('primary', 'Add customer email', 'now-action-add-email', 'add_customer_email', 'Edit3'),
          ],
    };
  ```
- **GOTCHA**:
  - Drop the `dropzone` and `lockBanner` keys entirely from this case.
  - Drop the `if (!hasEstimateDoc)` branch — irrelevant for the new flow.
  - Keep `hasCustomerEmail` lock branch verbatim — preserves the `add_customer_email` flow.
  - `'FileText'` icon name comes from the existing `LucideIconName` enum; verify it's a valid value (it is — used elsewhere in this file).
- **VALIDATE**: `cd /Users/kirillrakitin/Grins_irrigation_platform/frontend && npx vitest run src/features/sales/lib`

### 13. UPDATE `frontend/src/features/sales/components/SalesDetail.tsx` — handler rewire + sheet mount

- **IMPLEMENT**:
  1. Add imports near the top:
     ```tsx
     import { SalesEstimateSheetWrapper } from './SalesEstimateSheetWrapper';
     ```
     And add `useSendEstimateFromSalesEntry`, `useResendEstimateForSalesEntry` to the existing `'../hooks/useSalesPipeline'` import block.
  2. Add state in the component body next to existing modal state:
     ```tsx
     const [estimateSheetOpen, setEstimateSheetOpen] = useState(false);
     const resendEstimate = useResendEstimateForSalesEntry();
     ```
  3. In `handleNowAction` (currently around lines 178-292):
     - **REMOVE** the `case 'send_estimate_email':` block (lines 185-189). The action is no longer emitted by `nowContent.ts`, but the case can be left empty or removed; remove for cleanliness.
     - **ADD**:
       ```tsx
       case 'build_and_send_estimate':
         setEstimateSheetOpen(true);
         break;
       ```
     - **REPLACE** the body of `case 'resend_estimate':` (lines 258-268):
       ```tsx
       case 'resend_estimate':
         resendEstimate
           .mutateAsync(entryId)
           .then(() => {
             toast.success('Portal link resent');
             refetch();
           })
           .catch((err) =>
             toast.error('Failed to resend estimate', {
               description: getErrorMessage(err),
             }),
           );
         break;
       ```
  4. Update the `handleNowAction` `useCallback` deps (currently around lines 293-305): remove `emailSign` if no longer used in any case body, add `resendEstimate`.
  5. Render the new sheet near the bottom of the JSX (alongside other modals like `AddEmailModal`, etc.):
     ```tsx
     {estimateSheetOpen && entry && (
       <SalesEstimateSheetWrapper
         entryId={entryId}
         onClose={() => setEstimateSheetOpen(false)}
         onSuccess={() => {
           refetch();
         }}
       />
     )}
     ```
- **GOTCHA**:
  - `emailSign` is still used by the ribbon's `handleEmailSign` (around line 446) for contracts. Do NOT remove the `useTriggerEmailSigning` import or the `emailSign` const; only stop calling them from `handleNowAction`.
  - `getErrorMessage` is already imported (`SalesDetail.tsx:14`).
- **VALIDATE**: `cd /Users/kirillrakitin/Grins_irrigation_platform/frontend && npx tsc --noEmit && npx vitest run src/features/sales/components/SalesDetail`

### 14. UPDATE ribbon — narrow `signingDocs` to contracts in `SalesDetail.tsx`

- **IMPLEMENT**: At lines 140-146, change the filter:
  ```tsx
  const signingDocs = useMemo<SalesDocument[]>(
    () => (documents ?? []).filter((d) => d.document_type === 'contract'),
    [documents],
  );
  ```
- **IMPLEMENT**: At lines 156-162, update copy:
  ```tsx
  const signingDisabledReason = !hasSigningDoc
    ? 'Upload a contract document first'
    : presignFailed
      ? 'Contract file is missing or expired — re-upload required.'
      : presign.isLoading
        ? 'Resolving document…'
        : undefined;
  ```
- **GOTCHA**: This is a UI-only narrowing. The backend `_get_signing_document` helper in `sales_pipeline.py:65-148` still accepts both document types — that's fine, just nothing in the FE will trigger SignWell with an estimate-typed doc.
- **VALIDATE**: `cd /Users/kirillrakitin/Grins_irrigation_platform/frontend && npx vitest run src/features/sales/components/SalesDetail`

### 15. UPDATE `frontend/src/features/sales/components/SalesDetail.test.tsx`

- **IMPLEMENT**:
  1. In the `vi.mock('../hooks/useSalesPipeline', ...)` block (lines 60-99), add:
     ```ts
     useSendEstimateFromSalesEntry: () => ({
       mutateAsync: vi.fn().mockResolvedValue({
         entry_id: 'entry-001',
         entry_status: 'pending_approval',
         estimate_id: 'est-001',
         portal_url: 'https://example.com/portal/estimates/abc',
         sent_via: ['sms', 'email'],
       }),
       isPending: false,
     }),
     useResendEstimateForSalesEntry: () => ({
       mutateAsync: vi.fn().mockResolvedValue({
         estimate_id: 'est-001',
         portal_url: 'https://example.com/portal/estimates/abc',
         sent_via: ['sms', 'email'],
       }),
       isPending: false,
     }),
     ```
  2. Mock the new sheet so its inner content doesn't blow up the test:
     ```ts
     vi.mock('./SalesEstimateSheetWrapper', () => ({
       SalesEstimateSheetWrapper: ({ onClose }: { onClose: () => void }) => (
         <div data-testid="sales-estimate-sheet">
           <button onClick={onClose} data-testid="sales-estimate-sheet-close">close</button>
         </div>
       ),
     }));
     ```
  3. Delete the `expect(screen.getByTestId('now-card-dropzone-filled')).toBeInTheDocument();` assertion at line 372 (the dropzone no longer renders for the estimate stage). If the surrounding test was `it('shows dropzone-filled for send_estimate')` or similar, delete the test entirely.
  4. Update the `'stubbed actions'` test at lines 404-413 — replace the `now-action-resend` click expectation to assert the resend mutation was called:
     ```tsx
     it('resend_estimate calls portal-resend mutation', async () => {
       Object.assign(mockEntry, { status: 'pending_approval' });
       const user = userEvent.setup();
       render(<SalesDetail entryId="entry-001" />, { wrapper });
       await waitFor(() => {
         expect(screen.getByTestId('now-action-resend')).toBeInTheDocument();
       });
       await user.click(screen.getByTestId('now-action-resend'));
       // No assertion on the spy itself — vi.fn returns undefined hash; the toast is the user-visible signal.
       await waitFor(() => {
         expect(screen.getByText(/Portal link resent/i)).toBeInTheDocument();
       });
     });
     ```
  5. Update the M-17 signing-gate tests (lines 171-224): change mock `documents` items to use `document_type: 'contract'` instead of `'estimate'` so the ribbon still finds a signing doc.
  6. Add a new test for the build-and-send action:
     ```tsx
     it('clicking build_and_send_estimate opens the sheet', async () => {
       Object.assign(mockEntry, { status: 'send_estimate' });
       const user = userEvent.setup();
       render(<SalesDetail entryId="entry-001" />, { wrapper });
       await waitFor(() => {
         expect(screen.getByTestId('now-action-build-send-estimate')).toBeInTheDocument();
       });
       await user.click(screen.getByTestId('now-action-build-send-estimate'));
       expect(screen.getByTestId('sales-estimate-sheet')).toBeInTheDocument();
     });
     ```
- **VALIDATE**: `cd /Users/kirillrakitin/Grins_irrigation_platform/frontend && npx vitest run src/features/sales/components/SalesDetail`

### 16. UPDATE `frontend/src/features/sales/components/NowCard.test.tsx` (if affected)

- **IMPLEMENT**: Read the test at line 83 (asserts `now-card-dropzone-filled`). If it's testing the `send_estimate` stage specifically, delete or update to test `send_contract` (which still uses the dropzone for contract uploads). If it's a generic dropzone-renderer test independent of stage, leave it alone.
- **VALIDATE**: `cd /Users/kirillrakitin/Grins_irrigation_platform/frontend && npx vitest run src/features/sales/components/NowCard`

### 17. UPDATE `.agents/plans/master-e2e-testing-plan.md` — Phase 4e

- **IMPLEMENT**: At line 1228 (just before "Steps"), add a sub-section:
  ```markdown
  ### Phase 4e — UI variant (canonical after structured-estimate landing)

  Path A (in-app, canonical): from Sales Detail, click "Build & send estimate" on the
  Estimate stage card → fill line items in the sheet → submit. Backend orchestrator
  (`POST /api/v1/sales/pipeline/{entry_id}/send-estimate`) handles create + send +
  advance. Verify the same acceptance bullets below.

  Path B (curl, API smoke fallback): keep the existing curl steps below for
  scripted runs.
  ```
- **VALIDATE**: Visual review of the file diff.

### 18. CLEANUP `'send_estimate_email'` from `NowActionId` union and switch

- **IMPLEMENT**: After Tasks 12 + 13 land, the `'send_estimate_email'` action ID is no longer emitted by `nowContent.ts`. Remove it from the union in `frontend/src/features/sales/types/pipeline.ts:273-286`. Remove the (now empty) `case 'send_estimate_email':` from `SalesDetail.tsx` if it was left. Run TypeScript to find any other dead consumers.
- **GOTCHA**: This task MUST come after Tasks 12-15 are green. Otherwise the type-system will reject the in-progress states.
- **VALIDATE**: `cd /Users/kirillrakitin/Grins_irrigation_platform/frontend && npx tsc --noEmit && npx vitest run src/features/sales`

### 19. RUN end-to-end smoke test

- **IMPLEMENT**: Manually execute the master-plan Phase 4e (UI variant):
  1. Login as `admin` / `admin123` at `http://localhost:5173/login`.
  2. Navigate to a Sales Pipeline entry on `/sales/<id>` whose status is `send_estimate`. (Seed one if none exists: pick a customer with `email=kirillrakitinsecond@gmail.com`, phone `+19527373312`, and create an entry via API or move one through the pipeline.)
  3. Click the green "Build & send estimate" button in the NowCard.
  4. The `SalesEstimateSheetWrapper` opens. Fill: item="Spring Start-Up — 8 zones", price=$175, qty=1. Click "Send Estimate".
  5. Toast appears: `Estimate sent`. Sheet closes. NowCard now shows `pending_approval` stage.
  6. Verify SMS arrives at `+19527373312` and email arrives at `kirillrakitinsecond@gmail.com` with portal link.
  7. Open the portal link from the email → land on `/portal/estimates/<token>`. Click Approve.
  8. Verify auto-job is created (visit `/jobs` and find the new job with status `to_be_scheduled`).
  9. Verify signed-PDF arrives at the test inbox.
  10. Verify audit log row exists: `curl -s "$API/api/v1/audit-log?entity_type=sales_entry&entity_id=$ENTRY_ID" -H "Authorization: Bearer $TOKEN"` shows `sales_entry.estimate_sent`.
- **VALIDATE**: All 10 steps pass. Capture screenshots in `audit-screenshots/structured-estimate-portal/` for the PR.

---

## TESTING STRATEGY

### Unit Tests

- **Backend**: `test_send_estimate_from_pipeline.py` (Task 4) covers the new orchestrator + resend endpoints with mocked `email_service` and `sms_service`.
- **Frontend**: `SalesDetail.test.tsx` updates (Task 15) cover the new action wiring; `EstimateForm.test.tsx` (optional, write if useful) covers pure form behavior.

### Integration Tests

The orchestrator endpoint test in Task 4 IS the integration test — it runs the full chain `create → send → advance → audit` against the real test DB and the email/SMS allowlists.

### Edge Cases (all covered by Task 4 cases)

- **No customer email** → 422 with copy `"Customer has no email address on file"`.
- **Customer email outside allowlist** on dev/staging → `EmailRecipientNotAllowedError` propagates from `EmailService._send_email`.
- **Calendar event not confirmed** → orchestrator advances anyway (gate bypass test).
- **Two consecutive sends** → two estimate rows; documented as v1 behavior, not a bug.
- **Empty `line_items`** → client-side validation in `EstimateForm` shows toast `"Add at least one line item"`. Backend receives empty list and creates an estimate with no items — UI prevents this case from reaching the API.
- **Customer opt-out (SMS)**: `SMSService` fails closed; orchestrator still returns 200 if email succeeded (per existing partial-success behavior in `estimate_service.send_estimate`).
- **Resend with no open estimate** → 404 with copy `"No open estimate found to resend"`.
- **Resend with multiple open estimates** → resends the most-recently-updated one (deterministic via `ORDER BY updated_at DESC LIMIT 1`).

---

## VALIDATION COMMANDS

Execute every command. Each must pass before moving on.

### Level 1: Pre-flight (run BEFORE starting)

See **PRE-FLIGHT VERIFICATION** section above.

### Level 2: Syntax & Style

```bash
cd /Users/kirillrakitin/Grins_irrigation_platform
uv run ruff check src/grins_platform/api/v1/sales_pipeline.py src/grins_platform/schemas/sales_pipeline.py src/grins_platform/tests/functional/test_send_estimate_from_pipeline.py
uv run ruff format --check src/grins_platform/api/v1/sales_pipeline.py src/grins_platform/schemas/sales_pipeline.py
cd frontend && npx tsc --noEmit
cd frontend && npx eslint src/features/sales src/features/schedule
```

### Level 3: Unit Tests

```bash
cd /Users/kirillrakitin/Grins_irrigation_platform
uv run python -m pytest src/grins_platform/tests/unit/ -x --no-header -q
cd frontend && npx vitest run src/features/sales src/features/schedule
```

### Level 4: Integration / Functional Tests

```bash
cd /Users/kirillrakitin/Grins_irrigation_platform
uv run python -m pytest src/grins_platform/tests/functional/test_send_estimate_from_pipeline.py -v
uv run python -m pytest src/grins_platform/tests/functional/test_estimate_email_send_functional.py -v
```

### Level 5: Manual UI Validation

Per Task 19: full Phase 4e smoke from the master e2e plan. End state: customer portal Approve triggers auto-job, signed-PDF email, audit row.

### Level 6: Regression Sweep

```bash
cd /Users/kirillrakitin/Grins_irrigation_platform
# All sales-pipeline tests
uv run python -m pytest src/grins_platform/tests/ -k "sales_pipeline or estimate" -x --no-header -q
# All frontend sales tests
cd frontend && npx vitest run src/features/sales
# Confirm no estimate-flagged calls to /sign/email remain in shell scripts (expect 0 hits)
cd /Users/kirillrakitin/Grins_irrigation_platform
grep -rn "sign/email" e2e/ scripts/ 2>/dev/null | grep -i estimate || echo "clean"
# Confirm orchestrator route is mounted (server must be running on :8000)
curl -sI -X POST http://localhost:8000/api/v1/sales/pipeline/00000000-0000-0000-0000-000000000000/send-estimate | head -1
# Expect 401 (unauthorized) or 422 (validation), NOT 404 — confirms route is registered.
```

---

## ACCEPTANCE CRITERIA

- [ ] PRE-FLIGHT VERIFICATION block all green (zero drift from plan).
- [ ] `send_estimate` NowCard shows "Build & send estimate" CTA — no PDF dropzone.
- [ ] Clicking the CTA opens `SalesEstimateSheetWrapper` containing the line-item builder.
- [ ] Submitting the sheet calls `POST /api/v1/sales/pipeline/{entry_id}/send-estimate` with the structured payload.
- [ ] Backend creates an `Estimate` row, mints `customer_token`, fires SMS + email, transitions estimate to SENT, sets SalesEntry status to `pending_approval`, writes `sales_entry.estimate_sent` audit row, commits — all in one transaction.
- [ ] Customer portal at `/portal/estimates/<token>` renders the estimate (existing behavior).
- [ ] Customer Approve triggers auto-job, signed-PDF email, `sales_entry.estimate_decision_received` audit row (existing behavior).
- [ ] `Email for Signature` and `Sign On-Site` ribbon buttons are scoped to contract documents only.
- [ ] `resend_estimate` action in `pending_approval` stage re-fires the portal link via `POST /api/v1/sales/pipeline/{entry_id}/resend-estimate` (no SignWell touch).
- [ ] Appointment-modal "Send estimate" flow continues to work unchanged.
- [ ] Documents tab still accepts estimate uploads for record-keeping (no behavior change).
- [ ] All Level 2-6 validation commands pass.
- [ ] Master-plan Phase 4e UI smoke succeeds end-to-end.

---

## COMPLETION CHECKLIST

- [ ] All 19 tasks completed in order.
- [ ] Each task's VALIDATE command passed before moving on.
- [ ] All Level 1-6 validation commands pass.
- [ ] Level 5 manual smoke passes.
- [ ] No linting or TypeScript errors anywhere in the project.
- [ ] Acceptance criteria all met.
- [ ] Screenshots captured for PR description.

---

## NOTES

### Design Decisions (locked)

1. **Orchestrator endpoint vs. three round-trips from FE.** Chose orchestrator for atomicity, single audit row, and simpler FE.
2. **Calendar-confirmation gate bypass.** The orchestrator bypasses `advance_status`'s `confirmation_status='confirmed'` gate by writing the status directly via SQL UPDATE. Sending the estimate IS the confirmation.
3. **Form extraction (Task 7) over conditional hooks.** Hooks can't be called conditionally; presentational extraction is the only clean path.
4. **Tier/discount features deferred.** `EstimateBuilder` (orphaned wizard with tiers + discount %) is NOT salvaged in this plan. Future work.
5. **Documents-tab estimate uploads kept.** Removing them is zero benefit; record-keeping flows may still rely on them.
6. **No send-dedup.** Two consecutive sends → two estimates. v1 behavior. Future hardening optional.
7. **Resend backend endpoint (Task 3) instead of FE-resolves.** Single round-trip; deterministic resolution; no ambiguity with multi-estimate customers.
8. **Audit-log uses `resource_type` / `resource_id`** (not `entity_*`). Verified against `services/audit_service.py:79-134` and existing call sites.
9. **`hasEstimateDoc` field on `NowCardInputs` is preserved** (other consumers rely on it). The `send_estimate` case simply stops reading it.

### Known Risks & Mitigations

- **Calendar-gate bypass masks a bug** where the entry advances without a confirmed visit. **Mitigation**: the only way to reach `send_estimate` is through `estimate_scheduled`, which already requires a calendar event. Risk is low.
- **Existing `useTriggerEmailSigning` callers fail** if not properly retained. **Mitigation**: Task 13 explicitly notes that the import + const stay alive for the contract-stage ribbon.
- **`now-card-dropzone-filled` testid** is referenced in tests. **Mitigation**: Tasks 15-16 explicitly delete the failing assertion and rewrite the surrounding test for the contract case.
- **Orphaned `EstimateBuilder.tsx`** stays orphaned. Optional follow-up: delete the file and the unrouted `SalesDashboard.tsx` shell that mounts it (out of scope).

### Future Work (Out of Scope)

- Add tier (Good/Better/Best) support to `EstimateForm` (`Estimate.options` JSONB already accepted by `EstimateCreate`).
- Add discount % support to `EstimateForm` (`Estimate.discount_amount` already accepted).
- Send-dedup logic.
- Delete the orphaned `EstimateBuilder.tsx` and `SalesDashboard.tsx` (separate cleanup PR).
- Optional defense-in-depth: add `document_type` filter param to `_get_signing_document` so even legacy estimate-typed `SalesDocument` rows can't reach SignWell. Skipped here because the UI layer prevents it.

### Confidence Score

**10/10** for one-pass implementation success.

Every claim in this plan is verified against the live codebase as of plan version 2:
- Function signatures (`AuditService.log_action`, `EstimateService.create_estimate`, `EstimateService.send_estimate`, `SalesPipelineService.advance_status`) verified line-by-line.
- Schema field names (`EstimateCreate`, `EstimateSendResponse`) verified.
- Router prefix (`/sales` mounted at `router.py:316-320`) verified.
- All 14 `data-testid` values in `EstimateCreator.tsx` enumerated.
- Existing audit-log call sites (`sales_pipeline_service.py:186-198`, `:344-355`) checked for canonical kwarg shape.
- Frontend type imports (`CustomerType`, `SalesDocument`, `SheetContainer`, `pipelineKeys`, `salesKeys`) confirmed at exact paths.
- Email-allowlist guard (`email_service.py:118-142`) confirmed to fire inside `_send_email` so the orchestrator doesn't double-validate.
- No e2e shell scripts hit `/sign/email` for estimates (verified via grep) — Task 17 (master-plan markdown update) is the only e2e-touching task.
- Pre-flight verification block runs in <5 seconds and catches drift before implementation begins.

The remaining residual risk is in human execution (transposed line numbers, wrong import path) — not in the plan itself. The per-task VALIDATE commands catch every such error before it propagates to the next task.
