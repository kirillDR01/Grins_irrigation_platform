import { useQuery } from '@tanstack/react-query';
import { invoiceApi } from '../api/invoiceApi';
import type { InvoiceListParams } from '../types';

// Query key factory
export const invoiceKeys = {
  all: ['invoices'] as const,
  lists: () => [...invoiceKeys.all, 'list'] as const,
  list: (params?: InvoiceListParams) => [...invoiceKeys.lists(), params] as const,
  details: () => [...invoiceKeys.all, 'detail'] as const,
  detail: (id: string) => [...invoiceKeys.details(), id] as const,
  byJob: (jobId: string) => [...invoiceKeys.all, 'by-job', jobId] as const,
  overdue: (params?: InvoiceListParams) => [...invoiceKeys.all, 'overdue', params] as const,
  lienDeadlines: () => [...invoiceKeys.all, 'lien-deadlines'] as const,
};

// List invoices with pagination and filters
export function useInvoices(params?: InvoiceListParams) {
  return useQuery({
    queryKey: invoiceKeys.list(params),
    queryFn: () => invoiceApi.list(params),
  });
}

// Get single invoice by ID
export function useInvoice(id: string) {
  return useQuery({
    queryKey: invoiceKeys.detail(id),
    queryFn: () => invoiceApi.get(id),
    enabled: !!id,
  });
}

// Get overdue invoices
export function useOverdueInvoices(params?: InvoiceListParams) {
  return useQuery({
    queryKey: invoiceKeys.overdue(params),
    queryFn: () => invoiceApi.getOverdue(params),
  });
}

// Get lien deadlines
export function useLienDeadlines() {
  return useQuery({
    queryKey: invoiceKeys.lienDeadlines(),
    queryFn: () => invoiceApi.getLienDeadlines(),
  });
}

// Get invoices by job ID
export function useInvoicesByJob(jobId: string) {
  return useQuery({
    queryKey: invoiceKeys.byJob(jobId),
    queryFn: async () => {
      const response = await invoiceApi.list({ job_id: jobId } as InvoiceListParams);
      return response.items;
    },
    enabled: !!jobId,
  });
}
