/**
 * ResourceScheduleView — Mobile schedule card with route order, ETAs, and pre-job flags.
 */

import type { ResourceSchedule } from '../types';

interface Props {
  schedule: ResourceSchedule;
}

const STATUS_LABELS: Record<string, string> = {
  scheduled: 'Scheduled',
  in_progress: 'In Progress',
  completed: 'Completed',
};

const STATUS_COLORS: Record<string, string> = {
  scheduled: 'bg-blue-100 text-blue-800',
  in_progress: 'bg-yellow-100 text-yellow-800',
  completed: 'bg-green-100 text-green-800',
};

export function ResourceScheduleView({ schedule }: Props) {
  return (
    <div data-testid="resource-schedule-view" className="flex flex-col gap-3 p-4">
      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold text-gray-900">
          Today's Route — {schedule.date}
        </h2>
        <span className="text-sm text-gray-500">
          {Math.round(schedule.total_drive_minutes)} min drive
        </span>
      </div>

      {schedule.jobs.length === 0 ? (
        <p className="text-sm text-gray-500 py-4 text-center">No jobs scheduled.</p>
      ) : (
        <ol className="flex flex-col gap-3">
          {schedule.jobs.map((job) => (
            <li
              key={job.id}
              data-testid={`route-card-${job.route_order}`}
              data-job-id={job.id}
              className="bg-white rounded-xl border border-gray-200 shadow-sm p-4"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span className="flex-shrink-0 w-6 h-6 rounded-full bg-gray-100 text-gray-700 text-xs font-bold flex items-center justify-center">
                    {job.route_order}
                  </span>
                  <div>
                    <p className="text-sm font-semibold text-gray-900">{job.job_type}</p>
                    <p className="text-xs text-gray-500">{job.customer_name}</p>
                  </div>
                </div>
                <span
                  className={`text-xs font-medium px-2 py-0.5 rounded-full ${STATUS_COLORS[job.status] ?? 'bg-gray-100 text-gray-700'}`}
                >
                  {STATUS_LABELS[job.status] ?? job.status}
                </span>
              </div>

              <div className="mt-2 space-y-1">
                <p className="text-xs text-gray-600">{job.address}</p>
                <div className="flex items-center gap-3 text-xs text-gray-500">
                  <span>ETA {job.eta}</span>
                  <span>~{job.estimated_duration_minutes} min</span>
                </div>
                {job.gate_code && (
                  <p className="text-xs text-amber-700 font-medium">
                    Gate: {job.gate_code}
                  </p>
                )}
                {job.notes && (
                  <p className="text-xs text-gray-500 italic">{job.notes}</p>
                )}
                {job.requires_special_prep && (
                  <p className="text-xs text-red-600 font-medium">⚠ Special prep required</p>
                )}
              </div>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
