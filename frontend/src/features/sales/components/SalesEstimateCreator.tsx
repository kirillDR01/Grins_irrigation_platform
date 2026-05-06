/**
 * Sales-pipeline-side estimate creator. Mounts the shared
 * ``EstimateForm`` and routes submission through the
 * ``send-estimate`` orchestrator endpoint, which creates +
 * sends the estimate and advances the SalesEntry to
 * ``pending_approval`` atomically.
 */

import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { getErrorMessage } from '@/core/api';
import type { CustomerType } from '@/features/pricelist';
import {
  EstimateForm,
  type EstimateFormSubmitData,
} from '@/features/schedule/components/EstimateForm';
import { useSendEstimateFromSalesEntry } from '../hooks/useSalesPipeline';

interface SalesEstimateCreatorProps {
  entryId: string;
  onSuccess?: () => void;
  customerType?: CustomerType;
}

export function SalesEstimateCreator({
  entryId,
  onSuccess,
  customerType,
}: SalesEstimateCreatorProps) {
  const sendEstimate = useSendEstimateFromSalesEntry();
  const navigate = useNavigate();

  const handleSubmit = async (data: EstimateFormSubmitData) => {
    const subtotal = data.line_items.reduce(
      (sum, li) => sum + li.unit_price * li.quantity,
      0,
    );
    try {
      const result = await sendEstimate.mutateAsync({
        entryId,
        data: {
          template_id: data.template_id,
          line_items: data.line_items,
          notes: data.notes,
          subtotal,
          total: subtotal,
        },
      });
      toast.success('Estimate sent', {
        description: 'Customer received SMS + email with the portal link.',
        action: {
          label: 'View Estimate',
          onClick: () => navigate(`/estimates/${result.estimate_id}`),
        },
      });
      onSuccess?.();
    } catch (err) {
      toast.error('Failed to send estimate', {
        description: getErrorMessage(err),
      });
    }
  };

  return (
    <EstimateForm
      customerType={customerType}
      onSubmit={handleSubmit}
      submitting={sendEstimate.isPending}
    />
  );
}
