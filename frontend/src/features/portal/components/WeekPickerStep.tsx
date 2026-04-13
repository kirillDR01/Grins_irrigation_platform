import { useState, useMemo, useCallback } from 'react';
import { startOfWeek, format, isSameWeek, startOfMonth, endOfMonth } from 'date-fns';
import { CalendarIcon } from 'lucide-react';
import { Calendar } from '@/components/ui/calendar';
import { Button } from '@/components/ui/button';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import { cn } from '@/lib/utils';

/** Valid month ranges per service type. */
const SERVICE_MONTH_RANGES: Record<string, { label: string; monthStart: number; monthEnd: number }> = {
  spring_startup: { label: 'Spring Startup', monthStart: 3, monthEnd: 5 },
  mid_season_inspection: { label: 'Mid-Season Inspection', monthStart: 6, monthEnd: 8 },
  fall_winterization: { label: 'Fall Winterization', monthStart: 9, monthEnd: 11 },
  monthly_visit_5: { label: 'Monthly Visit — May', monthStart: 5, monthEnd: 5 },
  monthly_visit_6: { label: 'Monthly Visit — June', monthStart: 6, monthEnd: 6 },
  monthly_visit_7: { label: 'Monthly Visit — July', monthStart: 7, monthEnd: 7 },
  monthly_visit_8: { label: 'Monthly Visit — August', monthStart: 8, monthEnd: 8 },
  monthly_visit_9: { label: 'Monthly Visit — September', monthStart: 9, monthEnd: 9 },
};

export interface ServiceWeekSelection {
  jobType: string;
  label: string;
  mondayIso: string | null;
}

export interface WeekPickerStepProps {
  /** List of job types in the customer's package (e.g. from tier included_services). */
  services: Array<{ jobType: string; label?: string }>;
  /** Current selections keyed by jobType → ISO Monday date. */
  value: Record<string, string>;
  /** Called when any selection changes. */
  onChange: (selections: Record<string, string>) => void;
  /** Year for the date range restrictions. Defaults to current year. */
  year?: number;
}

/**
 * WeekPickerStep — onboarding wizard step that shows one week picker per
 * service in the customer's package, each restricted to the valid month range.
 *
 * Validates: Requirements 30.1, 30.2
 */
export function WeekPickerStep({
  services,
  value,
  onChange,
  year = new Date().getFullYear(),
}: WeekPickerStepProps) {
  const handleChange = useCallback(
    (jobType: string, mondayIso: string | null) => {
      const next = { ...value };
      if (mondayIso) {
        next[jobType] = mondayIso;
      } else {
        delete next[jobType];
      }
      onChange(next);
    },
    [value, onChange],
  );

  return (
    <div className="space-y-4" data-testid="week-picker-step">
      <h3 className="text-lg font-medium">Choose your preferred weeks</h3>
      <p className="text-sm text-muted-foreground">
        Select the week you'd like each service performed. Each picker is
        restricted to the valid season for that service.
      </p>
      <div className="space-y-3">
        {services.map(({ jobType, label }) => {
          const range = SERVICE_MONTH_RANGES[jobType];
          const displayLabel = label ?? range?.label ?? jobType;
          return (
            <div key={jobType} className="flex items-center gap-3">
              <span className="w-48 text-sm font-medium">{displayLabel}</span>
              <RestrictedWeekPicker
                value={value[jobType] ?? null}
                onChange={(iso) => handleChange(jobType, iso)}
                monthStart={range?.monthStart ?? 1}
                monthEnd={range?.monthEnd ?? 12}
                year={year}
                data-testid={`week-picker-${jobType}`}
              />
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Internal: week picker restricted to a month range                  */
/* ------------------------------------------------------------------ */

interface RestrictedWeekPickerProps {
  value: string | null;
  onChange: (mondayIso: string | null) => void;
  monthStart: number;
  monthEnd: number;
  year: number;
  'data-testid'?: string;
}

function RestrictedWeekPicker({
  value,
  onChange,
  monthStart,
  monthEnd,
  year,
  'data-testid': testId,
}: RestrictedWeekPickerProps) {
  const [open, setOpen] = useState(false);

  const selectedMonday = useMemo(
    () => (value ? new Date(value + 'T00:00:00') : null),
    [value],
  );

  const rangeStart = useMemo(
    () => startOfMonth(new Date(year, monthStart - 1)),
    [year, monthStart],
  );
  const rangeEnd = useMemo(
    () => endOfMonth(new Date(year, monthEnd - 1)),
    [year, monthEnd],
  );

  const disabledDays = useMemo(
    () => [{ before: rangeStart }, { after: rangeEnd }],
    [rangeStart, rangeEnd],
  );

  const handleSelect = useCallback(
    (day: Date | undefined) => {
      if (!day) {
        onChange(null);
        return;
      }
      const monday = startOfWeek(day, { weekStartsOn: 1 });
      onChange(format(monday, 'yyyy-MM-dd'));
      setOpen(false);
    },
    [onChange],
  );

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

  const displayText = selectedMonday
    ? `Week of ${format(selectedMonday, 'M/d/yyyy')}`
    : 'Select week';

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          className={cn(
            'w-52 justify-start text-left font-normal',
            !selectedMonday && 'text-muted-foreground',
          )}
          data-testid={testId}
        >
          <CalendarIcon className="mr-2 h-4 w-4" />
          <span className="text-sm">{displayText}</span>
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-auto p-0" align="start">
        <Calendar
          mode="single"
          selected={selectedMonday ?? undefined}
          onSelect={handleSelect}
          defaultMonth={rangeStart}
          disabled={disabledDays}
          modifiers={modifiers}
          modifiersClassNames={modifiersClassNames}
          weekStartsOn={1}
        />
      </PopoverContent>
    </Popover>
  );
}
