import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import { LineItemPicker } from './LineItemPicker';
import { serviceApi } from '@/features/pricelist/api/serviceApi';
import type { ServiceOffering } from '@/features/pricelist';

vi.mock('@/features/pricelist/api/serviceApi', () => ({
  serviceApi: {
    list: vi.fn(),
    get: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    deactivate: vi.fn(),
    history: vi.fn(),
    exportMarkdown: vi.fn(),
  },
}));

function makeOffering(overrides: Partial<ServiceOffering>): ServiceOffering {
  return {
    id: overrides.id ?? '11111111-1111-1111-1111-111111111111',
    name: overrides.name ?? 'Spring Start-Up',
    display_name: overrides.display_name ?? null,
    slug: overrides.slug ?? 'spring_startup_residential',
    category: overrides.category ?? 'seasonal',
    customer_type: overrides.customer_type ?? 'residential',
    subcategory: overrides.subcategory ?? null,
    pricing_model: overrides.pricing_model ?? 'flat',
    pricing_rule: overrides.pricing_rule ?? { price: 199 },
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

function wrapper() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  );
}

describe('LineItemPicker', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('emits a draft from a flat offering', async () => {
    vi.mocked(serviceApi.list).mockResolvedValue({
      items: [makeOffering({})],
      total: 1,
      page: 1,
      page_size: 100,
      total_pages: 1,
    });
    const onAdd = vi.fn();
    const user = userEvent.setup();

    render(<LineItemPicker customerType="residential" onAdd={onAdd} />, {
      wrapper: wrapper(),
    });

    await waitFor(() =>
      expect(screen.getByText('Spring Start-Up')).toBeInTheDocument(),
    );
    await user.click(
      screen.getByTestId(
        'line-item-picker-result-11111111-1111-1111-1111-111111111111',
      ),
    );
    await user.click(screen.getByTestId('line-item-picker-add'));

    expect(onAdd).toHaveBeenCalledWith(
      expect.objectContaining({
        service_offering_id: '11111111-1111-1111-1111-111111111111',
        unit_price: 199,
        quantity: 1,
        pricing_model: 'flat',
      }),
    );
  });

  it('renders range_anchors quick-pick chips when present', async () => {
    vi.mocked(serviceApi.list).mockResolvedValue({
      items: [
        makeOffering({
          id: 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
          pricing_model: 'flat_range',
          pricing_rule: {
            price_min: 100,
            price_max: 250,
            range_anchors: { low: 100, mid: 175, high: 250 },
          },
        }),
      ],
      total: 1,
      page: 1,
      page_size: 100,
      total_pages: 1,
    });
    const onAdd = vi.fn();
    const user = userEvent.setup();

    render(<LineItemPicker onAdd={onAdd} />, { wrapper: wrapper() });

    await waitFor(() =>
      expect(
        screen.getByTestId(
          'line-item-picker-result-aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
        ),
      ).toBeInTheDocument(),
    );
    await user.click(
      screen.getByTestId(
        'line-item-picker-result-aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
      ),
    );
    expect(screen.getByTestId('line-item-picker-anchor-low')).toBeInTheDocument();
    expect(screen.getByTestId('line-item-picker-anchor-high')).toBeInTheDocument();

    await user.click(screen.getByTestId('line-item-picker-anchor-mid'));
    expect(onAdd).toHaveBeenCalledWith(
      expect.objectContaining({
        unit_price: 175,
        selected_tier: 'mid',
      }),
    );
  });

  it('shows custom-quote prompt when quantity exceeds tier max', async () => {
    vi.mocked(serviceApi.list).mockResolvedValue({
      items: [
        makeOffering({
          id: 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
          pricing_model: 'tiered_zone_step',
          pricing_rule: { price: 60, max_zones_specified: 19 },
        }),
      ],
      total: 1,
      page: 1,
      page_size: 100,
      total_pages: 1,
    });
    const onAdd = vi.fn();
    const user = userEvent.setup();

    render(<LineItemPicker onAdd={onAdd} />, { wrapper: wrapper() });

    await waitFor(() =>
      expect(
        screen.getByTestId(
          'line-item-picker-result-bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
        ),
      ).toBeInTheDocument(),
    );
    await user.click(
      screen.getByTestId(
        'line-item-picker-result-bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
      ),
    );

    const qty = screen.getByTestId('line-item-picker-quantity');
    await user.clear(qty);
    await user.type(qty, '25');

    expect(screen.getByTestId('line-item-picker-above-max')).toBeInTheDocument();
    await user.click(screen.getByTestId('line-item-picker-custom-quote'));

    expect(onAdd).toHaveBeenCalledWith(
      expect.objectContaining({
        pricing_model: 'custom',
        unit_price: 0,
      }),
    );
  });

  it('passes the resolved customer type to the API by default', async () => {
    vi.mocked(serviceApi.list).mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 100,
      total_pages: 0,
    });
    render(<LineItemPicker customerType="commercial" onAdd={vi.fn()} />, {
      wrapper: wrapper(),
    });
    await waitFor(() =>
      expect(serviceApi.list).toHaveBeenCalledWith(
        expect.objectContaining({ customer_type: 'commercial' }),
      ),
    );
  });

  it('drops the customer_type filter when override toggle is on', async () => {
    vi.mocked(serviceApi.list).mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 100,
      total_pages: 0,
    });
    const user = userEvent.setup();
    render(<LineItemPicker customerType="residential" onAdd={vi.fn()} />, {
      wrapper: wrapper(),
    });
    await user.click(screen.getByTestId('line-item-picker-override'));
    await waitFor(() =>
      expect(serviceApi.list).toHaveBeenLastCalledWith(
        expect.objectContaining({ customer_type: undefined }),
      ),
    );
  });
});
