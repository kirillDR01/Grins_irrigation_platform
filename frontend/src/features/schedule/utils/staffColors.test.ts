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
    it('has Viktor as teal-500', () => {
      expect(STAFF_COLORS.Viktor).toBe('#14B8A6');
    });

    it('has Vas as violet-500', () => {
      expect(STAFF_COLORS.Vas).toBe('#8B5CF6');
    });

    it('has Dad as amber-500', () => {
      expect(STAFF_COLORS.Dad).toBe('#F59E0B');
    });

    it('has Gennadiy as amber-500 (alias for Dad)', () => {
      expect(STAFF_COLORS.Gennadiy).toBe('#F59E0B');
    });

    it('has Steven as rose-500', () => {
      expect(STAFF_COLORS.Steven).toBe('#F43F5E');
    });

    it('has Vitallik as blue-500', () => {
      expect(STAFF_COLORS.Vitallik).toBe('#3B82F6');
    });
  });

  describe('getStaffColor', () => {
    it('returns correct color for Viktor', () => {
      expect(getStaffColor('Viktor')).toBe('#14B8A6');
    });

    it('returns correct color for Vas', () => {
      expect(getStaffColor('Vas')).toBe('#8B5CF6');
    });

    it('returns correct color for Dad', () => {
      expect(getStaffColor('Dad')).toBe('#F59E0B');
    });

    it('returns correct color for Steven', () => {
      expect(getStaffColor('Steven')).toBe('#F43F5E');
    });

    it('returns correct color for Vitallik', () => {
      expect(getStaffColor('Vitallik')).toBe('#3B82F6');
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
    it('UNASSIGNED_COLOR is slate-500', () => {
      expect(UNASSIGNED_COLOR).toBe('#64748B');
    });

    it('DEFAULT_COLOR is emerald-500', () => {
      expect(DEFAULT_COLOR).toBe('#10B981');
    });
  });
});
