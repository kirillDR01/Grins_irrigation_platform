import { memo } from 'react';
import { Link } from 'react-router-dom';
import { AlertTriangle, Clock, ChevronRight } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/components/ui/card';
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
  const daysRemaining = Math.ceil(
    (new Date(invoice.due_date).getTime() - Date.now()) / (1000 * 60 * 60 * 24)
  );
  const isUrgent = daysRemaining < 7;
  const isWarning = daysRemaining >= 7 && daysRemaining < 30;

  const itemBgClass = isUrgent
    ? 'bg-red-50 border border-red-100'
    : isWarning
    ? 'bg-amber-50 border border-amber-100'
    : 'bg-slate-50';

  const daysTextClass = isUrgent
    ? 'text-red-600'
    : isWarning
    ? 'text-amber-600'
    : 'text-slate-500';

  return (
    <div
      className={`flex items-center justify-between p-3 rounded-lg ${itemBgClass}`}
      data-testid={`lien-deadline-item-${invoice.id}`}
    >
      <div className="flex-1 min-w-0">
        <Link
          to={`/invoices/${invoice.id}`}
          className="font-medium text-slate-700 hover:text-teal-600 truncate block"
          data-testid={`lien-deadline-link-${invoice.id}`}
        >
          {invoice.invoice_number}
        </Link>
        <p className="text-xs text-slate-500 truncate">
          Due: {formatDate(invoice.due_date)} • {formatCurrency(invoice.total_amount)}
        </p>
      </div>
      <div className="flex items-center gap-2 ml-2">
        <InvoiceStatusBadge status={invoice.status} />
        <span className={`text-sm font-bold ${daysTextClass}`}>
          {daysRemaining}d
        </span>
        <Link
          to={`/invoices/${invoice.id}`}
          className="text-teal-600 hover:text-teal-700 text-sm font-medium"
          data-testid={deadlineType === '45-day' ? `send-warning-btn-${invoice.id}` : `file-lien-btn-${invoice.id}`}
        >
          {deadlineType === '45-day' ? 'Send Warning' : 'File Lien'}
        </Link>
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
    <Card className={`bg-white rounded-2xl shadow-sm border border-slate-100 ${className || ''}`} data-testid="lien-deadlines-widget">
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-lg">
          <AlertTriangle className="h-5 w-5 text-amber-500" />
          Lien Deadlines
        </CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading && (
          <div
            className="flex items-center justify-center py-4"
            data-testid="lien-deadlines-loading"
          >
            <Clock className="h-5 w-5 animate-spin text-slate-400" />
            <span className="ml-2 text-sm text-slate-500">Loading...</span>
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
            className="text-sm text-slate-500 py-4 text-center"
            data-testid="lien-deadlines-empty"
          >
            No approaching lien deadlines
          </div>
        )}

        {!isLoading && !error && hasDeadlines && (
          <div className="space-y-3">
            {approaching45Day.length > 0 && (
              <div data-testid="lien-deadlines-45-day-section">
                <div className="flex items-center gap-2 mb-2">
                  <AlertTriangle className="h-4 w-4 text-amber-500" />
                  <h4 className="text-sm font-medium text-amber-700">
                    45-Day Warning Due ({approaching45Day.length})
                  </h4>
                </div>
                <div className="space-y-3">
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
                      className="flex items-center text-sm text-teal-600 hover:text-teal-700 font-medium pt-1"
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
                <div className="space-y-3">
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
                      className="flex items-center text-sm text-teal-600 hover:text-teal-700 font-medium pt-1"
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
