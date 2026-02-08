import type { BaseEntity, PaginationParams } from '@/core/api';

// Lead status enum values
export type LeadStatus = 'new' | 'contacted' | 'qualified' | 'converted' | 'lost' | 'spam';

// Lead situation enum values
export type LeadSituation = 'new_system' | 'upgrade' | 'repair' | 'exploring';

// Lead entity
export interface Lead extends BaseEntity {
  name: string;
  phone: string;
  email: string | null;
  zip_code: string;
  situation: LeadSituation;
  notes: string | null;
  source_site: string;
  status: LeadStatus;
  assigned_to: string | null;
  customer_id: string | null;
  contacted_at: string | null;
  converted_at: string | null;
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
