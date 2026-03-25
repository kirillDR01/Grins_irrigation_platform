import { apiClient } from '@/core/api';
import type { PaginatedResponse } from '@/core/api';
import type {
  AccountingSummary,
  Expense,
  ExpenseCreateRequest,
  ExpenseListParams,
  SpendingByCategory,
  ReceiptExtraction,
  TaxSummary,
  TaxEstimate,
  TaxProjectionRequest,
  TaxProjectionResponse,
  ConnectedAccount,
  PendingTransaction,
  AuditLogEntry,
  AuditLogParams,
  InvoiceSummaryItem,
  DateRangeFilter,
} from '../types';

export const accountingApi = {
  // Accounting summary metrics
  getSummary: async (dateRange?: DateRangeFilter): Promise<AccountingSummary> => {
    const response = await apiClient.get<AccountingSummary>('/accounting/summary', {
      params: dateRange,
    });
    return response.data;
  },

  // Pending invoices
  getPendingInvoices: async (): Promise<PaginatedResponse<InvoiceSummaryItem>> => {
    const response = await apiClient.get<PaginatedResponse<InvoiceSummaryItem>>('/invoices', {
      params: { status: 'sent,viewed' },
    });
    return response.data;
  },

  // Past due invoices
  getPastDueInvoices: async (): Promise<PaginatedResponse<InvoiceSummaryItem>> => {
    const response = await apiClient.get<PaginatedResponse<InvoiceSummaryItem>>('/invoices', {
      params: { status: 'overdue' },
    });
    return response.data;
  },

  // Expense CRUD
  getExpenses: async (params?: ExpenseListParams): Promise<PaginatedResponse<Expense>> => {
    const response = await apiClient.get<PaginatedResponse<Expense>>('/expenses', { params });
    return response.data;
  },

  createExpense: async (data: ExpenseCreateRequest): Promise<Expense> => {
    const formData = new FormData();
    formData.append('category', data.category);
    formData.append('description', data.description);
    formData.append('amount', String(data.amount));
    formData.append('date', data.date);
    if (data.job_id) formData.append('job_id', data.job_id);
    if (data.vendor) formData.append('vendor', data.vendor);
    if (data.notes) formData.append('notes', data.notes);
    if (data.receipt_file) formData.append('receipt_file', data.receipt_file);
    const response = await apiClient.post<Expense>('/expenses', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  updateExpense: async (id: string, data: Partial<ExpenseCreateRequest>): Promise<Expense> => {
    const response = await apiClient.patch<Expense>(`/expenses/${id}`, data);
    return response.data;
  },

  deleteExpense: async (id: string): Promise<void> => {
    await apiClient.delete(`/expenses/${id}`);
  },

  // Spending by category
  getSpendingByCategory: async (params?: { start_date?: string; end_date?: string }): Promise<SpendingByCategory[]> => {
    const response = await apiClient.get<SpendingByCategory[]>('/expenses/by-category', { params });
    return response.data;
  },

  // Receipt OCR extraction
  extractReceipt: async (file: File): Promise<ReceiptExtraction> => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await apiClient.post<ReceiptExtraction>('/expenses/extract-receipt', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  // Tax preparation
  getTaxSummary: async (taxYear?: number): Promise<TaxSummary> => {
    const response = await apiClient.get<TaxSummary>('/accounting/tax-summary', {
      params: { tax_year: taxYear },
    });
    return response.data;
  },

  // Tax estimate
  getTaxEstimate: async (): Promise<TaxEstimate> => {
    const response = await apiClient.get<TaxEstimate>('/accounting/tax-estimate');
    return response.data;
  },

  // Tax projection (what-if)
  projectTax: async (data: TaxProjectionRequest): Promise<TaxProjectionResponse> => {
    const response = await apiClient.post<TaxProjectionResponse>('/accounting/tax-projection', data);
    return response.data;
  },

  // Connected accounts (Plaid)
  getConnectedAccounts: async (): Promise<ConnectedAccount[]> => {
    const response = await apiClient.get<ConnectedAccount[]>('/accounting/connected-accounts');
    return response.data;
  },

  connectAccount: async (publicToken: string): Promise<ConnectedAccount> => {
    const response = await apiClient.post<ConnectedAccount>('/accounting/connect-account', {
      public_token: publicToken,
    });
    return response.data;
  },

  // Pending transactions for review
  getPendingTransactions: async (): Promise<PaginatedResponse<PendingTransaction>> => {
    const response = await apiClient.get<PaginatedResponse<PendingTransaction>>(
      '/accounting/transactions',
      { params: { status: 'pending_review' } }
    );
    return response.data;
  },

  approveTransaction: async (id: string, category: string): Promise<void> => {
    await apiClient.post(`/accounting/transactions/${id}/approve`, { category });
  },

  // Audit log
  getAuditLog: async (params?: AuditLogParams): Promise<PaginatedResponse<AuditLogEntry>> => {
    const response = await apiClient.get<PaginatedResponse<AuditLogEntry>>('/audit-log', { params });
    return response.data;
  },

  // Export tax CSV
  exportTaxCsv: async (taxYear: number): Promise<Blob> => {
    const response = await apiClient.get('/accounting/tax-summary/export', {
      params: { tax_year: taxYear },
      responseType: 'blob',
    });
    return response.data;
  },
};
