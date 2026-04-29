# Feature: Stripe Payment Links — E2E Bug Resolution (2026-04-28 hunt)

The following plan should be complete, but it's important that you validate documentation and codebase patterns and task sanity before you start implementing.

Pay special attention to naming of existing utils, types, and models. Import from the right files etc.

## Feature Description

Resolve every open finding from the 2026-04-28 Stripe Payment Links E2E bug hunt (`bughunt/2026-04-28-stripe-payment-links-e2e-bugs.md`). Bug 1 is already fixed in commit `102df83` (Alembic merge) — this plan retains its **process** follow-up (CI gate against multi-head). Bugs 2–7 are open. The work spans backend (FastAPI/SQLAlchemy/Pydantic), frontend (React/TanStack Query/types), test seeders, e2e shell scripts, deploy config, and a new pre-push/CI guardrail.

## User Story

As a developer working on the Grin's Irrigation Platform
I want the Stripe Payment Links flow to handle dev allowlist refusals, SMS/email fallback transparency, and CORS-on-5xx correctly, with seeders/E2E scripts that target the *right* fixtures
So that the dev backend stays reproducibly healthy, the frontend can show real failure reasons instead of opaque "Network Error" toasts, and CI/E2E runs catch regressions instead of masking them with green-but-wrong outcomes.

## Problem Statement

The 2026-04-28 E2E run uncovered:

| # | Severity | Title | Status |
|---|----------|-------|--------|
| 1 | P0 | Alembic multi-head crashed dev backend | **FIXED** (commit `102df83`) — only the **CI gate** remains |
| 2 | P1 | `send_payment_link` raises 500 on email-allowlist hard-block (should return spec'd 422 `NoContactMethodError`) | open |
| 3 | P1 | SMS soft-fail silently falls through to email even when SMS is the dev's allowlisted channel; response gives no signal | open |
| 4 | P2 | CORS headers absent on 5xx responses → frontend sees opaque `Network Error` instead of the real status/body | open |
| 5 | P2 | `seed_e2e_payment_links.py` reuses a customer found by phone but doesn't refresh `email`/opt-ins, bypassing the allowlist test invariant | open |
| 6 | P3 | `e2e/payment-links-flow.sh` Journey 1 clicks the *first* `.fc-event`, not the seeded appointment; tests an unrelated invoice and produces a misleading PASS | open |
| 7 | P3 | Railway dev `serviceManifest.build.builder = "RAILPACK"` while build actually consumed the in-repo `Dockerfile` (cosmetic but cost ~10 min triage) | open |

These bite the dev/E2E loop: Bug 4 hides Bug 2, Bug 3 masks both, and Bugs 5/6 produce false-green smoke runs.

## Solution Statement

Apply the surgical fixes called out in the bughunt's "Suggested fix" sections, paired with new tests and observability hooks:

1. **Bug 2** — wrap `_send_email` in `try/except EmailRecipientNotAllowedError` inside `InvoiceService.send_payment_link`, log a structured warning, fall through to the existing `NoContactMethodError` 422 path. Add unit + integration coverage.
2. **Bug 3** — extend `SendLinkResponse` (backend Pydantic + frontend TS) with `attempted_channels: list[Literal["sms", "email"]]` and `sms_failure_reason: Literal["consent", "rate_limit", "provider_error", "no_phone"] | None`. Plumb the reason through the SMS branch, render it in the toast on `PaymentCollector.tsx` and `InvoiceDetail.tsx`.
3. **Bug 4** — fix middleware ordering and add a top-level `Exception` handler that returns a JSON 500 (so `CORSMiddleware` wraps the response). Single global fix.
4. **Bug 5** — patch the seeder's reuse branch to PUT `{email, email_opt_in, sms_opt_in}` after lookup so the test invariants hold across runs.
5. **Bug 6** — make `payment-links-flow.sh` Journey 1 navigate to `/schedule?focus=$APPOINTMENT_ID` and click `[data-testid='fc-event-{id}']`. Add the `data-testid` on the calendar event renderer in the frontend.
6. **Bug 7** — pin Railway service builder back to `DOCKERFILE` (manual Railway-side action; documented in `docs/payments-runbook.md` as a one-time operational step).
7. **Bug 1 follow-up** — add a pre-push hook (Husky) **and** a `scripts/check-alembic-heads.sh` script invoked by both pre-push and CI to fail when `uv run alembic heads | wc -l != 1`. (Repo has no `.github/workflows/`; this plan adds one minimal workflow file alongside the script.)

## Feature Metadata

**Feature Type**: Bug Fix (multi-bug bundle)
**Estimated Complexity**: Medium — 7 distinct findings across 3 layers (backend, frontend, infra)
**Primary Systems Affected**:
- `services/invoice_service.py` (send_payment_link logic)
- `services/email_service.py` (exception import)
- `schemas/invoice.py` (`SendLinkResponse` shape)
- `app.py` (middleware/exception handler)
- `frontend/src/features/invoices/types/index.ts` (TS shape mirror)
- `frontend/src/features/schedule/components/PaymentCollector.tsx` + `frontend/src/features/invoices/components/InvoiceDetail.tsx` (toast rendering)
- `frontend/src/features/schedule/components/CalendarView.tsx` (or wherever `.fc-event` is rendered) — add `data-testid`
- `scripts/seed_e2e_payment_links.py` (seeder reuse branch)
- `e2e/payment-links-flow.sh` (Journey 1 selector)
- New: `scripts/check-alembic-heads.sh`, `.husky/pre-push`, `.github/workflows/alembic-heads.yml`
- `docs/payments-runbook.md` (Railway builder pin note)

**Dependencies**: No new runtime libraries. Husky (already implied by `package.json` if present — verify; otherwise install as devDependency in repo root). All fixes use existing `structlog`, `pydantic`, FastAPI, sonner toasts, and `agent-browser`.

---

## CONTEXT REFERENCES

### Relevant Codebase Files — IMPORTANT: YOU MUST READ THESE BEFORE IMPLEMENTING

- `bughunt/2026-04-28-stripe-payment-links-e2e-bugs.md` (full file, 442 lines) — Why: source of truth for every bug; quotes the exact log lines, traces, and suggested fixes. Read this end-to-end first.
- `src/grins_platform/services/invoice_service.py` (lines 902–1020) — Why: `send_payment_link` method with the SMS branch (961–994), email fallback (996–1013), and final `NoContactMethodError` (1015–1020). The Bug 2 fix slots between lines 1002 and 1012; the Bug 3 fix threads `attempted_channels` + `sms_failure_reason` through the existing branch points.
- `src/grins_platform/services/invoice_service.py` (lines 1098–1113) — Why: `_record_link_sent` increments `payment_link_sent_count`. Update its signature (or the caller) to accept the new metadata so the response carries `attempted_channels`.
- `src/grins_platform/services/email_service.py` (lines 55–112) — Why: defines `EmailRecipientNotAllowedError` (line 58) and the `_validate_email_recipient` guard that raises it (line 112). This is the exception we must catch.
- `src/grins_platform/services/email_service.py` (line 222) — Why: `_send_email` definition. Confirm signature so the `# noqa: SLF001` callsite stays valid.
- `src/grins_platform/services/sms_service.py` (lines 160–172) — Why: `SMSError`, `SMSConsentDeniedError`, `SMSRateLimitDeniedError`. The Bug 3 mapping is: consent→`"consent"`, rate-limit→`"rate_limit"`, other `SMSError`→`"provider_error"`, missing phone→`"no_phone"`, soft `result["success"] is False`→`"provider_error"` with `status` from `result`.
- `src/grins_platform/api/v1/invoices.py` (lines 723–767) — Why: `send_payment_link` route handler. No changes needed for Bug 2 (the existing `NoContactMethodError` → 422 branch covers it once the service catches the email exception). Verify imports.
- `src/grins_platform/schemas/invoice.py` (lines 636–649) — Why: `SendLinkResponse` Pydantic model — extend with `attempted_channels` and `sms_failure_reason`.
- `src/grins_platform/app.py` (lines 78–273) — Why: app factory + middleware order + exception handlers. **Critical:** `CORSMiddleware` is added first at lines 221–228 → in Starlette, the *last* added middleware runs *outermost*. `RequestSizeLimitMiddleware` and `SecurityHeadersMiddleware` are added after, so they wrap CORS, but `ServerErrorMiddleware` is implicitly outermost → 500s skip CORS. Bug 4 fix: add a `@app.exception_handler(Exception)` that returns a `JSONResponse` (CORS middleware honors `JSONResponse`). Place it at the end of `_register_exception_handlers` so it doesn't shadow the typed handlers.
- `src/grins_platform/exceptions/__init__.py` — Why: barrel for typed exceptions. `NoContactMethodError`, `LeadOnlyInvoiceError`, `InvoiceNotFoundError`, `InvalidInvoiceOperationError` already imported here. No changes needed; we don't add a new exception, we just catch one.
- `src/grins_platform/tests/unit/test_invoice_service_send_link.py` (lines 1–100, full file) — Why: existing unit test fixtures (`_make_invoice`, `_make_customer`, `_build_service`) for the send-link flow. Mirror these for the new tests.
- `frontend/src/features/invoices/types/index.ts` (lines 255–261) — Why: TS mirror of `SendLinkResponse`. Must stay in sync with backend Pydantic model.
- `frontend/src/features/invoices/api/invoiceApi.ts` (lines 18, 74–76) — Why: `sendPaymentLink` API call returning the typed response.
- `frontend/src/features/invoices/hooks/useInvoiceMutations.ts` (around line 95) — Why: `useSendPaymentLink` hook (TanStack mutation). Result already typed; only consumers need updating.
- `frontend/src/features/invoices/components/InvoiceDetail.tsx` (lines 51, 69–71) — Why: toast on success — `Payment Link sent via ${channelLabel}`. Update to surface `sms_failure_reason` when fallback occurred.
- `frontend/src/features/schedule/components/PaymentCollector.tsx` (lines 159–169) — Why: same toast on the modal path. Mirror the InvoiceDetail update.
- `frontend/src/features/schedule/components/PaymentCollector.test.tsx` — Why: existing test surface; add a case asserting the fallback toast description.
- `frontend/src/features/invoices/hooks/useSendPaymentLink.test.tsx` — Why: existing hook test. Extend to cover the new fields.
- `scripts/seed_e2e_payment_links.py` (lines 47–73) — Why: Bug 5 site. The `existing` reuse branch returns the customer ID without normalizing test fields.
- `e2e/payment-links-flow.sh` (lines 67–108) — Why: Bug 6 site. The `ab eval "..."` selector falls back to the first `.fc-event`. Replace with a deep link + `data-testid` lookup.
- `frontend/src/features/schedule/components/CalendarView.tsx` (and any FullCalendar `eventContent` / `eventDidMount` callback) — Why: where to add `data-testid="fc-event-{appointmentId}"`. **Read this file fully before editing** — the project may already render events via a custom React component returned from `eventContent`. Use `Grep` to locate the FullCalendar `events` prop wiring.
- `Dockerfile` (lines 1–60) — Why: confirms the build is Dockerfile-based; Bug 7 is purely a Railway dashboard config item (not a repo change).
- `alembic.ini` + `src/grins_platform/migrations/env.py` — Why: needed to wire `scripts/check-alembic-heads.sh` correctly (it must `cd` to the repo root and call `uv run alembic heads`).
- `.kiro/steering/code-standards.md`, `.kiro/steering/api-patterns.md`, `.kiro/steering/structure.md`, `.kiro/steering/tech.md`, `.kiro/steering/frontend-patterns.md`, `.kiro/steering/frontend-testing.md`, `.kiro/steering/agent-browser.md`, `.kiro/steering/spec-quality-gates.md`, `.kiro/steering/spec-testing-standards.md`, `.kiro/steering/devlog-rules.md`, `.kiro/steering/auto-devlog.md`, `.kiro/steering/parallel-execution.md`, `.kiro/steering/structure.md`, `.kiro/steering/vertical-slice-setup-guide.md`, `.kiro/steering/e2e-testing-skill.md` — Why: the steering rules below. Excluded from this plan: `.kiro/steering/kiro-cli-reference.md`, `.kiro/steering/knowledge-management.md`, `.kiro/steering/pre-implementation-analysis.md` (Kiro-CLI / Kiro-power-specific). Extracted directives that bind this plan are restated below in **Patterns to Follow**.

### New Files to Create

- `scripts/check-alembic-heads.sh` — Bug 1 follow-up: shell script that runs `uv run alembic heads --resolve-dependencies` and exits non-zero if more than one head is present. Used by pre-push hook and CI workflow.
- `.husky/pre-push` (or extend an existing one) — runs `bash scripts/check-alembic-heads.sh`. Only create if Husky is wired; otherwise the pre-push hook lives in `.git/hooks/pre-push` (sample existing) — but those aren't versioned. Preferred path: install `husky` as a root devDependency and commit `.husky/pre-push`.
- `.github/workflows/alembic-heads.yml` — single-job workflow: checkout, install uv, install backend deps, run `bash scripts/check-alembic-heads.sh`. Triggers on `pull_request` and `push` to `main`/`dev`. (Note: the repo currently has **no** `.github/workflows/`. Creating it is in scope.)
- `src/grins_platform/tests/unit/test_send_payment_link_email_allowlist.py` — Bug 2 unit test: `EmailRecipientNotAllowedError` from `_send_email` is caught and surfaces as `NoContactMethodError`.
- `src/grins_platform/tests/unit/test_send_payment_link_attempted_channels.py` — Bug 3 unit test: assert `attempted_channels` and `sms_failure_reason` shapes for the four SMS-failure modes (consent, rate-limit, provider-error, soft-fail).
- `src/grins_platform/tests/integration/test_send_payment_link_allowlist_integration.py` — Bug 2 integration test: hit `/api/v1/invoices/{id}/send-link` against a customer whose email is *not* in `EMAIL_TEST_ADDRESS_ALLOWLIST` and whose phone *is* in `SMS_TEST_PHONE_ALLOWLIST` but SMS will fail (mock provider) → assert HTTP 422 + `error.code = "NO_CONTACT_METHOD"`.
- `src/grins_platform/tests/integration/test_cors_on_5xx.py` — Bug 4 integration test: register a route via `app.dependency_overrides` that raises `RuntimeError("boom")`; assert the error response carries `Access-Control-Allow-Origin` header.

### Relevant Documentation — YOU SHOULD READ THESE BEFORE IMPLEMENTING

- [Starlette CORSMiddleware](https://www.starlette.io/middleware/#corsmiddleware) — Why: confirms that CORS headers are only set when the response is produced via a Starlette `Response`/`JSONResponse` returned through the middleware stack; raw exceptions bypass it unless caught upstream.
- [FastAPI Custom Exception Handlers](https://fastapi.tiangolo.com/tutorial/handling-errors/#install-custom-exception-handlers) — Why: documented mechanism for registering `@app.exception_handler(Exception)` to convert uncaught exceptions into `JSONResponse` so CORS middleware can wrap them. The handler must return a `JSONResponse`, not raise `HTTPException`.
- [FastAPI `add_middleware` ordering](https://fastapi.tiangolo.com/tutorial/middleware/) — Why: middleware added later runs outermost. Confirms our diagnosis that `CORSMiddleware` (added first in `app.py:221`) is *innermost* and so ends up underneath `ServerErrorMiddleware`. Either add CORS last or add an Exception handler.
- [Stripe Payment Links Webhook Best Practices](https://stripe.com/docs/payments/payment-links/webhooks) — Why: confirms that `payment_intent.succeeded` carries metadata; useful when verifying that Bug 6's deep-link change doesn't break the webhook reconciliation.
- [FullCalendar `eventDidMount` API](https://fullcalendar.io/docs/event-render-hooks#eventDidMount) — Why: lets us attach a `data-testid` attribute to `.fc-event` DOM nodes after FullCalendar renders them. Use `info.el.setAttribute('data-testid', \`fc-event-${info.event.id}\`)`.
- [Husky Setup](https://typicode.github.io/husky/) — Why: how to wire `.husky/pre-push`. Repo's `package.json` is currently a near-empty stub; we'll add `husky` and a `prepare` script.
- [Railway Builder Configuration](https://docs.railway.com/reference/build-configuration) — Why: the steps to switch the Railway service builder from RAILPACK to DOCKERFILE explicitly. **Manual** action — document, don't automate.
- [Sonner toast API](https://sonner.emilkowal.ski/) — Why: the project uses `toast.success(title, { description })`. Bug 3 fix uses `description` to show the SMS failure reason (matches existing pattern in `PaymentCollector.tsx:161-163`).

### Patterns to Follow

These are extracted from `.kiro/steering/` (excluding Kiro-CLI / knowledge / pre-implementation-Kiro-power docs) plus inspection of the surrounding code. **All new code must comply.**

**Naming Conventions** (`structure.md`, `tech.md`):
- Python: `snake_case.py`, tests `test_{module}.py`, classes `PascalCase`, functions/vars `snake_case`, constants `UPPER_SNAKE`.
- Frontend: components `PascalCase.tsx`, hooks `use{Name}.ts`, API `{feature}Api.ts`. Tests are co-located with the file under test.
- API endpoint event names: `{domain}.{component}.{action}_{state}` (e.g., `payment.send_link.email_blocked_by_allowlist`).

**Logging** (`code-standards.md`):
- Services use `LoggerMixin` (which `InvoiceService` already does — `self.log_started`, `self.log_rejected`, `self.log_failed`, `self.log_completed`). The new `try/except EmailRecipientNotAllowedError` block uses `self.logger.warning("payment.send_link.email_blocked_by_allowlist", ...)` — matches the existing `payment.send_link.sms_failed_soft` warning at line 978.
- Never log secrets or full PII. Email logging masks via `recipient_last4 = customer.email[-4:] if customer.email else None`.
- `DomainLogger.api_event` is for API endpoints — not needed here because the API handler in `invoices.py` doesn't add any new logging (it just keeps the existing typed exception → 4xx mapping).

**Error Handling** (`code-standards.md` §4 + `api-patterns.md`):
```python
try:
    result = self._process(data)
except ValidationError:
    raise  # already logged
except ExternalServiceError as e:
    self.log_failed("op", error=e)
    raise ServiceError(f"External failed: {e}") from e
```
- Bug 2 fix follows this: `EmailRecipientNotAllowedError` is treated as a *recoverable* condition that means "this dev customer is not deliverable via email" — we log it, set `email_sent=False`, and let the existing `NoContactMethodError` fire.

**Three-Tier Testing** (`code-standards.md` §2 + `tech.md` + `spec-testing-standards.md`):
- Unit tests in `src/grins_platform/tests/unit/` with `@pytest.mark.unit` (all mocked).
- Functional tests in `tests/functional/` with `@pytest.mark.functional` (real DB).
- Integration tests in `tests/integration/` with `@pytest.mark.integration` (full system).
- Test naming: `test_{method}_with_{condition}_returns_{expected}` (unit), `test_{workflow}_as_user_would_experience` (functional).
- Property-based tests via Hypothesis where invariants exist — for Bug 3, an invariant: `attempted_channels` always non-empty when the response is returned, and the last element matches the `channel` field.

**Frontend** (`frontend-patterns.md` + `frontend-testing.md`):
- Vertical Slice: features import from `core/` and `shared/` only. Never from each other.
- TanStack Query: use `useMutation` + `onSuccess` invalidations. `useSendPaymentLink` already follows this — only consumers (`InvoiceDetail.tsx`, `PaymentCollector.tsx`) need updates.
- `data-testid` convention: `{feature}-page`, `{feature}-table`, `{action}-{feature}-btn`. Bug 6's new attribute follows the spirit: `fc-event-{id}` — descriptive and stable.
- Toasts: `toast.success(title, { description })` / `toast.error(title, { description: getErrorMessage(err) })`. Mirror existing `PaymentCollector.tsx:161-168`.
- Component tests use Vitest + RTL with `<QueryProvider>` wrapper.

**API** (`api-patterns.md`):
- Existing endpoint already follows the `set_request_id`/`clear_request_id` + typed-exception → HTTPException pattern. **No new logging required at the API layer for these bugs.**
- Response models use Pydantic `BaseModel`. Field descriptions are the docstring/`Field(description=...)` pattern (matches `SendLinkResponse:642-649`).

**E2E** (`e2e-testing-skill.md` + `agent-browser.md`):
- agent-browser commands: `open`, `wait --load networkidle`, `snapshot -i`, `click`, `fill`, `screenshot`, `set viewport`, `console`, `errors`, `close`. The script pattern of `ab() { agent-browser --session "$SESSION" "$@"; }` is preserved — only the selector changes for Bug 6.
- Screenshots organized in `e2e-screenshots/payment-links-architecture-c/` (existing convention).

**Spec/Quality Gates** (`spec-quality-gates.md` + `spec-testing-standards.md`):
- Even though this is a bug-fix bundle, it touches enough surface that the work must end with: zero ruff violations, zero mypy errors, zero pyright errors, all tests green, agent-browser smoke run passes, frontend ESLint + TS strict zero errors. Final task includes a DEVLOG entry per `devlog-rules.md` / `auto-devlog.md`.

**Devlog** (`devlog-rules.md` + `auto-devlog.md`):
- After completion, prepend an entry under `## Recent Activity` in `DEVLOG.md` with category `BUGFIX`, formatted per `devlog-rules.md`. New entries go at TOP, immediately after the header.

**Architecture / VSA** (`vertical-slice-setup-guide.md` + `structure.md`):
- All changes stay within existing slices: `services/invoice_service.py`, `schemas/invoice.py`, `api/v1/invoices.py`, `frontend/src/features/invoices/*`, `frontend/src/features/schedule/components/PaymentCollector.tsx`. No new top-level features needed; no shared/ extraction triggered (still 1 feature using these types).

**Parallel Execution** (`parallel-execution.md`):
- Within Phase 2 below, the SMS-fallback metadata work, the email-allowlist catch, and the seeder/E2E fixes are independent — they can be done concurrently if delegated to subagents. Tests run sequentially after the parallel phase. Within a single agent's session, do them in the strict order in **STEP-BY-STEP TASKS** below.

---

## IMPLEMENTATION PLAN

### Phase 1: Foundation — schema/types alignment

Get the response shape right before touching the service code, so every downstream change has a stable target.

**Tasks:**
- Extend `SendLinkResponse` Pydantic model with `attempted_channels` and `sms_failure_reason` fields (Bug 3 surface).
- Mirror in the frontend TS interface `SendPaymentLinkResponse`.

### Phase 2: Core Implementation — backend service + middleware fixes

**Tasks:**
- Bug 2: catch `EmailRecipientNotAllowedError` inside `send_payment_link`'s email branch, log structured warning, treat as `email_sent = False`.
- Bug 3: thread `attempted_channels` and `sms_failure_reason` through the SMS branch and into `_record_link_sent` (or its caller) so the `SendLinkResponse` carries them. Map exceptions/results: `SMSConsentDeniedError`→`"consent"`, `SMSRateLimitDeniedError`→`"rate_limit"`, other `SMSError`→`"provider_error"`, `result.success is False`→`"provider_error"`, missing phone→`"no_phone"`.
- Bug 4: register a top-level `@app.exception_handler(Exception)` returning `JSONResponse(status_code=500, content={"success": False, "error": {"code": "INTERNAL_ERROR", "message": "Internal server error"}})` so CORS headers wrap it. Log via the existing `logger.error("api.exception.unhandled", ...)` pattern.

### Phase 3: Frontend rendering + seeder + E2E script

**Tasks:**
- Bug 3 (frontend): update `SendPaymentLinkResponse` TS interface; surface `sms_failure_reason` in toast `description` on `PaymentCollector.tsx` and `InvoiceDetail.tsx`. When `attempted_channels.length > 1`, the toast description becomes e.g. `"Sent via email (SMS rate-limited; will retry shortly)"`.
- Bug 5: refresh email/opt-ins on the seeder reuse branch.
- Bug 6: add `data-testid="fc-event-{appointment.id}"` on the FullCalendar event renderer; rewrite `payment-links-flow.sh` Journey 1 to use `/schedule?focus=$APPOINTMENT_ID` and the new selector.

### Phase 4: Operational guardrails (Bug 1 follow-up + Bug 7)

**Tasks:**
- Add `scripts/check-alembic-heads.sh`.
- Wire it into `.husky/pre-push` and `.github/workflows/alembic-heads.yml`.
- Document the Railway "pin builder to DOCKERFILE" step in `docs/payments-runbook.md` (Bug 7).

### Phase 5: Tests, validation, devlog

**Tasks:**
- Add unit tests for the email-allowlist catch and the `attempted_channels`/`sms_failure_reason` matrix.
- Add integration test for the 422 contract.
- Add integration test asserting CORS-on-5xx.
- Update existing tests in `test_invoice_service_send_link.py` to assert the new response fields.
- Run agent-browser E2E (`bash e2e/payment-links-flow.sh`) against the dev environment after re-seeding fixtures; capture fresh screenshots.
- Prepend `BUGFIX` entry in `DEVLOG.md` per `devlog-rules.md`.

---

## STEP-BY-STEP TASKS

IMPORTANT: Execute every task in order, top to bottom. Each task is atomic and independently testable.

### 1. UPDATE `src/grins_platform/schemas/invoice.py` — extend `SendLinkResponse`

- **IMPLEMENT**: Add two optional fields to the existing `SendLinkResponse` (lines 636–649):
  ```python
  attempted_channels: list[Literal["sms", "email"]] = Field(
      default_factory=list,
      description=(
          "Channels attempted in order. The last element equals `channel` "
          "on success. Useful for surfacing fallback context to the UI."
      ),
  )
  sms_failure_reason: Literal[
      "consent", "rate_limit", "provider_error", "no_phone"
  ] | None = Field(
      default=None,
      description=(
          "Reason the SMS branch failed when fallback to email succeeded. "
          "None when SMS succeeded or was not attempted."
      ),
  )
  ```
- **PATTERN**: Field-with-description matches the existing `channel`/`link_url`/`sent_at`/`sent_count` block at `schemas/invoice.py:642-649`.
- **IMPORTS**: `Literal` is **already** imported at `schemas/invoice.py:13` (`from typing import Literal`). No new import needed.
- **GOTCHA**: `default_factory=list` is required (mutable default rejected by Pydantic). Do not use `default=[]`.
- **VALIDATE**: `uv run ruff check src/grins_platform/schemas/invoice.py && uv run mypy src/grins_platform/schemas/invoice.py && uv run pyright src/grins_platform/schemas/invoice.py`

### 2. UPDATE `frontend/src/features/invoices/types/index.ts` — mirror new fields

- **IMPLEMENT**: Update the `SendPaymentLinkResponse` interface at lines 255–261:
  ```ts
  export interface SendPaymentLinkResponse {
    channel: 'sms' | 'email';
    link_url: string;
    sent_at: string;
    sent_count: number;
    attempted_channels: Array<'sms' | 'email'>;
    sms_failure_reason:
      | 'consent'
      | 'rate_limit'
      | 'provider_error'
      | 'no_phone'
      | null;
  }
  ```
- **PATTERN**: Field naming/casing exactly mirrors the Pydantic model (snake_case on the wire). Matches the existing `MassNotifyResponse`/`LienCandidate` patterns above/below in the same file.
- **IMPORTS**: None added; pure type extension.
- **GOTCHA**: `null` (not `undefined`) because the API returns JSON `null` from the optional Pydantic field.
- **VALIDATE**: `cd frontend && npx tsc -p tsconfig.app.json --noEmit`

### 3. UPDATE `src/grins_platform/services/invoice_service.py` — Bug 2 + Bug 3 service-side changes

- **IMPLEMENT**:
  1. Add a **runtime** import (not under TYPE_CHECKING) right after the existing runtime imports at line 47, before the `if TYPE_CHECKING:` block at line 49. Confirmed surface: `services/email_service.py:58` defines `class EmailRecipientNotAllowedError(Exception)`; the email_service module does not import from `invoice_service` so there is no circular-import risk.
     ```python
     from grins_platform.services.email_service import EmailRecipientNotAllowedError
     ```
     **Do not** add this under `TYPE_CHECKING` — the `except` clause needs the symbol at runtime. The existing `from grins_platform.services.email_service import EmailService` at line 58 lives under TYPE_CHECKING because the service is only used as a constructor type-hint; this new import is different.
  2. Inside `send_payment_link` (current line range 902–1020), introduce two locals at the top of the method body (after the lazy-create block, before line 958):
     ```python
     attempted_channels: list[Literal["sms", "email"]] = []
     sms_failure_reason: Literal["consent", "rate_limit", "provider_error", "no_phone"] | None = None
     ```
  3. In the SMS branch (current 961–994), append `"sms"` to `attempted_channels` immediately after entering the `if customer.phone and self.sms_service is not None:` block. If `customer.phone is None`, set `sms_failure_reason = "no_phone"` (do NOT append "sms" — the channel was not attempted).
  4. On `result.get("success") is True` (line 976), pass `attempted_channels` and `sms_failure_reason` to `_record_link_sent`. Map results before the `return`:
     - `SMSConsentDeniedError` caught → `sms_failure_reason = "consent"`
     - `SMSRateLimitDeniedError` caught → `sms_failure_reason = "rate_limit"` ⚠ **must be a separate `except` clause that comes BEFORE `except SMSError`** since `SMSRateLimitDeniedError` subclasses `SMSError` (verified at `sms_service.py:172`). Today, lines 989–994 catch them together as `except (SMSRateLimitDeniedError, SMSError)` — split into two clauses so the failure-reason label is precise.
     - generic `SMSError` caught (after the rate-limit clause) → `sms_failure_reason = "provider_error"`
     - `result.get("success") is False` (soft fail) → `sms_failure_reason = "provider_error"` (the `status` field comes through in the existing log; the user-facing label stays `"provider_error"`)
  5. Wrap the existing `_send_email` call (line 1002) in try/except (Bug 2):
     ```python
     attempted_channels.append("email")
     try:
         sent = self.email_service._send_email(  # noqa: SLF001 — established pattern
             to_email=customer.email,
             subject=(
                 f"Your invoice from Grin's Irrigation — ${invoice.total_amount}"
             ),
             html_body=html_body,
             text_body=text_body,
             email_type="payment_link",
             classification=EmailType.TRANSACTIONAL,
         )
     except EmailRecipientNotAllowedError:
         self.logger.warning(
             "payment.send_link.email_blocked_by_allowlist",
             invoice_id=str(invoice.id),
             recipient_last4=(customer.email[-4:] if customer.email else None),
         )
         sent = False
     ```
  6. Pass `attempted_channels` and `sms_failure_reason` into `_record_link_sent` for both the SMS-success (977) and email-success (1013) paths.
- **PATTERN**: Mirrors existing `payment.send_link.sms_failed_soft` warning logging at lines 978–982 and the `# noqa: SLF001` annotation already used at the same callsite.
- **IMPORTS**: `Literal` from `typing`, `EmailRecipientNotAllowedError` from `grins_platform.services.email_service`. Both add to existing import blocks; **verify by reading the top of the file first**.
- **GOTCHA**:
  - The existing handlers already catch `SMSConsentDeniedError`, `SMSRateLimitDeniedError`, and `SMSError`. Don't add new `try/except` blocks — set `sms_failure_reason` *inside* the existing handlers.
  - The soft-fail branch (lines 978–982) **does not** raise — just logs and falls through. Set `sms_failure_reason = "provider_error"` right before the existing log call so the variable is set if we proceed to the email branch.
  - `# noqa: SLF001` must remain — this is the established cross-service pattern for calling the underscored `_send_email`.
- **VALIDATE**:
  - `uv run ruff check src/grins_platform/services/invoice_service.py`
  - `uv run mypy src/grins_platform/services/invoice_service.py`
  - `uv run pyright src/grins_platform/services/invoice_service.py`

### 4. UPDATE `src/grins_platform/services/invoice_service.py` — `_record_link_sent` signature

- **IMPLEMENT**: Extend `_record_link_sent` (around line 1098) to accept `attempted_channels: list[str]` and `sms_failure_reason: str | None`, and include them in the returned `SendLinkResponse`. Existing callers updated in Task 3.
- **PATTERN**: Method already constructs and returns `SendLinkResponse` — just plumb the new fields through. Keep keyword-only args (`*,` separator) for clarity if not already present.
- **IMPORTS**: None new.
- **GOTCHA**: Callers in Task 3 use the same names. Don't introduce a default value for `attempted_channels` — make it required so the type checker enforces the wiring. `sms_failure_reason` defaults to `None`.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_invoice_service_send_link.py -v` — existing tests must still pass after fixture updates in Task 11.

### 5. UPDATE `src/grins_platform/app.py` — Bug 4: top-level Exception handler

- **IMPLEMENT**: At the END of `_register_exception_handlers` (after the WebAuthn handlers, just before the closing of the function), register:
  ```python
  @app.exception_handler(Exception)  # type: ignore[untyped-decorator]
  async def unhandled_exception_handler(
      request: Request,
      exc: Exception,
  ) -> JSONResponse:
      """Last-resort handler so 5xx responses carry CORS headers.

      Without this, Starlette's ServerErrorMiddleware emits the response
      *outside* CORSMiddleware and the browser sees an opaque CORS error
      instead of the real 500. (bughunt 2026-04-28 §Bug 4.)
      """
      logger.error(
          "api.exception.unhandled",
          path=request.url.path,
          method=request.method,
          error=str(exc),
          exc_type=type(exc).__name__,
          exc_info=exc,
      )
      return JSONResponse(
          status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
          content={
              "success": False,
              "error": {
                  "code": "INTERNAL_ERROR",
                  "message": "Internal server error",
              },
          },
      )
  ```
- **PATTERN**: Same shape as every other typed handler in the file (e.g., `customer_not_found_handler` at line 283); only the exception type and status differ.
- **IMPORTS**: `Request`, `JSONResponse`, `status`, and `logger` are already imported at the top of `app.py`.
- **GOTCHA**:
  - Place this **last** in `_register_exception_handlers` so the typed handlers (which match more specifically) still take precedence.
  - Do NOT broaden the existing `PydanticValidationError` or `ValidationError` handlers — keep the typed paths intact.
  - This ALSO covers the FastAPI default 500 path. Verify by running the integration test in Task 12.
- **VALIDATE**: `uv run mypy src/grins_platform/app.py && uv run pyright src/grins_platform/app.py && uv run ruff check src/grins_platform/app.py`

### 6. UPDATE `frontend/src/features/invoices/components/InvoiceDetail.tsx` — surface fallback reason in toast

- **IMPLEMENT**: Replace lines 69–71 (`const result = await sendPaymentLinkMutation.mutateAsync(invoice.id);` / `const channelLabel = ...` / `toast.success(...)`) with:
  ```ts
  const result = await sendPaymentLinkMutation.mutateAsync(invoice.id);
  const channelLabel = result.channel === 'sms' ? 'SMS' : 'email';
  const description =
    result.attempted_channels.length > 1 && result.sms_failure_reason
      ? `Sent via ${channelLabel} (SMS ${humanizeSmsFailure(result.sms_failure_reason)})`
      : `Sent via ${channelLabel}`;
  toast.success('Payment Link sent', { description });
  ```
  Add a tiny helper at the top of the file (or a local `const` map):
  ```ts
  const SMS_FAILURE_LABEL: Record<NonNullable<SendPaymentLinkResponse['sms_failure_reason']>, string> = {
    consent: 'opted out',
    rate_limit: 'rate-limited; retrying shortly',
    provider_error: 'provider error; will retry',
    no_phone: 'no phone on file',
  };
  const humanizeSmsFailure = (r: NonNullable<SendPaymentLinkResponse['sms_failure_reason']>) => SMS_FAILURE_LABEL[r];
  ```
- **PATTERN**: Matches `PaymentCollector.tsx:161-163` `toast.success(title, { description })` pattern.
- **IMPORTS**: `import type { SendPaymentLinkResponse } from '@/features/invoices/types';` if not already imported.
- **GOTCHA**: Don't show `sms_failure_reason` when `attempted_channels.length === 1` (SMS happy path) or when `sms_failure_reason === null`. Both cases collapse to the simpler `Sent via SMS`/`Sent via email` toast.
- **VALIDATE**: `cd frontend && npm test -- InvoiceDetail` (existing tests should still pass; we'll add a new one in Task 13).

### 7. UPDATE `frontend/src/features/schedule/components/PaymentCollector.tsx` — same fallback toast wiring

- **IMPLEMENT**: Replace lines 159–169 with the same `description` logic as Task 6. Reuse the `humanizeSmsFailure`/`SMS_FAILURE_LABEL` helper — extract to `frontend/src/features/invoices/utils/smsFailureLabel.ts` and re-export from the feature index so both call sites import once.
- **PATTERN**: Cross-feature shared utility belongs in the slice that owns the type (`features/invoices/`), per `vertical-slice-setup-guide.md` ("Move to shared/ when 3+ features need it. Until then, duplicate." — here we have 2 callers, both consuming the invoices type, so the util lives in `features/invoices/utils/`).
- **IMPORTS**: `import { humanizeSmsFailure } from '@/features/invoices';`
- **GOTCHA**: `PaymentCollector.tsx` is in `features/schedule/`. It already imports from `@/features/invoices` types — re-exporting `humanizeSmsFailure` from the invoices index is consistent.
- **VALIDATE**: `cd frontend && npx tsc -p tsconfig.app.json --noEmit && npm test -- PaymentCollector`

### 8. UPDATE `frontend/src/features/schedule/components/CalendarView.tsx` — add `data-testid="fc-event-{id}"`

- **IMPLEMENT**: The FullCalendar JSX is at `CalendarView.tsx:416-466`. Events already have `id: appointment.id` set in the event mapping (verified at `CalendarView.tsx:162`), so the `data-testid` value is already known to FullCalendar. Add the `eventDidMount` prop to the `<FullCalendar …>` block (anywhere between lines 436 and 466), matching the existing prop style:
  ```tsx
  eventDidMount={(info) => {
    if (info.event.id) {
      info.el.setAttribute('data-testid', `fc-event-${info.event.id}`);
    }
  }}
  ```
- **PATTERN**: `data-testid` convention from `frontend-patterns.md` — descriptive, kebab-case, includes a stable identifier. Existing examples in the codebase: `[data-testid='appointment-modal']`, `[data-testid='collect-payment-cta']`, `[data-testid='send-payment-link-btn']`, `[data-testid='calendar-view']` (line 413).
- **IMPORTS**: None new — the closure types are inferred by `@fullcalendar/react`.
- **GOTCHA**:
  - **`eventDidMount`, NOT `eventContent`**: line 452 already uses `eventContent={renderEventContent}` to render the *inside* of each event card. `eventContent` returns React content (the inner div), so a `data-testid` on its return value would land on a child element, not the `.fc-event` wrapper. The `eventDidMount` hook gives access to `info.el` — the actual `.fc-event` DOM node — which is what the E2E selector targets.
  - The existing `CalendarView.test.tsx` mocks `@fullcalendar/react` (lines 67–86) and won't exercise `eventDidMount`. No test changes required for this task; the test surface is the E2E script in Task 9.
- **VALIDATE**: After edit, run the dev server (`./scripts/dev.sh`), open `/schedule`, inspect a calendar event in DevTools, confirm `data-testid="fc-event-<uuid>"` is on the `.fc-event` node. Also: `cd frontend && npx tsc -p tsconfig.app.json --noEmit && npm test -- CalendarView` (existing tests must still pass — they mock FullCalendar and don't touch `eventDidMount`).

### 9. UPDATE `e2e/payment-links-flow.sh` — Bug 6: target seeded appointment by id

- **IMPLEMENT**: Replace the Journey 1 block (lines 67–108) with the version below. **Note**: `?focus=` deep linking is NOT implemented in `SchedulePage.tsx` (verified — it handles `?scheduleJobId=` at lines 87–98 only). Since the seeder creates the appointment for *today* and the calendar opens to the current week (`weekStartsOn: 1` in `CalendarView.tsx:83`), the seeded appointment WILL be in the default week view — we just need to find it by the new `data-testid`:
  ```bash
  # Journey 1: Send Payment Link from Appointment Modal — target the seeded appointment by id.
  # Relies on the data-testid="fc-event-{id}" attribute added in Task 8.
  if [[ -z "${APPOINTMENT_ID:-}" ]]; then
    echo "SKIP Journey 1: APPOINTMENT_ID not set (re-seed via scripts/seed_e2e_payment_links.py)."
  else
    ab open "$BASE/schedule"
    ab wait --load networkidle
    sleep 3  # allow weekly schedule query + FullCalendar to render
    HIT=$(ab get count "[data-testid='fc-event-$APPOINTMENT_ID']")
    if [[ "$HIT" == "0" ]]; then
      echo "FAIL Journey 1: seeded appointment $APPOINTMENT_ID not in current week view."
      echo "  (Seeder creates today's appointment; if today is on a Mon-boundary"
      echo "   the click-through can lag — re-run after refresh.)"
      ab close
      exit 1
    fi
    ab click "[data-testid='fc-event-$APPOINTMENT_ID']"
    ab wait "[data-testid='appointment-modal']"
    ab screenshot "$SHOTS/02a-modal-opened.png"
    # The Send Payment Link button lives inside the Payment sheet — open it
    # via the Collect Payment CTA (only rendered when status is in_progress
    # or completed; the seeder walks the appointment to in_progress).
    CTA_COUNT=$(ab get count "[data-testid='collect-payment-cta']")
    if [[ "$CTA_COUNT" == "0" ]]; then
      echo "WARN Journey 1: Collect Payment CTA absent (appointment must be in_progress/completed)."
    else
      ab click "[data-testid='collect-payment-cta']"
      sleep 1
      ab screenshot "$SHOTS/02b-payment-sheet-open.png"
    fi
    SEND_COUNT=$(ab get count "[data-testid='send-payment-link-btn'], [data-testid='resend-payment-link-btn']")
    if [[ "$SEND_COUNT" == "0" ]]; then
      echo "WARN Journey 1: payment sheet has no Send/Resend Payment Link button."
    else
      if [[ $(ab get count "[data-testid='send-payment-link-btn']") -gt "0" ]]; then
        ab click "[data-testid='send-payment-link-btn']"
      else
        ab click "[data-testid='resend-payment-link-btn']"
      fi
      sleep 3
      ab screenshot "$SHOTS/03-modal-link-sent.png"
      sleep 8
      ab screenshot "$SHOTS/04-modal-paid.png"
    fi
  fi
  ```
  Also update the required-env-var preamble (lines 17–19) to add `APPOINTMENT_ID`.
- **PATTERN**: `--session "$SESSION"` and the `ab() { agent-browser --session "$SESSION" "$@"; }` wrapper at line 49 are preserved. Matches `e2e-testing-skill.md` workflow.
- **IMPORTS**: N/A (shell).
- **GOTCHA**:
  - **No `?focus=` handler exists** in the schedule route (verified `SchedulePage.tsx:78-98` only consumes `scheduleJobId`). Don't fabricate one. The test relies on the seeder placing the appointment in the *current* week — which is always true because the seeder uses `today = dt.date.today().isoformat()` (`seed_e2e_payment_links.py:53`).
  - The seeder must `print(f"APPOINTMENT_ID={appt_id}")` to stdout — Task 10 adds this. Then the caller does `eval $(python scripts/seed_e2e_payment_links.py 2>/dev/null)` to export it.
  - **Edge case** (documented in the WARN): if the appointment is created late on a Sunday near midnight, the calendar's "current week" can race with FullCalendar's internal week rollover. The 3 s `sleep` is a buffer; if it still misses, re-running fixes it. Not worth a tighter guard.
- **VALIDATE**: `bash -n e2e/payment-links-flow.sh` (syntax-only). Full E2E run is in Level 4 below.

### 10. UPDATE `scripts/seed_e2e_payment_links.py` — Bug 5: refresh on reuse + emit `APPOINTMENT_ID`

- **IMPLEMENT**: Replace the reuse branch at lines 56–60 with:
  ```python
  existing = call("GET", f"/customers/lookup/phone/{PHONE}", None, token)
  if isinstance(existing, list) and existing:
      customer_id = existing[0]["id"]
      call(
          "PUT",
          f"/customers/{customer_id}",
          {
              "email": EMAIL,
              "email_opt_in": True,
              "sms_opt_in": True,
          },
          token,
      )
      print(f"# customer {customer_id} (reused, refreshed)", file=sys.stderr)
  else:
      …  # existing create branch
  ```
  At the END of `main()` add a stable, parsable line on stdout (not stderr) so callers can `eval $(python scripts/seed_e2e_payment_links.py)`:
  ```python
  print(f"APPOINTMENT_ID={appt_id}")
  print(f"INVOICE_ID={inv_id}")
  print(f"ZERO_INVOICE_ID={zero_inv_id}")
  ```
- **PATTERN**: The seeder already mixes `print(..., file=sys.stderr)` (comments) with `print(...)` (machine-readable). Stick to that.
- **IMPORTS**: None new.
- **GOTCHA**:
  - The PUT may 422 if the API enforces an `expected_version`/optimistic-lock body. Read `api/v1/customers.py` PUT handler before deciding the payload. If it does, add `"expected_version": existing[0]["version"]`.
  - Don't overwrite `first_name`/`last_name` on reuse — the test invariants only need email + opt-ins.
- **VALIDATE**: `python scripts/seed_e2e_payment_links.py` against a dev backend; confirm stdout ends with the three `KEY=VALUE` lines and stderr shows `(reused, refreshed)` on the second run.

### 11. UPDATE `src/grins_platform/tests/unit/test_invoice_service_send_link.py` — assert new response fields

- **IMPLEMENT**: For every existing test in this file that asserts on the returned `SendLinkResponse`, also assert:
  - `result.attempted_channels == ["sms"]` for SMS-success cases.
  - `result.attempted_channels == ["email"]` for the customer-with-no-phone case.
  - `result.attempted_channels == ["sms", "email"]` and the matching `sms_failure_reason` for fallback cases.
  - `result.sms_failure_reason` is `None` for SMS-success cases.
- **PATTERN**: Existing fixtures `_make_invoice`, `_make_customer`, `_build_service` (lines 30–100) — extend rather than rewrite.
- **IMPORTS**: None new.
- **GOTCHA**: Tests that drive `sms_exc=SMSConsentDeniedError` should assert `sms_failure_reason == "consent"`; `SMSRateLimitDeniedError` → `"rate_limit"`; generic `SMSError` → `"provider_error"`.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_invoice_service_send_link.py -v`

### 12. CREATE `src/grins_platform/tests/unit/test_send_payment_link_email_allowlist.py` — Bug 2 unit coverage

- **IMPLEMENT**: New unit test using the same `_build_service` pattern as `test_invoice_service_send_link.py`. The mocked `email_service._send_email` raises `EmailRecipientNotAllowedError("blocked")`. Assert that:
  1. `InvoiceService.send_payment_link` raises `NoContactMethodError` (not the email exception, not a `RuntimeError`).
  2. The structured warning log `payment.send_link.email_blocked_by_allowlist` was emitted (use `caplog`/`structlog` capture per project pattern).
- **PATTERN**: Mirror the helpers from `test_invoice_service_send_link.py:30-100`.
- **IMPORTS**:
  ```python
  from grins_platform.services.email_service import EmailRecipientNotAllowedError
  from grins_platform.exceptions import NoContactMethodError
  ```
- **GOTCHA**: The mocked customer must have `email` set but `phone` set to a value that causes the SMS branch to fail (e.g., mock `sms_service.send_message` to return `{"success": False}`). Then the email branch is the next step.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_send_payment_link_email_allowlist.py -v`

### 13. CREATE integration test `src/grins_platform/tests/integration/test_send_payment_link_allowlist_integration.py`

- **IMPLEMENT**: Integration test marked `@pytest.mark.integration` that:
  1. Creates a customer via the real DB with `email = "test-mock@example.com"` (NOT in `EMAIL_TEST_ADDRESS_ALLOWLIST`) and a phone NOT in `SMS_TEST_PHONE_ALLOWLIST`.
  2. Creates a job + invoice via real factories.
  3. POSTs to `/api/v1/invoices/{id}/send-link` with admin auth.
  4. Asserts `response.status_code == 422` and `response.json()["error"]["code"]` indicates no contact method (match the existing `NoContactMethodError` exception handler shape).
- **PATTERN**: Follow `tests/integration/test_invoice_integration.py` for fixtures (auth, DB setup). Test naming: `test_send_link_blocks_when_email_allowlist_refuses_returns_422`.
- **IMPORTS**: TestClient/AsyncClient per existing integration tests.
- **GOTCHA**:
  - This test must set `EMAIL_TEST_ADDRESS_ALLOWLIST` and `SMS_TEST_PHONE_ALLOWLIST` env vars in the test fixture (or `monkeypatch`) — otherwise the guards don't activate.
  - Existing `test_send_payment_link*` integration tests can be a model — search `rg -l "send_payment_link" src/grins_platform/tests/integration` first.
- **VALIDATE**: `uv run pytest -m integration -v src/grins_platform/tests/integration/test_send_payment_link_allowlist_integration.py`

### 14. CREATE integration test `src/grins_platform/tests/integration/test_cors_on_5xx.py`

- **IMPLEMENT**: Test that registers a temporary route (or uses `app.dependency_overrides` to make `health_check` raise `RuntimeError("intentional")`), then `client.get("/health", headers={"Origin": "http://localhost:5173"})`. Assert:
  1. `response.status_code == 500`.
  2. `response.headers.get("access-control-allow-origin") == "http://localhost:5173"`.
  3. `response.json()["error"]["code"] == "INTERNAL_ERROR"`.
- **PATTERN**: Follow the typed-exception integration tests in `tests/integration/`.
- **IMPORTS**: `from fastapi.testclient import TestClient`. Use `app.dependency_overrides` or define a tiny test-only route via a fixture; do NOT modify `app.py` to add a test route.
- **GOTCHA**: The CORS middleware is configured to honor an exact origin list. Use `http://localhost:5173` (in the default origins per `app.py:186-193`).
- **VALIDATE**: `uv run pytest -m integration -v src/grins_platform/tests/integration/test_cors_on_5xx.py`

### 15. CREATE `frontend/src/features/invoices/components/InvoiceDetail.test.tsx` — toast description coverage (or extend existing)

- **IMPLEMENT**: Add a Vitest case that mocks `sendPaymentLink` to resolve with `{ channel: 'email', attempted_channels: ['sms', 'email'], sms_failure_reason: 'rate_limit', ... }`. Assert that `toast.success` was called with `description` matching `/SMS rate-limited/`. Use `vi.spyOn` on the sonner module or render with a stub. If `InvoiceDetail.test.tsx` does not exist, create it; otherwise add a `describe('Send Payment Link', ...)` block.
- **PATTERN**: `frontend-testing.md` Component Test pattern — render with `<QueryProvider>` wrapper.
- **IMPORTS**: `import { toast } from 'sonner'; import { vi } from 'vitest';` etc.
- **GOTCHA**: Sonner's `toast` is module-scoped — mock with `vi.mock('sonner', () => ({ toast: { success: vi.fn(), error: vi.fn() } }));`.
- **VALIDATE**: `cd frontend && npm test -- InvoiceDetail`

### 16. UPDATE `frontend/src/features/schedule/components/PaymentCollector.test.tsx` — fallback toast assertion

- **IMPLEMENT**: Add a test mirroring Task 15 against `PaymentCollector.tsx`.
- **PATTERN**: Same as Task 15.
- **IMPORTS**: Same.
- **GOTCHA**: `PaymentCollector` already has tests — extend, don't replace.
- **VALIDATE**: `cd frontend && npm test -- PaymentCollector`

### 17. CREATE `scripts/check-alembic-heads.sh` — Bug 1 follow-up guardrail

- **IMPLEMENT**:
  ```bash
  #!/usr/bin/env bash
  # Fail if Alembic has more than one head. Bug 1 follow-up
  # (bughunt 2026-04-28) — see DEVLOG entry from this fix.
  set -euo pipefail
  cd "$(git rev-parse --show-toplevel)"
  HEADS=$(uv run alembic heads 2>/dev/null | grep -c '(head)' || true)
  if [[ "$HEADS" -ne 1 ]]; then
    echo "ERROR: alembic has $HEADS heads (expected 1). Create a merge revision:" >&2
    echo "  uv run alembic merge -m 'merge heads' <head1> <head2>" >&2
    uv run alembic heads >&2
    exit 1
  fi
  echo "OK: single alembic head."
  ```
  `chmod +x scripts/check-alembic-heads.sh`.
- **PATTERN**: Matches the `scripts/dev.sh`/`scripts/setup.sh` shell-script style (set -euo pipefail, plain bash).
- **IMPORTS**: N/A.
- **GOTCHA**: `uv run alembic heads` writes the head list to stdout. The `grep -c '(head)'` count is the canonical marker. Don't `wc -l` on raw output — it counts informational lines too.
- **VALIDATE**: `bash scripts/check-alembic-heads.sh` should print `OK: single alembic head.` on the current `dev` branch (because `102df83` already merged). Then introduce a fake second head locally (`uv run alembic revision -m "x"` with a wrong `down_revision`) and confirm the script exits non-zero. Revert the test revision.

### 18. CREATE `.github/workflows/alembic-heads.yml` — CI gate

- **IMPLEMENT**:
  ```yaml
  name: Alembic single-head check
  on:
    pull_request:
      branches: [main, dev]
    push:
      branches: [main, dev]
  jobs:
    alembic-heads:
      runs-on: ubuntu-latest
      steps:
        - uses: actions/checkout@v4
        - uses: astral-sh/setup-uv@v3
        - run: uv sync --frozen
        - run: bash scripts/check-alembic-heads.sh
  ```
- **PATTERN**: This is the first workflow in the repo — keep it minimal. Future workflows can add ruff/mypy/pyright/pytest gates.
- **IMPORTS**: N/A.
- **GOTCHA**:
  - Repo currently has **no** `.github/workflows/` directory. Create it.
  - `astral-sh/setup-uv` is the official action.
  - `uv sync --frozen` ensures `uv.lock` matches.
- **VALIDATE**: After push, GitHub Actions tab shows the workflow running and passing on a clean branch. Locally, the YAML parses with `yamllint .github/workflows/alembic-heads.yml` (if installed) or `python -c "import yaml; yaml.safe_load(open('.github/workflows/alembic-heads.yml'))"`.

### 19. SKIP — Husky local pre-push hook (deferred / out of scope)

- **DECISION**: Do **not** add Husky in this plan. Rely on the GitHub Actions workflow (Task 18) as the sole guard for Bug 1 follow-up.
- **WHY**:
  - Root `package.json` is currently a near-stub (`{"dependencies": {"vercel": "^50.28.0"}}`). The Vercel project (id `prj_SZexdljNexKryhM7PAJn3DQkDbSK`, per `.vercel/project.json`) builds frontend deploys from this checkout. Adding `husky` + a `prepare` script to root `package.json` would make Vercel run `npm install` against root and try to execute `husky install` during a production install — which fails because `.git` isn't present, breaking deploys.
  - Workarounds (a `prepare` script that no-ops outside git, or pinning Vercel rootDirectory to `frontend/`) introduce more risk than the bug being prevented. The CI workflow alone is sufficient: a multi-head can't reach `main`/`dev` without failing the workflow, and dev devs can run `bash scripts/check-alembic-heads.sh` manually if they want a local pre-push check.
- **WHAT TO DO INSTEAD**: Add a developer-facing line to `docs/payments-runbook.md` under the new "Railway service builder pin" section (Task 20):
  > **Optional local guard**: developers can manually wire a pre-push hook by symlinking the script into their local `.git/hooks/pre-push`:
  > `ln -s ../../scripts/check-alembic-heads.sh .git/hooks/pre-push && chmod +x .git/hooks/pre-push`
  > (not version-controlled; opt-in per developer.)
- **VALIDATE**: N/A — nothing to do in the repo. The CI workflow (Task 18) carries the load.

### 20. UPDATE `docs/payments-runbook.md` — Bug 7 operational note

- **IMPLEMENT**: Append a section "Railway service builder pin" with steps:
  1. Open Railway → `Grins-dev` → Settings → Build → set Builder to `DOCKERFILE` and Dockerfile path to `Dockerfile`.
  2. Repeat for the production service.
  3. Confirm by inspecting `serviceManifest.build` after the next deploy: `builder: "DOCKERFILE"`, `dockerfilePath: "Dockerfile"`.
  4. (Optional, per-developer) Add a local Alembic-heads pre-push guard:
     `ln -s ../../scripts/check-alembic-heads.sh .git/hooks/pre-push && chmod +x .git/hooks/pre-push`
- **PATTERN**: Match the existing `docs/payments-runbook.md` heading style and bullet structure.
- **IMPORTS**: N/A.
- **GOTCHA**: This is a **manual** Railway action — there is no API call to commit. Document only.
- **VALIDATE**: `markdownlint docs/payments-runbook.md` (if available) or visual review. The runbook is the artifact.

### 21. UPDATE `DEVLOG.md` — append BUGFIX entry per `devlog-rules.md`

- **IMPLEMENT**: Insert a new entry at the TOP of `DEVLOG.md`, immediately after the `## Recent Activity` header. Format per `devlog-rules.md`:
  ```markdown
  ## [2026-04-29 HH:MM] - BUGFIX: Stripe Payment Links E2E bug bundle (bughunt 2026-04-28)

  ### What Was Accomplished
  - Bug 2: `send_payment_link` now catches `EmailRecipientNotAllowedError` …
  - Bug 3: `SendLinkResponse` carries `attempted_channels` + `sms_failure_reason` …
  - Bug 4: top-level Exception handler emits JSON 500 so CORS headers wrap it …
  - Bug 5: seeder reuse branch refreshes email/opt-ins …
  - Bug 6: `payment-links-flow.sh` Journey 1 targets `[data-testid='fc-event-{id}']` via `?focus=` …
  - Bug 7: documented Railway DOCKERFILE-builder pin in payments runbook
  - Bug 1 follow-up: `scripts/check-alembic-heads.sh` + Husky pre-push + GitHub Actions workflow

  ### Technical Details
  - … (file paths + line numbers per Tasks 1–20)

  ### Decision Rationale
  - …

  ### Challenges and Solutions
  - …

  ### Next Steps
  - Re-run agent-browser smoke after Vercel/Railway re-deploy
  - Capture fresh `e2e-screenshots/payment-links-architecture-c/` set
  ```
- **PATTERN**: `devlog-rules.md` (entries at top, newest first, full structure with all five subsections).
- **IMPORTS**: N/A.
- **GOTCHA**: Keep timestamps in 24-hour local time; categories from `devlog-rules.md` Categories list (`BUGFIX`).
- **VALIDATE**: Visual review. Confirm the `## Recent Activity` header is preserved and the new entry is the first one beneath it.

---

## TESTING STRATEGY

Per `code-standards.md` §2 and `spec-testing-standards.md`:

### Unit Tests

- `test_invoice_service_send_link.py` — extend with `attempted_channels`/`sms_failure_reason` assertions for all 4 SMS-failure modes + happy path (Task 11).
- `test_send_payment_link_email_allowlist.py` — Bug 2 catch + structured-log assertion (Task 12).
- `InvoiceDetail.test.tsx` — toast description for fallback (Task 15).
- `PaymentCollector.test.tsx` — toast description for fallback (Task 16).

### Integration Tests

- `test_send_payment_link_allowlist_integration.py` — real DB + real handler returns 422 with `NoContactMethodError` shape when both channels are unreachable (Task 13).
- `test_cors_on_5xx.py` — middleware/handler emits CORS-wrapped 500 (Task 14).

### Edge Cases

- Customer has phone+email, both pass → `attempted_channels=["sms"]`, `sms_failure_reason=None`, channel=sms.
- Customer has no phone, has email allowed → `attempted_channels=["email"]`, `sms_failure_reason="no_phone"`, channel=email.
- Customer has phone (consent denied), email allowed → `attempted_channels=["sms","email"]`, `sms_failure_reason="consent"`, channel=email.
- Customer has phone (rate-limited), email allowed → `attempted_channels=["sms","email"]`, `sms_failure_reason="rate_limit"`, channel=email.
- Customer has phone (provider error), email allowed → `attempted_channels=["sms","email"]`, `sms_failure_reason="provider_error"`, channel=email.
- Customer has phone (soft-fail `success=false`), email allowed → same as provider_error.
- Customer has phone+email but email blocked by allowlist + SMS soft-fails → 422 `NoContactMethodError`.
- Customer has phone+email but neither service configured → 422 `NoContactMethodError`.
- 5xx response from any endpoint → CORS headers present, body shape `{"success": false, "error": {"code": "INTERNAL_ERROR", ...}}`.
- E2E seeder run twice → second run shows `(reused, refreshed)` and PUTs `email`/`email_opt_in`/`sms_opt_in`.
- Multi-head Alembic state → `scripts/check-alembic-heads.sh` exits non-zero with actionable error.

---

## VALIDATION COMMANDS

Per `tech.md` §"Quality Checks (all must pass with zero errors)" and `code-standards.md` §"Quality Commands".

### Level 1: Syntax & Style

```bash
uv run ruff check src/grins_platform/services/invoice_service.py \
                  src/grins_platform/schemas/invoice.py \
                  src/grins_platform/app.py \
                  src/grins_platform/tests/unit/test_invoice_service_send_link.py \
                  src/grins_platform/tests/unit/test_send_payment_link_email_allowlist.py \
                  src/grins_platform/tests/integration/test_send_payment_link_allowlist_integration.py \
                  src/grins_platform/tests/integration/test_cors_on_5xx.py
uv run ruff format --check src/grins_platform/
uv run mypy src/grins_platform/
uv run pyright src/grins_platform/services/invoice_service.py \
                src/grins_platform/schemas/invoice.py \
                src/grins_platform/app.py
cd frontend && npm run lint && npx tsc -p tsconfig.app.json --noEmit
bash -n e2e/payment-links-flow.sh
bash -n scripts/check-alembic-heads.sh
```

### Level 2: Unit Tests

```bash
uv run pytest -m unit -v \
  src/grins_platform/tests/unit/test_invoice_service_send_link.py \
  src/grins_platform/tests/unit/test_send_payment_link_email_allowlist.py
cd frontend && npm test -- --run src/features/invoices/components/InvoiceDetail \
                          src/features/schedule/components/PaymentCollector
```

### Level 3: Integration Tests

```bash
uv run pytest -m integration -v \
  src/grins_platform/tests/integration/test_send_payment_link_allowlist_integration.py \
  src/grins_platform/tests/integration/test_cors_on_5xx.py
```

### Level 4: Manual / agent-browser E2E Validation

Per `e2e-testing-skill.md` and `agent-browser.md`:

```bash
# 1. Re-seed dev fixtures (Bug 5 fix).
eval $(python scripts/seed_e2e_payment_links.py 2>/dev/null)
# expect APPOINTMENT_ID, INVOICE_ID, ZERO_INVOICE_ID exported

# 2. Run the full E2E flow (Bug 6 fix).
APPOINTMENT_ID=$APPOINTMENT_ID INVOICE_ID=$INVOICE_ID ZERO_INVOICE_ID=$ZERO_INVOICE_ID \
  bash e2e/payment-links-flow.sh

# 3. Manual cURL — confirm Bug 2 fix returns 422 (not 500).
curl -i -X POST -H "Authorization: Bearer $TOKEN" \
  https://grins-dev-dev.up.railway.app/api/v1/invoices/$BLOCKED_INVOICE_ID/send-link
# expect: HTTP/1.1 422 Unprocessable Entity
#         Access-Control-Allow-Origin: http://localhost:5173 (or the request origin)
#         {"success":false,"error":{"code":"NO_CONTACT_METHOD",...}}

# 4. Manual cURL with origin — confirm Bug 4 fix wraps 500s with CORS.
curl -i -H "Origin: http://localhost:5173" \
  https://grins-dev-dev.up.railway.app/__force-500
# expect: 500 + Access-Control-Allow-Origin header present + JSON body

# 5. Bug 1 guard — confirm script.
bash scripts/check-alembic-heads.sh
# expect: "OK: single alembic head."
```

### Level 5: Operational

- Push a branch and observe `.github/workflows/alembic-heads.yml` run + pass in GitHub Actions.
- Confirm `git push` triggers `.husky/pre-push`.
- Verify Railway deploy `serviceManifest.build.builder == "DOCKERFILE"` after the manual pin.

---

## ACCEPTANCE CRITERIA

- [ ] **Bug 2** — `POST /api/v1/invoices/{id}/send-link` returns HTTP 422 with `error.code` indicating no-contact-method (not 500) when both channels are unreachable; structured log `payment.send_link.email_blocked_by_allowlist` emitted on the email-allowlist refusal path. Unit + integration tests cover it.
- [ ] **Bug 3** — `SendLinkResponse` (backend) and `SendPaymentLinkResponse` (frontend) carry `attempted_channels` and `sms_failure_reason`. Toast on `InvoiceDetail` + `PaymentCollector` surfaces the fallback reason. All 5 SMS-failure modes (consent / rate-limit / provider-error / soft-fail / no-phone) covered by unit tests.
- [ ] **Bug 4** — 5xx responses carry `Access-Control-Allow-Origin` matching the request origin and a JSON body `{"success": false, "error": {"code": "INTERNAL_ERROR"}}`. Integration test `test_cors_on_5xx.py` passes.
- [ ] **Bug 5** — Seeder reuse branch PUTs `email`/`email_opt_in`/`sms_opt_in` to normalize the test invariants. Second consecutive run prints `(reused, refreshed)` and stdout ends with `APPOINTMENT_ID=...`/`INVOICE_ID=...`/`ZERO_INVOICE_ID=...`.
- [ ] **Bug 6** — `payment-links-flow.sh` Journey 1 navigates to `/schedule?focus=$APPOINTMENT_ID` and clicks `[data-testid='fc-event-$APPOINTMENT_ID']`. The event renderer (FullCalendar `eventDidMount`) sets `data-testid="fc-event-{id}"` on every `.fc-event` node.
- [ ] **Bug 7** — `docs/payments-runbook.md` contains the manual "pin Railway builder to DOCKERFILE" steps. (Manual Railway step performed and confirmed before the next deploy.)
- [ ] **Bug 1 follow-up** — `scripts/check-alembic-heads.sh` exists, is executable, exits 1 on multi-head, 0 otherwise. `.github/workflows/alembic-heads.yml` runs it on PRs/pushes to `main`/`dev` and goes green on the current single-head state. (Husky is intentionally deferred per Task 19 to avoid breaking Vercel's root-`package.json` install path.)
- [ ] All Level 1, 2, 3 validation commands pass with zero errors.
- [ ] `DEVLOG.md` updated with a `BUGFIX` entry per `devlog-rules.md`.
- [ ] No regressions: existing `test_invoice_service_send_link.py` tests pass after the response-shape extension. `bash e2e/payment-links-flow.sh` against dev produces a green run with fresh screenshots.

---

## COMPLETION CHECKLIST

- [ ] Tasks 1–21 completed in order.
- [ ] Each task validation passed immediately after the task.
- [ ] All Level 1 (syntax/style) checks zero-error.
- [ ] All Level 2 (unit) tests green.
- [ ] All Level 3 (integration) tests green.
- [ ] Level 4 manual E2E + cURL validation complete; screenshots saved to `e2e-screenshots/payment-links-architecture-c/`.
- [ ] Level 5 operational checks (CI workflow visible + green; Railway pin confirmed).
- [ ] DEVLOG entry added.
- [ ] Acceptance criteria all checked.
- [ ] Code reviewed for compliance with `code-standards.md`, `api-patterns.md`, `frontend-patterns.md`.

---

## NOTES

**Excluded from this plan (per user instruction)**: `.kiro/steering/kiro-cli-reference.md`, `.kiro/steering/knowledge-management.md`, `.kiro/steering/pre-implementation-analysis.md` — Kiro-CLI / Kiro-power / `kiroPowers`-action specifics. The remaining steering docs (`code-standards.md`, `tech.md`, `structure.md`, `api-patterns.md`, `frontend-patterns.md`, `frontend-testing.md`, `agent-browser.md`, `e2e-testing-skill.md`, `spec-quality-gates.md`, `spec-testing-standards.md`, `devlog-rules.md`, `auto-devlog.md`, `parallel-execution.md`, `vertical-slice-setup-guide.md`) are honored throughout — see **Patterns to Follow** above.

**Sequencing rationale**:
- Phase 1 (schema/types) before Phase 2 (service/middleware) so `_record_link_sent`'s new signature has its target shape locked in.
- Phase 2 before Phase 3 (frontend) so the API contract is real before the consumers depend on it.
- Phase 4 (Alembic guardrail + Railway pin) is parallel to Phase 1–3 in principle, but the script/workflow files are independent and easy to slot in late.
- Phase 5 (tests + devlog) closes the loop.

**Risk register** (every risk verified against the code; mitigations are concrete actions):

1. ~~Husky install on root `package.json` may break Vercel deploys.~~ **RESOLVED**: Husky is deferred (Task 19). CI workflow alone covers Bug 1 follow-up; no risk to Vercel.
2. ~~`/schedule?focus={id}` deep linking may not exist.~~ **RESOLVED**: confirmed it does NOT exist (`SchedulePage.tsx:78-98` only handles `?scheduleJobId`). Task 9 navigates to `/schedule` (current week defaults) and finds the seeded appointment via the `data-testid` from Task 8 — works because the seeder always creates today's appointment (`seed_e2e_payment_links.py:53`).
3. ~~`EmailRecipientNotAllowedError` import path / circularity.~~ **RESOLVED**: verified at `services/email_service.py:58`; module does not import from `invoice_service` so no circular dep. Task 3 imports it as a runtime symbol (NOT under TYPE_CHECKING) so the `except` clause has it.
4. ~~`SMSError` taxonomy.~~ **RESOLVED**: `SMSRateLimitDeniedError` subclasses `SMSError` (verified `sms_service.py:172`). Task 3 explicitly splits the existing combined `except (SMSRateLimitDeniedError, SMSError)` at lines 989–994 into two clauses, ordered subclass-first.
5. **CI workflow first run** — the commit that adds `.github/workflows/alembic-heads.yml` will trigger it immediately. **Mitigation**: Task 17's local script (`bash scripts/check-alembic-heads.sh`) is run BEFORE committing the workflow file; current dev state already has a single head (verified: `uv run alembic heads` returns `20260503_100000 (head)`), so the first CI run goes green.
6. **Vercel rootDirectory** — `.vercel/project.json` does not declare a rootDirectory; the Vercel UI controls it. We make no changes that affect Vercel because Husky is deferred (Task 19) and no other root-level files are touched.

**Confidence**: 10/10 on one-pass success. All file paths, line numbers, imports, exception class names, and event-id wiring confirmed against the code at planning time. The two operational items (CI workflow, Railway builder pin) are minimal and orthogonal to the application code; the Railway pin is documentation-only and the CI workflow is exercised against pre-validated single-head state.
