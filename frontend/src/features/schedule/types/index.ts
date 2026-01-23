/**
 * Schedule/Appointment types for the frontend.
 * Maps to backend appointment schemas.
 */

export type AppointmentStatus =
  | 'pending'
  | 'confirmed'
  | 'in_progress'
  | 'completed'
  | 'cancelled'
  | 'no_show';

export interface Appointment {
  id: string;
  job_id: string;
  staff_id: string;
  scheduled_date: string; // ISO date string (YYYY-MM-DD)
  time_window_start: string; // Time string (HH:MM:SS)
  time_window_end: string; // Time string (HH:MM:SS)
  status: AppointmentStatus;
  arrived_at: string | null;
  completed_at: string | null;
  notes: string | null;
  route_order: number | null;
  estimated_arrival: string | null;
  created_at: string;
  updated_at: string;
}

export interface AppointmentCreate {
  job_id: string;
  staff_id: string;
  scheduled_date: string;
  time_window_start: string;
  time_window_end: string;
  notes?: string;
}

export interface AppointmentUpdate {
  staff_id?: string;
  scheduled_date?: string;
  time_window_start?: string;
  time_window_end?: string;
  notes?: string;
  status?: AppointmentStatus;
  route_order?: number;
  estimated_arrival?: string;
}

export interface AppointmentListParams {
  page?: number;
  page_size?: number;
  status?: AppointmentStatus;
  staff_id?: string;
  job_id?: string;
  date_from?: string;
  date_to?: string;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

export interface AppointmentPaginatedResponse {
  items: Appointment[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface DailyScheduleResponse {
  date: string;
  appointments: Appointment[];
  total_count: number;
}

export interface StaffDailyScheduleResponse {
  staff_id: string;
  staff_name: string;
  date: string;
  appointments: Appointment[];
  total_scheduled_minutes: number;
}

export interface WeeklyScheduleResponse {
  start_date: string;
  end_date: string;
  days: DailyScheduleResponse[];
  total_appointments: number;
}

// Calendar event type for FullCalendar integration
export interface CalendarEvent {
  id: string;
  title: string;
  start: Date;
  end: Date;
  backgroundColor?: string;
  borderColor?: string;
  textColor?: string;
  extendedProps: {
    appointment: Appointment;
    status: AppointmentStatus;
    staffId: string;
    jobId: string;
  };
}

// Status display configuration
export const appointmentStatusConfig: Record<
  AppointmentStatus,
  { label: string; color: string; bgColor: string }
> = {
  pending: {
    label: 'Pending',
    color: 'text-yellow-800',
    bgColor: 'bg-yellow-100',
  },
  confirmed: {
    label: 'Confirmed',
    color: 'text-blue-800',
    bgColor: 'bg-blue-100',
  },
  in_progress: {
    label: 'In Progress',
    color: 'text-orange-800',
    bgColor: 'bg-orange-100',
  },
  completed: {
    label: 'Completed',
    color: 'text-green-800',
    bgColor: 'bg-green-100',
  },
  cancelled: {
    label: 'Cancelled',
    color: 'text-red-800',
    bgColor: 'bg-red-100',
  },
  no_show: {
    label: 'No Show',
    color: 'text-gray-800',
    bgColor: 'bg-gray-100',
  },
};
