/**
 * Main dashboard page component.
 * Displays metrics, schedule overview, and quick actions.
 */

import { Link, useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { PageHeader } from '@/shared/components/PageHeader';
import { LoadingSpinner } from '@/shared/components/LoadingSpinner';
import {
  Calendar,
  UserCheck,
  Plus,
  ArrowRight,
  Clock,
  CheckCircle,
  AlertCircle,
  Funnel,
} from 'lucide-react';
import { useAuth } from '@/features/auth';
import { useDashboardMetrics, useTodaySchedule } from '../hooks';
import { MetricsCard } from './MetricsCard';
import { MessagesWidget } from './MessagesWidget';
import { InvoiceMetricsWidget } from './InvoiceMetricsWidget';
import { RecentActivity } from './RecentActivity';
import { TechnicianAvailability } from './TechnicianAvailability';
import { SubscriptionDashboardWidgets } from './SubscriptionDashboardWidgets';
import { LeadDashboardWidgets } from './LeadDashboardWidgets';
import { JobStatusGrid } from './JobStatusGrid';
import { AIQueryChat } from '@/features/ai/components/AIQueryChat';
import { MorningBriefing } from '@/features/ai/components/MorningBriefing';
import { OverdueInvoicesWidget, LienDeadlinesWidget } from '@/features/invoices';

export function DashboardPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { data: metrics, isLoading: metricsLoading } = useDashboardMetrics();
  const { data: todaySchedule, isLoading: scheduleLoading } = useTodaySchedule();

  const isLoading = metricsLoading || scheduleLoading;

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500" data-testid="dashboard-page">
      <PageHeader
        title={`Hello, ${user?.name?.split(' ')[0] ?? 'there'}!`}
        description="Here's what's happening today."
        action={
          <div className="flex gap-2">
            <Button asChild variant="secondary" data-testid="view-schedule-btn">
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

          {/* Subscription Widgets */}
          <SubscriptionDashboardWidgets />

          {/* Lead Widgets */}
          <LeadDashboardWidgets />

          {/* Metrics Cards */}
          <div
            className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8"
            data-testid="metrics-grid"
          >
            <MetricsCard
              title="Today's Schedule"
              value={todaySchedule?.total_appointments ?? 0}
              description={`${todaySchedule?.completed_appointments ?? 0} completed`}
              icon={Calendar}
              variant="teal"
              testId="appointments-metric"
            />
            <MessagesWidget />
            <InvoiceMetricsWidget />
            <MetricsCard
              title="Staff"
              value={metrics?.available_staff ?? 0}
              description={`of ${metrics?.total_staff ?? 0} available`}
              icon={UserCheck}
              variant="blue"
              testId="staff-metric"
            />
          </div>

          {/* New Leads Card */}
          {(() => {
            const uncontacted = metrics?.uncontacted_leads ?? 0;
            const colorClass =
              uncontacted === 0
                ? 'border-green-200 bg-green-50'
                : uncontacted <= 5
                  ? 'border-amber-200 bg-amber-50'
                  : 'border-red-200 bg-red-50';
            const iconColorClass =
              uncontacted === 0
                ? 'text-green-600 bg-green-100'
                : uncontacted <= 5
                  ? 'text-amber-600 bg-amber-100'
                  : 'text-red-600 bg-red-100';
            const textColorClass =
              uncontacted === 0
                ? 'text-green-700'
                : uncontacted <= 5
                  ? 'text-amber-700'
                  : 'text-red-700';
            return (
              <Card
                data-testid="leads-metric"
                className={`cursor-pointer transition-all hover:shadow-md ${colorClass}`}
                onClick={() => navigate('/leads?status=new')}
              >
                <CardContent className="p-6">
                  <div className="flex items-center justify-between">
                    <div className="space-y-2">
                      <p className="text-sm font-semibold uppercase tracking-wider text-slate-400">
                        New Leads
                      </p>
                      <div className="text-3xl font-bold text-slate-800">
                        {metrics?.new_leads_today ?? 0}
                      </div>
                      <p className={`text-xs font-medium ${textColorClass}`}>
                        {uncontacted} uncontacted
                      </p>
                    </div>
                    <div className={`p-3 rounded-xl ${iconColorClass}`}>
                      <Funnel className="h-5 w-5" />
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })()}

          {/* Job Status Grid — 6 categories */}
          <JobStatusGrid />

          {/* Today's Schedule Summary */}
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

          {/* Two-column layout: Recent Jobs and Technician Availability */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8" data-testid="two-column-section">
            {/* Recent Activity (left) */}
            <RecentActivity />
            {/* Technician Availability (right) */}
            <TechnicianAvailability />
          </div>

          {/* AI Query Chat */}
          <AIQueryChat />
        </>
      )}
    </div>
  );
}
