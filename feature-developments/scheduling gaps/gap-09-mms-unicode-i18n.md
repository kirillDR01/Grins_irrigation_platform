# Gap 09 — MMS, Unicode, and Internationalization

**Severity:** 4 (low — edge case frequency, but unbounded failure modes)
**Area:** Backend (inbound parser)
**Status:** Investigated, not fixed
**Related files:**
- `src/grins_platform/services/sms/callrail_provider.py` — `parse_inbound_webhook`
- `src/grins_platform/services/job_confirmation_service.py:45-65` — keyword map (English-only)
- `src/grins_platform/services/campaign_response_service.py:187-200` — poll reply parser (ASCII digits only)

---

## Summary

The inbound reply parser assumes:
- **Text-only** (SMS, not MMS — no photos, audio, video).
- **ASCII / English keywords** (Y, yes, confirm, R, reschedule, C, cancel, 1, 2, 3).
- **No emoji / symbol replies** (👍, ✅, 👎 → unrecognized).
- **No non-English replies** (Spanish "sí" / "no" / "cancelar" → unrecognized).

Current behavior for any of the above: inbound lands in `_handle_needs_review` or orphans, is not actionable, sits for manual triage.

Customer-facing cost: low today (customer base is English-speaking, mostly 40+, MMS replies rare). Still worth documenting because:
- A single MMS reply can silently kill the correlation (depending on provider payload shape).
- Grins is in a multilingual metro (Minneapolis has significant Spanish and Somali-speaking populations).
- Emoji replies are common among younger customers (👍 is a natural "Y").

---

## 9.A — MMS handling (photos, multimedia replies)

### Current behavior

`parse_inbound_webhook` in the CallRail provider is presumed to read `content` / `body` text from the payload. If the customer sends an MMS (photo of their driveway, audio message, etc.), the text portion may be empty or contain only a caption.

Downstream:
- `handle_inbound` passes the empty/caption body to keyword parsing.
- Empty → `_handle_needs_review` → orphan row in `campaign_responses` or `communications`.
- Media URL(s) in the payload are **not captured** — no place to store them in `JobConfirmationResponse` or `RescheduleRequest`.

### Proposed fix

1. **Detect MMS in parser.** If `payload.media_urls` (or whatever CallRail's field is — needs verification) is non-empty, treat as MMS.

2. **Add `media_urls: JSONB` column to `JobConfirmationResponse`.** Or a sibling `InboundAttachment` table linked by response_id. Store the provider's media URLs so they're available for download later.

3. **Auto-reply policy for MMS:** send "Thanks for the photo — we'll review it with your appointment details." Create an Alert (`alert_type='MMS_RECEIVED'`) with a link to the media so admin can review.

4. **Do not fall through to needs_review silently.** MMS with empty text should surface distinctly, not look like a regular unrecognized reply.

### Edge cases
- **Storage cost:** CallRail hosts the media at a URL with a limited retention; need to download and rehost in S3 for long-term access. Tie into the existing `attachments` pattern if possible.
- **PII / content moderation:** customers could send photos of sensitive content. Follow existing photo-storage policy (encryption, access controls).

---

## 9.B — Unicode / emoji replies

### Current behavior

`job_confirmation_service.py:45-65` maps exact strings after `.lower()` and `.strip()`:

```python
CONFIRM_KEYWORDS = {"y", "yes", "confirm", "ok", "okay"}
RESCHEDULE_KEYWORDS = {"r", "reschedule", "different time", "change time"}
CANCEL_KEYWORDS = {"c", "cancel", "cancelled"}
```

Customer sends "👍" or "✅" or "sure 👍" — none match. Falls to `_handle_needs_review`.

### Examples that currently don't work

| Customer sends | Expected intent | Current behavior |
|---|---|---|
| 👍 | Confirm | needs_review |
| ✅ | Confirm | needs_review |
| 👎 | Cancel? | needs_review (ambiguous intent) |
| "yup" | Confirm | needs_review (not in keyword set) |
| "no" | Cancel? (or could mean "not yet") | needs_review |
| "k" | Confirm (texting shorthand) | needs_review |
| "👍 thanks" | Confirm | needs_review |
| "lol no" | Cancel (with attitude) | needs_review |

Each of these generates a queue item that an admin has to triage manually.

### Proposed fix

1. **Expand keyword sets with common emoji and shorthand:**
   ```python
   CONFIRM_KEYWORDS = {
       "y", "yes", "yeah", "yep", "yup", "ok", "okay", "k", "kk",
       "confirm", "confirmed", "sure", "sounds good", "great",
       "👍", "✅", "🙌", "👌", "💯",
   }
   ```
   Use substring containment for emoji-plus-text cases: `if "👍" in body.lower()` etc. (carefully, to avoid false positives).

2. **Confidence scoring.** Instead of boolean match, return `(keyword, confidence)`. High confidence → auto-process. Medium → ask for clarification ("Got it — just to confirm, are you saying YES?"). Low → needs_review.

3. **Reject dangerous auto-matches.** "No problem" should NOT map to "no" → cancel. Use word boundaries and care with substring matches.

### Edge cases
- **Regional emoji variation** (skin tone modifiers on 👍, variant selectors): normalize Unicode before matching.
- **Keyboard shortcut autocorrect** that changes "k" to "K." (with period) or "okay" to "OK" — handle punctuation stripping.

---

## 9.C — Non-English replies

### Current behavior

Spanish: "sí", "no", "cancelar", "reprogramar" — none match. Same for French, Somali, Hmong, etc.

### Scale of the problem today

Likely low. Grins' customer base is presumably mostly English-speaking. But the Minneapolis-Saint Paul metro has meaningful Spanish and Somali communities, and the product may expand. A single non-English customer generates 100% failure rate on their replies.

### Proposed fix (tiered)

1. **Short term: detect non-English and apologize.** Use a lightweight language-detect library (`langdetect`, `fasttext-langdetect`) on the raw body. If detected language != 'en', send: *"We currently only support English replies. Please call [business_phone] or reply in English."* Create an Alert for admin visibility.

2. **Medium term: Spanish.** If the customer base justifies it, translate the outbound templates and add Spanish keyword sets. Requires:
   - A `preferred_language` field on Customer.
   - Translated templates (confirmation, reschedule, cancellation, reminder).
   - Keyword sets per language.

3. **Long term: i18n framework.** Proper gettext or equivalent, admin UI for translators, per-locale opt-in.

### Edge cases
- **Code-switching:** a customer might send "yes" + some Spanish. Language detection may report Spanish but intent is confirm. Use keyword match as a first pass regardless of detected language — if it matches, take it.
- **Accented characters:** "sí" with accent vs. "si" without. Normalize diacritics before matching.

---

## Proposed consolidated priority

MMS and emoji handling are cheap wins (small code changes, no UI changes, reduces needs_review noise). Non-English handling is a larger cross-cut and should wait until customer-base signals demand for it.

Start with:
1. Emoji additions to keyword sets (`👍` = confirm, `👎` = needs_review with special alert).
2. MMS detection + capture of media URLs.
3. Shorthand additions ("yup", "k", "kk", "sure").

---

## Cross-references

- **Gap 01.C** — free-text alternatives attachment for rescheduling benefits from emoji/shorthand tolerance.
- **Gap 06** — informal opt-out in other languages (e.g., Spanish "deja de enviar") doesn't flag today.
- **Gap 14** — MMS and unrecognized-language should become dashboard alert types.
