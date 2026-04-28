/**
 * Pure mapper from customer-tag string → display label + visual variant
 * for the Pick Jobs page redesign.
 *
 * Known canonical tags (per `frontend/src/features/jobs/types`'s
 * `CustomerTag` union) get the reference design's locked palette. Any
 * other string (future tags, free-form values, property-derived labels)
 * degrades cleanly to the neutral dashed pill with a title-cased label.
 *
 * Note: this mapper owns the labels for the redesigned page only; the
 * existing `CUSTOMER_TAG_CONFIG` keeps its labels for other features
 * (Customer detail, Jobs tab) untouched.
 */

export type CustomerTagVariant =
  | 'vip'
  | 'prepaid'
  | 'red'
  | 'amber'
  | 'commerc'
  | 'hoa'
  | 'ladder'
  | 'dog'
  | 'gated'
  | 'neutral';

export interface CustomerTagStyle {
  label: string;
  variant: CustomerTagVariant;
}

const KNOWN_TAGS: Record<string, CustomerTagStyle> = {
  priority:     { label: 'VIP',        variant: 'vip' },
  red_flag:     { label: 'Red Flag',   variant: 'red' },
  slow_payer:   { label: 'Slow Payer', variant: 'amber' },
  new_customer: { label: 'New',        variant: 'prepaid' },
};

export function getCustomerTagStyle(tag: string): CustomerTagStyle {
  const known = KNOWN_TAGS[tag];
  if (known) return known;
  return { label: titleCase(tag), variant: 'neutral' };
}

function titleCase(raw: string): string {
  if (!raw) return '';
  return raw
    .replace(/_/g, ' ')
    .replace(/\w\S*/g, (word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase());
}
