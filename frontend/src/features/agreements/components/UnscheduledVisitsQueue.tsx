import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { LoadingSpinner } from '@/shared/components/LoadingSpinner';
import { useJobsReadyToSchedule } from '@/features/jobs';
import { formatJobType } from '@/features/jobs/types';
import { ChevronDown, ChevronUp, Calendar, Clock, MapPin } from 'lucide-react';
import type { Job } from '@/features/jobs/types';

function formatDateRange(start: string | null, end: string | null): string {
  if (!start && !end) return '';
  const fmt = (d: string) => new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  if (start && end) return `${fmt(start)} – ${fmt(end)}`;
  if (start) return `From ${fmt(start)}`;
  return `By ${fmt(end!)}`;
}

function formatDuration(minutes: number | null): string {
  if (minutes === null) return '';
  if (minutes < 60) return `${minutes}m`;
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return m === 0 ? `${h}h` : `${h}h ${m}m`;
}

interface GroupedJobs {
  label: string;
  jobType: string;
  jobs: Job[];
}

export function UnscheduledVisitsQueue() {
  const [collapsed, setCollapsed] = useState(false);
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set());
  const { data, isLoading, error } = useJobsReadyToSchedule();

  const jobs = data?.items ?? [];
  const count = jobs.length;

  // Group by job_type
  const grouped: GroupedJobs[] = [];
  const byType = new Map<string, Job[]>();
  for (const job of jobs) {
    const existing = byType.get(job.job_type) ?? [];
    existing.push(job);
    byType.set(job.job_type, existing);
  }
  for (const [type, typeJobs] of byType) {
    grouped.push({ label: formatJobType(type), jobType: type, jobs: typeJobs });
  }
  grouped.sort((a, b) => b.jobs.length - a.jobs.length);

  const toggleGroup = (jobType: string) => {
    setExpandedGroups((prev) => {
      const next = new Set(prev);
      if (next.has(jobType)) {
        next.delete(jobType);
      } else {
        next.add(jobType);
      }
      return next;
    });
  };

  return (
    <div className="bg-white rounded-xl border border-slate-100 overflow-hidden" data-testid="unscheduled-visits-queue">
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-slate-50 transition-colors"
      >
        <div className="flex items-center gap-2">
          <span className="font-medium text-slate-700">Unscheduled Visits</span>
          <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-700">{count}</span>
        </div>
        {collapsed ? <ChevronDown className="h-4 w-4 text-slate-400" /> : <ChevronUp className="h-4 w-4 text-slate-400" />}
      </button>

      {!collapsed && (
        <div className="border-t border-slate-100">
          {isLoading && <div className="p-4"><LoadingSpinner /></div>}
          {error && <Alert variant="destructive" className="m-4"><AlertDescription>Failed to load unscheduled visits.</AlertDescription></Alert>}
          {!isLoading && !error && count === 0 && (
            <p className="p-4 text-sm text-slate-500">All visits are scheduled.</p>
          )}
          {grouped.length > 0 && (
            <div className="divide-y divide-slate-50">
              {grouped.map((g) => {
                const isExpanded = expandedGroups.has(g.jobType);
                return (
                  <div key={g.jobType} data-testid={`unscheduled-group-${g.jobType}`}>
                    {/* Group header row */}
                    <button
                      onClick={() => toggleGroup(g.jobType)}
                      className="w-full flex items-center justify-between px-4 py-3 hover:bg-slate-50 transition-colors"
                      data-testid={`unscheduled-toggle-${g.jobType}`}
                    >
                      <div className="flex items-center gap-2">
                        <Calendar className="h-4 w-4 text-slate-400" />
                        <span className="text-sm font-medium text-slate-700">{g.label}</span>
                        <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">{g.jobs.length}</span>
                      </div>
                      <div className="flex items-center gap-3">
                        <Link
                          to="/schedule/generate"
                          className="text-xs font-medium text-teal-600 hover:text-teal-700"
                          onClick={(e) => e.stopPropagation()}
                          data-testid={`schedule-link-${g.jobType}`}
                        >
                          Schedule All →
                        </Link>
                        {isExpanded
                          ? <ChevronUp className="h-3.5 w-3.5 text-slate-400" />
                          : <ChevronDown className="h-3.5 w-3.5 text-slate-400" />
                        }
                      </div>
                    </button>

                    {/* Expanded individual jobs */}
                    {isExpanded && (
                      <div className="bg-slate-50/50">
                        {g.jobs.map((job) => (
                          <Link
                            key={job.id}
                            to={`/jobs/${job.id}`}
                            className="flex items-center justify-between px-4 py-2.5 pl-10 hover:bg-slate-100 transition-colors border-t border-slate-100/80"
                            data-testid={`unscheduled-job-${job.id}`}
                          >
                            <div className="flex items-center gap-3 min-w-0">
                              <span className="text-sm text-slate-700 truncate">
                                {formatJobType(job.job_type)}
                              </span>
                              {job.target_start_date || job.target_end_date ? (
                                <span className="flex items-center gap-1 text-xs text-slate-500">
                                  <MapPin className="h-3 w-3" />
                                  {formatDateRange(job.target_start_date, job.target_end_date)}
                                </span>
                              ) : null}
                              {job.estimated_duration_minutes ? (
                                <span className="flex items-center gap-1 text-xs text-slate-400">
                                  <Clock className="h-3 w-3" />
                                  {formatDuration(job.estimated_duration_minutes)}
                                </span>
                              ) : null}
                              {job.priority_level > 0 && (
                                <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                                  job.priority_level >= 2
                                    ? 'bg-red-100 text-red-700'
                                    : 'bg-orange-100 text-orange-700'
                                }`}>
                                  {job.priority_level >= 2 ? 'Urgent' : 'High'}
                                </span>
                              )}
                            </div>
                            <span className="text-xs text-teal-600 font-medium shrink-0">View →</span>
                          </Link>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
