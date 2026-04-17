# CallRail Inbound Webhook — Destination-Number Filtering

**Status:** Open / not implemented
**Discovered:** 2026-04-14, during prod CallRail webhook setup pre-deploy
**Severity:** Medium — causes duplicate cross-environment processing, not data loss
**Affects:** Both `Grins-dev` and `Grins_irrigation_platform` services

---

## Problem Statement

The inbound SMS webhook handler at `/api/v1/webhooks/callrail/inbound` (file: `src/grins_platform/api/v1/callrail_webhooks.py`, function `callrail_inbound`) does **not** filter incoming webhook payloads by the destination number (the CallRail tracking number that received the SMS).

CallRail allows multiple webhook URLs to be registered against the same account. When a customer texts any tracking number on the account, CallRail fires **every registered webhook URL** with the same payload. There is currently no per-number filter applied in CallRail's webhook configuration UI either (or at least none we've used).

The CallRail payload **does** include a `destination_number` field, and the platform parses it into the `InboundSMS.to_phone` field at `callrail_provider.py:271`. But `handle_inbound()` in `SMSService` ignores `to_phone` — it only uses `from_phone`, `body`, `provider_sid`, and `thread_id`.

Combined effect:

| Customer texts | CallRail fires | Dev backend processes? | Prod backend processes? |
|---|---|---|---|
| `+19525293750` (dev "Website" number) | both registered URLs | ✅ yes | ✅ yes ← unintended |
| `+19525229540` (prod "Google My Business" number) | both registered URLs | ✅ yes ← unintended | ✅ yes |

## Concrete Failure Modes

1. **Double `SmsConsentRecord` writes for STOP keywords.** Customer texts STOP to the prod number → both backends write a `consent_given=false` row to their respective databases. Dev's row is meaningless (not a real customer there) but adds noise.
2. **Cross-database lookup misses for Y/R/C confirmations.** A real prod customer's `R` reply for an appointment confirmation: dev tries to find the appointment in dev's DB, fails (because the appointment lives only in prod), logs a warning, and may write a stranded `JobConfirmationResponse` row.
3. **Stranded scheduling-poll responses.** A customer's reply to a prod scheduling poll arrives at dev too; dev has no matching `Campaign`, so the `CampaignResponse` insert either fails or attaches to nothing useful.
4. **Audit-log noise.** Both backends write `sms.webhook.inbound` audit rows for every inbound, doubling the audit footprint.
5. **Redis dedup does NOT solve this.** The dedup key is `sms:webhook:processed:callrail:{conversation_id}:{created_at}` and lives in *each backend's* Redis instance independently. Cross-backend dedup would require a shared Redis or, better, the destination-number filter described below.

## What CallRail Provides in the Payload

From `callrail_provider.py:267-274`:

```python
return InboundSMS(
    from_phone=str(payload.get("customer_phone_number") or ""),
    body=str(payload.get("content") or ""),
    provider_sid=str(payload.get("resource_id") or ""),
    to_phone=str(payload.get("destination_number") or "") or None,
    thread_id=str(payload.get("thread_resource_id") or "") or None,
    conversation_id=str(payload.get("conversation_id") or "") or None,
    raw_payload=payload,
)
```

The `destination_number` is present and parsed into `to_phone`. We just don't use it for filtering downstream.

---

## Three Mitigation Options

### Option A — Remove the unused webhook URL from CallRail (operational mitigation, no code change)

If only one environment needs to receive inbound SMS at any given time, remove the other environment's webhook URL from CallRail.

**Pros:**
- Zero code change.
- Zero deployment risk.
- Reversible in seconds (re-add the URL).
- Cleanest blast radius for production cutovers.

**Cons:**
- The "blind" environment loses all inbound SMS until its webhook is re-registered or replaced (e.g. via ngrok for local dev).
- Easy to forget to re-enable later, leaving dev permanently blind.
- Doesn't scale — if you later add staging, you have to choose which one environment "wins."

**Recommended use case:** Production launch / cutover window. Remove the dev URL right before going live, run for a stabilization period, then either re-add dev or move dev to ngrok / a separate CallRail account.

---

### Option B — Use CallRail's per-number webhook filter (configuration mitigation, no code change)

If CallRail's webhook configuration UI exposes a "scope this webhook to specific tracking numbers" option, configure it so that:
- Dev webhook only fires for `+19525293750` (Website tracker).
- Prod webhook only fires for `+19525229540` (Google My Business tracker).

**Pros:**
- Both environments keep working independently.
- No code change.
- Permanent, set-and-forget.

**Cons:**
- Depends on a CallRail feature that may or may not be available on the current plan tier — needs UI verification.
- Operational discipline required: every new tracking number added later has to be associated with the right webhook, or it falls back to firing both.

**Recommended use case:** First option to try. Open the CallRail webhook config and look for a per-tracker / per-number filter dropdown. If present, pick this and skip the other options.

---

### Option C — Add a destination-number filter to the inbound handler (code mitigation, permanent fix)

Modify `callrail_inbound()` in `src/grins_platform/api/v1/callrail_webhooks.py` to discard payloads whose `destination_number` does not match the local `CALLRAIL_TRACKING_NUMBER` env var. Approximate diff:

```python
# After signature verification and JSON parse, before the dedupe block:
expected_to = os.environ.get("CALLRAIL_TRACKING_NUMBER", "").strip()
incoming_to = str(payload.get("destination_number", "")).strip()
if expected_to and incoming_to and incoming_to != expected_to:
    logger.info(
        "sms.webhook.foreign_destination_skipped",
        provider="callrail",
        expected_to=expected_to,
        incoming_to=incoming_to,
    )
    return Response(
        content='{"status": "ignored_foreign_destination"}',
        status_code=status.HTTP_200_OK,
        media_type="application/json",
    )
```

Return 200 (not 4xx) so CallRail does not retry.

**Pros:**
- Permanent fix, robust to any number of webhook URLs registered in CallRail.
- Defensive — works even if CallRail's per-number filter is misconfigured later.
- Test coverage trivial: feed a payload whose `destination_number` doesn't match the env var and assert the response is 200 with the `ignored_foreign_destination` log emitted.

**Cons:**
- Requires a code change, a new commit, and a deploy.
- Needs symmetric handling: also consider whether the `signwell_webhooks` or any other multi-environment webhooks need the same treatment.
- Phone-number normalization concern: CallRail may return `destination_number` masked (e.g., `***9540`) for compliance — verify the env var format matches what CallRail actually sends. Normalize both sides through `phone_normalizer.normalize_to_e164()` before comparing.

**Recommended use case:** Long-term fix. Land in the next sprint after the launch dust settles, alongside any other observability / hardening work.

---

## Recommended Sequence

1. **Right now (pre-launch):** Option A — remove the dev webhook URL from CallRail. Zero risk to the launch, fastest to do.
2. **Within 24 hours:** Option B — re-add a dev webhook with a per-number filter, if CallRail supports one. Verify dev gets `+19525293750` traffic only.
3. **Within next sprint:** Option C — implement the destination-number filter in code. Once landed, the operational mitigation in step 1/2 becomes a defense-in-depth backstop instead of the primary control.

## Acceptance Criteria for "Done"

- [ ] Inbound SMS to `+19525293750` is processed only by the dev backend.
- [ ] Inbound SMS to `+19525229540` is processed only by the prod backend.
- [ ] No `JobConfirmationResponse` or `CampaignResponse` rows are written to the wrong-environment database during a 24-hour observation window.
- [ ] Audit logs (`sms.webhook.inbound` events) match the expected per-environment volume — no doubled-up entries.
- [ ] Code-level filter (Option C) has unit-test coverage for both the matching and the foreign-destination case.
- [ ] Runbook (`deployment-instructions/callrail-webhook-setup.md`) updated to describe the per-environment expectation and the filter behavior.

## Related Files

- `src/grins_platform/api/v1/callrail_webhooks.py` — webhook entry point
- `src/grins_platform/services/sms/callrail_provider.py` — payload parsing (`parse_inbound_webhook`)
- `src/grins_platform/services/sms_service.py` — `handle_inbound()` business logic
- `src/grins_platform/services/sms/phone_normalizer.py` — for normalizing both sides before comparison (Option C)
- `deployment-instructions/callrail-webhook-setup.md` — runbook to update once Option C lands
