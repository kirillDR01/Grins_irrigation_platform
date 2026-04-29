/**
 * Invoice types for the frontend.
 * Mirrors backend InvoiceStatus and PaymentMethod enums.
 */

import type { BaseEntity, PaginationParams } from '@/core/api';

export type InvoiceStatus =
  | 'draft'
  | 'sent'
  | 'viewed'
  | 'paid'
  | 'partial'
  | 'overdue'
  | 'lien_warning'
  | 'lien_filed'
  | 'cancelled'
  | 'refunded'
  | 'disputed';

// PaymentMethod mirrors the backend enum in grins_platform.models.enums.
// H-4 (bughunt 2026-04-16): `credit_card`, `ach`, and `other` were
// added as spec values. `stripe` is retained so legacy rows stored
// before H-4 still round-trip through the API — new UI pickers omit it.
export type PaymentMethod =
  | 'cash'
  | 'check'
  | 'venmo'
  | 'zelle'
  | 'stripe'
  | 'credit_card'
  | 'ach'
  | 'other';

export interface InvoiceStatusConfig {
  label: string;
  bgColor: string;
  color: string;
}

export const INVOICE_STATUS_CONFIG: Record<InvoiceStatus, InvoiceStatusConfig> = {
  draft: {
    label: 'Draft',
    bgColor: 'bg-yellow-100',
    color: 'text-yellow-700',
  },
  sent: {
    label: 'Sent',
    bgColor: 'bg-yellow-100',
    color: 'text-yellow-700',
  },
  viewed: {
    label: 'Viewed',
    bgColor: 'bg-yellow-100',
    color: 'text-yellow-700',
  },
  paid: {
    label: 'Paid',
    bgColor: 'bg-green-100',
    color: 'text-green-700',
  },
  partial: {
    label: 'Partial',
    bgColor: 'bg-yellow-100',
    color: 'text-yellow-700',
  },
  overdue: {
    label: 'Overdue',
    bgColor: 'bg-red-100',
    color: 'text-red-700',
  },
  lien_warning: {
    label: 'Lien Warning',
    bgColor: 'bg-red-100',
    color: 'text-red-700',
  },
  lien_filed: {
    label: 'Lien Filed',
    bgColor: 'bg-red-100',
    color: 'text-red-700',
  },
  cancelled: {
    label: 'Cancelled',
    bgColor: 'bg-slate-100',
    color: 'text-slate-500',
  },
  refunded: {
    label: 'Refunded',
    bgColor: 'bg-purple-100',
    color: 'text-purple-700',
  },
  disputed: {
    label: 'Disputed',
    bgColor: 'bg-orange-100',
    color: 'text-orange-700',
  },
};

export function getInvoiceStatusConfig(status: InvoiceStatus): InvoiceStatusConfig {
  return INVOICE_STATUS_CONFIG[status];
}

// Invoice line item
export interface InvoiceLineItem {
  description: string;
  quantity: number;
  unit_price: number;
  total: number;
}

// Invoice entity
export interface Invoice extends BaseEntity {
  job_id: string;
  customer_id: string;
  invoice_number: string;
  amount: number;
  late_fee_amount: number;
  total_amount: number;
  invoice_date: string;
  due_date: string;
  status: InvoiceStatus;
  payment_method: PaymentMethod | null;
  payment_reference: string | null;
  paid_at: string | null;
  paid_amount: number | null;
  reminder_count: number;
  last_reminder_sent: string | null;
  lien_eligible: boolean;
  lien_warning_sent: string | null;
  lien_filed_date: string | null;
  line_items: InvoiceLineItem[] | null;
  notes: string | null;
  customer_name: string | null;
  // bughunt M-12: server-computed fields, exclusive of each other.
  days_until_due: number | null;
  days_past_due: number | null;
  // Stripe Payment Link fields (Architecture C — Phase 2).
  stripe_payment_link_id: string | null;
  stripe_payment_link_url: string | null;
  stripe_payment_link_active: boolean;
  payment_link_sent_at: string | null;
  payment_link_sent_count: number;
}

// Invoice detail with job and customer info
export interface InvoiceDetail extends Invoice {
  job_description: string | null;
  customer_name: string | null;
  customer_phone: string | null;
  customer_email: string | null;
}

// Invoice list params — 9-axis composable AND filtering
export interface InvoiceListParams extends PaginationParams {
  status?: InvoiceStatus;
  customer_id?: string;
  customer_search?: string;
  job_id?: string;
  date_from?: string;
  date_to?: string;
  date_type?: 'created' | 'due' | 'paid';
  amount_min?: number;
  amount_max?: number;
  payment_types?: string;
  days_until_due_min?: number;
  days_until_due_max?: number;
  days_past_due_min?: number;
  days_past_due_max?: number;
  invoice_number?: string;
  // CG-13: substring match on payment_reference (e.g. paste a Stripe pi_*).
  payment_reference?: string;
  lien_eligible?: boolean;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

// Invoice create request
export interface InvoiceCreate {
  job_id: string;
  amount: number;
  late_fee_amount?: number;
  due_date: string;
  line_items?: InvoiceLineItem[];
  notes?: string;
}

// Invoice update request
export interface InvoiceUpdate {
  amount?: number;
  late_fee_amount?: number;
  due_date?: string;
  line_items?: InvoiceLineItem[];
  notes?: string;
}

// Payment record request
export interface PaymentRecord {
  amount: number;
  payment_method: PaymentMethod;
  payment_reference?: string;
}

// Notification types for bulk notify (Req 38)
export type NotificationType = 'REMINDER' | 'PAST_DUE' | 'LIEN_WARNING' | 'UPCOMING_DUE';

export const NOTIFICATION_TYPE_CONFIG: Record<NotificationType, { label: string; description: string }> = {
  REMINDER: { label: 'Reminder', description: 'General payment reminder' },
  PAST_DUE: { label: 'Past Due', description: 'Past due notice' },
  LIEN_WARNING: { label: 'Lien Warning', description: 'Mechanic\'s lien warning' },
  UPCOMING_DUE: { label: 'Upcoming Due', description: 'Upcoming due date reminder' },
};

export interface BulkNotifyRequest {
  invoice_ids: string[];
  notification_type: NotificationType;
}

export interface BulkNotifyResponse {
  sent: number;
  skipped: number;
  failed: number;
  total: number;
}

// Mass notify types (Req 29.3, 29.4)
// CR-5: ``lien_eligible`` removed — use the /invoices?tab=lien-review queue.
export type MassNotificationType = 'past_due' | 'due_soon';

export const MASS_NOTIFICATION_CONFIG: Record<MassNotificationType, { label: string; description: string }> = {
  past_due: { label: 'Past Due', description: 'Notify all customers with past-due invoices' },
  due_soon: { label: 'Due Soon', description: 'Notify customers with invoices due within a configurable window' },
};

export interface MassNotifyRequest {
  notification_type: MassNotificationType;
  due_soon_days?: number;
  lien_days_past_due?: number;
  lien_min_amount?: number;
  template?: string;
}

export interface MassNotifyResponse {
  notification_type: string;
  targeted: number;
  sent: number;
  failed: number;
  skipped: number;
}

// PDF generation types (Req 80)
export interface PdfUrlResponse {
  url: string;
}

// Stripe Payment Link send response (Architecture C — Phase 2.7).
export interface SendPaymentLinkResponse {
  channel: 'sms' | 'email';
  link_url: string;
  sent_at: string;
  sent_count: number;
  attempted_channels: Array<'sms' | 'email'>;
  sms_failure_reason:
    | 'consent'
    | 'rate_limit'
    | 'provider_error'
    | 'no_phone'
    | null;
}

// CR-5: Lien Review Queue (bughunt 2026-04-16)
export interface LienCandidate {
  customer_id: string;
  customer_name: string;
  customer_phone: string | null;
  oldest_invoice_age_days: number;
  total_past_due_amount: string;
  invoice_ids: string[];
  invoice_numbers: string[];
}

export interface LienNoticeResult {
  success: boolean;
  customer_id: string;
  sent_at: string | null;
  sms_message_id: string | null;
  message: string;
}

export interface LienCandidatesParams {
  days_past_due?: number;
  min_amount?: number;
}
