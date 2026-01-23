/**
 * Staff query hooks using TanStack Query.
 */

import { useQuery } from '@tanstack/react-query';
import { staffApi } from '../api/staffApi';
import type { StaffListParams } from '../types';

/**
 * Query key factory for staff queries.
 */
export const staffKeys = {
  all: ['staff'] as const,
  lists: () => [...staffKeys.all, 'list'] as const,
  list: (params?: StaffListParams) => [...staffKeys.lists(), params] as const,
  details: () => [...staffKeys.all, 'detail'] as const,
  detail: (id: string) => [...staffKeys.details(), id] as const,
  available: () => [...staffKeys.all, 'available'] as const,
};

/**
 * Hook to fetch paginated staff list.
 */
export function useStaff(params?: StaffListParams) {
  return useQuery({
    queryKey: staffKeys.list(params),
    queryFn: () => staffApi.list(params),
  });
}

/**
 * Hook to fetch a single staff member.
 */
export function useStaffMember(id: string | undefined) {
  return useQuery({
    queryKey: staffKeys.detail(id ?? ''),
    queryFn: () => staffApi.getById(id!),
    enabled: !!id,
  });
}

/**
 * Hook to fetch available staff members.
 */
export function useAvailableStaff() {
  return useQuery({
    queryKey: staffKeys.available(),
    queryFn: staffApi.getAvailable,
  });
}
