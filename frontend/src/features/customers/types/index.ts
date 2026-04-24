import type { BaseEntity, PaginationParams, PaginatedResponse } from '@/core/api';

// --- Customer Tag types (Requirements 12.1, 17.2) ---
export type TagTone = 'neutral' | 'blue' | 'green' | 'amber' | 'violet';
export type TagSource = 'manual' | 'system';

export interface CustomerTag extends BaseEntity {
  customer_id: string;
  label: string;
  tone: TagTone;
  source: TagSource;
}

export interface TagSaveRequest {
  tags: Array<{ label: string; tone: TagTone }>;
}

export interface TagSaveResponse {
  tags: CustomerTag[];
  added: number;
  removed: number;
}

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
  status: string;
  is_priority: boolean;
  is_red_flag: boolean;
  is_slow_payer: boolean;
  is_new_customer: boolean;
  sms_opt_in: boolean;
  email_opt_in: boolean;
  lead_source: string | null;
  lead_source_details: string | null;
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

// Invoice status color mapping — green (Complete), yellow (Pending), red (Past Due) per Req 29.2
export const invoiceStatusColors: Record<InvoiceStatus, string> = {
  draft: 'bg-yellow-100 text-yellow-700',
  sent: 'bg-yellow-100 text-yellow-700',
  viewed: 'bg-yellow-100 text-yellow-700',
  paid: 'bg-green-100 text-green-700',
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

// Merge candidate from review queue (CRM Changes Update 2 Req 5, 6)
export interface MergeCandidate {
  id: string;
  customer_a_id: string;
  customer_b_id: string;
  score: number;
  match_signals: Record<string, unknown>;
  status: string;
  created_at: string;
  resolved_at: string | null;
  resolution: string | null;
}

export interface PaginatedMergeCandidates {
  items: MergeCandidate[];
  total: number;
  skip: number;
  limit: number;
}

export interface MergeFieldSelection {
  field_name: string;
  source: 'a' | 'b';
}

// Merge request (CRM Changes Update 2 Req 6)
export interface MergeRequest {
  duplicate_id: string;
  field_selections: MergeFieldSelection[];
}

export interface MergePreview {
  primary_id: string;
  duplicate_id: string;
  merged_fields: Record<string, unknown>;
  jobs_to_reassign: number;
  invoices_to_reassign: number;
  properties_to_reassign: number;
  communications_to_reassign: number;
  agreements_to_reassign: number;
  blockers: string[];
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

// Optional primary-property payload sent with CustomerCreate. When present,
// the backend creates a Property row in the same transaction and marks it
// is_primary=true.
export interface PrimaryPropertyCreate {
  address: string;
  city: string;
  state?: string;
  zip_code?: string | null;
}

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
  internal_notes?: string | null;
  primary_property?: PrimaryPropertyCreate | null;
}

// Customer status values
export type CustomerStatus = 'active' | 'inactive';

export const CUSTOMER_STATUS_LABELS: Record<CustomerStatus, string> = {
  active: 'Active',
  inactive: 'Inactive',
};

// Update customer request
export interface CustomerUpdate {
  first_name?: string;
  last_name?: string;
  phone?: string;
  email?: string | null;
  status?: CustomerStatus;
  is_priority?: boolean;
  is_red_flag?: boolean;
  is_slow_payer?: boolean;
  sms_opt_in?: boolean;
  email_opt_in?: boolean;
  lead_source?: string | null;
  lead_source_details?: string | null;
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

// Gap 06: SMS consent status + history (drives OptOutBadge + ConsentHistoryPanel).
export interface ConsentStatus {
  customer_id: string;
  phone: string | null;
  is_opted_out: boolean;
  opt_out_method: string | null;
  opt_out_timestamp: string | null;
  pending_informal_opt_out_alert_id: string | null;
}

export interface ConsentHistoryEntry {
  id: string;
  consent_given: boolean;
  consent_type: string;
  consent_method: string;
  consent_timestamp: string;
  opt_out_method: string | null;
  opt_out_timestamp: string | null;
  created_by_staff_id: string | null;
  consent_language_shown: string;
}

export interface ConsentHistoryResponse {
  items: ConsentHistoryEntry[];
  total: number;
}
