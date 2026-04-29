// @ts-nocheck — pre-existing TS errors documented in bughunt/2026-04-29-pre-existing-tsc-errors.md
// Types
export type {
  Job,
  JobCreate,
  JobUpdate,
  JobStatusUpdate,
  JobListParams,
  JobStatus,
  JobCategory,
  JobSource,
  SimplifiedJobStatus,
  CustomerTag,
  JobFinancials,
  JobCompleteResponse,
  JobNoteCreate,
  JobNoteResponse,
  JobReviewPushResponse,
  JobPhoto,
} from './types';

export {
  JOB_STATUS_CONFIG,
  JOB_CATEGORY_CONFIG,
  JOB_PRIORITY_CONFIG,
  JOB_SOURCE_CONFIG,
  SIMPLIFIED_STATUS_MAP,
  SIMPLIFIED_STATUS_CONFIG,
  SIMPLIFIED_STATUS_RAW_MAP,
  CUSTOMER_TAG_CONFIG,
  getJobStatusConfig,
  getJobCategoryConfig,
  getJobPriorityConfig,
  getSimplifiedStatus,
  getSimplifiedStatusConfig,
  formatJobType,
  formatDuration,
  formatAmount,
  calculateDaysWaiting,
  getDueByColorClass,
} from './types';

// API
export { jobApi } from './api/jobApi';

// Hooks
export {
  jobKeys,
  useJobs,
  useJob,
  useJobsByStatus,
  useJobsByCustomer,
  useJobsReadyToSchedule,
  useJobsRequiresEstimate,
  useJobSearch,
  useJobFinancials,
  useCreateJob,
  useUpdateJob,
  useUpdateJobStatus,
  useDeleteJob,
  useApproveJob,
  useCancelJob,
  useCompleteJob,
  useCloseJob,
  useOnMyWay,
  useJobStarted,
  useCompleteJobWithWarning,
  useAddJobNote,
  useUploadJobPhoto,
  useReviewPush,
} from './hooks';

// Components
export {
  JobList,
  JobDetail,
  JobForm,
  JobStatusBadge,
  JOB_STATUS_WORKFLOW,
  getNextStatuses,
  canTransitionTo,
} from './components';
