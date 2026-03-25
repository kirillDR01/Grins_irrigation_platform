/**
 * InvoiceMetricsWidget — displays pending invoice count and total amount on the dashboard.
 * Replaces the old job-status-based invoice calculation.
 * Clicking navigates to /invoices.
 *
 * Validates: Requirements 5.1, 5.3
 */

import { useNavigate } from 'react-router-dom';
import { FileText } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import { usePendingInvoiceMetrics } from '../hooks';

function formatCurrency(amount: string): string {
  const num = parseFloat(amount);
  if (isNaN(num)) return '$0.00';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
  }).format(num);
}

export function InvoiceMetricsWidget() {
  const navigate = useNavigate();
  const { data, isLoading } = usePendingInvoiceMetrics();

  const count = data?.count ?? 0;
  const totalAmount = data?.total_amount ?? '0';

  const handleClick = () => {
    navigate('/invoices');
  };

  return (
    <Card
      data-testid="invoice-metrics-widget"
      className={cn(
        'relative cursor-pointer transition-all hover:shadow-md',
        count > 0 && 'border-emerald-200'
      )}
      onClick={handleClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          handleClick();
        }
      }}
    >
      <CardContent className="p-6">
        <div className="absolute top-4 right-4 p-3 rounded-xl bg-emerald-50">
          <FileText className="h-5 w-5 text-emerald-500" />
        </div>
        <div className="space-y-2">
          <p className="text-sm font-semibold uppercase tracking-wider text-slate-400">
            Pending Invoices
          </p>
          <div className="text-3xl font-bold text-slate-800">
            {isLoading ? '—' : count}
          </div>
          <p className="text-xs text-slate-400">
            {isLoading
              ? ''
              : count === 0
                ? 'No pending invoices'
                : `${formatCurrency(totalAmount)} total`}
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
