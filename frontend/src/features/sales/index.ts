// Components
export { SalesDashboard } from './components';
export { SalesPipeline } from './components';
export { SalesCalendar } from './components';
export { StatusActionButton } from './components';
export { EstimateBuilder } from './components';
export { MediaLibrary } from './components';
export { DiagramBuilder } from './components';
export { FollowUpQueue } from './components';
export { EstimateDetail } from './components';
export { EstimateList } from './components';
export { SalesDetail } from './components';
export { ScheduleVisitModal } from './components/ScheduleVisitModal';
export { DocumentsSection } from './components';

// Hooks
export {
  salesKeys,
  useSalesMetrics,
  useEstimates,
  useEstimateTemplates,
  useCreateEstimate,
  useSendEstimate,
  useMedia,
  useUploadMedia,
  useFollowUps,
  useEstimateDetail,
  useCancelEstimate,
  useCreateJobFromEstimate,
} from './hooks';

export {
  pipelineKeys,
  useSalesPipeline,
  useSalesEntry,
  useAdvanceSalesEntry,
  useOverrideSalesStatus,
  useMarkSalesLost,
  useTriggerEmailSigning,
  useGetEmbeddedSigningUrl,
  useSalesDocuments,
  useUploadSalesDocument,
  useDownloadSalesDocument,
  useDeleteSalesDocument,
  useSalesCalendarEvents,
  useCreateCalendarEvent,
  useUpdateCalendarEvent,
  useDeleteCalendarEvent,
} from './hooks/useSalesPipeline';

// Types
export type {
  SalesMetrics,
  EstimateListItem,
  EstimateLineItem,
  EstimateTier,
  TierName,
  EstimateCreateRequest,
  MediaItem,
  MediaListParams,
  FollowUpItem,
  EstimateTemplate,
  FunnelStage,
  EstimateStatus,
  ActivityEvent,
  LinkedDocument,
  EstimateDetail as EstimateDetailType,
} from './types';

export { ESTIMATE_STATUS_CONFIG } from './types';

// API
export { salesApi } from './api/salesApi';
export { salesPipelineApi } from './api/salesPipelineApi';
