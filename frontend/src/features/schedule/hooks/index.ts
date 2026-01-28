/**
 * Schedule/Appointment hooks exports.
 */

export {
  appointmentKeys,
  useAppointments,
  useAppointment,
  useDailySchedule,
  useStaffDailySchedule,
  useWeeklySchedule,
  useJobAppointments,
  useStaffAppointments,
} from './useAppointments';

export {
  useCreateAppointment,
  useUpdateAppointment,
  useCancelAppointment,
  useConfirmAppointment,
  useMarkAppointmentArrived,
  useMarkAppointmentCompleted,
  useMarkAppointmentNoShow,
} from './useAppointmentMutations';

export {
  scheduleGenerationKeys,
  useScheduleCapacity,
  useScheduleStatus,
  useGenerateSchedule,
  usePreviewSchedule,
} from './useScheduleGeneration';

export { useScheduleExplanation } from './useScheduleExplanation';
export { useUnassignedJobExplanation } from './useUnassignedJobExplanation';
export { useConstraintParser } from './useConstraintParser';
export { useJobsReadyToSchedule } from './useJobsReadyToSchedule';
