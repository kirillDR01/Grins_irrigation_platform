/**
 * Types and pure logic for the Pick Jobs Scheduler page.
 * Requirements: 4.10, 9.4, 9.5
 */

import type { CustomerTag } from '@/features/jobs/types';

// ─────────────────────────────────────────── Facet types

export interface FacetState {
  city: Set<string>;
  tags: Set<string>;
  jobType: Set<string>;
  priority: Set<string>;
  requestedWeek: Set<string>;
}

export const initialFacets: FacetState = {
  city: new Set(),
  tags: new Set(),
  jobType: new Set(),
  priority: new Set(),
  requestedWeek: new Set(),
};

// ─────────────────────────────────────────── Per-job time types

export interface PerJobTime {
  start: string; // HH:MM
  end: string;   // HH:MM
}

export type PerJobTimeMap = Record<string, PerJobTime>;

// ─────────────────────────────────────────── Sort types

export type SortKey = 'customer' | 'city' | 'requested_week' | 'priority' | 'duration';
export type SortDir = 'asc' | 'desc';

// ─────────────────────────────────────────── Priority level

/** Numeric priority levels: 0 = Normal, 1 = High, 2 = Urgent */
export type PriorityLevel = '0' | '1' | '2';

// ─────────────────────────────────────────── Extended JobReadyToSchedule

/**
 * Extended fields added to JobReadyToSchedule for the pick-jobs page.
 * Requirements: 4.1, 4.8, 4.9, 4.10
 */
export interface JobReadyToScheduleExtended {
  address?: string;
  customer_tags?: CustomerTag[];
  property_type?: 'residential' | 'commercial' | null;
  property_is_hoa?: boolean;
  property_is_subscription?: boolean;
  requested_week?: string;
  notes?: string;
  priority_level?: number;
}

// ─────────────────────────────────────────── Time helpers

/** Convert "HH:MM" to total minutes since midnight. */
export function timeToMinutes(time: string): number {
  const [h, m] = time.split(':').map(Number);
  return h * 60 + m;
}

/** Convert total minutes since midnight to "HH:MM". */
export function minutesToTime(minutes: number): string {
  const h = Math.floor(minutes / 60).toString().padStart(2, '0');
  const m = (minutes % 60).toString().padStart(2, '0');
  return `${h}:${m}`;
}

// ─────────────────────────────────────────── Cascade time computation

export interface JobForTiming {
  job_id: string;
  estimated_duration_minutes?: number;
}

/**
 * Compute start/end times for each selected job.
 *
 * Cascade logic:
 * - Walk forward from `startTime`.
 * - If a job has a per-job override, use it as an anchor and advance
 *   `currentMinutes` to that override's end.
 * - Otherwise, auto-assign sequentially from `currentMinutes`.
 *
 * Requirements: 9.4, 9.5
 */
export function computeJobTimes(
  selectedJobs: JobForTiming[],
  startTime: string,
  defaultDurationMinutes: number,
  perJobTimes: PerJobTimeMap,
): PerJobTimeMap {
  const result: PerJobTimeMap = {};
  let currentMinutes = timeToMinutes(startTime);

  for (const job of selectedJobs) {
    const override = perJobTimes[job.job_id];
    if (override) {
      result[job.job_id] = override;
      // Advance cursor to end of override so subsequent auto jobs cascade from here
      currentMinutes = timeToMinutes(override.end);
    } else {
      const duration = job.estimated_duration_minutes ?? defaultDurationMinutes;
      const endMinutes = currentMinutes + duration;
      result[job.job_id] = {
        start: minutesToTime(currentMinutes),
        end: minutesToTime(endMinutes),
      };
      currentMinutes = endMinutes;
    }
  }

  return result;
}
