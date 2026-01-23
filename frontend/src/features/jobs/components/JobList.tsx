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
import { ArrowUpDown, MoreHorizontal, Clock, DollarSign } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
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
import { LoadingPage, ErrorMessage } from '@/shared/components';
import { useJobs } from '../hooks';
import { JobStatusBadge } from './JobStatusBadge';
import type { Job, JobListParams, JobStatus, JobCategory } from '../types';
import { formatJobType, formatDuration, formatAmount } from '../types';

interface JobListProps {
  onEdit?: (job: Job) => void;
  onDelete?: (job: Job) => void;
  onStatusChange?: (job: Job, status: JobStatus) => void;
  customerId?: string;
}

export function JobList({ onEdit, onDelete, onStatusChange, customerId }: JobListProps) {
  const [sorting, setSorting] = useState<SortingState>([]);
  const [params, setParams] = useState<JobListParams>({
    page: 1,
    page_size: 20,
    customer_id: customerId,
  });

  const { data, isLoading, error, refetch } = useJobs(params);

  const columns: ColumnDef<Job>[] = [
    {
      accessorKey: 'job_type',
      header: ({ column }) => (
        <Button
          variant="ghost"
          onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
        >
          Job Type
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      ),
      cell: ({ row }) => {
        const job = row.original;
        return (
          <Link
            to={`/jobs/${job.id}`}
            className="font-medium hover:underline"
            data-testid={`job-type-${job.id}`}
          >
            {formatJobType(job.job_type)}
          </Link>
        );
      },
    },
    {
      accessorKey: 'status',
      header: 'Status',
      cell: ({ row }) => <JobStatusBadge status={row.original.status} />,
    },
    {
      accessorKey: 'category',
      header: 'Category',
      cell: ({ row }) => (
        <span
          className={`inline-flex items-center rounded-full px-2 py-1 text-xs font-medium ${
            row.original.category === 'ready_to_schedule'
              ? 'bg-green-100 text-green-800'
              : 'bg-amber-100 text-amber-800'
          }`}
        >
          {row.original.category === 'ready_to_schedule'
            ? 'Ready to Schedule'
            : 'Requires Estimate'}
        </span>
      ),
    },
    {
      accessorKey: 'priority_level',
      header: 'Priority',
      cell: ({ row }) => {
        const priority = row.original.priority_level;
        const config = {
          0: { label: 'Normal', className: 'bg-gray-100 text-gray-800' },
          1: { label: 'High', className: 'bg-orange-100 text-orange-800' },
          2: { label: 'Urgent', className: 'bg-red-100 text-red-800' },
        }[priority] || { label: 'Normal', className: 'bg-gray-100 text-gray-800' };

        return (
          <span
            className={`inline-flex items-center rounded-full px-2 py-1 text-xs font-medium ${config.className}`}
          >
            {config.label}
          </span>
        );
      },
    },
    {
      accessorKey: 'estimated_duration_minutes',
      header: 'Duration',
      cell: ({ row }) => (
        <div className="flex items-center gap-1 text-muted-foreground">
          <Clock className="h-4 w-4" />
          <span>{formatDuration(row.original.estimated_duration_minutes)}</span>
        </div>
      ),
    },
    {
      accessorKey: 'quoted_amount',
      header: 'Amount',
      cell: ({ row }) => (
        <div className="flex items-center gap-1">
          <DollarSign className="h-4 w-4 text-muted-foreground" />
          <span>
            {row.original.final_amount
              ? formatAmount(row.original.final_amount)
              : formatAmount(row.original.quoted_amount)}
          </span>
        </div>
      ),
    },
    {
      accessorKey: 'created_at',
      header: ({ column }) => (
        <Button
          variant="ghost"
          onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
        >
          Created
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      ),
      cell: ({ row }) => {
        const date = new Date(row.original.created_at);
        return (
          <span className="text-muted-foreground">
            {date.toLocaleDateString()}
          </span>
        );
      },
    },
    {
      id: 'actions',
      cell: ({ row }) => {
        const job = row.original;
        return (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                className="h-8 w-8 p-0"
                data-testid={`job-actions-${job.id}`}
              >
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem asChild>
                <Link to={`/jobs/${job.id}`}>View Details</Link>
              </DropdownMenuItem>
              {onEdit && (
                <DropdownMenuItem onClick={() => onEdit(job)}>Edit</DropdownMenuItem>
              )}
              <DropdownMenuSeparator />
              {onStatusChange && job.status === 'requested' && (
                <DropdownMenuItem onClick={() => onStatusChange(job, 'approved')}>
                  Approve
                </DropdownMenuItem>
              )}
              {onStatusChange && job.status === 'in_progress' && (
                <DropdownMenuItem onClick={() => onStatusChange(job, 'completed')}>
                  Mark Complete
                </DropdownMenuItem>
              )}
              {onStatusChange && job.status === 'completed' && (
                <DropdownMenuItem onClick={() => onStatusChange(job, 'closed')}>
                  Close Job
                </DropdownMenuItem>
              )}
              <DropdownMenuSeparator />
              {onStatusChange && !['cancelled', 'closed'].includes(job.status) && (
                <DropdownMenuItem
                  onClick={() => onStatusChange(job, 'cancelled')}
                  className="text-destructive"
                >
                  Cancel Job
                </DropdownMenuItem>
              )}
              {onDelete && (
                <DropdownMenuItem
                  onClick={() => onDelete(job)}
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
    return <LoadingPage message="Loading jobs..." />;
  }

  if (error) {
    return <ErrorMessage error={error} onRetry={() => refetch()} />;
  }

  return (
    <div data-testid="job-list">
      {/* Filters */}
      <div className="flex gap-4 mb-4">
        <Select
          value={params.status || 'all'}
          onValueChange={(value) =>
            setParams((p) => ({
              ...p,
              status: value === 'all' ? undefined : (value as JobStatus),
              page: 1,
            }))
          }
        >
          <SelectTrigger className="w-[180px]" data-testid="status-filter">
            <SelectValue placeholder="Filter by status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Statuses</SelectItem>
            <SelectItem value="requested">Requested</SelectItem>
            <SelectItem value="approved">Approved</SelectItem>
            <SelectItem value="scheduled">Scheduled</SelectItem>
            <SelectItem value="in_progress">In Progress</SelectItem>
            <SelectItem value="completed">Completed</SelectItem>
            <SelectItem value="cancelled">Cancelled</SelectItem>
            <SelectItem value="closed">Closed</SelectItem>
          </SelectContent>
        </Select>

        <Select
          value={params.category || 'all'}
          onValueChange={(value) =>
            setParams((p) => ({
              ...p,
              category: value === 'all' ? undefined : (value as JobCategory),
              page: 1,
            }))
          }
        >
          <SelectTrigger className="w-[200px]" data-testid="category-filter">
            <SelectValue placeholder="Filter by category" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Categories</SelectItem>
            <SelectItem value="ready_to_schedule">Ready to Schedule</SelectItem>
            <SelectItem value="requires_estimate">Requires Estimate</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="rounded-md border overflow-x-auto">
        <Table data-testid="job-table">
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
                <TableRow key={row.id} data-testid="job-row">
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
                  No jobs found.
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
            {Math.min(params.page! * params.page_size!, data.total)} of {data.total} jobs
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
