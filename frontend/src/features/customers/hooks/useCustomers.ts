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
