/**
 * Agreement types for the frontend.
 * Mirrors backend AgreementStatus, AgreementPaymentStatus, PackageType enums
 * and agreement Pydantic schemas.
 */

import type { PaginationParams } from '@/core/api';

// ---------------------------------------------------------------------------
// Enums
// ---------------------------------------------------------------------------

export type AgreementStatus =
  | 'pending'
  | 'active'
  | 'past_due'
  | 'paused'
  | 'pending_renewal'
  | 'cancelled'
  | 'expired';

export type PaymentStatus = 'current' | 'past_due' | 'failed';

export type PackageType = 'residential' | 'commercial';

export type BillingFrequency = 'annual' | 'monthly';

export type DisclosureType =
  | 'PRE_SALE'
  | 'CONFIRMATION'
  | 'RENEWAL_NOTICE'
  | 'ANNUAL_NOTICE'
  | 'CANCELLATION_CONF';

// ---------------------------------------------------------------------------
// Status display config
// ---------------------------------------------------------------------------

export interface AgreementStatusConfig {
  label: string;
  bgColor: string;
  color: string;
}

export const AGREEMENT_STATUS_CONFIG: Record<AgreementStatus, AgreementStatusConfig> = {
  pending: { label: 'Pending', bgColor: 'bg-amber-100', color: 'text-amber-700' },
  active: { label: 'Active', bgColor: 'bg-emerald-100', color: 'text-emerald-700' },
  past_due: { label: 'Past Due', bgColor: 'bg-red-100', color: 'text-red-700' },
  paused: { label: 'Paused', bgColor: 'bg-slate-100', color: 'text-slate-600' },
  pending_renewal: { label: 'Pending Renewal', bgColor: 'bg-blue-100', color: 'text-blue-700' },
  cancelled: { label: 'Cancelled', bgColor: 'bg-slate-100', color: 'text-slate-500' },
  expired: { label: 'Expired', bgColor: 'bg-slate-100', color: 'text-slate-500' },
};

export function getAgreementStatusConfig(status: AgreementStatus): AgreementStatusConfig {
  return AGREEMENT_STATUS_CONFIG[status];
}

// ---------------------------------------------------------------------------
// Tier
// ---------------------------------------------------------------------------

export interface AgreementTier {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  package_type: PackageType;
  annual_price: number;
  billing_frequency: BillingFrequency;
  included_services: Record<string, unknown>[];
  perks: string[] | null;
  is_active: boolean;
  display_order: number;
}

// ---------------------------------------------------------------------------
// Status log
// ---------------------------------------------------------------------------

export interface AgreementStatusLog {
  id: string;
  old_status: string | null;
  new_status: string;
  changed_by: string | null;
  changed_by_name: string | null;
  reason: string | null;
  metadata: Record<string, unknown> | null;
  created_at: string;
}

// ---------------------------------------------------------------------------
// Job summary (embedded in agreement detail)
// ---------------------------------------------------------------------------

export interface AgreementJobSummary {
  id: string;
  job_type: string | null;
  status: string;
  target_start_date: string | null;
  target_end_date: string | null;
}

// ---------------------------------------------------------------------------
// Agreement entities
// ---------------------------------------------------------------------------

export interface Agreement {
  id: string;
  agreement_number: string;
  customer_id: string;
  customer_name: string | null;
  tier_id: string;
  tier_name: string | null;
  package_type: string | null;
  property_id: string | null;
  status: AgreementStatus;
  annual_price: number;
  start_date: string | null;
  end_date: string | null;
  renewal_date: string | null;
  auto_renew: boolean;
  payment_status: PaymentStatus;
  preferred_schedule: string | null;
  preferred_schedule_details: string | null;
  created_at: string;
}

export interface AgreementDetail extends Agreement {
  stripe_subscription_id: string | null;
  stripe_customer_id: string | null;
  cancelled_at: string | null;
  cancellation_reason: string | null;
  cancellation_refund_amount: number | null;
  pause_reason: string | null;
  last_payment_date: string | null;
  last_payment_amount: number | null;
  renewal_approved_by: string | null;
  renewal_approved_at: string | null;
  consent_recorded_at: string | null;
  consent_method: string | null;
  last_annual_notice_sent: string | null;
  last_renewal_notice_sent: string | null;
  notes: string | null;
  jobs: AgreementJobSummary[];
  status_logs: AgreementStatusLog[];
}

// ---------------------------------------------------------------------------
// Disclosure record (compliance)
// ---------------------------------------------------------------------------

export interface DisclosureRecord {
  id: string;
  agreement_id: string | null;
  customer_id: string | null;
  disclosure_type: DisclosureType;
  sent_at: string;
  sent_via: string;
  recipient_email: string | null;
  recipient_phone: string | null;
  delivery_confirmed: boolean;
  created_at: string;
}

// ---------------------------------------------------------------------------
// Metrics
// ---------------------------------------------------------------------------

export interface AgreementMetrics {
  active_count: number;
  mrr: number;
  arpa: number;
  renewal_rate: number;
  churn_rate: number;
  past_due_amount: number;
}

// ---------------------------------------------------------------------------
// MRR History
// ---------------------------------------------------------------------------

export interface MrrDataPoint {
  month: string;
  mrr: number;
}

export interface MrrHistory {
  data_points: MrrDataPoint[];
}

// ---------------------------------------------------------------------------
// Tier Distribution
// ---------------------------------------------------------------------------

export interface TierDistributionItem {
  tier_id: string;
  tier_name: string;
  package_type: string;
  active_count: number;
}

export interface TierDistribution {
  items: TierDistributionItem[];
}

// ---------------------------------------------------------------------------
// Request / filter params
// ---------------------------------------------------------------------------

export interface AgreementListParams extends PaginationParams {
  status?: AgreementStatus;
  tier_id?: string;
  customer_id?: string;
  payment_status?: PaymentStatus;
  expiring_soon?: boolean;
}

export interface AgreementStatusUpdateRequest {
  status: string;
  reason?: string;
}

export interface AgreementRenewalRejectRequest {
  reason?: string;
}
