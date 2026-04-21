/**
 * Per-appointment "Send Confirmation" icon button for draft appointment cards (Req 8.4).
 * Small send icon that appears on DRAFT appointment cards in the calendar.
 * On click, calls POST /api/v1/appointments/{id}/send-confirmation.
 *
 * The button disables itself with a "Confirmation already sent" tooltip
 * whenever ``appointment.status !== 'draft'`` (H-8). The backend rejects
 * non-DRAFT with a 422; disabling client-side prevents the user from
 * clicking, getting a toast error, and having to figure out why.
 */

import { Send } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';
import { useSendConfirmation } from '../hooks/useAppointmentMutations';
import { useCustomerConsentStatus } from '@/features/customers/hooks/useConsentStatus';
import type { Appointment } from '../types';

interface SendConfirmationButtonProps {
  appointment: Appointment;
  /** Compact mode for inline calendar card display */
  compact?: boolean;
  /** Customer id enables Gap 06 opt-out-aware disable + tooltip. */
  customerId?: string | null;
}

export function SendConfirmationButton({
  appointment,
  compact = false,
  customerId,
}: SendConfirmationButtonProps) {
  const sendMutation = useSendConfirmation();
  const isDraft = appointment.status === 'draft';
  const customerName = appointment.customer_name || 'customer';
  const { data: consentStatus } = useCustomerConsentStatus(customerId);
  const isOptedOut = consentStatus?.is_opted_out === true;
  const tooltip = isOptedOut
    ? 'Customer has opted out of SMS — confirmation blocked'
    : isDraft
      ? `Send confirmation SMS to ${customerName}`
      : 'Confirmation already sent';
  const disabled = sendMutation.isPending || !isDraft || isOptedOut;

  const handleClick = async (e: React.MouseEvent) => {
    e.stopPropagation(); // Prevent event click from opening detail modal
    try {
      await sendMutation.mutateAsync(appointment.id);
      toast.success('Confirmation sent');
    } catch {
      toast.error('Failed to send confirmation');
    }
  };

  if (compact) {
    return (
      <button
        onClick={handleClick}
        disabled={disabled}
        className="inline-flex items-center justify-center w-5 h-5 rounded bg-teal-500/80 hover:bg-teal-600 text-white transition-colors disabled:opacity-50"
        title={tooltip}
        aria-label={tooltip}
        data-testid={`send-confirmation-icon-${appointment.id}`}
      >
        <Send className="h-3 w-3" />
      </button>
    );
  }

  return (
    <Button
      onClick={handleClick}
      disabled={disabled}
      size="sm"
      className="bg-teal-500 hover:bg-teal-600 text-white h-7 text-xs px-2"
      title={tooltip}
      aria-label={tooltip}
      data-testid={`send-confirmation-btn-${appointment.id}`}
    >
      <Send className="mr-1 h-3 w-3" />
      {sendMutation.isPending ? 'Sending...' : 'Send'}
    </Button>
  );
}
