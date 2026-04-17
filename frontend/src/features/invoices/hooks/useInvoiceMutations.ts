import { useMutation, useQueryClient } from '@tanstack/react-query';
import { invoiceApi } from '../api/invoiceApi';
import { invoiceKeys } from './useInvoices';
// H-9: cross-query invalidation so InvoiceHistory on the customer detail
// page refreshes when an invoice is paid / voided / updated elsewhere.
import { customerInvoiceKeys } from '@/features/customers/hooks/useCustomers';
import type { InvoiceCreate, InvoiceUpdate, PaymentRecord, BulkNotifyRequest, MassNotifyRequest } from '../types';

// Create invoice
export function useCreateInvoice() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: InvoiceCreate) => invoiceApi.create(data),
    onSuccess: () => {
      // Invalidate all invoice queries to ensure fresh data everywhere
      queryClient.invalidateQueries({ queryKey: invoiceKeys.all });
      // H-9: refresh customer InvoiceHistory
      queryClient.invalidateQueries({ queryKey: customerInvoiceKeys.all });
    },
  });
}

// Update invoice
export function useUpdateInvoice() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: InvoiceUpdate }) =>
      invoiceApi.update(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: invoiceKeys.lists() });
      queryClient.invalidateQueries({ queryKey: invoiceKeys.detail(id) });
      // H-9: refresh customer InvoiceHistory
      queryClient.invalidateQueries({ queryKey: customerInvoiceKeys.all });
    },
  });
}

// Cancel invoice
export function useCancelInvoice() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => invoiceApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: invoiceKeys.lists() });
      // H-9: refresh customer InvoiceHistory
      queryClient.invalidateQueries({ queryKey: customerInvoiceKeys.all });
    },
  });
}

// Send invoice
export function useSendInvoice() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => invoiceApi.send(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: invoiceKeys.lists() });
      queryClient.invalidateQueries({ queryKey: invoiceKeys.detail(id) });
      // H-9: refresh customer InvoiceHistory
      queryClient.invalidateQueries({ queryKey: customerInvoiceKeys.all });
    },
  });
}

// Record payment
export function useRecordPayment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: PaymentRecord }) =>
      invoiceApi.recordPayment(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: invoiceKeys.lists() });
      queryClient.invalidateQueries({ queryKey: invoiceKeys.detail(id) });
      queryClient.invalidateQueries({ queryKey: invoiceKeys.overdue() });
      // H-9: refresh customer InvoiceHistory (this is the "mark paid" path)
      queryClient.invalidateQueries({ queryKey: customerInvoiceKeys.all });
    },
  });
}

// Send reminder
export function useSendReminder() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => invoiceApi.sendReminder(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: invoiceKeys.detail(id) });
      // H-9: refresh customer InvoiceHistory (reminder_count changed)
      queryClient.invalidateQueries({ queryKey: customerInvoiceKeys.all });
    },
  });
}

// Send lien warning
export function useSendLienWarning() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => invoiceApi.sendLienWarning(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: invoiceKeys.lists() });
      queryClient.invalidateQueries({ queryKey: invoiceKeys.detail(id) });
      queryClient.invalidateQueries({ queryKey: invoiceKeys.lienDeadlines() });
      // H-9: refresh customer InvoiceHistory
      queryClient.invalidateQueries({ queryKey: customerInvoiceKeys.all });
    },
  });
}

// Mark lien filed
export function useMarkLienFiled() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, filingDate }: { id: string; filingDate: string }) =>
      invoiceApi.markLienFiled(id, filingDate),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: invoiceKeys.lists() });
      queryClient.invalidateQueries({ queryKey: invoiceKeys.detail(id) });
      queryClient.invalidateQueries({ queryKey: invoiceKeys.lienDeadlines() });
      // H-9: refresh customer InvoiceHistory
      queryClient.invalidateQueries({ queryKey: customerInvoiceKeys.all });
    },
  });
}

// Generate invoice from job
export function useGenerateInvoiceFromJob() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (jobId: string) => invoiceApi.generateFromJob(jobId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: invoiceKeys.lists() });
      // H-9: refresh customer InvoiceHistory
      queryClient.invalidateQueries({ queryKey: customerInvoiceKeys.all });
    },
  });
}

// Bulk notify customers (Req 38)
export function useBulkNotify() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: BulkNotifyRequest) => invoiceApi.bulkNotify(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: invoiceKeys.lists() });
      // H-9: refresh customer InvoiceHistory
      queryClient.invalidateQueries({ queryKey: customerInvoiceKeys.all });
    },
  });
}

// Mass notify customers (Req 29.3, 29.4)
export function useMassNotify() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: MassNotifyRequest) => invoiceApi.massNotify(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: invoiceKeys.lists() });
      // H-9: refresh customer InvoiceHistory
      queryClient.invalidateQueries({ queryKey: customerInvoiceKeys.all });
    },
  });
}

// Generate PDF for an invoice (Req 80)
export function useGeneratePdf() {
  return useMutation({
    mutationFn: (id: string) => invoiceApi.generatePdf(id),
  });
}

// Get PDF download URL (Req 80)
export function useGetPdfUrl() {
  return useMutation({
    mutationFn: (id: string) => invoiceApi.getPdfUrl(id),
  });
}
