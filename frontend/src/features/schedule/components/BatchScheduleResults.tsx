/**
 * BatchScheduleResults — multi-week campaign schedule display.
 * Shows jobs assigned by week/zone/resource, capacity utilization, and ranked best-fit jobs.
 */

import { cn } from '@/shared/utils/cn';

// ---- Types ----------------------------------------------------------------

export interface BatchWeekSummary {
  weekLabel: string; // e.g. "Week of Feb 16"
  startDate: string; // ISO date
  jobCount: number;
  utilization: number; // 0–100
  zones: string[];
  resources: string[];
}

export interface RankedJob {
  jobId: string;
  customerName: string;
  address: string;
  jobType: string;
  projectedRevenue: number;
  revenueImpact: string; // e.g. "+$240/hr"
  bestFitResource: string;
  bestFitDate: string;
}

export interface BatchScheduleResultsProps {
  weeks: BatchWeekSummary[];
  rankedJobs: RankedJob[];
  onAssignJob?: (jobId: string) => void;
}

// ---- Component ------------------------------------------------------------

export function BatchScheduleResults({
  weeks,
  rankedJobs,
  onAssignJob,
}: BatchScheduleResultsProps) {
  return (
    <div
      data-testid="batch-schedule-results"
      className="space-y-4 rounded-lg border border-gray-200 bg-white p-4 shadow-sm"
    >
      <h3 className="text-sm font-semibold text-gray-900">
        Multi-Week Campaign Results
      </h3>

      {/* Week summaries */}
      <div className="space-y-2">
        {weeks.map((week) => (
          <div
            key={week.startDate}
            className="flex items-center justify-between rounded border border-gray-100 bg-gray-50 px-3 py-2 text-xs"
          >
            <div>
              <span className="font-medium text-gray-800">{week.weekLabel}</span>
              <span className="ml-2 text-gray-500">
                {week.jobCount} jobs · {week.zones.join(', ')}
              </span>
            </div>
            <div
              className={cn(
                'font-medium',
                week.utilization > 90
                  ? 'text-red-600'
                  : week.utilization >= 60
                    ? 'text-green-600'
                    : 'text-yellow-600'
              )}
            >
              {week.utilization}%
            </div>
          </div>
        ))}
      </div>

      {/* Ranked best-fit jobs */}
      {rankedJobs.length > 0 && (
        <div>
          <h4 className="mb-2 text-xs font-semibold text-gray-700">
            Best-Fit Jobs by Revenue Impact
          </h4>
          <div className="space-y-1">
            {rankedJobs.map((job) => (
              <div
                key={job.jobId}
                className="flex items-center justify-between rounded border border-gray-100 px-3 py-2 text-xs"
              >
                <div>
                  <span className="font-medium text-gray-800">
                    {job.customerName}
                  </span>
                  <span className="ml-1 text-gray-500">· {job.jobType}</span>
                  <div className="text-gray-400">{job.address}</div>
                  <div className="text-gray-500">
                    {job.bestFitResource} · {job.bestFitDate}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-green-700">
                    {job.revenueImpact}
                  </span>
                  {onAssignJob && (
                    <button
                      onClick={() => onAssignJob(job.jobId)}
                      className="rounded bg-blue-600 px-2 py-1 text-white hover:bg-blue-700"
                    >
                      Assign
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
