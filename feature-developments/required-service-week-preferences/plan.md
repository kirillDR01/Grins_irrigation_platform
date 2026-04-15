# Required Service Week Preferences — Implementation Plan

## Problem

Today the onboarding form's "Preferred Service Weeks" section is labelled `(optional)` and customers can click **Complete Onboarding** without making any explicit selection. That creates gaps — the admin team doesn't know whether a blank value means "customer has no preference" or "customer skipped the question."

## Scope (agreed with user)

Make every tier-appropriate service week an **explicit choice** before onboarding completes. Each dropdown must be consciously set to either a specific week *or* "No preference" — no silent defaults. Propagate selections into the jobs that get auto-created on Stripe `checkout.session.completed`. Snapshot property-detail answers on the agreement for audit.

**No customer-facing modification UI.** Admins can still change `target_start_date` / `target_end_date` on a job via existing admin endpoints — that's sufficient.

**No backfill.** Rule applies to new onboardings only. Existing agreements with `NULL` snapshot fields stay as-is.

## Resolved decisions

| Topic | Decision |
|---|---|
| Tier names | Keep `Essential` / `Professional` / `Premium` (residential + commercial variants each). No rename. |
| Premium monthly visits | **5 total** across May, June, July, August, September. Mid-season is absorbed into the five. |
| Marketing copy | Leave `Grins_irrigation/frontend/src/shared/data/pricing.ts` untouched despite "4 Monthly…" wording — user's call. |
| Labels (customer-visible) | "Spring Start-Up", "Mid-Season Inspection & Tune Up", "Fall Winterization", "{Month} Monitoring Visit & Tune Up" |
| Internal `job_type` identifiers | Unchanged: `spring_startup`, `mid_season_inspection`, `fall_winterization`, `monthly_visit_5..monthly_visit_9` |
| Service windows | Spring: Mar–**Jun** (extended). Mid-Season: **May–Sep** (extended). Fall: Sep–Nov. Monthly: own month only. |
| Max selectable date | `2026-11-30` (end of November 2026) across all pickers. |
| "No preference" | Remains a valid choice but must be **actively selected**, not the default. Stored as `null` in `service_week_preferences[job_type]`. |
| Residential vs commercial onboarding UI | Identical — same tier service arrays, only price differs. Lock in with a test. |
| Existing customers | No backfill. New rule enforced only in `/onboarding/complete`. |
| Target-week modification | Admin-only, via existing job update endpoint. No new UI. |
| Controller Programming | Not a scheduled visit; no job row, no dropdown. Displayed in agreement/disclosure text only. |

## Tier → required dropdown map

| Tier | Dropdowns |
|---|---|
| Essential | `spring_startup`, `fall_winterization` |
| Professional | `spring_startup`, `mid_season_inspection`, `fall_winterization` |
| Premium | `spring_startup`, `monthly_visit_5`, `monthly_visit_6`, `monthly_visit_7`, `monthly_visit_8`, `monthly_visit_9`, `fall_winterization` |

Derived dynamically from the tier's `included_services` JSON — not hardcoded — so adding a future tier just needs a seed change.

## Implementation steps

### Backend

1. **Alembic migration** — `add_agreement_snapshot_fields`
   - Add to `service_agreements`: `tier_slug_snapshot VARCHAR(100) NULL`, `tier_name_snapshot VARCHAR(100) NULL`, `preferred_service_time VARCHAR(20) NULL`, `access_instructions TEXT NULL`, `gate_code VARCHAR(50) NULL`, `dogs_on_property BOOLEAN NULL`, `no_preference_flags JSONB NULL`.
   - Downgrade drops them.
   - All nullable → existing rows unaffected.

2. **Alembic migration** — `update_tier_descriptions_to_marketing_labels`
   - Rewrite `service_agreement_tiers.included_services` description strings across the six tier rows to match marketing: "Spring Start-Up", "Mid-Season Inspection & Tune Up", "Fall Winterization", "{Month} Monitoring Visit & Tune Up".
   - Downgrade restores previous strings.

3. **`ServiceAgreement` model** (`src/grins_platform/models/service_agreement.py`) — add ORM columns matching migration.

4. **`CompleteOnboardingRequest` schema** (`src/grins_platform/api/v1/onboarding.py`)
   - `service_week_preferences: dict[str, str | None]` — required, `null` values allowed.
   - Add `preferred_service_time`, `access_instructions`, `gate_code`, `dogs_on_property` fields to request body (if not already present upstream).
   - Pydantic validator: look up the session's agreement → tier → `included_services` → derive expected `job_type` set (expanding `monthly_visit` frequency) → every expected key must appear in the submitted dict; else 422.

5. **`OnboardingService.complete_onboarding`** (`src/grins_platform/services/onboarding_service.py`)
   - After validation, compute `no_preference_flags = {k: v is None for k, v in service_week_preferences.items()}`.
   - Write `tier_slug_snapshot`, `tier_name_snapshot`, `preferred_service_time`, `access_instructions`, `gate_code`, `dogs_on_property`, `no_preference_flags` to the agreement update payload.
   - `service_week_preferences` storage unchanged (already JSONB).

6. **`JobGenerator._resolve_dates`** (`src/grins_platform/services/job_generator.py`)
   - Confirm behavior: `null` in `service_week_preferences[job_type]` → fall back to full-month window.
   - Confirm Premium generates 7 jobs (not 8) — mid-season absorbed, not emitted as a separate job row. Review `_build_job_spec` / tier spec.

### Frontend

7. **`WeekPickerStep.tsx`** (`frontend/src/features/portal/components/`)
   - `SERVICE_MONTH_RANGES`:
     - `spring_startup`: months 3–6
     - `mid_season_inspection`: months 5–9
     - `fall_winterization`: months 9–11
     - `monthly_visit_5..9`: unchanged (single month each)
   - Labels → marketing-aligned strings.
   - Per-row state: `unset` | `week_selected` | `no_preference` (default `unset`).
   - Clicking "No preference" sets `no_preference` (keeps value `null`).
   - Picking a week sets `week_selected`.
   - Expose per-row state up to parent so submit can be disabled.
   - Section header: remove `(optional)`.
   - `RestrictedWeekPicker` `maxDate` clamp to `2026-11-30`.
   - Red inline error on any row still `unset` when user tries to submit.

8. **Onboarding parent form**
   - Disable "Complete Onboarding" button while any row is `unset`.
   - Payload: for each tier service, send `null` for no-preference rows and ISO Monday for chosen weeks. Never omit a key.
   - Include `preferred_service_time`, `access_instructions`, `gate_code`, `dogs_on_property` in the same payload.

### Tests

9. **Backend unit tests** (`tests/...`)
   - `CompleteOnboardingRequest` validator:
     - Essential session missing `fall_winterization` → 422.
     - Premium session with all 7 keys (5 as `null`, 2 as dates) → accepted.
     - Extra unexpected `job_type` key → tolerated or rejected? Decision: tolerate (forward-compat), log warning.

10. **Backend integration tests**
    - `POST /onboarding/complete` for each tier:
      - Essential → 2 jobs created with correct date ranges.
      - Professional → 3 jobs.
      - Premium → 7 jobs.
    - `null` preference → job's `target_start_date`/`target_end_date` span the full calendar month.
    - Specific Monday → job's dates span that Monday through Sunday.

11. **Agreement snapshot test**
    - Post a Premium completion → read agreement → assert all snapshot columns populated.
    - Read an existing (pre-migration) agreement row (seeded via raw SQL with `NULL` snapshot fields) → SQLAlchemy read returns `None` for those fields without error.

### E2E verification

12. **Environment check**
    - Confirm dev services are reachable (Vercel preview URL + Railway dev backend).
    - Confirm Stripe is in **test mode**.

13. **`agent-browser` script, per `STRIPE-CHECKOUT-AUTOMATION-GUIDE.md`** — run six flows:
    - Essential Residential, Essential Commercial
    - Professional Residential, Professional Commercial
    - Premium Residential, Premium Commercial

    For each:
    1. Navigate to `/service-packages`, subscribe to tier, fill modal.
    2. Complete Stripe checkout with test card `4242 4242 4242 4242`.
    3. On onboarding page:
       - Verify the correct number of dropdowns appears (2 / 3 / 7).
       - Verify "Complete Onboarding" is disabled initially.
       - Set each dropdown to a mix of specific weeks and "No preference".
       - Verify button enables only after all rows are explicit.
       - Submit.
    4. Post-submit: hit backend to confirm agreement row has snapshot columns populated, and expected job count exists with target date ranges.
    5. Screenshot each state into `e2e-screenshots/required-weeks-verification/<tier>/`.

## Out of scope

- Customer-facing "change preferred week" UI.
- Backfill of existing agreements' snapshot columns.
- Marketing copy updates in `Grins_irrigation`.
- Any Stripe product/price changes.
- Controller Programming scheduling.

## Risk notes

- **New columns additive & nullable.** Existing agreement rows get `NULL`; no breakage. Any admin dashboard column that renders them will show blank for old rows — cosmetic only.
- **Required-ness at app layer only.** No DB check constraint on `service_week_preferences` completeness — so old rows and non-onboarding insertions (if any) aren't broken.
- **Dynamic tier service derivation.** Validator reads tier.included_services at runtime; if that JSON is ever malformed, the validator should fail loud, not silently accept.
