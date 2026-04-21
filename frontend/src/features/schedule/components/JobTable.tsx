/**
 * JobTable — full-page job picker table component.
 * Requirements: 4.1–4.10, 5.1–5.5, 6.1–6.2, 15.3, 15.4
 */

import { RefObject } from 'react';
import { Search, StickyNote, Star, ArrowUp, ArrowDown } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Input } from '@/components/ui/input';
import { Checkbox } from '@/components/ui/checkbox';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { PropertyTags } from '@/shared/components/PropertyTags';
import { CUSTOMER_TAG_CONFIG } from '@/features/jobs/types';
import type { CustomerTag } from '@/features/jobs/types';
import type { JobReadyToSchedule, SortKey, SortDir } from '../types/pick-jobs';

interface Props {
  jobs: JobReadyToSchedule[];
  searchRef: RefObject<HTMLInputElement>;
  search: string;
  onSearchChange: (s: string) => void;
  selectedJobIds: Set<string>;
  onToggleJob: (id: string) => void;
  onToggleAllVisible: () => void;
  sortKey: SortKey;
  sortDir: SortDir;
  onSort: (key: SortKey, dir: SortDir) => void;
  anyFilterActive: boolean;
  onClearAllFilters: () => void;
}

export function JobTable({
  jobs, searchRef, search, onSearchChange,
  selectedJobIds, onToggleJob, onToggleAllVisible,
  sortKey, sortDir, onSort,
  anyFilterActive, onClearAllFilters,
}: Props) {
  const allVisibleSelected = jobs.length > 0 && jobs.every(j => selectedJobIds.has(j.job_id));
  const someVisibleSelected = jobs.some(j => selectedJobIds.has(j.job_id)) && !allVisibleSelected;

  function handleSort(key: SortKey) {
    // 3-state: asc → desc → default (priority desc)
    if (sortKey !== key) { onSort(key, 'asc'); return; }
    if (sortDir === 'asc') { onSort(key, 'desc'); return; }
    // third click: revert to default
    onSort('priority', 'desc');
  }

  return (
    <div className="flex flex-col gap-3 flex-1 min-h-0" data-testid="job-table">
      {/* Search toolbar */}
      <div className="flex items-center gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
          <Input
            ref={searchRef}
            value={search}
            onChange={e => onSearchChange(e.target.value)}
            placeholder="Search customer, address, phone, job type…"
            className="pl-9 rounded-lg"
            data-testid="job-search"
            onKeyDown={e => { if (e.key === 'Escape') onSearchChange(''); }}
          />
        </div>
        <span className="text-xs text-muted-foreground tabular-nums">
          {jobs.length} job{jobs.length !== 1 ? 's' : ''}
        </span>
      </div>

      {/* Table scroller */}
      <div className="flex-1 min-h-0 overflow-y-auto rounded-xl border border-border bg-card">
        {jobs.length === 0 ? (
          <div className="p-12 text-center text-sm text-muted-foreground">
            {anyFilterActive ? (
              <>
                <p>No jobs match these filters.</p>
                <Button variant="link" className="mt-1" onClick={onClearAllFilters}>
                  Clear all filters
                </Button>
              </>
            ) : (
              <p>
                All jobs are scheduled. Nice work.{' '}
                <Link to="/schedule" className="underline text-primary">Back to schedule</Link>
              </p>
            )}
          </div>
        ) : (
          <table className="w-full text-sm border-separate border-spacing-0">
            <thead className="sticky top-0 bg-slate-50 z-10">
              <tr className="text-left text-xs font-medium text-muted-foreground uppercase tracking-wide">
                <th className="w-10 p-2">
                  <Checkbox
                    checked={allVisibleSelected ? true : someVisibleSelected ? 'indeterminate' : false}
                    onCheckedChange={onToggleAllVisible}
                    aria-label="Select all visible jobs"
                    data-testid="job-table-select-all"
                  />
                </th>
                <SortHeader label="Customer" k="customer" sortKey={sortKey} sortDir={sortDir} onClick={handleSort} className="w-[220px]" />
                <th className="w-[180px] p-2">Job type</th>
                <th className="w-[160px] p-2">Tags</th>
                <SortHeader label="City" k="city" sortKey={sortKey} sortDir={sortDir} onClick={handleSort} className="w-[120px]" />
                <SortHeader label="Requested" k="requested_week" sortKey={sortKey} sortDir={sortDir} onClick={handleSort} className="w-[120px]" />
                <SortHeader label="Priority" k="priority" sortKey={sortKey} sortDir={sortDir} onClick={handleSort} className="w-[80px] text-right" />
                <SortHeader label="Dur." k="duration" sortKey={sortKey} sortDir={sortDir} onClick={handleSort} className="w-[80px] text-right" />
                <th className="w-[140px] p-2">Equipment</th>
              </tr>
            </thead>
            <tbody>
              {jobs.map(job => {
                const selected = selectedJobIds.has(job.job_id);
                const priorityLevel = job.priority_level ?? 0;
                return (
                  <JobRow
                    key={job.job_id}
                    job={job}
                    selected={selected}
                    priorityLevel={priorityLevel}
                    onToggle={onToggleJob}
                  />
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

// ─── Sub-components ───────────────────────────────────────────────────────────

interface JobRowProps {
  job: JobReadyToSchedule;
  selected: boolean;
  priorityLevel: number;
  onToggle: (id: string) => void;
}

function JobRow({ job, selected, priorityLevel, onToggle }: JobRowProps) {
  return (
    <>
      <tr
        data-testid={`job-row-${job.job_id}`}
        onClick={() => onToggle(job.job_id)}
        className={`border-t border-slate-100 cursor-pointer transition-colors ${
          selected ? 'bg-teal-50 hover:bg-teal-50' : 'hover:bg-slate-50'
        }`}
      >
        <td className="p-2">
          <Checkbox
            checked={selected}
            onCheckedChange={() => onToggle(job.job_id)}
            data-testid={`job-row-checkbox-${job.job_id}`}
            onClick={e => e.stopPropagation()}
          />
        </td>
        <td className="p-2">
          <div className="font-medium text-foreground">{job.customer_name}</div>
          {job.address && <div className="text-xs text-slate-500">{job.address}</div>}
        </td>
        <td className="p-2">
          <Badge variant="outline" className="font-mono text-[11px]">{job.job_type}</Badge>
        </td>
        <td className="p-2">
          <div className="flex flex-wrap gap-1">
            {/* Customer tags */}
            {(job.customer_tags ?? []).map(tag => {
              const cfg = CUSTOMER_TAG_CONFIG[tag as CustomerTag];
              if (!cfg) return null;
              return (
                <span
                  key={tag}
                  className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-medium ${cfg.bgColor} ${cfg.color}`}
                >
                  {cfg.label}
                </span>
              );
            })}
            {/* Property tags */}
            <PropertyTags
              propertyType={job.property_type}
              isHoa={job.property_is_hoa}
              isSubscription={job.property_is_subscription}
            />
          </div>
        </td>
        <td className="p-2 text-muted-foreground">{job.city}</td>
        <td className="p-2 text-muted-foreground">{formatWeek(job.requested_week)}</td>
        <td className="p-2 text-right">
          {priorityLevel >= 1
            ? <Star className="inline h-4 w-4 fill-amber-400 text-amber-400" />
            : <span className="text-slate-300">—</span>}
        </td>
        <td className="p-2 text-right text-muted-foreground">
          {job.estimated_duration_minutes ? `${job.estimated_duration_minutes}m` : '—'}
        </td>
        <td className="p-2 text-xs text-muted-foreground">
          {job.requires_equipment?.length ? job.requires_equipment.join(', ') : '—'}
        </td>
      </tr>
      {job.notes && (
        <tr key={`${job.job_id}-notes`} className="bg-amber-50/40 border-t border-amber-100">
          <td />
          <td colSpan={8} className="p-2 text-xs text-amber-900 italic">
            <StickyNote className="inline h-3 w-3 mr-1" />
            {job.notes}
          </td>
        </tr>
      )}
    </>
  );
}

interface SortHeaderProps {
  label: string;
  k: SortKey;
  sortKey: SortKey;
  sortDir: SortDir;
  onClick: (k: SortKey) => void;
  className?: string;
}

function SortHeader({ label, k, sortKey, sortDir, onClick, className }: SortHeaderProps) {
  const active = sortKey === k;
  const ariaSort = active ? (sortDir === 'asc' ? 'ascending' : 'descending') : 'none';
  return (
    <th aria-sort={ariaSort} className={`p-2 ${className ?? ''}`}>
      <button
        type="button"
        onClick={() => onClick(k)}
        className="inline-flex items-center gap-1 text-xs font-medium uppercase tracking-wide"
      >
        {label}
        {active && (sortDir === 'asc' ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />)}
      </button>
    </th>
  );
}

function formatWeek(iso?: string | null): string {
  if (!iso) return '—';
  const d = new Date(iso);
  return `Wk of ${d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}`;
}
