import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { LoadingSpinner } from '@/shared/components/LoadingSpinner';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { useTierDistribution } from '../hooks';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';

const TIER_COLORS = [
  '#10b981', // emerald
  '#3b82f6', // blue
  '#8b5cf6', // violet
  '#f59e0b', // amber
  '#ef4444', // red
  '#6366f1', // indigo
];

export function TierDistributionChart() {
  const { data, isLoading, error } = useTierDistribution();

  if (isLoading) return <LoadingSpinner />;
  if (error) {
    return (
      <Alert variant="destructive" data-testid="tier-distribution-chart-error">
        <AlertDescription>Failed to load tier distribution.</AlertDescription>
      </Alert>
    );
  }
  if (!data?.items?.length) return null;

  const chartData = data.items.map((item) => ({
    name: `${item.tier_name} (${item.package_type})`,
    count: item.active_count,
  }));

  return (
    <Card data-testid="tier-distribution-chart">
      <CardHeader>
        <CardTitle className="text-base font-semibold">Agreements by Tier</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" tick={{ fontSize: 11 }} angle={-20} textAnchor="end" height={60} />
            <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
            <Tooltip />
            <Bar dataKey="count" name="Active Agreements" radius={[4, 4, 0, 0]}>
              {chartData.map((_, index) => (
                <Cell key={`cell-${index}`} fill={TIER_COLORS[index % TIER_COLORS.length]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
