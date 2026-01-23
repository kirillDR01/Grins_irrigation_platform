/**
 * RecentActivity component for displaying recent jobs and appointments.
 * Shows a list of recent activity items with links to detail pages.
 */

import { Link } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ArrowRight, Briefcase, Calendar, User } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
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
      title: `Job: ${job.job_type}`,
      description: job.description || 'No description',
      status: job.status,
      timestamp: job.created_at,
      link: `/jobs/${job.id}`,
    })),
    ...(appointmentsData?.items ?? []).map((apt) => ({
      id: apt.id,
      type: 'appointment' as const,
      title: `Appointment`,
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
      requested: 'bg-yellow-100 text-yellow-800',
      approved: 'bg-blue-100 text-blue-800',
      scheduled: 'bg-purple-100 text-purple-800',
      in_progress: 'bg-orange-100 text-orange-800',
      completed: 'bg-green-100 text-green-800',
      cancelled: 'bg-red-100 text-red-800',
      pending: 'bg-yellow-100 text-yellow-800',
      confirmed: 'bg-blue-100 text-blue-800',
    };
    return colors[status] || 'bg-gray-100 text-gray-800';
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
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-lg font-medium">Recent Activity</CardTitle>
        <Button asChild variant="ghost" size="sm">
          <Link to="/jobs">
            View All <ArrowRight className="ml-2 h-4 w-4" />
          </Link>
        </Button>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="space-y-4">
            {[...Array(5)].map((_, i) => (
              <div
                key={i}
                className="flex items-center gap-4 animate-pulse"
              >
                <div className="h-8 w-8 rounded-full bg-muted" />
                <div className="flex-1 space-y-2">
                  <div className="h-4 w-1/3 bg-muted rounded" />
                  <div className="h-3 w-1/2 bg-muted rounded" />
                </div>
              </div>
            ))}
          </div>
        ) : recentItems.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            <User className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p>No recent activity</p>
          </div>
        ) : (
          <div className="space-y-4" data-testid="activity-list">
            {recentItems.map((item) => (
              <Link
                key={`${item.type}-${item.id}`}
                to={item.link}
                className="flex items-center gap-4 p-2 rounded-lg hover:bg-muted transition-colors"
                data-testid={`activity-item-${item.type}-${item.id}`}
              >
                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-muted">
                  {getIcon(item.type)}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{item.title}</p>
                  <p className="text-xs text-muted-foreground truncate">
                    {item.description}
                  </p>
                </div>
                <div className="flex flex-col items-end gap-1">
                  <Badge
                    variant="secondary"
                    className={getStatusColor(item.status)}
                  >
                    {item.status.replace('_', ' ')}
                  </Badge>
                  <span className="text-xs text-muted-foreground">
                    {formatDistanceToNow(new Date(item.timestamp), {
                      addSuffix: true,
                    })}
                  </span>
                </div>
              </Link>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
