import { memo } from 'react';
import { Link } from 'react-router-dom';
import { AlertTriangle, Clock, FileWarning, ChevronRight } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/components/ui/card';
import { Button } from '@/components/ui/button';
import { useLienDeadlines } from '../hooks';
import { InvoiceStatusBadge } from './InvoiceStatusBadge';
import type { Invoice } from '../types';

interface LienDeadlinesWidgetProps {
  className?: string;
}

function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
  }).format(amount);
}

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
  });
}

interface DeadlineItemProps {
  invoice: Invoice;
  deadlineType: '45-day' | '120-day';
}

const DeadlineItem = memo(function DeadlineItem({
  invoice,
  deadlineType,
}: DeadlineItemProps) {
  return (
    <div
      className="flex items-center justify-between py-2 border-b last:border-b-0"
      data-testid={`lien-deadline-item-${invoice.id}`}
    >
      <div className="flex-1 min-w-0">
        <Link
          to={`/invoices/${invoice.id}`}
          className="text-sm font-medium text-blue-600 hover:underline truncate block"
          data-testid={`lien-deadline-link-${invoice.id}`}
        >
          {invoice.invoice_number}
        </Link>
        <p className="text-xs text-gray-500 truncate">
          Due: {formatDate(invoice.due_date)} • {formatCurrency(invoice.total_amount)}
        </p>
      </div>
      <div className="flex items-center gap-2 ml-2">
        <InvoiceStatusBadge status={invoice.status} />
        {deadlineType === '45-day' ? (
          <Button
            size="sm"
            variant="outline"
            className="text-orange-600 border-orange-300 hover:bg-orange-50"
            asChild
            data-testid={`send-warning-btn-${invoice.id}`}
          >
            <Link to={`/invoices/${invoice.id}`}>Send Warning</Link>
          </Button>
        ) : (
          <Button
            size="sm"
            variant="outline"
            className="text-red-600 border-red-300 hover:bg-red-50"
            asChild
            data-testid={`file-lien-btn-${invoice.id}`}
          >
            <Link to={`/invoices/${invoice.id}`}>File Lien</Link>
          </Button>
        )}
      </div>
    </div>
  );
});

export const LienDeadlinesWidget = memo(function LienDeadlinesWidget({
  className,
}: LienDeadlinesWidgetProps) {
  const { data, isLoading, error } = useLienDeadlines();

  const approaching45Day = data?.approaching_45_day ?? [];
  const approaching120Day = data?.approaching_120_day ?? [];
  const hasDeadlines = approaching45Day.length > 0 || approaching120Day.length > 0;

  return (
    <Card className={className} data-testid="lien-deadlines-widget">
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-lg">
          <FileWarning className="h-5 w-5 text-orange-500" />
          Lien Deadlines
        </CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading && (
          <div
            className="flex items-center justify-center py-4"
            data-testid="lien-deadlines-loading"
          >
            <Clock className="h-5 w-5 animate-spin text-gray-400" />
            <span className="ml-2 text-sm text-gray-500">Loading...</span>
          </div>
        )}

        {error && (
          <div
            className="text-sm text-red-600 py-2"
            data-testid="lien-deadlines-error"
          >
            Failed to load lien deadlines
          </div>
        )}

        {!isLoading && !error && !hasDeadlines && (
          <div
            className="text-sm text-gray-500 py-4 text-center"
            data-testid="lien-deadlines-empty"
          >
            No approaching lien deadlines
          </div>
        )}

        {!isLoading && !error && hasDeadlines && (
          <div className="space-y-4">
            {approaching45Day.length > 0 && (
              <div data-testid="lien-deadlines-45-day-section">
                <div className="flex items-center gap-2 mb-2">
                  <AlertTriangle className="h-4 w-4 text-orange-500" />
                  <h4 className="text-sm font-medium text-orange-700">
                    45-Day Warning Due ({approaching45Day.length})
                  </h4>
                </div>
                <div className="space-y-1">
                  {approaching45Day.slice(0, 3).map((invoice) => (
                    <DeadlineItem
                      key={invoice.id}
                      invoice={invoice}
                      deadlineType="45-day"
                    />
                  ))}
                  {approaching45Day.length > 3 && (
                    <Link
                      to="/invoices?lien_eligible=true"
                      className="flex items-center text-sm text-blue-600 hover:underline pt-1"
                      data-testid="view-all-45-day-link"
                    >
                      View all {approaching45Day.length} invoices
                      <ChevronRight className="h-4 w-4" />
                    </Link>
                  )}
                </div>
              </div>
            )}

            {approaching120Day.length > 0 && (
              <div data-testid="lien-deadlines-120-day-section">
                <div className="flex items-center gap-2 mb-2">
                  <AlertTriangle className="h-4 w-4 text-red-500" />
                  <h4 className="text-sm font-medium text-red-700">
                    120-Day Filing Due ({approaching120Day.length})
                  </h4>
                </div>
                <div className="space-y-1">
                  {approaching120Day.slice(0, 3).map((invoice) => (
                    <DeadlineItem
                      key={invoice.id}
                      invoice={invoice}
                      deadlineType="120-day"
                    />
                  ))}
                  {approaching120Day.length > 3 && (
                    <Link
                      to="/invoices?status=lien_warning"
                      className="flex items-center text-sm text-blue-600 hover:underline pt-1"
                      data-testid="view-all-120-day-link"
                    >
                      View all {approaching120Day.length} invoices
                      <ChevronRight className="h-4 w-4" />
                    </Link>
                  )}
                </div>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
});
