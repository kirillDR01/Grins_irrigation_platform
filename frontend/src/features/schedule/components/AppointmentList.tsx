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
import { ChevronLeft, ChevronRight, MoreHorizontal, Clock, Calendar } from 'lucide-react';
import { useAppointments } from '../hooks/useAppointments';
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

// Status badge styling per design system
const getStatusBadgeClasses = (status: AppointmentStatus): string => {
  switch (status) {
    case 'completed':
      return 'bg-emerald-100 text-emerald-700';
    case 'confirmed':
    case 'pending':
      return 'bg-violet-100 text-violet-700';
    case 'in_progress':
      return 'bg-orange-100 text-orange-700';
    case 'cancelled':
      return 'bg-red-100 text-red-700';
    case 'no_show':
      return 'bg-slate-100 text-slate-500';
    default:
      return 'bg-slate-100 text-slate-500';
  }
};

const getStatusLabel = (status: AppointmentStatus): string => {
  switch (status) {
    case 'pending':
      return 'Pending';
    case 'confirmed':
      return 'Scheduled';
    case 'in_progress':
      return 'In Progress';
    case 'completed':
      return 'Completed';
    case 'cancelled':
      return 'Cancelled';
    case 'no_show':
      return 'No Show';
    default:
      return status;
  }
};

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
      header: 'Date/Time',
      cell: ({ row }) => {
        const date = new Date(row.original.scheduled_date);
        const start = row.original.time_window_start.slice(0, 5);
        const end = row.original.time_window_end.slice(0, 5);
        return (
          <div className="flex flex-col gap-1">
            <div className="flex items-center gap-1.5 text-sm font-medium text-slate-700">
              <Calendar className="h-3.5 w-3.5 text-slate-400" />
              {format(date, 'MMM d, yyyy')}
            </div>
            <div className="flex items-center gap-1.5 text-xs text-slate-500">
              <Clock className="h-3 w-3 text-slate-400" />
              {start} - {end}
            </div>
          </div>
        );
      },
    },
    {
      accessorKey: 'job_id',
      header: 'Job',
      cell: ({ row }) => {
        const jobType = row.original.job_type;
        const customerName = row.original.customer_name;
        return (
          <div className="flex flex-col gap-0.5">
            <span className="text-sm font-medium text-slate-700">
              {jobType ? jobType.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()) : 'Unknown Job'}
            </span>
            {customerName && (
              <span className="text-xs text-slate-500">
                {customerName}
              </span>
            )}
          </div>
        );
      },
    },
    {
      accessorKey: 'staff_id',
      header: 'Staff',
      cell: ({ row }) => {
        const staffName = row.original.staff_name;
        const initials = staffName 
          ? staffName.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2)
          : row.original.staff_id.slice(0, 2).toUpperCase();
        return (
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-full bg-slate-200 text-slate-600 font-semibold text-xs flex items-center justify-center">
              {initials}
            </div>
            <span className="text-sm text-slate-600">
              {staffName || 'Unknown Staff'}
            </span>
          </div>
        );
      },
    },
    {
      accessorKey: 'status',
      header: 'Status',
      cell: ({ row }) => {
        const status = row.original.status;
        return (
          <Badge
            className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusBadgeClasses(status)}`}
            data-testid={`status-${status}`}
          >
            {getStatusLabel(status)}
          </Badge>
        );
      },
    },
    {
      accessorKey: 'route_order',
      header: 'Route #',
      cell: ({ row }) => (
        <span className="text-sm text-slate-500">
          {row.original.route_order ?? '-'}
        </span>
      ),
    },
    {
      id: 'actions',
      header: 'Actions',
      cell: ({ row }) => (
        <Button
          variant="ghost"
          size="sm"
          className="text-slate-400 hover:text-teal-600 hover:bg-teal-50 rounded-lg p-2 transition-colors"
          onClick={(e) => {
            e.stopPropagation();
            onAppointmentClick?.(row.original.id);
          }}
          data-testid={`view-appointment-${row.original.id}`}
        >
          <MoreHorizontal className="h-4 w-4" />
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
    <div data-testid="appointment-list" className="space-y-4">
      {/* Table Container with design system styling */}
      <div className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
        {/* Toolbar */}
        <div className="p-4 border-b border-slate-100 flex flex-wrap gap-4">
          <div className="w-48">
            <Select
              value={params.status ?? 'all'}
              onValueChange={handleStatusChange}
            >
              <SelectTrigger 
                data-testid="status-filter"
                className="border-slate-200 rounded-lg bg-white text-slate-700 text-sm focus:ring-2 focus:ring-teal-100 focus:border-teal-500"
              >
                <SelectValue placeholder="Filter by status" />
              </SelectTrigger>
              <SelectContent className="bg-white rounded-lg shadow-lg border border-slate-100">
                {statusOptions.map((option) => (
                  <SelectItem 
                    key={option.value} 
                    value={option.value}
                    className="hover:bg-slate-50 text-slate-700"
                  >
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-sm text-slate-500">From:</span>
            <Input
              type="date"
              value={params.date_from ?? ''}
              onChange={handleDateFromChange}
              className="w-40 border-slate-200 rounded-lg bg-white text-slate-700 text-sm focus:ring-2 focus:ring-teal-100 focus:border-teal-500"
              data-testid="date-from-filter"
            />
          </div>
          <div className="flex items-center gap-2">
            <span className="text-sm text-slate-500">To:</span>
            <Input
              type="date"
              value={params.date_to ?? ''}
              onChange={handleDateToChange}
              className="w-40 border-slate-200 rounded-lg bg-white text-slate-700 text-sm focus:ring-2 focus:ring-teal-100 focus:border-teal-500"
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
            <div className="overflow-x-auto">
              <Table data-testid="appointment-table">
                <TableHeader>
                  {table.getHeaderGroups().map((headerGroup) => (
                    <TableRow key={headerGroup.id} className="bg-slate-50/50">
                      {headerGroup.headers.map((header) => (
                        <TableHead 
                          key={header.id}
                          className="px-6 py-4 text-slate-500 text-xs uppercase tracking-wider font-medium"
                        >
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
                  {table.getRowModel().rows.length === 0 ? (
                    <TableRow>
                      <TableCell
                        colSpan={columns.length}
                        className="h-24 text-center text-slate-500"
                      >
                        No appointments found.
                      </TableCell>
                    </TableRow>
                  ) : (
                    table.getRowModel().rows.map((row) => (
                      <TableRow
                        key={row.id}
                        data-testid="appointment-row"
                        className="cursor-pointer hover:bg-slate-50/80 transition-colors"
                        onClick={() => onAppointmentClick?.(row.original.id)}
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
                  {Math.min(params.page! * params.page_size!, data.total)} of{' '}
                  {data.total} appointments
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    className="border-slate-200 text-slate-700 hover:bg-slate-50"
                    onClick={() =>
                      setParams((prev) => ({ ...prev, page: prev.page! - 1 }))
                    }
                    disabled={params.page === 1}
                    data-testid="prev-page-btn"
                  >
                    <ChevronLeft className="h-4 w-4" />
                    Previous
                  </Button>
                  <span className="text-sm text-slate-600">
                    Page {params.page} of {data.total_pages}
                  </span>
                  <Button
                    variant="outline"
                    size="sm"
                    className="border-slate-200 text-slate-700 hover:bg-slate-50"
                    onClick={() =>
                      setParams((prev) => ({ ...prev, page: prev.page! + 1 }))
                    }
                    disabled={params.page === data.total_pages}
                    data-testid="next-page-btn"
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
    </div>
  );
}
