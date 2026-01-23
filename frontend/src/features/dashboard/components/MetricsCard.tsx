/**
 * MetricsCard component for displaying dashboard metrics.
 * Shows a metric value with label, description, and optional icon.
 */

import { memo, type ComponentType } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import type { LucideProps } from 'lucide-react';

export interface MetricsCardProps {
  title: string;
  value: number | string;
  description?: string;
  icon?: ComponentType<LucideProps>;
  trend?: {
    value: number;
    isPositive: boolean;
  };
  testId?: string;
}

export const MetricsCard = memo(function MetricsCard({
  title,
  value,
  description,
  icon: Icon,
  trend,
  testId,
}: MetricsCardProps) {
  return (
    <Card data-testid={testId}>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        {Icon && <Icon className="h-4 w-4 text-muted-foreground" />}
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        {description && (
          <p className="text-xs text-muted-foreground">{description}</p>
        )}
        {trend && (
          <p
            className={`text-xs ${
              trend.isPositive ? 'text-green-600' : 'text-red-600'
            }`}
          >
            {trend.isPositive ? '+' : '-'}
            {Math.abs(trend.value)}% from last period
          </p>
        )}
      </CardContent>
    </Card>
  );
});
