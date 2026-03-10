import { Link } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { LoadingSpinner } from '@/shared/components/LoadingSpinner';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { useDashboardSummary, useLeadMetricsBySource } from '../hooks';
import { Funnel, Users, Clock } from 'lucide-react';
import { cn } from '@/lib/utils';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts';

const SOURCE_COLORS: Record<string, string> = {
  website: '#3b82f6',
  phone_call: '#8b5cf6',
  google_form: '#10b981',
  referral: '#f59e0b',
  social_media: '#ec4899',
  other: '#6b7280',
};

function getSourceColor(source: string): string {
  return SOURCE_COLORS[source.toLowerCase()] ?? '#6b7280';
}

function formatSourceLabel(source: string): string {
  return source
    .split('_')
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ');
}

function formatAge(hours: number | null): string {
  if (hours === null || hours === 0) return 'None';
  if (hours < 1) return '<1h ago';
  if (hours < 24) return `${Math.round(hours)}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export function LeadDashboardWidgets() {
  const { data: summary, isLoading: summaryLoading, error: summaryError } = useDashboardSummary();
  const { data: sourceMetrics, isLoading: sourceLoading, error: sourceError } = useLeadMetricsBySource();

  if (summaryLoading && sourceLoading) return <LoadingSpinner />;

  const hasError = summaryError && sourceError;
  if (hasError) {
    return (
      <Alert variant="destructive" data-testid="lead-widgets-error">
        <AlertDescription>Failed to load lead metrics.</AlertDescription>
      </Alert>
    );
  }

  const oldestAge = summary?.leads_awaiting_contact_oldest_age_hours ?? null;
  const urgencyColor =
    oldestAge === null || oldestAge === 0
      ? 'text-green-600'
      : oldestAge < 12
        ? 'text-amber-600'
        : 'text-red-600';

  const chartData = (sourceMetrics?.items ?? []).map((item) => ({
    name: formatSourceLabel(item.lead_source),
    value: item.count,
    fill: getSourceColor(item.lead_source),
  }));

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      {/* Leads Awaiting Contact */}
      <Link to="/leads?status=new" className="block">
        <Card
          data-testid="widget-leads-awaiting-contact"
          className="cursor-pointer transition-all hover:shadow-md h-full"
        >
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div className="space-y-2">
                <p className="text-sm font-semibold uppercase tracking-wider text-slate-400">
                  Leads Awaiting Contact
                </p>
                <div className="text-3xl font-bold text-slate-800">
                  {summary?.new_leads_count ?? 0}
                </div>
                <div className={cn('flex items-center gap-1 text-xs font-medium', urgencyColor)}>
                  <Clock className="h-3 w-3" />
                  <span>Oldest: {formatAge(oldestAge)}</span>
                </div>
              </div>
              <div className="p-3 rounded-xl bg-amber-50">
                <Users className="h-5 w-5 text-amber-500" />
              </div>
            </div>
          </CardContent>
        </Card>
      </Link>

      {/* Follow-Up Queue */}
      <Link to="/leads?intake_tag=follow_up" className="block">
        <Card
          data-testid="widget-follow-up-queue"
          className="cursor-pointer transition-all hover:shadow-md h-full"
        >
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div className="space-y-2">
                <p className="text-sm font-semibold uppercase tracking-wider text-slate-400">
                  Follow-Up Queue
                </p>
                <div className="text-3xl font-bold text-slate-800">
                  {summary?.follow_up_queue_count ?? 0}
                </div>
                <p className="text-xs text-slate-400">Needs human review</p>
              </div>
              <div className="p-3 rounded-xl bg-orange-50">
                <Funnel className="h-5 w-5 text-orange-500" />
              </div>
            </div>
          </CardContent>
        </Card>
      </Link>

      {/* Leads by Source Chart */}
      <Card data-testid="widget-leads-by-source" className="h-full">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-semibold uppercase tracking-wider text-slate-400">
            Leads by Source
          </CardTitle>
        </CardHeader>
        <CardContent className="pb-4">
          {sourceLoading ? (
            <LoadingSpinner />
          ) : chartData.length === 0 ? (
            <p className="text-sm text-slate-400 text-center py-4">No lead data</p>
          ) : (
            <ResponsiveContainer width="100%" height={160}>
              <PieChart>
                <Pie
                  data={chartData}
                  dataKey="value"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  outerRadius={55}
                  innerRadius={30}
                >
                  {chartData.map((entry, i) => (
                    <Cell key={i} fill={entry.fill} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend
                  layout="vertical"
                  align="right"
                  verticalAlign="middle"
                  iconSize={8}
                  wrapperStyle={{ fontSize: '11px' }}
                />
              </PieChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
