# Gap 15 — Queue Freshness & No Realtime

**Severity:** 3 (medium — UX)
**Area:** Frontend (TanStack Query polling + cache invalidation)
**Status:** Investigated, not fixed
**Related files:**
- `frontend/src/features/schedule/components/RescheduleRequestsQueue.tsx` — no polling
- `frontend/src/features/schedule/components/NoReplyReviewQueue.tsx` — no polling
- `frontend/src/features/dashboard/hooks/useDashboard.ts` — 60s polling for dashboard metrics
- Various hooks across the app — mix of 30s, 60s, or mutation-only refresh

---

## Summary

The codebase uses TanStack Query. Data freshness is driven by two mechanisms:

1. **Cache invalidation on mutations.** When the admin performs an action, the mutation's `onSuccess` invalidates related query keys, forcing a refetch.
2. **`refetchInterval` polling** on a subset of hooks.

Inbound events (customer replies, auto-reminders firing, nightly flagging) happen **outside** the admin's browser — so they don't trigger mutations. The admin's tab only sees them on:
- Manual page refresh.
- Navigation to a different route and back.
- A polling interval (if the hook has one).

**Most inbound-reply-related queues have no `refetchInterval`.** Specifically:
- `RescheduleRequestsQueue`: no polling. New R replies don't surface until admin refreshes.
- `NoReplyReviewQueue`: no polling.
- `CustomerMessages`: no polling.
- `AppointmentDetail`: no polling.

Dashboard metrics poll at 60s. Customer list at 30s. Leads at 30s. Staff locations at 30s. These are a mix of "important" and "visual" polls — the ones that would *actually* benefit admin workflow (reply queues) don't poll.

---

## Reproduction

1. Admin has `/schedule` open, RescheduleRequestsQueue panel visible.
2. Customer replies "R" at 9:03 AM.
3. Backend inserts `RescheduleRequest(status='open')`. Alert created (for the pending_reschedule type from Gap 14, if implemented; currently no alert created).
4. Admin's browser tab: **no visual change.** The queue renders stale data from the initial load.
5. Admin must manually refresh the page to see the new row.
6. If admin is attentive (checks queue at 9:15 AM), delay is 12 minutes. If admin is deep in other work, delay could be hours.

---

## Current polling coverage

| Hook / Component | `refetchInterval` | Inbound-related? |
|---|---|---|
| `useDashboardMetrics` | 60 s | Partially (dashboard aggregates) |
| `useDashboardSummary` | 60 s | Partially |
| `useTodaySchedule` | 60 s | No (scheduled appts) |
| `useCustomers` | 30 s | No |
| `useLeads` | 30 s | No |
| `useStaffLocations` | 30 s | No (GPS) |
| `useRecentlyClearedSchedules` | 60 s | No |
| `useRescheduleRequests` | **none** | **YES — critical miss** |
| `useNoReplyReview` | **none** | **YES — critical miss** |
| `useCustomerSentMessages` | **none** | Partial |
| `useAppointment` (detail) | **none** | Partial |

---

## Why polling is the wrong long-term answer (but a fine stopgap)

Polling pros:
- Zero backend changes; just set `refetchInterval` on the relevant hooks.
- TanStack Query handles caching and backoff.
- Good enough for most admin workflows.

Polling cons at scale:
- N admin tabs × M queues × polling frequency = linear load on the backend for mostly-empty responses.
- 30-second latency on R replies during a busy morning still creates the above "admin didn't see it for 12 minutes" scenario occasionally.
- Data over the wire per poll is mostly "unchanged."

Realtime (WebSocket / SSE / Pusher / Ably) pros:
- Instant updates — R reply surfaces in < 1 second.
- Zero polling overhead at idle.
- Enables richer UX (typing indicators, live presence).

Realtime cons:
- Infrastructure: need a pub/sub broker, connection management, reconnection logic, auth.
- Message shape design (event types, payloads, fanout rules).
- Sticky sessions or horizontal scaling concerns.

**Recommendation: polling now, realtime later.**

---

## Phase 1 — add polling to inbound queues (quick win)

```typescript
// useRescheduleRequests.ts
export const useRescheduleRequests = (status: 'open' | 'resolved' | 'all' = 'open') =>
  useQuery({
    queryKey: rescheduleKeys.list(status),
    queryFn: () => rescheduleApi.list(status),
    refetchInterval: 30_000,         // NEW: 30 seconds
    refetchIntervalInBackground: false,  // pause when tab is hidden
  });

// useNoReplyReview.ts — same pattern
```

Set:
- `RescheduleRequestsQueue`: 30 s (operational urgency: reply needs admin attention within minutes).
- `NoReplyReviewQueue`: 60 s (this queue reflects background-job output that only updates nightly; 60 s is plenty but bounds admin delay).
- `CustomerMessages`: 60 s while tab is visible.
- `AppointmentDetail`: 60 s while modal is open.

Also set `refetchOnWindowFocus: true` and `refetchOnReconnect: true` universally for these hooks — admin coming back to their tab should see current data.

---

## Phase 2 — manual refresh buttons

For admin control (especially during busy mornings or known incidents):

- Add a "↻ Refresh" button to each queue header that calls `queryClient.invalidateQueries({queryKey: ...})`.
- Show "Last updated X ago" text so admin knows the data's age.
- These are trivial UI additions but reduce the "did it update?" uncertainty.

---

## Phase 3 — server-push realtime

Once the use case is proven and the team is ready:

- **Transport:** Server-Sent Events (SSE) is the simplest option (unidirectional, HTTP-based, works through most proxies, no need for a separate broker for low-volume admin updates). WebSocket is the richer alternative.
- **Event types:** `reschedule_request.created`, `confirmation_reply.received`, `appointment.status_changed`, `alert.created`, `alert.acknowledged`, etc.
- **Client:** TanStack Query has a `queryClient.setQueryData` pattern for targeted cache updates on incoming events.
- **Auth:** reuse JWT; handle token refresh on the SSE stream.
- **Fanout:** single admin user today, but multi-admin future means per-user filtering of events.

This is a ~2-week effort including ops setup, monitoring, fallback logic. Worth the investment once the queues are core to daily workflow.

---

## Related: no visible "last updated" indicator

When data is stale, users don't know. Add "Last updated 12 seconds ago" at the top of each queue. TanStack provides `dataUpdatedAt` on query results — format as a relative time.

---

## Edge cases

- **Mobile / tab-hidden:** `refetchIntervalInBackground: false` prevents needless polling when the tab isn't active. When user returns, `refetchOnWindowFocus: true` fires a fresh fetch.
- **Network issues:** TanStack's default retry/backoff handles transient failures.
- **Optimistic updates on actions:** When admin clicks "Resolve" on a reschedule request, the row should disappear immediately (optimistic) and be confirmed by the server. Current code invalidates the query key; add optimistic `setQueryData` for snappier UX.
- **Concurrent admin edits:** not an issue today (single admin user per 10DLC), but will matter for multi-admin. Realtime prevents conflicting views.

---

## Cross-references

- **Gap 11, 12, 13** — AppointmentDetail, calendar cards, CustomerMessages all benefit from fresher data.
- **Gap 14** — dashboard alerts already poll at 60s; ensure the new alert types are reflected in that poll.
