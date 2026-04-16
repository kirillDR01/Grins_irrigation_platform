import { useState, useMemo, useCallback } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import {
  flexRender,
  getCoreRowModel,
  useReactTable,
  getSortedRowModel,
  type ColumnDef,
  type SortingState,
} from '@tanstack/react-table';
import { ArrowUpDown, MoreHorizontal } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { LoadingPage, ErrorMessage, FilterPanel } from '@/shared/components';
import type { FilterAxis } from '@/shared/components';
import { InvoiceStatusBadge } from './InvoiceStatusBadge';
import { BulkNotify } from './BulkNotify';
import { MassNotifyPanel } from './MassNotifyPanel';
import { useInvoices } from '../hooks';
import type { Invoice, InvoiceListParams, InvoiceStatus, PaymentMethod } from '../types';

/* ------------------------------------------------------------------ */
/*  Filter axes definition (9 axes per Req 28.1)                       */
/* ------------------------------------------------------------------ */

const INVOICE_FILTER_AXES: FilterAxis[] = [
  {
    key: 'date',
    label: 'Date Range',
    type: 'date-range',
    fromKey: 'date_from',
    toKey: 'date_to',
  },
  {
    key: 'status',
    label: 'Status',
    type: 'select',
    options: [
      { value: 'draft', label: 'Draft' },
      { value: 'sent', label: 'Sent' },
      { value: 'viewed', label: 'Viewed' },
      { value: 'paid', label: 'Paid' },
      { value: 'partial', label: 'Partial' },
      { value: 'overdue', label: 'Overdue' },
      { value: 'lien_warning', label: 'Lien Warning' },
      { value: 'lien_filed', label: 'Lien Filed' },
      { value: 'cancelled', label: 'Cancelled' },
    ],
  },
  {
    key: 'customer_search',
    label: 'Customer',
    type: 'text',
    placeholder: 'Customer name...',
  },
  {
    key: 'job_id',
    label: 'Job',
    type: 'text',
    placeholder: 'Job ID...',
  },
  {
    key: 'amount',
    label: 'Amount',
    type: 'number-range',
    minKey: 'amount_min',
    maxKey: 'amount_max',
  },
  {
    key: 'payment_types',
    label: 'Payment Type',
    type: 'multi-select',
    // H-4 (bughunt 2026-04-16): new-data spec vocabulary. Legacy rows
    // stored as `stripe` remain in the DB but are not offered as a
    // filter option here — admins can still see the value in each
    // invoice's `payment_type` column and on the detail page.
    options: [
      { value: 'credit_card', label: 'Credit Card' },
      { value: 'cash', label: 'Cash' },
      { value: 'check', label: 'Check' },
      { value: 'ach', label: 'ACH' },
      { value: 'venmo', label: 'Venmo' },
      { value: 'zelle', label: 'Zelle' },
      { value: 'other', label: 'Other' },
    ],
  },
  {
    key: 'days_until_due',
    label: 'Days Until Due',
    type: 'number-range',
    minKey: 'days_until_due_min',
    maxKey: 'days_until_due_max',
  },
  {
    key: 'days_past_due',
    label: 'Days Past Due',
    type: 'number-range',
    minKey: 'days_past_due_min',
    maxKey: 'days_past_due_max',
  },
  {
    key: 'invoice_number',
    label: 'Invoice Number',
    type: 'text',
    placeholder: 'Exact invoice number...',
  },
];

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
  }).format(amount);
}

function daysDiff(dateStr: string): number {
  const now = new Date();
  now.setHours(0, 0, 0, 0);
  const target = new Date(dateStr);
  target.setHours(0, 0, 0, 0);
  return Math.round((target.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
}

function getDaysUntilDue(invoice: Invoice): number | null {
  if (invoice.status === 'paid' || invoice.status === 'cancelled') return null;
  const diff = daysDiff(invoice.due_date);
  return diff >= 0 ? diff : null;
}

function getDaysPastDue(invoice: Invoice): number | null {
  if (invoice.status === 'paid' || invoice.status === 'cancelled') return null;
  const diff = daysDiff(invoice.due_date);
  return diff < 0 ? Math.abs(diff) : null;
}

const PAYMENT_LABELS: Record<PaymentMethod, string> = {
  cash: 'Cash',
  check: 'Check',
  venmo: 'Venmo',
  zelle: 'Zelle',
  // H-4 (bughunt 2026-04-16): `stripe` still renders for legacy rows.
  stripe: 'Stripe',
  credit_card: 'Credit Card',
  ach: 'ACH',
  other: 'Other',
};

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

interface InvoiceListProps {
  onView?: (invoice: Invoice) => void;
  onEdit?: (invoice: Invoice) => void;
  onDelete?: (invoice: Invoice) => void;
}

export function InvoiceList({ onView, onEdit, onDelete }: InvoiceListProps) {
  const [sorting, setSorting] = useState<SortingState>([]);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [searchParams] = useSearchParams();

  // Build params from URL search params (FilterPanel persists to URL)
  const params: InvoiceListParams = useMemo(() => {
    const p: InvoiceListParams = {
      page: Number(searchParams.get('page')) || 1,
      page_size: 20,
    };
    const status = searchParams.get('status');
    if (status) p.status = status as InvoiceStatus;
    const dateFrom = searchParams.get('date_from');
    if (dateFrom) p.date_from = dateFrom;
    const dateTo = searchParams.get('date_to');
    if (dateTo) p.date_to = dateTo;
    const amountMin = searchParams.get('amount_min');
    if (amountMin) p.amount_min = Number(amountMin);
    const amountMax = searchParams.get('amount_max');
    if (amountMax) p.amount_max = Number(amountMax);
    const paymentTypes = searchParams.get('payment_types');
    if (paymentTypes) p.payment_types = paymentTypes;
    const daysUntilDueMin = searchParams.get('days_until_due_min');
    if (daysUntilDueMin) p.days_until_due_min = Number(daysUntilDueMin);
    const daysUntilDueMax = searchParams.get('days_until_due_max');
    if (daysUntilDueMax) p.days_until_due_max = Number(daysUntilDueMax);
    const daysPastDueMin = searchParams.get('days_past_due_min');
    if (daysPastDueMin) p.days_past_due_min = Number(daysPastDueMin);
    const daysPastDueMax = searchParams.get('days_past_due_max');
    if (daysPastDueMax) p.days_past_due_max = Number(daysPastDueMax);
    const invoiceNumber = searchParams.get('invoice_number');
    if (invoiceNumber) p.invoice_number = invoiceNumber;
    const customerId = searchParams.get('customer_search');
    if (customerId) p.customer_search = customerId;
    const jobId = searchParams.get('job_id');
    if (jobId) p.job_id = jobId;
    return p;
  }, [searchParams]);

  const { data, isLoading, error, refetch } = useInvoices(params);

  const invoiceItems = useMemo(() => data?.items ?? [], [data?.items]);
  const allSelected = invoiceItems.length > 0 && invoiceItems.every((inv) => selectedIds.has(inv.id));
  const someSelected = invoiceItems.some((inv) => selectedIds.has(inv.id));

  const toggleAll = useCallback(() => {
    if (allSelected) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(invoiceItems.map((inv) => inv.id)));
    }
  }, [allSelected, invoiceItems]);

  const toggleOne = useCallback((id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const columns: ColumnDef<Invoice>[] = useMemo(() => [
    {
      id: 'select',
      header: () => (
        <Checkbox
          checked={allSelected ? true : someSelected ? 'indeterminate' : false}
          onCheckedChange={toggleAll}
          aria-label="Select all invoices"
          data-testid="select-all-checkbox"
        />
      ),
      cell: ({ row }) => (
        <Checkbox
          checked={selectedIds.has(row.original.id)}
          onCheckedChange={() => toggleOne(row.original.id)}
          aria-label={`Select invoice ${row.original.invoice_number}`}
          data-testid={`select-invoice-${row.original.id}`}
        />
      ),
      enableSorting: false,
    },
    {
      accessorKey: 'invoice_number',
      header: ({ column }) => (
        <Button
          variant="ghost"
          onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
          className="text-slate-500 text-xs uppercase tracking-wider font-medium hover:bg-transparent hover:text-slate-700"
        >
          Invoice #
          <ArrowUpDown className="ml-2 h-3 w-3" />
        </Button>
      ),
      cell: ({ row }) => (
        <Link
          to={`/invoices/${row.original.id}`}
          className="font-medium text-slate-700 hover:text-teal-600 transition-colors"
          data-testid={`invoice-number-${row.original.id}`}
        >
          {row.original.invoice_number}
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
      id: 'job',
      header: () => (
        <span className="text-slate-500 text-xs uppercase tracking-wider font-medium">Job</span>
      ),
      cell: ({ row }) => (
        <Link
          to={`/jobs/${row.original.job_id}`}
          className="text-sm text-slate-600 hover:text-teal-600 transition-colors"
          data-testid={`invoice-job-link-${row.original.id}`}
        >
          {row.original.job_id.slice(0, 8)}…
        </Link>
      ),
    },
    {
      accessorKey: 'total_amount',
      header: ({ column }) => (
        <Button
          variant="ghost"
          onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
          className="text-slate-500 text-xs uppercase tracking-wider font-medium hover:bg-transparent hover:text-slate-700"
        >
          Cost
          <ArrowUpDown className="ml-2 h-3 w-3" />
        </Button>
      ),
      cell: ({ row }) => (
        <span className="font-semibold text-slate-800">
          {formatCurrency(row.original.total_amount)}
        </span>
      ),
    },
    {
      accessorKey: 'status',
      header: () => (
        <span className="text-slate-500 text-xs uppercase tracking-wider font-medium">Status</span>
      ),
      cell: ({ row }) => (
        <InvoiceStatusBadge status={row.original.status} data-testid="invoice-status-badge" />
      ),
    },
    {
      id: 'days_until_due',
      header: () => (
        <span className="text-slate-500 text-xs uppercase tracking-wider font-medium">Days Until Due</span>
      ),
      cell: ({ row }) => {
        const days = getDaysUntilDue(row.original);
        if (days === null) return <span className="text-sm text-slate-400">—</span>;
        return (
          <span className={`text-sm ${days <= 7 ? 'text-yellow-600 font-medium' : 'text-slate-600'}`}>
            {days}
          </span>
        );
      },
    },
    {
      id: 'days_past_due',
      header: () => (
        <span className="text-slate-500 text-xs uppercase tracking-wider font-medium">Days Past Due</span>
      ),
      cell: ({ row }) => {
        const days = getDaysPastDue(row.original);
        if (days === null) return <span className="text-sm text-slate-400">—</span>;
        return (
          <span className="text-sm text-red-600 font-medium">{days}</span>
        );
      },
    },
    {
      id: 'payment_type',
      header: () => (
        <span className="text-slate-500 text-xs uppercase tracking-wider font-medium">Payment Type</span>
      ),
      cell: ({ row }) => {
        const method = row.original.payment_method;
        if (!method) return <span className="text-sm text-slate-400">—</span>;
        return <span className="text-sm text-slate-600">{PAYMENT_LABELS[method] ?? method}</span>;
      },
    },
    {
      id: 'actions',
      header: () => (
        <span className="text-slate-500 text-xs uppercase tracking-wider font-medium">Actions</span>
      ),
      cell: ({ row }) => {
        const invoice = row.original;
        return (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                className="h-8 w-8 p-0 hover:text-teal-600 hover:bg-teal-50 rounded-lg transition-colors"
                data-testid={`invoice-actions-${invoice.id}`}
              >
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" data-testid="dropdown-menu">
              <DropdownMenuItem asChild>
                <Link to={`/invoices/${invoice.id}`}>View Details</Link>
              </DropdownMenuItem>
              {onView && (
                <DropdownMenuItem onClick={() => onView(invoice)}>Quick View</DropdownMenuItem>
              )}
              {onEdit && invoice.status === 'draft' && (
                <DropdownMenuItem onClick={() => onEdit(invoice)}>Edit</DropdownMenuItem>
              )}
              {onDelete && invoice.status === 'draft' && (
                <DropdownMenuItem
                  onClick={() => onDelete(invoice)}
                  className="text-red-600 focus:text-red-600"
                >
                  Cancel
                </DropdownMenuItem>
              )}
            </DropdownMenuContent>
          </DropdownMenu>
        );
      },
    },
  ], [allSelected, someSelected, selectedIds, toggleAll, toggleOne, onView, onEdit, onDelete]);

  const table = useReactTable({
    data: invoiceItems,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    onSortingChange: setSorting,
    state: { sorting },
  });

  if (isLoading) return <LoadingPage message="Loading invoices..." />;
  if (error) return <ErrorMessage error={error} onRetry={() => refetch()} />;

  return (
    <div data-testid="invoice-list">
      <div className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
        {/* Filter Panel + Actions Toolbar */}
        <div className="p-4 border-b border-slate-100 space-y-3" data-testid="invoice-filters">
          <div className="flex flex-wrap items-center gap-2">
            <FilterPanel axes={INVOICE_FILTER_AXES} persistToUrl />
            <div className="ml-auto flex gap-2">
              <MassNotifyPanel />
              <BulkNotify
                selectedInvoiceIds={Array.from(selectedIds)}
                onComplete={() => setSelectedIds(new Set())}
              />
            </div>
          </div>
        </div>

        {/* Table */}
        <div className="overflow-x-auto">
          <Table data-testid="invoice-table">
            <TableHeader>
              {table.getHeaderGroups().map((headerGroup) => (
                <TableRow key={headerGroup.id} className="bg-slate-50/50 hover:bg-slate-50/50">
                  {headerGroup.headers.map((header) => (
                    <TableHead key={header.id} className="px-6 py-4">
                      {header.isPlaceholder
                        ? null
                        : flexRender(header.column.columnDef.header, header.getContext())}
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
                    data-testid="invoice-row"
                    className="hover:bg-slate-50/80 transition-colors"
                  >
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
                    No invoices found.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </div>

        {/* Pagination */}
        {data && data.total_pages > 1 && (
          <div
            className="p-4 border-t border-slate-100 flex items-center justify-between"
            data-testid="pagination"
          >
            <div className="text-sm text-slate-500">
              Showing {(params.page! - 1) * params.page_size! + 1} to{' '}
              {Math.min(params.page! * params.page_size!, data.total)} of {data.total} invoices
            </div>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  const sp = new URLSearchParams(searchParams);
                  sp.set('page', String((params.page ?? 1) - 1));
                  window.history.pushState({}, '', `?${sp.toString()}`);
                  window.dispatchEvent(new PopStateEvent('popstate'));
                }}
                disabled={params.page === 1}
                className="bg-white hover:bg-slate-50 border-slate-200 text-slate-700 rounded-lg disabled:opacity-50"
                data-testid="pagination-prev"
              >
                Previous
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  const sp = new URLSearchParams(searchParams);
                  sp.set('page', String((params.page ?? 1) + 1));
                  window.history.pushState({}, '', `?${sp.toString()}`);
                  window.dispatchEvent(new PopStateEvent('popstate'));
                }}
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
