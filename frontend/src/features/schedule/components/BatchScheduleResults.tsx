/**
 * BatchScheduleResults — multi-week campaign schedule display.
 * Shows jobs by week, zone, resource with capacity utilization.
 */

import { cn } from '@/shared/utils/cn';

export interface BatchWeek {
  weekStart: string;
  weekLabel: string;
  utilizationPct: number;
  jobs: BatchJob[];
}

export interface BatchJob {
  id: string;
  jobType: string;
  customerName: string;
  zone: string;
  resourceName: string;
  date: string;
  revenue?: number;
}

export interface RankedJob {
  id: string;
  jobType: string;
  customerName: string;
  projectedRevenue: number;
  revenueImpact: string;
}

interface BatchScheduleResultsProps {
  weeks: BatchWeek[];
  totalJobsScheduled: number;
  notificationsReady: number;
  rankedJobs?: RankedJob[];
  onAssignJob?: (jobId: string) => void;
  onSendNotifications?: () => void;
}

export function BatchScheduleResults({
  weeks,
  totalJobsScheduled,
  notificationsReady,
  rankedJobs,
  onAssignJob,
  onSendNotifications,
}: BatchScheduleResultsProps) {
  return (
    <div data-testid="batch-schedule-results" className="flex flex-col gap-4 rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
      {/* Summary header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">Batch Schedule Results</h3>
          <p className="text-sm text-gray-500">
            {totalJobsScheduled} jobs scheduled across {weeks.length} weeks
          </p>
        </div>
        {notificationsReady > 0 && (
          <button
            onClick={onSendNotifications}
            className="rounded-md bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700"
          >
            Send {notificationsReady} Notifications
          </button>
        )}
      </div>

      {/* Week breakdown */}
      {weeks.map((week) => (
        <div key={week.weekStart} className="rounded border border-gray-200">
          <div className="flex items-center justify-between border-b border-gray-200 bg-gray-50 px-3 py-2">
            <span className="text-sm font-medium text-gray-900">{week.weekLabel}</span>
            <span
              className={cn(
                'rounded-full px-2 py-0.5 text-xs font-medium',
                week.utilizationPct > 90
                  ? 'bg-red-100 text-red-700'
                  : week.utilizationPct >= 60
                    ? 'bg-green-100 text-green-700'
                    : 'bg-yellow-100 text-yellow-700'
              )}
            >
              {Math.round(week.utilizationPct)}% utilized
            </span>
          </div>
          <div className="divide-y divide-gray-100">
            {week.jobs.map((job) => (
              <div key={job.id} className="flex items-center justify-between px-3 py-1.5 text-xs">
                <div className="flex items-center gap-3">
                  <span className="font-medium text-gray-900">{job.customerName}</span>
                  <span className="text-gray-500">{job.jobType}</span>
                  <span className="text-gray-400">{job.zone}</span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-gray-500">{job.resourceName}</span>
                  <span className="text-gray-400">{job.date}</span>
                  {job.revenue != null && (
                    <span className="font-medium text-green-700">${job.revenue}</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}

      {/* Ranked jobs for one-click assignment */}
      {rankedJobs && rankedJobs.length > 0 && (
        <div className="rounded border border-gray-200">
          <div className="border-b border-gray-200 bg-gray-50 px-3 py-2">
            <span className="text-sm font-medium text-gray-900">Best-Fit Jobs by Revenue</span>
          </div>
          <div className="divide-y divide-gray-100">
            {rankedJobs.map((job) => (
              <div key={job.id} className="flex items-center justify-between px-3 py-2 text-xs">
                <div>
                  <span className="font-medium text-gray-900">{job.customerName}</span>
                  <span className="ml-2 text-gray-500">{job.jobType}</span>
                  <span className="ml-2 text-green-700">{job.revenueImpact}</span>
                </div>
                <button
                  onClick={() => onAssignJob?.(job.id)}
                  className="rounded bg-blue-600 px-2 py-1 text-xs font-medium text-white hover:bg-blue-700"
                >
                  Assign
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
