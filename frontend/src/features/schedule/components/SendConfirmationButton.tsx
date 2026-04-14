/**
 * Per-appointment "Send Confirmation" icon button for draft appointment cards (Req 8.4).
 * Small send icon that appears on DRAFT appointment cards in the calendar.
 * On click, calls POST /api/v1/appointments/{id}/send-confirmation.
 */

import { Send } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';
import { useSendConfirmation } from '../hooks/useAppointmentMutations';

interface SendConfirmationButtonProps {
  appointmentId: string;
  /** Compact mode for inline calendar card display */
  compact?: boolean;
}

export function SendConfirmationButton({
  appointmentId,
  compact = false,
}: SendConfirmationButtonProps) {
  const sendMutation = useSendConfirmation();

  const handleClick = async (e: React.MouseEvent) => {
    e.stopPropagation(); // Prevent event click from opening detail modal
    try {
      await sendMutation.mutateAsync(appointmentId);
      toast.success('Confirmation sent');
    } catch {
      toast.error('Failed to send confirmation');
    }
  };

  if (compact) {
    return (
      <button
        onClick={handleClick}
        disabled={sendMutation.isPending}
        className="inline-flex items-center justify-center w-5 h-5 rounded bg-teal-500/80 hover:bg-teal-600 text-white transition-colors disabled:opacity-50"
        title="Send Confirmation"
        data-testid={`send-confirmation-icon-${appointmentId}`}
      >
        <Send className="h-3 w-3" />
      </button>
    );
  }

  return (
    <Button
      onClick={handleClick}
      disabled={sendMutation.isPending}
      size="sm"
      className="bg-teal-500 hover:bg-teal-600 text-white h-7 text-xs px-2"
      data-testid={`send-confirmation-btn-${appointmentId}`}
    >
      <Send className="mr-1 h-3 w-3" />
      {sendMutation.isPending ? 'Sending...' : 'Send'}
    </Button>
  );
}
