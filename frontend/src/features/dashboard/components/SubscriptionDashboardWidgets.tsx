import { Link } from 'react-router-dom';
import { Card, CardContent } from '@/components/ui/card';
import { LoadingSpinner } from '@/shared/components/LoadingSpinner';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { useDashboardSummary } from '../hooks';
import {
  FileText,
  DollarSign,
  RefreshCw,
  AlertTriangle,
} from 'lucide-react';
import { cn } from '@/lib/utils';

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
}

export function SubscriptionDashboardWidgets() {
  const { data, isLoading, error } = useDashboardSummary();

  if (isLoading) return <LoadingSpinner />;
  if (error) {
    return (
      <Alert variant="destructive" data-testid="subscription-widgets-error">
        <AlertDescription>Failed to load subscription metrics.</AlertDescription>
      </Alert>
    );
  }
  if (!data) return null;

  const widgets = [
    {
      testId: 'widget-active-agreements',
      title: 'Active Agreements',
      value: String(data.active_agreement_count),
      icon: FileText,
      iconBg: 'bg-emerald-50',
      iconColor: 'text-emerald-500',
      link: '/agreements?status=active',
    },
    {
      testId: 'widget-mrr',
      title: 'MRR',
      value: formatCurrency(data.mrr),
      icon: DollarSign,
      iconBg: 'bg-blue-50',
      iconColor: 'text-blue-500',
      link: '/agreements',
    },
    {
      testId: 'widget-renewal-pipeline',
      title: 'Renewal Pipeline',
      value: String(data.renewal_pipeline_count),
      icon: RefreshCw,
      iconBg: 'bg-violet-50',
      iconColor: 'text-violet-500',
      link: '/agreements?status=pending_renewal',
    },
    {
      testId: 'widget-failed-payments',
      title: 'Failed Payments',
      value: String(data.failed_payment_count),
      subtitle: `${formatCurrency(data.failed_payment_amount)} at risk`,
      icon: AlertTriangle,
      iconBg: 'bg-red-50',
      iconColor: 'text-red-500',
      link: '/agreements?payment_status=past_due',
    },
  ] as const;

  return (
    <div
      className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4"
      data-testid="subscription-dashboard-widgets"
    >
      {widgets.map((w) => (
        <Link key={w.testId} to={w.link} className="block">
          <Card
            data-testid={w.testId}
            className="cursor-pointer transition-all hover:shadow-md"
          >
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div className="space-y-2">
                  <p className="text-sm font-semibold uppercase tracking-wider text-slate-400">
                    {w.title}
                  </p>
                  <div className="text-3xl font-bold text-slate-800">
                    {w.value}
                  </div>
                  {'subtitle' in w && w.subtitle && (
                    <p className="text-xs text-slate-400">{w.subtitle}</p>
                  )}
                </div>
                <div className={cn('p-3 rounded-xl', w.iconBg)}>
                  <w.icon className={cn('h-5 w-5', w.iconColor)} />
                </div>
              </div>
            </CardContent>
          </Card>
        </Link>
      ))}
    </div>
  );
}
