/**
 * ScheduleOverviewEnhanced — custom resource-row × day-column grid layout.
 * Purpose-built grid for the AI scheduling view (not FullCalendar).
 */

import { useState } from 'react';
import { cn } from '@/shared/utils/cn';
import { CapacityHeatMap, type CapacityHeatMapData } from './CapacityHeatMap';

// ── Types ──────────────────────────────────────────────────────────────

export type ViewMode = 'day' | 'week' | 'month';

export type JobTypeColor =
  | 'spring_opening'
  | 'fall_closing'
  | 'maintenance'
  | 'new_build'
  | 'backflow_test';

export type AppointmentStatusType =
  | 'confirmed'
  | 'in_progress'
  | 'completed'
  | 'flagged';

export interface ScheduleJobCard {
  id: string;
  jobType: JobTypeColor | string;
  jobTypeName: string;
  timeWindow: string;
  customerName: string;
  address: string;
  isVip: boolean;
  hasConflict: boolean;
  status?: AppointmentStatusType;
  criteriaScores?: Record<string, unknown>;
  aiExplanation?: string;
}

export interface ScheduleResource {
  id: string;
  name: string;
  role: string;
  utilizationPct: number;
}

export interface ScheduleDay {
  date: string;
  label: string;
  jobCount: number;
}

export interface ScheduleCell {
  resourceId: string;
  day: string;
  jobs: ScheduleJobCard[];
}

export interface ScheduleOverviewEnhancedProps {
  weekTitle: string;
  resources: ScheduleResource[];
  days: ScheduleDay[];
  cells: ScheduleCell[];
  capacityData: CapacityHeatMapData[];
  onNewJob?: () => void;
  onViewModeChange?: (mode: ViewMode) => void;
  initialViewMode?: ViewMode;
}

// ── Color map ──────────────────────────────────────────────────────────

const JOB_TYPE_COLORS: Record<string, { bg: string; dot: string; label: string }> = {
  spring_opening: { bg: 'bg-green-50 border-green-300', dot: 'bg-green-500', label: 'Spring Opening' },
  fall_closing: { bg: 'bg-orange-50 border-orange-300', dot: 'bg-orange-500', label: 'Fall Closing' },
  maintenance: { bg: 'bg-blue-50 border-blue-300', dot: 'bg-blue-500', label: 'Maintenance' },
  new_build: { bg: 'bg-purple-50 border-purple-300', dot: 'bg-purple-500', label: 'New Build' },
  backflow_test: { bg: 'bg-teal-50 border-teal-300', dot: 'bg-teal-500', label: 'Backflow Test' },
};

const STATUS_INDICATORS: Record<AppointmentStatusType, string> = {
  confirmed: 'border-l-blue-500',
  in_progress: 'border-l-amber-500',
  completed: 'border-l-green-500',
  flagged: 'border-l-red-500',
};

function getJobColor(jobType: string) {
  return JOB_TYPE_COLORS[jobType] ?? { bg: 'bg-gray-50 border-gray-300', dot: 'bg-gray-400', label: jobType };
}

// ── Component ──────────────────────────────────────────────────────────

export function ScheduleOverviewEnhanced({
  weekTitle,
  resources,
  days,
  cells,
  capacityData,
  onNewJob,
  onViewModeChange,
  initialViewMode = 'week',
}: ScheduleOverviewEnhancedProps) {
  const [viewMode, setViewMode] = useState<ViewMode>(initialViewMode);

  const handleViewModeChange = (mode: ViewMode) => {
    setViewMode(mode);
    onViewModeChange?.(mode);
  };

  const getCellJobs = (resourceId: string, day: string) =>
    cells.find((c) => c.resourceId === resourceId && c.day === day)?.jobs ?? [];

  return (
    <div data-testid="schedule-overview-enhanced" className="flex flex-col rounded-lg border border-gray-200 bg-white shadow-sm">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-gray-200 px-4 py-3">
        <h2 className="text-lg font-semibold text-gray-900">{weekTitle}</h2>
        <div className="flex items-center gap-3">
          <div className="flex rounded-md border border-gray-300">
            {(['day', 'week', 'month'] as ViewMode[]).map((mode) => (
              <button
                key={mode}
                onClick={() => handleViewModeChange(mode)}
                className={cn(
                  'px-3 py-1.5 text-xs font-medium capitalize',
                  viewMode === mode
                    ? 'bg-blue-600 text-white'
                    : 'bg-white text-gray-600 hover:bg-gray-50',
                  mode === 'day' && 'rounded-l-md',
                  mode === 'month' && 'rounded-r-md'
                )}
              >
                {mode}
              </button>
            ))}
          </div>
          <button
            onClick={onNewJob}
            className="rounded-md bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700"
          >
            + New Job
          </button>
        </div>
      </div>

      {/* Color legend */}
      <div className="flex flex-wrap items-center gap-4 border-b border-gray-200 px-4 py-2">
        {Object.entries(JOB_TYPE_COLORS).map(([key, { dot, label }]) => (
          <div key={key} className="flex items-center gap-1.5">
            <span className={cn('inline-block h-2.5 w-2.5 rounded-full', dot)} />
            <span className="text-xs text-gray-600">{label}</span>
          </div>
        ))}
      </div>

      {/* Grid */}
      <div className="overflow-x-auto">
        {/* Day headers */}
        <div className="flex border-b border-gray-200">
          <div className="w-48 shrink-0 border-r border-gray-200 bg-gray-50 px-3 py-2 text-xs font-semibold text-gray-600">
            Resource
          </div>
          {days.map((day) => (
            <div
              key={day.date}
              className="flex-1 border-r border-gray-200 bg-gray-50 px-2 py-2 text-center text-xs font-semibold text-gray-600 last:border-r-0"
            >
              <div>{day.label}</div>
              <div className="text-[10px] font-normal text-gray-400">
                {day.jobCount} jobs
              </div>
            </div>
          ))}
        </div>

        {/* Resource rows */}
        {resources.map((resource) => (
          <div
            key={resource.id}
            data-testid={`resource-row-${resource.id}`}
            className="flex border-b border-gray-100 last:border-b-0"
          >
            {/* Resource info */}
            <div className="flex w-48 shrink-0 flex-col justify-center border-r border-gray-200 px-3 py-2">
              <span className="text-sm font-medium text-gray-900">{resource.name}</span>
              <span className="text-[10px] text-gray-500">
                {resource.role} — {Math.round(resource.utilizationPct)}% utilized
              </span>
            </div>

            {/* Day cells */}
            {days.map((day) => {
              const jobs = getCellJobs(resource.id, day.date);
              return (
                <div
                  key={day.date}
                  className="flex flex-1 flex-col gap-1 border-r border-gray-100 p-1 last:border-r-0"
                >
                  {jobs.map((job) => {
                    const color = getJobColor(job.jobType);
                    return (
                      <div
                        key={job.id}
                        data-testid={`job-card-${job.id}`}
                        className={cn(
                          'rounded border px-1.5 py-1 text-[10px] leading-tight border-l-2',
                          color.bg,
                          job.status && STATUS_INDICATORS[job.status]
                        )}
                        title={job.aiExplanation ?? undefined}
                      >
                        <div className="flex items-center gap-1">
                          <span className="font-medium truncate">{job.jobTypeName}</span>
                          {job.isVip && <span title="VIP">⭐</span>}
                          {job.hasConflict && <span title="Conflict">⚠️</span>}
                        </div>
                        <div className="truncate text-gray-500">{job.timeWindow}</div>
                        <div className="truncate text-gray-500">
                          {job.customerName} · {job.address}
                        </div>
                      </div>
                    );
                  })}
                </div>
              );
            })}
          </div>
        ))}
      </div>

      {/* Capacity heat map */}
      <CapacityHeatMap data={capacityData} />
    </div>
  );
}
