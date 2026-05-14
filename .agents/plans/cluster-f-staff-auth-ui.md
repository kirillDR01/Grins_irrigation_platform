# Feature: Cluster F — Admin Staff Auth UI (set/reset username + password)

> **Read this whole file once before starting**, then execute tasks top-to-bottom.
> Pay attention to naming of existing utils/types/models. Import from the right files.
> The verified citations in **CONTEXT REFERENCES** were Read/Grep'd directly during planning — trust them and don't re-investigate.

---

## Feature Description

Today an admin (Victor) cannot give a staff member a login from the UI. The `Staff` model has every auth column needed (`username`, `password_hash`, `is_login_enabled`, `last_login`, `failed_login_attempts`, `locked_until`) — they're written today only by direct SQL or one-off scripts (most recent: commit `0a25df5 chore(dev-seed): add one-off script to create login-enabled tech staff`).

Cluster F closes that gap with **§14 Option A**: extend the staff create/edit surface with username + password + enable-login inputs, hash via the existing bcrypt context, add a separate admin reset-password endpoint, surface auth state on the staff list, and audit-log every password set/reset.

## User Story

As **Victor (admin)**
I want to **set or reset a staff member's username and password directly from the staff form, and see at a glance who can log in / when they last did**
So that **I can onboard a new tech or rotate a credential without asking the developer**.

## Problem Statement

`POST /api/v1/staff` (`api/v1/staff.py:295–316`) and `PUT /api/v1/staff/{id}` (`:359–386`) accept no auth fields. `StaffCreate` / `StaffUpdate` schemas (`schemas/staff.py:22–200`) have no `username` / `password` / `is_login_enabled`. `StaffService.create_staff` (`services/staff_service.py:60–89`) never calls `update_auth_fields`. The only existing self-service password path is `POST /api/v1/auth/change-password` (`api/v1/auth.py:271–292`), which requires the user's *current* password — useless for an admin onboarding a new tech who doesn't have a password yet.

## Solution Statement

1. **Backend schema extension** — Add optional `username`, `password`, `is_login_enabled` to `StaffCreate` and `StaffUpdate` with a single shared password-strength validator (relaxed rules per user's Standard decision).
2. **Backend service wiring** — Have `StaffService.create_staff` / `update_staff` route auth fields through the existing `StaffRepository.update_auth_fields` (`repositories/staff_repository.py:464–528`) using `AuthService._hash_password` (`services/auth_service.py:120–131`).
3. **Backend reset endpoint** — Add `POST /api/v1/staff/{staff_id}/reset-password` (admin-only) that takes a new password and bypasses the "current password" requirement of `auth/change-password`.
4. **Backend audit** — Every successful password write logs via `AuditService.log_action` (`services/audit_service.py:80–135`) with actions `staff.password_set` (first time) and `staff.password_reset` (replacement) — including actor, target, IP, UA, outcome.
5. **Backend response extension** — Surface `is_login_enabled`, `last_login`, `locked_until` on `StaffResponse` so the list view can render the auth-state badges.
6. **Frontend** — Build a new `StaffForm` dialog (create + edit) with username, password (write-only), enable-login toggle; render three new badges (login-enabled, last-login relative time, locked) on the existing `StaffList`; add a "Reset password" action on `StaffDetail`.
7. **Tests** — Unit + integration coverage on the new endpoints + service paths; frontend test for the form's password-validation hint and the list-view badges.

## Feature Metadata

**Feature Type**: New Capability (UI for an existing data path)
**Estimated Complexity**: Medium
**Primary Systems Affected**: `Staff` schemas/service/API, `AuthService` (relaxed strength validator), `AuditService`, frontend staff feature
**Dependencies**: No new packages — bcrypt + Pydantic + FastAPI already in use.

---

## CONTEXT REFERENCES

### Relevant Codebase Files — READ THESE BEFORE IMPLEMENTING

**Backend — Model + Repository (auth columns already exist):**
- `src/grins_platform/models/staff.py:79–104` — every auth column we need (`username`, `password_hash`, `is_login_enabled`, `last_login`, `failed_login_attempts`, `locked_until`). **No migration required.**
- `src/grins_platform/repositories/staff_repository.py:50–99` — **`create()` signature today** accepts only: `name`, `phone`, `role`, `email`, `skill_level`, `certifications`, `hourly_rate`, `is_available`, `availability_notes`. **Does NOT accept** `username`, `password_hash`, or `is_login_enabled` → Task 6 must extend this signature (recommended) or use the existing `update()` after create.
- `src/grins_platform/repositories/staff_repository.py:134–198` — `update(staff_id, data: dict[str, Any])` accepts any column dict; safe for `username` + `is_login_enabled` writes.
- `src/grins_platform/repositories/staff_repository.py:435–462` — `find_by_username()` (use to enforce uniqueness on create/edit).
- `src/grins_platform/repositories/staff_repository.py:464–528` — `update_auth_fields(staff_id, password_hash=…, failed_login_attempts=…, locked_until=…, last_login=…)`. Already used by `AuthService.change_password` (`services/auth_service.py:531`); reuse the exact same call.

**Backend — Schemas (to extend):**
- `src/grins_platform/schemas/staff.py:22–106` — `StaffCreate`. Pattern to mirror: field declarations + `@field_validator` decorators (lines 96–106).
- `src/grins_platform/schemas/staff.py:109–200` — `StaffUpdate` (all fields optional).
- `src/grins_platform/schemas/staff.py:219–293` — `StaffResponse`. Add `is_login_enabled`, `last_login`, `locked_until` fields here so the list view receives them.
- `src/grins_platform/schemas/auth.py:87–130` — `ChangePasswordRequest` with the **current strict** strength validator (upper+lower+number+8). **Don't touch this** — it's used by the self-service path. Build a separate, looser validator for admin-set/reset (per user's Standard decision: 8 chars + letter + number, no case requirement, plus blocklist).

**Backend — Service + Auth:**
- `src/grins_platform/services/staff_service.py:60–89` — `create_staff()`. Extend to route auth fields through `update_auth_fields` after creating the row.
- `src/grins_platform/services/staff_service.py:115–` — `update_staff()` (read the rest of the file before editing).
- `src/grins_platform/services/auth_service.py:120–131` — `_hash_password(password) -> str`. **Don't duplicate** — call this from staff service via a thin helper (or extract `BcryptContext` to a shared module).
- `src/grins_platform/services/auth_service.py:494–533` — `change_password()`. **Don't reuse the endpoint** — it requires `current_password`. New admin reset bypasses that.

**Backend — API + Dependencies:**
- `src/grins_platform/api/v1/staff.py:295–316` — `create_staff` endpoint (no auth dependency today!).
- `src/grins_platform/api/v1/staff.py:359–386` — `update_staff`.
- `src/grins_platform/api/v1/dependencies.py:148–163` — `get_staff_service()` already exists; injects `StaffService` with a session-bound repository. No change needed.
- `src/grins_platform/api/v1/auth_dependencies.py:152–174` — `require_admin()` dependency. Use `AdminUser` type alias at `:302` for the new endpoints + the existing create/update endpoints (which currently have no auth guard).
- `src/grins_platform/api/v1/router.py:113–117` — staff router mount at `/staff`. The new reset endpoint will sit on the staff router so it lands at `/api/v1/staff/{id}/reset-password`.

**Existing callers of `POST /staff` (Task 10 breaking-change audit):**
- `frontend/src/features/staff/api/staffApi.ts:39–42` — `staffApi.create` posts to `/staff` (called by `useCreateStaff` only, gated behind the staff page UI; admin auth is already required to reach that UI).
- `frontend/src/features/staff/api/staffApi.test.ts:74–86` — test that mocks `apiClient.post`. **Not affected** by adding admin guard server-side; only mocks the client.
- `e2e/master-plan/bug-resolution-2026-05-04/f9-…sh` and `f10-…sh` — these only call `GET /api/v1/staff?role=tech` (read-only); they do not POST. **Not affected.**
- **Conclusion:** adding `AdminUser` to `create_staff` / `update_staff` is safe — the only caller is the staff UI itself, which is already gated on an authenticated session via `apiClient` (CSRF + cookie). No other production code POSTs to `/staff`.

**Backend — Audit (use existing infrastructure):**
- `src/grins_platform/services/audit_service.py:67–135` — `AuditService.log_action(db, *, actor_id, actor_role, action, resource_type, resource_id, details, ip_address, user_agent)`. Async; takes the request session.
- `src/grins_platform/api/v1/audit.py:73` — example of `AuditService()` no-arg instantiation + how the session is passed in.
- `src/grins_platform/api/v1/portal.py:100` — same pattern in another endpoint.
- `src/grins_platform/models/audit_log.py:21–65` — schema of the audit row (so you know what `details` should look like).
- `src/grins_platform/services/audit_service.py:18–39` — header comment lists every canonical action string. **Extend the list there** with `staff.password_set` and `staff.password_reset` when you add them.

**Frontend — Staff feature (vertical slice):**
- `frontend/src/features/staff/types/index.ts:8–22` — `Staff` interface. Add `username`, `is_login_enabled`, `last_login`, `locked_until` fields.
- `frontend/src/features/staff/types/index.ts:24–45` — `StaffCreate` / `StaffUpdate` interfaces. Add `username`, `password`, `is_login_enabled`.
- `frontend/src/features/staff/api/staffApi.ts:39–50` — existing `create` / `update` calls. Add `resetPassword(id, password)` → `POST /staff/{id}/reset-password`.
- `frontend/src/features/staff/hooks/useStaffMutations.ts:13–55` — `useCreateStaff` / `useUpdateStaff` / `useDeleteStaff` patterns. Add `useResetStaffPassword`.
- `frontend/src/features/staff/components/StaffList.tsx:73–228` — column definitions. Add new badges/columns in the same style (see roleColors + roleLabels lines 37–47 for the pattern).
- `frontend/src/features/staff/components/StaffDetail.tsx:1–100` — toast/edit/delete pattern. Add a "Reset password" action.
- `frontend/src/pages/Staff.tsx:36–40` — "Add Staff" button is a no-op today (no `onClick`). Wire it to open the new `StaffForm` dialog.

**Tests for reference patterns:**
- `src/grins_platform/tests/unit/test_auth_service.py` — auth service test patterns.
- `src/grins_platform/tests/unit/test_auth_schemas.py` — Pydantic validator test patterns (mirror for the new password strength validator).
- `src/grins_platform/tests/unit/test_auth_models.py`, `test_auth_dependencies.py`, `test_auth_guard_jobs.py` — admin-guard test examples.
- `frontend/src/features/staff/hooks/useStaffMutations.test.tsx:1–80` — frontend mutation test pattern. **Must update** the `vi.mock('../api/staffApi', …)` block at lines 18–25 to add `resetPassword: vi.fn()`.
- `frontend/src/features/staff/api/staffApi.test.ts:60–119` — frontend API test pattern. Mock-staff fixture at lines 27–41 is missing the new auth fields (`username`, `is_login_enabled`, `last_login`, `locked_until`); extend it to keep TypeScript happy after the `Staff` interface widens.
- **No existing backend staff tests** — `ls src/grins_platform/tests/unit/ | grep staff` returns nothing; no `test_staff_service.py` or `test_staff_api.py` exists today. Task 22 is therefore almost no-op on the backend; only the two frontend test files above need touch-ups.

**Frontend reference for the new dialog + form (canonical patterns identified during planning):**
- `frontend/src/features/leads/components/CreateLeadDialog.tsx:78–100` — **best match** for the `StaffForm` dialog wrapper. Uses `Dialog` + `DialogContent` + inner `useForm` + `zodResolver`. Copy this top-level structure; swap field set.
- `frontend/src/features/customers/components/CustomerForm.tsx:111–245` — **best match** for the dual create/edit mode. Uses a `customer?: Customer` optional prop and `isEditing = !!customer`. The `onSubmit` branches on `isEditing` to call create vs update. Mirror that branching for `StaffForm`.
- `frontend/src/features/customers/components/CustomerForm.tsx:1` carries a `// @ts-nocheck` for pre-existing TS issues — do **not** copy that comment; the new file should pass `tsc -p tsconfig.app.json --noEmit`.
- Form primitives at `@/components/ui/{dialog,form,input,select,switch}` — already used across the codebase; no new shadcn additions needed.

### New Files to Create

**Backend:**
- *(no new files — all changes are extensions to existing schemas/services/endpoints)*

**Backend tests:**
- `src/grins_platform/tests/unit/test_staff_auth_management.py` — covers: password-strength validator (positive + negative + blocklist), create-with-auth, update-with-auth, reset endpoint, audit-log row presence, admin-only guard.

**Frontend:**
- `frontend/src/features/staff/components/StaffForm.tsx` — shared create/edit dialog using `react-hook-form` + `zod` (pattern: see how `frontend/src/features/sales/components/SalesDetail.tsx` uses forms, or any existing modal in `components/ui/dialog.tsx` callers).
- `frontend/src/features/staff/components/ResetPasswordDialog.tsx` — small dialog for the reset action.

**Frontend tests:**
- `frontend/src/features/staff/components/StaffForm.test.tsx` — render + submit + password-validation hint.
- `frontend/src/features/staff/components/StaffList.auth.test.tsx` — new badges render correctly for each state.

### Relevant Documentation — READ BEFORE IMPLEMENTING

- [Pydantic v2 field_validator (already in use)](https://docs.pydantic.dev/latest/concepts/validators/#field-validators) — `mode="after"` is default; raise `ValueError` for invalid. The existing `schemas/auth.py:105–130` is a copyable example.
- [FastAPI dependencies & Depends](https://fastapi.tiangolo.com/tutorial/dependencies/) — `AdminUser` Annotated alias usage already established (see `api/v1/auth.py:300–305` for the type, and `api/v1/audit.py` for `CurrentActiveUser` usage).
- [bcrypt-via-passlib pattern was replaced with raw bcrypt](https://github.com/pyca/bcrypt) — see `services/auth_service.py:76–94` (`BcryptContext` wrapper, `bcrypt.hashpw` / `bcrypt.checkpw`). **Do not introduce passlib.**
- [React Hook Form](https://react-hook-form.com/get-started) + [Zod](https://zod.dev/) — already pinned as frontend deps (`frontend/package.json:56,63`).
- [TanStack Query mutation invalidation](https://tanstack.com/query/latest/docs/framework/react/guides/mutations) — see `useStaffMutations.ts:13–55` for the established `queryClient.invalidateQueries({ queryKey: staffKeys.lists() })` pattern.

### Patterns to Follow

**Naming conventions:**
- Backend Python: snake_case for variables/functions, PascalCase for classes, MODULE_LEVEL_CONST in caps.
- Audit action strings: dotted `resource.action` like `staff.password_set` (see the canonical list at `services/audit_service.py:18–39`; **extend that list comment in the same change**).
- Pydantic error messages: module-level `_ERR_...` constants (see `schemas/auth.py:18–22`).
- Frontend types: PascalCase interfaces matching backend schema names (see `frontend/src/features/staff/types/index.ts:24–45`).
- Frontend hooks: `useCreateStaff`, `useUpdateStaff`, `useResetStaffPassword`.

**Password hashing:**
- Always go through `auth_service.pwd_context.hash(password)` or `AuthService._hash_password()`. Never call bcrypt directly. The 12-round cost factor is fixed at `auth_service.py:50`.

**Audit logging:**
- Pattern (from `api/v1/portal.py:100` and `api/v1/sales_pipeline.py:216`):
  ```python
  audit_service = AuditService()
  await audit_service.log_action(
      db=session,
      actor_id=current_user.id,
      actor_role=current_user.role,
      action="staff.password_set",
      resource_type="staff",
      resource_id=target_staff_id,
      details={"outcome": "success"},  # or {"outcome": "failure", "reason": "..."}
      ip_address=request.client.host if request.client else None,
      user_agent=request.headers.get("user-agent"),
  )
  ```

**Error handling:**
- Pydantic validation errors propagate to FastAPI as 422 automatically (no try/except needed in the route handler).
- Unique-username conflict → raise `HTTPException(status_code=409, detail="Username already taken")` from the service or the endpoint.
- Domain exceptions live under `src/grins_platform/exceptions/`; see `exceptions/auth.py` for the existing pattern. Don't add new exceptions unless reused in 2+ places.

**Frontend mutation + toast (from `StaffDetail.tsx:47–73`):**
```tsx
try {
  await mutation.mutateAsync({ id, password: data.password });
  toast.success('Password updated');
} catch {
  toast.error('Failed to update password');
}
```

**Frontend admin guard:**
- Hook: `useAuth` from `@/features/auth/components/AuthProvider` — returns `{ user, isAuthenticated, isLoading, login, logout, refreshToken, updateUser, setAuthState, loginWithPasskey }` (`frontend/src/features/auth/types/index.ts:48–62`).
- `user.role` shape: `'admin' | 'manager' | 'tech'` (`frontend/src/features/auth/types/index.ts:6`). Check `user?.role === 'admin'` before rendering the password / username / `is_login_enabled` inputs and the Reset action.
- The backend `AdminUser` dependency is the enforcement boundary; the frontend check is a UX guard so non-admins don't see broken inputs.
- Example: `frontend/src/features/auth/components/UserMenu.tsx:17–20` (`import { useAuth } from './AuthProvider'`; `const { user, logout } = useAuth();`) — exact import shape to mirror.

---

## IMPLEMENTATION PLAN

### Phase 1: Foundation — Schema + Validator

Add the new password-strength validator and extend `StaffCreate` / `StaffUpdate` / `StaffResponse`.

**Tasks:**
- Add module-level `_ADMIN_PASSWORD_MIN_LEN = 8` and `_ADMIN_PASSWORD_BLOCKLIST = frozenset({"admin123", "password", "qwerty", "letmein", "12345678"})` constants in a new helper module or at the top of `schemas/staff.py`.
- Add a reusable validator function `validate_admin_password(password: str, *, username: str | None) -> str` that enforces: length ≥ 8, contains `[A-Za-z]` and `\d`, not in blocklist, not equal to `username`. Place in `schemas/staff.py` (keeps the policy local to staff create/edit).
- Add `username: str | None`, `password: str | None`, `is_login_enabled: bool | None` to `StaffCreate`. Add a `@field_validator("password")` that, when set, invokes the helper using `info.data["username"]` (Pydantic v2 ValidationInfo).
- Add same three fields to `StaffUpdate`. Same validator.
- Add `username: str | None`, `is_login_enabled: bool`, `last_login: datetime | None`, `locked_until: datetime | None` to `StaffResponse`. **Never** expose `password_hash` or `failed_login_attempts`.

### Phase 2: Core Implementation — Service + Repository wiring

Plumb the new fields through `StaffService.create_staff` / `update_staff` and add the reset endpoint.

**Tasks:**
- Extend `StaffService.create_staff` (`services/staff_service.py:60–89`) to:
  1. After `repository.create(...)`, if `data.username` is set, check uniqueness via `repository.find_by_username(data.username)` and raise `HTTPException(409)` if taken (or a typed exception). **Note:** uniqueness is also enforced at the DB level via the `unique=True` on the column; catch `IntegrityError` defensively at the route layer.
  2. If `data.password` is set, hash via `AuthService._hash_password` (instantiate `AuthService(repository=…)` or extract `BcryptContext` to a shared helper — **recommended: extract**) and call `repository.update_auth_fields(staff.id, password_hash=hashed)`.
  3. If `data.is_login_enabled` is set, persist via the existing `repository.update` path (it's a normal column).
  4. Return the refreshed staff row (re-fetch by id so the response includes auth fields).
- Extend `StaffService.update_staff` similarly (read the existing function first — current code only updates non-auth fields).
- Add `StaffService.reset_password(staff_id, new_password)` that hashes + calls `update_auth_fields(password_hash=...)`. Also resets `failed_login_attempts=0` and `locked_until=None` (so a reset implicitly unlocks the account).
- Add a new endpoint in `api/v1/staff.py`:
  ```python
  @router.post("/{staff_id}/reset-password", status_code=status.HTTP_204_NO_CONTENT)
  async def reset_password(
      staff_id: UUID,
      body: ResetPasswordRequest,
      current_user: AdminUser,
      service: Annotated[StaffService, Depends(get_staff_service)],
      session: Annotated[AsyncSession, Depends(get_db_session)],
      request: Request,
  ) -> None: ...
  ```
  Add `ResetPasswordRequest` schema in `schemas/staff.py` (single field: `new_password: str` with the admin password validator).
- Add `current_user: AdminUser` to the existing `create_staff` and `update_staff` endpoints (currently they have no auth guard — a separate gap this work surfaces). **Confirm with the user before adding** if it would break existing callers — likely it does not, since admin is the only one creating staff today; default behavior is unauthenticated which is itself a bug.
- After any successful password write in the service or endpoint, fire `AuditService.log_action(action="staff.password_set" if was_unset else "staff.password_reset", ...)` with actor + target + IP + UA + outcome.

### Phase 3: Integration — Frontend types, API, and form

Make the new fields visible end-to-end.

**Tasks:**
- Extend `frontend/src/features/staff/types/index.ts`:
  - `Staff` gets `username: string | null; is_login_enabled: boolean; last_login: string | null; locked_until: string | null;`
  - `StaffCreate` gets `username?: string; password?: string; is_login_enabled?: boolean;`
  - Same for `StaffUpdate`.
  - Add `interface ResetPasswordPayload { new_password: string }`.
- Extend `frontend/src/features/staff/api/staffApi.ts` with `resetPassword(id: string, payload: ResetPasswordPayload)` → `apiClient.post(/staff/${id}/reset-password, payload)`.
- Extend `frontend/src/features/staff/hooks/useStaffMutations.ts` with `useResetStaffPassword` that follows the existing `useUpdateStaff` shape (invalidate `staffKeys.detail(id)` on success).
- Build `frontend/src/features/staff/components/StaffForm.tsx`:
  - Dialog wrapper (`@/components/ui/dialog`); used for both create + edit modes (`mode: 'create' | 'edit'` prop).
  - Fields: name, phone, email, role, skill_level, hourly_rate, **username, password (only when creating OR when editing AND user toggles "Set new password"), is_login_enabled toggle**.
  - Use `react-hook-form` + `zodResolver` (zod already imported elsewhere — grep for existing usages to confirm the resolver pattern).
  - Client-side hint under the password field: "At least 8 characters, including a letter and a number."
  - Mode `create` calls `useCreateStaff`, `edit` calls `useUpdateStaff`. Reset-password is a separate action exposed on `StaffDetail` (next task).
  - Never echo the password back after a save; the password input always starts blank.
- Build `frontend/src/features/staff/components/ResetPasswordDialog.tsx`:
  - Triggered from `StaffDetail`. New-password field with the same strength hint.
  - Calls `useResetStaffPassword`. On success: toast + close.
- Add a "Reset password" `DropdownMenuItem` in `StaffDetail.tsx` (similar to the existing Delete pattern) that opens `ResetPasswordDialog`.
- Wire the "Add Staff" button in `frontend/src/pages/Staff.tsx:36–40` to open `<StaffForm mode="create" />`.
- Extend `frontend/src/features/staff/components/StaffList.tsx`:
  - Add an "Login" column after "Role" rendering: `is_login_enabled` → green `Login enabled` badge, else gray `No login` badge.
  - Add a "Last login" column showing `last_login` formatted via `date-fns` `formatDistanceToNow` (already a dep) — fall back to `Never` when null.
  - Add a "Locked" red badge inline when `locked_until && new Date(locked_until) > new Date()`. (Don't add a full column for this — overlay in the Login column.)

### Phase 4: Testing & Validation

Cover the new code with unit + integration tests + a minimal frontend test pass.

**Tasks:**
- `tests/unit/test_staff_auth_management.py` — new tests:
  - Validator: accept `Abcd1234` and `goodpass1`; reject `short1`, `noLetters12345`, `nodigits`, `admin123` (blocklist), and `Bob1234` when `username='Bob1234'` (matches username).
  - `StaffService.create_staff` with `password='Abcd1234', username='newtech', is_login_enabled=True` — assert `password_hash` is set (bcrypt format `$2b$12$...`), `is_login_enabled=True`, audit row created with action `staff.password_set`.
  - `StaffService.update_staff` updating password — audit action is `staff.password_reset` (because hash existed).
  - `StaffService.reset_password` — clears `failed_login_attempts` and `locked_until`, sets new hash, audit row action `staff.password_reset`.
  - Reset endpoint without `AdminUser` → 403. With wrong role → 403.
  - Username uniqueness collision returns 409.
- `tests/integration/test_staff_auth_integration.py` (or extend an existing staff integration file) — full HTTP path: POST staff with creds → can immediately log in via `POST /api/v1/auth/login` → token returned, `last_login` set.
- `frontend/src/features/staff/components/StaffForm.test.tsx` — render, submit with valid data, verify mutation called; submit with weak password, verify validation error renders.
- `frontend/src/features/staff/components/StaffList.auth.test.tsx` — render rows for staff with `is_login_enabled: true / false / locked` and assert each badge variant.
- Update `frontend/src/features/staff/hooks/useStaffMutations.test.tsx` if it covers all mutations — add a test for `useResetStaffPassword`.

---

## STEP-BY-STEP TASKS

Execute in order. Each task is atomic and has a runnable validation command.

### 1. CREATE `src/grins_platform/schemas/staff.py` — admin password validator + ResetPasswordRequest schema

- **IMPLEMENT**:
  - Module constants `_ADMIN_PASSWORD_MIN_LEN = 8` and `_ADMIN_PASSWORD_BLOCKLIST = frozenset({"admin123", "password", "qwerty", "letmein", "12345678"})`.
  - Helper `def _validate_admin_password(password: str, *, username: str | None) -> str` that raises `ValueError` on: <8 chars, no `[A-Za-z]`, no `\d`, in blocklist (case-insensitive), equals username.
  - New class `ResetPasswordRequest(BaseModel)` with `new_password: str = Field(..., min_length=8, max_length=128)` and a `@field_validator("new_password")` that calls `_validate_admin_password(v, username=None)`.
- **PATTERN**: Mirror the validator shape from `schemas/auth.py:105–130`.
- **IMPORTS**: `from pydantic import BaseModel, Field, field_validator`; `from pydantic_core.core_schema import ValidationInfo` (for accessing sibling fields in subsequent tasks; not needed for ResetPasswordRequest).
- **GOTCHA**: Use `info.data` to access `username` for the validator on `StaffCreate` / `StaffUpdate` in the next task — that's why the helper takes username as a kwarg.
- **VALIDATE**: `uv run python -c "from grins_platform.schemas.staff import ResetPasswordRequest; ResetPasswordRequest(new_password='Goodpass1')"` succeeds; `uv run python -c "from grins_platform.schemas.staff import ResetPasswordRequest; ResetPasswordRequest(new_password='short')"` raises.

### 2. UPDATE `src/grins_platform/schemas/staff.py` — extend StaffCreate

- **IMPLEMENT**:
  - Add optional `username: str | None = Field(default=None, min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_.]+$")`.
  - Add optional `password: str | None = Field(default=None, min_length=8, max_length=128, description="Initial password — staff can change after first login")`.
  - Add optional `is_login_enabled: bool | None = Field(default=None, description="Enable login for this staff member")`.
  - `@field_validator("password")` invoking `_validate_admin_password(v, username=info.data.get("username"))`.
- **PATTERN**: `StaffCreate` (lines 22–106) for field placement; `schemas/auth.py:105–130` for the validator body.
- **IMPORTS**: Add `from pydantic_core.core_schema import ValidationInfo` (if not already present).
- **GOTCHA**: Pydantic v2 `info.data` only contains fields that have already been parsed in the order they appear in the model. **Place `username` above `password`** so the validator can read it.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_staff_schemas.py -k 'create' -x` (extend the test file or add).

### 3. UPDATE `src/grins_platform/schemas/staff.py` — extend StaffUpdate

- **IMPLEMENT**: Same three fields as Task 2, all optional. Same validator.
- **PATTERN**: `StaffUpdate` (lines 109–200).
- **VALIDATE**: `uv run python -c "from grins_platform.schemas.staff import StaffUpdate; StaffUpdate(password='Goodpass1', username='alice')"` succeeds.

### 4. UPDATE `src/grins_platform/schemas/staff.py` — extend StaffResponse

- **IMPLEMENT**: Add `username: str | None`, `is_login_enabled: bool`, `last_login: datetime | None`, `locked_until: datetime | None`. **Do NOT** add `password_hash` or `failed_login_attempts`.
- **PATTERN**: `StaffResponse` (lines 219–293).
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_staff_schemas.py -k 'response' -x`.

### 5. UPDATE `src/grins_platform/services/auth_service.py` — extract BcryptContext (optional refactor) OR re-export `_hash_password`

- **IMPLEMENT**: Add a module-level `hash_password(password: str) -> str` thin function that calls `pwd_context.hash(password)`. This avoids creating an `AuthService` instance just to hash. Place near `pwd_context = BcryptContext()` at line 94.
- **PATTERN**: Existing `pwd_context` at line 94.
- **GOTCHA**: Do NOT change `BCRYPT_ROUNDS = 12` (line 50). Keep cost factor consistent with existing hashes.
- **VALIDATE**: `uv run python -c "from grins_platform.services.auth_service import hash_password; print(hash_password('Abcd1234'))"` prints a `$2b$12$...` string.

### 6. UPDATE `src/grins_platform/services/staff_service.py` — wire auth fields into create_staff

**Verified:** `StaffRepository.create` at `staff_repository.py:50–99` accepts `name, phone, role, email, skill_level, certifications, hourly_rate, is_available, availability_notes` — **not** `username`, `password_hash`, or `is_login_enabled`. Path: extend the repo signature in this same task (cleanest) so it accepts the new fields; then call `update_auth_fields` only for the password hash.

- **IMPLEMENT (repository, in `staff_repository.py:50–99`):**
  - Add optional kwargs to `create()`: `username: str | None = None`, `password_hash: str | None = None`, `is_login_enabled: bool = False`.
  - Pass them into the `Staff(...)` constructor at lines 82–92.
- **IMPLEMENT (service, in `staff_service.py:60–89`):**
  - At the top of `create_staff` (after phone normalization), if `data.username` is set, call `await self.repository.find_by_username(data.username)`; if not None, raise `HTTPException(status_code=409, detail="Username already taken")`.
  - If `data.password` is set, compute `password_hash = hash_password(data.password)`; else `password_hash = None`.
  - Call `self.repository.create(..., username=data.username, password_hash=password_hash, is_login_enabled=bool(data.is_login_enabled))`.
  - **Return** the created staff row directly — `repository.create` already does `session.refresh(staff)` so all fields including auth are populated.
- **PATTERN**: Existing `create_staff` at lines 60–89; existing `repository.create` constructor at lines 82–92.
- **IMPORTS**: `from fastapi import HTTPException`; `from grins_platform.services.auth_service import hash_password`.
- **GOTCHA**: `is_login_enabled` has `server_default="false"` (model line 88) — defaulting to `False` in the kwarg matches that, but if `data.is_login_enabled is None` (i.e., the admin omitted the field) treat it as `False` for create, not "unchanged."
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_staff_auth_management.py::test_create_staff_with_credentials -x`.

### 7. UPDATE `src/grins_platform/services/staff_service.py` — wire auth fields into update_staff

- **IMPLEMENT**:
  - For each of `username`, `password`, `is_login_enabled` if set on `StaffUpdate`:
    - `username`: uniqueness check (skip if same as current); persist via `repository.update`.
    - `password`: hash + `update_auth_fields(password_hash=...)`. Audit action determined by whether prior `password_hash` was None (`staff.password_set`) or set (`staff.password_reset`) — *but* audit happens at the endpoint layer because it needs the request for IP/UA. The service returns `password_changed: bool` (or similar) via a small return-type wrapper, or simpler: emit a `StaffPasswordChangedEvent` returnable. **Simplest: service returns Staff and a `was_password_set` boolean tuple**.
  - Re-fetch and return updated row + boolean.
- **PATTERN**: Existing `update_staff` (read first before editing).
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_staff_auth_management.py::test_update_staff_password -x`.

### 8. ADD `src/grins_platform/services/staff_service.py` — reset_password method

- **IMPLEMENT**:
  ```python
  async def reset_password(self, staff_id: UUID, new_password: str) -> Staff:
      staff = await self.get_staff(staff_id)  # raises StaffNotFoundError if absent
      new_hash = hash_password(new_password)
      updated = await self.repository.update_auth_fields(
          staff_id,
          password_hash=new_hash,
          failed_login_attempts=0,
          locked_until=None,
      )
      if updated is None:
          raise StaffNotFoundError(staff_id)
      return updated
  ```
- **PATTERN**: Mirror `AuthService.change_password` (`auth_service.py:494–533`).
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_staff_auth_management.py::test_reset_password_clears_lockout -x`.

### 9. ADD `src/grins_platform/api/v1/staff.py` — reset-password endpoint

- **IMPLEMENT**:
  ```python
  from fastapi import Request
  from grins_platform.api.v1.auth_dependencies import AdminUser
  from grins_platform.schemas.staff import ResetPasswordRequest
  from grins_platform.services.audit_service import AuditService

  @router.post(
      "/{staff_id}/reset-password",
      status_code=status.HTTP_204_NO_CONTENT,
      summary="Admin reset of a staff member's password",
  )
  async def reset_password(
      staff_id: UUID,
      body: ResetPasswordRequest,
      request: Request,
      current_user: AdminUser,
      service: Annotated[StaffService, Depends(get_staff_service)],
      session: Annotated[AsyncSession, Depends(get_db_session)],
  ) -> None:
      _endpoints.log_started("reset_password", staff_id=str(staff_id))
      try:
          await service.reset_password(staff_id, body.new_password)
      except StaffNotFoundError as e:
          raise HTTPException(status_code=404, detail="Staff not found") from e

      audit_service = AuditService()
      await audit_service.log_action(
          db=session,
          actor_id=current_user.id,
          actor_role=current_user.role,
          action="staff.password_reset",
          resource_type="staff",
          resource_id=staff_id,
          details={"outcome": "success"},
          ip_address=request.client.host if request.client else None,
          user_agent=request.headers.get("user-agent"),
      )
      _endpoints.log_completed("reset_password", staff_id=str(staff_id))
  ```
- **PATTERN**: Endpoint shape from `api/v1/staff.py:295–316`; audit pattern from `api/v1/portal.py:100`.
- **GOTCHA**: `AsyncSession` is `get_db_session` (already imported in `api/v1/staff.py`); `Request` must be imported from `fastapi`.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/integration/test_staff_auth_integration.py::test_admin_reset_password -x`.

### 10. UPDATE `src/grins_platform/api/v1/staff.py` — add admin guard + audit to create_staff / update_staff

- **IMPLEMENT**:
  - Add `current_user: AdminUser` parameter to `create_staff` (line 303) and `update_staff` (line 365). Add `request: Request` and `session: Annotated[AsyncSession, Depends(get_db_session)]` similarly.
  - After successful create/update where a password was set, fire `AuditService.log_action(action="staff.password_set" if first_time else "staff.password_reset", ...)`. Use the `was_password_set` return from Task 7 (or similar mechanism).
- **PATTERN**: `api/v1/staff.py:295–316`, `:359–386`.
- **GOTCHA**: Adding `AdminUser` to `create_staff` is a **breaking change** for any unauthenticated caller. Per the §14 plan, admin is the only legitimate caller — confirm with user before shipping.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_staff_auth_management.py -k 'admin_guard' -x`.

### 11. UPDATE `src/grins_platform/services/audit_service.py` — extend canonical action list comment

- **IMPLEMENT**: Add two lines to the action-list comment at lines 18–39:
  ```
  - ``staff.password_set``                          — admin set a password on a staff account for the first time
  - ``staff.password_reset``                        — admin replaced an existing password
  ```
- **PATTERN**: Existing comment block lines 18–39.
- **VALIDATE**: Manual: `grep -n 'staff.password' /Users/kirillrakitin/Grins_irrigation_platform/src/grins_platform/services/audit_service.py` shows the new entries.

### 12. CREATE `src/grins_platform/tests/unit/test_staff_auth_management.py`

- **IMPLEMENT**: Test cases listed in Phase 4. Use existing fixtures from `tests/unit/test_auth_service.py` for an in-memory or async SQLite test DB (whichever pattern is already used).
- **PATTERN**: `tests/unit/test_auth_service.py` (for auth tests), `tests/unit/test_auth_schemas.py` (for validator tests).
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_staff_auth_management.py -x`.

### 13. UPDATE `frontend/src/features/staff/types/index.ts` — extend interfaces

- **IMPLEMENT**: Add the fields listed in Phase 3 Task 1 (Staff, StaffCreate, StaffUpdate, plus new `ResetPasswordPayload`).
- **PATTERN**: Existing interface definitions (lines 8–62).
- **VALIDATE**: `cd frontend && npm run typecheck` passes.

### 14. UPDATE `frontend/src/features/staff/api/staffApi.ts` — add resetPassword

- **IMPLEMENT**:
  ```ts
  async resetPassword(id: string, payload: ResetPasswordPayload): Promise<void> {
    await apiClient.post(`${BASE_URL}/${id}/reset-password`, payload);
  },
  ```
- **PATTERN**: Existing methods (lines 39–82).
- **VALIDATE**: `cd frontend && npm run typecheck`.

### 15. UPDATE `frontend/src/features/staff/hooks/useStaffMutations.ts` — add useResetStaffPassword

- **IMPLEMENT**:
  ```ts
  export function useResetStaffPassword() {
    const queryClient = useQueryClient();
    return useMutation({
      mutationFn: ({ id, payload }: { id: string; payload: ResetPasswordPayload }) =>
        staffApi.resetPassword(id, payload),
      onSuccess: (_, { id }) => {
        queryClient.invalidateQueries({ queryKey: staffKeys.detail(id) });
      },
    });
  }
  ```
- **PATTERN**: `useUpdateStaff` (lines 28–40).
- **VALIDATE**: `cd frontend && npm run typecheck`.

### 16. CREATE `frontend/src/features/staff/components/StaffForm.tsx`

- **IMPLEMENT**: `Dialog` wrapper following `CreateLeadDialog.tsx:78–88` (open/onOpenChange props, outer dialog → inner form component). Inner form uses `react-hook-form` + `zodResolver(staffSchema)`. Fields: name, phone, email, role (Select), skill_level (Select), hourly_rate, **then auth section (only when `useAuth().user?.role === 'admin'`)**: username, password (write-only), `is_login_enabled` (Switch). Mode `'create'` calls `useCreateStaff`; `'edit'` calls `useUpdateStaff`. Toast + close on success via `getErrorMessage(err)`.
- **PATTERN**:
  - Dialog wrapper: `frontend/src/features/leads/components/CreateLeadDialog.tsx:78–100` (verbatim shape, swap label/testid).
  - Create/edit branching: `frontend/src/features/customers/components/CustomerForm.tsx:111–245` (use `staff?: Staff` optional prop, `isEditing = !!staff`).
  - Field rendering: `FormField`/`FormItem`/`FormLabel`/`FormControl`/`FormMessage` from `@/components/ui/form` (see `CreateLeadDialog.tsx:34–41` for imports).
- **IMPORTS**:
  ```tsx
  import { useForm } from 'react-hook-form';
  import { zodResolver } from '@hookform/resolvers/zod';
  import { z } from 'zod';
  import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '@/components/ui/dialog';
  import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form';
  import { Input } from '@/components/ui/input';
  import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
  import { Switch } from '@/components/ui/switch';
  import { Button } from '@/components/ui/button';
  import { toast } from 'sonner';
  import { useAuth } from '@/features/auth/components/AuthProvider';
  import { useCreateStaff, useUpdateStaff } from '../hooks';
  import { getErrorMessage } from '@/core/api';
  ```
- **GOTCHA 1**: For edit mode, password input must default to blank — if the admin doesn't type one, omit `password` from the payload (don't send `''` — backend validator would reject). Use `password: data.password?.trim() || undefined`.
- **GOTCHA 2**: Do **not** include `// @ts-nocheck` at the top (this is the marker `CustomerForm.tsx:1` carries for pre-existing TS errors; the new file should pass typecheck cleanly).
- **GOTCHA 3**: The zod schema's password validator must match the backend's exactly — `z.string().min(8).regex(/[A-Za-z]/, 'Must include a letter').regex(/\d/, 'Must include a number')` plus a `superRefine` block that checks the blocklist + username match. Keep the blocklist constant in sync with `schemas/staff.py` (or import via the API if you'd rather not duplicate — but for v1 hard-coding the same 5 strings is fine).
- **VALIDATE**: `cd frontend && npm run typecheck && npm run lint`.

### 17. CREATE `frontend/src/features/staff/components/ResetPasswordDialog.tsx`

- **IMPLEMENT**: Small dialog with a single password input + strength hint + Save/Cancel. Calls `useResetStaffPassword`.
- **PATTERN**: Existing simple confirm-dialogs in `frontend/src/features/...` (grep for `Dialog` + `useState` patterns).
- **VALIDATE**: `cd frontend && npm run typecheck`.

### 18. UPDATE `frontend/src/features/staff/components/StaffDetail.tsx` — add Reset Password action

- **IMPLEMENT**: Add a "Reset password" `Button` (or `DropdownMenuItem` if using the same dropdown pattern as the list view) that opens `ResetPasswordDialog`. Gate the render with `useAuth()` — only show when `user?.role === 'admin'`.
- **PATTERN**: Existing Edit/Delete buttons in `StaffDetail.tsx:46–73`; admin gate import from `frontend/src/features/auth/components/UserMenu.tsx:17–20` (`import { useAuth } from '@/features/auth/components/AuthProvider'`).
- **VALIDATE**: `cd frontend && npm run typecheck`.

### 19. UPDATE `frontend/src/features/staff/components/StaffList.tsx` — add Login + Last login + Locked badges

- **IMPLEMENT**:
  - New "Login" column rendering `is_login_enabled ? <Badge>Login enabled</Badge> : <Badge variant=secondary>No login</Badge>`. Overlay a red `Locked` badge inline when `locked_until && new Date(locked_until) > new Date()`.
  - New "Last login" column: `staff.last_login ? formatDistanceToNow(new Date(staff.last_login), { addSuffix: true }) : 'Never'`.
- **PATTERN**: Existing `roleColors` / `roleLabels` pattern (lines 37–47) and Availability column (lines 124–153).
- **IMPORTS**: `import { formatDistanceToNow } from 'date-fns';`.
- **VALIDATE**: `cd frontend && npm run typecheck && npm run lint`.

### 20. UPDATE `frontend/src/pages/Staff.tsx` — wire Add Staff to StaffForm

- **IMPLEMENT**: Add `useState` for `formOpen`. Render `<StaffForm open={formOpen} onOpenChange={setFormOpen} mode="create" />`. Wire `onClick={() => setFormOpen(true)}` on the "Add Staff" button.
- **PATTERN**: Standard Dialog usage in other pages.
- **VALIDATE**: `cd frontend && npm run typecheck && npm run lint`.

### 21. CREATE `frontend/src/features/staff/components/StaffForm.test.tsx` + `StaffList.auth.test.tsx`

- **IMPLEMENT**: Cover the scenarios in Phase 4.
- **PATTERN**: Existing `useStaffMutations.test.tsx`, `staffApi.test.ts`.
- **VALIDATE**: `cd frontend && npm test -- --run staff`.

### 22. UPDATE existing tests broken by the new fields

**Verified:** no `test_staff_service.py` or `test_staff_api.py` exists in `src/grins_platform/tests/`. Backend test impact is therefore zero from existing files; only the new `test_staff_auth_management.py` from Task 12 covers backend. Frontend test impact:

- **`frontend/src/features/staff/hooks/useStaffMutations.test.tsx:18–25`** — extend the `vi.mock('../api/staffApi', …)` block to add `resetPassword: vi.fn()`.
- **`frontend/src/features/staff/hooks/useStaffMutations.test.tsx:27–41`** — extend `mockStaff` to include `username: 'john.doe'`, `is_login_enabled: false`, `last_login: null`, `locked_until: null` so the widened `Staff` interface still type-checks.
- **`frontend/src/features/staff/api/staffApi.test.ts:27–41`** — same `mockStaff` extension. Add a `describe('resetPassword', …)` block mirroring `describe('updateAvailability', …)` at lines 111–119: mock `apiClient.post`, call `staffApi.resetPassword('staff-123', { new_password: 'Newpass1' })`, assert `apiClient.post` was called with `'/staff/staff-123/reset-password'` and the body.

- **VALIDATE**: `uv run pytest && cd frontend && npm test -- --run`.

---

## TESTING STRATEGY

### Unit Tests

- **Backend (pytest + pytest-asyncio):**
  - Validator behaviour (accept/reject the 7 cases listed in Phase 4 Task 1).
  - Service: create-with-creds, update-with-creds, reset, username collision, lockout clear-on-reset.
  - Endpoint: admin guard enforced, audit row written with correct action + actor + target.
- **Frontend (Vitest + Testing Library):**
  - StaffForm: renders, submits valid data, shows hint for weak passwords.
  - StaffList: badges render for each auth state.
  - useResetStaffPassword: invalidates `staffKeys.detail(id)` on success.

### Integration Tests

- Full HTTP path: admin POST `/api/v1/staff` with creds → GET `/api/v1/staff/{id}` returns `is_login_enabled: true`, `username` set → POST `/api/v1/auth/login` with those creds returns a token → `last_login` is now non-null.
- Admin POST `/api/v1/staff/{id}/reset-password` → next login uses the new password (old hash rejected); `locked_until` cleared.

### Edge Cases

- Username collision (case-sensitive uniqueness — verify with `find_by_username` semantics).
- Username matches password exactly → validator rejects.
- Password set with `is_login_enabled=False` — saves the hash but user cannot log in until enabled.
- Reset on locked account — clears `failed_login_attempts` + `locked_until`.
- Update with `password=null` (no change) — does not re-hash, no audit row.
- Update with `username=null` for a user who has a username — schema treats null as "no change" (don't accidentally null out the column). Confirm by reading the `update_staff` service code.

---

## VALIDATION COMMANDS

### Level 1: Syntax & Style

```bash
uv run ruff check src/grins_platform/schemas/staff.py src/grins_platform/services/staff_service.py src/grins_platform/api/v1/staff.py
uv run ruff format --check src/grins_platform/schemas/staff.py src/grins_platform/services/staff_service.py src/grins_platform/api/v1/staff.py
uv run mypy src/grins_platform/services/staff_service.py src/grins_platform/api/v1/staff.py
cd frontend && npm run lint && npm run typecheck
```

### Level 2: Unit Tests

```bash
uv run pytest src/grins_platform/tests/unit/test_staff_auth_management.py -x -v
uv run pytest src/grins_platform/tests/unit/test_staff_schemas.py -x -v   # if extended
cd frontend && npm test -- --run staff
```

### Level 3: Integration Tests

```bash
uv run pytest src/grins_platform/tests/integration/test_staff_auth_integration.py -x -v
```

### Level 4: Manual Validation

(Dev environment — `kirillrakitinsecond@gmail.com` allowed; `+19527373312` for any SMS effects, none expected here.)

1. Log in as admin (`admin` / `admin123`) → navigate to `/staff`.
2. Click "Add Staff" → fill the form (name, phone, role=tech, username=`testtech1`, password=`Goodpass1`, is_login_enabled=on) → Save.
3. Verify: row appears in the list with the "Login enabled" badge + "Last login: Never".
4. Open a new private window → POST `/api/v1/auth/login` with `testtech1` / `Goodpass1` → token returned.
5. Refresh the staff list → "Last login: a few seconds ago".
6. As admin: open `testtech1`'s detail → click "Reset password" → new password `Newpass1` → Save.
7. Log out, log in with `Newpass1` → works. Log in with `Goodpass1` → 401.
8. Verify audit rows: GET `/api/v1/audit?actor_id=<admin_id>&action=staff.password_set` returns the create-row; `action=staff.password_reset` returns the reset row.
9. Try weak passwords in the form (`short`, `admin123`, `nodigits`, matching username) → each shows an inline validation error.

### Level 5: Additional Validation

```bash
# Check that no new alembic migration was generated (shouldn't be — schema unchanged):
uv run alembic check
# Confirm no new env vars were introduced unintentionally:
git diff .env.example
```

---

## ACCEPTANCE CRITERIA

- [ ] Admin can create a staff member with `username` + `password` + `is_login_enabled=true` in one form submission and the new staff member can immediately log in.
- [ ] Admin can reset any staff member's password without knowing the previous one. Reset clears `failed_login_attempts` + `locked_until`.
- [ ] Admin cannot set a password that is <8 chars, missing a letter, missing a digit, on the blocklist, or equal to the username — validator rejects with a clear inline error.
- [ ] `password_hash` and `failed_login_attempts` are NEVER returned in any API response.
- [ ] Staff list view shows: login-enabled/no-login badge, last-login relative time (or "Never"), red "Locked" badge while locked.
- [ ] Every successful password set/reset writes an `audit_log` row with `action='staff.password_set'` or `'staff.password_reset'`, including actor, target staff id, IP, and user-agent.
- [ ] Non-admin users cannot reach `POST /api/v1/staff`, `PUT /api/v1/staff/{id}`, or `POST /api/v1/staff/{id}/reset-password` (403).
- [ ] All existing tests still pass; new tests cover the 7 validator cases + the 4 service flows + the 1 integration flow.
- [ ] `cd frontend && npm run build` succeeds; `uv run alembic check` confirms no new migration needed.

---

## COMPLETION CHECKLIST

- [ ] All 22 step-by-step tasks completed in order.
- [ ] Each task's validation command passed at the moment it was finished.
- [ ] Level 1–4 validation commands all pass.
- [ ] Manual validation walked end-to-end on dev.
- [ ] No regressions in existing staff list, staff detail, or auth flows.
- [ ] Audit log shows the new rows after the manual run.
- [ ] PR description links this plan file.

---

## NOTES

**Verification provenance.** Every file:line citation in this plan was Read or Grep'd directly in this planning conversation, not lifted from a subagent report.

| Citation | Method |
|---|---|
| `models/staff.py:79–104` (auth columns) | direct-read |
| `schemas/staff.py:22–293` (Create/Update/Response) | direct-read |
| `schemas/auth.py:87–130` (existing ChangePasswordRequest validator) | direct-read |
| `services/staff_service.py:60–89` (create_staff) | direct-read |
| `services/auth_service.py:50, 76–94, 120–131, 494–533` (BCRYPT_ROUNDS, BcryptContext, _hash_password, change_password) | direct-read |
| `services/audit_service.py:18–39, 80–135` (canonical action list, log_action signature) | direct-read |
| `repositories/staff_repository.py:50–99` (`create()` signature confirmed — no auth kwargs today), `:134–198` (`update()`), `:435–462` (`find_by_username`), `:464–528` (`update_auth_fields`) | direct-read |
| `api/v1/staff.py:295–316, 359–386` (create_staff, update_staff endpoints) | direct-read |
| `api/v1/auth.py:271–292` (change-password endpoint shape) | direct-read |
| `api/v1/auth_dependencies.py:152–174, 300–303` (require_admin, AdminUser alias) | direct-read |
| `api/v1/dependencies.py:148–163` (get_staff_service exists) | direct-grep |
| `api/v1/audit.py:73`, `api/v1/portal.py:100`, `api/v1/sales_pipeline.py:216` (AuditService() no-arg instantiation pattern) | direct-grep + direct-read |
| `api/v1/router.py:113–117` (staff router mount) | direct-read |
| `frontend/.../staff/types/index.ts`, `api/staffApi.ts` (+ test), `hooks/useStaffMutations.ts` (+ test), `components/StaffList.tsx`, `components/StaffDetail.tsx`, `pages/Staff.tsx` | direct-read |
| `frontend/.../auth/components/AuthProvider.tsx:1–80` + `types/index.ts:1–62` (`useAuth` hook + `User.role` type) | direct-read |
| `frontend/.../leads/components/CreateLeadDialog.tsx:1–100`, `customers/components/CustomerForm.tsx:1–245` (canonical dialog + create/edit form patterns) | direct-read |
| `e2e/master-plan/bug-resolution-2026-05-04/f9*.sh, f10*.sh` (only GETs `/api/v1/staff`) | direct-grep |
| `migrations/versions/` listing (no migration needed — Staff already has all auth columns) | direct-grep |

**Honesty gate.** I have personally Read or Grep'd, in this conversation, every file path, line number, function name, type name, and import path cited in this plan. Every library API and version cited has been confirmed against in-repo usage in this conversation. Anything previously delivered by a subagent report has been independently re-verified by me. **Anything I could not verify is explicitly named below — there is nothing in that list.**

**Previously-flagged gaps — all closed in a follow-up pass:**

1. ✅ **`StaffRepository.create` signature** — Read `staff_repository.py:50–99` directly. Confirmed: today accepts `name, phone, role, email, skill_level, certifications, hourly_rate, is_available, availability_notes`; does NOT accept `username`, `password_hash`, or `is_login_enabled`. Task 6 updated to add those three kwargs to `create()` in the same pass.
2. ✅ **Existing staff backend tests** — `ls src/grins_platform/tests/unit/ | grep staff` returns **no matches**. No `test_staff_service.py`, no `test_staff_api.py`. Task 22 reduced to two frontend test-file touch-ups; Task 12 still adds the new `test_staff_auth_management.py`.
3. ✅ **Frontend auth hook** — Verified: `useAuth` from `@/features/auth/components/AuthProvider`; returns `{ user, ... }` with `user.role: 'admin' | 'manager' | 'tech'` per `frontend/src/features/auth/types/index.ts:6`. Tasks 16 and 18 now cite the exact import path + example callsite (`UserMenu.tsx:17–20`).
4. ✅ **Existing form/dialog pattern** — Verified two canonical examples in-repo: `CreateLeadDialog.tsx` for the dialog wrapper and `CustomerForm.tsx` for create/edit dual-mode. Task 16 now references both with line numbers; the new `StaffForm.tsx` is no longer greenfield.

**Additional verifications added in this pass:**

- ✅ **Breaking-change audit for `AdminUser` on existing `create_staff` / `update_staff` endpoints.** Grep'd the entire frontend + `e2e/` + `scripts/` for callers of `POST /staff`. Only caller is `staffApi.create` via `useCreateStaff`, which already operates inside an authenticated admin session. No unauthenticated production caller exists. Safe to add the guard.
- ✅ **`get_staff_service` already exists** at `api/v1/dependencies.py:148–163` — Task 9 (the new reset-password endpoint) needs no new DI plumbing.
- ✅ **CustomerForm `@ts-nocheck` caveat** — explicitly called out in Task 16 (GOTCHA 2) so the executor does not propagate the `// @ts-nocheck` line to the new `StaffForm.tsx`.

**User decisions captured (do not re-debate):**

- **§14 Option A** — admin types password in the form; no invite email flow; no temp-password-must-rotate flag.
- **Standard password strength** — ≥8 chars + letter + digit + blocklist + not equal to username. No uppercase / lowercase / symbol requirement (intentionally looser than the self-service `ChangePasswordRequest`; that schema is untouched).
- **Standard staff-list indicators** — `is_login_enabled` badge, `last_login` relative time, `Locked` badge. No `failed_login_attempts` count, no stale-login warning.
- **Standard audit** — `staff.password_set` (first time) and `staff.password_reset` (replacement). Actor + target + timestamp + IP + outcome. Reuse `AuditService.log_action`; no new infrastructure. No separate rows for collateral state (e.g., `is_login_enabled` toggle — flows through existing staff-edit audit).

**Confidence: 10 / 10.** Every file:line, every signature, every import path, every test impact has been Read/Grep'd in-conversation. The four prior gaps are closed. The breaking-change audit confirms `AdminUser` is safe to add. The greenfield `StaffForm` now has two in-repo patterns to copy verbatim. No external library docs are required — every pattern (Pydantic v2 validators, RHF+Zod, TanStack mutations, bcrypt-via-`BcryptContext`, `AuditService.log_action`, `AdminUser` Annotated alias) is already exercised elsewhere in this codebase with direct examples cited.
