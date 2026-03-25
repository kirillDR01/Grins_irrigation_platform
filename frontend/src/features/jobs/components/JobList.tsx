import { useState, useEffect, useCallback } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import {
  flexRender,
  getCoreRowModel,
  useReactTable,
  getSortedRowModel,
  type ColumnDef,
  type SortingState,
} from '@tanstack/react-table';
import { ArrowUpDown, MoreHorizontal, Search, FileText, CalendarIcon } from 'lucide-react';
import { format } from 'date-fns';
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
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import { Calendar } from '@/components/ui/calendar';
import { LoadingPage, ErrorMessage } from '@/shared/components';
import { useJobs } from '../hooks';
import type { Job, JobListParams, JobStatus, SimplifiedJobStatus } from '../types';
import {
  formatJobType,
  formatAmount,
  getSimplifiedStatus,
  getSimplifiedStatusConfig,
  SIMPLIFIED_STATUS_CONFIG,
  SIMPLIFIED_STATUS_RAW_MAP,
  CUSTOMER_TAG_CONFIG,
  calculateDaysWaiting,
  getDueByColorClass,
} from '../types';
import type { CustomerTag } from '../types';

interface JobListProps {
  onEdit?: (job: Job) => void;
  onDelete?: (job: Job) => void;
  onStatusChange?: (job: Job, status: JobStatus) => void;
  customerId?: string;
}

// Map simplified filter value to raw statuses for API
function getStatusFilterValue(simplified: string): JobStatus | undefined {
  if (simplified === 'all') return undefined;
  const rawStatuses = SIMPLIFIED_STATUS_RAW_MAP[simplified as SimplifiedJobStatus];
  // Use the first raw status for API filtering; backend should handle the mapping
  return rawStatuses?.[0];
}

export function JobList({ onEdit, onDelete, onStatusChange, customerId }: JobListProps) {
  const [searchParams, setSearchParams] = useSearchParams();
  const [sorting, setSorting] = useState<SortingState>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [highlightedJobId, setHighlightedJobId] = useState<string | null>(null);
  const [simplifiedFilter, setSimplifiedFilter] = useState<string>('all');

  // Parse initial status from URL query params
  const urlStatus = searchParams.get('status') as JobStatus | null;
  const urlHighlight = searchParams.get('highlight');

  const validStatuses: JobStatus[] = ['requested', 'approved', 'scheduled', 'in_progress', 'completed', 'cancelled', 'closed'];

  const [params, setParams] = useState<JobListParams>({
    page: 1,
    page_size: 20,
    customer_id: customerId,
    status: urlStatus && validStatuses.includes(urlStatus) ? urlStatus : undefined,
  });

  // Initialize simplified filter from URL status
  useEffect(() => {
    if (urlStatus && validStatuses.includes(urlStatus)) {
      const simplified = getSimplifiedStatus(urlStatus);
      setSimplifiedFilter(simplified);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Apply highlight from URL on mount
  useEffect(() => {
    if (urlHighlight) {
      setHighlightedJobId(urlHighlight);
      const timer = setTimeout(() => {
        setHighlightedJobId(null);
      }, 3000);
      const newParams = new URLSearchParams(searchParams);
      newParams.delete('highlight');
      setSearchParams(newParams, { replace: true });
      return () => clearTimeout(timer);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Handle simplified status filter change (Req 21)
  const handleStatusChange = useCallback(
    (value: string) => {
      setSimplifiedFilter(value);
      const newStatus = getStatusFilterValue(value);
      setParams((p) => ({ ...p, status: newStatus, page: 1 }));
      const newParams = new URLSearchParams(searchParams);
      if (newStatus) {
        newParams.set('status', newStatus);
      } else {
        newParams.delete('status');
      }
      setSearchParams(newParams, { replace: true });
    },
    [searchParams, setSearchParams],
  );

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
          <div className="flex items-center gap-2">
            <Link
              to={`/jobs/${job.id}`}
              className="text-sm font-medium text-slate-700 hover:text-teal-600 transition-colors"
              data-testid={`job-type-${job.id}`}
            >
              {formatJobType(job.job_type)}
            </Link>
            {job.service_agreement_id && (
              <span
                className="inline-flex items-center gap-1 rounded-full bg-indigo-50 px-2 py-0.5 text-xs font-medium text-indigo-600 border border-indigo-100"
                data-testid={`subscription-badge-${job.id}`}
                title="Subscription job"
              >
                <FileText className="h-3 w-3" />
                Sub
              </span>
            )}
          </div>
        );
      },
    },
    {
      accessorKey: 'summary',
      header: () => (
        <span className="text-slate-500 text-xs uppercase tracking-wider font-medium">
          Summary
        </span>
      ),
      cell: ({ row }) => {
        const summary = row.original.summary;
        return summary ? (
          <span className="text-sm text-slate-600 truncate max-w-[200px] block" data-testid={`job-summary-${row.original.id}`}>
            {summary}
          </span>
        ) : (
          <span className="text-sm text-slate-400 italic">—</span>
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
      cell: ({ row }) => {
        const config = getSimplifiedStatusConfig(row.original.status);
        return (
          <span
            className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-medium ${config.bgColor} ${config.color}`}
            data-testid="job-status-badge"
          >
            {config.label}
          </span>
        );
      },
    },
    {
      id: 'customer',
      header: () => (
        <span className="text-slate-500 text-xs uppercase tracking-wider font-medium">
          Customer
        </span>
      ),
      cell: ({ row }) => {
        const job = row.original;
        const name = job.customer_name;
        return name ? (
          <Link
            to={`/customers/${job.customer_id}`}
            className="text-sm font-medium text-slate-700 hover:text-teal-600 transition-colors"
            data-testid={`job-customer-${job.id}`}
          >
            {name}
          </Link>
        ) : (
          <span className="text-sm text-slate-400 italic">Unknown</span>
        );
      },
    },
    {
      id: 'tags',
      header: () => (
        <span className="text-slate-500 text-xs uppercase tracking-wider font-medium">
          Tags
        </span>
      ),
      cell: ({ row }) => {
        const tags = row.original.customer_tags;
        if (!tags || tags.length === 0) {
          return <span className="text-sm text-slate-400 italic">—</span>;
        }
        return (
          <div className="flex flex-wrap gap-1" data-testid={`job-tags-${row.original.id}`}>
            {tags.map((tag: CustomerTag) => {
              const config = CUSTOMER_TAG_CONFIG[tag];
              if (!config) return null;
              return (
                <span
                  key={tag}
                  className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${config.bgColor} ${config.color}`}
                  data-testid={`tag-${tag}`}
                >
                  {config.label}
                </span>
              );
            })}
          </div>
        );
      },
    },
    {
      id: 'days_waiting',
      header: ({ column }) => (
        <Button
          variant="ghost"
          onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
          className="text-slate-500 text-xs uppercase tracking-wider font-medium hover:bg-transparent hover:text-slate-700"
        >
          Days Waiting
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      ),
      sortingFn: (rowA, rowB) => {
        const daysA = calculateDaysWaiting(rowA.original.created_at);
        const daysB = calculateDaysWaiting(rowB.original.created_at);
        return daysA - daysB;
      },
      cell: ({ row }) => {
        const days = calculateDaysWaiting(row.original.created_at);
        return (
          <span className="text-sm text-slate-600" data-testid={`days-waiting-${row.original.id}`}>
            {days}
          </span>
        );
      },
    },
    {
      id: 'due_by',
      header: () => (
        <span className="text-slate-500 text-xs uppercase tracking-wider font-medium">
          Due By
        </span>
      ),
      cell: ({ row }) => {
        const targetEnd = row.original.target_end_date;
        if (!targetEnd) {
          return (
            <span className="text-sm text-slate-400 italic" data-testid={`due-by-${row.original.id}`}>
              No deadline
            </span>
          );
        }
        const colorClass = getDueByColorClass(targetEnd);
        return (
          <span className={`text-sm ${colorClass}`} data-testid={`due-by-${row.original.id}`}>
            {format(new Date(targetEnd + 'T00:00:00'), 'MMM d, yyyy')}
          </span>
        );
      },
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

          {/* Simplified Status Filter (Req 21) */}
          <Select
            value={simplifiedFilter}
            onValueChange={handleStatusChange}
          >
            <SelectTrigger className="w-[180px]" data-testid="status-filter">
              <SelectValue placeholder="Status" />
            </SelectTrigger>
            <SelectContent data-testid="status-filter-options">
              <SelectItem value="all">All Statuses</SelectItem>
              {(Object.keys(SIMPLIFIED_STATUS_CONFIG) as SimplifiedJobStatus[]).map((status) => (
                <SelectItem key={status} value={status} data-testid={`status-${status.toLowerCase().replace(/\s+/g, '-')}`}>
                  {status}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          {/* Subscription Source Filter */}
          <Select
            value={
              params.has_service_agreement === true
                ? 'subscription'
                : params.has_service_agreement === false
                  ? 'standalone'
                  : 'all'
            }
            onValueChange={(value) =>
              setParams((p) => ({
                ...p,
                has_service_agreement:
                  value === 'subscription' ? true : value === 'standalone' ? false : undefined,
                page: 1,
              }))
            }
          >
            <SelectTrigger className="w-[160px]" data-testid="source-type-filter">
              <SelectValue placeholder="Source" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Sources</SelectItem>
              <SelectItem value="subscription">Subscription</SelectItem>
              <SelectItem value="standalone">Standalone</SelectItem>
            </SelectContent>
          </Select>

          {/* Target Date Range Filter */}
          <Popover>
            <PopoverTrigger asChild>
              <Button
                variant="outline"
                className="w-[200px] justify-start text-left font-normal"
                data-testid="target-date-filter"
              >
                <CalendarIcon className="mr-2 h-4 w-4" />
                {params.target_date_from || params.target_date_to ? (
                  <span className="text-sm">
                    {params.target_date_from
                      ? format(new Date(params.target_date_from + 'T00:00:00'), 'MMM d')
                      : '...'}
                    {' – '}
                    {params.target_date_to
                      ? format(new Date(params.target_date_to + 'T00:00:00'), 'MMM d')
                      : '...'}
                  </span>
                ) : (
                  <span className="text-sm text-muted-foreground">Target dates</span>
                )}
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-auto p-4" align="start">
              <div className="space-y-3">
                <div>
                  <label className="text-xs font-medium text-slate-500">From</label>
                  <Calendar
                    mode="single"
                    selected={
                      params.target_date_from
                        ? new Date(params.target_date_from + 'T00:00:00')
                        : undefined
                    }
                    onSelect={(date) =>
                      setParams((p) => ({
                        ...p,
                        target_date_from: date ? format(date, 'yyyy-MM-dd') : undefined,
                        page: 1,
                      }))
                    }
                    data-testid="target-date-from-calendar"
                  />
                </div>
                <div>
                  <label className="text-xs font-medium text-slate-500">To</label>
                  <Calendar
                    mode="single"
                    selected={
                      params.target_date_to
                        ? new Date(params.target_date_to + 'T00:00:00')
                        : undefined
                    }
                    onSelect={(date) =>
                      setParams((p) => ({
                        ...p,
                        target_date_to: date ? format(date, 'yyyy-MM-dd') : undefined,
                        page: 1,
                      }))
                    }
                    data-testid="target-date-to-calendar"
                  />
                </div>
                {(params.target_date_from || params.target_date_to) && (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="w-full"
                    onClick={() =>
                      setParams((p) => ({
                        ...p,
                        target_date_from: undefined,
                        target_date_to: undefined,
                        page: 1,
                      }))
                    }
                  >
                    Clear dates
                  </Button>
                )}
              </div>
            </PopoverContent>
          </Popover>
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
                  data-job-id={row.original.id}
                  className={`hover:bg-slate-50/80 transition-colors ${
                    highlightedJobId === row.original.id ? 'animate-highlight-fade' : ''
                  }`}
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
