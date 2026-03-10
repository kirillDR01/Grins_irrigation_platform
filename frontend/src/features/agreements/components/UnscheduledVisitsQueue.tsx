import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { LoadingSpinner } from '@/shared/components/LoadingSpinner';
import { useJobsReadyToSchedule } from '@/features/jobs';
import { ChevronDown, ChevronUp, Calendar } from 'lucide-react';

interface GroupedJobs {
  label: string;
  count: number;
}

export function UnscheduledVisitsQueue() {
  const [collapsed, setCollapsed] = useState(false);
  const { data, isLoading, error } = useJobsReadyToSchedule();

  const jobs = data?.items ?? [];
  const count = jobs.length;

  // Group by job_type
  const grouped: GroupedJobs[] = [];
  const byType = new Map<string, number>();
  for (const job of jobs) {
    byType.set(job.job_type, (byType.get(job.job_type) ?? 0) + 1);
  }
  for (const [type, cnt] of byType) {
    grouped.push({ label: type, count: cnt });
  }
  grouped.sort((a, b) => b.count - a.count);

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
              {grouped.map((g) => (
                <div key={g.label} className="flex items-center justify-between px-4 py-3" data-testid={`unscheduled-group-${g.label}`}>
                  <div className="flex items-center gap-2">
                    <Calendar className="h-4 w-4 text-slate-400" />
                    <span className="text-sm text-slate-700">{g.label}</span>
                    <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">{g.count}</span>
                  </div>
                  <Link
                    to="/schedule/generate"
                    className="text-xs font-medium text-teal-600 hover:text-teal-700"
                    data-testid={`schedule-link-${g.label}`}
                  >
                    Schedule →
                  </Link>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
