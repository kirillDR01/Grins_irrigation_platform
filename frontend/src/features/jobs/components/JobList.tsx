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
import { ArrowUpDown, MoreHorizontal, Search } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
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
import { formatJobType, formatAmount } from '../types';

interface JobListProps {
  onEdit?: (job: Job) => void;
  onDelete?: (job: Job) => void;
  onStatusChange?: (job: Job, status: JobStatus) => void;
  customerId?: string;
}

export function JobList({ onEdit, onDelete, onStatusChange, customerId }: JobListProps) {
  const [sorting, setSorting] = useState<SortingState>([]);
  const [searchQuery, setSearchQuery] = useState('');
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
          className="text-slate-500 text-xs uppercase tracking-wider font-medium hover:bg-transparent hover:text-slate-700"
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
            className="text-sm font-medium text-slate-700 hover:text-teal-600 transition-colors"
            data-testid={`job-type-${job.id}`}
          >
            {formatJobType(job.job_type)}
          </Link>
        );
      },
    },
    {
      accessorKey: 'status',
      header: () => (
        <span className="text-slate-500 text-xs uppercase tracking-wider font-medium">
          Status
        </span>
      ),
      cell: ({ row }) => (
        <span data-testid="job-status-badge">
          <JobStatusBadge status={row.original.status} />
        </span>
      ),
    },
    {
      accessorKey: 'category',
      header: () => (
        <span className="text-slate-500 text-xs uppercase tracking-wider font-medium">
          Category
        </span>
      ),
      cell: ({ row }) => (
        <span
          className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-medium ${
            row.original.category === 'ready_to_schedule'
              ? 'bg-emerald-50 text-emerald-600 border border-emerald-100'
              : 'bg-amber-50 text-amber-600 border border-amber-100'
          }`}
        >
          {row.original.category === 'ready_to_schedule'
            ? 'Ready'
            : 'Needs Estimate'}
        </span>
      ),
    },
    {
      accessorKey: 'priority_level',
      header: () => (
        <span className="text-slate-500 text-xs uppercase tracking-wider font-medium">
          Priority
        </span>
      ),
      cell: ({ row }) => {
        const priority = row.original.priority_level;
        const config = {
          0: { label: 'Normal', className: 'bg-slate-100 text-slate-500' },
          1: { label: 'High', className: 'bg-orange-50 text-orange-600' },
          2: { label: 'Urgent', className: 'bg-red-100 text-red-600' },
        }[priority] || { label: 'Normal', className: 'bg-slate-100 text-slate-500' };

        return (
          <span
            className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-medium ${config.className}`}
          >
            {config.label}
          </span>
        );
      },
    },
    {
      accessorKey: 'quoted_amount',
      header: () => (
        <span className="text-slate-500 text-xs uppercase tracking-wider font-medium">
          Amount
        </span>
      ),
      cell: ({ row }) => {
        const amount = row.original.final_amount || row.original.quoted_amount;
        return amount ? (
          <span className="text-sm text-slate-600">
            {formatAmount(amount)}
          </span>
        ) : (
          <span className="text-sm text-slate-400 italic">Not quoted</span>
        );
      },
    },
    {
      accessorKey: 'created_at',
      header: ({ column }) => (
        <Button
          variant="ghost"
          onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
          className="text-slate-500 text-xs uppercase tracking-wider font-medium hover:bg-transparent hover:text-slate-700"
        >
          Created
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      ),
      cell: ({ row }) => {
        const date = new Date(row.original.created_at);
        return (
          <span className="text-sm text-slate-500">
            {date.toLocaleDateString()}
          </span>
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
        const job = row.original;
        return (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                className="h-8 w-8 p-0 hover:text-teal-600 hover:bg-teal-50 rounded-lg transition-colors"
                data-testid={`job-actions-${job.id}`}
              >
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" data-testid="dropdown-menu">
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
      {/* Table Container with Design System Styling */}
      <div className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
        {/* Table Toolbar */}
        <div className="p-4 border-b border-slate-100 flex gap-4 items-center flex-wrap">
          {/* Search Input */}
          <div className="relative flex-1 min-w-[200px] max-w-sm">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
            <Input
              type="text"
              placeholder="Search jobs..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10 bg-slate-50 border-slate-200 rounded-lg focus:ring-2 focus:ring-teal-500/20 focus:border-teal-500"
              data-testid="job-search"
            />
          </div>

          {/* Status Filter */}
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
            <SelectTrigger className="w-[160px]" data-testid="status-filter">
              <SelectValue placeholder="Status" />
            </SelectTrigger>
            <SelectContent data-testid="status-filter-options">
              <SelectItem value="all">All Statuses</SelectItem>
              <SelectItem value="requested" data-testid="status-requested">Requested</SelectItem>
              <SelectItem value="approved">Approved</SelectItem>
              <SelectItem value="scheduled" data-testid="status-scheduled">Scheduled</SelectItem>
              <SelectItem value="in_progress">In Progress</SelectItem>
              <SelectItem value="completed">Completed</SelectItem>
              <SelectItem value="cancelled">Cancelled</SelectItem>
              <SelectItem value="closed">Closed</SelectItem>
            </SelectContent>
          </Select>

          {/* Category Filter */}
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
            <SelectTrigger className="w-[180px]" data-testid="category-filter">
              <SelectValue placeholder="Category" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Categories</SelectItem>
              <SelectItem value="ready_to_schedule">Ready to Schedule</SelectItem>
              <SelectItem value="requires_estimate">Requires Estimate</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Table */}
        <Table data-testid="job-table">
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
                  data-testid="job-row"
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
                  No jobs found.
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
              {Math.min(params.page! * params.page_size!, data.total)} of {data.total} jobs
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
    </div>
  );
}
