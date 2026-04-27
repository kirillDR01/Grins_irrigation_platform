# Design — Filling the Gaps

This document only covers the missing pieces from `current-state.md` §2. The token model, status transitions, and portal endpoints are already designed and shipped — we are not redesigning them.

## 1. Token model (already shipped — included for context)

The chosen model is a **DB-stored UUID v4** issued at estimate creation, with an absolute `token_expires_at` and a `token_readonly` boolean that flips on first decision. This was a good choice and we are keeping it. Reasons to NOT switch to JWT:

- A signed JWT carrying the estimate ID would let us rotate without writing to the DB, but estimate tokens are one-shot — once approved/rejected the token is dead — so the rotation argument is moot.
- The DB-stored UUID gives us free revocation (set `token_expires_at` to `now`) and free per-token audit (`approved_ip`, `approved_user_agent` are columns on the same row). JWTs would push that to a separate audit table.
- 122 bits of UUID v4 entropy is well past the threshold where guessing is meaningful. PostgreSQL `gen_random_uuid` is cryptographically random.

**Threat model accepted:** the token is a bearer credential. Anyone who possesses the URL can view + approve. This matches every estimate/quote vendor in the industry. Mitigations below.

### 1.1 URL token mitigations to consider

| Risk | Mitigation | Build effort |
|---|---|---|
| Token leaks via shared screen / forwarded email | **60-day expiry** (decided 2026-04-25). Could shorten if drift becomes an issue. | One-line change: `TOKEN_VALIDITY_DAYS = 60` |
| Token leaks via web server access logs at customer's ISP / corp proxy | Use POST-only for approval, not idempotent GET; we already do this. | Already done |
| Brute-force token guessing | Add rate limiter to `/portal/estimates/*` (e.g., 60 req/min per IP). | Small — `slowapi` or similar |
| Customer forwards email; second viewer "approves" pretending to be them | We log IP+UA but cannot fully prevent. Adding a confirm-by-SMS-code at approve time would close this if needed. **Decision: accept the risk in v1.** | Optional v2 |

## 2. Email vendor — Resend

This is settled in `../email and signing stack/stack-research-and-recommendations.md` §4. Summary:

- Free tier: 3,000/mo, 100/day. Covers projected volume (300–5,000 emails/mo) at the low end and most of the high end.
- AWS SES is the fallback if free tier is exceeded (~$0.20/mo at 2K emails after the first-year free, never above $1/mo at projected volume).
- Python SDK is `resend`; trivially drops into `_send_email`.
- Domain DNS setup (SPF, DKIM, DMARC for `grinsirrigation.com`) is required before launch — see `build-plan.md` §3.

### 2.1 Provider abstraction

We do **not** introduce a generic `EmailProvider` base class for v1. Reasons:

- There is exactly one provider planned (Resend). YAGNI.
- The existing `EmailService` is already the abstraction — `_send_email` is the one place a vendor lives.
- If we later swap to SES, the change is ~20 LOC inside `_send_email`, not a multi-class refactor.

If volume ever forces a multi-provider failover, that is the moment to introduce a strategy pattern. Not now.

## 3. `send_estimate_email` API design

New method on `EmailService`:

```python
def send_estimate_email(
    self,
    *,
    customer: Customer | Lead,  # accept either; estimates can be from a lead
    estimate: Estimate,
    portal_url: str,
) -> dict[str, Any]:
    ...
```

Signature mirrors existing `send_lead_confirmation` / `send_welcome_email`. Returns the same dict shape (`{"sent": bool, "sent_via": str, "recipient_email": str, "content": str, "disclosure_type": None}`).

**Classification:** `TRANSACTIONAL` (`_classify_email("estimate_sent")` — already in the transactional set at line 105 as `"invoice"` but `"estimate_sent"` will need adding). Estimates are responses to a request; CAN-SPAM does not apply, no unsubscribe required, sent from `noreply@grinsirrigation.com`.

**Subject line (proposed):** `Your estimate from Grin's Irrigation` — simple, low spam-flag risk. Avoid `$` and excessive punctuation.

**`Reply-To` header:** Set to `info@grinsirrigation.com` (Q6 decision). Customers who hit Reply land in the monitored inbox; the auto-responder on `noreply@` handles direct replies to the From address.

**Body template** (`templates/emails/estimate_sent.html`) — content blocks:

1. Greeting (`{{ customer_name }}`)
2. One-paragraph summary: "Your estimate is ready. Total: ${{ total }}. Valid through {{ valid_until }}."
3. CTA button → `{{ portal_url }}` — text: *Review your estimate*
4. Plain-text URL fallback below the button (some email clients strip CSS)
5. "Reply to this email or call (952) 818-1020 with any questions."
6. Standard footer with business address, phone, email
7. **No unsubscribe link** (transactional)

We will produce both an HTML version (Jinja2) and a plain-text alternative for clients that prefer text. Resend's SDK accepts both in one call.

## 4. `EstimateService.send_estimate` change

Replace the email-branch log-only block (`estimate_service.py:300–311`) with:

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
            self.log_failed("send_estimate_email", error=e, estimate_id=str(estimate_id))
```

Same fallback for `estimate.lead` is added below the `estimate.customer` block.

## 5. `portal_base_url` configuration

Move out of the `EstimateService.__init__` default. Add to `EmailSettings` (or a new `PortalSettings`):

```python
class EmailSettings(BaseSettings):
    ...
    portal_base_url: str = Field(default="http://localhost:5173", alias="PORTAL_BASE_URL")
```

Three values per environment:

| Env | `PORTAL_BASE_URL` |
|---|---|
| Dev | `http://localhost:5173` (Vite default) |
| Staging | `https://staging-portal.grinsirrigation.com` (TBD if a staging environment exists; not blocking) |
| Prod | `https://portal.grinsirrigation.com` (confirmed 2026-04-25) |

Wherever `EstimateService` is constructed in `dependencies.py` / DI wiring, pass `settings.portal_base_url`. Tests can keep the existing inline value.

## 6. Post-approval workflow

The customer-facing side does what it already does (`token_readonly=True`, lead tag flipped to `ESTIMATE_APPROVED`, follow-ups cancelled). Adding an internal staff notification on top.

### 6.1 Internal notification (decided 2026-04-25)

When a customer approves or rejects, fire **both** an internal email and an internal SMS to the sales team. Recipients are environment-configurable.

**Env vars:**
- `INTERNAL_NOTIFICATION_EMAIL` — empty default; dev `.env` ships with `kirillrakitinsecond@gmail.com`. Prod TBD.
- `INTERNAL_NOTIFICATION_PHONE` — empty default; dev `.env` ships with `+19527373312`. Prod TBD.

**Trigger points:** End of `EstimateService.approve_via_portal` and `EstimateService.reject_via_portal`, after the DB transaction commits successfully. A new private method on `EstimateService`:

```python
async def _notify_internal_decision(
    self,
    estimate: Estimate,
    decision: Literal["approved", "rejected"],
) -> None:
    """Fire-and-log internal staff notification. Never raises."""
    recipient_email = os.getenv("INTERNAL_NOTIFICATION_EMAIL", "").strip()
    recipient_phone = os.getenv("INTERNAL_NOTIFICATION_PHONE", "").strip()
    customer_name = self._resolve_customer_name(estimate)

    subject = f"Estimate {decision.upper()} for {customer_name}"
    body = self._render_internal_notification_body(estimate, decision)

    if recipient_email and self.email_service:
        try:
            self.email_service.send_internal_estimate_decision_email(
                to_email=recipient_email,
                subject=subject,
                body=body,
            )
        except Exception as e:
            self.log_failed("internal_notify_email", error=e, estimate_id=str(estimate.id))

    if recipient_phone and self.sms_service:
        sms_text = f"{subject}. Total ${estimate.total}. Open admin to action."
        try:
            await self.sms_service.send_automated_message(
                phone=recipient_phone,
                message=sms_text,
                message_type="internal_estimate_decision",
            )
        except Exception as e:
            self.log_failed("internal_notify_sms", error=e, estimate_id=str(estimate.id))
```

**Failure semantics:** All notification failures are logged at `WARNING` and swallowed. A vendor outage on Resend or the SMS provider must NOT undo the customer's approval — the customer's intent is recorded and we'll surface the decision via the existing lead tag UI even if the staff notification was lost.

**Reuse the dev allowlists:** Both `+19527373312` and `kirillrakitinsecond@gmail.com` are already on the SMS and email allowlists (per Q4 and the existing SMS rule), so the dev guard rails apply automatically. No extra wiring needed.

**Why both channels (email + SMS) instead of one:** Approval is a high-value event for the sales rep — it's the moment they should switch context to "send the contract." Email gives the searchable record; SMS gives the immediate ping if they're not at a desk. SMS for sales notifications carries no marketing-consent risk because it goes to internal staff, not customers.

### 6.2 SignWell handoff (unchanged from prior design)

For v1 scope: **skip auto-creating the SignWell contract**. The product flow today is "approval routes a lead, sales rep manually clicks send-for-signature" — and the new internal notification (§6.1) is what tells the rep to do it. Auto-creating a SignWell document on approval is a product decision that:

- Removes a checkpoint where a rep can sanity-check the line items before locking the contract
- Couples approval and contract — if the SignWell create fails, the customer's approval is still recorded, but the contract is in a broken state
- Has SignWell pricing implications (every approval becomes a billed SignWell document)

Recommend keeping the manual handoff. Revisit if the rep workflow turns out to be a bottleneck.

## 7. Status field semantics

Today the `EstimateStatus` enum has `VIEWED` but nothing transitions to it. Two options for v1:

- **(A) Skip VIEWED.** Leave the enum value but don't drive it. Pro: less code. Con: the sales UI cannot show "customer has looked at it but not decided."
- **(B) Transition to VIEWED on first GET.** In `get_portal_estimate`, after `_validate_portal_token` succeeds and the estimate is in `SENT`, write `status = VIEWED`. Idempotent — second GET is a no-op.

Recommend **(B)** — it costs ~5 lines and gives the sales tab a useful signal. Concern: GET is called every page reload, which is fine because the UPDATE only fires on the SENT→VIEWED transition.

## 8. Security checklist (final)

| Item | Status |
|---|---|
| Token never logged in full | ✅ already enforced (`_mask_token`) |
| Token in URL is HTTPS-only | Must verify deployment cert + HSTS |
| Approve/Reject is POST, not GET (so a link prefetcher cannot trigger approval) | ✅ already POST |
| Idempotent on already-decided estimates (409 not 500) | ✅ already enforced |
| IP + UA captured | ✅ already captured |
| Rate limiting on portal endpoints | ❌ open — see §1.1 |
| Email content does not include the token verbatim outside the link | ✅ template will only include the URL |
| Bounce / hard-fail handling on email send | ❌ open — Resend will report bounces; need to decide whether to surface to the sales rep or just suppress further sends |
| `RESEND_API_KEY` not committed to repo | ✅ — it goes in env, like all other secrets |
| `noreply@` is properly configured for replies (forward to a monitored inbox or auto-reply) | ❌ open — see open-questions.md |

Items marked ❌ are tracked in `build-plan.md` as either v1 must-haves or v2 follow-ups.
