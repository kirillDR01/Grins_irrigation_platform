import { useState, useCallback, useEffect } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import {
  flexRender,
  getCoreRowModel,
  useReactTable,
  type ColumnDef,
} from '@tanstack/react-table';
import { Phone, Inbox, MessageSquare, Plus, X, Trash2, ArrowRightCircle, Briefcase, ShoppingCart } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { LoadingPage, ErrorMessage } from '@/shared/components';
import { useLeads } from '../hooks/useLeads';
import { useDeleteLead, useMoveToJobs, useMoveToSales, useMarkContacted } from '../hooks/useLeadMutations';
import { LeadStatusBadge } from './LeadStatusBadge';
import { LeadTagBadges } from './LeadTagBadges';
import { LeadFilters } from './LeadFilters';
import { FollowUpQueue } from './FollowUpQueue';
import { BulkOutreach } from './BulkOutreach';
import { SheetsSync } from './SheetsSync';
import { CreateLeadDialog } from './CreateLeadDialog';
import { NewTextCampaignModal } from '@/features/communications';
import type { Lead, LeadListParams } from '../types';
import { LEAD_SOURCE_LABELS } from '../types';

export function LeadsList() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [highlightedLeadId, setHighlightedLeadId] = useState<string | null>(null);
  const [selectedLeadIds, setSelectedLeadIds] = useState<string[]>([]);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [campaignModalOpen, setCampaignModalOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<Lead | null>(null);
  const [estimateWarningLead, setEstimateWarningLead] = useState<Lead | null>(null);

  const urlStatus = searchParams.get('status') as LeadListParams['status'] | null;
  const urlHighlight = searchParams.get('highlight');

  const [params, setParams] = useState<LeadListParams>({
    page: 1,
    page_size: 20,
    sort_by: 'created_at',
    sort_order: 'desc',
    status: urlStatus && ['new', 'contacted'].includes(urlStatus)
      ? (urlStatus as LeadListParams['status'])
      : undefined,
  });

  useEffect(() => {
    if (urlHighlight) {
      setHighlightedLeadId(urlHighlight);
      const timer = setTimeout(() => setHighlightedLeadId(null), 3000);
      return () => clearTimeout(timer);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const { data, isLoading, error, refetch } = useLeads(params);
  const deleteLead = useDeleteLead();
  const moveToJobs = useMoveToJobs();
  const moveToSales = useMoveToSales();
  const markContacted = useMarkContacted();

  const handleFilterChange = useCallback(
    (changes: Partial<LeadListParams>) => {
      setParams((prev) => ({ ...prev, ...changes }));
      if ('status' in changes) {
        const newParams = new URLSearchParams(searchParams);
        if (changes.status) {
          newParams.set('status', changes.status);
        } else {
          newParams.delete('status');
        }
        setSearchParams(newParams, { replace: true });
      }
    },
    [searchParams, setSearchParams]
  );

  const handleRowClick = useCallback(
    (lead: Lead) => {
      navigate(`/leads/${lead.id}`);
    },
    [navigate]
  );

  const handleMoveToJobs = useCallback(
    async (e: React.MouseEvent, lead: Lead) => {
      e.stopPropagation();
      try {
        const result = await moveToJobs.mutateAsync({ id: lead.id });
        if (result.requires_estimate_warning) {
          setEstimateWarningLead(lead);
          return;
        }
        toast.success(`${lead.name} moved to Jobs`);
      } catch {
        toast.error('Failed to move lead to Jobs');
      }
    },
    [moveToJobs]
  );

  const handleEstimateConfirmMoveToJobs = useCallback(async () => {
    if (!estimateWarningLead) return;
    try {
      await moveToJobs.mutateAsync({ id: estimateWarningLead.id, force: true });
      toast.success(`${estimateWarningLead.name} moved to Jobs (estimate override)`);
    } catch {
      toast.error('Failed to move lead to Jobs');
    } finally {
      setEstimateWarningLead(null);
    }
  }, [estimateWarningLead, moveToJobs]);

  const handleEstimateConfirmMoveToSales = useCallback(async () => {
    if (!estimateWarningLead) return;
    try {
      const result = await moveToSales.mutateAsync(estimateWarningLead.id);
      if (result.merged_into_customer) {
        toast.success(`Merged into existing customer: ${result.merged_into_customer.name}`);
      } else {
        toast.success(`${estimateWarningLead.name} moved to Sales`);
      }
    } catch {
      toast.error('Failed to move lead to Sales');
    } finally {
      setEstimateWarningLead(null);
    }
  }, [estimateWarningLead, moveToSales]);

  const handleMoveToSales = useCallback(
    async (e: React.MouseEvent, lead: Lead) => {
      e.stopPropagation();
      try {
        const result = await moveToSales.mutateAsync(lead.id);
        if (result.merged_into_customer) {
          toast.success(`Merged into existing customer: ${result.merged_into_customer.name}`);
        } else {
          toast.success(`${lead.name} moved to Sales`);
        }
      } catch {
        toast.error('Failed to move lead to Sales');
      }
    },
    [moveToSales]
  );

  const handleMarkContacted = useCallback(
    async (e: React.MouseEvent, lead: Lead) => {
      e.stopPropagation();
      try {
        await markContacted.mutateAsync(lead.id);
        toast.success(`${lead.name} marked as contacted`);
      } catch {
        toast.error('Failed to mark lead as contacted');
      }
    },
    [markContacted]
  );

  const handleDeleteConfirm = useCallback(async () => {
    if (!deleteTarget) return;
    try {
      await deleteLead.mutateAsync(deleteTarget.id);
      toast.success(`${deleteTarget.name} permanently deleted`);
    } catch {
      toast.error('Failed to delete lead');
    } finally {
      setDeleteTarget(null);
    }
  }, [deleteTarget, deleteLead]);

  // Select all / individual selection
  const allLeadIds = data?.items?.map((l) => l.id) ?? [];
  const allSelected = allLeadIds.length > 0 && selectedLeadIds.length === allLeadIds.length;

  const toggleSelectAll = () => {
    setSelectedLeadIds(allSelected ? [] : allLeadIds);
  };

  const toggleSelectLead = (id: string) => {
    setSelectedLeadIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  };

  const columns: ColumnDef<Lead>[] = [
    {
      id: 'select',
      header: () => (
        <Checkbox
          checked={allSelected}
          onCheckedChange={toggleSelectAll}
          aria-label="Select all"
          data-testid="select-all-checkbox"
        />
      ),
      cell: ({ row }) => (
        <Checkbox
          checked={selectedLeadIds.includes(row.original.id)}
          onCheckedChange={() => toggleSelectLead(row.original.id)}
          aria-label={`Select ${row.original.name}`}
          onClick={(e) => e.stopPropagation()}
          data-testid={`select-lead-${row.original.id}`}
        />
      ),
    },
    {
      accessorKey: 'name',
      header: () => (
        <span className="text-slate-500 text-xs uppercase tracking-wider font-medium">
          Name
        </span>
      ),
      cell: ({ row }) => (
        <Link
          to={`/leads/${row.original.id}`}
          className="text-sm font-medium text-slate-700 hover:text-teal-600 transition-colors"
          data-testid={`lead-name-${row.original.id}`}
        >
          {row.original.name}
        </Link>
      ),
    },
    {
      accessorKey: 'phone',
      header: () => (
        <span className="text-slate-500 text-xs uppercase tracking-wider font-medium">
          Phone
        </span>
      ),
      cell: ({ row }) => (
        <div className="flex items-center gap-2">
          <Phone className="h-3.5 w-3.5 text-slate-400" />
          <span className="text-sm text-slate-600">{row.original.phone}</span>
        </div>
      ),
    },
    {
      accessorKey: 'address',
      header: () => (
        <span className="text-slate-500 text-xs uppercase tracking-wider font-medium">
          Job Address
        </span>
      ),
      cell: ({ row }) => (
        <span className="text-sm text-slate-600">
          {row.original.address ?? '—'}
        </span>
      ),
    },
    {
      accessorKey: 'city',
      header: () => (
        <span className="text-slate-500 text-xs uppercase tracking-wider font-medium">
          City
        </span>
      ),
      cell: ({ row }) => (
        <span className="text-sm text-slate-600" data-testid={`lead-city-${row.original.id}`}>
          {row.original.city ?? '—'}
        </span>
      ),
    },
    {
      accessorKey: 'job_requested',
      header: () => (
        <span className="text-slate-500 text-xs uppercase tracking-wider font-medium">
          Job Requested
        </span>
      ),
      cell: ({ row }) => (
        <span className="text-sm text-slate-600" data-testid={`lead-job-requested-${row.original.id}`}>
          {row.original.job_requested ?? '—'}
        </span>
      ),
    },
    {
      id: 'action_tags',
      header: () => (
        <span className="text-slate-500 text-xs uppercase tracking-wider font-medium">
          Tags
        </span>
      ),
      cell: ({ row }) => (
        <LeadTagBadges tags={row.original.action_tags ?? []} />
      ),
    },
    {
      accessorKey: 'status',
      header: () => (
        <span className="text-slate-500 text-xs uppercase tracking-wider font-medium">
          Status
        </span>
      ),
      cell: ({ row }) => <LeadStatusBadge status={row.original.status} />,
    },
    {
      accessorKey: 'last_contacted_at',
      header: () => (
        <span className="text-slate-500 text-xs uppercase tracking-wider font-medium">
          Last Contacted
        </span>
      ),
      cell: ({ row }) => {
        const val = row.original.last_contacted_at;
        if (!val) return <span className="text-sm text-slate-400">—</span>;
        const date = new Date(val);
        return (
          <span className="text-sm text-slate-500" title={date.toLocaleString()}>
            {formatDistanceToNow(date, { addSuffix: true })}
          </span>
        );
      },
    },
    {
      accessorKey: 'created_at',
      header: () => (
        <span className="text-slate-500 text-xs uppercase tracking-wider font-medium">
          Submitted
        </span>
      ),
      cell: ({ row }) => {
        const date = new Date(row.original.created_at);
        return (
          <span className="text-sm text-slate-500" title={date.toLocaleString()}>
            {formatDistanceToNow(date, { addSuffix: true })}
          </span>
        );
      },
    },
    {
      id: 'lead_source',
      header: () => (
        <span className="text-slate-500 text-xs uppercase tracking-wider font-medium">
          Source
        </span>
      ),
      cell: ({ row }) => (
        <span
          className="text-sm text-slate-600"
          data-testid={`lead-source-${row.original.lead_source}`}
        >
          {LEAD_SOURCE_LABELS[row.original.lead_source] ?? row.original.lead_source}
        </span>
      ),
    },
    {
      id: 'actions',
      header: () => (
        <span className="text-slate-500 text-xs uppercase tracking-wider font-medium">
          Actions
        </span>
      ),
      cell: ({ row }) => (
        <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
          {row.original.status === 'new' && (
            <Button
              variant="ghost"
              size="sm"
              className="h-7 px-2 text-yellow-600 hover:text-yellow-700 hover:bg-yellow-50"
              onClick={(e) => handleMarkContacted(e, row.original)}
              data-testid={`mark-contacted-${row.original.id}`}
              title="Mark as Contacted"
            >
              <ArrowRightCircle className="h-3.5 w-3.5" />
            </Button>
          )}
          <Button
            variant="ghost"
            size="sm"
            className="h-7 px-2 text-blue-600 hover:text-blue-700 hover:bg-blue-50"
            onClick={(e) => handleMoveToJobs(e, row.original)}
            data-testid={`move-to-jobs-${row.original.id}`}
            title="Move to Jobs"
          >
            <Briefcase className="h-3.5 w-3.5" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className="h-7 px-2 text-purple-600 hover:text-purple-700 hover:bg-purple-50"
            onClick={(e) => handleMoveToSales(e, row.original)}
            data-testid={`move-to-sales-${row.original.id}`}
            title="Move to Sales"
          >
            <ShoppingCart className="h-3.5 w-3.5" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className="h-7 px-2 text-red-500 hover:text-red-700 hover:bg-red-50"
            onClick={(e) => {
              e.stopPropagation();
              setDeleteTarget(row.original);
            }}
            data-testid={`delete-lead-${row.original.id}`}
            title="Delete lead"
          >
            <Trash2 className="h-3.5 w-3.5" />
          </Button>
        </div>
      ),
    },
  ];

  const table = useReactTable({
    data: data?.items ?? [],
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  if (isLoading) {
    return <LoadingPage message="Loading leads..." />;
  }

  if (error) {
    return <ErrorMessage error={error} onRetry={() => refetch()} />;
  }

  return (
    <div data-testid="leads-page" className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Leads</h1>
          {data && (
            <p className="text-sm text-slate-500 mt-1">
              {data.total} {data.total === 1 ? 'lead' : 'leads'} total
            </p>
          )}
        </div>
        <div className="flex items-center gap-2">
          <SheetsSync />
          <BulkOutreach
            selectedLeadIds={selectedLeadIds}
            onComplete={() => {
              setSelectedLeadIds([]);
              refetch();
            }}
          />
          <Button
            onClick={() => setCreateDialogOpen(true)}
            data-testid="add-lead-btn"
            className="bg-teal-500 hover:bg-teal-600 text-white shadow-sm shadow-teal-200"
          >
            <Plus className="mr-2 h-4 w-4" />
            Add Lead
          </Button>
        </div>
      </div>

      {/* Create Lead Dialog */}
      <CreateLeadDialog open={createDialogOpen} onOpenChange={setCreateDialogOpen} />

      {/* Follow-Up Queue Panel */}
      <FollowUpQueue />

      {/* Filters */}
      <LeadFilters params={params} onChange={handleFilterChange} />

      {/* Table */}
      <div className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
        <Table data-testid="leads-table">
          <TableHeader>
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow
                key={headerGroup.id}
                className="bg-slate-50/50 hover:bg-slate-50/50"
              >
                {headerGroup.headers.map((header) => (
                  <TableHead key={header.id} className="px-6 py-4">
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
            {table.getRowModel().rows?.length ? (
              table.getRowModel().rows.map((row) => (
                <TableRow
                  key={row.id}
                  data-testid="lead-row"
                  data-lead-id={row.original.id}
                  className={`hover:bg-slate-50/80 transition-colors cursor-pointer ${
                    highlightedLeadId === row.original.id ? 'animate-highlight-pulse' : ''
                  }`}
                  onClick={() => handleRowClick(row.original)}
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
            ) : (
              <TableRow>
                <TableCell
                  colSpan={columns.length}
                  className="h-32 text-center"
                >
                  <div className="flex flex-col items-center gap-2 text-slate-500">
                    <Inbox className="h-8 w-8 text-slate-300" />
                    <p className="text-sm">No leads found.</p>
                    <p className="text-xs text-slate-400">
                      Try adjusting your filters or check back later.
                    </p>
                  </div>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>

        {/* Pagination */}
        {data && data.total > 0 && (
          <div
            className="p-4 border-t border-slate-100 flex items-center justify-between"
            data-testid="leads-pagination"
          >
            <div className="text-sm text-slate-500">
              Showing{' '}
              {Math.min((params.page! - 1) * params.page_size! + 1, data.total)}{' '}
              to {Math.min(params.page! * params.page_size!, data.total)} of{' '}
              {data.total} leads
            </div>
            <div className="flex items-center gap-2">
              <span className="text-sm text-slate-500">
                Page {data.page} of {data.total_pages}
              </span>
              <Button
                variant="outline"
                size="sm"
                onClick={() =>
                  setParams((p) => ({ ...p, page: (p.page ?? 1) - 1 }))
                }
                disabled={params.page === 1}
                data-testid="leads-prev-page"
              >
                Previous
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() =>
                  setParams((p) => ({ ...p, page: (p.page ?? 1) + 1 }))
                }
                disabled={params.page === data.total_pages}
                data-testid="leads-next-page"
              >
                Next
              </Button>
            </div>
          </div>
        )}
      </div>

      {/* Sticky Bulk Action Bar */}
      {selectedLeadIds.length > 0 && (
        <div
          className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 flex items-center gap-3 bg-slate-900 text-white px-5 py-3 rounded-xl shadow-lg"
          data-testid="bulk-action-bar"
        >
          <span className="text-sm font-medium" data-testid="selected-count">
            {selectedLeadIds.length} selected
          </span>
          <Button
            size="sm"
            variant="secondary"
            className="gap-2"
            onClick={() => setCampaignModalOpen(true)}
            data-testid="text-selected-leads-btn"
          >
            <MessageSquare className="h-4 w-4" />
            Text Selected
          </Button>
          <Button
            size="sm"
            variant="ghost"
            className="text-white hover:text-white hover:bg-slate-700"
            onClick={() => setSelectedLeadIds([])}
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
          if (!open) setSelectedLeadIds([]);
        }}
        preSelectedLeadIds={selectedLeadIds}
      />

      {/* Delete Confirmation Dialog */}
      <Dialog open={!!deleteTarget} onOpenChange={(open) => !open && setDeleteTarget(null)}>
        <DialogContent data-testid="delete-lead-dialog">
          <DialogHeader>
            <DialogTitle>Delete Lead</DialogTitle>
            <DialogDescription>
              This will permanently delete <strong>{deleteTarget?.name}</strong>. This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setDeleteTarget(null)}
              data-testid="cancel-delete-btn"
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleDeleteConfirm}
              disabled={deleteLead.isPending}
              data-testid="confirm-delete-btn"
            >
              {deleteLead.isPending ? 'Deleting...' : 'Delete Permanently'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Estimate Warning Modal (Smoothing Req 6.1, 6.3) */}
      <Dialog open={!!estimateWarningLead} onOpenChange={(open) => !open && setEstimateWarningLead(null)}>
        <DialogContent data-testid="estimate-warning-dialog">
          <DialogHeader>
            <DialogTitle>Estimate Required</DialogTitle>
            <DialogDescription>
              This job type typically requires an estimate. Move to Jobs anyway, or move to Sales for the estimate workflow?
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="flex flex-col sm:flex-row gap-2">
            <Button
              variant="outline"
              onClick={() => setEstimateWarningLead(null)}
              data-testid="estimate-warning-cancel-btn"
            >
              Cancel
            </Button>
            <Button
              variant="default"
              className="bg-purple-600 hover:bg-purple-700 text-white"
              onClick={handleEstimateConfirmMoveToSales}
              disabled={moveToSales.isPending}
              data-testid="estimate-warning-move-to-sales-btn"
            >
              Move to Sales
            </Button>
            <Button
              variant="default"
              className="bg-blue-600 hover:bg-blue-700 text-white"
              onClick={handleEstimateConfirmMoveToJobs}
              disabled={moveToJobs.isPending}
              data-testid="estimate-warning-move-to-jobs-btn"
            >
              Move to Jobs
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
