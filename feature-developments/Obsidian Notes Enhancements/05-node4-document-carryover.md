# 05 — NODE 4: documents carry over from lead → customer on conversion

**Request (paraphrased):**
> When the last node in the sales tab auto-creates the customer and deletes the lead, the contract, estimate, and any other uploaded documents must auto-transfer to that customer so they're visible on the customer tab.

**Status:** ❌ NOT IMPLEMENTED for generic lead attachments · 🟡 SIGNED contracts already land in `CustomerDocument` via the SignWell webhook

---

## What exists today

- `LeadAttachment` model (`models/lead_attachment.py:30`) — documents attached to a **lead**.
- `CustomerDocument` model (`models/customer_document.py:34`) — documents attached to a **customer** (optionally scoped to a `sales_entry_id`).
- `SignWell` webhook (`api/v1/signwell_webhooks.py:167-176`): on signature, signed PDF goes **directly** into `CustomerDocument` (not `LeadAttachment`). This is a bypass path — it works, but only for the one signed document.
- `LeadService.convert_lead()` (`services/lead_service.py:938-1087`) has **no** document-transfer logic. Anything uploaded to the lead stays on the lead and is invisible on the customer detail page.

## What this means in practice

- If you upload an estimate PDF, site photos, or notes to the lead in the sales pipeline, on conversion they are orphaned.
- Only the SignWell-signed contract shows up on the customer — because SignWell wrote it straight to `CustomerDocument`, skipping the lead entirely.

## TODOs

- [ ] **TODO-05a** In `convert_lead()`, after creating the customer, migrate every `LeadAttachment` for the source lead into `CustomerDocument` (re-pointing foreign keys; preserve upload timestamp and uploader).
- [ ] **TODO-05b** Decide: do we also delete the `LeadAttachment` rows or keep them for audit? Recommend keeping them with a reference to the new `CustomerDocument.id`. ❓
- [ ] **TODO-05c** Confirm where in-app estimate PDFs are stored today — `LeadAttachment` or `CustomerDocument` or elsewhere. If they land on the lead, they'll be covered by TODO-05a. If they land on `SalesEntry`, a separate transfer pass is needed. ❓
- [ ] **TODO-05d** Add an integration test: upload 2 lead attachments, run `convert_lead()`, assert both appear on the customer's document list.

## Clarification questions ❓

1. **Source of truth after conversion:** do you want the lead's uploads moved (i.e. removed from lead), copied (exist on both), or just re-linked (lead keeps reference, customer is the canonical owner)?
2. **Which document types qualify?** Estimate, contract, inspection photos, notes, signed waivers — confirm scope so nothing is missed.
3. **Reverse flow:** if a lead-to-customer conversion is undone (does that even exist in the UI?), what should happen to the migrated documents?
