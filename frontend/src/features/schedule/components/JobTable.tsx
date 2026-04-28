/**
 * JobTable — full-page job picker table component (CSS grid + ARIA grid).
 * Requirements: 4.1–4.10, 5.1–5.5, 6.1–6.2, 15.3, 15.4
 */

import { RefObject } from 'react';
import { Search, StickyNote, ArrowUp, ArrowDown } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Input } from '@/components/ui/input';
import { Checkbox } from '@/components/ui/checkbox';
import { Button } from '@/components/ui/button';
import { PropertyTags } from '@/shared/components/PropertyTags';
import type { JobReadyToSchedule, SortKey, SortDir } from '../types/pick-jobs';
import { getJobTypeColorClass } from '../utils/job-type-colors';
import { getCustomerTagStyle } from '../utils/customer-tag-colors';

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
    if (sortKey !== key) { onSort(key, 'asc'); return; }
    if (sortDir === 'asc') { onSort(key, 'desc'); return; }
    onSort('priority', 'desc');
  }

  return (
    <div data-testid="job-table">
      {/* Search toolbar */}
      <div className="pjp-toolbar">
        <div className="relative">
          <Search
            className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 pointer-events-none"
            style={{ color: 'var(--pjp-ink4)' }}
          />
          <Input
            ref={searchRef}
            value={search}
            onChange={e => onSearchChange(e.target.value)}
            placeholder="Search customer, address, phone, job type…"
            className="pl-10"
            data-testid="job-search"
            onKeyDown={e => { if (e.key === 'Escape') onSearchChange(''); }}
          />
        </div>
        <span className="pjp-count-row">
          <b>{jobs.length}</b> job{jobs.length !== 1 ? 's' : ''}
        </span>
      </div>

      {/* Table card */}
      <div role="grid" className="pjp-table-card">
        {/* Header row */}
        <div role="row" className="pjp-table-head-row">
          <div role="columnheader" className="pjp-th">
            <Checkbox
              checked={allVisibleSelected ? true : someVisibleSelected ? 'indeterminate' : false}
              onCheckedChange={onToggleAllVisible}
              aria-label="Select all visible jobs"
              data-testid="job-table-select-all"
            />
          </div>
          <SortHeader label="Customer" k="customer" sortKey={sortKey} sortDir={sortDir} onClick={handleSort} />
          <div role="columnheader" className="pjp-th">Job type</div>
          <div role="columnheader" className="pjp-th">Tags</div>
          <SortHeader label="City" k="city" sortKey={sortKey} sortDir={sortDir} onClick={handleSort} />
          <SortHeader label="Requested" k="requested_week" sortKey={sortKey} sortDir={sortDir} onClick={handleSort} />
          <SortHeader label="Priority" k="priority" sortKey={sortKey} sortDir={sortDir} onClick={handleSort} className="pjp-th-num" />
          <SortHeader label="Dur." k="duration" sortKey={sortKey} sortDir={sortDir} onClick={handleSort} className="pjp-th-num" />
          <div role="columnheader" className="pjp-th">Equipment</div>
        </div>

        {jobs.length === 0 ? (
          <div className="pjp-table-empty">
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
          jobs.map(job => {
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
          })
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
  const jobTypeColor = getJobTypeColorClass(job.job_type);

  return (
    <>
      <div
        role="row"
        data-testid={`job-row-${job.job_id}`}
        onClick={() => onToggle(job.job_id)}
        className={`pjp-row${selected ? ' selected' : ''}`}
      >
        <div role="gridcell" className="pjp-cell">
          <Checkbox
            checked={selected}
            onCheckedChange={() => onToggle(job.job_id)}
            data-testid={`job-row-checkbox-${job.job_id}`}
            onClick={e => e.stopPropagation()}
          />
        </div>
        <div role="gridcell" className="pjp-cell pjp-cell-cust">
          <div className="pjp-name">{job.customer_name}</div>
          {job.address && <div className="pjp-addr">{job.address}</div>}
        </div>
        <div role="gridcell" className="pjp-cell">
          <span className={`pjp-pill ${jobTypeColor}`}>{job.job_type}</span>
        </div>
        <div role="gridcell" className="pjp-cell">
          <div className="pjp-tags">
            {(job.customer_tags ?? []).map(tag => {
              const style = getCustomerTagStyle(tag);
              return (
                <span key={tag} className={`pjp-tag ${style.variant}`}>
                  {style.label}
                </span>
              );
            })}
            <span className="pjp-tag-host">
              <PropertyTags
                propertyType={job.property_type}
                isHoa={job.property_is_hoa}
                isSubscription={job.property_is_subscription}
              />
            </span>
          </div>
        </div>
        <div role="gridcell" className="pjp-cell pjp-cell-city">{job.city}</div>
        <div role="gridcell" className="pjp-cell pjp-cell-req">{formatWeek(job.requested_week)}</div>
        <div role="gridcell" className="pjp-cell pjp-th-num">
          {priorityLevel >= 1
            ? <span className="pjp-prio high" aria-label="High priority" />
            : <span style={{ color: 'var(--pjp-ink4)' }}>—</span>}
        </div>
        <div role="gridcell" className="pjp-cell pjp-th-num pjp-dur">
          {job.estimated_duration_minutes ? `${job.estimated_duration_minutes}m` : '—'}
        </div>
        <div role="gridcell" className="pjp-cell pjp-equip">
          {job.requires_equipment?.length ? job.requires_equipment.join(', ') : '—'}
        </div>
      </div>
      {job.notes && (
        <div role="row" className="pjp-note-row" data-testid={`job-note-${job.job_id}`}>
          <span className="pjp-note-icon" aria-hidden="true">
            <StickyNote className="h-4 w-4" />
          </span>
          <div role="gridcell" className="pjp-note-body">
            {job.notes}
          </div>
        </div>
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
    <div role="columnheader" aria-sort={ariaSort} className={`pjp-th ${className ?? ''}`}>
      <button
        type="button"
        onClick={() => onClick(k)}
        className="pjp-th-btn"
      >
        {label}
        {active && (sortDir === 'asc' ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />)}
      </button>
    </div>
  );
}

function formatWeek(iso?: string | null): string {
  if (!iso) return '—';
  const d = new Date(iso);
  return `Wk of ${d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}`;
}
