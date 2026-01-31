import { memo } from 'react';
import { Link } from 'react-router-dom';
import { AlertCircle, ChevronRight } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { useOverdueInvoices } from '../hooks';
import { InvoiceStatusBadge } from './InvoiceStatusBadge';
import { LoadingSpinner } from '@/shared/components/LoadingSpinner';
import type { Invoice } from '../types';

interface OverdueInvoicesWidgetProps {
  className?: string;
}

function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
  }).format(amount);
}

function getDaysOverdue(dueDate: string): number {
  const due = new Date(dueDate);
  const today = new Date();
  const diffTime = today.getTime() - due.getTime();
  return Math.ceil(diffTime / (1000 * 60 * 60 * 24));
}

interface OverdueItemProps {
  invoice: Invoice;
}

const OverdueItem = memo(function OverdueItem({ invoice }: OverdueItemProps) {
  const daysOverdue = getDaysOverdue(invoice.due_date);

  return (
    <div
      className="flex items-center justify-between p-3 bg-red-50 rounded-lg border border-red-100"
      data-testid={`overdue-invoice-item-${invoice.id}`}
    >
      <div className="flex-1 min-w-0">
        <Link
          to={`/invoices/${invoice.id}`}
          className="text-sm font-medium text-slate-700 hover:text-teal-600 truncate block"
          data-testid={`overdue-invoice-link-${invoice.id}`}
        >
          {invoice.invoice_number}
        </Link>
        <p className="text-xs text-red-500 mt-0.5">
          {daysOverdue} days overdue
        </p>
      </div>
      <div className="flex items-center gap-3 ml-2">
        <span className="font-bold text-red-600 text-sm">
          {formatCurrency(invoice.total_amount)}
        </span>
        <div className="flex gap-2">
          <button
            className="text-red-600 hover:text-red-700 text-sm font-medium"
            data-testid={`send-reminder-btn-${invoice.id}`}
          >
            Send Reminder
          </button>
          <Button
            size="sm"
            variant="ghost"
            asChild
            className="text-teal-600 hover:text-teal-700"
            data-testid={`view-overdue-btn-${invoice.id}`}
          >
            <Link to={`/invoices/${invoice.id}`}>View</Link>
          </Button>
        </div>
      </div>
    </div>
  );
});

export const OverdueInvoicesWidget = memo(function OverdueInvoicesWidget({
  className,
}: OverdueInvoicesWidgetProps) {
  const { data, isLoading, error } = useOverdueInvoices({ page_size: 5 });

  const invoices = data?.items ?? [];
  const totalOverdue = data?.total ?? 0;
  const totalAmount = invoices.reduce((sum, inv) => sum + inv.total_amount, 0);

  return (
    <Card className={`bg-white rounded-2xl shadow-sm border border-slate-100 ${className || ''}`} data-testid="overdue-invoices-widget">
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-lg">
          <AlertCircle className="h-5 w-5 text-red-500" />
          Overdue Invoices
          {totalOverdue > 0 && (
            <span className="ml-auto px-3 py-1 rounded-full text-xs font-medium bg-red-100 text-red-700">
              {formatCurrency(totalAmount)}
            </span>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading && (
          <div
            className="flex items-center justify-center py-4"
            data-testid="overdue-invoices-loading"
          >
            <LoadingSpinner />
          </div>
        )}

        {error && (
          <div
            className="text-sm text-red-600 py-2"
            data-testid="overdue-invoices-error"
          >
            Failed to load overdue invoices
          </div>
        )}

        {!isLoading && !error && invoices.length === 0 && (
          <div
            className="text-sm text-slate-500 py-4 text-center"
            data-testid="overdue-invoices-empty"
          >
            No overdue invoices
          </div>
        )}

        {!isLoading && !error && invoices.length > 0 && (
          <div className="space-y-3">
            {invoices.map((invoice) => (
              <OverdueItem key={invoice.id} invoice={invoice} />
            ))}
            {totalOverdue > 5 && (
              <Link
                to="/invoices?status=overdue"
                className="flex items-center text-sm text-teal-600 hover:text-teal-700 pt-2"
                data-testid="view-all-overdue-link"
              >
                View all {totalOverdue} overdue invoices
                <ChevronRight className="h-4 w-4" />
              </Link>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
});
