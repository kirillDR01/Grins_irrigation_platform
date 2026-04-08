import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import {
  flexRender,
  getCoreRowModel,
  useReactTable,
  getSortedRowModel,
  type ColumnDef,
  type SortingState,
  type RowSelectionState,
} from '@tanstack/react-table';
import { ArrowUpDown, MoreHorizontal, Phone, Filter, Download, MessageSquare, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { CustomerSearch } from './CustomerSearch';
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
import { StatusBadge, LoadingPage, ErrorMessage } from '@/shared/components';
import { NewTextCampaignModal } from '@/features/communications';
import { useCustomers } from '../hooks';
import type { Customer, CustomerListParams } from '../types';
import { getCustomerFlags, getCustomerFullName } from '../types';

interface CustomerListProps {
  onEdit?: (customer: Customer) => void;
  onDelete?: (customer: Customer) => void;
}

export function CustomerList({ onEdit, onDelete }: CustomerListProps) {
  const [sorting, setSorting] = useState<SortingState>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [rowSelection, setRowSelection] = useState<RowSelectionState>({});
  const [campaignModalOpen, setCampaignModalOpen] = useState(false);
  const [params, setParams] = useState<CustomerListParams>({
    page: 1,
    page_size: 20,
  });

  // Reset pagination to page 1 when debounced search query changes
  useEffect(() => {
    setParams((prev) => ({ ...prev, page: 1 }));
  }, [searchQuery]);

  const handleSearch = useCallback((query: string) => {
    setSearchQuery(query);
  }, []);

  const { data, isLoading, error, refetch } = useCustomers({
    ...params,
    search: searchQuery || undefined,
  });

  const selectedCustomerIds = Object.keys(rowSelection)
    .map((idx) => (data?.items ?? [])[Number(idx)]?.id)
    .filter(Boolean) as string[];

  const selectedCount = selectedCustomerIds.length;

  const columns: ColumnDef<Customer>[] = [
    {
      id: 'select',
      header: ({ table }) => (
        <Checkbox
          checked={
            table.getIsAllPageRowsSelected() ||
            (table.getIsSomePageRowsSelected() && 'indeterminate')
          }
          onCheckedChange={(value) => table.toggleAllPageRowsSelected(!!value)}
          aria-label="Select all"
          data-testid="select-all-customers"
        />
      ),
      cell: ({ row }) => (
        <Checkbox
          checked={row.getIsSelected()}
          onCheckedChange={(value) => row.toggleSelected(!!value)}
          aria-label={`Select ${getCustomerFullName(row.original)}`}
          data-testid={`select-customer-${row.original.id}`}
        />
      ),
      enableSorting: false,
    },
    {
      accessorKey: 'name',
      header: ({ column }) => (
        <Button
          variant="ghost"
          onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
          className="text-slate-500 text-xs uppercase tracking-wider font-medium hover:bg-transparent hover:text-slate-700"
        >
          Name
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      ),
      cell: ({ row }) => {
        const customer = row.original;
        return (
          <Link
            to={`/customers/${customer.id}`}
            className="font-semibold text-slate-700 hover:text-teal-600 transition-colors"
            data-testid={`customer-name-${customer.id}`}
          >
            {getCustomerFullName(customer)}
          </Link>
        );
      },
    },
    {
      accessorKey: 'contact',
      header: () => (
        <span className="text-slate-500 text-xs uppercase tracking-wider font-medium">
          Contact
        </span>
      ),
      cell: ({ row }) => (
        <div className="flex flex-col gap-0.5">
          <div className="flex items-center gap-2">
            <Phone className="h-4 w-4 text-slate-400" />
            <a
              href={`tel:${row.original.phone}`}
              className="text-sm text-slate-600 hover:text-teal-600 transition-colors"
            >
              {row.original.phone}
            </a>
          </div>
          {row.original.email && (
            <a
              href={`mailto:${row.original.email}`}
              className="text-xs text-slate-400 hover:text-teal-600 transition-colors"
            >
              {row.original.email}
            </a>
          )}
        </div>
      ),
    },
    {
      accessorKey: 'lead_source',
      header: () => (
        <span className="text-slate-500 text-xs uppercase tracking-wider font-medium">
          Source
        </span>
      ),
      cell: ({ row }) => (
        <span className="text-sm text-slate-600">
          {row.original.lead_source || <span className="text-slate-400">-</span>}
        </span>
      ),
    },
    {
      accessorKey: 'flags',
      header: () => (
        <span className="text-slate-500 text-xs uppercase tracking-wider font-medium">
          Flags
        </span>
      ),
      cell: ({ row }) => {
        const flags = getCustomerFlags(row.original);
        return (
          <div className="flex gap-1 flex-wrap">
            {flags.map((flag) => (
              <StatusBadge key={flag} status={flag} type="customer" />
            ))}
            {flags.length === 0 && <span className="text-slate-400">-</span>}
          </div>
        );
      },
    },
    {
      id: 'actions',
      header: () => (
        <span className="text-slate-500 text-xs uppercase tracking-wider font-medium">
          Actions
        </span>
      ),
      cell: ({ row }) => {
        const customer = row.original;
        return (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                className="h-8 w-8 p-0 hover:text-teal-600 hover:bg-teal-50 rounded-lg transition-colors"
                data-testid={`customer-actions-${customer.id}`}
              >
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" data-testid="dropdown-menu">
              <DropdownMenuItem asChild>
                <Link to={`/customers/${customer.id}`}>View Details</Link>
              </DropdownMenuItem>
              {onEdit && (
                <DropdownMenuItem onClick={() => onEdit(customer)}>Edit</DropdownMenuItem>
              )}
              {onDelete && (
                <DropdownMenuItem
                  onClick={() => onDelete(customer)}
                  className="text-destructive"
                >
                  Delete
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
    onRowSelectionChange: setRowSelection,
    state: {
      sorting,
      rowSelection,
    },
  });

  if (isLoading) {
    return <LoadingPage message="Loading customers..." />;
  }

  if (error) {
    return <ErrorMessage error={error} onRetry={() => refetch()} />;
  }

  return (
    <div data-testid="customer-list">
      {/* Table Container with Design System Styling */}
      <div className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
        {/* Table Toolbar */}
        <div className="p-4 border-b border-slate-100 flex gap-4 items-center">
          {/* Debounced Search Input */}
          <div className="flex-1 max-w-sm">
            <CustomerSearch onSearch={handleSearch} />
          </div>
          {/* Filter Button */}
          <Button variant="outline" size="sm" className="gap-2">
            <Filter className="h-4 w-4" />
            Filter
          </Button>
          {/* Export Button */}
          <Button variant="outline" size="sm" className="gap-2">
            <Download className="h-4 w-4" />
            Export
          </Button>
        </div>

        {/* Table */}
        <Table data-testid="customer-table">
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
                  data-testid="customer-row"
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
                  No customers found.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>

        {/* Pagination */}
        {data && (
          <div
            className="p-4 border-t border-slate-100 flex items-center justify-between"
            data-testid="pagination"
          >
            <div className="text-sm text-slate-500">
              Showing {(params.page! - 1) * params.page_size! + 1} to{' '}
              {Math.min(params.page! * params.page_size!, data.total)} of {data.total}{' '}
              customers
            </div>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setParams((p) => ({ ...p, page: p.page! - 1 }))}
                disabled={params.page === 1}
                data-testid="prev-page-btn"
              >
                Previous
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setParams((p) => ({ ...p, page: p.page! + 1 }))}
                disabled={params.page === data.total_pages}
                data-testid="next-page-btn"
              >
                Next
              </Button>
            </div>
          </div>
        )}
      </div>

      {/* Sticky Bulk Action Bar */}
      {selectedCount > 0 && (
        <div
          className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 flex items-center gap-3 bg-slate-900 text-white px-5 py-3 rounded-xl shadow-lg"
          data-testid="bulk-action-bar"
        >
          <span className="text-sm font-medium" data-testid="selected-count">
            {selectedCount} selected
          </span>
          <Button
            size="sm"
            variant="secondary"
            className="gap-2"
            onClick={() => setCampaignModalOpen(true)}
            data-testid="text-selected-customers-btn"
          >
            <MessageSquare className="h-4 w-4" />
            Text Selected
          </Button>
          <Button
            size="sm"
            variant="ghost"
            className="text-white hover:text-white hover:bg-slate-700"
            onClick={() => setRowSelection({})}
            data-testid="clear-selection-btn"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
      )}

      {/* Campaign Modal */}
      <NewTextCampaignModal
        open={campaignModalOpen}
        onOpenChange={(open) => {
          setCampaignModalOpen(open);
          if (!open) setRowSelection({});
        }}
        preSelectedCustomerIds={selectedCustomerIds}
      />
    </div>
  );
}
