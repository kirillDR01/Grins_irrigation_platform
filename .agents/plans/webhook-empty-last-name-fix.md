# Feature: Webhook resilience to single-word Stripe customer names

The following plan should be complete, but it's important that you validate documentation and codebase patterns and task sanity before you start implementing.

Pay special attention to naming of existing utils, types and models. Import from the right files etc.

## Feature Description

Stripe Checkout collects the buyer's name in a single combined "Name" field. When a customer types a mononym ("Madonna") or only their first name ("Kirill"), the `checkout.session.completed` webhook handler currently builds a `CustomerCreate(... last_name="")` and crashes on Pydantic validation (`min_length=1`). The crash propagates uncaught, the SQL transaction rolls back, no `ServiceAgreement` is ever persisted, and the customer is then permanently locked out of `/onboarding` with the error **"We couldn't find your session. Please contact us."** even though Stripe successfully charged them.

This change makes the webhook tolerate single-word/empty names by substituting a clearly-marked placeholder for the missing `last_name`, so the agreement is created and the customer can complete onboarding. The fix is intentionally scoped to the webhook call site — the `CustomerCreate` schema is **not** changed, so every other caller (admin form, lead conversion, etc.) keeps its `min_length=1` guarantee.

## User Story

As a **paying Stripe customer who entered only one name** in checkout
I want to **complete the onboarding form successfully**
So that **I can finish setting up the service I just paid for, without contacting support**.

As an **on-call engineer**
I want **the `checkout.session.completed` webhook to not roll back on a single-word name**
So that **I don't have to manually replay Stripe events and reconstruct agreements every time someone signs up with a mononym**.

## Problem Statement

Production Railway logs (`grinsirrigationplatform-production.up.railway.app`) show recurring webhook failures:

```
event: stripe.stripewebhookhandler.webhook_checkout_session_completed_failed
error_type: ValidationError
error: 1 validation error for CustomerCreate
last_name
  String should have at least 1 character [type=string_too_short, input_value='', input_type=str]
```

Followed milliseconds later by `webhook_invoice_paid_failed: "No agreement for subscription <sub_…>"` — proof the rollback happened.

**18 distinct subscriptions** between 2026-04-21 and 2026-04-26 hit this pattern, including 3 with the explicit `ValidationError` log line (the rest are downstream `invoice.paid` failures whose sibling checkout-failure entry rolled out of retention). The frontend translates the resulting 404 from `POST /api/v1/onboarding/complete` into the user-visible message.

Locator: `src/grins_platform/api/v1/webhooks.py:283` builds `last_name = parts[1] if len(parts) > 1 else ""`. `src/grins_platform/schemas/customer.py:62-67` (on `main`; `81-86` on `dev`) declares `last_name: str = Field(..., min_length=1, max_length=100)`. The two are inconsistent on the empty-string boundary; only the webhook hits this boundary because it derives `last_name` from a single Stripe text field rather than a structured form.

## Solution Statement

**Change one line at the webhook call site** so that when the customer's full name has fewer than two whitespace-separated parts, `last_name` is set to a non-empty sentinel string `"-"` instead of `""`. Add a structured log line whenever the sentinel is used, so we can identify and follow up with affected customers. Add unit tests covering single-word, empty, whitespace-only, and multi-word names.

**Why this approach is least invasive:**

- `CustomerCreate.last_name` schema is **untouched** — admin UIs, lead conversion, REST API, and every other caller keep their `min_length=1` invariant.
- No try/except is added — the existing error path still catches genuine schema violations.
- No new dependencies, no migrations, no config changes.
- Single-file, single-line behavior change in `webhooks.py`. New code is bounded to one branch; the happy path for normal multi-word names is byte-identical.

**Sentinel choice:** `"-"` (single hyphen). Rationale: short, max_length=100 safe, obviously a placeholder when surfaced in admin UI, easy to grep for ("backfill any customer with `last_name = '-'`"). Documented inline.

## Feature Metadata

**Feature Type**: Bug Fix
**Estimated Complexity**: Low
**Primary Systems Affected**: `_handle_checkout_completed` in `webhooks.py` (single function, single branch)
**Dependencies**: None new

---

## CONTEXT REFERENCES

### Relevant Codebase Files — IMPORTANT: YOU MUST READ THESE BEFORE IMPLEMENTING

- `src/grins_platform/api/v1/webhooks.py` (`_handle_checkout_completed`, lines 220-475 on `main`)
  Why: This is where the bug lives. The customer-creation block at lines 279-330 splits `customer_details.name` (lines 280-283) and currently produces `last_name=""` for single-word inputs. The `CustomerCreate(...)` instantiation at lines 310-315 raises. The fix is on line 283 only (plus a new constant + a new `if`-block log); the surrounding try/except at 316-329 must remain unchanged so existing `DuplicateCustomerError` race-condition behavior stays intact.

- `src/grins_platform/schemas/customer.py` (lines 50-110 on `main`; lines 69-152 on `dev`)
  Why: This is the `CustomerCreate` schema with the `min_length=1` constraint we are intentionally NOT changing. Read it to confirm: `last_name` is required (`...`), validated by `min_length=1` (lines 62-67 on `main`, 81-86 on `dev`), and post-processed by the `strip_whitespace` field validator (lines 104-107 on `main`, 147-151 on `dev`). The strip happens *after* `min_length` is checked, so passing `" "` would still raise. Our sentinel `"-"` survives both checks.

- `src/grins_platform/tests/unit/test_webhook_handlers.py` (helpers at lines 33, 49, 68; class at line 83)
  Why: The `_make_event`, `_make_agreement`, `_make_handler` test helpers and the patching pattern (lines 83-188 show the complete `test_new_customer_created_when_no_match` example) are the canonical reference. The container class is **`TestCheckoutSessionCompleted`** (NOT `TestHandleCheckoutCompleted`). New tests live inside this class and must mirror its style — same 8-decorator `@patch` stack (which already includes `CustomerService`), `_make_handler()` helper, `_make_event("checkout.session.completed", ...)` builder, `await handler.handle_event(event)` invocation.

- `src/grins_platform/tests/unit/test_webhook_handlers.py` (lines 165-188 and 254)
  Why: Reference fixtures for the `customer_details.name` field. Existing tests use `"Jane Doe"` (line 171, in `test_new_customer_created_when_no_match`) and `"John"` (line 254, in `test_existing_customer_matched_by_email`). The `"John"` case is *exactly* the failing input shape — but the existing test doesn't assert that `CustomerCreate` succeeds in that path because the customer is matched by email first. New tests must force the no-email-match path (mirror `test_new_customer_created_when_no_match` exactly) so the `CustomerCreate` constructor is actually exercised.

- `src/grins_platform/services/customer_service.py`
  Why: `CustomerService.create_customer` is what receives our `CustomerCreate` and calls the repo. Skim it to confirm no downstream code path depends on `last_name != "-"`. (Spot check: customer matching is by phone/email, not by name. Property generation, surcharge logic, job generation, and disclosure creation never read `last_name`.)

### New Files to Create

None. The change is in-place in `webhooks.py` and tests are added to the existing `test_webhook_handlers.py`.

### Relevant Documentation — YOU SHOULD READ THESE BEFORE IMPLEMENTING

- [Stripe Checkout — `customer_details` object](https://docs.stripe.com/api/checkout/sessions/object#checkout_session_object-customer_details)
  Specific section: `customer_details.name`
  Why: Confirms `name` is a free-form single string ("The customer's full name…"), not split into first/last by Stripe. Confirms it can be `null`.

- [Pydantic v2 — Field constraints](https://docs.pydantic.dev/latest/concepts/fields/#string-constraints)
  Specific section: `min_length`
  Why: Confirms `min_length=1` rejects empty string with `string_too_short` (matching the production error). No change to the schema is required for our fix; this is just to verify the constraint we're working around.

- Internal: `production-bugs/2026-04-26-webhook-empty-last-name-orphaned-agreements.md`
  Why: Full root-cause investigation report for this bug. Contains the production Stripe + Railway evidence, the exact code path trace, the orphan customer cohort breakdown (Bucket A = 3 confirmed mononyms), and the rationale behind every choice in this plan. **This is the authoritative reference document; treat the plan as a derived implementation contract.** Note: the prior monorepo paths (`Grins_irrigation/changes_part_2.md`, `Grins_irrigation/e2e-screenshots/E2E-STRESS-TEST-REPORT.md`) referenced in older docs no longer exist in this repo — ignore them.

### Patterns to Follow

**Naming Conventions (match existing webhook handler):**
- Snake_case for variables and functions
- Structured log events use dot-separated paths: `webhook_<action>_<status>` (e.g., `webhook_customer_matched_by_phone` at line 297)
- New log event for placeholder usage: `webhook_customer_placeholder_last_name`

**Error Handling Pattern** (from `webhooks.py:303-307`):

```python
try:
    normalized_phone = normalize_phone(phone_raw)
    # …happy path…
except ValueError:
    self.log_started(
        "webhook_phone_normalize_failed",
        phone_raw=phone_raw[-4:] if phone_raw else "",
    )
```

→ Don't add a try/except for our fix. We're preventing the error condition rather than catching it.

**Logging Pattern** (from `webhooks.py:296-299`):

```python
self.log_started(
    "webhook_customer_matched_by_phone",
    customer_id=str(customer.id),
)
```

→ Use `self.log_started("webhook_customer_placeholder_last_name", full_name_provided=bool(full_name), first_name=first_name)`. **Never log full name or email** — PII guideline implicit in the existing handler (note how `phone_raw[-4:]` is used at line 306 instead of full phone).

**Sentinel Constant Pattern**: Define as a module-level constant near the top of the handler section so it's discoverable and editable in one place:

```python
# Sentinel for missing last_name in checkout.session.completed.
# Stripe's Checkout name field is a single string; mononyms ("Madonna")
# and first-name-only inputs ("Kirill") have no last name to extract.
# Using a non-empty placeholder lets CustomerCreate (min_length=1) succeed
# without rolling back the entire agreement transaction.
_MISSING_LAST_NAME_PLACEHOLDER = "-"
```

**Test Pattern** (from `tests/unit/test_webhook_handlers.py` — helpers at 33-77, reference test at 83-188): Use `_make_event`, `_make_handler`, and the 8-decorator `@patch` stack used by `test_new_customer_created_when_no_match` (which already patches `CustomerService`, `CustomerRepository`, `AgreementRepository`, `AgreementTierRepository`, `AgreementService`, `ComplianceService`, `JobGenerator`, `EmailService`). New test names follow `test_<scenario>_<expected_outcome>` style. Use `@pytest.mark.unit` and `@pytest.mark.asyncio`.

---

## IMPLEMENTATION PLAN

### Phase 1: Foundation

Define the sentinel constant and confirm the call site is the only place that needs changing.

**Tasks:**
- Add `_MISSING_LAST_NAME_PLACEHOLDER` module-level constant in `webhooks.py`
- Confirm by `grep` that `last_name` is not derived in any other webhook handler (it shouldn't be — only `_handle_checkout_completed` builds a `CustomerCreate`)

### Phase 2: Core Implementation

One-line behavioral change at the webhook call site, plus a structured log when the placeholder is used.

**Tasks:**
- Replace `last_name = parts[1] if len(parts) > 1 else ""` with `last_name = parts[1] if len(parts) > 1 else _MISSING_LAST_NAME_PLACEHOLDER`
- Emit `self.log_started("webhook_customer_placeholder_last_name", ...)` immediately after, only when the placeholder branch was taken
- Leave every other line of `_handle_checkout_completed` untouched

### Phase 3: Integration

There is no integration work — no new endpoints, no new services, no router changes, no config. The webhook handler is already wired and Stripe is already pointing at it (verified live: `STRIPE_WEBHOOK_SECRET` set, all `POST /api/v1/webhooks/stripe` returning 200).

**Tasks:**
- (None for phase 3)

### Phase 4: Testing & Validation

Add focused unit tests covering the four name-shape branches; verify no regressions in existing webhook tests; verify lint and type checks pass.

**Tasks:**
- Add 4 new unit tests to `test_webhook_handlers.py` covering: single-word name, empty name, whitespace-only name, multi-word name (regression).
- Run full webhook test class to confirm zero regressions.
- Run ruff + mypy to confirm zero new issues.

---

## STEP-BY-STEP TASKS

IMPORTANT: Execute every task in order, top to bottom. Each task is atomic and independently testable.

### Task 1: ADD module-level placeholder constant in `src/grins_platform/api/v1/webhooks.py`

- **IMPLEMENT**: Add a `_MISSING_LAST_NAME_PLACEHOLDER = "-"` constant with a docstring-style comment, placed immediately above the `class StripeWebhookHandler` definition (line 73 on `main`, after the `HANDLED_EVENT_TYPES` block that closes at line 70). Use a leading underscore — module-private convention already used elsewhere in the file (cf. `_endpoints` in `onboarding.py`).
- **PATTERN**: Module-level constants near the top of the file, before the handler class. Existing reference: `HANDLED_EVENT_TYPES` at `webhooks.py:61`.
- **IMPORTS**: None new.
- **GOTCHA**: Do NOT define this inside the handler class or inside `_handle_checkout_completed`. Keeping it module-level makes it greppable for future cleanup ("find all customers with placeholder last_name") and consistent with the file's other constants.
- **VALIDATE**: `grep -n "_MISSING_LAST_NAME_PLACEHOLDER" src/grins_platform/api/v1/webhooks.py` returns exactly 1 line (the definition) before Task 2.

### Task 2: UPDATE `_handle_checkout_completed` to use placeholder for missing last_name

- **IMPLEMENT**: In `src/grins_platform/api/v1/webhooks.py`, replace line 283:
  ```python
  last_name = parts[1] if len(parts) > 1 else ""
  ```
  with:
  ```python
  last_name = parts[1] if len(parts) > 1 else _MISSING_LAST_NAME_PLACEHOLDER
  ```
  Then, immediately after the `last_name = …` line, add a conditional log:
  ```python
  if last_name == _MISSING_LAST_NAME_PLACEHOLDER:
      self.log_started(
          "webhook_customer_placeholder_last_name",
          full_name_provided=bool(full_name),
          first_name=first_name,
      )
  ```
- **PATTERN**: `webhooks.py:296-299` for `log_started` style. Use `self.log_started`, not `logger.info` — the LoggerMixin wraps domain context.
- **IMPORTS**: None new.
- **GOTCHA #1**: Do NOT log `full_name` (PII). Log only `bool(full_name)` to distinguish "Stripe sent nothing" from "Stripe sent a single word." Log `first_name` because it's already going to be persisted to the DB anyway and is the same string Stripe sent — no incremental privacy loss.
- **GOTCHA #2**: The `parts[0] if parts else "Customer"` line above (282) is **untouched**. Don't try to "improve" it — its current behavior is intended ("Customer" placeholder for fully-empty name) and any change is out of scope.
- **GOTCHA #3**: Don't wrap `CustomerCreate(...)` in try/except. The genuine validation errors (e.g., `phone < 10 chars`) should still propagate to the existing rollback path. Our fix handles only the specific empty-`last_name` case.
- **GOTCHA #4**: The `@field_validator("first_name", "last_name")` `strip_whitespace` validator at `schemas/customer.py:147-151` runs *after* `min_length`. So passing `" "` (whitespace string) would still raise `string_too_short`. Our sentinel `"-"` is non-whitespace, survives both checks.
- **VALIDATE**: `grep -n "_MISSING_LAST_NAME_PLACEHOLDER" src/grins_platform/api/v1/webhooks.py` returns exactly 3 lines (definition, assignment, comparison). The diff vs. main on this file should be minimal — the constant + 2 changed/added lines + 4 new lines (the `if` block).

### Task 3: ADD unit test — single-word name does not crash and uses placeholder

- **IMPLEMENT**: Add a new test method to **`class TestCheckoutSessionCompleted`** (line 83 on `main`) in `src/grins_platform/tests/unit/test_webhook_handlers.py`. Method name: `test_single_word_customer_name_uses_placeholder_last_name`. The test must:
  1. Use the **same 8-decorator `@patch` stack** as `test_new_customer_created_when_no_match` (lines 90-103 on `main`): `EmailService`, `JobGenerator`, `ComplianceService`, `AgreementService`, `AgreementTierRepository`, `AgreementRepository`, **`CustomerService`** (yes — already patched there), `CustomerRepository` (in that decorator order; bottom-up arg order in the method signature). Copy the existing decorator order verbatim — pytest unwraps bottom-up.
  2. Set `cust_repo.find_by_email.return_value = []` AND `cust_repo.find_by_phone.return_value = None` so the code path actually constructs `CustomerCreate`.
  3. Build the event with `customer_details = {"email": "new@example.com", "name": "Madonna", "phone": "5551234567"}`. Include the same `customer`, `subscription`, `metadata` keys as the reference test (`consent_token`, `package_tier`, `package_type`).
  4. Capture the `CustomerCreate` argument that flows into `CustomerService.create_customer`. Because the patch is already wired in the reference test, you read it back with `cust_svc.create_customer.assert_called_once()` followed by `created = cust_svc.create_customer.call_args.args[0]` (or equivalently `cust_svc.create_customer.call_args[0][0]`).
  5. Assert: `result["status"] == "processed"` (no rollback), `created.first_name == "Madonna"`, `created.last_name == _MISSING_LAST_NAME_PLACEHOLDER`.
- **PATTERN**: `tests/unit/test_webhook_handlers.py:83-188` (the body of `test_new_customer_created_when_no_match`) is the canonical example. Mirror the imports, fixtures, and assertion style verbatim — only the `customer_details.name` value and the post-call assertion need to differ.
- **IMPORTS**: Add `from grins_platform.api.v1.webhooks import _MISSING_LAST_NAME_PLACEHOLDER` next to the existing `from grins_platform.api.v1.webhooks import StripeWebhookHandler` (line 21). Use the constant in the assertion rather than hardcoding `"-"` so the test stays valid if someone changes the sentinel.
- **GOTCHA**: A common mistake is to reduce the patch stack from 8 to 7 (mirroring the email-match test instead of the no-match test). Do NOT remove `@patch("grins_platform.api.v1.webhooks.CustomerService")` — without it, `CustomerService(customer_repo)` at `webhooks.py:317` instantiates the real service and the test will hit the real DB layer. Patch the class, not the instance.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_webhook_handlers.py::TestCheckoutSessionCompleted::test_single_word_customer_name_uses_placeholder_last_name -xvs` passes.

### Task 4: ADD unit test — empty name still uses defaults (regression coverage for fallback)

- **IMPLEMENT**: Add `test_empty_customer_name_uses_default_first_name_and_placeholder_last_name` to **`TestCheckoutSessionCompleted`**. Same 8-decorator `@patch` stack as Task 3. Build the event with `customer_details = {"email": "x@y.com", "name": "", "phone": "5551234567"}` (empty string). Assert: `created.first_name == "Customer"`, `created.last_name == _MISSING_LAST_NAME_PLACEHOLDER`, status `"processed"`.
- **PATTERN**: Same as Task 3.
- **IMPORTS**: Reuse Task 3 imports.
- **GOTCHA**: `customer_details.name` from Stripe can be `null`. Test the empty string explicitly here; Stripe-`null` becomes `""` via `str(cust_details.get("name", "") or "")` at `webhooks.py:280`, so this case covers both shapes.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_webhook_handlers.py::TestCheckoutSessionCompleted::test_empty_customer_name_uses_default_first_name_and_placeholder_last_name -xvs` passes.

### Task 5: ADD unit test — whitespace-only name behaves like empty name

- **IMPLEMENT**: Add `test_whitespace_only_customer_name_uses_defaults` to **`TestCheckoutSessionCompleted`**. Same shape as Task 4 but `name = "   "` (three spaces). Assert: `created.first_name == "Customer"`, `created.last_name == _MISSING_LAST_NAME_PLACEHOLDER`. Reason this is a distinct test: the `.strip().split()` chain would produce `[]` from whitespace-only input, hitting both fallbacks at once.
- **PATTERN**: Same as Task 3.
- **IMPORTS**: Reuse.
- **GOTCHA**: This case verifies that `parts = full_name.strip().split(maxsplit=1)` returns `[]` when input is whitespace-only, so both `parts[0] if parts else "Customer"` and `parts[1] if len(parts) > 1 else PLACEHOLDER` branches activate. Document this in a comment in the test.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_webhook_handlers.py::TestCheckoutSessionCompleted::test_whitespace_only_customer_name_uses_defaults -xvs` passes.

### Task 6: ADD unit test — multi-word name path is unchanged (regression guard)

- **IMPLEMENT**: Add `test_multi_word_customer_name_splits_normally` to **`TestCheckoutSessionCompleted`**. Same shape but `name = "Jane Smith"`. Assert: `created.first_name == "Jane"`, `created.last_name == "Smith"` (NOT the placeholder), status `"processed"`. Add a second sub-case for `name = "Mary Anne Watson"`: assert `created.first_name == "Mary"`, `created.last_name == "Anne Watson"` (everything after first split is one string, due to `maxsplit=1`). Keep both as separate test methods OR a single parametrized one — either is fine; do whichever fits the surrounding style of `TestCheckoutSessionCompleted`.
- **PATTERN**: Same as Task 3. This test exists primarily as a regression guard: if a future change replaces `split(maxsplit=1)` with something else, this test will catch it.
- **IMPORTS**: Reuse.
- **GOTCHA**: `maxsplit=1` is intentional — names like "Mary Anne Watson" should yield `last_name="Anne Watson"`, not `last_name="Anne"`. Don't change the split semantics.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_webhook_handlers.py::TestCheckoutSessionCompleted::test_multi_word_customer_name_splits_normally -xvs` passes.

### Task 7: VERIFY no other webhook code path constructs `CustomerCreate` from a Stripe name field

- **IMPLEMENT**: Run `grep -nE "CustomerCreate\(|customer_details.*name|full_name" src/grins_platform/api/v1/webhooks.py`. Confirm the only `CustomerCreate(...)` instantiation is at line ~309 in `_handle_checkout_completed`. If any other site is found that builds `last_name` from a freeform Stripe field, document it and decide whether the same fix needs to be applied there. As of the current main, only one site exists.
- **PATTERN**: N/A — verification step.
- **IMPORTS**: N/A.
- **GOTCHA**: This is a sanity check, not a code change. If the grep surfaces a second site, **stop and ask the user** before proceeding — the scope of the fix would expand and the plan needs updating.
- **VALIDATE**: `grep -cE "CustomerCreate\(" src/grins_platform/api/v1/webhooks.py` returns `1`.

### Task 8: RUN full webhook unit-test suite for regressions

- **IMPLEMENT**: Run the entire `test_webhook_handlers.py` and adjacent webhook tests to ensure no existing tests rely on `last_name == ""` behavior (none should — the existing tests all match by email and short-circuit before `CustomerCreate`, or use multi-word names like `"Jane Doe"`).
- **PATTERN**: Standard pytest invocation.
- **IMPORTS**: N/A.
- **GOTCHA**: If any test fails citing `last_name`, that test was depending on a behavior we just removed; investigate before "fixing" the test — the failing assertion may be encoding the bug.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_webhook_handlers.py src/grins_platform/tests/unit/test_stripe_webhook.py src/grins_platform/tests/unit/test_webhook_error_handling.py -x` exits 0.

### Task 9: RUN linting + type checks

- **IMPLEMENT**: Run `ruff check`, `ruff format --check`, and `mypy` on the changed files. Confirm zero new diagnostics. Constants and tests should follow existing style: `_UPPER_SNAKE_CASE` for constants, two blank lines around module-level definitions, type hints on all function signatures.
- **PATTERN**: Standard linting; check `pyproject.toml [tool.ruff]` and `[tool.mypy]` sections for enabled rule sets.
- **IMPORTS**: N/A.
- **GOTCHA**: The repo has strict ruff rules including `D` (pydocstyle) — the new constant needs a docstring-style comment, and the new test methods need docstrings.
- **VALIDATE**: All three commands return zero new findings:
  - `uv run ruff check src/grins_platform/api/v1/webhooks.py src/grins_platform/tests/unit/test_webhook_handlers.py`
  - `uv run ruff format --check src/grins_platform/api/v1/webhooks.py src/grins_platform/tests/unit/test_webhook_handlers.py`
  - `uv run mypy src/grins_platform/api/v1/webhooks.py`

### Task 10: MANUAL replay validation against Stripe test mode (optional but strongly recommended)

- **IMPLEMENT**: In Stripe **test mode** Dashboard, find a recent `checkout.session.completed` event whose `customer_details.name` was a single word (or use Stripe CLI `stripe trigger checkout.session.completed` to fabricate one and pass `--add 'customer_details[name]=Madonna'`). Send the event to a *staging* deploy of this fix (not prod). Verify in staging Railway logs: `webhook_customer_placeholder_last_name` log fires, `webhook_checkout_completed` succeeds (no rollback), agreement is created in the staging DB. Production replay is **out of scope** for this task — see Notes section.
- **PATTERN**: Stripe CLI `stripe events resend evt_…` or `stripe trigger`.
- **IMPORTS**: N/A.
- **GOTCHA**: Use staging/dev. Do not replay events against production until after the fix is deployed there.
- **VALIDATE**: Log line `webhook_customer_placeholder_last_name` visible in staging logs; corresponding `service_agreements` row exists in staging DB; `/api/v1/onboarding/complete?session_id=cs_test_…` returns 200 (not 404).

---

## TESTING STRATEGY

### Unit Tests

Add 4 new tests (Tasks 3-6) under **`class TestCheckoutSessionCompleted`** in `src/grins_platform/tests/unit/test_webhook_handlers.py` (line 83 on `main`). Each test:
- Uses the existing `_make_event` and `_make_handler` helpers.
- Mirrors the 8-decorator `@patch` stack of `test_new_customer_created_when_no_match` (which already includes `CustomerService` — no new patch is required).
- Forces the no-email-match, no-phone-match path so `CustomerCreate` is exercised.
- Captures the `create_customer` call's argument via `cust_svc.create_customer.call_args.args[0]` and asserts on `first_name` and `last_name`.

Coverage target: 100% of the modified branch (line 283 + the new `if` block) and 100% of the multi-word regression path.

### Integration Tests

None required for this scope. The fix doesn't touch the API surface, the database schema, or any cross-service contract. The end-to-end flow (Stripe → webhook → DB → onboarding endpoint) is already covered by `tests/integration/test_onboarding_preferred_schedule.py` and similar — those tests use multi-word names and continue to pass.

If the team later wants an integration test that specifically exercises a single-word name through the full webhook pipeline, that can be added under `src/grins_platform/tests/integration/test_webhooks_*.py` mirroring the existing patterns. Out of scope for this task.

### Edge Cases

Mandatory test coverage:
- `name = "Madonna"` → first="Madonna", last="-" (Task 3)
- `name = ""` → first="Customer", last="-" (Task 4)
- `name = "   "` (whitespace only) → first="Customer", last="-" (Task 5)
- `name = "Jane Doe"` → first="Jane", last="Doe" (Task 6, regression)
- `name = "Mary Anne Watson"` → first="Mary", last="Anne Watson" (Task 6, asserts maxsplit=1 preserved)

Considered-but-not-tested (existing tests already cover, or out of scope):
- `customer_details` missing entirely → existing fallback at `webhooks.py:279` produces `cust_details = {}`; covered transitively by the empty-name test.
- Customer matched by email → no `CustomerCreate` happens; existing `test_existing_customer_matched_by_email` covers.
- Customer matched by phone → no `CustomerCreate` happens; existing `test_existing_customer_matched_by_phone_when_email_differs` covers.
- Unicode names (e.g., `"José"`, `"李"`) → `.split()` splits on any whitespace (Unicode-aware in Python 3); behaves like single-word case. Covered transitively by Task 3.

---

## VALIDATION COMMANDS

Execute every command to ensure zero regressions and 100% feature correctness.

### Level 1: Syntax & Style

```bash
uv run ruff check src/grins_platform/api/v1/webhooks.py src/grins_platform/tests/unit/test_webhook_handlers.py
uv run ruff format --check src/grins_platform/api/v1/webhooks.py src/grins_platform/tests/unit/test_webhook_handlers.py
uv run mypy src/grins_platform/api/v1/webhooks.py
```

### Level 2: Unit Tests (new + regression)

```bash
# New tests added in this PR
uv run pytest src/grins_platform/tests/unit/test_webhook_handlers.py::TestCheckoutSessionCompleted -xvs

# Adjacent webhook test files for regression
uv run pytest src/grins_platform/tests/unit/test_stripe_webhook.py src/grins_platform/tests/unit/test_webhook_error_handling.py src/grins_platform/tests/unit/test_webhook_idempotency_property.py -x

# Full unit suite (slowest but most thorough)
uv run pytest -m unit -x
```

### Level 3: Integration Tests

```bash
uv run pytest -m integration src/grins_platform/tests/integration/test_onboarding_preferred_schedule.py -x
```

If integration tests touch a real DB and aren't normally run locally, skip Level 3 and rely on CI.

### Level 4: Manual Validation (staging)

1. Deploy branch to a staging Railway environment.
2. Use Stripe CLI in test mode:
   ```bash
   stripe trigger checkout.session.completed --add 'checkout_session:customer_details[name]=Madonna' --add 'checkout_session:customer_details[email]=test+madonna@example.com'
   ```
3. Watch staging Railway logs for `event=stripe.stripewebhookhandler.webhook_customer_placeholder_last_name` AND `event=stripe.stripewebhookhandler.webhook_checkout_completed` (success).
4. Confirm a `service_agreements` row exists in staging DB for the new subscription.
5. Open the staging onboarding URL with the test session_id; confirm the form loads (verify-session 200) and submit succeeds (complete 200, NOT 404).

### Level 5: Additional Validation (Stripe MCP / Railway MCP)

```bash
# After staging deploy, pull recent webhook logs filtered for the placeholder event
mcp__railway__get-logs workspacePath=/Users/kirillrakitin/Grins_irrigation_platform logType=deploy environment=production service=Grins_irrigation_platform lines=100 filter=placeholder_last_name
```

(Skip until the fix is in production. Pre-deploy, this filter will return zero lines, which is itself a sanity check.)

---

## ACCEPTANCE CRITERIA

- [ ] `_handle_checkout_completed` no longer raises `ValidationError` when `customer_details.name` is single-word, empty, or whitespace-only.
- [ ] When the placeholder is used, a `webhook_customer_placeholder_last_name` log line is emitted with `full_name_provided` and `first_name` fields (no PII beyond the first name).
- [ ] `CustomerCreate.last_name` schema is unchanged (`min_length=1` preserved).
- [ ] All 4 new unit tests pass; all existing tests in `test_webhook_handlers.py` pass without modification.
- [ ] `ruff check`, `ruff format --check`, and `mypy` produce zero new findings on `webhooks.py` and the test file.
- [ ] `grep` confirms `CustomerCreate(` appears exactly once in `webhooks.py` (no second site needs the same fix).
- [ ] Manual staging validation: a single-word-name checkout produces an agreement, and `/onboarding/complete` returns 200 for the resulting session_id.
- [ ] No changes to: `schemas/customer.py`, `services/customer_service.py`, `services/onboarding_service.py`, `api/v1/onboarding.py`, frontend code, or DB migrations.

---

## COMPLETION CHECKLIST

- [ ] Task 1 — sentinel constant added
- [ ] Task 2 — call site updated and conditional log added
- [ ] Task 3 — single-word-name test passes
- [ ] Task 4 — empty-name test passes
- [ ] Task 5 — whitespace-only-name test passes
- [ ] Task 6 — multi-word regression test passes
- [ ] Task 7 — `grep` verifies single `CustomerCreate(` site
- [ ] Task 8 — full webhook test suite green
- [ ] Task 9 — ruff + mypy green
- [ ] Task 10 — staging Stripe replay successful (optional but recommended)
- [ ] Acceptance criteria checklist all checked
- [ ] No untracked changes outside the two files mentioned
- [ ] Diff against `main` is small (≤ ~10 lines changed in `webhooks.py`, ≤ ~150 lines added in tests)

---

## NOTES

### Recovery of historical orphaned customers

The 18 subscriptions identified in production logs (April 21–26, 2026) — including `sub_1TQTVLG1xK8dFlaf3fN2xE1G` (latest as of investigation), `sub_1TQILUG1xK8dFlafDLMNIIt3`, `sub_1TQELWG1xK8dFlafeg0JTAGI`, etc. — represent customers who paid Stripe but have no `service_agreement` row.

**Recovery is out of scope for this fix.** Two recovery options to consider as a follow-up task:

1. **Replay via Stripe Dashboard**: For each affected subscription, Stripe stores the `checkout.session.completed` event for 30 days. After deploying this fix, use the Stripe Dashboard's "Resend" button on each event. The fixed webhook handler will succeed and the agreement will be created. Drawback: must be done within 30 days of the original event; some April 21 events are already at the edge.

2. **Manual SQL backfill**: Pull each affected `cus_…` from Stripe, look up their subscription metadata (tier, zone count, etc.), and INSERT directly into `service_agreements` + run the equivalent of `JobGenerator` for each. Higher risk, higher effort, but works regardless of the 30-day window.

Recommend a separate plan + ticket once this fix is in production. Until then, the on-call engineer can manually create agreements for any new affected customer using the same approach.

### Why not relax the schema?

`CustomerCreate.last_name` is consumed by:
- The webhook handler (this code path)
- `POST /api/v1/customers` (admin manual creation form)
- Lead-to-customer conversion in `LeadConversionService`
- Migration backfills

The admin form and conversion service legitimately want `min_length=1` — operators entering customer data should be required to fill in last name (it shows up in scheduling, invoicing, and the admin UI). Loosening the schema would degrade UX for those flows. The webhook is the only place where a non-empty `last_name` is genuinely impossible to obtain, so it's the right place to apply the workaround.

### Why a hyphen and not a more descriptive sentinel?

Considered alternatives:
- `"(unknown)"` — wraps in parens, looks like a system value but takes 9 chars
- `"-"` — single character, max_length=100 safe, obviously a placeholder, easy to query for cleanup
- `"Customer"` — already used as the empty-`first_name` fallback; reusing it would make `first_name == last_name` for fully-empty names, which complicates queries and reporting
- Using `first_name` as `last_name` — corrupts the data; e.g. "Madonna Madonna" implies the customer entered both names
- `""` (current) — crashes (the bug)

`"-"` wins on terseness, queryability ("find all customers whose last_name is `-`"), and visual unambiguity in the admin UI ("Madonna -"). If product later prefers `"(unknown)"` or another value, the change is localized to `_MISSING_LAST_NAME_PLACEHOLDER`.

### Confidence score

**10/10** for one-pass implementation success after the 2026-04-27 main-branch verification pass.

The change is mechanical and tightly bounded: one constant, one assignment swap, one conditional log line, and four near-identical unit tests modeled directly on `test_new_customer_created_when_no_match`. All cross-cutting unknowns are resolved against `main`:

- Container test class is **`TestCheckoutSessionCompleted`** (line 83). New tests go inside it.
- The reference test already patches `CustomerService` and exercises the no-match path — new tests copy its 8-decorator stack verbatim.
- `webhooks.py:283` is the single line to change; `CustomerCreate(` appears at `webhooks.py:310` and nowhere else in the file (verified by `grep`).
- `_MISSING_LAST_NAME_PLACEHOLDER` should be defined just above `class StripeWebhookHandler` (line 73 on `main`).
- `CustomerCreate.last_name` constraint is at `customer.py:62-67` on `main` (or `81-86` on `dev` if implementing on `dev`); `strip_whitespace` validator is at `104-107` on `main`.
- The retired monorepo doc references (`Grins_irrigation/...`) have been replaced with the live `production-bugs/2026-04-26-webhook-empty-last-name-orphaned-agreements.md`.

There is no remaining residual risk that requires runtime discovery during implementation.
