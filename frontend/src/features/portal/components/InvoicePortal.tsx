import { useParams } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { cn } from '@/lib/utils';
import {
  Loader2,
  AlertTriangle,
  CreditCard,
  CheckCircle2,
  FileText,
  Phone,
} from 'lucide-react';
import { usePortalInvoice } from '../hooks';

function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(amount);
}

const statusConfig: Record<string, { variant: 'success' | 'warning' | 'error' | 'info' | 'default'; label: string }> = {
  PAID: { variant: 'success', label: 'Paid' },
  PARTIAL: { variant: 'warning', label: 'Partially Paid' },
  SENT: { variant: 'info', label: 'Sent' },
  VIEWED: { variant: 'info', label: 'Viewed' },
  OVERDUE: { variant: 'error', label: 'Overdue' },
  DRAFT: { variant: 'default', label: 'Draft' },
};

export function InvoicePortal() {
  const { token = '' } = useParams<{ token: string }>();
  const { data: invoice, isLoading, error } = usePortalInvoice(token);

  const isExpired = error && (error as { response?: { status?: number } })?.response?.status === 410;

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50" data-testid="invoice-loading">
        <Loader2 className="h-8 w-8 animate-spin text-teal-500" />
      </div>
    );
  }

  if (isExpired) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 p-4" data-testid="invoice-expired">
        <div className="max-w-md text-center space-y-4">
          <AlertTriangle className="h-12 w-12 text-amber-500 mx-auto" />
          <h1 className="text-xl font-bold text-slate-800">Link Expired</h1>
          <p className="text-slate-600">
            This invoice link has expired (over 90 days old). Please contact the business for assistance.
          </p>
          <div className="bg-white rounded-xl border border-slate-200 p-4 space-y-2" data-testid="expired-contact-info">
            <Phone className="h-5 w-5 text-teal-500 mx-auto" />
            <p className="text-sm text-slate-600">
              Contact us for an updated invoice link.
            </p>
          </div>
        </div>
      </div>
    );
  }

  if (error || !invoice) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 p-4" data-testid="invoice-error">
        <div className="max-w-md text-center space-y-4">
          <AlertTriangle className="h-12 w-12 text-red-500 mx-auto" />
          <h1 className="text-xl font-bold text-slate-800">Unable to Load Invoice</h1>
          <p className="text-slate-600">
            We couldn&apos;t load this invoice. The link may be invalid or expired.
          </p>
        </div>
      </div>
    );
  }

  const status = statusConfig[invoice.payment_status] ?? { variant: 'default' as const, label: invoice.payment_status };
  const isPaid = invoice.balance_due <= 0;

  return (
    <div className="min-h-screen bg-slate-50" data-testid="invoice-portal-page">
      {/* Header with company branding */}
      <header className="bg-white border-b border-slate-200 px-4 py-6 md:px-8">
        <div className="max-w-3xl mx-auto flex items-center gap-4">
          {invoice.company_logo_url && (
            <img
              src={invoice.company_logo_url}
              alt={invoice.company_name ?? "Grin's Irrigation"}
              className="h-12 w-auto object-contain"
              data-testid="company-logo"
            />
          )}
          <div>
            <h1 className="text-lg font-bold text-slate-800">
              {invoice.company_name ?? "Grin's Irrigation"}
            </h1>
            {invoice.company_address && (
              <p className="text-sm text-slate-500">{invoice.company_address}</p>
            )}
            {invoice.company_phone && (
              <p className="text-sm text-slate-500">{invoice.company_phone}</p>
            )}
          </div>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 py-8 md:px-8 space-y-6">
        {/* Invoice header info */}
        <div className="bg-white rounded-xl border border-slate-200 p-6 space-y-4">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-2">
            <div className="flex items-center gap-2">
              <FileText className="h-5 w-5 text-teal-500" />
              <h2 className="text-lg font-semibold text-slate-800">
                Invoice {invoice.invoice_number}
              </h2>
            </div>
            <Badge variant={status.variant} data-testid="invoice-status-badge">
              {status.label}
            </Badge>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
            <div>
              <span className="text-slate-500">Bill to:</span>
              <p className="font-medium text-slate-800">{invoice.customer_name}</p>
            </div>
            <div>
              <span className="text-slate-500">Invoice date:</span>
              <p className="font-medium text-slate-800">
                {new Date(invoice.invoice_date).toLocaleDateString()}
              </p>
            </div>
            <div>
              <span className="text-slate-500">Due date:</span>
              <p className={cn(
                'font-medium',
                new Date(invoice.due_date) < new Date() && !isPaid
                  ? 'text-red-600'
                  : 'text-slate-800'
              )}>
                {new Date(invoice.due_date).toLocaleDateString()}
              </p>
            </div>
          </div>
        </div>

        {/* Line items table */}
        <div className="bg-white rounded-xl border border-slate-200 overflow-x-auto">
          <div className="p-4 border-b border-slate-100">
            <h3 className="font-semibold text-slate-800">Line Items</h3>
          </div>
          <Table data-testid="invoice-line-items-table">
            <TableHeader>
              <TableRow>
                <TableHead>Description</TableHead>
                <TableHead className="text-right">Qty</TableHead>
                <TableHead className="text-right">Unit Price</TableHead>
                <TableHead className="text-right">Total</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {invoice.line_items.map((item, idx) => (
                <TableRow key={idx}>
                  <TableCell className="font-medium">{item.description}</TableCell>
                  <TableCell className="text-right">{item.quantity}</TableCell>
                  <TableCell className="text-right">{formatCurrency(item.unit_price)}</TableCell>
                  <TableCell className="text-right font-medium">{formatCurrency(item.total)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>

        {/* Totals */}
        <div className="bg-white rounded-xl border border-slate-200 p-6 space-y-2" data-testid="invoice-totals">
          <div className="flex justify-between text-sm text-slate-600">
            <span>Total Amount</span>
            <span>{formatCurrency(invoice.total_amount)}</span>
          </div>
          {invoice.amount_paid > 0 && (
            <div className="flex justify-between text-sm text-emerald-600">
              <span>Amount Paid</span>
              <span>-{formatCurrency(invoice.amount_paid)}</span>
            </div>
          )}
          <div className={cn(
            'flex justify-between text-lg font-bold pt-2 border-t border-slate-100',
            isPaid ? 'text-emerald-600' : 'text-slate-800'
          )}>
            <span>Balance Due</span>
            <span>{formatCurrency(invoice.balance_due)}</span>
          </div>
        </div>

        {/* Payment action */}
        <div data-testid="invoice-payment-action">
          {isPaid ? (
            <div className="bg-emerald-50 rounded-xl border border-emerald-200 p-6 text-center space-y-2" data-testid="paid-confirmation">
              <CheckCircle2 className="h-10 w-10 text-emerald-500 mx-auto" />
              <h3 className="font-semibold text-emerald-800">Paid in Full</h3>
              <p className="text-sm text-emerald-600">Thank you for your payment.</p>
            </div>
          ) : invoice.stripe_payment_url ? (
            <a
              href={invoice.stripe_payment_url}
              target="_blank"
              rel="noopener noreferrer"
              className="block"
            >
              <Button className="w-full h-12" data-testid="pay-now-btn">
                <CreditCard className="h-4 w-4" />
                Pay Now — {formatCurrency(invoice.balance_due)}
              </Button>
            </a>
          ) : (
            <div className="bg-slate-100 rounded-xl border border-slate-200 p-6 text-center space-y-2" data-testid="payment-unavailable">
              <p className="text-sm text-slate-600">
                Online payment is not available for this invoice. Please contact the business to arrange payment.
              </p>
              {invoice.company_phone && (
                <a
                  href={`tel:${invoice.company_phone}`}
                  className="text-teal-600 font-medium text-sm hover:underline"
                >
                  {invoice.company_phone}
                </a>
              )}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
