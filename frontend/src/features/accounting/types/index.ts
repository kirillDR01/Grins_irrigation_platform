import type { PaginationParams } from '@/core/api';

// Accounting summary metrics
export interface AccountingSummary {
  ytd_revenue: number;
  ytd_expenses: number;
  ytd_profit: number;
  profit_margin: number;
  pending_invoice_count: number;
  pending_invoice_total: number;
  past_due_invoice_count: number;
  past_due_invoice_total: number;
}

// Date range filter
export type DateRangePreset = 'month' | 'quarter' | 'ytd' | 'custom';

export interface DateRangeFilter {
  preset: DateRangePreset;
  start_date?: string;
  end_date?: string;
}

// Invoice summary for pending/past-due sections
export interface InvoiceSummaryItem {
  id: string;
  invoice_number: string;
  customer_name: string;
  total_amount: number;
  status: string;
  due_date: string;
  days_past_due?: number;
  created_at: string;
}

// Expense types
export type ExpenseCategory =
  | 'MATERIALS'
  | 'FUEL'
  | 'MAINTENANCE'
  | 'LABOR'
  | 'MARKETING'
  | 'INSURANCE'
  | 'EQUIPMENT'
  | 'OFFICE'
  | 'SUBCONTRACTING'
  | 'OTHER';

export interface Expense {
  id: string;
  category: ExpenseCategory;
  description: string;
  amount: number;
  date: string;
  job_id: string | null;
  vendor: string | null;
  receipt_file_key: string | null;
  receipt_amount_extracted: number | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface ExpenseCreateRequest {
  category: ExpenseCategory;
  description: string;
  amount: number;
  date: string;
  job_id?: string;
  vendor?: string;
  notes?: string;
  receipt_file?: File;
}

export interface ExpenseListParams extends PaginationParams {
  category?: ExpenseCategory;
  start_date?: string;
  end_date?: string;
}

// Spending by category
export interface SpendingByCategory {
  category: ExpenseCategory;
  total: number;
  percentage: number;
}

// Receipt OCR extraction
export interface ReceiptExtraction {
  amount: number | null;
  vendor: string | null;
  category: ExpenseCategory | null;
  confidence: number;
}

// Tax preparation
export interface TaxCategorySummary {
  category: string;
  total: number;
}

export interface TaxSummary {
  tax_year: number;
  categories: TaxCategorySummary[];
  total_deductions: number;
  revenue_by_job_type: { job_type: string; total: number }[];
}

// Tax estimation
export interface TaxEstimate {
  estimated_tax_due: number;
  effective_tax_rate: number;
  taxable_income: number;
  total_deductions: number;
}

// Tax projection (what-if)
export interface TaxProjectionRequest {
  hypothetical_revenue: number;
  hypothetical_expenses: number;
}

export interface TaxProjectionResponse {
  current_tax_due: number;
  projected_tax_due: number;
  tax_impact: number;
  projected_taxable_income: number;
}

// Connected accounts (Plaid)
export interface ConnectedAccount {
  id: string;
  institution_name: string;
  account_name: string;
  account_type: string;
  mask: string;
  last_synced_at: string | null;
}

export interface PendingTransaction {
  id: string;
  date: string;
  description: string;
  amount: number;
  merchant_name: string | null;
  suggested_category: ExpenseCategory | null;
  status: 'pending_review' | 'approved' | 'rejected';
  account_id: string;
}

// Audit log
export interface AuditLogEntry {
  id: string;
  actor_id: string;
  actor_role: string;
  action: string;
  resource_type: string;
  resource_id: string;
  details: Record<string, unknown>;
  ip_address: string;
  created_at: string;
}

export interface AuditLogParams extends PaginationParams {
  action?: string;
  resource_type?: string;
  start_date?: string;
  end_date?: string;
}
