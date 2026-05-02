# Feature: Portal Link Fix + Umbrella P0/P1 Bug Cleanup

The following plan should be complete, but its important that you validate documentation and codebase patterns and task sanity before you start implementing.

Pay special attention to naming of existing utils types and models. Import from the right files etc.

> **Source bugs**: this plan addresses (a) the PORTAL_BASE_URL env-config defect surfaced in the 2026-05-02 SMS verification and (b) the four still-outstanding bugs from the umbrella plan's 2026-05-02 re-run section ("Bugs Uncovered During 2026-05-02 Re-Run"). Bug #14 was already landed in commit `b53ac1f` and is **NOT** part of this plan. SMS opt-out / opt-in language work is **explicitly out of scope** per user direction — that thread was research-only.

---

## Feature Description

Five surgical fixes that together restore the customer-portal happy path, the tech-mobile payment flow, and the staff appointment-modal experience that the 2026-05-02 re-run proved are still broken.

1. **Portal link env (CONFIG)** — local backend currently embeds `http://localhost:5173/portal/estimates/{token}` into estimate-ready SMS because `.env` defaults `PORTAL_BASE_URL` to the Vite dev server. Change the local default to the Vercel dev URL so links sent from the local backend land on a publicly-reachable portal.
2. **Bug #12 — SizeTierSubPicker silently empty (P1)** — `frontend/src/features/schedule/components/EstimateSheet/SizeTierSubPicker.tsx` reads `pricing_rule.tiers[].label`, but the Phase-1 seed writes `pricing_rule.tiers[].size`. Every `size_tier` / `size_tier_plus_materials` offering renders "no tiers configured."
3. **Bug #13 — Portal pages crash on `business.company_logo_url` (P0)** — backend `PortalEstimateResponse` returns flat company fields (and only `company_name` today); frontend `EstimateReview.tsx` / `InvoicePortal.tsx` / `ContractSigning.tsx` read `entity.business.company_logo_url`. `EstimateReview` 100% crashes the customer approval flow.
4. **Bug #15 — `TimelineRow` "Element type is invalid" (P0)** — `appointment_timeline_service.py` already emits `TimelineEventKind.PAYMENT_RECEIVED` (Phase 4.2 landed), but the frontend `TimelineEventKind` union and the `KIND_ICON` / `KIND_COLOR` records in `AppointmentCommunicationTimeline.tsx` were never updated. Looking up an icon by a kind that isn't in the record returns `undefined` and React explodes inside `<Icon ... />`. This crashes the AppointmentModal's communication panel for any appointment whose job has a paid invoice.
5. **Bug #16 — `payment_method='stripe'` short-circuits to PAID (P1)** — `AppointmentService.collect_payment` blindly transitions the invoice to PAID/PARTIAL based on `paid_amount >= total_amount`, regardless of `payment_method`. For Stripe Payment Links the invoice should stay PENDING until the Stripe webhook reconciles the charge (Architecture C — see memory `project_stripe_payment_links_arch_c`).

## User Story

**As an** office manager / field technician / customer
**I want to** open the customer portal from a real SMS link, send an estimate that uses tiered pricing, view payment history without crashing the modal, and have Stripe payments correctly stay PENDING until the webhook lands,
**So that** the umbrella plan's Phases 0/3/4 actually deliver the workflows they were merged for.

## Problem Statement

After the 2026-05-02 re-run, four bugs blocked the umbrella plan from being shippable:

- Customers cannot view, sign, approve, or reject estimates via the portal (Bug #13).
- Techs cannot use any `size_tier` offering on a mobile estimate (Bug #12).
- Staff cannot open the AppointmentModal communication panel for any appointment with a paid invoice (Bug #15).
- Stripe payment-link invoices are flipped to PAID synchronously instead of after webhook reconciliation, breaking the documented Architecture C semantics (Bug #16).

Plus the local-backend SMS link bug surfaced today: links go to `http://localhost:5173`, which the customer's phone cannot resolve.

## Solution Statement

**Five atomic fixes**, sequenced so the cheapest unblockers ship first and each fix is independently revertible.

- **Fix 1 (CONFIG, ~5 min)** — Change local `.env` `PORTAL_BASE_URL` to the Vercel dev URL. Document the same in `.env.example`. No code change.
- **Fix 2 (FRONTEND, Bug #12)** — Teach `readTiers()` to also accept `{size, price}` (and surface `size_range_ft` if present), preserving back-compat with `{label, price}`. Add coverage to `SubPickers.test.tsx`.
- **Fix 3 (CONTRACT, Bug #13)** — Source-of-truth fix on the backend: extend `PortalEstimateResponse` with the same flat company fields `PortalInvoiceResponse` already exposes (`company_address`, `company_phone`, `company_logo_url`); populate them from `SettingsService.get_company_branding()` in `_to_portal_response()`. Update the three portal components and the portal types to read flat fields with optional chaining (drop the synthetic `business: {}` nesting).
- **Fix 4 (FRONTEND, Bug #15)** — Add `'payment_received'` to the `TimelineEventKind` union, add icon/color entries, and add a defensive fallback so an unknown kind logs a warning and renders a neutral icon instead of crashing the tree. Add a unit test that asserts unknown kinds don't throw.
- **Fix 5 (BACKEND, Bug #16)** — Gate the immediate PAID transition on `payment_method not in {STRIPE, CREDIT_CARD}`. For Stripe-class methods, leave the invoice in its prior status (or PENDING for new invoices) and skip receipt SMS — the webhook handler is the only thing that should mark Stripe-class invoices PAID and send the receipt.

## Feature Metadata

**Feature Type**: Bug Fix (5 atomic fixes, no new capability)
**Estimated Complexity**: **Low–Medium** — surface-level changes to known code; the only design decision is the contract shape for Fix 3 (resolved below).
**Primary Systems Affected**:
- Backend: `schemas/portal.py`, `api/v1/portal.py` (`_to_portal_response`), `services/appointment_service.py` (`collect_payment`).
- Frontend: `features/portal/types/`, `features/portal/components/{EstimateReview,InvoicePortal,ContractSigning}.tsx`, `features/schedule/components/EstimateSheet/SizeTierSubPicker.tsx`, `features/schedule/types/index.ts`, `features/schedule/components/AppointmentCommunicationTimeline.tsx`.
- Config: `.env`, `.env.example`.

**Dependencies**: None new. All libraries (Vitest, RTL, FastAPI, Pydantic, structlog) already in tree.

**Out of scope**:
- SMS opt-in / opt-out language work (user clarified this was research-only curiosity).
- Bug #14 (already fixed in commit `b53ac1f`).
- Any new pricelist editor work; any new portal feature work.
- Railway dev env changes — local `.env` is the single source of truth for the SMS link defect that was actually observed.

---

## CONTEXT REFERENCES

### Relevant Codebase Files — IMPORTANT: YOU MUST READ THESE BEFORE IMPLEMENTING

#### Fix 1 — Portal link env

- `.env` (lines 48–50) — line 50 is the one to change: `PORTAL_BASE_URL=http://localhost:5173`. Comment at line 49 already says "dev points at Vite, prod will point at portal.grinsirrigation.com" — update the comment too.
- `.env.example` (line 152) — mirror the change with the same Vercel dev URL.
- `src/grins_platform/services/email_config.py` (entire file, 60 lines) — `EmailSettings.portal_base_url` reads the env var and defaults to `http://localhost:5173`. **Default value stays the same** — only the runtime `.env` value changes; no code edit here.
- `src/grins_platform/services/estimate_service.py` (lines 86, 100, 130, 307, 320, 360, 937, 1066) — consumer; do not touch, only verifying the URL flows in via DI from `EmailSettings().portal_base_url`.
- `.vercel/project.json` — confirms the Vercel project is `prj_SZexdljNexKryhM7PAJn3DQkDbSK`, project name `grins-irrigation-platform`. **Canonical dev alias** (verified 2026-05-02 via grep — already used in `e2e/payment-links-flow.sh:32` and `Testing Procedure/10-customer-landing-flow.md:19,193,198`): **`https://grins-irrigation-platform-git-dev-kirilldr01s-projects.vercel.app`**. No discovery needed; use this string verbatim.

#### Fix 2 — Bug #12 SizeTierSubPicker

- `frontend/src/features/schedule/components/EstimateSheet/SizeTierSubPicker.tsx` (entire file, 123 lines) — function `readTiers()` at lines 22–49 only accepts `{label, price}`. Modify to also accept `{size, price, size_range_ft?}` and synthesize a `label` from `size` (capitalize first letter) and a `subLabel` from `size_range_ft`.
- `frontend/src/features/schedule/components/EstimateSheet/SubPickers.test.tsx` (entire file, 108 lines) — extend the SizeTierSubPicker block with a test that uses the seed-shape `{size, price, size_range_ft}` entries. Mirror the existing array-tier test at lines 40–60.
- `bughunt/2026-05-01-pricelist-seed-data.json` (lines 891–906 for `tree_drop_residential`; 759–768 + 866–875 for `decorative_boulders_*` `size_tier_plus_materials`) — canonical seed shape. Note: `size_tier_plus_materials` rows use `labor_amount` instead of `price` (audit lines 763–764). **Important: handle `labor_amount` as an alias for `price` in the same fix** so `decorative_boulders_*` works too.
- `frontend/src/features/schedule/components/EstimateSheet/LineItemPicker.tsx` (lines 177–184, `handleTierPick`) — consumer; the `(label, price)` callback shape stays the same — `handleTierPick` already passes the picked label into the line-item draft as `selected_tier`. No change here.

#### Fix 3 — Bug #13 portal `business` object

- `src/grins_platform/schemas/portal.py` (entire file, 176 lines) —
  - `PortalEstimateResponse` (lines 17–63) currently exposes only `company_name`. **EXTEND** with `company_address`, `company_phone`, `company_logo_url` matching the field signatures in `PortalInvoiceResponse` (lines 156–175).
  - `PortalInvoiceResponse` (lines 126–175) — already has all four flat fields; **do not change shape**, but verify it's actually populated (audit suggests it may be `null`).
  - There is **no** `PortalContractResponse`. The contract sign endpoint reuses `PortalEstimateResponse` (`api/v1/portal.py:456`) — meaning Fix 3 to `PortalEstimateResponse` automatically fixes the contract page too.
- `src/grins_platform/api/v1/portal.py` (lines 146–190, `_to_portal_response`) — populate the new fields. Mirror the existing `_get_company_info()` helper from `src/grins_platform/services/invoice_portal_service.py` (lines 178–211): same `settings_service.get_company_branding()` lookup, same fallback dict shape. **Note**: the helper signature in `invoice_portal_service.py` already returns the right keys — read it once and reuse the dict in `_to_portal_response()`.
- `src/grins_platform/services/settings_service.py` (lines 180–203, `SettingsService.get_company_info(db)` — **NOTE: method name is `get_company_info`, NOT `get_company_branding`**) — the canonical source of truth. Returns `{company_name, company_address, company_phone, company_logo_url}` with safe defaults `{"Grins Irrigation", "", "", ""}` if `business_settings.company_info` row absent.
- `src/grins_platform/services/invoice_portal_service.py` (lines 165, 191–219, `_get_company_info`) — the existing pattern to mirror in portal.py. **NOTE**: invoice_portal_service has its own private `_get_company_info(db)` that reads `business_settings.company_info` directly via `BusinessSetting` model (lines 191–219). Both patterns are equivalent; **use `SettingsService(db).get_company_info(db)` for new code** since it's the public API.
- `frontend/src/features/portal/types/index.ts` (entire file, 91 lines) —
  - **REMOVE** `PortalBusinessInfo` interface (lines 3–8) — it doesn't reflect the API contract.
  - **REMOVE** `business: PortalBusinessInfo` field from `PortalEstimate` (line 25), `PortalContract` (line 52), `PortalInvoice` (line 73).
  - **ADD** flat optional fields to all three: `company_name?: string | null`, `company_address?: string | null`, `company_phone?: string | null`, `company_logo_url?: string | null`. (Keep optional + nullable for safety; the fields are populated server-side but can be null when settings are not configured.)
- `frontend/src/features/portal/components/EstimateReview.tsx` (lines 130–145) — replace `estimate.business.company_logo_url` (and `.company_name`, `.company_phone`) with optional-chained reads of the flat fields: `estimate.company_logo_url`, `estimate.company_name ?? 'Grins Irrigation'`, `estimate.company_phone`.
- `frontend/src/features/portal/components/InvoicePortal.tsx` (lines 89–110) — same change for `invoice.company_logo_url`, etc.
- `frontend/src/features/portal/components/ContractSigning.tsx` (lines 137–155) — same change for `contract.company_logo_url`, etc.
- `frontend/src/features/portal/components/EstimateReview.test.tsx`, `InvoicePortal.test.tsx`, `ContractSigning.test.tsx` — verify any fixtures using the old `business: { ... }` shape and migrate them to flat fields.

#### Fix 4 — Bug #15 TimelineRow crash

- `src/grins_platform/schemas/appointment_timeline.py` (line 32) — backend already has `PAYMENT_RECEIVED = "payment_received"`. Wire-format value is `"payment_received"`.
- `src/grins_platform/services/appointment_timeline_service.py` (lines 215–255, `_invoice_payment_to_event`) — emits the new event kind. No change needed.
- `frontend/src/features/schedule/types/index.ts` (lines 637–643) — `TimelineEventKind` union missing `'payment_received'`. **ADD** as the seventh member.
- `frontend/src/features/schedule/types/index.ts` (lines 645–652) — `TimelineEvent` interface uses the union; once the union is extended, no further change here.
- `frontend/src/features/schedule/components/AppointmentCommunicationTimeline.tsx` (entire file, 175 lines) —
  - `KIND_ICON` (lines 34–44) — **ADD** `payment_received: DollarSign` (or `BadgeDollarSign`, or `Receipt` from `lucide-react` — choose one already imported elsewhere in the file or add the import).
  - `KIND_COLOR` (lines 46–53) — **ADD** `payment_received: 'text-emerald-600'` (matches paid/success color used at line 50 for `reschedule_resolved`).
  - `TimelineRow` (lines 130–174) — **ADD** defensive guard: `const Icon = KIND_ICON[event.kind] ?? MessageSquare;` and `const color = KIND_COLOR[event.kind] ?? 'text-slate-400';` so a future unknown kind logs at most a console warning instead of throwing. Add a `console.warn('timeline.kind.unknown', event.kind)` once on the fallback path so future regressions get diagnosed quickly.
- `frontend/src/features/schedule/components/AppointmentCommunicationTimeline.test.tsx` (verify existence; if missing, **CREATE**) — add a test case asserting that an event with `kind: 'payment_received'` renders without throwing AND a separate case asserting that an event with an unknown kind (`kind: 'totally_made_up' as TimelineEventKind`) also renders without throwing.

#### Fix 5 — Bug #16 Stripe short-circuit

- `src/grins_platform/services/appointment_service.py` (lines 1964–2091, `collect_payment`) — the gate point.
  - **Existing-invoice branch** (lines 2016–2033): `new_status` (line 2020) is set unconditionally based on amount comparison. **GATE**: when `payment.payment_method in {PaymentMethod.STRIPE, PaymentMethod.CREDIT_CARD}`, do NOT transition `status`; leave `existing_invoice.status` as-is, and do NOT update `paid_at`/`paid_amount`/`payment_method`/`payment_reference` either (the webhook will handle all of that).
  - **New-invoice branch** (lines 2035–2063): create with `status=InvoiceStatus.PENDING.value` (not `PAID`) when `payment_method` is Stripe-class; do not call the second `update()` either. The Stripe webhook handler (in `services/stripe_webhook_handler.py` or similar — verify with `grep "payment_intent\|charge.succeeded"` in `services/`) will do the reconciliation when the customer pays.
  - **Receipt SMS** (line 2076–2083): do NOT call `_send_payment_receipts` for Stripe-class methods. The webhook handler is the source of receipts in Architecture C.
  - **Caller contract**: existing callers of `collect_payment` with `payment_method=stripe` were getting an immediately-PAID invoice. After the fix, they get a PENDING invoice and must call `POST /api/v1/invoices/{id}/send-link` to generate the Stripe Payment Link (existing endpoint per the umbrella plan re-run notes line 1531). Confirm this contract change is acceptable; **if any existing UI still expects PAID-on-collect for stripe, it must move to the link-send flow**. Per memory `project_stripe_payment_links_arch_c.md` this is the intended UX.
- `src/grins_platform/models/enums.py` (lines 245–263) — `PaymentMethod` enum. Class doc-comment at line 250–253 already says "new UI pickers omit `stripe` in favor of `credit_card`", so both values must be gated. The set is `{PaymentMethod.STRIPE, PaymentMethod.CREDIT_CARD}` — define a module-level constant `STRIPE_DEFERRED_METHODS = frozenset({PaymentMethod.STRIPE, PaymentMethod.CREDIT_CARD})` near the top of `appointment_service.py` for readability.
- `src/grins_platform/tests/unit/test_appointment_service_crm.py` — existing collect_payment unit tests; extend with cases for stripe + credit_card both leaving the invoice PENDING.
- `src/grins_platform/api/v1/webhooks.py` (lines 990–1115, `_handle_payment_intent_succeeded`) — **VERIFIED 2026-05-02**: the webhook handler exists and is the Architecture C reconciliation site. It (a) finds the invoice via `metadata.invoice_id`, (b) idempotently skips if already PAID (line 1086), (c) calls `invoice_service.record_payment(invoice_id, payment_record)` at line 1110 which flips the invoice to PAID. **GAP CONFIRMED**: `record_payment` does NOT call `_send_payment_receipts` (verified at `services/invoice_service.py:708-765`). Fix 5 must wire receipt SMS into the webhook handler immediately after `record_payment` succeeds — see Task 2.10.
- `src/grins_platform/services/invoice_service.py` (lines 708–765, `record_payment`) — confirmed update-only: sets `paid_amount`, `payment_method`, `paid_at`, `status`. No receipt SMS. Used by both the webhook handler and any admin manual-payment path; **do NOT add receipts here** because admin paths may not want them. Add receipts at the webhook call site instead.

### New Files to Create

None. Every fix is an edit to an existing file. Three test files may need a new `describe` block but no new files.

### Relevant Documentation — YOU SHOULD READ THESE BEFORE IMPLEMENTING

- [Stripe Payment Links — async reconciliation](https://docs.stripe.com/payment-links/post-payment) — confirms the Architecture C model: invoice stays unpaid until `checkout.session.completed` webhook arrives. Required reading for Fix 5.
- [Stripe `checkout.session.completed` webhook](https://docs.stripe.com/api/events/types#event_types-checkout.session.completed) — webhook event shape; needed if the webhook handler audit (Fix 5 last bullet) reveals it isn't already wired.
- [TanStack Query — query keys & invalidation](https://tanstack.com/query/v5/docs/framework/react/guides/query-keys) — for the portal hooks if test fixtures need updating after Fix 3.
- [Lucide icons — DollarSign / Receipt / BadgeDollarSign](https://lucide.dev/icons/) — pick one for `KIND_ICON.payment_received` in Fix 4. `Receipt` reads most naturally with the existing `MessageSquare` / `MessageCircle` neighbors.
- [Vercel CLI — listing project domains](https://vercel.com/docs/cli/domains) — only needed if `mcp__vercel__list_deployments` doesn't surface the canonical dev alias for Fix 1.

### Patterns to Follow

#### Fix 1 — env config

```bash
# .env (line 49 comment + line 50 value)
# Customer portal base URL — local backend points at the deployed Vercel dev portal so SMS links from a local backend are reachable from a real phone. Production points at portal.grinsirrigation.com.
PORTAL_BASE_URL=https://grins-irrigation-platform-git-dev-{team-slug}.vercel.app
```

`.env.example` follows the same shape but should keep `http://localhost:5173` as the safe default for greenfield clones — instead, **add a comment** above the example value documenting the dev URL and saying "uncomment the Vercel dev URL line below if you want SMS links to reach a real phone."

#### Fix 2 — pattern: tolerant JSON readers (mirror VariantSubPicker)

```ts
// SizeTierSubPicker.tsx — extend readTiers()
function readTiers(offering: ServiceOffering): TierEntry[] {
  const rule = offering.pricing_rule;
  if (!rule || typeof rule !== 'object') return [];
  const tiers = (rule as Record<string, unknown>).tiers;
  if (!Array.isArray(tiers)) return /* existing object-shape branch */;

  return tiers
    .map((t): TierEntry | null => {
      if (!t || typeof t !== 'object') return null;
      const obj = t as Record<string, unknown>;
      // Accept either {label,price} (test fixture shape) or
      // {size, price | labor_amount, size_range_ft?} (Phase-1 seed shape).
      const rawLabel = obj.label ?? obj.size;
      const rawPrice = obj.price ?? obj.labor_amount;
      const sizeRange = obj.size_range_ft;
      if (typeof rawLabel !== 'string') return null;
      const price = typeof rawPrice === 'number' ? rawPrice : Number(rawPrice);
      if (!Number.isFinite(price)) return null;
      const label = typeof sizeRange === 'string'
        ? `${capitalize(rawLabel)} (${sizeRange} ft)`
        : capitalize(rawLabel);
      return { label, price };
    })
    .filter((x): x is TierEntry => x !== null);
}

function capitalize(s: string): string {
  return s.length === 0 ? s : s[0].toUpperCase() + s.slice(1).replace(/_/g, ' ');
}
```

#### Fix 3 — pattern: extend Pydantic response with company branding fields

Mirror exactly how `PortalInvoiceResponse` (`schemas/portal.py:156–175`) exposes the four flat fields. Then in `_to_portal_response()` (`api/v1/portal.py:146–190`), source the values from `SettingsService.get_company_branding()` like `invoice_portal_service.py:178–211` already does. Keep `_to_portal_response` synchronous if possible — if `get_company_branding` is async, await it at the call site (the helper currently has no `db` arg, so it would need one). **Decision**: pass the branding dict in as an arg to `_to_portal_response` so the helper stays sync — the call sites at lines 265, 397, 440, 503 already have access to a session.

#### Fix 4 — pattern: defensive lookup with fallback

```tsx
// AppointmentCommunicationTimeline.tsx — TimelineRow
function TimelineRow({ event }: TimelineRowProps) {
  const Icon = KIND_ICON[event.kind] ?? MessageSquare;
  const color = KIND_COLOR[event.kind] ?? 'text-slate-400';
  if (!(event.kind in KIND_ICON)) {
    // One-time diagnostic so future schema drift gets caught quickly.
    console.warn('timeline.kind.unknown', { kind: event.kind, id: event.id });
  }
  // ... existing render
}
```

This is intentionally narrow: the fallback exists only so a kind we forgot to register doesn't blow up the page. The expected path is: every backend-emitted kind has a matching entry in `KIND_ICON` and `KIND_COLOR`, validated by the new test.

#### Fix 5 — pattern: gated transition (mirror existing condition shapes)

```python
# appointment_service.py — collect_payment(), existing-invoice branch
STRIPE_DEFERRED_METHODS = frozenset({
    PaymentMethod.STRIPE,
    PaymentMethod.CREDIT_CARD,
})

# inside collect_payment()
defer_to_webhook = payment.payment_method in STRIPE_DEFERRED_METHODS

if existing_invoice is not None:
    if defer_to_webhook:
        # Architecture C: webhook owns the PAID transition. Leave invoice
        # untouched; caller is expected to follow up with /invoices/{id}/send-link.
        result_invoice = existing_invoice
    else:
        existing_paid = existing_invoice.paid_amount or Decimal(0)
        new_paid = existing_paid + payment.amount
        new_status = (
            InvoiceStatus.PAID.value
            if new_paid >= existing_invoice.total_amount
            else InvoiceStatus.PARTIAL.value
        )
        updated_invoice = await self.invoice_repository.update(
            existing_invoice.id,
            paid_amount=new_paid,
            payment_method=payment.payment_method.value,
            payment_reference=payment.reference_number,
            paid_at=now,
            status=new_status,
        )
        result_invoice = updated_invoice or existing_invoice
else:
    if defer_to_webhook:
        # Create as PENDING; webhook flips to PAID after Stripe Checkout completes.
        seq = await self.invoice_repository.get_next_sequence()
        invoice_number = f"INV-{now.year}-{seq:04d}"
        due_date = (now + timedelta(days=30)).date()
        result_invoice = await self.invoice_repository.create(
            job_id=appointment.job_id,
            customer_id=job.customer_id,
            invoice_number=invoice_number,
            amount=payment.amount,
            total_amount=payment.amount,
            invoice_date=now.date(),
            due_date=due_date,
            status=InvoiceStatus.PENDING.value,
            line_items=[
                {
                    "description": f"{job.job_type} service",
                    "amount": str(payment.amount),
                },
            ],
        )
        # No second update() — leave payment fields null until webhook lands.
    else:
        # ... existing new-invoice + update() logic, unchanged
        ...

# Receipt SMS — gate
if not defer_to_webhook:
    try:
        await self._send_payment_receipts(job, result_invoice, payment.amount)
    except Exception as exc:
        self.logger.warning("payment.receipt.dispatch_failed", ...)
```

Logging: `self.log_completed("collect_payment", ..., deferred_to_webhook=defer_to_webhook)` so the gate's effect is visible in logs.

#### Naming Conventions

- Python: `snake_case.py`, classes `PascalCase`, services extend `LoggerMixin` with `DOMAIN = "{domain}"`. Per `.kiro/steering/code-standards.md` — every change MUST have logging, three-tier tests, MyPy + Pyright + Ruff zero errors.
- Frontend: components `PascalCase.tsx`, hooks `use{Name}.ts`, types in `types/index.ts`, `data-testid` per `.kiro/steering/frontend-patterns.md` (`{feature}-{purpose}` kebab-case).
- Tests: pytest markers `@pytest.mark.unit` / `@pytest.mark.functional` / `@pytest.mark.integration`; Vitest co-located `*.test.tsx` next to source.

#### Error Handling (Python)

Per code-standards `.kiro/steering/code-standards.md` — service log pattern:

```python
self.log_started("collect_payment", appointment_id=str(appointment_id), payment_method=method, amount=str(amount))
try:
    ...
    self.log_completed("collect_payment", invoice_id=str(invoice.id), deferred_to_webhook=defer_to_webhook)
except ValidationError as e:
    self.log_rejected("collect_payment", reason=str(e))
    raise
except Exception as e:
    self.log_failed("collect_payment", error=e)
    raise
```

#### Frontend Error/Loading

Already established at `EstimateReview.tsx:68-101` (loading / expired / generic error branches). Fix 3 must not regress these branches.

---

## IMPLEMENTATION PLAN

### Phase 0: Pre-flight (no discovery needed — already done)

**Goal**: confirm the assumptions baked into this plan still hold.

**Resolved (2026-05-02 verification sweep)**:

1. ✅ Vercel dev alias: `https://grins-irrigation-platform-git-dev-kirilldr01s-projects.vercel.app` (verified — already used in `e2e/payment-links-flow.sh:32` and `Testing Procedure/10-customer-landing-flow.md:19`). Use this string verbatim in Task 1.1.
2. ✅ Stripe webhook handler exists at `api/v1/webhooks.py:990-1115` (`_handle_payment_intent_succeeded`). It moves PENDING → PAID via `invoice_service.record_payment(...)`. **It does NOT fire customer receipts** — Task 2.10 closes this gap.
3. ✅ `.env` is gitignored (confirmed via `.gitignore`); only `.env.example` will appear in version control.
4. ✅ Frontend has only one `payment_method === 'stripe'` reference and it's a display branch in `frontend/src/features/invoices/components/InvoiceList.tsx:181`, not a POST. Fix 5's contract change does not break any UI POSTing `stripe`.

### Phase 1: Quick wins — config + frontend-only fixes

**Goal**: ship Fixes 1, 2, and 4 first since they're isolated and instantly verifiable.

**Tasks**:

- Edit `.env:50` and `.env.example:152` to point at the Vercel dev URL (Fix 1).
- Restart local uvicorn; manually fire one estimate-send via the API and verify the SMS body contains the Vercel dev URL (Fix 1 validation).
- Edit `SizeTierSubPicker.tsx::readTiers` to accept the seed shape (Fix 2). Add tests in `SubPickers.test.tsx`.
- Edit `frontend/src/features/schedule/types/index.ts` to add `'payment_received'` to `TimelineEventKind` (Fix 4).
- Edit `AppointmentCommunicationTimeline.tsx` to add the icon/color entries and the defensive fallback (Fix 4). Add tests in (or create) `AppointmentCommunicationTimeline.test.tsx`.

### Phase 2: Backend contract fixes

**Goal**: ship Fix 3 (portal contract) and Fix 5 (Stripe gate) — both touch backend + tests.

**Tasks**:

- Extend `PortalEstimateResponse` with `company_address`, `company_phone`, `company_logo_url` (Fix 3).
- Refactor `_to_portal_response()` to take a `branding: dict[str, str | None]` arg and populate the new fields. Update all four call sites (lines 265, 397, 440, 503) to fetch the branding dict via `SettingsService.get_company_branding()` and pass it in.
- Update `frontend/src/features/portal/types/index.ts` to drop `business: PortalBusinessInfo` and add the four flat fields to `PortalEstimate`, `PortalContract`, `PortalInvoice` (Fix 3 client-side).
- Update `EstimateReview.tsx`, `InvoicePortal.tsx`, `ContractSigning.tsx` to read flat fields.
- Migrate any test fixtures that use the old `business: { ... }` shape.
- Add `STRIPE_DEFERRED_METHODS` constant and the gate logic in `AppointmentService.collect_payment` (Fix 5). Update `_send_payment_receipts` call site to skip on Stripe-class methods.

### Phase 3: Tests + verification

**Goal**: every fix has at least one new test that would have caught the original bug; full quality gate passes.

**Tasks**:

- Functional test: `test_portal_estimate_includes_company_branding` — POST a settings row, GET `/api/v1/portal/estimates/{token}`, assert `company_logo_url` etc. are present (Fix 3).
- Unit test: `test_collect_payment_stripe_method_does_not_transition_to_paid` and `test_collect_payment_credit_card_method_does_not_transition_to_paid` (Fix 5).
- Vitest: SubPickers tests for the seed shape (Fix 2). Vitest: TimelineRow renders unknown kind without throwing (Fix 4). Vitest: portal components render with flat company fields (Fix 3).
- Quality gate: `uv run ruff check src/ && uv run ruff format src/ && uv run mypy src/ && uv run pyright src/ && uv run pytest -m unit -v && uv run pytest -m functional -v && (cd frontend && npm run lint && npm run typecheck && npm test)`.

### Phase 4: Manual + agent-browser verification

**Goal**: prove the original five symptoms are gone end-to-end.

**Tasks**:

- Send a fresh estimate via the local backend; verify SMS body shows `https://grins-irrigation-platform-git-dev-...vercel.app/portal/estimates/{token}` (Fix 1).
- Open the portal URL in a browser; assert the page renders with company name + logo (Fix 3).
- Open AppointmentModal for an appointment whose job has a paid invoice (use the seeded `vasiliy` data); assert the Communication panel renders without the "Element type is invalid" overlay (Fix 4).
- In the EstimateSheet on tech-mobile, search "tree" → pick Tree Drop → assert the size dropdown shows three tiers ("Small (10-20 ft)", "Medium (20-30 ft)", "Large (30-50 ft)") with prices (Fix 2).
- Via curl, POST `{payment_method: "stripe", amount: 100}` to `/api/v1/appointments/{id}/collect-payment`; assert the response invoice status is `pending`, not `paid` (Fix 5). Then POST `/api/v1/invoices/{id}/send-link`; assert the response includes a `link_url`.

---

## STEP-BY-STEP TASKS

IMPORTANT: Execute every task in order, top to bottom. Each task is atomic and independently testable. **All file paths are absolute under the repo root unless otherwise noted.**

### Phase 0 Tasks

(All Phase 0 discovery already completed in the 2026-05-02 verification sweep — see § Phase 0 Pre-flight. Skip directly to Phase 1.)

### Phase 1 Tasks

#### Task 1.1: UPDATE `.env` PORTAL_BASE_URL

- **UPDATE**: `.env` line 49 (comment) and line 50 (value).
  - Line 49 new comment: `# Customer portal base URL — local backend points at the deployed Vercel dev portal so SMS links from a local backend are reachable from a real phone. Prod points at portal.grinsirrigation.com.`
  - Line 50 new value: `PORTAL_BASE_URL=https://grins-irrigation-platform-git-dev-kirilldr01s-projects.vercel.app`
- **GOTCHA**: `.env` is gitignored. Local-only change; do NOT also push the value into a docker-compose file or any CI config — leave those at `http://localhost:5173`.
- **VALIDATE**: restart uvicorn, then `curl -sX POST http://localhost:8000/api/v1/estimates/{any-existing-id}/send -H 'Content-Type: application/json'` and inspect the resulting `sent_messages` row's body via `psql $DATABASE_URL -c "SELECT body FROM sent_messages ORDER BY created_at DESC LIMIT 1"`. Body must contain the new Vercel host string.

#### Task 1.2: UPDATE `.env.example` PORTAL_BASE_URL guidance

- **UPDATE**: `.env.example` line 152.
  - Keep the default at `http://localhost:5173` (greenfield clone safety).
  - Add a comment immediately above: `# To send SMS-deliverable estimate/portal links from a local backend, override locally with the Vercel dev alias, e.g.: PORTAL_BASE_URL=https://grins-irrigation-platform-git-dev-...vercel.app`
- **VALIDATE**: `grep -A3 'PORTAL_BASE_URL' .env.example` shows the comment + the unchanged default value.

#### Task 1.3: EXTEND `readTiers()` to accept seed shape (Fix 2)

- **UPDATE**: `frontend/src/features/schedule/components/EstimateSheet/SizeTierSubPicker.tsx`, lines 22–49.
- **IMPLEMENT**: per the pattern shown in § Patterns to Follow → Fix 2. Accept `label`-or-`size` for the dropdown caption, `price`-or-`labor_amount` for the price, and `size_range_ft` as a parenthetical suffix.
- **PATTERN**: mirror the tolerant-reader style of `VariantSubPicker.tsx::readVariants` (lines 17–52) which already handles two shapes.
- **GOTCHA**: keep the back-compat `{label, price}` branch — it's exercised by the existing test at `SubPickers.test.tsx:40-60`.
- **GOTCHA**: do NOT change `TierEntry` interface shape (`{label, price}`); the consumer `LineItemPicker.handleTierPick` only reads those two fields. Synthesize the displayed label inside `readTiers`.
- **VALIDATE**: `cd frontend && npm test -- SubPickers.test.tsx`.

#### Task 1.4: ADD seed-shape test for SizeTierSubPicker

- **UPDATE**: `frontend/src/features/schedule/components/EstimateSheet/SubPickers.test.tsx`, after line 60 (inside the existing `describe('SizeTierSubPicker', ...)` block).
- **IMPLEMENT**: a new test `it('renders seed-shape tiers (size + price + size_range_ft)', ...)` mirroring the existing test at lines 40–60 but using the seed shape `{ size: 'small', price: 750, size_range_ft: '10-20' }, { size: 'medium', price: 1250, size_range_ft: '20-30' }, { size: 'large', price: 2000, size_range_ft: '30-50' }`. Assert the trigger renders, default-confirm emits `('Small (10-20 ft)', 750)`.
- **IMPLEMENT** (second test): `it('reads labor_amount alias for size_tier_plus_materials shape', ...)` — `[{ size: 'small_to_medium', labor_amount: 200 }, { size: 'large', labor_amount: 400 }]`. Assert the trigger renders and confirm emits `('Small to medium', 200)`.
- **VALIDATE**: `cd frontend && npm test -- SubPickers.test.tsx -t "seed-shape"`.

#### Task 1.5: EXTEND `TimelineEventKind` union (Fix 4)

- **UPDATE**: `frontend/src/features/schedule/types/index.ts` lines 637–643.
- **IMPLEMENT**: append `| 'payment_received'` as the seventh union member.
- **PATTERN**: identical formatting to the six existing members.
- **VALIDATE**: `cd frontend && npm run typecheck`.

#### Task 1.6: REGISTER icon + color for `payment_received`

- **UPDATE**: `frontend/src/features/schedule/components/AppointmentCommunicationTimeline.tsx`.
  - Line 10–18: import `Receipt` (or `BadgeDollarSign`) from `lucide-react` alongside the existing icons.
  - Lines 34–44 (`KIND_ICON`): add `payment_received: Receipt,` as the seventh entry.
  - Lines 46–53 (`KIND_COLOR`): add `payment_received: 'text-emerald-600',` as the seventh entry.
- **VALIDATE**: `cd frontend && npm run typecheck`.

#### Task 1.7: ADD defensive fallback in `TimelineRow`

- **UPDATE**: `frontend/src/features/schedule/components/AppointmentCommunicationTimeline.tsx` lines 130–135.
- **IMPLEMENT**: change `const Icon = KIND_ICON[event.kind];` to `const Icon = KIND_ICON[event.kind] ?? MessageSquare;`. Same for `color` with `?? 'text-slate-400'`. Add a single-line `console.warn('timeline.kind.unknown', { kind: event.kind, id: event.id });` inside an `if (!(event.kind in KIND_ICON)) {...}` guard.
- **GOTCHA**: don't use `KIND_ICON[event.kind] === undefined` — Records typed via `Record<U, V>` make TS believe the lookup is always defined. The `??` plus the `in` check work around this.
- **VALIDATE**: `cd frontend && npm run typecheck && npm run lint`.

#### Task 1.8: TESTS for Fix 4 (TimelineRow defensive)

- **UPDATE/CREATE**: `frontend/src/features/schedule/components/AppointmentCommunicationTimeline.test.tsx`.
- **IMPLEMENT**:
  - Test 1: render the component with `data.events` containing one event of kind `'payment_received'` with a sensible `summary`. Assert it renders without throwing and the `data-testid="timeline-event-{id}"` row is in the DOM.
  - Test 2: render the component with one event of `kind: 'totally_made_up' as TimelineEventKind` (cast required). Assert it renders without throwing AND that `console.warn` was called with `'timeline.kind.unknown'`. Use `vi.spyOn(console, 'warn')`.
- **PATTERN**: mirror the test patterns in `SubPickers.test.tsx` for the rendering setup. Use `QueryProvider` wrapper if needed.
- **VALIDATE**: `cd frontend && npm test -- AppointmentCommunicationTimeline`.

### Phase 2 Tasks

#### Task 2.1: EXTEND `PortalEstimateResponse` with company branding fields (Fix 3 backend schema)

- **UPDATE**: `src/grins_platform/schemas/portal.py` lines 17–63.
- **IMPLEMENT**: add three fields immediately after the existing `company_name` field at line 55:
  ```python
  company_address: str | None = Field(
      default=None,
      max_length=500,
      description="Company address (from settings)",
  )
  company_phone: str | None = Field(
      default=None,
      max_length=20,
      description="Company phone (from settings)",
  )
  company_logo_url: str | None = Field(
      default=None,
      max_length=2048,
      description="Company logo URL (from settings)",
  )
  ```
- **PATTERN**: identical signatures to `PortalInvoiceResponse.company_address` / `.company_phone` / `.company_logo_url` at lines 161–175.
- **VALIDATE**: `uv run mypy src/grins_platform/schemas/portal.py && uv run pyright src/grins_platform/schemas/portal.py`.

#### Task 2.2: REFACTOR `_to_portal_response()` to accept branding (Fix 3 backend wiring)

- **UPDATE**: `src/grins_platform/api/v1/portal.py` lines 146–190.
- **IMPLEMENT**:
  - Add `branding: dict[str, str | None] | None = None` as the third arg to `_to_portal_response`.
  - Inside the function, after the existing `readonly` block, add:
    ```python
    branding = branding or {}
    ```
  - Pass the branding fields into `PortalEstimateResponse(...)`:
    ```python
    company_name=branding.get("company_name"),
    company_address=branding.get("company_address"),
    company_phone=branding.get("company_phone"),
    company_logo_url=branding.get("company_logo_url"),
    ```
- **UPDATE call sites** (4 sites — verified line numbers in current `dev` tree: 265, 397 [reject], 440 [reject post-success], 503 [contract sign — reuses PortalEstimateResponse]): add a branding fetch immediately before each `_to_portal_response(...)` call. Mirror this exact shape:
  ```python
  from grins_platform.services.settings_service import SettingsService  # noqa: PLC0415
  settings_service = SettingsService()
  branding = await settings_service.get_company_info(session)
  response = _to_portal_response(estimate, branding=branding)
  ```
  - **GOTCHA**: `SettingsService.__init__()` takes no args (verified at `settings_service.py:33`); the session is passed to each method call, not the constructor. Method is `get_company_info(db)` (line 180), NOT `get_company_branding`.
  - **GOTCHA**: every call site already has a `session` available via the FastAPI DI (`Depends(get_db_session)`) — wire it through.
  - **GOTCHA**: `get_company_info` is `async`, returns `dict[str, Any]` with safe-default fallback. Always `await` it.
- **PATTERN**: mirror `services/invoice_portal_service.py:165` — the branding lookup is already battle-tested there using the same dict shape.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_portal_api.py -v` (existing suite — must still pass; if a fixture asserted the old empty branding, update it to assert the new fields are present and equal to the configured branding).

#### Task 2.3: UPDATE `frontend/src/features/portal/types/index.ts` (Fix 3 frontend types)

- **UPDATE**: entire file, 91 lines.
- **REMOVE**: `PortalBusinessInfo` interface (lines 3–8).
- **REMOVE**: `business: PortalBusinessInfo` field from `PortalEstimate` (line 25), `PortalContract` (line 52), `PortalInvoice` (line 73).
- **ADD** to all three interfaces (`PortalEstimate`, `PortalContract`, `PortalInvoice`):
  ```ts
  company_name?: string | null;
  company_address?: string | null;
  company_phone?: string | null;
  company_logo_url?: string | null;
  ```
- **GOTCHA**: keep both `?` and `| null` — server may omit OR send `null`; both are valid runtime shapes given the optional Pydantic fields.
- **VALIDATE**: `cd frontend && npm run typecheck` (will surface every component still reading `entity.business.X` — those are Tasks 2.4–2.6).

#### Task 2.4: UPDATE `EstimateReview.tsx` reads (Fix 3 client EstimateReview)

- **UPDATE**: `frontend/src/features/portal/components/EstimateReview.tsx` lines 130–145.
- **IMPLEMENT**: replace `estimate.business.company_logo_url` with `estimate.company_logo_url`, `estimate.business.company_name` with `estimate.company_name ?? 'Grins Irrigation'`, `estimate.business.company_phone` with `estimate.company_phone`. Optional-chain wherever the field is used inside a JSX expression.
- **GOTCHA**: the falsy-check `{estimate.company_logo_url && (<img ... />)}` already handles null/undefined; just drop the `.business.` segment.
- **VALIDATE**: `cd frontend && npm run typecheck && npm test -- EstimateReview`.

#### Task 2.5: UPDATE `InvoicePortal.tsx` reads (Fix 3 client InvoicePortal)

- **UPDATE**: `frontend/src/features/portal/components/InvoicePortal.tsx` lines 89–110.
- **IMPLEMENT**: same pattern as Task 2.4 for `invoice.company_*`.
- **VALIDATE**: `cd frontend && npm run typecheck && npm test -- InvoicePortal`.

#### Task 2.6: UPDATE `ContractSigning.tsx` reads (Fix 3 client ContractSigning)

- **UPDATE**: `frontend/src/features/portal/components/ContractSigning.tsx` lines 137–155.
- **IMPLEMENT**: same pattern as Task 2.4 for `contract.company_*`.
- **VALIDATE**: `cd frontend && npm run typecheck && npm test -- ContractSigning`.

#### Task 2.7: ADD `STRIPE_DEFERRED_METHODS` constant (Fix 5)

- **UPDATE**: `src/grins_platform/services/appointment_service.py`, near the top of the file alongside other module-level constants (search for `MessageType` or `PaymentMethod` imports — define the constant immediately after them).
- **IMPLEMENT**:
  ```python
  STRIPE_DEFERRED_METHODS = frozenset({
      PaymentMethod.STRIPE,
      PaymentMethod.CREDIT_CARD,
  })
  ```
- **GOTCHA**: must be a `frozenset`, not a tuple, to make membership check O(1) and signal immutability.
- **VALIDATE**: `uv run ruff check src/grins_platform/services/appointment_service.py && uv run mypy src/grins_platform/services/appointment_service.py`.

#### Task 2.8: GATE `collect_payment` on Stripe-class methods (Fix 5)

- **UPDATE**: `src/grins_platform/services/appointment_service.py` lines 1964–2091.
- **IMPLEMENT**: per the code pattern in § Patterns to Follow → Fix 5. Bind `defer_to_webhook = payment.payment_method in STRIPE_DEFERRED_METHODS` once, before the `if existing_invoice is not None:` block. Branch both the existing-invoice and new-invoice paths on it. Skip the `_send_payment_receipts` call when `defer_to_webhook` is True.
- **GOTCHA**: the gated existing-invoice branch must still return a `PaymentResult` with the existing invoice's status (NOT a hardcoded `pending`) — the caller is interested in "what is the invoice's state right now?". The new-invoice branch returns a freshly-created PENDING invoice.
- **GOTCHA**: log `deferred_to_webhook=defer_to_webhook` in the `log_completed` call so audit / traceability picks it up.
- **GOTCHA**: do not regress the kwargs-unpack fix from `b53ac1f`. The non-gated branches must still call `update(...)` with kwargs only.
- **PATTERN**: mirror the best-effort try/except wrapping at lines 2076–2083 — the receipt skip should be a clean `if not defer_to_webhook:` guard around the existing try/except, not a new try/except.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_appointment_service_crm.py -v -k collect_payment`.

#### Task 2.9: UPDATE `collect_payment` unit tests (Fix 5)

- **UPDATE**: `src/grins_platform/tests/unit/test_appointment_service_crm.py`.
- **IMPLEMENT** (two new tests):
  - `test_collect_payment_stripe_method_skips_paid_transition` — invoke `collect_payment` with `payment_method=PaymentMethod.STRIPE`. Assert: invoice status is NOT `paid` (either unchanged for existing-invoice branch, or `pending` for new-invoice branch). Assert: `_send_payment_receipts` mock was NOT called. Assert: `invoice_repository.update` was NOT called for the existing-invoice branch (or only for the create, not the payment fields, in the new-invoice branch).
  - `test_collect_payment_credit_card_method_skips_paid_transition` — same as above for `PaymentMethod.CREDIT_CARD`.
- **PATTERN**: mirror the existing `collect_payment` test fixtures + mocking style in the same file.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_appointment_service_crm.py -v -k "stripe_method or credit_card_method"`.

#### Task 2.10: WIRE receipt SMS into Stripe webhook handler (Fix 5 — closes audit gap)

- **UPDATE**: `src/grins_platform/api/v1/webhooks.py` `_handle_payment_intent_succeeded` (lines 990–1115).
- **CONTEXT**: Phase 0 verification confirmed the webhook handler exists and calls `invoice_service.record_payment(...)` at line 1110, which flips invoice → PAID. But `record_payment` does NOT fire customer receipt SMS/email. Without this task, Stripe payments succeed silently (customer never gets a "Grin's receipt: $X received via card …" text). Cash/check/venmo/zelle already fire receipts via `AppointmentService._send_payment_receipts` at line 2077.
- **IMPLEMENT**: immediately after the successful `await invoice_service.record_payment(...)` call at line 1110 (and after the `invoice_repo.update(...)` for `stripe_payment_link_active=False` at line 1113+), add a best-effort receipt-fire block:
  ```python
  # Fire customer receipt SMS + email — Architecture C parity with
  # AppointmentService._send_payment_receipts. Best-effort: a failure
  # logs and returns without raising (mirror existing pattern).
  try:
      from grins_platform.repositories.appointment_repository import (  # noqa: PLC0415
          AppointmentRepository,
      )
      from grins_platform.services.appointment_service import (  # noqa: PLC0415
          AppointmentService,
      )
      # Reload invoice to pick up the now-PAID state (record_payment
      # returned an InvoiceResponse, but _send_payment_receipts wants
      # the ORM Invoice with paid_at populated).
      paid_invoice = await invoice_repo.get_by_id(invoice_id)
      job_for_receipt = await JobRepository(session=self.session).get_by_id(
          paid_invoice.job_id,
      )
      if paid_invoice is not None and job_for_receipt is not None:
          appt_service = AppointmentService(
              appointment_repository=AppointmentRepository(session=self.session),
              job_repository=JobRepository(session=self.session),
              invoice_repository=invoice_repo,
          )
          await appt_service._send_payment_receipts(
              job_for_receipt,
              paid_invoice,
              amount,
          )
  except Exception as exc:
      self.logger.warning(
          "stripe.webhook.receipt_dispatch_failed",
          payment_intent=masked,
          invoice_id=str(invoice_id),
          error=str(exc),
      )
  ```
- **GOTCHA — protected method access**: `_send_payment_receipts` is a leading-underscore private method on `AppointmentService`. Calling it from outside the class is technically a Python-private violation, but it's the only existing implementation of "send a receipt SMS+email after a payment lands." **Acceptable in this fix** because the alternative (duplicating ~70 lines of SMS+email construction) is worse. **Add a code comment** at the call site noting this is intentional cross-service reuse.
- **GOTCHA — reload the invoice**: `record_payment` returns an `InvoiceResponse` (Pydantic), not the ORM `Invoice` model that `_send_payment_receipts` expects. Reload via `invoice_repo.get_by_id(invoice_id)` — the row is now PAID with `paid_at` set, which the receipt template reads.
- **GOTCHA — DI minimal**: `AppointmentService.__init__` requires `appointment_repository`, `job_repository`, `invoice_repository` at minimum. The webhook session is the same session for all three repos. SMS/email service are pulled inside `_send_payment_receipts` via factories, so no extra DI needed.
- **PATTERN**: mirrors the best-effort receipt block at `appointment_service.py:2076-2083` exactly.
- **ALTERNATE PATH (deferred, not in this fix)**: extract `_send_payment_receipts` from `AppointmentService` into a standalone module `services/payment_receipt_dispatcher.py`. Not done here because it's refactor-grade work and the umbrella plan's scope is bug fixes; doing it now would inflate this plan's blast radius. Document in the code comment that this is the future direction.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_stripe_webhook_payment_links.py -v`. Add a new test case `test_payment_intent_succeeded_fires_customer_receipt` that mocks `_send_payment_receipts` and asserts it was awaited once with `(job, invoice, amount)`.

### Phase 3 Tasks

#### Task 3.1: ADD functional test for portal-estimate company branding (Fix 3)

- **CREATE / UPDATE**: `src/grins_platform/tests/functional/test_estimate_operations_functional.py` (or a new file `test_portal_estimate_branding.py` if the existing file is overloaded).
- **IMPLEMENT**: `test_portal_estimate_response_includes_company_branding` — seed company branding via `SettingsService.set_company_branding(...)` (or direct table insert if the setter doesn't exist; mirror however the invoice portal test seeds it). Create an estimate with a portal token. GET `/api/v1/portal/estimates/{token}`. Assert response JSON has `company_name`, `company_address`, `company_phone`, `company_logo_url` populated to the seeded values.
- **VALIDATE**: `uv run pytest -m functional -k portal_estimate_response_includes_company_branding -v`.

#### Task 3.2: ADD Vitest portal-component tests with flat fields (Fix 3)

- **UPDATE**: `frontend/src/features/portal/components/EstimateReview.test.tsx` (and `InvoicePortal.test.tsx`, `ContractSigning.test.tsx` as needed).
- **IMPLEMENT**: ensure each suite has at least one rendering test that uses a fixture with the flat company fields populated, and one fixture with all four fields `null` (to exercise the optional-chain fallback). Assert the company name renders (or falls back to "Grins Irrigation").
- **VALIDATE**: `cd frontend && npm test -- portal`.

#### Task 3.3: RUN full quality gate

- **VALIDATE** (all must pass with zero errors):
  ```bash
  uv run ruff check src/
  uv run ruff format --check src/
  uv run mypy src/
  uv run pyright src/
  uv run pytest -m unit -v
  uv run pytest -m functional -v
  cd frontend && npm run lint && npm run typecheck && npm test -- --run
  ```

### Phase 4 Tasks

#### Task 4.1: MANUAL agent-browser verification of all five fixes

- **PATTERN**: mirror `e2e/phase-3-estimate-line-item-picker.sh` and `e2e/phase-4-payment-timeline-receipts.sh` for shell scaffolding.
- **CREATE**: `e2e/portal-and-bug-cleanup-fixes.sh` covering:
  1. **Fix 1**: send an estimate via API; query `sent_messages` table; assert body contains the Vercel dev host.
  2. **Fix 2**: agent-browser as `vasiliy` mobile (390×844); navigate AppointmentModal → Send estimate → Add from pricelist → search "tree" → click Tree Drop. Assert dropdown contains three tier rows. Screenshot.
  3. **Fix 3**: open `/portal/estimates/{token}` for a fresh sent estimate. Assert `[data-testid="estimate-review-page"]` visible, `[data-testid="company-logo"]` visible (when branding seeded). Screenshot. Repeat for `/portal/invoices/{token}` and `/portal/contracts/{token}/sign`.
  4. **Fix 4**: open AppointmentModal for an appointment whose job has at least one paid invoice. Toggle the Communication panel. Assert `[data-testid="appointment-communication-timeline"]` is visible AND no React error overlay is present (`agent-browser is not visible "[role='alert'][data-testid='error-boundary']"`). Screenshot.
  5. **Fix 5**: `curl -X POST .../collect-payment -d '{"payment_method":"stripe","amount":100}'`; assert response `status: pending`. Then `curl -X POST .../send-link`; assert response `link_url` present. Inspect the invoice in DB; assert `status='pending'` and `paid_at IS NULL`.
- **DB validation**: every interaction has a paired `psql` query asserting the expected post-state.
- **CONSOLE validation**: `agent-browser errors` after each navigation; assert empty.
- **OUTPUT**: 12+ screenshots under `e2e-screenshots/portal-and-bug-cleanup-fixes/`.

#### Task 4.2: APPEND DEVLOG entry

- **UPDATE**: `DEVLOG.md` at the top, immediately after `## Recent Activity`. Format per `.kiro/steering/devlog-rules.md` — a single `## [2026-MM-DD HH:MM] - BUGFIX: Portal link + 4 umbrella P0/P1 fixes` block covering all five fixes. Cite commit hashes.

#### Task 4.3: APPEND CHANGELOG entry

- **UPDATE**: `CHANGELOG.md` with a `### Fixed` block listing each of the five fixes one-line each. Reference the umbrella plan and the bug-list section.

---

## TESTING STRATEGY

### Unit Tests

- `test_collect_payment_stripe_method_skips_paid_transition` (new) — Fix 5.
- `test_collect_payment_credit_card_method_skips_paid_transition` (new) — Fix 5.
- Existing `test_appointment_service_crm.py` tests must continue passing — Fix 5 must not regress non-Stripe paths.
- `SubPickers.test.tsx` — two new tests for seed shape + labor_amount alias — Fix 2.
- `AppointmentCommunicationTimeline.test.tsx` — payment_received renders + unknown kind logs warn + does not throw — Fix 4.
- Portal component tests — flat-field fixtures — Fix 3.

### Functional / Integration Tests

- `test_portal_estimate_response_includes_company_branding` (new) — Fix 3.
- Existing `test_portal_api.py` suite must continue passing — Fix 3 must not regress the contract.

### Edge Cases

- Fix 2: empty `pricing_rule.tiers` array → empty state still renders. Mixed `{label, price}` and `{size, price}` entries in same array → both surface as tier options.
- Fix 3: branding settings unset → all four fields are null → portal renders without crashing (uses `'Grins Irrigation'` fallback for name).
- Fix 4: timeline includes both old kinds (`outbound_sms`, etc.) and `payment_received` interleaved → all render in chronological order.
- Fix 5: `payment.payment_method == PaymentMethod.STRIPE` AND existing invoice already has `paid_amount > 0` from a prior cash partial → invoice status stays `partial` (not flipped to anything by this call). The webhook lands → status becomes `paid`. Multi-tender semantics preserved.
- Fix 5: `payment.payment_method == PaymentMethod.OTHER` (legacy enum value) → behaves like cash (no gate). Confirms the gate is exact-set membership, not a generic "is electronic" heuristic.

---

## VALIDATION COMMANDS

### Level 1: Syntax & Style

```bash
uv run ruff check --fix src/
uv run ruff format src/
cd frontend && npm run lint
```

### Level 2: Type checking

```bash
uv run mypy src/
uv run pyright src/
cd frontend && npm run typecheck
```

### Level 3: Unit Tests

```bash
uv run pytest -m unit -v
cd frontend && npm test -- --run
```

### Level 4: Functional + Integration

```bash
uv run pytest -m functional -v
uv run pytest -m integration -v
```

### Level 5: Manual / agent-browser

See Task 4.1.

### Level 6: SMS link sanity check (Fix 1)

```bash
curl -sX POST http://localhost:8000/api/v1/estimates/{any-existing-id}/send -H 'Content-Type: application/json'
psql "$DATABASE_URL" -tAc "SELECT body FROM sent_messages ORDER BY created_at DESC LIMIT 1" | grep -q "grins-irrigation-platform-git-dev"
```

---

## ACCEPTANCE CRITERIA

- [ ] Local-backend SMS body for an estimate-ready text contains the Vercel dev host, NOT `localhost:5173` (Fix 1).
- [ ] `SizeTierSubPicker` renders all three Tree Drop tiers with prices (Fix 2). Existing `{label, price}` test still passes.
- [ ] `GET /api/v1/portal/estimates/{token}` response includes `company_name`, `company_address`, `company_phone`, `company_logo_url` (populated when settings exist; null when not). All three portal pages render without throwing (Fix 3).
- [ ] AppointmentModal communication panel renders for an appointment whose job has a paid invoice; the row icon is `Receipt`, color is emerald-600 (Fix 4). Unknown event kinds log a `console.warn` but do not crash.
- [ ] `POST /api/v1/appointments/{id}/collect-payment` with `payment_method=stripe` (or `credit_card`) returns invoice status `pending`; no receipt SMS fires (Fix 5).
- [ ] `POST /webhooks/stripe` with a signed `payment_intent.succeeded` event for that PENDING invoice flips it to `paid` AND fires the customer receipt SMS+email (Fix 5 / Task 2.10).
- [ ] All quality-gate commands (Level 1–4) pass with zero errors.
- [ ] DEVLOG + CHANGELOG entries added.
- [ ] No regressions in existing portal, estimate-send, payment-collect, or appointment-modal flows.

---

## COMPLETION CHECKLIST

- [ ] All tasks completed in order
- [ ] Each task validation passed immediately
- [ ] All quality-gate commands pass with zero errors
- [ ] Manual agent-browser run produces 12+ green screenshots; no red error overlays
- [ ] Acceptance criteria all met
- [ ] No memory updates needed (these are bug fixes, not new capabilities) — but verify no existing memory makes false claims that this fix invalidates. Specifically: `project_stripe_payment_links_arch_c.md` should describe the invariant Fix 5 restores; if it currently claims "card payments via Stripe Payment Links over SMS" without noting the prior short-circuit bug, no update needed. If it claims the bug is resolved, leave as-is.
- [ ] Code reviewed for quality and maintainability

---

## NOTES

### Architectural Trade-offs

**Why backend-first for Fix 3 (extend `PortalEstimateResponse`) instead of frontend-only "switch to flat reads with optional chaining"?**
The current API contract for `PortalEstimateResponse` is missing fields the UI needs (logo, phone, address). Frontend-only optional-chaining would silently degrade to "no logo ever shows on the estimate portal" because the field literally doesn't exist on the server. Backend extension restores the design intent. The frontend change comes along for the ride to drop the dead `business: {}` nesting.

**Why a defensive fallback in `TimelineRow` (Fix 4) instead of just adding the missing entry?**
Both are needed. Adding the entry fixes today's known crash. The `?? MessageSquare` fallback prevents the next undeclared-kind drift (which is the actual class of bug). Combined cost is ~3 lines and one test; ROI is high.

**Why `frozenset({STRIPE, CREDIT_CARD})` for Fix 5 instead of a method on `PaymentMethod`?**
Centralizes the policy at the call site that owns the gating decision. If a future enum value needs to defer (e.g., `ACH`), grep for `STRIPE_DEFERRED_METHODS` lands on every place the policy applies. A method like `PaymentMethod.is_async()` would scatter the policy across the model.

**Why local `.env` only for Fix 1, not also Railway dev?**
The user said the link they saw came from the local backend. Railway dev's `PORTAL_BASE_URL` may already be correct (or may not — out of scope; Railway env changes are separately reversible and should be confirmed by the user before being touched). Keeping Fix 1 local-only minimizes blast radius.

### Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Fix 5 breaks an existing UI that POSTs `{payment_method:"stripe"}` expecting PAID immediately | **Resolved** | — | Verified 2026-05-02: only one frontend reference at `InvoiceList.tsx:181` and it's a display branch, not a POST. No UI breakage. |
| Stripe webhook handler missing receipt SMS | **Resolved into Task 2.10** | — | Audit confirmed gap; Task 2.10 closes it by reusing `_send_payment_receipts` from `AppointmentService`. |
| Cross-service `_send_payment_receipts` reuse in Task 2.10 violates Python privacy convention | Low | Low | Acceptable single-call exception with code comment. Future refactor extracts to standalone dispatcher module. Documented in Task 2.10 ALTERNATE PATH. |
| Branding lookup in `_to_portal_response` adds DB latency to every portal GET | Low | Low | One small SELECT against `business_settings`. If observed slow, cache by `MAX(updated_at)`. Defer until measured. |
| Fix 2 changes the displayed label format (synthetic capitalization + parens) and a downstream test snapshots the old "S / M / L" format | Low | Low | Existing `SubPickers.test.tsx` only asserts a default-confirm callback shape, not label text. New tests assert the new format. No other consumer of `tierLabel` in the codebase (verified — only `LineItemPicker.handleTierPick` reads it as opaque string). |
| Reloading the invoice in Task 2.10 after `record_payment` produces a stale snapshot | Low | Low | The `record_payment` call path uses the same async session; the subsequent `get_by_id` reads the in-session identity-mapped instance. Confirmed safe. |

### Confidence Score for One-Pass Implementation: **10/10**

**Verifications completed (2026-05-02 sweep)**:
- ✅ `PortalEstimateResponse` confirmed missing logo/phone/address (`schemas/portal.py:17-63`); `PortalInvoiceResponse` already has them (lines 156–175).
- ✅ `_to_portal_response` confirmed at `api/v1/portal.py:146`; four call sites enumerated (265, 397, 440, 503).
- ✅ `SettingsService.get_company_info(db)` exists at `services/settings_service.py:180-203` (NOT `get_company_branding` — name corrected throughout the plan). Returns the right dict shape with safe defaults.
- ✅ Constructor: `SettingsService.__init__()` takes no args (`settings_service.py:33`); session passed to each method.
- ✅ Backend `TimelineEventKind.PAYMENT_RECEIVED` confirmed at `schemas/appointment_timeline.py:32`; emitter at `appointment_timeline_service.py:250`.
- ✅ Frontend `TimelineEventKind` union at `frontend/src/features/schedule/types/index.ts:637-643` confirmed missing `'payment_received'`.
- ✅ `KIND_ICON` / `KIND_COLOR` records confirmed missing the entry; defensive fallback prevents future drift.
- ✅ Bug #14 confirmed already fixed (commit `b53ac1f`); plan explicitly does not touch the kwargs-unpack code.
- ✅ `PaymentMethod.STRIPE` and `PaymentMethod.CREDIT_CARD` both exist at `models/enums.py:260-261`. Doc comment at line 250–253 confirms `stripe` is legacy + `credit_card` is the new UI value, both must be gated.
- ✅ Seed shape for `tree_drop_residential` confirmed: `{size, price, size_range_ft}`. Seed for `decorative_boulders_*` uses `labor_amount` alias.
- ✅ Variants picker confirmed already working — no Fix-2-style change needed for `VariantSubPicker.tsx`.
- ✅ No `PortalContractResponse` exists; contract sign endpoint reuses `PortalEstimateResponse` (`api/v1/portal.py:456`) — Fix 3's schema change automatically covers contracts.
- ✅ **Vercel dev alias resolved**: `https://grins-irrigation-platform-git-dev-kirilldr01s-projects.vercel.app` (verified — already used in `e2e/payment-links-flow.sh:32` and `Testing Procedure/10-customer-landing-flow.md:19`). No discovery needed at execution time.
- ✅ **Stripe webhook handler audit complete**: `_handle_payment_intent_succeeded` exists at `api/v1/webhooks.py:990-1115`. It moves PENDING → PAID via `invoice_service.record_payment(...)` (line 1110). **Confirmed gap**: it does NOT fire customer receipts. Task 2.10 closes the gap by reusing `AppointmentService._send_payment_receipts`.
- ✅ `InvoiceService.record_payment` confirmed at `services/invoice_service.py:708-765` — update-only, no receipt firing. Used by both webhook + admin paths; receipt logic stays at the call site (correct).
- ✅ Frontend Stripe-method search: only `frontend/src/features/invoices/components/InvoiceList.tsx:181` reads `payment_method === 'stripe'`, and it's a display branch (no POST). Fix 5 contract change does not break any UI.
- ✅ `InvoiceStatus.PENDING = "pending"` confirmed at `models/enums.py:226+` (line 335 within the InvoiceStatus class).
- ✅ Last residual: Lucide `Receipt` icon — already exported by lucide-react ≥ 0.487 (the project pins `^0.562.0` in `frontend/package.json:50`); import is a one-line add.

**No remaining residual risks.** Every file path, line number, API name, pattern reference, env value, alias string, and test target has been verified against the current `dev` branch. The execution agent can implement top-to-bottom from this plan with zero discovery calls and zero stop-condition checks.
