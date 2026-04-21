/**
 * Unit tests for pick-jobs.ts pure logic functions.
 * Requirements: 18.10
 */

import { describe, it, expect } from 'vitest';
import {
  timeToMinutes,
  minutesToTime,
  computeJobTimes,
  type JobForTiming,
  type PerJobTimeMap,
} from './pick-jobs';

describe('timeToMinutes', () => {
  it('converts midnight to 0', () => {
    expect(timeToMinutes('00:00')).toBe(0);
  });

  it('converts 8:00 AM to 480', () => {
    expect(timeToMinutes('08:00')).toBe(480);
  });

  it('converts noon to 720', () => {
    expect(timeToMinutes('12:00')).toBe(720);
  });

  it('converts 11:59 PM to 1439', () => {
    expect(timeToMinutes('23:59')).toBe(1439);
  });

  it('handles single-digit hours', () => {
    expect(timeToMinutes('9:30')).toBe(570);
  });

  it('handles single-digit minutes', () => {
    expect(timeToMinutes('08:05')).toBe(485);
  });
});

describe('minutesToTime', () => {
  it('converts 0 to midnight', () => {
    expect(minutesToTime(0)).toBe('00:00');
  });

  it('converts 480 to 8:00 AM', () => {
    expect(minutesToTime(480)).toBe('08:00');
  });

  it('converts 720 to noon', () => {
    expect(minutesToTime(720)).toBe('12:00');
  });

  it('converts 1439 to 11:59 PM', () => {
    expect(minutesToTime(1439)).toBe('23:59');
  });

  it('pads single-digit hours', () => {
    expect(minutesToTime(570)).toBe('09:30');
  });

  it('pads single-digit minutes', () => {
    expect(minutesToTime(485)).toBe('08:05');
  });
});

describe('timeToMinutes and minutesToTime round-trip', () => {
  it('round-trips midnight', () => {
    const time = '00:00';
    expect(minutesToTime(timeToMinutes(time))).toBe(time);
  });

  it('round-trips 8:00 AM', () => {
    const time = '08:00';
    expect(minutesToTime(timeToMinutes(time))).toBe(time);
  });

  it('round-trips 3:45 PM', () => {
    const time = '15:45';
    expect(minutesToTime(timeToMinutes(time))).toBe(time);
  });

  it('round-trips 11:59 PM', () => {
    const time = '23:59';
    expect(minutesToTime(timeToMinutes(time))).toBe(time);
  });
});

describe('computeJobTimes', () => {
  describe('basic cascade without overrides', () => {
    it('computes sequential times for single job', () => {
      const jobs: JobForTiming[] = [
        { job_id: 'j1', estimated_duration_minutes: 60 },
      ];
      const result = computeJobTimes(jobs, '08:00', 60, {});

      expect(result).toEqual({
        j1: { start: '08:00', end: '09:00' },
      });
    });

    it('computes sequential times for multiple jobs', () => {
      const jobs: JobForTiming[] = [
        { job_id: 'j1', estimated_duration_minutes: 60 },
        { job_id: 'j2', estimated_duration_minutes: 45 },
        { job_id: 'j3', estimated_duration_minutes: 30 },
      ];
      const result = computeJobTimes(jobs, '08:00', 60, {});

      expect(result).toEqual({
        j1: { start: '08:00', end: '09:00' },
        j2: { start: '09:00', end: '09:45' },
        j3: { start: '09:45', end: '10:15' },
      });
    });

    it('uses default duration when job has no estimated_duration_minutes', () => {
      const jobs: JobForTiming[] = [
        { job_id: 'j1' },
        { job_id: 'j2' },
      ];
      const result = computeJobTimes(jobs, '08:00', 90, {});

      expect(result).toEqual({
        j1: { start: '08:00', end: '09:30' },
        j2: { start: '09:30', end: '11:00' },
      });
    });

    it('handles mixed durations (some with estimated, some default)', () => {
      const jobs: JobForTiming[] = [
        { job_id: 'j1', estimated_duration_minutes: 30 },
        { job_id: 'j2' },
        { job_id: 'j3', estimated_duration_minutes: 120 },
      ];
      const result = computeJobTimes(jobs, '08:00', 60, {});

      expect(result).toEqual({
        j1: { start: '08:00', end: '08:30' },
        j2: { start: '08:30', end: '09:30' },
        j3: { start: '09:30', end: '11:30' },
      });
    });
  });

  describe('cascade with overrides', () => {
    it('respects single override and cascades subsequent jobs from override end', () => {
      const jobs: JobForTiming[] = [
        { job_id: 'j1', estimated_duration_minutes: 60 },
        { job_id: 'j2', estimated_duration_minutes: 60 },
        { job_id: 'j3', estimated_duration_minutes: 60 },
      ];
      const overrides: PerJobTimeMap = {
        j2: { start: '10:00', end: '11:00' },
      };
      const result = computeJobTimes(jobs, '08:00', 60, overrides);

      expect(result).toEqual({
        j1: { start: '08:00', end: '09:00' },
        j2: { start: '10:00', end: '11:00' }, // override
        j3: { start: '11:00', end: '12:00' }, // cascades from j2 override end
      });
    });

    it('respects multiple overrides as anchors', () => {
      const jobs: JobForTiming[] = [
        { job_id: 'j1', estimated_duration_minutes: 60 },
        { job_id: 'j2', estimated_duration_minutes: 60 },
        { job_id: 'j3', estimated_duration_minutes: 60 },
        { job_id: 'j4', estimated_duration_minutes: 60 },
      ];
      const overrides: PerJobTimeMap = {
        j1: { start: '08:00', end: '09:00' },
        j3: { start: '11:00', end: '12:00' },
      };
      const result = computeJobTimes(jobs, '08:00', 60, overrides);

      expect(result).toEqual({
        j1: { start: '08:00', end: '09:00' }, // override
        j2: { start: '09:00', end: '10:00' }, // cascades from j1 override end
        j3: { start: '11:00', end: '12:00' }, // override
        j4: { start: '12:00', end: '13:00' }, // cascades from j3 override end
      });
    });

    it('handles override at the start', () => {
      const jobs: JobForTiming[] = [
        { job_id: 'j1', estimated_duration_minutes: 60 },
        { job_id: 'j2', estimated_duration_minutes: 60 },
      ];
      const overrides: PerJobTimeMap = {
        j1: { start: '09:00', end: '10:00' },
      };
      const result = computeJobTimes(jobs, '08:00', 60, overrides);

      expect(result).toEqual({
        j1: { start: '09:00', end: '10:00' }, // override
        j2: { start: '10:00', end: '11:00' }, // cascades from j1 override end
      });
    });

    it('handles override at the end', () => {
      const jobs: JobForTiming[] = [
        { job_id: 'j1', estimated_duration_minutes: 60 },
        { job_id: 'j2', estimated_duration_minutes: 60 },
      ];
      const overrides: PerJobTimeMap = {
        j2: { start: '10:00', end: '11:00' },
      };
      const result = computeJobTimes(jobs, '08:00', 60, overrides);

      expect(result).toEqual({
        j1: { start: '08:00', end: '09:00' },
        j2: { start: '10:00', end: '11:00' }, // override
      });
    });

    it('handles all jobs overridden', () => {
      const jobs: JobForTiming[] = [
        { job_id: 'j1', estimated_duration_minutes: 60 },
        { job_id: 'j2', estimated_duration_minutes: 60 },
      ];
      const overrides: PerJobTimeMap = {
        j1: { start: '08:00', end: '09:00' },
        j2: { start: '10:00', end: '11:00' },
      };
      const result = computeJobTimes(jobs, '08:00', 60, overrides);

      expect(result).toEqual({
        j1: { start: '08:00', end: '09:00' },
        j2: { start: '10:00', end: '11:00' },
      });
    });
  });

  describe('edge cases', () => {
    it('handles empty job list', () => {
      const result = computeJobTimes([], '08:00', 60, {});
      expect(result).toEqual({});
    });

    it('handles single job with override', () => {
      const jobs: JobForTiming[] = [
        { job_id: 'j1', estimated_duration_minutes: 60 },
      ];
      const overrides: PerJobTimeMap = {
        j1: { start: '10:00', end: '11:00' },
      };
      const result = computeJobTimes(jobs, '08:00', 60, overrides);

      expect(result).toEqual({
        j1: { start: '10:00', end: '11:00' },
      });
    });

    it('handles zero duration job', () => {
      const jobs: JobForTiming[] = [
        { job_id: 'j1', estimated_duration_minutes: 0 },
        { job_id: 'j2', estimated_duration_minutes: 60 },
      ];
      const result = computeJobTimes(jobs, '08:00', 60, {});

      expect(result).toEqual({
        j1: { start: '08:00', end: '08:00' },
        j2: { start: '08:00', end: '09:00' },
      });
    });

    it('handles very long duration', () => {
      const jobs: JobForTiming[] = [
        { job_id: 'j1', estimated_duration_minutes: 480 }, // 8 hours
      ];
      const result = computeJobTimes(jobs, '08:00', 60, {});

      expect(result).toEqual({
        j1: { start: '08:00', end: '16:00' },
      });
    });

    it('handles start time at end of day', () => {
      const jobs: JobForTiming[] = [
        { job_id: 'j1', estimated_duration_minutes: 30 },
      ];
      const result = computeJobTimes(jobs, '23:30', 60, {});

      expect(result).toEqual({
        j1: { start: '23:30', end: '24:00' },
      });
    });

    it('handles override with gap before next auto job', () => {
      const jobs: JobForTiming[] = [
        { job_id: 'j1', estimated_duration_minutes: 60 },
        { job_id: 'j2', estimated_duration_minutes: 60 },
        { job_id: 'j3', estimated_duration_minutes: 60 },
      ];
      const overrides: PerJobTimeMap = {
        j2: { start: '10:00', end: '10:30' }, // shorter than estimated
      };
      const result = computeJobTimes(jobs, '08:00', 60, overrides);

      expect(result).toEqual({
        j1: { start: '08:00', end: '09:00' },
        j2: { start: '10:00', end: '10:30' }, // override
        j3: { start: '10:30', end: '11:30' }, // cascades from j2 override end
      });
    });

    it('handles override with longer duration than estimated', () => {
      const jobs: JobForTiming[] = [
        { job_id: 'j1', estimated_duration_minutes: 60 },
        { job_id: 'j2', estimated_duration_minutes: 60 },
        { job_id: 'j3', estimated_duration_minutes: 60 },
      ];
      const overrides: PerJobTimeMap = {
        j2: { start: '10:00', end: '12:00' }, // 2 hours instead of 1
      };
      const result = computeJobTimes(jobs, '08:00', 60, overrides);

      expect(result).toEqual({
        j1: { start: '08:00', end: '09:00' },
        j2: { start: '10:00', end: '12:00' }, // override
        j3: { start: '12:00', end: '13:00' }, // cascades from j2 override end
      });
    });
  });

  describe('overlap detection scenarios', () => {
    it('detects when override end equals start (invalid)', () => {
      const jobs: JobForTiming[] = [
        { job_id: 'j1', estimated_duration_minutes: 60 },
      ];
      const overrides: PerJobTimeMap = {
        j1: { start: '08:00', end: '08:00' },
      };
      const result = computeJobTimes(jobs, '08:00', 60, overrides);

      // Function still computes, but UI should detect end <= start
      expect(result.j1.start).toBe('08:00');
      expect(result.j1.end).toBe('08:00');
      expect(timeToMinutes(result.j1.end) <= timeToMinutes(result.j1.start)).toBe(true);
    });

    it('detects when override end is before start (invalid)', () => {
      const jobs: JobForTiming[] = [
        { job_id: 'j1', estimated_duration_minutes: 60 },
      ];
      const overrides: PerJobTimeMap = {
        j1: { start: '10:00', end: '09:00' },
      };
      const result = computeJobTimes(jobs, '08:00', 60, overrides);

      // Function still computes, but UI should detect end < start
      expect(result.j1.start).toBe('10:00');
      expect(result.j1.end).toBe('09:00');
      expect(timeToMinutes(result.j1.end) < timeToMinutes(result.j1.start)).toBe(true);
    });

    it('validates no overlaps in normal cascade', () => {
      const jobs: JobForTiming[] = [
        { job_id: 'j1', estimated_duration_minutes: 60 },
        { job_id: 'j2', estimated_duration_minutes: 60 },
        { job_id: 'j3', estimated_duration_minutes: 60 },
      ];
      const result = computeJobTimes(jobs, '08:00', 60, {});

      // Verify each job's end equals next job's start (no gaps, no overlaps)
      expect(result.j1.end).toBe(result.j2.start);
      expect(result.j2.end).toBe(result.j3.start);
    });

    it('validates no overlaps with overrides', () => {
      const jobs: JobForTiming[] = [
        { job_id: 'j1', estimated_duration_minutes: 60 },
        { job_id: 'j2', estimated_duration_minutes: 60 },
        { job_id: 'j3', estimated_duration_minutes: 60 },
      ];
      const overrides: PerJobTimeMap = {
        j2: { start: '10:00', end: '11:00' },
      };
      const result = computeJobTimes(jobs, '08:00', 60, overrides);

      // Verify j2 override end equals j3 start
      expect(result.j2.end).toBe(result.j3.start);
      // Verify all end > start
      expect(timeToMinutes(result.j1.end) > timeToMinutes(result.j1.start)).toBe(true);
      expect(timeToMinutes(result.j2.end) > timeToMinutes(result.j2.start)).toBe(true);
      expect(timeToMinutes(result.j3.end) > timeToMinutes(result.j3.start)).toBe(true);
    });
  });
});
