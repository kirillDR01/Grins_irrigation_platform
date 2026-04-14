import type { BaseEntity, PaginationParams } from '@/core/api';

// Lead status enum values
export type LeadStatus = 'new' | 'contacted' | 'qualified' | 'converted' | 'lost' | 'spam';

// Lead situation enum values
export type LeadSituation = 'new_system' | 'upgrade' | 'repair' | 'exploring';

// Lead source channels (extended)
export type LeadSource =
  | 'website'
  | 'google_form'
  | 'phone_call'
  | 'text_message'
  | 'google_ad'
  | 'social_media'
  | 'qr_code'
  | 'email_campaign'
  | 'text_campaign'
  | 'referral'
  | 'other';

// Intake tag for routing
export type IntakeTag = 'schedule' | 'follow_up';

// Action tags for lead pipeline (Req 13)
export type ActionTag =
  | 'NEEDS_CONTACT'
  | 'NEEDS_ESTIMATE'
  | 'ESTIMATE_PENDING'
  | 'ESTIMATE_APPROVED'
  | 'ESTIMATE_REJECTED';

// Lead entity
export interface Lead extends BaseEntity {
  name: string;
  phone: string;
  email: string | null;
  address: string | null;
  city: string | null;
  state: string | null;
  zip_code: string | null;
  situation: LeadSituation;
  notes: string | null;
  source_site: string;
  status: LeadStatus;
  assigned_to: string | null;
  customer_id: string | null;
  contacted_at: string | null;
  converted_at: string | null;
  lead_source: LeadSource;
  source_detail: string | null;
  intake_tag: IntakeTag | null;
  action_tags: ActionTag[];
  sms_consent: boolean;
  terms_accepted: boolean;
  email_marketing_consent: boolean;
  job_requested: string | null;
  last_contacted_at: string | null;
}

// Lead move response (CRM2 Req 12.1, 12.2, Smoothing Req 6.1)
export interface LeadMoveResponse {
  success: boolean;
  lead_id: string;
  customer_id: string | null;
  job_id: string | null;
  sales_entry_id: string | null;
  message: string;
  requires_estimate_warning: boolean;
}

// Lead attachment (Req 15)
export type AttachmentType = 'ESTIMATE' | 'CONTRACT' | 'OTHER';

export interface LeadAttachment {
  id: string;
  lead_id: string;
  file_key: string;
  file_name: string;
  file_size: number;
  content_type: string;
  attachment_type: AttachmentType;
  download_url?: string;
  created_at: string;
}

// Estimate template (Req 17)
export interface EstimateLineItem {
  item: string;
  description: string;
  unit_price: number;
  quantity: number;
}

export interface EstimateTemplate {
  id: string;
  name: string;
  description: string | null;
  line_items: EstimateLineItem[];
  terms: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

// Contract template (Req 17)
export interface ContractTemplate {
  id: string;
  name: string;
  body: string;
  terms_and_conditions: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

// Estimate creation request
export interface CreateEstimateRequest {
  lead_id: string;
  template_id?: string;
  line_items: EstimateLineItem[];
  notes?: string;
  valid_until?: string;
}

// Contract creation request
export interface CreateContractRequest {
  lead_id: string;
  template_id?: string;
  body: string;
  terms_and_conditions?: string;
}

// Bulk outreach (Req 14)
export interface BulkOutreachRequest {
  lead_ids: string[];
  message_template: string;
  channel?: 'sms' | 'email';
}

export interface BulkOutreachResponse {
  sent_count: number;
  skipped_count: number;
  failed_count: number;
}

// Lead list query params
export interface LeadListParams extends PaginationParams {
  status?: LeadStatus;
  situation?: LeadSituation;
  search?: string;
  date_from?: string;
  date_to?: string;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
  lead_source?: string;
  intake_tag?: string;
  action_tag?: ActionTag;
  sms_consent?: boolean;
}

// Paginated lead response
export interface PaginatedLeadResponse {
  items: Lead[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// Lead update request
export interface LeadUpdate {
  status?: LeadStatus;
  assigned_to?: string | null;
  notes?: string;
  intake_tag?: IntakeTag | null;
  address?: string | null;
  city?: string | null;
  state?: string | null;
  zip_code?: string | null;
  action_tags?: ActionTag[];
}

// Lead conversion request
export interface LeadConversionRequest {
  first_name?: string;
  last_name?: string;
  create_job?: boolean;
  job_description?: string;
}

// Lead conversion response
export interface LeadConversionResponse {
  success: boolean;
  lead_id: string;
  customer_id: string;
  job_id: string | null;
  message: string;
}

// Follow-up queue item
export interface FollowUpLead extends Lead {
  time_since_created: number; // hours
}

// Paginated follow-up queue response
export interface PaginatedFollowUpResponse {
  items: FollowUpLead[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// Status display helpers
export const LEAD_STATUS_LABELS: Record<LeadStatus, string> = {
  new: 'New',
  contacted: 'Contacted (Awaiting Response)',
  qualified: 'Qualified',
  converted: 'Converted',
  lost: 'Lost',
  spam: 'Spam',
};

export const LEAD_SITUATION_LABELS: Record<LeadSituation, string> = {
  new_system: 'New System',
  upgrade: 'Upgrade',
  repair: 'Repair',
  exploring: 'Exploring',
};

export const LEAD_SOURCE_LABELS: Record<LeadSource, string> = {
  website: 'Website',
  google_form: 'Google Form',
  phone_call: 'Phone Call',
  text_message: 'Text Message',
  google_ad: 'Google Ad',
  social_media: 'Social Media',
  qr_code: 'QR Code',
  email_campaign: 'Email Campaign',
  text_campaign: 'Text Campaign',
  referral: 'Referral',
  other: 'Other',
};

export const LEAD_SOURCE_COLORS: Record<LeadSource, string> = {
  website: 'bg-blue-100 text-blue-800',
  google_form: 'bg-emerald-100 text-emerald-800',
  phone_call: 'bg-amber-100 text-amber-800',
  text_message: 'bg-violet-100 text-violet-800',
  google_ad: 'bg-red-100 text-red-800',
  social_media: 'bg-pink-100 text-pink-800',
  qr_code: 'bg-cyan-100 text-cyan-800',
  email_campaign: 'bg-indigo-100 text-indigo-800',
  text_campaign: 'bg-fuchsia-100 text-fuchsia-800',
  referral: 'bg-teal-100 text-teal-800',
  other: 'bg-gray-100 text-gray-800',
};

export const INTAKE_TAG_LABELS: Record<string, string> = {
  schedule: 'Schedule',
  follow_up: 'Follow Up',
};

export const ACTION_TAG_LABELS: Record<ActionTag, string> = {
  NEEDS_CONTACT: 'Needs Contact',
  NEEDS_ESTIMATE: 'Needs Estimate',
  ESTIMATE_PENDING: 'Estimate Pending',
  ESTIMATE_APPROVED: 'Estimate Approved',
  ESTIMATE_REJECTED: 'Estimate Rejected',
};

export const ACTION_TAG_COLORS: Record<ActionTag, string> = {
  NEEDS_CONTACT: 'bg-red-100 text-red-800 border-red-200',
  NEEDS_ESTIMATE: 'bg-orange-100 text-orange-800 border-orange-200',
  ESTIMATE_PENDING: 'bg-yellow-100 text-yellow-800 border-yellow-200',
  ESTIMATE_APPROVED: 'bg-green-100 text-green-800 border-green-200',
  ESTIMATE_REJECTED: 'bg-gray-100 text-gray-600 border-gray-200',
};

// From-call lead creation request
export interface FromCallRequest {
  name: string;
  phone: string;
  email?: string | null;
  address: string;
  zip_code?: string | null;
  situation: LeadSituation;
  notes?: string | null;
  lead_source?: LeadSource;
  source_detail?: string | null;
  intake_tag?: IntakeTag | null;
}

// Manual lead creation request
export interface ManualLeadCreateRequest {
  name: string;
  phone: string;
  email?: string | null;
  address?: string | null;
  city?: string | null;
  state?: string | null;
  zip_code?: string | null;
  situation?: LeadSituation;
  notes?: string | null;
}

// Lead metrics by source
export interface LeadSourceCount {
  lead_source: string;
  count: number;
}

export interface LeadMetricsBySourceResponse {
  items: LeadSourceCount[];
  total: number;
  date_from: string;
  date_to: string;
}

export interface LeadMetricsBySourceParams {
  date_from?: string;
  date_to?: string;
}
