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
import { ArrowUpDown, MoreHorizontal, Phone, Mail, CheckCircle, XCircle } from 'lucide-react';
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
import { Badge } from '@/components/ui/badge';
import { LoadingPage, ErrorMessage } from '@/shared/components';
import { useStaff } from '../hooks';
import type { Staff, StaffListParams, StaffRole } from '../types';

interface StaffListProps {
  onEdit?: (staff: Staff) => void;
  onDelete?: (staff: Staff) => void;
}

const roleColors: Record<StaffRole, string> = {
  tech: 'bg-blue-100 text-blue-800',
  sales: 'bg-green-100 text-green-800',
  admin: 'bg-purple-100 text-purple-800',
};

const roleLabels: Record<StaffRole, string> = {
  tech: 'Technician',
  sales: 'Sales',
  admin: 'Admin',
};

export function StaffList({ onEdit, onDelete }: StaffListProps) {
  const [sorting, setSorting] = useState<SortingState>([]);
  const [params, setParams] = useState<StaffListParams>({
    page: 1,
    page_size: 20,
  });

  const { data, isLoading, error, refetch } = useStaff(params);

  const columns: ColumnDef<Staff>[] = [
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
        const staff = row.original;
        return (
          <Link
            to={`/staff/${staff.id}`}
            className="font-medium hover:underline"
            data-testid={`staff-name-${staff.id}`}
          >
            {staff.name}
          </Link>
        );
      },
    },
    {
      accessorKey: 'role',
      header: 'Role',
      cell: ({ row }) => {
        const role = row.original.role;
        return (
          <Badge className={roleColors[role]} data-testid={`staff-role-${row.original.id}`}>
            {roleLabels[role]}
          </Badge>
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
      accessorKey: 'is_available',
      header: 'Availability',
      cell: ({ row }) => {
        const isAvailable = row.original.is_available;
        return (
          <div
            className="flex items-center gap-2"
            data-testid={`staff-availability-${row.original.id}`}
          >
            {isAvailable ? (
              <>
                <CheckCircle className="h-4 w-4 text-green-600" />
                <span className="text-green-600">Available</span>
              </>
            ) : (
              <>
                <XCircle className="h-4 w-4 text-red-600" />
                <span className="text-red-600">Unavailable</span>
              </>
            )}
          </div>
        );
      },
    },
    {
      accessorKey: 'skill_level',
      header: 'Skill Level',
      cell: ({ row }) =>
        row.original.skill_level ? (
          <span className="capitalize">{row.original.skill_level}</span>
        ) : (
          <span className="text-muted-foreground">-</span>
        ),
    },
    {
      id: 'actions',
      cell: ({ row }) => {
        const staff = row.original;
        return (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                className="h-8 w-8 p-0"
                data-testid={`staff-actions-${staff.id}`}
              >
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem asChild>
                <Link to={`/staff/${staff.id}`}>View Details</Link>
              </DropdownMenuItem>
              {onEdit && (
                <DropdownMenuItem onClick={() => onEdit(staff)}>Edit</DropdownMenuItem>
              )}
              {onDelete && (
                <DropdownMenuItem
                  onClick={() => onDelete(staff)}
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
    return <LoadingPage message="Loading staff..." />;
  }

  if (error) {
    return <ErrorMessage error={error} onRetry={() => refetch()} />;
  }

  return (
    <div data-testid="staff-list">
      <div className="rounded-md border overflow-x-auto">
        <Table data-testid="staff-table">
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
                <TableRow key={row.id} data-testid="staff-row">
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
                  No staff members found.
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
            staff members
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
