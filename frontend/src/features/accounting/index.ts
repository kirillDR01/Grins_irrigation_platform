// Components
export { AccountingDashboard } from './components';
export { ExpenseTracker } from './components';
export { SpendingChart } from './components';
export { TaxPreparation } from './components';
export { TaxProjection } from './components';
export { ReceiptCapture } from './components';
export { ConnectedAccounts } from './components';
export { AuditLog } from './components';

// Hooks
export {
  accountingKeys,
  useAccountingSummary,
  usePendingInvoices,
  usePastDueInvoices,
  useExpenses,
  useCreateExpense,
  useUpdateExpense,
  useDeleteExpense,
  useSpendingByCategory,
  useExtractReceipt,
  useTaxSummary,
  useTaxEstimate,
  useProjectTax,
  useConnectedAccounts,
  useConnectAccount,
  usePendingTransactions,
  useApproveTransaction,
  useAuditLog,
} from './hooks';

// Types
export type {
  AccountingSummary,
  DateRangePreset,
  DateRangeFilter,
  InvoiceSummaryItem,
  ExpenseCategory,
  Expense,
  ExpenseCreateRequest,
  ExpenseListParams,
  SpendingByCategory,
  ReceiptExtraction,
  TaxCategorySummary,
  TaxSummary,
  TaxEstimate,
  TaxProjectionRequest,
  TaxProjectionResponse,
  ConnectedAccount,
  PendingTransaction,
  AuditLogEntry,
  AuditLogParams,
} from './types';

// API
export { accountingApi } from './api/accountingApi';
