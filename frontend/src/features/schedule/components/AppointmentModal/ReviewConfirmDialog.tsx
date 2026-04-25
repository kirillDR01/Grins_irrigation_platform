/**
 * ReviewConfirmDialog — confirm-and-send dialog for the Send Review Request action.
 *
 * Stacks on top of AppointmentModal. Sends the Google review SMS via
 * `useRequestReview` and surfaces the existing 30-day-dedup 409 (REVIEW_ALREADY_SENT)
 * with an "Already Requested" info toast carrying the prior send date.
 */

import { Loader2, Star } from 'lucide-react';
import { toast } from 'sonner';
import axios from 'axios';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { useRequestReview } from '../../hooks/useAppointmentMutations';

interface ReviewConfirmDialogProps {
  appointmentId: string;
  customerName: string;
  customerPhone: string | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

function formatSentDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

export function ReviewConfirmDialog({
  appointmentId,
  customerName,
  customerPhone,
  open,
  onOpenChange,
}: ReviewConfirmDialogProps) {
  const requestReview = useRequestReview();

  const handleSend = async () => {
    try {
      await requestReview.mutateAsync(appointmentId);
      toast.success('Review Requested', {
        description: 'Google review request sent to the customer.',
      });
      onOpenChange(false);
    } catch (error: unknown) {
      if (axios.isAxiosError(error) && error.response?.status === 409) {
        const detail = (error.response.data as { detail?: unknown })?.detail;
        if (
          detail &&
          typeof detail === 'object' &&
          (detail as { code?: string }).code === 'REVIEW_ALREADY_SENT'
        ) {
          const lastSent = (detail as { last_sent_at?: string }).last_sent_at;
          const dateText = lastSent ? ` (sent ${formatSentDate(lastSent)})` : '';
          toast.info('Already Requested', {
            description: `Already sent within last 30 days${dateText}`,
          });
          onOpenChange(false);
          return;
        }
      }
      toast.error('Error', { description: 'Failed to send review request.' });
    }
  };

  const phoneDisplay = customerPhone ?? 'no phone on file';

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent data-testid="review-confirm-dialog" className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Send Google review request?</DialogTitle>
          <DialogDescription>
            Send Google review SMS to {customerName} at {phoneDisplay}?
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button
            variant="ghost"
            onClick={() => onOpenChange(false)}
            disabled={requestReview.isPending}
            data-testid="cancel-review-btn"
          >
            Cancel
          </Button>
          <Button
            onClick={handleSend}
            disabled={requestReview.isPending || !customerPhone}
            className="bg-[#0B1220] text-white hover:bg-[#0B1220]/90"
            data-testid="send-review-btn"
          >
            {requestReview.isPending ? (
              <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
            ) : (
              <Star className="mr-1.5 h-3.5 w-3.5" />
            )}
            Send
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
