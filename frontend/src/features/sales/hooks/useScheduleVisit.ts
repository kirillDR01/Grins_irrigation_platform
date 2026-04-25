import { useCallback, useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import { useQueryClient } from '@tanstack/react-query';
import { format } from 'date-fns';
import {
  useSalesCalendarEvents,
  useCreateCalendarEvent,
  useUpdateCalendarEvent,
  pipelineKeys,
} from './useSalesPipeline';
import {
  minToHHMMSS,
  hhmmssToMin,
  startOfWeek,
  iso,
  eventToBlock,
  detectConflicts,
} from '../lib/scheduleVisitUtils';
import type {
  Pick,
  SalesCalendarEvent,
  SalesEntry,
  EstimateBlock,
} from '../types/pipeline';

type Args = {
  entry: SalesEntry;
  customerId: string;
  customerName: string;
  jobSummary: string;
  /** Most recent existing event for this entry (reschedule path). */
  currentEvent: SalesCalendarEvent | null;
  defaultAssigneeId?: string | null;
  /** For tests. */
  now?: Date;
};

export function useScheduleVisit({
  entry,
  customerId,
  customerName,
  jobSummary,
  currentEvent,
  defaultAssigneeId,
  now: nowProp,
}: Args) {
  const qc = useQueryClient();
  const [now, setNow] = useState<Date>(() => nowProp ?? new Date());
  useEffect(() => {
    if (nowProp) return; // tests pass deterministic `now`
    const id = setInterval(() => setNow(new Date()), 60_000);
    return () => clearInterval(id);
  }, [nowProp]);

  const initialPick: Pick | null = useMemo(
    () =>
      currentEvent?.start_time && currentEvent.end_time
        ? {
            date: currentEvent.scheduled_date,
            start: hhmmssToMin(currentEvent.start_time),
            end: hhmmssToMin(currentEvent.end_time),
          }
        : null,
    [currentEvent],
  );

  const [pick, setPick] = useState<Pick | null>(initialPick);
  const [durationMin, setDurationMin] = useState<30 | 60 | 90 | 120>(60);
  const [assignedToUserId, setAssignedToUserId] = useState<string | null>(
    currentEvent?.assigned_to_user_id ?? defaultAssigneeId ?? null,
  );
  const [internalNotes, setInternalNotes] = useState<string>(
    currentEvent?.notes ?? '',
  );
  const [openedAt] = useState<Date>(() => new Date());

  const [weekStart, setWeekStart] = useState<Date>(() =>
    startOfWeek(
      initialPick
        ? new Date(initialPick.date + 'T12:00')
        : nowProp ?? new Date(),
    ),
  );

  const weekEnd = useMemo(() => {
    const d = new Date(weekStart);
    d.setDate(d.getDate() + 6);
    return d;
  }, [weekStart]);

  const { data: weekEvents, isLoading: loadingWeek } = useSalesCalendarEvents({
    start_date: format(weekStart, 'yyyy-MM-dd'),
    end_date: format(weekEnd, 'yyyy-MM-dd'),
  });

  const estimates: EstimateBlock[] = useMemo(
    () =>
      (weekEvents ?? []).map((e) =>
        eventToBlock(
          e,
          // For other-customer estimates we don't know the name; show the title as fallback.
          e.customer_id === customerId ? customerName : e.title,
          e.customer_id === customerId ? jobSummary : '',
        ),
      ),
    [weekEvents, customerId, customerName, jobSummary],
  );

  const conflicts = useMemo(
    () => detectConflicts(pick, estimates),
    [pick, estimates],
  );
  const hasConflict = conflicts.length > 0;

  // ── pick mutators ──
  const setPickFromCalendarClick = useCallback(
    (date: string, slotStartMin: number) => {
      setPick({ date, start: slotStartMin, end: slotStartMin + durationMin });
    },
    [durationMin],
  );

  const setPickFromCalendarDrag = useCallback(
    (date: string, startMin: number, endMin: number) => {
      setPick({ date, start: startMin, end: endMin });
      const span = endMin - startMin;
      if ([30, 60, 90, 120].includes(span)) {
        setDurationMin(span as 30 | 60 | 90 | 120);
      }
    },
    [],
  );

  const setPickDate = useCallback((date: string) => {
    setPick((p) =>
      p ? { ...p, date } : { date, start: 14 * 60, end: 14 * 60 + 60 },
    );
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

  const setPickDuration = useCallback((m: 30 | 60 | 90 | 120) => {
    setDurationMin(m);
    setPick((p) => (p ? { ...p, end: p.start + m } : null));
  }, []);

  // ── submit ──
  const create = useCreateCalendarEvent();
  const update = useUpdateCalendarEvent();
  const [error, setError] = useState<string | null>(null);
  const [isConflictError, setIsConflictError] = useState(false);

  const submit = useCallback(async (): Promise<{
    ok: boolean;
    conflict?: boolean;
  }> => {
    if (!pick) return { ok: false };
    setError(null);
    setIsConflictError(false);
    const payload = {
      sales_entry_id: entry.id,
      customer_id: customerId,
      // Hyphen (not em-dash) — matches existing SalesCalendar.tsx convention.
      title: `Estimate - ${customerName}`,
      scheduled_date: pick.date,
      start_time: minToHHMMSS(pick.start),
      end_time: minToHHMMSS(pick.end),
      notes: internalNotes || null,
      assigned_to_user_id: assignedToUserId,
    };
    try {
      if (currentEvent) {
        await update.mutateAsync({ eventId: currentEvent.id, body: payload });
      } else {
        await create.mutateAsync(payload);
      }
      return { ok: true };
    } catch (err) {
      if (axios.isAxiosError(err) && err.response?.status === 409) {
        setIsConflictError(true);
        setError('Slot was just taken — pick another time.');
        qc.invalidateQueries({ queryKey: pipelineKeys.calendarEvents() });
        return { ok: false, conflict: true };
      }
      setError(err instanceof Error ? err.message : 'Could not schedule.');
      return { ok: false };
    }
  }, [
    pick,
    entry.id,
    customerId,
    customerName,
    internalNotes,
    assignedToUserId,
    currentEvent,
    create,
    update,
    qc,
  ]);

  const isDirty = useMemo(() => {
    const initialEq = (a: Pick | null, b: Pick | null) =>
      (a === null && b === null) ||
      (!!a && !!b && a.date === b.date && a.start === b.start && a.end === b.end);
    return (
      !initialEq(pick, initialPick) ||
      internalNotes !== (currentEvent?.notes ?? '')
    );
  }, [pick, initialPick, internalNotes, currentEvent]);

  return {
    // state
    pick,
    durationMin,
    assignedToUserId,
    internalNotes,
    weekStart,
    estimates,
    loadingWeek,
    conflicts,
    hasConflict,
    submitting: create.isPending || update.isPending,
    error,
    isConflictError,
    isDirty,
    openedAt,
    now,
    isReschedule: !!currentEvent,
    // setters
    setPickFromCalendarClick,
    setPickFromCalendarDrag,
    setPickDate,
    setPickStart,
    setPickDuration,
    setAssignedToUserId,
    setInternalNotes,
    setWeekStart,
    // actions
    submit,
  };
}
