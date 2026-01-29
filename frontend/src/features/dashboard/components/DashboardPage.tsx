/**
 * Main dashboard page component.
 * Displays metrics, schedule overview, and quick actions.
 */

import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { PageHeader } from '@/shared/components/PageHeader';
import { LoadingSpinner } from '@/shared/components/LoadingSpinner';
import {
  Users,
  Briefcase,
  Calendar,
  UserCheck,
  Plus,
  ArrowRight,
  Clock,
  CheckCircle,
  AlertCircle,
} from 'lucide-react';
import { useDashboardMetrics, useTodaySchedule, useJobsByStatus } from '../hooks';
import { MetricsCard } from './MetricsCard';
import { RecentActivity } from './RecentActivity';
import { AIQueryChat } from '@/features/ai/components/AIQueryChat';
import { MorningBriefing } from '@/features/ai/components/MorningBriefing';
import { CommunicationsQueue } from '@/features/ai/components/CommunicationsQueue';
import { OverdueInvoicesWidget, LienDeadlinesWidget } from '@/features/invoices';

export function DashboardPage() {
  const { data: metrics, isLoading: metricsLoading } = useDashboardMetrics();
  const { data: todaySchedule, isLoading: scheduleLoading } = useTodaySchedule();
  const { data: jobsByStatus, isLoading: jobsLoading } = useJobsByStatus();

  const isLoading = metricsLoading || scheduleLoading || jobsLoading;

  return (
    <div className="space-y-6" data-testid="dashboard-page">
      <PageHeader
        title="Dashboard"
        description="Overview of your business operations"
        action={
          <div className="flex gap-2">
            <Button asChild variant="outline" data-testid="view-schedule-btn">
              <Link to="/schedule">
                <Calendar className="mr-2 h-4 w-4" />
                View Schedule
              </Link>
            </Button>
            <Button asChild data-testid="new-job-btn">
              <Link to="/jobs?action=new">
                <Plus className="mr-2 h-4 w-4" />
                New Job
              </Link>
            </Button>
          </div>
        }
      />

      {isLoading ? (
        <div className="flex items-center justify-center h-64">
          <LoadingSpinner />
        </div>
      ) : (
        <>
          {/* Morning Briefing */}
          <MorningBriefing />

          {/* Metrics Cards */}
          <div
            className="grid gap-4 md:grid-cols-2 lg:grid-cols-4"
            data-testid="metrics-grid"
          >
            <MetricsCard
              title="Total Customers"
              value={metrics?.total_customers ?? 0}
              description={`${metrics?.active_customers ?? 0} active`}
              icon={Users}
              testId="customers-metric"
            />
            <MetricsCard
              title="Today's Appointments"
              value={todaySchedule?.total_appointments ?? 0}
              description={`${todaySchedule?.completed_appointments ?? 0} completed`}
              icon={Calendar}
              testId="appointments-metric"
            />
            <MetricsCard
              title="Jobs Pending"
              value={
                (jobsByStatus?.requested ?? 0) + (jobsByStatus?.approved ?? 0)
              }
              description={`${jobsByStatus?.in_progress ?? 0} in progress`}
              icon={Briefcase}
              testId="jobs-metric"
            />
            <MetricsCard
              title="Staff Available"
              value={metrics?.available_staff ?? 0}
              description={`of ${metrics?.total_staff ?? 0} total`}
              icon={UserCheck}
              testId="staff-metric"
            />
          </div>

          {/* Today's Schedule Summary */}
          <div className="grid gap-4 md:grid-cols-2">
            <Card data-testid="today-schedule-card">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-lg font-medium">
                  Today's Schedule
                </CardTitle>
                <Button asChild variant="ghost" size="sm">
                  <Link to="/schedule">
                    View All <ArrowRight className="ml-2 h-4 w-4" />
                  </Link>
                </Button>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Clock className="h-4 w-4 text-muted-foreground" />
                      <span className="text-sm">Upcoming</span>
                    </div>
                    <span className="font-semibold">
                      {todaySchedule?.upcoming_appointments ?? 0}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <AlertCircle className="h-4 w-4 text-orange-500" />
                      <span className="text-sm">In Progress</span>
                    </div>
                    <span className="font-semibold">
                      {todaySchedule?.in_progress_appointments ?? 0}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <CheckCircle className="h-4 w-4 text-green-500" />
                      <span className="text-sm">Completed</span>
                    </div>
                    <span className="font-semibold">
                      {todaySchedule?.completed_appointments ?? 0}
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Jobs by Status */}
            <Card data-testid="jobs-status-card">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-lg font-medium">Jobs by Status</CardTitle>
                <Button asChild variant="ghost" size="sm">
                  <Link to="/jobs">
                    View All <ArrowRight className="ml-2 h-4 w-4" />
                  </Link>
                </Button>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="text-sm">Requested</span>
                    <span className="font-semibold text-yellow-600">
                      {jobsByStatus?.requested ?? 0}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm">Approved</span>
                    <span className="font-semibold text-blue-600">
                      {jobsByStatus?.approved ?? 0}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm">Scheduled</span>
                    <span className="font-semibold text-purple-600">
                      {jobsByStatus?.scheduled ?? 0}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm">In Progress</span>
                    <span className="font-semibold text-orange-600">
                      {jobsByStatus?.in_progress ?? 0}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm">Completed</span>
                    <span className="font-semibold text-green-600">
                      {jobsByStatus?.completed ?? 0}
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Invoice Widgets */}
          <div className="grid gap-4 md:grid-cols-2" data-testid="invoice-widgets-section">
            <OverdueInvoicesWidget />
            <LienDeadlinesWidget />
          </div>

          {/* Quick Actions */}
          <Card data-testid="quick-actions-card">
            <CardHeader>
              <CardTitle className="text-lg font-medium">Quick Actions</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-2">
                <Button asChild variant="outline" data-testid="add-customer-action">
                  <Link to="/customers?action=new">
                    <Plus className="mr-2 h-4 w-4" />
                    Add Customer
                  </Link>
                </Button>
                <Button asChild variant="outline" data-testid="add-job-action">
                  <Link to="/jobs?action=new">
                    <Plus className="mr-2 h-4 w-4" />
                    Create Job
                  </Link>
                </Button>
                <Button asChild variant="outline" data-testid="schedule-action">
                  <Link to="/schedule?action=new">
                    <Plus className="mr-2 h-4 w-4" />
                    Schedule Appointment
                  </Link>
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Recent Activity */}
          <RecentActivity />

          {/* Communications Queue */}
          <CommunicationsQueue />

          {/* AI Query Chat */}
          <AIQueryChat />
        </>
      )}
    </div>
  );
}
