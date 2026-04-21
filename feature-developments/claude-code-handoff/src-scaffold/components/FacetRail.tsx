/**
 * SCAFFOLD — FacetRail
 *
 * Drop into: frontend/src/features/schedule/components/FacetRail.tsx
 *
 * Renders the 5 facet groups (City, Tags, Job type, Priority, Requested week).
 * Implements the "relaxed count" rule from SPEC §6.1 — counts reflect what
 * would match if THIS group's filter were removed (other filters stay).
 */

import { useMemo } from 'react';
import { Checkbox } from '@/components/ui/checkbox';
import type { JobReadyToSchedule, FacetState } from '../types/pick-jobs';
import { initialFacets } from '../types/pick-jobs';

interface Props {
  jobs:    JobReadyToSchedule[];
  facets:  FacetState;
  onChange: (next: FacetState) => void;
  onClearAll: () => void;
}

type FacetKey = keyof FacetState;

export function FacetRail({ jobs, facets, onChange, onClearAll }: Props) {
  const anyActive = Object.values(facets).some(s => (s as Set<unknown>).size > 0);

  // Distinct values per group, sorted. TODO: memoize per jobs.
  const groups = useMemo(() => {
    const cities   = new Set<string>();
    const tags     = new Set<string>();
    const types    = new Set<string>();
    const priors   = new Set<string>();
    const weeks    = new Set<string>();
    for (const j of jobs) {
      if (j.city)           cities.add(j.city);
      (j.tags ?? []).forEach(t => tags.add(t.toLowerCase()));
      if (j.job_type)       types.add(j.job_type);
      if (j.priority)       priors.add(j.priority);
      if (j.requested_week) weeks.add(j.requested_week);
    }
    return {
      city:          [...cities].sort(),
      tags:          [...tags].sort(),
      jobType:       [...types].sort(),
      priority:      [...priors].sort(),
      requestedWeek: [...weeks].sort(),
    };
  }, [jobs]);

  // Relaxed count: matches if the given facet group were empty.
  // TODO: if performance matters, precompute once per facets change.
  function relaxedCount(group: FacetKey, value: string): number {
    const relaxed: FacetState = { ...facets, [group]: new Set() };
    return jobs.filter(j => matches(j, relaxed) && matchesValue(j, group, value)).length;
  }

  function toggle(group: FacetKey, value: string) {
    const next = { ...facets, [group]: new Set(facets[group] as Set<string>) } as FacetState;
    const s = next[group] as Set<string>;
    if (s.has(value)) s.delete(value); else s.add(value);
    onChange(next);
  }

  function clearGroup(group: FacetKey) {
    onChange({ ...facets, [group]: new Set() } as FacetState);
  }

  return (
    <nav className="space-y-6 pb-6 text-sm">
      {anyActive && (
        <button
          type="button"
          onClick={onClearAll}
          className="text-xs text-teal-600 hover:text-teal-700"
        >
          Clear all filters
        </button>
      )}

      <Group
        title="City"
        testId="facet-group-city"
        items={groups.city}
        selected={facets.city}
        countOf={v => relaxedCount('city', v)}
        onToggle={v => toggle('city', v)}
        onClear={() => clearGroup('city')}
      />
      <Group
        title="Tags"
        testId="facet-group-tags"
        items={groups.tags}
        selected={facets.tags}
        countOf={v => relaxedCount('tags', v)}
        onToggle={v => toggle('tags', v)}
        onClear={() => clearGroup('tags')}
      />
      <Group
        title="Job type"
        testId="facet-group-job-type"
        items={groups.jobType}
        selected={facets.jobType}
        countOf={v => relaxedCount('jobType', v)}
        onToggle={v => toggle('jobType', v)}
        onClear={() => clearGroup('jobType')}
      />
      <Group
        title="Priority"
        testId="facet-group-priority"
        items={groups.priority}
        selected={facets.priority as Set<string>}
        countOf={v => relaxedCount('priority', v)}
        onToggle={v => toggle('priority', v)}
        onClear={() => clearGroup('priority')}
      />
      <Group
        title="Requested week"
        testId="facet-group-week"
        items={groups.requestedWeek}
        selected={facets.requestedWeek}
        countOf={v => relaxedCount('requestedWeek', v)}
        onToggle={v => toggle('requestedWeek', v)}
        onClear={() => clearGroup('requestedWeek')}
        formatLabel={v => formatWeekLabel(v)}
      />
    </nav>
  );
}

// ─── helpers ───

function matches(job: JobReadyToSchedule, f: FacetState): boolean {
  if (f.city.size          && !f.city.has(job.city))                              return false;
  if (f.jobType.size       && !f.jobType.has(job.job_type))                       return false;
  if (f.priority.size      && !f.priority.has(job.priority as 'high' | 'normal')) return false;
  if (f.requestedWeek.size && !f.requestedWeek.has(job.requested_week ?? ''))     return false;
  if (f.tags.size) {
    const jobTags = new Set((job.tags ?? []).map(t => t.toLowerCase()));
    let any = false;
    for (const t of f.tags) if (jobTags.has(t)) { any = true; break; }
    if (!any) return false;
  }
  return true;
}

function matchesValue(j: JobReadyToSchedule, group: FacetKey, value: string): boolean {
  switch (group) {
    case 'city':          return j.city === value;
    case 'jobType':       return j.job_type === value;
    case 'priority':      return j.priority === value;
    case 'requestedWeek': return j.requested_week === value;
    case 'tags':          return (j.tags ?? []).map(t => t.toLowerCase()).includes(value);
  }
}

function formatWeekLabel(iso: string): string {
  const d = new Date(iso);
  return `Wk of ${d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}`;
}

interface GroupProps {
  title: string;
  testId: string;
  items: string[];
  selected: Set<string>;
  countOf: (value: string) => number;
  onToggle: (value: string) => void;
  onClear: () => void;
  formatLabel?: (value: string) => string;
}

function Group({ title, testId, items, selected, countOf, onToggle, onClear, formatLabel }: GroupProps) {
  if (items.length === 0) return null;
  return (
    <fieldset data-testid={testId} className="space-y-2">
      <div className="flex items-center justify-between">
        <legend className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">{title}</legend>
        {selected.size > 0 && (
          <button type="button" onClick={onClear} className="text-[10px] text-teal-600 hover:text-teal-700">
            Clear
          </button>
        )}
      </div>
      <ul className="space-y-1.5">
        {items.map(v => {
          const count = countOf(v);
          const dim = count === 0;
          return (
            <li key={v}>
              <label
                data-testid={`facet-value-${testId}-${v}`}
                className={`flex items-center justify-between gap-2 text-sm cursor-pointer ${dim ? 'text-slate-400' : 'text-foreground'}`}
              >
                <span className="flex items-center gap-2">
                  <Checkbox checked={selected.has(v)} onCheckedChange={() => onToggle(v)} />
                  <span>{formatLabel ? formatLabel(v) : v}</span>
                </span>
                <span className="text-xs text-muted-foreground tabular-nums">{count}</span>
              </label>
            </li>
          );
        })}
      </ul>
    </fieldset>
  );
}
