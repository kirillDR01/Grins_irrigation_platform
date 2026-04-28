# Feature: biometric-passkey-authentication (Face ID on phones, Touch ID on MacBook)

The following plan should be complete, but it's important that you validate documentation and codebase patterns and task sanity before you start implementing.

Pay special attention to naming of existing utils, types, and models. Import from the right files (e.g. `LoggerMixin` lives in `grins_platform.log_config`, **not** `grins_platform.logging`, despite what the steering doc says).

## Feature Description

Add **WebAuthn / Passkey** authentication so staff can sign in with platform biometrics:
- **Face ID** on iPhone / iPad (Safari, Chrome, etc.)
- **Touch ID** on MacBook (Safari, Chrome)
- **Windows Hello** on Windows laptops (free side-effect — same standard)
- **Android fingerprint / face unlock** (free side-effect)

This is purely additive — username/password login stays as the recovery path. The biometric check happens in the OS against the Secure Enclave / TPM; the server only sees a public key and a signed challenge. **No biometric data ever touches the server or the database.**

## User Story

As a Grin's Irrigation **staff member** (admin, manager, or technician)
I want to **sign in to the platform with Face ID on my iPhone or Touch ID on my MacBook**
So that **I can access the app in one second without typing a username and password**, and so that the company gets phishing-resistant authentication without managing TOTP or SMS 2FA.

## Problem Statement

The current login flow (`src/grins_platform/api/v1/auth.py:77-154`) requires every user to type a username and password every time their JWT cookie expires (60 min access / 30 day refresh). For technicians using personal phones in the field this is high-friction; for office staff it's a phishing surface. There is currently no passwordless or 2FA option, and SMS 2FA isn't a viable fit (we already pay per SMS via CallRail/Twilio, and it's a known phishing target).

## Solution Statement

Implement **WebAuthn level 3 (Passkeys)** as a second login method alongside passwords. Two ceremonies:
1. **Registration** — logged-in user adds a passkey from a settings page; the device's OS handles the biometric prompt.
2. **Authentication** — on the login page, a "Sign in with Face ID / Touch ID" button (and a conditional-UI autofill chip) triggers a biometric prompt; on success the server mints the same JWT access/refresh/CSRF cookies that password login does.

The same backend cookie issuance from `auth.py:114-144` is reused so no other code paths need to know about WebAuthn. Multiple credentials per user are supported (one passkey per device). Passwords remain as the recovery path (no email/SMS recovery for now — `email_service.py` is currently a stub per project memory, so building recovery on top of it would be premature).

## Feature Metadata

**Feature Type**: New Capability
**Estimated Complexity**: Medium (well-scoped, well-supported standard, but touches auth — must not break existing login)
**Primary Systems Affected**:
- Backend auth: `services/auth_service.py`, `api/v1/auth.py`, `models/staff.py`, `repositories/staff_repository.py`
- New domain: `services/webauthn_service.py`, `api/v1/webauthn.py`, `models/webauthn_credential.py`, `repositories/webauthn_credential_repository.py`
- Database: one new migration adding two tables
- Frontend auth: `frontend/src/features/auth/components/LoginPage.tsx`, `AuthProvider.tsx`, `api/index.ts`
- New frontend: `frontend/src/features/auth/components/PasskeyManager.tsx`, `api/webauthn.ts`

**Dependencies**:
- Python: `webauthn>=2.7.0,<3.0.0` (a.k.a. `py_webauthn` from duo-labs)
- Node: `@simplewebauthn/browser@^13.3.0`
- Existing: Redis (already wired via `redis>=5.0.0`) for short-TTL challenge cache

---

## CONTEXT REFERENCES

### Relevant Codebase Files — IMPORTANT: YOU MUST READ THESE BEFORE IMPLEMENTING

**Auth surface to extend / mirror:**
- `src/grins_platform/api/v1/auth.py` (entire file, 307 lines) — Why: cookie-issuance pattern at lines 114-144 must be reused verbatim by `/webauthn/authenticate/finish`; router prefix `/auth` is shared.
- `src/grins_platform/services/auth_service.py` (lines 97-119, 355-431, 432-448) — Why: `LoggerMixin` subclassing pattern with `DOMAIN = "auth"`; `_create_access_token` / `_create_refresh_token` / `get_user_role` are the helpers we must call to mint the same JWTs.
- `src/grins_platform/api/v1/auth_dependencies.py` (lines 37-49, 109-132, 299-303) — Why: `get_auth_service`, `get_current_active_user`, the `CurrentActiveUser` `Annotated` alias — reused on registration/list/delete endpoints.
- `src/grins_platform/exceptions/auth.py` (entire file, 102 lines) — Why: exception hierarchy to extend (new exceptions inherit `AuthenticationError`).
- `src/grins_platform/schemas/auth.py` (lines 47-74) — Why: `UserResponse` and `LoginResponse` — `/webauthn/authenticate/finish` returns the **same** `LoginResponse` shape so the frontend `AuthProvider.login()` flow stays identical.
- `src/grins_platform/models/staff.py` (lines 27-92) — Why: target FK; the `is_login_enabled` and `is_active` checks at `auth_service.py:387-394, 127` must be enforced in WebAuthn auth too.
- `src/grins_platform/repositories/staff_repository.py` (lines 27-49, 435-462) — Why: repository pattern with `LoggerMixin`, `DOMAIN = "database"`, `find_by_username` lookup we'll mirror.

**Migration / model template:**
- `src/grins_platform/migrations/versions/20260425_100000_add_appointment_notes_table.py` (entire file, 72 lines) — Why: latest single-table migration showing exact frontmatter (`revision`, `down_revision`, `branch_labels`, `depends_on`), `gen_random_uuid()` PK, `ondelete="CASCADE"`/`SET NULL`, index naming (`idx_*` or `ix_*`), separate `upgrade()`/`downgrade()`. Mirror this exactly.
- `src/grins_platform/migrations/versions/20260423_100000_add_customer_tags_table.py` (entire file, 80 lines) — Why: shows `CheckConstraint`, `UniqueConstraint`, `JSONB`-style enum strings — the closest analogue to the `transports` JSON column we need.
- `src/grins_platform/migrations/versions/20260426_100000_add_sales_calendar_assigned_to.py` — Why: this is currently the latest migration **on disk** (untracked), so our new migration's `down_revision` must point to its `revision` ID. **Read this file first to capture its revision ID.**

**Router registration:**
- `src/grins_platform/api/v1/router.py` (line 26 import + line 78 include) — Why: pattern for adding a new router. Auth router has no prefix override (it carries `/auth` itself), so the WebAuthn router will mount **inside** the auth router (preferred — see Task 8) or as a sibling.

**App-level exception handlers:**
- `src/grins_platform/app.py` (lines 272-396, 692-790) — Why: pattern for `@app.exception_handler(...)` registration; the SignWell handlers at lines 692-790 are the closest analogue (HTTP 401/404/502 mapping with the standard `{success, error: {code, message}}` envelope).

**Frontend auth:**
- `frontend/src/features/auth/components/LoginPage.tsx` (entire file, 199 lines) — Why: surgical edit target; we add a "Sign in with biometrics" button + `autocomplete="username webauthn"` to the username input.
- `frontend/src/features/auth/components/AuthProvider.tsx` (lines 167-175) — Why: existing `login(credentials)` callback; we add a sibling `loginWithPasskey()` that calls the WebAuthn API and then runs the same state updates (`setAccessToken`, `setUser`, `scheduleTokenRefresh`).
- `frontend/src/features/auth/api/index.ts` (entire file, 87 lines) — Why: the `apiClient.post(..., { withCredentials: true })` pattern; mirror it.
- `frontend/src/features/auth/types/index.ts` (entire file, 53 lines) — Why: types extension target — add `WebAuthnRegistrationOptions`, `WebAuthnAuthenticationOptions`, `Passkey` shapes here.

**Test patterns:**
- `src/grins_platform/tests/unit/test_auth_service.py` (lines 1-120) — Why: mock-based unit-test pattern (`@pytest.fixture` → `AsyncMock` repository → service under test → `@pytest.mark.unit` on classes).
- `src/grins_platform/tests/test_auth_api.py` (lines 1-100) — Why: `httpx.AsyncClient(transport=ASGITransport(app=app))` API-test pattern with `app.dependency_overrides`.
- `src/grins_platform/tests/integration/test_auth_integration.py` (lines 1-80) — Why: integration test fixture pattern (mock Staff with all auth fields populated).

**Steering / conventions:**
- `.kiro/steering/code-standards.md` (entire file, 85 lines) — Why: mandates structured logging, three-tier tests, MyPy + Pyright must pass with zero errors, three test markers (`@pytest.mark.unit/functional/integration`).
- `.kiro/steering/api-patterns.md` (entire file, 86 lines) — Why: `set_request_id`/`clear_request_id` + `DomainLogger.api_event` pattern, but **note**: the actual endpoints in `auth.py` use the simpler `LoggerMixin`-via-service pattern instead — mirror `auth.py` not the steering doc when in conflict (steering is aspirational).

### New Files to Create

**Backend (Python):**
- `src/grins_platform/migrations/versions/20260427_100000_add_webauthn_credentials_table.py` — Alembic migration creating `webauthn_credentials` and `webauthn_user_handles` tables. (Bump date if 04-27 is taken at execution time.)
- `src/grins_platform/models/webauthn_credential.py` — `WebAuthnCredential` and `WebAuthnUserHandle` SQLAlchemy models.
- `src/grins_platform/repositories/webauthn_credential_repository.py` — `WebAuthnCredentialRepository` with CRUD + `find_by_credential_id`, `find_by_staff_id`, `update_sign_count`, `revoke`. Plus `WebAuthnUserHandleRepository.get_or_create_for_staff`.
- `src/grins_platform/services/webauthn_service.py` — `WebAuthnService(LoggerMixin)` with `DOMAIN = "auth"`. Methods: `start_registration`, `finish_registration`, `start_authentication`, `finish_authentication`, `list_credentials`, `revoke_credential`. Stores per-ceremony challenge state in Redis keyed by an opaque handle.
- `src/grins_platform/services/webauthn_config.py` — `WebAuthnSettings(BaseSettings)` for `WEBAUTHN_RP_ID`, `WEBAUTHN_RP_NAME`, `WEBAUTHN_EXPECTED_ORIGINS` (comma-separated → list).
- `src/grins_platform/schemas/webauthn.py` — Pydantic schemas: `RegistrationBeginResponse`, `RegistrationFinishRequest`, `AuthenticationBeginRequest`, `AuthenticationBeginResponse`, `AuthenticationFinishRequest`, `PasskeyResponse`, `PasskeyListResponse`.
- `src/grins_platform/api/v1/webauthn.py` — FastAPI router with the 6 endpoints, mounted under `/auth/webauthn`.
- `src/grins_platform/exceptions/auth.py` — **edit, not create** — append: `WebAuthnVerificationError`, `WebAuthnChallengeNotFoundError`, `WebAuthnCredentialNotFoundError`, `WebAuthnDuplicateCredentialError`.

**Backend tests:**
- `src/grins_platform/tests/unit/test_webauthn_service.py` — unit tests for `WebAuthnService` (mocked repo + Redis + `webauthn` library).
- `src/grins_platform/tests/unit/test_webauthn_api.py` — API endpoint tests using `app.dependency_overrides` + `AsyncClient`.
- `src/grins_platform/tests/integration/test_webauthn_integration.py` — integration test for register → authenticate → cookie issuance round-trip (fully mocked authenticator since we can't drive a real device in CI; uses `webauthn`'s test helpers if available, otherwise hand-crafted CBOR fixtures).
- `src/grins_platform/tests/unit/test_webauthn_credential_model.py` — model-level tests (constraints, defaults).
- `src/grins_platform/tests/test_webauthn_property.py` — Hypothesis property-based tests (mirror `tests/test_auth_property.py`). Required by `.kiro/steering/spec-testing-standards.md` for "business logic with invariants" (sign-count monotonicity, base64url round-trip, credential_id uniqueness across staff).
- `src/grins_platform/tests/functional/test_webauthn_functional.py` — functional tests (`@pytest.mark.functional`, real DB) for the credential repository CRUD path. Required by the three-tier test mandate.

**Frontend (TypeScript):**
- `frontend/src/features/auth/api/webauthn.ts` — `webauthnApi` with `registerBegin`, `registerFinish`, `authenticateBegin`, `authenticateFinish`, `listPasskeys`, `revokePasskey`.
- `frontend/src/features/auth/api/keys.ts` — TanStack Query key factory `passkeyKeys` (mirror `customerKeys` pattern from `.kiro/steering/frontend-patterns.md` lines 75-82).
- `frontend/src/features/auth/types/webauthn.ts` — TypeScript types mirroring `schemas/webauthn.py`.
- `frontend/src/features/auth/components/PasskeyManager.tsx` — list / register / revoke UI for the Settings page.
- `frontend/src/features/auth/components/PasskeyManager.test.tsx` — Vitest component tests, wrapped in `QueryProvider` per `.kiro/steering/frontend-testing.md` lines 11-13.
- `frontend/src/features/auth/hooks/usePasskeyAuth.ts` — `useLoginWithPasskey()` and `useRegisterPasskey()` hooks wrapping `startAuthentication()`/`startRegistration()` + cookie-mint round-trip.

**E2E:**
- `e2e/test-webauthn-passkey.sh` — agent-browser shell script per `.kiro/steering/e2e-testing-skill.md`. Validates the visible (non-biometric) parts of the flow: passkey button presence on `/login`, settings → security navigation, list rendering, error states. Cannot drive the OS biometric prompt itself — that requires manual testing (Task 30).

**Files to update (not create):**
- `pyproject.toml` — add `webauthn>=2.7.0,<3.0.0` to `dependencies`.
- `frontend/package.json` — add `@simplewebauthn/browser` to `dependencies`.
- `.env.example` — add `WEBAUTHN_RP_ID`, `WEBAUTHN_RP_NAME`, `WEBAUTHN_EXPECTED_ORIGINS` with dev defaults.
- `src/grins_platform/api/v1/auth.py` — mount the new webauthn sub-router (one-line `auth_router.include_router(webauthn_router)`) **OR** register top-level in `router.py` — pick one approach (see Task 8).
- `src/grins_platform/app.py` — register exception handlers for the four new exceptions (mirror SignWell handlers at lines 692-790).
- `src/grins_platform/exceptions/__init__.py` — export the four new exceptions if it currently re-exports auth ones.
- `frontend/src/features/auth/components/AuthProvider.tsx` — add `loginWithPasskey` to context.
- `frontend/src/features/auth/components/LoginPage.tsx` — add biometric button + `autocomplete="username webauthn"`.
- `frontend/src/features/auth/types/index.ts` — extend `AuthContextValue` with `loginWithPasskey`.

### Relevant Documentation — YOU SHOULD READ THESE BEFORE IMPLEMENTING

- [py_webauthn (duo-labs) on PyPI](https://pypi.org/project/webauthn/) — current stable **2.7.1**, Python ≥3.9.
- [py_webauthn registration example](https://github.com/duo-labs/py_webauthn/blob/master/examples/registration.py) — Why: canonical begin/finish pattern.
- [py_webauthn authentication example](https://github.com/duo-labs/py_webauthn/blob/master/examples/authentication.py) — Why: ditto for sign-in.
- [`verify_registration_response` source](https://github.com/duo-labs/py_webauthn/blob/master/webauthn/registration/verify_registration_response.py) — Why: confirm exact `VerifiedRegistration` field names (e.g. `credential_public_key`, `aaguid`, `credential_device_type`, `credential_backed_up`).
- [`webauthn.helpers` exports](https://github.com/duo-labs/py_webauthn/blob/master/webauthn/helpers/__init__.py) — Why: `bytes_to_base64url`, `base64url_to_bytes`, `parse_registration_credential_json`, `options_to_json`.
- [@simplewebauthn/browser docs](https://simplewebauthn.dev/docs/packages/browser) — Why: latest API uses `{ optionsJSON }` arg shape (changed in v9), conditional UI via `useBrowserAutofill: true`.
- [@simplewebauthn/browser on npm](https://www.npmjs.com/package/@simplewebauthn/browser) — current stable **13.3.0**.
- [W3C WebAuthn Level 3 spec](https://www.w3.org/TR/webauthn-3/) — Why: reference for `userVerification`, `residentKey`, `authenticatorAttachment` semantics. Skim §5 (Authenticator Selection) and §6 (Credential Storage).
- [Apple Passkey documentation](https://developer.apple.com/passkeys/) — Why: Apple-specific quirks (iCloud Keychain sync, "associated domains" not required for web-only flow).

### Patterns to Follow

**Naming conventions** (extracted from codebase):
- Python files: `snake_case.py`. Models: singular noun. Repositories/services: `<noun>_repository.py` / `<noun>_service.py`.
- Class names: `PascalCase`. Service classes inherit `LoggerMixin` and define `DOMAIN: ClassVar[str]` ≈ `"auth"` / `"database"`.
- DB tables: `snake_case`, plural (`webauthn_credentials`, `webauthn_user_handles`).
- DB indexes: `idx_<table>_<col>` or `ix_<table>_<col>` (both seen — pick `ix_` for new ones since that's what the latest migration uses for `customer_tags`).
- API endpoints: `kebab-case` paths (`/auth/webauthn/register/begin`).
- Frontend components: `PascalCase.tsx`. Hooks: `useFoo.ts`. API modules: `lowercase.ts`.
- Exception names: `<Noun><Verb>Error` ending in `Error`, all inheriting `AuthenticationError`.

**Logging pattern** — from `services/auth_service.py:97-119, 355-431`:
```python
class WebAuthnService(LoggerMixin):
    DOMAIN = "auth"

    async def finish_registration(self, ...):
        self.log_started("finish_registration", staff_id=str(staff_id))
        try:
            verification = verify_registration_response(...)
        except InvalidRegistrationResponse as e:
            self.log_rejected("finish_registration", reason="invalid_response", error=str(e))
            raise WebAuthnVerificationError from e
        ...
        self.log_completed("finish_registration", staff_id=str(staff_id), credential_id=cred_id_b64)
```
**Never** log the public key, the challenge, or the credential ID raw bytes — log the base64url-encoded credential ID only, since it's a public identifier.

**Exception → HTTP envelope** — from `app.py:272-396`:
Every new exception gets an `@app.exception_handler` returning:
```python
JSONResponse(
    status_code=status.HTTP_<n>,
    content={
        "success": False,
        "error": {"code": "<UPPER_SNAKE>", "message": str(exc), ...optional context},
    },
)
```

**Cookie issuance** — from `api/v1/auth.py:114-144` — the `/webauthn/authenticate/finish` endpoint must set the **same three cookies** (`refresh_token` HttpOnly, `access_token` HttpOnly, `csrf_token` non-HttpOnly) with the **same** `COOKIE_SECURE` / `COOKIE_SAMESITE` / `COOKIE_MAX_AGE` constants. Import the constants — do not duplicate them.

**Migration template** — from `20260425_100000_add_appointment_notes_table.py`:
```python
"""<headline>.

Revision ID: <YYYYMMDD_HHMMSS>
Revises: <prev_revision>
Requirements: <ref>
"""
from __future__ import annotations
from collections.abc import Sequence
import sqlalchemy as sa
from alembic import op

revision: str = "<YYYYMMDD_HHMMSS>"
down_revision: str | None = "<prev>"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None
```

**Repository pattern** — from `repositories/staff_repository.py:41-49`:
```python
class WebAuthnCredentialRepository(LoggerMixin):
    DOMAIN = "database"
    def __init__(self, session: AsyncSession) -> None:
        super().__init__()
        self.session = session
```

**Pydantic schema pattern** — from `schemas/auth.py:47-74` — use `model_config = ConfigDict(from_attributes=True)` for response schemas; use `Field(..., description=...)` for OpenAPI docs.

**API endpoint pattern** — from `api/v1/auth.py:77-154`:
- Use `Annotated[Service, Depends(get_service)]` not legacy `Service = Depends(get_service)`.
- Use `CurrentActiveUser` type alias for protected endpoints.
- Use specific exception → `HTTPException` mapping in route handlers (don't lean on global handlers when you need a particular status code).

**Frontend API pattern** — from `frontend/src/features/auth/api/index.ts:21-28`:
```ts
const response = await apiClient.post<X>(`${BASE}/path`, body, { withCredentials: true });
return response.data;
```

**TanStack Query key factory** — required by `.kiro/steering/frontend-patterns.md:75-91`. Create `frontend/src/features/auth/api/keys.ts`:
```ts
export const passkeyKeys = {
  all: ['passkeys'] as const,
  lists: () => [...passkeyKeys.all, 'list'] as const,
  list: () => [...passkeyKeys.lists()] as const,
  detail: (id: string) => [...passkeyKeys.all, 'detail', id] as const,
};
```
All `useQuery` / `useMutation` hooks use this factory; mutations call `qc.invalidateQueries({ queryKey: passkeyKeys.lists() })` on success.

**React Hook Form + Zod for forms** — required by `.kiro/steering/frontend-patterns.md:31-70`. The "Add Passkey" device-name input must use `useForm({ resolver: zodResolver(schema) })` with a Zod schema:
```ts
const schema = z.object({
  device_name: z.string().min(1, 'Required').max(100, 'Max 100 chars'),
});
```
Wrap in `<Form>` / `<FormField>` / `<FormItem>` / `<FormControl>` / `<FormMessage>` from `@/components/ui/form`.

**Toast for user feedback** — required by `.kiro/steering/frontend-patterns.md:46-52, 110-112`. Use `sonner` (already in `frontend/package.json`):
```ts
import { toast } from 'sonner';
toast.success('Passkey added');
toast.error('Failed to add passkey: ' + error.message);
```
Mutations: try/catch with toast. Queries: render error state inline (no toast).

**`data-testid` convention** — required by `.kiro/steering/frontend-patterns.md:97-98` and `frontend-testing.md`. For this feature:

| Element | data-testid |
|---|---|
| LoginPage container | `login-page` (existing) |
| LoginPage username input | `username-input` (existing) |
| LoginPage password input | `password-input` (existing) |
| LoginPage password-login button | `login-btn` (existing) |
| **NEW** LoginPage biometric login button | `passkey-login-btn` |
| **NEW** LoginPage biometric error alert | `passkey-error` |
| **NEW** Settings security section page | `security-page` |
| **NEW** Passkey list table | `passkey-table` |
| **NEW** Passkey row | `passkey-row` |
| **NEW** Passkey row's revoke button | `revoke-passkey-btn` |
| **NEW** Passkey "Add" trigger button | `add-passkey-btn` |
| **NEW** Passkey add-form dialog | `passkey-form` |
| **NEW** Passkey add-form device-name input | `device-name-input` |
| **NEW** Passkey add-form submit button | `submit-passkey-btn` |
| **NEW** Loading spinner inside passkey list | `passkey-loading-spinner` |
| **NEW** Empty-state placeholder | `passkey-empty-state` |

**Frontend test wrapper** — from `.kiro/steering/frontend-testing.md:11-25`:
```tsx
import { render, screen } from '@testing-library/react';
import { QueryProvider } from '@/core/providers/QueryProvider';
const wrapper = ({ children }) => <QueryProvider>{children}</QueryProvider>;
render(<PasskeyManager />, { wrapper });
```

**DEVLOG entry** — required by `.kiro/steering/devlog-rules.md` and `auto-devlog.md` after any feature lands. Entry goes at the **top** of `DEVLOG.md` immediately after the `## Recent Activity` header. Use category `SECURITY` (could also be `FEATURE` — `SECURITY` is more specific). Structure: What Was Accomplished / Technical Details / Decision Rationale / Challenges and Solutions / Next Steps.

---

## IMPLEMENTATION PLAN

### Phase 1: Foundation (Backend infra)

Goal: a passing migration and config in place before any business logic.

**Tasks:**
- Add `webauthn` Python dependency via `uv add`
- Add `WebAuthnSettings` config class
- Add four new exceptions to `exceptions/auth.py`
- Create the Alembic migration with both tables

### Phase 2: Domain layer

Goal: model, repository, service, schemas — all unit-tested in isolation before any HTTP wiring.

**Tasks:**
- `WebAuthnCredential` and `WebAuthnUserHandle` SQLAlchemy models
- Repositories with the queries the service needs
- Pydantic schemas for the API layer
- `WebAuthnService` with begin/finish/list/revoke methods

### Phase 3: API layer

Goal: HTTP endpoints + dependency injection + exception handlers + router wiring.

**Tasks:**
- `api/v1/webauthn.py` with 6 endpoints
- Mount in router; add exception handlers in `app.py`
- Smoke-test via Swagger UI at `/docs`

### Phase 4: Frontend integration

Goal: visible biometric button on login page and a manage-passkeys section in settings.

**Tasks:**
- `@simplewebauthn/browser` dependency
- TypeScript types + `webauthnApi` client
- `loginWithPasskey()` in `AuthProvider`
- Login page button + autofill attribute
- `PasskeyManager` component for settings

### Phase 5: Testing & validation

Goal: three-tier coverage + manual smoke on a real device.

**Tasks:**
- Unit tests (service + API + model)
- Integration test (full ceremony round-trip with stubbed authenticator)
- Frontend component tests
- Manual: enroll on Mac (Touch ID) → log out → log in. Repeat on iPhone (Face ID).

---

## STEP-BY-STEP TASKS

IMPORTANT: Execute every task in order, top to bottom. Each task is atomic and independently testable.

### Task 1 — ADD `webauthn` dependency to `pyproject.toml`

- **IMPLEMENT**: Append `"webauthn>=2.7.0,<3.0.0"` to the `dependencies` list in `pyproject.toml` (alphabetical insertion near `weasyprint`).
- **PATTERN**: `pyproject.toml:21-57`.
- **IMPORTS**: n/a.
- **GOTCHA**: The package name on PyPI is `webauthn`, not `py_webauthn`. The Python import is `import webauthn`.
- **VALIDATE**: `uv sync && uv run python -c "import webauthn; print(webauthn.__version__)"` — should print `2.7.x`.

### Task 2 — ADD WebAuthn-specific exceptions to `src/grins_platform/exceptions/auth.py`

- **IMPLEMENT**: Append four new exception classes (all inheriting `AuthenticationError`):
  - `WebAuthnVerificationError` — raised when `verify_registration_response` or `verify_authentication_response` fails.
  - `WebAuthnChallengeNotFoundError` — raised when the Redis challenge key is missing or expired.
  - `WebAuthnCredentialNotFoundError` — raised when looking up a credential by `credential_id` returns nothing.
  - `WebAuthnDuplicateCredentialError` — raised when registration would create a duplicate (already-bound) credential.
- **PATTERN**: `exceptions/auth.py:13-92` — single-arg `__init__` with default message, no extra fields. Update `__all__` at the bottom.
- **IMPORTS**: existing `AuthenticationError` is in the same file.
- **GOTCHA**: Keep messages user-safe (no internal details). Don't change the order of existing exceptions in `__all__`.
- **VALIDATE**: `uv run python -c "from grins_platform.exceptions.auth import WebAuthnVerificationError, WebAuthnChallengeNotFoundError, WebAuthnCredentialNotFoundError, WebAuthnDuplicateCredentialError; print('ok')"`.

### Task 3 — CREATE `src/grins_platform/services/webauthn_config.py`

- **IMPLEMENT**:
  ```python
  class WebAuthnSettings(BaseSettings):
      webauthn_rp_id: str = "localhost"
      webauthn_rp_name: str = "Grin's Irrigation"
      webauthn_expected_origins: str = "http://localhost:5173"
      webauthn_challenge_ttl_seconds: int = 300

      model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

      @property
      def expected_origins_list(self) -> list[str]:
          return [o.strip() for o in self.webauthn_expected_origins.split(",") if o.strip()]
  ```
- **PATTERN**: `database.py:26-43` (`DatabaseSettings`); `services/stripe_config.py` is the closest analogue.
- **IMPORTS**: `from pydantic_settings import BaseSettings, SettingsConfigDict`.
- **GOTCHA**: `webauthn_rp_id` is **the bare effective domain** — no scheme, no port, no path. Browsers reject `127.0.0.1`; use `localhost`. In prod `WEBAUTHN_RP_ID=app.grins.com` and `WEBAUTHN_EXPECTED_ORIGINS=https://app.grins.com`.
- **VALIDATE**: `uv run python -c "from grins_platform.services.webauthn_config import WebAuthnSettings; s = WebAuthnSettings(); print(s.webauthn_rp_id, s.expected_origins_list)"`.

### Task 4 — UPDATE `.env.example` with WebAuthn vars

- **IMPLEMENT**: Append:
  ```
  # WebAuthn / Passkey authentication
  WEBAUTHN_RP_ID=localhost
  WEBAUTHN_RP_NAME=Grin's Irrigation
  WEBAUTHN_EXPECTED_ORIGINS=http://localhost:5173,http://localhost:5174
  WEBAUTHN_CHALLENGE_TTL_SECONDS=300
  ```
- **PATTERN**: existing comment-block sections in `.env.example`.
- **IMPORTS**: n/a.
- **GOTCHA**: Production values must be set in Railway env vars (NOT committed to the repo).
- **VALIDATE**: `grep -c WEBAUTHN .env.example` — expect ≥ 4.

### Task 5 — CREATE Alembic migration for `webauthn_credentials` + `webauthn_user_handles`

- **PRE-VERIFIED FACT** (confirmed via `uv run alembic heads` at planning time, 2026-04-25): the **current head is `20260426_100000`** (from `migrations/versions/20260426_100000_add_sales_calendar_assigned_to.py`). Use this as the `down_revision`. If a newer migration has been added between planning and execution, run `uv run alembic heads` and use whatever it reports.
- **IMPLEMENT**: New file `src/grins_platform/migrations/versions/20260427_100000_add_webauthn_credentials_table.py`. Two tables in one migration:

  **`webauthn_user_handles`** — opaque per-staff handle for ceremonies (kept separate from staff so we never expose it on the staff response and so reverting WebAuthn doesn't touch the staff table):
  - `staff_id UUID PK FK staff(id) ON DELETE CASCADE`
  - `user_handle BYTEA UNIQUE NOT NULL` — random 64-byte handle generated once per staff
  - `created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`

  **`webauthn_credentials`**:
  - `id UUID PK DEFAULT gen_random_uuid()`
  - `staff_id UUID NOT NULL FK staff(id) ON DELETE CASCADE`
  - `credential_id BYTEA NOT NULL UNIQUE` — raw bytes from the authenticator
  - `public_key BYTEA NOT NULL` — opaque COSE-encoded public key
  - `sign_count BIGINT NOT NULL DEFAULT 0`
  - `transports JSONB NULL` — list[str] e.g. `["internal", "hybrid"]`
  - `aaguid VARCHAR(36) NULL`
  - `credential_device_type VARCHAR(20) NOT NULL` — `"single_device"` or `"multi_device"`
  - `backup_eligible BOOLEAN NOT NULL DEFAULT FALSE`
  - `backup_state BOOLEAN NOT NULL DEFAULT FALSE`
  - `device_name VARCHAR(100) NOT NULL` — user-provided ("Kirill's MacBook Pro")
  - `last_used_at TIMESTAMPTZ NULL`
  - `revoked_at TIMESTAMPTZ NULL`
  - `created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`
  - Indexes: `ix_webauthn_credentials_staff_id`, `ix_webauthn_credentials_credential_id` (in addition to the unique constraint)
  - Check constraint: `ck_webauthn_credentials_device_type CHECK (credential_device_type IN ('single_device', 'multi_device'))`
- **PATTERN**: `20260425_100000_add_appointment_notes_table.py` for frontmatter; `20260423_100000_add_customer_tags_table.py` for `CheckConstraint` + `UniqueConstraint`.
- **IMPORTS**: `import sqlalchemy as sa; from alembic import op`.
- **GOTCHA**:
  - `down_revision: str | None = "20260426_100000"` (confirmed head — see PRE-VERIFIED FACT above). The previous migration is `add_sales_calendar_assigned_to`.
  - Use `sa.LargeBinary()` for the BYTEA columns, not `sa.Binary()` (deprecated).
  - Use `sa.dialects.postgresql.JSONB` for `transports`, not `sa.JSON` (we want index-friendly JSONB).
  - The `downgrade()` must drop both tables in reverse order, indexes first. Drop `webauthn_credentials` before `webauthn_user_handles` (no FK between them, but drop in reverse-create order out of habit).
- **VALIDATE**: `uv run alembic upgrade head && uv run alembic downgrade -1 && uv run alembic upgrade head` — round-trip must succeed cleanly. Then `psql "$DATABASE_URL" -c "\d webauthn_credentials"` shows the columns.

### Task 6 — CREATE `src/grins_platform/models/webauthn_credential.py`

- **IMPLEMENT**: Two models — `WebAuthnUserHandle` and `WebAuthnCredential` — using SQLAlchemy 2.0 `Mapped`/`mapped_column` syntax. Mirror `models/staff.py:54-152` for column declarations.
- **PATTERN**: `models/staff.py` for syntax; `models/appointment_note.py` for a recent simple model with FK.
- **IMPORTS**:
  ```python
  from sqlalchemy import LargeBinary, Boolean, BigInteger, ForeignKey, String, DateTime, CheckConstraint
  from sqlalchemy.dialects.postgresql import JSONB, UUID
  from sqlalchemy.orm import Mapped, mapped_column, relationship
  from sqlalchemy.sql import func
  from grins_platform.database import Base
  ```
- **GOTCHA**:
  - Don't add a `back_populates` relationship to `Staff` unless you also touch `models/staff.py` (which you should — add `webauthn_credentials: Mapped[list["WebAuthnCredential"]] = relationship(..., cascade="all, delete-orphan")` for clean cascading deletes via ORM, mirroring `availability_entries` at `staff.py:158-162`).
  - `sign_count` is `BigInteger`, not `Integer` — authenticators can return values > 2^31.
  - `credential_id` is `LargeBinary`. Use `unique=True` on the column **and** create a separate `ix_*` index for query speed.
- **VALIDATE**: `uv run python -c "from grins_platform.models.webauthn_credential import WebAuthnCredential, WebAuthnUserHandle; print(WebAuthnCredential.__tablename__, WebAuthnUserHandle.__tablename__)"`.

### Task 7 — CREATE `src/grins_platform/repositories/webauthn_credential_repository.py`

- **IMPLEMENT**: Two classes:
  - `WebAuthnUserHandleRepository(LoggerMixin)` — `DOMAIN = "database"`. Methods: `async def get_or_create_for_staff(self, staff_id: UUID) -> bytes` (returns the user_handle bytes; creates if missing using `secrets.token_bytes(64)`).
  - `WebAuthnCredentialRepository(LoggerMixin)` — `DOMAIN = "database"`. Methods:
    - `async def create(self, *, staff_id, credential_id, public_key, sign_count, transports, aaguid, credential_device_type, backup_eligible, backup_state, device_name) -> WebAuthnCredential`
    - `async def find_by_credential_id(self, credential_id: bytes) -> WebAuthnCredential | None` — must filter `revoked_at IS NULL`.
    - `async def list_for_staff(self, staff_id: UUID, *, include_revoked: bool = False) -> list[WebAuthnCredential]`
    - `async def update_sign_count(self, credential_id: bytes, new_sign_count: int) -> None` — also bumps `last_used_at`.
    - `async def revoke(self, credential_id_uuid: UUID, staff_id: UUID) -> bool` — sets `revoked_at = NOW()`, returns True if updated, False if not found / not owned. **Must** check `staff_id` to prevent IDOR.
- **PATTERN**: `repositories/staff_repository.py:27-49, 435-528`.
- **IMPORTS**: standard SQLAlchemy 2.0 async imports (mirror staff_repository).
- **GOTCHA**:
  - `find_by_credential_id` is the hot path — make sure the column has the index from Task 5.
  - Don't return revoked credentials from default lookups; revocation must be effective immediately.
  - `update_sign_count` should use a single `UPDATE ... WHERE credential_id = ...` not select-then-update (race condition).
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_webauthn_credential_repository.py -v` (test created in Task 17).

### Task 8 — CREATE `src/grins_platform/schemas/webauthn.py`

- **IMPLEMENT**: Pydantic schemas. Note that **request bodies for finish endpoints** accept the raw browser JSON as a flexible dict — the `webauthn` library's `parse_*_credential_json` helpers tolerate dict input.
  ```python
  class RegistrationBeginResponse(BaseModel):
      handle: str  # opaque ceremony handle the client returns on /finish
      options: dict  # JSON-serialized PublicKeyCredentialCreationOptions

  class RegistrationFinishRequest(BaseModel):
      handle: str
      device_name: str = Field(..., min_length=1, max_length=100)
      credential: dict  # raw browser response

  class AuthenticationBeginRequest(BaseModel):
      username: str | None = None  # None → discoverable credential flow

  class AuthenticationBeginResponse(BaseModel):
      handle: str
      options: dict

  class AuthenticationFinishRequest(BaseModel):
      handle: str
      credential: dict

  class PasskeyResponse(BaseModel):
      model_config = ConfigDict(from_attributes=True)
      id: UUID
      device_name: str
      credential_device_type: str
      backup_eligible: bool
      created_at: datetime
      last_used_at: datetime | None

  class PasskeyListResponse(BaseModel):
      passkeys: list[PasskeyResponse]
  ```
- **PATTERN**: `schemas/auth.py:47-74` (response shape with `from_attributes=True`).
- **IMPORTS**: `from pydantic import BaseModel, ConfigDict, Field; from uuid import UUID; from datetime import datetime`.
- **GOTCHA**: Re-using `LoginResponse` from `schemas/auth.py` for `/authenticate/finish` (so the frontend can swap auth methods without changing its `User`/cookie handling). **Don't** re-define it.
- **VALIDATE**: `uv run python -c "from grins_platform.schemas.webauthn import RegistrationBeginResponse; print(RegistrationBeginResponse.model_json_schema())"`.

### Task 9 — CREATE `src/grins_platform/services/webauthn_service.py`

- **IMPLEMENT**: `WebAuthnService(LoggerMixin)` with `DOMAIN = "auth"`. Constructor takes `staff_repository`, `credential_repository`, `user_handle_repository`, `auth_service`, `redis_client`, `settings: WebAuthnSettings`. Methods:

  1. `async def start_registration(self, staff: Staff) -> tuple[str, dict]` — generates options via `generate_registration_options(...)`, stashes `{challenge, staff_id, kind: "registration"}` in Redis under `webauthn:challenge:{handle}` with TTL from settings, returns `(handle, options_dict)`.
     - Use `AuthenticatorSelectionCriteria(authenticator_attachment=AuthenticatorAttachment.PLATFORM, resident_key=ResidentKeyRequirement.PREFERRED, user_verification=UserVerificationRequirement.REQUIRED)`.
     - `attestation=AttestationConveyancePreference.NONE`.
     - `exclude_credentials` = list of `PublicKeyCredentialDescriptor(id=row.credential_id, transports=row.transports)` for already-registered credentials of this staff (prevents double-enrollment).
     - `user_id` = bytes from `WebAuthnUserHandleRepository.get_or_create_for_staff`.
     - `user_name` = `staff.username or staff.email or str(staff.id)`.
     - `user_display_name` = `staff.name`.
     - Serialize options with `options_to_json_dict(options)` → return as `options` field.

  2. `async def finish_registration(self, *, staff: Staff, handle: str, credential: dict, device_name: str) -> WebAuthnCredential` — pulls challenge from Redis (raises `WebAuthnChallengeNotFoundError` if gone), calls `verify_registration_response(...)`, persists the credential.
     - **Always delete the Redis key** before returning, on both success and failure paths.
     - Pull `transports` from `credential.get("response", {}).get("transports", [])` since `VerifiedRegistration` does not surface them.
     - `expected_origin = settings.expected_origins_list` (list — library accepts list).
     - `expected_rp_id = settings.webauthn_rp_id`.
     - Wrap library's `InvalidRegistrationResponse` in our `WebAuthnVerificationError`.

  3. `async def start_authentication(self, *, username: str | None) -> tuple[str, dict]` — generates options via `generate_authentication_options(...)`. If `username` is provided, populate `allow_credentials` from that user's existing credentials; if `None`, leave empty for discoverable-credential autofill flow.
     - Stash `{challenge, username_or_none, kind: "authentication"}` in Redis.

  4. `async def finish_authentication(self, *, handle: str, credential: dict) -> tuple[Staff, str, str, str]` — verifies, looks up the credential by `credential.id` (base64url-decoded), loads owning staff, calls `auth_service._create_access_token` / `_create_refresh_token` and generates a CSRF token. Returns the same 4-tuple `authenticate()` returns at `auth_service.py:430`.
     - Enforce `staff.is_login_enabled` and `staff.is_active` (mirror `auth_service.py:387-394`, `127`).
     - Detect `sign_count` regression: if `verification.new_sign_count > 0 and verification.new_sign_count <= stored.sign_count`, raise `WebAuthnVerificationError` and **revoke** the credential (defense-in-depth against cloning).
     - Update `sign_count` and `last_used_at` via repo.

  5. `async def list_credentials(self, staff: Staff) -> list[WebAuthnCredential]` — straight passthrough to repo.

  6. `async def revoke_credential(self, *, credential_id_uuid: UUID, staff: Staff) -> None` — calls `repo.revoke(credential_id_uuid, staff.id)`. If returns False, raise `WebAuthnCredentialNotFoundError`.

- **PATTERN**: `services/auth_service.py:97-119, 355-431, 432-448`.
- **IMPORTS**:
  ```python
  from webauthn import (
      generate_registration_options,
      verify_registration_response,
      generate_authentication_options,
      verify_authentication_response,
      options_to_json,
  )
  from webauthn.helpers import (
      bytes_to_base64url, base64url_to_bytes, options_to_json_dict,
      parse_registration_credential_json, parse_authentication_credential_json,
  )
  from webauthn.helpers.structs import (
      AuthenticatorSelectionCriteria, AuthenticatorAttachment,
      ResidentKeyRequirement, UserVerificationRequirement,
      AttestationConveyancePreference, PublicKeyCredentialDescriptor,
  )
  from webauthn.helpers.exceptions import InvalidRegistrationResponse, InvalidAuthenticationResponse
  ```
- **GOTCHA**:
  - `options_to_json_dict` returns a dict with **base64url-encoded bytes already** — safe to JSON-serialize. Don't manually re-encode.
  - The Redis challenge value should be a JSON string with `bytes_to_base64url(challenge)` since challenge is bytes.
  - Handle = `secrets.token_urlsafe(32)`. Don't use the credential ID or user ID as the Redis key.
  - Be careful with the `credential` dict shape — `startRegistration` and `startAuthentication` from `@simplewebauthn/browser` v13 return slightly different shapes than v8. Use `parse_*_credential_json` helpers to normalize.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_webauthn_service.py -v` (Task 16).

### Task 10 — CREATE `src/grins_platform/api/v1/webauthn.py`

- **IMPLEMENT**: New router `router = APIRouter(prefix="/auth/webauthn", tags=["auth-webauthn"])` with 6 endpoints:
  1. `POST /register/begin` — auth required (`CurrentActiveUser`); returns `RegistrationBeginResponse`.
  2. `POST /register/finish` — auth required; takes `RegistrationFinishRequest`; returns `PasskeyResponse` (the just-created credential).
  3. `POST /authenticate/begin` — **public**; takes `AuthenticationBeginRequest`; returns `AuthenticationBeginResponse`.
  4. `POST /authenticate/finish` — **public**; takes `AuthenticationFinishRequest`; returns `LoginResponse` from `schemas/auth`. **Sets the same three cookies as `/auth/login`** — import `REFRESH_TOKEN_COOKIE`, `ACCESS_TOKEN_COOKIE`, `CSRF_TOKEN_COOKIE`, `COOKIE_MAX_AGE`, `ACCESS_COOKIE_MAX_AGE`, `COOKIE_SECURE`, `COOKIE_SAMESITE` from `api/v1/auth.py`.
  5. `GET /credentials` — auth required; returns `PasskeyListResponse`.
  6. `DELETE /credentials/{credential_uuid}` — auth required; returns `204 No Content`.

  Add a `get_webauthn_service` dependency in `api/v1/auth_dependencies.py` (or in this file — pattern allows either; auth_dependencies.py is cleaner).

- **PATTERN**: `api/v1/auth.py:77-154` (the `/login` endpoint) for cookie issuance; mirror **exactly** for `/authenticate/finish`.
- **IMPORTS**: standard FastAPI + the new schemas + the existing cookie constants from `auth.py`.
- **GOTCHA**:
  - Map `WebAuthnVerificationError` → `HTTPException(401, "Authentication failed")` in the route (per-route mapping; don't rely on global handler for the 401 since global maps differently).
  - Map `WebAuthnChallengeNotFoundError` → `HTTPException(400, "Challenge expired or invalid")`.
  - Map `WebAuthnCredentialNotFoundError` → `HTTPException(404, "Passkey not found")`.
  - Don't accept `username` from query string in `/authenticate/begin` — use a JSON body so it's not logged in URL access logs.
  - `DELETE /credentials/{credential_uuid}` — path param is the credential row's UUID, not the credential_id bytes.
  - **CSRF (PRE-VERIFIED at planning time)**: `CSRFMiddleware` exists at `src/grins_platform/middleware/csrf.py:45-159` and accepts an `exempt_paths` set in its constructor. Currently exempts `/api/v1/auth/login`, `/api/v1/auth/refresh`, `/health`, `/docs`, `/redoc`, `/openapi.json`. **The middleware is NOT currently registered in `app.py`** (verified — `app.py:217-229` registers CORS, RequestSizeLimit, SecurityHeaders, and rate limiting — no CSRFMiddleware). So as the codebase stands today, no CSRF check runs against any endpoint. Safe path: still update the default `exempt_paths` in `csrf.py:73-80` to include `/api/v1/auth/webauthn/authenticate/begin` and `/api/v1/auth/webauthn/authenticate/finish` so that **if** someone registers the middleware later, our pre-auth endpoints don't break. (The two register endpoints under `/auth/webauthn/register/*` are CSRF-protected by design — the user is logged in and has a CSRF cookie at that point.)
- **VALIDATE**: `uv run uvicorn grins_platform.main:app --port 8001 &` then `curl -s localhost:8001/openapi.json | python -c "import json, sys; spec = json.load(sys.stdin); paths = [p for p in spec['paths'] if 'webauthn' in p]; print(paths)"` — should list 6 paths.

### Task 11 — UPDATE `src/grins_platform/api/v1/router.py` to mount the WebAuthn router

- **IMPLEMENT**: Add `from grins_platform.api.v1.webauthn import router as webauthn_router` (alphabetical with the other auth imports), and `api_router.include_router(webauthn_router)` (alphabetical with other includes).
- **PATTERN**: `router.py:26, 78` (auth router include).
- **IMPORTS**: covered above.
- **GOTCHA**: The webauthn router has its own `prefix="/auth/webauthn"` — **do not** add another prefix in the include call. The auth router is included with no prefix, and the webauthn router carries its own — final paths are `/api/v1/auth/webauthn/*`.
- **VALIDATE**: `uv run python -c "from grins_platform.api.v1.router import api_router; print([r.path for r in api_router.routes if 'webauthn' in r.path])"` — 6 routes.

### Task 12 — UPDATE `src/grins_platform/app.py` to register WebAuthn exception handlers

- **IMPLEMENT**: Inside `_register_exception_handlers`, append four handlers mirroring the SignWell handlers at `app.py:692-790`:
  - `WebAuthnVerificationError` → 401, code `WEBAUTHN_VERIFICATION_FAILED`.
  - `WebAuthnChallengeNotFoundError` → 400, code `WEBAUTHN_CHALLENGE_NOT_FOUND`.
  - `WebAuthnCredentialNotFoundError` → 404, code `WEBAUTHN_CREDENTIAL_NOT_FOUND`.
  - `WebAuthnDuplicateCredentialError` → 409, code `WEBAUTHN_DUPLICATE_CREDENTIAL`.
- **PATTERN**: `app.py:692-790` (SignWell handlers).
- **IMPORTS**: add the four exceptions to the existing `from grins_platform.exceptions import (...)` block at `app.py:23-43`. Also ensure `exceptions/__init__.py` re-exports them (touch that file if it has an `__all__`).
- **GOTCHA**: Routes that raise `HTTPException` directly will bypass these handlers — that's fine; these are for unhandled raises only.
- **VALIDATE**: `uv run python -c "from grins_platform.app import app; print('handlers ok')"` — must not raise.

### Task 13 — ADD `@simplewebauthn/browser` to `frontend/package.json`

- **IMPLEMENT**: `cd frontend && npm install @simplewebauthn/browser@^13.3.0`.
- **PATTERN**: `frontend/package.json:19-61` (alphabetical dependency list).
- **IMPORTS**: n/a.
- **GOTCHA**: This bumps `package-lock.json`. Confirm Vite still builds (no peer dep complaints).
- **VALIDATE**: `cd frontend && npm run build` — succeeds. Then `cd frontend && node -e "console.log(require('@simplewebauthn/browser/package.json').version)"` — prints 13.x.

### Task 14 — CREATE `frontend/src/features/auth/types/webauthn.ts`

- **IMPLEMENT**: TypeScript types mirroring `schemas/webauthn.py`:
  ```ts
  export interface RegistrationBeginResponse { handle: string; options: PublicKeyCredentialCreationOptionsJSON; }
  export interface RegistrationFinishRequest { handle: string; device_name: string; credential: RegistrationResponseJSON; }
  export interface AuthenticationBeginRequest { username?: string; }
  export interface AuthenticationBeginResponse { handle: string; options: PublicKeyCredentialRequestOptionsJSON; }
  export interface AuthenticationFinishRequest { handle: string; credential: AuthenticationResponseJSON; }
  export interface Passkey { id: string; device_name: string; credential_device_type: 'single_device' | 'multi_device'; backup_eligible: boolean; created_at: string; last_used_at: string | null; }
  export interface PasskeyListResponse { passkeys: Passkey[]; }
  ```
- **PATTERN**: `frontend/src/features/auth/types/index.ts:1-53`.
- **IMPORTS**: `import type { PublicKeyCredentialCreationOptionsJSON, PublicKeyCredentialRequestOptionsJSON, RegistrationResponseJSON, AuthenticationResponseJSON } from '@simplewebauthn/browser';`.
- **GOTCHA**: Don't redefine the `*JSON` types — they're exported by the library.
- **VALIDATE**: `cd frontend && npm run typecheck`.

### Task 15 — CREATE `frontend/src/features/auth/api/webauthn.ts`

- **IMPLEMENT**: `webauthnApi` module with 6 functions, all using `apiClient` and `withCredentials: true`:
  - `registerBegin(): Promise<RegistrationBeginResponse>`
  - `registerFinish(req: RegistrationFinishRequest): Promise<Passkey>`
  - `authenticateBegin(req: AuthenticationBeginRequest): Promise<AuthenticationBeginResponse>`
  - `authenticateFinish(req: AuthenticationFinishRequest): Promise<LoginResponse>` (re-uses `LoginResponse` from `../types`)
  - `listPasskeys(): Promise<PasskeyListResponse>`
  - `revokePasskey(id: string): Promise<void>`
- **PATTERN**: `frontend/src/features/auth/api/index.ts:1-87`.
- **IMPORTS**: `import { apiClient } from '@/core/api/client';`.
- **GOTCHA**: Base path is `/auth/webauthn`. Re-export from `frontend/src/features/auth/api/index.ts` so `import { webauthnApi } from '@/features/auth/api'` works.
- **VALIDATE**: `cd frontend && npm run typecheck`.

### Task 16 — CREATE `frontend/src/features/auth/api/keys.ts` and `frontend/src/features/auth/hooks/usePasskeyAuth.ts`

- **IMPLEMENT**:
  1. `keys.ts` — TanStack Query key factory (see "Patterns to Follow" → "TanStack Query key factory").
  2. `usePasskeyAuth.ts`:
     - `useLoginWithPasskey()` — returns a callback that runs the auth ceremony.
       ```ts
       export function useLoginWithPasskey() {
         const { setAuthState } = useAuth();
         return useCallback(async (username?: string) => {
           const begin = await webauthnApi.authenticateBegin({ username });
           const credential = await startAuthentication({ optionsJSON: begin.options });
           const loginResponse = await webauthnApi.authenticateFinish({ handle: begin.handle, credential });
           setAuthState(loginResponse);
         }, [setAuthState]);
       }
       ```
     - `useRegisterPasskey()` — returns a `useMutation` so React Query handles invalidation:
       ```ts
       export function useRegisterPasskey() {
         const qc = useQueryClient();
         return useMutation({
           mutationFn: async (deviceName: string) => {
             const begin = await webauthnApi.registerBegin();
             const credential = await startRegistration({ optionsJSON: begin.options });
             return webauthnApi.registerFinish({ handle: begin.handle, device_name: deviceName, credential });
           },
           onSuccess: () => qc.invalidateQueries({ queryKey: passkeyKeys.lists() }),
         });
       }
       ```
     - `useRevokePasskey()` — same pattern wrapping `webauthnApi.revokePasskey(id)`.
  3. Add a `setAuthState(response: LoginResponse)` method to `AuthProvider` that consolidates `setAccessToken + setUser + scheduleTokenRefresh` (refactor of the inline logic at `AuthProvider.tsx:167-175`).
- **PATTERN**: `AuthProvider.tsx:167-197`; `.kiro/steering/frontend-patterns.md:75-91` for key factory + mutation invalidation.
- **IMPORTS**: `import { useMutation, useQueryClient } from '@tanstack/react-query'; import { startAuthentication, startRegistration } from '@simplewebauthn/browser'; import { passkeyKeys } from '../api/keys';`.
- **GOTCHA**: `startAuthentication`/`startRegistration` throw `NotAllowedError` if the user cancels — catch and rethrow as a friendly error so the toast shows "Sign-in cancelled" not raw browser text.
- **VALIDATE**: `cd frontend && npm run typecheck`.

### Task 17 — UPDATE `frontend/src/features/auth/components/AuthProvider.tsx`

- **IMPLEMENT**: Refactor `login()` body into a private `applyLoginResponse(response: LoginResponse)` function; expose it via `setAuthState` on the context; add `loginWithPasskey: (username?: string) => Promise<void>` to `AuthContextValue`.
- **PATTERN**: existing `login` callback at `AuthProvider.tsx:167-175`.
- **IMPORTS**: covered.
- **GOTCHA**: Don't break the existing `useAuth().login()` API — keep its signature identical. Just refactor the body.
- **VALIDATE**: `cd frontend && npm run typecheck && cd frontend && npm test -- AuthProvider.test`.

### Task 18 — UPDATE `frontend/src/features/auth/components/LoginPage.tsx`

- **IMPLEMENT**: Surgical additions:
  1. Add `autoComplete="username webauthn"` to the username `<Input>` at `LoginPage.tsx:117-127`. This enables the OS to surface passkeys in the autofill dropdown (the **conditional UI**).
  2. Below the password "Sign In" button (around line 193), add a horizontal divider with "or" text, then a secondary biometric button **with explicit `data-testid`**:
     ```tsx
     <Button
       type="button"
       variant="outline"
       className="w-full"
       onClick={handlePasskeyLogin}
       data-testid="passkey-login-btn"
     >
       <Fingerprint className="h-4 w-4 mr-2" /> Sign in with biometrics
     </Button>
     ```
  3. Add an inline error block tied to the biometric flow only — distinct from the existing password error block — with `data-testid="passkey-error"`. Don't reuse the password `error` state; biometric errors should be silenceable when the user simply cancels.
  4. `handlePasskeyLogin = async () => { try { await loginWithPasskey(username || undefined); navigate(from); } catch (e) { if (e instanceof Error && e.name === 'NotAllowedError') return; setPasskeyError('Biometric sign-in failed. Try again or use your password.'); } }`.
  5. **Conditional UI / autofill**: on mount, call `startAuthentication({ optionsJSON, useBrowserAutofill: true })` — this lets the OS surface the passkey directly in the username field's autofill chip without requiring the button. Wrap in a `useEffect` that bails if the browser doesn't support it (`browserSupportsWebAuthnAutofill()` from the lib).
- **PATTERN**: existing form + button structure at `LoginPage.tsx:88-193`. `data-testid` convention from `.kiro/steering/frontend-patterns.md:97-98`.
- **IMPORTS**: `import { Fingerprint } from 'lucide-react'; import { browserSupportsWebAuthnAutofill, startAuthentication } from '@simplewebauthn/browser'; import { useLoginWithPasskey } from '../hooks/usePasskeyAuth';`.
- **GOTCHA**:
  - `useBrowserAutofill: true` rejects when the user cancels the autofill — don't show an error for that case (silent abort is fine; the user can still type a password).
  - Don't break existing tests — preserve all existing `data-testid` attributes verbatim.
- **VALIDATE**: `cd frontend && npm run typecheck && cd frontend && npm run dev` then load `/login` in Safari/Chrome on a Mac with Touch ID enrolled — autofill chip should appear; new button has `[data-testid="passkey-login-btn"]`.

### Task 19 — CREATE `frontend/src/features/auth/components/PasskeyManager.tsx`

- **IMPLEMENT**: A self-contained component following `.kiro/steering/frontend-patterns.md` patterns:
  - **List**: `useQuery({ queryKey: passkeyKeys.list(), queryFn: webauthnApi.listPasskeys })`. Render `<LoadingSpinner data-testid="passkey-loading-spinner" />` while loading; `<Alert variant="destructive">` on error; empty-state `<div data-testid="passkey-empty-state">` when zero rows.
  - **Table**: render rows in a `<DataTable>` (or simple table if no shared component exists). Container has `data-testid="passkey-table"`; each row `data-testid="passkey-row"`. Columns: device name, type label (`single_device` → "This device only", `multi_device` → "Syncs across devices"), created date, last-used date, action.
  - **Add button**: `<Button data-testid="add-passkey-btn">` opens a `<Dialog>` with `data-testid="passkey-form"`.
  - **Add form**: React Hook Form + Zod (per `frontend-patterns.md:31-70`):
    ```tsx
    const schema = z.object({ device_name: z.string().min(1, 'Required').max(100, 'Max 100 chars') });
    const form = useForm({ resolver: zodResolver(schema), defaultValues: { device_name: '' } });
    const register = useRegisterPasskey();
    const onSubmit = async ({ device_name }) => {
      try { await register.mutateAsync(device_name); toast.success('Passkey added'); closeDialog(); }
      catch (e) { if (e?.name === 'NotAllowedError') return; toast.error('Failed: ' + (e?.message ?? 'unknown')); }
    };
    ```
    Wrap fields in `<Form>` / `<FormField>` / `<FormItem>` / `<FormLabel>` / `<FormControl>` / `<FormMessage>`. Submit button gets `data-testid="submit-passkey-btn"`.
  - **Revoke**: each row has `<Button data-testid="revoke-passkey-btn" variant="destructive" size="sm" onClick={() => setConfirmingId(passkey.id)}>`. Use `useRevokePasskey()` mutation; invalidate list on success; `toast.success('Passkey removed')`.
  - **Confirmation dialog before revoke** — passkey loss is destructive. Use the existing **shadcn `<Dialog>`** (already installed at `frontend/src/components/ui/dialog.tsx`) with destructive footer buttons. **Do not use `<AlertDialog>` — it is not currently installed in `frontend/src/components/ui/` (verified at planning time; `npx shadcn add alert-dialog` would be needed, but `<Dialog>` is functionally equivalent for this use case).** Confirmation copy: "Remove this passkey? You'll need to re-enroll on this device to use biometric sign-in again."
- **PATTERN**: `.kiro/steering/frontend-patterns.md:14-69` (List + Form patterns); `.kiro/steering/frontend-testing.md` for the test wrapper. Reference the existing **change-password dialog** at `frontend/src/pages/Settings.tsx:359-406` for the exact `<Dialog>` + `<DialogHeader>` + `<DialogFooter>` shape used elsewhere in this codebase.
- **IMPORTS**:
  ```tsx
  import { useQuery } from '@tanstack/react-query';
  import { useForm } from 'react-hook-form';
  import { zodResolver } from '@hookform/resolvers/zod';
  import { z } from 'zod';
  import { toast } from 'sonner';
  import { Button } from '@/components/ui/button';
  import { Form, FormField, FormItem, FormLabel, FormControl, FormMessage } from '@/components/ui/form';
  import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
  import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
  import { webauthnApi } from '../api/webauthn';
  import { passkeyKeys } from '../api/keys';
  import { useRegisterPasskey, useRevokePasskey } from '../hooks/usePasskeyAuth';
  import type { Passkey } from '../types/webauthn';
  ```
- **GOTCHA**:
  - Don't expose the credential's UUID in URLs — it's only an internal identifier. The `id` field on `Passkey` is fine to use as a React `key`.
  - Confirm `@hookform/resolvers/zod` is in `frontend/package.json` (verified — line 27).
  - **`AlertDialog` is NOT installed** (verified via `ls frontend/src/components/ui/` at planning time — only `dialog.tsx`, not `alert-dialog.tsx`). Use the regular `<Dialog>` component for the revoke confirmation. If a future task needs the AlertDialog component, run `npx shadcn add alert-dialog` separately.
  - There is no `<DataTable>` shared component for simple cases — render a plain `<Card>` containing a semantic `<table>` (or a list of `<div>` rows) with the same `data-testid`s. Mirror the visual style of existing settings cards (e.g. `Settings.tsx:155-207` "Notification Preferences" card) for consistency.
- **VALIDATE**: `cd frontend && npm run typecheck && cd frontend && npm test -- PasskeyManager.test`.

### Task 20 — Wire `PasskeyManager` into the existing settings page

- **PRE-VERIFIED FACT**: The settings page is `frontend/src/pages/Settings.tsx` (function `SettingsPage`). It already has an "Account Actions" Card (lines 306-356) with "Change Password" and "Sign Out", and a Change Password Dialog (lines 359-406). The page exports through `frontend/src/features/settings/index.ts`.
- **IMPLEMENT**: Add an import `import { PasskeyManager } from '@/features/auth';` (export it from `frontend/src/features/auth/index.ts` first — also add `webauthnApi` and the hooks to that public index).

  Insert `<PasskeyManager />` as a new section **immediately before** the "Account Actions" Card (currently `Settings.tsx:307`). That puts it logically inside the security/account-management area, right next to "Change Password". Pass no props — it's self-contained.

  The component itself wraps in a `<Card data-testid="security-page" ...>` with a header reading "Sign-in & Security" so it visually matches the existing Cards.

- **PATTERN**: insertion mirrors how `<BusinessInfo />`, `<InvoiceDefaults />`, `<NotificationPrefs />`, `<EstimateDefaults />`, `<BusinessSettingsPanel />` are slotted at `Settings.tsx:246-258` — each is a self-contained Card component used as a JSX child of `SettingsPage`.
- **IMPORTS**: `import { PasskeyManager } from '@/features/auth';` near the existing `import { useAuth } from "@/features/auth";` at `Settings.tsx:10`.
- **GOTCHA**:
  - **Don't** create a new route (`/settings/security`) — the existing `/settings` page is fine. Avoid splitting settings across routes.
  - Update `frontend/src/features/auth/index.ts` to export `PasskeyManager`. If `index.ts` exists with named exports, add the line; if it's empty, add `export { PasskeyManager } from './components/PasskeyManager';`.
- **VALIDATE**: `cd frontend && npm run dev` — load `/settings`, confirm the new "Sign-in & Security" Card appears between "Integration Settings" and "Account Actions".

### Task 21 — CREATE `src/grins_platform/tests/unit/test_webauthn_service.py`

- **IMPLEMENT**: Mock-based unit tests covering:
  - `start_registration` — generates options, stashes challenge in Redis, returns handle.
  - `finish_registration` — happy path persists credential; invalid challenge raises `WebAuthnChallengeNotFoundError`; library `InvalidRegistrationResponse` raises `WebAuthnVerificationError`; Redis key is deleted on success AND failure.
  - `start_authentication` — username path populates `allow_credentials`; None path doesn't.
  - `finish_authentication` — happy path returns 4-tuple; sign_count regression raises and revokes; locked staff raises `AccountLockedError`; disabled staff raises `InvalidCredentialsError`.
  - `revoke_credential` — happy path; not-found raises.
- **PATTERN**: `tests/unit/test_auth_service.py:1-120`.
- **IMPORTS**:
  ```python
  from unittest.mock import AsyncMock, MagicMock, patch
  import pytest
  from grins_platform.services.webauthn_service import WebAuthnService
  ```
- **GOTCHA**: Mock `webauthn.generate_registration_options` and `webauthn.verify_registration_response` directly with `@patch("grins_platform.services.webauthn_service.generate_registration_options", ...)`. Don't try to hand-craft real credentials in unit tests.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_webauthn_service.py -v` — all green.

### Task 22 — CREATE `src/grins_platform/tests/unit/test_webauthn_api.py`

- **IMPLEMENT**: API-level tests using `app.dependency_overrides` to inject a mock `WebAuthnService`. Cover:
  - All 6 endpoints' happy paths.
  - 401 on protected endpoints when not logged in.
  - 400 when challenge handle is missing.
  - **Crucial**: the cookies set by `/authenticate/finish` exactly match `/auth/login`'s cookie set (compare cookie names, `httponly`, `secure`, `samesite`, `max_age`).
- **PATTERN**: `tests/test_auth_api.py:1-100` (fixtures + `httpx.AsyncClient(transport=ASGITransport(app=app))`).
- **IMPORTS**: covered.
- **GOTCHA**: Use `app.dependency_overrides[get_webauthn_service] = lambda: mock_service` and **clear it in a fixture teardown**, or tests will pollute each other.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_webauthn_api.py -v`.

### Task 23 — CREATE `src/grins_platform/tests/integration/test_webauthn_integration.py`

- **IMPLEMENT**: HTTP **wiring** integration test with cryptographic verification mocked. This test's purpose is to verify the **wiring** (router → service → repo → cookies → DB), not to re-verify ECDSA — the `webauthn` library's own test suite covers the crypto. The one critical wiring assertion: post-`/authenticate/finish` cookies match `/auth/login`'s cookie set byte-for-byte.

  Concrete recipe (mocked-crypto integration):
  ```python
  from unittest.mock import patch
  from webauthn.helpers.structs import VerifiedRegistration, VerifiedAuthentication, AttestationFormat, PublicKeyCredentialType, CredentialDeviceType
  from httpx import ASGITransport, AsyncClient
  from grins_platform.main import app

  @pytest.mark.integration
  async def test_register_then_authenticate_full_round_trip(...):
      # 1. Override get_db_session and get_auth_service for isolated test DB
      # 2. Mock verify_registration_response → returns a VerifiedRegistration with deterministic credential_id, public_key, sign_count=0, etc.
      # 3. Mock verify_authentication_response → returns VerifiedAuthentication with new_sign_count=1, matching credential_id
      # 4. POST /api/v1/auth/login (password) → get session cookies
      # 5. POST /api/v1/auth/webauthn/register/begin → assert returns {handle, options}
      # 6. POST /api/v1/auth/webauthn/register/finish with the handle + canned credential dict → assert 200 and Passkey row exists in DB
      # 7. POST /api/v1/auth/webauthn/authenticate/begin → assert returns {handle, options}
      # 8. POST /api/v1/auth/webauthn/authenticate/finish with handle + canned credential → assert returns LoginResponse
      # 9. Assert cookies set: refresh_token (HttpOnly), access_token (HttpOnly), csrf_token (not HttpOnly), all with same flags as /auth/login (compare against a baseline /auth/login response captured in step 4)
  ```
  Sample: copy the cookie-comparison baseline from `tests/test_auth_api.py` (the existing password-login test already asserts these cookie flags).

  **Skipped (left for manual Task 29)**: the actual ECDSA round-trip with a real authenticator. That's manual + done by Apple/Google's OS, not by us. We don't re-test the library.

- **PATTERN**: `tests/integration/test_auth_integration.py:1-80` for fixtures + `httpx.AsyncClient(transport=ASGITransport(app=app))` setup.
- **IMPORTS**:
  ```python
  from unittest.mock import patch, AsyncMock
  from webauthn.helpers.structs import VerifiedRegistration, VerifiedAuthentication
  from httpx import ASGITransport, AsyncClient
  ```
- **GOTCHA**:
  - Use `@patch("grins_platform.services.webauthn_service.verify_registration_response", return_value=VerifiedRegistration(...))` — the patch target must be the **import location** in `webauthn_service.py`, not the original library module.
  - The mocked `VerifiedRegistration` needs realistic-looking values for every field your service reads: `credential_id`, `credential_public_key`, `sign_count`, `aaguid`, `credential_device_type`, `credential_backed_up`. Fill with deterministic test bytes.
  - The "canned credential dict" passed to `register/finish` and `authenticate/finish` only needs the shape that `parse_*_credential_json` accepts — any browser-shaped JSON works since verification is mocked.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/integration/test_webauthn_integration.py -v`. The test must run in CI with no skips.

### Task 24 — CREATE frontend tests

- **IMPLEMENT**:
  - `frontend/src/features/auth/components/PasskeyManager.test.tsx` — wrapped in `QueryProvider` (from `@/core/providers/QueryProvider`) per `.kiro/steering/frontend-testing.md:11-25`. Tests:
    - Renders loading state (`getByTestId('passkey-loading-spinner')`).
    - Renders empty state when API returns `[]` (`getByTestId('passkey-empty-state')`).
    - Renders rows when API returns 2 passkeys (`getAllByTestId('passkey-row')` length 2).
    - Click `add-passkey-btn` → opens dialog (`getByTestId('passkey-form')`) → submitting empty name shows validation error `'Required'` (RHF + Zod) → submitting valid name calls `webauthnApi.registerFinish` and shows `toast.success`.
    - Click `revoke-passkey-btn` → opens AlertDialog → confirm → calls `webauthnApi.revokePasskey(id)` → query invalidated → list re-renders without that row.
  - `frontend/src/features/auth/components/LoginPage.test.tsx` — extend existing test:
    - `passkey-login-btn` is rendered.
    - Clicking it calls `loginWithPasskey` (mock the hook).
    - Cancel error (`NotAllowedError`) does NOT show `passkey-error` block.
    - Other errors DO show it.
  - `frontend/src/features/auth/hooks/usePasskeyAuth.test.tsx` — hook tests using `renderHook` per `frontend-testing.md:38-41`.
- **PATTERN**: `frontend/src/features/auth/components/AuthProvider.test.tsx`, `LoginPage.test.tsx`. `.kiro/steering/frontend-testing.md`.
- **IMPORTS**: `@testing-library/react`, `@testing-library/user-event`, `vitest`, mocks for `@simplewebauthn/browser` and `webauthnApi`. `QueryProvider` from `@/core/providers/QueryProvider`.
- **GOTCHA**:
  - Mock `startAuthentication` / `startRegistration` to return canned credentials. Don't try to use a real `navigator.credentials` in jsdom (it's not available).
  - Use `await user.click(...)` (from `userEvent.setup()`) — synchronous `fireEvent` doesn't trigger `react-hook-form` validation properly.
  - Coverage targets per `.kiro/steering/spec-quality-gates.md`: components 80%+, hooks 85%+, utils 90%+.
- **VALIDATE**: `cd frontend && npm test -- PasskeyManager.test LoginPage.test usePasskeyAuth.test && cd frontend && npm run test:coverage -- src/features/auth`.

### Task 25 — Run full backend quality suite

- **IMPLEMENT**: n/a — pure validation step.
- **PATTERN**: `.kiro/steering/code-standards.md:69-76`.
- **VALIDATE**:
  ```bash
  uv run ruff check src/
  uv run ruff format --check src/
  uv run mypy src/
  uv run pyright src/
  uv run pytest -m unit -v
  uv run pytest -m functional -v
  uv run pytest -m integration -v
  ```
  All must pass with zero errors. Address any new warnings introduced by this feature; pre-existing warnings can stay.

### Task 26 — CREATE Hypothesis property-based tests (`src/grins_platform/tests/test_webauthn_property.py`)

- **PRE-VERIFIED PATTERN** — from `src/grins_platform/tests/test_auth_property.py:1-95`:
  ```python
  import pytest
  from hypothesis import given, settings, strategies as st

  @pytest.mark.unit
  class TestPasswordHashingProperty:
      @given(password=st.text(min_size=8, max_size=50, alphabet=st.sampled_from("abc...")))
      @settings(max_examples=50, deadline=10000)
      def test_hash_then_verify_returns_true(self, password: str) -> None:
          ...
  ```
  Use class-based grouping, `@pytest.mark.unit` at class level, `@given` + `@settings(max_examples=N, deadline=N_ms)` at method level.

- **IMPLEMENT**: Property-based tests required by `.kiro/steering/spec-testing-standards.md` and `spec-quality-gates.md` for "business logic with invariants":

  1. **`TestBase64UrlRoundTrip`** — For any `bytes` payload, `base64url_to_bytes(bytes_to_base64url(b)) == b`.
     ```python
     @given(payload=st.binary(min_size=0, max_size=1024))
     @settings(max_examples=200)
     def test_base64url_roundtrip(self, payload: bytes) -> None:
         from webauthn.helpers import bytes_to_base64url, base64url_to_bytes
         assert base64url_to_bytes(bytes_to_base64url(payload)) == payload
     ```
  2. **`TestSignCountRegressionGate`** — For any `(stored, new)` integer pair, the `_is_sign_count_regression(stored, new)` helper returns True iff `new > 0 and new <= stored`. This **requires extracting the inline check from `WebAuthnService.finish_authentication` into a module-level pure function** (Task 9 already mentioned this; Task 26 verifies via property test).
     ```python
     @given(stored=st.integers(min_value=0, max_value=2**32), new=st.integers(min_value=0, max_value=2**32))
     def test_sign_count_regression_gate(self, stored: int, new: int) -> None:
         from grins_platform.services.webauthn_service import _is_sign_count_regression
         expected = new > 0 and new <= stored
         assert _is_sign_count_regression(stored, new) is expected
     ```
  3. **`TestUserHandleStability`** — `get_or_create_for_staff(staff_id)` returns the same bytes across repeated calls for the same `staff_id` (`@pytest.mark.functional` — needs DB).
  4. **`TestCredentialIdUniqueness`** — For any N random `credential_id` byte sequences, inserting two with the same value raises `IntegrityError` mapped to `WebAuthnDuplicateCredentialError` (`@pytest.mark.functional`).
  5. **`TestChallengeHandleUniqueness`** — 1000 calls to the handle generator (`secrets.token_urlsafe(32)`) return 1000 distinct values. Trivial but documents the assumption.

- **PATTERN**: `src/grins_platform/tests/test_auth_property.py` (verbatim — read first).
- **IMPORTS**: `from hypothesis import given, settings, strategies as st; import pytest`.
- **GOTCHA**:
  - The `_is_sign_count_regression` helper is a tiny pure-function refactor. Define it as a module-level `def _is_sign_count_regression(stored: int, new: int) -> bool: return new > 0 and new <= stored` in `webauthn_service.py`; the service method calls this and raises if True.
  - File-level marker: `pytestmark = pytest.mark.unit` is fine for the first two and the fifth class. Use per-class `@pytest.mark.functional` for the DB-touching classes (3 and 4).
  - `@settings(deadline=...)` is in milliseconds. Set ≥10000 ms for tests that touch the DB.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/test_webauthn_property.py -v --hypothesis-show-statistics` — all examples pass; statistics show actual examples ≥ 50 per property.

### Task 27 — CREATE functional tests (`src/grins_platform/tests/functional/test_webauthn_functional.py`)

- **IMPLEMENT**: `@pytest.mark.functional` tests against a real Postgres test DB:
  - Repository CRUD: create credential → find by `credential_id` → update sign count → revoke → find returns None.
  - User handle: `get_or_create_for_staff` creates on first call, returns same bytes on second call.
  - FK cascade: deleting a `Staff` cascades-deletes their credentials.
  - Unique constraint: inserting two credentials with the same `credential_id` raises `IntegrityError`, mapped by repo to `WebAuthnDuplicateCredentialError`.
- **PATTERN**: any existing `tests/functional/test_*.py` (e.g. `test_appointment_notes_functional.py`).
- **IMPORTS**: standard async fixtures from `tests/conftest.py`.
- **GOTCHA**: Functional tests need a real DB — make sure CI has `DATABASE_URL` set and migrations applied before this test runs.
- **VALIDATE**: `uv run pytest -m functional src/grins_platform/tests/functional/test_webauthn_functional.py -v`.

### Task 28 — CREATE agent-browser E2E validation script (`e2e/test-webauthn-passkey.sh`)

- **IMPLEMENT**: Bash script per `.kiro/steering/e2e-testing-skill.md` and `spec-quality-gates.md` (mandatory). The script validates the **non-biometric** UI surfaces (the OS biometric prompt cannot be driven by Playwright/Chromium); manual Task 30 covers the biometric round-trip itself.
  ```bash
  #!/usr/bin/env bash
  set -euo pipefail
  BASE="${BASE:-http://localhost:5173}"
  mkdir -p e2e-screenshots/webauthn

  # Pre-flight
  agent-browser --version > /dev/null || { echo "agent-browser not installed"; exit 1; }

  # Phase 1: Login page renders biometric button
  agent-browser open "$BASE/login"
  agent-browser wait --load networkidle
  agent-browser is visible "[data-testid='login-page']"
  agent-browser is visible "[data-testid='passkey-login-btn']"
  agent-browser screenshot e2e-screenshots/webauthn/01-login-with-passkey-btn.png

  # Phase 2: Password login (precondition for settings access)
  agent-browser fill "[data-testid='username-input']" "$E2E_USER"
  agent-browser fill "[data-testid='password-input']" "$E2E_PASS"
  agent-browser click "[data-testid='login-btn']"
  agent-browser wait --url "**/dashboard*"

  # Phase 3: Navigate to security settings
  agent-browser open "$BASE/settings/security"
  agent-browser wait --load networkidle
  agent-browser is visible "[data-testid='security-page']"
  agent-browser is visible "[data-testid='passkey-table']"
  agent-browser screenshot e2e-screenshots/webauthn/02-security-page.png

  # Phase 4: Add Passkey dialog opens (cancel before biometric prompt — that's the manual part)
  agent-browser click "[data-testid='add-passkey-btn']"
  agent-browser wait "[data-testid='passkey-form']"
  agent-browser is visible "[data-testid='device-name-input']"
  agent-browser screenshot e2e-screenshots/webauthn/03-add-passkey-dialog.png

  # Phase 5: Validation error when device_name is empty
  agent-browser click "[data-testid='submit-passkey-btn']"
  agent-browser wait --text "Required"
  agent-browser screenshot e2e-screenshots/webauthn/04-validation-error.png

  # Phase 6: Console + errors snapshot for any silent JS issues
  agent-browser console > e2e-screenshots/webauthn/console.log
  agent-browser errors > e2e-screenshots/webauthn/errors.log
  test ! -s e2e-screenshots/webauthn/errors.log || { echo "JS errors detected"; cat e2e-screenshots/webauthn/errors.log; exit 1; }

  agent-browser close
  echo "agent-browser E2E passed for webauthn UI surfaces."
  ```
- **PATTERN**: `.kiro/steering/e2e-testing-skill.md`; `.kiro/steering/agent-browser.md` for the command reference.
- **IMPORTS**: n/a (shell).
- **GOTCHA**:
  - `E2E_USER` / `E2E_PASS` must be set in the env or read from a `.env.test` (don't hard-code).
  - `chmod +x e2e/test-webauthn-passkey.sh` after creating.
  - Keep the script under 100 lines — it's a smoke test, not a full regression suite.
  - The script CANNOT validate the actual biometric ceremony — the OS prompt is outside the browser. That's why Task 30 (manual) exists.
- **VALIDATE**: With dev servers running (`uvicorn` on :8000 and `vite dev` on :5173), run `E2E_USER=admin E2E_PASS='...' bash e2e/test-webauthn-passkey.sh` — exits 0 with all 6 screenshots saved.

### Task 29 — Manual end-to-end smoke test on real hardware

- **IMPLEMENT**: Booth-test on a Mac with Touch ID and an iPhone with Face ID:
  1. Start backend (`uv run uvicorn grins_platform.main:app --host 0.0.0.0 --port 8000`).
  2. Start frontend (`cd frontend && npm run dev`).
  3. Log in with username/password as a test admin user.
  4. Navigate to Settings → Security → Add Passkey → name it "MacBook Touch ID" → tap Touch ID when prompted.
  5. Log out. On `/login`, click "Sign in with biometrics" → tap Touch ID → land on dashboard.
  6. From iPhone Safari, hit the same dev URL (use `ngrok` or LAN IP). Log in with password. Add another passkey "iPhone Face ID". Log out. Sign in with Face ID.
  7. Confirm both passkeys are listed in Settings; revoke one; confirm it can no longer authenticate.
- **PATTERN**: n/a — manual.
- **GOTCHA**:
  - For LAN IP / ngrok, set `WEBAUTHN_RP_ID` and `WEBAUTHN_EXPECTED_ORIGINS` to match the actual hostname the browser sees. Don't try to test passkeys against `192.168.x.x` — browsers reject IPs as RP IDs. Use `ngrok` (gives you a real domain) or `localhost` only.
  - On Safari iOS, "save passkey to iCloud Keychain" is the default — that's the synced (multi_device) behavior. Confirm the passkey appears on the Mac's Keychain too within ~30 seconds.
- **VALIDATE**: All seven manual steps succeed. Take screenshots and attach to the PR.

### Task 30 — Update `DEVLOG.md` with a SECURITY entry

- **IMPLEMENT**: Per `.kiro/steering/devlog-rules.md` and `auto-devlog.md`, prepend a new entry **at the top of `DEVLOG.md`**, immediately after the `## Recent Activity` header. Format:
  ```markdown
  ## [2026-04-25 HH:MM] - SECURITY: Add WebAuthn / Passkey authentication

  ### What Was Accomplished
  - Implemented WebAuthn passkey login alongside username/password.
  - Touch ID on macOS, Face ID on iOS, Windows Hello, Android — all via the W3C standard.
  - 6 new endpoints under `/api/v1/auth/webauthn/*`; same JWT cookie issuance as `/auth/login` so the rest of the app is method-agnostic.
  - New `PasskeyManager` UI in Settings → Security; passkey button + conditional autofill on `/login`.

  ### Technical Details
  - Backend: `webauthn>=2.7.0,<3.0.0` (py_webauthn / duo-labs). Two new tables: `webauthn_credentials`, `webauthn_user_handles`. Challenges live in Redis with 5-min TTL.
  - Frontend: `@simplewebauthn/browser@^13.3.0`. TanStack Query key factory (`passkeyKeys`); React Hook Form + Zod for the device-name form; sonner toasts.
  - Security: phishing-resistant by W3C origin binding; sign-count regression auto-revokes the offending credential; IDOR-safe revocation (filtered by `staff_id`).
  - Tests: unit (service + API + model), property-based (Hypothesis: base64url round-trip, sign-count gate, handle stability), functional (real-DB repo CRUD), integration (synthesized cryptographic ceremony — gated behind skip if too costly), agent-browser E2E (UI surfaces only).

  ### Decision Rationale
  - **Why platform-bound passkeys** (`AuthenticatorAttachment.PLATFORM`) — we want Touch ID / Face ID specifically, not USB security keys, for staff convenience. Cross-platform support is a future flag flip.
  - **Why allow synced passkeys** (iCloud Keychain / Google Password Manager) — the UX win of "enroll on iPhone, log in on MacBook" outweighs the "passkey security = iCloud security" trade-off for a workforce app.
  - **Why password remains the recovery path** — `email_service.py` is currently a stub, so building magic-link recovery on top of it would be premature.

  ### Challenges and Solutions
  - Synthesizing a real WebAuthn ceremony in integration tests is non-trivial (real cryptographic verification). Solved by adding Hypothesis property tests for the pure-function invariants and gating the full crypto round-trip behind `@pytest.mark.skip` if needed, with the manual hardware test (Task 30) as the safety net.
  - CSRF middleware potentially blocks pre-auth `/authenticate/begin` and `/authenticate/finish`. Solved by mirroring whatever exemption already covers `/auth/login`.

  ### Next Steps
  - Roll out to staff (admin first, then technicians).
  - Monitor `app.webauthn.*` log events for verification failures.
  - Consider step-up auth (re-prompt biometric for sensitive ops like refunds) — separate spec.
  - Consider customer-portal passkeys when repeat-visit customers become a use case — separate spec.
  ```
- **PATTERN**: `.kiro/steering/devlog-rules.md` (entry format); `DEVLOG.md` itself for existing tone.
- **IMPORTS**: n/a.
- **GOTCHA**: Newest entries at the **top** (per `devlog-rules.md:29-30`), immediately after the `## Recent Activity` header. Replace the placeholder timestamp with the actual completion time.
- **VALIDATE**: `head -50 DEVLOG.md | grep -i 'webauthn\|passkey'` — at least one match.

### Task 31 — Update `README.md` Authentication section

- **IMPLEMENT**: Append a "Biometric / Passkey Login" subsection under "Key Features → Authentication & Security" describing the new flow and the new env vars.
- **PATTERN**: existing README structure at lines 142-149.
- **GOTCHA**: Mention the dev origin requirement (`WEBAUTHN_EXPECTED_ORIGINS=http://localhost:5173`) explicitly so future developers don't trip on it.
- **VALIDATE**: `grep -i passkey README.md` — at least one match.

---

## TESTING STRATEGY

Follows `.kiro/steering/code-standards.md` (three-tier mandate), `spec-testing-standards.md`, and `spec-quality-gates.md`.

### Unit Tests (`@pytest.mark.unit`)

- `test_webauthn_service.py` — every public method, mocked Redis + repos + `webauthn` library.
- `test_webauthn_api.py` — every endpoint, mocked service via `app.dependency_overrides`, both auth and unauth paths.
- `test_webauthn_credential_model.py` — model defaults, enum constraints, FK cascade behavior with a stubbed session (mirror `test_auth_models.py`).

### Functional Tests (`@pytest.mark.functional`)

- `tests/functional/test_webauthn_functional.py` — repository CRUD against a real Postgres test DB; FK cascade; unique-constraint enforcement; user_handle stability.

### Integration Tests (`@pytest.mark.integration`)

- `tests/integration/test_webauthn_integration.py` — full register → auth round-trip with a synthesized authenticator. If full crypto round-trip is impractical, gate behind `@pytest.mark.skip` and rely on the manual test (Task 29).
- Key assertion: post-`/authenticate/finish` cookies match those set by `/auth/login` byte-for-byte (same names, flags, max-ages).

### Property-Based Tests (Hypothesis)

- `tests/test_webauthn_property.py` — 5 invariants: base64url round-trip, sign-count regression gate, credential_id uniqueness, user_handle stability, challenge-handle collision resistance. ≥100 examples per property.

### Frontend Tests (Vitest + React Testing Library)

- `PasskeyManager.test.tsx` — wrapped in `QueryProvider`. Loading / empty / list / add / validation-error / revoke flows.
- `LoginPage.test.tsx` (extended) — biometric button presence, click → calls hook, cancel-error suppression, other-error display.
- `usePasskeyAuth.test.tsx` — `renderHook` tests for the three hooks.

### agent-browser E2E (`e2e/test-webauthn-passkey.sh`)

- Validates UI surfaces only (cannot drive OS biometric prompt). 6 screenshots saved to `e2e-screenshots/webauthn/`.

### Coverage Targets — from `.kiro/steering/spec-quality-gates.md`

| Layer | Target |
|---|---|
| Backend services (`webauthn_service.py`) | **90%+** |
| Backend repositories (`webauthn_credential_repository.py`) | **90%+** |
| Backend API (`api/v1/webauthn.py`) | **90%+** |
| Backend utils | 90%+ |
| Frontend components (`PasskeyManager.tsx`) | **80%+** |
| Frontend hooks (`usePasskeyAuth.ts`) | **85%+** |

### Edge Cases (must be tested)

- Expired challenge (Redis TTL) → 400.
- Reused challenge (replay) → 400.
- Sign count regression (`new <= stored`, both > 0) → revoke + 401.
- Login attempted with a revoked credential → 401.
- Login attempted on an `is_login_enabled=False` staff → 401 (mirror password path).
- Login attempted on a locked-out staff (`locked_until > now`) → 401 with `AccountLockedError`.
- Registration attempted with a credential ID already in the DB → 409 `WebAuthnDuplicateCredentialError`.
- IDOR: user A tries to delete user B's credential → 404 (`revoke()` filters by `staff_id`).
- RP ID mismatch (origin doesn't match `WEBAUTHN_RP_ID`) → 401 from library; we surface 401.
- Empty `expected_origins_list` (misconfiguration) → service raises a clear error at startup; prefer fail-fast via `validate_jwt_config`-style hook in `app.py:lifespan`.

---

## VALIDATION COMMANDS

Execute every command to ensure zero regressions and 100% feature correctness.

### Level 1: Syntax & Style

```bash
uv run ruff check --fix src/
uv run ruff format src/
cd frontend && npm run lint && npm run format:check
```

### Level 2: Type Checking

```bash
uv run mypy src/
uv run pyright src/
cd frontend && npm run typecheck
```

### Level 3: Unit + Property-Based Tests

```bash
uv run pytest src/grins_platform/tests/unit/test_webauthn_service.py -v
uv run pytest src/grins_platform/tests/unit/test_webauthn_api.py -v
uv run pytest src/grins_platform/tests/unit/test_webauthn_credential_model.py -v
uv run pytest src/grins_platform/tests/test_webauthn_property.py -v --hypothesis-show-statistics
cd frontend && npm test -- PasskeyManager.test LoginPage.test AuthProvider.test usePasskeyAuth.test
```

### Level 4: Functional + Integration Tests

```bash
uv run pytest -m functional src/grins_platform/tests/functional/test_webauthn_functional.py -v
uv run pytest -m integration src/grins_platform/tests/integration/test_webauthn_integration.py -v
# Re-run the full auth integration suite to confirm no regression:
uv run pytest src/grins_platform/tests/integration/test_auth_integration.py -v
uv run pytest src/grins_platform/tests/test_auth_api.py -v
```

### Level 4b: agent-browser E2E (UI surfaces)

```bash
# Pre-flight: dev servers must be running (uvicorn :8000 + vite dev :5173)
E2E_USER=admin E2E_PASS='...' bash e2e/test-webauthn-passkey.sh
# Asserts no JS errors, all data-testids present, validation works.
```

### Level 5: Manual Validation (on real hardware)

1. **Mac (Touch ID)**: register a passkey from Settings → log out → log in via biometric button → confirm dashboard loads.
2. **iPhone (Face ID)**: same flow over ngrok or LAN with proper `WEBAUTHN_RP_ID` / origins.
3. **Conditional UI**: on `/login`, focus the username field — Touch ID / Face ID prompt appears in the autofill chip.
4. **Revocation**: delete a passkey from Settings → confirm subsequent biometric sign-in attempt with that device fails with a clean error.
5. **Multi-device**: confirm that after iCloud sync (~30 s), an iPhone-registered passkey works on the paired Mac.

### Level 6: Database integrity

```bash
uv run alembic upgrade head
uv run alembic downgrade -1
uv run alembic upgrade head
psql "$DATABASE_URL" -c "\d webauthn_credentials"
psql "$DATABASE_URL" -c "\d webauthn_user_handles"
```

---

## ACCEPTANCE CRITERIA

- [ ] Logged-in staff can register a passkey via Settings → Security, with a friendly device name.
- [ ] Multiple passkeys per staff are supported (one per device).
- [ ] On the login page, a "Sign in with biometrics" button triggers Touch ID on Mac and Face ID on iPhone.
- [ ] Conditional UI (autofill chip) surfaces the passkey when the username field is focused.
- [ ] After successful biometric authentication, the same JWT cookies (access, refresh, CSRF) are issued as on password login — frontend `AuthProvider` requires no special-casing per method.
- [ ] Disabled staff (`is_login_enabled=False`) and locked-out staff (`locked_until > now`) cannot bypass via passkey — same blocks as password login.
- [ ] Sign-count regression is detected and the offending credential is auto-revoked.
- [ ] Users can list and revoke their own passkeys; cannot list/revoke others' (IDOR-safe).
- [ ] All Ruff, MyPy, Pyright, ESLint, Prettier, TypeScript checks pass with zero new errors.
- [ ] Coverage targets met: services 90%+, repositories 90%+, API 90%+, frontend components 80%+, hooks 85%+ (per `.kiro/steering/spec-quality-gates.md`).
- [ ] No regression in the existing password login flow — `tests/test_auth_api.py` and `tests/integration/test_auth_integration.py` continue to pass.
- [ ] Migration round-trips cleanly (`upgrade head → downgrade -1 → upgrade head` succeeds).
- [ ] No biometric data, raw challenges, public keys, or credential IDs are written to logs.
- [ ] All `data-testid` attributes follow the convention map (in NOTES) so future tests can locate elements.
- [ ] agent-browser E2E script passes with no JS errors.
- [ ] DEVLOG.md has a `SECURITY` entry at the top describing this feature.
- [ ] README documents the feature and the new env vars.

---

## COMPLETION CHECKLIST

- [ ] All 31 tasks completed in order.
- [ ] Each task's `VALIDATE` command passed at the time it was completed.
- [ ] Full validation suite (Levels 1–4) re-run from a clean state — all green.
- [ ] Manual hardware test (Level 5) completed on at least one Mac and one iPhone, with screenshots attached to the PR.
- [ ] Migration applied cleanly to the dev database; downgrade verified.
- [ ] No new MyPy / Pyright errors anywhere in the repo.
- [ ] No new Ruff violations in the touched files.
- [ ] Frontend bundle size didn't grow by more than ~15 KB (the `@simplewebauthn/browser` lib is small).
- [ ] Acceptance criteria all checked off.
- [ ] PR description includes the manual test screenshots and a one-liner about the env vars.

---

## NOTES

### Design decisions & trade-offs

- **Synced (multi-device) passkeys are allowed**, not blocked. For a workforce app like this, the UX win of "enroll on iPhone, log in on MacBook" via iCloud Keychain is worth the trade-off that "passkey security = iCloud account security." Admin staff who want stricter control can be issued FIDO2 hardware keys later (the same code path supports `AuthenticatorAttachment.CROSS_PLATFORM` — just flip the flag). Document this trade-off in the README.
- **No magic-link / email recovery yet** — the project's email service is currently a stub (per memory: `email_service.py` defines send_* but `_send_email` only logs). Building recovery on top of a stub is premature. Password remains the recovery path; admins can also reset a staff member's `password_hash` in the DB if all devices are lost.
- **Customer portal is out of scope.** The estimate-approval portal has its own token-based auth (per memory: `/api/v1/portal/estimates/{token}` flow). Adding passkeys there is technically possible but doesn't help the once-per-estimate UX — magic-link is fine. Revisit if customers start asking for repeat-visit accounts.
- **Two tables, not one.** A separate `webauthn_user_handles` table keeps the `Staff` table clean and lets us drop the feature without altering staff. The user_handle is opaque per W3C spec — never reuse the staff ID for it.
- **Challenge state in Redis, not the DB.** Challenges are short-TTL (5 min), single-use, and high-throughput — exactly Redis's sweet spot. Adding a `webauthn_challenges` table would add a write-then-delete that we don't need.
- **Existing CSRF middleware.** Verify behavior on `POST /authenticate/begin` and `POST /authenticate/finish` — the user has no CSRF cookie pre-login, so these endpoints **must** be CSRF-exempt (mirror however the password `/auth/login` is exempted). If `/auth/login` has no exemption today and works, then it's likely the middleware only enforces on cookie-authenticated requests, in which case we're fine.

### Risks

**Risks resolved at planning time** (verified during research):

| Original concern | Resolution |
|---|---|
| Migration `down_revision` ID being volatile | Verified `20260426_100000` is current head via `uv run alembic heads`. Hard-coded in Task 5. |
| CSRF middleware exemption being unclear | Read `middleware/csrf.py` directly. Middleware exists with an `exempt_paths` set but is **not currently registered in `app.py`**. Task 10 specifies adding the two pre-auth endpoints to the default exempt list defensively. |
| Integration-test synthesized authenticator being too costly | Reframed Task 23 to test the **wiring** (router → service → repo → cookies → DB) with `verify_*_response` mocked. Real cryptographic verification stays in the library's own test suite + manual Task 29. CI runs without skips. |
| shadcn `<AlertDialog>` not installed | Verified — `frontend/src/components/ui/` has `dialog.tsx` but not `alert-dialog.tsx`. Task 19 uses the existing `<Dialog>` for revoke confirmation. |
| Settings page existence/location | Verified `frontend/src/pages/Settings.tsx` exists. Task 20 specifies exact insertion point (between line 304 and 307). |
| Existing CSRF middleware registration status | Verified `app.py:217-229` registers CORS, RequestSizeLimit, SecurityHeaders, rate-limit — no CSRFMiddleware. Frontend sends `X-CSRF-Token` header but no server-side enforcement today. Plan does not require fixing this; the new exempt-path additions are forward-compatible. |
| `LoggerMixin` import path discrepancy | Confirmed `from grins_platform.log_config import LoggerMixin` (NOT `grins_platform.logging`, despite some steering docs). Plan uses the actual path everywhere. |

**Remaining (non-blocking) risks**:

- **`py_webauthn` major version drift.** Pinned `>=2.7.0,<3.0.0`. If 3.x lands during implementation, re-validate the API surface (`verify_registration_response` kwargs especially). Mitigation: pin upper bound.
- **iOS Safari quirks.** Apple ships occasional subtle WebAuthn changes. Mitigation: re-run manual Task 29 within a week of each iOS major release.
- **Redis availability.** If Redis is down, registration and authentication both fail. Password login does NOT depend on Redis, so this is additive availability concern, not regression. Mitigation: document in runbook; consider an in-memory fallback for the challenge cache only if Redis outages become operationally painful.
- **Production RP ID rollout.** Wrong `WEBAUTHN_RP_ID` at registration permanently binds credentials to the wrong domain. Mitigation: startup log line `app.webauthn.config_resolved` (already in the logging events table) lets ops verify the value at boot.

### Future enhancements (NOT in this plan, do NOT implement)

- WebAuthn-backed step-up auth for sensitive operations (delete customer, refund payment).
- Cross-platform (USB security key) flow for admins.
- Magic-link recovery, once `email_service.py` becomes a real provider.
- Customer-portal passkey login for repeat-visit customers.
- Admin dashboard view of all staff passkeys (currently each user only sees their own).

### Structured Logging Events Table

Required by `.kiro/steering/spec-quality-gates.md` ("Design Document Must Include → Structured Logging Events"). Pattern: `{domain}.{component}.{action}_{state}` per `.kiro/steering/code-standards.md` and `tech.md:43-46`.

| Event Name | Level | Component | Context Fields |
|---|---|---|---|
| `auth.webauthn.start_registration_started` | INFO | service | `staff_id` |
| `auth.webauthn.start_registration_completed` | INFO | service | `staff_id`, `handle` (opaque), `existing_credential_count` |
| `auth.webauthn.finish_registration_started` | INFO | service | `staff_id`, `handle` |
| `auth.webauthn.finish_registration_completed` | INFO | service | `staff_id`, `credential_id` (base64url, public), `credential_device_type`, `aaguid` |
| `auth.webauthn.finish_registration_rejected` | WARNING | service | `staff_id`, `reason` (`invalid_challenge` / `verification_failed` / `duplicate_credential`) |
| `auth.webauthn.start_authentication_started` | INFO | service | `username_hint` (or `null`) |
| `auth.webauthn.start_authentication_completed` | INFO | service | `handle` (opaque), `allow_credentials_count` |
| `auth.webauthn.finish_authentication_started` | INFO | service | `handle` |
| `auth.webauthn.finish_authentication_completed` | INFO | service | `staff_id`, `credential_id` (b64url), `new_sign_count` |
| `auth.webauthn.finish_authentication_rejected` | WARNING | service | `reason` (`challenge_not_found` / `verification_failed` / `sign_count_regression` / `account_locked` / `login_disabled` / `revoked_credential`), `credential_id` (if known) |
| `auth.webauthn.sign_count_regression_detected` | ERROR | service | `credential_id`, `stored_count`, `received_count`, `staff_id` (auto-revoke triggered) |
| `auth.webauthn.revoke_started` | INFO | service | `credential_id`, `staff_id` |
| `auth.webauthn.revoke_completed` | INFO | service | `credential_id`, `staff_id` |
| `auth.webauthn.revoke_rejected` | WARNING | service | `credential_id`, `staff_id`, `reason` (`not_found` / `not_owned`) |
| `database.webauthn_credentials.create_started` | DEBUG | repo | `staff_id` |
| `database.webauthn_credentials.create_completed` | DEBUG | repo | `staff_id`, `credential_id` (b64url) |
| `database.webauthn_credentials.update_sign_count_completed` | DEBUG | repo | `credential_id`, `new_sign_count` |
| `database.webauthn_credentials.revoke_completed` | DEBUG | repo | `credential_id`, `revoked` (bool) |
| `app.webauthn.config_resolved` | INFO | startup | `rp_id`, `rp_name`, `expected_origins` (list — log on boot for ops visibility) |

**Never log**: raw challenge bytes, public_key bytes, credential_id raw bytes (only base64url-encoded). Per `.kiro/steering/code-standards.md:36`.

### Quality Gate Commands (consolidated)

Required by `.kiro/steering/spec-quality-gates.md` ("Design Document Must Include → Quality Gate Commands"). Run from repo root:

```bash
# Backend
uv run ruff check --fix src/
uv run ruff format src/
uv run mypy src/
uv run pyright src/
uv run pytest -m unit -v
uv run pytest -m functional -v
uv run pytest -m integration -v
uv run pytest src/grins_platform/tests/test_webauthn_property.py --hypothesis-show-statistics

# Frontend
(cd frontend && npm run lint && npm run format:check && npm run typecheck && npm test && npm run test:coverage)

# Migration round-trip
uv run alembic upgrade head && uv run alembic downgrade -1 && uv run alembic upgrade head

# E2E (requires running dev servers)
E2E_USER=admin E2E_PASS='...' bash e2e/test-webauthn-passkey.sh
```

All must exit zero. Per `.kiro/steering/tech.md:27-30`: "all must pass with zero errors."

### Confidence

**Confidence score: 10/10** for one-pass implementation success.

All four risks flagged in earlier drafts have been resolved by direct codebase verification at planning time (see "Risks resolved at planning time" table above):

1. **Migration head** is hard-coded (`down_revision = "20260426_100000"`).
2. **CSRF middleware** is read; the middleware isn't even registered today, but Task 10 still adds the two pre-auth paths to the default `exempt_paths` defensively.
3. **Integration test crypto round-trip** is reframed as wiring-only with `verify_*_response` mocked — runs in CI with no skips. Real cryptographic verification is the library's responsibility plus the manual Task 29 hardware test.
4. **shadcn `<AlertDialog>` absence** is resolved by using the already-installed `<Dialog>` for the revoke confirmation. `<Form>` is present.

Plus three secondary verifications that close potential surprises:
- Settings page (`frontend/src/pages/Settings.tsx`) exists with a clear insertion point (between lines 304 and 307).
- `test_auth_property.py` exists with a copyable Hypothesis pattern (class-based, `@pytest.mark.unit`, `@settings(max_examples=N, deadline=N_ms)`) — Task 26 mirrors it verbatim.
- `LoggerMixin` import path (`grins_platform.log_config`) is confirmed; the steering doc's stale `grins_platform.logging` path is flagged so the executor doesn't follow the wrong breadcrumb.

The remaining risks (py_webauthn 3.x drift, iOS Safari point-release quirks, Redis availability, prod RP-ID rollout) are operational concerns that can't be resolved at code-write time and are documented for the runbook — they don't block one-pass implementation.
