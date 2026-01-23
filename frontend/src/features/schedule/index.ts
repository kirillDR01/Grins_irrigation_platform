/**
 * Schedule feature exports.
 */

// Types
export type {
  Appointment,
  AppointmentCreate,
  AppointmentUpdate,
  AppointmentStatus,
  AppointmentListParams,
  AppointmentPaginatedResponse,
  DailyScheduleResponse,
  StaffDailyScheduleResponse,
  WeeklyScheduleResponse,
  CalendarEvent,
} from './types';

export { appointmentStatusConfig } from './types';

// API
export { appointmentApi } from './api/appointmentApi';

// Hooks
export {
  appointmentKeys,
  useAppointments,
  useAppointment,
  useDailySchedule,
  useStaffDailySchedule,
  useWeeklySchedule,
  useJobAppointments,
  useStaffAppointments,
  useCreateAppointment,
  useUpdateAppointment,
  useCancelAppointment,
  useConfirmAppointment,
  useMarkAppointmentArrived,
  useMarkAppointmentCompleted,
  useMarkAppointmentNoShow,
} from './hooks';

// Components
export {
  SchedulePage,
  CalendarView,
  AppointmentList,
  AppointmentDetail,
  AppointmentForm,
} from './components';
