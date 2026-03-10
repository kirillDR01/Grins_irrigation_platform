import { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  flexRender,
  getCoreRowModel,
  useReactTable,
  getSortedRowModel,
  type ColumnDef,
  type SortingState,
} from '@tanstack/react-table';
import { ArrowUpDown } from 'lucide-react';
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
import { useAgreements } from '../hooks';
import type { Agreement, AgreementListParams, AgreementStatus } from '../types';
import { AGREEMENT_STATUS_CONFIG } from '../types';
import { cn } from '@/lib/utils';

// ---------------------------------------------------------------------------
// Status filter tabs
// ---------------------------------------------------------------------------

interface StatusTab {
  label: string;
  value: AgreementStatus | 'all' | 'expiring_soon';
}

const STATUS_TABS: StatusTab[] = [
  { label: 'All', value: 'all' },
  { label: 'Active', value: 'active' },
  { label: 'Pending', value: 'pending' },
  { label: 'Pending Renewal', value: 'pending_renewal' },
  { label: 'Past Due', value: 'past_due' },
  { label: 'Expiring Soon', value: 'expiring_soon' },
  { label: 'Cancelled', value: 'cancelled' },
  { label: 'Expired', value: 'expired' },
];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(amount);
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return '—';
  return new Date(dateStr).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function StatusBadge({ status }: { status: AgreementStatus }) {
  const cfg = AGREEMENT_STATUS_CONFIG[status];
  return (
    <span
      className={cn('inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium', cfg.bgColor, cfg.color)}
      data-testid={`status-${status}`}
    >
      {cfg.label}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function AgreementsList() {
  const [sorting, setSorting] = useState<SortingState>([]);
  const [activeTab, setActiveTab] = useState<string>('all');
  const [params, setParams] = useState<AgreementListParams>({ page: 1, page_size: 20 });

  // Build query params from active tab
  const queryParams: AgreementListParams = {
    ...params,
    ...(activeTab !== 'all' && activeTab !== 'expiring_soon' ? { status: activeTab as AgreementStatus } : {}),
    ...(activeTab === 'expiring_soon' ? { expiring_soon: true } : {}),
  };

  const { data, isLoading, error, refetch } = useAgreements(queryParams);

  const columns: ColumnDef<Agreement>[] = [
    {
      accessorKey: 'agreement_number',
      header: ({ column }) => (
        <Button
          variant="ghost"
          onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
          className="text-slate-500 text-xs uppercase tracking-wider font-medium hover:bg-transparent hover:text-slate-700"
        >
          Agreement #
          <ArrowUpDown className="ml-2 h-3 w-3" />
        </Button>
      ),
      cell: ({ row }) => (
        <Link
          to={`/agreements/${row.original.id}`}
          className="font-medium text-slate-700 hover:text-teal-600 transition-colors"
          data-testid={`agreement-number-${row.original.id}`}
        >
          {row.original.agreement_number}
        </Link>
      ),
    },
    {
      accessorKey: 'customer_name',
      header: () => (
        <span className="text-slate-500 text-xs uppercase tracking-wider font-medium">Customer</span>
      ),
      cell: ({ row }) => (
        <Link
          to={`/customers/${row.original.customer_id}`}
          className="text-sm text-slate-600 hover:text-teal-600 transition-colors"
        >
          {row.original.customer_name ?? row.original.customer_id.slice(0, 8)}
        </Link>
      ),
    },
    {
      accessorKey: 'tier_name',
      header: () => (
        <span className="text-slate-500 text-xs uppercase tracking-wider font-medium">Tier</span>
      ),
      cell: ({ row }) => <span className="text-sm text-slate-600">{row.original.tier_name ?? '—'}</span>,
    },
    {
      accessorKey: 'package_type',
      header: () => (
        <span className="text-slate-500 text-xs uppercase tracking-wider font-medium">Package</span>
      ),
      cell: ({ row }) => (
        <span className="text-sm text-slate-600 capitalize">{row.original.package_type ?? '—'}</span>
      ),
    },
    {
      accessorKey: 'status',
      header: () => (
        <span className="text-slate-500 text-xs uppercase tracking-wider font-medium">Status</span>
      ),
      cell: ({ row }) => <StatusBadge status={row.original.status} />,
    },
    {
      accessorKey: 'annual_price',
      header: ({ column }) => (
        <Button
          variant="ghost"
          onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
          className="text-slate-500 text-xs uppercase tracking-wider font-medium hover:bg-transparent hover:text-slate-700"
        >
          Annual Price
          <ArrowUpDown className="ml-2 h-3 w-3" />
        </Button>
      ),
      cell: ({ row }) => (
        <span className="font-semibold text-slate-800">{formatCurrency(row.original.annual_price)}</span>
      ),
    },
    {
      accessorKey: 'start_date',
      header: () => (
        <span className="text-slate-500 text-xs uppercase tracking-wider font-medium">Start Date</span>
      ),
      cell: ({ row }) => <span className="text-sm text-slate-500">{formatDate(row.original.start_date)}</span>,
    },
    {
      accessorKey: 'renewal_date',
      header: () => (
        <span className="text-slate-500 text-xs uppercase tracking-wider font-medium">Renewal Date</span>
      ),
      cell: ({ row }) => <span className="text-sm text-slate-500">{formatDate(row.original.renewal_date)}</span>,
    },
  ];

  const table = useReactTable({
    data: data?.items ?? [],
    columns,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    onSortingChange: setSorting,
    state: { sorting },
  });

  if (isLoading) return <LoadingPage message="Loading agreements..." />;
  if (error) return <ErrorMessage error={error} onRetry={() => refetch()} />;

  return (
    <div data-testid="agreements-list">
      <div className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
        {/* Status filter tabs */}
        <div className="border-b border-slate-100 px-4 flex gap-1 overflow-x-auto" data-testid="agreement-status-tabs">
          {STATUS_TABS.map((tab) => (
            <button
              key={tab.value}
              onClick={() => {
                setActiveTab(tab.value);
                setParams((p) => ({ ...p, page: 1 }));
              }}
              className={cn(
                'px-4 py-3 text-sm font-medium whitespace-nowrap border-b-2 transition-colors',
                activeTab === tab.value
                  ? 'border-teal-500 text-teal-600'
                  : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300',
              )}
              data-testid={`tab-${tab.value}`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Table */}
        <div className="overflow-x-auto">
          <Table data-testid="agreements-table">
            <TableHeader>
              {table.getHeaderGroups().map((headerGroup) => (
                <TableRow key={headerGroup.id} className="bg-slate-50/50 hover:bg-slate-50/50">
                  {headerGroup.headers.map((header) => (
                    <TableHead key={header.id} className="px-6 py-4">
                      {header.isPlaceholder ? null : flexRender(header.column.columnDef.header, header.getContext())}
                    </TableHead>
                  ))}
                </TableRow>
              ))}
            </TableHeader>
            <TableBody className="divide-y divide-slate-50">
              {table.getRowModel().rows?.length ? (
                table.getRowModel().rows.map((row) => (
                  <TableRow key={row.id} data-testid="agreement-row" className="hover:bg-slate-50/80 transition-colors">
                    {row.getVisibleCells().map((cell) => (
                      <TableCell key={cell.id} className="px-6 py-4">
                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                      </TableCell>
                    ))}
                  </TableRow>
                ))
              ) : (
                <TableRow>
                  <TableCell colSpan={columns.length} className="h-24 text-center text-slate-500">
                    No agreements found.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </div>

        {/* Pagination */}
        {data && data.total_pages > 1 && (
          <div className="p-4 border-t border-slate-100 flex items-center justify-between" data-testid="pagination">
            <div className="text-sm text-slate-500">
              Showing {(params.page! - 1) * params.page_size! + 1} to{' '}
              {Math.min(params.page! * params.page_size!, data.total)} of {data.total} agreements
            </div>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setParams((p) => ({ ...p, page: p.page! - 1 }))}
                disabled={params.page === 1}
                className="bg-white hover:bg-slate-50 border-slate-200 text-slate-700 rounded-lg disabled:opacity-50"
                data-testid="pagination-prev"
              >
                Previous
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setParams((p) => ({ ...p, page: p.page! + 1 }))}
                disabled={params.page === data.total_pages}
                className="bg-white hover:bg-slate-50 border-slate-200 text-slate-700 rounded-lg disabled:opacity-50"
                data-testid="pagination-next"
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
