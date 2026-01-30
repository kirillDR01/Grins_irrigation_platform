/**
 * MetricsCard component for displaying dashboard metrics.
 * Shows a metric value with label, description, and optional icon.
 */

import { memo, type ComponentType } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import type { LucideProps } from 'lucide-react';
import { cn } from '@/lib/utils';

export type MetricsCardVariant = 'teal' | 'violet' | 'emerald' | 'blue';

export interface MetricsCardProps {
  title: string;
  value: number | string;
  description?: string;
  icon?: ComponentType<LucideProps>;
  variant?: MetricsCardVariant;
  trend?: {
    value: number;
    isPositive: boolean;
  };
  testId?: string;
}

const variantStyles: Record<MetricsCardVariant, { bg: string; text: string }> = {
  teal: { bg: 'bg-teal-50', text: 'text-teal-500' },
  violet: { bg: 'bg-violet-50', text: 'text-violet-500' },
  emerald: { bg: 'bg-emerald-50', text: 'text-emerald-500' },
  blue: { bg: 'bg-blue-50', text: 'text-blue-500' },
};

export const MetricsCard = memo(function MetricsCard({
  title,
  value,
  description,
  icon: Icon,
  variant = 'teal',
  trend,
  testId,
}: MetricsCardProps) {
  const styles = variantStyles[variant];

  return (
    <Card data-testid={testId || 'metrics-card'} className="relative">
      <CardContent className="p-6">
        {Icon && (
          <div
            className={cn(
              'absolute top-4 right-4 p-3 rounded-xl',
              styles.bg
            )}
          >
            <Icon className={cn('h-5 w-5', styles.text)} />
          </div>
        )}
        <div className="space-y-2">
          <p className="text-sm font-semibold uppercase tracking-wider text-slate-400">
            {title}
          </p>
          <div className="text-3xl font-bold text-slate-800">{value}</div>
          {description && (
            <p className="text-xs text-slate-400">{description}</p>
          )}
          {trend && (
            <p
              className={cn(
                'text-xs font-medium',
                trend.isPositive ? 'text-emerald-600' : 'text-red-600'
              )}
            >
              {trend.isPositive ? '+' : '-'}
              {Math.abs(trend.value)}% from last period
            </p>
          )}
        </div>
      </CardContent>
    </Card>
  );
});
