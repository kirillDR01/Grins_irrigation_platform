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

// Lead entity
export interface Lead extends BaseEntity {
  name: string;
  phone: string;
  email: string | null;
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
  sms_consent: boolean;
  terms_accepted: boolean;
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
  contacted: 'Contacted',
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

// From-call lead creation request
export interface FromCallRequest {
  name: string;
  phone: string;
  email?: string | null;
  zip_code: string;
  situation: LeadSituation;
  notes?: string | null;
  lead_source?: LeadSource;
  source_detail?: string | null;
  intake_tag?: IntakeTag | null;
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
