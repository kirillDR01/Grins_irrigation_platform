/**
 * Appointment list component.
 * Displays appointments in a table format with filtering.
 */

import { useState } from 'react';
import { format } from 'date-fns';
import {
  useReactTable,
  getCoreRowModel,
  flexRender,
  type ColumnDef,
} from '@tanstack/react-table';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { ChevronLeft, ChevronRight, Eye } from 'lucide-react';
import { useAppointments } from '../hooks/useAppointments';
import { appointmentStatusConfig } from '../types';
import type { Appointment, AppointmentStatus, AppointmentListParams } from '../types';
import { LoadingSpinner } from '@/shared/components/LoadingSpinner';

interface AppointmentListProps {
  onAppointmentClick?: (appointmentId: string) => void;
}

const statusOptions: { value: AppointmentStatus | 'all'; label: string }[] = [
  { value: 'all', label: 'All Statuses' },
  { value: 'pending', label: 'Pending' },
  { value: 'confirmed', label: 'Confirmed' },
  { value: 'in_progress', label: 'In Progress' },
  { value: 'completed', label: 'Completed' },
  { value: 'cancelled', label: 'Cancelled' },
  { value: 'no_show', label: 'No Show' },
];

export function AppointmentList({ onAppointmentClick }: AppointmentListProps) {
  const [params, setParams] = useState<AppointmentListParams>({
    page: 1,
    page_size: 20,
    sort_by: 'scheduled_date',
    sort_order: 'desc',
  });

  const { data, isLoading, error } = useAppointments(params);

  const columns: ColumnDef<Appointment>[] = [
    {
      accessorKey: 'scheduled_date',
      header: 'Date',
      cell: ({ row }) => {
        const date = new Date(row.original.scheduled_date);
        return format(date, 'MMM d, yyyy');
      },
    },
    {
      accessorKey: 'time_window_start',
      header: 'Time',
      cell: ({ row }) => {
        const start = row.original.time_window_start.slice(0, 5);
        const end = row.original.time_window_end.slice(0, 5);
        return `${start} - ${end}`;
      },
    },
    {
      accessorKey: 'status',
      header: 'Status',
      cell: ({ row }) => {
        const status = row.original.status;
        const config = appointmentStatusConfig[status];
        return (
          <Badge
            className={`${config.bgColor} ${config.color}`}
            data-testid={`status-${status}`}
          >
            {config.label}
          </Badge>
        );
      },
    },
    {
      accessorKey: 'job_id',
      header: 'Job ID',
      cell: ({ row }) => (
        <span className="font-mono text-sm">
          {row.original.job_id.slice(0, 8)}...
        </span>
      ),
    },
    {
      accessorKey: 'staff_id',
      header: 'Staff ID',
      cell: ({ row }) => (
        <span className="font-mono text-sm">
          {row.original.staff_id.slice(0, 8)}...
        </span>
      ),
    },
    {
      accessorKey: 'route_order',
      header: 'Route #',
      cell: ({ row }) => row.original.route_order ?? '-',
    },
    {
      id: 'actions',
      header: 'Actions',
      cell: ({ row }) => (
        <Button
          variant="ghost"
          size="sm"
          onClick={() => onAppointmentClick?.(row.original.id)}
          data-testid={`view-appointment-${row.original.id}`}
        >
          <Eye className="h-4 w-4" />
        </Button>
      ),
    },
  ];

  const table = useReactTable({
    data: data?.items ?? [],
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  const handleStatusChange = (value: string) => {
    setParams((prev) => ({
      ...prev,
      status: value === 'all' ? undefined : (value as AppointmentStatus),
      page: 1,
    }));
  };

  const handleDateFromChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setParams((prev) => ({
      ...prev,
      date_from: e.target.value || undefined,
      page: 1,
    }));
  };

  const handleDateToChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setParams((prev) => ({
      ...prev,
      date_to: e.target.value || undefined,
      page: 1,
    }));
  };

  if (error) {
    return (
      <div className="p-8 text-center text-red-600">
        Error loading appointments: {error.message}
      </div>
    );
  }

  return (
    <div data-testid="appointment-list" className="space-y-4 p-4">
      {/* Filters */}
      <div className="flex flex-wrap gap-4">
        <div className="w-48">
          <Select
            value={params.status ?? 'all'}
            onValueChange={handleStatusChange}
          >
            <SelectTrigger data-testid="status-filter">
              <SelectValue placeholder="Filter by status" />
            </SelectTrigger>
            <SelectContent>
              {statusOptions.map((option) => (
                <SelectItem key={option.value} value={option.value}>
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">From:</span>
          <Input
            type="date"
            value={params.date_from ?? ''}
            onChange={handleDateFromChange}
            className="w-40"
            data-testid="date-from-filter"
          />
        </div>
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">To:</span>
          <Input
            type="date"
            value={params.date_to ?? ''}
            onChange={handleDateToChange}
            className="w-40"
            data-testid="date-to-filter"
          />
        </div>
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="flex items-center justify-center h-64">
          <LoadingSpinner />
        </div>
      ) : (
        <>
          <div className="rounded-md border overflow-x-auto">
            <Table data-testid="appointment-table">
              <TableHeader>
                {table.getHeaderGroups().map((headerGroup) => (
                  <TableRow key={headerGroup.id}>
                    {headerGroup.headers.map((header) => (
                      <TableHead key={header.id}>
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
              <TableBody>
                {table.getRowModel().rows.length === 0 ? (
                  <TableRow>
                    <TableCell
                      colSpan={columns.length}
                      className="h-24 text-center"
                    >
                      No appointments found.
                    </TableCell>
                  </TableRow>
                ) : (
                  table.getRowModel().rows.map((row) => (
                    <TableRow
                      key={row.id}
                      data-testid="appointment-row"
                      className="cursor-pointer hover:bg-muted/50"
                      onClick={() => onAppointmentClick?.(row.original.id)}
                    >
                      {row.getVisibleCells().map((cell) => (
                        <TableCell key={cell.id}>
                          {flexRender(
                            cell.column.columnDef.cell,
                            cell.getContext()
                          )}
                        </TableCell>
                      ))}
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>

          {/* Pagination */}
          {data && data.total_pages > 1 && (
            <div className="flex items-center justify-between">
              <div className="text-sm text-muted-foreground">
                Showing {(params.page! - 1) * params.page_size! + 1} to{' '}
                {Math.min(params.page! * params.page_size!, data.total)} of{' '}
                {data.total} appointments
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() =>
                    setParams((prev) => ({ ...prev, page: prev.page! - 1 }))
                  }
                  disabled={params.page === 1}
                >
                  <ChevronLeft className="h-4 w-4" />
                  Previous
                </Button>
                <span className="text-sm">
                  Page {params.page} of {data.total_pages}
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() =>
                    setParams((prev) => ({ ...prev, page: prev.page! + 1 }))
                  }
                  disabled={params.page === data.total_pages}
                >
                  Next
                  <ChevronRight className="h-4 w-4" />
                </Button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
