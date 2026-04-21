# Gap 07 — Webhook Security & Dedup

**Severity:** 2 (high — security)
**Area:** Backend (inbound webhook)
**Status:** Investigated, not fixed
**Related files:**
- `src/grins_platform/api/v1/callrail_webhooks.py:82-198` — webhook handler
- `src/grins_platform/api/v1/callrail_webhooks.py:30-80` — Redis dedup helpers
- `src/grins_platform/services/sms/callrail_provider.py:210-242` — `verify_webhook_signature`

---

## Summary

Three related inbound-webhook weaknesses, all on the CallRail inbound path:

- **7.A:** Signature verification is HMAC-SHA1 with no timestamp/nonce. Replay attacks are possible against captured payloads.
- **7.B:** Redis dedup on `(conversation_id, created_at)` silently passes when Redis is unavailable. A Redis outage turns every retried webhook into a duplicate processed event.
- **7.C:** No inbound rate limiter. An attacker or buggy provider could flood the endpoint.

Individually each is low-to-medium severity; together they allow:
- Replay + dedup bypass: captured webhook + Redis outage (or different `created_at`) → the replayed event processes as new.
- Flood: no rate limiter → unbounded inbound processing (DB inserts, SMS sends on acknowledgments) until the DB connection pool is exhausted.

---

## 7.A — HMAC-SHA1, no replay protection

### Current behavior

`callrail_provider.py:210-242`:

```python
async def verify_webhook_signature(
    self,
    headers: dict[str, str],
    raw_body: bytes,
) -> bool:
    if not self._webhook_secret:
        return False
    signature = headers.get("signature", "")
    if not signature:
        return False
    expected = base64.b64encode(
        hmac.new(
            self._webhook_secret.encode(),
            raw_body,
            hashlib.sha1,  # SHA1, not SHA256
        ).digest(),
    ).decode()
    return hmac.compare_digest(expected, signature)
```

Observations:
- **Algorithm:** HMAC-SHA1. (This is what CallRail documents; we're matching their spec. SHA1 is cryptographically broken for some use cases, but HMAC-SHA1 remains strong enough for message authentication. Not an immediate concern, just a note.)
- **Header:** `signature` (lowercase, no `x-` prefix).
- **Body:** raw bytes — not re-serialized. Good.
- **Comparison:** constant-time `hmac.compare_digest`. Good.
- **Timestamp / nonce:** **none**.

### Why the lack of timestamp check matters

A captured webhook payload (e.g., intercepted on a network or via a log that leaked) can be replayed indefinitely against our endpoint. If the payload represents a Y confirmation, it would re-arrive as a new webhook event:

- `conversation_id` in body is the same as original.
- `created_at` in body is the same as original.
- Signature still matches (body unchanged).

**Redis dedup** (`_is_duplicate`) should catch this — it keys on `(conversation_id, created_at)`. **But**:
- TTL is 24h. A replay after 24+ hours passes.
- If Redis is down or the key evicted, the replay passes immediately.

### Proposed fix

Layered defense:

1. **Timestamp header check.** CallRail sends `created_at` in the body; if there's a timestamp-like header, use it. Otherwise rely on body `created_at`. Reject if `now - created_at > ACCEPT_WINDOW` (suggest 5 minutes). This eliminates captured-payload replay after the window.

2. **Extend Redis TTL on `(conversation_id, created_at)` dedup to 7 days.** 24h is too short; webhook retries from providers can span days in failure cases. Memory cost at SMS volume is negligible.

3. **Optional: dual-key dedup.** Store `(provider_message_id)` key independently with 30-day TTL; any replay of a known message_id is blocked even if `created_at` was tampered. CallRail's payload structure needs verification — if `message_id` is stable, this is cheap.

### Edge cases
- Legitimate delayed webhooks (provider retries after network blip) land a few minutes late. 5-min window is usually enough; make it configurable per provider.
- Clock skew between our server and provider can shift `created_at` by seconds; use a generous window (5 min minimum).

---

## 7.B — Redis dedup silent pass on unavailability

### Current behavior

`callrail_webhooks.py:30-80`:

```python
_REDIS_KEY_PREFIX = "sms:webhook:processed:callrail"
_REDIS_TTL_SECONDS = 86400  # 24 hours

async def _is_duplicate(redis, conversation_id: str, created_at: str) -> bool:
    if redis is None:
        return False
    key = f"{_REDIS_KEY_PREFIX}:{conversation_id}:{created_at}"
    try:
        return (await redis.get(key)) is not None
    except Exception:
        logger.warning("sms.webhook.redis_unavailable")
        return False   # ← silent pass

async def _mark_processed(redis, conversation_id: str, created_at: str) -> None:
    if redis is None:
        return
    key = f"{_REDIS_KEY_PREFIX}:{conversation_id}:{created_at}"
    try:
        await redis.set(key, "1", nx=True, ex=_REDIS_TTL_SECONDS)
    except Exception:
        logger.warning("sms.webhook.redis_mark_failed")
```

When Redis is unavailable:
- `_is_duplicate` returns `False` → webhook is processed as new.
- `_mark_processed` silently fails → the next duplicate also passes.

Two duplicates in a row (legitimate provider retry during Redis outage) → both processed → possibly two `JobConfirmationResponse` rows, two auto-replies SMS sent to customer, two admin alerts for a single C reply, etc.

### Why it's a problem

- Redis isn't bulletproof. A planned or unplanned outage is routine.
- Providers retry on `5xx` responses aggressively — commonly within seconds, up to 10+ times over hours.
- Silent pass means the outage amplifies customer-facing consequences: duplicate cancellation SMSes, duplicate admin alerts, duplicate response rows.

### Proposed fix

Pick a policy and be explicit:

- **Option A — fail closed.** If Redis is unavailable, return `503 Service Unavailable`. Provider retries when Redis is back. Pros: no duplicates. Cons: brief outage windows reject valid webhooks that can be retried later.

- **Option B — fail open with DB-backed fallback dedup.** If Redis is unavailable, do a DB query: `SELECT 1 FROM sent_messages_processed WHERE provider_message_id=X` (new lightweight log table) and skip if seen. Falls back to DB at 10× the cost but maintains correctness.

- **Option C — fail open, accept duplicate risk, emit metric.** Document the tradeoff and alert on Redis unavailability so ops intervenes.

Recommendation: **Option B** for this codebase. It gives correctness without hard-failing the endpoint, and the DB is always available if the app is running.

### Edge cases
- Race between Redis recovery and in-flight requests: some requests see Redis down, some see it up. The DB fallback avoids the race because it reads authoritative data.
- Storage growth: add a rolling delete job for rows older than 30 days.

---

## 7.C — No inbound rate limiting

### Current behavior

Grep for `rate_limit`, `throttle`, `slowapi` on inbound paths — no inbound rate limiter. The outbound rate limiter (`rate_limit_tracker.py`) tracks CallRail's outbound quota headers; it has nothing to do with inbound.

An attacker hitting `POST /webhooks/callrail/inbound` with valid HMAC signatures (if the secret leaks, or via an exploit chain) can submit arbitrary payloads at full throughput. Even without a secret leak, if an attacker knows the URL they can DoS the endpoint with high-volume unauthenticated posts — every request still goes through signature verification (CPU), JSON parsing, body hashing.

### Why it matters

- Flood amplification: a single valid-looking webhook can trigger 1+ DB inserts (sent_message_processed log, `JobConfirmationResponse`, or `RescheduleRequest`), 1+ outbound SMS sends (auto-reply), and 1+ Alert row. Multiplier effect.
- Resource exhaustion: DB connection pool saturates → *other* paths (admin UI, customer-facing onboarding) start failing.
- Cost: outbound auto-reply SMSes cost real money per message; a flood of fake Y replies could generate a surprise SMS bill.

### Proposed fix

1. **Per-IP rate limit on the webhook endpoint.** A simple `slowapi` or Redis-backed leaky bucket: 60 requests/minute per IP, burst 20. CallRail traffic is low-volume (a few per minute at peak) so this has zero impact on legitimate traffic.

2. **Per-phone rate limit for auto-reply generation.** Even if inbound passes, only generate an auto-reply SMS if we haven't already sent one to that `from_phone` in the last N seconds. Prevents a flood of Y replies from generating a flood of reassurance SMSes.

3. **Global-circuit-breaker on outbound SMS.** If we're sending > X auto-replies/second, circuit-break and alert ops. Paired with the outbound rate limit tracker.

### Edge cases
- CallRail's legitimate retry behavior after a 5xx → our 429 rate limit would reject the retry and make things worse. Use a high threshold and emit 503 (not 429) if we want the provider to retry.
- Internal proxy/CDN: rate limit per-IP where "IP" is the original client, not the CDN egress. Use `X-Forwarded-For` correctly (with a trusted-proxies allowlist).

---

## Cross-references
- **Gap 05** — webhook processing events should be audited (at least per-attack investigation).
- **Gap 14** — add dashboard alert for "webhook signature failures in last hour" and "Redis fallback in use" so ops sees them.
- **Gap 03** — stale-thread correlation issues are amplified when replay protection is weak (an old Y can re-target the old appointment).
