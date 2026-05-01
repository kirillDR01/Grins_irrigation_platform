/**
 * ViewModeToggle — three-button segmented Day / Week / Month switch.
 *
 * Uses plain styled `<button>`s rather than `@radix-ui/react-toggle-group`
 * (not in `package.json`). Visual language matches the existing `<Tabs>`
 * styling on `SchedulePage` (slate-100 surface + active white pill).
 */

import { Clock, CalendarDays, Calendar } from 'lucide-react';
import type { ViewMode } from './types';

export interface ViewModeToggleProps {
  mode: ViewMode;
  onModeChange: (next: ViewMode) => void;
}

const MODES: Array<{
  value: ViewMode;
  label: string;
  Icon: typeof Clock;
  testId: string;
}> = [
  { value: 'day', label: 'Day', Icon: Clock, testId: 'view-mode-day-btn' },
  {
    value: 'week',
    label: 'Week',
    Icon: CalendarDays,
    testId: 'view-mode-week-btn',
  },
  {
    value: 'month',
    label: 'Month',
    Icon: Calendar,
    testId: 'view-mode-month-btn',
  },
];

export function ViewModeToggle({ mode, onModeChange }: ViewModeToggleProps) {
  return (
    <div
      data-testid="schedule-view-mode-toggle"
      className="inline-flex bg-slate-100 rounded-lg p-1 gap-1"
      role="tablist"
      aria-label="View mode"
    >
      {MODES.map(({ value, label, Icon, testId }) => {
        const active = value === mode;
        return (
          <button
            key={value}
            type="button"
            data-testid={testId}
            role="tab"
            aria-selected={active}
            onClick={() => onModeChange(value)}
            className={[
              'inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium',
              'transition-colors',
              active
                ? 'bg-white text-slate-900 shadow-sm'
                : 'text-slate-600 hover:text-slate-900',
            ].join(' ')}
          >
            <Icon className="size-4" aria-hidden />
            {label}
          </button>
        );
      })}
    </div>
  );
}
