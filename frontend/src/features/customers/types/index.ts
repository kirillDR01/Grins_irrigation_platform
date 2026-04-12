import type { BaseEntity, PaginationParams, PaginatedResponse } from '@/core/api';

// Property entity (returned nested in customer detail)
export interface Property extends BaseEntity {
  customer_id: string;
  address: string;
  city: string;
  state: string;
  zip_code: string | null;
  zone_count: number | null;
  system_type: string;
  property_type: string;
  is_primary: boolean;
  is_hoa: boolean;
  access_instructions: string | null;
  gate_code: string | null;
  has_dogs: boolean;
  special_notes: string | null;
  latitude: number | null;
  longitude: number | null;
}

// Customer entity
export interface Customer extends BaseEntity {
  first_name: string;
  last_name: string;
  phone: string;
  email: string | null;
  is_priority: boolean;
  is_red_flag: boolean;
  is_slow_payer: boolean;
  is_new_customer: boolean;
  sms_opt_in: boolean;
  email_opt_in: boolean;
  lead_source: string | null;
  internal_notes: string | null;
  preferred_service_times: { preference: string } | null;
  properties?: Property[];
}

// Customer photo entity (Req 9)
export interface CustomerPhoto extends BaseEntity {
  customer_id: string;
  file_key: string;
  file_name: string;
  file_size: number;
  content_type: string;
  caption: string | null;
  uploaded_by: string | null;
  download_url: string;
}

// Customer invoice entity (Req 10)
export type InvoiceStatus = 'draft' | 'sent' | 'viewed' | 'paid' | 'overdue' | 'cancelled' | 'void';

export interface CustomerInvoice extends BaseEntity {
  invoice_number: string;
  date: string;
  due_date: string | null;
  total_amount: number;
  status: InvoiceStatus;
  days_until_due: number | null;
  days_past_due: number | null;
}

// Invoice status color mapping
export const invoiceStatusColors: Record<InvoiceStatus, string> = {
  draft: 'bg-slate-100 text-slate-700',
  sent: 'bg-blue-100 text-blue-700',
  viewed: 'bg-violet-100 text-violet-700',
  paid: 'bg-emerald-100 text-emerald-700',
  overdue: 'bg-red-100 text-red-700',
  cancelled: 'bg-gray-100 text-gray-600',
  void: 'bg-gray-100 text-gray-600',
};

// Payment method entity (Req 56)
export interface PaymentMethod {
  id: string;
  brand: string;
  last4: string;
  exp_month: number;
  exp_year: number;
  is_default: boolean;
}

// Charge request (Req 56)
export interface ChargeRequest {
  payment_method_id: string;
  amount: number;
  description: string;
}

// Duplicate customer group (Req 7)
export interface DuplicateGroup {
  primary: Customer;
  duplicates: Customer[];
  match_reasons: string[];
}

// Merge request (Req 7)
export interface MergeRequest {
  primary_customer_id: string;
  duplicate_customer_ids: string[];
}

// Sent message entity (Req 82)
export interface SentMessage {
  id: string;
  message_type: string;
  recipient_phone: string | null;
  recipient_email: string | null;
  content: string;
  status: string;
  sent_at: string;
  created_at: string;
}

// Service preference entity (CRM2 Req 7)
export interface ServicePreference {
  id: string;
  service_type: string;
  preferred_week: string | null;
  preferred_date: string | null;
  time_window: string;
  notes: string | null;
}

export type ServicePreferenceCreate = Omit<ServicePreference, 'id'>;

// Re-export PaginatedResponse for convenience
export type { PaginatedResponse };

// Create customer request
export interface CustomerCreate {
  first_name: string;
  last_name: string;
  phone: string;
  email?: string | null;
  is_priority?: boolean;
  is_red_flag?: boolean;
  is_slow_payer?: boolean;
  sms_opt_in?: boolean;
  email_opt_in?: boolean;
  lead_source?: string | null;
}

// Update customer request
export interface CustomerUpdate {
  first_name?: string;
  last_name?: string;
  phone?: string;
  email?: string | null;
  is_priority?: boolean;
  is_red_flag?: boolean;
  is_slow_payer?: boolean;
  sms_opt_in?: boolean;
  email_opt_in?: boolean;
  lead_source?: string | null;
  internal_notes?: string | null;
  preferred_service_times?: { preference: string } | null;
}

// Customer list params
export interface CustomerListParams extends PaginationParams {
  search?: string;
  is_priority?: boolean;
  is_red_flag?: boolean;
  is_slow_payer?: boolean;
  sms_opt_in?: boolean;
  property_type?: 'residential' | 'commercial';
  is_hoa?: boolean;
  is_subscription_property?: boolean;
}

// Customer flags for display
export type CustomerFlag = 'priority' | 'red_flag' | 'slow_payer' | 'new_customer';

// Helper to get active flags
export function getCustomerFlags(customer: Customer): CustomerFlag[] {
  const flags: CustomerFlag[] = [];
  if (customer.is_priority) flags.push('priority');
  if (customer.is_red_flag) flags.push('red_flag');
  if (customer.is_slow_payer) flags.push('slow_payer');
  if (customer.is_new_customer) flags.push('new_customer');
  return flags;
}

// Full name helper
export function getCustomerFullName(customer: Customer): string {
  return `${customer.first_name} ${customer.last_name}`;
}
