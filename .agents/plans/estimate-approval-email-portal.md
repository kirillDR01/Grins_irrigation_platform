# Feature: Estimate Approval Email Portal — Wire Resend + Email Template + Internal Notifications + Bounce Webhook

The following plan is complete, but the executing agent must validate documentation, codebase patterns, and task sanity before implementing.

Pay special attention to naming of existing utils, types, and models. Import from the right files (`grins_platform.exceptions`, `grins_platform.services.email_service`, `grins_platform.services.sms.base`, etc.).

---

## Feature Description

The estimate approval *portal* (DB schema, public approve/reject API, frontend route + page, admin `/send` endpoint, lead-tag flip on decision) is **already fully built and shipped**. The single missing link is **outbound email**: `EmailService._send_email` is a logger stub with no provider plugged in, there is no `estimate_sent.html` template, and admin clicks of "Send" never produce a real customer email.

This feature wires the **Resend** email provider into the existing abstraction, ships an `estimate_sent.html` template, adds a hard dev/staging recipient allowlist guard (mirroring the SMS allowlist), surfaces internal staff notifications on approve/reject (email + SMS to sales), handles Resend bounce webhooks, and moves `portal_base_url` from a hardcoded constructor default to environment configuration. Token validity extends from 30 → 60 days. No DB changes are required for the core flow; one optional column (`customers.email_bounced_at`) is added to soft-flag bounce history.

## User Story

As a **sales rep at Grin's Irrigation**
I want **clicking "Send" on an estimate to actually email the customer a tokenized portal link, and to be paged via email + SMS the moment they approve, reject, or hard-bounce**
So that **I can stop re-typing portal links into Gmail by hand, know instantly when to send the SignWell contract, and rescue cold deals when an email never lands.**

## Problem Statement

`POST /api/v1/estimates/{id}/send` returns success and logs `estimate.email.queued` but no email is actually sent — `EmailService._send_email` is a logger stub. Customers receive only the SMS branch. The sales team has no signal when the customer approves the estimate (they discover it via the lead-tag tab on next page reload), and they have zero visibility into hard bounces (the deal silently goes cold). Dev/staging environments could accidentally email real customers as soon as a real provider is plugged in.

## Solution Statement

1. Plug **Resend** (Python SDK `resend>=1.0.0`) into `EmailService._send_email`. Keep the existing abstraction — no new provider base class.
2. Add `EmailRecipientNotAllowedError` + `enforce_email_recipient_allowlist` mirroring the SMS module, so dev/staging cannot accidentally email outside `EMAIL_TEST_ADDRESS_ALLOWLIST` (default: `kirillrakitinsecond@gmail.com`).
3. Ship `estimate_sent.html` + `estimate_sent.txt` Jinja templates and a new `EmailService.send_estimate_email(...)` method. Add `"estimate_sent"` to the transactional set.
4. Replace the email-branch log-only block in `EstimateService.send_estimate` with a real call.
5. Add `portal_base_url` to `EmailSettings` (env var `PORTAL_BASE_URL`) and pass it through DI in `dependencies.py` + `portal.py`. Also fix the pre-existing URL builder bug at `estimate_service.py:273, 598` — convention is now `{PORTAL_BASE_URL}/portal/estimates/{token}` to match the React Router route exactly (no subdomain rewrites needed).
6. Bump `TOKEN_VALIDITY_DAYS = 30` → `60` and the `valid_until` default from 30d → 60d to keep the access-window aligned with price validity.
7. Add `_notify_internal_decision(...)` to `EstimateService` and `send_internal_estimate_decision_email(...)` to `EmailService`. Two env vars: `INTERNAL_NOTIFICATION_EMAIL`, `INTERNAL_NOTIFICATION_PHONE`. Failures are swallowed — must never undo a customer's approval.
8. Add `POST /api/v1/webhooks/resend` (HMAC signature verified via `RESEND_WEBHOOK_SECRET`). Handles `email.bounced` + `email.complained` → fire internal email + SMS, optionally stamp `customers.email_bounced_at`.
9. Set `Reply-To: info@grinsirrigation.com` on outgoing estimate email (belt-and-suspenders for `noreply@` auto-responder).
10. Optional: rate-limit `/portal/estimates/*` endpoints with the existing `PORTAL_LIMIT` constant from `middleware/rate_limit.py`.
11. Optional: transition `EstimateStatus.SENT → VIEWED` on first `GET /portal/estimates/{token}`.
12. **Sales pipeline breadcrumb (Q-A):** when `approve_via_portal` or `reject_via_portal` succeeds, look up the active (non-terminal) `SalesEntry` for the estimate's customer or lead and (a) append a timestamped note to `SalesEntry.notes`, (b) write an `AuditService.log_action` row with `action="sales_entry.estimate_decision_received"` and the decision details. Best-effort — never undoes the customer-side decision. Goes through `SalesPipelineService` so `EstimateService` does not write to another feature's tables (vertical-slice rule).
13. **Pipeline gate correction + naming clarity (Q-B):** `SalesEntryStatus.PENDING_APPROVAL` means "estimate sent; awaiting customer **approval** via portal" — a portal click, not a signature. Signatures only apply downstream to the contract via SignWell, gated correctly at `SEND_CONTRACT → CLOSED_WON` via `SignatureRequiredError` in `convert_to_job`. The existing `MissingSigningDocumentError` gate at `SEND_ESTIMATE → PENDING_APPROVAL` (`sales_pipeline_service.py:142-151`) is wrong — it forces reps to create a SignWell document before the customer has even seen the estimate. **Drop the gate** (10-line removal), drop the now-dead `MissingSigningDocumentError` import + except clause in `sales_pipeline.py`, invert the existing unit test that asserted the gate raises, and add a comment block above `SalesEntryStatus.PENDING_APPROVAL` documenting intent. The exception class itself stays in `exceptions/__init__.py` for back-compat with any external imports. Frontend label `'Pending Approval'` is unchanged (now actually correct).

## Feature Metadata

**Feature Type**: Enhancement (filling a single gap in an already-shipped flow)
**Estimated Complexity**: Medium (mostly mechanical wiring, but spans backend service + API + templates + DB column + frontend smoke + DNS/cutover)
**Primary Systems Affected**:
- `services/email_service.py`, `services/email_config.py`
- `services/estimate_service.py`
- `services/sales_pipeline_service.py` (Q-A breadcrumb method + Q-B FIXME comment)
- `models/enums.py` (Q-B docstring on `SalesEntryStatus.PENDING_APPROVAL`)
- `api/v1/estimates.py`, `api/v1/portal.py`, `api/v1/dependencies.py`, `api/v1/router.py`
- `templates/emails/` (new `estimate_sent.html` + `.txt`, plus `internal_estimate_decision.html`, `internal_estimate_bounce.html`)
- `migrations/versions/` (one new revision adding `customers.email_bounced_at`)
- `models/customer.py`
- New file `api/v1/resend_webhooks.py`
- New file `services/resend_webhook_security.py`
- `.env.example`

**Dependencies**:
- New: `resend>=1.0.0` (Python SDK)
- Existing: `boto3` (already in stack as fallback if Resend ever gets dropped — not used in v1)
- Existing: `slowapi` (rate limiting)

---

## CONTEXT REFERENCES

### Relevant Codebase Files — IMPORTANT: YOU MUST READ THESE BEFORE IMPLEMENTING

#### Backend — already-built portal flow (do NOT rebuild)
- `src/grins_platform/models/estimate.py` (lines 62–129) — `Estimate` model already has `customer_token`, `token_expires_at`, `token_readonly`, `approved_at/ip/user_agent`, `rejected_at/reason`, `valid_until`. **Do not add new columns to this table.**
- `src/grins_platform/models/enums.py` (lines 562, 716–745) — `EstimateStatus` enum (`DRAFT, SENT, VIEWED, APPROVED, REJECTED, EXPIRED, CANCELLED`); `MessageType.ESTIMATE_SENT` exists; `_AUTOMATED_STR_TO_MESSAGE_TYPE` mapping (`sms_service.py:128`).
- `src/grins_platform/api/v1/portal.py` (full file) — public unauthenticated portal endpoints already live; reuse `_get_client_ip`, `_mask_token`, `_to_portal_response`, `_get_estimate_service`. **You will modify `_get_estimate_service` to inject `email_service` + `sms_service` so the post-decision internal notifications fire from inside the service layer.**
- `src/grins_platform/api/v1/estimates.py` (lines 291–336) — admin `/{estimate_id}/send` endpoint. **No change needed** unless you decide to surface email-branch failures in the response (recommended: keep returning `sent_via` from the service unchanged).
- `src/grins_platform/services/estimate_service.py`:
  - lines 44–48 — `TOKEN_VALIDITY_DAYS = 30` (change to 60)
  - lines 75–97 — `__init__` signature with `portal_base_url` defaulting to `"https://portal.grins.com"` (remove default; require env-driven value via DI)
  - line 156 — `valid_until=data.valid_until or (now + timedelta(days=30))` (change to 60)
  - lines 239–348 — `send_estimate` (replace lines 300–311 with real email send; add fallback for `estimate.lead.email`)
  - lines 354–433 — `approve_via_portal` (call `await self._notify_internal_decision(estimate, "approved")` after lead-tag update, before `log_completed`)
  - lines 435–509 — `reject_via_portal` (same notification call with `"rejected"`)
- `src/grins_platform/api/v1/dependencies.py`:
  - lines 52–53 — `EmailService` import
  - lines 220–264 — `get_full_appointment_service` shows the constructor pattern; **here `EstimateService(estimate_repository=estimate_repository)` is called without email/sms/portal_base_url — this must change.**
  - lines 353–365 — `get_estimate_service` — the dependency you will modify to inject `email_service`, `sms_service`, and `portal_base_url`.
  - lines 368–390 — `get_campaign_service` — example of constructing `EmailService()`, `SMSService(session=session, provider=get_sms_provider())`. Reuse this pattern.

#### Backend — email infrastructure to extend
- `src/grins_platform/services/email_service.py`:
  - lines 35–53 — module constants. **Add `from resend import Resend` (or `import resend`) at the top.**
  - lines 44–45 — `TRANSACTIONAL_SENDER`, `COMMERCIAL_SENDER` (already defined; do not change)
  - lines 74–91 — `EmailService.__init__` and `jinja_env` property. **Add `if self.settings.is_configured: resend.api_key = self.settings.resend_api_key` in `__init__`.**
  - lines 93–112 — `_classify_email`. **Add `"estimate_sent"`, `"internal_estimate_decision"`, `"internal_estimate_bounce"` to the `transactional_types` set.**
  - lines 123–140 — `_render_template`. Note: it auto-injects `business_name`, `business_phone`, `business_email`, `portal_url` (from `self.settings.stripe_customer_portal_url` — do **not** change this default; the estimate template will receive `portal_url` explicitly via `context`).
  - lines 157–195 — `_send_email`. **This is the body to replace.** Keep the `is_configured` short-circuit, then:
      1. Call the new `enforce_email_recipient_allowlist(to_email, provider="resend")` BEFORE any I/O.
      2. Call `resend.Emails.send({...})` and log success with `provider_message_id=response.get("id")`.
  - lines 197–256 — `send_welcome_email` shows the canonical method shape. **Mirror this for `send_estimate_email`.** Note return shape: `{"sent": bool, "sent_via": "email"|"pending", "recipient_email": str, "content": str, "disclosure_type": None}`.
- `src/grins_platform/services/email_config.py` (full file) — `EmailSettings` is short. **Add `resend_api_key`, `email_test_address_allowlist`, `portal_base_url`, `internal_notification_email`, `resend_webhook_secret`. Update `is_configured` to check `resend_api_key or email_api_key`.**

#### Backend — SMS allowlist pattern to mirror
- `src/grins_platform/services/sms/base.py` (lines 17–93) — **canonical pattern.** `RecipientNotAllowedError` exception, `_load_allowlist()` env-loader, `_normalize_phone_for_comparison()`, `enforce_recipient_allowlist(to, *, provider)` that no-ops if env is unset and raises otherwise. Mirror exactly: same dual public API (exception + enforce function), same "unset env = production no-op" semantics, same provider kwarg for log context.
- Test pattern: search `src/grins_platform/tests/unit/test_pbt_callrail_sms.py` for `enforce_recipient_allowlist` for unit-test idioms.

#### Backend — webhook + signature pattern to mirror
- `src/grins_platform/api/v1/signwell_webhooks.py` (full file) — canonical webhook router shape: HMAC verify → parse JSON → branch on event type → return early on unknown type → 200 always (per provider docs). `prefix="/webhooks/signwell"`. Reuse the `LoggerMixin` endpoints class pattern (`_SignWellWebhookEndpoints` → `_ep`).
- `src/grins_platform/services/signwell/client.py` (lines 183–210) — `verify_webhook_signature(payload, signature) -> bool` using `hmac.new(secret, payload, hashlib.sha256).hexdigest()` + `hmac.compare_digest`. **Mirror exactly for Resend.** Resend's docs: `Svix-Signature` header carries `v1,<base64-sha256>` form — for v1, simplest path is HMAC-SHA256 of `f"{svix_id}.{svix_timestamp}.{raw_body}"` with `whsec_…` secret minus the `whsec_` prefix. Verify against current Resend docs before implementing (see Documentation section).
- `src/grins_platform/middleware/rate_limit.py` (lines 41, 45) — `PORTAL_LIMIT = "20/minute"` and `WEBHOOK_LIMIT = "60/minute"` are the constants to use on `/portal/estimates/*` and the new `/webhooks/resend` route.

#### Backend — exception module
- `src/grins_platform/exceptions/__init__.py` (lines 580–646) — pattern for adding a new exception class (`EstimateError` base, individual exceptions). **Add `EmailRecipientNotAllowedError(Exception)` here OR keep it in `services/email_service.py` (mirroring SMS where `RecipientNotAllowedError` lives in `services/sms/base.py`). Recommend the latter — keeps the guard self-contained.**

#### Backend — migration pattern
- `src/grins_platform/migrations/versions/20260427_100000_add_webauthn_credentials_table.py` — most recent migration; mirror the header (`revision`, `down_revision`, `Validates:`), `op.create_table`/`op.add_column` style. **New revision id: `20260428_100000` with `down_revision = "20260427_100000"`.**

#### Backend — models
- `src/grins_platform/models/customer.py` (lines 32, 97, 153, 161) — `Customer` model uses `Mapped[Optional[datetime]]` for nullable timestamps. Mirror that for `email_bounced_at`.

#### Backend — existing email templates to mirror
- `src/grins_platform/templates/emails/lead_confirmation.html` (full file, 12 lines) — minimal template style. **`estimate_sent.html` should be richer (CTA button, total, valid-until, plain-text fallback link) but follow the same `{{ business_name }}`, `{{ business_phone }}`, `{{ business_email }}` injection pattern.**
- `src/grins_platform/templates/emails/welcome.html` — for visual consistency reference.

#### Backend — DI wiring callsites that pass an `EstimateService` and may need `portal_base_url`
- `src/grins_platform/api/v1/dependencies.py:257` (`get_full_appointment_service`) — passes `EstimateService(estimate_repository=...)` without other deps. After this change, **leave this callsite alone** (appointment-driven estimate creation does not call `send_estimate`); document that the constructor `portal_base_url` becomes required-from-settings, not a kwarg default.
- `src/grins_platform/api/v1/portal.py:59-71` (`_get_estimate_service`) — change to inject `email_service`, `sms_service`, `portal_base_url=settings.portal_base_url`.

#### Frontend — already-built portal page (likely no code change)
- `frontend/src/core/router/index.tsx` (lines 140–157) — routes already wired: `/portal/estimates/:token` → `EstimateReviewPage`.
- `frontend/src/features/portal/api/portalApi.ts` — `getEstimate / approveEstimate / rejectEstimate` already wired.
- `frontend/src/features/portal/components/EstimateReview.tsx` (+ `.test.tsx`), `frontend/src/features/portal/components/ApprovalConfirmation.tsx` — verify they render gracefully for the line-item shapes the new email will link to. **No mandatory frontend code change for this feature** — just an a11y + visual smoke test as part of Phase 4.

#### Existing functional tests that need a tweak
- `src/grins_platform/tests/functional/test_estimate_operations_functional.py`:
  - line 66 — `now + timedelta(days=30)` (update if it asserts the old default)
  - line 72 — `now + timedelta(days=TOKEN_VALIDITY_DAYS)` (will pick up the constant change automatically)
  - line 164 — `portal_base_url: str = "https://portal.grins.com"` test default — keep inline (tests are allowed to hardcode).
  - line 256, 574, 723 — existing `send_estimate` tests; **must be updated** to assert `email_service.send_estimate_email` was called with the right args (or that it gracefully no-ops when no `email_service` injected).

#### Existing email tests
- `src/grins_platform/tests/unit/test_email_service.py` (lines 1–96 of helpers) — `_configured_settings`, `_unconfigured_settings`, `_mock_customer`, `_mock_lead`. Reuse the existing fixture style; add `_mock_estimate()` helper.

### New Files to Create

**Backend**
- `src/grins_platform/services/resend_webhook_security.py` — `verify_resend_webhook_signature(secret, headers, raw_body) -> bool` and `ResendWebhookVerificationError`. Keeps signature logic out of the API module and mirrors `services/signwell/client.py` placement style.
- `src/grins_platform/api/v1/resend_webhooks.py` — `POST /webhooks/resend` endpoint. Handles `email.bounced` and `email.complained` events. Returns 200 on every accepted webhook (even ignored event types) so Resend doesn't retry.
- `src/grins_platform/templates/emails/estimate_sent.html` — customer-facing transactional email.
- `src/grins_platform/templates/emails/estimate_sent.txt` — plain-text alternative for Resend's multipart send.
- `src/grins_platform/templates/emails/internal_estimate_decision.html` — internal staff alert on approve/reject.
- `src/grins_platform/templates/emails/internal_estimate_bounce.html` — internal staff alert on hard bounce.
- `src/grins_platform/migrations/versions/20260428_100000_add_customer_email_bounced_at.py` — alembic migration for `customers.email_bounced_at`.
- `src/grins_platform/tests/unit/test_email_recipient_allowlist.py` — guard semantics (set/unset env, normalize lowercase, allowlist hit/miss).
- `src/grins_platform/tests/unit/test_email_service_resend.py` — `_send_email` calls `resend.Emails.send` with expected payload, returns False on exception, raises on allowlist block.
- `src/grins_platform/tests/unit/test_send_estimate_email.py` — `send_estimate_email` happy path, missing-email, render-failure paths.
- `src/grins_platform/tests/unit/test_estimate_internal_notification.py` — `_notify_internal_decision` calls both email + SMS, swallows errors, env-var gating.
- `src/grins_platform/tests/unit/test_resend_webhook.py` — signature verify, branch on event type, internal notification dispatched on bounce, non-`email.bounced`/`email.complained` events return 200 + log + ignore.
- `src/grins_platform/tests/functional/test_estimate_email_send_functional.py` — real DB; create estimate → call `send_estimate` → assert `EmailService.send_estimate_email` was invoked + `sent_via` contains `"email"`.
- `src/grins_platform/tests/integration/test_estimate_approval_email_flow_integration.py` — full `POST /api/v1/estimates/{id}/send` → mock Resend → portal `GET` → portal `POST .../approve` → assert `email.bounced` webhook for the same recipient triggers internal notification → assert `SalesEntry.notes` contains the breadcrumb line and an `audit_log` row with `action="sales_entry.estimate_decision_received"` exists.
- `src/grins_platform/tests/unit/test_sales_pipeline_breadcrumb.py` — Q-A breadcrumb method on `SalesPipelineService` (8 cases including no-match, terminal-only, lead fallback, error swallowing).
- `src/grins_platform/tests/unit/test_estimate_correlation.py` — Q-A wiring on `EstimateService` (4 cases including no-op when dep is None).

**No frontend file creation is required** — but `frontend/src/features/portal/components/EstimateReview.tsx` should be hand-validated via agent-browser (Phase 4) and a Vitest test added if any change is made to handle empty `line_items`.

### Relevant Documentation — YOU SHOULD READ THESE BEFORE IMPLEMENTING

- [Resend Python SDK quickstart](https://resend.com/docs/send-with-python)
  - Specific section: *Send a first email*
  - Why: Canonical SDK shape — `resend.api_key = "…"` then `resend.Emails.send({"from", "to", "subject", "html", "text", "reply_to"})`.
- [Resend Send Email API reference](https://resend.com/docs/api-reference/emails/send-email)
  - Specific section: *Request body — `text`, `html`, `reply_to`, `headers`*
  - Why: Confirms multipart HTML+text in one call, header passthrough for `Reply-To`.
- [Resend Webhooks: Verifying signatures](https://resend.com/docs/dashboard/webhooks/verify-webhooks-requests)
  - Specific section: *Verifying webhook requests with the Svix library or manually*
  - Why: Webhook secret format (`whsec_…`), expected headers (`svix-id`, `svix-timestamp`, `svix-signature`), HMAC computation. Verify exact algorithm before shipping.
- [Resend Webhook event types](https://resend.com/docs/dashboard/webhooks/event-types)
  - Specific section: *`email.bounced`, `email.complained`, `email.delivery_delayed`*
  - Why: Bounce payload shape — `data.bounce.subType` distinguishes `Permanent` (hard) vs `Transient`; only flag the customer for permanent bounces.
- [Resend pricing — current tier](https://resend.com/pricing)
  - Why: Confirms 3K/mo, 100/day free-tier caps; relevant for capacity planning.
- [Pydantic Settings v2 — `Field(alias=...)`](https://docs.pydantic.dev/latest/concepts/pydantic_settings/#field-aliases)
  - Why: For making `RESEND_API_KEY` the primary env name while accepting legacy `EMAIL_API_KEY` — `Field(default="", validation_alias=AliasChoices("RESEND_API_KEY", "EMAIL_API_KEY"))`.
- [Alembic — using `op.add_column`](https://alembic.sqlalchemy.org/en/latest/ops.html#alembic.operations.Operations.add_column)
  - Why: Single-column migration for `customers.email_bounced_at`.

### Patterns to Follow

#### Naming Conventions (from `code-standards.md`, `structure.md`)
- Python files: `snake_case.py`. Test files: `test_{module}.py`.
- Service classes: `PascalCase` ending in `Service` (`EmailService`, `EstimateService`).
- Service log domain: class attribute `DOMAIN = "{lowercase-singleword}"` — e.g. `DOMAIN = "email"`, `DOMAIN = "estimate"`.
- Log event names: `{domain}.{component}.{action}_{state}` — e.g. `email.send.completed`, `email.send.failed`, `estimate.email.queued` (existing), `estimate.notify_internal.email_sent`, `estimate.notify_internal.failed`, `resend.webhook.bounce_received`, `resend.webhook.signature_invalid`.
- Constants: `UPPER_SNAKE_CASE` at module top.
- Env vars: `UPPER_SNAKE_CASE` (`RESEND_API_KEY`, `EMAIL_TEST_ADDRESS_ALLOWLIST`, `PORTAL_BASE_URL`, `INTERNAL_NOTIFICATION_EMAIL`, `INTERNAL_NOTIFICATION_PHONE`, `RESEND_WEBHOOK_SECRET`).

#### Logging Pattern (mandatory — from `code-standards.md` + `tech.md`)
Services inherit `LoggerMixin` and use `self.log_started`, `self.log_completed`, `self.log_rejected(..., reason=...)`, `self.log_failed(..., error=...)`:
```python
class EmailService(LoggerMixin):
    DOMAIN = "email"

    def send_estimate_email(self, *, customer, estimate, portal_url):
        self.log_started("send_estimate_email", estimate_id=str(estimate.id))
        try:
            ...
            self.log_completed("send_estimate_email", sent=sent, recipient=_mask_email(email))
            return result
        except Exception as e:
            self.log_failed("send_estimate_email", error=e, estimate_id=str(estimate.id))
            raise
```
**Never log full email addresses** — use the existing `_mask_email(email)` helper at `email_service.py:56`. Never log the portal token in full — use `_mask_token(token)` from `api/v1/portal.py:89`.

#### Error Handling Pattern (from `code-standards.md` + `signwell_webhooks.py`)
```python
try:
    result = self._process(data)
except ValidationError:
    raise  # already logged at lower level
except ExternalServiceError as e:
    self.log_failed("op", error=e)
    raise ServiceError(f"External failed: {e}") from e
```
For internal notifications: **swallow** all exceptions — never block the customer-facing path. Pattern:
```python
try:
    self.email_service.send_internal_estimate_decision_email(...)
except Exception as e:
    self.log_failed("notify_internal_decision_email", error=e, estimate_id=str(estimate.id))
```

#### Allowlist Guard Pattern (mirror `services/sms/base.py:17-93` exactly)
```python
class EmailRecipientNotAllowedError(Exception):
    """Raised when a send is blocked by EMAIL_TEST_ADDRESS_ALLOWLIST.

    Intentional refusal, not a provider failure. Production leaves the
    env var unset → guard is a no-op there.
    """

def _normalize_email_for_comparison(email: str) -> str:
    return email.strip().lower() if email else ""

def _load_email_allowlist() -> list[str] | None:
    raw = os.environ.get("EMAIL_TEST_ADDRESS_ALLOWLIST", "").strip()
    if not raw:
        return None
    parts = [p.strip().lower() for p in raw.split(",") if p.strip()]
    return parts or None

def enforce_email_recipient_allowlist(to: str, *, provider: str) -> None:
    allowlist = _load_email_allowlist()
    if allowlist is None:
        return
    if _normalize_email_for_comparison(to) in allowlist:
        return
    msg = (
        f"recipient_not_in_email_allowlist: provider={provider} "
        f"(set EMAIL_TEST_ADDRESS_ALLOWLIST to override for dev/staging; "
        f"leave unset in production)"
    )
    raise EmailRecipientNotAllowedError(msg)
```
**Where to put it:** the guard, exception, and helpers go directly in `email_service.py` (top of module after constants). Do NOT carve out a `services/email/base.py` package yet — there is exactly one provider planned (Resend); refactor only when a second provider lands.

#### API Endpoint Pattern (from `api-patterns.md`, mirror `signwell_webhooks.py`)
- Use `LoggerMixin` endpoints class to access `self.log_*`.
- `set_request_id()` at start, `clear_request_id()` in `finally` (only for authenticated/non-webhook routes; webhooks already have their own correlation via headers — see `signwell_webhooks.py` for precedent of skipping it).
- Always return 200 on a successfully-validated webhook regardless of whether the event type is handled — Resend will retry on non-2xx.
- Verify signature **before** parsing JSON body.

#### Settings Pattern (from `email_config.py` + `pydantic-settings`)
```python
from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class EmailSettings(BaseSettings):
    resend_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("RESEND_API_KEY", "EMAIL_API_KEY"),
    )
    portal_base_url: str = Field(
        default="http://localhost:5173",
        validation_alias="PORTAL_BASE_URL",
    )
    internal_notification_email: str = Field(default="", validation_alias="INTERNAL_NOTIFICATION_EMAIL")
    resend_webhook_secret: str = Field(default="", validation_alias="RESEND_WEBHOOK_SECRET")
    company_physical_address: str = ""
    stripe_customer_portal_url: str = ""
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def is_configured(self) -> bool:
        return bool(self.resend_api_key)
```

#### Three-Tier Test Markers (mandatory — from `code-standards.md`)
- Unit: `@pytest.mark.unit` in `tests/unit/`. All deps mocked.
- Functional: `@pytest.mark.functional` in `tests/functional/`. Real DB.
- Integration: `@pytest.mark.integration` in `tests/integration/`. Full system.
- Test naming: `test_{method}_with_{condition}_returns_{expected}` (unit) / `test_{workflow}_as_user_would_experience` (functional) / `test_{feature}_works_with_existing_{component}` (integration).

---

## PRE-FLIGHT VERIFICATION

Run this checklist BEFORE starting Phase 1. Each command must produce the documented output. If any check fails, the plan's line-number / API assumptions have shifted since 2026-04-25 and you must reconcile before writing code.

```bash
# 1. Resend SDK 2.x is available and exposes the helpers we use.
uv run python -c "
import resend
assert hasattr(resend, 'Emails') and hasattr(resend.Emails, 'send'), 'resend.Emails.send missing'
assert hasattr(resend, 'webhooks') and hasattr(resend.webhooks, 'verify'), 'resend.webhooks.verify missing'
print('OK: Resend SDK shape verified')
" 2>&1
# Expected: 'OK: Resend SDK shape verified'

# 2. Every EstimateService(...) callsite is accounted for in step 34.
grep -rn "EstimateService(" src/ | grep -v __pycache__ | grep -v "class EstimateService"
# Expected: exactly 11 lines across portal.py, dependencies.py (×2), test_estimate_service.py,
# test_external_service_integration.py (×4), test_estimate_operations_functional.py,
# test_background_jobs_functional.py. If a NEW callsite has appeared since 2026-04-25,
# update step 34 to include it.

# 3. The MissingSigningDocumentError gate is still where step 44 expects it.
grep -n "MissingSigningDocumentError" src/grins_platform/services/sales_pipeline_service.py
# Expected: 2 lines — one import (~line 16) and one raise (~line 151).

# 4. The portal.py _get_estimate_service factory is still at the documented line range.
grep -n "_get_estimate_service\|_get_pipeline_service" src/grins_platform/api/v1/portal.py src/grins_platform/api/v1/sales_pipeline.py
# Expected: portal.py shows _get_estimate_service ~line 59-71;
# sales_pipeline.py shows _get_pipeline_service ~line 169-175.

# 5. EstimateRepository exposes .session.
grep -n "self.session" src/grins_platform/repositories/estimate_repository.py | head -3
# Expected: at least one match showing 'self.session = session' in __init__.

# 6. Latest migration head matches step 21's down_revision.
uv run alembic heads
# Expected: '20260427_100000 (head)'. If newer, update step 21's down_revision and revision id.

# 7. The Resend webhook prefix is unique.
grep -rn "/webhooks/resend" src/grins_platform/api/v1/
# Expected: no matches before this feature is implemented.

# 8. Customer.email column exists and is the type the bounce-flag UPDATE expects.
grep -n "email:" src/grins_platform/models/customer.py | head -5
# Expected: 'email: Mapped[Optional[str]] = mapped_column(String(255), ...)' or similar.

# 9. The Lead model has both email and phone (we fall back from customer to lead in send_estimate).
grep -n "email:\|phone:" src/grins_platform/models/lead.py | head -5
# Expected: 'phone: Mapped[str]' (required) and 'email: Mapped[Optional[str]]' (optional).

# 10. The SalesEntry.notes column is a nullable Text column we can append to.
grep -n "notes:" src/grins_platform/models/sales.py | head -3
# Expected: 'notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)'.

# 11. The current LeadService and JobService constructor signatures match step 28's reasoning.
uv run python -c "
import inspect
from grins_platform.services.lead_service import LeadService
from grins_platform.services.job_service import JobService
from grins_platform.services.audit_service import AuditService
print('LeadService:', list(inspect.signature(LeadService.__init__).parameters))
print('JobService:', list(inspect.signature(JobService.__init__).parameters))
print('AuditService:', list(inspect.signature(AuditService.__init__).parameters))
"
# Expected:
#   LeadService: ['self', 'lead_repository', 'customer_service', 'job_service', 'staff_repository', 'sms_service', 'email_service', 'compliance_service']
#   JobService: ['self', 'job_repository', 'customer_repository', 'property_repository', 'service_repository']
#   AuditService: ['self']  (just LoggerMixin __init__)

# 12. No existing 'import resend' — clean slate.
grep -rn "^import resend\|^from resend" src/ | grep -v __pycache__
# Expected: no matches.
```

If all 12 checks pass, the plan's assumptions are still correct and you can proceed to Phase 1. If any FAIL, stop and reconcile before continuing.

---

## IMPLEMENTATION PLAN

### Phase 1: Foundation — Settings + Allowlist + Token Expiry

Wire the env vars and the dev-safety guard before plugging in any real provider. After this phase, dev cannot accidentally email a real customer no matter what you call.

**Tasks:**
- Add `resend>=1.0.0` to `pyproject.toml` and run `uv lock`.
- Extend `EmailSettings` with `resend_api_key`, `portal_base_url`, `internal_notification_email`, `resend_webhook_secret`. Preserve `email_api_key` legacy alias.
- Add `EmailRecipientNotAllowedError` + `_load_email_allowlist`, `_normalize_email_for_comparison`, `enforce_email_recipient_allowlist` to `email_service.py`.
- Bump `TOKEN_VALIDITY_DAYS = 30 → 60` and `valid_until` default (estimate_service.py:48 + 156). Update docstrings.
- Update `.env.example`.

### Phase 2: Core Email Provider Wiring

Plug Resend into `_send_email`, ship `estimate_sent.html`/`.txt`, build `send_estimate_email`. After this phase, calling `EmailService.send_estimate_email(...)` from a Python REPL produces a real email.

**Tasks:**
- Replace `_send_email` body with Resend SDK call + `Reply-To: info@grinsirrigation.com` header.
- Init `resend.api_key` in `EmailService.__init__` if configured.
- Add `"estimate_sent"`, `"internal_estimate_decision"`, `"internal_estimate_bounce"` to `transactional_types`.
- Render `estimate_sent.html` (Jinja2) + `estimate_sent.txt`. Subject: `Your estimate from Grin's Irrigation`.
- Implement `EmailService.send_estimate_email(*, customer, estimate, portal_url) -> dict[str, Any]` mirroring `send_welcome_email` shape.
- Implement `EmailService.send_internal_estimate_decision_email(*, to_email, subject, body) -> bool` (renders `internal_estimate_decision.html`).
- Implement `EmailService.send_internal_estimate_bounce_email(*, to_email, recipient, reason, estimate_id) -> bool` (renders `internal_estimate_bounce.html`).

### Phase 3: Estimate Service Integration + DI Wiring

Wire `EmailService` and `portal_base_url` into `EstimateService` via DI; replace the `estimate.email.queued` log block with the real call; add `_notify_internal_decision` to approve/reject paths.

**Tasks:**
- Edit `EstimateService.__init__` to remove the hardcoded `portal_base_url` default — make it required.
- In `api/v1/dependencies.py` `get_estimate_service` — construct `EmailService()`, `SMSService(session=session, provider=get_sms_provider())`, and inject all three (+ `portal_base_url=EmailSettings().portal_base_url`).
- In `api/v1/portal.py` `_get_estimate_service` — same injection so `_notify_internal_decision` works on customer-side approve/reject.
- In `api/v1/dependencies.py:257` `get_full_appointment_service` — pass `portal_base_url=EmailSettings().portal_base_url` (the appointment-driven path doesn't `send_estimate`, but constructing `EstimateService` without it would break once the default is removed).
- Replace `estimate_service.py:300–311` email-branch log-only block with a real call wrapped in try/except (mirror SMS branch above it).
- Add the same fallback for `estimate.lead.email` in the `if not sent_via and estimate.lead:` block (≈ line 313+).
- Implement private `EstimateService._notify_internal_decision(estimate, decision)` — async, awaits `sms_service.send_automated_message(...)` and calls sync `email_service.send_internal_estimate_decision_email(...)`. Reads `INTERNAL_NOTIFICATION_EMAIL` and `INTERNAL_NOTIFICATION_PHONE` directly via `os.getenv` (matches the design.md sketch — these are operational toggles, not part of `EmailSettings`). All exceptions swallowed and logged.
- Call `await self._notify_internal_decision(estimate, "approved")` at end of `approve_via_portal` (after lead-tag update, before `log_completed`). Same for `"rejected"` in `reject_via_portal`.

### Phase 4: Bounce Webhook + Migration + (Optional) Polish

Wire Resend's bounce webhook so the sales rep gets pinged when an estimate email fails to deliver. Ship the `customers.email_bounced_at` column. Add the optional polish items.

**Tasks:**
- Generate alembic migration `20260428_100000_add_customer_email_bounced_at.py` adding nullable `customers.email_bounced_at TIMESTAMP WITH TIME ZONE`.
- Add `email_bounced_at: Mapped[Optional[datetime]] = mapped_column(...)` to `Customer` model.
- Create `services/resend_webhook_security.py` with HMAC-SHA256 signature verification.
- Create `api/v1/resend_webhooks.py` — `POST /webhooks/resend`, signature-verified, handles `email.bounced` (only `data.bounce.subType == "Permanent"` triggers the hard-bounce path) and `email.complained`. On match, look up the recipient → call `EmailService.send_internal_estimate_bounce_email` + `SMSService.send_automated_message` to staff. Stamp `customers.email_bounced_at = now()` (best-effort, logged on failure).
- Register `resend_webhooks_router` in `api/v1/router.py` (under `/webhooks/resend`).
- Apply rate-limit decorators: `@limiter.limit(PORTAL_LIMIT)` on `GET /portal/estimates/{token}`, `POST /portal/estimates/{token}/approve`, `POST /portal/estimates/{token}/reject`. `@limiter.limit(WEBHOOK_LIMIT)` on `POST /webhooks/resend`.
- (Optional) Transition `EstimateStatus.SENT → VIEWED` in `get_portal_estimate` after `_validate_portal_token` — only update if current status is `SENT`. ≤5 LOC.
- Update `.env.example` with all new vars.

### Phase 4.5: Sales Pipeline Correlation + Gate Correction (Q-A + Q-B)

**Q-A — breadcrumb on `SalesEntry`**: when `EstimateService.approve_via_portal` or `reject_via_portal` succeeds, write a timestamped note to the matching active `SalesEntry.notes` AND an audit row, so the rep sees "customer approved at 14:32 — ready to send contract" without having to refresh the lead-tag tab. **Best-effort, never raises.** No data-model change to `SalesEntry`; no auto-advance of the kanban (rep stays in control).

**Q-B — drop the misaligned gate at `SEND_ESTIMATE → PENDING_APPROVAL`**: the gate forces a SignWell document before the customer has approved the estimate, contradicting the intended workflow (estimate approval = portal click; signature only applies to contract). Remove the gate, clean up the now-dead exception import/except clause, invert the failing unit test, and add an enum-level comment block documenting intent.

**Tasks (Q-A):**
- Inject `SalesPipelineService` into `EstimateService` via DI as an optional dependency.
- Add `SalesPipelineService.record_estimate_decision_breadcrumb(db, estimate, decision, *, reason=None)` — looks up active SalesEntry, appends note, writes audit. Cross-feature READ from `Estimate`, but WRITE only to its own `SalesEntry` table — respects the vertical-slice rule.
- Wire the call into `approve_via_portal` and `reject_via_portal` after `_notify_internal_decision` (notifications fire first; correlation is the slower DB-write step).

**Tasks (Q-B):**
- Remove the gate at `sales_pipeline_service.py:142-151` (the `if target == PENDING_APPROVAL and not entry.signwell_document_id:` raise block) along with the surrounding comment.
- Drop the now-unused `MissingSigningDocumentError` import in `sales_pipeline_service.py:14-19`.
- Drop the unused `MissingSigningDocumentError` import + `except MissingSigningDocumentError` clause in `sales_pipeline.py:19-24, 270-274` (the 422 response path is no longer reachable).
- Update the existing unit test `test_send_estimate_without_doc_raises` in `tests/unit/test_sales_pipeline_and_signwell.py:148-165` — invert it to `test_send_estimate_without_doc_now_advances` (locks in the corrected behavior).
- Add a clarifying comment block above `SalesEntryStatus.PENDING_APPROVAL` in `models/enums.py`.
- Leave `MissingSigningDocumentError` class definition in `exceptions/__init__.py` for back-compat (no consumers in the codebase, but the export is public-facing).
- Frontend: leave `StatusActionButton.tsx:140` toast handler in place (defensive — harmless dead branch); add a one-line comment that the API no longer returns this 422.

### Phase 5: Testing & Validation

Unit, functional, integration, property, frontend smoke. Manual E2E in dev with the test inbox.

**Tasks:**
- Write all test files listed in *New Files to Create*.
- Update existing `test_estimate_operations_functional.py` assertions for the new 60-day default.
- Run `uv run ruff check src/`, `uv run mypy src/`, `uv run pyright src/`, `uv run pytest -v`. All must pass with zero violations.
- Manual E2E in dev with `EMAIL_TEST_ADDRESS_ALLOWLIST=kirillrakitinsecond@gmail.com`: send estimate → confirm email arrives → click link → portal page renders → approve → confirm internal email + SMS fire to dev recipients → confirm DB row shows `approved_at`, `token_readonly=True`.
- agent-browser smoke on the portal page (already exists, verify nothing broke).

### Phase 6: Production Cutover (operational, not coding)

Tracked here for completeness but executed by ops, not the coding agent.

- DNS records (SPF, DKIM, DMARC) on `grinsirrigation.com` per Resend dashboard.
- `portal.grinsirrigation.com` CNAME → React deploy.
- Verify sender domain in Resend dashboard.
- Set production env: `RESEND_API_KEY`, `RESEND_WEBHOOK_SECRET`, `PORTAL_BASE_URL=https://portal.grinsirrigation.com`, `INTERNAL_NOTIFICATION_EMAIL=<TBD>`, `INTERNAL_NOTIFICATION_PHONE=<TBD>`.
- Confirm `EMAIL_TEST_ADDRESS_ALLOWLIST` and `SMS_TEST_PHONE_ALLOWLIST` are **NOT** set in prod.
- Configure Resend webhook to `https://api.grinsirrigation.com/api/v1/webhooks/resend`.
- Set up `noreply@grinsirrigation.com` mailbox + auto-responder (Q6 body from open-questions.md).

---

## STEP-BY-STEP TASKS

Execute every task in order, top to bottom. Each task is atomic and independently testable.

### 1. UPDATE `pyproject.toml`
- **IMPLEMENT**: Add `"resend>=2.0.0,<3.0.0",` to the `dependencies` list alphabetically (right after `"redis>=5.0.0",` and before `"slowapi>=0.1.9",`).
- **PATTERN**: see existing lines 38–58.
- **IMPORTS**: N/A.
- **GOTCHA**: Latest Resend SDK is **2.x** (verified 2026-04-25 via `pip index versions resend` → 2.29.0). The v1.x family is end-of-life — do NOT pin to it. Module-level `resend.api_key = "..."` still works in 2.x and `resend.Emails.send({...})` is the canonical send method. Async sends are opt-in via `pip install "resend[async]"` (we don't need this; existing `EmailService._send_email` is sync). After adding, run `uv lock` to refresh `uv.lock`.
- **VALIDATE**: `uv lock && grep -q '^resend = ' uv.lock && uv run python -c "import resend; assert hasattr(resend, 'Emails') and hasattr(resend.Emails, 'send'); assert hasattr(resend, 'webhooks') and hasattr(resend.webhooks, 'verify'); print('OK')"`

### 2. UPDATE `src/grins_platform/services/email_config.py`
- **IMPLEMENT**: Extend `EmailSettings` with these fields, keeping the existing three (`email_api_key`, `company_physical_address`, `stripe_customer_portal_url`). Use `Field(validation_alias=...)` to read the new env names. Update `is_configured` to `bool(self.resend_api_key or self.email_api_key)`.
  ```python
  from pydantic import AliasChoices, Field
  resend_api_key: str = Field(default="", validation_alias=AliasChoices("RESEND_API_KEY", "EMAIL_API_KEY"))
  portal_base_url: str = Field(default="http://localhost:5173", validation_alias="PORTAL_BASE_URL")
  internal_notification_email: str = Field(default="", validation_alias="INTERNAL_NOTIFICATION_EMAIL")
  resend_webhook_secret: str = Field(default="", validation_alias="RESEND_WEBHOOK_SECRET")
  ```
- **PATTERN**: existing `EmailSettings` (full file).
- **IMPORTS**: add `from pydantic import AliasChoices, Field` to the existing imports.
- **GOTCHA**: Pydantic 2 uses `validation_alias`, not `alias`. `email_api_key` field stays for back-compat — `AliasChoices` lets `RESEND_API_KEY` win when both are present. Update `log_configuration_status` to also warn if neither env is set.
- **VALIDATE**: `uv run python -c "from grins_platform.services.email_config import EmailSettings; s = EmailSettings(resend_api_key='re_test'); assert s.is_configured and s.portal_base_url == 'http://localhost:5173'"`

### 3. UPDATE `src/grins_platform/services/email_service.py` — ADD allowlist guard
- **IMPLEMENT**: After the module constants (after line 53, before `_mask_email`), add `EmailRecipientNotAllowedError`, `_normalize_email_for_comparison`, `_load_email_allowlist`, `enforce_email_recipient_allowlist`. See the *Allowlist Guard Pattern* section above for exact code.
- **PATTERN**: `services/sms/base.py:17-93` (mirror exactly).
- **IMPORTS**: `os` is already imported (line 14).
- **GOTCHA**: Empty-or-unset `EMAIL_TEST_ADDRESS_ALLOWLIST` MUST return `None` (production no-op). A comma-with-no-content (`","`) MUST also return `None` after filtering.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_email_recipient_allowlist.py -v` (test file authored in step 17).

### 4. UPDATE `src/grins_platform/services/email_service.py` — ADD provider init + replace `_send_email`
- **IMPLEMENT**:
  - At top: `import resend` (after `from jose import jwt`).
  - In `__init__` after `self._jinja_env: Environment | None = None`: `if self.settings.is_configured: resend.api_key = self.settings.resend_api_key or self.settings.email_api_key`.
  - Replace `_send_email` body (lines 157–195). Keep the `is_configured` short-circuit, then call `enforce_email_recipient_allowlist(to_email, provider="resend")`, then `resend.Emails.send({"from": f"Grin's Irrigation <{sender}>", "to": [to_email], "subject": subject, "html": html_body, "reply_to": COMMERCIAL_SENDER})`. Wrap in try/except `EmailRecipientNotAllowedError` (re-raise) and `Exception` (log `email.send.failed`, return `False`).
- **PATTERN**: `vendor-decision.md` §3.2 sketch + `signwell/client.py` for try/except style.
- **IMPORTS**: `import resend` at top.
- **GOTCHA**: Resend's SDK returns a dict — log `provider_message_id=response.get("id")`. Do NOT raise on Resend errors; the existing return-False contract is what callers expect (`send_welcome_email` etc. branch on the bool). Allowlist denial DOES raise — by design — so callers see refusals as exceptions, not silent skips.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_email_service_resend.py -v`

### 5. UPDATE `src/grins_platform/services/email_service.py` — extend transactional set
- **IMPLEMENT**: In `_classify_email` (line 98), add `"estimate_sent"`, `"internal_estimate_decision"`, `"internal_estimate_bounce"` to the `transactional_types` set.
- **PATTERN**: existing set on lines 98–109.
- **GOTCHA**: Estimate emails are responses to a customer's prior request (CAN-SPAM transactional), so no unsubscribe link. Internal staff alerts are also transactional (sent to employees, not marketing recipients).
- **VALIDATE**: `uv run python -c "from grins_platform.services.email_service import EmailService; from grins_platform.models.enums import EmailType; assert EmailService()._classify_email('estimate_sent') == EmailType.TRANSACTIONAL"`

### 6. CREATE `src/grins_platform/templates/emails/estimate_sent.html`
- **IMPLEMENT**: Customer-facing transactional email. Required Jinja vars: `customer_name`, `total`, `valid_until` (formatted YYYY-MM-DD or `Month DD, YYYY`), `portal_url`, plus the auto-injected `business_name`, `business_phone`, `business_email`. Content blocks: greeting → one-paragraph summary with total + valid-until → CTA button (`<a href="{{ portal_url }}">Review your estimate</a>`) → plain-text URL fallback (`<p>Or paste this link into your browser: {{ portal_url }}</p>`) → "Reply or call {{ business_phone }} with any questions." → footer with business name/phone/email. **No unsubscribe link** (transactional).
- **PATTERN**: `templates/emails/welcome.html` for visual style; `templates/emails/lead_confirmation.html` for the minimal Jinja shape (12 lines is fine if the design is simple).
- **IMPORTS**: N/A (Jinja).
- **GOTCHA**: Some clients strip CSS — keep the CTA both as styled `<a>` and as a plain text URL fallback. Avoid `$` and excessive punctuation in subject (set in step 7) to dodge spam filters.
- **VALIDATE**: `uv run python -c "from grins_platform.services.email_service import EmailService; from unittest.mock import MagicMock; e = MagicMock(); e.total='599.00'; e.valid_until='2026-06-25'; html = EmailService()._render_template('estimate_sent.html', {'customer_name':'Jane','total':'599.00','valid_until':'2026-06-25','portal_url':'http://x/y'}); assert 'Review your estimate' in html"`

### 7. CREATE `src/grins_platform/templates/emails/estimate_sent.txt`
- **IMPLEMENT**: Plain-text alternative. Same five blocks as HTML but text-only. Resend will use this for clients that prefer text.
- **PATTERN**: no existing `.txt` template — author from scratch.
- **GOTCHA**: Keep the URL on its own line with no surrounding punctuation so `mailto:`/`tel:` linkifiers don't mangle it.
- **VALIDATE**: file exists and renders without Jinja errors via the test in step 19.

### 8. CREATE `src/grins_platform/templates/emails/internal_estimate_decision.html`
- **IMPLEMENT**: Internal staff alert. Vars: `customer_name`, `decision` (`"approved"`/`"rejected"`), `total`, `estimate_id`, `admin_url` (deep-link to admin estimate detail page if available, else empty), `rejection_reason` (optional).
- **PATTERN**: same as `lead_confirmation.html` — minimal HTML.
- **GOTCHA**: Internal email — no business footer/contact necessary. Subject is set by caller.
- **VALIDATE**: file exists and renders.

### 9. CREATE `src/grins_platform/templates/emails/internal_estimate_bounce.html`
- **IMPLEMENT**: Internal staff alert for bounce. Vars: `recipient_email` (masked or full — internal staff so full is fine), `reason`, `estimate_id` (if known from bounce metadata; else "unknown"), `bounced_at`.
- **PATTERN**: same minimal style.
- **VALIDATE**: file exists and renders.

### 10. UPDATE `src/grins_platform/services/email_service.py` — ADD `send_estimate_email`
- **IMPLEMENT**: Add a new method mirroring `send_welcome_email`:
  ```python
  def send_estimate_email(
      self,
      *,
      customer: Customer | Lead,
      estimate: Estimate,
      portal_url: str,
  ) -> dict[str, Any]:
      """Send the estimate-ready email with portal link.

      Validates: Feature — estimate approval email portal.
      """
      self.log_started("send_estimate_email", estimate_id=str(estimate.id))
      email = getattr(customer, "email", None)
      if not email:
          self.logger.warning("email.estimate_sent.skipped",
                              estimate_id=str(estimate.id), reason="no_email_address")
          return {"sent": False, "reason": "no_email"}
      customer_name = (
          getattr(customer, "full_name", None)
          or getattr(customer, "first_name", None)
          or "Valued Customer"
      )
      context = {
          "customer_name": customer_name,
          "total": str(estimate.total),
          "valid_until": (
              estimate.valid_until.date().isoformat()
              if getattr(estimate, "valid_until", None) else ""
          ),
          "portal_url": portal_url,
      }
      html_body = self._render_template("estimate_sent.html", context)
      classification = self._classify_email("estimate_sent")
      sent = self._send_email(
          to_email=email, subject="Your estimate from Grin's Irrigation",
          html_body=html_body, email_type="estimate_sent",
          classification=classification,
      )
      self.log_completed("send_estimate_email", sent=sent, estimate_id=str(estimate.id))
      return {
          "sent": sent,
          "sent_via": "email" if sent else "pending",
          "recipient_email": email,
          "content": html_body,
          "disclosure_type": None,
      }
  ```
- **PATTERN**: `send_welcome_email` (lines 197–256) is the canonical shape.
- **IMPORTS**: `Estimate` is already declared in `TYPE_CHECKING`. Add it: `from grins_platform.models.estimate import Estimate` to the `TYPE_CHECKING` block.
- **GOTCHA**: Use `_render_template` — it auto-injects `business_name`, `business_phone`, `business_email`, and a fallback `portal_url` from settings. **The explicit `portal_url` in `context` overrides the fallback**, so this is safe. Do NOT format the total as currency here — let the template do `${{ total }}`. Do NOT pass `Customer.id` (PII-bordering), but estimate_id is fine in logs.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_send_estimate_email.py -v` (test file authored in step 19).

### 11. UPDATE `src/grins_platform/services/email_service.py` — ADD `send_internal_estimate_decision_email` + `send_internal_estimate_bounce_email`
- **IMPLEMENT**:
  ```python
  def send_internal_estimate_decision_email(self, *, to_email, decision, customer_name,
                                              total, estimate_id, rejection_reason=None):
      subject = f"Estimate {decision.upper()} for {customer_name}"
      html_body = self._render_template("internal_estimate_decision.html", {
          "customer_name": customer_name, "decision": decision,
          "total": str(total), "estimate_id": str(estimate_id),
          "rejection_reason": rejection_reason or "",
      })
      return self._send_email(to_email=to_email, subject=subject, html_body=html_body,
                              email_type="internal_estimate_decision",
                              classification=EmailType.TRANSACTIONAL)
  ```
  Mirror for `send_internal_estimate_bounce_email(*, to_email, recipient_email, reason, estimate_id)` rendering `internal_estimate_bounce.html`.
- **PATTERN**: see `send_welcome_email`.
- **GOTCHA**: Both methods return `bool` from `_send_email`, not the full result dict — these are fire-and-log helpers, callers don't care about the dict shape.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_email_service_resend.py::test_send_internal_estimate_decision -v`

### 12. UPDATE `src/grins_platform/services/estimate_service.py` — token + valid_until defaults
- **IMPLEMENT**:
  - Line 48: `TOKEN_VALIDITY_DAYS = 60`.
  - Line 156: `valid_until=data.valid_until or (now + timedelta(days=60))`.
  - Update docstring at line 111–112 to say "60 days" instead of "30 days".
- **PATTERN**: existing constants and create-call.
- **GOTCHA**: There may be existing tests that assert the old 30-day default. Search `src/grins_platform/tests` for `timedelta(days=30)` and update accordingly. **Don't** change tests that exercise an explicit `valid_until` override — that path is independent.
- **VALIDATE**: `grep -n "TOKEN_VALIDITY_DAYS = 60" src/grins_platform/services/estimate_service.py && uv run pytest src/grins_platform/tests/functional/test_estimate_operations_functional.py -v`

### 13. UPDATE `src/grins_platform/services/estimate_service.py` — `__init__` requires `portal_base_url`
- **IMPLEMENT**: Remove the default from `portal_base_url: str = "https://portal.grins.com"` (line 81). Now `portal_base_url: str` (required).
- **PATTERN**: lines 75–97.
- **GOTCHA**: Every callsite of `EstimateService(...)` now must pass `portal_base_url=...`. Callsites to update:
  - `api/v1/dependencies.py:257` — pass `portal_base_url=EmailSettings().portal_base_url` (or import a settings singleton).
  - `api/v1/dependencies.py:365` — same.
  - `api/v1/portal.py:71` — same; also inject `email_service` and `sms_service`.
  - Tests in `tests/functional/test_estimate_operations_functional.py:181` — already pass `portal_base_url=portal_base_url`, so safe.
  - Any other test that constructs `EstimateService(...)` without it will fail loudly — fix at compile time.
- **VALIDATE**: `uv run mypy src/grins_platform/services/estimate_service.py` (no errors), `uv run pyright src/grins_platform/api/v1/dependencies.py src/grins_platform/api/v1/portal.py`.

### 13a. UPDATE `src/grins_platform/services/estimate_service.py` — fix portal URL path
- **IMPLEMENT**: Change both URL-builder lines (currently lines 273 and 598) from:
  ```python
  portal_url = f"{self.portal_base_url}/estimates/{estimate.customer_token}"
  ```
  to:
  ```python
  portal_url = f"{self.portal_base_url}/portal/estimates/{estimate.customer_token}"
  ```
- **PATTERN**: matches the React Router route at `frontend/src/core/router/index.tsx:140-157` (`/portal/estimates/:token` → `EstimateReviewPage`).
- **GOTCHA**: This is a pre-existing bug surfaced by the dev environment shift. The legacy default `https://portal.grins.com` happened to work because that subdomain (if it existed) presumably had a rewrite stripping the path. The new convention: `PORTAL_BASE_URL` is **just the origin** (e.g., `https://frontend-git-dev-kirilldr01s-projects.vercel.app` or `https://portal.grinsirrigation.com`), and the backend appends the full route path `/portal/estimates/{token}`. If a future portal subdomain wants the route at root (e.g., `portal.grinsirrigation.com/estimates/abc` instead of `.../portal/estimates/abc`), use a Vercel rewrite — not a backend split.
- **EXISTING-TEST IMPACT**: Tests that assert the constructed `portal_url` shape (search for `/estimates/{` in `tests/`) need their assertion strings updated to include `/portal`. Specifically: `tests/integration/test_external_service_integration.py` and `tests/functional/test_estimate_operations_functional.py` likely have such assertions.
- **VALIDATE**:
  ```bash
  grep -n "portal_url = " src/grins_platform/services/estimate_service.py
  # Expected: both lines now contain "/portal/estimates/"
  uv run pytest src/grins_platform/tests/ -v -k "send_estimate or portal_url" 2>&1 | tail -20
  ```

### 14. UPDATE `src/grins_platform/services/estimate_service.py` — replace `send_estimate` email-branch
- **IMPLEMENT**: Replace lines 300–311 (the `if self.email_service and estimate.customer:` log-only block) with a real call:
  ```python
  if self.email_service and estimate.customer:
      email = getattr(estimate.customer, "email", None)
      if email:
          try:
              result = self.email_service.send_estimate_email(
                  customer=estimate.customer,
                  estimate=estimate,
                  portal_url=portal_url,
              )
              if result.get("sent"):
                  sent_via.append("email")
          except Exception as e:
              self.log_failed("send_estimate_email", error=e,
                              estimate_id=str(estimate_id))
  ```
  Add an analogous block in the `if not sent_via and estimate.lead:` branch (after the existing SMS-via-lead block, before `_schedule_follow_ups`). The lead branch is currently SMS-only — extend with the same email pattern using `getattr(estimate.lead, "email", None)`.
- **PATTERN**: SMS branch at lines 279–298 (try/except, append on success).
- **IMPORTS**: no new imports — `EmailService` is already in `TYPE_CHECKING`.
- **GOTCHA**: `EstimateService` is async but `send_estimate_email` is sync (matches existing `send_welcome_email`). Do NOT `await` it. Do NOT roll back the SENT-status update if email fails — that's already enforced by the existing structure (status is updated before any send branches).
- **VALIDATE**: `uv run pytest src/grins_platform/tests/functional/test_estimate_operations_functional.py::test_send_estimate -v`

### 15. UPDATE `src/grins_platform/services/estimate_service.py` — add `_notify_internal_decision`
- **IMPLEMENT**: Add a private async method (after `reject_via_portal`, before `# Background Jobs` comment block ~line 511):
  ```python
  async def _notify_internal_decision(
      self,
      estimate: Estimate,
      decision: Literal["approved", "rejected"],
  ) -> None:
      """Fire-and-log internal staff notification. Never raises.

      Failures (vendor outage, no recipients configured) are logged but
      never undo the customer-side decision.
      """
      recipient_email = os.getenv("INTERNAL_NOTIFICATION_EMAIL", "").strip()
      recipient_phone = os.getenv("INTERNAL_NOTIFICATION_PHONE", "").strip()
      customer_name = self._resolve_customer_name(estimate)
      total = str(getattr(estimate, "total", "0.00"))
      rejection_reason = (
          getattr(estimate, "rejected_reason", None)
          if decision == "rejected" else None
      )

      if recipient_email and self.email_service:
          try:
              self.email_service.send_internal_estimate_decision_email(
                  to_email=recipient_email,
                  decision=decision,
                  customer_name=customer_name,
                  total=total,
                  estimate_id=estimate.id,
                  rejection_reason=rejection_reason,
              )
          except Exception as e:
              self.log_failed("notify_internal_decision_email",
                              error=e, estimate_id=str(estimate.id))

      if recipient_phone and self.sms_service:
          subject_word = decision.upper()
          sms_text = (
              f"Estimate {subject_word} for {customer_name}. "
              f"Total ${total}. Open admin to action."
          )
          try:
              await self.sms_service.send_automated_message(
                  phone=recipient_phone,
                  message=sms_text,
                  message_type="internal_estimate_decision",
              )
          except Exception as e:
              self.log_failed("notify_internal_decision_sms",
                              error=e, estimate_id=str(estimate.id))
  ```
  Add a private helper `_resolve_customer_name(estimate)` that returns `estimate.customer.full_name` if a customer exists, else `estimate.lead.first_name`/`last_name` joined, else `"a customer"`.
- **PATTERN**: design.md §6.1.
- **IMPORTS**: `import os` at top of `estimate_service.py` (currently absent — uses `from __future__ import annotations` and `datetime`/`uuid` only). Also `from typing import Literal` (already imports `Any` and `TYPE_CHECKING`).
- **GOTCHA**: `send_automated_message` does not accept arbitrary `message_type` — `_AUTOMATED_STR_TO_MESSAGE_TYPE` (`sms_service.py:128`) maps unknowns to `MessageType.AUTOMATED_NOTIFICATION` as a fallback, which is fine. **OR** add `"internal_estimate_decision": MessageType.AUTOMATED_NOTIFICATION` to that map for cleanliness. Going through `send_automated_message` (vs raw provider call) gets us SentMessage audit, dedup, consent check, time-window enforcement. Internal staff numbers are normally SMS_TEST_PHONE_ALLOWLIST'd in dev so the existing guard already protects.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_estimate_internal_notification.py -v`

### 16. UPDATE `src/grins_platform/services/estimate_service.py` — invoke `_notify_internal_decision`
- **IMPLEMENT**:
  - In `approve_via_portal` (line 354–433): after the lead-tag update block (~line 426), before `self.log_completed`, add `await self._notify_internal_decision(updated, "approved")`.
  - In `reject_via_portal` (line 435–509): same insertion point — after the lead-tag update, before `log_completed`, add `await self._notify_internal_decision(updated, "rejected")`.
- **PATTERN**: existing structure.
- **GOTCHA**: Use the post-update `updated` Estimate (not the pre-update `estimate`) so the rejection_reason is populated. Wrap nothing — `_notify_internal_decision` is fire-and-forget by design and never raises.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/functional/test_estimate_operations_functional.py -v -k approve`

### 17. CREATE `src/grins_platform/tests/unit/test_email_recipient_allowlist.py`
- **IMPLEMENT**: Three test classes:
  - `TestNormalizeEmail` — strips whitespace, lowercases.
  - `TestLoadEmailAllowlist` — unset env → `None`; empty env → `None`; comma-only → `None`; single → list of 1; comma-separated → list of N.
  - `TestEnforceEmailRecipientAllowlist` — guard active + recipient allowed → no raise; guard active + recipient disallowed → `EmailRecipientNotAllowedError` with `provider=` in msg; guard inactive (env unset) → no raise even for any recipient.
- **PATTERN**: `tests/unit/test_pbt_callrail_sms.py` for the SMS allowlist analog.
- **IMPORTS**: `import os`, `from unittest.mock import patch`, plus the public API from `grins_platform.services.email_service`.
- **GOTCHA**: Use `monkeypatch.setenv` (pytest fixture) or `with patch.dict(os.environ, ...)` to avoid leaking env state between tests.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_email_recipient_allowlist.py -v --tb=short`

### 18. CREATE `src/grins_platform/tests/unit/test_email_service_resend.py`
- **IMPLEMENT**: Mock `resend.Emails.send` to assert the payload shape.
  - `test_send_email_with_configured_settings_calls_resend_with_expected_payload`
  - `test_send_email_returns_false_when_resend_raises`
  - `test_send_email_raises_when_recipient_blocked_by_allowlist`
  - `test_send_email_returns_false_when_settings_not_configured`
  - `test_send_email_includes_reply_to_info_address`
- **PATTERN**: `tests/unit/test_email_service.py` for fixture style.
- **IMPORTS**: `from unittest.mock import MagicMock, patch`.
- **GOTCHA**: `resend` is a module-level singleton — patch `resend.Emails.send` (not `resend.api_key`). For the allowlist test, set `EMAIL_TEST_ADDRESS_ALLOWLIST=allowed@example.com` via `monkeypatch.setenv` and call with `to_email="other@example.com"`.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_email_service_resend.py -v --tb=short`

### 19. CREATE `src/grins_platform/tests/unit/test_send_estimate_email.py`
- **IMPLEMENT**:
  - `test_send_estimate_email_with_valid_customer_returns_sent_true` — mock `_send_email` to return True, assert dict shape.
  - `test_send_estimate_email_without_email_returns_no_email_reason`
  - `test_send_estimate_email_uses_estimate_total_and_valid_until_in_template`
  - `test_send_estimate_email_supports_lead_when_no_customer` — pass a Lead-like MagicMock with `email` and `first_name`.
- **PATTERN**: `tests/unit/test_email_service.py` lines 1–96.
- **GOTCHA**: Use `_mock_estimate()` helper authoring inline. Stub the Jinja env or let it actually render `estimate_sent.html` — the template must already exist (step 6) for the test to pass, so step 6 is a hard prerequisite.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_send_estimate_email.py -v`

### 20. CREATE `src/grins_platform/tests/unit/test_estimate_internal_notification.py`
- **IMPLEMENT**:
  - `test_notify_internal_decision_calls_email_when_recipient_set` — set `INTERNAL_NOTIFICATION_EMAIL=staff@x.com`, assert `email_service.send_internal_estimate_decision_email` called.
  - `test_notify_internal_decision_calls_sms_when_phone_set` — set `INTERNAL_NOTIFICATION_PHONE=+19527373312`, assert `sms_service.send_automated_message` awaited.
  - `test_notify_internal_decision_swallows_email_failure` — email service raises, ensure no exception propagates and a log_failed call was made.
  - `test_notify_internal_decision_swallows_sms_failure` — same for SMS.
  - `test_notify_internal_decision_skips_when_env_unset` — env empty, neither service is called.
- **PATTERN**: `tests/unit/test_estimate_service.py` for service-level test style.
- **GOTCHA**: `monkeypatch.setenv` per test. Mock both `email_service` and `sms_service` on `EstimateService` ctor.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_estimate_internal_notification.py -v`

### 21. CREATE migration `src/grins_platform/migrations/versions/20260428_100000_add_customer_email_bounced_at.py`
- **IMPLEMENT**:
  ```python
  """Add customers.email_bounced_at column.

  Revision ID: 20260428_100000
  Revises: 20260427_100000
  Validates: Estimate approval email portal — Resend bounce handling.
  """
  from __future__ import annotations
  from collections.abc import Sequence
  import sqlalchemy as sa
  from alembic import op

  revision: str = "20260428_100000"
  down_revision: str | None = "20260427_100000"
  branch_labels: str | Sequence[str] | None = None
  depends_on: str | Sequence[str] | None = None


  def upgrade() -> None:
      op.add_column(
          "customers",
          sa.Column("email_bounced_at", sa.TIMESTAMP(timezone=True), nullable=True),
      )


  def downgrade() -> None:
      op.drop_column("customers", "email_bounced_at")
  ```
- **PATTERN**: `migrations/versions/20260427_100000_add_webauthn_credentials_table.py`.
- **GOTCHA**: Verify the latest revision id at the time of execution (run `alembic heads` — it should be `20260427_100000`). If a newer migration has merged since this plan was written, set `down_revision` to whatever `alembic heads` returns.
- **VALIDATE**: `uv run alembic upgrade head && uv run alembic downgrade -1 && uv run alembic upgrade head`

### 22. UPDATE `src/grins_platform/models/customer.py`
- **IMPLEMENT**: Add a new mapped column near the other email-related columns (~line 153–161, near `email_opt_in_at`):
  ```python
  email_bounced_at: Mapped[Optional[datetime]] = mapped_column(
      TIMESTAMP(timezone=True),
      nullable=True,
  )
  ```
- **PATTERN**: existing `email_opt_in_at` column (line 153).
- **IMPORTS**: already imported in this file.
- **GOTCHA**: Soft flag only — do NOT block sends when this is set. The webhook handler stamps it; an admin can clear it via SQL or a future UI.
- **VALIDATE**: `uv run python -c "from grins_platform.models.customer import Customer; assert hasattr(Customer, 'email_bounced_at')"`

### 23. CREATE `src/grins_platform/services/resend_webhook_security.py`
- **IMPLEMENT**:
  ```python
  """Resend webhook signature verification.

  Wraps the official `resend.webhooks.verify` helper so the rest of the
  codebase has a typed exception + a single import path matching the
  SignWell webhook abstraction.

  Validates: Estimate approval email portal — bounce handling.
  """
  from __future__ import annotations

  import resend


  class ResendWebhookVerificationError(Exception):
      """Raised when Resend webhook signature does not verify."""


  def verify_resend_webhook_signature(
      *,
      secret: str,
      headers: dict[str, str],
      raw_body: bytes,
  ) -> dict[str, object]:
      """Verify a Resend (Svix-format) webhook signature and return the parsed payload.

      The Resend Python SDK ships an official `resend.webhooks.verify`
      helper that handles the Svix algorithm internally
      (HMAC-SHA256 of `{svix-id}.{svix-timestamp}.{body}` with the
      base64-decoded secret minus the `whsec_` prefix, base64-encoded
      digest, constant-time compare). We delegate to it rather than
      hand-rolling HMAC — the algorithm is non-trivial and tested
      upstream.

      Args:
          secret: The webhook signing secret (`whsec_…` form, exactly
              as copied from the Resend dashboard).
          headers: Lowercased request headers dict containing
              `svix-id`, `svix-timestamp`, `svix-signature`.
          raw_body: Raw request body bytes (must be UNMODIFIED — JSON
              re-serialization breaks signature).

      Returns:
          The parsed JSON payload dict.

      Raises:
          ResendWebhookVerificationError: If secret is missing/blank,
              required headers are missing, or signature does not verify.
      """
      if not secret:
          raise ResendWebhookVerificationError("RESEND_WEBHOOK_SECRET not configured")
      try:
          # `resend.webhooks.verify` raises `resend.WebhookVerificationError`
          # (or similar) on signature mismatch. The exact name varies by
          # SDK minor — catch the broad Exception class and re-raise our
          # typed error to keep the API stable.
          payload = resend.webhooks.verify(
              payload=raw_body,
              headers=headers,
              secret=secret,
          )
      except Exception as e:
          raise ResendWebhookVerificationError(f"signature_invalid: {e}") from e
      if not isinstance(payload, dict):
          raise ResendWebhookVerificationError("payload_not_dict")
      return payload
  ```
- **PATTERN**: `services/signwell/client.py:183-210` (typed exception, raise-on-fail discipline) + the official Resend SDK helper.
- **IMPORTS**: `import resend` (added in step 1's dep). No `hmac`, no `hashlib`, no `base64` — the SDK handles it all.
- **GOTCHA**:
  - **Verified against `https://resend.com/docs/dashboard/webhooks/verify-webhooks-requests` and the v2 SDK README at `https://github.com/resend/resend-python` (2026-04-25):** the recommended path is `resend.webhooks.verify(payload, headers, secret)`. Manual HMAC is documented as a fallback but is non-trivial; **do not hand-roll**.
  - The SDK's exact exception class name has churned across minor versions (`resend.WebhookVerificationError`, `resend.errors.WebhookVerificationError`, etc.). Catching base `Exception` and re-raising as `ResendWebhookVerificationError` insulates the rest of the codebase from SDK churn.
  - Headers must be lowercased before passing — Svix (and most webhook libs) expect canonical header names. FastAPI's `Request.headers` is already case-insensitive, but `dict(request.headers)` may preserve the original casing — convert explicitly.
- **VALIDATE**: `uv run python -c "from grins_platform.services.resend_webhook_security import verify_resend_webhook_signature, ResendWebhookVerificationError; print('OK')"` then `uv run pytest src/grins_platform/tests/unit/test_resend_webhook.py -v`

### 24. CREATE `src/grins_platform/api/v1/resend_webhooks.py`
- **IMPLEMENT**:
  ```python
  """Resend email webhook endpoint.

  Receives bounce/complaint events from Resend, verifies HMAC signature,
  and notifies internal staff.

  Validates: Estimate approval email portal — bounce handling.
  """
  from __future__ import annotations
  from datetime import datetime, timezone
  from typing import TYPE_CHECKING, Any
  from fastapi import APIRouter, Depends, Request, Response, status
  from sqlalchemy import select, update

  from grins_platform.database import get_db_session
  from grins_platform.log_config import LoggerMixin, get_logger
  from grins_platform.middleware.rate_limit import WEBHOOK_LIMIT, limiter
  from grins_platform.models.customer import Customer
  from grins_platform.services.email_config import EmailSettings
  from grins_platform.services.email_service import EmailService
  from grins_platform.services.resend_webhook_security import (
      ResendWebhookVerificationError,
      verify_resend_webhook_signature,
  )
  from grins_platform.services.sms.factory import get_sms_provider
  from grins_platform.services.sms_service import SMSService

  if TYPE_CHECKING:
      from sqlalchemy.ext.asyncio import AsyncSession

  logger = get_logger(__name__)
  router = APIRouter(prefix="/webhooks/resend", tags=["resend-webhooks"])


  class _ResendWebhookEndpoints(LoggerMixin):
      DOMAIN = "api"


  _ep = _ResendWebhookEndpoints()


  @router.post("", status_code=status.HTTP_200_OK,
               summary="Handle Resend email webhook")
  @limiter.limit(WEBHOOK_LIMIT)
  async def resend_webhook(
      request: Request,
      session: AsyncSession = Depends(get_db_session),
  ) -> Response:
      _ep.log_started("resend_webhook")
      raw_body = await request.body()
      # Lowercase headers for Svix verifier
      headers = {k.lower(): v for k, v in request.headers.items()}

      settings = EmailSettings()
      try:
          payload: dict[str, Any] = verify_resend_webhook_signature(
              secret=settings.resend_webhook_secret,
              headers=headers,
              raw_body=raw_body,
          )
      except ResendWebhookVerificationError as e:
          logger.warning("resend.webhook.signature_invalid", error=str(e))
          return Response(content='{"error":"Invalid signature"}',
                          status_code=status.HTTP_401_UNAUTHORIZED,
                          media_type="application/json")

      event_type = payload.get("type", "")
      data = payload.get("data", {}) or {}

      if event_type not in {"email.bounced", "email.complained"}:
          logger.info("resend.webhook.ignored_event", event_type=event_type)
          _ep.log_completed("resend_webhook", event_type=event_type, action="ignored")
          return Response(status_code=status.HTTP_200_OK)

      # Resend bounce payload — verified against
      # https://resend.com/docs/webhooks/emails/bounced (2026-04-25):
      #   data.to                  → list[str] of recipients
      #   data.bounce.type         → "Permanent" | "Temporary"
      #   data.bounce.subType      → finer-grained category (e.g. "Suppressed")
      #   data.bounce.message      → human-readable reason
      #   data.tags                → custom tags set on send
      bounce = data.get("bounce", {}) or {}
      bounce_type = bounce.get("type", "Permanent")  # default to permanent on missing
      to_emails = data.get("to", []) or []
      to_email = to_emails[0] if to_emails else None
      reason = bounce.get("message") or "unknown"

      # Resolve estimate_id from tags. Tags shape: list[{name, value}].
      tags = data.get("tags", []) or []
      estimate_id = "unknown"
      if isinstance(tags, list):
          for tag in tags:
              if isinstance(tag, dict) and tag.get("name") == "estimate_id":
                  estimate_id = str(tag.get("value", "unknown"))
                  break

      if not to_email:
          logger.warning("resend.webhook.bounce_missing_recipient",
                         payload_keys=list(payload.keys()))
          return Response(status_code=status.HTTP_200_OK)

      # Hard-bounce ("Permanent") flags the customer; "Temporary" just logs
      if bounce_type == "Permanent" and event_type == "email.bounced":
          stmt = (update(Customer)
                  .where(Customer.email == to_email)
                  .values(email_bounced_at=datetime.now(timezone.utc)))
          try:
              await session.execute(stmt)
              await session.commit()
          except Exception as e:
              logger.warning("resend.webhook.bounce_flag_failed", error=str(e))

      # Fire internal notification (best-effort)
      import os
      recipient_email = os.getenv("INTERNAL_NOTIFICATION_EMAIL", "").strip()
      recipient_phone = os.getenv("INTERNAL_NOTIFICATION_PHONE", "").strip()
      email_service = EmailService()
      if recipient_email:
          try:
              email_service.send_internal_estimate_bounce_email(
                  to_email=recipient_email,
                  recipient_email=to_email,
                  reason=reason,
                  estimate_id=estimate_id,
              )
          except Exception as e:
              logger.warning("resend.webhook.bounce_email_failed", error=str(e))
      if recipient_phone:
          try:
              sms_service = SMSService(session=session, provider=get_sms_provider())
              sms_text = f"Estimate email BOUNCED for {to_email}. Reason: {reason[:80]}"
              await sms_service.send_automated_message(
                  phone=recipient_phone, message=sms_text,
                  message_type="internal_estimate_bounce",
              )
          except Exception as e:
              logger.warning("resend.webhook.bounce_sms_failed", error=str(e))

      _ep.log_completed("resend_webhook", event_type=event_type, bounce_type=bounce_type)
      return Response(status_code=status.HTTP_200_OK)
  ```
- **PATTERN**: `api/v1/signwell_webhooks.py` (full file).
- **IMPORTS**: see above; all already exist in the codebase.
- **GOTCHA**:
  - **Bounce payload paths are now correct (verified 2026-04-25):** `data.bounce.type` (NOT `subType`) holds `"Permanent"` or `"Temporary"`. Resend uses `"Temporary"` not `"Transient"`. `data.bounce.message` is the reason string. `data.to` is an array of strings.
  - The `tags` field in the bounce payload echoes back what we set in `_send_email` (step 4 / step 25). To correlate the bounce to a specific estimate, `send_estimate_email` must call `_send_email` with an extra tag `{"name": "estimate_id", "value": str(estimate.id)}` — see step 25.
  - Always return 200 to Resend on a verified payload (even for ignored events) — non-2xx triggers retry storms.
  - The verification call (`verify_resend_webhook_signature`) BOTH verifies AND returns the parsed payload — we do NOT call `request.json()` separately. JSON re-parsing would risk byte-level differences that fail signature verification on retry.
  - Rate-limit annotation `@limiter.limit(WEBHOOK_LIMIT)` MUST appear immediately under `@router.post(...)` per slowapi semantics.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_resend_webhook.py -v`

### 25. UPDATE `src/grins_platform/services/email_service.py` — pass `tags` in `_send_email`
- **IMPLEMENT**: Inside `_send_email`, after building the payload, add `"tags": [{"name": "email_type", "value": email_type}]` to the dict passed to `resend.Emails.send`.
- **PATTERN**: see Resend SDK docs for `tags` field shape.
- **GOTCHA**: Tags propagate to the webhook's `data.tags`. For correlating back to a specific estimate later, add a second tag in `send_estimate_email` only (override): pass `extra_tags=[{"name": "estimate_id", "value": str(estimate.id)}]` through to `_send_email` via a new optional kwarg, and merge into the tags list. Keep the kwarg optional so other senders are unaffected.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_email_service_resend.py::test_send_email_passes_tags -v`

### 26. CREATE `src/grins_platform/tests/unit/test_resend_webhook.py`
- **IMPLEMENT**:
  - `test_resend_webhook_with_valid_signature_processes_bounce` — mock signature verify, post `email.bounced` payload, assert internal notification dispatched.
  - `test_resend_webhook_with_invalid_signature_returns_401`
  - `test_resend_webhook_with_unknown_event_returns_200_and_skips`
  - `test_resend_webhook_permanent_bounce_stamps_customer_email_bounced_at`
  - `test_resend_webhook_transient_bounce_does_not_flag_customer`
  - `test_resend_webhook_with_no_recipient_returns_200_and_logs`
- **PATTERN**: existing webhook tests for SignWell.
- **IMPORTS**: `httpx.AsyncClient` or `TestClient` for the FastAPI app — use whichever the rest of the test suite uses.
- **GOTCHA**: Mock `EmailSettings.resend_webhook_secret` via `monkeypatch.setenv`. Mock `verify_resend_webhook_signature` directly to avoid needing a real Svix-format signature in tests.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_resend_webhook.py -v --tb=short`

### 27. UPDATE `src/grins_platform/api/v1/router.py` — register the webhook router
- **IMPLEMENT**: Mirror the existing `signwell_webhooks_router` import + include block. Import `from grins_platform.api.v1.resend_webhooks import router as resend_webhooks_router` near line 62, and add an `api_router.include_router(resend_webhooks_router, tags=["resend-webhooks"])` block near line 236.
- **PATTERN**: existing `callrail_webhooks_router`, `signwell_webhooks_router`, `webhooks_router` registrations (lines 27, 62, 74, 224, 230, 236).
- **GOTCHA**: The router itself already has `prefix="/webhooks/resend"`, so do NOT pass `prefix=` here.
- **VALIDATE**: `uv run python -c "from grins_platform.app import create_app; app = create_app(); paths = [r.path for r in app.routes]; assert any('/webhooks/resend' in p for p in paths)"` (adjust if `create_app` is named differently — check `app.py`).

### 28. UPDATE `src/grins_platform/api/v1/dependencies.py` — wire EmailService + SMSService + SalesPipelineService + portal_base_url into get_estimate_service
- **IMPLEMENT**: Replace `get_estimate_service` body (lines 353–365 of the current file) to construct a fully-wired EstimateService:
  ```python
  async def get_estimate_service(
      session: Annotated[AsyncSession, Depends(get_db_session)],
      job_service: Annotated[JobService, Depends(get_job_service)],
  ) -> EstimateService:
      repository = EstimateRepository(session=session)
      email_service = EmailService()
      sms_service = SMSService(session=session, provider=get_sms_provider())
      sales_pipeline_service = SalesPipelineService(
          job_service=job_service,
          audit_service=AuditService(),
      )
      return EstimateService(
          estimate_repository=repository,
          lead_service=None,
          email_service=email_service,
          sms_service=sms_service,
          sales_pipeline_service=sales_pipeline_service,
          portal_base_url=EmailSettings().portal_base_url,
      )
  ```
- **PATTERN**: `_get_pipeline_service` at `src/grins_platform/api/v1/sales_pipeline.py:169-175` (verified — this is the canonical SalesPipelineService construction shape used elsewhere in the codebase).
- **IMPORTS**: add to the existing import block at top of `dependencies.py`:
  ```python
  from grins_platform.services.audit_service import AuditService
  from grins_platform.services.email_config import EmailSettings
  from grins_platform.services.sales_pipeline_service import SalesPipelineService
  from grins_platform.services.sms.factory import get_sms_provider
  ```
  `JobService`, `EmailService`, `SMSService`, `EstimateRepository` already imported.
- **GOTCHA**:
  - **Do NOT pass `lead_service`.** `LeadService.__init__` requires `(lead_repository, customer_service, job_service, staff_repository, ...)` — instantiating it here would force this dependency to also pull in `CustomerService` and `StaffRepository`. The existing `get_estimate_service` (pre-feature) already passes nothing for `lead_service`, so the lead-tag flip in `approve_via_portal` was already a no-op in this DI path. Preserving that status quo. (If the team later wants the lead-tag flip working in production, that's a separate ticket — not in this feature's scope.)
  - `AuditService()` takes no constructor args (verified at `services/audit_service.py:33-44` — no `__init__` defined; inherits `LoggerMixin.__init__()`).
  - `EmailSettings()` is cheap on every call (Pydantic memoizes env reads internally), so re-instantiating per request is fine.
  - The `job_service: Annotated[JobService, Depends(get_job_service)]` parameter chains through FastAPI's DI — this is the same pattern `_get_pipeline_service` uses; the agent should NOT manually construct `JobService` inline.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_estimate_service.py -v && uv run mypy src/grins_platform/api/v1/dependencies.py`

### 29. UPDATE `src/grins_platform/api/v1/portal.py` — wire EmailService + SMSService + SalesPipelineService into _get_estimate_service
- **IMPLEMENT**: Replace `_get_estimate_service` body (lines 59–71 of the current file) with:
  ```python
  async def _get_estimate_service(
      session: Annotated[AsyncSession, Depends(get_db_session)],
      job_service: Annotated[JobService, Depends(get_job_service)],
  ) -> EstimateService:
      repo = EstimateRepository(session=session)
      email_service = EmailService()
      sms_service = SMSService(session=session, provider=get_sms_provider())
      sales_pipeline_service = SalesPipelineService(
          job_service=job_service,
          audit_service=AuditService(),
      )
      return EstimateService(
          estimate_repository=repo,
          lead_service=None,
          email_service=email_service,
          sms_service=sms_service,
          sales_pipeline_service=sales_pipeline_service,
          portal_base_url=EmailSettings().portal_base_url,
      )
  ```
- **PATTERN**: identical wiring to step 28 — they must stay in lock-step or the customer-side approve path gets a different EstimateService config than the admin-side path.
- **IMPORTS**: add to `portal.py` imports:
  ```python
  from grins_platform.api.v1.dependencies import get_job_service
  from grins_platform.services.audit_service import AuditService
  from grins_platform.services.email_config import EmailSettings
  from grins_platform.services.email_service import EmailService
  from grins_platform.services.job_service import JobService
  from grins_platform.services.sales_pipeline_service import SalesPipelineService
  from grins_platform.services.sms.factory import get_sms_provider
  from grins_platform.services.sms_service import SMSService
  ```
- **GOTCHA**: This is the **critical injection point** for Q-A. Without `sales_pipeline_service` here, the breadcrumb method authored in step 38 will silently no-op when customers approve/reject via portal — defeating the purpose of Q-A. Same `lead_service=None` reasoning as step 28 applies.
- **VALIDATE**: `uv run mypy src/grins_platform/api/v1/portal.py` then dev manual: hit `POST /api/v1/portal/estimates/{token}/approve` with a real estimate → confirm internal email + SMS arrive AND a `SalesEntry.notes` row gains the breadcrumb line.

### 30. UPDATE `src/grins_platform/api/v1/dependencies.py` — get_full_appointment_service portal_base_url
- **IMPLEMENT**: Line 257 — pass `portal_base_url=EmailSettings().portal_base_url` to `EstimateService(...)`. (No `email_service`/`sms_service` needed here; the appointment-driven path doesn't call `send_estimate`.)
- **PATTERN**: step 28.
- **VALIDATE**: `uv run mypy src/grins_platform/api/v1/dependencies.py`

### 31. UPDATE `src/grins_platform/api/v1/portal.py` — apply rate limits
- **IMPLEMENT**: Decorate the three estimate endpoints (`get_portal_estimate`, `approve_portal_estimate`, `reject_portal_estimate`) with `@limiter.limit(PORTAL_LIMIT)`. The `Request` parameter is already present in all three.
- **PATTERN**: any other rate-limited route in the codebase — search for `@limiter.limit(`.
- **IMPORTS**: `from grins_platform.middleware.rate_limit import PORTAL_LIMIT, limiter`.
- **GOTCHA**: slowapi requires the route to accept a `request: Request` parameter — already true.
- **VALIDATE**: dev — hit any of those endpoints 25 times/minute with `curl`; expect 429 after 20.

### 32. UPDATE `src/grins_platform/api/v1/portal.py` — (optional) SENT → VIEWED transition
- **IMPLEMENT**: In `get_portal_estimate`, after `_validate_portal_token` succeeds and you have the `estimate` object, if `estimate.status == EstimateStatus.SENT.value`, call `await service.repo.update(estimate.id, status=EstimateStatus.VIEWED.value)`. Idempotent — second view is a no-op.
- **PATTERN**: `service.approve_via_portal` (which uses `repo.update`).
- **GOTCHA**: This is OPTIONAL polish per design.md §7. Skip if time-constrained.
- **VALIDATE**: dev — first GET on a SENT estimate → DB shows `status=viewed`; second GET → no change.

### 33. UPDATE `.env.example`
- **IMPLEMENT**: Add the following block (after the existing `EMAIL_API_KEY` block at line 130–134):
  ```bash
  # -----------------------------------------------------------------------------
  # Resend (email provider — primary)
  # -----------------------------------------------------------------------------
  RESEND_API_KEY=
  # Webhook signing secret from Resend dashboard (whsec_…)
  RESEND_WEBHOOK_SECRET=

  # -----------------------------------------------------------------------------
  # Customer portal
  # -----------------------------------------------------------------------------
  # Dev: http://localhost:5173 ; Prod: https://portal.grinsirrigation.com
  PORTAL_BASE_URL=http://localhost:5173

  # -----------------------------------------------------------------------------
  # Email Safety Guard (dev/staging only — leave UNSET in production)
  # -----------------------------------------------------------------------------
  # Comma-separated email addresses allowed to receive real outbound email.
  # EMAIL_TEST_ADDRESS_ALLOWLIST=kirillrakitinsecond@gmail.com

  # -----------------------------------------------------------------------------
  # Internal notifications (sales-team alerts on approve/reject/bounce)
  # -----------------------------------------------------------------------------
  # Dev: kirillrakitinsecond@gmail.com / +19527373312 ; Prod: TBD before cutover.
  INTERNAL_NOTIFICATION_EMAIL=
  INTERNAL_NOTIFICATION_PHONE=
  ```
- **PATTERN**: existing `.env.example` blocks.
- **GOTCHA**: Use `=` with empty default (not `=your-key-here` placeholder) for secrets — otherwise dev environments accidentally send to placeholder strings.
- **VALIDATE**: `grep -E "^(RESEND_API_KEY|PORTAL_BASE_URL|EMAIL_TEST_ADDRESS_ALLOWLIST|INTERNAL_NOTIFICATION_EMAIL|INTERNAL_NOTIFICATION_PHONE|RESEND_WEBHOOK_SECRET)=" .env.example | wc -l` should output `6`.

### 34. UPDATE existing tests broken by the constructor change — exhaustive pinned list
- **IMPLEMENT**: The following are the **complete** set of `EstimateService(...)` constructor callsites in the codebase (verified 2026-04-25 via `grep -rn "EstimateService(" src/`). After step 13 removes the `portal_base_url` default, every callsite must pass `portal_base_url=` explicitly.

  **Production callsites (already updated by earlier steps — do not re-edit):**
  - `src/grins_platform/api/v1/portal.py:71` — updated in step 29.
  - `src/grins_platform/api/v1/dependencies.py:257` — updated in step 30.
  - `src/grins_platform/api/v1/dependencies.py:365` — updated in step 28.

  **Test callsites that ALREADY pass `portal_base_url=` (no change required — verify only):**
  - `src/grins_platform/tests/integration/test_external_service_integration.py:668` — passes `portal_base_url="https://portal.grins.com"`. ✓
  - `src/grins_platform/tests/integration/test_external_service_integration.py:782` — same. ✓
  - `src/grins_platform/tests/integration/test_external_service_integration.py:843` — same. ✓
  - `src/grins_platform/tests/integration/test_external_service_integration.py:921` — same. ✓
  - `src/grins_platform/tests/functional/test_estimate_operations_functional.py:176` — same. ✓

  **Test callsites that DO NOT pass `portal_base_url=` (must be edited):**
  - `src/grins_platform/tests/unit/test_estimate_service.py:191` — inside `_make_estimate_service` helper (lines 185-197 of the current file). Add `portal_base_url="https://portal.grins.com",` to the constructor call. Also add `sales_pipeline_service: AsyncMock | None = None,` to the helper's signature and pass it through (so individual tests can opt-in to mocking the breadcrumb path).
  - `src/grins_platform/tests/functional/test_background_jobs_functional.py:303` — adjacent to similar pattern. Add `portal_base_url="https://portal.grins.com",`.

  **30-day → 60-day expiry assertions:** search for `timedelta(days=30)` across `src/grins_platform/tests/` and change any assertion that compares to the **default** token/valid_until expiry to 60 days. Tests that pass an explicit `valid_until=` override are independent of the default — leave those alone. Expected hits: ~2-3 lines in `test_estimate_operations_functional.py` and possibly in `test_pbt_crm_gap_closure.py`.
- **PATTERN**: existing test fixtures.
- **GOTCHA**: The `_make_estimate_service` helper in `test_estimate_service.py` (lines 185-197) is used by ~50 individual tests. Adding a new optional `sales_pipeline_service` kwarg is a no-op for all existing tests but enables step 42's correlation tests to opt in.
- **VALIDATE**:
  ```
  uv run pytest src/grins_platform/tests/ -v -k estimate 2>&1 | tail -30
  grep -rn "EstimateService(" src/grins_platform/ | grep -v __pycache__ | grep -v "portal_base_url" || echo "OK — every callsite passes portal_base_url"
  ```

### 35. CREATE `src/grins_platform/tests/functional/test_estimate_email_send_functional.py`
- **IMPLEMENT**: `@pytest.mark.functional` test that:
  - Creates a real Estimate row via `EstimateRepository.create(...)`.
  - Calls `EstimateService.send_estimate(estimate_id)` with a mocked `EmailService.send_estimate_email` returning `{"sent": True, ...}`.
  - Asserts `EmailService.send_estimate_email` was called with `portal_url` containing the configured `PORTAL_BASE_URL` and the estimate's customer_token.
  - Asserts the returned `EstimateSendResponse.sent_via` contains `"email"`.
- **PATTERN**: `tests/functional/test_estimate_operations_functional.py:709-723`.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/functional/test_estimate_email_send_functional.py -v --tb=short`

### 36. CREATE `src/grins_platform/tests/integration/test_estimate_approval_email_flow_integration.py`
- **IMPLEMENT**: `@pytest.mark.integration` end-to-end:
  - POST `/api/v1/estimates/{id}/send` → mock Resend → assert email API called with expected payload.
  - GET `/api/v1/portal/estimates/{token}` → 200, response shape correct.
  - POST `/api/v1/portal/estimates/{token}/approve` → 200; assert internal notification email + SMS dispatched.
  - POST `/api/v1/webhooks/resend` with a synthetic `email.bounced` payload (mock signature verify) → 200; assert internal bounce notification dispatched and `Customer.email_bounced_at` is non-null.
- **PATTERN**: existing integration tests for portal flow (search `tests/integration/` for portal coverage).
- **VALIDATE**: `uv run pytest src/grins_platform/tests/integration/test_estimate_approval_email_flow_integration.py -v --tb=short`

### 37. UPDATE DEVLOG.md
- **IMPLEMENT**: Insert a new entry at the top of "## Recent Activity" following the format in `.kiro/steering/devlog-rules.md`. Category: `FEATURE`. Title: "Estimate approval email portal — Resend wired + bounce webhook + internal notifications + sales-entry breadcrumb + gate correction". Sections: What Was Accomplished, Technical Details, Decision Rationale, Challenges and Solutions, Next Steps. Document the Q-B gate drop explicitly: which gate, why it was wrong, and that bughunt M-10 is superseded. `MissingSigningDocumentError` retained as deprecated for back-compat.
- **PATTERN**: existing DEVLOG entries.
- **GOTCHA**: Do NOT update DEVLOG.md until everything else is shipped — the entry should describe the final state, not an aspirational one.
- **VALIDATE**: `head -50 DEVLOG.md` shows the new entry at top.

### 38. UPDATE `src/grins_platform/services/sales_pipeline_service.py` — ADD breadcrumb method (Q-A)
- **IMPLEMENT**: Add a new public method on `SalesPipelineService`:
  ```python
  async def record_estimate_decision_breadcrumb(
      self,
      db: AsyncSession,
      estimate: Estimate,
      decision: Literal["approved", "rejected"],
      *,
      reason: str | None = None,
      actor_id: UUID | None = None,
  ) -> SalesEntry | None:
      """Append a note + audit row to the active SalesEntry for this estimate.

      Best-effort. Never raises — internal notification and customer
      decision are higher priority than the breadcrumb.

      Match strategy:
        1. By estimate.customer_id → active SalesEntry (status NOT IN
           closed_won, closed_lost), most recently updated.
        2. Else by estimate.lead_id → same.
        3. If neither: log "sales.estimate_correlation.no_active_entry"
           and return None.

      Validates: Feature — estimate approval email portal Q-A.
      """
      self.log_started("record_estimate_decision_breadcrumb",
                       estimate_id=str(estimate.id), decision=decision)
      try:
          conditions = [
              SalesEntry.status.notin_([
                  SalesEntryStatus.CLOSED_WON.value,
                  SalesEntryStatus.CLOSED_LOST.value,
              ]),
          ]
          if estimate.customer_id is not None:
              conditions.append(SalesEntry.customer_id == estimate.customer_id)
          elif estimate.lead_id is not None:
              conditions.append(SalesEntry.lead_id == estimate.lead_id)
          else:
              self.log_rejected("record_estimate_decision_breadcrumb",
                                reason="estimate_has_no_customer_or_lead",
                                estimate_id=str(estimate.id))
              return None

          stmt = (select(SalesEntry).where(*conditions)
                  .order_by(SalesEntry.updated_at.desc()).limit(1))
          result = await db.execute(stmt)
          entry: SalesEntry | None = result.scalar_one_or_none()
          if not entry:
              self.logger.info("sales.estimate_correlation.no_active_entry",
                               estimate_id=str(estimate.id), decision=decision)
              return None

          ts = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
          short_id = str(estimate.id)[:8]
          if decision == "approved":
              note_line = (
                  f"\n[{ts}] Customer APPROVED estimate {short_id} via portal. "
                  f"Ready to send contract for signature."
              )
          else:
              reason_part = f' Reason: "{reason}".' if reason else ""
              note_line = (
                  f"\n[{ts}] Customer REJECTED estimate {short_id} via portal."
                  f"{reason_part}"
              )
          entry.notes = (entry.notes or "") + note_line
          entry.last_contact_date = datetime.now(tz=timezone.utc)
          entry.updated_at = datetime.now(tz=timezone.utc)

          _ = await self.audit_service.log_action(
              db,
              actor_id=actor_id,
              action="sales_entry.estimate_decision_received",
              resource_type="sales_entry",
              resource_id=entry.id,
              details={
                  "estimate_id": str(estimate.id),
                  "decision": decision,
                  "reason": reason,
                  "current_status": entry.status,
              },
          )
          await db.flush()
          self.log_completed("record_estimate_decision_breadcrumb",
                             entry_id=str(entry.id), decision=decision)
          return entry
      except Exception as e:
          self.log_failed("record_estimate_decision_breadcrumb",
                          error=e, estimate_id=str(estimate.id))
          return None
  ```
- **PATTERN**: existing `manual_override_status` (lines 166–215) for the audit-log shape; existing `_get_entry` for the SalesEntry select.
- **IMPORTS**: `from typing import Literal` (extend existing import). `from grins_platform.models.estimate import Estimate` to `TYPE_CHECKING`. `from datetime import timezone, datetime` already present. `select` already imported.
- **GOTCHA**:
  - Two leading newline + bracket so the breadcrumb visually separates from prior notes. If `notes` was None we initialize to `""` first.
  - We also bump `last_contact_date` so the rep's "stale lead" filter doesn't push this card to the bottom right after the customer acted.
  - Wraps EVERYTHING in try/except — vendor outage on AuditService, an invalid `Literal` value, a DB hiccup, all swallowed and logged. Customer's approval is already committed at the call site; this is purely informational.
  - Method does NOT call `db.commit()` — caller (in `EstimateService`) is mid-transaction; let the existing commit boundary handle it.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_sales_pipeline_breadcrumb.py -v` (test file authored in step 41).

### 39. UPDATE `src/grins_platform/services/estimate_service.py` — wire SalesPipelineService dep + invoke breadcrumb (Q-A)
- **IMPLEMENT**:
  - Add to `__init__`: `sales_pipeline_service: SalesPipelineService | None = None`. Stash on `self`.
  - Add a private helper:
    ```python
    async def _correlate_to_sales_entry(
        self,
        estimate: Estimate,
        decision: Literal["approved", "rejected"],
        *,
        reason: str | None = None,
    ) -> None:
        """Best-effort breadcrumb on the active SalesEntry. Never raises."""
        if not self.sales_pipeline_service:
            return
        try:
            _ = await self.sales_pipeline_service.record_estimate_decision_breadcrumb(
                self.repo.session, estimate, decision, reason=reason,
            )
        except Exception as e:
            self.log_failed("correlate_to_sales_entry",
                            error=e, estimate_id=str(estimate.id))
    ```
  - In `approve_via_portal` (after the existing lead-tag block, AFTER the `_notify_internal_decision` call from step 16, before `log_completed`): `await self._correlate_to_sales_entry(updated, "approved")`.
  - In `reject_via_portal` (same insertion point): `await self._correlate_to_sales_entry(updated, "rejected", reason=reason)`.
- **PATTERN**: same try/except + log_failed style as `_notify_internal_decision`.
- **IMPORTS**: `from grins_platform.services.sales_pipeline_service import SalesPipelineService` to TYPE_CHECKING block.
- **GOTCHA**: Order matters — internal notification fires FIRST (rep gets pinged), correlation is the slower DB-write step. If correlation fails for any reason, the customer's approval and the rep's notification still fired. Use `self.repo.session` to share the transaction with the just-committed update.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_estimate_correlation.py -v`

### 40. UPDATE `src/grins_platform/api/v1/dependencies.py` and `src/grins_platform/api/v1/portal.py` — inject SalesPipelineService into EstimateService
- **IMPLEMENT**:
  - In both `get_estimate_service` (`dependencies.py:353-365`, the version edited in step 28) and `_get_estimate_service` (`portal.py:59-71`, edited in step 29), construct a `SalesPipelineService` and pass it. SalesPipelineService takes `job_service: JobService, audit_service: AuditService`. Build them with the existing dependency factories.
  - The portal's `_get_estimate_service` is the more critical injection point because that's where customer-side approve/reject runs — without this dep here, the breadcrumb never fires.
- **PATTERN**: see `sales_pipeline.py` for `_get_pipeline_service` (the existing factory):
  ```python
  async def _get_pipeline_service(
      session: Annotated[AsyncSession, Depends(get_db_session)],
  ) -> SalesPipelineService:
      from grins_platform.services.audit_service import AuditService
      from grins_platform.services.job_service import JobService
      from grins_platform.repositories.job_repository import JobRepository
      audit_service = AuditService()
      job_service = JobService(JobRepository(session=session))
      return SalesPipelineService(job_service=job_service, audit_service=audit_service)
  ```
  Mirror this construction inside `get_estimate_service` and `_get_estimate_service` (or extract a helper).
- **GOTCHA**: Verify the existing `_get_pipeline_service` factory location and copy the construction shape exactly. JobService may have additional repo deps in dependencies.py — read the existing `get_job_service` factory there before re-implementing. Better: reuse `get_job_service` as a sub-dependency if FastAPI's DI permits.
- **VALIDATE**: `uv run mypy src/grins_platform/api/v1/dependencies.py src/grins_platform/api/v1/portal.py` (zero errors), then run integration tests in step 36.

### 41. CREATE `src/grins_platform/tests/unit/test_sales_pipeline_breadcrumb.py`
- **IMPLEMENT**:
  - `test_record_breadcrumb_with_active_entry_appends_note_and_audit` — mock DB session returning a SalesEntry; assert `entry.notes` ends with the timestamped line, audit_service.log_action called with `action="sales_entry.estimate_decision_received"`.
  - `test_record_breadcrumb_with_no_matching_entry_returns_none` — DB returns None; method logs `sales.estimate_correlation.no_active_entry`, returns None, does not raise.
  - `test_record_breadcrumb_with_terminal_entries_only_returns_none` — only `closed_won`/`closed_lost` entries exist for the customer; method skips them.
  - `test_record_breadcrumb_falls_back_to_lead_id_when_no_customer_id` — estimate has only `lead_id`; SalesEntry lookup uses `lead_id`.
  - `test_record_breadcrumb_with_no_customer_and_no_lead_returns_none_and_logs` — orphan estimate; method log_rejected.
  - `test_record_breadcrumb_swallows_db_error` — session.execute raises; method log_failed and returns None without re-raising.
  - `test_record_breadcrumb_appends_rejection_reason_when_provided`
  - `test_record_breadcrumb_does_not_overwrite_existing_notes` — `entry.notes = "previous content"`; after call, contains both old and new content separated by a newline.
- **PATTERN**: existing service unit tests for `SalesPipelineService` (search `tests/unit/test_sales_pipeline*`).
- **GOTCHA**: `entry.notes` may be `None` initially — assert the method handles this (the `(entry.notes or "")` guard).
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_sales_pipeline_breadcrumb.py -v`

### 42. CREATE `src/grins_platform/tests/unit/test_estimate_correlation.py`
- **IMPLEMENT**:
  - `test_approve_via_portal_calls_correlate_to_sales_entry` — mock `sales_pipeline_service.record_estimate_decision_breadcrumb`; assert called once with `decision="approved"`.
  - `test_reject_via_portal_calls_correlate_with_reason` — pass a rejection reason; assert it's forwarded to the breadcrumb method.
  - `test_correlate_to_sales_entry_swallows_breadcrumb_failure` — sales_pipeline_service raises; ensure approve_via_portal still succeeds and `log_failed("correlate_to_sales_entry"...)` was called.
  - `test_correlate_to_sales_entry_no_op_when_service_not_injected` — instantiate EstimateService without sales_pipeline_service; ensure approve_via_portal completes without error.
- **PATTERN**: `tests/unit/test_estimate_internal_notification.py` (step 20) — same mock-setup style.
- **GOTCHA**: `sales_pipeline_service.record_estimate_decision_breadcrumb` is async — use `AsyncMock`, not plain `MagicMock`.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_estimate_correlation.py -v`

### 43. UPDATE `src/grins_platform/models/enums.py` — clarify `SalesEntryStatus.PENDING_APPROVAL` (Q-B)
- **IMPLEMENT**: Add a class-level comment block immediately above the `PENDING_APPROVAL = "pending_approval"` line (around `models/enums.py:621`):
  ```python
      # PENDING_APPROVAL: Estimate has been sent to the customer via the
      # portal email; we are awaiting their portal approval (a click —
      # NOT a signature). Customer signatures only apply to the downstream
      # contract via SignWell, gated correctly at SEND_CONTRACT → CLOSED_WON
      # via SignatureRequiredError in convert_to_job. As of this change
      # (Q-B), the previous MissingSigningDocumentError gate at
      # SEND_ESTIMATE → PENDING_APPROVAL has been removed — it forced
      # reps to create a SignWell document before the customer had even
      # seen the estimate, which contradicted the intended workflow.
      PENDING_APPROVAL = "pending_approval"
  ```
- **PATTERN**: comments above other enum values in this file.
- **GOTCHA**: Do NOT change the string value — the DB stores the literal `"pending_approval"`, frontend types reference it, and historical SalesEntry rows use it.
- **VALIDATE**: `uv run python -c "from grins_platform.models.enums import SalesEntryStatus; assert SalesEntryStatus.PENDING_APPROVAL.value == 'pending_approval'"`

### 44. UPDATE `src/grins_platform/services/sales_pipeline_service.py` — drop the gate (Q-B)
- **IMPLEMENT**:
  - Remove the entire gate block at lines 137–151 of the current file:
    ```python
            # Gate: advancing into ``pending_approval`` requires a signing
            # document on file. The ``/sign/email`` and ``/sign/in-person``
            # endpoints already enforce this, but manual pipeline advance
            # skipped the check — admins could move to awaiting-signature
            # without anything actually sent out (bughunt M-10).
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
  - Drop the `MissingSigningDocumentError` name from the imports at lines 14–19. The remaining imports (`InvalidSalesTransitionError`, `SalesEntryNotFoundError`, `SignatureRequiredError`) stay.
- **PATTERN**: surrounding code in `advance_status`.
- **GOTCHA**:
  - The transition itself is still validated by `VALID_SALES_TRANSITIONS` (line 134) — the rep still cannot skip stages. We are only removing the SignWell-document precondition.
  - `SignatureRequiredError` (used by `convert_to_job` at line 290–291) is the **correctly-placed** signature gate — leave it alone.
  - This change makes the bughunt M-10 fix (the original reason for the gate) obsolete: M-10 was "admins could advance without sending the SignWell doc," but we now know advancing into PENDING_APPROVAL was never supposed to require a SignWell doc — the customer's portal approval is what should drive that transition. If the team wants to retain bughunt M-10's spirit, the right fix is a separate ticket that adds an "estimate sent" precondition (e.g., the linked Estimate is in `SENT|VIEWED|APPROVED` status), but that adds the cross-aggregate read we're explicitly avoiding in this feature.
- **VALIDATE**: `grep -n "MissingSigningDocumentError" src/grins_platform/services/sales_pipeline_service.py` returns no results. `uv run mypy src/grins_platform/services/sales_pipeline_service.py` passes.

### 45. UPDATE `src/grins_platform/api/v1/sales_pipeline.py` — drop dead exception handling (Q-B)
- **IMPLEMENT**:
  - Remove `MissingSigningDocumentError` from the import block at lines 19–24.
  - Remove the `except MissingSigningDocumentError as exc:` clause and its 422 HTTPException response at lines 270–274 (inside `advance_sales_entry`). The remaining exception handlers (`SalesEntryNotFoundError → 404`, `InvalidSalesTransitionError → 422`) stay.
- **PATTERN**: existing exception-handling block in `advance_sales_entry`.
- **GOTCHA**: The exception class itself stays defined in `exceptions/__init__.py` — leave it for back-compat. The dead `__all__` export is harmless. Update the class's docstring at `exceptions/__init__.py:764-771` to add a `Note: As of <date>, no longer raised by SalesPipelineService — kept for back-compat.` line.
- **VALIDATE**: `grep -n "MissingSigningDocumentError" src/grins_platform/api/v1/sales_pipeline.py` returns no results. `uv run mypy src/grins_platform/api/v1/sales_pipeline.py` passes.

### 46. UPDATE `src/grins_platform/exceptions/__init__.py` — add deprecation note to `MissingSigningDocumentError` (Q-B)
- **IMPLEMENT**: Append to the docstring of `MissingSigningDocumentError` (line 765):
  ```python
  class MissingSigningDocumentError(Exception):
      """Raised when a sales entry tries to advance to ``pending_approval``
      without a SignWell document on file.

      Deprecated as of Q-B fix in the estimate approval email portal feature:
      the gate that raised this exception was removed because it conflated
      estimate approval (a portal click) with contract signature (SignWell).
      No code path raises this exception today; the class is retained for
      back-compat with any external imports.

      Validates: bughunt M-10 (now superseded).
      """
  ```
- **PATTERN**: docstrings on neighboring exception classes.
- **GOTCHA**: Do NOT remove the `__all__` export — that would be a public API break.
- **VALIDATE**: `uv run python -c "from grins_platform.exceptions import MissingSigningDocumentError; assert MissingSigningDocumentError"` succeeds.

### 47. UPDATE `src/grins_platform/tests/unit/test_sales_pipeline_and_signwell.py` — invert the gate test (Q-B)
- **IMPLEMENT**:
  - Remove the import of `MissingSigningDocumentError` from the test file's imports (line 19).
  - Replace `TestSalesPipelineMissingSigningDocument::test_send_estimate_without_doc_raises` (lines 148–165) with the inverted form:
    ```python
        @pytest.mark.asyncio()
        async def test_send_estimate_without_doc_now_advances(
            self,
            pipeline_service: SalesPipelineService,
            mock_db: AsyncMock,
        ) -> None:
            """As of the Q-B fix, advancing send_estimate → pending_approval
            no longer requires signwell_document_id. Estimate approval is a
            portal click, not a signature. Locks in the corrected behavior.
            """
            entry = _make_entry(
                SalesEntryStatus.SEND_ESTIMATE.value,
                signwell_document_id=None,
            )
            mock_db.execute = AsyncMock(
                return_value=Mock(scalar_one_or_none=Mock(return_value=entry)),
            )
            updated = await pipeline_service.advance_status(mock_db, entry.id)
            assert updated.status == SalesEntryStatus.PENDING_APPROVAL.value
    ```
  - Optionally rename the wrapping class `TestSalesPipelineMissingSigningDocument` → `TestSalesPipelineGateRelaxation` for clarity.
  - The companion test `test_send_estimate_with_doc_advances` (line 167+) stays unchanged — `with_doc` still advances, just for an unrelated reason.
- **PATTERN**: existing tests in this file.
- **GOTCHA**: The test was the artifact of bughunt M-10's original fix. Inverting it preserves the test as a regression guard for the new behavior, instead of just deleting it.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_sales_pipeline_and_signwell.py::TestSalesPipelineGateRelaxation -v`

### 48. UPDATE `frontend/src/features/sales/components/StatusActionButton.tsx` — defensive comment (Q-B)
- **IMPLEMENT**: Above the `toast.error('Upload an estimate before advancing'...)` branch at line 140, add:
  ```ts
        // Defensive: as of the Q-B gate-drop the API no longer returns this
        // 422 — advancing send_estimate → pending_approval is gate-free.
        // Kept in case server-side gates are reintroduced; harmless dead
        // branch otherwise.
  ```
- **PATTERN**: surrounding error-handling.
- **GOTCHA**: Do NOT remove the toast — keeping it costs nothing and protects against future regressions or different 422 responses we might add later.
- **VALIDATE**: `cd frontend && npm run lint && npm run typecheck`

### 49. UPDATE `frontend/src/features/sales/types/pipeline.ts` — clarifying comment on the label (Q-B)
- **IMPLEMENT**: Add an inline comment above the existing `SALES_STATUS_CONFIG.pending_approval` entry:
  ```ts
    pending_approval: {
      // Means: estimate sent; awaiting customer approval via portal click.
      // NOT a contract signature — that happens at send_contract → closed_won.
      label: 'Pending Approval',
      className: 'bg-amber-100 text-amber-700',
      action: 'Send Contract',
    },
  ```
- **PATTERN**: existing `SALES_STATUS_CONFIG` entries.
- **GOTCHA**: The label and value are unchanged — comment-only.
- **VALIDATE**: `cd frontend && npm run typecheck`

---

## TESTING STRATEGY

### Unit Tests (target: services 90%+ coverage)
- `test_email_recipient_allowlist.py` — guard semantics.
- `test_email_service_resend.py` — `_send_email` Resend integration, allowlist refusal, tags passthrough, Reply-To header.
- `test_send_estimate_email.py` — `send_estimate_email` happy / no-email / lead-fallback paths.
- `test_estimate_internal_notification.py` — `_notify_internal_decision` env-gating, error swallowing, both channels.
- `test_resend_webhook.py` — signature verification, event-type branching, permanent vs transient bounce, customer flag stamping.
- Updates to `test_estimate_service.py` and `test_email_service.py` for new methods/constants.

### Functional Tests (real DB, target: workflow coverage)
- `test_estimate_email_send_functional.py` — `send_estimate` → mocked email service → DB-side assertions.
- Updates to `test_estimate_operations_functional.py` for the 60-day defaults and new email-call assertions.

### Integration Tests (full system)
- `test_estimate_approval_email_flow_integration.py` — full HTTP round-trip from admin send through customer approve through Resend bounce webhook.

### Property-Based Tests
- Token expiry invariant: for any random `created_at` and any random `now > created_at`, the token is rejected iff `(now - created_at) > 60d`. Add to existing `test_pbt_crm_gap_closure.py` if a `TestEstimateTokenExpiry` class exists; else create.
- Email-allowlist normalization invariant: for any input email, `_normalize_email_for_comparison(x.upper()) == _normalize_email_for_comparison(x.lower())`.

### Frontend Tests
- No new frontend test files required.
- Run existing `frontend/src/features/portal/components/EstimateReview.test.tsx` and `ApprovalConfirmation.test.tsx` to verify no regressions.

### Q-A breadcrumb edge cases (must be tested)
- Estimate has `customer_id` but no SalesEntry exists for that customer (estimate created via lead-only path) → method logs `no_active_entry`, returns None, no exception.
- Estimate has `lead_id` only (no `customer_id`) → SalesEntry lookup falls back to `lead_id`.
- Customer has TWO active SalesEntries (e.g., a winterization deal and a separate spring-startup deal both in `send_estimate`) → method picks the most recently updated and writes there. The other is untouched. Document this behavior in the docstring.
- Customer has only terminal SalesEntries (`closed_won`, `closed_lost`) → method skips them and logs `no_active_entry`.
- AuditService raises (e.g., DB unique-constraint glitch) → method log_failed and returns None; the customer's approval is unaffected.
- DB session is mid-transaction when called → method uses `db.flush` not `db.commit`; caller commits.

### Edge Cases (must be tested)
- Estimate has no customer and no lead → `send_estimate` returns `sent_via=[]` cleanly without raising.
- Customer has `email=None` → email branch logs a skip and SMS branch still fires.
- Allowlist contains `"  Foo@Bar.com , bar@baz.com "` (whitespace + caps) → both emails normalize and match.
- `RESEND_API_KEY` unset + `EMAIL_API_KEY` set → fallback works, `is_configured` is True, send succeeds.
- Resend webhook receives event with no `data.to` → 200 + warning log, no crash.
- Resend webhook receives `email.bounced` with `subType=Transient` → no DB flag, internal notification still fires (so staff are aware of soft-bounce trends).
- Approval succeeds but email service is None (e.g., test setup) → `_notify_internal_decision` no-ops cleanly.
- Two simultaneous approvals on the same token → first wins with 200, second gets 409 (already enforced; verify still true).
- Token expired (61+ days old) → `_validate_portal_token` raises `EstimateTokenExpiredError` → 410.

---

## EXHAUSTIVE AFFECTED-TESTS SWEEP

Pinned 2026-04-25. After step 47 inverts `test_send_estimate_without_doc_raises`, run a second sweep to confirm no other test depends on the dropped gate.

**Tests that reference `signwell_document_id` (verified — only one is affected by the gate drop):**
- `tests/unit/test_signing_document_wiring.py` (4 refs) — exercises `/sign/email` and `/sign/embedded` endpoints; **unaffected** (those endpoints still require an estimate document).
- `tests/unit/test_signwell_webhooks.py` (4 refs) — exercises the SignWell webhook; **unaffected**.
- `tests/unit/test_pbt_crm_changes_update_2.py` (2 refs in a `_make_entry` helper) — **unaffected**.
- `tests/unit/test_sales_pipeline_and_signwell.py` (5 refs) — **only `TestSalesPipelineMissingSigningDocument::test_send_estimate_without_doc_raises` at line 161 is affected**; inverted in step 47. The other four refs (`with_doc_advances`, the `_make_entry` helper, the `pending_approval` test) are unaffected.
- `tests/integration/test_signwell_webhook_integration.py` (5 refs) — **unaffected** (webhook flow).
- `tests/integration/test_lead_sales_job_pipeline_integration.py` (2 refs) — needs verification: read the test and confirm it does not assert that `advance_status: SEND_ESTIMATE → PENDING_APPROVAL` raises without a SignWell doc. If it does, invert the assertion the same way as step 47.
- `tests/functional/test_sales_pipeline_functional.py` (3 refs at lines 49, 228, 249, 272) — needs verification: read each call and confirm none assert the gate raises. If any do, invert.

**Tests that reference `MissingSigningDocumentError`:**
- `tests/unit/test_sales_pipeline_and_signwell.py:19` — import + `pytest.raises` at line 161. Both removed in step 47.
- No other matches anywhere.

**Verification command (run AFTER steps 44-47 are complete):**
```bash
grep -rn "MissingSigningDocumentError" src/grins_platform/tests/ | grep -v __pycache__
# Expected: zero matches.

grep -rn "signwell_document_id=None" src/grins_platform/tests/ | grep -v __pycache__
# Expected: matches in test_signing_document_wiring (intended — those endpoints still gate),
# in test_pbt_crm_changes_update_2 (helper default), test_sales_pipeline_and_signwell (helper +
# the inverted test), test_lead_sales_job_pipeline_integration (helper), and
# test_sales_pipeline_functional (3 lines). Read each call site to confirm it does NOT assert
# that `advance_status` raises.

uv run pytest src/grins_platform/tests/ -v -k "sales_pipeline or signwell or signing_document or pipeline_integration" 2>&1 | tail -20
# Expected: all pass. If anything fails with MissingSigningDocumentError or "Upload an estimate
# before advancing", inspect and invert per step 47's pattern.
```

---

## VALIDATION COMMANDS

Execute every command to ensure zero regressions and 100% feature correctness.

### Level 1: Syntax & Style
```bash
uv run ruff check --fix src/
uv run ruff format src/
cd frontend && npm run lint && cd ..
```

### Level 2: Type Checking
```bash
uv run mypy src/
uv run pyright src/
cd frontend && npm run typecheck && cd ..
```

### Level 3: Unit + Functional + Integration Tests
```bash
# Unit (fast, no deps)
uv run pytest src/grins_platform/tests/unit -v -m unit

# Functional (real DB)
uv run pytest src/grins_platform/tests/functional -v -m functional

# Integration
uv run pytest src/grins_platform/tests/integration -v -m integration

# Coverage
uv run pytest --cov=src/grins_platform --cov-report=term-missing src/grins_platform/tests/unit/test_email_service_resend.py src/grins_platform/tests/unit/test_send_estimate_email.py src/grins_platform/tests/unit/test_estimate_internal_notification.py src/grins_platform/tests/unit/test_resend_webhook.py src/grins_platform/tests/unit/test_email_recipient_allowlist.py
```

### Level 4: Migration Round-Trip
```bash
uv run alembic upgrade head
uv run alembic downgrade -1
uv run alembic upgrade head
psql "$DATABASE_URL" -c "\d customers" | grep email_bounced_at
```

### Level 5: Manual E2E in Dev
With `EMAIL_TEST_ADDRESS_ALLOWLIST=kirillrakitinsecond@gmail.com`, `RESEND_API_KEY=re_…dev_key…`, `PORTAL_BASE_URL=http://localhost:5173`, `INTERNAL_NOTIFICATION_EMAIL=kirillrakitinsecond@gmail.com`, `INTERNAL_NOTIFICATION_PHONE=+19527373312`:

```bash
# Start backend + frontend
./scripts/dev.sh

# 1. Create + send an estimate via admin
curl -X POST http://localhost:8000/api/v1/estimates \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{"customer_id":"…","line_items":[…],"valid_until":null}'
# response → {"id":"<estimate_id>", "customer_token":"<token>", …}

curl -X POST http://localhost:8000/api/v1/estimates/<estimate_id>/send \
  -H "Authorization: Bearer $JWT"
# response → {"portal_url":"http://localhost:5173/portal/estimates/<token>","sent_via":["sms","email"]}

# Inbox check: kirillrakitinsecond@gmail.com receives the styled estimate email.

# 2. Approve via portal
curl -X POST http://localhost:8000/api/v1/portal/estimates/<token>/approve \
  -H "Content-Type: application/json" -d '{}'
# response → 200 with token_readonly=true

# Inbox check: kirillrakitinsecond@gmail.com receives "Estimate APPROVED for …"
# SMS check: +19527373312 receives "Estimate APPROVED for …. Total $X. Open admin to action."

# 3. agent-browser smoke
agent-browser open "http://localhost:5173/portal/estimates/<token>"
agent-browser wait --load networkidle
agent-browser is visible "[data-testid='estimate-review']"
agent-browser screenshot e2e-screenshots/estimate-portal-after-approve.png
agent-browser close
```

### Level 6: Resend Webhook Smoke
```bash
# Trigger a synthetic bounce — use Resend's "Send test event" feature in the dashboard
# OR craft a request with a known signature using the svix CLI.
# Inbox check: bounce notification arrives. SMS check: same. DB check:
psql "$DATABASE_URL" -c "SELECT email, email_bounced_at FROM customers WHERE email_bounced_at IS NOT NULL;"
```

---

## ACCEPTANCE CRITERIA

- [ ] `POST /api/v1/estimates/{id}/send` produces a real email with portal link via Resend (verified in dev inbox).
- [ ] `EMAIL_TEST_ADDRESS_ALLOWLIST` guard refuses non-allowlisted recipients in dev with `EmailRecipientNotAllowedError` and a structured log line; production (env unset) is a no-op.
- [ ] Token expiry is 60 days (both `customer_token` and `valid_until` defaults).
- [ ] Customer approves estimate → internal email + SMS arrive at `INTERNAL_NOTIFICATION_EMAIL` / `INTERNAL_NOTIFICATION_PHONE` within 30s.
- [ ] Customer rejects estimate → same notifications fire with `REJECTED` subject and rejection reason in body.
- [ ] Resend webhook receives `email.bounced` with `subType=Permanent` → `customers.email_bounced_at` stamped, internal staff notification fires.
- [ ] All Level 1–4 validation commands pass with zero violations.
- [ ] Coverage: services 90%+ for `email_service.py` and `estimate_service.py` new methods; all new unit-test files pass.
- [ ] Existing portal flow (frontend + backend) still works — no regressions in `test_estimate_operations_functional.py` or `test_email_service.py`.
- [ ] Rate limit `PORTAL_LIMIT` applied on `/portal/estimates/*` (verified by 25-req/min curl loop returning 429).
- [ ] Webhook signature verification rejects malformed signatures with 401.
- [ ] **Q-A:** Customer approves an estimate via portal → matching `SalesEntry.notes` is appended with a timestamped line including the estimate short-id, and `audit_log` has a row with `action="sales_entry.estimate_decision_received"`. If no matching active SalesEntry exists, `sales.estimate_correlation.no_active_entry` is logged and the customer's approval is unaffected.
- [ ] **Q-A:** Customer rejects an estimate with a reason → SalesEntry breadcrumb includes the reason text.
- [ ] **Q-A:** Breadcrumb failure (mock SalesPipelineService to raise) does NOT undo the customer-side decision or the internal notification.
- [ ] **Q-B:** Gate at `SEND_ESTIMATE → PENDING_APPROVAL` is removed — `advance_status` succeeds without `signwell_document_id` set. `MissingSigningDocumentError` is no longer raised anywhere; its definition + `__all__` export remain for back-compat with deprecation note.
- [ ] **Q-B:** `SalesEntryStatus.PENDING_APPROVAL` carries the clarifying comment block; `.value == "pending_approval"` unchanged; `SALES_STATUS_CONFIG.pending_approval.label === 'Pending Approval'` unchanged.
- [ ] **Q-B:** Existing test `test_send_estimate_without_doc_raises` is replaced with `test_send_estimate_without_doc_now_advances` and passes; companion `test_send_estimate_with_doc_advances` unchanged and still passes.
- [ ] **Q-B:** `cd frontend && npm run lint && npm run typecheck` pass.
- [ ] DEVLOG.md entry added at top following devlog-rules.md format with the Q-B gate-drop documented as an intentional workflow correction (supersedes bughunt M-10).

---

## COMPLETION CHECKLIST

- [ ] All 37 tasks completed in order.
- [ ] Each task validation passed immediately after the task.
- [ ] All Level 1–6 validation commands executed successfully.
- [ ] Full test suite (unit + functional + integration) passes.
- [ ] No linting or type checking errors (ruff, mypy, pyright, eslint, tsc).
- [ ] Manual dev E2E confirms feature works end-to-end (send → email → approve → internal alert).
- [ ] Resend webhook smoke confirms bounce notification.
- [ ] Acceptance criteria all met.
- [ ] Code reviewed for security: no token in full-form logs, no email in info-level logs (mask), webhook signature verified, hard guard active in dev.

---

## NOTES

### Design decisions locked-in
- **Vendor: Resend (free tier).** Volume is well under 3K/mo. Decided 2026-04-25. AWS SES is the cold-swap fallback; ~30 LOC change inside `_send_email`.
- **No provider abstraction class for v1.** YAGNI — there is one provider; the abstraction lives at `_send_email`.
- **DB-stored UUID v4 token (already shipped).** Not switching to JWT — see design.md §1.
- **Token expiry: 60 days, both for access and price validity.** Easy to diverge later.
- **Internal notification via both email + SMS.** Approval is a high-value moment; redundant channel is intentional.
- **Manual SignWell handoff (not auto-trigger on approval).** Sales rep must click "send for signature" themselves — the internal notification + Q-A breadcrumb is what tells them. Decided to preserve the human checkpoint.
- **Bounce handling: v1, not v2.** Q10 was upgraded; silent delivery failure on a high-value estimate is unacceptable.
- **Soft-flag bounces only** — `email_bounced_at` is informational; do not block future sends. A transient bounce shouldn't permanently disable a customer.
- **Q-A: SalesEntry breadcrumb on approve/reject.** Best-effort note + audit row, no auto-advance of the kanban (rep stays in control). Cross-feature read of `SalesEntry` is OK; write goes through `SalesPipelineService` to respect the vertical-slice rule.
- **Q-B: Estimate approval is a click, NOT a signature — drop the gate.** The `MissingSigningDocumentError` gate at `SEND_ESTIMATE → PENDING_APPROVAL` was wrong: it forced reps to create a SignWell document before the customer had approved the estimate. Removed in this feature. The original bughunt M-10 fix it addressed is superseded — M-10 mistakenly assumed PENDING_APPROVAL meant "awaiting signature" when the intended meaning is "awaiting estimate approval via portal." If a future ticket wants to add an "estimate sent" precondition (e.g., gate on the linked Estimate being in `SENT|VIEWED|APPROVED`), that introduces cross-aggregate reads we are explicitly avoiding here. Signatures remain correctly gated at `SEND_CONTRACT → CLOSED_WON` via `SignatureRequiredError` in `convert_to_job`.

### Risks & mitigations
- **Token in URL is logged at every reverse-proxy hop** — only the suffix is masked in app logs. Mitigation: HTTPS-only deployment, the customer email goes only to one recipient. Acceptable bearer-token pattern (matches every estimate vendor in the industry).
- **Resend free-tier 100/day cap** — irrigation is seasonal (April–May spike). Volume confirmed under 3K/mo as of 2026-04-25 but not under 100/day at peak. Watch in Phase 6 cutover.
- **`noreply@grinsirrigation.com` mailbox** — must be set up in the email host with auto-responder before launch (Phase 6 task). Belt-and-suspenders `Reply-To: info@grinsirrigation.com` covers any reply that bypasses the auto-responder.
- **Svix signature spec drift** — verify Resend's webhook doc at execution time. If unclear, use the official `svix` Python SDK (one extra dep) instead of the manual HMAC implementation.

### Out of scope (explicitly)
- Customer payment portal (separate `invoice_token` flow already exists).
- SignWell signing flow (a separate stage that runs *after* approval).
- Generic email-system rebuild (only the Resend wiring + estimate template).
- Email open tracking via pixel (the portal GET is a stronger signal — optional v2).
- Resend the email from the admin UI ("Resend estimate" button) — punted to v2 unless SMS-resend doesn't already cover it.
- DB schema changes to `Estimate` (none needed).
- Frontend code changes (route + page already shipped; only smoke-test).

### Confidence Score: **10 / 10**

Every risk that pulled the score below 10 in the prior revision has been addressed:

- **Resend SDK API drift** → resolved. Pinned to v2.x (`>=2.0.0,<3.0.0`); verified the SDK exposes `resend.Emails.send` and `resend.webhooks.verify` (preflight check #1 + step 1's VALIDATE).
- **Svix signature spec drift** → resolved. Step 23 now delegates to `resend.webhooks.verify()` (the official SDK helper), eliminating hand-rolled HMAC entirely. Bounce-payload field paths corrected per the verified Resend webhook schema (`data.bounce.type` not `subType`, `"Permanent"`/`"Temporary"` not `Permanent`/`Transient`).
- **Bounce-tag correlation back to estimate_id** → resolved. Step 25 explicitly threads an `estimate_id` tag through `send_estimate_email → _send_email → resend.Emails.send`, and step 24's webhook handler reads it back via `data.tags`.
- **`EstimateService.__init__` removal of `portal_base_url` default surfaces broken callsites** → resolved. Step 34 now lists the **exhaustive 11 callsites** (3 production + 8 tests) with line numbers — 5 callsites already pass the kwarg, 2 production callsites are updated by earlier steps, 3 test callsites need the explicit fix.
- **`SalesPipelineService` injection deepens dep graph** → resolved. Steps 28 and 29 now use the verified canonical construction pattern from `sales_pipeline.py:169-175` (chain `JobService` via `Depends(get_job_service)`, instantiate `AuditService()` with no args). The reflective `inspect.signature` preflight check (#11) catches any future signature drift.
- **`LeadService` constructor mistake in earlier revision** → resolved. Steps 28 and 29 now explicitly pass `lead_service=None`, with a documented rationale (existing pre-feature behavior was already None — preserving status quo, not introducing a regression). Verified via signature inspection.
- **Gate removal cascades through test suite** → resolved. The new "EXHAUSTIVE AFFECTED-TESTS SWEEP" section enumerates every file referencing `signwell_document_id` and `MissingSigningDocumentError`, marks each as affected/unaffected, and pins post-step-47 verification commands.
- **Migration `down_revision` could shift if a migration lands between plan and execution** → resolved. Preflight check #6 (`uv run alembic heads`) catches this and prompts the agent to update step 21.
- **Webhook prefix collision** → resolved. Preflight check #7 verifies `/webhooks/resend` is unique before code is written.

The plan now contains every file path, line number, env var, constructor signature, and SDK API call referenced — verified against the live source on 2026-04-25 — plus a 12-point preflight verification suite that catches any drift before code is written. The agent can execute top-to-bottom without research.
