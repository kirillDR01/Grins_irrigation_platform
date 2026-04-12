/**
 * Calendar view component using FullCalendar.
 * Displays appointments in day/week/month views.
 * Color-coded by staff member for easy identification.
 */

import { useCallback, useMemo, useState } from 'react';
import FullCalendar from '@fullcalendar/react';
import dayGridPlugin from '@fullcalendar/daygrid';
import timeGridPlugin from '@fullcalendar/timegrid';
import interactionPlugin from '@fullcalendar/interaction';
import type { DateClickArg, EventDropArg } from '@fullcalendar/interaction';
import type { DatesSetArg, EventInput, EventClickArg } from '@fullcalendar/core';
import { format, startOfWeek, endOfWeek, addDays } from 'date-fns';
import { toast } from 'sonner';
import { useWeeklySchedule } from '../hooks/useAppointments';
import { useUpdateAppointment } from '../hooks/useAppointmentMutations';
import { useStaff } from '@/features/staff/hooks/useStaff';
import { appointmentStatusConfig } from '../types';
import type { Appointment, AppointmentStatus } from '../types';
import { LoadingSpinner } from '@/shared/components/LoadingSpinner';
import './CalendarView.css';

interface CalendarViewProps {
  onDateClick?: (date: Date) => void;
  onEventClick?: (appointmentId: string) => void;
  /** Callback when the visible week changes */
  onWeekChange?: (weekStart: Date) => void;
  /** Currently selected date for highlighting */
  selectedDate?: Date | null;
  /** Callback when a customer name is clicked for inline panel */
  onCustomerClick?: (appointmentId: string) => void;
}

// Map appointment status to calendar event colors (Req 24, 28)

/**
 * Format a calendar event label as "{Staff Name} - {Job Type}" (Req 28).
 * Handles null/empty staff names and job types gracefully.
 */
export function formatCalendarEventLabel(
  staffName: string | null | undefined,
  jobType: string | null | undefined,
): string {
  const name = staffName || '';
  const type = jobType || 'Job';
  return name ? `${name} - ${type}` : type;
}

const statusColors: Record<AppointmentStatus, { bg: string; border: string }> = {
  pending: { bg: '#fef3c7', border: '#f59e0b' },
  scheduled: { bg: '#f3e8ff', border: '#a855f7' },
  confirmed: { bg: '#dbeafe', border: '#3b82f6' },
  in_progress: { bg: '#ffedd5', border: '#f97316' },
  completed: { bg: '#dcfce7', border: '#22c55e' },
  cancelled: { bg: '#fee2e2', border: '#ef4444' },
  no_show: { bg: '#f3f4f6', border: '#6b7280' },
};

export function CalendarView({ onDateClick, onEventClick, onWeekChange, selectedDate, onCustomerClick }: CalendarViewProps) {
  const [dateRange, setDateRange] = useState(() => {
    const today = new Date();
    const start = startOfWeek(today, { weekStartsOn: 0 });
    const end = endOfWeek(today, { weekStartsOn: 0 });
    return {
      start: format(start, 'yyyy-MM-dd'),
      end: format(addDays(end, 7), 'yyyy-MM-dd'), // Add extra week for buffer
    };
  });

  const { data: weeklySchedule, isLoading: isLoadingSchedule } = useWeeklySchedule(
    dateRange.start,
    dateRange.end
  );

  // Fetch staff list to map staff_id to staff_name for colors
  const { data: staffData, isLoading: isLoadingStaff } = useStaff({ page_size: 100 });

  // Mutation for drag-drop rescheduling (Req 24)
  const updateAppointment = useUpdateAppointment();

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

  // Convert appointments to FullCalendar events
  const events: EventInput[] = useMemo(() => {
    if (!weeklySchedule?.days) return [];

    const allAppointments: Appointment[] = [];
    weeklySchedule.days.forEach((day) => {
      allAppointments.push(...day.appointments);
    });

    // Filter out cancelled appointments
    const activeAppointments = allAppointments.filter(
      (appointment) => appointment.status !== 'cancelled'
    );

    // Format selected date for comparison
    const selectedDateStr = selectedDate ? format(selectedDate, 'yyyy-MM-dd') : null;

    return activeAppointments.map((appointment) => {
      // Get staff name from mapping
      const staffName = staffIdToName[appointment.staff_id] || '';
      
      // Check if this event is on the selected date
      const isOnSelectedDate = selectedDateStr === appointment.scheduled_date;
      
      // Use status-based colors (Req 24, 28: confirmed=blue, in_progress=orange, completed=green)
      let colors = statusColors[appointment.status];
      
      // If on selected date, use red highlight to indicate "will be cleared"
      if (isOnSelectedDate) {
        colors = { bg: '#fee2e2', border: '#ef4444' }; // Red highlight
      }
      
      // Event label: "{Staff Name} - {Job Type}" (Req 28)
      const displayTitle = formatCalendarEventLabel(staffName, appointment.job_type);

      // Parse time strings and combine with date
      const startDateTime = new Date(
        `${appointment.scheduled_date}T${appointment.time_window_start}`
      );
      const endDateTime = new Date(
        `${appointment.scheduled_date}T${appointment.time_window_end}`
      );

      // Confirmed statuses get solid border; unconfirmed get dashed/muted (Req 22)
      const isConfirmed = ['confirmed', 'en_route', 'in_progress', 'completed'].includes(appointment.status);
      const confirmationClass = isConfirmed ? 'appointment-confirmed' : 'appointment-unconfirmed';
      const classNames = isOnSelectedDate
        ? ['selected-day-event', confirmationClass]
        : [confirmationClass];

      return {
        id: appointment.id,
        title: isOnSelectedDate ? `⚠️ ${displayTitle}` : displayTitle,
        start: startDateTime,
        end: endDateTime,
        backgroundColor: colors.bg,
        borderColor: colors.border,
        textColor: '#1f2937',
        classNames,
        extendedProps: {
          appointment,
          status: appointment.status,
          staffId: appointment.staff_id,
          staffName,
          jobId: appointment.job_id,
          isOnSelectedDate,
        },
      };
    });
  }, [weeklySchedule, staffIdToName, selectedDate]);

  const handleDateClick = useCallback(
    (arg: DateClickArg) => {
      onDateClick?.(arg.date);
    },
    [onDateClick]
  );

  const handleEventClick = useCallback(
    (arg: EventClickArg) => {
      const appointmentId = arg.event.id;
      onEventClick?.(appointmentId);
    },
    [onEventClick]
  );

  // Handle drag-and-drop rescheduling (Req 24)
  const handleEventDrop = useCallback(
    async (arg: EventDropArg) => {
      const appointmentId = arg.event.id;
      const newStart = arg.event.start;
      const newEnd = arg.event.end;

      if (!newStart) {
        arg.revert();
        return;
      }

      const newDate = format(newStart, 'yyyy-MM-dd');
      const newStartTime = format(newStart, 'HH:mm:ss');
      const newEndTime = newEnd ? format(newEnd, 'HH:mm:ss') : undefined;

      try {
        await updateAppointment.mutateAsync({
          id: appointmentId,
          data: {
            scheduled_date: newDate,
            time_window_start: newStartTime,
            ...(newEndTime ? { time_window_end: newEndTime } : {}),
          },
        });
        toast.success('Appointment rescheduled');
      } catch (error: unknown) {
        arg.revert();
        const message = error instanceof Error ? error.message : 'Failed to reschedule';
        const is409 = typeof error === 'object' && error !== null && 'response' in error &&
          (error as { response?: { status?: number } }).response?.status === 409;
        toast.error(is409 ? 'Scheduling conflict' : 'Reschedule failed', {
          description: message,
        });
      }
    },
    [updateAppointment]
  );

  const handleDatesSet = useCallback((arg: DatesSetArg) => {
    setDateRange({
      start: format(arg.start, 'yyyy-MM-dd'),
      end: format(arg.end, 'yyyy-MM-dd'),
    });
    // Notify parent of week change
    if (onWeekChange) {
      const weekStart = startOfWeek(arg.start, { weekStartsOn: 0 });
      onWeekChange(weekStart);
    }
  }, [onWeekChange]);

  if (isLoadingSchedule || isLoadingStaff) {
    return (
      <div className="flex items-center justify-center h-96">
        <LoadingSpinner />
      </div>
    );
  }

  return (
    <div 
      data-testid="calendar-view" 
      className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden"
    >
      <FullCalendar
        plugins={[dayGridPlugin, timeGridPlugin, interactionPlugin]}
        initialView="timeGridWeek"
        headerToolbar={{
          left: 'prev,next today',
          center: 'title',
          right: 'dayGridMonth,timeGridWeek,timeGridDay',
        }}
        events={events}
        dateClick={handleDateClick}
        eventClick={handleEventClick}
        eventDrop={handleEventDrop}
        datesSet={handleDatesSet}
        editable={true}
        selectable={true}
        selectMirror={true}
        dayMaxEvents={true}
        weekends={true}
        slotMinTime="06:00:00"
        slotMaxTime="20:00:00"
        slotDuration="00:30:00"
        allDaySlot={false}
        height="auto"
        eventDisplay="block"
        eventTimeFormat={{
          hour: 'numeric',
          minute: '2-digit',
          meridiem: 'short',
        }}
        slotLabelFormat={{
          hour: 'numeric',
          minute: '2-digit',
          meridiem: 'short',
        }}
      />
    </div>
  );
}
