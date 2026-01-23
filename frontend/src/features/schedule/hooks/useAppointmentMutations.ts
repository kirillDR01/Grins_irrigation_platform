/**
 * TanStack Query mutation hooks for appointments.
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { appointmentApi } from '../api/appointmentApi';
import { appointmentKeys } from './useAppointments';
import type { AppointmentCreate, AppointmentUpdate } from '../types';

/**
 * Hook to create a new appointment.
 */
export function useCreateAppointment() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: AppointmentCreate) => appointmentApi.create(data),
    onSuccess: () => {
      // Invalidate all appointment lists and schedules
      queryClient.invalidateQueries({ queryKey: appointmentKeys.all });
    },
  });
}

/**
 * Hook to update an existing appointment.
 */
export function useUpdateAppointment() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: AppointmentUpdate }) =>
      appointmentApi.update(id, data),
    onSuccess: (_, variables) => {
      // Invalidate the specific appointment and all lists
      queryClient.invalidateQueries({
        queryKey: appointmentKeys.detail(variables.id),
      });
      queryClient.invalidateQueries({ queryKey: appointmentKeys.lists() });
      // Also invalidate daily and weekly schedules
      queryClient.invalidateQueries({
        queryKey: [...appointmentKeys.all, 'daily'],
      });
      queryClient.invalidateQueries({
        queryKey: [...appointmentKeys.all, 'weekly'],
      });
      queryClient.invalidateQueries({
        queryKey: [...appointmentKeys.all, 'staffDaily'],
      });
    },
  });
}

/**
 * Hook to cancel an appointment.
 */
export function useCancelAppointment() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => appointmentApi.cancel(id),
    onSuccess: (_, id) => {
      // Invalidate the specific appointment and all lists
      queryClient.invalidateQueries({ queryKey: appointmentKeys.detail(id) });
      queryClient.invalidateQueries({ queryKey: appointmentKeys.lists() });
      // Also invalidate daily and weekly schedules
      queryClient.invalidateQueries({
        queryKey: [...appointmentKeys.all, 'daily'],
      });
      queryClient.invalidateQueries({
        queryKey: [...appointmentKeys.all, 'weekly'],
      });
      queryClient.invalidateQueries({
        queryKey: [...appointmentKeys.all, 'staffDaily'],
      });
    },
  });
}

/**
 * Hook to confirm an appointment.
 */
export function useConfirmAppointment() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => appointmentApi.confirm(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: appointmentKeys.detail(id) });
      queryClient.invalidateQueries({ queryKey: appointmentKeys.lists() });
      queryClient.invalidateQueries({
        queryKey: [...appointmentKeys.all, 'daily'],
      });
      queryClient.invalidateQueries({
        queryKey: [...appointmentKeys.all, 'weekly'],
      });
    },
  });
}

/**
 * Hook to mark appointment as arrived (in progress).
 */
export function useMarkAppointmentArrived() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => appointmentApi.markArrived(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: appointmentKeys.detail(id) });
      queryClient.invalidateQueries({ queryKey: appointmentKeys.lists() });
      queryClient.invalidateQueries({
        queryKey: [...appointmentKeys.all, 'daily'],
      });
    },
  });
}

/**
 * Hook to mark appointment as completed.
 */
export function useMarkAppointmentCompleted() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => appointmentApi.markCompleted(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: appointmentKeys.detail(id) });
      queryClient.invalidateQueries({ queryKey: appointmentKeys.lists() });
      queryClient.invalidateQueries({
        queryKey: [...appointmentKeys.all, 'daily'],
      });
    },
  });
}

/**
 * Hook to mark appointment as no show.
 */
export function useMarkAppointmentNoShow() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => appointmentApi.markNoShow(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: appointmentKeys.detail(id) });
      queryClient.invalidateQueries({ queryKey: appointmentKeys.lists() });
      queryClient.invalidateQueries({
        queryKey: [...appointmentKeys.all, 'daily'],
      });
    },
  });
}
