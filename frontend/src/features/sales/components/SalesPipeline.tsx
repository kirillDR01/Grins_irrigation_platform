import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Phone, Inbox } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { LoadingPage, ErrorMessage } from '@/shared/components';
import { useSalesPipeline } from '../hooks/useSalesPipeline';
import { useSalesMetrics } from '../hooks';
import { StatusActionButton } from './StatusActionButton';
import {
  SALES_STATUS_CONFIG,
  type SalesEntry,
  type SalesEntryStatus,
} from '../types/pipeline';
import { formatDistanceToNow } from 'date-fns';

export function SalesPipeline() {
  const navigate = useNavigate();
  const [statusFilter, setStatusFilter] = useState<string | undefined>();
  const [page, setPage] = useState(0);
  const pageSize = 50;

  const { data: metrics } = useSalesMetrics();
  const { data, isLoading, error, refetch } = useSalesPipeline({
    skip: page * pageSize,
    limit: pageSize,
    status: statusFilter,
  });

  const handleRowClick = useCallback(
    (entry: SalesEntry) => {
      navigate(`/sales/${entry.id}`);
    },
    [navigate],
  );

  // 4 summary boxes migrated from Work Requests / old Sales Dashboard
  const summaryCards = [
    {
      title: 'Needs Estimate',
      value: metrics?.estimates_needing_writeup_count ?? data?.summary?.schedule_estimate ?? 0,
      color: 'text-orange-500',
      bg: 'bg-orange-50',
      filter: 'schedule_estimate',
      testId: 'pipeline-needs-estimate',
    },
    {
      title: 'Pending Approval',
      value: metrics?.pending_approval_count ?? data?.summary?.pending_approval ?? 0,
      color: 'text-amber-500',
      bg: 'bg-amber-50',
      filter: 'pending_approval',
      testId: 'pipeline-pending-approval',
    },
    {
      title: 'Needs Follow-Up',
      value: metrics?.needs_followup_count ?? data?.summary?.send_estimate ?? 0,
      color: 'text-blue-500',
      bg: 'bg-blue-50',
      filter: 'send_estimate',
      testId: 'pipeline-needs-followup',
    },
    {
      title: 'Revenue Pipeline',
      value: `$${(metrics?.total_pipeline_revenue ?? 0).toLocaleString()}`,
      color: 'text-emerald-500',
      bg: 'bg-emerald-50',
      filter: undefined,
      testId: 'pipeline-revenue',
    },
  ];

  if (isLoading) {
    return (
      <div data-testid="loading-spinner">
        <LoadingPage message="Loading sales pipeline..." />
      </div>
    );
  }

  if (error) {
    return (
      <div data-testid="error-message">
        <ErrorMessage error={error} onRetry={() => refetch()} />
      </div>
    );
  }

  const totalPages = Math.ceil((data?.total ?? 0) / pageSize);

  return (
    <div data-testid="sales-pipeline-page" className="space-y-6">
      {/* Summary Boxes */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {summaryCards.map((card) => (
          <Card
            key={card.testId}
            className="cursor-pointer hover:shadow-md transition-shadow"
            data-testid={card.testId}
            onClick={() => {
              setStatusFilter(
                statusFilter === card.filter ? undefined : card.filter,
              );
              setPage(0);
            }}
          >
            <CardContent className="p-6">
              <div className="space-y-1">
                <p className="text-sm font-medium text-slate-500">
                  {card.title}
                </p>
                <p className="text-2xl font-bold text-slate-800">
                  {card.value}
                </p>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Active filter indicator */}
      {statusFilter && (
        <div className="flex items-center gap-2">
          <span className="text-sm text-slate-500">Filtered by:</span>
          <span
            className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${SALES_STATUS_CONFIG[statusFilter as SalesEntryStatus]?.className ?? 'bg-slate-100 text-slate-700'}`}
          >
            {SALES_STATUS_CONFIG[statusFilter as SalesEntryStatus]?.label ??
              statusFilter}
          </span>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              setStatusFilter(undefined);
              setPage(0);
            }}
          >
            Clear
          </Button>
        </div>
      )}

      {/* Pipeline Table */}
      <div className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
        <Table data-testid="sales-pipeline-table">
          <TableHeader>
            <TableRow className="bg-slate-50/50 hover:bg-slate-50/50">
              <TableHead className="px-6 py-4">
                <span className="text-slate-500 text-xs uppercase tracking-wider font-medium">
                  Customer Name
                </span>
              </TableHead>
              <TableHead className="px-6 py-4">
                <span className="text-slate-500 text-xs uppercase tracking-wider font-medium">
                  Phone
                </span>
              </TableHead>
              <TableHead className="px-6 py-4">
                <span className="text-slate-500 text-xs uppercase tracking-wider font-medium">
                  Address
                </span>
              </TableHead>
              <TableHead className="px-6 py-4">
                <span className="text-slate-500 text-xs uppercase tracking-wider font-medium">
                  Job Type
                </span>
              </TableHead>
              <TableHead className="px-6 py-4">
                <span className="text-slate-500 text-xs uppercase tracking-wider font-medium">
                  Status
                </span>
              </TableHead>
              <TableHead className="px-6 py-4">
                <span className="text-slate-500 text-xs uppercase tracking-wider font-medium">
                  Last Contact
                </span>
              </TableHead>
              <TableHead className="px-6 py-4">
                <span className="text-slate-500 text-xs uppercase tracking-wider font-medium">
                  Actions
                </span>
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody className="divide-y divide-slate-50">
            {data?.items.length ? (
              data.items.map((entry) => (
                <TableRow
                  key={entry.id}
                  data-testid="sales-pipeline-row"
                  className="hover:bg-slate-50/80 transition-colors cursor-pointer"
                  onClick={() => handleRowClick(entry)}
                >
                  <TableCell className="px-6 py-4">
                    <span className="text-sm font-medium text-slate-700">
                      {entry.customer_name ?? (
                        <span className="text-slate-400 italic">Unknown</span>
                      )}
                    </span>
                  </TableCell>
                  <TableCell className="px-6 py-4">
                    {entry.customer_phone ? (
                      <div className="flex items-center gap-2">
                        <Phone className="h-3.5 w-3.5 text-slate-400" />
                        <span className="text-sm text-slate-600">
                          {entry.customer_phone}
                        </span>
                      </div>
                    ) : (
                      <span className="text-sm text-slate-400 italic">N/A</span>
                    )}
                  </TableCell>
                  <TableCell className="px-6 py-4">
                    <span className="text-sm text-slate-600 max-w-[200px] truncate block">
                      {entry.property_address ?? (
                        <span className="text-slate-400 italic">N/A</span>
                      )}
                    </span>
                  </TableCell>
                  <TableCell className="px-6 py-4">
                    <span className="text-sm text-slate-600">
                      {entry.job_type ?? (
                        <span className="text-slate-400 italic">N/A</span>
                      )}
                    </span>
                  </TableCell>
                  <TableCell className="px-6 py-4">
                    <span
                      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${SALES_STATUS_CONFIG[entry.status]?.className ?? 'bg-slate-100 text-slate-700'}`}
                      data-testid={`status-${entry.status}`}
                    >
                      {SALES_STATUS_CONFIG[entry.status]?.label ?? entry.status}
                    </span>
                    {entry.override_flag && (
                      <span className="ml-1 text-xs text-amber-600" title="Status was manually overridden">
                        ⚠
                      </span>
                    )}
                  </TableCell>
                  <TableCell className="px-6 py-4">
                    {entry.last_contact_date ? (
                      <span
                        className="text-sm text-slate-500"
                        title={new Date(
                          entry.last_contact_date,
                        ).toLocaleString()}
                      >
                        {formatDistanceToNow(
                          new Date(entry.last_contact_date),
                          { addSuffix: true },
                        )}
                      </span>
                    ) : (
                      <span className="text-sm text-slate-400 italic">
                        Never
                      </span>
                    )}
                  </TableCell>
                  <TableCell className="px-6 py-4">
                    <StatusActionButton entry={entry} />
                  </TableCell>
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={7} className="h-32 text-center">
                  <div className="flex flex-col items-center gap-2 text-slate-500">
                    <Inbox className="h-8 w-8 text-slate-300" />
                    <p className="text-sm">No sales entries found.</p>
                  </div>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>

        {/* Pagination */}
        {data && data.total > 0 && (
          <div className="p-4 border-t border-slate-100 flex items-center justify-between">
            <div className="text-sm text-slate-500">
              Showing {Math.min(page * pageSize + 1, data.total)} to{' '}
              {Math.min((page + 1) * pageSize, data.total)} of {data.total}{' '}
              entries
            </div>
            <div className="flex items-center gap-2">
              <span className="text-sm text-slate-500">
                Page {page + 1} of {totalPages}
              </span>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage((p) => p - 1)}
                disabled={page === 0}
              >
                Previous
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage((p) => p + 1)}
                disabled={page + 1 >= totalPages}
              >
                Next
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
