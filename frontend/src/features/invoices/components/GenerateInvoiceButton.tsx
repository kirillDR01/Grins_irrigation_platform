import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FileText, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';
import { invoiceApi } from '../api/invoiceApi';
import type { Job } from '@/features/jobs/types';

interface GenerateInvoiceButtonProps {
  job: Job;
  onSuccess?: (invoiceId: string) => void;
}

/**
 * Button to generate an invoice from a completed job.
 * Only visible when payment_collected_on_site is false.
 */
export function GenerateInvoiceButton({ job, onSuccess }: GenerateInvoiceButtonProps) {
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();

  // Don't show if payment was collected on site
  if (job.payment_collected_on_site) {
    return null;
  }

  // Only show for completed or closed jobs
  if (!['completed', 'closed'].includes(job.status)) {
    return null;
  }

  const handleGenerateInvoice = async () => {
    setIsLoading(true);
    try {
      const invoice = await invoiceApi.generateFromJob(job.id);
      toast.success('Invoice Generated', {
        description: `Invoice ${invoice.invoice_number} has been created.`,
      });
      if (onSuccess) {
        onSuccess(invoice.id);
      } else {
        navigate(`/invoices/${invoice.id}`);
      }
    } catch (error) {
      toast.error('Error', {
        description: error instanceof Error ? error.message : 'Failed to generate invoice',
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Button
      onClick={handleGenerateInvoice}
      disabled={isLoading}
      data-testid="generate-invoice-btn"
      className="bg-teal-500 hover:bg-teal-600 text-white px-5 py-2.5 rounded-lg shadow-sm shadow-teal-200 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
    >
      {isLoading ? (
        <>
          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          <span>Generating...</span>
        </>
      ) : (
        <>
          <FileText className="mr-2 h-4 w-4" />
          <span>Generate Invoice</span>
        </>
      )}
    </Button>
  );
}
