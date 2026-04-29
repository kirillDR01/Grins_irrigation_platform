# Scheduling Dashboard — Implementation Status Audit

**Date:** 2026-04-28
**Method:** Read-only static analysis of `Grins_irrigation_platform` (backend + admin dashboard).
**Baseline:** `Gap_Analysis_of_Requirements.md` (2026-03-31), verified against current code (~4 weeks of subsequent change).
**Source requirements:** `AI_Scheduling_System_Requirements.md` plus the freeform requirement description supplied for this audit.

Legend: ✅ Implemented · ⚠️ Partial · ❌ Missing

---

## 1. Admin Scheduling Dashboard (Capacity / Lead Time / Approval)

| Requirement | Status | Evidence | Gap |
|---|---|---|---|
| Approved-jobs review surface | ✅ | `frontend/src/features/schedule/pages/PickJobsPage.tsx`; `GET /api/v1/schedule/jobs-ready` (`api/v1/schedule.py:410`); recent commit `ad0e1ad` (2026-04-15) added persistent fixed tray, tier-aware effective priority | No SLA/conflict pre-check before bulk assign |
| Booked-out lead time | ⚠️ | `LeadTimeIndicator.tsx`; `AppointmentService.calculate_lead_time(max_per_day=10)`; `GET /api/v1/schedule/lead-time` | Single-number badge only ("X days/weeks"); no per-resource utilization, no multi-week heatmap, no backlog-pressure metric |
| Auto-build schedule | ⚠️ | `ScheduleGenerationService.generate_schedule` (`schedule_generation_service.py:56`); solver greedy + local search 30s timeout (`schedule_solver_service.py:59`); endpoints `/generate`, `/preview`, `/insert-emergency`, `/reoptimize` | Admin must initiate per day; no autonomous "build next week", no cross-week scheduling |
| Auto-assign staff | ❌ | Admin manually picks jobs + staff + date in Pick Jobs UI, then bulk-creates DRAFT appointments | No skill-or-capacity-driven auto-assignment |
| 30 decision criteria | ⚠️ 4–5 / 30 | Implemented: #1 proximity (Haversine + Google Distance Matrix in `travel_time_service.py`), #2 drive-time (weight 80), #8 availability (hard), #13 priority (weight 90, tier-aware as of 2026-04-10 commit `82a0c30`); partial: #3 city batching, #7 equipment | 22 criteria still missing: skills, weather, SLA, CLV, customer-resource history, complexity, demand forecast, etc. |
| Conflict resolution | ⚠️ | Hard constraints flag overlaps; `ConflictResolutionService` (cancel + waitlist + fill_gap), `StaffReassignmentService`, `UnassignedJobAnalyzer` explains why a job didn't fit | All resolution is admin-driven; no auto-swap, no "shift by 30 min" suggestion |
| Schedule publish/approve | ⚠️ | DRAFT-gate flow: `/apply` creates DRAFT appointments; admin clicks "Send Confirmation" per appt or "Send All Confirmations" before SMS goes out (`schedule.py:549`) | No "review whole generated schedule, accept/reject as a unit" workflow; no simulate / cost-impact preview |
| AI Chat (admin co-pilot) | ❌ | `SchedulingHelpAssistant`, `NaturalLanguageConstraintsInput`, `ConstraintParserService`, `ScheduleExplanationService` exist for explanation only | None of the 10 admin chat interactions from spec §3 are implemented |
| Alerts/Suggestions panel | ❌ | None | All 20 admin alerts/suggestions from spec §4 missing |

---

## 2. Per-Staff Schedule View (10 required fields)

`GET /api/v1/appointments/staff/{staff_id}/daily/{date}` is staff-scoped (`appointments.py:293`), enforces auth via `CurrentActiveUser`. Mobile UI: `MobileJobSheet.tsx`, `RoutePolyline.tsx` (sequence-ordered), `MapProvider` / `StaffLocationMap.tsx`. Tailwind `md:` / `lg:` breakpoints throughout.

| Field | Status | Evidence / Gap |
|---|---|---|
| 1. Customer name | ✅ | `Appointment.customer_name`; `AppointmentDetail.tsx:126` |
| 2. Customer contact info | ⚠️ | Phone shown (`AppointmentDetail.tsx:208`); email not surfaced |
| 3. Job type | ✅ | `Appointment.job_type` |
| 4. Location/address | ✅ | Property fields rendered as Google Maps deep-link (`AppointmentDetail.tsx:184`) |
| 5. Materials/equipment | ✅ | `materials_needed` JSONB on Appointment; `Job.materials_required` |
| 6. Amount to collect/charge | ❌ | No price/amount field on the appointment response or detail view |
| 7. Time given to complete | ✅ | `time_window_start/end`, `estimated_duration_minutes` |
| 8. Client data/history | ⚠️ | `last_completed` shown; no full visit history surfaced on mobile sheet |
| 9. Client directions (gate code, dogs, access) | ❌ | `Property.gate_code`, `has_dogs`, `access_instructions`, `special_notes` exist on the Property model but are **NOT returned in the appointment schema/detail view** — staff cannot see them at site |
| 10. Other applicable details | ⚠️ | `Appointment.notes` shown; `customer.internal_notes` is admin-scoped |

**Staff isolation:** ✅ properly scoped per-`staff_id`.
**Tablet / responsive:** ✅ Tailwind breakpoints, `md:hidden` MobileJobSheet, 48 px touch targets.

---

## 3. Admin Staff Tracking

| Requirement | Status | Evidence / Gap |
|---|---|---|
| GPS location (live) | ✅ | `staff_location_service.py` Redis 5-min TTL; `GET /api/v1/staff/locations` (`staff.py:208`); 30 s frontend refetch in `StaffLocationMap.tsx` |
| Current job in progress | ⚠️ | `appointment_id` stored alongside location (`staff_location_service.py:34`) but the location response does NOT enrich with appointment details — admin must join client-side |
| Time left to complete | ⚠️ | `time_elapsed_minutes` computed client-side as `defaultEstimatedMinutes − elapsed` (`StaffLocationMap.tsx:229`); no server-side overrun detection or warning |
| Same notes as staff | ⚠️ | Notes exist on appointment; not surfaced in tracking UI |

---

## 4. Customer Auto-Notifications

`NotificationService` defines methods for every required notification — but several are **not called from any status-transition endpoint**, so the automation chain is broken.

| Trigger | Status | Evidence / Gap |
|---|---|---|
| Day-of arrival (morning reminder) | ✅ | `send_day_of_reminders()` (`notification_service.py:334`); time-window message; SMS-consent gated; cron-scheduled |
| On-the-way ETA | ⚠️ | `send_on_my_way(eta_minutes)` (`notification_service.py:425`); endpoint `jobs.py:1248` exists. **Manually triggered only** — no auto-fire on `EN_ROUTE` transition |
| Delay notification with client approval | ⚠️ | `send_delay_notification()` exists (`notification_service.py:561`) but **never called from any code path**. Message is one-way (no Y/N reply path); `job_confirmation_service.py:46` parses Y/R/C for confirms only |
| Arrival notification | ❌ | `send_arrival_notification()` exists (`notification_service.py:504`) but **never invoked**; no `ARRIVED` enum (jumps straight to `IN_PROGRESS`) |
| Completion notification | ⚠️ | `send_completion_notification()` exists (`notification_service.py:628`) — includes job summary, invoice portal link, Google review link — but **NOT called when `jobs.py:1148` transitions to COMPLETED** |
| Next-customer cue (cascade ETA) | ❌ | No "next-in-route" logic anywhere |
| 30–45 min flexible window (gas-stop) | ❌ | `time_window_start/end` is a fixed window; no `flexible_arrival_window` or "request gas-stop buffer" mechanic |

**Channels:** SMS (consent-gated), Email (always). **No native mobile push** anywhere in the codebase (no FCM/APNS).
**Test guard:** ✅ `enforce_recipient_allowlist()` in `sms/base.py:65–93` reads `SMS_TEST_PHONE_ALLOWLIST` and raises `RecipientNotAllowedError`.

---

## 5. Staff On-Site Workflow (11-step process)

| Step | Status | Notes |
|---|---|---|
| Knock / call client | ❌ | No prompt or guided checklist |
| Review job request with client | ❌ | No review surface |
| Adjust prices/service | ⚠️ | Estimate edit possible but no in-flow scope-adjust UX |
| Upsell additional work | ❌ | No upsell prompt; spec §6.7 detects 12 + year-old controllers — not implemented |
| Start / complete job | ✅ | Status transitions exist |
| Present completed job | ❌ | No customer-facing "completed handoff" screen |
| Provide additional estimate | ⚠️ | Estimate creation works; no "during-appointment quick estimate" path |
| Collect payment / portal | ✅ | See §6 |
| Request Google review | ✅ | `appointment_service.request_review()` with 30-day dedup + SMS consent gate; `ReviewRequestResult` schema |
| Update notes | ✅ | `AppointmentNoteService.save_notes` with author/timestamp (`appointment_note_service.py:149`) |
| Mark complete | ✅ | Status transition; **does NOT auto-trigger completion notification** (see §4) |

**No orchestrated checklist exists** — each tool is reachable in isolation, no guided flow that walks staff step-by-step.

---

## 6. Per-Appointment Tools & Payment

> **Architecture note (2026-04-28):** Card payments now flow via **Stripe Payment Links over SMS** (Architecture C). M2 hardware terminal shelved; in-app Tap-to-Pay and Stripe Dashboard flows both rejected. Reconciliation deterministic via `metadata.invoice_id`. The presence of `stripe_terminal.py` in the codebase predates this decision — code exists but the physical-reader path is no longer the active strategy.

| Tool | Status | Evidence / Gap |
|---|---|---|
| Quick estimate | ⚠️ | `estimate_service.py:112` create, `:183` create_from_template, `:248` send via SMS/email + 60-day portal token; auto-route after 4 h unapproved (`AUTO_ROUTE_HOURS`); Resend wired (memory `project_estimate_email_portal_wired`). No on-site signature step; SignWell not in estimate flow (only sales contract) |
| Quick invoice | ✅ | `InvoiceService.create_invoice` (`invoice_service.py:262`), `generate_from_job` (`:866`), `record_payment` (`:642`); UI `InvoiceCreator` |
| Google review request | ✅ | See §5 |
| Notes update | ✅ | `appointment_note_service.py` |
| Standard price list | ✅ | `pricelist.md` reference doc + `ServiceOffering` table (`base_price`, `price_per_zone`, `pricing_model`); `ServiceOfferingService` CRUD |
| Services list catalog | ✅ | Same as above |
| Materials/parts consumed logging | ❌ | `materials_needed` (planned) exists but no `materials_used`/`parts_consumed` post-job tracking; no inventory model |
| Photo / attachment capture | ✅ | `appointment_attachment_service.py:49` (25 MB cap, S3 presigned URLs) |
| Card payment — Stripe Payment Link via SMS (Arch C) | ✅ | Memory `project_stripe_payment_links_arch_c` confirms live; reconciliation via `metadata.invoice_id` |
| Card payment — physical Stripe Terminal | ⚠️ code-only | `stripe_terminal.py:34–131` builds connection token + card-present PaymentIntent; **path shelved** in favor of Arch C |
| Cash / check | ⚠️ | `PaymentMethod` enum has CASH, CHECK, VENMO, ZELLE, ACH (`enums.py:217`); `Invoice.payment_method` field; bughunt H-4 (2026-04-16) noted UI picker dropped cash/check options |
| Portal-pay link | ✅ | `invoice_portal_service.py` 90-day token, sanitized response, Stripe-hosted checkout |
| "Push notification" invoice delivery | ⚠️ | Effectively delivered via SMS Payment Link (Arch C); no native push infrastructure exists. If "push notification" is read literally as mobile push, that is ❌ |

---

## 7. Estimate-as-Contract (T&Cs)

| Item | Status | Evidence / Gap |
|---|---|---|
| Terms text "approved estimate = formal contract" | ❌ | Grep for `terms`, `condition`, `formal contract` returns **nothing** in estimate code paths |
| T&C surfaced in approval portal | ❌ | `approve_via_portal()` records IP / UA but has no T&C checkbox (`estimate_service.py:387`) |
| SignWell on estimates | ❌ | `signwell/client.py` fully built (create, embed, fetch_signed_pdf) and used in **sales pipeline contracts** only — not wired to estimate approval (intentional design choice per memory). Vendor pricing concern open per `project_signwell_pricing_reality` |

---

## 8. Time-Overrun Alerts (staff-facing)

| Item | Status |
|---|---|
| Elapsed-time tracking on appointment | ❌ — only `arrived_at` / `completed_at`; no live elapsed counter |
| "You have N minutes left" warning | ❌ |
| "Move on to next" prompt | ❌ |

Grep for `time_remaining`, `overrun`, `behind_schedule`, `late_alert` returned **zero hits** in services.

---

## 9. Cross-Dashboard Auto-Sync

| Path | Status | Evidence / Gap |
|---|---|---|
| Estimate sent → Sales dashboard (2-day rule) | ⚠️ | `EstimateService.check_unapproved_estimates()` auto-routes after 4 h (note: 4 h, not the 2 days described in the requirement); `SalesPipelineService.record_estimate_decision_breadcrumb` exists; full call chain to dashboard not fully traced |
| Estimate approved → Job creation in scheduling | ⚠️ | DI wired in `portal.py:92`; `convert_to_job` / `force_convert_to_job` referenced in API; verify the call chain end-to-end |
| Special payment instructions → Accounting | ❌ | No `payment_instructions` field on Estimate / Invoice; `accounting_service.py` has YTD / tax / Plaid OCR but no estimate-instruction sync |
| Materials used → Inventory / Accounting | ❌ | No inventory model at all |
| Reschedule needed → back to scheduling queue | ⚠️ | Manual reschedule works (`ConflictResolutionService`); no event-driven re-queue when staff cancels / no-shows |

---

## 10. Tablet / Mobile Access

| Item | Status |
|---|---|
| Responsive layouts (Tailwind `md:` / `lg:`) | ✅ |
| `useMediaQuery('(max-width: 767px)')` adapts SchedulePage; CalendarView uses `listWeek` on mobile, drag-drop disabled; `MobileJobSheet` bottom-sheet | ✅ |
| Viewport meta in `index.html` | ✅ |
| PWA manifest / service worker / install prompt | ❌ — `vite.config.ts` has no `vite-plugin-pwa`, no `manifest.json`, no service worker |
| Native mobile app | ❌ |
| Offline mode | ❌ |

---

## 11. Mass-Text Consent Collection (SMS opt-in)

| Layer | Status | Evidence / Gap |
|---|---|---|
| Consent data model (TCPA-compliant, 7-yr retention) | ✅ | `models/sms_consent_record.py`: `consent_type` (marketing / transactional / operational), `consent_method`, IP / UA, language shown, timestamp, immutable rows |
| Per-type consent check | ✅ | `services/sms/consent.py:39` `check_sms_consent(phone, consent_type)`; hard-STOP precedence |
| Bulk attestation upload (CSV) | ✅ | `bulk_insert_attestation_consent()` (`consent.py:230`) — staff-attestation method recorded |
| 10DLC / brand registration | ✅ | Memory `project_callrail_integration` Phase 0 complete (2026-04-07) |
| Outbound SMS via CallRail | ✅ | `sms/callrail_provider.py` |
| Mass-text "do you consent? reply YES" campaign | ⚠️ | `CampaignService` is generic and supports targeting / audience filtering, but no dedicated **opt-in question template** or admin-side "consent campaign" builder UI surfaced |
| Inbound YES → flip `Customer.sms_opt_in` | ❌ | `CampaignResponseService` parses Option-N replies, but **no handler ties an inbound "YES" string to writing a new `SmsConsentRecord` row + flipping `customer.sms_opt_in`** |
| Inbound CallRail SMS webhook | ❌ | Per memory, Phase 0.5 only verified outbound. Phase 1 inbound webhook receiver (`POST /webhooks/callrail/sms` with HMAC verify) is **not yet implemented** — this is the blocker for closing the consent loop. Also blocks the date-range Scheduling Poll feature (memory `project_scheduling_poll_responses`) |

---

## Net Implementation Score

| Domain | Coverage |
|---|---|
| Data models (Customer, Job, Appointment, Property, Staff, ServiceOffering, ServiceAgreement, etc.) | ~70% |
| Solver / 30 decision criteria | ~15% (4–5 of 30) |
| Auto-scheduling (initiate-then-auto) | ~50% |
| Auto-assignment | 0% |
| Customer notifications (methods exist, triggers don't) | ~30% functional / ~70% latent |
| Per-appointment staff tools | ~60% |
| Payments (Arch C live + portal + cash/check enum; M2 shelved) | ~80% |
| Estimate-as-contract / e-signature on estimate | 0% |
| Time-overrun alerts | 0% |
| Cross-dashboard automation | ~25% |
| Tablet responsive | ~80% (no PWA, no native app, no offline) |
| Consent collection (model great, loop open) | ~50% |
| AI chat (admin + resource), alerts/suggestions | 0% |

---

## Highest-Leverage Gaps to Surface

1. **Notification triggers are wired-but-not-fired.** Methods for delay / arrival / completion exist; `jobs.py` status transitions don't call them. Cheap fix, big behavioral change.
2. **Property access fields missing from staff appointment payload.** `gate_code`, `has_dogs`, `access_instructions` are stored but not in the staff schedule response — staff can't see them at site.
3. **No "amount to collect / charge" on appointment view.** Required field per spec; not in current schema.
4. **Inbound CallRail SMS webhook not implemented.** Without it, mass-text consent collection cannot close the loop and the Scheduling Poll feature stays blocked (Phase 1 dependency per memory).
5. **No estimate-as-contract T&C language / checkbox.** Approval portal records IP / UA but no terms shown; this is a legal / contract gap, not just a feature gap.
6. **No time-overrun mechanism at all.** No elapsed-time tracking, no staff alert, no "skip-to-next" prompt.
7. **No mobile push** — completion-and-invoice "push notification" requirement is delivered via SMS / email only (which is the active Arch C strategy for payment links, but should be acknowledged as not literal push).
8. **No autonomous AI** — entire admin chat, resource chat, alerts / suggestions panel from the requirements doc are 0% built.
9. **No materials-consumed logging** — blocks both inventory and accounting sync.
10. **Capacity view is a single-day badge** — no multi-week heatmap or backlog-pressure metric, so the "how booked-out are we" decision-making goal is only partially served.

---

## What Has Changed Since the 2026-03-31 Gap Analysis

| Date | Commit / Memory | Impact |
|---|---|---|
| 2026-04-07 | `project_callrail_integration` Phase 0 | 10DLC brand + campaign verified; outbound via CallRail live |
| 2026-04-10 | `82a0c30` | Effective priority is now tier-aware (active service-agreement boost) |
| 2026-04-15 | `ad0e1ad` | Pick Jobs page redesigned with persistent fixed tray |
| 2026-04-20 | `project_email_sign_budget` | Budget ceiling <$25/mo set; in-person + remote signing both required |
| 2026-04-25 | `feedback_email_test_inbox` | Code-level email allowlist enforced (`kirillrakitinsecond@gmail.com`) |
| 2026-04-26 | `project_estimate_email_portal_wired` | Estimate email portal live via Resend; supersedes prior "stub" |
| 2026-04-28 | `project_stripe_payment_links_arch_c` | Card payments via Stripe Payment Links over SMS; M2 shelved; reconciliation via `metadata.invoice_id` |

---

*This document is the output of a read-only audit. No code was modified.*
