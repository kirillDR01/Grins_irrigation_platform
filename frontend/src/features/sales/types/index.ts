import type { PaginationParams } from '@/core/api';

// Sales pipeline metrics
export interface SalesMetrics {
  estimates_needing_writeup_count: number;
  pending_approval_count: number;
  needs_followup_count: number;
  total_pipeline_revenue: number;
  conversion_rate: number;
}

// Estimate list item for tables/cards
export interface EstimateListItem {
  id: string;
  customer_name: string;
  total: number;
  status: string;
  days_since_sent: number;
  next_follow_up: string | null;
  promotion_code: string | null;
  created_at: string;
}

// Estimate line item with material + labor costs
export interface EstimateLineItem {
  item: string;
  description: string;
  unit_price: number;
  quantity: number;
  material_cost: number;
  labor_cost: number;
}

// Estimate tier (Good/Better/Best)
export type TierName = 'good' | 'better' | 'best';

export interface EstimateTier {
  name: TierName;
  line_items: EstimateLineItem[];
  total: number;
}

// Estimate creation request
export interface EstimateCreateRequest {
  template_id?: string;
  lead_id?: string;
  customer_id?: string;
  job_id?: string;
  line_items: EstimateLineItem[];
  options?: EstimateTier[];
  promotion_code?: string;
  notes?: string;
  valid_until?: string;
}

// Media library item
export interface MediaItem {
  id: string;
  file_key: string;
  file_name: string;
  file_size: number;
  content_type: string;
  media_type: 'PHOTO' | 'VIDEO' | 'TESTIMONIAL';
  category: string;
  caption: string | null;
  is_public: boolean;
  created_at: string;
  download_url?: string;
}

// Media list query params
export interface MediaListParams extends PaginationParams {
  category?: string;
  media_type?: string;
}

// Follow-up queue item
export interface FollowUpItem {
  id: string;
  estimate_id: string;
  customer_name: string;
  estimate_total: number;
  days_since_sent: number;
  next_follow_up: string;
  promotion_code: string | null;
  status: string;
}

// Estimate template
export interface EstimateTemplate {
  id: string;
  name: string;
  description: string | null;
  line_items: EstimateLineItem[];
  terms: string | null;
  is_active: boolean;
}

// Conversion funnel data point
export interface FunnelStage {
  stage: string;
  count: number;
}

// Estimate status for detail view (Req 83)
export type EstimateStatus = 'draft' | 'sent' | 'viewed' | 'approved' | 'rejected' | 'cancelled' | 'expired';

// Activity timeline event (Req 83)
export interface ActivityEvent {
  event_type: string;
  timestamp: string;
  actor: string | null;
  details: string | null;
}

// Linked document (Req 83)
export interface LinkedDocument {
  type: string;
  name: string;
  url: string;
}

// Estimate detail (Req 83)
export interface EstimateDetail {
  id: string;
  estimate_number: string;
  customer_name: string;
  customer_email: string | null;
  customer_phone: string | null;
  status: EstimateStatus;
  created_at: string;
  valid_until: string | null;
  line_items: EstimateLineItem[];
  tiers: EstimateTier[] | null;
  subtotal: number;
  discount_amount: number;
  tax_amount: number;
  total: number;
  promotion_code: string | null;
  notes: string | null;
  activity_timeline: ActivityEvent[];
  linked_documents: LinkedDocument[];
}

// Status badge color mapping (Req 83)
export const ESTIMATE_STATUS_CONFIG: Record<EstimateStatus, { label: string; className: string }> = {
  draft: { label: 'Draft', className: 'bg-slate-100 text-slate-700' },
  sent: { label: 'Sent', className: 'bg-blue-100 text-blue-700' },
  viewed: { label: 'Viewed', className: 'bg-violet-100 text-violet-700' },
  approved: { label: 'Approved', className: 'bg-emerald-100 text-emerald-700' },
  rejected: { label: 'Rejected', className: 'bg-red-100 text-red-700' },
  cancelled: { label: 'Cancelled', className: 'bg-slate-100 text-slate-500' },
  expired: { label: 'Expired', className: 'bg-amber-100 text-amber-700' },
};
