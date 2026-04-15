import { useCallback, useMemo, useState } from 'react';
import { startOfWeek, endOfWeek, format, isSameWeek } from 'date-fns';
import { CalendarIcon } from 'lucide-react';
import { Calendar } from '@/components/ui/calendar';
import { Button } from '@/components/ui/button';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import { cn } from '@/lib/utils';
import { jobApi } from '../api/jobApi';
import type { Job } from '../types';

interface JobWeekEditorProps {
  job: Pick<Job, 'id' | 'status' | 'target_start_date' | 'target_end_date'>;
  /** Called after a successful save with the updated (start, end) ISO strings. */
  onSaved?: (startIso: string, endIso: string) => void;
  /** Extra className for the trigger button. */
  className?: string;
}

/** Align any date to its Monday–Sunday week range. */
function alignToWeek(d: Date): { monday: Date; sunday: Date } {
  const monday = startOfWeek(d, { weekStartsOn: 1 });
  const sunday = endOfWeek(d, { weekStartsOn: 1 });
  return { monday, sunday };
}

function formatIsoLocal(d: Date): string {
  // Mirror the backend's date model: local yyyy-MM-dd, no TZ suffix.
  return format(d, 'yyyy-MM-dd');
}

/**
 * Inline editor for a job's target service week.
 *
 * Click the "Week of M/D/YYYY" button → popover opens with a week-picker
 * calendar → select any day → the containing Mon–Sun is saved in place.
 *
 * Only jobs in `to_be_scheduled` are editable; for any other status the
 * cell renders as plain text (the backend would reject the edit, and
 * appointments attached to scheduled jobs can't be rewindowed here).
 */
export function JobWeekEditor({ job, onSaved, className }: JobWeekEditorProps) {
  const [open, setOpen] = useState(false);
  // Draft state so the row reflects the new week immediately on save.
  const [startOverride, setStartOverride] = useState<string | null>(null);
  const [endOverride, setEndOverride] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const effectiveStart = startOverride ?? job.target_start_date ?? null;
  const effectiveEnd = endOverride ?? job.target_end_date ?? null;

  const selectedMonday = useMemo(() => {
    if (!effectiveStart) return null;
    // Backend ISO dates come as "YYYY-MM-DD" (sometimes with a T suffix).
    const iso = effectiveStart.split('T')[0];
    const [y, m, d] = iso.split('-').map(Number);
    return new Date(y, m - 1, d);
  }, [effectiveStart]);

  const editable = job.status === 'to_be_scheduled';

  const displayText = selectedMonday
    ? `Week of ${format(selectedMonday, 'M/d/yyyy')}`
    : 'No week set';

  const handleSelect = useCallback(
    async (day: Date | undefined) => {
      if (!day) return;
      const { monday, sunday } = alignToWeek(day);
      const startIso = formatIsoLocal(monday);
      const endIso = formatIsoLocal(sunday);
      // Don't bother sending if the chosen week equals the current one.
      if (startIso === (effectiveStart ?? '').split('T')[0]) {
        setOpen(false);
        return;
      }
      setSaving(true);
      setError(null);
      try {
        await jobApi.update(job.id, {
          target_start_date: startIso,
          target_end_date: endIso,
        });
        setStartOverride(startIso);
        setEndOverride(endIso);
        setOpen(false);
        onSaved?.(startIso, endIso);
      } catch (err) {
        // Surface a short inline error; leave popover open so the admin
        // can retry or abandon without losing context.
        const message =
          err instanceof Error && err.message ? err.message : 'Save failed';
        setError(message);
      } finally {
        setSaving(false);
      }
    },
    [effectiveStart, job.id, onSaved],
  );

  // Highlight the full Mon-Sun range in the calendar.
  const modifiers = useMemo(() => {
    if (!selectedMonday) return {};
    return {
      selectedWeek: (day: Date) =>
        isSameWeek(day, selectedMonday, { weekStartsOn: 1 }),
    };
  }, [selectedMonday]);

  const modifiersClassNames = useMemo(
    () => ({
      selectedWeek:
        'bg-teal-100 text-teal-800 rounded-none first:rounded-l-md last:rounded-r-md',
    }),
    [],
  );

  if (!editable) {
    // Plain text for any non-to_be_scheduled job. Keep the test id stable
    // so existing tests that query `week-of-<id>` still work.
    return (
      <span
        className={cn('text-sm text-slate-600', className)}
        data-testid={`week-of-${job.id}`}
      >
        {displayText}
      </span>
    );
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="ghost"
          size="sm"
          disabled={saving}
          className={cn(
            'h-auto px-2 py-1 text-sm font-normal hover:bg-teal-50',
            !selectedMonday && 'text-slate-400 italic',
            className,
          )}
          data-testid={`week-of-${job.id}`}
          aria-label={`Edit target week for job ${job.id}`}
        >
          <CalendarIcon className="mr-1 h-3.5 w-3.5" />
          {saving ? 'Saving…' : displayText}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-auto p-0" align="start">
        <Calendar
          mode="single"
          selected={selectedMonday ?? undefined}
          onSelect={handleSelect}
          modifiers={modifiers}
          modifiersClassNames={modifiersClassNames}
          weekStartsOn={1}
          data-testid={`week-editor-calendar-${job.id}`}
        />
        {error && (
          <div
            className="border-t px-3 py-2 text-xs text-red-600"
            role="alert"
            data-testid={`week-editor-error-${job.id}`}
          >
            {error}
          </div>
        )}
      </PopoverContent>
    </Popover>
  );
}
