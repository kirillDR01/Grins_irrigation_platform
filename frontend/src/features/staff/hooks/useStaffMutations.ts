/**
 * Staff mutation hooks using TanStack Query.
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { staffApi } from '../api/staffApi';
import { staffKeys } from './useStaff';
import type { StaffCreate, StaffUpdate, StaffAvailabilityUpdate } from '../types';

/**
 * Hook to create a new staff member.
 */
export function useCreateStaff() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: StaffCreate) => staffApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: staffKeys.lists() });
      queryClient.invalidateQueries({ queryKey: staffKeys.available() });
    },
  });
}

/**
 * Hook to update an existing staff member.
 */
export function useUpdateStaff() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: StaffUpdate }) =>
      staffApi.update(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: staffKeys.lists() });
      queryClient.invalidateQueries({ queryKey: staffKeys.detail(id) });
      queryClient.invalidateQueries({ queryKey: staffKeys.available() });
    },
  });
}

/**
 * Hook to delete a staff member.
 */
export function useDeleteStaff() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => staffApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: staffKeys.lists() });
      queryClient.invalidateQueries({ queryKey: staffKeys.available() });
    },
  });
}

/**
 * Hook to update staff availability.
 */
export function useUpdateStaffAvailability() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: StaffAvailabilityUpdate }) =>
      staffApi.updateAvailability(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: staffKeys.lists() });
      queryClient.invalidateQueries({ queryKey: staffKeys.detail(id) });
      queryClient.invalidateQueries({ queryKey: staffKeys.available() });
    },
  });
}
