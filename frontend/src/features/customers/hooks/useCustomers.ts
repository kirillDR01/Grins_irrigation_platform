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
  sentMessages: (id: string) => [...customerKeys.all, id, 'sent-messages'] as const,
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

// Customer invoices (Req 10)
export function useCustomerInvoices(
  customerId: string,
  params?: { page?: number; page_size?: number }
) {
  return useQuery({
    queryKey: customerKeys.invoices(customerId, params),
    queryFn: () => customerApi.listInvoices(customerId, params),
    enabled: !!customerId,
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

// Customer sent messages (Req 82)
export function useCustomerSentMessages(customerId: string) {
  return useQuery({
    queryKey: customerKeys.sentMessages(customerId),
    queryFn: () => customerApi.listSentMessages(customerId),
    enabled: !!customerId,
  });
}
