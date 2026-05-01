/**
 * PaidConfirmationCard — green confirmation card surfaced inside the
 * appointment payment sheet when a payment has been collected.
 *
 * Replaces the live PaymentCollector inputs once a payment lands.
 * "Text receipt" CTA re-fires the receipt SMS to the customer.
 *
 * Umbrella plan §Phase 4.4 / design ref §8.5.
 */

import { CheckCircle2, MessageSquare } from 'lucide-react';

interface PaidConfirmationCardProps {
  amountPaid: number | string;
  paymentMethod: string;
  paymentReference?: string | null;
  paidAt?: string | Date | null;
  onTextReceipt?: () => void;
  textReceiptPending?: boolean;
}

const METHOD_LABELS: Record<string, string> = {
  cash: 'Cash',
  check: 'Check',
  venmo: 'Venmo',
  zelle: 'Zelle',
  credit_card: 'Credit card · Stripe',
  send_invoice: 'Invoice (sent)',
};

function formatMethod(method: string): string {
  return (
    METHOD_LABELS[method] ??
    method
      .split('_')
      .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
      .join(' ')
  );
}

function formatPaidAt(value?: string | Date | null): string {
  if (!value) return '';
  const d = typeof value === 'string' ? new Date(value) : value;
  if (Number.isNaN(d.getTime())) return '';
  return d.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });
}

function formatAmount(value: number | string): string {
  const n = typeof value === 'string' ? parseFloat(value) : value;
  if (Number.isNaN(n)) return String(value);
  return `$${n.toFixed(2)}`;
}

export function PaidConfirmationCard({
  amountPaid,
  paymentMethod,
  paymentReference,
  paidAt,
  onTextReceipt,
  textReceiptPending = false,
}: PaidConfirmationCardProps) {
  const methodLabel = formatMethod(paymentMethod);
  const amountLabel = formatAmount(amountPaid);
  const paidAtLabel = formatPaidAt(paidAt);

  return (
    <div
      data-testid="payment-paid-card"
      className="rounded-[14px] border border-[#A7F3D0] bg-[#ECFDF5] px-4 py-3 flex items-start gap-3"
    >
      <CheckCircle2
        size={18}
        className="text-[#059669] flex-shrink-0 mt-0.5"
        strokeWidth={2.5}
      />
      <div className="flex-1 min-w-0">
        <p className="text-[10px] font-extrabold tracking-[0.6px] text-[#047857] uppercase">
          Payment Received
        </p>
        <p className="text-[14px] font-semibold text-[#064E3B] leading-snug">
          {amountLabel} · {methodLabel}
          {paymentReference ? ` · #${paymentReference}` : ''}
        </p>
        {paidAtLabel && (
          <p className="text-[12px] text-[#047857] leading-tight mt-0.5">
            {paidAtLabel}
          </p>
        )}
      </div>
      {onTextReceipt && (
        <button
          type="button"
          onClick={onTextReceipt}
          disabled={textReceiptPending}
          data-testid="text-receipt-cta"
          className="flex-shrink-0 inline-flex items-center gap-1.5 rounded-md bg-white border border-[#A7F3D0] px-3 py-1.5 text-[12px] font-semibold text-[#047857] hover:bg-[#F0FDF4] disabled:opacity-50"
        >
          <MessageSquare size={14} strokeWidth={2.25} />
          {textReceiptPending ? 'Sending…' : 'Text receipt'}
        </button>
      )}
    </div>
  );
}
