// useScheduleVisit.ts
// Single source of truth for the modal's state. Both the form fields and the
// calendar grid are views of `pick`; this hook owns the reconciliation.
//
// IMPORTANT: do not duplicate this state in WeekCalendar or ScheduleFields —
// they should consume `pick` + `setPickFromX` from this hook.

import { useCallback, useEffect, useMemo, useState } from 'react';
import type {
  EstimateBlock,
  Pick,
  SalesEntry,
  ScheduleVisitRequest,
  ScheduleVisitResponse,
} from './data-shapes';

const SLOT_MIN = 30;

type Args = {
  entry: SalesEntry;
  defaultAssigneeId: string;
  now: Date;
};

export function useScheduleVisit({ entry, defaultAssigneeId, now }: Args) {
  // ---- pick (the one true picked slot) ----
  const initial = entry.appointment
    ? {
        date: entry.appointment.date,
        start: entry.appointment.start,
        end: entry.appointment.end,
      }
    : null;
  const [pick, setPick] = useState<Pick | null>(initial);

  // ---- companion form fields ----
  const [durationMin, setDurationMin] = useState<30 | 60 | 90 | 120>(60);
  const [assignedTo, setAssignedTo] = useState<string>(
    entry.appointment?.assigned_to ?? defaultAssigneeId,
  );
  const [internalNotes, setInternalNotes] = useState('');
  const [sendConfirmationText, setSendConfirmationText] = useState(true);

  // ---- visible week ----
  const [weekStart, setWeekStart] = useState<Date>(() =>
    startOfWeek(initial ? new Date(initial.date + 'T12:00') : now),
  );

  // ---- existing estimates fetched per week ----
  const [estimates, setEstimates] = useState<EstimateBlock[]>([]);
  const [loadingWeek, setLoadingWeek] = useState(false);
  useEffect(() => {
    let cancelled = false;
    setLoadingWeek(true);
    fetchWeekEstimates(weekStart, assignedTo)
      .then((rows) => !cancelled && setEstimates(rows))
      .finally(() => !cancelled && setLoadingWeek(false));
    return () => {
      cancelled = true;
    };
  }, [weekStart, assignedTo]);

  // ---- pick mutators ----
  const setPickFromCalendarClick = useCallback(
    (date: string, slotStartMin: number) => {
      setPick({
        date,
        start: slotStartMin,
        end: slotStartMin + durationMin,
      });
    },
    [durationMin],
  );

  const setPickFromCalendarDrag = useCallback(
    (date: string, startMin: number, endMin: number) => {
      // endMin is exclusive; caller already added one slot.
      setPick({ date, start: startMin, end: endMin });
      setDurationMin(((endMin - startMin) as 30 | 60 | 90 | 120) ?? 60);
    },
    [],
  );

  const setPickDate = useCallback((date: string) => {
    setPick((p) => (p ? { ...p, date } : { date, start: 14 * 60, end: 14 * 60 + 60 }));
    const ws = startOfWeek(new Date(date + 'T12:00'));
    setWeekStart((cur) => (iso(cur) === iso(ws) ? cur : ws));
  }, []);

  const setPickStart = useCallback(
    (startMin: number) => {
      setPick((p) =>
        p ? { ...p, start: startMin, end: startMin + durationMin } : null,
      );
    },
    [durationMin],
  );

  const setPickDuration = useCallback((min: 30 | 60 | 90 | 120) => {
    setDurationMin(min);
    setPick((p) => (p ? { ...p, end: p.start + min } : null));
  }, []);

  // ---- conflict detection ----
  const conflicts = useMemo(() => {
    if (!pick) return [];
    return estimates.filter(
      (e) =>
        e.date === pick.date &&
        !(e.end <= pick.start || e.start >= pick.end),
    );
  }, [pick, estimates]);
  const hasConflict = conflicts.length > 0;

  // ---- submit ----
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const submit = useCallback(async (): Promise<SalesEntry | null> => {
    if (!pick) return null;
    setSubmitting(true);
    setError(null);
    try {
      const payload: ScheduleVisitRequest = {
        date: pick.date,
        start: pick.start,
        end: pick.end,
        assigned_to: assignedTo,
        internal_notes: internalNotes || undefined,
        send_confirmation_text: sendConfirmationText,
      };
      const isReschedule = entry.status === 'estimate_scheduled';
      const res: ScheduleVisitResponse = await postSchedule(
        entry.id,
        payload,
        isReschedule,
      );
      return res.entry;
    } catch (e: any) {
      setError(e?.message ?? 'Could not schedule.');
      return null;
    } finally {
      setSubmitting(false);
    }
  }, [pick, assignedTo, internalNotes, sendConfirmationText, entry]);

  return {
    // state
    pick,
    durationMin,
    assignedTo,
    internalNotes,
    sendConfirmationText,
    weekStart,
    estimates,
    loadingWeek,
    conflicts,
    hasConflict,
    submitting,
    error,

    // setters (UI should use these, not setState directly)
    setPickFromCalendarClick,
    setPickFromCalendarDrag,
    setPickDate,
    setPickStart,
    setPickDuration,
    setAssignedTo,
    setInternalNotes,
    setSendConfirmationText,
    setWeekStart,

    // actions
    submit,
  };
}

// ---- helpers ----
export const SLOT_SIZE_MIN = SLOT_MIN;

function startOfWeek(d: Date): Date {
  const nd = new Date(d.getFullYear(), d.getMonth(), d.getDate());
  const day = nd.getDay();
  const diff = day === 0 ? -6 : 1 - day; // Monday-start
  nd.setDate(nd.getDate() + diff);
  return nd;
}
function iso(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

// ---- API stubs (replace with the real fetcher / RTK Query / etc.) ----
async function fetchWeekEstimates(
  weekStart: Date,
  _assignee: string,
): Promise<EstimateBlock[]> {
  // TODO: GET /api/sales/estimates/calendar?weekStart=...&assignee=...
  return [];
}
async function postSchedule(
  _entryId: string,
  _payload: ScheduleVisitRequest,
  _isReschedule: boolean,
): Promise<ScheduleVisitResponse> {
  // TODO: POST or PUT /api/sales/:id/schedule-visit
  throw new Error('not implemented');
}
