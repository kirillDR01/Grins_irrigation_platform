/**
 * ScheduleOverviewEnhanced — purpose-built resource × day grid for the AI schedule view.
 * Shows resources as rows, days as columns, with job cards, utilization, and capacity heat map.
 */

import { useState } from 'react';
import { cn } from '@/shared/utils/cn';
import { CapacityHeatMap } from './CapacityHeatMap';
import type { CapacityDay } from './CapacityHeatMap';

// ---- Types ----------------------------------------------------------------

export interface OverviewJob {
  id: string;
  jobTypeName: string;
  timeStart: string; // e.g. "8:00 AM"
  timeEnd: string; // e.g. "9:30 AM"
  customerLastName: string;
  address: string;
  isVip?: boolean;
  hasConflict?: boolean;
  status?: 'confirmed' | 'in_progress' | 'completed' | 'flagged';
  aiExplanation?: string;
  jobTypeColor?: string;
}

export interface OverviewResource {
  id: string;
  name: string;
  title: string;
  utilization: number; // 0–100
  jobsByDate: Record<string, OverviewJob[]>; // key = ISO date
}

export interface OverviewDay {
  date: string; // ISO date
  label: string; // e.g. "Mon 2/16"
  jobCount: number;
}

export interface ScheduleOverviewEnhancedProps {
  weekTitle: string;
  resources: OverviewResource[];
  days: OverviewDay[];
  capacityDays: CapacityDay[];
  onAddResource?: () => void;
  onRemoveResource?: (resourceId: string) => void;
  onViewModeChange?: (mode: 'day' | 'week' | 'month', date?: string) => void;
}

// ---- Job type color map ---------------------------------------------------

const JOB_TYPE_COLORS: Record<string, string> = {
  'Spring Opening': 'bg-green-100 border-green-300 text-green-900',
  'Fall Closing': 'bg-orange-100 border-orange-300 text-orange-900',
  Maintenance: 'bg-blue-100 border-blue-300 text-blue-900',
  'New Build': 'bg-purple-100 border-purple-300 text-purple-900',
  'Backflow Test': 'bg-teal-100 border-teal-300 text-teal-900',
};

const DEFAULT_JOB_COLOR = 'bg-gray-100 border-gray-300 text-gray-900';

const JOB_TYPE_LEGEND = [
  { label: 'Spring Opening', dot: 'bg-green-500' },
  { label: 'Fall Closing', dot: 'bg-orange-500' },
  { label: 'Maintenance', dot: 'bg-blue-500' },
  { label: 'New Build', dot: 'bg-purple-500' },
  { label: 'Backflow Test', dot: 'bg-teal-500' },
];

const STATUS_ICONS: Record<string, string> = {
  confirmed: '✓',
  in_progress: '▶',
  completed: '✔',
  flagged: '⚠',
};

// ---- Sub-components -------------------------------------------------------

function JobCard({ job }: { job: OverviewJob }) {
  const colorClass = JOB_TYPE_COLORS[job.jobTypeName] ?? DEFAULT_JOB_COLOR;
  return (
    <div
      data-testid={`job-card-${job.id}`}
      className={cn(
        'mb-1 rounded border px-2 py-1 text-xs leading-tight',
        colorClass
      )}
      title={job.aiExplanation}
    >
      <div className="flex items-center gap-1 font-medium">
        {job.isVip && <span title="VIP">⭐</span>}
        {job.hasConflict && <span title="Conflict">⚠️</span>}
        {job.status && STATUS_ICONS[job.status] && (
          <span>{STATUS_ICONS[job.status]}</span>
        )}
        <span className="truncate">{job.jobTypeName}</span>
      </div>
      <div className="text-gray-600">
        {job.timeStart} – {job.timeEnd}
      </div>
      <div className="truncate text-gray-500">
        {job.customerLastName} · {job.address}
      </div>
    </div>
  );
}

// ---- Main component -------------------------------------------------------

export function ScheduleOverviewEnhanced({
  weekTitle,
  resources,
  days,
  capacityDays,
  onAddResource,
  onRemoveResource,
  onViewModeChange,
}: ScheduleOverviewEnhancedProps) {
  const [viewMode, setViewMode] = useState<'day' | 'week' | 'month'>('week');

  function handleViewMode(mode: 'day' | 'week' | 'month') {
    setViewMode(mode);
    onViewModeChange?.(mode);
  }

  return (
    <div
      data-testid="schedule-overview-enhanced"
      className="flex flex-col overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm"
    >
      {/* Header */}
      <div className="flex items-center justify-between border-b border-gray-200 px-4 py-3">
        <h2 className="text-base font-semibold text-gray-900">{weekTitle}</h2>
        <div className="flex items-center gap-2">
          {(['day', 'week', 'month'] as const).map((m) => (
            <button
              key={m}
              onClick={() => handleViewMode(m)}
              className={cn(
                'rounded px-3 py-1 text-sm capitalize',
                viewMode === m
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              )}
            >
              {m}
            </button>
          ))}
          <button
            onClick={onAddResource}
            className="ml-2 rounded bg-blue-600 px-3 py-1 text-sm text-white hover:bg-blue-700"
          >
            + New Job
          </button>
        </div>
      </div>

      {/* Legend */}
      <div className="flex flex-wrap gap-3 border-b border-gray-100 px-4 py-2">
        {JOB_TYPE_LEGEND.map(({ label, dot }) => (
          <div key={label} className="flex items-center gap-1 text-xs text-gray-600">
            <span className={cn('h-2 w-2 rounded-full', dot)} />
            {label}
          </div>
        ))}
      </div>

      {/* Grid */}
      <div className="overflow-x-auto">
        {/* Column headers */}
        <div className="flex border-b border-gray-200 bg-gray-50">
          <div className="w-40 shrink-0 px-3 py-2 text-xs font-semibold text-gray-500">
            Resource
          </div>
          {days.map((day) => (
            <div
              key={day.date}
              className="flex-1 border-l border-gray-200 px-2 py-2 text-center text-xs font-semibold text-gray-700"
            >
              <div>{day.label}</div>
              <div className="text-gray-400">{day.jobCount} jobs</div>
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
            <div className="w-40 shrink-0 border-r border-gray-100 px-3 py-2">
              <div className="flex items-start justify-between">
                <div>
                  <div className="text-xs font-semibold text-gray-800">
                    {resource.name}
                  </div>
                  <div className="text-xs text-gray-500">{resource.title}</div>
                  <div
                    className={cn(
                      'mt-1 text-xs font-medium',
                      resource.utilization > 90
                        ? 'text-red-600'
                        : resource.utilization >= 60
                          ? 'text-green-600'
                          : 'text-yellow-600'
                    )}
                  >
                    {resource.utilization}% utilized
                  </div>
                </div>
                {onRemoveResource && (
                  <button
                    onClick={() => onRemoveResource(resource.id)}
                    className="ml-1 text-gray-300 hover:text-red-500"
                    title="Remove resource"
                  >
                    ×
                  </button>
                )}
              </div>
            </div>

            {/* Day cells */}
            {days.map((day) => {
              const jobs = resource.jobsByDate[day.date] ?? [];
              return (
                <div
                  key={day.date}
                  className="flex-1 border-l border-gray-100 px-2 py-2"
                >
                  {jobs.map((job) => (
                    <JobCard key={job.id} job={job} />
                  ))}
                </div>
              );
            })}
          </div>
        ))}

        {/* Capacity heat map row */}
        <CapacityHeatMap days={capacityDays} />
      </div>
    </div>
  );
}
