# 03 — Staff logins, per-user session isolation, weekly auto-login

**Request (paraphrased):**
> Staff should distinguish their own schedules. Either (a) admin adds staff with their own login, or (b) everyone is admin and toggles the schedule view. In either case, Kirill on his phone and Voss on his phone must not step on each other's view. Also: auto-persist login ~1 week (re-login Monday 8am).

**Status:** 🟡 PARTIAL — foundations exist; session duration + per-user UI state are the gaps

---

## What exists today

### Roles & multi-user login
- `Staff` model (`src/grins_platform/models/staff.py:54-93`) has `role`, `username`, `password_hash`, `is_login_enabled`.
- `StaffRole` enum = `TECH`, `SALES`, `ADMIN` (`src/grins_platform/models/enums.py:135-143`).
- `UserRole` mapped to `ADMIN`, `MANAGER`, `TECH` for API authz.
- `auth_service.py:432-448` maps staff.role → UserRole.
- Admin-create-staff endpoint at `src/grins_platform/api/v1/staff.py:250-268`.
- RBAC design: `feature-developments/multiple roles/schedule-tab-rbac-mvp.md` — TECH users see only their own appointments; ADMIN/MANAGER see all. This is enforced at the API layer.

### Session / tokens
- Access token lifetime = **60 minutes** (`auth_service.py:40`, `ACCESS_TOKEN_EXPIRE_MINUTES = 60`).
- Refresh token lifetime = **30 days** (`auth_service.py:41`, `REFRESH_TOKEN_EXPIRE_DAYS = 30`).
- Both stored as HttpOnly cookies (`api/v1/auth.py:113-133`).
- Frontend auto-refreshes 1 minute before access-token expiry via polling timer in `AuthProvider.tsx:94-116`.
- On mount, `AuthProvider.tsx:143-164` transparently restores session from refresh cookie.

### Per-user UI state
- All schedule filters (viewMode, selectedDate, selectedAppointmentId, staff filter) live in React `useState` in `frontend/src/features/schedule/components/SchedulePage.tsx:49-61`.
- No server-side "user preferences" table.

## What's missing / mismatched

1. **Session length mismatch:** user asked for ~7-day re-login; system is set to 30 days. Weekly cadence is not enforced.
2. **StaffCreate schema** (`schemas/staff.py:22-95`) doesn't appear to include `username` / `password` fields — meaning admins may not be able to set login creds at create-time from the UI. ❓
3. **create_staff endpoint** has no visible `@require_admin` — need to confirm it's actually guarded. ❓
4. **Per-user UI state isolation works by accident** today: each device has its own React state, so Kirill's and Voss's filter toggles don't cross-contaminate. But state is lost on reload, and there's no shared "my default filter set" per user.

## TODOs

- [ ] **TODO-03a** Change `REFRESH_TOKEN_EXPIRE_DAYS` from 30 → 7 (or whatever weekly cadence user confirms).
- [ ] **TODO-03b** Decide multi-user model (separate logins vs "everyone is admin"). Recommendation: keep separate logins since the infra is already in place. ❓
- [ ] **TODO-03c** Extend `StaffCreate` schema and the admin UI so an admin can set a username + temporary password when adding staff.
- [ ] **TODO-03d** Verify (and harden) that `create_staff` endpoint requires `ADMIN` role.
- [ ] **TODO-03e** Persist per-user preferences (e.g. default staff-filter selection on Schedules tab) to a `user_preferences` table so a user's setup is restored on any device, and still isolated between users.

## Clarification questions ❓

1. **Auth model:** separate logins per staff (clean RBAC), or all-admin-with-toggle (faster to ship)? Both are possible; the first is already 80% wired.
2. **Login cadence:** is 7 days the literal target, or do you want the *cookie* to last 7 days so users re-login each Monday?
3. **Where does staff get their first password?** Admin sets it and SMS/emails it? Or magic-link invite flow?
