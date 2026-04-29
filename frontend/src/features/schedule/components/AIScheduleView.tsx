/**
 * AIScheduleView — composed page component combining ScheduleOverviewEnhanced,
 * AlertsPanel, and SchedulingChat in a two-column layout.
 */

import { useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { ScheduleOverviewEnhanced } from './ScheduleOverviewEnhanced';
import { AlertsPanel } from '@/features/scheduling-alerts';
import { SchedulingChat } from '@/features/ai';
import { ErrorBoundary } from '@/shared/components/ErrorBoundary';
import { aiSchedulingKeys } from '../hooks/useAIScheduling';
import { alertKeys } from '@/features/scheduling-alerts';
import type { ScheduleChange } from '@/features/ai';

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

export function AIScheduleView() {
  const queryClient = useQueryClient();
  const [scheduleDate, setScheduleDate] = useState<string>(
    () => new Date().toISOString().split('T')[0]
  );

  function handleViewModeChange(
    _mode: 'day' | 'week' | 'month',
    date?: string
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

      <main className="flex flex-col overflow-auto">
        <ScheduleOverviewEnhanced
          weekTitle={`Schedule Overview — Week of ${scheduleDate}`}
          resources={[]}
          days={[]}
          capacityDays={[]}
          onViewModeChange={handleViewModeChange}
        />
        <AlertsPanel scheduleDate={scheduleDate} />
      </main>

      <aside className="border-l border-slate-200 flex flex-col overflow-hidden">
        <ErrorBoundary fallback={<ChatErrorFallback />}>
          <SchedulingChat onPublishSchedule={handlePublishSchedule} />
        </ErrorBoundary>
      </aside>
    </div>
  );
}
