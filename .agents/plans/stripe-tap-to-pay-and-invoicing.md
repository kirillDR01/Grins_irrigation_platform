# Feature: Stripe Card Payments via Payment Links over SMS (Architecture C)

**Status:** PLAN ONLY — no code changes. This is the executable, complete spec.

> The following plan should be complete, but it's important that you validate documentation and codebase patterns and task sanity before you start implementing. Pay special attention to naming of existing utils, types, and models. Import from the right files etc.

---

## Architectural journey (so this rewrite makes sense to future readers)

This is the third revision of this plan. Earlier revisions explored two paths that were ultimately rejected:

- **Architecture A — In-app Tap-to-Pay via the Stripe Terminal JavaScript SDK.** Discarded after we discovered Stripe's JS SDK does not support Tap-to-Pay or Bluetooth readers at all. The existing `PaymentCollector.tsx` code that *appears* to do this is non-functional — `discoverReaders({ method: 'tap_to_pay' })` is suppressed with `@ts-expect-error` because the SDK doesn't accept that parameter.
- **Architecture B — Stripe Dashboard mobile app + webhook reconciliation.** Workable but added a two-app workflow for techs and significant operational overhead (description-regex matching, customer-fallback, unmatched-charges admin queue, training).

**Architecture C** chooses simplicity: Stripe **Payment Links** generated server-side per invoice, delivered to the customer by SMS, paid on the customer's own phone with Apple Pay / Google Pay / card / ACH. **Reconciliation is deterministic** because we set `metadata.invoice_id` on every Payment Link. No M2 hardware. No Stripe Dashboard app. No description-regex fuzzy matching.

The Stripe Reader M2 the user owns is unused by this architecture and can be shelved or sold.

---

## Feature Description

When the field tech / admin is at (or has just completed) an appointment, they collect payment via one of two paths from inside the Appointment Modal:

1. **"Send Payment Link"** — primary CTA. The Grin's invoice already has a Stripe Payment Link auto-created at invoice creation time. Tapping the button SMS-es the link to the customer's phone (with email fallback). The customer taps the link and pays on their own phone via Apple Pay, Google Pay, card, or ACH on a Stripe-hosted page. Within seconds, our webhook handler reads `metadata.invoice_id` from `payment_intent.succeeded` and marks the invoice paid.
2. **"Record Other Payment"** — manual record of cash, check, Venmo, or Zelle for non-card payments (already working today; minor reference-prefix tweak only).

Either path produces (or updates) an **Invoice** that lands in the **Invoices tab** with the correct status, payment method, amount, Stripe charge ID, and audit trail. Refunds and disputes initiated from the Stripe Dashboard reconcile back via the same webhook pipeline.

Overdue-reminder SMS already exists in the codebase; this plan extends those messages to **automatically include the Payment Link**, turning every reminder into a one-tap path-to-payment.

## User Story

As an **admin or field technician** using the Grin's Irrigation web app on my phone,
I want to **send the customer a Stripe Payment Link via SMS in one tap**,
so that **the customer can pay in seconds with Apple Pay / Google Pay / their card on their own phone, the corresponding invoice is automatically marked paid in the Invoices tab, the customer gets an automatic Stripe receipt, and I never have to handle a card or use a separate app.**

## Problem Statement

Today the platform can record card payments only after the fact (manual entry of `pi_*` references), and there is no automated, customer-facing path for collecting card payments at all. The existing in-app Tap-to-Pay flow in `PaymentCollector.tsx` is broken (uses an unsupported SDK parameter). Field staff cannot:

- Take a card payment in a way that updates Grin's automatically.
- Collect remote payments at all (no estimate-then-pay-from-home flow).
- Re-send a payment link to a customer who didn't pay the first time.

Concretely:

1. The existing `PaymentCollector.tsx` Tap-to-Pay flow is non-functional dead code (lines ~71–360, anchored on `discoverReaders({ method: 'tap_to_pay' })` with a `@ts-expect-error` suppressing the SDK rejection).
2. The webhook handler does not subscribe to `payment_intent.*` or `charge.*` events.
3. `Customer.stripe_customer_id` is populated for some customers but not all; receipts will not auto-send for unlinked customers.
4. Overdue reminder SMS sends today but contains no payment path.

## Solution Statement

Five coordinated workstreams:

1. **Stripe account & ops setup** — register new webhook event subscriptions, configure receipt branding/sender domain, ensure tipping is disabled and tax is not collected (both already-decided non-goals).
2. **Customer linkage hardening** — make sure every Grin's customer has a `stripe_customer_id` (idempotent backfill + auto-create on customer create/update). Without this, receipts won't auto-send.
3. **Payment Link service + auto-creation hook** — new `StripePaymentLinkService` wrapping `stripe.PaymentLink.create({...})`. Hooks into `InvoiceService.create_invoice` to auto-create the link at the same moment the invoice is created, and into `InvoiceService.update_invoice` to regenerate the link if line items or total change.
4. **Webhook hardening + frontend rewire** — `payment_intent.succeeded` handler matches by `metadata.invoice_id` (deterministic, no fuzzy match). `PaymentCollector.tsx` rewritten with a primary "Send Payment Link" button. Invoice detail page also gets a "Send / Resend Link" action. `InvoiceList.tsx` channel pill renders "Payment Link" for these.
5. **Overdue reminder enhancement + docs** — overdue/late-payment reminder SMS templates are updated to include the Payment Link automatically. Tech 1-pager + runbook.

## Feature Metadata

- **Feature Type:** New capability replacing dead code; substantial enhancement to invoice flow.
- **Estimated Complexity:** **Medium** (smaller than Architecture B by roughly 30%).
- **Estimated Effort:** ~7–10 days of focused work for the full set; B1-style "ship now without code" is not applicable here — this requires real backend/frontend changes.
- **Primary Systems Affected:**
  - Backend: new `services/stripe_payment_link_service.py`, modified `services/invoice_service.py` (auto-create + regenerate hooks), `api/v1/webhooks.py` (new event handlers), `models/invoice.py` (new columns + Alembic migration), `models/enums.py` (REFUNDED, DISPUTED), `services/customer_service.py` (Stripe customer get-or-create), reminder service (link injection).
  - Frontend: `features/schedule/components/PaymentCollector.tsx` (major rewrite — delete broken Tap-to-Pay, replace with Send Link), `features/schedule/components/AppointmentModal/AppointmentModal.tsx` (paid pill + link-status display), `features/invoices/components/PaymentDialog.tsx` (small reference-prefix tweak), `features/invoices/pages/InvoiceDetail.tsx` (Send/Resend Link button), `features/invoices/components/InvoiceList.tsx` (channel pill).
  - Database: Alembic migration adding columns to `invoices`; enum addition.
  - Ops: Stripe webhook subscription update, receipt branding configuration, optional partial-unique-index on `customers.stripe_customer_id`.
- **Dependencies:** `stripe>=8.0.0` ✅ already installed. **No new packages required.** `@stripe/terminal-js` becomes unused (kept installed but unreferenced; flag for cleanup PR).
- **External:** Stripe account in good standing with tipping disabled. Resend (email fallback) already wired per recent memory.

## Out of Scope (explicit non-goals)

- **In-app card charging via Stripe Terminal SDK** (Architecture A) — rejected; SDK doesn't support it.
- **Stripe Dashboard mobile app workflow + webhook reconciliation** (Architecture B) — rejected as unnecessarily complex for this use case.
- **Stripe Reader M2 / S700 / WisePOS E hardware integration** — not used.
- **Native iOS / Android / React Native / Capacitor wrapper** — not built.
- **Tipping** — disabled at Stripe account level; no tip handling in code.
- **Sales tax** — not collected or remitted in this feature; invoice totals are charged as-is. If tax becomes in-scope it is a separate plan.
- **Subscription / recurring billing** — handled by existing service-agreement / subscription flow; this feature explicitly does not extend it. Webhook short-circuits subscription-related PaymentIntents (CG-7).
- **Custom Grin's-branded receipts** — Stripe sends receipts automatically; not double-sent.
- **QR code on invoice PDF** — defer to v2 unless explicitly requested.
- **Removing the `services/stripe_terminal.py` and `api/v1/stripe_terminal.py` modules.** Kept in place (deprecated) for a possible future Capacitor wrapper. Full removal is a separate cleanup PR.
- **Multi-invoice charge splitting** — not relevant here; each invoice gets its own link, customer pays each separately.

---

## DECISIONS (all locked)

> No open decisions remain. All design questions surfaced during brainstorming are resolved below.

### Previously locked
- **Tipping** — disabled at Stripe account level; no tip handling in code.
- **Sales tax** — not handled in this feature; invoice totals are charged as-is.

### Locked from the Architecture C brainstorm

- **D1: Auto-create Payment Link on invoice creation** (not lazy on first send). Cheap, deterministic, link exists when needed. Best-effort: if Stripe is down, invoice still saves; link gets created on first `send-link` attempt.
- **D2: `restrictions.completed_sessions.limit = 1`** — once paid, the link is auto-deactivated. No accidental double-pays.
- **D3: Regenerate link if invoice line items or total change.** Hook into `InvoiceService.update_invoice` — if the relevant fields changed, deactivate the existing Payment Link via Stripe API and create a fresh one. Persist the new ID/URL on the invoice.
- **D4: Short SMS template, trust the link.** `"Hi {first_name}, your invoice from Grin's Irrigation for ${amount} is ready: {link}"`. No invoice number, no job description — branding shows on the Stripe page.
- **D5: Auto-include link in overdue reminder SMS.** Existing reminder lifecycle adds the (still-active) Payment Link to every reminder. Free conversion lift.
- **D6: Delivery preference: SMS preferred → Email fallback → "no contact methods" warning.** The Send Link endpoint tries SMS first; if `customer.phone` is null or SMS provider returns hard failure, falls back to Resend email. If neither available, returns a structured error and the UI shows a warning.
- **D7: Manual + webhook race covered by existing idempotency.** No new code needed; the webhook handler already no-ops if invoice is already PAID.
- **D8: Show link as plain text + Copy button in modal.** Defensive UX for techs who want to read the link aloud or paste it into a different app. Low effort.
- **D9: QR code on invoice PDF — defer to v2.** Not blocking.
- **D10: Skip the existing customer portal as a redirect layer for invoices.** Use the Stripe-hosted Payment Link URL directly. Stripe's UX is good; an extra layer adds latency and breakage points.
- **D11: "Send Payment Link" button on both the Appointment Modal AND the Invoice Detail page.** Same backend endpoint. Office admin can resend any invoice's link without opening the appointment modal.
- **D12: Lead-only appointments** — block card-payment flow at the UI level; require Lead → Customer conversion first. Backend safety net: Send Link endpoint refuses if invoice's customer is null/lead-only. (Resolves the previously-open CG-3.)
- **D13: Discount / on-the-fly price adjustment** — admin edits the invoice in Grin's; the regenerate-link hook (D3) auto-creates a fresh Payment Link with the new amount; the next send uses the new link. (Resolves the previously-open CG-4.)
- **D14: Tech Stripe role permissions** — moot under Architecture C; techs do not access the Stripe Dashboard for charge entry. (Resolves the previously-open CG-17.)

---

## MANDATORY PROJECT STANDARDS (from `.kiro/steering/`)

These are non-negotiable. Every task in this plan must comply. Audited 2026-04-28 against `.kiro/steering/{code-standards,api-patterns,frontend-patterns,frontend-testing,spec-testing-standards,spec-quality-gates,structure,tech,agent-browser,e2e-testing-skill,vertical-slice-setup-guide,parallel-execution,auto-devlog,devlog-rules}.md`.

### S1 — Three-tier testing (mandatory)
| Tier | Directory | Marker | Deps |
|------|-----------|--------|------|
| Unit | `src/grins_platform/tests/unit/` | `@pytest.mark.unit` | All mocked |
| Functional | `src/grins_platform/tests/functional/` | `@pytest.mark.functional` | Real DB |
| Integration | `src/grins_platform/tests/integration/` | `@pytest.mark.integration` | Full system |

Property-based tests (Hypothesis) **required** for business logic with invariants — for our plan: the `_build_line_items` Decimal-to-cents conversion (idempotent, sum-preserving), the matcher logic (idempotency under replay), and amount-paid arithmetic. Fixture file `conftest.py` per directory.

Test naming:
- Unit: `test_{method}_with_{condition}_returns_{expected}`
- Functional: `test_{workflow}_as_user_would_experience`
- Integration: `test_{feature}_works_with_existing_{component}`

Every new file in this plan must produce tests in **all three tiers** plus a Hypothesis test where applicable.

### S2 — Coverage targets (mandatory)
| Layer | Target |
|-------|--------|
| Backend services | 90%+ |
| Frontend components | 80%+ |
| Hooks | 85%+ |
| Utils | 90%+ |

Acceptance Criteria below adds these as explicit gates. CI command: `uv run pytest --cov=src/grins_platform --cov-fail-under=90` for service modules; `npm run test:coverage` for frontend.

### S3 — Structured logging (mandatory)
- Event-naming pattern: `{domain}.{component}.{action}_{state}`
- Services: `class FooService(LoggerMixin)` with `DOMAIN = "payment"`. Use `self.log_started("op", **ctx)`, `self.log_completed`, `self.log_rejected`, `self.log_failed`.
- Utility functions: `logger = get_logger(__name__)` then `DomainLogger.{api_event,validation_event,...}(logger, "op", "started", **ctx)`.
- API endpoints (per `api-patterns.md`): **must** call `set_request_id()` at start and `clear_request_id()` in `finally`. Inside the handler, use `DomainLogger.api_event(logger, "op", "started"|"completed"|"failed", request_id=request_id, **ctx, status_code=...)`.
- Never log: passwords, tokens, full Stripe customer/charge IDs in plaintext logs at INFO level (mask middle chars), full email/phone (use last-4 or hash for correlation).
- Log levels: DEBUG=internals, INFO=business ops, WARNING=recoverable, ERROR=failures, CRITICAL=system.

### S4 — API endpoint template (mandatory; per `api-patterns.md`)

Every new endpoint must follow:

```python
@router.post("/path", response_model=Resp, status_code=status.HTTP_201_CREATED)
async def handler(
    request: Req,
    _current_user: CurrentActiveUser,
    service: Annotated[Svc, Depends(get_svc)],
) -> Resp:
    request_id = set_request_id()
    DomainLogger.api_event(logger, "handler", "started", request_id=request_id, **safe_ctx)
    try:
        DomainLogger.validation_event(logger, "handler_request", "started", request_id=request_id)
        # validation
        DomainLogger.validation_event(logger, "handler_request", "validated", request_id=request_id)

        result = await service.do_thing(request)
        DomainLogger.api_event(logger, "handler", "completed", request_id=request_id, status_code=201)
        return Resp(...)
    except ValidationError as e:
        DomainLogger.api_event(logger, "handler", "failed", request_id=request_id, error=str(e), status_code=400)
        raise HTTPException(status_code=400, detail=str(e)) from e
    except FooError as e:
        DomainLogger.api_event(logger, "handler", "failed", request_id=request_id, error=str(e), status_code=502)
        raise HTTPException(status_code=502, detail=...) from e
    except Exception as e:
        DomainLogger.api_event(logger, "handler", "failed", request_id=request_id, error=str(e), status_code=500)
        raise HTTPException(status_code=500, detail="Internal server error") from e
    finally:
        clear_request_id()
```

API endpoint tests must cover: 201/200/204 success path, 400 validation, 404 not found, 5xx server error.

### S5 — Frontend Vertical Slice Architecture (mandatory)
- `core/` = foundation (api/client.ts, providers, router). Used by everything.
- `shared/` = cross-feature utilities (3+ features). Move here when 3rd consumer arrives.
- `features/{name}/` = self-contained slice with `components/`, `hooks/`, `api/`, `types/`, `index.ts`.
- **Hard rule: features never import from each other.** Per `frontend-patterns.md:10` and `structure.md:32`.
- This **invalidates F14 of the original plan.** See **F14 (revised)** below.

### S6 — Frontend `data-testid` conventions (mandatory)
| Element | Convention |
|---------|------------|
| Pages | `{feature}-page` |
| Tables | `{feature}-table` |
| Rows | `{feature}-row` |
| Forms | `{feature}-form` |
| Buttons | `{action}-{feature}-btn` |
| Nav | `nav-{feature}` |
| Status | `status-{value}` |

Apply to every new/modified component:
- "Send Payment Link" button → `data-testid="send-payment-link-btn"`
- "Resend Payment Link" button → `data-testid="resend-payment-link-btn"`
- Payment instructions card container → `data-testid="payment-collector"` (already exists; keep)
- Channel pill in `InvoiceList` row → `data-testid="status-payment-link"` / `status-stripe-legacy` / `status-cash` etc.
- `PaidStatePill` → `data-testid="status-paid"` / `status-refunded` / `status-disputed`
- Unmatched-charges page (if Phase 4 lands) → `data-testid="unmatched-stripe-charges-page"`
- Copy-link button → `data-testid="copy-payment-link-btn"`

### S7 — Frontend test coverage (mandatory; per `frontend-testing.md`)
- Co-located `.test.tsx` next to the component file.
- Wrap with `<QueryProvider>` from `@/core/providers/QueryProvider`.
- Cover: rendering, loading state, error state, empty state, user interactions, form validation.
- Hook tests via `renderHook(...)` + `<QueryProvider>` wrapper.
- Form tests use `userEvent` (not `fireEvent`) for realistic interaction.

### S8 — Agent-Browser E2E validation (mandatory for any UI changes; per `spec-testing-standards.md` and `e2e-testing-skill.md`)
- Must produce explicit validation scripts for the new payment flow.
- Required scenarios:
  - Open invoice in appointment modal → "Send Payment Link" button visible → click → status changes to "Link sent…"
  - Invoice Detail page → "Send / Resend Payment Link" button visible → click → toast confirms.
  - Invoice list → channel pill renders correctly for `stripe:pi_*` references.
  - Mobile (375×812) and desktop (1440×900) viewports tested.
  - Loading/empty/error states screenshotted.
- Phase 6 of the plan now contains the concrete script — see Phase 6 update below.

### S9 — Quality gates (mandatory; per `tech.md` and `code-standards.md`)
All four must pass with **zero errors** before merge:
```bash
uv run ruff check --fix src/      # lint
uv run ruff format src/            # format (88-char lines)
uv run mypy src/                   # type check
uv run pyright src/                # type check (both required)
cd frontend && npm run lint         # ESLint
cd frontend && npm run typecheck    # TypeScript strict
```
Plus all three test tiers green plus the agent-browser E2E pass.

### S10 — DEVLOG entry (mandatory; per `auto-devlog.md` + `devlog-rules.md`)
After completing this feature, prepend an entry to `DEVLOG.md` immediately under `## Recent Activity`:

```markdown
## [2026-04-28 HH:MM] - FEATURE: Stripe Payment Links via SMS (Architecture C)

### What Was Accomplished
- ...

### Technical Details
- New service: services/stripe_payment_link_service.py
- New table: ... (no new tables — added 5 columns to invoices)
- Webhook handler extended: payment_intent.* + charge.* events
- ...

### Decision Rationale
- Why Architecture C over A/B (Stripe JS SDK doesn't support TTP/Bluetooth; Architecture B's two-app workflow added operational complexity)
- ...

### Challenges and Solutions
- ...

### Next Steps
- Add 5 webhook events to prod-sandbox endpoint when going to prod-sandbox
- Configure custom receipt sender domain (DNS coordination)
- Live mode keys + webhook (when going live)
```

Categories from `devlog-rules.md`: FEATURE | BUGFIX | REFACTOR | CONFIG | DOCS | TESTING | RESEARCH | PLANNING | INTEGRATION | PERFORMANCE | SECURITY | DEPLOYMENT.

### S11 — Performance targets (per `tech.md`)
- API: <200ms p95
- DB queries: <50ms p95
- Cache: <10ms p95

The new `send_payment_link` endpoint must comply. Lazy-create-link path may exceed this if it's the first call (Stripe API roundtrip ~300ms typical) — acceptable for a one-time link creation but document in the runbook.

### S12 — Parallel execution strategy (per `parallel-execution.md`)
For this plan's Phase 2:
- **2a sequential**: Alembic migration → enum addition → model column add (DB shape locked)
- **2b parallel**: `StripePaymentLinkService` | webhook handler skeleton | new exceptions class — independent units
- **2c sequential**: `_attach_payment_link` hook (depends on 2b service) → `send_payment_link` (depends on hook) → endpoint
- **2d parallel**: tests for each handler (independent)
- **2e sequential**: integration tests
Estimated savings: 40–55% vs fully sequential per `parallel-execution.md`.

### S13 — Cross-feature transactions (per `vertical-slice-setup-guide.md`)
- Feature A may **read** from Feature B's repository.
- Feature A must **never write** to Feature B's tables.
- For our plan: `AppointmentService.create_invoice_from_appointment` already uses `InvoiceRepository` (cross-feature read+write but invoice IS the cross-feature concern; this is the orchestrating-service pattern). No new violations.

### S14 — VSA file layout for new feature work
For frontend, the new payment-link concern lives entirely inside `features/invoices/` and `features/schedule/`. No new feature directory needed.

### S15 — Security (per `tech.md` and `spec-quality-gates.md`)
- Webhook endpoint already does signature verification (existing).
- Endpoint auth: `CurrentActiveUser` for `/send-link`, `AdminUser` for any admin reconciliation endpoints.
- Never log: full Stripe secret, full webhook secret, full payment_intent ID at INFO level (mask: `pi_3OX***xxxx`).
- PII masking: phone → last 4 (`***-***-3312`), email → first char + domain (`k***@gmail.com`) at INFO log level.

---

## VERIFIED CODE-LEVEL FINDINGS (pinned — no further investigation needed)

These are confirmed answers to every "verify before implementing" item that previously made the plan less than fully executable. Each was validated by reading the actual source on 2026-04-28.

### F1 — `create_invoice_from_appointment` is NOT idempotent today
- Location: `src/grins_platform/services/appointment_service.py:2080–2161`.
- Behavior today: every call creates a brand-new `Invoice` row with a fresh sequence-numbered `invoice_number`. Calling it twice on the same appointment creates **two** invoices.
- Its **docstring lies** ("Generates a Stripe payment link and sends via SMS + email") — the actual code only writes the Invoice row. No Stripe call, no SMS, no email. This is exactly the gap we're filling.
- **Required change in this plan (Task 2.4a):** wrap with an idempotency check using the *already-existing* helper `AppointmentService._find_invoice_for_job(job_id)` at `services/appointment_service.py:2719` — if it returns an Invoice, return it; only create when none exists. Also fix the lying docstring.

### F2 — Two coexisting line-item JSONB shapes
- The Pydantic schema `InvoiceLineItem` at `schemas/invoice.py:25–67` defines `{description: str, quantity: Decimal, unit_price: Decimal, total: Decimal}`.
- But the *internal* path in `create_invoice_from_appointment:2136–2141` writes the simpler legacy shape `[{"description": str, "amount": str}]` (yes, `amount` is a stringified Decimal because of JSONB).
- **Required behavior in `_build_line_items`:** support both shapes. Detect by key presence: `total` / `unit_price` present → Pydantic shape (use `total`); else `amount` present → legacy (parse as Decimal). Raise on neither.

### F3 — `Invoice.line_items` model column shape
- `models/invoice.py:167–170`: `Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB(), nullable=True)`.
- Always treat as a list of dicts; can be `None` for invoices without explicit line items (in which case the Stripe link uses a single line item derived from `Invoice.total_amount` with description `f"Invoice {invoice.invoice_number}"`).

### F4 — `PaymentRecord` schema (input to `record_payment`)
- `schemas/invoice.py:275–302`. Three fields: `amount: Decimal (>0)`, `payment_method: PaymentMethod`, `payment_reference: str | None (max 255)`.
- The webhook handler constructs this with `amount=Decimal(amount_received)/100`, `payment_method=PaymentMethod.CREDIT_CARD`, `payment_reference=f"stripe:{intent.id}"`.

### F5 — The payment gate on appointment completion (Req 36)
- `AppointmentService.transition_status` at `services/appointment_service.py:1925–1934` raises `PaymentRequiredError` when transitioning to `COMPLETED` unless `_has_payment_or_invoice` returns True or `admin_override=True`.
- `_has_payment_or_invoice` at `:2702–2717` calls `_find_invoice_for_job` (`:2719+`) which returns the most recent `Invoice` for the job, or `None`.
- **Implication:** as long as our Phase 2 hook auto-creates an Invoice at appointment-create time and our `create_invoice_from_appointment` becomes idempotent, the existing payment gate *just works* without modification. Don't touch the gate.

### F6 — Stripe API version pin
- Code state today: `grep -rn "stripe.api_version"` across `src/grins_platform/` → zero hits. Unpinned.
- **Pinned value (locked 2026-04-28): `"2025-03-31.basil"`** — confirmed via `stripe webhook_endpoints list` that this is the version Stripe is already sending events with for the existing 3 webhook endpoints in the sandbox account. Matching what Stripe is sending eliminates event-shape drift between SDK expectations and webhook payloads.
- Set as both the default in `StripeSettings.stripe_api_version` AND as `STRIPE_API_VERSION=2025-03-31.basil` in Railway env vars (dev today; prod when going live).

### F7 — SMS interface (verified exact signature)
- **Use `SMSService.send(...)` from `services/sms_service.py:176`** (high-level wrapper). Do NOT call providers directly.
- **Exact signature** (verified at `sms_service.py:215+`):
    ```python
    async def send(
        self,
        recipient: Recipient,
        message: str,
        message_type: MessageType,
        consent_type: ConsentType = "transactional",
        campaign_id: UUID | None = None,
        job_id: UUID | None = None,
        appointment_id: UUID | None = None,
        *,
        skip_formatting: bool = False,
    ) -> dict[str, Any]:
    ```
- **`Recipient`** is a dataclass at `services/sms/recipient.py:23`. Construct via existing factory or directly with `phone`, `source_type` (e.g., `"customer"` | `"lead"` | `"adhoc"`), and the entity's id.
- **`ConsentType`** is `Literal["marketing", "transactional", "operational"]` at `services/sms/consent.py:36`. **Use `"transactional"` for payment links** (already the default).
- **`MessageType`** from `schemas/ai.py:53`. Existing values include `APPOINTMENT_REMINDER`, `PAYMENT_REMINDER`, etc. — **`PAYMENT_LINK` does NOT exist; add it as a new enum value** in Task 2.7. The lazy alternative is to reuse `PAYMENT_REMINDER` and skip the schema change, but a distinct value is cleaner for analytics.
- **Return value:** `dict[str, Any]` with keys `success: bool`, `message_id: str`, `status: str`. Check `result["success"]` to determine success/failure.
- **Exceptions raised** (per docstring at `sms_service.py:240–243`):
  - `SMSConsentDeniedError` — consent check failed (covers hard-STOP, no-consent, opt-out cases). For payment links, this is the **expected fall-through to email** path.
  - `SMSRateLimitDeniedError` — rate limit exceeded; treat as transient failure.
  - `SMSError` — provider send failure; treat as transient.
- The dev/staging allowlist guard is enforced inside `SMSService` automatically (`SMS_TEST_PHONE_ALLOWLIST`).

### F8 — Email service interface
- File: `services/email_service.py`. Resend SDK is imported and live (`import resend` at line 20; `resend.Emails.send(payload)` at line 280).
- The recipient allowlist guard `enforce_email_recipient_allowlist(to_email, provider="resend")` is called at `:260` automatically — **we don't need to add allowlist logic in our code; it's already enforced inside `_send_email`.**
- Public-from-outside method: `_send_email(...)`. Yes, the leading underscore is misleading — the codebase calls it from `notification_service.py`, `campaign_service.py`, `lead_service.py` with `# noqa: SLF001`. Follow that pattern.
- Senders: `TRANSACTIONAL_SENDER = "noreply@grinsirrigation.com"` (line 46), `COMMERCIAL_SENDER = "info@grinsirrigation.com"` (line 47). Payment-link emails are transactional → use the transactional sender.
- Templates live at `services/templates/emails/` (Jinja2). New template: `payment_link_email.html` (and `.txt` for plaintext fallback).

### F9 — Existing reminder integration points
- **Per-invoice reminder:** `InvoiceService.send_reminder(invoice_id)` at `services/invoice_service.py:705`. Increments `reminder_count` and updates `last_reminder_sent`. **Modify to inject `Invoice.stripe_payment_link_url` into the SMS body when present.**
- **Bulk overdue runner:** `NotificationService.send_invoice_reminders` at `services/notification_service.py:705`. Already iterates due/overdue invoices. **No structural change** — it calls `send_reminder` so the template fix flows through automatically.
- Lien warning template lives in the same area; same modification (inject link).

### F10 — Frontend query keys (already-built factories)
- `invoiceKeys` lives at `frontend/src/features/invoices/hooks/useInvoices.ts:6–18`. Has `all`, `lists()`, `list(params)`, `details()`, `detail(id)`, `byJob(jobId)`, `overdue(params)`, `lienDeadlines()`, `lienCandidates(params)`. **Already the right shape; just import.**
- `customerInvoiceKeys` lives at `frontend/src/features/customers/hooks/useCustomers.ts` (and exported via `frontend/src/features/customers/hooks/index.ts`).
- Cross-feature import (importing `invoiceKeys` from `features/schedule/...` code) is **already common pattern** in this codebase; no lint rule blocks it. Confirmed by `Grep` for prior cross-feature imports.

### F11 — `InvoiceCreate.amount` requirement and the $0 edge case
- Schema `InvoiceCreate` at `schemas/invoice.py:75–115` requires `amount: Decimal (≥0)` — zero is *valid*, negative is not.
- The auto-create call site at `appointment_service.py:2134` falls back to `Decimal(0)` if the job has neither `quoted_amount` nor `final_amount`.
- **Stripe constraint:** `stripe.PaymentLink.create` requires line items with `unit_amount > 0` (cents). A $0 invoice cannot have a Payment Link.
- **Required behavior:** in the create-Payment-Link hook, if `Invoice.total_amount == 0`, **skip Payment Link creation entirely** (log `payment_link.skipped_zero_amount`). Frontend hides the Send Link CTA for $0 invoices.

### F12 — Transactional bypass for `sms_opt_in` / `email_opt_in` (locked 2026-04-28)
- `Customer.sms_opt_in` and `email_opt_in` exist at `models/customer.py:96–97` (both `default=False`).
- **Decision: payment-link SMS and email are TRANSACTIONAL and bypass the marketing opt-in flags.**
- **Legal rationale:**
  - **TCPA:** transactional SMS to a number the customer provided in the course of a commercial relationship — including payment requests for services already rendered — falls outside the TCPA's "advertising or telemarketing" scope. Industry guidance (FCC + CTIA) treats these as transactional/operational.
  - **CAN-SPAM:** the Act explicitly exempts "transactional or relationship messages" — including info needed to complete a commercial transaction the recipient previously agreed to (i.e., paying for service rendered).
- **Required behavior in `send_payment_link`:**
  - SMS path: only requires `customer.phone IS NOT NULL`. Do NOT check `sms_opt_in`. Call `SMSService.send(...)` with `consent_type="transactional"` (which is the default at `services/sms_service.py:217`).
  - Email path: only requires `customer.email IS NOT NULL`. Do NOT check `email_opt_in`. Use `TRANSACTIONAL_SENDER = "noreply@grinsirrigation.com"` (`services/email_service.py:46`).
  - Both null → raise `NoContactMethodError`.
- **Hard suppressions still respected** (mandatory, not optional):
  - Hard STOP via SMS keyword is enforced inside `SMSService.send`. When consent is denied (hard-STOP, opt-out, etc.), the method **raises `SMSConsentDeniedError`** (verified at `sms_service.py:240–243`). `send_payment_link` catches this and falls through to email — see Task 2.7 body.
  - Email global suppression (Resend's bounce/complaint suppression) is enforced inside `_send_email`. If the customer's email is on the suppression list, send fails gracefully and `_send_email` returns `False`.
- **What this changes vs the prior plan revision:** the `send_payment_link` body sketch in Task 2.7 no longer includes `customer.sms_opt_in` or `customer.email_opt_in` predicates. Edge cases 32–34 are simplified accordingly.
- **What stays the same:** the high-level service handles the actual hard-STOP / suppression enforcement; we don't need to check those ourselves.

### F13 — Existing `_find_invoice_for_job` direct query
- At `services/appointment_service.py:2719+` — fetches the most-recent `Invoice` for a `job_id`. Use this for both:
  - The new idempotency check in `create_invoice_from_appointment` (F1).
  - Any "does this appointment have an invoice already?" lookups elsewhere.

### F15 — Verified import paths and query-key prefixes (all confirmed 2026-04-28)

**Backend imports** (verified by direct grep on `log_config.py`):
```python
from grins_platform.log_config import (
    LoggerMixin,           # line 214
    DomainLogger,          # line 268
    get_logger,            # line 154
    set_request_id,        # line 169
    clear_request_id,      # line 186
)
```

**Note:** `.kiro/steering/code-standards.md:8` references `from grins_platform.logging` — that is **incorrect** (no such module exists). Always use `log_config`. Treat the steering doc as a typo for this one line.

**Frontend query-key prefixes** (verified by grep):
- `appointmentKeys.all = ['appointments'] as const` (`useAppointments.ts:11`)
- `customerInvoiceKeys.all = ['customer-invoices'] as const` (`useCustomers.ts:31`)
- `invoiceKeys.all = ['invoices'] as const` (`useInvoices.ts:7`)

For partial-key invalidation from `features/schedule/` (per F14 cross-feature import ban), use the literal strings:
```ts
queryClient.invalidateQueries({ queryKey: ['invoices'] });
queryClient.invalidateQueries({ queryKey: ['customer-invoices'] });
queryClient.invalidateQueries({ queryKey: ['appointments'] });
```

**Pytest markers:** the codebase uses `@pytest.mark.unit`, `.functional`, `.integration` (verified in `tests/unit/test_accounting_service.py:91`). `pyproject.toml [tool.pytest.ini_options]` does NOT register them explicitly, but `--strict-markers` is also not configured, so they work without warning. No registration needed for new tests; just use the markers.

**Test directories that exist:**
- `src/grins_platform/tests/unit/` — co-located with `__init__.py`, has many existing tests
- `src/grins_platform/tests/functional/` — exists
- `src/grins_platform/tests/integration/` — exists
- `src/grins_platform/tests/conftest.py` — shared fixtures
- Plus a flat layout at `src/grins_platform/tests/test_*.py` for older tests (mixed convention)

For new tests, place in the per-tier subdirectories with the appropriate markers.

### F14 (revised per S5) — Frontend cross-feature imports are FORBIDDEN
- Per `frontend-patterns.md:10` and `structure.md:32`: features import from `core/` and `shared/` only — never from each other.
- The original plan suggested importing `invoiceKeys` from `@/features/invoices/...` into `useAppointmentMutations.ts` (in `features/schedule/`). **This is not allowed.**
- **Correct pattern (TanStack Query partial-key invalidation):**
    ```ts
    // In features/schedule/hooks/useAppointmentMutations.ts
    onSuccess: () => {
      // Use the literal prefix string — same effect as invalidating invoiceKeys.all
      // without crossing the feature boundary.
      queryClient.invalidateQueries({ queryKey: ['invoices'] });
      queryClient.invalidateQueries({ queryKey: ['customer-invoices'] });
      queryClient.invalidateQueries({ queryKey: ['appointments'] });
    },
    ```
- TanStack Query v5 invalidates any query whose key **starts with** the given prefix. So `['invoices']` matches `invoiceKeys.lists()`, `invoiceKeys.detail(id)`, `invoiceKeys.byJob(...)`, etc. — equivalent functional outcome, no cross-feature import.
- **Only acceptable cross-feature reuse:** lift the relevant query-key factory to `frontend/src/shared/queryKeys.ts` if **3+ features** need it (per `vertical-slice-setup-guide.md:65` "extract to shared/ at 3rd usage"). For now, two features (schedule + invoices), so partial-key invalidation is the right move.

---

## CONTEXT REFERENCES

### Backend files — IMPORTANT: READ THESE BEFORE IMPLEMENTING

**Webhook layer:**
- `src/grins_platform/api/v1/webhooks.py` (1000+ lines, especially lines 60–71 for `HANDLED_EVENT_TYPES` and lines 960–1020 for the Stripe handler). Currently handles: `checkout.session.completed`, `invoice.paid`, `invoice.payment_failed`, `invoice.upcoming`, `customer.subscription.updated`, `customer.subscription.deleted`. **Must add:** `payment_intent.succeeded`, `payment_intent.payment_failed`, `payment_intent.canceled`, `charge.refunded`, `charge.dispute.created`.
- `src/grins_platform/models/stripe_webhook_event.py` (71 lines) — `stripe_webhook_events` table providing idempotency. Use as-is.
- `src/grins_platform/repositories/stripe_webhook_event_repository.py` — `get_by_stripe_event_id`, `create_event_record`, `mark_processed`.

**Stripe configuration:**
- `src/grins_platform/services/stripe_config.py` (lines 13–48) — `StripeSettings` Pydantic model. **Add:** `stripe_api_version` field for explicit pinning.

**Customer ↔ Stripe linkage:**
- `src/grins_platform/models/customer.py:111` — `stripe_customer_id: Mapped[Optional[str]]` already exists. No migration needed; just consistent population.
- `src/grins_platform/services/customer_service.py` (lines ~1445–1610) — already references Stripe. **Add:** `get_or_create_stripe_customer(customer_id) -> str` (idempotent).
- `src/grins_platform/models/service_agreement.py:88` — separate `stripe_customer_id` exists here too. Audit for divergence (one-shot SQL query); add invariant in `ServiceAgreementService` that this matches `customers.stripe_customer_id` for the same Grin's customer.

**Invoice domain:**
- `src/grins_platform/models/invoice.py` (221 lines) — `Invoice` model. Key fields: `payment_method`, `payment_reference`, `paid_at`, `paid_amount`, `status`, `total_amount` (Decimal), `invoice_number` (unique), `job_id`, `customer_id`, `line_items` (JSONB array), `notes`. **Must add:** `stripe_payment_link_id`, `stripe_payment_link_url`, `stripe_payment_link_active` (bool, default true), `payment_link_sent_at` (datetime, nullable), `payment_link_sent_count` (int, default 0).
- `src/grins_platform/models/enums.py` (lines 200–236) — `InvoiceStatus` and `PaymentMethod`. **Add:** `InvoiceStatus.REFUNDED` and `InvoiceStatus.DISPUTED`.
- `src/grins_platform/services/invoice_service.py` (500+ lines) — `record_payment(invoice_id, PaymentRecord)` is the canonical write path. Webhook calls into this for consistent audit/logging. **Hook into:** `create_invoice` (auto-create Payment Link after invoice persists) and `update_invoice` (regenerate link if line items or total changed).
- `src/grins_platform/repositories/invoice_repository.py` — standard async-SQLAlchemy repo. **Add:** `get_by_payment_link_id`, `get_by_payment_intent_reference`.
- `src/grins_platform/api/v1/invoices.py` — Invoice REST endpoints. DI pattern in `get_invoice_service()`.

**Appointment / Job linkage:**
- `src/grins_platform/services/appointment_service.py` (line 1763 onward) — `collect_payment` for manual flow. Webhook does NOT call this (writes via `InvoiceService.record_payment`).
- `src/grins_platform/models/job.py:152` — `payment_collected_on_site: bool` flag. Webhook handler sets this when marking invoice paid.
- `src/grins_platform/api/v1/appointments.py` (lines 1271–1318) — `POST /appointments/{id}/collect-payment` (manual flow, unchanged). Lines 1326+ — `POST /appointments/{id}/create-invoice` (must be idempotent for D1's auto-create).

**Existing reminder lifecycle:**
- `src/grins_platform/services/invoice_service.py` — `send_reminder(invoice_id)` and `send_lien_warning(invoice_id)`. **Modify** to inject `Invoice.stripe_payment_link_url` into the SMS body (D5).
- Reminder SMS template files (search `templates/` and `services/sms/`) — extend to include the link.
- Existing CallRail SMS integration is the send mechanism. Email fallback is via Resend (per memory; live in `_send_email`).

**Service-agreement skip logic:**
- `src/grins_platform/tests/unit/test_payment_warning_service_agreement.py` documents the rule: jobs with active `service_agreement_id` should not show payment CTAs. **Verify** the appointment modal already enforces this; if not, add it.

**Existing Stripe-Terminal code (deprecated, kept):**
- `src/grins_platform/services/stripe_terminal.py` (131 lines) — mark deprecated with module-level docstring; do not delete.
- `src/grins_platform/api/v1/stripe_terminal.py` (177 lines) — same.
- `frontend/src/features/schedule/api/stripeTerminalApi.ts` (49 lines) — same.

**Tests to read before touching code:**
- `src/grins_platform/tests/unit/test_stripe_webhook.py` — pattern for mocking `stripe.Webhook.construct_event`, asserting idempotency.
- `src/grins_platform/tests/unit/test_invoice_service.py`, `tests/integration/test_invoice_integration.py`.
- `src/grins_platform/tests/unit/test_subscription_management.py` — Stripe customer creation/lookup pattern.
- `src/grins_platform/tests/unit/test_payment_warning_service_agreement.py`.

### Frontend files — IMPORTANT: READ THESE BEFORE IMPLEMENTING

- `frontend/src/features/schedule/components/PaymentCollector.tsx` (447 lines) — **MAJOR REWRITE.** Delete the entire `tap_to_pay` `path` branch (lines ~71–360: `handleTapToPay`, `handleSendReceipt`, `tapStep`, `tapError`, all related state). Replace with a clean two-button layout: "Send Payment Link" (primary, purple Stripe button) + "Record Other Payment" (secondary, manual flow unchanged).
- `frontend/src/features/schedule/api/stripeTerminalApi.ts` — keep file but mark deprecated with header comment. Stop importing it from `PaymentCollector.tsx`.
- `frontend/src/features/schedule/components/AppointmentModal/PaymentSheetWrapper.tsx` — no change to wrapper.
- `frontend/src/features/schedule/components/AppointmentModal/AppointmentModal.tsx` (lines 117–123, 515–533, 651–666) — modal state and `openSheetExclusive('payment')` flow stays. Add a "Paid — $X via Payment Link on {date}" pill when invoice is `PAID` (or REFUNDED / DISPUTED for those states). Show "Link sent · waiting for payment" indicator when link has been sent but invoice still SENT/OVERDUE. Hide CTA entirely for service-agreement-covered jobs.
- `frontend/src/features/schedule/hooks/useAppointmentMutations.ts` (lines 198–210) — `useCollectPayment` invalidations need to include `invoiceKeys.all` and `customerInvoiceKeys.all`. Add a new `useSendPaymentLink` mutation.
- `frontend/src/features/invoices/components/PaymentDialog.tsx` (289 lines) — manual payment recording. **Tweak:** when user pastes a bare `pi_*` reference, auto-prepend `stripe:`. Don't double-prepend.
- `frontend/src/features/invoices/components/InvoiceList.tsx` — add a "Channel" pill column derived from `payment_reference` prefix:
  - `stripe:pi_*` (or `stripe_link:pi_*` if disambiguated) → "Payment Link" pill (purple).
  - Legacy `payment_method == 'stripe'` rows → "Stripe (legacy)" pill (neutral grey). No data migration.
  - Bare reference + non-stripe method → method label (Cash/Check/etc.).
- `frontend/src/features/invoices/types/index.ts` — add `'refunded'`, `'disputed'` to `InvoiceStatus`. Add new fields to `Invoice` type matching backend additions.
- `frontend/src/features/invoices/api/invoiceApi.ts` — add `sendPaymentLink(invoiceId)` method.
- `frontend/src/features/invoices/hooks/useInvoiceMutations.ts` — add `useSendPaymentLink` mutation with proper cache invalidation.
- `frontend/src/features/invoices/pages/InvoiceDetail.tsx` (or equivalent) — add "Send Payment Link" button (and "Resend" if already sent). Display sent count + last-sent timestamp.
- `frontend/src/core/api/client.ts` — no change.

### Stripe documentation — READ THESE BEFORE IMPLEMENTING

- **Payment Links API:** https://docs.stripe.com/api/payment_links/payment_links
  - `stripe.PaymentLink.create(...)`, `update(...)` (for deactivation), restrictions, line items.
- **Payment Link metadata + reconciliation:** https://docs.stripe.com/payment-links/customize#metadata
- **Webhooks intro & best practices:** https://docs.stripe.com/webhooks
- **Event types reference:** https://docs.stripe.com/api/events/types
  - `payment_intent.succeeded`, `payment_intent.payment_failed`, `payment_intent.canceled`, `charge.refunded`, `charge.dispute.created`.
- **Receipt configuration:** https://docs.stripe.com/receipts (Stripe sends receipts automatically when `customer.email` is set).
- **API versioning:** https://docs.stripe.com/api/versioning (pin `stripe.api_version`).
- **Disputes lifecycle:** https://docs.stripe.com/disputes/responding.
- **Refunds API:** https://docs.stripe.com/refunds.

### Patterns to follow (mirror these exactly)

**Backend service pattern (mirror `services/stripe_terminal.py`):**

```python
from grins_platform.log_config import LoggerMixin, get_logger
logger = get_logger(__name__)

class StripePaymentLinkError(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)

class StripePaymentLinkService(LoggerMixin):
    DOMAIN = "payment"
    def __init__(self, stripe_settings: StripeSettings) -> None:
        super().__init__()
        self.stripe_settings = stripe_settings
    def create_for_invoice(self, invoice: Invoice, customer: Customer) -> tuple[str, str]:
        self.log_started("create_for_invoice", invoice_id=str(invoice.id))
        try:
            link = stripe.PaymentLink.create(
                line_items=self._build_line_items(invoice),
                metadata={"invoice_id": str(invoice.id), "customer_id": str(customer.id)},
                restrictions={"completed_sessions": {"limit": 1}},
                customer_creation="if_required",
                after_completion={"type": "hosted_confirmation"},
            )
            self.log_completed("create_for_invoice", link_id=link.id)
            return link.id, link.url
        except stripe.StripeError as e:
            self.log_failed("create_for_invoice", error=e)
            raise StripePaymentLinkError(str(e)) from e
```

**Webhook event handler pattern (mirror existing `_handle_invoice_paid` in `webhooks.py`):**

- Verify event type in `HANDLED_EVENT_TYPES`.
- Check idempotency via `StripeWebhookEventRepository.get_by_stripe_event_id(event.id)` *before* doing any work.
- After processing, call `mark_processed(event.id)`.
- On failure, set `processing_status = "failed"` with `error_message`, **return 200 anyway** (Stripe should not retry our bugs forever — log and alert).
- Defensive double-layer idempotency: even if the webhook event is "new," check the *invoice's* current state before mutating.

**FastAPI endpoint pattern (mirror `api/v1/invoices.py`):**

```python
@router.post("/{invoice_id}/send-link", response_model=SendLinkResponse)
async def send_payment_link(
    invoice_id: UUID,
    _current_user: CurrentActiveUser,
    service: Annotated[InvoiceService, Depends(get_invoice_service)],
) -> SendLinkResponse:
    try:
        return await service.send_payment_link(invoice_id)
    except InvoiceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except NoContactMethodError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
```

**Frontend mutation pattern (mirror `useInvoiceMutations.ts`):**

```ts
return useMutation({
  mutationFn: (invoiceId: string) => invoiceApi.sendPaymentLink(invoiceId),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: invoiceKeys.all });
    queryClient.invalidateQueries({ queryKey: customerInvoiceKeys.all });
    queryClient.invalidateQueries({ queryKey: appointmentKeys.all });
  },
});
```

**Memory-aware safety guards (DO NOT bypass):**
- Per memory `feedback_email_test_inbox.md`: any email send in dev/staging must enforce a code-level allowlist. Only `kirillrakitinsecond@gmail.com` may receive real email. The Resend-backed email-fallback path inherits this.
- Per memory `feedback_sms_test_number.md`: same for SMS — only `+19527373312` in dev. The Send Link SMS path inherits this.
- Per memory `project_dev_stripe_price_mismatch.md` (Apr 15 incident): when running webhooks against dev Stripe, double-check `STRIPE_SECRET_KEY` is the test key.
- Per memory `project_estimate_email_portal_wired.md`: Resend is live in `_send_email`. Email fallback for Payment Link SMS reuses this path.

---

## IMPLEMENTATION PLAN

### Phase 0 — Stripe account & ops setup (no code; ~0.5 day)

- **Confirm Stripe account state:** good standing, US merchant, MCC code OK, test + live keys configured. Per memory, double-check dev `.env` has the test key.
- **Stripe webhook subscription:** in Stripe Dashboard → Developers → Webhooks → Grin's endpoint, add events:
  - `payment_intent.succeeded`, `payment_intent.payment_failed`, `payment_intent.canceled`, `charge.refunded`, `charge.dispute.created`.
  - Keep existing 6 events as-is.
  - Confirm signing secret matches `STRIPE_WEBHOOK_SECRET` in each env.
- **Receipt configuration:** Stripe Dashboard → Settings → Branding (logo, color, business name, support email/phone). Settings → Customer emails: confirm "Successful payments" toggle is ON.
- **Custom receipt sender domain:** Stripe Dashboard → Settings → Emails → Public details. Set sender to `payments@grins-irrigation.com` (or chosen domain). Add DKIM/SPF DNS records (Stripe provides values). Coordinate with whoever runs DNS.
- **Tipping disabled:** Stripe Dashboard → Settings → Tipping. Confirm OFF. (Already a locked decision.)
- **Validate end-to-end against test mode** (after Phase 2 ships): create a test invoice → auto-create Payment Link → send to a test phone → pay with Stripe test card → confirm webhook → confirm invoice flips to PAID + receipt arrives.

### Phase 1 — Customer linkage hardening (~1 day)

- **Add partial unique index on `customers.stripe_customer_id`** (Alembic migration): `CREATE UNIQUE INDEX ... WHERE stripe_customer_id IS NOT NULL`. If duplicates exist, dedupe first.
- **Implement `CustomerService.get_or_create_stripe_customer(customer_id) -> str`** (idempotent). Call `stripe.Customer.create(name, email, phone, metadata={"grins_customer_id": str(customer_id)})` only if not already linked.
- **Backfill script** `scripts/backfill_stripe_customers.py` — paginate `customers`, idempotent, rate-limit-aware.
- **Auto-create on customer create/update:** post-write hook in `CustomerService.create_customer` and `update_customer` (best-effort, log Stripe errors, don't fail the user-facing operation).
- **CG-18 audit:** one-shot query verifying `customer.stripe_customer_id == service_agreement.stripe_customer_id` for shared customers. Add invariant in `ServiceAgreementService.create_or_update`.

### Phase 2 — Backend Payment Link service + webhook + DB columns (~3 days)

- **Pin Stripe API version:** add `stripe_api_version: str = "2024-11-20.acacia"` (or current latest) to `StripeSettings`. Set `stripe.api_version` everywhere `stripe.api_key` is set.
- **Add InvoiceStatus enum values:** `REFUNDED`, `DISPUTED` (backend + frontend matching).
- **Alembic migration on `invoices` table:** add columns `stripe_payment_link_id` (string, nullable), `stripe_payment_link_url` (text, nullable), `stripe_payment_link_active` (boolean, default true, server_default true), `payment_link_sent_at` (datetime UTC, nullable), `payment_link_sent_count` (int, default 0, server_default 0). Index on `stripe_payment_link_id` (partial, where not null).
- **Create `services/stripe_payment_link_service.py`:**
  - `create_for_invoice(invoice, customer) -> (link_id, link_url)` — wraps `stripe.PaymentLink.create({...})` with line items derived from `invoice.line_items`, `metadata={invoice_id, customer_id}`, `restrictions.completed_sessions.limit=1`, `customer={stripe_customer_id}` if available.
  - `deactivate(link_id)` — `stripe.PaymentLink.update(link_id, active=false)`.
  - `_build_line_items(invoice)` — translates Grin's JSONB line items to Stripe `price_data` inline format (no Stripe Product needed).
  - Custom `StripePaymentLinkError` class.
- **Hook into `InvoiceService.create_invoice`:**
  - After invoice persists, call `get_or_create_stripe_customer(customer_id)`, then `StripePaymentLinkService.create_for_invoice(invoice, customer)`. Persist `stripe_payment_link_id` + `stripe_payment_link_url` on the invoice.
  - **Best-effort:** wrap in try/except; on Stripe failure, log warning `payment_link.create_failed_at_invoice_creation` and continue — link gets created on first send-attempt.
- **Hook into `InvoiceService.update_invoice`:**
  - Detect if `line_items` OR `total_amount` changed.
  - If yes AND existing link is active: call `StripePaymentLinkService.deactivate(old_link_id)`, then `create_for_invoice` for the new state, persist.
  - Log structured event `payment_link.regenerated`.
- **Implement `InvoiceService.send_payment_link(invoice_id) -> SendLinkResponse`:**
  - Lazy-create link if missing (covers the best-effort failure case at creation time).
  - **D6 delivery preference:** try SMS via existing CallRail integration (with allowlist guard in dev/staging). On hard failure, fall back to Resend email. If neither contact method available, raise `NoContactMethodError`.
  - Update `payment_link_sent_at = now`, increment `payment_link_sent_count`.
  - **D12 lead-only safety net:** if `customer_id` resolves to null or a Lead-only record, raise `LeadOnlyInvoiceError`.
  - Return `SendLinkResponse{channel: 'sms' | 'email', link_url, sent_at, sent_count}`.
- **Implement endpoint `POST /api/v1/invoices/{id}/send-link`** (CurrentActiveUser auth).
- **Extend `HANDLED_EVENT_TYPES`** in `api/v1/webhooks.py` with the 5 new event types.
- **Implement `_handle_payment_intent_succeeded(event, session)`:**
  - Read `event.data.object`: `id`, `metadata`, `amount_received`, `customer`, `invoice` (Stripe Invoice ID, for short-circuit).
  - **CG-7 short-circuit:** if `event.data.object.invoice` is non-null, this PaymentIntent belongs to a Stripe-side Invoice (subscription renewal) — already handled by `_handle_invoice_paid`. Log `payment_intent.subscription_intent_skipped` and return.
  - **Match by metadata.invoice_id** — lookup invoice. If not found, log `payment_intent.unmatched_metadata` (rare; means we created a Payment Link with a now-deleted invoice).
  - **CG-8 cancelled invoice:** if invoice status is CANCELLED, refuse to mark paid. Log WARNING `payment_intent.cancelled_invoice_charged` (admin must refund manually in Stripe).
  - **Idempotency:** if invoice already PAID, no-op. Log `payment_intent.invoice_already_paid`.
  - **Otherwise:** call `InvoiceService.record_payment(invoice_id, PaymentRecord(amount=Decimal(amount_received)/100, payment_method=PaymentMethod.CREDIT_CARD, payment_reference=f"stripe:{intent.id}"))`. Set `Job.payment_collected_on_site = True`. Set `Invoice.stripe_payment_link_active = false` (Stripe deactivates the link automatically with `completed_sessions.limit=1`, but mirror the state).
  - **Currency check:** if `currency != "usd"`, log error and don't mark paid (out of scope).
- **Implement `_handle_payment_intent_payment_failed`:** structured log only. No invoice mutation.
- **Implement `_handle_payment_intent_canceled`:** log only. No-op for our flow (Payment Links don't typically cancel from the Stripe side).
- **Implement `_handle_charge_refunded`:**
  - Look up invoice by `payment_reference == f"stripe:{payment_intent_id}"`.
  - **Full refund:** set `Invoice.status = REFUNDED`, `Job.payment_collected_on_site = False`. Idempotent.
  - **Partial refund:** adjust `Invoice.paid_amount`, set status to PARTIAL with notes annotation.
- **Implement `_handle_charge_dispute_created`:**
  - Mark invoice DISPUTED, append notes with dispute reason and due-by, log WARNING. Future: enqueue admin notification.
- **Tests** (`tests/unit/test_stripe_webhook.py` + new `tests/unit/test_payment_link_service.py`):
  - Payment Link create: happy path, missing customer, Stripe error.
  - Payment Link regenerate on invoice update.
  - Send link: SMS happy, SMS fail → email fallback, no contact methods → error.
  - Webhook: metadata-match, subscription short-circuit (CG-7), cancelled invoice (CG-8), already-paid no-op, currency mismatch, refund full/partial, dispute, idempotent replay.

### Phase 3 — Frontend rewire (~2–3 days)

- **`PaymentCollector.tsx` major rewrite:**
  - Delete: `tap_to_pay` `path` branch, `handleTapToPay`, `handleSendReceipt`, `tapStep`, `tapError`, the entire instructions card from Architecture B.
  - Add: primary "Send Payment Link" button (purple, prominent) that calls `useSendPaymentLink(invoiceId)`. After click, button transforms into status display: "✓ Link sent to {phone} · waiting for payment" with a 4s polling indicator (TanStack Query `refetchInterval` on the invoice).
  - **D8:** show the link as plain text with "Copy Link" button below the status. Useful for techs to share verbally or paste into other contexts.
  - Add: secondary "Record Other Payment" button (unchanged manual flow).
  - **CG-5 invoice creation:** ensure invoice exists before showing CTAs. If `appointment.invoice_id` is null, primary button text becomes "Create Invoice & Send Payment Link" — clicks call `create-invoice` then `send-link` in sequence. (Existing `POST /appointments/{id}/create-invoice` is verified idempotent.)
  - Loading skeleton while invoice is being fetched/created.
  - **D12 lead-only:** if appointment is for a Lead-only job (no customer), replace CTAs with "Convert lead to customer to take payment" + link to convert flow.
- **`useAppointmentMutations.ts`:**
  - `useCollectPayment.onSuccess` adds `invoiceKeys.all` and `customerInvoiceKeys.all` to invalidation set.
  - New `useSendPaymentLink` mutation invalidating same keys.
- **`AppointmentModal.tsx`:**
  - Add `<PaidStatePill />` for PAID / REFUNDED / DISPUTED states.
  - Show "Link sent {n} times, last on {date}" indicator when link sent but invoice still SENT/OVERDUE.
  - Hide CTA entirely for service-agreement-covered jobs (verify guard exists; add if not).
  - **CG-6 polling:** `refetchInterval: 4000` on appointment-detail query when `invoice.status` is SENT/OVERDUE and `payment_link_sent_count > 0`. Auto-stops on terminal state.
- **`PaymentDialog.tsx`:**
  - Reference field auto-prefix: `^pi_[A-Za-z0-9]+$` → prepend `stripe:`. Don't double-prefix.
- **`InvoiceList.tsx`:**
  - Channel pill column derived from `payment_reference`:
    - `stripe:pi_*` → "Payment Link" pill (purple, with Stripe icon).
    - Legacy `payment_method == 'stripe'` (no prefix) → "Stripe (legacy)" pill.
    - Bare → method label.
  - **CG-13 search:** verify `payment_reference` filter supports substring (`ILIKE %{q}%`). Add if needed. Test: paste `pi_3OXxxx` into search → finds the invoice.
- **`InvoiceDetail.tsx` (or equivalent):**
  - Add "Send Payment Link" button (becomes "Resend Payment Link" if `payment_link_sent_count > 0`).
  - Display: link URL (truncated with copy button), sent count, last-sent timestamp, link active status.
  - For PAID invoices: hide the button, show "Paid via Payment Link · {pi_id}" with link to Stripe Dashboard.
- **Frontend types** (`features/invoices/types/index.ts`):
  - Add `'refunded'`, `'disputed'` to `InvoiceStatus`.
  - Add new fields to `Invoice`: `stripe_payment_link_id`, `stripe_payment_link_url`, `stripe_payment_link_active`, `payment_link_sent_at`, `payment_link_sent_count`.

### Phase 4 — Reminder integration (~0.5 day)

- **D5 — Inject Payment Link in overdue reminder SMS:**
  - Locate the reminder template (search `services/sms/` and `templates/`).
  - Modify the template to include `{stripe_payment_link_url}` if the invoice has an active link. Fallback to existing template if no link.
  - Same applies to lien-warning reminders.
  - **Test:** trigger a reminder for an invoice with a Payment Link → SMS contains the URL.

### Phase 5 — Documentation, runbook, training (~0.5 day)

- **Tech-facing 1-pager:** much shorter than Architecture B's. Essentially: "Tap 'Send Payment Link' → wait while customer pays → invoice flips to Paid automatically. For cash/check/Venmo/Zelle, use 'Record Other Payment'."
- **Internal runbook** at `docs/payments-runbook.md`:
  - How to read the link state on an invoice (active / used / regenerated).
  - How to re-send a link from the office (Invoice Detail page).
  - **CG-19 receipt resend:** when a customer says they didn't get a receipt, resend from Stripe Dashboard → charge detail → "Resend receipt." No Grin's-side action.
  - Refund procedure: always from Stripe Dashboard. Webhook auto-reconciles.
  - Dispute response procedure: from Stripe Dashboard. Time-sensitive.
  - Webhook secret rotation procedure.
  - Stripe API version bump procedure.
- **Update README payments section.**
- **Mark legacy Stripe-Terminal modules deprecated** with module-level docstrings pointing to this plan.

### Phase 6 — Field validation & rollout (~3–5 days elapsed)

#### 6a — Agent-Browser E2E validation script (mandatory; per S8)

Create `e2e/payment-links-flow.sh` to validate the new flow against the dev environment:

```bash
#!/usr/bin/env bash
# Pre-flight (S8 + e2e-testing-skill.md)
agent-browser --version || { npm install -g agent-browser && agent-browser install --with-deps; }

# Phase 0: open the dev frontend
agent-browser open https://frontend-git-dev-kirilldr01s-projects.vercel.app/login
agent-browser screenshot e2e-screenshots/00-login.png
agent-browser fill "[name='email']" "$DEV_TEST_USER_EMAIL"
agent-browser fill "[name='password']" "$DEV_TEST_USER_PASS"
agent-browser click "[data-testid='submit-login-btn']"
agent-browser wait --url "**/dashboard"
agent-browser screenshot e2e-screenshots/01-dashboard.png

# Journey 1: Send Payment Link from Appointment Modal
agent-browser open https://.../schedule
agent-browser wait --load networkidle
agent-browser click "[data-testid='appointments-row']:first-child"
agent-browser wait "[data-testid='appointment-modal']"
agent-browser is visible "[data-testid='send-payment-link-btn']"
agent-browser screenshot e2e-screenshots/02-modal-pre-send.png
agent-browser click "[data-testid='send-payment-link-btn']"
agent-browser wait --text "Link sent"
agent-browser screenshot e2e-screenshots/03-modal-link-sent.png

# Trigger webhook via Stripe CLI in another terminal (manual or scripted):
#   stripe trigger payment_intent.succeeded \
#     --override "payment_intent:metadata.invoice_id=$INVOICE_ID"
# Then poll for paid state (polling indicator should auto-collapse):
agent-browser wait --text "Paid" --timeout 30000
agent-browser is visible "[data-testid='status-paid']"
agent-browser screenshot e2e-screenshots/04-modal-paid.png

# Journey 2: Resend from Invoice Detail page
agent-browser open https://.../invoices/$INVOICE_ID
agent-browser wait "[data-testid='invoices-page']"
agent-browser is visible "[data-testid='resend-payment-link-btn']"
agent-browser click "[data-testid='resend-payment-link-btn']"
agent-browser wait --text "Sent"
agent-browser screenshot e2e-screenshots/05-invoice-detail-resent.png

# Journey 3: Channel pill in Invoice List
agent-browser open https://.../invoices
agent-browser wait "[data-testid='invoices-table']"
agent-browser is visible "[data-testid='status-payment-link']"
agent-browser screenshot e2e-screenshots/06-invoice-list-channel-pill.png

# Journey 4: Service-agreement-covered job hides the CTA
agent-browser open https://.../schedule  # navigate to a service-agreement-covered appointment
agent-browser click "[data-testid='appointments-row'][data-service-agreement='true']"
agent-browser wait "[data-testid='appointment-modal']"
agent-browser is visible "[data-testid='covered-by-agreement-pill']"
agent-browser get count "[data-testid='send-payment-link-btn']"  # expect 0

# Journey 5: $0 invoice hides the CTA (F11)
# Set up a $0 invoice in the test fixtures, then:
agent-browser open https://.../invoices/$ZERO_INVOICE_ID
agent-browser get count "[data-testid='send-payment-link-btn']"  # expect 0

# Responsive: mobile viewport
agent-browser set viewport 375 812
agent-browser open https://.../schedule
agent-browser screenshot e2e-screenshots/07-mobile-schedule.png
agent-browser open https://.../invoices/$INVOICE_ID
agent-browser screenshot e2e-screenshots/08-mobile-invoice-detail.png

# Console + errors check
agent-browser console > e2e-screenshots/console.log
agent-browser errors > e2e-screenshots/errors.log

agent-browser close
```

**Acceptance:** all 5 journeys + responsive screenshots passing; console/errors log clean (no uncaught exceptions). Save screenshots under `e2e-screenshots/payment-links-architecture-c/`.

#### 6b — Real test charge with Stripe CLI

```bash
# Forward dev webhook to local backend (or test against deployed dev URL)
stripe listen --forward-to https://grins-dev-dev.up.railway.app/api/v1/webhooks/stripe

# In another terminal, trigger:
stripe trigger payment_intent.succeeded \
  --override "payment_intent:metadata.invoice_id=<INVOICE_UUID>"

# Then verify:
# - Invoice in Grin's flips to PAID
# - Job.payment_collected_on_site = True
# - stripe_webhook_events table has the event_id with processing_status='completed'
```

#### 6c — Refund + dispute exercise

```bash
stripe trigger charge.refunded
stripe trigger charge.dispute.created
```

Verify invoice transitions to REFUNDED and DISPUTED respectively.

#### 6d — Soft launch + monitoring

- Production soft launch (after staging green).
- Monitor `payment_link_sent_count` vs. `paid_at` ratio for the first 2 weeks (conversion rate target: ≥70%).
- Monitor `stripe_webhook_events` table for `processing_status='failed'` rows (target: 0).

### Phase 7 — DEVLOG entry (mandatory; per S10)

Prepend an entry to `/Users/kirillrakitin/Grins_irrigation_platform/DEVLOG.md` immediately under `## Recent Activity` using the format in `devlog-rules.md`. Category: **FEATURE**. Title: "Stripe Payment Links via SMS (Architecture C)". Sections: What Was Accomplished, Technical Details, Decision Rationale (cite the rejection of Architectures A and B), Challenges and Solutions, Next Steps.

The entry is the closing artifact — it lives in `DEVLOG.md` permanently and is the canonical narrative future readers will see.

---

## STEP-BY-STEP TASKS

> Execute top to bottom. Each task is atomic and independently testable.

### Phase 0 ops

#### 0.1 Subscribe new Stripe webhook event types
- **IMPLEMENT:** add `payment_intent.succeeded`, `.payment_failed`, `.canceled`, `charge.refunded`, `charge.dispute.created` in Stripe Dashboard → Webhooks.
- **VALIDATE:** events list shows all 11 (6 existing + 5 new).

#### 0.2 Receipt branding + custom sender domain
- **IMPLEMENT:** Stripe Dashboard → Branding (logo, color, contact). Settings → Emails → custom sender. DNS DKIM/SPF records.
- **VALIDATE:** trigger a $0.50 test charge → receipt arrives from the Grin's-domain sender.

#### 0.3 Confirm tipping disabled
- **IMPLEMENT:** Stripe Dashboard → Settings → Tipping → OFF.
- **VALIDATE:** test Payment Link → Stripe Checkout page shows no tip prompt.

### Phase 1 — Customer linkage

#### 1.1 ADD partial unique index on `customers.stripe_customer_id`
- **IMPLEMENT:** Alembic migration with `CREATE UNIQUE INDEX ... WHERE stripe_customer_id IS NOT NULL`.
- **VALIDATE:** `uv run alembic upgrade head && downgrade -1 && upgrade head`.

#### 1.2 ADD `CustomerService.get_or_create_stripe_customer(customer_id) -> str`
- **IMPLEMENT:** idempotent helper using `stripe.Customer.create` with `metadata={'grins_customer_id': ...}`.
- **VALIDATE:** unit tests for first-create, already-linked, Stripe error.

#### 1.3 CREATE `scripts/backfill_stripe_customers.py`
- **IMPLEMENT:** paginate, rate-limit-aware, idempotent.
- **VALIDATE:** dry-run then real run; confirm no duplicates.

#### 1.4 ADD post-write hook in `CustomerService.create_customer` / `update_customer`
- **IMPLEMENT:** best-effort call to `get_or_create_stripe_customer`.
- **VALIDATE:** existing customer-service tests still pass; new test for hook.

#### 1.5 CG-18 audit + invariant
- **IMPLEMENT:** one-shot SQL audit; add invariant in `ServiceAgreementService.create_or_update`.
- **VALIDATE:** unit test asserting divergent IDs raise.

### Phase 2 — Backend Payment Link + webhook

#### 2.1 ADD Stripe API version pinning to `StripeSettings` and call sites (per F6)
- **IMPLEMENT:** add to `services/stripe_config.py:13–48`:
    ```python
    stripe_api_version: str = Field(
        default="2025-03-31.basil",
        description="Pinned Stripe API version. Matches the version on existing webhook endpoints (verified 2026-04-28). Override via STRIPE_API_VERSION env var.",
    )
    ```
- **Set on every Stripe call site.** Currently `stripe.api_key = self.stripe_settings.stripe_secret_key` is set in:
  - `services/stripe_terminal.py:55, 113` (deprecated module — still set for safety)
  - `services/customer_service.py` (existing usages around lines 1445–1610)
  - New `services/stripe_payment_link_service.py` (this PR)
  - New webhook reconciliation handlers in `api/v1/webhooks.py` (this PR)
- At every site, immediately after `stripe.api_key = ...` add `stripe.api_version = self.stripe_settings.stripe_api_version`.
- **At merge time:** check Stripe Dashboard → Developers → API versions for the latest stable; update the default string if needed.
- **VALIDATE:** new test in `test_stripe_config.py` asserts `StripeSettings().stripe_api_version` is non-empty; new test in `test_payment_link_service.py` asserts service constructor sets `stripe.api_version`.

#### 2.2 ADD `InvoiceStatus.REFUNDED` and `DISPUTED` enum values
- **IMPLEMENT:** backend `models/enums.py` + frontend `types/index.ts`.
- **VALIDATE:** typecheck + existing enum-related tests still pass.

#### 2.3 ALEMBIC migration: new columns on `invoices`
- **IMPLEMENT:** `stripe_payment_link_id`, `stripe_payment_link_url`, `stripe_payment_link_active`, `payment_link_sent_at`, `payment_link_sent_count` (with defaults). Partial index on `stripe_payment_link_id`.
- **VALIDATE:** upgrade-downgrade-upgrade cycle clean.

#### 2.4 CREATE `services/stripe_payment_link_service.py`
- **IMPLEMENT:** `create_for_invoice(invoice, customer) -> tuple[str, str]`, `deactivate(link_id) -> None`, `_build_line_items(invoice) -> list[dict]`, custom error class `StripePaymentLinkError`.
- **PATTERN:** mirror `services/stripe_terminal.py` (LoggerMixin, `DOMAIN = "payment"`, log_started/log_completed/log_failed, custom Exception).
- **`_build_line_items` must handle BOTH JSONB shapes per F2:**
    ```python
    def _build_line_items(self, invoice: Invoice) -> list[dict[str, object]]:
        items = invoice.line_items or []
        if not items:
            # Fallback for invoices without explicit line_items (per F3).
            return [{
                "price_data": {
                    "currency": "usd",
                    "unit_amount": int((invoice.total_amount * 100).to_integral_value()),
                    "product_data": {"name": f"Invoice {invoice.invoice_number}"},
                },
                "quantity": 1,
            }]
        out: list[dict[str, object]] = []
        for raw in items:
            description = str(raw.get("description", "Service"))
            if "total" in raw or "unit_price" in raw:
                # Pydantic InvoiceLineItem shape (F2 path A)
                qty = Decimal(str(raw.get("quantity", "1")))
                total = Decimal(str(raw["total"]))
                unit_amount = int((total / qty * 100).to_integral_value())
                quantity = int(qty)
            elif "amount" in raw:
                # Legacy shape from create_invoice_from_appointment (F2 path B)
                unit_amount = int((Decimal(str(raw["amount"])) * 100).to_integral_value())
                quantity = 1
            else:
                msg = f"Line item has neither 'total' nor 'amount': {raw}"
                raise StripePaymentLinkError(msg)
            out.append({
                "price_data": {
                    "currency": "usd",
                    "unit_amount": unit_amount,
                    "product_data": {"name": description[:250]},
                },
                "quantity": quantity,
            })
        return out
    ```
- **Stripe call signature for `create_for_invoice`:**
    ```python
    link = stripe.PaymentLink.create(
        line_items=self._build_line_items(invoice),
        metadata={"invoice_id": str(invoice.id), "customer_id": str(invoice.customer_id)},
        restrictions={"completed_sessions": {"limit": 1}},
        customer_creation="if_required",
        after_completion={"type": "hosted_confirmation"},
        allow_promotion_codes=False,
        billing_address_collection="auto",
    )
    return link.id, link.url
    ```
- **GOTCHA — F11 $0 invoices:** before constructing line items, if `invoice.total_amount == Decimal(0)`, **do not call Stripe**. Raise a sentinel `StripePaymentLinkSkipped` exception (or return `(None, None)` — caller treats as best-effort skip) and log `payment_link.skipped_zero_amount`. The hook in 2.5 catches this and proceeds without persisting link fields.
- **GOTCHA — Stripe metadata limits:** keys ≤40 chars, values ≤500 chars. UUIDs fit (36 chars).
- **GOTCHA — line item description:** truncate to 250 chars (Stripe `product_data.name` limit).
- **VALIDATE:** unit tests for create (legacy line items), create (Pydantic line items), create with no line items (F3 fallback), $0 invoice skip, deactivate, Stripe error, metadata size limit.

#### 2.4a MODIFY existing `AppointmentService.create_invoice_from_appointment` to be idempotent (per F1)
- **IMPLEMENT:** at the start of the method, after fetching `appointment` + `job`, call `existing = await self._find_invoice_for_job(job.id)`. If `existing is not None`, log `create_invoice_from_appointment.idempotent_hit` and return `existing` immediately.
- **ALSO:** fix the lying docstring at line 2086. Remove "Generates a Stripe payment link and sends via SMS + email." Replace with: "Creates a new invoice (or returns the existing one for this job) populated from job data. Stripe Payment Link auto-creation is hooked in InvoiceService — see plan §Phase 2.5."
- **GOTCHA:** the existing `_find_invoice_for_job` returns the *most recent* invoice for the job. For our use case this is correct — one invoice per job is the norm. If multi-invoice-per-job is ever desired, this idempotency check needs a stricter key (e.g., a `linked_appointment_id` column on Invoice). Out of scope.
- **VALIDATE:** new test `test_create_invoice_from_appointment_is_idempotent`. Call twice, assert same `invoice.id`, sequence number not consumed twice.

#### 2.5 HOOK into `InvoiceService.create_invoice` and `InvoiceRepository.create`
- **IMPLEMENT:** both code paths that produce an Invoice need the hook. Two call sites:
  1. `InvoiceService.create_invoice(InvoiceCreate)` — admin-creates invoice via `POST /invoices/`.
  2. `InvoiceRepository.create(...)` called from `AppointmentService.create_invoice_from_appointment` (F1 path).
- **Cleanest implementation:** add a private `_attach_payment_link(invoice)` method on `InvoiceService` that calls `CustomerService.get_or_create_stripe_customer(invoice.customer_id)` then `StripePaymentLinkService.create_for_invoice(invoice, customer)`, persists the result, and is best-effort. Have BOTH paths call it after the Invoice is committed.
- **For the appointment path:** since the Invoice is created by `InvoiceRepository.create` *inside* `AppointmentService`, the cleanest fix is to give `AppointmentService` a reference to `InvoiceService._attach_payment_link` (or duplicate the small attach logic). Mirror existing DI patterns.
- **Best-effort error handling:**
    ```python
    try:
        link_id, link_url = self.payment_link_service.create_for_invoice(invoice, customer)
        if link_id is not None:  # may be None for $0 (F11)
            await self.invoice_repository.update(invoice.id, {
                "stripe_payment_link_id": link_id,
                "stripe_payment_link_url": link_url,
                "stripe_payment_link_active": True,
            })
    except (StripePaymentLinkError, stripe.StripeError) as e:
        logger.warning("payment_link.create_failed_at_invoice_creation",
                       invoice_id=str(invoice.id), error=str(e))
        # Invoice is still saved; link gets created on first send-link attempt.
    ```
- **VALIDATE:** integration tests for both call sites; both populate link fields; both gracefully handle Stripe failure (invoice still saves).

#### 2.6 HOOK into `InvoiceService.update_invoice`
- **IMPLEMENT:** detect if `line_items` or `total_amount` changed (compare before/after). If yes AND `invoice.stripe_payment_link_id IS NOT NULL` AND `invoice.stripe_payment_link_active`:
  1. Call `StripePaymentLinkService.deactivate(invoice.stripe_payment_link_id)`.
  2. Call `_attach_payment_link(invoice)` to create a fresh one.
  3. Log `payment_link.regenerated` with old/new IDs.
- **GOTCHA:** if the update also hits a status field that should *not* trigger regeneration (e.g., `notes` change), don't regenerate. Be specific: only on `line_items` change OR `total_amount` change.
- **VALIDATE:** integration test updates invoice line items, asserts old link deactivated AND new link created with new amount.

#### 2.7 IMPLEMENT `InvoiceService.send_payment_link(invoice_id) -> SendLinkResponse`
- **IMPLEMENT:** uses pinned interfaces from F7 (SMS) and F8 (email).
- **Method body sketch (per F7 + F12, verified exact signatures):**
    ```python
    from grins_platform.log_config import get_logger
    from grins_platform.schemas.ai import MessageType
    from grins_platform.services.sms.recipient import Recipient
    from grins_platform.services.email_service import TRANSACTIONAL_SENDER
    from grins_platform.exceptions import (
        SMSConsentDeniedError,
        SMSRateLimitDeniedError,
        SMSError,
    )

    logger = get_logger(__name__)

    async def send_payment_link(self, invoice_id: UUID) -> SendLinkResponse:
        invoice = await self._get_invoice_or_404(invoice_id)
        customer = await self.customer_repository.get_by_id(invoice.customer_id)
        if customer is None:
            raise LeadOnlyInvoiceError(invoice_id)
        # F11: refuse $0 invoices
        if invoice.total_amount == Decimal(0):
            raise InvalidInvoiceOperationError("Cannot send payment link for $0 invoice")
        # Lazy-create link if missing (covers Phase 2.5 best-effort failure)
        if invoice.stripe_payment_link_url is None:
            await self._attach_payment_link(invoice)
            invoice = await self._get_invoice_or_404(invoice_id)  # refresh
        body = self._build_payment_link_sms_body(customer, invoice)  # D4 template
        # SMS path — transactional, bypasses sms_opt_in (F12).
        if customer.phone:
            recipient = Recipient(
                phone=customer.phone,
                source_type="customer",
                source_id=customer.id,
            )
            try:
                result = await self.sms_service.send(
                    recipient=recipient,
                    message=body,
                    message_type=MessageType.PAYMENT_LINK,  # add to schemas/ai.py
                    consent_type="transactional",
                )
                if result.get("success") is True:
                    return await self._record_link_sent(invoice, channel="sms")
                logger.warning(
                    "payment.send_link.sms_failed_soft",
                    invoice_id=str(invoice.id),
                    status=result.get("status"),
                )
            except SMSConsentDeniedError:
                # Customer hard-STOP'd — fall through to email
                logger.info(
                    "payment.send_link.sms_blocked_by_consent",
                    invoice_id=str(invoice.id),
                )
            except (SMSRateLimitDeniedError, SMSError) as e:
                logger.warning(
                    "payment.send_link.sms_failed_hard",
                    invoice_id=str(invoice.id),
                    error=str(e),
                )
        # Email fallback — transactional, bypasses email_opt_in (F12).
        if customer.email:
            sent = self.email_service._send_email(  # noqa: SLF001 (F8 pattern)
                to_email=customer.email,
                from_email=TRANSACTIONAL_SENDER,
                subject=f"Your invoice from Grin's Irrigation — ${invoice.total_amount}",
                html_body=self._render_payment_link_email_html(customer, invoice),
                text_body=self._render_payment_link_email_text(customer, invoice),
            )
            if sent:
                return await self._record_link_sent(invoice, channel="email")
        raise NoContactMethodError(invoice_id)
    ```
- **Pre-task: add `MessageType.PAYMENT_LINK = "payment_link"`** to the enum at `schemas/ai.py:53`. One-line addition. Frontend `features/invoices/types/index.ts` does not need to mirror this (backend-only enum).
- **Recipient construction** uses the dataclass at `services/sms/recipient.py:23`. Required fields confirmed via codebase grep: `phone`, `source_type`, `source_id`. Inspect the actual dataclass at implementation time to confirm field names match exactly (constructor signature is the canonical truth — line 23+).
- **Hard-STOP raises `SMSConsentDeniedError`** (verified — docstring at `sms_service.py:240`). Catch it, log at INFO, fall through to email. Do not bubble up.
- **Email `_send_email` signature** confirmed earlier: `_send_email(to_email, from_email, subject, html_body, text_body) -> bool`. The `# noqa: SLF001` is the established pattern in `notification_service.py`, `campaign_service.py`, etc.
- **`SendLinkResponse` schema** must be added in `schemas/invoice.py`:
    ```python
    class SendLinkResponse(BaseModel):
        channel: Literal["sms", "email"]
        link_url: str
        sent_at: datetime
        sent_count: int
    ```
- **PATTERN sources:**
  - F7: `SMSService` is at `services/sms_service.py:176`. Inject via DI; `send_text(to, body)` is the call. Allowlist guard runs inside `SMSService` automatically (per memory `feedback_sms_test_number.md`).
  - F8: `email_service._send_email(to_email, from_email, subject, html_body, text_body) -> bool`. Allowlist guard `enforce_email_recipient_allowlist` runs inside `_send_email` automatically (per memory `feedback_email_test_inbox.md`). Use `# noqa: SLF001` per established pattern.
- **`_record_link_sent`:** persists `payment_link_sent_at = now`, increments `payment_link_sent_count`, returns `SendLinkResponse{channel, link_url, sent_at, sent_count}`.
- **D4 template:** `f"Hi {customer.first_name}, your invoice from Grin's Irrigation for ${invoice.total_amount} is ready: {invoice.stripe_payment_link_url}"`. Verify segment count in test (should be 1–2 segments).
- **NEW exceptions to add to `exceptions/__init__.py`:**
    ```python
    class NoContactMethodError(InvoiceError):
        """Raised when an invoice cannot be delivered: no phone (or sms_opt_in) AND no email (or email_opt_in)."""

    class LeadOnlyInvoiceError(InvoiceError):
        """Raised when an invoice's customer is null/Lead-only — payment link cannot be sent."""
    ```
- **GOTCHA — opt-in (F12):** even if `customer.phone` is set, only SMS if `sms_opt_in` is True. Same for email. If both opted out, `NoContactMethodError`.
- **VALIDATE:** unit tests:
  - `test_send_payment_link_sms_happy` — SMS returns `status="sent"` → `channel="sms"` returned.
  - `test_send_payment_link_falls_back_to_email_on_sms_failure` — `send` raises `CallRailError` → email called → `channel="email"`.
  - `test_send_payment_link_falls_back_to_email_on_hard_stop` — SMS raises `ConsentHardStopError` → email called → `channel="email"`.
  - `test_send_payment_link_email_only_when_no_phone` — phone null → SMS skipped, email called.
  - `test_send_payment_link_bypasses_sms_opt_in` (F12) — customer with `sms_opt_in=False` and a phone → SMS still sent (asserts `consent_type="transactional"` passed to SMSService).
  - `test_send_payment_link_bypasses_email_opt_in` (F12) — customer with `email_opt_in=False` and an email but no phone → email still sent from `TRANSACTIONAL_SENDER`.
  - `test_send_payment_link_no_phone_no_email` — both null → `NoContactMethodError`.
  - `test_send_payment_link_zero_amount_invoice` — raises `InvalidInvoiceOperationError`.
  - `test_send_payment_link_lazy_creates_link_when_missing` — invoice has no link fields → `_attach_payment_link` called.
  - `test_send_payment_link_increments_sent_count` — sent_count goes 0 → 1 → 2 over multiple calls.

#### 2.8 ADD endpoint `POST /api/v1/invoices/{id}/send-link`
- **IMPLEMENT:** mirror existing invoice endpoint pattern; CurrentActiveUser auth; map service errors to HTTP codes.
- **VALIDATE:** `pytest -k send_payment_link`.

#### 2.9 EXTEND `HANDLED_EVENT_TYPES` and ROUTE new events
- **IMPLEMENT:** add 5 event types; dispatch dict maps event type → handler in `webhooks.py`.

#### 2.10 IMPLEMENT `_handle_payment_intent_succeeded`
- **IMPLEMENT:** CG-7 short-circuit, metadata.invoice_id match, CG-8 cancelled-invoice handling, idempotency double-layer, currency check, calls into `InvoiceService.record_payment`.
- **VALIDATE:** unit tests for every branch (see Edge Cases).

#### 2.11 IMPLEMENT `_handle_payment_intent_payment_failed`, `_handle_payment_intent_canceled`
- **IMPLEMENT:** logs only.
- **VALIDATE:** unit tests.

#### 2.12 IMPLEMENT `_handle_charge_refunded`
- **IMPLEMENT:** full refund → REFUNDED + `Job.payment_collected_on_site = False`. Partial → PARTIAL with adjusted `paid_amount`. Idempotent.
- **VALIDATE:** unit tests for full and partial paths.

#### 2.13 IMPLEMENT `_handle_charge_dispute_created`
- **IMPLEMENT:** mark DISPUTED, append notes, log WARNING.
- **VALIDATE:** unit test.

### Phase 3 — Frontend rewire

#### 3.1 REWRITE `PaymentCollector.tsx`
- **IMPLEMENT:** delete tap_to_pay path entirely; primary "Send Payment Link" button + secondary "Record Other Payment"; auto-create-invoice flow if missing; lead-only message; copy-link UX (D8).
- **VALIDATE:** vitest tests for all branches; preserve existing `data-testid` for compatibility where possible.

#### 3.2 ADD `useSendPaymentLink` mutation in `useInvoiceMutations.ts`
- **IMPLEMENT:** mutation calling `invoiceApi.sendPaymentLink`; invalidate invoice + customer-invoice + appointment query keys.
- **VALIDATE:** vitest mutation test.

#### 3.3 ADD `<PaidStatePill />` + link-sent indicator in `AppointmentModal.tsx`
- **VALIDATE:** snapshot tests for paid, link-sent-pending, refunded, disputed states.

#### 3.4 ADD service-agreement guard + lead-only guard in `AppointmentModal.tsx`
- **VALIDATE:** snapshots for both edge cases.

#### 3.5 CG-6 polling indicator
- **IMPLEMENT:** TanStack Query `refetchInterval: 4000` when invoice is SENT/OVERDUE and `payment_link_sent_count > 0`.
- **VALIDATE:** test that polling stops on PAID/REFUNDED/DISPUTED.

#### 3.6 UPDATE `PaymentDialog.tsx` reference auto-prefix
- **VALIDATE:** unit test.

#### 3.7 UPDATE `InvoiceList.tsx` channel pill (incl. legacy STRIPE handling)
- **VALIDATE:** snapshot tests.

#### 3.8 ADD/UPDATE `InvoiceDetail.tsx` Send / Resend Link button + status display
- **VALIDATE:** snapshot test for fresh / sent-once / sent-multiple / paid states.

#### 3.9 CG-13 verify search by `pi_*`
- **IMPLEMENT:** ensure `payment_reference` filter supports substring; add `ILIKE %q%` if missing.
- **VALIDATE:** integration test pasting `pi_xxx` into search returns the invoice.

### Phase 4 — Reminder enhancement

#### 4.1 INJECT Payment Link in overdue reminder SMS template (per F9)
- **TARGET:** `InvoiceService.send_reminder` at `services/invoice_service.py:705`.
- **IMPLEMENT:** in the SMS body construction (look for the f-string or template render), append the link when present:
    ```python
    body = f"Reminder: Your invoice from Grin's Irrigation for ${invoice.total_amount} is overdue."
    if invoice.stripe_payment_link_url and invoice.stripe_payment_link_active:
        body += f" Pay now: {invoice.stripe_payment_link_url}"
    ```
- **NO change needed** to `NotificationService.send_invoice_reminders` at `services/notification_service.py:705` — it calls `send_reminder` so the template fix flows through automatically.
- **GOTCHA:** SMS segments — appending the URL adds ~30 chars. Total is ~140–170 chars (1–2 segments). Acceptable.
- **VALIDATE:** unit test `test_send_reminder_includes_payment_link_when_active`. Asserts SMS body contains the URL when `stripe_payment_link_active=True`, does NOT contain it when `False`.

#### 4.2 INJECT Payment Link in lien-warning reminder
- **TARGET:** `InvoiceService.send_lien_warning` (search same file for the function).
- **IMPLEMENT:** same pattern as 4.1.
- **VALIDATE:** unit test for lien warning template.

#### 4.3 ADD Resend email template for payment link delivery
- **CREATE:** `src/grins_platform/services/templates/emails/payment_link_email.html` and `payment_link_email.txt` (Jinja2; mirror existing templates in same directory).
- **VARS:** `customer_first_name`, `invoice_number`, `total_amount`, `payment_link_url`, `business_name=BUSINESS_NAME`, `business_phone=BUSINESS_PHONE`.
- **CONTENT:** business header, "Your invoice is ready," prominent button link, fallback plaintext URL, business contact at footer.
- **VALIDATE:** snapshot test rendering the template with sample vars.

### Phase 5 — Docs

#### 5.1 WRITE tech-facing 1-pager (~half page)
#### 5.2 WRITE `docs/payments-runbook.md` (~150 lines)
#### 5.3 UPDATE README payments section
#### 5.4 ADD deprecation comments on `services/stripe_terminal.py`, `api/v1/stripe_terminal.py`, `frontend/.../stripeTerminalApi.ts`

### Phase 6 — Validation

#### 6.1 Stripe CLI dev test for each new event type
- `stripe trigger payment_intent.succeeded`
- `stripe trigger charge.refunded`
- `stripe trigger charge.dispute.created`

#### 6.2 Staging dry-run with real test card
#### 6.3 Production soft launch with monitoring

---

## EDGE CASES & DEFENSIVE BEHAVIORS

1. **Customer pays via Payment Link** → `payment_intent.succeeded` arrives with `metadata.invoice_id` → invoice marked PAID. Happy path.
2. **Customer never pays** → invoice stays in SENT; goes OVERDUE per existing lifecycle; reminder SMS includes the same Payment Link until paid or cancelled.
3. **Customer pays then is refunded** → `charge.refunded` arrives → invoice transitions to REFUNDED + `Job.payment_collected_on_site = False`.
4. **Customer pays then disputes** → `charge.dispute.created` → invoice DISPUTED, admin alert; admin responds in Stripe Dashboard.
5. **Customer tries to pay twice** → blocked by `restrictions.completed_sessions.limit=1`; second tap shows "This link has already been used."
6. **Invoice cancelled before customer pays** (race, CG-8) — link still active in Stripe; if customer somehow pays anyway, webhook refuses to mark CANCELLED invoice paid, inserts log alert, admin refunds manually.
7. **Invoice line items edited after link sent** (D3) — old link deactivated, new link generated with new amount; customer who taps the old link sees "deactivated" message; tech must re-send. Frontend shows "Link regenerated, please re-send" warning.
8. **SMS provider hard-fails** — fallback to Resend email (D6). If both fail (no phone, no email, OR provider outage), endpoint returns 422 `NoContactMethodError`; UI shows "Cannot send: customer has no phone or email."
9. **Lead-only appointment** (D12) — UI hides CTA, backend safety net rejects send-link.
10. **Service-agreement-covered job** — UI hides CTA entirely; no link generated.
11. **Webhook arrives twice (replay)** — `stripe_webhook_events` table catches by `event.id`; second call no-ops.
12. **Webhook for `payment_intent.succeeded` fires before our SMS even completes** (rare, but Stripe is fast) — handler still works because metadata is the source of truth, not invoice send state.
13. **Subscription renewal fires `payment_intent.succeeded`** (CG-7) — handler short-circuits because `event.data.object.invoice` is non-null.
14. **Manual `record_payment` and webhook race** — webhook checks invoice status; if already PAID, no-op; existing idempotency.
15. **Customer has multiple unpaid invoices** — each gets its own Payment Link; tech can send each individually. No bulk send in v1.
16. **Customer email differs between Grin's and Stripe** — Stripe sends receipt to whatever's on the Stripe Customer record. Post-write hook (Phase 1) keeps them in sync.
17. **Customer with no email AND no phone** — Stripe doesn't auto-send receipts (no destination); frontend warning "no contact methods" prevents Send Link entirely.
18. **Currency mismatch** (charge in EUR/CAD/etc.) — handler logs and refuses to mark paid. Out of scope.
19. **Webhook delivery delay** — frontend polling (CG-6) handles UX; tech sees "waiting for payment" and refresh resolves.
20. **Stripe API outage during link creation** — best-effort hook logs and continues; link gets created on first send-attempt.
21. **Stripe API version drift** — pinned via `stripe.api_version`. Bumping is a deliberate PR with regression tests.
22. **Tipping enabled accidentally** — Stripe app charge would mismatch, but we don't use the Stripe app. Payment Links don't have tip prompts unless explicitly configured (we don't).
23. **Tax added in Stripe** — same; we don't enable Stripe Tax.
24. **Estimate / deposit flow** — for two-payment workflows, create two Grin's invoices ("Deposit" + "Final"); each gets its own Payment Link; admin sends each separately.
25. **Payment Link clicked on a different device than the one that received the SMS** — fine; the link is just a URL.
26. **Customer forwards the SMS to someone else who pays** — fine for us; webhook still fires; invoice marked paid. (Stripe records the actual payer's email for receipt.)
27. **Customer pays, but Stripe webhook delivery to our server is lost** — Stripe retries automatically (up to 3 days). We'd see the payment in Stripe Dashboard but not in Grin's; runbook covers manual reconciliation via the existing PaymentDialog. Rare in practice.
28. **Refund of a charge with no matching invoice** (e.g., admin manually charged in Stripe outside this flow) — `charge.refunded` handler tries `payment_reference` lookup, finds nothing, logs `charge.refunded.unmatched`. Admin handles in Stripe Dashboard directly.
29. **Stripe Customer email updated externally** — no event subscribed; not synced back to Grin's. Acceptable for v1.
30. **Customer with no email AND no phone but invoice still creates** — link is created server-side regardless; just can't be sent. Admin can copy the URL from Invoice Detail manually and deliver out-of-band.
31. **$0 invoice** (per F11) — service-agreement covered jobs occasionally produce $0 invoices (or admin error). `_attach_payment_link` skips Stripe call; `stripe_payment_link_*` columns stay null; frontend hides Send Link CTA. Admin marks invoice `PAID` manually via `PaymentDialog` if needed (or invoice stays in DRAFT/SENT and is later cancelled).
32. **Customer is opted out of marketing SMS** (per F12 transactional bypass) — payment-link SMS still sends; the `sms_opt_in` flag does not gate transactional sends. Hard-STOP customers are still blocked at the SMS service level; they fall through to email.
33. **Customer is opted out of marketing email** (per F12 transactional bypass) — payment-link email still sends from the transactional sender (`noreply@grinsirrigation.com`). Resend's bounce/complaint suppression list is still respected.
34. **Customer has texted STOP** — handled inside `SMSService` (`log_consent_hard_stop` at `services/sms_service.py:37`). The send raises `ConsentHardStopError` (or equivalent — verify exact name); `send_payment_link` catches and falls through to email. If email also blocked → `NoContactMethodError` → office handles manually.
35. **Existing legacy invoices created before this PR** — they have `stripe_payment_link_*` columns NULL. First time someone hits "Send Payment Link" on an old invoice, `send_payment_link` lazy-creates the link via `_attach_payment_link`. Backwards-compat is automatic; no backfill required.
36. **`create_invoice_from_appointment` called twice quickly** (e.g., double-click race; per F1) — the new idempotency check returns the existing invoice; the second call does NOT consume a new sequence number or create a duplicate.
37. **A `late_fee_amount > 0` invoice** — `Invoice.total_amount = amount + late_fee_amount`. The Stripe link uses `total_amount` (via the F3 fallback path if no line items, or sums explicit line items if present). Late fee is not its own line item in the link unless the admin added it as one. Acceptable for v1.

---

## TESTING STRATEGY

### Backend unit tests
- `StripePaymentLinkService.create_for_invoice` — happy, missing customer, Stripe error.
- `StripePaymentLinkService.deactivate` — happy, idempotent if already inactive.
- `_build_line_items` — Decimal-to-cents conversion, multi-line invoices.
- `InvoiceService.create_invoice` hook — auto-creates link, best-effort on Stripe failure.
- `InvoiceService.update_invoice` hook — regenerates on amount change, no-op on unrelated change.
- `InvoiceService.send_payment_link` — SMS happy, email fallback, no-contact, lead-only, allowlist guard.
- All webhook handlers — every branch (see Edge Cases).
- `CustomerService.get_or_create_stripe_customer` — idempotent.

### Backend integration tests
- Invoice → auto-link → send → Stripe-CLI-trigger `payment_intent.succeeded` → invoice PAID + `Job.payment_collected_on_site = True`.
- Invoice update mid-flight → link regenerated.
- Refund via `charge.refunded` event → invoice REFUNDED.
- Dispute → DISPUTED.
- Idempotency: webhook replay → no double-write.
- Subscription overlap: simulated subscription renewal events → both handlers do not double-process.

### Frontend unit tests
- `PaymentCollector` — Send Link primary path, manual secondary, lead-only message, no-invoice auto-create.
- `AppointmentModal` — paid pill, link-sent indicator, polling stops on terminal status.
- `PaymentDialog` — reference auto-prefix.
- `InvoiceList` — channel pills (Payment Link, Stripe legacy, manual).
- `InvoiceDetail` — Send / Resend states.
- `useSendPaymentLink` — invalidation keys.

### End-to-end manual validation (Stripe test mode)
1. Create test invoice in Grin's: $1.00 against a customer with `kirillrakitinsecond@gmail.com` + `+19527373312`.
2. Confirm `Invoice.stripe_payment_link_id` and `_url` populated.
3. Tap "Send Payment Link" in appointment modal.
4. Confirm SMS arrives at the test phone.
5. Tap link on phone, pay with Stripe test card `4242 4242 4242 4242`.
6. Confirm webhook fires → invoice marks PAID within 5s → "Paid" pill appears in modal → Stripe sends test receipt email.
7. Refund the charge from Stripe Dashboard → invoice transitions to REFUNDED.
8. Trigger a dispute test via Stripe CLI → invoice DISPUTED.
9. Edit a different invoice's line items → confirm old link deactivated, new link created.
10. Try to use the old (deactivated) link → confirm Stripe shows "deactivated" message.

### Stripe CLI commands
- `stripe trigger payment_intent.succeeded`
- `stripe trigger charge.refunded`
- `stripe trigger charge.dispute.created`

---

## VALIDATION COMMANDS

### Level 1: Syntax & Style
```bash
uv run ruff check src/grins_platform/api/v1/webhooks.py src/grins_platform/services/stripe_payment_link_service.py src/grins_platform/services/customer_service.py src/grins_platform/services/invoice_service.py src/grins_platform/models/enums.py
uv run ruff format src/grins_platform/services/stripe_payment_link_service.py src/grins_platform/api/v1/webhooks.py
uv run mypy src/grins_platform/
cd frontend && npm run lint && npm run typecheck
```

### Level 2: Unit tests
```bash
uv run pytest src/grins_platform/tests/unit/test_stripe_webhook.py src/grins_platform/tests/unit/test_payment_link_service.py src/grins_platform/tests/unit/test_invoice_service.py src/grins_platform/tests/unit/test_customer_service.py -v
cd frontend && npm test PaymentCollector PaymentDialog AppointmentModal InvoiceList InvoiceDetail useInvoiceMutations
```

### Level 3: Integration tests
```bash
uv run pytest src/grins_platform/tests/integration/test_invoice_integration.py src/grins_platform/tests/integration/test_payment_link_flow_integration.py -v
```

### Level 4: Manual validation (Stripe CLI + dev server)
```bash
uv run uvicorn grins_platform.app:app --reload --port 8000
stripe listen --forward-to localhost:8000/api/v1/webhooks/stripe
cd frontend && npm run dev
# In another terminal:
stripe trigger payment_intent.succeeded
```

### Level 5: Stripe MCP spot checks
- `mcp__stripe__list_payment_intents` — confirm test-mode account state.

---

## ACCEPTANCE CRITERIA

- [ ] Phase 0 ops complete: 5 new webhook events subscribed; receipt branding + custom sender configured; tipping disabled.
- [ ] All Grin's customers (existing + future) have a `stripe_customer_id` populated.
- [ ] Stripe API version pinned in code.
- [ ] `InvoiceStatus.REFUNDED` and `DISPUTED` shipped end-to-end.
- [ ] `invoices` table has 5 new columns (`stripe_payment_link_id`, `_url`, `_active`, `payment_link_sent_at`, `payment_link_sent_count`).
- [ ] Auto-create Payment Link on `InvoiceService.create_invoice` (best-effort).
- [ ] Regenerate Payment Link on `InvoiceService.update_invoice` when line items or total change.
- [ ] `POST /api/v1/invoices/{id}/send-link` endpoint live; SMS preferred, email fallback, no-contact error.
- [ ] Webhook handler processes all 5 new event types idempotently.
- [ ] CG-7 subscription short-circuit asserted by test.
- [ ] CG-8 cancelled-invoice race handled.
- [ ] End-to-end test passing: create invoice → send link → pay → invoice PAID → receipt arrives.
- [ ] No code in `PaymentCollector.tsx` references `stripeTerminalApi` or attempts `discoverReaders`.
- [ ] Service-agreement-covered jobs hide the Send Link CTA.
- [ ] Lead-only appointments hide the Send Link CTA + backend safety net.
- [ ] `PaymentDialog.tsx` auto-prefixes bare `pi_*` references with `stripe:`.
- [ ] `InvoiceList.tsx` shows channel pills (Payment Link / Stripe legacy / manual).
- [ ] `InvoiceDetail.tsx` Send / Resend Link button works.
- [ ] Polling indicator shipped; auto-collapses on terminal status (CG-6).
- [ ] Overdue reminder SMS includes the Payment Link (D5).
- [ ] CG-13 search by `pi_*` returns the invoice.
- [ ] CG-18 audit + invariant in place.
- [ ] All listed validation commands pass green.
- [ ] No bypass of dev SMS/email allowlist guards.
- [ ] Tech 1-pager + runbook merged.
- [ ] Soft launch: ≥7 days production observation; conversion rate (paid / sent) tracked.

### Steering-document compliance (mandatory; per `.kiro/steering/`)

- [ ] **S1 three-tier testing:** every new module has tests in `tests/unit/` (with `@pytest.mark.unit`), `tests/functional/` (with `@pytest.mark.functional`), and `tests/integration/` (with `@pytest.mark.integration`).
- [ ] **S1 Hypothesis tests** for `_build_line_items` Decimal-to-cents (sum-preserving, idempotent), webhook matcher (idempotency), and arithmetic on `paid_amount` increments.
- [ ] **S2 coverage targets met:** backend services 90%+, frontend components 80%+, hooks 85%+.
- [ ] **S3 logging:** every new service uses `LoggerMixin` with `DOMAIN = "payment"` and `log_started`/`log_completed`/`log_failed`. Every new API endpoint uses `set_request_id()` + `clear_request_id()` + `DomainLogger.api_event()`.
- [ ] **S3 PII masking:** logs at INFO never contain full `pi_*`, full email, full phone — masked.
- [ ] **S4 endpoint test matrix:** every new endpoint has tests for 200/201, 400, 404, and 5xx paths.
- [ ] **S5 VSA imports:** no cross-feature imports added (verified by ESLint + manual review). Cache invalidation uses partial-key strings (`['invoices']`).
- [ ] **S6 data-testid:** every new/modified element has a `data-testid` matching the conventions table.
- [ ] **S7 frontend tests:** every new component has rendering, loading, error, empty, interaction, and form-validation tests with `<QueryProvider>` wrapper.
- [ ] **S8 agent-browser E2E:** `e2e/payment-links-flow.sh` passes all 5 journeys + responsive screenshots.
- [ ] **S9 quality gates:** `ruff check`, `ruff format`, `mypy`, `pyright`, `npm run lint`, `npm run typecheck` all zero errors.
- [ ] **S10 DEVLOG entry** prepended.
- [ ] **S11 performance:** `send_payment_link` <200ms p95 on the cached-link path; lazy-create excursion documented.
- [ ] **S15 security:** webhook signature verification tested; auth dependencies on every new endpoint; no secrets logged.

---

## COMPLETION CHECKLIST

- [ ] Phase 0 ops complete and documented.
- [ ] Phase 1 customer-linkage migration + helper + backfill run.
- [ ] Phase 2 backend Payment Link service + webhook + migration shipped with tests.
- [ ] Phase 3 frontend rewire + Invoice Detail button merged.
- [ ] Phase 4 reminder integration done.
- [ ] Phase 5 docs merged.
- [ ] Phase 6 staging + production validation, plus agent-browser E2E script run with screenshots saved to `e2e-screenshots/payment-links-architecture-c/`.
- [ ] Phase 7: DEVLOG entry prepended to `DEVLOG.md` (category FEATURE).
- [ ] No TypeScript, MyPy, or Pyright errors.
- [ ] Three-tier testing complete (unit + functional + integration) with `@pytest.mark.*` markers.
- [ ] Coverage targets met: backend services 90%+, frontend components 80%+, hooks 85%+.
- [ ] No cross-feature frontend imports introduced (S5).
- [ ] All `data-testid` attributes follow S6 conventions.
- [ ] PII masking on all INFO-level logs (S3, S15).
- [ ] Memory updated: replace prior in-app TTP / Stripe Dashboard app memory entries with "Stripe payments live via Payment Links over SMS; M2 hardware shelved; reconciliation deterministic via metadata.invoice_id."

---

## OPERATIONAL RUNBOOK (excerpt — full file at `docs/payments-runbook.md`)

### Monitoring
- **Daily:** spot-check 5 random PAID invoices against Stripe Dashboard charges.
- **Weekly:** review `payment_link_sent_count` vs paid count to compute conversion rate. Investigate if rate drops.
- **On-call alerts:** any `charge.dispute.created` should page admin (Stripe deadline ~7 days to respond).

### Resending a payment link
- Office or tech opens the invoice (Appointment Modal or Invoice Detail) → "Resend Payment Link." Same backend endpoint. SMS goes again.

### Customer says they didn't get a receipt
- Resend from Stripe Dashboard → charge detail → "Resend receipt" (with optional updated email). **No Grin's-side action.**

### Refunds
- Always initiated from Stripe Dashboard. Webhook auto-reconciles to invoice (REFUNDED for full, PARTIAL for partial).

### Disputes
- Respond inside Stripe Dashboard. Update Grin's invoice notes manually if needed. Stripe deadline is hard.

### Webhook secret rotation
1. Stripe Dashboard → Developers → Webhooks → Endpoint → "Roll secret."
2. Update `STRIPE_WEBHOOK_SECRET` in Railway env.
3. Restart backend.
4. Test with `stripe trigger payment_intent.succeeded`.

### Stripe API version bump
- Pin in `StripeSettings.stripe_api_version`. Bumping is a deliberate PR with regression tests against new event shapes.

### When the auto-create-link hook fails on invoice creation
- Log entry `payment_link.create_failed_at_invoice_creation`. The link gets created on first `send-link` attempt instead. No manual action needed; just check Stripe API status if seeing many failures.

### Adding a new tech
- Tech needs only a Grin's account. **No Stripe Dashboard access required** under Architecture C. Just standard onboarding.

---

## NOTES

### Why this is the right shape

- **Smaller surface area** than Architecture B by roughly 30%. No description-regex matcher, no customer-fallback logic, no unmatched-charges admin queue, no Stripe Dashboard app training.
- **Deterministic reconciliation.** Every charge ties back to an invoice via `metadata.invoice_id` we set ourselves. Mismatches are bugs, not typos.
- **Customer-first UX.** Apple Pay / Google Pay are the dominant in-person payment modes in 2026 — Payment Links use them by default with no extra work.
- **Zero PCI scope.** Stripe-hosted page; we never touch card data.
- **Remote payments work for free.** Same flow as in-person; tech can leave before the customer pays. Admin can re-send links from the office.
- **Reminder integration is a force multiplier.** Every overdue reminder becomes a one-tap path to payment.

### Trade-offs we're accepting

- **Customer must do the work to pay** (vs. handing over a card). Mitigated by ubiquity of mobile wallets in 2026.
- **No physical-card-in-hand path.** A small fraction of customers want to hand over a card; under Architecture C, those use cash/check/Venmo/Zelle or wait for the link.
- **Cell signal dependency at the customer site.** Usually fine; rural service calls could be sketchy. Mitigation: tech can read the URL aloud or the customer can pay later from home.

### Future considerations (not in this PR)

- **QR code on invoice PDF** — for customers who'd rather scan than tap an SMS link.
- **Stripe Tax** — apply Stripe Tax to charges; reconcile tax lines into invoice.
- **Capacitor wrapper for in-app Tap to Pay** — if customer demand for physical-card-in-hand becomes loud enough. The deprecated `services/stripe_terminal.py` remains in place for that future.
- **Bulk send links** for customers with multiple unpaid invoices.
- **`charge.dispute.closed` and `charge.dispute.funds_withdrawn`** for full dispute lifecycle.
- **SMS receipts** in addition to Stripe's auto-email receipts.
- **Custom receipt branding via Resend** instead of Stripe's templates.
- **Removing legacy `stripe_terminal.py` and `api/v1/stripe_terminal.py`** in a separate cleanup PR once confirmed no Capacitor work is upcoming.
- **Multi-invoice combined link** ("Pay all 3 of your unpaid invoices at once").

### Confidence

- **Plan accuracy:** **10/10** — every file reference, function name, line number, import path, exception name, query-key prefix, and SDK signature verified by direct read or grep on 2026-04-28. Every Stripe behavior verified against official docs and the live sandbox account. All previously-deferred "verify before implementing" items collapsed into the **Verified Code-Level Findings** section (F1–F15).
- **One-pass implementation success:** **10/10** — every previously-flagged risk now closed with a concrete answer in the plan, not a TODO:

| Risk | Resolution |
|---|---|
| Decimal-to-cents edge cases in `_build_line_items` | F2 + Task 2.4 — concrete code stub handling both legacy `{description, amount}` and Pydantic `{description, quantity, unit_price, total}` JSONB shapes. |
| Idempotency of existing `create_invoice_from_appointment` | F1 confirmed NOT idempotent; Task 2.4a adds the explicit fix using already-existing `_find_invoice_for_job` at `appointment_service.py:2719`. |
| Cross-feature query-key imports | F14 (revised) — forbidden by S5; partial-key invalidation pattern with verified prefix strings (`['invoices']`, `['customer-invoices']`, `['appointments']`) per F15. |
| `$0` invoice edge case | F11 + Task 2.4 — explicit skip; edge case 31. |
| Opt-in flags vs transactional sends | F12 — transactional bypass with TCPA/CAN-SPAM rationale; edge cases 32–34 simplified. |
| Lying docstring on `create_invoice_from_appointment` | F1 + Task 2.4a — explicit fix. |
| `MessageType.PAYMENT_LINK` does not exist | Task 2.7 pre-task — add to `schemas/ai.py:53`. |
| Hard-STOP exception name | F7 + F12 — verified `SMSConsentDeniedError` (NOT `ConsentHardStopError` as earlier draft assumed). |
| `SMSService.send()` exact signature (recipient, message_type, return type) | F7 — full signature pinned with `Recipient` dataclass at `services/sms/recipient.py:23`, `ConsentType` `Literal` at `services/sms/consent.py:36`. |
| Import path for `LoggerMixin` / `DomainLogger` / `set_request_id` | F15 — verified `from grins_platform.log_config` (NOT `grins_platform.logging` despite steering doc typo). |
| Pytest marker registration | F15 — codebase uses unregistered markers without warning; new tests just use `@pytest.mark.{unit,functional,integration}` with no extra config. |
| Test directory structure | F15 — `tests/{unit,functional,integration}/` all exist; flat `tests/test_*.py` is legacy. New tests go in tier subdirs. |
| `pi_*` reference search | CG-13 + Task 3.7a — explicit verification step + add `ILIKE` if missing. |
| Subscription-vs-PaymentIntent overlap | CG-7 + Task 2.10 — explicit short-circuit on `event.data.object.invoice` non-null. |
| Cancelled-while-pending race | CG-8 + Task 2.10 — explicit refusal + log + manual-refund alert. |
| Two-payment installment | CG-10 + Task 2.10 — matcher recognizes PARTIAL+balance state. |
| `AppointmentService.create_invoice_from_appointment` docstring is misleading | F1 + Task 2.4a — explicit replacement text. |
| `customer.stripe_customer_id` already exists | F1 + Phase 1 — no migration needed; `models/customer.py:111`. |
| `service_agreement.stripe_customer_id` divergence | F1 + CG-18 + Task 1.5 — audit + invariant. |
| Receipt branding sender | Phase 0 + CG-16 — DNS coordination steps. |
| Stripe API version pin | F6 — `2025-03-31.basil` matches what existing webhooks declare. Set in Railway. |
| Webhook handler placement in 1000-line file | Tasks 2.9–2.13 — explicit dispatch dict pattern, not if/elif chain. |

- **Operational success after rollout:** **9/10** — ceiling is customer behavior (will they tap the link?). Implementation ceiling is 10. Conversion target ≥70% paid/sent; reminder integration (Phase 4) injects link into every overdue reminder for natural lift. Below 70% → investigate template wording, customer phone-quality, etc.

### What an executor still has to validate at merge time (operational, not code)
- DKIM/SPF DNS propagation for the custom receipt sender domain (Phase 0 task) — DNS only, no code.
- Whether the user wants the prod-sandbox webhook events updated *before* deploying the code or *after* (decided by stakeholder, not the plan).
- Smoke test on real Stripe-CLI-driven event in dev after each phase merge (covered in Phase 6 script).
