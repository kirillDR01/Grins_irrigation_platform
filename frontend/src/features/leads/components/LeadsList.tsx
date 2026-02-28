import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  flexRender,
  getCoreRowModel,
  useReactTable,
  type ColumnDef,
} from '@tanstack/react-table';
import { Phone, Inbox } from 'lucide-react';
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
import { useLeads } from '../hooks/useLeads';
import { LeadStatusBadge } from './LeadStatusBadge';
import { LeadSituationBadge } from './LeadSituationBadge';
import { LeadFilters } from './LeadFilters';
import type { Lead, LeadListParams } from '../types';

export function LeadsList() {
  const navigate = useNavigate();
  const [params, setParams] = useState<LeadListParams>({
    page: 1,
    page_size: 20,
    sort_by: 'created_at',
    sort_order: 'desc',
  });

  const { data, isLoading, error, refetch } = useLeads(params);

  const handleFilterChange = useCallback(
    (changes: Partial<LeadListParams>) => {
      setParams((prev) => ({ ...prev, ...changes }));
    },
    []
  );

  const handleRowClick = useCallback(
    (lead: Lead) => {
      navigate(`/leads/${lead.id}`);
    },
    [navigate]
  );

  const columns: ColumnDef<Lead>[] = [
    {
      accessorKey: 'name',
      header: () => (
        <span className="text-slate-500 text-xs uppercase tracking-wider font-medium">
          Name
        </span>
      ),
      cell: ({ row }) => (
        <span className="text-sm font-medium text-slate-700">
          {row.original.name}
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
      cell: ({ row }) => (
        <div className="flex items-center gap-2">
          <Phone className="h-3.5 w-3.5 text-slate-400" />
          <span className="text-sm text-slate-600">{row.original.phone}</span>
        </div>
      ),
    },
    {
      accessorKey: 'situation',
      header: () => (
        <span className="text-slate-500 text-xs uppercase tracking-wider font-medium">
          Situation
        </span>
      ),
      cell: ({ row }) => (
        <LeadSituationBadge situation={row.original.situation} />
      ),
    },
    {
      accessorKey: 'status',
      header: () => (
        <span className="text-slate-500 text-xs uppercase tracking-wider font-medium">
          Status
        </span>
      ),
      cell: ({ row }) => <LeadStatusBadge status={row.original.status} />,
    },
    {
      accessorKey: 'zip_code',
      header: () => (
        <span className="text-slate-500 text-xs uppercase tracking-wider font-medium">
          Zip Code
        </span>
      ),
      cell: ({ row }) => (
        <span className="text-sm text-slate-600">{row.original.zip_code}</span>
      ),
    },
    {
      accessorKey: 'created_at',
      header: () => (
        <span className="text-slate-500 text-xs uppercase tracking-wider font-medium">
          Submitted
        </span>
      ),
      cell: ({ row }) => {
        const date = new Date(row.original.created_at);
        return (
          <span className="text-sm text-slate-500" title={date.toLocaleString()}>
            {formatDistanceToNow(date, { addSuffix: true })}
          </span>
        );
      },
    },
    {
      accessorKey: 'assigned_to',
      header: () => (
        <span className="text-slate-500 text-xs uppercase tracking-wider font-medium">
          Assigned To
        </span>
      ),
      cell: ({ row }) => (
        <span className="text-sm text-slate-600">
          {row.original.assigned_to ? (
            row.original.assigned_to
          ) : (
            <span className="text-slate-400 italic">Unassigned</span>
          )}
        </span>
      ),
    },
  ];

  const table = useReactTable({
    data: data?.items ?? [],
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  if (isLoading) {
    return <LoadingPage message="Loading leads..." />;
  }

  if (error) {
    return <ErrorMessage error={error} onRetry={() => refetch()} />;
  }

  return (
    <div data-testid="leads-page" className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Leads</h1>
          {data && (
            <p className="text-sm text-slate-500 mt-1">
              {data.total} {data.total === 1 ? 'lead' : 'leads'} total
            </p>
          )}
        </div>
      </div>

      {/* Filters */}
      <LeadFilters params={params} onChange={handleFilterChange} />

      {/* Table */}
      <div className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
        <Table data-testid="leads-table">
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
                  data-testid="lead-row"
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
                >
                  <div className="flex flex-col items-center gap-2 text-slate-500">
                    <Inbox className="h-8 w-8 text-slate-300" />
                    <p className="text-sm">No leads found.</p>
                    <p className="text-xs text-slate-400">
                      Try adjusting your filters or check back later.
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
            data-testid="leads-pagination"
          >
            <div className="text-sm text-slate-500">
              Showing{' '}
              {Math.min((params.page! - 1) * params.page_size! + 1, data.total)}{' '}
              to {Math.min(params.page! * params.page_size!, data.total)} of{' '}
              {data.total} leads
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
                data-testid="leads-prev-page"
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
                data-testid="leads-next-page"
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
