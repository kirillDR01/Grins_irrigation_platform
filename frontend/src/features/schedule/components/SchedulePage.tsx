/**
 * Main schedule page component.
 * Displays calendar view with appointments.
 * Includes clear day feature and recently cleared section.
 */

import { useState, useMemo, useCallback, useEffect } from 'react';
import { format, startOfWeek, isSameDay } from 'date-fns';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useMutation, useQueryClient, useQueries } from '@tanstack/react-query';
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
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Plus, Calendar, List, CalendarPlus, MoreHorizontal } from 'lucide-react';
import { useMediaQuery } from '@/shared/hooks';
import { ResourceTimelineView } from './ResourceTimelineView';
import { AppointmentForm } from './AppointmentForm';
import { AppointmentModal } from './AppointmentModal';
import { AppointmentList } from './AppointmentList';
import { ClearDayButton } from './ClearDayButton';
import { ClearDayDialog } from './ClearDayDialog';
import { RecentlyClearedSection } from './RecentlyClearedSection';
import { RestoreScheduleDialog } from './RestoreScheduleDialog';
import { RescheduleRequestsQueue } from './RescheduleRequestsQueue';
import { NoReplyReviewQueue } from './NoReplyReviewQueue';
import { InboxQueue } from './InboxQueue';
import { DaySelector } from './DaySelector';
import { LeadTimeIndicator } from './LeadTimeIndicator';
import { JobSelector } from './JobSelector';
import { InlineCustomerPanel } from './InlineCustomerPanel';
import { SendAllConfirmationsButton } from './SendAllConfirmationsButton';
import { scheduleGenerationApi } from '../api/scheduleGenerationApi';
import { useDailySchedule, useWeeklySchedule, appointmentKeys } from '../hooks/useAppointments';
import { useStaff } from '@/features/staff/hooks/useStaff';
import { jobApi } from '@/features/jobs/api/jobApi';
import { customerApi } from '@/features/customers/api/customerApi';
import { formatJobType } from '@/features/jobs/types';
import type { ScheduleClearRequest } from '../types';
import type { Appointment } from '../types';

type ViewMode = 'calendar' | 'list';

export function SchedulePage() {
  const [viewMode, setViewMode] = useState<ViewMode>('calendar');
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [selectedAppointmentId, setSelectedAppointmentId] = useState<
    string | null
  >(null);
  const [selectedDate, setSelectedDate] = useState<Date | null>(null);
  const [createDialogDate, setCreateDialogDate] = useState<Date | null>(null);
  const [createDialogStaffId, setCreateDialogStaffId] = useState<string | null>(null);
  const [showClearDayDialog, setShowClearDayDialog] = useState(false);
  const [showRestoreDialog, setShowRestoreDialog] = useState(false);
  const [selectedAuditId, setSelectedAuditId] = useState<string | null>(null);
  const [showJobSelector, setShowJobSelector] = useState(false);
  const [inlinePanelAppointmentId, setInlinePanelAppointmentId] = useState<string | null>(null);
  const [editingAppointment, setEditingAppointment] = useState<Appointment | null>(null);

  const isMobile = useMediaQuery('(max-width: 767px)');

  const navigate = useNavigate();

  // Pre-fill job from query param (Req 11.7 — "Schedule" button on Jobs tab)
  const [searchParams, setSearchParams] = useSearchParams();
  const [preSelectedJobId, setPreSelectedJobId] = useState<string | null>(null);

  // Track the current week displayed in the calendar
  const [currentWeekStart, setCurrentWeekStart] = useState<Date>(() => 
    startOfWeek(new Date(), { weekStartsOn: 1 })
  );

  // Auto-open create dialog when navigated from Jobs tab with scheduleJobId (Req 11.7)
  useEffect(() => {
    const jobId = searchParams.get('scheduleJobId');
    if (jobId) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setPreSelectedJobId(jobId);
      setShowCreateDialog(true);
      // Clean up the URL param so it doesn't re-trigger
      const newParams = new URLSearchParams(searchParams);
      newParams.delete('scheduleJobId');
      setSearchParams(newParams, { replace: true });
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const queryClient = useQueryClient();

  // Fetch appointments for the selected day (for clear day dialog)
  const formattedSelectedDate = selectedDate ? format(selectedDate, 'yyyy-MM-dd') : undefined;
  const { data: dailySchedule } = useDailySchedule(formattedSelectedDate);

  // Fetch weekly schedule for appointment counts in day selector
  const weekEndDate = format(
    new Date(currentWeekStart.getTime() + 6 * 24 * 60 * 60 * 1000),
    'yyyy-MM-dd'
  );
  const { data: weeklySchedule } = useWeeklySchedule(
    format(currentWeekStart, 'yyyy-MM-dd'),
    weekEndDate
  );

  // Fetch staff data for mapping staff_id to staff_name
  const { data: staffData } = useStaff({ page_size: 100 });
  
  // Create staff_id to staff_name mapping
  const staffIdToName = useMemo(() => {
    const mapping: Record<string, string> = {};
    if (staffData?.items) {
      for (const staff of staffData.items) {
        mapping[staff.id] = staff.name;
      }
    }
    return mapping;
  }, [staffData]);

  // Get unique job IDs from daily schedule appointments
  const jobIds = useMemo(() => {
    if (!dailySchedule?.appointments) return [];
    return [...new Set(dailySchedule.appointments.map(apt => apt.job_id))];
  }, [dailySchedule]);

  // Fetch job details for all appointments
  const jobQueries = useQueries({
    queries: jobIds.map(jobId => ({
      queryKey: ['jobs', 'detail', jobId],
      queryFn: () => jobApi.get(jobId),
      enabled: !!jobId,
      staleTime: 5 * 60 * 1000, // Cache for 5 minutes
    })),
  });

  // Create job_id to job mapping
  const jobIdToJob = useMemo(() => {
    const mapping: Record<string, { job_type: string; customer_id: string }> = {};
    jobQueries.forEach((query) => {
      if (query.data) {
        mapping[query.data.id] = {
          job_type: query.data.job_type,
          customer_id: query.data.customer_id,
        };
      }
    });
    return mapping;
  }, [jobQueries]);

  // Get unique customer IDs from jobs
  const customerIds = useMemo(() => {
    const ids = Object.values(jobIdToJob).map(job => job.customer_id);
    return [...new Set(ids)];
  }, [jobIdToJob]);

  // Fetch customer details for all jobs
  const customerQueries = useQueries({
    queries: customerIds.map(customerId => ({
      queryKey: ['customers', 'detail', customerId],
      queryFn: () => customerApi.get(customerId),
      enabled: !!customerId,
      staleTime: 5 * 60 * 1000, // Cache for 5 minutes
    })),
  });

  // Create customer_id to customer name mapping
  const customerIdToName = useMemo(() => {
    const mapping: Record<string, string> = {};
    customerQueries.forEach((query) => {
      if (query.data) {
        mapping[query.data.id] = `${query.data.first_name} ${query.data.last_name}`;
      }
    });
    return mapping;
  }, [customerQueries]);

  // Calculate appointment counts per day for the day selector
  const appointmentCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    if (weeklySchedule?.days) {
      weeklySchedule.days.forEach((day) => {
        const activeAppointments = day.appointments.filter(
          (apt) => apt.status !== 'cancelled'
        );
        counts[day.date] = activeAppointments.length;
      });
    }
    return counts;
  }, [weeklySchedule]);

  // Count DRAFT appointments in the current view (Req 8.7)
  const draftAppointments = useMemo(() => {
    if (!weeklySchedule?.days) return [];
    return weeklySchedule.days.flatMap((day) =>
      day.appointments.filter((apt) => apt.status === 'draft')
    );
  }, [weeklySchedule]);

  const draftCount = draftAppointments.length;

  // Get appointment count and affected jobs for the clear day dialog
  const appointmentCount = dailySchedule?.appointments?.length ?? 0;
  const affectedJobs = useMemo(() => {
    if (!dailySchedule?.appointments) return [];
    return dailySchedule.appointments.map((apt) => {
      // Get job info
      const jobInfo = jobIdToJob[apt.job_id];
      const jobType = jobInfo?.job_type ? formatJobType(jobInfo.job_type) : 'Unknown Service';
      
      // Get customer name
      const customerId = jobInfo?.customer_id;
      const customerName = customerId ? customerIdToName[customerId] : null;
      
      // Get staff name
      const staffName = staffIdToName[apt.staff_id] || 'Unassigned';
      
      // Format time window
      const timeStart = apt.time_window_start.substring(0, 5); // HH:MM
      const timeEnd = apt.time_window_end.substring(0, 5); // HH:MM
      const timeWindow = `${timeStart} - ${timeEnd}`;
      
      return {
        job_id: apt.job_id,
        customer_name: customerName || 'Loading...',
        service_type: `${jobType} • ${staffName} • ${timeWindow}`,
      };
    });
  }, [dailySchedule, jobIdToJob, customerIdToName, staffIdToName]);

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
      // Clear the selected date after successful clear
      setSelectedDate(null);
    },
    onError: (error: Error) => {
      toast.error('Error', {
        description: error.message || 'Failed to clear schedule',
      });
    },
  });

  const handleDateClick = (staffId: string | null, date: Date) => {
    setCreateDialogDate(date);
    setCreateDialogStaffId(staffId);
    setShowCreateDialog(true);
  };

  const handleEventClick = (appointmentId: string) => {
    setSelectedAppointmentId(appointmentId);
  };

  const handleCreateSuccess = () => {
    setShowCreateDialog(false);
    setCreateDialogDate(null);
    setCreateDialogStaffId(null);
    setPreSelectedJobId(null);
  };

  const handleCloseDetail = () => {
    setSelectedAppointmentId(null);
  };

  // Handle day selection from DaySelector (toggle behavior)
  const handleDaySelect = useCallback((date: Date) => {
    setSelectedDate((prev) => {
      // If clicking the same day, deselect it
      if (prev && isSameDay(prev, date)) {
        return null;
      }
      // Otherwise, select the new day
      return date;
    });
  }, []);

  // Handle week change from calendar navigation
  const handleWeekChange = useCallback((weekStart: Date) => {
    setCurrentWeekStart(weekStart);
    // Clear selected date when navigating to a different week
    setSelectedDate(null);
  }, []);

  const handleClearDayClick = () => {
    // Only open dialog if a day is selected
    if (selectedDate) {
      setShowClearDayDialog(true);
    }
  };

  const handleClearDayConfirm = () => {
    if (!selectedDate) return;
    
    clearScheduleMutation.mutate({
      schedule_date: format(selectedDate, 'yyyy-MM-dd'),
      notes: `Cleared via Schedule page on ${format(new Date(), 'yyyy-MM-dd HH:mm')}`,
    });
  };

  const handleViewClearDetails = (auditId: string) => {
    setSelectedAuditId(auditId);
    setShowRestoreDialog(true);
  };

  // Handle inline customer panel open from calendar (Req 27)
  const handleCustomerClick = useCallback((appointmentId: string) => {
    setInlinePanelAppointmentId(appointmentId);
  }, []);

  // Handle edit from AppointmentDetail (Req 18)
  const handleEditAppointment = useCallback((appointment: Appointment) => {
    setSelectedAppointmentId(null); // close detail dialog
    setEditingAppointment(appointment); // open edit dialog
  }, []);

  return (
    <div 
      data-testid="schedule-page" 
      className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500"
    >
      <PageHeader
        title="Schedule"
        description="Manage appointments and view daily/weekly schedules"
        action={
          <div className="flex items-center gap-2 flex-wrap md:gap-3 lg:flex-nowrap lg:gap-4">
            {isMobile ? (
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button
                    variant="outline"
                    size="icon"
                    aria-label="More schedule actions"
                    data-testid="schedule-action-overflow-btn"
                    className="h-11 w-11"
                  >
                    <MoreHorizontal className="h-5 w-5" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent
                  align="end"
                  className="w-56"
                  data-testid="schedule-action-overflow-menu"
                >
                  <DropdownMenuLabel>View</DropdownMenuLabel>
                  <DropdownMenuItem
                    onClick={() => setViewMode('calendar')}
                    data-testid="overflow-menu-item-view-calendar"
                  >
                    <Calendar className="mr-2 h-4 w-4" />
                    Calendar
                    {viewMode === 'calendar' && (
                      <span className="ml-auto text-xs text-teal-600">●</span>
                    )}
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    onClick={() => setViewMode('list')}
                    data-testid="overflow-menu-item-view-list"
                  >
                    <List className="mr-2 h-4 w-4" />
                    List
                    {viewMode === 'list' && (
                      <span className="ml-auto text-xs text-teal-600">●</span>
                    )}
                  </DropdownMenuItem>
                  {(selectedDate || draftCount > 0) && <DropdownMenuSeparator />}
                  {selectedDate && (
                    <>
                      <DropdownMenuLabel>Actions</DropdownMenuLabel>
                      <DropdownMenuItem
                        onClick={handleClearDayClick}
                        disabled={clearScheduleMutation.isPending}
                        data-testid="overflow-menu-item-clear-day"
                      >
                        Clear day
                      </DropdownMenuItem>
                    </>
                  )}
                  {draftCount > 0 && (
                    <DropdownMenuItem
                      asChild
                      data-testid="overflow-menu-item-send-confirmations"
                    >
                      <SendAllConfirmationsButton
                        draftAppointments={draftAppointments}
                      />
                    </DropdownMenuItem>
                  )}
                </DropdownMenuContent>
              </DropdownMenu>
            ) : (
              <>
                <LeadTimeIndicator />
                <ClearDayButton
                  onClick={handleClearDayClick}
                  disabled={clearScheduleMutation.isPending}
                  hasSelectedDay={!!selectedDate}
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
                  onClick={() => {
                    const params = new URLSearchParams();
                    if (selectedDate) params.set('date', format(selectedDate, 'yyyy-MM-dd'));
                    navigate(`/schedule/pick-jobs${params.toString() ? `?${params}` : ''}`);
                  }}
                  variant="outline"
                  data-testid="add-jobs-btn"
                  className="hidden lg:inline-flex border-teal-200 text-teal-600 hover:bg-teal-50"
                >
                  <CalendarPlus className="mr-2 h-4 w-4" />
                  Add Jobs
                </Button>
                <Button
                  onClick={() => navigate('/schedule/pick-jobs')}
                  variant="outline"
                  data-testid="pick-jobs-btn"
                  className="hidden lg:inline-flex border-teal-200 text-teal-600 hover:bg-teal-50"
                >
                  <CalendarPlus className="mr-2 h-4 w-4" />
                  Pick jobs to schedule
                </Button>
                {draftCount > 0 && (
                  <SendAllConfirmationsButton draftAppointments={draftAppointments} />
                )}
              </>
            )}
            <Button
              onClick={() => setShowCreateDialog(true)}
              data-testid="add-appointment-btn"
              className="bg-teal-500 hover:bg-teal-600 text-white"
            >
              <Plus className="mr-2 h-4 w-4" />
              <span className="hidden sm:inline">New Appointment</span>
              <span className="sm:hidden">New</span>
            </Button>
          </div>
        }
      />

      {/* Day Selector for Clear Day feature */}
      {viewMode === 'calendar' && (
        <DaySelector
          weekStart={currentWeekStart}
          selectedDate={selectedDate}
          onSelectDate={handleDaySelect}
          appointmentCounts={appointmentCounts}
        />
      )}

      {/* Main Content */}
      <div className="bg-white rounded-lg border shadow-sm">
        {viewMode === 'calendar' ? (
          <ResourceTimelineView
            onDateClick={handleDateClick}
            onEventClick={handleEventClick}
            onWeekChange={handleWeekChange}
            selectedDate={selectedDate}
            onCustomerClick={handleCustomerClick}
          />
        ) : (
          <AppointmentList
            onAppointmentClick={(id) => setSelectedAppointmentId(id)}
          />
        )}
      </div>

      {/* Reschedule Requests Queue (Req 25) */}
      <RescheduleRequestsQueue
        onAppointmentClick={(id) => setSelectedAppointmentId(id)}
      />

      {/* No-Reply Confirmation Review Queue (bughunt H-7) */}
      <NoReplyReviewQueue
        onAppointmentClick={(id) => setSelectedAppointmentId(id)}
      />

      {/* Recently Cleared Section */}
      <RecentlyClearedSection onViewDetails={handleViewClearDetails} />

      {/* Unified Inbox Queue (scheduling-gaps gap-16 v0) */}
      <InboxQueue
        onAppointmentClick={(id) => setSelectedAppointmentId(id)}
      />

      {/* Create Appointment Dialog */}
      <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
        <DialogContent className="max-w-lg" aria-describedby="create-appointment-description">
          <DialogHeader>
            <DialogTitle>
              {createDialogDate
                ? `Schedule Appointment for ${format(createDialogDate, 'MMMM d, yyyy')}`
                : 'Schedule New Appointment'}
            </DialogTitle>
            <p id="create-appointment-description" className="text-sm text-muted-foreground">
              Fill in the details below to schedule a new appointment.
            </p>
          </DialogHeader>
          <AppointmentForm
            initialDate={createDialogDate ?? undefined}
            initialJobId={preSelectedJobId ?? undefined}
            initialStaffId={createDialogStaffId ?? undefined}
            onSuccess={handleCreateSuccess}
            onCancel={() => {
              setShowCreateDialog(false);
              setCreateDialogDate(null);
              setCreateDialogStaffId(null);
              setPreSelectedJobId(null);
            }}
          />
        </DialogContent>
      </Dialog>

      {/* Appointment Detail Modal */}
      {selectedAppointmentId && (
        <AppointmentModal
          appointmentId={selectedAppointmentId}
          open={!!selectedAppointmentId}
          onClose={handleCloseDetail}
          onEdit={handleEditAppointment}
        />
      )}

      {/* Clear Day Dialog */}
      {selectedDate && (
        <ClearDayDialog
          open={showClearDayDialog}
          onOpenChange={setShowClearDayDialog}
          date={selectedDate}
          appointmentCount={appointmentCount}
          affectedJobs={affectedJobs}
          onConfirm={handleClearDayConfirm}
          isLoading={clearScheduleMutation.isPending}
        />
      )}

      {/* Edit Appointment Dialog (Req 18) */}
      <Dialog
        open={!!editingAppointment}
        onOpenChange={(open) => {
          if (!open) {
            // On cancel, re-open the detail modal
            const apptId = editingAppointment?.id ?? null;
            setEditingAppointment(null);
            if (apptId) {
              setSelectedAppointmentId(apptId);
            }
          }
        }}
      >
        <DialogContent className="max-w-lg" aria-describedby="edit-appointment-description">
          <DialogHeader>
            <DialogTitle>Edit Appointment</DialogTitle>
            <p id="edit-appointment-description" className="text-sm text-muted-foreground">
              Modify the appointment details below.
            </p>
          </DialogHeader>
          {editingAppointment && (
            <AppointmentForm
              appointment={editingAppointment}
              onSuccess={() => {
                setEditingAppointment(null);
                queryClient.invalidateQueries({ queryKey: appointmentKeys.all });
              }}
              onCancel={() => {
                const apptId = editingAppointment.id;
                setEditingAppointment(null);
                setSelectedAppointmentId(apptId);
              }}
            />
          )}
        </DialogContent>
      </Dialog>

      {/* Restore Schedule Dialog */}
      <RestoreScheduleDialog
        open={showRestoreDialog}
        onOpenChange={setShowRestoreDialog}
        auditId={selectedAuditId}
      />

      {/* Legacy Job Selector Modal (Req 26) */}
      <JobSelector
        open={showJobSelector}
        onOpenChange={setShowJobSelector}
        defaultDate={selectedDate ? format(selectedDate, 'yyyy-MM-dd') : undefined}
      />

      {/* Inline Customer Panel (Req 27) */}
      <InlineCustomerPanel
        open={!!inlinePanelAppointmentId}
        onOpenChange={(open) => {
          if (!open) setInlinePanelAppointmentId(null);
        }}
        appointmentId={inlinePanelAppointmentId}
      />
    </div>
  );
}
