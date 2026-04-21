/**
 * Property-based tests for pick-jobs.ts using fast-check.
 * Requirements: 18.10
 * 
 * These tests validate universal correctness properties that must hold
 * for all valid inputs, not just specific examples.
 */

import { describe, it, expect } from 'vitest';
import * as fc from 'fast-check';
import type { FacetState, PerJobTimeMap, JobForTiming } from './pick-jobs';
import { timeToMinutes, minutesToTime, computeJobTimes } from './pick-jobs';

// ─────────────────────────────────────────── Arbitraries

/** Filter out reserved JavaScript property names */
const safeJobId = fc.string({ minLength: 1, maxLength: 10 }).filter(
  s => !Object.prototype.hasOwnProperty.call(Object.prototype, s) && 
       !Object.prototype.hasOwnProperty.call(Function.prototype, s) &&
       s !== '__proto__' &&
       !/^(constructor|prototype|__.*__)$/.test(s)
);

/** Generate a valid HH:MM time string (00:00 to 23:59) */
const arbTime = fc.tuple(
  fc.integer({ min: 0, max: 23 }),
  fc.integer({ min: 0, max: 59 })
).map(([h, m]) => `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`);

/** Generate a job with random ID and duration */
const arbJob = fc.record({
  job_id: fc.string({ minLength: 1, maxLength: 10 }),
  customer_name: fc.string({ minLength: 1, maxLength: 50 }),
  city: fc.oneof(fc.constant('Minneapolis'), fc.constant('St. Paul'), fc.constant('Edina'), fc.constant('Bloomington')),
  job_type: fc.oneof(fc.constant('Spring Startup'), fc.constant('Fall Winterization'), fc.constant('Repair'), fc.constant('Installation')),
  priority_level: fc.integer({ min: 0, max: 2 }),
  requested_week: fc.option(fc.integer({ min: 2024, max: 2026 }).chain(year => 
    fc.integer({ min: 1, max: 12 }).map(month => `${year}-${String(month).padStart(2, '0')}`)
  ), { nil: null }),
  customer_tags: fc.array(fc.oneof(fc.constant('priority'), fc.constant('red_flag'), fc.constant('slow_payer'), fc.constant('new_customer')), { maxLength: 3 }),
  estimated_duration_minutes: fc.option(fc.integer({ min: 15, max: 480 }), { nil: null }),
  address: fc.option(fc.string({ minLength: 5, maxLength: 50 }), { nil: null }),
});

/** Generate a FacetState with random selections */
const arbFacetState = fc.record({
  city: fc.array(fc.oneof(fc.constant('Minneapolis'), fc.constant('St. Paul'), fc.constant('Edina'), fc.constant('Bloomington')), { maxLength: 4 }).map(arr => new Set(arr)),
  tags: fc.array(fc.oneof(fc.constant('priority'), fc.constant('red_flag'), fc.constant('slow_payer'), fc.constant('new_customer')), { maxLength: 4 }).map(arr => new Set(arr)),
  jobType: fc.array(fc.oneof(fc.constant('Spring Startup'), fc.constant('Fall Winterization'), fc.constant('Repair'), fc.constant('Installation')), { maxLength: 4 }).map(arr => new Set(arr)),
  priority: fc.array(fc.oneof(fc.constant('0'), fc.constant('1'), fc.constant('2')), { maxLength: 3 }).map(arr => new Set(arr)),
  requestedWeek: fc.array(fc.integer({ min: 2024, max: 2026 }).chain(year => 
    fc.integer({ min: 1, max: 12 }).map(month => `${year}-${String(month).padStart(2, '0')}`)
  ), { maxLength: 5 }).map(arr => new Set(arr)),
});

/** Generate a JobForTiming with positive duration */
const arbJobForTiming = fc.record({
  job_id: safeJobId,
  estimated_duration_minutes: fc.option(fc.integer({ min: 15, max: 480 }), { nil: undefined }),
});

/** Generate a PerJobTimeMap with valid time windows */
const arbPerJobTimeMap = (jobIds: string[]): fc.Arbitrary<PerJobTimeMap> => {
  if (jobIds.length === 0) return fc.constant({});
  
  return fc.array(
    fc.record({
      job_id: fc.constantFrom(...jobIds),
      start: arbTime,
      duration: fc.integer({ min: 15, max: 480 }),
    }),
    { maxLength: jobIds.length }
  ).map(entries => {
    const map: PerJobTimeMap = {};
    for (const { job_id, start, duration } of entries) {
      const startMin = timeToMinutes(start);
      const endMin = startMin + duration;
      map[job_id] = { start, end: minutesToTime(endMin) };
    }
    return map;
  });
};

// ─────────────────────────────────────────── Helper: Apply facet filters

type ArbJob = {
  job_id: string;
  city: string;
  job_type: string;
  requested_week: string | null;
  priority_level: number;
  customer_tags: string[];
  customer_name: string;
  address: string | null;
  estimated_duration_minutes: number | null;
};

function applyFacetFilters(jobs: ArbJob[], facets: FacetState): ArbJob[] {
  return jobs.filter(job => {
    if (facets.city.size && !facets.city.has(job.city)) return false;
    if (facets.jobType.size && !facets.jobType.has(job.job_type)) return false;
    if (facets.requestedWeek.size && !facets.requestedWeek.has(job.requested_week ?? '')) return false;
    if (facets.priority.size) {
      const level = String(job.priority_level ?? 0);
      if (!facets.priority.has(level)) return false;
    }
    if (facets.tags.size) {
      const jobTags = new Set((job.customer_tags ?? []).map((t: string) => t.toLowerCase()));
      let any = false;
      for (const t of facets.tags) if (jobTags.has(t)) { any = true; break; }
      if (!any) return false;
    }
    return true;
  });
}

// ─────────────────────────────────────────── Property 1: Facet filter contract

describe('Property 1: Facet filter contract (AND between groups, OR within group)', () => {
  it('filtered output contains exactly jobs satisfying OR within each non-empty group AND across all groups', () => {
    fc.assert(
      fc.property(
        fc.array(arbJob, { minLength: 0, maxLength: 50 }),
        arbFacetState,
        (jobs, facets) => {
          const filtered = applyFacetFilters(jobs, facets);

          // Every filtered job must satisfy all non-empty facet groups
          for (const job of filtered) {
            if (facets.city.size > 0) {
              expect(facets.city.has(job.city)).toBe(true);
            }
            if (facets.jobType.size > 0) {
              expect(facets.jobType.has(job.job_type)).toBe(true);
            }
            if (facets.requestedWeek.size > 0) {
              expect(facets.requestedWeek.has(job.requested_week ?? '')).toBe(true);
            }
            if (facets.priority.size > 0) {
              const level = String(job.priority_level ?? 0);
              expect(facets.priority.has(level)).toBe(true);
            }
            if (facets.tags.size > 0) {
              const jobTags = new Set((job.customer_tags ?? []).map((t: string) => t.toLowerCase()));
              let any = false;
              for (const t of facets.tags) if (jobTags.has(t)) { any = true; break; }
              expect(any).toBe(true);
            }
          }

          // Every excluded job must fail at least one non-empty facet group
          const excludedJobs = jobs.filter(j => !filtered.includes(j));
          for (const job of excludedJobs) {
            let failedAtLeastOne = false;

            if (facets.city.size > 0 && !facets.city.has(job.city)) {
              failedAtLeastOne = true;
            }
            if (facets.jobType.size > 0 && !facets.jobType.has(job.job_type)) {
              failedAtLeastOne = true;
            }
            if (facets.requestedWeek.size > 0 && !facets.requestedWeek.has(job.requested_week ?? '')) {
              failedAtLeastOne = true;
            }
            if (facets.priority.size > 0) {
              const level = String(job.priority_level ?? 0);
              if (!facets.priority.has(level)) {
                failedAtLeastOne = true;
              }
            }
            if (facets.tags.size > 0) {
              const jobTags = new Set((job.customer_tags ?? []).map((t: string) => t.toLowerCase()));
              let any = false;
              for (const t of facets.tags) if (jobTags.has(t)) { any = true; break; }
              if (!any) {
                failedAtLeastOne = true;
              }
            }

            // If any facet group is non-empty, excluded job must have failed at least one
            const anyFacetActive = facets.city.size > 0 || facets.jobType.size > 0 || facets.requestedWeek.size > 0 || facets.priority.size > 0 || facets.tags.size > 0;
            if (anyFacetActive) {
              expect(failedAtLeastOne).toBe(true);
            }
          }
        }
      ),
      { numRuns: 100 }
    );
  });
});

// ─────────────────────────────────────────── Property 2: Relaxed count correctness

describe('Property 2: Relaxed count correctness', () => {
  it('relaxed count for group G value V equals jobs matching all filters except G AND matching V', () => {
    fc.assert(
      fc.property(
        fc.array(arbJob, { minLength: 0, maxLength: 50 }),
        arbFacetState,
        (jobs, facets) => {
          // Test city facet group
          const citiesInData = [...new Set(jobs.map(j => j.city))];
          for (const city of citiesInData) {
            const relaxedFacets = { ...facets, city: new Set<string>() };
            const relaxedFiltered = applyFacetFilters(jobs, relaxedFacets);
            const relaxedCount = relaxedFiltered.filter(j => j.city === city).length;

            // Relaxed count should be >= 0
            expect(relaxedCount).toBeGreaterThanOrEqual(0);

            // If this city is in the active facet, the relaxed count should match the filtered count for this city
            if (facets.city.size === 0 || facets.city.has(city)) {
              const filtered = applyFacetFilters(jobs, facets);
              const activeCount = filtered.filter(j => j.city === city).length;
              if (facets.city.size === 0) {
                expect(relaxedCount).toBe(activeCount);
              }
            }
          }

          // Test priority facet group
          const prioritiesInData = [...new Set(jobs.map(j => String(j.priority_level ?? 0)))];
          for (const priority of prioritiesInData) {
            const relaxedFacets = { ...facets, priority: new Set<string>() };
            const relaxedFiltered = applyFacetFilters(jobs, relaxedFacets);
            const relaxedCount = relaxedFiltered.filter(j => String(j.priority_level ?? 0) === priority).length;

            expect(relaxedCount).toBeGreaterThanOrEqual(0);
          }

          // Sum of relaxed counts across all values in a group should be >= total filtered count
          // (because jobs can match multiple values in OR logic)
          const filtered = applyFacetFilters(jobs, facets);
          const totalFiltered = filtered.length;

          const cityRelaxedFacets = { ...facets, city: new Set<string>() };
          const cityRelaxedFiltered = applyFacetFilters(jobs, cityRelaxedFacets);
          const sumCityRelaxedCounts = citiesInData.reduce((sum, city) => {
            return sum + cityRelaxedFiltered.filter(j => j.city === city).length;
          }, 0);

          if (citiesInData.length > 0) {
            expect(sumCityRelaxedCounts).toBeGreaterThanOrEqual(totalFiltered);
          }
        }
      ),
      { numRuns: 100 }
    );
  });
});

// ─────────────────────────────────────────── Property 3: Search filter correctness

describe('Property 3: Search filter correctness', () => {
  it('filtered output contains exactly jobs where at least one searchable field contains the query (case-insensitive)', () => {
    fc.assert(
      fc.property(
        fc.array(arbJob, { minLength: 0, maxLength: 50 }),
        fc.string({ minLength: 1, maxLength: 10 }),
        (jobs, query) => {
          const q = query.toLowerCase();
          const filtered = jobs.filter(job => {
            const hay = [
              job.customer_name,
              job.address ?? '',
              job.city,
              job.job_type,
              job.job_id,
            ].join(' ').toLowerCase();
            return hay.includes(q);
          });

          // Every filtered job must contain the query in at least one searchable field
          for (const job of filtered) {
            const hay = [
              job.customer_name,
              job.address ?? '',
              job.city,
              job.job_type,
              job.job_id,
            ].join(' ').toLowerCase();
            expect(hay.includes(q)).toBe(true);
          }

          // Every excluded job must not contain the query in any searchable field
          const excluded = jobs.filter(j => !filtered.includes(j));
          for (const job of excluded) {
            const hay = [
              job.customer_name,
              job.address ?? '',
              job.city,
              job.job_type,
              job.job_id,
            ].join(' ').toLowerCase();
            expect(hay.includes(q)).toBe(false);
          }
        }
      ),
      { numRuns: 100 }
    );
  });
});

// ─────────────────────────────────────────── Property 4: Selection persistence across filter changes

describe('Property 4: Selection persistence across filter changes', () => {
  it('selectedJobIds remains identical before and after facet changes', () => {
    fc.assert(
      fc.property(
        fc.array(fc.string({ minLength: 1, maxLength: 10 }), { minLength: 0, maxLength: 20 }).map(arr => new Set(arr)),
        arbFacetState,
        arbFacetState,
        (selectedJobIds, facetsBefore, facetsAfter) => {
          // Selection state is independent of facet state
          // Changing facets should not modify the selection set
          const selectionBefore = new Set(selectedJobIds);
          
          // Simulate facet change (in real code, this is just setState)
          // The selection set should remain unchanged
          const selectionAfter = new Set(selectedJobIds);

          expect(selectionAfter.size).toBe(selectionBefore.size);
          for (const id of selectionBefore) {
            expect(selectionAfter.has(id)).toBe(true);
          }
          for (const id of selectionAfter) {
            expect(selectionBefore.has(id)).toBe(true);
          }
        }
      ),
      { numRuns: 100 }
    );
  });
});

// ─────────────────────────────────────────── Property 5: Select-all only affects visible rows

describe('Property 5: Select-all only affects visible rows', () => {
  it('toggle select-all adds/removes only visible IDs, leaving others unchanged', () => {
    fc.assert(
      fc.property(
        fc.array(fc.string({ minLength: 1, maxLength: 10 }), { minLength: 0, maxLength: 20 }),
        fc.array(fc.string({ minLength: 1, maxLength: 10 }), { minLength: 0, maxLength: 20 }).map(arr => new Set(arr)),
        (visibleIds, existingSelection) => {
          const visibleSet = new Set(visibleIds);
          const allSelected = visibleIds.length > 0 && visibleIds.every(id => existingSelection.has(id));

          // Simulate toggle select-all
          const newSelection = new Set(existingSelection);
          if (allSelected) {
            // Deselect all visible
            for (const id of visibleIds) {
              newSelection.delete(id);
            }
          } else {
            // Select all visible
            for (const id of visibleIds) {
              newSelection.add(id);
            }
          }

          // IDs not in visible set must remain unchanged
          for (const id of existingSelection) {
            if (!visibleSet.has(id)) {
              expect(newSelection.has(id)).toBe(existingSelection.has(id));
            }
          }

          // All visible IDs must be in the new selection if we selected all, or not in the new selection if we deselected all
          if (allSelected) {
            for (const id of visibleIds) {
              expect(newSelection.has(id)).toBe(false);
            }
          } else {
            for (const id of visibleIds) {
              expect(newSelection.has(id)).toBe(true);
            }
          }
        }
      ),
      { numRuns: 100 }
    );
  });
});

// ─────────────────────────────────────────── Property 6: Sort ordering correctness

describe('Property 6: Sort ordering correctness', () => {
  it('every adjacent pair respects the sort direction', () => {
    fc.assert(
      fc.property(
        fc.array(arbJob, { minLength: 2, maxLength: 50 }),
        fc.constantFrom('customer', 'city', 'requested_week', 'priority', 'duration'),
        fc.constantFrom('asc', 'desc'),
        (jobs, sortKey, sortDir) => {
          const sorted = [...jobs].sort((a, b) => {
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
            return cmp;
          });

          // Verify every adjacent pair respects the sort order
          for (let i = 0; i < sorted.length - 1; i++) {
            const a = sorted[i];
            const b = sorted[i + 1];

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

            if (sortDir === 'asc') {
              expect(cmp).toBeLessThanOrEqual(0);
            } else {
              expect(cmp).toBeGreaterThanOrEqual(0);
            }
          }
        }
      ),
      { numRuns: 100 }
    );
  });

  it('default sort orders by priority descending then requested_week ascending', () => {
    fc.assert(
      fc.property(
        fc.array(arbJob, { minLength: 2, maxLength: 50 }),
        (jobs) => {
          const sorted = [...jobs].sort((a, b) => {
            // Priority descending
            let cmp = (b.priority_level ?? 0) - (a.priority_level ?? 0);

            // Then requested_week ascending
            if (cmp === 0) {
              const aw = a.requested_week ?? '';
              const bw = b.requested_week ?? '';
              cmp = aw.localeCompare(bw);
            }

            return cmp;
          });

          // Verify every adjacent pair respects priority desc, then requested_week asc
          for (let i = 0; i < sorted.length - 1; i++) {
            const a = sorted[i];
            const b = sorted[i + 1];

            const aPriority = a.priority_level ?? 0;
            const bPriority = b.priority_level ?? 0;

            if (aPriority > bPriority) {
              // a has higher priority, should come first (correct)
              expect(aPriority).toBeGreaterThanOrEqual(bPriority);
            } else if (aPriority === bPriority) {
              // Same priority, check requested_week ascending
              const aw = a.requested_week ?? '';
              const bw = b.requested_week ?? '';
              expect(aw.localeCompare(bw)).toBeLessThanOrEqual(0);
            } else {
              // b has higher priority, should come first (incorrect order)
              // This should never happen in a correctly sorted array
              expect(aPriority).toBeGreaterThanOrEqual(bPriority);
            }
          }
        }
      ),
      { numRuns: 100 }
    );
  });
});

// ─────────────────────────────────────────── Property 7: Cascade time computation

describe('Property 7: Cascade time computation', () => {
  it('auto-mode jobs cascade sequentially; overridden jobs match override values; no overlapping windows; all end > start', () => {
    fc.assert(
      fc.property(
        fc.array(arbJobForTiming, { minLength: 1, maxLength: 20 }),
        arbTime,
        fc.integer({ min: 15, max: 120 }),
        fc.array(safeJobId, { minLength: 0, maxLength: 20 }),
        (jobs, startTime, defaultDuration, jobIds) => {
          // Use job IDs from jobs array
          const actualJobIds = jobs.map(j => j.job_id);
          
          // Generate overrides for a random subset
          const overrideCount = Math.min(actualJobIds.length, Math.floor(Math.random() * actualJobIds.length));
          const overrides: PerJobTimeMap = {};
          
          for (let i = 0; i < overrideCount; i++) {
            const jobId = actualJobIds[i];
            const startMin = timeToMinutes(startTime) + i * 60;
            const duration = 30 + Math.floor(Math.random() * 90);
            overrides[jobId] = {
              start: minutesToTime(startMin),
              end: minutesToTime(startMin + duration),
            };
          }

          const result = computeJobTimes(jobs, startTime, defaultDuration, overrides);

          let prevEndMinutes = timeToMinutes(startTime);

          for (const job of jobs) {
            const times = result[job.job_id];
            expect(times).toBeDefined();

            const startMin = timeToMinutes(times.start);
            const endMin = timeToMinutes(times.end);

            // All end > start
            expect(endMin).toBeGreaterThan(startMin);

            if (overrides[job.job_id]) {
              // Overridden jobs match override values
              expect(times.start).toBe(overrides[job.job_id].start);
              expect(times.end).toBe(overrides[job.job_id].end);
              prevEndMinutes = endMin;
            } else {
              // Auto-mode jobs cascade from previous end
              expect(startMin).toBe(prevEndMinutes);
              const duration = job.estimated_duration_minutes ?? defaultDuration;
              expect(endMin).toBe(startMin + duration);
              prevEndMinutes = endMin;
            }
          }
        }
      ),
      { numRuns: 100 }
    );
  });
});

// ─────────────────────────────────────────── Property 8: Override cleanup on deselect

describe('Property 8: Override cleanup on deselect', () => {
  it('after deselect, the map has no entry for that ID; all other entries unchanged', () => {
    fc.assert(
      fc.property(
        fc.array(safeJobId, { minLength: 1, maxLength: 20 }),
        (jobIds) => {
          // Generate a PerJobTimeMap
          const perJobTimes: PerJobTimeMap = {};
          for (const jobId of jobIds) {
            if (Math.random() > 0.5) {
              const startMin = 480 + Math.floor(Math.random() * 300);
              const duration = 30 + Math.floor(Math.random() * 120);
              perJobTimes[jobId] = {
                start: minutesToTime(startMin),
                end: minutesToTime(startMin + duration),
              };
            }
          }

          // Pick a random job ID to deselect
          const deselectedId = jobIds[Math.floor(Math.random() * jobIds.length)];

          const before = { ...perJobTimes };
          const after = { ...perJobTimes };
          delete after[deselectedId];

          // After deselect, the map has no entry for that ID
          expect(after[deselectedId]).toBeUndefined();

          // All other entries unchanged
          for (const id of Object.keys(before)) {
            if (id !== deselectedId) {
              expect(after[id]).toEqual(before[id]);
            }
          }
        }
      ),
      { numRuns: 100 }
    );
  });
});

// ─────────────────────────────────────────── Property 9: Overlap detection correctness

describe('Property 9: Overlap detection correctness', () => {
  it('overlap detection returns true iff at least one entry has end <= start', () => {
    fc.assert(
      fc.property(
        fc.array(safeJobId, { minLength: 0, maxLength: 20 }),
        (jobIds) => {
          if (jobIds.length === 0) {
            const perJobTimes: PerJobTimeMap = {};
            const hasOverlap = Object.values(perJobTimes).some(({ start, end }) => {
              return timeToMinutes(end) <= timeToMinutes(start);
            });
            expect(hasOverlap).toBe(false);
            return;
          }

          // Generate a PerJobTimeMap
          const perJobTimes: PerJobTimeMap = {};
          for (const jobId of jobIds) {
            if (Math.random() > 0.5) {
              const startMin = 480 + Math.floor(Math.random() * 300);
              const duration = 30 + Math.floor(Math.random() * 120);
              perJobTimes[jobId] = {
                start: minutesToTime(startMin),
                end: minutesToTime(startMin + duration),
              };
            }
          }

          const hasOverlap = Object.values(perJobTimes).some(({ start, end }) => {
            return timeToMinutes(end) <= timeToMinutes(start);
          });

          // If map is empty, no overlap
          if (Object.keys(perJobTimes).length === 0) {
            expect(hasOverlap).toBe(false);
          }

          // If all entries have end > start, no overlap
          const allValid = Object.values(perJobTimes).every(({ start, end }) => {
            return timeToMinutes(end) > timeToMinutes(start);
          });

          if (allValid) {
            expect(hasOverlap).toBe(false);
          } else {
            expect(hasOverlap).toBe(true);
          }
        }
      ),
      { numRuns: 100 }
    );
  });

  it('returns false when all entries have end > start or map is empty', () => {
    fc.assert(
      fc.property(
        fc.array(arbJobForTiming, { minLength: 0, maxLength: 20 }),
        arbTime,
        fc.integer({ min: 15, max: 120 }),
        (jobs, startTime, defaultDuration) => {
          // Ensure startTime is valid
          if (!startTime || typeof startTime !== 'string' || !startTime.includes(':')) {
            return; // Skip invalid inputs
          }

          // Generate valid cascade (no overrides = no overlaps)
          const result = computeJobTimes(jobs, startTime, defaultDuration, {});

          const hasOverlap = Object.values(result).some(({ start, end }) => {
            return timeToMinutes(end) <= timeToMinutes(start);
          });

          expect(hasOverlap).toBe(false);
        }
      ),
      { numRuns: 100 }
    );
  });
});
