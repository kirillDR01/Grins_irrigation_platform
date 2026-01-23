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
import { ArrowUpDown, MoreHorizontal, Phone, Mail } from 'lucide-react';
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
import { StatusBadge, LoadingPage, ErrorMessage } from '@/shared/components';
import { useCustomers } from '../hooks';
import type { Customer, CustomerListParams } from '../types';
import { getCustomerFlags, getCustomerFullName } from '../types';

interface CustomerListProps {
  onEdit?: (customer: Customer) => void;
  onDelete?: (customer: Customer) => void;
}

export function CustomerList({ onEdit, onDelete }: CustomerListProps) {
  const [sorting, setSorting] = useState<SortingState>([]);
  const [params, setParams] = useState<CustomerListParams>({
    page: 1,
    page_size: 20,
  });

  const { data, isLoading, error, refetch } = useCustomers(params);

  const columns: ColumnDef<Customer>[] = [
    {
      accessorKey: 'name',
      header: ({ column }) => (
        <Button
          variant="ghost"
          onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
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
            className="font-medium hover:underline"
            data-testid={`customer-name-${customer.id}`}
          >
            {getCustomerFullName(customer)}
          </Link>
        );
      },
    },
    {
      accessorKey: 'phone',
      header: 'Phone',
      cell: ({ row }) => (
        <div className="flex items-center gap-2">
          <Phone className="h-4 w-4 text-muted-foreground" />
          <a href={`tel:${row.original.phone}`} className="hover:underline">
            {row.original.phone}
          </a>
        </div>
      ),
    },
    {
      accessorKey: 'email',
      header: 'Email',
      cell: ({ row }) =>
        row.original.email ? (
          <div className="flex items-center gap-2">
            <Mail className="h-4 w-4 text-muted-foreground" />
            <a href={`mailto:${row.original.email}`} className="hover:underline">
              {row.original.email}
            </a>
          </div>
        ) : (
          <span className="text-muted-foreground">-</span>
        ),
    },
    {
      accessorKey: 'flags',
      header: 'Flags',
      cell: ({ row }) => {
        const flags = getCustomerFlags(row.original);
        return (
          <div className="flex gap-1 flex-wrap">
            {flags.map((flag) => (
              <StatusBadge key={flag} status={flag} type="customer" />
            ))}
            {flags.length === 0 && <span className="text-muted-foreground">-</span>}
          </div>
        );
      },
    },
    {
      accessorKey: 'lead_source',
      header: 'Source',
      cell: ({ row }) =>
        row.original.lead_source || <span className="text-muted-foreground">-</span>,
    },
    {
      id: 'actions',
      cell: ({ row }) => {
        const customer = row.original;
        return (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                className="h-8 w-8 p-0"
                data-testid={`customer-actions-${customer.id}`}
              >
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
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
    state: {
      sorting,
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
      <div className="rounded-md border overflow-x-auto">
        <Table data-testid="customer-table">
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
                <TableRow key={row.id} data-testid="customer-row">
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
                  No customers found.
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
            customers
          </div>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setParams((p) => ({ ...p, page: p.page! - 1 }))}
              disabled={params.page === 1}
            >
              Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setParams((p) => ({ ...p, page: p.page! + 1 }))}
              disabled={params.page === data.total_pages}
            >
              Next
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
