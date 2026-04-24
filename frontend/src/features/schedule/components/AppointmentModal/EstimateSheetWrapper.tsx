/**
 * Wraps EstimateCreator inside SheetContainer for the appointment modal.
 * Requirements: 6.3
 */

import { SheetContainer } from '@/shared/components/SheetContainer';
import { EstimateCreator } from '../EstimateCreator';

interface EstimateSheetWrapperProps {
  appointmentId: string;
  onClose: () => void;
  onSuccess?: () => void;
}

export function EstimateSheetWrapper({
  appointmentId,
  onClose,
  onSuccess,
}: EstimateSheetWrapperProps) {
  return (
    <SheetContainer title="Create estimate" onClose={onClose}>
      <EstimateCreator
        appointmentId={appointmentId}
        onSuccess={() => {
          onSuccess?.();
          onClose();
        }}
      />
    </SheetContainer>
  );
}
