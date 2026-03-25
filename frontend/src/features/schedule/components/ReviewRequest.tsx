/**
 * Google review request button (Req 34).
 * Visible only when appointment status is completed.
 */

import { Star, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { useRequestReview } from '../hooks/useAppointmentMutations';
import type { AppointmentStatus } from '../types';

interface ReviewRequestProps {
  appointmentId: string;
  status: AppointmentStatus;
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
    } catch {
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
