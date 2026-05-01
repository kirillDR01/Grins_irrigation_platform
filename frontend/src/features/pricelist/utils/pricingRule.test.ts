import { describe, it, expect } from 'vitest';
import {
  defaultAmountFromRule,
  getStructuredFields,
  rangeAnchors,
  readField,
  writeField,
} from './pricingRule';

describe('pricingRule helpers', () => {
  describe('readField', () => {
    it('returns empty string for null rule', () => {
      expect(readField(null, 'price')).toBe('');
    });

    it('returns empty string for missing key', () => {
      expect(readField({ other: 1 }, 'price')).toBe('');
    });

    it('stringifies numeric value', () => {
      expect(readField({ price: 199 }, 'price')).toBe('199');
    });
  });

  describe('writeField', () => {
    it('coerces number input', () => {
      const next = writeField(null, 'price', '199', 'number');
      expect(next).toEqual({ price: 199 });
    });

    it('keeps text input as string', () => {
      const next = writeField(null, 'unit', 'zone', 'text');
      expect(next).toEqual({ unit: 'zone' });
    });

    it('clearing the value removes the key', () => {
      const next = writeField({ price: 199, unit: 'zone' }, 'unit', '', 'text');
      expect(next).toEqual({ price: 199 });
    });

    it('returns null when last key is cleared', () => {
      const next = writeField({ price: 199 }, 'price', '', 'number');
      expect(next).toBeNull();
    });
  });

  describe('rangeAnchors', () => {
    it('returns null when absent', () => {
      expect(rangeAnchors({ price: 1 })).toBeNull();
    });

    it('extracts low/mid/high', () => {
      expect(
        rangeAnchors({ range_anchors: { low: 1, mid: 2, high: 3 } }),
      ).toEqual({ low: 1, mid: 2, high: 3 });
    });
  });

  describe('defaultAmountFromRule', () => {
    it('prefers range_anchors.mid', () => {
      expect(
        defaultAmountFromRule({
          price: 100,
          range_anchors: { low: 50, mid: 75, high: 100 },
        }),
      ).toBe(75);
    });

    it('falls back to price', () => {
      expect(defaultAmountFromRule({ price: 199 })).toBe(199);
    });

    it('handles per_zone_range fallback', () => {
      expect(
        defaultAmountFromRule({ price_per_zone_min: 50, price_per_zone_max: 80 }),
      ).toBe(50);
    });

    it('returns null when no candidate', () => {
      expect(defaultAmountFromRule({ unit: 'zone' })).toBeNull();
    });
  });

  describe('getStructuredFields', () => {
    it('returns empty for unmapped models', () => {
      expect(getStructuredFields('compound_repair')).toEqual([]);
    });

    it('returns flat fields', () => {
      const fields = getStructuredFields('flat');
      expect(fields).toHaveLength(1);
      expect(fields[0].key).toBe('price');
    });

    it('returns per_zone_range fields with unit', () => {
      const keys = getStructuredFields('per_zone_range').map((f) => f.key);
      expect(keys).toEqual(['price_per_zone_min', 'price_per_zone_max', 'unit']);
    });
  });
});
