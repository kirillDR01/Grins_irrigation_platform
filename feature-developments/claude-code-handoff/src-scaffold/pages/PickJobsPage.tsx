/**
 * SCAFFOLD — PickJobsPage
 *
 * Drop into: frontend/src/features/schedule/pages/PickJobsPage.tsx
 *
 * This file wires together FacetRail, JobTable, SchedulingTray into
 * the 3-region grid layout described in SPEC §3. Pieces marked
 * `// TODO` are where you implement the interaction rules from SPEC §4–§6.
 */

import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { toast } from 'sonner';

import { useJobsReadyToSchedule } from '@/features/schedule/hooks/useJobsReadyToSchedule';
import { useStaff } from '@/features/staff/hooks/useStaff';
import { useCreateAppointment } from '@/features/schedule/hooks/useAppointmentMutations';
import { LoadingSpinner } from '@/shared/components/LoadingSpinner';

import { FacetRail } from '@/features/schedule/components/FacetRail';
import { JobTable } from '@/features/schedule/components/JobTable';
import { SchedulingTray } from '@/features/schedule/components/SchedulingTray';

import type {
  FacetState,
  JobReadyToSchedule,
  PerJobTimeMap,
  SortKey,
  SortDir,
} from '../types/pick-jobs';
import { initialFacets } from '../types/pick-jobs';

function todayIso(): string {
  return new Date().toISOString().split('T')[0];
}

export function PickJobsPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  // ─────────────────────────────────────────── data
  const { data, isLoading, error } = useJobsReadyToSchedule();
  const { data: staffData }        = useStaff({ is_active: true });
  const createAppointment          = useCreateAppointment();

  const jobs: JobReadyToSchedule[] = useMemo(() => data?.jobs ?? [], [data?.jobs]);
  const staff                       = staffData?.items ?? [];

  // ─────────────────────────────────────────── state (SPEC §5)
  const [search,         setSearch]         = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [facets,         setFacets]         = useState<FacetState>(initialFacets);
  const [selectedJobIds, setSelectedJobIds] = useState<Set<string>>(new Set());
  const [perJobTimes,    setPerJobTimes]    = useState<PerJobTimeMap>({});
  const [showTimeAdjust, setShowTimeAdjust] = useState(false);

  const [assignDate,    setAssignDate]    = useState<string>(searchParams.get('date') ?? todayIso());
  const [assignStaffId, setAssignStaffId] = useState<string>(searchParams.get('staff') ?? '');
  const [startTime,     setStartTime]     = useState<string>('08:00');
  const [duration,      setDuration]      = useState<number>(60);

  const [sortKey, setSortKey] = useState<SortKey>('priority');
  const [sortDir, setSortDir] = useState<SortDir>('desc');

  // ─────────────────────────────────────────── search debounce (150ms)
  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(search), 150);
    return () => clearTimeout(t);
  }, [search]);

  // ─────────────────────────────────────────── keyboard: "/" focuses search
  const searchRef = useRef<HTMLInputElement>(null);
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key !== '/') return;
      const t = e.target as HTMLElement | null;
      if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.isContentEditable)) return;
      e.preventDefault();
      searchRef.current?.focus();
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  // ─────────────────────────────────────────── filtering (SPEC §6.1)
  const filteredJobs = useMemo(() => {
    return jobs.filter((job) => {
      // search
      if (debouncedSearch) {
        const q = debouncedSearch.toLowerCase();
        const hay = [
          job.customer_name,
          job.address ?? '',
          job.city,
          job.job_type,
          job.job_id,
        ].join(' ').toLowerCase();
        if (!hay.includes(q)) return false;
      }
      // facets — empty Set = pass-through
      if (facets.city.size          && !facets.city.has(job.city))                              return false;
      if (facets.jobType.size       && !facets.jobType.has(job.job_type))                       return false;
      if (facets.priority.size      && !facets.priority.has(job.priority as 'high' | 'normal')) return false;
      if (facets.requestedWeek.size && !facets.requestedWeek.has(job.requested_week ?? ''))     return false;
      if (facets.tags.size) {
        const jobTags = new Set((job.tags ?? []).map(t => t.toLowerCase()));
        let any = false;
        for (const t of facets.tags) if (jobTags.has(t)) { any = true; break; }
        if (!any) return false;
      }
      return true;
    });
  }, [jobs, debouncedSearch, facets]);

  // TODO: relaxed-count computation for the facet rail (SPEC §6.1)
  // For each facet group, count matches that would remain if THIS facet
  // group's filter were removed (keeping all other filters + search).

  // ─────────────────────────────────────────── sorting (SPEC §6.2.2)
  const sortedJobs = useMemo(() => {
    // TODO: implement 3-state sort with default (priority desc, requested_week asc).
    return filteredJobs;
  }, [filteredJobs, sortKey, sortDir]);

  // ─────────────────────────────────────────── selection helpers
  function toggleJob(jobId: string) {
    setSelectedJobIds(prev => {
      const next = new Set(prev);
      if (next.has(jobId)) {
        next.delete(jobId);
        setPerJobTimes(pt => {
          const copy = { ...pt };
          delete copy[jobId];
          return copy;
        });
      } else {
        next.add(jobId);
      }
      return next;
    });
  }

  function toggleAllVisible() {
    setSelectedJobIds(prev => {
      const visibleIds = sortedJobs.map(j => j.job_id);
      const allSelected = visibleIds.length > 0 && visibleIds.every(id => prev.has(id));
      const next = new Set(prev);
      if (allSelected) {
        visibleIds.forEach(id => next.delete(id));
        setPerJobTimes(pt => {
          const copy = { ...pt };
          visibleIds.forEach(id => { delete copy[id]; });
          return copy;
        });
      } else {
        visibleIds.forEach(id => next.add(id));
      }
      return next;
    });
  }

  function clearSelection() {
    setSelectedJobIds(new Set());
    setPerJobTimes({});
  }

  function clearAllFilters() {
    setFacets(initialFacets);
    // Per SPEC §6.1: do NOT clear search.
  }

  // ─────────────────────────────────────────── unsaved-changes guard (SPEC §6.6)
  const suppressGuardRef = useRef(false);
  useEffect(() => {
    function onBeforeUnload(e: BeforeUnloadEvent) {
      if (selectedJobIds.size > 0 && !suppressGuardRef.current) {
        e.preventDefault();
        e.returnValue = '';
      }
    }
    window.addEventListener('beforeunload', onBeforeUnload);
    return () => window.removeEventListener('beforeunload', onBeforeUnload);
  }, [selectedJobIds.size]);

  // TODO: wire up react-router v7 `useBlocker()` for in-app navigation,
  // opening <AlertDialog> with the SPEC §6.6 copy.

  // ─────────────────────────────────────────── assign (SPEC §6.3.3)
  async function handleBulkAssign() {
    if (selectedJobIds.size === 0 || !assignStaffId) return;

    // TODO: compute per-job times exactly like JobPickerPopup.computeJobTimes
    // (sequential cascade using global startTime + each job's
    // estimated_duration_minutes, overridden by perJobTimes[jobId] when set).
    const times: Record<string, { start: string; end: string }> = {};

    let ok = 0;
    let fail = 0;
    for (const jobId of selectedJobIds) {
      const t = times[jobId];
      if (!t) { fail++; continue; }
      try {
        await createAppointment.mutateAsync({
          job_id: jobId,
          staff_id: assignStaffId,
          scheduled_date: assignDate,
          time_window_start: `${t.start}:00`,
          time_window_end:   `${t.end}:00`,
        });
        ok++;
      } catch {
        fail++;
      }
    }

    if (ok > 0)  toast.success(`Assigned ${ok} job${ok !== 1 ? 's' : ''} to schedule`);
    if (fail > 0) toast.error(`Failed to assign ${fail} job${fail !== 1 ? 's' : ''}`);

    clearSelection();
    if (ok > 0) {
      suppressGuardRef.current = true;
      navigate(`/schedule?date=${assignDate}`);
    }
  }

  // ─────────────────────────────────────────── render
  if (error) {
    return <div className="p-6 text-sm text-destructive">Failed to load jobs. Retry?</div>;
  }

  return (
    <div
      className="grid h-[calc(100vh-theme(spacing.16))] grid-cols-1 grid-rows-[auto_1fr_auto] gap-y-4 lg:grid-cols-[240px_1fr] lg:gap-x-6"
      data-testid="pick-jobs-page"
    >
      {/* Header ─────────────────────────────────────────────────── */}
      <header className="col-span-full px-6 pt-6">
        <button
          type="button"
          className="text-xs text-muted-foreground hover:text-foreground"
          onClick={() => navigate(-1)}
        >
          ← Back to schedule
        </button>
        <h1 className="text-2xl font-semibold tracking-tight">Pick jobs to schedule</h1>
        <p className="text-sm text-muted-foreground">
          Browse freely. Facets on the left narrow the list; the scheduling tray stays pinned below.
        </p>
      </header>

      {/* Facet rail ─────────────────────────────────────────────── */}
      <aside className="hidden lg:block overflow-y-auto pl-6" data-testid="facet-rail">
        <FacetRail
          jobs={jobs}
          facets={facets}
          onChange={setFacets}
          onClearAll={clearAllFilters}
        />
      </aside>

      {/* Main table region ──────────────────────────────────────── */}
      <main className="overflow-hidden flex flex-col px-6 lg:pl-0 lg:pr-6">
        {isLoading ? (
          <div className="flex-1 flex items-center justify-center"><LoadingSpinner /></div>
        ) : (
          <JobTable
            jobs={sortedJobs}
            searchRef={searchRef}
            search={search}
            onSearchChange={setSearch}
            selectedJobIds={selectedJobIds}
            onToggleJob={toggleJob}
            onToggleAllVisible={toggleAllVisible}
            sortKey={sortKey}
            sortDir={sortDir}
            onSort={(key, dir) => { setSortKey(key); setSortDir(dir); }}
            onClearAllFilters={clearAllFilters}
            anyFilterActive={
              Object.values(facets).some(s => (s as Set<unknown>).size > 0) || !!debouncedSearch
            }
          />
        )}
      </main>

      {/* Scheduling tray ────────────────────────────────────────── */}
      <footer className="col-span-full" data-testid="scheduling-tray">
        <SchedulingTray
          selectedJobIds={selectedJobIds}
          selectedJobs={sortedJobs.filter(j => selectedJobIds.has(j.job_id))}
          totalSelectedCount={selectedJobIds.size}
          staff={staff}

          assignDate={assignDate}
          onAssignDateChange={setAssignDate}
          assignStaffId={assignStaffId}
          onAssignStaffIdChange={setAssignStaffId}
          startTime={startTime}
          onStartTimeChange={setStartTime}
          duration={duration}
          onDurationChange={setDuration}

          perJobTimes={perJobTimes}
          onPerJobTimesChange={setPerJobTimes}
          showTimeAdjust={showTimeAdjust}
          onShowTimeAdjustChange={setShowTimeAdjust}

          isAssigning={createAppointment.isPending}
          onAssign={handleBulkAssign}
          onClearSelection={clearSelection}
        />
      </footer>
    </div>
  );
}
