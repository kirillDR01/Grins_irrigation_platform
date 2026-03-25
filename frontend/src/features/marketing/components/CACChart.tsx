import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { LoadingSpinner, ErrorMessage } from '@/shared/components';
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
import { useCAC } from '../hooks';

const COLORS = [
  '#14b8a6', '#f59e0b', '#6366f1', '#ec4899', '#10b981',
  '#f97316', '#8b5cf6', '#06b6d4',
];

export function CACChart() {
  const { data: cacData, isLoading, error } = useCAC();

  if (isLoading) return <LoadingSpinner />;
  if (error) return <ErrorMessage error={error} />;

  const chartData = (cacData ?? []).map((item) => ({
    source: item.source,
    cac: item.cac,
    customers: item.converted_customers,
    spend: item.total_spend,
  }));

  return (
    <Card data-testid="cac-chart">
      <CardHeader>
        <CardTitle className="text-lg">Customer Acquisition Cost by Channel</CardTitle>
      </CardHeader>
      <CardContent>
        {chartData.length === 0 ? (
          <p className="text-sm text-slate-500 text-center py-8">No acquisition cost data available</p>
        ) : (
          <ResponsiveContainer width="100%" height={350}>
            <BarChart data={chartData} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis
                dataKey="source"
                tick={{ fontSize: 12, fill: '#64748b' }}
                tickLine={false}
                axisLine={{ stroke: '#e2e8f0' }}
              />
              <YAxis
                tick={{ fontSize: 12, fill: '#64748b' }}
                tickLine={false}
                axisLine={{ stroke: '#e2e8f0' }}
                tickFormatter={(v: number) => `$${v}`}
              />
              <Tooltip
                formatter={(value: number, name: string) => {
                  if (name === 'cac') return [`$${value.toFixed(2)}`, 'CAC'];
                  return [value, name];
                }}
                contentStyle={{
                  borderRadius: '8px',
                  border: '1px solid #e2e8f0',
                  boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
                }}
              />
              <Bar dataKey="cac" name="cac" radius={[4, 4, 0, 0]}>
                {chartData.map((_entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  );
}
