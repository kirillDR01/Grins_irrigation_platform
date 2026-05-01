import { describe, it, expect } from 'vitest';
import { formatTimeWindow } from './formatTimeWindow';

describe('formatTimeWindow', () => {
  it('formats a morning window', () => {
    expect(formatTimeWindow('08:00:00', '09:25:00')).toBe('8:00 AM – 9:25 AM');
  });

  it('formats an afternoon window', () => {
    expect(formatTimeWindow('13:00:00', '14:15:00')).toBe('1:00 PM – 2:15 PM');
  });

  it('handles midnight (00:00) → 12:00 AM', () => {
    expect(formatTimeWindow('00:00:00', '00:30:00')).toBe('12:00 AM – 12:30 AM');
  });

  it('handles noon (12:00) → 12:00 PM', () => {
    expect(formatTimeWindow('12:00:00', '13:00:00')).toBe('12:00 PM – 1:00 PM');
  });

  it('zero-pads minute values below ten', () => {
    expect(formatTimeWindow('09:05:00', '09:50:00')).toBe('9:05 AM – 9:50 AM');
  });

  it('omits zero-minute padding for o\'clock times', () => {
    expect(formatTimeWindow('07:00:00', '20:00:00')).toBe('7:00 AM – 8:00 PM');
  });

  it('accepts `HH:MM` (no seconds) input', () => {
    expect(formatTimeWindow('08:00', '09:30')).toBe('8:00 AM – 9:30 AM');
  });
});
