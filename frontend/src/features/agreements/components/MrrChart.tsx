// @ts-nocheck — pre-existing TS errors documented in bughunt/2026-04-29-pre-existing-tsc-errors.md
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { LoadingSpinner } from '@/shared/components/LoadingSpinner';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { useMrrHistory } from '../hooks';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';

function formatCurrency(value: number | string): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(Number(value));
}

export function MrrChart() {
  const { data, isLoading, error } = useMrrHistory();

  if (isLoading) return <LoadingSpinner />;
  if (error) {
    return (
      <Alert variant="destructive" data-testid="mrr-chart-error">
        <AlertDescription>Failed to load MRR history.</AlertDescription>
      </Alert>
    );
  }
  if (!data?.data_points?.length) return null;

  const chartData = data.data_points.map((dp) => ({
    month: dp.month,
    mrr: Number(dp.mrr),
  }));

  return (
    <Card data-testid="mrr-chart">
      <CardHeader>
        <CardTitle className="text-base font-semibold">MRR Over Time</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="month" tick={{ fontSize: 12 }} />
            <YAxis tickFormatter={(v: number) => formatCurrency(v)} tick={{ fontSize: 12 }} />
            <Tooltip formatter={(value: number) => formatCurrency(value)} />
            <Line
              type="monotone"
              dataKey="mrr"
              stroke="#3b82f6"
              strokeWidth={2}
              dot={{ r: 3 }}
              name="MRR"
            />
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
