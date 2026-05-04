# Appointment Modal Combined — Payment + Estimate + Pricelist Audit

**Date**: 2026-05-01
**Scope**: Implementation status of `feature-developments/design_handoff_appointment_modal_combined 2/` against production code, plus admin-editable pricelist requirement.
**Type**: Read-only audit — no code changed.
**Trigger**: Confirm what is wired, what is missing, and what blocks "everything connected" between FE and BE for the on-site workflow.

---

## TL;DR

| Component | Status | Headline |
|---|---|---|
| Combined modal shell | ✅ ~95% | All 10 sections built; minor cosmetic gaps |
| Tag editor + customer-scoped tags | ✅ done | Backend + UI wired via `PUT /customers/{id}/tags` |
| Maps picker popover | ✅ done | Missing only the "Remember my choice" footer row |
| Payment collection | 🟡 mostly | Architecture C live; gaps in timeline visibility + receipts |
| Estimate flow | 🟡 70% | **Critical gap: auto-job-on-approval is missing entirely** |
| Admin-editable price list | ❌ FE missing | Backend ready, no frontend editor exists |

The big-ticket items still outstanding are: **(1)** auto-job-on-approval for estimates, **(2)** the admin price-list UI, **(3)** wiring estimate/payment line items to that price-list as the single source of truth.

---

## 1. Combined Appointment Modal — ~95% complete

All ten sections of the design spec are built under `frontend/src/features/schedule/components/AppointmentModal/`.

| Section | Status | File |
|---|---|---|
| Header (status + pills + H1 + date) | ✅ | `ModalHeader.tsx` |
| Timeline strip (4 dots) | ✅ | `TimelineStrip.tsx` |
| Action track (linear 3-card) | ✅ | `ActionTrack.tsx` / `ActionCard.tsx` |
| Secondary actions (incl. Edit tags) | ✅ | `SecondaryActionsStrip.tsx` (lines 42–86). AI draft button removed per spec. |
| Payment + Estimate CTAs | 🟡 | `AppointmentModal.tsx:598,606` — labeled "Create Estimate" instead of spec's "Send estimate" |
| Customer hero (incl. Tags row) | ✅ | `CustomerHero.tsx` (lines 31–98) |
| Property card + Get directions | ✅ | `PropertyDirectionsCard.tsx` + `MapsPickerPopover.tsx` |
| Scope + materials | ✅ | `ScopeMaterialsCard.tsx` |
| Assigned tech + Reassign | ✅ | `AssignedTechCard.tsx` |
| Footer (Edit / No show / Cancel) | ✅ | `ModalFooter.tsx` |

**Tag editor sheet** (`TagEditorSheet.tsx:115–201`) — built. Saves via `PUT /customers/{customer_id}/tags` (spec said PATCH; functionally equivalent). Backend has `Customer.tags` relation (`models/customer.py:243–248`) and a dedicated `CustomerTag` model with tones (neutral/blue/green/amber/violet) per `schemas/customer_tag.py:15–20`.

**Maps picker popover** (`MapsPickerPopover.tsx:55–106`) — Apple/Google rows present.

**Cosmetic-only gaps**:
- Estimate CTA labeled "Create Estimate" (spec says "Send estimate")
- Action card sublabels are "En route / On site / Done" (spec says "On my way / Job started / Job complete")
- `MapsPickerPopover` lacks the "Remember my choice" footer row + the `user.preferred_maps_app` persistence

These are 1-hour polish tickets, not blockers.

---

## 2. Payment Flow — Architecture C live, two visibility gaps

### Wired and working

- `PaymentCollector.tsx` (lines 1–415) — two paths: **Send Payment Link** (Architecture C) and **Manual record** (cash/check/Venmo/Zelle/send_invoice)
- Backend endpoint `POST /api/v1/appointments/{id}/collect-payment` → `AppointmentService.collect_payment()`
- `StripePaymentLinkService.create_for_invoice()` (`services/stripe_payment_link_service.py:57–129`) generates link, persisted to invoice
- `/api/v1/invoices/{id}/send-link` delivers via SMS + email (Resend fallback)
- Webhook `payment_intent.succeeded` flips invoice→PAID, sets `Job.payment_collected_on_site=true`, idempotent on event ID
- Tap-to-Pay (`stripe_terminal.py`) is **deprecated/shelved** — header comment says "New code MUST NOT import this module"

### Outstanding gaps

| # | Gap | Impact |
|---|---|---|
| 🔴 | Cash/check payments **not visible on the appointment timeline**. `appointment_timeline_service.py` aggregates SentMessage/JobConfirmationResponse/RescheduleRequest/SmsConsentRecord but does **not** join the `invoices` table | Staff can't see "Paid $X by check on-site" without drilling into Invoices tab |
| 🔴 | **No receipt SMS/email** after a payment is collected. Stripe shows its hosted confirmation, but nothing custom from Grin's | Customer gets no receipt for cash/check at all |
| 🟡 | **No "Paid — $NNN · $method" confirmation card** in the modal post-success — design §8.5 calls for the payment CTA to collapse into a green confirmation block | UX polish |
| 🟡 | Tap-to-Pay code retained as placeholder; should be deleted now that Architecture C is GA | Cleanup |

### Visual reference

- `audit-screenshots/missing-states/payment-01-start-line-items.png` — design's agreement-aware start sheet (production jumps to method choice with no concept of covered-vs-extra)
- `audit-screenshots/missing-states/payment-02-method-picker.png` — design's clean 4-tile picker (Tap to Pay / Cash / Check / Send invoice). Production has a different two-path layout. **Note**: the design's "Tap to Pay" tile is now obsolete — Architecture C means that tile should be replaced with **"Send Payment Link · text customer"**.
- `audit-screenshots/missing-states/payment-04-paid-confirmation.png` — design's "Payment received" green confirmation card with inline receipt + "Text receipt" CTA. Production fires only a toast.

---

## 3. Estimate Flow — 70% with one critical hole

### Wired

- Backend: `EstimateService` covers create / send / approve / reject + Day 3/7/14/21 follow-up scheduler + lead-tag updates
- API: `/api/v1/estimates` (CRUD) and `/api/v1/portal/estimates/{token}` (customer-facing)
- Customer-facing portal: `frontend/src/pages/portal/EstimateReview.tsx` + `ApprovalConfirmation.tsx` — token-authenticated, IP/UA tracked, one-click approve/reject with optional reason
- SMS + email delivery via Resend + SMS factory
- Decline flow

### ❌ The critical gap — auto-job-on-approval

- `estimate.job_id` FK exists (`models/estimate.py:52–55`) but is **never populated**
- `EstimateService.approve_via_portal()` records approval, cancels follow-ups, updates lead tag — but **never calls `JobService.create_job()`**
- No `target_start_date` / `target_end_date` field on the Estimate model — there's no week to schedule the job for even if you wanted to create one

Per Obsidian note 07 this was already flagged as missing. It's still missing.

The design literally has a **`Schedule follow-up`** primary CTA on the approved-state confirmation card (`audit-screenshots/missing-states/estimate-07-approved.png`) and a panel reading *"NEXT STEP: Create a follow-up job for the approved work. Pricing and line items carry over automatically."* — this CTA + handler is what's missing.

### Other estimate gaps

- Frontend `EstimateCreator.tsx` is a backend-style form, **not the sheet flow E1→E8** from the design spec
- Missing UI: SMS/Email delivery toggle, SMS preview step, "awaiting reply" status banner on return to modal
- Line-item catalog uses `EstimateTemplate` (full pre-baked estimates), not a per-line-item picker pulling from `ServiceOffering` (which is what the design's `ES_CATALOG` hardcoded items represent)

### Per-state status

| Design state | Status | Notes |
|---|---|---|
| E1_Start | ❌ | No violet sheet header / identity card / `LINE ITEMS` caps section |
| E2_Picker | 🟡 | Template selector exists; per-line picker w/ search not built. Should pull from `ServiceOffering`. |
| E3_Ready | ❌ | No SMS/Email toggle UI |
| E4_Preview | ❌ | No preview step before send |
| E5_Waiting | ❌ | No persistent "Estimate sent · awaiting reply" card; no Resend button |
| E6_CustomerSMS | ✅ | Customer SMS body + portal link wired |
| E7_Approved | 🟡 | Confirmation page exists; **`Schedule follow-up` CTA + auto-job missing** |
| E8_Declined | ✅ | Confirmation page exists |

### Visual reference

- `audit-screenshots/missing-states/estimate-01-empty-start.png` through `estimate-08-declined.png`

---

## 4. Admin-Editable Price List — backend ready, frontend missing

Per Obsidian note `09-admin-editable-pricelist.md`. User intent (paraphrased): *"the invoices tab should have a section where we modify the price list, and that price list is used by technicians on the field to make estimates."*

### 📂 Source-of-truth seed data

Viktor's actual price list (PDF: `Grins_Price_List (VIKTOR NOTES).docx.pdf`, effective Feb 2026, MN) has been extracted into a structured seed file:

- **Location**: `bughunt/2026-05-01-pricelist-seed-data.json`
- **Status**: DRAFT — pending Viktor confirmation on flagged source typos before seeding
- **Contents**: 73 line items across 7 subcategories (irrigation install / maintenance / service fees, landscaping install / edging / mulch & rock / tree & debris removal), each split residential ↔ commercial. Includes verbatim `source_text` per item for audit-back-to-PDF.
- **Source typos flagged inline**: `linear food` → foot (pipe leak), `Per diameter Inter` → Inch (stump grinding), duplicated `plant plant` (residential shrub), ambiguous mulch unit on commercial shredded hardwood, missing commercial backflow price, inconsistent straw blanket roll units, missing `per zone` on commercial drip.
- **Pricing-model coverage**: 14 distinct pricing shapes (per_zone_range, tiered_zone_step, tiered_linear, compound_per_unit, size_tier, yard_tier, variants, conditional_fee, flat_plus_materials, etc.) — most do NOT fit the existing `ServiceOffering.pricing_model` enum (`flat`/`zone_based`/`hourly`/`custom`). Migration will need to extend the enum or move pricing to a JSONB rule column. Compatibility notes are in the file's `metadata.compatibility_notes_for_existing_service_offering_model`.
- **Glossary**: `metadata.pricing_model_glossary` defines each pricing model used.

Before this seed is used to populate `ServiceOffering`, Viktor needs to confirm the flagged typos and the missing commercial-backflow price.

### ✅ Backend is ready

- `ServiceOffering` model (`models/service_offering.py:23–166`) — `base_price`, `price_per_zone`, `pricing_model` (flat / zone_based / hourly / custom), `category`, `is_active`, plus equipment/staffing/duration metadata
- Full CRUD API at `/api/v1/services` (`api/v1/services.py:34–337`):
  - `GET /api/v1/services` (list with filters, pagination)
  - `GET /api/v1/services/{id}` (get by ID)
  - `POST /api/v1/services` (create)
  - `PUT /api/v1/services/{id}` (update)
  - `DELETE /api/v1/services/{id}` (soft delete / deactivate)
  - `GET /api/v1/services/category/{category}`

### ❌ Frontend doesn't exist

- No `PriceList.tsx` / `ServiceCatalog.tsx` anywhere under `frontend/src/pages/` or `frontend/src/features/`
- Settings page (`frontend/src/pages/Settings.tsx:1–373`) hosts BusinessInfo, InvoiceDefaults, EstimateDefaults, NotificationPrefs, BusinessSettingsPanel — **no price-list editor**
- Router (`frontend/src/core/router/index.tsx`) has no `/settings/pricelist` (or `/invoices/pricelist`) route
- **Invoices tab does NOT host a price-list editor section** — the integration the user specifically asked about is not there
- No `serviceApi.ts` / `catalogApi.ts` client in the frontend at all

### ❌ Downstream consumers not wired to it

- `EstimateCreator.tsx` pulls from `useEstimateTemplates()`, not from `/api/v1/services`
- `PaymentCollector.tsx` has hardcoded payment methods only — no dynamic quick-picks from active services
- `JobForm.tsx` references `service_offering_id` but doesn't populate a dropdown from the live catalog

### ❌ Audit log not wired

- `ServiceOfferingService.update_service()` / `deactivate_service()` (`services/service_offering_service.py:112–179`) don't call `AuditService.log_action()`
- `AuditService` is wired for sales pipeline, business settings, lead/customer consent — but **not** for service offerings, so price changes are not tracked

### 🟡 `pricelist.md`

- Static markdown doc (148 lines, "Effective February 2026") — manually maintained, disconnected from the database
- Will drift; needs decision (retire / auto-generate)

### 🟡 Open decisions before seeding / wiring

These are unresolved at the close of the 2026-05-01 audit. Three buckets — Viktor data confirmations, engineering data-shape decisions, and product UX decisions. Until each is answered, the seed JSON (`bughunt/2026-05-01-pricelist-seed-data.json`) cannot be promoted to a migration and the pricelist editor UI cannot be designed.

#### Bucket A — Pending Viktor confirmations (source data)

| # | Item | Question | Why it blocks |
|---|---|---|---|
| **V1** 🔴 | `shredded_hardwood_mulch_commercial` | Source reads `$0.75 per 100-150 sq at 2-3 inch depth`. Is the rate `$0.75 per sq ft` (typo, "100-150 sq" was meant to be deleted) or `$0.75 per 100 sq ft` (i.e. `$0.0075/sq ft`)? | 100× swing on every commercial mulch quote. Currently seeded as per-sq-ft pending answer. |
| **V2** 🔴 | `backflow_preventer_replacement_commercial` | Commercial price is missing entirely from the source. Same $600 as residential? Different price? Or is commercial backflow not serviced? | Cannot seed a commercial backflow item without it. |
| **V3** 🟡 | `drip_irrigation_install_commercial` | Source says `$1,500 - $2,500` with no "per zone", but residential drip says "per zone". Was "per zone" omitted by accident? | 10× swing on commercial drip jobs — a 10-zone job is $15K–25K (per zone) vs $1.5K–2.5K (flat). |
| **V4** 🟡 | `straw_blanket_commercial` | Source self-contradicts: dimensions `8'×12'` = 96 sq ft, but stated coverage is "~900 sq ft". Which is right? | Per-roll pricing works either way ($200/roll). Breaks the "how many rolls do I need for X sq ft" calc. |
| **V5** ⚪ | Cosmetic typos | `linear food` → foot (pipe leak); `Per diameter Inter` → Inch (stump grinding); `$15 per plant plant` (duplicated word). | Zero ambiguity on intent — seed already has correct structured values. Worth fixing in the source PDF for legibility. |

#### Bucket B — Engineering data-shape decisions

| # | Decision | Options | Recommendation |
|---|---|---|---|
| **E1** | How to extend `ServiceOffering` to fit 14 distinct pricing models | (a) extend `pricing_model` enum + add column-per-model; (b) move to a JSONB `pricing_rule` column with a discriminated union; (c) hybrid — keep `pricing_model` enum as a tag, store the rule body in JSONB | (b) or (c). Seed has `per_zone_range`, `tiered_zone_step`, `tiered_linear`, `compound_per_unit`, `size_tier`, `yard_tier`, `variants`, `conditional_fee`, `flat_plus_materials` — column-per-model would balloon the schema. |
| **E2** | Materials pass-through model | (a) bool `includes_materials` + free-text `materials_pass_through` description; (b) separate `material_cost` decimal that the tech fills in at quote time; (c) distinct line-item types (labor vs material, both seeded) | (b) or (c). Seed says `tree_at_cost` / `mulch_at_cost` etc.; the actual dollar amount must come from somewhere at quote time. |
| **E3** | Customer-type partitioning | (a) add `customer_type` column to `ServiceOffering`, store res/com as distinct rows; (b) add `pricing_by_customer_type` JSONB on one row; (c) use category/tag to filter | (a) — matches the seed file's structure (73 rows = res/com pairs as distinct entries with distinct keys). Simpler queries, simpler admin UI. |
| **E4** | Audit logging on price changes | Whether to wire `AuditService.log_action()` into `ServiceOfferingService.create/update/deactivate` | Yes — pricelist is sensitive shared state; matches the `business_setting` pattern that already audits. Listed as TODO-09d in Obsidian note 09. |
| **E5** | Stable identifier strategy | Keep human-readable string keys (`spring_startup_residential`) as a `slug` column? Use UUID? Both? | Both — UUID for FK integrity, slug for tech-facing references and migration idempotency. The seed file's `key` field is the slug. |
| **E6** | Range pricing storage | For `per_zone_range`/`per_unit_range`/`flat_range`: store min + max as two columns or single JSONB? | Tied to E1 — collapses into the same field if E1 lands on JSONB. |
| **E7** | Estimate template vs ServiceOffering relationship | Seed replaces `EstimateTemplate` use in `EstimateCreator`. Do templates go away, or remain as bundles ("Spring Package = Spring Start-Up + WiFi Upgrade")? | Keep `EstimateTemplate` as bundle of `ServiceOffering` references. Templates are useful; just shouldn't be the only catalog. |

#### Bucket C — Product UX decisions

| # | Decision | Question | Notes |
|---|---|---|---|
| **P1** | Range pricing at quote time | When a service has a price range (e.g. $800–$1000/zone), does the tech (a) pick a single point inside the range, (b) submit the whole range to the customer, or (c) the system auto-picks based on `profile_factor` (flat-dirt vs hilly)? | (c) requires a property-profile field on `Property` (or per-job). Most ergonomic but most migration work. |
| **P2** | Tier selection in the line-item picker | For `size_tier` (Tree Drop S/M/L) and `yard_tier` (Delivery 0–3 yd / 4–6 yd) — does the picker show one row with a size dropdown, or three flat rows? | One-row + dropdown matches design intent; three-rows ships faster. |
| **P3** | Variants in the picker | `valve_repair_replacement_*` has 3 variants (single box / multi box / additional). Same question — collapsed row with sub-picker, or 3 distinct rows? | Same trade-off as P2. Recommend consistent treatment. |
| **P4** | Customer-type defaulting | Does the appointment modal know whether the customer is residential or commercial, so the picker pre-filters? Or does the tech pick "Residential / Commercial" as a top-level toggle? | `Customer.customer_type` already exists in the model — recommend using it to pre-filter, with a manual toggle override for edge cases. |
| **P5** | Materials cost capture UX | When a `flat_plus_materials` line is added, where does the tech enter the material cost — inline on the estimate row, in a separate "materials" sub-form, or pulled from a vendor catalog? | For Phase 1, inline material-cost field is the minimum. Vendor-cost catalog is a separate concern. |
| **P6** | Range vs fixed at the customer level | Customer-facing estimates — show "$800–$1000 per zone" or always a single number? | Industry norm is single number on customer estimates; range is staff-internal. |
| **P7** | Markup/discount layer | Do techs apply % markup or discount on top of seeded prices, or are seeded prices terminal? | Affects whether we need a `quote_adjustment` model. Not in scope for Phase 1 unless Viktor says otherwise. |
| **P8** | `pricelist.md` resolution | Retire the static markdown, auto-generate from DB on each save, or keep it manual as a fallback? | Auto-generate is cleanest — staff get a printable view, doc never drifts. |
| **P9** | Price-list editor location | User said: *"the invoices tab should have a section where we modify the price list"* — confirm whether that's a sub-tab inside `/invoices`, a new top-level `/pricelist`, or under `/settings`. | User intent is clear (Invoices tab). Confirm before building. |
| **P10** | Above-max behavior | Spring Start-Up tops out at 19 zones; Tree Drop at 50 ft; Delivery at 6 yards. What happens above max — fall back to "custom quote", linear-extrapolate, or prompt the tech? | Recommend "custom quote" prompt — matches Viktor's intent of guard-rails, not hard limits. |
| **P11** | Conditional-fee mechanics | Service Call Fee ($100/$125, waived if completed work covers it) and Consultation Fee (credited toward project if approved) — does the system auto-credit on the invoice, or does the tech apply manually? | Auto-credit is the goal but requires linking the fee invoice to the resulting work-order invoice. Manual is the Phase 1 fallback. |
| **P12** | Emergency Service Fee application | Is the +$150/$200 surcharge applied automatically based on appointment timestamp (after-hours/weekend/holiday) or manually toggled by the tech? | Auto-apply needs a holiday calendar + business-hours config. Manual toggle is the Phase 1 fallback. |

#### Sequencing recommendation

1. **First** — get answers to V1, V2, V3 (V4 nice-to-have, V5 cosmetic).
2. **Then** — decide E1, E2, E3 before writing the migration. These shape the schema.
3. **Then** — promote `bughunt/2026-05-01-pricelist-seed-data.json` to an Alembic migration that creates the `ServiceOffering` rows.
4. **Then** — design the editor UI (P9 first to confirm location, then P1–P8 / P10–P12 as the editor + estimate-picker design progress).

The seed file is the single artifact that surfaces all 23 of these decisions. Any decision deferred shows up later as a flagged item in the JSON or a missing field on the migration.

---

## 5. Concrete outstanding work, prioritized

### P0 — functional gaps that block the workflow

1. **Auto-job-on-approval** — wire `EstimateService.approve_via_portal()` to call `JobService.create_job(...)` with line items as scope; set `estimate.job_id = job.id`. Add `target_start_date` / `target_end_date` columns to `Estimate` so the job knows when to land. Add a `Schedule follow-up` button on the approved-state staff confirmation card per design §8.6.
2. **Admin price-list editor** — build `frontend/src/pages/Settings/PriceList.tsx` (or under Invoices tab per user preference) with table + inline CRUD against `/api/v1/services`. Add a route + nav entry. Add `frontend/src/features/.../api/serviceApi.ts` client.
3. **Wire estimate creator's catalog to `ServiceOffering`** — replace template-only picker with a per-line-item search/picker reading `/api/v1/services`. This is the consumer side of #2.

### P1 — visibility / UX polish

4. Surface payment events in `appointment_timeline_service.py` so cash/check/Stripe payments show up in the modal's communication history.
5. Wire a receipt SMS/email after `collect-payment` succeeds (manual + Stripe).
6. Add the "Paid — $NNN · $method" confirmation card in the modal (PaymentCollector → AppointmentModal handoff).
7. Add audit logging in `ServiceOfferingService` create/update/deactivate.

### P2 — design polish

8. Estimate sheet visual rebuild to match E1→E8 states (delivery toggle, preview, awaiting-reply banner, Resend button).
9. Modal CTA labels: "Send estimate" + action card sublabels match spec strings.
10. Maps popover: add "Remember my choice" footer + persist `user.preferred_maps_app`.
11. Decide on `pricelist.md` — retire or auto-generate from DB.
12. Delete deprecated `stripe_terminal.py` code if Tap-to-Pay isn't returning.

---

## 6. Visual reference

All design-state screenshots saved at:
```
/Users/kirillrakitin/Grins_irrigation_platform/audit-screenshots/missing-states/
├── payment-01-start-line-items.png
├── payment-02-method-picker.png
├── payment-04-paid-confirmation.png
├── estimate-01-empty-start.png
├── estimate-02-line-item-picker.png             ← consumer for the price list (#2)
├── estimate-03-review-with-sms-email-toggle.png
├── estimate-04-sms-preview.png
├── estimate-05-sent-waiting.png
├── estimate-06-customer-phone-view.png          ← reference (largely live)
├── estimate-07-approved.png                     ← `Schedule follow-up` = auto-job hook (#1)
└── estimate-08-declined.png
```

Captured by rendering `feature-developments/design_handoff_appointment_modal_combined 2/source/Appointment Modal Combined.html` via local HTTP server, isolating each `[data-dc-slot="..."]` artboard, full-page screenshot via headless browser.

---

## 7. Existing flow documentation in the repo

There is **no single end-to-end document** covering the full appointment → payment → estimate → auto-job → invoice → pricelist flow. The truth is split across **five buckets** described below.

### A. Obsidian Notes — investigation/audit (status, not spec)

`feature-developments/Obsidian Notes Enhancements/`

These are status notes (audited 2026-04-23) mapping 13 feature requests to current implementation state. They are diagnostic, not prescriptive — they tell you what's missing, not how to wire it.

| Document | Coverage | Status verdict (per note) |
|---|---|---|
| `00-investigation-summary.md` | Master scorecard for all 13 features; roadmap of TODOs grouped by priority tier | 6 PARTIAL, 5 NOT IMPLEMENTED, 2 IMPLEMENTED |
| `01-customer-tags-to-jobs.md` | Tags propagation customer→job | (covered) |
| `02-job-full-editability.md` | Job edit affordances | (covered) |
| `03-staff-auth-and-session.md` | Auth + session | (covered) |
| `04-lead-to-customer-lifecycle.md` | Lead→customer conversion | (covered) |
| `05-node4-document-carryover.md` | Document carryover at Node 4 | (covered) |
| `06-onsite-payment-collection.md` | Appointment modal → cash/check/Stripe Terminal on-site recording | 🟡 PARTIAL — button + `Job.payment_collected_on_site` flag exists; amount+method+receipt flow unclear |
| `07-estimate-button-autojob.md` | **[CRITICAL]** Estimate button → SMS Yes/No → **auto-create Job** | 🟡 PARTIAL — Estimate creator + SMS/email exist; auto-job-on-approval path not found |
| `08-invoices-source-of-truth.md` | Invoices tab w/ filters, reminders, 3% Stripe fee, 2-week due default | 🟡 PARTIAL — page + filters exist; scheduled reminders + surcharge logic missing |
| `09-admin-editable-pricelist.md` | Admin UI for ServiceOffering CRUD | ❌ NOT IMPLEMENTED — API exists, no UI |
| `10-schedule-multi-staff-overlay.md` | Schedule overlay | (covered) |
| `11-next-customer-eta-notify.md` | Next-customer ETA | (covered) |
| `12-directions-maps-toggle.md` | Apple/Google maps toggle | (covered — see Maps picker in §1) |
| `99-clarification-questions.md` | Open questions for PM | (covered) |
| `SPEC.md` / `CHECKLIST.md` / `README.md` | Investigation framing |  |

**Key quote from 07** (the auto-job gap): *"No code path was found that consumes the approval event and inserts into the Jobs table."*

**Key quote from 08** (TODO-08e): *"Confirm every on-site collect-payment flow (#06) also writes an `Invoice` row so the invoices tab truly is the source of truth."*

### B. Design handoffs — visual + behavior spec (intended UI, no backend wiring)

`feature-developments/`

- `design_handoff_appointment_modal_combined 2/README.md` — **the spec for the modal audited above**. Covers Collect Payment + Send Estimate buttons, customer-tags edit sheet, Apple/Google Maps picker, status timeline track, on-site action workflow, footer. References auto-job at §8.6: *"Send estimate → Estimate sheet. On send, post the estimate to the backend; track its state so returning to the appointment shows the most recent estimate status banner."* The actual auto-job mechanics are not specified — only the resulting status banner is implied.
- `design_handoff_appointment_modal_v2/` — earlier version of the same modal
- `design_handoff_appointment_modal_combined/` — predecessor (vs. "combined 2")
- `Schedule-Estimate-Visit-Reference.html` — visual reference for calendar → estimate-visit booking
- `Sales-Estimates-Schedule-Modal.zip`, `Sales_Estimate_Schedule_high_fidelity.zip`, `Schedule_estimate_combo.zip`, `Tech_Companion_Flow.zip` — design archives
- `design_handoff_tech_companion_flow/` — new untracked tech-companion designs

**Architectural note**: design copy explicitly calls for estimate approval → auto-job flow (the `Schedule follow-up` CTA on the Approved state — see `audit-screenshots/missing-states/estimate-07-approved.png`) but does not show the implementation path.

### C. Sales pipeline / stage walkthrough — behavior specs

`feature-developments/handoff-stage-walkthrough-and-pipeline/`

| Document | Coverage |
|---|---|
| `SPEC-stage-walkthrough.md` | 7-stage sales pipeline (Plan → Sign → Close) with Now-card content per stage. **Stage 4 (`send_contract`) has a "Week Of" picker for job target week** — closest existing precedent for the missing target-week field on the Estimate model. Shows the conceptual flow but doesn't detail auto-job mechanics. |
| `README.md` (in `schedule-estimate-visit-handoff/`) | Modal for picking estimate-visit time from sales pipeline detail screen; syncs form fields ↔ week calendar. Advances entry from `schedule_estimate` → `estimate_scheduled` on confirm. |
| `SPEC.md` (in `schedule-estimate-visit-handoff/`) | Calendar interaction spec: 6 AM – 8 PM slots, conflict detection, keyboard/mobile, edge cases. **Server contract at §4 shows existing `/api/v1/sales/calendar/events` endpoint auto-advances pipeline status.** |

### D. Implementation plans — scoped feature plans

`.agents/plans/`

| Plan | Scope |
|---|---|
| `schedule-estimate-visit-handoff.md` (40 KB) | Most detailed plan; for the scheduling modal that opens estimate-visit slots from sales pipeline. Verified fact: `POST /api/v1/sales/calendar/events` auto-advances `schedule_estimate → estimate_scheduled` (lines 583–599 of plan). |
| `appointment-modal-secondary-actions.md` | Add photo / Notes / Review wiring |
| `appointment-detail-communication-timeline.md` | Appointment timeline aggregation — **this is the file to extend for the payment-event visibility gap (P1 #4 above)** |
| `enforce-appointment-state-machine.md` | Appointment status transitions |
| `estimate-approval-email-portal.md` | Resend wiring + token portal (matches `design.md` + `build-plan.md` in feature-developments) |
| `schedule-visit-modal-full-redesign.md` / `schedule-visit-modal-ui-refresh-high-fidelity.md` | Earlier visit-modal variants |
| `tech-companion-mobile-schedule.md` | New (untracked) plan for the tech-mobile feature |
| `stripe-payment-links-e2e-bug-resolution.md` | Architecture C bug bundle (matches `bughunt/2026-04-28-stripe-payment-links-e2e-bugs.md`) |

**Each plan is scoped to a single slice — none covers the full appointment → payment → estimate → auto-job → invoice chain.**

### E. Feature-development working folders

`feature-developments/`

| Folder | Notable contents |
|---|---|
| `estimate approval email portal/` | `design.md` — portal token model (UUID v4 bearer), Resend email vendor, internal notification on approve/reject; covers portal approval → lead tag flipped to `ESTIMATE_APPROVED`. **Does NOT detail job auto-creation.** `build-plan.md` — 5 phases: (1) wire Resend, (2) template + send method, (3) wire into EstimateService, (4) optional polish, (5) prod cutover. **Zero mention of job creation from approval.** Plus `vendor-decision.md`, `current-state.md`, `open-questions.md`. |
| `email and signing stack/` | Vendor selection + integration architecture for Resend + SignWell |
| `schedule-estimate-visit-handoff/`, `schedule-estimate-visit-handoff 2/`, `..._high_fidelity/` | Multiple iterations of the same modal spec |
| `handoff-stage-walkthrough-and-pipeline/` | The 7-stage pipeline spec (see bucket C) |
| `claude-code-handoff/` | Onboarding/handoff notes |
| `signing document/` | SignWell document spec |
| `Scheduling/` | Scheduling artifacts |

**The omission across this bucket**: every doc that touches estimate approval (`design.md`, `build-plan.md`, `current-state.md`) covers everything up to "customer approves" and stops short of "create Job."

### F. The under-documented piece: auto-job-on-approval

This is the single most specifically undocumented link in the chain. It appears in three places, none of which specify implementation:

| Source | What it says |
|---|---|
| Design copy (estimate-sheet identity card) | *"Customer approves or declines via SMS"* |
| Design Approved-state mock (`estimate-07-approved.png`) | `Schedule follow-up` primary CTA + panel reading *"NEXT STEP: Create a follow-up job for the approved work. Pricing and line items carry over automatically."* |
| Obsidian note `07-estimate-button-autojob.md` (TODO-07a) | *"Auto-job-on-approval: The design handoff calls for auto-creating a Job on customer Yes. No code path was found that consumes the approval event and inserts into the Jobs table."* |

**What is NOT specified anywhere in the repo**:
- Who calls `JobService.create_job()` — `EstimateService.approve_via_portal()`? a separate listener? a webhook handler?
- What the new Job's `target_start_date` / `target_end_date` should be (the Estimate model has no such field today)
- What status the new Job lands in (`TO_BE_SCHEDULED`? `APPROVED`? something else?)
- Whether the line items carry over as a JSONB field on the Job, attach as JobScopeItems, or seed an Invoice
- Whether an Invoice is created at the same time, or only after the Job is completed
- How the appointment modal's status banner ("Estimate #EST-0142 sent · awaiting reply" → "Estimate approved · job scheduled") gets refreshed
- What happens if the customer approves an estimate for an existing customer who already has a parent Job vs. a fresh one

**Recommendation**: before this work is picked up, write a new plan file `.agents/plans/estimate-approval-auto-job-creation.md` covering the API contract, the Estimate model migration (`target_start_date` / `target_end_date`), the call-site (likely `EstimateService.approve_via_portal()`), the resulting Job status, and how the appointment modal's status banner reconciles.

### Verdict on documentation coverage (per workflow link)

| Workflow link | Documented? | Where |
|---|---|---|
| Calendar appointment chip → modal opens | ✅ | `design_handoff_appointment_modal_combined 2/README.md` |
| Modal → Collect payment sheet | ✅ UI / 🟡 backend wiring | Design spec + Obsidian #06 |
| On-site payment → Invoice row | 🟡 implicit | Obsidian #08 (TODO-08e flags it) |
| Cash/check → appointment timeline | ❌ not specified | (gap — P1 #4 above) |
| Receipt SMS/email after payment | ❌ not specified | (gap — P1 #5 above) |
| Modal → Send estimate sheet | ✅ UI | Design spec |
| Estimate → SMS/email + portal | ✅ | Estimate-approval-email-portal docs |
| Customer YES → **auto-job creation** | ❌ **no spec, no plan** | Obsidian #07 flags it; no plan file describes the API contract |
| Estimate target-week field | 🟡 implied | Obsidian #07 TODO-07a; sales-pipeline `send_contract` has analogous picker |
| Pricelist admin UI | 🟡 partial | Obsidian #09 names file `frontend/src/pages/Settings/PriceList.tsx` |
| Pricelist → estimate line-item picker | 🟡 partial | Obsidian #09 TODO-09b; design source `ES_CATALOG` |
| Pricelist → payment quick-picks | 🟡 partial | Obsidian #09 TODO-09b |
| Audit-log on price changes | ❌ not specified | Obsidian #09 TODO-09d |

### Key load-bearing passages (verbatim)

For future reference, when the docs above drift, anchor on these direct quotes:

- **Obsidian 07** (auto-job gap): *"No code path was found that consumes the approval event and inserts into the Jobs table."*
- **Design handoff README §8.6**: *"Send estimate → Estimate sheet. On send, post the estimate to the backend; track its state so returning to the appointment shows the most recent estimate status banner."*
- **Obsidian 08 TODO-08e**: *"Confirm every on-site collect-payment flow (#06) also writes an `Invoice` row so the invoices tab truly is the source of truth."*
- **Schedule-estimate-visit-handoff plan**: *"POST auto-advances `schedule_estimate` → `estimate_scheduled` (lines 583–599)"*
- **Design handoff §6.5 (CTAs)**: *"Both are always visible (no role / step gating in this modal)."* — confirms Send Estimate is a peer to Collect Payment, not gated.

### What an umbrella spec would need to cover

To replace the five-bucket fragmentation with a single source of truth:

1. **Appointment modal entry** — open from calendar, status machine, action track (referenced ✅)
2. **On-site payment** (Collect Payment button) — Invoice creation, cash/check recording on the timeline, receipt delivery, the "Paid — $NNN · $method" confirmation card
3. **Estimate workflow** (Send Estimate button) — sheet states E1–E8, line-item picker pulling from `ServiceOffering`, SMS/Email toggle, preview step, awaiting-reply banner
4. **Estimate approval → auto-job creation** — the under-documented link in §F above. New plan needed.
5. **Invoice as source of truth** — every on-site collect + estimate + signed agreement creates/references an Invoice row
6. **Pricelist catalog** — admin UI + downstream wiring (estimates, payment quick-picks, invoice templates) + audit-log on changes

The Obsidian audit (`00-investigation-summary.md` + TODO-07a / TODO-08e / TODO-09a) already identifies the exact TODOs needed to wire these connections — they just need a plan that strings them together.

---

## 8. References

- Design spec: `feature-developments/design_handoff_appointment_modal_combined 2/README.md`
- Design source: `feature-developments/design_handoff_appointment_modal_combined 2/source/{combined-modal,payment-sheet,estimate-sheet}.jsx`
- Obsidian notes: `feature-developments/Obsidian Notes Enhancements/{00-investigation-summary,06-onsite-payment-collection,07-estimate-button-autojob,08-invoices-source-of-truth,09-admin-editable-pricelist}.md`
- Estimate portal docs: `feature-developments/estimate approval email portal/{design,build-plan}.md`
- Sales pipeline: `feature-developments/handoff-stage-walkthrough-and-pipeline/SPEC-stage-walkthrough.md`
- Active plans: `.agents/plans/{schedule-estimate-visit-handoff,appointment-modal-secondary-actions,estimate-approval-email-portal,enforce-appointment-state-machine}.md`
- Memory: `project_stripe_payment_links_arch_c.md` (Architecture C is the agreed credit-card path; Tap-to-Pay shelved)
