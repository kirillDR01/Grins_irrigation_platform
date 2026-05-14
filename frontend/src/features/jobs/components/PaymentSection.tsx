// @ts-nocheck — pre-existing TS errors documented in bughunt/2026-04-29-pre-existing-tsc-errors.md
/**
 * Conditional payment section for job detail view.
 * Renders one of four states based on the job's payment path:
 * 1. Service agreement → "Covered by [name] — no payment needed"
 * 2. One-off, no invoice → "Create Invoice" + "Collect Payment" buttons
 * 3. Invoice sent → Invoice details with status badge + "Collect Payment"
 * 4. Paid on-site → "Payment collected — $X via method"
 *
 * Validates: Requirements 17.1, 17.2, 17.3, 17.4, 17.6
 */

import { Link, useNavigate } from 'react-router-dom';
import {
  ShieldCheck,
  CheckCircle2,
  CreditCard,
  FileText,
  DollarSign,
  Copy,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import type { Job } from '../types';
import { formatAmount } from '../types';
import { GenerateInvoiceButton, InvoiceStatusBadge, useInvoicesByJob } from '@/features/invoices';
import type { Invoice } from '@/features/invoices';
import { parseLocalDate } from '@/shared/utils/dateUtils';
import { toast } from 'sonner';

function stripPaymentRefPrefix(ref: string): string {
  if (ref.startsWith('stripe:')) return ref.slice('stripe:'.length);
  if (ref.startsWith('stripe_link:')) return ref.slice('stripe_link:'.length);
  return ref;
}

function truncatePaymentRef(stripped: string): string {
  return stripped.length > 14 ? `${stripped.slice(0, 12)}…` : stripped;
}

async function copyPaymentRef(rawRef: string): Promise<void> {
  const bare = stripPaymentRefPrefix(rawRef);
  try {
    await navigator.clipboard.writeText(bare);
    toast.success('Reference copied');
  } catch {
    toast.error('Could not copy reference');
  }
}

interface PaymentSectionProps {
  job: Job;
}

export function PaymentSection({ job }: PaymentSectionProps) {
  const navigate = useNavigate();
  const { data: invoices } = useInvoicesByJob(job.id);
  const linkedInvoice: Invoice | undefined = invoices?.[0];

  const isAgreementJob =
    !!job.service_agreement_id && !!job.service_agreement_active;
  const isPaidOnSite = !!job.payment_collected_on_site;
  const hasInvoice = !!linkedInvoice;

  // Determine which payment path to render (Req 17.6)
  // Order: agreement → paid on-site → invoice sent → no payment
  if (isAgreementJob) {
    return <AgreementCovered job={job} />;
  }

  if (isPaidOnSite) {
    return <PaidOnSite job={job} invoice={linkedInvoice} />;
  }

  if (hasInvoice) {
    return <InvoiceSent invoice={linkedInvoice} navigate={navigate} />;
  }

  return <NoPayment job={job} />;
}

/** Req 17.1: Service agreement job — green checkmark, no payment buttons */
function AgreementCovered({ job }: { job: Job }) {
  return (
    <div data-testid="payment-section-agreement" className="space-y-2">
      <p className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-2 flex items-center gap-1.5">
        <DollarSign className="h-3.5 w-3.5" />
        Payment
      </p>
      <div className="flex items-center gap-2 p-3 bg-emerald-50 border border-emerald-200 rounded-lg">
        <CheckCircle2 className="h-5 w-5 text-emerald-600 shrink-0" />
        <div>
          <p className="text-sm font-medium text-emerald-700">
            Covered by {job.service_agreement_name || 'Service Agreement'} — no payment needed
          </p>
        </div>
      </div>
    </div>
  );
}

/** Req 17.2: One-off job, no invoice — both buttons shown */
function NoPayment({ job }: { job: Job }) {
  return (
    <div data-testid="payment-section-no-payment" className="space-y-2">
      <p className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-2 flex items-center gap-1.5">
        <DollarSign className="h-3.5 w-3.5" />
        Payment
      </p>
      {job.status === 'completed' && (
        <div data-testid="generate-invoice-section">
          <GenerateInvoiceButton job={job} />
        </div>
      )}
      <Button
        variant="outline"
        size="sm"
        className="w-full border-teal-200 text-teal-600 hover:bg-teal-50"
        data-testid="collect-payment-btn"
        asChild
      >
        <Link to={`/jobs/${job.id}?collect=true`}>
          <CreditCard className="mr-1.5 h-3.5 w-3.5" />
          Collect Payment
        </Link>
      </Button>
    </div>
  );
}

/** Req 17.3: Invoice sent — invoice details with badge + Collect Payment */
function InvoiceSent({
  invoice,
  navigate,
}: {
  invoice: Invoice;
  navigate: ReturnType<typeof useNavigate>;
}) {
  const sentDate = invoice.invoice_date
    ? parseLocalDate(invoice.invoice_date).toLocaleDateString()
    : null;

  return (
    <div data-testid="payment-section-invoice" className="space-y-2">
      <p className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-2 flex items-center gap-1.5">
        <DollarSign className="h-3.5 w-3.5" />
        Payment
      </p>
      <div
        className="flex items-center justify-between p-3 bg-blue-50 rounded-lg hover:bg-blue-100 transition-colors cursor-pointer"
        onClick={() => navigate(`/invoices/${invoice.id}`)}
        data-testid="invoice-info-display"
      >
        <div className="flex items-center gap-2">
          <FileText className="h-4 w-4 text-blue-600" />
          <div>
            <p className="text-sm font-medium text-blue-700">
              Invoice #{invoice.invoice_number}
            </p>
            <p className="text-xs text-blue-600">
              {sentDate && `Sent on ${sentDate}, `}
              {formatAmount(invoice.total_amount)}
            </p>
            {invoice.status === 'paid' && invoice.paid_at && (
              <p className="text-xs text-blue-600" data-testid="payment-section-invoice-paid-at">
                Paid {new Date(invoice.paid_at).toLocaleDateString()}
              </p>
            )}
            {invoice.status === 'paid' && invoice.payment_reference && (
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  void copyPaymentRef(invoice.payment_reference!);
                }}
                title={stripPaymentRefPrefix(invoice.payment_reference)}
                className="inline-flex items-center gap-1 text-xs text-blue-600 hover:text-blue-800 font-mono"
                data-testid="payment-section-invoice-payment-ref"
              >
                Ref {truncatePaymentRef(stripPaymentRefPrefix(invoice.payment_reference))}
                <Copy className="h-3 w-3" />
              </button>
            )}
          </div>
        </div>
        <InvoiceStatusBadge status={invoice.status} />
      </div>
      <Button
        variant="outline"
        size="sm"
        className="w-full border-teal-200 text-teal-600 hover:bg-teal-50"
        data-testid="collect-payment-btn"
        asChild
      >
        <Link to={`/invoices/${invoice.id}`}>
          <CreditCard className="mr-1.5 h-3.5 w-3.5" />
          Collect Payment
        </Link>
      </Button>
    </div>
  );
}

/** Req 17.4: Paid on-site — green checkmark with payment details */
function PaidOnSite({ job, invoice }: { job: Job; invoice?: Invoice }) {
  // Try to get payment method from linked invoice, fall back to "on site"
  const methodLabel = invoice?.payment_method
    ? PAYMENT_METHOD_LABELS[invoice.payment_method] ?? invoice.payment_method
    : 'on site';
  const displayAmount = invoice?.paid_amount ?? job.final_amount;

  return (
    <div data-testid="payment-section-paid" className="space-y-2">
      <p className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-2 flex items-center gap-1.5">
        <DollarSign className="h-3.5 w-3.5" />
        Payment
      </p>
      <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-lg space-y-1">
        <div className="flex items-center gap-2">
          <CheckCircle2 className="h-5 w-5 text-emerald-600 shrink-0" />
          <p className="text-sm font-medium text-emerald-700">
            Payment collected
            {displayAmount ? ` — ${formatAmount(displayAmount)}` : ''}
            {` via ${methodLabel}`}
          </p>
        </div>
        {invoice?.paid_at && (
          <p
            className="text-xs text-emerald-700 pl-7"
            data-testid="payment-section-paid-on-site-paid-at"
          >
            Paid {new Date(invoice.paid_at).toLocaleDateString()}
          </p>
        )}
        {invoice?.payment_reference && (
          <button
            type="button"
            onClick={() => {
              void copyPaymentRef(invoice.payment_reference!);
            }}
            title={stripPaymentRefPrefix(invoice.payment_reference)}
            className="inline-flex items-center gap-1 pl-7 text-xs text-emerald-700 hover:text-emerald-900 font-mono"
            data-testid="payment-section-paid-on-site-payment-ref"
          >
            Ref {truncatePaymentRef(stripPaymentRefPrefix(invoice.payment_reference))}
            <Copy className="h-3 w-3" />
          </button>
        )}
      </div>
    </div>
  );
}

const PAYMENT_METHOD_LABELS: Record<string, string> = {
  cash: 'Cash',
  check: 'Check',
  venmo: 'Venmo',
  zelle: 'Zelle',
  stripe: 'Card',
  credit_card: 'Card (Tap to Pay)',
  stripe_terminal: 'Card (Tap to Pay)',
};
