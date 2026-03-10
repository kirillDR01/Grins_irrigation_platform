import { Card, CardContent } from '@/components/ui/card';
import { LoadingSpinner } from '@/shared/components/LoadingSpinner';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { useAgreementMetrics } from '../hooks';
import {
  FileText,
  DollarSign,
  RefreshCw,
  TrendingDown,
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

function formatPercent(value: number): string {
  return `${value.toFixed(1)}%`;
}

interface KpiCardProps {
  title: string;
  value: string;
  icon: React.ElementType;
  iconBg: string;
  iconColor: string;
  testId: string;
}

function KpiCard({ title, value, icon: Icon, iconBg, iconColor, testId }: KpiCardProps) {
  return (
    <Card data-testid={testId}>
      <CardContent className="p-6">
        <div className="flex items-center justify-between">
          <div className="space-y-2">
            <p className="text-sm font-semibold uppercase tracking-wider text-slate-400">
              {title}
            </p>
            <div className="text-3xl font-bold text-slate-800">{value}</div>
          </div>
          <div className={cn('p-3 rounded-xl', iconBg)}>
            <Icon className={cn('h-5 w-5', iconColor)} />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export function BusinessMetricsCards() {
  const { data: metrics, isLoading, error } = useAgreementMetrics();

  if (isLoading) return <LoadingSpinner />;
  if (error) {
    return (
      <Alert variant="destructive" data-testid="metrics-error">
        <AlertDescription>Failed to load agreement metrics.</AlertDescription>
      </Alert>
    );
  }
  if (!metrics) return null;

  return (
    <div
      className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4"
      data-testid="business-metrics-cards"
    >
      <KpiCard
        title="Active Agreements"
        value={String(metrics.active_count)}
        icon={FileText}
        iconBg="bg-emerald-50"
        iconColor="text-emerald-500"
        testId="metric-active-agreements"
      />
      <KpiCard
        title="MRR"
        value={formatCurrency(metrics.mrr)}
        icon={DollarSign}
        iconBg="bg-blue-50"
        iconColor="text-blue-500"
        testId="metric-mrr"
      />
      <KpiCard
        title="Renewal Rate"
        value={formatPercent(metrics.renewal_rate)}
        icon={RefreshCw}
        iconBg="bg-violet-50"
        iconColor="text-violet-500"
        testId="metric-renewal-rate"
      />
      <KpiCard
        title="Churn Rate"
        value={formatPercent(metrics.churn_rate)}
        icon={TrendingDown}
        iconBg="bg-slate-50"
        iconColor="text-slate-500"
        testId="metric-churn-rate"
      />
      <KpiCard
        title="Past Due Amount"
        value={formatCurrency(metrics.past_due_amount)}
        icon={AlertTriangle}
        iconBg="bg-red-50"
        iconColor="text-red-500"
        testId="metric-past-due-amount"
      />
    </div>
  );
}
