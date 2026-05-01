/**
 * Unit + property-based tests for the resource-timeline utils.
 *
 * Property: assigned lanes never share a time interval — interval-graph
 * coloring invariant. Verified across 100 random interval sets.
 */

import { describe, it, expect } from 'vitest';
import * as fc from 'fast-check';
import {
  DAY_END_MIN,
  DAY_SPAN_MIN,
  DAY_START_MIN,
  assignLanes,
  formatDayLabel,
  formatTimeRange,
  getInitials,
  minutesToPercent,
  timeToMinutes,
} from './utils';

describe('timeToMinutes', () => {
  it('parses HH:MM:SS', () => {
    expect(timeToMinutes('06:00:00')).toBe(360);
    expect(timeToMinutes('20:00:00')).toBe(1200);
  });

  it('parses HH:MM (no seconds)', () => {
    expect(timeToMinutes('14:30')).toBe(870);
    expect(timeToMinutes('00:00')).toBe(0);
  });

  it('handles single-digit hours', () => {
    expect(timeToMinutes('9:15')).toBe(555);
  });
});

describe('minutesToPercent', () => {
  it('maps DAY_START_MIN to 0%', () => {
    expect(minutesToPercent(DAY_START_MIN)).toBe(0);
  });

  it('maps DAY_END_MIN to 100%', () => {
    expect(minutesToPercent(DAY_END_MIN)).toBe(100);
  });

  it('maps midpoint to ~50%', () => {
    expect(minutesToPercent(DAY_START_MIN + DAY_SPAN_MIN / 2)).toBeCloseTo(50, 5);
  });

  it('clamps below 0% to 0%', () => {
    expect(minutesToPercent(0)).toBe(0);
  });

  it('clamps above 100% to 100%', () => {
    expect(minutesToPercent(DAY_END_MIN + 60)).toBe(100);
  });
});

describe('formatTimeRange', () => {
  it('formats HH:MM:SS to short form with en-dash', () => {
    expect(formatTimeRange('08:00:00', '09:30:00')).toBe('8:00\u20139:30');
  });

  it('keeps two-digit hours', () => {
    expect(formatTimeRange('14:00:00', '15:45:00')).toBe('14:00\u201315:45');
  });

  it('strips a single leading zero from the hour', () => {
    expect(formatTimeRange('06:15:00', '07:00:00')).toBe('6:15\u20137:00');
  });
});

describe('formatDayLabel', () => {
  it("formats '2026-04-27' (Monday) as 'MON 4/27'", () => {
    expect(formatDayLabel('2026-04-27')).toBe('MON 4/27');
  });

  it('uppercases the weekday', () => {
    // 2026-04-30 is a Thursday
    expect(formatDayLabel('2026-04-30')).toBe('THU 4/30');
  });
});

describe('getInitials', () => {
  it('returns first+last initials for two-word names', () => {
    expect(getInitials('Mike Davis')).toBe('MD');
  });

  it('returns single initial for single-word names', () => {
    expect(getInitials('Madonna')).toBe('M');
  });

  it('returns ? for empty string', () => {
    expect(getInitials('')).toBe('?');
  });

  it('returns ? for whitespace-only string', () => {
    expect(getInitials('   ')).toBe('?');
  });

  it('handles names with extra whitespace', () => {
    expect(getInitials('  Sarah   Kim  ')).toBe('SK');
  });

  it('takes first+last on three-word names', () => {
    expect(getInitials('Carlos M Rivera')).toBe('CR');
  });
});

describe('assignLanes', () => {
  it('puts non-overlapping intervals all on lane 0', () => {
    const items = [
      { start: 360, end: 420 },
      { start: 420, end: 480 },
      { start: 600, end: 660 },
    ];
    const result = assignLanes(items);
    expect(result.every((i) => i.lane === 0)).toBe(true);
  });

  it('puts overlapping intervals on different lanes', () => {
    const items = [
      { start: 360, end: 480 },
      { start: 420, end: 540 },
    ];
    const result = assignLanes(items);
    expect(new Set(result.map((i) => i.lane)).size).toBe(2);
  });

  it('reuses a lane after its previous item ends', () => {
    const items = [
      { start: 360, end: 420 }, // lane 0
      { start: 380, end: 440 }, // lane 1 (overlaps)
      { start: 450, end: 510 }, // lane 0 again (free)
    ];
    const result = assignLanes(items);
    const sorted = [...result].sort((a, b) => a.start - b.start);
    expect(sorted[0]?.lane).toBe(0);
    expect(sorted[1]?.lane).toBe(1);
    expect(sorted[2]?.lane).toBe(0);
  });

  it('returns empty array for empty input', () => {
    expect(assignLanes([])).toEqual([]);
  });

  /**
   * Property: for any random interval set within the visible day, no two
   * items with overlapping `[start, end)` end up sharing a lane.
   */
  it('property: no two overlapping intervals share a lane', () => {
    const intervalArb = fc
      .tuple(
        fc.integer({ min: DAY_START_MIN, max: DAY_END_MIN - 1 }),
        fc.integer({ min: 1, max: 120 })
      )
      .map(([start, dur]) => ({
        start,
        end: Math.min(start + dur, DAY_END_MIN),
      }));

    fc.assert(
      fc.property(fc.array(intervalArb, { maxLength: 50 }), (items) => {
        const placed = assignLanes(items);
        // Group by lane, then for each lane verify items are sorted and
        // non-overlapping.
        const byLane = new Map<number, typeof placed>();
        for (const item of placed) {
          const arr = byLane.get(item.lane) ?? [];
          arr.push(item);
          byLane.set(item.lane, arr);
        }
        for (const arr of byLane.values()) {
          const sorted = [...arr].sort((a, b) => a.start - b.start);
          for (let i = 1; i < sorted.length; i++) {
            const prev = sorted[i - 1];
            const curr = sorted[i];
            if (prev && curr) {
              expect(curr.start).toBeGreaterThanOrEqual(prev.end);
            }
          }
        }
      }),
      { numRuns: 100 }
    );
  });

  /**
   * Property: any non-overlapping interval set collapses to a single lane.
   */
  it('property: pre-sorted non-overlapping intervals all land on lane 0', () => {
    const nonOverlappingArb = fc
      .array(fc.integer({ min: 5, max: 60 }), { minLength: 1, maxLength: 20 })
      .map((durs) => {
        let cursor = DAY_START_MIN;
        const items: Array<{ start: number; end: number }> = [];
        for (const d of durs) {
          if (cursor + d > DAY_END_MIN) break;
          items.push({ start: cursor, end: cursor + d });
          cursor = cursor + d; // back-to-back, edge-touching = non-overlapping
        }
        return items;
      });

    fc.assert(
      fc.property(nonOverlappingArb, (items) => {
        const placed = assignLanes(items);
        return placed.every((i) => i.lane === 0);
      }),
      { numRuns: 100 }
    );
  });
});
