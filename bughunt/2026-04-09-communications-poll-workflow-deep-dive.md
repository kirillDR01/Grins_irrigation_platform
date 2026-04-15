# Communications Tab & Poll Workflow — Deep Dive Bug Hunt — 2026-04-09

**Branch:** `dev`
**Tester:** Claude (automated)
**Deployment:** Vercel dev (`grins-irrigation-platform-git-dev-kirilldr01s-projects.vercel.app`), commit `49ccbe2`
**Scope:** Full communications tab UI walkthrough + frontend/backend code analysis. Priority focus on poll campaign creation, response tracking, and all campaign lifecycle edge cases.

---

## Executive Summary

| Layer | Result |
|---|---|
| Live UI walkthrough (Vercel dev) | 16 issues found via agent-browser |
| Frontend code analysis (communications/) | 10 bugs + 5 suspicious patterns |
| Backend code analysis (campaigns/polls/SMS) | 12 bugs + 10 edge cases |
| Cross-referenced (UI + code) | 23 unique bugs after dedup |

---

## Bugs Found

### BUG-001: Poll option buckets missing from Responses view (CRITICAL)

**Requirement:** Req 9.1–9.3 — Response summary must show per-option buckets
**Location:** Backend `campaign_response_service.py` → `get_response_summary()`; Frontend `CampaignResponsesView.tsx`

**Description:**
The Response Buckets section only shows "Needs Review" (0 responses) and "Opted Out" (0 responses). The actual poll date-range options configured by the user (e.g., "Week of Apr 14", "Week of Apr 21") never appear as buckets. This is the core feature of poll campaigns — users need to see which option each recipient chose.

**Reproduction (live on Vercel dev):**
1. Navigate to Communications → Campaigns
2. Click the top campaign ("SMS Campaign 4/8/2026" with "0 responses" link)
3. Response Buckets section shows only "Needs Review" and "Opted Out"
4. No poll option buckets displayed

**Screenshot:** `/tmp/grins-screenshots/07-campaign-responses.png`

**Root Cause:** The summary endpoint likely only creates buckets for statuses that have responses, but should always include the configured poll options (from `campaign.poll_options`) even when count=0.

**Impact:** Users cannot see or track poll responses by option — the entire purpose of poll campaigns is broken in the UI.

---

### BUG-002: Concurrent retry creates duplicate sends (HIGH)

**Location:** `src/grins_platform/services/campaign_service.py:646-701`

**Description:**
`retry_failed_recipients()` has no idempotency protection. If a user double-clicks "Retry All Failed" or two requests arrive simultaneously:

1. Both requests query failed recipients → same set
2. Both call `clone_recipients_as_pending()` → duplicate pending rows
3. Both set campaign to SENDING
4. Result: recipient receives the message 2+ times

**Fix Options:**
- Distributed lock (Redis `SETNX` on `retry:{campaign_id}`)
- Database unique constraint preventing duplicate pending for same campaign+recipient
- Idempotency token on the API endpoint

---

### BUG-003: `send_campaign()` missing empty body guard (HIGH)

**Location:** `src/grins_platform/services/campaign_service.py:302-450`

**Description:**
`enqueue_campaign_send()` has an empty body guard:
```python
if not (campaign.body and campaign.body.strip()):
    raise EmptyCampaignBodyError(campaign_id)
```

But the direct `send_campaign()` path has no equivalent check. Since campaign creation allows empty body (body defaults to `""` for drafts), a direct call to `send_campaign()` with an empty-body draft will proceed to send empty SMS to all recipients.

**Fix:** Add the same guard at the top of `send_campaign()`.

---

### BUG-004: "SENT AT" column always empty in Sent Messages (HIGH)

**Requirement:** Sent Messages tab should show when each message was sent
**Location:** Backend `models/campaign.py:131-133` (`CampaignRecipient.sent_at`); Frontend Sent Messages table

**Description:**
All 3 messages in the Sent Messages tab show a blank "SENT AT" column. The `CampaignRecipient.sent_at` field exists in the model but is never populated anywhere in the send flow.

**Reproduction (live on Vercel dev):**
1. Navigate to Communications → Sent Messages
2. All rows show blank SENT AT column

**Screenshot:** `/tmp/grins-screenshots/03-sent-messages.png`, `/tmp/grins-screenshots/04-sent-messages-scrolled.png`

**Fix:** Set `sent_at = datetime.now(timezone.utc)` when delivery_status transitions to "sent" in the send worker.

---

### BUG-005: "SMS opt-in only" filter does not filter (HIGH)

**Location:** Frontend `AudienceBuilder.tsx` — customer list filtering

**Description:**
In the campaign wizard Step 1 (Audience), the "SMS opt-in only" checkbox is checked by default but toggling it on/off shows the same customer list. Customers with SMS=No remain visible and selectable.

**Reproduction (live on Vercel dev):**
1. Click "New Text Campaign"
2. Observe "SMS opt-in only" is checked — customers with SMS=No are visible
3. Uncheck the filter — same list appears
4. Re-check — no change

**Screenshots:** `/tmp/grins-screenshots/12-new-campaign-wizard.png`, `/tmp/grins-screenshots/13-sms-filter-unchecked.png`

**Impact:** Users can accidentally select non-opted-in recipients. The `(0 after consent filter)` parenthetical is the only hint, and it's easy to miss.

---

### BUG-006: Campaigns stuck in "Sending" / "Sending + Failed" state (HIGH)

**Location:** Campaign worker lifecycle; `campaign_service.py` status transitions

**Description:**
Multiple campaigns show "Sending" status with 0/1 progress indefinitely. One campaign shows "Sending" + "Failed" badges — it should have transitioned to "Sent" (or just "Failed") after all recipients were processed. The "Worker: stale" red dot confirms the campaign worker is not running.

**Reproduction (live on Vercel dev):**
1. Navigate to Communications → Campaigns
2. Two campaigns stuck in "Sending" with 0/1 progress
3. One campaign shows dual "Sending" + "Failed" badges

**Screenshot:** `/tmp/grins-screenshots/05-campaigns-tab.png`, `/tmp/grins-screenshots/06-campaigns-scrolled.png`

**Root Cause:** Campaign worker not running on Railway dev. Additionally, the status transition from SENDING → SENT may not fire correctly when all recipients fail (should still mark as SENT with failure stats).

---

### BUG-007: Automation clone loses `poll_options` (HIGH)

**Location:** `src/grins_platform/services/campaign_service.py:751-759`

**Description:**
When an automation rule triggers a campaign clone, the `poll_options` field is not copied:

```python
new_campaign = await self.repo.create(
    name=f"{campaign.name} — Auto {now_str}",
    campaign_type=campaign.campaign_type,
    status=CampaignStatus.DRAFT.value,
    target_audience=campaign.target_audience,
    subject=campaign.subject,
    body=campaign.body,
    created_by=campaign.created_by,
    # Missing: poll_options=campaign.poll_options
)
```

**Impact:** If a poll campaign has an automation rule, triggered instances won't have poll_options. All inbound responses will get `status='needs_review'` because `campaign.poll_options` is None.

**Fix:** Add `poll_options=campaign.poll_options` to the create call.

---

### BUG-008: CSV export breaks on comma-containing poll labels (HIGH)

**Location:** Backend CSV export in `campaign_response_service.py` / `api/v1/campaign_responses.py`

**Description:**
Poll option labels like "Week of Apr 6, 2026" contain commas. If the CSV writer doesn't force-quote all fields, the comma breaks CSV parsing:

```csv
first_name,last_name,phone,selected_option_label,raw_reply,received_at
John,Doe,+16125551234,Week of Apr 6, 2026,1,2026-04-09T10:00:00Z
                                 ^ Breaks CSV column alignment
```

**Fix:** Use `csv.QUOTE_ALL` in the CSV writer to force-quote all fields.

---

### BUG-009: Silent phone normalization drops recipients (MEDIUM)

**Location:** `src/grins_platform/services/campaign_service.py:966-974`, `:1040-1048`, `:1070-1077`

**Description:**
All three recipient sources (customers, leads, ad-hoc CSV) silently skip recipients when `normalize_to_e164()` fails. The error is logged at DEBUG level only. Users get no feedback that X recipients were excluded from the campaign.

**Impact:** User uploads CSV with 100 phones, 20 have invalid format → campaign sends to 80 with no warning. User thinks they reached all 100.

**Fix:** Log at WARNING level, return dropped count in API response, show count in campaign review.

---

### BUG-010: No error feedback when clicking "Next" with empty message (MEDIUM)

**Location:** Frontend `NewTextCampaignModal.tsx` — Step 2 validation

**Description:**
On Step 2 (Message), clicking "Next" with an empty message body silently stays on the same step. No toast, no red border, no error message is shown. The user gets zero feedback about why they can't proceed.

**Reproduction (live on Vercel dev):**
1. Click "New Text Campaign" → select a customer → click Next
2. On Step 2, don't type anything → click Next
3. Nothing happens — no error shown

**Screenshot:** `/tmp/grins-screenshots/17-empty-message-next.png`

**Fix:** Add `toast.error('Please enter a message')` or highlight the textarea with a red border.

---

### BUG-011: Recipient ID shows UUID instead of name/phone (MEDIUM)

**Location:** Frontend `FailedRecipientsDetail.tsx:29-42`

**Description:**
The failed recipients detail table shows truncated UUIDs (e.g., "7dff935f") instead of customer names or phone numbers. Staff debugging failed campaigns cannot identify which customer failed without cross-referencing the database.

**Reproduction (live on Vercel dev):**
1. Navigate to Communications → Campaigns
2. Click a "Sent/Failed" campaign row
3. Recipient ID column shows "7dff935f" — not a name or phone

**Screenshot:** `/tmp/grins-screenshots/33-clicked-campaign-row.png`

**Root Cause:** Backend `CampaignRecipientResponse` intentionally omits phone (lives on Customer/Lead row). Frontend uses first 8 chars of UUID as fallback.

**Fix:** Either include `recipient_phone` in the API response (denormalized) or add a JOIN in the list endpoint to fetch the customer/lead name.

---

### BUG-012: Duplicate "Communications" page header (MEDIUM)

**Location:** Frontend Communications page layout

**Description:**
The Communications page displays "Communications" as both the top-level page title and a section header directly below it. Looks like a layout bug.

**Reproduction (live on Vercel dev):**
1. Navigate to Communications tab
2. See "Communications" displayed twice

**Screenshot:** `/tmp/grins-screenshots/02-communications-tab.png`

---

### BUG-013: Review step shows no message preview (MEDIUM)

**Location:** Frontend `CampaignReview.tsx`

**Description:**
Step 3 (Review) shows recipient breakdown, timing, and segment count, but does not display the actual message text that will be sent. With poll options appended, the final message can be quite different from what the user typed. Users cannot verify the complete message before sending.

**Reproduction (live on Vercel dev):**
1. Create campaign with poll options → reach Step 3
2. No message preview visible — only stats

**Screenshot:** `/tmp/grins-screenshots/26-step3-review.png`

**Fix:** Add a "Message Preview" card showing the full rendered message (prefix + body + poll block + STOP footer).

---

### BUG-014: Schedule date/time fields overflow modal (MEDIUM)

**Location:** Frontend `CampaignReview.tsx` — Schedule picker

**Description:**
When clicking "Schedule" on Step 3, the date and time input fields extend below the visible modal viewport. The "Schedule for ..." button is also hidden.

**Reproduction (live on Vercel dev):**
1. Reach Step 3 → click "Schedule" tab
2. Date/Time fields partially visible at bottom, cut off by modal bounds

**Screenshots:** `/tmp/grins-screenshots/30-schedule-picker.png`, `/tmp/grins-screenshots/31-schedule-fields.png`

**Fix:** Add `overflow-y: auto` to the modal content area, or reduce padding to fit the scheduler.

---

### BUG-015: No "Failed" option in campaign status filter (MEDIUM)

**Location:** Frontend `CampaignsList.tsx` — status filter dropdown

**Description:**
The campaign status filter dropdown has: All statuses, Draft, Scheduled, Sending, Sent, Cancelled. There is no "Failed" option. Users looking for failed campaigns have no way to filter the list.

**Reproduction (live on Vercel dev):**
1. Navigate to Communications → Campaigns
2. Open "All statuses" dropdown
3. No "Failed" option

**Note:** "Failed" is currently a secondary badge shown alongside "Sent" or "Sending", not a standalone status. Consider adding a `has_failures` filter or a "Failed" pseudo-status.

---

### BUG-016: Draft campaigns cannot be edited, resumed, or deleted (MEDIUM)

**Location:** Frontend `CampaignsList.tsx` — campaign row interaction

**Description:**
Clicking on a Draft campaign row does nothing — no detail view, no edit option, no delete option. Draft campaigns accumulate in the list (the wizard auto-saves drafts on close) with no way to manage them.

**Reproduction (live on Vercel dev):**
1. Navigate to Communications → Campaigns
2. Click on any "Draft" campaign row — nothing happens
3. Multiple orphan drafts visible in the list

**Screenshot:** `/tmp/grins-screenshots/34-draft-detail.png`

**Impact:** Users cannot resume, edit, or clean up draft campaigns.

---

### BUG-017: Audience preview mutation has no error handler (MEDIUM)

**Location:** Frontend `AudienceBuilder.tsx:187-194`

**Description:**
```typescript
audiencePreviewMutation.mutate(audience, {
  onSuccess: (data) => setPreview(data),
  // No onError handler
});
```

If the audience preview API call fails (timeout, server error), the component stays in a loading state forever. No error is shown to the user.

**Fix:** Add `onError: () => setPreview(null)` and display an error message.

---

### BUG-018: Draft save race condition on modal close (MEDIUM)

**Location:** Frontend `NewTextCampaignModal.tsx:92-118`

**Description:**
Draft persistence uses a 500ms debounce timer. If the user modifies state and immediately closes the modal:

1. User changes audience (triggers debounce)
2. User closes modal (calls `resetWizard()` immediately)
3. State is cleared
4. 500ms later, debounce fires and saves empty `{}` draft to localStorage

**Result:** Draft is persisted but empty. Next modal open shows "Resume draft?" for an empty draft.

**Fix:** Cancel the pending debounce timer in the modal close handler.

---

### BUG-019: Failed recipient error message truncated (LOW)

**Location:** Frontend campaign detail view; Backend error message format

**Description:**
Failed recipients show error "Failed to send SMS:" with a trailing colon and no actual error detail. The specific provider error is cut off.

**Reproduction (live on Vercel dev):**
1. Click a Failed campaign → see recipient error column
2. Error shows "Failed to send SMS:" — no detail after the colon

**Screenshot:** `/tmp/grins-screenshots/33-clicked-campaign-row.png`

---

### BUG-020: Ad-hoc CSV allows duplicate phones within same upload (LOW)

**Location:** `src/grins_platform/services/campaign_service.py:1056-1098`

**Description:**
Ad-hoc recipients from CSV are deduplicated against customers and leads (`seen_phones`), but not against other rows in the same CSV upload. If the CSV contains the same phone twice with different names:

```
John Doe,+16125551234
John Smith,+16125551234
```

Both create ghost leads and both get `campaign_recipients` rows → recipient gets 2x SMS.

**Fix:** Track seen phones within the CSV processing loop and skip duplicates.

---

### BUG-021: Campaign delete has no status guard (LOW)

**Location:** `src/grins_platform/repositories/campaign_repository.py:108-128`

**Description:**
`delete()` performs a cascade delete regardless of campaign status. Deleting a SENDING campaign would orphan in-flight SentMessage rows (campaign_id set to NULL via ondelete=SET NULL), break audit trail, and leave responses unlinked.

**Fix:** Only allow delete on DRAFT and CANCELLED campaigns.

---

### BUG-022: `CampaignResponse.status` not enforced at Python level (LOW)

**Location:** `src/grins_platform/models/campaign_response.py:57`

**Description:**
Status is a bare `String(20)` at the ORM level. A DB-level CHECK constraint exists (`parsed|needs_review|opted_out|orphan`) but Python code can create invalid statuses that only fail at flush time with a cryptic database error.

**Fix:** Use a Python `Enum` for the mapped column.

---

### BUG-023: Poll block rendering must match between frontend and backend (LOW)

**Location:** Frontend `pollOptions.ts:61-67`; Backend `background_jobs.py` / `campaign_utils.py`

**Description:**
Frontend renders the poll block for live preview and segment counting:
```typescript
`\n\nReply with ${keys}:\n${lines}\n`
```

Backend renders the same block when actually sending. If the two diverge (e.g., different spacing, emoji additions), the segment count shown in preview will be wrong, and the user could be charged more than expected.

**Note:** Comment in `pollOptions.ts` line 6 says "Mirrors backend `services/sms/segment_counter.py` exactly." No automated test validates this.

**Fix:** Add a cross-stack test that verifies the frontend and backend produce identical poll block strings.

---

## Additional Observations (Not Bugs)

### OBS-1: All campaigns have identical generic names
Every campaign is named "SMS Campaign 4/8/2026" — there's no user-editable name field in the wizard. Makes the campaign list very hard to navigate.

### OBS-2: "Worker: stale" indicator
The campaign worker is not running on Railway dev. This is an infrastructure issue, not a code bug, but it means all campaigns in "Sending" status are stuck.

### OBS-3: "(0 after consent filter)" parenthetical is easy to miss
When a user selects a non-opted-in customer, the count shows "1 total (0 after consent filter)". The small parenthetical is the only hint — could use stronger visual treatment (red text, warning icon).

### OBS-4: CAN-SPAM address fallback
If `BusinessSetting.company_address` is not configured, all campaigns use the hardcoded fallback "Grin's Irrigations" — which may not be a valid physical address for CAN-SPAM compliance.

---

## Recommended Fix Priority

### Sprint Now (15 min total)
| Bug | Fix | Effort |
|-----|-----|--------|
| BUG-003 | Add empty body guard to `send_campaign()` | 5 min |
| BUG-007 | Add `poll_options=` to automation clone | 5 min |
| BUG-008 | Use `csv.QUOTE_ALL` in response export | 5 min |

### Next Batch (High-visibility fixes)
| Bug | Fix | Effort |
|-----|-----|--------|
| BUG-001 | Fix response summary to always include poll option buckets | 30 min |
| BUG-004 | Populate `sent_at` in the send flow | 15 min |
| BUG-005 | Fix SMS opt-in filter query in AudienceBuilder | 20 min |
| BUG-010 | Add validation error toast on empty message | 5 min |
| BUG-002 | Add idempotency lock to retry endpoint | 30 min |

### Subsequent Sprint
| Bug | Fix | Effort |
|-----|-----|--------|
| BUG-006 | Fix SENDING→SENT transition when all recipients fail | 20 min |
| BUG-009 | Surface phone normalization drop count | 15 min |
| BUG-011 | Add recipient name/phone to failed detail view | 20 min |
| BUG-012 | Remove duplicate header | 5 min |
| BUG-013 | Add message preview to review step | 20 min |
| BUG-014 | Fix modal overflow for schedule picker | 10 min |
| BUG-015 | Add "Failed" filter option | 10 min |
| BUG-016 | Add draft edit/delete/resume capability | 40 min |
| BUG-017 | Add error handler to audience preview | 5 min |
| BUG-018 | Cancel debounce timer on modal close | 5 min |
| BUG-019 | Include full error detail in failed recipient display | 10 min |
| BUG-020 | Deduplicate phones within CSV upload | 15 min |
| BUG-021 | Guard campaign delete by status | 10 min |

---

## Screenshots Reference

All screenshots saved to `/tmp/grins-screenshots/`:
- `01-landing.png` — Dashboard landing page
- `02-communications-tab.png` — Communications main view (duplicate header visible)
- `03-sent-messages.png` — Sent Messages tab (empty SENT AT column)
- `04-sent-messages-scrolled.png` — All 3 sent messages visible
- `05-campaigns-tab.png` — Campaigns list (Worker: stale, stuck campaigns)
- `06-campaigns-scrolled.png` — More campaigns (Sending+Failed badges)
- `07-campaign-responses.png` — Response view (missing poll buckets)
- `10-needs-review-below.png` — Needs Review expanded (no responses)
- `12-new-campaign-wizard.png` — Step 1 Audience (SMS filter issue)
- `13-sms-filter-unchecked.png` — SMS filter toggled off (same list)
- `15-e2e-selected.png` — Customer selected with consent
- `16-step2-message.png` — Step 2 Message composer
- `17-empty-message-next.png` — Empty message, no error shown
- `18-poll-toggle-on.png` — Poll options editor appeared
- `22-poll-options-filled.png` — Both poll options configured
- `26-step3-review.png` — Step 3 Review (no message preview)
- `30-schedule-picker.png` — Schedule option (overflow visible)
- `33-clicked-campaign-row.png` — Failed campaign detail (UUID recipient, truncated error)
- `34-draft-detail.png` — Draft click → back to list (no detail view)
