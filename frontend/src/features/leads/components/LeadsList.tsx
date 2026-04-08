import { useState, useCallback, useEffect } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import {
  flexRender,
  getCoreRowModel,
  useReactTable,
  type ColumnDef,
} from '@tanstack/react-table';
import { Phone, Inbox, MessageSquare, FileCheck, Plus, X } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
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
import { LeadStatusBadge } from './LeadStatusBadge';
import { LeadSourceBadge } from './LeadSourceBadge';
import { IntakeTagBadge } from './IntakeTagBadge';
import { LeadTagBadges } from './LeadTagBadges';
import { LeadFilters } from './LeadFilters';
import { FollowUpQueue } from './FollowUpQueue';
import { BulkOutreach } from './BulkOutreach';
import { SheetsSync } from './SheetsSync';
import { CreateLeadDialog } from './CreateLeadDialog';
import { NewTextCampaignModal } from '@/features/communications';
import type { Lead, LeadListParams } from '../types';

export function LeadsList() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [highlightedLeadId, setHighlightedLeadId] = useState<string | null>(null);
  const [selectedLeadIds, setSelectedLeadIds] = useState<string[]>([]);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [campaignModalOpen, setCampaignModalOpen] = useState(false);

  // Parse initial status from URL query params
  const urlStatus = searchParams.get('status') as LeadListParams['status'] | null;
  const urlHighlight = searchParams.get('highlight');

  const [params, setParams] = useState<LeadListParams>({
    page: 1,
    page_size: 20,
    sort_by: 'created_at',
    sort_order: 'desc',
    status: urlStatus && ['new', 'contacted', 'qualified', 'converted', 'lost', 'spam'].includes(urlStatus)
      ? (urlStatus as LeadListParams['status'])
      : undefined,
  });

  // Apply highlight from URL on mount
  useEffect(() => {
    if (urlHighlight) {
      setHighlightedLeadId(urlHighlight);
      const timer = setTimeout(() => {
        setHighlightedLeadId(null);
      }, 3000);
      const newParams = new URLSearchParams(searchParams);
      newParams.delete('highlight');
      setSearchParams(newParams, { replace: true });
      return () => clearTimeout(timer);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const { data, isLoading, error, refetch } = useLeads(params);

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

  // Select all / individual selection
  const allLeadIds = data?.items?.map((l) => l.id) ?? [];
  const allSelected = allLeadIds.length > 0 && selectedLeadIds.length === allLeadIds.length;

  const toggleSelectAll = () => {
    if (allSelected) {
      setSelectedLeadIds([]);
    } else {
      setSelectedLeadIds(allLeadIds);
    }
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
      accessorKey: 'city',
      header: () => (
        <span className="text-slate-500 text-xs uppercase tracking-wider font-medium">
          City
        </span>
      ),
      cell: ({ row }) => (
        <span className="text-sm text-slate-600" data-testid={`lead-city-${row.original.id}`}>
          {row.original.city ?? row.original.address ?? '—'}
        </span>
      ),
    },
    {
      id: 'lead_source',
      header: () => (
        <span className="text-slate-500 text-xs uppercase tracking-wider font-medium">
          Source
        </span>
      ),
      cell: ({ row }) => (
        <LeadSourceBadge source={row.original.lead_source} />
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
      id: 'intake_tag',
      header: () => (
        <span className="text-slate-500 text-xs uppercase tracking-wider font-medium">
          Intake
        </span>
      ),
      cell: ({ row }) => (
        <IntakeTagBadge tag={row.original.intake_tag} />
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
      id: 'consent',
      header: () => (
        <span className="text-slate-500 text-xs uppercase tracking-wider font-medium">
          Consent
        </span>
      ),
      cell: ({ row }) => (
        <div className="flex items-center gap-2">
          <span
            title={row.original.sms_consent ? 'SMS consent given' : 'No SMS consent'}
            data-testid={`sms-consent-${row.original.id}`}
          >
            <MessageSquare
              className={`h-4 w-4 ${row.original.sms_consent ? 'text-green-500' : 'text-gray-300'}`}
            />
          </span>
          <span
            title={row.original.terms_accepted ? 'Terms accepted' : 'Terms not accepted'}
            data-testid={`terms-accepted-${row.original.id}`}
          >
            <FileCheck
              className={`h-4 w-4 ${row.original.terms_accepted ? 'text-green-500' : 'text-gray-300'}`}
            />
          </span>
        </div>
      ),
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
                    highlightedLeadId === row.original.id ? 'animate-highlight-fade' : ''
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
    </div>
  );
}
