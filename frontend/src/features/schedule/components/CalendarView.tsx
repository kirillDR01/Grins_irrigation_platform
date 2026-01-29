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
import type { DateClickArg, EventClickArg } from '@fullcalendar/interaction';
import type { DatesSetArg, EventInput } from '@fullcalendar/core';
import { format, startOfWeek, endOfWeek, addDays } from 'date-fns';
import { useWeeklySchedule } from '../hooks/useAppointments';
import { useStaff } from '@/features/staff/hooks/useStaff';
import { getStaffColor, DEFAULT_COLOR } from '../utils/staffColors';
import { appointmentStatusConfig } from '../types';
import type { Appointment, AppointmentStatus } from '../types';
import { LoadingSpinner } from '@/shared/components/LoadingSpinner';

interface CalendarViewProps {
  onDateClick?: (date: Date) => void;
  onEventClick?: (appointmentId: string) => void;
}

// Map appointment status to calendar event colors (fallback when no staff color)
const statusColors: Record<AppointmentStatus, { bg: string; border: string }> = {
  pending: { bg: '#fef3c7', border: '#f59e0b' },
  scheduled: { bg: '#f3e8ff', border: '#a855f7' },
  confirmed: { bg: '#dbeafe', border: '#3b82f6' },
  in_progress: { bg: '#ffedd5', border: '#f97316' },
  completed: { bg: '#dcfce7', border: '#22c55e' },
  cancelled: { bg: '#fee2e2', border: '#ef4444' },
  no_show: { bg: '#f3f4f6', border: '#6b7280' },
};

// Convert hex color to lighter background version
function hexToLightBg(hex: string): string {
  // Remove # if present
  const cleanHex = hex.replace('#', '');
  const r = parseInt(cleanHex.substring(0, 2), 16);
  const g = parseInt(cleanHex.substring(2, 4), 16);
  const b = parseInt(cleanHex.substring(4, 6), 16);
  // Mix with white for lighter background (30% original, 70% white)
  const lightR = Math.round(r * 0.3 + 255 * 0.7);
  const lightG = Math.round(g * 0.3 + 255 * 0.7);
  const lightB = Math.round(b * 0.3 + 255 * 0.7);
  return `rgb(${lightR}, ${lightG}, ${lightB})`;
}

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

  const { data: weeklySchedule, isLoading: isLoadingSchedule } = useWeeklySchedule(
    dateRange.start,
    dateRange.end
  );

  // Fetch staff list to map staff_id to staff_name for colors
  const { data: staffData, isLoading: isLoadingStaff } = useStaff({ page_size: 100 });

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

    return activeAppointments.map((appointment) => {
      // Get staff name from mapping, then get color
      const staffName = staffIdToName[appointment.staff_id] || '';
      const staffColor = getStaffColor(staffName);
      
      // Use staff color if available, otherwise fall back to status color
      const useStaffColor = staffColor !== DEFAULT_COLOR;
      const colors = useStaffColor 
        ? { bg: hexToLightBg(staffColor), border: staffColor }
        : statusColors[appointment.status];
      
      const statusLabel = appointmentStatusConfig[appointment.status].label;
      const displayTitle = staffName 
        ? `${staffName} - ${statusLabel}`
        : `${statusLabel} - Job`;

      // Parse time strings and combine with date
      const startDateTime = new Date(
        `${appointment.scheduled_date}T${appointment.time_window_start}`
      );
      const endDateTime = new Date(
        `${appointment.scheduled_date}T${appointment.time_window_end}`
      );

      return {
        id: appointment.id,
        title: displayTitle,
        start: startDateTime,
        end: endDateTime,
        backgroundColor: colors.bg,
        borderColor: colors.border,
        textColor: '#1f2937',
        extendedProps: {
          appointment,
          status: appointment.status,
          staffId: appointment.staff_id,
          staffName,
          jobId: appointment.job_id,
        },
      };
    });
  }, [weeklySchedule, staffIdToName]);

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

  if (isLoadingSchedule || isLoadingStaff) {
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
