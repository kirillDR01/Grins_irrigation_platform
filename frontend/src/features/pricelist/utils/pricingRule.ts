/**
 * Helpers for the pricing_rule JSONB body — the editor stays
 * structured-where-it-can-be and JSON-textarea where it can't.
 *
 * The umbrella plan defers the full Pydantic discriminated union to
 * Phase 1.5; this Phase 2 surface lets admins edit the most common
 * fields with native inputs and falls back to raw JSON for the
 * remainder.
 */

import type { PricingModel, PricingRule } from '../types';

export interface PricingRuleField {
  key: string;
  label: string;
  // Native input type — `number` for numeric fields, `text` for everything else.
  inputType: 'number' | 'text';
  // For tier shorthand like ``range_anchors.low`` we still bind to a single
  // dotted path; render keeps the dot in the label.
  helpText?: string;
}

// The fields we surface as labelled inputs per discriminator.
// Anything not listed here lives in the Raw JSON tab below the form.
export const PRICING_RULE_FIELDS_BY_MODEL: Partial<
  Record<PricingModel, PricingRuleField[]>
> = {
  flat: [{ key: 'price', label: 'Price ($)', inputType: 'number' }],
  flat_range: [
    { key: 'price_min', label: 'Min price ($)', inputType: 'number' },
    { key: 'price_max', label: 'Max price ($)', inputType: 'number' },
  ],
  flat_plus_materials: [
    { key: 'price', label: 'Labor price ($)', inputType: 'number' },
    {
      key: 'materials_note',
      label: 'Materials note',
      inputType: 'text',
      helpText: 'Optional descriptor — materials passed at cost.',
    },
  ],
  per_unit_flat: [
    { key: 'price_per_unit', label: 'Price per unit ($)', inputType: 'number' },
    {
      key: 'unit',
      label: 'Unit',
      inputType: 'text',
      helpText: 'e.g. ``zone``, ``ft``, ``sqft``',
    },
  ],
  per_unit_range: [
    { key: 'price_per_unit_min', label: 'Min per unit ($)', inputType: 'number' },
    { key: 'price_per_unit_max', label: 'Max per unit ($)', inputType: 'number' },
    { key: 'unit', label: 'Unit', inputType: 'text' },
  ],
  per_unit_flat_plus_materials: [
    { key: 'price_per_unit', label: 'Labor per unit ($)', inputType: 'number' },
    { key: 'unit', label: 'Unit', inputType: 'text' },
  ],
  per_zone_range: [
    {
      key: 'price_per_zone_min',
      label: 'Min per zone ($)',
      inputType: 'number',
    },
    {
      key: 'price_per_zone_max',
      label: 'Max per zone ($)',
      inputType: 'number',
    },
    { key: 'unit', label: 'Unit', inputType: 'text', helpText: 'e.g. ``zone``' },
  ],
  hourly: [
    { key: 'price_per_hour', label: 'Hourly rate ($)', inputType: 'number' },
  ],
  conditional_fee: [
    { key: 'price', label: 'Fee ($)', inputType: 'number' },
    {
      key: 'waived_when',
      label: 'Waived when',
      inputType: 'text',
      helpText: 'Free-form copy — e.g. ``approved on this estimate``.',
    },
  ],
};

export function getStructuredFields(model: PricingModel): PricingRuleField[] {
  return PRICING_RULE_FIELDS_BY_MODEL[model] ?? [];
}

/**
 * Read a JSON value at ``path`` (no dots in v1 — flat keys only).
 * Returns ``''`` so number inputs render as empty rather than ``NaN``.
 */
export function readField(rule: PricingRule, key: string): string {
  if (!rule) return '';
  const v = rule[key];
  if (v == null) return '';
  return String(v);
}

/**
 * Write ``value`` at ``path`` and return a fresh copy. Empty strings
 * unset the key so the JSON stays terse.
 */
export function writeField(
  rule: PricingRule,
  key: string,
  value: string,
  inputType: 'number' | 'text',
): PricingRule {
  const next: Record<string, unknown> = { ...(rule ?? {}) };
  if (value === '' || value == null) {
    delete next[key];
    return Object.keys(next).length ? next : null;
  }
  if (inputType === 'number') {
    const n = Number(value);
    next[key] = Number.isFinite(n) ? n : value;
  } else {
    next[key] = value;
  }
  return next;
}

export function rangeAnchors(
  rule: PricingRule,
): { low?: number; mid?: number; high?: number } | null {
  if (!rule || typeof rule !== 'object') return null;
  const a = (rule as Record<string, unknown>).range_anchors;
  if (!a || typeof a !== 'object') return null;
  return a as { low?: number; mid?: number; high?: number };
}

/**
 * Default amount for a freshly added line item — middle anchor if range is
 * present, else falls back to base_price-ish keys, else null.
 */
export function defaultAmountFromRule(rule: PricingRule): number | null {
  if (!rule) return null;
  const anchors = rangeAnchors(rule);
  if (anchors?.mid != null) return Number(anchors.mid);
  const candidates = ['price', 'price_min', 'price_per_unit', 'price_per_zone_min'];
  for (const k of candidates) {
    const v = (rule as Record<string, unknown>)[k];
    if (typeof v === 'number') return v;
    if (typeof v === 'string' && Number.isFinite(Number(v))) return Number(v);
  }
  return null;
}
