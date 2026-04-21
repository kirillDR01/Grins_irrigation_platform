import { describe, it, expect, vi, afterEach } from 'vitest';
import { renderHook } from '@testing-library/react';
import * as fc from 'fast-check';
import { useStageAge, countStuck } from './useStageAge';
import type { SalesEntry, SalesEntryStatus } from '../types/pipeline';
import { AGE_THRESHOLDS } from '../types/pipeline';

// ─── helpers ────────────────────────────────────────────────────────────────

function makeEntry(
  status: SalesEntryStatus,
  daysAgo: number,
  id = 'e1',
): SalesEntry {
  const ref = new Date(Date.now() - daysAgo * 86_400_000).toISOString();
  return {
    id,
    customer_id: 'c1',
    property_id: null,
    lead_id: null,
    job_type: null,
    status,
    last_contact_date: null,
    notes: null,
    override_flag: false,
    closed_reason: null,
    signwell_document_id: null,
    created_at: ref,
    updated_at: ref,
    customer_name: null,
    customer_phone: null,
    property_address: null,
  };
}

const NON_TERMINAL_STATUSES: SalesEntryStatus[] = [
  'schedule_estimate',
  'estimate_scheduled',
  'send_estimate',
  'pending_approval',
  'send_contract',
];

// ─── unit tests ─────────────────────────────────────────────────────────────

describe('useStageAge', () => {
  afterEach(() => vi.restoreAllMocks());

  it('returns fresh for terminal closed_won', () => {
    const { result } = renderHook(() => useStageAge(makeEntry('closed_won', 100)));
    expect(result.current).toEqual({ days: 0, bucket: 'fresh', needsFollowup: false });
  });

  it('returns fresh for terminal closed_lost', () => {
    const { result } = renderHook(() => useStageAge(makeEntry('closed_lost', 100)));
    expect(result.current).toEqual({ days: 0, bucket: 'fresh', needsFollowup: false });
  });

  it('maps estimate_scheduled to schedule_estimate thresholds', () => {
    const thresholds = AGE_THRESHOLDS['schedule_estimate'];
    // Just past freshMax → stale
    const { result } = renderHook(() =>
      useStageAge(makeEntry('estimate_scheduled', thresholds.freshMax + 1)),
    );
    expect(result.current.bucket).toBe('stale');
  });

  it('returns fresh when days <= freshMax', () => {
    const { result } = renderHook(() =>
      useStageAge(makeEntry('schedule_estimate', 2)),
    );
    expect(result.current.bucket).toBe('fresh');
    expect(result.current.needsFollowup).toBe(false);
  });

  it('returns stale when days > freshMax and <= staleMax', () => {
    const { result } = renderHook(() =>
      useStageAge(makeEntry('schedule_estimate', 5)),
    );
    expect(result.current.bucket).toBe('stale');
    expect(result.current.needsFollowup).toBe(false);
  });

  it('returns stuck when days > staleMax', () => {
    const { result } = renderHook(() =>
      useStageAge(makeEntry('schedule_estimate', 8)),
    );
    expect(result.current.bucket).toBe('stuck');
    expect(result.current.needsFollowup).toBe(true);
  });

  it('pending_approval thresholds: fresh ≤4, stale ≤10, stuck >10', () => {
    const fresh = renderHook(() => useStageAge(makeEntry('pending_approval', 3)));
    expect(fresh.result.current.bucket).toBe('fresh');

    const stale = renderHook(() => useStageAge(makeEntry('pending_approval', 7)));
    expect(stale.result.current.bucket).toBe('stale');

    const stuck = renderHook(() => useStageAge(makeEntry('pending_approval', 11)));
    expect(stuck.result.current.bucket).toBe('stuck');
  });

  it('closed_won thresholds never go stale', () => {
    // closed_won is terminal → always returns fresh/0
    const { result } = renderHook(() => useStageAge(makeEntry('closed_won', 500)));
    expect(result.current).toEqual({ days: 0, bucket: 'fresh', needsFollowup: false });
  });
});

// ─── countStuck unit tests ───────────────────────────────────────────────────

describe('countStuck', () => {
  it('returns 0 for empty array', () => {
    expect(countStuck([])).toBe(0);
  });

  it('ignores terminal statuses', () => {
    const rows = [makeEntry('closed_won', 500), makeEntry('closed_lost', 500)];
    expect(countStuck(rows)).toBe(0);
  });

  it('counts stuck entries correctly', () => {
    const rows = [
      makeEntry('schedule_estimate', 8, 'a'),  // stuck (>7)
      makeEntry('schedule_estimate', 2, 'b'),  // fresh
      makeEntry('pending_approval', 11, 'c'),  // stuck (>10)
      makeEntry('closed_won', 100, 'd'),        // terminal
    ];
    expect(countStuck(rows)).toBe(2);
  });
});

// ─── Property 2: Age Bucket Classification ───────────────────────────────────

describe('Property 2: Age Bucket Classification', () => {
  it('bucket matches threshold rules for non-terminal statuses', () => {
    fc.assert(
      fc.property(
        fc.constantFrom(...NON_TERMINAL_STATUSES),
        fc.integer({ min: 0, max: 30 }),
        (status, daysAgo) => {
          const entry = makeEntry(status, daysAgo);
          const { result } = renderHook(() => useStageAge(entry));
          const { days, bucket, needsFollowup } = result.current;

          // (a) days equals floor((now - ref) / 86_400_000)
          const ref = new Date(entry.updated_at).getTime();
          const expectedDays = Math.floor((Date.now() - ref) / 86_400_000);
          // Allow ±1 due to timing
          expect(Math.abs(days - expectedDays)).toBeLessThanOrEqual(1);

          // (b) bucket matches threshold rules
          const stageKey =
            status === 'estimate_scheduled' ? 'schedule_estimate' : status;
          const thresholds = AGE_THRESHOLDS[stageKey as keyof typeof AGE_THRESHOLDS];
          if (days > thresholds.staleMax) {
            expect(bucket).toBe('stuck');
          } else if (days > thresholds.freshMax) {
            expect(bucket).toBe('stale');
          } else {
            expect(bucket).toBe('fresh');
          }

          // (c) needsFollowup === (bucket === 'stuck')
          expect(needsFollowup).toBe(bucket === 'stuck');
        },
      ),
      { numRuns: 100 },
    );
  });

  it('terminal statuses always return { days: 0, bucket: fresh, needsFollowup: false }', () => {
    fc.assert(
      fc.property(
        fc.constantFrom('closed_won' as SalesEntryStatus, 'closed_lost' as SalesEntryStatus),
        fc.integer({ min: 0, max: 500 }),
        (status, daysAgo) => {
          const entry = makeEntry(status, daysAgo);
          const { result } = renderHook(() => useStageAge(entry));
          expect(result.current).toEqual({ days: 0, bucket: 'fresh', needsFollowup: false });
        },
      ),
      { numRuns: 100 },
    );
  });
});

// ─── Property 4: countStuck Correctness ─────────────────────────────────────

describe('Property 4: countStuck Correctness', () => {
  it('count matches manual threshold computation', () => {
    const allStatuses: SalesEntryStatus[] = [
      'schedule_estimate',
      'estimate_scheduled',
      'send_estimate',
      'pending_approval',
      'send_contract',
      'closed_won',
      'closed_lost',
    ];

    fc.assert(
      fc.property(
        fc.array(
          fc.record({
            status: fc.constantFrom(...allStatuses),
            daysAgo: fc.integer({ min: 0, max: 30 }),
            id: fc.uuid(),
          }),
          { minLength: 0, maxLength: 20 },
        ),
        (items) => {
          const rows = items.map(({ status, daysAgo, id }) =>
            makeEntry(status, daysAgo, id),
          );

          // Manual computation
          let expected = 0;
          for (const r of rows) {
            if (r.status === 'closed_won' || r.status === 'closed_lost') continue;
            const stageKey =
              r.status === 'estimate_scheduled' ? 'schedule_estimate' : r.status;
            const thresholds = AGE_THRESHOLDS[stageKey as keyof typeof AGE_THRESHOLDS];
            const ref = new Date(r.updated_at).getTime();
            const days = Math.floor((Date.now() - ref) / 86_400_000);
            if (days > thresholds.staleMax) expected++;
          }

          expect(countStuck(rows)).toBe(expected);
        },
      ),
      { numRuns: 100 },
    );
  });
});
