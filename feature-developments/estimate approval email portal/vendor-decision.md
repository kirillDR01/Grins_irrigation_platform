# Email Vendor Decision

**Status:** ✅ **DECIDED — Resend, starting on free tier (3,000/mo, 100/day, no expiration). Upgrade to Pro $20/mo if/when we hit a cap.** Confirmed by user 2026-04-25.
**Date:** 2026-04-25
**Original recommendation considered:** Resend Pro vs. AWS SES (see analysis below). Free tier was the practical choice once user confirmed monthly volume is well under 3,000 emails.

This refreshes the broader vendor research at `../email and signing stack/stack-research-and-recommendations.md` (2026-04-20) with current pricing and a code-fit pass against `src/grins_platform/services/email_service.py`.

## 1. TL;DR

| Concern | Resend Pro | AWS SES |
|---|---|---|
| Monthly cost at 5K emails | $20 (flat to 50K) | ~$0.50 |
| New Python dep | `resend` (1 small package) | None — `boto3` is already used for S3 |
| Setup friction | DNS records, ~30 min | DNS records + sandbox approval (~24h) + SNS for bounces |
| Code change to integrate | ~25 LOC in `_send_email` | ~30 LOC in `_send_email` |
| Bounce/open/click webhooks | Built-in dashboard + webhooks | DIY via SNS topic + Lambda or webhook receiver |
| Multi-domain sender (`noreply@` + `info@`) | 10 verified domains included on Pro | Each address verified separately, no per-address fee |
| Debuggability | Dashboard with rendered email previews + full search | CloudWatch + manual setup |
| Vendor lock-in risk | Low — `_send_email` is the only call site | None — boto3 is provider-neutral within AWS |

**My recommendation:** Resend Pro. The $19.50/mo delta vs. SES buys (a) zero sandbox approval delay, (b) a usable debugging UI when emails don't deliver, (c) one fewer thing to operate, and (d) better DX during the build. SES becomes the right answer if Grins is already deeply invested in AWS-everything or if every dollar of fixed cost matters.

## 2. Pricing refresh — April 2026

Verified by hitting each vendor's pricing page on 2026-04-25.

| Vendor | Free tier | First paid tier | Overage / extra | Python SDK | Webhooks |
|---|---|---|---|---|---|
| **Resend** | 3,000/mo, **100/day cap**, no expiry | **$20/mo Pro — 50K/mo, 10 domains, 1 dedicated IP optional** | $0.90 / 1K | Official `resend` (April 2026) | Yes (delivered/bounced/opened/clicked) |
| **AWS SES** | 3,000/mo, **first 12 months only** | Pay-as-you-go: **$0.10 / 1K** = ~$0.50/mo at 5K | $0.10/1K, $0.12/GB attachments, dedicated IP $24.95/mo | `boto3` (already in stack) | Yes via SNS / EventBridge |
| **Brevo** | 300/day (~9K/mo), all features | **$9/mo Starter — 5K/mo** | Prepaid credit packs | Official `sib-api-v3-sdk` | Yes |
| **Postmark** | 100/mo, no expiry | **$15/mo — 10K/mo** | $1.80 / 1K | `postmarker` | Yes |
| **SendGrid** | 100/day trial | **$19.95/mo Essentials — 50K/mo** | ~$0.001/email | Official `sendgrid` | Yes |
| **Mailgun** | 100/day, 1 domain | **$35/mo Foundation — 50K/mo** | $1.30 / 1K | Community SDK | Yes |
| **ZeptoMail** | 10K credit (one-time) | ~$2.50–3 per 10K = $1.50/mo at 5K | Same; credits expire 6 months | None official | Yes |
| **Loops** | 4K sends/mo, 1K contacts | **$49/mo Starter** | None — by contact count | None (REST only) | Limited |
| **Plunk** | 1,000/mo | $0.001/email PAYG; self-hostable AGPL | Linear | OSS | Limited |
| **MailPace** | 100/mo (hidden) | ~$10/mo or $40/yr for 1K/mo | Tiered | None official | Yes |

### 2.1 What changed since the 2026-04-20 research

- **Resend Pro is now the right entry tier**, not the free tier. The prior doc's "free covers projected volume" claim relies on assuming 100 emails/day max. In practice Grins will exceed that on busy days — irrigation is seasonal (April–May spike), and a single batch of "send estimate" + "follow-up day 3" + "follow-up day 7" + welcome + lead confirm can easily push 100 in an hour.
- **Resend released an official Python SDK** in April 2026 (it was there before but recently went 1.0 with cleaner typings). Cleaner integration than 2025.
- **No major new entrants in the past 4 days.** Loops, Plunk, MailPace, ZeptoMail were already evaluated indirectly. None of them displace Resend or SES on the Grins constraint axes (need: managed, Python SDK, webhooks, cheap, 5K/mo headroom).

### 2.2 Why not the others

- **Mailgun ($35), Loops ($49):** over budget at entry tier.
- **Postmark ($15):** technically in budget but ActiveCampaign acquisition has degraded support reputation, and $1.80/1K overage is worst-in-class.
- **SendGrid ($19.95):** Twilio acquisition stagnation; recent shared-IP rejection by Microsoft for ~36h. Reputational risk for a small business that can't absorb a deliverability incident.
- **Brevo ($9):** real contender on price. Caps at 5K/mo (we'd hit it in peak season). Less developer-focused; UI is built more for marketing teams. Can revisit if user wants the $11/mo savings.
- **ZeptoMail:** cheapest paid, but 6-month credit expiry creates operational annoyance, and no first-party Python SDK means we'd write the HTTP layer ourselves.
- **Plunk, MailPace, Loops:** small vendors. Not worth the bus-factor risk for a business-critical integration.

## 3. Code-fit analysis

The vendor plugs into `src/grins_platform/services/email_service.py` at `_send_email` (line 157–195). Both Resend and SES are clean fits to the existing abstraction.

### 3.1 What the code expects from a provider

The current `_send_email` signature is:

```python
def _send_email(
    self,
    *,
    to_email: str,
    subject: str,
    html_body: str,
    email_type: str,
    classification: EmailType,
) -> bool:
```

The provider must:
- Accept HTML body (we render with Jinja2 already)
- Accept a `From` header that we set per-classification (`noreply@grinsirrigation.com` for transactional, `info@grinsirrigation.com` for commercial)
- Return success/failure synchronously (the codebase isn't using async sends today)
- Not require us to manage suppression lists ourselves — we already maintain `email_opt_in` flags in `Customer`

The codebase already has the surrounding infrastructure: Jinja2 templates, JWT-based unsubscribe tokens, sender splitting, CAN-SPAM physical-address gating. The vendor only owns transport.

### 3.2 Resend integration sketch

Diff against `email_service.py`:

```python
# Top of file
import resend  # NEW

# In __init__:
def __init__(self, settings: EmailSettings | None = None) -> None:
    super().__init__()
    self.settings = settings or EmailSettings()
    self._jinja_env: Environment | None = None
    if self.settings.is_configured:                    # NEW
        resend.api_key = self.settings.email_api_key   # NEW

# Replace _send_email body (line 172–195):
def _send_email(self, *, to_email, subject, html_body, email_type, classification) -> bool:
    sender = self._get_sender(classification)
    masked = _mask_email(to_email)

    if not self.settings.is_configured:
        self.logger.warning("email.send.pending", recipient=masked, email_type=email_type, classification=classification.value)
        return False

    try:
        response = resend.Emails.send({
            "from": f"Grin's Irrigation <{sender}>",
            "to": [to_email],
            "subject": subject,
            "html": html_body,
        })
        self.logger.info("email.send.completed", recipient=masked, email_type=email_type,
                         classification=classification.value, sender=sender, subject=subject,
                         provider_message_id=response.get("id"))
        return True
    except Exception as e:
        self.logger.error("email.send.failed", recipient=masked, email_type=email_type, error=str(e))
        return False
```

Plus `pyproject.toml` adds `resend>=1.0.0` and `.env.example` adds `RESEND_API_KEY=`.

**Total diff: ~25 LOC + 1 dep + 1 env var.**

### 3.3 AWS SES integration sketch

```python
# Top of file
import boto3                                      # NEW
from botocore.exceptions import ClientError      # NEW

# In __init__:
def __init__(self, settings: EmailSettings | None = None) -> None:
    super().__init__()
    self.settings = settings or EmailSettings()
    self._jinja_env: Environment | None = None
    self._ses = None                                                          # NEW
    if self.settings.is_configured:                                           # NEW
        self._ses = boto3.client("sesv2", region_name=self.settings.aws_region)  # NEW

# Replace _send_email body:
def _send_email(self, *, to_email, subject, html_body, email_type, classification) -> bool:
    sender = self._get_sender(classification)
    masked = _mask_email(to_email)

    if not self._ses:
        self.logger.warning("email.send.pending", recipient=masked, email_type=email_type)
        return False

    try:
        response = self._ses.send_email(
            FromEmailAddress=f"Grin's Irrigation <{sender}>",
            Destination={"ToAddresses": [to_email]},
            Content={
                "Simple": {
                    "Subject": {"Data": subject},
                    "Body": {"Html": {"Data": html_body}},
                },
            },
        )
        self.logger.info("email.send.completed", recipient=masked, email_type=email_type,
                         classification=classification.value, sender=sender, subject=subject,
                         provider_message_id=response["MessageId"])
        return True
    except ClientError as e:
        self.logger.error("email.send.failed", recipient=masked, email_type=email_type,
                          error_code=e.response["Error"]["Code"], error_msg=str(e))
        return False
```

Plus `EmailSettings` adds `aws_region: str = "us-east-2"` (or wherever S3 already is). No new dependency since boto3 is already in `pyproject.toml`.

**Total diff: ~30 LOC + 0 deps + 1 env var.**

### 3.4 Codebase fit verdict

Both fit. SES wins by one variable on "no new dependency"; Resend wins by one variable on "less verbose API call." The deciding factor isn't code — it's operational.

## 4. Operational comparison

| Operational concern | Resend | AWS SES |
|---|---|---|
| Initial DNS setup (SPF, DKIM, DMARC) | ~30 min (Resend dashboard provides records) | ~30 min (SES console provides records) |
| Sandbox-to-production approval | None | **AWS sandbox approval required** — submit a use-case form to AWS, typical turnaround 24h. Until approved, can only send to verified addresses. |
| Bounce / complaint handling | Built-in dashboard + optional webhook | **DIY** — must subscribe an SNS topic to the configured-set, then either receive SNS pushes or poll an SQS queue. Adds 1 service and ~50 LOC. |
| Reputation management | Resend manages shared IP pool | We manage on shared IP; pay $24.95/mo for dedicated IP if needed |
| Debuggability when an email goes missing | Dashboard search by recipient/status/event | CloudWatch logs + manual tracing |
| Vendor risk | Resend is Y Combinator W23, growing, well-funded as of 2026 | AWS — zero risk |

**Net:** SES is operationally heavier in the first month (sandbox + bounce wiring) but cheaper to run forever. Resend trades $19.50/mo for zero ops drag.

## 5. Cost projection — 2 years out

Pessimistic case: Grins grows to 1,000 estimates/mo, ~10K emails/mo.

| Year | Resend Pro | AWS SES |
|---|---|---|
| Year 1 | $240 | $0–6 (free tier 3K/mo for first 12 months) |
| Year 2 | $240 | $12–24 |
| 5-year cumulative | $1,200 | ~$50–120 |

The $1,150 5-year delta is real money for a small business. But this assumes Grins doesn't have one bounce/deliverability incident worth more than that in lost trust — which is exactly the kind of incident managed-vendor dashboards help avoid.

## 6. Recommendation

**Pick Resend Pro.**

Why:
- Stays under the $25/mo budget ceiling explicitly. ($20 leaves $5 for adjacent tools if needed.)
- Headroom: 50K/mo is 10× projected peak, so we never re-evaluate vendors due to volume in foreseeable horizon.
- Zero sandbox delay → Phase 1 of `build-plan.md` can start day one.
- Multiple verified domains on Pro covers `noreply@` + `info@` without paying extra (some vendors charge per domain).
- Bounce/open/click webhooks are turn-key for the v2 bounce-tracking work.
- The Python SDK is one of the cleanest in the field as of April 2026.
- If we later regret it, the swap to SES is ~30 LOC because the abstraction is already in place.

**Pick AWS SES instead** if:
- The business is on a strict budget where $20/mo is meaningful relative to total opex
- Engineering capacity is available to wire SNS bounce handling and absorb the sandbox approval delay
- There's an organizational preference for AWS-only

## 7. What this changes in the rest of the plan

- **`open-questions.md` Q1** is answered: Resend (subject to user override).
- **`build-plan.md` Phase 1** mostly stands as written — replace `RESEND_API_KEY` references and add `resend>=1.0.0` to deps.
- **Phase 0 DNS work** is unchanged — same SPF/DKIM/DMARC pattern as SES would have required.
- **Phase 4 v2 bounce handling** simplifies — Resend webhooks rather than SNS topic + Lambda.

## 8. Sources

- [Resend Pricing](https://resend.com/pricing)
- [Resend Python SDK](https://pypi.org/project/resend/)
- [AWS SES Pricing](https://aws.amazon.com/ses/pricing/)
- [Postmark Pricing](https://postmarkapp.com/pricing)
- [Postmark / ActiveCampaign FAQ](https://postmarkapp.com/postmark-activecampaign-faq)
- [SendGrid Pricing review](https://www.sender.net/reviews/sendgrid/pricing/)
- [Mailgun Pricing](https://www.mailgun.com/pricing/)
- [Brevo Pricing](https://www.brevo.com/pricing/)
- [Zoho ZeptoMail Pricing](https://www.zoho.com/zeptomail/pricing.html)
- [Loops Pricing](https://loops.so/pricing)
- [Plunk Pricing](https://www.useplunk.com/pricing)
- [MailPace Pricing](https://mailpace.com/pricing)
