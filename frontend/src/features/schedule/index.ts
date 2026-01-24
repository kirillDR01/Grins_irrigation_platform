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
  ScheduleGenerateRequest,
  ScheduleGenerateResponse,
  ScheduleJobAssignment,
  ScheduleStaffAssignment,
  UnassignedJobResponse,
  ScheduleCapacityResponse,
  ScheduleGenerationStatusResponse,
  GenerationStatus,
} from './types';

export { appointmentStatusConfig } from './types';

// API
export { appointmentApi } from './api/appointmentApi';
export { scheduleGenerationApi } from './api/scheduleGenerationApi';

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
  scheduleGenerationKeys,
  useScheduleCapacity,
  useScheduleStatus,
  useGenerateSchedule,
  usePreviewSchedule,
} from './hooks';

// Components
export {
  SchedulePage,
  CalendarView,
  AppointmentList,
  AppointmentDetail,
  AppointmentForm,
  ScheduleGenerationPage,
  ScheduleResults,
} from './components';
