/**
 * Main schedule page component.
 * Displays calendar view with appointments.
 * Includes clear day feature and recently cleared section.
 */

import { useState, useMemo } from 'react';
import { format } from 'date-fns';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { PageHeader } from '@/shared/components/PageHeader';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Plus, Calendar, List } from 'lucide-react';
import { CalendarView } from './CalendarView';
import { AppointmentForm } from './AppointmentForm';
import { AppointmentDetail } from './AppointmentDetail';
import { AppointmentList } from './AppointmentList';
import { ClearDayButton } from './ClearDayButton';
import { ClearDayDialog } from './ClearDayDialog';
import { RecentlyClearedSection } from './RecentlyClearedSection';
import { scheduleGenerationApi } from '../api/scheduleGenerationApi';
import { useDailySchedule, appointmentKeys } from '../hooks/useAppointments';
import type { ScheduleClearRequest } from '../types';

type ViewMode = 'calendar' | 'list';

export function SchedulePage() {
  const [viewMode, setViewMode] = useState<ViewMode>('calendar');
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [selectedAppointmentId, setSelectedAppointmentId] = useState<
    string | null
  >(null);
  const [selectedDate, setSelectedDate] = useState<Date | null>(null);
  const [clearDayDate, setClearDayDate] = useState<Date>(new Date());
  const [showClearDayDialog, setShowClearDayDialog] = useState(false);

  const queryClient = useQueryClient();

  // Fetch appointments for the selected clear day date
  const formattedClearDate = format(clearDayDate, 'yyyy-MM-dd');
  const { data: dailySchedule } = useDailySchedule(formattedClearDate);

  // Get appointment count and affected jobs for the clear day dialog
  const appointmentCount = dailySchedule?.appointments?.length ?? 0;
  const affectedJobs = useMemo(() => {
    if (!dailySchedule?.appointments) return [];
    return dailySchedule.appointments.map((apt) => ({
      job_id: apt.job_id,
      customer_name: apt.customer_name ?? 'Unknown Customer',
      service_type: apt.service_type ?? 'Service',
    }));
  }, [dailySchedule]);

  // Clear schedule mutation
  const clearScheduleMutation = useMutation({
    mutationFn: (request: ScheduleClearRequest) =>
      scheduleGenerationApi.clearSchedule(request),
    onSuccess: (data) => {
      // Invalidate all appointment queries
      queryClient.invalidateQueries({ queryKey: appointmentKeys.all });
      // Invalidate recent clears
      queryClient.invalidateQueries({ queryKey: ['schedule', 'recent-clears'] });

      toast.success('Schedule Cleared', {
        description: `Cleared ${data.appointments_deleted} appointments and reset ${data.jobs_reset} jobs.`,
      });
      setShowClearDayDialog(false);
    },
    onError: (error: Error) => {
      toast.error('Error', {
        description: error.message || 'Failed to clear schedule',
      });
    },
  });

  const handleDateClick = (date: Date) => {
    setSelectedDate(date);
    setShowCreateDialog(true);
  };

  const handleEventClick = (appointmentId: string) => {
    setSelectedAppointmentId(appointmentId);
  };

  const handleCreateSuccess = () => {
    setShowCreateDialog(false);
    setSelectedDate(null);
  };

  const handleCloseDetail = () => {
    setSelectedAppointmentId(null);
  };

  const handleClearDayClick = () => {
    // Use today's date as default for clear day
    setClearDayDate(new Date());
    setShowClearDayDialog(true);
  };

  const handleClearDayConfirm = () => {
    clearScheduleMutation.mutate({
      schedule_date: formattedClearDate,
      notes: `Cleared via Schedule page on ${format(new Date(), 'yyyy-MM-dd HH:mm')}`,
    });
  };

  const handleViewClearDetails = (auditId: string) => {
    // For now, just log - could open a detail dialog in the future
    console.log('View clear details:', auditId);
    toast.info('Audit Details', {
      description: `Viewing audit ${auditId}`,
    });
  };

  return (
    <div 
      data-testid="schedule-page" 
      className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500"
    >
      <PageHeader
        title="Schedule"
        description="Manage appointments and view daily/weekly schedules"
        action={
          <div className="flex items-center gap-4">
            <ClearDayButton
              onClick={handleClearDayClick}
              disabled={clearScheduleMutation.isPending}
            />
            <Tabs
              value={viewMode}
              onValueChange={(v) => setViewMode(v as ViewMode)}
              data-testid="schedule-view-toggle"
            >
              <TabsList className="bg-slate-100 rounded-lg p-1 flex">
                <TabsTrigger 
                  value="calendar" 
                  data-testid="view-calendar"
                  className="data-[state=active]:bg-white data-[state=active]:text-slate-900 data-[state=active]:shadow-sm"
                >
                  <Calendar className="mr-2 h-4 w-4" />
                  Calendar
                </TabsTrigger>
                <TabsTrigger 
                  value="list" 
                  data-testid="view-list"
                  className="data-[state=active]:bg-white data-[state=active]:text-slate-900 data-[state=active]:shadow-sm"
                >
                  <List className="mr-2 h-4 w-4" />
                  List
                </TabsTrigger>
              </TabsList>
            </Tabs>
            <Button
              onClick={() => setShowCreateDialog(true)}
              data-testid="add-appointment-btn"
              className="bg-teal-500 hover:bg-teal-600 text-white"
            >
              <Plus className="mr-2 h-4 w-4" />
              New Appointment
            </Button>
          </div>
        }
      />

      {/* Main Content */}
      <div className="bg-white rounded-lg border shadow-sm">
        {viewMode === 'calendar' ? (
          <CalendarView
            onDateClick={handleDateClick}
            onEventClick={handleEventClick}
          />
        ) : (
          <AppointmentList
            onAppointmentClick={(id) => setSelectedAppointmentId(id)}
          />
        )}
      </div>

      {/* Recently Cleared Section */}
      <RecentlyClearedSection onViewDetails={handleViewClearDetails} />

      {/* Create Appointment Dialog */}
      <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
        <DialogContent className="max-w-lg" aria-describedby="create-appointment-description">
          <DialogHeader>
            <DialogTitle>
              {selectedDate
                ? `Schedule Appointment for ${format(selectedDate, 'MMMM d, yyyy')}`
                : 'Schedule New Appointment'}
            </DialogTitle>
            <p id="create-appointment-description" className="text-sm text-muted-foreground">
              Fill in the details below to schedule a new appointment.
            </p>
          </DialogHeader>
          <AppointmentForm
            initialDate={selectedDate ?? undefined}
            onSuccess={handleCreateSuccess}
            onCancel={() => {
              setShowCreateDialog(false);
              setSelectedDate(null);
            }}
          />
        </DialogContent>
      </Dialog>

      {/* Appointment Detail Dialog */}
      <Dialog
        open={!!selectedAppointmentId}
        onOpenChange={() => handleCloseDetail()}
      >
        <DialogContent className="max-w-2xl" aria-describedby="appointment-detail-description">
          <DialogHeader>
            <DialogTitle>Appointment Details</DialogTitle>
            <p id="appointment-detail-description" className="text-sm text-muted-foreground">
              View and manage appointment information.
            </p>
          </DialogHeader>
          {selectedAppointmentId && (
            <AppointmentDetail
              appointmentId={selectedAppointmentId}
              onClose={handleCloseDetail}
            />
          )}
        </DialogContent>
      </Dialog>

      {/* Clear Day Dialog */}
      <ClearDayDialog
        open={showClearDayDialog}
        onOpenChange={setShowClearDayDialog}
        date={clearDayDate}
        appointmentCount={appointmentCount}
        affectedJobs={affectedJobs}
        onConfirm={handleClearDayConfirm}
        isLoading={clearScheduleMutation.isPending}
      />
    </div>
  );
}
