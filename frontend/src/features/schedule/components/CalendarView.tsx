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
import { SendConfirmationButton } from './SendConfirmationButton';
import { SendDayConfirmationsButton } from './SendDayConfirmationsButton';
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
  draft: { bg: '#f1f5f9', border: '#94a3b8' },
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
    const start = startOfWeek(today, { weekStartsOn: 1 });
    const end = endOfWeek(today, { weekStartsOn: 1 });
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

      // Prepaid indicator for service-agreement-linked jobs (Smoothing Req 7.5)
      const isPrepaid = !!appointment.service_agreement_id;
      const prepaidPrefix = isPrepaid ? '💎 ' : '';

      // Parse time strings and combine with date
      const startDateTime = new Date(
        `${appointment.scheduled_date}T${appointment.time_window_start}`
      );
      const endDateTime = new Date(
        `${appointment.scheduled_date}T${appointment.time_window_end}`
      );

      // Confirmed statuses get solid border; unconfirmed get dashed/muted (Req 22)
      // Draft appointments get dotted border + grayed-out (Req 8.3)
      const isDraft = appointment.status === 'draft';
      const isConfirmed = ['confirmed', 'en_route', 'in_progress', 'completed'].includes(appointment.status);
      const confirmationClass = isDraft
        ? 'appointment-draft'
        : isConfirmed
          ? 'appointment-confirmed'
          : 'appointment-unconfirmed';
      const classNames = isOnSelectedDate
        ? ['selected-day-event', confirmationClass]
        : isPrepaid
          ? [confirmationClass, 'appointment-prepaid']
          : [confirmationClass];

      return {
        id: appointment.id,
        title: isOnSelectedDate ? `⚠️ ${displayTitle}` : `${prepaidPrefix}${displayTitle}`,
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
          isPrepaid,
        },
      };
    });
  }, [weeklySchedule, staffIdToName, selectedDate]);

  // Build draft appointments per day for day header buttons (Req 8.5)
  const draftsByDay = useMemo(() => {
    if (!weeklySchedule?.days) return {};
    const map: Record<string, Appointment[]> = {};
    weeklySchedule.days.forEach((day) => {
      const drafts = day.appointments.filter((apt) => apt.status === 'draft');
      if (drafts.length > 0) {
        map[day.date] = drafts;
      }
    });
    return map;
  }, [weeklySchedule]);

  // Custom event content renderer to show send confirmation button on draft events (Req 8.4)
  // Also shows prepaid badge on service-agreement-linked appointments (Req 17.5)
  // Also shows attachment count badge (Req 10.10)
  const renderEventContent = useCallback(
    (eventInfo: { event: { id: string; title: string; extendedProps: Record<string, unknown> }; timeText: string }) => {
      const appointment = eventInfo.event.extendedProps.appointment as Appointment | undefined;
      const isDraft = eventInfo.event.extendedProps.status === 'draft';
      const isPrepaid = eventInfo.event.extendedProps.isPrepaid === true;
      const attachmentCount = (eventInfo.event.extendedProps.attachment_count as number) ?? 0;
      return (
        <div className="flex items-center gap-1 w-full overflow-hidden">
          <div className="flex-1 truncate">
            <span className="text-[10px] text-slate-500">{eventInfo.timeText}</span>
            {isPrepaid && (
              <span
                className="ml-1 inline-flex items-center rounded px-1 py-0.5 text-[9px] font-bold leading-none bg-emerald-100 text-emerald-700 border border-emerald-300"
                data-testid={`prepaid-indicator-${eventInfo.event.id}`}
                title="Covered by service agreement — no payment needed"
              >
                PREPAID
              </span>
            )}
            {attachmentCount > 0 && (
              <span
                className="ml-1 inline-flex items-center rounded px-1 py-0.5 text-[9px] font-bold leading-none bg-blue-100 text-blue-700 border border-blue-200"
                data-testid={`attachment-badge-${eventInfo.event.id}`}
                title={`${attachmentCount} attachment${attachmentCount > 1 ? 's' : ''}`}
              >
                📎{attachmentCount}
              </span>
            )}
            <span className="ml-1 truncate">{eventInfo.event.title}</span>
          </div>
          {isDraft && appointment && (
            <SendConfirmationButton
              appointment={appointment}
              compact
            />
          )}
        </div>
      );
    },
    []
  );

  // Custom day header content to show send day confirmations button (Req 8.5)
  const renderDayHeaderContent = useCallback(
    (headerInfo: { date: Date; text: string }) => {
      const dateStr = format(headerInfo.date, 'yyyy-MM-dd');
      const dayDrafts = draftsByDay[dateStr];
      return (
        <div className="flex items-center gap-1.5 justify-center">
          <span>{headerInfo.text}</span>
          {dayDrafts && (
            <SendDayConfirmationsButton
              date={dateStr}
              draftAppointments={dayDrafts}
            />
          )}
        </div>
      );
    },
    [draftsByDay]
  );

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
      const weekStart = startOfWeek(arg.start, { weekStartsOn: 1 });
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
        firstDay={1}
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
        eventContent={renderEventContent}
        dayHeaderContent={renderDayHeaderContent}
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
