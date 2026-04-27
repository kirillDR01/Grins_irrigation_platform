# Current State — What's Already Wired vs. What's Missing

All citations are file paths and line numbers as of 2026-04-25 (branch `dev`, HEAD `c7e1840`). Verify before relying for implementation.

## 1. Already wired (do not rebuild)

### 1.1 Schema

`Estimate` model (`src/grins_platform/models/estimate.py`):

| Column | Type | Notes |
|---|---|---|
| `id` | UUID | server-generated |
| `customer_token` | UUID, unique, indexed | line 103–107 |
| `token_expires_at` | timestamptz | line 108–111 |
| `token_readonly` | bool, default false | line 112–116; flips to true on approve/reject |
| `status` | str(20), default `"draft"` | line 62–66; values from `EstimateStatus` |
| `approved_at` | timestamptz | line 119–122 |
| `approved_ip` | str(45) | line 123 |
| `approved_user_agent` | str(500) | line 124 |
| `rejected_at` | timestamptz | line 125–128 |
| `rejected_reason` | text | line 129 |
| `valid_until` | timestamptz | line 96–99; separate from token_expires_at |

`EstimateStatus` enum (`models/enums.py:453–465`): `DRAFT, SENT, VIEWED, APPROVED, REJECTED, EXPIRED, CANCELLED`. `VIEWED` and `EXPIRED` exist but are not yet driven by code.

### 1.2 Service layer

`EstimateService` (`src/grins_platform/services/estimate_service.py`):

- `create_estimate` generates `customer_token = uuid.uuid4()` and `token_expires_at = now + 30d` (`TOKEN_VALIDITY_DAYS = 30`, line 48). Also sets `valid_until = now + 30d` if not specified (line 156).
- `send_estimate(estimate_id)` (line 239–348):
  - Sets `status = SENT`
  - Builds `portal_url = f"{self.portal_base_url}/estimates/{estimate.customer_token}"` (line 273)
  - Sends an SMS with that URL via `SMSService.send_automated_message(message_type="estimate_sent")` (line 287–291)
  - For email: only logs `estimate.email.queued` with the URL (line 305–310). **Does not send.**
  - Schedules follow-ups at days 3, 7, 14, 21 via `_schedule_follow_ups`
- `approve_via_portal(token, ip, user_agent)` (line 354–433):
  - Validates token (404/410 mapped via exceptions)
  - 409 if already approved or rejected
  - Writes `status = APPROVED`, `approved_at`, `approved_ip`, `approved_user_agent`, `token_readonly = True`
  - Cancels remaining follow-ups
  - Updates lead action tags: add `ESTIMATE_APPROVED`, remove `ESTIMATE_PENDING`
- `reject_via_portal(token, reason?)` (line 435–509): symmetric, plus tags `ESTIMATE_REJECTED`
- `_validate_portal_token` (line 749–772): single source of truth for not-found / expired

### 1.3 Public HTTP API

`src/grins_platform/api/v1/portal.py` (router prefix `/portal`):

| Method | Path | Function | Notes |
|---|---|---|---|
| GET | `/estimates/{token}` | `get_portal_estimate` (line 153–213) | Returns `PortalEstimateResponse` — internal IDs stripped (Req 78.6). 404/410. Logs masked-token suffix + IP + UA. |
| POST | `/estimates/{token}/approve` | `approve_portal_estimate` (line 221–302) | Captures IP from `X-Forwarded-For`, falls back to `request.client.host`. 404/409/410. |
| POST | `/estimates/{token}/reject` | `reject_portal_estimate` (line 310–386) | Optional `reason` in body. 404/409/410. |
| POST | `/contracts/{token}/sign` | `sign_portal_contract` (line 394–475) | This is the SignWell-style flow, separate from approval. |
| GET | `/invoices/{token}` | `get_portal_invoice` (line 483–534) | Read-only invoice viewer; 90-day token. |

All routes are unauthenticated; security is just "do you possess a valid unexpired token." Token suffixes (last 8 chars) are logged in audit events; full token never logged.

### 1.4 Admin send endpoint

`src/grins_platform/api/v1/estimates.py:291–336`:

- `POST /api/v1/estimates/{estimate_id}/send` — auth required (`CurrentActiveUser`)
- Calls `EstimateService.send_estimate(estimate_id)`
- Returns `EstimateSendResponse(estimate_id, portal_url, sent_via: list[str])`

### 1.5 Frontend

- Routes (`frontend/src/core/router/index.tsx:140–157`):
  - `/portal/estimates/:token` → `EstimateReviewPage`
  - `/portal/contracts/:token` → `ContractSigningPage`
  - `/portal/invoices/:token` → `InvoicePortalPage`
- API client (`frontend/src/features/portal/api/portalApi.ts`):
  - `getEstimate(token)` → GET `/portal/estimates/{token}`
  - `approveEstimate(token, data?)` → POST `.../approve`
  - `rejectEstimate(token, data?)` → POST `.../reject`
- Component: `frontend/src/features/portal/components/EstimateReview.tsx` (with `.test.tsx`)
- Page wrapper: `frontend/src/pages/portal/EstimateReview.tsx`

### 1.6 Email service framework

`src/grins_platform/services/email_service.py`:

- Jinja2 environment loading from `src/grins_platform/templates/emails/` (line 84–91)
- Sender split: `TRANSACTIONAL_SENDER = noreply@grinsirrigation.com`, `COMMERCIAL_SENDER = info@grinsirrigation.com` (line 44–45)
- `_classify_email` puts estimate emails into `TRANSACTIONAL` once added (line 93–112)
- `_render_template` injects `business_name`, `business_phone`, `business_email`, `portal_url` (line 123–140)
- Existing JWT-based unsubscribe token pattern (`generate_unsubscribe_token`, line 600–619) — **not reused** for the estimate token, since the estimate token is a DB-stored UUID, not a signed JWT
- Existing email templates: `welcome.html`, `confirmation.html`, `renewal_notice.html`, `annual_notice.html`, `cancellation_conf.html`, `lead_confirmation.html`, `subscription_manage.html`

## 2. What's missing

### 2.1 Email provider not actually plugged in

`email_service.py:157–195` — `_send_email` is a stub:

```python
# Production: call email provider API here.
self.logger.info("email.send.completed", ...)
return True
```

No `resend`, no `boto3.client('ses')`, no SMTP. `EmailSettings.is_configured` short-circuits to `False` when `EMAIL_API_KEY` is empty, so the stub returns `False` early in the dev environment.

The vendor decision is already made in `feature-developments/email and signing stack/stack-research-and-recommendations.md` §4: **Resend** as primary, AWS SES as fallback.

### 2.2 No `send_estimate_email` method on `EmailService`

`EstimateService.send_estimate` knows it should email but only logs `estimate.email.queued` (line 300–311) and tags `"email"` into `sent_via`. The comment at line 300 says: *"a dedicated send_estimate_email method can be added to EmailService when email templates are ready."*

### 2.3 No `estimate_sent.html` template

`src/grins_platform/templates/emails/` does not contain an estimate template. Need to design the content (subject line, greeting, total summary, CTA button, valid-until date, contact info, unsubscribe link if commercial — though estimate emails should classify as transactional and skip unsubscribe).

### 2.4 `portal_base_url` is hardcoded

`EstimateService.__init__` defaults `portal_base_url = "https://portal.grins.com"` (line 81). It is wired through the constructor but every test passes the same hardcoded string. There is no `PORTAL_BASE_URL` env or settings field. Dev / staging will need different URLs (e.g., `http://localhost:5173`, `https://staging.grins.com`).

### 2.5 No "approval received" notification to staff

When the customer approves, `approve_via_portal` updates DB + lead tags + cancels follow-ups. It does **not** notify the office (no email, no SMS, no Slack). For the workflow to feel complete, the sales rep needs to know "the customer approved estimate X — start preparing the SignWell contract." This may already be handled through the lead-tag UI, but it is worth confirming with the user.

### 2.6 No automatic estimate→contract handoff

After approval, the next step in the documented sales pipeline is generating a SignWell contract. Today nothing automatically queues that — a human sees the lead tag and clicks "send for signature." Whether this should auto-trigger or stay manual is a product question, not a technical one.

### 2.7 Email open tracking (out of scope, but worth noting)

The portal is the source of truth for "did they look at the estimate" — when the GET `/portal/estimates/{token}` endpoint is hit, that is a stronger signal than an email open pixel. We currently log it (`portal.access.attempted`) but do not write a `viewed_at` timestamp on the Estimate row. The `EstimateStatus.VIEWED` enum value exists but is not transitioned. If we want a "viewed" tile in the sales UI, that's a small follow-up.

## 3. Risks discovered during this audit

- **Hardcoded portal URL** (§2.4) — if not addressed, dev links will point at production, which could leak test estimates to wherever `portal.grins.com` resolves.
- **Token in URL is logged at every hop** that touches HTTP access logs. The codebase masks the suffix in app logs, but reverse proxies and CDN logs see the full URL. Mitigation in `design.md`.
- **No rate limiting on portal endpoints** is visible in `portal.py`. A bad actor with a guessed-token list could brute force. UUID v4 has 122 bits of entropy so this is extremely unlikely in practice, but worth a note.
- **Existing memory `project_email_sign_budget.md`** references self-hosting paths if Grins exceeds 3K emails/mo. Re-check actual volume before launch.
