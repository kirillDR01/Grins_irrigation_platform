// Components
export { LeadStatusBadge } from './components/LeadStatusBadge';
export { LeadSituationBadge } from './components/LeadSituationBadge';
export { LeadSourceBadge } from './components/LeadSourceBadge';
export { IntakeTagBadge } from './components/IntakeTagBadge';
export { LeadTagBadges } from './components/LeadTagBadges';
export { FollowUpQueue } from './components/FollowUpQueue';
export { ConvertLeadDialog } from './components/ConvertLeadDialog';
export { CreateLeadDialog } from './components/CreateLeadDialog';
export { LeadFilters } from './components/LeadFilters';
export { LeadsList } from './components/LeadsList';
export { LeadDetail } from './components/LeadDetail';
export { BulkOutreach } from './components/BulkOutreach';
export { AttachmentPanel } from './components/AttachmentPanel';

// Hooks
export {
  useLeads,
  useLead,
  useFollowUpQueue,
  useLeadMetricsBySource,
  useLeadAttachments,
  useEstimateTemplates,
  useContractTemplates,
  leadKeys,
  useUpdateLead,
  useConvertLead,
  useDeleteLead,
  useMoveToJobs,
  useMoveToSales,
  useMarkContacted,
  useCreateFromCall,
  useCreateManualLead,
  useBulkOutreach,
  useUploadAttachment,
  useDeleteAttachment,
  useCreateEstimate,
  useCreateContract,
} from './hooks';

// Types
export type {
  Lead,
  LeadStatus,
  LeadSituation,
  LeadSource,
  IntakeTag,
  ActionTag,
  LeadListParams,
  LeadUpdate,
  LeadConversionRequest,
  LeadConversionResponse,
  LeadMoveResponse,
  PaginatedLeadResponse,
  FollowUpLead,
  PaginatedFollowUpResponse,
  FromCallRequest,
  LeadMetricsBySourceParams,
  LeadMetricsBySourceResponse,
  LeadSourceCount,
  LeadAttachment,
  AttachmentType,
  EstimateTemplate,
  ContractTemplate,
  EstimateLineItem,
  BulkOutreachRequest,
  BulkOutreachResponse,
  CreateEstimateRequest,
  CreateContractRequest,
  ManualLeadCreateRequest,
} from './types';
export {
  LEAD_STATUS_LABELS,
  LEAD_SITUATION_LABELS,
  LEAD_SOURCE_LABELS,
  LEAD_SOURCE_COLORS,
  INTAKE_TAG_LABELS,
  ACTION_TAG_LABELS,
  ACTION_TAG_COLORS,
} from './types';

// API
export { leadApi } from './api/leadApi';
