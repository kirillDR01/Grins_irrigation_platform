import { describe, it, expect } from 'vitest';
import { isAddressLike, normalizeCity } from './city';

describe('normalizeCity', () => {
  it('case-insensitively normalizes the same city to one canonical form', () => {
    expect(normalizeCity('Eden Prairie')).toBe('Eden Prairie');
    expect(normalizeCity('eden prairie')).toBe('Eden Prairie');
    expect(normalizeCity(' EDEN PRAIRIE  ')).toBe('Eden Prairie');
  });

  it('returns null for empty / nullish / sentinel values', () => {
    expect(normalizeCity('')).toBe(null);
    expect(normalizeCity('   ')).toBe(null);
    expect(normalizeCity(null)).toBe(null);
    expect(normalizeCity(undefined)).toBe(null);
    expect(normalizeCity('Unknown')).toBe(null);
    expect(normalizeCity('UNKNOWN')).toBe(null);
  });

  it('returns null for digit-prefixed strings (street addresses)', () => {
    expect(normalizeCity('11071 Jackson Drive')).toBe(null);
    expect(normalizeCity('5808 View Ln Edina 55436')).toBe(null);
    expect(normalizeCity('4355 Vinewood Ln Plymouth, MN 55442')).toBe(null);
  });

  it('returns null for strings containing a state+ZIP token', () => {
    expect(normalizeCity('Andover, MN 55304')).toBe(null);
    expect(normalizeCity('Eden Prairie, MN 55344')).toBe(null);
    expect(normalizeCity('Plymouth MN 55442-1234')).toBe(null);
  });

  it('preserves punctuation in proper-noun abbreviations like "St. Paul"', () => {
    expect(normalizeCity('St. Paul')).toBe('St. Paul');
    expect(normalizeCity('st. paul')).toBe('St. Paul');
  });

  it('collapses internal whitespace', () => {
    expect(normalizeCity('Eden    Prairie')).toBe('Eden Prairie');
    expect(normalizeCity('  oak grove  ')).toBe('Oak Grove');
  });

  it('returns null when the value contains a bare street suffix token', () => {
    // "Plymouth Way" looks like a street name even without a digit prefix.
    expect(normalizeCity('Plymouth Way')).toBe(null);
    expect(normalizeCity('Vinewood Lane')).toBe(null);
  });
});

describe('isAddressLike', () => {
  it('returns true for digit-prefixed strings', () => {
    expect(isAddressLike('11071 Jackson Drive')).toBe(true);
    expect(isAddressLike('5808 View Ln Edina 55436')).toBe(true);
  });

  it('returns true for strings with state+ZIP tokens', () => {
    expect(isAddressLike('Andover, MN 55304')).toBe(true);
    expect(isAddressLike('Plymouth MN 55442')).toBe(true);
  });

  it('returns true for strings with bare street-suffix tokens', () => {
    expect(isAddressLike('Plymouth Way')).toBe(true);
    expect(isAddressLike('Main St')).toBe(true);
    expect(isAddressLike('Oak Drive')).toBe(true);
  });

  it('returns false for legitimate city names', () => {
    expect(isAddressLike('Eden Prairie')).toBe(false);
    expect(isAddressLike('Minneapolis')).toBe(false);
    expect(isAddressLike('St. Paul')).toBe(false);
    expect(isAddressLike('Bloomington')).toBe(false);
  });

  it('returns false for empty input', () => {
    expect(isAddressLike('')).toBe(false);
    expect(isAddressLike('   ')).toBe(false);
  });
});
