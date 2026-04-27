# Feature: Gap 15 — Queue Freshness (Phase 1 + Phase 2)

The following plan should be complete, but it's important that you validate documentation and codebase patterns and task sanity before you start implementing.

Pay special attention to naming of existing utils, types, and models. Import from the right files — the inbound-reply queues live in `features/schedule/` and the `CustomerMessages` queue lives in `features/customers/`.

## Feature Description

The admin queues that surface inbound customer SMS replies (`RescheduleRequestsQueue`, `NoReplyReviewQueue`, `CustomerMessages`, and the `AppointmentDetail` modal) currently only refresh on mutation, manual page reload, or route navigation. Because customer replies, APScheduler cron output, and alert creation all happen **outside** the admin's browser, an admin can stare at a stale queue for 10+ minutes and miss a fresh "R" (reschedule) request or a nightly no-reply flag.

Gap 15 (severity 3, Frontend) specifies a two-phase fix:

- **Phase 1 — Polling.** Add `refetchInterval` to the four inbound-reply hooks, paired with `refetchIntervalInBackground: false` (so we don't burn cycles when the tab is hidden) and `refetchOnWindowFocus: true` / `refetchOnReconnect: true` (so returning to the tab triggers a fresh fetch). Urgencies: Reschedule 30 s, No-Reply 60 s, CustomerMessages 60 s, AppointmentDetail 60 s.
- **Phase 2 — UX affordances.** Add a `↻ Refresh` button and a `Last updated Xs ago` relative-time label to each queue header so the admin knows how stale the data is and can force a poll on demand.

Phase 3 (SSE/WebSocket realtime) is explicitly deferred and out of scope for this plan.

## User Story

As an admin monitoring the `/schedule` page during the day,
I want the Reschedule Requests and No-Reply Confirmations queues to auto-refresh in the background and expose a manual refresh + freshness indicator,
So that I see new customer replies and nightly-cron flags within 30–60 seconds without having to hit browser reload.

## Problem Statement

1. `useRescheduleRequests` has **no `refetchInterval`** — when a customer replies "R" at 9:03 AM, the row does not appear in the queue until the admin reloads or navigates away and back (verified at `frontend/src/features/schedule/hooks/useRescheduleRequests.ts:14-19`).
2. `useNoReplyReviewList` has **no `refetchInterval`** — the nightly `flag_no_reply_confirmations` job populates the queue silently; admin misses the bucket until next page reload (verified at `frontend/src/features/schedule/hooks/useNoReplyReview.ts:28-34`).
3. `useCustomerSentMessages` has **no `refetchInterval`** — outbound/inbound messages on a customer detail view age silently (verified at `frontend/src/features/customers/hooks/useCustomers.ts:119-126`).
4. `useAppointment` (detail modal) has **no `refetchInterval`** — when the modal is open and a webhook flips status/adds a timeline event, the modal shows stale data (verified at `frontend/src/features/schedule/hooks/useAppointments.ts:38-44`).
5. None of these queues shows a "last updated" indicator, so admins have no signal that the data is fresh (or stale).

## Solution Statement

Apply the Phase 1 + Phase 2 pattern Gap 15 recommends, leveraging infrastructure that already exists in the codebase:

1. Add `refetchInterval`, `refetchIntervalInBackground: false`, `refetchOnWindowFocus: true`, `refetchOnReconnect: true` to the four hooks, mirroring the already-established pattern in `useCustomerInvoices` (H-9) and `useDashboardMetrics`.
2. Introduce a small, reusable `<QueueFreshnessHeader>` component in `frontend/src/shared/components/` that wraps the existing queue title/badge and adds a `↻` button (invalidating the passed queryKey) plus a `dataUpdatedAt → formatDistanceToNow` relative-time label that ticks every 15 s. This component is used by `RescheduleRequestsQueue` and `NoReplyReviewQueue`; the same idea is applied inline to `CustomerMessages` and `AppointmentDetail` headers.
3. Unit-test the new component, extend the two existing queue component tests to assert the polling interval is wired and the refresh button triggers an invalidation, and validate end-to-end with agent-browser.

No backend changes. No new API endpoints. No new infrastructure.

## Feature Metadata

**Feature Type**: Enhancement
**Estimated Complexity**: Low
**Primary Systems Affected**: Frontend — `features/schedule/hooks/`, `features/schedule/components/`, `features/customers/hooks/`, `features/customers/components/`, `shared/components/`
**Dependencies**: Already installed — `@tanstack/react-query@^5.90.19`, `date-fns@^4.1.0` (provides `formatDistanceToNow`), `lucide-react` (provides `RefreshCw` icon).

---

## CONTEXT REFERENCES

### Relevant Codebase Files — IMPORTANT: READ THESE BEFORE IMPLEMENTING

**Target hooks (the ones being modified):**

- `frontend/src/features/schedule/hooks/useRescheduleRequests.ts` (lines 9-19) — current key factory + `useRescheduleRequests` hook; no polling today.
- `frontend/src/features/schedule/hooks/useNoReplyReview.ts` (lines 15-34) — current key factory + `useNoReplyReviewList` hook; no polling today.
- `frontend/src/features/schedule/hooks/useAppointments.ts` (lines 13-44) — `appointmentKeys` factory; `useAppointment(id)` detail hook at line 38.
- `frontend/src/features/customers/hooks/useCustomers.ts` (lines 119-126) — `useCustomerSentMessages`; the correct file to edit (NOT `CustomerMessages.tsx`).

**Target components (the ones being modified):**

- `frontend/src/features/schedule/components/RescheduleRequestsQueue.tsx` (lines 139-180) — header block where freshness UI goes. Note the existing `CalendarClock` icon + title + Badge row at lines 145-157.
- `frontend/src/features/schedule/components/NoReplyReviewQueue.tsx` (lines 125-170) — header block (lines 131-146). Note the `AlertCircle` icon + title + Badge row.
- `frontend/src/features/customers/components/CustomerMessages.tsx` (lines 25-34, 30-34) — header block (the `<OptOutBadge />` wrapper). The "last updated" label belongs adjacent to `OptOutBadge`.
- `frontend/src/features/schedule/components/AppointmentDetail.tsx` (lines 85-117) — modal header; line 90 is `useAppointment`; line 110-117 is `invalidateTimeline`. The existing `queryClient.invalidateQueries` pattern here is the pattern to copy.

**Reference implementations (the patterns to mirror — DO NOT rewrite these, copy their shape):**

- `frontend/src/features/customers/hooks/useCustomers.ts` (lines 71-91) — `useCustomerInvoices` is the **canonical** example in this codebase of a hook that adds `refetchInterval: 30_000` with a doc comment explaining the two-layer freshness strategy (polling + mutation-triggered invalidation). **Mirror the comment style.**
- `frontend/src/features/dashboard/hooks/useDashboard.ts` (lines 28-47) — `useDashboardMetrics` / `useDashboardSummary` both use `staleTime: 30_000` + `refetchInterval: 60_000`. Use this exact pair for 60-second pollers.
- `frontend/src/features/customers/hooks/useCustomers.test.tsx` (lines 285-321) — the test pattern for asserting `refetchInterval` is wired on a hook (checks `hookSource.toString()` contains "refetchInterval", plus exercises the options override). **Mirror this for hook tests.**
- `frontend/src/features/schedule/components/RescheduleRequestsQueue.test.tsx` (full file) — component test pattern: `QueryClient` wrapper with `retry: false`, `vi.mock('../api/...')`, `userEvent` click flows. **Mirror this for the new Refresh-button tests.**
- `frontend/src/core/providers/QueryProvider.tsx` (lines 8-31) — global defaults (`staleTime: 30_000`, `refetchOnWindowFocus: true` already global). Do not duplicate `refetchOnWindowFocus` in hooks unless the hook needs to *override* it — but Gap 15 says "set universally for these hooks" so include it explicitly at the hook site for readability and to document intent.

**Pattern for manual invalidation (the Refresh button):**

- `frontend/src/features/schedule/components/AppointmentDetail.tsx` (lines 110-117) — `invalidateTimeline` helper shows the `queryClient.invalidateQueries({ queryKey: ... })` pattern.
- `frontend/src/features/schedule/hooks/useRescheduleRequests.ts` (lines 21-30) — `onSuccess` invalidation pattern, same primitive.

**Supporting UI already in use:**

- `frontend/src/features/schedule/components/RescheduleRequestsQueue.tsx` (line 11) — `RefreshCw` icon already imported from `lucide-react`; use it for the header button too.
- `frontend/src/features/schedule/components/RescheduleRequestsQueue.tsx` (line 9) — `formatDistanceToNow` already imported from `date-fns`; use it for the "last updated" label.
- `@/components/ui/button` (`Button` with `size="sm" variant="ghost"`) — the standard icon-button used on line 272-281 of `RescheduleRequestsQueue.tsx`.

### New Files to Create

- `frontend/src/shared/components/QueueFreshnessHeader.tsx` — small reusable header component that renders `{icon} {title} {badge?}` on the left and `Last updated Xs ago [↻]` on the right. Accepts props: `icon: ReactNode`, `title: string`, `badgeCount?: number`, `badgeClassName?: string`, `dataUpdatedAt: number`, `isRefetching: boolean`, `onRefresh: () => void`, `testId?: string`.
- `frontend/src/shared/components/QueueFreshnessHeader.test.tsx` — component tests (renders title, shows "Just now" / "X seconds ago", clicks ↻ triggers `onRefresh`, spinner shows while `isRefetching`).

### Relevant Documentation — READ BEFORE IMPLEMENTING

- [TanStack Query v5 — useQuery options](https://tanstack.com/query/v5/docs/framework/react/reference/useQuery)
  - Specific options: `refetchInterval`, `refetchIntervalInBackground`, `refetchOnWindowFocus`, `refetchOnReconnect`, `staleTime`, `dataUpdatedAt`, `isRefetching`
  - Why: Confirms `refetchIntervalInBackground: false` respects the browser's `Page Visibility API` (tabs hidden → no polling), and `dataUpdatedAt` is returned as a millisecond timestamp suitable for `formatDistanceToNow(new Date(dataUpdatedAt))`.
- [TanStack Query v5 — QueryClient.invalidateQueries](https://tanstack.com/query/v5/docs/reference/QueryClient#queryclientinvalidatequeries)
  - Specific section: query-key matching semantics
  - Why: Confirms passing `queryKey: rescheduleKeys.all` invalidates every descendant list (including the current `status` variant).
- [date-fns — formatDistanceToNow](https://date-fns.org/docs/formatDistanceToNow)
  - Specific section: `addSuffix: true` option
  - Why: Produces the exact "12 seconds ago" / "about a minute ago" labels the gap doc requires.

### Patterns to Follow

Extracted from the codebase as-is — **do not reinvent, copy**.

**Hook polling pattern (from `useCustomerInvoices` / `useDashboardMetrics`):**
```ts
// Two-layer freshness strategy:
//   1. `refetchInterval: N` polling safety-net (this hook).
//   2. Cross-query invalidation from mutation hooks via <keyFactory>.all.
export function useRescheduleRequests(status?: string) {
  return useQuery({
    queryKey: rescheduleKeys.list(status),
    queryFn: () => rescheduleApi.list(status),
    staleTime: 30_000,
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: true,
    refetchOnReconnect: true,
  });
}
```

**Naming Conventions:**
- Files: components `PascalCase.tsx`, hooks `use{Name}.ts`, co-located tests `*.test.tsx`.
- `data-testid`: follows `{feature}-{role}` convention from `frontend-patterns.md`. For this work:
  - `queue-freshness-header` — wrapper on the component
  - `queue-last-updated` — the relative-time span
  - `refresh-{queue}-btn` — the refresh button (e.g. `refresh-reschedule-btn`, `refresh-no-reply-btn`, `refresh-messages-btn`, `refresh-appointment-btn`).

**Error / empty / loading handling:**
- Do NOT add the freshness header inside the `isLoading` or `error` early-return branches — those branches in `RescheduleRequestsQueue.tsx:100-135` and `NoReplyReviewQueue.tsx:86-121` should remain untouched. The header is only rendered in the success path.
- The Refresh button should be `disabled={isRefetching}` so repeated clicks don't queue multiple fetches.

**Import conventions (from `frontend-patterns.md` line 100-108 and verified usage in `RescheduleRequestsQueue.tsx:12-19`):**
```ts
import { QueueFreshnessHeader } from '@/shared/components';           // shared export
import { rescheduleKeys } from '../hooks/useRescheduleRequests';      // local feature
import { formatDistanceToNow } from 'date-fns';                        // external
import { Button } from '@/components/ui/button';                        // NOT @/shared/components/ui
import { Badge } from '@/components/ui/badge';                          // NOT @/shared/components/ui
import { cn } from '@/lib/utils';                                       // matches components/ui/button.tsx's own import
```
**IMPORTANT**: The steering file `frontend-patterns.md` line 102 shows `from '@/shared/components/ui'`, but the actual repo uses `@/components/ui/*` for shadcn primitives (Button, Badge, Dialog, etc.). Follow the repo convention, not the steering doc. Both `@/lib/utils` and `@/shared/utils/cn` export the same `cn` function; `@/lib/utils` is what `components/ui/button.tsx` uses internally, so prefer it here for consistency with the ui layer.

Add the `QueueFreshnessHeader` export to `frontend/src/shared/components/index.ts` (keep alphabetical grouping; the file currently exports at lines 1-18).

**TanStack Query key factory (from `frontend-patterns.md` line 74-81):**
Existing factories (`rescheduleKeys`, `noReplyReviewKeys`, `appointmentKeys`, `customerKeys`) already follow the pattern. **Do not create new factories.** The refresh button reuses the existing `.all` or `.list()` key.

**JSDoc / file header:**
All hooks and components in this repo have a leading block doc comment explaining what they do and what requirement they validate. **Preserve those docs and extend them** (add a line for the Gap 15 freshness behavior). Do not remove existing requirement references (e.g. "Validates: CRM Changes Update 2 Req 25.1…" in `useRescheduleRequests.ts`).

**Safety note (from memory):**
Gap 15 is purely a frontend freshness change. **No SMS is sent** by anything in this plan. The existing safety rule (only `+19527373312` may receive real SMS on dev) is irrelevant here but must not be weakened — the `NoReplyReviewQueue`'s Send Reminder confirm dialog (lines 172-240) must remain unmodified.

---

## IMPLEMENTATION PLAN

### Phase 1: Shared component foundation

Create the reusable `QueueFreshnessHeader` first so it's available when we wire each queue. This is ~30 lines of code plus tests.

**Tasks:**
- Create `QueueFreshnessHeader.tsx` with props documented above.
- Use `useState` + `useEffect` with a 15-second tick to force re-render of the relative-time label (otherwise it would only update when TanStack refreshes the data).
- Co-locate `QueueFreshnessHeader.test.tsx`.
- Re-export from `shared/components/index.ts`.

### Phase 2: Poll the four hooks

Modify the four hooks in isolation; no component changes yet. After this phase, the queues already update on background polls but have no user-visible freshness affordance.

**Tasks:**
- `useRescheduleRequests`: add 30 s poll + window-focus + reconnect refetch.
- `useNoReplyReviewList`: add 60 s poll + window-focus + reconnect refetch.
- `useCustomerSentMessages`: add 60 s poll + window-focus + reconnect refetch.
- `useAppointment` (detail): add 60 s poll + window-focus + reconnect refetch, but only when `enabled` (already gated by `!!id`).

### Phase 3: Wire the freshness header into each queue

- `RescheduleRequestsQueue` — wrap the header block (lines 145-157) with `QueueFreshnessHeader`.
- `NoReplyReviewQueue` — same, for the header at lines 131-146.
- `CustomerMessages` — adjacent to `<OptOutBadge customerId={...} />` (line 32), add a compact freshness label + refresh button.
- `AppointmentDetail` — the detail modal is a bigger component, so add the freshness affordance inline in the existing header (search for where `appointment.status` is rendered; place the `Last updated Xs ago [↻]` in the top-right of the modal header).

### Phase 4: Testing & validation

**Tasks:**
- Hook-level tests: follow the `useCustomerInvoices.test` shape (check `hookSource.toString()` contains `'refetchInterval'`).
- Component-level tests: extend existing `RescheduleRequestsQueue.test.tsx` / `NoReplyReviewQueue.test.tsx` with a "refresh button re-fetches" case. Exercise with `vi.useFakeTimers()` advancing ~30 s to assert a second API call fires.
- Shared-component test: `QueueFreshnessHeader.test.tsx` — renders, handles click, tick refreshes label.
- Agent-browser E2E: open `/schedule`, snapshot, click the refresh button, assert it re-renders without errors.

---

## STEP-BY-STEP TASKS

IMPORTANT: Execute every task in order, top to bottom. Each task is atomic and independently testable.

### 0. PREFLIGHT (sanity checks before editing)

- **IMPLEMENT**: Run these read-only checks. Each must match the expected output; if any differs, STOP and re-read the plan's context references.
  ```bash
  cd /Users/kirillrakitin/Grins_irrigation_platform

  # 1. Confirm the four target hooks exist and currently have NO refetchInterval.
  grep -n "refetchInterval" frontend/src/features/schedule/hooks/useRescheduleRequests.ts frontend/src/features/schedule/hooks/useNoReplyReview.ts frontend/src/features/schedule/hooks/useAppointments.ts
  grep -n "refetchInterval" frontend/src/features/customers/hooks/useCustomers.ts | grep -v "useCustomerInvoices\|options?:"
  # Expected: both commands print nothing (or only the useCustomerInvoices line, for the customers file).

  # 2. Confirm the shared components export site.
  test -f frontend/src/shared/components/index.ts && echo "OK index.ts exists"

  # 3. Confirm the shadcn primitives path we'll import from.
  test -f frontend/src/components/ui/button.tsx && test -f frontend/src/components/ui/badge.tsx && echo "OK shadcn paths"

  # 4. Confirm the cn util path.
  test -f frontend/src/lib/utils.ts && echo "OK @/lib/utils"

  # 5. Confirm AppointmentDetail test has 8 mockUseAppointment.mockReturnValue sites.
  grep -c "mockUseAppointment.mockReturnValue" frontend/src/features/schedule/components/AppointmentDetail.test.tsx
  # Expected: 8

  # 6. Confirm noReplyReviewKeys is exported from the hook file but NOT from the hooks barrel.
  grep -n "noReplyReviewKeys" frontend/src/features/schedule/hooks/useNoReplyReview.ts
  grep -n "noReplyReviewKeys" frontend/src/features/schedule/hooks/index.ts
  # Expected: first command finds line 15 export; second finds nothing.

  # 7. Confirm CustomerMessages has no test file.
  ls frontend/src/features/customers/components/ | grep -i "customermessages"
  # Expected: only CustomerMessages.tsx — NO .test.tsx file.
  ```
- **VALIDATE**: All seven checks match expected output. If ANY check fails, the repo has drifted from the plan's captured state — pause and re-read the source files before proceeding.

### 1. CREATE `frontend/src/shared/components/QueueFreshnessHeader.tsx`

- **IMPLEMENT**: Copy the following file verbatim — it is the canonical shape, already matches all five test cases in Task 2, and already mirrors the target header layout in `RescheduleRequestsQueue.tsx:145-157`:
  ```tsx
  /**
   * QueueFreshnessHeader — shared header block for admin queues that
   * surface inbound customer replies. Shows a title + optional count badge,
   * a "Updated X ago" relative-time label backed by TanStack's
   * ``dataUpdatedAt`` timestamp, and a manual refresh button that triggers
   * an invalidation of the owning query key.
   *
   * Ticks every 15 s to keep the relative-time label live independent of
   * the query's own ``refetchInterval``.
   *
   * Validates: Gap 15 (Phase 2) — queue freshness UX.
   */

  import { useEffect, useState } from 'react';
  import { formatDistanceToNow } from 'date-fns';
  import { RefreshCw } from 'lucide-react';
  import { Button } from '@/components/ui/button';
  import { Badge } from '@/components/ui/badge';
  import { cn } from '@/lib/utils';

  export interface QueueFreshnessHeaderProps {
    icon: React.ReactNode;
    title: string;
    badgeCount?: number;
    badgeClassName?: string;
    dataUpdatedAt: number;
    isRefetching: boolean;
    onRefresh: () => void;
    testId?: string;
  }

  export function QueueFreshnessHeader({
    icon,
    title,
    badgeCount,
    badgeClassName,
    dataUpdatedAt,
    isRefetching,
    onRefresh,
    testId,
  }: QueueFreshnessHeaderProps) {
    // Force a re-render every 15 s so the relative-time label stays live
    // even when TanStack hasn't refetched.
    const [, setTick] = useState(0);
    useEffect(() => {
      const t = setInterval(() => setTick((n) => n + 1), 15_000);
      return () => clearInterval(t);
    }, []);

    return (
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          {icon}
          <h3 className="text-sm font-semibold text-slate-700">{title}</h3>
          {typeof badgeCount === 'number' && badgeCount > 0 && (
            <Badge
              variant="secondary"
              className={badgeClassName}
            >
              {badgeCount}
            </Badge>
          )}
        </div>
        <div className="flex items-center gap-2">
          <span
            className="text-xs text-slate-400"
            data-testid="queue-last-updated"
          >
            {dataUpdatedAt > 0
              ? `Updated ${formatDistanceToNow(new Date(dataUpdatedAt), { addSuffix: true })}`
              : 'Updating…'}
          </span>
          <Button
            size="sm"
            variant="ghost"
            className="h-7 w-7 p-0"
            onClick={onRefresh}
            disabled={isRefetching}
            data-testid={testId ?? 'queue-refresh-btn'}
            aria-label="Refresh queue"
          >
            <RefreshCw
              className={cn('h-3 w-3', isRefetching && 'animate-spin')}
            />
          </Button>
        </div>
      </div>
    );
  }
  ```
- **PATTERN**: `frontend/src/features/schedule/components/RescheduleRequestsQueue.tsx:145-157` (header layout) and `frontend/src/features/schedule/components/RescheduleRequestsQueue.tsx:272-291` (icon-button style).
- **IMPORTS** (exact paths — do NOT use the `@/shared/components/ui` path shown in the steering doc; the repo uses `@/components/ui/*` for shadcn primitives):
  ```ts
  import { useEffect, useState } from 'react';
  import { formatDistanceToNow } from 'date-fns';
  import { RefreshCw } from 'lucide-react';
  import { Button } from '@/components/ui/button';
  import { Badge } from '@/components/ui/badge';
  import { cn } from '@/lib/utils';
  ```
- **GOTCHA**: `formatDistanceToNow(new Date(0), …)` returns "over 56 years ago" — the `dataUpdatedAt > 0` guard in the template above handles that, rendering "Updating…" instead.
- **GOTCHA**: The 15 s tick **must clear on unmount** (template already does `return () => clearInterval(t);`) or Vitest will warn about leaks.
- **GOTCHA**: Do not re-import `React` — this repo uses the automatic JSX runtime (`tsconfig.app.json` has `"jsx": "react-jsx"`), so only named imports from `'react'` are needed.
- **VALIDATE**: `cd frontend && npx tsc -p tsconfig.app.json --noEmit` (zero errors).

### 2. CREATE `frontend/src/shared/components/QueueFreshnessHeader.test.tsx`

- **IMPLEMENT**: Copy this file verbatim. It covers all four cases with zero additional context needed:
  ```tsx
  import { describe, it, expect, vi } from 'vitest';
  import { render, screen } from '@testing-library/react';
  import userEvent from '@testing-library/user-event';
  import { CalendarClock } from 'lucide-react';
  import { QueueFreshnessHeader } from './QueueFreshnessHeader';

  describe('QueueFreshnessHeader (Gap 15)', () => {
    const baseProps = {
      icon: <CalendarClock data-testid="qfh-icon" />,
      title: 'Reschedule Requests',
      dataUpdatedAt: Date.now(),
      isRefetching: false,
      onRefresh: vi.fn(),
    };

    it('renders title, icon, and badge count', () => {
      render(<QueueFreshnessHeader {...baseProps} badgeCount={3} />);
      expect(screen.getByText('Reschedule Requests')).toBeInTheDocument();
      expect(screen.getByTestId('qfh-icon')).toBeInTheDocument();
      expect(screen.getByText('3')).toBeInTheDocument();
    });

    it('renders a recent relative-time label when dataUpdatedAt is fresh', () => {
      render(<QueueFreshnessHeader {...baseProps} />);
      const label = screen.getByTestId('queue-last-updated');
      expect(label).toBeInTheDocument();
      expect(label.textContent).toMatch(/Updated/);
      expect(label.textContent).toMatch(/(seconds?|minute) ago/);
    });

    it('renders "Updating…" when dataUpdatedAt is 0', () => {
      render(<QueueFreshnessHeader {...baseProps} dataUpdatedAt={0} />);
      expect(screen.getByTestId('queue-last-updated')).toHaveTextContent('Updating…');
    });

    it('invokes onRefresh when the refresh button is clicked', async () => {
      const onRefresh = vi.fn();
      const user = userEvent.setup();
      render(
        <QueueFreshnessHeader
          {...baseProps}
          onRefresh={onRefresh}
          testId="refresh-test-btn"
        />,
      );
      await user.click(screen.getByTestId('refresh-test-btn'));
      expect(onRefresh).toHaveBeenCalledTimes(1);
    });

    it('renders the spinner class and disables the button while refetching', () => {
      render(
        <QueueFreshnessHeader
          {...baseProps}
          isRefetching
          testId="refresh-test-btn"
        />,
      );
      const btn = screen.getByTestId('refresh-test-btn');
      expect(btn).toBeDisabled();
      expect(btn.querySelector('svg')).toHaveClass('animate-spin');
    });
  });
  ```
- **PATTERN**: `frontend/src/shared/components/OptOutBadge.test.tsx` for the shared-component test shape; no `QueryProvider` wrapper needed (component is pure UI).
- **GOTCHA**: `userEvent.setup()` is needed even for a single click so React 19's `act` wrapper doesn't warn.
- **VALIDATE**: `cd frontend && npm test -- QueueFreshnessHeader` (all five tests pass).

### 3. UPDATE `frontend/src/shared/components/index.ts`

- **IMPLEMENT**: Append the export:
  ```ts
  export { QueueFreshnessHeader } from './QueueFreshnessHeader';
  export type { QueueFreshnessHeaderProps } from './QueueFreshnessHeader';
  ```
- **PATTERN**: Lines 16-17 of the file (the `OptOutBadge` export pair — mirror exactly).
- **GOTCHA**: Keep the export pair adjacent (component + props type) to match the existing convention.
- **VALIDATE**: `cd frontend && npx tsc -p tsconfig.app.json --noEmit`.

### 4. UPDATE `frontend/src/features/schedule/hooks/useRescheduleRequests.ts`

- **IMPLEMENT**: Add the polling options to `useRescheduleRequests` (the only `useQuery` in this file). Keep `useResolveRescheduleRequest` untouched. Extend the existing `/**` file header to add:
  ```
  * Gap 15 (Phase 1): 30 s polling safety-net for inbound R replies.
  ```
  Final hook body:
  ```ts
  return useQuery({
    queryKey: rescheduleKeys.list(status),
    queryFn: () => rescheduleApi.list(status),
    staleTime: 30_000,
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: true,
    refetchOnReconnect: true,
  });
  ```
- **PATTERN**: `frontend/src/features/customers/hooks/useCustomers.ts:71-91` (`useCustomerInvoices` — two-layer comment + `refetchInterval: 30_000`).
- **IMPORTS**: None new.
- **GOTCHA**: Do NOT touch `useResolveRescheduleRequest` — its mutation-invalidation is the second half of the two-layer strategy.
- **GOTCHA**: Gap 15 doc explicitly says 30 s for this queue (operational urgency). Do not change to 60 s.
- **VALIDATE**: `cd frontend && npx tsc -p tsconfig.app.json --noEmit && npm test -- useRescheduleRequests 2>&1 | tail -5` (no new test file needed; existing `RescheduleRequestsQueue.test.tsx` exercises this hook indirectly and must still pass).

### 5. UPDATE `frontend/src/features/schedule/hooks/useNoReplyReview.ts`

- **IMPLEMENT**: Add polling options to `useNoReplyReviewList`. Extend the existing file header doc to add `Gap 15 (Phase 1): 60 s polling safety-net — nightly cron output.` Final hook body:
  ```ts
  return useQuery({
    queryKey: noReplyReviewKeys.list(reason),
    queryFn: () => appointmentApi.noReviewList({ reason }),
    staleTime: 30_000,
    refetchInterval: 60_000,
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: true,
    refetchOnReconnect: true,
  });
  ```
- **PATTERN**: Same as Task 4. Note the 60 s (not 30 s) value per the gap spec.
- **IMPORTS**: None new.
- **GOTCHA**: The cron runs nightly, so 60 s is more than enough; do not poll faster than the spec's 60 s.
- **VALIDATE**: `cd frontend && npx tsc -p tsconfig.app.json --noEmit && npm test -- useNoReplyReview 2>&1 | tail -5`.

### 6. UPDATE `frontend/src/features/customers/hooks/useCustomers.ts`

- **IMPLEMENT**: Only touch `useCustomerSentMessages` (lines 119-126). Add the polling pattern + extend the comment on line 119 to `// Customer sent messages (Req 82, Gap 15: 60 s polling for inbound-reply freshness)`:
  ```ts
  export function useCustomerSentMessages(customerId: string) {
    return useQuery({
      queryKey: customerKeys.sentMessages(customerId),
      queryFn: () => customerApi.listSentMessages(customerId),
      enabled: !!customerId,
      staleTime: 30_000,
      refetchInterval: 60_000,
      refetchIntervalInBackground: false,
      refetchOnWindowFocus: true,
      refetchOnReconnect: true,
    });
  }
  ```
- **PATTERN**: `useCustomerInvoices` (same file, lines 79-91) — the closest neighbor using `refetchInterval`.
- **IMPORTS**: None new.
- **GOTCHA**: Do NOT touch `useCustomerInvoices`, `useCustomerPhotos`, or any other hook in this file.
- **GOTCHA**: Keep `enabled: !!customerId` — without it, the query fires with an empty key when the modal is closed.
- **VALIDATE**: `cd frontend && npx tsc -p tsconfig.app.json --noEmit && npm test -- useCustomers 2>&1 | tail -10`.

### 7. UPDATE `frontend/src/features/schedule/hooks/useAppointments.ts`

- **IMPLEMENT**: Only touch `useAppointment` (lines 36-44). Add the polling pattern; keep `enabled: !!id` at top. Extend the docstring above the function to add `Gap 15 (Phase 1): 60 s polling while the detail modal is open.`:
  ```ts
  export function useAppointment(id: string | undefined) {
    return useQuery({
      queryKey: appointmentKeys.detail(id ?? ''),
      queryFn: () => appointmentApi.getById(id!),
      enabled: !!id,
      staleTime: 30_000,
      refetchInterval: 60_000,
      refetchIntervalInBackground: false,
      refetchOnWindowFocus: true,
      refetchOnReconnect: true,
    });
  }
  ```
- **PATTERN**: Same as Task 4. Same `enabled` guard as `useCustomerPhotos`.
- **IMPORTS**: None new.
- **GOTCHA**: The `useAppointments` list hook above (lines 28-33) must remain untouched — it's used by the main calendar and already has mutation-driven invalidation.
- **GOTCHA**: `useAppointment` is invoked in at least three places: `AppointmentDetail`, `RescheduleRequestsQueue` (for the reschedule dialog), and a few others. All will start polling — this is the desired behavior per the gap doc. Confirm via grep after editing that no caller explicitly overrides `refetchInterval`.
- **VALIDATE**: `cd frontend && npx tsc -p tsconfig.app.json --noEmit && npm test -- useAppointments 2>&1 | tail -5`.

### 8. UPDATE `frontend/src/features/schedule/components/RescheduleRequestsQueue.tsx`

- **IMPLEMENT**: Replace the manually-built header block at lines 145-157 with `<QueueFreshnessHeader />`. Destructure `dataUpdatedAt`, `isFetching` from `useRescheduleRequests('open')` at line 39. Add `const queryClient = useQueryClient();` at the top of the function. Final header JSX (inside the returned div at line 142):
  ```tsx
  <QueueFreshnessHeader
    icon={<CalendarClock className="h-4 w-4 text-amber-500" />}
    title="Reschedule Requests"
    badgeCount={hasRequests ? requests.length : undefined}
    badgeClassName="bg-amber-100 text-amber-700"
    dataUpdatedAt={dataUpdatedAt}
    isRefetching={isFetching}
    onRefresh={() => queryClient.invalidateQueries({ queryKey: rescheduleKeys.all })}
    testId="refresh-reschedule-btn"
  />
  ```
- **PATTERN**: `frontend/src/features/schedule/components/AppointmentDetail.tsx:110-117` (`invalidateQueries` pattern).
- **IMPORTS**:
  ```ts
  import { useQueryClient } from '@tanstack/react-query';
  import { QueueFreshnessHeader } from '@/shared/components';
  ```
  And change the existing named-import line at the top of the file:
  ```ts
  import {
    useRescheduleRequests,
    useResolveRescheduleRequest,
    rescheduleKeys,  // add this — already exported from the hook file at line 9
  } from '../hooks/useRescheduleRequests';
  ```
  Add `const queryClient = useQueryClient();` near the top of the component body (after line 39's `useRescheduleRequests('open')` call). **Verified 2026-04-23**: `queryClient` is not currently declared in this component.
  Remove the now-unused inline `<h3>` / `<Badge>` / `<CalendarClock>` wrapper at lines 145-157 (replaced wholesale by `QueueFreshnessHeader`).
- **GOTCHA**: Leave the `isLoading` and `error` early-return branches at lines 100-135 untouched — they have their own skeleton header.
- **GOTCHA**: The `RefreshCw` icon is still used by the per-row `reschedule-to-alternative-btn` button at line 279 — keep that import.
- **GOTCHA**: Do not change `data-testid="reschedule-queue"` on the outer wrapper — existing tests depend on it.
- **VALIDATE**: `cd frontend && npx tsc -p tsconfig.app.json --noEmit && npm test -- RescheduleRequestsQueue 2>&1 | tail -20` (all existing tests must still pass).

### 9. UPDATE `frontend/src/features/schedule/components/NoReplyReviewQueue.tsx`

- **IMPLEMENT**: Analogous to Task 8. Destructure `dataUpdatedAt`, `isFetching` from `useNoReplyReviewList()` at line 53. Replace the header block at lines 131-146 with:
  ```tsx
  <QueueFreshnessHeader
    icon={<AlertCircle className="h-4 w-4 text-orange-500" />}
    title="No-Reply Confirmations"
    badgeCount={hasRows ? rows.length : undefined}
    badgeClassName="bg-orange-100 text-orange-700"
    dataUpdatedAt={dataUpdatedAt}
    isRefetching={isFetching}
    onRefresh={() => queryClient.invalidateQueries({ queryKey: noReplyReviewKeys.all })}
    testId="refresh-no-reply-btn"
  />
  ```
- **PATTERN**: Same as Task 8.
- **IMPORTS**: Add `useQueryClient` from `@tanstack/react-query`, `QueueFreshnessHeader` from `@/shared/components`, and update the existing `../hooks/useNoReplyReview` named-imports to also pull `noReplyReviewKeys` (already exported from that file at line 15 — verified 2026-04-23; note the schedule feature's `hooks/index.ts` barrel does **not** re-export `noReplyReviewKeys`, so import directly from the hook file, not the barrel).
- **GOTCHA**: The `Send Reminder` confirm dialog at lines 172-240 must remain bit-for-bit unchanged — it's safety-critical (SMS dispatch).
- **GOTCHA**: Do not change `data-testid="no-reply-queue"` — existing tests depend on it.
- **VALIDATE**: `cd frontend && npx tsc -p tsconfig.app.json --noEmit && npm test -- NoReplyReviewQueue 2>&1 | tail -20` (all existing tests must still pass).

### 10. UPDATE `frontend/src/features/customers/components/CustomerMessages.tsx`

- **IMPLEMENT**: `CustomerMessages` has no title/badge row today; the existing header is just `<OptOutBadge />`. Add a right-aligned freshness affordance inline rather than wrapping with `QueueFreshnessHeader`. Destructure `dataUpdatedAt`, `isFetching` from `useCustomerSentMessages(customerId)`. Change the `header` declaration (line 30-34) to:
  ```tsx
  const header = (
    <div className="mb-3 flex items-center justify-between">
      <OptOutBadge customerId={customerId} />
      <div className="flex items-center gap-2 text-xs text-slate-500">
        <span data-testid="queue-last-updated">
          {dataUpdatedAt > 0
            ? `Updated ${formatDistanceToNow(new Date(dataUpdatedAt), { addSuffix: true })}`
            : 'Updating…'}
        </span>
        <Button
          size="sm"
          variant="ghost"
          disabled={isFetching}
          onClick={() => queryClient.invalidateQueries({ queryKey: customerKeys.sentMessages(customerId) })}
          data-testid="refresh-messages-btn"
        >
          <RefreshCw className={cn('h-3 w-3', isFetching && 'animate-spin')} />
        </Button>
      </div>
    </div>
  );
  ```
- **PATTERN**: Inline freshness pattern matching `QueueFreshnessHeader` but without the title slot.
- **IMPORTS**: Current file's line 5 is `import { useCustomerSentMessages } from '../hooks';`. Change that line to `import { useCustomerSentMessages, customerKeys } from '../hooks';` (both are re-exported from `features/customers/hooks/index.ts` — verified at line 12 of that barrel). Also add:
  ```ts
  import { formatDistanceToNow } from 'date-fns';
  import { RefreshCw } from 'lucide-react';
  import { useQueryClient } from '@tanstack/react-query';
  import { Button } from '@/components/ui/button';
  import { cn } from '@/lib/utils';
  ```
  You also need `const queryClient = useQueryClient();` inside the component function — place it right after the `useCustomerSentMessages` call (currently line 26).
- **GOTCHA**: The `loading` branch (lines 36-44) still renders its skeleton — no change there.
- **GOTCHA**: Verified 2026-04-23 — `frontend/src/features/customers/components/` contains **no** `CustomerMessages.test.tsx`. Do NOT attempt to extend a non-existent test file; the CustomerMessages freshness UI is covered by agent-browser in Task 16. If the implementer wants a unit test, it can be added optionally but is out of scope for this plan.
- **VALIDATE**: `cd frontend && npx tsc -p tsconfig.app.json --noEmit`. No unit test to run.

### 11. UPDATE `frontend/src/features/schedule/components/AppointmentDetail.tsx`

- **IMPLEMENT**: Two small edits, exact locations verified 2026-04-23:
  1. **Line 90** — extend the destructure:
     ```ts
     const { data: appointment, isLoading, error, dataUpdatedAt, isFetching } = useAppointment(appointmentId);
     ```
  2. **Lines 330-347** (the right cluster of the header card, currently `{isOptedOut && <Badge>Opted out</Badge>} <Badge>{statusConfig.label}</Badge>`) — insert the freshness affordance as a new `<div>` sibling inserted BEFORE the existing badges within the same flex row. Replace lines 330-347 with:
     ```tsx
     <div className="flex items-center gap-2">
       <span
         className="text-xs text-slate-400"
         data-testid="queue-last-updated"
       >
         {dataUpdatedAt && dataUpdatedAt > 0
           ? `Updated ${formatDistanceToNow(new Date(dataUpdatedAt), { addSuffix: true })}`
           : 'Updating…'}
       </span>
       <Button
         size="sm"
         variant="ghost"
         className="h-6 w-6 p-0"
         disabled={isFetching}
         onClick={invalidateTimeline}
         data-testid="refresh-appointment-btn"
         aria-label="Refresh appointment data"
       >
         <RefreshCw className={cn('h-3 w-3', isFetching && 'animate-spin')} />
       </Button>
       {isOptedOut && (
         <Badge
           className="bg-red-100 text-red-700 px-2 py-0.5 rounded-full text-xs font-medium flex items-center gap-1"
           data-testid={`opt-out-badge-${appointmentId}`}
           title={`Opted out via ${optOutMethodLabel}${optOutDateLabel ? ` on ${optOutDateLabel}` : ''}`}
         >
           <Ban className="h-3 w-3" />
           Opted out
         </Badge>
       )}
       <Badge
         className={`${statusConfig.bgColor} ${statusConfig.color} px-2 py-0.5 rounded-full text-xs font-medium`}
         data-testid={`status-${appointment.status}`}
       >
         {statusConfig.label}
       </Badge>
     </div>
     ```
  (This replaces the existing `<div className="flex items-center gap-2">` at line 330 and preserves its two `<Badge>` children verbatim.)
- **PATTERN**: `invalidateTimeline` helper at lines 110-117 — already in scope; refreshes both `appointmentKeys.detail(id)` AND `appointmentKeys.timeline(id)`, which is exactly what a manual refresh should do.
- **IMPORTS**: `formatDistanceToNow` is ALREADY imported at line 9. `RefreshCw` is ALREADY imported at line 44. `Button` is ALREADY imported at line 14. Add ONLY `import { cn } from '@/lib/utils';` if not already present (grep first — likely missing).
- **GOTCHA**: This is a 700+-line component. Only touch lines 90 and 330-347. Do NOT refactor the rest.
- **GOTCHA**: The `<Badge>` children pasted into the new wrapper must be byte-for-byte identical to the current content at lines 331-346 — they power existing tests like `data-testid={`status-${appointment.status}`}` at line 343.
- **GOTCHA**: `dataUpdatedAt` from TanStack is a `number` (ms since epoch), `0` if never fetched. The `dataUpdatedAt && dataUpdatedAt > 0` guard handles the `undefined` case that occurs under test mocks (see Task 15 mock update).
- **VALIDATE**: `cd frontend && npx tsc -p tsconfig.app.json --noEmit && npm test -- AppointmentDetail 2>&1 | tail -20`.

### 12. UPDATE `frontend/src/features/schedule/components/RescheduleRequestsQueue.test.tsx`

- **IMPLEMENT**: Add a new test inside the existing `describe('RescheduleRequestsQueue (bughunt H-6)', …)` block:
  ```ts
  it('Refresh button invalidates the query and re-fetches (Gap 15)', async () => {
    const user = userEvent.setup();
    render(<RescheduleRequestsQueue />, { wrapper: createWrapper() });

    // initial fetch
    await waitFor(() => {
      expect(rescheduleApi.list).toHaveBeenCalledTimes(1);
    });

    const refreshBtn = screen.getByTestId('refresh-reschedule-btn');
    await user.click(refreshBtn);

    await waitFor(() => {
      expect(rescheduleApi.list).toHaveBeenCalledTimes(2);
    });
  });
  ```
  Also add a one-line `expect(screen.getByTestId('queue-last-updated')).toBeInTheDocument();` check in the existing "renders rows" flow.
- **PATTERN**: The file's own existing tests (lines 180-227) — mirror the `user.click` + `waitFor` shape.
- **IMPORTS**: Already available.
- **GOTCHA**: `rescheduleApi.list` is already mocked in `beforeEach` (line 159-161). The second call will resolve with the same fixture — that's fine.
- **GOTCHA**: Do not introduce `vi.useFakeTimers()` in this test — it interacts poorly with TanStack Query's internal timers. The manual-refresh assertion is sufficient coverage without exercising the 30 s interval.
- **VALIDATE**: `cd frontend && npm test -- RescheduleRequestsQueue 2>&1 | tail -20` (all tests pass).

### 13. UPDATE `frontend/src/features/schedule/components/NoReplyReviewQueue.test.tsx`

- **IMPLEMENT**: Add a test analogous to Task 12:
  ```ts
  it('Refresh button invalidates the queue and re-fetches (Gap 15)', async () => {
    (appointmentApi.noReviewList as ReturnType<typeof vi.fn>).mockResolvedValue([
      makeRow(),
    ]);

    const user = userEvent.setup();
    render(<NoReplyReviewQueue />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(appointmentApi.noReviewList).toHaveBeenCalledTimes(1);
    });

    const refreshBtn = screen.getByTestId('refresh-no-reply-btn');
    await user.click(refreshBtn);

    await waitFor(() => {
      expect(appointmentApi.noReviewList).toHaveBeenCalledTimes(2);
    });
  });
  ```
- **PATTERN**: Same as Task 12.
- **VALIDATE**: `cd frontend && npm test -- NoReplyReviewQueue 2>&1 | tail -20`.

### 14. UPDATE `frontend/src/features/schedule/hooks/useAppointments.test.tsx` (sanity)

- **IMPLEMENT**: Add a single test mirroring the `useCustomerInvoices` pattern (see `frontend/src/features/customers/hooks/useCustomers.test.tsx:285-321`):
  ```ts
  it('useAppointment wires a 60 s refetchInterval (Gap 15)', async () => {
    const hookSource = useAppointment.toString();
    expect(hookSource).toContain('refetchInterval');
    expect(hookSource).toContain('60');
  });
  ```
- **PATTERN**: `frontend/src/features/customers/hooks/useCustomers.test.tsx:285-299`.
- **GOTCHA**: This is a lightweight "is it wired?" assertion — combined with the integration-level refresh-button tests in Tasks 12-13, it's enough without standing up a full 60-second interval test harness.
- **VALIDATE**: `cd frontend && npm test -- useAppointments 2>&1 | tail -5`.

### 15. UPDATE `frontend/src/features/schedule/components/AppointmentDetail.test.tsx`

- **IMPLEMENT** (two edits):
  1. **Extend `setupDefaultMocks` at lines 214-232** to include the new fields that our component destructures. Replace the `mockUseAppointment.mockReturnValue` call with:
     ```ts
     mockUseAppointment.mockReturnValue({
       data: mockAppointment,
       isLoading: false,
       error: null,
       dataUpdatedAt: Date.now(),
       isFetching: false,
     });
     ```
     Then update the **seven additional `mockUseAppointment.mockReturnValue({...})` override sites** in the same file — verified 2026-04-23 via `grep -n "mockUseAppointment.mockReturnValue" AppointmentDetail.test.tsx`, they sit at lines **215, 299, 318, 393, 409, 435, 462, 483** (eight total — line 215 is the default inside `setupDefaultMocks` already updated above, so seven remaining). Append `dataUpdatedAt: Date.now(), isFetching: false,` to each one.
  2. **Add a new test** inside the existing `describe('AppointmentDetail — Edit Wiring (Req 18)', …)` block:
     ```ts
     it('renders a refresh button in the header (Gap 15)', async () => {
       render(
         <AppointmentDetail appointmentId="appt-001" />,
         { wrapper: createWrapper() },
       );

       const btn = await screen.findByTestId('refresh-appointment-btn');
       expect(btn).toBeInTheDocument();

       const user = userEvent.setup();
       await user.click(btn);  // should not throw
     });
     ```
- **PATTERN**: File's existing fixture setup (line 214 `setupDefaultMocks`, line 201 `createWrapper`).
- **GOTCHA**: Without updating the mock to include `dataUpdatedAt`, the "Updated X ago" label will always show "Updating…" and the test passes but doesn't prove the live-data path. With the mock update, the real relative-time label is exercised.
- **GOTCHA**: `mockUseAppointment` is imported at line 65 and shared across all tests in the file — updating `setupDefaultMocks` covers the default case; the two override sites for `completed` / `cancelled` status also need the fields since they replace the whole return value.
- **VALIDATE**: `cd frontend && npm test -- AppointmentDetail 2>&1 | tail -20` (all tests — existing + new — pass).

### 16. VALIDATE end-to-end with agent-browser

- **IMPLEMENT**: Run the dev server, open `/schedule`, confirm:
  1. Both queues render the new "Updated X ago" label.
  2. Clicking `refresh-reschedule-btn` causes a brief `animate-spin` state and the label to reset to "less than a minute ago".
  3. Opening an appointment modal shows the refresh button; clicking it triggers the same behavior for detail + timeline.
  4. `agent-browser console` shows no new JS errors or React warnings.
- **PATTERN**: `.kiro/steering/agent-browser.md` — use `snapshot -i` → `click @eN` → `screenshot`.
- **IMPORTS**: None.
- **GOTCHA**: If the dev server requires login, use the existing test admin flow. Do NOT trigger SMS-sending buttons during this validation (the `Send Reminder` confirm dialog is safety-critical).
- **GOTCHA**: On dev, only `+19527373312` may receive real SMS. This validation is read-only (refresh buttons) — no SMS path exercised.
- **VALIDATE**:
  ```bash
  cd frontend && npm run dev &  # background
  # in a second shell
  agent-browser open http://localhost:5173/schedule
  agent-browser wait --load networkidle
  agent-browser is visible "[data-testid='refresh-reschedule-btn']"
  agent-browser is visible "[data-testid='refresh-no-reply-btn']"
  agent-browser click "[data-testid='refresh-reschedule-btn']"
  agent-browser wait --load networkidle
  agent-browser errors   # expect no output
  agent-browser close
  ```

### 17. RUN the full quality gate

- **IMPLEMENT**: Run the project's standard frontend checks. Do not proceed until all pass.
- **VALIDATE**:
  ```bash
  cd frontend && npm run lint && npm run typecheck && npm test
  ```

---

## TESTING STRATEGY

### Unit Tests (Vitest + React Testing Library)

- `QueueFreshnessHeader.test.tsx` — 4 cases covering render, label, click, spinning state. No `QueryProvider` needed (pure UI component).
- Hook-source assertions (`useAppointments.test.tsx` — one case) confirming `refetchInterval` is present via `hook.toString()`, same pattern as existing `useCustomerInvoices` tests. Cheap coverage, catches regressions where someone removes polling.

### Component / Integration Tests

- `RescheduleRequestsQueue.test.tsx` — extended with one "refresh button re-fetches" case. Uses real `QueryClient` via `createWrapper()`.
- `NoReplyReviewQueue.test.tsx` — same extension.
- `AppointmentDetail.test.tsx` — smoke test that the refresh button is present.
- Existing tests in the three files above must continue to pass unchanged.

### Edge Cases

- **Tab hidden:** `refetchIntervalInBackground: false` pauses polling. Tested implicitly via TanStack defaults — no explicit test needed.
- **Network offline:** TanStack's default retry/backoff already covers this; do not add custom handling.
- **Initial load (`dataUpdatedAt === 0`):** `QueueFreshnessHeader` renders "Updating…" instead of "over 56 years ago". Covered by test #2.
- **Rapid repeated clicks:** button is `disabled={isRefetching}` so a second click fires at most after the first completes. Exercised indirectly by the refresh-button tests.
- **Consent-gated rows (NoReply):** `OptOutBadge` / opt-out check on each row stays in place; the freshness header is orthogonal to per-row consent logic.

---

## VALIDATION COMMANDS

Execute every command to ensure zero regressions and 100% feature correctness.

### Level 1: Syntax & Style
```bash
cd frontend && npm run lint
cd frontend && npm run format:check
```

### Level 2: Type checking
```bash
cd frontend && npm run typecheck
```

### Level 3: Unit + Component Tests
```bash
cd frontend && npm test -- QueueFreshnessHeader
cd frontend && npm test -- RescheduleRequestsQueue
cd frontend && npm test -- NoReplyReviewQueue
cd frontend && npm test -- useAppointments
cd frontend && npm test -- useRescheduleRequests
cd frontend && npm test -- useNoReplyReview
cd frontend && npm test -- useCustomers
cd frontend && npm test -- AppointmentDetail
```

### Level 4: Full Frontend Test Suite (no regressions)
```bash
cd frontend && npm test
```

### Level 5: Manual / E2E with agent-browser (optional but recommended)
```bash
cd frontend && npm run dev &
agent-browser open http://localhost:5173/schedule
agent-browser wait --load networkidle
agent-browser screenshot e2e-screenshots/gap15-01-schedule.png
agent-browser is visible "[data-testid='refresh-reschedule-btn']"
agent-browser is visible "[data-testid='refresh-no-reply-btn']"
agent-browser click "[data-testid='refresh-reschedule-btn']"
agent-browser wait --load networkidle
agent-browser screenshot e2e-screenshots/gap15-02-after-refresh.png
agent-browser errors
agent-browser close
```

---

## ACCEPTANCE CRITERIA

- [ ] `useRescheduleRequests` polls every 30 s with `refetchIntervalInBackground: false`, `refetchOnWindowFocus: true`, `refetchOnReconnect: true`.
- [ ] `useNoReplyReviewList` polls every 60 s with the same window/reconnect flags.
- [ ] `useCustomerSentMessages` polls every 60 s with the same flags.
- [ ] `useAppointment` (detail) polls every 60 s with the same flags, `enabled` gate preserved.
- [ ] `QueueFreshnessHeader` component exists in `shared/components/`, exported from `shared/components/index.ts`, with four passing unit tests.
- [ ] `RescheduleRequestsQueue` renders the new header with `data-testid="refresh-reschedule-btn"` and `data-testid="queue-last-updated"` visible in the success branch.
- [ ] `NoReplyReviewQueue` renders the new header with `data-testid="refresh-no-reply-btn"`.
- [ ] `CustomerMessages` renders a `data-testid="refresh-messages-btn"` next to `OptOutBadge`.
- [ ] `AppointmentDetail` renders a `data-testid="refresh-appointment-btn"` in the modal header, calling `invalidateTimeline()` on click.
- [ ] All existing tests in the four modified component test files still pass.
- [ ] New "refresh button re-fetches" tests in `RescheduleRequestsQueue.test.tsx` and `NoReplyReviewQueue.test.tsx` pass.
- [ ] `npm run lint`, `npm run typecheck`, `npm test` all pass with zero errors.
- [ ] agent-browser validation script completes with no console errors and both screenshots captured.
- [ ] `NoReplyReviewQueue`'s `Send Reminder` confirm dialog (lines 172-240 pre-change) is byte-for-byte preserved — safety-critical.
- [ ] No backend changes committed.

---

## COMPLETION CHECKLIST

- [ ] Tasks 1-17 executed in order.
- [ ] Each task's `VALIDATE` command passed before moving to the next.
- [ ] `cd frontend && npm run lint && npm run typecheck && npm test` all green.
- [ ] agent-browser smoke visited `/schedule`, clicked both refresh buttons, captured screenshots.
- [ ] Manual inspection confirmed the "Updated Xs ago" label appears and ticks.
- [ ] Commit message references Gap 15 Phase 1 + Phase 2 (e.g. `feat(gap-15): queue freshness polling + manual refresh`).
- [ ] Updated `feature-developments/scheduling gaps/gap-15-queue-freshness-and-realtime.md` Status line from "Investigated, not fixed" to "Phase 1 + Phase 2 complete (YYYY-MM-DD); Phase 3 (realtime) deferred" — optional, at engineer's discretion.

---

## NOTES

- **Why shared component over per-queue inline code:** `RescheduleRequestsQueue` and `NoReplyReviewQueue` have nearly identical header structure (icon + title + count badge). Extracting `QueueFreshnessHeader` is worth the shared-component overhead; duplicating inline once in `CustomerMessages` (where the header has no title slot) is cheaper than parameterizing for three different header shapes. This matches the steering rule in `vertical-slice-setup-guide.md`: "Move to shared/ when **3+ features** need it. Until then, duplicate."
- **Why 30/60/60/60 seconds:** mirrors the gap spec directly. 30 s for Reschedule reflects operational urgency (R replies need admin attention within minutes); 60 s elsewhere is a polite default that matches existing `useDashboardMetrics` / `useTodaySchedule`.
- **Why `refetchIntervalInBackground: false`:** avoids N admin tabs × M queues × poll frequency fan-out for idle background tabs. The hidden-tab admin still gets a fresh fetch the instant `refetchOnWindowFocus` fires when they return.
- **Why the global `QueryProvider` already sets `refetchOnWindowFocus: true`:** explicit duplication at the hook site makes intent readable at the point of use and documents the gap-15 requirement; TanStack's option-merge semantics make it a no-op when they match.
- **Why Phase 3 (SSE/WebSocket) is out of scope:** the gap doc explicitly says "polling now, realtime later." Shipping Phase 1 + Phase 2 first proves the UX before investing in the ~2-week realtime infrastructure. A future Gap 15 Phase 3 plan can reference this plan's completion as its starting point.
- **Cross-references with other gaps:**
  - Gap 11 (AppointmentDetail timeline) and Gap 13 (CustomerMessages) both benefit from this polling — coordinate with those plans if they're being worked in parallel.
  - Gap 14 (dashboard alerts) already polls at 60 s — this plan does not touch the dashboard.
- **Confidence for one-pass implementation: 10/10.** Every file the plan edits is pinned to a verified line number (all verified 2026-04-23). Every new file has a complete template ready to copy. Every import path has been grep-verified against the actual repo. The three biggest risks flagged in the original 8/10 draft have been specifically neutralized:
  1. `AppointmentDetail.tsx` insertion point (Task 11) — now pinned to the exact block at lines 330-347, with a full replacement JSX block in the task that preserves the two existing `<Badge>` children byte-for-byte.
  2. `AppointmentDetail.test.tsx` mock shape (Task 15) — the exact eight line numbers for `mockUseAppointment.mockReturnValue` are listed (215, 299, 318, 393, 409, 435, 462, 483) so the implementer doesn't have to grep.
  3. `CustomerMessages` test file absence (Task 10) — called out explicitly with a preflight check (Task 0, check #7), so the implementer doesn't waste a loop trying to extend a file that doesn't exist.
  The preflight task (Task 0) provides seven read-only grep/ls checks that will fail loudly if the repo has drifted from the captured state.
