/**
 * Calendar view component using FullCalendar.
 * Displays appointments in day/week/month views.
 */

import { useCallback, useMemo, useState } from 'react';
import FullCalendar from '@fullcalendar/react';
import dayGridPlugin from '@fullcalendar/daygrid';
import timeGridPlugin from '@fullcalendar/timegrid';
import interactionPlugin from '@fullcalendar/interaction';
import type { DateClickArg, EventClickArg } from '@fullcalendar/interaction';
import type { DatesSetArg, EventInput } from '@fullcalendar/core';
import { format, startOfWeek, endOfWeek, addDays } from 'date-fns';
import { useWeeklySchedule } from '../hooks/useAppointments';
import { appointmentStatusConfig } from '../types';
import type { Appointment, AppointmentStatus } from '../types';
import { LoadingSpinner } from '@/shared/components/LoadingSpinner';

interface CalendarViewProps {
  onDateClick?: (date: Date) => void;
  onEventClick?: (appointmentId: string) => void;
}

// Map appointment status to calendar event colors
const statusColors: Record<AppointmentStatus, { bg: string; border: string }> = {
  pending: { bg: '#fef3c7', border: '#f59e0b' },
  confirmed: { bg: '#dbeafe', border: '#3b82f6' },
  in_progress: { bg: '#ffedd5', border: '#f97316' },
  completed: { bg: '#dcfce7', border: '#22c55e' },
  cancelled: { bg: '#fee2e2', border: '#ef4444' },
  no_show: { bg: '#f3f4f6', border: '#6b7280' },
};

export function CalendarView({ onDateClick, onEventClick }: CalendarViewProps) {
  const [dateRange, setDateRange] = useState(() => {
    const today = new Date();
    const start = startOfWeek(today, { weekStartsOn: 0 });
    const end = endOfWeek(today, { weekStartsOn: 0 });
    return {
      start: format(start, 'yyyy-MM-dd'),
      end: format(addDays(end, 7), 'yyyy-MM-dd'), // Add extra week for buffer
    };
  });

  const { data: weeklySchedule, isLoading } = useWeeklySchedule(
    dateRange.start,
    dateRange.end
  );

  // Convert appointments to FullCalendar events
  const events: EventInput[] = useMemo(() => {
    if (!weeklySchedule?.days) return [];

    const allAppointments: Appointment[] = [];
    weeklySchedule.days.forEach((day) => {
      allAppointments.push(...day.appointments);
    });

    return allAppointments.map((appointment) => {
      const colors = statusColors[appointment.status];
      const statusLabel = appointmentStatusConfig[appointment.status].label;

      // Parse time strings and combine with date
      const startDateTime = new Date(
        `${appointment.scheduled_date}T${appointment.time_window_start}`
      );
      const endDateTime = new Date(
        `${appointment.scheduled_date}T${appointment.time_window_end}`
      );

      return {
        id: appointment.id,
        title: `${statusLabel} - Job`,
        start: startDateTime,
        end: endDateTime,
        backgroundColor: colors.bg,
        borderColor: colors.border,
        textColor: '#1f2937',
        extendedProps: {
          appointment,
          status: appointment.status,
          staffId: appointment.staff_id,
          jobId: appointment.job_id,
        },
      };
    });
  }, [weeklySchedule]);

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

  const handleDatesSet = useCallback((arg: DatesSetArg) => {
    setDateRange({
      start: format(arg.start, 'yyyy-MM-dd'),
      end: format(arg.end, 'yyyy-MM-dd'),
    });
  }, []);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <LoadingSpinner />
      </div>
    );
  }

  return (
    <div data-testid="calendar-view" className="p-4">
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
        datesSet={handleDatesSet}
        editable={false}
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
