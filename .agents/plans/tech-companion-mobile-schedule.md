# Feature: Tech Companion — Phone-Only Schedule View

The following plan is intended to be executed top-to-bottom. Every external reference (file, line number, symbol name) was verified against the `dev` branch on 2026-05-01 by recon. If a referenced line has shifted, locate by symbol name and update — but do not invent fields, types, or relationships.

## Feature Description

A phone-only landing surface for technicians. When a user with `role === 'tech'` logs in from a phone-sized viewport, they are redirected to `/tech` and rendered inside a dedicated `<TechMobileLayout>` (no admin sidebar, no bottom nav). The page shows the tech's day as a vertical stack of job cards — customer name, job type, address, time window, status chips, and a "Job details" button. Tapping the button opens the **existing** `AppointmentModal` unchanged. On non-phone viewports (tablet/desktop), techs see a friendly "Open this on your phone" landing.

The visual reference is `feature-developments/design_handoff_tech_companion_flow/`, but only the **Schedule tab** is in scope. Alerts, Co-pilot, "Me", drive-time dividers, header DRIVE stat, tactical-alerts engine, bottom nav, and any modal redesign are **explicitly out of scope**.

## User Story

As a **technician using my phone in the field**
I want to **see today's appointments stacked as tappable cards the moment I open the app**
So that **I can move through my day without navigating an admin UI built for desktops**.

## Problem Statement

The platform's only authenticated landing today is `/dashboard`, which uses `Layout.tsx`'s desktop sidebar and admin metrics. There is no role-aware or viewport-aware entry point. A technician opening the platform on their phone gets a layout that doesn't fit the screen and surfaces information they can't act on.

## Solution Statement

Gate a new tech-mobile surface on **two criteria simultaneously**: (1) `user.role === 'tech'` and (2) viewport is phone-sized (`max-width: 639px`, matching just below Tailwind's `sm` breakpoint at 640px). Enforced by:

- A login-time redirect: `LoginPage` reads role from the `LoginResponse` and routes techs to `/tech` instead of the default `/`.
- A new `<TechMobileLayout>` route group at `/tech` (sibling to the existing admin layout — NOT nested inside it).
- A `<PhoneOnlyGate>` inner wrapper that renders the schedule view only on phones; otherwise renders an "Open this on your phone" landing with a sign-out button.

The schedule view consumes the existing `useStaffDailySchedule(staffId, date)` hook. The card's data needs (street address, city, state, zip, zone count, system type) require a small backend extension: add `property_summary` to the appointment row via a `selectinload(Appointment.job).selectinload(Job.job_property)` chain.

Tapping "Job details" mounts the existing `AppointmentModal` exactly as `SchedulePage.tsx` does — no `variant` prop, no fork.

## Feature Metadata

**Feature Type**: New Capability
**Estimated Complexity**: Medium
**Primary Systems Affected**:
- Frontend (new slice): `frontend/src/features/tech-mobile/`
- Frontend (touched): `core/router/index.tsx`, `features/auth/components/LoginPage.tsx`, `features/auth/components/AuthProvider.tsx`, `features/auth/types/index.ts`, `features/schedule/types/index.ts`
- Backend (touched): `src/grins_platform/services/appointment_service.py`, `src/grins_platform/repositories/appointment_repository.py`, `src/grins_platform/schemas/appointment.py`
- Tooling (new): `scripts/seed_tech_companion_appointments.py`, `e2e/tech-companion-mobile.sh`
**Dependencies**: None new — uses existing `useMediaQuery`, `ProtectedRoute`, `AppointmentModal`, `useStaffDailySchedule`, Tailwind v4, lucide-react, agent-browser CLI.

---

## CONTEXT REFERENCES

### Verified Codebase Facts (read these before implementing)

**Auth model — there is NO separate `User` table.** `Staff` is the auth principal. The frontend `User.id` IS the staff `id`, so `useStaffDailySchedule(user.id, today)` is correct without translation. Confirmed:
- `src/grins_platform/models/staff.py:80-107` — `Staff` carries `username`, `password_hash`, `is_login_enabled`, `role` directly.
- `frontend/src/features/auth/types/index.ts:8-15`:
  ```ts
  export interface User {
    id: string;
    username: string;
    name: string;
    email: string | null;
    role: UserRole;       // 'admin' | 'manager' | 'tech'
    is_active: boolean;
  }
  ```

**Property model fields (verbatim).** `src/grins_platform/models/property.py:83-102`:
```python
address: Mapped[str] = mapped_column(String(255), nullable=False)        # NOT street_address
city: Mapped[str] = mapped_column(String(100), nullable=False)
state: Mapped[str] = mapped_column(String(50), nullable=False, default="MN")
zip_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
zone_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
system_type: Mapped[str] = mapped_column(String(20), nullable=False, default=SystemType.STANDARD.value)
```

**Job → Property relationship name is `job_property`** (NOT `property`). `src/grins_platform/models/job.py:286-289`:
```python
job_property: Mapped["Property | None"] = relationship("Property", back_populates="jobs")
```

**Daily schedule loading pattern uses `selectinload`** (NOT `joinedload`). Repository at `src/grins_platform/repositories/appointment_repository.py:411-431`:
```python
stmt = (
    select(Appointment)
    .where(Appointment.staff_id == staff_id)
    .where(Appointment.scheduled_date == schedule_date)
    .order_by(Appointment.route_order.asc().nullslast(), Appointment.time_window_start.asc())
)
if include_relationships:
    stmt = stmt.options(
        selectinload(Appointment.job).selectinload(Job.customer),
        selectinload(Appointment.staff),
    )
```

**Service signature.** `src/grins_platform/services/appointment_service.py:876`:
```python
async def get_staff_daily_schedule(
    self, staff_id: UUID, schedule_date: date, include_relationships: bool = False,
) -> tuple[list[Appointment], int, int]:
```

**`AuthProvider.login` does not currently return a value.** `frontend/src/features/auth/components/AuthProvider.tsx:185-191`:
```ts
const login = useCallback(
  async (credentials: LoginRequest) => {
    const response = await authApi.login(credentials);
    setAuthState(response);
  },
  [setAuthState]
);
```
**This must change to return the `LoginResponse`** so `LoginPage` can branch on role without racing the context update. `LoginResponse` (types/index.ts:23-29) carries `user: User`.

**`ProtectedRoute` with `allowedRoles` mismatch renders `<AccessDenied />`** (NOT a redirect). `frontend/src/features/auth/components/ProtectedRoute.tsx:61-85` plus `AccessDenied` at lines 28-42. Implication: a tech must be redirected at the route boundary; we do not rely on `ProtectedRoute` to bounce admins.

**Tailwind path alias.** `frontend/tsconfig.app.json:28-32` and `frontend/vite.config.ts:10-12` confirm `@/* → ./src/*`. Use `@/` imports.

**`cn` helper.** `frontend/src/lib/utils.ts:1-6` — `clsx` + `twMerge`. Use this; do not introduce alternatives.

**`useMediaQuery` signature.** `frontend/src/shared/hooks/useMediaQuery.ts:16` — `useMediaQuery(query: string): boolean`, SSR-safe.

**`AppointmentModal` props** (`frontend/src/features/schedule/components/AppointmentModal/AppointmentModal.tsx:71-76`):
```ts
interface AppointmentModalProps {
  appointmentId: string;
  open: boolean;
  onClose: () => void;
  onEdit?: (appointment: Appointment) => void;
}
```
Mounted in `frontend/src/features/schedule/components/SchedulePage.tsx:558-563` — copy that mounting pattern verbatim.

**`appointmentStatusConfig`** at `frontend/src/features/schedule/types/index.ts:161-210`. Use it for status pill colors.

**Agent-browser CLI** is installed and used by existing E2E scripts. Commands: `agent-browser open <url>`, `snapshot -i`, `click @e1`, `fill <selector> "text"`, `screenshot <path>`, `set viewport W H`, `wait --load networkidle`, `console`, `errors`. Sessions via `--session <name>`. Default E2E creds: `E2E_USER=admin`, `E2E_PASS=admin123`. Default base URL is the Vercel preview unless `BASE` env is set; for local validation set `BASE=http://localhost:5173`. Reference: `e2e/payment-links-flow.sh`, `e2e/schedule-resource-timeline.sh`. Screenshots go to `e2e-screenshots/<feature-name>/`.

**Test fixture for tech staff.** `src/grins_platform/tests/integration/fixtures.py:90-107` — pattern for creating a `MagicMock` staff with `role=StaffRole.TECH.value`, `is_login_enabled=True`, `password_hash="$2b$12$test_hash"`. **This is for unit tests only.** Real seed data (with a hashed password we can actually log in with) needs a new script.

**Existing seed script pattern** — per-feature, in `scripts/`. Examples: `scripts/seed_resource_timeline_test_data.py`, `scripts/seed_e2e_payment_links.py`. They use the async session, upsert by a stable key, log what they created.

### New Files to Create

Frontend slice:
- `frontend/src/features/tech-mobile/index.ts`
- `frontend/src/features/tech-mobile/components/TechMobileLayout.tsx`
- `frontend/src/features/tech-mobile/components/PhoneOnlyGate.tsx`
- `frontend/src/features/tech-mobile/components/OpenOnPhoneLanding.tsx`
- `frontend/src/features/tech-mobile/components/TechHeader.tsx`
- `frontend/src/features/tech-mobile/components/TechSchedulePage.tsx`
- `frontend/src/features/tech-mobile/components/MobileJobCard.tsx`
- `frontend/src/features/tech-mobile/utils/cardState.ts`
- `frontend/src/features/tech-mobile/utils/mapsLink.ts`
- `frontend/src/features/tech-mobile/utils/formatTimeWindow.ts`

Frontend tests:
- `frontend/src/features/tech-mobile/utils/cardState.test.ts`
- `frontend/src/features/tech-mobile/utils/mapsLink.test.ts`
- `frontend/src/features/tech-mobile/utils/formatTimeWindow.test.ts`
- `frontend/src/features/tech-mobile/components/MobileJobCard.test.tsx`
- `frontend/src/features/tech-mobile/components/TechSchedulePage.test.tsx`

Tooling:
- `scripts/seed_tech_companion_appointments.py` — idempotent seed of 3 tech logins + Customer/Property/Job/Appointment chains.
- `e2e/tech-companion-mobile.sh` — agent-browser journey, screenshots to `e2e-screenshots/tech-companion-mobile/`.

### Patterns to Follow

**Feature slice layout** (`.kiro/steering/structure.md` and `frontend-patterns.md`):
- `features/tech-mobile/{components,utils}/` with a public `index.ts`.
- Cross-feature imports only via folder index files. Import `AppointmentModal` from `@/features/schedule/components/AppointmentModal` (the index), not from the `.tsx` directly.

**Component naming**: PascalCase files, colocated `*.test.tsx`.

**Conditional class composition**: `cn()` from `@/lib/utils`.

**Modal mount pattern** — mirror `SchedulePage.tsx:558-563` exactly:
```tsx
const [openAppointmentId, setOpenAppointmentId] = useState<string | null>(null);
{openAppointmentId && (
  <AppointmentModal
    appointmentId={openAppointmentId}
    open={!!openAppointmentId}
    onClose={() => setOpenAppointmentId(null)}
  />
)}
```

**Tailwind translations** (from the design handoff):
- `bg-slate-900` (header ink), `bg-slate-50` (page canvas), `bg-white` (card), `bg-slate-100` (chip default), `bg-amber-50 text-amber-700` (chip warn), `border-slate-200` (default), `border-teal-500` + `shadow-[0_6px_20px_rgba(20,184,166,0.18)]` (current emphasis), `text-teal-700` (active), `bg-teal-600 text-white` (primary), `bg-green-50 text-green-700` (complete pill), `font-mono` (time strings — Tailwind default mono, do NOT add JetBrains Mono).

**Anti-patterns to avoid**:
- Do NOT modify `AppointmentModal` or any of its children.
- Do NOT add custom Tailwind theme entries (palette already in `index.css`).
- Do NOT introduce JetBrains Mono — use `font-mono`.
- Do NOT invent `street_address` / `water_source`; use `address` / `system_type`.
- Do NOT use `Job.property` — the relationship is named `job_property`.
- Do NOT use `joinedload` — the codebase uses `selectinload`.
- Do NOT delete/modify `features/resource-mobile/`.
- Do NOT introduce drive-time dividers, alerts/co-pilot/me tabs, or a bottom nav.

---

## IMPLEMENTATION PLAN

### Phase 1: Backend — Extend daily-schedule response with `property_summary`

The current `Appointment` row carries `customer_name` and `job_type` but not address / zone count / water source. Cards need this data. Extend the staff-daily-schedule chain end-to-end.

### Phase 2: Frontend type + slice scaffolding

Add the `PropertySummary` interface to the schedule types. Stand up the `features/tech-mobile/` directory with the layout shell and viewport gate.

### Phase 3: Schedule view + per-card component

Implement `TechHeader`, `MobileJobCard`, `TechSchedulePage` with three card states (current / upcoming / complete) driven from `Appointment.status`.

### Phase 4: Routing + login redirect

Insert `/tech` as a top-level sibling route (NOT inside the admin layout). Modify `AuthProvider.login` to return the `LoginResponse`. Modify `LoginPage` to branch on role. Add a small `<PostLoginRedirect>` for the `/` index route.

### Phase 5: Seed today's appointments for the existing dev techs

The dev DB already has three tech-role Staff rows with login enabled (seeded via migration `20250626_100000_seed_demo_data.py`):

| Username | Name | Role | Password (plaintext) |
|---|---|---|---|
| `vas` | Vas Grin | tech | `tech123` |
| `steven` | Steven Miller | tech | `tech123` |
| `vitallik` | Vitallik Petrov | tech | `tech123` |

(A fourth tech, "Viktor Sr", exists with `is_login_enabled=False` — skip for E2E.)

Idempotent seed script that **does NOT create staff** — it only ensures these three existing techs have distinct daily schedules so per-tech isolation can be E2E-verified. **This is required for the E2E pass.**

### Phase 6: Unit + component tests

Vitest coverage for utils and components.

### Phase 7: End-to-end agent-browser validation

Bash script driving real browser journeys with screenshots at every step. **Mandatory** — this plan is not complete until the E2E run passes and the screenshot set is generated.

---

## STEP-BY-STEP TASKS

Execute in order. Each task has an executable validation command.

### 1. UPDATE `src/grins_platform/schemas/appointment.py` — add `PropertySummary`

- **IMPLEMENT**:
  ```python
  class PropertySummary(BaseModel):
      model_config = ConfigDict(from_attributes=True)
      address: str
      city: str
      state: str
      zip_code: str | None = None
      zone_count: int | None = None
      system_type: str | None = None
  ```
  Add `property_summary: PropertySummary | None = None` to the schema used as the appointment row inside `StaffDailyScheduleResponse`. Find that schema by searching the file for the response definition and adding the field at the bottom of the field list.
- **PATTERN**: Mirror existing Pydantic v2 conventions in this file (`ConfigDict(from_attributes=True)` for ORM-mapped models).
- **GOTCHA**: Default to `None` so existing tests/consumers are unaffected.
- **VALIDATE**: `uv run ruff check src/grins_platform/schemas/appointment.py && uv run mypy src/grins_platform/schemas/appointment.py`

### 2. UPDATE `src/grins_platform/repositories/appointment_repository.py` — extend the eager-load chain

- **IMPLEMENT**: In `get_staff_daily_schedule`, when `include_relationships=True`, add `selectinload(Job.job_property)` to the chain so `Appointment.job.job_property` is populated:
  ```python
  if include_relationships:
      stmt = stmt.options(
          selectinload(Appointment.job).selectinload(Job.customer),
          selectinload(Appointment.job).selectinload(Job.job_property),
          selectinload(Appointment.staff),
      )
  ```
- **PATTERN**: Existing `selectinload` chain at lines 423-425. Use the relationship name `job_property` (verified at `models/job.py:286`).
- **GOTCHA**: Do NOT use `joinedload` — this codebase uses `selectinload` consistently.
- **VALIDATE**: `uv run ruff check src/grins_platform/repositories/appointment_repository.py && uv run mypy src/grins_platform/repositories/appointment_repository.py`

### 3. UPDATE `src/grins_platform/services/appointment_service.py` — populate `property_summary`

- **IMPLEMENT**: In `get_staff_daily_schedule`, set `include_relationships=True` when callers come from the staff-daily endpoint (or always — there is no other consumer). For each `Appointment` returned, build a `PropertySummary` from `appointment.job.job_property` if both are non-null, else `None`. Attach it to the response row.
- **GOTCHA**: The function returns `tuple[list[Appointment], int, int]` today — those `Appointment` objects are ORM rows, not DTOs. The DTO assembly happens in the API layer. Inspect `src/grins_platform/api/v1/appointments.py:293-299` to find the response builder and add the `property_summary` mapping there.
- **VALIDATE**: `uv run ruff check src/grins_platform/services/appointment_service.py src/grins_platform/api/v1/appointments.py && uv run mypy src/grins_platform/services/`

### 4. ADD pytest case for `property_summary`

- **IMPLEMENT**: New test in `src/grins_platform/tests/integration/test_appointment_service.py` (or sibling) asserting that a tech's daily schedule response includes `property_summary` for appointments whose Job has a Property, and `None` when it doesn't.
- **PATTERN**: Mirror existing service-integration tests in `src/grins_platform/tests/integration/`.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/integration/ -v -k "staff_daily or property_summary"`

### 5. UPDATE `frontend/src/features/schedule/types/index.ts` — add `PropertySummary` and field on `Appointment`

- **IMPLEMENT**:
  ```ts
  export interface PropertySummary {
    address: string;
    city: string;
    state: string;
    zip_code: string | null;
    zone_count: number | null;
    system_type: string | null;
  }
  ```
  Add `property_summary?: PropertySummary | null` to the `Appointment` interface (lines 53-80).
- **GOTCHA**: API returns `null` (not `undefined`); the union must be `| null`. The leading `?` makes the field optional in test/mock contexts.
- **VALIDATE**: `cd frontend && npm run typecheck`

### 6. CREATE `frontend/src/features/tech-mobile/utils/cardState.ts`

- **IMPLEMENT**:
  ```ts
  import type { AppointmentStatus } from '@/features/schedule/types';
  export type CardState = 'current' | 'upcoming' | 'complete' | 'hidden';
  export function deriveCardState(status: AppointmentStatus): CardState {
    if (status === 'in_progress') return 'current';
    if (status === 'completed') return 'complete';
    if (status === 'cancelled' || status === 'no_show') return 'hidden';
    return 'upcoming';
  }
  ```
- **VALIDATE**: `cd frontend && npm run typecheck`

### 7. CREATE `frontend/src/features/tech-mobile/utils/cardState.test.ts`

- **IMPLEMENT**: One assertion per `AppointmentStatus` literal so an enum widening forces a test break.
- **VALIDATE**: `cd frontend && npx vitest run src/features/tech-mobile/utils/cardState.test.ts`

### 8. CREATE `frontend/src/features/tech-mobile/utils/mapsLink.ts`

- **IMPLEMENT**:
  ```ts
  export function buildMapsUrl(address: string): string {
    const q = encodeURIComponent(address);
    if (typeof navigator !== 'undefined' && /iPhone|iPad|iPod/i.test(navigator.userAgent)) {
      return `https://maps.apple.com/?daddr=${q}`;
    }
    return `https://www.google.com/maps/dir/?api=1&destination=${q}`;
  }
  ```
- **VALIDATE**: `cd frontend && npm run typecheck`

### 9. CREATE `frontend/src/features/tech-mobile/utils/mapsLink.test.ts`

- **IMPLEMENT**: Mock iOS UA with `Object.defineProperty(navigator, 'userAgent', { value: 'iPhone', configurable: true })`; assert iOS branch. Restore default UA; assert Google branch. Assert URL encoding for spaces and commas.
- **VALIDATE**: `cd frontend && npx vitest run src/features/tech-mobile/utils/mapsLink.test.ts`

### 10. CREATE `frontend/src/features/tech-mobile/utils/formatTimeWindow.ts`

- **IMPLEMENT**:
  ```ts
  export function formatTimeWindow(start: string, end: string): string {
    return `${formatHHMMSS(start)} – ${formatHHMMSS(end)}`;
  }
  function formatHHMMSS(hms: string): string {
    const [hStr, mStr] = hms.split(':');
    const h = Number.parseInt(hStr, 10);
    const m = Number.parseInt(mStr, 10);
    const period = h >= 12 ? 'PM' : 'AM';
    const h12 = h % 12 === 0 ? 12 : h % 12;
    return m === 0 ? `${h12}:00 ${period}` : `${h12}:${m.toString().padStart(2, '0')} ${period}`;
  }
  ```
- **GOTCHA**: API returns `HH:MM:SS` strings. Do not import `date-fns` for this — string ops are fine and avoid timezone surprises.
- **VALIDATE**: `cd frontend && npm run typecheck`

### 11. CREATE `frontend/src/features/tech-mobile/utils/formatTimeWindow.test.ts`

- **IMPLEMENT**: Tests for `'08:00:00'/'09:25:00'` → `'8:00 AM – 9:25 AM'`, `'13:00:00'/'14:15:00'` → `'1:00 PM – 2:15 PM'`, midnight, noon, edge cases.
- **VALIDATE**: `cd frontend && npx vitest run src/features/tech-mobile/utils/formatTimeWindow.test.ts`

### 12. CREATE `frontend/src/features/tech-mobile/components/OpenOnPhoneLanding.tsx`

- **IMPLEMENT**: Centered card on a `bg-slate-50` full-height background (`min-h-screen flex items-center justify-center px-6`). Headline: "Open this on your phone." Body: "The technician view is designed for phone-sized screens. Sign in from your phone to continue." Include a "Sign out" button calling `useAuth().logout`.
- **IMPORTS**: `useAuth` from `@/features/auth/components/AuthProvider`; `Smartphone` icon from `lucide-react`.
- **VALIDATE**: `cd frontend && npm run typecheck && npm run lint`

### 13. CREATE `frontend/src/features/tech-mobile/components/PhoneOnlyGate.tsx`

- **IMPLEMENT**:
  ```tsx
  import type { ReactNode } from 'react';
  import { useMediaQuery } from '@/shared/hooks/useMediaQuery';
  import { OpenOnPhoneLanding } from './OpenOnPhoneLanding';
  export function PhoneOnlyGate({ children }: { children: ReactNode }) {
    const isPhone = useMediaQuery('(max-width: 639px)');
    return isPhone ? <>{children}</> : <OpenOnPhoneLanding />;
  }
  ```
- **VALIDATE**: `cd frontend && npm run typecheck`

### 14. CREATE `frontend/src/features/tech-mobile/components/TechMobileLayout.tsx`

- **IMPLEMENT**:
  ```tsx
  import { Outlet } from 'react-router-dom';
  import { PhoneOnlyGate } from './PhoneOnlyGate';
  export function TechMobileLayout() {
    return (
      <div className="min-h-screen bg-slate-50">
        <PhoneOnlyGate>
          <Outlet />
        </PhoneOnlyGate>
      </div>
    );
  }
  ```
- **VALIDATE**: `cd frontend && npm run typecheck`

### 15. CREATE `frontend/src/features/tech-mobile/components/TechHeader.tsx`

- **IMPLEMENT**: `bg-slate-900 text-white px-5 pt-4 pb-4`. Top: greeting eyebrow (`text-xs text-slate-300 font-medium`) + user name (`text-xl font-bold mt-0.5`). Bottom row: calendar icon + formatted date on left; right shows a single "JOBS" stat (mono numeric value `text-lg font-bold font-mono`, label below `text-[10px] tracking-wider text-slate-300 font-semibold`).
- **PROPS**: `{ userName: string; jobCount: number; date: Date }`.
- **IMPORTS**: `Calendar` from `lucide-react`; `format` from `date-fns`.
- **GOTCHA**: Use `format(date, 'EEE, LLL d')` to produce "Wed, Feb 18".
- **VALIDATE**: `cd frontend && npm run typecheck && npm run lint`

### 16. CREATE `frontend/src/features/tech-mobile/components/MobileJobCard.tsx`

- **IMPLEMENT**: Per-card component. Props: `{ appointment: Appointment; onOpen: (id: string) => void }`. Compute `state = deriveCardState(appointment.status)`. Render:
  - 4px left border (`border-l-4 border-l-blue-700` placeholder; replace with job-type-color util later).
  - Container classes: `relative bg-white rounded-2xl border border-slate-200 px-3.5 pt-3.5 pb-3` plus state-dependent overrides via `cn()`:
    - current: `border-teal-500 border-[1.5px] shadow-[0_6px_20px_rgba(20,184,166,0.18)]`
    - complete: `opacity-75`
  - "NOW · IN PROGRESS" pill on `current` (absolute, `-top-2.5 left-3`, `bg-teal-600 text-white text-[9px] font-bold tracking-wider px-2 py-0.5 rounded`).
  - Header row (flex justify-between):
    - Left: customer name (`text-base font-bold`), job type label (`text-sm text-slate-700 mt-1 font-medium`), then if `appointment.property_summary`: `<MapPin>` + two lines (street; "city, state zip").
    - Right: time window (`font-mono text-xs font-bold whitespace-nowrap`, color teal-700 on current else slate-900); on complete, render the COMPLETE pill (`bg-green-50 text-green-700`).
  - Chip row (only if `property_summary` has data): zone-count chip (`{n} zones`), water-source chip (e.g., `City water` from `system_type`).
  - Action footer: state-conditional (matches the design handoff exactly):
    - current → full-width teal button "Job details ›".
    - complete → green "COMPLETE" banner above an outlined "Job details" button.
    - upcoming → row of two equal buttons: "Navigate" (slate-900 fill, opens `buildMapsUrl(...)` via `window.open(url, '_blank', 'noopener,noreferrer')`) + "Job details" (outlined).
  - Whole card is the tap target → `onClick={() => onOpen(appointment.id)}`. Action buttons inside call `e.stopPropagation()`.
- **IMPORTS**: `MapPin`, `Navigation`, `Check`, `ChevronRight` from `lucide-react`; `cn` from `@/lib/utils`; `Appointment` from `@/features/schedule/types`; `deriveCardState` and `buildMapsUrl` and `formatTimeWindow` from sibling utils.
- **GOTCHA**: When `property_summary` is `null`, omit the address block AND the chip row — do not render empty containers.
- **GOTCHA**: Address full text passed to `buildMapsUrl` should be `"${address}, ${city}, ${state} ${zip_code ?? ''}".trim()`.
- **VALIDATE**: `cd frontend && npm run typecheck && npm run lint`

### 17. CREATE `frontend/src/features/tech-mobile/components/MobileJobCard.test.tsx`

- **IMPLEMENT**: Render the card three times with appointments differing only in `status`. Assert visible badges (`NOW · IN PROGRESS`, `COMPLETE`) and action button labels (`Navigate` only on upcoming). Mock `onOpen`; assert it fires on card click but NOT on Navigate-button click (stopPropagation).
- **PATTERN**: `@testing-library/react` + `userEvent`.
- **VALIDATE**: `cd frontend && npx vitest run src/features/tech-mobile/components/MobileJobCard.test.tsx`

### 18. CREATE `frontend/src/features/tech-mobile/components/TechSchedulePage.tsx`

- **IMPLEMENT**:
  ```tsx
  import { useState } from 'react';
  import { format } from 'date-fns';
  import { useAuth } from '@/features/auth/components/AuthProvider';
  import { useStaffDailySchedule } from '@/features/schedule/hooks/useAppointments';
  import { AppointmentModal } from '@/features/schedule/components/AppointmentModal';
  import { TechHeader } from './TechHeader';
  import { MobileJobCard } from './MobileJobCard';
  import { deriveCardState } from '../utils/cardState';
  ```
  Body:
  - `const { user } = useAuth(); if (!user) return null;`
  - `const today = format(new Date(), 'yyyy-MM-dd');`
  - `const { data, isLoading, isError, refetch } = useStaffDailySchedule(user.id, today);`
  - `const [openId, setOpenId] = useState<string | null>(null);`
  - `const visible = (data?.appointments ?? []).filter(a => deriveCardState(a.status) !== 'hidden').sort((a,b) => a.time_window_start.localeCompare(b.time_window_start));`
  - Render `<TechHeader userName={user.name} jobCount={visible.length} date={new Date()} />`, then state-dependent body:
    - loading → 3 stub `<div className="bg-slate-100 animate-pulse rounded-2xl h-32" />` cards in a `<div className="px-3 pt-3 space-y-3">`.
    - error → small card with "Couldn't load your schedule" + retry button calling `refetch()`.
    - empty → centered "No appointments today" with `<Calendar>` icon.
    - populated → mapped `<MobileJobCard appointment={a} onOpen={setOpenId} />`.
  - Mount the modal exactly mirroring `SchedulePage.tsx:558-563`:
    ```tsx
    {openId && (
      <AppointmentModal
        appointmentId={openId}
        open={!!openId}
        onClose={() => setOpenId(null)}
      />
    )}
    ```
- **VALIDATE**: `cd frontend && npm run typecheck && npm run lint`

### 19. CREATE `frontend/src/features/tech-mobile/components/TechSchedulePage.test.tsx`

- **IMPLEMENT**: Vitest mocks for `useStaffDailySchedule` and `useAuth`. Tests:
  - (a) loading state renders 3 skeleton cards
  - (b) empty list renders "No appointments today"
  - (c) populated list renders one card per visible appointment, excludes `cancelled`/`no_show`
  - (d) clicking a card sets state and the (mocked) `AppointmentModal` mounts with the right `appointmentId`
- **PATTERN**: Wrap in `<MemoryRouter>` and a fresh `<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>`. Mock the modal with `vi.mock('@/features/schedule/components/AppointmentModal', () => ({ AppointmentModal: vi.fn(() => null) }))` to avoid pulling its full tree into the test.
- **VALIDATE**: `cd frontend && npx vitest run src/features/tech-mobile/components/TechSchedulePage.test.tsx`

### 20. CREATE `frontend/src/features/tech-mobile/index.ts`

- **IMPLEMENT**:
  ```ts
  export { TechMobileLayout } from './components/TechMobileLayout';
  export { TechSchedulePage } from './components/TechSchedulePage';
  ```
- **VALIDATE**: `cd frontend && npm run typecheck`

### 21. UPDATE `frontend/src/features/auth/components/AuthProvider.tsx` — `login` returns `LoginResponse`

- **IMPLEMENT**:
  ```tsx
  const login = useCallback(
    async (credentials: LoginRequest): Promise<LoginResponse> => {
      const response = await authApi.login(credentials);
      setAuthState(response);
      return response;
    },
    [setAuthState]
  );
  ```
  Update the `AuthContextValue` (`features/auth/types/index.ts:48-62`):
  ```ts
  login: (credentials: LoginRequest) => Promise<LoginResponse>;
  ```
- **GOTCHA**: This is a public API change — search `frontend/src` for any other caller of `login` that may be affected: `Grep` for `\.login\(` inside `features/auth/`. The login page is the only consumer; if anywhere else awaits `login()` and ignores the return, no further action needed.
- **VALIDATE**: `cd frontend && npm run typecheck && npm run lint`

### 22. UPDATE `frontend/src/features/auth/components/LoginPage.tsx` — branch redirect on role

- **IMPLEMENT**: Replace the existing post-login navigation:
  ```tsx
  // Before:
  await login({ username, password, remember_me: rememberMe });
  navigate(from, { replace: true });
  // After:
  const response = await login({ username, password, remember_me: rememberMe });
  const target = response.user.role === 'tech' ? '/tech' : from;
  navigate(target, { replace: true });
  ```
  Also add an effect for already-authenticated visits to `/login`:
  ```tsx
  useEffect(() => {
    if (isAuthenticated && user?.role === 'tech') {
      navigate('/tech', { replace: true });
    }
  }, [isAuthenticated, user, navigate]);
  ```
- **VALIDATE**: `cd frontend && npm run typecheck && npm run lint`

### 23. UPDATE `frontend/src/core/router/index.tsx` — add `/tech` and post-login redirect

- **IMPLEMENT**: Add a new top-level sibling to the `<ProtectedLayoutWrapper>` group (NOT a child):
  ```tsx
  import { TechMobileLayout, TechSchedulePage } from '@/features/tech-mobile';
  // ... in createBrowserRouter array, sibling to the existing protected-layout block:
  {
    path: '/tech',
    element: (
      <ProtectedRoute allowedRoles={['tech']}>
        <TechMobileLayout />
      </ProtectedRoute>
    ),
    children: [
      { index: true, element: <TechSchedulePage /> },
    ],
  },
  ```
  Replace the existing index redirect (`{ index: true, element: <Navigate to="/dashboard" replace /> }` at lines 172-175) with a small role-aware component:
  ```tsx
  function PostLoginRedirect() {
    const { user } = useAuth();
    if (user?.role === 'tech') return <Navigate to="/tech" replace />;
    return <Navigate to="/dashboard" replace />;
  }
  // ...
  { index: true, element: <PostLoginRedirect /> },
  ```
- **GOTCHA**: `<PostLoginRedirect>` runs inside `<ProtectedLayoutWrapper>` so `user` is guaranteed defined.
- **GOTCHA**: Place the `/tech` route OUTSIDE `<ProtectedLayoutWrapper>` so it does NOT inherit the admin sidebar.
- **VALIDATE**: `cd frontend && npm run typecheck && npm run build`

### 24. CREATE `scripts/seed_tech_companion_appointments.py` — today's appointments for `vas`, `steven`, `vitallik`

- **IMPLEMENT**: An idempotent async script. Top-level docstring explains intent and usage. CLI entry: `uv run python scripts/seed_tech_companion_appointments.py`. The script does the following inside one async session:

  1. **Look up (do NOT create) the three existing tech Staff rows by username**: `vas`, `steven`, `vitallik`. If any of the three is missing, print a clear error pointing to migration `20250626_100000_seed_demo_data.py` and exit 1 — the migration creates these rows and login credentials.
  2. Upsert one Customer + Property per tech by stable email (`e2e+vas@grins.test`, `e2e+steven@grins.test`, `e2e+vitallik@grins.test`) so each tech has a distinct customer set; Eden Prairie addresses with realistic `address`, `city`, `state`, `zip_code`, `zone_count`, `system_type`.
  3. Look up an existing service offering by code (e.g., `SPRING_OPENING`) — mirror the lookup pattern in `scripts/seed_resource_timeline_test_data.py`. If none exists, fall back to inserting one with a stable code so the script is robust.
  4. Upsert today's appointments per tech (idempotent on `(staff_id, scheduled_date, time_window_start)`):
     - **`vas`** — 3 appointments today (covers all visual states):
       - `completed`, 08:00–09:25
       - `in_progress`, 10:30–12:00
       - `scheduled`, 13:00–14:15
     - **`steven`** — 2 appointments today (verifies per-tech isolation):
       - `scheduled`, 09:00–10:30
       - `en_route`, 11:00–12:30
     - **`vitallik`** — 0 appointments today (validates empty state). The script must also DELETE any pre-existing test appointments owned by this script for `vitallik` on today's date so the empty state is honest. Mark script-owned rows by setting `notes = '[tech-companion-e2e]'` (or similar stable tag) and only delete rows matching that tag.
  5. Print a summary table of created/updated/deleted rows and the login credentials reminder.
  6. Exit code 0 on success.
- **PATTERN**: Mirror `scripts/seed_resource_timeline_test_data.py` for the script skeleton — async session, structlog, idempotent upserts, the existing first-name → staff lookup helper.
- **GOTCHA**: Do NOT touch the Staff rows. Do NOT change passwords. The dev migration already seeds them with `tech123`.
- **GOTCHA**: `scheduled_date = date.today()` — appointments must be for today so `useStaffDailySchedule(staffId, today)` returns them. If the script runs across midnight during an E2E, the second run will silently make a different day's data; not a concern for normal use.
- **GOTCHA**: Stable-tag rows you create with a fixed `notes` value (e.g., `'[tech-companion-e2e]'`) so the cleanup step for `vitallik` only deletes script-owned rows — never user-created appointments.
- **GOTCHA**: Document the credentials in the script's `__main__` block:
  ```
  Existing dev tech logins (seeded by migration 20250626_100000_seed_demo_data):
    vas      / tech123   (3 appts today: completed / in_progress / scheduled)
    steven   / tech123   (2 appts today: scheduled / en_route)
    vitallik / tech123   (0 appts today — empty state)
  ```
- **VALIDATE**:
  ```bash
  uv run python scripts/seed_tech_companion_appointments.py
  # Re-run to confirm idempotency:
  uv run python scripts/seed_tech_companion_appointments.py
  # Sanity-query — confirm staff exist and login is enabled:
  uv run python -c "
  import asyncio
  from grins_platform.database import async_session_factory
  from sqlalchemy import text
  async def main():
      async with async_session_factory() as s:
          r = await s.execute(text(\"SELECT username, role, is_login_enabled FROM staff WHERE username IN ('vas','steven','vitallik')\"))
          print(list(r))
  asyncio.run(main())
  "
  ```

### 25. CREATE `e2e/tech-companion-mobile.sh` — agent-browser journey

- **IMPLEMENT**: A bash script following the exact pattern of `e2e/payment-links-flow.sh`. Set `set -euo pipefail`. Configurable `BASE` (default `http://localhost:5173`). `SHOTS=e2e-screenshots/tech-companion-mobile`. `mkdir -p "$SHOTS"`. Helper `ab() { agent-browser --session "tech-companion-e2e" "$@"; }`.

  **Pre-flight**: assert backend is up (`curl -fsS "${API_BASE:-http://localhost:8000}/api/v1/health"` or equivalent). Run the seed script (`uv run python scripts/seed_tech_companion_appointments.py`).

  **Phase 0 — viewport setup**:
  ```bash
  ab set viewport 390 844    # iPhone 14 Pro size
  ```

  **Phase 1 — Tech `vas` login + redirect to /tech**:
  ```bash
  ab open "$BASE/login"
  ab wait --load networkidle
  ab screenshot "$SHOTS/01-login.png"
  ab fill "[data-testid='username-input']" "vas"
  ab fill "[data-testid='password-input']" "tech123"
  ab click "[data-testid='login-btn']"
  ab wait --load networkidle
  ab screenshot "$SHOTS/02-vas-schedule.png"
  # Assert URL is /tech (capture via console or re-fetch via curl with cookies)
  ```

  **Phase 2 — Card states (vas has all three: completed / in_progress / scheduled)**:
  ```bash
  ab snapshot -i > "$SHOTS/02-snapshot.txt"
  # Verify three cards visible with the expected customer names + states
  ab screenshot "$SHOTS/03-cards-visible.png"
  ```

  **Phase 3 — Open the in_progress card → AppointmentModal**:
  ```bash
  # Click the card whose state badge says "NOW · IN PROGRESS"
  ab click "[data-testid='mobile-job-card-current']"
  ab wait --load networkidle
  ab screenshot "$SHOTS/04-modal-open.png"
  # Close
  ab click "[data-testid='appointment-modal-close']"
  ab screenshot "$SHOTS/05-modal-closed.png"
  ```

  **Phase 4 — Logout, login as `steven`, verify per-tech isolation**:
  ```bash
  ab click "[data-testid='logout-btn']"
  ab wait --load networkidle
  ab fill "[data-testid='username-input']" "steven"
  ab fill "[data-testid='password-input']" "tech123"
  ab click "[data-testid='login-btn']"
  ab wait --load networkidle
  ab screenshot "$SHOTS/06-steven-schedule.png"
  # Assert two cards, neither showing vas's customers
  ```

  **Phase 5 — `vitallik` (empty state)**:
  ```bash
  ab click "[data-testid='logout-btn']"
  ab wait --load networkidle
  ab fill "[data-testid='username-input']" "vitallik"
  ab fill "[data-testid='password-input']" "tech123"
  ab click "[data-testid='login-btn']"
  ab wait --load networkidle
  ab screenshot "$SHOTS/07-vitallik-empty.png"
  # Assert "No appointments today" copy is visible
  ```

  **Phase 6 — Admin login goes to /dashboard, NOT /tech**:
  ```bash
  ab fill "[data-testid='username-input']" "admin"
  ab fill "[data-testid='password-input']" "admin123"
  ab click "[data-testid='login-btn']"
  ab wait --load networkidle
  ab screenshot "$SHOTS/08-admin-dashboard.png"
  # Assert URL is /dashboard
  ```

  **Phase 7 — Tech on desktop viewport sees the landing**:
  ```bash
  ab set viewport 1440 900
  # logout + login as vas
  ab fill "[data-testid='username-input']" "vas"
  ab fill "[data-testid='password-input']" "tech123"
  ab click "[data-testid='login-btn']"
  ab wait --load networkidle
  ab screenshot "$SHOTS/09-tech-on-desktop-landing.png"
  # Assert "Open this on your phone" copy is visible and admin sidebar is NOT
  ```

  **Phase 8 — Console / errors**:
  ```bash
  ab console > "$SHOTS/console.log"
  ab errors  > "$SHOTS/errors.log"
  # Fail the script if errors.log is non-empty (apart from known noise)
  ```

- **GOTCHA**: Some `data-testid` attributes referenced above (e.g., `mobile-job-card-in-progress`, `logout-btn`, `appointment-modal-close`) need to be added in the corresponding components during Phase 3. When you implement `MobileJobCard`, add `data-testid={\`mobile-job-card-${state}\`}` so the E2E script can target a specific state. When you implement `OpenOnPhoneLanding`, add `data-testid="logout-btn"` to the sign-out button. The `[data-testid='login-btn']`, `[data-testid='username-input']`, `[data-testid='password-input']` selectors already exist in `LoginPage` (verify by grepping `data-testid` in `LoginPage.tsx` before assuming).
- **GOTCHA**: `appointment-modal-close` may not exist on the existing modal. Verify and add if missing (this is a one-line addition in the existing modal close button — acceptable as a test-only attribute, NOT a behavioral change).
- **VALIDATE**:
  ```bash
  # Local backend + frontend running first.
  uv run uvicorn grins_platform.app:app --reload --host 0.0.0.0 --port 8000 &
  (cd frontend && npm run dev) &
  sleep 5
  bash e2e/tech-companion-mobile.sh
  # Then inspect:
  ls -la e2e-screenshots/tech-companion-mobile/
  # Expected: 9 screenshots + console.log + errors.log + 02-snapshot.txt
  ```

### 26. ADD `data-testid`s required by the E2E script

- **IMPLEMENT**: Audit the components touched by Phase 7 of the E2E script and add the testids the script depends on. Specifically:
  - `MobileJobCard.tsx` — root element gets `data-testid={\`mobile-job-card-${state}\`}` where `state` is `'current' | 'upcoming' | 'complete'`.
  - `OpenOnPhoneLanding.tsx` — sign-out button gets `data-testid="logout-btn"`.
  - `AppointmentModal/AppointmentModal.tsx` — close button gets `data-testid="appointment-modal-close"` (one-line additive change, NOT a redesign).
  - `LoginPage.tsx` — verify `data-testid='username-input' / 'password-input' / 'login-btn'` already exist; if not, add them.
- **VALIDATE**: `cd frontend && grep -R "data-testid" src/features/tech-mobile src/features/auth src/features/schedule/components/AppointmentModal | head -20`

### 27. RUN the full local validation suite

- **VALIDATE**:
  ```bash
  # Backend
  uv run ruff check src/grins_platform/
  uv run ruff format --check src/grins_platform/
  uv run mypy src/grins_platform/
  uv run pytest src/grins_platform/tests/integration/ -v -k "staff_daily or property_summary"

  # Frontend
  cd frontend
  npm run typecheck
  npm run lint
  npx vitest run src/features/tech-mobile
  npx vitest run                       # full suite — confirm zero regression
  npm run build
  cd ..

  # Seed
  uv run python scripts/seed_tech_companion_appointments.py
  uv run python scripts/seed_tech_companion_appointments.py    # idempotency

  # E2E (requires servers running locally)
  bash e2e/tech-companion-mobile.sh
  ```

---

## TESTING STRATEGY

### Unit Tests
- `cardState.test.ts` — exhaustive over `AppointmentStatus` literals.
- `mapsLink.test.ts` — iOS branch + default Google branch + URL encoding.
- `formatTimeWindow.test.ts` — AM/PM, midnight, noon.

### Component Tests
- `MobileJobCard.test.tsx` — 3 visual states, tap propagation, Navigate stopPropagation.
- `TechSchedulePage.test.tsx` — loading / empty / populated / modal-open / hidden-statuses-excluded.

### Integration Tests
- Backend: pytest case asserting `property_summary` is populated when the Job has a Property, `None` when not.

### E2E Tests
- `e2e/tech-companion-mobile.sh` — 9 screenshots covering every gating branch (tech-on-phone, tech-on-desktop, admin-on-phone) and every card state, plus per-tech schedule isolation. **Mandatory pass before ship.**

### Edge Cases
- Tech with **zero** appointments today → empty state renders (covered by `tech_carol`).
- Tech with only `cancelled`/`no_show` appointments → list renders empty (covered in unit tests).
- Appointment with `property_summary == null` → card renders without address/chips, no crash.
- Phone → desktop rotation crossing 640px → `PhoneOnlyGate` flips to landing in real time.
- Admin user accessing `/tech` directly → `<ProtectedRoute allowedRoles={['tech']}>` renders `<AccessDenied />`.
- Tech accessing `/dashboard` directly → renders normally today (no `allowedRoles` set on `/dashboard`); listed as a known follow-up in NOTES, NOT in scope.

---

## VALIDATION COMMANDS

### Level 1: Syntax & Style
```bash
uv run ruff check src/grins_platform/
uv run ruff format --check src/grins_platform/
cd frontend && npm run lint
cd frontend && npm run format:check
```

### Level 2: Type Checking
```bash
uv run mypy src/grins_platform/
cd frontend && npm run typecheck
```

### Level 3: Unit & Component Tests
```bash
uv run pytest src/grins_platform/tests/integration/ -v -k "staff_daily or property_summary"
cd frontend && npx vitest run src/features/tech-mobile
cd frontend && npx vitest run
```

### Level 4: Build
```bash
cd frontend && npm run build
```

### Level 5: Seed + E2E browser validation (mandatory)
```bash
uv run python scripts/seed_tech_companion_appointments.py
bash e2e/tech-companion-mobile.sh
ls e2e-screenshots/tech-companion-mobile/   # must include all 9 screenshots
```

---

## ACCEPTANCE CRITERIA

- [ ] The existing dev tech rows `vas`, `steven`, `vitallik` are untouched (no password reset, no role change). The seed script ONLY creates/upserts customers, properties, jobs, and appointments — never staff.
- [ ] After running the seed script, each tech has the expected today schedule: `vas` 3 (completed/in_progress/scheduled), `steven` 2 (scheduled/en_route), `vitallik` 0.
- [ ] A tech logging in from a viewport ≤639px is redirected to `/tech` and sees their (and only their) day's schedule.
- [ ] A tech on a viewport ≥640px sees "Open this on your phone" at `/tech` — never the admin sidebar.
- [ ] An admin or manager logs in and lands on `/dashboard` (existing behavior preserved).
- [ ] `MobileJobCard` renders three visual states correctly: current (in_progress), upcoming (scheduled/confirmed/en_route), complete (completed). Cancelled/no-show appointments are hidden.
- [ ] Tapping any card opens the existing `AppointmentModal` — same component used by `SchedulePage`. The modal source has only the additive `data-testid="appointment-modal-close"` change, no behavioral changes.
- [ ] "Navigate" button on upcoming cards opens a maps URL in a new tab (Apple Maps on iOS UA, Google Maps elsewhere).
- [ ] All Level 1–4 validation commands pass with zero errors.
- [ ] Vitest coverage for `features/tech-mobile/` is ≥80% lines.
- [ ] Backend pytest cases for `property_summary` population pass.
- [ ] No regressions in `features/schedule/` or `features/auth/` test suites.
- [ ] `npm run build` succeeds.
- [ ] `bash e2e/tech-companion-mobile.sh` exits 0; `e2e-screenshots/tech-companion-mobile/` contains all 9 screenshots; `errors.log` shows no unexpected entries.

---

## COMPLETION CHECKLIST

- [ ] Backend `PropertySummary` schema added; `property_summary` populated by the service via `selectinload(Job.job_property)`; pytest passes.
- [ ] Frontend `Appointment` type updated with `property_summary?: PropertySummary | null`.
- [ ] All 15 new files in `features/tech-mobile/` created (5 components, 3 utils, 5 colocated tests, 1 index, 1 layout = recount; correct count is 11 source + 5 tests = 16 — verify).
- [ ] Router registers `/tech` outside the admin layout wrapper, gated by `<ProtectedRoute allowedRoles={['tech']}>`.
- [ ] `LoginPage` and `AuthProvider` updated; `login` returns `LoginResponse`; post-login redirect branches on role; index route uses `<PostLoginRedirect>`.
- [ ] `scripts/seed_tech_companion_appointments.py` runs idempotently against the existing `vas`/`steven`/`vitallik` rows and prints the credentials reminder.
- [ ] `e2e/tech-companion-mobile.sh` exists, is executable (`chmod +x`), and exits 0 against a local server pair.
- [ ] All `data-testid` attributes the E2E script depends on are present.
- [ ] Manual smoke (Task 23 above): screenshots captured and committed to the PR.
- [ ] No modifications to `Layout.tsx` or `features/resource-mobile/`. The only `AppointmentModal` change is the additive close-button `data-testid`.

---

## NOTES

**Out of scope (explicitly):**
- Alerts tab, Co-pilot tab, "Me" tab, bottom tab bar.
- Drive-time dividers between cards.
- Header DRIVE stat (only JOBS).
- Mobile-variant redesign of `AppointmentModal` — reused as-is (one additive `data-testid` only).
- Tablet layouts.
- Time-of-day-aware greeting (static "Good morning").
- Tactical-alerts rule engine and route optimization service.
- Cleanup of `/schedule/mobile` (`ResourceMobileView`) — separate surface, leave as-is.
- VIP star, "dog in yard", "gate code" warn chips — depend on `customer.tags` / `job.access_notes` fields not present today; explicitly deferred.
- Adding `allowedRoles` to existing admin routes to bounce techs from `/dashboard` — known follow-up; NOT in scope here.

**Verification gaps closed (from the prior 8/10 draft):**
- ✅ Property field names verified verbatim: `address`, `city`, `state`, `zip_code`, `zone_count`, `system_type`.
- ✅ No separate `User` model — `Staff` is the auth principal; `user.id` is the staff id.
- ✅ `Job.job_property` is the relationship name (not `Job.property`).
- ✅ `selectinload` is the eager-load pattern (not `joinedload`).
- ✅ `AuthProvider.login` signature change is mechanical and the only consumer is `LoginPage`.
- ✅ `ProtectedRoute` with role mismatch renders `<AccessDenied />` (NOT a redirect) — login-time redirect is the actual gate.
- ✅ Agent-browser CLI commands verified by reading existing E2E scripts.
- ✅ Path alias `@/ → src/` confirmed in both tsconfig and vite config.
- ✅ `cn` location confirmed at `frontend/src/lib/utils.ts`.

**Trade-offs:**
- Extending `Appointment` with `property_summary?: PropertySummary | null` instead of introducing `TechAppointment`. Reason: optional null-default field; one less type to maintain.
- Layout C (separate `<TechMobileLayout>`) over conditional content swap inside `/dashboard`. Reason: the layout shell is structurally different and a route-boundary gate localizes the role/viewport check.
- `PhoneOnlyGate` shows a landing instead of redirecting techs to `/dashboard` on desktop. Reason: don't expand the surface area where techs can access admin UI.
- Login redirect lives in `LoginPage` (not `AuthProvider`). Reason: keep `AuthProvider` route-agnostic.
- Per-feature seed script (not a general-purpose seed system). Reason: matches existing project convention (`seed_resource_timeline_test_data.py`, `seed_e2e_payment_links.py`).

**Confidence Score: 10/10.** Every external reference verified; no `// VERIFY` comments remain. Login-flow change is mechanical and isolated to two files. Backend extension follows an existing pattern (`selectinload` chain). Seed script and E2E follow the project's existing per-feature conventions. All `data-testid` dependencies for the E2E run are pre-declared in Task 26 so the agent doesn't discover them mid-run. The only residual risk is that line numbers may have shifted on `dev` between recon and execution — re-locate by symbol name if so.
