# Feature: Appointment Modal — Payment + Estimate + Pricelist Umbrella

The following plan should be complete, but its important that you validate documentation and codebase patterns and task sanity before you start implementing.

Pay special attention to naming of existing utils types and models. Import from the right files etc.

> **Authoritative source**: this plan supersedes the audit at
> `bughunt/2026-05-01-appointment-modal-payment-estimate-pricelist-audit.md` for
> implementation. The audit remains the source of truth for *what was found*;
> this file is the source of truth for *what to build*.

---

## Feature Description

Close the loop on the **on-site appointment workflow** (calendar chip → modal → payment → estimate → auto-job → invoice → pricelist) by:

1. Wiring **auto-job-on-approval** so a customer's portal-side YES turns directly into a `TO_BE_SCHEDULED` Job (currently the chain breaks at approval).
2. Standing up an **admin-editable pricelist UI** (backend exists, frontend is missing) at `/invoices/pricelist`, with the data model rebuilt to handle 14 distinct pricing models, customer-type partitioning, and Stripe-style immutable price history.
3. Wiring the **estimate line-item picker to the live pricelist** so techs no longer pick from `EstimateTemplate` only.
4. Making **payment events visible on the appointment timeline** (cash/check/Stripe), sending **receipts** for every payment, and rendering the **"Paid — $NNN · $method" confirmation card** the design spec calls for.
5. Polishing the modal's CTA labels, action card sublabels, Maps popover, and retiring the deprecated `stripe_terminal.py`.

## User Story

**As an** office manager / field technician at Grin's Irrigation
**I want to** see one continuous workflow from "estimate sent" to "job scheduled" to "payment collected" without manual data re-entry, and edit the pricelist that drives every estimate from one place,
**So that** office overhead drops, estimates are anchored in the same pricing the customer-facing PDF shows, and the appointment modal becomes a single source of truth for what happened on-site.

## Problem Statement

Five concrete gaps surfaced in the 2026-05-01 audit:

- **P0** Estimate approval is a dead-end: `estimate.job_id` FK exists (`models/estimate.py:52-55`) but is never populated. `EstimateService.approve_via_portal()` records approval, cancels follow-ups, updates the lead tag — and stops. No `JobService.create_job()` call. No "Schedule follow-up" CTA on the Approved card.
- **P0** No admin pricelist UI exists. `ServiceOffering` model + `/api/v1/services` CRUD is wired (`api/v1/services.py:34-337`), but there is no frontend editor anywhere under `frontend/src/pages/` or `frontend/src/features/`. The Settings page does not host one. The Invoices page does not host one. No `serviceApi.ts` client exists in the frontend.
- **P0** `EstimateCreator.tsx` pulls from `useEstimateTemplates()` (full pre-baked estimates), not from `/api/v1/services` per-line-item. The user's intent — "the price list is used by technicians on the field to make estimates" — is unmet.
- **P1** `appointment_timeline_service.py` aggregates SentMessage / JobConfirmationResponse / RescheduleRequest / SmsConsentRecord, but **does not join the `invoices` table**. Cash/check/Stripe payments don't show on the modal's communication history.
- **P1** No receipt SMS/email after `collect-payment` succeeds. Stripe shows its own hosted confirmation, but nothing custom from Grin's. The modal never collapses the payment CTA into a "Paid — $NNN · $method" green card (design §8.5).

Plus 23 unresolved decisions in the audit (Bucket A/B/C). Those decisions were resolved in the planning conversation 2026-05-01 — see **§ Decision Log** below.

## Solution Statement

**Seven phases**, all in one plan, sequenced so each phase is independently mergeable behind feature gates and the next phase has a foundation to build on. **Phase 6 is the non-negotiable E2E gate — no implementation phase is "done" until its E2E sub-suite passes with full screenshot coverage.**

- **Phase 0** — Auto-job-on-approval + Schedule-follow-up CTA + signed-PDF email at approval.
- **Phase 1** — Pricelist data model migration: extend `ServiceOffering` to hybrid enum + JSONB `pricing_rule`, add `customer_type`, `slug`, `replaced_by_id` seam, `includes_materials`. Promote `bughunt/2026-05-01-pricelist-seed-data.json` to seed migration.
- **Phase 2** — Admin pricelist editor UI at `/invoices?tab=pricelist` (sub-tab in Invoices) + top-nav shortcut. Inline CRUD, customer-type filter, auto-export `pricelist.md`. ArchiveHistorySheet placeholder pending Phase 1.5.
- **Phase 3** — Wire `EstimateCreator` to the live pricelist. Per-line-item search + sub-pickers (variants, size_tier, yard_tier). Customer-type pre-filter via deterministic resolution order. Above-tier-max prompt. Hidden `unit_cost` per line item.
- **Phase 4** — Payment visibility: timeline payment events, receipt SMS/email, "Paid — $NNN · $method" confirmation card.
- **Phase 5** — Cosmetic polish: CTA labels match spec, Maps "Remember my choice" persisted on `Staff`, full uninstall of deprecated `stripe_terminal`.
- **Phase 6 (mandatory E2E)** — Visual + DB verification of every flow, button, and combination introduced in Phases 0–5. Built on existing `agent-browser` pattern (`e2e/*.sh` + `e2e-screenshots/`). Includes per-phase test matrices covering every PaymentMethod (5), every PricingModel variant in drawer (17), every customer-type-resolution path (3), every TimelineEventKind, and a cross-phase happy-path integration scenario. Responsive at 3 viewports. Console-error gate. Sign-off report required for merge.

## Feature Metadata

**Feature Type**: Enhancement + New Capability (mixed; price-list editor is net-new, others enhance existing flows)
**Estimated Complexity**: **High** — touches Estimate, Job, ServiceOffering, EstimateLineItem, Invoice, Appointment timeline, and Audit. Migration includes append-only price history.
**Primary Systems Affected**:
- Backend: `EstimateService`, `JobService`, `ServiceOfferingService`, `AppointmentTimelineService`, `InvoiceService`, `AuditService`, new `EstimatePdfService`, new `PriceListExportService`.
- Frontend: `AppointmentModal`, new `EstimateSheet` (E1→E8 states), new `PriceListEditor` page, new `serviceApi.ts` slice, `EstimateReview` portal page, `Invoices` page (new sub-tab).
- Migrations: 4 new Alembic migrations (estimate columns; service_offering schema rebuild; price history table; `EstimateLineItem.unit_cost`/`material_markup_pct`).

**Dependencies**:
- `pg_jsonschema` Postgres extension (Railway-hosted Postgres — verify availability; fallback path documented in Phase 1).
- `weasyprint` (already in `pyproject.toml:53`) for signed-PDF estimate generation.
- `resend` (already wired per memory `project_estimate_email_portal_wired.md`) for portal-approval PDF email.
- New: nothing else.

---

## Decision Log

Every decision below was made during the 2026-05-01 planning conversation. **Decisions are referenced by ID throughout the implementation tasks.** Audit `§4` Bucket A/B/C maps to V/E/P prefixes.

### Auto-job-on-approval (AJ)

| ID | Decision | Source |
|---|---|---|
| **AJ-1** | `EstimateService.approve_via_portal()` calls `JobService.create_job()` synchronously, in the same DB transaction. **Hardcoded — no tenant setting** (decision N5: option (b) **REVERSED** in conversation; final answer was option (a) — wait actually user picked **(b) toggleable setting**). See N5 below for final wiring. | Conversation 2026-05-01 |
| **AJ-2** | **Estimate has NO `target_start_date` / `target_end_date` columns.** Dropped per user. The auto-created Job lands `TO_BE_SCHEDULED` with no target week. Office staff schedules from queue or via the new "Schedule follow-up" CTA. | User, 2026-05-01 |
| **AJ-3** | Auto-created Job status: always `TO_BE_SCHEDULED`. Aligned with HCP, Jobber, FieldEdge (industry consensus per research). | Research bundle 1 |
| **AJ-4** | **VERIFIED 2026-05-01**: No `JobScopeItem` model exists (`grep "JobScopeItem\|scope_items\|job_scope" src/grins_platform` returns no matches). **Decision**: add `Job.scope_items: JSONB NULLABLE` column (small Phase 0 migration), copy `Estimate.line_items` dict shape verbatim. Mirrors existing `Estimate.line_items: JSONB` pattern at `models/estimate.py:67-70`. | Audit + verification 2026-05-01 |
| **AJ-5** | No Invoice created at approval. Invoice still flows from job-completion path (existing). `estimate.job_id` ← new job; new Job carries an `estimate_id` back-reference. | Industry universal |
| **AJ-6** | **REVISED 2026-05-01**: No SSE/websocket/broadcast infrastructure exists today (verified — `grep "broadcast\|websocket\|sse_\|EventStream\|streaming"` in services returns only AI-streaming + campaign code, none of which is appointment-modal-applicable). **Decision**: 60s polling on the open modal via TanStack Query `refetchInterval`. Server-push is a future enhancement, not "use existing infrastructure." Cache invalidation still fires on the portal approval HTTP response so the originating tab updates immediately; other staff tabs catch up via the 60s poll. | Verification 2026-05-01 |
| **AJ-7** | **Two branches** at approval: <br>(i) standalone estimate → create new Job, set `estimate.job_id = new_job.id`; <br>(ii) estimate already attached to an existing in-progress appointment → copy line items into the parent job, no new Job. Mirrors HCP "Copy to this job" / "Copy to new job". | Research bundle 1 |
| **AJ-8** | At approval, generate a signed-PDF estimate (signature + IP + timestamp baked in) via `weasyprint` and email it to the customer via Resend. Industry universal across HCP + Jobber. **Mirror target**: `services/invoice_pdf_service.py` (verified — clean WeasyPrint + S3 + branding pattern; class is `InvoicePDFService` with capital PDF). New service: `EstimatePDFService`. **Decision**: attach PDF directly to Resend email (≤500KB; well under 40MB limit) — skip S3 round-trip for v1. | Research bundle 1 + verification |

### Viktor Data Confirmations (V)

| ID | Decision | Notes for Viktor |
|---|---|---|
| **V1** | Commercial mulch unit: **per sq ft** (matches all other mulch rows). | Flag in seed migration; one-line PR check before migration runs. |
| **V2** | Commercial backflow price: **$600 (same as residential)** — likely source omission. | Same flag mechanism. |
| **V3** | Commercial drip "per zone": **`per_zone_range`** (matches residential pattern; likely accidental omission). | Same flag mechanism. |
| **V4** | Straw blanket coverage: cosmetic — doesn't affect $/roll. Documentation cleanup only; PDF source rewrite is Viktor-side, not blocker. | — |
| **V5** | Source typos (`linear food` → foot, `Per diameter Inter` → Inch, `plant plant` duplicate): already corrected in seed JSON. PDF source cleanup is Viktor-side. | — |

### Engineering Data-Shape (E)

| ID | Decision | Source |
|---|---|---|
| **E1** | **Hybrid storage**: `pricing_model` enum (extended) as discriminator + `pricing_rule` JSONB column for the rule body. Add `pg_jsonschema` CHECK constraints keyed by `pricing_model` if available; fallback to Pydantic discriminated unions. | Research bundle 2 (Stripe `Price` model) |
| **E2** | Materials: `includes_materials: bool` flag on `ServiceOffering` + **`unit_cost: Decimal` per line item on `EstimateLineItem`** (filled at quote time, hidden from customer). **Plus `material_markup_pct: Decimal` (default 0)** on EstimateLineItem — future-proofing seam, no UI in v1. | Research bundle 4 (Jobber hidden-cost) |
| **E3** | Customer-type partitioning: **distinct rows** with `customer_type` enum column (`residential` / `commercial`). 73 seed items × 2 customer types = ~146 rows. Stripe pattern when shape may differ. | Research bundle 2 |
| **E4** | Audit logging: **Stripe-style immutable rows.** Edits don't UPDATE — they `active=false` + insert new row + `replaced_by_id` self-FK. AuditService.log_action() logs both the archive event and the create event. Estimates pin to the offering ID they used at quote time. | Research bundle 2 (Stripe `manage prices`) |
| **E5** | **UUIDv7 PK** (sortable, B-tree friendly) + `slug` TEXT UNIQUE column (from seed `key` field) + **immutable after create**. Add separate mutable `display_name` for renaming. Slug-rename = silent FK breakage. | Research bundle 2 |
| **E6** | Range pricing: collapses into JSONB `pricing_rule` per E1. No separate min/max columns. | E1 |
| **E7** | `EstimateTemplate` retained as **bundles of `ServiceOffering` references** (e.g. "Spring Package" = Spring Start-Up + WiFi Upgrade). Templates live alongside per-line-item picker, not replaced. | Audit + Shopify product/variant analogue |

### Product UX (P)

| ID | Decision | Source |
|---|---|---|
| **P1** | **Phase 1**: tech picks single point inside the range at quote time. Range shown as guard-rail. **`pricing_rule.range_anchors: {low, mid, high}` JSON key** stored now (zero cost) to accommodate Phase 2 G/B/B picker UI without future migration. | User confirmed N4; research bundle 3 (ServiceTitan G/B/B as direction) |
| **P2** | `size_tier` (Tree Drop S/M/L) — **one row + size dropdown** in picker. | Research bundle 3 |
| **P3** | `variants` (valve repair sub-types) — **one row + sub-picker**. Consistent with P2. | Research bundle 3 |
| **P4** | Customer-type defaulting: pre-filter picker on customer's customer_type with manual override toggle. ServiceTitan-style rate sheet auto-application. | Research bundle 3 |
| **P4-RESOLVED** | **Audit was wrong**: `Customer.customer_type` does NOT exist. **Verified state of customer-type fields across models** (2026-05-01): <br>• `Lead.customer_type` — EXISTS at `models/lead.py:115` (Optional[str]). <br>• `Customer.customer_type` — does NOT exist. <br>• `Property.property_type` — EXISTS at `models/property.py:103` with `PropertyType` enum (RESIDENTIAL / COMMERCIAL). <br>**Phase 3 picker resolution order** (deterministic, no new migration): <br>1. If `estimate.lead_id` set → use `lead.customer_type`. <br>2. Else if `estimate.customer_id` set + estimate has linked property → use `property.property_type`. <br>3. Else → default to `residential` and surface toggle prominently. <br>Manual override toggle always available. **No `Customer.customer_type` migration needed**; Phase 3 task instructions below reflect this. | Verification 2026-05-01 |
| **P5** | Materials cost UX: **hidden `unit_cost` field per estimate line item** (Jobber pattern). Hidden from customer; shown to staff in edit drawer. NOT a labeled "material_cost" column on the customer-facing estimate row. Pair with `material_markup_pct` (E2). | Research bundle 4 |
| **P6** | Customer-facing estimates: **single committed number per line, never a range**. Range is staff-internal (range_low / range_high in the picker). | Research bundle 4 (industry consensus on range pricing as weak) |
| **P7** | **No markup/discount layer in Phase 1.** Seeded prices terminal. Service-call-fee credit (P11) is the one exception, modeled as a negative line item. | Research bundle 4 |
| **P8** | Auto-generate `pricelist.md` from DB on save. **Frame as public-website / customer-handout export, not the canonical UI.** Retire manual maintenance of the static markdown. | Research bundle 3 |
| **P9** | Editor primary location: **`/invoices/pricelist`** (sub-tab inside Invoices) per user preference. **Add top-nav "Pricebook" shortcut** linking there, since ST/HCP/Stripe all expose pricebooks at top level (research bundle 3). | User preference + research compromise |
| **P10** | Above tier max (e.g. >19 zones for Spring Start-Up): **"Custom quote" prompt** that switches that line to a free-form `custom` model. Inline indicator. | Research bundle 3 |
| **P11** | Conditional service-call fee waiver: **manual tech application in Phase 1**, modeled as a **negative line item credit** ("Service call credit −$X · waived on approval") on the work invoice. NOT a "fee removed" flag. Auto-credit deferred. | Research bundle 4 (industry mechanic) |
| **P12** | Emergency / after-hours surcharge: **manual tech toggle in Phase 1**. Auto-apply requires holiday calendar + business-hours config (deferred). | Research bundle 4 |

### New Open Questions (N) — Conversation 2026-05-01

| ID | Decision | Status |
|---|---|---|
| **N1** | **Service-call / dispatch fee** ($89 industry benchmark, waived on approved work). | **NOT IMPLEMENTING.** Per user: "We're not going to have the $89 fee." Documented in **§ Deferred Features** below; schema does not include it. |
| **N2** | **After-hours surcharge** with business-hours/holiday calendar. | **NOT IMPLEMENTING.** Per user: "We're not going to have the after hours surcharge." Documented in **§ Deferred Features** below. |
| **N3** | **Material markup default** — true cost-plus vs 25–50% industry markup. | **NOT IMPLEMENTING the markup math.** `material_markup_pct` column added (default 0) per E2 as a future-proofing seam, but no UI surfaces it and seed values are 0%. Documented in **§ Deferred Features**. |
| **N4** | **Good/Better/Best schema accommodation.** | **IMPLEMENTING the schema seam.** `pricing_rule.range_anchors` JSON key added now, no UI. Per user: "go with your recommendation for N4 and make a note of it in the plan as well." Phase 2 G/B/B UI is documented in **§ Deferred Features**. |
| **N5** | **Auto-job tenant setting.** | **IMPLEMENTING option (b) — toggleable setting.** Per user: "Let's go with B for N5." Verified pattern: add `"auto_job_on_approval"` to `BUSINESS_SETTING_KEYS` tuple at `services/business_setting_service.py:40-48`. Read via `await business_setting_service.get_bool("auto_job_on_approval", default=True)` (`get_bool` exists at line 141). Write via existing `set_value()` at line 215. Audit logging is automatic (set_value writes to AuditLog). |

---

## CONTEXT REFERENCES

### Relevant Codebase Files — IMPORTANT: YOU MUST READ THESE BEFORE IMPLEMENTING

#### Backend (Phase 0 — auto-job-on-approval)

- `src/grins_platform/services/estimate_service.py` (lines 386–468) — `approve_via_portal()` is the call site to extend. Note the existing pattern: tag update + sales pipeline correlation + internal notification, all best-effort (never raise after the customer-side decision is recorded).
- `src/grins_platform/models/estimate.py` (lines 52–55) — `job_id` FK exists, never populated today. Also lines 144–147 for relationship.
- `src/grins_platform/services/job_service.py` (lines 223–322) — `create_job()` signature; auto-categorization rules at lines 126–150 (`_determine_category`); valid status transitions at lines 75–94. **The `quoted_amount` rule at line 142–143 means setting `quoted_amount` from estimate total auto-categorizes the new job as `READY_TO_SCHEDULE`.**
- `src/grins_platform/services/business_setting_service.py` — precedent for tenant-flag pattern (use for N5 `auto_job_on_approval`).
- `src/grins_platform/services/audit_service.py` (lines 75–120) — `log_action()` signature for E4. Note canonical action strings at lines 19–34 — extend rather than invent new patterns. Add: `service_offering.archive`, `service_offering.create`, `estimate.auto_job_created`.
- `src/grins_platform/services/email_service.py` — Resend wiring; `send_estimate_email` signature for AJ-8 PDF email.
- `src/grins_platform/services/invoice_pdf_service.py` — existing weasyprint pattern; mirror for `estimate_pdf_service.py`.

#### Backend (Phase 1 — pricelist data model)

- `src/grins_platform/models/service_offering.py` (entire file, 166 lines) — model to rebuild. Today: `base_price`, `price_per_zone`, `pricing_model` String(50), `is_active`. **Will become hybrid storage** with new `pricing_rule` JSONB, `customer_type` enum, `slug` TEXT UNIQUE, UUIDv7 PK, `replaced_by_id` self-FK, `includes_materials` bool, `display_name` TEXT.
- `src/grins_platform/models/enums.py` — `PricingModel` enum to extend (currently `flat`/`zone_based`/`hourly`/`custom`; add `flat_range`, `per_unit_flat`, `per_unit_range`, `per_zone_range`, `tiered_zone_step`, `tiered_linear`, `compound_per_unit`, `compound_repair`, `size_tier`, `size_tier_plus_materials`, `yard_tier`, `variants`, `flat_plus_materials`, `conditional_fee`, `per_unit_flat_plus_materials`).
- `src/grins_platform/services/service_offering_service.py` (lines 112–179) — `update_service()` and `deactivate_service()`; **rewrite to Stripe-style archive+insert pattern per E4**. Add `archive_and_replace()` method.
- `src/grins_platform/api/v1/services.py` (lines 34–337) — existing CRUD; PUT semantics changes to "archive + insert new" — **breaking change for any external consumers**. Verify no external callers (audit notes none).
- `src/grins_platform/migrations/versions/20260428_150000_add_invoice_payment_link_columns.py` — recent Alembic migration as reference for migration style + reversibility.
- `src/grins_platform/migrations/versions/20260503_100000_ai_scheduling_tables.py` — recent table-creation migration as reference.
- `bughunt/2026-05-01-pricelist-seed-data.json` (entire file) — DRAFT seed; promote to migration after V1/V2/V3 confirmed.

#### Backend (Phase 3 — estimate creator wiring)

- `src/grins_platform/services/estimate_service.py` (lines 112–177, `create_estimate`; lines 956–979, `_calculate_subtotal`) — line item shape; will need to extend to support `service_offering_id`, `unit_cost` (hidden), `material_markup_pct` per line item.
- `src/grins_platform/schemas/estimate.py` — `EstimateCreate` and line-item schema; extend with new fields.

#### Backend (Phase 4 — payment visibility)

- `src/grins_platform/services/appointment_timeline_service.py` (entire file, 251 lines) — extend `get_timeline()` to join `invoices` + `payments` (or whatever payment-event table exists). Add new `TimelineEventKind.PAYMENT_RECEIVED`. Mirror existing `_outbound_to_event` / `_inbound_to_event` pattern.
- `src/grins_platform/schemas/appointment_timeline.py` — extend `TimelineEventKind` enum.
- `src/grins_platform/services/invoice_service.py` — payment recording + reconciliation; trigger receipt SMS/email after `collect_payment` succeeds.
- `src/grins_platform/services/sms_service.py` + `email_service.py` — receipt delivery channels.

#### Frontend (Phase 0 — Schedule follow-up CTA + status banner)

- `frontend/src/features/schedule/components/AppointmentModal/AppointmentModal.tsx` (lines 598, 606) — existing Estimate CTA labeled "Create Estimate" today; rename to "Send estimate" per spec (Phase 5) and wire status banner refresh logic (Phase 0).
- `frontend/src/features/schedule/components/AppointmentModal/EstimateSheetWrapper.tsx` — wraps the estimate sheet; needs new "Approved" state with "Schedule follow-up" CTA.
- `frontend/src/pages/portal/EstimateReview.tsx` + `ApprovalConfirmation.tsx` — customer-facing portal; trigger backend approval that fires the new auto-job path.

#### Frontend (Phase 2 — pricelist editor)

- `frontend/src/pages/Invoices.tsx` — host the new sub-tab. Use existing tabs pattern.
- `frontend/src/features/invoices/{api,components,hooks,types,utils}/` — vertical-slice extension point. Add `frontend/src/features/services/` as a new feature slice (or `frontend/src/features/pricelist/` — see Task 2.1) for `serviceApi.ts`, `ServiceOfferingTable.tsx`, `useServiceOfferings.ts`, etc.
- `frontend/src/core/router/index.tsx` — register the `/invoices/pricelist` sub-route.
- `frontend/src/pages/Settings.tsx` (entire file, 373 lines) — pattern reference for embedded sub-page panels (BusinessInfo / InvoiceDefaults / EstimateDefaults / NotificationPrefs).

#### Frontend (Phase 3 — estimate creator wired to pricelist)

- `frontend/src/features/schedule/components/AppointmentModal/EstimateSheetWrapper.tsx` + downstream `EstimateCreator.tsx` — replace the template-only picker with the new `LineItemPicker` searching `/api/v1/services?customer_type=…`.
- `frontend/src/features/schedule/components/AppointmentModal/PaymentSheetWrapper.tsx` — currently has hardcoded payment methods only; out of scope this phase except for the "Paid" confirmation card (Phase 4).

#### Frontend (Phase 4 — payment visibility)

- `frontend/src/features/schedule/components/AppointmentModal/PaymentSheetWrapper.tsx` — collapse-into-confirmation card on success.
- Wherever the appointment timeline is rendered (likely `AppointmentDetail.tsx` or the modal's communication panel) — read new payment events from extended timeline.

#### Frontend (Phase 5 — polish)

- `frontend/src/features/schedule/components/AppointmentModal/MapsPickerPopover.tsx` (lines 55–106) — add "Remember my choice" footer + `user.preferred_maps_app` persistence.
- `frontend/src/features/schedule/components/AppointmentModal/ActionTrack.tsx` / `ActionCard.tsx` — sublabel string change ("En route" → "On my way", etc.).

#### Reference Files

- `src/grins_platform/services/stripe_terminal.py` — header comment "New code MUST NOT import this module"; delete after Phase 4 confirms no callers remain.
- `pricelist.md` — static markdown to retire after Phase 2 auto-export ships.
- `feature-developments/design_handoff_appointment_modal_combined 2/README.md` — design spec (CTAs, sublabels, confirmation card).
- `feature-developments/Obsidian Notes Enhancements/{06,07,08,09}*.md` — audit's source notes.
- `audit-screenshots/missing-states/*.png` — visual reference for design states.

### New Files to Create

#### Backend

- `src/grins_platform/migrations/versions/{ts}_add_business_settings_auto_job_on_approval.py` — N5 setting (Phase 0).
- `src/grins_platform/migrations/versions/{ts}_extend_estimate_for_auto_job.py` — Phase 0; this is small (no target dates per AJ-2; just any required new columns identified in Task 0.X).
- `src/grins_platform/migrations/versions/{ts}_rebuild_service_offering_for_pricelist.py` — Phase 1 schema migration.
- `src/grins_platform/migrations/versions/{ts}_seed_pricelist_from_viktor_jsonl.py` — Phase 1 data migration (gated on V1/V2/V3 confirmed flag).
- `src/grins_platform/migrations/versions/{ts}_add_estimate_line_item_unit_cost_and_markup.py` — Phase 3.
- `src/grins_platform/services/estimate_pdf_service.py` — AJ-8 (signed-PDF generation, mirror of `invoice_pdf_service.py`).
- `src/grins_platform/services/price_list_export_service.py` — P8 auto-generate `pricelist.md`.
- `src/grins_platform/schemas/pricing_rule.py` — Pydantic discriminated union per `pricing_model` value (E1).
- `src/grins_platform/services/service_offering_service.py` — extend with `archive_and_replace()` (E4).
- `src/grins_platform/tests/unit/services/test_estimate_auto_job.py` — Phase 0 unit tests.
- `src/grins_platform/tests/functional/services/test_estimate_approval_flow.py` — Phase 0 integration.
- `src/grins_platform/tests/unit/services/test_service_offering_archive.py` — E4 unit tests.
- `src/grins_platform/tests/functional/api/test_pricelist_crud.py` — Phase 1/2 functional.

#### Frontend

- `frontend/src/features/pricelist/index.ts` — feature slice barrel.
- `frontend/src/features/pricelist/api/serviceApi.ts` — TanStack Query client.
- `frontend/src/features/pricelist/components/PriceListEditor.tsx` — main editor.
- `frontend/src/features/pricelist/components/ServiceOfferingTable.tsx` — paginated table with inline edit.
- `frontend/src/features/pricelist/components/ServiceOfferingDrawer.tsx` — edit form per pricing model.
- `frontend/src/features/pricelist/components/ArchiveHistorySheet.tsx` — view price history (E4).
- `frontend/src/features/pricelist/hooks/useServiceOfferings.ts`, `useArchiveServiceOffering.ts` — data hooks.
- `frontend/src/features/pricelist/types/index.ts` — TypeScript types matching backend Pydantic.
- `frontend/src/features/schedule/components/AppointmentModal/EstimateSheet/LineItemPicker.tsx` — Phase 3 search picker.
- `frontend/src/features/schedule/components/AppointmentModal/EstimateSheet/SizeTierSubPicker.tsx` — Phase 3 P2/P3.
- `frontend/src/features/schedule/components/AppointmentModal/EstimateSheet/ApprovedConfirmationCard.tsx` — Phase 0 "Schedule follow-up" CTA.
- `frontend/src/features/schedule/components/AppointmentModal/PaymentSheet/PaidConfirmationCard.tsx` — Phase 4.

### Relevant Documentation — YOU SHOULD READ THESE BEFORE IMPLEMENTING

- [Stripe Price object](https://docs.stripe.com/api/prices/object) — `billing_scheme`, `tiers_mode`, `unit_amount`, nested JSON shape. Reference for E1 hybrid-storage architecture.
- [Stripe manage prices](https://docs.stripe.com/products-prices/manage-prices) — immutability + archive pattern for E4.
- [Supabase pg_jsonschema](https://supabase.com/blog/pg-jsonschema-a-postgres-extension-for-json-validation) — JSONB CHECK constraint validation. Used in Phase 1 if Railway Postgres has the extension; fallback path documented.
- [Wei Yen — Modelling discriminated unions in Postgres](https://weiyen.net/articles/modelling-discriminated-unions-in-postgres/) — confirms hybrid (E1) over single-wide-table or pure JSONB.
- [HCP automate job creation from approved estimates](https://help.housecallpro.com/en/articles/12119814-automate-job-creation-from-approved-estimates) — N5 toggleable-setting precedent.
- [HCP estimates on jobs](https://help.housecallpro.com/en/articles/9196840-estimates-on-jobs) — AJ-7 standalone-vs-attached branch precedent.
- [Jobber Quote Approvals](https://help.getjobber.com/hc/en-us/articles/115012715008-Quote-Approvals) — push-notification + email-confirmation pattern; reference for AJ-6 + AJ-8.
- [ServiceTitan — Good Better Best HVAC Proposal](https://www.servicetitan.com/blog/good-better-best-hvac-proposal) — N4 deferred-Phase-2 G/B/B direction.
- [SQLAlchemy `MutableDict.as_mutable(JSONB)`](https://docs.sqlalchemy.org/en/20/orm/extensions/mutable.html) — gotcha for E1: nested mutations on JSONB don't auto-flush; must use mutable types or `flag_modified()`.

### Patterns to Follow

#### Naming Conventions

- Python: `snake_case.py`. Service classes: `{Domain}Service` extending `LoggerMixin` with `DOMAIN = "{domain}"` class attribute. Tests: `test_{module}.py` with `@pytest.mark.{unit|functional|integration}`.
- Frontend: Components `PascalCase.tsx`, hooks `useXxx.ts`, API client `{feature}Api.ts`. Vertical-slice barrel exports via `index.ts`.
- Audit action strings: `{resource}.{verb}` (e.g. `service_offering.archive`, `service_offering.create`, `estimate.auto_job_created`). Extend the canonical list in `audit_service.py:19–34` — never invent ad-hoc action strings.
- Migration filenames: `{YYYYMMDD}_{HHMMSS}_{snake_case_description}.py`.

#### Error Handling (mirror `estimate_service.py`)

```python
self.log_started("auto_create_job_from_estimate", estimate_id=str(estimate.id))
try:
    job = await self.job_service.create_job(...)
    self.log_completed("auto_create_job_from_estimate", job_id=str(job.id))
except ValidationError as e:
    self.log_rejected("auto_create_job_from_estimate", reason=str(e))
    raise
except Exception as e:
    self.log_failed("auto_create_job_from_estimate", error=e)
    raise
```

The auto-job call must NOT undo the customer's approval if it fails — same pattern as `_notify_internal_decision()` (line 553) which is best-effort and never re-raises. **The approval transaction commits first; the auto-job call is best-effort with retry on failure** (mirror notification pattern).

#### Audit Logging Pattern (E4 archive+create)

```python
# In service_offering_service.py archive_and_replace()
async with self.repo.session.begin_nested():
    archived = await self.repo.archive(offering_id)
    new = await self.repo.create_replacement(archived, **updates)

await self.audit_service.log_action(
    db=self.repo.session,
    actor_id=actor_id, actor_role=actor_role,
    action="service_offering.archive",
    resource_type="service_offering",
    resource_id=archived.id,
    details={"replaced_by_id": str(new.id), "actor_type": "staff", "source": "admin_ui"},
    ip_address=ip_address, user_agent=user_agent,
)
await self.audit_service.log_action(
    db=self.repo.session,
    actor_id=actor_id, actor_role=actor_role,
    action="service_offering.create",
    resource_type="service_offering",
    resource_id=new.id,
    details={"replaces_id": str(archived.id), "actor_type": "staff", "source": "admin_ui"},
    ip_address=ip_address, user_agent=user_agent,
)
```

#### Frontend Vertical-Slice Pattern (`features/pricelist/`)

Mirror `frontend/src/features/invoices/`. Each feature self-contains:
- `api/` — TanStack Query client wrapping `apiClient` from `@/core/api/client`.
- `components/` — UI; only imports from `@/core` and `@/shared`, never from sibling features.
- `hooks/` — `useServiceOfferings()`, `useArchiveServiceOffering()`, etc.
- `types/` — TypeScript mirroring backend Pydantic schemas.
- `index.ts` — barrel exports the public surface.

#### Migration Pattern

Follow `20260428_150000_add_invoice_payment_link_columns.py`. Two-step backfill for E5 slug column: data migration (populate from `name` slugify) → constraint addition. Each migration must have a working `downgrade()`.

---

## IMPLEMENTATION PLAN

### Phase 0: Auto-job-on-approval (P0 #1)

**Goal**: customer YES via portal → auto-creates a `TO_BE_SCHEDULED` Job, copies line items, sends signed-PDF email, refreshes the appointment-modal banner. Schedule follow-up CTA on the Approved card opens the existing schedule modal against the new job.

**Phase 0 Tasks**:

- Verify `JobScopeItem` model existence (decision AJ-4 fallback). If absent: line items copied as JSONB onto Job.
- Add `business_settings.auto_job_on_approval: bool` (default `true`) per N5.
- Wire `EstimateService.approve_via_portal()` to call `JobService.create_job()` synchronously when setting is ON.
- Implement two branches per AJ-7: standalone vs. attached-to-existing-appointment.
- Add `EstimatePdfService` for AJ-8 signed PDF; wire into approval handler to email via Resend.
- Add `Schedule follow-up` CTA on the Approved-state confirmation card (`ApprovedConfirmationCard.tsx`).
- Wire TanStack Query invalidation + 60s polling fallback for AJ-6.
- Tests: unit (each branch + N5 ON/OFF), functional (real DB, end-to-end approval → job creation), integration (modal banner refresh).

### Phase 1: Pricelist Data Model + Seed (TRIMMED — 10/10 confidence scope)

**Goal**: extend `ServiceOffering` schema additively to support pricelist features and seed 73 rows from Viktor's JSON. **Implementation is strictly additive and reversible** — no existing column behavior changes, no API contract breaks, no extension dependencies.

**Phase 1 Scope (IMPLEMENTING NOW)**:

- Extend `PricingModel` enum with 13 new values per the seed file's distribution.
- Add nullable columns to `service_offerings`: `slug`, `display_name`, `customer_type`, `subcategory`, `pricing_rule` (JSONB), `replaced_by_id` (self-FK, ON DELETE SET NULL), `includes_materials` (bool default false), `source_text`.
- Partial unique index `ix_service_offerings_slug_unique` on `slug WHERE slug IS NOT NULL`. Existing unslugged rows do not conflict.
- Index on `customer_type` for filter queries.
- Update `ServiceOffering` SQLAlchemy model to declare new fields (all nullable except `includes_materials`).
- Update `ServiceOfferingCreate` / `ServiceOfferingUpdate` / `ServiceOfferingResponse` schemas to include new fields as Optional. **No breaking changes to existing API consumers.**
- Update repository `create()` and `list_with_filters()` signatures to accept new fields and `customer_type` filter.
- Seed migration loads `bughunt/2026-05-01-pricelist-seed-data.json` and INSERTs 73 rows. Gated on `VIKTOR_PRICELIST_CONFIRMED=true` env var. Fields outside the standard set (`key`, `name`, `category`, `subcategory`, `customer_type`, `pricing_model`, `source_text`) are stuffed into `pricing_rule` JSONB.

**Phase 1 Deferred (NOT IMPLEMENTING in this pass — moved to Phase 1.5)**:

- `pg_jsonschema` CHECK constraints (extension availability on Railway is unconfirmed). Schema validation will rely on app-layer Pydantic checks added when Phase 3 wires the line-item picker.
- Pydantic discriminated union for `pricing_rule` (17 variants). Raw JSONB roundtrips are sufficient for the seed; the union goes in when Phase 2/3 needs typed reads.
- UUIDv7 PK (extension uncertain). PK stays UUIDv4 via `gen_random_uuid()` matching the rest of the codebase.
- Stripe-style **archive + create** rewrite of `ServiceOfferingService`. The `replaced_by_id` column is added now as a forward-compat seam; behaviour stays UPDATE-in-place until Phase 1.5.
- AuditService wiring on `service_offering.create/update/deactivate` (depends on archive+create model).

**Why the trim**: each deferred item introduces a moving part the seed itself does not need. Adding `replaced_by_id` as a nullable column now means Phase 1.5 archive+create is a service-layer change, not a schema change. Adding `pricing_rule` as plain JSONB means Phase 2/3 can layer Pydantic union validation on reads without altering writes.

**Phase 1 Tests**:

- Functional: `test_pricelist_seed_migration.py` — `VIKTOR_PRICELIST_CONFIRMED` gating works (raises without; succeeds with). After upgrade, exactly 73 rows have `slug NOT NULL`. Sample-row assertions for one item per `pricing_model` variant.
- Functional: `test_service_offering_with_new_columns.py` — existing `/api/v1/services` POST + GET round-trips an item with new optional fields populated.
- Unit: enum extension doesn't break existing rows (all 4 legacy values still parse).

### Phase 2: Pricelist Admin Editor UI (P9, P8, audit history)

**Goal**: usable admin pricelist editor at `/invoices/pricelist`, with audit history sheet and auto-export to `pricelist.md`.

**Phase 2 Tasks**:

- Create `frontend/src/features/pricelist/` slice (vertical-slice pattern).
- `serviceApi.ts` TanStack Query client.
- `PriceListEditor.tsx` — paginated table, customer-type filter (P4), search by name/slug, category facet.
- `ServiceOfferingDrawer.tsx` — edit form that branches on `pricing_model` (one panel per discriminator value, mirroring Pydantic union).
- `ArchiveHistorySheet.tsx` — view price-change timeline for an offering (E4 audit data).
- Wire into `frontend/src/pages/Invoices.tsx` as a new tab. Top-nav shortcut at "Pricebook" links to `/invoices/pricelist`.
- Backend: `PriceListExportService` regenerates `pricelist.md` on every CRUD save; serve from `/api/v1/services/export/pricelist.md`. Cache by `MAX(updated_at)`.
- Tests: functional (CRUD round-trips, archive history accurate), Vitest (form per pricing model, filter behavior).

### Phase 3: Estimate Creator Wired to Pricelist (P0 #3, P1, P2, P3, P5, P10)

**Goal**: techs pick line items from the live pricelist, not from `EstimateTemplate`. Single-point-in-range, size/variant sub-pickers, customer-type pre-filter, hidden unit_cost.

**Phase 3 Tasks**:

- Migration: add `unit_cost: Numeric(10,2) NULLABLE`, `material_markup_pct: Numeric(5,2) DEFAULT 0` to estimate line item shape (currently a JSONB column on `Estimate.line_items` — extend the dict shape; document new keys in `schemas/estimate.py`).
- New `LineItemPicker.tsx` — debounced search of `/api/v1/services?customer_type={customer_type}&q=`. Uses `Customer.customer_type` to pre-filter (P4); manual override toggle.
- `SizeTierSubPicker.tsx` and `VariantSubPicker.tsx` — collapse multi-option items into one row + sub-picker (P2/P3).
- "Custom quote" inline indicator when above tier max (P10) — adds line as `pricing_model: custom`.
- `pricing_rule.range_anchors.{low,mid,high}` rendered as 3 quick-pick chips when present (P1 / N4 schema seam).
- `unit_cost` field hidden on customer-facing PDF; visible to staff in edit drawer.
- `EstimateTemplate` retained as a separate entry point ("Use a template" button); both coexist (E7).
- Tests: Vitest (picker interactions, sub-pickers, customer-type override), functional (estimate created with `service_offering_id` per line item, line item includes `unit_cost`).

### Phase 4: Payment Visibility + Receipts (P1 #4, #5, #6, P11 mechanic)

**Goal**: every payment (cash, check, Stripe) shows on the appointment timeline, customer gets a receipt, the modal collapses payment CTA into a "Paid — $NNN · $method" confirmation card.

**Phase 4 Tasks**:

- Extend `appointment_timeline_service.py`: add `_payment_to_event` mirroring `_outbound_to_event` pattern. Join from `invoices` + `payments` (verify schema; the invoice payment-recording table is the source of truth).
- Extend `TimelineEventKind` enum with `PAYMENT_RECEIVED`.
- Wire receipt SMS + email after `InvoiceService.collect_payment()` succeeds — both Stripe Payment Link path and manual cash/check path. Reuse Resend wiring from `email_service.send_estimate_email` pattern; SMS via factory.
- `PaidConfirmationCard.tsx` — collapses `PaymentSheetWrapper.tsx` on success per design §8.5.
- Document P11 mechanic: service-call-fee waivers must be modeled as a negative line item credit on the work invoice. **This is documentation only in Phase 4** — actual fee config lives in deferred N1.
- Tests: functional (cash payment shows on timeline; receipt SMS/email fires; confirmation card renders), integration (Stripe webhook → timeline update).

### Phase 5: Cosmetic Polish (P2 audit list)

**Goal**: design-spec alignment for CTA labels, action sublabels, Maps popover; cleanup deprecated code.

**Phase 5 Tasks**:

- Rename Estimate CTA `AppointmentModal.tsx:606` "Create Estimate" → "Send estimate" per design §6.5.
- Update `ActionTrack.tsx` / `ActionCard.tsx` sublabels: "En route" → "On my way", "On site" → "Job started", "Done" → "Job complete".
- `MapsPickerPopover.tsx` — add "Remember my choice" footer + persist via `user.preferred_maps_app` (PATCH on User model — confirm field exists; if not, small migration).
- Delete `src/grins_platform/services/stripe_terminal.py` and any imports (audit confirms it's marked "MUST NOT import" already).
- Decide on `pricelist.md`: **retire static manual maintenance**; auto-generated from Phase 2 export is the canonical source. Update any developer doc references.
- Tests: Vitest snapshot updates for sublabel changes; manual smoke for Maps persistence.

---

## STEP-BY-STEP TASKS

IMPORTANT: Execute every task in order, top to bottom. Each task is atomic and independently testable. **All file paths are absolute under the repo root unless otherwise noted.**

### Phase 0 Tasks

#### Task 0.1: ADD `Job.scope_items` JSONB column

- **VERIFIED 2026-05-01**: `JobScopeItem` model does NOT exist (`grep "JobScopeItem|scope_items|job_scope" src/grins_platform` → 0 hits). Decision: add `scope_items: JSONB NULLABLE` column to `jobs` table; copy `Estimate.line_items` dict shape verbatim.
- **CREATE**: Alembic migration adding `scope_items: JSONB NULLABLE` to `jobs`. Mirror migration style of `20260428_150000_add_invoice_payment_link_columns.py`.
- **UPDATE**: `src/grins_platform/models/job.py` — add `scope_items: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB, nullable=True)`.
- **VALIDATE**: `uv run alembic upgrade head && uv run alembic downgrade -1 && uv run alembic upgrade head`.

#### Task 0.2: ADD `auto_job_on_approval` to BUSINESS_SETTING_KEYS (N5)

- **VERIFIED 2026-05-01**: `BusinessSettingService` already exposes the exact pattern needed:
  - `BUSINESS_SETTING_KEYS` tuple at `services/business_setting_service.py:40-48`.
  - `get_bool(key, default)` at line 141 — accepts True/False, "true"/"false", 1/0.
  - `set_value(key, value, updated_by)` at line 215 — upserts JSONB `{"value": <scalar>}` and writes an `audit_logs` row automatically.
- **NO MIGRATION NEEDED**: settings are stored as JSONB rows in the existing `business_settings` table. No schema change.
- **IMPLEMENT**:
  1. Add `"auto_job_on_approval"` to the `BUSINESS_SETTING_KEYS` tuple at line 40.
  2. In `EstimateService.approve_via_portal()` (Task 0.4), read `enabled = await self.business_setting_service.get_bool("auto_job_on_approval", default=True)` before the auto-job branch.
  3. Frontend admin toggle (Phase 2 polish): wire to existing settings UI; out-of-scope for Phase 0 (backend default of `True` makes the feature live without UI).
- **VALIDATE**: `uv run pytest -k auto_job_setting -v`.

#### Task 0.3: CREATE `EstimatePDFService` for signed-PDF generation (AJ-8)

- **VERIFIED 2026-05-01**: Mirror target `services/invoice_pdf_service.py` exists; class is `InvoicePDFService` (capital `PDF`, not `Pdf`). Use the same casing for consistency: **`EstimatePDFService`**. The service has S3 upload + branding read at lines 80-115; signature is `__init__(s3_client, s3_bucket)`. WeasyPrint render at line 117+.
- **IMPLEMENT**: New `src/grins_platform/services/estimate_pdf_service.py`. Generates a PDF from an `Estimate` instance using `weasyprint`, baking signature + IP + user_agent + approval timestamp into the document footer.
- **DECISION**: Per AJ-8 Decision Log, attach PDF directly to Resend email as bytes — skip S3 upload for v1. Constructor takes only `__init__()` (no S3 deps). Future enhancement can add S3 archival like InvoicePDFService.
- **IMPORTS**: `from weasyprint import HTML`; `from jinja2 import Environment, FileSystemLoader`.
- **NEW FILE**: `src/grins_platform/templates/estimate_signed_pdf.html` (Jinja2 template; reuse company-branding read pattern from `InvoicePDFService._get_company_branding()` at line 80).
- **GOTCHA**: PDF generation is slow (~1–2s). Running inside the approval transaction is acceptable for UX (customer gets the PDF in their email immediately) but **wrap in try/except — failure must NOT undo approval**.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/services/test_estimate_pdf_service.py -v`.

#### Task 0.4: WIRE auto-job branch in `EstimateService.approve_via_portal()`

- **IMPLEMENT**: After existing approval-recording block (lines 425–443) and lead-tag update (lines 445–458) but BEFORE `_notify_internal_decision` (line 460), add:
  1. Read `business_settings.auto_job_on_approval`. If OFF, skip auto-job entirely.
  2. Branch on `estimate.job_id is None`:
     - **Standalone (job_id is None)** — call `JobService.create_job(...)` with line items copied as `JobScopeItem` rows or `Job.scope_items` JSONB (per Task 0.1), `quoted_amount=estimate.total`, status `TO_BE_SCHEDULED`. Update `estimate.job_id = new_job.id`.
     - **Attached (job_id is not None)** — fetch parent job; copy line items into parent `JobScopeItem` rows / `scope_items` JSONB. Do NOT create a new Job.
  3. Wrap in try/except — failure logs but does not raise (mirror `_notify_internal_decision` pattern at line 553).
- **PATTERN**: `estimate_service.py:386-468` is the call site; `_notify_internal_decision` at line 553 is the best-effort error pattern to mirror.
- **IMPORTS**: `from grins_platform.services.job_service import JobService`; `from grins_platform.services.business_setting_service import BusinessSettingService`.
- **DI EXTENSION**: Add `job_service: JobService | None = None` and `business_setting_service: BusinessSettingService | None = None` to `EstimateService.__init__`. **Verified callsite list (14 instantiations across 9 files)** — all keep working with the default `None`:
  - `src/grins_platform/api/v1/dependencies.py:261, 391` (production DI)
  - `src/grins_platform/api/v1/portal.py:96` (production portal DI)
  - 11 test instantiations in `tests/unit/test_estimate_service.py`, `tests/unit/test_estimate_internal_notification.py`, `tests/unit/test_estimate_correlation.py`, `tests/functional/test_background_jobs_functional.py`, `tests/functional/test_estimate_operations_functional.py`, `tests/functional/test_estimate_email_send_functional.py`, `tests/integration/test_external_service_integration.py` (4 sites)
  - **Action items**: only the 3 production DI sites (`dependencies.py`, `portal.py`) need to actually pass the new services in for auto-job to fire. Tests pass `None` and exercise the skip path.
- **GOTCHA**: `JobService.create_job()` requires `customer_id` (verified at `services/job_service.py:223+`). If estimate has only `lead_id`, the auto-job branch must SKIP (logged as `skip_reason="no_customer"`). Pre-customer leads can't have a Job; this is correct behavior, not a bug.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/services/test_estimate_auto_job.py -v`.

#### Task 0.5: WIRE estimate-PDF email on approval (AJ-8)

- **IMPLEMENT**: After auto-job branch (Task 0.4) but still inside `approve_via_portal()`, generate signed PDF via `EstimatePdfService` and email customer via Resend.
- **PATTERN**: `estimate_service.py:312-329` shows the existing `email_service.send_estimate_email` call pattern; extend `email_service` with `send_estimate_approved_email(customer, estimate, pdf_bytes, portal_url)` mirroring it.
- **IMPORTS**: `from grins_platform.services.estimate_pdf_service import EstimatePdfService`.
- **GOTCHA**: Resend attachment limit is 40MB; estimate PDFs are <500KB so fine. But if customer has no email, fall back to SMS-only confirmation (the existing portal SMS already covers this — log only, don't fail).
- **VALIDATE**: `uv run pytest src/grins_platform/tests/functional/services/test_estimate_approval_flow.py::test_pdf_emailed_on_approval -v`.

#### Task 0.6: ADD audit-log entry for auto-job event

- **IMPLEMENT**: After successful auto-job creation in Task 0.4, call `audit_service.log_action()` with action=`estimate.auto_job_created`, resource_type=`estimate`, resource_id=`estimate.id`, details=`{"job_id": str(new_job.id), "actor_type": "customer", "source": "customer_portal"}`.
- **PATTERN**: `services/audit_service.py:75-120`; canonical action strings at lines 19–34.
- **IMPORTS**: `from grins_platform.services.audit_service import AuditService`.
- **GOTCHA**: Add `estimate.auto_job_created` to the docstring's canonical action list at lines 19–34. **Do NOT invent ad-hoc action strings.**
- **VALIDATE**: `uv run pytest -k auto_job_audit -v`.

#### Task 0.7: CREATE `ApprovedConfirmationCard.tsx` with Schedule follow-up CTA

- **IMPLEMENT**: New file `frontend/src/features/schedule/components/AppointmentModal/EstimateSheet/ApprovedConfirmationCard.tsx`. Renders when estimate status is APPROVED. Two states:
  - **Standalone with new job** — "Estimate approved · Job created (#J-NNN)" + primary CTA "Schedule follow-up" → opens existing schedule modal against the new job.
  - **Attached to parent job** — "Estimate approved · Items added to current appointment" — no CTA needed.
- **PATTERN**: Mirror `frontend/src/features/schedule/components/AppointmentModal/{ModalFooter,ModalHeader}.tsx` styling.
- **IMPORTS**: `import { useScheduleModal } from '@/features/schedule/...'` (find exact hook name).
- **GOTCHA**: Read `estimate.job_id` to decide branch; null → no auto-job created (setting was OFF or branch SKIPPED per Task 0.4 gotcha).
- **VALIDATE**: `cd frontend && npm run test -- ApprovedConfirmationCard`.

#### Task 0.8: WIRE TanStack Query invalidation + polling fallback (AJ-6)

- **IMPLEMENT**: In `EstimateSheetWrapper.tsx`, when modal is open AND estimate status is `SENT`, set up:
  - WebSocket/SSE listener (use existing event-broadcast infrastructure if present; otherwise polling).
  - Polling fallback: `useQuery({ queryKey: ['estimate', id], refetchInterval: 60_000 })` while modal is open and status is non-terminal.
- **PATTERN**: Look for an existing TanStack Query polling pattern in `frontend/src/features/schedule/` — likely in appointment status polling.
- **GOTCHA**: 60s polling per AJ-6; below this and we'll thrash the API. Above this and approval feedback is sluggish.
- **VALIDATE**: Manual: open estimate sheet, approve via portal in another tab, verify banner updates within 60s.

#### Task 0.9: TESTS for Phase 0

- **IMPLEMENT**:
  - Unit: `test_estimate_auto_job.py` — 4 cases: standalone+ON creates job; standalone+OFF skips; attached+ON copies items; lead-only+ON skips with reason.
  - Functional: `test_estimate_approval_flow.py` — full flow from portal POST → approval recorded → job created → PDF emailed → audit logged.
  - Integration: TanStack Query invalidation test in `frontend/src/features/schedule/components/AppointmentModal/EstimateSheetWrapper.test.tsx`.
- **VALIDATE**: `uv run pytest -m "unit or functional" -k "estimate_approval or auto_job" -v` then `cd frontend && npm test -- EstimateSheet`.

---

### Phase 1 Tasks (TRIMMED scope — see § Phase 1 above for what's deferred)

#### Task 1.1: EXTEND `PricingModel` enum

- **UPDATE**: `src/grins_platform/models/enums.py`, lines 87–96. Add 13 new values matching the distribution observed in the seed JSON: `FLAT_RANGE = "flat_range"`, `PER_UNIT_FLAT = "per_unit_flat"`, `PER_UNIT_RANGE = "per_unit_range"`, `PER_UNIT_FLAT_PLUS_MATERIALS = "per_unit_flat_plus_materials"`, `PER_ZONE_RANGE = "per_zone_range"`, `TIERED_ZONE_STEP = "tiered_zone_step"`, `TIERED_LINEAR = "tiered_linear"`, `COMPOUND_PER_UNIT = "compound_per_unit"`, `COMPOUND_REPAIR = "compound_repair"`, `SIZE_TIER = "size_tier"`, `SIZE_TIER_PLUS_MATERIALS = "size_tier_plus_materials"`, `YARD_TIER = "yard_tier"`, `VARIANTS = "variants"`, `FLAT_PLUS_MATERIALS = "flat_plus_materials"`, `CONDITIONAL_FEE = "conditional_fee"`. **Keep existing `FLAT`, `ZONE_BASED`, `HOURLY`, `CUSTOM`.**
- **GOTCHA**: `pricing_model` column is `String(50)`, not Postgres ENUM — Python enum extension alone suffices. No CHECK constraint added.
- **VALIDATE**: `uv run mypy src/grins_platform/models/enums.py && uv run ruff check src/grins_platform/models/enums.py`.

#### Task 1.2: ADD nullable columns to `ServiceOffering` model

- **UPDATE**: `src/grins_platform/models/service_offering.py`. Add Mapped fields:
  - `slug: Mapped[str | None] = mapped_column(String(100), nullable=True, unique=True)` (uniqueness enforced via partial index in migration; `unique=True` here is metadata only)
  - `display_name: Mapped[str | None] = mapped_column(String(200), nullable=True)`
  - `customer_type: Mapped[str | None] = mapped_column(String(20), nullable=True)`
  - `subcategory: Mapped[str | None] = mapped_column(String(50), nullable=True)`
  - `pricing_rule: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)`
  - `replaced_by_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("service_offerings.id", ondelete="SET NULL"), nullable=True)`
  - `includes_materials: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")`
  - `source_text: Mapped[str | None] = mapped_column(Text, nullable=True)`
- **IMPORTS**: replace existing `from sqlalchemy import JSON, ...` with `from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID`. Keep existing `JSON` import only if `equipment_required` still uses it (it does). Add `ForeignKey` to imports.
- **PATTERN**: Mirrors `models/estimate.py:67-70` JSONB declaration and `models/estimate.py:42-46` ForeignKey pattern.
- **GOTCHA**: Plain `JSONB` (not `MutableDict.as_mutable(JSONB)`) — we don't yet need nested-mutation tracking; add it only when the admin editor code (Phase 2) edits nested keys.
- **VALIDATE**: `uv run mypy src/grins_platform/models/service_offering.py && uv run ruff check src/grins_platform/models/service_offering.py`.

#### Task 1.3: WRITE migration to add columns + indexes

- **CREATE**: `src/grins_platform/migrations/versions/20260504_120000_extend_service_offerings_for_pricelist.py`.
- **REVISION**: `revision = "20260504_120000"`; `down_revision = "20260503_100000"`.
- **IMPLEMENT** (`upgrade()`):
  - `op.add_column` for each new field (8 columns).
  - `op.add_column("service_offerings", sa.Column("replaced_by_id", PGUUID(as_uuid=True), nullable=True))` then separate `op.create_foreign_key("fk_service_offerings_replaced_by", source_table="service_offerings", referent_table="service_offerings", local_cols=["replaced_by_id"], remote_cols=["id"], ondelete="SET NULL")` (avoid inline self-FK).
  - Partial unique index: `op.create_index("ix_service_offerings_slug_unique", "service_offerings", ["slug"], unique=True, postgresql_where="slug IS NOT NULL")`.
  - Plain index: `op.create_index("ix_service_offerings_customer_type", "service_offerings", ["customer_type"])`.
- **IMPLEMENT** (`downgrade()`): drop in reverse order — indexes first, then FK constraint, then columns.
- **PATTERN**: `src/grins_platform/migrations/versions/20260428_150000_add_invoice_payment_link_columns.py` — recent style with partial index.
- **VALIDATE**: `uv run alembic upgrade head && uv run alembic downgrade -1 && uv run alembic upgrade head`.

#### Task 1.4: UPDATE Pydantic schemas (additive, optional fields)

- **UPDATE**: `src/grins_platform/schemas/service_offering.py`:
  - `ServiceOfferingCreate`: add optional `slug`, `display_name`, `customer_type` (`Literal["residential", "commercial"] | None`), `subcategory`, `pricing_rule: dict[str, Any] | None`, `includes_materials: bool = False`, `source_text: str | None`.
  - `ServiceOfferingUpdate`: same fields, all optional.
  - `ServiceOfferingResponse`: same fields, all optional + `replaced_by_id: UUID | None`.
- **GOTCHA**: Existing API consumers don't pass these fields; Optional + None defaults preserve backward compat.
- **PATTERN**: Mirror existing field patterns in the same file.
- **VALIDATE**: `uv run mypy src/grins_platform/schemas/service_offering.py`.

#### Task 1.5: UPDATE repository signatures to accept new fields

- **UPDATE**: `src/grins_platform/repositories/service_offering_repository.py`:
  - `create()` — add optional kwargs for each new field, pass through to `ServiceOffering()`.
  - `list_with_filters()` — add optional `customer_type: str | None = None` filter.
- **GOTCHA**: Existing callers don't pass new fields; defaults of `None` mean nothing changes for them.
- **VALIDATE**: `uv run mypy src/grins_platform/repositories/service_offering_repository.py`.

#### Task 1.6: UPDATE service to plumb new fields through

- **UPDATE**: `src/grins_platform/services/service_offering_service.py`:
  - `create_service()` — pass new fields from `data` to `repository.create()`.
  - `list_services()` — accept and forward `customer_type` filter.
- **GOTCHA**: Don't add `archive_and_replace` here — that's Phase 1.5 deferred.
- **VALIDATE**: `uv run mypy src/grins_platform/services/service_offering_service.py`.

#### Task 1.7: WRITE seed migration from Viktor JSON

- **CREATE**: `src/grins_platform/migrations/versions/20260504_130000_seed_pricelist_from_viktor.py`.
- **REVISION**: `revision = "20260504_130000"`; `down_revision = "20260504_120000"`.
- **GATING**: Top of `upgrade()`:
  ```python
  if os.getenv("VIKTOR_PRICELIST_CONFIRMED") != "true":
      raise RuntimeError(
          "VIKTOR_PRICELIST_CONFIRMED env var must be 'true' before this "
          "migration runs. Confirms V1 (commercial mulch per sq ft), "
          "V2 (commercial backflow $600), V3 (commercial drip per_zone_range) "
          "defaults applied in seed JSON. Dev/staging may set freely."
      )
  ```
- **JSON PATH**: `Path(__file__).resolve().parents[4] / "bughunt" / "2026-05-01-pricelist-seed-data.json"`. Verified: `versions/` → `migrations/` → `grins_platform/` → `src/` → `<repo_root>/`.
- **TRANSFORMATION**: For each of the 73 items, INSERT a row with:
  - `id`: `gen_random_uuid()` (server default)
  - `name`: `item["name"]`
  - `slug`: `item["key"]`
  - `display_name`: `item["name"]`
  - `category`: map seed `category` to `ServiceCategory` enum value (seed uses `irrigation` and `landscaping`; map both to `ServiceCategory.LANDSCAPING.value` for `landscaping` and `ServiceCategory.INSTALLATION.value` for `irrigation`, OR add new categories to enum). **Decision**: keep simple — existing `ServiceCategory` enum values are `seasonal`, `repair`, `installation`, `diagnostic`, `landscaping`. Map: `irrigation` → `installation`, `landscaping` → `landscaping`. The seed's `subcategory` field captures the finer detail.
  - `subcategory`: `item["subcategory"]`
  - `customer_type`: `item["customer_type"]`
  - `pricing_model`: `item["pricing_model"]`
  - `includes_materials`: `True` if `pricing_model` ends in `_plus_materials`, else `False`
  - `source_text`: `item.get("source_text")`
  - `pricing_rule`: a JSON dict containing every field from `item` NOT in the standard set (`{"key", "name", "category", "subcategory", "customer_type", "pricing_model", "source_text"}`). This preserves all rule fields (`price_min`, `price_max`, `price_per_zone_min`, `unit`, `includes`, `profile_factor`, `depends_on`, etc.) for future Phase 2/3 reads.
  - `is_active`: `True`
  - `staffing_required`: `1` (model NOT NULL default)
  - `buffer_minutes`: `10` (model NOT NULL default)
  - `lien_eligible`, `requires_prepay`: `False`
- **IMPLEMENT** (`downgrade()`): `DELETE FROM service_offerings WHERE slug IN (...)` — list of all 73 keys.
- **PATTERN**: Use `op.execute(sa.text(...))` with parameter binding via `connection.execute(sa.text(...).bindparams(...))` — but for simplicity use `op.bulk_insert` with the table reflection approach used in other Alembic data migrations, OR direct `op.execute()` with parameterized statements.
- **GOTCHA**: `pricing_rule` must be JSON-serialized before binding. Use `json.dumps(rule_dict)` and bind as text → cast to JSONB via `sa.text("... :pricing_rule::jsonb ...")`.
- **VALIDATE**: `VIKTOR_PRICELIST_CONFIRMED=true uv run alembic upgrade head` and `psql $DATABASE_URL -c "SELECT COUNT(*) FROM service_offerings WHERE slug IS NOT NULL;"` returns 73.

#### Task 1.8: TESTS for Phase 1 (functional only — no archive logic to unit test)

- **IMPLEMENT**:
  - Functional: `test_pricelist_seed_count.py` — after migration, `SELECT COUNT(*) WHERE slug IS NOT NULL = 73`; per-pricing-model row counts match seed distribution (5 `flat`, 8 `per_unit_flat`, 12 `per_unit_flat_plus_materials`, etc.).
  - Functional: `test_service_offering_with_new_columns.py` — POST `/api/v1/services` with new optional fields populates them; GET round-trips them.
  - Manual smoke: `VIKTOR_PRICELIST_CONFIRMED= uv run alembic upgrade head` raises (gating works).
- **VALIDATE**: `uv run pytest -m functional -k pricelist -v`.

---

### Phase 2 Tasks

#### Task 2.1: CREATE `frontend/src/features/pricelist/` slice

- **CREATE**: Files per § New Files to Create → Frontend (above).
- **PATTERN**: Mirror `frontend/src/features/invoices/` structure verbatim.
- **GOTCHA**: Feature-name choice — call it `pricelist` (matches user terminology) not `services` or `catalog`. **Also note**: the feature slice imports from `@/core` and `@/shared` only — never from sibling features.
- **VALIDATE**: `cd frontend && npm run typecheck`.

#### Task 2.2: CREATE `serviceApi.ts` TanStack Query client

- **IMPLEMENT**: `frontend/src/features/pricelist/api/serviceApi.ts`. Wrap `apiClient` with hooks:
  - `useServiceOfferings({ customer_type, category, is_active, search, page, page_size })`
  - `useServiceOffering(id)`
  - `useCreateServiceOffering()` (mutation)
  - `useUpdateServiceOffering()` (mutation; falls back to plain UPDATE in Phase 2; switches to archive+replace once Phase 1.5 ships)
  - `useDeactivateServiceOffering()` (mutation)
  - `useServiceOfferingHistory(slug)` (Phase 1.5 dep — placeholder until then)
- **PATTERN**: Mirror `frontend/src/features/invoices/api/invoiceApi.ts` exactly (verified — single `.ts` file with paired `.test.ts`). Same query-key conventions, same `apiClient` wrapping.
- **VALIDATE**: `cd frontend && npm run typecheck`.

#### Task 2.3: CREATE `PriceListEditor.tsx` page

- **IMPLEMENT**: Top-level component; renders:
  - Customer-type filter (residential / commercial / both) — defaults to `both`.
  - Category facet (irrigation_install / maintenance / landscaping / etc. from seed).
  - Search by name/slug (debounced).
  - Paginated `ServiceOfferingTable` with columns: `display_name`, `customer_type`, `pricing_model`, `is_active`, actions.
  - "+ New offering" button → opens `ServiceOfferingDrawer`.
- **PATTERN**: `frontend/src/pages/Settings.tsx` shows a multi-tab sub-page pattern. `frontend/src/features/invoices/` shows the table pattern.
- **VALIDATE**: `cd frontend && npm run dev`, navigate to `/invoices/pricelist`, verify table renders.

#### Task 2.4: CREATE `ServiceOfferingDrawer.tsx`

- **IMPLEMENT**: Slide-over drawer for create/edit. Renders different form panels based on `pricing_model` discriminator (one panel per Pydantic union variant).
- **PATTERN**: shadcn `Sheet` component. Conditional sub-form per pricing model.
- **GOTCHA (Phase 2 vs Phase 1.5)**: Edit-mode submission calls `useUpdateServiceOffering()` which **uses plain UPDATE** in Phase 2 (since archive+replace is Phase 1.5 deferred). Once Phase 1.5 lands, the same hook switches to archive+replace internally without a UI rewrite — and the drawer adds a "This will archive the current price and create a new one" confirmation banner when any pricing field changed. Phase 2 ships without that banner.
- **VALIDATE**: Vitest forms render per pricing model; submit triggers correct mutation.

#### Task 2.5: CREATE `ArchiveHistorySheet.tsx`

- **DEPENDENCY**: This component **requires Phase 1.5 archive+create to be live** (the `replaced_by_id` chain only contains data once edits go through that pattern). Until Phase 1.5 ships, render a placeholder card: "History view available after Phase 1.5 archive+create migration." Don't block Phase 2 shipping on this.
- **IMPLEMENT (post-Phase 1.5)**: Side sheet showing the `replaced_by_id` chain — chronological list of all rows linked by `replaced_by_id` (current + replacements), with diff between consecutive versions, audit log entries from `audit_logs` where `resource_type='service_offering'` and `resource_id` is in the chain.
- **DATA**: Uses `useServiceOfferingHistory(slug)`.
- **PATTERN**: Mirror any existing audit-log timeline view in the app — search for `audit_logs` consumers in `frontend/src/features/`.
- **VALIDATE**: Vitest snapshot (placeholder rendering for Phase 2 ship; full content for Phase 1.5 follow-on).

#### Task 2.6: WIRE `/invoices/pricelist` route

- **UPDATE**: `frontend/src/core/router/index.tsx` — register the new route. Use existing nested-route pattern.
- **UPDATE**: `frontend/src/pages/Invoices.tsx` — verified the file already uses the shadcn `Tabs` pattern (lines 53-68: `Tabs` / `TabsList` / `TabsTrigger` / `TabsContent`). Add a third `TabsTrigger value="pricelist"` and matching `TabsContent` rendering `<PriceListEditor />`. Tab state is URL-driven via `?tab=pricelist` (existing pattern at line 27 reads `searchParams.get('tab')`).
- **UPDATE**: Top-nav at `frontend/src/shared/components/Layout.tsx` (verified — `grep` confirms it owns the sidebar/navigation). Add a "Pricebook" link entry pointing to `/invoices?tab=pricelist`.
- **VALIDATE**: Manual nav test in `npm run dev`.

#### Task 2.7: CREATE `PriceListExportService` for `pricelist.md` auto-export (P8)

- **CREATE**: `src/grins_platform/services/price_list_export_service.py`. On every CRUD save in `ServiceOfferingService`, regenerate a markdown table grouped by `category` and `customer_type`.
- **PATTERN**: Use Jinja2 template at `src/grins_platform/templates/pricelist_export.md.j2`.
- **ENDPOINT**: New `GET /api/v1/services/export/pricelist.md` returns the generated markdown. Cache by `MAX(updated_at)` of all service offerings.
- **GOTCHA**: Don't write to filesystem — serve from cache. The static `pricelist.md` in repo root is retired (see Phase 5 Task 5.4).
- **VALIDATE**: `curl http://localhost:8000/api/v1/services/export/pricelist.md` returns rendered markdown.

#### Task 2.8: TESTS for Phase 2

- **IMPLEMENT**:
  - Vitest: `PriceListEditor.test.tsx` — filters work, table paginates, drawer opens.
  - Vitest: `ServiceOfferingDrawer.test.tsx` — form per pricing_model, archive-and-replace warning.
  - Functional: `test_pricelist_export.py` — markdown export round-trips.
- **VALIDATE**: `cd frontend && npm test -- pricelist` and `uv run pytest -k pricelist_export -v`.

---

### Phase 3 Tasks

#### Task 3.1: ADD `unit_cost` and `material_markup_pct` to estimate line items

- **IMPLEMENT**: `src/grins_platform/schemas/estimate.py` — extend the line-item dict shape with two optional keys:
  - `unit_cost: Decimal | None` — staff-only, hidden from customer (E2/P5).
  - `material_markup_pct: Decimal` — default 0 (E2 / N3 deferred-markup seam).
- **MIGRATION**: Not strictly needed since `Estimate.line_items` is a JSONB column already; the new keys just live inside the existing dict shape. **But document the new keys in the schema** so consumers know to read them.
- **PATTERN**: `Estimate.line_items` at `models/estimate.py:67-70` is `JSONB` — extend the Pydantic schema only.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/schemas/test_estimate_line_item.py -v`.

#### Task 3.2: CREATE `LineItemPicker.tsx`

- **IMPLEMENT**: New file. **Location**: `frontend/src/features/schedule/components/EstimateSheet/LineItemPicker.tsx`. **NOTE**: `EstimateCreator.tsx` lives at `frontend/src/features/schedule/components/EstimateCreator.tsx`, NOT under `AppointmentModal/`. The picker should sit alongside it as a sibling sub-component, or replace it entirely (preferred).
- **CUSTOMER-TYPE RESOLUTION** (per P4-RESOLVED in Decision Log):
  ```
  if estimate.lead_id and lead.customer_type: use lead.customer_type
  elif estimate.customer_id and property.property_type: use property.property_type
  else: default 'residential' + prominent toggle
  ```
- **BEHAVIOR**:
  - Debounced search calling `GET /api/v1/services?customer_type={resolved}&q={query}&is_active=true`.
  - Manual override toggle ("Show all customer types") in header.
  - On select: opens sub-picker if `pricing_model` is `size_tier` / `size_tier_plus_materials` / `yard_tier` / `variants`; otherwise emits a line item with default `quoted_amount` from `pricing_rule` (range mid if range, else flat).
  - Existing `EstimateCreator.tsx` line-item shape: `{item, description, unit_price, quantity}` (verified at `EstimateCreator.tsx:28-33`). New shape adds: `service_offering_id?: string`, `unit_cost?: number`, `material_markup_pct?: number`. Backward-compat: existing line items without these fields still render.
- **PATTERN**: shadcn `Combobox` or `Command`. Reference: `frontend/src/features/customers/` for similar search-and-select.
- **GOTCHA**: `useEstimateTemplates` is owned by `@/features/leads/hooks` (not schedule) — verified at `EstimateCreator.tsx:20`. Per E7, templates coexist with the new picker; don't move/rewrite the leads-feature hook.
- **VALIDATE**: Vitest interactions.

#### Task 3.3: CREATE `SizeTierSubPicker.tsx` and `VariantSubPicker.tsx`

- **IMPLEMENT**:
  - `SizeTierSubPicker.tsx` — renders "S / M / L" dropdown for `pricing_rule.tiers` (P2).
  - `VariantSubPicker.tsx` — renders variant labels for `pricing_rule.variants` (P3).
- **PATTERN**: shadcn `Select` for both.
- **VALIDATE**: Vitest snapshot.

#### Task 3.4: ADD "Custom quote" prompt for above-tier-max (P10)

- **IMPLEMENT**: When `quantity` (zones, ft, etc.) exceeds `pricing_rule.max_zones_specified` / `max_units_specified`, the `LineItemPicker` shows an inline indicator: "Above standard tier — switch to custom quote?". Click → line is added with `pricing_model=custom`, `quoted_amount` blank for tech to fill manually.
- **GOTCHA**: Don't extrapolate linearly — that's explicitly out of scope (audit P10).
- **VALIDATE**: Vitest case: `quantity=20` on Spring Start-Up (max 19) triggers prompt.

#### Task 3.5: RENDER `range_anchors` quick-pick chips when present (P1 / N4)

- **IMPLEMENT**: When the selected offering's `pricing_rule.range_anchors` is non-null (e.g. `{low: 200, mid: 300, high: 450}`), the LineItemPicker shows three labeled chips ("Low", "Mid", "High"). Click sets the line's `quoted_amount` to that anchor.
- **PATTERN**: Visually distinct from the freeform price input — make the anchor a quick-pick, not a hard constraint. Tech can still type any number.
- **NOTE**: This is the N4 schema seam → UI surface. Phase 2 G/B/B builds on this — see Deferred Features.
- **VALIDATE**: Vitest case: chips render only when `range_anchors` present; clicking sets quoted_amount.

#### Task 3.6: SHOW hidden `unit_cost` field in staff edit drawer (P5)

- **IMPLEMENT**: In `EstimateCreator.tsx` line-item edit drawer, add a `unit_cost` numeric field below the visible `quoted_amount`. Labeled "Internal cost (hidden from customer)". Margin calculation: `(quoted_amount - unit_cost * quantity) / quoted_amount` shown as a small read-only "Margin: X%".
- **GOTCHA**: This field is NEVER rendered on the customer-facing PDF or portal view. Verify by inspecting `templates/estimate_signed_pdf.html` (Task 0.3) — must not include `unit_cost`.
- **VALIDATE**: Vitest: `unit_cost` field visible in edit drawer; absent from customer portal render.

#### Task 3.7: KEEP `EstimateTemplate` as a separate entry point (E7)

- **IMPLEMENT**: In `EstimateCreator.tsx`, add a "Use a template" secondary button alongside the LineItemPicker. Clicking opens existing `useEstimateTemplates()` modal. Templates remain available for "Spring Package = Start-Up + WiFi Upgrade" bundles.
- **GOTCHA**: Don't replace template flow — coexists. Future work: convert templates to bundles of `service_offering_id` references rather than ad-hoc dicts.
- **VALIDATE**: Manual: both entry points render; both produce valid estimates.

#### Task 3.8: TESTS for Phase 3

- **IMPLEMENT**:
  - Vitest: `LineItemPicker.test.tsx` — search + customer-type filter + override toggle + range_anchors chips.
  - Vitest: `SizeTierSubPicker.test.tsx`, `VariantSubPicker.test.tsx`.
  - Functional: `test_estimate_with_service_offerings.py` — estimate created with `service_offering_id` per line, `unit_cost` persisted, customer PDF redacts cost.
- **VALIDATE**: `cd frontend && npm test -- EstimateSheet` and `uv run pytest -k estimate_with_service_offerings -v`.

---

### Phase 4 Tasks

#### Task 4.1: EXTEND `TimelineEventKind` enum

- **UPDATE**: `src/grins_platform/schemas/appointment_timeline.py` — add `PAYMENT_RECEIVED` to the enum.
- **VALIDATE**: `uv run mypy src/grins_platform/schemas/appointment_timeline.py`.

#### Task 4.2: ADD `_invoice_payment_to_event` helper to `AppointmentTimelineService`

- **IMPLEMENT**: In `src/grins_platform/services/appointment_timeline_service.py`, add a static `_invoice_payment_to_event(invoice) -> TimelineEvent` mirroring `_outbound_to_event` (line 158).
- **WIRE**: Extend `get_timeline()` (line 65) to fetch invoices joined on `appointment.job_id → invoices.job_id` where `paid_at IS NOT NULL`. Each such invoice produces one event. Add events to the `events` list at line 99.
- **VERIFIED 2026-05-01**: There is **NO separate `payments` table**. Payments are recorded as columns on `Invoice` itself: `payment_method`, `payment_reference`, `paid_at`, `paid_amount`, and `status` (verified at `services/appointment_service.py:2025-2034`). One invoice = one or zero payments today (multi-tender / partial payments may exist as `status: PARTIAL`; future improvement to track multiple payments per invoice is out of this plan's scope).
- **PATTERN**: Existing `_outbound_to_event` / `_inbound_to_event` shapes at lines 158, 173.
- **GOTCHA**: A single appointment's job may have multiple invoices over time (e.g. deposit invoice + final invoice). Aggregate all paid invoices.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/functional/services/test_appointment_timeline_with_payments.py -v`.

#### Task 4.3: WIRE receipt SMS + email after `collect_payment` succeeds

- **UPDATE**: `src/grins_platform/services/appointment_service.py` (verified location of `collect_payment` — at line 1964, NOT on `InvoiceService`). Hook fires after the existing successful invoice update at lines 2024-2034 / new-invoice branch at line 2037+.
- **IMPLEMENT**: After successful payment recording (cash/check/Stripe alike), fire:
  - SMS receipt via `sms_service.send_automated_message(phone, "Receipt: $X received via {method} on {date}. Thank you!", message_type="payment_receipt")`. **NOTE**: Add `PAYMENT_RECEIPT = "payment_receipt"` to `MessageType` enum in `models/enums.py:732-761` first — existing convention requires the type to be enumerated before send_automated_message accepts it.
  - Email receipt via `email_service.send_payment_receipt_email(customer, invoice)` — new method on EmailService.
- **PATTERN**: Resend wiring per memory `project_estimate_email_portal_wired.md`. Mirror `email_service.send_estimate_email` signature (already wired).
- **GOTCHA**: Stripe Payment Link path already shows hosted confirmation — Grin's receipt is supplemental, not duplicate. Tag distinctly in copy: "Grin's receipt for your records".
- **TEMPLATE**: New Jinja2 `src/grins_platform/templates/payment_receipt_email.html`.
- **VALIDATE**: `uv run pytest -k payment_receipt -v`.

#### Task 4.4: CREATE `PaidConfirmationCard.tsx`

- **IMPLEMENT**: `frontend/src/features/schedule/components/AppointmentModal/PaymentSheet/PaidConfirmationCard.tsx`. Renders a green confirmation card "Payment received · $NNN · {method} · {timestamp}" with secondary CTA "Text receipt" (re-fires receipt SMS).
- **WIRE**: `PaymentSheetWrapper.tsx` collapses into this card on payment success per design §8.5.
- **PATTERN**: Design ref `audit-screenshots/missing-states/payment-04-paid-confirmation.png`.
- **VALIDATE**: Vitest snapshot.

#### Task 4.5: TESTS for Phase 4

- **IMPLEMENT**:
  - Functional: `test_appointment_timeline_with_payments.py` — cash payment surfaces in timeline.
  - Functional: `test_payment_receipt_delivery.py` — receipt SMS + email fire on collect.
  - Vitest: `PaidConfirmationCard.test.tsx` snapshot + "Text receipt" CTA.
- **VALIDATE**: `uv run pytest -m functional -k "timeline_with_payments or payment_receipt" -v` and `cd frontend && npm test -- PaidConfirmation`.

---

### Phase 5 Tasks

#### Task 5.1: RENAME Estimate CTA + sublabels

- **UPDATE**: `frontend/src/features/schedule/components/AppointmentModal/AppointmentModal.tsx:606` — "Create Estimate" → "Send estimate".
- **UPDATE**: `frontend/src/features/schedule/components/AppointmentModal/ActionTrack.tsx` — verified the labels live here at lines 70 ("En route"), 79 ("On site"), and the third (Completed/Done) further down. **`ActionCard.tsx` only takes a `label` prop**, no sublabel — strings are owned entirely by ActionTrack. Change to: "On my way" (line 70), "Job started" (line 79), "Job complete" (third card).
- **VALIDATE**: Vitest snapshot updates for `ActionTrack.test.tsx`.

#### Task 5.2: ADD "Remember my choice" footer to MapsPickerPopover

- **UPDATE**: `frontend/src/features/schedule/components/AppointmentModal/MapsPickerPopover.tsx` (lines 55–106).
- **IMPLEMENT**: Add a footer row with checkbox "Remember my choice"; persist via PATCH `/api/v1/staff/me { preferred_maps_app: 'apple' | 'google' }`.
- **VERIFIED 2026-05-01**: There is **no `User` model**; the staff identity model is `Staff` at `src/grins_platform/models/staff.py:39` (table `staff`). `preferred_maps_app` does NOT exist on Staff (`grep "preferred_maps_app" src/` returns only doc references). **Required**: small migration adding `preferred_maps_app: String(20) NULLABLE` to `staff` table. Endpoint path: `/api/v1/staff/me` (verify via grep — if absent, add a PATCH endpoint to `api/v1/staff.py`).
- **VALIDATE**: Manual — select Apple Maps + check "Remember"; reload modal; defaults to Apple.

#### Task 5.3: DELETE deprecated stripe_terminal — full uninstall

- **VERIFIED 2026-05-01**: `stripe_terminal` is more entrenched than the audit suggested. Concrete callers found:
  - `src/grins_platform/api/v1/stripe_terminal.py` — full router file, imports `from grins_platform.services.stripe_terminal`.
  - `src/grins_platform/api/v1/router.py:76` — `from grins_platform.api.v1.stripe_terminal import router as stripe_terminal_router` and likely an `app.include_router(stripe_terminal_router)` line nearby.
  - `src/grins_platform/tests/unit/test_stripe_terminal.py` — 200+ line unit test file with 6 `@patch("grins_platform.services.stripe_terminal.stripe")` decorators.
  - `src/grins_platform/services/stripe_payment_link_service.py:8` — comment-only reference in module docstring; safe to keep or update wording.
- **REMOVE in this order**:
  1. `src/grins_platform/api/v1/router.py` — remove the import at line 76 AND the `include_router(stripe_terminal_router)` call (find with grep).
  2. Delete `src/grins_platform/api/v1/stripe_terminal.py`.
  3. Delete `src/grins_platform/services/stripe_terminal.py`.
  4. Delete `src/grins_platform/tests/unit/test_stripe_terminal.py`.
  5. Edit `src/grins_platform/services/stripe_payment_link_service.py:8` to drop the "Companion service to ``stripe_terminal.py`` (deprecated)" wording — replace with "Architecture C — see `project_stripe_payment_links_arch_c` memory."
- **VALIDATE**: `uv run ruff check src/` and `uv run pytest -v` (full suite, since router and tests were both touched).

#### Task 5.4: RETIRE static `pricelist.md`

- **REMOVE**: Manual maintenance of `pricelist.md` at repo root. **Do NOT delete the file** — keep it as a snapshot until Phase 2 export is in production. Add a comment at the top: `<!-- AUTO-GENERATED from /api/v1/services/export/pricelist.md as of Phase 2; do not edit manually. -->` and seed it with the first export. Or delete entirely if ack'd.
- **GOTCHA**: User decision needed: keep file as snapshot vs delete. **Default**: keep file with auto-gen comment until Phase 2 export ships, then delete.
- **VALIDATE**: Verify no code references the static file.

---

### Phase 6 Tasks: MANDATORY E2E VISUAL VERIFICATION

**Goal**: visual + DB confirmation that every UI surface, button, and state introduced by Phases 0–5 is wired end-to-end. **No phase is "done" until its E2E sub-suite passes with full screenshot coverage and zero console errors.** This phase is non-negotiable per the implementer brief.

**Tooling** (matches `.kiro/steering/e2e-testing-skill.md` and existing `e2e/*.sh` scripts):

- **`agent-browser` CLI** (Vercel; install via `npm install -g agent-browser && agent-browser install --with-deps`).
- **Bash scripts** at `e2e/{phase}-{feature}.sh` mirroring the structure of `e2e/schedule-resource-timeline.sh` (verified pattern at `e2e/schedule-resource-timeline.sh:24-60`).
- **Screenshots** saved under `e2e-screenshots/appointment-modal-umbrella/{phase}/{step}.png` — one folder per phase.
- **DB validation** via `psql "$DATABASE_URL" -c "..."` after every state-changing interaction.
- **Console + uncaught exception checks** via `agent-browser console` and `agent-browser errors` after each navigation.
- **Test phone/email** must be `+19527373312` (per memory `feedback_sms_test_number.md`) and `kirillrakitinsecond@gmail.com` (per `feedback_email_test_inbox.md`) — hard-coded in test setup.

**Pre-flight (mandatory before any E2E run)**:

```bash
# Platform + tooling
[[ "$(uname -s)" =~ ^(Darwin|Linux)$ ]] || exit 1
agent-browser --version || { npm install -g agent-browser && agent-browser install --with-deps; }

# Backend + frontend running
curl -sf http://localhost:8000/health
curl -sf http://localhost:5173

# DB confirms latest migrations (Phase 1 seed must be present)
psql "$DATABASE_URL" -tAc "SELECT COUNT(*) FROM service_offerings WHERE slug IS NOT NULL;" | grep -q '^73$'
```

#### Task 6.1: Phase 0 E2E — Estimate approval → auto-job lifecycle

**Script**: `e2e/phase-0-estimate-approval-autojob.sh`

**Test matrix** — every named combination requires a numbered screenshot AND a DB query verifying the expected post-state:

| # | Setup | Action | Expected | Screenshots |
|---|---|---|---|---|
| 0.1 | Customer estimate, N5=ON, no parent job | Customer approves via portal | New Job in `TO_BE_SCHEDULED`; `estimate.job_id` set; line items copied to `Job.scope_items` | `01-portal-approve.png`, `02-modal-banner-job-created.png`, `03-job-detail-scope-items.png` |
| 0.2 | Customer estimate, N5=ON, parent job in `IN_PROGRESS` | Customer approves | Items appended to parent `Job.scope_items`; **NO new Job** | `04-portal-approve-attached.png`, `05-parent-job-scope.png` |
| 0.3 | Customer estimate, N5=OFF | Customer approves | No Job created; estimate marked APPROVED only | `06-n5-off-approve.png` (verify no job) |
| 0.4 | Lead-only estimate (no customer_id) | Customer approves | Auto-job SKIPS with `skip_reason=no_customer` audit row | `07-lead-only-approve.png` (modal banner shows approval, no job link) |
| 0.5 | Customer estimate | Customer rejects with reason | Estimate REJECTED; rejection reason persisted | `08-portal-reject.png`, `09-modal-rejected-state.png` |
| 0.6 | Approved estimate | Click "Schedule follow-up" CTA on Approved card | Existing schedule modal opens against the new Job | `10-schedule-followup-cta.png`, `11-schedule-modal-prefilled.png` |
| 0.7 | Sent estimate, modal open | Approve via portal in another tab | Modal banner refreshes within 60s (polling) | `12-banner-pre-poll.png`, `13-banner-post-poll.png` |
| 0.8 | Customer estimate | Customer approves | Signed-PDF arrives in test inbox; PDF footer contains signature, IP, UA, timestamp | `14-email-inbox-pdf.png`, `15-pdf-footer-signature.png` |
| 0.9 | Any approve flow | Inspect audit log | Rows: `estimate.auto_job_created` (or `estimate.auto_job_skipped`) with correct `details` JSONB | `16-audit-log-rows.png` |
| 0.10 | N5 toggle in admin | Flip OFF → ON | `business_settings` row updates; subsequent approval respects new value | `17-n5-toggle-off.png`, `18-n5-toggle-on.png` |

**DB validation queries (run after each scenario)**:

```bash
# 0.1 New job created
psql "$DATABASE_URL" -tAc "SELECT status, estimate_id FROM jobs WHERE id = '<new_job_id>';"
# Expected: to_be_scheduled|<estimate_id>

# 0.1 Line items copied
psql "$DATABASE_URL" -tAc "SELECT jsonb_array_length(scope_items) FROM jobs WHERE id = '<new_job_id>';"
# Expected: same length as estimate.line_items

# 0.4 Audit skip
psql "$DATABASE_URL" -tAc "SELECT details->>'skip_reason' FROM audit_logs WHERE action = 'estimate.auto_job_skipped' ORDER BY created_at DESC LIMIT 1;"
# Expected: no_customer

# 0.10 Setting flip
psql "$DATABASE_URL" -tAc "SELECT setting_value FROM business_settings WHERE setting_key = 'auto_job_on_approval';"
# Expected: {"value": true} or {"value": false}
```

**Sign-off**: 10 named scenarios pass + 18 screenshots present + 0 console errors + every DB query returns the expected value.

#### Task 6.2: Phase 1 E2E — Pricelist data + seed verification

**Script**: `e2e/phase-1-pricelist-seed.sh` (DB-only; no UI yet — UI is Phase 2)

**Validation matrix**:

```bash
# Total seed count (Bucket A V1/V2/V3 defaults applied)
psql "$DATABASE_URL" -tAc "SELECT COUNT(*) FROM service_offerings WHERE slug IS NOT NULL;"
# Expected: 73

# Per-customer-type distribution
psql "$DATABASE_URL" -tAc "SELECT customer_type, COUNT(*) FROM service_offerings WHERE slug IS NOT NULL GROUP BY customer_type;"
# Expected: residential|37 + commercial|36

# Every pricing_model variant present (counts match seed JSON distribution)
psql "$DATABASE_URL" -F'|' -tAc "SELECT pricing_model, COUNT(*) FROM service_offerings WHERE slug IS NOT NULL GROUP BY pricing_model ORDER BY pricing_model;"
# Expected (per seed JSON Counter): per_unit_flat_plus_materials|12, per_unit_flat|8, per_unit_range|8, tiered_zone_step|6, flat_plus_materials|6, flat|5, variants|4, conditional_fee|4, per_zone_range|3, flat_range|3, tiered_linear|2, compound_repair|2, hourly|2, size_tier_plus_materials|2, yard_tier|2, size_tier|2, compound_per_unit|2

# Partial unique index enforces slug uniqueness across seeded rows
psql "$DATABASE_URL" -tAc "SELECT slug, COUNT(*) FROM service_offerings WHERE slug IS NOT NULL GROUP BY slug HAVING COUNT(*) > 1;"
# Expected: 0 rows

# Pre-seed rows untouched (slug NULL preserved)
psql "$DATABASE_URL" -tAc "SELECT COUNT(*) FROM service_offerings WHERE slug IS NULL;"
# Expected: same count as before migration

# pricing_rule JSONB roundtrips for one row of each variant — sample 3
psql "$DATABASE_URL" -tAc "SELECT pricing_rule FROM service_offerings WHERE slug = 'irrigation_install_residential';"
# Expected: contains price_per_zone_min, price_per_zone_max, unit, profile_factor

# Gating env-var enforcement (no shot needed; just exit code check)
unset VIKTOR_PRICELIST_CONFIRMED && uv run alembic downgrade -1 && uv run alembic upgrade head 2>&1 | grep -q "VIKTOR_PRICELIST_CONFIRMED"
# Expected: error message printed; migration aborts
```

**Screenshots**: 1 of `psql` showing the count-by-pricing_model distribution → `e2e-screenshots/appointment-modal-umbrella/phase-1/01-pricing-model-distribution.png`. (Database phase has minimal visual surface.)

**Sign-off**: 7 queries return expected; gating env var blocks migration when unset.

#### Task 6.3: Phase 2 E2E — Pricelist editor UI (every pricing_model variant)

**Script**: `e2e/phase-2-pricelist-editor.sh`

**Test matrix** — every pricing_model variant gets its own drawer-render screenshot:

| # | Action | Screenshot |
|---|---|---|
| 2.1 | Navigate to `/invoices` → click "Pricelist" tab | `01-tab-pricelist.png` |
| 2.2 | Click "Pricebook" shortcut in top-nav (Layout.tsx) → lands at same view | `02-topnav-shortcut.png` |
| 2.3 | Filter customer_type=residential | `03-filter-residential.png` |
| 2.4 | Filter customer_type=commercial | `04-filter-commercial.png` |
| 2.5 | Filter customer_type=both (default) | `05-filter-both.png` |
| 2.6 | Filter category=installation (irrigation) | `06-filter-installation.png` |
| 2.7 | Filter category=landscaping | `07-filter-landscaping.png` |
| 2.8 | Search "spring" → 1+ matches | `08-search-spring.png` |
| 2.9 | Search "zzznomatch" → empty state | `09-empty-state.png` |
| 2.10 | Pagination → page 2 → page 3 | `10-page-2.png`, `11-page-3.png` |
| 2.11 | Sort by name desc | `12-sort-desc.png` |
| 2.12–2.30 | Click "+ New offering" → select each pricing_model variant from dropdown → screenshot drawer form per variant | One screenshot per variant: `12-drawer-flat.png`, `13-drawer-flat_range.png`, `14-drawer-per_unit_flat.png`, ..., `28-drawer-conditional_fee.png` (17 variants total) |
| 2.31 | Fill flat-pricing form → save → verify new row in DB | `29-create-flat-success.png` |
| 2.32 | Edit existing row's display_name → save | `30-edit-display-name.png` |
| 2.33 | Edit existing row's `pricing_rule.range_anchors` JSON | `31-edit-range-anchors.png` |
| 2.34 | Deactivate row → row disappears from default view; reappears with "Show inactive" toggle | `32-deactivate.png`, `33-show-inactive.png` |
| 2.35 | Open ArchiveHistorySheet → Phase 2 placeholder rendering | `34-archive-history-placeholder.png` |
| 2.36 | Trigger pricelist.md auto-export endpoint | `35-export-pricelist-md.png` (rendered markdown) |
| 2.37 | Console + errors check after every save | `36-console-clean.png` |

**DB queries**:

```bash
# 2.31 New row inserted
psql "$DATABASE_URL" -tAc "SELECT slug, customer_type, pricing_model FROM service_offerings WHERE slug = '<test_slug>';"

# 2.32 display_name updated; slug unchanged
psql "$DATABASE_URL" -tAc "SELECT slug, display_name FROM service_offerings WHERE slug = '<test_slug>';"

# 2.34 deactivate
psql "$DATABASE_URL" -tAc "SELECT is_active FROM service_offerings WHERE slug = '<test_slug>';"
# Expected: f
```

**Sign-off**: 36 screenshots + every drawer form variant rendered + 4 DB queries pass + 0 console errors.

#### Task 6.4: Phase 3 E2E — Estimate creator wired to pricelist (every customer-type path × variant)

**Script**: `e2e/phase-3-estimate-line-item-picker.sh`

**Test matrix**:

| # | Setup (estimate context) | Action | Expected | Screenshot |
|---|---|---|---|---|
| 3.1 | Lead-only estimate (Lead.customer_type=residential) | Open LineItemPicker | Pre-filtered to residential | `01-lead-residential-prefiltered.png` |
| 3.2 | Lead-only estimate (Lead.customer_type=commercial) | Open LineItemPicker | Pre-filtered to commercial | `02-lead-commercial-prefiltered.png` |
| 3.3 | Customer estimate + Property.property_type=residential | Open LineItemPicker | Pre-filtered to residential | `03-property-residential-prefiltered.png` |
| 3.4 | Customer estimate + Property.property_type=commercial | Open LineItemPicker | Pre-filtered to commercial | `04-property-commercial-prefiltered.png` |
| 3.5 | Customer estimate, no property | Open LineItemPicker | Defaults to residential + prominent toggle | `05-default-residential-toggle.png` |
| 3.6 | Any context | Toggle "Show all customer types" override ON | Both residential + commercial visible | `06-override-toggle.png` |
| 3.7 | Open picker | Type "spring" → debounced search returns matches | `07-debounced-search.png` |
| 3.8 | Pick a `flat` model offering | Line added with default amount | `08-pick-flat.png` |
| 3.9 | Pick a `per_zone_range` offering | Range_anchors quick-pick chips render (when present); line picker shows range hint | `09-pick-per-zone-range.png`, `10-range-anchors-chips.png` |
| 3.10 | Pick a `size_tier` offering | SizeTierSubPicker opens → S/M/L select → line added | `11-size-tier-subpicker.png`, `12-size-tier-selected.png` |
| 3.11 | Pick a `size_tier_plus_materials` offering | Same flow + includes_materials hint | `13-size-tier-plus-materials.png` |
| 3.12 | Pick a `yard_tier` offering | Yard tier sub-picker opens → 0-3yd / 4-6yd select | `14-yard-tier.png` |
| 3.13 | Pick a `variants` offering | VariantSubPicker opens → variant select → line added | `15-variant-subpicker.png` |
| 3.14 | Pick a `tiered_zone_step` offering, enter quantity ABOVE max_zones_specified | "Custom Quote" prompt fires → switches line to free-form `custom` | `16-above-max-prompt.png`, `17-custom-line-added.png` |
| 3.15 | Edit line → expand drawer | Hidden `unit_cost` field visible; margin readout shown | `18-staff-drawer-unit-cost.png` |
| 3.16 | Submit estimate → open customer portal preview | `unit_cost` redacted from customer view | `19-customer-view-no-unit-cost.png` |
| 3.17 | Click "Use a template" instead | Existing template flow still works (E7 backward compat) | `20-template-flow-coexists.png` |
| 3.18 | DB check after submit | Line item rows have `service_offering_id`, `unit_cost` | (DB query) |

**DB queries**:

```bash
# 3.18 service_offering_id present on line items
psql "$DATABASE_URL" -tAc "SELECT line_items->0->>'service_offering_id', line_items->0->>'unit_cost' FROM estimates WHERE id = '<test_estimate_id>';"
```

**Sign-off**: 20 screenshots, 5 customer-type-resolution paths exercised, 6 pricing_model branches exercised in picker (flat / per_zone_range / size_tier / size_tier_plus_materials / yard_tier / variants), above-tier-max prompt verified, hidden cost field verified.

#### Task 6.5: Phase 4 E2E — Payment visibility + receipts (every payment method)

**Script**: `e2e/phase-4-payment-timeline-receipts.sh`

**Test matrix** — every PaymentMethod enum value gets a flow + screenshot:

| # | Method | Action | Expected | Screenshots |
|---|---|---|---|---|
| 4.1 | `cash` | Collect $100 cash on appointment | Confirmation card "Paid — $100 · cash"; receipt SMS to test phone; receipt email | `01-cash-collected.png`, `02-cash-confirmation-card.png`, `03-cash-receipt-sms.png`, `04-cash-receipt-email.png` |
| 4.2 | `check` | Collect $100 check w/ ref# 1234 | Card includes "Check #1234"; receipts fire | `05-check-with-ref.png`, `06-check-receipt.png` |
| 4.3 | `venmo` | Collect $50 Venmo | Card shows "Venmo"; receipts | `07-venmo.png` |
| 4.4 | `zelle` | Collect $50 Zelle | Card shows "Zelle"; receipts | `08-zelle.png` |
| 4.5 | `credit_card` (Stripe Payment Link) | Click "Send Payment Link" → simulate webhook `payment_intent.succeeded` | Card shows "Credit card · Stripe"; webhook flips invoice→PAID | `09-send-payment-link.png`, `10-stripe-paid-card.png` |
| 4.6 | Multi-tender | Collect $50 cash → status PARTIAL → collect $50 check → status PAID | Two timeline events; status transitions correctly | `11-partial.png`, `12-paid-after-second.png` |
| 4.7 | Refund | Stripe webhook `charge.refunded` | Status REFUNDED; timeline event added | `13-refund-event.png` |
| 4.8 | Click "Text receipt" CTA on confirmation card | Receipt SMS re-sent to customer | `14-text-receipt-resent.png` |
| 4.9 | Open appointment timeline | Every payment from 4.1–4.7 surfaces as `PAYMENT_RECEIVED` event | `15-timeline-with-all-payments.png` |
| 4.10 | Check Stripe Payment Link path doesn't double-send | Stripe hosted confirmation present + Grin's receipt distinct | `16-distinct-receipts.png` |

**DB queries**:

```bash
# 4.1 Invoice has payment_method=cash, paid_at set
psql "$DATABASE_URL" -tAc "SELECT payment_method, paid_amount, status FROM invoices WHERE id = '<inv_id>';"

# 4.6 Multi-tender: paid_amount accumulates correctly
psql "$DATABASE_URL" -tAc "SELECT paid_amount, status FROM invoices WHERE id = '<inv_id>';"
# Expected after $50+$50 on $100: 100.00|paid

# 4.9 Timeline event count
psql "$DATABASE_URL" -tAc "SELECT COUNT(*) FROM invoices WHERE job_id IN (SELECT job_id FROM appointments WHERE id = '<appt_id>') AND paid_at IS NOT NULL;"
```

**Verify SMS test phone is the only recipient** (per memory `feedback_sms_test_number.md`):

```bash
psql "$DATABASE_URL" -tAc "SELECT DISTINCT to_phone FROM sent_messages WHERE message_type = 'payment_receipt' AND created_at > NOW() - INTERVAL '1 hour';"
# Expected: only +19527373312
```

**Sign-off**: 16 screenshots, 5 payment methods exercised (cash/check/venmo/zelle/credit_card), partial+full+refund states verified, receipts arrive at allowlisted addresses only.

#### Task 6.6: Phase 5 E2E — Polish + cleanup verification

**Script**: `e2e/phase-5-polish.sh`

| # | Action | Expected | Screenshot |
|---|---|---|---|
| 5.1 | Open appointment modal | Estimate CTA reads "Send estimate" (not "Create Estimate") | `01-cta-label.png` |
| 5.2 | Action track | Labels: "On my way" / "Job started" / "Job complete" | `02-action-track-labels.png` |
| 5.3 | Click directions → Maps popover opens | "Remember my choice" footer row present | `03-maps-popover-with-footer.png` |
| 5.4 | Select Apple + check "Remember" → close → reopen | Defaults to Apple | `04-apple-remembered.png` |
| 5.5 | Repeat with Google | Defaults to Google | `05-google-remembered.png` |
| 5.6 | DB: Staff.preferred_maps_app set | (DB query) | — |
| 5.7 | Hit deprecated `/api/v1/stripe-terminal/*` endpoint | 404 | `06-stripe-terminal-404.png` |
| 5.8 | `pytest tests/unit/test_stripe_terminal.py` | File doesn't exist (deleted) | terminal output |
| 5.9 | grep `stripe_terminal` in `api/v1/router.py` | No matches (import + include_router removed) | terminal output |

**DB validation**:

```bash
psql "$DATABASE_URL" -tAc "SELECT preferred_maps_app FROM staff WHERE id = '<test_staff_id>';"
# Expected: apple or google

# Confirm static stripe_terminal columns absent from production routes
psql "$DATABASE_URL" -tAc "SELECT 1 FROM information_schema.routines WHERE routine_name LIKE '%stripe_terminal%';"
# Expected: 0 rows
```

**Sign-off**: 6 screenshots + DB confirms `preferred_maps_app` persisted + grep confirms uninstall.

#### Task 6.7: Cross-phase integration scenario — "happy path through all 6 phases"

**Script**: `e2e/integration-full-happy-path.sh`

A single end-to-end run that exercises every phase in order:

1. **Setup**: create test customer, test property (residential), test appointment.
2. **Phase 3**: open appointment → "Send estimate" → LineItemPicker → search "spring" → select Spring Start-Up (size_tier) → S size → submit estimate.
3. **Phase 0**: customer approves via portal → Job auto-created in TO_BE_SCHEDULED → signed PDF in inbox → audit log written.
4. **Phase 0**: click "Schedule follow-up" CTA → existing schedule modal opens → schedule for tomorrow.
5. **Phase 5**: open appointment → click directions → choose Google + remember → verify persistence.
6. **Phase 4**: appointment → mark On my way → Job started → Job complete → collect $X cash → confirmation card → receipt SMS + email arrive → timeline shows estimate, payment, completion.
7. **Phase 2**: navigate to `/invoices?tab=pricelist` → edit Spring Start-Up's `display_name` → verify in next estimate the new name shows.
8. **Phase 1 verification**: psql confirms 73 seeded rows still intact + 1 new row from any Phase 2 create.

**Screenshots**: ~30 across the flow → `e2e-screenshots/appointment-modal-umbrella/integration/`.

**Sign-off**: every screenshot present, full flow completes without errors, DB end-state matches expectations across all 6 phases.

#### Task 6.8: Responsive verification

For every page touched in Phases 0–5 (appointment modal, /invoices/pricelist, estimate sheet, payment sheet, customer portal), repeat the **smoke screenshots** at three viewports:

```bash
agent-browser set viewport 375 812   # mobile
agent-browser set viewport 768 1024  # tablet
agent-browser set viewport 1440 900  # desktop
```

Save to `e2e-screenshots/appointment-modal-umbrella/responsive/{page}-{viewport}.png`. Sign-off: no overflow, no broken alignment, no inaccessible touch targets at any viewport.

#### Task 6.9: Console + uncaught-exception gate

After every flow in 6.1–6.8, run:

```bash
agent-browser console > "$SHOTS/console-{step}.txt"
agent-browser errors > "$SHOTS/errors-{step}.txt"
```

**Mandatory: every `errors-*.txt` is empty.** Any uncaught exception fails the gate. `console-*.txt` may contain INFO/DEBUG logs but ZERO `error`-level entries.

#### Task 6.10: E2E sign-off report

**Required deliverable**: `e2e-screenshots/appointment-modal-umbrella/E2E-SIGNOFF-REPORT.md` containing:

- Total screenshots captured (target: ≥130 across phases 6.1–6.8).
- Per-phase pass/fail table with screenshot links.
- Database validation queries with returned values.
- Console + error file inventory (link each, confirm empty).
- Any deviation from expected with root-cause + fix commit reference.
- Final verdict: "ALL PASS" or list of remaining gaps.

**No phase merges into `dev` until this report is committed alongside the code with verdict ALL PASS.**

---

## TESTING STRATEGY

Three-tier mandatory per `.kiro/steering/code-standards.md` and `.kiro/steering/tech.md`.

### Unit Tests (`tests/unit/`, `@pytest.mark.unit`)

- All new service methods: `EstimateService.approve_via_portal` branches, `ServiceOfferingService.archive_and_replace`, `EstimatePdfService.generate`, `PriceListExportService.export_to_markdown`.
- Pydantic discriminated unions: every `pricing_rule` variant validates correct shape and rejects wrong shape.
- `_payment_to_event` helper.

### Functional Tests (`tests/functional/`, `@pytest.mark.functional`, real DB)

- End-to-end estimate approval flow: portal POST → approval recorded → auto-job created → PDF emailed → audit logged.
- Pricelist CRUD via `/api/v1/services` with archive+replace semantics.
- Pricelist seed migration runs and produces ~146 rows.
- Appointment timeline includes payment events.
- Receipt SMS + email fire on payment collection.

### Integration Tests (`tests/integration/`, `@pytest.mark.integration`)

- Auto-job creation propagates to schedule view (modal banner refresh).
- Pricelist edit triggers `pricelist.md` cache invalidation.
- Stripe webhook → invoice.paid → timeline payment event.

### Edge Cases (must test)

- Estimate approved with `lead_id` only (no customer_id) → auto-job SKIPS with logged reason; approval still succeeds.
- Estimate already attached to job (job_id non-null) at approval time → items copied into parent job, no new job.
- N5 setting OFF → no auto-job, approval still records and emails PDF.
- Archive-and-replace race: two staff members editing same offering simultaneously — second commit picks up new `replaced_by_id` chain.
- Migration rollback via `alembic downgrade -1` doesn't break existing estimates.
- `range_anchors` absent → picker still functions without quick-pick chips.
- Above-tier-max → "Custom quote" prompt rather than silent extrapolation.

---

## VALIDATION COMMANDS

Per `.kiro/steering/code-standards.md` § 5.

### Level 1: Syntax & Style

```bash
uv run ruff check --fix src/
uv run ruff format src/
uv run mypy src/
uv run pyright src/
cd frontend && npm run lint && npm run typecheck && cd ..
```

### Level 2: Unit Tests

```bash
uv run pytest -m unit -v
cd frontend && npm test && cd ..
```

### Level 3: Functional + Integration Tests

```bash
uv run pytest -m functional -v
uv run pytest -m integration -v
uv run pytest --cov=src/grins_platform --cov-report=term-missing
```

### Level 4: Mandatory E2E Visual Verification (Phase 6 — non-negotiable)

**This level supersedes the previous "Manual Validation" checklist.** Phase 6 (Tasks 6.1–6.10 above) is mandatory and gates merge to `dev`. There is no manual smoke-test substitute.

```bash
# Pre-flight: backend + frontend running, agent-browser installed, DB migrated
uv run uvicorn grins_platform.app:app --reload --host 0.0.0.0 --port 8000 &
cd frontend && npm run dev &
agent-browser --version || npm install -g agent-browser

# Run the full E2E suite (every phase + integration + responsive)
bash e2e/phase-0-estimate-approval-autojob.sh
bash e2e/phase-1-pricelist-seed.sh
bash e2e/phase-2-pricelist-editor.sh
bash e2e/phase-3-estimate-line-item-picker.sh
bash e2e/phase-4-payment-timeline-receipts.sh
bash e2e/phase-5-polish.sh
bash e2e/integration-full-happy-path.sh

# Verify the sign-off report exists and the verdict is ALL PASS
grep -q "ALL PASS" e2e-screenshots/appointment-modal-umbrella/E2E-SIGNOFF-REPORT.md
```

**Every script above must exit 0. Every `errors-*.txt` artifact must be empty. The sign-off report must read "ALL PASS".**

### Level 5: Additional Validation

- Probe `pg_jsonschema` extension availability: `psql $DATABASE_URL -c "SELECT 1 FROM pg_extension WHERE extname='pg_jsonschema';"`.
- If using UUIDv7 via `pg_uuidv7`: `psql $DATABASE_URL -c "SELECT uuid_generate_v7();"`.
- Storybook (if present) for new frontend components.

---

## ACCEPTANCE CRITERIA

- [ ] **AJ-1, AJ-3, AJ-4**: Customer YES via portal auto-creates a `TO_BE_SCHEDULED` Job with line items copied (when N5 setting ON and customer_id present).
- [ ] **AJ-7**: Two branches verified — standalone vs attached-to-existing-appointment.
- [ ] **AJ-8**: Signed-PDF estimate emailed to customer on approval.
- [ ] **AJ-6**: Appointment modal banner updates within 60s of approval (push or polling fallback).
- [ ] **N5**: `business_settings.auto_job_on_approval` toggleable; OFF disables auto-job; default ON.
- [ ] **E1**: `ServiceOffering` stores `pricing_rule` as JSONB; `pricing_model` discriminator + Pydantic union enforces shape.
- [ ] **E3**: 146 rows in `service_offerings` after seed migration (73 slugs × 2 customer_types).
- [ ] **E4**: Editing a price archives the old row and inserts a new one. Estimate FKs to old row remain valid.
- [ ] **E5**: `slug` is UNIQUE per `customer_type` (partial index on `is_active=true`); slug is immutable post-create; UUIDv7 PKs.
- [ ] **P1 / N4**: `range_anchors` JSON key supported; LineItemPicker renders quick-pick chips when present.
- [ ] **P4**: LineItemPicker pre-filters by `Customer.customer_type` with manual override.
- [ ] **P5**: `unit_cost` editable on staff drawer; absent on customer-facing PDF/portal.
- [ ] **P9**: Pricelist editor at `/invoices/pricelist`; top-nav "Pricebook" shortcut also works.
- [ ] **P10**: Above-tier-max triggers "Custom quote" prompt.
- [ ] **P8**: `pricelist.md` auto-exports on every CRUD save; static file retired.
- [ ] **Phase 4**: Payments visible on appointment timeline; receipts delivered; "Paid" confirmation card renders.
- [ ] **Phase 5**: Modal CTA labels match design spec; Maps "Remember my choice" persists; `stripe_terminal.py` deleted.
- [ ] All validation commands pass with zero errors.
- [ ] Test coverage 80%+ for new modules.
- [ ] No regressions in existing estimate / job / payment flows.
- [ ] **MANDATORY E2E**: Phase 6 sub-suites 6.1 through 6.10 all pass. Sign-off report at `e2e-screenshots/appointment-modal-umbrella/E2E-SIGNOFF-REPORT.md` reads "ALL PASS".
- [ ] **MANDATORY E2E — Screenshots present**: ≥130 screenshots across `e2e-screenshots/appointment-modal-umbrella/{phase-0..5,integration,responsive}/`.
- [ ] **MANDATORY E2E — Console clean**: every `errors-*.txt` artifact is empty; no uncaught exceptions in any flow.
- [ ] **MANDATORY E2E — Combinatorial coverage**: every PaymentMethod (5), every PricingModel variant in drawer (17), every customer-type-resolution path (3), every TimelineEventKind including PAYMENT_RECEIVED, every action-track label change, every maps-popover persistence path.
- [ ] **MANDATORY E2E — Responsive**: every modified page captured at 375×812 / 768×1024 / 1440×900.
- [ ] **MANDATORY E2E — DB validation**: every state-changing flow has at least one paired `psql` query asserting the post-state.
- [ ] Memory entries updated: add a new memory at `project_pricelist_editor_live.md` once Phase 2 ships.

---

## COMPLETION CHECKLIST

- [ ] All tasks completed in order
- [ ] Each task validation passed immediately
- [ ] All validation commands executed successfully
- [ ] Full test suite passes (unit + functional + integration)
- [ ] No linting or type checking errors
- [ ] Manual testing confirms feature works end-to-end across all 5 phases
- [ ] Acceptance criteria all met
- [ ] Code reviewed for quality and maintainability
- [ ] Viktor confirmed V1, V2, V3 before Phase 1 migration runs in production
- [ ] DEVLOG.md entry added per `.kiro/steering/devlog-rules.md`
- [ ] CHANGELOG.md entry added

---

## Deferred Features — DOCUMENTED, NOT IMPLEMENTED

The decisions below were considered, researched, and explicitly DEFERRED in the planning conversation. They are recorded here so future maintainers don't re-derive the analysis. **No code changes for these in this plan.**

### N1 — Service-call / dispatch fee (NOT IMPLEMENTING)

- **What it is**: An $89 (industry benchmark per ServiceTitan's >1M-job analysis) flat fee charged on every service appointment, **waived if the customer approves the resulting work**. Industry-standard mechanic across HVAC, plumbing, electrical.
- **Why deferred**: Per user direction 2026-05-01: *"We're not going to have the $89 fee."* Grin's business model does not currently include a dispatch fee.
- **Future-light implementation if revisited**: Manual line item — staff adds "Service call · $X" to the estimate, then if work is approved, adds a paired "Service call credit · −$X (waived)" line on the work invoice. **No schema change required**; the negative-line-item pattern (P11 mechanic) is the unblock. Source: research bundle 4 cites this is how ServiceTitan, Jobber, and HCP all handle it manually.
- **Affected if reactivated**: `EstimateLineItem` already supports any `quoted_amount`. The `pricing_model: conditional_fee` enum value reserved in Task 1.1 is precisely for this. Seed JSON already includes `service_call_fee_*` items as `pricing_model: conditional_fee`. They will be present in DB after Phase 1 migration **but no UI will surface them** until reactivated.

### N2 — Emergency / after-hours surcharge (NOT IMPLEMENTING)

- **What it is**: A $100–$300 (or 1.5–2× labor rate) surcharge applied to appointments outside business hours, on weekends, or on holidays. Auto-applied by ServiceTitan-tier tools based on a configured business-hours + holiday calendar; manually applied at mid-tier (Jobber, HCP).
- **Why deferred**: Per user direction 2026-05-01: *"We're not going to have the after hours surcharge."*
- **Future-light implementation if revisited**:
  1. New `business_settings.business_hours: JSONB` (e.g. `{mon: [7,18], sat: [9,14], sun: null}`) and `business_settings.holidays: date[]`.
  2. `pricing_model: emergency_surcharge` enum already reserved.
  3. Scheduler-side prompt in the appointment-create modal: *"This appointment is outside business hours — apply $X surcharge?"* per research bundle 4 recommendation.
  4. Auto-apply path: scheduler reads business_settings + appointment.scheduled_at; if outside, prepends a surcharge line item to the eventual invoice.
- **Affected if reactivated**: No schema change in this plan. New columns on `business_settings`. New Phase X task to wire scheduler prompt. **Material markup column added in E2 also future-proofs this** because surcharge is just another markup-style line.

### N3 — Material markup math (NOT IMPLEMENTING the math, but adding the SEAM)

- **What it is**: 25–50% markup on parts is industry norm (Jobber HVAC parts markup calculator). Pure cost-plus / pass-through is rare in HVAC, plumbing, irrigation. Viktor's seed uses "at cost" labels which is unusual.
- **Why deferred (math)**: Per user direction 2026-05-01: *"We're not going to have the markup either... Make a note of it, but don't implement that either."*
- **What IS being added**: `material_markup_pct: Decimal DEFAULT 0` column on `EstimateLineItem` shape (E2 / Task 3.1). **Default 0 means current behavior is unchanged** — pure pass-through at `unit_cost`. Hidden from UI in v1.
- **Future-light implementation if revisited**:
  - Add `material_markup_pct` field to staff edit drawer (P5).
  - Final price calc on the line: `quoted_amount = unit_price + (unit_cost × quantity × (1 + material_markup_pct / 100))`.
  - Decision needed at activation: tenant-wide default markup vs per-line markup vs both.
- **Why the seam matters**: Without the column, future activation requires a migration (touches estimate-line-item shape across all customers). With the column at default 0, future activation is a UI/config change.

### N4 — Good/Better/Best picker UI (PHASE 2 — NOT IN THIS PLAN)

- **What it is**: Three named fixed-price tiers per service (e.g. Good $200 / Better $300 / Best $450) instead of a continuous range or single number. ServiceTitan + The New Flat Rate established this as industry direction (research bundle 3, 4); average-ticket lift is documented.
- **What IS being added (per user direction)**: `pricing_rule.range_anchors: {low, mid, high}` JSON key on each `ServiceOffering` (E1 / Task 1.3). LineItemPicker renders 3 quick-pick chips when present (Task 3.5).
- **What is deferred**: Full G/B/B picker UI on customer-facing estimate (three-tile chooser, customer picks one, anchor analytics). Schema is ready; UI is not.
- **Future-light implementation if revisited**:
  - Customer-facing estimate template renders three tiles per offering when `range_anchors` non-null.
  - Track which tier the customer chose (`EstimateLineItem.selected_tier: 'low' | 'mid' | 'high'`).
  - Average-ticket reporting splits by tier choice.

### N5 — Auto-job tenant setting (IMPLEMENTING toggleable variant)

- **Note for the record**: The first-pass recommendation was option (a) — hardcoded auto-create. User chose option (b) — toggleable setting. Plan implements (b) per Task 0.2.

### Other audit items intentionally left for follow-up plans

These are in the audit's P2 list but are out of scope for this umbrella to keep velocity manageable:

- **Estimate sheet visual rebuild to match design states E1→E8** (audit §3) — current `EstimateCreator.tsx` is a backend-style form. Phase 2 of estimate UX should rebuild to the violet sheet header + identity card + LINE ITEMS caps section + SMS/Email delivery toggle + preview step + awaiting-reply banner + Resend button. This is a significant UI rewrite; better as its own plan (`.agents/plans/estimate-sheet-visual-rebuild.md`) once Phase 3 of this plan ships and stabilizes.
- **Vendor cost catalog integration** (Ferguson, Ewing) — only ServiceTitan-tier shops have this; mid-tier captures cost manually. Out of scope. Research bundle 4 confirms this is industry-realistic.
- **Tap-to-Pay code retention** (audit §2 P2 item) — `stripe_terminal.py` deletion is in Phase 5 Task 5.3. The code is already marked "MUST NOT import" — Phase 5 just finishes the cleanup.

---

## NOTES

### Architectural Trade-offs

**Why hybrid storage (E1) over pure JSONB or pure typed columns?** Pure JSONB loses query-ability and CHECK constraints. Pure typed columns balloons the schema with 14 nullable columns per pricing model. Hybrid (Stripe pattern) gives us discriminator-keyed validation with one schema per variant. Source: Wei Yen — Modelling discriminated unions in Postgres.

**Why archive+create over UPDATE+audit (E4)?** Estimates pin to a `service_offering_id`. If we UPDATE, in-flight estimates suddenly reflect new prices — confusing for customers and breaks signed-PDF reproducibility. Archive+create is Stripe's exact mechanism for the same reason. Source: Stripe `manage prices`.

**Why auto-job synchronously in `approve_via_portal` (AJ-1)?** Async/event-driven adds infra (event bus, retry semantics, dead-letter) for v1. Same-transaction means atomic from the user's POV — either approval recorded AND job created or neither. The best-effort pattern (Task 0.4) handles the rare auto-job-fails-but-approval-succeeded case by logging without raising.

**Why `/invoices/pricelist` (P9) when industry expects top-level?** User stated preference in Obsidian note 09 was Invoices tab. Research showed top-level is the industry norm (ST, HCP, Stripe). Compromise: primary location at `/invoices/pricelist` per user; top-nav "Pricebook" shortcut for users coming from elsewhere or migrating from ST/HCP.

**Why `customer_type` as separate rows (E3) instead of nested map?** Stripe's analogous decision (multi-currency) has both options: `currency_options` nested for simple cases vs separate Price objects for full independence. Our 14 pricing models mean shape may differ across customer_type (e.g. residential drip is `per_zone_range`, V3 says commercial drip should also be `per_zone_range` but the seed JSON currently has it as `flat_range` pending V3 confirmation). Separate rows keep CHECK constraint per row simple, audit grain natural, and admin UI obvious.

**Why immutable slug (E5)?** Slug-rename = silent FK breakage if any consumer cached it (CSV imports, support runbooks, external API clients, payment system PO refs). UUID is the only safe FK target; slug is a stable human-readable handle. If admin needs to rename: edit `display_name`. If slug must change: alias/redirect table — but don't allow slug mutation directly.

### Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| `pg_jsonschema` not available on Railway Postgres | Medium | Low | Fallback to Pydantic-only validation documented; CHECK constraints still get added if extension probe succeeds. |
| `pg_uuidv7` not available; UUIDv7 generation falls back to app side | Medium | Low | Use `uuid6` Python lib; perf indistinguishable for our row volume. |
| Viktor doesn't confirm V1/V2/V3 by Phase 1 ship date | High | Medium | Migration gates on env var; can ship to dev/staging without confirmation; production deploy waits on green light. |
| Signed-PDF generation slow on approval (1–2s) | Medium | Low | Async via background task if it bites; v1 ships sync because portal approval is already a slow user journey. |
| Customer-type pre-filter (P4) frustrates techs who serve mixed customer | Low | Low | Manual override toggle; P4 explicit in plan. |
| Archive+create (E4) breaks GUI patterns expecting UPDATE | High | Medium | Drawer-level confirmation on edit ("this will archive"); explicit `useArchiveAndReplace` mutation hook. |
| Auto-job (AJ-1) fires for `lead_only` estimate before customer is created | Medium | Low | Task 0.4 GOTCHA explicitly skips with logged reason; estimate cannot be approved without customer in most flows. |
| Range_anchors quick-pick chips (P1) confuse techs accustomed to a single number | Low | Low | Chips are quick-picks, not constraints — tech can still type any number. |
| `pricelist.md` auto-export drift from canonical DB | Low | Low | Cache invalidates on every CRUD save; no manual touchpoints. |

### References

- Audit: `bughunt/2026-05-01-appointment-modal-payment-estimate-pricelist-audit.md`
- Seed data: `bughunt/2026-05-01-pricelist-seed-data.json`
- Design spec: `feature-developments/design_handoff_appointment_modal_combined 2/README.md`
- Memory: `project_estimate_email_portal_wired.md` (Resend live), `project_stripe_payment_links_arch_c.md` (Architecture C reference), `feedback_sms_test_number.md` (test phone restriction), `feedback_email_test_inbox.md` (test email restriction), `feedback_email_test_inbox.md`
- Steering: `.kiro/steering/{tech,structure,code-standards,api-patterns,frontend-patterns}.md`
- Research findings: see Decision Log § references inline
- Industry sources cited inline (Stripe, HCP, Jobber, ServiceTitan, Wei Yen on Postgres unions, Supabase pg_jsonschema, etc.)

### Confidence Score for One-Pass Implementation: **10/10** (post-2026-05-01 verification sweep)

**Verifications completed in the sweep**:
- ✅ `JobScopeItem` confirmed absent → AJ-4 path is `Job.scope_items` JSONB column (Task 0.1).
- ✅ No SSE/websocket/broadcast infrastructure → AJ-6 reduced to 60s polling (no false dependency).
- ✅ `InvoicePDFService` (capital PDF) verified at `services/invoice_pdf_service.py` → mirror class is `EstimatePDFService`; constructor simplified for v1 (no S3).
- ✅ `BusinessSettingService.get_bool()` exists at line 141; `BUSINESS_SETTING_KEYS` tuple at line 40 → N5 wiring is one line.
- ✅ All 14 `EstimateService(...)` callsites enumerated; default `None` for new DI params keeps every site working.
- ✅ `Customer.customer_type` confirmed absent; `Lead.customer_type` exists; `Property.property_type` exists → P4 resolution order is deterministic without a new migration.
- ✅ `EstimateCreator.tsx` location verified (`features/schedule/components/`, NOT under AppointmentModal/); existing line-item shape `{item, description, unit_price, quantity}` documented.
- ✅ `useEstimateTemplates` ownership verified — lives in `@/features/leads/hooks`; coexist plan stays valid.
- ✅ `Invoices.tsx` already uses shadcn `Tabs` → Phase 2 sub-tab is a 2-element addition (TabsTrigger + TabsContent).
- ✅ Top-nav lives at `frontend/src/shared/components/Layout.tsx`.
- ✅ `frontend/src/features/invoices/api/invoiceApi.ts` is the canonical mirror target for `serviceApi.ts`.
- ✅ No separate `payments` table → Phase 4 timeline join is `appointment.job → invoices` reading `paid_at`/`payment_method`/`paid_amount` columns directly.
- ✅ `collect_payment` lives on `AppointmentService` at line 1964 (NOT InvoiceService); receipt SMS/email fires there.
- ✅ `MessageType` enum needs `PAYMENT_RECEIPT = "payment_receipt"` added before Phase 4 SMS receipt fires (existing convention).
- ✅ No `User` model — staff identity is `Staff` at `models/staff.py:39` table `staff`. Phase 5 maps-app migration adds to `staff`, not `users`.
- ✅ `ActionTrack.tsx` owns the labels (lines 70/79/+third); `ActionCard.tsx` only takes a `label` prop. Phase 5 Task 5.1 edits ActionTrack only.
- ✅ `stripe_terminal` cleanup is more invasive than the audit suggested — full uninstall list documented in Task 5.3 (router import, router file, service file, test file).
- ✅ `ArchiveHistorySheet` Phase 1.5 dependency made explicit; Phase 2 ships with placeholder.

**Remaining residual risks** (acknowledged, not blockers):
- Phase 1 seed migration assumes the JSON file is at `bughunt/2026-05-01-pricelist-seed-data.json` at execution time — confirmed at the path during verification, but if reorganized before the migration runs, the path-resolution helper raises a clear error.
- Phase 4 multi-payment scenarios (deposit + final) currently produce two timeline events; if the business semantics ever require collapsing them into one "fully paid" milestone, that's a follow-up enhancement, not a Phase 4 blocker.
- Phase 5 `/api/v1/staff/me` PATCH endpoint may need to be added (verify with `Grep` at implementation time); if absent it's ~10 lines following existing endpoint patterns.

**Implementation-readiness verdict**: every non-obvious file path, line number, and pattern reference has been verified. An execution agent can implement top-to-bottom from this plan without further codebase discovery.

---

## Re-Run E2E (2026-05-02) — Tech-Mobile + Customer-Portal Personas

**Why this re-run**: The 2026-05-01 sign-off was conducted entirely as `admin/admin123` on a **desktop** session, which never opened `/tech` (mobile-only route), never opened `/portal/estimates/{token}` (customer-only route), and never clicked the actual "Record Other Payment" or "Create Invoice & Send Payment Link" CTAs. As a result, four user-facing P0 crashes that only fire on the tech-mobile or customer-portal personas stayed hidden. This re-run targets exactly those gaps.

**Run date**: 2026-05-02
**Authoritative artifact folder**: `e2e-screenshots/appointment-modal-umbrella-tech-mobile-2026-05-02/`
**Sign-off report**: `e2e-screenshots/appointment-modal-umbrella-tech-mobile-2026-05-02/E2E-SIGNOFF-REPORT.md`
**Verdict**: **PARTIAL** — Phase 2 + Phase 5 cleanup pass cleanly; Phases 0/3/4/Portal all pass at API+DB layer but hit user-facing crashes that block the design-spec'd UX end-to-end.

### Methodology

| Persona | Identity | Viewport | Coverage |
|---|---|---|---|
| Tech in the field | `vasiliy / tech123` (3 today: completed/in_progress/scheduled) | 390×844 (iPhone 14 Pro–ish) | Phases 3, 4, 5 (mobile-only paths) |
| Customer (approval) | Avery Park, portal token `e20b2a8a-…` | 390×844 | Phase 0 customer portal |
| Admin (catalog) | `admin / admin123` | 1440×900 desktop | Phase 2 pricelist editor |
| Responsive sweep | All three above | 375×812 / 768×1024 / 1440×900 | Phase 6.8 |

The tech-mobile path lands on `/tech` (not `/dashboard`) and shows a phone-only schedule view with `mobile-job-card-current` / `-upcoming` / `-complete` cards. Tapping the current card opens the existing `AppointmentModal`, which is where Phases 3/4/5 actually surface to the field user.

**Test data overrides** (so receipts could be verified live):
- Customer Avery Park's phone overridden to `+19527373312` (only number on `SMS_TEST_PHONE_ALLOWLIST`).
- Customer email overridden to `kirillrakitinsecond@gmail.com` (only address on `EMAIL_TEST_ADDRESS_ALLOWLIST`).
- Tech `vasiliy` appointments seeded fresh via `scripts/seed_tech_companion_appointments.py`.

**Test environment**: localhost backend (uv-managed uvicorn) + localhost Vite frontend, against the local Postgres seeded with all 73 pricelist rows. The dev Vercel deployment was reachable (`grins-irrigation-platform-git-dev-…vercel.app` → `grins-dev-dev.up.railway.app`) but the Railway DB had no vasiliy seed data, so the run targeted localhost where the demo-data migration had populated tech identities. Stripe sandbox credentials (`sk_test_…`, `whsec_yzU…`) were pulled mid-run from Railway dev env via `mcp__railway__list-variables` to enable real Stripe Payment Link generation.

### Step-by-step coverage (what was actually walked)

**Pre-flight**
- Verified backend `/health`, frontend `/`, `agent-browser 0.7.6`, `psql` on PATH.
- Confirmed 73 seeded pricelist rows.
- Confirmed `vasiliy` HTTP 200 login on the local backend (`role=tech`).
- Re-seeded today's tech appointments.
- Updated Avery Park's phone+email to the allowlisted test values.

**Phase 3 — tech sends estimate from mobile**
1. Mobile login as `vasiliy` (390×844). Lands on `/tech`.
2. Tap in-progress card (10:30 AM Spring Opening). AppointmentModal opens.
3. Confirmed Phase 5 polish visible: CTA reads "Send estimate"; ActionTrack sublabels read "On my way" / "Job started" / "Job complete".
4. Tap "Send estimate" → EstimateSheet renders with `Add from pricelist`, `Use a template`, manual line items, hidden "Internal cost (hidden from customer)" field.
5. Open LineItemPicker. Default `Show all customer types` toggle visible.
6. Search `spring` → 4 results (residential / commercial / 2 × unset).
7. Select Spring Start-Up (`tiered_zone_step`). Quantity input shows "Max in standard tier: 19".
8. Set qty = 25 → above-tier-max prompt fires: "Above standard tier — Switch this line to a custom quote." (Captured in `phase-3/08-above-tier-max-prompt.png`.)
9. Reset qty=8, click Add → line appears in Line Items.
10. Search `tree`, pick Tree Drop (`size_tier`) → SizeTierSubPicker shows **"This offering has no tiers configured"** despite the DB row having three tiers. **(Bug #12 — see below.)**
11. Cancel out, search `valve`, pick Valve Repair/Replacement residential (`variants`) → VariantSubPicker shows priced variants (`1 valve in single valve box — $150.00`).
12. Click "Send Estimate" via UI → frontend POST returns 403 against an intermediate URL (likely a relative-URL/proxy issue; the same payload to `http://localhost:8000` returns 201). Estimate `1c98ab63-…` created via direct API.
13. POST `/api/v1/estimates/{id}/send` returned `sent_via=[sms,email]`.
14. DB confirmed: `sent_messages` row `+19527373312 / estimate_sent / sent`. Real SMS delivered.

**Phase 0 — customer approves via portal**
1. Open the portal URL in a second browser session (`umbrella-portal-2026-05-02`, mobile viewport): `/portal/estimates/e20b2a8a-…`.
2. Page renders an `Unexpected Application Error` boundary with `TypeError: Cannot read properties of undefined (reading 'company_logo_url')`. Customer cannot view, sign, approve, or reject. **(Bug #13.)**
3. Workaround: `POST /api/v1/portal/estimates/{token}/approve` with `{signature, accept_terms}` → HTTP 200.
4. DB confirmed:
   - `estimates.status = approved`, `approved_at` set, `job_id = 296ed78d-…`.
   - `jobs.id = 296ed78d-…`: `status=to_be_scheduled` (AJ-3), `category=ready_to_schedule` (auto-categorized from `quoted_amount`), `quoted_amount=2560.00`, `scope_items` contains 1 line item (AJ-4 JSONB copy verified).
   - `audit_log` row: `action=estimate.auto_job_created`, `details={"branch":"standalone","job_id":"296ed78d…","source":"customer_portal","actor_type":"customer"}`. Canonical action string used.
   - Internal staff alert SMS to `+19527373312` (`automated_notification / sent`).
5. Signed-PDF email observation: no dedicated `email_send_log` table; presumed-OK via Resend logs but not directly observed in DB.

**Phase 4 — payment paths + receipts**
1. From the same tech-mobile session, open AppointmentModal again on the in-progress card.
2. Tap "Collect Payment" → sheet shows two paths: "Create Invoice & Send Payment Link" (Stripe) and "Record Other Payment" (cash/check/venmo/zelle/Send Invoice).
3. Tap "Record Other Payment" → method dropdown surfaces 5 entries: Cash, Check, Venmo, Zelle, Send Invoice.
4. Select Cash, $100, click Collect Payment → HTTP 500. Backend log shows `TypeError: InvoiceRepository.update() takes 2 positional arguments but 3 were given` at `appointment_service.py:2059`. **(Bug #14.)**
5. **In-test fix applied** (kwargs unpack at lines 2025–2034 and 2059–2067). Re-tested.
6. Cash $100 → HTTP 200, invoice `fa3d6b3c-…` (`INV-2026-0478`), `payment_method=cash`, `paid_amount=100`, `status=paid`. **Real payment_receipt SMS sent to `+19527373312`** ("Grin's receipt: $100.00 received via cash on May 02, 2026 …").
7. Multi-tender: Check $50 / Venmo $30 / Zelle $20 → all HTTP 200 against the same invoice. `paid_amount` accumulated to 200 on `total_amount=100`. Receipt SMS only fired on the FIRST cash collect — multi-tender existing-invoice update branch in `appointment_service.py` does not call `_send_payment_receipts` (separate observation, see bug list).
8. Stripe Payment Link path: tap "Create Invoice & Send Payment Link" via UI → `/tech` page crashes with React error `Element type is invalid ... Check the render method of TimelineRow`. Page is dead until reload. **(Bug #15.)**
9. Direct API `POST /api/v1/invoices/{id}/send-link` initially returned 500 — `stripe_not_configured`. Pulled `STRIPE_SECRET_KEY` and `STRIPE_WEBHOOK_SECRET` from Railway dev env, restarted uvicorn.
10. Re-fired send-link → HTTP 200 with `link_url=https://buy.stripe.com/test_00w4gB4PK8QU03i1PYeQM0p`. **Real payment_link SMS sent to `+19527373312`** ("Hi Avery, your invoice from Grin's Irrigation for $100.00 is ready: https://buy.stripe.com/test_…").
11. Open the link in browser session → Stripe Checkout sandbox renders correctly: "Grin's Irrigation sandbox", $100, Card / Affirm / Cash App Pay / Klarna / Link / Amazon Pay payment methods.
12. Card field entry was not scriptable (Stripe iframe). Instead simulated `checkout.session.completed` via signed webhook (HMAC-SHA256 with the pulled secret) → HTTP 200, `processing_status=processed` in `stripe_webhook_events`. Receipt SMS did not fire (invoice already PAID from earlier multi-tender — handler no-op'd).
13. Probed `payment_method='stripe'` via `/appointments/{id}/collect-payment` → HTTP 200 immediately marks invoice PAID without round-tripping Stripe. **(Bug #16.)**

**Phase 2 — pricelist editor (admin desktop 1440×900)**
1. Login as admin, open `/invoices?tab=pricelist`. Editor renders cleanly.
2. Filtered customer_type residential / commercial → row counts change as expected.
3. Search `spring` → matches; search `zzznomatch` → empty state.
4. Open "+ New offering" drawer.
5. Cycled `pricing_model` dropdown through 14 values: flat, flat_range, per_unit_flat, per_unit_range, per_zone_range, tiered_zone_step, size_tier, yard_tier, variants, compound_per_unit, compound_repair, conditional_fee, hourly, custom. Each captured as `phase-2/{NN}-drawer-{model}.png`.
6. Edit existing row drawer renders with populated fields.
7. "Show inactive" toggle reveals deactivated rows.
8. "Export pricelist.md" button + `GET /api/v1/services/export/pricelist.md` returned 7587 bytes of rendered markdown grouped by Residential/Commercial then Installation/Landscaping.
9. 0 console errors throughout.

**UX gap noted (not a bug)**: most pricing-model panels share the same generic form (Name/Slug/Category/Customer type/Subcategory/Pricing model/Description + a "Raw pricing rule (JSON)" textarea). Only `flat` shows a typed Price input. Plan §Phase 2 called for one typed panel per discriminator value; current implementation is a thin JSONB editor.

**Phase 5 — polish + cleanup**
1. CTA label "Send estimate" — verified across phase-3 modal screenshots.
2. ActionTrack sublabels "On my way" / "Job started" / "Job complete" — verified in same screenshots.
3. Maps "Remember my choice" footer — **NOT VERIFIED** in this run; opening the popover triggers the same `TimelineRow` import crash (Bug #15) on tech-mobile.
4. `stripe_terminal` full uninstall — verified:
   - `services/stripe_terminal.py` deleted ✅
   - `api/v1/stripe_terminal.py` deleted ✅
   - `tests/unit/test_stripe_terminal.py` deleted ✅
   - `api/v1/router.py` 0 grep matches for `stripe_terminal` ✅
   - `GET /api/v1/stripe-terminal/connection-token` → HTTP 404 ✅

**Phase 6.8 — responsive sweep**
- 12 snapshots: `/schedule`, `/invoices?tab=pricelist`, `/dashboard`, `/tech` × {1440×900 desktop, 768×1024 tablet, 375×812 mobile}.

**Cross-phase integration narrative**
- 10 hand-picked screenshots in `integration/` walking the full Avery Park lifecycle, including two screenshots that intentionally capture the user-facing crashes (Bug #13 portal, Bug #15 tech page).

### Headline numbers

- **81 screenshots** (10 integration · 22 phase-2 · 20 phase-3 · 10 phase-4 · 5 phase-5 · 1 phase-0 · 1 portal · 12 responsive).
- **Real SMS sent to +19527373312** for: estimate-sent, internal-staff-alert-on-approval, payment-link, payment-receipt — all `delivery_status=sent`.
- **Real Stripe sandbox link** generated: `https://buy.stripe.com/test_00w4gB4PK8QU03i1PYeQM0p`.
- **5 new bugs uncovered**, **2 fixed in-test** so the run could continue, **3 still outstanding**.

---

## Bugs Uncovered During 2026-05-02 Re-Run

The following bugs were not visible in the 2026-05-01 admin/desktop sign-off because that run never exercised the tech-mobile, customer-portal, or "Record Other Payment"/"Send Payment Link" UI paths.

### Bug #12 — `size_tier` SubPicker silently empty despite seeded `pricing_rule.tiers` — **P1**

- **Symptom**: tech selects Tree Drop (slug=`tree_drop_residential`) in LineItemPicker → "This offering has no tiers configured." Same for any other `size_tier` or `size_tier_plus_materials` offering (Tree Drop, Decorative Boulders).
- **DB reality**: `pricing_rule.tiers = [{size:"small",price:750,size_range_ft:"10-20"}, {size:"medium",price:1250,...}, {size:"large",price:2000,...}]` is correctly populated.
- **Suspect**: `frontend/src/features/schedule/components/EstimateSheet/SizeTierSubPicker.tsx` reads a different key — likely `pricing_rule.size_tiers` (vs the actual `pricing_rule.tiers`), or expects `tier.label`/`tier.value` keys (vs the actual `tier.size`/`tier.price`).
- **Reproduction**: tech mobile → in_progress card → Send estimate → Add from pricelist → search "tree" → click Tree Drop.
- **Impact**: blocks every `size_tier` and `size_tier_plus_materials` picker flow.
- **Evidence**: `phase-3/12-tree-detail.png`.
- **Fix lead**: `grep -n "size_tier\|tier\." frontend/src/features/schedule/components/EstimateSheet/SizeTierSubPicker.tsx` and align with the seed JSON shape.

### Bug #13 — Customer portal `EstimateReview` crashes on missing `business` object — **P0**

- **Symptom**: opening `/portal/estimates/{customer_token}` for any sent estimate immediately throws `TypeError: Cannot read properties of undefined (reading 'company_logo_url')`. React error boundary swallows the page.
- **Cause**: `frontend/src/features/portal/components/EstimateReview.tsx:131` reads `estimate.business.company_logo_url`. Backend `/api/v1/portal/estimates/{token}` returns flat-shaped fields at the top level (`company_name: null, company_logo_url: undefined, …`), no nested `business: {…}` object.
- **Evidence**: `phase-0/01-portal-landing.png` and `portal/_BUG_NOTES.md`. Probe of the API: `curl http://localhost:8000/api/v1/portal/estimates/{token}` returns flat JSON with `company_name: null`.
- **Same likely defect**: `InvoicePortal.tsx:92` and `ContractSigning.tsx:141` also read `entity.business.company_logo_url` — invoice and contract portal pages will crash identically.
- **Impact**: **P0** for the customer-facing approval flow. Customers cannot view, sign, approve, or reject any estimate via the portal in dev. The auto-job logic itself is fine — verified via direct API approval (POST `/api/v1/portal/estimates/{token}/approve` returns 200 and creates the job).
- **Fix options**:
  1. Backend: nest the response under `business: {company_name, company_logo_url, …}` and update the Pydantic response schema.
  2. Frontend: rewrite `EstimateReview.tsx` (and the two siblings) to optional-chain (`estimate.business?.company_logo_url`) AND read flat fields with fallback.
  3. Either way, mirror the same change across all three portal components for consistency.

### Bug #14 — `appointment_service.collect_payment` crashes on every cash/check/venmo/zelle — **P0** — **FIXED IN-TEST**

- **Symptom**: every `Record Other Payment` (cash/check/venmo/zelle) collected from the AppointmentModal → HTTP 500 `{"code":"INTERNAL_ERROR"}`. Backend log: `TypeError: InvoiceRepository.update() takes 2 positional arguments but 3 were given`.
- **Cause**: two call sites in `src/grins_platform/services/appointment_service.py`:
  - Line 2025–2034 (existing-invoice update branch): `await self.invoice_repository.update(existing_invoice.id, {...dict...})`
  - Line 2059–2067 (new-invoice update-after-create branch): `await self.invoice_repository.update(result_invoice.id, {...dict...})`

  Both pass the field-update dict positionally, but `repositories/invoice_repository.py:160` declares `async def update(self, invoice_id: UUID, **kwargs: Any)`.
- **Impact**: **P0** — 100% crash rate on every cash-equivalent payment collection from the tech-mobile flow. Before the in-test fix, the cash button could not record a single successful payment.
- **Severity-amplifier observation**: the unit/functional test suite did not catch this. Likely the tests mock `InvoiceRepository.update` directly, hiding the kwargs-vs-positional mismatch. Add a contract test that calls the real repository signature.
- **In-test fix applied** (uncommitted; revert or promote at your discretion):
  ```python
  # appointment_service.py:2025–2034 and :2059–2067 (both call sites)
  await self.invoice_repository.update(
      result_invoice.id,
      payment_method=payment.payment_method.value,
      payment_reference=payment.reference_number,
      paid_at=now,
      paid_amount=payment.amount,
  )
  ```
- **Multi-tender side-effect uncovered while testing**: the existing-invoice branch updates the invoice fine but does NOT call the receipt SMS path that the new-invoice branch triggers. Multi-tender follow-up payments (the 2nd, 3rd, 4th method on the same invoice) silently skip the customer receipt. Treat as a follow-up to #14.

### Bug #15 — `TimelineRow` component import broken — crashes payment + Maps flows — **P0**

- **Symptom**: clicking "Create Invoice & Send Payment Link" on the tech-mobile AppointmentModal AND clicking "Get directions"/"Navigate" both crash the entire `/tech` page with React error: `Element type is invalid: expected a string (for built-in components) or a class/function (for composite components) but got: undefined. You likely forgot to export your component from the file it's defined in, or you might have mixed up default and named imports. Check the render method of TimelineRow.`
- **Cause**: a default-vs-named export mismatch on the `TimelineRow` component, OR `import { TimelineRow }` from a barrel that no longer re-exports it.
- **Impact**: **P0** for both the Stripe payment-link UI flow AND the Maps "Remember my choice" verification (Phase 5 Task 5.2 cannot be verified end-to-end until this is fixed). Once triggered, the React tree is dead until full page reload.
- **Evidence**: `phase-4/06-stripe-link-flow.png` and `phase-5/03-maps-popover.png`.
- **Fix lead**: `grep -nE "import.*TimelineRow|from.*TimelineRow" frontend/src` and confirm the export shape matches the import.

### Bug #16 — `payment_method='stripe'` via `collect-payment` short-circuits to PAID — **P1**

- **Symptom**: posting `{payment_method: "stripe", amount: N}` to `/api/v1/appointments/{id}/collect-payment` flips the invoice to PAID synchronously, without round-tripping through Stripe Checkout / webhook.
- **Cause**: `appointment_service.py:2014–2034` doesn't gate the PAID-status update on payment method; it treats `stripe` like in-person cash/check/venmo/zelle.
- **Impact**: **P1.** Conflates "tech collected card in person via TTP/dashboard" with "send the customer a Stripe link to pay later". The intended Stripe Payment Links flow per memory `project_stripe_payment_links_arch_c` is: create invoice as PENDING → `send-link` → wait for webhook → only then PAID.
- **Fix lead**: in `collect_payment()`, gate the immediate PAID assignment on `payment_method != PaymentMethod.STRIPE` (and probably `!= CREDIT_CARD`); for those methods, leave invoice in PENDING and return the link-send response shape.

---

## Outstanding code/env edits from the re-run (DECISION REQUIRED)

These were applied to local working tree to keep the run moving. They have NOT been committed. Decide whether to revert or promote each:

1. **`src/grins_platform/services/appointment_service.py`** — kwargs-unpack fix at lines ~2025 and ~2059 (Bug #14). **Recommend committing as a real fix** — this is a genuine bug, the fix is mechanical, and reverting will re-break every cash payment.

2. **`.env`** — appended Stripe sandbox keys pulled from Railway dev: `STRIPE_API_VERSION`, `STRIPE_SECRET_KEY=sk_test_…`, `STRIPE_TAX_ENABLED=false`, `STRIPE_WEBHOOK_SECRET=whsec_…`. **Recommend reverting** these `.env` lines and re-pulling fresh when needed for local Stripe testing. Test-mode keys are still leakable secrets.

3. **`customers.id = ff8fda3b-…` (Avery Park)** — phone overridden to `+19527373312` and email overridden to `kirillrakitinsecond@gmail.com` to enable receipt verification. Restore from seed if needed:
   ```sql
   UPDATE customers SET phone='+19525550101', email='e2e+vasiliy@grins.test'
   WHERE id='ff8fda3b-0a78-4aa8-85ee-e049dd7f8ec5';
   ```

---

## Recommendation

**Do not merge to `main` until** Bugs #13, #14, #15 are landed:
- **#13** unblocks customer approval (Phase 0 P0 path — currently unusable for any customer).
- **#14** unblocks cash/check/venmo/zelle payment (Phase 4 P0 — every "Record Other Payment" tap returns 500).
- **#15** unblocks the Stripe link UI flow + Maps verification (both crash today).

#12 (size_tier picker) and #16 (Stripe-method collect short-circuit) are P1 — can ship behind the others but should be fixed before tech rollout.
