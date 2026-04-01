/**
 * ResourceScheduleView Component
 *
 * Mobile schedule card showing the resource's daily route with
 * route order, ETAs, pre-job flags, job details, and total drive time.
 */

import {
  MapPin,
  Clock,
  Car,
  Star,
  AlertTriangle,
  ClipboardList,
} from 'lucide-react';
import { useResourceSchedule } from '../hooks/useResourceSchedule';
import type { ResourceJobCard, ResourceScheduleParams } from '../types';

// ── Status styling ─────────────────────────────────────────────────────

const STATUS_STYLES: Record<string, string> = {
  scheduled: 'bg-slate-100 text-slate-600',
  en_route: 'bg-blue-100 text-blue-700',
  in_progress: 'bg-amber-100 text-amber-700',
  completed: 'bg-green-100 text-green-700',
  cancelled: 'bg-red-100 text-red-600',
};

// ── Job card sub-component ─────────────────────────────────────────────

function JobCard({ job }: { job: ResourceJobCard }) {
  return (
    <div
      className="rounded-xl border border-slate-200 bg-white p-3 space-y-2"
      data-testid={`job-card-${job.id}`}
    >
      {/* Top row: order + status */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="flex items-center justify-center h-6 w-6 rounded-full bg-teal-100 text-teal-700 text-xs font-bold">
            {job.route_order}
          </span>
          <span className="font-medium text-slate-800 text-sm">
            {job.job_type}
          </span>
          {job.is_vip && <Star className="h-3.5 w-3.5 text-amber-400" />}
          {job.has_prejob_flag && (
            <ClipboardList className="h-3.5 w-3.5 text-blue-500" />
          )}
        </div>
        <span
          className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_STYLES[job.status] ?? STATUS_STYLES.scheduled}`}
        >
          {job.status.replace('_', ' ')}
        </span>
      </div>

      {/* Address */}
      <div className="flex items-start gap-1.5 text-xs text-slate-600">
        <MapPin className="h-3.5 w-3.5 mt-0.5 flex-shrink-0 text-slate-400" />
        <span>{job.address}</span>
      </div>

      {/* Duration + ETA */}
      <div className="flex items-center gap-4 text-xs text-slate-500">
        <span className="flex items-center gap-1">
          <Clock className="h-3.5 w-3.5" />
          {job.estimated_duration} min
        </span>
        {job.eta && (
          <span className="flex items-center gap-1">
            ETA {job.eta}
          </span>
        )}
        {job.time_window_start && job.time_window_end && (
          <span className="text-slate-400">
            {job.time_window_start} – {job.time_window_end}
          </span>
        )}
      </div>

      {/* Customer notes */}
      {job.customer_notes && (
        <p className="text-xs text-slate-500 italic">{job.customer_notes}</p>
      )}

      {/* Pre-job flag */}
      {job.has_prejob_flag && (
        <div className="flex items-center gap-1 text-xs text-blue-600 bg-blue-50 rounded-lg px-2 py-1">
          <AlertTriangle className="h-3 w-3" />
          Special prep required — check pre-job info
        </div>
      )}
    </div>
  );
}

// ── Main component ─────────────────────────────────────────────────────

interface ResourceScheduleViewProps {
  params?: ResourceScheduleParams;
}

export function ResourceScheduleView({ params }: ResourceScheduleViewProps) {
  const { data, isLoading, error } = useResourceSchedule(params);

  if (isLoading) {
    return (
      <div
        className="p-4 text-center text-slate-400 text-sm"
        data-testid="resource-schedule-view"
      >
        Loading schedule…
      </div>
    );
  }

  if (error) {
    return (
      <div
        className="p-4 text-center text-red-500 text-sm"
        data-testid="resource-schedule-view"
      >
        Failed to load schedule
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className="space-y-3 p-4" data-testid="resource-schedule-view">
      {/* Day header */}
      <div className="flex items-center justify-between">
        <h3 className="font-bold text-slate-800">
          {new Date(data.date).toLocaleDateString('en-US', {
            weekday: 'long',
            month: 'short',
            day: 'numeric',
          })}
        </h3>
        <span className="text-xs text-slate-500">
          {data.jobs.length} job{data.jobs.length !== 1 ? 's' : ''}
        </span>
      </div>

      {/* Drive time summary */}
      <div className="flex items-center gap-4 text-xs text-slate-500">
        <span className="flex items-center gap-1">
          <Car className="h-3.5 w-3.5" />
          {data.total_drive_minutes} min drive
        </span>
        <span className="flex items-center gap-1">
          <Clock className="h-3.5 w-3.5" />
          {data.total_job_minutes} min work
        </span>
        <span>{data.utilization_pct}% utilized</span>
      </div>

      {/* Job cards */}
      <div className="space-y-2">
        {data.jobs
          .sort((a, b) => a.route_order - b.route_order)
          .map((job) => (
            <JobCard key={job.id} job={job} />
          ))}
      </div>

      {data.jobs.length === 0 && (
        <p className="text-center text-slate-400 text-sm py-8">
          No jobs scheduled for today
        </p>
      )}
    </div>
  );
}
