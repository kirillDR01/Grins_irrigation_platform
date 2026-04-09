/**
 * AudienceBuilder — Step 1 of the campaign wizard.
 *
 * Three additive source panels: Customers, Leads, Ad-hoc CSV.
 * Running total at top, live preview via audience/preview endpoint,
 * dedupe warning for cross-source phone collisions.
 *
 * Validates: Requirements 15.3, 15.4, 15.5, 15.6, 15.7, 25, 35
 */

import { useState, useCallback, useEffect, useMemo, useRef } from 'react';
import axios from 'axios';
import { Users, UserPlus, FileSpreadsheet, Upload, AlertTriangle, Search } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
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
import { useDebounce } from '@/shared/hooks/useDebounce';
import { useCustomers } from '@/features/customers/hooks';
import { useLeads } from '@/features/leads/hooks/useLeads';
import { useAudiencePreview, useAudienceCsv } from '../hooks';
import type { CustomerListParams } from '@/features/customers/types';
import type { LeadListParams } from '@/features/leads/types';
import type {
  TargetAudience,
  CustomerAudienceFilter,
  LeadAudienceFilter,
  AudiencePreview,
  CsvUploadResult,
} from '../types/campaign';

// --- Constants ---

const ATTESTATION_TEXT =
  'I confirm that all recipients in this CSV have provided prior express written consent to receive SMS marketing messages from Grins Irrigation, and I have records of such consent available for review.';
const ATTESTATION_VERSION = '1.0';
const CSV_MAX_SIZE_MB = 2;
const CSV_MAX_ROWS = 5000;

// Radix Select does not allow empty-string values, so use a sentinel.
const ALL_SOURCES_VALUE = '__all__';

// --- Props ---

export interface AudienceBuilderProps {
  /** Current audience value from parent form */
  value: TargetAudience;
  /** Callback when audience changes */
  onChange: (audience: TargetAudience) => void;
  /** Pre-populated customer IDs (from "Text Selected" on Customers tab) */
  preSelectedCustomerIds?: string[];
  /** Pre-populated lead IDs (from "Text Selected" on Leads tab) */
  preSelectedLeadIds?: string[];
}

type SourcePanel = 'customers' | 'leads' | 'adhoc';

export function AudienceBuilder({
  value,
  onChange,
  preSelectedCustomerIds,
  preSelectedLeadIds,
}: AudienceBuilderProps) {
  const [activePanel, setActivePanel] = useState<SourcePanel>(
    preSelectedLeadIds?.length ? 'leads' : 'customers',
  );

  // --- Customer state ---
  const [customerSearch, setCustomerSearch] = useState('');
  const debouncedCustomerSearch = useDebounce(customerSearch, 300);
  const [customerParams, setCustomerParams] = useState<CustomerListParams>({
    page: 1,
    page_size: 20,
  });
  const [selectedCustomerIds, setSelectedCustomerIds] = useState<string[]>(
    preSelectedCustomerIds ?? value.customers?.ids_include ?? [],
  );
  const [customerSmsFilter, setCustomerSmsFilter] = useState(true);
  const [customerCityFilter, setCustomerCityFilter] = useState('');

  // --- Lead state ---
  const [leadSearch, setLeadSearch] = useState('');
  const debouncedLeadSearch = useDebounce(leadSearch, 300);
  const [leadParams, setLeadParams] = useState<LeadListParams>({
    page: 1,
    page_size: 20,
  });
  const [selectedLeadIds, setSelectedLeadIds] = useState<string[]>(
    preSelectedLeadIds ?? value.leads?.ids_include ?? [],
  );
  const [leadSmsFilter, setLeadSmsFilter] = useState(true);
  const [leadSourceFilter, setLeadSourceFilter] = useState('');

  // --- Ad-hoc CSV state ---
  const [csvResult, setCsvResult] = useState<CsvUploadResult | null>(null);
  const [attestationChecked, setAttestationChecked] = useState(false);
  const [csvError, setCsvError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // --- Preview state ---
  const [preview, setPreview] = useState<AudiencePreview | null>(null);

  // --- Data fetching ---
  const { data: customersData, isLoading: customersLoading } = useCustomers({
    ...customerParams,
    search: debouncedCustomerSearch || undefined,
    sms_opt_in: customerSmsFilter || undefined,
  });
  const { data: leadsData, isLoading: leadsLoading } = useLeads({
    ...leadParams,
    search: debouncedLeadSearch || undefined,
  });
  const audiencePreviewMutation = useAudiencePreview();
  const csvUploadMutation = useAudienceCsv();

  // --- Build audience and propagate changes ---
  const buildAudience = useCallback((): TargetAudience => {
    const audience: TargetAudience = {};

    if (selectedCustomerIds.length > 0) {
      const filter: CustomerAudienceFilter = {
        ids_include: selectedCustomerIds,
        sms_opt_in: customerSmsFilter || null,
      };
      if (customerCityFilter) filter.cities = [customerCityFilter];
      audience.customers = filter;
    }

    if (selectedLeadIds.length > 0) {
      const filter: LeadAudienceFilter = {
        ids_include: selectedLeadIds,
        sms_consent: leadSmsFilter || null,
      };
      if (leadSourceFilter) filter.lead_source = leadSourceFilter;
      audience.leads = filter;
    }

    if (csvResult && csvResult.recipients.length > 0) {
      audience.ad_hoc = {
        csv_upload_id: csvResult.upload_id,
        recipients: csvResult.recipients,
        staff_attestation_confirmed: attestationChecked,
        attestation_text_shown: ATTESTATION_TEXT,
        attestation_version: ATTESTATION_VERSION,
      };
    }

    return audience;
  }, [
    selectedCustomerIds,
    selectedLeadIds,
    csvResult,
    attestationChecked,
    customerSmsFilter,
    customerCityFilter,
    leadSmsFilter,
    leadSourceFilter,
  ]);

  // Propagate audience changes to parent
  useEffect(() => {
    onChange(buildAudience());
  }, [buildAudience]); // eslint-disable-line react-hooks/exhaustive-deps

  // Fetch preview when selections change
  const hasSelection =
    selectedCustomerIds.length > 0 ||
    selectedLeadIds.length > 0 ||
    csvResult != null;

  useEffect(() => {
    if (hasSelection) {
      const audience = buildAudience();
      audiencePreviewMutation.mutate(audience, {
        onSuccess: (data) => setPreview(data),
        onError: () => setPreview(null),
      });
    }
  }, [selectedCustomerIds.length, selectedLeadIds.length, csvResult]); // eslint-disable-line react-hooks/exhaustive-deps

  // Derive effective preview — null when nothing selected
  const effectivePreview = hasSelection ? preview : null;

  // --- Totals ---
  const totalSelected =
    selectedCustomerIds.length +
    selectedLeadIds.length +
    (csvResult ? csvResult.total_rows - csvResult.rejected - csvResult.duplicates_collapsed : 0);

  const dedupeCount = effectivePreview
    ? totalSelected - effectivePreview.total
    : 0;

  // --- Customer selection handlers ---
  const toggleCustomer = useCallback((id: string) => {
    setSelectedCustomerIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id],
    );
  }, []);

  const toggleAllCustomers = useCallback(() => {
    const pageIds = customersData?.items.map((c) => c.id) ?? [];
    const allSelected = pageIds.every((id) => selectedCustomerIds.includes(id));
    if (allSelected) {
      setSelectedCustomerIds((prev) => prev.filter((id) => !pageIds.includes(id)));
    } else {
      setSelectedCustomerIds((prev) => [...new Set([...prev, ...pageIds])]);
    }
  }, [customersData, selectedCustomerIds]);

  // --- Lead selection handlers ---
  const toggleLead = useCallback((id: string) => {
    setSelectedLeadIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id],
    );
  }, []);

  const toggleAllLeads = useCallback(() => {
    const pageIds = leadsData?.items.map((l) => l.id) ?? [];
    const allSelected = pageIds.every((id) => selectedLeadIds.includes(id));
    if (allSelected) {
      setSelectedLeadIds((prev) => prev.filter((id) => !pageIds.includes(id)));
    } else {
      setSelectedLeadIds((prev) => [...new Set([...prev, ...pageIds])]);
    }
  }, [leadsData, selectedLeadIds]);

  // --- CSV upload handler ---
  const handleCsvUpload = useCallback(
    async (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      // Reset the input so selecting the same file again still fires onChange
      e.target.value = '';
      if (!file) return;
      setCsvError(null);

      if (!attestationChecked) {
        setCsvError(
          'Please check the staff consent attestation above before uploading.',
        );
        return;
      }

      if (file.size > CSV_MAX_SIZE_MB * 1024 * 1024) {
        setCsvError(`File exceeds ${CSV_MAX_SIZE_MB} MB limit.`);
        return;
      }

      csvUploadMutation.mutate(
        {
          file,
          attestation: {
            staff_attestation_confirmed: attestationChecked,
            attestation_text_shown: ATTESTATION_TEXT,
            attestation_version: ATTESTATION_VERSION,
          },
        },
        {
          onSuccess: (result) => setCsvResult(result),
          onError: (err) => {
            // Prefer the backend's FastAPI `detail` field over the generic
            // axios "Request failed with status code 400" message.
            if (axios.isAxiosError(err)) {
              const detail = err.response?.data?.detail;
              if (typeof detail === 'string') {
                setCsvError(detail);
                return;
              }
              if (Array.isArray(detail) && detail[0]?.msg) {
                setCsvError(String(detail[0].msg));
                return;
              }
            }
            setCsvError(
              err instanceof Error ? err.message : 'CSV upload failed',
            );
          },
        },
      );
    },
    [attestationChecked, csvUploadMutation],
  );

  // --- Page-level customer all-selected check ---
  const customerPageIds = useMemo(
    () => customersData?.items.map((c) => c.id) ?? [],
    [customersData],
  );
  const allCustomersOnPageSelected =
    customerPageIds.length > 0 &&
    customerPageIds.every((id) => selectedCustomerIds.includes(id));

  const leadPageIds = useMemo(
    () => leadsData?.items.map((l) => l.id) ?? [],
    [leadsData],
  );
  const allLeadsOnPageSelected =
    leadPageIds.length > 0 &&
    leadPageIds.every((id) => selectedLeadIds.includes(id));

  return (
    <div data-testid="audience-builder" className="space-y-4">
      {/* Running total */}
      <div className="flex items-center justify-between rounded-lg bg-slate-50 px-4 py-3 border border-slate-200">
        <div className="text-sm text-slate-700" data-testid="audience-total">
          <span className="font-semibold">{selectedCustomerIds.length}</span> customers
          {' + '}
          <span className="font-semibold">{selectedLeadIds.length}</span> leads
          {' + '}
          <span className="font-semibold">
            {csvResult
              ? csvResult.total_rows - csvResult.rejected - csvResult.duplicates_collapsed
              : 0}
          </span>{' '}
          ad-hoc
          {' = '}
          <span className="font-bold text-teal-700">{totalSelected} total</span>
          {effectivePreview && (
            <span className="text-slate-500">
              {' '}
              ({effectivePreview.total} after consent filter)
            </span>
          )}
        </div>
      </div>

      {/* Dedupe warning */}
      {dedupeCount > 0 && (
        <Alert data-testid="dedupe-warning">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>
            {dedupeCount} phone{dedupeCount > 1 ? 's are' : ' is'} in multiple
            sources — they&apos;ll only be texted once.
          </AlertDescription>
        </Alert>
      )}

      {/* Source panel tabs */}
      <div className="flex gap-2 border-b border-slate-200 pb-2">
        {([
          { key: 'customers' as const, icon: Users, label: 'Customers', count: selectedCustomerIds.length },
          { key: 'leads' as const, icon: UserPlus, label: 'Leads', count: selectedLeadIds.length },
          { key: 'adhoc' as const, icon: FileSpreadsheet, label: 'Ad-hoc CSV', count: csvResult ? csvResult.total_rows - csvResult.rejected - csvResult.duplicates_collapsed : 0 },
        ]).map(({ key, icon: Icon, label, count }) => (
          <Button
            key={key}
            variant={activePanel === key ? 'default' : 'outline'}
            size="sm"
            onClick={() => setActivePanel(key)}
            data-testid={`panel-${key}`}
            className="gap-2"
          >
            <Icon className="h-4 w-4" />
            {label}
            {count > 0 && (
              <Badge variant="secondary" className="ml-1 text-xs">
                {count}
              </Badge>
            )}
          </Button>
        ))}
      </div>

      {/* --- Customers Panel --- */}
      {activePanel === 'customers' && (
        <div data-testid="customers-panel" className="space-y-3">
          {/* Filters */}
          <div className="flex gap-3 items-center">
            <div className="relative flex-1 max-w-sm">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
              <Input
                placeholder="Search customers..."
                value={customerSearch}
                onChange={(e) => {
                  setCustomerSearch(e.target.value);
                  setCustomerParams((p) => ({ ...p, page: 1 }));
                }}
                className="pl-9"
                data-testid="customer-search-input"
              />
            </div>
            <div className="flex items-center gap-2">
              <Checkbox
                id="customer-sms-filter"
                checked={customerSmsFilter}
                onCheckedChange={(v) => setCustomerSmsFilter(!!v)}
                data-testid="customer-sms-filter"
              />
              <Label htmlFor="customer-sms-filter" className="text-sm">
                SMS opt-in only
              </Label>
            </div>
            <Input
              placeholder="City filter..."
              value={customerCityFilter}
              onChange={(e) => setCustomerCityFilter(e.target.value)}
              className="max-w-[160px]"
              data-testid="customer-city-filter"
            />
          </div>

          {/* Table */}
          <div className="rounded-lg border border-slate-200 overflow-hidden">
            <Table data-testid="customer-select-table">
              <TableHeader>
                <TableRow className="bg-slate-50/50">
                  <TableHead className="w-10 px-4">
                    <Checkbox
                      checked={allCustomersOnPageSelected}
                      onCheckedChange={toggleAllCustomers}
                      aria-label="Select all customers on page"
                      data-testid="select-all-customers"
                    />
                  </TableHead>
                  <TableHead className="text-xs uppercase text-slate-500">Name</TableHead>
                  <TableHead className="text-xs uppercase text-slate-500">Phone</TableHead>
                  <TableHead className="text-xs uppercase text-slate-500">SMS</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {customersLoading ? (
                  <TableRow>
                    <TableCell colSpan={4} className="text-center py-8 text-slate-400">
                      Loading...
                    </TableCell>
                  </TableRow>
                ) : customersData?.items.length ? (
                  customersData.items.map((c) => (
                    <TableRow
                      key={c.id}
                      className="hover:bg-slate-50/80 cursor-pointer"
                      onClick={() => toggleCustomer(c.id)}
                      data-testid={`customer-row-${c.id}`}
                    >
                      <TableCell className="px-4">
                        <Checkbox
                          checked={selectedCustomerIds.includes(c.id)}
                          onCheckedChange={() => toggleCustomer(c.id)}
                          onClick={(e) => e.stopPropagation()}
                        />
                      </TableCell>
                      <TableCell className="text-sm font-medium text-slate-700">
                        {c.first_name} {c.last_name}
                      </TableCell>
                      <TableCell className="text-sm text-slate-600">{c.phone}</TableCell>
                      <TableCell>
                        <Badge variant={c.sms_opt_in ? 'default' : 'secondary'} className="text-xs">
                          {c.sms_opt_in ? 'Yes' : 'No'}
                        </Badge>
                      </TableCell>
                    </TableRow>
                  ))
                ) : (
                  <TableRow>
                    <TableCell colSpan={4} className="text-center py-8 text-slate-400">
                      No customers found.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </div>

          {/* Pagination */}
          {customersData && customersData.total > 0 && (
            <div className="flex items-center justify-between text-sm text-slate-500">
              <span>
                {selectedCustomerIds.length} selected of {customersData.total} total
              </span>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={customerParams.page === 1}
                  onClick={() => setCustomerParams((p) => ({ ...p, page: (p.page ?? 1) - 1 }))}
                >
                  Previous
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={customerParams.page === customersData.total_pages}
                  onClick={() => setCustomerParams((p) => ({ ...p, page: (p.page ?? 1) + 1 }))}
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* --- Leads Panel --- */}
      {activePanel === 'leads' && (
        <div data-testid="leads-panel" className="space-y-3">
          {/* Filters */}
          <div className="flex gap-3 items-center">
            <div className="relative flex-1 max-w-sm">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
              <Input
                placeholder="Search leads..."
                value={leadSearch}
                onChange={(e) => {
                  setLeadSearch(e.target.value);
                  setLeadParams((p) => ({ ...p, page: 1 }));
                }}
                className="pl-9"
                data-testid="lead-search-input"
              />
            </div>
            <div className="flex items-center gap-2">
              <Checkbox
                id="lead-sms-filter"
                checked={leadSmsFilter}
                onCheckedChange={(v) => setLeadSmsFilter(!!v)}
                data-testid="lead-sms-filter"
              />
              <Label htmlFor="lead-sms-filter" className="text-sm">
                SMS consent only
              </Label>
            </div>
            <Select
              value={leadSourceFilter || ALL_SOURCES_VALUE}
              onValueChange={(v) =>
                setLeadSourceFilter(v === ALL_SOURCES_VALUE ? '' : v)
              }
            >
              <SelectTrigger className="w-[160px]" data-testid="lead-source-filter">
                <SelectValue placeholder="All sources" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={ALL_SOURCES_VALUE}>All sources</SelectItem>
                <SelectItem value="website">Website</SelectItem>
                <SelectItem value="google_form">Google Form</SelectItem>
                <SelectItem value="phone_call">Phone Call</SelectItem>
                <SelectItem value="referral">Referral</SelectItem>
                <SelectItem value="google_ad">Google Ad</SelectItem>
                <SelectItem value="social_media">Social Media</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Table */}
          <div className="rounded-lg border border-slate-200 overflow-hidden">
            <Table data-testid="lead-select-table">
              <TableHeader>
                <TableRow className="bg-slate-50/50">
                  <TableHead className="w-10 px-4">
                    <Checkbox
                      checked={allLeadsOnPageSelected}
                      onCheckedChange={toggleAllLeads}
                      aria-label="Select all leads on page"
                      data-testid="select-all-leads"
                    />
                  </TableHead>
                  <TableHead className="text-xs uppercase text-slate-500">Name</TableHead>
                  <TableHead className="text-xs uppercase text-slate-500">Phone</TableHead>
                  <TableHead className="text-xs uppercase text-slate-500">City</TableHead>
                  <TableHead className="text-xs uppercase text-slate-500">SMS</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {leadsLoading ? (
                  <TableRow>
                    <TableCell colSpan={5} className="text-center py-8 text-slate-400">
                      Loading...
                    </TableCell>
                  </TableRow>
                ) : leadsData?.items.length ? (
                  leadsData.items.map((l) => (
                    <TableRow
                      key={l.id}
                      className="hover:bg-slate-50/80 cursor-pointer"
                      onClick={() => toggleLead(l.id)}
                      data-testid={`lead-row-${l.id}`}
                    >
                      <TableCell className="px-4">
                        <Checkbox
                          checked={selectedLeadIds.includes(l.id)}
                          onCheckedChange={() => toggleLead(l.id)}
                          onClick={(e) => e.stopPropagation()}
                        />
                      </TableCell>
                      <TableCell className="text-sm font-medium text-slate-700">
                        {l.name}
                      </TableCell>
                      <TableCell className="text-sm text-slate-600">{l.phone}</TableCell>
                      <TableCell className="text-sm text-slate-600">{l.city ?? '—'}</TableCell>
                      <TableCell>
                        <Badge variant={l.sms_consent ? 'default' : 'secondary'} className="text-xs">
                          {l.sms_consent ? 'Yes' : 'No'}
                        </Badge>
                      </TableCell>
                    </TableRow>
                  ))
                ) : (
                  <TableRow>
                    <TableCell colSpan={5} className="text-center py-8 text-slate-400">
                      No leads found.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </div>

          {/* Pagination */}
          {leadsData && leadsData.total > 0 && (
            <div className="flex items-center justify-between text-sm text-slate-500">
              <span>
                {selectedLeadIds.length} selected of {leadsData.total} total
              </span>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={leadParams.page === 1}
                  onClick={() => setLeadParams((p) => ({ ...p, page: (p.page ?? 1) - 1 }))}
                >
                  Previous
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={leadParams.page === leadsData.total_pages}
                  onClick={() => setLeadParams((p) => ({ ...p, page: (p.page ?? 1) + 1 }))}
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* --- Ad-hoc CSV Panel --- */}
      {activePanel === 'adhoc' && (
        <div data-testid="adhoc-panel" className="space-y-4">
          {/* Staff attestation — must be checked BEFORE upload */}
          <div
            className="rounded-lg border border-amber-200 bg-amber-50 p-4 space-y-3"
            data-testid="attestation-block"
          >
            <p className="text-sm font-medium text-amber-800">
              Staff Consent Attestation (Required before upload)
            </p>
            <p className="text-xs text-amber-700">{ATTESTATION_TEXT}</p>
            <div className="flex items-center gap-2">
              <Checkbox
                id="attestation"
                checked={attestationChecked}
                onCheckedChange={(v) => setAttestationChecked(!!v)}
                data-testid="attestation-checkbox"
              />
              <Label htmlFor="attestation" className="text-sm text-amber-800">
                I confirm the above
              </Label>
            </div>
          </div>

          {/* Upload area */}
          <div className="rounded-lg border-2 border-dashed border-slate-300 p-6 text-center">
            <Upload className="mx-auto h-8 w-8 text-slate-400 mb-2" />
            <p className="text-sm text-slate-600 mb-1">
              Upload a CSV with <code className="text-xs bg-slate-100 px-1 rounded">phone</code> column
              (optional: <code className="text-xs bg-slate-100 px-1 rounded">first_name</code>,{' '}
              <code className="text-xs bg-slate-100 px-1 rounded">last_name</code>)
            </p>
            <p className="text-xs text-slate-400 mb-3">
              Max {CSV_MAX_SIZE_MB} MB, {CSV_MAX_ROWS.toLocaleString()} rows
            </p>
            <input
              ref={fileInputRef}
              type="file"
              accept=".csv"
              onChange={handleCsvUpload}
              className="hidden"
              data-testid="csv-file-input"
            />
            <Button
              variant="outline"
              size="sm"
              onClick={() => fileInputRef.current?.click()}
              disabled={csvUploadMutation.isPending || !attestationChecked}
              data-testid="csv-upload-btn"
            >
              {csvUploadMutation.isPending ? 'Uploading...' : 'Choose CSV'}
            </Button>
            {!attestationChecked && (
              <p className="text-xs text-amber-700 mt-2">
                Check the staff attestation above to enable upload.
              </p>
            )}
          </div>

          {csvError && (
            <Alert variant="destructive" data-testid="csv-error">
              <AlertDescription>{csvError}</AlertDescription>
            </Alert>
          )}

          {/* CSV result breakdown */}
          {csvResult && (
            <div
              className="rounded-lg border border-slate-200 p-4 space-y-2"
              data-testid="csv-result"
            >
              <p className="text-sm font-medium text-slate-700">
                Upload results: {csvResult.total_rows} rows processed
              </p>
              <div className="grid grid-cols-2 gap-2 text-sm text-slate-600">
                <span>Matched to customers: {csvResult.matched_customers}</span>
                <span>Matched to leads: {csvResult.matched_leads}</span>
                <span>Will become ghost leads: {csvResult.will_become_ghost_leads}</span>
                <span>Rejected: {csvResult.rejected}</span>
                {csvResult.duplicates_collapsed > 0 && (
                  <span className="col-span-2 text-amber-600">
                    {csvResult.duplicates_collapsed} duplicate phones collapsed
                  </span>
                )}
              </div>

              {csvResult.rejected_rows.length > 0 && (
                <details className="text-xs text-slate-500">
                  <summary className="cursor-pointer">
                    Show {csvResult.rejected_rows.length} rejected rows
                  </summary>
                  <ul className="mt-1 space-y-0.5 max-h-32 overflow-y-auto">
                    {csvResult.rejected_rows.map((r) => (
                      <li key={r.row_number}>
                        Row {r.row_number}: {r.phone_raw} — {r.reason}
                      </li>
                    ))}
                  </ul>
                </details>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
