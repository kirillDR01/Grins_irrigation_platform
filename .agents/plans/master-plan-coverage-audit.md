# Master E2E Testing Plan — Coverage Audit (2026-05-02)

This audit walks every plan, spec, runbook, bughunt, scheduling-gap, and steering doc in the repo against `.agents/plans/master-e2e-testing-plan.md` (24 main phases P0–P24 plus sub-phases P4a/4b/4c/4d/22b/23b) and produces a gap report. Findings are partitioned into:

1. **Per-source coverage table** — CONFIRMED / PARTIAL / MISSING counts.
2. **MISSING (real)** — scenarios about *currently-implemented* features that have no master-plan step. These should be added.
3. **PARTIAL** — surfaces named but specific edge cases not stepped. Extend existing phases.
4. **Out-of-scope (planned-but-not-built)** — scenarios from gap docs / plans that describe features that don't yet exist in source. Per the rule "don't invent features", these are NOT added to the master plan.
5. **Stale references** — claims in source docs that no longer match current code.
6. **Net-new features warranting whole new phases** — currently zero (HOA was the only candidate; verified absent from source → out-of-scope).

---

## 1. Inventory summary

156 source files surveyed. ~2,150 testable scenarios catalogued. Top 10 hotspots by scenario count:

| Rank | File | Scenarios |
|---|---|---|
| 1 | `.kiro/specs/schedule-workflow-improvements/activity.md` | 25 |
| 2 | `.kiro/specs/ui-redesign/tasks.md` | 25 |
| 3 | `scripts/e2e/test-schedule.sh` | 22 |
| 4 | `.agents/plans/master-e2e-testing-plan.md` | 31 (target) |
| 5 | `.agents/plans/schedule-and-appointment-modal-mobile-responsive.md` | 20 |
| 6 | `scripts/e2e/test-leads.sh` | 18 |
| 7 | `.agents/plans/schedule-estimate-visit-handoff.md` | 18 |
| 8 | `.agents/plans/appointment-modal-payment-estimate-pricelist-umbrella.md` | 18 (already folded) |
| 9 | `bughunt/2026-04-29-ai-scheduling-system-validation.md` | 12 |
| 10 | `bughunt/2026-04-16-high-fixes-plan.md` | 12 |

---

## 2. Per-source coverage — headline

| Source group | Files | Scenarios | CONFIRMED | PARTIAL | MISSING |
|---|---|---|---|---|---|
| Bughunts | 20 | ~95 | 65 (68%) | 12 (13%) | 18 (19%) |
| Scheduling gaps | 16 | 76 | 12 (16%) | 10 (13%) | 54 (71%) |
| Testing Procedure | 13 | 21 | 19 (90%) | 1 (5%) | 1 (5%) |
| Top-12 plans | 12 | ~150 | ~50% | ~42% | ~8% |
| Remaining plans + kiro specs | ~30 | ~150 | ~75% | ~20% | ~5% |

**Re-classified after source verification**: of the 18 "MISSING" bughunt scenarios, 7 were false positives (already covered by P4a/P4b/P4c/P4d folded from umbrella), leaving **11 genuinely MISSING**. Of the 54 "MISSING" scheduling-gap scenarios, **48 are out-of-scope** (proposed-but-unbuilt features), leaving **6 genuinely MISSING**.

After the re-classification, the bar is much smaller:

| Adjusted bucket | Count |
|---|---|
| **MISSING (real, must add)** | ~25 scenarios |
| **PARTIAL (extend existing phase)** | ~30 scenarios |
| **Out-of-scope (planned-but-unbuilt)** | ~75 scenarios |
| **Stale references (claims no longer match source)** | ~8 |

---

## 3. MISSING — real gaps that need to be added

For each, I include the recommended master-plan phase to extend, the exact regression check, and the verified source anchor.

### M-01 — Job action button visibility (Start Job / Mark Complete / Cancel Job)
- **Source**: `bughunt/job_actions_missing.md` (lines 9–47).
- **Bug summary**: Frontend dropdown in `JobList.tsx` previously checked `job.status === 'scheduled'` (a status that never existed) so "Start Job" / "Mark Complete" never rendered.
- **Source verification**: `JobList.tsx:409` now correctly checks `job.status === 'to_be_scheduled'` for "Start Job" and `:414` `=== 'in_progress'` for "Mark Complete". `:420` Cancel Job. **Bug fixed in current source.**
- **Master plan coverage today**: P7 step 10 ("Status transitions") is too vague — doesn't verify the dropdown menu items render at the right statuses.
- **Recommendation — extend P7**: Add explicit step: from a `to_be_scheduled` job row, open `[data-testid='job-actions-${id}']` dropdown, verify "Start Job" item present and clickable; transition to `in_progress`, verify "Mark Complete" present, "Start Job" gone; transition to `completed`, verify both gone but "Cancel Job" gone (per `:420` `!['cancelled', 'completed'].includes(...)`).

### M-02 — Session-refresh stale Authorization header regression
- **Source**: `bughunt/session_timeout.md` (lines 9–31).
- **Bug summary**: After axios interceptor refreshes a 401, the retry was using the stale `Authorization` header from `apiClient.defaults`, causing a refresh loop and premature `/login?reason=session_expired` redirect. Timer was also not rescheduled.
- **Source verification**: `frontend/src/core/api/client.ts:61` updates `apiClient.defaults.headers.common['Authorization']` on refresh; `:66` dispatches `'token-refreshed'` CustomEvent; `AuthProvider.tsx` listens and reschedules. **Bug fixed in current source.**
- **Master plan coverage today**: P1 step 5 ("Refresh token: trigger a 401, verify silent refresh") is correct but does NOT verify the specific bug — it doesn't assert no redirect-to-login loop and doesn't verify `'token-refreshed'` event fires.
- **Recommendation — extend P1 step 5**: Add sub-steps: (a) clear `access_token` cookie via `agent-browser eval`, (b) make a state-changing request, (c) verify response 200 (not redirect to /login), (d) verify console saw exactly one `'token-refreshed'` event, (e) verify subsequent request still sends fresh Authorization header (not stale), (f) verify proactive refresh timer was rescheduled (eval `window._authRefreshTimerScheduledAt`).

### M-03 — Capacity bar `utilization_pct` field render
- **Source**: `bughunt/2026-04-30-resource-timeline-loading-and-capacity-bugs.md`.
- **Source verification**: `utilization_pct` exists in 8 files including `src/grins_platform/api/v1/schedule.py`, `services/schedule_generation_service.py`, `schemas/schedule_generation.py`, `schemas/ai_scheduling.py`. **Currently implemented.**
- **Master plan coverage today**: P18 is generic about "AI Scheduling — Resource Timeline, Chat, Briefing, Generate, Alerts". Doesn't verify capacity bar utilization_pct rendering, doesn't verify "Loading…" doesn't persist after data loads.
- **Recommendation — extend P18**: Add steps: (a) open `/schedule` resource timeline view, wait `networkidle`, (b) `agent-browser get text "[data-testid='capacity-bar-pct']"` → assert non-empty integer 0–100, (c) screenshot `capacity-bar-loaded.png`, (d) verify "Loading…" text not present after 5s.

### M-04 — Appointment state-machine transition rejection
- **Source**: `.agents/plans/enforce-appointment-state-machine.md`; `feature-developments/scheduling gaps/gap-04-state-machine-not-enforced.md`.
- **Source verification**: `VALID_APPOINTMENT_TRANSITIONS` / `can_transition_to` exists in `services/appointment_service.py`, `repositories/appointment_repository.py`, `models/appointment.py`. **Currently implemented.**
- **Master plan coverage today**: P10 step 3 covers reschedule transition; no step exercises *invalid* transition rejection.
- **Recommendation — extend P10 (or add P10b)**: Attempt `PATCH /api/v1/appointments/{id}` with status transitions known invalid (e.g., COMPLETED → SCHEDULED, CANCELLED → IN_PROGRESS) → verify 422 with `InvalidStatusTransitionError`. Verify allowed transitions (SCHEDULED → CONFIRMED, IN_PROGRESS → COMPLETED) still pass.

### M-05 — Mobile modal overlap regression (sticky action bar hides Confirm/Cancel)
- **Source**: `bughunt/2026-03-26-e2e-battle-test.md` (lines 81–101).
- **Bug summary**: On mobile viewport, the sticky bottom bar overlapped Confirm/Cancel buttons in the appointment modal, making them un-clickable.
- **Source verification needed at audit time**: This was a FE layout bug in 2026-03-26. Plans `schedule-and-appointment-modal-mobile-responsive.md` and `schedule-visit-modal-full-redesign.md` describe the responsive redesign that may have fixed this; agents would need to re-verify the layout in current source. **For now, treat as testable at the symptom level** in P22.
- **Master plan coverage today**: P22 sweeps three viewports (375 / 768 / 1440) but doesn't explicitly assert "no overlapping CTA buttons in modals on 375px".
- **Recommendation — extend P22**: At 375px viewport, open AppointmentDetail modal, scroll to bottom, assert Confirm/Cancel buttons are visible and clickable (use `agent-browser eval "el.getBoundingClientRect()"` to verify y-position above sticky-bar y-position).

### M-06 — Lead form `min="1"` zone validation (HTML attr bypass)
- **Source**: `bughunt/2026-03-26-e2e-battle-test.md` (lines 62–74).
- **Bug summary**: Public lead form accepted `0` zone count via keyboard despite `min="1"` HTML attribute, and proceeded to create a Stripe checkout session.
- **Source verification needed at audit time**: Plans suggest validation moved to client + server. Treat as testable.
- **Master plan coverage today**: P2 (Marketing Site → Lead Intake) tests lead creation but no edge case for invalid zone count.
- **Recommendation — extend P2**: Add edge-case step: submit lead form with zone count `0` via `agent-browser eval "input.value='0'; input.dispatchEvent(new Event('change'))"` → verify form rejects (server returns 422 OR client refuses submit).

### M-07 — Lead form terms checkbox required
- **Source**: `bughunt/2026-03-26-e2e-battle-test.md` (lines 123–133).
- **Bug summary**: Terms checkbox was rendered but always serialized as `false`.
- **Master plan coverage today**: P2 mentions sms_consent but not the standalone Terms checkbox.
- **Recommendation — extend P2**: After lead submit, verify the persisted lead row has `terms_accepted=true` (or whatever the persisted column is per `migrations/versions/`); also verify with checkbox unchecked the form rejects.

### M-08 — Idempotent repeat-Y short-circuit
- **Source**: `.agents/plans/repeat-confirmation-idempotency.md`; `bughunt`-derived gap.
- **Source verification**: This is a *proposed fix*. The fix may or may not be merged. Grep `services/sms_inbound_service.py` or `_handle_confirm` for short-circuit logic before deciding.
- **If implemented**: extend P9 with E2-bis: "Reply Y twice → verify second send does NOT re-transition status, but DOES send reassurance SMS".
- **If not implemented**: out-of-scope (do NOT add).

### M-09 — Stripe Terminal tap-to-pay flow (gated on hardware)
- **Source**: `.agents/plans/stripe-tap-to-pay-and-invoicing.md`.
- **Source verification**: Memory entry `project_stripe_payment_links_arch_c.md` says "M2 hardware shelved". Architecture C live (Stripe Payment Links via SMS).
- **Recommendation**: Mark Stripe Terminal as **out-of-scope** per memory entry — feature shelved. Not a real gap.

### M-10 — Resource timeline cache invalidation on staff reassignment
- **Source**: `.agents/plans/fix-resource-timeline-loading-and-capacity-bugs.md`; `schedule-resource-timeline-view.md`.
- **Source verification**: TanStack Query cache keys exist; behavior verifiable.
- **Master plan coverage today**: P18 doesn't exercise stale-cache scenario.
- **Recommendation — extend P18**: After re-assigning an appointment to a different tech, verify capacity bar for both old and new tech updates within 1s (cache invalidation). Use `agent-browser eval` to query specific tech utilization cells.

### M-11 — Estimate appointment conflict detection in ScheduleVisit modal
- **Source**: `.agents/plans/schedule-estimate-visit-handoff.md`.
- **Source verification**: `useScheduleConflicts` or similar hook should exist; verify before adding.
- **Master plan coverage today**: P4 step 5 ("schedule visit") doesn't test conflict overlay.
- **Recommendation — extend P4**: When picking a slot that overlaps an existing appointment, verify red "conflict" banner renders + Save button disabled until reslotted.

### M-12 — Stripe Payment Link reconciliation: dispute path
- **Source**: `.agents/plans/stripe-payment-links-e2e-bug-resolution.md`; verified Stripe `charge.dispute.created` is part of webhook handler.
- **Master plan coverage today**: P14 covers `checkout.session.completed` and refund. Dispute path mentioned in `e2e/master-plan/sim/stripe_event.sh` wrapper but no explicit phase step.
- **Recommendation — extend P14**: Add step: trigger `charge.dispute.created` via `sim/stripe_event.sh charge.dispute.created` → verify invoice status transitions to `disputed`, customer notification suppressed, dashboard alert created.

### M-13 — City-priority job sorting
- **Source**: `.agents/plans/pick-jobs-city-requested-priority-fixes.md`.
- **Source verification needed**: confirm city-based sort exists in `pick-jobs` page. Likely implemented per plan `pick-jobs-ui-redesign-persistent-tray.md`.
- **Master plan coverage today**: P7/P8 don't test city sorting.
- **Recommendation — extend P7 or P8**: Verify pick-jobs list sorts by city (group cluster rendering) and city-priority badge appears.

### M-14 — Webhook empty-`last_name` resilience
- **Source**: `.agents/plans/webhook-empty-last-name-fix.md`.
- **Source verification**: schema accepts empty/null `last_name`; verified via plan reference.
- **Master plan coverage today**: P21 covers webhooks broadly but doesn't test malformed-but-valid payloads.
- **Recommendation — extend P21**: Add step: POST to inbound webhook with `last_name=""` → verify 200 + customer row created with `last_name=NULL` (or empty), no 500.

### M-15 — Send Confirmation button on DRAFT appointments (M-1 from medium-bugs)
- **Source**: `bughunt/2026-04-16-medium-bugs-plan.md` M-1.
- **Master plan coverage today**: P8 covers send-confirmation but doesn't explicitly test from DRAFT (vs SCHEDULED).
- **Recommendation — extend P8**: After creating a DRAFT appointment (no SMS yet), verify `[data-testid='send-confirmation-btn-${id}']` renders and click sends SMS, transitions to SCHEDULED.

### M-16 — Stripe Payment Link SMS-soft-fail transparency
- **Source**: `bughunt/2026-04-28-stripe-payment-links-e2e-bugs.md` Bug #3.
- **Master plan coverage today**: P14 step 8 covers this but the "transparency" detail (UI surfaces `attempted_channels` array, NOT silent fallthrough) is not explicit.
- **Recommendation — extend P14 step 8**: After `send-link` failure on SMS but success on email, verify response body includes `attempted_channels: ['sms','email']` and `sms_failure_reason` non-null. UI shows both attempts.

### M-17 — Surcharge price card vs. checkout drift
- **Source**: `bughunt/2026-03-26-e2e-battle-test.md` (lines 25–51).
- **Bug summary**: Public marketing card shows $7.50/zone residential, but Stripe checkout charged $8.00.
- **Master plan coverage today**: P2 covers lead form but not card-vs-checkout consistency.
- **Recommendation — extend P2 or add P15.1**: Cross-check that marketing card pricing matches the Stripe price in `service_packages` (`api/v1/checkout.py`). Programmatic API call: `GET /api/v1/marketing/pricing` vs. `GET /api/v1/checkout/prices` and assert equality per zone count.

### M-18 — Day-2 reminder for no-reply confirmations (from gap-10)
- **Source**: `feature-developments/scheduling gaps/gap-10-static-no-reply-escalation.md` Phase 1.
- **Source verification**: Manual queue exists. **Auto-reminder Phase 1 fix is not implemented.** → out-of-scope.

---

## 4. PARTIAL — extend existing phases

The following surfaces are mentioned in the master plan but lack the specific edge case detail. Each maps to a small extension within an existing phase, NOT a new phase.

| # | Source | Existing phase | What to add |
|---|---|---|---|
| P-01 | `bughunt/2026-04-16-cr1-cr6-e2e-verification.md` CR-3 | P9 | Verify `provider_thread_id` is persisted on outbound confirmation send (was a dev-env blocker per CR-3). |
| P-02 | `bughunt/2026-04-16-cr1-cr6-e2e-verification.md` CR-4 | P14 / P21 | Verify all 4 `billing_reason` branches of `invoice.paid` Stripe webhook (subscription_create, subscription_cycle, subscription_update, manual). |
| P-03 | `gap-01` 1.A | P10 | Already covered as "Duplicate R rows" — keep as-is, this was already validated CONFIRMED. |
| P-04 | `gap-01` 1.B | P10 | Verify reschedule cannot be resolved when appointment is in EN_ROUTE / IN_PROGRESS state (412 Precondition Failed expected). |
| P-05 | `gap-04` 4.A | P7 (state machine, see M-04) | Test that direct DB update bypassing service layer would NOT pass `@validates` (unit test territory; mention as out-of-E2E-scope but cite). |
| P-06 | `bughunt/2026-04-16-medium-bugs-plan.md` M-12 | P13 | Verify `days_until_due` and `days_past_due` are returned server-side (computed columns). |
| P-07 | `feature-developments/.../gap-05` STOP audit | P9 E8 | After STOP, query `/api/v1/audit-log?event_type=sms_consent_revoked` and verify entry. |
| P-08 | `schedule-visit-modal-full-redesign.md` | P22 / P8 | Visual regression: ScheduleVisit modal slate/white theme + tone-based event cards. Capture full-page screenshot, compare baseline. |
| P-09 | `schedule-estimate-visit-handoff.md` (drag boundary) | P4 | Verify drag past midnight or past week-edge prevents commit + shows boundary feedback. |
| P-10 | `pick-jobs-ui-redesign-persistent-tray.md` | P8 | Verify persistent tray remains visible across pick-jobs interactions; tray scroll-position sticky. |
| P-11 | `appointment-modal-secondary-actions.md` (notes/tags/photos/reschedule/mark-contacted) | P11 (tech mobile) + admin AppointmentDetail | Each of the 5 actions has its own UI affordance — verify each renders and persists. Could be one step per action under P11 or a single sub-section "Secondary actions matrix". |
| P-12 | `thread-correlation-hardening.md` (post-cancel "R") | P9 / P10 | After CANCEL, customer replies "R" → verify it does NOT reactivate the cancelled appointment, but DOES log a `stale_thread_reply` row. |

---

## 5. Out-of-scope — planned-but-not-built (do NOT add)

Per the rule "if a source doc claims a feature that doesn't exist, mark stale and move on", the following scenarios reference features that do NOT exist in current source. They are out-of-scope until built. Citing source for traceability so a future audit can re-classify if/when implementation lands.

| # | Source | Why out-of-scope |
|---|---|---|
| O-01 | `feature-developments/.../gap-02` (repeat-Y reassurance SMS) | Proposed; verify `_handle_confirm` short-circuit and reassurance SMS not in source. |
| O-02 | `gap-03` 3.A / 3.B (thread-id capture across reschedule SMS, stale-thread reactivation handler) | Plans propose `thread_id` propagation; not in current `services/sms` code paths. |
| O-03 | `gap-05` audit trail extensions for Y / R / opt-out | Proposed audit_log inserts not present in `_handle_confirm` / `_handle_reschedule` / consent-flip. |
| O-04 | `gap-06` informal opt-out triage UI / badge | Frontend page exists at `/alerts/informal-opt-out` per router but the badge-on-card and dashboard-widget are not built. Partial — would split. |
| O-05 | `gap-09` MMS / Unicode / i18n | Not implemented; backlog per gap doc. |
| O-06 | `gap-10` Phase 1 auto-reminder | Not implemented. |
| O-07 | `gap-11` AppointmentDetail timeline endpoint (`GET /api/v1/appointments/{id}/timeline`) | Endpoint not in router. |
| O-08 | `gap-12` calendar-card reply-state badges | Not in `CalendarView`. |
| O-09 | `gap-13` conversation threading endpoint (`GET /api/v1/customers/{id}/conversation`) | Endpoint not in router. |
| O-10 | `gap-14` alert types AT-1..AT-6 (PENDING_RESCHEDULE_REQUEST etc.) | Not in `models/enums.py` `AlertType`. |
| O-11 | `gap-15` queue refetchInterval polling | Not configured on `useRescheduleRequests` etc. |
| O-12 | `gap-16` unified inbox `/inbox` page + endpoint | Page and endpoint not in source. |
| O-13 | `.agents/plans/hoa-and-group-signup-codes.md` — entire HOA / signup-code feature | Verified absent: `grep -i "signup_code\|hoa_group\|hoa_id\|group_code" src/` returns 0 matches. Plan is brand-new and feature is unimplemented. |
| O-14 | `.agents/plans/stripe-tap-to-pay-and-invoicing.md` — Stripe Terminal tap flow | Memory `project_stripe_payment_links_arch_c.md`: "M2 hardware shelved". Feature deliberately not built. |
| O-15 | `.agents/plans/force-light-mode-only.md` | UI/theme constraint, not E2E-testable behavior. |
| O-16 | `bughunt/2026-04-29-pre-existing-tsc-errors.md` | TypeScript errors are unit-checked (`npm run typecheck`), already in P23. |

---

## 6. Stale references — claims that no longer match current source

| # | Source | Stale claim | Current truth |
|---|---|---|---|
| S-01 | `bughunt/2026-04-14-lead-form-sms-consent-rollback.md` L159 | Trailing newline in `VITE_API_URL` causing fetch failures | Verify in current Vercel env; if fixed, mark resolved. |
| S-02 | `bughunt/2026-04-14-lead-form-sms-consent-rollback.md` L173 | `?search=<phone>` doesn't match phone digits | Verify via `GET /api/v1/leads?search=9527373312` in current API. |
| S-03 | `bughunt/2026-03-27-service-packages-e2e.md` | Pre-existing jobs have wrong priority (all 0) | Data-only one-shot fix at the time; not a regression check. |
| S-04 | `bughunt/2026-03-27-service-packages-e2e.md` | Admin job dates off by one day (UTC conversion) | Verify if `JobDetail.tsx` / API responses use date-only vs. datetime. If fixed, regression-check belongs in P15 (subscription onboarding) at the boundary where job dates are derived. |
| S-05 | `scripts/e2e/*.sh` (26 of 27) | `[name='email']` and `[data-testid='email-input']` login selectors | Already flagged at master plan lines 2356–2370. Re-confirmed: do NOT copy login flow from those scripts. |
| S-06 | `bughunt/2026-04-16-cr1-cr6-e2e-verification.md` CR-3 dev-env blocker | "no `provider_thread_id` persistence in dev" | Verify via `SELECT provider_thread_id FROM sent_messages` on dev — likely fixed; refresh blocker note. |
| S-07 | Various plans referring to `/api/v1/audit-logs` (plural) | Master plan correctly notes singular `/audit-log` is current; older plan-doc references should be updated when those plans are next touched. |
| S-08 | `bughunt/2026-04-29-pre-existing-tsc-errors.md` | List of TSC errors as of 2026-04-29 | Likely changed; rerun `npm run typecheck` to refresh list. |

---

## 7. Recommended new sub-phases (zero new top-level phases)

After re-classification, **no whole new top-level phases are warranted**. All real gaps fit cleanly into extensions of existing phases:

- **P1** (M-02): session-refresh stale-header regression
- **P2** (M-06, M-07, M-17): zone validation, terms checkbox, surcharge consistency
- **P4** (M-11, P-09): conflict detection, drag-boundary
- **P7** (M-01, M-04, M-13): job action visibility, state-machine rejection, city sort
- **P8** (M-15, P-10): DRAFT send-confirmation, persistent tray
- **P9 / P10** (P-04, P-12): late-reschedule rejection, post-cancel "R" handling
- **P11** (P-11): AppointmentDetail secondary-actions matrix (5 actions)
- **P13** (P-06): `days_until_due` / `days_past_due` server-side fields
- **P14** (M-12, M-16): dispute path; SMS soft-fail transparency
- **P18** (M-03, M-10): capacity bar utilization_pct, cache invalidation
- **P21** (M-14): webhook empty-field resilience
- **P22** (M-05, P-08): mobile modal CTA visibility, ScheduleVisit visual regression

Each extension is small (1–5 added steps + a VERIFY sub-block).

---

## 8. Total edit budget

- ~25 MISSING items → ~25 step additions across 11 phases.
- ~12 PARTIAL items → ~12 sub-step additions.
- ~8 stale-reference notes → updates to "Stale-reference watchlist" sections within affected phases.
- 0 new top-level phases.
- Confidence section update to mention this audit pass.

Estimated edit count: **45–55 targeted Edit calls** to the master plan.

---

## 9. Items deliberately excluded from this audit

- Activity logs (`.kiro/specs/*/activity.md`) — these are historical change logs, not test scenarios. Skipped per "what NOT to save" rule (history is in git).
- `feature-developments/CallRail collection/*` — feature spec; SMS-poll feature is blocked on inbound webhook tunnel (memory entry `project_scheduling_poll_responses.md`), so not currently testable.
- 26 stale shell scripts in `scripts/e2e/` — already flagged at master plan lines 2356–2370. Not a re-audit target; their scenarios are subsumed by master-plan phases.
- Steering docs (`.kiro/steering/*`) — describe HOW to test (methodology), not WHAT to test. Already cited in master plan Context References section.

---

## 10. Verification log (samples)

| Claim | Verified by | Result |
|---|---|---|
| P4d covers auto-job-on-approval | `grep -n "Phase 4d" master-e2e-testing-plan.md` | Confirmed at line 902. Bughunt agent's "MISSING" was a false positive. |
| `utilization_pct` exists in source | `grep utilization_pct src/` | 8 files match. Real, testable. |
| `VALID_APPOINTMENT_TRANSITIONS` exists | `grep VALID_APPOINTMENT_TRANSITIONS src/` | Present in `services/appointment_service.py`, `models/appointment.py`. Real. |
| Job action buttons fixed | `grep "to_be_scheduled" frontend/src/features/jobs/components/JobList.tsx` | `:409` correct. Bug closed. Regression-check belongs in P7. |
| Session refresh fix landed | `grep "token-refreshed" frontend/src/core/api/client.ts` | `:66` dispatches event. Bug closed. Regression-check belongs in P1. |
| HOA / signup-code feature | `grep -i "signup_code\|hoa_group\|hoa_id\|group_code" src/` | 0 matches. Out-of-scope. |
| Stripe Terminal | Memory entry `project_stripe_payment_links_arch_c.md` | M2 hardware shelved. Out-of-scope. |
| Gap proposed audit-log inserts | `grep "audit_log\|AuditLog" src/grins_platform/services/sms_inbound_service.py 2>/dev/null` | (Verify before final report) |

---

## 11. Next step

Pending user approval. On approval, apply 45–55 Edit calls grouped by master-plan phase, then update the Confidence section with audit-pass evidence.

---

## 12. 2026-05-02 audit correction — gap-05 / 06 / 11 / 13 / 14 / 15 / 16 reclassified IN-scope

Initial pass through the gap docs misclassified 7 items as "proposed-but-not-built" because the verification greps used the gap-doc shorthand (e.g. `sms_consent_revoked`, `AT-1`) rather than the real symbol names. Re-running the greps with the correct symbols showed every one of these features is actually present in source. The master plan was extended to cover them:

| Item | Initial verdict (wrong) | Re-verified anchor | Master-plan coverage |
|---|---|---|---|
| Hard-STOP audit log | absent | `services/sms/audit.py:131` `log_consent_hard_stop` | **P9 E8 step 5** |
| Informal-opt-out alert + audit chain | absent | `audit.py:140-180`, `sms_service.py:1188` | **P9 E8b** |
| `AlertType` enum (PENDING_RESCHEDULE_REQUEST etc.) | absent | `models/enums.py:618` | **P19 steps 9–10** |
| Unified inbox endpoint | absent | `api/v1/inbox.py:28` | **P20 step 9** |
| Customer conversation endpoint | absent | `api/v1/customers.py:1823` | **P20 step 10** |
| AppointmentDetail timeline endpoint | absent | `api/v1/appointments.py:1013` | **P11 step 15a** |
| Queue `refetchInterval` polling | absent | 4 hooks under `frontend/src/features/schedule/hooks/` | **P20 steps 11–12** |

Genuinely out-of-scope after the second pass:

| Item | Why genuinely absent |
|---|---|
| MMS / Unicode emoji / non-English (gap-09) | No `media_url`, emoji keyword, or locale handling in `services/sms/`. |
| Auto-reminder day-2 path (gap-10 Phase 1) | Only manual `NoReplyReviewQueue` exists. |
| HOA / group signup codes | `grep -i "signup_code\|hoa_group\|hoa_id\|group_code" src/` → 0 matches. |
| Stripe Terminal tap-to-pay | Memory entry `project_stripe_payment_links_arch_c.md`: "M2 hardware shelved". P21 step 12 tests the uninstall instead. |

Net: of the original 18 MISSING bughunt scenarios + 6 reclassified scheduling-gap features, **23 real regression checks** were folded into the master plan across P1, P2, P4, P7, P8, P9, P10, P11, P13, P14, P18, P19, P20, P21, P22. Zero new top-level phases needed.
