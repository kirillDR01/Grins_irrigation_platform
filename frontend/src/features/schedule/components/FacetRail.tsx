/**
 * FacetRail — five facet groups for the Pick Jobs Scheduler page.
 *
 * Implements the "relaxed count" rule: counts reflect what would match if
 * THIS group's filter were removed (other filters stay).
 *
 * At lg+ (≥1024px): renders inline as the left rail in the new shell.
 * At md (768–1023px): collapses behind a "Filters" Sheet button.
 *
 * Requirements: 2.3, 3.1–3.10, 15.2
 */

import { useMemo, useState } from 'react';
import { SlidersHorizontal } from 'lucide-react';
import { Checkbox } from '@/components/ui/checkbox';
import { Button } from '@/components/ui/button';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from '@/components/ui/sheet';
import type { JobReadyToSchedule } from '../types/index';
import type { FacetState } from '../types/pick-jobs';
import { normalizeCity } from '../utils/city';

interface Props {
  jobs: JobReadyToSchedule[];
  facets: FacetState;
  onChange: (next: FacetState) => void;
  onClearAll: () => void;
}

type FacetKey = keyof FacetState;

const PRIORITY_LABELS: Record<string, string> = {
  '0': 'Normal',
  '1': 'High',
  '2': 'Urgent',
};

export function FacetRail({ jobs, facets, onChange, onClearAll }: Props) {
  const [sheetOpen, setSheetOpen] = useState(false);

  return (
    <>
      {/* md: Sheet trigger — hidden at lg+ */}
      <div className="lg:hidden pjp-rail-mobile-trigger">
        <Sheet open={sheetOpen} onOpenChange={setSheetOpen}>
          <SheetTrigger asChild>
            <Button variant="outline" size="sm" className="gap-2">
              <SlidersHorizontal className="h-4 w-4" />
              Filters
            </Button>
          </SheetTrigger>
          <SheetContent side="left" className="w-[85vw] sm:w-72 overflow-y-auto">
            <SheetHeader>
              <SheetTitle>Filters</SheetTitle>
            </SheetHeader>
            <div className="mt-4">
              <FacetRailContent
                jobs={jobs}
                facets={facets}
                onChange={onChange}
                onClearAll={onClearAll}
                inSheet
              />
            </div>
          </SheetContent>
        </Sheet>
      </div>

      {/* lg+: inline rail — hidden below lg */}
      <div className="hidden lg:block pjp-rail-desktop">
        <FacetRailContent
          jobs={jobs}
          facets={facets}
          onChange={onChange}
          onClearAll={onClearAll}
        />
      </div>
    </>
  );
}

// ─── Inner content (shared between inline and Sheet) ───────────────────────

interface ContentProps extends Props {
  inSheet?: boolean;
}

function FacetRailContent({ jobs, facets, onChange, onClearAll, inSheet }: ContentProps) {
  const anyActive = Object.values(facets).some(s => (s as Set<unknown>).size > 0);

  const groups = useMemo(() => {
    const cities = new Set<string>();
    const tags = new Set<string>();
    const types = new Set<string>();
    const priors = new Set<string>();
    const weeks = new Set<string>();
    for (const j of jobs) {
      const canonCity = normalizeCity(j.city);
      if (canonCity) cities.add(canonCity);
      (j.customer_tags ?? []).forEach(t => tags.add(t));
      if (j.job_type) types.add(j.job_type);
      if (j.priority_level != null) priors.add(String(j.priority_level));
      if (j.requested_week) weeks.add(j.requested_week);
    }
    return {
      city: [...cities].sort(),
      tags: [...tags].sort(),
      jobType: [...types].sort(),
      priority: [...priors].sort(),
      requestedWeek: [...weeks].sort(),
    };
  }, [jobs]);

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
    <nav
      data-testid="facet-rail"
      className={`pjp-rail${inSheet ? ' pjp-rail-in-sheet' : ''}`}
    >
      <div className="pjp-rail-head">
        <div className="pjp-rail-brand">
          <span className="pjp-rail-brand-mark" aria-hidden="true">F</span>
          Filters
        </div>
        {anyActive && (
          <button type="button" className="pjp-rail-clear" onClick={onClearAll}>
            Clear all filters
          </button>
        )}
      </div>

      <Group
        title="City"
        testId="facet-group-city"
        facetKey="city"
        items={groups.city}
        selected={facets.city}
        countOf={v => relaxedCount('city', v)}
        onToggle={v => toggle('city', v)}
        onClear={() => clearGroup('city')}
      />
      <Group
        title="Tags"
        testId="facet-group-tags"
        facetKey="tags"
        items={groups.tags}
        selected={facets.tags}
        countOf={v => relaxedCount('tags', v)}
        onToggle={v => toggle('tags', v)}
        onClear={() => clearGroup('tags')}
      />
      <Group
        title="Job type"
        testId="facet-group-job-type"
        facetKey="jobType"
        items={groups.jobType}
        selected={facets.jobType}
        countOf={v => relaxedCount('jobType', v)}
        onToggle={v => toggle('jobType', v)}
        onClear={() => clearGroup('jobType')}
      />
      <Group
        title="Priority"
        testId="facet-group-priority"
        facetKey="priority"
        items={groups.priority}
        selected={facets.priority as Set<string>}
        countOf={v => relaxedCount('priority', v)}
        onToggle={v => toggle('priority', v)}
        onClear={() => clearGroup('priority')}
        formatLabel={v => PRIORITY_LABELS[v] ?? v}
      />
      <Group
        title="Requested week"
        testId="facet-group-week"
        facetKey="requestedWeek"
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

// ─── helpers ───────────────────────────────────────────────────────────────

function matches(job: JobReadyToSchedule, f: FacetState): boolean {
  if (f.city.size && !f.city.has(normalizeCity(job.city) ?? '')) return false;
  if (f.jobType.size && !f.jobType.has(job.job_type)) return false;
  if (f.priority.size && !f.priority.has(String(job.priority_level ?? 0))) return false;
  if (f.requestedWeek.size && !f.requestedWeek.has(job.requested_week ?? '')) return false;
  if (f.tags.size) {
    const jobTags = new Set(job.customer_tags ?? []);
    let any = false;
    for (const t of f.tags) if (jobTags.has(t as import('@/features/jobs/types').CustomerTag)) { any = true; break; }
    if (!any) return false;
  }
  return true;
}

function matchesValue(j: JobReadyToSchedule, group: FacetKey, value: string): boolean {
  switch (group) {
    case 'city': return (normalizeCity(j.city) ?? '') === value;
    case 'jobType': return j.job_type === value;
    case 'priority': return String(j.priority_level ?? 0) === value;
    case 'requestedWeek': return j.requested_week === value;
    case 'tags': return (j.customer_tags ?? []).includes(value as import('@/features/jobs/types').CustomerTag);
  }
}

function formatWeekLabel(iso: string): string {
  const d = new Date(iso);
  return `Wk of ${d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}`;
}

interface GroupProps {
  title: string;
  testId: string;
  facetKey: string;
  items: string[];
  selected: Set<string>;
  countOf: (value: string) => number;
  onToggle: (value: string) => void;
  onClear: () => void;
  formatLabel?: (value: string) => string;
}

function Group({ title, testId, facetKey, items, selected, countOf, onToggle, onClear, formatLabel }: GroupProps) {
  if (items.length === 0) return null;
  return (
    <fieldset data-testid={testId} className="pjp-facet-group">
      <div className="pjp-facet-head">
        <legend className="pjp-facet-title">{title}</legend>
        {selected.size > 0 && (
          <button type="button" onClick={onClear} className="pjp-facet-clear">
            Clear
          </button>
        )}
      </div>
      <ul className="pjp-facet-list">
        {items.map(v => {
          const count = countOf(v);
          const isOn = selected.has(v);
          return (
            <li
              key={v}
              className="pjp-facet-row"
              data-on={isOn ? 'true' : 'false'}
              data-count={String(count)}
            >
              <label
                data-testid={`facet-value-${facetKey}-${v}`}
              >
                <Checkbox checked={isOn} onCheckedChange={() => onToggle(v)} />
                <span className="pjp-facet-lbl">{formatLabel ? formatLabel(v) : v}</span>
                <span className="pjp-facet-ct pjp-mono">{count}</span>
              </label>
            </li>
          );
        })}
      </ul>
    </fieldset>
  );
}
