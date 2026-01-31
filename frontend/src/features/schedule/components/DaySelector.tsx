/**
 * DaySelector component.
 * Shows 7 clickable day buttons for the current week.
 * Allows selecting a day for the Clear Day feature.
 */

import { format, addDays, isSameDay } from 'date-fns';
import { cn } from '@/lib/utils';

interface DaySelectorProps {
  /** The start of the week to display */
  weekStart: Date;
  /** Currently selected date (null if none) */
  selectedDate: Date | null;
  /** Callback when a day is selected */
  onSelectDate: (date: Date) => void;
  /** Optional: appointment counts per day (keyed by yyyy-MM-dd) */
  appointmentCounts?: Record<string, number>;
}

export function DaySelector({
  weekStart,
  selectedDate,
  onSelectDate,
  appointmentCounts = {},
}: DaySelectorProps) {
  // Generate 7 days starting from weekStart
  const days = Array.from({ length: 7 }, (_, i) => addDays(weekStart, i));
  const today = new Date();

  return (
    <div 
      className="flex gap-2 p-3 bg-slate-50 rounded-xl border border-slate-200"
      data-testid="day-selector"
    >
      <span className="flex items-center text-sm font-medium text-slate-600 mr-2">
        Select Day:
      </span>
      {days.map((day) => {
        const dateKey = format(day, 'yyyy-MM-dd');
        const isSelected = selectedDate && isSameDay(day, selectedDate);
        const isToday = isSameDay(day, today);
        const count = appointmentCounts[dateKey] ?? 0;

        return (
          <button
            key={dateKey}
            onClick={() => onSelectDate(day)}
            data-testid={`day-btn-${format(day, 'EEE').toLowerCase()}`}
            className={cn(
              'flex flex-col items-center px-3 py-2 rounded-lg transition-all min-w-[70px]',
              'hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-teal-500 focus:ring-offset-1',
              isSelected && 'bg-teal-500 text-white hover:bg-teal-600 ring-2 ring-teal-500 ring-offset-2',
              !isSelected && isToday && 'bg-blue-50 border-2 border-blue-300',
              !isSelected && !isToday && 'bg-white border border-slate-200'
            )}
          >
            {/* Day name */}
            <span className={cn(
              'text-xs font-medium',
              isSelected ? 'text-teal-100' : 'text-slate-500'
            )}>
              {format(day, 'EEE')}
            </span>
            
            {/* Date number */}
            <span className={cn(
              'text-lg font-bold',
              isSelected ? 'text-white' : 'text-slate-800'
            )}>
              {format(day, 'd')}
            </span>
            
            {/* Appointment count badge */}
            {count > 0 && (
              <span className={cn(
                'text-xs px-1.5 py-0.5 rounded-full mt-0.5',
                isSelected 
                  ? 'bg-teal-400 text-white' 
                  : 'bg-slate-200 text-slate-600'
              )}>
                {count}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
