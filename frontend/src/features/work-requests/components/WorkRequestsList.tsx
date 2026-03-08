import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  flexRender,
  getCoreRowModel,
  useReactTable,
  type ColumnDef,
} from '@tanstack/react-table';
import axios from 'axios';
import { Phone, Mail, Inbox, RefreshCw } from 'lucide-react';
import { toast } from 'sonner';
import { formatDistanceToNow } from 'date-fns';
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
import { useWorkRequests, useTriggerSync } from '../hooks/useWorkRequests';
import { ProcessingStatusBadge } from './ProcessingStatusBadge';
import { SyncStatusBar } from './SyncStatusBar';
import { WorkRequestFilters } from './WorkRequestFilters';
import type { WorkRequest, WorkRequestListParams } from '../types';
import { CLIENT_TYPE_LABELS, type SheetClientType } from '../types';

export function WorkRequestsList() {
  const navigate = useNavigate();
  const [params, setParams] = useState<WorkRequestListParams>({
    page: 1,
    page_size: 20,
    sort_by: 'imported_at',
    sort_order: 'desc',
  });

  const { data, isLoading, error, refetch } = useWorkRequests(params);
  const triggerSync = useTriggerSync();

  const handleFilterChange = useCallback(
    (changes: Partial<WorkRequestListParams>) => {
      setParams((prev) => ({ ...prev, ...changes }));
    },
    []
  );

  const handleRowClick = useCallback(
    (row: WorkRequest) => {
      navigate(`/work-requests/${row.id}`);
    },
    [navigate]
  );

  const columns: ColumnDef<WorkRequest>[] = [
    {
      accessorKey: 'name',
      header: () => (
        <span className="text-slate-500 text-xs uppercase tracking-wider font-medium">
          Name
        </span>
      ),
      cell: ({ row }) => (
        <span className="text-sm font-medium text-slate-700">
          {row.original.name ?? <span className="text-slate-400 italic">N/A</span>}
        </span>
      ),
    },
    {
      accessorKey: 'phone',
      header: () => (
        <span className="text-slate-500 text-xs uppercase tracking-wider font-medium">
          Phone
        </span>
      ),
      cell: ({ row }) =>
        row.original.phone ? (
          <div className="flex items-center gap-2">
            <Phone className="h-3.5 w-3.5 text-slate-400" />
            <span className="text-sm text-slate-600">{row.original.phone}</span>
          </div>
        ) : (
          <span className="text-sm text-slate-400 italic">N/A</span>
        ),
    },
    {
      accessorKey: 'email',
      header: () => (
        <span className="text-slate-500 text-xs uppercase tracking-wider font-medium">
          Email
        </span>
      ),
      cell: ({ row }) =>
        row.original.email ? (
          <div className="flex items-center gap-2">
            <Mail className="h-3.5 w-3.5 text-slate-400" />
            <span className="text-sm text-slate-600">{row.original.email}</span>
          </div>
        ) : (
          <span className="text-sm text-slate-400 italic">N/A</span>
        ),
    },
    {
      accessorKey: 'client_type',
      header: () => (
        <span className="text-slate-500 text-xs uppercase tracking-wider font-medium">
          Client Type
        </span>
      ),
      cell: ({ row }) => {
        const ct = row.original.client_type;
        return (
          <span className="text-sm text-slate-600">
            {ct && ct in CLIENT_TYPE_LABELS
              ? CLIENT_TYPE_LABELS[ct as SheetClientType]
              : ct ?? <span className="text-slate-400 italic">N/A</span>}
          </span>
        );
      },
    },
    {
      accessorKey: 'property_type',
      header: () => (
        <span className="text-slate-500 text-xs uppercase tracking-wider font-medium">
          Property
        </span>
      ),
      cell: ({ row }) => (
        <span className="text-sm text-slate-600">
          {row.original.property_type ?? <span className="text-slate-400 italic">N/A</span>}
        </span>
      ),
    },
    {
      accessorKey: 'processing_status',
      header: () => (
        <span className="text-slate-500 text-xs uppercase tracking-wider font-medium">
          Status
        </span>
      ),
      cell: ({ row }) => (
        <ProcessingStatusBadge status={row.original.processing_status} />
      ),
    },
    {
      accessorKey: 'date_work_needed_by',
      header: () => (
        <span className="text-slate-500 text-xs uppercase tracking-wider font-medium">
          Needed By
        </span>
      ),
      cell: ({ row }) => (
        <span className="text-sm text-slate-600">
          {row.original.date_work_needed_by ?? (
            <span className="text-slate-400 italic">N/A</span>
          )}
        </span>
      ),
    },
    {
      accessorKey: 'imported_at',
      header: () => (
        <span className="text-slate-500 text-xs uppercase tracking-wider font-medium">
          Imported
        </span>
      ),
      cell: ({ row }) => {
        const date = new Date(row.original.imported_at);
        return (
          <span className="text-sm text-slate-500" title={date.toLocaleString()}>
            {formatDistanceToNow(date, { addSuffix: true })}
          </span>
        );
      },
    },
  ];

  const table = useReactTable({
    data: data?.items ?? [],
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  if (isLoading) {
    return (
      <div data-testid="loading-spinner">
        <LoadingPage message="Loading work requests..." />
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

  return (
    <div data-testid="work-requests-page" className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Work Requests</h1>
          <div className="flex items-center gap-4 mt-1">
            {data && (
              <p className="text-sm text-slate-500" data-testid="submission-count">
                {data.total} {data.total === 1 ? 'submission' : 'submissions'} total
              </p>
            )}
            <SyncStatusBar />
          </div>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => {
            triggerSync.mutate(undefined, {
              onSuccess: (data) => {
                if (data.new_rows_imported > 0) {
                  toast.success('Sync Complete', {
                    description: `${data.new_rows_imported} new row${data.new_rows_imported === 1 ? '' : 's'} imported from Google Sheets.`,
                  });
                } else {
                  toast.info('Sync Complete', {
                    description: 'No new rows found in Google Sheets.',
                  });
                }
              },
              onError: (err) => {
                let message = 'Sync failed';
                if (axios.isAxiosError(err)) {
                  message = err.response?.data?.detail
                    ?? err.response?.data?.error?.message
                    ?? err.message;
                } else if (err instanceof Error) {
                  message = err.message;
                }
                toast.error('Sync Failed', { description: message });
              },
            });
          }}
          disabled={triggerSync.isPending}
          data-testid="trigger-sync-btn"
        >
          <RefreshCw className={`h-4 w-4 mr-2 ${triggerSync.isPending ? 'animate-spin' : ''}`} />
          {triggerSync.isPending ? 'Syncing...' : 'Sync Now'}
        </Button>
      </div>

      {/* Filters */}
      <WorkRequestFilters params={params} onChange={handleFilterChange} />

      {/* Table */}
      <div className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
        <Table data-testid="work-requests-table">
          <TableHeader>
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow
                key={headerGroup.id}
                className="bg-slate-50/50 hover:bg-slate-50/50"
              >
                {headerGroup.headers.map((header) => (
                  <TableHead key={header.id} className="px-6 py-4">
                    {header.isPlaceholder
                      ? null
                      : flexRender(
                          header.column.columnDef.header,
                          header.getContext()
                        )}
                  </TableHead>
                ))}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody className="divide-y divide-slate-50">
            {table.getRowModel().rows?.length ? (
              table.getRowModel().rows.map((row) => (
                <TableRow
                  key={row.id}
                  data-testid="work-request-row"
                  className="hover:bg-slate-50/80 transition-colors cursor-pointer"
                  onClick={() => handleRowClick(row.original)}
                >
                  {row.getVisibleCells().map((cell) => (
                    <TableCell key={cell.id} className="px-6 py-4">
                      {flexRender(
                        cell.column.columnDef.cell,
                        cell.getContext()
                      )}
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell
                  colSpan={columns.length}
                  className="h-32 text-center"
                  data-testid="empty-state"
                >
                  <div className="flex flex-col items-center gap-2 text-slate-500">
                    <Inbox className="h-8 w-8 text-slate-300" />
                    <p className="text-sm">No work requests found.</p>
                    <p className="text-xs text-slate-400">
                      Try adjusting your filters or trigger a sync.
                    </p>
                  </div>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>

        {/* Pagination */}
        {data && data.total > 0 && (
          <div
            className="p-4 border-t border-slate-100 flex items-center justify-between"
            data-testid="pagination-controls"
          >
            <div className="text-sm text-slate-500">
              Showing{' '}
              {Math.min((params.page! - 1) * params.page_size! + 1, data.total)}{' '}
              to {Math.min(params.page! * params.page_size!, data.total)} of{' '}
              {data.total} submissions
            </div>
            <div className="flex items-center gap-2">
              <span className="text-sm text-slate-500">
                Page {data.page} of {data.total_pages}
              </span>
              <Button
                variant="outline"
                size="sm"
                onClick={() =>
                  setParams((p) => ({ ...p, page: (p.page ?? 1) - 1 }))
                }
                disabled={params.page === 1}
              >
                Previous
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() =>
                  setParams((p) => ({ ...p, page: (p.page ?? 1) + 1 }))
                }
                disabled={params.page === data.total_pages}
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
