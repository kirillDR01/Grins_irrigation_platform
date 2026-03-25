/**
 * Tests for calendar event label formatting.
 * Property 31: Calendar event label format
 * Validates: Requirements 28.1
 */

import { describe, it, expect } from 'vitest';
import * as fc from 'fast-check';
import { formatCalendarEventLabel } from './CalendarView';

describe('Calendar event label format (P31)', () => {
  it('formats as "{Staff Name} - {Job Type}" when both are provided', () => {
    expect(formatCalendarEventLabel('John Smith', 'Spring Startup')).toBe(
      'John Smith - Spring Startup',
    );
  });

  it('uses "Job" as fallback when job_type is null', () => {
    expect(formatCalendarEventLabel('John Smith', null)).toBe('John Smith - Job');
  });

  it('uses "Job" as fallback when job_type is undefined', () => {
    expect(formatCalendarEventLabel('John Smith', undefined)).toBe('John Smith - Job');
  });

  it('uses "Job" as fallback when job_type is empty string', () => {
    expect(formatCalendarEventLabel('John Smith', '')).toBe('John Smith - Job');
  });

  it('returns only job type when staff_name is null', () => {
    expect(formatCalendarEventLabel(null, 'Winterization')).toBe('Winterization');
  });

  it('returns only job type when staff_name is undefined', () => {
    expect(formatCalendarEventLabel(undefined, 'Winterization')).toBe('Winterization');
  });

  it('returns only job type when staff_name is empty string', () => {
    expect(formatCalendarEventLabel('', 'Winterization')).toBe('Winterization');
  });

  it('returns "Job" when both staff_name and job_type are null', () => {
    expect(formatCalendarEventLabel(null, null)).toBe('Job');
  });

  it('returns "Job" when both are undefined', () => {
    expect(formatCalendarEventLabel(undefined, undefined)).toBe('Job');
  });

  it('returns "Job" when both are empty strings', () => {
    expect(formatCalendarEventLabel('', '')).toBe('Job');
  });

  /**
   * Property-based test: for any non-empty staff name and non-empty job type,
   * the label is always "{staffName} - {jobType}".
   * **Validates: Requirements 28.1**
   */
  it('property: label is "{Staff Name} - {Job Type}" for all non-empty inputs', () => {
    fc.assert(
      fc.property(
        fc.string({ minLength: 1, maxLength: 100 }).filter((s) => s.trim().length > 0),
        fc.string({ minLength: 1, maxLength: 100 }).filter((s) => s.trim().length > 0),
        (staffName: string, jobType: string) => {
          const label = formatCalendarEventLabel(staffName, jobType);
          expect(label).toBe(`${staffName} - ${jobType}`);
        },
      ),
      { numRuns: 100 },
    );
  });

  /**
   * Property-based test: when staff name is falsy, the label never contains " - " prefix.
   * **Validates: Requirements 28.1**
   */
  it('property: label has no dangling separator when staff name is absent', () => {
    fc.assert(
      fc.property(
        fc.constantFrom(null, undefined, ''),
        fc.oneof(
          fc.string({ minLength: 1, maxLength: 100 }).filter((s) => s.trim().length > 0),
          fc.constantFrom(null, undefined, ''),
        ),
        (staffName: string | null | undefined, jobType: string | null | undefined) => {
          const label = formatCalendarEventLabel(staffName, jobType);
          expect(label).not.toMatch(/^ - /);
          expect(label).not.toBe('');
        },
      ),
      { numRuns: 100 },
    );
  });
});
