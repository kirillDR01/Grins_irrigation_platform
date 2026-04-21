---
status: Draft proposal (pre-implementation)
date: 2026-04-21
scope: MVP — Schedule tab read-path visibility only
author: planning pass, no code changes
---

# Role-Based Schedule Visibility — MVP Plan

## Summary

Tech users see only the appointments assigned to them in the Schedule tab. Admin and Manager users continue to see everything. Read-only. Schedule tab only. No schema changes.

The auth foundation is already in place (JWT, `Staff` table as user store, `UserRole` enum, `require_admin` / `require_manager_or_admin` dependencies). The gap is that every appointment-read endpoint currently ignores the caller's identity and returns global data. This plan closes that gap with a minimum of surface area.

---

## Scope

**In scope**
- `GET` endpoints backing the Schedule tab (daily, weekly, list, single appointment, staff-daily).
- Frontend `SchedulePage` and `CalendarView` — hide admin-only controls for tech role.
- Promote currently-unauthenticated `/schedule/*` write endpoints to `ManagerOrAdminUser` (adjacent but cheap, and closes the worst blast-radius gap).

**Out of scope (parking lot, see §7)**
- Write/mutation ownership checks on appointments (`POST`, `PUT`, `PATCH`, `DELETE`, payment/invoice/estimate/review/photo endpoints).
- Other tabs: Jobs, Customers, Communications, Notifications, Billing, Dashboard widgets.
- Unscheduled-job visibility rules for tech.
- "View as tech" admin impersonation.
- Multi-role users (one staff member holding two roles simultaneously).

---

## 1. Schedule-tab endpoints to filter

Every route under `src/grins_platform/api/v1/appointments.py` that feeds the Schedule tab, plus the one `reschedule_requests` queue endpoint that currently exposes cross-staff data.

| # | Route | Function | File : line | Today's auth dep | Required change |
|---|-------|----------|-------------|------------------|-----------------|
| 1 | `GET /api/v1/appointments` | `list_appointments` | `appointments.py:138` | none | Inject `CurrentActiveUser`; if role is TECH, force `staff_id = current_user.id` and clamp any caller-supplied mismatched `staff_id`. |
| 2 | `GET /api/v1/appointments/daily/{schedule_date}` | `get_daily_schedule` | `appointments.py:238` | none | Inject `CurrentActiveUser`, filter tech results to own. |
| 3 | `GET /api/v1/appointments/staff/{staff_id}/daily/{schedule_date}` | `get_staff_daily_schedule` | `appointments.py:274` | none | Inject `CurrentActiveUser`; if tech and path `staff_id != current_user.id` → 404 (info-leak prevention). |
| 4 | `GET /api/v1/appointments/weekly` | `get_weekly_schedule` | `appointments.py:329` | none | Inject `CurrentActiveUser`, filter tech results to own. |
| 5 | `GET /api/v1/appointments/{appointment_id}` | `get_appointment` | `appointments.py:783` | none | Inject `CurrentActiveUser`; tech requesting foreign appointment → 404 (not 403). |
| 6 | `GET /api/v1/appointments/needs-review` | `list_needs_review_appointments` | `appointments.py:564` | `ManagerOrAdminUser` | Already gated — no change. |
| 7 | `GET /api/v1/schedule/reschedule-requests` | `list_reschedule_requests` | `reschedule_requests.py:81` | `CurrentActiveUser` | Promote to `ManagerOrAdminUser` for MVP (tech loses queue). |
| 8 | `GET /api/v1/schedule/lead-time` | `get_lead_time` | `schedule.py:627` | `CurrentActiveUser` | Leave as-is (aggregate capacity metric, no per-appointment PII). |

### Pseudo-diff: typical read (endpoint #2)

```python
async def get_daily_schedule(
    schedule_date: date,
    current_user: CurrentActiveUser,                            # + new
    service: Annotated[AppointmentService, Depends(get_appointment_service)],
) -> DailyScheduleResponse:
    appointments, total = await service.get_daily_schedule(
        schedule_date,
        current_user=current_user,                              # + new
        include_relationships=True,
    )
```

### Pseudo-diff: single appointment with 404-on-foreign (endpoint #5)

```python
try:
    result = await service.get_appointment(appointment_id, current_user=current_user)
except AppointmentNotFoundError as e:
    raise HTTPException(404, f"Appointment not found: {e.appointment_id}") from e
```
The service raises `AppointmentNotFoundError` in both the "row missing" and "not yours" cases — the HTTP response is identical.

---

## 2. Service-layer changes

File: `src/grins_platform/services/appointment_service.py`

Read methods that need a `current_user` kwarg:

- `list_appointments` — `appointment_service.py:789`
- `get_daily_schedule` — `appointment_service.py:824`
- `get_staff_daily_schedule` — `appointment_service.py:843` (defensive check: tech's id must match path `staff_id`)
- `get_weekly_schedule` — `appointment_service.py:879`
- `get_appointment` — `appointment_service.py:350`

### Centralized helpers

```python
def _apply_role_filter(
    self,
    query_kwargs: dict,
    current_user: Staff | None,
) -> dict:
    """If current_user is a tech, force staff_id filter to self.
    Admin/Manager/None: pass-through."""
    if current_user is None:
        return query_kwargs
    role = get_user_role(current_user)  # shared util — see below
    if role == UserRole.TECH:
        query_kwargs["staff_id"] = current_user.id
    return query_kwargs

def _filter_by_role(
    self,
    appointments: list[Appointment],
    current_user: Staff | None,
) -> list[Appointment]:
    if current_user is None:
        return appointments
    if get_user_role(current_user) == UserRole.TECH:
        return [a for a in appointments if a.staff_id == current_user.id]
    return appointments
```

For `get_appointment`, after the repo fetch:

```python
if current_user is not None and get_user_role(current_user) == UserRole.TECH:
    if appointment.staff_id != current_user.id:
        raise AppointmentNotFoundError(appointment_id)  # 404, not 403
```

### Critical: back-compat on the kwarg

Every `current_user` parameter **must default to `None`**. Internal callers (cron jobs, webhooks, `apply_schedule`, `bulk_send_confirmations`, other services) must not get accidentally role-filtered. Only API-layer callers pass a user.

### Role-mapping duplication — consolidate

`_get_user_role()` exists in two places today:
- `services/auth_service.py:432` (`AuthService.get_user_role`)
- `api/v1/auth_dependencies.py:135`

Lift into a single shared utility (suggested: `services/auth_service.py` module-level `get_user_role(staff) -> UserRole`, or a new `utils/user_role.py`). If the cleanup balloons, defer — the filtering helpers can import either location without blocking MVP.

---

## 3. Auth dependency pattern

**Use the existing `CurrentActiveUser`** (`api/v1/auth_dependencies.py:301`). It already enforces authenticated + active. No new dependency needed; filtering decisions happen inside the service based on the `Staff` object's role.

**403 vs 404 for foreign-appointment access**: use **404**.

- 403 confirms the appointment id exists, which is a minor information leak.
- 404 matches what the tech sees in the list view anyway (rows filtered out).
- Matches industry norms for private resources (GitHub, GitLab).
- Keeps endpoint code clean — one `AppointmentNotFoundError` path handles both "row missing" and "not yours".

**Unauthenticated**: unchanged — `get_current_user` (`api/v1/auth_dependencies.py:52`) already raises 401.

---

## 4. Frontend changes

Base path: `frontend/src/features/schedule/`

### Current user's role — already available

- `useAuth()` hook exposed at `frontend/src/features/auth/components/AuthProvider.tsx:222`
- `User.role: 'admin' | 'manager' | 'tech'` defined at `frontend/src/features/auth/types/index.ts:6`
- **No new state or fetch needed.**

### Hooks — no changes needed

`useDailySchedule`, `useWeeklySchedule`, `useAppointments`, `useAppointment`, `useStaffAppointments`, `useJobAppointments`, `useStaffDailySchedule` (all in `frontend/src/features/schedule/hooks/useAppointments.ts`) delegate to `appointmentApi`, which hits the now-filtered backend. The server enforces truth; the client just re-renders what it gets. Less client/server drift.

### `SchedulePage.tsx` — hide admin-only controls

Read `const { user } = useAuth(); const isTech = user?.role === 'tech';` and gate:

- `"Add Jobs"` button — `SchedulePage.tsx:361-369`
- `"New Appointment"` button — `SchedulePage.tsx:373-380`
- `ClearDayButton` — `SchedulePage.tsx:332-336`
- `SendAllConfirmationsButton` — `SchedulePage.tsx:370-372`
- `RescheduleRequestsQueue`, `NoReplyReviewQueue` — `SchedulePage.tsx:413-420`
- `RecentlyClearedSection` — `SchedulePage.tsx:423`

### `CalendarView.tsx` — disable drag-drop for tech

- Drag-drop reschedule fires `useUpdateAppointment`. Set `editable={!isTech}` on the FullCalendar instance. Backend will 403 on mutations regardless, but pre-empt in the UI so tech never sees a phantom rollback.
- `useStaff({ page_size: 100 })` at `CalendarView.tsx:80` powers color coding. Tech never sees other staff's events, so the fetch is a minor waste — safe to leave in MVP; optional follow-up to gate with `!isTech`.

### `AppointmentList.tsx`

No staff filter exists in this component today (status + date only — `AppointmentList.tsx:42-50`, `253-298`). Backend filter handles rows. No change.

### Bulk-assign modals

`JobPickerPopup.tsx`, `JobSelector.tsx` — entered from buttons we already hide. Gate the whole render behind `!isTech` as belt-and-suspenders.

### "Ghost cell" decision

**Hide other staff's appointments entirely for MVP.**
- Reason 1: rendering them shaded requires sending their data to the client, recreating the exact info-leak the plan closes.
- Reason 2: conflict detection is moot because tech can't create appointments.
- If the future UX needs it, add a lightweight `GET /api/v1/schedule/busy-slots/{date}` returning anonymized `(start, end)` tuples.

---

## 5. Tests

### Existing tests that will need fixture updates

These assume unfiltered data; add an admin-role user fixture so behavior is preserved:

- `src/grins_platform/tests/integration/test_appointment_integration.py`
- `src/grins_platform/tests/unit/test_schedule_appointment_api.py`
- `src/grins_platform/tests/unit/test_send_confirmation.py`
- `src/grins_platform/tests/unit/test_bulk_send_confirmations.py`
- `src/grins_platform/tests/functional/test_no_reply_review_functional.py`
- `src/grins_platform/tests/test_appointment_service.py` (service level — add `current_user=None` assertion to preserve back-compat)

### New tests

Create `src/grins_platform/tests/integration/test_schedule_role_visibility.py`:

```
test_tech_sees_only_own_appointments_daily
test_tech_sees_only_own_appointments_weekly
test_tech_list_appointments_forces_own_staff_id
test_admin_sees_all_appointments
test_manager_sees_all_appointments
test_tech_gets_404_for_other_staffs_appointment
test_tech_gets_404_via_staff_daily_for_other_staff
test_tech_accessing_own_staff_daily_returns_200
test_unauthenticated_gets_401
```

### Frontend tests

- Extend `SchedulePage.test.tsx`: mock `useAuth()` with each role; assert presence/absence of the six controls listed in §4.
- New case in `AppointmentDetail.test.tsx`: 404 → friendly "Appointment not found" message.

---

## 6. Schema

**No changes required for MVP.** `Appointment.staff_id` is already FK-indexed via the declaration at `models/appointment.py:105`.

**Optional follow-up** (not required): composite index `(staff_id, scheduled_date)` would help tech-scoped daily/weekly queries once the table grows past ~100k rows. Add an Alembic migration when p95 regresses — not before.

---

## 7. Parking lot — mutations that remain unprotected

These accept `CurrentActiveUser` but don't verify resource ownership. A tech hitting the API directly (bypassing the UI) could modify other staff's data. Prioritized by damage potential.

| Endpoint | File : line | Damage if abused by tech |
|---|---|---|
| `POST /api/v1/appointments` | `appointments.py:457` | **High** — create appointments for any staff on any job. |
| `PUT /api/v1/appointments/{id}` | `appointments.py:817` | **High** — reschedule, reassign staff_id, mutate status on anyone's appointment. |
| `DELETE /api/v1/appointments/{id}` | `appointments.py:875` | **High** — cancel anyone's appointment (fires cancellation SMS). |
| `PATCH /api/v1/appointments/{id}/reschedule` | `appointments.py:983` | **High** — drag-drop reschedule. |
| `POST /api/v1/appointments/{id}/collect-payment` | `appointments.py:1119` | **High** — record payment on any appointment. |
| `POST /api/v1/appointments/{id}/create-invoice` | `appointments.py:1171` | **Medium** — mint invoice for any job. |
| `POST /api/v1/appointments/{id}/create-estimate` | `appointments.py:1227` | **Medium** — same. |
| `POST /api/v1/appointments/{id}/photos` | `appointments.py:1286` | **Low** — upload photo to someone else's appointment. |
| `POST /api/v1/appointments/{id}/request-review` | `appointments.py:1405` | **Medium** — sends review SMS; burns 30-day dedup window. |
| `POST /api/v1/appointments/{id}/send-confirmation` | `appointments.py:931` | **Medium** — fires Y/R/C SMS. |
| `POST /api/v1/appointments/send-confirmations` (bulk) | `appointments.py:511` | **High** — bulk SMS blast. |
| `POST /api/v1/schedule/apply` | `schedule.py:486` | **Critical** — rewrites an entire day's schedule. No auth at all today. |
| `POST /api/v1/schedule/insert-emergency` | `schedule.py:215` | **Critical** — admin-only planning op; no auth. |
| `POST /api/v1/schedule/generate` | `schedule.py:119` | **Critical** — no auth. |
| `POST /api/v1/schedule/re-optimize` | `schedule.py:252` | **Critical** — no auth. |

**Phase 2 sequencing**: `/schedule/*` admin ops first, then appointment PUT/DELETE/PATCH, then payment/invoice/estimate trio.

---

## 8. Open questions (decide before PR 1 merges)

1. **Tech and unscheduled jobs** — should a tech see unscheduled jobs anywhere (e.g. AppointmentForm job picker)? Recommend no — they can't create appointments anyway.
2. **Dashboard "today's count" widget** — `GET /api/v1/dashboard/today-schedule` (`dashboard.py:217`) and `/metrics` (`dashboard.py:56`) aggregate all staff today. Tech's dashboard should show: (a) their count, (b) team count, or (c) hidden? Out of Schedule-tab MVP but will be the next complaint.
3. **Single login vs separate** — same `/login` form, or a separate `/tech-login`? Recommend single login, diverge on post-login route based on role.
4. **"View as tech" admin impersonation** — defer past MVP; cheap to build later via `?as_staff_id=<uuid>` override gated by admin.
5. **Tech fieldwork actions** — tech needs to mark their own appointments arrived/completed. Out of MVP (read-only) but flag as PR 3 priority.
6. **Queues for tech (Reschedule Requests, No-Reply Review)** — recommend hidden entirely in MVP by promoting endpoints to `ManagerOrAdminUser`. Some orgs may eventually want tech to see reschedule requests for their own jobs only — note and defer.

---

## 9. Phased delivery

### PR 1 — Backend read-path filtering + endpoint auth

- Add `current_user` kwarg to 5 read methods on `AppointmentService` (defaults to `None`).
- Add `_apply_role_filter` / `_filter_by_role` helpers on the service.
- Lift `get_user_role` into a shared util (or import the existing one consistently).
- Wire `CurrentActiveUser` into the 5 appointment GET endpoints listed in §1.
- Promote `/api/v1/schedule/reschedule-requests` to `ManagerOrAdminUser`.
- **Bonus, same PR**: add `ManagerOrAdminUser` guard to every unprotected `/schedule/*` write endpoint (`schedule.py:119, 215, 252, 486`). Not strictly on the Schedule read path but the single highest-leverage change in this plan — closes the worst unauthenticated surface.
- New test suite + update existing fixtures.
- No UI changes yet. Admin/manager UX unchanged. Tech login works but still sees admin-only controls (which will now fail with 401/403 on click).

### PR 2 — Frontend role-aware Schedule tab

- Consume `useAuth().user.role` in `SchedulePage.tsx` and `CalendarView.tsx`.
- Hide the six admin-only controls from §4.
- Disable drag-drop for tech.
- Frontend role tests (`SchedulePage.test.tsx`).
- Shippable standalone: after merge, tech sees a clean read-only Schedule tab.

### PR 3 (out of MVP, sequenced next)

- `Appointment.staff_id == current_user.id` ownership checks on PUT/PATCH/DELETE and on-site ops (payment, invoice, estimate, review, photos, confirmation send).
- Bulk endpoints (`apply_schedule`, `bulk_send_confirmations`) get a product call: row-level ownership or admin-only wholesale?

---

## 10. Effort and risk

| Phase | Effort | Risk |
|---|---|---|
| PR 1 (backend) | 1.5–2 days | **Medium**. The `current_user=None` back-compat is the subtle one — a service-layer caller that forgets the kwarg won't be caught by the type system and will silently over-filter. Mitigation: pytest sweep every public service method with `current_user=None` asserting unfiltered behavior; CI grep for `.list_appointments(` calls from API files missing the kwarg. |
| PR 2 (frontend) | 0.5–1 day | **Low**. Straightforward conditional rendering against a single role boolean. |
| PR 3 (write path, out of MVP) | 2–3 days | **High**. Bulk endpoints and unprotected `/schedule/*` ops each have their own shape of ownership question. Product decisions required. |

### Red flag

`apply_schedule` at `schedule.py:486` is completely unauthenticated today (no `CurrentActiveUser` dep). Even if "admin ships first, tech ships later" is the framing, the write path has to be audited eventually. Folding a `ManagerOrAdminUser` guard onto every `/schedule/*` route into PR 1 is the single highest-leverage change in this plan — worth including even though it's technically adjacent to the read-only Schedule-tab MVP.

---

## Critical files (quick reference)

- Backend
  - `src/grins_platform/api/v1/appointments.py`
  - `src/grins_platform/api/v1/schedule.py`
  - `src/grins_platform/api/v1/reschedule_requests.py`
  - `src/grins_platform/api/v1/auth_dependencies.py`
  - `src/grins_platform/services/appointment_service.py`
  - `src/grins_platform/services/auth_service.py`
  - `src/grins_platform/models/staff.py`
  - `src/grins_platform/models/appointment.py`
  - `src/grins_platform/models/enums.py`
- Frontend
  - `frontend/src/features/schedule/components/SchedulePage.tsx`
  - `frontend/src/features/schedule/components/CalendarView.tsx`
  - `frontend/src/features/schedule/hooks/useAppointments.ts`
  - `frontend/src/features/auth/components/AuthProvider.tsx`
  - `frontend/src/features/auth/types/index.ts`
- Tests
  - `src/grins_platform/tests/integration/test_schedule_role_visibility.py` (new)
  - Existing appointment suites listed in §5
