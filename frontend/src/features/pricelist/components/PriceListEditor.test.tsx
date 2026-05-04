import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import { PriceListEditor } from './PriceListEditor';
import type { ServiceOffering } from '../types';
import { serviceApi } from '../api/serviceApi';

vi.mock('../api/serviceApi', () => ({
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

const mockOfferings: ServiceOffering[] = [
  {
    id: '11111111-1111-1111-1111-111111111111',
    name: 'Spring Start-Up',
    display_name: 'Spring Start-Up',
    slug: 'spring_startup_residential',
    category: 'seasonal',
    customer_type: 'residential',
    subcategory: 'maintenance',
    pricing_model: 'flat',
    pricing_rule: { price: 199 },
    description: null,
    base_price: '199.00',
    price_per_zone: null,
    estimated_duration_minutes: 60,
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
  },
  {
    id: '22222222-2222-2222-2222-222222222222',
    name: 'Drip Install',
    display_name: 'Drip Install',
    slug: 'drip_install_commercial',
    category: 'installation',
    customer_type: 'commercial',
    subcategory: null,
    pricing_model: 'per_zone_range',
    pricing_rule: { price_per_zone_min: 200, price_per_zone_max: 300 },
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
    includes_materials: true,
    source_text: null,
    created_at: '2026-05-01T00:00:00Z',
    updated_at: '2026-05-01T00:00:00Z',
  },
];

function wrapper() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  );
}

describe('PriceListEditor', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(serviceApi.list).mockResolvedValue({
      items: mockOfferings,
      total: mockOfferings.length,
      page: 1,
      page_size: 20,
      total_pages: 1,
    });
  });

  it('renders rows from API', async () => {
    render(<PriceListEditor />, { wrapper: wrapper() });
    await waitFor(() => {
      expect(screen.getByText('Spring Start-Up')).toBeInTheDocument();
      expect(screen.getByText('Drip Install')).toBeInTheDocument();
    });
  });

  it('passes ?search= to the API after debounce', async () => {
    const user = userEvent.setup();
    render(<PriceListEditor />, { wrapper: wrapper() });
    await waitFor(() =>
      expect(screen.getByText('Spring Start-Up')).toBeInTheDocument(),
    );

    vi.mocked(serviceApi.list).mockClear();
    await user.type(screen.getByTestId('price-list-search'), 'Spring');

    await waitFor(
      () => {
        expect(serviceApi.list).toHaveBeenCalledWith(
          expect.objectContaining({ search: 'Spring' }),
        );
      },
      { timeout: 1500 },
    );
  });

  it('clears the search param when input is emptied', async () => {
    const user = userEvent.setup();
    render(<PriceListEditor />, { wrapper: wrapper() });
    await waitFor(() =>
      expect(screen.getByText('Spring Start-Up')).toBeInTheDocument(),
    );

    await user.type(screen.getByTestId('price-list-search'), 'drip');
    await waitFor(
      () =>
        expect(serviceApi.list).toHaveBeenCalledWith(
          expect.objectContaining({ search: 'drip' }),
        ),
      { timeout: 1500 },
    );

    vi.mocked(serviceApi.list).mockClear();
    await user.clear(screen.getByTestId('price-list-search'));
    await waitFor(
      () =>
        expect(serviceApi.list).toHaveBeenCalledWith(
          expect.objectContaining({ search: undefined }),
        ),
      { timeout: 1500 },
    );
  });

  it('opens drawer for new offering', async () => {
    const user = userEvent.setup();
    render(<PriceListEditor />, { wrapper: wrapper() });
    await waitFor(() =>
      expect(screen.getByTestId('price-list-new')).toBeInTheDocument(),
    );

    await user.click(screen.getByTestId('price-list-new'));
    const drawer = await screen.findByTestId('service-offering-drawer');
    expect(drawer).toBeInTheDocument();
    // "Cancel" button is unique to the drawer footer.
    expect(within(drawer).getByText('Cancel')).toBeInTheDocument();
  });

  it('shows empty state when API returns zero rows', async () => {
    const user = userEvent.setup();
    render(<PriceListEditor />, { wrapper: wrapper() });
    await waitFor(() =>
      expect(screen.getByText('Spring Start-Up')).toBeInTheDocument(),
    );

    vi.mocked(serviceApi.list).mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 20,
      total_pages: 0,
    });
    await user.type(screen.getByTestId('price-list-search'), 'zzznomatch');
    expect(await screen.findByTestId('price-list-empty')).toBeInTheDocument();
  });

  it('export downloads markdown', async () => {
    const user = userEvent.setup();
    vi.mocked(serviceApi.exportMarkdown).mockResolvedValue('# Pricelist');
    const createUrl = vi
      .spyOn(URL, 'createObjectURL')
      .mockReturnValue('blob:test');
    const revokeUrl = vi
      .spyOn(URL, 'revokeObjectURL')
      .mockImplementation(() => undefined);

    render(<PriceListEditor />, { wrapper: wrapper() });
    await waitFor(() =>
      expect(screen.getByTestId('price-list-export')).toBeInTheDocument(),
    );

    await user.click(screen.getByTestId('price-list-export'));
    await waitFor(() =>
      expect(serviceApi.exportMarkdown).toHaveBeenCalled(),
    );
    expect(createUrl).toHaveBeenCalled();
    revokeUrl.mockRestore();
    createUrl.mockRestore();
  });
});
