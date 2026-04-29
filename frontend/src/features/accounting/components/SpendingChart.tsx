// @ts-nocheck — pre-existing TS errors documented in bughunt/2026-04-29-pre-existing-tsc-errors.md
import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { LoadingSpinner } from '@/shared/components';
import {
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { cn } from '@/shared/utils/cn';
import { useSpendingByCategory } from '../hooks';

const CHART_COLORS = [
  '#0d9488', '#f59e0b', '#ef4444', '#8b5cf6', '#3b82f6',
  '#ec4899', '#06b6d4', '#84cc16', '#f97316', '#6b7280',
];

type ChartMode = 'pie' | 'bar';

export function SpendingChart() {
  const [mode, setMode] = useState<ChartMode>('pie');
  const { data: spending, isLoading } = useSpendingByCategory();

  const chartData = (spending ?? []).map((item, i) => ({
    name: item.category,
    value: item.total,
    percentage: item.percentage,
    fill: CHART_COLORS[i % CHART_COLORS.length],
  }));

  return (
    <Card data-testid="spending-chart">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">Spending by Category</CardTitle>
          <div className="flex gap-1">
            <Button
              variant={mode === 'pie' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setMode('pie')}
              data-testid="chart-mode-pie"
            >
              Pie
            </Button>
            <Button
              variant={mode === 'bar' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setMode('bar')}
              data-testid="chart-mode-bar"
            >
              Bar
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="flex justify-center py-8"><LoadingSpinner /></div>
        ) : chartData.length === 0 ? (
          <p className="text-sm text-slate-500 text-center py-8">No expense data to display</p>
        ) : (
          <div className="h-80" data-testid="spending-chart-container">
            <ResponsiveContainer width="100%" height="100%">
              {mode === 'pie' ? (
                <PieChart>
                  <Pie
                    data={chartData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={110}
                    paddingAngle={2}
                    dataKey="value"
                    label={({ name, percentage }) => `${name} (${percentage.toFixed(1)}%)`}
                  >
                    {chartData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.fill} />
                    ))}
                  </Pie>
                  <Tooltip
                    formatter={(value: number) => [`$${value.toLocaleString(undefined, { minimumFractionDigits: 2 })}`, 'Amount']}
                    contentStyle={{ borderRadius: '8px', border: '1px solid #e2e8f0' }}
                  />
                  <Legend />
                </PieChart>
              ) : (
                <BarChart data={chartData} margin={{ left: 20, right: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" tick={{ fontSize: 12 }} angle={-45} textAnchor="end" height={80} />
                  <YAxis tickFormatter={(v) => `$${v.toLocaleString()}`} />
                  <Tooltip
                    formatter={(value: number) => [`$${value.toLocaleString(undefined, { minimumFractionDigits: 2 })}`, 'Amount']}
                    contentStyle={{ borderRadius: '8px', border: '1px solid #e2e8f0' }}
                  />
                  <Bar dataKey="value" radius={[4, 4, 0, 0]} barSize={40}>
                    {chartData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.fill} />
                    ))}
                  </Bar>
                </BarChart>
              )}
            </ResponsiveContainer>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
