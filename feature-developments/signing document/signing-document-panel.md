# Signing Document Panel — Feature Spec

**Status:** Proposed
**Author:** Design pass, 2026-04-18
**Scope:** Sales pipeline — `send_estimate` and `pending_approval` stages
**Related:** CRM Changes Update 2 Req 9.3, 9.5, 14.4, 14.5, 18.1, 18.2

---

## 1. Summary

Introduce a dedicated **Signing Document** card on the sales entry detail page that surfaces which uploaded file will be sent for signature, its SignWell state, and the action to send it. Replaces the currently scattered signing controls on `SalesDetail.tsx` and makes the implicit "signing document" concept explicit in the UI.

Companion changes to `DocumentsSection` expose `document_type` at upload and flag the active signing document in the flat list.

---

## 2. Problem Statement

A user on the `send_estimate` pipeline stage clicks the advance button ("Mark Sent") and hits the error:

> "This sales entry needs a signing document on file before it can move to pending approval."

Three things are unclear from the UI:

1. **What counts as a signing document.** The documents tab shows a flat list with no indication of which file is the "signing" one, and the upload flow silently tags every PDF as `contract` regardless of intent.
2. **What action actually sets it up.** The "Mark Sent" button *looks* like the step that sends the document, but the backend gate (`SalesEntry.signwell_document_id`) is only populated by the separate "Email for Signature" or embedded-signer actions, which live in a different row of the action bar and are easy to miss.
3. **How the current state of signing is progressing.** Once SignWell has been triggered, there is no surface that shows "sent to X, awaiting signature" — the user has to infer it from whether the advance button works or not.

Net effect: a user can upload a contract and click every visible button without ever actually sending the document for signature, then be told the document is missing.

---

## 3. Current Behavior (Investigation Findings)

### 3.1 What gates the pipeline transition

The validation lives in `src/grins_platform/services/sales_pipeline_service.py:142-151`:

```python
if (
    target == SalesEntryStatus.PENDING_APPROVAL
    and not entry.signwell_document_id
):
    self.log_rejected(
        "advance_status",
        entry_id=str(entry_id),
        reason="missing_signing_document",
    )
    raise MissingSigningDocumentError(entry_id)
```

The sole gate is `SalesEntry.signwell_document_id IS NOT NULL` — a string column on the `sales_entries` table (`src/grins_platform/models/sales.py:77-80`). Having an uploaded document does **not** pass the gate; the SignWell envelope must exist.

### 3.2 How signing documents are identified

The helper that picks *which* `CustomerDocument` becomes the signing document lives at `src/grins_platform/api/v1/sales_pipeline.py:57-141`:

```python
async def _get_signing_document(
    session: AsyncSession,
    customer_id: UUID,
    sales_entry_id: UUID | None = None,
    *,
    include_legacy: bool = False,
) -> CustomerDocument | None:
    conditions = [
        CustomerDocument.customer_id == customer_id,
        CustomerDocument.document_type.in_(("estimate", "contract")),
    ]
    # ... scopes to sales_entry_id when provided ...
    # ... returns most recent by uploaded_at ...
```

Rules:

- A document qualifies only if its `document_type` is `"estimate"` or `"contract"` (`enums.py:672-684`).
- When `sales_entry_id` is supplied, the document must be scoped to that entry (prevents cross-contamination between concurrent sales entries on the same customer).
- Multiple qualifying docs → most recent `uploaded_at` wins by default; the UI has a dropdown to override (`SalesDetail.tsx:306-333`).

The SignWell ID is written in the signing endpoints `src/grins_platform/api/v1/sales_pipeline.py:312-366` (email) and `369-426` (embedded):

```python
entry.signwell_document_id = doc.get("id")
await session.commit()
```

### 3.3 Current UI limitations

| Problem | Location |
|---|---|
| Upload form hardcodes type: `"contract"` for non-images, `"photo"` for images; user cannot change it | `DocumentsSection.tsx:50` |
| No visual indicator in the documents list of which file is the signing doc | `DocumentsSection.tsx:125-165` |
| "Email for Signature" and embedded signer buttons are mixed into the pipeline action row, not grouped as signing actions | `SalesDetail.tsx:335-357` |
| Multi-signing-doc dropdown only appears conditionally inside the action row | `SalesDetail.tsx:306-333` |
| Button label "Mark Sent" on `send_estimate` suggests manual sending, but the backend gate requires SignWell automation | `types/pipeline.ts:60` |
| No indicator that SignWell has been triggered / is awaiting customer signature | nowhere in UI |
| No surface for the signed PDF when the customer signs | nowhere in UI |

---

## 4. Proposed Design

### 4.1 Overall Layout

`SalesDetail` page, top-to-bottom on the right pane:

```
+---------------------------------------------------+
|  Sales Entry Header (customer, status, metrics)   |
+---------------------------------------------------+
|  Pipeline Actions Row                             |
|    [Mark Sent / Convert to Job]  [Mark Lost]      |
+---------------------------------------------------+
|  SIGNING DOCUMENT CARD  <-- NEW                   |
|    (state-dependent contents; see 4.2)            |
+---------------------------------------------------+
|  Documents Section                                |
|    - Upload (with document_type selector)         |
|    - Flat list with [Signing doc] badge on active |
+---------------------------------------------------+
|  Internal Notes                                   |
+---------------------------------------------------+
```

The Signing Document card is **only rendered when the entry is in a pre-terminal status** where signing is meaningful:
`send_estimate`, `pending_approval`, `send_contract`.
Hidden on `schedule_estimate`, `estimate_scheduled` (no document expected yet), `closed_won`, `closed_lost` (terminal).

On `send_contract` the card reflects the contract-sending step with the same four-state model, but points at `contract`-type documents.

### 4.2 SigningDocumentCard — Component States

Four states, determined by two boolean signals and one external signal:

| Signal | Source |
|---|---|
| `hasSigningDoc` | result of `_get_signing_document(customer_id, sales_entry_id)` — at least one `estimate`/`contract` row scoped to this entry |
| `hasSignwellId` | `entry.signwell_document_id !== null` |
| `signwellStatus` | SignWell webhook state (`sent`, `viewed`, `signed`, `declined`, `canceled`) — already tracked via `src/grins_platform/api/v1/signwell_webhooks.py` |

State resolution:

```
if !hasSigningDoc                    -> State 1: No Signing Document
else if !hasSignwellId               -> State 2: Ready to Send
else if signwellStatus != 'signed'   -> State 3: Awaiting Signature
else                                 -> State 4: Signed
```

---

#### State 1 — No Signing Document

Condition: no `estimate` or `contract` document exists for this sales entry.

```
+-- Signing Document ------------------- [needs action] --+
|                                                          |
|   No estimate or contract on file yet.                   |
|                                                          |
|   Upload a document and tag it as Estimate or Contract   |
|   to send for signature.                                 |
|                                                          |
|   [  Upload Estimate  ]    [  Upload Contract  ]         |
|                                                          |
+----------------------------------------------------------+
```

- Both buttons open the native file picker and pre-fill `document_type` on the upload POST (`estimate` or `contract` respectively).
- After a successful upload → transitions to **State 2**.
- Copy is identical on `send_estimate` and `pending_approval`; on `send_contract`, the Upload Estimate button is hidden (only `contract` is valid at that stage).

Empty-state hint (tooltip on the header badge): "A signing document is required to advance past this stage."

---

#### State 2 — Ready to Send

Condition: at least one `estimate`/`contract` exists; no SignWell envelope yet.

```
+-- Signing Document ------------------- [ready to send] -+
|                                                          |
|   [pdf]  estimate_jones_apr15.pdf                        |
|          Estimate  .  1.2 MB  .  uploaded 2h ago         |
|                                                          |
|                             [  Change document  v  ]     |
|                                                          |
|   +--------------------------------------------------+   |
|   |                                                   |   |
|   |   [  Email for Signature  ]   [  Sign In-Person  ]|  |
|   |                                                   |   |
|   +--------------------------------------------------+   |
|                                                          |
+----------------------------------------------------------+
```

- Shows the currently selected signing document: file name, `document_type`, size, uploaded-age.
- `Change document` dropdown appears **only when >1 qualifying document exists** on this sales entry. Reuses the existing selector (`SalesDetail.tsx:306-333`), relocated into this card.
- Two primary actions:
  - **Email for Signature** → POST `/sales/pipeline/{id}/sign/email`. Disabled + tooltip when customer has no email on file.
  - **Sign In-Person** → opens the embedded signer iframe (existing `SignWellEmbeddedSigner` component).
- Both actions write `signwell_document_id` server-side → transitions to **State 3**.
- If the chosen document is deleted while in this state, card falls back to **State 1** (or re-resolves to another qualifying document if any remain).

---

#### State 3 — Awaiting Signature

Condition: `signwell_document_id` set; SignWell status is not yet `signed`.

```
+-- Signing Document ----------------- [awaiting signature]+
|                                                          |
|   [mail]  Sent via email to jones@example.com            |
|   [pdf]   estimate_jones_apr15.pdf                       |
|                                                          |
|   Sent 10 min ago  .  SignWell doc_abc123  .  Viewed     |
|                                                          |
|   [ Resend email ]  [ Sign In-Person instead ]  [ Cancel ]|
|                                                          |
+----------------------------------------------------------+
```

- Top line reflects the send channel:
  - Email: "Sent via email to `<email>`"
  - Embedded: "Signed in-person session in progress" (if session is active) or "Ready for in-person signing" (if session expired without completion).
- Status chip reflects webhook state: `Sent`, `Viewed`, `Declined`. On `Declined`, show the decline reason if SignWell returned one and surface a "Send again" primary action.
- Actions:
  - **Resend email** → POST `/sales/pipeline/{id}/sign/email` again with `resend=true` flag (new optional param; see §5.2).
  - **Sign In-Person instead** → opens embedded signer; reuses the existing SignWell document rather than creating a new one (if supported by SignWell) — if not, voids and recreates.
  - **Cancel** → destructive, confirm dialog: "This voids the pending SignWell envelope and returns the sales entry to the ready-to-send state." On confirm, clears `signwell_document_id` and calls SignWell void API.
- Auto-transitions to **State 4** on webhook `signed`.

---

#### State 4 — Signed

Condition: `signwell_document_id` set; SignWell status is `signed`; a `signed_contract` document has been generated.

```
+-- Signing Document ---------------------------[ signed ]-+
|                                                          |
|   [check]  Signed by customer on Apr 17, 2026 at 2:14 PM |
|   [pdf]    signed_contract_jones_apr17.pdf               |
|                                                          |
|            [  Download signed PDF  ]                     |
|                                                          |
+----------------------------------------------------------+
```

- Pulls from the `signed_contract`-type document returned by the SignWell completion webhook.
- Download action uses existing presigned-URL flow.
- If the sales entry is still on `pending_approval` at this point, show a secondary callout: "Ready to convert to job — use the action bar above."
- State is terminal from the card's perspective.

---

### 4.3 State Diagram

```
                         (upload estimate/contract)
  [ State 1: No Doc ]  ---------------------------->  [ State 2: Ready ]
                                                            |
                                                            |  (click Email / In-Person;
                                                            |   signwell_document_id set)
                                                            v
                                                    [ State 3: Awaiting ]
                                                            |
                                                            |  (webhook: signed)
                                                            v
                                                    [ State 4: Signed ]

  Transitions backward:
    - State 2 <- State 1  : none (requires upload)
    - State 1 <- State 2  : last qualifying document deleted
    - State 2 <- State 3  : Cancel (voids SignWell, clears signwell_document_id)
    - State 3 <- State 4  : none (signed is terminal for the card)
```

### 4.4 Component Props & Data Sources

```ts
interface SigningDocumentCardProps {
  entry: SalesEntry;                // includes signwell_document_id
  customerEmail: string | null;     // for email-disabled tooltip
  onStateChange?: () => void;       // refetch hook for parent
}

// Internally:
const { data: signingDocs } = useSigningDocuments(entry.customer_id, entry.id);
// -> filtered to document_type IN ('estimate', 'contract')
// -> scoped to sales_entry_id
// -> sorted by uploaded_at desc

const { data: signwellStatus } = useSignwellStatus(entry.signwell_document_id);
// -> polls or subscribes to webhook state; returns 'sent' | 'viewed' | 'signed' | 'declined' | 'canceled'

const { data: signedContract } = useSignedContractDoc(entry.customer_id, entry.id);
// -> filtered to document_type = 'signed_contract', scoped to entry
```

React Query keys:

```ts
export const signingKeys = {
  all: ['signing'] as const,
  forEntry: (id: string) => [...signingKeys.all, 'entry', id] as const,
  status: (signwellId: string) => [...signingKeys.all, 'status', signwellId] as const,
};
```

---

### 4.5 DocumentsSection Changes

#### 4.5.1 Upload form with `document_type` selector

Replace the single-click `[Upload]` button (`DocumentsSection.tsx:107-116`) with a popover/dialog:

```
+-- Upload Document ----------+
|                             |
|  File:  [ Choose file... ]  |
|                             |
|  Type:  (o) Estimate         |
|         ( ) Contract         |
|         ( ) Photo            |
|         ( ) Diagram          |
|         ( ) Reference        |
|                             |
|  Optional: scope to this    |
|  sales entry                |
|  [x] Link to current entry  |
|                             |
|         [ Cancel ] [ Upload ]|
+-----------------------------+
```

- Default selection: infer from mime type (image → Photo, PDF/doc → Estimate) but let user override.
- "Link to current entry" checkbox maps to `sales_entry_id` query param on upload. Default **on** when rendered from a sales entry page; hidden when rendered from the customer detail page (where no sales entry context exists).
- Remove hardcoded logic at `DocumentsSection.tsx:50`:

  ```ts
  documentType: file.type.startsWith('image/') ? 'photo' : 'contract',
  ```

  Replace with user selection.

#### 4.5.2 Signing-doc badge in flat list

Each `document-row` (`DocumentsSection.tsx:125-165`) reads whether it's the active signing doc from the parent context:

```
+-- Documents ---------------------------- [Upload v] +
|                                                     |
|  [pdf] estimate_jones_apr15.pdf  [signing doc]      |
|        estimate . 1.2 MB . Apr 15                   |
|                              [download] [delete]    |
|                                                     |
|  [pdf] old_estimate.pdf                             |
|        estimate . 900 KB . Apr 10                   |
|                              [download] [delete]    |
|                                                     |
|  [img] site_photo.jpg                               |
|        photo . 340 KB . Apr 15                      |
|                              [download] [delete]    |
|                                                     |
|  [pdf] signed_contract_jones_apr17.pdf  [signed]    |
|        signed_contract . 1.3 MB . Apr 17            |
|                              [download] [delete]    |
|                                                     |
+-----------------------------------------------------+
```

- `[signing doc]` badge only on the row that `_get_signing_document` currently resolves to.
- `[signed]` badge on any `signed_contract`-type row.
- Badge style matches the pipeline status chips in `SALES_STATUS_CONFIG` (amber for pending, emerald for signed) for visual consistency.

#### 4.5.3 Delete guardrails

On delete of a document that is currently the active signing doc (badge `[signing doc]`):

- If `signwell_document_id` references it → confirm dialog:
  "This document has been sent to the customer via SignWell. Deleting it will also cancel the pending signature request. Continue?"
  On confirm: call SignWell void → clear `signwell_document_id` → delete document.
- If no SignWell envelope yet → normal confirm: "Delete this document?"

On delete of a `signed_contract` row → block with error: "Signed contracts cannot be deleted for compliance. Archive the sales entry instead."

---

### 4.6 StatusActionButton Changes

The `send_estimate` stage's advance button currently shows "Mark Sent" (`types/pipeline.ts:60`). Two options:

#### Option A (light) — Rename only

```ts
send_estimate: {
  label: 'Send Estimate',
  className: 'bg-violet-100 text-violet-700',
  action: 'Move to Pending Approval',  // was: 'Mark Sent'
},
```

- Clarifies the button is a pipeline step, not a send action.
- The user still clicks two buttons: "Email for Signature" (in the signing card) then "Move to Pending Approval" (in the action bar).

#### Option B (bold, **recommended**) — Auto-advance on send

Modify `/sign/email` and `/sign/embedded` (`sales_pipeline.py:312-426`) to auto-advance the status on successful send:

```python
# after entry.signwell_document_id = doc.get("id")
if SalesEntryStatus(entry.status) == SalesEntryStatus.SEND_ESTIMATE:
    entry.status = SalesEntryStatus.PENDING_APPROVAL.value
    entry.updated_at = datetime.now(tz=timezone.utc)
    # existing log_completed...
await session.commit()
```

- Matches the user's mental model: "I sent it" = "it's with the customer now."
- Removes the "Mark Sent" button entirely on `send_estimate` (button hides when `config.action === null`).
- Preserves the gate behavior — the SignWell send **is** the advance; any manual advance attempt without the send still fails the gate as before.
- Admin override dropdown (`ALL_STATUSES` in `SalesDetail.tsx`) still allows manual status changes for edge cases.

**Recommendation:** Option B. If adopted, also update `types/pipeline.ts:55` so `estimate_scheduled.action` reflects that "Send Estimate" leads into the signing card rather than advancing directly.

---

## 5. API / Data Model

### 5.1 Existing endpoints used (no change)

| Endpoint | Purpose |
|---|---|
| `GET /customers/{id}/documents` | list all customer documents |
| `POST /customers/{id}/documents?document_type=...&sales_entry_id=...` | upload with type + scope |
| `DELETE /customers/{id}/documents/{doc_id}` | delete document |
| `POST /sales/pipeline/{id}/sign/email` | create SignWell email envelope |
| `POST /sales/pipeline/{id}/sign/embedded` | create SignWell embedded session |
| `POST /sales/pipeline/{id}/advance` | advance one pipeline step |

### 5.2 New / modified endpoints

| Change | Purpose |
|---|---|
| `POST /sales/pipeline/{id}/sign/email?resend=true` | optional param for resending the email without creating a new SignWell doc |
| `POST /sales/pipeline/{id}/sign/cancel` | **new** — void the current SignWell envelope and clear `signwell_document_id`. Returns the entry to State 2. |
| `GET /sales/pipeline/{id}/signwell-status` | **new** — returns `{status, last_event_at, recipient}` for the current envelope. Thin wrapper over whatever the webhook table stores. Used by `useSignwellStatus`. |
| `POST /sales/pipeline/{id}/sign/email` (Option B) | on success, auto-advance `send_estimate -> pending_approval` |
| `POST /sales/pipeline/{id}/sign/embedded` (Option B) | same auto-advance |

### 5.3 Data model

No schema changes. All required fields already exist:

- `customer_documents.document_type` (enum string)
- `customer_documents.sales_entry_id` (nullable UUID FK)
- `sales_entries.signwell_document_id` (nullable string)
- SignWell webhook events are already persisted via `signwell_webhooks.py`; the new `GET /signwell-status` endpoint reads from that store.

---

## 6. File Impact Summary

### Frontend

| File | Change | Size |
|---|---|---|
| `frontend/src/features/sales/components/SigningDocumentCard.tsx` | **new** — the four-state panel | ~300 lines |
| `frontend/src/features/sales/components/SigningDocumentCard.test.tsx` | **new** — state coverage tests | ~200 lines |
| `frontend/src/features/sales/components/SalesDetail.tsx` | mount `<SigningDocumentCard>`; remove signing actions from action row (lines 306-357); keep advance button only | ~-50 / +10 lines |
| `frontend/src/features/sales/components/DocumentsSection.tsx` | upload popover with type selector; signing-doc badge row logic; delete guardrail | ~+80 lines |
| `frontend/src/features/sales/components/DocumentsSection.test.tsx` | tests for new upload form + badge | ~+60 lines |
| `frontend/src/features/sales/hooks/useSalesPipeline.ts` | add `useSigningDocuments`, `useSignwellStatus`, `useSignedContractDoc`, `useCancelSignwell`, `useResendSignwellEmail` | ~+100 lines |
| `frontend/src/features/sales/api/salesPipelineApi.ts` | add `cancelSignwell`, `getSignwellStatus`, `resendEmail` methods | ~+30 lines |
| `frontend/src/features/sales/types/pipeline.ts` | adjust `SALES_STATUS_CONFIG.send_estimate.action` per Option A or B | ~5 lines |
| `frontend/src/features/sales/index.ts` | export `SigningDocumentCard` | ~2 lines |

### Backend

| File | Change | Size |
|---|---|---|
| `src/grins_platform/api/v1/sales_pipeline.py` | add `POST /sign/cancel`, `GET /signwell-status`; Option B auto-advance in `/sign/email` and `/sign/embedded` | ~+80 lines |
| `src/grins_platform/services/sales_pipeline_service.py` | add `cancel_signwell()` method; Option B: extract advance-to-pending helper reused by sign endpoints | ~+40 lines |
| `src/grins_platform/schemas/sales_pipeline.py` | add `SignwellStatusResponse` schema | ~+15 lines |
| `src/grins_platform/integrations/signwell.py` (or equivalent) | wrap SignWell void API | ~+20 lines |
| `src/grins_platform/tests/unit/test_sales_pipeline_and_signwell.py` | cancel + auto-advance + resend cases | ~+150 lines |
| `src/grins_platform/tests/functional/test_sales_pipeline_functional.py` | state 2 -> 3 -> 2 (cancel) -> 3 -> 4 flow test | ~+80 lines |

---

## 7. Implementation Phases

### Phase 1 — Upload type selector (unblocks UX without backend changes)

- Change `DocumentsSection.tsx` upload flow to expose `document_type` radio buttons and `sales_entry_id` linkage checkbox.
- No backend changes; the API already accepts `document_type` as a query param.
- Ship alone as a small PR.

### Phase 2 — Signing Document Card (read-only states first)

- Add `SigningDocumentCard.tsx` covering States 1, 2, 4.
- State 3 shows "Sent" but without live webhook status polling yet — falls back to static "Awaiting signature".
- Relocate the existing "Email for Signature" and embedded-signer controls into the card; remove them from `SalesDetail` action row.
- Add the `[signing doc]` / `[signed]` badges to `DocumentsSection` rows.

### Phase 3 — Live SignWell status + cancel

- Implement `GET /sales/pipeline/{id}/signwell-status` endpoint.
- Add `useSignwellStatus` hook with React Query polling (30s) or SSE if available.
- Implement `POST /sales/pipeline/{id}/sign/cancel` backend + frontend wiring for the State 3 "Cancel" action.
- Add the resend-email flow.

### Phase 4 — Auto-advance (Option B)

- Modify `/sign/email` and `/sign/embedded` to auto-advance `send_estimate -> pending_approval`.
- Remove the `send_estimate` advance-button label (`config.action = null`).
- Update tests in `test_sales_pipeline_functional.py` and `test_sales_pipeline_and_signwell.py` for the new expected behavior.
- Communicate the behavior change to the user before shipping; this is a flow change, not just a UI change.

---

## 8. Acceptance Criteria

### Signing Document Card

- **AC-1** On a `send_estimate` entry with no uploaded documents, the card renders State 1 with both upload buttons.
- **AC-2** Clicking "Upload Estimate" opens a file picker; selecting a valid PDF posts to the upload endpoint with `document_type=estimate` and transitions the card to State 2.
- **AC-3** On an entry with one `estimate` document and `signwell_document_id = null`, the card renders State 2 with that document shown and no "Change document" selector.
- **AC-4** On an entry with two or more `estimate`/`contract` documents, the card renders State 2 with a "Change document" dropdown listing all qualifying docs; the most-recent is selected by default.
- **AC-5** Clicking "Email for Signature" in State 2 calls `/sign/email`, sets `signwell_document_id`, and (Option B) auto-advances status to `pending_approval`. Card transitions to State 3.
- **AC-6** Clicking "Sign In-Person" in State 2 opens the embedded signer iframe; on completion, card transitions to State 4.
- **AC-7** In State 3, the card shows send-channel, timestamp, SignWell doc ID, and current webhook status chip.
- **AC-8** In State 3, clicking "Cancel" opens a confirm dialog; on confirm, the SignWell envelope is voided and the card returns to State 2.
- **AC-9** On webhook `signed`, the card transitions to State 4 without a page refresh.
- **AC-10** State 4 shows the signed PDF metadata and a functional download button.
- **AC-11** The card is hidden on `schedule_estimate`, `estimate_scheduled`, `closed_won`, `closed_lost`.

### Documents Section

- **AC-12** The upload button opens a form with a file picker and a `document_type` radio group.
- **AC-13** Uploading with `document_type = estimate` creates a `CustomerDocument` row with that type; API contract unchanged.
- **AC-14** A document that matches the current signing-doc resolution displays a `[signing doc]` badge; all other rows do not.
- **AC-15** A `signed_contract` row displays a `[signed]` badge.
- **AC-16** Deleting the active signing document while a SignWell envelope is live shows a confirm dialog mentioning the cancellation; on confirm, the envelope is voided and the document is deleted.
- **AC-17** Deleting a `signed_contract` row is blocked with an error toast.

### Backend

- **AC-18** `POST /sales/pipeline/{id}/sign/cancel` voids the SignWell envelope via the SignWell API, clears `signwell_document_id`, and returns 200 with the updated entry.
- **AC-19** `GET /sales/pipeline/{id}/signwell-status` returns `{status, last_event_at, recipient}` for the current envelope, or 404 if `signwell_document_id` is null.
- **AC-20** (Option B) A successful `POST /sign/email` on an entry in `send_estimate` status advances it to `pending_approval` in the same transaction; failure path does not advance.

---

## 9. Edge Cases

- **Customer with no email.** "Email for Signature" button is disabled with tooltip: "Customer has no email on file. Add one on the customer page or use Sign In-Person." No silent failure.
- **Concurrent sales entries on same customer.** `_get_signing_document` already scopes by `sales_entry_id`. The card must always pass `sales_entry_id` to the signing-docs query; never fall back to customer-level docs.
- **Document uploaded without `sales_entry_id` link.** Currently `_get_signing_document` has an `include_legacy` flag for this. The new card should surface these under "Change document" when the strict query returns empty, with an "unlinked" badge. Prompt the user to link the document on selection.
- **SignWell envelope expired.** Webhook state becomes `canceled` or similar. Treat as State 2 (ready to re-send) with a "The previous signature request expired" callout. Clear `signwell_document_id` on the backend side when expiration is detected.
- **Customer declines.** Treat as State 3 with a red chip "Declined" and the decline reason. Primary action becomes "Send again" (clears the envelope, returns to State 2, re-sends in one click).
- **Admin manually overrides status.** If an admin uses the status dropdown (`SalesDetail.tsx:258-263`) to jump to `pending_approval` without a signwell_document_id, the backend gate currently blocks it. Verify the override path (`POST /override`) either (a) also enforces the gate, or (b) sets an `override_flag` marker that the card displays as a warning: "Status was manually advanced without a signature."
- **Entry on `send_contract` stage.** The card's document filter should prefer `contract` over `estimate` at this stage (estimates are for the prior stage). Consider splitting into two variants or parameterizing by stage.
- **Document deleted while SignWell envelope active.** The SignWell side still has the PDF; deletion of the S3 file doesn't affect the signing flow. But the UI would lose the ability to show the doc metadata. Either: (a) soft-delete — hide from list but retain row until envelope is voided; (b) block the delete behind the guardrail in §4.5.3.

---

## 10. Open Questions

1. **Option A vs Option B on auto-advance.** Recommendation is B, but it changes a publicly observable flow. Confirm with the user before Phase 4.
2. **Polling cadence vs SSE for `signwellStatus`.** SignWell webhooks already fire server-side. Polling every 30s is simple; SSE or WebSocket is nicer UX but a bigger lift. Start with polling.
3. **Should the card appear on the customer detail page** (outside of a sales entry context)? Likely no — signing is inherently per-sales-entry. Customer page shows documents only.
4. **Branding / legal text.** Do we need a "by sending, you authorize..." disclaimer anywhere on the card? Check with legal before Phase 2 ships.
5. **Mobile layout.** The four-state card is designed for desktop widths. Confirm the breakpoint behavior — on narrow widths, stack the two primary-action buttons vertically.
6. **Override flag surfacing.** When `entry.override_flag` is set (status was manually advanced), should the card render a warning banner? Currently `SalesPipeline.tsx:243-244` just shows a small amber marker in the list; the detail page could be more prominent.

---

## Appendix A — State-to-Backend Condition Cheat Sheet

| Card State | `entry.status` | `hasSigningDoc` | `hasSignwellId` | `signwellStatus` |
|---|---|---|---|---|
| 1 | `send_estimate` / `pending_approval` / `send_contract` | false | false | n/a |
| 2 | same | true | false | n/a |
| 3 | same | true | true | `sent` / `viewed` / `declined` |
| 4 | same | true | true | `signed` |

## Appendix B — Color / Badge Reference

Matches existing `SALES_STATUS_CONFIG` palette:

| Badge | Color class | Used for |
|---|---|---|
| `[needs action]` | `bg-orange-100 text-orange-700` | State 1 header |
| `[ready to send]` | `bg-violet-100 text-violet-700` | State 2 header |
| `[awaiting signature]` | `bg-amber-100 text-amber-700` | State 3 header |
| `[signed]` | `bg-emerald-100 text-emerald-700` | State 4 header + signed_contract row |
| `[signing doc]` | `bg-slate-100 text-slate-700` | active signing doc row |
| `[declined]` | `bg-red-100 text-red-700` | State 3 when declined |
