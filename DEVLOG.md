# Development Log

## Project Overview
Grin's Irrigation Platform — field service automation for residential/commercial irrigation.

## Recent Activity

## [2026-04-26 02:45] - FEATURE: Estimate approval email portal — Resend wired + bounce webhook + internal notifications + sales-entry breadcrumb + gate correction

### What Was Accomplished
- Resend Python SDK plugged into `EmailService._send_email`; previously a logger stub. Sends carry `Reply-To: info@grinsirrigation.com`, multipart HTML+text body, and a `tags` array (`email_type`, `estimate_id`) for downstream webhook correlation.
- New `EmailService.send_estimate_email`, `.send_internal_estimate_decision_email`, `.send_internal_estimate_bounce_email` methods with new templates `estimate_sent.html` / `estimate_sent.txt` / `internal_estimate_decision.html` / `internal_estimate_bounce.html`.
- `EMAIL_TEST_ADDRESS_ALLOWLIST` hard guard added at the top of `_send_email` (mirrors the `SMS_TEST_PHONE_ALLOWLIST` pattern at `services/sms/base.py`); raises `EmailRecipientNotAllowedError` so callers see refusals as exceptions, not silent skips. Production no-op when env unset.
- `EstimateService.send_estimate` now calls the real email branch (lead fallback included). Token validity bumped from 30 → 60 days for both `customer_token` and `valid_until` defaults.
- `EstimateService.__init__` now requires `portal_base_url` (no hardcoded `https://portal.grins.com` default). Pre-existing portal URL bug fixed: builder now emits `{PORTAL_BASE_URL}/portal/estimates/{token}` matching the React Router route.
- New `_notify_internal_decision` on `EstimateService` fires email + SMS to `INTERNAL_NOTIFICATION_EMAIL` / `INTERNAL_NOTIFICATION_PHONE` on every approve/reject; failures are swallowed and logged so they never undo the customer-side decision.
- `POST /api/v1/webhooks/resend` (signature-verified via `resend.Webhooks.verify` Svix helper, `RESEND_WEBHOOK_SECRET`) handles `email.bounced` / `email.complained`. On `data.bounce.type == "Permanent"` we stamp `customers.email_bounced_at` and ping internal staff via email + SMS. Always returns 200 on a verified payload to avoid Resend retry storms.
- New `customers.email_bounced_at` nullable timestamp column (Alembic `20260428_100000`), soft-flag only (informational, never blocks future sends).
- `PORTAL_LIMIT` (`20/minute`) applied to the three portal estimate endpoints; `WEBHOOK_LIMIT` (`60/minute`) applied to the new Resend webhook.
- Portal `GET /api/v1/portal/estimates/{token}` transitions estimates from `SENT → VIEWED` on first portal load (idempotent — second view is a no-op).
- **Q-A breadcrumb:** new `SalesPipelineService.record_estimate_decision_breadcrumb` writes a timestamped note + `audit_log` row (`action="sales_entry.estimate_decision_received"`) to the active SalesEntry whenever a customer approves/rejects via portal. Best-effort; vertical-slice rule respected (cross-feature read of `Estimate`, write only to `SalesEntry`).
- **Q-B gate drop:** removed the `MissingSigningDocumentError` gate at `SEND_ESTIMATE → PENDING_APPROVAL` in `sales_pipeline_service.py:142-151`. The gate forced reps to upload a SignWell document before the customer had even seen the estimate, conflating estimate approval (a portal click) with contract signature. The pre-existing test `test_send_estimate_without_doc_raises` was inverted to `test_send_estimate_without_doc_now_advances` to lock in the corrected behavior. `MissingSigningDocumentError` retained in `exceptions/__init__.py` as deprecated for back-compat. SignWell signature gating still enforced correctly at `SEND_CONTRACT → CLOSED_WON` via `SignatureRequiredError` in `convert_to_job` — that gate is *not* affected.
- 211 / 211 feature-impacted tests pass; new test files: `test_email_recipient_allowlist.py`, `test_email_service_resend.py`, `test_send_estimate_email.py`, `test_estimate_internal_notification.py`, `test_resend_webhook.py`, `test_sales_pipeline_breadcrumb.py`, `test_estimate_correlation.py`, `test_estimate_email_send_functional.py`.

### Technical Details
- New dep: `resend>=2.0.0,<3.0.0` (v2.29.0 resolved). Webhook verification delegates to `resend.Webhooks.verify(VerifyWebhookOptions{payload, headers, webhook_secret})`; the SDK ships the Svix algorithm internally so no manual HMAC.
- `EmailSettings` extended with `resend_api_key`, `email_api_key` (legacy fallback), `portal_base_url`, `internal_notification_email`, `resend_webhook_secret`. `is_configured = bool(self.resend_api_key or self.email_api_key)` so flipping the env var is enough to migrate. Pydantic settings field-name → uppercased env-var convention used (no `validation_alias`/`AliasChoices` collisions).
- `EstimateService` now optionally accepts `sales_pipeline_service`; the customer-side approve/reject path runs `_notify_internal_decision` first (rep gets pinged immediately), then `_correlate_to_sales_entry` (slower DB-write step). Both helpers tolerate `Estimate | None` and never raise.
- DI wiring: both `dependencies.py:get_estimate_service` (admin path) and `portal.py:_get_estimate_service` (customer path) now construct identically-configured `EstimateService` with `EmailService`, `SMSService`, and `SalesPipelineService`. `lead_service` intentionally `None` — preserves pre-feature behavior; deeper LeadService DI is a separate ticket.
- Bounce payload field paths verified against current Resend webhook docs (2026-04-26): `data.bounce.type` (`"Permanent"`/`"Temporary"`, NOT `subType`/`"Transient"`), `data.bounce.message`, `data.to[]`, `data.tags[]`. Webhook handler reads back the `estimate_id` tag we threaded through `send_estimate_email → _send_email → resend.Emails.send` to correlate bounces to specific estimates.
- New env vars (added to `.env.example`): `RESEND_API_KEY`, `RESEND_WEBHOOK_SECRET`, `PORTAL_BASE_URL`, `EMAIL_TEST_ADDRESS_ALLOWLIST` (commented out — leave UNSET in production), `INTERNAL_NOTIFICATION_EMAIL`, `INTERNAL_NOTIFICATION_PHONE`.

### Decision Rationale
- **Resend over SES** — free tier (3K/mo, 100/day) covers our seasonal volume; SES kept as cold-swap fallback (~30 LOC). No provider abstraction class for v1 (YAGNI; one provider).
- **Hard allowlist guard, not soft warn-and-send** — mirrors the SMS `RecipientNotAllowedError` pattern that prevented several near-miss prod sends. Production safety > developer convenience in dev.
- **Internal notification via both email + SMS** — approval is a high-value moment; redundant channel is intentional. Failures swallowed because the customer's decision is already committed.
- **Q-B: drop the gate, don't replace it** — the original bughunt M-10 fix mistakenly assumed `PENDING_APPROVAL` meant "awaiting signature" when the intended meaning is "awaiting estimate approval via portal." A future ticket could add an "estimate sent" precondition (gate on linked `Estimate` being in `SENT|VIEWED|APPROVED`) but that introduces cross-aggregate reads we are explicitly avoiding here. Comment-only frontend change retains the toast handler defensively.
- **`MissingSigningDocumentError` retained in `exceptions/__init__.py`** — kept as deprecated for back-compat with any external imports/`__all__` consumers. Class docstring documents it as superseded.
- **Manual SignWell handoff (not auto-trigger on approval)** — sales rep must click "send for signature" themselves; the internal notification + Q-A breadcrumb is what tells them. Preserves the human checkpoint.

### Challenges and Solutions
- **Resend SDK v2 API drift from plan** — plan referenced `resend.webhooks.verify(payload, headers, secret)`; v2.29.0 actually exposes `resend.Webhooks.verify(VerifyWebhookOptions)`. Wrapper in `services/resend_webhook_security.py` adapts so the rest of the codebase has a stable typed API.
- **Pydantic Settings AliasChoices collision** — initial plan used `AliasChoices("RESEND_API_KEY", "EMAIL_API_KEY")` for `resend_api_key` AND a separate `email_api_key` field reading `EMAIL_API_KEY`; the overlap broke init via field-name kwargs (Pydantic Settings issue). Refactored to plain field names (`resend_api_key`, `email_api_key`) with default field-name → uppercased-env-var convention.
- **Existing email tests contaminated by repo `.env`** — autouse fixture in `test_email_service.py` clears `EMAIL_TEST_ADDRESS_ALLOWLIST`, `RESEND_API_KEY`, `EMAIL_API_KEY` and patches `resend.Emails.send`; helper functions pass `_env_file=None` to fully isolate the test fixture.
- **Webhook signature verification SDK churn** — `resend.Webhooks.verify` returns `None` on success and raises `ValueError` on failure (it does NOT return the parsed payload). The wrapper does its own `json.loads` after verification succeeds, returning the dict for the caller. Catches base `Exception` and re-raises as our typed `ResendWebhookVerificationError` to insulate from future SDK exception-class renames.

### Next Steps
- **Phase 6 cutover (ops, not code):** DNS records (SPF/DKIM/DMARC) on `grinsirrigation.com`; verify sender domain in Resend dashboard; set production env vars (`RESEND_API_KEY`, `RESEND_WEBHOOK_SECRET`, `PORTAL_BASE_URL=https://portal.grinsirrigation.com`, `INTERNAL_NOTIFICATION_EMAIL=<TBD>`, `INTERNAL_NOTIFICATION_PHONE=<TBD>`); confirm `EMAIL_TEST_ADDRESS_ALLOWLIST` is NOT set in prod; configure Resend webhook to `https://api.grinsirrigation.com/api/v1/webhooks/resend`; set up `noreply@grinsirrigation.com` mailbox + auto-responder.
- **Manual dev E2E:** Apply migration `20260428_100000`; confirm `customers.email_bounced_at` exists; with `EMAIL_TEST_ADDRESS_ALLOWLIST=kirillrakitinsecond@gmail.com`, send an estimate → confirm email arrives → click portal link → approve → confirm internal email + SMS fire → trigger Resend test bounce event → confirm flag stamped + internal alert sent.
- **Integration test:** `test_estimate_approval_email_flow_integration.py` (full HTTP round-trip from admin send → customer approve → bounce webhook with DB-side assertions) deferred to a follow-up; the unit + functional + service-layer coverage already exercises every branch in isolation.
- **Phase 2 frontend smoke:** validate `EstimateReviewPage` and `ApprovalConfirmation` render gracefully on the new portal URL shape via agent-browser at multiple viewports.

## [2026-04-25 19:18] - FEATURE: Schedule + Appointment Modal mobile responsiveness

### What Was Accomplished
- FullCalendar viewport-aware mode (listWeek on mobile, timeGridWeek on desktop) with simplified mobile toolbar and drag-drop disabled below 768 px
- Schedule page action bar collapses to a `+ New Appointment` button + overflow `DropdownMenu` on mobile; full inline cluster preserved on desktop
- AppointmentModal nested sub-sheets (Tags, Estimate, Payment) each gain a back-button `SubSheetHeader` so the absolute-overlay reads as a replacement view rather than a layered modal
- NotesPanel + PhotosPanel migrated from inline styles to Tailwind classes; NotesPanel Save/Cancel row now stacks (Save above Cancel) on mobile so it stays reachable above the iOS soft keyboard
- ModalHeader close button bumped 40 → 44 px; CustomerHero "Call" button now meets the 44 × 44 px Apple HIG floor
- ActionTrack tightens horizontal padding/gap on `< sm:` so the three ActionCards don't collide on iPhone SE
- Surrounding components made responsive: AppointmentForm time inputs (`grid-cols-1 sm:grid-cols-2`), AppointmentList filter row (full-width on mobile), DaySelector (horizontal `overflow-x-auto`), SchedulingTray grid, FacetRail Sheet width

### Technical Details
- New `useMediaQuery` hook at `frontend/src/shared/hooks/useMediaQuery.ts` built on `useSyncExternalStore` (race-free subscription, no setState-in-effect lint warning); exported via the hooks barrel; 5 vitest cases covering initial match, change events, unmount cleanup, and query-change re-subscription
- New `SubSheetHeader` shared component at `frontend/src/features/schedule/components/AppointmentModal/SubSheetHeader.tsx` with sticky-top header, 44 × 44 px back button, optional `rightAction` slot, 4 vitest cases
- New `@fullcalendar/list@^6.1.20` package added (matched to other `@fullcalendar/*` versions)
- `useMediaQuery('(max-width: 767px)')` drives behavior-level branching (FullCalendar config, Schedule action bar) rather than CSS-only `display: none` — avoids mounting hidden DOM and keeps mocks meaningful in tests
- `data-testid` convention preserved for all existing testids; new testids added: `schedule-action-overflow-btn`, `schedule-action-overflow-menu`, `overflow-menu-item-{view-calendar,view-list,clear-day,send-confirmations}`, `subsheet-header`, `subsheet-back-btn`, `subsheet-tags`, `subsheet-payment`, `subsheet-estimate`
- 660 / 660 schedule + shared-hook tests pass; production build succeeds; typecheck and lint counts unchanged from baseline (91 errors / 47 lint problems, all pre-existing)
- No backend changes; no new env vars

### Decision Rationale
- Mobile-first responsive web (not native, not separate route tree) — chosen for lowest-risk path to parity
- `listWeek` as default mobile calendar view — mirrors ServiceTitan / Jobber / Housecall Pro field-tech UIs
- Drag-drop reschedule disabled on mobile — avoids touch / scroll conflicts; route through Edit dialog instead
- Sub-sheet Option A (back-button header) — chosen over Option B (standalone Radix Sheets) for lower risk; Option B deferred to Phase 3
- PickJobsPage stays desktop-only — bulk job picking is an office workflow, not a tech workflow; trigger buttons hidden behind `hidden lg:inline-flex`
- `useSyncExternalStore` rewrite of `useMediaQuery` — replaces the planned `useState + useEffect` pattern that triggered the project's `react-hooks/set-state-in-effect` lint rule

### Challenges and Solutions
- Stacking context: `absolute inset-0` inside `position: fixed` modal looked layered on mobile — addressed via `SubSheetHeader` wrapping each sub-sheet so it reads as a replacement view with explicit back affordance
- PhotosPanel + NotesPanel inline styles bypassed Tailwind's responsive system — migrated to Tailwind classes so future mobile-specific tweaks compose cleanly
- `react-hooks/set-state-in-effect` lint rule blocked the planned `useState + useEffect + setMatches(...)` pattern — switched to `useSyncExternalStore` which is the canonical React 18+ primitive for external store subscription and avoids the rule entirely
- Stripe Terminal Web SDK iframe risk inside the wrapped `PaymentSheetWrapper` — kept Task 17b as the last code change so it can be reverted independently if real-device QA reveals iframe layout issues

### Next Steps
- Real-device manual QA (iPhone 13/14, iPad Air portrait + landscape, MacBook Chrome + Safari) — required before merge per Phase 1G
- Stripe Terminal payment flow on real iPhone with real Reader — required before Task 17b can ship
- Visual regression diff (`compare -metric AE`) on NotesPanel + PhotosPanel at 1440 px and 375 px — required before merge per VISUAL REGRESSION STRATEGY
- agent-browser E2E scripts at viewports 375 × 812, 768 × 1024, 1440 × 900 — Validation Level 5 per `spec-quality-gates.md`
- Phase 2: extend mobile responsiveness to Sales pipeline, Customers, Jobs, Invoices, Settings (see `feature-developments/mobile-responsiveness-investigation/05_RECOMMENDED_APPROACH.md`)

## [2026-04-25 23:05] - SECURITY: Add WebAuthn / Passkey authentication

### What Was Accomplished
- Added biometric / passkey login (Face ID, Touch ID, Windows Hello,
  Android) alongside the existing username/password flow. Passwords stay
  as the recovery path.
- Six endpoints under `/api/v1/auth/webauthn/*` (register begin/finish,
  authenticate begin/finish, credentials list/delete). The
  `/authenticate/finish` endpoint mints the same JWT cookie set as the
  password `/auth/login`, so `AuthProvider` is method-agnostic.
- Two new tables (`webauthn_credentials`, `webauthn_user_handles`) plus a
  `WebAuthnService` that owns the four ceremonies. Challenges live in
  Redis with a 5-min TTL.
- New `PasskeyManager` UI in Settings ("Sign-in & Security" card);
  biometric button and `autocomplete="username webauthn"` on the login
  page.

### Technical Details
- Backend: `webauthn>=2.7.0,<3.0.0` (py_webauthn / duo-labs). Sign-count
  regression auto-revokes the offending credential. Revocation is
  IDOR-safe (filtered by `staff_id`).
- Frontend: `@simplewebauthn/browser@^13.3.0`, TanStack Query
  (`passkeyKeys` factory), React Hook Form + Zod for the device-name
  form, sonner toasts.
- Tests: unit (service + API + property-based on base64url round-trip,
  sign-count gate, handle uniqueness). Integration / functional /
  frontend tests are scaffolded in the plan but require real DB and were
  deferred.

### Decision Rationale
- **Platform-bound passkeys** (`AuthenticatorAttachment.PLATFORM`) — we
  want Face ID / Touch ID specifically, not USB security keys, for
  staff convenience.
- **Synced passkeys allowed** — UX win of "enroll on iPhone, log in on
  MacBook" via iCloud Keychain outweighs the trade-off for a workforce
  app. Hardware keys can be re-enabled later by flipping the flag.
- **Password remains the recovery path** — `email_service.py` is a stub
  per memory, so magic-link recovery would be premature.

### Challenges and Solutions
- `Annotated[AsyncSession, Depends(...)]` with `from __future__ import
  annotations` left the type as a forward reference. Fix: import
  `AsyncSession` and `AuthService` at module level in `api/v1/webauthn.py`.
- FastAPI `include_router` snapshots routes at call time. Fix: include
  the webauthn sub-router into auth_router *before* including auth into
  the api_router.
- Local Postgres wasn't running, so migration round-trip and DB-touching
  tests are deferred to first dev-DB boot.

### Next Steps
- Apply migration to dev: `uv run alembic upgrade head`.
- Run manual hardware test (Mac Touch ID, iPhone Face ID) — Task 29.
- Add functional + integration tests once a test DB is available.
- Roll out to staff (admin first, then technicians).
- Monitor `auth.webauthn.*` log events for verification failures.

## [2026-04-23 21:10] - REFACTOR: Enforce appointment state machine (gap-04.A + 4.B)

### What Was Accomplished
Closed gap-04 by making `VALID_APPOINTMENT_TRANSITIONS` the structural
source of truth at both the model (ORM attribute set) and repository (SQL
UPDATE) layers, and added the missing `CONFIRMED → SCHEDULED` edge that
`reschedule_for_request` already depends on.

- **4.B dict edit.** Added `CONFIRMED → SCHEDULED` (the edge
  `appointment_service.reschedule_for_request` writes to resolve a
  customer-initiated reschedule from a confirmed appointment) plus
  `SCHEDULED → COMPLETED` and `CONFIRMED → COMPLETED` (the skip-to-complete
  path used by `/api/v1/jobs/{id}/complete` when an admin clicks Complete
  on a still-scheduled job that never went through IN_PROGRESS).
- **4.A model-level enforcement.** `Appointment._validate_status_transition`
  is a `@validates("status")` hook that mirrors the existing
  `staff_availability.py` pattern. Any `appt.status = X` that violates the
  transitions dict raises `InvalidStatusTransitionError`. Initial inserts
  (`self.status is None`) and idempotent same-status sets are no-ops.
- **4.A repository-level enforcement.** `AppointmentRepository.update()` and
  `update_status()` now route through `_validate_status_transition_or_raise`
  before issuing the SQL UPDATE. SQLAlchemy's `Session.execute(sa.update())`
  construct bypasses `@validates` entirely; without the repo guard the
  enforcement would be decorative.
- **`Appointment.transition_to(session, new_status, *, actor_id, reason)`.**
  New async helper that pairs a validated status set with an `AuditLog`
  write (`action="appointment.status.transition"`). Audit-write failures
  are logged and swallowed so the transition itself still commits — same
  contract as `_record_reschedule_reconfirmation_audit`.
- **Service-side guards.** `ConflictResolutionService.cancel_appointment`
  short-circuits on `is_terminal_status()` (returns the existing "already
  cancelled" response shape); `reschedule_appointment` raises
  `InvalidStatusTransitionError`. `AppointmentService.update_appointment`
  and `reschedule` forced-reset blocks narrow the inner `if` to only run
  for `CONFIRMED` / `CANCELLED` pre-states, so EN_ROUTE / IN_PROGRESS /
  COMPLETED / NO_SHOW pass through without triggering the new guard.

### Technical Details
- Model: `models/appointment.py` — `validates` import, three new dict
  edges, `_validate_status_transition`, `transition_to`.
- Repo: `repositories/appointment_repository.py` — runtime
  `AppointmentStatus` import, `_validate_status_transition_or_raise`,
  guard calls in `update()` and `update_status()`.
- Services: `services/conflict_resolution_service.py` (terminal-state
  guards in two places), `services/appointment_service.py` (two
  forced-reset narrowings).
- Tests (new): `tests/unit/test_appointment_state_machine.py` (16 tests:
  validator hook, dict edges, repo guard, transition_to + audit, Hypothesis
  property), `tests/functional/test_appointment_state_machine_functional.py`
  (4 tests: reschedule_for_request happy + negative, repo guard accept +
  reject).
- Tests (extended): `tests/integration/test_combined_status_flow_integration.py`
  — new `TestStateMachineSmoke` class running the golden path against a
  real `Appointment` instance so `@validates` actually fires.

### Decision Rationale
- **Two enforcement layers.** `@validates` is the ergonomic place for the
  rule but does not fire on `Session.execute(sa.update(...))`. Without the
  repository guard, `reschedule_for_request` and `send_confirmation` would
  slip through. Two layers cost one extra single-column SELECT per
  status-bearing UPDATE — cheap, and defence-in-depth.
- **No `session.merge()` switch.** Routing all updates through the ORM
  attribute path would change `updated_at` semantics, complicate the
  `rescheduled_from_id` self-reference cascade, and ship a much larger
  diff with no correctness gain over the explicit guard.
- **Skip-to-complete edges.** `/jobs/{id}/complete` accepts any
  non-terminal source. Without the new edges, turning on `@validates`
  would break the common admin "Complete" click on a still-SCHEDULED job.
  The `JobService.VALID_TRANSITIONS[TO_BE_SCHEDULED] ∋ COMPLETED` precedent
  (bughunt M-1) is the same rationale at the job layer.

### Challenges and Solutions
- **Test-infrastructure constraint.** No real-DB test fixture exists in
  the repo (verified via grep for `async_sessionmaker`/`create_async_engine`
  — zero hits). All three tiers use mocks. `@validates` does not fire on
  `MagicMock.status = X`, so the existing 28+ files of mock-based tests
  are untouched by this change. The new tests construct real `Appointment`
  instances (no session needed for attribute-level validation) and mock
  the `AsyncSession.execute` for the repo-guard tests.
- **Forced-reset edge case.** `update_appointment` and `reschedule` both
  end with an `if updated.status != SCHEDULED → write SCHEDULED` that
  could legitimately receive `EN_ROUTE` / `IN_PROGRESS` from the same
  request. Narrowed the inner `if` to `CONFIRMED` / `CANCELLED` so the
  new guard is never invoked against a non-customer-facing pre-state.

### Next Steps
- **gap-05 (audit centralisation).** Migrate the remaining 17 direct
  `appt.status = X` assignments to `transition_to()` so every status
  change writes an audit row. Mechanical multi-file refactor unblocked
  by this PR.
- **gap-01.B (EN_ROUTE reschedule guard cleanup).** `_handle_reschedule`'s
  `blocked_statuses` is now belt-and-suspenders given the validator;
  can be simplified.

## [2026-04-21 12:00] - FEAT: Thread Correlation Hardening (Gap 03)

### What Was Accomplished
Closed two latent defects in Y/R/C SMS-reply correlation so admin-initiated
appointment changes never silently strand the customer on a stale thread.

- **3.A — Widened confirmation-like correlation.** `find_confirmation_message`
  now matches `APPOINTMENT_CONFIRMATION`, `APPOINTMENT_RESCHEDULE`, and
  `APPOINTMENT_REMINDER` (previously only confirmation). Replies on a
  reschedule-notification or reminder thread now route through the same
  Y/R/C handler tree.
- **3.A — Post-cancellation reply handler.** New `handle_post_cancellation_reply`
  on `JobConfirmationService` routes replies to a cancellation SMS: `R`
  opens a `RescheduleRequest` for the CANCELLED appointment, `Y` raises a
  new `CUSTOMER_RECONSIDER_CANCELLATION` admin alert (no auto-transition),
  anything else goes to `needs_review`. Wired into `SMSService._try_confirmation_reply`
  as the third-rung fallback (confirmation → reschedule-followup →
  cancellation → None).
- **3.B — Supersession marker.** New `sent_messages.superseded_at` column +
  partial index `ix_sent_messages_active_confirmation_by_appointment`. The
  marker runs automatically inside `SMSService.send_message` (log-and-swallow
  on failure) so every confirmation-like outbound tombstones its
  predecessors for the same appointment. `find_confirmation_message`
  filters `superseded_at IS NULL`.
- **3.B — Stale-thread reply telemetry.** A Y/R/C on a thread whose only
  confirmation-like row is superseded writes a
  `JobConfirmationResponse(status='stale_thread_reply')` audit row and
  returns a courteous auto-reply ("please reply to the most recent
  message…") rather than a silent no_match.

### Technical Details
- Migration: `20260421_100100_add_sent_messages_superseded_at.py`
- Enum: `AlertType.CUSTOMER_RECONSIDER_CANCELLATION`
- Service: `JobConfirmationService` gains `find_cancellation_thread`,
  `handle_post_cancellation_reply`, `_handle_post_cancel_reschedule`,
  `_handle_post_cancel_reconsider`, `_dispatch_reconsider_cancellation_alert`,
  `_handle_stale_thread_reply`, `_find_superseded_confirmation_for_thread`
- Service: `NotificationService.send_admin_reconsider_cancellation_alert`
  (email + Alert row, log-and-swallow contract)
- Tests (new): `test_thread_correlation_lifecycle.py` (20 unit),
  `test_post_cancellation_reply_functional.py` (3 functional),
  `test_thread_correlation_integration.py` (4 integration).
- Tests (extended): `test_thread_id_storage.py` (+4 supersession tests),
  `test_sms_service_gaps.py` (+3 third-rung fallback), `test_correlation_properties.py`
  (+2 Hypothesis supersession invariants).

### Decision Rationale
- Supersession is wired inside `SMSService.send_message` rather than at
  every send site so the guarantee is uniform regardless of caller.
- `APPOINTMENT_CANCELLATION` is intentionally NOT part of the confirmation-like
  set — a Y on a cancellation SMS means "un-cancel," which must be a manual
  admin decision rather than an automatic status flip.
- Post-cancel R creates a `RescheduleRequest` row so the admin dashboard
  surfaces the signal; `reschedule_for_request` already rejects CANCELLED
  as a source status, so admin must reactivate first (tracked as a
  follow-up gap).

### Next Steps
- Manual validation on dev (SMS restricted to +19527373312):
  seed confirmation, drag-drop reschedule, reply Y to new thread, reply Y
  to stale thread, cancel + reply R, cancel + reply Y. Expected outcomes
  documented in `.agents/plans/thread-correlation-hardening.md` Level-5
  validation checklist.
- Future gap: extend `reschedule_for_request.allowed_statuses` to accept
  CANCELLED so the admin path can resolve a post-cancel R without a
  manual reactivation step first.

## [2026-04-18 18:00] - REFACTOR: Internal Notes Simplification — Revert Notes Timeline to Single-Blob Edit/Save

### What Was Accomplished
Reverted the multi-entry Notes Timeline system (introduced April 16th) back to the simple single-blob Edit/Save pattern. The timeline's per-entry author/timestamp/stage-tag chrome proved unwieldy for day-to-day admin use. A new shared `InternalNotesCard` component now renders the same Edit → type → Save Notes interaction on every surface where a customer or lead appears.

### Technical Details
**Removed:**
- `NotesTimeline` component, `useNotes`/`useCreateNote` hooks, `NoteService`, `Note` model, notes API endpoints (`/api/v1/.../notes`), `notes` database table
- All timeline-related tests (PBT Properties 7/8/9, NoteService functional/integration tests, NotesTimeline.test.tsx)

**Added/Kept:**
- `InternalNotesCard` shared component at `frontend/src/shared/components/InternalNotesCard.tsx` — encapsulates collapsed/expanded state, Edit/Cancel/Save buttons, toasts, readOnly mode
- Consumer wiring on 5 surfaces: CustomerDetail, LeadDetail, SalesDetail, AppointmentForm, SalesCalendar
- `invalidateAfterCustomerInternalNotesSave()` helper for cross-surface query invalidation
- Lead-to-customer notes carry-forward (`_carry_forward_lead_notes`) on Move to Sales / Move to Jobs
- `customers.internal_notes` and `leads.notes` columns (pre-existing, no new columns)

**Fold Migration:** `20260418_100700_fold_notes_table_into_internal_notes.py`
- Folds `notes.body` entries into `customers.internal_notes` (subject_type='customer') and `leads.notes` (subject_type='lead')
- Discards `sales_entry` and `appointment` subject_type entries (logged count + sample before drop)
- Drops the `notes` table
- Notes rows migrated per subject_type: counts depend on dev DB state at migration time (logged to migration output)

### Decision Rationale
- The always-visible textarea + append-only history felt noisy for the simple task of jotting context about a customer
- One source-of-truth blob per individual, one interaction pattern, shown everywhere that individual appears
- Sales entries and appointments read/write the customer's `internal_notes` — no per-surface duplication

### Next Steps
- Manual smoke test on dev: edit notes on Customer Detail, verify propagation to Sales Entry and Appointment surfaces
- Verify lead notes carry-forward on a newly-routed lead

## [2026-04-16 20:30] - BUGFIX: 17 MEDIUM Customer Lifecycle Fixes (M-1..M-17)

### What Was Accomplished
Closed all 17 MEDIUM findings from the 2026-04-16 customer-lifecycle bug hunt, on top of the already-merged CR-1..CR-6 + H-1..H-14 fixes. Work ran in seven phases (1: SMS templates → 2: audits → 3: send_message routing → 4: schedule UX → 5: invoices → 6: sales → 7: renewals/uploads/docs), each commit gated through ruff/mypy/pyright/unit tests before merge.

### Technical Details
- **SMS template alignment (M-3/M-4/M-5/M-6):** `_KEYWORD_MAP` extended with `ok/okay/yup/yeah/1` (CONFIRM) and `different time/change time/2` (RESCHEDULE) — `stop` and `3` intentionally excluded. CONFIRM auto-reply now includes appointment date + time via new `_build_confirm_message` helper. Reschedule ack uses spec-exact wording. Google Review SMS uses spec verbiage (no `Grin's Irrigations`, no first-name prefix).
- **Audit coverage (M-7/M-8):** New `_record_update_audit` and `_record_reactivate_audit` on `AppointmentService` capture pre/post field snapshots, `notify_customer`, and `actor_id`. Customer-SMS cancel writes audit with `source="customer_sms"` and gates on `transitioned` to skip CR-3 short-circuit cases.
- **Audit trail completeness (M-9):** Y/R/C auto-reply and reschedule follow-up SMS now route through `SMSService.send_message` with new `APPOINTMENT_CONFIRMATION_REPLY` and `RESCHEDULE_FOLLOWUP` MessageType values. Migration `20260416_100400` widens the `ck_sent_messages_message_type` CHECK constraint.
- **Schedule UX (M-1/M-2):** `AppointmentDetail` now renders the canonical `SendConfirmationButton` for drafts (was a hand-rolled inline button). `CancelAppointmentDialog` keeps both action buttons visible for DRAFT and adds a `title` tooltip on the disabled "Cancel & text" variant.
- **Invoices (M-12/M-14/M-15):** `days_until_due` / `days_past_due` are now Pydantic `computed_field`s on `InvoiceResponse` (UTC, mutually exclusive). Frontend reads them directly. New `render_invoice_template()` + `validate_invoice_template()` helpers introduce canonical merge keys (`{customer_name}/{invoice_number}/{amount}/{due_date}`) and accept the spec's bracket form. Invalid templates → 400 with named missing keys. Stripe webhook returns 503 (was 400) on missing secret so Stripe retries.
- **Sales (M-10/M-11):** Regression test locks `StatusActionButton` calling convertToJob first on `SEND_CONTRACT` (no code change — the bughunt's "advance-first" claim was stale). `_get_signing_document` defaults to strict `sales_entry_id` scope; legacy customer-scope fallback gated behind `include_legacy=True` (reporting reads only).
- **Renewals/uploads/docs (M-13/M-16/M-17):** `PARTIALLY_APPROVED` fires on first approval (was waiting for zero PENDING). `PhotoService.validate_file` raises `TypeError` for MIME (→ 415) vs. `ValueError` for size (→ 413); all upload endpoints differentiate. New `useDocumentPresign` hook resolves presigned URL at render so signing buttons disable when the file is missing or expired.

### Files Created
- `src/grins_platform/migrations/versions/20260416_100400_widen_sent_messages_for_confirmation_reply_and_followup.py`
- `frontend/src/features/sales/components/StatusActionButton.test.tsx` (M-10 regression)
- `frontend/src/features/sales/components/SalesDetail.test.tsx` (M-17 signing gate)

### Files Modified
- `src/grins_platform/services/job_confirmation_service.py` (M-3/M-4/M-5/M-8)
- `src/grins_platform/services/appointment_service.py` (M-7)
- `src/grins_platform/services/sms_service.py` (M-9)
- `src/grins_platform/services/invoice_service.py` (M-14)
- `src/grins_platform/services/contract_renewal_service.py` (M-13)
- `src/grins_platform/services/photo_service.py` (M-16)
- `src/grins_platform/api/v1/jobs.py` (M-6, M-16)
- `src/grins_platform/api/v1/customers.py` (M-16)
- `src/grins_platform/api/v1/leads.py` (M-16)
- `src/grins_platform/api/v1/appointments.py` (M-7, M-16)
- `src/grins_platform/api/v1/invoices.py` (M-14)
- `src/grins_platform/api/v1/sales_pipeline.py` (M-11)
- `src/grins_platform/api/v1/webhooks.py` (M-15)
- `src/grins_platform/schemas/invoice.py`, `schemas/ai.py` (M-12, M-9)
- `src/grins_platform/models/enums.py`, `models/sent_message.py` (M-9)
- `frontend/src/features/schedule/components/AppointmentDetail.tsx` + test (M-1)
- `frontend/src/features/schedule/components/CancelAppointmentDialog.tsx` + test (M-2)
- `frontend/src/features/invoices/components/InvoiceList.tsx`, `types/index.ts` (M-12)
- `frontend/src/features/sales/components/SalesDetail.tsx`, `hooks/useSalesPipeline.ts` (M-17)

### Quality Check Results
- Backend `ruff check src/`: 179 errors baseline = 179 mine (no regression).
- Backend `mypy src/`: 230 errors baseline = 230 mine.
- Backend `pyright` on touched files: 10 errors / 102 warnings baseline = 10 / 102 mine after cleanup commit.
- Backend `pytest -m unit`: 49 fail / 3066 pass baseline = same on this branch (all 49 failures pre-existing).
- Frontend `tsc --noEmit`: clean.
- Frontend `eslint`: 4 errors baseline = 4 mine.
- Frontend `vitest`: 3 fail / 1379 pass baseline = same on this branch.

### Decisions
- **M-3:** `stop` and `3` are NOT cancel synonyms (`stop` is reserved compliance keyword; `3` would be ambiguous numeric mapping).
- **M-9:** Two new MessageType values (`appointment_confirmation_reply`, `reschedule_followup`) over reusing `appointment_confirmation` so per-type dedup and audit reporting stay accurate.
- **M-11:** Default behavior change — multi-entry customers with legacy unscoped docs now get a 422 prompting upload rather than silently signing the wrong entry's doc. Reporting reads opt back in with `include_legacy=True`.
- **M-15:** Behavioral change — Stripe missing-secret returns 503 (Stripe retries with backoff + on-call paged) rather than 400 (terminal, silent drop).

### Next Steps
- Manual E2E verification on dev for SMS #1 happy path with each new keyword (`ok`, `yup`, `1`, `R`, `different time`, repeat `C`) against `+19527373312`.
- Manual E2E for Job Complete → Google Review SMS (verify spec wording on owner's phone).
- LOW/UX findings L-1..L-11 remain open from the same hunt.

## [2026-04-16 17:50] - BUGFIX: 14 HIGH Customer Lifecycle Fixes (H-1..H-14)

### What Was Accomplished
Closed all 14 HIGH findings from the 2026-04-16 customer-lifecycle bug hunt, on top of the already-merged CR-1..CR-6 CRITICAL fixes. Work ran in four waves of parallel subagents (H-10/H-13/H-14 → H-2/H-3/H-4/H-8/H-9 → H-5/H-6/H-11 → H-1/H-7/H-12), each branch gated through ruff / mypy / pyright / unit tests before merging to dev.

### Technical Details
- **New surfaces:** `Alert` model + `AlertRepository` + `/api/v1/alerts` endpoint; `NoReplyReviewQueue` (`/schedule` tab); `BusinessSettingsPanel` (`/settings`); `reschedule-from-request` + `send-reminder-sms` endpoints; `useLeadRoutingActions` shared hook.
- **Nightly cron:** `flag_no_reply_confirmations` (6 AM local) flags SCHEDULED appointments with no Y/R/C reply after N days (BusinessSetting, default 3).
- **Consent hygiene:** `mass_notify` now batch-filters opt-outs via `SmsConsentRepository.get_opted_out_customer_ids`; response carries `skipped_count` + `skipped_reasons`.
- **Auth:** `bulk_notify_invoices` now genuinely `ManagerOrAdmin`-gated (was effectively open with `type: ignore` suppressions).
- **Calendar correctness:** `weekStartsOn: 1` + `firstDay={1}` unified across the schedule feature so admins and the backend `align_to_week()` agree.
- **PaymentMethod:** `credit_card` / `ach` / `other` added to the enum + CHECK constraint; `stripe` retained for legacy rows per owner decision — no data migration.
- **Renewal math:** `+52 weeks` → `replace(year=year+1)` + align-to-Monday with leap-day fallback; five-year roll test confirms weekday stability.

### Files Created
- `src/grins_platform/models/alert.py`, `src/grins_platform/repositories/alert_repository.py`, `src/grins_platform/schemas/alert.py`, `src/grins_platform/api/v1/alerts.py`
- `src/grins_platform/services/admin_config.py`, `src/grins_platform/services/business_setting_service.py`
- Alembic migrations: `20260416_100000` (H-4 payment-method CHECK), `20260416_100100` (H-5 alerts table), `20260416_100200` (H-7 needs_review_reason), `20260416_100300` (H-12 business-settings seeds)
- `frontend/src/features/schedule/components/NoReplyReviewQueue.tsx` + test
- `frontend/src/features/settings/components/BusinessSettingsPanel.tsx` + test, `useBusinessSettings.ts`, `businessSettingsApi.ts`
- `frontend/src/features/leads/hooks/useLeadRoutingActions.ts` + test
- `frontend/src/features/schedule/hooks/useNoReplyReview.ts`
- Multiple new backend + frontend test files

### Quality Check Results
- Backend unit + functional tests on all affected modules: green (144+ tests across H-5/H-7/H-11/H-12 alone).
- Frontend tests for affected features: green across customers, invoices, schedule, leads, settings (193 tests).
- Migrations: round-trip `alembic upgrade head` + `downgrade -1` verified for the 20260416 chain.
- Frontend typecheck baseline: 69 pre-existing errors; 0 new from Waves 1–4.

### Decisions (user-confirmed)
- **D-1 (H-1):** Full parity with `LeadsList` including requires-estimate + CR-6 conflict modal; shared `useLeadRoutingActions` hook.
- **D-3 (H-4):** Add `credit_card` / `ach` / `other`; keep `stripe` rows untouched; FE dropdown omits `stripe` going forward. No data migration.
- **D-5 (H-7):** 3-day no-reply default, overridable via `BusinessSetting.confirmation_no_reply_days`.
- **D-6 (H-12):** BusinessSettings panel placed as a new `Card` on the existing `/settings` page (the page uses stacked cards, not tabs).

### Follow-ups
- The two RescheduleRequestsQueue FE integration tests were re-enabled by mocking `AppointmentForm` (tests now verify the queue's own wiring rather than driving the full form + Radix Dialog chain in jsdom). Real form behavior still covered by its own component tests.
- The two long-form plan / finding documents that were lost mid-session (`customer-lifecycle-bughunt.md` and `critical-fixes-plan.md`) were reconstructed verbatim from the conversation's session-start Read captures.
- Agent-browser E2E validation for H-1 / H-3 / H-7 / H-12 not yet run in this session.

## [2026-04-16 14:00] - BUGFIX: 6 Critical Customer Lifecycle Fixes (CR-1..CR-6)

### What Was Accomplished
Closed all 6 CRITICAL findings from the 2026-04-16 customer-lifecycle bug hunt (`bughunt/2026-04-16-customer-lifecycle-bughunt.md`). Six fix branches merged to `dev` across three waves.

### Technical Details
- **CR-1** (`fix/cr-1-apply-schedule-draft`, 2f7caaf): `apply_schedule` now writes `AppointmentStatus.DRAFT.value` and leaves `Job.status`/`Job.scheduled_at` untouched. Draft Mode silence restored.
- **CR-2** (`fix/cr-2-job-started-scheduled`, c65283e): `SCHEDULED → IN_PROGRESS` added to the transitions table; `job_started` pre-state tuple includes SCHEDULED. DRAFT stays blocked per decision.
- **CR-3** (`fix/cr-3-repeat-cancel-sms`, 9a30fac): `_handle_cancel` short-circuits when appointment already CANCELLED, returning empty `auto_reply` so the SMS guard suppresses the send.
- **CR-4** (`fix/cr-4-invoice-billing-reason`, 6d99587): renewal branch gated on Stripe `billing_reason == "subscription_cycle"`. Three-branch dispatch: first_invoice / renewal_cycle / other.
- **CR-5** (`fix/cr-5-lien-review-queue`, d679c25): `mass_notify("lien_eligible")` raises deprecation → 400; new `compute_lien_candidates` + `send_lien_notice` service methods; two new endpoints + `LienReviewQueue` component as tab on `/invoices`.
- **CR-6** (`fix/cr-6-convert-lead-dedup`, 7007002): `convert_lead` runs `check_tier1_duplicates`; raises `LeadDuplicateFoundError` → 409 with structured detail; FE `LeadConversionConflictModal` surfaces "Use existing" / "Convert anyway" (force=true).

### Quality Check Results
- Each CR's new and modified tests pass locally. Pre-existing dev-branch failures were documented as drift notes per fix.
- Ruff / MyPy / Pyright surfaces match baseline — fix branches add zero new errors.
- FE typecheck + vitest pass on the new components and hooks.

### Decisions
- CR-1: Job status stays `to_be_scheduled` during DRAFT creation (admin promotes explicitly via Send Confirmation).
- CR-2: DRAFT cannot skip to IN_PROGRESS; only SCHEDULED / CONFIRMED / EN_ROUTE can.
- CR-5: Lien Review Queue is a tab on `/invoices`; client-side dismiss only for MVP.
- CR-6: 409 detail uses structured `{error:"duplicate_found", duplicates:[...]}`.

## [2026-02-07 21:30] - BUGFIX: Lead Form CORS Error Diagnosis & Documentation

### What Was Accomplished
Diagnosed and documented the CORS error blocking lead form submissions from the Vercel landing page (`grins-irrigation.vercel.app`) to the Railway backend (`grins-platform-production.up.railway.app`). Created solution documentation for the deployment fix.

### Technical Details
- The browser's preflight `OPTIONS` request to `POST /api/v1/leads` was rejected because the backend's `CORS_ORIGINS` env var on Railway did not include `https://grins-irrigation.vercel.app`
- Confirmed no code changes needed — `src/grins_platform/app.py` already reads `CORS_ORIGINS` as a comma-separated env var and merges with localhost defaults
- Fix is purely a Railway environment variable update: add `https://grins-irrigation.vercel.app` to `CORS_ORIGINS`

### Files Created
- `LeadErrorSolution.md` — concise problem/solution/verification reference at workspace root
- `docs/lead-form-cors-fix.md` — detailed guide with step-by-step Railway instructions, curl verification commands, environment variable reference, and troubleshooting section (created in prior session)

### Decision Rationale
Documented the fix as a standalone markdown file rather than a code change because the issue is a deployment configuration gap, not a code bug. The CORS middleware is already correctly implemented — it just needs the right origins configured in production.

### Next Steps
- Apply the fix: add `https://grins-irrigation.vercel.app` to `CORS_ORIGINS` on Railway
- Verify with the curl commands in `LeadErrorSolution.md`
- Consider adding rate limiting to the public `/api/v1/leads` endpoint

## [2026-02-07 20:10] - FEATURE: Lead Capture (Website Form Submission)

### What Was Accomplished
Complete lead capture feature implemented end-to-end across backend and frontend, covering the full lifecycle from public form submission through admin management to customer conversion.

### Technical Details

**Backend (Python/FastAPI):**
- Lead SQLAlchemy model with Alembic migration, indexes on phone/status/created_at/zip_code
- Pydantic schemas with phone normalization, zip validation, HTML sanitization, honeypot bot detection
- Repository layer with filtered listing, search, pagination, and dashboard metric queries
- Service layer with duplicate detection (merges active duplicates), status transition validation, lead-to-customer conversion with optional job creation
- 6 API endpoints: public POST (no auth), admin GET list/detail, PATCH update, POST convert, DELETE
- Custom exceptions: LeadNotFoundError, LeadAlreadyConvertedError, InvalidLeadStatusTransitionError
- Dashboard integration: new_leads_today and uncontacted_leads metrics

**Frontend (React/TypeScript):**
- Full feature slice: types, API client, TanStack Query hooks, 5 components
- LeadsList with filtering (status, situation, date range, search), pagination, sorting
- LeadDetail with status management, staff assignment, action buttons
- ConvertLeadDialog with auto name-splitting, optional job creation toggle
- Status/Situation badge components with color coding
- Dashboard "New Leads" widget with color-coded urgency, sidebar nav with uncontacted count badge

**Testing:**
- 168 backend tests (unit, functional, integration, PBT) — all passing
- 6 property-based tests: phone normalization idempotency, status transition validity, duplicate detection, input sanitization, name splitting, honeypot transparency
- 793 frontend tests across 67 files — all passing
- Agent-browser E2E validation: form submission, lead management, filtering, status changes, conversion flow, deletion

### Quality Check Results
- Ruff: 0 lead-related violations (pre-existing seed migration issues only)
- MyPy: 0 errors
- Pyright: 0 errors
- Backend tests: 1870 passed (6 pre-existing failures in auth_service)
- Frontend lint: 0 errors
- Frontend typecheck: 0 errors
- Frontend tests: 793/793 passing

### Decisions and Deviations
- Public form submission endpoint has no auth (by design) for website integration
- Honeypot field returns identical 201 response shape to avoid bot detection leakage
- Duplicate detection merges data into existing active leads rather than rejecting
- CORS issue discovered during E2E testing — production backend needs landing page domain added to CORS_ORIGINS env var (documented in docs/lead-form-cors-fix.md)

### Next Steps
- Add landing page domain to Railway CORS_ORIGINS environment variable
- Consider adding rate limiting to public lead submission endpoint
- Future: automated SMS/email notifications on lead submission
