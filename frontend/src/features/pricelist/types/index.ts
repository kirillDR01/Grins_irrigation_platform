/**
 * Pricelist (ServiceOffering) types — mirror backend Pydantic schemas.
 * Source: src/grins_platform/schemas/service_offering.py
 */

import type { BaseEntity, PaginationParams } from '@/core/api';

// Mirrors backend ServiceCategory enum.
export type ServiceCategory =
  | 'seasonal'
  | 'repair'
  | 'installation'
  | 'diagnostic'
  | 'landscaping';

export const SERVICE_CATEGORY_LABEL: Record<ServiceCategory, string> = {
  seasonal: 'Seasonal',
  repair: 'Repair',
  installation: 'Installation',
  diagnostic: 'Diagnostic',
  landscaping: 'Landscaping',
};

export type CustomerType = 'residential' | 'commercial';

// Mirrors backend PricingModel enum (extended in umbrella plan Phase 1).
// Order intentionally matches the backend enum so dropdowns render
// legacy → flat → range → tiered → composite to keep mental model.
export const PRICING_MODELS = [
  'flat',
  'zone_based',
  'hourly',
  'custom',
  'flat_range',
  'flat_plus_materials',
  'per_unit_flat',
  'per_unit_range',
  'per_unit_flat_plus_materials',
  'per_zone_range',
  'tiered_zone_step',
  'tiered_linear',
  'compound_per_unit',
  'compound_repair',
  'size_tier',
  'size_tier_plus_materials',
  'yard_tier',
  'variants',
  'conditional_fee',
] as const;

export type PricingModel = (typeof PRICING_MODELS)[number];

export const PRICING_MODEL_LABEL: Record<PricingModel, string> = {
  flat: 'Flat',
  zone_based: 'Zone-based',
  hourly: 'Hourly',
  custom: 'Custom (free-form)',
  flat_range: 'Flat range (low/high)',
  flat_plus_materials: 'Flat + materials',
  per_unit_flat: 'Per-unit flat',
  per_unit_range: 'Per-unit range',
  per_unit_flat_plus_materials: 'Per-unit + materials',
  per_zone_range: 'Per-zone range',
  tiered_zone_step: 'Tiered zone step',
  tiered_linear: 'Tiered linear',
  compound_per_unit: 'Compound per-unit',
  compound_repair: 'Compound repair',
  size_tier: 'Size tier (S/M/L)',
  size_tier_plus_materials: 'Size tier + materials',
  yard_tier: 'Yard tier',
  variants: 'Variants',
  conditional_fee: 'Conditional fee',
};

// JSONB shape — keys vary by pricing_model; treated as opaque dict at the
// transport layer. Editor surfaces a structured panel per discriminator.
export type PricingRule = Record<string, unknown> | null;

export interface ServiceOffering extends BaseEntity {
  name: string;
  category: ServiceCategory;
  description: string | null;
  base_price: string | number | null;
  price_per_zone: string | number | null;
  pricing_model: PricingModel;
  estimated_duration_minutes: number | null;
  duration_per_zone_minutes: number | null;
  staffing_required: number;
  equipment_required: string[] | null;
  buffer_minutes: number;
  lien_eligible: boolean;
  requires_prepay: boolean;
  is_active: boolean;

  // Pricelist-editor extensions (umbrella plan Phase 1).
  slug: string | null;
  display_name: string | null;
  customer_type: CustomerType | null;
  subcategory: string | null;
  pricing_rule: PricingRule;
  replaced_by_id: string | null;
  includes_materials: boolean;
  source_text: string | null;
}

// Computed display label — falls back to canonical name if display_name is unset.
export function offeringDisplayLabel(o: ServiceOffering): string {
  return o.display_name?.trim() || o.name;
}

// POST /api/v1/services payload.
export interface ServiceOfferingCreate {
  name: string;
  category: ServiceCategory;
  pricing_model: PricingModel;
  description?: string | null;
  base_price?: number | null;
  price_per_zone?: number | null;
  estimated_duration_minutes?: number | null;
  duration_per_zone_minutes?: number | null;
  staffing_required?: number;
  equipment_required?: string[] | null;
  buffer_minutes?: number;
  lien_eligible?: boolean;
  requires_prepay?: boolean;

  slug?: string | null;
  display_name?: string | null;
  customer_type?: CustomerType | null;
  subcategory?: string | null;
  pricing_rule?: PricingRule;
  includes_materials?: boolean;
  source_text?: string | null;
}

// PUT /api/v1/services/{id} payload — every field optional.
export type ServiceOfferingUpdate = Partial<ServiceOfferingCreate> & {
  is_active?: boolean;
};

// GET /api/v1/services list params — mirrors api/v1/services.py query model.
export interface ServiceOfferingListParams extends PaginationParams {
  category?: ServiceCategory;
  is_active?: boolean;
  customer_type?: CustomerType;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
  // Client-only filter applied at render time — backend has no full-text
  // filter today, so the page does substring filter on the in-page slice.
  search?: string;
}

// History entry — one row per archived predecessor in the replaced_by_id
// chain. Phase 2 ships with placeholder data (no archive+create yet);
// Phase 1.5 will populate the full chain.
export interface ServiceOfferingHistoryEntry {
  id: string;
  display_name: string | null;
  pricing_model: PricingModel;
  pricing_rule: PricingRule;
  is_active: boolean;
  replaced_by_id: string | null;
  created_at: string;
  updated_at: string;
}

export type ServiceOfferingHistory = ServiceOfferingHistoryEntry[];
