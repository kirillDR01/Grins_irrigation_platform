/**
 * "Send All Confirmations" button at top of Schedule tab (Req 8.6, 8.7).
 * Shows count badge with number of unsent DRAFT appointments.
 * On click, shows a summary modal listing customer names and dates.
 * Modal has "Send All" and "Cancel" buttons.
 */

import { useMemo, useState } from 'react';
import { Send } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { toast } from 'sonner';
import { useBulkSendConfirmations } from '../hooks/useAppointmentMutations';
import type { Appointment } from '../types';

interface SendAllConfirmationsButtonProps {
  draftAppointments: Appointment[];
}

export function SendAllConfirmationsButton({
  draftAppointments,
}: SendAllConfirmationsButtonProps) {
  const [showModal, setShowModal] = useState(false);
  const bulkSendMutation = useBulkSendConfirmations();

  // Defensive re-filter (H-2): even though callers are expected to pre-filter
  // to DRAFTs, a caller regression must not cause the count badge / modal
  // list to disagree with the submit payload.
  const onlyDrafts = useMemo(
    () => draftAppointments.filter((a) => a.status === 'draft'),
    [draftAppointments],
  );
  const draftCount = onlyDrafts.length;

  if (draftCount === 0) return null;

  const handleSendAll = async () => {
    const ids = onlyDrafts.map((apt) => apt.id);
    try {
      const result = await bulkSendMutation.mutateAsync({ appointment_ids: ids });
      const parts: string[] = [
        `sent ${result.sent_count}`,
      ];
      if (result.deferred_count) parts.push(`deferred ${result.deferred_count}`);
      if (result.skipped_count) parts.push(`skipped ${result.skipped_count}`);
      if (result.failed_count) parts.push(`failed ${result.failed_count}`);
      const summary = parts.join(' · ');
      const anyProblem =
        (result.deferred_count ?? 0) +
          (result.skipped_count ?? 0) +
          (result.failed_count ?? 0) >
        0;
      if (anyProblem) {
        toast.warning('Bulk send finished with exceptions', { description: summary });
      } else {
        toast.success(summary);
      }
      setShowModal(false);
    } catch {
      toast.error('Failed to send confirmations');
    }
  };

  return (
    <>
      <Button
        onClick={() => setShowModal(true)}
        variant="outline"
        data-testid="send-all-confirmations-btn"
        className="border-violet-200 text-violet-600 hover:bg-violet-50 relative"
      >
        <Send className="mr-2 h-4 w-4" />
        Send All Confirmations
        <span className="ml-2 inline-flex items-center justify-center px-2 py-0.5 rounded-full text-xs font-medium bg-violet-100 text-violet-700">
          {draftCount}
        </span>
      </Button>

      <Dialog open={showModal} onOpenChange={setShowModal}>
        <DialogContent className="max-w-md" aria-describedby="send-all-description">
          <DialogHeader>
            <DialogTitle>Send All Confirmations</DialogTitle>
            <p id="send-all-description" className="text-sm text-muted-foreground">
              Send confirmation SMS to all draft appointments.
            </p>
          </DialogHeader>
          <div className="space-y-3">
            <p className="text-sm text-slate-600">
              {draftCount} draft appointment{draftCount !== 1 ? 's' : ''} will receive a confirmation SMS:
            </p>
            <div className="max-h-60 overflow-y-auto space-y-2">
              {onlyDrafts.map((apt) => (
                <div
                  key={apt.id}
                  className="flex items-center justify-between text-sm p-2 bg-slate-50 rounded"
                >
                  <span className="font-medium">{apt.customer_name || 'Customer'}</span>
                  <span className="text-slate-500">{apt.scheduled_date}</span>
                </div>
              ))}
            </div>
            <div className="flex gap-2 justify-end pt-2">
              <Button
                variant="outline"
                onClick={() => setShowModal(false)}
                data-testid="send-all-cancel-btn"
              >
                Cancel
              </Button>
              <Button
                onClick={handleSendAll}
                disabled={bulkSendMutation.isPending}
                className="bg-teal-500 hover:bg-teal-600 text-white"
                data-testid="send-all-confirm-btn"
              >
                <Send className="mr-2 h-4 w-4" />
                {bulkSendMutation.isPending ? 'Sending...' : 'Send All'}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}
