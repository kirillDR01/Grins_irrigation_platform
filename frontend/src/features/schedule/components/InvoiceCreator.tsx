/**
 * On-site invoice creation from appointment (Req 31).
 * Pre-populates from job/customer data.
 */

import { FileText, Loader2, Send } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { useCreateInvoiceFromAppointment } from '../hooks/useAppointmentMutations';

interface InvoiceCreatorProps {
  appointmentId: string;
  customerName?: string | null;
  jobType?: string | null;
  onSuccess?: () => void;
}

export function InvoiceCreator({
  appointmentId,
  customerName,
  jobType,
  onSuccess,
}: InvoiceCreatorProps) {
  const createInvoice = useCreateInvoiceFromAppointment();

  const handleCreate = async () => {
    try {
      const result = await createInvoice.mutateAsync(appointmentId);
      toast.success('Invoice Created', {
        description: `Invoice #${result.invoice_number} for $${result.total_amount.toFixed(2)} has been sent.`,
      });
      onSuccess?.();
    } catch {
      toast.error('Error', { description: 'Failed to create invoice.' });
    }
  };

  return (
    <div data-testid="invoice-creator" className="space-y-2 p-3 bg-slate-50 rounded-xl">
      <div className="flex items-center gap-2 mb-1">
        <FileText className="h-3.5 w-3.5 text-slate-400" />
        <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">
          Create Invoice
        </p>
      </div>

      <div className="text-xs text-slate-600 space-y-0.5">
        {customerName && <p>Customer: <span className="font-medium">{customerName}</span></p>}
        {jobType && <p>Service: <span className="font-medium">{jobType}</span></p>}
      </div>

      <Button
        onClick={handleCreate}
        disabled={createInvoice.isPending}
        size="sm"
        className="w-full bg-violet-500 hover:bg-violet-600 text-white min-h-[48px] text-sm md:min-h-0 md:h-8 md:text-xs"
        data-testid="create-invoice-btn"
      >
        {createInvoice.isPending ? (
          <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
        ) : (
          <Send className="mr-1.5 h-3.5 w-3.5" />
        )}
        Create &amp; Send Invoice
      </Button>
    </div>
  );
}
