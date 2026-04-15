import { useState, useMemo, useCallback } from 'react';
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

interface WeekPickerProps {
  /** Currently selected Monday date as ISO string (YYYY-MM-DD) or null */
  value: string | null;
  /** Called with the Monday ISO string when a week is selected, or null on clear */
  onChange: (mondayIso: string | null) => void;
  /** Placeholder text when no week is selected */
  placeholder?: string;
  /** Additional className for the trigger button */
  className?: string;
  /** data-testid for the trigger */
  'data-testid'?: string;
}

/** Align any date to its Monday–Sunday week range. */
function alignToWeek(d: Date): { monday: Date; sunday: Date } {
  const monday = startOfWeek(d, { weekStartsOn: 1 });
  const sunday = endOfWeek(d, { weekStartsOn: 1 });
  return { monday, sunday };
}

/**
 * WeekPicker — calendar that highlights and selects full Monday–Sunday weeks.
 *
 * Displays "Week of M/D/YYYY" when a week is selected.
 */
export function WeekPicker({
  value,
  onChange,
  placeholder = 'Select week',
  className,
  'data-testid': testId = 'week-picker',
}: WeekPickerProps) {
  const [open, setOpen] = useState(false);

  const selectedMonday = useMemo(
    () => (value ? new Date(value + 'T00:00:00') : null),
    [value],
  );

  const handleSelect = useCallback(
    (day: Date | undefined) => {
      if (!day) {
        onChange(null);
        return;
      }
      const { monday } = alignToWeek(day);
      onChange(format(monday, 'yyyy-MM-dd'));
      setOpen(false);
    },
    [onChange],
  );

  // Highlight the full week containing the selected Monday
  const modifiers = useMemo(() => {
    if (!selectedMonday) return {};
    return {
      selectedWeek: (day: Date) =>
        isSameWeek(day, selectedMonday, { weekStartsOn: 1 }),
    };
  }, [selectedMonday]);

  const modifiersClassNames = useMemo(
    () => ({
      selectedWeek: 'bg-teal-100 text-teal-800 rounded-none first:rounded-l-md last:rounded-r-md',
    }),
    [],
  );

  const displayText = selectedMonday
    ? `Week of ${format(selectedMonday, 'M/d/yyyy')}`
    : placeholder;

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          className={cn(
            'justify-start text-left font-normal',
            !selectedMonday && 'text-muted-foreground',
            className,
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
          modifiers={modifiers}
          modifiersClassNames={modifiersClassNames}
          weekStartsOn={1}
          data-testid="week-picker-calendar"
        />
        {selectedMonday && (
          <div className="border-t p-2">
            <Button
              variant="ghost"
              size="sm"
              className="w-full"
              onClick={() => {
                onChange(null);
                setOpen(false);
              }}
              data-testid="week-picker-clear"
            >
              Clear week
            </Button>
          </div>
        )}
      </PopoverContent>
    </Popover>
  );
}
