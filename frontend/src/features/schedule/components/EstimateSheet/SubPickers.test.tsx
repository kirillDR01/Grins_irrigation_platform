import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { SizeTierSubPicker } from './SizeTierSubPicker';
import { VariantSubPicker } from './VariantSubPicker';
import type { ServiceOffering } from '@/features/pricelist';

function offering(rule: Record<string, unknown>, model = 'size_tier'): ServiceOffering {
  return {
    id: 'cccccccc-cccc-cccc-cccc-cccccccccccc',
    name: 'Tree Drop',
    display_name: 'Tree Drop',
    slug: 'tree_drop',
    category: 'landscaping',
    customer_type: 'residential',
    subcategory: null,
    pricing_model: model as ServiceOffering['pricing_model'],
    pricing_rule: rule,
    description: null,
    base_price: null,
    price_per_zone: null,
    estimated_duration_minutes: null,
    duration_per_zone_minutes: null,
    staffing_required: 1,
    equipment_required: null,
    buffer_minutes: 10,
    lien_eligible: false,
    requires_prepay: false,
    is_active: true,
    replaced_by_id: null,
    includes_materials: false,
    source_text: null,
    created_at: '2026-05-01T00:00:00Z',
    updated_at: '2026-05-01T00:00:00Z',
  };
}

describe('SizeTierSubPicker', () => {
  it('renders array tiers and emits selection', async () => {
    const onSelect = vi.fn();
    const user = userEvent.setup();
    render(
      <SizeTierSubPicker
        offering={offering({
          tiers: [
            { label: 'S', price: 100 },
            { label: 'M', price: 200 },
            { label: 'L', price: 300 },
          ],
        })}
        onSelect={onSelect}
        onCancel={vi.fn()}
      />,
    );
    expect(screen.getByTestId('size-tier-subpicker')).toBeInTheDocument();
    await user.click(screen.getByTestId('size-tier-subpicker-confirm'));
    // Default selection is the first tier.
    expect(onSelect).toHaveBeenCalledWith('S', 100);
  });

  it('renders empty state when no tiers configured', () => {
    render(
      <SizeTierSubPicker
        offering={offering({})}
        onSelect={vi.fn()}
        onCancel={vi.fn()}
      />,
    );
    expect(screen.getByTestId('size-tier-subpicker-empty')).toBeInTheDocument();
  });

  it('renders seed-shape tiers (size + price + size_range_ft)', async () => {
    const onSelect = vi.fn();
    const user = userEvent.setup();
    render(
      <SizeTierSubPicker
        offering={offering({
          tiers: [
            { size: 'small', price: 750, size_range_ft: '10-20' },
            { size: 'medium', price: 1250, size_range_ft: '20-30' },
            { size: 'large', price: 2000, size_range_ft: '30-50' },
          ],
        })}
        onSelect={onSelect}
        onCancel={vi.fn()}
      />,
    );
    expect(screen.getByTestId('size-tier-subpicker')).toBeInTheDocument();
    await user.click(screen.getByTestId('size-tier-subpicker-confirm'));
    expect(onSelect).toHaveBeenCalledWith('Small (10-20 ft)', 750);
  });

  it('reads labor_amount alias for size_tier_plus_materials shape', async () => {
    const onSelect = vi.fn();
    const user = userEvent.setup();
    render(
      <SizeTierSubPicker
        offering={offering(
          {
            tiers: [
              { size: 'small_to_medium', labor_amount: 200 },
              { size: 'large', labor_amount: 400 },
            ],
          },
          'size_tier_plus_materials',
        )}
        onSelect={onSelect}
        onCancel={vi.fn()}
      />,
    );
    expect(screen.getByTestId('size-tier-subpicker')).toBeInTheDocument();
    await user.click(screen.getByTestId('size-tier-subpicker-confirm'));
    expect(onSelect).toHaveBeenCalledWith('Small to medium', 200);
  });
});

describe('VariantSubPicker', () => {
  it('renders variants array with prices', async () => {
    const onSelect = vi.fn();
    const user = userEvent.setup();
    render(
      <VariantSubPicker
        offering={offering(
          {
            variants: [
              { label: 'Brass valve', price: 75 },
              { label: 'Plastic valve', price: 35 },
            ],
          },
          'variants',
        )}
        onSelect={onSelect}
        onCancel={vi.fn()}
      />,
    );
    await user.click(screen.getByTestId('variant-subpicker-confirm'));
    expect(onSelect).toHaveBeenCalledWith('Brass valve', 75);
  });

  it('renders empty state when no variants configured', () => {
    render(
      <VariantSubPicker
        offering={offering({}, 'variants')}
        onSelect={vi.fn()}
        onCancel={vi.fn()}
      />,
    );
    expect(screen.getByTestId('variant-subpicker-empty')).toBeInTheDocument();
  });
});
