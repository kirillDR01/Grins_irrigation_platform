/**
 * React Query hook for the appointment communication timeline (Gap 11).
 */

import { useQuery } from '@tanstack/react-query';
import { appointmentApi } from '../api/appointmentApi';
import { appointmentKeys } from './useAppointments';

/**
 * Fetch the chronological communication timeline for an appointment.
 *
 * Stale time set to 30s so the panel does not refetch on every tab focus
 * while an admin is reading. Mutations that change communication state
 * (confirm, cancel, mark-contacted, send-reminder, resolve-reschedule)
 * invalidate the key manually.
 */
export function useAppointmentTimeline(id: string | undefined) {
  return useQuery({
    queryKey: appointmentKeys.timeline(id ?? ''),
    queryFn: () => appointmentApi.getTimeline(id!),
    enabled: !!id,
    staleTime: 30_000,
  });
}
