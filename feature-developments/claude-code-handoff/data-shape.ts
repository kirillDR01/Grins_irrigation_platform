/**
 * Data shapes for the /schedule/pick-jobs page.
 *
 * Most types re-export from existing `features/schedule/types` —
 * don't duplicate the server contracts. This file only adds the
 * page-local state shapes (facets, per-job overrides) and a mock
 * data constant for local development / Storybook / tests.
 */

// Re-export existing server contract — do NOT redefine.
// Adjust the path if your project uses a different alias.
export type { JobReadyToSchedule } from '@/features/schedule/types';
export type { Staff } from '@/features/staff/types';

// ───────────────────────────────────────────────────────────────────
// Page-local state shapes
// ───────────────────────────────────────────────────────────────────

export type PriorityLevel = 'high' | 'normal';

/** Facet groups rendered in the left rail. */
export interface FacetState {
  city:          Set<string>;
  tags:          Set<string>;          // normalized lowercase (e.g. 'vip', 'dog-on-site')
  jobType:       Set<string>;
  priority:      Set<PriorityLevel>;
  requestedWeek: Set<string>;          // ISO date of Monday, e.g. '2026-04-27'
}

export const initialFacets: FacetState = {
  city:          new Set(),
  tags:          new Set(),
  jobType:       new Set(),
  priority:      new Set(),
  requestedWeek: new Set(),
};

export interface PerJobTime {
  start: string; // 'HH:MM'
  end:   string; // 'HH:MM'
}

export type PerJobTimeMap = Record<string, PerJobTime>;

export type SortKey = 'customer' | 'city' | 'requested_week' | 'priority' | 'duration';
export type SortDir = 'asc' | 'desc';

// ───────────────────────────────────────────────────────────────────
// Mock data — local development only. Delete this export before prod.
// Shape mirrors JobReadyToSchedule from features/schedule/types.
// ───────────────────────────────────────────────────────────────────

export const MOCK_JOBS_READY_TO_SCHEDULE = [
  {
    job_id:   'j-001',
    customer_name: 'Cinda Baxter',
    address:  '1842 Harold Ave',
    city:     'Golden Valley',
    job_type: 'fall_winterization',
    tags:     ['vip', 'prepaid'],
    priority: 'high',
    priority_level: 1,
    requested_week: '2026-04-27',
    estimated_duration_minutes: 60,
    requires_equipment: ['ladder 20ft'],
    notes: 'Gate code 4412. Owner prefers mornings before 10am. Dog is friendly but skittish.',
  },
  {
    job_id:   'j-002',
    customer_name: 'Kaylee Traynor',
    address:  '611 Vicksburg Ln',
    city:     'Plymouth',
    job_type: 'spring_startup',
    tags:     ['commercial'],
    priority: 'high',
    priority_level: 1,
    requested_week: '2026-04-27',
    estimated_duration_minutes: 60,
    requires_equipment: [],
    notes: 'Commercial property, check-in with front desk.',
  },
  // Add more mock rows as needed for local dev.
] as const;
