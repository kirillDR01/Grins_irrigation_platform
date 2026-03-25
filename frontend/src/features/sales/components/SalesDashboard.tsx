import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { LoadingSpinner, ErrorMessage } from '@/shared/components';
import { FileText, Clock, CheckCircle2, DollarSign } from 'lucide-react';
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
import { useSalesMetrics } from '../hooks';
import { EstimateBuilder } from './EstimateBuilder';
import { MediaLibrary } from './MediaLibrary';
import { DiagramBuilder } from './DiagramBuilder';
import { FollowUpQueue } from './FollowUpQueue';
import { EstimateList } from './EstimateList';

const FUNNEL_COLORS = ['#0d9488', '#14b8a6', '#5eead4', '#99f6e4'];

export function SalesDashboard() {
  const navigate = useNavigate();
  const { data: metrics, isLoading, error } = useSalesMetrics();
  const [activeTab, setActiveTab] = useState('overview');
  const [estimateFilter, setEstimateFilter] = useState('all');

  if (isLoading) return <LoadingSpinner />;
  if (error) return <ErrorMessage error={error} />;

  const funnelData = [
    { stage: 'Leads', count: (metrics?.estimates_needing_writeup_count ?? 0) + (metrics?.pending_approval_count ?? 0) + (metrics?.needs_followup_count ?? 0) },
    { stage: 'Estimates', count: (metrics?.pending_approval_count ?? 0) + (metrics?.needs_followup_count ?? 0) },
    { stage: 'Approved', count: Math.round(((metrics?.conversion_rate ?? 0) / 100) * ((metrics?.pending_approval_count ?? 0) + (metrics?.needs_followup_count ?? 0))) },
    { stage: 'Jobs', count: Math.round(((metrics?.conversion_rate ?? 0) / 100) * (metrics?.pending_approval_count ?? 0)) },
  ];

  const pipelineCards = [
    {
      title: 'Needs Estimate',
      value: metrics?.estimates_needing_writeup_count ?? 0,
      icon: FileText,
      color: 'text-orange-500',
      bg: 'bg-orange-50',
      filter: 'needs_estimate',
      testId: 'pipeline-needs-estimate',
    },
    {
      title: 'Pending Approval',
      value: metrics?.pending_approval_count ?? 0,
      icon: Clock,
      color: 'text-amber-500',
      bg: 'bg-amber-50',
      filter: 'pending_approval',
      testId: 'pipeline-pending-approval',
    },
    {
      title: 'Needs Follow-Up',
      value: metrics?.needs_followup_count ?? 0,
      icon: CheckCircle2,
      color: 'text-blue-500',
      bg: 'bg-blue-50',
      filter: 'needs_followup',
      testId: 'pipeline-needs-followup',
    },
    {
      title: 'Revenue Pipeline',
      value: `$${(metrics?.total_pipeline_revenue ?? 0).toLocaleString()}`,
      icon: DollarSign,
      color: 'text-emerald-500',
      bg: 'bg-emerald-50',
      filter: 'all',
      testId: 'pipeline-revenue',
    },
  ];

  return (
    <div data-testid="sales-dashboard" className="space-y-6">
      {/* Pipeline Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {pipelineCards.map((card) => (
          <Card
            key={card.title}
            className="cursor-pointer hover:shadow-md transition-shadow"
            data-testid={card.testId}
            onClick={() => {
              if (card.filter === 'needs_estimate') {
                navigate(`/leads?action_tag=${card.filter}`);
              } else {
                setEstimateFilter(card.filter === 'pending_approval' ? 'sent' : card.filter);
                setActiveTab('estimates');
              }
            }}
          >
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div className="space-y-1">
                  <p className="text-sm font-medium text-slate-500">{card.title}</p>
                  <p className="text-2xl font-bold text-slate-800">{card.value}</p>
                </div>
                <div className={`p-3 rounded-xl ${card.bg}`}>
                  <card.icon className={`h-5 w-5 ${card.color}`} />
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Tabs for sub-sections */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList data-testid="sales-tabs">
          <TabsTrigger value="overview" data-testid="tab-overview">Overview</TabsTrigger>
          <TabsTrigger value="estimate-builder" data-testid="tab-estimate-builder">Estimate Builder</TabsTrigger>
          <TabsTrigger value="media" data-testid="tab-media">Media Library</TabsTrigger>
          <TabsTrigger value="diagrams" data-testid="tab-diagrams">Diagrams</TabsTrigger>
          <TabsTrigger value="follow-ups" data-testid="tab-follow-ups">Follow-Up Queue</TabsTrigger>
          <TabsTrigger value="estimates" data-testid="tab-estimates">Estimates</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-6 mt-4">
          {/* Conversion Funnel Chart */}
          <Card data-testid="conversion-funnel">
            <CardHeader>
              <CardTitle className="text-lg">Conversion Funnel</CardTitle>
              <p className="text-sm text-slate-500">
                Lead to job conversion pipeline • {(metrics?.conversion_rate ?? 0).toFixed(1)}% conversion rate
              </p>
            </CardHeader>
            <CardContent>
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={funnelData} layout="vertical" margin={{ left: 20, right: 30 }}>
                    <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                    <XAxis type="number" />
                    <YAxis type="category" dataKey="stage" width={80} />
                    <Tooltip
                      formatter={(value: number) => [value, 'Count']}
                      contentStyle={{ borderRadius: '8px', border: '1px solid #e2e8f0' }}
                    />
                    <Bar dataKey="count" radius={[0, 4, 4, 0]} barSize={32}>
                      {funnelData.map((_entry, index) => (
                        <Cell key={`cell-${index}`} fill={FUNNEL_COLORS[index % FUNNEL_COLORS.length]} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="estimate-builder" className="mt-4">
          <EstimateBuilder />
        </TabsContent>

        <TabsContent value="media" className="mt-4">
          <MediaLibrary />
        </TabsContent>

        <TabsContent value="diagrams" className="mt-4">
          <DiagramBuilder />
        </TabsContent>

        <TabsContent value="follow-ups" className="mt-4">
          <FollowUpQueue />
        </TabsContent>

        <TabsContent value="estimates" className="mt-4">
          <EstimateList initialFilter={estimateFilter} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
