/**
 * AIScheduleView — composed page component combining ScheduleOverviewEnhanced,
 * AlertsPanel, and SchedulingChat in a two-column layout.
 *
 * Bug 1 fix: previously rendered ScheduleOverviewEnhanced with empty
 * resources/days/capacityDays arrays. Now wires useUtilizationReport and
 * useCapacityForecast and adapts the responses into the overview shape.
 */

import { useMemo, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';

import { SchedulingChat } from '@/features/ai';
import type { ScheduleChange } from '@/features/ai';
import { AlertsPanel, alertKeys } from '@/features/scheduling-alerts';
import { ErrorBoundary, ErrorMessage } from '@/shared/components/ErrorBoundary';
import { LoadingSpinner } from '@/shared/components/LoadingSpinner';

import {
  aiSchedulingKeys,
  useCapacityForecast,
  useUtilizationReport,
  type CapacityForecastExtended,
  type UtilizationReport,
} from '../hooks/useAIScheduling';
import {
  ScheduleOverviewEnhanced,
  type OverviewDay,
  type OverviewResource,
} from './ScheduleOverviewEnhanced';
import type { CapacityDay } from './CapacityHeatMap';

function ChatErrorFallback() {
  return (
    <div className="flex flex-col items-center justify-center h-full p-6 text-center">
      <p className="text-slate-600 mb-2 font-medium">Chat unavailable</p>
      <a
        href="/schedule/generate"
        className="text-teal-600 hover:underline text-sm"
      >
        Retry
      </a>
    </div>
  );
}

function MainErrorFallback() {
  return (
    <div className="flex flex-col items-center justify-center h-full p-6 text-center">
      <p className="text-slate-600 mb-2 font-medium">Schedule unavailable</p>
      <a href="/schedule" className="text-teal-600 hover:underline text-sm">
        Reload
      </a>
    </div>
  );
}

function shortDayLabel(iso: string): string {
  const d = new Date(`${iso}T00:00:00`);
  const wkday = d.toLocaleDateString('en-US', { weekday: 'short' });
  return `${wkday} ${d.getMonth() + 1}/${d.getDate()}`;
}

function mapToOverviewShape(
  util: UtilizationReport | undefined,
  capacity: CapacityForecastExtended | undefined,
  scheduleDate: string,
): {
  resources: OverviewResource[];
  days: OverviewDay[];
  capacityDays: CapacityDay[];
} {
  const resources: OverviewResource[] = (util?.resources ?? []).map((r) => ({
    id: r.staff_id,
    name: r.name,
    title: 'Technician',
    utilization: Math.round(r.utilization_pct),
    jobsByDate: {},
  }));

  const dayLabel = shortDayLabel(scheduleDate);
  const dayJobCount = capacity?.total_jobs ?? 0;

  const days: OverviewDay[] = [
    {
      date: scheduleDate,
      label: dayLabel,
      jobCount: dayJobCount,
    },
  ];

  const overallUtilization = util?.resources?.length
    ? util.resources.reduce((sum, r) => sum + r.utilization_pct, 0) /
      util.resources.length
    : 0;
  const utilization = Math.round(
    capacity?.utilization_pct ?? overallUtilization,
  );
  const capacityDays: CapacityDay[] = [
    {
      date: scheduleDate,
      label: dayLabel,
      utilization,
    },
  ];

  return { resources, days, capacityDays };
}

export function AIScheduleView() {
  const queryClient = useQueryClient();
  const [scheduleDate, setScheduleDate] = useState<string>(
    () => new Date().toISOString().split('T')[0],
  );

  const utilization = useUtilizationReport(scheduleDate);
  const capacity = useCapacityForecast(scheduleDate);

  const { resources, days, capacityDays } = useMemo(
    () => mapToOverviewShape(utilization.data, capacity.data, scheduleDate),
    [utilization.data, capacity.data, scheduleDate],
  );

  const isLoading = utilization.isLoading || capacity.isLoading;
  const queryError = (utilization.error ?? capacity.error) as Error | null;

  function handleViewModeChange(
    _mode: 'day' | 'week' | 'month',
    date?: string,
  ) {
    if (date) setScheduleDate(date);
  }

  function handlePublishSchedule(_changes: ScheduleChange[]) {
    void queryClient.invalidateQueries({ queryKey: aiSchedulingKeys.all });
    void queryClient.invalidateQueries({ queryKey: alertKeys.all });
  }

  return (
    <div
      className="grid h-full"
      style={{ gridTemplateColumns: '1fr 380px' }}
      data-testid="ai-schedule-page"
    >
      {/* Visually hidden heading for accessibility */}
      <h1 className="sr-only">AI Schedule</h1>

      <ErrorBoundary fallback={<MainErrorFallback />}>
        <main className="flex flex-col overflow-auto">
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <LoadingSpinner size="lg" />
            </div>
          ) : queryError ? (
            <ErrorMessage error={queryError} />
          ) : (
            <ScheduleOverviewEnhanced
              weekTitle={`Schedule Overview — Week of ${scheduleDate}`}
              resources={resources}
              days={days}
              capacityDays={capacityDays}
              currentDate={scheduleDate}
              onViewModeChange={handleViewModeChange}
            />
          )}
          <AlertsPanel scheduleDate={scheduleDate} />
        </main>
      </ErrorBoundary>

      <aside className="border-l border-slate-200 flex flex-col overflow-hidden">
        <ErrorBoundary fallback={<ChatErrorFallback />}>
          <SchedulingChat onPublishSchedule={handlePublishSchedule} />
        </ErrorBoundary>
      </aside>
    </div>
  );
}
