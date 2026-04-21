# Email, Estimate, and Contract-Signing Stack — Research & Recommendations

**Status:** Research / Proposal
**Author:** Deep-dive research pass, 2026-04-20
**Scope:** Choosing vendors and implementation approach for three adjacent capabilities under a tight shared budget:
  1. Outbound email delivery (transactional + commercial)
  2. Estimate document creation (PDFs sent to customers)
  3. Contract signing — both in-person on an iPad/phone and remote via emailed link
**Constraint:** <$25/mo total combined cost, 100–500 documents/mo steady-state volume, integrate into the existing FastAPI + React stack (not a vertical-SaaS swap like Jobber/ServiceTitan).
**Related:**
  - `feature-developments/signing document/signing-document-panel.md` — existing four-state signing-panel UI spec built around SignWell
  - `src/grins_platform/services/email_service.py` — existing email service with unplugged provider stub
  - `src/grins_platform/services/invoice_pdf_service.py` — existing WeasyPrint-based PDF pattern that the estimate flow can mirror

---

## 1. Executive Summary

| Capability | Recommendation | Cost (steady state) | Why |
|---|---|---|---|
| **Email sending** | **Resend** (free tier primary) with **AWS SES** as a zero-vendor-lock-in fallback | **$0/mo** at <3K emails/mo; $20/mo if scaled past 3K | Free tier covers projected volume; modern Python SDK; drops into the existing `EmailService._send_email()` stub in ~20 lines |
| **Estimate PDFs** | No vendor — build `EstimatePDFService` that mirrors the existing `InvoicePDFService` pattern using **WeasyPrint + Jinja2** (already installed) | **$0/mo** | Pattern, dependencies, S3 storage, and presigned-URL delivery are already in production for invoices |
| **Contract signing** | **Short-term:** stay on SignWell (free/PAYG tier is fine below ~25 docs/mo). **Medium-term:** swap to **DocuSeal self-hosted** once volume climbs, or build a **DIY ESIGN-compliant in-app signer**. | **$0–$10/mo** (self-hosted DocuSeal on Railway) or **$0** (DIY) | At 100–500 docs/mo every hosted API SaaS — including the one Grins already integrated — is $56+/mo. The budget simply does not buy hosted e-sign at this volume in 2026. |
| **Combined steady-state monthly cost** | | **~$0–$10/mo** | Well under $25/mo ceiling |

**One surprising finding:** SignWell is already fully wired into the platform, but its API pricing at the stated volume target is **$56–$356/mo** (pay-as-you-go) or **$275/mo** (flat paid plan) — **2× to 14× over the budget ceiling**. Either the 100–500/mo volume target is aspirational and SignWell's free tier (3 docs/mo) covers today's reality, or the budget ceiling and vendor choice are incompatible and something has to change. See §6 for the full analysis and §9.2 for the decision this forces.

---

## 2. Scoping Inputs (user answers, 2026-04-20)

The research scope was fixed up-front by these four answers:

| Dimension | User answer | Research implication |
|---|---|---|
| Total monthly budget | **Under $25/mo combined** | Eliminates most hosted e-sign APIs; favors free tiers, pay-per-use, and self-hosted |
| Architecture | **Integrate into our app** (not all-in-one vertical SaaS, not hybrid with standalone tools) | Must expose APIs callable from FastAPI; must not fragment data out of the Grins DB |
| Signing contexts | **In-person on iPad/phone AND remote via emailed link** | Vendor must support both embedded signing (iframe/web) and email-link signing, OR a DIY approach must cover both UX patterns |
| Volume | **100–500 documents/mo** at steady state | Eliminates per-doc pricing in the $0.50+/doc range; requires unlimited-plan or self-host economics |

The combination of (<$25/mo) + (100–500 docs/mo) + (API/embedded signing required) is the binding constraint. No major hosted e-sign vendor prices at this intersection in 2026.

---

## 3. Existing Stack Audit (What's Already Built)

Before making any recommendation I read the dependency manifests and grepped the backend/frontend for pre-existing wiring. The findings reshaped the recommendation substantially — most of the question was partly pre-answered by the current codebase.

### 3.1 Backend — `pyproject.toml` dependencies relevant to this work

| Dependency | Version spec | Role in this work |
|---|---|---|
| `fastapi` | `>=0.100.0` | HTTP framework — hosts email-send endpoints, webhook receivers, sign endpoints |
| `jinja2` | `>=3.1.0` | Template engine for email HTML + PDF HTML |
| `weasyprint` | `>=62.0` | **HTML → PDF rendering (already used for invoices)** — the estimate-creation "tool" the user asked about |
| `boto3` | `>=1.34.0` | AWS SDK — already used for S3; also how AWS SES would be accessed |
| `python-multipart` | `>=0.0.6` | Form parsing — relevant for file uploads on signing flow |
| `python-jose[cryptography]` | `>=3.3.0` | JWT — already used for unsubscribe tokens in email |
| `aiofiles` | `>=23.0.0` | Async file I/O |
| `apscheduler` | `>=3.10.0,<4.0.0` | Already scheduling notification jobs |
| `structlog` | `>=25.5.0` | Logging (used throughout EmailService) |
| `stripe` | `>=8.0.0` | Payment — integration point if estimate-acceptance triggers a deposit |
| `twilio` | `>=9.10.0` | SMS sender (NotificationService fallback) |

**Missing dependencies** that any of the evaluated options would require:
- `resend` (for Resend)
- `docuseal-sdk` (there is no first-party Python SDK for DocuSeal — HTTP calls via `httpx` which is already installed)
- No SDK needed for AWS SES (use `boto3.client('ses')` or `sesv2`)

### 3.2 Frontend — `frontend/package.json` dependencies relevant to this work

| Dependency | Version | Role |
|---|---|---|
| `react` / `react-dom` | `^19.2.0` | UI framework |
| `signature_pad` | `^5.1.3` | **HTML5 canvas-based signature capture — already installed, currently unused in any signing flow I can locate in the source tree** |
| `@stripe/terminal-js` | `^0.26.0` | In-person Stripe Terminal — relevant if in-person signing is paired with in-person payment |
| `react-hook-form` + `zod` | | Form handling — signing flow would use these |
| `@tanstack/react-query` | `^5.90.19` | Data fetching — would coordinate with React Query cache on signing state |
| `axios` | `^1.13.2` | HTTP client for backend calls |
| `sonner` | `^2.0.7` | Toasts — UX for "signature captured" feedback |
| Radix UI suite | | Dialog/Popover for signing modals |

### 3.3 Existing services, endpoints, and models

**Email:**
- `src/grins_platform/services/email_service.py` — 500+ line class with:
  - Jinja2 template pipeline (`_render_template`, line ~123)
  - Sender-identity separation: `TRANSACTIONAL_SENDER = noreply@grinsirrigation.com`, `COMMERCIAL_SENDER = info@grinsirrigation.com` (lines 44–45)
  - CAN-SPAM classification logic (`_classify_email`, line ~93)
  - Unsubscribe token generation with JWT (`JWT_SECRET_KEY`, HS256, 30-day expiry)
  - Compliance email methods: `send_welcome_email`, `send_confirmation_email` (MN auto-renewal 5-term disclosure)
  - **Stub at `_send_email()` line ~186: `# Production: call email provider API here.`** — this is where the vendor plugs in.
- `src/grins_platform/services/email_config.py` — `EmailSettings(BaseSettings)` with:
  - `email_api_key: str = ""` (generic, no vendor assumed)
  - `company_physical_address: str = ""` (CAN-SPAM requirement; blocks commercial sends if empty)
  - `stripe_customer_portal_url: str = ""`
- Templates at `src/grins_platform/templates/emails/` (welcome.html, confirmation.html, …)
- `NotificationService` at `src/grins_platform/services/notification_service.py` — already orchestrates SMS vs email via consent flags; expects a working `EmailService` injected.

**PDFs / estimates:**
- `src/grins_platform/services/invoice_pdf_service.py` — `InvoicePDFService(LoggerMixin)`:
  - Uses WeasyPrint for HTML→PDF
  - Uploads to S3 via `S3ClientProtocol` (put_object + generate_presigned_url)
  - Returns presigned download URLs
  - Reads company branding from `business_settings`
  - Validates Req 80.2, 80.3, 80.4, 87.7
- Force-download hardening on presigned URLs: recent commit `5ff5d87 feat(storage): force download on document/PDF presigned URLs`
- Auth requirement on doc endpoints: recent commit `001eb2d fix(security): require auth for customer document endpoints`
- **No analogous `EstimatePDFService` exists today.** Estimates are uploaded as `CustomerDocument` rows with `document_type='estimate'` but the PDF is not auto-generated — it's a file a team member manually uploads.

**E-signature (SignWell):**
- `src/grins_platform/services/signwell/` package:
  - `config.py` — `SignWellSettings` (api_key, webhook_secret, base_url `https://www.signwell.com/api/v1`)
  - `client.py` — HTTP client wrapper
  - `__init__.py`
- `src/grins_platform/api/v1/signwell_webhooks.py` — webhook receiver endpoint for SignWell events (sent/viewed/signed/declined/canceled/expired)
- `src/grins_platform/api/v1/sales_pipeline.py`:
  - `POST /sales/pipeline/{id}/sign/email` (lines 312–366) — create email signing envelope
  - `POST /sales/pipeline/{id}/sign/embedded` (lines 369–426) — create embedded signing session
- `src/grins_platform/models/sales.py` — `SalesEntry.signwell_document_id` (nullable string, lines 77–80)
- `src/grins_platform/services/sales_pipeline_service.py:142-151` — pipeline gate: status can't advance to `PENDING_APPROVAL` unless `signwell_document_id IS NOT NULL`
- Frontend `SignWellEmbeddedSigner` component (referenced in `signing-document-panel.md`)
- Test file: `src/grins_platform/tests/unit/test_signing_document_wiring.py`

**SignWell surface area is substantial.** Replacing it is a real migration, not a drop-in swap — though the abstraction boundary is cleaner than most migrations because everything is gated through the `signwell_document_id` column and the two sign endpoints.

**In-flight signing spec:**
- `feature-developments/signing document/signing-document-panel.md` — four-state UI panel (No Doc → Ready → Awaiting → Signed) with cancel, resend, embedded signer, webhook-driven state, delete guardrails. This spec is written assuming SignWell remains the backend.

### 3.4 What this audit changes about the research

- **"Tool to create estimates" is not a vendor question.** The infra is in-place; the work is a 1–2 day `EstimatePDFService` + Jinja2 template.
- **"Vendor to send emails" is a focused one-line config + SDK-call question.** The service abstraction is already well-factored (sender identities, templates, classification, compliance hooks) — just plug in a provider.
- **"Tool to sign contracts" is where the real decision lives.** The current answer (SignWell) is expensive at target volume, and switching costs non-trivial engineering time.

---

## 4. Part 1 — Email Sending

### 4.1 Volume estimate

If Grins does 100–500 estimates/contracts per month, the implied email volume is higher because of associated messages:

| Event | Emails per estimate/contract |
|---|---|
| Lead confirmation | 1 |
| Appointment confirmation | 1 |
| Estimate sent (with PDF link) | 1 |
| Signing request (if emailed, not in-person) | 1 |
| Reminder (if unsigned after N days) | 0–2 |
| Signed-confirmation receipt | 1 |
| Welcome / onboarding (service agreement) | 1 |
| Compliance (renewal notice, 45-day MN auto-renewal) | Occasional, annual |
| Invoice notifications | 1–3 (pre-due, past-due, lien) |
| Manual follow-ups | 0–2 |

Realistic load: **3–10 emails per estimate/contract** → at 500 docs/mo that's 1,500–5,000 emails/mo. At 100 docs/mo, 300–1,000 emails/mo.

### 4.2 Vendor comparison (verified 2026-04-20)

| Provider | Free tier | First paid tier | Overage model | Python SDK | Deliverability reputation | Key notes |
|---|---|---|---|---|---|---|
| **Resend** | **3,000/mo free, 100/day, 1,000 marketing contacts** | **$20/mo Pro — 50,000 emails/mo** | Pay-as-you-go overages, hard cap at 5× monthly quota | `resend` — modern, typed, clean | Good and improving; SPF/DKIM straightforward | **Built around developer DX.** React Email integration (react-email components → rendered HTML). Dashboard shows rendered previews. Free tier likely covers Grins' entire projected volume. |
| **AWS SES** | $0.10 per 1,000 emails ≈ **$0.05/mo at 500 emails/mo**; first-year 3,000/mo included | Linear pay-per-use after free tier | Five billing layers (see below) | Via `boto3` (already in deps) | Excellent if you warm up properly and manage reputation; mediocre if you don't | **Cheapest absolute.** But: must request production access out of sandbox; must verify domain + sender identities; Virtual Deliverability Manager **doubles per-email cost** if enabled; dedicated IPs are $24.95/mo (standard) or $15/mo + usage (managed) — don't need at this volume. |
| **Postmark** | 100/mo free developer plan, doesn't expire | **$15/mo Basic — 10,000 emails/mo** | $1.80/1K over Basic; $1.30 on Pro; $1.20 on Platform | Official SDK | **Best-in-class for transactional deliverability** | Overkill for Grins' volume; free tier is too small. |
| **SendGrid** | 100/day free | **$19.95/mo Essentials — 50,000/mo** | Per-tier | Mature | Reputation has slipped in recent years; large sender churn | Mature but no DX or price advantage over Resend in 2026. |
| **Mailgun** | 100/day on Flex | **$15/mo Foundation — 10,000/mo** | Per-tier | Mature | Fine; deliverability controversies in past but improved | No advantage at Grins' volume. |

**AWS SES five-billing-layer detail** (source: [AWS SES Pricing](https://aws.amazon.com/ses/pricing/)):
1. Base sending: $0.10 / 1,000 emails
2. Virtual Deliverability Manager (optional): $0.07 / 1,000 — **when enabled, each email counts twice → effectively $0.20/1,000**
3. Dedicated IP: $24.95/mo standard, or $15/mo + usage (managed)
4. Data transfer: $0.12 / GB
5. SNS notification fees for event tracking (bounces/complaints/opens)

At Grins' volume: the relevant layer is just #1 plus optional SNS for bounce handling. That's ~$0.05/mo + maybe $0.01 for SNS.

### 4.3 Recommendation — Resend (primary) with AWS SES fallback

**Why Resend wins at Grins' volume:**
- 3K/mo free tier covers 300–500 docs/mo in most scenarios; no billing at all
- Python SDK + React Email template interop mesh with Grins' React 19 + Jinja2 stack (React Email can export HTML that Jinja2 can still interpolate if needed)
- Dashboard previews and sent-email search save debugging time vs. SES's CloudWatch dive
- Zero infrastructure setup beyond domain DNS records
- Clean escape hatch: if deliverability issues or pricing change, `EmailService` is already abstracted — swap providers in ~20 lines

**Why AWS SES might win instead:**
- Grins already has AWS credentials (boto3, S3) — one less vendor relationship
- Infinitely cheaper at scale (if Grins 10× the business, SES still costs pennies)
- Lower vendor-lock-in risk

**Why *not* Postmark even though it has the best deliverability reputation:** At Grins' volume the $15/mo floor doesn't give ROI over Resend's free tier, and their API/DX are not enough better to offset.

### 4.4 Integration design into existing `EmailService`

The stub at `src/grins_platform/services/email_service.py:186` is where a vendor drops in. Resend integration sketch:

```python
# email_service.py — sketch, not final
import resend

class EmailService(LoggerMixin):
    def __init__(self, settings: EmailSettings | None = None) -> None:
        super().__init__()
        self.settings = settings or EmailSettings()
        if self.settings.is_configured:
            resend.api_key = self.settings.email_api_key

    def _send_email(
        self,
        *,
        to_email: str,
        subject: str,
        html_body: str,
        email_type: str,
        classification: EmailType,
    ) -> bool:
        sender = self._get_sender(classification)
        masked = _mask_email(to_email)

        if not self.settings.is_configured:
            self.logger.warning("email.send.pending", recipient=masked, ...)
            return False

        try:
            result = resend.Emails.send({
                "from": sender,
                "to": [to_email],
                "subject": subject,
                "html": html_body,
                "headers": {
                    "List-Unsubscribe": f"<{self._unsubscribe_url(to_email)}>",
                    "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
                },
            })
            self.logger.info("email.send.completed", resend_id=result.get("id"),
                             recipient=masked, email_type=email_type, ...)
            return True
        except resend.exceptions.ResendError as exc:
            self.logger.error("email.send.failed", recipient=masked, error=str(exc))
            return False
```

**Config changes** (`email_config.py`):
- `email_api_key` → rename-optional to `resend_api_key` (the existing generic name is fine, can keep)
- Add `email_provider: Literal["resend", "ses", "none"] = "resend"` to allow flipping providers via env var without code change

**DNS setup** (operational, not code):
- Add Resend-provided SPF (`include:_spf.resend.com`), DKIM CNAMEs, and DMARC TXT to the `grinsirrigation.com` zone before going live
- Resend's dashboard walks through verification; takes <30 min

**Testing compliance** (per saved feedback memory):
- Never send to real-customer email addresses during dev/testing
- Either use a test inbox or set `settings.is_configured = False` in the dev environment (then emails go to `email.send.pending` log lines)

### 4.5 Estimated effort

- Integration: **~0.5 days** of engineering (add dependency, write send implementation, add tests mocking `resend.Emails.send`, update config)
- Domain/DNS setup: **~30 min ops**
- Monitoring: add a Grafana/structlog-query alert on `email.send.failed` rate (optional)

---

## 5. Part 2 — Estimate Creation

### 5.1 Why no vendor is needed

The user asked about "a tool to create estimates." The space of tools the market sells:

| Tool class | Example vendors | Price | Fit for Grins |
|---|---|---|---|
| **Proposal builders** (WYSIWYG editor, templates, acceptance portals) | Proposify, Qwilr, PandaDoc, Better Proposals | $35–$50/user/mo | **Over budget; optimized for non-engineers to author documents** |
| **All-in-one service CRM** (estimate/quote module bundled) | Jobber, Housecall Pro, ServiceTitan, Service Fusion | $29–$300+/mo | **Rejected in scoping** (user chose integrate-into-app architecture) |
| **PDF-generation API** | DocRaptor, APITemplate.io, PDFMonkey | $15–$30/mo | Unnecessary — WeasyPrint does this in-process for free |
| **DIY HTML → PDF in your own stack** | WeasyPrint, Playwright, pdfkit | Free | **Already installed and in production use for invoices** |

At Grins' budget and architecture choice, the correct answer is to replicate the existing invoice-PDF pattern for estimates.

### 5.2 Proposed `EstimatePDFService` design

Mirror `src/grins_platform/services/invoice_pdf_service.py`:

```python
# src/grins_platform/services/estimate_pdf_service.py — sketch
class EstimatePDFService(LoggerMixin):
    """Service for estimate PDF generation and management.

    Uses WeasyPrint for HTML→PDF conversion, uploads to S3,
    and manages pre-signed download URLs.
    """

    DOMAIN = "estimate_pdf"

    def __init__(self, session: AsyncSession, s3_client: S3ClientProtocol,
                 settings: ...) -> None:
        ...

    async def generate_pdf(self, sales_entry_id: UUID) -> CustomerDocument:
        """Render the estimate HTML, convert to PDF, store to S3,
        and create a CustomerDocument row with document_type='estimate'.
        """
        # 1. Load sales entry + customer + line items
        # 2. Load business_settings for branding
        # 3. Render Jinja2 template templates/pdfs/estimate.html
        # 4. weasyprint.HTML(string=rendered).write_pdf(buffer)
        # 5. s3_client.put_object(Bucket=..., Key=..., Body=buffer, ContentType=application/pdf)
        # 6. Create CustomerDocument(document_type='estimate', sales_entry_id=...,
        #    s3_key=..., file_size=..., uploaded_by=system_user)
        # 7. Return the CustomerDocument
        ...

    def get_presigned_url(self, customer_document: CustomerDocument,
                         *, expires_in: int = 300) -> str:
        """Generate a presigned URL with ResponseContentDisposition
        set to 'attachment' (honoring the recent force-download hardening).
        """
        ...
```

### 5.3 Template structure (`templates/pdfs/estimate.html`)

Minimum sections (mirrors typical irrigation-industry estimate format):

1. **Header** — Grins logo, company address (from `business_settings.company_physical_address`), phone, license number, estimate number, date, estimate expiration
2. **Bill-to / Site-to** — customer name, service address, contact
3. **Line items table** — description, quantity, unit price, line total
4. **Totals** — subtotal, MN sales tax (if applicable; already computed elsewhere), grand total
5. **Scope notes / assumptions / exclusions** — plain prose
6. **Payment terms + deposit required** — copy from `business_settings`
7. **Acceptance block** — either "Sign to accept (link in email)" or the e-sign flow the signed-contract equivalent uses
8. **Footer** — license info, warranty, contact

All sections fed by existing `SalesEntry`, `Customer`, `LineItem`, and `BusinessSettings` models.

### 5.4 Integration points

1. **Sales pipeline** — when a user clicks "Generate Estimate PDF" in the UI, call `EstimatePDFService.generate_pdf(sales_entry_id)` → returns a `CustomerDocument`. Reuse the existing `_get_signing_document` resolver (`sales_pipeline.py:57-141`) which already looks for `document_type IN ('estimate', 'contract')`.
2. **Signing flow** — the generated estimate PDF is a `CustomerDocument`, which means it is automatically eligible as a signing document per the existing signing-document-panel spec. Generation and signing are orthogonal concerns.
3. **Email delivery** — once generated, the estimate email uses Resend to send a link to the presigned URL (don't attach; link is better for deliverability and file-size).

### 5.5 When a vendor *would* be warranted

If Grins later wants to let **non-engineers author custom-branded estimates with a WYSIWYG editor and per-customer customization**, then a proposal-builder tool (Proposify / Qwilr / PandaDoc) becomes useful — but at $35–$50/mo it blows the budget and is redundant with SignWell if chosen for signing. Deferring this until clear product pull.

### 5.6 Estimated effort

- Service + template + route: **~1–2 days** of engineering
- Tests: **~0.5 days** (mock S3, snapshot the rendered HTML, assert PDF byte count sanity)
- UI button on `SalesDetail.tsx` to trigger generation: **~0.5 days**

Total: **~2–3 days.** No ongoing cost.

---

## 6. Part 3 — Contract Signing / E-Signature

This is the hardest part of the research because the budget constraint fights the volume target.

### 6.1 Current state — SignWell is already in production

See §3.3 for the detailed surface-area inventory. Summary: SignWell has a DB column, a settings class, a client package, an HTTP API webhook receiver, two API endpoints, a feature-spec for a UI panel being built around it, and unit tests for the wiring. It is not a research target — it is **the status quo** that the research has to either endorse or recommend replacing.

### 6.2 SignWell pricing — verified 2026-04-20

From [SignWell API Pricing](https://www.signwell.com/api-pricing/) and [SignWell Pricing](https://www.signwell.com/pricing/):

| Plan | Monthly | Documents included | Overage | API access |
|---|---|---|---|---|
| **Free Developer** | $0 | 3 docs/mo | — | Yes |
| **Pay-as-you-go API** (cited in search results but not clearly on the main API pricing page — may be a legacy tier) | $0 base | 25 docs/mo free | **$0.75/doc** | Yes |
| **Paid API Plan** (current official API tier) | **$275/mo** | 25 docs/mo free + pay-as-you-go | **$0.66/doc** | Yes, with SOC 2, HIPAA, dedicated support |
| **Personal** (web, no API) | $10/mo (annual) | Unlimited signing | — | No |
| **Business** (web, no API) | **$30/seat/mo × 3-seat minimum = $90/mo floor** | Unlimited signing, teams | — | No |
| **Enterprise** | Custom | Custom | — | Yes |

**Cost at Grins' target volume:**

| Monthly document volume | Pay-as-you-go cost | $275/mo plan cost |
|---|---|---|
| 3 | $0 (free tier) | $275 |
| 25 | $0 (free tier) | $275 |
| 100 | $56.25 (75 × $0.75) | $275 |
| 250 | $168.75 | $275 + (250-25-??) = $424.50 if the $275 plan also carves out 25 free; otherwise $275 + 225 × $0.66 = $423.50 |
| 500 | $356.25 | $588.50 |

**Every production-volume scenario is 2× to 14× over the $25/mo budget.**

### 6.3 Competitive landscape — hosted e-sign with API at Grins' volume

| Vendor | Cheapest tier with production API + embedded signing | Cost at 100/mo | Cost at 500/mo | Fits budget? |
|---|---|---|---|---|
| **SignWell** (current) | $275/mo flat OR PAYG $0.75/doc + 25 free | ~$56 PAYG / $275 plan | ~$356 PAYG / $589 plan | **No** |
| **BoldSign** | Enterprise API $30/mo, includes 40 docs, $0.75 overage | $75 ($30 + 60 × $0.75) | $375 ($30 + 460 × $0.75) | **No** |
| **Dropbox Sign (HelloSign) API** | ~$100/mo standard API tier; essentials web plans don't include API | ≥$100 | ≥$100 + per-doc fees | **No** |
| **PandaDoc** | $35/user/mo Essentials (no API); $49+ Business with API | ≥$49 | ≥$49 | Over budget |
| **DocuSign** | $45/user/mo Business Pro (no API); $75+/mo API Developer tier | ≥$75 | Higher | Over budget |
| **eversign** | $9.99/mo for 25 docs; $39.99/mo for 100; $79.99/mo for unlimited | $39.99 | $79.99 | **Unlimited tier fits for $79.99 but volume-dependent.** Still over $25 ceiling. |
| **Signaturely** | $20/user/mo unlimited, **no developer API** | N/A | N/A | Web-only, disqualified |
| **Documenso Cloud** | $25/mo Individual — unlimited docs + API | $25 | $25 | **Exactly at budget ceiling; 1 user only.** Viable. |
| **Documenso Cloud Teams** | $40/mo + $8/extra user | $40 | $40 | Over budget |
| **DocuSeal Cloud Pro** | $20/user/mo — unlimited docs + API + embedded | $20 | $20 | **Fits.** |
| **DocuSeal Self-Hosted** | Free AGPL-3.0 software; only pay hosting | $5–10 hosting | $5–10 hosting | **Fits, cheapest non-DIY option.** |
| **Documenso Self-Hosted** | AGPL-3.0, but commercial self-host licensing terms are ambiguous on their pricing page | $5–10 hosting + unclear license | Same | **Uncertain; verify license before betting on it** |

### 6.4 Recommended options for Grins

Three realistic paths that fit under $25/mo:

#### Option A — Self-hosted DocuSeal on Railway (recommended if volume stays high)

**DocuSeal** (`docusealco/docuseal` on GitHub) is an open-source DocuSign alternative under AGPL-3.0. Self-hosting is free; cloud Pro is $20/user/mo.

**Pros:**
- Full API + embedded signing + webhooks — same surface SignWell provides
- Truly free software (AGPL permits commercial use as long as source modifications are made available to end users; a self-hosted instance that users don't modify source on has minimal AGPL obligation)
- HIPAA, GDPR, SOC 2 compliant out of the box
- Railway deployment template exists; ~$5–10/mo hosting on Railway
- Postman collection + strong API docs
- Active maintenance

**Cons:**
- You run the infra (uptime, backups, TLS, database)
- No legal indemnity like a hosted SaaS provides — if a signature is challenged, you carry the audit-trail burden yourself (though DocuSeal generates the audit trail)
- Migrating off SignWell is ~1–2 weeks of engineering (see §8)

**Total monthly cost:** ~$5–10 hosting. Well under budget.

#### Option B — DIY ESIGN-compliant in-app signer (recommended if volume stays low and eng time available)

Leverage what's already installed: `signature_pad` (frontend) + WeasyPrint (backend) + S3 + JWT. Build signing in-house.

**Pros:**
- $0 ongoing cost
- Full control over UX — both iPad-on-site and remote-email-link flows use the same React component, no iframe awkwardness, no third-party branding
- No vendor dependency; no rate limits; no pricing risk
- Audit trail lives in your own DB, queryable for reporting

**Cons:**
- Legal review recommended before first production signature (especially for a regulated industry with MN auto-renewal rules already in play)
- No "we use a known vendor" signal to customers — though this rarely comes up for residential irrigation contracts
- You build the UI (signature pad, consent disclosure, thank-you confirmation)
- You build the audit trail (IP, user agent, timestamp, SHA-256 of the signed PDF)
- You build the "signed PDF" generation (re-render with signature image embedded)

**Total monthly cost:** $0 (beyond existing infra). Engineering cost: ~3–5 days (see §6.5 below).

#### Option C — Documenso Cloud Individual ($25/mo)

Documenso Cloud Individual plan at exactly $25/mo: unlimited documents, API access, 1 user.

**Pros:**
- Hosted — no infra ops
- At the budget ceiling (not over)
- Open-source vendor with transparent pricing
- No per-doc fees up to plan limit
- API + embedded signing + webhooks

**Cons:**
- **1-user cap.** If multiple team members need to send for signature from their own accounts, you need Teams at $40/mo.
- A single API key drives all signing, so attribution to which employee sent which envelope has to live in Grins' own DB, not Documenso's
- Right at the budget — no headroom; any Documenso price change requires re-evaluation
- Migration from SignWell is still needed (same ~1–2 weeks as DocuSeal)

**Total monthly cost:** $25 (entire budget).

### 6.5 DIY e-sign — ESIGN Act / UETA compliance specifics

For Option B (DIY signer), the legal framework is the **ESIGN Act** (federal, 2000) and **UETA** (state-level model, adopted by 48 states including MN). Both require the same four elements for an electronic signature to be legally equivalent to a wet-ink signature:

| Requirement | What it means | How Grins would implement |
|---|---|---|
| **1. Intent to sign** | The signer must demonstrate clear intent — not accidental | A typed legal name field + an explicit "I agree and sign this contract" button. Tick-box with "By clicking sign, I intend to sign this document" label. |
| **2. Consent to do business electronically** | Signer must consent to electronic records rather than paper | One-time disclosure modal on first signing: "You agree to receive contracts electronically. You can request paper copies by contacting info@grinsirrigation.com. Hardware/software requirements: modern browser with JavaScript." Store consent record (customer_id, timestamp, version of disclosure). |
| **3. Association of signature with record** | The signature must be verifiably tied to the specific document | Compute SHA-256 of the final PDF before signature; store `(document_sha256, signature_image, signer_ip, user_agent, timestamp, geo_approx)` in an audit-log table; embed the signature image into the PDF at a fixed location; re-hash the signed PDF and store that too. |
| **4. Record retention** | Both parties can access and retain the signed document | Store in S3 (already done). Email the signed PDF to the customer on completion. Make available for download via customer portal. |

**Implementation sketch** (new files/models):

```
src/grins_platform/services/inapp_signer/
  __init__.py
  service.py              # InAppSignerService with sign() / verify_audit()
  audit_log.py            # Dataclass or pydantic model for audit events
  pdf_embedder.py         # Uses weasyprint/pypdf to embed signature image

src/grins_platform/models/signature_audit.py
  class SignatureAudit(Base):
      id: UUID PK
      customer_document_id: UUID FK -> customer_documents
      signer_name: str
      signer_email: str
      signer_ip: str
      signer_user_agent: str
      signed_at: datetime
      pre_sign_pdf_sha256: str
      post_sign_pdf_sha256: str
      signature_image_s3_key: str
      consent_disclosure_version: str
      consent_accepted_at: datetime
      # intent fields
      typed_name: str         # what the user typed as their name
      intent_statement: str   # e.g. "I agree and intend to sign..."

frontend/src/features/sales/components/InAppSigner.tsx
  # wraps signature_pad; captures draw, typed name, IP via backend, consent
  # POSTs audit fields + signature PNG to POST /sign/inapp/{document_id}
```

**Legal review checklist before shipping:**
- Disclosure copy reviewed (ESIGN-compliant; mentions hardware/software requirements, paper-copy option, withdrawal of consent, contact info)
- Intent statement reviewed
- Audit log field completeness (IP capture method, timezone consistency)
- Retention policy (recommend indefinite retention of signed contracts in S3 with delete-guard per `signing-document-panel.md` §4.5.3 AC-17)
- MN-specific considerations: MN Stat. 325L (the Uniform Electronic Transactions Act as adopted in MN) — largely tracks UETA but confirm with counsel

### 6.6 Which option I'd pick (given what I know)

If I had to choose without further input: **Option A — DocuSeal self-hosted on Railway.**

Reasoning:
- Keeps all SignWell-equivalent features (API, embedded signing, webhooks, templates) at ~$5–10/mo hosting
- Avoids legal-review work required for DIY
- Avoids the 1-user ceiling of Documenso Cloud Individual
- AGPL is well-understood; DocuSeal is widely adopted for commercial self-hosting
- Grins already runs Railway infrastructure — no new ops surface

**When DIY (Option B) is the right choice instead:**
- If volume stays below 25/mo indefinitely (then SignWell free tier works today with no change)
- If legal review is cheap to obtain and UX control matters more than vendor polish
- If opinionated about zero third-party dependencies for core business workflow

---

## 7. Bundled Recommendations

### 7.1 Recommended phased rollout

| Phase | Trigger | Email | Estimates | Contracts | Monthly cost |
|---|---|---|---|---|---|
| **Phase 0 — Today** | Current: demo / early customers, <25 docs/mo | Plug Resend into existing EmailService stub (~0.5 days) | Build EstimatePDFService (~2–3 days) | Keep SignWell on free tier (3 docs/mo) or PAYG | **~$0** (Resend free + SignWell free tier, SES pennies if chosen) |
| **Phase 1 — Growth** | Volume crosses 25 docs/mo | Same Resend | Same `EstimatePDFService` | **Migrate SignWell → DocuSeal self-hosted on Railway** (~1–2 weeks eng work) | **~$5–10/mo** (Railway hosting for DocuSeal) |
| **Phase 2 — Scale** | Volume crosses 3,000 emails/mo (~500+ docs) | Resend Pro ($20/mo) or shift to AWS SES ($0.05–$0.50/mo) | Unchanged | Unchanged | **~$25/mo or less** depending on email choice |
| **Optional Phase 3** | If non-engineers want to build visual proposals | Unchanged | **Consider Proposify/Qwilr** ($35/mo) if pull justifies it | Unchanged | ~$55+/mo (breaks budget) |

Phase 0 work can ship immediately. Phase 1 is ~2 weeks when the trigger hits.

### 7.2 Alternative if staying on SignWell is politically required

If for any reason SignWell must stay (e.g., contractual, customer expectation, existing enterprise deal I don't know about), then the budget ceiling has to rise:

- SignWell $275/mo flat plan + Resend free tier + DIY WeasyPrint estimates = **$275/mo total** — same price as the cheapest hosted estimate-and-sign bundle (PandaDoc at ~$49/user but comparable stack by the time API is added). Within that line item, SignWell is actually competitive for the API + embedded signing + enterprise features.
- Raise the budget to ~$300/mo and this is a fine stack, just not a <$25/mo one.

---

## 8. Migration Plan — If Switching Off SignWell

If Phase 1 triggers and DocuSeal replaces SignWell, the migration surface touches:

### 8.1 Backend changes

| File | Change | Rough size |
|---|---|---|
| `src/grins_platform/services/signwell/` | Rename package to `esign/` or keep as-is but add `docuseal/` sibling package | — |
| `src/grins_platform/services/esign/provider.py` (new) | Abstract interface `ESignProvider` with methods `send_email_envelope`, `create_embedded_session`, `void_envelope`, `get_status` — both SignWell and DocuSeal implementations conform | ~50 lines |
| `src/grins_platform/services/esign/docuseal_client.py` (new) | Concrete DocuSeal HTTP client (DocuSeal has no first-party Python SDK; use `httpx`) | ~200 lines |
| `src/grins_platform/services/esign/signwell_client.py` (existing, moved) | Wrap existing SignWell client in the new interface — zero behavior change | ~0 net lines (move only) |
| `src/grins_platform/models/sales.py:77-80` | Add `esign_provider: str` and `esign_document_id: str` columns; keep `signwell_document_id` nullable for backward-compat and backfill; Alembic migration | +3 columns, 1 migration |
| `src/grins_platform/api/v1/sales_pipeline.py:312-426` | Route `/sign/email` and `/sign/embedded` through the abstract provider based on env config | ~30 line delta |
| `src/grins_platform/api/v1/signwell_webhooks.py` → `esign_webhooks.py` | Add DocuSeal webhook handler; keep SignWell handler live during dual-write period | ~+200 lines |
| `src/grins_platform/services/sales_pipeline_service.py:142-151` | Gate check updates from `signwell_document_id` → `esign_document_id` | ~5 lines |
| `src/grins_platform/services/signwell/config.py` + new `docuseal/config.py` | Parallel settings classes | ~50 lines |
| Feature flag `ESIGN_PROVIDER=docuseal|signwell` | Env var + settings | — |

### 8.2 Frontend changes

| File | Change |
|---|---|
| `SignWellEmbeddedSigner.tsx` → `EmbeddedSigner.tsx` | Accept provider-agnostic session URL; behavior is iframe of session URL which is the same mechanic for both vendors |
| `SigningDocumentCard.tsx` (from `signing-document-panel.md`) | Read `entry.esign_document_id` instead of `signwell_document_id`; status chip text changes per provider (or stay vendor-neutral) |
| API client | Same endpoints, provider-agnostic |

### 8.3 Data migration

For in-flight SignWell envelopes at cutover time:
1. Freeze new sends on SignWell 1 week before cutover
2. Let existing envelopes complete (customers sign within that window) or void and re-send via DocuSeal
3. Mark old `signwell_document_id` as read-only in UI (download only, no new actions)
4. Retain SignWell account for 90 days read-only to serve audit-log requests

### 8.4 Effort estimate

- Backend abstraction + DocuSeal client: **~5 days**
- Frontend rename + embedded-signer abstraction: **~1 day**
- Webhook handler: **~2 days**
- Migrations + dual-write period + tests: **~3 days**
- Railway deployment of DocuSeal + DNS/TLS + monitoring: **~1 day ops**
- **Total: ~10–12 engineering days.** Contiguous 2-week push or parallel with other work over 4–6 weeks.

---

## 9. Open Questions (Decisions Needed From User)

### 9.1 Is the 100–500/mo volume target actual or aspirational?

If **actual current volume**: SignWell is already over budget today and Phase 1 (migration) should start soon.

If **12-month aspirational**: SignWell free tier or pay-as-you-go is fine today (Phase 0); plan Phase 1 migration for when the 25-doc/mo threshold hits — no urgency.

### 9.2 Does the <$25/mo ceiling include SignWell, or is contract-signing a separate budget line?

If **combined**: Phase 1 (DocuSeal migration) is required as volume grows.

If **separate / signing has its own larger budget**: SignWell $275/mo flat plan is a reasonable status quo; email + estimates still only cost $0–$10/mo and the Phase 0 work stands alone.

### 9.3 Is Grins willing to self-host a third-party open-source service on Railway?

If **yes**: Option A (DocuSeal) is the cleanest Phase 1 target.

If **no** (prefers hosted SaaS or DIY-in-app only): Option B (DIY in-app signer) is the path; plan for 3–5 days of eng work plus legal review.

### 9.4 Does Grins prefer Resend or AWS SES for email?

Default recommendation is Resend. But if the team strongly prefers single-vendor AWS consolidation (simpler billing, IAM consolidation, boto3-only codebase), SES is fine — the incremental effort is marginal and cost is pennies.

### 9.5 For DIY signing (if chosen), has legal counsel reviewed ESIGN-compliance language?

Before shipping any in-app signing flow, a legal pass on the disclosure + intent language is recommended. Estimate: 1–2 hours of attorney time or use of a reputable template vetted for MN consumer contracts.

### 9.6 Where do we want the signed PDF emailed to on completion — customer only, or customer + info@grinsirrigation.com?

Current SignWell default typically emails both parties. Whatever DocuSeal/DIY replaces it with should match.

---

## 10. Appendix A — Complete Vendor Matrix

### 10.1 Email

| Provider | Monthly floor | Free tier | Cost at 500 emails/mo | Cost at 5K/mo | Cost at 50K/mo | Python SDK | Notes |
|---|---|---|---|---|---|---|---|
| Resend | $0 | 3K/mo | $0 | $20/mo | $20/mo (50K cap) | `resend` (modern) | React Email interop |
| AWS SES | $0 | 3K/mo first year only | ~$0.05 | ~$0.50 | ~$5 | `boto3` (already installed) | Sandbox exit + DNS required |
| Postmark | $15 (Basic) | 100/mo | $15 | $15 | $15 + overages | Official | Best deliverability reputation |
| SendGrid | $19.95 (Essentials) | 100/day | $19.95 | $19.95 | $19.95 | Official | Mature; reputation slipped |
| Mailgun | $15 (Foundation) | 100/day | $15 | $15 | $15 + overages | Official | Fine alternative |

### 10.2 E-signature (production API + embedded signing)

| Vendor | Floor | 100 docs/mo | 500 docs/mo | Hosted or self-host | Notes |
|---|---|---|---|---|---|
| SignWell (current) | $0 dev, $275 prod | $56 PAYG / $275 plan | $356 PAYG / $589 plan | Hosted | Already integrated |
| BoldSign | $30 Enterprise API (40 docs) | $75 | $375 | Hosted | — |
| Dropbox Sign API | ~$100 | $100+ | $100+ | Hosted | — |
| PandaDoc | $49+ Business | $49 | $49 + per-doc | Hosted | — |
| DocuSign | $75+ Developer | $75+ | $75+ | Hosted | — |
| eversign | $9.99 / $39.99 / $79.99 | $39.99 (100 docs plan) | $79.99 (unlimited plan) | Hosted | Unlimited tier fits near ceiling |
| Signaturely | $20 | N/A (no API) | N/A | Hosted | Disqualified — no API |
| Documenso Cloud Individual | $25 | $25 | $25 | Hosted | **At ceiling, 1 user** |
| Documenso Cloud Teams | $40 | $40 | $40 | Hosted | Over budget |
| DocuSeal Cloud Pro | $20/user | $20 | $20 | Hosted | **Under budget** |
| **DocuSeal Self-Hosted** | Free software | $5–10 hosting | $5–10 hosting | Self | **Recommended** |
| Documenso Self-Hosted | Free software + unclear commercial license | $5–10 hosting | $5–10 hosting | Self | Verify license |

### 10.3 Estimate / proposal builders (for completeness, all over budget)

| Vendor | Floor | API access | Notes |
|---|---|---|---|
| Proposify | $35/user/mo | Yes on higher tiers | WYSIWYG editor |
| Qwilr | $35/user/mo | Limited | Web-page-style proposals |
| PandaDoc | $49/user/mo Business | Yes | Bundled with e-sign |
| Better Proposals | $19/mo Starter | Limited | Lower price but fewer integrations |
| DocRaptor | $15/mo for 125 docs | PDF-gen API only | Just HTML→PDF — redundant with WeasyPrint |

---

## 11. Appendix B — ESIGN Act / UETA Requirements Reference

Source: [DocuSign — US electronic signature laws (ESIGN Act and UETA)](https://www.docusign.com/products/electronic-signature/learn/esign-act-ueta); [Adobe — difference between ESIGN Act vs UETA](https://www.adobe.com/acrobat/business/hub/difference-between-esign-act-vs-ueta.html).

The four requirements for an electronic signature to be legally valid under U.S. law apply to both ESIGN (federal, 2000) and UETA (state, 1999, adopted by 48 states including MN):

1. **Intent to sign.** Signer must demonstrate clear intent — equivalent to the gesture of writing a signature on paper. A passive click-through is insufficient; a deliberate action tied to a signing label is required.

2. **Consent to do business electronically.** Parties must consent, typically via an e-consent disclosure covering:
   - The right to receive paper copies on request
   - Hardware/software requirements to access the record
   - Procedure to withdraw consent
   - Contact info for the business

3. **Association of signature with record.** The system must generate an audit trail that demonstrates the signature is bound to this specific document. Standard elements:
   - Document hash before signature
   - Signer identity verification (email link, IP, optional SMS OTP for higher-assurance)
   - Timestamp
   - Post-signature document hash

4. **Record retention.** Both parties must be able to access and store the signed document in a form that accurately reflects the agreement. Typically: signed PDF emailed to signer + stored in a retention-compliant manner.

### What hosted e-sign vendors add beyond these requirements

- **Legal indemnity** — some vendors (DocuSign enterprise, Adobe Sign) indemnify you against signature challenges
- **Identity verification levels** — KBA (knowledge-based authentication), ID document scanning, video notarization — not required for standard US commercial contracts
- **Templates with reusable signature fields** — UX polish
- **Multi-party routing** — not needed for Grins' 1:1 customer contracts
- **SOC 2 / HIPAA compliance reporting** — nice for procurement but not legally required for irrigation contracts

For residential irrigation contracts in MN, items 1–4 above are the legal floor. Everything beyond is UX and risk-reduction.

---

## 12. Appendix C — Sources

Verified 2026-04-20.

**Email:**
- [Resend — Pricing](https://resend.com/pricing)
- [Resend — New Free Tier](https://resend.com/blog/new-free-tier)
- [AWS SES — Pricing](https://aws.amazon.com/ses/pricing/)
- [Postmark — Pricing and Free Trial](https://postmarkapp.com/pricing)
- [Email API Pricing Comparison (April 2026) — Resend, SendGrid, Postmark](https://www.buildmvpfast.com/api-costs/email)

**E-signature:**
- [SignWell — API Pricing](https://www.signwell.com/api-pricing/)
- [SignWell — Pricing (web app)](https://www.signwell.com/pricing/)
- [BoldSign — Electronic Signature Pricing](https://boldsign.com/electronic-signature-pricing/)
- [BoldSign — eSignature API](https://boldsign.com/esignature-api/)
- [Documenso — Pricing](https://documenso.com/pricing)
- [Documenso — GitHub](https://github.com/documenso/documenso)
- [DocuSeal — Pricing](https://www.docuseal.com/pricing)
- [DocuSeal — GitHub](https://github.com/docusealco/docuseal)
- [DocuSeal — Signing API](https://www.docuseal.com/signing-api)
- [Railway — Deploy Documenso](https://railway.com/deploy/documenso)
- [Sliplane — 5 Open-Source DocuSign Alternatives](https://sliplane.io/blog/5-open-source-docusign-alternatives)

**Legal / ESIGN / UETA:**
- [DocuSign — US electronic signature laws (ESIGN Act and UETA)](https://www.docusign.com/products/electronic-signature/learn/esign-act-ueta)
- [Adobe — Difference between ESIGN Act vs UETA](https://www.adobe.com/acrobat/business/hub/difference-between-esign-act-vs-ueta.html)
- [Juro — Electronic signature law in the US: ESIGN Act and UETA](https://juro.com/learn/esign-act-ueta)
- [Ironclad — Electronic Signature Law: ESIGN and UETA](https://ironcladapp.com/journal/contract-management/electronic-signature-law)

---

## 13. Next Actions (If Proceeding)

1. **User decides** on the open questions in §9 — specifically 9.1, 9.2, 9.3
2. **Phase 0 (always-good)** — ship Resend integration + EstimatePDFService regardless of the contract-signing decision. ~3 engineering days total.
3. **Phase 1 trigger set** — when SignWell monthly cost crosses $25, begin DocuSeal migration (or flip to DIY, depending on §9.3).
4. **Decision log** — capture the final vendor choice in `DEVLOG.md` with reasoning so future contributors understand why the stack looks the way it does.
