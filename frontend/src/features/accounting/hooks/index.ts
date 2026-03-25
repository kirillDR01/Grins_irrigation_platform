import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { accountingApi } from '../api/accountingApi';
import type {
  DateRangeFilter,
  ExpenseCreateRequest,
  ExpenseListParams,
  TaxProjectionRequest,
  AuditLogParams,
} from '../types';

// Query key factory
export const accountingKeys = {
  all: ['accounting'] as const,
  summary: (dateRange?: DateRangeFilter) => [...accountingKeys.all, 'summary', dateRange] as const,
  pendingInvoices: () => [...accountingKeys.all, 'pending-invoices'] as const,
  pastDueInvoices: () => [...accountingKeys.all, 'past-due-invoices'] as const,
  expenses: () => [...accountingKeys.all, 'expenses'] as const,
  expenseList: (params?: ExpenseListParams) => [...accountingKeys.expenses(), params] as const,
  spendingByCategory: (params?: { start_date?: string; end_date?: string }) =>
    [...accountingKeys.all, 'spending-by-category', params] as const,
  taxSummary: (year?: number) => [...accountingKeys.all, 'tax-summary', year] as const,
  taxEstimate: () => [...accountingKeys.all, 'tax-estimate'] as const,
  connectedAccounts: () => [...accountingKeys.all, 'connected-accounts'] as const,
  pendingTransactions: () => [...accountingKeys.all, 'pending-transactions'] as const,
  auditLog: () => [...accountingKeys.all, 'audit-log'] as const,
  auditLogList: (params?: AuditLogParams) => [...accountingKeys.auditLog(), params] as const,
};

// Accounting summary
export function useAccountingSummary(dateRange?: DateRangeFilter) {
  return useQuery({
    queryKey: accountingKeys.summary(dateRange),
    queryFn: () => accountingApi.getSummary(dateRange),
  });
}

// Pending invoices
export function usePendingInvoices() {
  return useQuery({
    queryKey: accountingKeys.pendingInvoices(),
    queryFn: () => accountingApi.getPendingInvoices(),
  });
}

// Past due invoices
export function usePastDueInvoices() {
  return useQuery({
    queryKey: accountingKeys.pastDueInvoices(),
    queryFn: () => accountingApi.getPastDueInvoices(),
  });
}

// Expenses
export function useExpenses(params?: ExpenseListParams) {
  return useQuery({
    queryKey: accountingKeys.expenseList(params),
    queryFn: () => accountingApi.getExpenses(params),
  });
}

export function useCreateExpense() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: ExpenseCreateRequest) => accountingApi.createExpense(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: accountingKeys.expenses() });
      qc.invalidateQueries({ queryKey: accountingKeys.summary() });
      qc.invalidateQueries({ queryKey: accountingKeys.spendingByCategory() });
    },
  });
}

export function useUpdateExpense() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<ExpenseCreateRequest> }) =>
      accountingApi.updateExpense(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: accountingKeys.expenses() });
      qc.invalidateQueries({ queryKey: accountingKeys.summary() });
      qc.invalidateQueries({ queryKey: accountingKeys.spendingByCategory() });
    },
  });
}

export function useDeleteExpense() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => accountingApi.deleteExpense(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: accountingKeys.expenses() });
      qc.invalidateQueries({ queryKey: accountingKeys.summary() });
      qc.invalidateQueries({ queryKey: accountingKeys.spendingByCategory() });
    },
  });
}

// Spending by category
export function useSpendingByCategory(params?: { start_date?: string; end_date?: string }) {
  return useQuery({
    queryKey: accountingKeys.spendingByCategory(params),
    queryFn: () => accountingApi.getSpendingByCategory(params),
  });
}

// Receipt extraction
export function useExtractReceipt() {
  return useMutation({
    mutationFn: (file: File) => accountingApi.extractReceipt(file),
  });
}

// Tax summary
export function useTaxSummary(taxYear?: number) {
  return useQuery({
    queryKey: accountingKeys.taxSummary(taxYear),
    queryFn: () => accountingApi.getTaxSummary(taxYear),
  });
}

// Tax estimate
export function useTaxEstimate() {
  return useQuery({
    queryKey: accountingKeys.taxEstimate(),
    queryFn: () => accountingApi.getTaxEstimate(),
  });
}

// Tax projection
export function useProjectTax() {
  return useMutation({
    mutationFn: (data: TaxProjectionRequest) => accountingApi.projectTax(data),
  });
}

// Connected accounts
export function useConnectedAccounts() {
  return useQuery({
    queryKey: accountingKeys.connectedAccounts(),
    queryFn: () => accountingApi.getConnectedAccounts(),
  });
}

export function useConnectAccount() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (publicToken: string) => accountingApi.connectAccount(publicToken),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: accountingKeys.connectedAccounts() });
    },
  });
}

// Pending transactions
export function usePendingTransactions() {
  return useQuery({
    queryKey: accountingKeys.pendingTransactions(),
    queryFn: () => accountingApi.getPendingTransactions(),
  });
}

export function useApproveTransaction() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, category }: { id: string; category: string }) =>
      accountingApi.approveTransaction(id, category),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: accountingKeys.pendingTransactions() });
      qc.invalidateQueries({ queryKey: accountingKeys.expenses() });
    },
  });
}

// Audit log
export function useAuditLog(params?: AuditLogParams) {
  return useQuery({
    queryKey: accountingKeys.auditLogList(params),
    queryFn: () => accountingApi.getAuditLog(params),
  });
}
