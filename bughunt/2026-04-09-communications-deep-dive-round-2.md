# Communications & Polling Pipeline Deep Dive — Round 2

**Date:** 2026-04-09
**Scope:** Full end-to-end audit of campaign send flow, poll response collection, CSV export, inbound webhooks, audience building, and all frontend components.
**Method:** Parallel code review agents covering 5 pipeline segments.

**Result:** 3 CRITICAL + 9 HIGH + 26 MEDIUM + 19 LOW = **57 bugs total**

Round 1 (same day) found 23 bugs (BUG-001–023), of which 22 were fixed. This round covers everything beyond those initial fixes.

---

## CRITICAL — TCPA / Compliance Risk

All three share the same root cause: CallRail masks inbound phone numbers (e.g. `***3312`), and the opt-out flow blindly uses the masked value instead of resolving the real E.164 phone from the sent_message correlation.

### BUG-C1: Opt-out consent stored with masked phone — STOP is silently lost

**Files:** `src/grins_platform/services/sms_service.py:616,446-458`
**Severity:** CRITICAL

When CallRail sends an inbound STOP message, `from_phone` is the masked form (e.g. `***3312`). `_process_exact_opt_out` calls `self._format_phone(phone)` which strips non-digits, yielding `3312`, then prefixes `+` to produce `+3312`. This garbage value is stored as `SmsConsentRecord.phone_number`. The consent check normalizes to E.164 (`+1XXXXXXXXXX`) and will never match `+3312`, so the customer's real phone is never marked as opted-out and they continue receiving messages.

**Fix:** Resolve the real phone via `thread_id` → `sent_message.recipient_phone` correlation before writing the consent record, matching what `record_opt_out_as_response` already does.

---

### BUG-C2: Opt-out confirmation SMS sent to masked phone — goes nowhere

**File:** `src/grins_platform/services/sms_service.py:640`
**Severity:** CRITICAL

Same root cause as BUG-C1. The confirmation SMS `provider.send_text(formatted_phone, OPT_OUT_CONFIRMATION_MSG)` is sent to `+3312`. The CallRail API will reject this or silently fail. The customer never receives the legally required opt-out confirmation.

**Fix:** Same as BUG-C1 — resolve the real E.164 phone first.

---

### BUG-C3: `_process_exact_opt_out` never receives `thread_id`

**File:** `src/grins_platform/services/sms_service.py:487,599-601`
**Severity:** CRITICAL

`_process_exact_opt_out` is called with only `(from_phone, body_lower)`. The `thread_id` is available in `handle_inbound` scope but is never passed down. Without it, the opt-out handler cannot correlate back to the sent_message to find the real phone number.

**Fix:** Add `thread_id` parameter to `_process_exact_opt_out` and use it to look up the real phone via thread correlation.

---

## HIGH

### BUG-H1: `Campaign.recipients` uses `lazy="selectin"` — every Campaign load eagerly fetches ALL recipients

**File:** `src/grins_platform/models/campaign.py:81-86`
**Severity:** HIGH

```python
recipients: Mapped[list["CampaignRecipient"]] = relationship(
    "CampaignRecipient",
    back_populates="campaign",
    cascade="all, delete-orphan",
    lazy="selectin",
)
```

Every time a `Campaign` is loaded — including `repo.get_by_id()`, `list_with_filters()`, and the worker's `session.get(Campaign, cid)` — SQLAlchemy issues a second SELECT to load ALL recipients. For a campaign with 1000 recipients, this loads 1000 ORM objects into memory on every single Campaign access. The list endpoint showing 20 campaigns loads ALL recipients for ALL 20.

**Fix:** Change to `lazy="noload"` (or `lazy="raise"` to catch accidental access) and use explicit `selectinload()` only where the recipients collection is actually needed.

---

### BUG-H2: No advisory lock on `/send` — concurrent double-click creates duplicate recipients

**File:** `src/grins_platform/services/campaign_service.py:460-548`
**Severity:** HIGH

`enqueue_campaign_send()` checks `campaign.status` is not SENT/SENDING, but there is no `SELECT ... FOR UPDATE` or advisory lock. Two concurrent requests can both see status=DRAFT, both pass the guard, and both create duplicate `CampaignRecipient` rows. Every person receives the SMS twice.

Compare to `retry_failed_recipients()` at line 673-679, which correctly uses `pg_advisory_xact_lock`. The same pattern is missing here.

**Fix:** Add advisory lock before the status check:
```python
await self.repo.session.execute(
    sa_text("SELECT pg_advisory_xact_lock(hashtext(:key))"),
    {"key": f"send:{campaign_id}"},
)
```

---

### BUG-H3: Worker `_update_campaign_status` overwrites CANCELLED back to SENT

**Files:** `src/grins_platform/services/background_jobs.py:647-661`, `src/grins_platform/services/campaign_service.py:579-580`
**Severity:** HIGH

Timeline:
1. User calls `cancel_campaign()` — sets campaign status to `cancelled`, sets pending recipients to `cancelled`.
2. Worker tick is mid-flight with a recipient claimed before the cancel. It finishes sending, then calls `_update_campaign_status()`.
3. `_update_campaign_status()` counts recipients. If all are terminal (worker-sent + cancel-set), it overwrites `campaign.status = SENT`.

This silently un-cancels the campaign.

**Fix:** Add guard in `_update_campaign_status()`:
```python
if campaign.status == CampaignStatus.CANCELLED.value:
    return  # Respect explicit user cancellation
```

---

### BUG-H4: Webhook handler has no try/except — 500 triggers CallRail retries

**File:** `src/grins_platform/api/v1/callrail_webhooks.py:162-168`
**Severity:** HIGH

The call to `sms_service.handle_inbound(...)` is not wrapped in a try/except. Any exception returns HTTP 500 to CallRail, which retries the webhook, potentially causing duplicate processing (the Redis mark-as-processed on line 172 never ran). The session auto-rollback also discards consent revocation records.

**Fix:** Wrap in try/except that logs the error and returns HTTP 200 to prevent retries:
```python
try:
    result = await sms_service.handle_inbound(...)
except Exception:
    logger.exception("sms.webhook.handle_inbound_failed")
    return Response(content='{"status": "error"}', status_code=200)
```

---

### BUG-H5: CSV export buffers entire file in memory — defeats StreamingResponse

**File:** `src/grins_platform/api/v1/campaign_responses.py:141-171`
**Severity:** HIGH

The endpoint uses `StreamingResponse`, but writes all rows into a single `io.StringIO` buffer, then passes `iter([buf.getvalue()])` — a single-element iterator. The database side streams in batches of 100, but all that streaming is wasted because the API endpoint collects everything into memory first. For 50k+ recipients, this risks OOM.

**Fix:** Yield chunks from a true async generator. Write header + each batch to a small StringIO, yield its `.getvalue()`, then `.truncate(0)`.

---

### BUG-H6: `update_campaign` skips `_audience_to_dict()` — date-range filters crash JSONB serialization

**File:** `src/grins_platform/services/campaign_service.py:254`
**Severity:** HIGH

`create_campaign` correctly calls `_audience_to_dict(data.target_audience)` which uses `model_dump(mode="json", exclude_none=True)`, converting `date` objects to ISO strings. But `update_campaign` uses `data.model_dump(exclude_unset=True, exclude_none=False)` — no `mode="json"`, so date-range filters (`last_service_between`, `created_between`) produce raw `datetime.date` objects that crash with `TypeError: Object of type date is not JSON serializable`.

**Fix:** After the poll_options special handling, add:
```python
if "target_audience" in update_fields and update_fields["target_audience"] is not None:
    update_fields["target_audience"] = _audience_to_dict(data.target_audience)
```

---

### BUG-H7: `_filter_recipients` calls `.year` on ISO date string from JSONB

**File:** `src/grins_platform/services/campaign_service.py:979-994`
**Severity:** HIGH

When reading `last_service_between` and `created_between` from `campaign.target_audience` (JSONB column), the values are ISO date strings like `"2024-01-01"`, not `datetime.date` objects. The code at line 980 does `start_d.year`, which throws `AttributeError: 'str' object has no attribute 'year'`. This crashes both preview and send for any campaign using date-range filters.

**Fix:** Parse ISO strings to `date` objects:
```python
from datetime import date as _date
if isinstance(start_d, str):
    start_d = _date.fromisoformat(start_d)
if isinstance(end_d, str):
    end_d = _date.fromisoformat(end_d)
```

---

### BUG-H8: Schedule mode falls through to `onSendNow()` when date is empty

**File:** `frontend/src/features/communications/components/CampaignReview.tsx:108-116`
**Severity:** HIGH

In `handleConfirm()`, the condition is `if (mode === 'schedule' && scheduledDate)`. If `scheduledDate` is empty (user selected "Schedule" mode but didn't pick a date), the code falls through to the `else` branch which calls `onSendNow()` — sending immediately instead of scheduling. The confirm button is disabled in this state, but this can be bypassed via keyboard or race conditions.

**Fix:** Explicitly guard the else branch:
```typescript
if (mode === 'schedule') {
  if (!scheduledDate) return;
  onSchedule(`${scheduledDate}T${scheduledTime}:00`);
} else {
  onSendNow();
}
```

---

### BUG-H9: Stale `selectedCampaign` snapshot after mutations

**File:** `frontend/src/features/communications/components/CommunicationsDashboard.tsx:17-21`
**Severity:** HIGH

When the user clicks a campaign row, a copy of the `Campaign` object is stored in state. Mutations (retry/cancel/delete) change the backend but `selectedCampaign` keeps the old snapshot. The detail view uses stale `campaign.status` to decide which buttons to show and which detail component to render.

**Fix:** Store only the campaign ID, and use a `useCampaign(id)` query hook to always get fresh data from the cache.

---

## MEDIUM

### BUG-M1: Redis dedup key uses wrong field — `payload["id"]` instead of `resource_id`

**File:** `src/grins_platform/api/v1/callrail_webhooks.py:128`
**Severity:** MEDIUM

Per CallRail payload docs, `id` is the conversation-level ID (same for all messages in a conversation), while `resource_id` is the unique per-message ID. Two different inbound messages in the same conversation share `id`, so the second one gets incorrectly deduped and dropped.

**Fix:** Change to `dedup_id = str(payload.get("resource_id", ""))`.

---

### BUG-M2: `correlate_reply` only matches `delivery_status='sent'`, misses `'delivered'`

**File:** `src/grins_platform/services/campaign_response_service.py:110-112`
**Severity:** MEDIUM

If a delivery status webhook updates the sent_message to `'delivered'` before the reply arrives, the correlation fails and the reply becomes an orphan. This race condition becomes more likely with high-volume campaigns and fast delivery confirmations.

**Fix:** `SentMessage.delivery_status.in_(["sent", "delivered"])`

---

### BUG-M3: `parse_inbound_webhook` converts `None` → string `"None"`

**File:** `src/grins_platform/services/sms/callrail_provider.py:267-274`
**Severity:** MEDIUM

If a CallRail payload field is explicitly `null`, `payload.get("thread_resource_id", "")` returns `None` (key exists with value None), then `str(None)` produces the literal string `"None"`. The `or None` on line 272 doesn't catch this because `"None"` is truthy. Correlation attempts with `"None"` as thread_id will fail, creating orphan rows.

**Fix:** Use `payload.get("thread_resource_id") or None` instead of `str(payload.get(...)) or None`.

---

### BUG-M4: `cancel_campaign` has no status guard

**File:** `src/grins_platform/services/campaign_service.py:554-587`
**Severity:** MEDIUM

Allows cancelling DRAFT campaigns (misleading — creates a cancelled campaign with 0 recipients) and already-SENT campaigns (overwrites historical status). An already-cancelled campaign can be cancelled again.

**Fix:** Add status check: only allow cancelling `sending` or `scheduled` campaigns.

---

### BUG-M5: `enqueue_campaign_send` uses `campaign.campaign_type` as channel

**File:** `src/grins_platform/services/campaign_service.py:533`
**Severity:** MEDIUM

For `"both"` type campaigns, the channel is set to `"both"`. The background worker only picks up recipients where `channel == "sms"`, so `"both"` recipients are stuck in `pending` forever.

**Fix:** Determine channel(s) per recipient using `_resolve_channels`, or hardcode `"sms"` for SMS campaigns.

---

### BUG-M6: Recipients inserted one-by-one instead of bulk

**File:** `src/grins_platform/services/campaign_service.py:528-535`
**Severity:** MEDIUM

`enqueue_campaign_send` calls `repo.add_recipient()` per recipient (each does `flush()+refresh()`). For 500 recipients = 1000 DB round trips. The repo already has `add_recipients_bulk()` which flushes once.

**Fix:** Build list and call `repo.add_recipients_bulk()`.

---

### BUG-M7: No DB index on `sent_messages.provider_thread_id`

**File:** `src/grins_platform/models/sent_message.py`
**Severity:** MEDIUM

The `correlate_reply` query filters on `provider_thread_id` but there's no index. As `sent_messages` grows, this degrades to a sequential scan, directly impacting webhook response latency.

**Fix:** Add `Index("ix_sent_messages_provider_thread_id", "provider_thread_id")` to the model and create a migration.

---

### BUG-M8: No unique constraint on `campaign_responses.provider_message_id`

**File:** `src/grins_platform/models/campaign_response.py`
**Severity:** MEDIUM

If Redis dedup fails (Redis unavailable, or BUG-M1 using wrong key), webhook retries insert duplicate response rows. No unique constraint prevents this at the DB level.

**Fix:** Add `CREATE UNIQUE INDEX uq_campaign_responses_provider_msg ON campaign_responses (provider_message_id) WHERE provider_message_id IS NOT NULL`, or add an existence check before insert.

---

### BUG-M9: `record_opt_out_as_response` missing name/address snapshot

**File:** `src/grins_platform/services/campaign_response_service.py:376-388`
**Severity:** MEDIUM

`record_poll_reply` populates `recipient_name` and `recipient_address` from `sent_msg.customer`/`sent_msg.lead`, but `record_opt_out_as_response` doesn't. Opt-out rows show blank names in the response list.

**Fix:** Extract name/address resolution into a shared helper and call from both methods.

---

### BUG-M10: CSV export missing `status` column

**File:** `src/grins_platform/schemas/campaign_response.py:92-100`
**Severity:** MEDIUM

`CampaignResponseCsvRow` has no `status` field. When exporting all responses (no `option_key` filter), the CSV mixes parsed, needs_review, and opted_out rows with no way to distinguish them. Also missing `recipient_address`.

**Fix:** Add `status: str` and `address: str` to `CampaignResponseCsvRow` and populate in `iter_csv_rows`.

---

### BUG-M11: Unicode digits pass `isdigit()` but never match ASCII keys

**File:** `src/grins_platform/services/campaign_response_service.py:173-181`
**Severity:** MEDIUM

Python's `str.isdigit()` returns `True` for non-ASCII digits (Arabic-Indic, fullwidth, etc.). These enter the single-digit branch but fail the `valid_keys` lookup (ASCII-only), silently classifying a valid intent as `needs_review`.

**Fix:** Replace `cleaned.isdigit()` with `cleaned in "123456789"` or `cleaned.isascii() and cleaned.isdigit()`. Use `[0-9]` instead of `\d` in `_OPTION_N_RE`.

---

### BUG-M12: Non-poll sent campaigns always route to FailedRecipientsDetail

**File:** `frontend/src/features/communications/components/CommunicationsDashboard.tsx:70-86`
**Severity:** MEDIUM

A successfully sent non-poll campaign with zero failures still lands on `FailedRecipientsDetail`, showing "No failed recipients" with a confusing layout. There's no generic "sent campaign detail" view.

**Fix:** Add a condition to show a success summary when `stats.failed === 0`, or create a generic `CampaignDetail` component.

---

### BUG-M13: DB draft not updated on step 1 to step 2 transition

**File:** `frontend/src/features/communications/components/NewTextCampaignModal.tsx:211-223`
**Severity:** MEDIUM

When clicking Next from step 1 to step 2, only `setStep(2)` is called — no `updateCampaign.mutateAsync()` to persist the message body and poll options. The DB draft retains the empty body from step 0. If the user closes the browser after reaching step 2 but before sending, the message is lost.

**Fix:** Call `updateCampaign.mutateAsync` in the step 1→2 transition.

---

### BUG-M14: Audience preview has stale closure on filter changes

**File:** `frontend/src/features/communications/components/AudienceBuilder.tsx:188-196`
**Severity:** MEDIUM

The `useEffect` dependency array only includes `.length` values and `csvResult`, but `buildAudience()` captures filter state (`customerSmsFilter`, `customerCityFilter`, etc.). Changing a filter without changing selection count shows stale preview data. The eslint-disable hides this.

**Fix:** Include `buildAudience` in the dependency array, or include the individual filter values.

---

### BUG-M15: Lead SMS filter checkbox has no effect on displayed table

**File:** `frontend/src/features/communications/components/AudienceBuilder.tsx:126-129`
**Severity:** MEDIUM

`leadSmsFilter` state exists and the checkbox toggles it, but it's never passed to `useLeads()`. The leads table always shows all leads regardless of the SMS consent checkbox state.

**Fix:** Pass `sms_consent: leadSmsFilter || undefined` to the `useLeads` params.

---

### BUG-M16: Retry button visible for cancelled campaigns

**File:** `frontend/src/features/communications/components/FailedRecipientsDetail.tsx:139-148`
**Severity:** MEDIUM

"Retry All Failed" is shown whenever `hasFailed` is true, but the backend rejects retries for cancelled campaigns (throws error). User clicks the button and gets a confusing error toast.

**Fix:** Add `campaign.status !== 'cancelled'` to the visibility condition.

---

### BUG-M17: Cancel mutation doesn't invalidate stats/recipients cache

**File:** `frontend/src/features/communications/hooks/useSendCampaign.ts`
**Severity:** MEDIUM

`useCancelCampaign`'s `onSuccess` invalidates `detail` and `lists` but not `stats` or `recipients`. After cancelling, the stats summary and recipients table show stale data until manual navigation.

**Fix:** Add `qc.invalidateQueries({ queryKey: campaignKeys.stats(id) })` and `campaignKeys.recipients(id)` to the onSuccess callback.

---

### BUG-M18: Ghost lead creation failure silently drops ad-hoc recipient

**File:** `src/grins_platform/services/campaign_service.py:1137-1142`
**Severity:** MEDIUM

When `create_ghost_leads=True`, if `create_ghost()` raises an exception, the ad-hoc recipient is silently skipped via `continue` with a `debug`-level log. The preview shows N ad-hoc recipients but some are silently dropped at send time.

**Fix:** Create the `CampaignRecipient` row with `delivery_status="failed"` and `error_message="ghost_lead_creation_failed"` so failures are visible.

---

### BUG-M19: `Recipient.phone` stores raw non-E164 phone

**File:** `src/grins_platform/services/campaign_service.py:1019,1095`
**Severity:** MEDIUM

`normalize_to_e164(cust.phone)` is called for the `seen_phones` dedup key, but `Recipient.from_customer(cust)` stores `cust.phone` (raw DB value like `"6127385301"`). The `Recipient.phone` field may not be E.164 format, causing inconsistencies in phone masking, logging, and downstream `SentMessage.recipient_phone`.

**Fix:** Use the already-normalized phone variable in the Recipient constructor.

---

### BUG-M20: Re-uploading CSV creates duplicate consent records

**File:** `src/grins_platform/services/sms/consent.py:187`
**Severity:** MEDIUM

`bulk_insert_attestation_consent` uses `pg_insert(...).values(rows)` without `ON CONFLICT`. Re-uploading a CSV with overlapping phones creates duplicate `SmsConsentRecord` rows, inflating audit reports.

**Fix:** Add `.on_conflict_do_nothing()` to the insert statement.

---

### BUG-M21: `CampaignResponse` model has `lazy="selectin"` on all 4 relationships

**File:** `src/grins_platform/models/campaign_response.py:79-94`
**Severity:** MEDIUM

All four relationships (`campaign`, `sent_message`, `customer`, `lead`) use `lazy="selectin"`, firing 4 additional SELECTs on every query. Most callers (CSV export, summary, list endpoint) don't need the relationships. The frontend `CampaignResponseRow` type doesn't include nested objects.

**Fix:** Change to `lazy="raise"` and add explicit `selectinload()` only where needed (e.g., `correlate_reply`).

---

### BUG-M22: `retry_failed_recipients` bounces campaign between SENT and SENDING

**File:** `src/grins_platform/services/campaign_service.py:689-707`
**Severity:** MEDIUM

Retry sets campaign from SENT back to SENDING. After retried recipients complete, `_update_campaign_status` sets it back to SENT. This bouncing confuses the frontend and the worker's claim query (which expects SENDING campaigns to have pending recipients).

**Fix:** Either add a `RETRYING` status, or leave as SENT and modify the worker to also pick up pending rows from SENT campaigns.

---

### BUG-M23: Worker rate-limit revert bypasses state machine

**File:** `src/grins_platform/services/background_jobs.py:516-518`
**Severity:** MEDIUM

The code validates `sending→failed` transition, but then actually writes `pending`. The state machine doesn't allow `sending→pending`. Works operationally but the state machine is deliberately circumvented.

**Fix:** Either add `sending→pending` as a valid transition (for rate-limit retries), or don't call `transition()` at all in this path.

---

### BUG-M24: `needsReviewCount`/`optedOutCount` only reads first bucket

**File:** `frontend/src/features/communications/components/CampaignResponsesView.tsx:74-77`
**Severity:** MEDIUM

Uses `.find()?.count` (first match only) instead of `.filter().reduce()` (sum all). If the backend returns multiple needs_review buckets (one per option_key), only the first is counted. `parsedCount` correctly uses `.filter().reduce()`.

**Fix:** Use `.filter().reduce()` for both `needsReviewCount` and `optedOutCount`.

---

### BUG-M25: "After consent filter" preview label is misleading

**File:** `frontend/src/features/communications/components/AudienceBuilder.tsx:338`
**Severity:** MEDIUM

The preview endpoint does NOT check `SmsConsentRecord` consent or hard-STOP status. It only applies audience query filters. Real consent checks only happen at send time in the background worker. The label implies more filtering than actually occurs.

**Fix:** Change label to `"after audience filter"` or `"after dedup"`.

---

### BUG-M26: `_format_phone` produces invalid E.164 for masked phones

**File:** `src/grins_platform/services/sms_service.py:446-458`
**Severity:** MEDIUM

Strips non-digits and blindly prepends `+`. For CallRail's `***3312`, produces `+3312`. For empty strings, produces `+`. Used in opt-out flow and campaign dedup.

**Fix:** Replace with `normalize_to_e164` from `phone_normalizer`, and handle `PhoneNormalizationError`.

---

## LOW

### BUG-L1: Schedule datetime constructed without timezone suffix

**File:** `frontend/src/features/communications/components/CampaignReview.tsx:111`
**Severity:** LOW

`${scheduledDate}T${scheduledTime}:00` has no timezone. Backend interprets in server timezone, not Central Time as the UI claims.

**Fix:** Append `-05:00` (CST) or `-06:00` (CDT), or use a timezone-aware library.

---

### BUG-L2: Typed confirmation is case-sensitive

**File:** `frontend/src/features/communications/components/CampaignReview.tsx:101-102`
**Severity:** LOW

Expected: `SEND 50`. If user types `send 50`, button stays disabled with no explanation.

**Fix:** Case-insensitive comparison: `typedConfirmation.toUpperCase() === expectedConfirmation`.

---

### BUG-L3: Headers-only CSV silently succeeds with 0 recipients

**File:** `src/grins_platform/services/sms/csv_upload.py:140-194`
**Severity:** LOW

A CSV with only headers returns `CsvParseResult(total_rows=0, recipients=[])`. No error or warning shown.

**Fix:** Raise `ValueError("CSV contains no data rows")` if `total_rows == 0`.

---

### BUG-L4: Content-Disposition filename not quoted per RFC 6266

**File:** `src/grins_platform/api/v1/campaign_responses.py:170`
**Severity:** LOW

`attachment; filename={filename}` should be `attachment; filename="{filename}"`.

---

### BUG-L5: `list_responses` parameter `status` shadows `fastapi.status` import

**File:** `src/grins_platform/api/v1/campaign_responses.py:17,101`
**Severity:** LOW

Function parameter `status: str | None` shadows `from fastapi import status`. Maintenance trap — any use of `status.HTTP_xxx` inside the function would reference the query parameter.

**Fix:** Rename parameter to `response_status` or alias import.

---

### BUG-L6: No `page_size` upper bound on campaign responses list

**File:** `src/grins_platform/api/v1/campaign_responses.py:102-103`
**Severity:** LOW

Client can request `page_size=1000000`, loading all rows into memory.

**Fix:** Add `page_size: int = Query(default=20, ge=1, le=100)`.

---

### BUG-L7: CSV "Export all" includes opted-out and needs-review with no filter

**File:** `src/grins_platform/repositories/campaign_response_repository.py:147-170`
**Severity:** LOW

`iter_for_export` has no `status` filter. Combined with BUG-M10 (no status column in CSV), exports mix valid selections with unrecognized replies and opt-outs.

**Fix:** Add optional `status` filter parameter.

---

### BUG-L8: `_mask_phone` produces `"***"` for CallRail-masked phones

**File:** `src/grins_platform/services/campaign_response_service.py:44-48`
**Severity:** LOW

Already-masked phones like `***3312` (7 chars) get `len < 10` path, losing even the last-4 digits info.

**Fix:** If phone already contains `*`, return as-is.

---

### BUG-L9: Orphan recovery resets sending rows of cancelled campaigns to failed

**File:** `src/grins_platform/services/sms/state_machine.py:84-90`
**Severity:** LOW

The orphan recovery SQL updates ALL `sending` rows older than 5 minutes, regardless of campaign status. Cancelled campaigns' sending rows become `failed` instead of `cancelled`.

**Fix:** Join to `campaigns` and only recover rows from SENDING-status campaigns.

---

### BUG-L10: Worker creates new Redis connection per recipient

**File:** `src/grins_platform/services/background_jobs.py:499-526`
**Severity:** LOW

`Redis.from_url(redis_url)` is called inside the per-recipient loop. Should be created once at tick level and reused.

---

### BUG-L11: Double consent check — worker checks, then SMSService checks again

**File:** `src/grins_platform/services/background_jobs.py:487-495`
**Severity:** LOW

Worker explicitly calls `check_sms_consent()`, then `sms_svc.send_message()` checks again internally. Two DB queries for consent per recipient.

**Fix:** Remove the explicit worker-level check; let `SMSService.send_message()` be the single enforcement point.

---

### BUG-L12: Selection checkboxes in FailedRecipientsDetail have no corresponding action

**File:** `frontend/src/features/communications/components/FailedRecipientsDetail.tsx:85-100`
**Severity:** LOW

Checkboxes exist for individual row selection, but "Retry All Failed" ignores selection and retries ALL. No "Retry Selected" button exists. The `data-testid` is `retry-selected-btn` but the label says "Retry All Failed".

**Fix:** Either remove checkboxes or add a "Retry Selected" action.

---

### BUG-L13: `selectedIds` not cleared on page change

**File:** `frontend/src/features/communications/components/FailedRecipientsDetail.tsx:66`
**Severity:** LOW

Paginating retains IDs from previous pages in the `selectedIds` Set.

**Fix:** Clear `selectedIds` when `page` changes.

---

### BUG-L14: N+1 API calls — `useCampaignStats` called per campaign row

**File:** `frontend/src/features/communications/components/CampaignsList.tsx:54-66`
**Severity:** LOW

Each visible campaign row triggers `/campaigns/{id}/stats`. With page size 20, that's 20 extra API calls.

**Fix:** Include basic stats in the campaigns list endpoint response.

---

### BUG-L15: Progress bar can overflow on rounding

**File:** `frontend/src/features/communications/components/CampaignsList.tsx:72-73`
**Severity:** LOW

`sentPct + failedPct` can exceed 100% due to independent `Math.round()` calls, overflowing the bar container.

**Fix:** Cap `failedPct` at `Math.min(failedPct, 100 - sentPct)`.

---

### BUG-L16: `dedupeCount` conflates cross-source dedup with server-side filter exclusions

**File:** `frontend/src/features/communications/components/AudienceBuilder.tsx:207-209`
**Severity:** LOW

Client-side `totalSelected - effectivePreview.total` is labeled as "dedupe" but the difference may include filter exclusions (deactivated customers, etc.), not actual phone deduplication.

**Fix:** Return true cross-source dedup count from the server in `AudiencePreviewResponse`.

---

### BUG-L17: No pagination for CommunicationsQueue unaddressed items

**File:** `frontend/src/features/communications/components/CommunicationsQueue.tsx:29-36`
**Severity:** LOW

Only the first page is shown with no way to navigate further.

---

### BUG-L18: `markAddressed.isPending` disables all buttons simultaneously

**File:** `frontend/src/features/communications/components/CommunicationsQueue.tsx:102`
**Severity:** LOW

All "Mark as Addressed" buttons share the same pending state. Can't tell which is being processed.

---

### BUG-L19: Status badge not capitalized in SentMessagesLog

**File:** `frontend/src/features/communications/components/SentMessagesLog.tsx:279`
**Severity:** LOW

Raw lowercase status values shown inconsistently with other components that capitalize.

---

## Priority Fix Order

**Phase 1 — Compliance (CRITICAL):**
BUG-C1, C2, C3 (single root-cause fix in opt-out flow)

**Phase 2 — Data Integrity (HIGH):**
BUG-H1 (lazy loading), BUG-H2 (double-send lock), BUG-H3 (cancel race), BUG-H6+H7 (date-range crash)

**Phase 3 — Reliability (HIGH):**
BUG-H4 (webhook error handling), BUG-H5 (CSV streaming), BUG-H8 (schedule fallthrough), BUG-H9 (stale state)

**Phase 4 — Medium batch:**
BUG-M1 through M26, grouped by file to minimize context switching

**Phase 5 — Low / polish:**
BUG-L1 through L19
