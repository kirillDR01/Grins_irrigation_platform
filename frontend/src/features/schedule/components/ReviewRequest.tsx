/**
 * Google review request button (Req 34).
 * Visible only when appointment status is completed.
 */

import { Star, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import axios from 'axios';
import { Button } from '@/components/ui/button';
import { useRequestReview } from '../hooks/useAppointmentMutations';
import type { AppointmentStatus } from '../types';

interface ReviewRequestProps {
  appointmentId: string;
  status: AppointmentStatus;
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

export function ReviewRequest({ appointmentId, status }: ReviewRequestProps) {
  const requestReview = useRequestReview();

  if (status !== 'completed') return null;

  const handleRequest = async () => {
    try {
      const result = await requestReview.mutateAsync(appointmentId);
      if (result.already_requested) {
        toast.info('Already Requested', {
          description: 'A review request was already sent for this appointment.',
        });
      } else {
        toast.success('Review Requested', {
          description: 'Google review request sent to the customer.',
        });
      }
    } catch (error: unknown) {
      // E-BUG-F: when backend returns 409 REVIEW_ALREADY_SENT, show the
      // last-sent date instead of a generic failure.
      if (axios.isAxiosError(error) && error.response?.status === 409) {
        const detail = (error.response.data as { detail?: unknown })?.detail;
        if (detail && typeof detail === 'object' && (detail as { code?: string }).code === 'REVIEW_ALREADY_SENT') {
          const lastSent = (detail as { last_sent_at?: string }).last_sent_at;
          const dateText = lastSent ? ` (sent ${formatSentDate(lastSent)})` : '';
          toast.info('Already Requested', {
            description: `Already sent within last 30 days${dateText}`,
          });
          return;
        }
      }
      toast.error('Error', { description: 'Failed to send review request.' });
    }
  };

  return (
    <div data-testid="review-request" className="p-3 bg-slate-50 rounded-xl">
      <Button
        onClick={handleRequest}
        disabled={requestReview.isPending}
        size="sm"
        variant="outline"
        className="w-full border-amber-200 text-amber-600 hover:bg-amber-50 h-8 text-xs"
        data-testid="request-review-btn"
      >
        {requestReview.isPending ? (
          <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
        ) : (
          <Star className="mr-1.5 h-3.5 w-3.5" />
        )}
        Request Google Review
      </Button>
    </div>
  );
}
