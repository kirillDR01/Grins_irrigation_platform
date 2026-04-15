// Components
export { CommunicationsDashboard } from './components';
export { CommunicationsQueue } from './components';
export { SentMessagesLog } from './components';
export { AudienceBuilder } from './components';
export { MessageComposer } from './components';
export { NewTextCampaignModal } from './components';
export { CampaignsList } from './components';
export { PollOptionsEditor } from './components';
export { renderPollOptionsBlock } from './utils/pollOptions';
export type { AudienceBuilderProps } from './components/AudienceBuilder';
export type { PollOptionsEditorProps } from './components/PollOptionsEditor';
export type { MessageComposerProps } from './components/MessageComposer';
export type { NewTextCampaignModalProps } from './components/NewTextCampaignModal';

// Utils
export { countSegments, findInvalidMergeFields, renderTemplate, SENDER_PREFIX, STOP_FOOTER, ALLOWED_MERGE_FIELDS } from './utils/segmentCounter';
export type { Encoding } from './utils/segmentCounter';

// Hooks
export {
  communicationsKeys,
  useUnaddressedCommunications,
  useUnaddressedCount,
  useMarkAddressed,
  useSentMessages,
  // Campaign hooks
  campaignKeys,
  useCampaigns,
  useCampaign,
  useCampaignStats,
  useCreateCampaign,
  useDeleteCampaign,
  useSendCampaign,
  useCancelCampaign,
  useAudiencePreview,
  useAudienceCsv,
  useCampaignProgress,
  useWorkerHealth,
  // Campaign response hooks
  campaignResponseKeys,
  useCampaignResponseSummary,
  useCampaignResponses,
} from './hooks';

// Types
export type {
  Communication,
  CommunicationChannel,
  CommunicationDirection,
  SentMessage,
  DeliveryStatus,
  SentMessageListParams,
  UnaddressedCountResponse,
  CampaignType,
  CampaignStatus,
  RecipientDeliveryStatus,
  CustomerAudienceFilter,
  LeadAudienceFilter,
  AdHocAudienceFilter,
  TargetAudience,
  Campaign,
  CampaignCreate,
  CampaignRecipient,
  CampaignSendAccepted,
  CampaignCancelResult,
  CampaignStats,
  AudiencePreviewRecipient,
  AudiencePreview,
  CsvRejectedRow,
  CsvUploadResult,
  RateLimitInfo,
  WorkerHealth,
  PollOption,
  CampaignResponseRow,
  CampaignResponseBucket,
  CampaignResponseSummary,
} from './types';

// API
export { communicationsApi } from './api/communicationsApi';
export { campaignsApi } from './api/campaignsApi';
export type { CampaignResponseListParams } from './hooks';
