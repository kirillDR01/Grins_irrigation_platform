/**
 * Wraps PaymentCollector inside SheetContainer for the appointment modal.
 * Requirements: 6.2
 */

import { SheetContainer } from '@/shared/components/SheetContainer';
import { PaymentCollector } from '../PaymentCollector';

interface PaymentSheetWrapperProps {
  appointmentId: string;
  invoiceAmount?: number;
  customerPhone?: string;
  customerEmail?: string;
  onClose: () => void;
  onSuccess?: () => void;
}

export function PaymentSheetWrapper({
  appointmentId,
  invoiceAmount,
  customerPhone,
  customerEmail,
  onClose,
  onSuccess,
}: PaymentSheetWrapperProps) {
  return (
    <SheetContainer title="Collect payment" onClose={onClose}>
      <PaymentCollector
        appointmentId={appointmentId}
        invoiceAmount={invoiceAmount}
        customerPhone={customerPhone}
        customerEmail={customerEmail}
        onSuccess={() => {
          onSuccess?.();
          onClose();
        }}
      />
    </SheetContainer>
  );
}
