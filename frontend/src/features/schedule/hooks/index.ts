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
  useCollectPayment,
  useCreateInvoiceFromAppointment,
  useCreateEstimateFromAppointment,
  useUploadAppointmentPhotos,
  useRequestReview,
  useSendConfirmation,
  useBulkSendConfirmations,
  useRescheduleFromRequest,
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
export {
  rescheduleKeys,
  useRescheduleRequests,
  useResolveRescheduleRequest,
} from './useRescheduleRequests';

export { useAppointmentTimeline } from './useAppointmentTimeline';

export {
  aiSchedulingKeys,
  useCapacityForecast,
  useBatchGenerate,
  useUtilizationReport,
  useEvaluateSchedule,
  useCriteriaConfig,
} from './useAIScheduling';
export type {
  CriterionResult,
  ScheduleEvaluation,
  CapacityForecastExtended,
  BatchScheduleRequest,
  BatchScheduleResponse,
  UtilizationReport,
  CriteriaConfig,
} from './useAIScheduling';

export {
  appointmentNoteKeys,
  useAppointmentNotes,
  useSaveAppointmentNotes,
} from './useAppointmentNotes';
export type { AppointmentNotesResponse } from './useAppointmentNotes';
