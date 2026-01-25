import { describe, it, expect } from 'vitest';
import {
  STAFF_COLORS,
  UNASSIGNED_COLOR,
  DEFAULT_COLOR,
  getStaffColor,
  getColoredStaffNames,
} from './staffColors';

describe('staffColors', () => {
  describe('STAFF_COLORS', () => {
    it('has Viktor as red', () => {
      expect(STAFF_COLORS.Viktor).toBe('#EF4444');
    });

    it('has Vas as blue', () => {
      expect(STAFF_COLORS.Vas).toBe('#3B82F6');
    });

    it('has Dad as green', () => {
      expect(STAFF_COLORS.Dad).toBe('#22C55E');
    });

    it('has Gennadiy as green (alias for Dad)', () => {
      expect(STAFF_COLORS.Gennadiy).toBe('#22C55E');
    });

    it('has Steven as amber', () => {
      expect(STAFF_COLORS.Steven).toBe('#F59E0B');
    });

    it('has Vitallik as purple', () => {
      expect(STAFF_COLORS.Vitallik).toBe('#8B5CF6');
    });
  });

  describe('getStaffColor', () => {
    it('returns correct color for Viktor', () => {
      expect(getStaffColor('Viktor')).toBe('#EF4444');
    });

    it('returns correct color for Vas', () => {
      expect(getStaffColor('Vas')).toBe('#3B82F6');
    });

    it('returns correct color for Dad', () => {
      expect(getStaffColor('Dad')).toBe('#22C55E');
    });

    it('returns correct color for Steven', () => {
      expect(getStaffColor('Steven')).toBe('#F59E0B');
    });

    it('returns correct color for Vitallik', () => {
      expect(getStaffColor('Vitallik')).toBe('#8B5CF6');
    });

    it('returns DEFAULT_COLOR for unknown staff', () => {
      expect(getStaffColor('Unknown Person')).toBe(DEFAULT_COLOR);
    });

    it('returns DEFAULT_COLOR for empty string', () => {
      expect(getStaffColor('')).toBe(DEFAULT_COLOR);
    });
  });

  describe('getColoredStaffNames', () => {
    it('returns all staff names with colors', () => {
      const names = getColoredStaffNames();
      expect(names).toContain('Viktor');
      expect(names).toContain('Vas');
      expect(names).toContain('Dad');
      expect(names).toContain('Steven');
      expect(names).toContain('Vitallik');
    });

    it('returns correct number of staff', () => {
      const names = getColoredStaffNames();
      expect(names.length).toBe(6); // Viktor, Vas, Dad, Gennadiy, Steven, Vitallik
    });
  });

  describe('color constants', () => {
    it('UNASSIGNED_COLOR is gray', () => {
      expect(UNASSIGNED_COLOR).toBe('#6B7280');
    });

    it('DEFAULT_COLOR is light gray', () => {
      expect(DEFAULT_COLOR).toBe('#9CA3AF');
    });
  });
});
