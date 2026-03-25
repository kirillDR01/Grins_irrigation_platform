import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { LoadingSpinner, ErrorMessage } from '@/shared/components';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { Users, Percent, Clock, Star } from 'lucide-react';
import { cn } from '@/shared/utils/cn';
import { useLeadAnalytics } from '../hooks';
import { ConversionFunnel } from './ConversionFunnel';
import { CampaignManager } from './CampaignManager';
import { BudgetTracker } from './BudgetTracker';
import { QRCodeGenerator } from './QRCodeGenerator';
import { CACChart } from './CACChart';
import type { DateRangePreset, DateRangeFilter } from '../types';

export function MarketingDashboard() {
  const [activeTab, setActiveTab] = useState('overview');
  const [datePreset, setDatePreset] = useState<DateRangePreset>('ytd');
  const [customStart, setCustomStart] = useState('');
  const [customEnd, setCustomEnd] = useState('');

  const dateRange: DateRangeFilter =
    datePreset === 'custom'
      ? { preset: 'custom', start_date: customStart, end_date: customEnd }
      : { preset: datePreset };

  const { data: analytics, isLoading, error } = useLeadAnalytics(dateRange);

  if (isLoading) return <LoadingSpinner />;
  if (error) return <ErrorMessage error={error} />;

  const metricsCards = [
    {
      title: 'Total Leads',
      value: analytics?.total_leads ?? 0,
      icon: Users,
      color: 'text-teal-500',
      bg: 'bg-teal-50',
      format: 'number' as const,
      testId: 'metric-total-leads',
    },
    {
      title: 'Conversion Rate',
      value: analytics?.conversion_rate ?? 0,
      icon: Percent,
      color: 'text-blue-500',
      bg: 'bg-blue-50',
      format: 'percent' as const,
      testId: 'metric-conversion-rate',
    },
    {
      title: 'Avg Time to Conversion',
      value: analytics?.avg_time_to_conversion_days ?? 0,
      icon: Clock,
      color: 'text-amber-500',
      bg: 'bg-amber-50',
      format: 'days' as const,
      testId: 'metric-avg-conversion-time',
    },
    {
      title: 'Top Source',
      value: analytics?.top_source ?? 'N/A',
      icon: Star,
      color: 'text-violet-500',
      bg: 'bg-violet-50',
      format: 'text' as const,
      testId: 'metric-top-source',
    },
  ];

  const formatValue = (value: string | number, format: string) => {
    if (format === 'percent') return `${(value as number).toFixed(1)}%`;
    if (format === 'days') return `${value} days`;
    if (format === 'number') return (value as number).toLocaleString();
    return String(value);
  };

  const leadSourceData = (analytics?.lead_sources ?? []).map((s) => ({
    source: s.source,
    count: s.count,
  }));

  return (
    <div data-testid="marketing-dashboard" className="space-y-6">
      {/* Date Range Picker */}
      <div className="flex items-end gap-4" data-testid="date-range-picker">
        <div className="space-y-1">
          <Label className="text-sm text-slate-500">Date Range</Label>
          <Select value={datePreset} onValueChange={(v) => setDatePreset(v as DateRangePreset)}>
            <SelectTrigger className="w-40" data-testid="date-range-select">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="month">This Month</SelectItem>
              <SelectItem value="quarter">This Quarter</SelectItem>
              <SelectItem value="ytd">Year to Date</SelectItem>
              <SelectItem value="custom">Custom Range</SelectItem>
            </SelectContent>
          </Select>
        </div>
        {datePreset === 'custom' && (
          <>
            <div className="space-y-1">
              <Label className="text-sm text-slate-500">Start</Label>
              <Input
                type="date"
                value={customStart}
                onChange={(e) => setCustomStart(e.target.value)}
                data-testid="date-range-start"
              />
            </div>
            <div className="space-y-1">
              <Label className="text-sm text-slate-500">End</Label>
              <Input
                type="date"
                value={customEnd}
                onChange={(e) => setCustomEnd(e.target.value)}
                data-testid="date-range-end"
              />
            </div>
          </>
        )}
      </div>

      {/* Key Metrics Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {metricsCards.map((card) => (
          <Card key={card.title} data-testid={card.testId}>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div className="space-y-1">
                  <p className="text-sm font-medium text-slate-500">{card.title}</p>
                  <p className="text-2xl font-bold text-slate-800">
                    {formatValue(card.value, card.format)}
                  </p>
                </div>
                <div className={cn('p-3 rounded-xl', card.bg)}>
                  <card.icon className={cn('h-5 w-5', card.color)} />
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList data-testid="marketing-tabs">
          <TabsTrigger value="overview" data-testid="tab-overview">
            Overview
          </TabsTrigger>
          <TabsTrigger value="campaigns" data-testid="tab-campaigns">
            Campaigns
          </TabsTrigger>
          <TabsTrigger value="budget" data-testid="tab-budget">
            Budget
          </TabsTrigger>
          <TabsTrigger value="qrcodes" data-testid="tab-qrcodes">
            QR Codes
          </TabsTrigger>
          <TabsTrigger value="cac" data-testid="tab-cac">
            CAC Analysis
          </TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-6 mt-4">
          {/* Lead Sources Chart */}
          <Card data-testid="lead-sources-chart">
            <CardHeader>
              <CardTitle className="text-lg">Lead Sources</CardTitle>
            </CardHeader>
            <CardContent>
              {leadSourceData.length === 0 ? (
                <p className="text-sm text-slate-500 text-center py-8">No lead source data</p>
              ) : (
                <ResponsiveContainer width="100%" height={350}>
                  <BarChart
                    data={leadSourceData}
                    margin={{ top: 5, right: 20, left: 10, bottom: 5 }}
                  >
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
                    />
                    <Tooltip
                      contentStyle={{
                        borderRadius: '8px',
                        border: '1px solid #e2e8f0',
                        boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
                      }}
                    />
                    <Bar dataKey="count" name="Leads" fill="#14b8a6" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              )}
            </CardContent>
          </Card>

          {/* Conversion Funnel */}
          <ConversionFunnel stages={analytics?.funnel ?? []} />

          {/* Advertising Channels Table */}
          <Card data-testid="advertising-channels">
            <CardHeader>
              <CardTitle className="text-lg">Advertising Channels</CardTitle>
            </CardHeader>
            <CardContent>
              {(analytics?.advertising_channels ?? []).length === 0 ? (
                <p className="text-sm text-slate-500 text-center py-4">
                  No advertising channel data
                </p>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Channel</TableHead>
                      <TableHead>Spend</TableHead>
                      <TableHead>Leads</TableHead>
                      <TableHead>Cost per Lead</TableHead>
                      <TableHead>Status</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {(analytics?.advertising_channels ?? []).map((ch) => (
                      <TableRow key={ch.channel} data-testid="ad-channel-row">
                        <TableCell className="font-medium">{ch.channel}</TableCell>
                        <TableCell>${ch.spend.toFixed(2)}</TableCell>
                        <TableCell>{ch.lead_count}</TableCell>
                        <TableCell>${ch.cost_per_lead.toFixed(2)}</TableCell>
                        <TableCell>
                          <span
                            className={cn(
                              'inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium',
                              ch.is_active
                                ? 'bg-emerald-100 text-emerald-700'
                                : 'bg-slate-100 text-slate-500',
                            )}
                          >
                            {ch.is_active ? 'Active' : 'Inactive'}
                          </span>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Campaigns Tab */}
        <TabsContent value="campaigns" className="mt-4">
          <CampaignManager />
        </TabsContent>

        {/* Budget Tab */}
        <TabsContent value="budget" className="mt-4">
          <BudgetTracker />
        </TabsContent>

        {/* QR Codes Tab */}
        <TabsContent value="qrcodes" className="mt-4">
          <QRCodeGenerator />
        </TabsContent>

        {/* CAC Analysis Tab */}
        <TabsContent value="cac" className="mt-4">
          <CACChart />
        </TabsContent>
      </Tabs>
    </div>
  );
}
