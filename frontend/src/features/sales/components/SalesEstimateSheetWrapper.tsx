/**
 * Wraps SalesEstimateCreator inside SheetContainer for the
 * Sales Pipeline ``send_estimate`` stage.
 */

import { SheetContainer } from '@/shared/components/SheetContainer';
import type { CustomerType } from '@/features/pricelist';
import { SalesEstimateCreator } from './SalesEstimateCreator';

interface SalesEstimateSheetWrapperProps {
  entryId: string;
  onClose: () => void;
  onSuccess?: () => void;
  customerType?: CustomerType;
}

export function SalesEstimateSheetWrapper({
  entryId,
  onClose,
  onSuccess,
  customerType,
}: SalesEstimateSheetWrapperProps) {
  return (
    <SheetContainer title="Build & send estimate" onClose={onClose}>
      <SalesEstimateCreator
        entryId={entryId}
        customerType={customerType}
        onSuccess={() => {
          onSuccess?.();
          onClose();
        }}
      />
    </SheetContainer>
  );
}
