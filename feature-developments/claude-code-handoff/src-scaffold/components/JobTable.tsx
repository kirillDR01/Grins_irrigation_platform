/**
 * SCAFFOLD — JobTable
 *
 * Drop into: frontend/src/features/schedule/components/JobTable.tsx
 * See SPEC §6.2 for full column + interaction rules.
 */

import { RefObject } from 'react';
import { Search, StickyNote, Star, ArrowUp, ArrowDown } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Checkbox } from '@/components/ui/checkbox';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import type { JobReadyToSchedule, SortKey, SortDir } from '../types/pick-jobs';

const TAG_COLORS: Record<string, string> = {
  vip:           'bg-amber-50 text-amber-700 border-amber-200',
  commercial:    'bg-blue-50 text-blue-700 border-blue-200',
  hoa:           'bg-purple-50 text-purple-700 border-purple-200',
  prepaid:       'bg-teal-50 text-teal-700 border-teal-200',
  'needs-ladder':'bg-slate-100 text-slate-700 border-slate-300',
  'dog-on-site': 'bg-red-50 text-red-700 border-red-200',
  gated:         'bg-orange-50 text-orange-700 border-orange-200',
};

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
    // 3-state: asc → desc → default(SPEC §6.2.2)
    if (sortKey !== key) { onSort(key, 'asc'); return; }
    if (sortDir === 'asc') onSort(key, 'desc');
    else onSort('priority', 'desc'); // revert to default
  }

  return (
    <div className="flex flex-col gap-3 flex-1 min-h-0" data-testid="job-table">
      {/* Toolbar */}
      <div className="flex items-center gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
          <Input
            ref={searchRef}
            value={search}
            onChange={e => onSearchChange(e.target.value)}
            placeholder="Search customer, address, phone, job type…"
            className="pl-9"
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
                <Button variant="link" className="mt-1" onClick={onClearAllFilters}>Clear all filters</Button>
              </>
            ) : (
              <p>All jobs are scheduled. Nice work.</p>
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
                <SortHeader label="Customer" k="customer" {...{sortKey, sortDir, onClick: handleSort}} className="w-[220px]" />
                <th className="w-[180px] p-2">Job type</th>
                <th className="w-[160px] p-2">Tags</th>
                <SortHeader label="City" k="city" {...{sortKey, sortDir, onClick: handleSort}} className="w-[120px]" />
                <SortHeader label="Requested" k="requested_week" {...{sortKey, sortDir, onClick: handleSort}} className="w-[120px]" />
                <SortHeader label="Priority" k="priority" {...{sortKey, sortDir, onClick: handleSort}} className="w-[80px] text-right" />
                <SortHeader label="Dur." k="duration" {...{sortKey, sortDir, onClick: handleSort}} className="w-[80px] text-right" />
                <th className="w-[140px] p-2">Equipment</th>
              </tr>
            </thead>
            <tbody>
              {jobs.map(job => {
                const selected = selectedJobIds.has(job.job_id);
                return (
                  <>
                    <tr
                      key={job.job_id}
                      data-testid={`job-row-${job.job_id}`}
                      onClick={() => onToggleJob(job.job_id)}
                      className={`border-t border-slate-100 cursor-pointer ${selected ? 'bg-teal-50 hover:bg-teal-50' : 'hover:bg-slate-50'}`}
                    >
                      <td className="p-2">
                        <Checkbox
                          checked={selected}
                          onCheckedChange={() => onToggleJob(job.job_id)}
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
                          {(job.tags ?? []).map(t => {
                            const key = t.toLowerCase();
                            const cls = TAG_COLORS[key] ?? 'bg-slate-100 text-slate-700 border-slate-300';
                            return <Badge key={key} variant="outline" className={`text-[10px] ${cls}`}>{t.toUpperCase()}</Badge>;
                          })}
                        </div>
                      </td>
                      <td className="p-2 text-muted-foreground">{job.city}</td>
                      <td className="p-2 text-muted-foreground">{formatWeek(job.requested_week)}</td>
                      <td className="p-2 text-right">
                        {job.priority === 'high'
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
                      <tr className="bg-amber-50/40 border-t border-amber-100">
                        <td></td>
                        <td colSpan={8} className="p-2 text-xs text-amber-900 italic">
                          <StickyNote className="inline h-3 w-3 mr-1" /> {job.notes}
                        </td>
                      </tr>
                    )}
                  </>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

function SortHeader({
  label, k, sortKey, sortDir, onClick, className,
}: { label: string; k: SortKey; sortKey: SortKey; sortDir: SortDir; onClick: (k: SortKey) => void; className?: string }) {
  const active = sortKey === k;
  const ariaSort = active ? (sortDir === 'asc' ? 'ascending' : 'descending') : 'none';
  return (
    <th aria-sort={ariaSort} className={`p-2 ${className ?? ''}`}>
      <button type="button" onClick={() => onClick(k)} className="inline-flex items-center gap-1 text-xs font-medium uppercase tracking-wide">
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
