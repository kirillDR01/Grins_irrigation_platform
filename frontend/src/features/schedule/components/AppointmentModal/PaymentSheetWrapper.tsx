/**
 * Wraps PaymentCollector inside SheetContainer for the appointment modal.
 *
 * Props pass-through includes invoice/lead/service-agreement context so
 * the collector can render the right CTA (plan §Phase 3).
 *
 * Requirements: 6.2
 */

import { SheetContainer } from '@/shared/components/SheetContainer';
import { PaymentCollector } from '../PaymentCollector';

interface PaymentSheetWrapperProps {
  appointmentId: string;
  jobId?: string;
  invoiceAmount?: number | string;
  customerPhone?: string | null;
  customerEmail?: string | null;
  customerExists?: boolean;
  serviceAgreementActive?: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

export function PaymentSheetWrapper({
  appointmentId,
  jobId,
  invoiceAmount,
  customerPhone,
  customerEmail,
  customerExists = true,
  serviceAgreementActive = false,
  onClose,
  onSuccess,
}: PaymentSheetWrapperProps) {
  return (
    <SheetContainer title="Collect payment" onClose={onClose}>
      <PaymentCollector
        appointmentId={appointmentId}
        jobId={jobId}
        invoiceAmount={invoiceAmount}
        customerPhone={customerPhone}
        customerEmail={customerEmail}
        customerExists={customerExists}
        serviceAgreementActive={serviceAgreementActive}
        onSuccess={() => {
          onSuccess?.();
          onClose();
        }}
      />
    </SheetContainer>
  );
}
