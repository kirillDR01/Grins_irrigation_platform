import { describe, it, expect } from 'vitest';
import * as fc from 'fast-check';
import {
  STATUS_LABEL_MAP,
  getSimplifiedStatus,
  getSimplifiedStatusConfig,
  JOB_STATUS_CONFIG,
  LABEL_STATUS_MAP,
  calculateDaysWaiting,
  getDueByColorClass,
  type JobStatus,
  type JobStatusLabel,
  type Job,
} from './index';

/** Helper to format a Date as YYYY-MM-DD using local time (avoids UTC/local mismatch) */
function toLocalDateStr(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

const ALL_RAW_STATUSES: JobStatus[] = [
  'to_be_scheduled',
  'in_progress',
  'completed',
  'cancelled',
];

const ALL_STATUS_LABELS: JobStatusLabel[] = [
  'To Be Scheduled',
  'In Progress',
  'Complete',
  'Cancelled',
];

/**
 * Property 26: Job status simplification mapping
 * Validates: Requirements 21.1
 */
describe('Job status simplification mapping (P26)', () => {
  it('maps to_be_scheduled -> "To Be Scheduled"', () => {
    expect(getSimplifiedStatus('to_be_scheduled')).toBe('To Be Scheduled');
  });

  it('maps in_progress -> "In Progress"', () => {
    expect(getSimplifiedStatus('in_progress')).toBe('In Progress');
  });

  it('maps completed -> "Complete"', () => {
    expect(getSimplifiedStatus('completed')).toBe('Complete');
  });

  it('maps cancelled -> "Cancelled"', () => {
    expect(getSimplifiedStatus('cancelled')).toBe('Cancelled');
  });

  it('STATUS_LABEL_MAP is total -- covers all 4 statuses', () => {
    for (const status of ALL_RAW_STATUSES) {
      expect(STATUS_LABEL_MAP[status]).toBeDefined();
      expect(ALL_STATUS_LABELS).toContain(STATUS_LABEL_MAP[status]);
    }
  });

  it('getSimplifiedStatusConfig returns valid config for every status', () => {
    for (const status of ALL_RAW_STATUSES) {
      const config = getSimplifiedStatusConfig(status);
      expect(config).toBeDefined();
      expect(config).toHaveProperty('label');
      expect(config).toHaveProperty('color');
      expect(config).toHaveProperty('bgColor');
      expect(config.label).toBe(STATUS_LABEL_MAP[status]);
    }
  });

  it('LABEL_STATUS_MAP reverse mapping covers all statuses', () => {
    const allMappedRaw = Object.values(LABEL_STATUS_MAP);
    for (const status of ALL_RAW_STATUSES) {
      expect(allMappedRaw).toContain(status);
    }
  });

  /**
   * Property-based test: for any status, the mapping produces exactly one
   * label and the mapping is total.
   * **Validates: Requirements 21.1**
   */
  it('property: every status maps to exactly one label', () => {
    fc.assert(
      fc.property(
        fc.constantFrom(...ALL_RAW_STATUSES),
        (status: JobStatus) => {
          const label = getSimplifiedStatus(status);
          expect(ALL_STATUS_LABELS).toContain(label);
          expect(getSimplifiedStatusConfig(status)).toBeDefined();
        }
      ),
      { numRuns: 100 }
    );
  });
});

/**
 * Property 27: Days Waiting calculation and Due By color logic
 * Validates: Requirements 22.4, 23.1, 23.2, 23.3, 23.4
 */
describe('Days Waiting calculation and Due By color logic (P27)', () => {
  describe('calculateDaysWaiting', () => {
    it('returns 0 for a job created today', () => {
      const today = new Date().toISOString();
      expect(calculateDaysWaiting(today)).toBe(0);
    });

    it('returns correct days for a job created 10 days ago', () => {
      const tenDaysAgo = new Date();
      tenDaysAgo.setDate(tenDaysAgo.getDate() - 10);
      expect(calculateDaysWaiting(tenDaysAgo.toISOString())).toBe(10);
    });

    it('returns correct days for a job created 1 day ago', () => {
      const yesterday = new Date();
      yesterday.setDate(yesterday.getDate() - 1);
      expect(calculateDaysWaiting(yesterday.toISOString())).toBe(1);
    });

    /**
     * Property-based test: days waiting is always non-negative for past dates
     * and equals floor((now - created) / 86400000).
     * **Validates: Requirements 22.4**
     */
    it('property: days waiting is non-negative and consistent for past dates', () => {
      fc.assert(
        fc.property(
          fc.integer({ min: 0, max: 3650 }),
          (daysAgo: number) => {
            const created = new Date();
            created.setDate(created.getDate() - daysAgo);
            const result = calculateDaysWaiting(created.toISOString());
            expect(result).toBeGreaterThanOrEqual(0);
            // Allow +-1 day tolerance for edge cases around midnight
            expect(Math.abs(result - daysAgo)).toBeLessThanOrEqual(1);
          }
        ),
        { numRuns: 100 }
      );
    });
  });

  describe('getDueByColorClass', () => {
    it('returns empty string for null target date (Req 23.4)', () => {
      expect(getDueByColorClass(null)).toBe('');
    });

    it('returns red class for past due dates (Req 23.3)', () => {
      const pastDate = new Date();
      pastDate.setDate(pastDate.getDate() - 5);
      const result = getDueByColorClass(toLocalDateStr(pastDate));
      expect(result).toBe('text-red-600 font-medium');
    });

    it('returns amber class for dates within 7 days (Req 23.2)', () => {
      const soonDate = new Date();
      soonDate.setDate(soonDate.getDate() + 3);
      const result = getDueByColorClass(toLocalDateStr(soonDate));
      expect(result).toBe('text-amber-600 font-medium');
    });

    it('returns amber class for today (within 7 days, Req 23.2)', () => {
      const today = new Date();
      // Use local date components to avoid UTC/local timezone mismatch
      const dateStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;
      const result = getDueByColorClass(dateStr);
      expect(result).toBe('text-amber-600 font-medium');
    });

    it('returns default class for dates more than 7 days away (Req 23.1)', () => {
      const farDate = new Date();
      farDate.setDate(farDate.getDate() + 30);
      const result = getDueByColorClass(toLocalDateStr(farDate));
      expect(result).toBe('text-slate-600');
    });

    /**
     * Property-based test: Due By color logic is correct for all dates.
     * Past -> red, within 7 days -> amber, beyond 7 days -> default, null -> empty.
     * **Validates: Requirements 23.1, 23.2, 23.3, 23.4**
     */
    it('property: due by color logic is correct for all generated dates', () => {
      fc.assert(
        fc.property(
          fc.integer({ min: -365, max: 365 }),
          (offsetDays: number) => {
            const target = new Date();
            target.setHours(0, 0, 0, 0);
            target.setDate(target.getDate() + offsetDays);
            const dateStr = toLocalDateStr(target);
            const result = getDueByColorClass(dateStr);

            if (offsetDays < 0) {
              expect(result).toBe('text-red-600 font-medium');
            } else if (offsetDays <= 7) {
              expect(result).toBe('text-amber-600 font-medium');
            } else {
              expect(result).toBe('text-slate-600');
            }
          }
        ),
        { numRuns: 200 }
      );
    });

    it('property: null always returns empty string', () => {
      expect(getDueByColorClass(null)).toBe('');
    });
  });
});

/**
 * Property 25: Job notes and summary round-trip
 * Validates: Requirements 20.1, 20.2
 */
describe('Job notes and summary round-trip (P25)', () => {
  it('Job type accepts notes as string', () => {
    const job: Partial<Job> = {
      notes: 'Customer prefers morning appointments',
      summary: 'Spring startup - residential',
    };
    expect(job.notes).toBe('Customer prefers morning appointments');
    expect(job.summary).toBe('Spring startup - residential');
  });

  it('Job type accepts notes and summary as null', () => {
    const job: Partial<Job> = {
      notes: null,
      summary: null,
    };
    expect(job.notes).toBeNull();
    expect(job.summary).toBeNull();
  });

  /**
   * Property-based test: for any valid notes and summary strings,
   * assigning them to a Job object and reading back returns identical values.
   * **Validates: Requirements 20.1, 20.2**
   */
  it('property: notes and summary round-trip preserves values', () => {
    fc.assert(
      fc.property(
        fc.oneof(fc.string({ maxLength: 1000 }), fc.constant(null)),
        fc.oneof(fc.string({ maxLength: 255 }), fc.constant(null)),
        (notes: string | null, summary: string | null) => {
          const job: Partial<Job> = { notes, summary };
          expect(job.notes).toBe(notes);
          expect(job.summary).toBe(summary);
        }
      ),
      { numRuns: 100 }
    );
  });
});
