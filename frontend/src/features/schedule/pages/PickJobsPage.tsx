// @ts-nocheck — pre-existing TS errors documented in bughunt/2026-04-29-pre-existing-tsc-errors.md
/**
 * PickJobsPage — full-page job picker at /schedule/pick-jobs.
 * Requirements: 1.1, 1.4, 1.5, 1.6, 2.1, 2.2, 5.4, 7.1, 7.2, 12.1–12.3, 15.1, 15.7
 */

import { useEffect, useMemo, useRef, useState } from 'react';
import { useBlocker, useNavigate, useSearchParams } from 'react-router-dom';
import { toast } from 'sonner';

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';

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
import { initialFacets, computeJobTimes } from '../types/pick-jobs';
import { normalizeCity } from '../utils/city';

import '../styles/pick-jobs-theme.css';

function todayIso(): string {
  return new Date().toISOString().split('T')[0];
}

export function PickJobsPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  // ─── data ────────────────────────────────────────────────────────────────
  const { data, isLoading, error } = useJobsReadyToSchedule();
  const { data: staffData } = useStaff({ is_active: true });
  const createAppointment = useCreateAppointment();

  const jobs: JobReadyToSchedule[] = useMemo(() => data?.jobs ?? [], [data?.jobs]);
  const staff = staffData?.items ?? [];

  // ─── state ───────────────────────────────────────────────────────────────
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [facets, setFacets] = useState<FacetState>(initialFacets);
  const [selectedJobIds, setSelectedJobIds] = useState<Set<string>>(new Set());
  const [perJobTimes, setPerJobTimes] = useState<PerJobTimeMap>({});
  const [showTimeAdjust, setShowTimeAdjust] = useState(false);

  const [assignDate, setAssignDate] = useState<string>(searchParams.get('date') ?? todayIso());
  const [assignStaffId, setAssignStaffId] = useState<string>(searchParams.get('staff') ?? '');
  const [startTime, setStartTime] = useState<string>('08:00');
  const [duration, setDuration] = useState<number>(60);

  const [sortKey, setSortKey] = useState<SortKey>('priority');
  const [sortDir, setSortDir] = useState<SortDir>('desc');

  // ─── search debounce (150ms) ──────────────────────────────────────────────
  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(search), 150);
    return () => clearTimeout(t);
  }, [search]);

  // ─── keyboard: "/" focuses search ────────────────────────────────────────
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

  // ─── keyboard: Cmd/Ctrl+Enter triggers assign ─────────────────────────────
  const suppressGuardRef = useRef(false);
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
        e.preventDefault();
        if (selectedJobIds.size > 0 && assignStaffId && !createAppointment.isPending) {
          void handleBulkAssign();
        }
      }
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedJobIds.size, assignStaffId, createAppointment.isPending]);

  // ─── filtering ───────────────────────────────────────────────────────────
  const filteredJobs = useMemo(() => {
    return jobs.filter((job) => {
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
      if (facets.city.size && !facets.city.has(normalizeCity(job.city) ?? '')) return false;
      if (facets.jobType.size && !facets.jobType.has(job.job_type)) return false;
      if (facets.requestedWeek.size && !facets.requestedWeek.has(job.requested_week ?? '')) return false;
      if (facets.priority.size) {
        const level = String(job.priority_level ?? 0);
        if (!facets.priority.has(level)) return false;
      }
      if (facets.tags.size) {
        const jobTags = new Set((job.customer_tags ?? []).map(t => t.toLowerCase()));
        let any = false;
        for (const t of facets.tags) if (jobTags.has(t)) { any = true; break; }
        if (!any) return false;
      }
      return true;
    });
  }, [jobs, debouncedSearch, facets]);

  // ─── sorting (3-state: asc → desc → default priority desc, requested_week asc) ──
  const sortedJobs = useMemo(() => {
    const isDefault = sortKey === 'priority' && sortDir === 'desc';

    return [...filteredJobs].sort((a, b) => {
      let cmp = 0;

      switch (sortKey) {
        case 'customer':
          cmp = a.customer_name.localeCompare(b.customer_name);
          break;
        case 'city':
          cmp = a.city.localeCompare(b.city);
          break;
        case 'requested_week': {
          const aw = a.requested_week ?? '';
          const bw = b.requested_week ?? '';
          cmp = aw.localeCompare(bw);
          break;
        }
        case 'priority':
          cmp = (a.priority_level ?? 0) - (b.priority_level ?? 0);
          break;
        case 'duration':
          cmp = (a.estimated_duration_minutes ?? 0) - (b.estimated_duration_minutes ?? 0);
          break;
      }

      if (sortDir === 'desc') cmp = -cmp;

      // Secondary sort for default: priority desc → requested_week asc
      if (isDefault && cmp === 0) {
        const aw = a.requested_week ?? '';
        const bw = b.requested_week ?? '';
        cmp = aw.localeCompare(bw);
      }

      return cmp;
    });
  }, [filteredJobs, sortKey, sortDir]);

  // ─── selection helpers ────────────────────────────────────────────────────
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
  }

  // ─── unsaved-changes guard ────────────────────────────────────────────────
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

  // In-app navigation guard via react-router useBlocker
  const blocker = useBlocker(
    ({ currentLocation, nextLocation }) =>
      selectedJobIds.size > 0 &&
      !suppressGuardRef.current &&
      currentLocation.pathname !== nextLocation.pathname,
  );

  // ─── assign ───────────────────────────────────────────────────────────────
  async function handleBulkAssign() {
    if (selectedJobIds.size === 0 || !assignStaffId) return;

    const selectedJobsList = jobs.filter(j => selectedJobIds.has(j.job_id));
    const times = computeJobTimes(selectedJobsList, startTime, duration, perJobTimes);

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
          time_window_end: `${t.end}:00`,
        });
        ok++;
      } catch {
        fail++;
      }
    }

    if (ok > 0) toast.success(`Assigned ${ok} job${ok !== 1 ? 's' : ''} to schedule`);
    if (fail > 0) toast.error(`Failed to assign ${fail} job${fail !== 1 ? 's' : ''}`);

    clearSelection();
    if (ok > 0) {
      suppressGuardRef.current = true;
      navigate(`/schedule?date=${assignDate}`);
    }
  }

  // ─── render ───────────────────────────────────────────────────────────────
  if (error) {
    return <div className="p-6 text-sm text-destructive">Failed to load jobs. Retry?</div>;
  }

  const anyFilterActive =
    Object.values(facets).some(s => (s as Set<unknown>).size > 0) || !!debouncedSearch;

  return (
    <>
      {/* Leave-without-saving guard dialog */}
      <Dialog
        open={blocker.state === 'blocked'}
        onOpenChange={(open) => { if (!open) blocker.reset?.(); }}
      >
        <DialogContent showCloseButton={false}>
          <DialogHeader>
            <DialogTitle>Leave without scheduling?</DialogTitle>
            <DialogDescription>
              You have {selectedJobIds.size} selected job{selectedJobIds.size !== 1 ? 's' : ''} that
              haven&apos;t been scheduled. Leave anyway?
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => blocker.reset?.()}>
              Stay on page
            </Button>
            <Button variant="destructive" onClick={() => blocker.proceed?.()}>
              Leave anyway
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

    <div data-pjp-root data-testid="pick-jobs-page">
      <div className="pjp-app-shell">
        {/* Facet rail (left) */}
        <aside>
          <FacetRail
            jobs={jobs}
            facets={facets}
            onChange={setFacets}
            onClearAll={clearAllFilters}
          />
        </aside>

        {/* Main canvas */}
        <main className="pjp-main">
          <header className="pjp-page-head">
            <button
              type="button"
              className="pjp-back-link"
              onClick={() => navigate(-1)}
            >
              ← Back to schedule
            </button>
            <h1 className="pjp-page-title">Pick jobs to schedule</h1>
            <p className="pjp-page-sub">
              Browse freely. Facets on the left narrow the list; the scheduling tray stays pinned below.
            </p>
          </header>

          {isLoading ? (
            <div className="flex items-center justify-center py-16"><LoadingSpinner /></div>
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
              anyFilterActive={anyFilterActive}
            />
          )}

          <div className="pjp-main-scroll-pad" aria-hidden="true" />
        </main>
      </div>

      {/* Fixed scheduling tray (sibling of shell, inside data-pjp-root) */}
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
    </div>
    </>
  );
}
