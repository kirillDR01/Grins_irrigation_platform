import { describe, it, expect } from 'vitest';
import fc from 'fast-check';
import {
  minToHHMMSS,
  hhmmssToMin,
  startOfWeek,
  isPastSlot,
  detectConflicts,
  eventToBlock,
  formatShortName,
} from './scheduleVisitUtils';
import type { EstimateBlock, SalesCalendarEvent } from '../types/pipeline';

describe('scheduleVisitUtils', () => {
  describe('minToHHMMSS', () => {
    it('formats a few canonical points', () => {
      expect(minToHHMMSS(0)).toBe('00:00:00');
      expect(minToHHMMSS(840)).toBe('14:00:00');
      expect(minToHHMMSS(1439)).toBe('23:59:00');
    });
  });

  describe('hhmmssToMin', () => {
    it('parses HH:MM:SS and HH:MM forms', () => {
      expect(hhmmssToMin('00:00:00')).toBe(0);
      expect(hhmmssToMin('14:00:00')).toBe(840);
      expect(hhmmssToMin('23:59')).toBe(1439);
    });
  });

  it('round-trips minToHHMMSS ↔ hhmmssToMin (property)', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 0, max: 1439 }),
        (m) => hhmmssToMin(minToHHMMSS(m)) === m,
      ),
    );
  });

  describe('startOfWeek', () => {
    it('returns Monday for any input day-of-week', () => {
      // Sun Apr 26 2026 → previous Monday Apr 20.
      const sun = new Date(2026, 3, 26);
      expect(startOfWeek(sun).getDate()).toBe(20);
      expect(startOfWeek(sun).getDay()).toBe(1);

      // Mon Apr 20 → itself.
      const mon = new Date(2026, 3, 20);
      expect(startOfWeek(mon).getDate()).toBe(20);

      // Wed Apr 22 → Mon Apr 20.
      const wed = new Date(2026, 3, 22);
      expect(startOfWeek(wed).getDate()).toBe(20);

      // Fri Apr 24 → Mon Apr 20.
      const fri = new Date(2026, 3, 24);
      expect(startOfWeek(fri).getDate()).toBe(20);

      // Sat Apr 25 → Mon Apr 20.
      const sat = new Date(2026, 3, 25);
      expect(startOfWeek(sat).getDate()).toBe(20);
    });
  });

  describe('isPastSlot', () => {
    const now = new Date(2026, 3, 21, 10, 30); // Tue Apr 21, 10:30 AM
    const today = new Date(2026, 3, 21);
    const yesterday = new Date(2026, 3, 20);
    const tomorrow = new Date(2026, 3, 22);

    it('yesterday is always past', () => {
      expect(isPastSlot(yesterday, 14 * 60, now)).toBe(true);
    });

    it("today's earlier minute is past", () => {
      expect(isPastSlot(today, 9 * 60, now)).toBe(true);
    });

    it("today's future minute is not past", () => {
      expect(isPastSlot(today, 14 * 60, now)).toBe(false);
    });

    it('tomorrow is not past', () => {
      expect(isPastSlot(tomorrow, 6 * 60, now)).toBe(false);
    });
  });

  describe('detectConflicts', () => {
    const a: EstimateBlock = {
      id: 'a',
      date: '2026-05-05',
      startMin: 14 * 60,
      endMin: 15 * 60,
      customerName: 'A',
      jobSummary: '',
      assignedToUserId: null,
    };

    it('returns overlap on same date', () => {
      const conflicts = detectConflicts(
        { date: '2026-05-05', start: 14 * 60 + 30, end: 15 * 60 + 30 },
        [a],
      );
      expect(conflicts).toHaveLength(1);
    });

    it('returns empty for non-overlap on same date', () => {
      const conflicts = detectConflicts(
        { date: '2026-05-05', start: 16 * 60, end: 17 * 60 },
        [a],
      );
      expect(conflicts).toHaveLength(0);
    });

    it('returns empty across dates', () => {
      const conflicts = detectConflicts(
        { date: '2026-05-06', start: 14 * 60, end: 15 * 60 },
        [a],
      );
      expect(conflicts).toHaveLength(0);
    });

    it('treats touching boundaries as non-overlap (exclusive end)', () => {
      const conflicts = detectConflicts(
        { date: '2026-05-05', start: 15 * 60, end: 16 * 60 },
        [a],
      );
      expect(conflicts).toHaveLength(0);
    });
  });

  describe('eventToBlock', () => {
    const baseEvent: SalesCalendarEvent = {
      id: 'e1',
      sales_entry_id: 's1',
      customer_id: 'c1',
      title: 'Estimate',
      scheduled_date: '2026-05-05',
      start_time: null,
      end_time: null,
      notes: null,
      assigned_to_user_id: null,
      created_at: '',
      updated_at: '',
    };

    it('null start/end → full-day default 0..1440', () => {
      const block = eventToBlock(baseEvent, 'A', 'B');
      expect(block.startMin).toBe(0);
      expect(block.endMin).toBe(24 * 60);
    });

    it('populated start/end → minute math', () => {
      const block = eventToBlock(
        { ...baseEvent, start_time: '14:00:00', end_time: '15:30:00' },
        'A',
        'B',
      );
      expect(block.startMin).toBe(14 * 60);
      expect(block.endMin).toBe(15 * 60 + 30);
    });
  });

  describe('formatShortName', () => {
    it('First Last → First L.', () => {
      expect(formatShortName('Viktor Petrov')).toBe('Viktor P.');
    });
    it('single name → as-is', () => {
      expect(formatShortName('Cher')).toBe('Cher');
    });
    it('empty → Customer', () => {
      expect(formatShortName('')).toBe('Customer');
    });
    it('null → Customer', () => {
      expect(formatShortName(null)).toBe('Customer');
    });
    it('extra whitespace handled → First M.', () => {
      expect(formatShortName('  Mary  Anne  Smith  ')).toBe('Mary A.');
    });
  });
});
