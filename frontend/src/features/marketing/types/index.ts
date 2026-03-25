import type { PaginationParams } from '@/core/api';

// Lead source analytics
export interface LeadSourceData {
  source: string;
  count: number;
  conversion_rate: number;
}

export interface FunnelStage {
  stage: string;
  count: number;
  conversion_rate: number;
}

export interface LeadAnalytics {
  lead_sources: LeadSourceData[];
  funnel: FunnelStage[];
  total_leads: number;
  conversion_rate: number;
  avg_time_to_conversion_days: number;
  top_source: string;
  advertising_channels: AdvertisingChannel[];
}

export interface AdvertisingChannel {
  channel: string;
  spend: number;
  lead_count: number;
  cost_per_lead: number;
  is_active: boolean;
}

// Customer acquisition cost
export interface CACBySource {
  source: string;
  total_spend: number;
  converted_customers: number;
  cac: number;
}

// Campaign types
export type CampaignType = 'EMAIL' | 'SMS' | 'BOTH';
export type CampaignStatus = 'DRAFT' | 'SCHEDULED' | 'SENDING' | 'SENT' | 'CANCELLED';
export type RecipientStatus = 'PENDING' | 'SENT' | 'DELIVERED' | 'FAILED' | 'BOUNCED' | 'OPTED_OUT';

export interface Campaign {
  id: string;
  name: string;
  campaign_type: CampaignType;
  status: CampaignStatus;
  subject: string | null;
  body: string;
  target_audience: Record<string, unknown>;
  scheduled_at: string | null;
  sent_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface CampaignCreateRequest {
  name: string;
  campaign_type: CampaignType;
  subject?: string;
  body: string;
  target_audience: Record<string, unknown>;
  scheduled_at?: string;
}

export interface CampaignStats {
  total_recipients: number;
  sent: number;
  delivered: number;
  failed: number;
  bounced: number;
  opted_out: number;
}

export interface CampaignListParams extends PaginationParams {
  status?: CampaignStatus;
}

// Marketing budget
export interface MarketingBudget {
  id: string;
  channel: string;
  budget_amount: number;
  period_start: string;
  period_end: string;
  actual_spend: number;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface MarketingBudgetCreateRequest {
  channel: string;
  budget_amount: number;
  period_start: string;
  period_end: string;
  notes?: string;
}

export interface BudgetListParams extends PaginationParams {
  channel?: string;
}

// QR Code
export interface QRCodeRequest {
  target_url: string;
  campaign_name: string;
}

export interface QRCodeResponse {
  qr_code_url: string;
  target_url_with_utm: string;
  campaign_name: string;
}

// Date range filter
export type DateRangePreset = 'month' | 'quarter' | 'ytd' | 'custom';

export interface DateRangeFilter {
  preset: DateRangePreset;
  start_date?: string;
  end_date?: string;
}
