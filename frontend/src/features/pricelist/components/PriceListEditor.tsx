import { useMemo, useState } from 'react';
import { Plus, Search, History as HistoryIcon } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { ErrorMessage, LoadingPage } from '@/shared/components';
import {
  useDeactivateServiceOffering,
  useServiceOfferings,
} from '../hooks';
import {
  PRICING_MODEL_LABEL,
  SERVICE_CATEGORY_LABEL,
  type CustomerType,
  type ServiceCategory,
  type ServiceOffering,
  offeringDisplayLabel,
} from '../types';
import { ServiceOfferingDrawer } from './ServiceOfferingDrawer';
import { ArchiveHistorySheet } from './ArchiveHistorySheet';

const PAGE_SIZE_OPTIONS = [20, 50, 100] as const;

const CATEGORY_OPTIONS: ServiceCategory[] = [
  'seasonal',
  'repair',
  'installation',
  'diagnostic',
  'landscaping',
];

type CustomerTypeFilter = CustomerType | 'both';

export function PriceListEditor() {
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState<number>(20);
  const [customerType, setCustomerType] = useState<CustomerTypeFilter>('both');
  const [category, setCategory] = useState<ServiceCategory | 'all'>('all');
  const [search, setSearch] = useState('');
  const [showInactive, setShowInactive] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editTarget, setEditTarget] = useState<ServiceOffering | null>(null);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [historyTarget, setHistoryTarget] = useState<ServiceOffering | null>(
    null,
  );

  const params = useMemo(
    () => ({
      page,
      page_size: pageSize,
      customer_type: customerType === 'both' ? undefined : customerType,
      category: category === 'all' ? undefined : category,
      is_active: showInactive ? undefined : true,
      sort_by: 'name',
      sort_order: 'asc' as const,
    }),
    [page, pageSize, customerType, category, showInactive],
  );

  const { data, isLoading, isError, error, refetch } = useServiceOfferings(params);
  const deactivate = useDeactivateServiceOffering();

  const filtered = useMemo(() => {
    if (!data?.items) return [] as ServiceOffering[];
    if (!search.trim()) return data.items;
    const q = search.toLowerCase();
    return data.items.filter((o) => {
      const label = offeringDisplayLabel(o).toLowerCase();
      const slug = (o.slug ?? '').toLowerCase();
      const sub = (o.subcategory ?? '').toLowerCase();
      return label.includes(q) || slug.includes(q) || sub.includes(q);
    });
  }, [data?.items, search]);

  function handleNew() {
    setEditTarget(null);
    setDrawerOpen(true);
  }

  function handleEdit(o: ServiceOffering) {
    setEditTarget(o);
    setDrawerOpen(true);
  }

  function handleHistory(o: ServiceOffering) {
    setHistoryTarget(o);
    setHistoryOpen(true);
  }

  async function handleDeactivate(o: ServiceOffering) {
    if (
      !window.confirm(
        `Deactivate "${offeringDisplayLabel(o)}"? It will hide from estimate pickers.`,
      )
    ) {
      return;
    }
    try {
      await deactivate.mutateAsync(o.id);
      toast.success(`Deactivated "${offeringDisplayLabel(o)}"`);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Deactivate failed');
    }
  }

  async function handleExport() {
    try {
      // Lazy import to avoid pulling axios cancellation types into the page bundle.
      const { serviceApi } = await import('../api/serviceApi');
      const md = await serviceApi.exportMarkdown();
      const blob = new Blob([md], { type: 'text/markdown' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'pricelist.md';
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Export failed');
    }
  }

  return (
    <div className="space-y-4" data-testid="price-list-editor">
      {/* Filter row */}
      <div className="flex flex-wrap items-center gap-3 rounded-md border border-slate-200 bg-white p-3">
        <div className="relative flex-1 min-w-[220px]">
          <Search className="absolute left-2 top-2.5 h-4 w-4 text-slate-400" />
          <Input
            data-testid="price-list-search"
            placeholder="Search name, slug, subcategory…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-8"
          />
        </div>

        <Select
          value={customerType}
          onValueChange={(v) => {
            setPage(1);
            setCustomerType(v as CustomerTypeFilter);
          }}
        >
          <SelectTrigger
            className="w-[160px]"
            data-testid="price-list-customer-type"
          >
            <SelectValue placeholder="Customer type" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="both">All customer types</SelectItem>
            <SelectItem value="residential">Residential</SelectItem>
            <SelectItem value="commercial">Commercial</SelectItem>
          </SelectContent>
        </Select>

        <Select
          value={category}
          onValueChange={(v) => {
            setPage(1);
            setCategory(v as ServiceCategory | 'all');
          }}
        >
          <SelectTrigger className="w-[160px]" data-testid="price-list-category">
            <SelectValue placeholder="Category" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All categories</SelectItem>
            {CATEGORY_OPTIONS.map((c) => (
              <SelectItem key={c} value={c}>
                {SERVICE_CATEGORY_LABEL[c]}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <label className="flex items-center gap-2 text-sm text-slate-600">
          <Checkbox
            checked={showInactive}
            onCheckedChange={(v) => {
              setPage(1);
              setShowInactive(v === true);
            }}
            data-testid="price-list-show-inactive"
          />
          Show inactive
        </label>

        <div className="ml-auto flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleExport}
            data-testid="price-list-export"
          >
            Export pricelist.md
          </Button>
          <Button onClick={handleNew} data-testid="price-list-new">
            <Plus className="h-4 w-4 mr-1" />
            New offering
          </Button>
        </div>
      </div>

      {/* Table */}
      {isLoading && <LoadingPage message="Loading pricelist…" />}
      {isError && (
        <ErrorMessage
          error={error instanceof Error ? error : new Error('Failed to load pricelist')}
          onRetry={() => refetch()}
        />
      )}
      {!isLoading && !isError && (
        <div className="rounded-md border border-slate-200 bg-white overflow-hidden">
          <Table data-testid="price-list-table">
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Customer</TableHead>
                <TableHead>Category</TableHead>
                <TableHead>Pricing model</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filtered.length === 0 && (
                <TableRow>
                  <TableCell
                    colSpan={6}
                    className="text-center text-sm text-slate-500 py-8"
                    data-testid="price-list-empty"
                  >
                    No offerings match the current filters.
                  </TableCell>
                </TableRow>
              )}
              {filtered.map((o) => (
                <TableRow key={o.id} data-testid={`price-list-row-${o.id}`}>
                  <TableCell>
                    <div className="font-medium text-slate-800">
                      {offeringDisplayLabel(o)}
                    </div>
                    {o.slug && (
                      <div className="text-xs text-slate-400">{o.slug}</div>
                    )}
                  </TableCell>
                  <TableCell className="capitalize">
                    {o.customer_type ?? '—'}
                  </TableCell>
                  <TableCell>
                    {SERVICE_CATEGORY_LABEL[o.category] ?? o.category}
                    {o.subcategory && (
                      <span className="text-xs text-slate-400">
                        {' '}
                        · {o.subcategory}
                      </span>
                    )}
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline">
                      {PRICING_MODEL_LABEL[o.pricing_model] ?? o.pricing_model}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    {o.is_active ? (
                      <span className="text-emerald-600 text-sm">Active</span>
                    ) : (
                      <span className="text-slate-400 text-sm">Inactive</span>
                    )}
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleHistory(o)}
                        data-testid={`price-list-history-${o.id}`}
                        aria-label="View history"
                      >
                        <HistoryIcon className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleEdit(o)}
                        data-testid={`price-list-edit-${o.id}`}
                      >
                        Edit
                      </Button>
                      {o.is_active && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDeactivate(o)}
                          data-testid={`price-list-deactivate-${o.id}`}
                        >
                          Deactivate
                        </Button>
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      {/* Pagination */}
      {data && data.total > 0 && (
        <div className="flex items-center justify-between text-sm text-slate-600">
          <div>
            Showing {(data.page - 1) * data.page_size + 1}–
            {Math.min(data.page * data.page_size, data.total)} of {data.total}
          </div>
          <div className="flex items-center gap-2">
            <Select
              value={String(pageSize)}
              onValueChange={(v) => {
                setPage(1);
                setPageSize(Number(v));
              }}
            >
              <SelectTrigger
                className="w-[80px]"
                data-testid="price-list-page-size"
              >
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {PAGE_SIZE_OPTIONS.map((n) => (
                  <SelectItem key={n} value={String(n)}>
                    {n}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button
              variant="outline"
              size="sm"
              disabled={page <= 1}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              data-testid="price-list-prev"
            >
              Previous
            </Button>
            <span data-testid="price-list-page-indicator">
              Page {data.page} / {data.total_pages || 1}
            </span>
            <Button
              variant="outline"
              size="sm"
              disabled={page >= (data.total_pages || 1)}
              onClick={() => setPage((p) => p + 1)}
              data-testid="price-list-next"
            >
              Next
            </Button>
          </div>
        </div>
      )}

      <ServiceOfferingDrawer
        open={drawerOpen}
        onOpenChange={setDrawerOpen}
        offering={editTarget}
      />
      <ArchiveHistorySheet
        open={historyOpen}
        onOpenChange={setHistoryOpen}
        offering={historyTarget}
      />
    </div>
  );
}
