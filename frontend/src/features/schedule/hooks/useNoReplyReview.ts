/**
 * TanStack Query hooks for the no-reply review queue (bughunt H-7).
 *
 * Surfaces the nightly ``flag_no_reply_confirmations`` cron output to
 * the ``/schedule`` admin page and exposes the Send Reminder and
 * Mark Contacted mutations that resolve a flagged row.
 *
 * Validates: bughunt 2026-04-16 finding H-7.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { appointmentApi } from '../api/appointmentApi';
import { appointmentKeys } from './useAppointments';

export const noReplyReviewKeys = {
  all: ['no-reply-review'] as const,
  list: (reason?: string) =>
    [...noReplyReviewKeys.all, 'list', reason ?? null] as const,
};

/**
 * Hook to list appointments flagged by the nightly cron.
 *
 * @param params.reason Review-reason token filter. Defaults to
 *   ``no_confirmation_response`` so the default queue view only shows
 *   the H-7 bucket.
 */
export function useNoReplyReviewList(params?: { reason?: string }) {
  const reason = params?.reason ?? 'no_confirmation_response';
  return useQuery({
    queryKey: noReplyReviewKeys.list(reason),
    queryFn: () => appointmentApi.noReviewList({ reason }),
  });
}

/**
 * Hook to mark a flagged appointment as "contacted" — clears
 * ``needs_review_reason`` so the row drops off the queue.
 */
export function useMarkContacted() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (appointmentId: string) =>
      appointmentApi.markContacted(appointmentId),
    onSuccess: (_, appointmentId) => {
      qc.invalidateQueries({ queryKey: noReplyReviewKeys.all });
      qc.invalidateQueries({
        queryKey: appointmentKeys.detail(appointmentId),
      });
      qc.invalidateQueries({
        queryKey: appointmentKeys.timeline(appointmentId),
      });
    },
  });
}

/**
 * Hook to re-fire the Y/R/C confirmation SMS for a SCHEDULED
 * appointment as a reminder. The confirm dialog in
 * ``NoReplyReviewQueue`` surfaces the recipient phone before calling
 * this mutation — the safety rule on dev (only ``+19527373312`` may
 * receive real SMS) is enforced UI-side via that dialog.
 */
export function useSendReminder() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (appointmentId: string) =>
      appointmentApi.sendReminder(appointmentId),
    onSuccess: (_, appointmentId) => {
      qc.invalidateQueries({ queryKey: noReplyReviewKeys.all });
      qc.invalidateQueries({
        queryKey: appointmentKeys.timeline(appointmentId),
      });
    },
  });
}
