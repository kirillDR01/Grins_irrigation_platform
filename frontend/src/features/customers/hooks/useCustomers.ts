import { useQuery } from '@tanstack/react-query';
import { customerApi } from '../api/customerApi';
import type { CustomerListParams } from '../types';

// Query key factory
export const customerKeys = {
  all: ['customers'] as const,
  lists: () => [...customerKeys.all, 'list'] as const,
  list: (params?: CustomerListParams) => [...customerKeys.lists(), params] as const,
  details: () => [...customerKeys.all, 'detail'] as const,
  detail: (id: string) => [...customerKeys.details(), id] as const,
  search: (query: string) => [...customerKeys.all, 'search', query] as const,
  photos: (id: string) => [...customerKeys.all, id, 'photos'] as const,
  invoices: (id: string, params?: { page?: number; page_size?: number }) =>
    [...customerKeys.all, id, 'invoices', params] as const,
  paymentMethods: (id: string) => [...customerKeys.all, id, 'payment-methods'] as const,
  duplicates: (id: string) => [...customerKeys.all, id, 'duplicates'] as const,
  duplicateReviewQueue: (skip: number, limit: number) =>
    [...customerKeys.all, 'duplicate-review-queue', skip, limit] as const,
  sentMessages: (id: string) => [...customerKeys.all, id, 'sent-messages'] as const,
  servicePreferences: (id: string) => [...customerKeys.all, id, 'service-preferences'] as const,
};

// H-9: Cross-query invalidation key factory for the customer-detail invoice
// history. Invoice mutation hooks (useUpdateInvoice, useRecordPayment, etc.)
// import `customerInvoiceKeys` and invalidate `customerInvoiceKeys.all`
// in their onSuccess handlers so InvoiceHistory reflects paid/voided/updated
// invoices without a manual refresh.
export const customerInvoiceKeys = {
  all: ['customer-invoices'] as const,
  byCustomer: (customerId: string) =>
    [...customerInvoiceKeys.all, customerId] as const,
};

// List customers with pagination and filters
export function useCustomers(params?: CustomerListParams) {
  return useQuery({
    queryKey: customerKeys.list(params),
    queryFn: () => customerApi.list(params),
  });
}

// Get single customer by ID
export function useCustomer(id: string) {
  return useQuery({
    queryKey: customerKeys.detail(id),
    queryFn: () => customerApi.get(id),
    enabled: !!id,
  });
}

// Search customers with debounced query
export function useCustomerSearch(query: string) {
  return useQuery({
    queryKey: customerKeys.search(query),
    queryFn: () => customerApi.search(query),
    enabled: query.length >= 2,
  });
}

// Customer photos (Req 9)
export function useCustomerPhotos(customerId: string) {
  return useQuery({
    queryKey: customerKeys.photos(customerId),
    queryFn: () => customerApi.listPhotos(customerId),
    enabled: !!customerId,
  });
}

// Customer invoices (Req 10, Req 29.5, H-9 — real-time refresh)
// Two-layer freshness strategy:
//   1. `refetchInterval: 30_000` polling safety-net (this hook).
//   2. Cross-query invalidation from invoice mutation hooks via
//      `customerInvoiceKeys.all` (see useInvoiceMutations.ts).
// The query key includes BOTH the precise `customerKeys.invoices(...)` tuple
// AND the coarse `customerInvoiceKeys.byCustomer(customerId)` tuple so mutations
// can invalidate by either factory.
export function useCustomerInvoices(
  customerId: string,
  params?: { page?: number; page_size?: number },
  options?: { refetchInterval?: number | false; enabled?: boolean }
) {
  return useQuery({
    queryKey: [
      ...customerKeys.invoices(customerId, params),
      ...customerInvoiceKeys.byCustomer(customerId),
    ],
    queryFn: () => customerApi.listInvoices(customerId, params),
    enabled: !!customerId,
    refetchInterval: 30_000, // H-9: poll every 30s for real-time invoice state changes
    ...(options ?? {}),
  });
}

// Customer payment methods (Req 56)
export function useCustomerPaymentMethods(customerId: string) {
  return useQuery({
    queryKey: customerKeys.paymentMethods(customerId),
    queryFn: () => customerApi.listPaymentMethods(customerId),
    enabled: !!customerId,
  });
}

// Customer duplicates (Req 7)
export function useCustomerDuplicates(customerId: string) {
  return useQuery({
    queryKey: customerKeys.duplicates(customerId),
    queryFn: () => customerApi.getDuplicates(customerId),
    enabled: !!customerId,
  });
}

// Paginated duplicate review queue (CRM Changes Update 2 Req 5, 6)
export function useDuplicateReviewQueue(skip = 0, limit = 20) {
  return useQuery({
    queryKey: customerKeys.duplicateReviewQueue(skip, limit),
    queryFn: () => customerApi.getDuplicateReviewQueue(skip, limit),
  });
}

// Customer sent messages (Req 82)
export function useCustomerSentMessages(customerId: string) {
  return useQuery({
    queryKey: customerKeys.sentMessages(customerId),
    queryFn: () => customerApi.listSentMessages(customerId),
    enabled: !!customerId,
  });
}

// Customer service preferences (CRM2 Req 7)
export function useServicePreferences(customerId: string) {
  return useQuery({
    queryKey: customerKeys.servicePreferences(customerId),
    queryFn: () => customerApi.listServicePreferences(customerId),
    enabled: !!customerId,
  });
}
