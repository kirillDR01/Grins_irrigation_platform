// ============================================================
// SalesPipeline.tsx — Pipeline List (replaces old SalesPipeline)
// Adapted from scaffold/PipelineList.tsx
// ============================================================

import { useState, useMemo, useCallback } from 'react';
import type React from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { Phone, Inbox, X } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table';
import { LoadingPage, ErrorMessage } from '@/shared/components';
import { useSalesPipeline } from '../hooks/useSalesPipeline';
import { useSalesMetrics } from '../hooks';
import { useStageAge, countStuck } from '../hooks/useStageAge';
import { AgeChip } from './AgeChip';
import {
  AGE_THRESHOLDS,
  SALES_STATUS_CONFIG,
  type SalesEntry,
  type SalesEntryStatus,
} from '../types/pipeline';

const ACTION_LABELS: Record<SalesEntryStatus, string | null> = {
  schedule_estimate:  'Schedule',
  estimate_scheduled: 'Send',
  send_estimate:      'Send',
  pending_approval:   'Nudge',
  send_contract:      'Convert',
  closed_won:         'View job',
  closed_lost:        null,
};

export function SalesPipeline() {
  const navigate = useNavigate();
  const [statusFilter, setStatusFilter] = useState<SalesEntryStatus | undefined>();
  const [stuckFilter, setStuckFilter] = useState(false);
  const [page, setPage] = useState(0);
  const pageSize = 50;

  const { data: metrics } = useSalesMetrics();
  const { data, isLoading, error, refetch } = useSalesPipeline({
    skip: page * pageSize,
    limit: pageSize,
    status: statusFilter,
  });

  const rows = useMemo(() => data?.items ?? [], [data?.items]);
  const followupCount = useMemo(() => countStuck(rows), [rows]);

  // stuckFilter: show only entries whose computed bucket is 'stuck'
  // Date.now() is captured outside useMemo to satisfy the react-compiler purity rule
  const nowRef = Date.now();
  const visibleRows = useMemo(() => {
    if (!stuckFilter) return rows;
    return rows.filter(r => {
      if (r.status === 'closed_won' || r.status === 'closed_lost') return false;
      const stageKey = r.status === 'estimate_scheduled' ? 'schedule_estimate' : r.status;
      const thresholds = AGE_THRESHOLDS[stageKey as keyof typeof AGE_THRESHOLDS];
      const ref = r.updated_at ?? r.created_at;
      const days = Math.floor((nowRef - new Date(ref).getTime()) / 86_400_000);
      return days > thresholds.staleMax;
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rows, stuckFilter]);

  const handleRowClick = useCallback(
    (entry: SalesEntry) => navigate(`/sales/${entry.id}`),
    [navigate],
  );

  const summary = [
    {
      title: 'Needs Estimate',
      value: data?.summary?.schedule_estimate ?? 0,
      testId: 'pipeline-summary-needs-estimate',
      onClick: () => {
        setStatusFilter(statusFilter === 'schedule_estimate' ? undefined : 'schedule_estimate');
        setPage(0);
      },
      bg: '',
    },
    {
      title: 'Pending Approval',
      value: data?.summary?.pending_approval ?? 0,
      testId: 'pipeline-summary-pending-approval',
      onClick: () => {
        setStatusFilter(statusFilter === 'pending_approval' ? undefined : 'pending_approval');
        setPage(0);
      },
      bg: '',
    },
    {
      title: 'Needs Follow-Up',
      value: followupCount,
      testId: 'pipeline-summary-needs-followup',
      onClick: () => setStuckFilter(v => !v),
      bg: 'bg-amber-50',
      delta: <FollowupDelta count={followupCount} />,
    },
    {
      title: 'Revenue Pipeline',
      value: `$${(metrics?.total_pipeline_revenue ?? 0).toLocaleString()}`,
      testId: 'pipeline-summary-revenue',
      onClick: undefined as (() => void) | undefined,
      bg: '',
      delta: undefined as React.ReactNode,
    },
  ];

  if (isLoading) return <LoadingPage message="Loading sales pipeline..." />;
  if (error)     return <ErrorMessage error={error} onRetry={() => refetch()} />;

  const totalPages = Math.ceil((data?.total ?? 0) / pageSize);

  return (
    <div data-testid="pipeline-list-page" className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {summary.map((c) => (
          <Card
            key={c.testId}
            data-testid={c.testId}
            className={[
              c.bg,
              c.onClick ? 'cursor-pointer hover:shadow-md transition-shadow' : '',
            ].join(' ')}
            onClick={c.onClick}
          >
            <CardContent className="p-6 space-y-1">
              <p className="text-sm font-medium text-slate-500">{c.title}</p>
              <p className="text-2xl font-bold text-slate-800">{c.value}</p>
              {c.delta}
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Active filters */}
      {(statusFilter || stuckFilter) && (
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-sm text-slate-500">Filtered by:</span>
          {statusFilter && (
            <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${SALES_STATUS_CONFIG[statusFilter]?.className}`}>
              {SALES_STATUS_CONFIG[statusFilter]?.label}
            </span>
          )}
          {stuckFilter && (
            <span
              className="inline-flex items-center gap-1 rounded-full border-[1.5px] border-red-500 bg-red-50 px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide text-red-700"
              data-testid="pipeline-filter-age-stuck"
            >
              ⚡ Stuck entries only
            </span>
          )}
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              setStatusFilter(undefined);
              setStuckFilter(false);
              setPage(0);
            }}
          >
            Clear
          </Button>
        </div>
      )}

      {/* Table */}
      <div className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow className="bg-slate-50/50 hover:bg-slate-50/50">
              <Th className="min-w-[180px]">Customer</Th>
              <Th className="w-[140px]">Phone</Th>
              <Th className="w-[160px]">Job Type</Th>
              <Th className="min-w-[260px]">Status</Th>
              <Th className="w-[140px]">Last Contact</Th>
              <Th className="w-[120px]">Actions</Th>
            </TableRow>
          </TableHeader>
          <TableBody className="divide-y divide-slate-50">
            {visibleRows.length ? (
              visibleRows.map(entry => (
                <PipelineRow
                  key={entry.id}
                  entry={entry}
                  onRowClick={handleRowClick}
                />
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={6} className="h-32 text-center">
                  <div className="flex flex-col items-center gap-2 text-slate-500">
                    <Inbox className="h-8 w-8 text-slate-300" />
                    <p className="text-sm">No sales entries found.</p>
                  </div>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>

        {data && data.total > 0 && (
          <div className="p-4 border-t border-slate-100 flex items-center justify-between">
            <div className="text-sm text-slate-500">
              Showing {Math.min(page * pageSize + 1, data.total)} to{' '}
              {Math.min((page + 1) * pageSize, data.total)} of {data.total} entries
            </div>
            <div className="flex items-center gap-2">
              <span className="text-sm text-slate-500">Page {page + 1} of {totalPages}</span>
              <Button variant="outline" size="sm" onClick={() => setPage(p => p - 1)} disabled={page === 0}>
                Previous
              </Button>
              <Button variant="outline" size="sm" onClick={() => setPage(p => p + 1)} disabled={page + 1 >= totalPages}>
                Next
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ────────── Row component ──────────

function PipelineRow({
  entry,
  onRowClick,
}: {
  entry: SalesEntry;
  onRowClick: (e: SalesEntry) => void;
}) {
  const age = useStageAge(entry);
  const statusConfig = SALES_STATUS_CONFIG[entry.status];
  const actionLabel = ACTION_LABELS[entry.status];
  const stageKey = entry.status === 'estimate_scheduled' ? 'schedule_estimate' : entry.status;
  const showAgeChip = entry.status !== 'closed_won' && entry.status !== 'closed_lost';

  return (
    <TableRow
      data-testid={`pipeline-row-${entry.id}`}
      className="hover:bg-slate-50/80 transition-colors cursor-pointer"
      onClick={() => onRowClick(entry)}
    >
      <TableCell className="px-6 py-4">
        <span
          className="text-sm font-semibold text-slate-700"
          title={entry.property_address ?? undefined}
        >
          {entry.customer_name ?? <i className="text-slate-400">Unknown</i>}
        </span>
      </TableCell>

      <TableCell className="px-6 py-4">
        {entry.customer_phone ? (
          <div className="flex items-center gap-2">
            <Phone className="h-3.5 w-3.5 text-slate-400" />
            <span className="text-sm text-slate-600">{entry.customer_phone}</span>
          </div>
        ) : (
          <span className="text-sm text-slate-400 italic">N/A</span>
        )}
      </TableCell>

      <TableCell className="px-6 py-4">
        <span className="text-sm text-slate-600">
          {entry.job_type ?? <i className="text-slate-400">N/A</i>}
        </span>
      </TableCell>

      <TableCell className="px-6 py-4">
        <span
          className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${statusConfig?.className ?? 'bg-slate-100 text-slate-700'}`}
        >
          {statusConfig?.label ?? entry.status}
        </span>
        {entry.override_flag && (
          <span className="ml-1 text-xs text-amber-600" title="Manually overridden">⚠</span>
        )}
        {showAgeChip && (
          <AgeChip
            age={age}
            stageKey={stageKey}
            data-testid={`pipeline-row-age-${entry.id}`}
          />
        )}
      </TableCell>

      <TableCell className="px-6 py-4">
        {entry.last_contact_date ? (
          <span className="text-sm text-slate-500" title={new Date(entry.last_contact_date).toLocaleString()}>
            {formatDistanceToNow(new Date(entry.last_contact_date), { addSuffix: true })}
          </span>
        ) : (
          <span className="text-sm text-slate-400 italic">Never</span>
        )}
      </TableCell>

      <TableCell className="px-6 py-4" onClick={e => e.stopPropagation()}>
        <div className="flex items-center gap-1">
          {actionLabel && (
            <Button
              size="sm"
              variant={entry.status === 'closed_won' ? 'ghost' : 'default'}
              data-testid={`pipeline-row-action-${entry.id}`}
              onClick={(e) => {
                e.stopPropagation();
                onRowClick(entry);
              }}
            >
              {actionLabel}
            </Button>
          )}
          <Button
            size="icon"
            variant="ghost"
            className="h-7 w-7"
            data-testid={`pipeline-row-dismiss-${entry.id}`}
            onClick={(e) => {
              e.stopPropagation();
              toast.info('Dismiss not wired yet — TODO(backend)');
            }}
          >
            <X className="h-3.5 w-3.5 text-slate-400" />
          </Button>
        </div>
      </TableCell>
    </TableRow>
  );
}

// ────────── Follow-up delta (WoW) ──────────

function FollowupDelta({ count }: { count: number }) {
  const key = 'sales_followup_prev_count';
  const weekKey = 'sales_followup_prev_week';
  const isoWeek = getIsoWeek(new Date());

  const prev = (() => {
    const storedWeek = localStorage.getItem(weekKey);
    if (storedWeek !== isoWeek) {
      localStorage.setItem(weekKey, isoWeek);
      localStorage.setItem(key, String(count));
      return count;
    }
    const raw = localStorage.getItem(key);
    return raw == null ? count : Number(raw);
  })();

  const delta = count - prev;
  if (delta === 0) {
    return (
      <span className="text-xs text-slate-500" data-testid="pipeline-summary-followup-delta">
        — same as last week
      </span>
    );
  }
  const up = delta > 0;
  return (
    <span
      className={`text-xs font-semibold ${up ? 'text-amber-600' : 'text-emerald-600'}`}
      data-testid="pipeline-summary-followup-delta"
    >
      {up ? '▲' : '▼'} {Math.abs(delta)} since last week
    </span>
  );
}

function getIsoWeek(d: Date): string {
  const date = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()));
  const dayNum = date.getUTCDay() || 7;
  date.setUTCDate(date.getUTCDate() + 4 - dayNum);
  const yearStart = new Date(Date.UTC(date.getUTCFullYear(), 0, 1));
  const weekNo = Math.ceil((((date.getTime() - yearStart.getTime()) / 86_400_000) + 1) / 7);
  return `${date.getUTCFullYear()}-W${String(weekNo).padStart(2, '0')}`;
}

function Th({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return (
    <TableHead className={`px-6 py-4 ${className}`}>
      <span className="text-slate-500 text-xs uppercase tracking-wider font-medium">
        {children}
      </span>
    </TableHead>
  );
}
