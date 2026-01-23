import type { BaseEntity, PaginationParams } from '@/core/api';

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
}

// Customer list params
export interface CustomerListParams extends PaginationParams {
  search?: string;
  is_priority?: boolean;
  is_red_flag?: boolean;
  is_slow_payer?: boolean;
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
