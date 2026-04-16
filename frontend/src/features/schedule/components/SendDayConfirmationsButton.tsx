/**
 * "Send Confirmations for [Day]" button on each day column header (Req 8.5).
 * Appears when there are DRAFT appointments on that day.
 * On click, calls the bulk endpoint with the date range for that day.
 * Shows count of DRAFT appointments as a badge.
 */

import { useMemo } from 'react';
import { Send } from 'lucide-react';
import { toast } from 'sonner';
import { useBulkSendConfirmations } from '../hooks/useAppointmentMutations';
import type { Appointment } from '../types';

interface SendDayConfirmationsButtonProps {
  date: string; // YYYY-MM-DD
  draftAppointments: Appointment[];
}

export function SendDayConfirmationsButton({
  date,
  draftAppointments,
}: SendDayConfirmationsButtonProps) {
  const bulkSendMutation = useBulkSendConfirmations();

  // Defensive re-filter (H-2): callers are expected to pre-filter to DRAFTs,
  // but this component re-filters so the count badge and submit payload
  // always agree even if a caller regresses.
  const onlyDrafts = useMemo(
    () => draftAppointments.filter((a) => a.status === 'draft'),
    [draftAppointments],
  );
  const draftCount = onlyDrafts.length;

  if (draftCount === 0) return null;

  const handleClick = async (e: React.MouseEvent) => {
    e.stopPropagation();
    const draftAppointmentIds = onlyDrafts.map((apt) => apt.id);
    try {
      const result = await bulkSendMutation.mutateAsync({
        appointment_ids: draftAppointmentIds,
        date_from: date,
        date_to: date,
      });
      const exceptionCount =
        (result.deferred_count ?? 0) +
        (result.skipped_count ?? 0) +
        (result.failed_count ?? 0);
      const summaryParts: string[] = [`sent ${result.sent_count}`];
      if (result.deferred_count) summaryParts.push(`deferred ${result.deferred_count}`);
      if (result.skipped_count) summaryParts.push(`skipped ${result.skipped_count}`);
      if (result.failed_count) summaryParts.push(`failed ${result.failed_count}`);
      const summary = `${summaryParts.join(' · ')} for ${date}`;
      if (exceptionCount > 0) {
        toast.warning('Bulk send finished with exceptions', { description: summary });
      } else {
        toast.success(summary);
      }
    } catch {
      toast.error('Failed to send confirmations');
    }
  };

  return (
    <button
      onClick={handleClick}
      disabled={bulkSendMutation.isPending}
      className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium bg-violet-100 text-violet-700 hover:bg-violet-200 transition-colors disabled:opacity-50"
      title={`Send ${draftCount} confirmation${draftCount !== 1 ? 's' : ''} for this day`}
      data-testid={`send-day-confirmations-${date}`}
    >
      <Send className="h-2.5 w-2.5" />
      {draftCount}
    </button>
  );
}
