/**
 * On-site estimate creation from appointment context (Req 32).
 *
 * Thin wrapper around ``EstimateForm`` that injects the appointment-side
 * mutation. The Sales Pipeline mounts the same form via
 * ``SalesEstimateCreator``.
 */

import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import type { CustomerType } from '@/features/pricelist';
import { useCreateEstimateFromAppointment } from '../hooks/useAppointmentMutations';
import { EstimateForm, type EstimateFormSubmitData } from './EstimateForm';

interface EstimateCreatorProps {
  appointmentId: string;
  onSuccess?: () => void;
  /**
   * Optional resolved customer type for the picker pre-filter.
   * Phase 3 / P4-RESOLVED — caller decides via lead.customer_type
   * → property.property_type → fallback. Defaults to ``residential``
   * with the override toggle inside the picker.
   */
  customerType?: CustomerType;
}

export function EstimateCreator({
  appointmentId,
  onSuccess,
  customerType,
}: EstimateCreatorProps) {
  const createEstimate = useCreateEstimateFromAppointment();
  const navigate = useNavigate();

  const handleSubmit = async (data: EstimateFormSubmitData) => {
    try {
      const result = await createEstimate.mutateAsync({
        id: appointmentId,
        data: {
          template_id: data.template_id,
          line_items: data.line_items,
          notes: data.notes,
        },
      });
      toast.success('Estimate Created', {
        description: 'Estimate has been sent to the customer.',
        action: {
          label: 'View Details',
          onClick: () => navigate(`/estimates/${result.id}`),
        },
      });
      onSuccess?.();
    } catch {
      toast.error('Error', { description: 'Failed to create estimate.' });
    }
  };

  return (
    <EstimateForm
      customerType={customerType}
      onSubmit={handleSubmit}
      submitting={createEstimate.isPending}
    />
  );
}
