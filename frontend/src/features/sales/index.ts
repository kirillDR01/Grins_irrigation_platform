// Components
export { SalesDashboard } from './components';
export { EstimateBuilder } from './components';
export { MediaLibrary } from './components';
export { DiagramBuilder } from './components';
export { FollowUpQueue } from './components';
export { EstimateDetail } from './components';
export { EstimateList } from './components';

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
