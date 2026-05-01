/**
 * Reassign an appointment to a different staff member (drag-drop in the
 * resource-timeline view). Thin wrapper around `useUpdateAppointment`
 * that surfaces a specific `toast.error` on the BE's 409 staff-conflict
 * guard so the dispatcher knows the slot is already booked.
 *
 * The underlying PATCH `/appointments/{id}` already handles the cache
 * invalidation fan-out (daily / weekly / staffDaily / lists / detail).
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';
import type { AxiosError } from 'axios';
import { toast } from 'sonner';
import { appointmentApi } from '../api/appointmentApi';
import { appointmentKeys } from './useAppointments';

export interface ReassignAppointmentInput {
  id: string;
  /** New staff member to take over the appointment. */
  staffId: string;
  /** Optional new date for combined reassign+reschedule. */
  scheduledDate?: string;
}

function isHttpStatus(error: unknown, status: number): boolean {
  const axiosErr = error as AxiosError | undefined;
  return axiosErr?.response?.status === status;
}

export function useReassignAppointment() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, staffId, scheduledDate }: ReassignAppointmentInput) =>
      appointmentApi.update(id, {
        staff_id: staffId,
        ...(scheduledDate ? { scheduled_date: scheduledDate } : {}),
      }),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({
        queryKey: appointmentKeys.detail(variables.id),
      });
      queryClient.invalidateQueries({ queryKey: appointmentKeys.lists() });
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
    onError: (error: unknown) => {
      if (isHttpStatus(error, 409)) {
        toast.error(
          'Scheduling conflict — that tech is already booked at that time'
        );
        return;
      }
      const message =
        error instanceof Error ? error.message : 'Failed to reassign';
      toast.error(`Failed to reassign: ${message}`);
    },
  });
}
