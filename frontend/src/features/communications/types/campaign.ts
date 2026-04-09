/**
 * Campaign types for the Communications feature.
 *
 * Mirrors backend schemas in src/grins_platform/schemas/campaign.py
 * Validates: Requirements 15.1, 22.6
 */

// --- Enums ---

export type CampaignType = 'email' | 'sms' | 'both';

export type CampaignStatus =
  | 'draft'
  | 'scheduled'
  | 'sending'
  | 'sent'
  | 'cancelled';

/** UI-facing delivery status labels per Requirement 27 */
export type RecipientDeliveryStatus =
  | 'pending'
  | 'sending'
  | 'sent'
  | 'failed'
  | 'cancelled';

// --- Audience Filters (Requirement 13) ---

export interface CustomerAudienceFilter {
  sms_opt_in?: boolean | null;
  ids_include?: string[] | null;
  cities?: string[] | null;
  last_service_between?: [string, string] | null;
  tags_include?: string[] | null;
  lead_source?: string | null;
  is_active?: boolean | null;
  no_appointment_in_days?: number | null;
}

export interface LeadAudienceFilter {
  sms_consent?: boolean | null;
  ids_include?: string[] | null;
  statuses?: string[] | null;
  lead_source?: string | null;
  intake_tag?: string | null;
  action_tags_include?: string[] | null;
  cities?: string[] | null;
  created_between?: [string, string] | null;
}

export interface AdHocRecipientPayload {
  phone: string;
  first_name?: string | null;
  last_name?: string | null;
}

export interface AdHocAudienceFilter {
  csv_upload_id?: string | null;
  /**
   * Parsed CSV recipients embedded directly in the audience. Preferred over
   * csv_upload_id — travels with the draft and doesn't depend on server-side
   * staging.
   */
  recipients?: AdHocRecipientPayload[] | null;
  staff_attestation_confirmed: boolean;
  attestation_text_shown: string;
  attestation_version: string;
}

export interface TargetAudience {
  customers?: CustomerAudienceFilter | null;
  leads?: LeadAudienceFilter | null;
  ad_hoc?: AdHocAudienceFilter | null;
}

// --- Campaign ---

export interface Campaign {
  id: string;
  name: string;
  campaign_type: CampaignType;
  status: CampaignStatus;
  target_audience: TargetAudience | null;
  subject: string | null;
  body: string;
  scheduled_at: string | null;
  sent_at: string | null;
  created_by: string | null;
  created_at: string;
  updated_at: string;
}

export interface CampaignCreate {
  name: string;
  campaign_type: CampaignType;
  target_audience?: TargetAudience | null;
  subject?: string | null;
  /** Optional at draft-create time; required before send. */
  body?: string;
  scheduled_at?: string | null;
}

export interface CampaignUpdate {
  name?: string;
  target_audience?: TargetAudience | null;
  subject?: string | null;
  body?: string;
  scheduled_at?: string | null;
}

// --- Campaign Recipient ---

export interface CampaignRecipient {
  id: string;
  campaign_id: string;
  customer_id: string | null;
  lead_id: string | null;
  channel: string;
  delivery_status: RecipientDeliveryStatus;
  sent_at: string | null;
  error_message: string | null;
  created_at: string;
}

// --- Campaign Results ---

export interface CampaignSendAccepted {
  campaign_id: string;
  total_recipients: number;
  status: string;
  message: string;
}

export interface CampaignCancelResult {
  campaign_id: string;
  cancelled_recipients: number;
}

export interface CampaignRetryResult {
  campaign_id: string;
  retried_recipients: number;
}

export interface CampaignStats {
  campaign_id: string;
  total: number;
  sent: number;
  delivered: number;
  failed: number;
  bounced: number;
  opted_out: number;
}

// --- Audience Preview ---

export interface AudiencePreviewRecipient {
  phone_masked: string;
  source_type: 'customer' | 'lead' | 'ad_hoc';
  first_name: string | null;
  last_name: string | null;
}

export interface AudiencePreview {
  total: number;
  customers_count: number;
  leads_count: number;
  ad_hoc_count: number;
  matches: AudiencePreviewRecipient[];
}

// --- CSV Upload ---

export interface CsvRejectedRow {
  row_number: number;
  phone_raw: string;
  reason: string;
}

export interface CsvUploadResult {
  upload_id: string;
  total_rows: number;
  matched_customers: number;
  matched_leads: number;
  will_become_ghost_leads: number;
  rejected: number;
  duplicates_collapsed: number;
  rejected_rows: CsvRejectedRow[];
  /** Parsed and normalized recipients — embed in target_audience.ad_hoc.recipients */
  recipients: AdHocRecipientPayload[];
}

// --- Worker Health ---

export interface RateLimitInfo {
  hourly_allowed: number;
  hourly_used: number;
  hourly_remaining: number;
  daily_allowed: number;
  daily_used: number;
  daily_remaining: number;
}

export interface WorkerHealth {
  last_tick_at: string | null;
  last_tick_duration_ms: number | null;
  last_tick_recipients_processed: number | null;
  pending_count: number;
  sending_count: number;
  orphans_recovered_last_hour: number;
  rate_limit: RateLimitInfo;
  status: 'healthy' | 'stale' | 'unknown';
}
