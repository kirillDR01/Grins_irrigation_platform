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
  | 'cancelled';

export type PaymentMethod = 'cash' | 'check' | 'venmo' | 'zelle' | 'stripe';

export interface InvoiceStatusConfig {
  label: string;
  bgColor: string;
  color: string;
}

export const INVOICE_STATUS_CONFIG: Record<InvoiceStatus, InvoiceStatusConfig> = {
  draft: {
    label: 'Draft',
    bgColor: 'bg-slate-100',
    color: 'text-slate-500',
  },
  sent: {
    label: 'Sent',
    bgColor: 'bg-blue-100',
    color: 'text-blue-700',
  },
  viewed: {
    label: 'Viewed',
    bgColor: 'bg-blue-100',
    color: 'text-blue-700',
  },
  paid: {
    label: 'Paid',
    bgColor: 'bg-emerald-100',
    color: 'text-emerald-700',
  },
  partial: {
    label: 'Partial',
    bgColor: 'bg-violet-100',
    color: 'text-violet-700',
  },
  overdue: {
    label: 'Overdue',
    bgColor: 'bg-red-100',
    color: 'text-red-700',
  },
  lien_warning: {
    label: 'Lien Warning',
    bgColor: 'bg-amber-100',
    color: 'text-amber-700',
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
}

// Invoice detail with job and customer info
export interface InvoiceDetail extends Invoice {
  job_description: string | null;
  customer_name: string | null;
  customer_phone: string | null;
  customer_email: string | null;
}

// Invoice list params
export interface InvoiceListParams extends PaginationParams {
  status?: InvoiceStatus;
  customer_id?: string;
  job_id?: string;
  date_from?: string;
  date_to?: string;
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
