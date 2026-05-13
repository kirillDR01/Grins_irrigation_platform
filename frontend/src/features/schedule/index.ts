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
  useCollectPayment,
  useCreateInvoiceFromAppointment,
  useCreateEstimateFromAppointment,
  useUploadAppointmentPhotos,
  useRequestReview,
  useSendConfirmation,
  useBulkSendConfirmations,
  scheduleGenerationKeys,
  useScheduleCapacity,
  useScheduleStatus,
  useGenerateSchedule,
  usePreviewSchedule,
  rescheduleKeys,
  useRescheduleRequests,
  useResolveRescheduleRequest,
  aiSchedulingKeys,
  useCapacityForecast,
  useBatchGenerate,
  useUtilizationReport,
  useEvaluateSchedule,
  useCriteriaConfig,
} from './hooks';

// Components
export {
  SchedulePage,
  AppointmentList,
  AppointmentDetail,
  AppointmentForm,
  ScheduleGenerationPage,
  ScheduleResults,
  UnassignedJobExplanationCard,
  JobsReadyToSchedulePreview,
  LeadTimeIndicator,
  JobSelector,
  JobPickerPopup,
  InlineCustomerPanel,
  StaffWorkflowButtons,
  PaymentCollector,
  InvoiceCreator,
  EstimateCreator,
  AppointmentNotes,
  ReviewRequest,
  RescheduleRequestsQueue,
  SendConfirmationButton,
  SendDayConfirmationsButton,
  SendAllConfirmationsButton,
  CapacityHeatMap,
  ScheduleOverviewEnhanced,
  BatchScheduleResults,
  AIScheduleView,
} from './components';
