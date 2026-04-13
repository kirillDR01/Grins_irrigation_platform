# Session Timeout Bug Investigation

**Date:** 2026-04-11
**Requirement:** 2.1, 2.2, 2.3
**Symptom:** Premature logout during normal platform usage

## Root Cause Analysis

### Bug 1: Stale Authorization Header After Interceptor Refresh (PRIMARY)

**Location:** `frontend/src/core/api/client.ts` (response interceptor) + `frontend/src/features/auth/components/AuthProvider.tsx`

**Mechanism:**

1. On login, `AuthProvider` stores the access token in React state and sets `apiClient.defaults.headers.common['Authorization'] = 'Bearer <token>'`.
2. The access token expires after 60 minutes. The `AuthProvider` schedules a proactive refresh at 59 minutes via `setTimeout`.
3. If the browser tab is backgrounded or the computer sleeps, `setTimeout` is suspended. The timer fires late — after the token has already expired.
4. The next API call sends the stale `Authorization` header, gets a 401.
5. The axios response interceptor catches the 401 and calls `POST /auth/refresh`. This succeeds — the backend sets a fresh `access_token` cookie.
6. The interceptor retries the original request. **However**, the retry still sends the stale `Authorization: Bearer <expired_token>` header from `apiClient.defaults.headers.common`.
7. The backend `get_current_user` dependency checks the Authorization header **first**, finds the expired token, and returns 401 again.
8. This second 401 hits the interceptor, but the URL is the original request (not `/auth/refresh`), so it tries to refresh again — but `isRefreshing` is now false (it was reset), so it enters a refresh loop.
9. Eventually the refresh itself may fail or the user gets redirected to `/login?reason=session_expired`.

**Why the cookie fallback doesn't help:** The `get_current_user` function in `auth_dependencies.py` checks `credentials` (from the Authorization header) first. Only if `credentials is None` does it fall back to the cookie. Since `AuthProvider` always sets the Authorization header, the cookie is never used after login.

### Bug 2: Timer Not Rescheduled After Interceptor Refresh

**Location:** `frontend/src/core/api/client.ts` (response interceptor)

The axios interceptor performs a silent refresh but does not notify `AuthProvider` to reschedule the proactive refresh timer. After the first interceptor-based refresh, no further proactive refreshes are scheduled, making the system entirely dependent on the reactive 401-based refresh path — which is broken by Bug 1.

### Bug 3: CSRF Cookie Loss on Cross-Origin Deployments (SECONDARY)

**Location:** `src/grins_platform/middleware/csrf.py` + `src/grins_platform/api/v1/auth.py`

In production (Vercel frontend + Railway backend), cookies use `SameSite=None; Secure`. Modern browsers increasingly block third-party cookies. If the CSRF cookie is blocked:
- State-changing requests (POST/PUT/DELETE/PATCH) fail with 403 from CSRF middleware.
- The frontend does not handle 403 as an auth error — it just logs "Access forbidden" and rejects the promise.
- The user sees silent failures on all mutations, which may appear as "the app is broken" rather than a clear logout.

This is a secondary issue that only affects cross-origin production deployments.

## Fix Applied

### Fix for Bug 1: Update Authorization header after interceptor refresh

In `frontend/src/core/api/client.ts`, after a successful refresh, extract the new access token from the response and update `apiClient.defaults.headers.common['Authorization']`. Also dispatch a custom event so `AuthProvider` can update its state and reschedule the timer.

### Fix for Bug 2: Reschedule timer via custom event

`AuthProvider` listens for a `'token-refreshed'` custom event dispatched by the interceptor. On receiving it, it updates its internal state and reschedules the proactive refresh timer.

### No change to token expiry values

The existing 60-minute access / 30-day refresh configuration is correct and does not need adjustment. The premature logout was caused by the stale header bug, not by timeout values.
