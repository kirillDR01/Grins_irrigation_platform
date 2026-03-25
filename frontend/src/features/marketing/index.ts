// Components
export { MarketingDashboard } from './components';
export { CampaignManager } from './components';
export { BudgetTracker } from './components';
export { QRCodeGenerator } from './components';
export { CACChart } from './components';
export { ConversionFunnel } from './components';

// Hooks
export {
  marketingKeys,
  useLeadAnalytics,
  useCAC,
  useCampaigns,
  useCampaignStats,
  useCreateCampaign,
  useUpdateCampaign,
  useDeleteCampaign,
  useSendCampaign,
  useBudgets,
  useCreateBudget,
  useUpdateBudget,
  useDeleteBudget,
  useGenerateQRCode,
} from './hooks';

// Types
export type {
  LeadSourceData,
  FunnelStage,
  LeadAnalytics,
  AdvertisingChannel,
  CACBySource,
  CampaignType,
  CampaignStatus,
  RecipientStatus,
  Campaign,
  CampaignCreateRequest,
  CampaignStats,
  CampaignListParams,
  MarketingBudget,
  MarketingBudgetCreateRequest,
  BudgetListParams,
  QRCodeRequest,
  QRCodeResponse,
  DateRangePreset,
  DateRangeFilter,
} from './types';

// API
export { marketingApi } from './api/marketingApi';
