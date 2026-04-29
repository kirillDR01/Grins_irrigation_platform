/**
 * On-site payment workflow.
 *
 * Architecture C (Stripe Payment Links): the primary path sends the
 * customer a Stripe Payment Link via SMS (with email fallback). The
 * legacy Tap-to-Pay terminal path was deleted in plan §Phase 3.
 *
 * Validates: Requirements 16.1, 16.3, 16.4, 16.5, 16.9 + plan §Phase 3.1.
 */

import { useState } from 'react';
import {
  CheckCircle2,
  CreditCard,
  DollarSign,
  Link as LinkIcon,
  Loader2,
  Receipt,
  Send,
} from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { getErrorMessage } from '@/core/api/client';
import { useInvoicesByJob } from '@/features/invoices/hooks/useInvoices';
import { useSendPaymentLink } from '@/features/invoices/hooks/useInvoiceMutations';
import {
  useCollectPayment,
  useCreateInvoiceFromAppointment,
} from '../hooks/useAppointmentMutations';
import type { PaymentMethod } from '../types';

interface PaymentCollectorProps {
  appointmentId: string;
  /** Job ID, used to look up the invoice for this appointment. */
  jobId?: string;
  invoiceAmount?: number | string;
  customerPhone?: string | null;
  customerEmail?: string | null;
  /**
   * Whether the appointment has a fully-converted Customer record. When
   * false, the appointment belongs to a Lead and Payment Link sends are
   * blocked (plan D12).
   */
  customerExists?: boolean;
  /**
   * If true, the parent job is covered by an active service agreement
   * and the entire payment CTA is hidden (plan §Phase 3.4).
   */
  serviceAgreementActive?: boolean;
  onSuccess?: () => void;
}

type PaymentPath = 'choose' | 'manual';

const MANUAL_PAYMENT_METHODS: { value: PaymentMethod; label: string }[] = [
  { value: 'cash', label: 'Cash' },
  { value: 'check', label: 'Check' },
  { value: 'venmo', label: 'Venmo' },
  { value: 'zelle', label: 'Zelle' },
  { value: 'send_invoice', label: 'Send Invoice' },
];

const METHODS_REQUIRING_REFERENCE: PaymentMethod[] = [
  'cash',
  'check',
  'venmo',
  'zelle',
];

export function PaymentCollector({
  appointmentId,
  jobId,
  invoiceAmount,
  customerPhone,
  customerEmail,
  customerExists = true,
  serviceAgreementActive = false,
  onSuccess,
}: PaymentCollectorProps) {
  const [path, setPath] = useState<PaymentPath>('choose');

  const [method, setMethod] = useState<PaymentMethod | ''>('');
  const [amount, setAmount] = useState(
    invoiceAmount != null && invoiceAmount !== ''
      ? Number(invoiceAmount).toFixed(2)
      : '',
  );
  const [referenceNumber, setReferenceNumber] = useState('');
  const collectPayment = useCollectPayment();

  const { data: invoices, isLoading: invoicesLoading } = useInvoicesByJob(
    jobId ?? '',
  );
  // Pick the most recent non-cancelled invoice (defensive — backend rule is
  // one active invoice per job, but legacy data may have cancelled rows).
  const invoice =
    invoices?.find((i) => i.status !== 'cancelled') ?? invoices?.[0] ?? null;

  const createInvoice = useCreateInvoiceFromAppointment();
  const sendLink = useSendPaymentLink();

  const showReference =
    method !== '' && METHODS_REQUIRING_REFERENCE.includes(method);

  // ------------------------------------------------------------------
  // Service-agreement-covered jobs: parent should hide the CTA, but we
  // also defensively short-circuit here so the component is safe to use
  // standalone (plan §Phase 3.4 / edge case 10).
  // ------------------------------------------------------------------
  if (serviceAgreementActive) {
    return null;
  }

  // ------------------------------------------------------------------
  // Lead-only message: replace CTAs entirely (plan D12 / edge case 9).
  // ------------------------------------------------------------------
  if (!customerExists) {
    return (
      <div
        data-testid="payment-collector"
        className="space-y-2 p-3 bg-slate-50 rounded-xl"
      >
        <div className="flex items-center gap-2 mb-1">
          <CreditCard className="h-3.5 w-3.5 text-slate-400" />
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            Collect Payment
          </p>
        </div>
        <p
          data-testid="payment-collector-lead-only"
          className="text-sm text-slate-600"
        >
          Convert this lead to a customer before taking payment.
        </p>
      </div>
    );
  }

  const linkActive =
    !!invoice?.stripe_payment_link_url && !!invoice?.stripe_payment_link_active;
  const sentCount = invoice?.payment_link_sent_count ?? 0;
  const linkSentBefore = sentCount > 0;

  const sendOrCreateAndSend = async () => {
    try {
      let invoiceId = invoice?.id;
      if (!invoiceId) {
        const created = await createInvoice.mutateAsync(appointmentId);
        invoiceId = created.id;
      }
      const result = await sendLink.mutateAsync(invoiceId);
      const channelLabel = result.channel === 'sms' ? 'SMS' : 'email';
      toast.success(`Payment Link sent`, {
        description: `Sent via ${channelLabel}`,
      });
      onSuccess?.();
    } catch (err) {
      toast.error('Failed to send Payment Link', {
        description: getErrorMessage(err),
      });
    }
  };

  const handleCopyLink = async () => {
    if (!invoice?.stripe_payment_link_url) return;
    try {
      await navigator.clipboard.writeText(invoice.stripe_payment_link_url);
      toast.success('Link copied to clipboard');
    } catch {
      toast.error('Could not copy link');
    }
  };

  // ---- Manual Payment Flow ----
  const handleManualSubmit = async () => {
    if (!method) {
      toast.error('Please select a payment method');
      return;
    }
    const parsedAmount = parseFloat(amount);
    if (isNaN(parsedAmount) || parsedAmount <= 0) {
      toast.error('Please enter a valid amount');
      return;
    }
    try {
      await collectPayment.mutateAsync({
        id: appointmentId,
        data: {
          payment_method: method,
          amount: parsedAmount,
          reference_number: referenceNumber || undefined,
        },
      });
      toast.success('Payment Collected', {
        description: `$${parsedAmount.toFixed(2)} via ${MANUAL_PAYMENT_METHODS.find((m) => m.value === method)?.label}`,
      });
      setMethod('');
      setAmount('');
      setReferenceNumber('');
      setPath('choose');
      onSuccess?.();
    } catch (err) {
      toast.error('Error', { description: getErrorMessage(err) });
    }
  };

  const isSendingLink =
    invoicesLoading || sendLink.isPending || createInvoice.isPending;

  // ---- Choose Path View ----
  if (path === 'choose') {
    const sendButtonLabel = invoice
      ? linkSentBefore
        ? 'Resend Payment Link'
        : 'Send Payment Link'
      : 'Create Invoice & Send Payment Link';

    return (
      <div
        data-testid="payment-collector"
        className="space-y-3 p-3 bg-slate-50 rounded-xl"
      >
        <div className="flex items-center gap-2 mb-1">
          <CreditCard className="h-3.5 w-3.5 text-slate-400" />
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            Collect Payment
          </p>
        </div>

        {linkSentBefore && invoice && (
          <div
            className="flex items-center gap-2 rounded-md bg-violet-50 border border-violet-100 px-2.5 py-1.5"
            data-testid="payment-link-sent-indicator"
          >
            <CheckCircle2 className="h-3.5 w-3.5 text-violet-500 shrink-0" />
            <span className="text-xs text-violet-700">
              Link sent {sentCount}{' '}
              {sentCount === 1 ? 'time' : 'times'} · waiting for payment
            </span>
          </div>
        )}

        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          <Button
            onClick={sendOrCreateAndSend}
            disabled={isSendingLink}
            className="flex items-center gap-2 min-h-[48px] text-sm bg-violet-600 hover:bg-violet-700 text-white"
            data-testid="send-payment-link-btn"
          >
            {isSendingLink ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
            <span>{sendButtonLabel}</span>
          </Button>
          <Button
            onClick={() => setPath('manual')}
            variant="outline"
            className="flex items-center gap-2 min-h-[48px] text-sm border-slate-200 hover:bg-slate-100"
            data-testid="record-other-payment-btn"
          >
            <Receipt className="h-4 w-4 text-slate-500" />
            <span>Record Other Payment</span>
          </Button>
        </div>

        {/* D8 — copy-link UX. Visible whenever an active link exists. */}
        {linkActive && invoice?.stripe_payment_link_url && (
          <div
            className="flex items-center gap-2 rounded-md border border-slate-200 bg-white px-2.5 py-1.5"
            data-testid="payment-link-copy-row"
          >
            <LinkIcon className="h-3.5 w-3.5 text-slate-400 shrink-0" />
            <code
              className="flex-1 text-xs text-slate-600 truncate"
              data-testid="payment-link-url"
            >
              {invoice.stripe_payment_link_url}
            </code>
            <Button
              size="sm"
              variant="ghost"
              onClick={handleCopyLink}
              className="text-xs h-6 px-2"
              data-testid="copy-payment-link-btn"
            >
              Copy
            </Button>
          </div>
        )}

        {!customerPhone && !customerEmail && (
          <p
            className="text-xs text-amber-600"
            data-testid="payment-collector-no-contact"
          >
            Customer has no phone or email — link can be created but not
            delivered automatically.
          </p>
        )}
      </div>
    );
  }

  // ---- Manual Payment Form (Record Other Payment) ----
  return (
    <div
      data-testid="payment-collector"
      className="space-y-3 p-3 bg-slate-50 rounded-xl"
    >
      <div className="flex items-center justify-between mb-1">
        <div className="flex items-center gap-2">
          <Receipt className="h-3.5 w-3.5 text-slate-400" />
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            Record Other Payment
          </p>
        </div>
        <Button
          size="sm"
          variant="ghost"
          onClick={() => setPath('choose')}
          className="text-xs text-slate-400 h-6 px-2"
        >
          Back
        </Button>
      </div>

      <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
        <div>
          <label className="text-xs font-medium text-slate-600 mb-1 block">
            Method
          </label>
          <Select
            value={method}
            onValueChange={(v) => setMethod(v as PaymentMethod)}
          >
            <SelectTrigger
              data-testid="payment-method-select"
              className="min-h-[44px] text-sm md:min-h-0 md:h-8 md:text-xs"
            >
              <SelectValue placeholder="Select method..." />
            </SelectTrigger>
            <SelectContent>
              {MANUAL_PAYMENT_METHODS.map((m) => (
                <SelectItem key={m.value} value={m.value}>
                  {m.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div>
          <label className="text-xs font-medium text-slate-600 mb-1 block">
            Amount
          </label>
          <div className="relative">
            <DollarSign className="absolute left-2 top-1/2 -translate-y-1/2 h-3 w-3 text-slate-400" />
            <Input
              type="number"
              step="0.01"
              min="0"
              placeholder="0.00"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              className="pl-6 min-h-[44px] text-sm md:min-h-0 md:h-8 md:text-xs"
              data-testid="payment-amount-input"
            />
          </div>
        </div>
      </div>

      {showReference && (
        <div>
          <label className="text-xs font-medium text-slate-600 mb-1 block">
            Reference Number
          </label>
          <Input
            placeholder="Check #, transaction ID, etc."
            value={referenceNumber}
            onChange={(e) => setReferenceNumber(e.target.value)}
            className="min-h-[44px] text-sm md:min-h-0 md:h-8 md:text-xs"
            data-testid="payment-reference-input"
          />
        </div>
      )}

      <Button
        onClick={handleManualSubmit}
        disabled={collectPayment.isPending || !method || !amount}
        size="sm"
        className="w-full bg-teal-500 hover:bg-teal-600 text-white min-h-[48px] text-sm md:min-h-0 md:h-8 md:text-xs"
        data-testid="collect-payment-btn"
      >
        {collectPayment.isPending ? (
          <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
        ) : (
          <DollarSign className="mr-1.5 h-3.5 w-3.5" />
        )}
        Collect Payment
      </Button>
    </div>
  );
}
