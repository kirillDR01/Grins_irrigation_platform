import { useState, useEffect, useCallback } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import {
  flexRender,
  getCoreRowModel,
  useReactTable,
  getSortedRowModel,
  type ColumnDef,
  type SortingState,
} from '@tanstack/react-table';
import { ArrowUpDown, MoreHorizontal, AlertTriangle, ShieldCheck, CalendarPlus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { GlobalSearch } from '@/shared/components/GlobalSearch';
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
import { LoadingPage, ErrorMessage, WeekPicker, PropertyTags } from '@/shared/components';
import { useJobs } from '../hooks';
import { JobWeekEditor } from './JobWeekEditor';
import type { Job, JobListParams, JobStatus, JobStatusLabel } from '../types';
import {
  formatJobType,
  formatAmount,
  getSimplifiedStatusConfig,
  JOB_STATUS_CONFIG,
  LABEL_STATUS_MAP,
  STATUS_LABEL_MAP,
  CUSTOMER_TAG_CONFIG,
  calculateDaysWaiting,
  getDueByColorClass,
} from '../types';
import type { CustomerTag, JobCategory } from '../types';

interface JobListProps {
  onEdit?: (job: Job) => void;
  onDelete?: (job: Job) => void;
  onStatusChange?: (job: Job, status: JobStatus) => void;
  customerId?: string;
}

// Map filter label to backend status for API
function getStatusFilterValue(label: string): JobStatus | undefined {
  if (label === 'all') return undefined;
  return LABEL_STATUS_MAP[label as JobStatusLabel];
}

export function JobList({ onEdit, onDelete, onStatusChange, customerId }: JobListProps) {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [sorting, setSorting] = useState<SortingState>([]);
  const [highlightedJobId, setHighlightedJobId] = useState<string | null>(null);
  const [simplifiedFilter, setSimplifiedFilter] = useState<string>('all');

  // Parse initial status from URL query params
  const urlStatus = searchParams.get('status') as JobStatus | null;
  const urlHighlight = searchParams.get('highlight');

  const validStatuses: JobStatus[] = ['to_be_scheduled', 'scheduled', 'in_progress', 'completed', 'cancelled'];

  const [params, setParams] = useState<JobListParams>({
    page: 1,
    page_size: 20,
    customer_id: customerId,
    status: urlStatus && validStatuses.includes(urlStatus) ? urlStatus : undefined,
  });

  // Initialize simplified filter from URL status
  useEffect(() => {
    if (urlStatus && validStatuses.includes(urlStatus)) {
      const label = STATUS_LABEL_MAP[urlStatus];
      setSimplifiedFilter(label);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Apply highlight from URL on mount (param stays in URL for refresh persistence)
  useEffect(() => {
    if (urlHighlight) {
      setHighlightedJobId(urlHighlight);
      const timer = setTimeout(() => {
        setHighlightedJobId(null);
      }, 3000);
      return () => clearTimeout(timer);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Free-text job search is delegated to the shared <GlobalSearch
  // scope="job" /> toolbar widget which navigates to the job detail page
  // on result click. The Jobs list itself no longer drives `params.search`
  // — Cluster C harmonized this with the top-bar search.

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
                className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-medium text-emerald-700 border border-emerald-200"
                data-testid={`prepaid-badge-${job.id}`}
                title="Covered by Service Agreement"
              >
                <ShieldCheck className="h-3 w-3" />
                Prepaid
              </span>
            )}
            {job.category === 'requires_estimate' && (
              <span
                className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2 py-0.5 text-xs font-medium text-amber-700 border border-amber-200"
                data-testid={`estimate-needed-badge-${job.id}`}
                title="Estimate Needed"
              >
                <AlertTriangle className="h-3 w-3" />
                Estimate Needed
              </span>
            )}
            <PropertyTags
              propertyType={job.property_type}
              isHoa={job.property_is_hoa ?? false}
              isSubscription={job.property_is_subscription ?? false}
            />
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
          Week Of
        </span>
      ),
      cell: ({ row }) => {
        // Inline editor for jobs in `to_be_scheduled`; renders plain text
        // (with the due-by color cue) for other statuses. Re-fetch the
        // list after a save so filters / sorting stay consistent.
        const colorClass = getDueByColorClass(row.original.target_end_date);
        return (
          <span className={`text-sm ${colorClass}`}>
            <JobWeekEditor job={row.original} onSaved={() => refetch()} />
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
        const isSchedulable = job.status === 'to_be_scheduled' || job.status === 'scheduled';
        return (
          <div className="flex items-center gap-1">
            {isSchedulable && (
              <Button
                variant="outline"
                size="sm"
                className="h-8 px-2.5 text-xs border-teal-200 text-teal-600 hover:bg-teal-50 hover:text-teal-700"
                data-testid={`schedule-job-btn-${job.id}`}
                onClick={() => navigate(`/schedule?scheduleJobId=${job.id}`)}
              >
                <CalendarPlus className="mr-1 h-3.5 w-3.5" />
                Schedule
              </Button>
            )}
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
              {onStatusChange && job.status === 'to_be_scheduled' && (
                <DropdownMenuItem onClick={() => onStatusChange(job, 'in_progress')}>
                  Start Job
                </DropdownMenuItem>
              )}
              {onStatusChange && job.status === 'in_progress' && (
                <DropdownMenuItem onClick={() => onStatusChange(job, 'completed')}>
                  Mark Complete
                </DropdownMenuItem>
              )}
              <DropdownMenuSeparator />
              {onStatusChange && !['cancelled', 'completed'].includes(job.status) && (
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
    return <LoadingPage message="Loading jobs..." />;
  }

  if (error) {
    return <ErrorMessage error={error} onRetry={() => refetch()} />;
  }

  return (
    <div data-testid="job-list">
      <div className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-x-auto">
        {/* Table Toolbar */}
        <div className="p-4 border-b border-slate-100 flex gap-4 items-center flex-wrap">
          {/* Shared global-search component (job-scoped) */}
          <div className="flex-1 min-w-[200px] max-w-sm">
            <GlobalSearch scope="job" />
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
              {(Object.entries(JOB_STATUS_CONFIG) as [JobStatus, { label: string }][]).map(([, cfg]) => (
                <SelectItem key={cfg.label} value={cfg.label} data-testid={`status-${cfg.label.toLowerCase().replace(/\s+/g, '-')}`}>
                  {cfg.label}
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

          {/* Category Filter — Estimate Needed (Smoothing Req 6.6) */}
          <Select
            value={params.category ?? 'all'}
            onValueChange={(v) =>
              setParams((p) => ({
                ...p,
                category: v === 'all' ? undefined : (v as JobCategory),
                page: 1,
              }))
            }
          >
            <SelectTrigger className="w-[180px]" data-testid="category-filter">
              <SelectValue placeholder="Category" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Categories</SelectItem>
              <SelectItem value="requires_estimate" data-testid="filter-requires-estimate">Estimate Needed</SelectItem>
              <SelectItem value="ready_to_schedule">Ready to Schedule</SelectItem>
            </SelectContent>
          </Select>

          {/* Property Type Filter (Req 8.5) */}
          <Select
            value={params.property_type ?? 'all'}
            onValueChange={(v) => setParams((p) => ({ ...p, page: 1, property_type: v === 'all' ? undefined : (v as 'residential' | 'commercial') }))}
          >
            <SelectTrigger className="w-[150px]" data-testid="property-type-filter">
              <SelectValue placeholder="Property Type" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Types</SelectItem>
              <SelectItem value="residential">Residential</SelectItem>
              <SelectItem value="commercial">Commercial</SelectItem>
            </SelectContent>
          </Select>

          {/* HOA Filter (Req 8.5) */}
          <Select
            value={params.is_hoa === undefined ? 'all' : params.is_hoa ? 'yes' : 'no'}
            onValueChange={(v) => setParams((p) => ({ ...p, page: 1, is_hoa: v === 'all' ? undefined : v === 'yes' }))}
          >
            <SelectTrigger className="w-[120px]" data-testid="hoa-filter">
              <SelectValue placeholder="HOA" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All</SelectItem>
              <SelectItem value="yes">HOA</SelectItem>
              <SelectItem value="no">Non-HOA</SelectItem>
            </SelectContent>
          </Select>

          {/* Week Of Filter (CRM2 Req 20) */}
          <WeekPicker
            value={params.target_date_from ?? null}
            onChange={(mondayIso) =>
              setParams((p) => ({
                ...p,
                target_date_from: mondayIso ?? undefined,
                target_date_to: mondayIso
                  ? (() => {
                      const [y, m, d] = mondayIso.split('-').map(Number);
                      const sun = new Date(y, m - 1, d + 6);
                      return `${sun.getFullYear()}-${String(sun.getMonth() + 1).padStart(2, '0')}-${String(sun.getDate()).padStart(2, '0')}`;
                    })()
                  : undefined,
                page: 1,
              }))
            }
            placeholder="Filter by week"
            className="w-[200px]"
            data-testid="target-week-filter"
          />
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
                    highlightedJobId === row.original.id ? 'animate-highlight-pulse' : ''
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
