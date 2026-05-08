# Feature: Stripe Payment Link audit row + inbox `from_phone` normalization

The following plan should be complete, but it's important that you validate documentation and codebase patterns and task sanity before you start implementing.

Pay special attention to naming of existing utils, types, and models. Import from the right files, etc.

## Feature Description

Two informational findings from the 2026-05-06 master E2E sign-off (`e2e-screenshots/master-plan/runs/2026-05-06/_candidate-findings.md`) need code-level resolution:

1. **14.A — Stripe Payment Link auto-creation is silent on invoice POST.** When `POST /api/v1/invoices` succeeds and `_attach_payment_link` creates a live Stripe Payment Link inline (Architecture C, 2026-04-28), no `audit_log` row is written. Operators have no breadcrumb for "when was this link first attached, by whom?" Compare with the parallel auto-job flow on estimate approval (`estimate.auto_job_created`), which already writes an audit row.

2. **20.A — `from_phone` format inconsistent across inbox source tables.** The inbox aggregator UNIONs four source tables (`job_confirmation_responses`, `reschedule_requests`, `campaign_responses`, `communications`) plus a fifth gated source (`sms_consent_record` via `text_stop`/`text_start`). Each writer stored phones differently (E.164 in some, dashed `952-737-3312` in others); the inbox merges raw without normalizing, so the same customer can appear with different `from_phone` strings depending on which inbound landed. The repo already has a hardened `normalize_to_e164` helper (`services/sms/phone_normalizer.py`); we apply it at the inbox aggregation seam.

## User Story

As an **admin operator triaging the unified inbox and auditing payment activity**
I want **a single normalized phone format on every inbox row and an audit-log breadcrumb when a Payment Link is auto-created on invoice POST**
So that **I can confidently group inbound replies by sender and reconstruct who/when an invoice's Payment Link first went live**.

## Problem Statement

**14.A**: `POST /api/v1/invoices` → `InvoiceService.create_invoice` (`services/invoice_service.py:330-353`) calls `_attach_payment_link` (lines 758-837) which, on success, persists `stripe_payment_link_id` / `stripe_payment_link_url` / `stripe_payment_link_active` via `invoice_repository.update(...)` (lines 827-832) and mirrors them on the in-memory invoice (lines 835-837). No audit row is written. The audit log already documents canonical action strings in `services/audit_service.py:18-37` and the auto-job flow at `services/estimate_service.py:848-880` is the exact pattern to mirror.

**20.A**: `services/inbox_service.py` builds `InboxItem` rows from each source table inline:

- Line 367: `from_phone=row.from_phone` (job_confirmation_responses; usually E.164 from provider parsing)
- Line 409: `from_phone=None` (reschedule_requests; no source phone column — leave alone)
- Line 455: `from_phone=row.phone` (campaign_responses; **mixed dashed and E.164**)
- Line 496: `from_phone=None` (communications; no source phone column — leave alone)
- Line 555: `from_phone=row.phone_number` (sms_consent_record; **mixed legacy formats**)

The schema field at `schemas/inbox.py:62-65` documents intent ("E.164 or provider canonical form") but enforces nothing.

## Solution Statement

**14.A**:

1. Wire `audit_service: AuditService | None = None` into `InvoiceService.__init__` (constructor at `services/invoice_service.py:191-236`).
2. Add private helper `_audit_payment_link_auto_created(invoice, *, actor_id, actor_role)` mirroring `services/estimate_service.py:848-880`. Best-effort, never raises.
3. Call it at the end of `_attach_payment_link` after the successful update (lines 827-832), only when a fresh `link_id` was created (not on the early-return idempotent branch).
4. Plumb `actor_id` + `actor_role` from the API endpoint (`api/v1/invoices.py:158-186`) through `create_invoice` as optional kwargs. `ip_address` / `user_agent` stay `None` for now (adding a `Request` dependency is out of scope).
5. Update `get_invoice_service` DI factory (`api/v1/invoices.py:69-101`) to construct `AuditService()` and pass it to `InvoiceService`.
6. Register the new action `stripe.payment_link.auto_created` in the `audit_service.py` docstring "Canonical action strings" list (lines 18-37) so future contributors see it.
7. Add a frontend badge color in the audit log UI map (`frontend/src/features/accounting/components/AuditLog.tsx:20-32`).

**20.A**:

1. Add a private helper `_safe_normalize_phone(raw: str | None) -> str | None` at module level in `services/inbox_service.py` that imports `normalize_to_e164` and `PhoneNormalizationError` from `services/sms/phone_normalizer.py` and returns `None` on any error / empty input. Pure function — easy to unit test.
2. Replace the three raw assignments (`from_phone=row.from_phone` line 367, `from_phone=row.phone` line 455, `from_phone=row.phone_number` line 555) with `from_phone=_safe_normalize_phone(row.<field>)`.
3. Tighten the `InboxItem.from_phone` field description in `schemas/inbox.py:62-65` to "E.164 (`+1NXXXXXXX`) when derivable, else `None`".

No alembic migration, no backfill — the helper applies normalization at the read seam. Existing inbound rows continue to land in raw form in their source tables; only the inbox projection canonicalizes.

## Feature Metadata

**Feature Type**: Bug Fix (informational findings; both behaviors silent, audit + display gaps)
**Estimated Complexity**: Low
**Primary Systems Affected**:
- `src/grins_platform/api/v1/invoices.py`
- `src/grins_platform/services/invoice_service.py`
- `src/grins_platform/services/inbox_service.py`
- `src/grins_platform/services/audit_service.py` (docstring only)
- `src/grins_platform/schemas/inbox.py` (field description only)
- `frontend/src/features/accounting/components/AuditLog.tsx` (one map entry)
**Dependencies**: None new. `AuditService`, `normalize_to_e164`, `PhoneNormalizationError` all already shipped.

---

## CONTEXT REFERENCES

### Relevant Codebase Files — IMPORTANT: YOU MUST READ THESE BEFORE IMPLEMENTING

**14.A — Stripe Payment Link audit row**

- `src/grins_platform/api/v1/invoices.py:69-101` — `get_invoice_service` DI factory. Add `AuditService` here and pass to `InvoiceService(...)`.
- `src/grins_platform/api/v1/invoices.py:158-186` — `create_invoice` route handler. Pass `actor_id=_current_user.id`, `actor_role=_current_user.role` to `service.create_invoice(...)`.
- `src/grins_platform/services/invoice_service.py:191-236` — `InvoiceService.__init__`. Add `audit_service` kwarg. **Place alongside other optional service kwargs (after `email_service`).**
- `src/grins_platform/services/invoice_service.py:330-353` — `create_invoice` method. Signature gets `actor_id` + `actor_role` kwargs; pass them into `_attach_payment_link`.
- `src/grins_platform/services/invoice_service.py:758-837` — `_attach_payment_link`. New audit call goes after the `invoice_repository.update(...)` at lines 827-832 and the in-memory mirror at 835-837, **only on the success branch where `link_id` is not None** (skip the no-op early-return at lines 772-777 and the `$0` branch at line 825).
- `src/grins_platform/services/estimate_service.py:848-880` — **PATTERN TO MIRROR EXACTLY**. `_audit_auto_job_created`: best-effort (`if self.audit_service is None: return`), wrapped in `try/except` that logs `log_failed` rather than raising, awaits `self.audit_service.log_action(self.repo.session, action=..., resource_type=..., resource_id=..., details={...}, ip_address=..., user_agent=...)`.
- `src/grins_platform/services/audit_service.py:79-134` — `log_action` signature. **Kwargs-only after `db: AsyncSession`** (note the `*,` at line 82). Required: `action`, `resource_type`. Optional: everything else.
- `src/grins_platform/services/audit_service.py:18-37` — canonical action strings docstring. **Add `stripe.payment_link.auto_created` to this list** alongside `estimate.auto_job_created`. Group with `estimate.*` entries since they share the same actor/source semantics.
- `src/grins_platform/services/audit_service.py:7-42` — `details` JSONB discriminator contract. New rows MUST include `actor_type` and `source` keys. For the auto-create on invoice POST: `actor_type="staff"` (manager/admin clicked "Create"), `source="admin_ui"`.
- `src/grins_platform/repositories/audit_log_repository.py:37-95` — `create()` repository method. UUIDs accepted directly; `flush` + `refresh` happen here. Confirms the audit write is sync within the request.
- `src/grins_platform/models/audit_log.py` — model columns: `id, actor_id, actor_role, action, resource_type, resource_id, details (JSONB), ip_address, user_agent, created_at`.
- `src/grins_platform/api/v1/auth_dependencies.py:301-303` — `CurrentActiveUser`, `AdminUser`, `ManagerOrAdminUser` aliases. The invoice POST uses `ManagerOrAdminUser` (line 160) which resolves to a `Staff` instance with `.id` and `.role`.

**20.A — Inbox phone normalization**

- `src/grins_platform/services/inbox_service.py:1-85` — module imports + module-level helpers. **Add `_safe_normalize_phone` here**, alongside `_classify_triage` / `_matches_filter`.
- `src/grins_platform/services/inbox_service.py:36-52` — current imports. Add `from grins_platform.services.sms.phone_normalizer import PhoneNormalizationError, normalize_to_e164`.
- `src/grins_platform/services/inbox_service.py:360-377` — `_fetch_confirmation_responses` `InboxItem(...)` construction; line 367 is `from_phone=row.from_phone`.
- `src/grins_platform/services/inbox_service.py:421-463` — `_fetch_campaign_responses` construction; line 455 is `from_phone=row.phone`.
- `src/grins_platform/services/inbox_service.py:508-565` — `_fetch_consent_records` construction; line 555 is `from_phone=row.phone_number`.
- `src/grins_platform/services/inbox_service.py:379-419` — `_fetch_reschedule_requests`; line 409 is `from_phone=None`. **DO NOT CHANGE — source has no phone column.**
- `src/grins_platform/services/inbox_service.py:465-506` — `_fetch_communications`; line 496 is `from_phone=None`. **DO NOT CHANGE — source has no phone column.**
- `src/grins_platform/services/sms/phone_normalizer.py:1-79` — `normalize_to_e164(phone: str) -> str` and `PhoneNormalizationError(ValueError)`. **Raises** on empty/None/letters/extension/invalid area code/FCC test number. Wrap with try/except in the helper. No `phonenumbers` library dependency — the function is pure regex + NANP rules.
- `src/grins_platform/schemas/inbox.py:62-65` — `from_phone` Pydantic field description. Tighten to reflect new invariant.
- `src/grins_platform/models/campaign_response.py:57` — `phone: Mapped[str]` VARCHAR(32). Mixed dashed / E.164 source.
- `src/grins_platform/models/job_confirmation.py:66` — `from_phone: Mapped[str]` VARCHAR(20). Provider-sourced; usually E.164.
- `src/grins_platform/models/sms_consent_record.py:65` — `phone_number: Mapped[str]` VARCHAR(20). Mixed legacy formats.

### Test pattern references

- `src/grins_platform/tests/unit/test_lead_service_move_audit_actor.py:1-110` — **AUDIT TEST PATTERN TO MIRROR**. Patches `grins_platform.services.audit_service.AuditService`, replaces with `AsyncMock()` instance, asserts `mock_audit.log_action.assert_awaited_once()` and inspects `mock_audit.log_action.call_args.kwargs`.
- `src/grins_platform/tests/unit/test_invoice_service.py:1-115` — `TestInvoiceServiceCreateInvoice`. Already has fixtures for `mock_invoice_repo`, `mock_job_repo`, plus `_create_mock_job` and `_create_mock_invoice` helpers. Extend the `service` fixture to optionally accept `audit_service`. Mock invoice already exposes `stripe_payment_link_id` etc. (lines 109-114).
- `src/grins_platform/tests/unit/test_inbox_service.py:1-80` — **INBOX TEST PATTERN TO MIRROR**. Module-level `_make_item` factory, `@pytest.mark.unit` class-based tests with `pytest.mark.parametrize` for the dispatch table cases.
- `src/grins_platform/tests/unit/test_phone_variants_and_normalizer.py` — covers `normalize_to_e164`. Don't duplicate — only test the new `_safe_normalize_phone` wrapper's None / error-swallow behavior.

### Confirmed facts (no need to re-verify before editing)

- `InvoiceService` does NOT currently have `audit_service` attribute (`grep audit_service src/grins_platform/services/invoice_service.py` returns zero matches). This adds it.
- `AuditService.log_action` first positional arg is `db: AsyncSession`; after that all kwargs (`*,` separator at line 82). The `EstimateService._audit_auto_job_created` call passes `self.repo.session` for `db`. For `InvoiceService` use `self.invoice_repository.session` (the repository exposes `session` — confirmed by `_get_settings_service` at line 252 doing `BusinessSettingService(self.invoice_repository.session)`).
- `_current_user.role` exists on `Staff` model (used elsewhere in the API layer).
- `frontend/src/features/accounting/components/AuditLog.tsx:20-32` — `ACTION_COLORS` is a plain string-keyed object map; adding one entry won't break the renderer (the component renders unknown actions with a default badge style).
- `InboxItem` is a Pydantic v2 BaseModel with `model_config = ConfigDict(from_attributes=True)` (`schemas/inbox.py:46`). `from_phone: str | None` accepts None at construction.
- The fifth source `sms_consent_record` is gated by env `INBOX_SHOW_CONSENT_FLIPS=true`. Tests for `_fetch_consent_records` already mock this branch.

### Relevant Documentation — YOU SHOULD READ THESE BEFORE IMPLEMENTING

- [Stripe Payment Links — Metadata + identifying source](https://docs.stripe.com/payment-links#use-cases) — confirms the `stripe.PaymentLink.create` payload already includes `metadata.invoice_id` (verified at `services/stripe_payment_link_service.py:102-114`). The new audit row is internal-only; no Stripe API changes.
- [FastAPI Dependency Injection — sub-deps](https://fastapi.tiangolo.com/tutorial/dependencies/sub-dependencies/) — `get_invoice_service` is a synchronous factory; constructing `AuditService()` inline (it's a stateless service) is the same pattern already used for `CustomerService`, `EmailService`, etc.
- [Pydantic v2 — Field description](https://docs.pydantic.dev/latest/concepts/fields/#field-description) — description-only updates do not change validation or serialization.

### Patterns to Follow

**Naming Conventions:**

- Audit action: dot-separated `<resource>.<verb>[.<modifier>]`, all lowercase. Existing examples: `estimate.auto_job_created`, `appointment.confirm_repeat`, `consent.opt_out_sms`. **Use `stripe.payment_link.auto_created`** — `stripe` as resource family signals it's a Stripe-side artifact.
- Private async helper methods on services use leading underscore + verb-noun: `_audit_payment_link_auto_created`, mirrors `_attach_payment_link`, `_audit_auto_job_created`.
- Module-level helper functions in services use leading underscore: `_safe_normalize_phone`, mirrors `_classify_triage`, `_sort_key`.

**Error Handling (audit best-effort):**

```python
# services/estimate_service.py:858-880 — exact pattern to mirror
if self.audit_service is None:
    return
try:
    await self.audit_service.log_action(
        self.repo.session,
        action="estimate.auto_job_created",
        resource_type="estimate",
        resource_id=estimate.id,
        details={
            "job_id": str(job_id),
            "branch": branch,
            "actor_type": "customer",
            "source": "customer_portal",
        },
        ip_address=ip_address,
        user_agent=user_agent,
    )
except Exception as e:
    self.log_failed(
        "audit_auto_job_created",
        error=e,
        estimate_id=str(estimate.id),
    )
```

**Phone normalization wrapper pattern:**

```python
# Module-level in inbox_service.py — mirrors _classify_triage / _sort_key style
def _safe_normalize_phone(raw: str | None) -> str | None:
    """Normalize a phone string from a source table to E.164.

    Returns None for empty / unparseable input rather than raising —
    inbox aggregation must keep streaming even when one row's phone is
    malformed (legacy data, out-of-band imports).
    """
    if not raw:
        return None
    try:
        return normalize_to_e164(raw)
    except PhoneNormalizationError:
        return None
```

**Logging Pattern:**

- `LoggerMixin` provides `self.log_started`, `self.log_completed`, `self.log_failed`. Audit write failures use `log_failed` (see `estimate_service.py:876-880`). Phone normalization failures should not log per-row — that would flood production logs; just return None silently.

---

## IMPLEMENTATION PLAN

### Phase 1: Foundation

Wire the dependency-injection seams without changing call sites.

**Tasks:**
- Add `audit_service: AuditService | None = None` kwarg to `InvoiceService.__init__`.
- Add `from grins_platform.services.audit_service import AuditService` to imports under `TYPE_CHECKING` block.
- Update `get_invoice_service` factory in `api/v1/invoices.py` to pass `audit_service=AuditService()`.
- Add `_safe_normalize_phone` module-level helper to `services/inbox_service.py` and import `normalize_to_e164` + `PhoneNormalizationError`.

### Phase 2: Core Implementation

Apply the helpers at the targeted call sites.

**Tasks:**
- Add `_audit_payment_link_auto_created` private method to `InvoiceService` mirroring `EstimateService._audit_auto_job_created`.
- Call it from `_attach_payment_link` after a successful fresh link creation (after lines 835-837).
- Replace `from_phone=row.from_phone` (line 367), `from_phone=row.phone` (line 455), `from_phone=row.phone_number` (line 555) with `_safe_normalize_phone(...)`.
- Plumb `actor_id` + `actor_role` kwargs through `InvoiceService.create_invoice` and `InvoiceService._attach_payment_link`.

### Phase 3: Integration

Surface the new action string and tighten the schema description.

**Tasks:**
- Update API endpoint `create_invoice` (`api/v1/invoices.py:158-186`) to pass `actor_id=_current_user.id, actor_role=_current_user.role` to `service.create_invoice(data, actor_id=..., actor_role=...)`.
- Add `stripe.payment_link.auto_created` to the audit_service.py canonical-actions docstring.
- Tighten `InboxItem.from_phone` description in `schemas/inbox.py:62-65` to "E.164 (`+1NXXXXXXX`) when derivable, else `None`".
- Add `'stripe.payment_link.auto_created'` to the frontend `ACTION_COLORS` map in `AuditLog.tsx`.

### Phase 4: Testing & Validation

**Tasks:**
- Unit-test `_safe_normalize_phone` for the four input categories: dashed, E.164, malformed, None.
- Unit-test `_audit_payment_link_auto_created` — best-effort no-op when audit_service None, kwargs-correct call when present, swallows exceptions.
- Unit-test `create_invoice` — confirms audit_service.log_action is awaited once with `action="stripe.payment_link.auto_created"` and `resource_id=invoice.id` after a successful link attach.
- Run full pytest suite + ruff + mypy.

---

## STEP-BY-STEP TASKS

IMPORTANT: Execute every task in order, top to bottom. Each task is atomic and independently testable.

### 1. UPDATE `src/grins_platform/services/invoice_service.py` — add AuditService import + constructor kwarg

- **IMPLEMENT**:
  - Inside the `TYPE_CHECKING:` block (lines 52-65), add `from grins_platform.services.audit_service import AuditService` alongside the other service-type imports.
  - Add `audit_service: AuditService | None = None,` to `__init__` signature (lines 191-202) — place it after `email_service`.
  - Add `self.audit_service = audit_service` to the `__init__` body (lines 228-236) — place it after `self.email_service = email_service`.
  - Extend the `__init__` docstring (lines 203-227) with one line: `audit_service: Optional :class:`AuditService` used to record Payment Link auto-creation breadcrumbs (canonical action ``stripe.payment_link.auto_created``).`
- **PATTERN**: `services/estimate_service.py:93,128` — same `audit_service: AuditService | None = None` shape.
- **IMPORTS**: `AuditService` under `TYPE_CHECKING`. No runtime import — the audit call site uses duck-typing through the attribute.
- **GOTCHA**: Do NOT import `AuditService` at module level — that would create a circular import risk. The `TYPE_CHECKING` guard mirrors how `EstimateService` does it.
- **VALIDATE**: `cd /Users/kirillrakitin/Grins_irrigation_platform && uv run python -c "from grins_platform.services.invoice_service import InvoiceService; import inspect; sig = inspect.signature(InvoiceService.__init__); assert 'audit_service' in sig.parameters; print('OK: audit_service kwarg present')"`

### 2. UPDATE `src/grins_platform/services/invoice_service.py` — extend `create_invoice` signature with actor kwargs

- **IMPLEMENT**:
  - Change `async def create_invoice(self, data: InvoiceCreate) -> InvoiceResponse:` (line 281 area) to `async def create_invoice(self, data: InvoiceCreate, *, actor_id: UUID | None = None, actor_role: str | None = None) -> InvoiceResponse:`.
  - Add the `*` keyword-only marker before `actor_id` so existing positional callers don't break.
  - Pass `actor_id=actor_id, actor_role=actor_role` into `await self._attach_payment_link(invoice, ...)` at line 346.
- **PATTERN**: `services/estimate_service.py` plumbs ip_address/user_agent through internal helpers via kwargs. Same shape.
- **IMPORTS**: `UUID` already imported at line 14.
- **GOTCHA**: All existing callers of `create_invoice(data)` continue to work because the new kwargs default to None. **Do not drop the `*` marker** — it forces future callers to use kwargs and prevents accidental positional misuse.
- **VALIDATE**: `cd /Users/kirillrakitin/Grins_irrigation_platform && uv run pytest src/grins_platform/tests/unit/test_invoice_service.py -k create_invoice -x --no-header -q 2>&1 | tail -20`

### 3. UPDATE `src/grins_platform/services/invoice_service.py` — extend `_attach_payment_link` signature with actor kwargs

- **IMPLEMENT**:
  - Change `_attach_payment_link(self, invoice: Invoice) -> None:` (line 758) to `_attach_payment_link(self, invoice: Invoice, *, actor_id: UUID | None = None, actor_role: str | None = None) -> None:`.
  - Do NOT add audit call yet — that's task 4.
- **PATTERN**: matches the new `create_invoice` signature.
- **GOTCHA**: `_attach_payment_link` is also called from `send_payment_link` at line 926 (lazy creation). Update that call site too — pass `actor_id=None, actor_role=None` (the lazy path is best-effort and we don't want to plumb actor through the entire send-link flow in this task).
- **VALIDATE**: `cd /Users/kirillrakitin/Grins_irrigation_platform && uv run ruff check src/grins_platform/services/invoice_service.py`

### 4. ADD `_audit_payment_link_auto_created` helper to `src/grins_platform/services/invoice_service.py`

- **IMPLEMENT**: Insert immediately AFTER `_attach_payment_link` (current end at line 837 area). Method body:

  ```python
  async def _audit_payment_link_auto_created(
      self,
      invoice: Invoice,
      *,
      link_id: str,
      actor_id: UUID | None,
      actor_role: str | None,
  ) -> None:
      """Best-effort audit row for inline Payment Link auto-creation.

      Validates: e2e-signoff 2026-05-06 finding 14.A.
      """
      if self.audit_service is None:
          return
      try:
          await self.audit_service.log_action(
              self.invoice_repository.session,
              actor_id=actor_id,
              actor_role=actor_role,
              action="stripe.payment_link.auto_created",
              resource_type="invoice",
              resource_id=invoice.id,
              details={
                  "stripe_payment_link_id": link_id,
                  "invoice_number": invoice.invoice_number,
                  "actor_type": "staff",
                  "source": "admin_ui",
              },
          )
      except Exception as e:
          self.log_failed(
              "audit_payment_link_auto_created",
              error=e,
              invoice_id=str(invoice.id),
          )
  ```

- **PATTERN**: Mirrors `services/estimate_service.py:848-880` exactly — same try/except shape, same `log_failed` on error, same `actor_type` + `source` keys in details.
- **IMPORTS**: `UUID` already imported. `Invoice` already imported under `TYPE_CHECKING`.
- **GOTCHA**:
  - Pass `self.invoice_repository.session` as the first positional `db` arg — confirmed by `_get_settings_service` (line 252) using the same access pattern.
  - `details["stripe_payment_link_id"]` is a string (the `plink_…` id), not a UUID. Do NOT cast.
  - `actor_type` = `"staff"` (manager/admin clicked "Create"); `source` = `"admin_ui"`. These keys are part of the JSONB discriminator contract documented at `audit_service.py:7-42`.
- **VALIDATE**: `cd /Users/kirillrakitin/Grins_irrigation_platform && uv run ruff check src/grins_platform/services/invoice_service.py && uv run mypy src/grins_platform/services/invoice_service.py 2>&1 | tail -20`

### 5. UPDATE `_attach_payment_link` in `src/grins_platform/services/invoice_service.py` — call audit helper after success branch

- **IMPLEMENT**: After the in-memory mirror block at lines 835-837 (the last three lines `invoice.stripe_payment_link_id = link_id` etc.), append:

  ```python
  await self._audit_payment_link_auto_created(
      invoice,
      link_id=link_id,
      actor_id=actor_id,
      actor_role=actor_role,
  )
  ```

- **PATTERN**: Mirrors how `EstimateService` calls `_audit_auto_job_created` from the auto-job branch — at the very end, after persistence is complete, so the audit row reflects the final committed state.
- **GOTCHA**:
  - **DO NOT call audit on the early-return branches**: lines 772-777 (already attached, idempotent no-op), lines 779-785 (DI missing), lines 787-794 (no customer), lines 815-821 (StripePaymentLinkError), line 825 (`$0` invoice). The audit row should ONLY fire when a fresh link was successfully created and persisted.
  - The order matters: audit AFTER `invoice_repository.update(...)` returns — so the row reflects the persisted state.
- **VALIDATE**: `cd /Users/kirillrakitin/Grins_irrigation_platform && uv run pytest src/grins_platform/tests/unit/test_invoice_service.py -x --no-header -q 2>&1 | tail -30`

### 6. UPDATE `src/grins_platform/api/v1/invoices.py` — wire AuditService into DI factory

- **IMPLEMENT**:
  - Add `from grins_platform.services.audit_service import AuditService` to imports (alongside the other `services.*` imports near line 53-64).
  - In `get_invoice_service` (lines 69-101), insert `audit_service = AuditService()` after `email_service = EmailService()` (line 92).
  - Pass `audit_service=audit_service` to `InvoiceService(...)` constructor call (lines 93-101). Add it after `email_service=email_service`.
- **PATTERN**: All other optional services in the factory are constructed inline (cheap, stateless). `AuditService` follows the same pattern — it's a `LoggerMixin` subclass with no constructor args.
- **GOTCHA**: `AuditService()` takes no arguments. Don't pass session here — the session is passed per-call to `log_action(db=..., ...)`.
- **VALIDATE**: `cd /Users/kirillrakitin/Grins_irrigation_platform && uv run python -c "from grins_platform.api.v1.invoices import get_invoice_service; import inspect; print(inspect.getsource(get_invoice_service))" | grep -E "audit_service|AuditService"`

### 7. UPDATE `src/grins_platform/api/v1/invoices.py` — pass actor through `create_invoice` route

- **IMPLEMENT**: In the `create_invoice` route handler (lines 158-186), change:
  ```python
  return await service.create_invoice(data)
  ```
  to:
  ```python
  return await service.create_invoice(
      data,
      actor_id=_current_user.id,
      actor_role=_current_user.role,
  )
  ```
- **PATTERN**: Several other routes already thread `_current_user.id`. `_current_user: ManagerOrAdminUser` resolves to a `Staff` instance with `.id` (UUID) and `.role` (string).
- **GOTCHA**: `_current_user` already exists in the function signature at line 160 — do NOT add a new dependency.
- **VALIDATE**: `cd /Users/kirillrakitin/Grins_irrigation_platform && uv run ruff check src/grins_platform/api/v1/invoices.py`

### 8. UPDATE `src/grins_platform/services/audit_service.py` — register new canonical action in docstring

- **IMPLEMENT**: In the canonical action strings list (lines 18-37), add a new entry alongside `estimate.auto_job_created`:
  ```
  - ``stripe.payment_link.auto_created``            — Payment Link inlined on invoice POST (14.A)
  ```
  Place it AFTER `estimate.auto_job_skipped` (line 36) and BEFORE `sales_pipeline.nudge.sent` (line 37). Bump alignment of column `—` if needed for column-uniformity (the existing list is column-aligned with two-space gutter; preserve the alignment).
- **PATTERN**: Documentation-only update — no code change, no test required. The list is the canonical contract; future contributors must not invent new strings outside it.
- **GOTCHA**: This is RST inside a Python docstring; don't accidentally break the surrounding `Validates:` block at line 39.
- **VALIDATE**: `cd /Users/kirillrakitin/Grins_irrigation_platform && grep -n "stripe.payment_link.auto_created" src/grins_platform/services/audit_service.py`

### 9. UPDATE `src/grins_platform/services/inbox_service.py` — add normalizer imports + `_safe_normalize_phone` helper

- **IMPLEMENT**:
  - Add to the imports block at lines 36-52: `from grins_platform.services.sms.phone_normalizer import PhoneNormalizationError, normalize_to_e164`. Place it alphabetically — after `from grins_platform.schemas.inbox import (...)`.
  - Add module-level helper after `_matches_filter` (line 185 area) and BEFORE the `class InboxService` declaration (line 188):

    ```python
    def _safe_normalize_phone(raw: str | None) -> str | None:
        """Best-effort E.164 normalization for inbox source-table phones.

        Source tables store phones in mixed formats (E.164 from SMS providers,
        dashed/legacy from older campaign ingestion). This wrapper normalizes
        at the inbox-aggregation seam without forcing a backfill, returning
        ``None`` when the raw input is missing or unparseable so the inbox
        stream keeps flowing on malformed legacy rows.

        Validates: e2e-signoff 2026-05-06 finding 20.A.
        """
        if not raw:
            return None
        try:
            return normalize_to_e164(raw)
        except PhoneNormalizationError:
            return None
    ```

- **PATTERN**: Mirrors module-level pure helpers `_sort_key` (line 116) and `_classify_triage` (line 137). All are lowercase-snake-case private (leading underscore) free functions.
- **GOTCHA**: Do NOT log inside the helper — it's called once per inbox row, and noisy per-row logs would flood production.
- **VALIDATE**: `cd /Users/kirillrakitin/Grins_irrigation_platform && uv run python -c "from grins_platform.services.inbox_service import _safe_normalize_phone; assert _safe_normalize_phone('952-737-3312') == '+19527373312'; assert _safe_normalize_phone(None) is None; assert _safe_normalize_phone('') is None; assert _safe_normalize_phone('garbage') is None; print('OK')"`

### 10. UPDATE `src/grins_platform/services/inbox_service.py` — apply `_safe_normalize_phone` at the three real source-table seams

- **IMPLEMENT**:
  - Line 367 (inside `_fetch_confirmation_responses`): change `from_phone=row.from_phone,` to `from_phone=_safe_normalize_phone(row.from_phone),`.
  - Line 455 (inside `_fetch_campaign_responses`): change `from_phone=row.phone,` to `from_phone=_safe_normalize_phone(row.phone),`.
  - Line 555 (inside `_fetch_consent_records`): change `from_phone=row.phone_number,` to `from_phone=_safe_normalize_phone(row.phone_number),`.
- **PATTERN**: All three are inside `InboxItem(...)` constructor calls — the change is a single-line wrap.
- **GOTCHA**:
  - **DO NOT change line 409 (`_fetch_reschedule_requests`) or line 496 (`_fetch_communications`)**. Both already use `from_phone=None` because their source tables (`reschedule_requests`, `communications`) have no phone column. Wrapping `None` in the normalizer is unnecessary noise.
  - Confirm line numbers before editing — lines may have shifted slightly after task 9's helper insertion. Match by surrounding context (`InboxItem(`, `source_table=`).
- **VALIDATE**: `cd /Users/kirillrakitin/Grins_irrigation_platform && grep -n "_safe_normalize_phone\|from_phone=" src/grins_platform/services/inbox_service.py`

### 11. UPDATE `src/grins_platform/schemas/inbox.py` — tighten `from_phone` field description

- **IMPLEMENT**: At lines 62-65, change the description from `"Sender phone (E.164 or provider canonical form)"` to `"Sender phone normalized to E.164 (+1NXXXXXXX) when derivable, else None"`.
- **PATTERN**: Description-only change — no validator, no type change. The string `from_phone` field still allows `None`.
- **GOTCHA**: Do not add a Pydantic regex validator. The helper at the service seam is the source of truth; adding a validator would re-reject the same `None`s the helper just handled, or worse, reject E.164 strings if the regex is wrong.
- **VALIDATE**: `cd /Users/kirillrakitin/Grins_irrigation_platform && uv run python -c "from grins_platform.schemas.inbox import InboxItem; field = InboxItem.model_fields['from_phone']; assert 'E.164' in field.description; print(field.description)"`

### 12. UPDATE `frontend/src/features/accounting/components/AuditLog.tsx` — add badge color for new action

- **IMPLEMENT**: In the `ACTION_COLORS` map at lines 20-32, add a new entry: `'stripe.payment_link.auto_created': 'bg-blue-100 text-blue-700'` alongside the existing `'payment.collect': 'bg-green-100 text-green-700'`. Place it adjacent to other `payment.*` entries for grouping.
- **PATTERN**: The map keys are dot-separated action strings; values are Tailwind utility classes. Existing colors: green for payment success, red for cancellations, etc. Blue is a free slot.
- **GOTCHA**: This is a TypeScript file — preserve the trailing comma after the last entry to satisfy ESLint's trailing-comma rule (likely configured).
- **VALIDATE**: `cd /Users/kirillrakitin/Grins_irrigation_platform/frontend && grep -n "stripe.payment_link.auto_created" src/features/accounting/components/AuditLog.tsx`

### 13. ADD unit tests for `_safe_normalize_phone` to `src/grins_platform/tests/unit/test_inbox_service.py`

- **IMPLEMENT**: At the end of the file, append a new `@pytest.mark.unit` class:

  ```python
  @pytest.mark.unit
  class TestSafeNormalizePhone:
      """Inbox aggregator must normalize source-table phones to E.164 or None."""

      def test_dashed_normalizes_to_e164(self) -> None:
          from grins_platform.services.inbox_service import _safe_normalize_phone
          assert _safe_normalize_phone("952-737-3312") == "+19527373312"

      def test_already_e164_passthrough(self) -> None:
          from grins_platform.services.inbox_service import _safe_normalize_phone
          assert _safe_normalize_phone("+19527373312") == "+19527373312"

      def test_paren_format_normalizes(self) -> None:
          from grins_platform.services.inbox_service import _safe_normalize_phone
          assert _safe_normalize_phone("(952) 737-3312") == "+19527373312"

      def test_none_returns_none(self) -> None:
          from grins_platform.services.inbox_service import _safe_normalize_phone
          assert _safe_normalize_phone(None) is None

      def test_empty_string_returns_none(self) -> None:
          from grins_platform.services.inbox_service import _safe_normalize_phone
          assert _safe_normalize_phone("") is None

      def test_garbage_returns_none_no_raise(self) -> None:
          from grins_platform.services.inbox_service import _safe_normalize_phone
          assert _safe_normalize_phone("not-a-phone") is None
          assert _safe_normalize_phone("555-0100") is None  # FCC test number
  ```

- **PATTERN**: Mirrors `test_inbox_service.py` `@pytest.mark.unit` class style at line 50.
- **GOTCHA**: Inline imports inside test methods so the test file load doesn't fail if `_safe_normalize_phone` is renamed — better signal localization.
- **VALIDATE**: `cd /Users/kirillrakitin/Grins_irrigation_platform && uv run pytest src/grins_platform/tests/unit/test_inbox_service.py::TestSafeNormalizePhone -v --no-header 2>&1 | tail -20`

### 14. ADD unit tests for `_audit_payment_link_auto_created` to `src/grins_platform/tests/unit/test_invoice_service.py`

- **IMPLEMENT**: Append a new test class at the end of the file:

  ```python
  @pytest.mark.unit
  class TestAuditPaymentLinkAutoCreated:
      """14.A: invoice POST must write a stripe.payment_link.auto_created audit row."""

      @pytest.fixture
      def mock_audit_service(self) -> AsyncMock:
          mock = AsyncMock()
          return mock

      @pytest.fixture
      def service_with_audit(
          self,
          mock_invoice_repo: AsyncMock,
          mock_job_repo: AsyncMock,
          mock_audit_service: AsyncMock,
      ) -> InvoiceService:
          mock_invoice_repo.session = AsyncMock()
          return InvoiceService(
              invoice_repository=mock_invoice_repo,
              job_repository=mock_job_repo,
              audit_service=mock_audit_service,
          )

      @pytest.mark.asyncio
      async def test_no_op_when_audit_service_missing(
          self,
          mock_invoice_repo: AsyncMock,
          mock_job_repo: AsyncMock,
      ) -> None:
          service = InvoiceService(
              invoice_repository=mock_invoice_repo,
              job_repository=mock_job_repo,
          )
          invoice = self._create_mock_invoice()
          await service._audit_payment_link_auto_created(
              invoice,
              link_id="plink_test123",
              actor_id=None,
              actor_role=None,
          )
          # No assertion needed — must not raise.

      @pytest.mark.asyncio
      async def test_writes_audit_row_with_correct_kwargs(
          self,
          service_with_audit: InvoiceService,
          mock_audit_service: AsyncMock,
      ) -> None:
          invoice = self._create_mock_invoice()
          actor_id = uuid4()
          await service_with_audit._audit_payment_link_auto_created(
              invoice,
              link_id="plink_test123",
              actor_id=actor_id,
              actor_role="admin",
          )
          mock_audit_service.log_action.assert_awaited_once()
          kwargs = mock_audit_service.log_action.call_args.kwargs
          assert kwargs["action"] == "stripe.payment_link.auto_created"
          assert kwargs["resource_type"] == "invoice"
          assert kwargs["resource_id"] == invoice.id
          assert kwargs["actor_id"] == actor_id
          assert kwargs["actor_role"] == "admin"
          assert kwargs["details"]["stripe_payment_link_id"] == "plink_test123"
          assert kwargs["details"]["actor_type"] == "staff"
          assert kwargs["details"]["source"] == "admin_ui"

      @pytest.mark.asyncio
      async def test_swallows_audit_exception(
          self,
          service_with_audit: InvoiceService,
          mock_audit_service: AsyncMock,
      ) -> None:
          mock_audit_service.log_action.side_effect = RuntimeError("audit broken")
          invoice = self._create_mock_invoice()
          # Must NOT raise — best-effort.
          await service_with_audit._audit_payment_link_auto_created(
              invoice,
              link_id="plink_test123",
              actor_id=None,
              actor_role=None,
          )
  ```

  Add `_create_mock_invoice` to this class via inheritance from `TestInvoiceServiceCreateInvoice` OR copy the helper inline. Inheritance is cleaner: `class TestAuditPaymentLinkAutoCreated(TestInvoiceServiceCreateInvoice):` and rely on the inherited `_create_mock_invoice` + fixtures.

- **PATTERN**: Mirrors `tests/unit/test_lead_service_move_audit_actor.py:79-89` for kwargs assertion style.
- **GOTCHA**: `mock_invoice_repo.session = AsyncMock()` is required because the audit helper accesses `self.invoice_repository.session`.
- **VALIDATE**: `cd /Users/kirillrakitin/Grins_irrigation_platform && uv run pytest src/grins_platform/tests/unit/test_invoice_service.py::TestAuditPaymentLinkAutoCreated -v --no-header 2>&1 | tail -30`

### 15. ADD integration test for `_attach_payment_link` happy path to `src/grins_platform/tests/unit/test_invoice_service.py`

- **IMPLEMENT**: Append a test verifying that `_attach_payment_link` calls the audit helper after a successful link creation:

  ```python
  @pytest.mark.asyncio
  async def test_attach_payment_link_writes_audit_on_success(
      self,
      service_with_audit: InvoiceService,
      mock_audit_service: AsyncMock,
      mock_invoice_repo: AsyncMock,
  ) -> None:
      invoice = self._create_mock_invoice()
      invoice.stripe_payment_link_id = None
      invoice.stripe_payment_link_active = False
      mock_customer = MagicMock(id=uuid4())
      service_with_audit.customer_repository = AsyncMock()
      service_with_audit.customer_repository.get_by_id.return_value = mock_customer
      service_with_audit.payment_link_service = MagicMock()
      service_with_audit.payment_link_service.create_for_invoice.return_value = (
          "plink_test123",
          "https://stripe.test/plink_test123",
      )
      mock_invoice_repo.update.return_value = invoice

      await service_with_audit._attach_payment_link(
          invoice,
          actor_id=uuid4(),
          actor_role="admin",
      )

      mock_audit_service.log_action.assert_awaited_once()
      assert (
          mock_audit_service.log_action.call_args.kwargs["action"]
          == "stripe.payment_link.auto_created"
      )

  @pytest.mark.asyncio
  async def test_attach_payment_link_no_audit_on_idempotent_skip(
      self,
      service_with_audit: InvoiceService,
      mock_audit_service: AsyncMock,
  ) -> None:
      invoice = self._create_mock_invoice()
      # Already has live link — _attach_payment_link must early-return without auditing.
      invoice.stripe_payment_link_id = "plink_existing"
      invoice.stripe_payment_link_active = True

      await service_with_audit._attach_payment_link(
          invoice,
          actor_id=uuid4(),
          actor_role="admin",
      )

      mock_audit_service.log_action.assert_not_called()
  ```

- **PATTERN**: Same fixture + assertion style as task 14.
- **GOTCHA**: The `customer_service` attribute is only used if non-None; leave it unset to skip the Stripe customer link-up branch.
- **VALIDATE**: `cd /Users/kirillrakitin/Grins_irrigation_platform && uv run pytest src/grins_platform/tests/unit/test_invoice_service.py -k "test_attach_payment_link_writes_audit_on_success or test_attach_payment_link_no_audit_on_idempotent_skip" -v --no-header 2>&1 | tail -20`

### 16. RUN full backend validation

- **IMPLEMENT**: nothing.
- **VALIDATE**:
  ```bash
  cd /Users/kirillrakitin/Grins_irrigation_platform && uv run ruff check src/grins_platform/services/invoice_service.py src/grins_platform/services/inbox_service.py src/grins_platform/services/audit_service.py src/grins_platform/api/v1/invoices.py src/grins_platform/schemas/inbox.py
  ```
  ```bash
  cd /Users/kirillrakitin/Grins_irrigation_platform && uv run pytest src/grins_platform/tests/unit/test_invoice_service.py src/grins_platform/tests/unit/test_inbox_service.py src/grins_platform/tests/unit/test_invoice_service_send_link.py -x --no-header 2>&1 | tail -30
  ```

### 17. RUN frontend validation

- **IMPLEMENT**: nothing.
- **VALIDATE**:
  ```bash
  cd /Users/kirillrakitin/Grins_irrigation_platform/frontend && npm run typecheck 2>&1 | tail -20
  ```

---

## TESTING STRATEGY

### Unit Tests

- `TestSafeNormalizePhone` — six parametrized cases for the helper (dashed, E.164, paren-format, None, empty string, malformed).
- `TestAuditPaymentLinkAutoCreated` — three cases: no-op when audit_service None, kwargs-correct on success, exception swallowed.
- Two new methods on `TestInvoiceServiceCreateInvoice` (or a sibling class) — `_attach_payment_link` writes audit on success branch; `_attach_payment_link` does NOT write audit on idempotent skip.

Use `AsyncMock` for `audit_service` and `invoice_repository.session`. Mirror the `mock_audit.log_action.assert_awaited_once()` + `call_args.kwargs[...]` assertions from `test_lead_service_move_audit_actor.py:79-89`.

### Integration Tests

The existing functional tests under `src/grins_platform/tests/functional/` (`test_invoice_filtering_functional.py`) drive a real database session. **Do not add new functional tests in this plan** — the unit-test layer is sufficient because:

1. The audit write path is identical to `estimate.auto_job_created` which already has functional coverage indirectly via the e2e portal-approval flow.
2. The phone normalizer wrapper is pure (no DB).

If the implementation agent finds the functional layer needs extension, defer to a follow-up.

### Edge Cases

- Phone normalization receives `None` (line 409 / line 496 callers won't hit the helper, but defensive None-handling is required for upstream null-safety).
- Phone normalization receives the FCC 555-0100..0199 test range — `normalize_to_e164` raises; helper must return None silently.
- Invoice POST with `customer_repository=None` (legacy unit-test construction) — `_attach_payment_link` early-returns at line 779-785 before any audit write. Test confirms.
- Invoice POST with $0 amount — `_attach_payment_link` returns at line 825 before persistence. No audit row.
- Audit service raises mid-call (Stripe outage on the customer-link side, or DB rollback) — helper must swallow and log via `log_failed`. The invoice creation must succeed regardless.

---

## VALIDATION COMMANDS

Execute every command to ensure zero regressions and 100% feature correctness.

### Level 1: Syntax & Style

```bash
cd /Users/kirillrakitin/Grins_irrigation_platform && uv run ruff check src/grins_platform/services/invoice_service.py src/grins_platform/services/inbox_service.py src/grins_platform/services/audit_service.py src/grins_platform/api/v1/invoices.py src/grins_platform/schemas/inbox.py
```

```bash
cd /Users/kirillrakitin/Grins_irrigation_platform && uv run ruff format --check src/grins_platform/services/invoice_service.py src/grins_platform/services/inbox_service.py src/grins_platform/api/v1/invoices.py
```

```bash
cd /Users/kirillrakitin/Grins_irrigation_platform && uv run mypy src/grins_platform/services/invoice_service.py src/grins_platform/services/inbox_service.py 2>&1 | tail -20
```

### Level 2: Unit Tests

```bash
cd /Users/kirillrakitin/Grins_irrigation_platform && uv run pytest src/grins_platform/tests/unit/test_invoice_service.py -v --no-header 2>&1 | tail -30
```

```bash
cd /Users/kirillrakitin/Grins_irrigation_platform && uv run pytest src/grins_platform/tests/unit/test_inbox_service.py -v --no-header 2>&1 | tail -30
```

```bash
cd /Users/kirillrakitin/Grins_irrigation_platform && uv run pytest src/grins_platform/tests/unit/test_invoice_service_send_link.py -x --no-header 2>&1 | tail -20
```

### Level 3: Broader regression sweep

```bash
cd /Users/kirillrakitin/Grins_irrigation_platform && uv run pytest src/grins_platform/tests/unit/ -k "invoice or inbox or audit" --no-header 2>&1 | tail -30
```

### Level 4: Manual Validation (against dev)

Per memory `feedback_no_remote_alembic`, do NOT alembic-push from local; commit + push and let Railway apply. **No alembic migration is part of this plan**, so a normal git push suffices.

After deploying to dev:

1. Login as admin to the dev frontend (`https://grins-irrigation-platform-git-dev-kirilldr01s-projects.vercel.app`).
2. Pick a customer with a non-$0 job and create a new invoice via the admin UI.
3. Run:
   ```bash
   API="https://grins-dev-dev.up.railway.app"
   T="<bearer token>"
   INVOICE_ID="<id from step 2>"
   curl -s "$API/api/v1/audit-log?resource_type=invoice&resource_id=$INVOICE_ID&action=stripe.payment_link.auto_created" -H "Authorization: Bearer $T" | jq '.items[0]'
   ```
   Expect one row with `action=stripe.payment_link.auto_created`, `details.stripe_payment_link_id` matching the invoice's `stripe_payment_link_id`, `details.actor_type=staff`, `details.source=admin_ui`.
4. Open the admin AuditLog UI and confirm the row renders with the new badge color.
5. For 20.A: open the unified inbox (`/schedule` 4th queue card) and confirm `from_phone` displays consistently as `+1NXXXXXXX` for rows from all source tables. The seed customer (per memory: `+19527373312`) should display E.164 in every row that surfaces them.
6. Per memory `feedback_test_recipients_prod_safety` and `feedback_test_email_only_allowlist`: any test invoice MUST be created against `email=kirillrakitinsecond@gmail.com` and `phone=+19527373312` only.

### Level 5: Frontend type-check

```bash
cd /Users/kirillrakitin/Grins_irrigation_platform/frontend && npm run typecheck 2>&1 | tail -20
```

---

## ACCEPTANCE CRITERIA

- [ ] `POST /api/v1/invoices` against a non-$0 invoice writes an `audit_log` row with `action=stripe.payment_link.auto_created`, `resource_type=invoice`, `resource_id=<invoice_id>`, `actor_id=<creating staff id>`, `actor_role=<admin|manager>`, `details.stripe_payment_link_id=<plink_…>`, `details.actor_type=staff`, `details.source=admin_ui`.
- [ ] `POST /api/v1/invoices` against an idempotent re-call (invoice already has an active link) writes NO additional audit row.
- [ ] `POST /api/v1/invoices` against a $0 invoice writes NO audit row.
- [ ] If `audit_service` write fails (mocked exception), `POST /api/v1/invoices` still returns 201 with the invoice + Payment Link fields populated.
- [ ] `GET /api/v1/inbox` returns `from_phone` in `+1NXXXXXXX` form for every row from `job_confirmation_responses`, `campaign_responses`, and `sms_consent_record`. Rows from `reschedule_requests` and `communications` continue to return `from_phone=null`.
- [ ] An inbox row whose source phone is unparseable returns `from_phone=null` instead of breaking aggregation.
- [ ] `audit_service.py` canonical actions docstring lists `stripe.payment_link.auto_created`.
- [ ] `frontend/src/features/accounting/components/AuditLog.tsx` `ACTION_COLORS` map contains `stripe.payment_link.auto_created`.
- [ ] `InboxItem.from_phone` field description in `schemas/inbox.py` reflects the new invariant.
- [ ] All Level 1 + Level 2 + Level 3 validation commands pass with no new failures (pre-existing failures noted in 2026-05-06 sign-off do not regress).
- [ ] Frontend `npm run typecheck` introduces no new errors beyond the 7 pre-existing (per 2026-05-06 sign-off P23).

---

## COMPLETION CHECKLIST

- [ ] All 17 tasks completed in order
- [ ] Each task validation passed immediately
- [ ] Level 1-5 validation commands executed successfully
- [ ] No new linting or type-check errors
- [ ] Manual dev validation confirms the audit row + inbox normalization
- [ ] Acceptance criteria all met
- [ ] Code reviewed against pattern references (`estimate_service.py:848-880`, `inbox_service.py:_classify_triage`)

---

## NOTES

**Why we plumb actor_id/actor_role but skip ip_address/user_agent:** The `Staff` instance is already in scope at the API layer via `_current_user`. Plumbing actor through is a one-line change. `ip_address` / `user_agent` require adding a `Request` dependency to the route handler and threading it through two service layers — out of scope for this targeted fix. The audit_log columns are nullable for both, so missing values are valid. A separate follow-up can add `Request`-scoped capture if operators ask for IP attribution on Payment Link breadcrumbs.

**Why best-effort audit, not transactional:** The auto-job audit at `estimate_service.py:848-880` is also best-effort. The contract is "audit must not block the user-visible operation". An audit DB outage shouldn't fail invoice creation. The pattern is well-established — we mirror it.

**Why not migrate `campaign_responses.phone` and `sms_consent_record.phone_number` to E.164 at write-time?** That's the long-term right answer and was considered. But: (a) it requires a backfill migration that touches potentially thousands of rows; (b) writers are spread across multiple ingestion paths (CallRail, web form, manual admin); (c) per memory `feedback_no_remote_alembic` we want migrations to flow through Railway-applied branches. Read-seam normalization closes the operator-visible gap immediately at zero migration risk. Write-time canonicalization is a separate, larger plan.

**Why only `payment_link.auto_created` and not `payment_link.created` (covering the lazy `send_payment_link` path too)?** Finding 14.A is specifically about the silent inline creation on invoice POST. The lazy send-link path already emits a `payment.send_link.*` log line and (per the live e2e run) is operator-initiated, so the operator already knows it happened. We can extend coverage to the lazy path in a follow-up if needed — the audit helper is reusable.

**On the `Y/R/C` reply rows in `job_confirmation_responses.from_phone` (line 367):** Memory says these usually arrive E.164 from the SMS provider, so passing them through `_safe_normalize_phone` is essentially a no-op. We still wrap them so the InboxItem invariant ("E.164 or None") holds uniformly across all five sources without callers having to remember which is which.

**Plan file path**: `.agents/plans/payment-link-audit-and-inbox-phone-normalization.md`
