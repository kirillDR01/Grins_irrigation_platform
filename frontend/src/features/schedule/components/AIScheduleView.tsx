/**
 * AIScheduleView — composed admin page for AI scheduling.
 * Renders ScheduleOverviewEnhanced + AlertsPanel in <main>,
 * SchedulingChat in <aside> with error boundary isolation.
 */

import { useState, Component, type ReactNode } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { ScheduleOverviewEnhanced, type ViewMode } from './ScheduleOverviewEnhanced';
import { AlertsPanel } from '@/features/scheduling-alerts';
import { SchedulingChat } from '@/features/ai/components/SchedulingChat';
import { useWeeklySchedule } from '../hooks';
import { useScheduleCapacity } from '../hooks/useScheduleGeneration';
import { alertKeys } from '@/features/scheduling-alerts';
import { scheduleGenerationKeys } from '../hooks/useScheduleGeneration';
import type { ScheduleChange } from '@/features/ai/hooks/useSchedulingChat';
import type {
  ScheduleResource,
  ScheduleDay,
  ScheduleCell,
} from './ScheduleOverviewEnhanced';
import type { CapacityHeatMapData } from './CapacityHeatMap';

// ── Error boundary for chat isolation ──────────────────────────────────

interface ErrorBoundaryState {
  hasError: boolean;
}

class ChatErrorBoundary extends Component<
  { children: ReactNode; fallback: ReactNode },
  ErrorBoundaryState
> {
  state: ErrorBoundaryState = { hasError: false };

  static getDerivedStateFromError(): ErrorBoundaryState {
    return { hasError: true };
  }

  render() {
    if (this.state.hasError) return this.fallback;
    return this.props.children;
  }

  private get fallback() {
    return this.props.fallback;
  }
}

function ChatErrorFallback() {
  return (
    <div
      data-testid="chat-error-fallback"
      className="flex flex-col items-center justify-center h-full p-6 text-center"
    >
      <p className="text-sm text-gray-500">Chat unavailable</p>
      <button
        onClick={() => window.location.reload()}
        className="mt-2 text-xs text-blue-600 hover:underline"
      >
        Reload page
      </button>
    </div>
  );
}

// ── Helpers ────────────────────────────────────────────────────────────

function getWeekTitle(date: string): string {
  const d = new Date(date + 'T00:00:00');
  const day = d.getDay();
  const monday = new Date(d);
  monday.setDate(d.getDate() - ((day + 6) % 7));
  const sunday = new Date(monday);
  sunday.setDate(monday.getDate() + 6);
  const fmt = (dt: Date) =>
    dt.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  return `${fmt(monday)} – ${fmt(sunday)}, ${monday.getFullYear()}`;
}

function getWeekDays(date: string): string[] {
  const d = new Date(date + 'T00:00:00');
  const day = d.getDay();
  const monday = new Date(d);
  monday.setDate(d.getDate() - ((day + 6) % 7));
  return Array.from({ length: 7 }, (_, i) => {
    const dt = new Date(monday);
    dt.setDate(monday.getDate() + i);
    return dt.toISOString().split('T')[0];
  });
}

// ── Component ──────────────────────────────────────────────────────────

export function AIScheduleView() {
  const [scheduleDate, setScheduleDate] = useState<string>(
    () => new Date().toISOString().split('T')[0]
  );

  const queryClient = useQueryClient();
  const weekDays = getWeekDays(scheduleDate);
  const startDate = weekDays[0];
  const endDate = weekDays[6];

  const { data: weeklyData } = useWeeklySchedule(startDate, endDate);
  const { data: capacityData } = useScheduleCapacity(scheduleDate);

  // Transform weekly data into ScheduleOverviewEnhanced props
  const resourceMap = new Map<string, ScheduleResource>();
  const cellMap = new Map<string, ScheduleCell>();
  const dayJobCounts = new Map<string, number>();

  if (weeklyData?.days) {
    for (const day of weeklyData.days) {
      let dayCount = 0;
      for (const appt of day.appointments) {
        const staffId = appt.staff_id ?? 'unassigned';
        const staffName = appt.staff_name ?? 'Unassigned';

        if (!resourceMap.has(staffId)) {
          resourceMap.set(staffId, {
            id: staffId,
            name: staffName,
            role: 'Technician',
            utilizationPct: 0,
          });
        }

        const cellKey = `${staffId}-${day.date}`;
        if (!cellMap.has(cellKey)) {
          cellMap.set(cellKey, { resourceId: staffId, day: day.date, jobs: [] });
        }
        cellMap.get(cellKey)!.jobs.push({
          id: appt.id,
          jobType: appt.job_type ?? 'maintenance',
          jobTypeName: appt.job_type ?? 'Job',
          timeWindow: appt.time_window_start
            ? `${appt.time_window_start.slice(0, 5)} – ${appt.time_window_end.slice(0, 5)}`
            : '',
          customerName: appt.customer_name ?? '',
          address: '',
          isVip: false,
          hasConflict: false,
          status: (['confirmed', 'in_progress', 'completed', 'flagged'] as const).includes(
            appt.status as 'confirmed' | 'in_progress' | 'completed' | 'flagged'
          )
            ? (appt.status as 'confirmed' | 'in_progress' | 'completed' | 'flagged')
            : undefined,
        });
        dayCount++;
      }
      dayJobCounts.set(day.date, dayCount);
    }
  }

  const resources = Array.from(resourceMap.values());
  const days: ScheduleDay[] = weekDays.map((date) => ({
    date,
    label: new Date(date + 'T00:00:00').toLocaleDateString('en-US', {
      weekday: 'short',
      month: 'short',
      day: 'numeric',
    }),
    jobCount: dayJobCounts.get(date) ?? 0,
  }));
  const cells = Array.from(cellMap.values());

  const heatMapData: CapacityHeatMapData[] = weekDays.map((date) => ({
    day: date,
    utilization: capacityData && date === scheduleDate
      ? Math.round(
          (capacityData.scheduled_minutes / Math.max(capacityData.total_capacity_minutes, 1)) * 100
        )
      : 0,
  }));

  const handleViewModeChange = (_mode: ViewMode) => {
    // View mode changes could adjust the date range anchor.
    // For day mode, keep current date; for week/month, snap to start of period.
    // Currently the date stays as-is since the overview handles its own display.
    setScheduleDate((prev) => prev);
  };

  const handlePublishSchedule = (_changes: ScheduleChange[]) => {
    queryClient.invalidateQueries({ queryKey: ['appointments'] });
    queryClient.invalidateQueries({ queryKey: scheduleGenerationKeys.all });
    queryClient.invalidateQueries({ queryKey: alertKeys.all });
  };

  return (
    <div
      data-testid="ai-schedule-page"
      className="grid h-full"
      style={{ gridTemplateColumns: '1fr 380px' }}
    >
      <h1 className="sr-only">AI Scheduling Workspace</h1>

      <main className="overflow-y-auto p-4 space-y-4">
        <ScheduleOverviewEnhanced
          weekTitle={getWeekTitle(scheduleDate)}
          resources={resources}
          days={days}
          cells={cells}
          capacityData={heatMapData}
          onViewModeChange={handleViewModeChange}
        />
        <AlertsPanel scheduleDate={scheduleDate} />
      </main>

      <aside className="overflow-hidden border-l border-gray-200">
        <ChatErrorBoundary fallback={<ChatErrorFallback />}>
          <SchedulingChat onPublishSchedule={handlePublishSchedule} />
        </ChatErrorBoundary>
      </aside>
    </div>
  );
}
