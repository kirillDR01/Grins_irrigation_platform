import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { LoadingSpinner, ErrorMessage } from '@/shared/components';
import { DollarSign, TrendingUp, TrendingDown, Percent, AlertTriangle, Clock } from 'lucide-react';
import { cn } from '@/shared/utils/cn';
import { useAccountingSummary, usePendingInvoices, usePastDueInvoices } from '../hooks';
import { ExpenseTracker } from './ExpenseTracker';
import { SpendingChart } from './SpendingChart';
import { TaxPreparation } from './TaxPreparation';
import { TaxProjection } from './TaxProjection';
import { ConnectedAccounts } from './ConnectedAccounts';
import { AuditLog } from './AuditLog';
import type { DateRangePreset, DateRangeFilter } from '../types';

export function AccountingDashboard() {
  const [activeTab, setActiveTab] = useState('overview');
  const [datePreset, setDatePreset] = useState<DateRangePreset>('ytd');
  const [customStart, setCustomStart] = useState('');
  const [customEnd, setCustomEnd] = useState('');

  const dateRange: DateRangeFilter = datePreset === 'custom'
    ? { preset: 'custom', start_date: customStart, end_date: customEnd }
    : { preset: datePreset };

  const { data: summary, isLoading, error } = useAccountingSummary(dateRange);
  const { data: pendingInvoices } = usePendingInvoices();
  const { data: pastDueInvoices } = usePastDueInvoices();

  if (isLoading) return <LoadingSpinner />;
  if (error) return <ErrorMessage error={error} />;

  const metricsCards = [
    {
      title: 'YTD Revenue',
      value: summary?.ytd_revenue ?? 0,
      icon: DollarSign,
      color: 'text-emerald-500',
      bg: 'bg-emerald-50',
      format: 'currency',
      testId: 'metric-ytd-revenue',
    },
    {
      title: 'YTD Expenses',
      value: summary?.ytd_expenses ?? 0,
      icon: TrendingDown,
      color: 'text-red-500',
      bg: 'bg-red-50',
      format: 'currency',
      testId: 'metric-ytd-expenses',
    },
    {
      title: 'YTD Profit',
      value: summary?.ytd_profit ?? 0,
      icon: TrendingUp,
      color: 'text-blue-500',
      bg: 'bg-blue-50',
      format: 'currency',
      testId: 'metric-ytd-profit',
    },
    {
      title: 'Profit Margin',
      value: summary?.profit_margin ?? 0,
      icon: Percent,
      color: 'text-violet-500',
      bg: 'bg-violet-50',
      format: 'percent',
      testId: 'metric-profit-margin',
    },
  ];

  const formatValue = (value: number, format: string) => {
    if (format === 'currency') return `$${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    if (format === 'percent') return `${value.toFixed(1)}%`;
    return String(value);
  };

  return (
    <div data-testid="accounting-dashboard" className="space-y-6">
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

      {/* Metrics Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {metricsCards.map((card) => (
          <Card key={card.title} data-testid={card.testId}>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div className="space-y-1">
                  <p className="text-sm font-medium text-slate-500">{card.title}</p>
                  <p className={cn('text-2xl font-bold', card.title === 'YTD Profit' && (summary?.ytd_profit ?? 0) < 0 ? 'text-red-600' : 'text-slate-800')}>
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
        <TabsList data-testid="accounting-tabs">
          <TabsTrigger value="overview" data-testid="tab-overview">Overview</TabsTrigger>
          <TabsTrigger value="expenses" data-testid="tab-expenses">Expenses</TabsTrigger>
          <TabsTrigger value="tax" data-testid="tab-tax">Tax</TabsTrigger>
          <TabsTrigger value="connected" data-testid="tab-connected">Connected Accounts</TabsTrigger>
          <TabsTrigger value="audit" data-testid="tab-audit">Audit Log</TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-6 mt-4">
          {/* Pending Invoices */}
          <Card data-testid="pending-invoices-section">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg flex items-center gap-2">
                  <Clock className="h-5 w-5 text-amber-500" />
                  Pending Invoices
                </CardTitle>
                <span className="text-sm text-slate-500">
                  {summary?.pending_invoice_count ?? 0} invoices •{' '}
                  ${(summary?.pending_invoice_total ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                </span>
              </div>
            </CardHeader>
            <CardContent>
              {(pendingInvoices?.items?.length ?? 0) > 0 ? (
                <div className="divide-y">
                  {pendingInvoices?.items.map((inv) => (
                    <div key={inv.id} className="flex items-center justify-between py-3" data-testid="pending-invoice-row">
                      <div>
                        <p className="font-medium text-slate-800">{inv.invoice_number}</p>
                        <p className="text-sm text-slate-500">{inv.customer_name}</p>
                      </div>
                      <div className="text-right">
                        <p className="font-medium">${inv.total_amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}</p>
                        <p className="text-sm text-slate-500">Due {new Date(inv.due_date).toLocaleDateString()}</p>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-slate-500 text-center py-4">No pending invoices</p>
              )}
            </CardContent>
          </Card>

          {/* Past Due Invoices */}
          <Card data-testid="past-due-invoices-section">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg flex items-center gap-2">
                  <AlertTriangle className="h-5 w-5 text-red-500" />
                  Past Due Invoices
                </CardTitle>
                <span className="text-sm text-red-500 font-medium">
                  {summary?.past_due_invoice_count ?? 0} invoices •{' '}
                  ${(summary?.past_due_invoice_total ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                </span>
              </div>
            </CardHeader>
            <CardContent>
              {(pastDueInvoices?.items?.length ?? 0) > 0 ? (
                <div className="divide-y">
                  {pastDueInvoices?.items.map((inv) => (
                    <div key={inv.id} className="flex items-center justify-between py-3" data-testid="past-due-invoice-row">
                      <div>
                        <p className="font-medium text-slate-800">{inv.invoice_number}</p>
                        <p className="text-sm text-slate-500">{inv.customer_name}</p>
                      </div>
                      <div className="text-right">
                        <p className="font-medium text-red-600">${inv.total_amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}</p>
                        <p className="text-sm text-red-500">{inv.days_past_due} days past due</p>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-slate-500 text-center py-4">No past due invoices</p>
              )}
            </CardContent>
          </Card>

          {/* Spending Chart */}
          <SpendingChart />
        </TabsContent>

        {/* Expenses Tab */}
        <TabsContent value="expenses" className="space-y-6 mt-4">
          <ExpenseTracker />
          <SpendingChart />
        </TabsContent>

        {/* Tax Tab */}
        <TabsContent value="tax" className="space-y-6 mt-4">
          <TaxPreparation />
          <TaxProjection />
        </TabsContent>

        {/* Connected Accounts Tab */}
        <TabsContent value="connected" className="mt-4">
          <ConnectedAccounts />
        </TabsContent>

        {/* Audit Log Tab */}
        <TabsContent value="audit" className="mt-4">
          <AuditLog />
        </TabsContent>
      </Tabs>
    </div>
  );
}
