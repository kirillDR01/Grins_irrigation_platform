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
import { ArrowUpDown, MoreHorizontal, Calendar, DollarSign } from 'lucide-react';
import { Button } from '@/components/ui/button';
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { LoadingPage, ErrorMessage } from '@/shared/components';
import { InvoiceStatusBadge } from './InvoiceStatusBadge';
import { useInvoices } from '../hooks';
import type { Invoice, InvoiceListParams, InvoiceStatus } from '../types';

const STATUS_OPTIONS: { value: InvoiceStatus | 'all'; label: string }[] = [
  { value: 'all', label: 'All Statuses' },
  { value: 'draft', label: 'Draft' },
  { value: 'sent', label: 'Sent' },
  { value: 'viewed', label: 'Viewed' },
  { value: 'paid', label: 'Paid' },
  { value: 'partial', label: 'Partial' },
  { value: 'overdue', label: 'Overdue' },
  { value: 'lien_warning', label: 'Lien Warning' },
  { value: 'lien_filed', label: 'Lien Filed' },
  { value: 'cancelled', label: 'Cancelled' },
];

interface InvoiceListProps {
  onView?: (invoice: Invoice) => void;
  onEdit?: (invoice: Invoice) => void;
  onDelete?: (invoice: Invoice) => void;
}

function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
  }).format(amount);
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

export function InvoiceList({ onView, onEdit, onDelete }: InvoiceListProps) {
  const [sorting, setSorting] = useState<SortingState>([]);
  const [params, setParams] = useState<InvoiceListParams>({
    page: 1,
    page_size: 20,
  });
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [dateFrom, setDateFrom] = useState<string>('');
  const [dateTo, setDateTo] = useState<string>('');

  const { data, isLoading, error, refetch } = useInvoices({
    ...params,
    status: statusFilter !== 'all' ? (statusFilter as InvoiceStatus) : undefined,
    date_from: dateFrom || undefined,
    date_to: dateTo || undefined,
  });

  const columns: ColumnDef<Invoice>[] = [
    {
      accessorKey: 'invoice_number',
      header: ({ column }) => (
        <Button
          variant="ghost"
          onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
        >
          Invoice #
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      ),
      cell: ({ row }) => {
        const invoice = row.original;
        return (
          <Link
            to={`/invoices/${invoice.id}`}
            className="font-medium hover:underline"
            data-testid={`invoice-number-${invoice.id}`}
          >
            {invoice.invoice_number}
          </Link>
        );
      },
    },
    {
      accessorKey: 'customer_id',
      header: 'Customer',
      cell: ({ row }) => (
        <span className="text-muted-foreground">
          {row.original.customer_id.slice(0, 8)}...
        </span>
      ),
    },
    {
      accessorKey: 'total_amount',
      header: ({ column }) => (
        <Button
          variant="ghost"
          onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
        >
          Amount
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      ),
      cell: ({ row }) => (
        <div className="flex items-center gap-2">
          <DollarSign className="h-4 w-4 text-muted-foreground" />
          <span className="font-medium">{formatCurrency(row.original.total_amount)}</span>
        </div>
      ),
    },
    {
      accessorKey: 'status',
      header: 'Status',
      cell: ({ row }) => <InvoiceStatusBadge status={row.original.status} />,
    },
    {
      accessorKey: 'due_date',
      header: ({ column }) => (
        <Button
          variant="ghost"
          onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
        >
          Due Date
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      ),
      cell: ({ row }) => (
        <div className="flex items-center gap-2">
          <Calendar className="h-4 w-4 text-muted-foreground" />
          <span>{formatDate(row.original.due_date)}</span>
        </div>
      ),
    },
    {
      id: 'actions',
      cell: ({ row }) => {
        const invoice = row.original;
        return (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                className="h-8 w-8 p-0"
                data-testid={`invoice-actions-${invoice.id}`}
              >
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem asChild>
                <Link to={`/invoices/${invoice.id}`}>View Details</Link>
              </DropdownMenuItem>
              {onView && (
                <DropdownMenuItem onClick={() => onView(invoice)}>
                  Quick View
                </DropdownMenuItem>
              )}
              {onEdit && invoice.status === 'draft' && (
                <DropdownMenuItem onClick={() => onEdit(invoice)}>Edit</DropdownMenuItem>
              )}
              {onDelete && invoice.status === 'draft' && (
                <DropdownMenuItem
                  onClick={() => onDelete(invoice)}
                  className="text-destructive"
                >
                  Cancel
                </DropdownMenuItem>
              )}
            </DropdownMenuContent>
          </DropdownMenu>
        );
      },
    },
  ];

  const table = useReactTable({
    data: data?.items ?? [],
    columns,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    onSortingChange: setSorting,
    state: {
      sorting,
    },
  });

  if (isLoading) {
    return <LoadingPage message="Loading invoices..." />;
  }

  if (error) {
    return <ErrorMessage error={error} onRetry={() => refetch()} />;
  }

  return (
    <div data-testid="invoice-list">
      {/* Filters */}
      <div className="flex flex-wrap gap-4 mb-4" data-testid="invoice-filters">
        <div className="w-48">
          <Select
            value={statusFilter}
            onValueChange={(value) => {
              setStatusFilter(value);
              setParams((p) => ({ ...p, page: 1 }));
            }}
          >
            <SelectTrigger data-testid="invoice-filter-status">
              <SelectValue placeholder="Filter by status" />
            </SelectTrigger>
            <SelectContent>
              {STATUS_OPTIONS.map((option) => (
                <SelectItem key={option.value} value={option.value}>
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="flex items-center gap-2">
          <Input
            type="date"
            value={dateFrom}
            onChange={(e) => {
              setDateFrom(e.target.value);
              setParams((p) => ({ ...p, page: 1 }));
            }}
            className="w-40"
            data-testid="invoice-filter-date-from"
            placeholder="From date"
          />
          <span className="text-muted-foreground">to</span>
          <Input
            type="date"
            value={dateTo}
            onChange={(e) => {
              setDateTo(e.target.value);
              setParams((p) => ({ ...p, page: 1 }));
            }}
            className="w-40"
            data-testid="invoice-filter-date-to"
            placeholder="To date"
          />
        </div>
      </div>

      {/* Table */}
      <div className="rounded-md border overflow-x-auto">
        <Table data-testid="invoice-table">
          <TableHeader>
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <TableHead key={header.id}>
                    {header.isPlaceholder
                      ? null
                      : flexRender(header.column.columnDef.header, header.getContext())}
                  </TableHead>
                ))}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {table.getRowModel().rows?.length ? (
              table.getRowModel().rows.map((row) => (
                <TableRow key={row.id} data-testid="invoice-row">
                  {row.getVisibleCells().map((cell) => (
                    <TableCell key={cell.id}>
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={columns.length} className="h-24 text-center">
                  No invoices found.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>

      {/* Pagination */}
      {data && data.total_pages > 1 && (
        <div className="flex items-center justify-between py-4">
          <div className="text-sm text-muted-foreground">
            Showing {(params.page! - 1) * params.page_size! + 1} to{' '}
            {Math.min(params.page! * params.page_size!, data.total)} of {data.total}{' '}
            invoices
          </div>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setParams((p) => ({ ...p, page: p.page! - 1 }))}
              disabled={params.page === 1}
              data-testid="pagination-prev"
            >
              Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setParams((p) => ({ ...p, page: p.page! + 1 }))}
              disabled={params.page === data.total_pages}
              data-testid="pagination-next"
            >
              Next
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
