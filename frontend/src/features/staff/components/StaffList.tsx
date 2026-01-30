import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
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
import { Badge } from '@/components/ui/badge';
import { LoadingPage, ErrorMessage } from '@/shared/components';
import { useStaff } from '../hooks';
import type { Staff, StaffListParams, StaffRole } from '../types';

interface StaffListProps {
  onEdit?: (staff: Staff) => void;
  onDelete?: (staff: Staff) => void;
}

const roleColors: Record<StaffRole, string> = {
  tech: 'bg-blue-100 text-blue-700',
  sales: 'bg-emerald-100 text-emerald-700',
  admin: 'bg-violet-100 text-violet-700',
};

const roleLabels: Record<StaffRole, string> = {
  tech: 'Technician',
  sales: 'Sales',
  admin: 'Admin',
};

// Helper to get initials from name
function getInitials(name: string): string {
  return name
    .split(' ')
    .map((n) => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);
}

export function StaffList({ onEdit, onDelete }: StaffListProps) {
  const navigate = useNavigate();
  const [sorting, setSorting] = useState<SortingState>([]);
  const [params, setParams] = useState<StaffListParams>({
    page: 1,
    page_size: 20,
  });

  const { data, isLoading, error, refetch } = useStaff(params);

  const handleRowClick = (staffId: string) => {
    navigate(`/staff/${staffId}`);
  };

  const columns: ColumnDef<Staff>[] = [
    {
      accessorKey: 'name',
      header: ({ column }) => (
        <Button
          variant="ghost"
          onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
          className="text-slate-500 text-xs uppercase tracking-wider font-medium hover:text-slate-700"
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
            className="flex items-center gap-3 group"
            data-testid={`staff-name-${staff.id}`}
          >
            {/* Avatar */}
            <div className="w-10 h-10 rounded-full bg-slate-200 text-slate-600 font-semibold text-sm flex items-center justify-center">
              {getInitials(staff.name)}
            </div>
            <span className="font-medium text-slate-700 group-hover:text-teal-600 transition-colors">
              {staff.name}
            </span>
          </Link>
        );
      },
    },
    {
      accessorKey: 'role',
      header: () => (
        <span className="text-slate-500 text-xs uppercase tracking-wider font-medium">
          Role
        </span>
      ),
      cell: ({ row }) => {
        const role = row.original.role;
        return (
          <Badge
            className={`${roleColors[role]} px-3 py-1 rounded-full text-xs font-medium`}
            data-testid={`staff-role-${row.original.id}`}
          >
            {roleLabels[role]}
          </Badge>
        );
      },
    },
    {
      accessorKey: 'is_available',
      header: () => (
        <span className="text-slate-500 text-xs uppercase tracking-wider font-medium">
          Availability
        </span>
      ),
      cell: ({ row }) => {
        const isAvailable = row.original.is_available;
        // Determine status: Available, On Job, or Unavailable
        // For now, we'll use is_available to determine Available vs Unavailable
        // "On Job" would require additional data about current assignments
        return (
          <div
            className="flex items-center gap-2"
            data-testid={`staff-availability-${row.original.id}`}
          >
            <div
              className={`w-2 h-2 rounded-full ${
                isAvailable ? 'bg-emerald-500' : 'bg-slate-300'
              }`}
              data-testid="availability-indicator"
            />
            <span className="text-xs font-medium text-slate-600">
              {isAvailable ? 'Available' : 'Unavailable'}
            </span>
          </div>
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
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-2">
            <Phone className="h-3.5 w-3.5 text-slate-400" />
            <a
              href={`tel:${row.original.phone}`}
              className="text-sm text-slate-600 hover:text-teal-600 transition-colors"
            >
              {row.original.phone}
            </a>
          </div>
          {row.original.email && (
            <div className="flex items-center gap-2">
              <Mail className="h-3.5 w-3.5 text-slate-400" />
              <a
                href={`mailto:${row.original.email}`}
                className="text-xs text-slate-400 hover:text-teal-600 transition-colors"
              >
                {row.original.email}
              </a>
            </div>
          )}
        </div>
      ),
    },
    {
      id: 'actions',
      header: () => (
        <span className="text-slate-500 text-xs uppercase tracking-wider font-medium">
          Actions
        </span>
      ),
      cell: ({ row }) => {
        const staff = row.original;
        return (
          <div onClick={(e) => e.stopPropagation()}>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="ghost"
                  className="h-8 w-8 p-0 hover:text-teal-600 hover:bg-teal-50 rounded-lg transition-colors"
                  data-testid={`staff-actions-${staff.id}`}
                >
                  <MoreHorizontal className="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" data-testid="dropdown-menu">
                <DropdownMenuItem asChild>
                  <Link to={`/staff/${staff.id}`}>View Details</Link>
                </DropdownMenuItem>
                {onEdit && (
                  <DropdownMenuItem onClick={() => onEdit(staff)}>Edit</DropdownMenuItem>
                )}
                {onDelete && (
                  <DropdownMenuItem
                    onClick={() => onDelete(staff)}
                    className="text-red-600 hover:text-red-700 hover:bg-red-50"
                  >
                    Delete
                  </DropdownMenuItem>
                )}
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
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
      {/* Table container with design system styling */}
      <div className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
        <Table data-testid="staff-table">
          <TableHeader>
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id} className="bg-slate-50/50 border-b border-slate-100">
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
                  data-testid="staff-row"
                  className="hover:bg-slate-50/80 transition-colors cursor-pointer"
                  onClick={() => handleRowClick(row.original.id)}
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
                  No staff members found.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>

      {/* Pagination */}
      {data && data.total_pages > 1 && (
        <div className="flex items-center justify-between py-4 px-2" data-testid="pagination">
          <div className="text-sm text-slate-500">
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
              data-testid="prev-page-btn"
              className="border-slate-200 hover:bg-slate-50"
            >
              Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setParams((p) => ({ ...p, page: p.page! + 1 }))}
              disabled={params.page === data.total_pages}
              data-testid="next-page-btn"
              className="border-slate-200 hover:bg-slate-50"
            >
              Next
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
