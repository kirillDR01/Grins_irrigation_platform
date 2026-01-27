/**
 * Morning Briefing component.
 * Displays personalized daily summary with overnight requests, schedule, and pending actions.
 */

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Link } from 'react-router-dom';
import { Sun, Moon, Sunrise, Sunset, ArrowRight, AlertCircle, Clock, DollarSign, MessageSquare } from 'lucide-react';
import { useDashboardMetrics, useJobsByStatus, useTodaySchedule } from '@/features/dashboard/hooks';

function getGreeting(): { text: string; icon: typeof Sun } {
  const hour = new Date().getHours();
  if (hour < 6) return { text: 'Good night', icon: Moon };
  if (hour < 12) return { text: 'Good morning', icon: Sunrise };
  if (hour < 18) return { text: 'Good afternoon', icon: Sun };
  if (hour < 22) return { text: 'Good evening', icon: Sunset };
  return { text: 'Good night', icon: Moon };
}

export function MorningBriefing() {
  const { data: metrics } = useDashboardMetrics();
  const { data: jobsByStatus } = useJobsByStatus();
  const { data: todaySchedule } = useTodaySchedule();

  const greeting = getGreeting();
  const GreetingIcon = greeting.icon;

  const overnightRequests = (jobsByStatus?.requested ?? 0);
  const unconfirmedAppointments = (todaySchedule?.upcoming_appointments ?? 0);
  const pendingCommunications = 0; // TODO: Get from communications API
  const outstandingInvoices = 0; // TODO: Get from invoices API

  return (
    <Card data-testid="morning-briefing" className="border-primary/20">
      <CardHeader className="pb-3">
        <div className="flex items-center gap-2">
          <GreetingIcon className="h-5 w-5 text-primary" />
          <CardTitle className="text-xl" data-testid="greeting">
            {greeting.text}, Viktor!
          </CardTitle>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Overnight Requests */}
        <div data-testid="overnight-requests" className="space-y-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertCircle className="h-4 w-4 text-yellow-600" />
              <span className="font-medium">Overnight Requests</span>
            </div>
            <span className="text-2xl font-bold text-yellow-600">{overnightRequests}</span>
          </div>
          {overnightRequests > 0 && (
            <div className="text-sm text-muted-foreground pl-6">
              {jobsByStatus?.requested ?? 0} need categorization
            </div>
          )}
        </div>

        {/* Today's Schedule */}
        <div data-testid="today-schedule" className="space-y-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Clock className="h-4 w-4 text-blue-600" />
              <span className="font-medium">Today's Schedule</span>
            </div>
            <span className="text-2xl font-bold text-blue-600">
              {todaySchedule?.total_appointments ?? 0}
            </span>
          </div>
          <div className="text-sm text-muted-foreground pl-6 space-y-1">
            <div>{todaySchedule?.completed_appointments ?? 0} completed</div>
            <div>{todaySchedule?.in_progress_appointments ?? 0} in progress</div>
            <div>{todaySchedule?.upcoming_appointments ?? 0} upcoming</div>
          </div>
        </div>

        {/* Unconfirmed Appointments */}
        {unconfirmedAppointments > 0 && (
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <AlertCircle className="h-4 w-4 text-orange-600" />
                <span className="font-medium">Unconfirmed</span>
              </div>
              <span className="text-2xl font-bold text-orange-600">{unconfirmedAppointments}</span>
            </div>
          </div>
        )}

        {/* Pending Communications */}
        <div data-testid="pending-communications" className="space-y-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <MessageSquare className="h-4 w-4 text-purple-600" />
              <span className="font-medium">Pending Messages</span>
            </div>
            <span className="text-2xl font-bold text-purple-600">{pendingCommunications}</span>
          </div>
        </div>

        {/* Outstanding Invoices */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <DollarSign className="h-4 w-4 text-green-600" />
              <span className="font-medium">Outstanding Invoices</span>
            </div>
            <span className="text-2xl font-bold text-green-600">{outstandingInvoices}</span>
          </div>
        </div>

        {/* Quick Actions */}
        <div data-testid="quick-actions" className="pt-2 space-y-2">
          <div className="text-sm font-medium text-muted-foreground">Quick Actions</div>
          <div className="flex flex-wrap gap-2">
            {overnightRequests > 0 && (
              <Button asChild variant="outline" size="sm" data-testid="review-requests-btn">
                <Link to="/jobs?status=requested">
                  Review Requests <ArrowRight className="ml-1 h-3 w-3" />
                </Link>
              </Button>
            )}
            <Button asChild variant="outline" size="sm" data-testid="morning-briefing-view-schedule-btn">
              <Link to="/schedule">
                View Schedule <ArrowRight className="ml-1 h-3 w-3" />
              </Link>
            </Button>
            {pendingCommunications > 0 && (
              <Button asChild variant="outline" size="sm" data-testid="send-confirmations-btn">
                <Link to="/communications">
                  Send Confirmations <ArrowRight className="ml-1 h-3 w-3" />
                </Link>
              </Button>
            )}
            {outstandingInvoices > 0 && (
              <Button asChild variant="outline" size="sm" data-testid="view-invoices-btn">
                <Link to="/invoices">
                  View Invoices <ArrowRight className="ml-1 h-3 w-3" />
                </Link>
              </Button>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
