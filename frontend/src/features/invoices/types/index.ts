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
    bgColor: 'bg-gray-100',
    color: 'text-gray-800',
  },
  sent: {
    label: 'Sent',
    bgColor: 'bg-blue-100',
    color: 'text-blue-800',
  },
  viewed: {
    label: 'Viewed',
    bgColor: 'bg-indigo-100',
    color: 'text-indigo-800',
  },
  paid: {
    label: 'Paid',
    bgColor: 'bg-green-100',
    color: 'text-green-800',
  },
  partial: {
    label: 'Partial',
    bgColor: 'bg-yellow-100',
    color: 'text-yellow-800',
  },
  overdue: {
    label: 'Overdue',
    bgColor: 'bg-red-100',
    color: 'text-red-800',
  },
  lien_warning: {
    label: 'Lien Warning',
    bgColor: 'bg-orange-100',
    color: 'text-orange-800',
  },
  lien_filed: {
    label: 'Lien Filed',
    bgColor: 'bg-red-200',
    color: 'text-red-900',
  },
  cancelled: {
    label: 'Cancelled',
    bgColor: 'bg-gray-100',
    color: 'text-gray-500',
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
