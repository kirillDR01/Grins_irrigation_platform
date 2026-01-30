/**
 * RecentActivity component for displaying recent jobs and appointments.
 * Shows a list of recent activity items with links to detail pages.
 */

import { Link } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Briefcase, Calendar, User } from 'lucide-react';
import { format } from 'date-fns';
import { useJobs } from '@/features/jobs/hooks';
import { useAppointments } from '@/features/schedule/hooks';

export function RecentActivity() {
  const { data: jobsData, isLoading: jobsLoading } = useJobs({
    page: 1,
    page_size: 5,
  });
  const { data: appointmentsData, isLoading: appointmentsLoading } =
    useAppointments({
      page: 1,
      page_size: 5,
    });

  const isLoading = jobsLoading || appointmentsLoading;

  // Combine and sort recent items
  const recentItems = [
    ...(jobsData?.items ?? []).map((job) => ({
      id: job.id,
      type: 'job' as const,
      title: job.job_type,
      description: job.description || 'No description',
      status: job.status,
      timestamp: job.created_at,
      link: `/jobs/${job.id}`,
    })),
    ...(appointmentsData?.items ?? []).map((apt) => ({
      id: apt.id,
      type: 'appointment' as const,
      title: 'Appointment',
      description: `Scheduled for ${apt.scheduled_date}`,
      status: apt.status,
      timestamp: apt.created_at,
      link: `/schedule?appointment=${apt.id}`,
    })),
  ]
    .sort(
      (a, b) =>
        new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
    )
    .slice(0, 10);

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      requested: 'bg-amber-100 text-amber-700',
      approved: 'bg-blue-100 text-blue-700',
      scheduled: 'bg-violet-100 text-violet-700',
      in_progress: 'bg-orange-100 text-orange-700',
      completed: 'bg-emerald-100 text-emerald-700',
      cancelled: 'bg-red-100 text-red-700',
      pending: 'bg-amber-100 text-amber-700',
      confirmed: 'bg-blue-100 text-blue-700',
      closed: 'bg-slate-100 text-slate-500',
    };
    return colors[status] || 'bg-slate-100 text-slate-600';
  };

  const getIcon = (type: 'job' | 'appointment') => {
    return type === 'job' ? (
      <Briefcase className="h-4 w-4" />
    ) : (
      <Calendar className="h-4 w-4" />
    );
  };

  return (
    <Card data-testid="recent-activity-card">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-6">
        <CardTitle className="font-bold text-slate-800 text-lg">Recent Jobs</CardTitle>
        <Link
          to="/jobs"
          className="text-teal-600 text-sm font-medium hover:text-teal-700 flex items-center gap-1"
          data-testid="view-all-jobs-link"
        >
          View All
        </Link>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="space-y-4">
            {[...Array(5)].map((_, i) => (
              <div
                key={i}
                className="flex items-center justify-between p-4 bg-slate-50 rounded-xl animate-pulse"
              >
                <div className="flex items-center gap-4">
                  <div className="h-10 w-10 rounded-lg bg-slate-200" />
                  <div className="space-y-2">
                    <div className="h-4 w-32 bg-slate-200 rounded" />
                    <div className="h-3 w-24 bg-slate-200 rounded" />
                  </div>
                </div>
                <div className="h-6 w-20 bg-slate-200 rounded-full" />
              </div>
            ))}
          </div>
        ) : recentItems.length === 0 ? (
          <div className="text-center py-8 text-slate-400">
            <User className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p>No recent activity</p>
          </div>
        ) : (
          <div className="space-y-4" data-testid="activity-list">
            {recentItems.map((item) => (
              <Link
                key={`${item.type}-${item.id}`}
                to={item.link}
                className="flex items-center justify-between p-4 bg-slate-50 rounded-xl hover:bg-slate-100 transition-colors cursor-pointer group"
                data-testid={`activity-item-${item.type}-${item.id}`}
              >
                <div className="flex items-center gap-4">
                  <div className="bg-white p-3 rounded-lg shadow-sm group-hover:shadow text-teal-600 transition-shadow">
                    {getIcon(item.type)}
                  </div>
                  <div>
                    <p className="font-semibold text-slate-800">{item.title}</p>
                    <p className="text-xs text-slate-500">
                      {format(new Date(item.timestamp), 'MMM d, yyyy')} • ID: {item.id.slice(0, 8)}
                    </p>
                  </div>
                </div>
                <Badge
                  variant="secondary"
                  className={`${getStatusColor(item.status)} px-3 py-1 rounded-full text-xs font-medium`}
                >
                  {item.status.replace('_', ' ')}
                </Badge>
              </Link>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
