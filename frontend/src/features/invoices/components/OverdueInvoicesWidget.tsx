import { memo } from 'react';
import { Link } from 'react-router-dom';
import { AlertCircle, ChevronRight } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/components/ui/card';
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
      className="flex items-center justify-between py-2 border-b last:border-b-0"
      data-testid={`overdue-invoice-item-${invoice.id}`}
    >
      <div className="flex-1 min-w-0">
        <Link
          to={`/invoices/${invoice.id}`}
          className="text-sm font-medium text-blue-600 hover:underline truncate block"
          data-testid={`overdue-invoice-link-${invoice.id}`}
        >
          {invoice.invoice_number}
        </Link>
        <p className="text-xs text-gray-500 truncate">
          {formatCurrency(invoice.total_amount)} • {daysOverdue} days overdue
        </p>
      </div>
      <div className="flex items-center gap-2 ml-2">
        <InvoiceStatusBadge status={invoice.status} />
        <Button
          size="sm"
          variant="outline"
          asChild
          data-testid={`view-overdue-btn-${invoice.id}`}
        >
          <Link to={`/invoices/${invoice.id}`}>View</Link>
        </Button>
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

  return (
    <Card className={className} data-testid="overdue-invoices-widget">
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-lg">
          <AlertCircle className="h-5 w-5 text-red-500" />
          Overdue Invoices
          {totalOverdue > 0 && (
            <span className="text-sm font-normal text-red-600">({totalOverdue})</span>
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
            className="text-sm text-gray-500 py-4 text-center"
            data-testid="overdue-invoices-empty"
          >
            No overdue invoices
          </div>
        )}

        {!isLoading && !error && invoices.length > 0 && (
          <div className="space-y-1">
            {invoices.map((invoice) => (
              <OverdueItem key={invoice.id} invoice={invoice} />
            ))}
            {totalOverdue > 5 && (
              <Link
                to="/invoices?status=overdue"
                className="flex items-center text-sm text-blue-600 hover:underline pt-2"
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
